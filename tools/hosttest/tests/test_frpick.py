"""4.2 preseason friendlies, part (b): the opponent pick tools/frpick.c against tools/frpick.h's rules. Host only: the
C file built natively (clang -shared, ctypes) at -O0 / -O2 / -Oz, compared with ref() below - a Python reference of
the header's rules written from the header, not from the C (only the hash's constants are shared: the header leaves
the mix to the C file) - on random synthetic FRSS v2 tables, plus the directed cases of every rule, the committed real
tables (tools/frdata/frstr_w*.bin; a v1 1996-97 blob is made v2 here) and the size / stack of the object built with
cobj's exe flags at -Oz. HT_FRPICK_CASES = the number of random cases (default 2000)."""
import ctypes
import os
import random
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(TOOLS, 'frpick.c')
CASES = int(os.environ.get('HT_FRPICK_CASES') or 2000)
NONE = 0xFFFF
OK, NOSELF, BADBLOB, NOPOOL, GIVEN = 0, -1, -2, -3, -4
E_NOCLUB, E_SELF, E_BTEAM, E_DUP, E_HOME, E_ROOM = -1, -2, -3, -4, -5, -6
STRONGER, SIMILAR, WEAKER = 0, 1, 2
M32 = 0xFFFFFFFF


class FrPick(ctypes.Structure):
    _fields_ = [('word', ctypes.c_uint16 * 4), ('home', ctypes.c_uint8), ('fb', ctypes.c_uint8),
                ('band', ctypes.c_uint8 * 4), ('why', ctypes.c_int8 * 4)]


CACHED = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint16)


class FrRoom(ctypes.Structure):
    _fields_ = [('room', ctypes.c_uint32), ('cached', CACHED), ('ctx', ctypes.c_void_p)]


_LIB = {}
_TMP = tempfile.mkdtemp(prefix='frpick')


def lib(opt='-O2'):
    if opt not in _LIB:
        so = os.path.join(_TMP, f'frpick{opt}.dylib')
        subprocess.run(['clang', '-shared', opt, '-Wall', '-Werror', '-o', so, SRC], check=True)
        l = ctypes.CDLL(so)
        l.fr_pick.restype = ctypes.c_int
        l.fr_pick.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(FrPick)]
        _LIB[opt] = l
    return _LIB[opt]


def cpick(blob, world, self_, self2=NONE, given=None, avoid=(), room=None, cached=(), season=0, seed=0, nhome=2,
          opt='-O2', calls=None):
    """fr_pick -> (rc, words, home, fb, bands, why); room = None (no FrRoom) or the room count, cached = the words
    in the team cache; calls = a list that receives every cached() call's word"""
    out = FrPick()
    ctypes.memset(ctypes.byref(out), 0xA5, ctypes.sizeof(out))      # (the C must not rely on a zeroed *out)
    g = (ctypes.c_uint16 * 4)(*given) if given is not None else None
    a = (ctypes.c_uint16 * max(1, len(avoid)))(*avoid)
    r = None
    if room is not None:
        def cb(ctx, w):
            if calls is not None:
                calls.append(w)
            return 1 if w in cached else 0
        r = FrRoom(room, CACHED(cb), None)
    rc = lib(opt).fr_pick(blob, len(blob), world, self_, self2, g, a, len(avoid), ctypes.byref(r) if r else None,
                          season & M32, seed & M32, nhome, ctypes.byref(out))
    return rc, list(out.word), out.home, out.fb, list(out.band), list(out.why)


# ---- the table ----
def mkblob(blocks, version=2):
    """blocks = [(world, file, country, [strength by ordinal])] in the given order"""
    idx, vals = b'', []
    for w, fl, c, st in blocks:
        idx += struct.pack('<BBBBH', w, fl, len(st), c, len(vals))
        vals += st
    return b'FRSS' + struct.pack('<BBH', version, 0, len(blocks)) + idx + struct.pack(f'<{len(vals)}H', *vals)


def word(fl, o):
    return fl | o << 8


# ---- the reference (frpick.h's rules) ----
def rhash(seed, season, slot, w):
    h = (seed ^ (season * 0x9E3779B1) ^ ((slot << 16 | w) * 0x85EBCA6B)) & M32
    h ^= h >> 16
    h = h * 0x7FEB352D & M32
    h ^= h >> 15
    h = h * 0x846CA68B & M32
    return h ^ h >> 16


def rparse(b):
    """[(world, file, country, [strengths])] of a v2 blob, None = refused"""
    if len(b) < 8 or b[:4] != b'FRSS' or b[4] != 2:
        return None
    n = struct.unpack_from('<H', b, 6)[0]
    if len(b) < 8 + 6 * n:
        return None
    ent, end = [], 0
    for i in range(n):
        w, fl, cnt, c, first = struct.unpack_from('<BBBBH', b, 8 + 6 * i)
        if first != end:
            return None
        ent.append((w, fl, c, cnt, first))
        end += cnt
    if len(b) != 8 + 6 * n + 2 * end:
        return None
    return [(w, fl, c, list(struct.unpack_from(f'<{cnt}H', b, 8 + 6 * n + 2 * first))) for w, fl, c, cnt, first in ent]


