"""Zone colours in the league tables (4.0; Davide's palette): each row's background tells its end-of-season zone.

    light blue 0Dh  the best way up: Champions League / Champions Cup places, or direct promotion
    green      0Eh  the second way up: Europa League / UEFA Cup places, a promotion or European play-off
    dark blue  08h  the third European cup: Conference League places (league-phase worlds)
    orange     0Ch  play-out / relegation play-off
    red        0Ah  direct relegation
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

LIGHT_BLUE, GREEN, DARK_BLUE, ORANGE, RED = 0x0D, 0x0E, 0x08, 0x0C, 0x0A
NAME = 41                       # the slot's name field (as fmtpage.NAME)
RANGES = 8
ENTRY = 1 + NAME + 1 + 3 * RANGES   # world, title, n, (first, last, colour) * RANGES = 67
ENTRY_PAD = 68


def _title(pk_meta, lang, name):
    bn = pk_meta.get('button_names') or {}
    return f"{bn.get(lang, pk_meta.get('button', ''))} {name}".upper()[:NAME - 1]


def _lp_world(meta_by_world, n):
    wc = meta_by_world.get(n, {})
    return any(wc.get(k, {}).get('format') == 'league_phase' for k in ('cc', 'cwc', 'uefa'))


def pack_zones(d, lang, lp=False):
    """[(world, title, [(first, last, colour), ...])] of one pack's league divisions."""
    m = json.load(open(os.path.join(d, 'pack.json')))
    cl = os.path.join(d, 'clubs.csv')
    clubs = [dict(r, file=r.get('file') or 'league', division=r.get('division') or '0')
             for r in complist.csv.DictReader(open(cl, encoding='utf-8'))] if os.path.exists(cl) else []
    world = m.get('world', 0) if m.get('kind') == 'career' else 0
    out = []
    for comp in m.get('competitions', []):
        if comp['type'] != 'league':
            continue
        lg = complist._league(comp, clubs)
        divs = [dv for lv in lg['levels'] for dv in lv]
        top = set(id(dv) for dv in lg['levels'][0])
        po = comp.get('ko_playoffs') or []
        if isinstance(po, int):
            po = []
        for i, dv in enumerate(divs):
            n, rng = dv['clubs'], []
            if id(dv) in top:
                pl = m.get('europe_places', {})
                if lp:
                    a = 1
                    for k, col, cnt in (('cc', LIGHT_BLUE, pl.get('cc', 0)), ('cwc', GREEN, max(0, pl.get('cwc', 0) - 1)),
                                        ('uefa', DARK_BLUE, pl.get('uefa', 0))):
                        if cnt:
                            rng.append((a, a + cnt - 1, col))
                            a += cnt
                else:
                    a = 1
                    if pl.get('cc'):
                        rng.append((1, pl['cc'], LIGHT_BLUE))
                        a = pl['cc'] + 1
                    if pl.get('uefa'):
                        rng.append((a, a + pl['uefa'] - 1, GREEN))
            if dv['up']:
                rng.append((1, dv['up'], LIGHT_BLUE))
            for p in po:                                 # pack-level knockout play-offs: [division, place] entrants
                ent = [e for e in p.get('entrants', []) if isinstance(e, list) and e[0] == i]
                if not ent:
                    continue
                kind = p.get('kind', 'promotion')
                wd = p.get('winner_div')
                for _, place in ent:
                    if kind in ('europe',):
                        col = GREEN
                    elif kind == 'playout':
                        col = ORANGE
                    elif kind == 'promotion':
                        col = GREEN if (wd is None or wd < i) else ORANGE
                    else:
                        continue
                    rng.append((place, place, col))
            if lg['special'] and comp.get('playoffs') == 'ita':
                if i == 1:                               # Serie B
                    rng += [(3, 8, GREEN), (16, 17, ORANGE)]
                elif i >= 2:                             # the Serie C groups
                    rng.append((2, 10, GREEN))
            if dv['down']:
                rng.append((n - dv['down'] + 1, n, RED))
            if rng:
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), rng[:RANGES]))
    return out


