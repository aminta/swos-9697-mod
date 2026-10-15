# World 2025-26 — real squads: bigger career squads and our own squad pipeline (study, 2026-10-15)

Study only (feasibility, design, estimate); nothing implemented. Two questions from Davide:
1. can the club managed in a career have 22-30 **real** players instead of 16 + generated ones?
2. can the 2025-26 squads come from our own sources (Transfermarkt or similar) instead of the SWOS 2020 team files,
   with a tool that can be re-run for 2026-27?

Terms: **record** = one 684-byte club entry of a TEAM.nnn file (16 players of 38 bytes from +76); **managed club** =
the club the human manages in the career; **CPU club** = every other club; **filler** = a player the game invents.
Addresses are labels of `ref/swos.asm` (ITA/ENG offsets differ; find them with `addrmap.py` when patching).

## 1. Career squads in the engine

### Facts
- **The managed club holds 32 players.** `careerTeam db 1292` = one TeamFile (684) + 16 more PlayerFile (16 x 38 =
  608): slots 0-15 are the record's players, slots 16-31 follow contiguously. `careerNumPlayers dw` (right after it)
  is the count; `currentMatchPlayers dw 16 dup` (32 bytes, right before it) is the squad order (squad position ->
  slot). Both sit between `careerFileBuffer` and `g_numSelectedTeams`, i.e. **inside the .CAR fixed part**: a squad of
  up to 32 is already saved and loaded by the game, no save-format change.
- **CPU clubs have 16, always.** `GetPlayerAtIndex`: the managed club goes through `currentMatchPlayers`, the current
  match team through `playerPositions`, any other club through `TeamFile.playerNumbers` and an index >= 16 hits the
  game's `int 3; jmp $` trap. CPU records only exist as 684-byte records (team files, `tmdFileBuffer` in the .CAR).
- **Where the 'fake' players come from** (not a pool file): `cseg_52588`, called by `ShowPlayMatchMenu` and
  `PlayTrainingGame` (not for a national selector):
  - counts available goalkeepers (`cseg_3A110`) and fit outfield players (`cseg_3A2CE`) over `careerNumPlayers`;
  - fewer than 2 goalkeepers -> adds a goalkeeper; fewer fit outfield players than 11 + subs - 2 (22 + subs - 2 in
    training) -> adds outfield players with a random position 1..7 (RB..A), **while careerNumPlayers < 30**;
  - surplus (more than 2 keepers / enough outfield) and a generated player present -> `cseg_52EA6` removes him.
  - `cseg_52956` puts the new player in the first free slot, appends it to `currentMatchPlayers`,
    `careerNumPlayers += 1`, wage via `cseg_5E345` (table `dseg_D6BA6`, one dword per slot).
  - `cseg_52A3E` fills him: name from `cseg_52B6A` = first name of a random player of a random club of the same
    country + surname of another one (nationality and skin copied from the donor); **skills dword (bytes 28-31) = 0,
    price (byte 32) = 0**, shirt number 16, flag bit 1 of byte 26 (`positionAndFace`) = 'generated'.
  So the fillers are temporary emergency players with zero skills: they appear when injuries/suspensions leave the
  squad short and go away again when it is full. With 22+ real players they would almost never appear.
- **Not the squad, the market:** `FillCareerTeamPlayers` (from `InitializeNewSeason`) fills the *home transfer list*
  `homeMarketPlayers` (max 25) with random players of other clubs of the same country in the managed club's price
  range (`AddCareerTeamPlayer` -> `AddPlayerToCareerContest`). The *foreign* list comes from `POOLPLYR.DAT`
  (`LoadPoolplyrDat`, 52200 B = 900 `PoolPlayer` of 58 B: team id, ordinal, team name, PlayerFile;
  `AddRandomForeignMarketPlayer`). The world 2025-26 still uses the 1996 POOLPLYR.DAT (SWOS 2020 ships a 2025_26
  one): 1996 players on the foreign market are the other 'fake' players a 2025-26 manager sees.
