"""N7 piece 3 (MC 10/11): the club registry's SWC1 section 'IT' (swe.c it_save / it_load, sreg.c at obj4+SREG_AT,
SREG_DIV at obj4+SREG_DIV_AT), on the static image of HT_N7_EXE (else c/HTn7s: the release recipe with SREG_FORCE=1 and
HOSTTEST_SYMS=1, an empty shape) with S7's shape (MC 11/11) poked into SREG_NF / SREG_NCLUB / SREG_SPEC / SREG_DIV (A =
102 Serie A, B, C + 2 x 20, B = 144 Serie D 9 x 18, no pool rows, the 36 stand-ins off the files: 262 rows, 298 idents),
and of HT_N7D_EXE (else c/HTn7r4d: the same recipe, dormant). The obj4 .bss (SWC1 and the arena) is
garbage at the start (0AAh), as DOS/4GW may leave it. A registry is compared by its state (view(): what sr_reg_build
writes; the struct's unused tail keeps the arena's bytes).

- a new career (en_finish with nothing found, then swe_st_load): SWC1's head the dormant build's, byte for byte, and
  no section; the first save writes 'IT' (344 B with its header) from the spec;
- save -> load: a registry other than the spec's (two clubs' divisions swapped) comes back (its state), SREG_LAST 1;
  the load overwrites a garbage SWC1 before any read (its bytes the block's);
- another layout (group I of 17, its last club off the files): 0, the registry the new spec's; the next save writes 'IT' again at its new
  size, cut from its place, a section after it kept;
- a corrupt section (every ident 0) and a short one: -1, the registry rebuilt - the same bytes from two garbage
  arenas;
- the dormant build: SREG_FN 0, a new career's save writes no section.
Piece 4 (n7-p4.md §3, §6b):
- SREG_WORLD the shape's world (5, World 2026-27: the SREG_FORCE build's); a career of world 4 (1984-85) and a
  world-0 save (a DIY / friendly career, a season: cw_byte 0) save no 'IT' (one in SWC1 cut), and their loads leave
  the registry as it was (SREG_LAST 0) even with an 'IT' in the block; a world-5 save loaded after them comes back
  (1, its flags) and saves the same 'IT' again;
- the section's flags: SREG_FLAGS (PENDING | season 27 << 8) saved at +8, read back by a load, 0 after sreg_new and
  after a load of another layout; the same registry with flags 0 and 3 loads as 1 both times (+8 not in the layout)."""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402
import test_swc1 as ts  # noqa: E402

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import engine  # noqa: E402
import trailer  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_N7_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTn7rf', 'SWOS', 'ITALIAN.EXE')
DORM = os.environ.get('HT_N7D_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTn7rd', 'SWOS', 'ITALIAN.EXE')
IT, HDR = 0x5449, 20
_H = open(os.path.join(TOOLS, 'swce', 'swosrules.h')).read()
FILES, CLUBS, DIVS = (int(re.search(rf'#define {k}\s+(\d+)', _H).group(1)) for k in ('SR_REG_FILES', 'SR_REG_CLUBS',
                                                                                     'SR_DIVS'))
POOL, OUT = 0xFE, 0xFF
WORLD = 5                                                   # (sreg.FORCE_WORLD: World 2026-27)
FSIZE = 2 + 2 * DIVS + 2                                   # sr_reg_file: file, ndiv, div[], size[], u16 pool
REGSIZE = 8 + FILES * FSIZE + 2 * CLUBS + FILES * 256 * 2 + FILES * 256 + 2 * FILES     # sr_registry


def spec_bytes(files):
    out = b''
    for num, divs, pool in files:
        d = bytes(x for x, _ in divs).ljust(DIVS, b'\0')
        s = bytes(n for _, n in divs).ljust(DIVS, b'\0')
        out += bytes([num, len(divs)]) + d + s + struct.pack('<H', pool)
    return out.ljust(FILES * FSIZE, b'\0')


def view(b):
    """the registry's state: what sr_reg_build writes (nfiles, nclub, their files, words, rows, the files' 256 rows);
    the rest of the struct keeps the arena's bytes, never read"""
    nf, nc = struct.unpack_from('<ii', b, 0)
    if not (0 < nf <= FILES and 0 <= nc <= CLUBS):
        return ('bad', nf, nc)
    w, at = 8 + FILES * FSIZE, 8 + FILES * FSIZE + 2 * CLUBS
    rd_, rows = at + FILES * 512, at + FILES * 512 + FILES * 256
    return (nf, nc, b[8:8 + nf * FSIZE], b[w:w + 2 * nc], b[at:at + nf * 512], b[rd_:rd_ + nf * 256],
            b[rows:rows + 2 * nf])


