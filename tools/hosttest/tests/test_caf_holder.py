"""CAF art. IV.5 (CL and CC): an association engages at most 2 clubs and the holder defending the cup is one of them (it takes the
association's LAST place; the lowest qualifier drops). Adapted from Convergence's repro.py (15/11): plays 2 seasons of the real
caf spec through conti._native, snapshots CT_ST, then per case writes the CL / CC holder as a club of rsa (2 CL places) or gha
(1 place) at league place 1 / 2 / 5 and counts that association's clubs in the cup (all rounds). The holder must be one of
them, never an extra club. Needs the private conti data (skipped without it)."""
import ctypes
import os
import struct
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import conti  # noqa: E402


def _run():
    try:
        spec, assocs, cups = conti.load(['caf'])
    except Exception as e:                                  # (no private data: internal/conti)
        print('SKIP', e)
        return None
    L = conti._native()
    lay = (ctypes.c_uint32 * 20).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out = lay[0], lay[1], lay[2]
    o_league, o_cup, o_club, o_nent, o_ent = lay[3], lay[4], lay[7], lay[11], lay[12]
    NA, NL, NC, NCUP, NRD, NE = lay[14:20]
    buf = ctypes.create_string_buffer(spec, len(spec))
    ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
    IN, OUT, ST = [(ctypes.c_ubyte * n).in_dll(L, s) for n, s in ((s_in, 'CT_IN'), (s_out, 'CT_OUT'), (s_st, 'CT_ST'))]
    cupno = {k: c for c, (f, k) in enumerate(cups)}
    clubs = [((100 + a) | k << 8, a, 4000 - 150 * k) for a, ak in enumerate(assocs) if not ak.startswith('g:') for k in range(18)]
    last = {}

    def season(order_of, seed, fin=True):
        b = bytearray(s_in)
        struct.pack_into('<IHH', b, 0, seed, len(clubs), 0)
        for i, (cid, a, st) in enumerate(clubs):
            struct.pack_into('<HBBII', b, o_club + 12 * i, cid, a, 0, st, 1000)
        for a in range(len(assocs)):
            mine = order_of(a, [i for i, c in enumerate(clubs) if c[1] == a])
            last[a] = mine
            for l, i in enumerate(mine[:NL]):
                struct.pack_into('<H', b, o_league + 2 * (a * NL + l), i + 1)
            if mine:
                struct.pack_into('<H', b, o_cup + 2 * a, mine[6] + 1)
        if fin:
            L.ct_finish()
        ctypes.memmove(IN, bytes(b), s_in)
        L.ct_season()

    def in_cup(cup):
        o, ib = bytes(OUT), bytes(IN)
        ids = set()
        for r in range(NRD):
            n = o[o_nent + cup * NRD + r]
            for x in struct.unpack_from(f'<{n}H', o, o_ent + 2 * (cup * NRD * NE + r * NE)):
                if x:
                    ids.add(struct.unpack_from('<H', ib, o_club + 12 * (x - 1))[0])
        return ids

    season(lambda a, m: m, 1)
    season(lambda a, m: m, 2)
    L.ct_finish()
    snap = bytearray(ST)

    def count(cup, ha, hold, P, also=None):
        def order(a, m):
            if a != ha or hold is None:
                return m
            hi = [i for i in m if clubs[i][0] == hold][0]
            m = [i for i in m if i != hi]
            return m[:P] + [hi] + m[P:]
        st = bytearray(snap)
        if hold is not None:
            struct.pack_into('<HBB', st, 4 + 12 * cup, hold, ha, 0)
        else:                                           # (the holder another association's club)
            ob = assocs.index('egy' if assocs[ha] != 'egy' else 'mar')
            struct.pack_into('<HBB', st, 4 + 12 * cup, (100 + ob) | 5 << 8, ob, 0)
        if also:                                        # (the OTHER cup's holder: (cup, club id, association))
            struct.pack_into('<HBB', st, 4 + 12 * also[0], also[1], also[2], 0)
        ctypes.memmove(ST, bytes(st), s_st)
        season(order, 3, fin=False)
        lg = [clubs[i][0] for i in last[ha]]
        return sorted(lg.index(c) + 1 for c in in_cup(cup) if (c & 0xFF) - 100 == ha)
    out = []
    for kind in ('cl', 'cc'):
        for ak in ('rsa', 'gha'):
            ha = assocs.index(ak)
            base = count(cupno[kind], ha, None, 0)
            hold = (100 + ha) | 5 << 8                  # (a club of that association holds the cup)
            for P in (0, 1, 4):
                out.append((kind, ak, P, len(base), count(cupno[kind], ha, hold, P)))
    for ak in ('rsa', 'gha'):                           # art. IV.4: the CC holder is the national champion: it defends the CC, the CL place
        ha = assocs.index(ak)                           # of the champion passes on (a federation with two clubs enters its 3rd)
        base = count(cupno['cl'], ha, None, 0)
        cch = (100 + ha) | 0 << 8                       # (league place 1's club)
        out.append(('art4', ak, 0, len(base), count(cupno['cl'], ha, None, 0, also=(cupno['cc'], cch, ha))))
    return out


def test_holder_is_one_of_two_never_extra():
    out = _run()
    if out is None:
        return True, 'SKIP: private conti data missing'
    bad = [o for o in out if len(o[4]) != min(2, max(o[3], 1)) or (o[0] == 'art4' and 1 in o[4])]
    assert not bad, f'(cup, association, holder place, places without holder, clubs in the cup with the holder): {bad}'


if __name__ == '__main__':
    r = _run()
    for o in r or []:
        print(o)
    test_holder_is_one_of_two_never_extra()
    print('ok')
