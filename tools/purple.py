"""Purple kits (3.3.0): an 11th kit colour, 10 = purple (Fiorentina, Anderlecht, Austria Wien, Valladolid...).

In a match sprites use palette entries 0..15 only, all taken: 0/7/8/9 pitch, 1/2/3 grey/white/black, 4/5/6 skin,
10..15 the kit colours (red, blue, MAROON = the "brown" kit colour 6, light blue, green, yellow); shirtColorTable maps
the 10 kit colours to them. Purple borrows entry 12 for the match: kit colour 10 converts to entry 12 like maroon,
and when the kits worn in the match have purple and no maroon, entry 12 becomes purple in the match palette.
- shirtColorTable (10 bytes, followed by a string) -> an 11-byte copy (10 -> 12); its two users (ConvertTeamColor,
  ConvertPlayerDressColor) retargeted.
- conflictingBasicTeamColorsTable / conflictingShortsTeamColorsTable (10 words each, adjacent; rows as kitcolors.py
  leaves them) -> 11-row copies: purple clashes with purple and maroon (and maroon with purple), so the game's own kit
  choice gives one of them its other kit when they meet (Fiorentina-Torino).
- kTeamColorsTable (the menus' kit sprites, same palette entries) -> 11 words; the Edit Teams kit editor cycles 0..10.
- ConvertTeamKitColors (writes the kit a team wears into topTeamInGame / bottomTeamInGame): its first instruction
  `mov al, [D0]` becomes `call pk_mark`, which records for that team whether shirt, stripes (not on a plain shirt),
  shorts or socks are purple or maroon.
- the match palette: GameLoop's `mov ecx, 768 / rep movsb` (savedPalette -> g_workingPalette, before the upper half is
  darkened from it) and the stadium screen's copy of the stad.256 palette (ShowStadiumInit) become `call pk_pal`: the
  same copy, then entry 12 = purple when a team wears purple and none wears maroon.
"""
import re
import struct

import kitcolors
import nasmcave

PURPLE = 10                     # the new kit colour
SLOT = 12                       # the palette entry it borrows (maroon's)
RGB = (24, 8, 34)               # 6-bit VGA purple (Fiorentina's viola)
MAROON = 6
MENU_MAROON = (27, 0, 9)        # entry 12 of the menu palettes (FILL.256, STAD.256)

ASM = r"""
pk_mark:                                ; replaces `mov al, [D0]` at the start of ConvertTeamKitColors
    pushad                              ; D0 shirt type, D1 shirt, D2 stripes, D3 shorts, D4 socks, A1 -> team
    mov eax, [A1]
    xor ebx, ebx
    cmp eax, TOP
    je .team
    inc ebx
    cmp eax, BOTTOM
    jne .out
.team:
    xor ecx, ecx                        ; bit 0 purple, bit 1 maroon
    mov al, [D0 + 4]
    call .chk
    cmp byte [D0], 0                    ; a plain shirt has no stripes
    je .nostripes
    mov al, [D0 + 8]
    call .chk
.nostripes:
    mov al, [D0 + 12]
    call .chk
    mov al, [D0 + 16]
    call .chk
    mov [MARKS + ebx], cl
.out:
    popad
    mov al, [D0]
    ret
.chk:
    cmp al, PURPLE_
    jne .m
    or cl, 1
    ret
.m:
    cmp al, MAROON_
    jne .r
    or cl, 2
.r:
    ret

pk_pal:                                 ; replaces `mov ecx, 768 / rep movsb` (esi -> source palette, edi -> working)
    push eax
    push edi
    mov ecx, 768
.copy:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .copy
    pop edi
    mov al, [MARKS]
    or al, [MARKS + 1]
    cmp al, 1                           ; purple, no maroon
    jne .done
    mov byte [edi + SLOT_ * 3], R_
    mov byte [edi + SLOT_ * 3 + 1], G_
    mov byte [edi + SLOT_ * 3 + 2], B_
.done:
    pop eax
    ret

pk_edit:                                ; replaces `mov dword [A6], editTeamsTeam` at the start of Primary- and
    mov dword [A6], EDITTEAM            ; SecondaryKitColorConversion (the Edit Teams / SELECT KITS kit sprites)
    pushad
    mov esi, EDITTEAM
    xor ecx, ecx
    lea ebx, [esi + 26]                 ; first kit: type, shirt, stripes, shorts, socks
    call kitchk
    lea ebx, [esi + 31]                 ; second kit
    call kitchk
    mov edi, WORKING
    mov al, R_
    mov ah, G_
    mov dl, B_
    cmp cl, 1                           ; purple, no maroon: entry 12 purple, else the menus' maroon
    je .set
    mov al, MR_
    mov ah, MG_
    mov dl, MB_
.set:
    mov [edi + SLOT_ * 3], al
    mov [edi + SLOT_ * 3 + 1], ah
    mov [edi + SLOT_ * 3 + 2], dl
    mov edi, FADE
    mov [edi + SLOT_ * 3], al
    mov [edi + SLOT_ * 3 + 1], ah
    mov [edi + SLOT_ * 3 + 2], dl
    mov esi, WORKING
    call SETPAL
    popad
    ret

kitchk:                                 ; ebx -> kit (type, shirt, stripes, shorts, socks) -> cl |= 1 purple, 2 maroon
    mov al, [ebx + 1]
    call pk_mark.chk
    cmp byte [ebx], 0
    je .ns
    mov al, [ebx + 2]
    call pk_mark.chk
.ns:
    mov al, [ebx + 3]
    call pk_mark.chk
    mov al, [ebx + 4]
    jmp pk_mark.chk
"""


