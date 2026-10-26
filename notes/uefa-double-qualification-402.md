# European places, double qualification (4.0.2): findings and open points

Data session, 2026-10-25. Branch `uefa402`. User Pietro, World 2026-27 (4.0.1): MILAN won Serie A AND the Conference League in
2027-28, was placed in the Europa League in 2028-29 instead of the Champions League.

## Cause (tools/uefaq.c, uq_season)
The holder's status was 'league' (the holder uses its domestic place) only when its domestic place is in ITS OWN cup's league
phase (the UECL winner: EL_LS). A UECL winner with a domestic Champions League place was 'own': it got the holder's Europa
League place and its domestic CL place was passed down (native replay: status [0,0,2], Italy's CL clubs 5 -> 4).

## Fix
1. uq_season: the UECL holder with a domestic CL_LS place is 'league' too.
2. UQ_OUT.hkeep[2]: that holder is already in the CL league-phase list; the game's lists (gl) keep it there, nothing is
   routed to the EL list (want counts and the taken[] exclusion skip it).
3. uefaq.py uq_fill: no exclusion of a kept holder; w_hkeep[2] is set from UQ_OUT.hkeep; careerworld.w_holders skips a row
   whose w_hkeep is set (it appended the holder to the EL list). Clearing the holder word to FFFFh trapped the new season
   (obj1+0x81390): the game reads it later.

## Verified
- Native replay of uefaq.c on a real UQ_IN dump (about 4000 random holder combinations: league + UECL / UEL / UCL, cup
  winners, outsiders): the three game lists 36 each, no club in two lists, hkeep only when the holder is in the CL list.
- Natural in-game flow on the fix build (world_full_uefa, UQ_BSS=186000 UQ_BP=b5000 for the 401rc3 build): PASS.
- Unchanged and right before: league + UEL (status 'league', the vacated place rebalanced), league + UCL, UCL holder.

## Open points
(a) THE FORCED IN-GAME CHECK is missing. UQ_HOLD (swostest, pokes UQ_IN.hold and the game's holder words at the uq_season call)
    traps the new season even in a control case that does not touch the fix (UQ_HOLD_CASE=x,x,2:8). Probably the holder
    words have no matching record in the game's saved-holder buffers. world_uefa_double is committed as WIP and FAILs until
    the forcing is reworked (the Integratore, at 4.0.2 rc time), or until a real save is available: Pietro's file
    internal/reports/pietro_MILAN_20261025.CAR holds NARDO / GRAEME BOXALL at the start of the world, not Milan's career;
    ask for a save of 2027-28 before the season end.
(b) The classic holder rules (w_pick_cc / WH_SAVE: a champion that holds the CWC / UEFA Cup plays the Champions Cup) are old
    rules of the 1996-97 lists; not touched, probably unrelated.
(c) National cup winner + league place: the model's assign() shifts the cup winner's place to the next league club; no
    violation in the random combinations, not tested in-game.
(d) A holder in a higher list and the record-count checks (w_chk_tot*): not exercised in-game by a forced case (see a).

Build notes: the 401 build moved uq_season (obj1+0xb5000) and the bss (obj2+0x186000) from the 4.0 values (0xb0000 / 0x183000):
read both from the patch log line 'UEFA qualifying rounds' (patch.patch_exe prints it) before using UQ_BP / UQ_BSS.