def ref(blob, world, self_, self2=NONE, given=None, avoid=(), room=None, cached=(), season=0, seed=0, nhome=2):
    """the header's rules -> (rc, words, home, fb, bands, why); words .. bands None when rc < 0"""
    why = [0] * 4
    tab = rparse(blob)
    if tab is None:
        return BADBLOB, None, None, None, None, why
    clubs, info = [], {}                                # table order; word -> (strength, country), first entry wins
    seen = set()
    for w, fl, c, st in tab:
        if w != world:
            continue
        for o, s in enumerate(st):
            if s:
                clubs.append((word(fl, o), s, c))
                if fl not in seen:
                    info[word(fl, o)] = (s, c)
        seen.add(fl)
    if self_ not in info:
        return NOSELF, None, None, None, None, why
    S, home_c = info[self_]
    M = max(11, S // 10)

    def band(s):
        return STRONGER if s - S > M else WEAKER if s - S < -M else SIMILAR

    given = list(given) if given is not None else [NONE] * 4
    left = room
    four = [None] * 4                                   # (word, strength, country)
    for k, g in enumerate(given):
        if g == NONE:
            continue
        if g not in info:
            why[k] = E_NOCLUB
        elif g == self_:
            why[k] = E_SELF
        elif g == self2:
            why[k] = E_BTEAM
        elif g in given[:k]:
            why[k] = E_DUP
        elif info[g][1] == home_c:
            why[k] = E_HOME
        elif room is not None and g not in cached and left == 0:
            why[k] = E_ROOM
        else:
            if room is not None and g not in cached:
                left -= 1
            four[k] = (g,) + info[g]
    if any(why):
        return GIVEN, None, None, None, None, why
    mix = [SIMILAR, SIMILAR, WEAKER, STRONGER]          # the order the uncovered bands are taken in
    for f in four:
        if f and band(f[1]) in mix:
            mix.remove(band(f[1]))
    empty = [k for k in range(4) if four[k] is None]
    wanted = sorted(mix[:len(empty)], key=lambda b: -b)             # weakest first: weaker 2, similar 1, stronger 0
    fb = 0
    for k, want in zip(empty, wanted):
        used_w = {f[0] for f in four if f}
        used_c = {f[2] for f in four if f}
        best = None
        for w, s, c in clubs:
            if c == home_c or w in (self_, self2) or w in used_w:
                continue
            if room is not None and left == 0 and w not in cached:
                continue
            d = s - S
            if band(s) == want:
                dist = 0
            elif want == STRONGER:
                dist = (S + M + 1) - s
            elif want == WEAKER:
                dist = s - (S - M - 1)
            else:
                dist = abs(d) - M
            assert dist >= 0
            key = (dist, int(w in avoid), int(c in used_c), rhash(seed & M32, season & M32, k, w))
            if best is None or key < best[0]:
                best = (key, (w, s, c))
        if best is None:
            return NOPOOL, None, None, None, None, [0] * 4
        if room is not None and best[1][0] not in cached:
            left -= 1
        four[k] = best[1]
        if best[0][0]:
            fb |= 1 << k
    order = sorted(range(4), key=lambda k: (four[k][1], k))
    home = sum(1 << k for k in order[:min(nhome, 4)])
    return OK, [f[0] for f in four], home, fb, [band(f[1]) for f in four], why


def same(c, r):
    """a C result against a reference result: everything on FR_OK, the code and why[] otherwise"""
    return c == r if r[0] == OK else (c[0], c[5]) == (r[0], r[5])


# ---- random cases ----
def rand_case(rng):
    nb = rng.randint(1, 14)
    nc = rng.randint(1, 8)
    files = sorted(rng.sample(range(0, 200), nb))
    spread = rng.choice([3, 30, 200, 600, 5000, 60000])
    base = rng.randint(5, 65535 - spread)
    world = rng.randint(0, 3)
    blocks = []
    for fl in files:
        cnt = rng.choice([0, 1, 2, 3, 5, 8, 20, 40]) if rng.random() < .9 else 255
        st = [0 if rng.random() < .08 else base + rng.randint(0, spread) for _ in range(cnt)]
        blocks.append((world if rng.random() < .85 else (world + 1) & 3, fl, rng.randint(0, nc - 1), st))
    if rng.random() < .15:                                  # the same file in another world too
        w, fl, c, st = rng.choice(blocks)
        blocks.append(((w + 2) & 3, fl, rng.randint(0, nc - 1), [rng.randint(5, 500) for _ in range(rng.randint(0, 9))]))
    blocks.sort(key=lambda b: (b[0], b[1]))
    mine = [(word(fl, o), s) for w, fl, c, st in blocks if w == world for o, s in enumerate(st)]
    live = [w for w, s in mine if s]

    def club():
        r = rng.random()
        if r < .8 and live:
            return rng.choice(live)
        if r < .9 and mine:
            return rng.choice(mine)[0]
        return rng.randint(0, 0xFFFF)

    self_ = club() if rng.random() < .97 else rng.randint(0, 0xFFFF)
    self2 = NONE if rng.random() < .5 else (self_ & 0xFF | rng.randint(0, 40) << 8) if rng.random() < .6 else club()
    given = None
    r = rng.random()
    if r < .25:
        given = [club() if rng.random() < .45 else NONE for _ in range(4)]
        if rng.random() < .15:
            given[rng.randint(1, 3)] = given[0]
        if rng.random() < .1:
            given[rng.randint(0, 3)] = rng.choice([self_, self2])
    elif r < .3:
        given = [NONE] * 4
    avoid = [club() for _ in range(rng.choice([0, 0, 2, 4, 4, 6]))]
    room, cached = None, set()
    if rng.random() < .5:
        room = rng.choice([0, 0, 1, 2, 3, 4, 9])
        cached = {w for w in live if rng.random() < rng.choice([0, .05, .3, .9])}
    return dict(blob=mkblob(blocks), world=world, self_=self_, self2=self2, given=given, avoid=avoid, room=room,
                cached=cached, season=rng.choice([0, 1, 7, 1996, rng.getrandbits(32)]), seed=rng.getrandbits(32),
                nhome=rng.randint(0, 5) if rng.random() < .5 else 2)


def test_frpick_random_vs_reference():
    rng = random.Random(0xF41E)
    codes = {}
    for i in range(CASES):
        a = rand_case(rng)
        calls = []
        c, r = cpick(calls=calls, **a), ref(**a)
        if not same(c, r):
            return False, f'case {i}: C {c} != reference {r} ({ {k: v for k, v in a.items() if k != "blob"} })'
        if r[0] != GIVEN and any(c[5]):
            return False, f'case {i}: why {c[5]} with code {c[0]}'
        if a['room'] is None and calls:
            return False, f'case {i}: cached() called without a room'
        g = a['given'] or [NONE] * 4
        auto = sum(1 for x in g if x == NONE)
        for w in set(calls):
            if calls.count(w) > auto + g.count(w):
                return False, f'case {i}: cached({w:#x}) called {calls.count(w)} times, {auto} automatic slots'
        codes[r[0]] = codes.get(r[0], 0) + 1
    if min(codes.get(k, 0) for k in (OK, NOSELF, NOPOOL, GIVEN)) < 10:
        return False, f'the random cases do not reach every code: {codes}'
    return True, f'{CASES} random tables: C == reference; codes {dict(sorted(codes.items()))}'


def test_frpick_det():
    """the same outputs at -O0 / -O2 / -Oz (Motore's condition: test_frpick_det)"""
    rng = random.Random(0xDE7)
    n = max(300, CASES // 4)
    for i in range(n):
        a = rand_case(rng)
        rs = [cpick(opt=o, **a) for o in ('-O0', '-O2', '-Oz')]
        if rs[0][0] == OK and not rs[0] == rs[1] == rs[2] or len({(r[0], tuple(r[5])) for r in rs}) != 1:
            return False, f'case {i}: -O0 {rs[0]} -O2 {rs[1]} -Oz {rs[2]}'
        if cpick(**a) != rs[1]:
            return False, f'case {i}: two calls differ'
    return True, f'{n} random cases: -O0 == -O2 == -Oz, and call == call'


# ---- directed cases ----
def league(strengths, files=None, countries=None, world=0):
    """one block per list of strengths: file 10 + i, country = i unless given"""
    return mkblob([(world, files[i] if files else 10 + i, countries[i] if countries else i, st)
                   for i, st in enumerate(strengths)])


# self = file 10 ordinal 0, strength 200 (M = 20): weaker < 180, similar 180..220, stronger > 220
MIXED = league([[200, 210], [100, 150, 179], [180, 195, 205, 220], [221, 300, 400], [120, 200, 260], [90, 215, 500]])
SELF = word(10, 0)


def strength_of(blob, world=0):
    return {word(fl, o): (s, c) for w, fl, c, st in rparse(blob) if w == world for o, s in enumerate(st)}


def test_frpick_mix():
    st = strength_of(MIXED)
    for seed in range(200):
        rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF, seed=seed, season=seed * 7)
        if rc or bands != [WEAKER, SIMILAR, SIMILAR, STRONGER] or fb or any(why):
            return False, f'seed {seed}: {rc} bands {bands} fb {fb} why {why}'
        d = [st[w][0] - 200 for w in ws]
        if not (d[0] < -20 and abs(d[1]) <= 20 and abs(d[2]) <= 20 and d[3] > 20):
            return False, f'seed {seed}: strengths {d} off the bands'
    # the edges of the bands: S + M and S - M are similar, one more is stronger / weaker
    edge = league([[200], [180], [220], [179], [221]])
    rc, ws, home, fb, bands, why = cpick(edge, 0, SELF)
    if (rc, ws, fb) != (0, [word(13, 0), ws[1], ws[2], word(14, 0)], 0) or set(ws[1:3]) != {word(11, 0), word(12, 0)}:
        return False, f'edges: {rc} {ws} fb {fb}'
    # M by integer division: S = 119 -> M 11 (130 similar, 131 stronger), S = 120 -> M 12 (132 similar, 133 stronger)
    for S, sim, strg in ((119, 130, 131), (120, 132, 133), (50, 61, 62)):
        b = league([[S], [sim], [strg], [S], [S - 30]])
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF)
        if rc or fb or ws[3] != word(12, 0) or ws[0] != word(14, 0):
            return False, f'margin S {S}: {rc} {ws} fb {fb} {bands}'
    # the seeds really vary the choice
    if len({tuple(cpick(MIXED, 0, SELF, seed=s)[1]) for s in range(200)}) < 10:
        return False, 'the seed does not vary the four'
    if len({tuple(cpick(MIXED, 0, SELF, season=s)[1]) for s in range(200)}) < 10:
        return False, 'the season does not vary the four'
    return True, '200 seeds: weaker, similar, similar, stronger, fb 0; band edges; M = max(11, S / 10)'


