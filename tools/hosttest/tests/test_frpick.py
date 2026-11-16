"""4.2 preseason friendlies, part (b): the opponent pick tools/frpick.c against tools/frpick.h's rules. Host only: the
C file built natively (clang -shared, ctypes) at -O0 / -O2 / -Oz, compared with ref() below - a Python reference of
the header's rules written from the header, not from the C (only the hash's constants are shared: the header leaves
the mix to the C file) - on random synthetic FRSS v2 tables (fr_pick with chosen clubs, FR_AUTO slots, FR_VENUES; fr_level),
plus the directed cases of every rule, the committed real
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
E_NOCLUB, E_SELF, E_BTEAM, E_DUP, E_HOME, E_ROOM, E_VENUE = -1, -2, -3, -4, -5, -6, -7
STRONGER, SIMILAR, WEAKER, FAR_UP, FAR_DOWN = 0, 1, 2, 3, 4
M32 = 0xFFFFFFFF
TWO = (3, 5, 6, 9, 10, 12)                 # the venue masks of 2 home + 2 away


def AUTO(band):
    return 0xF0FF | band << 8


def VENUES(mask):
    return 0x100 | mask


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
        subprocess.run(['clang', '-shared', opt, '-Wall', '-Werror', '-DFRPICK_TEST', '-o', so, SRC], check=True)
        l = ctypes.CDLL(so)
        l.fr_pick.restype = ctypes.c_int
        l.fr_pick.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(FrPick)]
        l.fr_given.restype = ctypes.c_int
        l.fr_given.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16,
                               ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8)]
        l.fr_level.restype = ctypes.c_uint32
        l.fr_level.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint16]
        l.fr_test_band.restype = ctypes.c_uint32            # (FRPICK_TEST only: the C's own band function)
        l.fr_test_band.argtypes = [ctypes.c_int32, ctypes.c_int32]
        _LIB[opt] = l
    return _LIB[opt]


def cpick(blob, world, self_, self2=NONE, given=None, avoid=(), room=None, cached=(), season=0, seed=0, nhome=2,
          opt='-O2', calls=None, navoid_null=7):
    """fr_pick -> (rc, words, home, fb, bands, why); room = None (no FrRoom) or the room count, cached = the words
    in the team cache; calls = a list that receives every cached() call's word"""
    out = FrPick()
    ctypes.memset(ctypes.byref(out), 0xA5, ctypes.sizeof(out))      # (the C must not rely on a zeroed *out)
    g = (ctypes.c_uint16 * 4)(*given) if given is not None else None
    a = (ctypes.c_uint16 * max(1, len(avoid)))(*avoid) if avoid is not None else None
    navoid = len(avoid) if avoid is not None else navoid_null
    r = None
    if room is not None:
        def cb(ctx, w):
            if calls is not None:
                calls.append(w)
            return 1 if w in cached else 0
        r = FrRoom(room, CACHED(cb), None)
    rc = lib(opt).fr_pick(blob, len(blob), world, self_, self2, g, a, navoid, ctypes.byref(r) if r else None,
                          season & M32, seed & M32, nhome, ctypes.byref(out))
    return rc, list(out.word), out.home, out.fb, list(out.band), list(out.why)


def cgiven(blob, world, self_, self2, given, k, room=None, cached=(), calls=None, opt='-O2'):
    """fr_given -> (code, band)"""
    g = (ctypes.c_uint16 * 4)(*given) if given is not None else None
    r = None
    if room is not None:
        def cb(ctx, w):
            if calls is not None:
                calls.append(w)
            return 1 if w in cached else 0
        r = FrRoom(room, CACHED(cb), None)
    band = ctypes.c_uint8(0x5A)
    rc = lib(opt).fr_given(blob, len(blob), world, self_, self2, g, k, ctypes.byref(r) if r else None, ctypes.byref(band))
    return rc, band.value


def given_vs_pick(a):
    """fr_given for every k against fr_pick on the same list (THE GIVEN CHECK): None, or what differs. a = cpick's
    arguments (the venues left at the default: FR_E_VENUE is fr_pick's only)"""
    a = {k: v for k, v in a.items() if k in ('blob', 'world', 'self_', 'self2', 'given', 'room', 'cached')}
    rc, ws, home, fb, bands, why = cpick(**a)
    g = a.get('given') or [NONE] * 4
    for k in range(4):
        calls = []
        e, band = cgiven(a['blob'], a['world'], a['self_'], a.get('self2', NONE), a.get('given'), k, a.get('room'),
                         a.get('cached', ()), calls)
        if rc in (BADBLOB, NOSELF):
            if (e, band) != (rc, 0xFF):
                return f'k {k}: fr_given {e} band {band}, fr_pick {rc}'
            continue
        if e != (why[k] if rc == GIVEN else 0):
            return f'k {k}: fr_given {e}, fr_pick {rc} why {why}'
        pin = pin_of(g[k])
        if g[k] == NONE and band != 0xFF or pin is not None and band != pin:
            return f'k {k}: band {band} for {g[k]:#x}'
        if rc == OK and g[k] != NONE and pin is None and band != bands[k]:
            return f'k {k}: band {band}, fr_pick band {bands[k]}'
        if e == E_NOCLUB and band != 0xFF or e in (E_SELF, E_BTEAM, E_DUP, E_ROOM) and band > 4:
            return f'k {k}: code {e} band {band}'
        if len(calls) > k + 1 or (a.get('room') is None and calls) or any(calls.count(w) > g[:k + 1].count(w) for w in calls):
            return f'k {k}: cached() calls {calls}'
    return None


# ---- the table ----
def mkblob(blocks, version=2):
    """blocks = [(world, file, country, [strength by ordinal])] in the given order"""
    idx, vals = b'', []
    for w, fl, c, st in blocks:
        assert 1 <= len(st) <= 256
        idx += struct.pack('<BBBBH', w, fl, len(st) & 0xFF, c, len(vals))
        vals += st
    return b'FRSS' + struct.pack('<BBH', version, 0, len(blocks)) + idx + struct.pack(f'<{len(vals)}H', *vals)


def word(fl, o):
    return fl | o << 8


# ---- the reference (frpick.h's rules) ----
def rband(d, M):
    if d < -4 * M:
        return FAR_DOWN
    if d < -M:
        return WEAKER
    if d <= M:
        return SIMILAR
    return STRONGER if d <= 4 * M else FAR_UP


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
        cnt = cnt or 256
        if first != end or fl == 0xFF:
            return None
        ent.append((w, fl, c, cnt, first))
        end += cnt
    if len(b) != 8 + 6 * n + 2 * end:
        return None
    return [(w, fl, c, list(struct.unpack_from(f'<{cnt}H', b, 8 + 6 * n + 2 * first))) for w, fl, c, cnt, first in ent]


def rtable(tab, world):
    """a parsed blob -> (the world's clubs [(word, strength, country)] in table order, {word: (strength, country)})"""
    clubs, info = [], {}                                # (a word resolves through the first entry of its file)
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
    return clubs, info


