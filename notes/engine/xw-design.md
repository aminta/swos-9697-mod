# XW: contests across any worlds (design, 2026-11-06, MC; code after P)

Engine step 3b (engine-estimate-20261104): a friendly or DIY contest may mix clubs of two career worlds (Europe
1984-85 + World 2026-27), not only "one career world + the 1996-97 game" (W-modes mixing A). Design only: the code
follows P, because the visitor map is saved state.

## The collision (measured on c/HTP1, the registry in obj4)

- World 2026-27 (stem `tmw5`) owns file numbers 101..219 (91 files); Europe 1984-85 (stem `team`) owns 101..132
  (32 files). The 1996-97 game: 0..100 (80..85 = its national files). Free in every namespace: **220..253** (34).
- One namespace is in the game's tables at a time (careerworld w_ns_set: countriesTable, competitionsTable,
  teamsCountryNumbers rows of the current world). A contest's record keeps a team word = file | ordinal << 8, so a
  1984-85 club in file 105 and a 2026-27 club in file 105 cannot both be in one contest.

## The remap: per visitor *file*, not per team

- The contest's **host world** = the first career world picked (as mixing A's lock today). The other one is the
  **visitor** world. Each visitor file the contest uses gets a free number from 220..253, the first unused one.
  A DIY of 64 clubs touches at most 32 visitor files (Europe 1984-85 has 32), so 34 numbers are enough. The estimate's
  "per picked team" was wrong: one number serves every club of that file.
- For a remapped number r → (visitor world w, original file f):
  - LoadTeamFile builds `data\<stem of w>.<f>`: careerworld w_ns_stem already chooses a stem per number; XW gives
    it the table r → (stem, f). Careers never see 220..253, so a career's path stays bit-identical (the old-save rule).
  - countriesTable[r] = the visitor world's label for f (its country name in the exe language), so lists, the
    pre-match screen and results name the right country.
  - teamsCountryNumbers[r] = the visitor world's base for f (the global numbering of its clubs), unique against the
    host's: needs the check that no two worlds' bases collide in a contest (bigtables 2000+ globals in 2026-27).
  - XTRA name (careerworld XNAMEW) and the players' nationalities per visitor file: the visitor world's.
- The team word in each picked record is rewritten f → r when the club is picked (swe_sel_post), and back never:
  the contest only lives with r.

## Saved state: the DIY file, not the career

- XW contests are friendlies and DIY contests, never careers, so the map is **not** an SWC1 section (SWC1 is the
  .CAR's). It extends the DIY tail block 'WM' (W-modes M2): today `'W' 'M', len 1, world`. XW: **len 2 + 3·k**:
  host world, visitor world, then k triples (r, f, flags). k ≤ 34 → at most 105 B + 4.
- The loader keeps today's rules: the block counts only when the file size is exactly the game's part + the block
  and the tag matches; a 1-byte 'WM' (mixing A) is read as today. An older exe ignores the tail (the game's part is
  unchanged), so it loads an XW contest with the visitor clubs unresolved → **those builds must refuse it**: the
  older 4.1 loader already reads only len 1, so it reads world 0 and lists the 220..253 clubs as missing files.
  **Decision (Davide, 06/11): acceptable - an XW DIY needs ≥ the XW build; no guard for older builds.**
- A friendly saves nothing. Presets / seasons: none (they are one world's).

## Where the code goes

- obj4 (swe.c): the map, its allocation at pick time, the rewrite, the WM v2 save / load. **obj4 → 3 pages** if
  the code passes 0x1800 (today 0x1150 of 0x1800 before the registry).
- careerworld: w_ns_stem gets the r → (stem, f) lookup; w_ns_set fills countriesTable / teamsCountryNumbers rows
  220..253 from the map on each namespace change (the host world's swap must not clear them).
- No change in trailer.py, no SWC1 room.

## Tests

- Tier B (host): the allocation (first free, at most 34, a full map refused), the rewrite, WM v2 round trip
  (mixing A files read unchanged, a short / long tail read as world 0), w_ns_stem's names for 220..253.
- DOSBox, 4 languages: a 1984-85 club vs a 2026-27 club in a friendly (pre-match names, the match, the result);
  a DIY cup with clubs of both worlds saved, reloaded, played to the end; a career afterwards is bit-identical
  (old-save scenarios + C20=2).

## Estimate

22–30 h as in the estimate (unchanged): allocation + rewrite 6, careerworld stems / rows 6, WM v2 4, Tier B 3,
DOSBox 4 languages 5–8, notes 1–2. Inputs: P merged (for the engine line, not for room), W-modes M2.