def test_frpick_nearest_band():
    # the top club: no stronger one -> slot 3 takes the strongest club left (nearest to the stronger band's edge)
    top = league([[500], [100, 200], [460, 470, 480], [300, 499], [520, 0]], countries=[0, 1, 2, 3, 0])
    for seed in range(50):
        rc, ws, home, fb, bands, why = cpick(top, 0, SELF, seed=seed)
        left = max(s for w, (s, c) in strength_of(top).items() if c and w not in ws[:3])     # (c = 0: self's country)
        if rc or fb != 8 or bands != [WEAKER, SIMILAR, SIMILAR, SIMILAR] or strength_of(top)[ws[3]][0] != left:
            return False, f'top club seed {seed}: {rc} {ws} fb {fb:#x} bands {bands}'
        if ws[3] & 0xFF == 14:
            return False, f'top club seed {seed}: the stronger club of self\'s country picked'
    # the bottom club: no weaker one -> slot 0 takes the weakest club left
    bot = league([[50], [51, 55, 60], [58, 61], [62, 90, 300]])
    for seed in range(50):
        rc, ws, home, fb, bands, why = cpick(bot, 0, SELF, seed=seed)
        if rc or fb != 1 or bands != [SIMILAR, SIMILAR, SIMILAR, STRONGER] or ws[0] != word(11, 0):
            return False, f'bottom club seed {seed}: {rc} {ws} fb {fb:#x} bands {bands}'
    # no similar club at all: the two similar slots take the two nearest to the band, on either side
    gap = league([[200], [100, 170], [150, 240], [300, 260]])
    rc, ws, home, fb, bands, why = cpick(gap, 0, SELF)
    if rc or fb != 6 or set(ws[1:3]) != {word(11, 1), word(12, 1)} or sorted(bands[1:3]) != [STRONGER, WEAKER]:
        return False, f'no similar: {rc} {ws} fb {fb:#x} bands {bands}'
    # everything stronger: fb on the weaker and similar slots, the band of the club itself reported
    up = league([[100], [300, 310], [320, 330], [340, 350]])
    rc, ws, home, fb, bands, why = cpick(up, 0, SELF)
    if rc or fb != 7 or bands != [STRONGER] * 4 or ws[0] != word(11, 0) or ws[1] != word(11, 1) or ws[2] != word(12, 0):
        return False, f'all stronger: {rc} {ws} fb {fb:#x} bands {bands}'
    return True, 'top club: strongest left; bottom club: weakest left; empty similar band; fb only on an empty band'


