"""Shirt numbers above 16 (3.2.5, Marco): the real number over the controlled / booked player.

The game draws the number over the controlled player (UpdateControlledPlayerNumbers) and over the booked player
(UpdateBookedPlayerNumberSprite) as one sprite, SPR_CORNER_FLAG_FRAME_3 (1187) + shirt number, and BENCH.DAT has
number sprites for 1..16 only: 17 and up picked other sprites (17 the player mark, 18-19 goal parts, 20 a grid, 21+
the replay frames), seen in matches of teams with edited numbers (a tall column of sprites, a green bar next to the
player).

Both sites read `mov word [D0], 1187 / mov ax, [D1] / add [D0], ax / mov ax, [D0]`: the `add` (7 bytes, an absolute
operand with its fixup) becomes `call num_sprite; nop; nop`, the `mov ax, [D0]` (6 bytes) `call fix_d0; nop`:
- 1..16: as the game (1187 + number);
- 17..99: sprite NEWBASE + number - 17, built once by build_numbers the first time one is needed in a match (the
  bench sprites are loaded then): two digits side by side, made from the game's own digit sprites (2..9 as they are,
  the narrow 1 and the 0 cut from the "10" sprite, as the game writes 10..16), 1 pixel apart, centred like 10..16;
- SWOS++ (3.2.6; 3.2.5 hid the booked player's number under it, Marco): its FixPlayerBooking adds 9000 to 0 and 17+
  before the booked player's site, and its own hook replaces our `add` at the controlled player's site
  (DrawControlledPlayerNumbers+0x184) with the same mark; its DrawSprites hook then prints any sprite over 9000 itself.
  num_sprite and fix_d0 (which SWOS++ does not overwrite) turn 9000 + 17..99 into our sprites, so no sprite number
  over 9000 is left for those (one less thing that can reach a drawing path SWOS++ does not hook); 0 and 100+ keep
  SWOS++'s mark;
- anything else (0, 100+, or the 16-colour EGA mode, whose sprites have another layout): no sprite (-1); mkseason
  renumbers pack players outside 1..99, so only teams edited by the players can meet this.
In memory a game sprite is a 24-byte SpriteGraphics header + 4-bit pixels, 2 per byte, high nibble first, wquads * 8
bytes per line (DrawSprite16Pixels); the digits are 1 quad (16 pixels) wide, so are the new numbers (at most 7 pixels).
The new sprites live in a zero-filled tail of obj2 (BSS_SIZE); their pointers extend spritesIndex (the 5340-byte copy
of sprite.dat, 1335 entries) into the 3072 bytes after it, a register save stack used only by two routines that
nothing calls (cseg_9A9E1 / cseg_9A9FD: no call, no pointer; checked in all four exes).
"""
import re

import nasmcave

NEWBASE = 1335                  # first new sprite index (spritesIndex has 1335 entries: 1334 + the 0 end mark)
LABELS = {}                     # after patch(): obj1 offsets of build_numbers, CUR_BUF/BASE/NEW; EGA, SPRIDX (obj2)
BSS_SIZE = 0x3000               # flag + digit table (256 B) + 83 sprites x 96 B (header 24 + 8 lines x 8 B)

