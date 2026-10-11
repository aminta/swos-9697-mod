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
- No same-country ties in rounds 1-2 (2026-10-10, branch career-euro-nodorby): RSSF 1980-90 UEFA Cup shows no
  same-association tie in rounds 1-2 (~300 ties parsed), some later. With contest byte 8 = 0 the FIRST round is
  shuffled by cseg_28139 (cseg_87DA0, list DIY_competitionStart+2CDh, [4Fh] ties), rounds 2.. by cseg_27F08 (via
  hist_draw, list A2+59h). careerworld.late hooks both (w_draw1 / w_draw -> w_fixpairs: a same-country tie swaps its
  away club with another tie's; country = low byte of the team number at DIY+24Dh). Derby test world (DERBY=1
  mkworld3: season-1 UEFA 10 x 6 + 4 clubs, ~2.5 derbies per draw expected): first build hooked only cseg_27F08 ->
  1 derby seen, debugger BP never hit; with w_draw1 (ITALIAN 1f3ae3ea) 0 derbies in 25 visible ties. Round 2 not
  checked yet. The 1996-97 game has the same flaw from season 2 (JUVE2 / APOK4: 8 of 16 UEFA first-round ties
  same-country): fixing it there changes normal careers -> Davide to decide for the next release.

### BUG (found 2026-10-10, present in 2.5 and 2.6.1 releases): Intercontinental + a European cup in the same season

- Case: JUVE2.CAR (Juventus, 1997/98; won the CC 1996/97 -> Intercontinental pair Juventus / Alianza Lima in the trailer;
  E092F = 1 = Cup Winners' Cup). Season set-up is corrupt: CWC round 1 = Juventus v Club Brugge (1st leg, 2-3) but the
  2nd leg is Juventus v AC Milan; the Intercontinental final sits among the first Serie A rounds. Playing it from the
  calendar works (4-4, pens). FINISCI STAGIONE stops on the team screen instead of the new-season message; then VIS.
  RISULTATI traps in cseg_3C4CE (`cmp word [A3], 1; jz; int 3`, IT obj1+0x2C689): DIY_competitionStart holds a 16-club
  COPPA CAMPIONI EUROPEA (id 0, [2Bh] = 2 = slot 2, [0] = 0) — slot 2 data is not the Intercontinental.
- Likely cause: sacups euro_found -> int_step builds the Intercontinental (cseg_8B2D3 into slot 2) in the middle of
  InitializeNewSeason's European branch and disturbs the CWC build (River's tested case went through the SA branch).
  Not related to the euro-128 / no-derby work, nor to other sessions' hooks (lib97 / historic check their ids).
- Next: dedicated session (after an automated DOSBox-X test harness), JUVE2.CAR as the repro (copy in the session
  scratchpad: JUVE2_orig.CAR; c/SWOS/JUVE2.CAR restored).