ITALY = [(102, [(k, 20) for k in range(5)], 0), (144, [(5 + g, 18) for g in range(9)], 0)]
ITALY_DIV = [k // 20 for k in range(100)] + [5 + g for g in range(9) for _ in range(18)] + [OUT] * 36


class N7:
    def __init__(self, exe):
        self.sy = json.load(open(exe[:-4] + '.syms.json'))
        self.uc, self.le, self.rd = ts.static_machine(exe)
        base = {1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}
        self.at = lambda m, k: base[self.sy[m][k][0] or 1] + self.sy[m][k][1]
        self.swc1 = self.at('swe', 'SWC1')
        en_read = self.at('trailer', 'en_read')
        c = self.rd(en_read, 0x60)
        self.en_n = ts._disp(self.rd, en_read, 0x60, b'\x81\xf9') if b'\x81\xf9' in c else c[c.find(b'\x83\xf9') + 2]
        self.found = ts._disp(self.rd, en_read, 0x80, b'\xc6\x81')
        self.d1 = ts._disp(self.rd, self.at('trailer', 'save_trailer'), 0x200, b'\x81\x05')   # add dword [D1], BLOCK
        st = self.at('swe', 'swe_st_save')
        if b'\x66\x83\x3d' in self.rd(st, 0x40):                  # (a career: SWE_GTYPE 4)
            self.uc.mem_write(ts._disp(self.rd, st, 0x40, b'\x66\x83\x3d'), b'\x04\x00')
        self.cwb = ts._disp(self.rd, st, 0x40, b'\x0f\xb6\x05') if b'\x0f\xb6\x05' in self.rd(st, 0x40) else None
        self.world(WORLD)
        self.uc.mem_map(ts.BUF, 0x10000)

    def world(self, n):                                         # (the career's world byte: cw_byte's SWE_CWB)
        if self.cwb is not None:
            self.uc.mem_write(self.cwb, bytes([n]))

    def w(self, a, b):
        self.uc.mem_write(a, b)

    def call(self, m, k, *args):
        return tr._call(self.uc, self.at(m, k), *args)

    def new_career(self):                                       # (new_career_defaults: en_reset, en_finish, then the
        self.w(self.found, b'\0' * (self.en_n + 1))            # after_new callbacks - swe_st_new in a registry build;
        ts._run(self.uc, self.at('trailer', 'en_finish'), tr.RET)   # no swe_st_load: the game loads nothing there,
        if 'swe_st_new' in self.sy.get('swe', {}):             # MC 13/11 - the model before hid Shaved's NOREG)
            self.call('swe', 'swe_st_new')

    def load(self, swc1):                                       # (en_read + en_finish + swe_st_load, SWC1 garbage)
        sid = engine.item_id('SWC1')
        body = struct.pack('<HH', sid, len(swc1)) + swc1
        self.w(ts.BUF, struct.pack('<HH', trailer.EN_MARK, len(body)) + body)
        self.w(self.found, b'\0' * (self.en_n + 1))
        self.w(self.d1, struct.pack('<I', 0x30000))
        self.w(self.swc1, b'\xEE' * len(swc1))
        from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBX
        ts._run(self.uc, self.at('trailer', 'en_read'), tr.RET, {UC_X86_REG_ESI: ts.BUF, UC_X86_REG_EBX: 0})
        ts._run(self.uc, self.at('trailer', 'en_finish'), tr.RET)
        self.call('swe', 'swe_st_load')


def sections(b):
    out, p = [], HDR
    while p + 4 <= len(b) and struct.unpack_from('<H', b, p)[0]:
        k, n = struct.unpack_from('<HH', b, p)
        out.append((k, b[p + 4:p + 4 + n]))
        p += 4 + n
    return out


def test_sreg():
    for e, what in ((EXE, 'HT_N7_EXE: SREG_FORCE=1 HOSTTEST_SYMS=1'), (DORM, 'HT_N7D_EXE: HOSTTEST_SYMS=1, dormant')):
        if not os.path.exists(e) or not os.path.exists(e[:-4] + '.syms.json'):
            return False, f'{e} / its .syms.json missing ({what}, the release recipe)'
    m, d = N7(EXE), N7(DORM)
    if 'sreg' not in m.sy:
        return False, 'HT_N7_EXE has no sreg (not an SREG_FORCE build)'
    errs = []
    sw = struct.unpack('<I', m.rd(m.at('sreg', 'SREG_WORLD'), 4))[0]
    if sw != WORLD or m.cwb is None:
        errs.append(f'SREG_WORLD {sw} (want {WORLD}), cw_byte\'s world byte {"not " if m.cwb is None else ""}found')
    if 'SREG_FN' in d.sy.get('swe', {}) or 'sreg' in d.sy:    # (dormant: swe.c's 'IT' code not compiled at all -
        errs.append(f'dormant: swe SREG_FN {"SREG_FN" in d.sy.get("swe", {})}, sreg linked {"sreg" in d.sy}')   # SWC1_BSS)
    if 'SREG_FN' not in m.sy.get('swe', {}):
        errs.append('SREG_FORCE build: swe.c without SREG_FN (SWC1_BSS not set)')
    reg = struct.unpack('<I', m.rd(m.at('sreg', 'SREG_REG'), 4))[0]
    if reg != m.at('swe', 'SWE_ARENA_AT'):
        errs.append(f'SREG_REG {reg:#x}, the arena {m.at("swe", "SWE_ARENA_AT"):#x}')

    def shape(files, div):
        m.w(m.at('sreg', 'SREG_NF'), struct.pack('<ii', len(files), len(div)))
        m.w(m.at('sreg', 'SREG_SPEC'), spec_bytes(files))
        m.w(m.at('sreg', 'SREG_DIV'), bytes(div).ljust(CLUBS, b'\0'))
    regb = lambda: view(m.rd(reg, REGSIZE))
    last = lambda: struct.unpack('<i', m.rd(m.at('sreg', 'SREG_LAST'), 4))[0]
    flags = lambda: struct.unpack('<I', m.rd(m.at('sreg', 'SREG_FLAGS'), 4))[0]

    def fresh():                                            # (the spec's registry, as sreg_build makes it)
        m.w(m.swc1 + 2, struct.pack('<H', WORLD))            # (SWC1's world: sreg.c's gate)
        if m.call('sreg', 'sreg_build'):
            errs.append('sreg_build refused the shape')
        return regb()
    shape(ITALY, ITALY_DIV)
    R0 = fresh()
    m.call('sreg', 'sreg_new')
    m.w(reg, b'\xAA' * REGSIZE)
    size = 32 + 4 + m.call('sreg', 'sreg_size')                 # (SWC1: 32 + the section, sreg_size 12 + 328)
    if size != 32 + 344:
        errs.append(f'SWC1 {size} B, want 32 + 344 (S7\'s shape)')

    # a new career: SWC1 (garbage .bss) zeroed and started, as the dormant build's; the first save writes 'IT'
    m.w(m.swc1, b'\xAA' * size)
    m.new_career()
    d.new_career()
    head, dhead = m.rd(m.swc1, size), d.rd(d.swc1, 32)
    if head[:2] + b'\0\0' + head[4:32] != dhead or any(head[32:]) or sections(dhead):
        errs.append(f'new career: SWC1 head {head[:HDR].hex()} vs the dormant {dhead[:HDR].hex()} (bar the world), '
                    f'{sum(map(bool, head[HDR:]))} non-zero byte(s) after it, dormant sections {sections(dhead)}')
    if regb() != R0:
        errs.append('new career: the registry not the spec\'s')
    # Shaved 13/11 (world_s7cross_down / _up: S7_NOREG at the end of season 1 of a career never saved): a new career's
    # SWC1 carries its world at once (swe_st_new), so sreg's gate is open before any save; a new world-4 career: shut
    if 'swe_st_new' in d.sy.get('swe', {}):
        errs.append('dormant: swe_st_new compiled (SWC1_BSS only)')
    for wn, open_ in ((4, False), (WORLD, True)):
        m.world(wn)
        m.new_career()
        hw, n = struct.unpack('<H', m.rd(m.swc1 + 2, 2))[0], m.call('sreg', 'sreg_size')
        if hw != wn or (n > 0) != open_:
            errs.append(f'new world-{wn} career, never saved: SWC1 world {hw}, sreg_size {n} '
                        f'(want {wn}, {"> 0" if open_ else "0"})')
    if regb() != R0:
        errs.append('new career after the world gate: the registry not the spec\'s')
    m.call('swe', 'swe_st_save')
    d.call('swe', 'swe_st_save')
    s = sections(m.rd(m.swc1, size))
    if [(k, len(b)) for k, b in s] != [(IT, 340)]:
        errs.append(f'new career, first save: sections {[(hex(k), len(b)) for k, b in s]} (want IT 340)')
    if sections(d.rd(d.swc1, 32)):
        errs.append(f'dormant save: sections {sections(d.rd(d.swc1, 32))}')

    # save -> load: a registry other than the spec's (club 0, Serie A, and club 150, Serie D group 3, swapped)
    D2 = list(ITALY_DIV)
    D2[0], D2[150] = D2[150], D2[0]
    shape(ITALY, D2)
    R2 = fresh()
    if R2 == R0:
        errs.append('the swapped divisions built the spec\'s registry')
    m.call('swe', 'swe_st_save')
    S2 = m.rd(m.swc1, size)
    shape(ITALY, ITALY_DIV)
    m.w(reg, b'\x55' * REGSIZE)
    m.load(S2)
    if m.rd(m.swc1, size) != S2:
        errs.append('load: SWC1 not the block\'s bytes')
    if last() != 1 or regb() != R2:
        errs.append(f'save -> load: SREG_LAST {last()}, registry {"=" if regb() == R2 else "!="} the saved one')

    # another layout (group I of 17, its last club off): 0, the new spec's registry; the next save cuts 'IT', keeps 'ZZ'
    ITALY35 = [ITALY[0], (144, ITALY[1][1][:8] + [(13, 17)], 0)]
    D35 = ITALY_DIV[:261] + [OUT] + ITALY_DIV[262:]
    shape(ITALY35, D35)
    R35 = fresh()
    m.call('sreg', 'sreg_new')
    zz = struct.pack('<HH', 0x5A5A, 4) + b'zzzz'
    S2z = S2[:HDR + 4 + 340] + zz + S2[HDR + 4 + 340 + len(zz):]
    m.load(S2z)
    if last() != 0 or regb() != R35:
        errs.append(f'another layout: SREG_LAST {last()}, registry {"=" if regb() == R35 else "!="} the new spec\'s')
    m.call('swe', 'swe_st_save')
    s = sections(m.rd(m.swc1, size))
    if [(k, len(b)) for k, b in s] != [(0x5A5A, 4), (IT, 339)] or s[0][1] != b'zzzz':
        errs.append(f'another layout, save: sections {[(hex(k), len(b)) for k, b in s]} (want ZZ 4 kept, IT 339)')

    # the flags: PENDING | season 27 << 8 saved at the section's +8, back after a load; 0 after sreg_new, and after
    # a load of another layout (S2z under ITALY35 above: a different layout)
    shape(ITALY, ITALY_DIV)
    fresh()
    FL = 2 | 27 << 8
    m.w(m.at('sreg', 'SREG_FLAGS'), struct.pack('<I', FL))
    m.call('swe', 'swe_st_save')
    SF = m.rd(m.swc1, size)
    it = dict(sections(SF)).get(IT, b'')
    if it[8:10] != struct.pack('<H', FL):
        errs.append(f'flags: the section\'s +8 {it[8:10].hex()} (want {FL:04x})')
    m.call('sreg', 'sreg_new')
    if flags():
        errs.append(f'flags: {flags():#x} after sreg_new')
    m.load(SF)
    if last() != 1 or flags() != FL:
        errs.append(f'flags: load {last()}, SREG_FLAGS {flags():#x} (want 1, {FL:#x})')
    S3 = bytearray(SF)                                      # (flags 3, the same registry: the layout check does
    o3, p3 = None, HDR                                      #  not hash +8 - loads as 1, the flags back)
    while o3 is None and struct.unpack_from('<H', SF, p3)[0]:
        k3, n3 = struct.unpack_from('<HH', SF, p3)
        o3, p3 = (p3 + 4 + 8 if k3 == IT else None), p3 + 4 + n3
    S3[o3:o3 + 2] = struct.pack('<H', 3)
    S0 = bytearray(SF)
    S0[o3:o3 + 2] = b'\0\0'
    for fl, blk in ((0, S0), (3, S3)):
        m.call('sreg', 'sreg_new')
        m.load(bytes(blk))
        if last() != 1 or flags() != fl:
            errs.append(f'flags {fl}: load {last()}, SREG_FLAGS {flags():#x} (want 1, {fl:#x})')
    shape(ITALY35, D35)
    m.load(SF)
    if last() != 0 or flags():
        errs.append(f'flags: another layout\'s load {last()}, SREG_FLAGS {flags():#x} (want 0, 0)')

    # the world gate: a world-4 (1984-85) career and a world-0 save (a DIY / friendly career, a season: cw_byte 0)
    # save no 'IT' (one there cut), and their loads leave the registry alone; then a world-5 save beside them still
    # round-trips (its 'IT' read back, the same section written again)
    shape(ITALY, ITALY_DIV)
    R = fresh()
    for wn in (4, 0):
        m.load(SF)                                          # (SWC1 holds an 'IT' before the save: it must go)
        m.world(wn)
        m.call('swe', 'swe_st_save')
        s4 = m.rd(m.swc1, size)
        if struct.unpack_from('<H', s4, 2)[0] != wn or IT in dict(sections(s4)):
            errs.append(f'world {wn}: SWC1 world {struct.unpack_from("<H", s4, 2)[0]}, sections '
                        f'{[(hex(k), len(b)) for k, b in sections(s4)]} (want {wn}, no IT)')
        S4 = SF[:2] + struct.pack('<H', wn) + SF[4:]           # (an 'IT' in a world-4 / world-0 block: never read)
        m.call('sreg', 'sreg_new')
        m.load(S4)
        if last() != 0 or regb() != R or flags():
            errs.append(f'world {wn} load: SREG_LAST {last()}, registry {"kept" if regb() == R else "changed"}, '
                        f'flags {flags():#x} (want 0, kept, 0)')
    m.world(WORLD)
    m.call('sreg', 'sreg_new')
    m.load(SF)
    m.call('swe', 'swe_st_save')
    it5, itf = dict(sections(m.rd(m.swc1, size))).get(IT), dict(sections(SF)).get(IT)
    if last() != 1 or flags() != FL or it5 is None or it5 != itf:
        errs.append(f'world 5 after them: load {last()}, flags {flags():#x}, IT {"=" if it5 == itf else "!="} the '
                    f'saved one (want 1, {FL:#x}, =)')

    # corrupt (every ident 0) and short: -1, rebuilt - the same bytes from two garbage arenas
    shape(ITALY, ITALY_DIV)
    bad = S2[:HDR + 4 + 12] + bytes(328) + S2[HDR + 4 + 340:]
    short = S2[:HDR] + struct.pack('<HH', IT, 5) + S2[HDR + 4:HDR + 9] + bytes(size - HDR - 9)
    for tag, blk in (('corrupt', bad), ('short', short)):
        got = []
        for g in (b'\x11', b'\xC3'):
            m.w(reg, g * REGSIZE)
            m.load(blk)
            got.append((last(), regb()))
        if any(x != -1 for x, _ in got) or got[0][1] != got[1][1] or got[0][1] != R0:
            errs.append(f'{tag}: SREG_LAST {[x for x, _ in got]}, rebuilt {"the same" if got[0][1] == got[1][1] else "differently"}'
                        f', {"=" if got[0][1] == R0 else "!="} the spec\'s')
    return not errs, '; '.join(errs) or ('new career = the dormant head + IT 340 at the first save; save -> load of a '
                                         'non-spec registry 1, its state back; another layout 0 + IT cut (ZZ kept); '
                                         'corrupt / short -1, the same rebuild twice; flags saved + loaded; worlds 4 and 0: no IT, load '
                                         'ignored, world 5 round-trips after them; dormant: no sreg, no section')


def test_sreg_shape():
    """sreg.shape_of on a pack's files / clubs (n7-p4.md §1-§2): S7's shape (MC 11/11) from an S7-like pack (102 Serie
    A, B, C + 2, 144 Serie D 9 x 18, the 36 stand-ins off the files in role 'pool') = test_sreg's ITALY / ITALY_DIV, its
    SREG_SPEC bytes = spec_bytes'; refused: a club out of its file's division order, pool_rows not its pool clubs, a
    division its file does not hold, an empty division, a registry-file club with no division."""
    import types
    import sreg
    fs = {'league': {'file': 102, 'base': 92, 'divisions': [0, 1, 2, 3, 4]},
          'league_b': {'file': 144, 'base': 160, 'divisions': list(range(5, 14))},
          'pool': {'file': 253, 'base': 0}}
    rows = ([('league', str(d)) for d in ITALY_DIV[:100]] + [('league_b', str(d)) for d in ITALY_DIV[100:262]] +
            [('pool', '')] * 36)

    def pk(rs, files=fs):
        return types.SimpleNamespace(meta={'files': files}, clubs={f'c{i}': {'file': f, 'division': d}
                                                                   for i, (f, d) in enumerate(rs)}, world=5, path='t')
    errs = []
    got = sreg.shape_of(pk(rows))
    if got != (5, ITALY, ITALY_DIV):
        errs.append(f'S7 shape: {got[1] if got else got}')
    elif sreg.spec_bytes(ITALY, FILES, DIVS) != spec_bytes(ITALY):
        errs.append('spec_bytes differs from the host test\'s')
    swap = [rows[100]] + rows[:100] + rows[101:]            # (a Serie D club first in clubs.csv: another file - ok;
    swap2 = list(rows)                                      #  a Serie B club before a Serie A one: refused)
    swap2[0], swap2[30] = swap2[30], swap2[0]
    nopool = dict(fs, league_b=dict(fs['league_b'], pool_rows=1))   # (pool_rows with no pool clubs)
    nodiv = list(rows)
    nodiv[5] = ('league', '7')
    empty = dict(fs, league=dict(fs['league'], divisions=[0, 1, 2, 3, 4, 14]))
    blank = list(rows)
    blank[3] = ('league', '')
    for tag, p, want in (('Serie D club first (another file)', pk(swap), None), ('B before A', pk(swap2), 'order'),
                         ('pool_rows 1', pk(rows, nopool), 'pool_rows'), ('a division off its file', pk(nodiv),
                         'does not hold'), ('an empty division', pk(rows, empty), 'rows'),
                         ('no division', pk(blank), 'needs a division')):
        try:
            sreg.shape_of(p)
            if want:
                errs.append(f'{tag}: accepted')
        except AssertionError as e:
            if not want or want not in str(e):
                errs.append(f'{tag}: {e}')
    return not errs, '; '.join(errs) or ('S7 shape + SREG_SPEC bytes from an S7-like pack; refused: order, '
                                         'pool_rows, off-file division, empty division, no division')


def test_sreg_walk():
    """sreg_walk.c (n7-p4.md §4 step 3) built natively: WS_W / WS_G lines over a buffer through a sorted word map
    (sr_wpair, as sr_wmap_import returns it; an italy42-like move: (102, 120) -> (144, 20), (102, 130) -> (144, 30), (102, 5) unchanged).
    W: mapped words rewritten, 0 / FFFFh and unmapped words kept, the count of changes returned; G: globals of file
    102 (base 92) to file 144's (base G144 = 400 here, a test value), another country's global kept; a line past the
    bytes -1 with nothing written; O8 / K -2."""
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, 'w.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n#include "{TOOLS}/sreg_walk.c"\n')
    lib = os.path.join(d, 'w.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-I', os.path.join(TOOLS, 'swce'), '-o', lib, src],
                       capture_output=True, text=True)
    if r.returncode:
        return False, 'cc: ' + r.stderr[-300:]
    L = ctypes.CDLL(lib)
    pairs = sorted([(102 | 120 << 8, 144 | 20 << 8), (102 | 130 << 8, 144 | 30 << 8)])
    m = (ctypes.c_uint16 * 4)(*[x for p in pairs for x in p])
    g = struct.pack('<BBH', 102, 0, 92) + struct.pack('<BBH', 144, 0, 400) + struct.pack('<BBH', 120, 30, 600)

    def walk(site, buf):
        b = (ctypes.c_uint8 * len(buf)).from_buffer(buf)
        s = ctypes.create_string_buffer(struct.pack('<HHHHBB', *site), 10)
        return L.sreg_walk_site(s, b, len(buf), m, 2, ctypes.create_string_buffer(g, len(g)), 3)
    errs = []
    W = [102 | 120 << 8, 0, 0xFFFF, 102 | 5 << 8, 102 | 130 << 8, 161 | 3 << 8]
    buf = bytearray(b'\xAA' * 2 + b''.join(struct.pack('<HH', w, 0x1234) for w in W))
    n = walk((0, 2, 4, len(W), 1, 0), buf)
    got = [struct.unpack_from('<H', buf, 2 + 4 * k)[0] for k in range(len(W))]
    want = [144 | 20 << 8, 0, 0xFFFF, 102 | 5 << 8, 144 | 30 << 8, 161 | 3 << 8]
    if n != 2 or got != want or buf[:2] != b'\xAA\xAA' or any(struct.unpack_from('<H', buf, 4 + 4 * k)[0] != 0x1234
                                                              for k in range(len(W))):
        errs.append(f'W: {n} changed, {[hex(x) for x in got]}')
    G = [92 + 120, 92 + 5, 92 + 130, 600 + 3, 7]
    buf = bytearray(b''.join(struct.pack('<H', x) for x in G))
    n = walk((0, 0, 2, len(G), 2, 0), buf)
    got = list(struct.unpack(f'<{len(G)}H', buf))
    if n != 2 or got != [400 + 20, 92 + 5, 400 + 30, 600 + 3, 7]:
        errs.append(f'G: {n} changed, {got}')
    buf = bytearray(struct.pack('<4H', 102 | 120 << 8, 0, 0, 0))
    before = bytes(buf)
    if walk((0, 0, 4, 3, 1, 0), buf) != -1 or bytes(buf) != before:
        errs.append('past the bytes: not -1, or written')
    if walk((0, 0, 2, 1, 3, 0xFF), bytearray(4)) != -2 or walk((0, 0, 2, 1, 4, 0), bytearray(4)) != -2:
        errs.append('O8 / K: not -2')
    return not errs, '; '.join(errs) or 'W: 2 mapped words rewritten, none / unmapped / other files kept; G: 102 -> 144 ' \
                                         'globals, others kept; past the bytes -1, untouched; O8 / K -2'


