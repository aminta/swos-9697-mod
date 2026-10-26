# Buying players 17-30 of other clubs (4.0.2 design note, 2026-10-26; nothing coded)

## What the game does (ref/swos.asm)
- Home market = `homeMarketPlayers` (max 25 entries x 4 bytes): word = team number (low byte team file, high byte club ordinal),
  byte = player index 0..15 in that club's record, 1 pad. Filled by `FillCareerTeamPlayers` (InitializeNewSeason) and refilled
  by `cseg_5509D` (weekly: drops random entries via `cseg_8DF16`, adds with `AddCareerTeamPlayer` up to 25).
- `AddCareerTeamPlayer`: random club of the SAME country (the career's selected-teams buffer), random index `Rand2 & 0xF`,
  accepted when its price is within [lowest, highest + 3] of the managed squad, not a midfielder/bench (shirtNumber bit 2 test),
  not already listed (`IsPlayerInCareerContest`), then `AddPlayerToCareerContest` stores (team, index).
- Display / pick (`cseg_5A227` list, `cseg_5A4FE` filter): per entry `VerifyTeamLoaded(team)` -> A0 = team record, then
  `+ index * 0x26 (38)` -> the PlayerFile. Index >= 16 would run into the next club's record: every consumer computes the pointer
  this way (about 40 `VerifyTeamLoaded` callers in the exe; the market ones: list, view, offer/buy `BuyPlayerMenu` -> `cseg_54063`,
  `cseg_55F53` offers, `RemovePlayerFromTeam` -> `cseg_546DF`/`cseg_547AC`).
- Foreign market = POOLPLYR.DAT (900 fixed players, `AddRandomForeignMarketPlayer`): untouched by this work.
- Purchase: the player's 38 bytes are copied into the next free slot of `careerTeam` (cap `careerNumPlayers`, `cseg_547AC` drops
  offers at 32), the seller club loses him through `RemovePlayerFromTeam` (rewrites the 16 of the seller's record).

## Design
1. **Index 16..29 = the club's XTRA player (idx-16).** Entries keep the same 4-byte format, so the list, `IsPlayerInCareerContest`,
   the weekly drop/refill and the .CAR (homeMarketPlayers sits in the fixed part) need no format change.
2. **One pointer helper** `xt_player(team, idx)` replacing `team + 76 + idx*38` at the market consumers: idx < 16 as the game,
   else a pointer into a small cache of XTRA blocks (the club's file read once, 2-4 files cached, the same `int 21h` read as
   xtra_read; sold players zeroed in the cache). Needs a trace of each consumer's pointer arithmetic (list, view, offer, buy): ~6 sites.
3. **Picking** (`AddCareerTeamPlayer`): index drawn from 0..(16+count-1) of the chosen club (count from the XTRA header); the price test uses
   the extra's price (already capped <= the weakest of its club's 16, so they are cheap players: right for small managed clubs,
   rarely in range for rich ones - to accept; wage from our scale = the game's own formula over price, 66%/33% flags unchanged).
4. **Buying an extra**: the 38 bytes go into our squad exactly like a normal purchase; instead of `RemovePlayerFromTeam` on the
   seller's record (it would rewrite the 16 and shift players), the player is added to the **sold list**. Cap: purchase blocked
   by the game at 32; our fillers stop at 30 (as now).
5. **State = sold list in the .CAR trailer** (the mod already writes chunks there: 'C1'..'C3', 'S3'...): new chunk 'XS' = n + n x
   (team word, extra idx), written at save, read at load; applied (a) in the XTRA cache (zeroed names) and (b) in `xtra_load`
   (a club we later manage does not get a player we bought). Old saves have no chunk = empty list (loads as before); a chunk read by
   an old exe is ignored. Max 25-50 entries a season is enough; cap 256.
6. Not in scope: CPU clubs never trade; a bought player also bought by another club does not exist (CPU clubs do not buy).

## Risks
- The 6-ish pointer sites (one missed = reads the next club's bytes or int 3): mitigated by a scenario per screen (list, view, offer, buy, sell).
- Idx >= 16 entries left in a saved homeMarketPlayers when an old exe loads the save (not supported, one-way).
- homeMarketPlayers weekly refill picks the managed club's own file/ordinal: skip entries of the managed club itself (already the game's rule).

## Plan and estimate (own branch off the tip after xsq-402; NO merge)
| Step | Work | h |
|---|---|---|
| 1 | trace the market consumers' pointer arithmetic, list them in ref/addrmap | 2-3 |
| 2 | xt_player + XTRA multi-file cache + idx range in AddCareerTeamPlayer | 3-4 |
| 3 | buy path: skip RemovePlayerFromTeam for idx >= 16, sold list, wages/cap | 2-3 |
| 4 | .CAR trailer chunk 'XS' + old-save check (feedback_swos_load_hooks) | 2 |
| 5 | scenarios: list shows an extra (name/price), buy it, squad = n+1, not buyable twice, season + save/reload, old 4.0.1 save, career_20seasons x2 | 4-5 |
Total about 13-17 h (2-3 sessions). Test case: a Serie D career sees a Celle Varazze extra in the market, buys it, it is gone from the list and
from Celle Varazze's block after a reload.

## As built (2026-10-26, branch xsq-402)
Everything is in tools/xtra.py (cave code, same page group; patch.py gives the xtra pages one more page when XTRA is on).
- `xtra_readto` (ax = team word, edi = dest) is xtra_read's file reader made general; `xt_block` = cache of 4 clubs' blocks (round
  robin, flushed when the world's XTRA name changes), entry = dw team, db players, db valid, 14 x 38.
- **GetPlayer is the one accessor**: its `call GetTeamPointer` -> `gp_wide` (D1 >= 16 of another club -> A0 so that A0 + idx*38 = the
  XTRA slot). That covers the offer / buy / third-party flow (about 14 functions). Two sites do their own `team + idx*38`:
  the market row (cseg_5A017: `mov [A0], eax` -> mp_a6) and the market list (cseg_5A227: `add [A0], eax` -> mp_a1).
- AddCareerTeamPlayer: after its index draw (`mov [D2+2], dx` -> `xt_pick`): one Rand2, uniform over 16 + extras; a blank slot (bought)
  keeps the game's own pick. The weekly refill and cseg_8DF16 / IsPlayerInCareerContest need nothing (entries keep the 4-byte format).
- **Sold list**: cseg_56379's last `call cseg_56615` -> `xt_sold` (D0 team, D1 idx restored; the player was already copied): index >= 16 of
  another club -> (team word, index) in `xsold` (128 x 3 B, marker 'XSLD' for the harness), the cache block blanked. Not applied to
  xtra_load / wages (a club managed later gets its block back: the bought player left with us). Saved as engine item 'XS' (world_only,
  `engine.save_item` + ITEM_AT in xtra.patch); an old save has none -> zeroed at load.
- The 30-player cap is the game's own (cseg_584D7: TOO_LARGE_SQUAD above 30): a 30-man club must sell first.
- Seen: the weekly market of CHISOLA had 3 XTRA players among 13 entries; the list / offer / squad screens show them (shots in the run dir).
- Tests: `xtra_market` (XTRA30_BUILD; CHISOLA buys a LIGORNA extra, list / offer / squad / save / reload / list again / match day);
  career_20seasons x3 at CHISOLA, an old 25-man save on the new exe, xtra_world30, xtra_squad, xtra_season.
- Users: a 4.0.2 save whose market lists such a player (or whose sold list is not empty) is one-way: older versions would read index
  16.. past the club's record. Release-note line to add.
