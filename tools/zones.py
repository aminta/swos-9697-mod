"""Zone colours in the league tables (4.0; Davide's palette): each row's background tells its end-of-season zone.

    light blue 0Dh  the best way up: Champions League / Champions Cup places, or direct promotion
    green      0Eh  the second way up: Europa League / UEFA Cup places, a promotion or European play-off
    dark blue  08h  the third European cup: Conference League places (league-phase worlds)
    orange     0Ch  play-out / relegation play-off
    gray       02h  direct relegation (red was the plain rows' own computer-club name colour: Davide)
    the game's own alternating rows (7 / 9) elsewhere; computer clubs' names in the row colour (as lp36), so the
    human club's name box keeps its player / coach colour.

Hook: the table row loop's `mov ax, [dseg_11F41C]` at cseg_49B65 (the row colour D3 is final there; lp36.py's lp_col
uses the same site for its league phase: then zn_col calls lp_col first and skips lp36's own tables). The table is
found by the career's world (someLeaguesTable[1845] in a career, else 0) and the title the game shows (DIY+4, as
fmtpage.py), cached per table: one compare per row.

Zones from the packs (mkseason.ENABLED):
- top level: europe_places. Classic worlds (the game's cseg_93974): the champion to the Champions Cup (cc), the next
  `uefa` clubs to the UEFA Cup (the Cup Winners' Cup is the cup winner's). League-phase worlds (careerworld QUAL_ASM):
  the top `cc` to the Champions League, the next `cwc - 1` to the Europa League (the cup winner takes one), the next
  `uefa` to the Conference League;
- promoted / relegated per division; ko_playoffs entrants (a promotion play-off: green for the lower division's
  clubs, orange for the upper one's; a European play-off green; a play-out orange); 'playoffs': 'ita' (dplay.py:
  Serie B 3-8 play-off, 16-17 play-out; each Serie C group 2-10 play-off).
"""
import json
import os
import re
import struct

import complist
import nasmcave

LIGHT_BLUE, GREEN, DARK_BLUE, ORANGE, RED = 0x0D, 0x0E, 0x08, 0x0C, 0x02   # RED: relegation, gray (Davide: red
                                                                         # was the computer clubs' own name colour)


def access_list():
    """uefaq.c's AL (the 2026/27 access list by association rank): {rank: [(round, code)]}; round < 8 Champions
    League, < 14 Europa League, else Conference League; code 0 the champion, 1 the cup winner, k the k-th place."""
    import re
    src = open(os.path.join(os.path.dirname(__file__), 'uefaq.c')).read()
    body = src[src.index('static const u8 AL[] = {'):]
    body = body[body.index('{') + 1:body.index('};')]
    v = [int(x) for x in re.findall(r'\d+', re.sub(r'/\*.*?\*/', '', body, flags=re.S))]
    out, i = {}, 0
    while v[i]:
        r, n = v[i], v[i + 1]
        out[r] = [(v[i + 2 + 2 * k], v[i + 3 + 2 * k]) for k in range(n)]
        i += 2 + 2 * n
    return out


def rank_colours(nranks=56):
    """[rank 1..nranks-1 (index rank - 1)] -> EU_PLACES colours of places 1..EU_PLACES (0 = none): the access list (the
    cup winner's place aside; the European Performance Spots are decided at the season end: not shown)."""
    out = bytearray()
    for r in range(1, nranks):
        col = [0] * EU_PLACES
        for rnd, code in access_list().get(r, []):
            if code == 1:
                continue
            place = 1 if code == 0 else code
            if place <= EU_PLACES:
                col[place - 1] = LIGHT_BLUE if rnd < 8 else GREEN if rnd < 14 else DARK_BLUE
        out += bytes(col)
    return bytes(out)


def lp_places(rank, cc):
    """[(place, colour)] of a league-phase world's top flight in season 1: the access list of its rank (the cup
    winner's place aside), the pack's own Champions League count when larger (the European Performance Spots)."""
    al = access_list().get(rank, [])
    comps = [r for r, code in sorted(((c if c else 1, r) for r, c in al if c != 1), key=lambda x: x[0])
             for _ in [0]]
    comps = [r for _, r in sorted((c if c else 1, r) for r, c in al if c != 1)]
    cols = [LIGHT_BLUE if r < 8 else GREEN if r < 14 else DARK_BLUE for r in comps]
    ncl = sum(1 for c in cols if c == LIGHT_BLUE)
    while ncl < cc:
        cols.insert(ncl, LIGHT_BLUE)
        ncl += 1
    return [(k + 1, c) for k, c in enumerate(cols)]
NAME = 41                       # the slot's name field (as fmtpage.NAME)
RANGES = 8
LEG = 6                         # legend boxes (the colours a table uses, in place order; 6 since rc12: NED's CL EL
                                # CONF P.OFF P.OUT RETR - the euro play-off's own P.OFF)
ENTRY = 1 + NAME + 1 + 3 * RANGES + 1 + 2 * LEG   # world, title, n, ranges, n legend, (colour, label) * LEG = 80
ENTRY_PAD = 96                  # (+GLEG: the group headers' legend, n + GLEG_N boxes, before LEGX)
ECODE = ENTRY + 2               # a league-phase top flight: its association's code (the league's team file, uefacoef)
EU_PLACES = 10                  # the access list's places looked at per rank (the top 9 + 1)
EFLAG = ENTRY                   # 1: a league-phase world's top flight (its European places: season 1 only); + 1 the
GLEG, GLEG_N = ENTRY + 3, 4     # year, + 2 ECODE; then the group headers' legend (at most 4 boxes: it ends at LEGX)
EU_SEASON1_ONLY = False         # (True: season-1 colours in season 1 only; False: every season from uc_rank, the
                                # ranking a year old that decides the next season's places, uefacoef 131f04b)
LEG_W, LEG_TXT = 30, 8
FILE = {'it': b'data/zonit', 'en': b'data/zonen', 'fr': b'data/zonfr', 'de': b'data/zonde'}          # a legend box's width (5 small-font characters), its text buffer
CONFED = {'lib': LIGHT_BLUE, 'sud': GREEN, 'ccc': LIGHT_BLUE, 'acle': LIGHT_BLUE, 'acl2': GREEN, 'cafcl': LIGHT_BLUE,
          'cafcc': GREEN, 'ofc': LIGHT_BLUE}   # the other confederations' club cups: the first light blue, the second green
CONFED_LAB = dict(lib='LIB', sud='SUD', ccc='CONC', acle='ACLE', acl2='ACL2', cafcl='CAFCL', cafcc='CAFCC', ofc='OFC')
# legend labels (<= 5 characters): top flight of a league-phase world, of a classic world, a lower division
LABELS = {
    'it': dict(next='PASSA', cl='CL', el='EL', conf='CONF', cc='CAMP', uefa='UEFA', up='PROM', po='P.OFF', out='P.OUT', down='RETR', **CONFED_LAB),
    'en': dict(next='NEXT', cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='UP', po='P.OFF', out='P.OUT', down='DOWN', **CONFED_LAB),
    'fr': dict(next='QUAL.', cl='LDC', el='LE', conf='LC', cc='C1', uefa='C3', up='MONT', po='BARR', out='MAINT', down='DESC', **CONFED_LAB),
    'de': dict(next='WEIT.', cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='AUF', po='AUF-R', out='ABS-R', down='AB', **CONFED_LAB),
}
KEYS = ('cl', 'el', 'conf', 'cc', 'uefa', 'up', 'po', 'out', 'down', 'lib', 'sud', 'ccc', 'acle', 'acl2', 'cafcl', 'cafcc', 'ofc',
        'next')