def test_sreg_oldwords():
    """sreg_import.c (n7-p4.md §4 step 1) built natively: sreg_old_words from old_ord (a row 0..255, or 256 + a pool
    index, or FFFFh) and an RI slot map (gplay ri_apply: maps[x] 0 = its own record, else identity maps[x] - 1).
    No map: rows -> their slot's word, pool / none -> SR_REG_NONE. Swaps (two season ends: pool 0 and pool 1 on slots
    0 and 1, row 1 on slot 2): the rows swapped off -> NONE, each club on its current slot. Refused: an identity on
    two slots (-1), an identity past RIS + npool (-1), nslot past RIS (-2)."""
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, 'o.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n'
                f'#include "{TOOLS}/sreg_import.c"\n')
    lib = os.path.join(d, 'o.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-I', os.path.join(TOOLS, 'swce'), '-o', lib, src],
                       capture_output=True, text=True)
    if r.returncode:
        return False, 'cc: ' + r.stderr[-300:]
    L = ctypes.CDLL(lib)
    NONE, W = 0xFFFF, lambda x: 102 | x << 8
    old = [0, 1, 2, 256, 257, 0xFFFF]

    def run(maps, nslot=3, npool=2):
        o = (ctypes.c_uint16 * len(old))(*old)
        w = (ctypes.c_uint16 * len(old))(*([0x5A5A] * len(old)))
        m = (ctypes.c_uint16 * len(maps))(*maps) if maps is not None else None
        n = L.sreg_old_words(o, len(old), m, nslot, npool, 102, w)
        return n, list(w)
    errs = []
    for tag, maps, want in (('no map', None, (3, [W(0), W(1), W(2), NONE, NONE, NONE])),
                            ('no swaps', [0, 0, 0], (3, [W(0), W(1), W(2), NONE, NONE, NONE])),
                            ('swaps', [257, 258, 2], (3, [NONE, W(2), NONE, W(0), W(1), NONE]))):
        got = run(maps)
        if got != want:
            errs.append(f'{tag}: {got[0]} {[hex(x) for x in got[1]]}')
    for tag, maps, nslot, want in (('two slots', [0, 1, 0], 3, -1), ('past the pool', [0, 0, 259], 3, -1),
                                   ('nslot 257', None, 257, -2)):
        if run(maps, nslot)[0] != want:
            errs.append(f'{tag}: {run(maps, nslot)[0]}')
    return not errs, '; '.join(errs) or ('old words: no map / swaps -> each club on its current slot, the rest NONE; '
                                         'refused: one identity on two slots, past the pool, nslot past RIS')


