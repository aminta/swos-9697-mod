"""4.2 S7 season-end swap builder (s7swap.c at obj4+swreg.S7SWAP_AT; internal/handoff/s7-swap-plan.md piece 2), on the
static image of HT_S7_EXE (else c/S7W-h1: a shaped IT build - the S7 test pack - with HOSTTEST_SYMS=1). The registry
comes from the build's spec (sreg_get); gplay.c's snapshots S7X are poked (a test switch in memory, no season played):
S7X[0] = file 102's 9 clubs down (each Serie C group's last place direct, then 2 play-out losers per group), S7X[1] =
file 144's 9 up (each Serie D group's first). SLTCOPY = a buffer: no in-struct move (all 0), then one in-struct move.

- s7_season: status OK, 9 swaps, 18 crossers; every down club now in file 144 on a Serie D group, every up club in
  file 102 on a Serie C group; each division keeps its size (rows per rdiv = the spec's); each crosser's group = a
  Python oracle of s7swap.c's rule (its area, else the nearest group with a free place; S7X order); every row's
  delta in SLTCOPY = its new local division - the row's shipped one (record +25); deterministic (twice from the
  same start = the same registry and SLTCOPY);
- an in-struct move (a Serie B club relegated: delta +1 on its global) keeps its row, its rdiv follows;
- refused, nothing changed (registry, SLTCOPY): counts unequal (COUNT), a bad snapshot (BAD), last season's stamp on
  one side (STALE), a crosser not on its boundary level (PLACE).

test_s7load (piece 3, s7_load: ri_load's call after LoadTeamFile read TEAM.102 / .144), on the same build with its
DATA\\TMW5.102 / .144: S7_HRUN = the spec registry's first words; S7_FNV = the files' FNV-1a; after the 9 swaps every
row of both files holds its registry club's home record (S7_ORIG, filled as orig_read would) and keeps its own bytes
0..4, 23 and 25 (one check per kept byte, MC 13/11: each poked in the row before the call and found again after);
rows of clubs that did not move stay as read; moved = 9 per file; a file that differs from its ORIG's FNV (ORIG read again - its open fails here: LD_READ), ORIG not read (oread 2: LD_READ, retried at the next load), a wrong count: nothing applied; another file: no call
counted; no registry (no world byte): LD_NOREG."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402
import test_sreg as tg  # noqa: E402
import test_swc1 as ts  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_S7_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-p3', 'SWOS', 'ITALIAN.EXE')
OK, STALE, BAD, COUNT, PLACE = 1, 3, 4, 5, 6
FA, FB = 102, 144
SEASON = 7
SLT_AT = ts.BUF + 0x8000                                # (SLTCOPY stand-in: 2400 bytes in the test buffer)


class M(tg.N7):
    def __init__(self, exe):
        super().__init__(exe)
        self.reg = struct.unpack('<I', self.rd(self.at('sreg', 'SREG_REG'), 4))[0]
        self.s7x = self.at('gplay', 'S7X')
        self.log = self.at('s7swap', 'S7_LOG')
        self.area = self.rd(self.at('s7swap', 'S7_AREA'), 320)
        self.up = self.rd(self.at('s7swap', 'S7_UP'), self.rd(self.at('s7swap', 'S7_NUP'), 1)[0])
        self.lo = self.rd(self.at('s7swap', 'S7_LO'), self.rd(self.at('s7swap', 'S7_NLO'), 1)[0])
        self.gb = [struct.unpack_from('<3H', self.rd(self.at('s7swap', 'S7_GB'), 12), 6 * k) for k in range(2)]

    def fresh(self):
        self.call('swe', 'swe_init')
        self.world(tg.WORLD)
        self.new_career()                               # (swe_st_load: SWC1's world byte, sreg_new)
        assert self.call('sreg', 'sreg_get') == 1, 'sreg_get: no registry (world byte)'

    def regb(self):
        return self.rd(self.reg, tg.REGSIZE)

    def state(self):
        return tg.view(self.regb())

    def snap(self, k, file, ents, season=SEASON, bad=0):
        b = struct.pack('<HBBB3x', file, len(ents), bad, season)
        for glob, team, kind, dr, dv, rank in ents:
            b += struct.pack('<HHBBBB', glob, team, kind, dr, dv, rank)
        self.w(self.s7x + 200 * k, b.ljust(200, b'\0'))


def reg_parse(b):
    """(files [(file, divs, sizes)], word[ident], at[fi][o], rdiv[fi][o], rows[fi])"""
    nf, nc = struct.unpack_from('<ii', b, 0)
    fs = []
    for i in range(nf):
        o = 8 + i * tg.FSIZE
        nd = b[o + 1]
        fs.append((b[o], list(b[o + 2:o + 2 + nd]), list(b[o + 2 + tg.DIVS:o + 2 + tg.DIVS + nd])))
    w = 8 + tg.FILES * tg.FSIZE
    word = list(struct.unpack_from(f'<{nc}H', b, w))
    at_ = w + 2 * tg.CLUBS
    at = [list(struct.unpack_from('<256H', b, at_ + 512 * i)) for i in range(nf)]
    rd_ = at_ + tg.FILES * 512
    rdiv = [list(b[rd_ + 256 * i:rd_ + 256 * i + 256]) for i in range(nf)]
    rows = list(struct.unpack_from(f'<{nf}H', b, rd_ + tg.FILES * 256))
    return fs, word, at, rdiv, rows


def base_local(f, o):
    r = 0
    for k, n in enumerate(f[2]):
        r += n
        if o < r:
            return k
    return -1


def glob_of(gb, o):
    return gb[2] + o - gb[1] if gb[1] and o >= gb[1] else gb[0] + o


def crossings(fs, gb):
    """S7X entries: 102's Serie C groups (its divisions 2..4): row last direct, then rows -3 / -4 play-out losers;
    144's groups: row 0 (the winner)"""
    a, b = fs
    down, up = [], []
    for loc in (2, 3, 4):
        last = sum(a[2][:loc + 1]) - 1
        down.append((glob_of(gb[0], last), FA | last << 8, 0, 1, loc, 19))
    for loc in (2, 3, 4):
        last = sum(a[2][:loc + 1]) - 1
        for o in (last - 3, last - 4):
            down.append((glob_of(gb[0], o), FA | o << 8, 1, 1, 0xFF, 0))
    for loc in range(len(b[1])):
        o = sum(b[2][:loc])
        up.append((glob_of(gb[1], o), FB | o << 8, 0, 0, loc, 0))
    return down, up


