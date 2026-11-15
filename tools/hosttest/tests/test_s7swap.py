"""4.2 S7 season-end swap builder (s7swap.c at obj4+swreg.S7SWAP_AT; internal/handoff/s7-swap-plan.md piece 2), on the
static image of HT_S7_EXE (else c/S7W-ws4c (the Integratore rebuilds it at the merged tip): a shaped IT build - the S7 test pack - with HOSTTEST_SYMS=1). The registry
comes from the build's spec (sreg_get); gplay.c's snapshots S7X are poked (a test switch in memory, no season played):
S7X[0] = file 102's 9 clubs down (each Serie C group's last place direct, then 2 play-out losers per group), S7X[1] =
file 144's 9 up (each Serie D group's first). SLTCOPY = a buffer: no in-struct move (all 0), then one in-struct move.

- s7_season: status OK, 9 swaps, 18 crossers; the XTRA caches keyed by word (xcache, xlbt) flushed; every down club now in file 144 on a Serie D group, every up club in
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
EXE = os.environ.get('HT_S7_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-ws4c', 'SWOS', 'ITALIAN.EXE')
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
    if 'S7RD_PTR' in m.sy['s7swap']:                    # (4.2 redraw builds: this test is the crossers' place() rule - the redraw's
        m.w(m.at('s7swap', 'S7RD_PTR'), bytes(4))       #  fallback / S7_REDRAW_OFF; test_s7redraw_exe tests the redraw itself)
    m.fresh()
    r0 = m.regb()
    fs, word, at, rdiv, rows = reg_parse(r0)
    sizes0 = {d: n for f in fs for d, n in zip(f[1], f[2])}
    down, up = crossings(fs, m.gb)
    want = oracle(m, fs, word, down, up)
    import xtra
    xc = m.at('xtra', 'xcache') if 'xcache' in m.sy.get('xtra', {}) else None     # (obj1)
    xl = tr.B3 + m.sy['xleft']['xlbt'][1] if 'xlbt' in m.sy.get('xleft', {}) else None   # (obj3: its LABELS are bare)
    for k in range(xtra.NC if xc else 0):               # (MC 13/11: the XTRA caches keyed by the current word)
        m.w(xc + k * xtra.ENT, struct.pack('<HBB', 0x1266, 5, 1))
    if xl:
        m.w(xl, struct.pack('<H', 0x1266))
    st, nsw, ncr, slt = run(m, down, up)
    if (st, nsw, ncr) != (OK, 9, 18):
        return False, f'status {st} swaps {nsw} crossers {ncr} (want {OK}, 9, 18); log {m.rd(m.log, 8).hex()}'
    if xc is None or xl is None:
        errs.append('no xtra xcache / xleft xlbt symbols (a shaped build has XTRA)')
    else:
        xt = m.at('xtra', 'xteam')

        def warm():
            for k in range(xtra.NC):
                m.w(xc + k * xtra.ENT, struct.pack('<HBB', 0x1266, 5, 1))
            m.w(xl, struct.pack('<H', 0x1266))
            m.w(xt, struct.pack('<H', 0x1266))

        def cold(what):
            v = [m.rd(xc + k * xtra.ENT + 3, 1)[0] for k in range(xtra.NC)]
            if any(v) or m.rd(xl, 2) != b'\xff\xff' or m.rd(xt, 2) != b'\xff\xff':
                errs.append(f'{what}: xcache valid bytes {v}, xlbt {m.rd(xl, 2).hex()}, xteam {m.rd(xt, 2).hex()} '
                            f'(want all 0 / ffff / ffff)')
        if any(m.rd(xc + k * xtra.ENT + 3, 1)[0] for k in range(xtra.NC)) or m.rd(xl, 2) != b'\xff\xff':
            errs.append('after the swaps: the XTRA caches not flushed')
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
    if xc is not None and xl is not None:
        for fn in ('sreg_new', 'sreg_build'):          # (a load / new career: SREG_CHG -> s7_flush, MC 13/11)
            warm()
            m.call('sreg', fn)
            cold(f'after {fn}')
        warm()
        m.call('sreg', 'sreg_load', ts.BUF, 0)          # (a load with no / a bad 'IT': cold all the same)
        cold('after sreg_load')
    return not errs, '; '.join(errs[:6]) or (f'9 down + 9 up as 9 registry swaps; down into groups {dn}, sizes kept, '
                                             f'SLTCOPY re-based, deterministic; in-struct move kept its row; refused '
                                             f'COUNT / BAD / STALE / PLACE with nothing changed; the XTRA word caches cold after the swaps, '
                                             f'sreg_new / sreg_build / sreg_load')


def test_s7stadium():
    """42-s7stad (MC 13/11): stadium.py's st_find keys the versus screen's stadium by the HOME word. After the 9 swaps
    every club of both files is looked up by its current team word (gameTeam1 -> a record in the test buffer):
    ST_CUR = (current word, word keyed) - a crosser is keyed by its shipped home word, a club that did not move by
    itself. st_find runs up to its first DOS call (the file open: an interrupt here, caught); before any swap every
    club keys itself."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'ST_CUR' not in sy.get('s7swap', {}):
        return True, f'SKIP: {EXE}: no stadium hook (a build without stadium.py / the S7 stub)'
    from unicorn import UcError
    m = M(EXE)
    base = {1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}
    s7 = sy['s7swap']
    where = lambda k: base[s7[k][0] or 1] + s7[k][1]
    rec = ts.BUF + 0xA000
    errs = []

    def look(w):
        m.w(rec, struct.pack('<H', w) + bytes(682))
        m.w(where('ST_GT1'), struct.pack('<I', rec))
        m.w(where('ST_CUR'), bytes(4))
        try:
            ts._run(m.uc, where('ST_FIND'), tr.RET)
        except UcError:
            pass                                        # (int 21h: the file open - the key is set by then)
        return struct.unpack('<HH', m.rd(where('ST_CUR'), 4))
    m.fresh()
    fs, word, at, rdiv, rows = reg_parse(m.regb())
    before = [look(w) for w in word[:40]]
    bad0 = [(hex(c), hex(h)) for c, h in before if c != h]
    if bad0 or any(c == 0 for c, _ in before):
        errs.append(f'before any swap: keys {bad0[:3]} (want each club keyed by itself)')
    down, up = crossings(fs, m.gb)
    st, nsw, ncr, _ = run(m, down, up)
    if (st, nsw, ncr) != (OK, 9, 18):
        return False, f'status {st} swaps {nsw} crossers {ncr}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    moved = other = 0
    for fi, f in enumerate(fs1):
        for o in range(rows1[fi]):
            i = at1[fi][o]
            if i >= len(word):
                continue
            cur = f[0] | o << 8
            c, h = look(cur)
            if c != cur or h != word[i]:
                errs.append(f'row {hex(cur)} (ident {i}): current {hex(c)} keyed {hex(h)}, want home {hex(word[i])}')
            moved += cur != word[i]
            other += cur == word[i]
    hp = where('st_hptr') if 'st_hptr' in s7 else None
    sv = m.rd(sy['stadium']['st_hptr'][1] + tr.B3, 4) if 'stadium' in sy and 'st_hptr' in sy['stadium'] else None
    cross = [f[0] | o << 8 for fi, f in enumerate(fs1) for o in range(rows1[fi]) if at1[fi][o] < len(word)
             and (f[0] | o << 8) != word[at1[fi][o]]]
    if sv is not None and cross:                        # (control: no hook = the current word keyed: the check bites)
        m.w(sy['stadium']['st_hptr'][1] + tr.B3, bytes(4))
        c0, h0 = look(cross[0])
        m.w(sy['stadium']['st_hptr'][1] + tr.B3, sv)
        if h0 != cross[0]:
            errs.append(f'control (st_hptr 0): a crosser keyed {hex(h0)}, want its current word {hex(cross[0])}')
    if moved != 18:
        errs.append(f'{moved} rows whose home word differs from their place, want 18')
    return not errs, '; '.join(errs[:5]) or (f'before the swaps every club keys itself; after them {moved} crossers keyed by '
                                              f'their home word, {other} others by themselves')


