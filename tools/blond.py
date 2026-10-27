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

4.0.3 bald players: PlayerFile byte 25 (field_19, after the 22-byte name; the game never reads it) bit 0 = bald.
Older versions ignore it (the player keeps his hair). A bald dark player (face 2 / 3) gets flag 2, a bald light one
(face 0 / 1) flag 3; InitInGamePlayer (ig_face) runs for all 32 before ConvertColorsAndTextSprites, so copy_sets
knows the variants of the match (NEED) and gives the first two present (darkblond, bald dark, bald light, in that
order) the pairs of sets 1418 / 1519 and 1708 / 1809 (spritesIndex's room ends at 2103 and it cannot move: SWOS++
addresses it); with all three a bald light player plays as face 1. The bald sets are copies of the raw set with bald_shape's head (Davide's
look A, 27/10): the hair (raw colours 13 / 9 / 12) loses its outer ring, the rest takes the raw skin colours (6 on top,
4 at the sides, 5 inside), then the team's face 2 / face 0 conversion. In BSS2 (the obj2 tail's end: nothing before
it moves). Menus keep the file's face icon; goalkeepers keep their hair.
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
NEW3 = 1708                             # 4.0.3: the second pair of variant sets (team 1, team 2 = + 101), after
SCR_OFF = 2 * SET_BYTES                 # menunum's 1620..1707 (to 1909: spritesIndex's room ends at 2103)
BSS2_SIZE = SCR_OFF + 0x400             # (patch.py: at the obj2 tail's end; + bald_shape's scratch)
BALD_AT = 25                            # PlayerFile.field_19 (from the player record; positionAndFace = 26)
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
    push edi                            ; 4.0.3: bald (the player record's byte 25 bit 0, A5 -> record + 76 - 26 ..)
    mov edi, [A5]
    test byte [edi + 66h - 26 + BALD_AT_], 1
    pop edi
    jz .s
    cmp al, 2
    je .d
    mov byte [esi + FLAG_], 3           ; light: the bald light sets
    jmp .s
.d:
    mov byte [esi + FLAG_], 2           ; dark (also darkblond): the bald dark sets
.s:
    mov [esi + FACE_OFF], al
    push ecx                            ; (the variants this match needs: copy_sets allocates their sets)
    movzx ecx, byte [esi + FLAG_]
    bts [NEED], ecx
    pop ecx
    ret

copy_sets:                              ; replaces mov word [D0], 341 (after InitInGamePlayer for all 32: NEED set)
    pushad                              ; 4.0.3: the variants present (flag 1 darkblond, 2 bald dark, 3 bald light,
    mov dword [VB], 0                   ; in that order) get the two pairs of sets, 1418 / 1519 and 1708 / 1809; a
    mov dword [VB + 4], 0               ; third one gets none (fo: bald light -> face 1)
    mov word [PV], 0
    xor ecx, ecx
    mov edx, 1
.v:
    bt [NEED], edx
    jnc .nx
    cmp ecx, 2
    jae .nx
    mov [PV + ecx], dl
    mov ax, [PIDX + ecx * 2]
    mov [VB + edx * 2], ax
    push ecx
    push edx
    mov byte [SHAPE], 0
    cmp dl, 2
    jb .ns0
    mov byte [SHAPE], 1                 ; (bald: look A)
.ns0:
    movzx ebp, word [PIDX + ecx * 2]
    mov edi, [PBUF + ecx * 4]
    push ebp
    push edi
    mov edx, 341
    call .set
    pop edi
    pop ebp
    add ebp, 101
    add edi, SET_
    mov edx, 644
    call .set
    pop edx
    pop ecx
    inc ecx
.nx:
    inc edx
    cmp edx, 4
    jb .v
    mov byte [SHAPE], 0
    mov dword [NEED], 0
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
    cmp byte [SHAPE], 0
    je .ns
    pushad
    mov ebx, [SPRIDX + ebp * 4]
    call bald_shape
    popad
.ns:
    inc edx
    inc ebp
    pop ecx
    dec ecx
    jnz .spr
    ret

bald_shape:                             ; ebx = a copied raw sprite (1 quad wide): look A on its hair (13 / 9 / 12)
    cmp word [ebx + 14], 1
    jne .r
    movzx ecx, word [ebx + 12]
    test ecx, ecx
    jz .r
    cmp ecx, 24
    ja .r
    shl ecx, 4                          ; ecx = pixels
    mov esi, [ebx]
    xor edx, edx
.u:                                     ; unpack: SCR[2j] = high nibble, SCR[2j+1] = low
    mov al, [esi + edx]
    mov ah, al
    shr al, 4
    and ah, 0Fh
    mov [SCR + edx * 2], al
    mov [SCR + edx * 2 + 1], ah
    inc edx
    lea eax, [edx * 2]
    cmp eax, ecx
    jb .u
    xor edx, edx                        ; pass 1: MARK = hair with a transparent / outside 4-neighbour
.p1:
    mov byte [MARK + edx], 0
    mov al, [SCR + edx]
    call .hair
    jne .n1
    mov eax, edx
    sub eax, 16
    jb .d1
    cmp byte [SCR + eax], 0
    je .d1
    lea eax, [edx + 16]
    cmp eax, ecx
    jae .d1
    cmp byte [SCR + eax], 0
    je .d1
    test dl, 0Fh
    jz .d1
    cmp byte [SCR + edx - 1], 0
    je .d1
    mov al, dl
    and al, 0Fh
    cmp al, 0Fh
    je .d1
    cmp byte [SCR + edx + 1], 0
    jne .n1
.d1:
    mov byte [MARK + edx], 1
.n1:
    inc edx
    cmp edx, ecx
    jb .p1
    xor edx, edx                        ; pass 2: drop them
.p2:
    cmp byte [MARK + edx], 0
    je .n2
    mov byte [SCR + edx], 0
.n2:
    inc edx
    cmp edx, ecx
    jb .p2
    xor edx, edx                        ; pass 3: the rest of the hair -> skin: 6 on top, 4 at the sides, 5 inside
.p3:
    mov al, [SCR + edx]
    call .hair
    jne .n3
    mov bl, 6
    cmp edx, 16
    jb .w3
    cmp byte [SCR + edx - 16], 0
    je .w3
    mov bl, 4
    test dl, 0Fh
    jz .w3
    cmp byte [SCR + edx - 1], 0
    je .w3
    mov al, dl
    and al, 0Fh
    cmp al, 0Fh
    je .w3
    cmp byte [SCR + edx + 1], 0
    je .w3
    mov bl, 5
.w3:
    mov [SCR + edx], bl
.n3:
    inc edx
    cmp edx, ecx
    jb .p3
    xor edx, edx                        ; repack
.k:
    mov al, [SCR + edx * 2]
    shl al, 4
    or al, [SCR + edx * 2 + 1]
    mov [esi + edx], al
    inc edx
    lea eax, [edx * 2]
    cmp eax, ecx
    jb .k
.r:
    ret
.hair:                                  ; ZF = 1 when al is a raw hair colour
    cmp al, 13
    je .h
    cmp al, 9
    je .h
    cmp al, 12
.h:
    ret

SHAPE: db 0
PV: db 0, 0                             ; the variant (flag) in each pair this match, 0 = none
FACEOF: db 0, FACE_, 2, 0               ; per flag: the conversion table (darkblond 3, bald dark 2, bald light 0)
align 2
PIDX: dw NEW1_, NEW3_                   ; each pair's team 1 sets (team 2 = + 101)
VB: dw 0, 0, 0, 0                       ; per flag: its team 1 first sprite this match, 0 = none
align 4
PBUF: dd BUF, BUF2
NEED: dd 0

conv1:                                  ; replaces mov ax, [useIndividualPlayerSkinColor] before team 1's goalkeepers
    pushad
    xor esi, esi
    mov edi, T1TAB
    call convp
    popad
    mov ax, [USEIND]
    ret
conv2:
    pushad
    mov esi, 101
    mov edi, T2TAB
    call convp
    popad
    mov ax, [USEIND]
    ret
convp:                                  ; the pairs in use: esi = team offset (0 / 101), edi = colour table
    xor ebx, ebx
.l:
    movzx eax, byte [PV + ebx]
    test eax, eax
    jz .n
    movzx eax, byte [FACEOF + eax]
    push eax
    movzx eax, word [PIDX + ebx * 2]
    add eax, esi
    push eax
    push edi
    call conv
.n:
    inc ebx
    cmp ebx, 2
    jb .l
    ret
conv:                                   ; [esp+4] colour table, [esp+8] first new sprite, [esp+12] face table index
    cmp word [USEIND], 0                ; one face for the whole team: the set is not used
    je .out
    pushad
    mov ebx, [esp + 36]
    mov eax, [esp + 44]
    mov [D0], al
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
    ret 12

fo1:                                    ; replaces mov ax, [D0] / mov bx, 442 / sub bx, 341 / mul bx (team 1 player)
    mov ebx, [A0 + 8]                   ; A2 -> player
    push ecx
    mov ecx, -341
    jmp fo
fo2:
    mov ebx, [A0 + 12]                  ; A3 -> player
    push ecx
    mov ecx, 101 - 644
fo:
    xor dx, dx
    movzx eax, byte [ebx + FLAG_]
    test eax, eax
    jz .norm
    mov ax, [VB + eax * 2]              ; 4.0.3: the flag's sets this match
    test ax, ax
    jz .fb
    add ax, cx
    jmp .r
.fb:
    cmp byte [ebx + FLAG_], 3           ; bald light without sets (all three variants in the match): face 1
    jne .norm
    mov ax, 101
    jmp .r
.norm:
    mov ax, [D0]
    mov bx, 101
    mul bx
.r:
    pop ecx
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


def patch(p, area, at, bss, spr, bss2):
    """Code at obj1:at, sets at obj2:bss (BSS_SIZE zero bytes) and obj2:bss2 (BSS2_SIZE, bald dark), spr = spritesIndex
    (obj2). Returns the code end."""
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
    un = one(rb'\xC7\x05....\x1F\x01\x00\x00\xC7\x05....\x33\x01\x00\x00\xE8....\xC7\x05....\x35\x01\x00\x00\xE8')
    assert None not in (face, copy, c1, c2, f1, f2, cyc, un), (face, copy, c1, c2, f1, f2, cyc, un)
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

    usp, utz = rel(un + 20), rel(un + 35)                  # InitGameRestoreTeams: mov D0, 287 / mov D1, 307 /
    assert d1[usp:usp + 3] == b'\x66\xA1' + d1[usp + 2:usp + 3]   # call UnchainSprites / mov D0, 309 / call ..TilZero
    d3 = t(usp + 8)                                       # UnchainSprites: mov ax, word [D0] / mov word [D3], ax
    assert t(usp + 2) == (2, D0) and d3 == (2, D0 + 12), (t(usp + 2), d3)
    at = (at + 15) & ~15
    UNCH.update(site=un + 35, sym={'D0': (2, D0), 'D1': (2, D1), 'D3': d3, 'USP': (1, usp), 'UTZ': (1, utz),
                                   'NEW1_': (0, NEW1), 'NEW2_': (0, NEW2)})
    assert t(face - 0x16 + 2) == (2, A0 + 20), t(face - 0x16 + 2)   # (mov esi, [A5] / mov al, [esi+66h] before it)
    sym = {'D0': (2, D0), 'D1': (2, D1), 'A0': (2, A0), 'A6': (2, A6), 'SPRIDX': (2, spr), 'BUF': (2, bss),
           'A5': (2, A0 + 20), 'BUF2': (2, bss2), 'BALD_AT_': (0, BALD_AT), 'NEW3_': (0, NEW3), 'SCR': (2, bss2 + SCR_OFF), 'MARK': (2, bss2 + SCR_OFF + 0x200),
           'USEIND': useind, 'T1TAB': (2, t1tab), 'T2TAB': (2, t2tab), 'SKINTAB': (1, skintab), 'CONVSPR': (1, csc),
           'FACE_': (0, FACE), 'FLAG_': (0, FLAG), 'FACE_OFF': (0, face_off), 'NEW1_': (0, NEW1), 'NEW2_': (0, NEW2),
           'SET_': (0, SET_BYTES)}
    code, cfix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    UNCH['sym'].update(PV=(1, lab['PV']), PIDX=(1, lab['PIDX']))
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


UNCH = {}
UNCH_ASM = r"""
unch:                                   ; replaces InitGameRestoreTeams' call UnchainSpritesTilZero (half / EGA mode
    call UTZ                            ; only: sprites 309.. to the first empty index entry go planar). The sets
    pushad                              ; variant sets lie past the shirt numbers' entries (empty until built): they
    xor ebx, ebx                        ; stayed chunky and the EGA drawing made a block of them (MALEN, 4.0.2).
.l:                                     ; 4.0.3: the pairs in use this match (copy_sets' PV), 202 sprites each
    cmp byte [PV + ebx], 0
    je .n
    mov dword [D3], 0
    movzx eax, word [PIDX + ebx * 2]
    mov [D0], eax
    add eax, 202
    mov [D1], eax
    call USP
.n:
    inc ebx
    cmp ebx, 2
    jb .l
    popad
    ret

"""


def unch_patch(p, at):
    """The half / EGA mode's unchaining of NEW1 / NEW2 (UNCH_ASM) at obj1:at (after patch()). Returns the end."""
    code, fix = nasmcave.assemble(UNCH_ASM, at, UNCH['sym'])
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    site = UNCH['site']
    assert p.get(1, site, 1) == b'\xE8'
    p.put(1, site + 1, struct.pack('<i', at - (site + 5)))
    print(f'exe: blond sets made planar in half / EGA mode (obj1+{at:#x}, {len(code)} B, call at obj1+{site:#x})')
    return at + len(code)


# Real players of the mod's seasons with black skin and blond hair (face 3): only documented cases.
PLAYERS = {b'CARLOS VALDERRAMA'}       # blond afro all career long: Tampa Bay Mutiny (MLS 1997), Montpellier (1988-89)


# 4.0.3: real bald (shaved-head) players of the World 2026-27, by hand (the data has no hair field; full names as in the
# team files, unique there): byte 25 bit 0. MALEN: darkblond in the data, bald in reality (the 4.0.2 MALEN report).
BALD = {b'DONYELL MALEN', b'ANTONIO RUDIGER', b'KALIDOU KOULIBALY', b'SERHOU GUIRASSY', b'MICHAIL ANTONIO', b'MOUSSA NIAKHATE',   # dark
        b'TIM REAM', b'NEMANJA MATIC', b'JOSIP ILICIC'}                                                                       # light


def bald(player):
    """A 38-byte player record with byte 25 bit 0 set when he is in BALD (the extras' files: xtra.build)."""
    name = bytes(player[3:25]).split(b'\0')[0]
    if name not in BALD:
        return bytes(player)
    assert len(name) <= 21, name
    return bytes(player[:BALD_AT]) + bytes((player[BALD_AT] | 1,)) + bytes(player[BALD_AT + 1:])


def faces(data, header=True):
    """Team file bytes -> (bytes, players set to face 3): PLAYERS get bits 3-4 of positionAndFace = 11; BALD get
    byte 25 bit 0 (names of at most 21 letters: byte 25 stays after the name's 0)."""
    d, n, o0 = bytearray(data), 0, 2 if header else 0
    for k in range((len(d) - o0) // 684):
        for j in range(16):
            p = o0 + k * 684 + 76 + j * 38
            name = bytes(d[p + 3:p + 26]).split(b'\0')[0]
            if name in PLAYERS:
                d[p + 26] |= 0x18
                n += 1
            if name in BALD:
                assert len(name) <= 21, name
                d[p + BALD_AT] |= 1
    return bytes(d), n
