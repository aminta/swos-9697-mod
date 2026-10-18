"""The FORMAT page's texts (fmtpage.py): a compact in-game rendering of the competitions' formats, 4 languages.

Keys: the title the game shows in the competition view = the country's button name in the exe language + ' ' + the
competition's first name (packs: button_names / names), e.g. 'ITALIA 1947-48 SERIE A 1947-48'; European cups of a pack
(layout european) and tourneys have no country (the game writes '' + ' ' + name). The contest id (the pack's 'id',
hex: 'EC' = 0xEC) goes with the key.
Texts: upper case, the game's font (no accents: transliterated), lines of at most W characters, pages of
fmtpage.LINES lines. The model of a competition is complist's (_league / _cup), plus the pack's win points.

Usage: python3 tools/fmtgame.py OUT_DIR PACK_DIR ...   (writes FMTxx[world].DAT for xx = IT, EN, FR, DE)
"""
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
import complist
import fmtpage

W = 40
EXTRA = []      # [(world, contest id or None, {lang: title}, {lang: [lines]})] from readers other than the packs:
                # 4.0's from_build9697 (the 1996-97 base game, the worlds' generated European cups, with 4.0's names)
LANGS = ('it', 'en', 'fr', 'de')

T = {
    'it': dict(promedio=['GIU: ULTIMO PROMEDIO (3 STAGIONI)', 'E ULTIMO DELLA CLASSIFICA ANNUALE;', 'PARI: SPAREGGIO IN CAMPO NEUTRO'], po_kind={'promotion': 'PLAY-OFF PROMOZIONE', 'europe': 'PLAY-OFF EUROPEO', 'placement': 'SPAREGGIO', 'playout': 'PLAY-OUT', 'title': 'PLAY-OFF SCUDETTO'}, better='IN PARITA PASSA LA MEGLIO PIAZZATA', et_better='SUPPLEMENTARI, POI LA MEGLIO PIAZZATA', gap='NON SI GIOCA SE C SONO {n}+ PUNTI DI DISTACCO', win_to='LA VINCENTE IN {d}', ita=['PLAY-OFF B: 3A-8A, PLAY-OUT: 16A-17A', 'PLAY-OFF C A 28 SQUADRE: 4A PROMOSSA'],
               teams='{n} SQUADRE', clubs='{n} SQUADRE', rr={1: 'GIRONE DI SOLA ANDATA', 2: 'ANDATA E RITORNO', 3: 'TRE GIRONI',
                                        4: 'QUATTRO GIRONI'},
               days='{n} GIORNATE', rest='UNA SQUADRA RIPOSA OGNI GIORNATA', pts='VITTORIA {w} PUNTI, PAREGGIO 1',
               up='PROMOSSE: {n}', down='RETROCESSE: {n}', none_down='NESSUNA RETROCESSIONE',
               ko='{n} SQUADRE A ELIMINAZIONE DIRETTA', byes='{n} ESENTI FINO AL 2. TURNO',
               r={'single': 'GARA UNICA, IN PARITA RIGORI', 'single_et': 'GARA UNICA, SUPPLEMENTARI E RIGORI',
                  'two_legs': 'ANDATA E RITORNO, GOL IN TRASFERTA', 'single_replay': 'GARA UNICA, IN PARITA RIPETIZIONE',
                  'two_legs_pens': 'ANDATA E RITORNO, POI RIGORI', 'two_legs_replay': 'ANDATA E RITORNO, IN PARITA SPAREGGIO'},
               rk='TURNI {a}-{b}: ', r1='TURNO {a}: ', final='FINALE: ', real='PRIMO TURNO COME NEL SORTEGGIO VERO',
               gen='SORTEGGIO DEL GIOCO', groups='{k} GIRONI PARALLELI DA {s}', split='DOPO {a} GIORNATE:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: NIENT ALTRO', half=', PUNTI DIMEZZATI', reset=', DA 0 PUNTI',
               po='{name}: {who}', third='FINALE 3. POSTO', ord=lambda n: f'{n}A'),
    'en': dict(promedio=['DOWN: THE LAST 3-SEASON PROMEDIO', 'AND THE LAST OF THE ANNUAL TABLE;', 'LEVEL: A PLAY-OFF, NEUTRAL GROUND'], po_kind={'promotion': 'PROMOTION PLAY-OFF', 'europe': 'EUROPEAN PLAY-OFF', 'placement': 'PLACEMENT PLAY-OFF', 'playout': 'PLAY-OUT', 'title': 'TITLE PLAY-OFF'}, better='LEVEL: THE BETTER PLACED GOES THROUGH', et_better='EXTRA TIME, THEN THE BETTER PLACED', gap='NOT PLAYED WITH A {n}+ POINT GAP', win_to='THE WINNER TO {d}', ita=['SERIE B PLAY-OFF 3RD-8TH, PLAY-OUT 16-17', 'SERIE C PLAY-OFF OF 28 CLUBS: 4TH UP'],
               teams='{n} TEAMS', clubs='{n} CLUBS', rr={1: 'SINGLE ROUND ROBIN', 2: 'HOME AND AWAY', 3: 'TRIPLE ROUND ROBIN',
                                      4: 'QUADRUPLE ROUND ROBIN'},
               days='{n} MATCHDAYS', rest='ONE CLUB RESTS EACH MATCHDAY', pts='WIN {w} POINTS, DRAW 1',
               up='PROMOTED: {n}', down='RELEGATED: {n}', none_down='NO RELEGATION',
               ko='{n} CLUBS, KNOCKOUT', byes='{n} BYES TO ROUND 2',
               r={'single': 'SINGLE MATCH, A DRAW: PENALTIES', 'single_et': 'SINGLE MATCH, EXTRA TIME, PENALTIES',
                  'two_legs': 'TWO LEGS, AWAY GOALS', 'single_replay': 'SINGLE MATCH, A DRAW: REPLAY',
                  'two_legs_pens': 'TWO LEGS, THEN PENALTIES', 'two_legs_replay': 'TWO LEGS, LEVEL: A REPLAY'},
               rk='ROUNDS {a}-{b}: ', r1='ROUND {a}: ', final='FINAL: ', real='ROUND 1 AS REALLY DRAWN',
               gen='DRAWN BY THE GAME', groups='{k} PARALLEL GROUPS OF {s}', split='AFTER {a} MATCHDAYS:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: NO MORE MATCHES', half=', POINTS HALVED', reset=', FROM 0 POINTS',
               po='{name}: {who}', third='THIRD PLACE MATCH', ord=lambda n: f'{n}{complist._sfx(n).upper()}'),
    'fr': dict(promedio=['DESCENTE: DERNIER PROMEDIO (3 ANS)', 'ET DERNIER DU CLASSEMENT ANNUEL;', 'EGALITE: BARRAGE, TERRAIN NEUTRE'], po_kind={'promotion': 'BARRAGES DE MONTEE', 'europe': 'BARRAGES EUROPEENS', 'placement': 'BARRAGES DE CLASSEMENT', 'playout': 'BARRAGES DE MAINTIEN', 'title': 'PLAY-OFF DU TITRE'}, better='NUL: LE MIEUX CLASSE PASSE', et_better='PROLONGATION, PUIS LE MIEUX CLASSE', gap='PAS JOUE AVEC {n}+ POINTS D ECART', win_to='LE VAINQUEUR EN {d}', ita=['BARRAGES SERIE B 3E-8E, MAINTIEN 16E-17E', 'BARRAGES SERIE C A 28 CLUBS: 4E PROMU'],
               teams='{n} EQUIPES', clubs='{n} CLUBS', rr={1: 'MATCHS ALLER', 2: 'MATCHS ALLER ET RETOUR', 3: 'TROIS TOURS',
                                      4: 'QUATRE TOURS'},
               days='{n} JOURNEES', rest='UN CLUB AU REPOS A CHAQUE JOURNEE', pts='VICTOIRE {w} POINTS, NUL 1',
               up='PROMUS: {n}', down='RELEGUES: {n}', none_down='PAS DE RELEGATION',
               ko='{n} CLUBS, ELIMINATION DIRECTE', byes='{n} EXEMPTS JUSQU AU 2E TOUR',
               r={'single': 'MATCH UNIQUE, NUL: TIRS AU BUT', 'single_et': 'MATCH UNIQUE, PROLONGATION, T.A.B.',
                  'two_legs': 'ALLER-RETOUR, BUTS A L EXTERIEUR', 'single_replay': 'MATCH UNIQUE, NUL: A REJOUER',
                  'two_legs_pens': 'ALLER-RETOUR, PUIS TIRS AU BUT', 'two_legs_replay': 'ALLER-RETOUR, EGALITE: A REJOUER'},
               rk='TOURS {a}-{b}: ', r1='TOUR {a}: ', final='FINALE: ', real='1ER TOUR COMME LE VRAI TIRAGE',
               gen='TIRAGE DU JEU', groups='{k} GROUPES PARALLELES DE {s}', split='APRES {a} JOURNEES:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: PLUS DE MATCHS', half=', POINTS DIVISES PAR 2',
               reset=', A PARTIR DE 0 POINT', po='{name}: {who}', third='MATCH POUR LA 3E PLACE',
               ord=lambda n: f'{n}E'),
    'de': dict(promedio=['ABSTIEG: LETZTER PROMEDIO (3 SAISONS)', 'UND LETZTER DER JAHRESTABELLE;', 'GLEICH: ENTSCHEIDUNGSSPIEL, NEUTRAL'], po_kind={'promotion': 'AUFSTIEGSPLAYOFFS', 'europe': 'EUROPAPOKAL-PLAYOFFS', 'placement': 'PLATZIERUNGSSPIELE', 'playout': 'ABSTIEGSPLAYOFFS', 'title': 'MEISTER-PLAYOFFS'}, better='REMIS: DER BESSER PLATZIERTE', et_better='VERLAENGERUNG, DANN DER BESSER PLATZIERTE', gap='NICHT GESPIELT BEI {n}+ PUNKTEN ABSTAND', win_to='DER SIEGER IN DIE {d}', ita=['SERIE B: PLAYOFFS 3.-8., PLAYOUT 16.-17.', 'SERIE C: PLAYOFFS MIT 28 VEREINEN: 4. AUF'],
               teams='{n} MANNSCHAFTEN', clubs='{n} VEREINE', rr={1: 'EINFACHRUNDE', 2: 'HIN- UND RUECKRUNDE', 3: 'DREI RUNDEN',
                                        4: 'VIER RUNDEN'},
               days='{n} SPIELTAGE', rest='JEDEN SPIELTAG HAT EIN VEREIN FREI', pts='SIEG {w} PUNKTE, REMIS 1',
               up='AUFSTEIGER: {n}', down='ABSTEIGER: {n}', none_down='KEIN ABSTIEG',
               ko='{n} VEREINE, K.-O.-SYSTEM', byes='{n} FREILOSE BIS RUNDE 2',
               r={'single': 'EIN SPIEL, REMIS: ELFMETER', 'single_et': 'EIN SPIEL, VERLAENGERUNG, ELFMETER',
                  'two_legs': 'HIN- UND RUECKSPIEL, AUSWAERTSTORE', 'single_replay': 'EIN SPIEL, REMIS: WIEDERHOLUNG',
                  'two_legs_pens': 'HIN- UND RUECKSPIEL, DANN ELFMETER', 'two_legs_replay': 'HIN- UND RUECKSPIEL, GLEICHSTAND: WIEDERHOLUNG'},
               rk='RUNDEN {a}-{b}: ', r1='RUNDE {a}: ', final='FINALE: ', real='RUNDE 1 WIE DIE ECHTE AUSLOSUNG',
               gen='AUSLOSUNG DES SPIELS', groups='{k} PARALLELE STAFFELN ZU {s}', split='NACH {a} SPIELTAGEN:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: KEINE SPIELE MEHR', half=', PUNKTE HALBIERT',
               reset=', AB 0 PUNKTEN', po='{name}: {who}', third='SPIEL UM PLATZ 3', ord=lambda n: f'{n}.'),
}

