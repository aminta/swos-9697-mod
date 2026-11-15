"""Real Serie C / Serie D groups from the saved it.wikipedia wikitexts (S7 redraw, Panchina 15/11): the validation data of
tools/s7redraw.py. Sources: internal/sources/s7redraw/ (URL + md5 in its README.txt).
Serie C: each group's table lists its clubs (template {{Calcio <name>|N}} + the town's links); ONE national map per page gives every
club's coordinates ({{Mappa di localizzazione~|ITA|lat=..|long=..|label=<small>{{Calcio <name>|N}}</small>}}; a shared point labelled
'Milano' stands for Alcione + Inter U23).
Serie D: each group section has its own map, one point per club (lat, long, label), the member list (the table lists fewer clubs on
some pages).
`python3 tools/s7redraw_src.py <season> <C|D>` prints the groups."""
import os
import re

SRC = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'sources', 's7redraw')
SECOND = re.compile(r'U23|Next Gen|Futuro', re.I)


def town(cell):
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', cell):
        tgt, shown = m.group(1), m.group(2) or m.group(1)
        if tgt.startswith(('Provincia', 'Città metropolitana', 'File:')) or re.fullmatch(r'[A-Z]{2}', shown):
            continue
        return re.sub(r'\s*\((Italia|[^)]*)\)$', '', shown).strip()
    return ''


def _rows(tab):
    """The club rows of a table: {{Calcio X|N}} first cell, then the town cell (cells split by '||' or one per line)."""
    rows = []
    for r in re.split(r'\n\|-', tab)[1:]:
        r = r.strip()
        cells = [c.strip() for c in (re.split(r'\|\|', r.lstrip('|')) if '||' in r else [ln.lstrip('|').strip() for ln in r.split('\n')])]
        m = re.search(r'\{\{Calcio ([^|}]+)', cells[0]) if cells else None
        if m and len(cells) >= 2:
            tc = cells[2] if '||' in r and len(cells) > 2 else cells[1]
            rows.append((m.group(1).strip(), town(tc)))
    return rows


def _clean(lab):
    lab = re.sub(r'\{\{Calcio ([^|}]+)\|N\}\}', r'\1', lab)
    return re.sub(r"'{2,}|<[^>]+>", '', lab).strip()


def national_points(season):
    """Serie C page: {club label: (lat, lon)} of the national map."""
    t = open(os.path.join(SRC, f'itwiki-Serie_C_{season}.wikitext'), encoding='utf-8').read()
    return {_clean(lab): (float(la), float(lo)) for la, lo, lab in
            re.findall(r'\{\{Mappa di localizzazione~\|\s*ITA\s*\|\s*lat=([\d.]+)\s*\|\s*long=([\d.]+)\s*\|\s*label=<small>(.*?)</small>', t)}


def groups(season, level='C'):
    """{'A': [(club, town, lat, lon, second)]}: every club of the level's groups that season (lat / lon None: the map lacks it)."""
    out = {}
    if level == 'C':
        t = open(os.path.join(SRC, f'itwiki-Serie_C_{season}.wikitext'), encoding='utf-8').read()
        pts = national_points(season)
        for m in re.finditer(r'^== Girone ([A-C]) ==\n(.*?)(?=^== Girone |\Z)', t, re.S | re.M):
            g, sec = m.group(1), m.group(2)
            i = sec.index('Squadre partecipanti')
            gl = []
            for nm, tw in _rows(sec[i:].split('|}', 1)[0]):
                c = pts.get(nm) or pts.get(tw) or (None, None)
                gl.append((nm, tw, c[0], c[1], bool(SECOND.search(nm))))
            out[g] = gl
        return out
    for fn in [f'itwiki-Serie_D_{season}_gironi_{g}.wikitext' for g in ('A-B-C', 'D-E-F', 'G-H-I')]:
        t = open(os.path.join(SRC, fn), encoding='utf-8').read()
        for m in re.finditer(r'^== Girone ([A-I]) ==\n(.*?)(?=^== Girone |^== [A-Z][^=]|\Z)', t, re.S | re.M):
            g = m.group(1)
            if g in out:
                continue
            gl = []
            for ln in m.group(2).split('\n'):              # (one point a line; a section can hold several maps: islands, mainland)
                if not ln.startswith('{{Mappa di localizzazione~'):
                    continue
                c = re.search(r'lat=\s*([\d.]+)\s*\|\s*long=\s*([\d.]+)', ln)
                lb = re.search(r'label=(.*?)(?:\|position=|\|mark=|\}\}$)', ln)
                if c and lb:
                    gl.append((_clean(lb.group(1)), '', float(c.group(1)), float(c.group(2)), bool(SECOND.search(lb.group(1)))))
            out[g] = gl
    return out


if __name__ == '__main__':
    import sys
    for g, rows in groups(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'C').items():
        print(g, len(rows), 'no coords:', [n for n, t, la, lo, s in rows if la is None], [f'{n}({la},{lo})' for n, t, la, lo, s in rows][:3])
