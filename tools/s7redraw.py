"""S7 redraw oracle (Panchina 15/11, MC's design internal/handoff/s7-redraw.md section 2): Serie C (3 x 20) and Serie D (9 x 18) groups
redrawn from the clubs' coordinates and last season's groups. ONE deterministic rule for both levels, pure Python, integer-free of
hidden state: the same input gives the same groups (a host test runs it twice).

    rule(clubs, anchors, size, last, second=None, prev_second=None, seed=0) -> {ident: group}

clubs   {ident: (lat, lon)} the level's clubs next season (islands: pass travel(lat, lon), not the town)
anchors {group: (lat, lon)} the centroids of LAST season's groups (a group keeps its identity: A stays north-west, ...)
size    clubs per group (18 / 20): every group gets exactly `size`
last    {ident: group or None} the club's group last season at this level (None: it was not there): the stability tie-break
second  {ident} the second teams (U23 / Next Gen / Futuro); prev_second {ident: group} where each played last season
seed    the career's season seed (the draw of the second teams' text)

1. Anchors = last season's centroids. 2. Travel coordinates: island clubs use a mainland port point (TRAVEL). 3. Capacity-constrained
assignment: every club to a group, exactly `size` per group, minimising the total distance to the anchors (Hungarian algorithm on
group slots; ties: stability, then the club's ident). 4. Second teams: never two in one group; a second team goes to a group other
than last season's (the official alternation clause); the draw among the allowed arrangements uses the seed and is taken among the
arrangements of the least total distance. 5. Stability: a club whose group did not need to change keeps it (an epsilon prefers its
last group in every cost).
"""
import itertools
import math

# Island travel points (a mainland port the real groups pair the island with; evidence: s7redraw-sources.md / the validation report):
# Sardinia's Serie D clubs play in the Lazio group (Civitavecchia), Sicily's with Calabria (the Messina strait).
TRAVEL = {'sardinia': (4209, 1180), 'sicily': (3819, 1557)}       # (hundredths of a degree)


def pt(lat, lon):
    """A point in INTEGER hundredths of a degree (the whole rule is integer arithmetic: the C port gives the same groups bit for bit)."""
    return (int(round(lat * 100)), int(round(lon * 100)))


def travel(lat, lon):
    """The point a club travels from (integer hundredths): its own town, or its island's mainland port (a float or an int pair in, an int pair out)."""
    la, lo = (lat, lon) if isinstance(lat, int) else pt(lat, lon)
    if 3880 <= la <= 4140 and 800 <= lo <= 990:
        return TRAVEL['sardinia']
    if 3650 <= la <= 3840 and 1230 <= lo <= 1570:
        return TRAVEL['sicily']
    return (la, lo)


def idist(a, b):
    """The rule's distance between two integer points: isqrt((4 dlat)^2 + (3 dlon)^2), units of 1/400 degree (lon scaled by cos 41.4 ~ 3/4)."""
    return math.isqrt(16 * (a[0] - b[0]) ** 2 + 9 * (a[1] - b[1]) ** 2)