def oracle(m, fs, word, down, up):
    """{ident: destination division} by s7swap.c's rule"""
    ident = {w: i for i, w in enumerate(word)}
    fup = [0] * len(m.up)
    flo = [0] * len(m.lo)
    for e in down:
        o = e[1] >> 8
        fup[[2, 3, 4].index(next(k for k in range(len(fs[0][1])) if o < sum(fs[0][2][:k + 1])))] += 1
    for e in up:
        o = e[1] >> 8
        flo[next(k for k in range(len(fs[1][1])) if o < sum(fs[1][2][:k + 1]))] += 1

    def place(free, a):
        n = len(free)
        if a < n and free[a]:
            return a
        for d in range(1, n):
            if 0 <= a - d < n and free[a - d]:
                return a - d
            if a + d < n and free[a + d]:
                return a + d
        if a >= n:
            return next((g for g in range(n) if free[g]), -1)
        return -1
    out = {}
    for e in down:
        i = ident[e[1]]
        g = place(flo, m.area[i] >> 4)
        flo[g] -= 1
        out[i] = m.lo[g]
    for e in up:
        i = ident[e[1]]
        g = place(fup, m.area[i] & 0xF)
        fup[g] -= 1
        out[i] = m.up[g]
    return out


def run(m, down, up, slt=None, sa=SEASON, sb=SEASON, bad=(0, 0)):
    m.snap(0, FA, down, sa, bad[0])
    m.snap(1, FB, up, sb, bad[1])
    m.w(SLT_AT, slt or bytes(2400))
    m.call('s7swap', 's7_season', SLT_AT)
    st, season, nsw, ncr = m.rd(m.log, 4)
    return st, nsw, ncr, m.rd(SLT_AT, 2400)


