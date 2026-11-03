# The automated test harness (tools/swostest.py) — technical guide

State: release 3.1 work, 2026-10-12. `notes/testing.md` is the work log (history, results, timings); this file is how
the harness works today and how to extend it.

## 1. What it is

A Python program that runs the real game (the IT exe under test) in a private DOSBox-X, plays it through its menus
like a player, pauses it whenever it wants to look, reads the game's memory and saves, and decides PASS / FAIL. Nobody
touches the keyboard: no window focus is needed, several runs can go at the same time.

```
python3 tools/swostest.py list                       # scenarios
python3 tools/swostest.py run [-jN] [NAME ...]       # all or some, N at a time; exit code 1 on a failure
python3 tools/swostest.py keys EXE CAR|- 'KEYS' ...  # ad-hoc key script (see the module docstring)
```

Environment: `SWOSTEST_BUILD` (dir with ITALIAN.EXE + DATA under test; else `SWOSTEST_BRANCH` = a git branch/commit to
build; else this checkout), `W8485_BUILD` (build for the 1984-85 world scenarios), `SWOSTEST_RUNS` (run dirs, default
`internal/swostest/runs`: a second suite needs its own), `TURBO=0` (real-time speed), `CORE=normal` (needed for code
breakpoints), `W84NAT_REDO=1` (remake the cached national-team saves).

## 2. How one run works

1. **Private copy.** `prepare()` copies the game (`internal/swostest/base` = c/SWOS without exes and saves) to
   `runs/<name>/SWOS`, adds the exe under test and the saves the scenario needs. `c/SWOS` is never written.
2. **Patched exe (run copy only).** `test_exe()` patches the copy: intro skipped; the menus' `call GetKey` goes to a
   *key feeder* stub on a new obj1 page. The stub types the scenario's keys one by one (scan code into keyBuffer +
   key-state flags, as the keyboard interrupt would) and waits between keys counting **GetKey calls, i.e. menu
   frames**, not seconds: loading and simulating do not eat the waits, so the same script gives the same game run.
   A special step `dump` executes `int 3`: that is a **pause**.
3. **DOSBox-X under a pseudo-terminal**, started with `-break-start`, `BPINT 3` set in its debugger, `cycles=max`,
   **turbo on** (the emulated PC runs as fast as the host allows: ~10x real time in menus). The mod's own fatal traps
   are `int 3; jmp $` too, so a crash of the game is caught as a "trap" (EIP outside the feeder page).
4. **At a pause** the runner (class `Session`):
   - dumps memory with the debugger's `MEMDUMPBIN`: all 32 MB at the first pause (to find where obj1/obj2 are in
     linear memory), then ~1 MB (feeder page + obj2) per pause, and small ranges on demand (`Result.read`);
     4.0.6+ builds have obj3 (benchx; CONVENTIONS 23), which DOS/4GW loads apart (below obj1 in DOSBox-X):
     `Result.base3` comes from an obj1 pointer into obj3, `Result.lin((obj, off))` maps any object offset, and
     benchx's variables are `Off3` offsets (`bench_switch`), so the scenarios read them the same on 4.0.5 and 4.0.6;
   - parses the current menu (`Screen`: g_currentMenu in obj2 — entries with text, invisible/disabled flags,
     left/right/up/down links, x/y/w/h);
   - writes the next keys into the feeder's script area (`SM` commands typed into the debugger), moves EIP past the
     `int 3` (`SR EIP`) and resumes (F5).
5. **Oracles**: saves written by the game (`.CAR`, parsed by `car_info`, `checkw1`), memory structures read at a
   pause (cup and group team lists, holders, flags), the outcome (pause reached / trap / timeout / DOSBox exited).
6. **Timeouts**: each Session has its own (scenario-set) timeout; `SWOSTEST_TIMEOUT_MUL=2` (or 3) scales them all when
   both Macs are saturated (load 50-250: DOSBox crawls, a dump can take minutes).

## 3. Driving the game

- `press(s, screen, 'TEXT')`: finds the visible entry, computes the key path with a BFS on the menu links (skipping
  invisible entries as the game does), checks on the next pause that it is selected (a move can be taken twice),
  then fires. Every step is verified, so a dropped key is retried instead of derailing the run.
