"""Season-pack drafts from it.wikipedia: an Italian league season and its clubs' season pages.

  python3 tools/itwiki_season.py fetch packs/<id>     download the pages named in packs/<id>/itwiki.json into raw/itwiki
  python3 tools/itwiki_season.py draft packs/<id>     write clubs.csv + players.csv from the downloaded pages

packs/<id>/itwiki.json (everything the pages do not say, so a re-run gives the same CSVs):
  league        page title of the season, e.g. "Serie A 1947-1948" (final table + participants with 'dettagli' links)
  file          clubs.csv 'file' of the league clubs (default "league")
  template_src  calibrate source whose records give positions and kits (e.g. "orig/DATA/TEAM.020")
  templates     {club key: club name in template_src}: the record giving positions (default: the record of the
                club's own when its average price is within 6 of the target, else the record of the top two
                divisions closest to the target)
  same_club     {club key: club name in template_src}: the club's own record (its kit) when the names differ
  names         {club key: name shown in game} (default: the club's short name, upper case)
  coaches       {club key: coach} (default: the coach with most rounds, else the first one listed)
  apps          {club key: {player: appearances}} from other sources, for pages without player statistics
  targets       {"from": [points, target], "to": [points, target]}: average price byte, linear in final points;
                {"clubs": {key: target}} overrides
                (clubs without one take kit1 from the page's kit box, plain shirt)
  kits          {club key: "type shirt stripes shorts socks"} (kit1), overrides the page

Players: the squad box ('Calciatore in rosa') in order of league appearances (statistics table, else 'apps'); players
with unknown appearances follow those with 10 or more. Roles P D C A -> G D M A; nationality = flag of the squad box.
The pages are cached in raw/itwiki (provenance, as for the other packs); 'fetch' only downloads missing pages.
"""
import csv
import json
import os
import re
import struct
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
UA = 'swos-9697-mod season-pack tool (github.com/aminta/swos-9697-mod)'
ROLE = {'P': 'G', 'D': 'D', 'C': 'M', 'A': 'A'}
# it.wikipedia flag code -> SWOS player nationality (orig TEAM.080-085 national teams)
NAT = {'ALB': 0, 'AUT': 1, 'BEL': 2, 'BUL': 3, 'CRO': 4, 'CYP': 5, 'CSK': 6, 'CZE': 6, 'TCH': 6, 'DEN': 7, 'ENG': 8,
       'FIN': 11, 'FRA': 12, 'GER': 13, 'DEU': 13, 'GRE': 14, 'HUN': 15, 'ISL': 16, 'ISR': 17, 'ITA': 18, 'MLT': 22,
       'NED': 23, 'NLD': 23, 'NIR': 24, 'NOR': 25, 'POL': 26, 'POR': 27, 'PRT': 27, 'IRL': 46, 'ROU': 28, 'URS': 29,
       'RUS': 29, 'SCO': 31, 'SVN': 32, 'SWE': 33, 'TUR': 34, 'WAL': 36, 'YUG': 37, 'SVK': 39, 'ESP': 40, 'SUI': 45,
       'CHE': 45, 'ARG': 68, 'BOL': 69, 'BRA': 70, 'CHI': 71, 'CHL': 71, 'COL': 72, 'ECU': 73, 'PAR': 74, 'PRY': 74,
       'PER': 79, 'URU': 76, 'URY': 76, 'VEN': 77, 'USA': 58, 'MEX': 56, 'EGY': 105}
# SWOS kit colours (0 grey 1 white 2 black 3 orange 4 red 5 blue 6 maroon 7 light blue 8 green 9 yellow), RGB guesses
COLOURS = [(192, 192, 192), (255, 255, 255), (0, 0, 0), (255, 140, 0), (230, 0, 0), (0, 0, 200), (128, 20, 40),
           (120, 180, 240), (0, 160, 0), (255, 220, 0)]


def raw_dir(pack):
    return os.path.join(pack, 'raw', 'itwiki')


def page_file(pack, title):
    return os.path.join(raw_dir(pack), re.sub(r'[^\w.-]+', '_', title) + '.wiki')


