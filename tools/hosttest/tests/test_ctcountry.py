"""conti.c ct_country (MC 12/11, class D: 'usa: access() found no club left'): a country's season-end input from
its division's whole table (ct_table) when the champion is in that table - also when it is not the table's leader
(the MLS Cup's play-off winner): the champion first, then the table's order; a table of another division (champion
not in it): the top 9 records alone, as before. Native conti.c (conti._native), CONCACAF's spec."""
import ctypes
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import conti  # noqa: E402

REC = 0x2AC


def _run(L, lay, assocs, a, table, champ, top9, cup):
    NL = lay[15]
    s_in, o_league, o_cup, o_club = lay[0], lay[3], lay[4], lay[7]
    diy = bytearray(0x12D + 2 * len(table) + 2)
    struct.pack_into('<H', diy, 0x31, len(table))
    for i, w in enumerate(table):                       # (rows in place order: row i at offset 18 i)
        struct.pack_into('<H', diy, 0x6D + 2 * i, 18 * i)
        struct.pack_into('<H', diy, 0x12D + 2 * i, w)
    stand = bytearray(9 * REC)
    for k, w in enumerate(top9):
        struct.pack_into('<H', stand, k * REC, w)
        for j in range(16):
            stand[k * REC + 76 + 38 * j + 32] = 9 - k
    cuprec = bytearray(REC)
    struct.pack_into('<H', cuprec, 0, cup)
    L.ct_begin()
    db, sb, cb = (ctypes.create_string_buffer(bytes(x), len(x)) for x in (diy, stand, cuprec))
    L.ct_table(db)
    L.ct_country(sb, cb)
    ib = bytes((ctypes.c_ubyte * s_in).in_dll(L, 'CT_IN'))
    word = lambda x: struct.unpack_from('<H', ib, o_club + 12 * (x - 1))[0] if x else 0
    lg = [word(x) for x in struct.unpack_from(f'<{NL}H', ib, o_league + 2 * NL * a) if x]
    return lg, word(struct.unpack_from('<H', ib, o_cup + 2 * a)[0])


def test_ctcountry_champion_not_leader():
    spec, assocs, cups = conti.load(['concacaf'])
    L = conti._native()
    lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
    buf = ctypes.create_string_buffer(spec, len(spec))
    ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
    a = assocs.index('usa')
    f = 100 + a                                         # (conti.load's test files: 100 + index)
    w = [f | i << 8 for i in range(30)]
    bad = []
    # 1. the champion (the MLS Cup's winner) 5th of the table: the whole table, the champion first
    lg, cw = _run(L, lay, assocs, a, w, w[4], [w[4]] + w[:4] + w[5:9], w[7])
    want = [w[4]] + w[:4] + w[5:]
    if lg != want[:len(lg)] or len(lg) != min(30, lay[15]):
        bad.append(f'champion 5th: league {[hex(x) for x in lg[:12]]}.. ({len(lg)}), want {len(want)} champion first')
    if cw != w[7]:
        bad.append(f'champion 5th: cup winner {cw:#x}')
    # 2. the champion the leader: unchanged
    lg2, _ = _run(L, lay, assocs, a, w, w[0], w[:9], w[7])
    if lg2 != w[:len(lg2)] or len(lg2) != min(30, lay[15]):
        bad.append(f'leader champion: {len(lg2)} clubs')
    # 3. a table of another division (the champion not in it): the top 9 records alone
    other = [(f + 1) | i << 8 for i in range(30)]
    lg3, _ = _run(L, lay, assocs, a, other, w[2], [w[2]] + w[:2] + w[3:9], w[7])
    if lg3 != [w[2]] + w[:2] + w[3:9]:
        bad.append(f'other division: {[hex(x) for x in lg3]}')
    return not bad, '; '.join(bad) or (f'US champion 5th: {len(lg)} league clubs, the champion first then the table '
                                       f'(was the top 9 alone); leader champion: {len(lg2)}; another division\'s '
                                       f'table: the top 9 records ({len(lg3)})')
