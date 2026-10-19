# World 2026-27: the other confederations' club cups (4.0, integrator, started 2026-10-20)

Davide: 4.0 ships with every confederation's club cups in the World 2026-27 career, in their real formats: CONMEBOL
(Libertadores, Sudamericana, Recopa), CONCACAF (Champions Cup + the Central American / Caribbean Cups that feed it),
AFC (Champions League Elite, Two, Challenge League), CAF (Champions League, Confederation Cup, Super Cup), OFC
(Champions League), FIFA (Intercontinental Cup; the Club World Cup if it falls in the world's seasons). CONMEBOL
first.

## Why not the 1996-97 machinery
sacups.py runs the 1997 South American cups as contests of the South America continent; a career club's cup goes
into season slot 3 (E092F 3..5), and at the season end sa_qualify re-simulates every South American league from the
1996-97 country structs and reads the tables by global team number. A world's clubs reuse those numbers: wrong
tables and club counts, cseg_3283C's trap. careerworld.late skips it in every world, so no world club ever entered a
non-UEFA cup. The new layer keeps the safe ideas (a career club plays its cup in slot 3; the game's own type-1 / type-2
contests) and replaces the rest.

## The generic layer: one cup = format + access, the career club's path = segments in slot 3
- **conti.c** (C, uefaq-style, its own obj1 pages + .bss, state in the engine block): every cup of every
  confederation is DATA: a format (rounds) + an access list (per association: places by league rank, the cup
  winner, the holders, the clubs dropping in from another cup's round). One C engine:
  - collects at the season end each world country's final top list + cup winner (+ Argentina's stage titles from
    GP_SS / gplay's stage_title), for every confederation (the season end's country loop, next to uefaq's
    uq_country);
  - makes the next editions' entrants from them (the access lists), the holders included;
  - draws (pots by the confederation's ranking, no two clubs of one association in a group / tie when the rules say
    so, fixed pairings when the format has them);
  - simulates every round the career club does not play (strengths: the 16 players' prices, as uefaq), world-wide,
    so every cup has a winner, a runner-up and the next season's holders;
  - keeps every club's path (round reached) for the honours and the season review.
- **The career club's path**: the rounds it plays are SEGMENTS, each a contest of the game's own built in slot 3
  (free for a non-UEFA club): a knockout round / several (type 1), a group stage (type 2: groups, the team list in
  our drawn order), a league stage (lp36's engine, ACL Elite). At a segment's end (its contest over) the game's
  results go back to conti.c, the other clubs of that round are simulated, and the next segment is built in slot 3
  (gplay's 'FEh calendar' trick for the old entries). Cross-cup moves are just a next segment in another cup
  (Libertadores Q3 loser -> Sudamericana groups; a Libertadores group 3rd -> the Sudamericana play-off).
- **Calendar**: one edition per world season, named for its year (2026-27 plays the 2027 editions), its rounds spread
  over the season's months by the format's own month list (package 6: qualifying Aug-Sep, groups Oct-Dec, play-offs
  Jan, knockouts Feb-Apr, finals May); entrants from the previous world season (made at its end). Season 1: the real
  2027 entrants where known, else the real 2026 tables (data).
- **Honours**: the contest ids / names per cup (4 languages); the trophy and the season record through D8CBE / the
  record lines as the UEFA cups; FORMAT pages + zones (the confed colours become real).

## Data format (package 6: formats; data: access lists, entrants, names)
One JSON per confederation, `packs/.../continental/<conf>.json` (or internal while drafting):
```
{"conf": "conmebol", "ranking": {"<pack key>": points, ...},          # (pots; frozen 2025 for 4.0)
 "cups": [
  {"key": "lib", "names": {"it": ["COPA LIBERTADORES", "LIBERTADORES"], "en": [...], ...},
   "rounds": [                                                         # in order; each: kind + its rule
     {"key": "q1", "kind": "ko", "legs": 2, "level": "pens", "draw": {"pots": 2, "same_assoc": "allow_if_via"},
      "month": 8},
     {"key": "q2", "kind": "ko", ...}, {"key": "q3", ...},
     {"key": "groups", "kind": "groups", "groups": 8, "size": 4, "rounds": 2,
      "draw": {"pots": 4, "same_assoc": "no", "holder": "A1"}, "months": [10, 11, 12],
      "out": {"1": "r16", "2": "r16", "3": "sud:po"}},                  # where each place goes
     {"key": "r16", "kind": "ko", "legs": 2, "level": "pens", "draw": "seeded_1v2", "month": 2}, ...,
     {"key": "final", "kind": "ko", "legs": 1, "level": "et_pens", "host": "neutral", "month": 5}],
   "losers": {"q3": "sud:groups"},                                     # where a round's losers go
   "access": {"bra": [["groups", 5], ["q2", 2]], "arg": [["groups", 5], ["q2", 1]], ...,
              "holders": {"lib": "groups", "sud": "groups"}},          # by league rank in order; "cup" = cup winner
   "entrants_season1": [...]}, ...]}
```
Entry codes as uefaq.c's AL (champion 0, cup winner 1, k-th place k); single-table associations' Apertura /
Clausura champion places map to the table's 1st / 2nd (declared, 4.0; exact with their split seasons in 4.0.1).

## Engine facts (checked)
- A world's season end walks EVERY world country (careerworld w_list: the world record's list, not seasonEndList):
  for each, `call cseg_91393` (its season end: tables, the top 9 records in STAND, the cup winner) then
  `call cseg_93974` (obj1 0x812f6 / 0x8133e in the IT exe).
- cseg_93974 returns at once for a country whose continent byte is not 0 (Europe): the UEFA hooks (w_q_cl ->
  uq_country) never see a non-European country. conti.py hooks those two `call cseg_93974` instead: the country's
  top list + cup winner into conti.c's input, then on to cseg_93974.

## Phases / owners
1. Engine core (integrator): conti.c (collect, entrants, draws, simulation, holders, paths, state) + conti.py (data ->
   bytes, sites, build) + the season-end hook + save / load. CONMEBOL data as the first user.
2. Slot-3 segments (integrator): contest building from the C state, segment end -> back to C, the rebuild.
3. Honours / FORMAT / zones / notes (3.3.6 + regia), names (data).
4. CONMEBOL data (package 6 formats, data access lists + season-1 entrants, ranking join) and scenarios (Serie C).
5. Other confederations: data + formats on the same engine (+ ACL Elite's league stage through lp36's engine).
6. FIFA Intercontinental (single matches between the confederations' winners) / Club World Cup if in range.
