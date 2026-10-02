# Amiga port — feasibility analysis (Session A1, 2026-10-02, analysis only)

Release files, `orig/` and the PC builds were not touched. Amiga game files are in `amiga/orig/` and the unpacked/derived files in
`amiga/work/`. Both folders are git-ignored.

## 1. Source image
- Davide's copy is the WHDLoad install **SWOS9697** (slave v2.3 by JOTD, 19-05-2024), stored inside `AmigaVision.hdf` on the NAS
  (`/home/pi/shares/roms/roms/commodore/amiga/AmigaVision.hdf`, RDB with 2 PFS3 partitions, `DH1:WHD/G/S/SWOS9697`).
  To extract it, `tools/amiga/pfs3.py` (a read-only PFS3 reader: RDB, superindex, split anodes, dir blocks) runs on the NAS
  through `ssh pi@192.168.0.132 python3 - HDF DH1 get WHD/G/S/SWOS9697 DST < tools/amiga/pfs3.py`.
- Edition: **ENGLISH, "SWOS VERSION 152 (06/11/96 13.55)"**, which is the final 96/97 version. This is the slave's "v1.52", detected
  by its unpacked size `$57264`. Because the edition is English, it compares 1:1 with `ENGLISH.EXE`, and the Session 17 addresses are ENG.
- Files: `data/SWOS2` (the program), `data/SWOS2.REL` (its relocations), `data/data/TEAM.*` + `*.TMD` + `POOLPLYR.DAT`, plus `grafs/`,
  `sound/` and `save/`. The slave redirects saves (.CAR/.SEA/.TAC/.DIY/.PRE/.HIL) to `SAVE/`.

## 2. Executable format: NOT a hunk file
- `SWOS2` is a **raw 68000 image compressed with RNC ProPack method 1** (356,964 B unpacked). It is linked at `$100000`, and its
  entry point is `jmp $1000C4`.
- `SWOS2.REL` is also RNC1 compressed. It holds 15,444 big-endian longs, sorted. Each value **minus 1** is the image offset of a
  32-bit absolute pointer. Three entries (193/194/195) fall inside the version string; the slave skips them.
- The slave reloads the program into fast RAM (ExpMem). Its layout: REL at ExpMem+0, SWOS2 at ExpMem+`$80000`, and a 256 KB buffer
  for big TEAM files at ExpMem+`$100000` (the virtual `$180000`). The slave adds `ExpMem+$80000-$100000` to every listed long whose
  high byte is 0 and whose second byte is `$10..$17`. After that it picks a patch routine by the unpacked size. The table has 8
  versions, and `$57264` uses the routine at slave+`$54C`. WHDLoad header: BaseMem `$100000` (1 MB chip), ExpMem `$140000`.
- The program takes up **exactly `$100000-$180000`**: 357 KB image plus BSS up to `$17FFF6`. `g_selectedTeams` (100×684) ends at
  `$17FFE6`. The code also writes to **absolute, unrelocated chip addresses**, for example `$D656` (error code) and the buffer
  `$C9BBC`. The game owns all of chip RAM, so nothing new can go there.
- Tools written: `tools/amiga/rnc.py` (RNC1 unpacker), `tools/amiga/hunk.py` (hunk parser for CODE/DATA/BSS/RELOC32/
  RELOC32SHORT/SYMBOL/DEBUG; used on the slave), `tools/amiga/amimg.py` (image + reloc helper: `l/w/b/cstr/isptr/refs`),
  `tools/amiga/m68dis.py` (68000 disassembler via capstone; capstone is in a scratch venv, `pip install capstone`).
  Not done yet: an RNC **method 2** unpacker (`*.TMD`, `POOLPLYR.DAT`), which the port does not need.

## 3. PC → Amiga map (ENG obj2 offset → Amiga address)
| structure | PC ENG | Amiga | notes |
|---|---|---|---|
| countriesTable | obj2+0x6742 | `$14E638` | 256 relocated longs; names 0..89 identical; Italy record `$14E230` |
| competitionsTable | obj2+0x8B1C | `$1507D6` | same holes (9,47,52-54,56-59,61,63,68,70,74,86-99); continent lists 80..85 identical in content |
| Italy country table | | `$150E1E` | [league `$14FE16`, -2, Coppa Italia `$15053A`, -1] |
| Italy league struct | obj2+0x7EE8 | `$14FE16` | **byte-identical layout**; pointers become BE longs; byte 0 = competition id |
| seasonEndList | obj2+0x943A | `$1510F4` | identical bytes |
| all_countries_list | obj2+0x93F8 | `$1510B2` | identical bytes |
| teamsCountryNumbers | obj2+0xB2A38 | `$14DEC4` | same values, big-endian words |
| cseg_91428 (season end + **80-team assert**) | | `$12BAB4` | `cmpi.w #$50,$157408`; cup counts 16/32/32 at `$12B0B0/2/4`; error = `move.w #$8998,$D656; jsr $102450` |
| careerFileBuffer | VA 0xC958C | `$157408` | |
| g_numSelectedTeams / g_selectedTeams | | `$16F4B4` / `$16F4B6` | |
| LoadCareerFile / SaveCareerFile / ProcessCareerFile | | `$151900` / `$151944` / `$151874` | 1:1 with the PC code; LoadFile `$105928`, WriteFile `$105B02` |
| jump stubs j_Load/j_SaveCareerFile | | `$151978` / `$15197A` | `bra.b` |
| career team save/restore (32 teams → chip `$C9BBC`, `$5582` B) | | `$12AFA8` / `$12AFC8` | |
- **Competition ids differ.** Leagues are PC+1 (65 of 65). Cups are PC−16 (51), plus one at −88. A PC→Amiga id table has to be
  generated automatically by walking competitionsTable on both sides; the walk is in the session scratch code, to be turned into a tool.
