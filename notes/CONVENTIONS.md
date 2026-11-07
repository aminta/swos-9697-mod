# Mod conventions: read this before adding a feature or fixing a bug

These are the mod's settled design rules (Davide's decisions, 2026-10). Every session checks a change against them,
**reuses the shared code named here instead of writing a new variant**, and adds a line here when Davide settles a
new rule. If a rule seems wrong for a case, ask the regia session; don't silently deviate.

## Screens and text
1. **Font characters only, everything fits.** Titles and names use only the game font's glyphs and fit their bar:
   35-byte title field; calendar labels ≤ 70 px before the (C)/(F) marker, **both lines** of a two-line cup entry.
   The build asserts this (complist.check_titles / rnames). No stray characters, no cut words.
2. **4 languages, the game's own words.** Every new text exists in IT / EN / FR / DE, in each exe's own wording.
3. **Club names = the national press** (Italy: Gazzetta dello Sport, ...), never legal names.
4. **FORMAT pages are discursive prose** (the approved Libertadores style), full-width wrap, a blank line between
   paragraphs, PAG. SUCC. / PAG. PREC.

## Tables
5. **One legend, always in the same place: the row ABOVE the table header, top left** (CL / [CONF] / EL, PROM /
   P.OFF / P.OUT / RETR, PASSA / P.OFF ...), as in the league tables. Never at the bottom, never over a button,
   never over a group title. The legend is built by the shared zones code (zones.py) for leagues, splits and conti
   cup groups alike.
   Legend boxes are plain colour boxes with no inner frame (Davide 2026-10-22, CONF included). The career club's
   row is its own clean colour, never framed; only when its colour equals the zone colour (player-coach light blue
   on a light-blue zone) it gets a 1-px black border flush with the box edge.
6. **Legend == zones painted.** An entry appears in the legend only if at least one row is painted in that colour,
   and every painted zone has its legend entry. Zones are computed **per group** in split / zoned / cup-group
   tables (group place, not overall place).
7. **Every competition's real places are painted**: titles, promotion, play-offs (P.OFF), play-outs, relegation,
   European / continental places (the colour is the competition the place leads to: CL / EL / CONF ...). A place that
   only leads to a PLAY-OFF for a European place (e.g. Austria's / the Netherlands' European play-offs) is green P.OFF,
   not the cup's colour (Davide 2026-10-22).
8. **Group tables**: header rows (ZONA A, GRUPPO TITOLO ...) + one blank spacer row between groups; the title bar
   shows the league's own name; scroll reaches the last row (one fire on the arrow = one row).

## Competition rules
9. **Real formats exactly**; approximate only when the engine can't, ask Davide, and declare it in the notes.
10. **Knockout tie-breaks are one shared engine setting per round**, chosen from: two legs (aggregate / away goals
    as the real rules), single match + extra time + penalties, single match + extra time + **better-placed club
    advances**, replays (only where the real competition replays). Never invent a mode per competition; never leave
    replay dates in a competition that has no replays.
11. **A career club plays only the competitions its real club would** (e.g. a Serie D club: its group + Coppa Italia
    Serie D; the national Coppa Italia keeps being simulated for its winner but is hidden from that club's calendar
    and VISUAL. COMPETIZ.).
12. **Every rule is documented** in the release notes (EN + IT) and, for 4.x worlds, in "Rebuilt exactly" or
    "Mod rules".

## Data and engine
13. **Off-file / pooled clubs** (Eccellenza pool, second pools, state-only, continental guests) must never trap any
    career path: transfers both ways, job offers, takeovers, cups. Any new code that loads a club's file goes through
    the shared loader (ripool / team cache), never a private copy.
14. **Shared data files change only with or after their engine change.**

## Tests
15. Result-dependent cases are **forced** (pokes / *_FORCE / CONTI_GPLACE ...), never re-run hoping. Test switches
    never in release builds. Minimal line-up by default. Each language's checks run on that language's own exe.
16. Every new feature gets a harness scenario; every bug found by a player gets a regression scenario.
17. Release checks: full suite all PASS on the release candidate; the 20-season career; the patcher's outputs
    byte-equal to the build.