def get(pack, title):
    path = page_file(pack, title)
    if not os.path.exists(path):
        url = 'https://it.wikipedia.org/w/index.php?' + urllib.parse.urlencode({'title': title, 'action': 'raw'})
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA})) as f:
            text = f.read().decode('utf-8')
        os.makedirs(raw_dir(pack), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        time.sleep(1)
    with open(path, encoding='utf-8') as f:
        return f.read()


def strip_refs(s):
    return re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', s, flags=re.S)


def article(s):
    """[[Title (disambiguation)|Text]] II -> ('Title', 'Text II'); plain text -> (text, text)."""
    s = strip_refs(s).replace("''", '')
    m = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', s)
    if not m:
        t = s.strip()
        return t, t
    tail = s[m.end():].strip()
    return re.sub(r'\s*\(.*?\)', '', m.group(1)).strip(), ((m.group(2) or m.group(1)) + ' ' + tail).strip()


def numeral(visible):
    m = re.search(r'\s(I{1,3}|IV|V|VI)$', visible)
    return m.group(1) if m else ''


def league(pack, cfg):
    """[(club key, Calcio template name, season page title, points)] in final table order."""
    w = get(pack, cfg['league'])
    pages = dict(re.findall(r'\{\{Calcio ([^|}]+)\|N(?:\|[^}]*)?\}\}\s*\n\|\s*\'\'\[\[([^\]|]+)\|dettagli\]\]', w))
    table = w[w.index('Classifica finale'):]
    table = table[:table.index('|}')]
    rows = re.findall(r"\{\{Calcio ([^|}]+)(?:\|[^}]*)?\}\}[^\n]*\n\|\|'*(\d+)'*", table)
    out = []
    for name, pts in rows:
        key = re.sub(r'\W', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower())
        out.append((key, name, pages[name], int(pts)))
    return out


def squad(w):
    rosa = []
    for m in re.finditer(r'\{\{Calciatore in rosa\|([^\n]*)\}\}', w):
        f = dict(x.split('=', 1) for x in re.split(r'\|(?![^\[]*\]\])', strip_refs(m.group(1))) if '=' in x)
        art, vis = article(f.get('nome', ''))
        n = numeral(vis)
        rosa.append(dict(name=art + (' ' + n if n and not art.endswith(n) else ''), art=art,
                         role=ROLE[f.get('ruolo', '').strip()],
                         nat=f.get('nazione', '').split()[0] if f.get('nazione') else 'ITA'))
    return rosa


def stats(w):
    """[(full name or None, surname, initial, appearances)] from 'Statistiche dei giocatori'."""
    if 'Statistiche dei giocatori' not in w:
        return []
    sec = strip_refs(w[w.rindex('Statistiche dei giocatori'):])
    sec = re.split(r'\n==[^=]', sec)[0]
    out = []
    for line in sec.split('\n'):
        m = re.search(r'\{\{Sommastat\|C=no\s*\|\s*(\d+)', line)
        if m:
            s = re.search(r'\{\{Sortname\|([^|}]*)\|([^|}]*)(?:\|([^|}=]*))?', line)
            if s:
                full = re.sub(r'\s*\(.*?\)', '', s.group(3)).strip() if s.group(3) else None
                out.append((full, s.group(2).strip(), s.group(1).strip()[:1], int(m.group(1))))
            else:                                   # plain text: | N. Lombardi {{Sommastat...
                t = re.sub(r'\{\{.*', '', line.lstrip('| ')).strip()
                out.append((None, t.split()[-1], t[:1], int(m.group(1))))
            continue
        m = re.match(r'\|\s*(?:\{\{[^}]*\}\}\s*)?(\[\[[^\]]+\]\][^|]*)\|\|\s*(\d+)', line)
        if m:                                       # wikitable: | [[Name]] || pres || gol
            art, vis = article(m.group(1))
            out.append((art, art.split()[-1], art[:1], int(m.group(2))))
    return out


def appearances(p, st, extra):
    if p['art'] in extra or p['name'] in extra:
        return extra.get(p['art'], extra.get(p['name']))
    for full, sur, ini, n in st:
        if full == p['art']:
            return n
    words = p['art'].split()                        # else surname + initial (the link may name another homonym)
    hits = [n for full, sur, ini, n in st
            if re.sub(r'\s+(I{1,3}|IV|V|VI)$', '', sur) in (words[-1], ' '.join(words[1:]))
            and (not ini or p['art'].startswith(ini))]
    if len(hits) == 1:
        return hits[0]
    return 0 if st else None                        # not in the statistics table: no league appearance


def coach(w, key, cfg):
    if key in cfg.get('coaches', {}):
        return cfg['coaches'][key]
    box = dict(re.findall(r'\|(allenatore\d?|titolo allenatore\d?)\s*=\s*([^\n]*)', w))
    field = next((box[k.replace('titolo ', '')] for k, v in box.items()
                  if k.startswith('titolo') and v.strip().lower() == 'allenatore'), None) or \
        box.get('allenatore1') or box.get('allenatore', '')
    field = strip_refs(field)
    names = re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]\s*(?:<small>\((\d+)ª-(\d+)ª\)</small>)?', field)
    if not names:
        return ''
    best = max(names, key=lambda x: int(x[3]) - int(x[2]) if x[2] else -1) if any(x[2] for x in names) else names[0]
    return re.sub(r'\s*\(.*?\)', '', best[0]).strip()


