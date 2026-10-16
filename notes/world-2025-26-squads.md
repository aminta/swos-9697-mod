# World 2026-27 — real squads: bigger career squads and our own squad pipeline (study, 2026-10-15/16)

Study only (feasibility, design, estimate); nothing implemented. Two questions from Davide:
1. can the club managed in a career have 22-30 **real** players instead of 16 + generated ones?
2. can the squads come from our own sources instead of the SWOS 2020 team files, with a deterministic tool that can
   be re-run for the next season?

**Decision (Davide, 2026-10-16):** the historic career world is **season 2026-27** (branch and file names keep
'2025-26'); squads from **Transfermarkt at the end of the summer 2026 window**, fully independent of SWOS 2020 (no
SWOS 2020 records, kits, ratings or faces); coaches from Transfermarkt, kits from Wikipedia infoboxes (other
session); fetch politely, raw data only in `internal/`, Transfermarkt credited. Part 2 below follows this decision.

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
  `AddRandomForeignMarketPlayer`). The world still uses the 1996 POOLPLYR.DAT: 1996 players on the foreign market
  are the other 'fake' players a 2026-27 manager sees (-> a POOLPLYR built from Transfermarkt, below).
- **Changing club drops slots 16-31.** `cseg_5A6A1` (from `cseg_942F2` <- `ContinueCareerNextSeason` when a job offer
  was accepted) writes the first 16 of the career order back into the old club's record (`cseg_94193` -> tmd buffer)
  and sets `careerNumPlayers = 16`. A managed club's extra players live only while the human manages it.
- **Limits:** buffer 32 slots; fillers stop at 30; `cseg_547AC` (from `RemovePlayerFromTeam`, transfers) tests 32.
  The squad screens already scroll past 16 (squads grow by transfers in the original game).
- **Squad load point (traced 2026-10-16): `cseg_5DB56`** (in: D0 = team number, D1 = starting balance), called by
  `InitCareer+1D1` (new career) and by the tail `jmp` of `cseg_942F2` (new job). It copies the club's 684-byte
  record into `careerTeam` and `g_selectedTeams[0]` (342 words), copies the record's `playerNumbers` into
  `currentMatchPlayers`, sets `careerNumPlayers = 16`, `teamsLoaded = 0`. It does NOT run on a .CAR load or at a
  season start, so a hook at its end needs no 'already added' flag. Slots 16-31 are not cleared (a previous club's
  extras stay there as dead bytes).
- Team number: low byte = team file number (TEAM.nnn, `LoadTeamFile`; 100 = CUSTOMS.EDT), high byte = the
  club's ordinal in the file.
- **Wages:** `dseg_D6BA6 dd 32 dup` (32 slots). Both callers of `cseg_5DB56` go on to `InitializeNewSeason`, whose
  `cseg_5DEB9` (+96B) computes the wage of every player 0..careerNumPlayers-1 -> the hook does not compute wages.
- **Purchase cap:** `cseg_547AC` (transfers): when `careerNumPlayers >= 32` the pending purchase offers are dropped;
  32 = full. With 25 players there is room for 7 purchases (fillers stop at 30).
- File I/O from a stub: plain `int 21h` (3Dh / 42h / 3Fh / 3Eh) with flat 32-bit pointers works under DOS/4GW (the
  mod's diag code in careerworld.py writes files this way).

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
- Variant B (fillers become real players): see 'Two ways to the 25' below.

### Two ways to the 25 (Alex's request via the 3.2.6 session, 2026-10-16)
The 3.2.6 release session suggests hooking the game's trial-player routine (here `cseg_52956` / `cseg_52A3E`,
'AddTrialPlayer' in its map) so each invented player is the next unused real player of an extended roster, with the
used ones remembered in the .CAR trailer and random names as the fallback. Same data as XTRA, different moment:
| | A. XTRA at squad set-up (recommended) | B. Real trial players |
|---|---|---|
| When | new career / new job: the 25 are there at once | only when injuries / suspensions leave the squad short |
| Squad screen | 25 to choose from from day one | 16, grows only in emergencies, shrinks again (`cseg_52EA6`) |
| Skills | real (from the roster) | real instead of 0 |
| Hook | one, after the squad load (point still to trace) | one, in the filler routine (already traced) |
| State | 'extras loaded' flag | list of used players in the .CAR trailer |
Recommendation: A for Davide's 25 (he wants them visible), plus B's hook as the fallback: when the 25 are not
enough, the game's filler takes the next real player not yet in the squad instead of a random name with zero skills.
Both read the same per-world roster file, so the 1984-85 world (DaniSwos DB, full squads) can use it too.

