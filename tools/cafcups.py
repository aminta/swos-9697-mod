"""African club cups (step 1): CAF Champions League, CAF Cup Winners' Cup, CAF Cup.

Same layout as the South American cups (sacups.py): the Champions League copies the European Champions
Cup (16 teams, 4 groups of 4, then knockout; the real 1997 edition had a group stage too), the other two are
16-team two-legged knockouts. They appear as cup buttons of the Africa continent (preset competitions, career
world view) and in the international contests list.
Initial team lists (first season): 1996-97 final standings (1997 for Nigeria/Cameroon, file order of
africa.py); for Algeria, South Africa and Ghana (alphabetical files) the strongest clubs, with the real
1996-97 champions where SWOS has them (Manning Rangers, Obuasi Goldfields).
Step 2 (todo): player's club enters them in career, qualifiers from the standings at season end, persistence.
"""
import struct

import sacups

CAFCL_ID, CAFCWC_ID, CAFCUP_ID = 0x76, 0x77, 0x78
NAMES = {CAFCL_ID: b'CAF CHAMPIONS LEAGUE', CAFCWC_ID: b'CAF CUP WINNERS CUP', CAFCUP_ID: b'CAF CUP'}
ALG, SAF, GHA, EGY, MAR, TUN, NGA, CMR = 42, 69, 79, 52, 53, 54, 56, 58

# groups / pairings are consecutive; no two clubs of one country together
CHAMPIONS_LEAGUE = [
    (EGY, 0), (MAR, 1), (NGA, 0), (GHA, 4),        # Al Ahly, Wydad, Eagle Cement, Hearts of Oak
    (MAR, 0), (TUN, 1), (CMR, 0), (SAF, 5),        # Raja, Esperance, Cotonsport, Kaizer Chiefs
    (TUN, 0), (EGY, 1), (ALG, 12), (CMR, 1),       # Etoile du Sahel, Zamalek, USM Harrach, Stade Bandjoun
    (SAF, 7), (GHA, 6), (NGA, 1), (ALG, 8),        # Manning Rangers, Obuasi Goldfields, Jasper United, NA Hussein Dey
]
CUP_WINNERS_CUP = [
    (EGY, 2), (SAF, 9), (MAR, 2), (ALG, 2),        # El Mansoura - Orlando Pirates, RS Settat - CR Belcourt
    (TUN, 2), (GHA, 0), (NGA, 2), (CMR, 3),        # CS Sfaxien - Asante Kotoko, Shooting Stars - Leopard Douala
    (CMR, 2), (EGY, 3), (ALG, 7), (TUN, 3),        # Union Douala - Ismaily, MC Alger - CA Bizertin
    (SAF, 6), (NGA, 3), (GHA, 3), (MAR, 3),        # Sundowns - Julius Berger, Great Olympics - JS Massira
]
CAF_CUP = [
    (EGY, 4), (CMR, 4), (MAR, 4), (SAF, 8),        # Al Ittihad - Olympic Mvolye, DH El Jadida - Moroka Swallows
    (TUN, 4), (ALG, 5), (NGA, 4), (GHA, 2),        # Club Africain - JSK, Udoji United - Dawu Youngsters
    (ALG, 1), (EGY, 5), (SAF, 12), (TUN, 5),       # CA Batna - El Qanah, Umtata Bucks - Olympique Beja
    (MAR, 5), (NGA, 5), (CMR, 5), (GHA, 1),        # CODM Meknes - Gombe United, PWD Bamenda - Cape Coast
]


def structs(p, area, cave):
    """Write the three contests into the obj1 cave; returns (new cave end, [(1, struct offset)] for the continent)."""
    d2 = p.le.obj_bytes(2)
    euro = sacups.unique(d2, sacups.EUROCUP_HDR)
    cwc = sacups.unique(d2, sacups.CWC_HDR)
    cl = bytearray(d2[euro:euro + 47])
    cl[0] = CAFCL_ID
    defs = [(CAFCL_ID, cl, 39, CHAMPIONS_LEAGUE),
            (CAFCWC_ID, sacups.knockout16(d2[cwc:cwc + 28], CAFCWC_ID), 19, CUP_WINNERS_CUP),
            (CAFCUP_ID, sacups.knockout16(d2[cwc:cwc + 28], CAFCUP_ID), 19, CAF_CUP)]
    at = cave
    out = []
    for cid, body, name_at, lst in defs:
        assert len(lst) == 16 and len(set(lst)) == 16
        rel = area.add(NAMES[cid] + b'\0') - sacups.STR_BASE
        blob = bytes(body[:name_at]) + struct.pack('<II', rel, rel) + sacups.teams(lst)
        assert blob[5] + 5 == name_at and blob[7] + 7 == name_at + 8
        p.put(1, at, blob)
        out.append((1, at))
        at += len(blob)
    at = (at + 3) & ~3

    # international contests list (relocated by sacups): append the three cups
    lst, code = sacups.INTL_LIST[0]
    d1 = p.get(1, lst, 0x400)
    entries = []
    while d1[4 * len(entries):4 * len(entries) + 4] != b'\xff' * 4:
        entries.append(p.target(1, lst + 4 * len(entries)))
    entries += out
    new = at
    for k, (tobj, toff) in enumerate(entries):
        p.add_ptr(1, at + 4 * k, tobj, toff)
    at += 4 * len(entries)
    p.put(1, at, b'\xff' * 4)
    at += 4
    for off in code:
        p.retarget(1, off, 1, new)
    print(f'exe: CAF cups (ids {CAFCL_ID:#x}-{CAFCUP_ID:#x}) @ obj1+{out[0][1]:#x}, intl list -> obj1+{new:#x} '
          f'({len(entries)} entries)')
    return at, out
