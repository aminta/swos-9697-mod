"""RI x S7 controls (MC 13/11, Panchina's flags (a) / (b); the exact oracles come with the fixes).
(b) test_ripool_cross_queue: gplay.c built natively (as test_cd_dt does), a planted one-file table (kind 0, 4 slots, a pool
of 3), RI_STATE planted as after a first season end (init 2): slot 0's map word names identity X = a club the S7 swap moved
to the other file ("left by S7": the invariant's input). Slot 0 is relegated from the lowest level -> ri_swap pushes
`was = map[0] - 1` = X at the queue's tail. INVARIANT after ri_season: none of the "left by S7" identities is in the queue,
no identity on two slots, none in the queue AND on a slot. FAILS on today's gplay.c (X queued): the bug (duplicate players
when X's pool turn comes back while it plays in the other file)."""
import ctypes
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_cd_dt as cd                              # (its native gplay.c build: _lib, FLAGS, TOOLS)

RIS, RP, RQT, RO, RMT = 256, 20, 192, 16, 640
FILE, WORLD = 144, 5
SLOTS = 4                                           # the file's slots in the table
POOL = 3                                            # RS records
BASE_G = 192                                        # slot i's global number


def ri_table(slots=SLOTS, pool=POOL, moff=0):
    """gplay.c ri_season's table (ripool.table_bytes' layout): one file, one kind-0 pool."""
    t = bytes([1])                                   # db files
    t += bytes((WORLD, FILE, 1)) + struct.pack('<HHHB', BASE_G, moff, slots, 0)   # world, file, pools; base, moff, nmap, nspare
    pl = bytes((0, pool))                            # db kind, n
    pl += bytes((5,)) + struct.pack('<H', slots)     # low = 5, slots
    for i in range(slots):
        pl += struct.pack('<HBB', BASE_G + i, 5, 0)  # global, base division 5, D area
    pl += bytes(pool)                                # n x D area
    pl += bytes(range(pool))                         # n x RS record (the first order)
    return t + pl


def plant(L, maps, queue):
    """The one place that knows RI_STATE's layout (struct ri_state: init[RF] qn[RP] q[RQT] ovr[RP][RO] maps[RMT])."""
    RF = 8
    st = (ctypes.c_uint8 * (RF + RP + 2 * RQT + 2 * RP * RO + 2 * RMT)).in_dll(L, 'RI_STATE')
    raw = bytearray(len(st))
    raw[0] = 2                                       # file 0 init: a first season end already done
    raw[RF] = len(queue)                             # qn[0]
    struct.pack_into(f'<{len(queue)}H', raw, RF + RP, *queue)
    struct.pack_into(f'<{len(maps)}H', raw, RF + RP + 2 * RQT + 2 * RP * RO, *maps)
    ctypes.memmove(st, bytes(raw), len(raw))


def read_state(L):
    RF = 8
    n = RF + RP + 2 * RQT + 2 * RP * RO + 2 * RMT
    raw = bytes((ctypes.c_uint8 * n).in_dll(L, 'RI_STATE'))
    qn = raw[RF]
    q = list(struct.unpack_from(f'<{qn}H', raw, RF + RP))
    maps = list(struct.unpack_from(f'<{SLOTS}H', raw, RF + RP + 2 * RQT + 2 * RP * RO))
    return q, maps


S7_FLAGS = ['-DGP_S7=1', '-DS7_FA=102', '-DS7_FB=144', '-DS7_DIRS={1,2,3,4}', '-DGP_DATA_SECTION=', '-DSS_NB=1',
            '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0']
NONE = 0xFFFF
POOL_FIRST = 100                                     # (the stand-in registry's pool idents: 100, 101, 102)


class Reg:
    """A stand-in S7 registry: occupant[row] = the ident playing at word FILE | row << 8; ri_pool decides, we apply."""
    def __init__(self, occ):
        self.occ = list(occ)
        self.cb = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_uint32)
        self.ident = self.cb(lambda w: self.occ[w >> 8] if (w & 0xFF) == FILE and (w >> 8) < len(self.occ) else NONE)
        self.poolk = self.cb(lambda i: i - POOL_FIRST if POOL_FIRST <= i < POOL_FIRST + POOL else NONE)
        self.home = self.cb(lambda w: w)             # (HOME: not used by ri_pool's S7 branch)