def test_frpick_venues():
    st = strength_of(MIXED)
    for seed in range(40):
        for nhome in range(6):
            rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF, seed=seed, nhome=nhome)
            order = sorted(range(4), key=lambda k: (st[ws[k]][0], k))
            if rc or home != sum(1 << k for k in order[:min(nhome, 4)]):
                return False, f'seed {seed} nhome {nhome}: home {home:#x}, strengths {[st[w][0] for w in ws]}'
    rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF)
    if bin(home).count('1') != 2 or not home & 1 or home & 8:
        return False, f'default 2H / 2A: home {home:#x}'
    # ties: the lower slot first (given clubs of equal strength)
    tie = league([[200], [200], [200], [200], [200]])
    g = [word(11, 0), word(12, 0), word(13, 0), word(14, 0)]
    for nhome, want in ((0, 0), (1, 1), (2, 3), (3, 7), (4, 15), (5, 15), (99, 15)):
        rc, ws, home, fb, bands, why = cpick(tie, 0, SELF, given=g, nhome=nhome)
        if rc or home != want:
            return False, f'ties nhome {nhome}: {rc} home {home:#x}'
    return True, 'the nhome weakest at home for nhome 0..5 (> 4 = 4), default 2H / 2A, ties by slot'


def test_frpick_pool():
    # Italy's two files (115 + 144) share a country id: none of them is ever picked for an Italian club
    it = mkblob([(0, 20, 5, [200, 190, 210, 205]), (0, 30, 6, [150, 200, 250, 0, 201]), (0, 40, 7, [140, 199, 260]),
                 (0, 50, 8, [120, 202, 270]), (0, 60, 9, [100, 203, 280]),
                 (0, 115, 3, [200, 205, 150, 260, 0]), (0, 144, 3, [195, 100, 300, 210]),
                 (1, 70, 9, [200, 150, 260, 205])])                  # another world's block: never read
    st = strength_of(it)
    self_, self2 = word(115, 0), word(20, 1)
    seen = set()
    for seed in range(400):
        rc, ws, home, fb, bands, why = cpick(it, 0, self_, self2=self2, seed=seed, season=seed // 9)
        if rc or len(set(ws)) != 4:
            return False, f'seed {seed}: {rc} {ws}'
        for w in ws:
            if w in (self_, self2) or w & 0xFF in (115, 144, 70) or w not in st or not st[w][0]:
                return False, f'seed {seed}: {w:#x} picked ({ws})'
        seen |= set(ws)
    if word(30, 3) in seen or len(seen) < 8:
        return False, f'pool seen {sorted(seen)}'
    # ordinal >= count is never read: a blob whose only other clubs are self's country -> FR_NOPOOL, not a pick
    one = league([[200, 210, 190]])
    if cpick(one, 0, SELF)[0] != NOPOOL:
        return False, 'a one-country table must be FR_NOPOOL'
    # never twice: exactly four clubs abroad -> the four, each once, for every seed
    four = league([[200], [100, 0], [0, 200], [205], [300]])
    for seed in range(50):
        rc, ws, *_ = cpick(four, 0, SELF, seed=seed)
        if rc or sorted(ws) != sorted([word(11, 0), word(12, 1), word(13, 0), word(14, 0)]):
            return False, f'four clubs: {rc} {ws}'
    three = league([[200], [100, 0], [0, 200], [205]])
    if cpick(three, 0, SELF)[0] != NOPOOL:
        return False, 'three clubs abroad must be FR_NOPOOL'
    # self2 = FR_NONE excludes nothing; a self2 abroad is excluded
    if cpick(four, 0, SELF, self2=word(14, 0))[0] != NOPOOL or cpick(four, 0, SELF, self2=NONE)[0] != OK:
        return False, 'self2'
    return True, 'never self / self2 / self\'s country (two files, one id) / strength 0 / another world; no duplicates'


def test_frpick_avoid_countries():
    # each band has clubs of several countries: 4 distinct countries for every seed
    b = league([[200], [100, 190, 300, 110, 195, 310], [120, 200, 320, 125, 201, 330], [130, 205, 340, 135],
                [140, 210, 350, 145, 199], [150, 191, 360]])
    st = strength_of(b)
    for seed in range(300):
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, seed=seed)
        if rc or fb or len({st[w][1] for w in ws}) != 4:
            return False, f'seed {seed}: countries {[st[w][1] for w in ws]}'
    # ... but never at the cost of the band: the only similar clubs are in one country
    b2 = league([[200], [100, 300], [200, 201, 202], [110, 310]])
    rc, ws, home, fb, bands, why = cpick(b2, 0, SELF)
    if rc or fb or ws[1] >> 0 & 0xFF != 12 or ws[2] & 0xFF != 12:
        return False, f'band before country: {rc} {ws} fb {fb}'
    # avoid: last season's four are not picked again while the bands have other clubs
    for seed in range(100):
        last = cpick(b, 0, SELF, seed=seed)[1]
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, seed=seed, avoid=last)
        if rc or fb or set(ws) & set(last):
            return False, f'seed {seed}: {ws} repeats {last}'
        if cpick(b, 0, SELF, seed=seed, avoid=[])[1] != last:
            return False, 'navoid 0 changed the pick'
    # avoid before country: slot 1's similar clubs are (country 2, avoided) and (country 1 = slot 0's country)
    b3 = league([[200], [100, 201], [202], [300]])
    rc, ws, home, fb, bands, why = cpick(b3, 0, SELF, avoid=[word(12, 0)])
    if rc or ws != [word(11, 0), word(11, 1), word(12, 0), word(13, 0)]:
        return False, f'avoid before country: {rc} {ws}'
    # ... never at the cost of the band: the only weaker club is avoided -> still picked, fb 0
    rc, ws, home, fb, bands, why = cpick(b3, 0, SELF, avoid=[word(11, 0), word(13, 0)])
    if rc or fb or ws[0] != word(11, 0) or ws[3] != word(13, 0):
        return False, f'avoid against the band: {rc} {ws} fb {fb}'
    return True, '4 distinct countries where the bands allow; avoid respected while the band allows; band first'


