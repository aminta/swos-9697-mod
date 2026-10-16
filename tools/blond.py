"""Black players with blond hair (3.3.0): face value 3 (bits 3-4 of PlayerFile.positionAndFace = 11, unused by the game).

The game draws each team's outfield players from three sets of 101 sprites (TEAM1/2/3.DAT hold three raw copies:
341-441 / 442-542 / 543-643 team 1, 644-946 team 2), recoloured per match by ConvertColorsAndTextSprites with the
kit colours and skinAndHairColorConversionTable[face] (white = black hair, ginger = hair in skin colours, black = black
skin and hair); InitializePlayerSpriteFrameIndices gives each player sprite frameOffset = face * 101. Face 3 would
reach the next team's sprites. Here:
- skinAndHairColorConversionTable (3 pointers, 4 users) -> 4 pointers: face 3 = black skin, hair -> yellow (entry 15)
  and orange (6): the stadium screen's little players (FillSkinColorConversionTable) get it too;
- InitInGamePlayer: `mov al, [D0] / mov esi, [A6] / mov [esi+face], al` -> ig_face: face 3 is stored as 2 (black,
  so the bench, the face counts, the goalkeepers and the menus treat him as a black player) with the flag byte
  PlayerInfoHeader+49 (field_31, unused by the game) = 1;
- ConvertColorsAndTextSprites: before team 1's first set is converted (`mov word [D0], 341`), copy_sets copies the
  raw sets 341-441 and 644-744 into a zero-filled obj2 tail and registers them as sprites NEW1.. / NEW2.. (the
  spritesIndex extension of shirtnum.py); after each team's third set (before its goalkeepers) conv1 / conv2 convert
  them with the team's colour table and face 3;
- InitializePlayerSpriteFrameIndices: a flagged player gets frameOffset NEW1 - 341 (NEW2 - 644);
- menus: face icon 189 (an empty 8x8 sprite after the three faces 186-188) is rebuilt from 188 with its hair (colour
  3 in the top three rows) yellow whenever a face icon is set (all six `add word [Dx], 186`: squad screens cseg_13A55 /
  cseg_13DFB, SetMenuEntryPlayerFace, InitEditTeamsMenu, the Edit Teams face button, whose cycle now runs 0..3).
Goalkeepers flagged blond are drawn as black (their sprites follow team*GoalieFaces, kept at 0..2).
"""
import re
import struct

import nasmcave
import shirtnum

FACE = 3
NEW1 = shirtnum.NEWBASE + 83            # 1418: after the shirt numbers 17..99
NEW2 = NEW1 + 101
SET_BYTES = 0x3C00                      # 101 sprites: 15216 bytes (TEAM1/2/3.DAT, all 1 quad wide, at most 20 lines)
BSS_SIZE = 2 * SET_BYTES
FLAG = 49                               # PlayerInfoHeader.field_31
BLOND = (6, 4, 5, 4, 4, 3, 13, 15, 9, 15, 12, 6, -1)   # black skin; hair bright/medium -> yellow, dark -> orange