def test_s7wndisk():
    """42-s7wn (MC 13/11): winners.py's wn_disk reads a club's name from DATA\\TEAM.nnn - the disk rows are the HOME layout -
    so a crossed club's current word must be mapped to its home word first (ri_wnhome, the patched exe's real wn_disk
    entry: call ri_wnhome -> s7_home_word -> the original body). Run under Unicorn up to its first DOS call (the file
    open): WN_FN names TEAM.<home file> and ESI (the word the body goes on with) = the home word. After the 9 swaps the
    18 crossers map to their shipped home word, the 244 other rows to themselves; before any swap every club does."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'WN_DISK' not in sy.get('s7swap', {}):
        return True, f'SKIP: {EXE}: no wn_disk hook (a build without the WINNERS page / S7_WNOFF)'
    from unicorn import UcError
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESI
    m = M(EXE)
    base = {1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}
    s7 = sy['s7swap']
    where = lambda k: base[s7[k][0] or 1] + s7[k][1]
    errs = []

    def look(w):
        m.w(where('WN_FN'), b'data/team.000\0')
        try:
            ts._run(m.uc, where('WN_DISK'), tr.RET, {UC_X86_REG_EAX: 0xABCD0000 | w})
        except UcError:
            pass                                        # (int 21h: the file open)
        fn = bytes(m.rd(where('WN_FN'), 13))
        return int(fn[10:13]), m.uc.reg_read(UC_X86_REG_ESI) & 0xFFFF
    m.fresh()
    fs, word, at, rdiv, rows = reg_parse(m.regb())
    bad0 = [(hex(w), look(w)) for w in word[:40] if look(w) != (w & 0xFF, w)]
    if bad0:
        errs.append(f'before any swap: {bad0[:3]} (want each club by itself)')
    down, up = crossings(fs, m.gb)
    st, nsw, ncr, _ = run(m, down, up)
    if (st, nsw, ncr) != (OK, 9, 18):
        return False, f'status {st} swaps {nsw} crossers {ncr}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    moved = other = 0
    for fi, f in enumerate(fs1):
        for o in range(rows1[fi]):
            i = at1[fi][o]
            if i >= len(word):
                continue
            cur = f[0] | o << 8
            if look(cur) != (word[i] & 0xFF, word[i]):
                errs.append(f'row {hex(cur)} (ident {i}): file / word {look(cur)}, want home {hex(word[i])}')
            moved += cur != word[i]
            other += cur == word[i]
    if moved != 18:
        errs.append(f'{moved} crossers, want 18')
    hp = s7['S7_HPTR'] if 'S7_HPTR' in s7 else None
    return not errs, '; '.join(errs[:5]) or (f'wn_disk (patched entry): before the swaps every club by itself; after them {moved} '
                                              f'crossers read their home TEAM file / record, {other} others their own')


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
        m.call('s7swap', 's7_load', TB, f, 0)
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
        m.call('s7swap', 's7_load', TB, f, 0)
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
        m.call('s7swap', 's7_load', TB, FB, 0)
        if ld(m)[0] != want or m.rd(TB, len(b)) != bytes(b):
            errs.append(f'{name}: status {ld(m)[0]} (want {want}), buffer {"kept" if m.rd(TB, len(b)) == bytes(b) else "changed"}')
    b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))   # ORIG not readable: oread 2 -> LD_READ, retried next load
    b[1] = 2
    m.w(m.at('s7swap', 'S7_LD'), bytes(b))
    m.w(TB, fil[FB])
    c0 = ld(m)[3]
    m.call('s7swap', 's7_load', TB, FB, 0)                 # (Unicorn: no DOS - the retry's read fails again)
    if ld(m)[0] != LD_READ or m.rd(TB, len(fil[FB])) != fil[FB] or ld(m)[3] != c0 + 1:
        errs.append(f'LD_READ: status {ld(m)[0]}, buffer {"kept" if m.rd(TB, len(fil[FB])) == fil[FB] else "changed"}')
    c1 = ld(m)[3]
    m.call('s7swap', 's7_load', TB, 103, 0)
    if ld(m)[3] != c1:
        errs.append('file 103 counted')
    m.world(0)                                          # (a new career in another world: no registry)
    m.new_career()
    m.call('s7swap', 's7_load', TB, FB, 0)
    if ld(m)[0] != LD_NOREG:
        errs.append(f'no world: status {ld(m)[0]} (want {LD_NOREG})')
    return not errs, '; '.join(errs[:6]) or (f'9 + 9 rows given their registry club\'s home record, bytes {KEPT} kept '
                                             f'(one mark each), unmoved rows as read; refused a changed file (re-read) / '
                                             f'a wrong count / LD_READ / LD_NOREG with the buffer kept; other files ignored')


OB = TB + 0x20000                                       # (a pooled file's RI_ORIG stand-in: the file as read)


def test_s7load_pooled():
    """MC 13/11 (2a, option B): on a pooled file ripool's ri_apply writes the pool identities into TEAMBUF BEFORE
    s7_load; s7_load must hash the file AS READ (ri's ORIG copy, its third argument) and apply to TEAMBUF. After the
    9-swap season: LD_OK, 9 rows given their registry club's home record, every other row exactly as ri_apply left it
    (its pool identity kept). CONTROL: the old call (orig 0 = hash TEAMBUF) on the same buffer is refused (LD_FILE /
    LD_READ), nothing applied - the bug seen on the real pack (S7_LD 5 at every load of file 144)."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 's7_load' not in sy.get('s7swap', {}):
        return False, f'{EXE}: no s7_load (piece 3 not linked)'
    data = os.path.join(os.path.dirname(EXE), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (FA, FB)}
    m = M(EXE)
    m.uc.mem_map(TB, 0x40000)
    import s7swap
    oat = struct.unpack('<II', m.rd(m.at('s7swap', 'S7_OAT'), 8))
    onrec = struct.unpack('<HH', m.rd(m.at('s7swap', 'S7_ONREC'), 4))
    m.fresh()
    fs, word, at, rdiv, rows = reg_parse(m.regb())
    m.w(m.at('swefile', 'swe_fopen_r'), b'\xb8\xfe\xff\xff\xff\xc3')   # (no DOS: a re-read fails)
    down, up = crossings(fs, m.gb)
    st, nsw, _, _ = run(m, down, up)
    if st != OK:
        return False, f'season status {st}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    orig = m.at('swe', 'S7_ORIG')

    def fill_orig():
        for s_, f in enumerate((FA, FB)):
            m.w(orig + oat[s_], fil[f])
        b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))
        b[1] = 1
        m.w(m.at('s7swap', 'S7_LD'), bytes(b))
        m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *(s7swap.fnv(fil[f]) for f in (FA, FB))))
    f, fi = FB, 1
    rec = lambda f_, o: fil[f_][2 + 684 * o:2 + 684 * (o + 1)]
    pooled = bytearray(fil[f])                          # (ri_apply's stand-in: every row a pool identity - its name
    for o in range(onrec[fi]):                          #  bytes and the rest of its record changed, row bytes kept)
        for b in range(5, 684):
            if b not in KEPT:
                pooled[2 + 684 * o + b] ^= 0x5A
    errs = []
    fill_orig()
    m.w(TB, bytes(pooled))
    m.call('s7swap', 's7_load', TB, f, 0)               # CONTROL: the old call (hash TEAMBUF after ri_apply)
    st0 = ld(m)[0]
    if st0 == LD_OK or m.rd(TB, len(pooled)) != bytes(pooled):
        errs.append(f'control (old order / hash): status {st0}, buffer {"kept" if m.rd(TB, len(pooled)) == bytes(pooled) else "changed"} '
                    f'(want a refusal: the bug)')
    fill_orig()
    m.w(OB, fil[f])
    m.w(TB, bytes(pooled))
    m.call('s7swap', 's7_load', TB, f, OB)              # (option B: the file as read hashed, TEAMBUF applied)
    st1, oread, moved, _ = ld(m)
    if (st1, moved) != (LD_OK, 9):
        errs.append(f'pooled: status {st1} moved {moved} (want {LD_OK}, 9)')
    got = m.rd(TB, len(pooled))
    kept = mv = 0
    for o in range(rows1[fi]):
        h = word[at1[fi][o]]
        r = got[2 + 684 * o:2 + 684 * (o + 1)]
        if h == (f | o << 8):
            kept += 1
            if r != bytes(pooled[2 + 684 * o:2 + 684 * (o + 1)]):
                errs.append(f'row {o}: its own club, but not as ri_apply left it')
        else:
            mv += 1
            want = bytearray(rec(h & 0xFF, h >> 8))
            for b in KEPT:
                want[b] = pooled[2 + 684 * o + b]
            if r != bytes(want):
                errs.append(f'row {o} (home {h & 0xFF}/{h >> 8}): not its registry club\'s home record')
    if m.rd(OB, len(fil[f])) != fil[f]:
        errs.append('the ORIG copy was written')
    return not errs, '; '.join(errs[:6]) or (f'file {f} pooled: control (old hash of TEAMBUF) refused with status {st0}, '
                                             f'nothing applied; option B: LD_OK, {mv} rows their registry club\'s home '
                                             f'record, {kept} rows exactly as ri_apply left them, ORIG untouched')


