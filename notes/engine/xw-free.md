# XW: team-file numbers free in every namespace (XW-F, measured 11/11/2026)

This corrects xw-design.md "Lifting the 19". That section counts six numbers free in both worlds (145..148, 162, 189).
MC fixes the text on xw-42. The measured count, binding (MC 11/11), is **one: 189**.

## Where the numbers come from

Measured on a built exe: c/HTW and c/REL42strmap4, the release recipe with world5tm-s1rank-int3 and every SEASON_PACKS
pack. A namespace is the set of team files one world loads:
- TEAM.nnn holds the 1996-97 game, the base world (Europe 1984-85) and the global packs.
- TMWn.nnn holds world n's own files.

In the range 101..219:

| numbers | used by |
|---|---|
| 101..144, 180..185 | TEAM: Europe 1984-85 |
| 145 | TEAM: italia-1947-48 (global tourney) |
| 146 | TEAM: world-cup-1934 (global tourney) |
| 101..143, 149..188, 210..218 | TMW5: World 2026-27 (162 = Brazil's states; 149 too) |
| 190..194 | TMW5: the guest files (guests.py); with 195..199 also mkseason.POOL_IDS, reserved |
| 200..209 | reserved: mkseason.WMENU (CLASSIC CAREERS world entries) |
| 219 | reserved: the registry's end (xw.c XW_FIRST - 1) |
| 147, 148 | reserved: packs/_template_tourney (the guide's slot for the next tourney pack, MC 11/11) |
| **189** | **free in every namespace** |

## Used in one namespace only

These are never free. XW borrows such numbers per contest.
- 144 is TEAM.144 (1984-85). With S7 it is also TMW5.144 (Serie D), the second user of 144 in another namespace.
- Fine inside each world. A 1984-85 club picked into a 2026-27 game is the borrowing case.

## The design

It holds (MC 11/11). The fixed pool is 220..238 (19) + 189 = 20 visitor files without borrowing, instead of 25.
Borrowing covers the rest.

## The test

tools/hosttest/tests/test_xwfree.py `test_xw_free_files` derives the free set from the build's DATA file names and
the reserved ranges, each read from its owner (mkseason.POOL_IDS / WMENU, xw.c XW_FIRST, the template's pack.json).
- It asserts the set is not empty.
- Once xw.c defines `XW_FREE_FILES {...}`, it asserts the set equals that constant.
- A control adds a TMW5 file on the lowest free number, which must take that number away.
- A future pack that takes 189 makes the set empty, so the test FAILs.
