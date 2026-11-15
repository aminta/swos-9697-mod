# Career save room: ledger (engine step P0, 2026-11-04)

The career .CAR of a big world (World 2026-27, Europe 1984-85) keeps three things in careerworld's cache room
(CONVENTIONS 21):

- the team cache: SEL_N × 684 B;
- the trailer's main block;
- the engine block 'EN'.

`trailer.py` asserts that SEL_N × 684 + main + 'EN' ≤ SEL_ROOM. A new item costs 4 B (its id and length) plus its size.

**Measured on 406-i10j a25886a, release recipe (c/HTI10j, world5tm-403c13b), NACIONAL season-1 save:**
SEL_N 160 × 684 = 109440, main block 948, 'EN' block 15343 (25 items) → 125731 of SEL_ROOM 125824: **93 B left**.

**4.1 (41-selroom, 08/11), release recipe c/REL41sr (8dfa5ea + the room change, world5tm-403c16):** SEL_ROOM grows by
640 B (B_STAGE 0x7B000 → 0x7AE40, the gaps around the stage; B_UQ and everything after it unchanged). 109440 + 948 +
'EN' 15368 (26 items) = 125756 of SEL_ROOM 126464: **708 B left**, for S2b (the UEFA cups' earlier rounds). The gaps
allow at most +679 B: past this, move B_UQ and the tail after it, or fold gplay's items into SWC1 (4.2).
Old saves: the .CAR layout does not change and B_STAGE is a file I/O buffer only (no save stores an address into it):
the 8 archived saves round-trip byte for byte as on 8dfa5ea (test_roundtrip, fixtures p0_uru_load_sr / _srbase).
Edge case (pre-existing): a 3.0 .. 3.3.2 Europe 1984-85 save without BIGC and with 90 or fewer cached teams loads into
the game's 68400-B cache; a world career's whole 'EN' block fits there only up to 76 cached teams (75 with S2b's 'US',
290 B), past that save_trailer drops 'EN' at runtime, as before.
**4.1 S2b (Shaved, 08/11):** 'US' 182 B + 4 (the career club's UEFA cup's earlier knockout stages, line below) →
'EN' 15554 B (27 items): 522 B left. **S2b LP (Davide 08/11):** + the league phase's final table, 108 B → 'US' 290 B,
'EN' 15662 B (27 items): **414 B left**.

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
| US | 290 | uesum (Shaved) | 4.1 S2b | RIEPILOGO's earlier knockout stages of the career club's own UEFA cup (uesum.c US_REC: u8 contest id, u8 ties per stage [play-offs, R16, QF, SF], u8 season stamp, 22 ties x 8 B - team words x / y, leg 1 / leg 2 / penalties as goals x << 4 | y, flags; then the league phase's final table: 36 team words + 36 u8 points, place order). Ties recorded at cseg_28E76's exit after every match, the table at lp36's lp_cb_gend; world_only (big worlds; 1984-85 carries a zero block). Clear: an older save loads it zeroed = the S2a page. With its header 294 B, on top of MC's 41-selroom (SEL_ROOM +640): **414 B left** |
| SWC1 | 32 | swe (engine P) | 4.1 | the engine's state: header (version, world, spec hash, season, flags, seed) + sections; grows by version |
| UP | 8 | uprize (Shaved) | 4.1 RC3 | the UEFA prizes already paid this season (uprize.c UP_ST); world-only; a save without it: zeroed = what is reached counts as paid (an older save); a new career: up_new |
| SWC1:IT | 0 dormant / 344 shaped | swe + sreg (Panchina N7) | 4.2 | SWC1's section 'IT' (not an item: inside SWC1, whose size grows by it): the club registry's identity map (sr_regsave: 12 B header + 10 bits a row; Italy 102 + 144 = 100 + 162 = 262 rows, MC 11/11: no pool rows, the 36 stand-ins off-file as in 4.1 -> 4 + 12 + 328 = 344 B). Dormant (0 B, SWC1 32) until a world has a registry shape (S7, piece 4); shaped Italy fits today's 506 B (162 left). Only World 2026-27 careers carry it (sreg.c's gate: SWC1's world byte = SREG_WORLD, the shape pack's 'world'); header +8 flags = sreg.c SREG_FLAGS (IMPORTED 1, PENDING 2, the pending import's season << 8). RI stays live for Italy on file 144 (MC 11/11, model (i): the RI row keeps its 2332 B, Italy's share 396 B); RB is dropped for Italy |
| LR | 404 | lrank (MC) | 4.2 S1.3 | the career league's head to head: one byte a pair of clubs (lrank.c LR_BLK, obj4); world-only; a save without it: void for that season |
| ST | 144 | swe / engine sr_stled.c (Panchina P6, MC A1) | 4.2 | a groups stage's state: 16 B key (season, purpose, entrants' FNV-1a) + groups + results, 8x4 2 legs (obj4+0x5000); world-only; absent = not started, redrawn |
| TR | 1 | trial (Mercato CPU) | 4.2.x | trial players: bits 0-3 the PROVA role (0 QUALSIASI, 1..8 = position 0..7), bit 4 QUALITA'+ off; all careers; a save without it: 0 = QUALSIASI with QUALITA'+ on |
| T3 | 1 | t3 (Mercato CPU) | 4.2.y | PRIMAVERA: the period code of the last youth signing (t3.c T3_ITEM: 1 + (currentSeasonNumber x 64 + week / 4) mod 255; 0 = none); all careers (not world_only); a save without it: 0 = none signed, the list open. With its header 5 B, as TR (MC's room note 12/11: 414 B of the .CAR fixed part left) |
| DF | 1 | difficulty (Difficoltà) | 4.2 | OPTIONS row DIFFICULTY: DF_W's low byte (0 = NORMAL); all careers (not world_only); after_load df_load / after_new df_new keep the session's level as cpucards. A save without it loads NORMAL. With its header 5 B, as TR / T3 |

## Engine P (2026-11-06, branch p-persist off engine = trymerge cd4e54c)

**Re-measured on the 4.1 recipe** (406-omm, c/HTOMM): 'EN' 15368 B (26 items) + main 948 → **68 B left** of SEL_ROOM.

- **SEL_ROOM + 207 B** (0x4000 → 0x40CF over the cache): all the room between the stage's end and B_UQ, nothing
  moved (B_SEL + SEL_ROOM still 945 B below B_STAGE). A constant, not an old-save-trap change: old saves are
  smaller. The other way round, a save of this build can be up to 207 B bigger than a 4.1 exe's room (a downgrade, not
  supported).