def test_frpick_room():
    b = league([[200], [100, 190, 300, 110, 195, 310], [120, 200, 320, 125, 201, 330], [130, 205, 340, 135],
                [140, 210, 350, 145, 199], [150, 191, 360]])
    st = strength_of(b)
    live = [w for w in st if w != SELF]
    rng = random.Random(5)
    for i in range(300):
        cached = {w for w in live if rng.random() < rng.choice([.1, .4, .8])}
        room = rng.randint(0, 4)
        calls = []
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, seed=i, room=room, cached=cached, calls=calls)
        if rc == OK and sum(1 for w in ws if w not in cached) > room:
            return False, f'case {i}: {ws} loads more than room {room}'
        if rc not in (OK, NOPOOL) or (rc, ws, home, fb, bands, why) != ref(b, 0, SELF, seed=i, room=room, cached=cached) \
                and rc == OK:
            return False, f'case {i}: rc {rc} or C != reference'
        if max((calls.count(w) for w in set(calls)), default=0) > 4:
            return False, f'case {i}: a club asked more than once per slot pass'
    # room NULL: no call, and the same four as a room that fits everything
    free = cpick(b, 0, SELF, seed=3)
    calls = []
    if cpick(b, 0, SELF, seed=3, room=4, cached=set(), calls=calls) != free or len(calls) != 4:
        return False, f'room 4: {len(calls)} calls (4 expected: the chosen club of each slot)'
    calls = []
    if cpick(b, 0, SELF, seed=3, room=0, cached=set(live), calls=calls) != free:
        return False, 'room 0 with every club cached must change nothing'
    # room 0, nothing cached: FR_NOPOOL; room 0, four cached: exactly those
    if cpick(b, 0, SELF, room=0, cached=set())[0] != NOPOOL:
        return False, 'room 0 with an empty cache must be FR_NOPOOL'
    four = {word(11, 0), word(12, 1), word(13, 1), word(14, 2)}
    rc, ws, *_ = cpick(b, 0, SELF, room=0, cached=four)
    if rc or set(ws) != four:
        return False, f'room 0, four cached: {rc} {ws}'
    # one slot pass (three given): every candidate asked at most once, the given ones once each
    g = [word(11, 0), word(12, 1), NONE, word(14, 2)]
    for room, cached in ((0, {word(11, 0), word(12, 1), word(14, 2), word(13, 1)}), (3, set()), (4, set()), (9, set(live))):
        calls = []
        rc, ws, *_ = cpick(b, 0, SELF, given=g, room=room, cached=cached, calls=calls)
        if max(calls.count(w) for w in set(calls)) > 1 or any(calls.count(w) != 1 for w in g if w != NONE):
            return False, f'room {room}: calls {sorted(calls)}'
        if (rc == OK) != (room != 3):
            return False, f'room {room}: rc {rc}'
    # a given club that does not fit: FR_GIVEN / FR_E_ROOM on the first one past the room, cached ones still pass
    rc, ws, home, fb, bands, why = cpick(b, 0, SELF, given=g, room=1, cached={word(14, 2)})
    if rc != GIVEN or why != [0, E_ROOM, 0, 0]:
        return False, f'given without room: {rc} {why}'
    rc, ws, home, fb, bands, why = cpick(b, 0, SELF, given=g, room=0, cached=set())
    if rc != GIVEN or why != [E_ROOM, E_ROOM, 0, E_ROOM]:
        return False, f'given, room 0: {rc} {why}'
    return True, 'automatic slots skip what does not fit; given -> FR_E_ROOM; no call without a room; <= 1 call per pass'