ASM = r"""
ig_face:                                ; replaces mov al, [D0] / mov esi, [A6] / mov [esi+face], al
    mov al, [D0]
    mov esi, [A6]
    mov byte [esi + FLAG_], 0
    cmp al, FACE_
    jne .w
    mov al, 2
    mov byte [esi + FLAG_], 1
.w:
    mov [esi + FACE_OFF], al
    ret

copy_sets:                              ; replaces mov word [D0], 341
    pushad
    mov edx, 341
    mov ebp, NEW1_
    mov edi, BUF
    call .set
    mov edx, 644
    mov ebp, NEW2_
    mov edi, BUF + SET_
    call .set
    popad
    mov word [D0], 341
    ret
.set:                                   ; edx = first raw sprite, ebp = first new index, edi -> buffer
    mov ecx, 101
.spr:
    push ecx
    mov esi, [SPRIDX + edx * 4]
    movzx eax, word [esi + 14]          ; wquads
    movzx ecx, word [esi + 12]          ; lines
    imul eax, ecx
    shl eax, 3                          ; pixel bytes
    push eax
    xor ecx, ecx
.hdr:
    mov eax, [esi + ecx]
    mov [edi + ecx], eax
    add ecx, 4
    cmp ecx, 24
    jb .hdr
    pop ecx                             ; pixel bytes (a multiple of 8)
    mov esi, [esi]
    lea eax, [edi + 24]
    mov [edi], eax
    mov [edi + 22], bp
    mov [SPRIDX + ebp * 4], edi
    add edi, 24
.pix:
    mov eax, [esi]
    mov [edi], eax
    add esi, 4
    add edi, 4
    sub ecx, 4
    jnz .pix
    inc edx
    inc ebp
    pop ecx
    dec ecx
    jnz .spr
    ret

conv1:                                  ; replaces mov ax, [useIndividualPlayerSkinColor] before team 1's goalkeepers
    push dword NEW1_
    push dword T1TAB
    call conv
    mov ax, [USEIND]
    ret
conv2:
    push dword NEW2_
    push dword T2TAB
    call conv
    mov ax, [USEIND]
    ret
conv:                                   ; [esp+4] colour table, [esp+8] first new sprite
    cmp word [USEIND], 0                ; one face for the whole team: the set is not used
    je .out
    pushad
    mov ebx, [esp + 36]
    mov byte [D0], FACE_
    mov [A0 + 4], ebx                   ; A1 -> colour table
    call SKINTAB
    mov ecx, 101
    mov edx, [esp + 40]
.l:
    push ecx
    push edx
    mov [D0], dx
    mov ebx, [esp + 44]
    mov [A0], ebx
    push dword [A0 + 20]                ; A5, A6 (as the game around ConvertSpriteColors)
    push dword [A0 + 24]
    call CONVSPR
    pop dword [A0 + 24]
    pop dword [A0 + 20]
    pop edx
    pop ecx
    inc edx
    dec ecx
    jnz .l
    popad
.out:
    ret 8

fo1:                                    ; replaces mov ax, [D0] / mov bx, 442 / sub bx, 341 / mul bx (team 1 player)
    mov ebx, [A0 + 8]                   ; A2 -> player
    mov ax, NEW1_ - 341
    jmp fo
fo2:
    mov ebx, [A0 + 12]                  ; A3 -> player
    mov ax, NEW2_ - 644
fo:
    xor dx, dx
    cmp byte [ebx + FLAG_], 0
    jne .r
    mov ax, [D0]
    mov bx, 101
    mul bx
.r:
    ret

icon_d0:                                ; replaces add word [D0], 186 (face icon)
    add word [D0], 186
    jmp build_icon
icon_d1:
    add word [D1], 186
build_icon:                             ; sprite 189 = 188 with the hair (colour 3, top three rows) yellow
    pushad
    mov esi, [SPRIDX + 188 * 4]
    mov edi, [SPRIDX + 189 * 4]
    movzx ecx, word [esi + 12]
    movzx eax, word [edi + 12]
    cmp ecx, eax
    jne .out
    cmp word [esi + 14], 1
    jne .out
    cmp word [edi + 14], 1
    jne .out
    mov esi, [esi]
    mov edi, [edi]
    shl ecx, 3                          ; bytes
    xor edx, edx
.b:
    mov al, [esi + edx]
    cmp edx, 24                         ; rows 0..2 (8 bytes each): colour 3 -> 15
    jae .put
    mov ah, al
    and ah, 0F0h
    cmp ah, 30h
    jne .lo
    or al, 0F0h
.lo:
    mov ah, al
    and ah, 0Fh
    cmp ah, 3
    jne .put
    or al, 0Fh
.put:
    mov [edi + edx], al
    inc edx
    cmp edx, ecx
    jb .b
.out:
    popad
    ret
"""


