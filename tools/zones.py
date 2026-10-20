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
LEG = 5                         # legend boxes (the colours a table uses, in place order)
ENTRY = 1 + NAME + 1 + 3 * RANGES + 1 + 2 * LEG   # world, title, n, ranges, n legend, (colour, label) * LEG = 78
ENTRY_PAD = 84
ECODE = 80                      # a league-phase top flight: its association's code (the league's team file, uefacoef)
EU_PLACES = 10                  # the access list's places looked at per rank (the top 9 + 1)
EFLAG = 78                      # 1: a league-phase world's top flight (its European places: season 1 only)
EU_SEASON1_ONLY = False         # (True: season-1 colours in season 1 only; False: every season from uc_rank, the
                                # ranking a year old that decides the next season's places, uefacoef 131f04b)
LEG_W, LEG_TXT = 30, 8
FILE = {'it': b'data/zonit', 'en': b'data/zonen', 'fr': b'data/zonfr', 'de': b'data/zonde'}          # a legend box's width (5 small-font characters), its text buffer
CONFED = {'lib': LIGHT_BLUE, 'sud': GREEN, 'ccc': LIGHT_BLUE, 'acle': LIGHT_BLUE, 'acl2': GREEN, 'cafcl': LIGHT_BLUE,
          'cafcc': GREEN, 'ofc': LIGHT_BLUE}   # the other confederations' club cups: the first light blue, the second green
CONFED_LAB = dict(lib='LIB', sud='SUD', ccc='CCC', acle='ACLE', acl2='ACL2', cafcl='CAFCL', cafcc='CAFCC', ofc='OFC')
# legend labels (<= 5 characters): top flight of a league-phase world, of a classic world, a lower division
LABELS = {
    'it': dict(cl='CL', el='EL', conf='CONF', cc='CAMP', uefa='UEFA', up='PROM', po='P.OFF', out='P.OUT', down='RETR', **CONFED_LAB),
    'en': dict(cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='UP', po='P.OFF', out='P.OUT', down='DOWN', **CONFED_LAB),
    'fr': dict(cl='LDC', el='LE', conf='LC', cc='C1', uefa='C3', up='MONT', po='BARR', out='MAINT', down='DESC', **CONFED_LAB),
    'de': dict(cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='AUF', po='AUF-R', out='ABS-R', down='AB', **CONFED_LAB),
}
KEYS = ('cl', 'el', 'conf', 'cc', 'uefa', 'up', 'po', 'out', 'down', 'lib', 'sud', 'ccc', 'acle', 'acl2', 'cafcl', 'cafcc', 'ofc')
LEG_COLOUR = {DARK_BLUE: 0x13}  # the legend box: dark blue with a frame (08h alone vanishes on the menu's blue)


def _title(pk_meta, lang, name):
    bn = pk_meta.get('button_names') or {}
    return f"{bn.get(lang, pk_meta.get('button', ''))} {name}".upper()[:NAME - 1]


