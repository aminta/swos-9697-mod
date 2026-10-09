# SWOS++ on the modded ENGLISH.EXE — feasibility study (2026-10-09)

**SWOS++** = Zlatko Karakas's add-on for SWOS 96/97 (github.com/zlatkok/swospp, MIT, latest release v1.9.2.2 of
2026-08-26): network play, full match recordings/replays, DIY competition editor, shirt numbers 0-255, joystick
calibration, auto-save options. English CD exe only.

**Verdict: feasible on ENGLISH.EXE, with limits** (English only; needs a DOSBox-X playtest). Analysis and an
experimental build only: nothing released, nothing installed into c/SWOS.

## How SWOS++ hooks into the game

Two stages:

1. **Install** (`patch/patchit.com`, data in `patch/pdata.asm`): 36 chunks written at fixed **file** offsets of the
   original CD ENGLISH.EXE (size 0x20942F, md5 aa21cd1c…). It only warns on a size mismatch, then writes anyway.
   Exe names tried: `sws!!!_!.exe`, `swos.exe`, `swsengpp.exe`, `sws.exe`. The release zip ships only `loader.bin` +
   `swospp.bin` (no patchit.com), so users need an already patched exe or the patcher from the sources.
2. **Run time**: the installed stub loads `LOADER.BIN` into `pitchDatBuffer`; the loader reads `swospp.bin`
   (ZKBF format, checksummed), relocates it against the obj1/obj2 bases and patches **54 sites** in memory at English
   object offsets (taken from `mapcvt/Swos.map`), then calls its init.

### Install, decoded semantically (orig vs orig + pdata, via tools/le.py)

All 36 `orig_data` chunks match our orig/ENGLISH.EXE. 21 chunks are inside the fixup record table, 15 inside objects.
As object bytes + fixups the whole install comes down to this:

| Site | Change |
|---|---|
| obj1+0x18 (`main_+8`) | `sub esp,0` -> 6 nops; `call SWOS` -> `call DumpTimerVariables` (relative) |
| obj1+0xA929..0xA9B4 (`DumpTimerVariables`, unused debug code) | loader stub: save regs and D0/D1/A0/A1 pseudo-registers, `LoadFile("LOADER.BIN", pitchDatBuffer)`, size check, `call pitchDatBuffer` with eax = obj2 base and ebx = obj1 base, restore, `jmp SWOS` |
| obj1+0x11953 (`SetDefaultOptions+0x10`) | 01 -> 00 |
| obj2+0x54F4 (`aSaveDiskFiling`) | `SAVE DISK F` -> `LOADER.BIN\0` |
| obj2+0xBE168 (`spinBigS`) | 01 -> 00 |
| fixups in obj1 0xA92D..0xA9AC | 14 original records removed (the debug prints' `mov ax,[var]` / `mov esi,offset`); 7 added: 0xA92D->obj2:0xB16EB (SWOS_StackTop), 0xA934->obj2:0 (data base), 0xA982->obj1:0 (code base), 0xA992/0xA998/0xA99E/0xA9A4->obj2:0x31491/0x3148D/0x31471/0x3146D (pops of the pseudo-registers). 0xA934 and 0xA998 are retargets of existing records. |

All other calls and jumps in the stub are relative (LoadFile 0xA1A8, SWOS 0x5758), so they hold as long as obj1 does not
move, and the mod never moves it. Fixup count goes from 73395 to 73388.

### Run-time sites (54 records, identical in the sources and in the released swospp.bin)

Initialization (+0x1C, +0x4D, +0x5E), SWOS_MainMenu (+4, +0xC, +0x22, +0x9E (36-byte new entry), +0xCE),
SWOSMainMenuInit, DrawMenuText+0xB7, GetTextSize+0x81, GameLoop+0x1C8/+0x64C, ToMainGameLoop+0x10,
Increment/ValidateHilPointer*, FindFiles/GetFilenameAndExtension/SelectFileToSaveDialog/SelFilesBeforeDrawCommon
(+ their jump-back targets), DrawControlledPlayerNumbers, DrawSprites, DrawSubstitutesMenuEntry (8 sites),
DrawLittlePlayersAndBall, SetBenchPlayersNumbers, BookPlayer, SetPrevVideoModeEndProgram, BenchCheckControls+0x78F,
SaveCoordinatesForHighlights, MainKeysCheck, Flip, MenuProc, InputText (+0x78, +0x25D), strncpy_+0x1D, CheckControls,
ClearBackground, ShowMenu (+0x34, +0x66), InitMainMenuStuff+0x114, SetDefaultOptions, DoUnchainSpriteInMenus,
UpdateTime, MakePlayerNameSprite, PlayMatchMenuSwapPlayers, ReadGamePort, Joy1/Joy2SetStatus.
For SWOS 2016/17 data it also rewrites ExitEuropeanChampionshipMenu+6 and CommonMenuExit+0x99/+0x176 (main menu copy).

## Collision check against the mod (build4.py, ENGLISH.EXE of the current tree)

The mod changes 241 bytes and 32 original fixups in obj1, and 227 bytes in obj2 (country/competition tables, cup name
strings, DIY/career/season hooks). Each SWOS++ site was checked against those changes: install bytes, install
fixups, LoadFile, pitchDatBuffer (10032 B), the D0..A1 pseudo-registers, SWOS_StackTop, all 54 run-time records and
their jump-back targets (each record ±3 bytes for fixup fields).

- **0 overlaps.**
- The mod adds no reference to DumpTimerVariables, `aSaveDiskFiling`, pitchDatBuffer or SWOS_StackTop. It does
  use the D0..A1 pseudo-registers like the original code does; the stub saves and restores them.
- All 495 distinct SWOS addresses that swospp.bin uses (191 code, 304 data, from its relocation table) avoid every
  mod-changed byte; the nearest code reference is 1142 bytes away from a mod hook. Of the tables the mod extends,
  SWOS++ only uses `teamFileBuffer` (netplay/DIY team loading), which keeps its layout.
- The mod grows obj1/obj2 by pages appended at the end (vsize 0xA6000/0xC7000). SWOS++ allocates its own memory with
  DPMI and does not care.

## Experimental build

`tools/swospp.py MODDED_ENGLISH.EXE OUT.EXE` re-applies the install through lepatch: it checks the original bytes,
writes the same object bytes, removes the 14 records and adds the 7. Verification:

- On orig/ENGLISH.EXE its output is semantically identical to patchit's output: the same object bytes and the same
  73388 fixups. The fixup table comes out 49 bytes shorter because lepatch re-serializes it, while patchit edits the
  records in place.
- On the mod ENGLISH.EXE (scratch build, md5 of the result 21985380…), the diff mod -> mod+SWOS++ equals the diff
  orig -> orig+SWOS++, byte for byte and fixup for fixup (74284 -> 74277 fixups). The LE header is consistent: file
  length = data pages + 364 × 4 KB + last page, and import tables = end of the record table.
- ndisasm of obj1+0xA929 and of main_ matches patch/swoscode.asm. Note: the size check compares against 0x10032, not
  the 10032 the source comment talks about. This is harmless because loader.bin is 1071 bytes.

## Limits

- **English only.** swospp.bin is linked against English object offsets. Italian/French/German would need a rebuilt
  swospp.bin from a translated map (notes/addrmap.json gives ENG->ITA deltas) and a toolchain (nasm + Watcom/
  GCC-DOS, Makefile.pl): roughly 3-5 sessions per language and a fork to maintain. Not recommended without Zlatko.
- The DIY editor, netplay lobby, etc. do not know about the mod's new countries/competitions (>85, the 101+ packs);
  they keep working on what they enumerate. Netplay needs the identical exe + TEAM files on both sides.
- The installed exe loses `SAVE DISK F…` (SWOS++ choice, same as vanilla SWOS++).
- The mod's patcher (patch.py / web patcher) would need an optional "SWOS++" variant for ENGLISH.EXE; the
  incremental-update patcher must recognise mod+SWOS++ exes as well.

## To test in DOSBox-X (scratch exe + loader.bin + swospp.bin from the 1.9.2.2 zip, English install)

1. Boot: SWOS++ title line, "SWOS++" entry at the top of the main menu, its menu opens/closes.
2. Mod menus: TORNEI STORICI / HISTORIC, CLASSIC SEASONS, CARR. STORICHE, new countries in the
   season/competition menus (ShowMenu Push/PopMenu hooks).
3. Friendly + preset cup match: shirt numbers, substitutions screen, bookings, replay + highlights saving (.RPL/.HIL in
   the file dialogs).
4. Career with mod cups (Italy C1/C2, Libertadores, CAF/AFC) through one season end, plus save/load .CAR (trailer
   intact). Also a world career (career packs) save/load.
5. DIY competition editor + load/save of an old DIY competition (the mod hooks SaveDIYLeague/InitDIYCup/
   RestoreDIYTournament).
6. Optional: a two-instance netplay with the mod's exe on both sides.
