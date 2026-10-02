#!/usr/bin/env python3
"""Minimal read-only PFS3 reader for RDB hardfiles (AmigaVision.hdf).
usage: pfs3.py HDF PART ls PATH | get PATH OUTDIR (recursive) | find NAME"""
import struct, sys, os
BS = 512
class PFS:
    def __init__(s, path, part):
        s.f = open(path, 'rb')
        s.parts = s.rdb()
        lo, hi, heads, bpt = s.parts[part]
        s.base = lo * heads * bpt
        rb = s.blk(2)
        s.opt = struct.unpack('>I', rb[4:8])[0]
        s.rbs = struct.unpack('>H', rb[64:66])[0]
        s.ext = struct.unpack('>I', rb[88:92])[0]
        s.idx = struct.unpack('>104I', rb[96:96+416])
        s.apb = (s.rbs - 16) // 12          # anodes per anodeblock
        s.ipb = (s.rbs - 12) // 4           # entries per index block
        s.cache = {}
    def rdb(s):
        s.f.seek(0); b = s.f.read(BS)
        assert b[:4] == b'RDSK'
        nb = struct.unpack('>I', b[28:32])[0]; parts = {}
        while nb != 0xffffffff:
            s.f.seek(nb * BS); p = s.f.read(BS)
            n = p[36]; de = struct.unpack('>20I', p[128:208])
            parts[p[37:37+n].decode()] = (de[9], de[10], de[3], de[5])
            nb = struct.unpack('>I', p[16:20])[0]
        return parts
    def blk(s, n, cnt=1):
        s.f.seek((s.base + n) * BS); return s.f.read(cnt * BS)
    def res(s, n):                          # reserved block (rbs bytes)
        return s.blk(n, s.rbs // BS)
    def anodeblock(s, seq):
        if seq in s.cache: return s.cache[seq]
        if s.opt & 0x80:                    # MODE_SUPERINDEX
            rext = s.res(s.ext)
            # rootblockextension: id(2) nu(2) ext_options(4) datestamp(4) pfs2version(4) root_date[3](6) volume_date[3](6)
            # postponed_op[4](16) reserved_roving(4) rovingbit(2) curranseqnr(2) deldirroving(2) deldirsize(2) fnsize(2) nu[3](6) superindex[16]
            off = 2+2+4+4+4+6+6+16+4+2+2+2+2+2+6
            sup = struct.unpack('>16I', rext[off:off+64])
            si = s.res(sup[seq // (s.ipb * s.ipb)])
            ib_n = struct.unpack('>I', si[12+4*((seq // s.ipb) % s.ipb):][:4])[0]
        else:
            ib_n = s.idx_small(seq)
        ib = s.res(ib_n)
        ab_n = struct.unpack('>I', ib[12+4*(seq % s.ipb):][:4])[0]
        ab = s.res(ab_n); s.cache[seq] = ab; return ab
    def idx_small(s, seq):
        rb = s.blk(2); small = struct.unpack('>99I', rb[96+20:96+20+396])
        return small[seq // s.ipb]
    def anode(s, nr):
        if s.opt & 0x02: seq, off = nr >> 16, nr & 0xffff   # MODE_SPLITTED_ANODES
        else: seq, off = divmod(nr, s.apb)
        a = s.anodeblock(seq)
        return struct.unpack('>III', a[16+12*off:16+12*off+12])
    def chain(s, nr):
        while nr:
            cs, bn, nx = s.anode(nr); yield bn, cs; nr = nx
    def readdir(s, anr):
        for bn, cs in s.chain(anr):
            for i in range(0, cs, s.rbs // BS):
                d = s.blk(bn + i, s.rbs // BS)
                if d[:2] != b'DB': continue
                p = 20
                while p < len(d) and d[p]:
                    ln = d[p]; e = d[p:p+ln]
                    typ = struct.unpack('>b', e[1:2])[0]
                    an, size = struct.unpack('>II', e[2:10]); nl = e[17]
                    name = e[18:18+nl].decode('latin-1')
                    yield name, typ, an, size
                    p += ln
    def lookup(s, path):
        anr, typ, size = 5, 1, 0
        for comp in [c for c in path.split('/') if c]:
            for n, t, a, sz in s.readdir(anr):
                if n.lower() == comp.lower(): anr, typ, size = a, t, sz; break
            else: raise FileNotFoundError(path)
        return anr, typ, size
    def read(s, anr, size):
        out = bytearray()
        for bn, cs in s.chain(anr):
            out += s.blk(bn, cs)
            if len(out) >= size: break
        return bytes(out[:size])
    def get(s, anr, typ, size, dst):
        if typ > 0:
            os.makedirs(dst, exist_ok=True)
            for n, t, a, sz in s.readdir(anr): s.get(a, t, sz, os.path.join(dst, n))
        else:
            open(dst, 'wb').write(s.read(anr, size))
if __name__ == '__main__':
    fs = PFS(sys.argv[1], sys.argv[2]); cmd = sys.argv[3]
    if cmd == 'info': print(fs.parts, hex(fs.opt), fs.rbs, fs.ext)
    elif cmd == 'ls':
        anr, t, _ = fs.lookup(sys.argv[4] if len(sys.argv) > 4 else '')
        for n, t, a, sz in fs.readdir(anr): print(('D ' if t > 0 else 'F ') + n, sz)
    elif cmd == 'get':
        anr, t, sz = fs.lookup(sys.argv[4]); fs.get(anr, t, sz, sys.argv[5])
