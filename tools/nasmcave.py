"""Assemble cave code with nasm and find the LE fixups it needs.

Symbols are given as {name: (obj, offset)} and become %defines.  The source
is assembled three times: plain, with obj1 moved and with obj2 moved; every
dword that follows a move is an absolute reference and gets a fixup.
Relative jumps/calls into obj1 do not change when obj1 moves (the code
moves with it), so they need none.
assemble_obj (4.0.6) places the code in any object (obj3): its rel32s into
the other objects get self-relative LE fixups.
"""
import os
import struct
import subprocess
import tempfile

SHIFT = 0x01000000


def _nasm(src, org, symbols, bases, obj=1):
    head = [f'bits 32', f'org {org + bases[obj]:#x}']
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


def sub(src, old, new, n=1):
    """src with old replaced by new; old must occur exactly n times (None: at least once). A rewrite whose pattern is
    gone (changed code, an earlier rewrite) fails the build instead of passing silently (CONVENTIONS 19)."""
    c = src.count(old)
    assert (c >= 1) if n is None else c == n, (old[:60], c, n)
    return src.replace(old, new)


def assemble(src, org, symbols):
    """Return (code, [(offset_in_code, target_obj, target_off)]) for code placed at obj1:org."""
    code, fix, rel = assemble_obj(src, org, symbols, 1)
    assert not rel, ('obj1 code with a rel32 into another object: use assemble_obj', rel)
    return code, fix


def _diffs(base, moved):
    """[(start, moved - base)] of the dwords that differ (only their top byte moves: SHIFT is 2^24)."""
    out, k = [], 0
    while k < len(base):
        if base[k] != moved[k]:
            start = k - 3
            dv = (struct.unpack_from('<I', moved, start)[0] - struct.unpack_from('<I', base, start)[0]) & 0xffffffff
            out.append((start, dv))
            k = start + 4
        else:
            k += 1
    return out


def assemble_obj(src, org, symbols, obj):
    """(code, fix, rel) for code placed at obj:org. fix: [(offset_in_code, target_obj, target_off)] absolute refs
    (32-bit offset fixups); rel: [(offset_in_code, target_obj, target_off)] rel32s into another object (self-relative
    fixups). Moving the code's own object alone: its absolute refs go +SHIFT, its rel32s out of it -SHIFT; moving
    another object: both kinds into it go +SHIFT, told apart by the first run."""
    objs = sorted({1, 2, obj} | {o for o, _ in symbols.values() if o})
    zero = {o: 0 for o in objs}
    base = _nasm(src, org, symbols, zero, obj)
    fix, rel, out = [], [], set()
    for start, dv in _diffs(base, _nasm(src, org, symbols, {**zero, obj: SHIFT}, obj)):
        if dv == SHIFT:
            fix.append((start, obj, struct.unpack_from('<I', base, start)[0]))
        else:
            assert dv == (-SHIFT) & 0xffffffff, (obj, hex(start), hex(dv))
            out.add(start)
    for o in objs:
        if o == obj:
            continue
        for start, dv in _diffs(base, _nasm(src, org, symbols, {**zero, o: SHIFT}, obj)):
            assert dv == SHIFT, (o, hex(start), hex(dv))
            v = struct.unpack_from('<I', base, start)[0]
            if start in out:                           # rel32 = target - (org + start + 4) with every base 0
                rel.append((start, o, (v + org + start + 4) & 0xffffffff))
                out.discard(start)
            else:
                fix.append((start, o, v))
    assert not out, ('rel32 out of the object to no symbol', [hex(x) for x in out])
    return base, sorted(fix), sorted(rel)


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
