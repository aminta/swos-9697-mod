# World 2026-27: mid-season split and per-division meetings (tools/split.py)

Squads session, 2026-10-18. Branch `split` from world-2025-26. The spec is in the private
`internal/world2526/formats2627.md`, and the data in the data session's `formats_data.SPLIT` / `GAMES`.

## Pack keys (mkseason.splits)
- `split` on the league (one-division country; for a multi-division country it applies to division 1) or on
  `divisions[i]`: `{"after": 33, "home": "balance", "groups": [{"places": [1, 6], "rounds": "single",
  "points": "full"}, ...]}`.
  - `after`: the match days before the split, a whole number of meetings (Scotland 33 = 3 x 11).
  - `rounds`: `single`, `double`, `triple`, `quadruple` (Latvia 1996: the bottom 4 meet four more times) or `none`
    per group; several round robins alternate home and away.
  - `points`:
    - `full`;
    - `half_up` (Romania, Greece 5-8) or `half_down`, both with "points before rounding" as the first tie-break;
    - `reset` (Malta);
    - `h2h_half` (alias `half_down_h2h`, Moldova): half the points won against the group's clubs before the split,
      rounded down, at most 8 clubs.
  - `home` for a single round after the split:
    - `balance`: the club that hosted the other fewer times, so every pair ends 2 + 2;
    - `reverse3`: the club that was away in their 3rd meeting (Northern Ireland);
    - `seeded` (default): a balanced calendar, the extra home games to the better placed.
    A double round is that calendar mirrored.
- `stages` (Malta): `{"stages": [split, split, ...]}`. Each stage is a split of the table at its `after` day
  (cumulative), plus `"reset": true` (every figure from 0: played, W/D/L, goals, points) and `"keep": "opening"`
  (the table just before the reset stays in the state for the title play-offs: the row by place at DIY+20Dh+102,
  then the points by place, words, at +22).
- `games` on a division: its own meetings in the season. The league struct has one `games` byte for every division
  (Scotland's lower divisions: 4).
- Even divisions of at most 24 clubs. At most 64 match days per split league (the state lives at the end of the
  weeks table).

## Engine (swos.asm; obj1 offsets differ per language: found by pattern, all four checked)
- A league runs in DIY_competitionStart.
- cseg_8F1F2 sets up a league struct's division in DIY (the career league through cseg_883B8's `jz`, and the
  season-end simulation cseg_3ABB2). It ends with cseg_2653B: [5Dh] meetings, [5Fh] cycles left, [1C3h] days,
  then cseg_2730A spreads the days' weeks from week [37h] to [38h] into +1CDh (a byte per day).
- Every match = cseg_89758 (the pairing) + cseg_8922B (the counters: [1C9h] matches today, [1BFh] day done,
  [1C1h] day, [2Eh] its week, [5Fh] = 0 when the stage is over) + cseg_883DD (the sort into +6Dh).
  These are used by the career, the season-end simulation, the calendar builder cseg_8B8D9 and cseg_8EF7B
  (the computer's matches up to the career club's).
- The career calendar (dseg_DB3E6) holds one 22-byte block per league day, with only the career club's match
  (+0Ah: 1 = at home, 2 = away; teamControls 1 = the computer's club).

## Hooks
| Site | Stub | What it does |
|---|---|---|
| cseg_8F1F2 start (`mov ax, [D0]`) | sp_div8f | Keeps the division: D7 is a loop counter by the routine's end. |
| cseg_8F1F2 `call cseg_2653B` | sp_init | Clears an old mark. For a division in SP_TAB (world byte, team file, division, clubs): a fresh state; [5Dh] = [5Fh] = meetings + 1, so the stage does not end at the split; [1C3h] = days before + after; the weeks spread again. |
| cseg_89758, before its home / away test | sp_pair | From day `after`: our calendar (places to rows). The first such call, unless from the calendar builder, freezes the groups from +6Dh, applies the points rule, sorts and rewrites the career calendar's post-split blocks. |
| cseg_8922B, after the played counts | sp_count | Day counters for any number of matches a day (groups of different sizes, byes); the stage ends after the last day. |
| cseg_883DD's last `jns` | sp_sort | After the engine's sort: a stable partition into the groups, then the "points before rounding" tie-break. +6Dh is always the final table in place order, so dplay / gplay read it unchanged. |
| cseg_8EF7B's first `call cseg_89758` | sp_cpu | When the career club plays no more on this day after the split (a bye in an odd group, a shorter group), only the rest of the day is played. Otherwise cseg_8EF7B ran on into the next day up to the career club's match, its block was then played twice, and the season stuck on its last league block. |
| cseg_88CBB `add word [esi+1BDh], 1` | sp_res | Head-to-head points per pair before the split. Installed only with `h2h_half` groups. |

The state (166 bytes) sits at DIY+20Dh, the end of the weeks table: magic FEh 50h, entry, frozen, place to row,
group of each row, points before the split, head-to-head. It is saved with the league slot (733h).

## Odd leagues (tools/oddtables.py, its own commit, main-able)
- The game's pair tables for an odd size (5..23 clubs) are not rounds. The engine counts n // 2 pairs as a day,
  and many of those days have a club twice.
- In careers the calendar builder then wrote two of the career club's matches into one block, which overran the
  next one: int 3 at cseg_8B8D9+A0 at the next season. Italy 1947-48 had irregular match days.
- The tables are rewritten in place as rounds: one club at rest each round, at most 3 home or away running.
  It runs with mkseason.odd_leagues, so no hooks are needed.

## Bugs met (do not repeat)
- Not in the rows. cseg_26395 clears the rows' figures but not their team dword, and some routines walk all
  64 rows: state bytes in rows 48-63 crashed the next season (`No byte handler for write to ffff0003`).
- The game's sort uses every register: pushad around it, not only the D0..A6 pseudo registers.
- cseg_8F1F2's D7 is not the division at its end.
- teamControls 1 = the computer's club (the calendar record's home / away came out inverted).
- A cup copied into DIY (443h) leaves the league's tail: every hook checks DIY+0 = 0 (a league).

## Tests (swostest, private data internal/world2526/world5tm)
- `world_split_reverse3` (Northern Ireland), `world_split_odd` (Bulgaria: groups of 5 with byes),
  `world_split_three` (Greece), `world_split_none` (Czech Republic), `world_split_stages` (Malta), `world_odd_league`
  (New Zealand 11 on a full odd build: 22 days, 20 matches each, two seasons).
- `world_split_single` (Scotland 33 + 5, balance, at ST. MIRREN), `world_split_double` (Austria 22 + 10, at
  HARTBERG), `world_split_halved` (Romania 30 + 10, half_up, at BOTOSANI), `world_split_h2h` (Moldova 21 + 10,
  h2h_half, at PETROCUB). SPLIT_BUILD reuses a build.
- Each plays two seasons and checks:
  - the days and everyone's matches;
  - the groups in place order;
  - every club's points by the rule;
  - the career club's post-split fixtures (in its group, home side by the balance rule).
- swostest also draws the menu from memory (linAdr384k + g_fadePalette) when the window cannot be captured
  (locked screen).