def table(lang, pack_dirs):
    """The build's zone table: [(world, title, ranges)] (no two keys alike)."""
    metas = {}
    for d in pack_dirs:
        m = json.load(open(os.path.join(d, 'pack.json')))
        if m.get('kind') == 'career' and m.get('world_cups'):
            metas[m.get('world', 0)] = m['world_cups']
    out, seen = [], set()
    for d in pack_dirs:
        m = json.load(open(os.path.join(d, 'pack.json')))
        w = m.get('world', 0) if m.get('kind') == 'career' else 0
        for world, title, rng in pack_zones(d, lang, _lp_world(metas, w)):
            assert (world, title) not in seen, (world, title)
            seen.add((world, title))
            out.append((world, title, rng))
    return out


def blob(rows):
    b = bytearray(struct.pack('<I', len(rows)))
    for world, title, rng in rows:
        t = title.encode('latin-1')[:NAME - 1]
        e = bytes([world]) + t + b'\0' * (NAME - len(t)) + bytes([len(rng)])
        for a, z, c in rng:
            e += bytes([a, z, c])
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
    mov [ZKEY], bl                      ; search ZTAB, cache the key and the entry (0 = none)
    xor ecx, ecx
.ck:
    mov al, [esi + ecx]
    mov [ZKEY + 1 + ecx], al
    inc ecx
    cmp ecx, NAME_
    jb .ck
    mov dword [ZHIT], 0
    mov edi, ZTAB + 4
    mov edx, [ZTAB]
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
    mov [ZHIT], edi
    jmp .hit
.n:
    add edi, ENTRY_
    dec edx
    jmp .e
.hit:
    mov edi, [ZHIT]
    test edi, edi
    jz .x
    movzx eax, word [D7]
    shr eax, 1
    inc eax                             ; the row's place 1..
    movzx ecx, byte [edi + 1 + NAME_]
    lea esi, [edi + 2 + NAME_]
.r:
    jecxz .x
    cmp al, [esi]
    jb .rn
    cmp al, [esi + 1]
    ja .rn
    movzx edx, byte [esi + 2]           ; the zone's colour
    mov [D3], dx
    mov esi, [A1]                       ; club (team file record): a computer club's name in the row colour
    cmp byte [esi + 4], 1
    jne .x
    mov esi, [A5]
    mov [esi + 1Eh], dx
    jmp .x
.rn:
    add esi, 3
    dec ecx
    jmp .r
.x:
    popad
    ret
"""


def patch(p, at, area, lang, pack_dirs, world=None):
    """Code at obj1:at, the table in obj2 area; world = careerworld's sites in a build with career worlds."""
    import lp36
    s = lp36._sites(p)
    site, a0, diy = s['col'], s['A0'], s['DIY']
    d1 = p.le.obj_bytes(1)
    assert d1[site:site + 2] == b'\x66\xa1'
    c11 = p.target(1, site + 2)
    cur = bytes(p.get(1, site, 6))
    lp = cur[0] == 0xE8                                   # lp36's lp_col is there
    rows = table(lang, pack_dirs)
    base = area.add(blob(rows))
    keys = area.add(bytes(4 + 1 + NAME + 3))             # ZHIT, ZKEY (world + title)
    first = ('    call LP_COL\n' if lp else '    mov ax, [C11]\n')
    src = ASM.replace('FIRST\n', first)
    src = src.replace('LP_SKIP\n', '    call LP_OURS\n    je .x\n' if lp else '')
    src = src.replace('WORLD_BYTE\n', '''    cmp word [GAMETYPE], 4
    jne .w
    mov bl, [SLT + 1845]
.w:
''' if world else '')
    sym = {'D3': (2, a0 - 20), 'D7': (2, a0 - 4), 'A1': (2, a0 + 4), 'A5': (2, a0 + 20), 'DIY': (2, diy),
           'C11': c11, 'ZTAB': (2, base), 'ZHIT': (2, keys), 'ZKEY': (2, keys + 4), 'NAME_': (0, NAME),
           'ENTRY_': (0, ENTRY_PAD)}
    if lp:
        sym.update({'LP_COL': (1, site + 5 + struct.unpack('<i', cur[1:5])[0]), 'LP_OURS': (1, lp36.LABELS['lp_ours'])})
    if world:
        sym.update({'GAMETYPE': world['gametype'], 'SLT': world['slt']})
    at = (at + 15) & ~15
    code, cfix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    if not lp:
        p.remove(1, site + 2)
    p.put(1, site, b'\xE8' + struct.pack('<i', lab['zn_col'] - (site + 5)) + b'\x90')
    print(f'exe: zone colours: {len(rows)} league tables, code obj1+{at:#x} ({len(code)} B), '
          f'{"after lp36 lp_col" if lp else "alone"}')
    return at + len(code)
