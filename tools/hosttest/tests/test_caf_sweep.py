"""CAF art. IV.4 / IV.5 over many seasons (backlog-42 rows 146/149, the sweep): the real caf spec through conti._native,
300 season ends with every world association's table shuffled, clubs of realistic strengths (the 2026-27 world's CAF
clubs ~300 down, the guests' own), so holders come from the world AND from the guest associations (data's real lists:
a guest that wins comes back next season through its listed place too). From season 151 on the holders are also forced
to guests: a CL holder, a CC holder, and a CC holder that is listed in the CL (art. IV.4).

Per season and per cup (CL, CC; the access only: a CC club that is also in the CL dropped down from it):
- no association engages more than 2 clubs (IV.5);
- the holder defending the cup is in it from its holder round (or later, a bye) - never ALSO through a place of its
  association in an earlier round (one entry per cup);
- with the holder in, its association has exactly as many clubs as its places (at least 1): the holder is one of them;
- IV.4: the CC holder defending the CC is not in the CL.
Fails on 42-int c77f689: a guest holder entered twice (q1 + q2), a guest association over 2 clubs, a CC holder
listed in the CL playing both. Needs the private conti data (skipped without it)."""
import ctypes
import os
import random
import struct
import sys
from collections import Counter

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import conti  # noqa: E402

SEASONS = 300


def _run():
    try:
        spec, assocs, cups = conti.load(['caf'])
        fm, ac = conti._read('caf', 'format'), conti._read('caf', 'access') or {}
    except Exception as e:                                  # (no private data: internal/conti)
        print('SKIP', e)
        return None
    rounds = {c['key']: [r['key'] for r in c['rounds']] for c in fm['cups']}
    hround = {c['key']: rounds[c['key']].index(c['access']['holders'][c['key']])
              for c in ac['cups'] if c['key'] in ('cl', 'cc')}
    L = conti._native()
    lay = (ctypes.c_uint32 * 20).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out = lay[0], lay[1], lay[2]
    o_league, o_cup, o_club, o_nent, o_ent = lay[3], lay[4], lay[7], lay[11], lay[12]
    NA, NL, NC, NCUP, NRD, NE = lay[14:20]
    buf = ctypes.create_string_buffer(spec, len(spec))
    ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
    IN, OUT, ST = [(ctypes.c_ubyte * n).in_dll(L, s) for n, s in ((s_in, 'CT_IN'), (s_out, 'CT_OUT'), (s_st, 'CT_ST'))]
    cupno = {k: c for c, (f, k) in enumerate(cups)}
    clubs = [((100 + a) | k << 8, a, 300 - 13 * k) for a, ak in enumerate(assocs) if not ak.startswith('g:') for k in range(18)]
    rng = random.Random(7)

    def entrants(cup):
        o, ib = bytes(OUT), bytes(IN)
        ids = {}
        for r in range(NRD):
            n = o[o_nent + cup * NRD + r]
            for x in struct.unpack_from(f'<{n}H', o, o_ent + 2 * (cup * NRD * NE + r * NE)):
                if x:
                    cid, a = struct.unpack_from('<HB', ib, o_club + 12 * (x - 1))
                    ids.setdefault(cid, []).append((r, a))
        return ids

    guests, places, bad, seen = [], Counter(), [], Counter()
    for s in range(1, SEASONS + 1):
        b = bytearray(s_in)
        struct.pack_into('<IHH', b, 0, s, len(clubs), 0)
        for i, (cid, a, st) in enumerate(clubs):
            struct.pack_into('<HBBII', b, o_club + 12 * i, cid, a, 0, st, 1000)
        for a in range(len(assocs)):
            mine = [i for i, c in enumerate(clubs) if c[1] == a]
            rng.shuffle(mine)
            for l, i in enumerate(mine[:NL]):
                struct.pack_into('<H', b, o_league + 2 * (a * NL + l), i + 1)
            if mine:
                struct.pack_into('<H', b, o_cup + 2 * a, rng.choice(mine) + 1)
        L.ct_finish()
        if s > SEASONS // 2 and guests:                     # (forced guest holders: CL, CC, a CC holder listed in the CL)
            st = bytearray(ST)
            kind = s % 3
            g = guests[s % len(guests)] if kind < 2 else next(x for x in guests[s % len(guests):] + guests if x in incl)
            struct.pack_into('<HBB', st, 4 + 12 * cupno['cl' if kind == 0 else 'cc'], g[0], g[1], 0)
            ctypes.memmove(ST, bytes(st), s_st)
        ctypes.memmove(IN, bytes(b), s_in)
        L.ct_season()
        st = bytes(ST)
        hold = {k: struct.unpack_from('<HB', st, 4 + 12 * cupno[k]) for k in ('cl', 'cc')}
        ecl, ecc = entrants(cupno['cl']), entrants(cupno['cc'])
        if s == SEASONS // 2:                               # (the guests, and those listed in the CL)
            ib = bytes(IN)
            for i in range(struct.unpack_from('<H', ib, 4)[0]):
                cid, a = struct.unpack_from('<HB', ib, o_club + 12 * i)
                if assocs[a].startswith('g:') and (cid, a) not in guests:
                    guests.append((cid, a))
            incl = [g for g in guests if g[0] in ecl]
        for k, e in (('cl', ecl), ('cc', ecc)):
            per = Counter(v[0][1] for c, v in e.items() if not (k == 'cc' and c in ecl))
            hid, ha = hold[k]
            if s < SEASONS // 2:                            # (each association's places: the most it had, unforced)
                for a, n in per.items():
                    places[(k, a)] = max(places[(k, a)], n)
            for a, n in per.items():
                if n > 2:
                    bad.append((s, k, 'over 2', assocs[a], n))
            if not hid:
                continue
            seen[(k, 'guest' if assocs[ha].startswith('g:') else 'world')] += 1
            rs = [r for r, _ in e.get(hid, [])]
            if not rs:
                bad.append((s, k, 'holder missing', assocs[ha]))
                continue
            if min(rs) < hround[k]:                        # (later is a bye: the holder through to the next round)
                bad.append((s, k, 'holder also entered in an earlier round', assocs[ha], rs))
            want = max(1, min(2, places[(k, ha)]))
            if per[ha] != want:
                bad.append((s, k, "holder's association", assocs[ha], per[ha], want))
            if k == 'cc' and hid in ecl:
                bad.append((s, 'cl', 'art. IV.4: the CC holder also in the CL', assocs[ha]))
    return bad, seen


def test_caf_sweep_holders_and_cap():
    r = _run()
    if r is None:
        return True, 'SKIP: private conti data missing'
    bad, seen = r
    assert seen[('cl', 'guest')] >= 20 and seen[('cc', 'guest')] >= 20 and seen[('cl', 'world')] >= 100, \
        f'holders seen (the sweep must reach guest and world holders): {dict(seen)}'
    assert not bad, f'{len(bad)} findings, first: {bad[:6]}'
    return True, f'{SEASONS} seasons, holders {dict(seen)}: no association over 2, holders in once, IV.4 / IV.5 hold'


if __name__ == '__main__':
    print(test_caf_sweep_holders_and_cap())