- `advance(s, stop)`: the results-only career loop Davide uses (PARTITA → VIS. RISULTATI → ESCI …): message screens,
  cup round screens, the squad screen. Special cases:
  - squad screen without VIS. RISULTATI (an injured/suspended player in the first 16): `substitute()` takes a
    frame of the screen, finds the red rows, swaps them with fit reserves (a goalkeeper for row 1). Standing rule
    (Davide, 2026-10-19): the MINIMAL line-up is the default - `substitute_min()`: an unavailable starter changes
    places with the first fit reserve the 17th row shows, nothing more (no best-reserve search, no starter brought
    back). The full selection (`SWOSTEST_LINEUP=full`: the best fit reserve of the slot's role by value, the starters
    restored when fit) only in scenarios that judge the career club's own results or strength; it cycled every
    reserve at every squad screen and was ~50-60% of a long career's pauses (world_full_arg / _eng, rc1);
  - injured goalkeeper: first the reserve goalkeeper of row 12 (the rows' positions are drawn, not menu entries);
  - the long bench (4.0.5 benchx, a bench over 5): rows 12..17 are a window on the places from 12 on, moved only by
    FIRE on the box left of row 17 (4.0.6, Marco: the name rows never scroll it; up to 4.0.5 the cursor did on rows
    12 / 17); the game swaps by place (the mark is kept while the window scrolls). So every swap goes through
    `swap_in()` / `swap_rows()`: a reserve shown on row 17 is fired FIRST, then the starter's row (rows 1..11 never
    move); a bench row only after `window_home()` (the box to window 0; `bx_window()` reads benchx's window word),
    then the box to the reserve. Up to rc14p the fixer marked the row first and came back to row 17 - the way up had
    scrolled the window back, another player went in, and careers looped for hours (world_full_eng 30/10). `substitute_min` stops as soon as VIS. RISULTATI shows (an unavailable
    bench player is left out at the kick-off), and the fixer fails after LINEUP_STUCK (3) squad screens in a row left
    by ESCI without VIS. RISULTATI. No red row but VIS. RISULTATI hidden (rc19): the first 16 places are read from
    memory (`lineup_mem`: an unmarked suspended player is fixed; no keeper in goal -> the keeper swap); a fit keeper
    and nobody unavailable = the game refuses the line-up -> an immediate FAIL ('the game refuses the line-up ...',
    rc19 world_gplay_nzchamp's NZ Grand Final), no keeper ping-pong. Scenario `bench_lineup` (BENCH_BUILD) checks the fixer and the game's swaps;
  - national team: menu without TRASFERIMENTI, PARTITA disabled until the squad is called up: `nat_callups()` adds
    players from the home leagues (enabled player rows = eligible) until "SCEGLI ALTRI 0".
- `next_season_save(s, NAME)`: season-end menu → (job offers if sacked) → CONTINUA CARRIERA → new season → save.
- `Session.poke(linear, bytes)`: writes game memory (debug switches, see §4).

## 4. Shortcuts: never wait for luck, never replay seasons

Rare events are **forced** and slow parts are **done once and saved**:

- **Debug switches poked into memory** (test run only, never in the build): the game's `dseg_17A3CE = 2` makes the
  national team of the manager's nationality offer its job at once; `dseg_C8B14` (bit per season in which a European
  national team may offer a job) set to all ones; `currentSeasonShowing` poked to start in another cycle.
  Addresses come from patterns in the exe under test (`nat_offsets`), so they follow every build and language.
- **Smallest league**: the club season before a national job is played at St. Andrews (Malta: 10 clubs, 18 matches,
  low expectations), not in a big league: the national team depends on the coach's nationality, not on the club.
- **Cached saves**: `nat_offer_save()` plays the club season once (England's offer kept, career saved at the season
  end) and keeps it in `internal/swostest/saves/<NAME>.CAR` with the exe's md5; later runs reload it. A new build
  remakes it automatically.
- **Reading at the right moment**: the season-end processing runs *after* the chairman's opinion that follows
  CONTINUA CARRIERA: read the finalists at the next career menu (`after_end`). If the manager was sacked, CONTINUA
  CARRIERA is disabled: the test enables it by a poke of the menu entry, only to let the season end run.

## 5. Scenarios (2026-10-12)

| scenario | what it proves | time |
|---|---|---|
| italy_season | Juventus 1997/98 season end: no trap, save written, next Champions Cup 16 distinct with Italian clubs | ~10 s |
| roundtrip | load/save/reload/save of a career: byte-identical | ~20 s |
| juve2_trap | known old save (E092F): the season end must not trap | ~8 s |
| world_roundtrip | world 3 (31 countries, 128 European records): two saves identical, W1 block, cups 32/32/64 | ~25 s |
| euro_draws | season end 1997/98 → 1998/99: Champions Cup holder rule, no same-country ties in rounds 1-2 | ~60 s |
| italy_advance | mid-season 1998/99 save → results loop with substitutions → new season → CC list | ~3 min |
| world8485 | Europe 1984-85: new career at Liverpool, 2 seasons (save, reload, save), checkw1 on both | ~6 min |
| world8485_nat | coach nationalities (YUG/FRG/URS/GDR in the menu); England's job (forced); call-ups at home (the world's English divisions) and abroad (the world's 32 countries); real Euro 88 qualifying groups; a national career saved mid-qualifying and reloaded (groups intact); Euro 88 = West Germany + the 7 group winners, the 8-team finals played; next cycle: Italia 90 draw (host out), the 24 (holder, host, 13 European, real others), the World Cup played, its winner becomes the holder; an East German coach gets the GDR job, squad "EAST GERMANY", call-ups from the DDR-Oberliga clubs | ~14 min (first run on a build) / ~8 min |
| classic_wc34 | 3.2 tourney pack: World Cup 1934 in CLASSIC TOURNEYS: round 1 = ties.csv, every later tie = the winners of two adjacent ties (also after replays), coin tosses, third place, final | ~30 s |
| classic_groups | 3.2 tourney pack with groups (the template, in a test build with SEASON_PACKS): 2 groups of 4, crossed semi-finals, third place, final; its round robin (5 clubs, home and away: 20 matches) | ~1 min + build |
| classic_tourneys | World Cup 1982, Mitropa Cup 1934 (real bracket also after play-offs), FA Cup 1871-72 played to the final | ~2.5 min |
| xtra_squad | extended career squads (xtra.py): new career at HAMBURG with a test DATA/XTRA.014 = 16 + 9 real players (copies of its own first 9), no invented reserves, each extra's wage 66% of his twin's, form byte untouched, 25 after save + load; HANSA ROSTOCK (no block) = 16 + 10 reserves | ~40 s |
| xtra_world30 | extended squads of the World 2026-27 (XTRA30_BUILD = the world built with TM_EXTRA=14): a career at CELLE VARAZZE (Serie D A, XTRA30_CLUB / XTRA30_PATH / XTRA30_LAST to change) starts with 30 players, slots 16..29 = its XTRA block in file order (STEFANO CHIAIA the 30th), order 0..29, wages > 0; two seasons with save + reload keep the extras | ~5 min |
| (W8485_RNG) | 4.0.5: world8485's `W8485_RNG=<6 bytes hex>` pins the game's two random generators (Rand / Rand2: seed, randXorIndex, randXorKey; rng_sites) at the career's start. Their state there follows every Rand call since the game started, i.e. DOSBox timing and the exe's load: 31/10 f1dd98f's 233 B (never executed) moved it and xtra_world30 took another season (contract not renewed, 22 players). xtra_world30 sets it by default (XTRA30_RNG, 000000000000); seasons still differ slightly between builds (emulator timing), but no longer at the start | - |
| (W8485_RNGSTEP) | 4.0.5: `W8485_RNGSTEP=<salt>` re-pins both generators at every harness pause from md5(salt:season:pause number). CareerMenu reseeds Rand from currentTick on every entry, so the start pin alone still let the exe layout choose the path (gs3 / gsOFF: CELLE VARAZZE in the play-out, contract not renewed, MODICA, 24 players). xtra_world30 sets it by default (XTRA30_RNGSTEP, 'x30'): PASS on c/REL405gs3 and c/INT405pre26 | - |
| xtra_market | buying players 17-30 of other clubs (XTRA30_BUILD, TM_EXTRA=14 data): CHISOLA (25) starts, the game's own market holds XTRA players (index >= 16), the home market poked with three LIGORNA extras, list + offer screens (shots), the first bought (squad +1, his name, market entry gone, sold list 'XS' = (team, 16)), save, reload (same squad, XS back), list again, match day | ~1 min |
| xtra_club_browse | the extras findable in their club (XTRA30_BUILD): LIGORNA's list in ACQ. ALTRO GIOCAT. NAZION. has the button PAG. SUCC. (entry 31), page 2 = its extras (numbers 17.., shots), the first one picked + bought from CHISOLA (squad +1, sold list, page 2 compacted, shot), a club with its block zeroed (IMPERIA, a modified XTRA file) has no button, CELLE VARAZZE (30) is refused (squad full), save + reload | ~2 min |
| xtra_squad_views | a club's full squad in the squad screen (XTRA30_BUILD): VISUALIZZA MONDO > ... > SERIE A > STAT > VIS. SQUADRE > MILAN: page 1 = 16 + button PAG. SUCC. (entry 6, left of ESCI), page 2 = extras (shots), record bytes unchanged, a club with a zeroed block (PARMA) no button, the same through VISUAL. COMPETIZ. (LIGORNA), own squad afterwards normal | ~1 min |
| xtra_season | XTRA1.CAR (HAMBURG, 25) played to the season end by results (no sacking when the harness has nosack_off), next season saved: at most 32 players, the real extras still there, wages recomputed at the season start = 66% of the twins' (twins' bytes 25-37 copied in at the season end) | ~4 min |
| world_split_single | world 2026-27 (private world5tm) with the SPLITS keys (build world_split; SPLIT_BUILD reuses one): two seasons at ST. MIRREN, Scotland 33 + 5 (balance): days, matches, groups in place order, points, the career club's post-split fixtures (its group, home by the balance rule) | ~40 min |
| world_split_double | the same build at HARTBERG: Austria 22 + 10 (double round after the split) | ~40 min |
| world_split_halved | the same build at BOTOSANI: Romania 30 + 10 (6 double, 10 single, points halved rounded up, 'points before rounding' first) | ~35 min |
| world_split_h2h | the same build at PETROCUB: Moldova 21 + 10 (top 6 from half their head-to-head points; 7th-8th done) | ~40 min |
| world_split_reverse3 / _odd / _three / _none / _stages | the same build kind (all SPLITS keys) at BANGOR (NIR, reverse3), LOKOMOTIV SOFIA (Bulgaria, odd groups and rest days), VOLOS (Greece), PARDUBICE (Czech middle group stops), HIBERNIANS (Malta, 3 stages: reset, kept Opening table) | ~60 min each |
| world_odd_league | an odd-size division (ODD_BUILD, default the newest builds/w2627odd-*; ODD_TEAM, ODD_CLUBS): a season at AUCKLAND CITY (NZ 11): 22 days, 20 matches each, the next season started | ~40 min |
| world_ns | two career worlds in one exe, each with its own country namespace (build: 1984-85 + a 20-country 2025-26 test world from the private SWOS 2020 converter, FIRST_FILE=112 so its files 112-131 reuse 1984-85 numbers; XTRA hook): new careers at AEK Larnaca 2025-26 and Valletta 1984-85 (after a detour into world 5's club list) = the same team word 0x83, each with its own world's extras (XTRA.131 / XTW5.131); each save loaded after the other world's in one session: VIEW WORLD lists the right world (INGHILTERRA / ENGLAND), the season played to the end and saved, checkw1 | ~20 min |
| menu_numbers | 3.3.4: tactics editor (MOD. TATTICA > UTN A; English MENU_PATH='EDIT TACTICS,USER_A') with LEICESTER poked to 17..32: the pitch's little numbers 12..99 are menunum's sprites 1620.., each = tens + 1 px + units of the menu's own digits (pixel-exact); screenshot | ~20 s |
| bench_world | 4.1 panchina blocks 1-3 (tools/benchx.py): World 2026-27 build (BENCH_BUILD), a new player-coach career at CELLE VARAZZE (30 players), bx_bench poked to 15, the first match played for real ('- PARTITA -' with nop_league_int3, GIOCA PARTITA): gameMaxSubstitutes 15, the club's in-match team 26 named (11 + 15), the opponent 16 + 10 empty places, the name sprites of places 17..26 (1910.. / 1920..: 112 x 6, drawn), the bench list seen on screen; the bench cursor down to place 21 (BENCH_SUB, 12..26): the window of 5 follows it (down, up 6, down again), the change made (NumSubs + 1), bx_ord = one swap in that team's half once he is on, the other half untouched; a goal poked into the record of the player who went off (now at place 21) reaches his squad record after the match; played to the career menu. SWOSTEST_MEMSIZE=8: the same in the 16-colour mode (no bench-list pixel check). BENCH_SQUAD=2: the long lists of SQUADRA, the pre-match screen and the tactics editor (box window, marked swap while the box scrolls; 4.0.6 Marco: the name rows never scroll - down on row 17 -> the game's next entry (`wrap_reach`: ESCI / GIOCA PARTITA / ANNULL.; 4.0.6 Marco / Davide 02/11, as the original game: on the pre-match screen the player / coach line, entry 6, then down PLAY MATCH, entry 9, up back to 6 and row 17; ESCI up and UTN A / C / E left -> 6 too; entry 6 hidden by a poke (a manager): row 17 down -> 9, up -> row 17, ESCI up / UTN left -> row 17), up on row 12 -> row 11, the window kept), IT and SWOSTEST_UI=en; BENCH_VIEW=1: ViewSquad (the box only, the name rows as the game); BENCH_SAMPLE=secs: each in-match bench-cursor key through sample() (BPINT 8): a dump that never comes back gives the obj1 EIPs (02/11: such stalls were DOSBox starved under load, ~12 timer ticks in 90 s, not a game hang) | ~1-3 min |
| fin_statement | 4.0.6 finance's row on the in-season statement (tools/finance.py fi_stmt, Davide on the MiSTer: the income was credited with no row): SWOSTEST_BUILD (SWOSTEST_UI it / en / fr / de, that language's exe as ITALIAN.EXE); a new JUVENTUS career and the old save JUVEFIX3.CAR, each to the career menu after one match charge, ANDAMENTO CLUB: the label `finance.ROW[lang]` visible, font characters, within its entry, label rows apart and above CONTINUA; the row = the sponsorship x the exe's currency (lire x 2); old + total = new; the shown rows + the hidden D6B88 / bonuses = the total; screenshots `statement_new` / `statement_old` | ~1 min |
| stadium_versus | 4.0.6 (Davide 02/11) the stadium name on the versus screen (stadium.py), STADIUM_BUILD or the harness build (CORE=normal) + a test DATA\\STADTEAM.DAT: friendlies INTER v MILAN, FIORENTINA v ROMA (32 chars), JUVENTUS v LAZIO (no record); pairs of the same case because RandomlySwapTeams picks the home side; a breakpoint after VersusInit's fade-in: stadium_vs_check - the name (small font) in the text ink colours only, stadium.GAP rows under the bars' last row, centred on the title (+-1), one text line, inside the screen; no name: no title ink under the bars | ~3 min |
| stadium_world | 4.0.6 stadium names per team-file namespace (STADIUM_BUILD / BENCH_BUILD, release recipe): World 2026-27 career at ROMA, training game: STADTMW5.DAT's name on the versus screen (stadium_vs_check), STADTEAM.DAT's decoy for the same (file, ordinal) ignored | ~1 min |
| stadium_venues | 4.0.6 neutral finals (STADIUM_BUILD, a release build with its own STADTMW5.DAT v2): World 2026-27 career at ROMA, training game; a breakpoint at st_find's end puts each case's strings into gameName / gameRound (+ currentSeasonShowing) and sets EIP back to st_find: every venue row (all 4 languages) -> its venue before the home club, wrong season / cut competition / other round -> the club, the game's '*' padding ends a string; the real strings back -> the club's name on the versus screen (stadium_vs_check; the tour: STADIUM_SHOW=k case k's venue instead, STADIUM_SHOWNAME=name that name poked into st_name; any SWOSTEST_UI incl. fr / de), the line-ups after it. All cases in one match | ~2 min |
| stadium_nofile | 4.0.6 (Davide 02/11: names only in World 2026-27): the build ships no DATA\\STADTEAM.DAT; friendlies INTER v MILAN with it absent, empty (0 bytes), version 1: st_find ran, no name, no title ink under the bars, the match goes on | ~3 min |
| bench_cup | 4.0.5 real benches per competition (bench2627.json + build-time fallbacks): a World 2026-27 career at RANGERS (BENCH_BUILD, BENCH_CUP_TEAM), season 1 (world8485, results only); benchx's lookup at every pre-match screen (bx_lkname / bx_lkres, W8485_HEX on obj1) logged: BENCH_CUP_WANT ('SCOZIA SCOTTISH PREMIERSHIP=9:5;SCOZIA SCOTTISH CUP=9:5') seen, no title it plays left at 5 (its UEFA qualifying tie included). bench_world: BENCH_TITLE = the title looked up at the kick-off | ~15 min |
| bench_training | 4.0.6 (Marco) a training game keeps the game's 2 from 2 (benchx bx_look skips it): a World 2026-27 career at ROMA (BENCH_BUILD, TRAIN_PATH), SQUADRA -> TRAINING (IT: PRATICA): the kick-off's gameMin / MaxSubstitutes 2 / 2, both in-match teams named in places < 16, the dugout shot (train_dugout); the training played out, then the league match: its kick-off has the real bench again (TRAIN_REAL, default 15:5, ITALIA SERIE A) | ~3 min |
| oppo_list | 4.0.6 (Davide's option b) the opponent's squad, read only, in the in-match bench menu (oppl.py): bench_world's match (BENCH_OPPL=1, release exe); UP on the coach opens it (g_subsState 5): page 0 its 11 on the pitch, DOWN its bench pages (11 a page: places 12.. not used, not sent off), UP back, nothing past either end (page / rows checked against its in-match team); FIRE / LEFT / RIGHT close it (state 0, cursor 0); both in-match teams (1704 bytes) and NumSubs unchanged; benchTeam / benchTeamGame = the bench team's own at every dump with the list open (the draw's shadow never leaks); the SWOS++ mark poked to 0B8h (what SWOS++ writes, swospp_bench) -> UP leaves it shut; every page has the opponent's name row on top (oppl_title: its frame in the list's frame colour at y 8 / 18 and the list's columns, the name's ink inside; Davide's look review); then a change as usual (bench_sub). Shots oppl_page0 / oppl_down1.. | ~1 min |
| kits_training | 4.0.6 (Marco) SELECT KITS in a training game (kittrain.py: slots by name + team pointer): ROMA A / SQUADRA B, MAGLIE -> OK (the automatic A first / B second), SOLO PARTITA / SEMPRE hidden, the kick-off's in-match kits differ (TeamGame's worn colours), careerTeam's kits unchanged; then the league match: SELECT KITS on the club and its opponent, played | ~4 min |
| squad_numbers | 4.0.6 (Marco) editable shirt numbers on the club's squad screen (squadnum.py: shirtedit's editor there): JUVEFIX3, SQUADRA: LEFT lights row 7's number, UP = next free, typed 23 (holder swapped), ESC undoes (still on the squad screen), typed 7 + ENTER (swap, pin bit), DOWN moves, a starter <-> bench swap keeps the numbers; saved (.CAR careerTeam at 56192) + reloaded: same numbers; another club's squad (VISUAL. COMPETIZ. > SERIE A > STAT > VIS. SQUADRE > CAGLIARI): LEFT / UP / 23 change nothing. Shots squad / lit / typed23 / after / reloaded / opponent | ~1 min |
| squad_numgap | 4.0.6 (Davide 02/11, MiSTer) two-digit shirt numbers clear of the face box and the name bar (numcol.py: number column x 14, names 2 px right on the lists): a new World 2026-27 ROMA career (99, 43, 86...) on NUMGAP_BUILD (a release dir, ITALIAN.EXE = the language's exe; any SWOSTEST_UI) -> squad screen, team screen (PRATICA / TRAINING), tactics editor (MOD. TATTICA -> the first user tactic: UTN A / USER_A / UTIL A / SPIEL A): numgap_check - every row's number ink (2 / 8) keeps 1 clear column after the face box and 1 before the name bar, on all three (Davide 03/11: names +2 px on the lists); shots squad / team / tactics | ~1 min |
| market_keep_page | 4.0.6 (Enzo) the market list keeps its page after an offer (mklist.py), release exe (foreign_exe), World 2026-27 INTER: national market (filled to 25 when under 21) ELENCA, ALTRI, row 13 -> offer -> ESCI: page 10, same found count and rows, cursor on row 13, label ALTRI; ALTRI -> page 20; a page-20 pick with the market cut to 20 under the offer -> back on page 10; foreign market (INTER: 12 players): ALTRI to page 10, a pick, ESCI -> page 10, same rows. 4.0.5: page 0, empty list. Shots nat_p2 / nat_back / nat_p3 / nat_emptied / for_page / for_back | ~2 min |
| scorers_int | 4.0.5 INT column (tools/scorint.py): Luigi's PROVA.CAR (SCORERS_CAR) loaded on SWOSTEST_BUILD (SWOSTEST_UI it / en / fr / de), VISUAL. COMPETIZ. -> CAPO CANNONIERI NAZIONALE: every row's numbers read from the screenshot (digit shapes learnt from the rank column), LEGA + COP1 + COP2 + INT = TOT, the numbers apart, the last row = its player's record +33..+36, the others some record's; FAILs on rc19 (no INT column) | ~10 s |
| scorers_int_world | the same after a World 2026-27 career season (SCORERS_TEAM, default NAPOLI: Serie A + Champions League; world8485 W8485_SAVE_END, then loaded) | ~6 min |
| goal_slot_sc / _sc_real / _cd / _po | 4.0.5 goal counters (tools/goalslot.py): a World 2026-27 career (INTER / FIDELIS ANDRIA / MODENA forced 5th of Serie B on a DPLAY_FORCE=5 build) on GOALSLOT_BUILD up to the SUPERCOPPA / COPPA ITALIA SERIE D / PLAY-OFF results (W8485_MIDTEXT, else the season's end; _sc_real: the SUPERCOPPA ITALIANA final played for real, W8485_REALPLAY - the match engine's write-back); gs_add's ring of the remapped goal writes (both write-back sites: played and simulated matches) read from obj1 at every screen: +37 (form / trial mark) unchanged, the goals in COP1 / COP2 / LEGA, never slot 4 as the game | ~3-8 min |

Preset competitions are driven by `play_preset(s, button)`: COMP. PREDEFINITA > TORNEI STORICI > button > TORNEO,
then VIS. RISULTATI / REPLAY / PROSS. PARTITA / PROSSIMO TURNO / TURNO RITORNO until only STAT and ESCI are left;
it returns the rounds (title, ties shown: at most 6 per screen) and the coin-toss texts.

`run -j4` runs them in parallel (own DOSBox-X and run dir each).

## 6. Adding a scenario

1. Write `@scenario def name(): """one-line purpose"""` returning `(ok, message)`.
2. Start from a save close to the point to check (copy it into the run with the `cars` argument); if none exists,
   make it once in a helper and cache it like `nat_offer_save`.
3. Use `Session(...)`, `press`, `advance`, `next_season_save`; force rare events with `poke` (find the variable's
   address by a byte pattern in the exe, not a fixed offset).
4. Check with `check(cond, message, errs)`; put what you saw in the message: the report is the evidence.
5. Run it twice: same result (the feeder is deterministic; match results may vary between runs because game time
   leaks in, so never assert a specific score or winner).
6. Line-ups: leave the default minimal line-up (§3); set `SWOSTEST_LINEUP=full` in the scenario only when it checks
   the career club's results or strength (the full best-reserve search costs about half of a career's run time).

## 7. What the tests do not cover (a person still has to look)

- **Playing a match** with the joystick/keyboard: scenarios use VIS. RISULTATI (simulated results), as Davide's own
  quick loop; the match engine itself is the original game.
- **The look of the screens**: names, kits, colours, text alignment (only entry texts and red rows are read).
- **Languages at run time**: scenarios run the Italian exe; EN/FR/DE are only patched and assembled.
- **Every branch of the career**: e.g. the World Cup 1986 list exists only if one coaches a national team during
  1984-85 (as in the original game); jobs of national teams other than England and East Germany; job offers from
  clubs to a national coach; long careers beyond 1990.

## 8. Troubleshooting

- Frames (`shots/*.png`) are built from the paused game's memory, not captured from the window (since 2026-10-18:
  macOS asked for screen recording again and again): video memory at A0000 + `g_workingPalette`, 320x200, one pixel
  per game pixel (`Session.shot(tag)`; a trap writes `final.png` from its full dump). A running game cannot be read,
  so periodic shots and the `final.png` of a timeout need `SWOSTEST_SCREENCAPTURE=1` (window screencapture as before).
- `timeout` with no trap: the script went astray; `runs/<name>/session.log` lists every screen and the keys sent
  (with `SWOSTEST_SCREENCAPTURE=1`, `shots/final.png` the last screen).
- DOSBox-X windows open on screen and can take the focus: keys or a Cmd+Q meant for another application can end a
  run (`DOSBox-X ended: ...` in session.log); `SWOSTEST_NOEXIT=1` keeps DOSBox-X at the DOS prompt when the game
  exits to DOS, so its message stays on screen.
- `DOSBox-X ended: exit code 0` after a few minutes of a long run (fixed 2026-10-15): DOSBox-X's `-time-limit` counts
  EMULATED seconds; the old 14400 ran out after ~4.5 real minutes in turbo. Keep it huge (the runner kills DOSBox-X).
- `MEMDUMPBIN ...: no file`: the debugger lost a typed command (the dump is retried 3 times; if it still fails, DOSBox
  probably died: see `debugger.raw`).
- Breakpoints (`Session.bp`, `SWOSTEST_BP`) need `CORE=normal` (the dynamic core does not re-check translated code).
- Never run `config -wcd` inside DOSBox-X: it overwrote the user's DOSBox-X preferences once.
- `SWOSTEST_UI=fr` / `de` full seasons stuck at the season end's 'TERMINER LA SAISON' / 'SAISON BEENDEN' until
  2026-10-20: the label map (tools/swostest_lang.json) had no FINISCI STAGIONE for them; added (FR / DE seasons with
  save now pass). A season loop that sticks on a menu in another language: look for its label in that map first.
- Country names in another language's exe: the harness maps the labels it knows (swostest_lang.json, the 1996-97
  menus) back to Italian, so a 1996-97 country keeps its Italian name in `W8485_TEAM` (BRASILE in the EN exe), while a
  world-only one needs that language's name (NEW ZEALAND, NOUV. ZELANDE, NEUSEELAND: the pack's `button_names`).
