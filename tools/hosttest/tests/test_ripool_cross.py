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


def run_season(L, maps, queue, relegated):
    plant(L, maps, queue)
    t = ctypes.create_string_buffer(ri_table(), 256)
    slt = (ctypes.c_int8 * 2400)()
    copy = (ctypes.c_int8 * 2400)()
    for s in relegated:
        copy[BASE_G + s] = 1                         # relegated from the lowest level (division 5 -> 6)
    ctypes.c_int32.in_dll(L, 'RI_MGR').value = 99999
    L.ri_season.argtypes = [ctypes.c_void_p] * 3 + [ctypes.c_int, ctypes.c_void_p]
    L.ri_season(ctypes.addressof(t), ctypes.addressof(slt), ctypes.addressof(copy), WORLD, None)
    return read_state(L)


def test_ripool_cross_queue():
    import tempfile as tf
    d = tf.mkdtemp(prefix='ricross')
    gsrc = open(os.path.join(cd.TOOLS, 'gplay.c')).read()
    L = cd._lib(d, gsrc, 1, 'ri')
    X = 7                                            # the identity (file record 7: not slot 0's own) the S7 swap moved away
    # slot 0 holds X (map word X + 1); slots 1..3 their own; the queue: 3 pool identities (256 + k)
    # control of the control: X's slot NOT relegated (slot 1 is): nothing of X reaches the queue, the invariant holds
    q0, m0 = run_season(L, [X + 1, 0, 0, 0], [RIS + 0, RIS + 1, RIS + 2], [1])
    ids0 = [(m - 1) if m else i for i, m in enumerate(m0)]
    if X in q0 or len(set(ids0)) != len(ids0) or set(ids0) & set(q0):
        return False, f'the invariant check itself fails on a clean season: queue {q0}, slots {ids0}'
    # slot 0 holds X (map word X + 1); slots 1..3 their own; the queue: 3 pool identities (256 + k); slot 0 relegated
    q, maps = run_season(L, [X + 1, 0, 0, 0], [RIS + 0, RIS + 1, RIS + 2], [0])
    left = {X}                                       # identities the S7 swap moved to the other file
    errs = []
    if left & set(q):
        errs.append(f'identity {sorted(left & set(q))} left by S7 is in the queue {q}')
    ids = [(m - 1) if m else i for i, m in enumerate(maps)]
    if len(set(ids)) != len(ids):
        errs.append(f'an identity on two slots: {ids}')
    if set(ids) & set(q):
        errs.append(f'in the queue AND on a slot: {sorted(set(ids) & set(q))} (slots {ids}, queue {q})')
    ok_swap = maps[0] != X + 1 and maps[0] != 0 and len(q) == POOL        # (the swap ran: slot 0 took the queue head)
    return not errs, '; '.join(errs) or f'swap ran ({ok_swap}); queue {q}, slots {ids}: no left-by-S7 identity queued, no duplicate'


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
