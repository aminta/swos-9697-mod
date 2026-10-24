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

Next (4.0.2): ask the reporter WHERE it shows (squad list, match, stadium screen) + a screenshot; then the match
route (stadium little players + Malen on the pitch) on REL40hf and the current build. Estimate 2-4 h.
