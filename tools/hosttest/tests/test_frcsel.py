"""4.2 preseason friendlies, the chooser's selection state tools/frcsel.c against tools/frcsel.h's rules. Host only:
frcsel.c + frpick.c built natively (clang -shared, ctypes). The pick's rules are NOT re-tested here (test_frpick.py):
every expected value is fr_pick's own answer for the given[] / nhome the header says the page's state means.
HT_FRCSEL_CASES = the number of random walks (default 300)."""
import ctypes
import glob
import os
import random
import struct
import subprocess
import tempfile

import test_frpick as T
from test_frpick import FrPick, FrRoom, CACHED, NONE, AUTO, VENUES, mkblob, word

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
CASES = int(os.environ.get('HT_FRCSEL_CASES') or 300)
MIX, EASY, MEDIUM, HARD = 0, 1, 2, 3
FILL = {MIX: NONE, EASY: AUTO(T.WEAKER), MEDIUM: AUTO(T.SIMILAR), HARD: AUTO(T.STRONGER)}
LBAND = {EASY: T.WEAKER, MEDIUM: T.SIMILAR, HARD: T.STRONGER}
VAUTO = 0xFF
ST_OFF, ST_SHIFT = 11, 6
M_NONE, M_CLUB, M_DUP, M_ROOM, M_NOPOOL = range(5)


class FrcCtx(ctypes.Structure):
    _fields_ = [('frss', ctypes.c_char_p), ('len', ctypes.c_uint32), ('world', ctypes.c_uint8),
                ('self', ctypes.c_uint16), ('self2', ctypes.c_uint16), ('avoid', ctypes.POINTER(ctypes.c_uint16)),
                ('navoid', ctypes.c_uint32), ('room', ctypes.POINTER(FrRoom)), ('season', ctypes.c_uint32),
                ('seed', ctypes.c_uint32), ('nhome', ctypes.c_uint32), ('frst', ctypes.POINTER(ctypes.c_uint8))]


class FrcSel(ctypes.Structure):
    _fields_ = [('c', ctypes.POINTER(FrcCtx)), ('club', ctypes.c_uint16 * 4), ('level', ctypes.c_uint8),
                ('venues', ctypes.c_uint8), ('msg', ctypes.c_int8), ('out', FrPick)]


_LIB = {}
_TMP = tempfile.mkdtemp(prefix='frcsel')


def lib(opt='-O2'):
    if opt not in _LIB:
        so = os.path.join(_TMP, f'frcsel{opt}.dylib')
        subprocess.run(['clang', '-shared', opt, '-Wall', '-Werror', '-o', so, os.path.join(TOOLS, 'frcsel.c'),
                        os.path.join(TOOLS, 'frpick.c')], check=True)
        l = ctypes.CDLL(so)
        P = ctypes.POINTER
        l.frc_init.argtypes = [P(FrcSel), P(FrcCtx)]
        l.frc_set_level.argtypes = [P(FrcSel), ctypes.c_int]
        l.frc_set_club.argtypes = [P(FrcSel), ctypes.c_uint32, ctypes.c_uint16]
        l.frc_swap_venue.argtypes = [P(FrcSel), ctypes.c_uint32]
        l.frc_trial.argtypes = [P(FrcSel), ctypes.c_uint32, ctypes.c_uint16, P(ctypes.c_uint8)]
        l.frc_result.argtypes = [P(FrcSel), P(ctypes.c_uint16 * 4), P(ctypes.c_uint8)]
        l.frc_result.restype = None
        l.frc_msg.argtypes = [ctypes.c_int]
        l.fr_pick.restype = ctypes.c_int
        l.fr_pick.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                              ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(FrPick)]
        _LIB[opt] = l
    return _LIB[opt]


