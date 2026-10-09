"""Experimental: install SWOS++ (Zlatko Karakas, github.com/zlatkok/swospp) on a modded ENGLISH.EXE.

SWOS++'s patchit.com only accepts the original CD ENGLISH.EXE: it writes 36 chunks at fixed FILE
offsets, 21 of them inside the LE fixup record table.  The mod rebuilds that table and appends
pages, so those file offsets are wrong on a modded exe.  This tool re-applies the same install
semantically through lepatch: identical object bytes at identical object offsets and identical
fixup changes (derived by diffing orig/ENGLISH.EXE against orig + patch/pdata.asm, see
notes/swospp.md).

What the install does:
  - main_+8: 'sub esp,0' -> nops, 'call SWOS' -> 'call DumpTimerVariables' (unused debug routine)
  - DumpTimerVariables is overwritten by a stub that saves registers, LoadFile('LOADER.BIN')
    into pitchDatBuffer (<= 10032 bytes), calls it with eax = obj2 base, ebx = obj1 base, then
    restores everything and jumps to SWOS.  The 'SAVE DISK F' string (obj2+0x54f4) becomes the
    file name 'LOADER.BIN'.
  - SetDefaultOptions+0x10 and spinBigS: one byte 1 -> 0 each.
At run time loader.bin loads swospp.bin and patches ~55 more sites in memory by English symbol
address; none of them is touched by the mod (checked in notes/swospp.md).

Usage: python3 tools/swospp.py MODDED_ENGLISH.EXE OUT.EXE   (ENGLISH only; never into c/SWOS)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lepatch import LEPatch

# (obj, offset, original bytes, SWOS++ bytes)
OBJ = [
    (1, 0x00018, '81ec00000000e83557',
        '909090909090e806a9'),
    (1, 0x0a929, '66ba0a0066a1e3050b00bee0ac0000e8f602000066ba140066a1e5050b00bee0ac0000e8e2020000'
                 '66ba1e0066a1e1050b00bee0ac0000e8ce02000066ba280066a1e7050b00bee0ac0000e8ba020000'
                 '66ba320066a1c0460c00bee0ac0000e8a602000066ba3c0066a13a030500bee0ac0000e892020000'
                 '66ba460066a136030500bee0ac0000e87e020000',
        '90908925eb160b009c60bb00000000ffb36d140300ffb371140300ffb38d140300ffb3911403008d83f4'
        '54000089838d1403008d835e530500898391140300e83bf8ffff8b83711403003d320001007603ccebfd'
        '8bcb8bc3bb0000000081c15e5305009090ffd18f05911403008f058d1403008f05711403008f056d1403'
        '00619d9090e9a7adffffc3c3c3c3'),
    (1, 0x11953, '01', '00'),
    (2, 0x054f4, '53415645204449534b2046', '4c4f414445522e42494e00'),   # 'SAVE DISK F' -> 'LOADER.BIN\0'
    (2, 0xbe168, '01', '00'),
]
# fixups in DumpTimerVariables (obj1): original ones to drop, new ones (obj1 offset, target obj, target offset)
FIX_REMOVE = [0xa92f, 0xa934, 0xa943, 0xa948, 0xa957, 0xa95c, 0xa96b, 0xa970, 0xa97f, 0xa984,
              0xa993, 0xa998, 0xa9a7, 0xa9ac]
FIX_ADD = [
    (0xa92d, 2, 0xb16eb),   # mov [SWOS_StackTop], esp
    (0xa934, 2, 0),         # mov ebx, data_base (obj2 base)
    (0xa982, 1, 0),         # mov ebx, code_base (obj1 base)
    (0xa992, 2, 0x31491),   # pop [tmp10]
    (0xa998, 2, 0x3148d),   # pop [tmp09]
    (0xa99e, 2, 0x31471),   # pop [tmp02]
    (0xa9a4, 2, 0x3146d),   # pop [tmp01]
]


# SWOS++'s own installer (patch/pdata.asm): (file offset, original, patched) on the ORIGINAL CD/GOG ENGLISH.EXE only.
# Used to recognise a vanilla game that already has SWOS++ (the patcher upgrades it to mod + SWOS++).
PATCHIT = [
    (0x00d134, '2f', '2d'),
    (0x00d137, 'e305', 'eb16'),
    (0x00d13d, '43', '34'),
    (0x00d140, 'e5050b', '000000'),
    (0x00d146, '57', '82'),
    (0x00d148, '02e1050b', '01000000'),
    (0x00d14f, '6b', '92'),
    (0x00d152, 'e7050b', '911403'),
    (0x00d158, '7f', '98'),
    (0x00d15b, 'c0460c', '8d1403'),
    (0x00d498, '34', 'c0'),
    (0x00d49f, '48', 'c0'),
    (0x00d4a6, '5c', 'c0'),
    (0x00d4ad, '70', 'c0'),
    (0x00d4b4, '84', 'c0'),
    (0x00d4bb, '93', '9e'),
    (0x00d4be, '3a0305', '711403'),
    (0x00d4c4, '98', 'c0'),
    (0x00d4cb, 'a7', 'a4'),
    (0x00d4ce, '360305', '6d1403'),
    (0x00d4d4, 'ac', 'c0'),
    (0x0a3e18, '81ec00000000', '909090909090'),
    (0x0a3e1f, '3557', '06a9'),
    (0x0ae729, '66ba0a0066a1e3050b00bee0ac', '90908925eb160b009c60bb0000'),
    (0x0ae738, 'e8f602000066ba140066a1e5050b00bee0ac0000e8e202', 'ffb36d140300ffb371140300ffb38d140300ffb3911403'),
    (0x0ae750, '0066ba1e', '8d83f454'),
    (0x0ae755, '66a1e1050b00bee0ac0000e8ce02000066ba280066a1e7050b00bee0ac', '0089838d1403008d835e530500898391140300e83bf8ffff8b83711403'),
    (0x0ae773, '00e8ba02', '3d320001'),
    (0x0ae778, '0066ba320066a1c0460c', '7603ccebfd8bcb8bc3bb'),
    (0x0ae783, 'bee0ac0000e8a602', '00000081c15e5305'),
    (0x0ae78c, '0066ba3c0066a13a', '9090ffd18f059114'),
    (0x0ae795, '0500bee0ac00', '008f058d1403'),
    (0x0ae79c, 'e89202000066ba460066a136030500bee0ac0000e87e020000', '8f05711403008f056d140300619d9090e9a7adffffc3c3c3c3'),
    (0x0b5753, '01', '00'),
    (0x14a2f4, '53415645204449534b2046', '4c4f414445522e42494e00'),
    (0x202f68, '01', '00'),
]


def patchit(data):
    """Byte-exact result of SWOS++'s patchit.com 'install' on an original ENGLISH.EXE (bytes in, bytes out)."""
    d = bytearray(data)
    for off, old, new in PATCHIT:
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        assert d[off:off + len(old)] == old, f'{off:#x}: not an original ENGLISH.EXE'
        d[off:off + len(new)] = new
    return bytes(d)


def install(src, dst):
    p = LEPatch(src)
    for objn, off, old, new in OBJ:
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        # fixup fields of the original code hold relocated-independent offsets, so a plain compare works
        have = p.get(objn, off, len(old))
        if have != old:
            raise SystemExit(f'obj{objn}+{off:#x}: unexpected bytes (exe already patched or not ENGLISH?)')
        p.put(objn, off, new)
    for off in FIX_REMOVE:
        p.remove(1, off)
    for off, tobj, toff in FIX_ADD:
        p.add_ptr(1, off, tobj, toff)
    return p.save(dst)


if __name__ == '__main__':
    delta, shift = install(sys.argv[1], sys.argv[2])
    print(f'{sys.argv[2]}: fixup table {delta:+d} bytes, data pages moved {shift:+#x}')
