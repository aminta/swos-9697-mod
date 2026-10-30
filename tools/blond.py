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
addresses it); with all three a bald light player plays as face 1. The bald sets are copies of the raw set with bald_shape's head (bald.c;
4.0.5 look E 'receding', Davide 30/10): the hair's top rows (raw colours 13 / 9 / 12) take raw skin 6, the sides and
the back keep the hair, then the team's face 2 / face 0 conversion. In BSS2 (the obj2 tail's end: nothing before it
moves). Menus: the bald face icons 1910 / 1911 (bald.c's bald_icon, the same look); goalkeepers keep their hair.
4.0.5 (Davide 30/10, 'bald players done properly'): two looks, byte 25 bit 1 = shaved (packs/bald-looks-2627.csv):
flags 2 / 3 receding dark / light (look E), 4 / 5 shaved dark / light (an oval head in one colour: black, or the NEW
pink tone - palette index 84, drawn by DrawSprite16Pixels' table, pal_setup / pal_write). copy_sets gives each team's
variants single-team set slots (1418, 1519, 1708, 1809, 1932: ORDER's priority, team 1 first) instead of the pairs
above; a variant without a slot falls back (shaved -> the team's receding set, light -> face 1, else the normal face).
Icons: receding 1910 / 1911, shaved 2033 / 2034. Under SWOS++ no bald look (Panchina's gate).
"""
import os
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
ICONBL = 1910                           # 4.0.5: the bald face icons (light, dark = + 1)
SCR_OFF = 2 * SET_BYTES                 # menunum's 1620..1707 (to 1909: spritesIndex's room ends at 2103)
BUF3_OFF = SCR_OFF + 0x1000             # 4.0.5: the fifth set slot's buffer
BSS2_SIZE = BUF3_OFF + SET_BYTES        # (patch.py: at the obj2 tail's end; + bald.c's .bss)
BALD_AT = 25                            # PlayerFile.field_19 (from the player record; positionAndFace = 26)
# 4.0.5 (Davide 30/10, 'bald players done properly'): the look of each bald variant as data (bald.c's L_* / D_* macros):
# shape 'E' (receding) or 'oval' (one colour, the face too), the skull's raw colour (7 = the variant's NEW palette tone,
# drawn by DrawSprite16Pixels' table; 6 / 5 / 4 skin, 3 black) and the half / EGA mode's colour for a 7.
LOOKS = {'receding': {'light': dict(shape='E', skull=6, ega=6), 'dark': dict(shape='E', skull=6, ega=6)},
         'shaved': {'light': dict(shape='oval', skull=7, ega=6), 'dark': dict(shape='oval', skull=6, ega=6)}}
TONES = {'light': (84, (240, 150, 120)), 'dark': (85, (70, 30, 10))}   # palette index (free in every pitch), RGB
# (Davide 30/10: the dark oval in the dark face's colour - raw 6, converted 4: head = face; index 85 stays spare). Variant flags (PlayerInfoHeader FLAG): 1 darkblond,
# 2 / 3 receding dark / light, 4 / 5 shaved dark / light; bald.c's look = (flag - 2) xor 1.
FLAGS = {2: ('receding', 'dark'), 3: ('receding', 'light'), 4: ('shaved', 'dark'), 5: ('shaved', 'light')}
NSLOT = 5                               # single-team set slots: NEW1 / + 101, NEW3 / + 101, SLOT5 (4.0.5)
SLOT5 = 1932                            # (after benchx's 1912..1931)
ICON3 = SLOT5 + 101                     # 2033 / 2034: the shaved face icons (light, dark)
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
    cmp byte [SPPMMI], 66h              ; 4.0.5: under SWOS++ (its code over SWOSMainMenuInit's first mov) no bald look:
    jne .s                              ; with the long bench its PLAY MATCH stalls (Panchina 30/10, harness probe)
    push edi                            ; bald: the player record's byte 25 (A5 -> record + 76 - 26 ..): bit 0 bald,
    mov edi, [A5]                       ; bit 1 shaved (4.0.5; bit 0 alone = receding)
    mov ah, [edi + 66h - 26 + BALD_AT_]
    pop edi
    test ah, 1
    jz .s
    mov byte [esi + FLAG_], 3           ; 3 receding light, 2 receding dark (also darkblond), + 2 shaved
    cmp al, 2
    jne .sh
    mov byte [esi + FLAG_], 2
.sh:
    test ah, 2
    jz .s
    add byte [esi + FLAG_], 2
.s:
    mov [esi + FACE_OFF], al
    push ecx                            ; (the variants each team needs: copy_sets allocates their sets; A4 -> the
    push edx                            ; team in the game, topTeamInGame = team 1)
    xor edx, edx
    cmp dword [A4], TOPTEAM
    setne dl
    movzx ecx, byte [esi + FLAG_]
    bts [NEEDT + edx * 4], ecx
    pop edx
    pop ecx
    ret

copy_sets:                              ; replaces mov word [D0], 341 (after InitInGamePlayer for all 32: NEEDT set)
    pushad                              ; 4.0.5: the variants each team needs (flag 1 darkblond, 2 / 3 receding
    xor eax, eax                        ; dark / light, 4 / 5 shaved dark / light) get single-team sets in the five
    mov [VBT], eax                      ; slots (SIDX: 1418, 1519, 1708, 1809, 1932), in ORDER's priority, team 1
    mov [VBT + 4], eax                  ; then team 2 for each flag; a variant without a slot falls back (fo)
    mov [VBT + 8], eax
    mov [VBT + 12], eax
    mov [VBT + 16], eax                 ; (VBT5)
    mov [SFL], eax
    mov byte [SFL + 4], 0
    xor ecx, ecx                        ; ecx = the next free slot
    xor ebx, ebx                        ; ebx = ORDER's position
.f:
    movzx edx, byte [ORDER + ebx]
    xor eax, eax                        ; eax = the team
.t:
    bt [NEEDT + eax * 4], edx
    jnc .nt
    cmp ecx, NSLOT_
    jae .nt
    mov [SFL + ecx], dl
    mov [STM + ecx], al
    push eax
    push ebx
    push ecx
    push edx
    mov byte [SHAPE], 0
    cmp dl, 2
    jb .ns0
    mov [SHAPE], dl                     ; (bald: the flag - bald.c's look)
.ns0:
    movzx ebp, word [SIDX + ecx * 2]
    cmp dl, 5
    je .v5
    lea esi, [VBT + eax * 8]
    mov [esi + edx * 2 - 2], bp         ; (VBT: per team, flags 1..4; flag 5 in VBT5)
    jmp .v4
.v5:
    mov [VBT5 + eax * 2], bp
.v4:
    mov edi, [SBUF + ecx * 4]
    imul edx, eax, 644 - 341
    add edx, 341                        ; (team 1's raw sets 341.., team 2's 644..)
    call .set
    pop edx
    pop ecx
    pop ebx
    pop eax
    inc ecx
.nt:
    inc eax
    cmp eax, 2
    jb .t
    inc ebx
    cmp ebx, 5
    jb .f
    mov byte [SHAPE], 0
    mov dword [NEEDT], 0
    mov dword [NEEDT + 4], 0
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

bald_shape:                             ; ebx = a copied raw sprite: its head reshaped by bald.c (bald_c), SHAPE = the
    cmp word [ebx + 14], 1              ; flag (2..5: bald.c's look (flag - 2) xor 1: 0 receding light, 1 receding
    jne .r                              ; dark, 2 shaved light, 3 shaved dark)
    pushad
    xor eax, eax
    cmp word [SETUPDAT], -1             ; (the half / EGA mode: no palette table, no new tone)
    sete al
    push eax                            ; ega
    movzx eax, byte [SHAPE]
    sub eax, 2
    xor eax, 1
    push eax                            ; look
    movzx eax, word [ebx + 12]
    push eax                            ; lines
    push dword [ebx]                    ; pixels
    call BALDC
    add esp, 16
    popad
.r:
    ret

pal_setup:                              ; 4.0.5 replaces DrawSprite16Pixels' mov bh, [g_deltaColor] (each `or bl, bh` of
    push eax                            ; its loops is `mov bl, [ebx]`): ebx = bald.c's table + the slot of the delta;
    mov ebx, [LUTP]                     ; a sprite of a set slot (data in SBUF[s] .. + SET_) drawn with delta 0 gets
    test ebx, ebx                       ; the slot of its flag's tone (LUTSL: 0 none, 3 light, 4 dark - nibble 7 ->
    jnz .t                              ; the tone's palette index)
    pushad
    call PALINIT
    popad
    mov ebx, [LUTP]
.t:
    movzx eax, byte [DELTA]
    test eax, eax
    jnz .d
    push ecx
    push edx
    mov edx, [A0]                       ; (the sprite data)
    xor ecx, ecx
.s:
    cmp byte [SFL + ecx], 0
    je .sn
    mov eax, [SBUF + ecx * 4]
    cmp edx, eax
    jb .sn
    add eax, SET_
    cmp edx, eax
    jae .sn
    movzx eax, byte [SFL + ecx]
    movzx eax, byte [LUTSL + eax]
    shl eax, 8
    add ebx, eax
    jmp .sx
.sn:
    inc ecx
    cmp ecx, NSLOT_
    jb .s
.sx:
    pop edx
    pop ecx
    jmp .x
.d:
    cmp al, 10h
    jne .e
    add ebx, 256
    jmp .x
.e:
    cmp al, 70h
    jne .o
    add ebx, 512
    jmp .x
.o:                                     ; (any other delta: slot 5 filled now)
    push ecx
    add ebx, 1280
    xor ecx, ecx
.f:
    mov ah, cl
    or ah, al
    mov [ebx + ecx], ah
    inc ecx
    cmp ecx, 16
    jb .f
    pop ecx
.x:
    pop eax
    ret

pal_write:                              ; 4.0.5 replaces InitGameRestoreTeams' mov esi, g_workingPalette (@@save_palette:
    mov byte [WPAL + TL_ * 3], TLR_     ; the working palette -> savedPalette, after the pitch type's colours): the
    mov byte [WPAL + TL_ * 3 + 1], TLG_ ; bald tones (6-bit) into indices that no pitch uses; GameLoop copies them to
    mov byte [WPAL + TL_ * 3 + 2], TLB_ ; the darkened upper half with the rest
    mov byte [WPAL + TD_ * 3], TDR_
    mov byte [WPAL + TD_ * 3 + 1], TDG_
    mov byte [WPAL + TD_ * 3 + 2], TDB_
    mov esi, WPAL
    ret

SHAPE: db 0
SIG: db 'BLDSLOT5'                      ; (harness variant_sets: SIG, SFL, STM, VBT, VBT5)
SFL: db 0, 0, 0, 0, 0                   ; per slot: its flag this match, 0 = free
STM: db 0, 0, 0, 0, 0                   ; per slot: its team (0 / 1)
align 2
VBT: dw 0, 0, 0, 0, 0, 0, 0, 0          ; per team (8 bytes): flags 1..4's first sprite this match, 0 = none
VBT5: dw 0, 0                           ; per team: flag 5's
SIDX: dw NEW1_, NEW1_ + 101, NEW3_, NEW3_ + 101, SLOT5_
FACEOF: db 0, FACE_, F2_, F3_, F4_, F5_ ; per flag: the face conversion table (darkblond 3; bald: face 2 / 0, or 5 / 4
                                        ; with a new tone: raw 13 -> 7, the tone's nibble)
LUTSL: db 0, 0, S2_, S3_, S4_, S5_      ; per flag: pal_init's table slot of its tone (0 none, 3 light, 4 dark)
ORDER: db 1, 5, 4, 3, 2                 ; slot priority: darkblond, shaved light / dark, receding light / dark
align 4
SBUF: dd BUF, BUF + SET_, BUF2, BUF2 + SET_, BUF3
NEEDT: dd 0, 0

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
    mov esi, 1
    mov edi, T2TAB
    call convp
    popad
    mov ax, [USEIND]
    ret
convp:                                  ; the team's slots: esi = team (0 / 1), edi = its colour table
    xor ebx, ebx
.l:
    movzx eax, byte [SFL + ebx]
    test eax, eax
    jz .n
    movzx edx, byte [STM + ebx]
    cmp edx, esi
    jne .n
    movzx eax, byte [FACEOF + eax]
    push eax
    movzx eax, word [SIDX + ebx * 2]
    push eax
    push edi
    call conv
.n:
    inc ebx
    cmp ebx, NSLOT_
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
    push esi
    mov ecx, -341
    xor esi, esi
    jmp fo
fo2:
    mov ebx, [A0 + 12]                  ; A3 -> player
    push ecx
    push esi
    mov ecx, -644
    mov esi, 1
fo:                                     ; ax = the player's set (first sprite) - the team's raw base
    movzx eax, byte [ebx + FLAG_]
    test eax, eax
    jz .norm
    call .vb
    jnz .ok
    cmp byte [ebx + FLAG_], 4           ; a shaved player without a slot: his receding set when the team has it
    jb .fb
    movzx eax, byte [ebx + FLAG_]
    sub eax, 2
    call .vb
    jnz .ok
.fb:
    movzx eax, byte [ebx + FLAG_]       ; light bald (3, 5) without sets: face 1 (the skin-coloured hair); dark and
    cmp eax, 3                          ; darkblond: the normal sets
    je .f1
    cmp eax, 5
    jne .norm
.f1:
    xor dx, dx
    mov ax, 101
    jmp .r
.ok:
    xor dx, dx
    add ax, cx
    jmp .r
.norm:
    mov ax, [D0]
    mov bx, 101
    mul bx
.r:
    pop esi
    pop ecx
    ret
.vb:                                    ; eax = flag -> eax = the team's (esi) set of it, ZF: none (edx changed)
    cmp eax, 5
    je .v5
    lea edx, [esi * 8]
    movzx eax, word [VBT + edx + eax * 2 - 2]
    test eax, eax
    ret
.v5:
    movzx eax, word [VBT5 + esi * 2]
    test eax, eax
    ret

icon_d0:                                ; replaces add word [D0], 186 (face icon; A6 -> the player record)
    add word [D0], 186
    call build_icon
    push edx
    push eax
    mov edx, D0
    mov eax, [A6]
    jmp bicon
icon_d1:
    add word [D1], 186
    call build_icon
    push edx
    push eax
    mov edx, D1
    mov eax, [A6]
    jmp bicon
icon_d1a:                               ; (the Edit Teams face button: A0 -> the player record)
    add word [D1], 186
    call build_icon
    push edx
    push eax
    mov edx, D1
    mov eax, [A0]
bicon:                                  ; 4.0.5: a bald player (record byte 25 bit 0; bit 1 shaved) gets the bald icon of
    test eax, eax                       ; his look and skin: ICONS = receding light / dark (1910 / 1911, from 186 /
    jz .r                               ; 188), shaved light / dark (ICON3 / + 1)
    cmp byte [SPPMMI], 66h              ; (4.0.5: not under SWOS++, as the match sets above)
    jne .r
    test byte [eax + 66h - 26 + BALD_AT_], 1
    jz .r
    call build_bald
    push ebx
    xor ebx, ebx
    cmp word [edx], 186 + 2
    setae bl                            ; (faces 2 / 3: dark)
    test byte [eax + 66h - 26 + BALD_AT_], 2
    jz .i
    add ebx, 2
.i:
    movzx ebx, word [ICONS + ebx * 2]
    mov [edx], bx
    pop ebx
.r:
    pop eax
    pop edx
    ret
build_bald:                             ; the four bald icons: the face icon (186 light, 188 dark) with its head by
    pushad                              ; bald.c's bald_icon (look 0..3 as bald_c's)
    xor ebp, ebp
.l:
    mov ebx, ebp
    and ebx, 1
    lea ebx, [186 + ebx * 2]
    mov edi, ebp
    shl edi, 8
    add edi, ICONBUF
    call .one
    inc ebp
    cmp ebp, 4
    jb .l
    popad
    ret
.one:                                   ; ebx = the source icon, ebp = the look, edi -> buffer
    mov esi, [SPRIDX + ebx * 4]
    test esi, esi
    jz .x
    cmp word [esi + 14], 1
    jne .x
    movzx ecx, word [esi + 12]
    cmp ecx, 16
    ja .x
    xor eax, eax
.h:
    mov edx, [esi + eax]
    mov [edi + eax], edx
    add eax, 4
    cmp eax, 24
    jb .h
    lea eax, [edi + 24]
    mov [edi], eax
    mov ax, [ICONS + ebp * 2]
    mov [edi + 22], ax
    movzx eax, ax
    mov [SPRIDX + eax * 4], edi
    mov esi, [esi]
    shl ecx, 3
    xor eax, eax
.p:
    mov dl, [esi + eax]
    mov [edi + 24 + eax], dl
    inc eax
    cmp eax, ecx
    jb .p
    shr ecx, 3                          ; the head: bald.c (bald_icon)
    push ebp
    push ecx
    lea eax, [edi + 24]
    push eax
    call BALDI
    add esp, 12
.x:
    ret
ICONS: dw ICONBL_, ICONBL_ + 1, ICON3_, ICON3_ + 1

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
    # 4.0.5 the new tones: face 0 / face 2 with raw 13 -> 7 (bald.c paints a tone skull in raw 13; nibble 7 is drawn
    # as the tone by DrawSprite16Pixels' table - raw 7 itself is a kit colour, 7 never comes out of a conversion else)
    tone = []
    for f in (0, 2):
        w = list(struct.unpack('<13h', d2[old[f]:old[f] + 26]))
        assert w[6] == 13 and w[-1] == -1, w
        w[7] = 7
        tone.append(area.add(struct.pack('<13h', *w)))
    newtab = area.add(b'\0' * 24)
    for k, toff in enumerate(old + [blond] + tone):
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
    mmi = [m.start() for m in re.finditer(rb'\x66\xc7\x05.{4}\xff\xff\xe8.{4}\xe8.{4}\xeb\x00', d1, re.S)]
    assert len(mmi) == 2 and mmi[0] < 0x20000, [hex(x) for x in mmi]   # (SWOSMainMenuInit's `mov currentTeamNumber, -1`
                                                                       # is the first: SWOS++ makes its 66h a B8h)
    sym = {'SPPMMI': (1, mmi[0]), 'D0': (2, D0), 'D1': (2, D1), 'A0': (2, A0), 'A6': (2, A6), 'SPRIDX': (2, spr), 'BUF': (2, bss),
           'A5': (2, A0 + 20), 'BUF2': (2, bss2), 'BALD_AT_': (0, BALD_AT), 'NEW3_': (0, NEW3), 'ICONBL_': (0, ICONBL), 'ICONBUF': (2, bss2 + SCR_OFF + 0x800), 'SCR': (2, bss2 + SCR_OFF), 'MARK': (2, bss2 + SCR_OFF + 0x200),
           'USEIND': useind, 'T1TAB': (2, t1tab), 'T2TAB': (2, t2tab), 'SKINTAB': (1, skintab), 'CONVSPR': (1, csc),
           'FACE_': (0, FACE), 'FLAG_': (0, FLAG), 'FACE_OFF': (0, face_off), 'NEW1_': (0, NEW1), 'NEW2_': (0, NEW2),
           'SET_': (0, SET_BYTES), 'NSLOT_': (0, NSLOT), 'SLOT5_': (0, SLOT5), 'ICON3_': (0, ICON3),
           'BUF3': (2, bss2 + BUF3_OFF), 'A4': (2, A0 + 16), 'TOPTEAM': topteam(p),
           **{f'F{f}_': (0, (5 if skin == 'dark' else 4) if LOOKS[look][skin]['skull'] == 7 else (2 if skin == 'dark' else 0))
              for f, (look, skin) in FLAGS.items()},
           **{f'S{f}_': (0, (4 if skin == 'dark' else 3) if LOOKS[look][skin]['skull'] == 7 else 0)
              for f, (look, skin) in FLAGS.items()}}
    assert SLOT5 >= blond_free() and ICON3 + 2 <= 2103, 'spritesIndex map'
    import cobj                                           # 4.0.5: bald.c (the bald heads) first, the glue after it
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bald.c'), look_flags())
    csyms, cend, cbss = cobj.link(p, obj, at, (2, bss2 + SCR_OFF), limit=at + 0x900)
    assert cbss <= BUF3_OFF - SCR_OFF, hex(cbss)
    sym['BALDC'] = csyms['bald_c']
    sym['BALDI'] = csyms['bald_icon']
    sym['PALINIT'], sym['LUTP'] = csyms['pal_init'], csyms['LUTP']
    # 4.0.5 the palette route: DrawSprite16Pixels (mov bh, [g_deltaColor] / cmp word [spriteClipped], -1 / jz) and
    # InitGameRestoreTeams' working palette -> savedPalette copy (GameLoop copies it back: the reverse pair)
    bh = one(rb'\x8a\x3d....\x66\x83\x3d....\xff\x0f\x84')
    ors = [m.start() for m in re.finditer(rb'\x0a\xdf\x88', d1[bh:bh + 0x200])]
    assert bh is not None and len(ors) == 20, (bh, len(ors))
    cp = [(m.start(), t(m.start() + 1), t(m.start() + 6)) for m in
          re.finditer(rb'\xbe....\xbf....\xb9\x00\x03\x00\x00\xf3\xa4', d1, re.S)]
    sv = [o for o, a, b in cp if any(a2 == b and b2 == a for _, a2, b2 in cp)]   # (working <-> savedPalette)
    src = [a for _, a, b in cp]
    sv = [o for o in sv if src.count(t(o + 1)) > 1]       # (the working palette: also copied to the menus' one)
    assert len(sv) == 1, [hex(o) for o in sv]
    wpal = t(sv[0] + 1)
    (tl, rgbl), (td, rgbd) = TONES['light'], TONES['dark']
    sym.update(DELTA=t(bh + 2), WPAL=wpal, SETUPDAT=SETUPDAT(p), SET2_=(0, 2 * SET_BYTES), TL_=(0, tl), TD_=(0, td),
               **{f'T{v}{c}_': (0, x >> 2) for v, rgb in (('L', rgbl), ('D', rgbd)) for c, x in zip('RGB', rgb)})
    print(f'exe: bald.c obj1+{at:#x}..{cend:#x}, .bss {cbss} B')
    at = (cend + 15) & ~15
    code, cfix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    UNCH['sym'].update(SFL=(1, lab['SFL']), SIDX=(1, lab['SIDX']), NSLOT_=(0, NSLOT))
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
    hook(bh, 6, 'pal_setup', (2,))                        # mov bh, [g_deltaColor]
    for o in ors:
        assert p.get(1, bh + o, 2) == b'\x0a\xdf'
        p.put(1, bh + o, b'\x8a\x1b')                     # or bl, bh -> mov bl, [ebx]
    hook(sv[0], 5, 'pal_write', (1,))                     # mov esi, g_workingPalette
    hook(copy, 9, 'copy_sets', (3,))                      # mov word [D0], 341
    hook(c1 + 11, 6, 'conv1', (2,))                       # mov ax, [useIndividualPlayerSkinColor]
    hook(c2 + 11, 6, 'conv2', (2,))
    hook(f1, 18, 'fo1', (2,))                             # mov ax,[D0] / mov bx,442 / sub bx,341 / mul bx
    hook(f2, 18, 'fo2', (2,))
    for s in icons:
        reg = t(s + 3)
        assert reg in ((2, D0), (2, D1)), (hex(s), reg)
        lab_ = 'icon_d0' if reg == (2, D0) else 'icon_d1a' if cyc < s < cyc + 0x80 else 'icon_d1'
        hook(s, 9, lab_, (3,))
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
.l:                                     ; 4.0.5: the set slots in use this match (copy_sets' SFL), 101 sprites each
    cmp byte [SFL + ebx], 0
    je .n
    mov dword [D3], 0
    movzx eax, word [SIDX + ebx * 2]
    mov [D0], eax
    add eax, 101
    mov [D1], eax
    call USP
.n:
    inc ebx
    cmp ebx, NSLOT_
    jb .l
    popad
    ret

"""


def look_flags():
    """bald.c's -D flags from LOOKS / TONES: look 0 receding light, 1 receding dark, 2 shaved light, 3 shaved dark."""
    f = []
    for k, (look, skin) in enumerate((('receding', 'light'), ('receding', 'dark'), ('shaved', 'light'), ('shaved', 'dark'))):
        lk = LOOKS[look][skin]
        f += [f'-DSH{k}={dict(E=0, oval=1)[lk["shape"]]}', f'-DSK{k}={lk["skull"]}', f'-DEG{k}={lk["ega"]}']
    return f + [f'-DTONE_L={TONES["light"][0]}', f'-DTONE_D={TONES["dark"][0]}']


def blond_free():
    """The first spritesIndex entry after benchx's names (1912..1931)."""
    return ICONBL + 2 + 20


def topteam(p):
    """topTeamInGame (obj2): InitializeInGameTeamsAndStartGame's mov A6, team1AppPercent / mov A4, topTeamInGame (the
    first of the two such pairs; the second is bottomTeamInGame)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    pat = rb'\xc7\x05' + re.escape(struct.pack('<I', a0 + 24)) + rb'....\xc7\x05' + re.escape(struct.pack('<I', a0 + 16))
    m = [x.start() for x in re.finditer(pat, d1, re.S)]
    pr = [(a, b) for a, b in zip(m, m[1:]) if b - a < 0x400]          # (the two teams' init, close together)
    assert len(pr) == 1, [hex(x) for x in m]
    top, bot = p.target(1, pr[0][0] + 16), p.target(1, pr[0][1] + 16)
    assert top != bot and top[0] == 2, (top, bot)
    return top


def SETUPDAT(p):
    """setupDatBuffer (obj2): its first word = EGA_graphics in the match, -1 = the half mode (fullgfx.PAT)."""
    import fullgfx
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(fullgfx.PAT, d1, re.S)]
    if not m:                                             # (fullgfx already applied: its `ja` became `jmp`)
        m = [x.start() for x in re.finditer(fullgfx.PAT.replace(rb'\x77', rb'\xeb'), d1, re.S)]
    assert len(m) == 1, m
    return p.target(1, m[0] + 3)


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


# Real bald players of the World 2026-27 (4.0.3 by hand; 4.0.5: packs/bald-looks-2627.csv, Dati coppe from photos,
# confirmed by Davide 30/10 - country, club, name as in the team files, look shaved / receding, face light / dark): byte 25
# bit 0 = bald, bit 1 = shaved (bit 0 alone = receding). Names are unique in the list (the data has no hair field).
BALD_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'packs', 'bald-looks-2627.csv')


def _bald():
    import csv
    rows = list(csv.DictReader(open(BALD_CSV, encoding='utf-8')))
    out = {r['name'].encode('latin-1'): 1 | (2 if r['look'] == 'shaved' else 0) for r in rows}
    assert len(out) == len(rows) and all(len(n) <= 21 for n in out), 'bald list: duplicate or long names'
    return out


BALD = _bald()                          # name -> byte 25 bits


def bald(player):
    """A 38-byte player record with byte 25's bald bits when he is in BALD (the extras' files: xtra.build)."""
    name = bytes(player[3:25]).split(b'\0')[0]
    if name not in BALD:
        return bytes(player)
    return bytes(player[:BALD_AT]) + bytes((player[BALD_AT] | BALD[name],)) + bytes(player[BALD_AT + 1:])


def faces(data, header=True):
    """Team file bytes -> (bytes, players set to face 3): PLAYERS get bits 3-4 of positionAndFace = 11; BALD get
    byte 25's bald bits (names of at most 21 letters: byte 25 stays after the name's 0)."""
    d, n, o0 = bytearray(data), 0, 2 if header else 0
    for k in range((len(d) - o0) // 684):
        for j in range(16):
            p = o0 + k * 684 + 76 + j * 38
            name = bytes(d[p + 3:p + 26]).split(b'\0')[0]
            if name in PLAYERS:
                d[p + 26] |= 0x18
                n += 1
            if name in BALD:
                d[p + BALD_AT] |= BALD[name]
    return bytes(d), n
