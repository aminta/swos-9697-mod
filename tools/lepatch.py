"""Patch an LE executable including its fixup tables.

The fixup record table is split into raw records per page; records can be
retargeted or added, and save() re-serializes the page table + record table.
If the records outgrow the padding before the data pages, the data pages are
moved down (keeping 512-byte alignment) and the header offsets follow.
Only what SWOS needs is supported: internal references, no imports,
no non-resident name table or debug info after the pages.
"""
import struct

from le import LE

ALIGN = 0x200


class LEPatch:
    def __init__(self, path):
        self.le = le = LE(path)
        self.out = bytearray(le.data)
        h = le.hdr
        u = lambda off: struct.unpack_from('<I', le.data, h + off)[0]
        assert u(0x74) == 0 and u(0x7c) == 0 and u(0x88) == 0 and u(0x98) == 0
        assert u(0x70) == u(0x78)
        self.page_obj = []
        for o in le.objs:
            for p in range(o.npages):
                self.page_obj.append((o.idx, p * le.page_size))
        self.recs = [[] for _ in range(le.npages)]   # per page: [raw bytes]
        d = le.data
        for gp in range(le.npages):
            start, end = struct.unpack_from('<2I', d, le.fix_page_tab + gp * 4)
            p, stop = le.fix_rec_tab + start, le.fix_rec_tab + end
            while p < stop:
                n = self._rec_len(d, p)
                self.recs[gp].append(bytes(d[p:p + n]))
                p += n
            assert p == stop
        self.old_end = le.fix_rec_tab + struct.unpack_from('<I', d, le.fix_page_tab + le.npages * 4)[0]

    @staticmethod
    def _rec_len(d, p):
        src, flg = d[p], d[p + 1]
        n = 2 + (1 if src & 0x20 else 2)
        assert flg & 3 == 0
        n += 2 if flg & 0x40 else 1
        if src & 0xf != 2:
            n += 4 if flg & 0x10 else 2
        if src & 0x20:
            n += 2 * d[p + 2]
        return n

    # --- object data -------------------------------------------------------
    def put(self, objn, off, data):
        for i, b in enumerate(data):
            fo = self.le.file_off(objn, off + i)
            assert fo is not None
            self.out[fo] = b

    def get(self, objn, off, n):
        return bytes(self.out[self.le.file_off(objn, off + i)] for i in range(n))

    def set_vsize(self, objn, vsize):
        o = self.le.obj(objn)
        assert vsize <= o.npages * self.le.page_size
        obj_tab = self.le.hdr + struct.unpack_from('<I', self.out, self.le.hdr + 0x40)[0]
        struct.pack_into('<I', self.out, obj_tab + (objn - 1) * 24, vsize)

    def add_flags(self, objn, flags):
        obj_tab = self.le.hdr + struct.unpack_from('<I', self.out, self.le.hdr + 0x40)[0]
        at = obj_tab + (objn - 1) * 24 + 8
        struct.pack_into('<I', self.out, at, struct.unpack_from('<I', self.out, at)[0] | flags)

    # --- fixups ------------------------------------------------------------
    def _page(self, objn, off):
        o = self.le.obj(objn)
        return o.page_idx - 1 + off // self.le.page_size, off % self.le.page_size

    def _find(self, objn, off):
        """(page, index) of the single-source record fixing up objn:off."""
        gp, po = self._page(objn, off)
        hits = []
        for i, r in enumerate(self.recs[gp]):
            if not r[0] & 0x20 and struct.unpack_from('<h', r, 2)[0] == po:
                hits.append(i)
        assert len(hits) == 1, (objn, hex(off), hits)
        return gp, hits[0]

    def target(self, objn, off):
        gp, i = self._find(objn, off)
        r = self.recs[gp][i]
        p = 4
        tobj = struct.unpack_from('<H', r, p)[0] if r[1] & 0x40 else r[p]
        p += 2 if r[1] & 0x40 else 1
        toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, p)[0]
        return tobj, toff

    @staticmethod
    def _record(src_type, po, tobj, toff):
        return struct.pack('<BBhBI', src_type, 0x10, po, tobj, toff)

    def retarget(self, objn, off, tobj, toff):
        gp, i = self._find(objn, off)
        r = self.recs[gp][i]
        assert not r[1] & 0x40
        self.recs[gp][i] = self._record(r[0], struct.unpack_from('<h', r, 2)[0], tobj, toff)

    def remove(self, objn, off):
        """Drop the fixup at objn:off (before overwriting the instruction holding it)."""
        gp, i = self._find(objn, off)
        del self.recs[gp][i]

    def add_ptr(self, objn, off, tobj, toff):
        """Add a 32-bit offset fixup at objn:off and store the offset there."""
        gp, po = self._page(objn, off)
        assert po <= self.le.page_size - 4, 'pointer straddles a page'
        assert not any(not r[0] & 0x20 and struct.unpack_from('<h', r, 2)[0] == po
                       for r in self.recs[gp])
        self.recs[gp].append(self._record(0x07, po, tobj, toff))
        self.put(objn, off, struct.pack('<I', toff))

    # --- output ------------------------------------------------------------
    def save(self, path):
        le, out, h = self.le, self.out, self.le.hdr
        table = bytearray()
        offs = []
        for page in self.recs:
            offs.append(len(table))
            table += b''.join(page)
        offs.append(len(table))
        pt = struct.pack(f'<{len(offs)}I', *offs)
        assert len(pt) == le.fix_rec_tab - le.fix_page_tab
        end = le.fix_rec_tab + len(table)
        old_data = le.data_pages
        new_data = max(old_data, (end + ALIGN - 1) // ALIGN * ALIGN)
        shift = new_data - old_data
        body = out[old_data:]
        out = out[:le.fix_page_tab] + pt + table + bytes(new_data - end) + body
        delta = end - self.old_end
        for off in (0x30, 0x38):                     # fixup / loader section sizes
            struct.pack_into('<I', out, h + off, struct.unpack_from('<I', out, h + off)[0] + delta)
        for off in (0x70, 0x78):                     # (empty) import tables
            struct.pack_into('<I', out, h + off, end - h)
        struct.pack_into('<I', out, h + 0x80, new_data)
        open(path, 'wb').write(out)
        return delta, shift


def add_object_page(data, objn):
    """Give object objn one more (zero) page; returns the new file bytes.

    The page is stored at the end of the file (physical page N+1) and mapped
    as the object's next logical page, so no existing page moves.  The old
    last page is zero-padded to a full page first: only the file's last page
    may be short, and the loader must not read the new page's bytes as the
    tail of the previous one.
    """
    d = bytearray(data)
    h = struct.unpack_from('<I', d, 0x3c)[0]
    u = lambda off: struct.unpack_from('<I', d, h + off)[0]
    setu = lambda off, v: struct.pack_into('<I', d, h + off, v)
    npages, psize, last = u(0x14), u(0x28), u(0x2c)
    assert len(d) == u(0x80) + (npages - 1) * psize + last, 'unexpected data after the pages'
    obj_tab, nobj = h + u(0x40), u(0x44)
    objs = [list(struct.unpack_from('<6I', d, obj_tab + 24 * i)) for i in range(nobj)]
    logical = objs[objn - 1][3] - 1 + objs[objn - 1][4]          # 0-based logical index of the new page

    d += bytes(psize - last) + bytes(psize)                     # pad last page, append the new one
    setu(0x2c, psize)
    # page map entry (24-bit big-endian physical page number + flags)
    pm = h + u(0x48) + logical * 4
    d[pm:pm] = bytes(((npages + 1) >> 16 & 0xff, (npages + 1) >> 8 & 0xff, (npages + 1) & 0xff, 0))
    for off in (0x50, 0x58, 0x5c, 0x68, 0x6c, 0x70, 0x78):      # tables after the page map
        if u(off):
            setu(off, u(off) + 4)
    # fixup page table: the new page gets an empty record range
    fpt = h + u(0x68) + (logical + 1) * 4
    d[fpt:fpt] = d[fpt - 4:fpt]
    for off in (0x6c, 0x70, 0x78):
        setu(off, u(off) + 4)
    setu(0x30, u(0x30) + 4)                                     # fixup section size
    setu(0x38, u(0x38) + 8)                                     # loader section size
    # the 8 inserted bytes come out of the padding before the data pages
    data_pages = u(0x80)
    end = h + u(0x70)
    assert end <= data_pages and not any(d[end:data_pages])
    del d[data_pages - 8:data_pages]
    setu(0x14, npages + 1)
    objs[objn - 1][4] += 1
    for o in objs[objn:]:
        o[3] += 1
    for i, o in enumerate(objs):
        struct.pack_into('<6I', d, obj_tab + 24 * i, *o)
    return bytes(d)
