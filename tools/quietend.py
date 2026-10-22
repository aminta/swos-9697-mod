"""4.0.1 quiet season end (World 2026-27): the other countries' competitions are simulated without being shown.

At CONTINUA CARRIERA the season end (cseg_91428) walks the season-end list: the career club's own country first
(`call cseg_9153F` before the loop), then every other listed country (the loop's `call cseg_9153F`). cseg_9153F
simulates the country's league divisions (cseg_91D4D -> cseg_915ED -> cseg_3ABB2) and cups (cseg_91857 ->
cseg_916C2 -> cseg_3ACAB), and each simulation ends by showing the competition through ShowMenu
(ShowDiyLeaguesTournamentMenu / cseg_45B51): one full menu per competition, frame-paced. A world of 91 countries
shows ~260 of them (Davide's ao486: minutes).

The game's own switch: dseg_10E846 = 1 (cseg_8ECAE sets it around its own cseg_3ABB2) makes cseg_3AE87 / cseg_3B18F
return before the show (`cmp dseg_10E846, 0 / jnz ret`); every other test of the flag is or'ed with dseg_10E848,
which cseg_91428 already sets for the whole season end, so the simulation itself is unchanged.

qe_call replaces the loop's `call cseg_9153F`: in a career (g_gameType 4) of the World 2026-27 (world byte W27) it
calls cseg_9153F with dseg_10E846 = 1 and restores the old value; anywhere else it is the plain call. The career
club's own country (the call before the loop) is not touched: its tables and cups still show as in the original.
"""
import re
import struct

import nasmcave

ASM = r"""
qe_call:                                ; replaces the season-end loop's `call cseg_9153F` (cseg_91428)
    cmp word [GAMETYPE], 4
    jne .plain
    cmp byte [SLT + WORLD_BYTE_], W27_
    jne .plain
    push dword [QFLAG]                  ; (the word and its neighbour, restored as they were)
    mov word [QFLAG], 1
    call C9153F
    pop dword [QFLAG]
    ret
.plain:
    jmp C9153F
"""


def sites(p):
    """(the loop's call site, cseg_9153F, dseg_10E846) in obj1 / obj2 offsets, from the original exe's bytes."""
    d = p.le.obj_bytes(1)
    pat = rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0\x75.' \
          rb'\x66\xa1(....)\x66\x0b\xc0\x74'
    m = [x.start() for x in re.finditer(pat, d, re.S)]           # cseg_3AE87 / cseg_3B18F: 11F9CC, 10E848, 10E846
    assert len(m) == 2, m
    flags = {p.target(1, x + 2 + 11 * 2) for x in m}
    assert len(flags) == 1, flags
    qflag = flags.pop()
    import careerworld
    s = careerworld.SITES or careerworld.sites(p)
    tail = d[s['list']:s['list'] + 0x80]                          # the loop: ... cmp [D0], al / jz / call 9153F
    loop = [x.start() for x in re.finditer(rb'\x38\x05....\x74.\xe8', tail, re.S)]
    assert len(loop) == 1, loop
    site = s['list'] + loop[0] + 8
    target = site + 5 + struct.unpack_from('<i', d, site + 1)[0]
    first = [x.start() for x in re.finditer(rb'\xe8' , d[s['list'] - 0x30:s['list']])]
    calls = {s['list'] - 0x30 + x + 5 + struct.unpack_from('<i', d, s['list'] - 0x30 + x + 1)[0] for x in first}
    assert target in calls, ('the loop calls the function the career country gets', hex(target))
    return site, target, qflag


def patch(p, at, w27):
    """qe_call at obj1:at; returns its end. w27: the World 2026-27's world byte."""
    import careerworld
    site, c9153f, qflag = sites(p)
    assert p.get(1, site, 5) == p.le.obj_bytes(1)[site:site + 5], ('the loop call already patched', hex(site))
    cs = careerworld.SITES or careerworld.sites(p)
    sobj, slt = cs['slt']
    gt = cs['gametype']
    sym = {'GAMETYPE': gt, 'SLT': (sobj, slt), 'WORLD_BYTE_': (0, careerworld.WORLD_BYTE), 'W27_': (0, w27),
           'QFLAG': qflag, 'C9153F': (1, c9153f)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site, b'\xe8' + struct.pack('<i', lab['qe_call'] - (site + 5)))
    print(f'exe: quiet season end (World 2026-27, world {w27}): the loop call obj1+{site:#x} -> qe_call obj1+{at:#x} '
          f'({len(code)} B), dseg_10E846 obj2+{qflag[1]:#x}')
    return at + len(code)