def kit_from_page(w):
    def colour(h):
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        return min(range(10), key=lambda c: sum((a - b) ** 2 for a, b in zip(rgb, COLOURS[c])))
    k = dict(re.findall(r'\b(body|shorts|socks)\s*=\s*([0-9A-Fa-f]{6})', w))
    return f"0 {colour(k['body'])} {colour(k['body'])} {colour(k['shorts'])} {colour(k['socks'])}" if len(k) == 3 else ''


def records(path):
    d = open(os.path.join(ROOT, path), 'rb').read()
    return [d[2 + k * 684:2 + (k + 1) * 684] for k in range(struct.unpack('>H', d[:2])[0])]


def draft(pack):
    cfg = json.load(open(os.path.join(pack, 'itwiki.json'), encoding='utf-8'))
    clubs = league(pack, cfg)
    trecs = records(cfg['template_src'])
    tnames = [r[5:22].split(b'\0')[0].decode('latin1') for r in trecs]
    avg = lambda r: sum(r[76 + j * 38 + 32] for j in range(16)) / 16
    tg = cfg.get('targets', {})
    (p0, t0), (p1, t1) = tg.get('from', [0, 15]), tg.get('to', [100, 30])
    crow, prow = [], []
    for key, short, title, pts in clubs:
        w = get(pack, title)
        rosa, st, extra = squad(w), stats(w), cfg.get('apps', {}).get(key, {})
        for p in rosa:
            p['apps'] = appearances(p, st, extra)
        known = sorted([p for p in rosa if p['apps'] is not None], key=lambda p: -p['apps'])
        unknown = [p for p in rosa if p['apps'] is None]
        if unknown:
            hi = [p for p in known if p['apps'] >= 10]
            known = hi + unknown + [p for p in known if p['apps'] < 10]
        target = tg.get('clubs', {}).get(key, round(t0 + (pts - p0) * (t1 - t0) / (p1 - p0)))
        own = cfg.get('same_club', {}).get(key, short.upper())
        own = tnames.index(own) if own in tnames else ''
        if key in cfg.get('templates', {}):
            templ = tnames.index(cfg['templates'][key])
        elif own != '' and abs(avg(trecs[own]) - target) <= 6:
            templ = own                             # its own record reaches the target (calibrate moves +-3 levels)
        else:                                       # the top-two-division record closest to the target strength
            templ = min((k for k, r in enumerate(trecs) if r[25] <= 1),
                        key=lambda k: (abs(avg(trecs[k]) - target), k))
        crow.append(dict(key=key, name=cfg.get('names', {}).get(key, short.upper())[:16], coach=coach(w, key, cfg),
                         country='ITA', file=cfg.get('file', 'league'), template=templ, target=target, kit='' if own in ('', templ) else own,
                         kit1=cfg.get('kits', {}).get(key, kit_from_page(w) if own == '' else ''), kit2='',
                         source=title, points=pts))
        for p in known:
            prow.append(dict(club=key, name=p['name'], role=p['role'], nat=NAT.get(p['nat'], ''),
                             apps='' if p['apps'] is None else p['apps']))
        print(f"{key:12} {pts:3} pts target {target:2} template {templ!s:3} coach {crow[-1]['coach']:22} "
              f"{len(rosa)} players, {len(unknown)} without appearances")
    for name, rows in (('clubs.csv', crow), ('players.csv', prow)):
        with open(os.path.join(pack, name), 'w', encoding='utf-8', newline='') as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)


def fetch(pack):
    cfg = json.load(open(os.path.join(pack, 'itwiki.json'), encoding='utf-8'))
    for key, short, title, pts in league(pack, cfg):
        get(pack, title)
        print(key, title)


if __name__ == '__main__':
    {'fetch': fetch, 'draft': draft}[sys.argv[1]](sys.argv[2].rstrip('/'))