- **SWC1** (swe.c, obj4, 32 B in v1): the engine's state, one 'EN' item that *grows*. Header 20 B: u16 version (1),
  u16 world (the career's world byte), u32 spec hash, u16 season (P 5: seasonPlaying at the save), u16 flags, u64 seed (0 until the steps that use
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
- **The import path (P 3):** a load-only item with no old place (ITEM_AT) is read into its slot of swe.c's
  SWE_IMP (obj4 BSS, swe.imports()); swe.c sees -DIMPK_<name> (its found byte SWE_ENF[k] = trailer's EN_FOUND +
  EN_NS + k) and -DIMP_<name> (its slot). swe_st_load, on a save from before P only (SWC1_LOADED 0), runs
  swe_import: each retired item that was in the save becomes an SWC1 section (swc1_add; swc1_find reads one back).
  The step that retires an item adds its line there. A save with SWC1 never imports (its sections are the state).
- **Old saves' added items (P 3, test_roundtrip_old):** every item an archived save (3.3.6 .. 4.0.5) lacks comes in
  as zero, but SWC1 (started: version 1 + the career's world byte) and SH (a 4.0 save's split state moved in,
  sp_migrate) - asserted, so a new item with a non-zero old-save default needs its line here and in the test.
- Tier B: test_swc1.py (static image): the save, this build's load, shorter (grow) / longer / missing SWC1, a plain
  item of another length skipped, and (EN_RETIRE_PROBE=1 build) a load-only item read, never saved, imported as section 'RP' only into a save from
  before P (none from nothing, none over a save of P).

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
  - grow SEL_ROOM by moving B_STAGE, a change of the old-save-trap class that needs its own old-save gate (done once in
    4.1 for S2b, +640 B: the gaps are used up).
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
- Presets (.PRE) and seasons (.SEA) get no block in W-modes (engine P c, 2026-11-07):
  - **.SEA is SaveCareerFile's** (SaveContest's season branch calls j_SaveCareerFile): a season's save already carries
    the trailer and SWC1. SWC1's world is the career's byte only when the game type is a career (4); a season writes 0,
    since someLeaguesTable's byte is stale outside a career (it would be an earlier career's). A season's load already
    gives the base namespace back (engine_sea_ns: after a mixed friendly, WCUR = base).
  - **.PRE is the DIY file's body** (SavePresetCompetitionFile = SaveDIYFile, LoadPresetFile = LoadDIYFile). No preset
    of a career world exists yet, so a .PRE is never written with a block (no save hook: the file stays the game's).
    Its load goes through swe_diy_loaded (swe_pre_load_tramp at LoadOldCompetitionMenu's '.PRE' call): no 'WM' block,
    so the base namespace back. Before it, a preset loaded after a mixed friendly kept namespace 5 (engine_pre_ns).
  - When a world gets presets or seasons, their start sets the contest's world (SWE_CWORLD for a preset, then the
    preset save hook as the DIY one; SWC1's world for a season) - not before.

## Not save room: file 144's global numbers (S7-G, MC 11/11, option (i))

A club's global number indexes someLeaguesTable and leaguesTableCopy, and with them every save's table: a big
world's numbers 2000..2408 sit in the 80-record area (bigtables.LIMIT = 2409). World 2026-27 (world5tm-s1rank-int3)
leaves only 2283..2289 free, and S7's file 102 (Serie A + B + C, 256 -> 100 rows) gives up 192..347. File 144 (Serie
D 9 x 18 = 162 rows; the 36 stand-ins stay off-file, pool 253, as in 4.1) therefore takes two runs, from one function
(tools/globnum.py, `glob(pk, file, ordinal)`; `split(world)` gives the runs):

| file | ordinals | global numbers | rule |
|---|---|---|---|
| 144 (G144 = 192) | 0..155 (156) | 192..347 | run 1: the free numbers right after file 102's run (Serie D's 4.1 numbers) |
| 144 | 156..161 (6) | 2283..2288 | run 2: the lowest free numbers after the guest files (whose numbers stay 4.1's) |
| (free) | | 2289 | one spare |

- teamsCountryNumbers[144] = 192 (run 1). The exe gives run 2 through worldpool.wp_glob, the chain on
  SetTeamGlobalNumbers' store: in world 5's namespace (WCUR), ordinals >= 156 of file 144. uefacoef uc_g (team word ->
  global) does the same. In world 4, file 144 keeps its own one base.
- Refused, not worked around: no free numbers for both runs raises GlobError at the build.
- Old saves: the numbers 192..347 were Serie D's (file 102) in 4.1. 2283..2288 were free (no club, a 0 byte in
  someLeaguesTable). The old-save import re-keys the words (n7-s7-clubmap §3). The bytes someLeaguesTable keeps at
  192..347 are those of the 4.1 slots (102, 100..255), so the import must move them with the clubs (OPEN, import
  piece: not covered by S7-G).
