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


def plant(L, maps, queue, init=2):
    """The one place that knows RI_STATE's layout (struct ri_state: init[RF] qn[RP] q[RQT] ovr[RP][RO] maps[RMT])."""
    RF = 8
    st = (ctypes.c_uint8 * (RF + RP + 2 * RQT + 2 * RP * RO + 2 * RMT)).in_dll(L, 'RI_STATE')
    raw = bytearray(len(st))
    raw[0] = init                                    # file 0 init: 2 = a first season end already done, 0 = a new career
    raw[RF] = len(queue) if init else 0              # qn[0]
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

        def pk(i):
            if i & 0x10000:                          # 0x10000 | k = the ident of RS record k (s7swap's one place of the rule)
                k = i & 0xFFFF
                return POOL_FIRST + k if k < POOL else NONE
            return i - POOL_FIRST if POOL_FIRST <= i < POOL_FIRST + POOL else NONE
        self.poolk = self.cb(pk)
        self.home = self.cb(lambda w: w)


WRAP = (
    '#include <stdint.h>\n#include "gplay.c"\n'
    'uint32_t (*t_ident)(uint32_t); uint32_t (*t_poolk)(uint32_t); uint32_t (*t_home)(uint32_t);\n'
    'uint32_t s7_ident(uint32_t w) { return t_ident(w); }\n'
    'uint32_t s7_poolk(uint32_t i) { return t_poolk(i); }\n'
    'uint32_t s7_home_word(uint32_t w) { return t_home(w); }\n'
    '#define DATA\n#include "s7ri.c"\n'
    'void t_wire(void) { GP_RIPOOL = s7ri_pool; GP_CDSTR = s7ri_cdstr; }\n'
    'void t_unwire(void) { GP_RIPOOL = 0; GP_CDSTR = 0; }\n'
    'u32 t_cd_str(u16 w) { return cd_str(w); }\n'
    'void t_cdd(const u8 *p) { GP_CDD = p; }\n')


def s7_lib(tag='s7', extra=()):
    """gplay.c + s7ri.c in one native translation unit (as s7swap.c includes s7ri.c in the exe)."""
    prev = cd.FLAGS
    cd.FLAGS = S7_FLAGS + list(extra)
    try:
        d = tempfile.mkdtemp(prefix='ris7')
        return cd._lib(d, WRAP, 1, tag)
    finally:
        cd.FLAGS = prev


def s7_hooks(L, reg):
    if os.environ.get('RIX_MUTANT_NOIDENT'):         # (control of the test: the registry answers "none")
        reg.ident = reg.cb(lambda w: NONE)
    for name, fn in (('t_ident', reg.ident), ('t_poolk', reg.poolk), ('t_home', reg.home)):
        ctypes.c_void_p.in_dll(L, name).value = ctypes.cast(fn, ctypes.c_void_p).value
    L.t_wire()


def s7_season(L, reg, relegated, queue=None, qn=None):
    """One season end: ri_season with the registry stand-in; returns (moves [(row, out, in)], queue). The stand-in registry
    applies the moves (what s7_season does): the row's occupant = the incoming ident."""
    RF = 8
    if queue is not None:
        plant(L, [], queue, 2 if queue else 0)
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
    # the first order (a new career, init 0): q[] = the idents of RS records 0, 1, 2 in the table's order, then the swap
    reg = Reg([10, 11, 12, 13])
    s7_hooks(L, reg)
    mv, q = s7_season(L, reg, [0], queue=[])
    if mv != [(0, 10, 100)] or q != [101, 102, 10]:
        errs.append(f'first order: moves {mv}, queue {q} (want [(0, 10, 100)] / [101, 102, 10])')
    s7_checks(L, reg, q, universe, errs, 'first order')
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
# (a) s7_load, re-planted on the registry model (s7-ri-fix.md "Changes", MC 13/11): EVERY row of both league files gets the
# record of the club the registry puts there, by its occupant's ident: a native (of either file) = its disk home record,
# a pool ident = RS record k (S7_RIPOOL + 2 + 684 * k, k = s7_poolk(ident)); the row's own bytes (0..4, 23, 25) kept.
# oracle unchanged from 4f2ebd0 ("each row = its occupant's right record"), independent of s7_load's code: the expected
# record is computed here from the registry (at[]) and the pack's home words (s7swap.homes).
import test_s7rimoves as rm  # noqa: E402


