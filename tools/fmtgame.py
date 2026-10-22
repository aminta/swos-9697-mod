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
import fmtprose

W = 40
EXTRA = []      # [(world, contest id or None, {lang: title}, {lang: [lines]})] from readers other than the packs:
                # 4.0's from_build9697 (the 1996-97 base game, the worlds' generated European cups, with 4.0's names)
LANGS = ('it', 'en', 'fr', 'de')

T = {
    'it': dict(promedio=['GIU: ULTIMO PROMEDIO (3 STAGIONI)', 'E ULTIMO DELLA CLASSIFICA ANNUALE;', 'PARI: SPAREGGIO IN CAMPO NEUTRO'], po_kind={'promotion': 'PLAY-OFF PROMOZIONE', 'europe': 'PLAY-OFF EUROPEO', 'placement': 'SPAREGGIO', 'playout': 'PLAY-OUT', 'title': 'PLAY-OFF SCUDETTO'}, better='IN PARITA PASSA LA MEGLIO PIAZZATA', et_better='SUPPLEMENTARI, POI LA MEGLIO PIAZZATA', gap='NON SI GIOCA SE C SONO {n}+ PUNTI DI DISTACCO', same='NON SI GIOCA SE E LA STESSA SQUADRA', seeds='TESTE DI SERIE {a}-{b} DELLE FASI', win_to='LA VINCENTE IN {d}', ita=['PLAY-OFF B: 3A-8A, PLAY-OUT: 16A-17A', 'PLAY-OFF C A 28 SQUADRE: 4A PROMOSSA'],
               teams='{n} SQUADRE', clubs='{n} SQUADRE', rr={1: 'GIRONE DI SOLA ANDATA', 2: 'ANDATA E RITORNO', 3: 'TRE GIRONI',
                                        4: 'QUATTRO GIRONI'},
               days='{n} GIORNATE', rest='UNA SQUADRA RIPOSA OGNI GIORNATA', pts='VITTORIA {w} PUNTI, PAREGGIO 1',
               up='PROMOSSE: {n}', down='RETROCESSE: {n}', none_down='NESSUNA RETROCESSIONE',
               ko='{n} SQUADRE A ELIMINAZIONE DIRETTA', real_cup='COPPA VERA: {n} SQUADRE', real_in='INGRESSI: ', in_game='NEL GIOCO: ', rn=lambda k: {0: 'PRELIM.', 64: 'TRENTADUESIMI', 32: 'SEDICESIMI', 16: 'OTTAVI', 8: 'QUARTI', 4: 'SEMIFINALI'}.get(k, f'{k}. TURNO'), byes='{n} ESENTI FINO AL 2. TURNO',
               r={'single': 'GARA UNICA, IN PARITA RIGORI', 'single_et': 'GARA UNICA, SUPPLEMENTARI E RIGORI',
                  'two_legs': 'ANDATA E RITORNO, GOL IN TRASFERTA', 'single_replay': 'GARA UNICA, IN PARITA RIPETIZIONE',
                  'two_legs_pens': 'ANDATA E RITORNO, POI RIGORI', 'two_legs_replay': 'ANDATA E RITORNO, IN PARITA SPAREGGIO'},
               rk='TURNI {a}-{b}: ', r1='TURNO {a}: ', final='FINALE: ', real='PRIMO TURNO COME NEL SORTEGGIO VERO',
               gen='SORTEGGIO DEL GIOCO', groups='{k} GIRONI PARALLELI DA {s}', split='DOPO {a} GIORNATE:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: NIENT ALTRO', half=', PUNTI DIMEZZATI', reset=', DA 0 PUNTI',
               po='{name}: {who}', third='FINALE 3. POSTO', ord=lambda n: f'{n}A'),
    'en': dict(promedio=['DOWN: THE LAST 3-SEASON PROMEDIO', 'AND THE LAST OF THE ANNUAL TABLE;', 'LEVEL: A PLAY-OFF, NEUTRAL GROUND'], po_kind={'promotion': 'PROMOTION PLAY-OFF', 'europe': 'EUROPEAN PLAY-OFF', 'placement': 'PLACEMENT PLAY-OFF', 'playout': 'PLAY-OUT', 'title': 'TITLE PLAY-OFF'}, better='LEVEL: THE BETTER PLACED GOES THROUGH', et_better='EXTRA TIME, THEN THE BETTER PLACED', gap='NOT PLAYED WITH A {n}+ POINT GAP', same='NOT PLAYED IF ONE CLUB IS ON BOTH SIDES', seeds="SEEDS {a}-{b} OF THE SEASON'S ROUNDS", win_to='THE WINNER TO {d}', ita=['SERIE B PLAY-OFF 3RD-8TH, PLAY-OUT 16-17', 'SERIE C PLAY-OFF OF 28 CLUBS: 4TH UP'],
               teams='{n} TEAMS', clubs='{n} CLUBS', rr={1: 'SINGLE ROUND ROBIN', 2: 'HOME AND AWAY', 3: 'TRIPLE ROUND ROBIN',
                                      4: 'QUADRUPLE ROUND ROBIN'},
               days='{n} MATCHDAYS', rest='ONE CLUB RESTS EACH MATCHDAY', pts='WIN {w} POINTS, DRAW 1',
               up='PROMOTED: {n}', down='RELEGATED: {n}', none_down='NO RELEGATION',
               ko='{n} CLUBS, KNOCKOUT', real_cup='REAL CUP: {n} CLUBS', real_in='ENTERING: ', in_game='IN THE GAME: ', rn=lambda k: {0: 'PRELIM.', 64: 'LAST 64', 32: 'LAST 32', 16: 'LAST 16', 8: 'QF', 4: 'SF'}.get(k, f'ROUND {k}'), byes='{n} BYES TO ROUND 2',
               r={'single': 'SINGLE MATCH, A DRAW: PENALTIES', 'single_et': 'SINGLE MATCH, EXTRA TIME, PENALTIES',
                  'two_legs': 'TWO LEGS, AWAY GOALS', 'single_replay': 'SINGLE MATCH, A DRAW: REPLAY',
                  'two_legs_pens': 'TWO LEGS, THEN PENALTIES', 'two_legs_replay': 'TWO LEGS, LEVEL: A REPLAY'},
               rk='ROUNDS {a}-{b}: ', r1='ROUND {a}: ', final='FINAL: ', real='ROUND 1 AS REALLY DRAWN',
               gen='DRAWN BY THE GAME', groups='{k} PARALLEL GROUPS OF {s}', split='AFTER {a} MATCHDAYS:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: NO MORE MATCHES', half=', POINTS HALVED', reset=', FROM 0 POINTS',
               po='{name}: {who}', third='THIRD PLACE MATCH', ord=lambda n: f'{n}{complist._sfx(n).upper()}'),
    'fr': dict(promedio=['DESCENTE: DERNIER PROMEDIO (3 ANS)', 'ET DERNIER DU CLASSEMENT ANNUEL;', 'EGALITE: BARRAGE, TERRAIN NEUTRE'], po_kind={'promotion': 'BARRAGES DE MONTEE', 'europe': 'BARRAGES EUROPEENS', 'placement': 'BARRAGES DE CLASSEMENT', 'playout': 'BARRAGES DE MAINTIEN', 'title': 'PLAY-OFF DU TITRE'}, better='NUL: LE MIEUX CLASSE PASSE', et_better='PROLONGATION, PUIS LE MIEUX CLASSE', gap='PAS JOUE AVEC {n}+ POINTS D ECART', same='PAS JOUE SI LE MEME CLUB DES DEUX COTES', seeds='TETES DE SERIE {a}-{b} DES PHASES', win_to='LE VAINQUEUR EN {d}', ita=['BARRAGES SERIE B 3E-8E, MAINTIEN 16E-17E', 'BARRAGES SERIE C A 28 CLUBS: 4E PROMU'],
               teams='{n} EQUIPES', clubs='{n} CLUBS', rr={1: 'MATCHS ALLER', 2: 'MATCHS ALLER ET RETOUR', 3: 'TROIS TOURS',
                                      4: 'QUATRE TOURS'},
               days='{n} JOURNEES', rest='UN CLUB AU REPOS A CHAQUE JOURNEE', pts='VICTOIRE {w} POINTS, NUL 1',
               up='PROMUS: {n}', down='RELEGUES: {n}', none_down='PAS DE RELEGATION',
               ko='{n} CLUBS, ELIMINATION DIRECTE', real_cup='VRAIE COUPE: {n} CLUBS', real_in='ENTREES: ', in_game='DANS LE JEU: ', rn=lambda k: {0: 'PRELIM.', 64: '32ES', 32: '16ES', 16: '8ES', 8: 'QUARTS', 4: 'DEMIS'}.get(k, f'TOUR {k}'), byes='{n} EXEMPTS JUSQU AU 2E TOUR',
               r={'single': 'MATCH UNIQUE, NUL: TIRS AU BUT', 'single_et': 'MATCH UNIQUE, PROLONGATION, T.A.B.',
                  'two_legs': 'ALLER-RETOUR, BUTS A L EXTERIEUR', 'single_replay': 'MATCH UNIQUE, NUL: A REJOUER',
                  'two_legs_pens': 'ALLER-RETOUR, PUIS TIRS AU BUT', 'two_legs_replay': 'ALLER-RETOUR, EGALITE: A REJOUER'},
               rk='TOURS {a}-{b}: ', r1='TOUR {a}: ', final='FINALE: ', real='1ER TOUR COMME LE VRAI TIRAGE',
               gen='TIRAGE DU JEU', groups='{k} GROUPES PARALLELES DE {s}', split='APRES {a} JOURNEES:',
               grp='{a}-{b}: {rr}', grp0='{a}-{b}: PLUS DE MATCHS', half=', POINTS DIVISES PAR 2',
               reset=', A PARTIR DE 0 POINT', po='{name}: {who}', third='MATCH POUR LA 3E PLACE',
               ord=lambda n: f'{n}E'),
    'de': dict(promedio=['ABSTIEG: LETZTER PROMEDIO (3 SAISONS)', 'UND LETZTER DER JAHRESTABELLE;', 'GLEICH: ENTSCHEIDUNGSSPIEL, NEUTRAL'], po_kind={'promotion': 'AUFSTIEGSPLAYOFFS', 'europe': 'EUROPAPOKAL-PLAYOFFS', 'placement': 'PLATZIERUNGSSPIELE', 'playout': 'ABSTIEGSPLAYOFFS', 'title': 'MEISTER-PLAYOFFS'}, better='REMIS: DER BESSER PLATZIERTE', et_better='VERLAENGERUNG, DANN DER BESSER PLATZIERTE', gap='NICHT GESPIELT BEI {n}+ PUNKTEN ABSTAND', same='ENTFAELLT BEI GLEICHEM VEREIN', seeds='SETZPLAETZE {a}-{b} DER RUNDEN', win_to='DER SIEGER IN DIE {d}', ita=['SERIE B: PLAYOFFS 3.-8., PLAYOUT 16.-17.', 'SERIE C: PLAYOFFS MIT 28 VEREINEN: 4. AUF'],
               teams='{n} MANNSCHAFTEN', clubs='{n} VEREINE', rr={1: 'EINFACHRUNDE', 2: 'HIN- UND RUECKRUNDE', 3: 'DREI RUNDEN',
                                        4: 'VIER RUNDEN'},
               days='{n} SPIELTAGE', rest='JEDEN SPIELTAG HAT EIN VEREIN FREI', pts='SIEG {w} PUNKTE, REMIS 1',
               up='AUFSTEIGER: {n}', down='ABSTEIGER: {n}', none_down='KEIN ABSTIEG',
               ko='{n} VEREINE, K.-O.-SYSTEM', real_cup='ECHTER POKAL: {n} VEREINE', real_in='EINSTIEG: ', in_game='IM SPIEL: ', rn=lambda k: {0: 'QUALI', 64: '1/32', 32: '1/16', 16: 'ACHTELF.', 8: 'VIERTELF.', 4: 'HALBF.'}.get(k, f'RUNDE {k}'), byes='{n} FREILOSE BIS RUNDE 2',
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


PX = {' ': 3, "'": 2, '(': 3, ')': 3, ',': 2, '-': 4, '.': 2, '1': 2, ':': 2, ';': 3, 'I': 2}   # the small font's
PX_MAX = 298                    # widths (charset sprites: 6 px else); the FORMAT page's usable width (entries of 304)


def px(t):
    return sum(PX.get(c, 6) for c in t)


def wrap_px(text, w=PX_MAX):
    """wrap() by the small font's pixel width (and the line buffer's fmtpage.LINE_W - 1 characters)."""
    out = []
    for para in text.split('\n'):
        line = ''
        for word in para.split(' '):
            if not word:
                continue
            cand = f'{line} {word}' if line else word
            if px(cand) <= w and len(cand) < fmtpage.LINE_W:
                line = cand
            else:
                if line:
                    out.append(line)
                line = word
        out.append(line)
    return out


GAP = '\x00'                     # pages(): a paragraph break in prose (a blank line)


def pages(lines):
    """Pages of fmtpage.LINES lines from lines or from paragraphs (lists of wrapped lines): a paragraph is not split
    across two pages when it fits on one, and one ending with ':' (a heading) goes with the next."""
    n = fmtpage.LINES
    paras = [x if isinstance(x, list) else [x] for x in lines]
    glued = []
    for pa in paras:
        if glued and glued[-1] and glued[-1][-1].endswith(':') and len(glued[-1]) + len(pa) <= n:
            glued[-1] = glued[-1] + pa
        else:
            glued.append(list(pa))
    out, gap = [[]], False
    for pa in glued:
        if pa == [GAP]:                         # (prose: a blank line before the next paragraph, never at a page top)
            gap = bool(out[-1])
            continue
        if gap and out[-1] and len(out[-1]) + 1 + len(pa) <= n:
            out[-1].append('')
        elif out[-1] and len(out[-1]) + len(pa) + gap > n and len(pa) <= n:
            out.append([])
        gap = False
        for line in pa:
            if len(out[-1]) == n:
                out.append([])
            out[-1].append(line)
    return out


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
    fx = [st for st in ((div.get('split') or {}).get('stages') or []) if 'fixtures' in st]
    if fx:                                      # (a fixture-list league: Argentina's two tournaments of 16 days)
        days = sum(len(st['fixtures']) for st in fx)
        lines = [t['clubs'].format(n=n), t['days'].format(n=days)]
    else:
        lines = [f"{t['clubs'].format(n=n)}, {t['rr'].get(g, '')}", t['days'].format(n=days)]
    if n % 2 and rest_note and not fx:
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
    two = t['r']['two_legs'].split(',')[0]          # ('ANDATA E RITORNO': the level rule follows)
    if lvl == 'better':
        base = (two if legs == 2 else t['r']['single'].split(',')[0]) + ', ' + t['better']
    elif lvl == 'et_better':
        base = (two if legs == 2 else t['r']['single'].split(',')[0]) + ', ' + t['et_better']
    elif lvl == 'pens' and legs == 2:
        base = t['r']['two_legs_pens']
    return base


def po_text(po, names, t, lang):
    by = {}
    for e in po.get('entrants', []):
        if isinstance(e, list):
            by.setdefault(e[0], []).append(e[1])
    seeds = sorted(e['split_seed'] for e in po.get('entrants', []) if isinstance(e, dict) and 'split_seed' in e)
    who = [t['seeds'].format(a=seeds[0], b=seeds[-1])] if seeds else []
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
    if any(r.get('skip_if_same') for r in po['rounds']):
        out.append(t['same'])
    if po.get('kind') == 'promotion' and po.get('winner_div') is not None and names:
        out.append(t['win_to'].format(d=complist._nm(names[po['winner_div']], lang)))
    return out


RN = {'Qualifying Round': 0, 'Preliminary Round': 0, 'First Round': 1, 'Second Round': 2, 'Third Round': 3,
      'Fourth Round': 4, '5th round': 5, 'Round of 64': 64, 'Round of 32': 32, 'Round of 16': 16, 'Last 16': 16,
      'Quarter-Finals': 8, 'Semi-Finals': 4}


def cup_text(cp, t):
    real = cp.get('real') and len(cp['real']['rounds']) > 1   # (the real competition first, then the game's slice)
    lines = [t['real_cup'].format(n=cp['real']['clubs']),
             t['real_in'] + ', '.join(f"{t['rn'](RN[r['tm']]) if r['tm'] in RN else r['tm'].upper()} {r['new']}"
                                      for r in cp['real']['rounds'] if r['new'])] if real else []
    lines += [(t['in_game'] if real else '') + t['ko'].format(n=cp['clubs'])]
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


# the table colours (zones.py) and a league-phase top flight's European places (zones.eu_places), as the table shows them
ZT = {
    'it': dict(head='COLORI DELLA CLASSIFICA:', col=('AZZURRO', 'VERDE', 'BLU', 'ARANCIONE', 'GRIGIO'),
               why=dict(cc='COPPA DEI CAMPIONI', uefa='COPPA UEFA', up='PROMOZIONE DIRETTA', po_up='PLAY-OFF PROMOZIONE',
                        po_eu='PLAY-OFF EUROPEO', po_title='PLAY-OFF SCUDETTO', po_place='PLAY-OFF', po_down='SPAREGGIO SALVEZZA', out='PLAY-OUT', down='RETROCESSIONE DIRETTA',
                        cl='CHAMPIONS LEAGUE', el='EUROPA LEAGUE', conf='CONFERENCE LEAGUE', eu='COPPE EUROPEE'),
               eu='POSTI EUROPEI DAL RANKING UEFA DELLA FEDERAZIONE (ACCESS LIST UEFA): CLASSIFICA {y} PER LE COPPE {y2}, '
                  'RANKING VERO {r}:',
               cup='VINCITRICE DELLA COPPA: {c}', s2='DALLA STAGIONE DOPO: RANKING SIMULATO',
               eps='I 2 EUROPEAN PERFORMANCE SPOTS E I POSTI SPOSTATI PER I DETENTORI DEI TITOLI SI DECIDONO A FINE '
                   'STAGIONE: NON COLORATI IN ANTICIPO'),
    'en': dict(head='TABLE COLOURS:', col=('LIGHT BLUE', 'GREEN', 'DARK BLUE', 'ORANGE', 'GRAY'),
               why=dict(cc='CHAMPIONS CUP', uefa='UEFA CUP', up='PROMOTED', po_up='PROMOTION PLAY-OFF',
                        po_eu='EUROPEAN PLAY-OFF', po_title='TITLE PLAY-OFF', po_place='PLAY-OFFS', po_down='RELEGATION PLAY-OFF', out='PLAY-OUT', down='RELEGATED',
                        cl='CHAMPIONS LEAGUE', el='EUROPA LEAGUE', conf='CONFERENCE LEAGUE', eu='EUROPEAN CUPS'),
               eu='EUROPEAN PLACES BY THE ASSOCIATION UEFA RANKING (UEFA ACCESS LIST): THE {y} TABLE FOR THE {y2} CUPS, '
                  'REAL {r} RANKING:',
               cup='THE CUP WINNER: {c}', s2='FROM THE NEXT SEASON ON: SIMULATED RANKING',
               eps='THE 2 EUROPEAN PERFORMANCE SPOTS AND THE TITLE HOLDERS REBALANCING ARE DECIDED AT THE SEASON END, '
                   'NOT COLOURED IN ADVANCE'),
    'fr': dict(head='COULEURS DU CLASSEMENT:', col=('BLEU CLAIR', 'VERT', 'BLEU FONCE', 'ORANGE', 'GRIS'),
               why=dict(cc='COUPE DES CHAMPIONS', uefa='COUPE UEFA', up='MONTEE DIRECTE', po_up='BARRAGES DE MONTEE',
                        po_eu='BARRAGES EUROPEENS', po_title='PLAY-OFF DU TITRE', po_place='BARRAGES', po_down='BARRAGE DE MAINTIEN', out='BARRAGES DE MAINTIEN',
                        down='DESCENTE DIRECTE', cl='LIGUE DES CHAMPIONS', el='LIGUE EUROPA', conf='LIGUE CONFERENCE',
                        eu='COUPES D EUROPE'),
               eu='PLACES EUROPEENNES SELON LE CLASSEMENT UEFA DE L ASSOCIATION (LISTE D ACCES UEFA): CLASSEMENT {y} POUR '
                  'LES COUPES {y2}, CLASSEMENT UEFA REEL {r}:',
               cup='VAINQUEUR DE LA COUPE: {c}', s2='DES LA SAISON SUIVANTE: CLASSEMENT SIMULE',
               eps='LES 2 EUROPEAN PERFORMANCE SPOTS ET LE REEQUILIBRAGE DES TENANTS SONT DECIDES EN FIN DE SAISON: PAS '
                   'COLORES A L AVANCE'),
    'de': dict(head='FARBEN DER TABELLE:', col=('HELLBLAU', 'GRUEN', 'DUNKELBLAU', 'ORANGE', 'GRAU'),
               why=dict(cc='LANDESMEISTERPOKAL', uefa='UEFA-POKAL', up='DIREKTER AUFSTIEG', po_up='AUFSTIEGSPLAYOFFS',
                        po_eu='EUROPAPOKAL-PLAYOFFS', po_title='MEISTER-PLAYOFFS', po_place='PLAYOFFS', po_down='RELEGATION', out='ABSTIEGSPLAYOFFS',
                        down='DIREKTER ABSTIEG', cl='CHAMPIONS LEAGUE', el='EUROPA LEAGUE', conf='CONFERENCE LEAGUE',
                        eu='EUROPAPOKALE'),
               eu='EUROPAPOKALPLAETZE NACH DER UEFA-RANGLISTE DES VERBANDS (UEFA-ZUGANGSLISTE): TABELLE {y} FUER DIE '
                  'POKALE {y2}, ECHTE RANGLISTE {r}:',
               cup='POKALSIEGER: {c}', s2='AB DER NAECHSTEN SAISON: SIMULIERTE RANGLISTE',
               eps='DIE 2 EUROPEAN PERFORMANCE SPOTS UND DER AUSGLEICH FUER TITELVERTEIDIGER WERDEN AM SAISONENDE '
                   'ENTSCHIEDEN: NICHT IM VORAUS GEFAERBT'),
}
CONFED_NAMES = dict(lib='COPA LIBERTADORES', sud='COPA SUDAMERICANA', ccc='CONCACAF CHAMPIONS CUP',
                    acle='AFC CHAMPIONS LEAGUE ELITE', acl2='AFC CHAMPIONS LEAGUE TWO', cafcl='CAF CHAMPIONS LEAGUE',
                    cafcc='CAF CONFEDERATION CUP', ofc='OFC CHAMPIONS LEAGUE')
for _z in ZT.values():
    _z['why'].update(CONFED_NAMES)
for _l, (_w, _e) in {'it': ('FASE FINALE', 'IN OGNI GIRONE'), 'en': ('KNOCKOUT STAGE', 'IN EACH GROUP'),
                      'fr': ('PHASE FINALE', 'DANS CHAQUE GROUPE'), 'de': ('ENDRUNDE', 'IN JEDER GRUPPE')}.items():
    ZT[_l]['why']['po_grp'] = _w                    # 4.0 group headers: a zone's places by group place
    ZT[_l]['each'] = _e
CONFED_NOTES = {   # zones.continental_all's notes: leagues whose real places are not table positions
    'it': dict(annual='IN REALTA: CAMPEON DE LIGA E POSTI DALLA CLASSIFICA ANNUALE (STAT > CLASSIFICA GENERALE, CON QUESTI COLORI), OLTRE AI CAMPIONI DI APERTURA E CLAUSURA',
               split='IN REALTA: I CAMPIONI DI APERTURA E CLAUSURA, POI LA CLASSIFICA ANNUALE; QUI LA CLASSIFICA DEL GIOCO',
               final='IN REALTA: IL CAMPIONE DI UNA FINALE / DEI PLAY-OFF, POI LA CLASSIFICA ANNUALE; QUI LA CLASSIFICA DEL GIOCO'),
    'en': dict(annual='IN REALITY: THE CAMPEON DE LIGA AND THE PLACES BY THE ANNUAL TABLE (STAT > OVERALL TABLE, WITH THESE COLOURS), BESIDES THE APERTURA AND CLAUSURA CHAMPIONS',
               split='IN REALITY: THE APERTURA AND CLAUSURA CHAMPIONS, THEN THE ANNUAL TABLE; HERE THE GAME S TABLE',
               final='IN REALITY: THE CHAMPION OF A FINAL / THE PLAY-OFFS, THEN THE ANNUAL TABLE; HERE THE GAME S TABLE'),
    'fr': dict(annual='EN REALITE: LE CAMPEON DE LIGA ET LES PLACES PAR LE CLASSEMENT ANNUEL (STAT > CLASSEMENT GENERAL, AVEC CES COULEURS), OUTRE LES CHAMPIONS D OUVERTURE ET DE CLOTURE',
               split='EN REALITE: LES CHAMPIONS D OUVERTURE ET DE CLOTURE, PUIS LE CLASSEMENT ANNUEL; ICI LE CLASSEMENT DU JEU',
               final='EN REALITE: LE CHAMPION D UNE FINALE / DES PLAY-OFFS, PUIS LE CLASSEMENT ANNUEL; ICI LE CLASSEMENT DU JEU'),
    'de': dict(annual='IN WIRKLICHKEIT: DER CAMPEON DE LIGA UND DIE PLATZE NACH DER JAHRESTABELLE (STAT > GESAMTTABELLE, MIT DIESEN FARBEN), NEBEN DEN APERTURA- UND CLAUSURA-MEISTERN',
               split='IN WIRKLICHKEIT: DIE APERTURA- UND CLAUSURA-MEISTER, DANN DIE JAHRESTABELLE; HIER DIE TABELLE DES SPIELS',
               final='IN WIRKLICHKEIT: DER MEISTER EINES FINALES / DER PLAYOFFS, DANN DIE JAHRESTABELLE; HIER DIE TABELLE DES SPIELS'),
}
_ZCTX = {}


def _zctx(d=None, world=None):
    """zones.context over the build's packs (mkseason.ENABLED), keyed by real path; a career pack whose world is not
    among them (fmtgame.py run on a data dir, or a test build) gets its own world's context from its sibling packs
    (the world's root has world_cups: league phase, start year), so a world never falls back to the classic cups."""
    import zones
    if None not in _ZCTX:
        import mkseason
        dirs = [e if os.sep in e else os.path.join(mkseason.PACKS, e) for e in mkseason.ENABLED]
        metas, ranks = zones.context(dirs)
        _ZCTX[None] = (metas, {os.path.realpath(x): r for x, r in ranks.items()})
    metas, ranks = _ZCTX[None]
    if d is None or world is None or world in metas:
        return metas, ranks
    par = os.path.dirname(os.path.realpath(d))
    if par not in _ZCTX:
        sib = [os.path.join(par, x) for x in sorted(os.listdir(par)) if os.path.exists(os.path.join(par, x, 'pack.json'))]
        m2, r2 = zones.context(sib)
        _ZCTX[par] = ({**metas, **m2}, {**ranks, **{os.path.realpath(x): r for x, r in r2.items()}})
    return _ZCTX[par]


def zone_text(rw, t, lang, eu=None, confed=None):
    """The FORMAT lines of a table's colours: rw = [(first, last, colour, why)] (zones.pack_zones detail); eu =
    (places, cup winner's cup, season) of a league-phase top flight."""
    import zones
    z = ZT[lang]
    cols = (zones.LIGHT_BLUE, zones.GREEN, zones.DARK_BLUE, zones.ORANGE, zones.RED)
    ord_ = t['ord']
    def one(a, b, c, w):
        rng = ord_(a) if a == b else f'{ord_(a)}-{ord_(b)}'
        if w == 'po_grp':
            rng += ' ' + z['each']
        return f"{z['col'][cols.index(c)]} {rng}: {z['why'][w]}"
    rw = list(dict.fromkeys((a & 0x7F, b & 0x3F, c, w) if w == 'po_grp' else (a, b, c, w) for a, b, c, w in rw
                            if not w.endswith('/grp')))   # (a split league's group copies: the plain lines say it)
    merged = []
    for a, b, c, w in sorted(rw, key=lambda r: (r[3] == 'po_grp', r)):
        if merged and merged[-1][2:] == (c, w) and merged[-1][1] == a - 1:
            merged[-1] = (merged[-1][0], b, c, w)
        else:
            merged.append((a, b, c, w))
    lines = []
    if eu:
        places, cw, y = eu
        lines.append(z['eu'].format(y=f'{y}-{(y + 1) % 100:02d}', y2=f'{y + 1}-{(y + 2) % 100:02d}', r=y))   # (a table
        # shows the places of the next season's cups: uefacoef 131f04b, from the 5 seasons up to the year before)
        lines += [one(*x) for x in places]
        if cw:
            lines.append(z['cup'].format(c=z['why'][cw]))
        lines += [z['s2'], z['eps']]
    if merged:
        lines.append(z['head'])
        lines += [one(*x) for x in merged]
    for e in confed or []:                      # another confederation: the cup winner's place, the real rule
        if e.get('via') == 'cup':
            lines.append(z['cup'].format(c=z['why'][e['cup']]))
        elif e.get('note'):
            lines.append(CONFED_NOTES[lang][e['note']])
    return lines


TEXTS = T                                  # (from_pack may swap a world's two_legs text)
NOAWAY = {'it': 'ANDATA E RITORNO, SUPPL. E RIGORI', 'en': 'TWO LEGS, EXTRA TIME, PENALTIES',
          'fr': 'ALLER-RETOUR, PROLONGATION, TAB', 'de': 'HIN- UND RUECKSPIEL, VERL., ELFM.'}
_YEARS = {}


# the pages of the contests the game makes outside the packs' competitions: the worlds' European cups and the
# career club's qualifying tie (careerworld / uefaq), the packs' ko_playoffs (gplay), Italy's play-offs (dplay),
# the Brazilian state championships (statecup); texts as the release notes' rules
EX = {
    'it': dict(
        cupd=['TUTTE LE SQUADRE DI SERIE D, SUL TABELLONE VERO 2026-27: TURNO PRELIMINARE, PRIMO TURNO, POI FINO ALLA FINALE',
              'GARA UNICA, NIENTE SUPPLEMENTARI: IN PARITA RIGORI', 'SEMIFINALI E FINALE ANDATA E RITORNO, IN PARITA RIGORI (NIENTE GOL IN TRASFERTA)',
              'CAMPO SORTEGGIATO FINO AI TRENTADUESIMI, POI GIOCA IN CASA CHI ERA FUORI NEL TURNO PRIMA',
              'DALLA 2A STAGIONE LE NUOVE DELLA SERIE D GIOCANO IL TURNO PRELIMINARE'],
        lp=['{n} SQUADRE, FASE CAMPIONATO A CLASSIFICA UNICA', '4 FASCE DA 9: 8 PARTITE, 2 AVVERSARIE PER FASCIA, UNA IN CASA E UNA FUORI',
            'MAI UNA SQUADRA DELLA STESSA FEDERAZIONE, AL MASSIMO 2 DELLA STESSA'],
        lp6=['{n} SQUADRE, FASE CAMPIONATO A CLASSIFICA UNICA', '6 FASCE DA 6: 6 PARTITE, UNA AVVERSARIA PER FASCIA, 3 IN CASA E 3 FUORI',
             'MAI UNA SQUADRA DELLA STESSA FEDERAZIONE, AL MASSIMO 2 DELLA STESSA'],
        lp_ko=['1A-8A AGLI OTTAVI, 9A-24A AGLI SPAREGGI, 25A-36A FUORI',
               'SPAREGGI: 9/10 CONTRO 23/24, 11/12 CONTRO 21/22, 13/14 CONTRO 19/20, 15/16 CONTRO 17/18, RITORNO IN CASA DELLA TESTA DI SERIE',
               'OTTAVI, QUARTI E SEMIFINALI SU TABELLONE FISSO DAI PIAZZAMENTI',
               'ANDATA E RITORNO, IN PARITA SUPPLEMENTARI E RIGORI (NIENTE GOL IN TRASFERTA)', 'FINALE IN GARA UNICA',
               'A PARI PUNTI: DIFFERENZA RETI, GOL, GOL FUORI CASA, VITTORIE, VITTORIE FUORI, POI PUNTI, DIFFERENZA RETI E GOL DELLE AVVERSARIE, PUNTI DISCIPLINARI, COEFFICIENTE'],
        lp_q='PRIMA: TURNI PRELIMINARI DELL ACCESS LIST 2026-27 (PERCORSO CAMPIONI E PIAZZATE), LE ELIMINATE SCENDONO DI COPPA',
        q=['IL TURNO PRELIMINARE DELLA TUA SQUADRA', '2 SQUADRE, ANDATA E RITORNO, IN PARITA SUPPLEMENTARI E RIGORI (NIENTE GOL IN TRASFERTA)',
           '1. TURNO INIZIO LUGLIO, 2. FINE LUGLIO, 3. INIZIO AGOSTO, SPAREGGIO FINE AGOSTO',
           'TURNI E PERCORSI DELL ACCESS LIST UEFA 2026-27; CHI PERDE SCENDE NELLA COPPA SOTTO, COME DA REGOLAMENTO'],
        po_n='{n} SQUADRE', grp_po='GIRONE DA {n}, SOLA ANDATA', grp_po2='GIRONE DA {n}, ANDATA E RITORNO', series='AL MEGLIO DELLE 3 GARE',
        drawn='ACCOPPIAMENTI SORTEGGIATI', neutral='IN CAMPO NEUTRO',
        st_byes='{who} ESENTI, ENTRANO AL TURNO DOPO', st_down='RETROCESSE: {n}', 
        state='CAMPIONATO STATALE: {n} SQUADRE', st_grp='{g} GIRONI DA {s}, SOLA ANDATA', st_grp1='GIRONE UNICO DA {s}, SOLA ANDATA',
        st_cross=' (CONTRO LE SQUADRE DELL ALTRO GIRONE)', st_cross_n=' (CONTRO LE SQUADRE DEGLI ALTRI GIRONI)', st_grp2='POI {g} GIRONI DA {s}', st_ko='{n} SQUADRE: {r}',
        ita_b=['TERZA PROMOSSA DI SERIE B: 3A-8A', 'TURNO PRELIMINARE: 5A-8A E 6A-7A, GARA UNICA IN CASA DELLA MEGLIO PIAZZATA, SUPPLEMENTARI, POI LA MEGLIO PIAZZATA',
               'SEMIFINALI: 3A E 4A CONTRO LE VINCENTI, ANDATA E RITORNO, IN PARITA LA MEGLIO PIAZZATA',
               'FINALE: ANDATA E RITORNO, IN PARITA LA MEGLIO PIAZZATA; A PARI PUNTI IN CAMPIONATO SUPPLEMENTARI E RIGORI',
               'SE LA 3A HA PIU DI 14 PUNTI SULLA 4A SALE DIRETTAMENTE'],
        ita_out=['16A CONTRO 17A, ANDATA E RITORNO, ANDATA IN CASA DELLA 17A', 'IN PARITA RESTA LA 16A; A PARI PUNTI IN CAMPIONATO SUPPLEMENTARI E RIGORI',
                 'SE LA 16A HA PIU DI 4 PUNTI SULLA 17A NON SI GIOCA: LA 17A RETROCEDE'],
        ita_c=['28 SQUADRE: 2A-10A DEI 3 GIRONI E LA VINCITRICE DELLA COPPA ITALIA SERIE C; LA VINCENTE SALE IN SERIE B',
               'FASE DEI GIRONI: 5A-10A, 6A-9A, 7A-8A, GARA UNICA IN CASA DELLA MEGLIO PIAZZATA, IN PARITA LA MEGLIO PIAZZATA; POI CON LA 4A',
               'FASE NAZIONALE: 2 TURNI CON TESTE DI SERIE, ANDATA E RITORNO, IN PARITA LA TESTA DI SERIE',
               'FINAL FOUR: SORTEGGIO LIBERO, ANDATA E RITORNO, SUPPLEMENTARI E RIGORI']),
    'en': dict(
        cupd=['EVERY SERIE D CLUB, ON THE REAL 2026-27 BRACKET: PRELIMINARY ROUND, FIRST ROUND, THEN TO THE FINAL',
              'SINGLE MATCH, NO EXTRA TIME: LEVEL, PENALTIES', 'SEMI-FINALS AND FINAL OVER TWO LEGS, LEVEL: PENALTIES (NO AWAY GOALS)',
              'HOSTS DRAWN UP TO THE ROUND OF 64, THEN THE CLUB AWAY IN ITS PREVIOUS TIE HOSTS',
              'FROM SEASON 2 THE CLUBS NEW TO THE SERIE D PLAY THE PRELIMINARY ROUND'],
        lp=['{n} CLUBS, A LEAGUE PHASE WITH ONE TABLE', '4 POTS OF 9: 8 MATCHES, 2 OPPONENTS FROM EACH POT, ONE AT HOME AND ONE AWAY',
            'NEVER A CLUB OF THE SAME ASSOCIATION, AT MOST 2 FROM ONE'],
        lp6=['{n} CLUBS, A LEAGUE PHASE WITH ONE TABLE', '6 POTS OF 6: 6 MATCHES, ONE OPPONENT FROM EACH POT, 3 AT HOME AND 3 AWAY',
             'NEVER A CLUB OF THE SAME ASSOCIATION, AT MOST 2 FROM ONE'],
        lp_ko=['1ST-8TH TO THE ROUND OF 16, 9TH-24TH TO THE KNOCKOUT PLAY-OFFS, 25TH-36TH OUT',
               'PLAY-OFFS: 9/10 V 23/24, 11/12 V 21/22, 13/14 V 19/20, 15/16 V 17/18, THE SEEDED CLUB AT HOME IN THE 2ND LEG',
               'ROUND OF 16, QUARTER- AND SEMI-FINALS ON A BRACKET FIXED BY THE PLACES',
               'TWO LEGS, LEVEL: EXTRA TIME AND PENALTIES (NO AWAY GOALS)', 'SINGLE-MATCH FINAL',
               'LEVEL ON POINTS: GOAL DIFFERENCE, GOALS, AWAY GOALS, WINS, AWAY WINS, THEN THE OPPONENTS POINTS, GOAL DIFFERENCE AND GOALS, DISCIPLINARY POINTS, COEFFICIENT'],
        lp_q='BEFORE: THE QUALIFYING ROUNDS OF THE 2026-27 ACCESS LIST (CHAMPIONS AND LEAGUE PATHS), THE LOSERS DROP A CUP',
        q=['YOUR CLUB S QUALIFYING TIE', '2 CLUBS, TWO LEGS, LEVEL: EXTRA TIME AND PENALTIES (NO AWAY GOALS)',
           'ROUND 1 EARLY JULY, ROUND 2 LATE JULY, ROUND 3 EARLY AUGUST, PLAY-OFF LATE AUGUST',
           'ROUNDS AND PATHS OF THE UEFA 2026-27 ACCESS LIST; THE LOSERS DROP INTO THE CUP BELOW AS THE REGULATIONS SAY'],
        po_n='{n} CLUBS', grp_po='A GROUP OF {n}, SINGLE ROUND', grp_po2='A GROUP OF {n}, HOME AND AWAY', series='BEST OF 3 MATCHES',
        drawn='TIES DRAWN', neutral='AT A NEUTRAL GROUND',
        st_byes='{who} WITH A BYE TO THE NEXT ROUND', st_down='RELEGATED: {n}', 
        state='STATE CHAMPIONSHIP: {n} CLUBS', st_grp='{g} GROUPS OF {s}, SINGLE ROUND', st_grp1='ONE GROUP OF {s}, SINGLE ROUND',
        st_cross=' (AGAINST THE OTHER GROUP S CLUBS)', st_cross_n=' (AGAINST THE OTHER GROUPS CLUBS)', st_grp2='THEN {g} GROUPS OF {s}', st_ko='{n} CLUBS: {r}',
        ita_b=['SERIE B THIRD PROMOTED CLUB: 3RD-8TH', 'PRELIMINARY ROUND: 5TH V 8TH, 6TH V 7TH, SINGLE MATCH AT THE BETTER PLACED, EXTRA TIME, THEN THE BETTER PLACED',
               'SEMI-FINALS: 3RD AND 4TH V THE WINNERS, TWO LEGS, LEVEL: THE BETTER PLACED',
               'FINAL: TWO LEGS, LEVEL: THE BETTER PLACED; LEVEL ON LEAGUE POINTS: EXTRA TIME AND PENALTIES',
               'A 3RD MORE THAN 14 POINTS AHEAD OF THE 4TH GOES UP DIRECTLY'],
        ita_out=['16TH V 17TH, TWO LEGS, FIRST LEG AT THE 17TH', 'LEVEL: THE 16TH STAYS UP; LEVEL ON LEAGUE POINTS: EXTRA TIME AND PENALTIES',
                 'NOT PLAYED WHEN THE 16TH IS MORE THAN 4 POINTS AHEAD: THE 17TH GOES DOWN'],
        ita_c=['28 CLUBS: 2ND-10TH OF THE 3 GROUPS AND THE COPPA ITALIA SERIE C WINNER; THE WINNER GOES UP TO SERIE B',
               'GROUP PHASE: 5TH V 10TH, 6TH V 9TH, 7TH V 8TH, SINGLE MATCH AT THE BETTER PLACED, LEVEL: THE BETTER PLACED; THEN WITH THE 4TH',
               'NATIONAL PHASE: 2 SEEDED ROUNDS, TWO LEGS, LEVEL: THE SEED', 'FINAL FOUR: FREE DRAW, TWO LEGS, EXTRA TIME AND PENALTIES']),
    'fr': dict(
        cupd=['TOUS LES CLUBS DE SERIE D, SUR LE VRAI TABLEAU 2026-27: TOUR PRELIMINAIRE, PREMIER TOUR, PUIS JUSQU A LA FINALE',
              'UN MATCH, SANS PROLONGATION: EGALITE, TAB', 'DEMI-FINALES ET FINALE EN ALLER-RETOUR, EGALITE: TAB (PAS DE BUTS A L EXTERIEUR)',
              'TERRAIN TIRE AU SORT JUSQU AUX 32ES, PUIS RECOIT LE CLUB QUI JOUAIT A L EXTERIEUR AU TOUR PRECEDENT',
              'DES LA 2E SAISON LES NOUVEAUX DE SERIE D JOUENT LE TOUR PRELIMINAIRE'],
        lp=['{n} CLUBS, PHASE DE LIGUE A CLASSEMENT UNIQUE', '4 CHAPEAUX DE 9: 8 MATCHS, 2 ADVERSAIRES PAR CHAPEAU, UN A DOMICILE ET UN A L EXTERIEUR',
            'JAMAIS UN CLUB DE LA MEME ASSOCIATION, AU PLUS 2 D UNE MEME'],
        lp6=['{n} CLUBS, PHASE DE LIGUE A CLASSEMENT UNIQUE', '6 CHAPEAUX DE 6: 6 MATCHS, UN ADVERSAIRE PAR CHAPEAU, 3 A DOMICILE ET 3 A L EXTERIEUR',
             'JAMAIS UN CLUB DE LA MEME ASSOCIATION, AU PLUS 2 D UNE MEME'],
        lp_ko=['1ER-8E EN 8ES, 9E-24E EN BARRAGES, 25E-36E ELIMINES',
               'BARRAGES: 9/10 CONTRE 23/24, 11/12 CONTRE 21/22, 13/14 CONTRE 19/20, 15/16 CONTRE 17/18, RETOUR CHEZ LA TETE DE SERIE',
               '8ES, QUARTS ET DEMI-FINALES SUR UN TABLEAU FIXE PAR LES PLACES',
               'ALLER-RETOUR, EGALITE: PROLONGATION ET TAB (PAS DE BUTS A L EXTERIEUR)', 'FINALE SUR UN MATCH',
               'EGALITE DE POINTS: DIFFERENCE DE BUTS, BUTS, BUTS A L EXTERIEUR, VICTOIRES, VICTOIRES A L EXTERIEUR, PUIS POINTS, DIFFERENCE ET BUTS DES ADVERSAIRES, POINTS DISCIPLINAIRES, COEFFICIENT'],
        lp_q='AVANT: LES TOURS DE QUALIFICATION DE LA LISTE D ACCES 2026-27 (VOIES CHAMPIONS ET LIGUE), LES PERDANTS DESCENDENT D UNE COUPE',
        q=['LE TOUR DE QUALIFICATION DE VOTRE CLUB', '2 CLUBS, ALLER-RETOUR, EGALITE: PROLONGATION ET TAB (PAS DE BUTS A L EXTERIEUR)',
           '1ER TOUR DEBUT JUILLET, 2E FIN JUILLET, 3E DEBUT AOUT, BARRAGE FIN AOUT',
           'TOURS ET VOIES DE LA LISTE D ACCES UEFA 2026-27; LES PERDANTS DESCENDENT DANS LA COUPE INFERIEURE SELON LE REGLEMENT'],
        po_n='{n} CLUBS', grp_po='UN GROUPE DE {n}, MATCHS SIMPLES', grp_po2='UN GROUPE DE {n}, ALLER-RETOUR', series='AU MEILLEUR DES 3 MATCHS',
        drawn='AFFICHES TIREES AU SORT', neutral='SUR TERRAIN NEUTRE',
        st_byes='{who} EXEMPTES JUSQU AU TOUR SUIVANT', st_down='RELEGUES: {n}', 
        state='CHAMPIONNAT D ETAT: {n} CLUBS', st_grp='{g} GROUPES DE {s}, MATCHS SIMPLES', st_grp1='UN GROUPE DE {s}, MATCHS SIMPLES',
        st_cross=' (CONTRE LES CLUBS DE L AUTRE GROUPE)', st_cross_n=' (CONTRE LES CLUBS DES AUTRES GROUPES)', st_grp2='PUIS {g} GROUPES DE {s}', st_ko='{n} CLUBS: {r}',
        ita_b=['3E PROMU DE SERIE B: 3E-8E', 'TOUR PRELIMINAIRE: 5E-8E ET 6E-7E, UN MATCH CHEZ LE MIEUX CLASSE, PROLONGATION, PUIS LE MIEUX CLASSE',
               'DEMI-FINALES: 3E ET 4E CONTRE LES VAINQUEURS, ALLER-RETOUR, EGALITE: LE MIEUX CLASSE',
               'FINALE: ALLER-RETOUR, EGALITE: LE MIEUX CLASSE; A EGALITE DE POINTS EN CHAMPIONNAT PROLONGATION ET TAB',
               'UN 3E AVEC PLUS DE 14 POINTS D AVANCE SUR LE 4E MONTE DIRECTEMENT'],
        ita_out=['16E CONTRE 17E, ALLER-RETOUR, ALLER CHEZ LE 17E', 'EGALITE: LE 16E RESTE; A EGALITE DE POINTS EN CHAMPIONNAT PROLONGATION ET TAB',
                 'PAS JOUE SI LE 16E A PLUS DE 4 POINTS D AVANCE: LE 17E DESCEND'],
        ita_c=['28 CLUBS: 2E-10E DES 3 GROUPES ET LE VAINQUEUR DE LA COPPA ITALIA SERIE C; LE VAINQUEUR MONTE EN SERIE B',
               'PHASE DES GROUPES: 5E-10E, 6E-9E, 7E-8E, UN MATCH CHEZ LE MIEUX CLASSE, EGALITE: LE MIEUX CLASSE; PUIS AVEC LE 4E',
               'PHASE NATIONALE: 2 TOURS AVEC TETES DE SERIE, ALLER-RETOUR, EGALITE: LA TETE DE SERIE',
               'FINAL FOUR: TIRAGE LIBRE, ALLER-RETOUR, PROLONGATION ET TAB']),
    'de': dict(
        cupd=['ALLE VEREINE DER SERIE D, AUF DEM ECHTEN TABLEAU 2026-27: VORRUNDE, ERSTE RUNDE, DANN BIS ZUM FINALE',
              'EIN SPIEL, KEINE VERLAENGERUNG: GLEICHSTAND, ELFMETER', 'HALBFINALE UND FINALE MIT HIN- UND RUECKSPIEL, GLEICHSTAND: ELFMETER (KEINE AUSWAERTSTORE)',
              'HEIMRECHT BIS ZUR RUNDE DER LETZTEN 64 AUSGELOST, DANN HAT DER IN DER VORRUNDE AUSWAERTS SPIELENDE HEIMRECHT',
              'AB DER 2. SAISON SPIELEN DIE NEUEN DER SERIE D DIE VORRUNDE'],
        lp=['{n} VEREINE, LIGAPHASE MIT EINER TABELLE', '4 TOEPFE ZU 9: 8 SPIELE, 2 GEGNER AUS JEDEM TOPF, EINER DAHEIM UND EINER AUSWAERTS',
            'NIE EIN VEREIN DESSELBEN VERBANDS, HOECHSTENS 2 AUS EINEM'],
        lp6=['{n} VEREINE, LIGAPHASE MIT EINER TABELLE', '6 TOEPFE ZU 6: 6 SPIELE, EIN GEGNER AUS JEDEM TOPF, 3 DAHEIM UND 3 AUSWAERTS',
             'NIE EIN VEREIN DESSELBEN VERBANDS, HOECHSTENS 2 AUS EINEM'],
        lp_ko=['1.-8. INS ACHTELFINALE, 9.-24. IN DIE PLAYOFFS, 25.-36. RAUS',
               'PLAYOFFS: 9./10. GEGEN 23./24., 11./12. GEGEN 21./22., 13./14. GEGEN 19./20., 15./16. GEGEN 17./18., RUECKSPIEL BEIM GESETZTEN',
               'ACHTEL-, VIERTEL- UND HALBFINALE NACH EINEM FESTEN TABLEAU AUS DEN PLAETZEN',
               'HIN- UND RUECKSPIEL, GLEICHSTAND: VERLAENGERUNG UND ELFMETER (KEINE AUSWAERTSTORE)', 'FINALE IN EINEM SPIEL',
               'PUNKTGLEICH: TORDIFFERENZ, TORE, AUSWAERTSTORE, SIEGE, AUSWAERTSSIEGE, DANN PUNKTE, TORDIFFERENZ UND TORE DER GEGNER, DISZIPLINARPUNKTE, KOEFFIZIENT'],
        lp_q='DAVOR: DIE QUALIFIKATIONSRUNDEN DER ZUGANGSLISTE 2026-27 (MEISTER- UND LIGAWEG), DIE VERLIERER RUTSCHEN EINEN POKAL TIEFER',
        q=['DIE QUALIFIKATIONSRUNDE DEINES VEREINS', '2 VEREINE, HIN- UND RUECKSPIEL, GLEICHSTAND: VERLAENGERUNG UND ELFMETER (KEINE AUSWAERTSTORE)',
           '1. RUNDE ANFANG JULI, 2. ENDE JULI, 3. ANFANG AUGUST, PLAYOFF ENDE AUGUST',
           'RUNDEN UND WEGE DER UEFA-ZUGANGSLISTE 2026-27; DIE VERLIERER RUTSCHEN LAUT REGLEMENT IN DEN POKAL DARUNTER'],
        po_n='{n} VEREINE', grp_po='EINE GRUPPE ZU {n}, EINFACHE RUNDE', grp_po2='EINE GRUPPE ZU {n}, HIN UND RUECK', series='BEST OF 3',
        drawn='PAARUNGEN AUSGELOST', neutral='AUF NEUTRALEM PLATZ',
        st_byes='{who} MIT FREILOS IN DIE NAECHSTE RUNDE', st_down='ABSTEIGER: {n}', 
        state='STAATSMEISTERSCHAFT: {n} VEREINE', st_grp='{g} GRUPPEN ZU {s}, EINFACHE RUNDE', st_grp1='EINE GRUPPE ZU {s}, EINFACHE RUNDE',
        st_cross=' (GEGEN DIE VEREINE DER ANDEREN GRUPPE)', st_cross_n=' (GEGEN DIE VEREINE DER ANDEREN GRUPPEN)', st_grp2='DANN {g} GRUPPEN ZU {s}', st_ko='{n} VEREINE: {r}',
        ita_b=['DRITTER AUFSTEIGER DER SERIE B: 3.-8.', 'VORRUNDE: 5.-8. UND 6.-7., EIN SPIEL BEIM BESSER PLATZIERTEN, VERLAENGERUNG, DANN DER BESSER PLATZIERTE',
               'HALBFINALE: 3. UND 4. GEGEN DIE SIEGER, HIN- UND RUECKSPIEL, GLEICHSTAND: DER BESSER PLATZIERTE',
               'FINALE: HIN- UND RUECKSPIEL, GLEICHSTAND: DER BESSER PLATZIERTE; BEI GLEICHEN LIGAPUNKTEN VERLAENGERUNG UND ELFMETER',
               'EIN 3. MIT MEHR ALS 14 PUNKTEN VOR DEM 4. STEIGT DIREKT AUF'],
        ita_out=['16. GEGEN 17., HIN- UND RUECKSPIEL, HINSPIEL BEIM 17.', 'GLEICHSTAND: DER 16. BLEIBT; BEI GLEICHEN LIGAPUNKTEN VERLAENGERUNG UND ELFMETER',
                 'NICHT GESPIELT BEI MEHR ALS 4 PUNKTEN VORSPRUNG DES 16.: DER 17. STEIGT AB'],
        ita_c=['28 VEREINE: 2.-10. DER 3 GRUPPEN UND DER SIEGER DER COPPA ITALIA SERIE C; DER SIEGER STEIGT IN DIE SERIE B AUF',
               'GRUPPENPHASE: 5.-10., 6.-9., 7.-8., EIN SPIEL BEIM BESSER PLATZIERTEN, GLEICHSTAND: DER BESSER PLATZIERTE; DANN MIT DEM 4.',
               'NATIONALE PHASE: 2 RUNDEN MIT GESETZTEN, HIN- UND RUECKSPIEL, GLEICHSTAND: DER GESETZTE',
               'FINAL FOUR: FREIE AUSLOSUNG, HIN- UND RUECKSPIEL, VERLAENGERUNG UND ELFMETER']),
}
# the game's own names of the European cups (a classic world: the exe's strings), keyed as world_cups
GAME_CUPS = {'it': {'cc': 'COPPA CAMPIONI EUROPEA', 'cwc': 'COPPA D. COPPE EUROPEA', 'uefa': 'COPPA EUFA'},
             'en': {'cc': 'EUROPEAN CHAMPIONS CUP', 'cwc': 'EUROPEAN CUP-WINNERS CUP', 'uefa': 'EUFA CUP'},
             'fr': {'cc': "CPE D'EUROPE DES CHAMPS", 'cwc': "CPE D'EUR VAINQ. DE CPE", 'uefa': 'COUPE EUFA'},
             'de': {'cc': 'EUROPAPOKAL LANDESMEISTER', 'cwc': 'EUROPAPOKAL POKALSIEGER', 'uefa': 'EUFA-CUP'}}
CODES = {0x94: 'two_legs', 0x84: 'two_legs_pens', 0x14: 'single', 0x54: 'single_et'}


def world_items():
    """[(world, cid, titles, texts)] of the career worlds' European cups (mkseason.world_defs) and, in a league-phase
    world, the career club's qualifying tie (uefaq: 'PRELIM. ' + the cup, per language). Titles: '' + ' ' + the
    cup's long name, as the game writes a contest without a country."""
    import mkseason
    out = []
    for w in mkseason.world_defs():
        n, T = w['n'], (_noaway_texts() if w.get('year', 0) >= 2021 else TEXTS)
        for key, (rounds, clubs) in w['cups'].items():
            lp = rounds == __import__('careerworld').LP_ROUNDS
            names = w['cupnames'].get(key)
            titles = {lang: ' ' + (names[0] if names else GAME_CUPS[lang][key]) for lang in LANGS}
            texts = {}
            for lang in LANGS:
                e = EX[lang]
                if lp:
                    texts[lang] = [x.format(n=len(clubs)) for x in (e['lp6'] if key == 'uefa' else e['lp'])] + \
                        e['lp_ko'] + [e['lp_q']]
                else:
                    texts[lang] = dict(fmtprose.cup(dict(clubs=len(clubs), rounds=[CODES[b] for b in rounds]), lang), tail=[])
            out.append((n, None, titles, texts))
            out.append((n, None, {lang: t[1:] for lang, t in titles.items()}, texts))   # (careerworld w_pfx, 4.0:
            # a contest of a country with no name gets no '<country> ' prefix, no space either; the old key kept)
        if any(r == __import__('careerworld').LP_ROUNDS for r, _ in w['cups'].values()):
            import uefaq
            for cid, cup in zip(uefaq.QIDS, uefaq.CUPS):
                titles = {lang: ' ' + uefaq.NAMES[lang] + cup.decode() for lang in LANGS}
                out.append((n, cid, titles, {lang: list(EX[lang]['q']) for lang in LANGS}))
                out.append((n, cid, {lang: t[1:] for lang, t in titles.items()}, {lang: list(EX[lang]['q']) for lang in LANGS}))
    return out


CT_RN = {   # 4.0 other confederations' cups (conti.py formats): round names on their FORMAT page
    'it': dict(qual='TURNO DI QUALIFICAZIONE', q='TURNO PRELIMINARE {n}', first='PRIMO TURNO', pre='TURNO PRELIMINARE', r1='PRIMO TURNO',
               league='FASE CAMPIONATO', losers='PERDENTI', thirds='TERZE', groups='FASE A GIRONI', po='SPAREGGI', r16='OTTAVI',
               qf='QUARTI', sf='SEMIFINALI', final='FINALE'),
    'en': dict(qual='QUALIFYING STAGE', q='QUALIFYING ROUND {n}', first='FIRST ROUND', pre='PRELIMINARY ROUND', r1='FIRST ROUND',
               league='LEAGUE STAGE', losers='LOSERS', thirds='THIRDS', groups='GROUP STAGE', po='PLAY-OFFS', r16='ROUND OF 16',
               qf='QUARTER-FINALS', sf='SEMI-FINALS', final='FINAL'),
    'fr': dict(qual='PHASE DE QUALIFICATION', q='TOUR PRELIMINAIRE {n}', first='PREMIER TOUR', pre='TOUR PRELIMINAIRE', r1='PREMIER TOUR',
               league='PHASE DE LIGUE', losers='PERDANTS', thirds='TROISIEMES', groups='PHASE DE GROUPES', po='BARRAGES',
               r16='HUITIEMES', qf='QUARTS', sf='DEMI-FINALES', final='FINALE'),
    'de': dict(qual='QUALIFIKATION', q='QUALIFIKATIONSRUNDE {n}', first='ERSTE RUNDE', pre='VORRUNDE', r1='ERSTE RUNDE',
               league='LIGAPHASE', losers='VERLIERER', thirds='DRITTEN', groups='GRUPPENPHASE', po='PLAYOFFS', r16='ACHTELFINALE',
               qf='VIERTELFINALE', sf='HALBFINALE', final='FINALE'),
}
CT_TX = {
    'it': dict(two='ANDATA E RITORNO, POI RIGORI', one='GARA UNICA, RIGORI', one_et='GARA UNICA, SUPPLEMENTARI E RIGORI',
               neutral='IN CAMPO NEUTRO', groups='{g} GIRONI DA {s}, ANDATA E RITORNO; PASSANO LE PRIME DUE',
               noaway='NESSUNA REGOLA DEI GOL IN TRASFERTA', away='VALE LA REGOLA DEI GOL IN TRASFERTA',
               league='{c} SQUADRE IN {r} ZONE, {m} PARTITE CIASCUNA; PASSANO LE PRIME {q} DI OGNI ZONA', losers='I PERDENTI DEL {r} ALLA {c} ({to})',
               third='LE TERZE DEI GIRONI ALLA {c} ({to})', inn='ENTRANO DALLA {c}: {what}'),
    'en': dict(two='TWO LEGS, THEN PENALTIES', one='ONE MATCH, PENALTIES', one_et='ONE MATCH, EXTRA TIME AND PENALTIES',
               neutral='AT A NEUTRAL GROUND', groups='{g} GROUPS OF {s}, HOME AND AWAY; THE TOP TWO GO THROUGH',
               noaway='NO AWAY GOALS RULE', away='THE AWAY GOALS RULE APPLIES',
               league='{c} CLUBS IN {r} REGIONS, {m} MATCHES EACH; THE TOP {q} OF EACH REGION GO THROUGH', losers='THE {r} LOSERS GO TO THE {c} ({to})',
               third='THE GROUPS\' THIRDS GO TO THE {c} ({to})', inn='FROM THE {c}: {what}'),
    'fr': dict(two='ALLER-RETOUR, PUIS TIRS AU BUT', one='MATCH UNIQUE, TIRS AU BUT',
               one_et='MATCH UNIQUE, PROLONGATIONS ET TIRS AU BUT', neutral='SUR TERRAIN NEUTRE',
               groups='{g} GROUPES DE {s}, ALLER-RETOUR; LES DEUX PREMIERS QUALIFIES', noaway='PAS DE BUTS A L\'EXTERIEUR',
               away='LES BUTS A L\'EXTERIEUR COMPTENT DOUBLE',
               league='{c} CLUBS EN {r} ZONES, {m} MATCHS CHACUN; LES {q} PREMIERS DE CHAQUE ZONE QUALIFIES',
               losers='LES PERDANTS DU {r} EN {c} ({to})', third='LES TROISIEMES DES GROUPES EN {c} ({to})',
               inn='DE LA {c}: {what}'),
    'de': dict(two='HIN- UND RUECKSPIEL, DANN ELFMETER', one='EIN SPIEL, ELFMETER',
               one_et='EIN SPIEL, VERLAENGERUNG UND ELFMETER', neutral='AUF NEUTRALEM PLATZ',
               groups='{g} GRUPPEN ZU {s}, HIN UND RUECK; DIE ERSTEN ZWEI WEITER', noaway='KEINE AUSWAERTSTORREGEL',
               away='DIE AUSWAERTSTORREGEL GILT',
               league='{c} KLUBS IN {r} REGIONEN, JE {m} SPIELE; DIE ERSTEN {q} JEDER REGION WEITER',
               losers='DIE VERLIERER DER {r} IN DIE {c} ({to})', third='DIE GRUPPENDRITTEN IN DIE {c} ({to})',
               inn='AUS DER {c}: {what}'),
}


def conti_items():
    """[(world, cid, titles, texts)]: the FORMAT pages of the other confederations' cups (conti.py), in the World
    2026-27 world; titles as the game writes a contest without a country (' ' + the name, and without the space)."""
    import conti
    import mkseason
    worlds = {pk.world for pk in mkseason.packs() if pk.meta.get('id', '').startswith('world-2026-27-') and pk.world}
    if not worlds:
        return []
    n_world = min(worlds)
    out = []
    cups = {c['key']: c for conf in conti.ready() for c in conti._read(conf, 'format')['cups']}
    where = {c['key']: (conf, k) for conf in conti.ready() for k, c in enumerate(conti._read(conf, 'format')['cups'])}
    accs = {c['key']: c.get('access') for conf in conti.ready() for c in conti._read(conf, 'access')['cups']}
    gst = {k for conf in conti.ready() for g in ((conti._read(conf, 'guests') or {}).get('clubs') or [])
           for k in (g.get('access') or {})}
    import fmtprose
    assoc = {pk.meta['id'][len('world-2026-27-'):]: pk.meta for pk in mkseason.packs()
             if pk.meta.get('id', '').startswith('world-2026-27-')}
    aname = lambda lang, a: ((assoc.get(a) or {}).get('button_names') or {}).get(lang) or a.upper()

    def rname(lang, key):
        r = CT_RN[lang]
        return r['q'].format(n=key[1:]) if key[0] == 'q' and key[1:].isdigit() else r.get(key, key.upper())

    def cname(lang, key):
        c = cups.get(key)
        return (c['names'].get(lang) or c['names']['en'])[0].upper() if c else key.upper()
    for key, c in cups.items():
        titles, texts = {}, {}
        for lang in LANGS:
            x, lines = CT_TX[lang], []
            for rd in c['rounds']:
                if rd['kind'] == 'league_stage':
                    q = max((int(k.split('-')[1]) for k in (rd.get('out') or {}) if '-' in k), default=8)
                    lines.append(f"{rname(lang, rd['key'])}: " + x['league'].format(
                        c=rd.get('regions', 1) * rd.get('clubs_per_region', 0), r=rd.get('regions', 1),
                        m=rd.get('matches', 0), q=q))
                    continue
                if rd['kind'] == 'groups':
                    lines.append(f"{rname(lang, rd['key'])}: " + x['groups'].format(g=rd['groups'], s=rd['size']))
                    continue
                how = x['two'] if rd.get('legs', 2) == 2 else x['one_et'] if rd.get('level') == 'et_pens' else x['one']
                if rd.get('host') == 'neutral':
                    how += ' ' + x['neutral']
                lines.append(f"{rname(lang, rd['key'])}: {how}")
            lines.append(x['away'] if any(rd.get('level') == 'away_pens' for rd in c['rounds']) else x['noaway'])
            for rk, to in (c.get('losers') or {}).items():
                ck, tr = to.split(':')
                lines.append(x['losers'].format(r=rname(lang, rk), c=cname(lang, ck), to=rname(lang, tr)))
            for tr, what in (c.get('in') or {}).items():
                ck, rest = what.split(':', 1)
                tail = ' '.join(CT_RN[lang]['losers'] if w == 'losers' else CT_RN[lang]['thirds'] if w == '3rds'
                                else w.upper() for w in rest.split()[1:])
                lines.append(x['inn'].format(c=cname(lang, ck), what=f'{rname(lang, rest.split()[0])} {tail}') +
                             f' -> {rname(lang, tr)}')
            titles[lang] = ' ' + (c['names'].get(lang) or c['names']['en'])[0].upper()
            texts[lang] = {'prose': fmtprose.conti(c, accs.get(key), lang, lambda k, lang=lang: cname(lang, k),
                                                   lambda a, lang=lang: aname(lang, a), *where[key], key in gst),
                           'tail': []}                  # (4.0 plain prose; lines: the schema)
        out.append((n_world, None, titles, texts))
        out.append((n_world, None, {lang: s[1:] for lang, s in titles.items()}, texts))
    return out


def _noaway_texts():
    return {lang: dict(TEXTS[lang], r=dict(TEXTS[lang]['r'], two_legs=NOAWAY[lang])) for lang in TEXTS}


def po_page(po, names, t, lang):
    """A play-off contest's own page (gplay): who, the rounds (groups, series, draws, neutral grounds)."""
    e = EX[lang]
    lines = po_text(po, names, t, lang)
    ent = po.get('entrants', [])
    if ent and not any(isinstance(x, list) for x in ent):
        lines[0] = lines[0].rstrip(': ') + ': ' + e['po_n'].format(n=len(ent))
    rs = po.get('rounds', [])
    if any('group' in r or r.get('series') or r.get('pairing') == 'draw' or r.get('host') == 'neutral' for r in rs):
        lines = lines[:1]
        for i, r in enumerate(rs):
            if 'group' in r:
                g = r['group']
                lines.append(t['r1'].format(a=i + 1) + (e['grp_po2'] if g.get('rounds', 1) == 2 else e['grp_po']).format(
                    n=len(r.get('members', []))))
                continue
            s = _rule(r, t)
            if r.get('series'):
                s = e['series']
            if r.get('pairing') == 'draw':
                s += ', ' + e['drawn']
            if r.get('host') == 'neutral':
                s += ', ' + e['neutral']
            lines.append(t['r1'].format(a=i + 1) + s)
        if any(r.get('gap') for r in rs):
            lines.append(t['gap'].format(n=max(r.get('gap') or 0 for r in rs)))
    return lines


def _po_prose(po, names, lang):
    """po_page in prose (4.0): who plays it in a sentence, then its rounds' lines as sentences."""
    import fmtprose
    lines = po_page(po, names, T[lang], lang)
    who = fmtprose.po_who(po, names, lang, lambda n: complist._nm(n, lang))
    if not who:
        return lines
    return {'prose': [' '.join([who] + fmtprose.sentences(lines[1:]))], 'tail': []}


def state_text(c, t, lang):
    e = EX[lang]
    lines = [e['state'].format(n=len(c.get('clubs', [])))]
    first = True
    for st in c.get('stages', []):
        if st['type'] == 'groups':
            g, n = st.get('groups', 1), st['teams']
            if first:
                s = (e['st_grp1'].format(s=n) if g == 1 else e['st_grp'].format(g=g, s=n // g))
                if st.get('cross') and g > 1:
                    s += e['st_cross'] if g == 2 else e['st_cross_n']
            else:
                s = e['st_grp2'].format(g=g, s=n // g)
            lines.append(s)
        elif st['type'] == 'knockout':
            lines.append(e['st_ko'].format(n=st['teams'], r=t['r'][st.get('matches', 'single')]))
            if st.get('byes'):                  # ('1A' = the 1st of group A)
                one = (c.get('stages') or [{}])[0].get('groups', 1) == 1
                who = [t['ord'](int(b[:-1])) + ('' if one else ' ' + b[-1]) for b in st['byes']]
                lines.append(e['st_byes'].format(who=', '.join(who)))
        first = False
    lines.append(t['pts'].format(w=c.get('win_points', 3)))
    if c.get('relegated'):
        lines.append(e['st_down'].format(n=c['relegated']))
    return lines




def world_year(w, d=None):
    """A world's first year (its root pack's world_cups.start_year): from 2021-22 on, no away goals (careerworld
    w_noaway: the engine applies the same rule). d: a pack of that world (its siblings when not in the build)."""
    if not _YEARS:
        import mkseason
        for pk in mkseason.packs():
            if pk.world is not None and 'world_cups' in pk.meta:
                _YEARS[pk.world] = pk.meta['world_cups'].get('start_year', 0)
    if w not in _YEARS and d is not None:
        return _zctx(d, w)[0].get(w, {}).get('start_year', 0)
    return _YEARS.get(w, 0)


WN = {   # the SEASON WINNERS page (fmtpage / winners.py): page title, a title not decided yet, a 'title' league's table
    'it': dict(po='PLAYOFF', down='RETROCESSA', title='VINCITORI', tbp='DA GIOCARE', reg=' (STAGIONE REGOLARE)'),
    'en': dict(po='PLAYOFFS', down='RELEGATED', title='WINNERS', tbp='TO BE PLAYED', reg=' (REGULAR SEASON)'),
    'fr': dict(po='PLAY-OFFS', down='RELEGUE', title='VAINQUEURS', tbp='A JOUER', reg=' (SAISON REGULIERE)'),
    'de': dict(po='PLAYOFFS', down='ABSTEIGER', title='SIEGER', tbp='NOCH OFFEN', reg=' (HAUPTRUNDE)'),
}
WN_SKIP = ('promedio', 'playout', 'placement')   # (no single winner: the promedio's and a play-out's relegated, places)


def _stage_start(div, po):
    """A stage title's start: the league days before its split stage (the one whose 'then' builds it, its knockout:
    'build_after'), FFh when it has no stage of its own (the Trofeo: started once its knockout is built)."""
    sp = div.get('split') or {}
    stages = sp.get('stages') or ([sp] if sp else [])
    days = 0
    for st in stages:
        if po.get('build_after') and st.get('then') == po['build_after']:
            return days if days < 0xFF else 0xFF
        days += len(st.get('fixtures') or [])
    return 0xFF


def _po_divs(po):
    """The divisions a play-off's entrants come from."""
    out = set()
    for e in po.get('entrants') or []:
        if isinstance(e, list) and len(e) == 2:
            out.add(e[0])
        elif isinstance(e, dict) and ('div' in e or 'stage_place' in e or 'split_seed' in e):
            out.add(e.get('div', 0))
    return out


WN_TITLES = {   # official titles (data session, 2026-27): (country, ko_playoffs key) -> {lang: name}; the league line
    ('usa', 'mls_po'): {'*': 'MLS CUP'},                              # ((country, None): instead of '(regular season)')
    ('aus', 'finals'): {'it': 'CAMPIONE A-LEAGUE MEN', 'en': 'A-LEAGUE MEN CHAMPIONS', 'fr': 'CHAMPION A-LEAGUE MEN',
                        'de': 'MEISTER A-LEAGUE MEN'},
    ('can', 'cpl_po'): {'*': 'NORTH STAR CUP'},
    ('mlt', 'final_four'): {'it': 'CAMPIONE DI MALTA', 'en': 'MALTESE CHAMPIONS', 'fr': 'CHAMPION DE MALTE',
                            'de': 'MALTESISCHER MEISTER'},
    ('ita', 'poule_scudetto'): {'it': 'SCUDETTO SERIE D', 'en': 'SERIE D CHAMPIONS', 'fr': 'CHAMPION SERIE D',
                                'de': 'SERIE-D-MEISTER'},
    ('usa', None): {'*': "SUPPORTERS' SHIELD"},
    ('aus', None): {'it': 'PREMIERS A-LEAGUE', 'en': 'A-LEAGUE PREMIERS', 'fr': 'PREMIERS A-LEAGUE', 'de': 'PREMIERS A-LEAGUE'},
    ('can', None): {'*': 'CPL SHIELD'},
}


WN_SUBS = {   # intermediate official titles inside a play-off (data session): (country, key) -> [(global tie, names)]
    ('usa', 'mls_po'): [(14, {'it': 'CAMPIONE EASTERN CONFERENCE', 'en': 'EASTERN CONFERENCE CHAMPIONS',
                              'fr': 'CHAMPION CONFERENCE EST', 'de': 'MEISTER EASTERN CONFERENCE'}),
                        (15, {'it': 'CAMPIONE WESTERN CONFERENCE', 'en': 'WESTERN CONFERENCE CHAMPIONS',
                              'fr': 'CHAMPION CONFERENCE OUEST', 'de': 'MEISTER WESTERN CONFERENCE'})],
}


def _wn_title(cc, key, lang):
    t = WN_TITLES.get((cc, key))
    return {'*': [t.get(lang) or t['*']]} if t else None


def win_lines(comp, div, k, cc='', tfile=None):
    """The SEASON WINNERS page of division k of a league: {lang: [(title, source)]}, {} when it has no title beyond its
    table (the page's entry stays hidden). Sources (winners.py wn_src): 'L' the table's 1st once the league is over;
    'K' + pi (2 hex digits) the last tie's winner of play-off pi (gplay GP_ST.ko: the career club's, played);
    'D' + stage + pi + ss a stage title decided mid-season (GP_ST.dec[stage], pi its play-off), in progress once the
    league has played more than ss days (its stage started; FFh: once its knockout is built)."""
    pos = comp.get('ko_playoffs') or []
    lines = {lang: [] for lang in LANGS}
    title_po = False
    for pi, po in enumerate(pos if isinstance(pos, list) else []):
        divs = _po_divs(po)
        if po.get('kind') in WN_SKIP or not po.get('names') or k not in divs or pi > 0xFF:
            continue
        title_po |= po.get('kind') == 'title' and divs == {k}       # (its champion is not the table's 1st)
        st = po.get('stage') if po.get('kind') == 'stage_title' else None
        src = f'D{st}{pi:02X}{_stage_start(div, po):02X}' if st is not None and 0 <= st < 3 else f'K{pi:02X}'
        for lang in LANGS:
            own = _wn_title(cc, po.get('key'), lang)
            if own and po.get('kind') == 'title':           # (Davide: 'PLAYOFF - MLS CUP', the title it gives)
                own = {'*': [WN[lang]['po'] + ' - ' + own['*'][0]]}
            lines[lang].append((_wn_fit(own or po['names'], lang), src))
        for tie, nm in WN_SUBS.get((cc, po.get('key')), []):  # ('T' + pi + tie: after the champion, Davide)
            for lang in LANGS:
                lines[lang].append((_wn_fit({'*': [nm[lang]]}, lang), f'T{pi:02X}{tie:02X}'))
    par = comp.get('parallel')                  # dplay (pack 'playoffs': 'ita'): the Serie B play-off and play-out (its
    par = par[0] if isinstance(par, list) else par   # relegated club), a Serie C group's play-off ('P' + dplay's kind)
    if comp.get('playoffs') == 'ita' and par:
        import dplay
        po = [(dplay.NAMES[0], 'P1', ''), (dplay.NAMES[1], 'P2', 'down')] if k == par['upper'] else \
            [(dplay.NAMES[2], 'P3', '')] if par['first'] <= k < par['first'] + par['count'] else []
        for nm, src, tail in po:
            for lang in LANGS:
                lines[lang].append((_wn_fit({'*': [nm.decode()]}, lang, ' - ' + WN[lang][tail] if tail else ''), src))
    if not lines['it']:
        return {}
    sp = div.get('split')
    tabs = [st for st in ((sp.get('stages') or [sp]) if sp else []) if st.get('table') is not None]
    end = end_played(div)
    stages = (sp.get('stages') or [sp]) if sp else []
    days = sum(len(st.get('fixtures') or []) for st in stages)  # (a stage table's league: the season's match days)
    src = None
    if tabs and 0 < days < 256:                                 # its annual / last table, once the days are played
        src = f"S{2 if any(st.get('annual') for st in tabs) else tabs[-1]['table']}{days:02X}"
    elif not tabs and end is not None:
        src = f'L{end:02X}'
    src = src and src + f'{k:02X}'                              # (+ the division: 4.0.1's last season, WN_ST 'L')
    if src:
        for lang in LANGS:
            own = _wn_title(cc, None, lang) if title_po else None      # (the regular season's own title)
            lines[lang].insert(0, (_wn_fit(own, lang) if own else
                                   _wn_fit(div['name'], lang, WN[lang]['reg'] if title_po else ''), src))
    if tfile is not None and 0 <= tfile < 256:                  # 4.0.1: its key first for the last season's page (the
        for lang in LANGS:                                      # division the career club played in: WN_ST 'M')
            lines[lang].insert(0, ('', f'H{tfile:02X}{k:02X}'))
    return lines


def _wn_fit(names, lang, tail=''):
    """A title of the SEASON WINNERS page, 'title:' within the page's width (rule 1): the long name, else the short
    one, else the long one without the tail."""
    v = names.get(lang) or names.get('*') or next(iter(names.values()))
    v = v if isinstance(v, list) else [v]
    tries = [x + tail for x in v] + [v[-1]]
    for t in tries:
        t = ascii_up(t, lang)
        if px(t + ':') <= PX_MAX:
            return t
    raise ValueError(f'SEASON WINNERS: {v} does not fit ({lang})')


def end_played(div):
    """The matches the table's 1st has played once the league is over (the SEASON WINNERS page's 'L' source), None
    when not known: a fixture-list league its days, a split league the last stage's (from 0 if it resets) plus its
    first group's rounds, else (n - 1) x meetings."""
    n, g = div['clubs'], div['games']
    sp = div.get('split')
    stages = (sp.get('stages') or [sp]) if sp else []
    fx = [st for st in stages if 'fixtures' in st]
    if fx:                                      # (each club's matches in the lists: one count for all, else unknown)
        cnt = {}
        for st in fx:
            for day in st['fixtures']:
                for m in day:
                    for c in m[:2]:
                        cnt[c] = cnt.get(c, 0) + 1
        out = cnt.popitem()[1] if cnt and len(set(cnt.values())) == 1 else None
    elif stages:
        st = stages[-1]
        gr = (st.get('groups') or [{}])[0]
        a, b = gr.get('places', [1, 0])
        r = {'none': 0, 'single': 1, 'double': 2, 'triple': 3, 'quadruple': 4}[gr.get('rounds', 'single')]
        base = max([x['after'] for x in stages if x.get('reset')] or [0])   # (the figures from 0 at the last reset)
        out = st['after'] - base + (b - a) * r if n % 2 == 0 and a == 1 and b > a else None
    else:
        out = (n - 1) * g
    return out if out is not None and 0 < out < 256 else None


def from_pack(d):
    """[(world, contest id, {lang: title}, {lang: [lines]})] of one pack."""
    m = complist.load_pack(d)
    clubs = complist.csv.DictReader(open(os.path.join(d, 'clubs.csv'), encoding='utf-8')) \
        if os.path.exists(os.path.join(d, 'clubs.csv')) else []
    clubs = [dict(r, file=r.get('file') or 'league', division=r.get('division') or '0') for r in clubs]
    tp = os.path.join(d, 'ties.csv')
    ties = list(complist.csv.DictReader(open(tp, encoding='utf-8'))) if os.path.exists(tp) else []
    bn = m.get('button_names') or {}
    T = TEXTS
    if m.get('world') is not None and world_year(m['world'], d) >= 2021:   # (no away goals: the round's ET / penalties)
        T = {lang: dict(TEXTS[lang], r=dict(TEXTS[lang]['r'], two_legs=NOAWAY[lang])) for lang in TEXTS}
    world = m.get('world', 0) if m.get('kind') == 'career' else 0
    import zones
    metas, ranks = _zctx(d, m.get('world', 0) if m.get('kind') == 'career' else None)
    rank = ranks.get(os.path.realpath(d))
    lp = zones._lp_world(metas, m.get('world', 0) if m.get('kind') == 'career' else 0)
    zdet = {lang: {} for lang in LANGS}
    for lang in LANGS:
        zones.pack_zones(d, lang, lp, rank, zdet[lang])
    out = []
    for ci, comp in enumerate(m.get('competitions', [])):
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
                    eu = None
                    if lp and rank and lv is lg['levels'][0]:
                        places, cw = zones.eu_places(rank)
                        eu = (places, cw, metas.get(m.get('world', 0), {}).get('start_year', 0))
                    for lang in LANGS:
                        nm = complist._nm(div['name'], lang)
                        titles[lang] = title(lang, nm)
                        low = (lg['closed'] or lv is lg['levels'][-1]) and not any(
                            po.get('kind') == 'promedio' for po in comp.get('ko_playoffs') or [])
                        sch = league_text(div, win, T[lang], lg['names'], lang, low) + \
                            (T[lang]['ita'] if lg['special'] and k == min(1, len(lg['names']) - 1) else []) + \
                            zone_text(zdet[lang].get((ci, k), []), T[lang], lang, eu,
                                      zones.continental_all(m) if lv is lg['levels'][0] and not m.get('europe_places') else None)
                        import fmtprose             # 4.0: the prose (the schematic lines' tail: the colours)
                        h = ZT[lang]['head']
                        tail = sch[sch.index(h):] if h in sch else [x for x in sch if x.startswith(ZT[lang]['eu'].split('{')[0][:30])]
                        pos_ = comp.get('ko_playoffs') or []
                        texts[lang] = {'prose': fmtprose.league(div, k, lg, win, lang, pos_ if isinstance(pos_, list) else [],
                                                                low, lambda x, lang=lang: complist._nm(x, lang),
                                                                ((comp.get('divisions') or [comp])[k] if k < len(comp.get('divisions') or [comp])
                                                                 else {}).get('real_down')) +
                                       (T[lang]['ita'] if lg['special'] and k == min(1, len(lg['names']) - 1) else []),
                                       'tail': sch[sch.index(next(x for x in sch if x.startswith(ZT[lang]['eu'].split('{')[0][:30]))):]
                                       if any(x.startswith(ZT[lang]['eu'].split('{')[0][:30]) for x in sch) else tail}
                    out.append((world, cid, titles, texts))
                    wl = win_lines(comp, div, k, (m.get('id') or '').rsplit('-', 1)[-1],
                                   ((m.get('files') or {}).get(comp.get('clubs')) or {}).get('file'))
                    if wl:
                        out.append((world, cid, titles, {'win': wl}))
                    k += 1
        elif comp['type'] == 'cup':
            side = os.path.join(d, 'complist.json')     # (the converter's facts: the real cup as TM lists it)
            info = (json.load(open(side)) if os.path.exists(side) else {}).get(comp['key'], {})
            cp = complist._cup(comp, ties, 'cup', info if comp['key'] == 'cup' else {})
            titles = {lang: title(lang, complist._nm(comp['names'], lang)) for lang in LANGS}
            out.append((world, cid, titles, {lang: dict(fmtprose.cup(cp, lang), tail=[]) for lang in LANGS}))
        elif comp['type'] == 'tourney':
            titles = {lang: title(lang, complist._nm(comp['names'], lang)) for lang in LANGS}
            out.append((world, cid, titles, {lang: tourney_text(comp, T[lang]) for lang in LANGS}))
        elif comp['type'] == 'state':           # (statecup: a Brazilian state championship)
            titles = {lang: title(lang, complist._nm(comp['names'], lang)) for lang in LANGS}
            out.append((world, cid, titles, {lang: dict(prose=fmtprose.state(comp, lang), tail=[]) for lang in LANGS}))
            out.append((world, cid, titles, {'win': {lang: [(_wn_fit(comp['names'], lang), 'C')] for lang in LANGS}}))
        if comp['type'] != 'league':
            continue
        lg = complist._league(comp, clubs)
        pos = comp.get('ko_playoffs') or []
        for po in pos if isinstance(pos, list) else []:          # gplay: each play-off is a contest of its own
            if po.get('kind') == 'promedio' or not po.get('names'):
                continue
            titles = {lang: title(lang, complist._nm(po['names'], lang)) for lang in LANGS}
            out.append((world, None, titles, {lang: _po_prose(po, lg['names'], lang) for lang in LANGS}))
        if comp.get('cup_d'):                   # cupd: the Coppa Italia Serie D
            nm = comp['cup_d'].get('names') or {'*': ['COPPA ITALIA SERIE D', 'COPPA IT SERIE D']}
            titles = {lang: title(lang, complist._nm(nm, lang)) for lang in LANGS}
            out.append((world, None, titles, {lang: list(EX[lang]['cupd']) for lang in LANGS}))
        if comp.get('playoffs') == 'ita':       # dplay: Serie B play-off / play-out, Serie C play-off
            import dplay
            for nm, k in zip(dplay.NAMES, ('ita_b', 'ita_out', 'ita_c')):
                titles = {lang: title(lang, nm.decode()) for lang in LANGS}
                out.append((world, None, titles, {lang: list(EX[lang][k]) for lang in LANGS}))
    return out


def write(out_dir, items):
    """FMTxx[world].DAT per language and world from [(world, cid, titles, texts)]."""
    by, keys, wins = {}, {}, {}
    for world, cid, titles, texts in items:
        if 'win' in texts:                      # (the SEASON WINNERS page's lines: the file's WIN entries)
            for lang in LANGS:
                key = titles[lang][:fmtpage.NAME - 1]
                lst = wins.setdefault((lang, world), [])
                if all(k_ != key for _, k_, _ in lst):
                    lst.append((cid, key, texts['win'][lang]))
            continue
        for lang in LANGS:
            lines = texts[lang]
            import fmtprose                     # 4.0: every competition's text in plain prose (the colours' lines kept)
            h = ZT[lang]['head']
            if isinstance(lines, dict):
                prose, tail = lines['prose'], lines['tail']
            else:
                tail = lines[lines.index(h):] if h in lines else []
                prose = fmtprose.sentences(lines[:len(lines) - len(tail)])
            hand = fmtprose.text(world, titles['it'], lang)   # (hand texts keyed by the Italian title)
            if hand and isinstance(lines, dict) and lines.get('real'):   # a national cup's real cup first, then the hand text
                hand = [lines['real']] + hand
            if hand and not isinstance(lines, dict):      # a national cup's real draw first (complist: real_cup / real_in)
                rc = [x for x in lines if x.startswith(TEXTS[lang]['real_cup'].split('{')[0]) or
                      x.startswith(TEXTS[lang]['real_in'])]
                if rc:
                    hand = fmtprose.sentences(rc) + hand
            prose = hand or prose
            if prose:
                if hand:                        # (a hand text tells the real rule itself)
                    tail = [x for x in tail if x not in CONFED_NOTES[lang].values()]
                body = []
                for para in prose:
                    body += [wrap_px(ascii_up(para, lang)), [GAP]]
                tl = [wrap_px(ascii_up(t, lang)) for t in tail]
                if tl:
                    body += tl                      # (the colours' lines fill the page and go on: not prose)
                elif body:
                    body.pop()                      # (no trailing paragraph break)
            else:
                body = [wrap_px(ascii_up(line, lang)) for line in lines]      # (paragraphs: pages())
            key = titles[lang][:fmtpage.NAME - 1]
            k = (lang, world, key)
            if k in keys:                       # the same title twice (two divisions with one name): one page,
                keys[k].extend([['']] + body)     # both descriptions
                continue
            keys[k] = body
            by.setdefault((lang, world), []).append((cid, key, None))
    by = {lw: [(cid, key, pages(keys[(lw[0], lw[1], key)])) for cid, key, _ in lst] for lw, lst in by.items()}
    files = []
    for (lang, world), lst in sorted(by.items()):
        name = f'FMT{lang.upper()}{world or ""}.DAT'
        fmtpage.build(os.path.join(out_dir, name), lst, wins.get((lang, world), []))
        files.append((name, len(lst)))
    return files


def file_names(pack_dirs):
    """The FMTxx[world].DAT names write() makes for these packs (mkpatcher: the files to ship)."""
    worlds = sorted({w for d in pack_dirs for w, *_ in from_pack(d)} | {w for w, *_ in EXTRA})
    return [f'FMT{lang.upper()}{w or ""}.DAT' for w in worlds for lang in LANGS]


def main(argv):
    """The packs given (pack dirs or dirs of packs) are the build (mkseason.ENABLED): their worlds' league phase, start
    year, European cups and qualifying ties as in patch.py's build."""
    out, dirs = argv[0], argv[1:]
    pk = []
    for d in dirs:
        if os.path.exists(os.path.join(d, 'pack.json')):
            pk.append(d)
        else:
            pk += [os.path.join(d, s) for s in sorted(os.listdir(d)) if os.path.exists(os.path.join(d, s, 'pack.json'))]
    import mkseason
    mkseason.ENABLED = [os.path.abspath(d) for d in pk if os.path.basename(d.rstrip(os.sep)) != mkseason.NATIONAL]
    items = [x for d in pk for x in from_pack(d)]
    try:
        items += world_items()
    except Exception as e:                      # (packs that are no full world: no European cups)
        print(f'(no European cups: {e})')
    for name, n in write(out, items):
        print(f'{name}: {n} competitions')


if __name__ == '__main__':
    main(sys.argv[1:])