def rlevel(blob, world, w):
    """THE LEVEL: 1 + 5 * (clubs strictly weaker) / (clubs), 0 = no level"""
    tab = rparse(blob)
    if tab is None:
        return 0
    clubs, info = rtable(tab, world)
    if w not in info:
        return 0
    return min(5, 1 + 5 * sum(1 for _, s, _ in clubs if s < info[w][0]) // len(clubs))


def pin_of(g):
    """the pinned band of a given entry (FR_AUTO), None for anything else"""
    return (g >> 8) - 0xF0 if g & 0xFF == 0xFF and 0xF0 <= g >> 8 <= 0xF2 else None


def ref(blob, world, self_, self2=NONE, given=None, avoid=(), room=None, cached=(), season=0, seed=0, nhome=2):
    """the header's rules -> (rc, words, home, fb, bands, why); words .. bands None when rc < 0"""
    why = [0] * 4
    tab = rparse(blob)
    if tab is None:
        return BADBLOB, None, None, None, None, why
    clubs, info = rtable(tab, world)
    if self_ not in info:
        return NOSELF, None, None, None, None, why
    S, home_c = info[self_]
    M = max(11, S // 10)

    def band(s):
        return rband(s - S, M)

    avoid = avoid or ()

    given = list(given) if given is not None else [NONE] * 4
    left = room
    four = [None] * 4                                   # (word, strength, country)
    want = [None] * 4                                   # the wanted band of an automatic slot
    chosen = []
    for k, g in enumerate(given):
        if g == NONE:
            continue
        if pin_of(g) is not None:
            want[k] = pin_of(g)
            continue
        if g not in info:
            why[k] = E_NOCLUB
        elif g == self_:
            why[k] = E_SELF
        elif g == self2:
            why[k] = E_BTEAM
        elif g in chosen:
            why[k] = E_DUP
        elif room is not None and g not in cached and left == 0:
            why[k] = E_ROOM
        else:
            if room is not None and g not in cached:
                left -= 1
            four[k] = (g,) + info[g]
        chosen.append(g)
    if any(why):
        return GIVEN, None, None, None, None, why
    if nhome >= 0x100 and bin(nhome & 0xF).count('1') != 2:
        return GIVEN, None, None, None, None, [E_VENUE] * 4
    mix = [SIMILAR, SIMILAR, WEAKER, STRONGER]          # the order the uncovered bands are taken in
    for b in [band(f[1]) for f in four if f] + [w for w in want if w is not None]:
        if b in mix:
            mix.remove(b)
    empty = [k for k in range(4) if four[k] is None and want[k] is None]
    assert len(mix) >= len(empty)                       # (so "everything covered -> similar" never arises)
    for k, b in zip(empty, sorted(mix[:len(empty)], key=lambda b: -b)):     # weakest first: weaker 2 .. stronger 0
        want[k] = b
    auto = [k for k in range(4) if four[k] is None]
    wanted = [want[k] for k in auto]
    fb = 0
    for k, want in zip(auto, wanted):
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
                dist = M + 1 - d if d <= M else d - 4 * M
            elif want == WEAKER:
                dist = d + M + 1 if d >= -M else -4 * M - d
            else:
                dist = abs(d) - M
            assert dist > 0 or band(s) == want
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
    home = nhome & 0xF if nhome >= 0x100 else sum(1 << k for k in order[:min(nhome, 4)])
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
        cnt = rng.choice([1, 1, 2, 3, 5, 8, 20, 40]) if rng.random() < .9 else rng.choice([255, 256])
        st = [0 if rng.random() < .08 else base + rng.randint(0, spread) for _ in range(cnt)]
        blocks.append((world if rng.random() < .85 else (world + 1) & 3, fl, rng.randint(0, nc - 1), st))
    if rng.random() < .15:                                  # the same file in another world too
        w, fl, c, st = rng.choice(blocks)
        blocks.append(((w + 2) & 3, fl, rng.randint(0, nc - 1), [rng.randint(5, 500) for _ in range(rng.randint(1, 9))]))
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
    elif r < .55:                                           # pinned slots, chosen clubs (of any country), junk FF words
        given = [rng.choice([NONE, AUTO(0), AUTO(1), AUTO(2), AUTO(rng.randint(0, 2)), club(),
                             rng.choice(live) if live else NONE,
                             rng.choice([0xF3FF, 0xEFFF, 0x00FF, 0xFEFF, 0x12FF]) if rng.random() < .15 else NONE])
                 for _ in range(4)]
    avoid = [club() for _ in range(rng.choice([0, 0, 2, 4, 4, 6]))] if rng.random() < .93 else None
    room, cached = None, set()
    if rng.random() < .5:
        room = rng.choice([0, 0, 1, 2, 3, 4, 9])
        cached = {w for w in live if rng.random() < rng.choice([0, .05, .3, .9])}
    return dict(blob=mkblob(blocks), world=world, self_=self_, self2=self2, given=given, avoid=avoid, room=room,
                cached=cached, season=rng.choice([0, 1, 7, 1996, rng.getrandbits(32)]), seed=rng.getrandbits(32),
                nhome=rng.choice([rng.randint(0, 5), 2, 2, VENUES(rng.choice(TWO)), VENUES(rng.choice(TWO)),
                                  VENUES(rng.randint(0, 15)), 0x7700 | rng.choice(TWO), rng.randint(6, 0xFF)]))


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
        auto = sum(1 for x in g if x == NONE or pin_of(x) is not None)
        for w in [a['self_'], a['self2']] + g + [rng.randint(0, 0xFFFF)]:
            lv = lib().fr_level(a['blob'], len(a['blob']), a['world'], w)
            if lv != rlevel(a['blob'], a['world'], w) or lv > 5:
                return False, f'case {i}: fr_level({w:#x}) = {lv}, reference {rlevel(a["blob"], a["world"], w)}'
        for w in set(calls):
            if calls.count(w) > auto + g.count(w):
                return False, f'case {i}: cached({w:#x}) called {calls.count(w)} times, {auto} automatic slots'
        d = given_vs_pick(a)
        if d:
            return False, f'case {i}: fr_given: {d} ({ {k: v for k, v in a.items() if k != "blob"} })'
        codes[r[0]] = codes.get(r[0], 0) + 1
    if min(codes.get(k, 0) for k in (OK, NOSELF, NOPOOL, GIVEN)) < 10:
        return False, f'the random cases do not reach every code: {codes}'
    return True, f'{CASES} random tables: fr_pick == reference, fr_level == reference, fr_given == fr_pick for every k; ' \
                 f'codes {dict(sorted(codes.items()))}'


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
def near(s):
    """a fixture strength written for self = 200 (M 20) brought inside the bounded bands: below 180 -> 121..179
    (weaker), above 220 -> 221..280 (stronger), order kept"""
    return 121 + (s - 90) * 58 // 89 if 0 < s < 180 else 221 + (s - 221) * 59 // 279 if s > 220 else s


def league(strengths, files=None, countries=None, world=0, fit=False):
    """one block per list of strengths: file 10 + i, country = i unless given; fit: near() on every strength"""
    if fit:
        strengths = [[near(x) for x in st] for st in strengths]
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
    up = league([[100], [130, 131], [132, 133], [134, 140]])
    rc, ws, home, fb, bands, why = cpick(up, 0, SELF)
    if rc or fb != 7 or bands != [STRONGER] * 4 or ws[0] != word(11, 0) or ws[1] != word(11, 1) or ws[2] != word(12, 0):
        return False, f'all stronger: {rc} {ws} fb {fb:#x} bands {bands}'
    return True, 'top club: strongest left; bottom club: weakest left; empty similar band; fb only on an empty band'


def test_frpick_bounded_bands():
    # self 200, M 20: weaker 120..179, stronger 221..280; 119 = far down, 281 = far up
    edge = league([[200], [120], [119], [280], [281], [200], [201]])
    for seed in range(100):
        rc, ws, home, fb, bands, why = cpick(edge, 0, SELF, seed=seed)
        if rc or fb or ws[0] != word(11, 0) or ws[3] != word(13, 0) or bands != [WEAKER, SIMILAR, SIMILAR, STRONGER]:
            return False, f'-4M / 4M exactly, seed {seed}: {rc} {ws} fb {fb:#x} bands {bands}'
    # only the far clubs outside the similar band: taken by the nearest-band rule, band 3 / 4 with fb
    far = league([[200], [119], [281], [200], [201]])
    rc, ws, home, fb, bands, why = cpick(far, 0, SELF)
    if rc or fb != 9 or ws[0] != word(11, 0) or ws[3] != word(12, 0) or bands != [FAR_DOWN, SIMILAR, SIMILAR, FAR_UP]:
        return False, f'far clubs by fallback: {rc} {ws} fb {fb:#x} bands {bands}'
    # the fallback distance on both sides of the wanted band: weaker wanted, 100 (20 below the band: -4M - d) against
    # 190 (11 above it: d + M + 1) -> 190; stronger wanted, 305 (d - 4M = 25) against the similar clubs left (M + 1 - d:
    # 10 for 211, 20 / 21 for 201 / 200) -> the strongest similar club left
    two = league([[200], [100], [190], [305], [211], [200, 201]])
    rc, ws, home, fb, bands, why = cpick(two, 0, SELF)
    st = strength_of(two)                   # (211 may be in a similar slot already: then the strongest similar left)
    left = max(st[w][0] for w in (word(14, 0), word(15, 0), word(15, 1)) if w not in ws[1:3])
    if rc or fb != 9 or ws[0] != word(12, 0) or st[ws[3]][0] != left or bands != [SIMILAR] * 4:
        return False, f'both sides: {rc} {ws} fb {fb:#x} bands {bands}'
    two = league([[200], [118], [190, 189], [283], [211, 212], [200, 201]])       # ... and the far side when nearer (2 / 3)
    rc, ws, home, fb, bands, why = cpick(two, 0, SELF)
    if rc or fb != 9 or ws[0] != word(11, 0) or ws[3] != word(13, 0) or bands != [FAR_DOWN, SIMILAR, SIMILAR, FAR_UP]:
        return False, f'the far side nearer: {rc} {ws} fb {fb:#x} bands {bands}'
    # the far clubs are never taken while the wanted band has a club (many far ones, one club per band slot)
    crowd = league([[200], [5, 50, 100, 119, 150], [300, 400, 9000, 281, 250], [200, 60000, 10], [199, 1000, 30]])
    for seed in range(300):
        rc, ws, home, fb, bands, why = cpick(crowd, 0, SELF, seed=seed)
        if rc or fb or ws != [word(11, 4), ws[1], ws[2], word(12, 4)] or max(bands) > 2:
            return False, f'far clubs picked, seed {seed}: {rc} {ws} fb {fb:#x} bands {bands}'
    # S small enough that S - 4M < 0 (S 20, M 11: nothing can be far down; weaker 0 < s < 9, stronger 32..64)
    small = league([[20], [5, 8, 1], [9, 31], [32, 64], [65, 1000], [20]])
    st = strength_of(small)
    for seed in range(100):
        rc, ws, home, fb, bands, why = cpick(small, 0, SELF, seed=seed)
        s = [st[w][0] for w in ws]
        if rc or fb or s[0] not in (5, 8, 1) or s[3] not in (32, 64) or bands != [WEAKER, SIMILAR, SIMILAR, STRONGER]:
            return False, f'small S, seed {seed}: {rc} strengths {s} fb {fb:#x} bands {bands}'
    small = league([[20], [9], [31, 25], [65], [20], [66]])                       # no weaker / stronger: 9 (dist 1), 65 (dist 1)
    rc, ws, home, fb, bands, why = cpick(small, 0, SELF)
    if rc or fb != 9 or ws[0] != word(11, 0) or ws[3] != word(13, 0) or bands != [SIMILAR, SIMILAR, SIMILAR, FAR_UP]:
        return False, f'small S fallback: {rc} {ws} fb {fb:#x} bands {bands}'
    # the top of the scale: uint16 strengths, no wrap (S 65535, M 6553)
    big = league([[65535], [39323, 39322], [58982, 58981], [65000, 65535], [1, 60000]])
    rc, ws, home, fb, bands, why = cpick(big, 0, SELF)
    if rc or fb != 8 or ws[0] not in (word(11, 0), word(12, 1)) or bands != [WEAKER, SIMILAR, SIMILAR, SIMILAR]:
        return False, f'S 65535: {rc} {ws} fb {fb:#x} bands {bands}'
    return True, 'edges -4M / -M / M / 4M; far clubs only by the nearest-band rule (band 3 / 4, fb); S - 4M < 0; S 65535'


def test_frpick_block256():
    """the count byte 0 = 256 clubs: ordinal 255 picked, accepted as a given club and as self; lengths"""
    big = [0] * 255 + [250]
    b = mkblob([(0, 10, 0, [200]), (0, 20, 1, big), (0, 21, 2, [150, 200]), (0, 22, 3, [201, 160]),
                (0, 23, 0, [0] * 200 + [230] + [0] * 55)])
    if b[8 + 6 + 2] != 0 or rparse(b) is None:
        return False, 'the fixture has no count byte 0'
    last = word(20, 255)
    for seed in range(50):
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, seed=seed)
        if rc or fb or ws[3] != last or bands[3] != STRONGER:
            return False, f'ordinal 255 not picked, seed {seed}: {rc} {ws} fb {fb:#x}'
    rc, ws, home, fb, bands, why = cpick(b, 0, SELF, given=[last, NONE, NONE, NONE])
    if rc or ws[0] != last or bands != [STRONGER, WEAKER, SIMILAR, SIMILAR]:
        return False, f'ordinal 255 given: {rc} {ws} {bands} {why}'
    rc, ws, home, fb, bands, why = cpick(b, 0, last)                 # self 250, M 25: 200 / 201 weaker, 230 similar
    if rc or word(23, 200) not in ws[1:3] or bands[0] != WEAKER:
        return False, f'ordinal 255 as self: {rc} {ws} {bands}'
    if cpick(b, 0, word(20, 254))[0] != NOSELF:                      # (strength 0)
        return False, 'ordinal 254 (strength 0) as self'
    # a 255-club block: ordinal 255 is past the count
    b255 = mkblob([(0, 10, 0, [200]), (0, 20, 1, big[1:]), (0, 21, 2, [150, 200]), (0, 22, 3, [201, 160])])
    if cpick(b255, 0, last)[0] != NOSELF or cpick(b255, 0, SELF, given=[last, NONE, NONE, NONE])[5][0] != E_NOCLUB:
        return False, 'ordinal 255 of a 255-club block must not exist'
    if cpick(b255, 0, SELF)[1][3] != word(20, 254):
        return False, 'ordinal 254 of a 255-club block'
    # the length and the contiguity count 256 for 0
    n = len(b)
    for name, bad in (('2 B short', b[:-2]), ('512 B short (count 0 read as 0)', b[:n - 512]),
                      ('next first = previous first + 0', b[:8 + 12 + 4] + struct.pack('<H', 1) + b[8 + 18:])):
        if cpick(bad, 0, SELF)[0] != BADBLOB:
            return False, f'FR_BADBLOB ({name})'
    # 256 blocks of 256 clubs: the sum does not fit the 16-bit first index -> refused, not wrapped
    huge = b'FRSS' + struct.pack('<BBH', 2, 0, 257) + b''.join(struct.pack('<BBBBH', 0, i & 0xFF, 0, i & 0xFF, (i * 256) & 0xFFFF)
                                                              for i in range(257))
    huge += struct.pack('<H', 200) * (257 * 256)
    if cpick(huge, 0, 0)[0] != BADBLOB:
        return False, 'a table past 65535 clubs must be refused'
    return True, 'count 0 = 256: ordinal 255 picked / given / self; a 255-club block ends at 254; lengths'


def test_frpick_avoid_null():
    b = league([[200], [100, 190, 300, 110, 195, 310], [120, 200, 320, 125, 201, 330], [130, 205, 340, 135],
                [140, 210, 350, 145, 199], [150, 191, 360]], fit=True)
    for seed in range(100):
        a = cpick(b, 0, SELF, seed=seed, avoid=[])
        for n in (0, 4, 7, 0xFFFFFFFF):
            if cpick(b, 0, SELF, seed=seed, avoid=None, navoid_null=n) != a:
                return False, f'avoid NULL with navoid {n} differs from navoid 0 (seed {seed})'
    return True, 'avoid == NULL = navoid 0, whatever navoid says'


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
                [140, 210, 350, 145, 199], [150, 191, 360]], fit=True)
    st = strength_of(b)
    for seed in range(300):
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, seed=seed)
        if rc or fb or len({st[w][1] for w in ws}) != 4:
            return False, f'seed {seed}: countries {[st[w][1] for w in ws]}'
    # ... but never at the cost of the band: the only similar clubs are in one country
    b2 = league([[200], [100, 300], [200, 201, 202], [110, 310]], fit=True)
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
    b3 = league([[200], [100, 201], [202], [300]], fit=True)
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
                [140, 210, 350, 145, 199], [150, 191, 360]], fit=True)
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
    b = mkblob([(w, fl, c, [near(x) for x in st]) for w, fl, c, st in
                [(0, 10, 0, [200, 199]), (0, 11, 1, [100, 190, 300, 0]), (0, 12, 2, [120, 200, 320]),
                 (0, 13, 3, [130, 205, 340]), (0, 14, 0, [150, 210]), (0, 15, 4, [90, 180, 400, 215]),
                 (0, 17, 6, [1000, 20]), (1, 16, 5, [200, 200])]])
    self2 = word(14, 1)                                         # a B team abroad by file, same country here
    X = NONE
    cases = [                                                   # (given, expected why)
        ([word(16, 0), X, X, X], [E_NOCLUB, 0, 0, 0]),          # another world's file
        ([word(99, 0), X, X, X], [E_NOCLUB, 0, 0, 0]),          # no such file
        ([X, word(11, 4), X, X], [0, E_NOCLUB, 0, 0]),          # ordinal >= count
        ([X, X, word(11, 3), X], [0, 0, E_NOCLUB, 0]),          # strength 0
        ([X, X, X, SELF], [0, 0, 0, E_SELF]),
        ([self2, X, X, X], [E_BTEAM, 0, 0, 0]),                 # (self2 is of self's country: still refused)
        ([word(12, 0), word(12, 0), X, X], [0, E_DUP, 0, 0]),
        ([word(10, 1), X, word(10, 1), X], [0, 0, E_DUP, 0]),           # a club of self's country: accepted, DUP
        ([SELF, SELF, X, X], [E_SELF, E_SELF, 0, 0]),           # SELF before DUP
        ([word(0xFF, 0xF3), X, X, X], [E_NOCLUB, 0, 0, 0]),             # file 255, not FR_AUTO / FR_NONE
        ([X, word(0xFF, 0), word(0xFF, 0xEF), word(0xFF, 0xFE)], [0, E_NOCLUB, E_NOCLUB, E_NOCLUB]),
        ([AUTO(0), AUTO(0), word(99, 0), AUTO(0)], [0, 0, E_NOCLUB, 0]),        # pinned slots are never refused / DUP
        ([word(99, 9), SELF, self2, word(12, 5)], [E_NOCLUB, E_SELF, E_BTEAM, E_NOCLUB]),   # all reported together
        ([word(12, 0), word(99, 9), word(12, 0), word(99, 9)], [0, E_NOCLUB, E_DUP, E_NOCLUB]),
    ]
    for g, want in cases:
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=g)
        if rc != GIVEN or why != want:
            return False, f'given {g}: {rc} why {why}, expected {want}'
    # FR_E_ROOM is the last check
    rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=[word(12, 0), self2, X, word(12, 0)], room=0)
    if rc != GIVEN or why != [E_ROOM, E_BTEAM, 0, E_DUP]:
        return False, f'room last: {rc} {why}'
    # FR_E_HOME is never set any more: clubs of self's country (both its files) are accepted, in their bands
    for seed in range(30):
        g = [word(10, 1), word(14, 0), X, X]
        rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=g, seed=seed)
        if rc or any(why) or ws[:2] != g[:2] or bands != [SIMILAR, WEAKER, SIMILAR, STRONGER] or fb:
            return False, f'chosen clubs of self\'s country: {rc} {ws} {bands} why {why}'
        if any(w & 0xFF in (10, 14) for w in ws[2:]):
            return False, f'an automatic slot took a club of self\'s country: {ws}'
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
        # a given club in a far band covers no band: its slot only is lost to the mix (the last uncovered one drops)
        ([X, X, X, word(17, 0)], [WEAKER, SIMILAR, SIMILAR, FAR_UP]),
        ([word(17, 1), X, X, X], [FAR_DOWN, WEAKER, SIMILAR, SIMILAR]),
        ([word(17, 1), word(17, 0), X, X], [FAR_DOWN, FAR_UP, SIMILAR, SIMILAR]),
        ([word(17, 0), SI, SI2, X], [FAR_UP, SIMILAR, SIMILAR, WEAKER]),
        ([word(17, 0), SI, W, X], [FAR_UP, SIMILAR, WEAKER, SIMILAR]),
        ([word(17, 0), ST, X, X], [FAR_UP, STRONGER, SIMILAR, SIMILAR]),
    ]
    for g, want in table:
        for seed in range(20):
            rc, ws, home, fb, bands, why = cpick(b, 0, SELF, self2=self2, given=g, seed=seed, avoid=[x for x in g if x != X])
            if rc or fb or bands != want or any(why) or any(x != X and ws[k] != x for k, x in enumerate(g)) \
                    or len(set(ws)) != 4:
                return False, f'given {g} seed {seed}: {rc} {ws} bands {bands} (expected {want}) fb {fb}'
    return True, f'{len(cases)} refusal lists (order NOCLUB, SELF, BTEAM, DUP, ROOM; no HOME), {len(table)} given mixes'


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
    if cpick(one, 0, SELF)[0] != NOPOOL or cpick(one, 0, SELF, given=[SELF, NONE, NONE, NONE])[0] != GIVEN:
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
                b = rband(s - S, M)
                if not s or cc == sc or w == self_ or bands[k] != b:
                    return False, f'{names.get(self_)}: slot {k} {names.get(w)} strength {s} country {cc} band {bands[k]}'
                if (b != [WEAKER, SIMILAR, SIMILAR, STRONGER][k]) != bool(fb >> k & 1):
                    return False, f'{names.get(self_)}: slot {k} band {b} fb {fb:#x}'
            if len({st[w][1] for w in ws}) != 4 and not fb:
                return False, f'{names.get(self_)}: countries {[st[w][1] for w in ws]}'
            if season == 0 and i < 2:
                shown.append(f'{names.get(self_)} ({S}): ' + ', '.join(f'{names.get(w)} {st[w][0]}' for w in ws)
                             + f' fb {fb:#x}')
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