LEG_COLOUR = {}                 # (a legend box's colour code when not the zone's own: none - the Conference's
                                # dark blue is a plain box like the others, no inner frame: Davide 2026-10-22)


def _title(pk_meta, lang, name):
    bn = pk_meta.get('button_names') or {}
    return f"{bn.get(lang, pk_meta.get('button', ''))} {name}".upper()[:NAME - 1]


def _lp_world(meta_by_world, n):
    wc = meta_by_world.get(n, {})
    return any(wc.get(k, {}).get('format') == 'league_phase' for k in ('cc', 'cwc', 'uefa'))


def state_zones(c):
    """A state championship's first group stage: the places that go on to the next stage (its 'from' list, a
    knockout's byes = straight to a later round: light blue NEXT; the others green P.OFF), the relegated (one group:
    the last ones; several groups: not painted, the relegation runs on the overall table). The places are group
    places (the same in every group); size = the group size for several groups (zn_col counts places per group)."""
    st = c.get('stages') or []
    if not st or st[0]['type'] != 'groups':
        return None
    g = st[0].get('groups', 1)
    size = st[0]['teams'] // g
    nxt = [s for s in st[1:]]
    first = set()
    if nxt and nxt[0].get('from'):
        first = {int(x[:-1]) for x in nxt[0]['from']}
    elif nxt and nxt[0]['type'] == 'knockout':
        first = set(range(1, nxt[0]['teams'] // g + 1))
    byes = {int(x[:-1]) for s in nxt for x in (s.get('byes') or [])}   # (a knockout's byes: straight to the next round)
    rng, why = [], []
    for p in sorted(byes - first):
        rng.append((p, p, LIGHT_BLUE))
        why.append('next')
    for p in sorted(first):
        rng.append((p, p, GREEN))
        why.append('po_title')
    if g == 1 and c.get('relegated'):
        rng.append((size - c['relegated'] + 1, size, RED))
        why.append('down')
    rng, why = _merge(rng, why)
    return rng, why, (size if g > 1 else 0)


def _merge(rng, why):
    """Plain ranges of one colour and reason joined into runs of consecutive places (a play-off's entrants come one
    place each), in the order of their first appearance (the first matching range wins); group ranges kept after."""
    runs, order = {}, []
    for (a, z, c), w in zip(rng, why):
        if a & 0x80:
            continue
        if (c, w) not in runs:
            runs[(c, w)] = set()
            order.append((c, w))
        runs[(c, w)].update(range(a, z + 1))
    out, ow, seen = [], [], set()
    for c, w in order:
        ps = sorted(set(runs[(c, w)]) - seen)    # (places an earlier zone paints: never this one's)
        seen.update(runs[(c, w)])
        if not ps:
            continue
        s = ps[0]
        for k, p in enumerate(ps):
            if k + 1 == len(ps) or ps[k + 1] != p + 1:
                out.append((s, p, c))
                ow.append(w)
                if k + 1 < len(ps):
                    s = ps[k + 1]
    for r, w in zip(rng, why):
        if r[0] & 0x80:
            out.append(r)
            ow.append(w)
    return out, ow


LIGUILLA_ZONES = {'world-2026-27-mex'}    # packs whose tables colour their Liguilla places (P.OFF), not the
                                         # confederation's (Davide 2026-10-24: Liga MX + Liga de Expansion)


def pack_zones(d, lang, lp=False, rank=None, detail=None):
    """[(world, title, [(first, last, colour), ...])] of one pack's league divisions; detail (a dict): {(competition
    index, division index): [(first, last, colour, why)]} for the FORMAT page (fmtgame.py), why in WHY."""
    m = complist.load_pack(d)
    cl = os.path.join(d, 'clubs.csv')
    clubs = [dict(r, file=r.get('file') or 'league', division=r.get('division') or '0')
             for r in complist.csv.DictReader(open(cl, encoding='utf-8'))] if os.path.exists(cl) else []
    world = m.get('world', 0) if m.get('kind') == 'career' else 0
    out = []
    for ci, comp in enumerate(m.get('competitions', [])):
        if comp['type'] == 'state':                      # 4.0.1: a Brazilian state championship's group table
            sr = state_zones(comp)
            if sr:
                rng, why, size = sr
                out.append((world, _title(m, lang, complist._nm(comp['names'], lang)), rng[:RANGES], 'state', size,
                            [], why[:RANGES]))
            continue
        if comp['type'] != 'league':
            continue
        lg = complist._league(comp, clubs)
        divs = [dv for lv in lg['levels'] for dv in lv]
        top = set(id(dv) for dv in lg['levels'][0])
        po = comp.get('ko_playoffs') or []
        if isinstance(po, int):
            po = []
        for i, dv in enumerate(divs):
            n, rng, why = dv['clubs'], [], []
            if id(dv) in top:
                pl = m.get('europe_places', {})
                if not pl and continental(m):            # another confederation: its club cups' places
                    for e in continental(m):
                        rng.append((e['places'][0], e['places'][1], CONFED[e['cup']]))
                        why.append(e['cup'])
                elif lp:                                 # (run time from uc_rank unless EU_SEASON1_ONLY)
                    for place, col in (lp_places(rank, pl.get('cc', 0)) if rank and EU_SEASON1_ONLY else []):
                        if rng and rng[-1][2] == col and rng[-1][1] == place - 1:
                            rng[-1] = (rng[-1][0], place, col)
                        else:
                            rng.append((place, place, col))
                            why.append('eu')
                else:
                    a = 1
                    if pl.get('cc'):
                        rng.append((1, pl['cc'], LIGHT_BLUE))
                        why.append('cc')
                        a = pl['cc'] + 1
                    if pl.get('uefa'):
                        rng.append((a, a + pl['uefa'] - 1, GREEN))
                        why.append('uefa')
            if dv['up']:
                rng.append((1, dv['up'], LIGHT_BLUE))
                why.append('up')
            for p in po:                                 # pack-level knockout play-offs: [division, place] entrants
                if p.get('kind') == 'stage_title' and m.get('id') in LIGUILLA_ZONES and not groups_of(dv):
                    for e in p.get('entrants', []):          # 4.0.1 (Davide, Mexico): a one-table split league's
                        if isinstance(e, dict) and 'stage_place' in e and e.get('div', 0) == i:   # Liguilla: its
                            rng.append((e['place'], e['place'], GREEN))   # tournament's top places (the shown
                            why.append('po_title')                        # table is the current tournament's: 'reset')
                    continue
                ent = [e for e in p.get('entrants', []) if isinstance(e, list) and e[0] == i]
                if not ent:
                    continue
                kind = p.get('kind', 'promotion')
                wd = p.get('winner_div')
                for _, place in ent:
                    if kind in ('europe',):              # a European play-off's entrants: P.OFF green as every
                        col, w = GREEN, 'po_eu'          # play-off (Davide 2026-10-22: in the competition's colour
                                                         # they read as its places - AUT's 5th and 7th-8th as CONF)
                    elif kind == 'playout':
                        col, w = ORANGE, 'out'
                    elif kind == 'promotion':
                        col, w = (GREEN, 'po_up') if (wd is None or wd < i) else (ORANGE, 'po_down')
                    else:                                # title / placement play-offs (CONVENTIONS rule 7)
                        col, w = GREEN, 'po_title' if kind == 'title' else 'po_place'
                    rng.append((place, place, col))
                    why.append(w)
            if lg['special'] and comp.get('playoffs') == 'ita':
                li = next(k for k, lv in enumerate(lg['levels']) if any(x is dv for x in lv))
                if li == 1:                              # Serie B
                    rng += [(3, 8, GREEN), (16, 17, ORANGE)]
                    why += ['po_up', 'out']
                elif li == 2:                            # the Serie C groups
                    rng.append((2, 10, GREEN))
                    why.append('po_up')
            if dv['down']:
                rng.append((n - dv['down'] + 1, n, RED))
                why.append('down')
            gleg = []
            for g, ga, gz in group_ranges(dv, po, i):   # 4.0 group headers (longtable): a zone's places by
                rng.append((ga | 0x80, gz | (g << 6), GREEN))   # its group place, shown only with the headers on
                why.append('po_grp')
                gleg = [(GREEN, 'po')]
            sg = split_groups(dv) if not groups_of(dv) else []
            if sg:                                       # a split league after its split: each range by group place too
                plain = [(r, w) for r, w in zip(rng, why) if not r[0] & 0x80]
                for (a, z, c), w in plain:
                    for g, (ga, gz, _) in enumerate(sg[:4]):
                        if a <= gz and z >= ga:
                            rng.append(((max(a, ga) - ga + 1) | 0x80, (min(z, gz) - ga + 1) | (g << 6), c))
                            why.append(w + '/grp')
                gleg = None                              # (the plain legend, filled below)
            rng, why = _merge(rng, why)                  # (one range per run of places: RANGES is short)
            if detail is not None:
                detail[(ci, i)] = [r + (w,) for r, w in zip(rng[:RANGES], why)]
            if rng:
                kind = ('lp' if lp else 'classic') if id(dv) in top and (m.get('europe_places') or rank) else 'lower'
                if id(dv) in top and not m.get('europe_places') and continental(m):
                    kind = 'confed/' + '/'.join(dict.fromkeys(e['cup'] for e in continental(m)))
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), rng[:RANGES], kind,
                            m['files'][comp['clubs']]['file'] if kind == 'lp' else 0, gleg, why[:RANGES]))
            elif lp and rank and id(dv) in top and not EU_SEASON1_ONLY:   # European colours only at run time
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), [], 'lp',
                            m['files'][comp['clubs']]['file'], [], []))
    return out