def test_s7swap():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    if 's7swap' not in json.load(open(EXE[:-4] + '.syms.json')):
        return False, f'{EXE}: no s7swap (not a shaped build)'
    m = M(EXE)
    errs = []
    m.fresh()
    r0 = m.regb()
    fs, word, at, rdiv, rows = reg_parse(r0)
    sizes0 = {d: n for f in fs for d, n in zip(f[1], f[2])}
    down, up = crossings(fs, m.gb)
    want = oracle(m, fs, word, down, up)
    st, nsw, ncr, slt = run(m, down, up)
    if (st, nsw, ncr) != (OK, 9, 18):
        return False, f'status {st} swaps {nsw} crossers {ncr} (want {OK}, 9, 18); log {m.rd(m.log, 8).hex()}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    for i, d in want.items():
        f = word1[i] & 0xFF
        fi = [x[0] for x in fs1].index(f)
        got = rdiv1[fi][word1[i] >> 8]
        if got != d or (d in m.lo) != (f == FB):
            errs.append(f'ident {i}: file {f} division {got}, want {d}')
    cnt = {}
    for fi, f in enumerate(fs1):
        for o in range(rows1[fi]):
            cnt[rdiv1[fi][o]] = cnt.get(rdiv1[fi][o], 0) + 1
            b = base_local(f, o)
            if b >= 0:
                g = glob_of(m.gb[fi], o)
                loc = f[1].index(rdiv1[fi][o])
                if struct.unpack('b', slt[g:g + 1])[0] != loc - b:
                    errs.append(f'file {f[0]} row {o}: delta {struct.unpack("b", slt[g:g + 1])[0]} != {loc - b}')
    if {d: cnt.get(d) for d in sizes0} != sizes0:
        errs.append(f'division sizes {cnt} != {sizes0}')
    reg1 = m.regb()
    m.fresh()                                           # (determinism: the same start, the same result)
    st2, _, _, slt2 = run(m, down, up)
    if st2 != OK or m.regb() != reg1 or slt2 != slt:
        errs.append('not deterministic')
    m.fresh()                                           # an in-struct move: Serie B's row 20 relegated (+1)
    s = bytearray(2400)
    g = glob_of(m.gb[0], 20)
    s[g] = 1
    st3, _, _, slt3 = run(m, down, up, bytes(s))
    fs3, word3, at3, rdiv3, _ = reg_parse(m.regb())
    if st3 != OK or rdiv3[0][20] != 2 or at3[0][20] != at[0][20] or slt3[g] != 1:
        errs.append(f'in-struct move: status {st3} rdiv {rdiv3[0][20]} row ident {at3[0][20]}/{at[0][20]} delta {slt3[g]}')
    for name, kw, code in (('COUNT', dict(down=down[:-1]), COUNT), ('BAD', dict(bad=(0, 2)), BAD),
                           ('STALE', dict(sb=SEASON - 1), STALE),
                           ('PLACE', dict(up=up[:-1] + [(glob_of(m.gb[0], 0), FA, 0, 0, 0, 0)]), PLACE)):
        m.fresh()
        a = dict(down=down, up=up)
        a.update({k: v for k, v in kw.items() if k in ('down', 'up')})
        stx, nx, _, sltx = run(m, a['down'], a['up'], sa=SEASON, sb=kw.get('sb', SEASON), bad=kw.get('bad', (0, 0)))
        if stx != code or m.regb() != r0 or any(sltx):
            errs.append(f'{name}: status {stx} (want {code}), registry {"changed" if m.regb() != r0 else "kept"}, '
                        f'SLTCOPY {"touched" if any(sltx) else "kept"}')
    dn = sorted(want[i] for i in want if want[i] in m.lo)
    return not errs, '; '.join(errs[:6]) or (f'9 down + 9 up as 9 registry swaps; down into groups {dn}, sizes kept, '
                                             f'SLTCOPY re-based, deterministic; in-struct move kept its row; refused '
                                             f'COUNT / BAD / STALE / PLACE with nothing changed')


