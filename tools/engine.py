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

    engine.LEAGUE_AT['ita'] = obj1 offset of Italy's league struct (or (obj, offset): e.g. (2, off) in obj2)

State to keep with the career (any world): engine.save_item(name, size) + ITEM_AT[name] = (obj, offset) during
patch_exe; trailer.py writes the items as one chained block 'EN' after its main block.

World 0 runs in careers of the original world (world byte 0) and in Season mode (one division, one year: gameType 3;
split and gplay look up world 0 there). Moves of several divisions keep cseg_9487A's checks (pgroups.BALANCE).
"""
LEAGUE_AT = {}          # key -> obj1 offset, or (obj, offset), of a world-0 league struct (set by the 4.0 code
                        # during patch_exe; the game's own league structs are in obj2)
GPLAY = []              # (key, ko_playoffs, ndiv)
PGROUPS = []            # (levels, clubs)
SPLITS = []             # (team file, division, clubs, spec)
RESERVES = []           # (nd, low, [(global, base division)], [pool globals, first order])
SAVE_ITEMS = {}         # name -> (size, clear): state saved in the .CAR's engine block 'EN' (trailer.py)
ITEM_AT = {}            # name -> (obj, offset) of its bytes, set by the owning module during patch_exe
AFTER_LOAD = []         # names of routines called after a career load (after_load)
CALL_AT = {}            # name -> (obj, offset) of the routine


def clear():
    LEAGUE_AT.clear()
    del GPLAY[:], PGROUPS[:], SPLITS[:], RESERVES[:]
    ITEM_AT.clear()
    CALL_AT.clear()


def save_item(name, size, clear=True):
    """Save `size` bytes with the career, in the engine block 'EN' after the trailer's main block (any world, world 0
    too). The owner sets ITEM_AT[name] = (obj, offset) before trailer.patch runs, or later (then
    trailer.late() binds it, at the end of patch_exe). clear: a save without the item (an
    older save, or one from before the item existed) zeroes it at load; False = leave it as the load left it (e.g. a
    big world's bigtables bytes, also kept in its own area). The id in the save is a hash of the name: an item
    another build does not know is skipped."""
    assert 0 < size < 0x8000 and SAVE_ITEMS.get(name, (size, clear)) == (size, clear), (name, size)
    SAVE_ITEMS[name] = (size, clear)


def after_stage(name):
    """A routine called (pushad / popad, D0..A6 saved) right after the last league day of a split stage whose spec
    says then: name (not in the season-end simulation of a league): e.g. the 4.0 session's Argentine knockout build.
    The owner sets CALL_AT[name] = (obj, offset) before patch_exe ends (split.late binds it)."""
    import split
    if name not in split.CALLBACKS:
        split.CALLBACKS.append(name)


def after_load(name):
    """Call CALL_AT[name] (pushad / popad around it, no arguments) after a career load, once the engine block's items
    are read or cleared (an older save): to rebuild derived state, e.g. contest pointers. The owner sets CALL_AT[name]
    = (obj, offset) of its routine before trailer.patch runs."""
    if name not in AFTER_LOAD:
        AFTER_LOAD.append(name)


def after_loads():
    """[(name, (obj, offset) or None: set later, trailer.late)] in registration order (trailer.patch)."""
    return [(n, CALL_AT.get(n)) for n in AFTER_LOAD]


def item_id(name):
    import zlib
    return zlib.crc32(name.encode()) & 0xFFFF


def save_items():
    """[(name, id, size, clear, (obj, offset) or None: set later, trailer.late)] in name order (trailer.patch); ids
    unique."""
    out = [(n, item_id(n), sz, cl, ITEM_AT.get(n)) for n, (sz, cl) in sorted(SAVE_ITEMS.items())]
    assert len({i for _, i, _, _, _ in out}) == len(out), 'engine.save_item: two names with one id'
    return out


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
