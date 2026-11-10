"""4.2 option C (tools/strmap.py), without a snapshot: gplay.c's gp_strmap_c as linked into a build (obj1..obj4
relocated into Unicorn, INT 21h served from the build's DATA) on a crafted 64-season record block against the build's
own DATA\\STRMAP41.DAT. The build: HT_STRMAP_BUILD (default c/REL42strmap-ht/SWOS: ITALIAN.EXE of a HOSTTEST_SYMS=1
build + DATA/STRMAP41.DAT; none there: SKIP as a PASS).

- a 4.1 save (tag 0, the 4.1 engine item seen): every moved rel -> its new rel (both 1 KB chunks of the section),
  a gone rel (new 0) and a rel at the same place / not in the map unchanged;
- not a 4.1 save: tag 1 (a 4.2 save), no 4.1 item (a 4.0.x save): nothing changed;
- the file missing, another header (to-release 43), a truncated section: nothing changed / only what was read, and
  the file closed every time (no handle left open)."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
BUILD = os.environ.get('HT_STRMAP_BUILD') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'REL42strmap-ht', 'SWOS')
LANG = 0                                            # (ITALIAN.EXE: the IT section)


class Exe:
    def __init__(self, files):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_INTR
        from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS
        sys.path.insert(0, TOOLS)
        sys.path.insert(0, os.path.join(TOOLS, 'hosttest'))
        import emu
        from le import LE
        exe = os.path.join(BUILD, 'ITALIAN.EXE')
        le = LE(open(exe, 'rb').read())
        al = lambda x: (x + 0xFFFF) & ~0xFFFF
        n = len(le.objs)
        self.base = {1: 0x100000}
        for k in range(2, n + 1):
            self.base[k] = al(self.base[k - 1] + le.obj(k - 1).vsize)
        o1, o2, le2 = emu.relocate(exe, *(self.base.get(k) for k in (1, 2, 3, 4)))
        self.top = al(self.base[n] + le.obj(n).vsize)
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(0, self.top + 0x200000)
        for k, img in ((1, o1), (2, o2), (3, le2.img3), (4, le2.img4)):
            if k in self.base and img is not None:
                uc.mem_write(self.base[k], bytes(img))
        self.gdt, self.stack, self.sent, self.recs = self.top, self.top + 0x100000, self.top + 0x1FF000, self.top + 0x110000
        g = bytearray(8 * 64)
        g[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
        g[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
        uc.mem_write(self.gdt, bytes(g))
        uc.reg_write(UC_X86_REG_GDTR, (0, self.gdt, len(g) - 1, 0))
        for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
            uc.reg_write(r, emu.DATA_SEL)
        uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
        uc.mem_write(self.sent, b'\xf4')
        g = json.load(open(os.path.join(BUILD, 'ITALIAN.syms.json')))['gplay']
        self.syms = {k.split('.', 1)[-1]: v for k, v in g.items()}   # (C symbols as 'csyms.name')
        self.files, self.open, self.opened = files, {}, []
        uc.hook_add(UC_HOOK_INTR, self._int)

    def _int(self, uc, intno, _):
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS
        assert intno == 0x21, intno
        rd = uc.reg_read
        ah, cf = (rd(UC_X86_REG_EAX) >> 8) & 0xFF, 0
        if ah == 0x3D:
            name = bytes(uc.mem_read(rd(UC_X86_REG_EDX), 64)).split(b'\0')[0].decode().lower().replace('\\', '/')
            self.opened.append(name)
            if name in self.files:
                h = 5 + len(self.opened)
                self.open[h] = [self.files[name], 0]
                uc.reg_write(UC_X86_REG_EAX, h)
            else:
                uc.reg_write(UC_X86_REG_EAX, 2)
                cf = 1
        elif ah in (0x3F, 0x42, 0x3E):
            f = self.open.get(rd(UC_X86_REG_EBX) & 0xFFFF)
            assert f is not None, ('handle', hex(ah))
            if ah == 0x3F:
                d = f[0][f[1]:f[1] + rd(UC_X86_REG_ECX)]
                uc.mem_write(rd(UC_X86_REG_EDX), d)
                f[1] += len(d)
                uc.reg_write(UC_X86_REG_EAX, len(d))
            elif ah == 0x42:
                assert rd(UC_X86_REG_EAX) & 0xFF == 0
                f[1] = (rd(UC_X86_REG_ECX) & 0xFFFF) << 16 | rd(UC_X86_REG_EDX) & 0xFFFF
                uc.reg_write(UC_X86_REG_EAX, f[1] & 0xFFFF)
            else:
                del self.open[rd(UC_X86_REG_EBX) & 0xFFFF]
        else:
            raise AssertionError(f'INT 21h AH={ah:#x}')
        fl = rd(UC_X86_REG_EFLAGS)
        uc.reg_write(UC_X86_REG_EFLAGS, fl | 1 if cf else fl & ~1)

    def strmap(self, recs, tag, en41):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
        self.uc.mem_write(self.recs, recs)
        sp = self.stack - 64
        self.uc.mem_write(sp, struct.pack('<4I', self.sent, self.recs, tag, en41))
        self.uc.reg_write(UC_X86_REG_ESP, sp)
        o, a = self.syms['gp_strmap_c']
        self.uc.emu_start(self.base[o] + a, self.sent, count=5_000_000)
        return self.uc.reg_read(UC_X86_REG_EAX), bytes(self.uc.mem_read(self.recs, len(recs)))


def section(dat, lang):
    off, cnt = struct.unpack_from('<2I', dat, 12 + 8 * lang)
    return [struct.unpack_from('<2I', dat, off + 8 * i) for i in range(cnt)]


def block(lines):
    """64 records x 106 B, record i's +16h..+22h = lines[4i..4i+3] (season byte r[2] != 0)"""
    b = bytearray(106 * 64)
    for i in range(64):
        if 4 * i >= len(lines):
            break
        b[106 * i + 2] = 1 + i
        for f in range(4):
            if 4 * i + f < len(lines):
                struct.pack_into('<I', b, 106 * i + 0x16 + 4 * f, lines[4 * i + f])
    return bytes(b)


