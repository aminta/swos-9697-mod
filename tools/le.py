"""Minimal reader for DOS/4GW Linear Executable (LE) files, e.g. SWOS ITALIAN.EXE.

Gives object layout, virtual <-> file offset mapping and internal fixups,
which is all we need to find code by signature and patch it safely.
"""
import struct
import sys


class Obj:
    def __init__(self, idx, vsize, base, flags, page_idx, npages):
        self.idx, self.vsize, self.base, self.flags = idx, vsize, base, flags
        self.page_idx, self.npages = page_idx, npages

    def __repr__(self):
        kind = 'code' if self.flags & 4 else 'data'
        return (f'obj{self.idx} {kind} base={self.base:#x} vsize={self.vsize:#x} '
                f'pages={self.page_idx}..{self.page_idx + self.npages - 1} flags={self.flags:#x}')


class LE:
    def __init__(self, path):
        self.path = path
        self.data = bytearray(open(path, 'rb').read())
        d = self.data
        self.hdr = h = struct.unpack_from('<I', d, 0x3c)[0]
        assert d[h:h + 2] == b'LE', 'not an LE file'
        u = lambda off: struct.unpack_from('<I', d, h + off)[0]
        self.npages = u(0x14)
        self.eip_obj, self.eip = u(0x18), u(0x1c)
        self.esp_obj, self.esp = u(0x20), u(0x24)
        self.page_size = u(0x28)
        self.last_page = u(0x2c)
        obj_tab, nobj = u(0x40), u(0x44)
        page_map = u(0x48)
        self.fix_page_tab = h + u(0x68)
        self.fix_rec_tab = h + u(0x6c)
        self.data_pages = u(0x80)
        self.objs = []
        for i in range(nobj):
            vs, base, fl, pi, npg, _ = struct.unpack_from('<6I', d, h + obj_tab + i * 24)
            self.objs.append(Obj(i + 1, vs, base, fl, pi, npg))
        # page map: 24-bit big-endian page number + flags byte
        self.page_file = []
        for i in range(self.npages):
            b = d[h + page_map + i * 4: h + page_map + i * 4 + 4]
            num = (b[0] << 16) | (b[1] << 8) | b[2]
            self.page_file.append(self.data_pages + (num - 1) * self.page_size)

    def obj(self, n):
        return self.objs[n - 1]

    def file_off(self, objn, off):
        """File offset of object-relative offset (None if in uninitialized tail)."""
        o = self.obj(objn)
        page = off // self.page_size
        if page >= o.npages:
            return None
        return self.page_file[o.page_idx - 1 + page] + off % self.page_size

    def obj_bytes(self, objn):
        """Initialized bytes of an object, concatenated page by page."""
        o = self.obj(objn)
        out = bytearray()
        for p in range(o.npages):
            gp = o.page_idx - 1 + p
            size = self.last_page if gp == self.npages - 1 else self.page_size
            out += self.data[self.page_file[gp]:self.page_file[gp] + size]
        return bytes(out)

    def fixups(self):
        """Yield (src_obj, src_off, type, target_obj, target_off, rec_file_off, tgt_field_off, tgt_is32)."""
        d = self.data
        page_obj = []
        for o in self.objs:
            for p in range(o.npages):
                page_obj.append((o.idx, p * self.page_size))
        for gp in range(self.npages):
            start = struct.unpack_from('<I', d, self.fix_page_tab + gp * 4)[0]
            end = struct.unpack_from('<I', d, self.fix_page_tab + gp * 4 + 4)[0]
            p = self.fix_rec_tab + start
            stop = self.fix_rec_tab + end
            sobj, pbase = page_obj[gp]
            while p < stop:
                rec = p
                src, flg = d[p], d[p + 1]
                p += 2
                if src & 0x20:
                    cnt = d[p]
                    p += 1
                    srcoffs = None
                else:
                    srcoffs = struct.unpack_from('<h', d, p)[0]
                    p += 2
                assert flg & 3 == 0, f'non-internal fixup at {rec:#x}'
                if flg & 0x40:
                    tobj = struct.unpack_from('<H', d, p)[0]
                    p += 2
                else:
                    tobj = d[p]
                    p += 1
                toff, tfield, t32 = None, None, False
                if src & 0xf != 2:  # selector fixups carry no offset
                    tfield = p
                    if flg & 0x10:
                        toff = struct.unpack_from('<I', d, p)[0]
                        p += 4
                        t32 = True
                    else:
                        toff = struct.unpack_from('<H', d, p)[0]
                        p += 2
                if srcoffs is None:
                    for _ in range(cnt):
                        so = struct.unpack_from('<h', d, p)[0]
                        p += 2
                        yield (sobj, pbase + so, src & 0xf, tobj, toff, rec, tfield, t32)
                else:
                    yield (sobj, pbase + srcoffs, src & 0xf, tobj, toff, rec, tfield, t32)


if __name__ == '__main__':
    le = LE(sys.argv[1])
    print(f'pages={le.npages} page_size={le.page_size:#x} data_pages={le.data_pages:#x}')
    print(f'entry obj{le.eip_obj}:{le.eip:#x} stack obj{le.esp_obj}:{le.esp:#x}')
    for o in le.objs:
        print(o)
    fx = list(le.fixups())
    print(f'{len(fx)} fixups')