class Exe386:
    """the exe-flag object's .text run in Unicorn (it has no relocation): fr_pick / fr_given / fr_level called cdecl,
    the lowest stack byte written = the real stack use (frames + pushed arguments + return addresses, the entry's
    return address included; the cached() stub's own frame is not ours)"""
    TEXT, BLOB, DATA, STUB, TOP = 0x100000, 0x200000, 0x300000, 0x400000, 0x600000

    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
        from unicorn import x86_const as X
        self.X = X
        sizes, su, relocs, b = _exe_object()
        assert not relocs
        shoff = struct.unpack_from('<I', b, 0x20)[0]
        entsz, num, strndx = struct.unpack_from('<HHH', b, 0x2E)
        sh = [struct.unpack_from('<10I', b, shoff + i * entsz) for i in range(num)]
        names = [b[sh[strndx][4] + s[0]:].split(b'\0')[0].decode() for s in sh]
        ti = names.index('.text')
        sym = sh[names.index('.symtab')]
        self.sym = {}
        for i in range(sym[5] // 16):
            nm, val, sz, info, oth, shndx = struct.unpack_from('<IIIBBH', b, sym[4] + 16 * i)
            if shndx == ti:
                self.sym[b[sh[sym[6]][4] + nm:].split(b'\0')[0].decode()] = val
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(0x100000, 0x500000)
        uc.mem_write(self.TEXT, b[sh[ti][4]:sh[ti][4] + sh[ti][5]])
        uc.mem_write(self.STUB, b'\x31\xc0\xc3' + b'\x90' * 13 + b'\x31\xc0\x40\xc3' + b'\x90' * 12 + b'\xf4')
        self.low = self.TOP
        uc.hook_add(UC_HOOK_MEM_WRITE, self._w, begin=0x500000, end=self.TOP)

    def _w(self, uc, access, addr, size, value, data):
        self.low = min(self.low, addr)

    def call(self, name, *args):
        """-> (eax, stack bytes used)"""
        X, uc = self.X, self.uc
        esp = self.TOP - 0x100
        uc.mem_write(esp, struct.pack(f'<{len(args) + 1}I', self.STUB + 0x20, *[a & M32 for a in args]))
        uc.reg_write(X.UC_X86_REG_ESP, esp)
        self.low = esp
        uc.emu_start(self.TEXT + self.sym[name], self.STUB + 0x20, count=20000000)
        assert uc.reg_read(X.UC_X86_REG_EIP) == self.STUB + 0x20
        return uc.reg_read(X.UC_X86_REG_EAX), esp + 4 - self.low

    def pick(self, blob, world, self_, self2=NONE, given=None, avoid=(), room=None, all_cached=False, season=0, seed=0,
             nhome=2, **_):
        uc, D = self.uc, self.DATA
        uc.mem_write(self.BLOB, blob)
        uc.mem_write(D, struct.pack('<4H', *(given or [0] * 4)) + struct.pack(f'<{len(avoid or ()) + 1}H', 0, *(avoid or ())))
        uc.mem_write(D + 0x100, struct.pack('<3I', room or 0, self.STUB + (0x10 if all_cached else 0), 0))
        uc.mem_write(D + 0x200, b'\xA5' * 18)
        rc, used = self.call('fr_pick', self.BLOB, len(blob), world, self_, self2, D if given is not None else 0,
                             D + 10 if avoid is not None else 0, len(avoid or ()), D + 0x100 if room is not None else 0,
                             season, seed, nhome, D + 0x200)
        o = bytes(uc.mem_read(D + 0x200, 18))
        w = list(struct.unpack_from('<4H', o))
        return (rc - (1 << 32 if rc >> 31 else 0), w, o[8], o[9], list(o[10:14]),
                list(struct.unpack_from('<4b', o, 14))), used

    def given(self, blob, world, self_, self2, given, k, room=None, all_cached=False):
        uc, D = self.uc, self.DATA
        uc.mem_write(self.BLOB, blob)
        uc.mem_write(D, struct.pack('<4H', *(given or [0] * 4)))
        uc.mem_write(D + 0x100, struct.pack('<3I', room or 0, self.STUB + (0x10 if all_cached else 0), 0))
        uc.mem_write(D + 0x200, b'\x5A')
        rc, used = self.call('fr_given', self.BLOB, len(blob), world, self_, self2, D if given is not None else 0, k,
                             D + 0x100 if room is not None else 0, D + 0x200)
        return (rc - (1 << 32 if rc >> 31 else 0), uc.mem_read(D + 0x200, 1)[0]), used

    def level(self, blob, world, w):
        self.uc.mem_write(self.BLOB, blob)
        return self.call('fr_level', self.BLOB, len(blob), world, w)


def test_frpick_exe_run():
    """the object built with the exe flags (i486, -Oz) EXECUTED in Unicorn: the same results as the native build, and
    the stack it really uses < 256 B (Motore's condition), on random tables and on the committed world tables"""
    try:
        exe = Exe386()
    except ImportError as e:
        return True, f'SKIP: no Unicorn ({e})'
    rng = random.Random(0x386)
    worst = {'fr_pick': 0, 'fr_given': 0, 'fr_level': 0}
    cases = [rand_case(rng) for _ in range(max(200, CASES // 5))]
    import glob
    for p in sorted(glob.glob(os.path.join(TOOLS, 'frdata', 'frstr_w*.bin'))):
        blob = open(p, 'rb').read()
        tab = rparse(blob)
        if tab is None:
            continue
        live = sorted(rtable(tab, tab[0][0])[1])
        for i in range(6):
            g = [rng.choice([NONE, NONE, AUTO(rng.randint(0, 2)), rng.choice(live)]) for _ in range(4)]
            cases.append(dict(blob=blob, world=tab[0][0], self_=rng.choice(live), self2=NONE, given=g if i % 3 else None,
                              avoid=rng.sample(live, 4), room=rng.choice([None, 0, 2, 4]), cached=(), seed=i, season=i, nhome=2))
    for i, a in enumerate(cases):
        allc = bool(i & 1)
        live = {word(fl, o) for w, fl, c, st in (rparse(a['blob']) or []) for o in range(len(st))}
        a = dict(a, cached=live | set(range(0x10000)) if allc else set())
        r, used = exe.pick(all_cached=allc, **a)
        n = cpick(**a)
        if not (r == n if n[0] == OK else (r[0], r[5]) == (n[0], n[5])):
            return False, f'case {i}: the i486 object {r} != the native build {n}'
        worst['fr_pick'] = max(worst['fr_pick'], used)
        for k in range(4):
            r, used = exe.given(a['blob'], a['world'], a['self_'], a['self2'], a['given'], k, a['room'], allc)
            n = cgiven(a['blob'], a['world'], a['self_'], a['self2'], a['given'], k, a['room'], a['cached'])
            if r != n:
                return False, f'case {i}: fr_given({k}) i486 {r} != native {n}'
            worst['fr_given'] = max(worst['fr_given'], used)
        for w in (a['self_'], rng.randint(0, 0xFFFF)):
            r, used = exe.level(a['blob'], a['world'], w)
            if r != lib().fr_level(a['blob'], len(a['blob']), a['world'], w):
                return False, f'case {i}: fr_level({w:#x}) i486 {r} != native'
            worst['fr_level'] = max(worst['fr_level'], used)
    if max(worst.values()) >= 256:
        return False, f'stack used {worst}: 256 B or more'
    return True, f'{len(cases)} cases: i486 -Oz object == native build; stack really used (return address in) {worst} < 256'


def test_frpick_exe_object():
    """Motore's conditions on the object linked in FRND: built with the exe flags (-Oz), no data, no undefined symbol
    (no libc, no exe address), stack < 256 B"""
    sizes, su, relocs, obj = _exe_object()
    text, data = sizes.get('.text', 0), sizes.get('.data', 0) + sizes.get('.bss', 0)
    ro = sizes.get('.rodata', 0)
    if data or relocs:
        return False, f'.data + .bss {data} B, {relocs} relocations: a global or an outside symbol'
    for sym in (b'memset', b'memcpy', b'__', b'fr_test'):
        if sym in obj:
            return False, f'the object names {sym.decode()}'
    if text > 2400:                                         # (2306 B on 16/11 with fr_given / fr_level / FR_AUTO)
        return False, f'.text {text} B: over the 2400 B this test allows (tell Motore before raising it)'
    if su is None or 'fr_pick' not in su:
        return True, f'SKIP: no -fstack-usage output from this clang (.text {text} .data {data} .rodata {ro})'
    # (frames only: pushed arguments and return addresses are not in -fstack-usage; the stack really used is measured
    #  by test_frpick_exe_run, which runs this object)
    deep = su['fr_pick'] + su.get('fr_auto', 0) + 24
    if deep >= 256:
        return False, f'stack {su}: fr_pick + fr_auto + a call = {deep} B'
    return True, f'-Oz exe flags: .text {text} B, .data {data} B, .rodata {ro} B, 0 relocations; frames {su}'


def test_frpick_pinned():
    """FR_AUTO(band): an automatic slot with its band fixed; it covers the band like a chosen club; over-pinned lists"""
    b = league([[200, 199], [100, 190, 300, 110, 195, 310], [120, 200, 320, 125, 201, 330], [130, 205, 340, 135],
                [140, 210, 350, 145, 199], [150, 191, 360], [1000, 20], [150, 210, 260]], fit=True,
               countries=[0, 1, 2, 3, 4, 5, 6, 0])
    st = strength_of(b)
    if (AUTO(STRONGER), AUTO(SIMILAR), AUTO(WEAKER)) != (0xF0FF, 0xF1FF, 0xF2FF):
        return False, 'FR_AUTO values'
    X, H, MED, E = NONE, AUTO(STRONGER), AUTO(SIMILAR), AUTO(WEAKER)
    W, SI, ST, FAR = word(11, 0), word(12, 1), word(12, 2), word(16, 0)
    table = [                                                   # (given, the four's bands)
        ([H, X, X, X], [STRONGER, WEAKER, SIMILAR, SIMILAR]),
        ([X, X, X, E], [SIMILAR, SIMILAR, STRONGER, WEAKER]),
        ([X, MED, X, X], [WEAKER, SIMILAR, SIMILAR, STRONGER]),
        ([E, MED, MED, H], [WEAKER, SIMILAR, SIMILAR, STRONGER]),
        ([H, MED, MED, E], [STRONGER, SIMILAR, SIMILAR, WEAKER]),
        ([H, E, X, X], [STRONGER, WEAKER, SIMILAR, SIMILAR]),
        ([X, H, X, ST], [SIMILAR, STRONGER, SIMILAR, STRONGER]),        # chosen stronger + pinned hard: 2 covered once
        ([SI, MED, X, X], [SIMILAR, SIMILAR, WEAKER, STRONGER]),
        ([W, E, X, X], [WEAKER, WEAKER, SIMILAR, SIMILAR]),
        ([FAR, H, X, X], [FAR_UP, STRONGER, SIMILAR, SIMILAR]),
        # over-pinned
        ([H, H, H, X], [STRONGER, STRONGER, STRONGER, SIMILAR]),
        ([H, H, H, H], [STRONGER] * 4),
        ([E, E, E, E], [WEAKER] * 4),
        ([MED, MED, MED, MED], [SIMILAR] * 4),
        ([MED, MED, MED, X], [SIMILAR, SIMILAR, SIMILAR, WEAKER]),
        ([E, E, X, E], [WEAKER, WEAKER, SIMILAR, WEAKER]),
        ([ST, word(13, 2), H, X], [STRONGER, STRONGER, STRONGER, SIMILAR]),     # 2 chosen stronger + a pinned hard
        ([ST, word(13, 2), H, E], [STRONGER, STRONGER, STRONGER, WEAKER]),
        ([H, H, X, X], [STRONGER, STRONGER, SIMILAR, SIMILAR]),
        ([E, E, H, X], [WEAKER, WEAKER, STRONGER, SIMILAR]),
        ([X, H, E, H], [SIMILAR, STRONGER, WEAKER, STRONGER]),
    ]
    for g, want in table:
        for seed in range(15):
            a = dict(blob=b, world=0, self_=SELF, given=g, seed=seed)
            c = cpick(**a)
            rc, ws, home, fb, bands, why = c
            if rc or fb or bands != want or any(why) or len(set(ws)) != 4 or c != ref(**a):
                return False, f'given {[hex(x) for x in g]} seed {seed}: {rc} {ws} bands {bands} (expected {want}) fb {fb}'
            for k, x in enumerate(g):
                if pin_of(x) is None and x != X and ws[k] != x:
                    return False, f'a chosen club moved: {ws}'
                if (pin_of(x) is not None or x == X) and st[ws[k]][1] == 0:
                    return False, f'slot {k} (automatic) took a club of self\'s country: {ws}'
    # a pinned slot follows the automatic rules: nearest band with fb, avoid, room
    thin = league([[200], [150, 199], [201, 202], [203, 204], [205, 206]])          # one weaker club, no stronger one
    rc, ws, home, fb, bands, why = cpick(thin, 0, SELF, given=[H, H, E, E])
    if rc or fb != 0b1011 or bands != [SIMILAR, SIMILAR, WEAKER, SIMILAR] or ws[2] != word(11, 0) \
            or ws[0] != word(14, 1) or ws[1] != word(14, 0) or ws[3] != word(11, 1):
        return False, f'pinned + nearest band: {rc} {ws} fb {fb:#b} bands {bands}'
    last = cpick(b, 0, SELF, given=[H, MED, MED, E], seed=4)[1]
    rc, ws, *_ = cpick(b, 0, SELF, given=[H, MED, MED, E], seed=4, avoid=last)
    if rc or set(ws) & set(last):
        return False, f'pinned slots ignore avoid: {ws} after {last}'
    calls = []
    cached = {word(12, 2), word(13, 1), word(14, 1), word(11, 0)}
    rc, ws, *_ = cpick(b, 0, SELF, given=[H, MED, MED, E], room=0, cached=cached, calls=calls)
    if rc or set(ws) != cached:
        return False, f'pinned slots and the room: {rc} {ws}'
    if cpick(b, 0, SELF, given=[H, MED, MED, E], room=0, cached=set())[0] != NOPOOL:
        return False, 'pinned slots without room must be FR_NOPOOL'
    return True, f'{len(table)} lists with FR_AUTO (11 over-pinned): bands, foreign only, fallback, avoid, room'


def test_frpick_venues_given():
    st = strength_of(MIXED)
    for mask in range(16):
        for nh in (VENUES(mask), 0x7700 | mask, 0xFFFFFF00 | mask, 0x110 | mask):
            rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF, seed=mask, nhome=nh)
            if mask in TWO:
                if rc or home != mask or any(why):
                    return False, f'nhome {nh:#x}: {rc} home {home:#x} why {why}'
                if (ws, fb, bands) != cpick(MIXED, 0, SELF, seed=mask)[1:2] + cpick(MIXED, 0, SELF, seed=mask)[3:5]:
                    return False, f'nhome {nh:#x} changed the four'
            elif rc != GIVEN or why != [E_VENUE] * 4:
                return False, f'nhome {nh:#x} (not 2 + 2): {rc} why {why}'
    # the strength rule is off: the two strongest at home
    rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF, nhome=VENUES(0b1100))
    if rc or home != 0b1100 or cpick(MIXED, 0, SELF)[2] != 0b0011:
        return False, f'venues as given against the strength rule: {home:#x}'
    # a refused given entry: its codes only, the venue check skipped; a bad mask comes before FR_NOPOOL
    rc, ws, home, fb, bands, why = cpick(MIXED, 0, SELF, given=[SELF, NONE, word(99, 0), NONE], nhome=VENUES(0b0111))
    if rc != GIVEN or why != [E_SELF, 0, E_NOCLUB, 0]:
        return False, f'a refused entry + a bad mask: {rc} {why}'
    one = league([[200, 210], [200]])
    if cpick(one, 0, SELF, nhome=VENUES(1))[5] != [E_VENUE] * 4 or cpick(one, 0, SELF, nhome=VENUES(3))[0] != NOPOOL:
        return False, 'the venue check must run before the automatic slots'
    if cpick(MIXED, 0, SELF, nhome=0xFF)[2] != 15 or cpick(MIXED, 0, SELF, nhome=5)[2] != 15:
        return False, 'nhome 5 .. 0xFF = 4'
    return True, 'FR_VENUES: the 6 masks of 2 + 2 taken as given (any nhome >= 0x100), the 10 others FR_E_VENUE x 4'


def test_frpick_level():
    lv = lambda blob, w, world=0: lib().fr_level(blob, len(blob), world, w)
    b = league([list(range(10, 110))])                      # 100 clubs, strengths 10..109: 20 per level
    got = [lv(b, word(10, o)) for o in range(100)]
    if got != [1 + o // 20 for o in range(100)]:
        return False, f'100 distinct strengths: {got}'
    # equal strengths share a level; the weakest are 1; strictly below only
    b = league([[50] * 7, [50, 60, 60, 0, 70]])
    got = [lv(b, word(10, 0)), lv(b, word(11, 1)), lv(b, word(11, 2)), lv(b, word(11, 4))]
    if got != [1, 1 + 5 * 8 // 11, 1 + 5 * 8 // 11, 1 + 5 * 10 // 11]:
        return False, f'ties: {got}'
    if lv(league([[77]]), word(10, 0)) != 1 or lv(league([[5, 9]]), word(10, 1)) != 3:
        return False, 'one / two clubs'
    # 0: not a club (the FR_E_NOCLUB rules) or a refused blob
    b = mkblob([(0, 10, 0, [50, 0, 60]), (1, 11, 1, [70]), (0, 12, 2, [0] * 255 + [90])])
    for name, w, world in (('strength 0', word(10, 1), 0), ('ordinal >= count', word(10, 3), 0), ('no file', word(99, 0), 0),
                           ('another world', word(11, 0), 0), ('FR_NONE', NONE, 0), ('FR_AUTO', AUTO(1), 0),
                           ('file 255', 0x00FF, 0), ('no world', word(10, 0), 7)):
        if lv(b, w, world) != 0:
            return False, f'fr_level ({name}) = {lv(b, w, world)}'
    if (lv(b, word(12, 255)), lv(b, word(10, 0)), lv(b, word(11, 0), 1)) != (4, 1, 1):
        return False, 'ordinal 255 of a 256-club block / the other world'
    for name, bad in (('v1', b[:4] + b'\1' + b[5:]), ('magic', b'X' + b[1:]), ('short', b[:-2]), ('empty', b''),
                      ('file 255', mkblob([(0, 10, 0, [50]), (0, 255, 1, [60])]))):
        if lv(bad, word(10, 0)) != 0 or cpick(bad, 0, word(10, 0))[0] != BADBLOB:
            return False, f'a refused blob ({name}) has a level / is picked from'
    # the level is absolute, the band relative to self: the same club, three selves
    b = league([[100], [200], [300], [200, 201, 202, 203]])
    mid = word(11, 0)
    bands = [cpick(b, 0, word(10 + i, 0), given=[mid if i != 1 else word(13, 0), NONE, NONE, NONE])[4][0] for i in (0, 2)]
    if bands != [FAR_UP, WEAKER] or len({lv(b, mid) for _ in range(3)}) != 1:
        return False, f'absolute level / relative band: {bands}'
    return True, 'quintiles of 100 clubs, ties, strictly-below rule, 0 for no club / refused blob, 256-club block'


def test_frpick_real_bands():
    """every committed world table: for every club as self, every club of the world falls in exactly one of the five
    bands BY THE C's OWN fr_band (the FRPICK_TEST export), the bands are the header's intervals, contiguous and
    ordered, with the edges where the header puts them"""
    import glob
    fs = sorted(glob.glob(os.path.join(TOOLS, 'frdata', 'frstr_w*.bin')))
    if not fs:
        return True, 'SKIP: no tools/frdata/frstr_w*.bin'
    cband = lib().fr_test_band
    order = [FAR_DOWN, WEAKER, SIMILAR, STRONGER, FAR_UP]           # from the weakest to the strongest
    msgs = []
    for p in fs:
        blob = open(p, 'rb').read()
        if blob[4] != 2:
            return True, f'SKIP: {os.path.basename(p)} is not a v2 blob'
        tab = rparse(blob)
        if tab is None:
            return False, f'{os.path.basename(p)}: refused'
        world = tab[0][0]
        clubs, info = rtable(tab, world)
        vals = sorted({s for _, s, _ in clubs})
        pairs = 0
        for S in vals:
            M = max(11, S // 10)
            got = [cband(s - S, M) for s in vals]
            pairs += len(vals)
            for s, g in zip(vals, got):
                d = s - S
                hdr = [d < -4 * M, -4 * M <= d < -M, -M <= d <= M, M < d <= 4 * M, d > 4 * M]       # the header's lines
                if sum(hdr) != 1 or g != order[hdr.index(True)]:
                    return False, f'world {world}: S {S} s {s}: C band {g}, header {hdr}'
            rank = [order.index(g) for g in got]
            if rank != sorted(rank):
                return False, f'world {world}: S {S}: the bands are not ordered by strength'
            edges = [(-4 * M - 1, FAR_DOWN), (-4 * M, WEAKER), (-M - 1, WEAKER), (-M, SIMILAR), (0, SIMILAR), (M, SIMILAR),
                     (M + 1, STRONGER), (4 * M, STRONGER), (4 * M + 1, FAR_UP)]
            for d, want in edges:
                if cband(d, M) != want:
                    return False, f'world {world}: S {S} M {M}: d {d} is band {cband(d, M)}, the header says {want}'
        # the same through the public path on a few clubs: a chosen club's band[k]
        live = sorted(info, key=lambda w: (info[w][0], w))
        for self_ in (live[0], live[len(live) // 2], live[-1]):
            for g in random.Random(self_).sample(live, 12):
                if g == self_:
                    continue
                r = cpick(blob, world, self_, given=[g, NONE, NONE, NONE])
                if r[0] != OK or r[4][0] != rband(info[g][0] - info[self_][0], max(11, info[self_][0] // 10)):
                    return False, f'world {world}: self {self_:#x} given {g:#x}: {r}'
        smp = []
        for nm, S in (('weakest', vals[0]), ('median', sorted(s for _, s, _ in clubs)[len(clubs) // 2]), ('strongest', vals[-1])):
            M = max(11, S // 10)
            smp.append(f'{nm} S {S}: S-4M {S - 4 * M}, S-M {S - M}, S+M {S + M}, S+4M {S + 4 * M}')
        msgs.append(f'world {world}: {len(clubs)} clubs, {len(vals)} strengths ({pairs} pairs), M {max(11, vals[0] // 10)}'
                    f'..{max(11, vals[-1] // 10)}; ' + '; '.join(smp))
    return True, 'bands disjoint, complete, ordered | ' + ' | '.join(msgs)


def test_frpick_given_check_real():
    """THE GIVEN CHECK on every committed world table: fr_given(k) == fr_pick's why[k] / band[k] on a few hundred given
    lists per world (valid clubs, clubs of self's country, self / self2, duplicates, FR_AUTO, junk; with and without a
    room)"""
    import glob
    fs = sorted(glob.glob(os.path.join(TOOLS, 'frdata', 'frstr_w*.bin')))
    if not fs:
        return True, 'SKIP: no tools/frdata/frstr_w*.bin'
    n = int(os.environ.get('HT_FRPICK_GIVEN') or 300)
    msgs = []
    for p in fs:
        blob = open(p, 'rb').read()
        tab = rparse(blob)
        if tab is None:
            return True, f'SKIP: {os.path.basename(p)} is not a v2 blob this pick accepts'
        world = tab[0][0]
        clubs, info = rtable(tab, world)
        live = sorted(info)
        by_c = {}
        for w in live:
            by_c.setdefault(info[w][1], []).append(w)
        rng = random.Random(0x61 + world)
        seen = {}
        for i in range(n):
            self_ = rng.choice(live)
            mates = by_c[info[self_][1]]
            self2 = rng.choice([NONE, rng.choice(mates), rng.choice(live)])
            good = [NONE, AUTO(rng.randint(0, 2))] + [rng.choice(live) for _ in range(3)] + [rng.choice(mates)]
            bad = [self_, self2, word(rng.choice(live) & 0xFF, 255), rng.choice([0xF3FF, 0x00FF, rng.randint(0, 0xFFFF)])]
            g = [rng.choice(good + bad if i % 2 else good) for _ in range(4)]
            if i % 2 and rng.random() < .4:
                g[rng.randint(1, 3)] = g[0]
            a = dict(blob=blob, world=world, self_=self_, self2=self2, given=g)
            if rng.random() < .5:
                a['room'] = rng.randint(0, 3)
                a['cached'] = set(rng.sample(live, len(live) // rng.choice([2, 10, 50])))
            d = given_vs_pick(a)
            if d:
                return False, f'world {world} list {i}: {d} (self {self_:#x} self2 {self2:#x} given {[hex(x) for x in g]})'
            r = cpick(**a)
            seen[('pick', r[0])] = seen.get(('pick', r[0]), 0) + 1
            for e in (r[5] if r[0] == GIVEN else [0] * 4):
                seen[e] = seen.get(e, 0) + 1
            if r[0] == OK and any(info[w][1] == info[self_][1] for w in r[1]):
                seen['home'] = seen.get('home', 0) + 1
        if any(seen.get(e, 0) < 5 for e in (0, E_NOCLUB, E_SELF, E_BTEAM, E_DUP, E_ROOM, 'home', ('pick', OK))) \
                or E_HOME in seen:
            return False, f'world {world}: the lists do not reach every case: {seen}'
        msgs.append(f'world {world}: {n} lists ({seen[("pick", OK)]} accepted, {seen["home"]} with a club of self\'s '
                    f'country), codes ' + ' '.join(f'{e}: {seen.get(e, 0)}' for e in (0, -1, -2, -3, -4, -6)))
    return True, 'fr_given == fr_pick | ' + ' | '.join(msgs)