def _imp_protos(L):
    """sreg_import / sreg_ri_import's prototypes (Apple arm64 packs small stack arguments: ctypes must know the u8s)"""
    import ctypes
    P, I32, U8, U32 = ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint8, ctypes.c_uint32
    L.sreg_import.argtypes = [P, P, I32, P, I32, P, P, I32, I32, U8, P, P, I32, U8, U32, P, P, I32, P, I32, P]
    L.sreg_import.restype = I32
    if hasattr(L, 'sreg_ri_import'):
        L.sreg_ri_import.argtypes = [P, P, I32, P, I32, P, P, I32, P, I32, P, P, U8, U8, U8, P, P, P, P]
        L.sreg_ri_import.restype = I32
    if hasattr(L, 'sreg_slt_import'):
        L.sreg_slt_import.argtypes = [P, P, I32, P, P, P, P, I32, P, P, I32, P]
        L.sreg_slt_import.restype = I32


def test_sreg_import():
    """sreg_import (sreg_import.c, n7-p4.md §9c, MC's option 1) built natively, on a small S7-like shape: file 102 =
    division 0 (4 clubs) + 1 (4), file 144 = Serie D groups 5 and 6 (3 each) + 2 pool rows; 16 idents: a0..a3, b0..b3
    (4.1 rows 0..7), d0 d1 (rows 8, 9) + J (a joiner: 4.1 pool 0) in group 5, e0..e2 (rows 10..12) in group 6, p1 p2 (4.1
    pool 1, 2) on the pool rows. 4.1 had one file of 13 slots and a pool of 3.
    - a fresh 4.1 save: no swap, every club its spec division, J pending (flags IMPORTED | PENDING | season 27 << 8),
      the map = the 5 Serie D words 102 -> 144;
    - after season ends: b0 (div 1) down to group 5 and d0 up to 1 (one cross-file swap), a3 / b1 traded 0 <-> 1 in
      file 102 (no row moves, only the division), RI: p1 onto d1's slot 9 (group 5), d1 off -> the pool: every club's
      registry division = its actual one (J's spec), the map follows every club on a slot;
    - deterministic: two imports from different garbage give the same registry, swaps, map and result;
    - J swapped on by RI (option B, MC 12/11): an ordinary club on its slot, not pending; S7's no-pool shape: the free
      144 row to a filler (a spec Serie D club off the files) in the RI queue's order, then spec order (a queue cut
      short / empty), none left: DRY; a stand-in on a slot RI promoted into division 1 goes off, its slot word and
      division to the next filler (MC 12/11: was RI_KIND);
    - refused, with the club: a club down to group 6 with nobody up (BALANCE, it), a
      division byte the registry lacks (DIV), an identity on two slots (MAP), a slot no ident has (LOST, 0x8000 | slot),
      room for no swap (ROOM)."""
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, 'i.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n'
                f'#include "{TOOLS}/sreg_import.c"\n'
                'uint32_t imp_work_size(void) { return sizeof(sreg_imp_work); }\n'
                'uint32_t imp_res_size(void) { return sizeof(sreg_imp_res); }\n')
    lib = os.path.join(d, 'i.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-Wall', '-Werror', '-I', os.path.join(TOOLS, 'swce'), '-o',
                        lib, src], capture_output=True, text=True)
    if r.returncode:
        return False, 'cc: ' + r.stderr[-400:]
    L = ctypes.CDLL(lib)
    _imp_protos(L)
    W102, W144 = (lambda x: 102 | x << 8), (lambda x: 144 | x << 8)
    names = ['a0', 'a1', 'a2', 'a3', 'b0', 'b1', 'b2', 'b3', 'd0', 'd1', 'J', 'e0', 'e1', 'e2', 'p1', 'p2']
    I = {k: i for i, k in enumerate(names)}
    sdiv = [0] * 4 + [1] * 4 + [5] * 3 + [6] * 3 + [POOL] * 2
    old = list(range(10)) + [256] + [10, 11, 12] + [257, 258]
    spec = spec_bytes([(102, [(0, 4), (1, 4)], 0), (144, [(5, 3), (6, 3)], 2)])
    slot0 = [0] * 4 + [1] * 4 + [5, 5] + [6] * 3
    IMP = {-1: 'ARGS', -2: 'SPEC', -3: 'MAP', -4: 'LOST', -5: 'DIV', -7: 'PEND', -8: 'BALANCE', -9: 'ROOM',
           -10: 'WMAP', -11: 'DRY'}

    def imp(maps=None, slot=slot0, maxsw=64, fill=0xAA, spec=spec, sdiv=sdiv, queue=()):
        R = ctypes.create_string_buffer(bytes([fill]) * REGSIZE, REGSIZE)
        wk = ctypes.create_string_buffer(bytes([fill ^ 0x55]) * L.imp_work_size(), L.imp_work_size())
        res = ctypes.create_string_buffer(L.imp_res_size())
        sw = (ctypes.c_uint16 * (3 * 64))(*([0x5A5A] * 192))
        mp = (ctypes.c_uint16 * (2 * 64))(*([0x5A5A] * 128))
        m = (ctypes.c_uint16 * 13)(*maps) if maps else None
        q = (ctypes.c_uint16 * len(queue))(*queue) if queue else None
        n = L.sreg_import(R, ctypes.create_string_buffer(spec, len(spec)), 2, bytes(sdiv), len(names),
                          (ctypes.c_uint16 * len(old))(*old), m, 13, 3, 102, bytes(slot), q, len(queue), 144, 27, wk,
                          sw, maxsw, mp, 64, res)
        nswap, nmap, npend, bad, flags = struct.unpack_from('<iiiiI', res.raw, 0)
        pend = list(struct.unpack_from(f'<{npend}H', res.raw, 20)) if n >= 0 else []
        b = R.raw
        words = struct.unpack_from(f'<{len(names)}H', b, 8 + FILES * FSIZE)
        at = 8 + FILES * FSIZE + 2 * CLUBS
        rdiv = at + FILES * 512

        def div(c):                                     # sr_reg_div: its row's division
            w = words[c]
            if w == 0xFFFF:
                return OUT
            fi = {102: 0, 144: 1}[w & 0xFF]
            return b[rdiv + 256 * fi + (w >> 8)]
        return dict(n=n, why=IMP.get(n, n), bad=bad, flags=flags, pend=pend,
                    swaps=[tuple(sw[3 * k:3 * k + 3]) for k in range(max(n, 0))],
                    pairs=[tuple(mp[2 * k:2 * k + 2]) for k in range(nmap if n >= 0 else 0)],
                    words=words, divs=[div(c) for c in range(len(names))], view=view(b))
    errs = []
    # a fresh 4.1 save
    g = imp()
    want_pairs = sorted([(W102(8), W144(0)), (W102(9), W144(1)), (W102(10), W144(3)), (W102(11), W144(4)),
                         (W102(12), W144(5))])
    if (g['n'], g['pend'], g['flags'], g['divs'], g['pairs']) != (0, [I['J']], 1 | 2 | 27 << 8, sdiv, want_pairs):
        errs.append(f"fresh: {g['why']} pend {g['pend']} flags {g['flags']:#x} divs {g['divs']} pairs {g['pairs']}")
    # after season ends: b0 down to 5, d0 up to 1, a3 <-> b1 in file 102, RI: p1 (identity 257) on slot 9, d1 off
    maps = [0] * 13
    maps[9] = 257 + 1
    slot = list(slot0)
    slot[4], slot[8], slot[3], slot[5] = 5, 1, 1, 0
    g = imp(maps, slot)
    act = list(sdiv)
    act[I['b0']], act[I['d0']], act[I['a3']], act[I['b1']], act[I['p1']], act[I['d1']] = 5, 1, 1, 0, 5, POOL
    if g['n'] != 1 or g['divs'] != act or g['pend'] != [I['J']]:
        errs.append(f"seasons: {g['why']} {g['swaps']} divs {g['divs']} pend {g['pend']}")
    else:
        if sorted(g['swaps'][0][:2]) != sorted([W102(4), W144(0)]) or g['swaps'][0][2] != 0xFFFF:
            errs.append(f"seasons: swap {[hex(x) for x in g['swaps'][0]]}")
        if g['words'][I['b0']] != W144(0) or g['words'][I['d0']] != W102(4) or g['words'][I['p1']] != W144(6):
            errs.append(f"seasons: words b0 {g['words'][I['b0']]:#x} d0 {g['words'][I['d0']]:#x} "
                        f"p1 {g['words'][I['p1']]:#x}")
        pm = dict(g['pairs'])                           # every club on a 4.1 slot -> its word now
        for c in range(len(names)):
            ow = None
            if old[c] < 256 and maps[old[c]] == 0:
                ow = W102(old[c])
            elif old[c] == 257:
                ow = W102(9)
            if ow is not None and pm.get(ow, ow) != g['words'][c]:
                errs.append(f'seasons: map {names[c]} {ow:#x} -> {pm.get(ow, ow):#x}, now {g["words"][c]:#x}')
        if W102(9) not in pm or pm[W102(9)] != W144(6):
            errs.append('seasons: the slot RI gave p1 not mapped to its row')
    g2 = imp(maps, slot, fill=0x33)
    if any(g[k] != g2[k] for k in ('n', 'bad', 'flags', 'pend', 'swaps', 'pairs', 'words', 'divs', 'view')):
        errs.append('not deterministic (two garbage fills)')
    # refusals
    m6 = [0] * 13
    m6[9] = 256 + 1                                     # J swapped on (d1 off)
    s_bal = list(slot0)
    s_bal[I['b2']] = 6
    s_div = list(slot0)
    s_div[10] = 9                                       # (slot 10 = e0's)
    m2 = [0] * 13
    m2[3] = 2 + 1                                       # identity 2 on slots 2 and 3
    m_lost = [0] * 13
    g = imp(maps=m6)                                    # (option B, MC 12/11: J on a slot = an ordinary club there)
    if g['n'] < 0 or g['pend'] or g['words'][I['J']] == 0xFFFF or g['divs'][I['J']] != 5:
        errs.append(f"J swapped on (pool rows): {g['why']} bad {g['bad']} pend {g['pend']} J div {g['divs'][I['J']]}")
    for tag, kw, want in (('down, nobody up', dict(slot=s_bal), ('BALANCE', I['b2'])),
                          ('unknown division', dict(slot=s_div), ('DIV', I['e0'])),
                          ('two slots', dict(maps=m2), ('MAP', -1)),
                          ('no swap room', dict(maps=maps, slot=slot, maxsw=0), ('ROOM', -1))):
        g = imp(**kw)
        if (g['why'], g['bad']) != want:
            errs.append(f"{tag}: {g['why']} bad {g['bad']}")
    # S7 as MC 11/11: file 144 = the groups only, p1 p2 off the files (OUT); the same season ends: p1 onto 144 from the
    # pool (a pool swap: d1's row), d1 off the files
    spec0 = spec_bytes([(102, [(0, 4), (1, 4)], 0), (144, [(5, 3), (6, 3)], 0)])
    sdiv0 = sdiv[:14] + [OUT] * 2
    g = imp(maps, slot, spec=spec0, sdiv=sdiv0)
    act0 = list(act)
    act0[I['d1']], act0[I['p2']] = OUT, OUT
    divs0 = g['divs']
    pm = dict(g['pairs'])
    if g['n'] != 2 or divs0 != act0 or g['words'][I['p1']] != W144(1) or g['words'][I['d1']] != 0xFFFF or \
            pm.get(W102(9)) != W144(1) or (W144(1), 0xFFFF, I['p1']) not in g['swaps']:
        errs.append(f"no pool rows: {g['why']} {g['swaps']} divs {divs0} p1 {g['words'][I['p1']]:#x}")
    f0 = imp(spec=spec0, sdiv=sdiv0)
    if (f0['n'], f0['pend']) != (0, [I['J']]):
        errs.append(f"no pool rows, fresh: {f0['why']} pend {f0['pend']}")
    # option B (MC 12/11, n7-six-real.md): J already on a slot (slot 9: d1 off) is ordinary; 144's free row goes to a
    # filler - a spec Serie D club off the files - in the save's RI queue order, then (the queue short) in spec order
    g = imp(m6, spec=spec0, sdiv=sdiv0, queue=[9, 257, 258])
    if g['n'] < 0 or g['pend'] != [I['d1']] or g['divs'][I['J']] != 5 or g['divs'][I['d1']] != 5 or \
            g['flags'] != 1 | 2 | 27 << 8:
        errs.append(f"B, J on a slot: {g['why']} bad {g['bad']} pend {g['pend']} flags {g['flags']:#x}")
    m7 = list(m6)
    m7[12] = 258 + 1                                    # (p2 on e2's slot 12: d1 and e2 both off, one free row)
    for tag, q, want in (('queue order', [12, 9, 257], 'e2'), ('queue cut short', [257], 'd1'), ('no queue', [], 'd1')):
        g = imp(m7, spec=spec0, sdiv=sdiv0, queue=q)
        if g['n'] < 0 or g['pend'] != [I[want]] or g['words'][I['e2' if want == 'd1' else 'd1']] != 0xFFFF:
            errs.append(f"B, filler by {tag}: {g['why']} bad {g['bad']} pend {[names[c] for c in g['pend']]} (want {want})")
    s_dry = list(slot0)
    s_dry[9] = 1                                        # (d1 up to division 1; J on b3's slot 7, now division 5)
    s_dry[7] = 5
    m_dry = [0] * 13
    m_dry[7] = 256 + 1
    g = imp(m_dry, s_dry, spec=spec0, sdiv=sdiv0, queue=[7, 257, 258])
    if (g['why'], g['bad']) != ('DRY', -1):
        errs.append(f"B, no filler at all: {g['why']} bad {g['bad']} (want DRY, -1)")
    # the substitution (MC 12/11, was RI_KIND): p1 on 4.1 slot 4 (division 1: Serie C) through RI, b0 off; p2 on slot 9,
    # d1 off. p1 goes off the files; slot 4 (its word, division 1) goes to the next filler, d1 (queue [J, b0, d1])
    m8 = [0] * 13
    m8[4], m8[9] = 257 + 1, 258 + 1
    g = imp(m8, spec=spec0, sdiv=sdiv0, queue=[256, 4, 9])
    pm = dict(g['pairs'])
    if g['n'] < 0 or g['words'][I['p1']] != 0xFFFF or g['divs'][I['d1']] != 1 or g['pend'] != [I['J']] or \
            g['words'][I['d1']] & 0xFF != 102 or pm.get(W102(4), W102(4)) != g['words'][I['d1']] or \
            g['divs'][I['p2']] != 5 or W102(4) in [b for _, b in g['pairs']] and pm.get(W102(4)) is None:
        errs.append(f"B, stand-in in Serie C substituted: {g['why']} bad {g['bad']} p1 {g['words'][I['p1']]:#x} d1 "
                    f"{g['words'][I['d1']]:#x} div {g['divs'][I['d1']]} map 102|4 -> {pm.get(W102(4), W102(4)):#x} pend {g['pend']}")
    g2 = imp(m8, spec=spec0, sdiv=sdiv0, queue=[256, 4, 9], fill=0x33)
    if any(g[k] != g2[k] for k in ('n', 'bad', 'flags', 'pend', 'swaps', 'pairs', 'words', 'divs', 'view')):
        errs.append('B, substitution: not deterministic')
    old_l = list(old)
    old[I['e2']] = 0xFFFF                               # slot 12's club unknown to the pack (e2 a new club: pending)
    g = imp(m_lost)
    if (g['why'], g['bad']) != ('LOST', 0x8000 | 12):
        errs.append(f"lost slot: {g['why']} bad {g['bad']:#x}")
    old[:] = old_l
    return not errs, '; '.join(errs) or ('fresh: no swap, J pending, 5 Serie D words to 144; seasons: 1 cross-file '
                                         'swap, every division the save\'s, map follows each club, RI slot -> pool row; '
                                         'deterministic; no pool rows (S7 11/11): the stand-in on by a pool swap, the club off OUT; '
                                         'option B: J on a slot ordinary, the free row to a filler by queue order / spec '
                                         'order (queue short or empty), none: DRY; a stand-in in Serie C substituted '
                                         '(off, its slot to the filler); refused BALANCE / DIV / MAP / ROOM / LOST with '
                                         'the club')