def test_frpick_given():
    b = mkblob([(0, 10, 0, [200, 199]), (0, 11, 1, [100, 190, 300, 0]), (0, 12, 2, [120, 200, 320]),
                (0, 13, 3, [130, 205, 340]), (0, 14, 0, [150, 210]), (0, 15, 4, [90, 180, 400, 215]),
                (1, 16, 5, [200, 200])])
    self2 = word(14, 1)                                         # a B team abroad by file, same country here
    X = NONE
    cases = [                                                   # (given, expected why)
        ([word(16, 0), X, X, X], [E_NOCLUB, 0, 0, 0]),          # another world's file
        ([word(99, 0), X, X, X], [E_NOCLUB, 0, 0, 0]),          # no such file
        ([X, word(11, 4), X, X], [0, E_NOCLUB, 0, 0]),          # ordinal >= count
        ([X, X, word(11, 3), X], [0, 0, E_NOCLUB, 0]),          # strength 0
        ([X, X, X, SELF], [0, 0, 0, E_SELF]),
        ([self2, X, X, X], [E_BTEAM, 0, 0, 0]),                 # (before FR_E_HOME: self2 is of self's country)
        ([word(12, 0), word(12, 0), X, X], [0, E_DUP, 0, 0]),
        ([word(10, 1), X, word(10, 1), X], [E_HOME, 0, E_DUP, 0]),      # DUP before HOME
        ([SELF, SELF, X, X], [E_SELF, E_SELF, 0, 0]),           # SELF before DUP
        ([word(10, 1), word(14, 0), X, X], [E_HOME, E_HOME, 0, 0]),     # the country's two files
        ([word(99, 9), SELF, self2, word(10, 1)], [E_NOCLUB, E_SELF, E_BTEAM, E_HOME]),     # all reported together
        ([word(12, 0), word(99, 9), word(12, 0), word(14, 0)], [0, E_NOCLUB, E_DUP, E_HOME]),
    ]
    for g, want in cases:
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=g)
        if rc != GIVEN or why != want:
            return False, f'given {g}: {rc} why {why}, expected {want}'
    # FR_E_ROOM is the last check
    rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=[word(12, 0), word(10, 1), X, X], room=0)
    if rc != GIVEN or why != [E_ROOM, E_HOME, 0, 0]:
        return False, f'room last: {rc} {why}'
    # NULL == 4 x FR_NONE
    for seed in range(50):
        if cpick(b, 0, SELF, seed=seed, given=None) != cpick(b, 0, SELF, seed=seed, given=[X] * 4):
            return False, 'given NULL != 4 x 0xFFFF'
    # valid given: keep their slot, cover their band; the empty slots take the uncovered bands
    W, SI, ST = word(11, 0), word(12, 1), word(12, 2)           # weaker 100, similar 200, stronger 320
    SI2, ST2, W2 = word(13, 1), word(13, 2), word(13, 0)
    table = [                                                   # (given, the four's bands)
        ([X, X, X, ST], [WEAKER, SIMILAR, SIMILAR, STRONGER]),
        ([ST, X, X, X], [STRONGER, WEAKER, SIMILAR, SIMILAR]),
        ([X, W, X, X], [SIMILAR, WEAKER, SIMILAR, STRONGER]),
        ([X, X, SI, X], [WEAKER, SIMILAR, SIMILAR, STRONGER]),
        ([SI, X, X, X], [SIMILAR, WEAKER, SIMILAR, STRONGER]),
        ([SI, SI2, X, X], [SIMILAR, SIMILAR, WEAKER, STRONGER]),
        ([X, X, SI, SI2], [WEAKER, STRONGER, SIMILAR, SIMILAR]),
        ([ST, ST2, X, X], [STRONGER, STRONGER, SIMILAR, SIMILAR]),     # 2 stronger: similar, similar are taken first
        ([W, X, W2, X], [WEAKER, SIMILAR, WEAKER, SIMILAR]),
        ([X, ST, X, ST2], [SIMILAR, STRONGER, SIMILAR, STRONGER]),
        ([ST, ST2, word(15, 2), X], [STRONGER, STRONGER, STRONGER, SIMILAR]),
        ([W, W2, word(15, 0), X], [WEAKER, WEAKER, WEAKER, SIMILAR]),
        ([SI, SI2, word(15, 1), X], [SIMILAR, SIMILAR, SIMILAR, WEAKER]),
        ([ST, W, X, X], [STRONGER, WEAKER, SIMILAR, SIMILAR]),
        ([ST, SI, X, X], [STRONGER, SIMILAR, WEAKER, SIMILAR]),
        ([ST, SI, SI2, X], [STRONGER, SIMILAR, SIMILAR, WEAKER]),
        ([ST, SI, SI2, W], [STRONGER, SIMILAR, SIMILAR, WEAKER]),
    ]
    for g, want in table:
        for seed in range(20):
            rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=g, seed=seed, avoid=[x for x in g if x != X])
            if rc or fb or bands != want or any(why) or any(x != X and ws[k] != x for k, x in enumerate(g)) \
                    or len(set(ws)) != 4:
                return False, f'given {g} seed {seed}: {rc} {ws} bands {bands} (expected {want}) fb {fb}'
    return True, f'{len(cases)} refusal lists (order NOCLUB, SELF, BTEAM, DUP, HOME, ROOM), {len(table)} given mixes'


