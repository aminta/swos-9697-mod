"""Zero the mod's obj2 tail at startup (4.0.2, Davide's MiSTer: no number over a controlled player numbered 17..99).

The mod's run-time buffers live in a tail of obj2 beyond its file pages (patch.py set_vsize(2, ..., bss=tail):
careerworld / gplay / conti / uefaq's .bss, shirtnum's number sprites and their 'built' flag, blond, menunum, fmtpage,
teamstab), and their code assumes the tail starts at zero. The game's Watcom startup zeroes only its own .bss
(sampleHandles.._end, `rep stosd` before __InitRtns), and DOS/4GW does not clear the memory it maps for the rest: on
DOSBox-X it happens to be zero, on a MiSTer (ao486 / z486) or GOG's DOSBox 0.74 it can hold anything. A non-zero
shirtnum flag reads as 'built' but not 1 = no sprite: every number over 16 vanished (reproduced in DOSBox-X by
poking 5Ah there). The start's `call __CMain` (after __InitRtns; the only call of the pattern, all exes) goes to
tz_zero, which clears the whole tail (dword stores, ES = DS for the duration) and jumps on to __CMain.
TAILZERO_FILL_TEST (hex byte, test builds only): fill the tail with it instead of zero (the MiSTer-like start).
"""
import os
import re
import struct

SIZE = 48                               # the stub's reserved bytes (patch.py reserves them in the cosmetics page)

ASM = r"""
tz_zero:
    pushad
    push es
    push ds
    pop es
    mov edi, TAIL
    mov ecx, TAIL_DW
    mov eax, FILL
    cld
    rep stosd
    pop es
    popad
    jmp CMAIN
"""


def patch(p, at, tail_off, tail_size, nasmcave):
    """Hook start's `call __CMain` to the stub at obj1:at (SIZE bytes), which zeroes obj2:tail_off..+tail_size."""
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xb8\xff\x00\x00\x00\xe8....\x29\xed\xe8', d1, re.S)]
    assert len(m) == 1, m                       # mov eax, 0FFh / call __InitRtns / sub ebp, ebp / call __CMain
    site = m[0] + 12
    cmain = site + 5 + struct.unpack_from('<i', d1, site + 1)[0]
    assert tail_off % 4 == 0 and tail_size % 4 == 0
    fill = int(os.environ.get('TAILZERO_FILL_TEST', '0'), 16) * 0x01010101
    sym = {'TAIL': (2, tail_off), 'TAIL_DW': (0, tail_size // 4), 'FILL': (0, fill), 'CMAIN': (1, cmain)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    assert len(code) <= SIZE, len(code)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.put(1, site + 1, struct.pack('<i', at - (site + 5)))
    print(f'exe: obj2 tail obj2+{tail_off:#x}..+{tail_size:#x} zeroed at startup (start obj1+{site:#x} -> obj1+{at:#x}'
          + (f', TEST FILL {fill & 0xFF:02X}' if fill else '') + ')')