- A scenario that PASSes here and FAILs on the second Mac (remote_run.sh) with a scenario-built exe: compare the two
  builds (`md5` of `ITALIAN.EXE` and `DATA/*`). Since 2026-10-30 they are byte-identical for one commit + env:
  - every build writes `INPUTS.txt` (the files of `~/swos-mod/{internal,c,orig,ref}` it read, sha1 + size + time, and
    the dirs it listed); a build whose inputs changed (or one without the file) is not reused, the key moves on;
  - `tools/cobj.py` keeps every C object it compiles in `internal/swostest/cobj/<key>.o`; with `COBJ_REF=1` (set by
    remote_run.sh on the server) the build takes this Mac's object instead of compiling: the server's Apple clang 15
    makes other code than clang 21 here (gplay.c 901 bytes longer, the exe one page longer). An object missing there
    is compiled locally with a `COBJ WARNING` / `BUILD WARNING`, and that build (`builds/<name>-nonref-<key>`) is
    never reused;
  - remote_run.sh first pre-builds the scenarios here (`SWOSTEST_BUILD_ONLY=1`: each stops at its first game start,
    `BUILT <name>`; log in `internal/swostest/remote/.prebuild/<RUNSNAME>.log`), then syncs those builds' inputs and
    the objects to the server. `REMOTE_PREBUILD=0` skips it (then the server builds from its own copies, as before).
    A build made after a scenario's first game start is not pre-built: it gets the warning above.

