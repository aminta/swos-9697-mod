"""Average player price at least 1 (3.3.4; Daniele, Europe 1984-85 career with an Icelandic club).

GetAveragePlayerPrice returns the integer mean of the price index (0..) of a team's first 16 players. A season-end
routine of the career (cseg_3C4CE, ENGLISH va 0x3C784) divides by it: a team whose 16 prices add up to less than 16
(30 clubs of the 1984-85 world, IR Reykjavik and Volsungur among them; low-value edited teams) stopped the game with a
divide error (DOS/4GW dump, black screen and yellow text). The function's `mov word ptr D0, ax` after `div bx`
becomes `call ap_fix`, which stores max(ax, 1).
"""
import re
import struct

import nasmcave

ASM = r"""
ap_fix:                                 ; replaces `mov word ptr D0, ax` after GetAveragePlayerPrice's `div bx`
    cmp ax, 1                           ; CF when 0
    adc ax, 0
    mov [D0], ax
    ret
"""


def patch(p, at):
    """Code at obj1:at; returns its end."""
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x66\xBB\x10\x00\x66\xF7\xF3\x66\xA3....\x66\x89\x15....\xC3', d1, re.S)]
    assert len(m) == 1, m
    site = m[0] + 7                                     # 66 A3 <D0>
    d0 = p.target(1, site + 2)
    assert p.get(1, site, 6) == d1[site:site + 6] and p.target(1, site + 9) == (d0[0], d0[1] + 2)
    at = (at + 15) & ~15
    code, cfix = nasmcave.assemble(ASM, at, {'D0': d0})
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, site + 2)
    p.put(1, site, b'\xE8' + struct.pack('<i', at - (site + 5)) + b'\x90')
    print(f'exe: average player price >= 1 (GetAveragePlayerPrice obj1+{site:#x}, code obj1+{at:#x})')
    return at + len(code)