def groups_of(dv):
    """A division's groups of consecutive places (its split stage's 'zones', e.g. Argentina's zones A / B, the MLS
    conferences): [(first place, size)], or [] for none."""
    for st in ((dv.get('split') or {}).get('stages') or []):
        zs = st.get('zones')
        if zs and len(zs) > 1:
            out, a = [], 1
            for z in zs:
                out.append((a, len(z)))
                a += len(z)
            return out
    return []


def split_groups(dv):
    """A split division's groups after its split (the last stage with 2+ groups): [(first, last, names)], names
    {lang: [long, short]} or None; [] for none."""
    out = []
    for st in ((dv.get('split') or {}).get('stages') or ([dv['split']] if dv.get('split') else [])):
        gs = st.get('groups') or []
        if len(gs) > 1:
            out = [(g['places'][0], g['places'][1], g.get('title') or g.get('names')) for g in gs]
    return out


def group_ranges(dv, po, i):
    """[(group, first, last)] in group places: a split-stage play-off's entrants of division i (stage_place
    entrants: places of the stage's table), per group; [] without groups."""
    gs = groups_of(dv)
    if not gs:
        return []
    per = {}
    for p in po:
        for e in p.get('entrants', []):
            if isinstance(e, dict) and 'stage_place' in e and e.get('div', 0) == i:
                for g, (a, n) in enumerate(gs):
                    if a <= e['place'] < a + n:
                        per.setdefault(g, set()).add(e['place'] - a + 1)
    out = []
    for g, pl in sorted(per.items()):
        pl = sorted(pl)
        out.append((g, pl[0], pl[-1]))
    return out[:2]


HDR_NAMES = {     # 4.0 group headers: default labels (a pack's "zone_names": {lang: [..]} overrides)
    'conf': {'it': ['CONFERENCE EST', 'CONFERENCE OVEST'], 'en': ['EASTERN CONFERENCE', 'WESTERN CONFERENCE'],
             'fr': ['CONFERENCE EST', 'CONFERENCE OUEST'], 'de': ['EASTERN CONFERENCE', 'WESTERN CONFERENCE']},
    'zone': {'it': 'ZONA', 'en': 'ZONE', 'fr': 'ZONE', 'de': 'ZONE'},
}
HDR_LABEL = 24                  # a label's bytes (NUL padded)
CONF_PACKS = ('usa', 'pan')     # leagues of two conferences, East first (4.0.1: Panama's Conferencia Este / Oeste)


def header_labels(lang, pack_dirs):
    """gplay.c gp_hlabel_c's table: [count dw] + per long table of groups: title (NAME) + 4 labels (HDR_LABEL):
    the MLS conferences, otherwise ZONA A / B ... in the exe language."""
    rows = []
    for d in pack_dirs:
        m = complist.load_pack(d)                       # (as pack_zones: the game's titles)
        if m.get('kind') != 'career':
            continue
        cl = os.path.join(d, 'clubs.csv')
        clubs = [dict(r, file=r.get('file') or 'league', division=r.get('division') or '0')
                 for r in complist.csv.DictReader(open(cl, encoding='utf-8'))] if os.path.exists(cl) else []
        for comp in m.get('competitions', []):
            if comp['type'] != 'league':
                continue
            lg = complist._league(comp, clubs)
            for dv in (x for lv in lg['levels'] for x in lv):
                gs = groups_of(dv)
                sg = [] if gs else split_groups(dv)
                if not gs and not sg:
                    continue
                zn = m.get('zone_names') or {}
                conf = m.get('id', '').split('-')[-1] in CONF_PACKS and len(gs or sg) == 2
                if conf and not (lang in zn or '*' in zn):      # (two conferences: the MLS, Panama: East / West)
                    labels = HDR_NAMES['conf'][lang]
                elif sg:                                # a split league: its groups' names (the data's 'title')
                    gen = {'it': 'GRUPPO', 'en': 'GROUP', 'fr': 'GROUPE', 'de': 'GRUPPE'}[lang]
                    labels = [complist._nm(nm, lang) if nm else f'{gen} {chr(65 + g)}' for g, (_, _, nm) in enumerate(sg)]
                elif lang in zn or '*' in zn:
                    labels = zn.get(lang) or zn['*']
                else:
                    labels = [f"{HDR_NAMES['zone'][lang]} {chr(65 + g)}" for g in range(len(gs))]
                rows.append((_title(m, lang, complist._nm(dv['name'], lang)), labels[:4]))
    b = bytearray(struct.pack('<I', len(rows)))
    for title, labels in rows:
        t = title.encode('latin-1')[:NAME - 1]
        b += t + bytes(NAME - len(t))
        for k in range(4):
            x = (labels[k] if k < len(labels) else '').encode('latin-1')[:HDR_LABEL - 1]
            b += x + bytes(HDR_LABEL - len(x))
    return bytes(b)


