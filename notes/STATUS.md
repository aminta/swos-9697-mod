# SWOS 96/97 ITA mod — status

## Decisions (2026-09-29)
- Target: patch original DOS ITALIAN.EXE (md5 60cdb6b1e7418f206fee7a7b4b0ae911)
- C1 and C2: single 18-team divisions (no parallel gironi)
- Euro cups: 1997-98 format (CL 6 groups of 4) — details in session 6

## Session 1 — tooling (done)
- tools/le.py: LE parser (objects, page->file mapping, internal fixups). obj1 code @0x10000, obj2 data @0xC0000
- tools/addrmap.py -> notes/addrmap.json: ENGLISH->ITALIAN piecewise deltas (obj1 11 runs, obj2 16 runs)
- swos-port swos/swos.asm labels == ENGLISH.EXE VAs (verified: cseg_914F1 = assert)
- 80-team assert: ENG va 0x914F1 -> ITA va 0x91345 (verified by signature)
- DOSBox-X: dosbox-swos.conf, game installed in c/SWOS, CD = orig/swos9697ita.iso. Boots, intro FMV plays.
  ("Packed file is corrupt" warning in log is harmless so far)

## Next: session 2 — reproduce + understand
1. Fast path to end of season (edit career save near season end, or test patch that auto-resolves user matches)
2. DOSBox-X debugger breakpoint at 0x91345 / ContinueCareerNextSeason
3. Add minimal C1 (league table in exe + teams in TEAM.020), trigger the freeze, read how the 80 teams are collected (cseg_92BBF, RestoreSelectedTeams, dseg_180784/86/88)

## Session 2 — findings (2026-09-29)
- Italy league struct (ITA obj2+0x8032, 42 B): hdr10 [num,type,country,start,end,nameOff,0,0,0,nDiv] + 02 03 35 + 6 B/div
  [teams, promDirect, promPlayoffTeams, relegated, relPlayoff, playoffData] + 00 + 2 name dwords/div (offset from aChairmanScenes = obj2+0x183a).
  England has 4 divisions with same format -> 4 levels supported.
- teamsCountryNumbers (ITA obj2+0xb28b0): Italy base 424 (file 0x1F72D8 = A8 01), only 51 slots (Latvia starts at 475).
  someLeaguesTable[2000] stores per-global-team promotion/relegation deltas (SetLeagueNumbers) -> >51 Italian teams collide with Latvia
  -> likely the 1997 freeze (FatalError = int 3; jmp $). Free global numbers ~1794..1999.
- tools/patch.py: Italy base 1850; 4-div struct (A18/B20/C1 18/C2 18, 4 up/4 down) in obj1 slack @0xa09d0, obj1 vsize->0xa1000,
  italyTable fixup widened 16->32 bit (fixup table grows 2 B into 505 B padding). TEAM.020 -> 74 teams (13 non-league -> C1 + placeholders).