UMLAUT = {'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE', 'ß': 'SS', 'ä': 'AE', 'ö': 'OE', 'ü': 'UE'}


def ascii_up(s, lang='it'):
    """Upper case in the game's font: accents dropped (German umlauts as AE / OE / UE)."""
    if lang == 'de':
        s = ''.join(UMLAUT.get(c, c) for c in s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return s.upper().replace(';', ',')


def wrap(text, w=W):
    out = []
    for para in text.split('\n'):
        line = ''
        for word in para.split(' '):
            if not word:
                continue
            if len(line) + len(word) + (1 if line else 0) <= w:
                line = f'{line} {word}' if line else word
            else:
                if line:
                    out.append(line)
                while len(word) > w:
                    out.append(word[:w])
                    word = word[w:]
                line = word
        out.append(line)
    return out


def pages(lines):
    n = fmtpage.LINES
    return [lines[i:i + n] for i in range(0, len(lines), n)] or [[]]


def _runs(codes, t):
    if not codes:
        return []
    if all(c == codes[0] for c in codes[:-1]) and len(codes) > 1:
        out = [(t['rk'].format(a=1, b=len(codes) - 1) if len(codes) > 2 else t['r1'].format(a=1)) + t['r'][codes[0]]]
    else:
        out, a = [], 0
        for i in range(1, len(codes)):
            if i == len(codes) - 1 or codes[i] != codes[a]:
                out.append((t['rk'].format(a=a + 1, b=i) if i - a > 1 else t['r1'].format(a=a + 1)) + t['r'][codes[a]])
                a = i
    out.append(t['final'] + t['r'][codes[-1]])
    return out


def league_text(div, win, t, names=None, lang='it', lowest=False, rest_note=True):
    n, g = div['clubs'], div['games']
    days = (n if n % 2 else n - 1) * g
    lines = [f"{t['clubs'].format(n=n)}, {t['rr'].get(g, '')}", t['days'].format(n=days)]
    if n % 2 and rest_note:
        lines.append(t['rest'])
    lines.append(t['pts'].format(w=win))
    if div.get('up'):
        lines.append(t['up'].format(n=div['up']))
    if div.get('down'):
        lines.append(t['down'].format(n=div['down']))
    elif lowest:
        lines.append(t['none_down'])
    sp = div.get('split')
    if sp:
        for st in sp.get('stages') or [sp]:
            if 'fixtures' in st:                # (a fixture-list stage, e.g. Argentina's zones: no places groups)
                continue
            lines.append(t['split'].format(a=st['after']))
            for gr in st['groups']:
                a, b = gr['places']
                r = {'none': 0, 'single': 1, 'double': 2}[gr.get('rounds', 'single')]
                s = t['grp0'].format(a=a, b=b) if not r else t['grp'].format(a=a, b=b, rr=t['rr'][r])
                s += {'half_up': t['half'], 'half_down': t['half'], 'reset': t['reset']}.get(gr.get('points', 'full'), '')
                lines.append(s)
    for po in div.get('playoffs') or []:
        lines += po_text(po, names, t, lang)
    return lines


def _rule(r, t):
    legs, lvl = r.get('legs', 1), r.get('level', 'et_pens')
    if legs == 2:
        base = t['r']['two_legs']
    else:
        base = t['r']['single_et' if lvl in ('et_pens', 'et_better') else 'single']
    if lvl == 'better':
        base = (t['r']['two_legs'] if legs == 2 else t['r']['single'].split(',')[0]) + ', ' + t['better']
    elif lvl == 'et_better':
        base = t['r']['single'].split(',')[0] + ', ' + t['et_better']
    return base


def po_text(po, names, t, lang):
    by = {}
    for e in po.get('entrants', []):
        if isinstance(e, list):
            by.setdefault(e[0], []).append(e[1])
    who = []
    for dv, pls in sorted(by.items()):
        pls = sorted(pls)
        rng = t['ord'](pls[0]) if len(pls) == 1 else (f"{t['ord'](pls[0])}-{t['ord'](pls[-1])}"
                                                      if pls == list(range(pls[0], pls[-1] + 1)) else
                                                      ', '.join(t['ord'](p) for p in pls))
        who.append((complist._nm(names[dv], lang) + ' ' if len(by) > 1 and names else '') + rng)
    if po.get('kind') == 'promedio':            # Argentina: no entrants, no rounds
        return list(t['promedio'])
    out = [f"{t['po_kind'].get(po.get('kind', 'promotion'), 'PLAY-OFF')}: {' + '.join(who)}"]
    rs = [_rule(r, t) for r in po['rounds']]
    if all(x == rs[0] for x in rs):
        out.append(rs[0])
    else:
        out += [t['r1'].format(a=i + 1) + x for i, x in enumerate(rs)]
    if any(r.get('gap') for r in po['rounds']):
        out.append(t['gap'].format(n=max(r.get('gap') or 0 for r in po['rounds'])))
    if po.get('kind') == 'promotion' and po.get('winner_div') is not None and names:
        out.append(t['win_to'].format(d=complist._nm(names[po['winner_div']], lang)))
    return out


def cup_text(cp, t):
    lines = [t['ko'].format(n=cp['clubs'])]
    if cp.get('byes'):
        lines.append(t['byes'].format(n=cp['byes']))
    lines += _runs(cp['rounds'], t)
    if cp.get('src') == 'real':
        lines.append(t['real'])
    return lines


def tourney_text(c, t):
    st = c.get('stages', [])
    ko = [x for x in st if x['type'] == 'knockout']
    lines = [t['ko'].format(n=ko[0]['teams']).replace(t['clubs'].format(n=ko[0]['teams']), t['teams'].format(n=ko[0]['teams']))] if ko else []
    ms = {x['matches'] for x in st if 'matches' in x}     # (a group stage has no 'matches': lp36's test pack)
    if len(ms) == 1:
        lines.append(t['r'][ms.pop()])
    else:
        lines += [f"{t['clubs'].format(n=x['teams'])}: {t['r'][x['matches']]}" for x in ko if 'matches' in x]
    if any(x['type'] == 'third_place' for x in st):
        lines.append(t['third'])
    return lines


def from_pack(d):
    """[(world, contest id, {lang: title}, {lang: [lines]})] of one pack."""
    m = json.load(open(os.path.join(d, 'pack.json')))
    clubs = complist.csv.DictReader(open(os.path.join(d, 'clubs.csv'), encoding='utf-8')) \
        if os.path.exists(os.path.join(d, 'clubs.csv')) else []
    clubs = [dict(r, file=r.get('file') or 'league', division=r.get('division') or '0') for r in clubs]
    tp = os.path.join(d, 'ties.csv')
    ties = list(complist.csv.DictReader(open(tp, encoding='utf-8'))) if os.path.exists(tp) else []
    bn = m.get('button_names') or {}
    world = m.get('world', 0) if m.get('kind') == 'career' else 0
    out = []
    for comp in m.get('competitions', []):
        cid = int(comp['id'], 16) if comp.get('id') else None
        euro = comp.get('layout') == 'european' or comp['type'] == 'tourney'
        def title(lang, name):
            country = '' if euro else bn.get(lang, m.get('button', ''))   # the game's own spelling: as is
            return f'{country} {name}'.upper()
        if comp['type'] == 'league':
            lg = complist._league(comp, clubs)
            win = comp.get('win_points', 3)
            k = 0
            for lv in lg['levels']:
                for div in lv:
                    titles, texts = {}, {}
                    for lang in LANGS:
                        nm = complist._nm(div['name'], lang)
                        titles[lang] = title(lang, nm)
                        low = lg['closed'] or lv is lg['levels'][-1]
                        texts[lang] = league_text(div, win, T[lang], lg['names'], lang, low) + \
                            (T[lang]['ita'] if lg['special'] and k == min(1, len(lg['names']) - 1) else [])
                    out.append((world, cid, titles, texts))
                    k += 1
        elif comp['type'] == 'cup':
            cp = complist._cup(comp, ties, 'cup', {})
            titles = {lang: title(lang, complist._nm(comp['names'], lang)) for lang in LANGS}
            out.append((world, cid, titles, {lang: cup_text(cp, T[lang]) for lang in LANGS}))
        elif comp['type'] == 'tourney':
            titles = {lang: title(lang, complist._nm(comp['names'], lang)) for lang in LANGS}
            out.append((world, cid, titles, {lang: tourney_text(comp, T[lang]) for lang in LANGS}))
    return out


def write(out_dir, items):
    """FMTxx[world].DAT per language and world from [(world, cid, titles, texts)]."""
    by, keys = {}, {}
    for world, cid, titles, texts in items:
        for lang in LANGS:
            body = [x for line in texts[lang] for x in wrap(ascii_up(line, lang))]
            key = titles[lang][:fmtpage.NAME - 1]
            k = (lang, world, key)
            if k in keys:                       # the same title twice (two divisions with one name): one page,
                keys[k].extend([''] + body)     # both descriptions
                continue
            keys[k] = body
            by.setdefault((lang, world), []).append((cid, key, None))
    by = {lw: [(cid, key, pages(keys[(lw[0], lw[1], key)])) for cid, key, _ in lst] for lw, lst in by.items()}
    files = []
    for (lang, world), lst in sorted(by.items()):
        name = f'FMT{lang.upper()}{world or ""}.DAT'
        fmtpage.build(os.path.join(out_dir, name), lst)
        files.append((name, len(lst)))
    return files


def file_names(pack_dirs):
    """The FMTxx[world].DAT names write() makes for these packs (mkpatcher: the files to ship)."""
    worlds = sorted({w for d in pack_dirs for w, *_ in from_pack(d)} | {w for w, *_ in EXTRA})
    return [f'FMT{lang.upper()}{w or ""}.DAT' for w in worlds for lang in LANGS]


def main(argv):
    out, dirs = argv[0], argv[1:]
    items = []
    for d in dirs:
        if os.path.exists(os.path.join(d, 'pack.json')):
            items += from_pack(d)
        else:
            items += [x for s in sorted(os.listdir(d)) if os.path.exists(os.path.join(d, s, 'pack.json'))
                      for x in from_pack(os.path.join(d, s))]
    for name, n in write(out, items):
        print(f'{name}: {n} competitions')


if __name__ == '__main__':
    main(sys.argv[1:])