def km(a, b):
    """Great-circle km between two (lat, lon) in DEGREES (reports only: the rule itself uses idist on integer points)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def centroid(points):
    """The integer mean of integer points (floor division: the same in C for the non-negative coordinates of Italy)."""
    pts = list(points)
    return (sum(p[0] for p in pts) // len(pts), sum(p[1] for p in pts) // len(pts))


def hungarian(cost):
    """Min-cost assignment of n rows to n columns (the Jonker-Volgenant form of the Hungarian algorithm), deterministic: returns col of each row."""
    n = len(cost)
    inf = 1 << 60
    u, v = [0] * (n + 1), [0] * (n + 1)
    p, way = [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    res = [0] * n
    for j in range(1, n + 1):
        res[p[j] - 1] = j - 1
    return res


STAY = 540                               # (step 5, stability: a club's cost to its LAST group is this many units (1/400 degree ~ 0.28 km) lower: 540 = ~150 km, frozen by the sweep of the validation)


def assign(clubs, anchors, size, last, fixed=None):
    """{ident: group}: `fixed` {ident: group} clubs are placed first (their slot taken), the rest by the min-cost assignment."""
    groups = sorted(anchors)
    fixed = dict(fixed or {})
    free = sorted(i for i in clubs if i not in fixed)            # (ident order: the deterministic tie-break)
    cap = size if isinstance(size, dict) else {g: size for g in groups}              # (a group's size: one number for all, or per group)
    left = {g: cap[g] - sum(1 for x in fixed.values() if x == g) for g in groups}
    assert all(v >= 0 for v in left.values()) and sum(left.values()) == len(free), (left, len(free))
    slots = [g for g in groups for _ in range(left[g])]
    cost = [[idist(clubs[i], anchors[g]) - (STAY if last.get(i) == g else 0) for g in slots] for i in free]
    col = hungarian(cost)
    out = dict(fixed)
    for i, c in zip(free, col):
        out[i] = slots[c]
    return out


def total(clubs, anchors, grp):
    return sum(idist(clubs[i], anchors[g]) for i, g in grp.items())


def rule(clubs, anchors, size, last, second=None, prev_second=None, seed=0):
    second = sorted(second or [])
    prev_second = prev_second or {}
    groups = sorted(anchors)
    if not second:
        return assign(clubs, anchors, size, last)       # (Serie D's one second team has no written constraint: an ordinary club)
    # second teams: the official placement is a DRAW (the career's season seed) among the arrangements that respect the written
    # constraints - distinct groups, none on last season's (the alternation clause). The arrangements are listed in a fixed order
    # (lexicographic over the sorted groups), the seed picks one; the other clubs are then assigned around them.
    allowed = [arr for arr in itertools.permutations(groups, len(second))
               if not any(prev_second.get(i) == g for i, g in zip(second, arr))]
    assert allowed, 'no arrangement of the second teams respects the alternation'
    arr = allowed[seed % len(allowed)]
    return assign(clubs, anchors, size, last, fixed=dict(zip(second, arr)))


def compactness(clubs, grp):
    """(mean km, max km) from each club to its group's centroid (travel coordinates): how compact the groups are."""
    by = {}
    for i, g in grp.items():
        by.setdefault(g, []).append(clubs[i])
    ds = []
    for g, pts in by.items():
        c = centroid(pts)
        ds += [km((p[0] / 100, p[1] / 100), (c[0] / 100, c[1] / 100)) for p in pts]
    return sum(ds) / len(ds), max(ds)


# ---- validation against the real groups (MC's gate 1) -------------------------------------------------------------------------------
import csv
import difflib
import os
import re

ROOT = os.path.join(os.path.expanduser('~'), 'swos-mod')
DATA = os.path.join(ROOT, 'internal', 'world2526', 'world5tm-h3s7', 'ita')
TOWNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7pack_towns.csv')
LEVELS = {'C': ('league', 2, 20), 'D': ('league_b', 5, 18)}          # (clubs.csv file, first division, group size)


def norm(s):
    s = s.lower().replace('next gen', 'ng').replace('calcio', '').replace('football club', '')
    return re.sub(r'[^a-z0-9]', '', s)


KEYS = {}                                # ident -> clubs.csv key (filled by load_ours: the name similarity of match_last uses it)


def load_ours(level):
    """[(ident, name, group letter, (lat, lon), second)] of the level's real 2026-27 clubs. ident = the club's 0-based ROW in clubs.csv of the h3s7r data
    (= the registry's ident, which is what the exe knows); the rule orders clubs and second teams by it (the goldens are keyed by it)."""
    fl, d0, size = LEVELS[level]
    towns = {r['key']: (float(r['lat']), float(r['lon'])) for r in csv.DictReader(open(TOWNS, encoding='utf-8'))}
    out = []
    for i, r in enumerate(csv.DictReader(open(os.path.join(DATA, 'clubs.csv'), encoding='utf-8'))):
        KEYS[i] = r['key']
        if r['file'] == fl and r['division'].isdigit() and d0 <= int(r['division']) < d0 + (3 if level == 'C' else 9):
            out.append((i, r['name'], 'ABCDEFGHI'[int(r['division']) - d0], towns[r['key']], bool(r['second_of'])))
    return out


def match_last(ours, last_groups):
    """{key: (group, member)} the 2025-26 member each of our clubs is (name similarity and distance), None when it was not in that level."""
    members = [(g, m) for g, ms in last_groups.items() for m in ms if m[2] is not None]
    res = {}
    for key, name, _g, pos, _s in ours:
        best = None
        for g, m in members:
            d = km(pos, (m[2], m[3]))
            r = max(difflib.SequenceMatcher(None, norm(name), norm(m[0])).ratio(), difflib.SequenceMatcher(None, norm(KEYS.get(key, str(key))), norm(m[0])).ratio())
            if d <= 25 and r >= 0.55 and (best is None or (r, -d) > best[0]):
                best = ((r, -d), g, m)
        res[key] = (best[1], best[2]) if best else None
    return res