def s7_lib(tag='s7'):
    prev = cd.FLAGS
    cd.FLAGS = S7_FLAGS
    try:
        d = tempfile.mkdtemp(prefix='ris7')
        return cd._lib(d, open(os.path.join(cd.TOOLS, 'gplay.c')).read(), 1, tag)
    finally:
        cd.FLAGS = prev


def s7_hooks(L, reg):
    if os.environ.get('RIX_MUTANT_NOIDENT'):         # (control of the test: the hook unset = today's slot-keyed ri path)
        reg.ident = reg.cb(lambda w: NONE)
    for name, fn in (('GP_IDENT', reg.ident), ('GP_POOLK', reg.poolk), ('GP_HOME', reg.home)):
        ctypes.c_void_p.in_dll(L, name).value = ctypes.cast(fn, ctypes.c_void_p).value


def s7_season(L, reg, relegated, queue=None, qn=None):
    """One season end: ri_season with the registry stand-in; returns (moves [(row, out, in)], queue). The stand-in registry
    applies the moves (what s7_season does): the row's occupant = the incoming ident."""
    RF = 8
    if queue is not None:
        plant(L, [], queue)
    t = ctypes.create_string_buffer(ri_table(), 256)
    slt = (ctypes.c_int8 * 2400)()
    copy = (ctypes.c_int8 * 2400)()
    for r in relegated:
        copy[BASE_G + r] = 1
    ctypes.c_int32.in_dll(L, 'RI_MGR').value = 99999
    L.ri_season.argtypes = [ctypes.c_void_p] * 3 + [ctypes.c_int, ctypes.c_void_p]
    L.ri_season(ctypes.addressof(t), ctypes.addressof(slt), ctypes.addressof(copy), WORLD, None)
    n = ctypes.c_int.in_dll(L, 'RI_NMOVES').value
    mv = [tuple((ctypes.c_uint16 * 3).in_dll(L, 'RI_MOVES')[0:0]) for _ in range(0)]
    arr = (ctypes.c_uint16 * (64 * 3)).in_dll(L, 'RI_MOVES')
    mv = [(arr[3 * k], arr[3 * k + 1], arr[3 * k + 2]) for k in range(n)]
    for row, out, inn in mv:
        reg.occ[row] = inn
    q, _maps = read_state(L)
    return mv, q


def read_raw(L):
    RF = 8
    return bytes((ctypes.c_uint8 * (RF + RP + 2 * RQT + 2 * RP * RO + 2 * RMT)).in_dll(L, 'RI_STATE'))


def write_raw(L, raw):
    ctypes.memmove(ctypes.addressof((ctypes.c_uint8 * len(raw)).in_dll(L, 'RI_STATE')), raw, len(raw))