def patch(p, area, at, bss, spr):
    """Code at obj1:at, sets at obj2:bss (BSS_SIZE zero bytes), spr = spritesIndex (obj2). Returns the code end."""
    d1, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    fix = list(p.le.fixups())
    one = lambda pat: (lambda m: m[0] if len(m) == 1 else None)([x.start() for x in re.finditer(pat, d1, re.S)])
    t = lambda o: p.target(1, o)
    rel = lambda o: o + 5 + struct.unpack('<i', d1[o + 1:o + 5])[0]

    # face conversion pointer table -> 4 entries
    wt = d2.find(struct.pack('<13h', 6, 6, 5, 5, 4, 4, 13, 3, 9, 3, 12, 3, -1))
    ptab = [o for so, o, ty, to, tt, *_ in fix if so == 2 and to == 2 and tt == wt]
    assert len(ptab) == 1
    ptab = ptab[0]
    old = [p.target(2, ptab + 4 * k)[1] for k in range(3)]
    users = [o for so, o, ty, to, tt, *_ in fix if so == 1 and to == 2 and tt == ptab]
    assert len(users) == 4, users
    blond = area.add(struct.pack('<13h', *BLOND))
    newtab = area.add(b'\0' * 16)
    for k, toff in enumerate(old + [blond]):
        p.add_ptr(2, newtab + 4 * k, 2, toff)
    for o in users:
        p.retarget(1, o, 2, newtab)
        p.put(1, o, struct.pack('<I', newtab))

    face = one(rb'\x66\xC1\x2D....\x03\xA0....\x8B\x35....\x88\x46\x2F')
    copy = one(rb'\x66\xC7\x05....\x55\x01\xC7\x05........\xFF\x35....\xFF\x35....\xFF\x35....\xE8')
    c1 = one(rb'\x66\x81\x3D....\x84\x02\x75.\x66\xA1')
    c2 = one(rb'\x66\x81\x3D....\xB3\x03\x75.\x66\xA1')
    f1 = one(rb'\x66\xA1....\x66\xBB\xBA\x01\x66\x81\xEB\x55\x01\x66\xF7\xE3')
    f2 = one(rb'\x66\xA1....\x66\xBB\xE9\x02\x66\x81\xEB\x84\x02\x66\xF7\xE3')
    cyc = one(rb'\x66\x83\x05....\x01\x66\x83\x3D....\x03\x75')
    assert None not in (face, copy, c1, c2, f1, f2, cyc), (face, copy, c1, c2, f1, f2, cyc)
    icons = [m.start() for m in re.finditer(rb'\x66\x81\x05....\xBA\x00', d1, re.S)]
    assert len(icons) == 6, [hex(s) for s in icons]       # every `add word [Dx], 186`: a face icon (squad screens,
                                                          # SetMenuEntryPlayerFace, Edit Teams list and face button)

    D0 = t(face + 3)[1]
    assert t(face + 9) == (2, D0)
    A6 = t(face + 15)[1]
    A0 = A6 - 24
    D1 = t([s for s in icons if cyc < s < cyc + 0x80][0] + 3)[1]
    assert D1 == D0 + 4 and t(copy + 3) == (2, D0)
    face_off = d1[face + 21]                              # mov [esi+face], al: disp8
    t1tab = t(copy + 15)[1]
    assert t(copy + 11) == (2, A0)
    csc = rel(copy + 37)                                  # call ConvertSpriteColors
    # the call before `mov word [D0], 341`: mov byte [D0], 0 / mov [A1], team1 table / call ConvertColorTableToSkinColor
    m = re.compile(rb'\xC7\x05....(....)\xE8', re.S)
    sk = [x for x in m.finditer(d1, copy - 0x20, copy) if t(x.start() + 2) == (2, A0 + 4)]
    assert sk, 'ConvertColorTableToSkinColor call'
    skintab = rel(sk[-1].end() - 1)
    useind = t(c1 + 13)
    assert useind == t(c2 + 13)
    # team 2's colour table: the A1 load just after conv2's site (mov al, team2GoalieFaces / ... / mov [A1], table)
    t2 = [x for x in m.finditer(d1, c2, c2 + 0x40) if t(x.start() + 2) == (2, A0 + 4)]
    assert t2, 'team 2 colour table'
    t2tab = t(t2[0].start() + 6)[1]

    at = (at + 15) & ~15
    sym = {'D0': (2, D0), 'D1': (2, D1), 'A0': (2, A0), 'A6': (2, A6), 'SPRIDX': (2, spr), 'BUF': (2, bss),
           'USEIND': useind, 'T1TAB': (2, t1tab), 'T2TAB': (2, t2tab), 'SKINTAB': (1, skintab), 'CONVSPR': (1, csc),
           'FACE_': (0, FACE), 'FLAG_': (0, FLAG), 'FACE_OFF': (0, face_off), 'NEW1_': (0, NEW1), 'NEW2_': (0, NEW2),
           'SET_': (0, SET_BYTES)}
    code, cfix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)

    def hook(site, n, label, fixups):
        assert p.get(1, site, n) == d1[site:site + n], hex(site)
        for f in fixups:
            p.remove(1, site + f)
        p.put(1, site, b'\xE8' + struct.pack('<i', lab[label] - (site + 5)) + b'\x90' * (n - 5))

    hook(face + 8, 14, 'ig_face', (1, 7))                 # mov al,[D0] / mov esi,[A6] / mov [esi+face],al
    hook(copy, 9, 'copy_sets', (3,))                      # mov word [D0], 341
    hook(c1 + 11, 6, 'conv1', (2,))                       # mov ax, [useIndividualPlayerSkinColor]
    hook(c2 + 11, 6, 'conv2', (2,))
    hook(f1, 18, 'fo1', (2,))                             # mov ax,[D0] / mov bx,442 / sub bx,341 / mul bx
    hook(f2, 18, 'fo2', (2,))
    for s in icons:
        reg = t(s + 3)
        assert reg in ((2, D0), (2, D1)), (hex(s), reg)
        hook(s, 9, 'icon_d1' if reg == (2, D1) else 'icon_d0', (3,))
    assert p.get(1, cyc + 15, 1) == b'\x03'
    p.put(1, cyc + 15, b'\x04')                           # Edit Teams face button: 0..3
    print(f'exe: blond hair: face 3 (sets {NEW1}.., {NEW2}.., obj2+{bss:#x}; code obj1+{at:#x}, {len(code)} B)')
    return at + len(code)


# Real players of the mod's seasons with black skin and blond hair (face 3): only documented cases.
PLAYERS = {b'CARLOS VALDERRAMA'}       # blond afro all career long: Tampa Bay Mutiny (MLS 1997), Montpellier (1988-89)


def faces(data, header=True):
    """Team file bytes -> (bytes, players set to face 3): PLAYERS get bits 3-4 of positionAndFace = 11."""
    d, n, o0 = bytearray(data), 0, 2 if header else 0
    for k in range((len(d) - o0) // 684):
        for j in range(16):
            p = o0 + k * 684 + 76 + j * 38
            if bytes(d[p + 3:p + 26]).split(b'\0')[0] in PLAYERS:
                d[p + 26] |= 0x18
                n += 1
    return bytes(d), n
