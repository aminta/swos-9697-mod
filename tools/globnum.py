"""Global team numbers of a pack's clubs: glob(pk, file, ordinal), the one place every tool takes them from (S7-G, MC
11/11, notes/engine/save-ledger.md "File 144's global numbers").

Every team file f: global = base(f) + ordinal, its base = teamsCountryNumbers[f] (pk.files[key] = (f, base)) - as the
game's SetTeamGlobalNumbers does. One exception: a league over two team files (S7, Italy 2026-27: 'league' = file
102 = Serie A + B + C, 'league_b' = file 144 = Serie D 9 x 18) whose second file has no single free run of its rows
in its world's numbering (LIMIT 2409: the world uses them all but 7 + what file A gives up). Its rows then take TWO
runs (split()):
  run 1 = the free numbers right after file A's run (the numbers file A's Serie D rows held in 4.1: 102 at 92, 256
          rows -> 100 rows, so 192..347), at most its rows;
  run 2 = the rest from the lowest free numbers left after the guest files (guests.alloc), which are allocated with
          run 1 already taken - so the guests keep their 4.1 numbers.
No free numbers enough: refused (raise, with the reason), never a fallback. The exe side: worldpool.wp_glob's chain
(SetTeamGlobalNumbers' store, SPLIT_* symbols): file B's ordinals from run 1's length go to run 2.
"""
import os
import functools

SPLIT_KEY, PARTNER_KEY = 'league_b', 'league'     # (s7pack.py's pack.json 'files' roles)
RESERVED = range(1730, 1850)        # career marks, world byte, the saved SA block (trailer.py; mkworld_tm, guests.py)


class GlobError(Exception):
    pass


def split_file(pk):
    """(file B, file A) of a pack whose league is over two team files, else None."""
    fs = getattr(pk, 'files', {}) or {}
    if SPLIT_KEY in fs and PARTNER_KEY in fs:
        return fs[SPLIT_KEY][0], fs[PARTNER_KEY][0]
    return None


def _world_packs(w):
    import mkseason
    return [pk for pk in mkseason.packs() + mkseason.nationals() if pk.world == w]


def file_runs(w, packs=None):
    """[(lo, hi, file)] of world w's team files with one base (every file but a split one)."""
    out = []
    for pk in packs if packs is not None else _world_packs(w):
        sp = split_file(pk)
        for key, (f, b) in pk.files.items():
            if sp and f == sp[0]:
                continue
            n = pk.count.get(key, 0)
            if n:
                out.append((b, b + n, f))
    return out


def _free_after(used, start, limit):
    g = start
    while g < limit and g not in used:
        g += 1
    return g - start


def _split_pk(w, packs):
    sp = [(pk, split_file(pk)) for pk in packs if split_file(pk)]
    if len(sp) > 1:
        raise GlobError(f'world {w}: {len(sp)} leagues over two files (one supported)')
    return sp[0] if sp else (None, None)


def run1(w, packs=None, limit=None):
    """(file B, lo, n) of world w's split file's first run, or None: the free numbers right after file A's run."""
    import bigtables
    packs = packs if packs is not None else _world_packs(w)
    limit = limit or bigtables.LIMIT_CLUBS
    pk, sp = _split_pk(w, packs)
    if not pk:
        return None
    fb, fa = sp
    rows = pk.count[SPLIT_KEY]
    used = set(RESERVED)
    for lo, hi, _ in file_runs(w, packs):
        used.update(range(lo, hi))
    a = [(lo, hi) for lo, hi, f in file_runs(w, [pk]) if f == fa]
    if len(a) != 1:
        raise GlobError(f'world {w}: file {fa} (the league\'s first file) has {len(a)} runs')
    lo = a[0][1]
    n = min(rows, _free_after(used, lo, limit))
    if n == 0:
        raise GlobError(f'world {w}: no free global number right after file {fa}\'s run (..{lo - 1}) for file {fb}')
    return fb, lo, n