def _lp_world(meta_by_world, n):
    wc = meta_by_world.get(n, {})
    return any(wc.get(k, {}).get('format') == 'league_phase' for k in ('cc', 'cwc', 'uefa'))


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
                ent = [e for e in p.get('entrants', []) if isinstance(e, list) and e[0] == i]
                if not ent:
                    continue
                kind = p.get('kind', 'promotion')
                wd = p.get('winner_div')
                for _, place in ent:
                    if kind in ('europe',):
                        col, w = GREEN, 'po_eu'
                    elif kind == 'playout':
                        col, w = ORANGE, 'out'
                    elif kind == 'promotion':
                        col, w = (GREEN, 'po_up') if (wd is None or wd < i) else (ORANGE, 'po_down')
                    else:
                        continue
                    rng.append((place, place, col))
                    why.append(w)
            if lg['special'] and comp.get('playoffs') == 'ita':
                li = next(k for k, lv in enumerate(lg['levels']) if any(x is dv for x in lv))
                if li == 1:                              # Serie B
                    rng += [(3, 8, GREEN), (16, 17, ORANGE)]
                    why += ['po_up', 'out']
                elif li == 2:                            # the Serie C groups (not the Serie D's: their own play-offs)
                    rng.append((2, 10, GREEN))
                    why.append('po_up')
            if dv['down']:
                rng.append((n - dv['down'] + 1, n, RED))
                why.append('down')
            for g, ga, gz in group_ranges(dv, po, i):   # 4.0 group headers (longtable): a zone's places by
                rng.append((ga | 0x80, gz | (g << 6), GREEN))   # its group place, shown only with the headers on
                why.append('po_grp')
            if detail is not None:
                detail[(ci, i)] = [r + (w,) for r, w in zip(rng[:RANGES], why)]
            if rng:
                kind = ('lp' if lp else 'classic') if id(dv) in top and (m.get('europe_places') or rank) else 'lower'
                if id(dv) in top and not m.get('europe_places') and continental(m):
                    kind = 'confed/' + '/'.join(dict.fromkeys(e['cup'] for e in continental(m)))
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), rng[:RANGES], kind,
                            m['files'][comp['clubs']]['file'] if kind == 'lp' else 0))
            elif lp and rank and id(dv) in top and not EU_SEASON1_ONLY:   # European colours only at run time
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), [], 'lp',
                            m['files'][comp['clubs']]['file']))
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
                if not gs:
                    continue
                zn = m.get('zone_names') or {}
                if lang in zn or '*' in zn:
                    labels = zn.get(lang) or zn['*']
                elif m.get('id', '').endswith('-usa') and len(gs) == 2:
                    labels = HDR_NAMES['conf'][lang]
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
        for world, title, rng, kind, code in pack_zones(d, lang, _lp_world(metas, w), ranks.get(d)):
            assert (world, title) not in seen, (world, title)
            seen.add((world, title))
            out.append((world, title, rng, legend(rng, kind), kind, metas.get(world, {}).get('start_year', 1900) - 1900,
                        code))
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


def legend(rng, kind):
    """[(colour, label key)] in place order, one per colour."""
    if kind.startswith('confed/'):
        cups = kind.split('/')[1:]
        names = {CONFED[c]: c for c in reversed(cups)}
        names.update({ORANGE: 'out', RED: 'down'})
        kind = 'confed'
    names = names if kind == 'confed' else {'lp': {LIGHT_BLUE: 'cl', GREEN: 'el', DARK_BLUE: 'conf', ORANGE: 'out', RED: 'down'},
             'classic': {LIGHT_BLUE: 'cc', GREEN: 'uefa', ORANGE: 'out', RED: 'down'},
             'lower': {LIGHT_BLUE: 'up', GREEN: 'po', ORANGE: 'out', RED: 'down'}}[kind]
    out, seen = [], set()
    for a, z, c in sorted(r for r in rng if not r[0] & 0x80):
        if c not in seen and c in names:
            seen.add(c)
            out.append((c, names[c]))
    return out[:LEG]


def blob(rows):
    b = bytearray(struct.pack('<I', len(rows)))
    for world, title, rng, leg, kind, year, code in rows:
        t = title.encode('latin-1')[:NAME - 1]
        e = bytes([world]) + t + b'\0' * (NAME - len(t)) + bytes([len(rng)])
        for a, z, c in rng:
            e += bytes([a, z, c])
        e += b'\0' * (1 + NAME + 1 + 3 * RANGES - len(e)) + bytes([len(leg)])
        for c, k in leg:
            e += bytes([LEG_COLOUR.get(c, c), KEYS.index(k)])
        e += b'\0' * (EFLAG - len(e)) + bytes([1 if kind == 'lp' else 0, year % 256, code])
        if any(r[0] & 0x80 for r in rng):              # 4.0 group headers: their legend (one box)
            e += bytes([1, LEG_COLOUR.get(GREEN, GREEN), KEYS.index('po')])
        b += e + b'\0' * (ENTRY_PAD - len(e))
    return bytes(b)