def test_s7load_ri_home():
    import mkseason
    import s7swap
    import test_s7swap as t7
    m, why = rm.setup()
    if not m:
        return why.startswith('SKIP'), why
    pack = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita')
    if not os.path.isfile(os.path.join(pack, 'pack.json')):
        return True, f'SKIP: {pack} missing'
    home, _ = s7swap.homes(mkseason.Pack(pack))
    fs, word, at, rdiv, rows = t7.reg_parse(m.regb())
    p0, np_ = struct.unpack('<HH', m.rd(m.at('s7swap', 'S7_POOL0'), 4))
    fb = [f[0] for f in fs].index(t7.FB)
    ends = [sum(fs[fb][2][:g + 1]) - 1 for g in range(2)]
    mv = [(r, at[fb][r], p0 + k) for k, r in enumerate(ends)]          # two pool clubs into Serie D (ri's moves)
    rm.poke_moves(m, mv)
    st, nsw, _, _ = t7.run(m, *t7.crossings(fs, m.gb))
    if st != t7.OK:
        return False, f'season status {st}'
    fs1, word1, at1, rdiv1, rows1 = t7.reg_parse(m.regb())
    data = os.path.join(os.path.dirname(rm.EXE), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (t7.FA, t7.FB)}
    rs = open(os.path.join(data, 'RS5144.DAT'), 'rb').read()
    oat = struct.unpack('<II', m.rd(m.at('s7swap', 'S7_OAT'), 8))
    orig = m.at('swe', 'S7_ORIG')
    for s_, f in enumerate((t7.FA, t7.FB)):
        m.w(orig + oat[s_], fil[f])
    b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))
    b[1] = 1
    m.w(m.at('s7swap', 'S7_LD'), bytes(b))
    m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *(s7swap.fnv(fil[f]) for f in (t7.FA, t7.FB))))
    ripool = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_RIPOOL'), 4))[0]
    if os.environ.get('RIX_MUTANT_NORS'):                # (control of the test: the pool buffer left empty)
        pass
    else:
        m.w(ripool, rs)
    m.uc.mem_map(t7.TB, 0x40000)
    errs = []
    rec = lambda f, o: fil[f][2 + 684 * o:2 + 684 * (o + 1)]
    for fi, f in enumerate((t7.FA, t7.FB)):
        buf = bytearray(fil[f])
        for o in range(rows1[fi]):                      # (every row's own bytes marked: kept from the buffer)
            for k, kb in enumerate(t7.KEPT):
                buf[2 + 684 * o + kb] = (0x40 + 7 * k + o) & 0xFF
        m.w(t7.OB, fil[f])
        m.w(t7.TB, bytes(buf))
        m.call('s7swap', 's7_load', t7.TB, f, t7.OB)
        st = struct.unpack('<B', m.rd(m.at('s7swap', 'S7_LD'), 1))[0]
        if st != t7.LD_OK:
            errs.append(f'{f}: status {st}')
            continue
        got = m.rd(t7.TB, len(buf))
        bad = 0
        for o in range(rows1[fi]):
            ident = at1[fi][o]
            h = home[ident]
            if h == 0xFFFF:                              # a pool club: RS record k
                want = bytearray(rs[2 + 684 * (ident - p0):2 + 684 * (ident - p0 + 1)])
            else:                                        # a native: its disk home record
                want = bytearray(rec(h & 0xFF, h >> 8))
            for kb in t7.KEPT:
                want[kb] = buf[2 + 684 * o + kb]
            if got[2 + 684 * o:2 + 684 * (o + 1)] != bytes(want):
                bad += 1
                if bad <= 2:
                    errs.append(f'file {f} row {o} (ident {ident}, home {h:#x}): not its occupant\'s record')
        if bad > 2:
            errs.append(f'file {f}: {bad} rows wrong')
    if struct.unpack('<i', m.rd(m.at('s7swap', 'RI_S7_BAD'), 4))[0]:
        errs.append('RI_S7_BAD != 0')
    return not errs, '; '.join(errs[:5]) or (f'both files, every row = its occupant\'s record: natives their disk home record '
                                             f'(crossers too), the {len(mv)} pool clubs RS records {[e[2] - p0 for e in mv]}; '
                                             f'own bytes kept')




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
    # (Shaved 13/11, MC: s7swap.pool_order - the order, and the check skipped only with no pool on BOTH sides)
    p0, np_ = s7swap.pool_order(pk, home)
    if (p0, np_) != (home.index(0xFFFF), n):
        errs.append(f'pool_order {p0, np_}: want ({home.index(0xFFFF)}, {n})')
    sw = bytearray(orig)                               # RS records 0 and 1 swapped: the same set, another order
    sw[2:2 + 684], sw[2 + 684:2 + 2 * 684] = orig[2 + 684:2 + 2 * 684], orig[2:2 + 684]
    pk.pool_data = bytes(sw)
    try:
        s7swap.pool_order(pk, home)
        errs.append('RS records 0 / 1 swapped: pool_order not refused')
    except AssertionError as e:
        if 'not RS record j' not in str(e):
            errs.append(f'swapped order: wrong message {e}')
    keep_pf = getattr(pk, 'pool_file', None)
    pk.pool_data, pk.pool_file = None, None            # registry pool rows, no RS file: refused, never skipped
    try:
        s7swap.pool_order(pk, home)
        errs.append('pool rows without an RS file: not refused')
    except AssertionError as e:
        if 'no RS file' not in str(e):
            errs.append(f'no RS file: wrong message {e}')
    pk.pool_data, pk.pool_file = orig, keep_pf
    s7t = os.environ.get('HT_S7T_PACK') or '/private/tmp/claude-501/-Users-davide/161293a9-d461-4832-8300-ab312d6d3a9a/scratchpad/s7t/ita'
    if os.path.isfile(os.path.join(s7t, 'pack.json')):  # (the s7t test pack: no off-file pool on either side - skipped)
        pt = mkseason.Pack(s7t)
        ht, _ = s7swap.homes(pt)
        if s7swap.pool_order(pt, ht) != (0xFFFF, 0):
            errs.append(f's7t: pool_order {s7swap.pool_order(pt, ht)}: want (0xFFFF, 0)')
    return not errs, '; '.join(errs) or (f'{n} pool rows = RS5144 clubs by name, both ways, in order (idents '
                                         f'{p0}..{p0 + n - 1}); four refusals' + ('; s7t skipped' if os.path.isfile(
                                             os.path.join(s7t, 'pack.json')) else ''))


