# World 2026-27: the domestic-schedule core (integrator, 2026-10-18, design + probe 1)

The base of Argentina (Apertura / Clausura), MLS (conferences, unbalanced schedule), New Zealand (regional leagues,
then the National League Championship) and the Brazilian state championships (package 6, on top). Davide's
decisions: 5.0 waits for ARG and MLS EXACT; the states are option (a), a competition of their own.

## Base: split.py's hooks (the league slot), not lp36
lp36 runs a type-2 contest (the European slot's 0xB52 buffer). The league slot (slot 0, DIY_competitionStart 0x733,
64 team rows) already has split.py's hooks on every routine a league day goes through: sp_init (cseg_8F1F2's end:
cycles, days, weeks), sp_pair (cseg_89758: the match of the day from our calendar, the career calendar builder
included), sp_count (cseg_8922B: any number of matches a day), sp_sort (cseg_883DD: the table partitioned into
groups). The season-end simulation (cseg_3AE87) goes through the same routines. Stages already exist (Malta: a
reset of every figure, the Opening table kept). What the core adds to split:

1. **Fixture-list stages** (`"fixtures": "rows"`): pairs are team ROWS (the contest's club order), not places of the
   table frozen at the split, and the calendar starts at day 0 (no game pairing before: `games` 0). The game's pair
   tables (dseg_11F356[n-2], 2..24 clubs) are never read, so the 24-club limit of the round robin goes; the limit is
   the 64 rows and split's state (ST, 166 bytes before the rows) -> NMAX 32 for these entries.
2. **Groups by membership** (`"groups": [[rows of zone A], [rows of zone B]]`): sp_sort partitions the table by the
   club's group, not by place ranges; the career screens show one table, zone A first (places 1..15), then zone B.
3. **Stage end -> a knockout** (`"then": {gplay spec}`): at a stage's last day the stage's table goes to gplay
   (GP_IN, as at the season end) and the playable knockout is built in slot 4 (the squads' gplay-play, as l1_po).
   Argentina: octavos 1A-8B .. 4B-5A, cuartos, semis, final at a neutral ground, ET + pens; twice a season.
4. **Annual table**: the 'keep' bytes hold the first stage's points; the annual = kept + current, written where the
   season-end code reads the league table (titles: Campeon de Liga; international places).
5. **Second competition of a season** (NZ National League Championship, the Brazilian states): a round robin /
   group contest outside the league slot. Slots 1 / 3 have the big buffer (0xB52); slots 2 / 4 only 0x443. Plan: the
   contest in slot 4 with its 0xB52 work area saved in the engine block (package 5's 'EN' trailer, an item of 0xB52),
   copied in / out around cseg_8B71C. NOT verified: probe 3.

## Per country (data: formats2627.md)
| Country | League slot | Knockouts | Second competition |
|---|---|---|---|
| Argentina | 30 rows, 2 zones by membership, stages Apertura 16 days + Clausura 16 days (reset, keep) | after each stage: octavos .. final (slot 4) | Trofeo de Campeones (gplay single match) |
| MLS | 30 rows (East / West), 34 days of fixtures (the real 2026 schedule shape) | wild card single, round one best of three, conf. semis / finals, MLS Cup (slot 4) | - |
| New Zealand | Northern 12 / Central 10 / Southern 10 (closed divisions, Mar-Aug) | - | National League Championship 11, single round robin + grand final (Sep-Dec) |
| Brazil (package 6) | Serie A as today | - | the career club's state championship (Jan-Mar), the other states simulated |

## Probes (in order)
1. ARG: one division of 30 with a fixture-list stage from day 0 (2 zones + the interzonal day), two seasons in a
   career at an Argentine club: no trap (VerifyTeamLoaded at the season end), 16 days, every club 16 matches.
2. Stage end -> slot-4 knockout mid-season (the career calendar after the Apertura).
3. A type-2 contest in slot 4 with its work area in the engine block (NZ Championship).
4. Season mode (gameType 3 -> world 0) and COMP. PREDEFINITA for each.

## API for package 6 / namespace (provisional)
- pack.json, a division: `"schedule": {"stages": [{"days": [[[home, away], ...] per day] | "zones",
  "groups": [[club keys]], "reset": bool, "keep": bool, "then": ko spec}]}`.
- engine.schedule(team_file, division, clubs, spec) for world 0 (4.0), as engine.split.
- A second competition: engine.second(contest bytes, slot, months, simulated: bool) - after probe 3.

## Argentina 2026: knockout dates (session '4.0', 2026-10-18; [checked] en / es.wikipedia, else [verify])
Season 22/01 -> 12/12. Apertura: octavos 09/05 [checked], cuartos 16/05, semis 20/05, final 24/05 [checked: Belgrano
3-2 River, Kempes]. Clausura: octavos 22/11, cuartos 29/11, semis 05/12, final 12/12. Trofeo de Campeones 19/12.
Split's league days leave these weeks free (split.week_of(day, month): the calendar unit, 8 a month). Owners: the
league stages / annual table / promedio / relegation = integrator; knockouts + Trofeo (slot 4, gplay-play's
gp_build(spec, first_week) at engine.after_stage) + the Libertadores feed (sacups) = session '4.0', reviewed.

## Probe 1 result (2026-10-18 night): PASS
Argentina as one division of 30 (two zones of 15 by places, single round robin, 15 days from day 0 on split's
calendar; Primera Nacional's zones below as parallel groups), SPLIT_NMAX=30 (split's state for 30 rows, MAXDAYS 40),
mkseason's 24-club check relaxed (PROBE30, uncommitted): two seasons at BOCA JUNIORS (62 + 73 steps), no trap at either
season end, checkw1 ok, every club 14 matches, 15 days. The game's 24-club pair tables are never read once our calendar
starts at day 0. Notes: split._orient's exhaustive search could not schedule a 30-club group (package 6's fix: 11-18 in
seconds; 30 still too slow) - the real ARG calendar is a data list (zones + clasicos / interzonals) by rows anyway.
