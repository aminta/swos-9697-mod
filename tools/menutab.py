"""The team-choice menu's competition tables, for countries with more than 10 competitions (World 2026-27: Italy's
14 divisions; VIEW WORLD adds the cups: 16+).

SelectTeamsFinalMenu puts every division (and, in VIEW WORLD, every cup) of the chosen country into one list:
leaguesPtrTable (dd x 10: the competition's struct) and leagueNumbersTable (dw x 10: its division index), read back
by the entry's index when the player picks it. Both are 10 slots and nothing checks the count: the 11th-14th
pointers went over leagueNumbersTable[0..7], the 11th-14th numbers over isContestContinentalCup, isCountryNumber,
countryNumber and gotCountryName (found 2026-10-19 on w2627-latest; ref/swos.asm ~63200-63880, data ~207901).

patch(): both tables move to SLOTS-entry copies in the obj2 area (static data, there in every build); every fixup
into them is retargeted (6 in the original game: 2 at the build of the list, 4 at the pick), their count asserted.
No loop of the game compares against the 10: the list's length is numLeaguesInCountry. (The menu itself shows
entries 11..20 only: more divisions need the level -> group step.)
"""
import re
import struct

SLOTS = 32
SITES = 6


def _find(p):
    """obj2 offsets of leaguesPtrTable, leagueNumbersTable: `mov [A3], offset leaguesPtrTable; mov [A4], offset
    leagueNumbersTable` (the list's build in SelectTeamsFinalMenu)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xc7\x05' + pk(r['A0'] + 12) + rb'(.{4})\xc7\x05' + pk(r['A0'] + 16) + rb'(.{4})',
                                d1, re.S)]
    def tg(off):
        try:
            return p.target(1, off)
        except AssertionError:
            return None
    pairs = {(tg(x.start(1)), tg(x.start(2))) for x in m}
    pairs = [(a, b) for a, b in pairs if a and b and a[0] == 2 and b == (2, a[1] + 40)]   # (dd x 10, then dw x 10)
    assert len(pairs) == 1, pairs
    return pairs[0][0][1], pairs[0][1][1]


def patch(p, area):
    ptrs, nums = _find(p)
    new_p = (area.add(bytes(SLOTS * 4 + 4)) + 3) & ~3
    new_n = new_p + SLOTS * 4
    n = 0
    for f in p.le.fixups():
        if f[0] != 1 or f[3] != 2 or f[4] is None:
            continue
        if ptrs <= f[4] < ptrs + 40:
            p.retarget(1, f[1], 2, new_p + f[4] - ptrs)
        elif nums <= f[4] < nums + 20:
            p.retarget(1, f[1], 2, new_n + f[4] - nums)
        else:
            continue
        n += 1
    assert n == SITES, n
    print(f'exe: team-choice competition tables obj2+{ptrs:#x} / +{nums:#x} (10) -> obj2+{new_p:#x} / +{new_n:#x} '
          f'({SLOTS}; {n} fixups)')
