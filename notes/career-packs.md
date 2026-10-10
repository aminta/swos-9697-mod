# Historic careers ("career packs") — study (2026-10-09, session 30)

Goal (Davide): an era world (e.g. 1984-85) limited to a set of countries, played as a career **in the same exe**
(CARRIERE STORICHE menu next to the normal career), described by data like the season packs.

Addresses: swos-port names (ENGLISH.EXE); the mod finds everything by content.

## What the engine already does for us

- **Season end runs on a country list.** `cseg_91428` processes the player's country, then every country byte of
  `seasonEndList` (`dseg_C943A`, FF-terminated, one code reference): `cseg_9153F` (league: simulated or read from
  slot 0, promotions/relegations) + `cseg_93974` (European qualifiers, only for continent byte 0). A reduced world =
  a shorter list.
- **European places are data.** `cseg_936C0` copies three static country lists into the working lists:
  `dseg_C947C` -> `dseg_18072F` (Champions Cup), `dseg_C94CB` -> `dseg_180740` (Cup Winners' Cup), `dseg_C951A` ->
  `dseg_180761` (UEFA); a country appears once per place. `cseg_939C9` / `939FE` / `93A60` pick the clubs from the
  standings (skipping holders `dseg_18070F` / `180715` / `180727` / `180711`) into the 80-record buffer at
  `dseg_1807C2` (684 B per club). Counters `dseg_180784/86/88` must end at 16/32/32 and the total at 80
  (`careerFileBuffer` used as counter vs `CN_EUROPE`): immediates in `cseg_91428`, patchable per world.
- **Multi-division leagues with promotion/relegation are native** (Italy A/B/C1/C2 of the mod): the division byte
  (+25) and `someLeaguesTable` (deltas per global number) live in the save.
- **Job offers only from loaded clubs.** `cseg_5B705` -> `AddJobOffer` picks clubs from `competitionFileBuffer`
  (the player's league) and `tmdFileBuffer` (European cup clubs): no 1996-97 club leaks into a historic world.
  Exception: national-team calls (`lastNationalityCall`, national teams 80..85 = the 1996-97 nations) -> to be
  disabled in historic worlds (or era national teams later).
- **Countries 101..251 are free and work** (season-pack test 2026-10-09: TEAM.101/102 loaded, menus, structs).
  The team file name is built as 3 digits from 0..255 (`LoadTeamFile`).

## Design (same exe)

1. **Pack countries live permanently at 101..251**: their `countriesTable` / `competitionsTable` /
   `teamsCountryNumbers` entries and TEAM files never need swapping. A career pack's countries are reachable only
   from its world.
2. **World switch** = a small set of swaps, done when a historic career starts and when one is loaded, undone for a
   normal career:
   - the `seasonEndList` pointer (1 code ref) -> the world's country list;
   - the 3 static qualifier lists (3 code refs, or copy over them: they are FF-terminated);
   - the European cup structs (formats: team counts, rounds) and their first-season participants (today the
     `eurocup.tmd` / `eurocwc.tmd` / `uefacup.tmd` files via `LoadSomeEuroCup`);
   - the 16/32/32/80 checks of `cseg_91428`;
   - the season year shown (the career computes it from 1996; `CareerOverFinish` has the 1995/+100 logic);
   - the career-start team selector menu (the comp[254] swap already used for CLASSIC SEASONS).
3. **Save mark**: the .CAR trailer (today 'C6') gets a world id; `LoadCareerFile` sets the world before
   `ProcessCareerFile` rebuilds the slot pointers. Normal careers have no mark (= 1996-97 world).
4. **Global numbers**: all clubs of one world coexist, so they need unique numbers inside the world (< 2000); a
   historic world may reuse the 1996-97 numbers (the two worlds never run together; `someLeaguesTable` is per save)
   — to verify.
5. **Names**: competition names in a career must not carry a year (they last many seasons).

## Career pack format (sketch)

Like a season pack, plus per country: leagues with divisions (teams, promoted, relegated, play-offs), national cup,
European places (CC / CWC / UEFA), and per world: the European cup formats, the first-season participants
(optional real brackets), the start year, which countries exist.

## Still to verify (next study / first test world)

- European cups after season 1: are the qualifiers written to the save (80-record buffer) or to the TMD files?
- Transfer market: which teams supply players (expected: the loaded ones, like job offers).
- European formats with more than 80 clubs in total (e.g. CC 32 + CWC 32 + UEFA 64 = 128): the 80-record buffer
  must move (done before for the South American cups); formats up to 80 fit as they are.
- First test world from our own data: DDR with 2 divisions (Oberliga 14 + a second division from the 18 cup-only
  clubs) + the test country, European cups among them only.

## Estimate

Study done for the main questions; ~5-8 sessions to a first playable career pack (test world first, then 1984-85
with Daniele Bordes's data).

## M1 — test world (2026-10-09): PASSED

- mkseason: pack `kind` ('season' | 'career'); league `divisions` [{teams, promoted, relegated, names}] with the
  clubs.csv `division` column (record byte +25); career packs go to pseudo-continent 98 CLASSIC CAREERS
  (CARR. STORICHE), shown only in the career team selector: `career_sel` replaces `call ChooseTeamsDialog` in
  SelectTeamToManage and swaps comp[254] for a world table with 98 (cont_check accepts 97 and 98); historic
  hist_names colours the button.
- Test world (scratchpad only): country 101 'DDR (TEST)', Oberliga 14 (2 relegated) + DDR-LIGA 18 (2 promoted),
  FDGB-POKAL; still the 1996-97 European world.
- Davide's playtest: CARR. STORICHE -> DDR (TEST) -> Dynamo Schwerin (DDR-LIGA); season 1 ended, season 2 started,
  job offers arrived, saved WCARR1.CAR. Save read: someLeaguesTable deltas Zwickau +1, Union +1 (relegated),
  Eisenhuettenstadt -1, Thale -1 (promoted, 1st and 2nd of the DDR-LIGA table) = correct.
- Expected gaps (M2): year 1996/97, 1996-97 European cups and world view (VISUALIZZA MONDO -> Europa has no DDR).

## M2 — world switch: analysis so far (2026-10-09)

- Career start: ChooseTeamAndStartCareer -> SelectTeamToManage -> ChooseTeamsDialog (also used by
  BuyOtherForeignPlayer: in a historic world that browser must show only the world -> same comp[254] swap) ->
  InitCareer(D0 = country << 8 | ordinal). InitCareer loads the 80 European clubs: careerFileBuffer = 0, then
  LoadSomeEuroCup(euroCup / cupWinnersCup / uefaCup) appends data\eurocup.tmd / eurocwc.tmd / uefacup.tmd (plain
  684-byte records) into tmdFileBuffer (careerFileBuffer = count); the .CAR fixed part starts at careerFileBuffer, so
  these clubs (and their successors) live in the save.
- Season end qualifiers: cseg_9153F leaves the country's standings as records from dseg_1807C2 (684 each);
  cseg_939C9 (CC: the champion), cseg_939FE (CWC: from dseg_181D22, skipping holders), cseg_93A60 (UEFA: from
  dseg_1827D2 or dseg_180A6E, skipping holders/already qualified via cseg_93B9C / 93BB5 = "already in CWC/UEFA list").
  cseg_93D67 appends the global number (word) to the list pointed by dseg_180796 / 18079A / 18079E, counters
  dseg_180784 / 86 / 88, then cseg_94193 (to read: probably copies the record into the next-season buffer).
  cseg_93DAA removes a club from a list.
- Idea for the world id: someLeaguesTable[1999] (saved with the .CAR fixed part, no club uses global 1999), written
  where sacups writes the 'S3' career mark at career start (from the selected club's country: pack country -> world
  index + 1, else 0). Hooks read it: seasonEndList pointer (cseg_91428), the 3 static qualifier lists (cseg_936C0),
  the TMD loads (InitCareer), the 16/32/32/80 checks, the year, comp[254] in career menus.
- Format change needed: a career pack = a WORLD with several countries (each: files, league with divisions, cup,
  European places) + world European cups (formats, first-season clubs = generated TMD-like files).
- Next to read: cseg_94193, cseg_92BBF (holders), how euroCupCopy / cupWinnersCupCopy / uefaCupCopy are built from
  the lists at the next InitNewSeason (sizes: original structs 16 groups / 32 / 32), cseg_8D661 (membership).
- Test material for the next sessions: internal/career-test/ (git-ignored; README there). c/SWOS currently holds the
  M1 test build (ITALIAN.EXE da08e328 + DATA/TEAM.101); 2.6 exe = c/SWOS/ITALIAN_26.EXE (9881320f); save WCARR1.CAR.

## M2 — European chain fully read (2026-10-09, session 31)

- **Career start** (InitCareer): clears someLeaguesTable[0..1999] (2000 bytes, so [1999] is cleared too), then
  `careerFileBuffer = 0` + LoadSomeEuroCup(euroCup / cupWinnersCup / uefaCup) = data\eurocup.tmd / eurocwc.tmd /
  uefacup.tmd appended to tmdFileBuffer; SetTeamGlobalNumbers writes record word +2 = teamsCountryNumbers[byte 0] +
  byte 1 (so a TMD record is just a copy of a team-file record). Then the `careerContests` table [src, dst, size]
  copies the static structs into the save: euroCup -> euroCupCopy (79 B), cupWinnersCup -> cupWinnersCupCopy (92 B),
  uefaCup -> uefaCupCopy (92 B).
- **Cup struct team list** = byte [7] + 7 (CC: 47, CWC/UEFA: 28), one (country file, ordinal) byte pair per club;
  CC 16 pairs, CWC/UEFA 32 pairs. So a world fits in the existing save with KNOCKOUT formats of at most
  CC 16 / CWC 32 / UEFA 32 clubs (total <= 80 records): no buffer has to move.
- **Season end** (cseg_91428): cseg_936C0 points dseg_18078A/96 (CC), 18078E/9A (CWC), 180792/9E (UEFA) at the
  team list INSIDE euroCupCopy / cupWinnersCupCopy / uefaCupCopy and zeroes the counters 180784/86/88; it expands the
  static place tables into the working country lists 18072F / 180740 / 180761 with cseg_93E36. A place table is
  `[dd ptr, dw n, dw take]...` + dd -1: from the n country bytes at ptr, `take` are chosen at random (shuffle) — e.g.
  CC: 4 of {0E,14,23,08}, 5 of 6, 5 of 11, 2 of 22. Then careerFileBuffer = 0 and every country of seasonEndList
  (player's first) gets cseg_9153F + cseg_93974; cseg_93D67 writes the club pair into the cup's own list and
  cseg_94193 copies its 684-byte record to tmdFileBuffer[careerFileBuffer++] (it asserts the club is in a loaded file:
  SearchTeamInTmdFile). So the next season's cups are the in-save copies themselves.
- Checks: careerFileBuffer == 80 after the loop; cseg_92BBF (holders): for each of CC / CWC / UEFA holder
  (dseg_18070F / 180711 / 180713, FFFF = none) not qualified, a random list entry of another country (not the
  player's) is replaced by the holder (cseg_9423A removes the record, cseg_94193 adds the holder's, record saved in
  dseg_182A7E / 182D2A / 182FD6); then 16 / 32 / 32 / 80 again. All immediates -> per-world values.
- **ProcessCareerFile** (load): only needs dseg_E092F (which copy the player is in) — nothing world-specific.

### M2 implementation plan (same exe)

World byte = someLeaguesTable[1845] + balance byte [1846] = -world (written by an InitCareer hook from the chosen club's
country; 0 = 1996-97). NOT [1999]: global 1999 belongs to a TEAM.062 club, and cseg_9487A traps (int 3) unless the
table sums to 0 mod 256 (that is why the 'S3' mark at 1847..1849 has a balance byte too).
1. InitCareer: world -> load the world TMD (one file `data\wNN.tmd`, all first-season euro clubs) instead of the 3
   files, and overwrite the 3 copies with the world's KO structs after the careerContests copy.
2. cseg_91428: seasonEndList, the 3 place tables (cseg_936C0) and the 16/32/32/80 checks read per-world values.
3. Holders: FFFF at a world start (nothing to inherit).
4. Later (M3): year, comp[254] in BuyOtherForeignPlayer, national-team calls, other-continent cups in the world view.

### M2 built (2026-10-09, session 31) — awaiting playtest

- tools/careerworld.py (hooks + world data), mkseason: pack.json `world` (number), `europe_places` {cc, cwc, uefa},
  optional `first_europe` {cup: [club keys]} (default: league order), `world_cups` {cup: {rounds}} in exactly one
  pack of the world (default rounds: two legs, single-match final). Cups: knockout, power of 2, CC <= 16,
  CWC / UEFA <= 32. Build writes DATA/WORLDnn.TMD (first-season European clubs). World clubs may reuse 1996-97
  European global numbers (mkseason.career_file: exempt from the global-number check).
- Hooks: InitCareer entry (club country), 3 LoadSomeEuroCup calls (world: one TMD), after careerContests (3 cup
  structs), cseg_91428 seasonEndList + 5 checks, cseg_936C0 3 place tables (+ the UEFA first-group read).
  Without worlds the build is byte-identical (M1 da08e328 rebuilt).
- Holder insertion (cseg_92C4D) compares entry word >> 8 with holder >> 8: on PC that is the club ORDINAL (byte 1),
  not the country (68000 big-endian leftover). It replaces a random entry with a different ordinal that is not the
  player's: it ends as long as some entry has another ordinal (true when the holder's own country place went to
  another club).
- Test world 2 (internal/career-test/mkworld2.py -> world2/a..d): countries 101 DDR (TEST) base 1786, 102 TEST B
  base 64, 103 TEST C base 0, 104 TEST D base 32 (cloned DDR data, prefixed names), each CC 1 / CWC 1 / UEFA 2 ->
  cups 4 / 4 / 8. Build ITALIAN a0ac95c6 installed in c/SWOS with TEAM.101-104 + WORLD01.TMD (WCARR1.CAR = M1 save,
  1996-97 world: do not use for M2).
- Playtest: CARR. STORICHE -> a club of a test country; season 1 European cups = the 4/4/8 world clubs; finish
  season 1 (no freeze = checks OK), season 2 cups = world qualifiers; save + reload; a normal career still has the
  1996-97 cups.

### Playtest 1 (2026-10-09): season 1 OK, season 2 = 1996-97 qualifiers -> fixed

- Season 1: CC 4 / CWC 4 / UEFA 8 world clubs, no freeze at season end, year 1997/98, save OK, normal career OK.
- Season 2 cups held 1996-97 clubs (save WCARR2: 80 records of every European country, world byte 0): InitCareer
  calls InitializeNewSeason, whose cseg_8CC4E copies leaguesTableCopy back over someLeaguesTable, wiping the world
  byte written only in someLeaguesTable. Fix: world byte + balance also in leaguesTableCopy (found from the two
  copy routines cseg_8CC0A / cseg_8CC4E; IT obj2+0x5953C, EN +0x593F2). Build ITALIAN 271146d8 -> replay with a NEW
  career (WCARR2 is a 1996-97-world save now).

### Playtest 2 (2026-10-09): M2 PASSED (save WCARRFIX.CAR)

- New career with 271146d8: season 2 cups hold only world clubs (CC 4, CWC 4, UEFA 8), DDR-Liga clubs promoted,
  save: world 1 / balance 255, table sum 0, 16 euro records (101: 4, 102: 6, 103: 3, 104: 3).
- Engine rule seen: the CC holder (B Dynamo Dresden) replaced a random qualifier (BFC Dynamo, DDR champion) —
  cseg_92C4D replaces, it never adds. Real formats with a holder place of its own (e.g. 1984-85: 31 + holder) need a
  hook (count places + 1 before the holder step, or add instead of replace). Decide with Davide in M3.

## M3 (2026-10-09, session 31): PASSED (save WCARFIX2.CAR, build ITALIAN 89558430)

- Year: world_cups.start_year (test 1988); w_cups sets seasonPlaying; PrintNameAndSeason (cmp 1996) and
  CareerOverFinish (cmp 1995) compare with the world's year. Seen: CAMP. 1988/89 -> 1989/90.
- World view + BuyOtherForeignPlayer: comp[254] = [first, -1, 99] and comp[99] = world continent (cups -> the in-save
  copies, countries); countriesTable[99] = CLASSIC CAREERS record; cont_check accepts 99. Seen: one CARR. STORICHE
  continent with 3 cups + 4 countries; foreign browser = the 4 world countries (bought from C Energie Cottbus).
- National team: cseg_8D7B4 tail stores -1 in lastNationalityCall in a world.
- Holders (Davide: extra place): first try froze — cseg_93BCE clears a holder that qualified through its league, so the
  appended place was missing. Now the 3 calls of cseg_93BCE skip holders and clubs already in any list (next club of
  the table) and w_holders appends the 3 holders + records. Save: 13 qualifiers + B Dynamo Dresden (CC holder),
  C BFC Dynamo (CWC), D Dynamo Dresden (UEFA), no duplicates. Places = size - 1, root pack fills the holder place in
  season 1. World code moved to a 6th obj1 page (0xA6000, only in builds with worlds; no-world builds unchanged).
- Next: a real world (1984-85 with Daniele Bordes's data), world name per world (button text), long-career test.

### 'S3' mark missing in world saves -> 1.2 bug, fixed (2026-10-09)

sacups.init_sa (InitializeNewSeason, branch "club in no European cup") checks the 'S3' mark and, on a new career,
calls trailer.new_career_defaults (saved lists from the defaults + mark). The other branch (euro_found: the club is in
a European cup) never did: a new career starting in a European cup had no mark until the save was reloaded, kept the
lists of a career loaded earlier in the same game session, and a later season without European cup reset the
SA/CAF/Asian lists to the 1997 defaults. Present since 1.2 in normal careers too. Fix: euro_found does the same check
first. Build ITALIAN a78d5d0a (world2 test build + fix) installed in c/SWOS. To test: new career with a club in a
European cup (e.g. Juventus, or Dynamo Dresden in CARR. STORICHE), save at once, check the mark in the .CAR.
- Playtest 2026-10-09: new career with Dynamo Dresden (CARR. STORICHE, in the Champions Cup at season 1), saved at once without reload: DRESDA.CAR has 'S3z' at 1847..1849, world 1 / balance 255, table sum 0. PASSED.
- Release 2.6.1 build (d38a5d1c) playtested 2026-10-10: new Juventus career saved at once (JUVE.CAR) has 'S3z', 80 euro records, sum 0; DDR season with Dynamo Dresden shows COPPA UEFA 1988-89 as 3rd competition.

## Euro 128 — analysis (2026-10-10, branch career-euro128): CC 32 / CWC 32 / UEFA 64 in a world

Goal: the real 1984-85 format (all knockout, two legs, no byes) = 128 European clubs vs the engine's 80 (16/32/32).
Every place that assumes 80 / 16-32-32 (swos-port names):

- **tmdFileBuffer** (80 x 684 = 54720 B) sits in the .CAR fixed part (careerFileBuffer .. g_numSelectedTeams = 95151 B,
  word 0 = record count) and cannot grow in place (dseg_D6B4E, currentSeasonShowing, the management record, someLeaguesTable
  follow). Its code references: SearchTeamInTmdFile, LoadSomeEuroCup, cseg_52D40, cseg_5AB36 (x2), cseg_5B705 (job offers),
  cseg_94193 (add record), cseg_9423A (remove) = 8 `mov Ax, offset tmdFileBuffer` sites; records are always addressed as
  base + i*684, so a relocated buffer works if all 8 read the same base.
- **Cup copies** euroCupCopy 79 / cupWinnersCupCopy 92 / uefaCupCopy 92 B (in the fixed part). World structs use the CWC
  layout (list at +28, 2 B per club): CC 32 = 92 B, CWC 32 = 92 B, UEFA 64 = 156 B. References: ProcessCareerFile (3,
  dseg_D8CB6 from dseg_E092F), InitializeNewSeason (3, membership), cseg_92D55 / 9307A / 9339D (3, finish the cups,
  winners), cseg_936C0 (3, qualifier list pointers), careerContests (3 dst: the world structs are written after it, as in
  M2), and **dseg_C707E** (contest list read by cseg_24DFA / cseg_87DA0 / one more: a contest in it gets DIY [3Bh] = 0 =
  clubs from the tmd buffer; a relocated world cup MUST be listed there or it would load clubs from team files).
- cseg_91428 checks 80 / 16 / 32 / 32 (+ cseg_92BBF holders): already per world (W_CHK, w_holders).
- Cup engine: a type-1 slot buffer is 0x443 = 0x43 + 64 x 16 B, i.e. 64 clubs max; CLASSIC SEASONS already run UEFA
  1988-89 with 64 clubs and 6 rounds (same CWC header, euro8889 / mkseason). Non-player cups are simulated at season end by
  cseg_3ADAE in the DIY area (same engine). So 32 / 32 / 64 knockout fits the engine; more than 64 per cup does not.
- Saves: g_selectedTeams room 68400 B holds N cached teams (N seen 10..47: the player's league + national cup clubs) + the
  948-B trailer. 48 more full records (32832 B) fit only while N <= 50: too tight. But a tmd record = team-file record +
  global number + byte 4 (status 1) / byte 22 + per-player season stats (+1, +33..36) — verified on WCARFIX2 / JUVE /
  APOK4. So records 80..127 can be **rebuilt from the TEAM files at load** (LoadTeamFile applies the save's division
  deltas) and only their (file, ordinal) pairs are saved: cost = the season stats of those clubs' players after a reload
  (cosmetic, reset at the next season end anyway).
- Memory: WTMD 128 x 684 = 87552 B + 3 cup buffers. The LE loader padding has only ~100 B left (8 B per added page = 12
  pages), so not as file pages: **raise obj2's virtual size** (zero-filled BSS above the last page, like the original obj2
  tail) — only in builds with a big world.
- Not affected: season-end qualifiers (cseg_93974 writes into the list the cseg_936C0 pointers give), job offers (random
  tmd record), VIEW WORLD (W_CONT -> world buffers), foreign transfer browser (comp[254] swap), ProcessCareerFile.

### Design (behind the world flag; normal careers unchanged)

1. Big world = total > 80 (world record flag). Helper `w_tmd`: base = WTMD in a big world, else tmdFileBuffer; the 8
   sites call it. Helpers `w_cc / w_cwc / w_uefa`: the world cup buffer in a big world, else the copy; 12 code sites.
   dseg_C707E copied into the cave + 3 world buffers, its 3 references retargeted (unconditional, harmless).
2. w_cups writes the world structs into the world buffers; W_CONT points there.
3. Save (trailer): big world -> WTMD[0..80) copied over tmdFileBuffer (fixed part) before WriteFile, then a 'W1' block
   after the C7 block: the 3 cup buffers + the pairs of records 80..k-1. Load: fixed -> WTMD[0..80), cups restored,
   records 80+ rebuilt with LoadTeamFile (byte 4 = 1). Normal careers write no 'W1' block (files identical).
4. mkseason / careerworld: CC <= 32, CWC <= 32, UEFA <= 64, total <= 128 (powers of 2) for worlds.
5. Test world: 8 countries x 20 clubs (mkworld3), cups 32 / 32 / 64.

Estimate: 1 session to build (hooks + trailer + checks + test world), 1 playtest/fix round, docs in the release session.
Verdict: GO (no engine limit is exceeded; the risks are the BSS growth under DOS/4GW and the season-end path with 128,
both covered by the first test).

### Euro 128 built (2026-10-10, commit 0dac0b3) — awaiting playtest

- careerworld: big world = more than 80 clubs or a cup above 16/32/32 (record dword +48). 18 `mov [Ax], offset X`
  sites (8 tmdFileBuffer, 4 per copy... see sites(): tmd_sites, copy_sites, list_sites) call stubs that pick the moved
  buffer in a big world; dseg_C707E copied to WCLIST + WCC/WCWC/WUEFA (its 3 code refs retargeted). Moved buffers in
  the obj2 tail (BSS[0] = first page after the free pages, vsize + 0x16000): WTMD 128 records, cups at +0x15600 (160 B
  apart), place lists at +0x157E0 (64 / 64 / 96). Found in all 4 languages.
- .CAR: trailer.patch(tails=True) ends with jmp [SAVE_TAIL] / [LOAD_TAIL]; patch_tails: save copies WTMD[0..80) into
  the fixed part and appends 'W1' (5194 B: cups 92/92/160 + 48 x (pair + 99 VAROFF bytes)); load copies them back and
  rebuilds records 80..k-1 with LoadTeamFile (GetTeamPointer's callee) + the saved bytes, then teamsLoaded = 0.
- Found while building: a cup of 6 rounds is 29 + 2n B (UEFA 64 = 157 -> 160 B buffers); 31 career packs do not fit the
  shared caves -> career packs get obj1 pages 0xA7000-0xA9000 (CAREER_DATA) and a 2nd free obj2 page (Obj2Area keeps
  blocks inside one page); the free contest ids (0xCB..0xFE) are too few for 31 leagues + 31 cups -> a LEAGUE id may be
  shared by the packs of one world (mkseason check). To verify in game: career record / history with shared ids.
- Per country the engine qualifies at most the top 9 of the top division + the cup finalists (cseg_927A2): fine for
  the real places (1984-85: at most CC 1 + CWC 1 + UEFA 4).
- Test world 3 (internal/career-test/mkworld3.py): 31 countries TEAM.101..131 (DDR clones, prefixes B0.., bases 32k),
  world 3 from 1984, places CC 1 / CWC 1 / UEFA 2 (root 3) -> 32 / 32 / 64 with the holders. Build IT c3ad9f2f (+ EN
  65e603bd FR 720c1aee DE b4787104), WORLD03.TMD 128 records; no-world build still d38a5d1c, world2 build OK.
  Installed in c/SWOS (2.6.1 exe saved as c/SWOS/ITALIAN_261.EXE). Save checker: internal/career-test/checkw1.py.

### Euro 128 playtest (2026-10-10) — fixes found on the way

1. World table indexed by position, not by world number: a lone world 3 read an empty record (empty TMD name ->
   LoadFile error -> exit to DOS). WTAB now has a slot per world number (missing ones zero).
2. 'W1' after the C7 trailer did not fit: a world career caches ~92 teams (own 32 + the 60 foreign UEFA clubs of the
   player's cup) and the 68400-B room was full -> W1 skipped silently, empty cups after a load, freeze at season end.
   W1 (13274 B: cups + 128 x (pair + 99 VAROFF bytes)) now lives in the fixed part's 80-record area; load rebuilds all
   128 records from the TEAM files (LoadTeamFile) + the saved bytes.
3. Season 2 end froze after PARAGUAY (DOSBox-X debugger, core=normal, menu Debug: EIP in cseg_3283C's int 3): the
   1996-97 qualifier simulations (arg_agg -> sa_qualify: SA / CAF / Asia / CONCACAF / Argentina) read someLeaguesTable at
   their clubs' global numbers, which world clubs reuse -> wrong division size. In a world the season end now calls
   cseg_92D55 directly (careerworld.late; also fixes world 2, whose numbers only hit European clubs).
4. Then a freeze on the chairman's note (MEMDUMPBIN of the debugger, 32 MB): g_numSelectedTeams 104 > 100, pseudo
   registers overwritten, endless search in cseg_32E15. cseg_92D55 ends the Champions Cup as the 1996-97 group cup (type
   2: played cseg_89B5C, simulated cseg_3ADAE -> cseg_320A3 reads the club count at byte 15 = 0x94 = 148). A world's
   Champions Cup is a knockout: in a world those two calls go to the CWC's cseg_45B51 / cseg_3ACAB (winner readers
   cseg_92F1C / cseg_93241 are alike). Latent since M2 (4-club cups: 20 entries, no overflow).
- Debug recipe kept: internal DIAG build (DIAG=1: int 3 + timer watchdog writing DIAG.BIN) did NOT fire under DOS/4GW
  here; the DOSBox-X debugger from a terminal tab (Debug menu -> debugger, MEMDUMPBIN 0168:00000000 2000000) did.
  ITALIAN obj1 at linear 0x263000, obj2 at 0x30C000 in these builds.
- PASSED: build ITALIAN 25f5d535: seasons 1 and 2 ended with a load in between (W128.CAR -> W128B.CAR, season
  1986/87): cups 32 / 32 / 64, 31 countries, no duplicates, W1 ok, table sum 0.
- PASSED (Davide, 2026-10-10): W128B loaded, season 3 ended (W128C.CAR, 1987/88: k 128, W1 ok, sum 0), career record
  shows the right league names with the shared id, a normal Juventus career to season 2 (JUVE2.CAR: world 0, 80
  records, 'S3', C7). Builds IT 25f5d535 EN 754fe831 FR ebd58c01 DE db9b2520 (EN/FR/DE not run); no-world IT d38a5d1c.
- Docs: packs/CAREERS(.it).md limits (32 / 32 / 64, 128, places per country), manual sources IT/EN chapter 23 item
  'Euro 128' (artifacts not republished); mkseason check: europe_places at most cc 1, cwc 1, uefa 6.

### First-round draw (2026-10-10, Daniele Bordes's report)

- Cup struct byte [8] != 0 = first round in list order (DIY [4Fh] = 1), [9] = 0 = later rounds drawn. The season end
  fills the lists country by country, so a world's UEFA Cup had 31 of 32 same-country first-round ties (W128B/C).
  World structs now get [8] = 0 (careerworld.struct_for): first round drawn at random. Playtest (new career, build
  ITALIAN 24f09873): UEFA 1st round mixed, no same-country tie seen. A same-country tie can still come up by chance
  (~1 in 2 seasons for 64 clubs); the real 1984-85 rule kept them apart -> possible follow-up: swap such ties after the
  draw. Saves made before keep [8] = 1 in their W1 cups.
