# SWOS 96/97 Mod — guide for Claude sessions

Read this first; then the tail of `notes/STATUS.md` (latest work) and, before any test, `notes/harness.md`.

## Who and how
- Davide (maintainer) writes in Italian: **reply in Italian**. Public texts (README, notes, manual) are EN + IT.
- **Never push, merge to main or publish a release without Davide's explicit ok.** Commit messages end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (or the attribution line the session gives).
- Do not ask Davide to test by hand what the harness can test; offer a playtest only for what it cannot see.
- Credits: the 1984-85 database author is credited **only as "DaniSwos"**, never by real name. Players who send
  feedback (e.g. Marco) are credited by first name only.
- Names of countries, worlds and menus always per exe language (the game's own spelling), never English-only.

## State (2026-10-15)
- Released: **v3.2.7**. 3.0 Europe 1984-85 career world, 3.1 its national teams + faster harness,
  3.2 tourney packs + World Cup 1934 + menu alignment, 3.2.1 ESCI arrow links, 3.2.2 patcher "Download all",
  3.2.3 KITS button aligned with the names in the English exe, 3.2.4 kits carry-over fix + world UEFA places,
  3.2.5 shirt numbers 17..99, 3.2.6 the same with SWOS++,
  3.2.7 season-end crash for careers spanning 128+ weeks (Indian clubs, Brazilian clubs in the mod SA cups).
- Release notes: `release/notes-<version>.md`; the patcher page `release/swos-9697-mod-patcher.html`.

## Layout
- `tools/patch.py it|en|fr|de` builds an exe + team files into `c/SWOS` from the originals in `orig/` (git-ignored,
  shared with the main checkout through symlinks in worktrees: `c`, `orig`, `ref`, `internal`).
- Main modules: `mkseason.py` (season / career / tourney / national packs from `packs/`), `careerworld.py` (historic
  career worlds), `historic.py` (CLASSIC TOURNEYS, fixed draws, ESCI fix, own obj1 page), `kitcolors.py`, `sacups.py`,
  `lepatch.py` / `le.py` (LE executable), `nasmcave.py` (nasm stubs), `mkpatcher.py` (the HTML patcher).
- Data packs: `packs/` with guides `packs/README.md` (seasons), `CAREERS.md` (career worlds), `TOURNEYS.md`
  (tournaments); each with an `.it.md` version.
- Docs: `docs/src/manual.{en,it}.html` (technical manual) -> `python3 tools/mkdocs.py` -> `docs/`.
- Private material (never in the repo): `~/swos-mod/internal/` — `world8485/` (DaniSwos DB converters),
  `12bit-packages.md` (how to build the 12bit eXoDOS / MiSTer packages and update Davide's MiSTer),
  `announcements/`, `swostest/` (harness builds, runs, cached saves).

## Testing: always with the automated harness
`tools/swostest.py` plays the real game in DOSBox-X (turbo, in-exe key feeder, memory reads). Guide:
`notes/harness.md`; work log: `notes/testing.md`.

```
python3 tools/swostest.py list
python3 tools/swostest.py run -j4                      # the whole suite (~12 min), all must PASS
SWOSTEST_BUILD=~/swos-mod/c/RELxx/SWOS W8485_BUILD=~/swos-mod/c/RELxx/SWOS python3 tools/swostest.py run -j4
```
- Every change that touches the exe or the data is checked with the suite before a release; a new feature gets its
  own scenario (see "Adding a scenario" in `notes/harness.md`). UI changes: read the menu geometry / send real keys
  through a `Session` (as `play_preset`, `press`).
- Test shortcuts: smallest league (Malta) unless a specific one is needed; force rare events by pokes of the game's
  own switches; cache slow saves (`nat_offer_save`).
- Never run `config -wcd` inside DOSBox-X (it overwrote Davide's DOSBox-X preferences once).
- Parallel sessions: give every suite its own SWOSTEST_RUNS dir (two harnesses in one run dir break each other).
- If the harness cannot add its page (`add_object_page` assertion), the LE header padding ran out: keep new stubs'
  absolute references few (one base register), or move code to a page of its own.

## Release checklist
1. Build all languages, CD and GOG, into a release dir (`c/RELxx/SWOS`, `c/RELxx/gog`; see `notes/STATUS.md`).
2. Full harness suite on that build: all PASS.
3. `VERSION` in `tools/mkpatcher.py`; save the previous published patcher as `orig/old-patchers/patcher-v<prev>.html`;
   `PATCHER_BUILD=c/RELxx python3 tools/mkpatcher.py`; test the page's own code in Node (originals CD/GOG, previous
   releases and SWOS++ upgrade; outputs = the release build).
4. Notes (`release/notes-x.md`), README EN/IT, manual + `mkdocs.py`, `notes/STATUS.md`.
5. With Davide's ok: merge to main, push, `gh release create vX release/swos-9697-mod-patcher.html --notes-file ...`.
6. If asked: Davide's MiSTer and the 12bit packages (procedure in `~/swos-mod/internal/12bit-packages.md`).
