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

## Data: birth years (Dati coppe, 02/11)
players.csv column 'born' (yyyy) between 'skin' and 'pa', snapshots world5tm-403c10b and world5tm-403c11b (403c11 +
that players.csv, the release recipe's base). mkseason reads players.csv by header, so the extra column is harmless.
B teams: 577 rows, 34 empty (AUS sydneyii / westsydneyii / melbournecity2 27, ned utrechtu21 1, nzl 6): empty = age
unknown -> callable, not counted as over-age (to state in the notes).

## Davide's answers (via Regia, 02/11)
- (a) Windows for the SEASON ATTACHMENT only = the real transfer windows per country, from the world calendar's
  dates (Europe: summer to 1 Sep, winter 1 Jan - early Feb; AUS / NZ and others by their real dates). One table in one
  place; the dates in the notes. The normal market and the one-match call-ups stay open all year (do not touch).
- (b) Button on the club's squad screen; free entries to agree with Panchina (sqnum / benchx live there).
- (c) Texts approved as proposed (IT/EN/FR/DE, list sent to Regia 02/11).
- (d) Borrowed player marker: the fillers' colour AND a letter "B" next to the shirt number.

## Re-base onto 406-i7c acaff0d (Shaved, 2026-11-03)
Trace commits moved onto branch 406-bteam2 (off 406-i7c). Hook points re-checked against i7c's tools:
- **obj3**: the chain ends at stoppage -> xleft -> usc_snap -> stadium -> (conti view); REL406i7c build.log: obj3 end
  0x885c..0x897c, **1668-1956 B left** before LT3_AT (OBJ3_PAGES = 10). Panchina's cpurefill (uncommitted) also goes at
  the chain's end, then MC's ctgame. bteam (code + the squad-screen menu copy + tables, ~4-5 KB) does NOT fit:
  **OBJ3_PAGES 10 -> 11** (or 12 with ctgame + cpurefill), a single constant; Integratore to set the order.
- **Purchase tail (conflict)**: cseg_56379's last call (SOLD_SITE -> cseg_56615, the invented replacement) is now a
  chain: xtra (xt_sold) -> xleft (xl_sold) -> cpurefill (cr_sold, FROM SQUAD swaps an XTRA player in). Attachment (2)
  must NOT run through cseg_56379 as a purchase: own copy routine + a direct call of cseg_56615 for the replacement in
  the B record (AddCareerPoolPlayer entry kept, so the B club keeps it at reloads), with a 'bteam' flag the chain
  members skip (no XS/XL entry, no cpurefill swap, no money, no xt_sold mark). The return (2) writes the original back
  into the record slot AND that change-list entry.
- **XTRA B players (places 17+)**: they live in xtra/xleft (XS bought / XL left lists, 32 entries). Calling one up
  needs XS/XL bookkeeping both ways. Option: callable = the B team's 16 + its XTRA block (full spec), or the 16 only.
- **xleft**: cseg_52EA6 (xl_rm, removal + compaction) and cseg_942F2 (xl_job) are hooked; return (1) by our own removal
  must keep xl_rm's bookkeeping right (a borrowed player is not an XTRA leaver); return (2) before cseg_942F2 chains
  in front of xl_job. 4.0.2 idx>=16 overflow fix (cseg_243BD) is in i7c: our copy never goes through idx>=16 slots.
- **Wages**: cseg_5E345 is hooked by finance.py (and xtra): (1) wage 0 = a chained check in front of finance's hook.
- **Save**: BU as an engine item (engine.save_item('BU', ~84 B: 10 entries x 8 B + count), world_only), not a raw
  trailer chunk. i7c EN block 15244 B, "EN saved with up to 97 cached teams": +84 B may cost one cached team (check).
- **Squad screen**: button (a) 45x15 left of ESCI (x = live ESCI.x - 46) still valid; sqnum / benchx after-draws are
  chained there (squadnum HL_SITE marker + the 'B' letter) - re-measure ESCI in the 4 languages at step 1.
- Unchanged: cseg_52588 (filler surplus) unhooked; gp_adv chain (gplay) for return (1); InitializeNewSeason chain
  (xtra, sacups, ...) for return (2).

## Design for M2 / M3 (Shaved, 2026-11-03, after Davide's GO: full spec, places 17+ too)
- **Purchase copy, as the game does it (cseg_56379)**: GetPlayer(seller D0, D1) -> A1; the lowest free careerTeam slot
  D1 (not in currentMatchPlayers); GetPlayer(selTeamNumber, slot) -> A0; cseg_63919; A1+66h |= 4; A1+6Dh..70h = 0;
  38 bytes A1+4Ch -> A0+4Ch; the slot inserted in currentMatchPlayers after the match's 11 + bench (competition
  file's +65h / +4Dh, + 0Bh); SetBenchPlayersNumbers; careerNumPlayers++; cseg_5E345 (wage); cseg_56615 (the
  seller's invented replacement, SOLD_SITE = the chain xt_sold -> xl_sold -> cr_sold). bteam's bt_add = this copy
  without the money / chain: bit 1 (generated) set instead of bit 2, the wage hook (1: 0; 2: the game's).
- **Places 17+** (an XTRA block, static DATA\\XTWn.nnn): read through xtra's xt_block (the market's block cache,
  xl_readto blanks XL entries). A borrowed XTRA player needs no replacement (as the market: no invented one for 17+)
  and nothing at his return (the block is static). While borrowed he must not be buyable from the B club's block:
  xt_block chained -> names in BU blanked (as XS / XL).
- **BU entry (8 B)**: db kind (1 match / 2 season), db B index (0..29), dw B team word, dd name hash (22-byte name,
  before bit / stat changes). 10 entries (4 + 2 windows x 3). Return finds the careerTeam slot by the hash.
- **Return (2), index < 16**: the B record holds the generated replacement (cseg_56615 called directly, D0 = B word,
  D1 = index: AddCareerPoolPlayer entry (team, index) in careerForeignMarketPlayers). Back: the careerTeam copy (bit 1
  cleared) overwrites that change-list entry's 38 bytes AND the cached record slot (if cached); then cseg_52EA6-style
  removal from careerTeam (xl_rm told: not an XTRA leaver - bteam flag).
- **Age**: U23 = age code (birth - 1900) >= season's first year - 1900 - U23 limit (season year from the career's
  season counter); 0 = unknown -> callable, not over-age. GK: any age, not counted as over-age.