def test_frpick_codes():
    st = [[200, 210], [100, 150, 179], [180, 195, 205, 220], [221, 300, 400]]
    good = league(st)
    blocks = [(0, 10 + i, i, s) for i, s in enumerate(st)]
    if cpick(good, 0, SELF)[0] != OK:
        return False, 'the good blob'
    for name, self_, world in (('no file', word(99, 0), 0), ('ordinal >= count', word(10, 2), 0), ('world', SELF, 1)):
        r = cpick(good, world, self_)
        if r[0] != NOSELF or any(r[5]):
            return False, f'FR_NOSELF ({name}): {r}'
    if cpick(league([[0, 210]] + st[1:]), 0, SELF)[0] != NOSELF:
        return False, 'FR_NOSELF (strength 0)'
    bad = {'v1': mkblob(blocks, version=1), 'v3': mkblob(blocks, version=3), 'magic': b'FRSX' + good[4:],
           'short': good[:-2], 'odd': good[:-1], 'long': good + b'\0\0', 'empty': b'', '7 B': good[:7],
           'index cut': good[:8 + 6 * 2], 'header only': good[:8],
           'first != 0': good[:8 + 4] + b'\1\0' + good[8 + 6:],
           'gap': good[:8 + 6 + 4] + struct.pack('<H', 3) + good[8 + 12:],
           'count + 1': good[:8 + 2] + bytes([good[8 + 2] + 1]) + good[8 + 3:],
           'blocks + 1': good[:6] + struct.pack('<H', 5) + good[8:]}
    for name, b in bad.items():
        r = cpick(b, 0, SELF)
        if r[0] != BADBLOB or any(r[5]):
            return False, f'FR_BADBLOB ({name}): {r}'
        if ref(b, 0, SELF)[0] != BADBLOB:
            return False, f'the reference accepts {name}'
    # FR_BADBLOB before FR_NOSELF before FR_GIVEN before FR_NOPOOL
    if cpick(bad['v1'], 0, word(99, 0))[0] != BADBLOB or cpick(good, 0, word(99, 0), given=[SELF] * 4)[0] != NOSELF:
        return False, 'the order of the codes'
    one = league([[200, 210]])
    if cpick(one, 0, SELF)[0] != NOPOOL or cpick(one, 0, SELF, given=[word(10, 1), NONE, NONE, NONE])[0] != GIVEN:
        return False, 'FR_NOPOOL / FR_GIVEN first'
    r = cpick(league([[200], [100], [200], [300]]), 0, SELF)
    if r[0] != NOPOOL or any(r[5]):
        return False, f'FR_NOPOOL with 3 clubs: {r}'
    return True, f'FR_NOSELF x 4, FR_BADBLOB x {len(bad)} (v1, magic, lengths, index), FR_NOPOOL, the codes\' order'


