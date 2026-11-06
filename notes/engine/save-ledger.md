# Career save room: ledger (engine step P0, 2026-11-04)

The career .CAR of a big world (World 2026-27, Europe 1984-85) keeps three things in careerworld's cache room
(CONVENTIONS 21):

- the team cache: SEL_N × 684 B;
- the trailer's main block;
- the engine block 'EN'.

`trailer.py` asserts that SEL_N × 684 + main + 'EN' ≤ SEL_ROOM. A new item costs 4 B (its id and length) plus its size.

**Measured on 406-i10j a25886a, release recipe (c/HTI10j, world5tm-403c13b), NACIONAL season-1 save:**
SEL_N 160 × 684 = 109440, main block 948, 'EN' block 15343 (25 items) → 125731 of SEL_ROOM 125824: **93 B left**.

| Item | B | Owner (module) | Since | What |
|---|---|---|---|---|
| GP | 2048 | gplay | 4.0 | play-off / title-group state (GP_ST) |
| GS | 1408 | gplay | 4.0 | stages (GS) |
| SS | 1542 | gplay / split | 4.0 | the career league's season bank |
| SS2 | 1542 | gplay / split | 4.0.5 | the second bank (Apertura / Clausura) |
| RI | 2332 | ripool | 4.0 | reserve pools |
| CE | 2260 | conti | 4.0.2 | the conti edition being played (4.0.6: pad bit 0 = B2 season 1, bit 1 = ED_G2 goals model) |
| CT | 196 | conti | 4.0.2 | conti holders / state |
| CD | 1032 | gplay (Coppa D) | 4.0.1 | Coppa Italia Serie D |
| SR | 470 | statespec | 4.0.3 | Brazilian states' rankings |
| SB | 32 | statespec | 4.0.3 | the states' knockout round |
| PR | 388 | (patch.py) | 4.0 | |
| BT_EXT | 409 | bigtables | 4.0 | big tables' extension (no clear) |
| XS | 386 | xtra | 4.0.2 | XTRA players bought |
| XL | 101 | xleft | 4.0.6 | XTRA players who left their club |
| CF | 260 | gplay (cupsf) | 4.0.1 | the clubs' last-season places |
| F1 | 248 | gplay | 4.0.5 | the FASE 1 page's table |
| SC | 204 | supercup | 4.0 | supercups |
| WN | 164 | gplay | 4.0.1 | the WINNERS page's last season |
| BU | 84 | bteam | 4.0.6 | B-team call-ups |
| SH | 66 | split | 4.0.1 | head-to-head / keep block |
| CN | 36 | gplay | 4.0.5 | the career club's last division name |
| BQ | 24 | gplay | 4.0.6 | may each B team go up |
| CC | 4 | cpucards | 4.0.6 | OPTIONS: CPU red cards / injuries |
| GI | 2 | gkinj | 4.0.6 | OPTIONS: goalkeeper injuries |
| CR | 1 | cpurefill | 4.0.6 | CPU replacements switch |
| FF | 21 | ffp (Integratore; state in finance.py FF_ST) | 4.0.6 (after I10j) | financial fair play: FF_ON, FF_BLOCK, FF_VALID (1 B each), FF_INC (the season's gates), FF_IPREV (last season's income), FF_FINE, FF_TVW (the season's TV credit share paid for the wages, left out of FFP's income) (dd each), FF_NCH (dw: the season's match charges, for the season-end wage bill). Plain bytes, no pointers, clear: an older save loads it zeroed = the rule OFF; a new career sets ON + VALID (after_new). With its header 25 B: **68 B left** on I10j + FFP |

## Engine P (2026-11-06, branch p-persist off engine = trymerge cd4e54c)

**Re-measured on the 4.1 recipe** (406-omm, c/HTOMM): 'EN' 15368 B (26 items) + main 948 → **68 B left** of SEL_ROOM.

- **SEL_ROOM + 207 B** (0x4000 → 0x40CF over the cache): all the room between the stage's end and B_UQ, nothing
  moved (B_SEL + SEL_ROOM still 945 B below B_STAGE). A constant, not an old-save-trap change: old saves are
  smaller. The other way round, a save of this build can be up to 207 B bigger than a 4.1 exe's room (a downgrade, not
  supported).
