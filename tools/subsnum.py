"""Two-digit shirt numbers in the in-match bench / substitution list (4.0.2, Davide's MiSTer b5: '99M. SVILAR').

DrawSubstitutesMenuEntry prints a row as: face icon (x .. x+8), the shirt number CENTRED at x+13
(PrintCenteredStringInColor; menunum.py writes 0..99 into playerNumberString), the short name from x+18 (x = the
row's left edge + 9 with individual faces, which the game always uses here). A one-digit number (6 px; '1' is 2 px)
fits between the two; a two-digit one (up to 12 px: 107..119) runs into the face and the name - the game only ever had
12..16 there. Now:
- the number is right-aligned to end at x+22 (sn_print replaces the number's `call PrintCenteredStringInColor`:
  centre += 9 - width/2, widths of the small font: '1' 2 px, other digits 6), so every number ends in one column and
  '99' (12 px) starts a pixel after the face;
- the name starts at x+24 (the first of name setup's two `add word [D1], 9` becomes 15): +6 px for every row. The
  longest short name (14 characters, at most 84 px) ends at x+108, before the position column (centred at x+116,
  2 letters: from x+110).
Rows without face icons (the game's other setting) keep the same relative layout.
"""
import re
import struct

import nasmcave

ASM = r"""
sn_print:                               ; replaces the number's `call PrintCenteredStringInColor`
    push eax
    push ecx
    push esi
    mov esi, NUMSTR
    xor ecx, ecx
.w:
    mov al, [esi]
    test al, al
    jz .d
    add ecx, 6
    cmp al, '1'
    jne .n
    sub ecx, 4
.n:
    inc esi
    jmp .w
.d:
    shr ecx, 1
    mov ax, 9
    sub ax, cx
    add [D1], ax                        ; right edge at the old centre + 9
    pop esi
    pop ecx
    pop eax
    jmp PRINTC
"""


def sites(p):
    """(the number's print call, PrintCenteredStringInColor, the name's first `add word [D1], 9`, D1, numstr)."""
    import sacups
    d = p.le.obj_bytes(1)
    a0 = sacups.regs(d)['A0']
    d1 = a0 - 28
    pk = lambda x: re.escape(struct.pack('<I', x))
    ms = list(re.finditer(rb'\xc7\x05' + pk(a0) + rb'(....)\x66\x83\x05' + pk(a0 - 24) + rb'\x01\x66\xc7\x05' + pk(a0 - 20)
                          + rb'\x02\x00(?:\xff\x35....){8}\xe8', d, re.S))   # mov [A0], playerNumberString / D2+1 / D3=2
    assert len(ms) == 1, ('number print block', len(ms))
    m = ms[0]
    call = m.end() - 1
    printc = call + 5 + struct.unpack_from('<i', d, call + 1)[0]
    nm = [call + x.start() for x in re.finditer(rb'\x66\x83\x05' + pk(d1) + rb'\x09\x66\xa1....\x66\x0b\xc0\x74.\x66\x83\x05'
                                                + pk(d1) + rb'\x09', d[call:call + 0x300], re.S)]
    assert len(nm) == 1, ('name x', nm)
    return call, printc, nm[0], d1, p.target(1, m.start() + 6)[1]


def patch(p, at):
    """Code at obj1:at; returns the end."""
    call, printc, name, d1, numstr = sites(p)
    assert p.get(1, call, 1) == b'\xe8' and p.get(1, name + 7, 1) == b'\x09', 'another module patched the row'
    at = (at + 15) & ~15
    sym = {'D1': (2, d1), 'NUMSTR': (2, numstr), 'PRINTC': (1, printc)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.put(1, call + 1, struct.pack('<i', at - (call + 5)))
    p.put(1, name + 7, b'\x0f')                       # name x: +9 -> +15
    print(f'exe: bench list numbers right-aligned, names +6 px (number call obj1+{call:#x}, name obj1+{name:#x}; '
          f'code obj1+{at:#x}, {len(code)} B)')
    return at + len(code)