def context(pack_dirs):
    """({world: world_cups}, {pack dir: season-1 association rank}) of a build's packs."""
    metas = {}
    for d in pack_dirs:
        m = complist.load_pack(d)
        if m.get('kind') == 'career' and m.get('world_cups'):
            metas[m.get('world', 0)] = m['world_cups']
    coef = {}                                            # season-1 association ranks: 5 seasons' coefficients
    for d in pack_dirs:
        m = complist.load_pack(d)
        if m.get('uefa_coef', {}).get('country'):
            coef.setdefault(m.get('world', 0), []).append((-sum(m['uefa_coef']['country']), d))
    ranks = {d: k + 1 for w, lst in coef.items() for k, (_, d) in enumerate(sorted(lst))}
    return metas, ranks


def eu_places(rank):
    """A league-phase top flight's European places in season 1 by its rank, as the table colours them: ([(first,
    last, colour, 'cl' / 'el' / 'conf')], the cup winner's cup or None); the EPS / title holders' rebalancing aside."""
    al = access_list().get(rank, [])
    comp = lambda r: ('cl', LIGHT_BLUE) if r < 8 else ('el', GREEN) if r < 14 else ('conf', DARK_BLUE)
    out = []
    for place, r in sorted((1 if c == 0 else c, r) for r, c in al if c != 1):
        k, col = comp(r)
        if out and out[-1][3] == k and out[-1][1] == place - 1:
            out[-1] = (out[-1][0], place, col, k)
        else:
            out.append((place, place, col, k))
    cw = [comp(r)[0] for r, c in al if c == 1]
    return out, (cw[0] if cw else None)


def table(lang, pack_dirs):
    """The build's zone table: [(world, title, ranges)] (no two keys alike)."""
    metas, ranks = context(pack_dirs)
    out, seen = [], set()
    for d in pack_dirs:
        m = complist.load_pack(d)
        w = m.get('world', 0) if m.get('kind') == 'career' else 0
        for world, title, rng, kind, code, gleg, why in pack_zones(d, lang, _lp_world(metas, w), ranks.get(d)):
            assert (world, title) not in seen, (world, title)
            seen.add((world, title))
            leg = legend(rng, kind, why)
            out.append((world, title, rng, leg, kind, metas.get(world, {}).get('start_year', 1900) - 1900,
                        code, leg if gleg is None else gleg))
    out += [r for r in conti_rows(lang, metas) if (r[0], r[1]) not in seen]
    return out


CONTI_LAB = {'lib': 'lib', 'sud': 'sud', 'ccc': 'ccc', 'acle': 'acle', 'acl2': 'acl2', 'cl': 'cafcl', 'cc': 'cafcc',
             'ocl': 'ofc'}
LEGX, CUPY, CUPT = 92, 3, 70   # (an entry's byte: 1 = a cup's group table: its legend in the title row, y CUPY, the
                                # title bar from x CUPT (the groups' header rows have no room: GRUPPO A ...))


def conti_rows(lang, metas):
    """4.0: the other confederations' group stages (conti.py; the game's own group tables, titled with the cup's name
    as the FORMAT page): light blue for the places that go on in the cup, green for those that move to another cup."""
    import conti
    import mkseason
    worlds = {pk.world for pk in mkseason.packs() if pk.meta.get('id', '').startswith('world-2026-27-') and pk.world}
    if not worlds or not conti.ready():
        return []
    w, out = min(worlds), []
    for conf in conti.ready():
        for c in conti._read(conf, 'format')['cups']:
            gs = [rd for rd in c['rounds'] if rd['kind'] == 'groups' and rd.get('out')]
            for rd in sorted(gs, key=lambda r: -r['groups'] * r['size'])[:1]:   # (the biggest group stage: the one
                                                                                 # the game plays, conti.py)
                rng, leg = [], [(LIGHT_BLUE, 'next')]
                for p, to in sorted(rd['out'].items(), key=lambda x: int(x[0])):
                    col = GREEN if ':' in to or to == 'po' else LIGHT_BLUE   # (play-offs / another cup: green)
                    if col == GREEN and not any(l[0] == GREEN for l in leg):
                        leg.append((GREEN, CONTI_LAB.get(to.split(':')[0], 'po') if ':' in to else 'po'))
                    if rng and rng[-1][2] == col and rng[-1][1] == int(p) - 1:
                        rng[-1] = (rng[-1][0], int(p), col)
                    else:
                        rng.append((int(p), int(p), col))
                name = (c['names'].get(lang) or c['names']['en'])[0].upper()
                for title in (' ' + name, name):
                    out.append((w, title[:NAME - 1], rng[:RANGES], leg, 'cupgrp',   # (code: the group size, the
                                metas.get(w, {}).get('start_year', 1900) - 1900, rd['size'], leg))   # place per group)
    return out


def write(out_dir, pack_dirs):
    """DATA\\ZONxx[world].DAT for every language and world: [(name, tables)]."""
    files = []
    for lang in FILE:
        by = {}
        for row in table(lang, pack_dirs):
            by.setdefault(row[0], []).append(row)
        for w, rows in sorted(by.items()):
            name = f'ZON{lang.upper()}{w or ""}.DAT'
            data = blob(rows)
            assert len(data) <= 0x8000, (name, len(data))
            open(os.path.join(out_dir, name), 'wb').write(data)
            files.append((name, len(rows)))
    return files


def file_names(pack_dirs):
    worlds = sorted({row[0] for row in table('it', pack_dirs)})
    return [f'ZON{lang.upper()}{w or ""}.DAT' for w in worlds for lang in FILE]


def continental(m):
    """A pack's places in its confederation's club cups: pack.json "continental_places" ([{"cup": key, "places": [first,
    last]}], keys in CONFED), else confed2627's table by pack id; [] for none."""
    return [e for e in continental_all(m) if 'places' in e]


def continental_all(m):
    """continental()'s entries with the cup winner's ("via") and the notes ("note")."""
    if 'continental_places' in m:
        return m['continental_places'] or []
    import confed2627
    return confed2627.PLACES.get(m.get('id'), [])


WHY_LAB = {'next': 'next', 'up': 'up', 'po_up': 'po', 'po_title': 'po', 'po_place': 'po', 'po_eu': 'po', 'po_down': 'out', 'out': 'out',
           'down': 'down', 'cc': 'cc', 'uefa': 'uefa'}