class Page:
    """one FrcSel over a context; pick() = the engine's installing call for a given[] / venues"""

    def __init__(self, blob, world, self_, self2=NONE, avoid=(), room=None, cached=(), season=1, seed=7, nhome=2,
                 level=MIX, opt='-O2'):
        self.l = lib(opt)
        self.blob = blob
        self.avoid = (ctypes.c_uint16 * max(1, len(avoid)))(*avoid)
        self.cb = CACHED(lambda ctx, w: 1 if w in cached else 0)
        self.room = FrRoom(room, self.cb, None) if room is not None else None
        self.frst = (ctypes.c_uint8 * 12)(*([0x5A] * 12))
        self.frst[ST_OFF] = 0x15 | level << ST_SHIFT
        self.ctx = FrcCtx(blob, len(blob), world, self_, self2, self.avoid, len(avoid),
                          ctypes.pointer(self.room) if self.room else None, season, seed, nhome,
                          ctypes.cast(self.frst, ctypes.POINTER(ctypes.c_uint8)))
        self.s = FrcSel()
        ctypes.memset(ctypes.byref(self.s), 0xA5, ctypes.sizeof(self.s))
        self.rc = self.l.frc_init(ctypes.byref(self.s), ctypes.byref(self.ctx))

    def pick(self, given, venues=VAUTO):
        c, out = self.ctx, FrPick()
        g = (ctypes.c_uint16 * 4)(*given)
        rc = self.l.fr_pick(self.blob, len(self.blob), c.world, c.self, c.self2, g, self.avoid, c.navoid,
                            ctypes.byref(self.room) if self.room else None, c.season, c.seed,
                            c.nhome if venues == VAUTO else VENUES(venues), ctypes.byref(out))
        return rc, snap(out)

    def state(self):
        s = self.s
        return list(s.club), s.level, s.venues, snap(s.out)

    def result(self):
        g, v = (ctypes.c_uint16 * 4)(), ctypes.c_uint8(0x77)
        self.l.frc_result(ctypes.byref(self.s), ctypes.byref(g), ctypes.byref(v))
        return list(g), v.value

    def level(self, d):
        return self.l.frc_set_level(ctypes.byref(self.s), d)

    def club(self, k, w):
        return self.l.frc_set_club(ctypes.byref(self.s), k, w)

    def swap(self, k):
        return self.l.frc_swap_venue(ctypes.byref(self.s), k)

    def trial(self, k, w):
        b = ctypes.c_uint8(0xEE)
        return self.l.frc_trial(ctypes.byref(self.s), k, w, ctypes.byref(b)), b.value


def snap(o):
    return list(o.word), o.home, o.fb, list(o.band), list(o.why)


def code(rc, out):
    """the header's refusal code of an fr_pick answer"""
    if rc == T.GIVEN:
        return 16 + next(w for w in out[4] if w)
    return rc


def table(rnd, world=3, files=6, per=(8, 30)):
    """a synthetic one-world table: files of distinct countries, strengths spread around every band"""
    blocks = [(world, 10 + f, 10 + f, [rnd.choice((0, rnd.randint(5, 400), rnd.randint(5, 4000)))
                                       for _ in range(rnd.randint(*per))]) for f in range(files)]
    blob = mkblob(blocks)
    clubs = [word(fl, o) for _, fl, _, st in blocks for o, v in enumerate(st) if v]
    return blob, world, clubs


def consistent(p):
    """the page's preview == the engine's installing call with what frc_result hands back (H: preview == final)"""
    clubs, level, venues, out = p.state()
    g, v = p.result()
    exp = [c if c != NONE else FILL[level] for c in clubs]
    if g != exp or v != venues:
        return f'frc_result {g} / {v:#x}, state means {exp} / {venues:#x}'
    rc, o = p.pick(g, v)
    if rc or o != out:
        return f'preview {out} but fr_pick({g}, venues {v:#x}) = {rc} {o}'
    return None


def test_frcsel_init_levels():
    """frc_init reads the level from FR_ST +10 bits 14-15; MIX (and a save without the bits) = given 4 x 0xFFFF =
    today's automatic pick; EASY / MEDIUM / HARD = 4 x FR_AUTO(weaker / similar / stronger)"""
    rnd = random.Random(1)
    n = 0
    for i in range(60):
        blob, world, clubs = table(rnd)
        me = rnd.choice(clubs)
        for level in (MIX, EASY, MEDIUM, HARD):
            p = Page(blob, world, me, level=level, seed=i)
            rc, o = p.pick([FILL[level]] * 4)
            if p.rc != code(rc, o):
                return False, f'case {i} level {level}: frc_init {p.rc}, fr_pick {rc}'
            if rc:
                continue
            if p.state() != ([NONE] * 4, level, VAUTO, o) or p.s.msg:
                return False, f'case {i} level {level}: {p.state()} msg {p.s.msg}, fr_pick {o}'
            if level == MIX and p.pick([NONE] * 4)[1] != o:
                return False, f'case {i}: MIX is not the plain automatic pick'
            n += 1
    return True, f'{n} pages: every level opens on fr_pick\'s own answer; MIX = given 4 x 0xFFFF'