### Resources already taken (mod 3.3.0, main 400a9e6)
`PlayerInfoHeader+49` (`field_31`) = blond flag (`blond.py`); `spritesIndex` extension entries 1335..1619 = shirt
numbers 17-99 + blond sets (`shirtnum.py`, `blond.py`). Any squad hook must not reuse them; rebase on main before
building.

### Risks
- Returning to a club later re-adds its XTRA players, even ones the human sold while there (keep a small per-world
  'sold' list in the .CAR trailer, or accept it).
- Extra players are invisible to the transfer market and to other clubs (CPU clubs never trade anyway).
- Wage totals rise with a 28-man squad: club finances need a check (balance after one season, harness).
- A hook in the job-change path must coexist with the mod's season-end hooks (`cseg_91428` and the world fixes).
- National selector mode must be left alone (`isNationalSelector`, it uses `careerNumPlayers` = 20).

## 2. Our own squads (independent of SWOS 2020)

### What the game needs per player (measured on the 1996-97 files, ~25,000 players)
| Byte | Meaning | Rule |
|---|---|---|
| 0 | nationality | game number 0-152 (`shortCountryNames`, 153 entries) |
| 2 | shirt number | the 1996 files hold 1-16; real numbers 1-99 are drawn in matches since mod 3.2.5 (the 1984-85 career uses them) -> Transfermarkt numbers, a free number when missing or > 99 |
| 3-25 | name | upper-case ASCII, no accents (none in either data set), 22 chars max, full name ('BUKAYO SAKA'); long ones shortened ('M. DAL COMPARE', `c1c2.swos_name`) |
| 26 | position bits 5-7, face bits 3-4 | G RB LB D RW LW M A; face 0 light, 1 ginger, 2 dark, 3 dark skin + blond hair (mod 3.3.0, `tools/blond.py`, pack skin `darkblond`); no other hair |
| 28-31 | 7 skills | nibbles pa / ve he / ta co / sp fi, value 0-7, bit 3 = key skill |
| 32 | price | **outfield: price = sum of the 7 skills, in 100% of the records of both sets** (so <= 49). Goalkeepers: skills 0, price = keeper quality (mean 11) |

- (Measured on the 1996-97 files and, for comparison only, SWOS 2020; nothing of SWOS 2020 is used.)
- Mix per 16: G 2.3, RB 1.2, LB 1.2, D 3.5, RW 1.1, LW 1.1, M 4.0, A 3.7 (1996-97).
- Skill profile of the original (mean value, key skill share): RB/LB tackling + speed (key 97/89%), D heading +
  tackling, RW/LW ball control + speed, M passing + tackling, A heading + finishing; the others ~1. The original gives
  **2 key skills** to 78% of players; SWOS 2020 gives none to 93%.
- Price distribution (1996-97, step 5): 0-4 14%, 5-9 20%, 10-14 30%, 15-19 22%, 20-24 8%, 25-29 3%, 30+ 3%; SWOS 2020
  2025-26 is a bit stronger (30+ 7%).

### Sources (decided: Transfermarkt)
| Source | Coverage | Data | Licence / terms | Use |
|---|---|---|---|---|
| **Transfermarkt** (site) | every league of the world (~1300-1600 clubs) | squad page per club ('detailed' view): name, shirt number, sub-position (Centre-Back, Right Winger...), birth date, nationality (+2nd), foot, height, contract, market value; squad stats page: appearances / minutes; coach | terms forbid bots / automated copying and redistribution without written consent; no public API | **chosen by Davide**: polite fetch (one pass, cache, delay between pages, clear user agent), raw pages only in `internal/`, credit Transfermarkt; asking them for written consent is still advisable before a release |
| Wikipedia club infoboxes | nearly all clubs | kits | CC BY-SA 4.0 | kits (other session); squads only as a cross-check if Transfermarkt lacks a club |
| dcaribou/transfermarkt-datasets | ~40 competitions, ~400 clubs | same Transfermarkt fields, weekly | tagged CC0, data scraped from Transfermarkt | not needed; at most a check of our parser on the big leagues |
| EA SPORTS FC 27 ratings | ~750 licensed clubs | ~30 attributes | EA's data | not in the decision; optional open question (finer skill profiles) |
| SWOS 2020 | — | — | — | **not used** (decision 2026-10-16) |

