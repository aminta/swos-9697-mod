# The career calendar (calendar contract C)

*Italian version: [calendar.it.md](calendar.it.md).*

This page describes how the mod reasons about the weeks of a career season. It covers the model, its single entry point, which piece owns which weeks, and the invariants the harness checks on every career menu. Design: MC, 13/11 (`internal/handoff/c-calendar-contract.md`).

## The model

- **Career week**: the calendar's week byte, 8 weeks a month, counted from January of the season's first year. A year is 96 weeks. `split.week_of` converts a date to a week.
- **Career day**: one entry of the game's own calendar (obj2). Each entry has its slot (0 = the league, 1..4 = the other contests), its week, its round and its played marks.
- **League unit**: the week of one league matchday of a division, byes included. They come from the pack and from the original exe's league structs (the header bytes 3 and 4 give the first and last week).
- **Window**: (kind, B, E, source). B is the first week the window is open, E its last (inclusive). Source is `data` (from the pack) or `default`.

## One entry point: `tools/cal.py`

Every piece that needs career weeks reads them through `cal.py`, never through its own copy of the week maths. The maths itself lives in `fport.py` (the fixture port, Motore's P3) and is not duplicated.

| Function | Returns |
|---|---|
| `season_start(pk)` | S, the season's first career week (the earliest league unit of any division) |
| `league_units(pk)` | the league units per division |
| `reserved(pk)` | the slot-4 reserved windows (= `fport.windows`, identical JSON on the 91 countries) |
| `transfer_windows(pk)` | the summer and winter windows of the country |
| `season_end(pk)` | (E, source): the week at whose end the country's season is over |
| `window_at(wins, week)` | (kind, w) with w = week - B, or None |
| `country(pk)`, `world(src)` | all of the above for one country / one career world |

## Who owns which weeks

| Weeks | Owner | Notes |
|---|---|---|
| League matchdays (slot 0) | the game + the season / world builders (`mkseason.py`, `careerworld.py`) | real midweek rounds share a weekend's career week at 8 weeks a month (MLS, Honduras, Peru, Colombia) |
| Slot-4 reserved windows | the fixture port (`fport.py`, `fpad.c`) | season-end play-offs (dplay, gplay ko_playoffs), stage titles, supercups, Coppa Italia Serie D. A static superset: B is never later than the real build advance |
| Transfer windows | `cal.py`, read by the CPU market (4.3) | per country. Real FIFA TMS dates from pack.json `transfer_windows`, otherwise the default: summer from S for 8 weeks, winter from S + 40 for 4 weeks (Davide's W, still open) |
| Season end | `cal.py season_end` | `native` (a phase runs at the career's season end), else the later of the last league unit / last reserved E (`league` / `reserved`). World 2026-27: 57 league, 27 native, 7 reserved |
| FIFA windows | none yet (4.5) | the kind exists so the table layout does not change |

The run-time table of windows (C2, CALW in obj4, 8 B a window) is linked only when a consumer needs it. The first consumer is the CPU market in 4.3.

## The invariants (C1-C4)

The same four rules are checked in two places:

- **Host**: `tools/hosttest/tests/test_calendar_lib.py` (Panchina). Its goldens are red on the reverted 4.0.5 bugs (NZ Grand Final, Libertadores q2, Serie D FINISH SEASON, early supercup) and green on the fixes.
- **Live, in every world scenario**: `swostest.py cal_check`, on every career-menu screen of `advance()`. It reads the game's own calendar from memory, with no exe code and no test switch. A violation FAILs the scenario; the result line shows `[cal: N checks (M C4 at the menu), 0 violations]`. `SWOSTEST_CALCHECK=0` turns it off for a debug run only.

| Rule | What must hold |
|---|---|
| C1 | the calendar is well formed: `count` entries of at least 8 bytes, weeks never decreasing |
| C2 | the league has at most two career days in one week (a third is a duplicated round). Other contests may be played in a block (a final four, the national team's finals): logged, never a FAIL |
| C3 | no career day is left ahead of the cursor in a week already reached |
| C4 | FINISH SEASON (careerFinished) is set exactly when no career day is ahead, on the screens that show the button and outside the season change |

C4 is also the **menu contract**: the career menu offers FINISH SEASON exactly when nothing is left to play.

## Open points

- Davide's W: the default lengths of the summer and winter windows (8 / 4 weeks).
- Data item for 4.3 (exactness rule): the real transfer windows of the 91 countries in their packs.
- C2 CALW: designed (per world x country, `end` entries for the per-country season end), linked with the market's hooks.
