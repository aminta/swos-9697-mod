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
   - parses the current menu (`Screen`: g_currentMenu in obj2 — entries with text, invisible/disabled flags,
     left/right/up/down links, x/y/w/h);
   - writes the next keys into the feeder's script area (`SM` commands typed into the debugger), moves EIP past the
     `int 3` (`SR EIP`) and resumes (F5).
5. **Oracles**: saves written by the game (`.CAR`, parsed by `car_info`, `checkw1`), memory structures read at a
   pause (cup and group team lists, holders, flags), the outcome (pause reached / trap / timeout / DOSBox exited).

## 3. Driving the game

- `press(s, screen, 'TEXT')`: finds the visible entry, computes the key path with a BFS on the menu links (skipping
  invisible entries as the game does), checks on the next pause that it is selected (a move can be taken twice),
  then fires. Every step is verified, so a dropped key is retried instead of derailing the run.
- `advance(s, stop)`: the results-only career loop Davide uses (PARTITA → VIS. RISULTATI → ESCI …): message screens,
  cup round screens, the squad screen. Special cases:
  - squad screen without VIS. RISULTATI (an injured/suspended player in the first 16): `substitute()` takes a
    window screenshot, finds the red rows, swaps them with fit reserves (a goalkeeper for row 1);
  - injured goalkeeper: first the reserve goalkeeper of row 12 (the rows' positions are drawn, not menu entries);
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
| xtra_squad | extended career squads (xtra.py): new career at HAMBURG with a test DATA/XTRA.014 = 16 + 9 real players, no invented reserves, 25 after save + load; HANSA ROSTOCK (no block) = 16 + 10 reserves | ~40 s |
| xtra_season | XTRA1.CAR (HAMBURG, 25) played to the season end by results, next season saved: at most 32 players, the real extras still there | ~3 min |

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

## 7. What the tests do not cover (a person still has to look)

- **Playing a match** with the joystick/keyboard: scenarios use VIS. RISULTATI (simulated results), as Davide's own
  quick loop; the match engine itself is the original game.
- **The look of the screens**: names, kits, colours, text alignment (only entry texts and red rows are read).
- **Languages at run time**: scenarios run the Italian exe; EN/FR/DE are only patched and assembled.
- **Every branch of the career**: e.g. the World Cup 1986 list exists only if one coaches a national team during
  1984-85 (as in the original game); jobs of national teams other than England and East Germany; job offers from
  clubs to a national coach; long careers beyond 1990.

## 8. Troubleshooting

- `timeout` with no trap: the script went astray; `runs/<name>/session.log` lists every screen and the keys sent,
  `shots/final.png` the last screen.
- DOSBox-X windows open on screen and can take the focus: keys or a Cmd+Q meant for another application can end a
  run (`DOSBox-X ended: ...` in session.log); `SWOSTEST_NOEXIT=1` keeps DOSBox-X at the DOS prompt when the game
  exits to DOS, so shots/final shows its message.
- `DOSBox-X ended: exit code 0` after a few minutes of a long run (fixed 2026-10-15): DOSBox-X's `-time-limit` counts
  EMULATED seconds; the old 14400 ran out after ~4.5 real minutes in turbo. Keep it huge (the runner kills DOSBox-X).
- `MEMDUMPBIN ...: no file`: the debugger lost a typed command (the dump is retried 3 times; if it still fails, DOSBox
  probably died: see `debugger.raw`).
- Breakpoints (`Session.bp`, `SWOSTEST_BP`) need `CORE=normal` (the dynamic core does not re-check translated code).
- Never run `config -wcd` inside DOSBox-X: it overwrote the user's DOSBox-X preferences once.