EXE4 = os.environ.get('HT_S7W_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-p6w', 'SWOS', 'ITALIAN.EXE')
CACHE_AT = 0x6300000                                    # (a stand-in team cache: S7_SELBASE -> here)
S7_WSITE = 9


def test_s7walk():
    """piece 4 on c/S7W-p6w (shaped, S7_WSITES_TEST=1: wsites.TEST_ROWS = a cache row of 3 words at record +100, a
    careerFileBuffer row of 4 globals at +0x200, the engine item ST's 4 words at +16): after the 9 swaps
    - every listed word / global of a club that moved is its club's new one (the registry's), a global of a split
      file's second run included when one moves, the others kept (unmoved, none 0 / FFFF, another file);
    - the team cache's records follow their clubs: a moved club's record gets its new row's word (0..1), global (2..3,
      LE as in memory) and league byte (25 = the row's base + next season's delta), its other bytes kept; unmoved
      records untouched;
    - the career club (option B, MC 13/11) crossing down: selTeamNumber = its new word, careerTeamLeague = the new
      row's base division, careerTeam's own bytes as a cache record's, the rest of careerTeam (its squad) kept; the
      partner club (the one now at the career club's old word) keeps its own cached record (no squad written back);
      a career club that does not cross: nothing of its words changes;
    - S7_WLOG: rows walked 3, words changed, cache records moved;
    - a bad row (form O8 poked into WSITES): the season refused before the registry changes (S7_WSITE), nothing
      written."""
    if not os.path.exists(EXE4) or not os.path.exists(EXE4[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE4} (shaped, S7_WSITES_TEST=1 HOSTTEST_SYMS=1) missing'
    sy = json.load(open(EXE4[:-4] + '.syms.json'))
    if 'ST_ITEM' not in sy.get('s7swap', {}):
        return False, f'{EXE4}: no WSITES test rows (S7_WSITES_TEST=1)'
    m = M(EXE4)
    m.uc.mem_map(CACHE_AT, 0x10000)
    errs = []
    m.fresh()
    r0 = m.regb()
    fs, word, at, rdiv, rows = reg_parse(r0)
    down, up = crossings(fs, m.gb)
    gb = m.gb

    def glob(f, o):
        return glob_of(gb[0 if f == FA else 1], o)
    dn = [e[1] for e in down]                           # (moving words: 102's down, 144's up)
    upw = [e[1] for e in up]
    stay = FA | 10 << 8
    words = [dn[0], upw[0], stay]
    cfbg = [glob(FA, dn[1] >> 8), glob(FB, upw[1] >> 8), glob(FA, 10), 7]
    stw = [dn[2], 0xFFFF, 0, 103 | 4 << 8]
    data = os.path.join(os.path.dirname(EXE4), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (FA, FB)}
    recs = []
    for w in (dn[0], upw[0], stay):                     # the cache: 3 records (their file records), marked
        r = bytearray(fil[w & 0xFF][2 + 684 * (w >> 8):2 + 684 * ((w >> 8) + 1)])
        for k, x in enumerate(words):
            struct.pack_into('<H', r, 100 + 2 * k, x)
        r[200] = 0x5A
        recs.append(bytes(r))
    m.w(CACHE_AT, b''.join(recs))
    m.w(m.at('s7swap', 'S7_NUMSEL'), struct.pack('<H', 3))
    m.w(m.at('s7swap', 'S7_SELBASE'), struct.pack('<I', CACHE_AT))
    cfb = m.at('s7swap', 'S7_CFB') + 0x200
    st = m.at('s7swap', 'ST_ITEM') + 16
    m.w(cfb, struct.pack('<4H', *cfbg))
    m.w(st, struct.pack('<4H', *stw))
    cteam0 = bytearray(recs[0])                         # the career club = the cached dn[0] (its squad marked)
    cteam0[300:310] = b'CAREERSQD!'
    m.w(m.at('s7swap', 'S7_CTEAM'), bytes(cteam0))
    m.w(m.at('s7swap', 'S7_SELTEAM'), struct.pack('<H', dn[0]))
    m.w(m.at('s7swap', 'S7_CTLEAGUE'), struct.pack('<H', 4))
    stt, nsw, ncr, slt = run(m, down, up)
    if stt != OK:
        return False, f'season status {stt}'
    fs1, word1, at1, rdiv1, rows1 = reg_parse(m.regb())
    ident = {w: i for i, w in enumerate(word)}
    nw = lambda w: word1[ident[w]] if w in ident else w
    gfile = {}

    def nglob(g):
        for f in (FA, FB):
            for o in range(rows[[x[0] for x in fs].index(f)]):
                if glob(f, o) == g:
                    w2 = nw(f | o << 8)
                    return glob(w2 & 0xFF, w2 >> 8)
        return g
    got_c = list(struct.unpack('<4H', m.rd(cfb, 8)))
    if got_c != [nglob(g) for g in cfbg] or got_c[2] != cfbg[2] or got_c[3] != 7:
        errs.append(f'CFB globals {got_c} (want {[nglob(g) for g in cfbg]})')
    got_s = list(struct.unpack('<4H', m.rd(st, 8)))
    if got_s != [nw(stw[0]), 0xFFFF, 0, stw[3]]:
        errs.append(f'ST words {[hex(x) for x in got_s]}')
    cache = m.rd(CACHE_AT, 3 * 684)
    for k, w in enumerate((dn[0], upw[0], stay)):
        r = cache[684 * k:684 * (k + 1)]
        w2 = nw(w)
        fi2 = [x[0] for x in fs1].index(w2 & 0xFF)
        want = bytearray(recs[k])
        for j, x in enumerate(words):
            struct.pack_into('<H', want, 100 + 2 * j, nw(x))
        if w2 != w:
            want[0], want[1] = w2 & 0xFF, w2 >> 8
            g2 = glob(w2 & 0xFF, w2 >> 8)
            struct.pack_into('<H', want, 2, g2)
            want[25] = (base_local(fs1[fi2], w2 >> 8) + struct.unpack('b', slt[g2:g2 + 1])[0]) & 0xFF
        if r != bytes(want):
            errs.append(f'cache record {k} ({w:#x} -> {w2:#x}): differs at {[b for b in range(684) if r[b] != want[b]][:8]}')
    wl = struct.unpack('<hhHHHH', m.rd(m.at('s7swap', 'S7_WLOG'), 12))
    if wl[0] != -1 or wl[5] != 3 or wl[3] != 2:
        errs.append(f'S7_WLOG {wl} (row -1, rows 3, cache 2)')
    # (MC 13/11) the game's own in-memory global: the crossed record through SetLoadedTeamsGlobalNumbers
    ri = sy.get('ripool', {})
    if 'SETGLOBALS' in ri:
        tb = m.at('ripool', 'TEAMBUF')                  # (the mov's immediate: teamFileBuffer itself)
        rec0 = bytearray(cache[0:684])
        rec0[2:4] = b'\0\0'
        m.w(tb, b'\0\1' + bytes(rec0))
        from test_registry import _call as rcall
        if m.call('swe', 'reg_enter', 5) != 1:          # (world 5's teamsCountryNumbers, as in the game after the load)
            errs.append('reg_enter(5) refused')
        rcall(m.uc, m.at('ripool', 'SETGLOBALS'))
        m.call('swe', 'reg_leave')
        gg = struct.unpack_from('<H', m.rd(tb + 2, 4), 2)[0]
        if gg != struct.unpack_from('<H', cache, 2)[0]:
            errs.append(f'crossed record {cache[0]}/{cache[1]} global {struct.unpack_from("<H", cache, 2)[0]} != the game\'s {gg} (world {tg.WORLD})')
    else:
        errs.append('no ripool SETGLOBALS / TEAMBUF in the syms')
    c2 = nw(dn[0])                                      # the career club
    sel = struct.unpack('<H', m.rd(m.at('s7swap', 'S7_SELTEAM'), 2))[0]
    lg = struct.unpack('<H', m.rd(m.at('s7swap', 'S7_CTLEAGUE'), 2))[0]
    ct = m.rd(m.at('s7swap', 'S7_CTEAM'), 684)
    want = bytearray(cteam0)
    g2 = glob(c2 & 0xFF, c2 >> 8)
    b2 = base_local(fs1[[x[0] for x in fs1].index(c2 & 0xFF)], c2 >> 8)
    want[0], want[1] = c2 & 0xFF, c2 >> 8
    struct.pack_into('<H', want, 2, g2)
    want[25] = (b2 + struct.unpack('b', slt[g2:g2 + 1])[0]) & 0xFF
    if sel != c2 or c2 & 0xFF != FB or lg != b2 or ct != bytes(want):
        errs.append(f'career club: selTeamNumber {sel:#x} (want {c2:#x}), league {lg} (want {b2}), careerTeam '
                    f'{"ok" if ct == bytes(want) else [b for b in range(684) if ct[b] != want[b]][:8]}')
    if any(cache[684 * k + 300:684 * k + 310] == b'CAREERSQD!' for k in range(3)):
        errs.append('the career squad was written into a cached record')
    cl = struct.unpack('<HHh', m.rd(m.at('s7swap', 'S7_CLOG'), 6))
    if cl != (dn[0], c2, b2):
        errs.append(f'S7_CLOG {cl}')
    m.fresh()                                           # a career club that does not cross: its words kept
    m.w(m.at('s7swap', 'S7_SELTEAM'), struct.pack('<H', stay))
    m.w(m.at('s7swap', 'S7_CTLEAGUE'), struct.pack('<H', 0))
    m.w(m.at('s7swap', 'S7_CTEAM'), recs[2])
    stt, _, _, _ = run(m, down, up)
    if stt != OK or struct.unpack('<H', m.rd(m.at('s7swap', 'S7_SELTEAM'), 2))[0] != stay or \
            m.rd(m.at('s7swap', 'S7_CTEAM'), 684) != recs[2] or m.rd(m.at('s7swap', 'S7_CTLEAGUE'), 2) != b'\0\0':
        errs.append('a staying career club changed')
    m.fresh()                                           # a bad row: refused before anything changes
    ws = m.at('s7swap', 'WSITES')
    row = bytearray(m.rd(ws + 10, 10))
    row[8] = 3
    m.w(ws + 10, bytes(row))
    m.w(cfb, struct.pack('<4H', *cfbg))
    stt, _, _, slt = run(m, down, up)
    wl = struct.unpack('<hhHHHH', m.rd(m.at('s7swap', 'S7_WLOG'), 12))
    if stt != S7_WSITE or wl[0] != 1 or m.regb() != r0 or any(slt) or list(struct.unpack('<4H', m.rd(cfb, 8))) != cfbg:
        errs.append(f'bad row: status {stt} row {wl[0]}, registry {"kept" if m.regb() == r0 else "changed"}')
    return not errs, '; '.join(errs[:6]) or ('cache / CFB / ST rows remapped (moved words + globals, others kept), '
                                             'cache records followed their clubs (0..3, 25 new; rest kept), the career club crossed (selTeamNumber, careerTeamLeague, careerTeam own bytes; squad kept, not written to the partner), a staying one untouched, bad row '
                                             'refused before the registry changed')