- **.CAR is not compatible with the PC.** The fixed part is `$16F4B4-$157408` = **98,476 B** on Amiga against 95,151 on the PC, so
  some careerFileBuffer offsets differ. The file layout is the same: fixed part + word N + N×684 teams. The trailer fits the same way.
- **TEAM files: all 72 Amiga TEAM.xxx, once unpacked, are byte-identical to the PC ones.** The mod's TEAM.020 and its new TEAM files
  can be shipped as they are (unpacked, if the slave's loader takes plain files: WHDLoad's decrunch passes non-RNC files through, but
  this is NOT verified). The Amiga is missing TEAM.047 (Costa Rica), 057, 059, 068, 070 and 074.
- Not yet located: InitializeNewSeason, the European cup builders, someLeaguesTable, and the remaining hook sites. The method that works:
  data signature → `refs()` of the relocated address → 68000 disassembly that matches the PC routine. Code order differs from swos.asm.

## 4. Memory, saves, new code, toolchain
- **Where the extension goes:** not a new hunk. Instead (a) zero-pad the image to the end of its BSS, (b) append new data and code
  for the virtual range `$1C0000+` (after the slave's 256 KB buffer at `$180000`), (c) add the new pointers to SWOS2.REL
  (sorted list, value = offset+1), and (d) patch the slave in 3 places: the size check (`cmp.l #$57264`), the reloc filter
  (`cmpi.b #$18` → `#$20`), and the ExpMem header (`$140000` → `$180000`, giving 256 KB of room, much more than the PC obj pages).
  Its patch routine (slave+`$54C`) patches fixed offsets, so its patch sites must be listed and kept clear of the mod's hooks.
  The 68000 code is hooked with `jsr`/`jmp` absolute + REL entry (simpler than LE fixups).
- **Memory configurations:** 1 MB (A500/A600 stock): **NO**. The game already fills 1 MB of chip RAM plus 512 KB, and the floppy
  version has no room. A1200 with 2 MB of chip and no fast RAM: NO (the WHDLoad slave already asks for 1 MB chip + 2.5 MB other).
  **A1200/AGA or any Amiga with ≥ 4 MB of fast RAM + WHDLoad: YES**, with +256 KB of ExpMem. **MiSTer Minimig AmigaVision** (2 MB chip +
  Zorro III fast): YES. So only the WHDLoad/HD version is supported; no ADF.
- **Career saves:** saved on HD in `SAVE/` (no floppy limit). The trailer mechanism is the same as on the PC (guard
  N×684+T ≤ 68400; here the area after g_selectedTeams is the slave buffer/our extension, so the guard is mandatory).
- **Toolchain on the Mac M1:** FS-UAE 3.1.66 is installed (x86_64, so it runs under Rosetta), and **vAmiga** is installed. WinUAE is
  Windows only. vasm/vlink are not in Homebrew: build them from source (plain C, arm64 OK), or write the hooks as hex with capstone
  as the checker. AmigaVision on MiSTer is available for the real test. A WHDLoad test setup in FS-UAE needs a Kickstart 3.x ROM
  (`AmigaVision.rom` on the NAS) plus WHDLoad. The WHDLoad dev package and the slave source (JOTD, whdload.de) are public:
  using them is better than patching the binary.

## 5. Go / no-go and estimate
**GO, with conditions:** WHDLoad/HD only, English edition 1.52 (the Italian/German Amiga editions would need a separate map), and
a patched slave distributed as a diff. Technically the Amiga is *easier* than the PC in several places: the data is identical (TEAM
files byte-identical, tables with the same layout), the code is the 68000 original (the PC hooks' "registers" D0-D7/A0-A6 map 1:1),
relocation is a plain list, and there is 256 KB of room.
Real costs: re-deriving every hook address (no IDA symbols on the Amiga; it has to be done by signatures), the competition-id
translation, the slave, and emulator tests that need Davide.

| block | sessions |
|---|---|
| Infrastructure: slave patch (size/filter/ExpMem), image extension + REL, `amipatch.py` (PC lepatch equivalent), automatic PC→Amiga map (data + call graph), id translation | 2-3 |
| Data: TEAM files (reused), countries/competitions/continent tables/seasonEndList/strings | 1 |
| 68000 hooks for the 1.2 scope (C1/C2, SA cups, Intercontinental, new countries, CAF/CONCACAF/Asian cups, .CAR trailer). About 560 explicit x86 lines in sacups/trailer + inline patches in c1c2/countries/africa/asia/namerica/cafcups: about 1000-1500 lines | 4-6 |
| 2.0 extras (historic tournaments, 1:1 Libertadores 97, lib97/historic about 170 x86 lines + data) | +3-4 |
| Emulator tests (FS-UAE/vAmiga + MiSTer, multi-season career) | 2-3 (Davide's playtests) |
| Patcher: an Amiga mode in the HTML patcher (RNC1 decrunch in JS, SWOS2+REL+slave diff, TEAM files) | 1-1.5 |
| **Total, 1.2 parity** | **about 10-14** |
| **Total, 2.0 parity** | **about 13-18** |

Recommended first step (session A2): the pilot. Patch the slave to accept an extended image, add one test string at `$1C0000`,
point a contest name at it, and boot in FS-UAE/vAmiga. This proves the extension mechanism end to end before any data work,
just as Session 17 did on the PC.