def validate(level, last_season='2025-2026', verbose=True, seed=0):
    import s7redraw_src as S
    _fl, _d0, size = LEVELS[level]
    ours = load_ours(level)
    last = S.groups(last_season, level)
    mt = match_last(ours, last)
    anchors = {g: centroid(travel(m[2], m[3]) for m in ms if m[2] is not None) for g, ms in last.items()}
    clubs = {k: travel(*p) for k, n, g, p, s in ours}
    lastg = {k: (mt[k][0] if mt[k] else None) for k in clubs}
    sec = {k for k, n, g, p, s in ours if s} if level == 'C' else set()      # (D's one second team: no written constraint)
    prev = {k: mt[k][0] for k in sec if mt[k]}
    real = {k: g for k, n, g, p, s in ours}
    got = rule(clubs, anchors, size, lastg, sec, prev, seed)
    same = sum(1 for k in clubs if got[k] == real[k])
    if verbose:
        names = {k: n for k, n, g, p, s in ours}
        print(f'Serie {level} {last_season} -> 2026-27: {same}/{len(clubs)} = {100 * same / len(clubs):.1f}% in the real group; matched to last season: '
              f'{sum(1 for k in clubs if mt[k])}/{len(clubs)}; last-season group sizes {{{", ".join(g + ":" + str(len(m)) for g, m in sorted(last.items()))}}}')
        gs = sorted(anchors)
        print('   real\\rule ' + ' '.join(f'{g:>3}' for g in gs))
        for rg in gs:
            print(f'   {rg:>9} ' + ' '.join(f'{sum(1 for k in clubs if real[k] == rg and got[k] == g):>3}' for g in gs))
        cr, cg = compactness(clubs, real), compactness(clubs, got)
        print(f'   compactness (mean / max km to the group centroid): real {cr[0]:.0f} / {cr[1]:.0f}   rule {cg[0]:.0f} / {cg[1]:.0f}')
        print('   moved vs reality:', sorted((names[k], real[k], got[k]) for k in clubs if got[k] != real[k])[:40])
        print('   second teams:', {names[k]: (prev.get(k), got[k], real[k]) for k in sec})
    return same, len(clubs), got, real


def validate_hist(level, s0='2024-2025', s1='2025-2026', verbose=True, seed=0):
    """The control: the same rule on the PREVIOUS real transition s0 -> s1 (clubs = s1's members with a map point; capacities = s1's real group sizes)."""
    import s7redraw_src as S
    g0, g1 = S.groups(s0, level), S.groups(s1, level)
    m0 = [(g, m) for g, ms in g0.items() for m in ms if m[2] is not None]
    clubs, real, lastg, sec, prev = {}, {}, {}, set(), {}
    for g, ms in g1.items():
        for m in ms:
            if m[2] is None:
                continue
            k = f'{g}:{m[0]}'
            clubs[k], real[k] = travel(m[2], m[3]), g
            best = None
            for g0_, m0_ in m0:
                d = km((m[2], m[3]), (m0_[2], m0_[3]))
                r = difflib.SequenceMatcher(None, norm(m[0]), norm(m0_[0])).ratio()
                if d <= 5 and r >= 0.7 and (best is None or r > best[0]):
                    best = (r, g0_)
            lastg[k] = best[1] if best else None
            if m[4] and level == 'C':
                sec.add(k)
                prev[k] = lastg[k]
    anchors = {g: centroid(travel(m[2], m[3]) for m in ms if m[2] is not None) for g, ms in g0.items()}
    sizes = {g: sum(1 for k in real if real[k] == g) for g in g1}
    got = rule(clubs, anchors, sizes, lastg, sec, {k: v for k, v in prev.items() if v}, seed)
    same = sum(1 for k in clubs if got[k] == real[k])
    if verbose:
        cr, cg = compactness(clubs, real), compactness(clubs, got)
        print(f'Serie {level} {s0} -> {s1} (control): {same}/{len(clubs)} = {100 * same / len(clubs):.1f}%; matched to {s0}: '
              f'{sum(1 for k in clubs if lastg[k])}, of which unchanged group {sum(1 for k in clubs if lastg[k] and lastg[k] == real[k])}; '
              f'compactness real {cr[0]:.0f} / {cr[1]:.0f}, rule {cg[0]:.0f} / {cg[1]:.0f}')
    return same, len(clubs)


