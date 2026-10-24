"""Joypad safety (4.0.1): VerifyJoypadControls at the game's start.

The game keeps its controls in SETUP.DAT (word at +6, g_inputControls: 1 keyboard only, 2 joypad, 3 joypad + keyboard ...). A
SETUP.DAT with controls != 1 and NO stick plugged in (an absent game port reads FFh = a stick pinned in a corner) froze every
menu: the keyboard was ignored. The original exe has the cure, VerifyJoypadControls (reads the port with 65535 loops: no stick 1
-> controls = 1; stick 1 but no stick 2 -> controls = 3), but nothing calls it. This patch makes the game call it once, right
after ReadSetupDat in Initialization (before any load): `call ReadSetupDat` becomes `call jf_start`, which does both calls.
A factory SETUP.DAT (controls = 1) returns at once (its first instruction). The patcher ticks 'I have a joypad' by default, which
installs a calibrated SETUP.DAT (controls = 3): with this call, no pad = keyboard as before, a pad = joypad + keyboard.
"""
import re
import struct

import nasmcave

VJC_PAT = rb'\x66\x83\x3d....\x01\x74.\x66\xff\x35....\x66\xff\x35....\x66\xc7\x05....\xff\xff\x66\xc7\x05....\xff\xff'   # VerifyJoypadControls
RSD_PAT = rb'\xba....\xb0\x00\xb4\x3d\xcd\x21\x72.\x66\x8b\xd8\xba'                                              # ReadSetupDat

ASM = r"""
vjc:                                    ; VerifyJoypadControls' own place (the function has no caller): ReadSetupDat + the check
    call RSD                            ; Initialization's `call ReadSetupDat` now comes here
    push dword [NL1]                    ; g_numLoopsJoy1 / 2 (adjacent words)
    mov dword [NL1], 0xffffffff         ; read the port with the longest loops
    call RGP
    pop dword [NL1]
    mov ax, [JX]                        ; g_joy1X: 65535 (the port reads all ones) or 0 (all zeros: DOSBox-X 'auto' without a
    inc ax                              ; pad) = no stick 1; a real stick, centred, counts somewhere in between
    cmp ax, 1
    jbe .kb
    cmp word [JX2], -1                  ; stick 1 but no stick 2: joypad + keyboard (the original design)
    je .both
    ret
.kb:
    mov word [CTL], 1                   ; keyboard only
    ret
.both:
    mov word [CTL], 3
    ret
"""


def _fixup_at(p, off):
    try:
        return p.target(1, off)
    except AssertionError:
        return None


def patch(p, at=None):
    """Rewrites VerifyJoypadControls (dead code, 0x66 bytes before ReadGamePort) in place; the single `call ReadSetupDat` of
    Initialization calls it. `at` is unused (no cave needed: the cosmetics page was full). Returns `at`."""
    d1 = p.le.obj_bytes(1)
    vj = [m.start() for m in re.finditer(VJC_PAT, d1, re.S)]
    rs = [m.start() for m in re.finditer(RSD_PAT, d1, re.S)]
    assert len(vj) == 1 and len(rs) == 1, (vj, rs)
    vj, rs = vj[0], rs[0]
    size = 0x66
    rgp = vj + size
    assert d1[rgp:rgp + 3] == b'\x66\x83\x3d' and d1[rgp + 7] == 1 and d1[vj - 1:vj] != b'' and d1[vj + size - 1] == 0xc3, 'ReadGamePort follows'
    cmps = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\xff\x74', d1[vj:rgp], re.S)]
    assert len(cmps) == 2, cmps                       # cmp g_joy1X, -1 / cmp g_joy2X, -1
    sym = {'RSD': (1, rs), 'RGP': (1, rgp), 'CTL': p.target(1, vj + 3), 'NL1': p.target(1, vj + 13),
           'JX': p.target(1, vj + cmps[0] + 3), 'JX2': p.target(1, vj + cmps[1] + 3)}
    calls = [m.start() for m in re.finditer(rb'\xe8', d1)
             if m.start() + 5 <= len(d1) and m.start() + 5 + struct.unpack_from('<i', d1, m.start() + 1)[0] == rs]
    assert len(calls) == 1, [hex(c) for c in calls]
    site = calls[0]
    code, fix = nasmcave.assemble(ASM, vj, sym)
    assert len(code) <= size, len(code)
    for off in range(vj, rgp):                        # the old function's fixups go with it
        if _fixup_at(p, off) is not None:
            p.remove(1, off)
    p.put(1, vj, code + b'\x90' * (size - len(code)))
    for o, t_obj, t_off in fix:
        p.add_ptr(1, vj + o, t_obj, t_off)
    p.put(1, site, b'\xe8' + struct.pack('<i', vj - (site + 5)))
    print(f'exe: ReadSetupDat -> VerifyJoypadControls ({len(code)} of {size} bytes at obj1+{vj:#x}, call site obj1+{site:#x})')
    return at
