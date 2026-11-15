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
TRAVEL = {'sardinia': (42.09, 11.80), 'sicily': (38.19, 15.57)}


def travel(lat, lon):
    """The coordinates a club travels from: its own, or its island's mainland port."""
    if 38.8 <= lat <= 41.4 and 8.0 <= lon <= 9.9:
        return TRAVEL['sardinia']
    if 36.5 <= lat <= 38.4 and 12.3 <= lon <= 15.7:
        return TRAVEL['sicily']
    return (lat, lon)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def centroid(points):
    pts = list(points)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def hungarian(cost):
    """Min-cost assignment of n rows to n columns (the Jonker-Volgenant form of the Hungarian algorithm), deterministic: returns col of each row."""
    n = len(cost)
    inf = float('inf')
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
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


EPS = 1e-6                               # (the stability tie-break: far below one metre of distance, above float noise)


def assign(clubs, anchors, size, last, fixed=None):
    """{ident: group}: `fixed` {ident: group} clubs are placed first (their slot taken), the rest by the min-cost assignment."""
    groups = sorted(anchors)
    fixed = dict(fixed or {})
    free = sorted(i for i in clubs if i not in fixed)            # (ident order: the deterministic tie-break)
    left = {g: size - sum(1 for x in fixed.values() if x == g) for g in groups}
    assert all(v >= 0 for v in left.values()) and sum(left.values()) == len(free), (left, len(free))
    slots = [g for g in groups for _ in range(left[g])]
    cost = [[km(clubs[i], anchors[g]) - (EPS if last.get(i) == g else 0.0) for g in slots] for i in free]
    col = hungarian(cost)
    out = dict(fixed)
    for i, c in zip(free, col):
        out[i] = slots[c]
    return out


def total(clubs, anchors, grp):
    return sum(km(clubs[i], anchors[g]) for i, g in grp.items())


def rule(clubs, anchors, size, last, second=None, prev_second=None, seed=0):
    second = sorted(second or [])
    prev_second = prev_second or {}
    groups = sorted(anchors)
    if not second:
        return assign(clubs, anchors, size, last)
    # second teams: every arrangement of distinct groups, none on last season's; the cheapest total (the rest assigned), a draw among ties
    best = []
    for arr in itertools.permutations(groups, len(second)):
        if any(prev_second.get(i) == g for i, g in zip(second, arr)):
            continue
        grp = assign(clubs, anchors, size, last, fixed=dict(zip(second, arr)))
        best.append((round(total(clubs, anchors, grp), 6), arr, grp))
    assert best, 'no arrangement of the second teams respects the alternation'
    best.sort(key=lambda b: (b[0], b[1]))
    cheapest = [b for b in best if b[0] == best[0][0]]
    return cheapest[seed % len(cheapest)][2]