- **Changing club drops slots 16-31.** `cseg_5A6A1` (from `cseg_942F2` <- `ContinueCareerNextSeason` when a job offer
  was accepted) writes the first 16 of the career order back into the old club's record (`cseg_94193` -> tmd buffer)
  and sets `careerNumPlayers = 16`. A managed club's extra players live only while the human manages it.
- **Limits:** buffer 32 slots; fillers stop at 30; `cseg_547AC` (from `RemovePlayerFromTeam`, transfers) tests 32.
  The squad screens already scroll past 16 (squads grow by transfers in the original game).
- Not traced in this study: the exact point where the managed club's 16 are first copied into `careerTeam` for a new
  career and for a new job (callers at swos.asm lines ~25056-25133 / 38195 / 54359-54403 are the candidates), the
  size of `dseg_D6BA6` (must be 32 dwords) and the transfer purchase cap.

### Verdict
**Feasible, for the managed club only.** A CPU club stays at 16 (no engine room; making CPU records bigger would
touch every team-file path). The managed club can start with up to 30 real players (keep 30 = the fillers' cap; 25-28
leaves room for purchases).

### Design (recommended): XTRA files + one hook
- **Data:** next to each TEAM.nnn of a world, an optional `XTRA.nnn`: for record k of the team file, a block of up
  to 14 PlayerFile records (38 B, same bytes as in the record) + a count. Per country it is small (20 clubs x 14 x 38
  = ~10.6 KB); the hook reads only the managed club's file (or the whole file into a spare buffer, as the big team
  buffer already does).
- **Hook:** right after the game fills `careerTeam` with the club's 16 (new career, new job; NOT at every
  `InitializeNewSeason`, the squad persists across seasons): if `careerNumPlayers == 16` and the club has a block,
  copy its players to slots 16.., append 16.. to `currentMatchPlayers`, set `careerNumPlayers`, call `cseg_5E345`
  per new slot (wages). Mark 'extras loaded' in a spare byte of the career state so a load or a season start never
  adds them twice.
- **Builder:** mkseason writes XTRA.nnn from the same players.csv: rows 1-16 of a club -> the record (as today),
  rows 17-30 -> its XTRA block (only for packs that enable `extended_squads`). The 16 in the record are the club's
  most-used players, so CPU clubs play with their real first choices.
- **POOLPLYR.DAT per world:** same pipeline, 900 real players of clubs outside the world (Russia, Canada, Korea, ...),
  under a per-world file name (string patch in `LoadPoolplyrDat`, which only runs in career).
- Cheaper variant (1 session, not recommended): hook `cseg_52A3E` so a filler takes the next real reserve of the
  club (name, nationality, skills, price from XTRA) instead of a random name with zero skills. Real reserves then
  appear only in emergencies and vanish again.

### Risks
- Returning to a club later re-adds its XTRA players, even ones the human sold while there (keep a small per-world
  'sold' list in the .CAR trailer, or accept it).
- Extra players are invisible to the transfer market and to other clubs (CPU clubs never trade anyway).
- Wage totals rise with a 28-man squad: club finances need a check (balance after one season, harness).
- A hook in the job-change path must coexist with the mod's season-end hooks (`cseg_91428` and the world fixes).
- National selector mode must be left alone (`isNationalSelector`, it uses `careerNumPlayers` = 20).

## 2. Our own squads (independent of SWOS 2020)

### What the game needs per player (measured on the 1996-97 files and SWOS 2020 2025-26, ~25,000 players each)
| Byte | Meaning | Rule |
|---|---|---|
| 0 | nationality | game number 0-152 (`shortCountryNames`, 153 entries) |
| 2 | shirt number | the files hold 1-16 (squad slot); the vanilla game swaps numbers with players (line ~52066), real numbers only make sense with SWOS++ (0-255) |
| 3-25 | name | upper-case ASCII, no accents (none in either data set), 22 chars max, full name ('BUKAYO SAKA'); long ones shortened ('M. DAL COMPARE', `c1c2.swos_name`) |
| 26 | position bits 5-7, skin bits 3-4 | G RB LB D RW LW M A; skin 0 light, 1 ginger, 2 dark (the game has only these 3 faces, no hair) |
| 28-31 | 7 skills | nibbles pa / ve he / ta co / sp fi, value 0-7, bit 3 = key skill |
| 32 | price | **outfield: price = sum of the 7 skills, in 100% of the records of both sets** (so <= 49). Goalkeepers: skills 0, price = keeper quality (mean 11) |