17a. **Release builds differ from test builds** (Davide 2026-10-22, after the foreign-market crash that only release builds
    had): a release build carries the world data / pools / packs (e.g. POOL05's file-190 pool clubs), a default harness
    build does not. So every gameplay path that reads data files (transfers incl. the FOREIGN market, cups, careers,
    season ends, saves) must be exercised on the RELEASE recipe (buildrel.sh exes + release DATA), not only on
    scenario-built test exes; a scenario that builds its own exe gets a release-exe variant (SWOSTEST_BUILD = c/RELxx).
    A new data file / pool / pseudo file number needs a test that loads it through every engine path that can.

## Known engine pitfalls
18. (Under investigation, not a rule yet) The game's type-2 group contest hung with New Zealand's single 11-club group;
    odd groups of 3 (Serie D poule) work, so the cause is not just the odd size. Check here before using a large single group.
19. Post-load hooks in the career save-load chain are safe since 284da66 (2026-10-22). Cause of the old season-3 trap
    (0x17064): trailer.patch()'s after_process rewrite removed the text the LOAD_TAIL substitution looked for, so big-world
    loads silently skipped w_load_tail. Rule: every text rewrite of asm source asserts its pattern count (trailer._sub;
    the shared nasmcave.sub for the other patchers in the upcoming 4.0.1). Any load / save-path change still runs
    career_20seasons (C20_SEASONS>=2) + old-save loads before its sha.
20. obj2's page count is frozen (213 pages in the release build since 4.0): an added obj2 page moves obj2's zero-filled
    tail (careerworld.BSS: the big team cache, the W1 lists, teamsTable...) and 4.0 / 4.0.1 saves played on trap in
    the next season (FindTeamInCache's fatal int 3 at obj1+0x17064: 4.0.2 b2..rc1, CONTROLS' two obj2 pages). obj1 may
    grow (every release did; obj2's base moves with it and the loads handle that). Rule: new code AND data go in obj1
    pages of their own (obj1 is writable), as controls.py does; a new obj2 page needs Davide's ok and old-save play-on
    (world_cuplist_mestre + world_winners_oldsave on a release-recipe dir) before its sha.
21. The career save's engine block ('EN' after the trailer, trailer.py) shares careerworld.SEL_ROOM with the 160-team
    cache: SEL_N x 684 + main block + engine block <= SEL_ROOM (trailer.py asserts it). Room left, release recipe:
    93 B on 406-i10j, 68 B with FFP's FF (21 + 4) (engine block 15343 B, 25 items, main block 948 B; measured by the engine's P0, item by item in
    notes/engine/save-ledger.md). A new item costs 4 + its size; past the room the build fails - plan any 4.0.6+ item
    against this figure, add its line to the ledger and update it here.
22. obj1 has a ceiling too: 237 pages in the release build (4.0.5, Panchina's SWOS++ probe: obj1 in memory <= 238 pages
    starts every match under SWOS++ 1.9.2.2, 239+ makes PLAY MATCH stall - obj2's base moves past what SWOS++ tolerates;
    the harness adds 1 obj1 page of its own, so 237 file pages = 238 under test = the real limit). patch.py prints
    'exe: object pages: obj1 N ..., obj2 M' and warns over 237; buildrel.sh fails a release build with obj1 > 237 or
    obj2 != 213. Room was made in 4.0.5 by capping the historic pages (patch.py h2, 1 used of the 4 it had become).
    A 4.0.5+ item needing obj1 pages must find room in the existing pages first; the structural cure is rule 23 (4.0.6:
    obj1 235 pages once benchx moved to obj3).
23. **New mod code and data go in obj3** (4.0.6, internal/design/obj3-406.md), the LE object after obj2
    (lepatch.add_object, flags 0x2047). Never add obj1 pages (rule 22) or obj2 pages (rule 20).
    - Layout: obj3's file pages (mod pages, benchx first, then the C engine's code, PLAN §19 step O) stay below
      patch.OBJ3_ARENA = 0x20000 (buildrel.sh fails over 32 pages). The engine's arena + spec buffer go at 0x20000 as
      zero-filled vsize; the engine zeroes it itself (DOS/4GW zeroes no tail).
    - No obj3 address is ever stored in a save, so obj3 may grow and move freely.
    - Cross-object control transfer: self-relative fixups (type 8, lepatch.add_rel / branch), as the game's own 42
      obj1 <-> obj2 calls. Code is assembled with nasmcave.assemble_obj(src, org, sym, 3); its rel32s into the game
      come back as `rel` and get add_rel.
    - A chaining hook reads a call site's previous target with lepatch.call_target(obj, off), never by decoding the
      rel32 (behind a type-8 fixup it is 0 until load); put() asserts over an existing type-8 rel32.
    - DOS/4GW loads obj3 apart from obj1 + obj2 (below obj1 in DOSBox-X): the harness reads it at Result.base3 (an obj1
      pointer into obj3), obj3 offsets as swostest.Off3, any (obj, off) through Result.lin().
23bis. **obj4 is the competition engine's, and only the engine's** (engine step O, 04/11, Regia GO after the SWOS++ /
    DOS/4GW probe). No 4.0.x minor ever adds code, data or pages to obj4; their code stays in obj3 (rule 23).
    - Layout (tools/swe.py): obj4+0 the header ('SWOS-ENG', version, a self pointer, -> swe_init, -> the arena, the
      .bss size, -> SWE_STATE); obj4+0x40 the engine's code + data (swe.OBJ4_PAGES file pages); the arena = the C
      .bss, zero-filled vsize. patch.py adds obj4 right after obj3's pages; swe.patch() links it and puts its base
      above obj3's end. buildrel.sh fails a build with a 5th object.
    - **DOS/4GW zeroes no tail: the engine zeroes its own arena** (swe_init, before any other engine call). Never rely
      on a zero obj4 byte that the engine did not write.
    - 4.1 exception (Davide 08/11 via Regia, MC as obj4 owner): obj4 page 3+ may hold engine-adjacent views at a
      named address (uesum, the UEFA RIEPILOGO page, at swreg.UESUM_AT = 0x2000; 4.2 moves it to 0x3000 with the
      registry). The engine's code + registry stay below swreg.OBJ4_END (0x2000), each view has its own range
      assert, and the 23bis gates below apply to it as to engine code.
    - No obj4 address is ever stored in a save (engine state = 'EN' items, rule 21), so obj4 may grow and move freely.
    - Calls between the game / obj3 and obj4: self-relative fixups (type 8) as rule 23; cobj.link(text_obj=4).
    - The harness finds obj4 by its header (Result.base4: the magic + the self pointer), not by a game pointer.
    - Gates for any obj4 change: engine_obj4 (IT, and SWOSTEST_UI=en for SWOS++ 1.9.2.2), bench_world with
      BENCH_SPP=1 (a match under SWOS++), host tests test_swe + test_roundtrip; before a minor ships, a MiSTer
      z486 / ao486 boot of the obj4 exe.
