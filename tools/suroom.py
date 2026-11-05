"""More room for the game's save-under stack (4.0.6, MiSTer panel H1): the bench menus' rectangles overflowed it.

DrawRectangle (obj1 0xcd38 IT) first saves the back buffer under each rectangle (SaveUnder, 0xd0c0: ((w >> 2) + 1)
dwords x h, a 16-byte entry each) onto one stack, popped at the next frame. The stack lives in a fixed region of the
DOS block the game allocates at start (DPMI 0100h, 0x940f: 0x60c00 + 0x5582 bytes): base+0x4fc00 .. base+0x60c00 =
69 632 B, then base+0x60c00 = a 0x5582-byte area ([0x31684]: a backup copy of the 0x5580-byte structure at [0x20a72],
0x1d7e3 / 0x1d84a). The substitutes menu with formwide's wider rows (shadow / frame 144, background 142) saves
70 440 B, with bstrip's two boxes 79 488 B (the original rows 63 432 B; harness save_under, bench_sub): the overflow
wrote into that backup, and on the MiSTer the match's bottom panel came out garbled after a substitution.
Fix: the block ROOM bytes longer and the backup area ROOM bytes further (the allocation's `mov ebx, 60C00h` and the
backup pointer's `add eax, 60C00h`): the stack's region 69 632 + ROOM B, the rest of the block as it was. Every user
of the stack goes through the pointer [0x31694] (base+0x4fc00, unchanged). The same bytes in the four exes.
The block grows from 418 to 450 KB of conventional memory (DOS/4GW's DOS-memory allocation).
"""
import re
import struct

ROOM = 0x8000                           # +32 KB: the stack's region 102 400 B (Regia 05/11: room for the long bench
                                        # in friendlies + the strip + future boxes, not a 6.5 KB margin)
OLD = 0x60C00                           # the backup area's offset in the block (= the old block size - 0x5582)


def sites(p):
    """obj1 offsets of the two immediates (the allocation's size, the backup area's offset)."""
    d = p.le.obj_bytes(1)
    a = [m.start() + 1 for m in re.finditer(rb'\xbb\x00\x0c\x06\x00\x81\xc3\x82\x55\x00\x00\xc1\xeb\x04\x43\xcd\x31', d)]
    b = [m.start() + 1 for m in re.finditer(rb'\x05\x00\x0c\x06\x00\xa3', d)]
    assert len(a) == 1 and len(b) == 1 and 0 < b[0] - a[0] < 0x80, ('suroom: the DOS block allocation', a, b)
    return a[0], b[0]


def patch(p):
    for site in sites(p):
        assert p.get(1, site, 4) == struct.pack('<I', OLD), ('suroom: already patched', hex(site))
        p.put(1, site, struct.pack('<I', OLD + ROOM))
    a, b = sites(p)
    print(f'exe: suroom: save-under region {0x11000 + ROOM} B (+{ROOM}), DOS block +{ROOM} B (obj1+{a:#x}, +{b:#x})')
