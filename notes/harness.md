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
7. **Dirty RAM** (4.0.6, Davide's I8 two-row noise on the MiSTer z486): DOSBox-X starts with zeroed RAM.
   `SWOSTEST_DIRTY=5A` runs tools/dirty/DIRTY.COM before the game. It fills free conventional memory above its own
   64 KB and every free XMS block with that byte, and prints `DIRTY 5A: conv .. para, xms .. KB in .. blocks, found
   xx` into the run's DIRTY.TXT, where `found` is the block's byte before the fill. It also sets `ems=false`
   (`SWOSTEST_DIRTY_EMS=1` keeps EMS), so DOS/4GW takes XMS.
   - Measured on REL401rc3 at the first pause: 16 / 30 MB and the game's free heap hold 5Ah. The game's malloc'd
     buffers start dirty, as on real hardware.
   - What it does NOT cover: an object's BSS tail (obj2 +0xd5000.., obj3's CG_BSS) still reads 00, because DOS/4GW
     under DOSBox-X zero-fills it at load. So tail_zero's MiSTer case (REL401rc3 / 402b4 without the stub) still
     passes shirt_numbers dirty: prove BSS clearing with the in-exe fills (TAILZERO_FILL_TEST, CG_FILL_TEST) instead.
   - 4.0.6 (the I10o MiSTer panel hunt): tailzero's stub clears obj3's tail too (tail_zero checks both parts, fill 0).
     The fills take 2 hex digits (that byte) or 8 (a dword, bytes that differ as real leftovers do):
     TAILZERO_FILL_TEST = obj2's tail, TAILZERO_FILL3_TEST = obj3's (defaults to the first). A filled build is a
     test build: tail_zero FAILs on it (the negative control). E.g. TAILZERO_FILL3_TEST=A55AC33C on the I10o layout:
     the match panel (panelprobe2.py, INTER v MONZA, kick-off + two poked goals) stays clean in DOSBox-X.

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
| kbfirst | 4.0.6 fix A (tools/kbfirst.py, Davide 04/11): a held keyboard direction beats a stick that reads off centre. No joystick (SWOSTEST_JOY=none: ReadGamePort counts g_numLoopsJoy1), the factory SETUP.DAT, then the device poked 3 and stick 1 read as held UP (numLoops 166, centre 166 / 300, min y 200: a clipped full up, no divide). DOWN held = keyboardControlFlags poked 2 (the feeder's key is released before the dump and the stick takes the cursor straight back). Menu: DOWN moves the cursor down; SWOS++'s mark poked: it stays (off there). Match (friendly, HAMBURG human = player 1): pl1Direction / the team's direction 0 -> 4, the controlled player's y grows. On the 406-i8 base it FAILs (menu y 41 -> 41, the player goes up): the original behaviour (~1.5 min) |
| xtra_cpu_refill | 4.0.6 the CPU replacements switch (tools/cpurefill.py, Davide 03/11 after Nicola's MILAN purchases) on SWOSTEST_BUILD (the release recipe, World 2026-27): a new INTER career; TRASFERIMENTI > ACQUISTA GIOCATORE: the switch (entry 8, right of ESCI) 'RIMP. CPU: INVENTATI', cr_mode 0 (the obj3 'CRFL' mark); fire -> 'RIMP. CPU: DALLA ROSA', 1. MILAN's best extra for place 11 poked onto the home market; our balance poked to 100M before each purchase (the offer is capped at it, MILAN refuses one 20% under its price); CAMARDA (place 11, A) bought through ACQ. ALTRO GIOCAT. NAZION. > SERIE A > MILAN: the CPU change list's last entry (careerForeignMarketPlayers: MILAN, index 10) = `cpurefill_pick`'s NEXT pick (the Python twin of the rule; the market one skipped), XS lists him, cr_count 1, CAMARDA in our squad; MAIGNAN (place 1, P): the goalkeeper extra. Saved (CRON.CAR), reloaded: cr_mode 1, the change list identical, MILAN's record copies in memory hold both. Then a NEW career (CARRIERA > ABBANDONA): cr_mode 0, the switch INVENTATI, CAMARDA bought -> an invented player (not one of MILAN's extras; usually a name in no data file, `cpurefill_names`: the game's generator may take first name and surname from the same player), no new XS entry, cr_count unchanged. Shots: menu_invented / menu_squad, MILAN's pages before / after / reload / invented_after | ~3 min |
| xtra_cpu_refill_labels | 4.0.6 the switch's labels, SWOSTEST_UI's exe (it / en / fr / de: SWOSTEST_BUILD a copy whose ITALIAN.EXE is that language's exe): INTER career, ACQUISTA GIOCATORE: entry 8 visible, cpurefill.TEXTS[UI] for both values, the small font's characters, <= the button's 121 px - 8, on ESCI's row right of it; shots menu_<lang>_0 / _1; it only: a real 1996-97 JUVENTUS career and a Europe 1984-85 LIVERPOOL one: the switch hidden | ~2 min |
| xtra_cpu_refill_spp | 4.0.6 the switch under SWOS++ 1.9.2.2 (SWOSTEST_UI=en, SWOSPP_BUILD = SWOSTEST_BUILD = a copy whose ITALIAN.EXE is the English release exe): INTER career, TRANSFERS > BUY PLAYER: entry 8 'CPU REPL.: INVENTED', visible; fire -> 'CPU REPL.: FROM SQUAD', cr_mode 1. No purchase (under SWOS++'s timer feed the offer's fire+right raises do not register; the promotion is the same code: xtra_cpu_refill). Shots spp_menu_0 / _1 | ~1 min |
| engine_obj4 | engine step O (CONVENTIONS 23bis): obj4 = the engine's object in the exe; DOS/4GW loads it: its header found in memory (Result.base4: 'SWOS-ENG' + self pointer), swe_init / arena / SWE_STATE pointers relocated to obj4's base, version as built, main menu up. SWOSTEST_UI=en: the same under SWOS++ 1.9.2.2 (swospp_on). Shots menu_dos4gw / menu_swospp | ~1 min |
| xtra_squad_views | a club's full squad in the squad screen (XTRA30_BUILD): VISUALIZZA MONDO > ... > SERIE A > STAT > VIS. SQUADRE > MILAN: page 1 = 16 + button PAG. SUCC. (entry 6, left of ESCI), page 2 = extras (shots), record bytes unchanged, a club with a zeroed block (PARMA) no button, the same through VISUAL. COMPETIZ. (LIGORNA), own squad afterwards normal | ~1 min |
| xtra_season | XTRA1.CAR (HAMBURG, 25) played to the season end by results (no sacking when the harness has nosack_off), next season saved: at most 32 players, the real extras still there, wages recomputed at the season start = 66% of the twins' (twins' bytes 25-37 copied in at the season end) | ~4 min |
| world_split_single | world 2026-27 (private world5tm) with the SPLITS keys (build world_split; SPLIT_BUILD reuses one): two seasons at ST. MIRREN, Scotland 33 + 5 (balance): days, matches, groups in place order, points, the career club's post-split fixtures (its group, home by the balance rule) | ~40 min |
| world_split_double | the same build at HARTBERG: Austria 22 + 10 (double round after the split) | ~40 min |
| world_split_halved | the same build at BOTOSANI: Romania 30 + 10 (6 double, 10 single, points halved rounded up, 'points before rounding' first) | ~35 min |
| world_split_h2h | the same build at PETROCUB: Moldova 21 + 10 (top 6 from half their head-to-head points; 7th-8th done) | ~40 min |
| world_split_reverse3 / _odd / _three / _none / _stages | the same build kind (all SPLITS keys) at BANGOR (NIR, reverse3), LOKOMOTIV SOFIA (Bulgaria, odd groups and rest days), VOLOS (Greece), PARDUBICE (Czech middle group stops), HIBERNIANS (Malta, 3 stages: reset, kept Opening table) | ~60 min each |
| world_odd_league | an odd-size division (ODD_BUILD, default the newest builds/w2627odd-*; ODD_TEAM, ODD_CLUBS): a season at AUCKLAND CITY (NZ 11): 22 days, 20 matches each, the next season started | ~40 min |
| world_ns | two career worlds in one exe, each with its own country namespace (build: 1984-85 + a 20-country 2025-26 test world from the private SWOS 2020 converter, FIRST_FILE=112 so its files 112-131 reuse 1984-85 numbers; XTRA hook): new careers at AEK Larnaca 2025-26 and Valletta 1984-85 (after a detour into world 5's club list) = the same team word 0x83, each with its own world's extras (XTRA.131 / XTW5.131); each save loaded after the other world's in one session: VIEW WORLD lists the right world (INGHILTERRA / ENGLAND), the season played to the end and saved, checkw1 | ~20 min |
| menu_levels_cursor | 4.0.6 (menulevels setsel, Regia 04/11): World 2026-27 (GRPA_BUILD, default builds/w2627-latest), CARRIERA 2026-27 -> SCEGLI SQUADRA -> ITALIA: SERIE D opens with the cursor on SERIE D GIRONE A, ESCI -> on SERIE D, SERIE C -> on SERIE C GIRONE A, ESCI -> on SERIE C; a career at CELLE VARAZZE, its VISUALIZZA MONDO -> ITALIA -> SERIE D: on GIRONE A, ESCI -> on SERIE D (ml_pick2); shots groups / vw_groups; IT and SWOSTEST_UI=en. Before the fix (REL406i10l): the cursor on GIRONE D / C (the levels' saved index) | ~1 min |
| menu_numbers | 3.3.4: tactics editor (MOD. TATTICA > UTN A; English MENU_PATH='EDIT TACTICS,USER_A') with LEICESTER poked to 17..32: the pitch's little numbers 12..99 are menunum's sprites 1620.., each = tens + 1 px + units of the menu's own digits (pixel-exact); screenshot | ~20 s |
| (every bench scenario) save_under | 4.0.6 MiSTer panel H1 (suroom.py): bench_sub, with the subs menu open, reads the game's save-under stack (DrawRectangle saves the back buffer under each rectangle into one region of its DOS block; the restore leaves the entry after the last one, so the table's highest end = the high-water) and FAILs when it passes the region (the live pointers [0x31684] - [0x31694] IT: 69 632 B in the original layout, 102 400 B with suroom (+32 KB)). Measured 05/11: original rows 63 432 B, formwide 70 152-70 440 B, formwide + bstrip's boxes 79 488 B; without suroom the formwide build FAILs ('save-under overflow'), the overflow wrote the next area (a 21.9 KB backup copy) and garbled the MiSTer's bottom panel after a substitution. BENCH_PANEL=1: 14 shots (1.5 s apart) after the change (<tag>panelNN). | - |
| bench_world | 4.1 panchina blocks 1-3 (tools/benchx.py): World 2026-27 build (BENCH_BUILD), a new player-coach career at CELLE VARAZZE (30 players), bx_bench poked to 15, the first match played for real ('- PARTITA -' with nop_league_int3, GIOCA PARTITA): gameMaxSubstitutes 15, the club's in-match team 26 named (11 + 15), the opponent 16 + 10 empty places, the name sprites of places 17..26 (1910.. / 1920..: 112 x 6, drawn), the bench list seen on screen; the bench cursor down to place 21 (BENCH_SUB, 12..26), down, up 6, down again (4.0.6 long dugouts: no window, bx_win stays 0) and `dugout_check` (4.0.6 two-row dugouts, Davide 03/11, dugout.py): benchY 373 (the top dugout, grown upwards: 389 - 16 x ADD) / 485, the camera at the halfway line (g_cameraY = CAM_MID - 100 = 350 +-10: both dugouts in one frame), `dugout_frame` (Davide 03/11): both dugouts whole on the screen (dugout.INK, roof cap to steps, y 352..547) and the match clock (`clock_box`: currentTimeSprite as DrawSprites places it) on the screen and off both dugouts (bx_clock: top right with the bench open), the frame = the loaded set's map (4.1 41-vandug `pitch_maps`: PITCHA-E with the long bench, `vd_check` first) but the bench sprites (the pitch found by fit), `dugout_rows`: per row (back = the coach + places 1..7 in x 27..35, front = places 8..15 in x 36..44, 3 px lower) the seated sprites end DUG_SPR (17) rows below the row's last filled seat (every place seated; BENCH_INJ's left-out places are empty seats), the other bench read in the same frame; BENCH_SUB 21 = a front-row place (the mirrored arrow), 18 = the last back-row place (exit e: he stands up in front of the front row); shot dugout; before every bench call `keeper_let_go` plays on while a keeper holds the ball (gameState 3, bench_vars GSTATE: the game's bench takes no cursor key then and the match stands still with the bench open; 03/11 tr2 runs called it on a top goal kick every time); `cam_settle` after every bench call: the bench is drawn and takes keys only once the camera is at the dugout, ~0.5 s later than with the old dugout when the ball is near the halfway line), the change made (NumSubs + 1), bx_ord = one swap in that team's half once he is on, the other half untouched; a goal poked into the record of the player who went off (now at place 21) reaches his squad record after the match; played to the career menu. SWOSTEST_MEMSIZE=8: the same in the 16-colour mode (no bench-list pixel check, no formwide subs-menu check; the save-under guard counts entries instead of bytes: EGA_FillRectangle -> cseg_98EFD copies inside video memory and keeps only 16-byte entries, two tables of 256 swapped by EGAFlip, nothing in the DOS-block region; 05/11 on m1s6: 85 IT / 83 FR, VGA 79,664 B IT / 79,488 FR of 102,400). SU_SAMPLES=n: n more dumps with the subs menu open, the highest kept. BENCH_SQUAD=2: the long lists of SQUADRA, the pre-match screen and the tactics editor (box window, marked swap while the box scrolls; 4.0.6 Marco: the name rows never scroll - down on row 17 -> the game's next entry (`wrap_reach`: ESCI / GIOCA PARTITA / ANNULL.; 4.0.6 Marco / Davide 02/11, as the original game: on the pre-match screen the player / coach line, entry 6, then down PLAY MATCH, entry 9, up back to 6 and row 17; ESCI up and UTN A / C / E left -> 6 too; entry 6 hidden by a poke (a manager): row 17 down -> 9, up -> row 17, ESCI up / UTN left -> row 17), up on row 12 -> row 11, the window kept), IT and SWOSTEST_UI=en; BENCH_VIEW=1: ViewSquad (the box only, the name rows as the game); BENCH_SAMPLE=secs: each in-match bench-cursor key through sample() (BPINT 8): a dump that never comes back gives the obj1 EIPs (02/11: such stalls were DOSBox starved under load, ~12 timer ticks in 90 s, not a game hang) 16-colour mode (SWOSTEST_MEMSIZE=8): dugout_check checks benchY and the camera only (the screen is 4 bit planes, no linear frame); a frame no pitch map fits is kept as <tag>dugout_frame.bin. Bisect knobs: BENCH_RNG=<6 bytes hex> pins both random generators at the first bench call, BENCH_DIAG=1 logs camera / benchY / the bench gating words per call, BENCH_KEYHOLD=s the cursor key's hold. 03/11: the cursor that sometimes never moved (EGA on the dynamic core, the CD original too: ega_bench_cursor) = a game bug: coming from the top half, MoveCamera's step ((delta >> 2) x 0.25 px) is 0 at 1..3 px above its target, the camera never stands still (cameraCoordinatesValid 0) and BenchCheckControls skips the keys (CD exe: camera 346 for 349, VGA). benchx's bx_camlo snaps the camera onto its target (two-row T2): ega_bench_cursor PASS on the two-row build, seeds 010203040506 / a1b2c3d4e5f6, memsize 6 / 8. DUG_OPP=1: `opp_dugout_shot` = shot <h1/h2>_both_dugouts (both benches' rows in the one frame), the second half's from play-on step DUG_OPP_K (default 40) on BENCH_HIL=1 (4.0.6 replays): an instant replay saved as a highlights scene, after the match HIGHLIGHTS played (bench 15, the name sprites) and saved / reloaded as HILB15.HIL (bench and, 4.1, the long-art bit poked off first); 4.1 41-vandug `hil_art` on both playbacks: bit 15 in pitchNumberAndType / hilPitchNumber / the VDPL log and the frame = a PITCHA-E map (the long art from the replay's own header). | ~1-3 min 4.0.6 formwide (Marco's B2, fw_rows / fw_check): every row of the subs menu and the bench list (and oppo_list's pages) with the wide geometry measured on the frame (frame span 144, one background column each side of the card, the card's shadow 1 px from the face, the name / cross gap, the right frame gap); none under SWOS++ (its own rows: formwide's hooks keep the game's x while it runs); BENCH_FWPROBE=1 books starters 2 / 3 (yellow / red, Sprite.cards) and gives starters 2 / 4 a 0x20 injury record (a steady cross) before the subs-menu shot, so the card and cross columns are on it. | BENCH_SPP=1 (Regia 05/11: a SWOS++ smoke test, SWOSTEST_UI=en): SWOS++ 1.9.2.2 installed, keys from the timer; under it press() walks one tap at a time (key:0.3) and fires on a selection still there one pause later ('fire up:0.05': its UP overwrites the latched last key), a plain fire on a grouped level (ml_pick rebuilds the list at that depth with the cursor on the same index: the UP would move it), off a dead entry (ESCI) by down / up / down (Panchina's pgrp.py); the squad / tactics window checks are left to the plain run. 04/11 (Panchina, 406-sppm): no latched last key under SWOS++ (SWOSTEST_SPP_NOLATCH), keys held SPP_HOLD (20) timer ticks, the squad screen's PLAY MATCH fire held SPP_PM_HOLD (16): under SWOS++ the long-bench squad screen takes a fire only held >= ~12 ticks (0.17 s; 4.0.5 release ~20, 4.0.5 without benches ~6-8), a shorter one is missed (the old 10/10 START / STALL); the match is played (bench, a change, the goal poke) to the career menu; the line-ups pages / name sprites are info only under SWOS++. BENCH_SPP_LATCH=1: the old latched flow. Run it WITHOUT SWOSTEST_DIRTY (Regia 05/11): with DIRTY.COM the SWOS++ timer-fed menus miss the held fire (5A, 00, EMS kept: all stall; plain bench_world keeps the DIRTY coverage) - a DOSBox-X effect to confirm on Davide's MiSTer; and alone on a Mac (load-sensitive).
| ega_bench_cursor | 03/11: the 16-colour bench cursor stall, game or mod: EGA_BUILD (a game folder: c/ORIGCD/SWOS = the CD ISO as it is, or a release's SWOS), DOSBox-X memsize EGA_MEMSIZE (default 8; the CD exe needs 6 or less to go to 16 colours; a release exe exits at once with 6), friendly HAMBURG v SCHALKE, both random generators pinned at kick-off (EGA_SEED), up to 10 bench calls, 3 x down on an open bench (0xb16be = 30), the cursor read. 03/11: CD original memsize 6 seeds 010203040506 / a1b2c3d4e5f6 and memsize 5 seed 0: the cursor never moves (seed 0 at 6: moves); I4 seed 0: moves. Before each call `keeper_let_go` (as bench_sub: a bench opened while a keeper holds the ball takes no key, the game's rule); each call's gameState listed. Two-row tr3 (03/11 evening): memsize 8 seeds 010203040506 / a1b2c3d4e5f6 PASS 4.1 (Integratore 08/11): each bench key only at a stoppage (gameState not 100: played on up to 60 dumps first) - the seed is poked at a wall-clock moment after the kick-off (turbo, cycles=max), so the match flow varies with the host's load (REL41s31 seed 0 gave two flows; a VD41rel run under load met no stoppage in 10 fixed-time keys, kept as internal/swostest/remote/vd41_egac); the message lists gameState at the key and after. | ~1 min |
| fin_statement | 4.0.6 finance's row on the in-season statement (tools/finance.py fi_stmt, Davide on the MiSTer: the income was credited with no row): SWOSTEST_BUILD (SWOSTEST_UI it / en / fr / de, that language's exe as ITALIAN.EXE); a new JUVENTUS career and the old save JUVEFIX3.CAR, each to the career menu after one match charge, ANDAMENTO CLUB: the label `finance.ROW[lang]` visible, font characters, within its entry, label rows apart and above CONTINUA; the row = the sponsorship x the exe's currency (lire x 2); old + total = new; the shown rows + the hidden D6B88 / bonuses = the total; screenshots `statement_new` / `statement_old` | ~1 min |
| ffp_season | 4.0.6 financial fair play (tools/ffp.py, Marco / Davide 04-05/11): a new ST. ANDREWS career (Malta, 1984-85), FFP_MODES over / off / real / oldsave: over = an FFP_FORCE=over build (the limit 0): ANDAMENTO CLUB's row (entry 22 ffp.RATIO[lang], '--' before a season; entry 23 the game's ON) above the old balance; season 1 played; at the season start the memo ffp.MEMO[lang] (raw bytes: '£', umlauts; within its rows; small font + the game's memo characters), FF_BLOCK 1, FF_FINE = half the season-end wage bill (thousands), the TV wage share (FF_TVW) counted and reset, the statement's fine row (9 / 19) and old + total = new, ACQUISTA GIOCATORE = the game's message 1; off = the switch turned OFF on ANDAMENTO CLUB (UP from CONTINUA): nothing; real = SWOSTEST_BUILD, the 40 % limit; oldsave = JUVE2F loads OFF. SWOSTEST_UI it / en / fr / de | ~4 min |
| ffp_star | 4.0.6 FFP at a big club (Davide's check): an OFFER_FORCE build of the World 2026-27 (W2627REL_DATA), a REAL MADRID career, FFP_STAR (default 1,3,6; 0 = baseline) purchases of the dearest player in ACQ. ALTRO GIOCAT. NAZION. > LALIGA > BARCELONA's list (each row's info line read; the bank poked to 500 M and put back), season 1, CONTINUA CARRIERA: the season-end W, I (FF_IPREV), over <=> FF_BLOCK, FF_FINE = half the excess; one star never sanctioned. Measured 05/11 (40 %): 0 31.9 %, 1 37.5 %, 3 40.6 % (block, fine 0.12 M) | ~5 min a case |
| stadium_versus | 4.0.6 (Davide 02/11) the stadium name on the versus screen (stadium.py), STADIUM_BUILD or the harness build (CORE=normal) + a test DATA\\STADTEAM.DAT: friendlies INTER v MILAN, FIORENTINA v ROMA (48 chars: the widest World 2026-27 name, 254 px), JUVENTUS v LAZIO (no record), INTER v MILAN from a version-2 file (33-byte names: still read); IT / EN only (the friendly menu walk); pairs of the same case because RandomlySwapTeams picks the home side; a breakpoint after VersusInit's fade-in: stadium_vs_check - the name (small font) in the text ink colours only, stadium.GAP rows under the bars' last row, centred on the title (+-1), one text line, inside the screen; no name: no title ink under the bars | ~3 min |
| stadium_world | 4.0.6 stadium names per team-file namespace (STADIUM_BUILD / BENCH_BUILD, release recipe): World 2026-27 career at ROMA, training game: STADTMW5.DAT's name on the versus screen (stadium_vs_check), STADTEAM.DAT's decoy for the same (file, ordinal) ignored | ~1 min |
| stadium_venues | 4.0.6 neutral finals (STADIUM_BUILD, a release build with its own STADTMW5.DAT v2): World 2026-27 career at ROMA, training game; a breakpoint at st_find's end puts each case's strings into gameName / gameRound (+ currentSeasonShowing) and sets EIP back to st_find: every venue row (all 4 languages) -> its venue before the home club, wrong season / cut competition / other round -> the club, the game's '*' padding ends a string; the real strings back -> the club's name on the versus screen (stadium_vs_check; the tour: STADIUM_SHOW=k case k's venue instead, STADIUM_SHOWNAME=name that name poked into st_name; any SWOSTEST_UI incl. fr / de), the line-ups after it. All cases in one match | ~2 min |
| stadium_clublist | 4.0.6 the stadium club list (tools/stadium_tmw5_clubs.csv) against a release build's World 2026-27 data (STADIUM_BUILD, else W2627FULL): every row is that club in DATA\\TMW5.nnn (stadium.unmatched = 0), every name (clubs, venues) 1..48 characters of the game charset and at most 318 px in the small font (4.0.6 full names), DATA\\STADTMW5.DAT is there. The build itself only drops a row that is not that club (old-save builds on the released 4.0's data, world_ns's partial world) and prints the count. No DOSBox | 0 s |
| stadium_nofile | 4.0.6 (Davide 02/11: names only in World 2026-27): the build ships no DATA\\STADTEAM.DAT; friendlies INTER v MILAN with it absent, empty (0 bytes), version 1: st_find ran, no name, no title ink under the bars, the match goes on | ~3 min |
| bench_cup | 4.0.5 real benches per competition (bench2627.json + build-time fallbacks): a World 2026-27 career at RANGERS (BENCH_BUILD, BENCH_CUP_TEAM), season 1 (world8485, results only); benchx's lookup at every pre-match screen (bx_lkname / bx_lkres, W8485_HEX on obj1) logged: BENCH_CUP_WANT ('SCOZIA SCOTTISH PREMIERSHIP=9:5;SCOZIA SCOTTISH CUP=9:5') seen, no title it plays left at 5 (its UEFA qualifying tie included). bench_world: BENCH_TITLE = the title looked up at the kick-off | ~15 min |
| bench_friendly | 4.0.6 (Regia / Davide 05/11) the long bench in World 2026-27 friendlies (benchx bx_frset / bx_frpm): BENCH_FR=<cases> (default all): 'mixed' CELLE VARAZZE (Serie D, 9) - REAL MADRID (LaLiga, 12) -> 12:5, 'same' two Serie D clubs -> 9:5, 'seriea' INTER - MILAN -> 15:5 + bench_sub from place 21 (save-under guard), 'diy' = mixed with g_gameType poked 1, 'nat' ITALY - SPAIN -> the game's 2 from 5, '9697' a 1996-97 friendly -> 2 from 5; per case the pre-match bench (bx_lkres), at the kick-off gameMin/MaxSubstitutes and both in-match teams (11 + bench places: the record's 16 + the club's XTRA block, the rest empty). (B, Davide 05/11) 'mixed' / 'diy' (FR_B) also `fr_order` on the pre-match screen: the club's own order (benchx fr_find, mark 'FRTB': places 0..15 = TeamFile.playerNumbers, 16.. its XTRA players), numPlayersToShowInMenu = 16 + n, row 17 + the box shown, the box window 1..n-1, 0; a swap of row 17 (place 17) with row 2: the two places swapped, playerNumbers = the record's players in the new order (never an index >= 16), with place 12's record player poked injured (after the swap the record's 11th, on the bench on the screen) PLAY MATCH stays shown (benchx fr_a2 / fr_a1: the checks read the order; c/LB4 without them FAILs); `fr_tactics`: MOD. TATTICA (fire through the choose-tactics list), editTacticsNumPlayers = 16 + n, swap row 17 <-> row 3 and back; at the kick-off the XTRA player among the human club's starters (PlayerInfo.playerIndex), the record player he replaced on the bench. 'diycup' a real DIY cup (COMPET. PERSONAL. > COPPA, one round), '9697w' INTER - MILAN of 1996-97 picked in the 2026-27 picker -> 2 from 5 (SWE_W27 builds only, else SKIP). BENCH_BUILD = a World 2026-27 build; BENCH_SPP=1 (SWOSTEST_UI=en, no SWOSTEST_DIRTY; run BENCH_FR=mixed,diy): a smoke test under SWOS++ 1.9.2.2 - the pre-match bench, named:used and both in-match teams, no B swaps (as bench_world's); bench_world's unlatched feed, every menu step a press() tap, a fire carried into the next menu skips that step, the DIY type screen's keys held 8 ticks (20 repeat there), PLAY MATCH held 24 / 36 / 48 ticks until it goes (36 on c/LB7en); not diycup: SWOS++'s DIY cup ROUNDS never gives 1. seriea's bench_sub calls the human's own bench (bench_sub human_key: PgDn the top team's, PgUp the bottom's, from TeamGeneralInfo.playerNumber; up to 40 calls, the cursor tried once g_inSubstitutesMenu says it is open - the game clears a bench call every frame of play, so a key lands only while play is stopped); 'seriea_top' = seriea with the human made the top team (playerNumber poked at the kick-off; BENCH_TOP=1 does the same in seriea). BENCH_DIAG: per call bench1Called / bench2Called / g_inSubstitutesMenu, shots, both TeamGeneralInfos (player / coach numbers, club, teamNumber) 4.1 (41-vandug, Marco): at every case's kick-off `vd_check` - bit 15 of pitchNumberAndType and of hilPitchNumber = gameMaxSubstitutes > 5, and benchx vd_pitch's log 'VDPL' (obj3: GMAX as ReadPitchFile ran, the bit, the load count) the same: the timing proven (the kick-off's bench, not the 5 before it) - and the kick-off frame fitted to the chosen set (`pitch_fit` over `pitch_maps`: PITCHA-E for a long bench, the game's PITCH1-5 for 5: '9697', 'nat', 'kick9697'); a bench of 5 in `dugout_check` -> `van_dugout`: benchY 389 / 485, camera y 349 +-10 (the game's 449 destination; bx_camlo's snap kept outside training), the clock not moved by bx_clock, the frame = a PITCH1-5 map. | ~1-8 min |
| bench_tap | 4.1 (Regia 06/11) the joypad's bench call (a stick / pad has no PgUp / PgDn; MiSTer players): the 'seriea' friendly (INTER - MILAN, BENCH_BUILD), both sides in turn - the human club poked the top team (playerNumber 1: player 1's tap branch), then the bottom one (player 2's). Per side and TAP_GRID (hold, gap) = 4/4 and 10/8 feeder calls: 2 openings by DOWN tapped 3 x (BenchCheckControls: the 1st tap sets subsPrevPl1/2Direction, the 2nd and 3rd count subsPl1/2TapCount to 2), no dump inside the taps; g_inSubstitutesMenu set and benchTeam (`bench_team`) = the human's TeamGeneralInfo. A try the taps do not open is checked at once with the human's own bench key: it opens -> FAIL (the taps missed a stopped moment), it does not -> play on. After each opening the own key shuts it and the next taps wait for g_cameraLeavingSubsTimer (`leave_timer`, 55 frames: BenchCheckControls skips every call while it runs) to reach 0, then TAP_LEAD (0.6 s) with no direction before the first tap (the original exe too misses 10/8 taps typed 0.05 s after a pause, 5/5); a miss counts only when play was stopped both before and after the taps (gameStatePl, gameState), else 'stopped mid-taps'. 06/11 tapprobe (Panchina): original / LB7 / RC3 open on taps alike, the tap code is the original's | ~3-6 min |
| engine_wmodes_swospp | 4.1 (Regia 05/11 + 06/11) the one-world-per-contest lock: engine_wmodes (FRIENDLY) + engine_wmodes_diy (DIY cup saved / loaded with its world) with the lock line asserted on screen (wm_lock): after INTER (2026-27) the top list and STORICO's show swe.LOCK_LINE of SWOSTEST_UI in the title bar (IT 'UN SOLO MONDO PER COMPETIZIONE', EN 'ONE WORLD PER COMPETITION', FR 'UN SEUL MONDE PAR COMPETITION', DE 'NUR EINE WELT PRO WETTBEWERB'; the text in the exe under test, fits the bar, font chars). EN: under SWOS++ 1.9.2.2 on SWOSPP_BUILD (timer feed; raw fires by spp_fire_held, wm_fire). IT / FR / DE: SWOS++ installs on ENGLISH.EXE only, so the same on SWOSTEST_BUILD without it ('SWOS++ n/a'). PASS LB7 it/en/fr/de | ~2 min |
| bench_training | 4.0.6 (Marco) a training game keeps the game's 2 from 2 (benchx bx_look skips it): a World 2026-27 career at ROMA (BENCH_BUILD, TRAIN_PATH), SQUADRA -> TRAINING (IT: PRATICA): the kick-off's gameMin / MaxSubstitutes 2 / 2, both in-match teams named in places < 16, the dugout shot (train_dugout); the training played out, then the league match: its kick-off has the real bench again (TRAIN_REAL, default 15:5, ITALIA SERIE A) | ~3 min |
| oppo_list | 4.0.6 (Davide's option b) the opponent's squad, read only, in the in-match bench menu (oppl.py): bench_world's match (BENCH_OPPL=1, release exe); UP on the coach opens it (g_subsState 5): page 0 its 11 on the pitch, DOWN its bench pages (11 a page: places 12.. not used, not sent off), UP back, nothing past either end (page / rows checked against its in-match team); FIRE / LEFT / RIGHT close it (state 0, cursor 0); both in-match teams (1704 bytes) and NumSubs unchanged; benchTeam / benchTeamGame = the bench team's own at every dump with the list open (the draw's shadow never leaks); the SWOS++ mark poked to 0B8h (what SWOS++ writes, swospp_bench) -> UP leaves it shut; every page has the opponent's name row on top (oppl_title: its frame in the list's frame colour at y 8 / 18 and the list's columns, the name's ink inside; Davide's look review); then a change as usual (bench_sub). Shots oppl_page0 / oppl_down1.. Every page also through fw_check (formwide). | ~1 min |
| bench_strip_world | 4.0.6 (Francesco) the bench info strip (bstrip.py): bench_world's match (BENCH_STRIP=1, release recipe exe); the reference = the pre-match screen's rows (the texts are one set of entries the game re-points row by row: row 17's; the box left of row 17 steps the reserves' window, every bench / reserve player through row 17, back to the first); in the match the bench cursor down through the places: per place the BSTR mirror (state 0, place, the PlayerInfo = that place's in-match player, its name) and skills / value = his squad row (names the squad rows cut short: 'M. DI BATTIS.') or, off the reference, a value with a digit + 0-3 letters (none for a keeper); FIRE on place 12: state 1, the box of the one going in (plToEnterGameIndex) and of every highlighted row (a player on the pitch, 10+ rows); 10+ boxes against the reference; both in-match teams unchanged; the SWOS++ mark poked to 0B8h: nothing drawn (shot strip_spp); then a change (bench_sub). dugout_check's pitch fit skips the strip's area (x 80..239, y < 62) in every run (the strip is in every build). IT / EN / FR / DE: SWOSTEST_UI=<l> with a build whose ITALIAN.EXE is that language's (bench_world runs ITALIAN.EXE). BENCH_SPP=1 (SWOSTEST_UI=en, alone on the Mac): nothing drawn through a whole change (the mirror's frame counters stay 0; strip_subs_menu = SWOS++'s own menu). Shots strip_b* (bench) / strip_s* (subs menu). | ~2 min |
| kits_training | 4.0.6 (Marco) SELECT KITS in a training game (kittrain.py: slots by name + team pointer): ROMA A / SQUADRA B, MAGLIE -> OK (the automatic A first / B second), SOLO PARTITA / SEMPRE hidden, the kick-off's in-match kits differ (TeamGame's worn colours), careerTeam's kits unchanged; then the league match: SELECT KITS on the club and its opponent, played | ~4 min |
| squad_numbers | 4.0.6 (Marco) editable shirt numbers on the club's squad screen (squadnum.py: shirtedit's editor there): JUVEFIX3, SQUADRA: LEFT lights row 7's number, UP = next free, typed 23 (holder swapped), ESC undoes (still on the squad screen), typed 7 + ENTER (swap, pin bit), DOWN moves, a starter <-> bench swap keeps the numbers; saved (.CAR careerTeam at 56192) + reloaded: same numbers; another club's squad (VISUAL. COMPETIZ. > SERIE A > STAT > VIS. SQUADRE > CAGLIARI): LEFT / UP / 23 change nothing. Shots squad / lit / typed23 / after / reloaded / opponent | ~1 min |
| squad_numgap | 4.0.6 (Davide 02/11, MiSTer) two-digit shirt numbers clear of the face box and the name bar (numcol.py: number column x 14, names 2 px right on the lists): a new World 2026-27 ROMA career (99, 43, 86...) on NUMGAP_BUILD (a release dir, ITALIAN.EXE = the language's exe; any SWOSTEST_UI) -> squad screen, team screen (PRATICA / TRAINING), tactics editor (MOD. TATTICA -> the first user tactic: UTN A / USER_A / UTIL A / SPIEL A): numgap_check - every row's number ink (2 / 8) keeps 1 clear column after the face box and 1 before the name bar, on all three (Davide 03/11: names +2 px on the lists); shots squad / team / tactics | ~1 min |
| edit_custom_teams | 4.0.6 (Marco) EDIT CUSTOM TEAMS looks and numbers (edteam.py): 90 MINUTES XI in the editor: FIRE on row 0's face 10 times = the ten looks in order (record byte 26 face / byte 25 bits, the button's icon each), rows 1..3 set to looks 7 / 8 / 4; the number box on order[4]: RIGHT lights it (4.0.6 RC3: the number is right of the face; et_reopen = RIGHT, LEFT, RIGHT; et_off_face before OK), UP = next free, typed 23 (holder swapped), ESC undoes, 7 + ENTER (swap, pin bit), reopen / DOWN / FIRE (look unchanged) / DOWN; OK + the save prompt (SALVA / SAVE / ENREG / SPEICH): CUSTOMS.EDT = the edited team (kept as saves/ET_CUSTOMS_<UI>.EDT). Then a friendly with the edited list (the team human: GIOCA-ALLENA's colour, A C ARTISAN the CPU): the team screen's numbers, its face icons (pixels per row: one picture per look, as many rows each - rows follow the formation), a starter <-> bench swap keeps the numbers; in the match the three players' look flags (4 / 7 / 3). Any SWOSTEST_UI (FR / DE labels: CHOISIR LES EQUIPES, MATCHS AMICAUX; DE umlaut entries = the one before ESCI). SWOSPP_BUILD (EN): the four faces only, byte 25 untouched, no match flags read. Shots editor / looks / look0..9 / lit / typed23 / after / prematch / match | ~1.5 min |
| squad_benchnum | 4.0.6 (Davide, RC3 on the MiSTer) a bench player's number on the long-bench squad screen: a new World 2026-27 career at CELLE VARAZZE (NUMFIX_BUILD, else the harness build; SWOSTEST_UI it / en / fr / de, that language's exe as ITALIAN.EXE), bx_bench poked to 15, SQUADRA: LEFT + 8 8 + ENTER on starter row 3, bench rows 12 / 15 (window at the top), row 12 after the box moved the window one place, row 13 after three more: only the player that row shows (careerTeam's place order + benchx's bx_sq) gets the number. RC3: with the window moved the player that many places above did (squadnum's sq_row ignored bx_sq) | ~1 min |
| edteam_right | 4.0.6 (Davide, RC3 on the MiSTer) EDIT CUSTOM TEAMS, the number reached the way it is drawn: on row 5's face RIGHT lights the number (cursor stays), 8 8 + ENTER, the next RIGHT moves to the name, LEFT back to the face, LEFT on the face opens no box. A RIGHT within DWELL (~0.3 s) of arriving on a face is a move (shirtedit's rule, as LEFT had). NUMFIX_BUILD; SWOSTEST_UI it / en / fr / de. RC3: RIGHT went to the name at once | ~15 s |
| market_keep_page | 4.0.6 (Enzo) the market list keeps its page after an offer (mklist.py), release exe (foreign_exe), World 2026-27 INTER: national market (filled to 25 when under 21) ELENCA, ALTRI, row 13 -> offer -> ESCI: page 10, same found count and rows, cursor on row 13, label ALTRI; ALTRI -> page 20; a page-20 pick with the market cut to 20 under the offer -> back on page 10; foreign market (INTER: 12 players): ALTRI to page 10, a pick, ESCI -> page 10, same rows. 4.0.5: page 0, empty list. Shots nat_p2 / nat_back / nat_p3 / nat_emptied / for_page / for_back | ~2 min |
| scorers_int | 4.0.5 INT column (tools/scorint.py): Luigi's PROVA.CAR (SCORERS_CAR) loaded on SWOSTEST_BUILD (SWOSTEST_UI it / en / fr / de), VISUAL. COMPETIZ. -> CAPO CANNONIERI NAZIONALE: every row's numbers read from the screenshot (digit shapes learnt from the rank column), LEGA + COP1 + COP2 + INT = TOT, the numbers apart, the last row = its player's record +33..+36, the others some record's; FAILs on rc19 (no INT column) | ~10 s |
| scorers_int_world | the same after a World 2026-27 career season (SCORERS_TEAM, default NAPOLI: Serie A + Champions League; world8485 W8485_SAVE_END, then loaded) | ~6 min |
| goal_slot_sc / _sc_real / _cd / _po | 4.0.5 goal counters (tools/goalslot.py): a World 2026-27 career (INTER / FIDELIS ANDRIA / MODENA forced 5th of Serie B on a DPLAY_FORCE=5 build) on GOALSLOT_BUILD up to the SUPERCOPPA / COPPA ITALIA SERIE D / PLAY-OFF results (W8485_MIDTEXT, else the season's end; _sc_real: the SUPERCOPPA ITALIANA final played for real, W8485_REALPLAY - the match engine's write-back); gs_add's ring of the remapped goal writes (both write-back sites: played and simulated matches) read from obj1 at every screen: +37 (form / trial mark) unchanged, the goals in COP1 / COP2 / LEGA, never slot 4 as the game | ~3-8 min |
| world_namefix | 4.1 (41-namefix, namespr ns_fix; Francesco's ISCHIA, Tally's CHIEVO): NAMEFIX_BUILD (a release-recipe dir, its league int 3 NOP-ed), fixtures/namefix/ISCHIAF1.CAR: its first 3 matches for real (W8485_REALN), the rest simulated, through the season end without a reload: obj2 NF_WIN (0x8000..0xCFFF) unchanged to the season end (it rewrites 0x9702.. legitimately), careerFileBuffer 108, the 32 name sprites drawn at each real match ([names]), ChainFont's window logged ([nswin]: 0xA1C0..0xCBBF on the 4.1 builds, 0x81C0.. on REL405); W84B.CAR count 108, loaded back. Baseline (no ns_fix): FAIL at kick-offs 2 / 3 | ~7 min |
| career_namefix | the same in a normal 1996-97 career (Regia): JUVEFIX3 (the coach only: realplay presses ALLENATORE after cycling ALLENA:), its next 3 SERIE A matches for real in one program run: NF_WIN at each kick-off = as on the career menu before it, names drawn. Baseline: 0 / 10004 / 10241 bytes (tmdFileBuffer's team records) | ~5 min |
| match_names14 | 4.0.5 14-character match names (namespr.py), a friendly HAMBURG v SCHALKE: 32 sprites 112 x 6 drawn, 6 long names past 80 px; VGA + EGA (memsize 8). SWOSTEST_UI it / en / fr / de (SWOSTEST_BUILD's ITALIAN.EXE that language's; the original of that language for the addresses). SWOSPP_BUILD (= SWOSTEST_BUILD, SWOSTEST_UI=en): under SWOS++ 1.9.2.2, VGA only, held taps | ~1-2 min |

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
round a day, does to it what the game's view does - cseg_8B71C / cseg_8B7EA - and closes it), the random state
pinned at every pause on both (W8485_RNGSTEP: CareerMenu reseeds Rand from currentTick on every entry, and B's views
cost time - unpinned, a one-tick shift moved one draw, a season-2 record's byte 0x11143, on I10h and I10i alike,
04/11): the two season-2 .CARs byte-identical, B's CG_G with views opened, no bad sum, no sticky fallback, no failed build (CGG_TEAM, default
HAMRUN SPARTANS). On the release recipe per language: the language's exe as ITALIAN.EXE in c/CGG_<A|B>_<lang>/SWOS,
SWOSTEST_UI=<lang>. B is NEVER made with buildrel.sh: it clears every modver.BUILD_SWITCHES entry, CONTI_CGVIEW too
("test switches cleared: CONTI_CGVIEW"), so its B = A (same md5) and the guard passes proving nothing (I7, 03/11).
Make B from A's release dir: copy it, then `CONTI_CGVIEW=1 MODVER_TAG=.. python3 internal/release-tools/bfull.py
orig/ITALIAN.EXE <B>/SWOS/ITALIAN.EXE it <B>/SWOS/DATA` with buildrel's SEASON_PACKS exported; check A's and B's
md5 differ. Tier B (test_ctgame.py, fixtures with ct_daily + save_trailer hits): test_cg_guard_close (the
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
4.0.6 continent screens (VISUALIZZA MONDO: each continent's cups as green buttons above its nations - EUROPA the
world's UEFA cups, moved from MONDO (Davide 03/11): the game's own views -, FIFA's on MONDO; ctview world_cups / cw_after, careerworld w_choose; the lists with the buttons swapped in
only around VIEW WORLD's picker - ctview cw_on / cw_off - the new career's club picker and the foreign market keep the
plain ones): world_cgame_view goes on after the COPPE CONTINENTALI part - MONDO + every continent (gwalk: the picker's
links pass through hidden entries, walk finds no path), button names in the font and within their buttons, each cup
button -> its rounds menu (title = the cup) -> every round -> RIEPILOGO (that cup only) -> ESCI to the career menu, CT
state unchanged; the foreign market's picker (ACQ. ALTRO GIOCAT. STRANIERO) first - after the game's own cup view opened from VIEW
WORLD (cseg_3AA17: a UEFA cup) the career menu's up from OFFERTE LAVORO goes into the fixture rows, on the
released 4.0.5 (runs-cgnav2-405: its loaders cseg_3ABB2 / 3ADAE set dseg_DF4F4, CheckTransfers' 'transfers closed
till the next match' flag, so TRASFERIMENTI was disabled and skipped). FIXED in 4.0.6: careerworld w_vcup puts
dseg_DF4F4 / dseg_E0052 back after that view; world_cgame_view's tr_ok asserts TRASFERIMENTI enabled and up from
entry 5 (job offers) landing on it after the load, a stock VISUAL. COMPETIZ. view and each UEFA cup from EUROPA - and, in a second session, the new
career's (CARR. STORICHE - MONDO 2026-27): no cup names on them. CV_OWN=<club> with a save of that club in a conti
round in progress (runs-cgslot3/boca_libgr_it.CAR: BOCA JUNIORS on a CONTI_FORCE=lib:groups build, after its 2nd
Libertadores match): its round shown with no ctgame view opened (CG_G[3] unchanged) = the game's slot 3. Tier B
fixture now cw_uru6 (the cg_uru2 recipe on c/HTcw6: careerworld's w_choose grew, the older snapshots' layout no
longer maps).

Option C P4 (the fallbacks: a round the game's screen can't show -> cg_view 0 -> ctview's cr_go shows version A's
page, the state as it was): Tier B test_cg_fallback (HT_CODE=c/HTcw7 or newer on cw_uru6) - each reason once on a
played knockout round, cg_view 0 with its CG_ERR, nothing left open, no bad sum, the saved state byte-identical:
E_GUEST 10 (a club in no team file of the world - CG_FCNT, ctgame.py fcnt: each file's last ordinal + a bitmap of the
files the world loads, asserted at the build against every pack club and guest; poked as an unloaded file and as an
ordinal past its file's clubs: GetTeamPointer's search of a file has no end, the game would hang), E_NOREC 11 (a played
round with no goals kept: CG_ROOM poked to 4), E_CACHE 4 (CG_NUMSEL 159; the count put back), E_GUARD 7 (CG_G[6]
sticky), E_KIND 5 (ACL Elite's league stage); plus the replay record's real use under 3/4 of its room (1437 of 3836 B:
P4 moved it to the scratch's end, CG_REC 3280h, 4 KB - it had 1852 B at 17C0h). test_cg_view accepts E_NOREC only for
a round with no record (a week past the snapshot's). DOSBox `world_cgame_fallback` (CV_BUILD = world_cgame_view's
build, CV_S2): CG_G[6] poked sticky -> each round button shows the very page RIEPILOGO shows, CG_G[3] unchanged, back
on the rounds menu with its links, CT_SEG / CT_ED unchanged; poked back -> a view again; then a new career's season
1 (CGF_TEAM, default ROMA: no 'CE' edition) - every COPPE CONTINENTALI button the page at once, VIEW WORLD's
SUDAMERICA cup the page, no view opened. `world_cgame_swospp` (SWOSTEST_UI=en, CV_BUILD = the English release exe):
world_cgame_view with SWOS++ 1.9.2.2 installed (CGV_SWOSPP: its loader files, timer keys; swospp_on asserted); the
save loaded by name - under SWOS++ the list opens on ABBANDONA and the load ends on the day's league table, ESCI ->
the chairman's note -> the career menu, 4.0.5 + SWOS++ the same; SLOW_FIRE 3 s after walk / gwalk's fire; no foreign
market part). Status 03/11: up to 13 rounds opened and closed in a row under SWOS++ (legs, aggregate, groups), but
the run does not reach its end - SWOS++'s timer-fed keys come late or twice (a view's ESCI not taken, a fire into
NEW ZEALAND's leagues): a harness limit, not a view fault seen so far.
4.0.6 ctcursor (Davide GO 05/11, variant a): the rounds menu opens on the CURRENT round - ctview.c cv_rounds' CR_SEL,
the first listed round not played yet (drawn, its month over: the summary page's rule), every one played the last
(after the final: the final, RIEPILOGO one key away); ctview cr_sel writes it into CR_MENU's initialEntry before
SHOW_MENU on both ways in (cv_open, cw_after); back from a round's view or RIEPILOGO the game keeps the entry it left.
The list is cup by cup (calendar order within a cup), so the pick is the first cup's open round. world_cgame_view
asserts every rounds menu opens on a visible round button; `world_ctcursor` (DOSBox, CV_BUILD / CV_S2 as
world_cgame_view): season 1 (new INTER career) every menu on its first round; the season-2 save on a round; the
current calendar entry's week poked to FF (restored, nothing saved) every menu and VIEW WORLD's SUDAMERICA cup on its
last round, never before the plain week's pick; shots ctc_<s1|s2|end>_<k>, ctc_world_cup.