- ROOT CAUSE + FIX (commit 2b96905): sacups.euro_found called int_step BEFORE `mov ax, [D7]; mov [E092F], ax`; int_step
  builds the Intercontinental with cseg_8B2D3, which clobbers D7. A CC holder (always in next season's CC) that plays
  the Intercontinental got E092F = 1 (CWC) while cseg_8D661 had built the CC into slot 3. Now E092F is stored first.
  Confirmed with JUVEFIX.CAR (= JUVE2 with E092F 1 -> 0): season 1997/98 ends, 1998/99 reached with CC groups.
  Saves already made with the wrong E092F need the same one-word edit (save offset 0x173A3).
- 1996-97 no-derby (build ITALIAN 84ad6364 = 2.6.1 + both fixes): JUVEFIX -> 1998/99 UEFA round 1 random order, no
  same-country tie in the 16 ties seen (Lokeren-Juventus, Roma-Barcelona, Man Utd-Reggiana, Lazio-Vojvodina ...).
- Round 2 (2026-10-10): JUVER2 (old build) had Betis-Zaragoza in UEFA R2 = 2CDh pair (26, 28): the 1996-97 UEFA round 2
  does not go through cseg_27F08 -> w_draw2 hooks the tie copy at cseg_26CC9 (IT obj1+0x16b14: A2+59h -> A4+2CDh, both
  draw and seeded paths). Still Cagliari-Inter in R2 with that build (JUVEFIX3, CPU-simulated UEFA): suspected the
  g_gameType gate (cups the computer simulates may run outside game type 4) -> w_dok now applies ids 1/2 in every game
  mode (a world: ids 0..2 when game type 4). Build IT a9ffa81e (EN c5fbbef7 FR 0c40364c DE 1bbad94b) installed in
  c/SWOS, UNTESTED for round 2 -> to verify with the test harness (JUVEFIX3.CAR, play to the UEFA R2 draw, no derby).
- Open (original engine, noted in M2): cseg_92C4D makes room for the CC holder by replacing a random entry with a
  different ORDINAL (68000 leftover) instead of another country: Juventus (holder, 4th) in, Italian champion out
  (JUVEFIX3). Decide the 1996-97 rule with Davide.
- Holder rule 1996-97 (Davide: the holder plays in addition, as in 1984-85): the 16-club group CC cannot take a 17th
  club, so the closest real rule = the holder enters and the place goes to a club of ANOTHER country. cseg_92C4D now
  compares countries (the two `shr word [D4/D1], 8` NOPed: low byte of the team number = country; it compared ordinals).
  Applies to CC / CWC / UEFA holders of normal careers (worlds use w_holders). Build IT a0f38ad5 (EN fde8cdca FR
  70aa73a2 DE 333ec176), untested in game: next season end with a holder that missed its league place.
- Round 2 in careers (harness BP run, 2026-10-11): w_draw2 (cseg_26CC9) is never reached by career cups; there is no
  round-2 draw at all: cseg_8A7BF (end of a round, player's and simulated career cups) calls cseg_2ACAE, which puts
  the winners first at DIY_competitionStart+2CDh in tie order, and the next round pairs them two by two (fixed
  bracket). New hook w_r2 on that call: after round 1 ([4Fh] ties == [31h]/2) w_fixpairs on the winners. Build IT
  1994e494 (EN f553bb66 FR bea0ff37 DE 4af31d4f), to verify with the harness (JUVE2F -> 1998/99, UEFA R2 ties at
  slot+2CDh first 16 entries after the R1 return leg).
- Round 2, status 2026-10-11 (build IT 9216c1ec, commit after 14e6e84): w_r2 hooks every `call cseg_2ACAE`; harness
  run euro_draws (dazzling-rhodes worktree, SWOSTEST_BUILD) still FAILS: UEFA R2 Inter v Juventus. Probe
  (internal/career-test/r2probe.py: BPs on w_fixpairs call/return, records DIY_competitionStart +2Dh/+31h/+4Fh/+2CDh/
  +24Dh) shows the fix DOES run on the UEFA round-1 winners in DIY_competitionStart (2 hits with id 2 / [4Fh] 16, first
  pair (20,20) -> swapped), but the round-2 ties the player sees come from elsewhere: the slot's own +2CDh (slot buffer
  dseg_DA0E2) keeps the old order. Next: follow cseg_8A7BF's A2/A4 (it copies A4+2CDh -> A2+59h after cseg_2ACAE;
  A4/A2 may be the slot buffers, not DIY_competitionStart) and cseg_29659's flow for the player's cup; fix the list
  that actually feeds round 2.
- ROUND 2 FIXED (2026-10-11, build IT 24033dd3, EN daf2d516 FR 6d1489d3 DE 0a1fe6de): the player's cup ends a round in
  cseg_29659 (called once, from cseg_284D8): after cseg_2ACAE it copies the winners to dseg_1728B6 and REBUILDS
  DIY_competitionStart+2CDh as winners[DIY+30Dh[i]] (the next round's order), so w_r2's swap (done inside cseg_2ACAE's
  call) was undone. New hook w_r2p on `call cseg_29659`: same fix (w_r2fix) on the rebuilt list. Simulated cups
  (cseg_8A7BF) have no permutation: w_r2 alone. Harness euro_draws PASS (JUVE2F -> 1998/99, UEFA rounds 1-2, no
  same-country tie, 747 s); italy_season and roundtrip PASS.


## Europe 1984-85 world (branch world-1984-85, from 2026-10-10)

Data: DB squadre Daniele Bordes (CM01/02 Retro Update Team). Two files, used together:
- `out_2026_10_10.csv` (tab, UTF-8, 66,297 players): Daniele's SWOS conversion (P V H T C S F 0-7, PriceValue 0-49,
  role, TeamValue). Accents fixed; club names still cut at 30 chars.
- `exported_players-extended_V788_000.csv` (';', cp1252, 102 columns): the raw CM01/02 export. Full club names (the
  30-char prefixes map to one name except 4 Portuguese/Brazilian ones), side ratings (Left/Central/Right, cols 43-45:
  RB/LB/RW/LW), squad numbers. 99.6 % of the `out` rows join on (name, club[:30]).
- Gaps: coaches, kits, 1983-84 final tables (club order), national cups, real European entrants -> Wikipedia (session 2).

