"""The chairman's season-end opinion, signed (4.2; Davide 12/11, found by the 4.1.2 zone-position work).

ShowChairmanOpinionAboutTheSeason rates the season by (expected place - place) x 100 / teams:
    movsx eax, word [D0]; mov ebx, 100; imul ebx; mov [D0], eax; xor edx, edx; mov eax, [D0];
    movzx ebx, word [D3]; idiv ebx
The `xor edx, edx` clears the high half of the dividend instead of sign-extending it: a club BELOW its expected
place divides 2^32 - |d| x 100, and the low word of that quotient reads as noise (breakpoint-checked at cseg_3C271:
Malta 2nd for 1st expected -> 554Dh, COMPLIMENTI; River 3rd of its zone -> 887Bh, NON BUONA). `cdq; nop` makes it the
signed division the comparisons after it expect. Only the note's text changes: the board's decision (contract not
renewed, cseg_3E55C) comes from seasonReview, cseg_3E3B0's own ratio, already signed (`imul bx; idiv word`).
The other `xor edx, edx; idiv` sites of the exe (cseg_3C4CE, the DIY tournament menus, FillColorfulnessTableElement)
have a dividend >= 0: left as they are.
"""
import re
import struct


def site(d1):
    """obj1 offset of the opinion's `xor edx, edx` (original bytes)."""
    import sacups
    a0 = sacups.regs(d1)['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    D0, D3 = a0 - 32, a0 - 20
    m = [x.start() + 12 for x in re.finditer(rb'\xbb\x64\x00\x00\x00\xf7\xeb\xa3' + A(D0) + rb'[\x31\x33]\xd2\xa1'
                                             + A(D0) + rb'\x0f\xb7\x1d' + A(D3) + rb'\xf7\xfb', d1, re.S)]
    assert len(m) == 1, ('opinion ratio', [hex(x) for x in m])
    return m[0]


def patch(p):
    d1 = p.le.obj_bytes(1)
    s = site(d1)
    assert p.get(1, s, 2) == d1[s:s + 2], 'opinion ratio: site already patched'
    assert not any(f[0] == 1 and s - 3 <= f[1] < s + 2 for f in p.le.fixups()), 'opinion ratio: a fixup in the bytes'
    p.put(1, s, b'\x99\x90')                            # cdq; nop
    print(f'exe: season-end opinion ratio signed (cdq, obj1+{s:#x})')