def test_frcsel_result_bits():
    """frc_result writes only bits 14-15 of FR_ST +10 and nothing else of FR_ST; the next season's page reads them"""
    rnd = random.Random(2)
    blob, world, clubs = table(rnd, per=(30, 40))
    seen = set()
    for start in (MIX, EASY, MEDIUM, HARD):
        p = Page(blob, world, clubs[0], level=start)
        if p.rc:
            return False, f'page refused {p.rc}'
        for d in (1, 1, -1, 1, 1, 1, -1, -1, -1):
            before = p.s.level
            rc = p.level(d)
            if not rc and p.s.level != (before + d) % 4:
                return False, f'level {before} {d:+d} -> {p.s.level}'
            p.result()
            b = list(p.frst)
            if b[:ST_OFF] != [0x5A] * ST_OFF or b[ST_OFF] != (0x15 | p.s.level << ST_SHIFT):
                return False, f'FR_ST after frc_result: {b}'
            seen.add(p.s.level)
            q = Page(blob, world, clubs[0], level=b[ST_OFF] >> ST_SHIFT)
            if q.s.level != p.s.level:
                return False, 'the written level is not the one read back'
    return len(seen) == 4, f'levels {sorted(seen)} written and read back, the other 94 bits untouched'


def test_frcsel_refused_keeps_state():
    """a change fr_pick refuses leaves the state and its preview as they were; msg = the reason; the message table
    covers every code (H4)"""
    l = lib()
    blob = mkblob([(1, 20, 20, [100, 100, 95, 0]), (1, 21, 21, [100, 104, 90, 300, 30]),
                   (1, 22, 22, [101, 99, 250, 40, 100, 100])])
    me, b = word(20, 0), word(20, 1)
    p = Page(blob, 1, me, self2=b)
    if p.rc:
        return False, f'page refused: {p.rc}'
    want = [(word(20, 3), 16 + T.E_NOCLUB, M_CLUB), (word(99, 0), 16 + T.E_NOCLUB, M_CLUB),
            (me, 16 + T.E_SELF, M_CLUB), (b, 16 + T.E_BTEAM, M_CLUB)]
    for w, c, m in want:
        st = p.state()
        rc = p.club(1, w)
        if rc != c or p.s.msg != c or l.frc_msg(rc) != m or p.state() != st:
            return False, f'club {w:#x}: rc {rc} (want {c}) msg {p.s.msg} text {l.frc_msg(rc)}, state kept {p.state() == st}'
    if p.club(0, word(21, 0)) or p.s.club[0] != word(21, 0) or p.s.out.word[0] != word(21, 0) or p.s.msg:
        return False, 'a valid club refused'
    if p.club(0, word(20, 2)) or p.s.out.word[0] != word(20, 2):
        return False, 'a club of my own country refused (D2: allowed for a chosen slot)'
    st = p.state()
    rc = p.club(2, word(20, 2))
    if rc != 16 + T.E_DUP or l.frc_msg(rc) != M_DUP or p.state() != st:
        return False, f'duplicate: rc {rc}'
    codes = [0, T.NOSELF, T.BADBLOB, T.NOPOOL] + [16 + e for e in (T.E_NOCLUB, T.E_SELF, T.E_BTEAM, T.E_DUP, T.E_HOME,
                                                                  T.E_ROOM, T.E_VENUE)]
    texts = {c: l.frc_msg(c) for c in codes}
    if texts[0] != M_NONE or any(not 0 < texts[c] < 5 for c in codes[1:]) or texts[16 + T.E_ROOM] != M_ROOM \
            or texts[T.NOPOOL] != M_NOPOOL:
        return False, f'message table {texts}'
    return True, f'{len(want) + 1} refusals keep the state; own-country club accepted; message table covers {len(codes)} codes'


