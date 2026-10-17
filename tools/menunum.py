"""Shirt numbers above 16 in the menus (3.3.4): the game's menus only know 1..16 (and the real numbers of the 1984-85
world go up to 41, the 2026-27 world's up to 99).

- DrawSubstitutesMenuEntry (the bench / substitutes menu in a match) turns the number into text assuming < 20:
  10..19 = '1' + digit, so 23 came out as '1' + chr(48 + 13) = '1='. Its 88-byte block (mov al,[D5] ... the string)
  starts with `mov al, [D5] / mov [D0], al` (10 bytes): that becomes `call mn_text`, which writes 0..99 properly into
  playerNumberString and goes on at the block's last instruction (`mov [A0], offset playerNumberString`).
- The little numbers over the players on the menu pitches (DrawLittlePlayersAndBall: the tactics pitch;
  cseg_51729, both of the tactics editor's pitch) are sprites 161 + number, but the menu's small numbers are 1..11
  only (162..172; 173 on are other sprites: a 30 drew the big shorts). `add word [D0], 161` / `add word [D4], 161`
  become calls: 1..11 as the game, 12..99 sprites NEWBASE + number - 12, made once from the menu's own small digits
  by shirtnum.py's build_numbers (two digits 1 pixel apart; the menu's "10" has no gap, so its 1 is sprite 162 and
  its 0 the rest of "10"); 0 and 100+ as the game.
SWOS++ (English) hooks DrawSubstitutesMenuEntry+0x570 (its own text for 17+, after our block: it overrides it, same
result) and DrawLittlePlayersAndBall+0x323 (it prints 161 + n itself from [D0] = sprite): our sites are other bytes
(+0x506 and +0x300). With SWOS++ running (the byte at +0x323 is no longer the game's `push`) the tactics pitch keeps
[D0] = 161 + n: SWOS++ prints 0 and 12+ itself; cseg_51729, which SWOS++ does not touch, always uses our sprites.
"""
import re
import struct

import nasmcave

NEWBASE = 1620                  # sprites 1620..1707 = numbers 12..99 (shirtnum 1335..1417, blond 1418..1619)
BSS_SIZE = 0x3000               # flag + digit table (256 B) + 88 sprites x 96 B
TEXTLEN = 88                    # DrawSubstitutesMenuEntry's number -> text block, up to its last instruction

ASM = r"""
mn_text:                                ; replaces `mov al, [D5] / mov [D0], al` in DrawSubstitutesMenuEntry
    push eax
    push edx
    movzx eax, byte [D5]
    mov dl, 100
    div dl
    movzx eax, ah                       ; n mod 100
    mov dl, 10
    div dl                              ; al = tens, ah = units
    mov edx, NUMSTR
    test al, al
    jz .units
    add al, '0'
    mov [edx], al
    inc edx
.units:
    mov [D0], ah                        ; as the game leaves it: the last digit's value
    add ah, '0'
    mov [edx], ah
    mov byte [edx + 1], 0
    pop edx
    pop eax
    add dword [esp], TEXTLEN_ - 5       ; on at the block's last instruction
    ret

mn_tactics:                             ; replaces `add word [D0], 161` in DrawLittlePlayersAndBall
    cmp byte [SWOSPP], 0FFh             ; SWOS++ draws the number itself from [D0] = 161 + n
    jne .game
    push eax
    mov ax, [D0]
    call mn_pick
    mov [D0], ax
    pop eax
    ret
.game:
    add word [D0], 161
    ret

mn_prematch:                            ; replaces `add word [D4], 161` in cseg_51729
    push eax
    mov ax, [D4]
    call mn_pick
    mov [D4], ax
    pop eax
    ret

mn_pick:                                ; ax = shirt number -> ax = its menu sprite
    cmp ax, 12                          ; the menu's small numbers are 1..11 (162..172; 173 is another sprite)
    jl .game
    cmp ax, 99
    jg .game
    cmp word [EGA], -1                  ; 16-colour mode: other sprite layout
    je .game
    cmp byte [MBUF], 0
    jne .built
    mov dword [CUR_BUF], MBUF           ; the menu set: small digits 161 + n, "10" = 171
    mov dword [CUR_BASE], 161
    mov dword [CUR_NEW], NEWBASE_
    mov dword [CUR_FIRST], 12
    mov dword [CUR_MENU], 1
    call BUILD
.built:
    cmp byte [MBUF], 1
    jne .game
    add ax, NEWBASE_ - 12
    ret
.game:
    add ax, 161
    ret
"""


