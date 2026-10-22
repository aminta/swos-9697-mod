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