def s7_checks(L, reg, q, universe, errs, tag):
    """The invariants: every ident of the universe exactly once across the rows + the queue; maps[] untouched (all 0);
    RI_SWAPPED never set; RI_S7_BAD 0."""
    allv = reg.occ + q
    if sorted(allv) != sorted(universe):
        dup = sorted({x for x in allv if allv.count(x) > 1})
        errs.append(f'{tag}: rows {reg.occ} + queue {q}: duplicates {dup}, missing {sorted(set(universe) - set(allv))}')
    _q, maps = read_state(L)
    if any(maps):
        errs.append(f'{tag}: maps[] written {maps}')
    if ctypes.c_int.in_dll(L, 'RI_S7_BAD').value:
        errs.append(f'{tag}: RI_S7_BAD {ctypes.c_int.in_dll(L, "RI_S7_BAD").value}')
    sw = bytes((ctypes.c_uint8 * (8 * (RIS // 8))).in_dll(L, 'RI_SWAPPED'))
    if any(sw):
        errs.append(f'{tag}: RI_SWAPPED set')


def test_ripool_cross_queue():
    """MC 13/11 rulings (s7-ri-fix.md "Changes"): S7 builds, the REGISTRY decides, maps[] unused. (b) oracle: no ident twice
    across the rows + the queue. gplay.c built natively with GP_S7=1, a stand-in registry through GP_IDENT / GP_POOLK, a
    planted table (4 slots) + queue of the pool idents. Cases: 1 a native relegated (row 0); 2 a native on another row
    (the occupants permuted: ri only reads the occupant's ident); 3 a foreign club (an ident of the other file) relegated;
    a pool club relegated; several rows at once; 5 seasons with a save / load of RI_STATE in the middle, a native out and
    back into another row."""
    L = s7_lib()
    errs = []
    natives = [10, 11, 12, 13]                      # idents of the file's 4 rows; foreign = 50 (a 102 club)
    pool = [100, 101, 102]
    universe = natives + pool
    # 1 + 2: a permuted native occupancy, row 0 relegated: the occupant (13) out, the head (100) in
    reg = Reg([13, 11, 12, 10])
    s7_hooks(L, reg)
    mv, q = s7_season(L, reg, [0], queue=pool)
    if mv != [(0, 13, 100)] or q != [101, 102, 13]:
        errs.append(f'case 1/2: moves {mv}, queue {q} (want [(0, 13, 100)] / [101, 102, 13])')
    s7_checks(L, reg, q, universe, errs, 'case 1/2')
    # 3: a foreign club (50) on row 2 relegated; a native sits away (its ident 12 is in the queue: crossed out earlier)
    reg = Reg([10, 11, 50, 13])
    s7_hooks(L, reg)
    mv, q = s7_season(L, reg, [2], queue=[101, 102, 12])
    uni3 = [10, 11, 50, 13, 101, 102, 12]
    if mv != [(2, 50, 101)] or q != [102, 12, 50]:
        errs.append(f'case 3: moves {mv}, queue {q}')
    s7_checks(L, reg, q, uni3, errs, 'case 3')
    # a pool club on a row relegated, two rows at once
    reg = Reg([100, 11, 101, 13])
    s7_hooks(L, reg)
    mv, q = s7_season(L, reg, [0, 2], queue=[102, 10, 12])
    if mv != [(0, 100, 102), (2, 101, 10)] or q != [12, 100, 101]:
        errs.append(f'two rows: moves {mv}, queue {q}')
    s7_checks(L, reg, q, [100, 11, 101, 13, 102, 10, 12], errs, 'two rows')
    # a row whose occupant the registry does not know: the club stays, RI_S7_BAD counts (control of the checks)
    reg = Reg([10, NONE, 12, 13])
    s7_hooks(L, reg)
    before = ctypes.c_int.in_dll(L, 'RI_S7_BAD').value
    mv, q = s7_season(L, reg, [1], queue=pool)
    if mv or ctypes.c_int.in_dll(L, 'RI_S7_BAD').value != before + 1:
        errs.append(f'unknown occupant: moves {mv}, RI_S7_BAD {ctypes.c_int.in_dll(L, "RI_S7_BAD").value}')
    ctypes.c_int.in_dll(L, 'RI_S7_BAD').value = 0
    # 5 seasons, RI_STATE saved and reloaded between seasons 2 and 3; native 10 goes out in season 1 and must be back by 4
    reg = Reg([10, 11, 12, 13])
    s7_hooks(L, reg)
    mv, q = s7_season(L, reg, [0], queue=pool)       # 10 out
    s7_checks(L, reg, q, universe, errs, 's1')
    mv, q = s7_season(L, reg, [1])
    s7_checks(L, reg, q, universe, errs, 's2')
    saved, occ = read_raw(L), list(reg.occ)          # (the career is saved here: RI_STATE + the registry)
    mv3, q3 = s7_season(L, reg, [2])
    s7_checks(L, reg, q3, universe, errs, 's3')
    occ3 = list(reg.occ)
    write_raw(L, saved)                              # a load: the same state again; season 3 replayed must be the same
    reg.occ = list(occ)
    mv3b, q3b = s7_season(L, reg, [2])
    if (mv3b, q3b, reg.occ) != (mv3, q3, occ3):
        errs.append(f'save/load in the middle: replay {mv3b} {q3b} {reg.occ} != {mv3} {q3} {occ3}')
    mv, q = s7_season(L, reg, [3])
    s7_checks(L, reg, q, universe, errs, 's4')
    if reg.occ[3] != 10:                             # the native out in season 1 is the queue head in season 4: back, on ANOTHER row
        errs.append(f'native 10 should be back on row 3 after season 4: rows {reg.occ}, queue {q}')
    mv, q = s7_season(L, reg, [0])
    s7_checks(L, reg, q, universe, errs, 's5')
    if 10 not in reg.occ + q:
        errs.append('the native 10 vanished')
    return not errs, '; '.join(errs[:6]) or ('S7 ri_pool: the occupant out / the head in, logged; no ident twice across rows + queue in '
                                             'cases 1/2/3, two rows, 5 seasons with a save/load; maps[] untouched, RI_SWAPPED never set')


# ---------------------------------------------------------------------------------------------------------------------
# (a) s7_load: a moved row's registry club whose HOME slot ri has swapped must get its CURRENT record (MC 13/11, Shaved:
# RI_STATE.maps[moff(home file) + home slot]: word - 1 >= 256 = that file's pool record (id - 256), 1..255 = the ORIG
# record id - 1, 0 = the home record as today).
RIP_EXE = os.environ.get('HT_RIP_EXE') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'S7W-rip1', 'SWOS',
                                                       'ITALIAN.EXE')


def s7swap_fnv(b):
    import s7swap
    return s7swap.fnv(b)


def ri_where(sy, file):
    """THE helper that knows where ri's state lives in the host exe: (k, moff, ORIG offset key, POOL key) of a pooled
    team file, from the exe's .syms.json (ripool LABELS: RI_F{k} / RI_MOFF{k} / RI_ORIG{k} / RI_POOL{k})."""
    rs = sy['ripool']
    for k in range(8):
        if f'RI_F{k}' in rs and rs[f'RI_F{k}'][1] == file:
            return k, rs[f'RI_MOFF{k}'][1], f'RI_ORIG{k}', f'RI_POOL{k}'
    return None


def ri_plant(m, k, moff, okey, pkey, home_slots, orig_file, pool_recs):
    """Plant ri's state: ORIG buffer = the file as read, POOL buffer = BE count + the given records, maps[moff + slot] for
    each (slot, word)."""
    import ripool
    m.w(m.at('ripool', okey), orig_file)
    pool = struct.pack('>H', len(pool_recs)) + b''.join(pool_recs)
    m.w(m.at('ripool', pkey), pool)
    base = m.at('gplay', 'RI_STATE') + ripool.OVR_AT + 2 * ripool.RP * ripool.RO         # maps[0]
    for slot, word in home_slots:
        m.w(base + 2 * (moff + slot), struct.pack('<H', word))


def test_s7load_ri_home():
    import test_s7swap as s7
    if not os.path.exists(RIP_EXE) or not os.path.exists(RIP_EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {RIP_EXE} (a shaped HOSTTEST_SYMS=1 build with the ripool export) missing'
    sy = json.load(open(RIP_EXE[:-4] + '.syms.json'))
    w = ri_where(sy, s7.FB)
    if w is None:
        return False, f'{RIP_EXE}: RI_F{{k}} / RI_MOFF{{k}} not exported for file {s7.FB} (ripool LABELS)'
    k, moff, okey, pkey = w
    data = os.path.join(os.path.dirname(RIP_EXE), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (s7.FA, s7.FB)}
    rec = lambda f, o: fil[f][2 + 684 * o:2 + 684 * (o + 1)]
    m = s7.M(RIP_EXE)
    m.uc.mem_map(s7.TB, 0x40000)
    oat = struct.unpack('<II', m.rd(m.at('s7swap', 'S7_OAT'), 8))
    m.fresh()
    fs, word, at, rdiv, rows = s7.reg_parse(m.regb())
    m.w(m.at('swefile', 'swe_fopen_r'), b'\xb8\xfe\xff\xff\xff\xc3')
    down, up = s7.crossings(fs, m.gb)
    st, nsw, _, _ = s7.run(m, down, up)
    if st != s7.OK:
        return False, f'season status {st}'
    fs1, word1, at1, rdiv1, rows1 = s7.reg_parse(m.regb())
    orig = m.at('swe', 'S7_ORIG')
    for s_, f in enumerate((s7.FA, s7.FB)):              # (the disk files, as the other tests)
        m.w(orig + oat[s_], fil[f])
    b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))
    b[1] = 1
    m.w(m.at('s7swap', 'S7_LD'), bytes(b))
    m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *(s7swap_fnv(fil[f]) for f in (s7.FA, s7.FB))))
    # the moved rows of file FA whose registry club's HOME is in file FB (the pooled one): plant its ri state
    fi = 0
    cand = []
    for o in range(rows1[fi]):
        h = word[at1[fi][o]]
        if h & 0xFF == s7.FB:
            cand.append((o, h >> 8))
    if len(cand) < 2:
        return False, f'only {len(cand)} moved rows of {s7.FA} come from {s7.FB}'
    pool_recs = []
    plan = []                                            # (row, home slot, word, the record it must get)
    for n, (o, hs) in enumerate(cand):
        if n % 2 == 0:                                   # a pool identity: record 0, 1, ... (distinct bytes)
            pr = bytearray(rec(s7.FB, hs))
            for b_ in range(5, 684):
                pr[b_] ^= 0x3C
            plan.append((o, hs, 256 + len(pool_recs) + 1, bytes(pr)))
            pool_recs.append(bytes(pr))
        else:                                            # an ORIG identity of another slot
            idn = (hs + 5) % 100                         # (another slot of the file, 0..99)
            plan.append((o, hs, idn + 1, rec(s7.FB, idn)))
    # control of the control: no ri state planted (maps all 0): the rows must be the disk home records (today's, and the
    # fix's, rule for a word 0)
    m.w(s7.TB, fil[s7.FA])
    m.call('s7swap', 's7_load', s7.TB, s7.FA, 0)
    got0 = m.rd(s7.TB, len(fil[s7.FA]))
    for o, hs, _, _ in plan:
        w0 = bytearray(rec(s7.FB, hs))
        for b_ in s7.KEPT:
            w0[b_] = fil[s7.FA][2 + 684 * o + b_]
        if got0[2 + 684 * o:2 + 684 * (o + 1)] != bytes(w0):
            return False, f'control of the control: row {o} is not its disk home record with no ri state'
    ri_plant(m, k, moff, okey, pkey, [(hs, wd) for _, hs, wd, _ in plan], fil[s7.FB], pool_recs)
    m.w(s7.TB, fil[s7.FA])
    m.call('s7swap', 's7_load', s7.TB, s7.FA, 0)
    got = m.rd(s7.TB, len(fil[s7.FA]))
    errs = []
    for o, hs, wd, want_rec in plan:
        want = bytearray(want_rec)
        for b_ in s7.KEPT:
            want[b_] = fil[s7.FA][2 + 684 * o + b_]
        r = got[2 + 684 * o:2 + 684 * (o + 1)]
        if r != bytes(want):
            disk = bytearray(rec(s7.FB, hs))                 # (today: the home record of the disk file)
            for b_ in s7.KEPT:
                disk[b_] = fil[s7.FA][2 + 684 * o + b_]
            errs.append(f'row {o} (home {s7.FB}/{hs}, map word {wd}): '
                        f'{"the DISK home record" if r == bytes(disk) else "some other record"} '
                        f'(want the {"pool" if wd > 256 else "ORIG"} record)')
    return not errs, '; '.join(errs[:5]) or f'{len(plan)} moved rows took their ri identity\'s record'


