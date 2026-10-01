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
  NOT in someLeaguesTable (0 entries 1850-1923 in both saves); save caches only some team records -> league layout of the
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
