#!/usr/bin/env python3
"""4.2 AFC mode (MC 11/11): decode a refused group draw from a harness run dir.

    python3 tools/ctsd_replay.py <run dir>          (the dir holding ctsd_dump.json + ctsd_dump/, swostest's ctsd_dump)

The refused round (CT_SDRAW_ERR: season << 16 | cup << 12 | round << 8 | -rc; the round itself stays empty: not
drawn) and the edition's rounds from the dumped CT_OUT - team word, association, the manager starred, per association
counts (CTSD_ALL=1: every round). Compare them with the access data's maximum (a forced extra entrant shows as one
club of its association more than the data can give)."""
import ctypes
import json
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conti  # noqa: E402

ST_SEASON = 2                                       # (conti.h struct ct_state: u16 mark, u16 season)


def entrants(o, ib, lay, assocs, ci, r, mgr):
    o_club, o_nent, o_ent = lay[7], lay[11], lay[12]
    NRD, NE = lay[18], lay[19]
    n = o[o_nent + ci * NRD + r]
    out = []
    for q in range(n):
        x = struct.unpack_from('<H', o, o_ent + 2 * (ci * NRD * NE + r * NE + q))[0]
        if not x:
            out.append(('-', '-', 0, False))
            continue
        cid, a, _, st, _ = struct.unpack_from('<HBBII', ib, o_club + 12 * (x - 1))
        out.append((f'{cid:#06x}', assocs[a] if a < len(assocs) else f'#{a:#x}', st, x == mgr))
    return out


def show(tag, o, ib, lay, assocs, cups, mgr, refused):
    NRD = lay[18]
    print(f'== {tag}')
    for ci, (conf, ck) in enumerate(cups):
        for r in range(NRD):
            es = entrants(o, ib, lay, assocs, ci, r, mgr)
            if not es:
                continue
            mark = '  <== REFUSED' if (ci, r) == refused else ''
            cnt = Counter(e[1] for e in es)
            if (ci, r) == refused or os.environ.get('CTSD_ALL'):
                print(f'{conf}:{ck} round {r}: {len(es)} entrants{mark}')
                print('   by association:', dict(cnt.most_common()))
                print('   ', [f'{w}/{a}{"*" if m else ""}' for w, a, _, m in es])


def main(run):
    meta = json.load(open(os.path.join(run, 'ctsd_dump.json')))
    d = os.path.join(run, 'ctsd_dump')
    blob = {k[:-4]: open(os.path.join(d, k), 'rb').read() for k in os.listdir(d) if k.endswith('.bin')}
    err = meta['ERR']
    season, ci, r, rc = err >> 16, (err >> 12) & 15, (err >> 8) & 15, -(err & 0xFF)
    print(f'CT_SDRAW_ERR {err:#x}: season {season}, cup {ci}, round {r}, rc {rc} (N {meta["N"]}, HIT {meta["HIT"]})')
    _, assocs, cups = conti.load(conti.CONFS)
    L = conti._native()
    lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out = lay[0], lay[1], lay[2]
    ib, o = blob['CT_IN'][:s_in], blob['CT_OUT'][:s_out]
    mgr = struct.unpack_from('<IHH', ib, 0)[2]
    print(f'CT_IN: seed {struct.unpack_from("<I", ib, 0)[0]}, {struct.unpack_from("<H", ib, 4)[0]} clubs, manager {mgr}')
    show('the game (dumped CT_OUT)', o, ib, lay, assocs, cups, mgr, (ci, r))
    # (no native replay: the exe's spec carries patched pointers - CT_LP, the ranking in obj4 - a native conti.c
    #  reads differently; a replay of it ran other draws. The dumped CT_OUT is the edition itself.)


if __name__ == '__main__':
    main(sys.argv[1])