def test_frcsel_room():
    """a chosen club that does not fit in the team cache is refused with the ROOM text; cached clubs cost nothing"""
    l = lib()
    blob = mkblob([(1, 20, 20, [100]), (1, 21, 21, [100, 104, 96, 98, 102, 99, 101, 97])])
    me = word(20, 0)
    p = Page(blob, 1, me, room=4)
    if p.rc:
        return False, f'page refused {p.rc}'
    auto = set(p.s.out.word)
    free = [word(21, o) for o in range(8) if word(21, o) not in auto]
    q = Page(blob, 1, me, room=4, cached=set(auto))
    # 4 automatic clubs are cached (cost 0): 4 new chosen clubs fit exactly
    for k in range(4):
        if q.club(k, free[k]):
            return False, f'chosen club {k} refused with room 4: {q.s.msg}'
    r = Page(blob, 1, me, room=1, cached=set(auto))
    if r.rc or r.club(0, free[0]):
        return False, 'room 1: the first new club must fit'
    st = r.state()
    rc = r.club(1, free[1])
    if rc != 16 + T.E_ROOM or l.frc_msg(rc) != M_ROOM or r.state() != st:
        return False, f'room 1: the second new club: rc {rc}'
    return True, 'room 4 takes 4 new clubs, room 1 refuses the second (state kept, ROOM text)'


def test_frcsel_swap():
    """FIRE on a venue: slot k and the nearest slot of the other venue (ties: the lower) flip, 2 home + 2 away stay;
    the mask then holds while clubs and the level change"""
    rnd = random.Random(4)
    n = 0
    for i in range(200):
        blob, world, clubs = table(rnd)
        p = Page(blob, world, rnd.choice(clubs), seed=i, level=rnd.randrange(4))
        if p.rc:
            continue
        for _ in range(6):
            k = rnd.randrange(4)
            home = p.s.out.home
            other = [j for j in range(4) if (home >> j ^ home >> k) & 1]
            j = min(other, key=lambda x: (abs(x - k), x))
            if p.swap(k):
                return False, f'case {i}: swap refused {p.s.msg}'
            exp = home ^ 1 << k ^ 1 << j
            if p.s.venues != exp or p.s.out.home != exp or bin(exp).count('1') != 2:
                return False, f'case {i}: home {home:04b} swap {k} -> venues {p.s.venues:04b} home {p.s.out.home:04b}, want {exp:04b}'
            e = consistent(p)
            if e:
                return False, f'case {i}: {e}'
            if rnd.random() < 0.5:
                p.level(1)
                p.club(rnd.randrange(4), rnd.choice(clubs + [NONE]))
                if p.s.venues != exp or p.s.out.home != exp:
                    return False, f'case {i}: the swapped venues did not hold'
            n += 1
    # an engine nhome that is not 2: nothing to pair with -> no change
    blob, world, clubs = table(random.Random(5))
    p = Page(blob, world, clubs[0], nhome=4)
    if not p.rc:
        st = p.state()
        if p.swap(1) or p.state() != st:
            return False, 'nhome 4: a swap must change nothing'
    return True, f'{n} swaps: nearest slot of the other venue, always 2 + 2, kept across later changes'


def test_frcsel_trial():
    """frc_trial (the club list's colours and grey entries) = what frc_set_club would do, without changing the state"""
    rnd = random.Random(6)
    n = ref = 0
    for i in range(120):
        blob, world, clubs = table(rnd)
        p = Page(blob, world, rnd.choice(clubs), seed=i, level=rnd.randrange(4), room=rnd.choice((None, 3, 6)))
        if p.rc:
            continue
        if rnd.random() < 0.6:
            p.club(rnd.randrange(4), rnd.choice(clubs))
        for _ in range(12):
            k, w = rnd.randrange(4), rnd.choice(clubs + [word(77, 1)])
            st = p.state()
            rc, band = p.trial(k, w)
            if p.state() != st:
                return False, f'case {i}: frc_trial changed the state'
            keep = ctypes.string_at(ctypes.byref(p.s), ctypes.sizeof(p.s))
            rc2 = p.club(k, w)
            if rc != rc2 or (not rc and (p.s.out.word[k] != w or p.s.out.band[k] != band)):
                return False, f'case {i}: trial {rc} band {band}, set {rc2} band {p.s.out.band[k]}'
            ctypes.memmove(ctypes.byref(p.s), keep, len(keep))
            n += 1
            ref += rc != 0
    return ref > 0 and n > ref, f'{n} trials == the real change ({ref} refusals), state untouched'


