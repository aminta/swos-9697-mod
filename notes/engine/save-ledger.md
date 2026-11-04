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
| FF | 15 | ffp (Integratore; state in finance.py FF_ST) | 4.0.6 (after I10j) | financial fair play: FF_ON, FF_BLOCK, FF_VALID (1 B each), FF_INC (the season's gates), FF_IPREV (last season's income), FF_FINE (dd each). Plain bytes, no pointers, clear: an older save loads it zeroed = the rule OFF; a new career sets ON + VALID (after_new). With its header 19 B: **74 B left** on I10j + FFP |

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