- **Windows**: current week = CAL[CAL_CUR].week (gplay gp_week); open if first <= week <= last for a window of the
  B team's rules (BAGE 'BR'); per-window count of (2) kept in BU (entries of kind 2 with their window number in the
  high bit of kind).
- **UI (M3)**: squad screen (squadMenu, the career club only, not a national selector, the club has a B team):
  'SQ. B' 45x15 left of ESCI -> the B page (menu copy in obj3 as kbd2 / cpurefill): the B squad (name, role, age,
  'U23' / over-age mark), select -> 'SOLO PROSSIMA PARTITA' / 'PER LA STAGIONE'; refusals: MAX 4 PER PARTITA, TROPPI
  FUORI QUOTA, MERCATO CHIUSO, ROSA PIENA (careerNumPlayers >= 30: the game's own trial cap), ANCORA %d PER LA
  STAGIONE. Marker on the squad screen: fillers' colour (bit 1) + a 'B' after the shirt number (se_hl chain).

## AUS / NZ rules, researched (Shaved, 2026-11-03, Regia: "look up the real 2026-27 rules")
- **Windows, Australia (A-League + NPL men), exact**: Football Australia Domestic Match Calendar 2026/27, "Men's Transfer
  Windows": 12-week window 24 June - 15 September 2026; 4-week window 12 January - 8 February 2027.
  Source: https://footballaustralia.com.au/sites/default/files/2026-07/260526%20-%20DMC%2026-27%20-%20For%20Public%20Release.pdf
- **Windows, New Zealand clubs**: AUCKLAND and WELLINGTON are A-League clubs (registered through Football Australia), so
  their first-team call-ups follow the same FA windows as above. No NZ Football 2026 National League registration
  window was found (nzfootball.co.nz: no 2026 regulations page found).
- **Over-age, Australia: none allowed (cap 0)** - the A-League clubs' NPL sides are U23 squads:
  - NSW (SYDNEY II, WEST SYDNEY II): Football NSW 2026 Competitions Regulations, section 3.2 "A-League Men's (ALM)
    Academy Clubs": 1st grade players born between 1 January 2003 and 31 December 2010; 3.2.c the goalkeeper
    exception applies only to the U20 competition.
    https://footballnsw.com.au/wp-content/uploads/sites/33/2025/12/20251219-LEG-2026-Competition-Regulations-Official-v1.pdf
  - VIC (MELBOURNE CITY 2): Football Victoria 2026 Advanced Competitions Rules of Competition, 6.1.8 "The A-League
    Club's Senior (NPL/VPL) side must consist of players no older than the age of 23 (born in 2003)".
    https://footballvictoria.com.au/sites/ffv/files/2026-02/2026%20Advanced%20Competitions%20Rules%20of%20Competition%20-%20FINAL.pdf
  - QLD (BRISBANE ROAR 2): Football Queensland 2026 Advanced Leagues Rules of Competition, f) "Players registering
    to Brisbane Roar NPL Men's Team must be under the age of 23 (born 2003 or later)"; exemptions only on application.
    https://footballqueensland.com.au/wp-content/uploads/2025/10/2026-Football-Queensland-Advanced-Leagues-Rules-of-Competition.pdf
  - No goalkeeper exception in the three (the engine gives a goalkeeper any age: a difference, asked to Regia).
- **Over-age, New Zealand reserves (AUCKLAND FC RES, PHOENIX RES.)**: NOT FOUND in an official 2026 source. Only
  Wikipedia (Wellington Phoenix FC Reserves): "up to four professional players are eligible to play for the reserves"
  + two U20s by agreement - a limit on first-team pros playing down, not an age cap. Asked to Regia before choosing.