def test_s7_pool_names():
    """MC 13/11: s7swap.check_pool_names on the real S7 pack: the registry's 36 pool rows = RS5144's clubs by name, both
    ways; CONTROLS: a pool club renamed in the RS file / a registry pool row missing are refused with both lists."""
    import mkseason
    import s7swap
    src = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita')
    if not os.path.isfile(os.path.join(src, 'pack.json')):
        return True, f'SKIP: {src} missing'
    pk = mkseason.Pack(src)
    home, _ = s7swap.homes(pk)
    n = s7swap.check_pool_names(pk, home)
    errs = []
    bad = list(home)                                   # a registry pool row that is not a pool row any more
    bad[home.index(0xFFFF)] = 144 | 0 << 8
    try:
        s7swap.check_pool_names(pk, bad)
        errs.append('a registry pool row dropped: not refused')
    except AssertionError as e:
        if 'only in RS' not in str(e):
            errs.append(f'wrong message {e}')
    orig = pk.pool_data
    ren = bytearray(orig)
    ren[2 + 5:2 + 7] = b'ZZ'                           # record 0's name changed
    pk.pool_data = bytes(ren)
    try:
        s7swap.check_pool_names(pk, home)
        errs.append('a renamed RS club: not refused')
    except AssertionError:
        pass
    pk.pool_data = orig
    return not errs, '; '.join(errs) or f'{n} pool rows = RS5144 clubs by name, both ways; two refusals'