Scope (Davide 2026-10-10): option "c" = every single-group division the DB has full squads for; the 5 small countries
(Albania, Cyprus, Iceland, Luxembourg, Malta: generic 'A Premier/Lower Division', clubs by the players' majority
nationality) as mini leagues; Wales has no league (Wrexham, Cardiff, Swansea play in England; Wrexham's 1984-85 CWC
place to be handled in season 1). Parallel groups (C1/C2, D2 A/B, Segunda B1/B2, Oberliga, DDR-Liga, Portuguese /
Polish / Czechoslovak / Yugoslav / Swedish second tiers) left out: the engine has one chain of divisions per country.

Converter (private, internal/world8485/, git-ignored): `mkworld8485.py OUT EXT GAME OUTDIR` -> 32 career packs
(world 4, TEAM.101-132, league id CB shared, cups CC..EB, England root, start 1984, calendar dates_from 8 for all),
`short_names.csv` (hand-made 16-char names, wins over the 1996-97 game names and the generated ones),
`build.py` (test build). Squads 'explicit': 16 per club in record order G RB LB D D RW LW M M A A G D M A + best
remaining; best = PriceValue then skill sum; RB/LB/RW/LW = the most right/left-sided of the role's top 3; borrowed
roles take the slot's position; fillers (names from the same nationality's DB names, low skills) when short; 3 key
skills = the 3 highest; nationality bytes from docs/SWOS/teams.txt; skin by nationality (cosmetic); kit + tactic from
the 1996-97 record of the same club, else a random club of the same SWOS country. tools/mkseason.py: COUNTRY 'ENG' = 8.
Session 1 placeholders: club order = TeamValue, national cups generated (top 2^n <= 64 clubs, stronger wins),
europe_places guessed (Albania cc/cwc 0 so that 31 + holder = 32), first_europe = league order.
Result: 784 clubs (ENG 22+22+24+24, SCO 10+14+14, FRG 18+20, ITA 16+20, ESP 18+20, NED 18+18, BEL 18+16, AUT/SUI/DEN
16+16, URS 18+22, HUN 16+20, the others one division), `mkseason check` OK (cups 32/32/64), build IT 9b8f8626
EN bc9ce7bb FR 4ee86e86 DE b657d9f5. Installed in c/SWOS (ITALIAN.EXE + TEAM.101-132 + WORLD04.TMD; the previous test
exe 24f09873 and world-3 TEAM.1xx saved in c/W3BAK). First smoke test = engine scale (92-club England, 784 clubs).
Season 1 note: the engine needs places + 1 = cup size per cup, while in 1984-85 Liverpool was both holder and English
champion -> exact season-1 entrants need first_europe lists not tied to the places (mkseason relax, to study).
- Playtest 1 (Davide, Exeter, 2026-10-10): season end exited to DOS after "ENGLAND FA CUP FINALE" with a foreign
  finalist (FC PORTO, then AZ '67). Dump (DOSBox-X debugger under a pty bridge, MEMDUMPBIN after the exit; obj1 at
  linear 0x263000, obj2 0x30C000; return addresses left on the stack at ~0x3D1D00): cseg_91857 -> cseg_928CC ->
  cseg_929BB (copies the 2 finalists from DIY_competitionStart+2CDh/+24Dh) -> VerifyTeamLoaded -> EndProgram. Cause:
  SaveSelectedTeams / RestoreSelectedTeams park only 32 cached records (21888 B at dosMemOfs60c00h) while the season
  end simulates a contest in the same cache; the career cache was 64 FA Cup + 24 league clubs, so records 32..63 came
  back as the simulated UEFA clubs. World 3 never hit it (exactly 32 own clubs cached). Fix (careerworld, big worlds
  only): both procs park count + 100 records at BSS+0x16000 (BSS_SIZE 0x16000 -> 0x27000). Builds: world 4 IT
  0483cb8f EN 548a771d FR 057f5bae DE e4ba0487; world 3 IT 2920e8fb; no-world IT d38a5d1c (2.6.1, unchanged).
- Playtest 2 (Davide, 2026-10-10, build 0483cb8f): EXE1.CAR loaded, season 2 ended (sacked at Exeter, then Port Vale),
  saved PORVALE.CAR: checkw1 k 128, N 84, W1 ok, sum 0, cups 32 / 32 / 64 without duplicates. Next: load + season 3.
- Playtest 3 (Davide, 2026-10-10): game restarted, PORVALE.CAR loaded, season 3 ended (Colchester), COLCHEST.CAR:
  k 128, N 83, W1 ok, sum 0, cups 32 / 32 / 64, no duplicates. ENGINE OK for the 784-club world (3 seasons + load).
  Next (session 2): real data from Wikipedia (1983-84 tables, coaches, 1984-85 national cups, European entrants and
  places, exact season-1 lists -> mkseason relax), short-name review with Davide, credits.