def test_cd_str_s7():
    """MC 13/11 (point 1): in S7 builds cd_str gives the Coppa D tie seeding a club's REAL strength whoever sits on the row:
    a native of this file by its home row, a pool club by its RS index, a club of the OTHER league file by its home row in the
    obj4 table S7RI_STRF / S7RI_STR (cupd.other_strengths), never the floor 5 unless its strength is that low.
    gplay.c is #included natively (cd_str is static); GP_IDENT / GP_POOLK / GP_HOME stand-ins; CD_DT built like cupd's."""
    import cupd
    import mkseason
    L = s7_lib('str', ['-DGP_CD2=1'])
    CD_O = 8                                         # (GP_CD2)
    OTHER, FILE_ = 102, 144
    nat = [5 + 7 * i for i in range(256)]            # the file's own ordinals' strengths
    pool = [40, 41, 42]
    oth = [9 + 3 * i for i in range(256)]
    oth[2] = 3                                       # a very weak club: the floor 5 applies by the rule, not by default
    blk = struct.pack('<HHH', 0, 162, len(pool)) + struct.pack('<256H', *nat) + b''.join(struct.pack('<H', x) for x in pool)
    dt = bytes(CD_O + 256) + blk
    ctypes.c_uint16.in_dll(L, 'S7RI_STRF').value = OTHER                 # (s7swap.py writes these: obj4, not the gplay pages)
    (ctypes.c_uint16 * 256).in_dll(L, 'S7RI_STR')[:] = oth
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
    poolk = cb(lambda i: i - 100 if 100 <= i <= 102 else NONE)      # (cd_str never asks the 0x10000 form)
    home = cb(lambda w: occ[w >> 8][1] if (w >> 8) in occ else w)
    for name, fn in (('t_ident', ident), ('t_poolk', poolk), ('t_home', home)):
        ctypes.c_void_p.in_dll(L, name).value = ctypes.cast(fn, ctypes.c_void_p).value
    L.t_wire()
    sq = lambda v: max(5, v) ** 2
    errs = []
    for row, want, what in ((5, sq(nat[5]), 'a native on its home row'), (6, sq(nat[20]), 'a native on another row (home 20)'),
                            (7, sq(pool[1]), 'a pool club (RS index 1)'), (8, sq(oth[30]), 'a club of the other file (home 102/30)'),
                            (9, sq(5), 'the weak club of the other file (3 -> the floor 5 by the rule)')):
        got = L.t_cd_str(FILE_ | row << 8)
        if got != want:
            errs.append(f'{what}: {got} != {want}')
    # cupd on the real pack: other_strengths = the other file's rows by the same rule; strengths() keeps today's bytes even in cd2
    src_pack = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita')
    if os.path.isfile(os.path.join(src_pack, 'pack.json')):
        pk = mkseason.Pack(src_pack)
        f_o, rows = cupd.other_strengths(pk, 144)
        k0 = next(k for k in pk.clubs if pk.where.get(k, (None, None))[0] == 102)
        i0 = pk.where[k0][1]
        if f_o != 102 or not 0 < len(rows) <= 256 or rows[i0] != cupd.strength(pk, k0):
            errs.append(f'cupd.other_strengths: file {f_o}, {len(rows)} rows, row {i0} {rows[i0] if i0 < len(rows) else None}')
        real = cupd.cd2
        cupd.cd2 = lambda: True
        try:
            b = cupd.strengths(pk, 144)
        finally:
            cupd.cd2 = real
        if len(b) != 6 + 512 + 2 * struct.unpack_from('<H', b, 4)[0]:
            errs.append(f'cupd.strengths grew in a cd2 build: {len(b)} B')
    return not errs, '; '.join(errs) or 'cd_str S7: native / moved native / pool / other-file / floor-by-rule; cupd block ok, non-cd2 bytes unchanged'
