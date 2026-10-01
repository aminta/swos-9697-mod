"""African club cups (step 1): CAF Champions League, CAF Cup Winners' Cup, CAF Cup.

Same layout as the South American cups (sacups.py): the Champions League copies the European Champions
Cup (16 teams, 4 groups of 4, then knockout; the real 1997 edition had a group stage too), the other two are
16-team two-legged knockouts. They appear as cup buttons of the Africa continent (preset competitions, career
world view) and in the international contests list.
Initial team lists (first season): 1996-97 final standings (1997 for Nigeria/Cameroon, file order of
africa.py); for Algeria, South Africa and Ghana (alphabetical files) the strongest clubs, with the real
1996-97 champions where SWOS has them (Manning Rangers, Obuasi Goldfields).
Step 2: the player's club enters them in career (sacups chain, D7/E092F 6..8) and the next season's lists come from
the standings at season end (sacups.qualify_hook). Not yet saved with the career (after a reload the world view
shows the 1997 lists until the season end recomputes them).
"""
import struct

import sacups

CAFCL_ID, CAFCWC_ID, CAFCUP_ID, CCC_ID = 0x76, 0x77, 0x78, 0x79
NAMES = {CAFCL_ID: b'CAF CHAMPIONS LEAGUE', CAFCWC_ID: b'CAF CUP WINNERS CUP', CAFCUP_ID: b'CAF CUP',
         CCC_ID: b'CONCACAF CHAMPIONS CUP'}
ALG, SAF, GHA, EGY, MAR, TUN, NGA, CMR = 42, 69, 79, 52, 53, 54, 56, 58
MEX, USA, SLV, CRC = 60, 73, 51, 47

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

# CONCACAF Champions' Cup (1.2): 16-team knockout, first season = strong clubs of the 4 countries in the spirit of the
# 1997 edition (Cruz Azul, Guadalajara, LA Galaxy, DC United, Saprissa...); consecutive pairs from different countries
CONCACAF = [
    (MEX, 10), (USA, 17), (SLV, 5), (CRC, 11),     # Necaxa - DC United, Alianza - Saprissa
    (USA, 6), (MEX, 15), (CRC, 0), (SLV, 33),      # LA Galaxy - Cruz Azul, Alajuela - Luis Angel Firpo
    (MEX, 7), (SLV, 29), (USA, 14), (CRC, 6),      # Guadalajara - FAS, Tampa Bay - Herediano
    (SLV, 4), (CRC, 8), (MEX, 0), (USA, 5),        # Aguila - Puntarenas, America - Kansas City
]

# (id, team list, groups (Champions Cup clone) or knockout, league ranks taken at season end, continent,
#  euro cup of the same rank for trophy/prize: 0 Champions Cup, 1 Cup Winners' Cup, 2 UEFA)
CUPS = [
    (CAFCL_ID, CHAMPIONS_LEAGUE, True, (1, 2), 'africa', 0),
    (CAFCWC_ID, CUP_WINNERS_CUP, False, (3, 4), 'africa', 1),   # no readable national cup winners: ranks 3-4
    (CAFCUP_ID, CAF_CUP, False, (5, 6), 'africa', 2),
    (CCC_ID, CONCACAF, False, (1, 2, 3, 4), 'north_america', 0),
]


def structs(p, area, cave):
    """Write the CUPS contests into the obj1 cave; returns (new cave end, [(1, struct offset)] in CUPS order)."""
    d2 = p.le.obj_bytes(2)
    euro = sacups.unique(d2, sacups.EUROCUP_HDR)
    cwc = sacups.unique(d2, sacups.CWC_HDR)
    defs = []
    for cid, lst, groups, *_ in CUPS:
        if groups:
            body = bytearray(d2[euro:euro + 47])
            body[0] = cid
            defs.append((cid, body, 39, lst))
        else:
            defs.append((cid, sacups.knockout16(d2[cwc:cwc + 28], cid), 19, lst))
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
    print(f'exe: extra club cups (ids {CUPS[0][0]:#x}-{CUPS[-1][0]:#x}) @ obj1+{out[0][1]:#x}')
    return at, out


# season end (sacups.qualify_hook table): (country, league rank) per list position, same pattern as the 1997 lists.
# The Cup Winners' Cup takes ranks 3-4: the game keeps no national cup winners we could read (simplification).
def _q(lst, ranks):
    seen = {}
    out = []
    for c, _ in lst:
        out.append((c, ranks[seen.get(c, 0)]))
        seen[c] = seen.get(c, 0) + 1
    return out


def continents(caf):
    """{continent: [(1, struct offset)]}: cup buttons for countries.patch."""
    out = {}
    for (cid, lst, groups, ranks, cont, kind), ptr in zip(CUPS, caf):
        out.setdefault(cont, []).append(ptr)
    return out


def career_info(caf):
    """What sacups needs: contest offsets (slot-3 chain, D7 = 6, 7, ...), their euro rank and the qualification entries."""
    offs = [off for _, off in caf]
    return {'structs': offs, 'kinds': [c[5] for c in CUPS],
            'q': [(off + (47 if c[2] else 27), _q(c[1], c[3])) for c, off in zip(CUPS, offs)]}


def intl_list(p, caf, at):
    """Append the CUPS contests to the international contests list (relocated by sacups)."""
    lst, code = sacups.INTL_LIST[0]
    d1 = p.get(1, lst, 0x400)
    entries = []
    while d1[4 * len(entries):4 * len(entries) + 4] != b'\xff' * 4:
        entries.append(p.target(1, lst + 4 * len(entries)))
    entries += caf
    new = at
    for k, (tobj, toff) in enumerate(entries):
        p.add_ptr(1, at + 4 * k, tobj, toff)
    at += 4 * len(entries)
    p.put(1, at, b'\xff' * 4)
    at += 4
    for off in code:
        p.retarget(1, off, 1, new)
    print(f'exe: intl list -> obj1+{new:#x} ({len(entries)} entries)')
    return at