def legend(rng, kind, why=None):
    """[(colour, label key)] in place order, one per painted zone (CONVENTIONS rule 6): the label from the zone's
    reason where it names one (a play-off is P.OFF whatever its colour), else from the colour and the table's kind."""
    if kind.startswith('confed/'):
        cups = kind.split('/')[1:]
        names = {CONFED[c]: c for c in reversed(cups)}
        names.update({ORANGE: 'out', RED: 'down'})
        kind = 'confed'
    names = names if kind == 'confed' else {'lp': {LIGHT_BLUE: 'cl', GREEN: 'el', DARK_BLUE: 'conf', ORANGE: 'out', RED: 'down'},
             'classic': {LIGHT_BLUE: 'cc', GREEN: 'uefa', ORANGE: 'out', RED: 'down'},
             'lower': {LIGHT_BLUE: 'up', GREEN: 'po', ORANGE: 'out', RED: 'down'}}.get(kind, {})
    why = list(why or []) + [None] * (len(rng) - len(why or []))
    out, seen = [], set()
    for (a, z, c), w in sorted((r, w) for r, w in zip(rng, why) if not r[0] & 0x80):
        k = WHY_LAB.get(w) or (w if w in CONFED else None) or names.get(c)
        if kind == 'lp' and k in ('cl', 'el', 'conf'):   # (a league-phase top flight's European labels come from its
            continue                                     # run-time colours: EU_LEG)
        if k and (c, k) not in seen:
            seen.add((c, k))
            out.append((c, k))
    return out[:LEG]


def blob(rows):
    b = bytearray(struct.pack('<I', len(rows)))
    for world, title, rng, leg, kind, year, code, gleg in rows:
        t = title.encode('latin-1')[:NAME - 1]
        e = bytes([world]) + t + b'\0' * (NAME - len(t)) + bytes([len(rng)])
        for a, z, c in rng:
            e += bytes([a, z, c])
        e += b'\0' * (1 + NAME + 1 + 3 * RANGES - len(e)) + bytes([len(leg)])
        for c, k in leg:
            e += bytes([LEG_COLOUR.get(c, c), KEYS.index(k)])
        e += b'\0' * (EFLAG - len(e)) + bytes([1 if kind == 'lp' else 0, year % 256, code])
        if any(r[0] & 0x80 for r in rng):              # 4.0 group headers: their legend (+GLEG: n, (colour, label))
            assert len(e) == GLEG, len(e)
            e += bytes([len(gleg[:GLEG_N])]) + b''.join(bytes([LEG_COLOUR.get(c, c), KEYS.index(k)]) for c, k in gleg[:GLEG_N])
        assert len(e) <= min(ENTRY_PAD, LEGX) or kind != 'cupgrp', len(e)
        e += b'\0' * (ENTRY_PAD - len(e))
        if kind == 'cupgrp':                           # (a cup's group screen: LEGX = 3: places per group (bit 0) and
            e = e[:LEGX] + bytes((3, code)) + e[LEGX + 2:]   # the legend in the title row (bit 1); LEGX + 1 = the size)
        elif kind == 'state' and code:                   # (a state of several groups: places per group only)
            e = e[:LEGX] + bytes((1, code)) + e[LEGX + 2:]
        b += e
    return bytes(b)


ASM = r"""
zn_col:                                 ; replaces `mov ax, [dseg_11F41C]` at cseg_49B65 (or lp36's call there)
FIRST
    pushad
    call zn_roff                        ; (the row's name box: our ring off - a scrolled table reuses the entries)
LP_SKIP
    xor ebx, ebx                        ; the table's world: a career's world byte, else 0
WORLD_BYTE
    mov esi, DIY + 4
    cmp bl, [ZKEY]                      ; the cached table?
    jne .look
    xor ecx, ecx
.cc:
    mov al, [esi + ecx]
    cmp al, [ZKEY + 1 + ecx]
    jne .look
    test al, al
    jz .hit
    inc ecx
    cmp ecx, NAME_
    jb .cc
    jmp .hit
.look:
    mov [ZKEY], bl                      ; read DATA\ZONxx[world].DAT, cache the key and the entry (none: ZHIT 0)
    xor ecx, ecx
.ck:
    mov al, [esi + ecx]
    mov [ZKEY + 1 + ecx], al
    inc ecx
    cmp ecx, NAME_
    jb .ck
    mov dword [ZHIT], 0
    mov edi, ZFILE + FN_BASE_           ; the file name: data/zonxx + the world number + .dat
    movzx eax, bl
    test eax, eax
    jz .fn
    xor edx, edx
    mov ecx, 10
    div ecx
    test eax, eax
    jz .u
    add al, '0'
    stosb
.u:
    lea eax, [edx + '0']
    stosb
.fn:
    mov dword [edi], 7461642Eh          ; '.dat'
    mov byte [edi + 4], 0
    mov edx, ZFILE
    mov eax, 3D00h
    int 21h
    jc .hit
    mov ebp, eax                        ; (bl: the world, kept)
    push ebx
    mov ebx, ebp
    mov edx, BUF
    mov ecx, BUFLEN_
    mov ah, 3Fh
    int 21h
    pushfd
    mov ah, 3Eh
    int 21h
    popfd
    pop ebx
    jc .hit
    mov edi, BUF + 4
    mov edx, [BUF]
.e:
    test edx, edx
    jz .hit
    cmp bl, [edi]
    jne .n
    xor ecx, ecx
.t:
    mov al, [edi + 1 + ecx]
    cmp al, [esi + ecx]
    jne .n
    test al, al
    jz .f
    inc ecx
    cmp ecx, NAME_
    jb .t
.f:
    mov esi, edi                        ; the entry -> ZENT (the buffer is shared with the FORMAT page)
    mov edi, ZENT
    mov ecx, ENTRY_ / 4
    rep movsd
    mov dword [ZHIT], ZENT
    jmp .hit
.n:
    add edi, ENTRY_
    dec edx
    jmp .e
.hit:
    mov edi, [ZHIT]
    test edi, edi                       ; 4.0: no club of the table (DIY, +31h clubs) has played a match yet (a table
    jz .z0                              ; before its first match day, the clubs in their initial order): no zones, no
    movzx ecx, word [DIY + 31h]         ; legend (Davide)
    lea esi, [DIY + 2B3h + 4]           ; (a row: +0 team, +4 played .. +10h points)
.z1:
    jecxz .z2
    cmp word [esi], 0
    jne .z0
    add esi, 18
    loop .z1
.z2:
    xor edi, edi
.z0:
    cmp word [D7], 0                    ; the first row: the European places (run time), the legend boxes
    jne .nl
RANK_CALL
    call zn_leg
.nl:
    test edi, edi
    jz .x
    call zn_eu                          ; bh = 1: no European colours (EU_SEASON1_ONLY, a later season)
EU_ROW
    movzx eax, word [D7]
    shr eax, 1
    inc eax                             ; the row's place 1..
    test byte [edi + LEGX_], 1          ; groups shown one after the other: the rows run on (B = 5..8):
    jz .pg                              ; the place within its group
    push ecx
    push edx
    dec eax
    xor edx, edx
    movzx ecx, byte [edi + LEGX_ + 1]
    div ecx
    lea eax, [edx + 1]
    pop edx
    pop ecx
.pg:
OV_ROW
    xor ebp, ebp                        ; (4.0 group headers: ebp = 10000h + group * 100h + its group place)
HDR_PREP
    movzx ecx, byte [edi + 1 + NAME_]
    lea esi, [edi + 2 + NAME_]
.r:
    test ecx, ecx                       ; (jecxz: out of short range)
    jz .x
HDR_RANGE
    cmp al, [esi]
    jb .rn
    cmp al, [esi + 1]
    ja .rn
.m:
    movzx edx, byte [esi + 2]           ; the zone's colour
    call zn_iseu
    je .rn
.apply:
    mov [D3], dx
    mov esi, [A1]                       ; club (team file record): a computer club's name in the row colour
    cmp byte [esi + 4], 1
    jne .hu
    mov esi, [A5]
    mov [esi + 1Eh], dx
    jmp .x
.hu:
    call zn_ron                         ; the human's name box keeps its own colour, clean as in the game; a ring
    jmp .x                              ; only when that colour is the zone's (Davide 2026-10-22)
.rn:
    add esi, 3
    dec ecx
    jmp .r
.x:
    popad
    ret

zn_leg:                                 ; edi = the table's entry or 0: the legend boxes (the menu's last LEG_
    pushad                              ; entries), on the GC header's line, the colours the table uses
    xor ebp, ebp
    test edi, edi
    jz .c
    movzx ebp, byte [edi + LEGN_]
.c:
    movzx ecx, word [MENU + 10h]
    sub ecx, LEG_
    imul ebx, ecx, 38h
    add ebx, MENU + 16h
    mov dx, [MENU + 16h + 16h]          ; the header line: under the title bar (entry 24 moves in a long table)
    add dx, [MENU + 16h + 1Ah]
    inc dx
    push ebx
    call zn_eu
    mov [ZEU], bh
    pop ebx
    xor ecx, ecx                        ; ecx = box
EU_LEG
.d:
HDR_LEG
    xor esi, esi                        ; esi = the entry's legend item
.l:
    cmp ecx, LEG_
    jae .o
.it:
    cmp esi, ebp
    jae .h
    cmp byte [ZEU], 0
    je .take
    push edx
    movzx edx, byte [edi + LEGN_ + 2 + esi * 2]     ; a European label (cl, el, conf, cc, uefa): skip it
    cmp edx, 4
    pop edx
    ja .take
    inc esi
    jmp .it
.take:
    mov al, [edi + LEGN_ + 1 + esi * 2]
    mov ah, [edi + LEGN_ + 2 + esi * 2]
    inc esi
    call zn_box
    jmp .l
.h:
    mov word [ebx + 4], 1
    add ebx, 38h
    inc ecx
    jmp .l
.o:
    mov word [MENU + 16h + 14h], 8      ; the title bar: whole width
    mov word [MENU + 16h + 18h], 304
    mov edi, [esp]                      ; (the entry as it came: HDR_LEG moves edi to the group legend)
    test edi, edi                       ; a cup's group table: the boxes in the title row, the bar from CUPT_
    jz .q
    test byte [edi + LEGX_], 2
    jz .q
    mov word [MENU + 16h + 14h], CUPT_
    mov word [MENU + 16h + 18h], 312 - CUPT_
    movzx ecx, word [MENU + 10h]
    sub ecx, LEG_
    imul ebx, ecx, 38h
    add ebx, MENU + 16h
    mov ecx, LEG_
.s:
    mov word [ebx + 16h], CUPY_
    add ebx, 38h
    dec ecx
    jnz .s
.q:
    popad
    ret

zn_box:                                 ; ebx = a legend box, ecx = its number, dx = y, al = colour, ah = label:
    push eax                            ; shown; ebx and ecx to the next one
    push esi
    push edi
    mov word [ebx + 4], 0
    push eax
    imul eax, ecx, LEG_W_ + 1
    add eax, 8
    mov [ebx + 14h], ax
    pop eax
    mov [ebx + 16h], dx
    push eax
    movzx eax, al
    mov [ebx + 1Eh], ax
    pop eax
    movzx eax, ah
    lea esi, [LABS + eax * 8]
    lea edi, [LEGBUF + ecx * 8]
    movsd
    movsd
    pop edi
    pop esi
    pop eax
    add ebx, 38h
    inc ecx
    ret

zn_eu:                                  ; edi = the entry (or 0) -> bh = 1 when its European colours are off
    push eax                            ; (seasonPlaying = the year - 1900: the world's first season = its start year)
    mov al, bl
    xor bh, bh
    test edi, edi
    jz .r
    cmp byte [edi + EFLAG_], 0
    je .r
SEASON_TEST
.r:
    mov bl, al
    pop eax
    ret

zn_iseu:                                ; dl = a colour, bh = 1 -> ZF = 1 when it is a European one to drop
    test bh, bh
    jz .no
    cmp dl, 0Dh
    je .r
    cmp dl, 0Eh
    je .r
    cmp dl, 08h
    je .r
.no:
    or bh, 0                            ; (bh != 0 here or the jz above: ZF = 0)
    cmp bh, 0FFh
.r:
    ret
"""