- Dormant build (no league over two files): exe + DATA md5-identical to 42-s1rank 78fbf73.

## Not save room: the S7 redraw's rule version in the registry's 'IT' flags (4.2, 42-redrawc, MC 15/11)
- **0 B.** SWC1 section 'IT' (the club registry, sr_regsave) keeps its size: the u16 flags at +8 had bits 0 IMPORTED, 1 PENDING
  and 8..15 the pending import's season. Bits **4..7 now hold the S7 redraw's rule version** (s7swap.c `S7RD_RULE_VER`, 1 = the
  frozen rule of 42-redraw 31db319: integer, 1/100 degree, isqrt((4 dlat)^2 + (3 dlon)^2), integer Hungarian, STAY 540). The season
  end writes it after every redraw; 0 = no redraw season end yet (a new career, a save from before the redraw, an import).
  Bits 2..3 stay free.
- Old saves: every save we have reads 0 there today (host test `test_s7redraw_saves`: 1074 .CAR under internal/ on 15/11, 177 with an 'IT',
  bits 2..7 all 0), so they redraw with rule 1 from their next season end.
- A save from a NEWER build (version > S7RD_RULE_VER): the season end keeps its groups (the crossers' place() only, no redraw,
  `S7RD_NEWER` 1) and never lowers the version; no refusal, no crash (`test_s7redraw_fallback`).
