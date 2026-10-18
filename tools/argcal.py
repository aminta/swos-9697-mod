"""Argentina's Liga Profesional calendar (LPF 'Reglamento Torneos Primera Division 2026', art. 8.1): two zones of 15,
a single round robin in each zone; with 15 clubs one club of each zone is free every matchday and the two free clubs
are rivals ('clasico' or interzonal: the zone fixtures are drawn so that the rivals rest on the same day); plus one
extra matchday of interzonal matches between drawn opponents (not rivals) = 16 matchdays. The Clausura plays the same
pairs with home and away reversed.

    days = argcal.tournament(zone_a, zone_b, rival, seed=2026, interzonal_day=16)
    [[(home key, away key), ...] per day]           (pack.json split stage 'fixtures': lists of [home, away])
    argcal.reverse(days)                            (the Clausura)

zone_a / zone_b = club keys (15 each); rival = {key: rival key} for every club, each rival in the other zone.
"""
import random


def _circle(clubs):
    """Single round robin of an odd number of clubs (circle method with a free slot): [(pairs, free club)] per day,
    home and away alternating for every club as far as the method allows."""
    n = len(clubs)
    assert n % 2 == 1
    slots = list(clubs) + [None]
    m = n + 1
    days = []
    for r in range(n):
        pairs, free = [], None
        for i in range(m // 2):
            a, b = slots[i], slots[m - 1 - i]
            if a is None or b is None:
                free = b if a is None else a
                continue
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        days.append((pairs, free))
        slots = [slots[0]] + [slots[-1]] + slots[1:-1]
    return days


def tournament(zone_a, zone_b, rival, seed=2026, interzonal_day=16):
    assert len(zone_a) == len(zone_b) == 15 and set(rival[a] for a in zone_a) == set(zone_b)
    assert all(rival[rival[a]] == a for a in zone_a)
    rng = random.Random(seed)
    za = list(zone_a)
    rng.shuffle(za)                             # (the draw of the zone fixtures)
    days = []
    for d, (pairs, free) in enumerate(_circle(za)):
        b_pairs = [(rival[h], rival[a]) for h, a in pairs]          # zone B mirrors zone A through the rivals:
        clasico = (free, rival[free]) if d % 2 == 0 else (rival[free], free)   # the two free clubs are rivals
        days.append(pairs + b_pairs + [clasico])
    for _ in range(1000):                       # the interzonal day: drawn A v B, never rivals
        perm = list(zone_b)
        rng.shuffle(perm)
        if all(rival[a] != b for a, b in zip(zone_a, perm)):
            break
    inter = [(a, b) if k % 2 == 0 else (b, a) for k, (a, b) in enumerate(zip(zone_a, perm))]
    days.insert(interzonal_day - 1, inter)
    days = balance(days)
    check(days, zone_a, zone_b, rival)
    return days


def balance(days):
    """Home and away: each match at the club with fewer home matches so far, on a tie the one away last time (8
    home + 8 away each, runs of at most 2 in practice)."""
    home, last = {}, {}
    out = []
    for d in days:
        o = []
        for a, b in d:
            ka = (home.get(a, 0), last.get(a) == 'h')
            kb = (home.get(b, 0), last.get(b) == 'h')
            h, w = (a, b) if ka <= kb else (b, a)
            home[h] = home.get(h, 0) + 1
            last[h], last[w] = 'h', 'a'
            o.append((h, w))
        out.append(o)
    return out


def reverse(days):
    return [[(b, a) for a, b in d] for d in days]


def check(days, zone_a, zone_b, rival):
    clubs = set(zone_a) | set(zone_b)
    assert len(days) == 16
    seen = set()
    for d in days:
        assert len(d) == 15 and {c for pr in d for c in pr} == clubs, d
        for a, b in d:
            key = frozenset((a, b))
            assert key not in seen, (a, b)
            seen.add(key)
    for z in (zone_a, zone_b):                  # every pair of a zone once
        for i, a in enumerate(z):
            for b in z[i + 1:]:
                assert frozenset((a, b)) in seen, (a, b)
    for a in zone_a:                            # every club meets its rival once
        assert frozenset((a, rival[a])) in seen, a
