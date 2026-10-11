# Automated tests (tools/swostest.py) — 2026-10-10, branch test-harness

Goal: routine regression checks without driving DOSBox-X by hand. Usage and internals: docstring of tools/swostest.py.

## What is reliable

- Private runs: internal/swostest/runs/<name>/SWOS (copy of c/SWOS game files + exe under test + copied saves), own
  conf, own DOSBox-X (core=dynamic, cycles=max, nosound). c/SWOS, the saves there and dosbox-swos*.conf are only read.
- Input: AUTOTYPE was tried first and dropped. Its keys are held ~50 ms on a wall-clock pace, while SWOS menus poll
  the held state every ~2 ticks, and keys typed while a screen loads are lost: results changed from run to run.
  Instead the exe under test (run copy only) gets an in-game key feeder: MenuCheckControls' and InputTextKeyLoop's
  `call GetKey` go to a stub on a new obj1 page, which types the script keys (keyBuffer + SetKeyboardControlFlags
  press, release after 3 calls), counting waits in GetKey calls. The same script gives the same GetKey count every run
  (3/3 runs identical); loading/simulating does not consume waits. Intro skipped (skipIntro test -> jmp), menus read
  the latched last key (MenuCheckControls' g_inputControls == 5 branch always on).
- Freeze/stop oracle: -break-start + BPINT 3 under a pty; a trap (`int 3; jmp $`) or the script's 'dump' step breaks
  into the debugger, the runner writes MEMDUMP.BIN (32 MB) and reads EIP from the debugger's code view. obj1/obj2
  bases are searched in the dump: they differ per build (0x262000/0x309000 no-world, 0x263000/0x30D000 world 3), so
  the old fixed 0x263000/0x30C000 only held for some builds. Typed debugger commands are ignored while running (no
  queued commands).
- Screens: window screenshots (screencapture -l + a Swift window-id helper) every N s in `keys` runs: used to learn the
  menu paths; scenarios do not need them.
- Speed: menu at ~3 s after start, one season-end run ~60 s, a load/save round trip ~70 s per save.

## Menu paths learnt (IT, cursor positions are the defaults)

- Main menu: AMICHEVOLE selected; 5 x down = CARICA VECCHIA COMPETIZIONE; fire; the first save in the list is selected
  (each run copies only its saves, so the list is predictable).
- Career menu after a load: middle button selected (FINISCI STAGIONE, or PARTITA when the player has a match):
  fire. Row 3 middle = ESCI -> main menu with CONTINUA CARRIERA / SALVA CARRIERA / CARICA (cursor: go to the bottom
  with downs, then up = SALVA).
- Season-end menu ('1998 FINE CAMP.'): VISUAL. COMPETIZ. / OFFERTE LAVORO (selected) / CONTINUA CARRIERA / SALVA
  CARRIERA / ESCI. VISUAL. COMPETIZ. lists the competitions (league table, cups' final results).
- Save screen: list, NOME FILE field (old name), SALVA (selected), ABBANDONA: up, fire, backspaces, letters, Enter
  saves at once.
- Player match: career PARTITA -> round screen (fire) -> squad screen (VIS. RISULTATI / ESCI / AVVERSARI / MOD.
  TATTICA; cursor on ESCI): left + fire = VIS. RISULTATI = the result is simulated -> round screen with the score ->
  fire -> career menu. A generic "advance N matches" loop does not work yet: screens differ (cup round vs league).

## Suite (python3 tools/swostest.py run)

- italy_season: JUVE2 with byte 0x173A3 (E092F) = 0 -> FINISCI STAGIONE -> save -> no trap, table sum 0, C7, next
  CC list 16 distinct clubs incl. Italian ones. PASS on a0f38ad5 (euro9697-nodorby 2ec51ba).
- roundtrip: JUVE2F load -> save from the main menu (ROUNDT1) -> reload -> save (ROUNDT2): byte-identical. PASS.
- world_roundtrip: world 3 build from this checkout (mkworld3 without DERBY, generated into internal/swostest/worlds)
  + W128B: two saves identical, W1 block, 128 records, cups 32/32/64, sum 0. PASS (cef7d6b1). W128B as written by
  25f5d535 differs from a re-save by this build in 6 bytes (+16 each: offsets 63339..63355 step 4 and 95133): build
  drift (ids?), not a round-trip error; to look at if old saves must load unchanged.
- juve2_trap: JUVE2 as saved (E092F = 1), FINISCI STAGIONE: must not trap. Davide's freeze (squad screen, VIS.
  RISULTATI traps at cseg_3C4CE) is NOT reproduced here, also with 2.6.1 d38a5d1c: FINISCI goes straight to the
  season-end menu. Difference with Davide's runs still unknown (options in his install? state of c/SWOS at the time?).

## Interactive sessions and the results-only loop (2026-10-10, evening)

- Session (tools/swostest.py): each 'dump' is a pause. The runner dumps memory, reads the current menu (g_currentMenu
  in obj2, found from MenuProc: header 0x16 B, entries 0x38 B: text pointer at +26h, isInvisible +4, links l/r/u/d at
  +8, skip links at +10h, x/y/w/h at +14h; selectedEntry at +0Ch), then writes the next steps into the stub's script
  area with the debugger (SM), sets EIP past the int 3 (SR EIP) and resumes (F5). press(screen, 'TEXT') walks the
  entry links (BFS, skip links for invisible neighbours) and fires: every step is checked on the next screen, so a
  dropped key is retried instead of derailing the script.
- advance(stop): Davide's fast loop: career menu PARTITA -> VIS. RISULTATI (cup round screen: '- RISULTATO -' first,
  it leads to the squad screen) -> ESCI -> PARTITA ...; other screens: ESCI, else fire. Squad screen without VIS.
  RISULTATI = an injured/suspended player in the first 16 (red row): the runner screenshots the paused window, finds
  the red rows (row background at x=100), fires on the red row, fires on the 17th row's face (cycles the players
  beyond the 16th) until that row is not red, fires on the 17th row's name (swap). JUVEFIX3 -> FINISCI STAGIONE in 140
  steps (~20 min), 17 squad screenshots on the way.
