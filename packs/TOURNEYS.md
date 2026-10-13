# Classic tourneys: add a historic tournament to PRESET COMPETITION

*Italiano: [TOURNEYS.it.md](TOURNEYS.it.md).*

A **tourney pack** (3.2) is a folder of plain data that adds one historic tournament to **PRESET COMPETITION >
CLASSIC TOURNEYS**, next to the World Cup 1982, the Mitropa Cup 1934 and the FA Cup 1871-72. No code: the
formula (groups, knockout rounds, third place match, replays) is described in `pack.json`. The first one is
[`world-cup-1934`](world-cup-1934): the 1934 World Cup with its real bracket.

A league season played as a tournament (a round robin) needs no tourney pack: a season pack with
`"classic_tourney": true` on its league is also listed there ([README.md](README.md)).

## Quick start

1. Copy [`_template_tourney`](_template_tourney) and rename it (e.g. `world-cup-1938`).
2. `clubs.csv`: one row per team, in the order of the draw (groups: the teams of group A first, then B ...;
   a knockout start: as in `ties.csv` round 1).
3. Squads: `players.csv` (names and roles, or every skill: the same formats as a season pack, see
   [README.md](README.md)), or whole teams taken from a SWOS team file (`records`, below).
4. `pack.json`: names in the four languages, the stages, `win_points`.
5. Knockout start with the real bracket: `ties.csv` with every tie and its winner (as for the cups of a season pack).
6. `python3 tools/mkseason.py check packs/<your folder>`, then send it to us (an issue with the folder zipped, or in
   the SWOS groups). We give it a team file number and a contest id and put it in the build.

## pack.json

A complete example is [`world-cup-1934/pack.json`](world-cup-1934/pack.json).

- `files`: one team file, `base` always 1786 (all the classic tourneys share 32 global numbers: at most 32 teams).
- `stages` (2 to 6, in order; the last one is the final, a knockout of 2):
  - `{"type": "groups", "teams": 24, "groups": 6}`: groups of `teams / groups`, everyone plays everyone once.
    Odd groups work (1982: groups of 3). The next stage takes the best of every group; if its teams are not a
    multiple of the groups, the game adds the best of the next places (as the 1986 World Cup's third-placed teams).
  - `{"type": "knockout", "teams": 8, "matches": "..."}`: 2, 4, 8, 16 or 32 teams, half of them go through.
  - `{"type": "third_place", "matches": "..."}`: the semi-final losers, just before the final.
  - `"from": ["1A", "2B", "1C", "2D", ...]` on the stage after a group stage: where each qualifier goes (1A = winner
    of group A); tie 1 = the first two, tie 2 the next two... (for groups: group A = the first ones). Without it the
    game draws.
- `matches`:

  | value | a match | a draw |
  |---|---|---|
  | `single` | one match | as the game's own cups |
  | `single_et` | one match | extra time, penalties |
  | `two_legs` | home and away | away goals, extra time, penalties |
  | `single_replay` | one match | replayed; a drawn replay is decided by a coin toss |
  | `two_legs_replay` | home and away | a play-off; a drawn play-off is decided by a coin toss |

  The game cannot play extra time before a replay. A tourney uses either replays (`*_replay`) or penalties, not both.
- `draw`: `fixed` (default): a knockout keeps its bracket, tie k of a round = the winners of ties 2k-1 and 2k before
  (the real bracket with `ties.csv`); `random`: the game draws every round.
- `win_points`: points for a win in the groups (2 before 1994, 3 after).
- `id`: a contest id we assign (hex; ED for 1934).

## Squads

- `explicit`, `calibrate`, `game`: as in a season pack ([README.md](README.md)).
- `records`: whole teams (players, skills, kit, tactic, coach) from a SWOS team file: a `TEAM.xxx` or a SWOS 2020
  `CUSTOMS.EDT`. `clubs.csv` column `record` = the team's name in that file; `name`, and `coach` when not empty,
  replace its own; `kit1` / `kit2` optional. Files of other authors are used only with their permission and credit,
  and stay out of the repository (`orig/swos2020/`).

## What the player sees

PRESET COMPETITION > CLASSIC TOURNEYS > the tourney's name: the team selection (all by the computer, or some by
players), then the rounds as in the game's own cups. Replays show "(REPLAY)" in the round's title; a coin toss shows
"... WINS THE TOSS" on the results.

## Limits (today)

- No byes (every knockout round halves the teams); at most 32 teams, 6 stages, groups of at most 24.
- Two stages with the same number of teams cannot both keep a fixed order (use `draw: random`).
- Only in PRESET COMPETITION (not in Season or Career).