ASM = r"""
zn_col:                                 ; replaces `mov ax, [dseg_11F41C]` at cseg_49B65 (or lp36's call there)
FIRST
    pushad
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
    mov esi, [A5]                       ; the human's name box: its own colour, framed (inner frame colour =
    and word [esi + 1Eh], 0FF0Fh        ; the high nibble, yellow), so a player-coach's light blue stays apart
    or word [esi + 1Eh], FRAME_         ; from a light-blue zone row
    jmp .x
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
    mov dx, [MENU + 16h + 24 * 38h + 16h]
    push ebx
    call zn_eu
    mov [ZEU], bh
    pop ebx
    xor ecx, ecx                        ; ecx = box
HDR_LEG
EU_LEG
.d:
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
    cmp word [DIY + 51h], LT_ROWS_
    jbe .hp
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
HDR_LEG_ASM = """    test edi, edi                       ; group headers on: the group legend (entry +81)
    jz .hl
    cmp dword [GP_HON], 0
    je .hl
    cmp word [DIY + 4Fh], 1
    jne .hl
    cmp word [DIY + 51h], LT_ROWS_
    jbe .hl
    cmp byte [edi + 81], 0
    je .hl
    add edi, 81 - LEGN_
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
    jz .d                               ; order, one box each (Conference: the framed dark blue)
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
    cmp al, 08h
    jne .e2
    mov al, 13h
.e2:
    call zn_box
    jmp .e
.e1:
    pop ecx
    jmp .e
"""


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
    src = ASM.replace('FIRST\n', first)
    src = src.replace('LP_SKIP\n', '    call LP_OURS\n    je .x\n' if lp else '')
    import uefacoef
    rt = lp and world is not None and not EU_SEASON1_ONLY and 'uc_rank' in uefacoef.LABELS
    src = src.replace('RANK_CALL\n', RANK_CALL if rt else '').replace('EU_ROW\n', EU_ROW if rt else '')
    src = src.replace('EU_LEG\n', EU_LEG if rt else '')
    if rt:
        src += RANK_ASM
    src = src.replace('SEASON_TEST\n', '    mov bl, [SEASONP]\n    cmp bl, [edi + EFLAG_ + 1]\n    je .r\n    mov bh, 1\n'
                      if world and EU_SEASON1_ONLY else '')
    src = src.replace('WORLD_BYTE\n', '''    cmp word [GAMETYPE], 4
    jne .w
    mov bl, [SLT + 1845]
.w:
''' if world else '')
    sym = {'D3': (2, a0 - 20), 'D7': (2, a0 - 4), 'A1': (2, a0 + 4), 'A5': (2, a0 + 20), 'DIY': (2, diy),
           **({'C11': c11} if c11 else {}), 'ZHIT': (2, keys), 'ZEU': (2, keys + 47), 'ZKEY': (2, keys + 4), 'NAME_': (0, NAME), 'ZENT': (2, zent),
           'ZFILE': (2, zfile), 'FN_BASE_': (0, len(FILE[lang])), 'BUF': (2, bss), 'BUFLEN_': (0, bss_len),
           'ENTRY_': (0, ENTRY_PAD), 'LEG_': (0, LEG), 'LEG_W_': (0, LEG_W), 'LEGN_': (0, 1 + NAME + 1 + 3 * RANGES),
           'FRAME_': (0, int(os.environ.get('ZN_FRAME', '0x60'), 16)), 'LABS': (2, labs), 'EFLAG_': (0, EFLAG), 'ECODE_': (0, ECODE), 'EU_PLACES_': (0, EU_PLACES), 'LEGBUF': (2, legbuf), 'MENU': cur_menu}
    import fmtpage
    import gplay
    ov = 'on' in fmtpage.OV and 'GP_OV_ANNUAL' in gplay.LABELS
    hdr = 'GP_HON' in gplay.LABELS and 'GP_HG' in gplay.LABELS
    src = src.replace('HDR_PREP\n', HDR_PREP_ASM if hdr else '').replace('HDR_RANGE\n', HDR_RANGE_ASM if hdr else '')
    src = src.replace('HDR_LEG\n', HDR_LEG_ASM if hdr else '')
    if hdr:
        import longtable
        sym.update({'GP_HON': gplay.LABELS['GP_HON'], 'GP_HG': gplay.LABELS['GP_HG'], 'GP_HGP': gplay.LABELS['GP_HGP'],
                    'LT_ROWS_': (0, longtable.ROWS)})
    src = src.replace('OV_ROW\n', '''    cmp byte [OV_ON], 2                 ; 4.0 the overall table in its annual form (Argentina): the last relegated
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
