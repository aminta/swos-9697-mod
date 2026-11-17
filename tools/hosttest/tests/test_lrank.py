"""4.2 S1.3, tier B without a snapshot: lrank.c as linked into a build (obj1..obj4 relocated into Unicorn, the game's
variables written by the test) against the rules library built natively (tools/swce/sr_stage.c, ctypes) on random
Serie A seasons. The build: HT_LRANK_BUILD (default c/S1R/SWOS, a build with tie-breaker lists and HOSTTEST_SYMS=1;
none there: SKIP as a PASS).

- lr_res through lr_res_hook (esi = DIY, the game's own `add word [esi+1BDh], 1` done there): the pairs block equals
  the season's results (14 cap, FFh not played);
- lr_rank: DIY+6Dh = sr_league_rank's order with that block (the list's head-to-head), the native library's;
- the game's sort itself through its hooked entry (cseg_883DD -> lr_sort_hook -> lp36's lp_sort -> the sort ->
  lr_rank): the same order;
- void: a block started mid-season ranks without head to head (pairs NULL), and differs from the full list on some
  seasons (the control);
- not ours: the career club not in the league, a split league, Season mode (g_gameType 3): DIY+6Dh untouched."""
import ctypes
import json
import os
import random
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import fixroot  # noqa: E402
BUILD = fixroot.build_dir('HT_LRANK_BUILD')       # (the current fixture, never a fixed c/<old> dir: MC 17/11)
SEASONS = int(os.environ.get('HT_LRANK_SEASONS') or 300)


class SRow(ctypes.Structure):
    _fields_ = [('club', ctypes.c_uint8), ('pad', ctypes.c_uint8), ('pts', ctypes.c_int16)] + \
               [(f, ctypes.c_uint16) for f in ('pl', 'w', 'd', 'l', 'gf', 'ga', 'aw', 'agf')]


def native():
    d = tempfile.mkdtemp()
    so = os.path.join(d, 'libsr.dylib')
    subprocess.run(['clang', '-shared', '-O1', '-o', so, os.path.join(TOOLS, 'swce', 'sr_stage.c')], check=True)
    lib = ctypes.CDLL(so)
    lib.sr_league_rank.restype = ctypes.c_int32
    return lib