- Patched exe boots. PENDING: user playtest of career season end (results-only mode).
- 2026-09-29 PLAYTEST 1 (user, Serie A team, results-only): career season 1 end OK, no freeze. 4 leagues visible.
  CARRIERA.CAR: first 80 records = next-season euro teams (count 80 ok). someLeaguesTable @ save off 59352 (no Italian entries:
  player's nation kept as full records in save cache, 45/74 present). Moves verified: A<->B 4/4, B<->C1 4/4, C1->C2 seen.
  NEXT: user plays 2 more seasons + short career from a C2 team. Optional proof: rebuild with ITALY_BASE=884 to reproduce old freeze.
- PLAYTEST 2 (user): career from a C2 team, 2 seasons, no freeze (CARR2.CAR). Italian league moves of the player's nation are
  [WRONG: read at save off 59352; the table is at 0xE8DC and does hold Italian moves, cumulative since career start (FE/02 seen)]; save caches only some team records -> league layout of the
  player's nation lives elsewhere in the save (not yet decoded). Career fix considered working (sessions 2-4 goal met).
- 1997 method (user recollection): inserted bytes between Italy and Latvia league structs. ~50 nation league structs follow Italy
  (latvian_league ... ghana_league) and are reached via fixed fixup pointers -> all read shifted by N -> garbage leagues,
  only processed at season end (world-wide promotions) -> FatalError. Plus global-number overlap. Zero runs at obj2+0x8d44.
  Optional repro: "1997-style" exe (+28 after Italy, -28 at 0x8d44).

## Idea: Copa Libertadores in career (discussed 2026-09-29)
- Unused string aSouthAmericanCup 'SOUTH AMERICAN CUP*****' (no xref). argentinaTable = league only. Club cups only in europeTable
  (euroCup 16, cupWinnersCup 32, uefaCup 32) + country list bytes; continental_cups = national-team cups.
- Level 1 (recommended, ~3-4 sessions): SA career swaps the 3 euro slots -> Libertadores/Supercopa/CONMEBOL, SA country list, SA TMD.
- Level 2 (~6+ sessions, high risk): both continents + Intercontinental Cup.
- Order: after sessions 6-7 (euro cups), as sessions 9-11.
- DECISION 2026-09-29: ADD (not replace) Libertadores, Supercopa, Copa CONMEBOL to whole game + career.
  European career: SA cups simulated round by round, viewable in competitions menu (option b) -> enables real Intercontinental.
  Plan: 9-10 SA cups in preset comps (+TMD files, cup loader, southAmericaTable relocation, tmd buffer 80->160 via obj1 BSS growth);
  11-13 career integration; 14 Libertadores 1997 real format (groups); 15-16 Intercontinental (optional).

## Session 5 — C1/C2 data (2026-09-29)
- tools/c1c2.py: real 1996-97 clubs (it.wikipedia standings). C1 = 10 existing (Acireale, Ancona, Ascoli, Avellino, Como, Fidelis Andria,
  Modena, Monza, Pistoiese, SPAL) + Treviso, Brescello, Carpi, Saronno, Prato, Nocerina, Casarano, Juve Stabia.
  C2 = Pisa, Taranto, Ternana + Lumezzane, Lecco, Livorno, Battipagliese, Turris, Benevento, Catanzaro, Triestina, Rimini, Frosinone,
  Sandona, Pro Patria, Catania, Pro Sesto, Cittadella. Kits approximate. New clubs: random Italian player/coach names (seed 1997),
  skills/positions copied from non-league templates. TEAM.020 sorted alphabetically (old test saves now incompatible).
- Real rosters: deferred (user: "per ora non preoccupiamoci delle rose").

## Session 9 — SA cups: analysis started (2026-09-29). User skips 6-8 for now: wants to play SA career seasons first.
- Career season = 5 contest slots (InitNewSeason, arrayOfPointers): competitionFileBuffer, dseg_D8D0A, dseg_D985C, dseg_DA0E2,
  dseg_D9C9F. Slots 0-2 from country table (league, then after -2: cup, league cup) via cseg_8B2D3(D0=slot).
- InitializeNewSeason: checks player's membership in euroCupCopy / cupWinnersCupCopy / uefaCupCopy via cseg_8D661 (D7=0/1/2);
  cseg_8D661 reads team list at cup+7+[cup+7], count by cup type ([+1]==1 -> [+0Ah], 2 -> [+0Fh], else [+0Dh]).
- Qualification engine (end of season) = cluster cseg_92BBF..cseg_9423A: cseg_92D55 (euroCup), cseg_9307A (CWC), cseg_9339D (UEFA),
  cseg_936C0 (combine), cseg_93B30/93B9C/93BB5/93C19/93C3C/93C5F (add to lists, counters dseg_180784/86/88 = 16/32/32),
  cseg_91428 = final assert (80 total). Also InitCareer, ProcessCareerFile, __init_80x87 (europeTable), LoadSomeEuroCup
  (eurocup.tmd/uefacup.tmd/eurocwc.tmd -> tmdFileBuffer, SetTeamGlobalNumbers).
- OPEN QUESTIONS for next session: (1) are euro cups the player is NOT in simulated round by round, or only resolved at season end?
  (2) how qualifiers are picked from foreign leagues (standings are not played); (3) where slot 3/4 get the player's euro cup;
  (4) career menu "view competitions" source list.
- Design sketch: SA cups = clone of euro path keyed on continent (southAmericaTable relocated w/ club cups + country list),
  new TMDs from TEAM.043/045/046/048/049/050/064/065/071/077 (ARG BOL BRA CHI COL ECU PAR PER URU VEN, ~200 clubs),
  second 80-team buffer in obj1 BSS (grow vsize), trophy bits 10-15 free, name string aSouthAmericanCup unused.
- USER ANSWER (gameplay): (1) euro cups the player is NOT in ARE simulated round by round. (2)-(4) re-asked in player terms:
  foreign league tables visible? foreign qualifiers = strongest clubs or random? which competitions appear in career competitions menu
  (all 3 euro cups even if not qualified?).
- USER ANSWERS cont.: (2) foreign league tables ARE viewable anytime; foreign cup qualifiers look standings-based, not random.
  (3/4) career competitions menu (Maltese club in Champions Cup): "Malta prima divisione, Malta coppa, Coppa campioni europea"
  = only player's own contests. "Visualizza mondo" shows, at any time, league + national cup + continental cups of EVERY nation
  -> whole world is tracked (find how: likely per-country simulation/generation on view; SA cups must show in world view under
  South America / continental, and in player's list when qualified).
- WORLD VIEW (user screenshots, career "Visualizza mondo"): EUROPA = 3 green cup buttons on top (COPPA CAMPIONI EUROPEA,
  COPPA D. COPPE EUROPEA, COPPA EUFA) + 3-col grid of 43 countries + ESCI. SUDAMERICA = 11 countries (ARG BOL BRA CHI COL ECU PAR
  PER SUR URU VEN) in grid, NO cup buttons, empty space on top. Goal: 3 green buttons (LIBERTADORES, SUPERCOPA, CONMEBOL) there.
  Menu likely built from europeTable club-cup entries + country byte list -> check if southAmericaTable entries would render the same.
- Hex-editor-only analysis: zero runs reachable with 16-bit fixup (obj2 0x6a16, 0x8df8, 606 B each) are unused slots of
  country-indexed tables (0x8df8 is INSIDE competitionsTable @0x8c66, 256 dword entries) -> not safely free.
  italyTable fixup record file 0x9c4ea = 07 00 ae 02 02 32 80 (src page off 0x2ae, obj2, target 0x8032).

## Session 9 (cont.) — SA cups step 1 implemented (2026-09-29, untested in game)
- Disassembly now kept locally: ref/swos.asm, ref/symbols.txt, ref/docs (was only in /tmp). tools/asmbytes.py dumps db bytes of a label.
- WORLD VIEW MECHANISM: ViewWorldMenu -> ChooseCompetitionMenu -> SelectTeamsFinalMenu(showCupsAndOther=1): every pointer in the
  continent's competitionsTable entry becomes a button (euro club cups not special-cased; national cups filtered in career).
  Selecting one -> cseg_3AA17: looks up careerContests (static struct -> copy + size); if it is one of the player's 4 slots shows live
  state, else cseg_3ABB2 REGENERATES it on the fly: Randomize2(seed = contest id<<8 | seasonPlaying), InitTeams, simulate to date.
  => contests the player is not in have NO persistent state; SA cups need no save data to be viewable.
- Contest struct: [0] id [1] type (1 knockout, 2 groups+KO) [2] country FF [3][4] months [5] names @+5+[5] (2 dwords, string VA -
  (obj2+0x16F8)) [7] team list @+7+[7] [8] 1=fixed list; type1: [10] teams, [14..] 1 byte/round (0x94 2 legs, 0x14 final) then 00.
  type2 (euroCup): [15] teams, groups of 4. Team list = (TEAM file number, index) byte pairs.
- Free contest ids: 0x6C..0x7B (used: leagues 0x24-0x6B, customs 0x7C, cups 0x7D-0xB1).
- dseg_C707E (ITA obj2+0x71C8, 45 entries, 3 code refs) = international contests -> DIY field 0x3B = 0 (sim flag, CalculateViewResult).
- tools/lepatch.py: rebuilds LE fixup tables (retarget/add_ptr, grows section and moves data pages if needed). Round-trip identical;
  Italy patch through it identical to the playtested exe. Fixup padding left ~16 B (next additions will move data pages: supported).
- tools/sacups.py: COPA LIBERTADORES (0x6C, euroCup clone, 16 teams 4 groups), SUPERCOPA (0x6D) and COPA CONMEBOL (0x6E) (16-team
  two-leg knockouts), 1997 entrants from TEAM.043-077; new South America table in obj1 cave (WCQ, Copa America, 3 cups);
  intl list relocated + 3 cups. Cave used to obj1+0xA0C00 (of 0xA1000).
- BUG FIXED: TEAM.020 re-sort (session 5) broke Italian clubs in preset euro cups (Juventus->Cosenza...); patch.py now remaps by name.
- NEXT: playtest (preset competition -> Sudamerica -> 3 cups; career world view Sudamerica; a match; euro cups still OK).
  Then career: careerContests entries? (not needed for viewing), yearly qualifiers from SA league standings instead of fixed lists.
- PLAYTEST 3 (user): Sudamerica preset shows 3 new buttons, Libertadores opens with the 16 right teams, BUT names garbage:
  name offsets are relative to obj2+0x16F8 (same base for leagues; "chairman 0x183a" was wrong for ITA) and obj1/obj2 are NOT
  loaded at file distance -> strings in obj1 cave break (SERIE C1/C2 too, since session 2). FIX: tools/strpool.py puts new names
  in obj2: unused '.COPPA AFRICANA CLUB' (27 B) + 'COPPA SUDAMERICANA' (24 B) + '*' padding of 2nd 'COPPA EUFA' (14 B). Pool now FULL.
  Rule: never store obj2-relative offsets to obj1 data; pointers across objects only via fixups.
- PLAYTEST 4 (user): all OK — SA cup names, euro cups (Juve/Milan), COPPA EUFA name, career world view, SERIE C1/C2 names.
  Career with RIVER PLATE: "Visual. competiz." lists only ARGENTINA PRIMA DIVISIONE -> expected: player's slots only know the
  3 euro cups (InitializeNewSeason/cseg_8D661 on euroCupCopy/cupWinnersCupCopy/uefaCupCopy). River is in the fixed Libertadores
  list, so the world view simulates River in the Libertadores while the player is not in it. NEXT (sessions 10-11): player's
  SA cup slot (membership check + slot fill for SA cups), then yearly qualifiers from SA standings.

## Session 10 — player's club enters SA cups (2026-09-29, untested)
- Every season: ContinueCareerNextSeason -> InitializeNewSeason (also from InitCareer). Euro cup entry = chain of cseg_8D661(A0=cup copy,
  D7=0/1/2): scans team list words vs selTeamNumber (lo=file, hi=index); hit -> cseg_8B2D3(D0=3) loads cup into slot 3,
  dseg_D8CBE = dseg_E092F = D7. ProcessCareerFile (load save) maps E092F 0/1/2 -> dseg_D8CB6 (slot-3 contest ptr); other values -> none.
  D8CBE users: cseg_3D7CB trophy flags (0 CC, 2 UEFA, else CWC), cseg_5DEB9 bonus (1 CWC, 2 UEFA, else CC formula).
- ITA addresses: A0 obj2+0x315D7, D7 obj2+0x315D3, E092F obj2+0x20A79, cseg_8D661 obj1+0x7D4B5, hooks obj1+0x7D307 (11 B) and
  obj1+0x237FD (12 B). Disassembler: ndisasm (/opt/homebrew/bin), hand-assembled via sacups.Asm; lepatch.remove() drops fixups of
  overwritten instructions.
- sacups.career_hooks: InitializeNewSeason tries Libertadores/Supercopa/CONMEBOL with D7=3/4/5; ProcessCareerFile maps E092F 3..5.
  KNOWN: SA cup win sets the CWC trophy flag (fix with trophies); bonus = Champions Cup formula. Fixups grew past padding:
  data pages moved +0x200 (first time; LE re-parses fine).
- TEST: new career RIVER PLATE -> competitions should list COPA LIBERTADORES; play/sim a group match; save + reload career, cup still there.
- PLAYTEST 5 (user): WORKS. River Plate career: COPA LIBERTADORES in competitions, group draw by game, played River 2-1 Barcelona,
  survives save/reload ("river" save). World view CONMEBOL simulated fine.
- Lanus career -> COPA CONMEBOL entered (slot value 5 verified).

## Session 10 (cont.) — step 2a: SA qualifiers from standings (untested)
- Season end (cseg_91428): cseg_936C0; national stuff; cseg_92D55/9307A/9339D (build euro cup lists from last season's TMD
  results?); careerFileBuffer=0; player's country cseg_9153F + cseg_93974; then every country in dseg_C943A (Europe) the same;
  assert careerFileBuffer==80 (CN_EUROPE marker) and counters 16/32/32; cseg_92BBF.
  cseg_9153F(country): league -> cseg_91D4D (per division: player's live one via cseg_8B6B0 copy slot0->DIY + table menu, others
  cseg_915ED = cseg_3ABB2 world-view simulation of the whole season); div 0 -> cseg_927A2 top 9 team numbers -> dseg_180715 (+ team
  data -> dseg_1807C2); cseg_93FD8/9221F/9228D promotions. Cup (91857), league cup (91AD0). cseg_93974 adds qualifiers to TMD buffer.
- DIY_competitionStart (ITA obj2+0x4EFF3) = working contest; league layout: +31h teams, +6Dh row offsets in finishing order (rows 12h B),
  +12Dh team number per row. Slot 0 competitionFileBuffer (obj2+0x1F640) same layout (cseg_8B71C copies 0x733 B).
  ITA vars: A1 315DB A2 315DF A3 315E3 A4 315E7 D0 315B7 D1 315BB D2 315BF; dseg_D8CAA obj2+0x18DF4, dseg_D6CDC obj2+0x16E26.
- sacups.qualify_hook: call cseg_92D55 @obj1+0x812C4 -> sa_qualify (nasm, tools/nasmcave.py finds fixups by triple assembly):
  per SA country simulate top division via cseg_915ED (player's own top division: read slot 0), write ranks into Libertadores
  (champions of 10 countries + runners-up ARG BRA URU PAR COL CHI, 4 mixed groups) and CONMEBOL (next places, 8 pairs) lists.
  Supercopa list fixed. obj1 flagged writable (0x2047). Cave used to obj1+0xA0DD2 (0x22E left).
- NOT persisted: after loading a save the lists are the 1997 defaults again until next season end (only world view of cups the
  player is not in is affected; entry is decided right after season end in the same session). Step 2b = persistence.
- TEST: career (e.g. River, results only) to season end, no freeze; new season Libertadores = ARG champion etc.; world view
  Libertadores/CONMEBOL show new clubs; also a European career season end still OK.
- PLAYTEST 6 (user): step 2a test 1 PASSED (River season end, no freeze, next-season SA cups from standings). European season end: pending.
- Euro rules confirmed in code: cup winners stored (18070F/711/713) and auto-entered in the same cup next season (cseg_92BBF ->
  cseg_92C4D bumps a random qualified team to keep 16/32/32; cleared by cseg_93BCE if already qualified via league);
  per country cseg_93974: CC = champion, CWC = national cup winner skipping champion/CC holder (finalist steps in), UEFA = next ranks.
  User wants: Libertadores holder auto-entry (proposed: replaces own country's runner-up slot, else CHI2); open: new Libertadores
  winner into Supercopa (drop last), CONMEBOL holder rule.
- PLAYTEST 7 (user): step 2a test 2 PASSED (Italian career season end OK). User: follow real 1997 rules (Lib holder auto-entry, new Lib champion -> Supercopa, no CONMEBOL holder rule).
- Step 2a+: Libertadores holder rule (real 1997: holder defends title AND plays Supercopa as former champion). sa_qualify prologue:
  [A4]=Libertadores, call cseg_92D55+10 (skips "mov [A4], euroCupCopy"): finishes the cup (player's slot 3 if he plays it,
  else cseg_3ADAE simulation) and cseg_92F1C writes the winner to dseg_18070F (ITA obj2+0xC058B; the real cseg_92D55 overwrites it
  right after). After the standings: winner not in new Libertadores list -> replaces its country's runner-up slot (BRA/ARG/PAR/CHI/
  URU/COL), else CHI2 (group G3 has no BOL/ECU/PER/VEN); winner not in Supercopa -> takes Supercopa last slot (rotating 16th place).
  No CONMEBOL holder rule (real). Code 248 B, cave to obj1+0xA0E5A.
- PLAYTEST 8 (user): Bolivar (Bolivian champion) won the Libertadores -> next season in BOTH Libertadores (BOL1) and Supercopa (last slot), no freeze.
  Holder-replaces-runner-up path NOT yet exercised (Bolivar qualified via league).
- Discussed 6th career slot: not worth it (slot ptrs D8CAA..D8CBA followed by D8CBE, arrayOfPointers followed by slot-1 buffer,
  ~250 refs in ~100 procs, save format). SA clubs have empty slots 1/2 -> use slot 1 for Supercopa (double participation).

## NEXT SESSION (11)
1. Double participation Libertadores (slot 3) + Supercopa (slot 1) for SA clubs: InitializeNewSeason slot-1 fill when country has
   no cup; ProcessCareerFile restore of slot-1 ptr (dseg_D8CAE) on load; end-of-season with no country cup; trophy/bonus.
2. Step 2b: persist SA cup lists (Lib/Sup/CON, 96 B) across save/load (hook SaveCareerFile/LoadCareerFile trailer, or free bytes).
3. Trophies for SA cups (bits 10-15 free), then Intercontinental.

## Session 11 — double participation: Supercopa in slot 1 (2026-09-30, untested)
- Slot buffers ITA obj2: s0 0x1F640, s1 0x18E54, s2 0x199A6, s3 0x1A22C, s4 0x19DE9; careerFileBuffer 0x96D6 (= save offset 0).
  Slot buffer header: +0 type word, +2Bh slot index, +2Dh contest id (verified in RIVER/BOLIVAR/CARRIERA saves), +27h name ptr.
  Slot contest ptrs dseg_D8CAA..: ITA 0x18DF4 + 4*slot. selTeamNumber obj2+0x16E20. cseg_8B2D3 obj1+0x7B127 (slots 1/2 accept only
  type-1 knockout cups), GetCurrentSeasonPointer obj1+0x2915F, season info cup name at +1Ah (slot 1).
- career_hooks rewritten in nasm (CAREER_ASM): InitializeNewSeason: if slot 1 empty (no national cup) and club in Supercopa list
  -> Supercopa loaded in slot 1 exactly like a national cup; slot-1 id byte cleared first so stale saves don't restore it.
  Then slot 3: Libertadores, Supercopa (only if not in slot 1), CONMEBOL. ProcessCareerFile: new hook at obj1+0x237C1 restores
  dseg_D8CAE = Supercopa when slot-1 buffer id == 0x6D, plus the slot-3 mapping hook. nasmcave.labels() reads nasm map files.
- obj1 cave almost FULL: used to 0xA0F32 of 0xA1000. Next code needs a new home (e.g. add an obj1 page, or reclaim dead code).
- KNOWN: Supercopa win in slot 1 counts as national cup trophy/bonus (fix with trophies).
- TEST: new career RIVER PLATE -> competitions: league + COPA LIBERTADORES + SUPERCOPA; fixtures of both in calendar; save+reload
  keeps both; BOCA JUNIORS -> league + SUPERCOPA only. Old saves (BOLIVAR.CAR: Supercopa in slot 3) still load.
- PLAYTEST 9 (user): ALL PASSED. River: ARGENTINA PRIMA DIVISIONE + SUPERCOPA (slot 1) + COPA LIBERTADORES (slot 3); Boca: Supercopa only;
  save/reload OK; old BOLIVAR.CAR loads. "CAPO CANNONIERI NAZIONALE" entry = original menu item (viewCompetitionsMenu has a fixed
  TOP GOAL SCORERS button -> TopGoalScorersMenu, shown once there are scorers), not a contest.
- CODE SPACE: lepatch.add_object_page(data, 1) adds a 4 KB page to obj1: physical page N+1 appended at file end (old last page
  zero-padded to 4 KB, last_page=0x1000), page map entry inserted after obj1's pages, empty fixup-page entry, header table
  offsets +4/+8, obj2 page_idx+1. obj1 vsize 0xA2000. All SA code/data now in the new page from obj1+0xA1000 (used to 0xA151A,
  ~2.7 KB free); old cave 0xA0A18-0xA1000 free again (~1.5 KB). obj diff vs original = only intended patches (checked).
- PLAYTEST 10 (user): new obj1 page build ALL PASSED: boot, preset SA cups, River career (league+Supercopa+Libertadores), save/reload,
  season end: ALIANZA LIMA won the Libertadores -> next season in Libertadores AND Supercopa; River mid-table -> Supercopa only
  (slot 1, former champion). Session 11 DONE.

## NEXT SESSION (12)
1. Step 2b persistence: SA cup lists (Lib/Sup/CON 3x32 B) + LIBWIN across save/load (sidecar file next to .CAR written/read
   by hooks in SaveCareerFile/LoadCareerFile, or free bytes inside the saved range).
2. Trophies for SA cups (bits 10-15 free; today: Lib/CON win -> CWC flag, Supercopa in slot 1 -> national cup flag) + bonuses.
3. Then Intercontinental (Libertadores winner vs Champions Cup winner), or back to euro cups 1997-98 format (sessions 6-8).

## Session 12 — step 2b: SA lists persisted with the career (untested)
- someLeaguesTable ITA obj2+0x17FB2 (save offset 0xE8DC, verified in saves: +/-1 deltas at real teams), leaguesTableCopy obj2+0x5953C.
  Season end: cseg_8CC0A copies some->copy, promotions edit the copy, InitializeNewSeason cseg_8CC4E copies copy->some.
  InitCareer zeroes someLeaguesTable (new career). Global numbers 1730..1849 belong to no team file.
- someLeaguesTable[1740..1837] = 'SA' (0x4153) + Libertadores/Supercopa/CONMEBOL lists (3x32 B), mirrored in leaguesTableCopy.
  lists_out (season end, new career) writes both; load_slot1 (every load) restores lists from it, or the 1997 DEFAULTS when no
  marker (old saves); init_sa: no marker (new career) -> DEFAULTS + write. LIBWIN not persisted (recomputed at season end).
- PLAYTEST 11 (user): FREEZE at season end right after the Argentine division table. CAUSE: cseg_9487A (end of cseg_9153F per country)
  asserts sum of leaguesTableCopy[0..1999] (bytes, mod 256) == 0 and the player's country file slice == 0 -> our block broke it.
  FIX: balance byte at someLeaguesTable[1838] = -(sum of the 98 bytes), mirrored in the copy (99 bytes). Also dropped rep movsb
  (byte copies through DS only). Build md5 22ec217f. Lesson: any data parked in game tables must respect the game's checksums.
- PLAYTEST 12 (user): PERSISTENCE WORKS. River season end passed (checksum fix), RIVSA.CAR holds 'SA' lists (table sum 0),
  after full DOSBox restart + load the world view shows the saved lists (not 1997). tools/salists.py decodes a save.
  Holder rule exercised: ALIANZA LIMA (holder, 2nd in Peru) took the CHI2 Libertadores slot + Supercopa last slot.
  OPEN: Alianza also in CONMEBOL (as PER2) -> fix: holder's CONMEBOL entry goes to the team it displaced in the Libertadores.

## Session 12 (cont.) — holder/CONMEBOL fix + trophies (untested, build md5 8e6aeeb4)
- Holder re-entered in the Libertadores: the club it displaces takes the holder's CONMEBOL place (no club in both).
- Trophies: season record (ManagementRecordMenu) already names the slot contests + result (COPA LIBERTADORES - WINNERS).
  Trophy bits built in cseg_39392 from flags D6C64 (CC, bit 2, rep +100), D6C68 (UEFA, bit 3, +50), D6C66 (CWC, bit 4, +50);
  cseg_3D7CB picks the flag from dseg_D8CBE (ITA obj2+0x18E08), cseg_5DEB9 the prize. init_sa now sets D8CBE = D7-3 on an SA hit:
  Libertadores counts as Champions Cup, Supercopa (slot 3 only) as CWC, CONMEBOL as UEFA. Supercopa in slot 1 = national cup win.
  Real SA trophy names/bits would need strings (obj2 pool full) + display work: not done.
- TEST: River season end with the holder case; winning Libertadores -> reputation like CC.
- Intercontinental step A (untested): COPPA INTERCONTINENTALE id 0x6F, type-1 knockout 2 teams, one round 0x14 (single match),
  default Juventus - River Plate (Tokyo Nov 1996). In SA world view/preset table + intl list. Name from strpool: 'ERRORE DISCO'
  + 26 stars truncated (25 B free, 1 left). NEXT: season end -> [CC winner (dseg_18070F after cseg_92D55), Lib winner];
  persistence (+4 B in saved block); career entry (slot for CC/Lib winner next season: SA club slot 1/2, euro club slot 2?);
  also show it under EUROPA (europeTable relocation).
- Europe table relocated too (obj1+0xA110C: 252, EC, CC, CWC, UEFA, Intercontinental, -1, 43 countries); build md5 4c22ce5c.
- PLAYTEST 13 (user): Intercontinental OK in preset Europa + Sudamerica (5 green buttons fit), plays as single final Juventus - River,
  world view OK. Career entry was missing (expected).
- Intercontinental step B (untested, md5 4497736e): career entry in SLOT 2 (league-cup slot, free for Italy and all SA countries):
  init_sa loads it when dseg_D8CB2 (obj2+0x18DFC) == 0 and the club is one of the two finalists; slot-2 buf obj2+0x199A6
  (+2Dh id cleared each season), season info name at +1Eh; load_slot1 restores D8CB2 when slot-2 id == 0x6F.
  NOT YET: finalists update at season end (CC winner dseg_18070F after cseg_92D55 + LIBWIN) + persistence (+4 B);
  countries with a league cup (England, Scotland, ...) have no free slot 2.
- Contest months: [3]/[4] = 8*month from January of the season's first year (>=12 next year): euro 0x40-0x20 Sep-May, Copa America 0x88-0x90 Jun-Jul next year. Intercontinental set 0x58-0x60 (December, window to January). md5 in next line.
5c219bfd17abbcad37ca6218f2b61560
- FIX: Juventus did not get the Intercontinental: init_sa only runs on the 'no cup' branch. int_step is now a subroutine, also called from a new hook on the 'found' branch (obj1+0x7D312, 12 B, both fixups removed) -> euro_found. md5 b399ba01. River test (slot 2) PASSED before the fix.
- PLAYTEST 14 (user): Intercontinental in career PASSED for Juventus (slot 2 via euro_found) and River; match falls in December.

## NEXT SESSION (13)
1. Intercontinental finalists at season end: sa_qualify calls cseg_92D55 itself (instead of jmp), then INTLIST = [dseg_18070F CC
   winner, LIBWIN]; persist the 4 bytes (extend saved block 1740.. to 1843 + balance byte; lists_in/out + DEFAULTS).
2. Test pending from session 12: holder -> CONMEBOL swap; trophy mapping (Lib = CC rep/prize).
3. Clubs of league-cup countries (ENG, SCO, ...) have no free slot 2 for the Intercontinental: pick another slot (4?) or skip.

## ROADMAP after session 13 (decided 2026-09-30 by Davide)
- SESSION 14 (NEW, requested by Davide 2026-09-30, BEFORE the language port): real Serie C1/C2 1996-97 data.
  Check that C1/C2 clubs are the real 1996-97 ones (tools/c1c2.py: 18+18 picked from the real standings; reality was C1 2x18 =
  36 clubs, C2 3x18 = 54, we keep single 18-team divisions), then REAL player names (1996-97 rosters, sources: it.wikipedia club
  season pages, almanacs) and skill values coherent with the level (below Serie B, C1 > C2; calibrate on existing Serie B / old
  non-league records). Update tools/c1c2.py (today random Italian names, skills copied from non-league templates).
- SESSION 15: port all work to the other language exes (ENGLISH/FRENCH/GERMAN.EXE, same CD). Known ITA-specific bits to generalize:
  STR_BASE 0x16F8, hardcoded pseudo-register offsets in sacups regexes (A0 315D7, A1 315DB, D0 315B7...), strpool source strings
  (Italian texts '.COPPA AFRICANA CLUB', 'COPPA SUDAMERICANA', 'COPPA EUFA', 'ERRORE DISCO'), cup/league display names per language,
  someLeaguesTable/slot/buffer addresses (all found by signature -> check each), notes/addrmap.json (ENG<->ITA deltas).
- SESSION 16: release a patch users apply to their own original copy, runnable on current Windows / Linux / macOS. DECIDED (Davide 2026-09-30): single-file HTML/JS patcher.
  Distribute only differences (no copyrighted game files). Idea: single self-contained HTML/JS patcher (runs in any browser,
  no install): user selects original ITALIAN.EXE (+ DATA/TEAM.020 ...), md5 check of inputs, applies binary diffs, downloads the
  patched files; alternative/extra: BPS/xdelta patches + plain Python script. Include README (ITA/ENG), credits, uninstall = keep originals.

## Session 13 — NON ESEGUITA (2026-09-30, run schedulato)
Avvio con finestra 5h Pro già al 91% (soglia stop 85%, extra usage disabilitato, reset ~01:00 UTC).
Nessuna modifica: build, tools e salvataggi intatti. Il piano "NEXT SESSION (13)" resta valido così com'è
(task A–E: backup ITALIAN_S12.EXE, finaliste Intercontinentale a fine stagione via CSEG_92D55 + INTLIST,
blocco salvato 'S2' con INTLIST e byte di bilanciamento a +102, salists.py per entrambi i formati).
Da rilanciare quando la finestra è libera.

## Session 13 — Intercontinental finalists at season end + persisted (untested, build md5 0dacb95cf1ff1a201940f0b93026c56c)
- Backup of the last playtested build: c/SWOS/ITALIAN_S12.EXE (md5 b399ba01557e5462c129a13d2b1bf267). Restore it over
  ITALIAN.EXE if the new build misbehaves (S12 cannot read 'S2' blocks: it falls back to the 1997 lists, no crash expected).
- sa_qualify tail (obj1+0xA16FA): `call CSEG_92D55` (obj1+0x82BA9, real CC end; both branches end in cseg_92F1C which always
  writes dseg_18070F = obj2+0xC058B), then INTLIST[0] = HOLDER, INTLIST[1] = LIBWIN (each skipped if 0FFFFh), `call lists_out`,
  `ret` (back to obj1+0x812C9). INTLIST = Intercontinental struct + 24 = obj1+0xA10DD (default 14 20 2B 21 = Juventus - River).
- Saved block (someLeaguesTable[1740..1842], obj2+0x1867E; mirror leaguesTableCopy obj2+0x59C08): marker 'S2' (0x3253) + 96 B
  lists + 4 B INTLIST + balance byte at +102 (sum of the 103 bytes = 0), mirror 103 B. lists_in (obj1+0xA14EA) now also reads the
  4 bytes after the lists into INTLIST (entry int_in obj1+0xA1506); lists_out (obj1+0xA1514) writes them, marker S2.
  load_slot1 (obj1+0xA135F): 'S2' -> all from save; 'SA' (session-12 saves) -> saved lists + DEFAULT pair (DEFAULTS+96 =
  obj1+0xA15F1); else DEFAULTS (100 B at obj1+0xA1591). init_sa (obj1+0xA121C): 'S2' or 'SA' = existing career, 0 = new.
- Static checks done: build asserts; ndisasm of sa_qualify tail, lists_in/out, init_sa, load_slot1 and all hooks (0x237C1 ->
  load_slot1, 0x237FD -> load_slot3, 0x7D307 -> init_sa, 0x7D312 -> euro_found, 0x812C4 -> sa_qualify); every absolute operand
  has a fixup to the right obj/offset; obj2 identical to S12, obj1 differs only in the cave page and the 3 hook rel32s; 9 more
  fixups, none outside the cave. salists.py decodes both formats (RIVSA.CAR = 'SA', sum 0, prints default pair). Checksum
  emulated on a copy of RIVSA.CAR converted to 'S2' (scratch only): block sum 0, whole 2000-byte table sum 0; 1843..1849 = 0.
- UNTESTED in game. Note: a season-12 'SA' career that reaches season end is rewritten as 'S2' (old balance byte position
  becomes INTLIST data, new balance at +102).

### Findings (read-only, not implemented): slot 4 for the Intercontinental of league-cup countries
- Slot table dseg_D8CAA: 0 league, 1 D8CAE national cup, 2 D8CB2 league cup, 3 D8CB6 euro cup, 4 D8CBA (+ D8CC0), buffer of
  slot 4 = dseg_D9C9F (ProcessCareerFile pointer list). ProcessCareerFile reloads D8CBA/D8CC0 on every load from the player's
  league record: byte [league + div*6 + 12h] = offset of a (contest ptr, D8CC0) pair; 0 = none -> slot 4 free for that division.
- cseg_8B2D3 with D0=4: accepts only type-1 contests ([A0+1]==1; Intercontinental IS type 1, OK), then fills dseg_10F0F6 with
  careerTeam x [A0+0Ah] (tour/friendly logic: every entry = the player's club). So an Intercontinental in slot 4 would need its
  team list rewritten AFTER cseg_8B2D3 (int_step already writes the slot buffer; same trick as slot 2), and load_slot1 would have
  to restore D8CBA (reset by ProcessCareerFile from the league record) when the slot-4 buffer id == INT_ID, like slot 2.
- Slot 2 is also used for friendlyCopy/tourCopy (cseg_37A50 compares D8CB2 with them): slot 2 is not only the league cup.
- Risk: divisions whose record has a tour (e.g. some English/Scottish divisions) would lose it or clash; displays (cseg_3760C
  menu) must be checked for slot 4 with a knockout contest. Estimate: ~1 session incl. playtest. Alternative: skip for those clubs.

### TEST LIST per Davide (sessione 13)
1. Carica una carriera nuova con Juventus o River: al primo dicembre l'Intercontinentale c'è ancora (Juventus - River, default).
2. Carica RIVSA.CAR (formato vecchio 'SA'): le liste SA sono quelle salvate, l'Intercontinentale resta Juventus - River.
3. Porta una carriera (River o Juventus) a FINE STAGIONE: nessun blocco dopo le classifiche (checksum). All'inizio della nuova
   stagione, vista mondo/Coppa Intercontinentale = vincitrice Coppa Campioni + vincitrice Libertadores della stagione appena
   finita. Se la tua squadra è una delle due, deve avere l'Intercontinentale in slot 2 a dicembre; se non lo è, non deve averla.
4. Salva (es. INT13.CAR), esci da DOSBox, riavvia, ricarica: finaliste ancora quelle nuove.
   Controllo: `python3 tools/salists.py c/SWOS/INT13.CAR` -> "format S2, block sum mod 256 = 0" + riga INTERCONTINENTALE.
5. Slot 4 (club di paesi con coppa di lega, es. Inghilterra): una squadra inglese finalista (vincitrice Coppa Campioni) deve
   avere a dicembre l'Intercontinentale E la coppa di lega; salva/ricarica prima di dicembre; a fine campionato nessun blocco.
6. Se qualcosa si rompe: `cp c/SWOS/ITALIAN_S12.EXE c/SWOS/ITALIAN.EXE` (build sessione 12).
Ancora da provare dalla sessione 12: holder -> scambio CONMEBOL; trofeo Libertadores = reputazione/premio Coppa Campioni.

### Session 13 (cont., Davide awake: "procedi col punto E") — Intercontinental in SLOT 4 (untested, md5 cb6c817fbaa54d5e0096fa7d1df3f0f1)
- Correction to the findings: slot 4 = the DIVISION PLAY-OFFS (not friendlies/tours). cseg_8DAC3 (end of InitializeNewSeason)
  builds them with placeholder teams (careerTeam x n, cseg_8B2D3 D0=4 skips scheduling); at the league's end cseg_8ECAE takes the
  real teams from the standings (D8CC0 table) and schedules (cseg_32E15, 8B71C, 27436, 8B8B8, 8B7EA), sets D6B62 = 1 (only
  "no sacking during play-offs") and slot4+3Dh..41h = league's DF533.. (= substitution rules 5/2/8, InitCareer).
- int4_step (obj1+0xA1506) replaces `call cseg_8DAC3` at obj1+0x7D31E (DONE, reached by both init paths): calls cseg_8DAC3; if
  D8CBA (obj2+0x18E04) == 0 (division without play-offs): clear slot4 id (+2Dh); if not already in slot 2 and the club is in
  INTLIST: park slot-2 buffer (league cup, obj2+0x199A6) in slot-4 buffer (obj2+0x19DE9 = slot2 + 0x443), build the Intercontinental
  as slot 2 (cseg_8B2D3 D0=2, full scheduling), swap the two 0x443-byte buffers, slot4+2Bh = 4, slot4+3Dh..41h = league subs
  (ITA obj2+0x1F67D = ENG DF533), restore D8CB2, D8CBA = INT.
- playoffs (obj1+0xA15E9) replaces cseg_8ECAE's `cmp dword [D8CBA],0; jz out` (obj1+0x7EB02, 13 B, fixup removed): also skips
  when D8CBA == INT (else at the league's end it would rebuild our finished cup from the play-off table).
- load_slot1: D8CBA == 0 and slot4 id == INT_ID -> D8CBA = INT (ProcessCareerFile reloads D8CBA from the league record).
- Static checks: build asserts (slot4 == slot2+0x443, cseg_8ECAE tail pattern, ret at jz target), ndisasm of all new code and
  hooks, fixups OK, obj2 identical to S12, only fixup change outside the cave = removed 0x7EB04.
- Limits: clubs in a division WITH play-offs still get no Intercontinental; the season record (SeasonInformations) gets no
  name for slot 4 (the game never writes one for play-offs). Unknown: cseg_8BF89 (called by cseg_8B2D3) might keep slot-specific
  state; menus/fixture lists never saw a knockout "cup" in slot 4 before December.
- EXTRA TESTS (slot 4): an English (or Scottish) club that won the Champions Cup / is a finalist: e.g. start a career with an
  English top-division club, win the CC (or edit nothing: play until the CC final), season end -> next season Intercontinental in
  December alongside the league cup (both must be playable); league cup unaffected; save/reload in between; at the league's end no
  freeze and no play-off rebuild. Also a Juventus/River career must still use slot 2 (unchanged).

## Session 14 — real Serie C1/C2 1996-97 squads (2026-09-30, TEAM.020 md5 4dccfc83c4e931233411d9edd1a06097, exe unchanged cb6c817f)
- Clubs checked against it.wikipedia Serie C1/C2 1996-1997 final standings: all 36 are real 1996-97 C1/C2 clubs (C1: 10 existing +
  Treviso, Brescello, Carpi, Saronno, Prato [girone A 1-4, 6], Nocerina, Casarano, Juve Stabia [girone B 5-7]; C2: Pisa, Taranto,
  Ternana existing + Lumezzane, Lecco, Livorno, Battipagliese, Turris [promoted], Benevento, Catanzaro, Triestina, Rimini, Frosinone,
  Sandona, Pro Patria, Catania, Pro Sesto, Cittadella).
- tools/c1c2_rosters.py: real squads + coaches of the 23 new clubs from it.wikipedia "<club> 1996-1997" pages (rosa); Triestina's
  2nd keeper Paolo Bianchet from unionetriestina.it (wiki lists him as defender). Known regulars first. Foreigners: Aubameyang,
  Nzamba (GAB, black face), Vollmar (GER), Donato (ARG). Names: uppercase ASCII, > 22 chars -> initial (M. DAL COMPARE).
- c1c2.real_team: template = a non-league club whose role mix (G/D/M/A classes of the 16 positions) fits the roster (random among
  best fits), real names by role in list order (borrow a neighbour role if short), then skills (v&7, flag bit 3 kept) and prices
  shifted by whole steps (1 skill step = 2 price units, clamp -3..+2) towards TARGET avg price from the standings: C1 new 17-19
  (result 16.7-19.0, existing C1 14.3-20.2), C2 new 12.5-15 (result 12.8-15.0; existing Pisa 17.2, Taranto 14.8, Ternana 14.4).
  Goalkeepers have no skills in SWOS (price only). Names already in TEAM.020 go last in their role (mid-season transfers);
  6 unavoidable repeats left (5 keepers: Vinti, Monguzzi, Ambrosio, Locatelli, Cornacchia; Palmieri = homonym). The original
  SWOS data already has 61 repeated names.
- The 13 existing clubs keep SWOS's original squads (untouched). Old career saves keep their cached team data: start a NEW career
  to see the new squads.
- TEST: new career (any club) -> world view / Serie C1 and C2 team lists: real names (e.g. CASARANO: FABRIZIO MICCOLI,
  LUMEZZANE: SIMONE INZAGHI, PRO SESTO: CRISTIAN BROCCHI, TRIESTINA: PIERRE AUBAMEYANG black face);
  (14b: Oddo, Liverani, Rocchi, Bazzani now included; existing clubs updated too, see below);
  simulate a C1 and a C2 season: new C2 clubs should be weaker than C1 ones, no crash in squad/transfer menus.

### Session 14b (same day, Davide: Oddo/Liverani/Rocchi/Bazzani in, existing clubs too) — TEAM.020 md5 ded1b97bd1cc24bbeed7994bfa483d5c
- Oddo (Prato), Liverani (Nocerina), Rocchi (Pro Patria), Bazzani (Sandona) moved first in their role -> in the 16.
- The 13 existing C1/C2 clubs (Acireale, Ancona, Ascoli, Avellino, Como, Fidelis Andria, Modena, Monza, Pistoiese, SPAL, Pisa,
  Taranto, Ternana) now also get their real 1996-97 squads + coaches (c1c2_rosters.EXISTING, it.wikipedia season pages; Ascoli
  ordered by appearances) through the same real_team path; their own kits kept; a role the source lacks is filled with the club's
  original SWOS player (Modena: FERRO TONTINI, SPAL: MASSIMO BATTARA as 2nd keeper). Strength targets from the standings
  (Fidelis Andria 19 ... SPAL 15.5; Ternana 15, Pisa 13.5, Taranto 12). Results within +-1: C1 avg ~17.8, C2 ~13.9.
  Monza's Oddo (loan) kept at Prato only. Repeated names: 5 (orig 61). E.g. COMO: GIANLUCA ZAMBROTTA, MONZA: CHRISTIAN ABBIATI,
  PISTOIESE: LEGROTTAGLIE, PIOLI, ZENONI x2.
- Reminder: 1996-97 reality was C1 2 gironi x 18, C2 3 gironi x 18; the mod keeps single 18-team C1/C2 (session 1 decision).

### Docs (2026-09-30)
- Technical manual for developers, Italian + English, kept in sync: docs/src/manual.it.html / manual.en.html (artifacts IT
  https://claude.ai/artifact/58v5iQpxMECsUzG2VHxkjN, EN https://claude.ai/artifact/2GdFS8VJho8AEDk3SryDxG).
  `python3 tools/mkdocs.py` -> docs/index.html (IT) + docs/en.html (EN) for GitHub Pages (asserts same structure in both).
  RULE: every session that changes the mod updates BOTH manuals, reruns mkdocs.py and republishes both artifacts.

### PLAYTEST 15 (user, 2026-09-30 evening) — sessions 13-14
- ALL PASSED: (1) boot + preset SA cups / Europe cups; (2) new career, real C1/C2 squads OK; (3) River/Juve season end: no freeze,
  INT13.CAR = format S2, sum 0, Intercontinental AC MILAN - GREMIO (CC winner - Libertadores winner), holder Gremio in Lib (BRA2)
  and Supercopa, no club in both Lib and CONMEBOL; reload after full DOSBox restart keeps it; (4) other Italian club season end OK;
  (5) RIVSA.CAR (old 'SA') loads.
- NOT YET: Intercontinental in slot 4 (English CC winner) -> experimental in 1.0; trophy mapping (Lib = CC reputation/prize).
- Seen: English clubs show 14 players in the pre-match line-up. Same with the ORIGINAL exe + TEAM.020 (checked by Davide, orig
  files swapped in and back): original game behaviour, TEAM.008 has 16 players per club. Mod build restored (ITALIAN_S14.EXE /
  TEAM020_S14.BIN = copies of the release candidate cb6c817f / ded1b97b).

## Session 15 — port to ENGLISH / FRENCH / GERMAN (2026-09-30 evening, static checks only)
- `python3 tools/patch.py [it|en|fr|de]` (LANGS in patch.py). ITA output unchanged (cb6c817f). Generalized: pseudo registers from
  signatures (sacups.regs: InitializeNewSeason tail + ProcessCareerFile slot-3 test; D0..D7, A0..A6 consecutive dwords),
  STR_BASE from the Italy league struct (patch_italy -> sacups.STR_BASE, 0x16F8 in all 4), obj1 cave = align16(vsize).
- String pool per language (strpool.SOURCES): EN '.AFRICAN CLUBS CUP', 'SOUTH AMERICAN CUP', padding of 2nd 'EUFA CUP',
  'DISK ERROR', 'EURO CW CUP'; DE '.AFRIKAVEREINSPOKAL', 'SUEDAMERIKAMEISTERSCHAFT', 2nd 'EUFA-CUP', INT name = the game's own
  'WELTPOKAL' (pool.reuse); FR has no '*' padding: 'COUPE D'AFRIQUE DES CLUBS', 'COUPE SUD-AMERICAINE' + 4 freed duplicates
  (2nd name dword of COPA AMERICA / COUPE D'ASIE / COUPE D'OCEANIE / COUPE EUFA contests retargeted to the 1st copy, strpool.DUPLICATES).
  INT names: EN 'INTERCONTINENTAL CUP', FR 'COUPE INTERCONTINENTALE', DE 'WELTPOKAL'.
- Checks per language: all signature addresses == ENGLISH disassembly labels (EN); same 7 hook sites -> same labels
  (0xA135F, 0xA13FC, 0xA121C, 0xA1457, 0xA1506, 0xA15E9, 0xA1716) in all 4; cave code identical except address operands;
  12 fixups changed outside the cave in every language; obj2 diffs = names, Italian club remap, Italy base (+ FR 4 name dwords).
- md5: ENGLISH d094c39d, FRENCH 1b7e87d9, GERMAN 69071a3d. Originals saved in orig/ (FRENCH/GERMAN copied from c/SWOS).
  DOSBox configs: dosbox-swos-en.conf / -fr / -de. tools/salists.py finds the saved block in any language (same save offset).
- PLAYTEST EN (user): Juventus career to season end: ENTEST.CAR format S2, sum 0, Intercontinental MANCHESTER UTD - CRUZEIRO.
  Reload of ENTEST after a full DOSBox restart: Intercontinental still MANCHESTER UTD - CRUZEIRO (PASSED).

- PLAYTEST FR + DE (user): all OK (menus/names incl. the 4 French freed duplicates, career to season end).

## Session 16 — release patcher 1.0 (2026-09-30 evening)
- tools/mkpatcher.py -> release/swos-9697-mod-patcher.html (73 KB, self-contained, offline, IT/EN UI). Delta format SWD1:
  COPY(offset,len) from the user's original (>= 16-byte matches) / INSERT(new bytes); per exe ~6.1 KB (5.7 KB inserted), TEAM.020
  18 KB. md5 checked on input (original) and output (patched); unknown or already patched files refused.
- Verified in Node with the page's own JS: md5 == node crypto, all 5 originals recognised, outputs = cb6c817f / d094c39d /
  1b7e87d9 / 69071a3d / ded1b97b; a patched exe is not accepted as original. Template: tools/patcher_template.html.
- Credits: Davide Lorigliola (with Claude); swos-port for disassembly/docs.
- TODO before publishing: EN manual with ENGLISH.EXE addresses (Davide: IT manual for ITALIAN.EXE, EN manual for ENGLISH.EXE);
  GitHub repo (sources + docs + release, no game files) and GitHub Pages on docs/.

- PUBLISHED (Davide's ok, 2026-09-30 night): repo https://github.com/aminta/swos-9697-mod (public; no game files: orig/, c/,
  ref/, saves, DOSBox confs ignored), GitHub Pages https://aminta.github.io/swos-9697-mod/ (docs/), release v1.0 with
  swos-9697-mod-patcher.html. Foreword by Davide (docs/src/foreword.it.md + English translation foreword.en.md) at the top of
  README, release notes, both manuals and the patcher.
- EN manual now uses ENGLISH.EXE addresses (offset = disassembly VA - base; 145 ITA->ENG pairs from the cave fixups confirmed it).
  README and release notes: English first, then Italian. GitHub Pages: index.html = EN manual, it.html = IT, en.html = redirect.

- ANNOUNCED (Davide's ok): SWOS United forum, section PC, topic
  https://sensiblesoccer.de/forum/pc/27756-swos-96-97-mod-1-0-serie-c1-c2-libertadores-intercontinental-cup
  (posted from Davide's account in the built-in browser, subscribed to replies; text in release/forum-announcement.bbcode).

- Thank-you issue to Zlatko: https://github.com/zlatkok/swos-port/issues/4 . Announcement texts in release/announcements/
  (SwosIt Facebook IT, SWOS United Discord/Facebook EN, GOG/VOGONS/Reddit EN): Davide posts them (not logged in / blocked in the
  built-in browser). GOG sells SWOS 96/97: its exes may differ from the CD (no-CD patch?) -> patcher would refuse them.

## 1.0.1 — GOG version support (2026-09-30 night)
- GOG installer (gog_sensible_world_of_soccer_96_97_2.0.0.1.sh, a zip after a shell stub) holds the same files as the CD:
  TEAM.020 identical, each exe differs by 2 bytes (contest 0x8F, country 15 = Hungary, months 00 20 -> 40 28: GOG's date fix).
  Originals in orig/gog/ (git-ignored). Mod built on them = CD mod except those 2 bytes. md5 GOG mod: ITA 40344702,
  ENG 85f16703, FRA add5e74a, GER 1387feeb. mkpatcher.FILES has the 4 GOG entries (VERSION 1.0.1); Node test: 9/9 files OK.

- Announced 1.0.1: Facebook group "Sensible World of Soccer" (official SWOS United group, facebook.com/groups/125891707442035,
  post by Davide Lorigliola, text release/announcements/5-facebook-group-swos-united-en.txt; link preview shows the forum's
  "429 Too Many Requests" -> preview removed by editing the post); forum reply on GOG support (topic 27756, post #147326).
- SWOS United Discord (discord.gg/jFsBSSw): posted by Davide (text 2-swos-united-discord-en.txt). VOGONS: 403 for the extension/built-in
  browser, Reddit blocked -> manual. VOGONS: posted by Davide (Release Announcements, text 3b-vogons-en.bbcode). Reddit: posted by Davide on r/retrogaming and
  r/dosgaming, both removed by Reddit's filters -> modmail sent to both asking approval (2026-10-01).
- Personal email to Zlatko (zlatko.karakas@gmail.com, public on his GitHub) sent by Davide (text 6-zlatko-email-en.txt).
- Ali Erdinc Koroglu (Swos Working Group admin, swos.erdinc.info): Davide found a likely LinkedIn profile and sent a connection
  request with a note (7-ali-linkedin-note-en.txt); full message ready for after he accepts (8-ali-linkedin-message-en.txt).

## BACKLOG after 1.0 (Davide 2026-09-30)
- (done in 1.0.1) GOG version support.
- English line-up shows only 14 players (11 + 3 bench) also in the original game: find where the bench size comes from
  (per-country/league rule; slot +3Dh..41h substitution words, DF533 5/2/8 set in InitCareer) and offer 16 (5 on the bench).
- Intercontinental in slot 4 playtest (English CC winner); C1 with two groups (analysis first).

## NEXT SESSION (15)
- Playtest results of sessions 13-14 first (fix if needed). Then the language port (roadmap SESSION 15).

## ROADMAP 2 — more continents (decided 2026-10-01 with Davide; not started)
Original 96/97 data (ENGLISH.EXE competitionsTable obj2+0x8B1C + TEAM files):
- Continental CLUB cups exist only for Europe (CC, CWC, UEFA). Africa/N.America/Asia/Oceania tables = WCQ + nations cup only.
  Unused string '.AFRICAN CLUBS CUP' = the developers' abandoned African club cup (we reused its space for SA names).
- Club leagues outside Europe/SA: Algeria 16, South Africa 16, Ghana 8 (Africa); Japan 28 (+2 cups), Taiwan 12, India 6 (Asia);
  Mexico 40, USA 18, El Salvador 46 (N/C America); Australia 51, New Zealand 30 (Oceania). Team files WITHOUT a league:
  Costa Rica (TEAM.047, 12 clubs), South Korea (1), Malaysia (1), Tanzania (1).
- Real 1996-97 club competitions missing: CAF Champions' Cup (-> CAF Champions League 1997, groups), African Cup Winners' Cup,
  CAF Cup; Asian Club Championship, Asian Cup Winners' Cup; CONCACAF Champions' Cup; UEFA Intertoto, UEFA Super Cup.
  Oceania: no club cup in 1996-97 (1987, then 1999) -> nothing to add. Strong African/Asian clubs are in countries SWOS lacks
  (Egypt, Morocco, Tunisia, Nigeria, Cameroon; South Korea, China, Saudi Arabia, Iran, UAE).
Constraints found:
- Global team numbers < 2000: ~300 free (runs 238-301 64, 483-513 31, 884-934 51, 995-1043 49, 1171-1204 34, 1924-1999 76;
  1730-1849 hosts our saved SA block). Enough for ~15 new 16-team leagues. someLeaguesTable (2000 B) is ALSO our only known
  persistence space: the 'S2' block leaves ~17 free bytes in 1730..1849 -> new cup lists (32 B each) need another place
  (other free global numbers compete with new leagues; or find free bytes elsewhere in the .CAR).
- String pool full. obj2 vsize 0xC5FC0 vs physical 0xC5000 (only ~4 KB BSS at the end) -> adding data pages after it
  (zero page + new page, like obj1's add_object_page) should give room for names without touching game variables.
- Real 1996-97 squads for African/Asian clubs: sources much poorer than for Serie C (expect partly reconstructed squads).
- Tool to consider: LubosKolouch/swos-editor (TEAM.* / .CAR editor).
Feasibility: (a) new continental club cups among EXISTING countries (CONCACAF, Africa, Asia) = high, same machinery as the
SA cups; (b) Costa Rica league = high (clubs exist); (c) NEW countries (Egypt, Morocco, Korea...) = plausible but unknowns:
per-country tables sized to 86 entries (names, flags, nationality maps, world-view lists), team-file numbering, strings.
Plan: S1 analysis (obj2 data page, how a country is registered, persistence budget) -> go/no-go for new countries;
Africa (new leagues + CAF cups) -> CONCACAF (Costa Rica + Champions' Cup) -> Asia -> Europe (Intertoto, Super Cup, CL 97-98).


## Session 17 — analysis for Roadmap 2 (2026-10-01 night, analysis only, release builds untouched)
(First scheduled run aborted at 98% of the 5-hour window; redone interactively after the reset. All addresses = ENGLISH.EXE.)

### A. obj2 data space — FEASIBLE (static proof + boot)
- ENG obj2: base 0xC0000, vsize 0xC5FC0, 197 physical pages (0xC5000), last page only 0x62F bytes in orig -> initialized data ends
  0xC462F, BSS/stack 0xC462F..0xC5FC0. Entry ESP = obj2:0xC5FC0 (stack top = end of vsize, grows down).
- lepatch.add_object_page(data, 2) works for obj2 unchanged: pads the file's last page, appends the new physical page, maps it as obj2's
  next logical page. Because 0xC5000..0xC5FC0 is BSS/stack, ONE page is not enough: add TWO pages (0xC5000 = zero page covering the
  old BSS/stack, 0xC6000 = free) and set_vsize(2, 0xC7000). Stack stays at 0xC5FC0, so the new page is above it and never touched.
- Experiment (scratch only): rebuilt ENGLISH.EXE from orig with patch.py functions -> md5 d094c39d (= release, build reproducible), then
  2x add_object_page(.., 2), vsize 0xC7000, wrote 'TEST NEW PAGE CUP' at obj2+0xC6000 and pointed the Intercontinental contest name
  (two STR_BASE-relative dwords in the obj1 cave at obj1+0xA10D5) at it (rel = 0xC6000 - 0x16F8).
  Re-parsed with le.py: obj2 bytes 0..0xC5000 byte-identical, padding zero, obj1 differs only in those 2 dwords, 73696 fixups identical.
  DOSBox-X boot of the scratch exe: DOS/4GW loaded it and the game switched to 640x480 graphics (no loader error).
  NOT verified: the name on screen (needs a look at the Intercontinental menu).
- Steps for the real build: in patch_exe after add_object_page(.., 1): add_object_page twice for obj2, set_vsize(2, align_up(vsize,0x1000)
  + 0x1000) per language (compute, do not hardcode 0xC7000), then StrPool can get a second area at obj2+0xC6000 (4 KB; add more pages
  if needed). Strings there are reachable both by STR_BASE-relative dwords (league/contest names) and by fixup pointers (add_ptr).
- Risks: (1) fixups whose SOURCE lies in a new obj2 page (e.g. a relocated pointer table placed there) are untested; the same path
  already works for the added obj1 page, so low risk; or keep pointer tables in the obj1 cave and only strings in obj2.
  (2) DOS/4GW object size limits: none hit (obj2 +8 KB, total < 2 MB). (3) release md5s change -> patcher regenerated (as usual).

### B. How a country is registered (team file number = country number, 0..255)
- LoadTeamFile (asm line ~39055): any number 0..255 -> 'data/team.nnn' (100 = CUSTOMS.EDT); file must be <= 64000 B (93 teams),
  else FatalError. So TEAM.052, TEAM.086.. etc. load fine once something references them.
- Tables indexed by country number (all ENG obj2):
  | table | addr | entry | entries | notes |
  | countriesTable | obj2+0x6742 | dword ptr (fixup) -> [continent byte, NAME\0, ADJECTIVE\0] | 256 (+6 continent adjectives) | holes: 47 (Costa Rica!), 52-54, 56-59, 61, 63, 68, 70, 74, 86-99, 101-251. Continent byte: 0 EUR, 1 N.AM, 2 S.AM, 3 ASIA, 4 OCE, 5 AFR. 13 code xrefs |
  | competitionsTable | obj2+0x8B1C | dword ptr -> country table [league/cup ptrs, -2, -1] | 256 | null for the same holes |
  | teamsCountryNumbers | obj2+0xB2A38 | word global base | 256 | 1 xref (SetTeamGlobalNumbers); global = base[team byte0] + team byte1; entries 86..255 all = 1730 (!) |
  | continent tables 81..85 | Africa obj2+0x8FC8, S.Am 0x8FD8, N.Am 0x8FF0, Asia 0x9000, Oce 0x9010 | [WCQ ptr, nations cup ptr, -1 x4] + country bytes + FF | AFR [42,79,69], N.AM [51,60,73], ASIA [75,55,67], OCE [44,62] | world view / preset menus; must be relocated to add a country (as sacups did for SA) |
  | seasonEndList | obj2+0x943A | byte, FF-terminated | 65 | 1 xref obj1+0x814AD (cseg_91428): at season end every listed country gets cseg_9153F + cseg_93974 (league processing + cup qualifiers). A new league country MUST be added -> relocate list + retarget that fixup |
  | all_countries_list | obj2+0x93F8 | byte | 66 | no fixup xref to its start (maybe +1 or unused); same set as seasonEndList |
  | shortCountryNames | obj2+0x6B98 | 3 chars | 153 | PLAYER nationalities, separate numbering: already has ALG 80, SAF 81, GHA 88, TUN 91, CMR 94, EGY 105, NIG 107, JAP 118, KOR 127, IRN 128, SAU 131, CHI 139, UAE 147, MAR 115, CRC 51, MEX 56, USA 58, ELS 66 -> no new nationality needed |
- No per-country flag graphics found (country menus are text). Code tests country >= 80 only as ranges 80..85 = national teams
  (5 of 28 sites read); 100 = customs. Safest numbers for new countries: the unused gaps 52, 53, 54, 56, 58, 61, 63 (7 slots); 86..99
  probably fine too (not fully verified). Avoid 57/59/70 (single-team files SOUTH KOREA / MALAYSIA / TANZANIA exist) and 68 (60 teams).
- New country X needs: TEAM.0nn (clubs, league byte 0..), countriesTable[n] record (continent byte + name + adjective, strings in the new
  obj2 page, add_ptr), teamsCountryNumbers[n] = free global base (plain word), competitionsTable[n] -> new country table + league
  struct (obj1 cave, like Italy), add n to the continent table and to seasonEndList (both relocated), league name string.
- Costa Rica (47): TEAM.047 has 12 clubs (league byte 0), global base 1073 already reserved (1073..1084). Missing: countriesTable[47]
  (name 'COSTA RICA'/'COSTA RICAN', continent 1), competitionsTable[47] + league struct (12 teams, 1 division), 47 in the North America
  table and in seasonEndList. That is all — no global-number work.

### C. Persistence budget
- .CAR = obj2 dump from careerFileBuffer (ENG VA 0xC958C) to g_numSelectedTeams (save offset 0x173AF = 95151 B fixed part), then
  N team records (684 B). 9 saves: N = 25..60. g_selectedTeams has room for 100 teams (68400 B) and is followed directly by the
  pseudo registers D0..D7.
- REAL free global numbers (computed from all TEAM files + mod Italy base 1850): only 424-474 (51, Italy's old range), 1730-1849 (120,
  S2 block uses 1740-1842 -> 1730-1739 and 1843-1849 free = 17), 1924-1999 (76). Total 144. The older estimate (~300, runs 238-301 etc.)
  was WRONG: those runs are taken by team files. Global numbers >= 2000 are not usable (someLeaguesTable[2000] is followed by currentTeam).
  => global numbers are needed both for new countries' clubs and for persistence: 144 = e.g. 5 African leagues x 16 (80) + 64 left.
- Bytes zero in all 9 saves (fixed part): tail of careerForeignMarketPlayers (352 x 42 B, 11822 B zero) and of dseg_D761E (season history,
  1060 words, 1872 B zero) — NOT usable: the market loops always run over all 352 entries; the history fills up season by season.
- Recommended: a save TRAILER. Hook SaveCareerFile (length = fixed + 2 + N*684, add T bytes copied from a block in the new obj2 page)
  and LoadCareerFile (after LoadFile: if file size > 95151+2+N*684 and marker ok, copy the trailer back; else defaults). Old saves still
  load (no trailer -> defaults). Guard: write the trailer only if N*684 + T <= 68400 (T <= 684 B keeps N <= 99; observed max N 60),
  otherwise LoadFile would overwrite D0..D7. Fallback: keep using free global numbers (balance byte rule of cseg_9487A).

### D. Go / no-go
1. New continental club cups among EXISTING countries: GO. Same machinery as the SA cups (sacups.py). Few teams per continent though
   (Africa 3 countries / 40 clubs, N.Am 3 (+CR) / 104, Asia 3 / 46), so a real CAF/AFC field needs new countries. Persistence via trailer.
2. Costa Rica league: GO, smallest item (~1 session incl. relocating the N.America and seasonEnd lists + strings in the new page).
3. Brand-new countries (Egypt, Morocco, Tunisia, Nigeria, Cameroon, South Korea...): GO with limits: 7 safe country numbers (52,53,54,
   56,58,61,63; more in 86..99 after checking), ~127 free global numbers outside the S2 range (=> about 5-7 leagues of 16-18, or more
   with 12-14 team leagues), strings in the new obj2 page. Main cost = data (rosters, sources poor).
Effort (sessions): infrastructure (obj2 pages in patch.py for 4 languages, generic add_country/add_league/relocate lists, save trailer)
1.5-2; Costa Rica 1; Africa: 5 new countries' data 2-3 + registration 1 + CAF Champions League 97 (groups) / Cup Winners' Cup / CAF Cup
2-3 => 6-8; CONCACAF Champions' Cup 1-2; Asia (new countries + 2 cups) 4-5; Europe extras (Intertoto, Super Cup, CL 97-98) separate.
Recommended order (Davide wants Africa first): S18 infrastructure + Costa Rica as the pilot of "register a country/league"
(proves countriesTable/competitionsTable/continent/seasonEnd relocation in game) -> S19 save trailer + first African country (Egypt) end to
end -> S20-21 Morocco, Tunisia, Nigeria, Cameroon data -> S22-23 CAF cups -> CONCACAF -> Asia.
NOT verified this session: menu display of a name stored in the new page; the 23 unread country>=80 tests; whether all_countries_list is
used; what the single-team files 057/059/070 and TEAM.068 are used for; the max N of cached teams in a career; game behaviour with a 12-team
league (12 exists already: Taiwan).

## Session 18 — infrastructure + Costa Rica pilot (2026-10-01, static checks only, UNTESTED in game)
- obj2 grows in patch.py: pages added with lepatch.add_object_page(.., 2) until (npages-1)*4096 >= old vsize (EN/IT +2 pages,
  FR/DE +3: their obj2 has 196 physical pages and vsize 0xC5950/0xC5750), vsize = 0xC7000 in all 4. Free area obj2+0xC6000..0xC7000
  (above the stack top ESP = old vsize). le.LE now also accepts bytes.
- tools/countries.py: COUNTRIES config (number -> continent, name/adjective per language, league), Obj2Area allocator (strings and
  country records in the new obj2 page), tables() finds countriesTable / teamsCountryNumbers / seasonEndList by content in every
  language, patch(): country record + countriesTable ptr, league struct + country table [league, -2, -1] in the obj1 cave +
  competitionsTable ptr, continent table rebuilt in the cave with the new country (retarget competitionsTable[80+k]), seasonEndList
  copied to the cave + new league countries (retarget the single obj1 reference, ENG obj1+0x814AD). Contest ids from 0x70 (free 0x70..0x7B).
- Costa Rica (47): record [1,'COSTA RICA','COSTA RICAN' (EN; other languages adjective = name)], league id 0x70, 1 division of 12,
  2 games per pair (22 rounds), 3 points, season bytes 0x38/0x20 (as El Salvador/Mexico), names 'PRIMERA DIVISION'/'PRIMERA' (existing
  Spanish strings reused). TEAM.047 unchanged (12 clubs, league byte 0, global base 1073).
- Diff vs 1.0.1 (all 4 languages): obj2 only countriesTable[47] + competitionsTable[47] dwords; obj1 only 104 new cave bytes
  (0xA1932..0xA19B2); fixups +5 added, 2 retargeted (competitionsTable[83], seasonEndList ref), none removed. obj1 cave now ends 0xA19B4
  of 0xA2000 (~1.6 KB left: Africa will need another obj1 page).
- Builds in c/SWOS: ITALIAN 089bbb06, ENGLISH ee8fb457, FRENCH d7060663, GERMAN 015e36cd, TEAM.020 ded1b97b (unchanged).
  1.0.1 release builds backed up in c/REL101/ (cb6c817f, d094c39d, 1b7e87d9, 69071a3d, ded1b97b).
- PLAYTEST needed (Davide): (1) Select teams / world view -> North America shows COSTA RICA with 12 clubs and PRIMERA DIVISION;
  (2) new career with a Costa Rican club, play/simulate to season end + save/reload; (3) a career with another club (e.g. Italian)
  to season end: no freeze with the longer season-end list; (4) one non-Italian language quick check of the name.
- Pending after the playtest: manuals IT+EN (docs/src, mkdocs.py, 2 artifacts), patcher 1.1 (mkpatcher), then session 19 (save trailer
  + Egypt).

## Session 19a — five new African countries (2026-10-01, static checks only, UNTESTED in game)
- tools/africa.py: Egypt (TEAM.052, 16 clubs, 1996-97), Morocco (053, 16, 1996-97), Tunisia (054, 14, 1996-97), Nigeria (056, 18, 1997),
  Cameroon (058, 18, 1997). Clubs + final order from RSSSF allfirst9697 / allfirst97 / kam97 and Wikipedia (fetched 2026-10-01).
  Squads and coaches GENERATED from common local names (real 1996-97 rosters not available) on positions/faces/skills of template
  clubs (Algeria TEAM.042 for EGY/MAR/TUN, white faces; Ghana TEAM.079 for NGA/CMR, black faces), skill step from a target price
  falling linearly with the final position (EGY 17->10, MAR 16->10, TUN 16->9.5, NGA 14->9, CMR 13.5->8.5; step capped +-3, so the top
  clubs reach ~15). Nationalities EGY 105, MAR 115, TUN 91, NIG 107, CMR 94. Kits approximate. Deterministic (seeded) -> same files
  for every language: TEAM.052 3b0307de, 053 a012d036, 054 e3dee409, 056 a4dc1905, 058 81df476a.
- Global bases (teamsCountryNumbers, plain words): 424 / 440 / 456 / 1924 / 1942. patch.write_new_teams checks every new global
  number against all original team files (game formula base[byte0] + byte1, NOT the stored word, which is stale), Italy 1850..1923 and
  the S2 block 1740..1842. Still free: 470-474, 1960-1999, 1730-1739, 1843-1849.
- countries.py: 'base' support; Africa continent table rebuilt in the cave: [42, 79, 69, 52, 53, 54, 56, 58]; season-end list 71
  countries; league ids 0x71..0x75 (unnamed single divisions like Algeria; season bytes 0x40/0x28 North Africa, 0x38/0x28 NGA/CMR).
  German names without umlauts (AGYPTEN), as the game does (OSTERREICH).
- Builds in c/SWOS: ITALIAN f7db32d2, ENGLISH 6929efc6, FRENCH 2d9e6a1f, GERMAN 04722bee, TEAM.020 ded1b97b + the 5 new TEAM files.
  The patcher must ship the new TEAM files whole (they contain only our data) -> mkpatcher change pending.
- PLAYTEST (added to session 18 list): Africa menu shows 8 countries; each new league (names, 14/16/18 clubs, kits); a career with
  an Egyptian club to season end + save/reload; season end of any career with 71 countries in the list.

## Session 19b — African national cups + CAF cups step 1 (2026-10-01, static checks only, UNTESTED in game)
- National cups for the 5 new countries (africa.NATIONAL_CUPS, countries.py 'cup'): clones of the Algerian cup struct (18 B:
  [id, 1, country, 0x60, 0x80, 0 x5, teams, 1, 0x35, 2, rounds]), country table [league, -2, cup, -1]. Ids 0xB2..0xB6 (after the
  last original cup 0xB1; no id range checks found in the code: ids are identifiers + Randomize seed). EGY/MAR/NGA/CMR 16 teams
  (rounds 54 54 94 14 as Algeria), TUN 8 (54 54 14, like Taiwan's 8-team cup with 12 clubs). Original Africa: Algeria and South
  Africa have a cup, Ghana none.
- tools/cafcups.py (step 1): CAF CHAMPIONS LEAGUE (0x76, Champions Cup clone: 16 teams, 4 groups of 4 + knockout), CAF CUP WINNERS
  CUP (0x77) and CAF CUP (0x78) (16-team knockouts, sacups.knockout16). Names in the new obj2 page. Initial lists: top 2 / 3-4 / 5-6
  of the 1996-97 tables (new countries), strongest clubs + real champions where present for ALG/SAF/GHA. Added to the Africa
  continent table (cup buttons) and to the international contests list (membership test only, no size limit; sacups now exports
  INTL_LIST; the list is relocated again, old copy left unused in the cave).
- BUG FIXED in countries.py: the continent table's -1 + country bytes were written at +8 regardless of the pointer count.
- Builds in c/SWOS: see md5 below. obj1 cave ends ~0xA1D00 of 0xA2000 (step 2 needs another obj1 page).
- NEXT (step 2): career (slot-3 chain D7 = 6/7/8 + ProcessCareerFile mapping + trophy flag), season-end qualifiers from the
  standings of the 8 African countries (sacups.qualify_hook generalised), persistence of the 3 lists (96 B) -> .CAR trailer
  (session 17 C). Then manuals + patcher 1.1 (ship TEAM.052..058 whole).
- md5 19b: IT EN FR DE = 1415fc77 45ade57e 1189010f 618c08fc 

## Session 19c — CAF cups step 2: career + season-end qualifiers (2026-10-01, static checks only, UNTESTED in game)
- obj1 grows by a SECOND page (OBJ1_NEW_VSIZE 0xA3000): 0xA1000 = SA cave (sacups), 0xA2000 = WORLD_CAVE (cafcups structs,
  countries, CAF intl list). Build order: patch_italy -> cafcups.structs -> countries.patch (needs the CAF ptrs for the Africa
  table; finds competitionsTable itself, countries.COMP) -> sacups.patch(.., cafcups.career_info) -> cafcups.intl_list.
- Career (sacups CAREER_ASM): slot-3 chain after CONMEBOL tries CAF CL / CWC / CAF Cup with D7 = 6 / 7 / 8; CUP_KIND = D7-3 or D7-6
  (Champions Cup / CWC / UEFA rank); load_slot3 maps E092F 6..8 back to the CAF struct.
- Season end (sacups.qualify_hook): QTABLE now has 18 countries; African entries: CAF CL ranks 1-2, CWC ranks 3-4 (no readable cup
  winners -> league ranks), CAF Cup ranks 5-6, list positions as the 1997 lists (cafcups.CL_Q/CWC_Q/CUP_Q). qualify_hook follows
  country tables into obj1 (new countries).
- NOT persisted: after loading a save the CAF lists are the 1997 ones until the next season end recomputes them (world view only;
  the player's own CAF cup is in its slot buffer, saved by the game). Persistence -> .CAR trailer (next).
- md5 19c: IT EN FR DE = 7974c499 3320e8c3 555b8ecc eb001b72 
- PLAYTEST: career with an African top club (e.g. AL AHLY, RAJA) -> CAF Champions League in slot 3 in season 1, save/reload keeps it;
  season end -> next season's CAF lists = standings (world view / the player's qualification).

## PLAYTEST sessions 18-19 (Davide, 2026-10-01): ALL PASSED
- After fix 230e17e (league byte 5 = names offset 9 + 6*divisions; 0x15 broke the 1-division Costa Rica league -> freeze in
  preset competitions). Builds 5ff732c5 / e4ad379a / 002aab76 / cc6a9075.
- TODO (Davide's question, not urgent): long careers were only tested 2-3 seasons (SA cups) / 1 season (Roadmap 2). No known
  accumulating state (lists rewritten each season with fixed sizes, balance byte recomputed, single-division new leagues, global numbers
  static), but test: results-only careers of 6-8 seasons (Italian club; African club, ideally moving country by job offer), saving
  each season under a new name; check the saved block with salists.py. Known cosmetic: a CAF/SA cup win counts as the euro trophy
  of the same rank.

## Session 20 — .CAR trailer: CAF lists saved with the career (2026-10-01, UNTESTED in game)
- tools/trailer.py: save_trailer replaces `call WriteFile` in SaveCareerFile (ENG obj1+0x23245): if N*684 + 98 <= 68400 it writes
  'C1' + the 3 CAF lists (96 B) after the team records and adds 98 to D1 (length). load_trailer replaces `call ProcessCareerFile`
  in LoadCareerFile (ENG obj1+0x231AC): file size (D1 from LoadFile) >= 95153 + N*684 + 98 and mark 'C1' -> lists from the file,
  else the first-season defaults. new_career_defaults is called by sacups init_sa when a new career starts (no S2 mark).
  careerFileBuffer ENG obj2+0x958C, g_numSelectedTeams obj2+0x2093B (save offset 95151). The same load/save code pattern is used
  twice for competition files (buffer obj2+0x1F4F6): the career one is the buffer used once.
- Code @ WORLD_CAVE obj1+0xA2288, 16 fixups. Builds: IT 4156ff39, EN 2b1753cb, FR 369d5004, DE a8e363c0.
- TEST: load EGY.CAR (no trailer, 106097 B) -> OK as before; save under a new name -> 106195 B (+98, ends with 'C1' + lists);
  reload it; a new career after loading a save -> CAF lists = 1997 ones.
- PLAYTEST session 20 (Davide): EGY.CAR (no trailer) loaded, played on, saved as EGY2.CAR = 106195 B (+98), trailer 'C1' + 3 lists,
  reload OK. The saved lists are the season-end ones from the standings (CAF CL starts with EL MANSOURA = Egyptian champion of the
  simulated season, WYDAD, JASPER UNITED...): CAF qualifiers from standings also confirmed. PASSED.

## Release 1.1 (2026-10-01, Davide's ok)
- Patcher 1.1 (mkpatcher VERSION 1.1): 14 outputs; new TEAM.052..058 shipped whole (Davide's call), produced together with TEAM.020
  (entries with 'with': 'TEAM.020', delta from an empty source); GOG exes rebuilt (c/gog: IT da2e0c46, EN 9d329d03, FR aaeeae22,
  DE 33866252; 2 bytes from the CD builds). Node test of the page's own JS: 14/14 outputs OK.
- Manuals IT+EN: new chapter 19 (New countries and African cups), overview rows, limits, history 15-20, roadmap; mkdocs OK.
- README + release notes: new countries, CAF cups, invented players explained + invitation to send real squads.
- Announced 1.1 (Davide, 2026-10-01): forum reply text + short Facebook/Discord version prepared in session (posted by Davide).

## Session 21 — CONCACAF Champions' Cup (2026-10-01, static checks only, UNTESTED in game)
- cafcups.py generalised: CUPS = [(id, list, groups?, ranks at season end, continent, euro rank)]; CAF CL 0x76 / CWC 0x77 / CAF Cup
  0x78 + CONCACAF CHAMPIONS CUP 0x79 (16-team knockout; first season: Necaxa, Cruz Azul, Guadalajara, America / DC United, LA Galaxy,
  Tampa Bay, Kansas City / Alianza, Firpo, FAS, Aguila / Saprissa, Alajuela, Herediano, Puntarenas; season end: ranks 1-4 of MEX,
  USA, SLV, CRC top divisions). Button in the North America table (cafcups.continents).
- sacups CAREER_ASM: the extra-cup slot-3 chain and the load mapping are generated (D7/E092F = 6 + index); trophy/prize rank from a
  KINDS table (0,1,2 for Lib/Sup/CON, then cafcups kinds: CAF 0,1,2, CONCACAF 0).
- trailer.py: mark 'C2' + 4 lists (130 B); 'C1' saves of 1.1: their 3 CAF lists are read, CONCACAF starts from the defaults.
- QTABLE 22 countries. Builds IT EN FR DE = c48c7706 fa8de5b9 f4f9fbab 90af0fc8 
- PLAYTEST: North America menu -> CONCACAF CHAMPIONS CUP; career with Necaxa/DC United/Saprissa -> cup in slot 3; save (file +130 B,
  'C2') + reload; load a 1.1 'C1' save (EGY2.CAR) -> OK; season end -> CONCACAF list from the standings.
- PLAYTEST session 21 (Davide): all OK. NEXACA.CAR (Mexican club, 20 cached teams) = 108963 B with 'C2' trailer (130 B), 4 lists
  recomputed at season end (CONCACAF: UNAM, Kansas City, Atletico Marte, Puriscal...). PASSED.

## Session 22 — all saved lists in the .CAR trailer, global numbers 1730-1846 freed (2026-10-01, UNTESTED in game)
- trailer.py block 'C3' (230 B): Lib, Sup, CON (32 B each), Intercontinental pair (4 B), CAF CL/CWC/CAF Cup, CONCACAF (32 B each).
  load_trailer: defaults first; 1.0/1.1 'S2'/'SA' block in someLeaguesTable[1740..] -> read, then CLEARED (sum 0, checksum kept);
  trailer 'C3' all / 'C2' extra 4 / 'C1' CAF 3; then career mark 'S3' + balance 0x7A at someLeaguesTable[1847..1849] (+ copy).
- sacups: init_sa = "no S3 mark -> call [NEW_CAREER_PTR]" (trailer.new_career_defaults via a dword filled after the trailer is
  assembled); load_slot1 no longer reads lists; lists_out is a no-op (season end stores nothing: lists live in the cave until saved).
  sacups exports TABLES (someLeaguesTable, leaguesTableCopy) and SAVE_ITEMS.
- Free global numbers now: 470-474, 1730-1846 (117), 1960-1999 (40). patch.write_new_teams reserves only 1847-1849.
- Builds IT EN FR DE = . Saves backed up in c/SAVES_BACKUP/.
- TEST: load a 1.0 save (RIVER.CAR, S2), a 1.1 save (EGY2.CAR, S2 + C1), NEXACA.CAR (S2 + C2); save each under a new name ->
  +230 B 'C3', someLeaguesTable[1740..1842] = 0, 'S3' mark; reload; new career after loading a save -> 1997 lists.
- PLAYTEST session 22 (Davide): PASSED. RIVERN (from RIVER, 1.0 without block): defaults, C3; EGY2N (S2 + C1): SA lists + INT
  (JUVENTUS - SAO PAULO) from S2, CAF from C1, CONCACAF default; NEXACAN (S2 + C2): all migrated. All: 230 B 'C3' trailer,
  someLeaguesTable[1740..1842] zero, 'S3' 53 33 7A at 1847, table sum 0.

## Session 23 — Asia (2026-10-01, static checks only, UNTESTED in game)
- Country numbers 86..99 checked: every "national team" test in the code is 80 <= n <= 85 (28 sites listed), tables are 256 entries
  -> 86+ are club countries. Assigned: South Korea 61, China 63, Saudi Arabia 86 (Guatemala 87, Honduras 88 next).
- tools/asia.py (reuses africa.build/countries_config, now parameterised): KOR 10 clubs (1997 K-League), CHN 12 (1997 Jia-A),
  KSA 12 (1996-97), RSSSF allfirst97/allfirst9697. Generated squads (templates: J-League TEAM.055 for KOR/CHN, Algeria for KSA),
  nationalities KOR 127, CHN 139, KSA 131. Bases 1730/1740/1752. Leagues ids 0xB7-0xB9 (first league ids after the cups range),
  national cups 0xBA-0xBC (8 teams). Season months: KOR/CHN as Japan (0x10/0x50), KSA 0x40/0x28.
- cafcups.CUPS + ASIAN CLUB CHAMPIONSHIP 0x7A (Japan/Korea/China/Saudi ranks 1-3, Taiwan/India 1-2) and ASIAN CUP WINNERS CUP 0x7B
  (next ranks); Asia continent table [WCQ, Asian Cup, ACC, ACWC] + [75, 55, 67, 61, 63, 86]. QTABLE 28 countries.
- trailer 'C4' (294 B, 10 items); old trailers table: C3 (8 items), C2 (CAF+CONCACAF), C1 (CAF). mkpatcher VERSION 1.2 + TEAM.061/063/086.
- Builds IT EN FR DE = 059dcfc0 1d7b74c4 bd6c7a93 7c00cc18 ; TEAM.061/063/086 = dba8059d d61bbc3d 810a88f0 
- Free global numbers now: 1764-1846, 1960-1999, 470-474.
- TEST: Asia menu (3 new countries, 2 cups; names fit?); career with a Korean/Saudi club; save (+294 B 'C4') / reload; load NEXACAN (C3).
- PLAYTEST session 23 (Davide): all OK. ASIA1.CAR (Korean club) 102287 B, 'C4' 294 B, lists recomputed at season end
  (ACC: YAKUHEMA MERUNOS, CHI-HAI, PUSAN DAEWOO, EAST BENGAL...). PASSED.

## Session 24 — Guatemala and Honduras (2026-10-01, static checks only, UNTESTED in game)
- tools/namerica.py: Guatemala 87 (12 clubs, play-off champion Comunicaciones first), Honduras 88 (10 clubs), 1996-97 (RSSSF
  allfirst9697). Generated squads on El Salvador templates (TEAM.051), nationalities GUA 53, HON 54, bases 1764 / 1776, league ids
  0xBD/0xBE, national cups 0xBF/0xC0 (8 teams), season months as El Salvador. North America table [51, 60, 73, 47, 87, 88].
- CONCACAF list 1.2: MEX 4, USA 3, CRC 3, SLV 2, GUA 2, HON 2 (Necaxa, DC United, Saprissa, Comunicaciones, Olimpia, Cruz Azul...).
  QTABLE 30 countries. mkpatcher + TEAM.087/088.
- Builds IT EN FR DE = cb940d42 ad93f6cb dd7d41b0 2e92ddcd . Free global numbers: 1786-1846, 1960-1999, 470-474.
- PLAYTEST session 24 (Davide): OK. OLIMPIA.CAR (Honduran club) 'C4', CONCACAF recomputed with GUA/HON clubs. PASSED.

## Release 1.2 (2026-10-01, Davide's ok)
- Patcher 1.2: 19 outputs (4 CD exes, TEAM.020, 10 new TEAM files shipped whole with TEAM.020, 4 GOG exes); Node test 19/19 OK.
  GOG rebuilt: IT 8bfdd743, EN ef2b78a7, FR a82592bd, DE e8daa60a (2 bytes from the CD builds).
- Manuals IT+EN: chapter 19 extended (Asia, Central America, CONCACAF, trailer C4/S2 migration, country numbers 86+), note in 15,
  overview, limits, history 21-24, roadmap. README + release notes (invented players: 138 clubs).

## Session 25 — Libertadores 5 gironi (2026-10-01, static checks only, UNTESTED in game)
- Report by Playaveli (Swos2020 lead): the 1996/1997 Libertadores had 5 groups of 4 (two countries per group), top 3 + the
  holder (bye) to a two-leg round of 16. 1997 groups (Wikipedia): BOL+PAR, ARG+ECU, CHI+VEN, BRA+PER, URU+COL; River holder.
- ANALYSIS (type-2 contest struct, converter cseg_24DFA -> DIY file, stage records 0x76 B at +0x15D..):
  [0Eh] stage count, [0Fh] teams, then per stage a triple (teams, groups, teams per group) -> [161h] [169h]/[15Dh] [16Bh];
  the next triple's first byte = teams going through ([163h]); after the last stage the winners' count (01); groups = FF in
  a triple = third-place match (World Cup). From +22h one byte per stage: bits 7-6 legs (0x94 two legs, 0x14 one match).
  Teams per group must be even (int 3 otherwise). [0Ah] = groups home and away (CC 1, Copa/EC/WC/Asian 0).
  Examples: CC 04 10 04 04 | 08 00 08 | 04 00 04 | 02 00 02 | 01; WC 06 18 06 04 | 10 00 10 | 08.. | 04.. | 02 FF 02 | 02.. | 01;
  Copa America 04 0C 03 04 | 08 00 08 ... (2 best thirds); Asian Cup 05 1E 05 06 | 10 00 10 ... (5 groups of 6 -> 16).
- Group stage end = cseg_8A2CE (WC: cseg_8A94F): q = advancing / groups, r = remainder; merged table scored by place
  (1st..q-th by group order, the (q+1)-th of every group sorted by their record), first r of those go through too. Then
  the knockout draw (cseg_26A78): after a group stage no strength seeding, pairs i vs n-1-i, home/away random.
  => 5 groups of 4, 16 through = top 3 + best 4th is native (same rule as the original Asian Cup).
  NO byes: every team of the list plays the group stage (team table = [0Fh] teams, groups equal size) -> holder must play
  in a group. Chosen fallback: holder in its country's group in place of its runner-up (rule of 1.0-1.2, no 3 clubs of one
  country in a group, CONMEBOL swap kept); 16 = top 3 + best 4th. 1997 list: River replaces Racing (ARG runner-up).
  Known: R16 pairs 1st A-best 4th, 1st B-3rd E ... 2nd A-3rd A (same group: inherent to i vs n-1-i). Final kept single
  match (0x14) as in every original SWOS cup (two-leg final untested in the engine: possible experiment).
- Career: slot 3 holds a type-2 contest as the whole DIY file (cseg_8B71C: type 2 -> diyFileBufferCopy, 0xB52 B), current
  stage 0x443 B: 20 rows end at 0x2C3 + 20*18 = 0x42B < 0x443. cseg_8D661 counts type-2 teams by [+0Fh] = 20. OK.
- IMPLEMENTED: sacups LIBERTADORES (20, 1997 groups, River holder), LIB_STAGES, LIB_Q = champion + runner-up of all 10
  countries (5 groups of 2 countries, 1997 pairings, fixed every season), CON_Q = ARG 3-5, BRA 3-5, CHI 3-4, URU 3-4,
  others 3rd; holder loop LIB_N. trailer 'C5' (302 B: Lib 40 B); 'C4'/'C3' read through OLD_ITEMS (Lib -> LIB16 buffer),
  1.0/1.1 S2/SA too; lib_merge: old 16 clubs = groups 1-4 + first 4 default clubs not among them = group 5.
  salists.py decodes C4/C5 trailers.
- Builds IT EN FR DE = 707068a3 ca5cf9c0 97928a51 b40b2943; GOG 6fddbd2b 6be9f5f7 a01027c5 4d3d37d7 (2 B from CD each).
  TEAM files unchanged. 1.2 exes backed up in c/REL12 (+ c/REL12/gog). Diff vs 1.2: obj2 identical; obj1 below the caves
  only the 7 hook call displacements (SA cave +8 B); fixups outside caves: SA/Europe continent tables, intl list.
- TEST: preset Sudamerica -> Libertadores: 5 groups of 4, then round of 16; River career to season end (new lists: 20,
  champions + runners-up); save (+302 B 'C5') / reload; load OLIMPIA.CAR / ASIA1.CAR (C4: group 5 = GUARANI, ORIENTE,
  CERRO PORTENO, VELEZ for OLIMPIA).

## Session 26 — tornei storici: analisi (2026-10-01, analysis only, no code, builds untouched)
Goal (Davide): historic tournaments with real squads, playable ONLY in preset competitions and season, never in career:
World Cup 1982, European Cup 1988-89, Serie A 1986-87 (alt. Euro 88). Disassembly line numbers = ref/swos.asm.

### How the team/competition menus are built
- Every selection screen is SelectTeamsFinalMenu (63087) started with D0=255 -> D7=254 -> competitionsTable[254] = worldTable
  (193158): [worldCup, -1] + bytes 80..85 (continents) + FF. Country bytes after -1 are read ONLY when D7 = 254 or 80..85
  (63522); a club country's table is [leagues, -2, cups, -1] (cups shown only if showCupsAndOther).
- Callers (all start from the world table): SelectTeamsForPresetCompetition (64253, choosingPreset=1, showCups=1),
  season cseg_4C6EE (64276, playSeason=1, showCups=0), GoGetTeamsForPlay (friendly/DIY), ChooseCompetitionMenu (career
  ViewWorldMenu), ChooseTeamsDialog (career SelectTeamToManage, edit/import teams), cseg_4C83A (career Buy Other Domestic/
  Foreign Player).
- Season (InitNewSeason 124910): slot 0 = first entry of competitionsTable[country], slots 1-2 = the entries after -2 -> a
  country used in Season must have ONLY its league (+ real national cups), never the historic cups.

### a) Container + exclusion from career (b): swap the world table, no menu filtering
- Hook: replace `call SelectTeamsFinalMenu` in SelectTeamsForPresetCompetition and in cseg_4C6EE with calls to a cave stub that
  saves competitionsTable[254], writes the address of an extended world table (preset: + CLASSICS 89 + league countries;
  season: + league countries only), calls SelectTeamsFinalMenu, restores the saved dword. 2 retargeted calls + ~40 B cave.
- Every other path (career start, career world view, transfers, edit/import teams, friendlies, DIY) keeps the original world
  table -> historic countries are simply unreachable there. Filtering inside the country loop is NOT safe (click index maps to
  the byte list). Not added to continent tables, seasonEndList, QTABLE, trailer -> career never loads their files.
  Foreign market uses POOLPLYR.DAT, not team files. teamsCountryNumbers has 1 xref (SetTeamGlobalNumbers) -> no reverse lookup.
- Layout proposal: 89 'CLASSICS' (it 'STORICI') = cups-only table [-2, WC82, EC89, (Euro 88...), -1] (preset only; no team
  file of its own: cups list teams as (file, ordinal) pairs like euroCup/worldCup, country byte FF); each historic league = its
  own country with [league, -2, -1] (e.g. 91 'ITALIA 1986-87', TEAM.091), in both extended tables. Team files: 89 = WC82
  nations, 90 = EC 88-89 clubs, 91 = Serie A 86-87 (one file per tournament).
- countries.py needs a 'historic' flag: register countriesTable/competitionsTable/teamsCountryNumbers, skip continent tables
  and seasonEndList.

### c) National teams in a club-numbered file (89)
- National tests are all 80 <= n <= 85. IsTeamNational (50206) returns 1 for every team outside career (irrelevant);
  CheckIsTeamNational sets isNationalTeam which nothing reads; FillManagementRecordInfo / ProcessCareerFile helpers = career only.
  Remaining non-career sites: SquadFinish (2434: squad menu entries 13/55 moved up 13 px for national teams = cosmetic),
  cseg_47981 (59610, team byte 301) and cseg_48CA1 (60782) not decoded -> playtest item (squad screen, match). No rule found
  (foreigners, subs) tied to 80..85 outside career. Kits/faces/nationalities come from the records (copy the 1996 national
  records from TEAM.080-085 as templates).

### d) Global numbers
- SetLoadedTeamsGlobalNumbers runs at every LoadTeamFile; SetLeagueNumbers / someLeaguesTable only in career (39137).
- Historic teams never meet each other across tournaments nor real teams (preset/season only, own files), so ALL historic files
  can share ONE block: base 1786 for every file (ordinals 0..31) -> 32 numbers total for any number of tournaments
  (left after that: 1818-1846, 1960-1999, 470-474 = 74). Unique inside each file. Not using >= 2000 (non-career arrays indexed
  by global number not fully excluded).

### e) Contest ids
- Used by the mod up to 0xC0; free 0xC1..0xFE (no range checks known, ids = identifiers + Randomize seed).
  Proposed: 0xC1 WC82, 0xC2 EC 88-89, 0xC3 Serie A 86-87, 0xC4 Euro 88.

### Formats
- World Cup 1982: the game's own worldCup (187280) is already 24 teams, 6 groups of 4, best 16 (incl. 4 best thirds) -> round of
  16, QF, SF, F = the 1986 format: closest approximation (real 1982: 12 teams to a second group stage of 4x3, then SF). Clone it
  with 24 pairs (89, 0..23) and the real draw order (group A Italy/Poland/Peru/Cameroon ... ). Same 2-points rule? cup structs
  have the points byte (3) -> set 2 for 1982/88.
- European Cup 1988-89: 32-team two-leg knockout, single final = cupWinnersCup layout (32 pairs (90, 0..31)).
- Serie A 1986-87: league 1 division of 16, 2 games, 2 points per win, no promotion/relegation.
- Euro 88: europeanChampionships clone (8 teams, 2 groups of 4 -> SF, F).

### Data / effort
- 72 teams x 16 players: WC82 from one Wikipedia squads page (easy), Serie A 86-87 from it.wikipedia club season pages (good),
  EC 88-89: big clubs good, minor clubs (Valur, Dundalk, Pezoporikos, Jeunesse Esch...) partial -> partly reconstructed.
- Strength: c1c2-style calibration from the real final ranking (WC: final position; EC: round reached; Serie A: table), stars
  hand-set to max (Maradona, Platini... per tournament list).
- Estimate: impianto + WC82 = 1.5 sessions; Serie A 86-87 = 1; EC 88-89 = 1.5-2 (Euro 88 instead = 0.5). Docs/release apart.
- RELEASE NOTES 1.3 (Davide's ok): explain that the game has no byes, so the holder plays the group stage in place of its
  country's runner-up (rule since 1.0); with 16 of 20 going through it is almost a bye. Also mention: final single match,
  R16 pairing 2nd A - 3rd A same group (engine draw).
- PLAYTEST session 25 (Davide): tests 1-4 PASSED (menu 5 groups + R16, River career season end, save/reload, OLIMPIA/ASIA1
  C4 load). RIVER20.CAR = 126235 B (N=45, 'C5' 302 B): Libertadores of 20 from the standings (BOLIVAR, PRESIDENTE HAYES,
  WILSTERMAN, CERRO PORTENO / INDEPENDIENTE, EL NACIONAL, RIVER PLATE, EMELEC / ...), Intercontinental JUVENTUS - GREMIO
  (Gremio won the 20-club Libertadores; in Lib as BRA2 and in Supercopa). No club in both Libertadores and CONMEBOL.
- 1.3 prepared locally (Davide's ok after the playtest): manuals IT+EN (chapter 9 group formats, 14, 19, 20, 21, build md5),
  mkdocs, artifacts republished (EN v9, IT v8), internal hex manual v3 (CC vs Libertadores 1.3 dumps, C5 block of
  RIVER20.CAR); README EN/IT; patcher 1.3 (template notes, VERSION 1.3, Node test 19/19); release/notes-1.3.md;
  thank-you texts release/announcements/1.3/playaveli-thanks-{en,it}.txt. NOT pushed / released: waiting for Davide's ok.

## Release 1.3 (2026-10-01, Davide's ok)
- Pushed (main 91c220d) and released: github.com/aminta/swos-9697-mod/releases/tag/v1.3 (patcher 1.3 attached, notes from
  release/notes-1.3.md). Pages updated (manual "sessions 1–25, release 1.3"). Thank-you texts for Playaveli in
  release/announcements/1.3/ (to be posted by Davide).

## Session 26b — historic tournaments: framework + World Cup 1982 skeleton (2026-10-01, static checks only, UNTESTED in game)
- Davide's list (changed after the analysis): World Cup 1982 first, then European Cup 1959-60 (Puskas/Di Stefano), then one
  tournament of another era that is neither a World Cup nor a European Cup. Davide: use the SWOS 2020 community data (they
  made many historic teams and would be happy we use them) -> get their files before writing squads by hand.
- tools/historic.py: country 89 CLASSICS (it STORICI, fr CLASSIQUES, de KLASSIKER), countriesTable record (continent Europe),
  teamsCountryNumbers[89] = 1786 (shared base for all historic files, 1786..1817 reserved), competitionsTable[89] = [-2, WC82,
  -1]. WORLD CUP 1982 (id 0xC1) = clone of the game's worldCup (24 teams, 6x4, best 16) with points byte 2 and 24 pairs
  (89, 0..23) in the real group order A-F; name = the language's World Cup name + ' 1982'.
- Hook: `call SelectTeamsFinalMenu` in SelectTeamsForPresetCompetition (IT obj1+0x3C553 area, found by pattern in all 4 exes)
  -> hist_preset: push [competitionsTable+254*4]; point it at the extended world table [worldCup, -1] + continents + 89 + FF;
  call; pop. Season call left untouched (no historic league yet). patch.py: historic.patch after countries.patch, TEAM.089
  written by write_new_teams (global numbers checked free).
- TEAM.089 = PLACEHOLDER: the 1996 national records of the 24 nations (renamed WEST GERMANY, CZECHOSLOVAKIA, USSR), real 1982
  squads still to do (SWOS 2020 data or Wikipedia + c1c2-style calibration).
- Builds IT EN FR DE = c0d88d2b 94d2a07d 7dd496e5 021fa4fa, TEAM.089 e544e16b; installed in c/SWOS (session 25 exes backed up in
  c/S25BAK, IT 707068a3). Other TEAM files byte-identical.
- PLAYTEST: (1) preset competition -> top menu shows CLASSICS/STORICI after the continents -> WORLD CUP 1982 -> plays (groups,
  2 points, knockout); (2) season menu: no CLASSICS; (3) career: new career team choice, world view, transfer search: no
  CLASSICS; (4) friendly/DIY team choice: no CLASSICS; (5) save/load a running WC 1982 preset competition.
- PLAYTEST session 26b (Davide, 2026-10-01): all OK (CLASSICS/WC 1982 in preset; absent from season/career/friendly/DIY).
- Decided: third historic tournament = Mitropa Cup (1930s). Order: WC 1982 real squads -> European Cup 1959-60 -> Mitropa 1930s.
  Squads: ask Davide for the SWOS 2020 community files (location/format) first.
- SWOS 2020 historic data (search 2026-10-01): DLCs for every World Cup WC1950..WC2018 and Euro EC1960..EC2020 exist, installed
  through the in-app DLC Manager of SWOS 2020 (Windows app, v7.7, 94 MB, sensiblesoccer.de/swos-2020). No club/Mitropa DLC seen.
  No local copy (old CrossOver bottles 'Swos 2020' deleted; installer swos2020_4.0_setup.exe no longer in Downloads).
  Plan: with Davide's ok download SWOS 2020, install in CrossOver, fetch the WC1982 DLC (and others), compare their team format
  with TEAM.xxx (SWOS 2020 derives from the 96/97 DOS exe -> probably same 684-byte records), convert into TEAM.089.
  European Cup 1959-60 and Mitropa 1930s: probably by hand (Wikipedia/RSSSF + c1c2-style calibration).
- SWOS 2020 data permission (2026-10-01, via Davide): Playaveli (SWOS 2020, curator of the historic DLCs): "I think it's fine.
  Just use it... and credit the author"; per-DLC authors: "see DLC window" (DLC Manager) -> copy the exact credits from there
  into README / release notes / manuals when the historic squads ship.

## Session 26c — World Cup 1982 real squads from SWOS 2020 (2026-10-01, UNTESTED in game)
- SWOS 2020 DLC server: https://sensiblesoccer.de/swos2020/dlc/<kind>/<Name>.7z with indexes dlc/cup/cup-info.csv and
  dlc/teamdb/teamdb-info.csv (Name, Author, Version). Cup DLC = CUSTOMS.EDT (48 x 684 B records, SAME format as TEAM files)
  + a .DIY cup. Historic: every World Cup 1930-2026 and Euro 1960-2024 (author "Insane"), CLUB TEAMS 1956-1979 / 1970s / 1980s
  ... (Insane), UEFA European Cup 1991-92, CL 1992-96, "1900s Retro Pack Teams (1900-1970)" (Francescomanetti82 and Gorzo),
  "British Football Pioneers", "1968-69 TEAMS" (Kanchelskis); teamdb "VIVA SWOS (History of the World Cup 1930-1974)" (Kazax),
  "Synchronated SWOS Legends". Candidates: EC 1959-60 -> CLUB TEAMS (1956-1979); Mitropa 1930s -> 1900s Retro Pack.
- Downloaded '1982 FIFA WORLD CUP (Spain)' v1.1 by Insane -> orig/swos2020/ (git-ignored; CUSTOMS.EDT md5 fa21fa9d, WC1982.DIY,
  the two index csv). historic.build_teams takes the 24 nations by name in group order A-F (+24 legend teams ignored), sets
  byte0 89, ordinal, global 1786+i; skills/prices kept as the author's (avg 34-41, max 49 = Maradona).
- TEAM.089 = 47b28c41 (16418 B), exes unchanged (c0d88d2b ...). Credit for README/release: "World Cup 1982 squads: SWOS 2020
  DLC by Insane (SWOS United, sensiblesoccer.de), used with permission".
- Public use OK (Davide relayed, 2026-10-01: "Just use it... and credit the author"): TEAM.089 may ship in the patcher with the credit above.
- Checked candidate DLCs (orig/swos2020/x_*): 'CLUB TEAMS (1956-1979)' (Insane) = only the European Cup FINALISTS 1956-79
  (2 per year: REAL MADRID 60 + FRANKFURT 60 for 1959-60; nearby: REIMS 59, REAL MADRID 59, BARCELONA 61, BENFICA 61, MILAN 58).
  '1900s Retro Pack Teams (1900-1970)' (Francescomanetti82 and Gorzo) = 48 iconic clubs (REAL MADRID 1958, BARCELONA 1951,
  ARSENAL 1930, BAYERN 1931, HERTHA 1929, AIK 1931, BOCA 1919...) but NO Mitropa clubs (Bologna, Ambrosiana, Juventus, Rapid,
  Austria Wien, Admira, Sparta, Slavia, Ferencvaros, Ujpest). => EC 1959-60: 2 clubs from SWOS 2020, the others by hand;
  Mitropa 1930s: all by hand (Wikipedia/RSSSF) unless another DLC has them.

## Session 26d — World Cup 1982 with the REAL formula (2026-10-01, UNTESTED in game)
- Davide: never approximate when the real format can be replicated (memory feedback_swos_exact_formats).
- Contest stages (+0Eh): count, (teams, groups, teams per group) per stage (knockout groups 0, 3rd place FF), then 1
  right after the last stage, padding; +22h one byte per stage (0 groups, 0x14 single match, 0x94 two legs). The DIY
  designer draws "%0 GROUPS OF %1" for ANY round and the round names include FINAL GROUP(S) -> group stages after the first
  are supported by the engine.
- WC82 stages: [5, 24,6,4, 12,4,3, 4,0,4, 2,FF,2, 2,0,2, 1, 0..., legs 0,0,14,14,14]: 6x4 (top 2) -> 4x3 (winners) -> SF,
  3rd place, F; 2 points. Builds IT EN FR DE = ee4ae05b d8834c10 02d6c886 14619f2f (TEAM.089 47b28c41), in c/SWOS.
- TO VERIFY in game: how the engine fills the second-round groups (real 1982: A Poland/Belgium/USSR = 1A,1C,2F;
  B FRG/England/Spain = 1B,1D,2E; C Italy/Argentina/Brazil = 2A,2C,1F; D Austria/France/N.Ireland = 2B,2D,1E) and
  which group winners meet in the semis (real: A-C, B-D). If the engine's rule differs, find the code and replicate.
- PLAYTEST 26d: freeze on TORNEO. Cause: cseg_24DFA (preset/DIY cup -> DIY tournament buffer) traps `test D0,1; jz; int 3;
  jmp $` on an ODD teams-per-group count. Group stages run as DIY leagues (DIY_competitionStart: [79] groups, [81] per group,
  [453] = n div 2 matches per group per day, days = n(n-1)/2 / (n div 2) = n for odd n) and DIY leagues accept 2..24 teams
  (DesignDIYLeagueChangeNumberOfTeams) -> historic.odd_groups turns that jz into jmp (IT/FR/DE obj1+0x1523F, EN +0x153F4).
  Builds IT EN FR DE = 87b7b35b 1dcfc517 cc517a10 d3e33d09 (c/SWOS). UNTESTED.
- Next-round placement (for the exact 1982 second round and SF A-C / B-D): group qualifiers are scored in cseg_8A2CE
  (worldCup has its own cseg_8A94F; generic: rank bonus 7D00h - 100*group - 1000*rank) and sorted -> list 1A..1F, 2A..2F
  (to verify: the score field +2C3h may already hold points); the next round is filled by cseg_26DFC (worldCup:
  cseg_277E5, Euro: cseg_31CFE; generic with struct[9]=0 -> cseg_27F08 draw, else slot-major fill). Plan: hook cseg_26DFC
  for id 0xC1 and permute A2+59h with the 1982 table [0,2,11, 1,3,10, 6,8,5, 7,9,4] (round 2) and [0,2,1,3] (SF).
  Same hook could give the real 1997 Libertadores (holder straight into the round of 16).
- PLAYTEST odd groups (Davide): OK, 4 groups of 3 play. Second round was a RANDOM draw (cseg_27F08 = Fisher-Yates shuffle of
  A2+59h, called from cseg_26A78 and cseg_26DFC when round struct[9] = 0).
- historic.hist_draw replaces both `call cseg_27F08`: if (contest id, round teams) is in DRAWS -> permute A2+59h
  (new[k] = old[perm[k]]), else the original shuffle. WC82: 12 -> [0,2,11, 1,3,10, 6,8,5, 7,9,4] (1A 1C 2F | 1B 1D 2E |
  2A 2C 1F | 2B 2D 1E), 4 -> [0,2,1,3] (SF A-C, B-D). Qualifier order verified statically (cseg_8A2CE: +2C3h = points,
  cleared by cseg_26395; bonus 32000 - 100*group - 1000*rank). Builds IT EN FR DE = 33c2602b c64bf941 fc3f702f 70537ae3.
- CLASSICS button styling (Davide): hist_names replaces `call SetCountryNames` in SelectTeamsReinit (IT obj1+0x3A77C; after
  SetTeamsCoordinates + SetLeagueNames); after it, the visible entry (ordinals 21..86, 56 B each, CalcMenuEntryAddress(21))
  whose fg.string (+26h) == the CLASSICS name gets bg.backAndFrameColor (+1Eh) = 11 BLUE_TO_PURPLE and y (+16h) += 5.
  (The game already colours names starting with '.' PINK_TO_BROWN_7.) Builds IT EN FR DE = 0f5d5996 af054b11 e9fd74c3 cb612d39.
- Container renamed (Davide): it 'TORNEI STORICI', en 'CLASSIC TOURNEYS', fr 'TOURNOIS ANCIENS', de 'TURNIERKLASSIKER' (<= 16 chars). Builds IT EN FR DE = be8719ea 73060d93 674693d9 2b20a4a7.
- PLAYTEST WC 1982 full (Davide, 2026-10-01): PASSED. R1 1A Italy 2A Poland, 1B Chile 2B FRG, 1C Argentina 2C Belgium, 1D England 2D France, 1E Spain 2E Yugoslavia, 1F New Zealand 2F Scotland -> R2 A Argentina/Italy/Scotland, B Chile/England/Yugoslavia, C Belgium/NZ/Poland, D France/Spain/FRG (= 1A1C2F, 1B1D2E, 2A2C1F, 2B2D1E), 2 games each; SF Scotland-Belgium (A-C), England-Spain (B-D); 3rd place England-Scotland; final Spain-Belgium. TORNEI STORICI button purple with gap OK.

## Session 26e — research: European Cup 1959-60 (parked) and Mitropa Cup 1934 (next, Davide: "il Bologna che tremare il mondo fa")
- EC 1959-60 (en.wikipedia): 27 in the draw, 26 played (KuPS withdrew). Preliminary round two legs (byes: holder Real Madrid,
  Sparta Rotterdam, Young Boys, B 1909, Red Star): Nice-Shamrock 4-3, Eintracht-KuPS w/o, Barcelona-CDNA 8-4, Wiener SC-Petrolul
  2-1, IFK Goteborg-Linfield 7-3, Jeunesse-LKS 6-2, CH Bratislava-Porto 4-1, Milan-Olympiacos 5-3, Fenerbahce-Csepel 4-3,
  Rangers-Anderlecht 7-2, Wolves-Vorwarts 3-2. First round 16 -> QF -> SF two legs (play-off on aggregate tie), final single
  match (Hampden, Real 7-3 Eintracht).
- Mitropa 1934 (en.wikipedia): 16 clubs (ITA, AUT, HUN, TCH x4), all rounds two legs incl. the final, play-off on aggregate tie
  (one decided by coin toss). R16: Ferencvaros-Floridsdorfer, Kladno-Ambrosiana, Bologna-Bocskai, Slavia-Rapid, Austria Wien-
  Ujpest, Juventus-Teplitzer, Admira-Napoli (play-off 5-0), MTK-Sparta (play-off, coin). QF: Ferencvaros-Kladno, Ujpest-Juventus,
  Bologna-Rapid, Admira-Sparta. SF: Ferencvaros-Bologna, Admira-Juventus. Final Admira-Bologna 3-2, Bologna-Admira 5-1.
  Top scorer Reguzzoni 10.
- Engine: replays exist (REPLAY strings, cup option bits from the legs byte -> round +16Dh/+16Fh/+171h), away goals exist too.

## Session 27 — Libertadores 1997 1:1 (2026-10-01, ANALYSIS, no code, builds untouched)
- REAL 1997 FORMAT (RSSSF sacups/copa97, Wikipedia "1997 Copa Libertadores"): 21 clubs. 20 in 5 groups of 4 (two
  countries per group: BOL+PAR, ARG+ECU, CHI+VEN, BRA+PER, URU+COL), home and away, 3 points; River Plate (holder) bye
  straight to the round of 16. Top 3 of every group (15) + holder = 16. NO best 4th. Groups 1997: G1 Bolivar, Oriente
  Petrolero, Guarani, Cerro Porteno; G2 Velez, El Nacional, RACING, Emelec; G3 Colo-Colo, U. Catolica, Minerven, Mineros;
  G4 Gremio, Cruzeiro, Sporting Cristal, Alianza Lima; G5 Penarol, Millonarios, Nacional, Deportivo Cali.
  R16 (first-leg host first, Wikipedia bracket order): 3G2 Racing - H River | 2G5 Millonarios - 1G5 Penarol |
  3G4 Sporting Cristal - 1G2 Velez | 3G3 Minerven - 1G1 Bolivar | 2G2 El Nacional - 2G4 Cruzeiro | 3G1 Guarani - 1G4 Gremio |
  3G5 Nacional - 1G3 Colo-Colo | 2G3 U. Catolica - 2G1 Oriente. Group winners + holder host the 2nd leg.
  QF (fixed bracket): Penarol(T2)-Racing(T1), Bolivar(T4)-S.Cristal(T3), Cruzeiro(T5)-Gremio(T6), U.Catolica(T8)-Colo-Colo(T7).
  SF: Racing-S.Cristal, Cruzeiro-Colo-Colo. FINAL two legs: S.Cristal-Cruzeiro 0-0, 0-1.
  Ties: aggregate, NO away goals (Racing-River 3-3 a, 1-1: River would have gone through on away goals, Racing won 5-3 on
  pens), NO extra time (RSSSF marks no 'aet' anywhere), straight to penalties.
  1996 (holder Gremio, BRA in G4) used a different R16 schema: holder - 3rd of its own country's group (3G4), 1G2-2G5,
  1G5-3G2, other ties as 1997 -> the schema depends on the holder's group (no general rule derivable from 2 editions).
- DIFFERENCES vs 1.3 (session 25): holder plays the groups in place of Racing (should be 21 clubs, holder bye); best 4th
  goes through (should not); R16 pairs i vs n-1-i with random home (should be the fixed table above); QF/SF random draw
  (fixed bracket); away goals after 90' ON (OFF); extra time ON (OFF); final single match (two legs).
- ENGINE FINDINGS:
  * contest header [0Ah] is NOT "groups home and away" (session 25 note wrong): cseg_24DFA -> DIY [49h] -> cseg_258E4 ->
    competition [5Dh] = AWAY GOALS (0 off, 1 after 90', 2 after e.t.; cseg_2AE97 two-leg decision). Champions Cup = 1.
    Group home/away comes from [0Bh] -> round [165h] (meetings per group, 1..4). [0Ch] = points (167h), [0Dh] nibbles -> [4Bh]/[4Dh].
  * stage byte +22h: bits 7-6 legs (16Dh: 2 = two legs), 5-4 extra time (16Fh: 0 no, 1 yes, 2 if replay), 3-2 penalties
    (171h: 0 no, 1 yes, 2 if replay). 0x94 = 2 legs + e.t. + pens; 0x84 = 2 legs, no e.t., pens.
  * contest [8] != 0 -> DIY [4Fh] = 1 = fixed first-stage list (contest order); contest [9] -> round [15Fh] for every
    stage: 0 = cseg_27F08 shuffle (= hist_draw) then consecutive pairs; != 0 = seeded i vs n-1-i, random home (1.3 Lib: 1).
  * group stage records are indexed by TEAM TABLE INDEX (cseg_270C7: A5+6Dh = list[i]*18, A2+119h group of each index);
    A2+59h is a byte list sized for all [0Fh] teams; cseg_24DFA orders it as the contest list. Stage 1 takes the first
    [161h] entries -> with [0Fh] = 21 and stage 1 = (20,5,4) the 21st club (holder) plays no group and its index stays in
    A2+59h[20] (cseg_8A2CE rewrites only [31h] = 20 entries). Stage buffer: 21 rows end at 0x2C3 + 21*18 = 0x43D < 0x443.
  * bye: hist_draw at the R16 (id 0x6C, 16 teams): list[15] (best 4th picked by cseg_8A2CE because 16/5 leaves r = 1)
    := list[20] (holder), then the fixed permutation. Old saves: their running Lib DIY has [15Fh] = 1 -> never reaches hist_draw.
- Session 26f — Mitropa Cup 1934 skeleton (UNTESTED): id 0xC2 'COPPA MITROPA 1934' / 'MITROPA CUP 1934' / 'COUPE MITROPA 1934' /
  'MITROPACUP 1934', TEAM.090 (16 clubs, countriesTable[90] = CLASSICS record, base 1786), type-2 struct (worldCup header,
  away goals [0Ah] = 0), stages [4, 16,0,16, 8,0,8, 4,0,4, 2,0,2, 1] all 0xA8 (two legs, e.t. + pens only in the replay).
  Ties in the real order (home club first); DRAWS: 16/8 identity, SF [0,1,3,2] (Admira home first), final [1,0].
  CLASSICS table [-2, WC82, M34, -1]. TEAM.090 = PLACEHOLDER 1996 clubs renamed. Builds IT EN FR DE = 09874895 4dae5cdf
  eaaa5499 e2b5f232, TEAM.090 8e8b3a12. TO VERIFY: winners keep tie order; first-leg home = first listed; replay after a
  two-leg aggregate tie works (else ask Davide).
- Session 26g — Mitropa 1934 real squads (UNTESTED): tools/mitropa34.py (16 clubs in tie order, coach, nationality, target
  price, kit, players by role starters first; sources in its docstring: tempofradi.hu line-ups of all Hungarian-club ties,
  it.wikipedia season pages (Bologna, Juventus, Ambrosiana, Napoli), cs.wikipedia 1. asociacni liga 1933/1934 squads (Slavia,
  Sparta, Kladno, Teplitzer FK), en.wikipedia 1933-34 Rapid season). historic.build_m34: template = the club nation's 1934
  team of the SWOS 2020 DLC "1934 FIFA WORLD CUP (Italy)" by Insane (slots, shirt numbers, faces); 1934 internationals keep
  Insane's record; others levelled to the club target (c1c2.level_player); STARS (Meazza, Sindelar, Sarosi, Bican,
  Schiavio, Planicka, Reguzzoni, Nejedly, Monti, Orsi) price 49 + 1. 22 invented names for unsourced slots ('?', listed by
  the build; FAC 4, Bocskai 5, Admira 3, Austria 2, Ujpest 2, Hungaria 2, FTC/Ambrosiana/Bologna/Teplitz 1). Unknown coaches
  (FAC, Austria, Teplitz, Admira) left blank. Kits: given for FAC/Ambrosiana/Bocskai/Admira, else the 1996 club's.
  TEAM.090 5ec479a8 installed (exes unchanged 09874895...). Libertadores session works in the same tree: commit only own hunks.

## Session 27b — Libertadores 1997 1:1: implementation (2026-10-01, static checks only, UNTESTED in game)
- Davide: holder meets the 3rd of ITS OWN country's group (1997: group 2 -> exact; other groups: that 3rd and 3G2 swap
  places in the 1997 schema); replicate the real group calendar too; plan A (preset) + B (career) together.
- tools/lib97.py (commit f3bb002): lib_bye replaces `call cseg_2573C` at the end of cseg_24DFA (IT obj1+0x15335, EN
  +0x154EA): diyFileBufferCopy (IT obj2+0x4EBD4) round 1 [161h] 21 -> 20 for id 0x6C. lib_pre called by hist_draw at
  .perm: list[15] := list[20] (holder), list[11] <-> list[10+h] (h = group of a club of the holder's country, A2+119h).
  lib_cal replaces `mov esi,[A0]` at @@european_championships of cseg_89758 (IT obj1+0x79676): Lib groups of 4 read
  LIB_CAL (per group 12 slot pairs; second cycle stored reversed, the engine swaps when [5Fh] is odd). Guards: id 0x6C
  and diyFileBufferCopy [31h] = 21 (old 1.3 contests keep the game's table and [15Fh] = 1, never reach hist_draw).
  Real calendar: groups 1-4 exactly as played by matchday (days 4-6 mirror 1-3); group 5 (irregular) closest fit,
  days ordered by first match date (Millonarios exact, others swap 1-2 matches).
  DRAWS 0x6C: R16 [11,15,9,4,13,1,12,0,6,8,10,3,14,2,7,5], QF [1,0,3,2,4,5,7,6], SF [0,1,2,3], F [0,1].
- sacups: LIBERTADORES 21 (Racing in group 2, River last), LIB_GROUPS 20, stages (21,5,4)(16)(8)(4)(2) legs 0x84
  (two legs, no e.t., penalties; final two legs), contest [9] = 0, [0Ah] = 0. Season end: LIBLIST[20] = Lib winner;
  if it also qualified through its league, its berth goes to its country's 3rd (taken from the CONMEBOL list, whose
  place goes to SPARE = the rank after the country's last CONMEBOL rank: ARG/BRA 6, CHI/URU 5, others 4); if it is in
  the CONMEBOL list, SPARE takes that place. Old runner-up displacement removed.
- trailer 'C6' (304 B, Lib 42 B); 'C5' read with a 40-B Lib (OLD_ITEMS40) and completed by lib_merge with the first
  default club not in it (the season end rebuilds the list anyway); C4..C1, S2/SA as before. salists decodes C6.
- Static: ndisasm of lib_bye/lib_pre/lib_cal and of both hook sites OK (jmp -> cseg_2573C obj1+0x15587, A0 0x315D7,
  A3 0x315E3); fixup diff vs HEAD~ build: below the caves only the removed fixup of the lib_cal site (obj1+0x79678) and
  3 pointers into the world cave moved (+0x218); obj2 only the CLASSICS competitions pointer. TEAM files unchanged.
- Builds IT EN FR DE = 132c024f 8f7a1897 01ef3d79 0674721a installed in c/SWOS (includes the Mitropa 1934 work of
  session 26g); previous exes (09874895 4dae5cdf eaaa5499 e2b5f232) backed up in c/S27BAK. GOG builds not made.
- PLAYTEST: (1) preset Sudamerica -> Libertadores: 21 clubs, River in no group, Racing in group 2; group calendar
  (G1 day 1 Guarani-Cerro, Oriente-Bolivar; day 2 Oriente-Guarani, Bolivar-Cerro ...); round of 16 = 3G2-River, 2G5-1G5,
  3G4-1G2, 3G3-1G1, 2G2-2G4, 3G1-1G4, 3G5-1G3, 2G3-2G1 (first named at home in the 1st leg), QF/SF on the bracket, final
  two legs; aggregate tie -> penalties with no extra time and no away goals. (2) career with a South American club
  (River = holder: no group matches, enters the R16) to season end: new list 20 + holder; save (C6) / reload.
  (3) load RIVER20.CAR (C5) and an old C4 save (OLIMPIA.CAR).

## RELEASE TODO — sources and credits for the historic tournaments (Davide, 2026-10-01)
README + release notes (EN first, then IT) must list EVERY source used, with an invitation to contact us for corrections or
removal ("if you are an author and want something changed, open an issue / write to us"):
- SWOS 2020 / SWOS United (sensiblesoccer.de): DLC "1982 FIFA WORLD CUP (Spain)" v1.1 and "1934 FIFA WORLD CUP (Italy)" by
  Insane (squads, skills, faces, kits) - used with permission (Playaveli: "Just use it... and credit the author").
- tempofradi.hu, "A KK tortenete - 1934, a Bologna masodszor" (Mitropa 1934 line-ups).
- it.wikipedia season pages: Bologna Sezione Calcio 1933-1934, Foot-Ball Club Juventus 1933-1934, Associazione Sportiva
  Ambrosiana-Inter 1933-1934, Associazione Calcio Napoli 1933-1934; Coppa dell'Europa Centrale 1934.
- cs.wikipedia "1. asociacni liga 1933/1934" (Slavia, Sparta, Kladno, Teplitzer FK squads).
- en.wikipedia "1933-34 SK Rapid Wien season" (data from rapidarchiv.at), "1934 Mitropa Cup", "1959-60 European Cup".
- RSSSF (Karel Stokkermans), "Mitropa Cup 1934" (results, play-offs).
- hu.wikipedia "1934-es kozep-europai kupa"; A Ferencvarosi TC 1933-1934-es szezonja.
Keep this list updated as new tournaments are added (European Cup 1959-60 next). Mention invented names (marked in STATUS).
- PLAYTEST Mitropa 1934 (Davide, 2026-10-01): 'ok a posto' (build 132c024f from the Libertadores session, includes M34). Next: FA Cup 1871-72 (first edition) - analysis.

## Session 26h — FA Cup 1871-72 (first edition): research (Davide's choice; format agreed 2026-10-01)
- Format agreed: 15 real clubs, real first-round draw (7 ties + Hampstead Heathens bye), single matches, NO extra time, NO
  penalties, replay on a draw (legs byte 0x00), open draw each later round (engine draw), final. Not reproducible: walkovers,
  withdrawals, committee "both teams go through" decisions (Hitchin-Crystal Palace, Queen's Park-Donington, Wanderers-Crystal
  Palace), Queen's Park withdrawing before the semi-final replay.
- Line-up sources found: en.wikipedia "1872 FA Cup final" (both XIs, kits: Wanderers orange/violet/black halves? (pattern),
  RE red/navy hoops + navy shorts), "1871-72 Barnes F.C. season" (Barnes x6, Civil Service, Hampstead Heathens x2, Crystal
  Palace v Barnes), "1871-72 Queen's Park F.C. season" (SF XI; QP played dark blue shirts, grey shorts, black socks),
  England v Scotland 1870-72 page (players with clubs), forum.hitchintownfc.club t=2506 (Hitchin v CP and Hitchin v RE, both
  teams), cpfc.co.uk Peter Manning articles (CP: Chenery, Chappell, Ottaway, Morten in goal), stevesfootballstats.uk (results,
  scorers: Dunnage, P. Weston; Young 2 for Maidenhead; Kenrick 2 + Thompson for Clapham; Pelham for Wanderers; Bouch, Chenery,
  Lloyd for CP; Highton/Barker; Leach; Renny-Tailyour 2, Mitchell).
- Missing: Clapham Rovers, Upton Park (Ogilvie, Stair), Maidenhead (Young), Marlow, Reigate Priory, Donington School,
  Harrow Chequers (Betts, Welch + few). Pioneers DLC (Francescomanetti82 & Gorzo) has Barnes, Civil Service, Clapham, Crystal
  Palace, Hampstead, Marlow, QP, RE, Upton Park, Wanderers but mixes decades and invented/modern names -> only verifiable names.
  Pioneers almanac PDF (tinyurl in the DLC readme) not downloaded yet (needs Davide's ok).
- PLAYTEST 27b preset (Davide, 2026-10-01, IT): PASSED from screenshots. Groups 5x4 without River, Racing in group B;
  last group match Penarol-Dep. Cali (real last day of group 5). R16 exactly per table: Emelec(3B)-River, Cali(2E)-
  Nacional(1E), Gremio(3D)-El Nacional(1B), U.Catolica(3C)-Bolivar(1A), Racing(2B)-Alianza(2D), Guarani(3A)-Cruzeiro(1D),
  Millonarios(3E)-Colo Colo(1C), Mineros(2C)-Cerro(2A), first named at home in the 1st leg. No away goals (Cerro-Mineros
  2-2 a, 1-1 -> penalties). QF Nacional-Emelec, Bolivar-Gremio, Alianza-Cruzeiro, Mineros-Colo Colo; SF Nacional-Bolivar,
  Cruzeiro-Colo Colo; two-leg final Bolivar-Cruzeiro, 0-0 aggregate -> penalties. Still to test: career + C6/C5/C4 saves.
- PLAYTEST 27b career River (Davide): season 1 River (holder) played no group, R16 vs Velez (3rd of group B = holder's
  country group) away first, home second; Supercopa and league unaffected. Season 2 list (RIV27.CAR, trailer C6 304 B,
  salists): 20 group clubs from the standings (River in group B as ARG 1/2) + holder NACIONAL (season-1 winner, URU,
  not in URU top 2 nor in CONMEBOL) as 21st; Intercontinental AC MILAN - NACIONAL. Still to test: reload RIV27.CAR,
  RIVER20.CAR (C5), OLIMPIA.CAR (C4).
- PLAYTEST 27b saves (Davide): RIV27.CAR reload OK (same groups, holder outside). RIVER20.CAR (C5) and OLIMPIA.CAR (C4)
  load, play to season end and save as RIVER20B.CAR / OLIMPIAB.CAR with trailer C6: new lists 20 + holder (RIVER20B:
  ATLETICO MINEIRO, not in BRA top 2 nor CONMEBOL, also added to the Supercopa; Intercontinental JUVENTUS - ATLETICO
  MINEIRO. OLIMPIAB: SAO PAULO). ALL 27b TESTS PASSED. Not exercised yet: holder also qualified through its league
  (3rd moves up from CONMEBOL, SPARE fills) and holder in the CONMEBOL list; extra time absence not seen on screen.
- Release plan (Davide, 2026-10-01): pushed main up to 0844f4e; ONE release 2.0 (Davide: big release) when the historic tournaments are done
  (FA Cup 1871-72 included). Ready for it, local only: manuals IT/EN Libertadores 1997 (9a83c61, mkdocs rebuilt; artifacts
  to republish at release), release/notes-1.4.md draft (42ca203). Still to do at release: historic section + credits,
  patcher (mkpatcher.py), GOG builds, artifacts, tag, announcements (Playaveli thanks).
- Session 26i — FA Cup 1871-72 built (UNTESTED): id 0xC3 'FA CUP 1871-72', TEAM.091 (15 clubs, base 1786, countriesTable[91]
  = CLASSICS record). Struct = worldCup header, stages [4, 15,0,15, 8,0,8, 4,0,4, 2,0,2, 1], legs 0 (1 leg, no e.t., no pens
  -> replay on a draw), away goals off. Clubs in the real first-round order, Hampstead Heathens (bye) 15th. lib97.lib_bye:
  FA with [161h] 15 -> 14 (round 1 without the bye club); hist_draw DRAWS (FA,14) identity, (FA,8) [FF] = 'pre only':
  lib97.lib_pre puts list[14] (never touched: cseg_8A7BF copies [31h] = 14 entries, cseg_2ACAE winners first) into list[7]
  (= first loser) and then the game's random draw (open draw as in 1872); later rounds random too. CLASSICS table
  [-2, WC82, M34, FA, -1].
- Squads: tools/facup72.py (sources in its docstring, incl. British Newspaper Archive OCR snippets via Davide's account:
  Reading Mercury / Windsor & Eton Express 18 Nov 1871 Maidenhead v Marlow; Sportsman 15 Nov 1871 + Bell's Life 18 Nov 1871
  Clapham Rovers v Upton Park; Bell's Life 21 Oct 1871 Harrow Chequers). historic.build_fa on the Pioneers DLC
  (Francescomanetti82 & Gorzo) templates; 59 invented names (Reigate Priory 15, Donington School 16, Harrow Chequers 6,
  Maidenhead 5, Marlow 5, Upton Park 4, ...). Positions reconstructed. Kits of Hitchin/Maidenhead/Reigate = Windsor Home Park
  template (unknown). Name 'HAMPSTEAD HEATH.' (16-char limit).
- Builds IT EN FR DE = b204b202 4b683dbe fd171ece 8195ebc1, TEAM.091 abad62ed; previous (Libertadores session) exes in
  c/S26FA_BAK (132c024f ...).
- TO VERIFY: preset TORNEI STORICI -> FA CUP 1871-72: round 1 = the 7 real ties (Barnes-Civil Service, Hitchin-Crystal Palace,
  Maidenhead-Marlow, Upton Park-Clapham Rovers, Queen's Park-Donington, Royal Engineers-Reigate Priory, Wanderers-Harrow
  Chequers), Hampstead not playing; draws replayed; round 2 = 7 winners + Hampstead, random pairs; then SF, final.
- PLAYTEST 26i (Davide): FA Cup first round = the 7 real ties, Hampstead joins round 2 (OK). BUG: legs byte 0 (no e.t., no
  pens) -> endless replays (Maidenhead-Hampstead 30+ replays; the game has REPLAY / 2ND / 3RD REPLAY texts and then repeats).
- Session 26j — coin toss (Davide's choice "C", also for the Mitropa, whose MTK-Sparta tie really ended by coin toss):
  FA legs byte 0x28 (1 match, extra time and 'penalties' only in the replay), Mitropa stays 0xA8. For our contests
  (diyFileBufferCopy[2Dh] = 0xC2 / 0xC3) the shoot-out becomes a coin toss: coin_sim replaces `call cseg_2B84D` in cseg_2AE97
  (simulated: D5/D6 = 7F/7E, random side), coin_play replaces `call StartPenalties` in UpdateTime @@switch_to_penalties
  (played: team1/team2PenaltyGoals = 7F/7E, winningTeamPtr = top/bottomTeamInGame, jmp EndOfGame; the post-match code reads
  the 'penalty goals' because penaltiesState is already -1), coin_text replaces `mov ax, [skip]` before the results
  PrintFormatted in cseg_289AC (pens flag + scores >= 7Eh -> COIN_TEXT, long/short pair as the game's strings; it '%a VINCE
  AL SORTEGGIO', en '%a WIN ON THE TOSS OF A COIN', fr '%a GAGNE AU TIRAGE AU SORT', de '%a GEWINNT DURCH LOSENTSCHEID').
  Random = the game's Rand2 (first call of cseg_27F08). IT sites: sim 0x1B330, StartPenalties 0x5FC1B, text 0x18BA1.
  Builds IT EN FR DE = 85a9a968 69b3e77d 1b06e429 dd66787e (TEAM files unchanged). RELEASE NOTES: explain the coin toss rule.
- PLAYTEST 26j (Davide): FREEZE when clicking VIS. PARTITA (watch) on an FA Cup REPLAY (Maidenhead-Hampstead); simulated
  results OK. Coin hooks are not reached at kick-off -> cause unknown; record bytes checked (all player bytes within the
  originals' ranges; team byte 24 = tactic 10 ATTACK from the DLC templates, valid). Fixed meanwhile: coin_sim now leaves a
  played match's toss alone ([dseg_114C9E] >= 0 -> original cseg_2B84D); Queen's Park shorts grey (colour 0).
  Builds IT EN FR DE = 62a5215f 71ae66ef b32a33b8 1a770f46, TEAM.091 a00c1adf. NEXT: Davide's tests (watch a first-round FA
  match, a WC82/Mitropa match) + DOSBox-X debugger EIP at the freeze.
- Davide: the freeze is VIS. RISULTATI (simulated) on a replay, watching is fine -> likely the 127-126 'penalty score' used as counts. Coin result now 1-0 / 0-1; coin_text = our contest + pens flag (no real shoot-outs exist there). Builds IT EN FR DE = 500b1f1e d6ed7a07 74eff77a 77622a92 (UNTESTED).
- Coin toss debugging (2026-10-02): test build T1 (engine's own penalties, no coin code) crashed too -> not the coin code.
  FREEZE.PRE (Davide's save, c/SWOS) showed replay counter [32Fh] = 4: the engine's 'extra time / penalties IF REPLAY' never
  applied in the preset cup and the 4th replay crashed (DOS/4GW invalid opcode at a garbage EIP, DOSBox-X log 'GRP5 Illegal
  call 7'). The .PRE file = diyFileBufferCopy (round records at the same offsets, little-endian) + DIY_competitionStart at
  file 0x420 (big-endian words).
- NEW coin toss: legs bytes FA 0x00 (1 match), Mitropa 0x80 (2 legs), no e.t./pens; coin_draw replaces `or byte [D7],80h;
  and byte [D7],0FDh` (draw -> replay, cseg_2B52F, IT obj1+0x1B37A, then the original jmp) in cseg_2AE97 for simulated and
  played matches alike: in our contests, if DIY_competitionStart[32Fh] != 0 (already a replay/play-off) -> random winner,
  flags |= 0Ah (decided + 'penalties'), D5/D6 1-0 / 0-1; coin_text shows the toss. coin_sim/coin_play removed.
  Builds IT EN FR DE = d434f928 6fc064a9 a2f9dc8c 7f0adb2f (UNTESTED; FREEZE.PRE is unusable: it carries the old 0x28 rounds).
- ROOT CAUSE of all coin-toss crashes (DOSBox-X debugger, `BP 160:27C37A` + `LOG`; obj1 loads at linear 0x261000): the hooks
  that overwrite instructions holding absolute addresses (coin_text over `mov ax,[skip]`, coin_draw over `or/and byte [D7]`)
  kept the old LE fixups, so the loader rewrote our call displacement (`call 337D9758`). Fixed with p.remove at draw_site+2,
  +9 and text_site+2 (as lib97 does for its calendar hook). The earlier conclusions ('engine e.t./pens if replay crash',
  T1/T3/T5) were all this bug. Kept design: coin_draw on draw->replay, legs FA 0x00 / Mitropa 0x80.
  Builds IT EN FR DE = 94a90a53 19cc3e18 091e31e3 80d288e0 (UNTESTED in game).
- PLAYTEST coin toss (Davide, 2026-10-02): PASSED - simulated FA Cup to the end, final replay Royal Engineers 0-0 Wanderers, 'WANDERERS VINCE AL SORTEGGIO', no crash. Still to check: a played/watched drawn replay, a Mitropa play-off.
- PLAYTEST Mitropa play-off (Davide): Admira Wien 2-2 Napoli in the first-round play-off -> 'NAPOLI VINCE AL SORTEGGIO' (as in 1934 that tie went to a play-off). PASSED. Left: a played/watched drawn replay.
- Short cup names (Playaveli's suggestion: long names overlap on the career main screen/schedule): patch.short_names writes the 2nd name dword (the game's short name, <= 13 chars, e.g. 'C.D. COP EURO') of the SA, CAF, CONCACAF and Asian cups: COPA LIB., SUPERCOPA, COPA CONMEBOL, COPPA INTERC./INTERC. CUP/COUPE INTERC. (de keeps WELTPOKAL), CAF CL, CAF CWC, CAF CUP, CONCACAF CUP, ASIAN CC, ASIAN CWC (strings in the obj2 page; sacups/cafcups expose NAME_SITES). Builds IT EN FR DE = 9a2c4f15 608cc88a 3a3480e2 255e4d60 (UNTESTED: check the career main screen with a Libertadores club). Release notes: credit Playaveli for the suggestion.
- Roles fix (Davide: Kirkpatrick in goal shown as M, the DLC's role): players copied from the DLCs keep the slot's role (facup72 / mitropa34), only skills/face come from the DLC. TEAM.090 / TEAM.091 rebuilt (md5 above in c/SWOS), exes unchanged. Played replay Civil Service 2-4 Barnes OK.

## BACKLOG — ideas from Daniele Bordes (Facebook SWOS group, 2026-10-02; he hex-edits SWOS DOS and SWOS 2020)
- Kit selection: his hack (TEAM.* files + exe) works around the game's bad kit-clash algorithm so that e.g. Milan, Inter and
  Juventus meet each other in their home kits (SWOS 2020 has a kit selector; the DOS game does not). Worth a look for the mod.
- Rudimentary transfer market tool: swap(teamFrom, playerFrom, teamTo, playerTo) updating both the TEAM.* file and the career
  (.CAR) file; plus 'replace/retire' (a player becomes a new name with new values). Interesting as a Python tool here
  (tools/, on top of le/TEAM parsing and the .CAR layout we know: fixed part 95151 B + N cached team records).
- He also changed: Champions League to a pure knock-out (no groups), nations/number of teams per nation in the euro cups,
  Coppa Italia final as a single match. (Our mod already rewrites cup formats; possible exchange of notes / collaboration.)
- PLAYTEST watched drawn replay (Davide, 2026-10-02): FA Cup 2nd round replay Barnes 0-0 Queen's Park watched (VIS. PARTITA):
  no e.t., no shoot-out, teams left the pitch, results screen 'BARNES VINCE AL SORTEGGIO'. PASSED.
- HISTORIC TOURNAMENTS DONE (World Cup 1982, Mitropa Cup 1934, FA Cup 1871-72): all playtests passed. Handed over to the
  Libertadores session for the 2.0 release notes / patcher (release only with Davide's ok). European Cup 1959-60 parked
  (research in session 26e). Debug config dosbox-swos-debug.conf (core=normal, git-ignored) kept for future crashes.

## Release 2.0 (2026-10-02, Davide's ok)
- Contents: Copa Libertadores 1997 1:1 (session 27), classic tourneys World Cup 1982 / Mitropa 1934 / FA Cup 1871-72
  (sessions 26b-26j), short cup names in the career calendar. Builds IT EN FR DE = 9a2c4f15 608cc88a 3a3480e2 255e4d60,
  GOG c547c312 aa3cee26 ebc0a26e 661f698e (c/gog; 1.3 GOG backed up in c/REL13/gog), TEAM.089 47b28c41, TEAM.090 9817384a,
  TEAM.091 bdfbff16. Reproducible from HEAD (scratch rebuild = c/SWOS byte for byte).
- Patcher 2.0 (TEAM.089-091 added, notes): Python round trip asserted for every file, JS applyDelta checked with node
  (IT exe, TEAM.020, TEAM.089-091, IT GOG -> expected md5).
- Docs: manuals IT/EN chapter 20 'Classic tourneys' (limits 21, history 22), golden rule on fixups of overwritten
  addresses, overview + history rows 26-27; README features/install/credits; artifacts republished (EN v10, IT v9).
- Release notes release/notes-2.0.md (EN, IT), announcements in release/announcements/2.0/ (forum EN BBCode, forum IT,
  Facebook IT/EN) to be posted by Davide.

## Session 28 — Australia NSL 1996-97 1:1 for 2.1: feasibility analysis (2026-10-02, Davide's request; no code yet)
Original data (TEAM.044, 51 clubs, division byte = record +25; league struct obj2+0x81D4 in ENGLISH.EXE: id 0x57, country 0x2C,
start 0x10, end 0x50, 4 divisions [12,12,14,12], no promotion/relegation/playoffs; names 1ST DIVISION, SOUTH DIVISION,
NSW DIVISION (short NSW), QUEENSLAND DIVISION (short QUEENSLAND)):
- 1ST DIVISION = the 1995-96 NSL (Adelaide City, Brisbane Strikers, Canberra Cosmos, Marconi, Melbourne Knights, Morwell Falcons,
  Newcastle Breakers, South Melbourne, Sydney United, UTS Olympic, West Adelaide, Wollongong City).
- The 3 lower "divisions" are state leagues (SOUTH mixes Victoria and South Australia, which never had one league); Brunswick United
  has no league. No Oceania club cup in 1996-97 (OFC club championship 1987, then 1999) -> nothing to add there.
Real 1996-97 (en.wikipedia "1996-97 National Soccer League", ozfootball.net archive on the Wayback Machine):
- 14 clubs: + Perth Glory (new), + Collingwood Warriors (Heidelberg United merged into them), Morwell -> GIPPSLAND FALCONS.
  26 rounds, closed league (premiers Sydney United 56 pts). Final table: SU, Brisbane, South Melb., Adelaide C., Marconi,
  Melb. Knights, Perth, West Adelaide, UTS Olympic, Wollongong, Newcastle, Gippsland, Collingwood, Canberra.
- Finals series (top 6, ozfootball Playoff.html): two-leg ties 1v2 (major semi), 3v6, 4v5; Match 1 = winners of 3v6 and 4v5
  (single); Match 2 = loser of 1v2 v winner of Match 1 (single); Match 3 = Grand Final, winner of 1v2 v winner of Match 2.
  1997: Brisbane beat Sydney United on away goals (1-0, 1-2), Grand Final Brisbane 2-0 Sydney United 25/5/97.
- NSL Cup 1996-97 (Sept 1996, before the league): 16 teams, two-leg round of 16 and quarter-finals...: 13 NSL clubs (no Perth) +
  South Australian Select XI, Northern NSW Select XI, Brisbane Lions.
Sources for squads: web.archive.org/web/2005/http://www.ozfootball.net:80/ark/NSL/9697/ Round01..Round26.html, Playoff.html,
NSLCup.html = full line-ups with subs of EVERY match (ozfootball.net itself is now a hijacked spam site, use the Wayback copy);
Wikipedia season pages with squad lists exist for Perth Glory, Collingwood Warriors, Canberra Cosmos, Newcastle Breakers.
Feasibility:
1. NSL to 14 clubs: EASY. Brunswick United (no league) -> Perth Glory, Heidelberg Utd -> Collingwood Warriors moved to div 0,
   Morwell -> Gippsland Falcons; divisions [14,11,14,12] = 51, no new global numbers. Squads of the 14 from the line-ups
   (appearance counts), existing players keep their ratings. Rename 1ST DIVISION -> NSL / NATIONAL SOCCER LEAGUE (Davide:
   "rinominare 1st division in NSL") with a new string (the old one may be shared).
2. Finals series: the league engine has only promotion/relegation playoffs between divisions (Germany-like structs), no title
   playoffs. Needs a career cup whose entrants are NSL places 1-6 (as our cups taken from tables) + custom code for the
   double chance (loser of 1v2 continues, winner of 1v2 waits for the Grand Final): MEDIUM-HARD, like lib97. To ask Davide
   before approximating.
3. NSL Cup 1996-97: optional, needs 2 select XIs (+ Brisbane Lions exists) and a cup before the league.
4. Season dates start 0x10 / end 0x50: check vs Oct-May.

## Session 28b — NSL 1996-97: clubs and squads (2026-10-02, Davide: 2.1, finals AND NSL Cup yes; build T1 UNTESTED in game)
- tools/nsl_lineups.py: parses the 26 rounds + finals + NSL Cup line-ups (internal/nsl9697, Wayback copies of ozfootball.net,
  git-ignored): 410 line-ups, nested/unclosed substitutions handled, one source typo fixed (Mitroulas).
- tools/nsl97.py build(): TEAM.044 in place (same 51 records and global numbers 984..1034): Brunswick United (no league) ->
  PERTH GLORY (purple), Heidelberg Utd -> COLLINGWOOD WAR. (black-white stripes, Heidelberg merged into them in 1996), Morwell ->
  GIPPSLAND FALCON, typos fixed (BRIS. STRIKERS, MARCONI-FAIRFLD); coaches 1996-97 (Nyskohus, Farina, Lyons, Matic, Arok, Kosmina,
  Marocchi, Postecoglou, Culina; others kept). Squads: 16 most-used players (starts + sub appearances), a mid-season mover goes
  to the club he played most for; 128 players reuse their SWOS record (skills, nationality; name = the line-ups' spelling),
  94 new ones take the slot's skills; roles from the line-up place when >= 3 starts, else SWOS. Two backup keepers missing
  (Gippsland, South Melbourne): the 1995-96 SWOS keeper stays. 9 NSL players also remain in their 1995-96 state club (no data
  for the state leagues; the original file already had 26 repeated names).
- nsl97.patch(): Australia league struct (obj2, sig 57 00 2C 10 50 21 ...) divisions [14, 11, 14, 12], division 1 long and short
  name 'NSL'. No free global numbers after 1034 (TEAM.045 starts at 1035) and no 52-number free run anywhere -> no 52nd club:
  the SOUTH division has 11 clubs = FIRST ODD-SIZED CAREER LEAGUE (original data has none; DIY leagues accept odd sizes). MUST be
  playtested; fallback: Heidelberg stays in SOUTH and Collingwood replaces another club, or South drops to 10 + 1 unattached.
- Build T1 installed in c/SWOS: ITALIAN.EXE ceb667a7, DATA/TEAM.044 f73b75ad (2.0 kept as ITALIAN_S20.EXE 9a2c4f15, original
  TEAM.044 in c/SAVES_BACKUP/TEAM044_ORIG.BIN). Other files identical to 2.0.
- Finals series: NATIVE mechanism found. cseg_8DAC3 (end of InitializeNewSeason): for the player's division, the playoffData byte
  (div entry +5, struct +12h) is a relative offset from that byte to 2 dwords: contest struct pointer (built as slot 4 by
  cseg_8B2D3 D0=4) and a list pointer stored in D8CC0. cseg_8ECAE (league end): list = count x (league ptr, division, position)
  dwords; cseg_8EF2C takes standings[A1+1ADh + 2*position] -> team list -> cseg_32E15 + scheduling. So 'NSL places 1..6' is a
  plain play-off definition. Missing: the double chance (loser of 1v2 goes to the preliminary final, winner of 1v2 waits for the
  Grand Final) -> custom per-round team lists, like lib97's lib_pre insertion; fixed pairings via hist_draw DRAWS.
  Only for a career in the NSL (play-offs are built only for the player's division).
- NSL Cup 1996-97: needs 2 select XIs (South Australia, Northern NSW) = new team records, but no free global numbers in
  Australia's range -> a separate team file (like the historic ones) or a reused range; to study.

## Session 28c — New Zealand check (2026-10-02, Davide: "controlla la Nuova Zelanda"; analysis only)
- SWOS: TEAM.062, 30 clubs, league struct obj2+0x82FC (EN) id 61h country 3Eh, 3 divisions of 10 (NORTHERN/CENTRAL/SOUTHERN
  REGION), no promotion/relegation.
- Real 1996-97 (en.wikipedia "1996-97 National Summer Soccer League", Nov 1996 - Apr 1997): 10 invited clubs, home and away
  (18 games), 4 pts win / 1 draw + 1 bonus to the shoot-out winner after every draw; top-4 play-offs: 1v2 (winner to the final),
  3v4, loser 1v2 v winner 3v4, final (Waitakere City 3-1 Napier City, 6/4/97). Table: Napier, Central Utd, Waitakere, North Shore,
  Miramar, Nelson Suburbs, Melville Utd (SWOS: WAIKATO UNITED), Wellington Utd, Woolston WMC, Mount Maunganui (SWOS typo
  MOUNT MANGANUI). All 10 are in TEAM.062. Winter regional leagues still existed (with the NSSL clubs in them too).
- Exact: 10-club national division, 4 pts per win (header byte), top-4 double-chance play-offs (same mechanism as the NSL).
  NOT exact: shoot-out bonus point (leagues have no shoot-outs) -> ask. No 1996-97 squad source found (RSSSF pages gone,
  ultimatenzsoccer.com covers women's football) -> keep SWOS 1995-96 squads. Remaining 20 clubs (N 5, C 6, S 9): options asked
  (2 island divisions 11+9, 3 regions 5/6/9, one division of 20).

## Session 28d — NZ: feasibility of the shoot-out bonus point + regional clubs (2026-10-02, analysis only)
Shoot-out after league draws (+1 point to the winner), what the code offers (ref/swos.asm):
- Played match: UpdateTime at full time on a draw goes to StartPenalties when penaltiesState != 0 (no extra time needed:
  extraTimeState 0). penaltiesState is set per match by the match setup (cseg_29E79: DIY/cup rounds set it from the round's
  penalties flag; 0 otherwise). StartPenalties saves the 90' goals (savedTeam1/2Goals) and the setup keeps statsTeamXGoalsCopy ->
  the league result can stay the 90' score. Needs: a hook at the CAREER league match setup (not yet located) to set
  penaltiesState = 1 for NZ division 0, and to read team1/2PenaltyGoals afterwards.
- Simulated matches (CPU v CPU, results-only): cup results come from cseg_2AE97 (our coin_draw site); the career league
  simulation path is still to locate; a random shoot-out winner (Rand2) like coin_flip.
- Bonus point: the league table update routine (where League.pointsForWin is added) is still to locate; +1 to the shoot-out
  winner there. Leagues of other countries while the player is elsewhere: simulation path unknown (may not get the bonus).
Verdict: probably feasible, 2-3 sessions + playtests, risk like the coin toss (hooks in match/result code).
Regional clubs: no free global numbers after NZ (1248..1277, TEAM.064 from 1278). The only free 40-number run is 1960..1999
(someLeaguesTable size 2000; 1810..1849 holds S3/saved lists) -> NZ could MOVE its base there and get 10 more clubs
(10 NSSL + 3 regions x 10). Costs: 2.0 careers involving NZ clubs see different teams; 10 more clubs need real 1996 regional
league names (squads would be invented). Island split 11 (North) + 9 (South) is forced by geography (Central non-NSSL clubs
are all North Island).

## Session 28e — Australia without sacrificing clubs (2026-10-02, Davide: "trovare un modo per non sacrificare squadre australiane")
- Global number = teamsCountryNumbers[record byte 0] + byte 1, recomputed by SetTeamGlobalNumbers at every LoadTeamFile; cup
  lists use (file, ordinal) pairs; our tools store no global numbers -> a country's base can move. Bolivia (TEAM.045, 14 clubs,
  1035..1048) -> 1960..1973 (free run 1960..1999, someLeaguesTable < 2000): Australia may use 984..1048.
- TEAM.044 now 52 clubs: PERTH GLORY = new record 51 (global 1035, built on Brunswick's record), Brunswick United (no league in
  SWOS) -> SOUTH in place of Heidelberg (Collingwood). Divisions [14, 12, 14, 12]: no odd league any more.
- nsl97.BASE_MOVES = {45: 1960} (exe) + write_new_teams uses it and checks Australia's numbers.
- Build T2 installed: ITALIAN.EXE + DATA/TEAM.044 (md5 below in git log). Caveat: a 2.0 career saved with Bolivian clubs cached
  may hold their old global numbers until the team file is reloaded -> recommend new careers for 2.1.
- Room left for the NSL Cup select XIs (records 52, 53 -> 1036, 1037) and NZ ideas: 1974..1999 (26) still free.

## Session 28f — NZ shoot-out bonus: the three routines FOUND (2026-10-02, Davide: "sì", analysis only, no code)
1. Career league match setup = cseg_89381 (called 3x by cseg_88A12): sets `mov penaltiesState, 0` (ref line ~123620) before
   InitializeInGameTeamsAndStartGame, then copies statsTeam1/2GoalsCopy to dseg_114C96/98 (the 90' result). Hook: penaltiesState
   = 1 when DIY_competitionStart is NZ division 0 (remove the fixup of the overwritten instruction!). UpdateTime then plays the
   shoot-out at full time on a draw (no extra time: extraTimeState stays 0); team1/2PenaltyGoals hold it. To verify in game:
   the copy variables keep the 90' score (StartPenalties zeroes statsTeamXGoals, saves savedTeamXGoals).
2. League matchday = cseg_88A12 (career): result in D1/D2 (played: stored goals; else simulated), table entries A3 (home),
   A4 (away) in DIY_competitionStart's team table: +2B9h won, +2BBh drawn, +2BDh lost, +2BFh GF, +2C1h GA, +2C3h POINTS,
   [DIY+61h] = points for a win, [DIY+1BDh] matches played counter. Draw branch cseg_88D6A adds 1 point to both.
   Hook there: after the draw points, if NZ division 0 -> shoot-out winner (played: penalty goals; simulated: Rand2) +1 point.
3. Simulated matches: cseg_88A12 gets D1/D2 for every fixture of the player's division (CPU v CPU too) -> the same hook covers
   them (random winner). The cup result routine cseg_2AE97 (penalties via round flag [A5+7Dh], cseg_2B84D) is not used by
   career leagues. Still unknown: leagues of OTHER countries while the player is elsewhere (probably not simulated per match).
Verdict: FEASIBLE for a career in NZ (all 3 hook points located, small code: 2 hooks + ~40 bytes). ~1-2 sessions + playtests.
Open: which team is team1 for the penalty goals (top/bottom swap), result screen shows only 1-1 (no "pens" note).

## Session 28g — NZ regional leagues 1996 (2026-10-02, Davide: NSSL ok, "stesso trucco della Bolivia")
Sources: ultimatenzsoccer.com NZClubSoccer (Jeremy Ruane), Wayback copies in internal/nz9697 (git-ignored): id271 NSSL 1996-97
(all results, '*' = decided on penalties, BP column), id327/328 Northern League 1996/1997, id377/378 Central League 1996/1997,
id295/296 Southern League 1996/1997.
- 1996 Northern League top div (12): Lynn-Avon Utd (champ), Blockhouse Bay, Fencibles Utd, Ngaruawahia Utd, Papakura City, Oratia
  Utd, Northland Utd, Eden, Cambridge, Hamilton Wanderers, Takapuna, Mt Albert-Ponsonby. (NSSL clubs played lower divs.)
- 1996 Central League Premier (12): Western Suburbs (champ), North Wellington, Gisborne City, Tararua Utd, Seatoun, Waterside
  Karori, Napier City*, Island Bay Utd, Raumati Hearts, New Plymouth City, Wellington Utd*, Stokes Valley (* = NSSL).
- 1996 Southern League: Div One North (Canterbury, 10: Northern Hearts champ, Canterbury Univ., Western, Kaiapoi, Avon Utd,
  Cashmere W., Burnside, Timaru City, Parklands, Ashburton) and Div One South (Otago, 10: Mosgiel champ, Roslyn Wakari,
  Dunedin Technical, Caversham, Green Island, Waihopai, Otago Univ., Northern, Invercargill Thistle, Queens Park).
- NUMBER SPACE: Bolivia already uses 1960..1973 -> NZ (40) does not fit in 1974..1999. Plan: NZ -> 1960..1999, Bolivia -> 1248..1261
  (NZ's old range). Australia 984..1048 unchanged. Free after that: 1262..1277.
- Proposal to Davide: NSSL 10 + NORTHERN/CENTRAL/SOUTHERN 10 each = the 20 SWOS regional clubs (all kept) + 10 real 1996 clubs:
  North +5 (Lynn-Avon, Blockhouse Bay, Fencibles, Ngaruawahia, Papakura City), Central +4 (Western Suburbs, North Wellington,
  Gisborne City, Tararua Utd), South +1 (Mosgiel or Northern Hearts). New clubs' squads would be invented (no source).
- 28g DONE (build T3, untested in game): tools/nz97.py: TEAM.062 = 40 clubs (30 SWOS in place + 10 new, invented squads/coaches,
  template = a SWOS club of the same region), divisions NSSL/NORTH/CENTRAL/SOUTH x 10; renames MT. MAUNGANUI, NAPIER CITY ROV.,
  MELVILLE UNITED. exe: new 4-division struct in the new obj2 page (4 points a win, div 1 'NAT. SUMMER LEAGUE'/'NSSL', regions
  keep their names), the single pointer to the old struct retargeted (scan of all fixup records, added ones included).
  BASE_MOVES = {Bolivia 45: 1035 -> 1248, NZ 62: 1248 -> 1960}. Original TEAM.062 in c/SAVES_BACKUP/TEAM062_ORIG.BIN.

## Session 28h — NSSL shoot-out bonus point: code (2026-10-02, build T4, static checks OK, UNTESTED in game)
- nz97.shootout(): nz_setup replaces `mov word [penaltiesState],0` in cseg_89381 (IT obj1+0x79490): 0, then 1 if both teams
  are NSSL clubs (record byte 0 = 62, ordinal in NSSL_MASK); clears team1/2PenaltyGoals. nz_draw replaces the last
  `mov esi,[A4]; add word [esi+2C3h],1` of the draw branch in cseg_88A12 (IT obj1+0x78BE8): if both NSSL, +1 point to the
  shoot-out winner (penalty goals if a shoot-out was played, home = team 1; else Rand bit 0), then clears the penalty goals.
  Fixups of both overwritten instructions removed; ndisasm of sites and cave OK. Code at obj1+0xA295C (222 B).
- TO TEST: a played NSSL draw -> shoot-out at 90' (no extra time), table: winner +2, loser +1, result stays the draw; the
  right team gets the point (team 1 = home?). Simulated NSSL draws: points = 4W + D + bonus (one bonus per draw).

## QUEUE 2.1 — USA (MLS) (Davide 2026-10-02: "metti in coda usa")
SWOS TEAM.073: MLS 1996, the 10 real clubs (div 0, struct obj2+0x83F6 EN: id 69h country 49h, 1 division, 2 games per pair,
3 pts) + 8 A-League clubs without a league (div 4). Real MLS 1996/1997: no draws, 35-yard shoot-out: winner 1 pt, loser 0
(win 3); 32 games (unbalanced: conference rivals more often), East/West conferences, play-offs best-of-3, MLS Cup.
Points: exact with a variant of the NSSL hook (draw: only the shoot-out winner +1). 35-yard shoot-out -> penalties
(approximation, ask). Calendar/conferences/best-of-3: to study. Which season (1996 or 1997) and squads: to check.

## Session 28i — NSSL shoot-out shown in the results list (2026-10-02, Davide: "fai terzo innesto"; build T6, static OK)
- T5 PLAYTEST (Davide): played 0-0 Waitakere - Wellington: shoot-out at 90' (no extra time), result stays 0-0, Waitakere
  2 -> 4 points, Wellington 5 -> 6: the bonus works. (T4 gave 1 point each: nz_draw checked A3/A4, fixed to A1/A2.)
- nz_mark replaces the last store of cseg_2A71E (mov ax,[D6]; mov esi,[A1]; mov [esi+14h],ax; IT obj1+0x1A89C): for an NSSL
  draw it sets the game-list entry flags |= 8Ah (+1 away win) and D6 = shoot-out score (played: real; simulated: winner by lot,
  4-2/4-3/5-3/5-4), so the list prints "%a WIN %0-%1 ON PENS"; the manager's statistics (counted before, in the same routine)
  still see a draw. NZ_WIN hands the winner to nz_draw (table point) so both agree. Team ids in the entry: +0Ch/+0Eh words
  (low byte file, high byte ordinal). Rand clobbers esi (reloaded) and D0 (saved).
- obj1 grows by a THIRD page (OBJ1_NEW_VSIZE 0xA4000, NZ_CAVE = 0xA3000 for 2.1 code); obj2 base 0xC0000 still above.

## Session 28j — finals series (NSL top 6, NSSL top 4): native play-off mechanism studied (2026-10-02, analysis only)
- T6 PLAYTEST (Davide): NSSL draw Waitakere - Mt. Maunganui: career game list shows "MT. MAUNGANUI WIN x-y ON PENS",
  table +2/+1 correct. The league-table screen's results list shows only 0-0 (it never prints extra lines, cups neither):
  accepted, to mention in the release notes.
- Division play-off data (div entry +5 = relative offset to [contest ptr, team-list ptr, delta table...]):
  * candidates: after every matchday cseg_88A12 fills DIY+1ADh (8 words max) with [55h] = promotion-play-off teams from
    standings position [53h] (= promoted directly) and [59h] = relegation-play-off teams above the direct relegations
    (DIY+6Dh = sorted standings, DIY+31h teams, 53h/55h/57h/59h = div entry bytes 1..4). So "0 promoted, 6 to the promotion
    play-off" in the NSL entry = places 1..6 (4 for the NSSL).
  * list entries (league ptr, division, k) take DIY+1ADh[k] (cseg_8ECAE/8EF2C) -> slot 4 contest, played after the league
    ONLY for the player's division; other divisions' play-offs are simulated at season end (cseg_9228D -> cseg_916C2).
  * results: cseg_925C9 reads the play-off's final standings (DIY+2CDh) and a signed delta byte per place (+ relegate,
    - promote) applied to leaguesTableCopy -> all-zero deltas = nobody moves (what the NSL/NSSL need).
  * BUT the native play-off is a MINI-LEAGUE: cseg_8B2D3 builds slot 4 only from a type-1 (league) contest
    (`cmp byte [A0+1],1; jnz skip`), and cseg_925C9 reads league standings. Original examples: country 25 (0x37: div 0
    2 relegation-play-off teams + div 1 2 promotion-play-off teams, 4-team league, 4 games each), 0x4D, 0x67.
- Consequence: the real finals (two-leg ties, single matches, double chance, Grand Final) need a KNOCKOUT in slot 4:
  allow a type-2 contest there (session 13 already ran a cup in slot 4: the Intercontinental), fixed pairings via
  hist_draw, and custom code for the double chance (loser of 1v2 into the preliminary final, winner of 1v2 into the Grand
  Final), plus the season-end path (cseg_925C9 must not read cup data as standings; deltas zero anyway). Big: 2-4 sessions.

## Session 28k — NSL Cup 1996-97 (2026-10-02, Davide: plan B = finish/test the rest, play-offs last; build T7, static only)
- SWOS already has an Australian cup (id ADh, obj2 struct, 32 clubs drawn from the file: list offset byte [7] = 0).
  A type-1 cup with [7] != 0 takes the team list at +7+[7], count [0Ah] (cseg_32024, as the euro cups).
- nsl97.cup(): copy of the header, 16 clubs, rounds 94h (two legs, extra time, penalties), 54h, 54h, 14h (final), fixed list in
  bracket order (real ties, home side of the first leg first), new struct in the obj2 page, Australia's table retargeted.
  hist_draw DRAWS for ADh: 16 and 8 identity, SF [1,0,2,3] (South Melbourne at home v Collingwood), final identity.
  Real: R16 AC-WA, SA Reds-Collingwood (sudden death e.t.), SM-Gippsland, Canberra-Knights, Wollongong-Marconi,
  NNSW-Newcastle, Brisbane Lions-Strikers (sudden death e.t.), Sydney U.-UTS; QF CW-AC 0-0 (CW 3-1 pens), SM-MK 1-0, MF-NB 3-1,
  BS-UO; SF SM 1-3 CW, MF 5-0 BS; FINAL Collingwood 1-0 Marconi (6/10/96, Lakeside).
- TEAM.044 = 54 records: 52 league + SOUTH AUS. REDS (52, global 1036) and NTH NSW LIONS (53, 1037), no league (div 4);
  squads = their only line-up (surnames) + invented names to 16. Brisbane Lions keep their SWOS squad.
- NOT exact: golden goal ("sudden death extra time") -> normal 30' extra time (ask Davide). Cup name: SWOS default (check).
- T7 PLAYTEST (Davide): Australian cup shown as the default national cup name ("Australia coppa"), 16 clubs, real round of 16,
  two legs: OK. Golden goal -> normal extra time ACCEPTED by Davide (release notes). Open: rename to "NSL CUP"?
  Still to see: the cup played to the final along the fixed bracket.
- T8: cup named 'NSL CUP' (Davide's choice; long = short) and FIXED a T7 bug: the rounds list had no 0 terminator (the team
  list followed directly: after the final the engine could have read it as more rounds). Layout now as
  sacups.knockout16: header, rounds, 0, two name dwords, list ([5] = 0Eh, [7] = 14h).
- T8 PLAYTEST (Davide): NSLCUP.CAR: round of 16 = the real ties in bracket order (decoded from the save), cup played to the
  final without freezes, next season starts. NSL Cup DONE.
- CORRECTION to 28j: the native play-off contest is a TYPE-1 CUP (knockout: country 25's is 4 clubs, rounds 94h 94h, list
  offset [7] = 11h), not a mini-league; type 0 = league, 1 = cup. So slot 4 natively plays a knockout: only the double chance
  needs custom code (per-round team lists, like lib97's insertion).

## Play-off definition layout (decoded 2026-10-02, originals of countries 25, 35, 71)
div entry +5 (playoffData) = offset from that byte to: [contest ptr][list ptr][n words: candidate index of contest slot k
(simulated path: index into the season's candidate list dseg_1807A2, filled per division by cseg_9221F from DIY+1ADh)]
[n x n delta bytes (signed, leaguesTableCopy moves; 0 = stay)]. list (player's path, cseg_8ECAE) = n x (league ptr dword,
division dword, k dword) -> DIY+1ADh[k] of that division. Contest = type-1 cup, [0Ah] = n, [7] = 11h (list), rounds, names.
4-club example: index words 0,3,1,2; deltas 00 FF 00 FF 00 FF 00 FF 01 00 01 00 01 00 01 00.
Round descriptors in the DIY buffer: stride 76h from DIY_competitionStart: +161h clubs in the round, +15Dh, +15Fh (0 =
random draw), +163h, +16Bh, +16Dh legs, +16Fh extra time, +171h penalties (set by cseg_24DFA from the rounds bytes).
Winners of a round fill DIY+59h[0..] in tie order (Libertadores/FA hooks rely on it).

## QUEUE — Argentina (Davide's question, 2026-10-02)
SWOS: TEAM.043 40 clubs, Primera 20 (2 down) + Nacional B 20 (2 up), one double round-robin table. Real 1996-97: Apertura 1996
and Clausura 1997 (19 rounds each, two champions, River Plate both), relegation by 3-season average ("promedio"); Nacional B
own format (champion + "reducido" play-off). Same 38 fixtures; different titles/relegation -> separate project, after USA.

## Session 28l — finals series code (2026-10-02, build T9, static checks OK, UNTESTED in game)
- Type-1 cups (cseg_87DA0) derive the rounds by halving [0Ah] (6 clubs -> 2 rounds): unusable for 6-2-2-2. Type-2 cups
  (worldCup layout, historic.py) declare every stage: finals97 contests C4h 'NSL FINALS' (stages 6,2,2,2; legs 94h,14h,14h,
  14h; [0Ah] = 6 = slot-4 placeholders and away goals on) and C5h 'NSSL PLAY-OFFS' (4,2,2; 14h x3).
- slot4_type: in cseg_8B2D3 the slot-4 test `cmp byte [esi+1],1; jnz skip` -> `cmp byte [esi+1],0; jz skip` (IT obj1+0x7B245
  +9/+11; slot-3 block before it untouched).
- League structs NSL and NSSL relocated into the new obj2 page with the play-off block (div 0: 0 promoted, n to the
  "promotion play-off", playoffData 52), block = [contest][list][order words][n*n zero deltas]; list = (league, 0, k) in tie
  order NSL [0,1,2,5,3,4], NSSL [0,1,2,3].
- fin_pre (obj1+0xA3400, FIN_CAVE) called first by lib97.lib_pre (hist_draw, DRAWS (C4,6),(C4,2),(C5,4),(C5,2) identity):
  round 1 keeps the 1v2 pair in list[20..21], round counter list[24]; later rounds rebuild list[0..1]: NSL R2 W3v6-W4v5,
  R3 L1v2-W(R2), R4 W1v2-W(R3); NSSL R2 L1v2-W3v4, R3 W1v2-W(R2).
- TO TEST: career with an NSL club that finishes top 6 (e.g. Sydney United, results only to the end): NSL FINALS appear after
  round 26 with 1v2, 3v6, 4v5 two legs; then the double chance; no freeze at season end; nobody changes division.
  Same with an NSSL club (top 4). Unknowns: winners order after a 6-club stage, draw call for 2-club stages, season end.

## Session 28m — T9 FREEZE explained; finals series postponed? (2026-10-02)
- T9 PLAYTEST (Davide): freeze as soon as an Australian club is chosen in career. Restored T8 as ITALIAN.EXE (rebuilt from
  f2566ef: md5 e31e0a0d, identical); T9 kept as c/SWOS/ITALIAN_T9.EXE.
- CAUSE: cseg_8B7EA copies the built contest into its slot buffer with a size by type: league 733h, type-1 cup 443h,
  type-2 cup B52h (from diyFileBufferCopy). Slot 4 (dseg_D9C9F) is a 443h buffer (slot4 = slot2 + 443h): a type-2 contest
  overflows it. Type-2 finals in slot 4 = impossible without moving buffers. (cseg_883B8 dispatches: type 0 cseg_8F1F2,
  1 cseg_87DA0, 2 cseg_24DFA.)
- Remaining way: type-1 cup (cseg_87DA0: rounds from halving [31h]) + custom code for entrants/counts per round. Proposed to
  Davide: postpone to the end of 2.1.
- Argentina analysis (see QUEUE): 20 Primera clubs of SWOS = the real 1996-97 ones (Huracan Corrientes, Union promoted);
  Apertura/Clausura = mid-season title + table reset (custom hook after round 19, Apertura title has no place in the season
  record); promedio relegation needs 1994-95/1995-96 points (RSSSF) + per-season storage in the .CAR trailer + a season-end
  hook (relegated 1997: Banfield, Huracan Corrientes); Nacional B real 32 clubs/zones/reducido not replicable with 20;
  SA cup qualifiers read the table (choose which). 3-5 sessions.

## Session 28n — USA (MLS) feasibility (2026-10-02, analysis only)
Real (en.wikipedia 1996/1997 MLS seasons): 10 clubs, 2 conferences of 5; 32 games (conference rivals x4 = 16, other
conference x3 = 15, + 1 more v a designated club); regulation win 3, shoot-out win 1, any loss 0 (35-yard shoot-out);
top 4 per conference -> conference semis and finals best-of-three, MLS Cup single (DC United 1996 and 1997).
SWOS: TEAM.073 the 10 real clubs (1996 names), one 10-club league, 2 games per pair, 3/1 points; 8 A-League clubs no league.
Mod: USA ranks 1-4 feed our CONCACAF Champions' Cup (cafcups).
Feasible: exact points (variant of nz97 hooks: draw = 0 each, +1 to the shoot-out winner; ON PENS line); custom 32-round
calendar like lib97.lib_cal (needs the real fixture list) or uniform 3x/4x (27/36 games) approximation. Not native: two
conference tables, best-of-three play-offs (with the NSL finals). Approximation: 35-yard shoot-out -> penalties.
Questions to Davide: season 1996 or 1997, penalties OK, calendar (real / uniform / keep), conferences + play-offs later.

## Session 28o — MLS 1997 (2026-10-02, Davide: 1997, penalties, uniform calendar (4 games per pair), one table; build T10)
- Sources: Transfermarkt squad statistics MLS 1997 (saison_id 1996) for the 10 clubs (internal/mls97/*.apps.html,
  tools/mls_tm.py: name, position, nationality, appearances); en.wikipedia 1997 MLS season (format, head coaches).
  SWOS 2020 teamdbs checked: "1997_98 - Team Updates" = SWOS's 1996 MLS unchanged; "1997_98 - Revised" = MLS 1998 (Chicago,
  Miami): not usable. FBref = Cloudflare check (not bypassed).
- tools/mls97.py: TEAM.073 MLS records in place (names COLUMBUS CREW, KANSAS CITY WIZ., D.C. UNITED; 1997 coaches Fitzgerald,
  Myernick, Dir, Newman, Zambrano, Rongen, Parreira, Quinn, Kowalski, Arena); 16 most-used players per club, movers to the
  club with most apps, roles from Transfermarkt, SWOS record reused when the player exists (skills), nationality from the
  game's code table (obj2 'ALBAUTBEL...' 153 codes, USA = 58). exe: MLS struct games per pair 2 -> 4 (36 games).
- nz97 shoot-out code generalised: kind_of/pair_kind (NSSL = file 62 + NSSL_MASK, MLS = file 73 + MLS_MASK 0x2566D);
  MLS draw: the engine's +1 each is taken back, +1 to the shoot-out winner (3/1/0). Same ON PENS line. Code 532 B.
- Build T10 installed (contains the inert finals code: FINALS = False, fin_pre never matches). Original TEAM.073 in
  c/SAVES_BACKUP/TEAM073_ORIG.BIN.
- T10 PLAYTEST (Davide, 2026-10-02): ALL PASSED (MLS career: names, squads, 10-club table, played draw -> penalties 1/0 +
  ON PENS, wins 3; NSSL regression from WAITAKER.CAR; Australian career starts). MLS 1997 DONE.

## Session 28p — Argentina 1996-97: decisions (Davide, 2026-10-02)
- Apertura and Clausura are TWO tournaments: after round 19 record the Apertura champion and reset the table (rounds 20-38 =
  Clausura; the engine's season champion = Clausura). Apertura champion: message + into the season history if possible.
- Relegation by "promedio" exactly (1994-95 and 1995-96 points from RSSSF + every career season stored in the save).
- Nacional B unchanged (20 clubs, top 2 up): declared approximation.
- SA cup qualifiers from the aggregate Apertura + Clausura table.
- Promedio source: es.wikipedia "Campeonato de Primera Division 1996-97 (Argentina)", "Tabla de descenso" (2 points per win
  for the averages, every season): points 1994-95 / 1995-96 / 1996-97, total, matches (114 = 3 x 38). Colon, Estudiantes:
  from 1995-96 (76); Union, Huracan Corrientes: 1996-97 only (38). Bottom: Hur. Corrientes 0.842, Banfield 0.728 (relegated).
  RSSSF arg95/96/97 (internal/arg9697): Apertura/Clausura tables (Apertura 1996 River 46, Clausura 1997 River 41).
- Engine facts (Argentina design, 28p):
  * League DIY counters (cseg_8922B, per match): [5Bh] matches played in the matchday, [4Fh] matches per matchday, [1CBh]
    matchday within the cycle, [6Bh] matchdays left in the cycle, [69h] matchdays per cycle (19), [5Fh] cycles left
    (playEach = 2 -> 2). At the end of cycle 1 [5Fh] 2 -> 1 and [6Bh] reloads: = end of the Apertura. At the season end
    [5Fh] = 0. Table entries (A3/A4 of cseg_88A12): +2B7h played, +2B9h won, +2BBh drawn, +2BDh lost, +2BFh GF, +2C1h GA,
    +2C3h points; DIY+6Dh = sorted standings (cseg_883DD sorts after every match).
  * SeasonInformations (0x6A per season, the MANAGER's club): trophyFlags (4 trophy icons, entries 17-20),
    leagueStringOffset, strOffset1, strOffset2, field_22 (competition lines), finalPosition... -> "Apertura in the history"
    can only mean the manager's own club record (a competition line and/or a trophy when he wins it).
- PLAN (3-5 sessions):
  1. hook after the sort in cseg_88A12: Argentina Primera (league id 56h, file 43 div 0) and [5Fh] == 1 and every club has
     played 19 -> store each club's Apertura W/D/L/GF/GA/Pts (aggregate), Apertura champion = DIY+6Dh[0], message, history,
     zero +2B7h..+2C3h of the 20 entries.
  2. .CAR trailer C7: Apertura champion + aggregate of the running season + per club (2-point points, games) of the last
     2 Primera seasons (initialised from the es.wikipedia table for a new career).
  3. season end: before cseg_93FD8 (relegation) put the 2 worst promedios last in DIY+6Dh (Argentina div 0 only); SA cup
     qualifiers (sacups season-end code) read the aggregate order.
  4. message / history display: to research.
- Davide (2026-10-02): "non era meglio considerarle come due manifestazioni diverse?" -> not possible as two leagues (one
  league per division; slots 1-3/4 take cups only, 443h buffers < league 733h; a club can't be in two leagues). Agreed
  presentation: division 0 named 'TORNEO APERTURA' at season start; at the Apertura end the DIY name pointer (DIY+27h) and
  the manager's season leagueStringOffset switch to 'TORNEO CLAUSURA'; the Apertura stays in the manager's history as its
  own line (position) + trophy if won. Step 1 now.
- 28p step 1 (build T11, static OK, UNTESTED): tools/arg97.py: Argentine struct relocated with names (div 0 TORNEO APERTURA /
  APERTURA, div 1 NACIONAL B); arg_after replaces the `call cseg_883DD` (sort) that follows nz97's draw site in cseg_88A12
  (IT obj1+0x78CAB) -> sort, then if DIY id 56h and home team file 43 division 0 and [5Fh] == 1 and every club played n-1:
  APERTURA_CHAMP = top team word, zero +2B7h..+2C3h of all entries, DIY+27h (name ptr) = 'TORNEO CLAUSURA'. Code at
  ARG_CAVE obj1+0xA3500 (156 B).
- T11 PLAYTEST (Davide): at round 22 still TORNEO APERTURA, table not reset. Cause: the sort hook ran only after the player's
  match (cseg_88A12); the other matches of the division go through cseg_8B8D9, so "all played 19" was never true there.
- T12: arg_round replaces `mov dword [A0], offset DIY` at the start of cseg_8922B (per-match counters, called by cseg_88A12
  AND cseg_8B8D9; IT obj1+0x7907F, fixups +2/+6 removed): at the first match of the second cycle ([5Fh] 1, [5Bh] 0, [1CBh]
  0, top club file 43 division 0, all played n-1) -> Apertura champion, reset, TORNEO CLAUSURA. The final Apertura table
  stays visible until round 20 starts.
- T12 PLAYTEST (Davide): table resets at round 20 OK; names still TORNEO APERTURA: the game shows the TEXT built at season
  start into DIY+4..+26h (StringCopy in cseg_8F1F2: optional country + division name), not the DIY+27h pointer.
- T13: arg_round also replaces 'APERTURA' with 'CLAUSURA' (same length) in DIY+4..; the next season's build restores it.
- Davide: the management record still says TORNEO APERTURA (position 1, still playing): InitializeNewSeason stores
  leagueStringOffset (+16h of the 6Ah SeasonInformations, via GetCurrentSeasonPointer, IT obj1+0x2915F) at season start.
- T14: at the switch arg_round also calls GetCurrentSeasonPointer (A0/D0 saved) and, if the season's leagueStringOffset is
  TORNEO APERTURA's, sets it to TORNEO CLAUSURA's. Still to do: an Apertura line (final position) in the record.
- T14 PLAYTEST (Davide): record shows TORNEO CLAUSURA (position 1) + two UNNAMED lines (River: Supercopa "out in phase 1",
  Intercontinental "finalist": pre-existing, our SA cups write no name into the record, to fix later) + Copa Libertadores;
  table title TORNEO CLAUSURA; but the career screen with the fixture list still says APERTURA: CareerGameListCommon reads
  the competition's SHORT name from the struct ([struct+5+[5]] + division*8 + 4).
- T15: arg_names keeps the struct's division-0 name dwords (long, short) in step with the phase (Clausura when [5Fh] == 0,
  or [5Fh] == 1 and the table was reset); called after every Primera match (arg_round), at the start of every season
  (arg_season replaces the `call GetCurrentSeasonPointer` in InitializeNewSeason, IT obj1+0x7D16E: DIY+27h and text back
  to APERTURA) and after loading a career (arg_load wraps trailer's load_trailer at the LoadCareerFile call, IT
  obj1+0x23000). The Primera is recognised by DIY+27h = its APERTURA/CLAUSURA long-name string.
- LESSON: p.le.obj_bytes() returns the ORIGINAL bytes; to read an instruction another module already patched use p.get()
  (first T15 build wrapped ProcessCareerFile directly and would have skipped the .CAR trailer).
- T15 PLAYTEST (Davide, CLAUS.CAR): season 2 first matchday showed CLAUSURA, after a match APERTURA; record confused.
  Decoded CLAUS.CAR: both season records leagueStringOffset = CLAUSURA, league DIY text 'ARGENTINA TORNEO CLAUSURA' with
  [5Fh] = 2 (season 2, round 1 played). Cause: InitializeNewSeason builds the player's league into the career slot 0 buffer
  (competitionFileBuffer, IT obj2+0x1F640: its +27h is what the season record reads; DIY_competitionStart 0x4EFF3 is the
  matchday working copy) from the struct names, which were still CLAUSURA; arg_season fixed DIY after the build, too late.
- T16: arg_prebuild replaces the `call cseg_8B2D3` before that GetCurrentSeasonPointer (IT obj1+0x7D163): struct names back to
  APERTURA before the build. arg_names takes the buffer in ebp: DIY in arg_round, SLOT0 (obj2+0x1F640) in arg_load.
  CLAUS.CAR's season 2 stays mislabelled (built by T15): test with a new career.
- T16 PLAYTEST (Davide): new River career shows CLAUSURA on the main screen at once. Likely a league buffer processed at
  career creation with [5Fh] = 0 (not started), which the T15/T16 rule read as "season over".
- T17: arg_names: Clausura only if (every club has played n-1 and [5Fh] == 0) or (not every club and [5Fh] == 1);
  empty buffer ([31h] = 0) -> Apertura.
- T17 PLAYTEST (Davide): CLAUSURA only the first time the career main screen is shown at career start, then fine.
- T18: no name sync after every match any more; the struct names change only at the switch (CLAUSURA), at every new
  season (arg_prebuild: APERTURA) and after a career load (arg_names on SLOT0).
- T18 PLAYTEST (Davide, fresh DOSBox, no load, new River career): calendar says CLAUSURA at once; NUOVA.CAR decoded: league
  buffer text 'ARGENTINA TORNEO APERTURA', [27h] = AP_LONG ptr, season record leagueStringOffset = AP, [5Fh] 2, nothing
  played: the BUILD is right and the struct in the exe has AP names -> the short name the screen shows is overwritten at
  runtime (or read elsewhere).
- T19 (experiment): arg_load hook switched off (ARG_LOAD_HOOK = False in patch.py). If CLAUSURA is gone, the load path of a
  new career runs arg_names with a bad phase; if not, look at arg_round or at another reader of the name.
- T19 PLAYTEST (Davide): still CLAUSURA on the first career screen -> not the load hook. T20 (experiment): arg_round hook off
  too (ROUND_HOOK = False); only arg_prebuild (writes APERTURA) remains of the Argentina name code.
- T20 PLAYTEST (Davide): APERTURA at career start with the switch hook OFF -> the switch (arg_round) fires during career
  creation (the counters routine is also reached while the game builds/advances the calendar, with all clubs at n-1).
- T21 DIAGNOSTIC: switch hook on again; when it fires it stores its caller (return address of cseg_8922B's caller) in the
  manager's season record field_22 (+22h of the 6Ah record). Save at career start, read it from the .CAR.
- T21 PLAYTEST (Davide): CLAUSURA at career start again, but the caller log wasn't in DIAG.CAR (the season record found was
  not the one GETSEASON returned at that time). Reasoning from the engine order: cseg_88A12 calls cseg_8922B (played +1)
  BEFORE adding the result to the table; the calendar building also calls cseg_8922B (results counters at 0): at the
  middle of that every club has played n-1 -> the switch fired during creation and left the struct names on CLAUSURA.
- T22: switch condition = [5Fh] 1, [5Bh] 0, [1CBh] 0 AND every club has n-1 played AND n-1 results (won+drawn+lost): true
  only in real play, at the START of the first Clausura match (nothing of it counted yet). arg_names rule: cycles left
  [5Fh] 2 = Apertura, 1/0 = Clausura, empty buffer = Apertura. Load hook back on. Diagnostic removed.
- T22 PLAYTEST (Davide, 2026-10-02): PASSED. New River career: APERTURA at start (management record: TORNEO APERTURA, ancora in
  gioco), CLAUSURA after the switch (record TORNEO CLAUSURA posizione 12 for season 1), second season starts as APERTURA
  again; saved as APOK.CAR. Still open for Argentina: reload check of a Clausura save (arg_load), aggregate table, promedio,
  Apertura champion message + record line, SA cup qualifiers from the aggregate; unnamed Supercopa/Intercontinental lines.

## Session 28q — management record: nameless Supercopa / Intercontinental lines (2026-10-02)
- Record layout (SeasonInformations, 6Ah each): +16h league name, +1Ah slot-1 name (national cup), +1Eh slot-2 name, +22h slot-3
  name, status bytes +56h..+59h; every name = (string address - chairman address), read back as + aChairmanScenes.
- APOK.CAR decoded: +1Ah = 0x30A6F0 and +1Eh = 0x309DBE (absolute-looking, wrong) while +22h (Copa Libertadores, original
  game code) = 0x465A (relative, right). Cause: sacups' asm (`sub eax, STR_BASE` after the Supercopa slot-1 build, IT obj1+0xA12AE,
  and int_step for the Intercontinental in slot 2, +0xA15E1) declared STR_BASE as a plain constant (symbol type 0): the original
  `sub eax, offset aChairmanScenes` is an ABSOLUTE address with a loader fixup, ours subtracted 0x16F8 only -> a pointer to garbage
  -> empty name line. Fix: 'STR_BASE': (2, STR_BASE) in sacups' symbols -> both subs now carry a fixup (T23, new careers).
  Records already saved (APOK.CAR etc.) keep the wrong values.

## Session 28r — Argentina: aggregate table + promedio relegation (2026-10-02, build T24, static checks only)
- Season end (cseg_91428): `call cseg_92D55` is sacups' sa_qualify; arg_agg (arg97.late(), after sacups) runs first: for the
  player's Argentine Primera (slot 0 name = AP/CL, AP_N > 0): LOAD slot 0 -> DIY (cseg_8B71C), add the stored Apertura stats
  row by row (team word = DIY+12Dh), SORT (cseg_883DD), SAVE DIY -> slot 0 (cseg_8B7EA), then jmp [SAFTER_PTR] = sa_qualify.
  => the qualifiers (which read SLOT0), the final table screen and the relegation all see Apertura + Clausura.
- Relegation (cseg_93FD8, single caller IT obj1+0x81FCA): arg_relegate for DIY id 56h with relegations ([57h] != 0): promedio
  = (2*won + drawn this season + PROM history) / (matches + history matches); the two worst rows go to the last two places
  of DIY+6Dh (second worst, then worst), the real routine runs, the order is restored, PROM updated (old <- last, last <- this
  season, rows without an entry get one). PROM defaults (32 x [team, pts, games, pts, games], 1994-95 and 1995-96) from
  es.wikipedia's "Tabla de descenso" (Colon, Estudiantes: 1995-96 only; Union, Huracan Corrientes: none).
- Saved data: .CAR trailer C7 = C6 + AP block (AP_N, AP_CH, 20 x [team + 7 stat words]) + PROM (320 B); 2.0 'C6' saves load
  (new items from defaults). New 4th obj1 page (OBJ1_NEW_VSIZE 0xA5000; NZ 0xA4000, FIN 0xA4300, ARG 0xA4400, 2430 B) because
  the bigger trailer (948 B) overflowed the world cave into the old 0xA3000 page.
- TO TEST: (1) a full Argentine season with River, all matches: the final table screen = aggregate (38 matches); the two
  relegated = the two worst promedios (compare with the real calculation); next season starts as APERTURA; PROM/AP in the
  trailer; (2) qualifiers use the aggregate table; (3) load of an older save (C6) still works.
- T24 PLAYTEST (Davide, APOK3.CAR, River, season 1 + start of season 2): PASSED by the data.
  * The end-of-season table screen shows the CLAUSURA (19 matches, champion Gimnasia-Esgrima 37, River 3rd 30): the engine shows
    that table right after the last match, before arg_agg. Davide: "la schermata delle 38 giornate non si vede" (by design;
    option: show the aggregate there instead / message with the Apertura champion).
  * Aggregate (decoded from the .CAR): River 74 (44 Apertura + 30 Clausura), Gimnasia-Esgrima 64, Independiente 63, Hur.
    Corrientes 63, Dep. Espanol 56. Libertadores ARG = River, Gimnasia-Esgrima; CONMEBOL ARG 3-5 = Independiente, Hur.
    Corrientes, Dep. Espanol: EXACTLY the aggregate order (3-point, goal difference as tie-break).
  * Promedio: recomputed from PROM (1994-95/1995-96 defaults + this season 2-pt aggregate): Ferrocarril 95/114 = 0.833 and
    Platense 95/114 = 0.833 are the two worst (Colon .842, Huracan .868...). Season 2 starts with Almirante Brown and Douglas
    Haig instead of Platense and Ferrocarril: relegation by promedio WORKS (the Clausura bottom two were Huracan and Ferrocarril).
  * PROM after the season: old <- 1995-96, last <- this season (e.g. Banfield 25 / 42); AP block keeps the Apertura stats.
  * Management record: Supercopa / Coppa Intercontinentale / Copa Libertadores now all named (T23 fix OK).
- tools/salists.py reads the C7 trailer.
- Davide: reloading APOK3.CAR works (load hook / C7 trailer OK). Chose option 1 for the Apertura champion.
- T25: no in-game message system found; the Apertura champion goes into the management record's league line: at the switch the
  record's leagueStringOffset becomes a fixed text 'CLAUSURA (AP: <CHAMPION>)' (one per TEAM.043 club, 40 texts in the cave,
  champion trimmed to 11 chars, 26 chars max), so it survives save/load and every season keeps its own. obj1 grows to FIVE
  added pages (OBJ1_NEW_VSIZE 0xA6000); ARG code 3670 B at 0xA4400.

## 2.5 DOCS TODO (this release is 2.5, Davide 2026-10-02; "2.1" elsewhere in these notes = the same release) — release notes + "stable" README + manuals (Davide, 2026-10-02; write ONLY with his ok to publish)
MUST explain, in release notes AND in the stable README (IT + EN, manual chapters in docs/src IT+EN too):
1. ARGENTINA 1996-97 (exact where possible):
   - TORNEO APERTURA and TORNEO CLAUSURA: the Primera's 38 matchdays are two tournaments (19 each); at the end of the Apertura
     the table is reset and the league is renamed CLAUSURA (calendar, table, management record); every season starts as
     APERTURA; the Apertura champion appears in the record line "CLAUSURA (AP: <club>)".
   - AGGREGATE TABLE (Apertura + Clausura, 3 points a win, goal difference as tie-break) decides the South American
     qualifiers (Libertadores 1-2, CONMEBOL 3-5 of Argentina); the table shown at the end of a season is the Clausura one.
   - PROMEDIO relegation exactly as the AFA did it: points (2 per win) / matches over the last three seasons; the two worst
     averages go down (Nacional B's two best come up). History 1994-95 / 1995-96 from es.wikipedia, kept in the career file
     season after season (clubs without Primera seasons count only the ones played; promoted clubs start from zero).
   - Nacional B: 20 clubs, top 2 up (declared approximation: real 1996-97 had 32 clubs in zones + 'reducido').
   - Old careers (2.0) load; a new career is recommended (team numbers moved: Bolivia, New Zealand).
2. Australia NSL 1996-97 (14 clubs, 26 rounds; Perth Glory + Collingwood Warriors; real squads from the ozfootball line-ups;
   NSL Cup with real bracket; golden goal -> normal extra time; finals series NOT yet (type-1 design pending)).
3. New Zealand NSSL (10 clubs, 4 points a win, shoot-out after every draw +1 point, ON PENS line in the results list but not in
   the league-table screen; 10 real 1996 regional clubs with invented squads).
4. MLS 1997 (real squads from Transfermarkt; 4 games per pair = 36, one table, penalties instead of the 35-yard shoot-out, 3/1/0
   points; no conferences, no play-offs).
5. Management record fixes (Supercopa / Intercontinental names), tools: salists reads C7.
6. Credits (sources): ozfootball.net archive (Thomas Esamie, Chris Dunkerley...) via Wayback Machine, The Ultimate New Zealand
   Soccer Website (Jeremy Ruane), Transfermarkt, Wikipedia EN/ES, RSSSF, SWOS 2020 community DB (checked, not used).

## RELEASE NAME: 2.5 (Davide, 2026-10-02: "questa sarà la release 2.5")
Everything called "2.1" in sessions 28-28r is the 2.5 release: Argentina Apertura/Clausura + aggregate + promedio, Australia NSL,
New Zealand NSSL, MLS 1997. T25 PLAYTEST: Apertura champion in the record, OK (Davide "ok").
Left for 2.5: (a) NSL/NSSL finals series (type-1 design) or declare them postponed; (b) test EN/FR/DE builds (only IT played);
(c) docs (release notes, stable README IT+EN, manual chapters IT+EN, patcher via mkpatcher.py), (d) -, (e) Davide's ok before any push/release/announcement.
- T25 PLAYTEST (Davide screenshot): management record shows "CLAUSURA (AP: INDEPENDIEN)" / Posizione 2 / Supercopa / Coppa
  Intercontinentale / Copa Libertadores: WORKS. Davide: "bellissimo tocco, evidenziamolo nella documentazione" -> in the release
  notes, the stable README and the manual, give the Apertura-champion line its own highlighted paragraph WITH THIS SCREENSHOT
  (River Plate record, 1996/97; the Apertura winner Independiente in brackets).
- T25 PLAYTEST season 2 (Davide, APOK4.CAR): Apertura champion in the record CORRECT (Independiente, 40 pts in the Apertura);
  season 1 record keeps 'CLAUSURA (AP: INDEPENDIEN)' (the cave text, leagueStringOffset negative = obj1 address - chairman) after
  season 2 starts; season 2 record 'TORNEO APERTURA'. Libertadores ARG = Independiente, Hur. Corrientes = the season's 2-point
  totals top 2 (57, 49; Dep. Espanol 48 next). ARGENTINA DONE for 2.5.

## Session 28s — finals series: time-boxed attempt with a type-1 cup (2026-10-02, Davide: "facciamo un tentativo")
- Type-1 cups (cseg_87DA0 -> cseg_268C6): clubs per round are n, n/2, n/4... fixed by halving [31h] (rounds = floor(log2(n/2))+1,
  matches [4Fh] = n/2); round advance cseg_26A78 -> cseg_27F08 draw / cseg_27B4B pairing. No bye, no 'wait a round' and no odd
  counts, in any slot: NSL (6 clubs, 4 rounds with 3-1-1-1 ties and a club skipping round 2) and NSSL (4 clubs, 3 rounds with a
  club waiting) cannot be expressed. Overriding per-round counts ([161h] per round, [4Fh]) à la lib_bye would mean reworking the
  engine's round advance + the slot-4 season-end path (cseg_9228D/cseg_925C9) = several sessions, high risk. Type-2 (explicit
  stages) is the right shape but overflows the 443h slot-4 buffer (T9 freeze).
- VERDICT: the exact finals series are NOT feasible for 2.5. FINALS = False stays; finals97.py kept for a future attempt (idea:
  enlarge/move the slot-4 buffer so a type-2 contest fits, then fin_pre as written).
- Davide's rule: no silent approximation. Options offered: (A) postpone to a later release and document it (recommended);
  (B) approximate (NSSL top-4 native 4-club knockout, no double chance; NSL not expressible); (C) long engine work.

## DECISION (Davide, 2026-10-02): finals series = option B for 2.5, option A KEPT AS A FUTURE GOAL
- B for 2.5: native 4-club type-1 play-off (clone of country 25's contest): semi-finals 1st v 4th and 2nd v 3rd, then the final, for
  the NSSL (single matches) and the NSL (top 4 only: 5th and 6th do not play; semi-finals two legs, Grand Final single).
  Declared approximations in the docs: NSL 6 clubs -> 4, no double chance (second chance of the loser of 1v2).
- A (FUTURE, keep in the backlog): the exact formats (NSL: 1v2, 3v6, 4v5 two legs, then the double-chance sequence; NSSL: 1v2,
  3v4, loser v winner, final): needs per-round control (byes / waiting clubs) = a type-2 contest in slot 4 (buffer 443h too small)
  or a rewrite of the round advance; finals97.py (type-2 contests + fin_pre) kept for it.
- T26 (build, static OK, UNTESTED): option B implemented: finals97.structs builds, for the NSL and NSSL division 0, the play-off
  block (div entry: 0 promoted, 4 'promotion play-off' clubs = places 1-4, playoffData -> block) with a TYPE-1 contest cloned from
  country 25's (14-byte header, rounds NSL 0x94 (two legs) + 0x14, NSSL 0x14 + 0x14, names 'NSL FINALS' / 'NSSL PLAYOFFS',
  4 placeholder clubs), candidate order [0,3,1,2] (1v4, 2v3), zero deltas (nobody moves), fixed draws (hist_draw DRAWS, ids C4/C5,
  4 and 2 clubs). fin_pre is a bare `ret` (DOUBLE_CHANCE = False); slot4_type not applied. FINALS = True in patch.py.
- T26 PLAYTEST NSSL (Davide, NSSL18.CAR / NSSL18B.CAR, Waitakere City): at the end of the 18 rounds 'NSSL PLAYOFFS FINALE' appears in
  the calendar (Waitakere reached the final), the season closes without a freeze, season 2 starts (same 10 clubs in division 0
  of the cached records, nobody moved; regular-season draws show 'VINCE 5-3 AI RIG' lines). NSL (Australia) still to test.

## Session 28t — NSL play-off bugs (2026-10-02)
- T27: season-end record froze (int3 + jmp $ at obj1+0x2BCC3) for Perth Glory: the record lookup (obj1+0x2B6ED) does not find
  the club in the slot-1 cup (Perth is not in the real NSL Cup 1996-97 list). finals97.rec_guard: lookup returns -1, the cup is
  dropped from the record (SeasonInformations +1Ah/+1Eh/+22h := 0). TESTED OK (Perth, Collingwood, Gippsland).
- Debug note: obj1 is loaded at linear 0x262000 (not 0x261000): BP 160:(0x262000 + obj1 offset).
- No final in the NSL/NSSL play-offs (the "FINALE" rounds were the SEMI-FINALS): slot-4 DIY [59h] (rounds) = 1 in every save
  (31h = 4), so the career calendar (type-1 branch of cseg_8BF89, IT obj1+0x7BF46) gave dates only to round 0 and the play-off
  ended after the semis (NSSL too: its earlier "final" was the semi-final). Origin of the 1 NOT found (cseg_268C6 computes 2
  for 4 clubs; no other writer of +59h). T29: finals97.cal_rounds hooks that read: contests C4/C5 with 4 clubs get 59h = 2 in
  the slot buffer before the calendar is built. NSL rounds back to [0x94, 0x14]. TESTED OK (Davide, new Gippsland career): 'S-FINALE AND./RIT.' (two legs, away
  goals), then 'FINALE' single match (lost 0-1 to Melbourne Knights), season closes. Record still 'NSL VINCITORI' (1st of the
  regular season) -> option 3 to do.
- Davide's choice on the record (option 3): the play-off winner should be the champion in the management record (to do after
  the final works; today 'NSL VINCITORI' = 1st of the regular season).
- T30 (build fb4467e1, UNTESTED): finals97.rec_playoff (option 3): the league line of the season record (+56h) of a club that
  played our play-off = its play-off result (1 VINCITORI, FINALISTA, ALLE SEMI-FINALI) via the game's own cup lookup/position
  on slot 4 (obj2+0x19DE9, contest ptr = slot-0 ptr + 16); others keep the regular-season place. Code after the Argentina
  cave (obj1+0xa5280): the FIN cave is full. Test from PRE.CAR (T29 Gippsland career, before the semis, 59h = 2).
- NSSL check (Claude, via computer use, new Napier City career saved as NZT30.CAR): slot 4 C5 [59h] = 2, calendar has slot-4
  entries for round 0 AND round 1 (semis + final). Builds EN/FR/DE + GOG made (EN d9d521d6 FR dff1ecb4 DE 314ac1a3; GOG
  105e69a2 8c1520eb a3eb3f59 bfe9137c), patcher 2.5, docs committed (65f44d1). In-game EN/FR/DE test: Davide.
- Driving SWOS in DOSBox-X by computer use: full-screen tools, hold_key ~0.05-0.1 s (plain key presses are missed), arrows +
  left Ctrl = fire; Return in text fields.

## NEXT (Davide, 2026-10-05): DDR 1988-89 as a historic "nation" (start after the weekly reset, Thu 8 Oct)
- DDR-Oberliga 1988-89 (14 clubs, 26 rounds, 2 points a win) + FDGB-Pokal 1988-89 (real bracket from the round where all
  Oberliga clubs enter; lower-league clubs still in it at that point included).
- Own country number (free 92-99) + new TEAM file (14 Oberliga clubs + Pokal clubs), real squads (16 most-used players:
  de.wikipedia, weltfussball.de, RSSSF; check SWOS 2020 community packs first).
- Visible in the historic tourneys menu of Preset competitions AND in Season mode team choice (pick e.g. Dynamo Dresden, play
  Oberliga + Pokal); NEVER in career. To verify first: how Season mode builds its world menu (hook like hist_preset) and how it
  assigns European cups.
- Option 3 chosen: start with DDR only; meanwhile look for a community 1988-89 database. If found: rebuild the 1988-89
  European cups (CC, CWC, UEFA, ~120 clubs) so Season mode plays them too. No 1996-97 squads as stand-ins.

## Session 29 — DDR 1988-89: data (2026-10-08)
- Davide: preset historic menu = Oberliga 1988-89; Season mode = Oberliga + FDGB-Pokal + (if possible) European cups 1988-89.
  Pokal: Davide chose to start from the 2nd main round (32 clubs: 14 Oberliga + 18 lower; all 14 Oberliga clubs survived round 1).
- tools/ddr89.py: OBERLIGA (14 clubs, final-table order, coach, players by Oberliga minutes from weltfussball.de
  'Statistik: Einsätze'), LOWER (18 Pokal clubs from weltfussball 1988/89 squads; HFC Chemie II 11 names, Neustrelitz and
  Weida 13 with surnames only -> invented fillers needed), POKAL_R2 ordered so consecutive winners meet as in reality
  (natural pairing then gives the real R16/QF/SF/final); real results in comments.
- weltfussball.de works only in the built-in browser (Cloudflare blocks curl). New URL scheme:
  /teams/<teXXX>/<slug>/vs1988-1989/kader/ (squad by role), /teams/<teXXX>/<slug>/se3583/1988-1989/statistik-spiele/
  (Oberliga 1988/89 appearances by minutes; se3583 = Oberliga 88/89), Pokal 88/89 = co1415/se19295.
- Skills source: SWOS 2020 teamdb '1990_91 - Team Updates' (Peppecapello) -> its TEAM.010 = 14 NOFV-Oberliga clubs 1990-91
  (Hansa, Dresden, Erfurt, HFC, Chemnitzer, Jena, Lok, Brandenburg, Eisenhüttenstadt, Magdeburg, BFC, Sachsen Leipzig,
  Cottbus, Vorwärts Frankfurt). Downloaded to the session scratchpad (re-download: sensiblesoccer.de/swos2020/dlc/teamdb/
  1990_91%20-%20Team%20Updates.7z) -> copy to orig/swos2020/x_1990_91 when building. Credit Peppecapello. (TEAM.010 in the
  real game = another country: DDR needs its own free number.)
- NEXT: (1) code study: how Season mode builds its world menu and assigns European cups (season call of SelectTeamsFinalMenu,
  historic._calls 'season'); (2) country number + TEAM file + Oberliga league struct (14, 2 points) + Pokal cup (32,
  single matches, e.t.+pens, fixed draws via historic.DRAWS); (3) European cups 1988-89 for Season (needs ~100 clubs of 88-89).
