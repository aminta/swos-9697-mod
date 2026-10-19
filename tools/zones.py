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
ENTRY_PAD = 80
LEG_W, LEG_TXT = 30, 8
FILE = {'it': b'data/zonit', 'en': b'data/zonen', 'fr': b'data/zonfr', 'de': b'data/zonde'}          # a legend box's width (5 small-font characters), its text buffer
# legend labels (<= 5 characters): top flight of a league-phase world, of a classic world, a lower division
LABELS = {
    'it': dict(cl='CL', el='EL', conf='CONF', cc='CAMP', uefa='UEFA', up='PROM', po='P.OFF', out='P.OUT', down='RETR'),
    'en': dict(cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='UP', po='P.OFF', out='P.OUT', down='DOWN'),
    'fr': dict(cl='LDC', el='LE', conf='LC', cc='C1', uefa='C3', up='MONT', po='BARR', out='MAINT', down='DESC'),
    'de': dict(cl='CL', el='EL', conf='CONF', cc='EC', uefa='UEFA', up='AUF', po='AUF-R', out='ABS-R', down='AB'),
}
KEYS = ('cl', 'el', 'conf', 'cc', 'uefa', 'up', 'po', 'out', 'down')
LEG_COLOUR = {DARK_BLUE: 0x13}  # the legend box: dark blue with a frame (08h alone vanishes on the menu's blue)


def _title(pk_meta, lang, name):
    bn = pk_meta.get('button_names') or {}
    return f"{bn.get(lang, pk_meta.get('button', ''))} {name}".upper()[:NAME - 1]


def _lp_world(meta_by_world, n):
    wc = meta_by_world.get(n, {})
    return any(wc.get(k, {}).get('format') == 'league_phase' for k in ('cc', 'cwc', 'uefa'))


def pack_zones(d, lang, lp=False, rank=None):
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
                if lp and rank:
                    for place, col in lp_places(rank, pl.get('cc', 0)):
                        if rng and rng[-1][2] == col and rng[-1][1] == place - 1:
                            rng[-1] = (rng[-1][0], place, col)
                        else:
                            rng.append((place, place, col))
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
                kind = ('lp' if lp else 'classic') if id(dv) in top and (m.get('europe_places') or rank) else 'lower'
                out.append((world, _title(m, lang, complist._nm(dv['name'], lang)), rng[:RANGES], kind))
    return out


def table(lang, pack_dirs):
    """The build's zone table: [(world, title, ranges)] (no two keys alike)."""
    metas = {}
    for d in pack_dirs:
        m = json.load(open(os.path.join(d, 'pack.json')))
        if m.get('kind') == 'career' and m.get('world_cups'):
            metas[m.get('world', 0)] = m['world_cups']
    coef = {}                                            # season-1 association ranks: 5 seasons' coefficients
    for d in pack_dirs:
        m = json.load(open(os.path.join(d, 'pack.json')))
        if m.get('uefa_coef', {}).get('country'):
            coef.setdefault(m.get('world', 0), []).append((-sum(m['uefa_coef']['country']), d))
    ranks = {d: k + 1 for w, lst in coef.items() for k, (_, d) in enumerate(sorted(lst))}
    out, seen = [], set()
    for d in pack_dirs:
        m = json.load(open(os.path.join(d, 'pack.json')))
        w = m.get('world', 0) if m.get('kind') == 'career' else 0
        for world, title, rng, kind in pack_zones(d, lang, _lp_world(metas, w), ranks.get(d)):
            assert (world, title) not in seen, (world, title)
            seen.add((world, title))
            out.append((world, title, rng, legend(rng, kind)))
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


def legend(rng, kind):
    """[(colour, label key)] in place order, one per colour."""
    names = {'lp': {LIGHT_BLUE: 'cl', GREEN: 'el', DARK_BLUE: 'conf', ORANGE: 'out', RED: 'down'},
             'classic': {LIGHT_BLUE: 'cc', GREEN: 'uefa', ORANGE: 'out', RED: 'down'},
             'lower': {LIGHT_BLUE: 'up', GREEN: 'po', ORANGE: 'out', RED: 'down'}}[kind]
    out, seen = [], set()
    for a, z, c in sorted(rng):
        if c not in seen and c in names:
            seen.add(c)
            out.append((c, names[c]))
    return out[:LEG]


def blob(rows):
    b = bytearray(struct.pack('<I', len(rows)))
    for world, title, rng, leg in rows:
        t = title.encode('latin-1')[:NAME - 1]
        e = bytes([world]) + t + b'\0' * (NAME - len(t)) + bytes([len(rng)])
        for a, z, c in rng:
            e += bytes([a, z, c])
        e += b'\0' * (1 + NAME + 1 + 3 * RANGES - len(e)) + bytes([len(leg)])
        for c, k in leg:
            e += bytes([LEG_COLOUR.get(c, c), KEYS.index(k)])
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
    cmp word [D7], 0                    ; the first row: the legend boxes
    jne .nl
    call zn_leg
.nl:
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
    xor ecx, ecx
.l:
    cmp ecx, LEG_
    jae .o
    cmp ecx, ebp
    jae .h
    mov word [ebx + 4], 0
    imul eax, ecx, LEG_W_ + 1
    add eax, 8
    mov [ebx + 14h], ax
    mov [ebx + 16h], dx
    movzx eax, byte [edi + LEGN_ + 1 + ecx * 2]
    mov [ebx + 1Eh], ax
    movzx eax, byte [edi + LEGN_ + 2 + ecx * 2]
    push edi
    lea esi, [LABS + eax * 8]
    lea edi, [LEGBUF + ecx * 8]
    movsd
    movsd
    pop edi
    jmp .n
.h:
    mov word [ebx + 4], 1
.n:
    add ebx, 38h
    inc ecx
    jmp .l
.o:
    popad
    ret
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
    src = src.replace('WORLD_BYTE\n', '''    cmp word [GAMETYPE], 4
    jne .w
    mov bl, [SLT + 1845]
.w:
''' if world else '')
    sym = {'D3': (2, a0 - 20), 'D7': (2, a0 - 4), 'A1': (2, a0 + 4), 'A5': (2, a0 + 20), 'DIY': (2, diy),
           **({'C11': c11} if c11 else {}), 'ZHIT': (2, keys), 'ZKEY': (2, keys + 4), 'NAME_': (0, NAME), 'ZENT': (2, zent),
           'ZFILE': (2, zfile), 'FN_BASE_': (0, len(FILE[lang])), 'BUF': (2, bss), 'BUFLEN_': (0, bss_len),
           'ENTRY_': (0, ENTRY_PAD), 'LEG_': (0, LEG), 'LEG_W_': (0, LEG_W), 'LEGN_': (0, 1 + NAME + 1 + 3 * RANGES),
           'LABS': (2, labs), 'LEGBUF': (2, legbuf), 'MENU': cur_menu}
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
    p.retarget(1, menu_ref, 2, menu_new)
    p.put(1, menu_ref, struct.pack('<I', menu_new))
    if not lp:
        p.remove(1, site + 2)
    p.put(1, site, b'\xE8' + struct.pack('<i', lab['zn_col'] - (site + 5)) + b'\x90')
    print(f'exe: zone colours: {len(rows)} league tables (DATA\\ZON{lang.upper()}*.DAT), code obj1+{at:#x} ({len(code)} B), '
          f'{"after lp36 lp_col" if lp else "alone"}')
    return at + len(code)