- **SWC1** (swe.c, obj4, 32 B in v1): the engine's state, one 'EN' item that *grows*. Header 20 B: u16 version (1),
  u16 world (the career's world byte), u32 spec hash, u16 season, u16 flags, u64 seed (0 until the steps that use
  them), then sections (u16 id, u16 length, bytes; id 0 ends). swe_st_save (engine.before_save) writes the header;
  swe_st_load (engine.after_load) keeps the save's version in SWC1_LOADED (0 = a save from before P) and starts a
  missing state. With its 4-B item header: **36 B → 239 B left** (HTP1).
- **Item flags in the trailer** (EN_ITEMS' third dword): bit 16 clear, **bit 17 grow** (a shorter saved length loads,
  the rest zeroed; a longer one is a newer build's: skipped, as before). **Load-only items**
  (engine.retire_item): read by id and size, never written; the save loops write EN_NS items, the load knows EN_N.
- **How the room comes back:** a step that takes a legacy item over (S1..S3: GP, GS, SS, SS2, CD, CF, WN, F1, CN, BQ)
  retires it (load-only, its import in swe_st_load when SWC1_LOADED is 0) and grows SWC1 by a section: its bytes + 4
  move from the item to SWC1, the item's own 4-B header comes free. **SWC1 ≤ the retired items + 239 B**; beyond
  that, a B_STAGE / B_UQ move (+~4 h, its own old-save gate), asked first.
- Tier B: test_swc1.py (static image): the save, this build's load, shorter (grow) / longer / missing SWC1, a plain
  item of another length skipped, and (EN_RETIRE_PROBE=1 build) a load-only item read, never saved.

## The round trip (test_roundtrip.py, Tier B)

- **A save of the current build:** save(load(x)) = x, byte for byte.
- **The archived saves, 3.3.6 to 4.0.5:**
  - They are upgraded exactly once:
    - the main block, the team cache and every item they had are unchanged;
    - only the missing items are added, with their defaults;
    - in the fixed part only the game's absolute pointers are re-based to the exe, plus 4.0's split state, which `sp_migrate` moves.
  - After that they are a fixed point.
- **Step H's "5083 of 16192 B differ":** that was a byte-offset comparison of an upgraded trailer with an older one. The added items shift the later ones; item by item, nothing changes.

## Consequences for the engine (step P)

- **SWC1 cannot fit in 93 B.** Choose one of these, or both:
  - fold legacy items into SWC1 as the engine absorbs their modules: GP + GS + SS + SS2 + CD + CF + WN + F1 + CN + BQ ≈ 9.3 KB are gplay's and become the engine's. That frees what the engine state needs, as long as it stays within their sum;
  - grow SEL_ROOM by moving B_STAGE, a change of the old-save-trap class that needs its own old-save gate.
- **The rule from now on:** a new item in a 4.0.x minor gets a line here, and a P import entry when the engine starts, before its sha.

## Not save room: the default world (W-modes M1, 2026-11-04)

- **SETUP.DAT +105** (1 B, config, no .CAR room): the main menu's world switch (mainbtn). 0 = World 2026-27 (also a
  105-B file: a fresh install, INSTALL.EXE, the patcher's factory file), 1 = the 1996-97 game, 2 = Europe 1984-85; a
  value the build has no world for reads as 0.
- The game reads SETUP.DAT whole into setupDatBuffer: +105 is the first of 6 padding bytes nobody references, so a
  106-B file is safe for every exe, the original included. controls' SAVE now writes 106 B and keeps it.
- The registry header's +28 (swreg v2) points at it, for the W-modes pickers.

## Not save room: the DIY contest's world, block 'WM' (W-modes M2, 2026-11-05)

- **A .DIY file's tail** (4 B, no .CAR room, no 'EN' item): `'W' 'M'`, u8 length (1), u8 the contest's world (swreg's
  world number: 4 = Europe 1984-85, 5 = World 2026-27). Mixing A: one career world per contest, plus the 1996-97 game's
  clubs. A contest of 1996-97 clubs alone writes no block, so its file is byte-identical to the game's.
- Written by obj4 after the game's SaveDIYFile (SaveContest's call, retargeted): the file is opened again and the block
  appended at its end. The game's own part (competitionFileBuffer .. the last 684-B record + 2) is unchanged.
- Read by obj4 after LoadDIYFile (LoadOldCompetitionMenu's call, retargeted). The block counts only when the file's
  size is exactly the game's part + 4 and the tag matches. Any other file (the game's, an older mod's, a preset) reads
  as world 0. An older exe loads a file with the block whole: the 4 B land past the last record and nobody reads them.
- Presets (.PRE) and seasons (.SEA) get no block in W-modes. Their worlds come at 4.1 (engine P: SWC1 in those saves).