def test_frcsel_walk():
    """random walks over every action: after each one the preview is exactly the engine's installing call for what
    frc_result hands back; a refused action changes nothing; the same at -O0 / -O2 / -Oz"""
    rnd = random.Random(7)
    acts = refused = 0
    for i in range(CASES):
        blob, world, clubs = table(rnd)
        me = rnd.choice(clubs)
        kw = dict(seed=rnd.getrandbits(32), season=rnd.randrange(40), level=rnd.randrange(4),
                  room=rnd.choice((None, None, 4, 5, 8)), avoid=rnd.sample(clubs, min(4, len(clubs))),
                  self2=rnd.choice((NONE, rnd.choice(clubs))))
        ps = [Page(blob, world, me, opt=o, **kw) for o in ('-O0', '-O2', '-Oz')]
        if len({p.rc for p in ps}) != 1:
            return False, f'walk {i}: frc_init differs by -O level'
        if ps[0].rc:
            continue
        for _ in range(25):
            a = rnd.randrange(4)
            k, w, d = rnd.randrange(4), rnd.choice(clubs + [NONE, NONE, me, word(250, 0)]), rnd.choice((1, -1))
            st = ps[0].state()
            rcs = [p.level(d) if a == 0 else p.swap(k) if a == 1 else p.club(k, w) for p in ps]
            if len(set(rcs)) != 1 or any(p.state() != ps[0].state() for p in ps):
                return False, f'walk {i}: the -O levels differ'
            p = ps[0]
            acts += 1
            if rcs[0]:
                refused += 1
                if p.state() != st or p.s.msg != rcs[0]:
                    return False, f'walk {i}: a refused action ({rcs[0]}) changed the state'
            elif p.s.msg:
                return False, f'walk {i}: msg {p.s.msg} after an accepted action'
            e = consistent(p)
            if e:
                return False, f'walk {i}: {e}'
    return acts > 1000 and refused > 0, f'{acts} actions ({refused} refused): preview == final, -O0 == -O2 == -Oz'


def test_frcsel_levels_real_tables():
    """Davide 16/11: EASY / MEDIUM / HARD are disjoint, in every world's committed table (tools/frdata/frstr_w*.bin),
    for EVERY club of the world as the career club: a slot not filled by the pick's nearest-band rule (fb) is in its
    level's band (weaker / similar / stronger than the club) - so no club can be in two levels' lists unless the
    world has no such opponent left for that club (counted below, the pick's own fallback)."""
    fs = sorted(glob.glob(os.path.join(TOOLS, 'frdata', 'frstr_w*.bin')))
    if not fs:
        return True, 'SKIP: no tools/frdata/frstr_w*.bin'
    msgs = []
    for path in fs:
        raw = bytearray(open(path, 'rb').read())
        if raw[4] == 1:                                 # (test_frpick._real: the 1996-97 v1 table, country = file)
            if raw[8] != 0:
                return True, f'SKIP: {os.path.basename(path)} is a v1 blob of world {raw[8]}'
            raw[4] = 2
            for i in range(struct.unpack_from('<H', raw, 6)[0]):
                raw[8 + 6 * i + 3] = raw[8 + 6 * i + 1]
        blob, world = bytes(raw), raw[8]
        st = T.strength_of(blob, world)
        live = [w for w in st if st[w][0]]
        pages = fbs = shared = 0
        for me in live:
            lists = {}
            for level in (EASY, MEDIUM, HARD):
                p = Page(blob, world, me, level=level, seed=me)
                if p.rc:
                    return False, f'{os.path.basename(path)} club {me:#06x} level {level}: no page ({p.rc})'
                words, home, fb, bands, _ = snap(p.s.out)
                for k in range(4):
                    if fb >> k & 1:
                        fbs += 1
                    elif bands[k] != LBAND[level]:
                        return False, f'{os.path.basename(path)} club {me:#06x} level {level} slot {k}: band {bands[k]}'
                if bin(home).count('1') != 2 or len(set(words)) != 4 or me in words:
                    return False, f'{os.path.basename(path)} club {me:#06x} level {level}: {words} home {home:04b}'
                lists[level] = {w for k, w in enumerate(words) if not fb >> k & 1}
                pages += 1
            if lists[EASY] & lists[MEDIUM] or lists[MEDIUM] & lists[HARD] or lists[EASY] & lists[HARD]:
                return False, f'{os.path.basename(path)} club {me:#06x}: a club in two levels'
        msgs.append(f'world {world}: {len(live)} clubs x 3 levels = {pages} pages, disjoint; {fbs} of {pages * 4} '
                    f'slots from the nearest-band rule')
    return True, ' | '.join(msgs)