Pages: ~1500 clubs x 2 (squad + squad stats) = ~3000 pages, plus competition pages for the club lists; at one page
every 5-10 s that is 4-8 hours, once per season, resumable (each page cached as soon as it is fetched).

### Chosen pipeline (private converter, deterministic)
`internal/world2526/squads/` (nothing of it in the repo): `fetch.py`, `build.py`, `maps/`, `raw/`, `out/`.
1. **Snapshot**: one parameter `--season 2026-27 --as-of 2026-09-02` (after the summer 2026 window). Every fetch
   goes to `raw/transfermarkt/<season>/<as-of>/...` with the date it was taken and is never fetched again (a manifest
   with URL, date, hash). Transfermarkt shows the current squad, so the snapshot IS the fetch date: fetch in a few
   days after the window closes. The build reads only `raw/`: same input -> byte-identical output. **Next season =
   a new snapshot + rerun** (plus a diff report: transfers, new clubs). Calendar-year leagues (Brazil, Argentina,
   MLS, Scandinavia, Japan...) are mid-season on that date: their squad is the one of that day.
2. **Club list and mapping**: the world's clubs come from the Transfermarkt competition pages of the snapshot
   (league members 2026-27); `maps/clubs.csv` world club key -> Transfermarkt id (+ Wikipedia title for kits).
   Built once by name matching + hand fixes (~1500 rows); reused every season.
3. **Players**: everything from the Transfermarkt squad page (name, number, sub-position, nationality, birth date,
   market value) + minutes of the previous season from the squad stats page; order = importance (minutes, then
   market value).
4. **Mapping tables** (`maps/`, versioned with the converter):
   - `positions.csv`: Goalkeeper G; Right-Back RB; Left-Back LB; Centre-Back D; Right Winger / Right Midfield RW;
     Left Winger / Left Midfield LW; Defensive / Central / Attacking Midfield M; Centre-Forward / Second Striker A.
     A bare 'Defender' / 'Midfield' / 'Attack' (no sub-position) -> D / M / A.
   - `nations.csv`: FIFA code -> game number (0-152); first (sporting) nationality; a missing nation -> the closest
     existing one, listed in the build log.
   - `names.csv`: overrides (known short names: 'VINICIUS JUNIOR', 'RODRI'), then `swos_name` (NFKD -> ASCII,
     ß -> SS, upper, 22 max, 'J. SURNAME' when longer).
   - `faces.csv`: face from FC 27 (skin tone + hair colour -> light / ginger / dark / darkblond) where the player
     exists, plus correction lists;
     default light (Transfermarkt has no such field; no SWOS 2020 faces).