def lines_of(b):
    return [struct.unpack_from('<I', b, 106 * i + 0x16 + 4 * f)[0] for i in range(64) for f in range(4)]


def test_strmap():
    dat_path = os.path.join(BUILD, 'DATA', 'STRMAP41.DAT')
    if not os.path.exists(os.path.join(BUILD, 'ITALIAN.syms.json')) or not os.path.exists(dat_path):
        return True, f'SKIP: no HOSTTEST_SYMS build with STRMAP41.DAT in {BUILD}'
    dat = open(dat_path, 'rb').read()
    sec = section(dat, LANG)
    moved = [(a, b) for a, b in sec if b]
    gone = [a for a, b in sec if not b]
    keys = {a for a, _ in sec}
    same = [r for r in range(1, 400) if r not in keys][:6]       # (not in the map: kept)
    assert len(moved) > 128, len(moved)                          # (both chunks)
    pick = moved[:60] + moved[120:140] + moved[-40:]             # 120 moved
    lines = [a for a, _ in pick] + gone[:4] + same + [0] * 3     # (a 0 line stays 0)
    import random
    rnd = random.Random(42)
    rnd.shuffle(lines)
    lines = lines[:256]
    want = {a: b for a, b in pick}
    rb = block(lines)
    files = {'data/strmap41.dat': dat}
    out = []

    x = Exe(files)
    n, got = x.strmap(rb, 0, 1)
    exp = [want.get(v, v) for v in lines] + [0] * (256 - len(lines))
    if lines_of(got) != exp:
        bad = [(i, v, g, e) for i, (v, g, e) in enumerate(zip(lines + [0] * 256, lines_of(got), exp)) if g != e]
        return False, f'4.1 save: {len(bad)} lines wrong, first {bad[:3]}'
    if n != len(pick) or x.open:
        return False, f'4.1 save: {n} translated (want {len(pick)}), open handles {list(x.open)}'
    if got[2::106][:len(lines) // 4] != rb[2::106][:len(lines) // 4] or len(got) != len(rb):
        return False, 'record bytes outside the lines changed'
    out.append(f'4.1 save {n} lines (moved {len(moved)}, gone {len(gone)})')

    for what, tag, en41, fs in (('4.2 save (tag 1)', 1, 1, files), ('4.0.x save (no 4.1 item)', 0, 0, files),
                                ('no STRMAP41.DAT', 0, 1, {}),
                                ('to-release 43', 0, 1, {'data/strmap41.dat': dat[:8] + struct.pack('<H', 43) + dat[10:]}),
                                ('format 2', 0, 1, {'data/strmap41.dat': dat[:4] + struct.pack('<H', 2) + dat[6:]})):
        x = Exe(fs)
        n, got = x.strmap(rb, tag, en41)
        if got != rb or n or x.open:
            return False, f'{what}: {n} translated, block changed {got != rb}, open {list(x.open)}'
        out.append(f'{what}: untouched')

    cut = struct.unpack_from('<I', dat, 12 + 8 * LANG)[0] + 8 * 128     # (the section cut after its first chunk)
    x = Exe({'data/strmap41.dat': dat[:cut]})
    n, got = x.strmap(rb, 0, 1)
    first = dict(sec[:128])
    exp = [first.get(v) or v for v in lines] + [0] * (256 - len(lines))
    if lines_of(got) != exp or x.open:
        return False, f'truncated: {n} translated, lines as the first chunk {lines_of(got) == exp}, open {list(x.open)}'
    out.append(f'truncated after 1 KB: {n} (the first chunk only)')
    return True, '; '.join(out)
