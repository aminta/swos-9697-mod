"""N7 piece 3 (MC 10/11): the club registry's SWC1 section 'IT' (swe.c it_save / it_load, sreg.c at obj4+SREG_AT,
SREG_DIV at obj4+SREG_DIV_AT), on the static image of HT_N7_EXE (else c/HTn7: the release recipe with SREG_FORCE=1 and
HOSTTEST_SYMS=1, an empty shape) with the italy42 shape poked into SREG_NF / SREG_NCLUB / SREG_SPEC / SREG_DIV (A = 102
Serie A, B, C + 2 x 20, B = 144 Serie D 9 x 18 + 36 pool rows, 10 off-file clubs: the engine's tests/rules/reg_save.c
shape, 298 rows), and of HT_N7D_EXE (else c/HTn7d: the same recipe, dormant). The obj4 .bss (SWC1 and the arena) is
garbage at the start (0AAh), as DOS/4GW may leave it. A registry is compared by its state (view(): what sr_reg_build
writes; the struct's unused tail keeps the arena's bytes).

- a new career (en_finish with nothing found, then swe_st_load): SWC1's head the dormant build's, byte for byte, and
  no section; the first save writes 'IT' (389 B with its header) from the spec;
- save -> load: a registry other than the spec's (two clubs' divisions swapped) comes back (its state), SREG_LAST 1;
  the load overwrites a garbage SWC1 before any read (its bytes the block's);
- another layout (a pool row fewer): 0, the registry the new spec's; the next save writes 'IT' again at its new
  size, cut from its place, a section after it kept;
- a corrupt section (every ident 0) and a short one: -1, the registry rebuilt - the same bytes from two garbage
  arenas;
- the dormant build: SREG_FN 0, a new career's save writes no section."""
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
EXE = os.environ.get('HT_N7_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTn7', 'SWOS', 'ITALIAN.EXE')
DORM = os.environ.get('HT_N7D_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTn7d', 'SWOS', 'ITALIAN.EXE')
IT, HDR = 0x5449, 20
_H = open(os.path.join(TOOLS, 'swce', 'swosrules.h')).read()
FILES, CLUBS, DIVS = (int(re.search(rf'#define {k}\s+(\d+)', _H).group(1)) for k in ('SR_REG_FILES', 'SR_REG_CLUBS',
                                                                                     'SR_DIVS'))
POOL, OUT = 0xFE, 0xFF
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


ITALY = [(102, [(k, 20) for k in range(5)], 0), (144, [(5 + g, 18) for g in range(9)], 36)]
ITALY_DIV = [k // 20 for k in range(100)] + [5 + g for g in range(9) for _ in range(18)] + [POOL] * 36 + [OUT] * 10


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
        self.uc.mem_map(ts.BUF, 0x10000)

    def w(self, a, b):
        self.uc.mem_write(a, b)

    def call(self, m, k, *args):
        return tr._call(self.uc, self.at(m, k), *args)

    def new_career(self):                                       # (new_career_defaults: en_reset, en_finish; after_new)
        self.w(self.found, b'\0' * (self.en_n + 1))
        ts._run(self.uc, self.at('trailer', 'en_finish'), tr.RET)
        self.call('swe', 'swe_st_load')

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
    fn = struct.unpack('<5I', d.rd(d.at('swe', 'SREG_FN'), 20))
    if any(fn) or 'sreg' in d.sy:
        errs.append(f'dormant: SREG_FN {fn}, sreg linked {"sreg" in d.sy}')
    reg = struct.unpack('<I', m.rd(m.at('sreg', 'SREG_REG'), 4))[0]
    if reg != m.at('swe', 'SWE_ARENA_AT'):
        errs.append(f'SREG_REG {reg:#x}, the arena {m.at("swe", "SWE_ARENA_AT"):#x}')

    def shape(files, div):
        m.w(m.at('sreg', 'SREG_NF'), struct.pack('<ii', len(files), len(div)))
        m.w(m.at('sreg', 'SREG_SPEC'), spec_bytes(files))
        m.w(m.at('sreg', 'SREG_DIV'), bytes(div).ljust(CLUBS, b'\0'))
    regb = lambda: view(m.rd(reg, REGSIZE))
    last = lambda: struct.unpack('<i', m.rd(m.at('sreg', 'SREG_LAST'), 4))[0]

    def fresh():                                            # (the spec's registry, as sreg_build makes it)
        if m.call('sreg', 'sreg_build'):
            errs.append('sreg_build refused the shape')
        return regb()
    shape(ITALY, ITALY_DIV)
    R0 = fresh()
    m.call('sreg', 'sreg_new')
    m.w(reg, b'\xAA' * REGSIZE)
    size = 32 + 4 + m.call('sreg', 'sreg_size')                 # (SWC1: 32 + the section, sreg_size 12 + 373)
    if size != 32 + 389:
        errs.append(f'SWC1 {size} B, want 32 + 389 (the italy42 shape)')

    # a new career: SWC1 (garbage .bss) zeroed and started, as the dormant build's; the first save writes 'IT'
    m.w(m.swc1, b'\xAA' * size)
    m.new_career()
    d.new_career()
    head, dhead = m.rd(m.swc1, size), d.rd(d.swc1, 32)
    if head[:32] != dhead or any(head[32:]) or sections(dhead):
        errs.append(f'new career: SWC1 head {head[:HDR].hex()} vs the dormant {dhead[:HDR].hex()}, '
                    f'{sum(map(bool, head[HDR:]))} non-zero byte(s) after it, dormant sections {sections(dhead)}')
    if regb() != R0:
        errs.append('new career: the registry not the spec\'s')
    m.call('swe', 'swe_st_save')
    d.call('swe', 'swe_st_save')
    s = sections(m.rd(m.swc1, size))
    if [(k, len(b)) for k, b in s] != [(IT, 385)]:
        errs.append(f'new career, first save: sections {[(hex(k), len(b)) for k, b in s]} (want IT 385)')
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

    # another layout (a pool row fewer): 0, the new spec's registry; the next save cuts 'IT', keeps 'ZZ' after it
    ITALY35 = [ITALY[0], (144, ITALY[1][1], 35)]
    D35 = ITALY_DIV[:262 + 35] + [OUT] * 10
    shape(ITALY35, D35)
    R35 = fresh()
    m.call('sreg', 'sreg_new')
    zz = struct.pack('<HH', 0x5A5A, 4) + b'zzzz'
    S2z = S2[:HDR + 4 + 385] + zz + S2[HDR + 4 + 385 + len(zz):]
    m.load(S2z)
    if last() != 0 or regb() != R35:
        errs.append(f'another layout: SREG_LAST {last()}, registry {"=" if regb() == R35 else "!="} the new spec\'s')
    m.call('swe', 'swe_st_save')
    s = sections(m.rd(m.swc1, size))
    if [(k, len(b)) for k, b in s] != [(0x5A5A, 4), (IT, 384)] or s[0][1] != b'zzzz':
        errs.append(f'another layout, save: sections {[(hex(k), len(b)) for k, b in s]} (want ZZ 4 kept, IT 384)')

    # corrupt (every ident 0) and short: -1, rebuilt - the same bytes from two garbage arenas
    shape(ITALY, ITALY_DIV)
    bad = S2[:HDR + 4 + 12] + bytes(373) + S2[HDR + 4 + 385:]
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
    return not errs, '; '.join(errs) or ('new career = the dormant head + IT 385 at the first save; save -> load of a '
                                         'non-spec registry 1, its state back; another layout 0 + IT cut (ZZ kept); '
                                         'corrupt / short -1, the same rebuild twice; dormant: no sreg, no section')