- Session 2 (2026-10-10), real data, converter now config-driven (internal/world8485/world.json + europe_1984_85.json +
  tables_1983_84.json + short_names.csv; fetch/parse helpers r1.py, tables.py, titles.txt): European entrants = the
  real first rounds (Wikipedia): CC 32 (31 champions + Liverpool holder/champion; Albania cc/cwc 0 from season 2),
  CWC 32 (no Albania, Wrexham listed with England in season 1), UEFA 64 (England 4 + Tottenham holder, FRG/ESP 4,
  ... 1 for the small countries); places from season 2 = the same counts. tools/mkseason.py: first_europe may list
  any number of clubs per country, the world check is each cup's total = places + 1. Club order = 1983-84 final
  tables (1983 for calendar-year leagues): same level by position, then relegated from above, then promoted from
  below, clubs in no table by strength (165, mostly promoted clubs; no tables for BEL/AUT/SUI/DEN second divisions).
  Iceland and Malta capped at 10 clubs (previous table's clubs first). 772 clubs. Build IT 9c252bfe EN db943872
  FR 037adb9e DE 4420d57b (not installed). Still open: real national cups 1984-85, coaches (ask Daniele for a staff
  export of the CM DB), short-name review by Davide.
- Session 2b (2026-10-11): coaches (it/es/nl/pt/fr.wikipedia season tables + Wikidata P286/P6087 in Aug-Sep 1984,
  coaches.py) -> 222 clubs (ITA/NED complete, ESP/FRG 34 of 38, POR 14, ENG 25 = First Division, few elsewhere).
  Real national cups 1984-85 (cupparse.py: any of OneLegResult/TwoLegResult/footballbox/wikitables/RD-brackets per
  round section, replays merged; a winner = the club in the next round): the first round of 8..64 clubs whose next
  rounds halve; participants outside the leagues = cup-only clubs (a 'cuponly' file per country, files 133-144,
  bases after all leagues, contiguous) with their DB squad when the DB has them (same nationality), else invented.
  15 countries real (ENG FA Cup 3rd round 64 incl. Dagenham, Telford; FRG 64; NOR 64; ITA/ESP last 16 ...), the
  others generated. 949 clubs. One-command harness internal/world8485/run.sh (convert -> check -> build). Build IT
  b7b870a9 EN 0ab28390 FR 489fe4e5 DE 78a87742, 44 team files 1xx. Cup-only files in a world: untested in game.
- Automated test (test-harness session, tools/swostest.py run world8485, 2026-10-11): PASS on IT 4c280af8 (= 9b9b10b,
  real European entrants + table order + coaches, generated national cups). New career Liverpool, results-only loop,
  season end, CONTINUA CARRIERA, save, reload, season 2 (Liverpool last -> sacked -> first offer Plymouth Argyle,
  1986/87). No freeze/trap. W84A (start 1985/86): k 128, N 64, C7, W1 ok, world 4, sum 0, cups 32/32/64, dups 0;
  W84B: k 128, N 73, same checks ok. Saves in internal/swostest/saves/. Albania (file 129) absent from the cups
  from season 2: expected (no places: cc/cwc 0 by choice, uefa 0 as in 1984-85). Build with real national cups and
  cup-only files (b7b870a9): own scenario internal/world8485/test_w8485.py running.
- Automated test PASS on IT b7b870a9 (real national cups + cup-only files 133-144, 949 clubs), 2026-10-11:
  swostest world8485 (test-harness 1c0e99c, W8485_BUILD = that build), 3880 s: season 1 219 steps, season 2 148
  steps, no freeze/trap; W84A and W84B: k 128, W1 ok, world 4, sum 0, cups 32/32/64, dups 0, bad pairs 0.
- Release 3.0 prep (2026-10-11, branch release-3.0 = euro9697-nodorby + world-1984-85 + test-harness): world packs in
  packs/europe-1984-85 (built by default, mkseason WORLDS), short names via world.json 'short_strip' (converter in the
  world-1984-85 worktree's internal/world8485), credit DaniSwos. Builds in c/REL30 (c/SWOS untouched): IT b5bba176 EN
  c6679535 FR b38d9024 DE 043a5052, GOG IT 2542baa0 EN 4ecff1f9 FR 38ab1410 DE 4eeec1c5, SWOS++ 21897e1b / e55ebc98,
  WORLD04.TMD 0db4960d; patcher: PATCHER_BUILD=c/REL30 python3 tools/mkpatcher.py. Harness: world8485 PASS (Liverpool, 2
  seasons, R1 checked), world R2 checked with W8485_TEAM="WEST GERMANY,BUNDESLIGA,BAYERN MUNCHEN" W8485_R2=1: CWC round 2,
  8 ties, no same-country tie (Liverpool, Juventus, Everton went out in round 1).
