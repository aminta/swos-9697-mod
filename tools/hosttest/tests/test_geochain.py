"""4.2 Serie D geography (MC 14/11): s7geo.c's s7geochain, the chain of one-step moves that makes a seat in a full girone for
a pool arrival. Native (gplay.c + s7ri.c, test_ripool_cross.s7_lib): 9 gironi of 18 stayers, the pack's neighbour table
(ita pack.json 'geo'), the cases: a neighbour with a seat = one step; only a far girone with a seat = a chain of single steps
along the edges (never one big jump); the manager's club, this season end's arrivals and pending clubs never move; no seat
anywhere = no chain and nothing touched; the order of a girone's list decides (control: the reversed list ends elsewhere)."""
import ctypes
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import test_ripool_cross as rc  # noqa: E402

PACK = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita', 'pack.json')
FL, G, SZ = 5, 9, 18


def neigh_table(lists):
    tab = bytearray(b'\xff' * 81)
    for i, L in enumerate(sorted(lists)):
        nb = [ord(c) - 65 for c in lists[L]]
        tab[9 * i:9 * i + len(nb)] = bytes(nb)
    return bytes(tab)


def pack_lists():
    if not os.path.exists(PACK):
        return None
    return (json.load(open(PACK, encoding='utf-8')).get('geo') or {}).get('neighbours')


class Gi:
    def __init__(self, L, lists, occ=None):
        self.L = L
        ctypes.memmove(ctypes.addressof(ctypes.c_uint8.in_dll(L, 'S7GEO_NEIGH')), neigh_table(lists), 81)
        ctypes.c_uint8.in_dll(L, 'S7GEO_ON').value = 1
        ctypes.c_int.in_dll(L, 'S7GEO_NLOG').value = 0
        ctypes.c_int.in_dll(L, 'S7GEO_BAD').value = 0
        self.ent = bytearray()
        self.copy = (ctypes.c_int8 * 2400)()
        self.slt = (ctypes.c_int8 * 2400)()
        for i in range(G * SZ):
            h = 300 + i
            self.ent += bytes((h & 255, h >> 8, 0))
            self.copy[h] = self.slt[h] = FL + i // SZ
        self.c = ctypes.create_string_buffer(bytes(self.ent), len(self.ent))
        self.occ = (ctypes.c_uint8 * G)(*(occ or [SZ] * G))
        self.sz = (ctypes.c_uint8 * G)(*([SZ] * G))
        self.pend = (ctypes.c_uint8 * 4096)()

    def club(self, x, k):
        return 300 + x * SZ + k

    def call(self, a, og=(), mgr=-1, pending=()):
        for h in pending:
            self.pend[h >> 3] |= 1 << (h & 7)
        ogs = (ctypes.c_uint16 * max(1, len(og)))(*og)
        f = self.L.s7geochain
        f.restype = ctypes.c_int32
        f.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
                      ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32,
                      ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
        return f(ctypes.addressof(self.c), 3, G * SZ, FL, a, G, ctypes.addressof(self.sz), ctypes.addressof(self.occ),
                 ctypes.addressof(self.slt), ctypes.addressof(self.copy), ctypes.addressof(self.pend), 32768,
                 ctypes.addressof(ogs), len(og), mgr)

    def where(self, h):
        return self.copy[h] - FL

    def log(self):
        n = ctypes.c_int.in_dll(self.L, 'S7GEO_NLOG').value
        arr = (ctypes.c_uint16 * (2 * 48)).from_address(ctypes.addressof(ctypes.c_uint16.in_dll(self.L, 'S7GEO_LOG')))
        return [(arr[2 * i], arr[2 * i + 1] >> 8, arr[2 * i + 1] & 255) for i in range(n)]


E_, D_, F_, G_, H_, I_ = 4, 3, 5, 6, 7, 8


def occ_with(room):
    o = [SZ] * G
    for x in room:
        o[x] = SZ - 1
    return o


