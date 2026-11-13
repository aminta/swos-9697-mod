"""RI x S7 controls (MC 13/11, Panchina's flags (a) / (b); the exact oracles come with the fixes).
(b) test_ripool_cross_queue: gplay.c built natively (as test_cd_dt does), a planted one-file table (kind 0, 4 slots, a pool
of 3), RI_STATE planted as after a first season end (init 2): slot 0's map word names identity X = a club the S7 swap moved
to the other file ("left by S7": the invariant's input). Slot 0 is relegated from the lowest level -> ri_swap pushes
`was = map[0] - 1` = X at the queue's tail. INVARIANT after ri_season: none of the "left by S7" identities is in the queue,
no identity on two slots, none in the queue AND on a slot. FAILS on today's gplay.c (X queued): the bug (duplicate players
when X's pool turn comes back while it plays in the other file)."""
import ctypes
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
