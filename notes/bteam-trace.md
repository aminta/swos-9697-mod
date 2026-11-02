# B-team call-ups (4.0.6) — step 1: the careerTeam walkers (trace, 2026-11-02)

Feature (Regia/Davide 02/11): (1) one-match call-up of B-team players (U23, GK any age, per-country over-age caps, max 4
per match, automatic return, no finances); (2) season attachment (max 3 per window, windows only, generated replacement
in the B record, wages). Base 406-kbd2 836edaa; obj3 after kbd2.

## Facts (ref/swos.asm)
- 132 procs touch careerTeam / careerNumPlayers / currentMatchPlayers (script: enclosing proc of every reference).
  Most are match-time (team pointer compares, in-game structures) or display.
- **Byte +71h of the player (GetPlayerAtIndex A0 + 113) is NOT a free flag.** It is a signed per-player value
  -100..+100 (cseg_908B4 after a match: adds, clamps to 64h / 9Ch = -100; cseg_64E3E the same) with two markers out
  of range: 9Ah (-102) = reserve, 9Bh (-101) = trial. About 15 procs test the two markers in pairs. A new marker
  (e.g. 99h) would be clamped back to -100 by cseg_908B4 / cseg_64E3E -> **no new flag value**; the borrowed players
  are kept in our own list (trailer chunk), keyed by identity (B team word + index + name), not by slot (slots move:
  cseg_52EA6 / RemovePlayerFromTeam compact the squad).
- CheckPlayersLeavingComing (weekly): only 9Ah / 9Bh players leave; trial joins while < 30. A borrowed player (normal
  value) never leaves by itself; the trial join counts him (fine).

## Walkers that matter (career state outside the match)
| Group | Procs | Borrowed player must |
|---|---|---|
| Add / remove | cseg_52956 (filler add), cseg_52EA6 (remove + compaction, also from RemovePlayerFromTeam, cseg_56129), cseg_56379 (purchase into careerTeam; writes a generated replacement into the seller's record via cseg_56615) | reuse: add = the purchase copy; return = cseg_52EA6-style removal |
| Fillers | cseg_52588 (ShowPlayMatchMenu, PlayTrainingGame): counts keepers / fit outfield over careerNumPlayers | count as available (wanted) |
| Wages | cseg_5E345 (per slot), cseg_5DEB9 (season start, InitializeNewSeason) | (1) wage 0; (2) the game's wage |
| Selling | PutPlayerOnMarketMenu, PlayerOffersOnSelect10/11/12 (cseg_584D7), GiveFreeTransfer | not listable / not sellable |
| CPU bids for our players | cseg_5A8DE -> cseg_5A90B -> cseg_5AB36 / cseg_5B468 / cseg_5B518 | skipped |
| Accepting offers | cseg_55F53, cseg_592D5 -> cseg_547AC / cseg_56129 | never reached (no bids) |
| Season start | InitializeNewSeason: cseg_5CDF2, cseg_5DEB9, FillCareerTeamPlayers (price range via GetLowestAndHighestPlayerPrice) | (2) returned before it |
| Job change | cseg_942F2 -> cseg_5A6A1 (first 16 written back to the old club's record, careerNumPlayers = 16) | returned before it |
| National selector | SelectNationalTeam*, cseg_5C7D3 / cseg_5CC6F / cseg_5CFE2 (isNationalSelector: careerTeam is the national squad) | feature off for a national selector |
| After the match | cseg_2AE97 / cseg_88688 -> cseg_908B4 (form, injuries); cseg_903B1 / cseg_9072A (simulated view result) | (1) the return hook runs after these |

## The 'generated' bit does most of the guarding
Byte 26 of the PlayerFile (`positionAndFace`, A0+66h) bit 1 = 'generated' (the fillers). Tested (15 sites) by:
- **selling / offers**: PutPlayerOnMarketMenu, PlayerOffersOnSelect10 / 11 -> a generated player cannot be listed or
  offered;
- **CPU bids**: cseg_5A90B, cseg_5B468, cseg_5B518 -> never bid for;
- display: SquadAfterDrawCommon, cseg_247C8, EditTacticsAfterDrawPlayerNames, cseg_54116 (own name colour);
- fillers: cseg_52588 (x2), cseg_3A2CE (x3) -> counts, and the surplus removal of a generated player (cseg_52EA6).
So a borrowed player = his 38 bytes copied with bit 1 set: unsellable and never bid for at no cost, shown in the
fillers' colour. The one thing to guard: cseg_52588's surplus removal must not pick a borrowed one (our list) - one
hook. Nothing to clear at the return: the player leaves careerTeam, and the B record holds his original bytes.

## Plan of hooks (to confirm site by site in the build)
- add: our routine = cseg_56379's copy without the money / seller part (1), with it at price 0 + the game's own
  generated replacement in the B record (2); bit 1 set; entry in our list (chunk 'BU': B team word, idx, kind, name).
- return (1): at the start of the calendar advance (gp_adv chain, after the match and its cseg_908B4 update): every
  kind-1 entry removed (cseg_52EA6-style compaction, currentMatchPlayers kept consistent), list cleared.
- return (2): before InitializeNewSeason in ContinueCareerNextSeason, and before cseg_942F2 (job change): the
  player's bytes back into the B record slot (replacing the generated one), removed from careerTeam.
- guard: cseg_52588 surplus removal skips borrowed; feature off when isNationalSelector.
- no new flag value (+71h is form, see above).