def golden_cases():
    """The goldens of Shaved's host test (the C redraw must give these groups byte for byte): inputs are integers (hundredths of a degree).
    1 'real_D' / 'real_C': the real 2025-26 -> 2026-27 inputs (season 1 end, no crossings);  2 'C_seeds': the Serie C case with the season seeds 0..5
    (the second teams' draw);  3 'chain10_D' / 'chain10_C': ten seasons in a row from the real 2026-27 groups, each season's anchors = the centroids of the
    previous output, 6 (D) / 3 (C) clubs a season made 'arrivals' (no last group) by a fixed LCG: stability, arrivals and the capacities over a chain."""
    import s7redraw_src as S
    cases = []
    for lv in ('C', 'D'):
        _fl, _d0, size = LEVELS[lv]
        ours = load_ours(lv)
        last = S.groups('2025-2026', lv)
        mt = match_last(ours, last)
        anchors = {g: centroid(travel(m[2], m[3]) for m in ms if m[2] is not None) for g, ms in last.items()}
        clubs = {k: travel(*p) for k, n, g, p, s in ours}
        lastg = {k: (mt[k][0] if mt[k] else None) for k in clubs}
        sec = sorted(k for k, n, g, p, s in ours if s) if lv == 'C' else []
        prev = {k: mt[k][0] for k in sec if mt[k]}
        base = dict(level=lv, size=size, anchors=anchors, clubs=clubs, last=lastg, second=sec, prev_second=prev)
        cases.append(dict(base, name=f'real_{lv}', seed=0, out=rule(clubs, anchors, size, lastg, set(sec), prev, 0)))
        if lv == 'C':
            for sd in range(1, 6):
                cases.append(dict(base, name=f'C_seed{sd}', seed=sd, out=rule(clubs, anchors, size, lastg, set(sec), prev, sd)))
        # the 10-season chain
        grp = rule(clubs, anchors, size, lastg, set(sec), prev, 0)
        keys = sorted(clubs)
        x = 12345
        for season in range(1, 11):
            anc = {g: centroid(clubs[k] for k in keys if grp[k] == g) for g in sorted(anchors)}
            nlast = {k: grp[k] for k in keys}
            for _ in range(6 if lv == 'D' else 3):
                x = (x * 1103515245 + 12345) & 0x7FFFFFFF
                nlast[keys[x % len(keys)]] = None
            nprev = {k: grp[k] for k in sec}
            grp = rule(clubs, anc, size, nlast, set(sec), nprev, season)
            cases.append(dict(level=lv, name=f'chain10_{lv}_s{season}', size=size, anchors=anc, clubs=clubs, last=nlast, second=sec,
                              prev_second=nprev, seed=season, out=grp))
    return cases


def golden_json(c):
    """A case with INTEGER idents as arrays (JSON object keys are strings): clubs [[id, lat, lon]], last [[id, group|null]], prev_second / out [[id, group]],
    all sorted by ident; second = the sorted idents; anchors stay {group: [lat, lon]}."""
    return dict(name=c['name'], level=c['level'], size=c['size'], seed=c['seed'], anchors={g: list(v) for g, v in c['anchors'].items()},
                clubs=[[k, *c['clubs'][k]] for k in sorted(c['clubs'])], last=[[k, c['last'][k]] for k in sorted(c['last'])],
                second=sorted(c['second']), prev_second=[[k, c['prev_second'][k]] for k in sorted(c['prev_second'])],
                out=[[k, c['out'][k]] for k in sorted(c['out'])])


def golden_inputs(j):
    """The inverse of golden_json: (clubs, anchors, size, last, second set, prev_second, seed) with integer idents."""
    return ({k: (la, lo) for k, la, lo in j['clubs']}, {g: tuple(v) for g, v in j['anchors'].items()}, j['size'],
            {k: g for k, g in j['last']}, set(j['second']), {k: g for k, g in j['prev_second']}, j['seed'])


GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7redraw_golden.json')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if sys.argv[1:] == ['golden']:
        import json
        cs = [golden_json(c) for c in golden_cases()]    # (one case a line: later diffs stay readable)
        with open(GOLDEN, 'w') as f:
            f.write('[\n' + ',\n'.join(json.dumps(c, sort_keys=True, separators=(',', ':')) for c in cs) + '\n]\n')
        print('wrote', GOLDEN, len(cs), 'cases')
        raise SystemExit
    for lv in (sys.argv[1:] or ['C', 'D']):
        validate(lv)
        validate_hist(lv)