def sites(p):
    """(text block, DrawLittlePlayersAndBall's add, cseg_51729's add, D0, D4, D5, playerNumberString) on the original."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    d0, d4 = a0 - 32, a0 - 16
    pk = lambda x: re.escape(struct.pack('<I', x))
    t = [m.start() for m in re.finditer(rb'\xa0....\xa2' + pk(d0) + rb'\xc7\x05' + pk(a0) + rb'....\x80\x3d' + pk(d0)
                                       + rb'\x0a\x72', d1, re.S)]
    assert len(t) == 1, ('number text', t)
    t = t[0]
    assert d1[t + TEXTLEN:t + TEXTLEN + 6] == b'\xc7\x05' + struct.pack('<I', a0), 'number text block end'
    # DrawLittlePlayersAndBall: add word [D0], 161 / sub word [D2], 9 / 3 pushes / push [A4] (SWOS++: +0x23)
    tac = [m.start() for m in re.finditer(rb'\x66\x81\x05' + pk(d0) + rb'\xa1\x00\x66\x83\x2d' + pk(a0 - 24) + rb'\x09'
                                         rb'(?:\xff\x35....){3}\xff\x35' + pk(a0 + 16), d1, re.S)]
    assert len(tac) == 1, ('tactics pitch', tac)
    pre = [m.start() for m in re.finditer(rb'\x66\x81\x05' + pk(d4) + rb'\xa1\x00', d1, re.S)]
    assert len(pre) == 1, ('pre-match pitch', pre)
    return t, tac[0], pre[0], d0, d4, p.target(1, t + 1)[1], p.target(1, t + 16)[1]


def patch(p, at, bss):
    """Code at obj1:at, the menu sprites at obj2:bss (BSS_SIZE zero bytes); needs shirtnum.patch first. Returns the end."""
    import shirtnum
    text, tac, pre, d0, d4, d5, numstr = sites(p)
    at = (at + 15) & ~15
    sym = {'D0': (2, d0), 'D4': (2, d4), 'D5': (2, d5), 'NUMSTR': (2, numstr), 'TEXTLEN_': (0, TEXTLEN),
           'SWOSPP': (1, tac + 0x23), 'EGA': (2, shirtnum.LABELS['EGA']), 'MBUF': (2, bss), 'NEWBASE_': (0, NEWBASE),
           'BUILD': (1, shirtnum.LABELS['build_numbers']), 'CUR_BUF': (1, shirtnum.LABELS['CUR_BUF']),
           'CUR_BASE': (1, shirtnum.LABELS['CUR_BASE']), 'CUR_NEW': (1, shirtnum.LABELS['CUR_NEW']),
           'CUR_FIRST': (1, shirtnum.LABELS['CUR_FIRST']), 'CUR_MENU': (1, shirtnum.LABELS['CUR_MENU'])}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, text + 1)                            # mov al,[D5]; mov [D0],al -> call mn_text; 5 x nop
    p.remove(1, text + 6)
    p.put(1, text, b'\xe8' + struct.pack('<i', lab['mn_text'] - (text + 5)) + b'\x90' * 5)
    for site, label in ((tac, 'mn_tactics'), (pre, 'mn_prematch')):
        p.remove(1, site + 3)                        # add word [Dx], 161 -> call; 4 x nop
        p.put(1, site, b'\xe8' + struct.pack('<i', lab[label] - (site + 5)) + b'\x90' * 4)
    print(f'exe: menu numbers 12..99: substitutes text obj1+{text:#x}, pitches obj1+{tac:#x} / +{pre:#x}, sprites '
          f'{NEWBASE}.. at obj2+{bss:#x}; code obj1+{at:#x}, {len(code)} B')
    return at + len(code)