class Exe:
    """the build's objects in Unicorn at fixed bases, flat selectors"""
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS
        sys.path.insert(0, TOOLS)
        sys.path.insert(0, os.path.join(TOOLS, 'hosttest'))
        import emu
        from le import LE
        exe = os.path.join(BUILD, 'ITALIAN.EXE')
        le = LE(open(exe, 'rb').read())
        al = lambda x: (x + 0xFFFF) & ~0xFFFF
        self.base = {1: 0x100000}
        for k in (2, 3, 4):
            self.base[k] = al(self.base[k - 1] + le.obj(k - 1).vsize)
        o1, o2, le2 = emu.relocate(exe, *(self.base[k] for k in (1, 2, 3, 4)))
        self.top = al(self.base[4] + le.obj(4).vsize)
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(0, self.top + 0x200000)
        for k, img in ((1, o1), (2, o2), (3, le2.img3), (4, le2.img4)):
            uc.mem_write(self.base[k], bytes(img))
        self.gdt, self.stack, self.sent = self.top, self.top + 0x100000, self.top + 0x1FF000
        g = bytearray(8 * 64)
        g[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
        g[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
        uc.mem_write(self.gdt, bytes(g))
        uc.reg_write(UC_X86_REG_GDTR, (0, self.gdt, len(g) - 1, 0))
        for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
            uc.reg_write(r, emu.DATA_SEL)
        uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
        uc.mem_write(self.sent, b'\xf4')
        self.syms = json.load(open(os.path.join(BUILD, 'ITALIAN.syms.json')))['lrank']

    def lin(self, name):
        o, a = self.syms[name]
        return self.base[o] + a

    def rd(self, a, n):
        return bytes(self.uc.mem_read(a, n))

    def wr(self, a, b):
        self.uc.mem_write(a, bytes(b))

    def call(self, at, esi=0):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ESI
        sp = self.stack - 64
        self.wr(sp, struct.pack('<I', self.sent))
        self.uc.reg_write(UC_X86_REG_ESP, sp)
        self.uc.reg_write(UC_X86_REG_ESI, esi)
        self.uc.emu_start(at, self.sent, count=20_000_000)


LR_N = 20                                           # (lrank.c: the pairs block's clubs)


def ita(x, ent):
    """LR_TAB's entry ent of Italy (0 Serie A, 2 Serie C group A, 5 Serie D group A): every world league has entries
    since the 4.2 H2 import, Italy's are the 14 in a row"""
    tab, divs = x.lin('LR_TAB'), []
    while x.rd(tab + 24 * len(divs), 4) != bytes(4):
        divs.append(x.rd(tab + 24 * len(divs) + 5, 1)[0])
    return tab + 24 * (next(i for i in range(len(divs)) if divs[i:i + 14] == list(range(14))) + ent)


def setup(x, n, teams, career, gtype=4, serie_a=True, ent=0):
    ud = x.lin('UD')
    e = x.rd(ita(x, ent), 24)
    league, world, div = struct.unpack_from('<IBB', e)
    assert div == ent
    x.wr(ud, bytes(0x2B3 + 18 * 64))
    x.wr(ud + 0x31, struct.pack('<H', n))
    x.wr(ud + 0x4F, struct.pack('<HH', 1, n))       # (one group of n: cseg_883DD's loop)
    x.wr(ud + 0x61, struct.pack('<H', 3))
    for k, t in enumerate(teams):
        x.wr(ud + 0x12D + 2 * k, struct.pack('<H', t))
        x.wr(ud + 0x6D + 2 * k, struct.pack('<H', 18 * k))
    x.wr(x.lin('GAMETYPE'), struct.pack('<H', gtype))
    x.wr(x.lin('SIMFLAG'), struct.pack('<H', 0))
    x.wr(x.lin('CAREERTEAM'), struct.pack('<H', career))
    x.wr(x.lin('D8CAA'), struct.pack('<I', league if serie_a else league + 4))
    x.wr(x.lin('D6CDC'), struct.pack('<H', div))
    x.wr(x.lin('WORLDB'), bytes([world]))
    return ud, e[8:24].split(b'\0')[0]


def season(rnd, n):
    """a double round robin's results in a random match order: [(h, a, hg, ag)]"""
    m = [(h, a) for h in range(n) for a in range(n) if h != a]
    rnd.shuffle(m)
    pw = [rnd.random() for _ in range(n)]
    g = lambda s: min(rnd.choice((0, 0, 1, 1, 1, 2, 2, 3, 4)) + (s > 0.8) + (rnd.random() < 0.003) * 14, 20)
    return [(h, a, g(pw[h] + 0.1), g(pw[a])) for h, a in m]


def play(x, ud, res, upto, rows):
    """results [0, upto) through lr_res_hook, the rows as the game adds them after it"""
    a0 = x.lin('A3')
    for h, a, hg, ag in res[:upto]:
        x.wr(a0, struct.pack('<I', ud + 18 * h))
        x.wr(x.lin('A4'), struct.pack('<I', ud + 18 * a))
        x.wr(x.lin('D1'), struct.pack('<I', hg))
        x.wr(x.lin('D2'), struct.pack('<I', ag))
        x.call(x.lin('lr_res_hook'), esi=ud)
        for c, gf, ga in ((h, hg, ag), (a, ag, hg)):
            r = rows[c]
            r[0] += 1
            r[1 + (0 if gf > ga else 1 if gf == ga else 2)] += 1
            r[4] += gf
            r[5] += ga
            r[6] += 3 if gf > ga else gf == ga
    for c, r in enumerate(rows):
        x.wr(ud + 0x2B3 + 18 * c + 4, struct.pack('<7H', *r))


def lib_rank(lib, n, rows, pairs, codes, seed):
    a = (SRow * 64)()
    for c, r in enumerate(rows):
        a[c].club, a[c].pts, a[c].pl, a[c].w, a[c].d, a[c].l, a[c].gf, a[c].ga = c, r[6], *r[:6]
    if pairs is not None:
        for h in range(n):
            for k in range(n):
                v = pairs[h * n + k]
                if v != 0xFF:
                    a[k].agf += v & 15
                    a[k].aw += (v & 15) > v >> 4
    ordb = (ctypes.c_uint8 * 64)()
    pb = (ctypes.c_uint8 * len(pairs)).from_buffer_copy(bytes(pairs)) if pairs is not None else None
    tb = (ctypes.c_uint8 * 17).from_buffer_copy(codes + bytes(17 - len(codes)))
    r = lib.sr_league_rank(n, a, pb, None, 3, 1, 0, tb, ctypes.c_uint32(seed), ordb)
    assert r == n, r
    return list(ordb[:n])


def order(x, ud, n):
    return [struct.unpack_from('<H', x.rd(ud + 0x6D + 2 * k, 2))[0] // 18 for k in range(n)]


def test_lrank_differential():
    fixroot.need(BUILD, 'test_lrank', 'ITALIAN.syms.json')
    x, lib, rnd = Exe(), native(), random.Random(1926)
    blk = x.lin('LR_BLK')
    stats = dict(seasons=0, sort=0, void_differs=0, notours=0, partial=0)
    for s in range(SEASONS):
        ent = (0, 2, 5)[s % 3]                                     # (Serie A, C, D: their lists)
        n = x.rd(ita(x, ent) + 7, 1)[0]                            # (the division's clubs: mine() checks DIY's n)
        stats[f'div{ent}'] = stats.get(f'div{ent}', 0) + 1
        teams = [0x1300 | k + 1 + (s % 7) for k in range(n)]
        sp = (s % 90) + 1
        x.wr(x.lin('SEASONP'), bytes([sp]))
        ud, codes = setup(x, n, teams, teams[s % n], ent=ent)
        res = season(rnd, n)
        upto = len(res) if s % 4 else rnd.randrange(1, len(res))   # (a quarter: the table mid-season)
        rows = [[0] * 7 for _ in range(n)]
        mid = s % 10 == 9                                          # (a block started mid-season: void)
        if mid:
            x.wr(blk, bytes(4))
            for c in range(n):
                rows[c][1] = 1                                     # (a played row before the first result)
            for c, r in enumerate(rows):
                x.wr(ud + 0x2B3 + 18 * c + 4, struct.pack('<7H', *r))
        play(x, ud, res, upto, rows)
        b = x.rd(blk, 4 + n * n)
        stamp = (sp + 1) & 0xFF
        if mid:
            if b[:2] != bytes([stamp, n | 0x80]):
                return False, f'season {s}: void block head {b[:4].hex()}'
            pairs = None
        else:
            want = bytearray([0xFF]) * (n * n)
            for h, a, hg, ag in res[:upto]:
                want[h * n + a] = min(hg, 14) << 4 | min(ag, 14)
            if b[:4] != bytes([stamp, n]) + struct.pack('<H', teams[0]) or b[4:] != want:
                return False, f'season {s}: pairs block differs ({b[:4].hex()})'
            pairs = bytes(b[4:])
        seed = (stamp * 0x9E3779B1 ^ teams[0]) & 0xFFFFFFFF
        ref = lib_rank(lib, n, rows, pairs, codes, seed)
        if not mid:
            nov = lib_rank(lib, n, rows, None, codes, seed)
            stats['void_differs'] += nov != ref
        x.call(x.lin('lr_rank'))
        got = order(x, ud, n)
        if got != ref:
            return False, f'season {s} (upto {upto}, void {mid}): exe {got} != library {ref}'
        for k in range(n):                                         # (the game's sort through its hooked entry)
            x.wr(ud + 0x6D + 2 * k, struct.pack('<H', 18 * ((k * 7) % n)))
        x.call(x.base[1] + x.syms['ext.sort'][1])
        got = order(x, ud, n)
        if got != ref:
            return False, f'season {s}: the sort entry gives {got}, the library {ref}'
        stats['sort'] += 1
        stats['partial'] += upto < len(res)
        blk0 = x.rd(blk, 4 + LR_N * LR_N)
        for how in ('stranger', 'split', 'season_mode', 'other_league', 'groups', 'clubs'):   # (not ours: 6Dh untouched)
            setup(x, n, teams, 0x7777 if how == 'stranger' else teams[0], gtype=3 if how == 'season_mode' else 4,
                  serie_a=how != 'other_league', ent=ent)
            if how == 'groups':                                    # (H5 B1: a European group stage holding the career
                x.wr(ud + 0x4F, struct.pack('<HH', 2, n // 2))     #  club under the league's globals - 2 groups)
            if how == 'clubs':                                     # (a league phase of another size: n - 1 clubs)
                x.wr(ud + 0x31, struct.pack('<H', n - 1))
                x.wr(ud + 0x4F, struct.pack('<HH', 1, n - 1))
            for c, r in enumerate(rows):
                x.wr(ud + 0x2B3 + 18 * c + 4, struct.pack('<7H', *r))
            if how == 'split':
                import split
                x.wr(ud + split.ST, struct.pack('<H', split.MAGIC))
            perm = list(range(n))
            rnd.shuffle(perm)
            for k in range(n):
                x.wr(ud + 0x6D + 2 * k, struct.pack('<H', 18 * perm[k]))
            x.call(x.lin('lr_rank'))
            if order(x, ud, n) != perm:
                return False, f'season {s}: {how} league re-ranked'
            if how == 'stranger':                                  # (the game's own sort behind the hook: points,
                x.call(x.base[1] + x.syms['ext.sort'][1])          #  goal difference, goals for)
                key = [(r[6], r[4] - r[5], r[4]) for r in rows]
                o = order(x, ud, n)
                if any(key[o[k]] < key[o[k + 1]] for k in range(n - 1)) or o == ref and o != sorted(o, key=lambda c: key[c], reverse=True):
                    return False, f'season {s}: the game sort did not run behind the hook ({o})'
                stats['gamesort'] = stats.get('gamesort', 0) + 1
            play(x, ud, [(0, 1, 2, 1)], 1, [list(r) for r in rows])        # (a result there: the block untouched)
            if x.rd(blk, 4 + LR_N * LR_N) != blk0:
                return False, f'season {s}: {how}: a result changed the pairs block'
            stats['notours'] += 1
        stats['seasons'] += 1
    if not stats['void_differs']:
        return False, f'control: head to head never changed an order ({stats})'
    return True, ', '.join(f'{k} {v}' for k, v in stats.items())


def test_lrank_vendored():
    """tools/swce/ = the engine's rules/ files at tools/swce/SWCE_SHA (HT_ENGINE checkout; none: SKIP as a PASS)"""
    eng = os.environ.get('HT_ENGINE') or os.path.join(os.path.expanduser('~'), 'swos-competition-engine')
    sha = open(os.path.join(TOOLS, 'swce', 'SWCE_SHA')).read().split()[0]
    if not os.path.isdir(eng):
        return True, f'SKIP: no engine checkout at {eng}'
    for f in ('swosrules.h', 'sr_stage.c'):
        r = subprocess.run(['git', '-C', eng, 'show', f'{sha}:rules/{f}'], capture_output=True)
        if r.returncode:
            return False, f'{sha}: {r.stderr.decode().strip()}'
        if r.stdout != open(os.path.join(TOOLS, 'swce', f), 'rb').read():
            return False, f'tools/swce/{f} differs from the engine at {sha}'
    return True, f'tools/swce = engine {sha}'