def split(w, packs=None, guest_runs=None, limit=None):
    """{file B: [(lo, n), (lo, n)]} of world w's split file (at most two runs), {} without one. guest_runs:
    [(lo, hi)] of the guest files (default guests.alloc's of this world)."""
    import bigtables
    packs = packs if packs is not None else _world_packs(w)
    limit = limit or bigtables.LIMIT_CLUBS
    r1 = run1(w, packs, limit)
    if not r1:
        return {}
    fb, lo, n = r1
    pk, _ = _split_pk(w, packs)
    rows = pk.count[SPLIT_KEY]
    runs = [(lo, n)]
    if n < rows:
        if guest_runs is None:
            import guests
            gw = guests.world()
            guest_runs = ([(b, b + guests.counts()[f]) for f, b in guests.alloc().items()] if gw == w else [])
        used = set(RESERVED) | set(range(lo, lo + n))
        for a, b, _ in file_runs(w, packs):
            used.update(range(a, b))
        for a, b in guest_runs:
            used.update(range(a, b))
        k = rows - n
        g = next((g for g in range(limit - k + 1) if _free_after(used, g, g + k) == k), None)
        if g is None:
            free = sum(1 for x in range(limit) if x not in used)
            raise GlobError(f'world {w}: file {fb} needs {rows} global numbers: {n} after file A, no free run of the '
                            f'other {k} below {limit} ({free} free in all)')
        runs.append((g, k))
    return {fb: runs}


@functools.lru_cache(maxsize=None)
def _split_cached(w):
    return split(w)


_OWN = {}


def _split_of(pk):
    """split() of pk's world with pk as its split league: the world's packs (mkseason.packs / nationals) when pk is
    one of them, else those with pk in place of the pack of the same id (a pack built outside the enabled list:
    s7pack's output, its host tests) - cached per pack folder."""
    import os
    here = os.path.realpath(pk.path)
    ws = _world_packs(pk.world)
    if any(os.path.realpath(q.path) == here for q in ws):
        return _split_cached(pk.world)
    key = (pk.world, here)
    if key not in _OWN:
        pid = pk.meta.get('id')
        _OWN[key] = split(pk.world, [q for q in ws if q.meta.get('id') != pid] + [pk])
    return _OWN[key]


def glob(pk, f, i):
    """The global number of ordinal i of pack pk's team file f."""
    sp = split_file(pk)
    if sp and f == sp[0] and pk.world is not None:
        for lo, n in _split_of(pk)[f]:
            if i < n:
                return lo + i
            i -= n
        raise GlobError(f'file {f}: ordinal past its {pk.count[SPLIT_KEY]} rows')
    return next(b for ff, b in pk.files.values() if ff == f) + i


def base(pk, f):
    """teamsCountryNumbers[f]: the global of ordinal 0."""
    return glob(pk, f, 0)


def runs_of(pk, f):
    """[(lo, n)] of file f's global numbers (one run, or a split file's two)."""
    sp = split_file(pk)
    if sp and f == sp[0] and pk.world is not None:
        return list(_split_of(pk)[f])
    key = next(k for k, (ff, _) in pk.files.items() if ff == f)
    return [(pk.files[key][1], pk.count.get(key, 0))]


def split_alone(w, f):
    """(4.2 rc, MC 16/11) A build with no country namespaces (careerworld defines no WCUR: one world) may drop the
    split hooks' world test only if no other pack - another world's, a season pack's - has a team file numbered f:
    asserted here, with the packs that share it."""
    import mkseason
    other = sorted({os.path.basename(pk.path) for pk in mkseason.packs() if pk.world != w
                    and any(v[0] == f for v in pk.files.values())})
    assert not other, (f'globnum: split file {f} of world {w} in a build without namespaces (no careerworld WCUR), '
                       f'but {other} use file {f} too: the split hooks cannot tell them apart')


def exe_split():
    """(world, file B, run 1's length, run 2's first number) for worldpool.wp_glob, or None (no league over two files,
    or file B fits run 1). Its tcn row is run 1's first number (mkseason._patch_pack: base())."""
    import mkseason
    for w in sorted({pk.world for pk in mkseason.packs() if pk.world is not None}):
        for f, runs in split(w).items():
            if len(runs) == 2:
                return w, f, runs[0][1], runs[1][0]
    return None
