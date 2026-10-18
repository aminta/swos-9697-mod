"""The season-end engine for world byte 0 (the original 1996-97 world: 4.0) - knockout play-offs / play-outs (gplay),
parallel groups (pgroups) and mid-season splits (split) declared by the build's own code instead of career packs.

The career worlds' tables come from their packs (mkseason.gplay_tables / parallel_tables / splits). World 0 has no
pack: the 4.0 code registers its tables here BEFORE patch.patch_exe (patch_exe sizes its pages from them), e.g. in
patch_teams or at import:

    import engine
    engine.gplay('ita', ko_playoffs, ndiv=7)            # pack.json ko_playoffs shape (gplay.py docstring)
    engine.pgroups(levels, clubs)                       # [(first division, [group sizes])] over the whole chain,
                                                        # [(global, base division, [area per level of groups])]
    engine.split(team_file, division, clubs, spec)      # mkseason.splits()' spec shape (split.py)

and, once it has built the league struct (its obj1 offset known), before gplay.patch runs:

    engine.LEAGUE_AT['ita'] = obj1 offset of Italy's league struct

World 0 runs in careers of the original world (world byte 0) and in Season mode (one division, one year: gameType 3;
split and gplay look up world 0 there). Moves of several divisions keep cseg_9487A's checks (pgroups.BALANCE).
"""
LEAGUE_AT = {}          # key -> obj1 offset of a world-0 league struct (set by the 4.0 code during patch_exe)
GPLAY = []              # (key, ko_playoffs, ndiv)
PGROUPS = []            # (levels, clubs)
SPLITS = []             # (team file, division, clubs, spec)
RESERVES = []           # (nd, low, [(global, base division)], [pool globals, first order])


def clear():
    LEAGUE_AT.clear()
    del GPLAY[:], PGROUPS[:], SPLITS[:], RESERVES[:]


def gplay(key, ko_playoffs, ndiv):
    import gplay as g
    g.compile_spec(ko_playoffs, ndiv)           # validates now (ValueError)
    GPLAY.append((key, ko_playoffs, ndiv))


def pgroups(levels, clubs):
    PGROUPS.append((levels, clubs))


def split(team_file, division, clubs, spec):
    SPLITS.append((team_file, division, clubs, spec))


def reserve(nd, low, clubs, pool):
    """A reserve below the lowest level (gplay.c rs_season): nd = the division out of the league (the number of
    divisions), low = the lowest level's first division, clubs = every league club (global, base division; the pool's
    with base nd), pool = the reserve's globals in the order they come back (the first season's promoted first)."""
    RESERVES.append((nd, low, clubs, pool))


def reserve_tables():
    return [(0, nd, low, clubs, pool) for nd, low, clubs, pool in RESERVES]


def gplay_tables():
    """gplay.patch rows: (world 0, ('w0', key), spec bytes); the league struct comes from LEAGUE_AT[key]."""
    import gplay as g
    return [(0, ('w0', key), g.compile_spec(pos, ndiv)) for key, pos, ndiv in GPLAY]


def parallel_tables():
    return [(0, levels, clubs) for levels, clubs in PGROUPS]


def split_tables():
    return [(0, f, d, n, spec) for f, d, n, spec in SPLITS]