ASM = r"""
num_sprite:                             ; replaces `add [D0], ax`: ax = shirt number (sign-extended), [D0] = 1187
    cmp ax, 9000                        ; SWOS++'s FixPlayerBooking marks 0 and 17+ as 9000 + number
    jae .swospp
    call pick
    mov [D0], ax
    ret
.swospp:
    push eax
    sub ax, 9000
    call pick
    cmp ax, -1
    je .keep
    add esp, 4
    mov [D0], ax
    ret
.keep:                                  ; 0, 100+: SWOS++ draws them itself (its DrawSprites hook)
    pop eax
    add [D0], ax
    ret

fix_d0:                                 ; replaces `mov ax, [D0]` after it: SWOS++'s own hook of the controlled
    mov ax, [D0]                        ; player's site (DrawControlledPlayerNumbers+0x184) leaves 9000 + 1187 + n
    cmp ax, 9000 + 1187 + 17
    jb .r
    cmp ax, 9000 + 1187 + 99
    ja .r
    sub ax, 9000 + 1187
    call pick
    mov [D0], ax
.r:
    ret

pick:                                   ; ax = shirt number -> ax = its sprite, or -1 (none)
    cmp ax, 1
    jl .none
    cmp ax, 16
    jg .big
    add ax, 1187
    ret
.big:
    cmp ax, 99
    jg .none
    cmp word [EGA], -1                  ; 16-colour mode: other sprite layout
    je .none
    cmp byte [NUMBUF], 0
    jne .built
    mov dword [CUR_BUF], NUMBUF         ; the match set: digits 1187 + n, "10" = 1197, new sprites NEWBASE..
    mov dword [CUR_BASE], 1187
    mov dword [CUR_NEW], NEWBASE_
    mov dword [CUR_FIRST], 17
    mov dword [CUR_MENU], 0
    call build_numbers
.built:
    cmp byte [NUMBUF], 1
    jne .none
    add ax, NEWBASE_ - 17
    ret
.none:
    mov ax, -1                          ; no sprite: the number is not drawn
    ret

get_nib:                                ; esi -> sprite, edx = line, ecx = column -> al = pixel (0..15)
    push ebx
    push ecx
    mov ebx, [esi]
    lea ebx, [ebx + edx * 8]
    shr ecx, 1
    mov al, [ebx + ecx]
    pop ecx
    test cl, 1
    jnz .lo
    shr al, 4
.lo:
    and al, 0Fh
    pop ebx
    ret

put_nib:                                ; edi -> sprite, edx = line, ecx = column, al = pixel (not 0)
    push eax
    push ebx
    push ecx
    mov ebx, [edi]
    lea ebx, [ebx + edx * 8]
    shr ecx, 1
    add ebx, ecx
    pop ecx
    test cl, 1
    jnz .lo
    shl al, 4
.lo:
    or [ebx], al
    pop ebx
    pop eax
    ret

col_used:                               ; esi -> sprite, ecx = column, ebp = lines -> ZF = 0 if a pixel is set
    push eax
    push edx
    xor edx, edx
.r:
    call get_nib
    test al, al
    jnz .o
    inc edx
    cmp edx, ebp
    jb .r
    xor eax, eax
.o:
    pop edx
    pop eax
    ret

glyph:                                  ; eax = digit, ebx = column in edi's sprite -> ebx = after the digit
    push eax
    push ecx
    push edx
    push esi
    imul eax, eax, 12
    add eax, [CUR_BUF]
    add eax, 16
    mov esi, [eax]
    mov ecx, [eax + 4]                  ; first column in its sprite
    mov eax, [eax + 8]                  ; width
.c:
    xor edx, edx
.r:
    push eax
    call get_nib
    test al, al
    jz .s
    push ecx
    mov ecx, ebx
    call put_nib
    pop ecx
.s:
    pop eax
    inc edx
    cmp edx, ebp
    jb .r
    inc ecx
    inc ebx
    dec eax
    jnz .c
    pop esi
    pop edx
    pop ecx
    pop eax
    ret

first_col:                              ; esi, ebp -> ecx = first used column of 0..15 (CF = 1: none)
    xor ecx, ecx
.l:
    call col_used
    jnz .ok
    inc ecx
    cmp ecx, 16
    jb .l
    stc
    ret
.ok:
    clc
    ret

last_col:                               ; esi, ebp -> ecx = last used column (a column is known to be used)
    mov ecx, 15
.l:
    call col_used
    jnz .ok
    dec ecx
    jmp .l
.ok:
    ret

build_numbers:                          ; [CUR_BUF]: 1 = built, 2 = not possible (unexpected digit sprites); the set:
    pushad                              ; digits [CUR_BASE] + n, "10" = [CUR_BASE] + 10, new [CUR_NEW] + n - first
    mov edi, [CUR_BUF]
    mov byte [edi], 2
    mov esi, [CUR_BASE]
    mov esi, [SPRIDX + esi * 4 + 40]    ; "10"
    cmp word [esi + 14], 1              ; one quad wide
    jne .out
    movzx ebp, word [esi + 12]          ; lines
    cmp ebp, 8
    ja .out
    mov eax, 2
.dig:                                   ; digits 2..9: their own sprites (base + digit)
    mov esi, [CUR_BASE]
    add esi, eax
    mov esi, [SPRIDX + esi * 4]
    cmp word [esi + 14], 1
    jne .out
    cmp [esi + 12], bp
    jne .out
    call first_col
    jc .out
    mov ebx, ecx
    call last_col
    sub ecx, ebx
    inc ecx
    imul edi, eax, 12
    add edi, [CUR_BUF]
    add edi, 16
    mov [edi], esi
    mov [edi + 4], ebx
    mov [edi + 8], ecx
    inc eax
    cmp eax, 10
    jb .dig
    cmp dword [CUR_MENU], 0
    jne .menu10
    mov esi, [CUR_BASE]
    mov esi, [SPRIDX + esi * 4 + 40]    ; "10": its narrow 1, then its 0
    call first_col
    jc .out
    mov ebx, ecx
.one:
    inc ecx
    cmp ecx, 16
    jae .out
    call col_used
    jnz .one
    mov eax, [CUR_BUF]
    mov [eax + 16 + 12], esi
    mov [eax + 16 + 16], ebx
    mov edx, ecx
    sub edx, ebx
    mov [eax + 16 + 20], edx
.gap:
    inc ecx
    cmp ecx, 16
    jae .out
    call col_used
    jz .gap
    mov ebx, ecx
    call last_col
    sub ecx, ebx
    inc ecx
    mov eax, [CUR_BUF]
    mov [eax + 16], esi
    mov [eax + 16 + 4], ebx
    mov [eax + 16 + 8], ecx
    jmp .numbers
.menu10:                                ; the menu's "10" has no gap: 1 = its own sprite, 0 = "10" after that width
    mov esi, [CUR_BASE]
    mov esi, [SPRIDX + esi * 4 + 4]     ; "1"
    cmp word [esi + 14], 1
    jne .out
    cmp [esi + 12], bp
    jne .out
    call first_col
    jc .out
    mov ebx, ecx
    call last_col
    sub ecx, ebx
    inc ecx
    mov eax, [CUR_BUF]
    mov [eax + 16 + 12], esi
    mov [eax + 16 + 16], ebx
    mov [eax + 16 + 20], ecx
    mov edx, ecx                        ; the 1's width
    mov esi, [CUR_BASE]
    mov esi, [SPRIDX + esi * 4 + 40]    ; "10"
    call first_col
    jc .out
    add ecx, edx
.gap0:
    cmp ecx, 16
    jae .out
    call col_used
    jnz .zero
    inc ecx
    jmp .gap0
.zero:
    mov ebx, ecx
    call last_col
    sub ecx, ebx
    inc ecx
    mov eax, [CUR_BUF]
    mov [eax + 16], esi
    mov [eax + 16 + 4], ebx
    mov [eax + 16 + 8], ecx
.numbers:
    mov eax, [CUR_FIRST]
.num:                                   ; sprites first..99
    mov edi, eax
    sub edi, [CUR_FIRST]
    imul edi, edi, 96
    add edi, [CUR_BUF]
    add edi, 256
    mov esi, [CUR_BASE]
    mov esi, [SPRIDX + esi * 4 + 40]
    xor ecx, ecx
.hdr:                                   ; header of "10" (no string instructions: ES may differ from DS)
    mov edx, [esi + ecx]
    mov [edi + ecx], edx
    add ecx, 4
    cmp ecx, 24
    jb .hdr
.clr:
    mov dword [edi + ecx], 0
    add ecx, 4
    cmp ecx, 96
    jb .clr
    lea edx, [edi + 24]
    mov [edi], edx                      ; its pixels
    push eax
    xor edx, edx
    mov ecx, 10
    div ecx                             ; eax = tens, edx = units
    xor ebx, ebx
    call glyph
    cmp byte [CUR_MENU], 0              ; match numbers: 1 pixel apart; the menus' (4.0.2, Malave): side by side,
    jne .tight                          ; as the menu's own "10"
    inc ebx
.tight:
    mov eax, edx
    call glyph
    mov [edi + 10], bx                  ; width
    shr ebx, 1
    mov [edi + 16], bx                  ; centre x, as 10..16 (5 wide: 2)
    pop eax
    mov edx, [CUR_NEW]
    add edx, eax
    sub edx, [CUR_FIRST]
    mov [edi + 22], dx                  ; its sprite number
    mov [SPRIDX + edx * 4], edi
    inc eax
    cmp eax, 100
    jb .num
    mov eax, [CUR_BUF]
    mov byte [eax], 1
.out:
    popad
    ret

align 4
CUR_BUF: dd 0                           ; the set being built (also menunum.py's menu numbers)
CUR_BASE: dd 0
CUR_NEW: dd 0
CUR_FIRST: dd 0                         ; the first number built (17 here, 12 for the menus)
CUR_MENU: dd 0                          ; 1: the 1 from its own sprite (the menu's "10" has no gap between 1 and 0)
"""