def _retarget(p, site, toff):
    p.retarget(1, site, 2, toff)
    p.put(1, site, struct.pack('<I', toff))


def patch(p, area, at):
    """After kitcolors.patch (conflict rows) and kitcolors.button (INFO). Code at obj1:at; returns its end."""
    info = kitcolors.INFO
    assert info, 'kitcolors.button first'
    d1, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    fix = list(p.le.fixups())

    # 1. shirtColorTable -> 11 bytes
    old = bytes([1, 2, 3, 6, 10, 11, 12, 13, 14, 15])
    t = d2.find(old + b'data/team')
    assert t >= 0
    refs = [o for so, o, ty, to, tt, *_ in fix if so == 1 and to == 2 and tt == t]
    assert len(refs) == 2, refs
    tab = area.add(old + bytes([SLOT]) + b'\0')
    for o in refs:
        _retarget(p, o, tab)

    # 2. the two conflict tables -> 11 rows (current rows: kitcolors' variant)
    pat = rb'\x66\x81\x25....\xff\x00\x66\x81\x25....\xff\x00\x66\xd1\x25....\xc7\x05....(....)'
    sites = [m.start(1) for m in re.finditer(pat, d1, re.S)]
    assert len(sites) == 2, sites
    for o in sites:
        toff = p.target(1, o)[1]
        rows = list(struct.unpack('<10H', p.get(2, toff, 20)))
        rows[MAROON] |= 1 << PURPLE
        rows.append(1 << PURPLE | 1 << MAROON)
        _retarget(p, o, area.add(struct.pack('<11H', *rows)))

    # 2b. kTeamColorsTable (menu kit sprites: kit colour -> palette entry, 10 words) -> 11 words
    kt = d2.find(struct.pack('<10H', *old) + bytes([70, 71]))
    krefs = [o for so, o, ty, to, tt, *_ in fix if so == 1 and to == 2 and tt == kt]
    assert kt >= 0 and len(krefs) == 6, krefs
    ktab = area.add(struct.pack('<11H', *old, SLOT))
    for o in krefs:
        _retarget(p, o, ktab)

    # 2c. the Edit Teams kit editor cycles 0..9: wrap down `sub byte [D0], 1 / jns / mov byte [D0], 9` -> 10,
    #     wrap up `add byte [D0], 1 / cmp byte [D0], 10 / jnz` -> 11 (shirt, stripes, shorts, socks; both kits)
    down = [m for m in re.finditer(rb'\x80\x2D(....)\x01(?:\x79.|\x0F\x89....)\xC6\x05(....)\x09', d1, re.S)
            if m.group(1) == m.group(2)]
    assert len(down) == 8, len(down)
    lo, hi = down[0].start() - 0x100, down[-1].start() + 0x100
    up = [m for m in re.finditer(rb'\x80\x05(....)\x01\x80\x3D(....)\x0A\x75', d1, re.S)
          if m.group(1) == m.group(2) and lo <= m.start() <= hi]
    assert len(up) == 8, len(up)
    for m in down:
        assert p.get(1, m.end() - 1, 1) == b'\x09'
        p.put(1, m.end() - 1, bytes([PURPLE]))
    for m in up:
        assert p.get(1, m.start() + 13, 1) == b'\x0A'
        p.put(1, m.start() + 13, bytes([PURPLE + 1]))

    # 3. ConvertTeamKitColors: first instruction mov al, [D0]
    conv, D0, A0 = info['convert'], info['D0'], info['A0']
    assert p.get(1, conv, 5) == d1[conv:conv + 5] and d1[conv] == 0xA0 and p.target(1, conv + 1) == (2, D0)

    # 4. palette copies: GameLoop (mov esi, savedPalette / mov edi, g_workingPalette / mov ecx, 768 / rep movsb) and
    #    ShowStadiumInit (add esi, 64000 / mov edi, g_workingPalette / mov ecx, 768 / rep movsb / mov A0, aStad_256)
    gl = [x.start() for x in re.finditer(rb'\xBE....\xBF....\xB9\x00\x03\x00\x00\xF3\xA4', d1, re.S)]
    st = [x.start() for x in re.finditer(rb'\x81\xC6\x00\xFA\x00\x00\xBF....\xB9\x00\x03\x00\x00\xF3\xA4\xC7\x05', d1, re.S)]
    assert len(st) == 1, st
    working = p.target(1, st[0] + 7)
    gl = [x for x in gl if p.target(1, x + 6) == working]
    assert len(gl) == 1, [hex(x) for x in gl]
    copies = [gl[0] + 10, st[0] + 11]                    # the `mov ecx, 768` of each

    # 5. the kit editor: Primary/SecondaryKitColorConversion start `mov dword [A6], editTeamsTeam / mov [A2], .. /
    #    mov [A3], kTeamColorsTable`; SetPalette, g_workingPalette, g_fadePalette from FillPalettes
    edits = [o - 26 for o in krefs if d1[o - 26:o - 24] == b'\xC7\x05' and d1[o - 16:o - 14] == b'\xC7\x05'
             and d1[o - 6:o - 4] == b'\xC7\x05']
    assert len(edits) == 2, edits
    a6, et = p.target(1, edits[0] + 2), p.target(1, edits[0] + 6)
    assert all(p.target(1, e + 2) == a6 and p.target(1, e + 6) == et for e in edits)
    fp = re.search(rb'\xbf....\xbe....\xb9\x0f\x00\x00\x00', d1, re.S)
    fade = p.target(1, fp.start() + 1)
    assert p.target(1, fp.start() + 6) == (2, working[1])
    q = d1.find(b'\xBE', fp.end())
    assert p.target(1, q + 1) == (2, working[1]) and d1[q + 5] == 0xE8
    setpal = q + 10 + struct.unpack('<i', d1[q + 6:q + 10])[0]

    marks = area.add(b'\0\0\0\0')
    at = (at + 15) & ~15
    sym = {'D0': (2, D0), 'A1': (2, A0 + 4), 'TOP': info['top'], 'BOTTOM': info['bottom'], 'MARKS': (2, marks),
           'PURPLE_': (0, PURPLE), 'MAROON_': (0, MAROON), 'SLOT_': (0, SLOT),
           'R_': (0, RGB[0]), 'G_': (0, RGB[1]), 'B_': (0, RGB[2]),
           'MR_': (0, MENU_MAROON[0]), 'MG_': (0, MENU_MAROON[1]), 'MB_': (0, MENU_MAROON[2]),
           'A6': a6, 'EDITTEAM': et, 'WORKING': working, 'FADE': fade, 'SETPAL': (1, setpal)}
    code, cfix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, conv + 1)
    p.put(1, conv, b'\xE8' + struct.pack('<i', lab['pk_mark'] - (conv + 5)))
    for e in edits:
        p.remove(1, e + 2)
        p.remove(1, e + 6)
        p.put(1, e, b'\xE8' + struct.pack('<i', lab['pk_edit'] - (e + 5)) + b'\x90' * 5)
    for c in copies:
        assert p.get(1, c, 7) == b'\xB9\x00\x03\x00\x00\xF3\xA4'
        p.put(1, c, b'\xE8' + struct.pack('<i', lab['pk_pal'] - (c + 5)) + b'\x90\x90')
    print(f'exe: purple kits: colour {PURPLE} -> palette {SLOT} when no maroon (code obj1+{at:#x}, {len(code)} B; '
          f'ConvertTeamKitColors obj1+{conv:#x}, palette copies obj1+{copies[0]:#x}, +{copies[1]:#x})')
    return at + len(code)

