# Mod conventions: read this before adding a feature or fixing a bug

These are the mod's settled design rules (Davide's decisions, 2026-10). Every session checks a change against them,
**reuses the shared code named here instead of writing a new variant**, and adds a line here when Davide settles a
new rule. If a rule seems wrong for a case, ask the regia session; don't silently deviate.

**Rule 0 - general, scalable solutions only (Davide, 2026-11-16, standing rule for ALL SWOS work).** Always choose the
general, scalable solution that lets the mod extend later at low cost, never a local stopgap that must be reworked
(e.g. a limit such as the team cache is fixed once at the root, as one mechanism for every world/career with a bound
check and old-save compatibility, and every feature reuses it). Every design gets a Fable check for scalability
before coding; the brief and the review say which general mechanism the change uses or adds. In every task check
with Fable and, where it helps, hand the work to Fable.

## Screens and text
1. **Font characters only, everything fits.** Titles and names use only the game font's glyphs and fit their bar:
   35-byte title field; calendar labels ≤ 70 px before the (C)/(F) marker, **both lines** of a two-line cup entry.
   The build asserts this (complist.check_titles / rnames). No stray characters, no cut words.
2. **4 languages, the game's own words.** Every new text exists in IT / EN / FR / DE, in each exe's own wording.
   DE umlauts: the fonts' bytes (8Eh / 99h / 9Ah = Ä / Ö / Ü) **only in big-font titles** (e.g. ÜBERSICHT); every
   small-font text writes AE / OE / UE (its dots barely show; Davide 26/10 + 08/11). complist.DE_UMLAUT, asserted.
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
14a. **An impossible draw is refused, never relaxed** (Davide, 2026-11-10, option B). When no draw satisfies every
    constraint of the stage (protected pairs, the same-association separation, ...), the engine relaxes nothing: the
    draw fails with an error (sr_group_draw_p -2 = none exists, -3 = undecided within the budget) and the caller
    reports it; no silent fallback to a weaker draw. The one exception is a competition whose real regulations say how
    to relax, and then exactly as they say (its spec carries that rule). The harness fails a build whose real data
    hits a refusal.
14b. **Group draws are proven before they ship** (42-acl2, MC 11/11). Every continental group stage with an association rule
    goes through the build's draw gate (tools/drawgate.py, run by conti.patch in every build): all the association
    mixes the stage can really receive (exhaustive up to 4096, else saturated + random) x 1024 seeds, through the same
    ctdraw.c code the game runs. A budget hit or a refusal on any of them FAILS THE BUILD; results are cached by content
    in internal/drawgate/. The harness adds CT_SDRAW_ERR == 0 and CT_SDRAW_HIT > 0 in every conti scenario. A drawable
    field is never refused. Only two competitions may relax, and only to what their regulations say (14a): the AFC
    Champions League Two groups and the AFC Champions League Elite preliminary stage ("unless unavoidable"): the draw
    then takes the fewest same-country pairs a legal field allows ('fewest', per region), nothing more. Everything else
    (Elite league stage, CAF, CONMEBOL, OFC, UEFA) refuses. CONMEBOL's rule for clubs coming from the qualifying round
    is a fixed class, not a relaxation. Sources and article numbers: internal/handoff/nota-draw-rules.md.
14c. **S7 crossings: Serie D groups by area, an approximation** (Davide via Regia, 2026-11-13). The LND recomposes the
    Serie D groups every year; the mod does not. A club relegated from Serie C goes into the Serie D group of its
    clubs.csv area (else the nearest group with room), taking the place of a club promoted from that group, so every
    group keeps its size; a promoted club takes the Serie C group by area the same way. Direct relegations first, then
    play-out losers. Not exact: declared in the release notes (EN + IT) and in "Rebuilt exactly" as approximated.
    Unequal counts or a bad snapshot = the season's crossings refused and logged (S7_LOG), never guessed.