- Mix per 16: G 2.3, RB 1.2, LB 1.2, D 3.5, RW 1.1, LW 1.1, M 4.0, A 3.7 (1996-97).
- Skill profile of the original (mean value, key skill share): RB/LB tackling + speed (key 97/89%), D heading +
  tackling, RW/LW ball control + speed, M passing + tackling, A heading + finishing; the others ~1. The original gives
  **2 key skills** to 78% of players; SWOS 2020 gives none to 93%.
- Price distribution (1996-97, step 5): 0-4 14%, 5-9 20%, 10-14 30%, 15-19 22%, 20-24 8%, 25-29 3%, 30+ 3%; SWOS 2020
  2025-26 is a bit stronger (30+ 7%).

### Sources
| Source | Coverage 2025-26 | Data | Licence / terms | Use |
|---|---|---|---|---|
| Transfermarkt (site) | every league we need (all ~1300-1600 clubs) | name, sub-position (Centre-Back, Right Winger...), shirt number, nationality (+2nd), birth date, market value, minutes | terms forbid bots / automated copying and redistribution without written consent; no public API | best data; **only with written permission** (Davide asks); without it only small manual saves (as MLS 1997, 10 pages) |
| dcaribou/transfermarkt-datasets (GitHub, Kaggle) | ~40 competitions, ~400 clubs (big European leagues + cups), weekly | players (position, sub_position, citizenship, value, birth date), appearances, valuations | tagged CC0, but the data are scraped from Transfermarkt | big-league strength (values, minutes); ask/credit both the author and Transfermarkt |
| Wikipedia club pages ('Current squad') | nearly all top flights, most 2nd tiers; weaker for Serie C groups, NPL, Central America | name, number, GK/DF/MF/FW, nationality flag, coach | CC BY-SA 4.0 (facts + attribution); API allowed with user agent and rate limit | **primary for names/roles/numbers**: the revision at a fixed date makes it deterministic |
| EA SPORTS FC 26 (ea.com ratings, sofifa, Kaggle dumps) | 17,000+ players, ~750 licensed clubs | overall + ~30 attributes (pace, passing, heading, tackling, ball control, finishing...) | EA's data; Kaggle 'CC0' labels cannot grant EA's rights | **best skill source**: used privately to compute SWOS skills (derived values, the raw data never shipped); credit EA / sofifa; Davide decides |
| FBref | big leagues | minutes, starts | Sports Reference terms limit bots; stats partly Opta | optional: squad order |
| SWOS 2020 2025-26 | 1282 league clubs | full SWOS records | community DB, used today with credit | cross-check only (independence); faces could be kept by name if Davide agrees |

### Chosen pipeline (private converter, deterministic)
`internal/world2526/squads/` (nothing of it in the repo): `fetch.py`, `build.py`, `maps/`, `raw/`, `out/`.
1. **Snapshot**: one parameter `--season 2025-26 --as-of 2025-09-02` (day after the summer window). Every fetch
   goes to `raw/<source>/<as-of>/...` and is never fetched again; Wikipedia by revision id at the date (`oldid`
   recorded in a manifest with hashes). The build reads only `raw/`: same input -> byte-identical output.
   **2026-27 = a new `--as-of 2026-09-01` snapshot + rerun** (plus a diff report: transfers, new clubs).
2. **Club mapping**: `maps/clubs.csv` world club key (from mkworld2526) -> Wikipedia title, Transfermarkt id, FC
   team id. Built once by name matching + hand fixes (the slow part, ~1500 rows); reused every season.
3. **Players**: merge sources by (club, normalised name, birth date): names/numbers/roles from Wikipedia (or
   Transfermarkt with permission), fine position from Transfermarkt sub-position or FC position, strength from FC
   (else market value), order by minutes (2024-25, or 2025-26 up to the snapshot) / FC overall.