TB = 0x6200000                                          # (the team buffer: 2 + 162 x 684 B)
LD_OK, LD_NOREG, LD_READ, LD_SIZE, LD_FILE = 1, 2, 3, 4, 5
KEPT = (0, 1, 2, 3, 4, 23, 25)


def ld(m):
    st, oread, f, _, moved, rows, calls, rc = struct.unpack('<BBBBHHIi', m.rd(m.at('s7swap', 'S7_LD'), 16))
    return st, oread, moved, calls


def test_s7load():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 's7_load' not in sy.get('s7swap', {}):
        return False, f'{EXE}: no s7_load (piece 3 not linked)'
    data = os.path.join(os.path.dirname(EXE), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (FA, FB)}
    m = M(EXE)
    m.uc.mem_map(TB, 0x20000)
    errs = []
    oat = struct.unpack('<II', m.rd(m.at('s7swap', 'S7_OAT'), 8))
    onrec = struct.unpack('<HH', m.rd(m.at('s7swap', 'S7_ONREC'), 4))
    hrun = [struct.unpack_from('<HHBB2x', m.rd(m.at('s7swap', 'S7_HRUN'), 64), 8 * k) for k in range(8)]
    import s7swap
    for s, f in enumerate((FA, FB)):
        if (len(fil[f]) - 2) // 684 != onrec[s]:
            return False, f'TMW5.{f}: {len(fil[f])} B vs the exe\'s {onrec[s]} records'
    m.fresh()
    fs, word, at, rdiv, rows = reg_parse(m.regb())

    def home(i):
        for a, n, f, o in hrun:
            if n and a <= i < a + n:
                return f | (o + i - a) << 8
        return 0xFFFF
    if [home(i) for i in range(len(word))] != word:
        errs.append('S7_HRUN != the spec registry\'s words')
    orig = m.at('swe', 'S7_ORIG')

    def fill_orig():
        for s, f in enumerate((FA, FB)):
            m.w(orig + oat[s], fil[f])
        b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))
        b[1] = 1
        m.w(m.at('s7swap', 'S7_LD'), bytes(b))
        m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *(s7swap.fnv(fil[f]) for f in (FA, FB))))
    m.w(m.at('swefile', 'swe_fopen_r'), b'\xb8\xfe\xff\xff\xff\xc3')   # (Unicorn: no DOS - every open fails, -2)
    down, up = crossings(fs, m.gb)
    st, nsw, _, _ = run(m, down, up)
    if st != OK:
        return False, f'season status {st}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    fill_orig()
    rec = lambda f, o: fil[f][2 + 684 * o:2 + 684 * (o + 1)]
    for fi, f in enumerate((FA, FB)):
        buf = bytearray(fil[f])
        for k, b in enumerate(KEPT):                    # (a per-byte mark in every row: found again after the call)
            for o in range(onrec[fi]):
                buf[2 + 684 * o + b] = (0x40 + k * 7 + o) & 0xFF
        marked = bytes(buf)
        # the marks change the FNV: the file check would refuse -> the call sees the file as read, marks after
        m.w(TB, fil[f])
        m.call('s7swap', 's7_load', TB, f)
        st, oread, moved, calls = ld(m)
        if (st, oread) != (LD_OK, 1) or moved != 9:
            errs.append(f'{f}: status {st} oread {oread} moved {moved} (want {LD_OK}, 1, 9)')
        got = m.rd(TB, len(fil[f]))
        # the kept bytes: rerun on a buffer whose row bytes differ from the file - by patching the FNV check's input:
        # poke the marked buffer, recompute S7_FNV for it (the exe's own data: a test switch in memory)
        fsave = m.rd(m.at('s7swap', 'S7_FNV'), 8)
        fn = list(struct.unpack('<II', fsave))
        fn[fi] = s7swap.fnv(marked)
        m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *fn))
        m.w(TB, marked)
        m.call('s7swap', 's7_load', TB, f)
        st2 = ld(m)[0]
        got2 = m.rd(TB, len(fil[f]))
        m.w(m.at('s7swap', 'S7_FNV'), fsave)
        if st2 != LD_OK:
            errs.append(f'{f} marked: status {st2}')
        for o in range(rows1[fi]):
            i = at1[fi][o]
            h = word[i]
            want = bytearray(rec(h & 0xFF, h >> 8))
            for b in KEPT:
                want[b] = fil[f][2 + 684 * o + b]
            r = got[2 + 684 * o:2 + 684 * (o + 1)]
            if r != bytes(want):
                errs.append(f'{f} row {o} (ident {i}, home {h & 0xFF}/{h >> 8}): record differs at '
                            f'{[b for b in range(684) if r[b] != want[b]][:6]}')
            r2 = got2[2 + 684 * o:2 + 684 * (o + 1)]
            for k, b in enumerate(KEPT):
                if r2[b] != marked[2 + 684 * o + b]:
                    errs.append(f'{f} row {o}: kept byte {b} not kept ({r2[b]:#x} != {marked[2 + 684 * o + b]:#x})')
            if h == (f | o << 8) and r != rec(f, o):
                errs.append(f'{f} row {o}: unmoved club changed')
    # refusals: nothing applied
    for name, prep, want in (('changed file (ORIG read again: fails here)', lambda b: b.__setitem__(700, b[700] ^ 1), LD_READ),
                             ('LD_SIZE', lambda b: b.__setitem__(1, b[1] - 1), LD_SIZE)):
        fill_orig()
        b = bytearray(fil[FB])
        prep(b)
        m.w(TB, bytes(b))
        m.call('s7swap', 's7_load', TB, FB)
        if ld(m)[0] != want or m.rd(TB, len(b)) != bytes(b):
            errs.append(f'{name}: status {ld(m)[0]} (want {want}), buffer {"kept" if m.rd(TB, len(b)) == bytes(b) else "changed"}')
    b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))   # ORIG not readable: oread 2 -> LD_READ, retried next load
    b[1] = 2
    m.w(m.at('s7swap', 'S7_LD'), bytes(b))
    m.w(TB, fil[FB])
    c0 = ld(m)[3]
    m.call('s7swap', 's7_load', TB, FB)                 # (Unicorn: no DOS - the retry's read fails again)
    if ld(m)[0] != LD_READ or m.rd(TB, len(fil[FB])) != fil[FB] or ld(m)[3] != c0 + 1:
        errs.append(f'LD_READ: status {ld(m)[0]}, buffer {"kept" if m.rd(TB, len(fil[FB])) == fil[FB] else "changed"}')
    c1 = ld(m)[3]
    m.call('s7swap', 's7_load', TB, 103)
    if ld(m)[3] != c1:
        errs.append('file 103 counted')
    m.world(0)                                          # (a new career in another world: no registry)
    m.new_career()
    m.call('s7swap', 's7_load', TB, FB)
    if ld(m)[0] != LD_NOREG:
        errs.append(f'no world: status {ld(m)[0]} (want {LD_NOREG})')
    return not errs, '; '.join(errs[:6]) or (f'9 + 9 rows given their registry club\'s home record, bytes {KEPT} kept '
                                             f'(one mark each), unmoved rows as read; refused a changed file (re-read) / '
                                             f'a wrong count / LD_READ / LD_NOREG with the buffer kept; other files ignored')