def test_geochain():
    lists = pack_lists()
    if not lists:
        print('SKIP: no ita pack.json geo.neighbours')
        return
    L = rc.s7_lib('geo')
    errs = []
    # 1. a neighbour with a seat: one step, the lowest row of the full girone
    g = Gi(L, lists, occ_with([D_]))
    r = g.call(E_)
    if (r, g.where(g.club(E_, 0)), g.occ[E_], g.occ[D_], g.log()) != (1, D_, SZ - 1, SZ, [(g.club(E_, 0), E_, D_)]):
        errs.append(f'1 one step: {r} {g.where(g.club(E_, 0))} occ {g.occ[E_]}/{g.occ[D_]} {g.log()}')
    # 2. only I has a seat: E -> F -> H -> I (BFS in list order: E's list D F G reaches H through F first), three single steps, never one jump
    g = Gi(L, lists, occ_with([I_]))
    r = g.call(E_)
    want = [(g.club(H_, 0), H_, I_), (g.club(F_, 0), F_, H_), (g.club(E_, 0), E_, F_)]
    got = sorted(g.log(), key=lambda x: -x[1])
    if r != 1 or [tuple(x) for x in got] != want or [g.occ[i] for i in (E_, F_, H_, I_)] != [SZ - 1, SZ, SZ, SZ]:
        errs.append(f'2 chain E-F-H-I: {r} log {g.log()} want {want} occ {list(g.occ)}')
    # 3. the manager's club, an arrival of this season end and a pending club are never the mover: the next row moves
    g = Gi(L, lists, occ_with([D_]))
    r = g.call(E_, og=[g.club(E_, 1)], mgr=g.club(E_, 0), pending=[g.club(E_, 2)])
    if (r, [x[0] for x in g.log()]) != (1, [g.club(E_, 3)]):
        errs.append(f'3 exclusions: {r} {g.log()} (want the 4th club of E)')
    # 4. nowhere a seat: no chain, nothing touched, BAD counted
    g = Gi(L, lists)
    r = g.call(E_)
    if (r, g.log(), ctypes.c_int.in_dll(L, 'S7GEO_BAD').value, g.where(g.club(E_, 0))) != (0, [], 1, E_):
        errs.append(f'4 no seat: {r} {g.log()}')
    # 5. a girone whose only movable clubs are all excluded: no half chain (the first step would have a mover, the second none)
    g = Gi(L, lists, occ_with([I_]))
    r = g.call(E_, og=[g.club(H_, k) for k in range(SZ)])
    if (r, g.log(), [g.where(g.club(E_, k)) for k in range(2)]) != (0, [], [E_, E_]):
        errs.append(f'5 half chain: {r} {g.log()}')
    # 6. control: the list order decides - E's list reversed (G F D) with seats in D and F: the real list goes to D, the reversed to F
    g = Gi(L, lists, occ_with([D_, F_]))
    g.call(E_)
    real = g.log()
    rev = dict(lists)
    rev['E'] = lists['E'][::-1]
    g2 = Gi(L, rev, occ_with([D_, F_]))
    g2.call(E_)
    if not (real and g2.log() and real[0][2] == D_ and g2.log()[0][2] == F_):
        errs.append(f'6 order control: real {real} reversed {g2.log()} (want D then F)')
    assert not errs, '; '.join(errs)


if __name__ == '__main__':
    test_geochain()
    print('PASS test_geochain')


