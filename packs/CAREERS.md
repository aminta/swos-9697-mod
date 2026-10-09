# Classic careers: build a whole historic world

A **season pack** ([README.md](README.md)) gives one historic season to play in Season mode. A **classic career**
goes further: a whole football **world** of an era (for example Europe 1984-85) played as a *career*, season after
season, with promotions and relegations, national cups and the European cups, all among the clubs of that world.
It shows up in the career team selector under **CLASSIC CAREERS** (Italian: CARR. STORICHE).

A world is a set of **career packs**, one per country. Each career pack has the same files as a season pack
(`pack.json`, `clubs.csv`, `players.csv`, `ties.csv`), plus a few extra fields in `pack.json`. Nothing here is code:
you prepare data, we compile it.

*Italiano: [CAREERS.it.md](CAREERS.it.md).*

## Quick start

1. Copy the folder [`_template_world`](_template_world). It is a small valid world with two countries:
   `alpha` (two divisions of 4 clubs, a cup of 8) and `beta` (one division of 4, a cup of 4).
2. Make one folder per country of your world (rename `alpha`, `beta`, add more) and replace their rows with your
   data. Everything about `clubs.csv`, `players.csv`, `ties.csv` and squads is the same as for season packs:
   see [README.md](README.md).
3. Fill the world fields of each `pack.json` (below).
4. Optional, if you have Python 3: check the whole world at once, all its folders on one line:

   ```bash
   python3 tools/mkseason.py check packs/my-world/alpha packs/my-world/beta
   ```

   It checks every country, then prints the world: first year, countries, the size of each European cup and the
   clubs that play them in the first season.
5. Send it to us: open an issue on this repository with the folder zipped (or post it in the SWOS groups where we
   are).

As for season packs, you do not need to care about `files` (file numbers and global numbers), contest `id`s,
`squads` and `dates_from`: we assign them when the world goes into the build.

## What changes in pack.json

```json
{
  "format": 1,
  "id": "europe-1984-85-ita",
  "kind": "career",
  "button": "ITALY",
  "continent": "europe",
  "world": 1,
  "europe_places": {"cc": 1, "cwc": 1, "uefa": 4},
  "first_europe": {"cc": ["juventus"], "cwc": ["roma"], "uefa": ["inter", "torino", "fiorentina", "verona"]},
  "world_cups": {"start_year": 1984},
  ...
}
```

| Field | Meaning |
|---|---|
| `kind` | `"career"` (a season pack has `"season"` or nothing) |
| `button` | the country's button in the world |
| `world` | the world's number: all the countries of one world have the same number |
| `europe_places` | places of this country in the European Cup (`cc`), Cup Winners' Cup (`cwc`) and UEFA Cup (`uefa`) |
| `first_europe` | optional: the clubs that play each European cup in the **first** season (club keys of this country). Default: the clubs in league order, top division first (Champions Cup first, then Cup Winners' Cup, then UEFA Cup) |
| `world_cups` | in **one** pack of the world only (the *root* country): `start_year` (the first season, e.g. `1984` for 1984-85) and optionally the `rounds` of each cup, e.g. `{"cc": {"rounds": ["two_legs", "two_legs", "two_legs", "two_legs", "single"]}}`. Default rounds: two legs, single-match final |

**Leagues with divisions.** A country can have several divisions with promotion and relegation: in the league
competition, `divisions` lists them from the top (`teams`, `promoted`, `relegated`, `names`), and `clubs.csv` gets a
`division` column (0 = top division, 1 = the next, …). The template's `alpha` country shows how.

## How the European cups work

- They are **knockout** cups (no groups). The number of clubs of each cup must be a **power of 2**: Champions Cup at
  most **16**, Cup Winners' Cup and UEFA Cup at most **32**, all three together at most **80**.
- **The holder has a place of its own**: cup size = all the countries' places + 1. Example: 15 countries with one
  Champions Cup place each + the holder = 16 clubs. In the first season the holder's place goes to the root country
  (its `first_europe` lists one club more per cup).
- **From the second season on, the clubs qualify from the season just played**: Champions Cup = the league champion;
  Cup Winners' Cup = the national cup winner; UEFA Cup = the next places of the league table. A holder always plays
  its own cup as holder: if it also wins its league (or its cup, or a UEFA place), that place goes to the next club.
- The names are the game's own (COPPA CAMPIONI EUROPEA, …) and carry no year, since a career lasts many seasons.

## What the player sees

- The season year starts from `start_year` (CAMP. 1984/85, then 1985/86, …).
- VIEW WORLD shows only this world: its countries and its three European cups.
- Buying a foreign player shows only the clubs of this world.
- No national-team job offers (the national teams of the game are the 1996-97 ones).
- The other clubs never trade players among themselves: they keep their squads every season (that is how SWOS 96/97
  works); only your club buys and sells.

## What a contributor sends us

For each country of the world, at the start season:

- the clubs of every division, in the order of the previous season's final table (that is the order shown);
- the squads (16+ players per club with role, ideally ordered by appearances) and the coaches;
- the national cup bracket of the first season, with the winners (`ties.csv`, as for season packs);
- the places in the three European cups, and the clubs that played them in the first season.

Ratings are optional (they are calibrated from the club's strength); real ratings from another database (e.g.
Championship Manager) can be used with its authors' permission and credit.

## Limits (today)

- Up to about 90 clubs per country (all its divisions together) and about 150 countries (team files 101–251).
- European cups: knockout only, sizes as above.
- One menu name for all worlds (CLASSIC CAREERS); a name per world will come.
- Long careers (5+ seasons) have not been played yet: tell us what you see.
