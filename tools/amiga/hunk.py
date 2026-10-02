#!/usr/bin/env python3
"""AmigaDOS hunk executable parser (HUNK_HEADER/CODE/DATA/BSS/RELOC32/SYMBOL/DEBUG/END).
usage: hunk.py FILE  -> prints hunks, sizes, memory flags and reloc counts."""
import struct, sys
H = {0x3e9: 'CODE', 0x3ea: 'DATA', 0x3eb: 'BSS', 0x3ec: 'RELOC32', 0x3f0: 'SYMBOL', 0x3f1: 'DEBUG',
     0x3f2: 'END', 0x3f3: 'HEADER', 0x3f7: 'DREL32', 0x3fc: 'RELOC32SHORT'}
MEM = {0: 'any', 1: 'chip', 2: 'fast'}
def parse(d):
    p = 0
    def L():
        nonlocal p; v = struct.unpack('>I', d[p:p+4])[0]; p += 4; return v
    assert L() == 0x3f3, 'not a hunk executable'
    while L(): pass                                    # resident library names
    n, first, last = L(), L(), L()
    sizes = [L() for _ in range(last - first + 1)]
    hunks = []; cur = None
    while p < len(d):
        t = L() & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            nl = L(); cur = {'type': H[t], 'data': d[p:p+nl*4], 'relocs': {}}; p += nl * 4; hunks.append(cur)
        elif t == 0x3eb:
            cur = {'type': 'BSS', 'size': L() * 4, 'data': b'', 'relocs': {}}; hunks.append(cur)
        elif t == 0x3ec:
            while True:
                c = L()
                if not c: break
                h = L(); cur['relocs'].setdefault(h, []).extend(L() for _ in range(c))
        elif t == 0x3fc or t == 0x3f7:
            while True:
                c = struct.unpack('>H', d[p:p+2])[0]; p += 2
                if not c: break
                h = struct.unpack('>H', d[p:p+2])[0]; p += 2
                cur['relocs'].setdefault(h, []).extend(struct.unpack('>%dH' % c, d[p:p+2*c])); p += 2 * c
            p = (p + 3) & ~3
        elif t == 0x3f0:
            while True:
                nl = L()
                if not nl: break
                p += nl * 4 + 4
        elif t == 0x3f1:
            p += L() * 4
        elif t == 0x3f2:
            continue
        else:
            raise ValueError(f'unknown hunk {t:#x} at {p-4:#x}')
    for h, s in zip(hunks, sizes):
        h['alloc'] = (s & 0x3fffffff) * 4; h['mem'] = MEM.get(s >> 30, 'ext')
    return hunks
if __name__ == '__main__':
    for i, h in enumerate(parse(open(sys.argv[1], 'rb').read())):
        print(i, h['type'], h['mem'], 'alloc', h['alloc'], 'file', len(h['data']),
              'relocs', {k: len(v) for k, v in h['relocs'].items()})