# Clubs the game (and the mod's packs) dressed in maroon for want of purple: their kit colour 6 becomes 10.
CLUBS = {b'FIORENTINA', b'AUSTRIA VIENNA', b'AUSTRIA WIEN', b'ANDERLECHT', b'TOULOUSE', b'VALLADOLID',
         b'SAPRISSA DEPORTO', b'SON HIROSHIMA', b'DEFENSOR SPORT', b'AUSTRIA SALZBURG'}
VANILLA_FILES = (1, 2, 13, 35, 47, 55, 71)   # original team files with such a club and nothing else changed by the mod
TEAM_SIZE = 684


def recolor(data, header=True):
    """Team file bytes (header: the 2-byte count first) -> (bytes, clubs recoloured): CLUBS' kit colour 6 -> 10."""
    d, n, o0 = bytearray(data), 0, 2 if header else 0
    for k in range((len(d) - o0) // TEAM_SIZE):
        o = o0 + k * TEAM_SIZE
        if bytes(d[o + 5:o + 22]).split(b'\0')[0] in CLUBS:
            for at in (27, 28, 29, 30, 32, 33, 34, 35):             # shirt, stripes, shorts, socks of both kits
                if d[o + at] == MAROON:
                    d[o + at] = PURPLE
            n += 1
    return bytes(d), n