HDR_PREP_ASM = """    cmp dword [GP_HON], 0               ; headers drawn in this table (a long table of one group)
    je .hp
    cmp word [DIY + 4Fh], 1
    jne .hp
    movzx ebp, byte [GP_HG + eax]
    shl ebp, 8
    push edx
    movzx edx, byte [GP_HGP + eax]
    or ebp, edx
    pop edx
    or ebp, 10000h
.hp:
"""
HDR_RANGE_ASM = """    test byte [esi], 80h                ; a group range (headers on only): group place, group
    jnz .g
    test ebp, 10000h                    ; a plain range: headers off only
    jnz .rn
    jmp .pl
.g: test ebp, 10000h
    jz .rn
    push eax
    push edx
    mov eax, ebp
    mov dl, [esi]
    and dl, 7Fh
    cmp al, dl
    jb .gn
    mov dl, [esi + 1]
    mov dh, dl
    and dl, 3Fh
    cmp al, dl
    ja .gn
    shr dh, 6
    cmp ah, dh
    jne .gn
    pop edx
    pop eax
    jmp .m
.gn:
    pop edx
    pop eax
    jmp .rn
.pl:
"""
HDR_LEG_ASM = """    test edi, edi                       ; group headers on: the group legend (entry +GLEG)
    jz .hl
    cmp dword [GP_HON], 0
    je .hl
    cmp word [DIY + 4Fh], 1
    jne .hl
    cmp byte [edi + GLEG_], 0
    je .hl
    add edi, GLEG_ - LEGN_
    movzx ebp, byte [edi + LEGN_]
.hl:
"""

def _menu_copy(p, area, legbuf):
    """DIY_leagueTournamentMenu (its init DIYLeagueTournamentInit: mov word [..], 0 / mov word [..], 0 / call) copied
    whole into area (its pointers moved along) with LEG legend boxes after its last entry (invisible until zn_leg
    shows them; x, y, colour and text set there). Returns (the copy, the obj1 site of `mov [A6], offset menu`)."""
    import re
    d2 = p.le.obj_bytes(2)
    hdr = struct.pack('<hhhhHHHH', 0, 0, 304, 14, 4, 0x17, 8, 0) + b'\xff' * 4 + b'\0\0' + struct.pack('<hhhh', 0, 188, 202, 12)
    fx = list(p.le.fixups())
    d1 = p.le.obj_bytes(1)
    starts = []
    for m in re.finditer(re.escape(hdr), d2):
        st = m.start() - 16
        init = p.target(2, st)
        if init[0] == 1 and re.match(rb'\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00\xe8', d1[init[1]:init[1] + 23], re.S):
            starts.append(st)
    assert len(starts) == 1, starts
    st = starts[0]
    tgt = {f[1]: (f[3], f[4]) for f in fx if f[0] == 2}
    end = st + 16
    while not (d2[end:end + 2] == b'\x19\xfc' and (end + 2) in tgt):   # -999, then the next menu's header
        end += 2
        assert end < st + 0x2000
    body = bytearray(d2[st:end])
    ptrs = [(o - st, t) for o, t in tgt.items() if st <= o < end]
    for k in range(LEG):
        e = struct.pack('<hhhh', 8 + k * (LEG_W + 1), 0, LEG_W, 8) + struct.pack('<H', 1) + struct.pack('<HH', 4, 7)
        e += struct.pack('<HH', 8, 0)
        ptrs.append((len(body) + len(e), (2, legbuf + k * LEG_TXT)))
        body += e + b'\0\0\0\0' + b'\0\0'
    body += struct.pack('<h', -999)
    base = area.add(bytes(body))
    for o, (t_obj, t_off) in ptrs:
        assert (base + o) // 0x1000 == (base + o + 3) // 0x1000, 'a pointer straddles a page'
        p.add_ptr(2, base + o, t_obj, t_off)
    refs = [f[1] for f in fx if f[0] == 1 and (f[3], f[4]) == (2, st)]
    assert len(refs) == 1, refs
    return base, refs[0]


