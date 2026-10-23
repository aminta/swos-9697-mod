# 4.0.1 South America: from declared approximations to exact (package 6, for Davide's choice after 4.0)

## 1. Peru: the national-title play-off
- **Real rule** (Liga1 2026 bases, as summarised by es.wikipedia "Liga1 2026"; press: futbolperuano.com,
  americatv.com.pe, caretas.pe):
  - The entrants are A = the Apertura winner, C = the Clausura winner, and T1 / T2 = the accumulated table's top 2.
  - A = C: A is national champion and there is no play-off.
  - {A, C} = {T1, T2}: a final A v C, no semi-finals.
  - Only one tournament winner X is among T1 / T2: X goes straight to the final. The other tournament winner meets
    the other top-2 club in a semi-final, and its winner plays X in the final.
  - All four distinct: semi-finals, then the final. The exact pairing is still to be read in the LFP bases.
    Candidate: A v T2, C v T1.
  - 2026 dates: semi-finals 28 Nov / 4 Dec, final 9 / 13 Dec; a direct final 28 Nov / 6 Dec. These are two-legged
    ties. The tie-break level is to be confirmed in the bases; candidate: penalties.
- **Engine need**: one new gplay entrant type, `title_seed` (variant 'per'). It is shaped like Malta's split_seed
  (type 6), from GP_SS r[0] p1, r[1] p1 and r[2] p1 / p2.
  - It produces seeds s1..s4 for a fixed bracket SF [[s1, s4], [s2, s3]], F [[W0, W1]], every tie skip_if_same:
    - A = C: s1 = s2 = s3 = s4 = A;
    - direct final: s1 = s4 = X, s2 = s3 = Y;
    - three clubs: s1 = s4 = X, then s2 / s3 are the semi-final pair;
    - four clubs: the bases' pairing.
  - The play-off is kind 'title' (built at the season end, gp_need).
  - Optional and separate: the Libertadores places play-off (3rd v 4th of the accumulated table, then the winner v
    the 2nd) only matters for the continental spec.
- **Hours**: C entrant type + spec 3; a forced-seed scenario (GPLAY_FORCE pokes per case) 1.5; data + FORMAT /
  notes 0.5. About **5 h**.

## 2. Colombia: the cuadrangulares by the real draw
- **Real rule** (Dimayor regulations since 2025-I, noticiascaracol.com May 2025; kept for 2026-II, publimetro.co
  19/08/2026):
  - The 1st and 2nd of the 19 rounds head groups A and B.
  - The other six (3rd-8th) are drawn at random, three per group, with no pots: 3rd and 4th can share a group.
  - The two heads play at home on the last group matchday.
  - Group fixtures are drawn by Dimayor, and clubs sharing a city / stadium are never at home on the same day.
  - Each group winner (most points) goes to the two-legged final.
- **Engine need**: a gplay group draw. A group round would take `"draw": {"heads": [0, 1], "pot": [2..7]}`: the
  heads are fixed, the pot is shuffled into the groups (the same RNG as the knockout `pairing: draw`), and it is
  stored in GP_ST so a reload keeps the groups.
  - Group schedule: the existing 'listed' host order, with the heads' last match at home.
  - Equal points in a group: the real tie-break after points (goal difference, goals...) is to be confirmed. Today
    gplay ranks a group by points, goal difference, goals, then the better place.
- **Hours**: group draw in gplay.c + spec 3; GP_ST field + reload check 1; scenario (two seeds, draw kept across a
  save) 1. About **5 h**.

## 3. The missing Transfermarkt matchdays: exact now (data only, no engine)
- **Finding**: every listed Clausura / Finalizacion matchday k is the Apertura's matchday k with home and away
  swapped. Peru 13/13, Colombia 17/17, Uruguay 12/12, every pair and every venue. These are the federations' mirrored
  calendars, so the missing days are the Apertura's days 14-17 (Peru), 18-19 (Colombia) and 13-15 (Uruguay) mirrored.
- **Done**: sa_exact.fixtures_full now completes from the mirror whenever every listed day matches it, and keeps the
  backtracking completion only as a fallback.
  - Peru's last date comes out at 22/11, the real end of the Clausura (L1 Radio via americatv.com.pe).
  - The missing dates for Colombia and Uruguay stay a week apart: still to be checked against the federations'
    published dates.
- **Hours**: 0 more for the fixtures. 0.5 for the dates if Dimayor / AUF list them. Rerun world_full_* after the
  release.