14d. **A crossing of the career club is not a job change** (MC 13/11, option B): when the career club crosses between
    Serie C and Serie D, its squad (all of it, 17..30 included), its funds and the job count are kept, no reserves are
    invented and no squad is written back to a club record. Only the club's place changes: selTeamNumber,
    careerTeamLeague and careerTeam's own bytes (word, global number, league), as a team record in memory has them;
    the new season then takes its league from the club's new team file, as natively.

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
    The old-save trio = world_winners_oldsave + world_cuplist_mestre + world_s1conti_oldsave, run on a release-recipe build
    dir, always with career_20seasons C20_SEASONS=2; a change that adds or reads a save item also runs that item's own
    old-save case (MC 16/11).
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
    4.1 (41-selroom, for S2b): SEL_ROOM + 640 (0x280), B_STAGE 0x7B000 -> 0x7AE40 - the two gaps around the stage
    (1152 B below, 207 B above), nothing after it moves (B_UQ, obj2's size): **708 B left** (engine block 15368 B,
    26 items, 4.1 staging 8dfa5ea); S2b's 'US' (290 + 4, with the LP table) leaves **414 B** (engine block 15662 B, 27 items). That is the last room the gaps give (at most +679 B); more means moving B_UQ and the
    tail after it, or folding gplay's items into SWC1 (4.2) - the next item past this room waits for one of those.
    4.2 A1: the cache's memory stays 160 teams (careerworld.SEL_CAP: SEL_ROOM, the season-end park) and the save is
    budgeted at SEL_N = **159**: the assert above runs at 159 (+684 B). A save with 160 cached teams (peak seen 124)
    takes the trailer's own skip: the engine block no longer fits ROOMV, so it is NOT written, and the load zeroes
    every 'EN' item as from an older save (LR void for the season, ST 'not started' = redrawn, the same groups) -
    the career goes on, nothing crashes (world_en_drop forces that path). 4.2 room: 'ST' (144 + 4) leaves **542 B**
    (engine block 16218 B); the 4.2 ledger is in internal/handoff/mc-engine.md "ST save room".