## Breaking a busy game (Session.sample)

The harness pauses only at the in-exe stub's int 3 (the game asking for a key). A game that runs on without asking -
a busy loop, an endless draw, a slow season end - only ever shows as 'timeout'. `Session.sample(keys, secs)` breaks
it: it sends the keys with a breakpoint on the timer interrupt (`BPINT 8`, every tick, ~18 / s), records each tick's
EIP (obj1 offset) and runs on, for `secs` seconds.

- Returns `(hist, result)`: `hist` = `{obj1 offset: ticks}`, the session log gets a `SAMPLE obj1+..:n` line (top 12).
  `result.outcome` is 'dump' when the game reached our pause first (no hang: the ticks ended there), else 'trap' at
  the last tick with a full MEMDUMP.BIN (pseudo registers: D0 at obj2+0x315B7 ... in the original layout) for the
  post-mortem.
- The ticks slow the game ~10x: read it as a histogram (where the time goes - I/O vs compute for Davide's season-end
  profiling), not as a timing. CORE=normal gives exact EIPs. The timer breakpoint is removed afterwards and the int 3
  one re-armed, so the session goes on (a 'trap' result: as after any trap).
- Use it from a scenario's W84_HOOK at the screen before the step that hangs: navigate to the entry, then
  `hist, r = s.sample('fire dump:3', 25)` instead of the press. Map offsets to routines with ref/swos.asm (obj1
  offset + 0x101AC ~ the cseg label in most of the code: check a known site first).