def test_cd_str_s7():
    """MC 13/11 (point 1): in S7 builds cd_str gives the Coppa D tie seeding a club's REAL strength whoever sits on the row:
    a native of this file by its home row, a pool club by its RS index, a club of the OTHER league file by its home row in the
    table block cupd.strengths appends (db other file, 256 x dw), never the floor 5 unless its strength is that low.
    gplay.c is #included natively (cd_str is static); GP_IDENT / GP_POOLK / GP_HOME stand-ins; CD_DT built like cupd's."""
    import cupd
    import mkseason
    d = tempfile.mkdtemp(prefix='cdstr')
    src = ('#include "gplay.c"\n'
           'u32 t_cd_str(u16 w) { return cd_str(w); }\n'
           'void t_cdd(const u8 *p) { GP_CDD = p; }\n')
    prev = cd.FLAGS
    cd.FLAGS = S7_FLAGS + ['-DGP_CD2=1']
    try:
        L = cd._lib(d, src, 1, 'str')
    finally:
        cd.FLAGS = prev
    CD_O = 8                                         # (GP_CD2)
    OTHER, FILE_ = 102, 144
    nat = [5 + 7 * i for i in range(256)]            # the file's own ordinals' strengths
    pool = [40, 41, 42]
    oth = [9 + 3 * i for i in range(256)]
    oth[2] = 3                                       # a very weak club: the floor 5 applies by the rule, not by default
    blk = struct.pack('<HHH', 0, 162, len(pool)) + struct.pack('<256H', *nat) + b''.join(struct.pack('<H', x) for x in pool) \
        + struct.pack('<H', OTHER) + struct.pack('<256H', *oth)
    dt = bytes(CD_O + 256) + blk
    buf = ctypes.create_string_buffer(dt, len(dt))
    L.t_cdd.argtypes = [ctypes.c_void_p]
    L.t_cdd(ctypes.addressof(buf))
    L.t_cd_str.argtypes, L.t_cd_str.restype = [ctypes.c_uint16], ctypes.c_uint32
    # stand-in registry: row -> (ident, home word); pool idents 100..102 -> k
    occ = {5: (10, FILE_ | 5 << 8),                 # a native on its home row
           6: (11, FILE_ | 20 << 8),                # a native on another row (home row 20)
           7: (100 + 1, FILE_ | 7 << 8),            # a pool club (its home = its row)
           8: (50, OTHER | 30 << 8),                # a club of the other file (home 102 / 30)
           9: (51, OTHER | 2 << 8)}                 # the weak one (strength 3 -> 5)
    cb = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_uint32)
    ident = cb(lambda w: occ[w >> 8][0] if (w >> 8) in occ else NONE)
    poolk = cb(lambda i: i - 100 if 100 <= i <= 102 else NONE)
    home = cb(lambda w: occ[w >> 8][1] if (w >> 8) in occ else w)
    for name, fn in (('GP_IDENT', ident), ('GP_POOLK', poolk), ('GP_HOME', home)):
        ctypes.c_void_p.in_dll(L, name).value = ctypes.cast(fn, ctypes.c_void_p).value
    sq = lambda v: max(5, v) ** 2
    errs = []
    for row, want, what in ((5, sq(nat[5]), 'a native on its home row'), (6, sq(nat[20]), 'a native on another row (home 20)'),
                            (7, sq(pool[1]), 'a pool club (RS index 1)'), (8, sq(oth[30]), 'a club of the other file (home 102/30)'),
                            (9, sq(5), 'the weak club of the other file (3 -> the floor 5 by the rule)')):
        got = L.t_cd_str(FILE_ | row << 8)
        if got != want:
            errs.append(f'{what}: {got} != {want}')
    # cupd.strengths on the real pack: the block is there in a cd2 build and holds the other file's strengths
    src_pack = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita')
    if os.path.isfile(os.path.join(src_pack, 'pack.json')):
        pk = mkseason.Pack(src_pack)
        real = cupd.cd2
        cupd.cd2 = lambda: True
        try:
            b = cupd.strengths(pk, 144)
        finally:
            cupd.cd2 = real
        npool = struct.unpack_from('<H', b, 4)[0]
        o = 6 + 512 + 2 * npool
        if len(b) != o + 2 + 512 or struct.unpack_from('<H', b, o)[0] != 102:
            errs.append(f'cupd.strengths: length {len(b)} / other file {struct.unpack_from("<H", b, o)[0] if len(b) > o else None}')
        else:
            k0 = next(k for k in pk.clubs if pk.where.get(k, (None, None))[0] == 102)
            i0 = pk.where[k0][1]
            if struct.unpack_from('<H', b, o + 2 + 2 * i0)[0] != cupd.strength(pk, k0):
                errs.append('cupd.strengths: a 102 club\'s strength differs from cupd.strength')
        if len(cupd.strengths(pk, 144)) != 6 + 512 + 2 * npool:      # (not cd2: today's bytes)
            errs.append('cupd.strengths changed the non-cd2 bytes')
    return not errs, '; '.join(errs) or 'cd_str S7: native / moved native / pool / other-file / floor-by-rule; cupd block ok, non-cd2 bytes unchanged'
