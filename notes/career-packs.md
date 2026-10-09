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
