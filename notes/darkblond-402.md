# DONYELL MALEN (ROMA, darkblond) "pixel ammucchiati" - parked for 4.0.2

User report (site form, 4.0 GOG, Italian, JUVENTUS career): "MALEN della Roma compare come una serie di pixel
ammucchiati". Data: ita/players.csv `roma,DONYELL MALEN,...,darkblond` = face 3 (blond.py: dark skin + blond hair;
29 players of the World 2026-27 have it).

Findings so far (2026-10-24, Motore; scenario `world_darkblond`, remote runs internal/swostest/remote/dkb*):
1. Face icon OK on REL401rc3: a career at ROMA (DKB_TEAM=EUROPA,ITALIA,SERIE A,ROMA DKB_SQUAD=1), SQUADRA screen -
   MALEN's icon (189) has dark skin + yellow hair (remote/dkb4-rc3/world_darkblond/shots/squad.png).
2. The match sprite is not reproduced yet: in the harness, firing the visible "- PARTITA -" of the career match
   screen traps at obj1+0x38B79 (the game's own `int 3` in DIYLeagueTournamentMatch) on REL40hf and rc3 alike - a
   harness-input artifact (the suite always takes "- RISULTATO -"); an engine match in a world career needs another
   entry route (not built yet).
3. rc3 layout: blond's sprite sets at obj2+0x27F000..0x286800 (between the shirt-number sprites 0x27C000 and the
   menu-number sprites 0x286800): no overlap with careerworld's big-world areas (end ~0x1F6000) nor conti
   (0x264000..0x279FBF). The 4.0 build log has no addresses: the reporter's 4.0 layout is unverified.

User screenshot (2026-10-25, photo of a CRT/TV: internal/reports/malen_darkblond_match_20261025.jpg): IN THE MATCH,
at kick-off, ROMA 0-0 NAPOLI (Roma the home side, team 1), centre circle. The Roma player with the '14' marker stands
on the ball and his sprite is a garbled block about two to three sprites wide: columns of white / light blue / red /
dark pixels - Napoli's colours, not Roma's dark red (the Roma player to his right is drawn normally, as are the Napoli
players). So: the in-match darkblond set, standing frame(s) at least; the block's width and colours suggest frames
read with the wrong header / quad width and/or from a set converted with the other team's colour table (blond.py's
NEW1 / NEW2 sets: team 1 -> NEW1 - 341, team 2 -> NEW2 - 644; conv1 / conv2 after each team's third set).
Target for the reproduction: a ROMA career match with Malen in the XI, a frame of the pitch at kick-off (and the
sets' registration / pixels as blond_faces reads them), on REL40hf and the current build.

Unparked 2026-10-25 (Davide). Reproduction attempts, all CLEAN (darkblond players drawn right; scenario
world_darkblond's exact check: every frame of both teams' darkblond sets = the team's black-skin set in size and pixel
positions, yellow hair, the three skin / hair sets the same size, each raw set 15216 B within copy_sets' 15360):
- REL401rc3 CD: a World 2026-27 career at ROMA, its first match played (ROMA v NAPOLI / UDINESE), kick-off frames;
- REL40hf CD and GOG exe, REL40rc12 (4.0 of 22/10) GOG exe: the same, Roma home and away (MONZA v ROMA);
- 1996-97 friendlies on rc3 with all outfield players of FIORENTINA / ROMA forced to face 3: human v CPU, CPU v CPU,
  a second match in the same session (JUVENTUS v MILAN first), the post-match REPLAY;
- GOG data files (TEAM1/2/3.DAT, CHARSET.DAT, internal/joypad-gog) are identical to the CD's.
Harness note: the league fixture's '- PARTITA -' runs DIYLeagueTournamentMatch, whose first instruction is the game's
own `int 3` (the original exe too): harmless on a real PC, a trap under the harness's BPINT 3 - world_darkblond NOPs it
in a test copy. The reporter's photo (zoomed): a block ~4 columns x 6 rows of single-line pieces in light blue /
white (Napoli) AND dark red (Roma): as if a frame were drawn with a wrong header (width / lines) over data running
across the end of the Roma set (NEW1) into the Napoli set (NEW2) - not reproduced in any run above.
Questions for the reporter: played or watched (VIS. PARTITA / highlights)? first half or after a goal / half-time?
every match with Malen or once? exact install (patcher version, SWOS++?, own DOSBox / GOG DOSBox and its conf)?
a career started on an older version? the .CAR if possible.

Next (4.0.2): ask the reporter WHERE it shows (squad list, match, stadium screen) + a screenshot; then the match
route (stadium little players + Malen on the pitch) on REL40hf and the current build. Estimate 2-4 h.