def _real(p):
    """one committed table tools/frdata/frstr_w<N>.bin -> (ok, message). A v2 blob is used as it is (frstr.py's
    country ids: one per country, the lowest file number of its club files). A v1 blob (the 1996-97 table before
    frstr.py's v2) is converted here with country id = the file number: in the 1996-97 world a club file IS a country
    (frstr.world0_files: TEAM.nnn of country nnn of the exe's continent tables), so no exe is needed."""
    raw = bytearray(open(p, 'rb').read())
    n = struct.unpack_from('<H', raw, 6)[0]
    if raw[4] == 1:
        if cpick(bytes(raw), raw[8], raw[9])[0] != BADBLOB:
            return False, 'the v1 blob must be refused'
        if raw[8] != 0:
            return True, f'SKIP: {os.path.basename(p)} is a v1 blob of world {raw[8]}: no country ids without the build'
        raw[4] = 2
        for i in range(n):
            raw[8 + 6 * i + 3] = raw[8 + 6 * i + 1]
    blob, world = bytes(raw), raw[8]
    if rparse(blob) is None:
        return False, f'{os.path.basename(p)}: the blob is refused'
    st = strength_of(blob, world)
    live = sorted((w for w in st if st[w][0]), key=lambda w: (st[w][0], w))
    names = {}
    for ln in open(p[:-4] + '.txt'):
        if ln.startswith('#'):
            cols = ln[1:].split() if 'ordinal' in ln else None
        else:
            f = ln.split(None, len(cols) - 1)
            names[word(int(f[cols.index('file')]), int(f[cols.index('ordinal')]))] = f[-1].strip() if len(f) == len(cols) else ''
    shared = [w for w in live if w & 0xFF != st[w][1]]              # clubs of a country's second file
    picks = [live[-1], live[0], live[len(live) // 2], live[len(live) // 4], live[-40]] + shared[:1] + shared[-1:] \
        + random.Random(96).sample(live, 40)
    shown = []
    for i, self_ in enumerate(picks):
        S, sc = st[self_]
        M = max(11, S // 10)
        for season in range(3):
            a = dict(blob=blob, world=world, self_=self_, season=1996 + season, seed=0x5EED + i)
            c = cpick(**a)
            rc, ws, home, fb, bands, why = c
            if c != ref(**a):
                return False, f'{names.get(self_)}: C {c} != reference {ref(**a)}'
            if rc or len(set(ws)) != 4 or any(why) or bin(home).count('1') != 2:
                return False, f'{names.get(self_)}: {c}'
            for k, w in enumerate(ws):
                s, cc = st[w]
                b = STRONGER if s - S > M else WEAKER if s - S < -M else SIMILAR
                if not s or cc == sc or w == self_ or bands[k] != b:
                    return False, f'{names.get(self_)}: slot {k} {names.get(w)} strength {s} country {cc} band {bands[k]}'
                if (b != [WEAKER, SIMILAR, SIMILAR, STRONGER][k]) != bool(fb >> k & 1):
                    return False, f'{names.get(self_)}: slot {k} band {b} fb {fb:#x}'
            if len({st[w][1] for w in ws}) != 4 and not fb:
                return False, f'{names.get(self_)}: countries {[st[w][1] for w in ws]}'
            if season == 0 and i < 2:
                shown.append(f'{names.get(self_)} ({S}): ' + ', '.join(f'{names.get(w)} {st[w][0]}' for w in ws)
                             + f' fb {fb:#x}')
    bot = cpick(blob, world, live[0])[3]
    if cpick(blob, world, live[-1])[3] & 7 or bot & 14:
        return False, f'top club fb {cpick(blob, world, live[-1])[3]:#x}, bottom club fb {bot:#x}'
    return True, f'world {world}: {len(picks)} clubs x 3 seasons of {len(live)} ({len(shared)} in a shared-country ' \
                 f'file); ' + '; '.join(shown)


def test_frpick_real_tables():
    """the committed tables of every world (tools/frdata/frstr_w*.bin), the 1996-97 one first"""
    import glob
    fs = sorted(glob.glob(os.path.join(TOOLS, 'frdata', 'frstr_w*.bin')))
    if not fs:
        return True, 'SKIP: no tools/frdata/frstr_w*.bin'
    msgs = []
    for p in fs:
        ok, m = _real(p)
        if not ok or m.startswith('SKIP'):
            return ok, m
        msgs.append(m)
    return True, ' | '.join(msgs)


def _exe_object():
    """frpick.c with cobj's exe flags at -Oz -> (sizes by section, {function: stack bytes} or None)"""
    sys.path.insert(0, TOOLS)
    import cobj
    flags = ['-Oz' if f == '-Os' else f for f in cobj.CFLAGS]
    assert '-Oz' in flags
    o = os.path.join(_TMP, 'frpick_exe.o')
    r = subprocess.run(['clang', *flags, '-fstack-usage', '-c', SRC, '-o', o], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    b = open(o, 'rb').read()
    assert b[:4] == b'\x7fELF' and b[4] == 1
    shoff = struct.unpack_from('<I', b, 0x20)[0]
    entsz, num, strndx = struct.unpack_from('<HHH', b, 0x2E)
    sh = [struct.unpack_from('<10I', b, shoff + i * entsz) for i in range(num)]
    sizes, relocs = {}, 0
    for s in sh:
        nm = b[sh[strndx][4] + s[0]:].split(b'\0')[0].decode()
        if nm.startswith(('.text', '.data', '.rodata', '.bss')) and not nm.startswith('.rel'):
            k = '.' + nm.split('.')[1]
            sizes[k] = sizes.get(k, 0) + s[5]
        if s[1] in (4, 9):                                  # SHT_RELA / SHT_REL
            relocs += s[5] // (s[9] or 8)
    su = None
    if os.path.isfile(o[:-2] + '.su'):
        su = {}
        for ln in open(o[:-2] + '.su'):
            m = re.match(r'.*:(\w+)\t(\d+)\t', ln)
            if m:
                su[m.group(1)] = int(m.group(2))
    return sizes, su, relocs, b


def test_frpick_exe_object():
    """Motore's conditions on the object linked in FRND: built with the exe flags (-Oz), no data, no undefined symbol
    (no libc, no exe address), stack < 256 B"""
    sizes, su, relocs, obj = _exe_object()
    text, data = sizes.get('.text', 0), sizes.get('.data', 0) + sizes.get('.bss', 0)
    ro = sizes.get('.rodata', 0)
    if data or relocs:
        return False, f'.data + .bss {data} B, {relocs} relocations: a global or an outside symbol'
    for sym in (b'memset', b'memcpy', b'__'):
        if sym in obj:
            return False, f'the object names {sym.decode()}'
    if text > 1800:                                         # (1667 B on 16/11: the figure given to Motore for FRND)
        return False, f'.text {text} B: over the 1800 B this test allows (tell Motore before raising it)'
    if su is None or 'fr_pick' not in su:
        return True, f'SKIP: no -fstack-usage output from this clang (.text {text} .data {data} .rodata {ro})'
    deep = su['fr_pick'] + max([v for k, v in su.items() if k != 'fr_pick'] or [0]) + 8      # + a callee's frame + call
    if deep >= 256:
        return False, f'stack {su}: {deep} B'
    return True, f'-Oz exe flags: .text {text} B, .data {data} B, .rodata {ro} B, 0 relocations; stack {su} (< 256)'