- Player data (not used yet): the career squad (24 players) sits in memory as PlayerFile records; cardsInjuries
  (+1Bh) bit 3 = red card (Montero/Di Livio were 0x08), bits 5-7 injuries.
- keys extras (asked by the kit-colors session): 'fire+right' (two keys held, first typed), -match (feeder in all 12
  GetKey calls, so esc works in a match), -name RUN.

## Results 2026-10-10 night (build a0f38ad5 = euro9697-nodorby 2ec51ba)

- italy_advance PASS (140 steps, ~28 min): 1999/2000 CC list 16 distinct, Italian champion (20,45) in, Juventus out.
- euro_draws: JUVE2F -> 1998/99 (Juve in the UEFA Cup): round 1 no same-country tie; at the first pause with round
  index 1 the slot's ties still pair all 32 indices and k=2 is Italy-Italy (0x1E14 v 0x2014): stop condition or a
  real derby, to be settled with the euro session. Holder words (obj2+0xC058B) read 0 at the season-end menu and
  CC FFFF / CWC 0x1A14 / UEFA FFFF in the new season.

## More results (2026-10-11)

- euro_draws on 1994e494 (euro9697-nodorby c3971c4, w_r2 hook): round 1 OK; round 2 FAILS: the cup's round-2 screen
  'COPPA EUFA SECONDO TURNO ANDATA' lists INTER MILAN v JUVENTUS (slot+2CDh pair k=2 = 0x1E14 v 0x2014, same bytes as
  on a0f38ad5); w_r2's call (obj1+0x7A64E) was hit 3 times. Career cups have no round-2 draw: cseg_2ACAE puts the
  winners first at +2CDh in tie order, the next round pairs them two by two (euro session). The scenario now checks
  round 2 on that cup's round-2 screen.
- Breakpoints: Session.bp(linear, callback) / SWOSTEST_BP=obj1 offsets (counting). Code breakpoints need
  CORE=normal: with the dynamic core a BP fires only the first time (translated code is not re-checked). Each resume
  moves the debugger's code view away (C 0160:0) so that a break at the same address is redrawn and seen; BPDEL *
  also deletes BPINT 3 (re-added).
- Squad screen: unavailable = red row background OR red pixels in the face column (a goalkeeper with a red icon keeps
  his green row); the reserve for row 1 must be a goalkeeper (position text P at x=108 of the 17th row).
- world8485 (Europe 1984-85, IT 4c280af8 = world-1984-85 9b9b10b + 32 world4 packs): new career at Liverpool via
  CARRIERA -> SCEGLI SQUADRA -> CARR. STORICHE -> ENGLAND -> FIRST DIVISION -> LIVERPOOL; season 1984/85 finished,
  new season saved (W84A.CAR): checkw1 k 128, N 64, C7, W1 ok, world 4, sum 0, cups 32/32/64 no dups, W1 records 128
  bad pairs 0. A season of an English club takes ~70 min in the results-only loop.
- SWOS++ (-timer): the feeder hooks TimerProc's call BumpIntroTimers (70 Hz) because SWOS++ re-patches MenuProc /
  CheckControls / InputText at run time. Kit-colors session: full friendly flow passed; in this mode a key can move a
  menu cursor twice (latched + held seen in different frames): use paths that stop at a border.

## Europe 1984-85 world: PASS (2026-10-11)

- Build IT 4c280af8 (world-1984-85 9b9b10b + the 32 world4 packs with a pack.json). Scenario world8485: new career
  at Liverpool (CARRIERA -> SCEGLI SQUADRA -> CARR. STORICHE -> ENGLAND -> FIRST DIVISION -> LIVERPOOL),
  results-only loop, new season saved, reload, second season, saved again. No freeze, no trap.
- W84A.CAR (start of 1985/86): k 128, N 64, C7, W1 ok, world 4, sum 0, CC 32 / CWC 32 / UEFA 64, no dups, W1
  records 128, bad pairs 0.
- Season 1985/86: Liverpool last, manager sacked at the season end; the runner takes the first job offer (offers
  screen rows, the letter's ACCETTA) -> Plymouth Argyle 1986/87. W84B.CAR: k 128, N 73, C7, W1 ok, world 4, sum 0,
  cups 32/32/64 no dups, W1 records 128, bad pairs 0. Saves kept in internal/swostest/saves/W84A.CAR, W84B.CAR.
- Learnt on the way: the season-end menu can come without FINISCI STAGIONE (every match played); keys are held 1
  frame (3 frames triggered SWOS menu auto-repeat in slow menus, a move taken twice); press() checks the selection
  before firing; invisible menu neighbours are skipped in the same direction; sacked = CONTINUA CARRIERA disabled
  -> OFFERTE LAVORO -> offer row -> ACCETTA; BPINT 3 is confirmed at start (lost under load = no pauses); the window
  id helper also finds windows off screen (other Space). A season of an English club: ~25 min.

## Not done yet / next

- Friendly matches (kit-colors session): reachable with `keys` + screenshots, scenario not written.
