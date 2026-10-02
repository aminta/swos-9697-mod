#!/usr/bin/env python3
"""Rob Northen ProPack method 1 unpacker. usage: rnc.py IN OUT"""
import struct, sys

def _mirror(x, n):
    r = 0
    for _ in range(n): r = (r << 1) | (x & 1); x >>= 1
    return r

class _Bits:
    def __init__(s, d, p):
        s.d, s.p = d, p
        s.buf, s.cnt = s.w(p), 16
    def w(s, p): return s.d[p] | (s.d[p+1] << 8) if p + 1 < len(s.d) else (s.d[p] if p < len(s.d) else 0)
    def peek(s, mask): return s.buf & mask
    def adv(s, n):
        s.buf >>= n; s.cnt -= n
        if s.cnt < 16:
            s.p += 2; s.buf |= s.w(s.p) << s.cnt; s.cnt += 16
    def read(s, mask, n):
        v = s.peek(mask); s.adv(n); return v
    def fix(s):
        s.cnt -= 16; s.buf &= (1 << s.cnt) - 1
        s.buf |= s.w(s.p) << s.cnt; s.cnt += 16

def _table(b):
    num = b.read(0x1f, 5)
    if not num: return []
    lens = [b.read(0xf, 4) for _ in range(num)]
    t, code = [], 0
    for i in range(1, max(lens + [1]) + 1):
        for j in range(num):
            if lens[j] == i:
                t.append((_mirror(code, i), i, j)); code += 1
        code <<= 1
    return t

def _huf(t, b):
    for code, ln, val in t:
        if b.peek((1 << ln) - 1) == code: break
    else: raise ValueError('bad huffman code')
    b.adv(ln)
    if val >= 2:
        v = 1 << (val - 1); v |= b.read(v - 1, val - 1); return v
    return val

def unpack(d):
    assert d[:3] == b'RNC' and d[3] == 1, 'not RNC method 1'
    usize, psize = struct.unpack('>II', d[4:12])
    out = bytearray(); b = _Bits(d, 18); b.adv(2)
    while len(out) < usize:
        raw, dist, ln = _table(b), _table(b), _table(b)
        cnt = b.read(0xffff, 16)
        while True:
            n = _huf(raw, b)
            if n:
                out += d[b.p:b.p+n]; b.p += n; b.fix()
            cnt -= 1
            if cnt <= 0: break
            pos = _huf(dist, b) + 1; n = _huf(ln, b) + 2
            for _ in range(n): out.append(out[-pos])
    return bytes(out[:usize])

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    open(sys.argv[2], 'wb').write(unpack(d) if d[:3] == b'RNC' else d)