21bis. **someLeaguesTable's reserved globals** (saved in the .CAR's fixed part, no 'EN' room; cseg_9487A traps unless
    the table sums to 0, so every byte used here has its balance byte). Globals 1730..1849 belong to no club
    (bigtables keeps them out of its remap); taken: 1786..1817 historic.BASE clubs, 1842 the save's release tag +
    1843 its balance (4.2, N3 option C: 0 = a 4.1 or older save, 1 = 4.2, 2 = 4.3 ...; written at every save,
    InitCareer clears it), 1844 pgroups.BALANCE, 1845 + 1846 careerworld's world byte + balance, 1847..1849 the 'S3'
    career mark (sacups). Free: 1818..1841 (1740..1842 were the 1.0/1.1 'S2' / 'SA' block: trailer.load_trailer reads
    and clears it, so take a new byte from the top down and read it only from a save that carries 'S3'). Add any new
    byte here before its sha.
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
      named address (uesum, the UEFA RIEPILOGO page, at swreg.UESUM_AT = 0x2000; 4.1 RC2: usmenu, its phase menu, the
      4th page at swreg.USMENU_AT = 0x3000; 4.2, xw-42: engine code below REG_AT 0x2800, registry 0x2800..OBJ4_END
      0x3000, uesum moved to UESUM_AT 0x4000 and usmenu after it - Regia 09/11). The engine's code
      + registry stay below swreg.OBJ4_END (0x2000 in 4.1), each view has its own range assert, and the 23bis gates
      below apply to it as to engine code.
    - 4.2 slow (PARKED 13/11: patch.SLOW = False, SLOW_AT..NAMEFIT_AT asserted zero; page 13 stays for the rest):
      obj4 page 13, SLOW_AT 0xC000 (slow.py, the OPTIONS row MATCH SPEED + its SPEED.CFG; MC 12/11,
      SREG2 0xB000 below it, T3 0xD000 (Mercato CPU), CT spare 0xE000; a 23bis exception, Davide's ok via Regia 12/11).
    - 4.2 shirtbox: obj4 0xCF00..0xD000 (in slow's page 13, top; swreg.BOX_AT / BOX_END, MC 12/11): shirtedit's
      se_unsh (the lit number box's afterDraw) + its 4 data bytes, because the career cave is full. Slow's code stays below TRIAL_AT.
    - 4.2.x trial players: obj4 0xC800..0xCF00 (page 13, between slow and the shirtbox; swreg.TRIAL_AT / TRIAL_END, MC
      12/11): trial.py's code + its 'TRFL' variables, out of obj3 (REL42i13 left IT obj3 112 B); obj1's three call sites
      are type-8 fixups into obj4, the buttons stay in cpurefill's obj3 menu copy with pointers into obj4.
    - 4.2 names-fit: obj4 0xC400..0xC800 (page 13, between slow and trial; swreg.NAMEFIT_AT / NAMEFIT_END, MC 12/11):
      namefit.py's code + 16 x 24 B row buffers (menu names cut by pixels); 3 obj1 call sites + the scorers' obj2 one = type-8 fixups into obj4;
      slow's link limit is NAMEFIT_AT.
    - 4.2.y T3: obj4 page 14, T3_AT 0xD000 (swreg.T3_AT..T3_END 0xE000; t3.py / t3.c, Mercato CPU; MC 12/11).
    - No obj4 address is ever stored in a save (engine state = 'EN' items, rule 21), so obj4 may grow and move freely.
    - Calls between the game / obj3 and obj4: self-relative fixups (type 8) as rule 23; cobj.link(text_obj=4).
    - The harness finds obj4 by its header (Result.base4: the magic + the self pointer), not by a game pointer.
    - Gates for any obj4 change: engine_obj4 (IT, and SWOSTEST_UI=en for SWOS++ 1.9.2.2), bench_world with
      BENCH_SPP=1 (a match under SWOS++), host tests test_swe + test_roundtrip; before a minor ships, a MiSTer
      z486 / ao486 boot of the obj4 exe.
24. **Shared hook sites**: a site that one module hooks and another may need later is listed here. A later hook chains
    to the earlier one (p.get() / lepatch.call_target, never obj_bytes), and the first one asserts it found the
    original bytes.
    - euro.py (4.1 RC3; 4.2 de945f4: its code on obj3's last page after longtable + mainbtn, MC 10/11): both `call conv` of the money conversion (Int2Pounds and
      cseg_24AB6) -> eu_money; ChainFont's first instruction (`shl [D0], 2`, 7 B) -> jmp eu_chain; obj2's currency
      strings block (pound, nullString, the short K / M forms) rewritten in place. A build with a euro world fails if the
      patch did not go in (EURO_OPTIONAL=1 only for scenario builds without gplay's tail).

25. **Inline asm in Mod C under `__i386__`** (MC 11/11, after 42-strmap's sm_dos broke the engine's rules-check): any
    `__asm__` in a Mod C file that the engine's host tests compile (rules-check includes gplay.c; the host suite's cc
    is arm64) goes under `#if defined(__i386__)` with a host stub that keeps the C path working (a DOS call: -1 = no
    file / not found, as 9f33156 / sm_dos). The release objects stay byte-identical (check the exes' md5s).

26. **Adding teams to the team cache: tc_room / tc_reserve / TC_CAP, never a constant** (MC 16/11, team cache 1a,
    tools/tcache.py). One rule for both caches (the game's 100 records, the big cache's careerworld.SEL_CAP): a
    MEMORY CAP that stops the game ("TEAM CACHE FULL (n) - PLEASE REPORT") instead of overwriting what follows the
    cache, and a SAVE BUDGET (trailer.py: nmax for the game's cache, TC_CAP for the big one) = the most records with
    which the whole trailer still fits the save. The game's 6 inserts are hooked (the memory cap); every OPTIONAL
    feature that adds clubs (friendlies, contest views, supercups, any future loader) first asks tc_reserve(list, n) /
    tc_room() and skips itself cleanly on "no" - never a hand-written count (ctgame.c's 160 is gone). A world whose
    late MANDATORY installs need room sets tcache.RESERVE[world]. A count written without an insert goes through
    tc_clamp. tcache's code is in obj3 (23 / 23bis: mod code, not the engine's obj4); a caller reaches it ONLY through a
    dword of its own bound by tcache.ref (careerworld's wl stub, ctgame.c's TC_ROOMP / TC_CLAMPP, the trailer's
    after_process slot through engine.CALL_AT) - never a literal address; tcache.check fails the build on an unbound
    one. 21's SEL_N is replaced by TC_CAP (computed per build from the blocks).
    **TC_FLOOR** (MC 16/11): TC_CAP may only ever GROW across versions, never shrink - a build asserts TC_CAP >=
    tcache.TC_FLOOR (159; TC_FLOOR_FP 155 with 'FP'), so a career saved at the floor by an earlier exe loads in every
    later one. A trailer item that breaks it fails the build: its owner finds room elsewhere (never lowers the floor).
27. **Mini-league stages on the fixture port: one pack row, no competition in the code** (Supercoppa Serie C, 17/11;
    notes/4.2-supercoppa-c.md). A small round robin among clubs taken from final tables is ONE row of the league
    competition's `mini_leagues` in pack.json (entrants `[division, place]`, `schedule`, `points`, `tiebreak`, `units` =
    offsets from the league's last unit); fpad.py compiles it into FP_MLT and fpml.c (obj4 FPML) runs it with the
    engine's sr_mini_sched / sr_rr_table. Nothing in C names a division, a file or a club. Rules that follow:
    (a) an entrant of a mini-league is NOT in its division's season-end play-offs: while its stage runs, the slot-4
    windows open to the season's end (fport's `[L, END]` dplay / play-off / play-out windows) are off for that club
    (fpad.c h_windows asks fpml.c fp_ml_busy) - never a per-competition exception; a row whose entrant place can reach
    a play-off is a data error. (b) The port is in a build when the data has a producer (a `mini_leagues` row) or
    FPORT=1 (test builds); a build without either holds no byte of it. (c) The career club's matches are port
    fixtures (level NONE: a level score stands), one at a time, the next one queued only after the result; every other
    match is scored by the producer; a stage with no instance at the season end (the career club not an entrant, an
    older save) is opened, simulated and closed there. (d) State = the FP item's ML block (v2: 'ML', version 1, 2 x 56 B
    at +36); a new mini-league = a new row (a third instance = +56 B: a new FP item version).
