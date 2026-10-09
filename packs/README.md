# Season packs

A **season pack** is a folder of plain data files (no code) describing one historic season: its clubs, squads,
league and cups. `tools/mkseason.py` compiles the packs into the mod (team files + exe tables). The compiler is
**deterministic**: the same pack always gives the same bytes. The first pack is `ddr-1988-89` (the DDR 1988-89 of
release 2.6, CLASSIC SEASONS menu).

Check a pack (validation and summary, nothing is written):

```bash
python3 tools/mkseason.py check packs/ddr-1988-89
```

The packs that go into the build are listed in `mkseason.ENABLED`.

*Italiano: [README.it.md](README.it.md).*

## Build your own season

Anyone can prepare a season and send it to us; we check it, finish the technical part and add it to a release.

1. Copy the folder [`_template`](_template) and rename it (e.g. `italy-1984-85`). It is a small valid example
   (4 league clubs, an 8-club cup): replace its rows with your data.
2. Fill `clubs.csv`, `players.csv` and `ties.csv` (Excel or any spreadsheet: save as "CSV UTF-8"), then in
   `pack.json` the button text, the competitions (names, rules, rounds) and the sources.
3. Optional, if you have Python 3: `python3 tools/mkseason.py check packs/<your folder>` tells you what is wrong.
4. Send it: open an issue on this repository with the folder zipped (or post it in the SWOS groups where we are).

You do not need to care about `files` (file numbers and global numbers), contest `id`s, `squads` and `dates_from`:
we assign them when the pack goes into the build. A spreadsheet with the same columns is fine too, and so is a
database export (e.g. Championship Manager): tell us where it comes from.

## Files

| File | Content |
|---|---|
| `pack.json` | season button text, team files, squad building, competitions and rules, which club plays which European cup |
| `clubs.csv` | one row per club |
| `players.csv` | one row per player, in squad order |
| `ties.csv` | one row per tie of every cup (the bracket) |
| `raw/` | optional: the source data as downloaded (provenance only, not read by the compiler) |

CSV files are UTF-8, comma-separated, with a header row (Excel: "CSV UTF-8").

### clubs.csv

| Column | Meaning |
|---|---|
| `key` | short unique id used by the other files (e.g. `dresden`) |
| `name` | club name as shown in the game: upper case, at most 16 characters |
| `coach` | coach's name (empty = none shown) |
| `country` | country code (`GDR`, `FRG`, `ITA`, `ESP`…: see `mkseason.COUNTRY`) |
| `file` | the team file the club goes into: a key of `files` in `pack.json` |
| `template`, `target`, `kit` | squad building, see below |
| `source` | the club's name in the source (provenance) |

The club order in each file matters: for the league file it is the order shown in the game (the final table of the
season, for instance).

### players.csv

`club` (a club key), `name`, `role` (`G` goalkeeper, `D` defender, `M` midfielder, `A` attacker). List the players in
order of importance (for instance minutes played), with 2 goalkeepers. A club gets 16 players: the compiler fills
each of the 16 squad slots with the next player of the slot's role (or of a near role when that role is used up).
`?` as a name = no known player: a filler is invented.

### ties.csv

`competition` (a cup key of `pack.json`), `round` (1, 2, …), `home`, `away`, `winner` (club keys).

- Round 1: every tie in bracket order; a club with a **bye** (straight into round 2, like a cup holder) is a row
  with an empty `away` and itself as `winner`, after the other round-1 rows.
- Later rounds: the real ties, home club first. Every club must be a winner of the round before.
- The final has no winner (it is played in the game).

The compiler turns this into the fixed draw of every round: if the same clubs win as in reality, the game plays the
real bracket.

### pack.json

```json
{
  "format": 1,
  "id": "ddr-1988-89",
  "button": "DDR 1988-89",
  "continent": "europe",
  "sources": ["..."],
  "files": {"league": {"file": 92, "base": 1786}, "cuponly": {"file": 93, "base": 1800}, "cc": {"file": 94, "base": 1850}},
  "shared_base_files": ["cc"],
  "squads": [ ... ],
  "competitions": [ ... ],
  "season": {"league": "oberliga", "cup": "pokal", "europe": {"bfc": "cc"}, "europe_placeholder": "cc"}
}
```

- `button`: the text of the country button in CLASSIC SEASONS (same in every language).
- `files`: the team files of the pack (`file` = file number, TEAM.0nn) and the first **global number** of each
  (the game's id of a club, 0–1999: base + position in the file). The league must be alone in its file (the game
  counts a country's clubs from these bases), so clubs that only play the cup get a file of their own.
  `shared_base_files`: files that may reuse the same numbers (only one of them runs in a season, e.g. the foreign
  clubs of each European cup).
- `squads`: how records are built, one entry per group of files:
  - `calibrate`: each club on the record `template` (position) of a `source` team file (positions, kit, skills);
    `kit` = another record of that file for the colours; skills moved towards `target` (average player value);
    players found by name in the source keep its ratings (for the files in `reuse_ratings`).
  - `game`: each club on its own record of the 1996-97 game when it has one, else a club of its country; players
    already in the game keep their ratings.
  - `explicit`: every byte comes from the pack (no source file, nothing estimated). `clubs.csv` adds `tactic`
    (0–15), `kit1` and `kit2` (5 numbers each: kit type, shirt, stripes, shorts, socks colours) and `lineup` (16
    numbers 0–15: which player takes each line-up place). `players.csv` lists exactly 16 players per club in record
    order and adds `position` (`G RB LB D RW LW M A`, matching the role), `number`, `nat` (the game's nationality
    number), `skin` (`light`, `dark`, `ginger`), the 7 skills `pa ve he ta co sp fi` (passing, shooting, heading,
    tackling, ball control, speed, finishing: 0–7, a trailing `*` marks a key skill) and `price` (0–49).
  - `seed`: random seed of the fillers (part of the determinism).

### Ratings: three ways, none required

1. **No ratings**: names and roles only; skills are estimated from the club's strength (`calibrate`, `game`).
2. **SWOS skills by hand**: the `explicit` columns above.
3. **From another database** (Championship Manager, SWOS 2020, anything with player ratings): a small converter
   turns it into the `explicit` columns. The compiler never depends on where the data comes from; a converter is
   just an option, used with the permission and credit of the database's authors.
- `competitions`: in order.
  - league: `id` (contest id, hex), `clubs` (its file key), `dates_from` (country whose calendar it copies),
    `games` (2 = home and away), `win_points`, `relegated`, `classic_tourney` (also in CLASSIC TOURNEYS), `names`.
  - cup: `id`, `layout` (`national` or `european` contest layout), `dates_from` (national), `rounds` (one per round:
    `two_legs`, `single`, `single_et` = single match with extra time and penalties), `names`.
  - `names`: per language (`it`, `en`, `fr`, `de`, or `*` for all): `[long name, short name]`, upper case, short
    name at most 16 characters.
- `season`: what a club plays in Season mode: the `league`, the national `cup`, and in `europe` which league club
  plays which European cup (`europe_placeholder`: any of those cups, replaced at run time).

## What a contributor sends us

The minimum for a new season: the league table (clubs in final order), the squads (16+ players per club with role,
ideally ordered by appearances), the coaches, and the cup brackets with the winners. Ratings are optional (they are
calibrated from the club's strength); real ratings from another database can be used with its author's permission
and credit.

## Limits

- One national league per pack, single division.
- Team files: 98, 99 and 101–251 are free (tested with 101–102); packs may share global numbers, since two
  packs never run in the same season.
