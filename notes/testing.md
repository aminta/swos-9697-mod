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

## Not done yet / next

- Season advance through player matches (W128B, JUVEFIX3 mid-season): needs a script that reacts to the screen.
  Plan: the stub's 'dump' break becomes a pause (runner reads memory, sets EIP past the int 3 with the debugger, writes
  more keys into the script area, F5), so the runner can loop "advance until FINISCI STAGIONE".
- The euro session's round-2 no-derby check (UEFA R2 ties at DIY+2CDh, teams at DIY+24Dh) can read the dump once the
  season can be advanced to that draw.
- Friendly matches (kit-colors session): reachable with `keys` + screenshots, scenario not written.