def pg_world(L, hook, demand_order, mgr_g=-1):
    """pg_season (the real pg_one) on a Serie D-shaped table: 9 gironi of 18 seats, 14 stayers each + 4 freed rows each (the
    relegated clubs' seats) taken by 36 pool arrivals (ri_over) whose own girone is demand_order[k] (row k of the freed rows).
    Returns {arrival k: final girone}, {stayer global: (from, to)} for the stayers that moved."""
    lists = pack_lists()
    Gi(L, lists)                                         # (S7GEO table + log reset; the entries below are our own)
    L.t_geo(1 if hook else 0)
    L.t_og_clear()
    L.t_mgr(mgr_g)
    ents, slt, copy = bytearray(), (ctypes.c_int8 * 2400)(), (ctypes.c_int8 * 2400)()
    arr, stay, k = {}, {}, 0
    for x in range(G):
        for j in range(18):
            g = 400 + x * 18 + j
            area = 15
            if j >= 14:                                   # a freed row: a pool arrival takes it
                area = demand_order[k]
                L.t_og_set(g)
                arr[k] = g
                k += 1
            else:
                stay[g] = x
                area = x
            ents += bytes((g & 255, g >> 8, 0, area))
            slt[g] = copy[g] = FL + x
    hdr = bytes((5, 1, FL, G)) + bytes([SZ] * G) + bytes((1, G * 18 & 255, G * 18 >> 8))
    t = bytes((1,)) + hdr + bytes(ents)
    buf = ctypes.create_string_buffer(t, len(t))
    L.pg_season.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    L.pg_season(ctypes.addressof(buf), ctypes.addressof(slt), ctypes.addressof(copy), 5)
    final = {kk: copy[g] - FL for kk, g in arr.items()}
    moved = {g: (x, copy[g] - FL) for g, x in stay.items() if copy[g] - FL != x}
    return final, moved


def test_geochain_pg_one():
    """The chain through the real pg_one: the real pack's demand (A3 B3 C4 D3 E5 F5 G4 H5 I4 own-girone arrivals over 4 freed rows
    per girone): with GP_GEOCH every arrival ends in its own girone, each girone holds 18, the stayers that moved moved once,
    the manager's club never; control (no hook = today's pg_room fallback): some arrival lands elsewhere."""
    lists = pack_lists()
    if not lists:
        print('SKIP: no ita pack.json geo.neighbours')
        return
    L = rc.s7_lib('geo2')
    dem = [0] * 3 + [1] * 3 + [2] * 4 + [3] * 3 + [4] * 5 + [5] * 5 + [6] * 4 + [7] * 5 + [8] * 4
    errs = []
    mgr = 400 + 4 * 18                                   # (E's first stayer: the lowest-row mover otherwise)
    final, moved = pg_world(L, True, dem, mgr)
    out = [k for k in final if final[k] != dem[k]]
    if out:
        errs.append(f'hook on: arrivals {out} not in their own girone {[(k, dem[k], final[k]) for k in out]}')
    cnt = [0] * G
    for kk, x in final.items():
        cnt[x] += 1
    for g, (x, y) in moved.items():
        cnt[y] += 1
    stay = [0] * G
    for x in range(G):
        stay[x] = 14 - sum(1 for g, (a, b) in moved.items() if a == x)
    tot = [stay[x] + cnt[x] - sum(1 for g, (a, b) in moved.items() if b == x) + sum(1 for g, (a, b) in moved.items() if b == x) for x in range(G)]
    if mgr in moved:
        errs.append(f'the manager club moved {moved[mgr]}')
    if not moved or any(abs(a - b) != 1 and (a, b) not in {(0, 3), (3, 0), (3, 1), (1, 3), (3, 2), (2, 3), (3, 4), (4, 3), (3, 5), (5, 3), (4, 5), (5, 4), (4, 6), (6, 4), (5, 6), (6, 5), (5, 7), (7, 5), (6, 7), (7, 6), (7, 8), (8, 7), (1, 2), (2, 1), (0, 1), (1, 0)} for a, b in moved.values()):
        errs.append(f'moves not along the adjacency or none: {moved}')
    sizes = [sum(1 for k in final if final[k] == x) + 14 - sum(1 for g, (a, b) in moved.items() if a == x) + sum(1 for g, (a, b) in moved.items() if b == x) for x in range(G)]
    if sizes != [SZ] * G:
        errs.append(f'girone sizes {sizes} (want 18 each)')
    f0, m0 = pg_world(L, False, dem, mgr)
    if all(f0[k] == dem[k] for k in f0):
        errs.append('control (no hook): every arrival in its own girone - the test does not need the chain')
    assert not errs, '; '.join(errs)