def spr_index(p):
    """obj2 offset of spritesIndex: the dword after the free 3072 bytes points at their start (spritesIndex + 5340)."""
    cand = [(o, tt) for so, o, t, to, tt, *_ in p.le.fixups() if so == 2 and to == 2 and tt is not None
            and o - tt == 3072]
    assert len(cand) == 1, cand
    o, free = cand[0]
    callers = [(so, oo) for so, oo, t, to, tt, *_ in p.le.fixups() if to == 2 and tt == o]
    assert len(callers) == 4 and all(so == 1 for so, _ in callers), callers   # only the two dead routines
    assert not any(p.le.obj_bytes(2)[free:free + 3072])
    return free - 5340


def patch(p, at, bss):
    """Hook both sites; the code goes at obj1:at, the sprites at obj2:bss (BSS_SIZE zero bytes). Returns the end."""
    d1 = p.le.obj_bytes(1)
    sites = [m.start() for m in re.finditer(rb'\x66\xc7\x05....\xa3\x04\x66\xa1....\x66\x01\x05....\x66\xa1', d1, re.S)]
    assert len(sites) == 2, sites
    d0 = {p.target(1, s + 3) for s in sites} | {p.target(1, s + 18) for s in sites}
    assert len(d0) == 1, d0                 # the mov and the add both address D0
    tobj, d0 = d0.pop()
    assert tobj == 2
    ega = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\xff\x0f\x84....\x66\x81\x3d....\x33\x01', d1, re.S)]
    assert len(ega) == 1, ega               # DrawSprite16Pixels: cmp EGA_graphics, -1 / cmp word [D0], SPR_TEAM1_NAME
    tobj, ega = p.target(1, ega[0] + 3)
    assert tobj == 2
    spr = spr_index(p)
    at = (at + 15) & ~15
    sym = {'D0': (2, d0), 'EGA': (2, ega), 'SPRIDX': (2, spr), 'NUMBUF': (2, bss), 'NEWBASE_': (0, NEWBASE)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    lab = nasmcave.labels(ASM, at, sym)
    LABELS.update(lab, EGA=ega, SPRIDX=spr)
    for s in sites:
        add, mov = s + 15, s + 22
        assert p.get(1, add, 13) == d1[add:add + 13], 'another module patched the number sprite code'
        p.remove(1, add + 3)
        p.put(1, add, b'\xE8' + (lab['num_sprite'] - (add + 5)).to_bytes(4, 'little', signed=True) + b'\x90\x90')
        p.remove(1, mov + 2)
        p.put(1, mov, b'\xE8' + (lab['fix_d0'] - (mov + 5)).to_bytes(4, 'little', signed=True) + b'\x90')
    print(f'exe: shirt numbers: 17..99 built from the digits (obj1+{sites[0]:#x}, +{sites[1]:#x} -> obj1+{at:#x}, '
          f'{len(code)} B; sprites obj2+{bss:#x}, spritesIndex obj2+{spr:#x})')
    return at + len(code)