5. **Skills** (proposal, Transfermarkt data only):
   - **Level**: target skill sum S from market value on a log scale, corrected per league (the same value means
     more in a weak league) and by age (young players' values are inflated), fitted so the world's distribution
     matches the game's (outfield mean ~13, stars 38-45, cap 49). No value: the club's median minus a step.
   - **Profile**: S is split over the 7 skills with the original game's profile of the player's sub-position
     (RB/LB tackling + speed, D heading + tackling, RW/LW ball control + speed, M passing + tackling, A heading +
     finishing; Defensive Midfield leans to tackling, Attacking Midfield to passing / ball control, Second Striker to
     ball control / finishing); height adds heading, a deterministic per-player variation (hash of the Transfermarkt
     id, no RNG) keeps players of one role from being identical. Rounded to 0-7 with the sum preserved; key skills =
     the 2 of the profile (as the original).
   - **Goalkeepers**: skills 0, price = S of the same curve. **Price = S** for everyone (the engine's own rule).
   - **EA FC 27** (Davide, 2026-10-16) where the player exists: pa = short passing / vision, ve = shot power / long
     shots, he = heading accuracy / jumping, ta = standing / sliding tackle / interceptions, co = ball control /
     dribbling, sp = sprint speed / acceleration, fi = finishing; S still from the same level curve (FC overall
     blended with the Transfermarkt value), split by the player's own attribute profile; key skills = his 2 best.
6. **Calibration** (the mod's rule): per club print the first-11 skill sum and price next to the real 2025-26
   table (and the 2026-27 one as it grows); adjust the curve per league (never by whole skill levels with a small price shift: that was the
   1947-48 flaw); then simulated seasons in the harness for ~5 leagues (champion and bottom clubs roughly right).
7. **Output**: the world pack in mkseason's `explicit` format (players.csv with position, number, nat, skin, the 7
   skills, price; 16 rows -> the record, rows 17-30 -> XTRA when extended squads exist) + a per-world POOLPLYR.DAT.
   mkworld2526 switches from method `records` to `explicit`; mkseason itself never depends on the source.

### Legal and credits
- Raw pages, dumps and ratings stay in `internal/`; the repo gets only the converted packs (as for DaniSwos'
  1984-85 database) and only after Davide's ok.
- Credits in the release notes and README: Transfermarkt (squads, coaches), 'Wikipedia contributors (CC BY-SA 4.0)'
  (kits); EA only if Q6 says yes. Written consent from Transfermarkt is advisable before publishing (open question 2).

## Open questions for Davide
Settled 2026-10-16: season 2026-27, Transfermarkt at the end of the summer 2026 window, no SWOS 2020, real shirt
numbers (1-99, mod 3.2.5). Davide's answers (2026-10-16):
1. Managed club: **25 players** (16 in the record + 9 in XTRA). CPU clubs 16 (call-ups: section 3).
2. Written consent from Transfermarkt: **Davide asks**.
3. Skin: see below (a hand list for ~37,000 players is not realistic).
4. Key skills: **2 per player, as the original**.
5. **Yes**: a 2026-27 POOLPLYR.DAT per world.
6. **EA FC 27 too**: attributes for the skill profiles (and skin, below) where the player exists; Transfermarkt
   value/league/age model for the others. Private use, credit EA SPORTS FC 27.

Skin (open): FC 27's player data carry a skin tone and a hair colour per player -> light / ginger (red hair) /
dark / darkblond (dark skin, blond hair; mod 3.3.0) for the
~17,000 FC players, matched to Transfermarkt by name + birth date + club. The others (clubs outside FC: about half
of the world) default to light, with optional per-league correction lists that Davide or players who know a league
can send (a small CSV: Transfermarkt id, skin). No guessing from nationality or photos.

## Estimate (sessions)
| Part | Sessions |
|---|---|
| 1a. Trace the squad-load point (new career, new job), wage table size, purchase cap | 1 |
| 1b. XTRA format in mkseason, hook stub, harness scenario (squad of 28 shown, match, save/load, job change, return) | 1-2 |
| 1c. Per-world POOLPLYR.DAT (builder + file-name patch + harness) | 1 |
| 2a. Polite fetch/cache layer + manifest + Transfermarkt parser (squad, stats, coach) | 1 |
| 2b. Club mapping ~1500 clubs (matching + hand fixes) | 2 |
| 2c. Mapping tables (nations, positions, names, faces) | 1 |
| 2d. Skill model (value/league/age/sub-position) + calibration against the game's distributions | 1-2 |
| 2e. Pack output (explicit + XTRA), mkworld2526 switch | 1 |
| 2f. Strength check (tables + simulated seasons) | 1-2 |
| **Total** | **10-13** (part 1: 3-4; part 2: 7-9) |
| Later: next season (new snapshot, rerun, new clubs in the mapping, strength check) | ~1-2 |

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

### Bench: 5 is the engine's maximum (follow-up: 'today 9-12 sit on the bench')
- `MaxSubstitutes` cycles 0..5 (= players on the bench), `MinSubstitutes` <= it (= substitutions allowed);
  `InitializeInGameTeamsAndStartGame` gets both (D1/D2) and the match squad is 11 + bench (`RotatePlayersLeft`:
  `add D0, 11`), drawn from the record's 16 through `playerNumbers`. So 5 substitutions with a bench of 5 already work.
- In the match everything is sized for 16 per team: one PlayerInfo per player (`InitInGamePlayer`), the saved teams
  of replays / highlights (`topTeamSaved` / `bottomTeamSaved db 1704`), the bench screen (`DrawSubstitutesMenu`,
  5 rows, `BenchCheckControls`, `SubstitutePlayer`, `SetBenchPlayersNumbers`), and SWOS++ patches the same sites
  (DrawSubstitutesMenuEntry 8 sites, BenchCheckControls+0x78F).
- A bench of 7-12 = match squad 18-23 = the record limit again plus the match engine, replay/highlight formats and
  SWOS++ compatibility: the most fragile part of the game. Not recommended (estimate 15-25 sessions, high risk).
- What the call-up design gives instead: squad of 24-30, before each match the human picks the 11 + the 5 he may
  bring on (all 5 usable, as the 5-substitution rule); CPU clubs by rule or real call-ups. The only loss vs reality:
  the 5 substitutes are chosen before kick-off, not among 9-12 during the match. The '3 windows' rule is not modelled.