- First use (2026-10-22, NZ championship, 4.0.1): the 10th match day's 25 s were spent in DrawChar /
  ConvertSpriteColors / FlipInMenu - an endless menu draw, not a fixtures loop.

## Host tests (tools/hosttest, 4.0.5 rc20+): the exe's code in an emulator, from a real snapshot
For logic bugs, seconds instead of a career run. Unicorn (x86) in internal/hosttest/.venv (`python3 -m venv` +
`pip install unicorn`, not the system Python); `python3 tools/hosttest/run.py [-k name]` re-runs itself there.
1. Build with symbols: `HOSTTEST_SYMS=1` on any build (patch.py writes ITALIAN.syms.json next to the exe: every
   module's LABELS / SYMS / C symbols, `[obj, offset]`; obj 0 = an asm label's obj1 offset). The exe is unchanged.
2. Fixtures: `python3 tools/hosttest/snapshot.py BUILD_DIR module.label OUT_DIR [--car SAVE] [--team PATH]`: a career
   (world_uru_nacional / world8485) with a breakpoint at the label; every hit dumps the whole memory (32 MB) + the obj
   bases (internal/hosttest/fixtures/<name>/<k>.bin / .json; private, not in the repo). CORE=normal.
3. Tests: tools/hosttest/tests/test_*.py, functions test_*() -> (ok, message). emu.Machine(dir, k) loads a snapshot
   (flat GDT with the game's selectors 160h / 168h), m.call('module.label') runs a routine to its return (a sentinel),
   m.read / u8 / u16 / u32 / write by symbol or linear address; INTs stop the run (InterruptError with the EIP) unless
   m.on_int[n] handles them; m.watch = [(lo, hi)] makes writes there StrayWrite (catches stray writes).
First test (test_conti): conti.py ct_prep must never put the career club's next tie in a week already reached -
the control build (rc19, before adce370) FAILS on the Libertadores q2 after a won q1 (week 56 built at week 59), the
fixed one PASSES (60). Builds c/HT19 / c/HT20 (HT_CONTROL / HT_FIX).
New code on old fixtures: `Machine(dir, k, code_from=BUILD_DIR)` relocates that build's obj1 / obj2 onto the snapshot
(LE fixups at the snapshot's bases; the snapshot's run.EXE = the exe as run, with the harness's page) and keeps the
state: bytes the game changed at run time stay; a changed byte of a named label that moved goes to its new place;
anything else = LayoutChanged (re-snapshot). test_ct_prep_overlay: the rc19 q2 snapshot + the fixed code -> week 60.
Fixtures from ANY world8485-based run (e.g. a sweep config that reproduces a bug): add `HT_SNAP_LABELS=module.label,..`
(+ `HT_SNAP_OUT`, `HT_SNAP_WEEKMIN`, `HT_SNAP_MAX`) and point W8485_BUILD / the scenario's build at a HOSTTEST_SYMS
build of the same exe (e.g. c/HT19R = c/REL405rc19 byte for byte, with ITALIAN.syms.json). Scenario `ht_snapshot`
(HT_BUILD, HT_LABELS, HT_NAME, HT_SCEN, HT_TEAM...) does the same with the dumps in its run dir (remote_run brings them back).
Engine step H (PLAN §19.3, 4.0.6): test_hooks.py = one Tier B test per bridge hook of PLAN §3.6 on today's code, the
contract the engine keeps when it takes a hook over. Fixtures h_uru (a NACIONAL career, two seasons) and h_uru_load
(its season-2 load) from c/HTI4 (406-i4 b0c5e07, release recipe + HOSTTEST_SYMS=1): gp_draw, gp_cap, gp_end,
w_season_end, ct_daily, ct_prep, lp_sort, save_trailer, load_trailer. Each call returns, is deterministic (same pages on
a second run), < 1 s, and writes only pages of its golden footprint (footprint.json; `HT_REGOLD=1` rewrites it after a
deliberate change). test_save_bytes: the emulated save_trailer writes the game's own .CAR byte for byte;
test_finish_season_flag: the game's next-day scan (cseg_8EC2B) says FINISH SEASON exactly when no career-club day is
left. test_rules_lib.py (Tier A): the rules library's own `make test` (HT_ENGINE checkout). Emulator: the VGA status
port 3DAh toggles (vsync waits), INT 21h create / write into memory (m.files_written, `dos_files(root, writes=True)`),
the write hook only while m.watch has ranges. snapshot.py: --max per label; a trailer.load_* label arms before the
load's key (W84_HOOK.pre_load). Open for step P: save(load(x)) differs from x in the trailer (5083 of 16192 B after the
after-load callbacks) - classify it before P's persistence work.
Option C P1 (4.0.6, the competition screens' builder, tools/ctgame.c): `world_cgame_self` (DOSBox) - a FLAMENGO
career on CONTI_FORCE=lib:q1 + CONTI_KOWIN + CONTI_CGTEST: after every contest conti's ct_build puts in slot 3 (the
q1 / q2 / q3 ties, the group stage) cg_selftest rebuilds it with the view's builder into the scratch and compares it
with slot 3 byte for byte (CG_T through the 'CGTRPTR' block: builds, mismatches, first diff, cache count before /
after). CG_FILL=1 builds with CG_FILL_TEST=5A (the scratch filled with 5Ah first, as DOS/4GW may leave it). CG_S1: a
cached season-1 save. Tier B test_ctgame.py on fixtures cg_uru (`snapshot.py c/HTcg1/SWOS conti.ct_daily cg_uru
--car h_uru/save_s1.CAR --max 8 --every 6`: one ct_daily hit in 6 of NACIONAL's season 2): cg_replay changes no
conti state and its goals give CT_OUT's results (conti.grec_check, also CONTI_TEST_GREC=1 in `conti.py --test`);
cg_build of every drawn round (and a first tie) deterministic, < 1 s, work area + D0..A6 put back, pages outside the
scratch within the golden footprint; a full team cache -> 0, CG_ERR 4, nothing written. emu.Machine.base3: obj3 from
an obj1 pointer (run.EXE's fixups). snapshot.py --every N.

Option C P2 (the save guards: ctgame.c cg_open / cg_close / cg_guard, CG_G through the 'CGTRPTR' block's 4th dword):
`world_cgame_guard` (DOSBox, the GO/NO-GO 2 gate) - one season-1 save (CGG_S1, else season 1 on A), its season 2
played on CGG_A (the release recipe) and on CGG_B (the same + CONTI_CGVIEW=1: conti's ct_daily opens one drawn conti
round a day, does to it what the game's view does - cseg_8B71C / cseg_8B7EA - and closes it): the two season-2
.CARs byte-identical, B's CG_G with views opened, no bad sum, no sticky fallback, no failed build (CGG_TEAM, default
HAMRUN SPARTANS). On the release recipe per language: the language's exe as ITALIAN.EXE in c/CGG_<A|B>_<lang>/SWOS,
SWOSTEST_UI=<lang>. Tier B (test_ctgame.py, fixtures with ct_daily + save_trailer hits): test_cg_guard_close (the
saved state - fixed part, the cache's N records, CG_GTAB's kept and summed ranges, work area, D0..A6 - byte-identical
after open + a view's changes + close, also with the scratch 5Ah first; a saved byte changed while open -> bad sum,
sticky, the next open refused: E_GUARD 7), test_cg_guard_daily / test_cg_guard_save (a view left open at ct_daily /
save_trailer: closed first - CG_G trips 1 - and the day's state / the .CAR byte-identical to the one with no view).
What a build writes in the saved state was measured on 330 builds (the unicorn write hook): the cache count,
careerFileBuffer + 16ABCh, statespec's ST_RANK (an 'EN' item: a type-2 init sorts its table through lp36), lib97's
NC_DW; the rest (team file buffer + its name and file globals, careerworld WTPHYS / w_tcache, 32E15's club flags,
gplay's GP_SLT) is not saved and the game sets it before it reads it.

Option C P3 (the rounds in the game's own competition screen: ctview's rounds menu -> ctgame cg_view -> cseg_37B74 ->
cg_close): `world_cgame_view` (DOSBox) - on world_contiview's build and a season-2 save (CV_BUILD, CV_S2; a
mid-season one: W8485_MIDTEXT='PREMIER:31' on an ARSENAL season 2 from cv_s2): every confederation's rounds menu
(labels in the menu font, <= 144 px), each visible round opened (shot cgv_<k>_<j>; its visible texts in the font and
within their boxes - the game's hidden texts, FR's tooltips, aside), a group stage's PASSA legend pressed, ESCI back
to the rounds menu with its links (cr_init again: the game puts the menu back from its packed data, links FF),
RIEPILOGO and back; CT_SEG / CT_ED byte-identical around every view. Per language: SWOSTEST_UI=<lang> + the
language's exe as ITALIAN.EXE (the IT save is fine: the screens' names come from the exe). Tier B test_cg_view
(HT_CODE=<a newer HOSTTEST_SYMS build>: its code over the fixture's snapshots - emu.overlay now covers obj3; HT_CG
picks the fixture): every drawn round at weeks mo+1, mo+4, 250 - each tie's winner flag = conti's result, the
legs' scores the replay's, a level aggregate only with away goals / pens; a group's P = W+D+L, pts = 3W+D, the
matches played = the record's at 250, an empty slot (rows from n: a group short of a club) last in its order and
playing nothing; the close leaves the saved state byte-identical; deterministic. snapshot.py takes one hit per run
(the counter keeps the first week's hits): one run per week with --week-min (fixtures cg_w60, cg_w106).