def test_sreg_riimport():
    """sreg_ri_import (sreg_import.c, MC 11/11 model (i)) built natively on test_sreg_import's no-pool shape (102 =
    divisions 0, 1 x 4; 144 = groups 5, 6 x 3; J the joiner, p1 p2 the stand-ins, 4.1 pool 0, 1, 2). Two RI tables:
    4.1 = another file (161, 4 slots, pools of 2 and 1) then Italy (102, 13 slots, pool 3); S7 = Italy (144, 6 slots,
    pool 2) then 161: 161's init / maps / queues / overrides land at their new offsets byte for byte.
    - an RI season end (p1 on 4.1 slot 9, d1 queued as identity 9; b0 / d0 traded across files): map[1] = p1's S7
      identity (256 + 0) + 1, the record at row 1 still d1's; the queue J (out: joiner), p2 -> 257, d1 -> 1;
    - a Serie C club relegated twice (b3: 4.1 slot 7 holds p2, b3 queued as 7): the import's cross-file move carries
      b3's record to 144 row 0, so b3's identity is 0 and map[0] = p2's (257) + 1;
    - a stand-in RI-promoted into Serie C (p1 on 4.1 slot 4, p2 on d1's slot 9, queue J / b0 / d1): substituted (MC
      12/11, option B): J and d1 (the filler on slot 4) leave the queue, b0 -> its record's row, p1 at the tail;
    - init 0 (no RI season end): Italy's state empty; deterministic (two garbage fills);
    - refused: an identity no club has (QUEUE), newpool not 0xFF for J (POOLMAP),
      161 with another slot count (LAYOUT), init 0 with a pool swap (LAYOUT)."""
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, 'r.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n'
                f'#include "{TOOLS}/sreg_import.c"\n'
                'uint32_t imp_work_size(void) { return sizeof(sreg_imp_work); }\n'
                'uint32_t imp_res_size(void) { return sizeof(sreg_imp_res); }\n'
                'uint32_t ri_work_size(void) { return sizeof(sreg_ri_work); }\n')
    lib = os.path.join(d, 'r.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-Wall', '-Werror', '-I', os.path.join(TOOLS, 'swce'), '-o',
                        lib, src], capture_output=True, text=True)
    if r.returncode:
        return False, 'cc: ' + r.stderr[-400:]
    L = ctypes.CDLL(lib)
    _imp_protos(L)
    names = ['a0', 'a1', 'a2', 'a3', 'b0', 'b1', 'b2', 'b3', 'd0', 'd1', 'J', 'e0', 'e1', 'e2', 'p1', 'p2']
    I = {k: i for i, k in enumerate(names)}
    sdiv = [0] * 4 + [1] * 4 + [5] * 3 + [6] * 3 + [OUT] * 2
    old = list(range(10)) + [256] + [10, 11, 12] + [257, 258]
    spec = spec_bytes([(102, [(0, 4), (1, 4)], 0), (144, [(5, 3), (6, 3)], 0)])
    slot0 = [0] * 4 + [1] * 4 + [5, 5] + [6] * 3
    RI = {0: 'ok', -21: 'ARGS', -22: 'LAYOUT', -23: 'KIND', -24: 'NOID', -25: 'QUEUE', -27: 'POOLMAP'}

    def lay(files):                                 # sreg.ri_layout's bytes
        return bytes([len(files)]) + b''.join(bytes([w, fl]) + struct.pack('<HH', mo, nm) + bytes([len(ns)]) +
                                              bytes(ns) for w, fl, mo, nm, ns in files)
    OLD = lay([(5, 161, 0, 4, [2, 1]), (5, 102, 4, 13, [3])])
    NEW = lay([(5, 144, 0, 6, [2]), (5, 161, 6, 4, [2, 1])])

    def ri_state(init, qn, q, ovr, maps):
        b = bytearray(2332)
        b[0:len(init)] = bytes(init)
        b[8:8 + len(qn)] = bytes(qn)
        for k, v in q.items():
            struct.pack_into('<H', b, 28 + 2 * k, v)
        for (p, j), v in ovr.items():
            struct.pack_into('<H', b, 412 + 2 * (16 * p + j), v)
        for k, v in maps.items():
            struct.pack_into('<H', b, 1052 + 2 * k, v)
        return bytes(b)
    # 161's part (file index 0, pools 0 and 1, queue words 0..2, maps 0..3) - arbitrary bytes, moved as they are
    B161 = dict(init=[2], qn=[2, 1], q={0: 0x0101, 1: 0x0202, 2: 0x8003}, ovr={(0, 3): 0x2A1, (1, 0): 0x3A1},
                maps={0: 7, 1: 0, 2: 300, 3: 1})

    def run(maps41, slot, q41, init=2, newpool=(0xFF, 0, 1), fill=0xAA, new=NEW):
        R = ctypes.create_string_buffer(bytes([fill]) * REGSIZE, REGSIZE)
        wk = ctypes.create_string_buffer(bytes([fill]) * L.imp_work_size(), L.imp_work_size())
        res = ctypes.create_string_buffer(L.imp_res_size())
        sw = (ctypes.c_uint16 * 192)()
        mp = (ctypes.c_uint16 * 128)()
        m = (ctypes.c_uint16 * 13)(*maps41)
        sp = ctypes.create_string_buffer(spec, len(spec))
        oo = (ctypes.c_uint16 * len(old))(*old)
        qq = (ctypes.c_uint16 * len(q41))(*q41) if q41 else None
        n = L.sreg_import(R, sp, 2, bytes(sdiv), len(names), oo, m, 13, 3, 102, bytes(slot), qq, len(q41), 144, 27, wk,
                          sw, 64, mp, 64, res)
        if n < 0:
            return ('import', n)
        o41 = ri_state(B161['init'] + [init], B161['qn'] + [len(q41)], {**B161['q'], **{3 + k: v for k, v in
                       enumerate(q41)}}, B161['ovr'], {**B161['maps'], **{4 + k: v for k, v in enumerate(maps41)}})
        out = ctypes.create_string_buffer(bytes([fill]) * 2332, 2332)
        rw = ctypes.create_string_buffer(bytes([fill]) * L.ri_work_size(), L.ri_work_size())
        bad = ctypes.c_int32()
        k = L.sreg_ri_import(R, sp, 2, bytes(sdiv), len(names), oo, sw, n, bytes(newpool), 3, OLD, new, 5, 102, 144,
                             o41, out, rw, ctypes.byref(bad))
        b = out.raw
        st = dict(init=list(b[0:2]), qn=list(b[8:11]), q=list(struct.unpack_from('<5H', b, 28)),
                  maps=list(struct.unpack_from('<10H', b, 1052)), ovr=(struct.unpack_from('<H', b, 412 + 2 * (16 * 1 + 3))[0],
                  struct.unpack_from('<H', b, 412 + 2 * (16 * 2 + 0))[0]), rest=b)
        return (RI.get(k, k), bad.value, st)
    errs = []

    def chk161(st, tag):                            # 161 = new file index 1, pools 1 and 2, queue at 2..4, maps at 6..9
        if (st['init'][1], st['qn'][1:3], st['q'][2:5], st['maps'][6:10], st['ovr']) != \
                (2, [2, 1], [0x0101, 0x0202, 0x8003], [7, 0, 300, 1], (0x2A1, 0x3A1)):
            errs.append(f"{tag}: 161 not moved as it is: {st['init']} {st['qn']} {st['q']} {st['maps']} {st['ovr']}")
    # an RI season end: p1 (identity 257) on slot 9, d1 out (identity 9); b0 <-> d0 across files, a3 <-> b1 in 102
    m1 = [0] * 13
    m1[9] = 257 + 1
    s1 = list(slot0)
    s1[4], s1[8], s1[3], s1[5] = 5, 1, 1, 0
    g = run(m1, s1, [256, 258, 9])
    if g[0] != 'ok' or g[2]['init'][0] != 2 or g[2]['maps'][:6] != [0, 257, 0, 0, 0, 0] or g[2]['qn'][0] != 2 or \
            g[2]['q'][:2] != [257, 1]:
        errs.append(f"season: {g[:2]} maps {g[2]['maps'][:6] if len(g) > 2 else ''} q {g[2]['q'][:2] if len(g) > 2 else ''}")
    else:
        chk161(g[2], 'season')
        g2 = run(m1, s1, [256, 258, 9], fill=0x33)
        if g2[2]['rest'] != g[2]['rest']:
            errs.append('season: not deterministic')
    # b3 (Serie C at the spec) relegated twice: slot 7 holds p2 (identity 258), slot 7's division 5; d0 up to 1
    m2 = [0] * 13
    m2[7] = 258 + 1
    s2 = list(slot0)
    s2[7], s2[8] = 5, 1
    g = run(m2, s2, [256, 257, 7])
    if g[0] != 'ok' or g[2]['maps'][:6] != [258, 0, 0, 0, 0, 0] or g[2]['q'][:2] != [256, 0]:
        errs.append(f"twice: {g[:2]} maps {g[2]['maps'][:6] if len(g) > 2 else ''} q {g[2]['q'][:2] if len(g) > 2 else ''}")
    # a stand-in RI-promoted into Serie C (MC 12/11: substituted, no longer refused): p1 on 4.1 slot 4 (division 1),
    # b0 off; p2 on slot 9, d1 off; queue [J, b0, d1]. sreg_import gives slot 4 to d1 (the filler): J leaves the queue
    # (PENDING on its row), b0 -> its record's S7 identity, d1 leaves (on 102 now), p1 at the tail (256 + 0)
    m3 = [0] * 13
    m3[4], m3[9] = 257 + 1, 258 + 1
    g = run(m3, list(slot0), [256, 4, 9])
    if g[0] != 'ok' or g[2]['qn'][0] != 2 or g[2]['q'][1] != 256 or g[2]['q'][0] >= 6:
        errs.append(f"stand-in in Serie C: {g[:2]} q {g[2]['q'][:2] if len(g) > 2 else ''} qn "
                    f"{g[2]['qn'][0] if len(g) > 2 else ''} (want ok, [b0's row, 256])")
    else:
        g2 = run(m3, list(slot0), [256, 4, 9], fill=0x33)
        if g2[2]['rest'] != g[2]['rest']:
            errs.append('stand-in in Serie C: not deterministic')
    # init 0: nothing swapped yet
    g = run([0] * 13, slot0, [], init=0)
    if g[0] != 'ok' or g[2]['init'][0] != 0 or any(g[2]['maps'][:6]) or g[2]['qn'][0]:
        errs.append(f"init 0: {g[:2]}")
    else:
        chk161(g[2], 'init 0')
    # refusals
    for tag, kw, want in (('unknown identity', dict(maps41=m1, slot=s1, q41=[256, 258, 99]), 'QUEUE'),
                          ('newpool J kept', dict(maps41=m1, slot=s1, q41=[256, 258, 9], newpool=(2, 0, 1)), 'POOLMAP'),
                          ('161 resized', dict(maps41=m1, slot=s1, q41=[256, 258, 9],
                                               new=lay([(5, 144, 0, 6, [2]), (5, 161, 6, 5, [2, 1])])), 'LAYOUT'),
                          ('init 0 + a pool swap', dict(maps41=m1, slot=s1, q41=[256, 258, 9], init=0), 'LAYOUT')):
        g = run(**kw)
        if g[0] != want:
            errs.append(f'{tag}: {g[:2]}')
    return not errs, '; '.join(errs) or ('RI season end: stand-in map, queue joiner out / p2 / d1; relegated twice: the '
                                         'record via the cross move; a stand-in in Serie C substituted (fillers out, it at the tail); init 0 empty; 161 '
                                         'moved byte for byte; deterministic; refused QUEUE / POOLMAP / LAYOUT')


