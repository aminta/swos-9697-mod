"""Assemble cave code with nasm and find the LE fixups it needs.

Symbols are given as {name: (obj, offset)} and become %defines.  The source
is assembled three times: plain, with obj1 moved and with obj2 moved; every
dword that follows a move is an absolute reference and gets a fixup.
Relative jumps/calls into obj1 do not change when obj1 moves (the code
moves with it), so they need none.
"""
import os
import struct
import subprocess
import tempfile

SHIFT = 0x01000000


def _nasm(src, org, symbols, bases):
    head = [f'bits 32', f'org {org + bases[1]:#x}']
    for name, (obj, off) in symbols.items():
        if obj == 0:                                   # plain constant / text
            head.append(f'%define {name} {off}')
        else:
            head.append(f'%define {name} {bases[obj] + off:#x}')
    with tempfile.TemporaryDirectory() as t:
        asm, out = os.path.join(t, 'c.asm'), os.path.join(t, 'c.bin')
        open(asm, 'w').write('\n'.join(head) + '\n' + src)
        r = subprocess.run(['nasm', '-f', 'bin', '-o', out, asm], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return open(out, 'rb').read()


def assemble(src, org, symbols):
    """Return (code, [(offset_in_code, target_obj, target_off)]) for code placed at obj1:org."""
    base = _nasm(src, org, symbols, {1: 0, 2: 0})
    fix = []
    for obj in (1, 2):
        moved = _nasm(src, org, symbols, {1: SHIFT if obj == 1 else 0, 2: SHIFT if obj == 2 else 0})
        assert len(moved) == len(base)
        k = 0
        while k < len(base):
            if base[k] != moved[k]:
                start = k - 3
                a = struct.unpack_from('<I', base, start)[0]
                b = struct.unpack_from('<I', moved, start)[0]
                assert b - a == SHIFT, (obj, hex(start))
                fix.append((start, obj, a))
                k = start + 4
            else:
                k += 1
    return base, sorted(fix)


def labels(src, org, symbols):
    """Addresses (obj1 offsets) of the global labels in src, from a nasm map file."""
    import re
    head = ['bits 32', f'org {org:#x}']
    for name, (obj, off) in symbols.items():
        head.append(f'%define {name} {off}' if obj == 0 else f'%define {name} {off:#x}')
    with tempfile.TemporaryDirectory() as t:
        asm, out, mp = (os.path.join(t, n) for n in ('c.asm', 'c.bin', 'c.map'))
        open(asm, 'w').write('\n'.join(head) + f'\n[map symbols {mp}]\n' + src)
        r = subprocess.run(['nasm', '-f', 'bin', '-o', out, asm], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        text = open(mp).read()
    return {m.group(2): int(m.group(1), 16) for m in re.finditer(r'^\s*([0-9A-F]+)\s+[0-9A-F]+\s+([A-Za-z_]\w*)\s*$', text, re.M)}