4. **Mapping tables** (`maps/`, versioned with the converter):
   - `positions.csv`: Goalkeeper G; Right-Back RB; Left-Back LB; Centre-Back D; Right Winger / Right Midfield RW;
     Left Winger / Left Midfield LW; Defensive / Central / Attacking Midfield M; Centre-Forward / Second Striker A.
     Wikipedia-only (GK/DF/MF/FW): G/D/M/A, full-backs and wingers taken from FC, else from the template's slots.
   - `nations.csv`: FIFA code -> game number (0-152); first (sporting) nationality; a missing nation -> the closest
     existing one, listed in the build log.
   - `names.csv`: overrides (known short names: 'VINICIUS JUNIOR', 'RODRI'), then `swos_name` (NFKD -> ASCII,
     ß -> SS, upper, 22 max, 'J. SURNAME' when longer).
   - `faces.csv`: skin per player only by explicit list (FC face data if available, else hand-made overrides);
     default light. Kept as a separate, reviewable file.
5. **Skills** (proposal, FC attributes):
   pa = short passing / vision; ve (shooting) = shot power / long shots; he = heading accuracy (+ jumping);
   ta = standing / sliding tackle, interceptions; co = ball control / dribbling; sp = sprint speed / acceleration;
   fi = finishing. Each player: target skill sum S = f(overall) (piecewise linear, fitted so the 2025-26 world's
   distribution matches the game's: mean ~13, top stars 38-45, cap 49), split over the 7 skills in proportion to the
   player's own attribute profile, rounded to 0-7 with the sum preserved; key skills = the player's 2 best (as the
   original). Goalkeepers: skills 0, price = f(GK overall). Price = S. No FC data: S from market value (log scale,
   per league) with the same curve; no value either: mkseason `calibrate` from the club's strength.
6. **Calibration** (the mod's rule): per club print the first-11 skill sum and price next to the real 2024-25 /
   2025-26 table; adjust the curve per league (never by whole skill levels with a small price shift: that was the
   1947-48 flaw); then simulated seasons in the harness for ~5 leagues (champion and bottom clubs roughly right).
7. **Output**: the world pack in mkseason's `explicit` format (players.csv with position, number, nat, skin, the 7
   skills, price; 16 rows -> the record, rows 17-30 -> XTRA when extended squads exist) + a per-world POOLPLYR.DAT.
   mkworld2526 switches from method `records` to `explicit`; mkseason itself never depends on the source.

### Legal and credits
- Raw pages, dumps and ratings stay in `internal/`; the repo gets only the converted packs (as for DaniSwos'
  1984-85 database) and only after Davide's ok.
- Davide asks permission where needed (Transfermarkt; the dcaribou author; EA data use) and credits every source in
  the release notes and README: 'Wikipedia contributors (CC BY-SA 4.0)', Transfermarkt, dcaribou/transfermarkt-
  datasets, 'ratings derived from EA SPORTS FC 26 (sofifa.com)', SWOS 2020 if faces are reused.

## Open questions for Davide
1. Squad size of the managed club: 25 (UEFA list size) or up to 28-30? CPU clubs stay 16 — OK?
2. Sources: ask Transfermarkt for written permission? Use EA FC 26 ratings for the skills (privately, credited)?
3. Snapshot date: start of season (2025-09-02, after the window) or end of season?
4. Skin: only from an explicit list (FC faces / hand overrides), default light — or keep SWOS 2020 faces by name?
5. Shirt numbers: slot numbers 1-16 (vanilla) or real numbers (meaningful only with SWOS++)?
6. Key skills: 2 per player as the original 96/97, or none as SWOS 2020?
7. Foreign market: a 2025-26 POOLPLYR.DAT per world (900 real players of clubs outside the world)?

## Estimate (sessions)
| Part | Sessions |
|---|---|
| 1a. Trace the squad-load point (new career, new job), wage table size, purchase cap | 1 |
| 1b. XTRA format in mkseason, hook stub, harness scenario (squad of 28 shown, match, save/load, job change, return) | 1-2 |
| 1c. Per-world POOLPLYR.DAT (builder + file-name patch + harness) | 1 |
| 2a. Fetch/cache layer + manifest (Wikipedia revisions; TM/FC once permitted) | 1 |
| 2b. Club mapping ~1500 clubs (matching + hand fixes) | 2 |
| 2c. Mapping tables (nations, positions, names, faces) | 1 |
| 2d. Skill model + calibration against the game's distributions | 1-2 |
| 2e. Pack output (explicit + XTRA), mkworld2526 switch | 1 |
| 2f. Strength check (tables + simulated seasons) | 1-2 |
| **Total** | **10-13** (part 1: 3-4; part 2: 7-9) |
| Later: 2026-27 (new snapshot, rerun, new clubs in the mapping, strength check) | ~1-2 |

## 3. Every club with 24+ players (follow-up question, 2026-10-15)
Davide: can ALL clubs have 24 (e.g. a classic tourney 'Serie A 2023-24' with every real squad)?

### Why not by making the record bigger
16 is wired through the engine: the 684-byte record (~70 immediates 684/683/2ACh in swos.asm), `playerNumbers[16]`,
loops 'for 16 players' (`UpdatePlayerInjuries`: `mov D2, 15`), random picks `and 0Fh` (`AddCareerTeamPlayer`),
the `GetPlayerAtIndex` trap for index >= 16, `g_selectedTeams db 68400` (= 100 x 684), the TEAM.nnn / .CAR /
competition save formats, and every outside tool (SWOS 2020 files, editors, SWOS++). A 24-player record = rewrite
of all of that: not realistic (15+ sessions, high risk, every existing team file incompatible).

### What works: squad of 24, 16 called up per match ('convocati')
A match only ever uses 16 (11 + 5 on the bench): the engine's 16 can be the **matchday squad**, as in real
football; the other players wait in an extension table outside the record.
- **Data:** `XTRA.nnn` as in part 1, but for every club of the file (rows 17-30 of players.csv). In a season or a
  classic tourney (<= 100 clubs: 20 x 10 x 38 = ~7.6 KB for Serie A) the table sits in a mod page next to
  `g_selectedTeams`, one block per selected team.
- **Call-up hook** before each match day: per club, the 16 called up are written into the record's 16 slots, the
  others go to the table. CPU clubs: a fixed rule (squad order = importance; replace the unavailable by the next of
  the same role; optional rotation), or for a historic tourney the **real matchday squads** from a per-round file.
  Note: the engine does not even record injuries of CPU clubs (`UpdatePlayerInjuries` returns for TEAM_COMPUTER),
  so today a CPU club always fields the same 16.
- **Human club:** in career the managed club already has 32 slots and its squad screen (part 1). In a season /
  tourney the human club is a 684-byte record too -> a new 'SQUAD 24' screen to swap players between the 16 and the
  reserves (the mod already builds menus), or v1 automatic call-up like the CPU.
- **Top scorers** are stored as (team, slot) and shown with `GetPlayer(team, slot)`
  (`CompetitionTopGoalScorersInit`, `TopGoalScorersBeforeDrawCommon`): when a scorer leaves the 16 his entry must
  follow him (a virtual slot 16+ that those two display sites resolve in the table; same for the season best scorer).
- **Injuries / cards** of human players in the stands: ticked by the hook per match day.
- **Saves:** season / preset / DIY saves have their own writers (`SaveContest` -> `SaveDIYFile`,
  `SavePresetCompetitionFile`, season); the table and the call-up state need a trailer there too, as the .CAR has.
- Rejected alternative: patch `GetPlayer` so slots 16-23 of any club read the table (`@@look_up_team` path; the
  managed club already reads 32 from careerTeam). Cleaner data, but every loop that walks the 16 raw slots would
  need an audit.

### Estimate
| Part | Sessions |
|---|---|
| Trace the match-day point, call-up hook for CPU clubs, scorer remap, save trailer (season/tourney) | 3-4 |
| 'SQUAD 24' screen for the human club (season/tourney) | 2-3 |
| Real per-round call-ups for a historic tourney (data + file format) | 1-2 |
| Career worlds: table for every club (~1500 x 8-14 x 38 = 0.45-0.8 MB), job change, .CAR trailer | 2-3 |