def test_sreg_sltimport():
    """sreg_slt_import (sreg_import.c, MC 11/11 from Shaved's S7-G) built natively on test_sreg_riimport's 'twice'
    shape: 4.1 globals = file 102's 13 slots from 92 (92..104); S7's = 102 x 8 from 92, 144 = 100 x 4 + 2283 x 2 (the
    split run, as globnum.split's 144). Every club's someLeaguesTable byte goes from its 4.1 global to its S7 one:
    Serie A / B (92..98), d0 up into 102 row 7 (99), the stand-in p2 on 144 row 0 by RI (100: the row's global),
    e0 / e1 / e2 in Serie D at other ordinals (103, 2283, 2284), J (a joiner) 0 at 102, the old global nobody uses
    now (104) 0, another country's byte (50) kept. The byte is a signed delta on the club's base division, re-based
    (MC 11/11): A / B keep their base (copied, one negative delta kept), d0 (4.1 Serie D 3 -> 1), d1 / p2 (3 -> group
    5), e0..e2 (3 -> group 6) re-based, negative results stored as two's complement; refused: a 144 ordinal past its
    runs (GLOB), a division past ndiv and a re-based delta past +127 (DELTA, the club)."""
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, 's.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n'
                f'#include "{TOOLS}/sreg_import.c"\n'
                'uint32_t imp_work_size(void) { return sizeof(sreg_imp_work); }\n'
                'uint32_t imp_res_size(void) { return sizeof(sreg_imp_res); }\n')
    lib = os.path.join(d, 's.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-Wall', '-Werror', '-I', os.path.join(TOOLS, 'swce'), '-o',
                        lib, src], capture_output=True, text=True)
    if r.returncode:
        return False, 'cc: ' + r.stderr[-400:]
    L = ctypes.CDLL(lib)
    _imp_protos(L)
    names = ['a0', 'a1', 'a2', 'a3', 'b0', 'b1', 'b2', 'b3', 'd0', 'd1', 'J', 'e0', 'e1', 'e2', 'p1', 'p2']
    I = {k: i for i, k in enumerate(names)}
    sdiv = [0] * 4 + [1] * 4 + [5] * 3 + [6] * 3 + [OUT] * 2
    old = list(range(10)) + [256] + [10, 11, 12] + [257, 258]
    spec = spec_bytes([(102, [(0, 4), (1, 4)], 0), (144, [(5, 3), (6, 3)], 0)])
    slot = [0] * 4 + [1] * 4 + [5, 5] + [6] * 3
    slot[7], slot[8] = 5, 1                             # ('twice': b3's slot 7 now Serie D, holds p2; d0 up to 1)
    maps = [0] * 13
    maps[7] = 258 + 1
    R = ctypes.create_string_buffer(b'\xAA' * REGSIZE, REGSIZE)
    wk = ctypes.create_string_buffer(b'\xAA' * L.imp_work_size(), L.imp_work_size())
    res = ctypes.create_string_buffer(L.imp_res_size())
    sw, mp = (ctypes.c_uint16 * 192)(), (ctypes.c_uint16 * 128)()
    n = L.sreg_import(R, ctypes.create_string_buffer(spec, len(spec)), 2, bytes(sdiv), len(names),
                      (ctypes.c_uint16 * len(old))(*old), (ctypes.c_uint16 * 13)(*maps), 13, 3, 102, bytes(slot),
                      (ctypes.c_uint16 * 3)(256, 257, 7), 3, 144, 27, wk, sw, 64, mp, 64, res)
    if n < 0:
        return False, f'sreg_import {n}'

    def gl(files):                                  # sreg.glob_bytes' format
        return bytes([len(files)]) + b''.join(bytes([fl, len(rs)]) + b''.join(struct.pack('<HH', a, c) for a, c in rs)
                                              for fl, rs in files)
    OLD, NEW = gl([(102, [(92, 13)])]), gl([(102, [(92, 8)]), (144, [(100, 4), (2283, 2)])])
    NS = 2300
    o = bytearray(NS)
    dl = [0, 1, 0, 0, 0, -1, 0, 0, -2, 0, 1, 0, 2]      # 4.1 rows' signed deltas (row 7 = b3's slot, p2 through RI)
    for x in range(13):
        o[92 + x] = dl[x] & 0xFF
    o[2283] = o[2284] = 0x77                            # (stale bytes at the new run: overwritten / zeroed)
    o[50] = 0x55                                        # (another country's)
    ob = [0] * 4 + [1] * 4 + [3] * 3 + [3] * 3 + [3] * 2           # 4.1 base divisions (Serie D 3, stand-ins 3)
    nb = [0] * 4 + [1] * 4 + [1, 5, 5] + [6] * 3 + [3, 5]         # S7 bases: d0 up to B, d1 / J / p2 group 5, e* 6

    def run(new=NEW, ndiv=7, obase=ob, nbase=nb, old=o):
        out = ctypes.create_string_buffer(b'\xEE' * NS, NS)
        bad = ctypes.c_int32()
        k = L.sreg_slt_import(R, wk, len(names), OLD, new, bytes(obase), bytes(nbase), ndiv, bytes(old), out, NS,
                              ctypes.byref(bad))
        return k, bad.value, out.raw
    errs = []
    k, bad, b = run()
    want = bytearray(o)
    for g in range(92, 105):
        want[g] = 0
    want[2283] = want[2284] = 0
    for g, club, x in ((92, 'a0', 0), (93, 'a1', 1), (94, 'a2', 2), (95, 'a3', 3), (96, 'b0', 4), (97, 'b1', 5),
                       (98, 'b2', 6), (99, 'd0', 8), (100, 'p2', 7), (101, 'd1', 9), (103, 'e0', 10), (2283, 'e1', 11),
                       (2284, 'e2', 12)):
        want[g] = (ob[I[club]] + dl[x] - nb[I[club]]) & 0xFF
    if k != 13 or bytes(want) != b:
        dif = [(g, b[g], want[g]) for g in range(NS) if b[g] != want[g]]
        errs.append(f'moved {k}: (global, got, want) {dif[:8]}')
    if (b[97], b[99], b[100], b[101], b[103], b[2283], b[2284]) != (0xFF, 0, 0xFE, 0xFE, 0xFE, 0xFD, 0xFF):
        errs.append(f'deltas: {b[97]} {b[99]} {b[100]} {b[101]} {b[103]} {b[2283]} {b[2284]}')
    if b[102] != 0 or b[104] != 0:
        errs.append(f'J / unused global: {b[102]} {b[104]}')
    k, bad, _ = run(gl([(102, [(92, 8)]), (144, [(100, 4)])]))
    if (k, bad) != (-32, I['e1']):
        errs.append(f'144 past its runs: {k} bad {bad}')
    k, bad, _ = run(ndiv=5)                             # e2: 3 + 2 = division 5, past a 5-division league
    if (k, bad) != (-33, I['e2']):
        errs.append(f'division past ndiv: {k} bad {bad}')
    o2 = bytearray(o)
    o2[92] = 100                                        # a0: base 100 + 100 = division 200, S7 base 0 -> +200
    k, bad, _ = run(ndiv=256, obase=[100] + ob[1:], old=o2)
    if (k, bad) != (-33, I['a0']):
        errs.append(f'delta past +127: {k} bad {bad}')
    return not errs, '; '.join(errs) or ('13 clubs moved: A / B kept (b1 -1 as is), d0 into 102 row 7 (re-based 0), '
                                         'p2 on its RI row\'s global (-2), d1 / e0..e2 re-based (-2 -2 -3 -1) at their '
                                         'new globals (2 in 144\'s second run), J and the old unused global 0, another '
                                         'country\'s kept; refused: past the runs (GLOB, e1), division past ndiv and '
                                         'delta past +127 (DELTA, e2 / a0)')