def _current_menu(p):
    """g_currentMenu (the unpacked menu): ActivateMenu's `mov A1, offset g_currentMenu` (as purple.py finds it)."""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    m = [x for x in re.finditer(rb'\xA1(....)\xA3....\xA1(....)\xA3....\xC7\x05(....)(....)\xFF\x35....\xE8', d1, re.S)
         if x.group(1) == x.group(2) and struct.unpack('<I', x.group(3))[0] == a0 + 4]
    assert len(m) == 1, len(m)
    return p.target(1, m[0].start() + 26)


RANK_ASM = r"""
zn_rank:                                ; edi = a league-phase top flight's entry: ZEUC = its places' colours by the
    pushad                              ; association's rank in uc_rank (the ranking a year old: the one that
    xor eax, eax                        ; decides the next season's places, uefacoef 131f04b)
    mov [ZEUC], eax
    mov [ZEUC + 4], eax
    mov [ZEUC + 8], ax
    mov ebp, CBV
    call UC_RANK
    mov al, [edi + ECODE_]
    xor ecx, ecx
.f:
    cmp ecx, [UC_N]
    jae .o
    cmp al, [UC_C + ecx]
    je .g
    inc ecx
    jmp .f
.g:
    cmp ecx, ZRANKS_
    jae .o
    imul esi, ecx, EU_PLACES_
    add esi, ZAL
    mov edi, ZEUC
    mov ecx, EU_PLACES_
    rep movsb
.o:
    popad
    ret
"""
RANK_CALL = """    test edi, edi
    jz .lg
    cmp byte [edi + EFLAG_], 0
    je .lg
    call zn_rank
.lg:
"""
EU_ROW = """    cmp byte [edi + EFLAG_], 0          ; a league-phase top flight: places 1..EU_PLACES_ from ZEUC
    je .eur
    movzx eax, word [D7]
    shr eax, 1
    cmp eax, EU_PLACES_
    jae .eur
    movzx edx, byte [ZEUC + eax]
    test edx, edx
    jnz .apply
.eur:
"""
EU_LEG = """    test edi, edi                       ; a league-phase top flight: its European colours first, in place
    jz .d                               ; order, one box each (Conference: dark blue)
    cmp byte [edi + EFLAG_], 0
    je .d
    mov byte [ZSEEN], 0
    xor esi, esi
.e:
    cmp esi, EU_PLACES_
    jae .d
    mov al, [ZEUC + esi]
    inc esi
    mov ah, 0
    cmp al, 0Dh
    je .e0
    mov ah, 1
    cmp al, 0Eh
    je .e0
    mov ah, 2
    cmp al, 08h
    je .e0
    jmp .e
.e0:
    push ecx
    mov cl, ah
    mov ch, 1
    shl ch, cl
    test [ZSEEN], ch
    jnz .e1
    or [ZSEEN], ch
    pop ecx
    cmp ecx, LEG_
    jae .o
    call zn_box
    jmp .e
.e1:
    pop ecx
    jmp .e
"""


RING_ASM = r"""
zn_roff:                                ; zn_col, every row: its name box (A5) loses our ring (entries are reused)
    push esi
    mov esi, [A5]
    cmp dword [esi + 34h], zn_ring
    jne .n
    and dword [esi + 34h], 0
.n:
    pop esi
    ret

zn_ron:                                 ; zn_col, the human's name box in a zone row, dl = the zone's colour: its own
    push esi                            ; colour stays; a black ring (afterDraw) only when that colour is the zone's
    push eax                            ; (a player-coach's light blue in a light-blue row)
    mov esi, [A5]
    mov al, [esi + 1Eh]
    and al, 0Fh
    cmp al, dl
    jne .n
    mov dword [esi + 34h], zn_ring
.n:
    pop eax
    pop esi
    ret

zn_ring:                                ; afterDraw of the human's name box (zn_col: its colour = the zone's): a 1-px
    pushad                              ; black ring on the box's own edge, the name's white / shadow pixels kept
    mov esi, [A5]
    movzx edi, word [esi + 16h]         ; y * 320 + x + the menus' screen (DrawEmptyMenuItem's)
    imul edi, edi, 320
    movzx eax, word [esi + 14h]
    add edi, eax
    add edi, [LIN384]
    movzx ecx, word [esi + 18h]         ; width
    movzx edx, word [esi + 1Ah]         ; height
    test ecx, ecx
    jz .x
    test edx, edx
    jz .x
    lea ebx, [edx - 1]
    imul ebx, ebx, 320                  ; (the top row -> the bottom row)
    xor ebp, ebp
.h:
    lea eax, [edi + ebp]
    call .px
    add eax, ebx
    call .px
    inc ebp
    cmp ebp, ecx
    jb .h
    mov eax, edi
.v:
    call .px
    push eax
    lea eax, [eax + ecx - 1]
    call .px
    pop eax
    add eax, 320
    dec edx
    jnz .v
.x:
    popad
    ret
.px:
    cmp byte [eax], WHITE_
    je .k
    cmp byte [eax], SHADOW_
    je .k
    mov byte [eax], BLACK_
.k:
    ret
"""
RING = None                     # {label: (obj, off)} of zn_roff / zn_ron / zn_ring when ring_patch put them in gplay's
                                # pages (the cosmetics page is full); else zones.patch assembles them with its own code


def _ring_sym(p):
    import lp36
    import sacups
    d1 = p.le.obj_bytes(1)
    a1 = struct.pack('<I', sacups.regs(d1)['A0'] + 4)
    hits = [m.start() for m in re.finditer(rb'\xa1(.{4})\x05\x00\x00\x01\x00\xa3' + re.escape(a1), d1, re.S)]
    assert len(hits) == 1, hits                          # LoadFillAndSwtitle: mov eax, [linAdr384k] / add eax, 65536
    return {'A5': (2, lp36._sites(p)['A0'] + 20), 'LIN384': p.target(1, hits[0] + 1),
            'WHITE_': (0, 2), 'SHADOW_': (0, 8), 'BLACK_': (0, 3)}   # (the menus' palette: the font's white and shadow)


def ring_patch(p, at):
    """zn_ring at obj1:at (gplay's pages); returns its end."""
    global RING
    at = (at + 15) & ~15
    sym = _ring_sym(p)
    code, cfix = nasmcave.assemble(RING_ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    lab = nasmcave.labels(RING_ASM, at, sym)
    RING = {k: (1, lab[k]) for k in ('zn_roff', 'zn_ron', 'zn_ring')}
    return at + len(code)


def patch(p, at, area, lang, pack_dirs, bss, bss_len, world=None):
    """Code at obj1:at, small data in obj2 area; the tables in DATA\\ZONxx[world].DAT (write()), read into the shared
    buffer obj2:bss (bss_len bytes, fmtpage's) when the table changes; world = careerworld's sites in a world build."""
    import lp36
    s = lp36._sites(p)
    site, a0, diy = s['col'], s['A0'], s['DIY']
    d1 = p.le.obj_bytes(1)
    assert d1[site:site + 2] == b'\x66\xa1'
    cur = bytes(p.get(1, site, 6))
    lp = cur[0] == 0xE8                                   # lp36's lp_col is there (its fixup at site + 2 is gone)
    c11 = None if lp else p.target(1, site + 2)
    rows = table(lang, pack_dirs)
    keys = area.add(bytes(4 + 1 + NAME + 3))             # ZHIT, ZKEY (world + title)
    zent = area.add(bytes(ENTRY_PAD))
    zfile = area.add(FILE[lang] + bytes(12))
    L = LABELS[lang]
    labs = area.add(b''.join(L[k].encode('latin-1')[:LEG_TXT - 1].ljust(LEG_TXT, b'\0') for k in KEYS))
    legbuf = area.add(bytes(LEG * LEG_TXT))
    menu_new, menu_ref = _menu_copy(p, area, legbuf)
    cur_menu = _current_menu(p)
    first = ('    call LP_COL\n' if lp else '    mov ax, [C11]\n')
    src = nasmcave.sub(ASM, 'FIRST\n', first)
    src = nasmcave.sub(src, 'LP_SKIP\n', '    call LP_OURS\n    je .x\n' if lp else '')
    import uefacoef
    rt = lp and world is not None and not EU_SEASON1_ONLY and 'uc_rank' in uefacoef.LABELS
    src = nasmcave.sub(src, 'RANK_CALL\n', RANK_CALL if rt else '')
    src = nasmcave.sub(src, 'EU_ROW\n', EU_ROW if rt else '')
    src = nasmcave.sub(src, 'EU_LEG\n', EU_LEG if rt else '')
    if rt:
        src += RANK_ASM
    src = nasmcave.sub(src, 'SEASON_TEST\n', '    mov bl, [SEASONP]\n    cmp bl, [edi + EFLAG_ + 1]\n    je .r\n    mov bh, 1\n'
                      if world and EU_SEASON1_ONLY else '')
    src = nasmcave.sub(src, 'WORLD_BYTE\n', '''    cmp word [GAMETYPE], 4
    jne .w
    mov bl, [SLT + 1845]
.w:
''' if world else '')
    sym = {'D3': (2, a0 - 20), 'D7': (2, a0 - 4), 'A1': (2, a0 + 4), 'A5': (2, a0 + 20), 'DIY': (2, diy),
           **({'C11': c11} if c11 else {}), 'ZHIT': (2, keys), 'ZEU': (2, keys + 47), 'ZKEY': (2, keys + 4), 'NAME_': (0, NAME), 'ZENT': (2, zent),
           'ZFILE': (2, zfile), 'FN_BASE_': (0, len(FILE[lang])), 'BUF': (2, bss), 'BUFLEN_': (0, bss_len),
           'ENTRY_': (0, ENTRY_PAD), 'LEG_': (0, LEG), 'LEG_W_': (0, LEG_W), 'LEGN_': (0, 1 + NAME + 1 + 3 * RANGES), 'LEGX_': (0, LEGX), 'CUPY_': (0, CUPY), 'CUPT_': (0, CUPT),
           'LABS': (2, labs), 'EFLAG_': (0, EFLAG), 'ECODE_': (0, ECODE), 'GLEG_': (0, GLEG), 'EU_PLACES_': (0, EU_PLACES), 'LEGBUF': (2, legbuf), 'MENU': cur_menu}
    import fmtpage
    import gplay
    ov = 'on' in fmtpage.OV and 'GP_OV_ANNUAL' in gplay.LABELS
    hdr = 'GP_HON' in gplay.LABELS and 'GP_HG' in gplay.LABELS
    src = nasmcave.sub(src, 'HDR_PREP\n', HDR_PREP_ASM if hdr else '')
    src = nasmcave.sub(src, 'HDR_RANGE\n', HDR_RANGE_ASM if hdr else '')
    src = nasmcave.sub(src, 'HDR_LEG\n', HDR_LEG_ASM if hdr else '')
    if hdr:
        import longtable
        sym.update({'GP_HON': gplay.LABELS['GP_HON'], 'GP_HG': gplay.LABELS['GP_HG'], 'GP_HGP': gplay.LABELS['GP_HGP'],
                    'LT_ROWS_': (0, longtable.ROWS)})
    src = nasmcave.sub(src, 'OV_ROW\n', '''    cmp byte [OV_ON], 2                 ; 4.0 the overall table in its annual form (Argentina): the last relegated
    jne .o
    cmp eax, [GP_OV_N]
    jne .o
    mov edx, RED_
    jmp .apply
.o:
''' if ov else '')
    if ov:
        sym.update({'OV_ON': (2, fmtpage.OV['on']),
                    'GP_OV_N': gplay.LABELS['GP_OV_N'], 'RED_': (0, RED)})
    if rt:
        zal = area.add(rank_colours())
        zeuc = area.add(bytes(EU_PLACES + 2))
        sym.update({'UC_RANK': (1, uefacoef.LABELS['uc_rank']), 'UC_N': (1, uefacoef.LABELS['UC_N']),
                    'UC_C': (1, uefacoef.LABELS['UC_C']), 'CBV': uefacoef.LABELS['CB_ADDR'], 'ZAL': (2, zal),
                    'ZEUC': (2, zeuc), 'ZSEEN': (2, zeuc + EU_PLACES + 1), 'ZRANKS_': (0, 55)})
    if lp:
        sym.update({'LP_COL': (1, site + 5 + struct.unpack('<i', cur[1:5])[0]), 'LP_OURS': (1, lp36.LABELS['lp_ours'])})
    if world:
        sym.update({'GAMETYPE': world['gametype'], 'SLT': world['slt'], 'SEASONP': (2, world['season'])})
    if RING:
        sym.update(RING)
    else:
        src += RING_ASM
        sym.update(_ring_sym(p))
    at = (at + 15) & ~15
    code, cfix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.retarget(1, menu_ref, 2, menu_new)
    p.put(1, menu_ref, struct.pack('<I', menu_new))
    if not lp:
        p.remove(1, site + 2)
    p.put(1, site, b'\xE8' + struct.pack('<i', lab['zn_col'] - (site + 5)) + b'\x90')
    print(f'exe: zone colours: {len(rows)} league tables (DATA\\ZON{lang.upper()}*.DAT), code obj1+{at:#x} ({len(code)} B), '
          f'{"after lp36 lp_col" if lp else "alone"}')
    return at + len(code)
