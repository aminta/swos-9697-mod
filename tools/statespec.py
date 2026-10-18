"""State championships of a career world (pack.json competitions of type 'state'): the spec compiler for statecup.py.

A state championship is a type-2 contest (the Champions Cup layout: groups, then knockout stages) played in career
slot 1 by the clubs of its state (statecup's picker). pack.json, in the country's pack (one per country: every club of
the country is a key of it, the state-only clubs in a shared-base file):

  {"key": "pr", "type": "state", "id": "C4", "names": {"*": ["CAMPEONATO PARANAENSE", "PARANAENSE"]},
   "win_points": 3, "months": [1, 4],
   "clubs": [club keys in group order: group A first],
   "stages": [{"type": "groups", "teams": 12, "groups": 2, "meetings": 1, "cross": 2},
              {"type": "knockout", "teams": 8, "matches": "two_legs", "from": ["4A", "1A", "3A", "2A", ...]},
              {"type": "knockout", "teams": 4, "matches": "two_legs"},
              {"type": "knockout", "teams": 2, "matches": "two_legs"}]}

- the stage syntax is the tourney packs' (packs/TOURNEYS.md): 'groups' (teams, groups), 'knockout' (teams, matches,
  'from' after a group stage: 1A = winner of group A; tie k = the k-th pair, the first listed at home in a single
  match, at home in the FIRST leg of two), the last stage the final; fixed brackets (tie k = winners of 2k-1, 2k);
- 'meetings' (a group stage): 1 or 2 matches per pair (one value for every group stage of a contest: the header's);
- 'cross': k on the first group stage = the clubs are k blocks of equal size in list order and play only the clubs of
  the OTHER blocks, once (a fixed calendar: lp36.FIXTURES); groups = cross: each block is a group (its own table:
  Paranaense, Catarinense), groups = 1: one table for all (Goiano, Paraense);
- 'months': first and last month of the contest (1 = January).
The contest's champion = its final's winner (the game's national-cup trophy line).
"""
import random

from mkseason import MATCHES, _need


def cross_calendar(n, blocks, seed=2026):
    """n clubs in `blocks` equal blocks (list order): every pair of different blocks once, in rounds where every club
    plays (n even); home sides balanced (each club home ceil / floor of half its matches). [(home, away)] by day."""
    size = n // blocks
    blk = [i // size for i in range(n)]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if blk[i] != blk[j]]
    per = n // 2
    rng = random.Random(seed + n * 31 + blocks)
    days_n = len(pairs) // per
    for attempt in range(2000):                 # perfect matchings, greedy with backtracking over shuffled edges
        left = set(pairs)
        days = []
        ok = True
        for d in range(days_n):
            m = _matching(rng, n, left)
            if m is None:
                ok = False
                break
            days.append(m)
            left -= set(m)
        if ok and not left:
            break
    else:
        raise ValueError(f'cross calendar {n} / {blocks}: no rounds found')
    out = [list(m) for day in days for m in day]
    for k, m in enumerate(out):                 # alternate, then flip until every club hosts half (+- 1/2)
        if k % 2:
            m.reverse()
    games = [sum(1 for m in out if v in m) for v in range(n)]
    for _ in range(10000):
        home = [sum(1 for m in out if m[0] == v) for v in range(n)]
        bad = [v for v in range(n) if abs(2 * home[v] - games[v]) > 1]
        if not bad:
            break
        v = bad[0]
        hi = 2 * home[v] > games[v]
        cand = [m for m in out if (m[0] if hi else m[1]) == v]
        rng.shuffle(cand)
        o = lambda m: m[1] if hi else m[0]
        m = min(cand, key=lambda m: (2 * home[o(m)] - games[o(m)]) * (1 if hi else -1))
        m.reverse()
    return [tuple(m) for m in out], days_n


def _matching(rng, n, edges):
    """A perfect matching of n vertices from `edges` (DFS on the lowest free vertex), or None."""
    adj = {v: [] for v in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    for v in adj:
        rng.shuffle(adj[v])
    used, out = set(), []

    def go():
        free = next((v for v in range(n) if v not in used), None)
        if free is None:
            return True
        used.add(free)
        for w in adj[free]:
            if w not in used:
                used.add(w)
                out.append((min(free, w), max(free, w)))
                if go():
                    return True
                out.pop()
                used.discard(w)
        used.discard(free)
        return False
    return out if go() else None


def compile_state(c, n_clubs):
    """pack.json 'state' comp -> {'stages': [(groups, per group, qualifiers)], 'stage_bytes', 'meetings', 'points',
    'months': (b3, b4), 'draws': [(perm, sort)], 'fixture': (groups, per group, days, calendar) or None}."""
    w = f"{c['key']}:"
    st = c.get('stages') or []
    _need(2 <= len(st) <= 5, f'{w} 2 to 5 stages (the last one the final)')
    _need(isinstance(c.get('win_points'), int) and 1 <= c['win_points'] <= 9, f'{w} win_points 1..9')
    m1, m2 = c.get('months', [1, 6])
    _need(1 <= m1 <= m2 <= 12, f'{w} months [first, last], 1..12')
    trip, sb, draws, meet, fixture, prev = [], [], [], None, None, None
    for i, x in enumerate(st):
        t, n = x.get('type'), x.get('teams')
        sw = f'{w} stage {i + 1}:'
        _need(t in ('groups', 'knockout'), f'{sw} type groups or knockout')
        _need(isinstance(n, int) and n >= 2, f'{sw} teams')
        if i == 0:
            _need(n == n_clubs, f'{sw} {n} teams, {n_clubs} clubs')
        elif prev['type'] == 'groups':
            _need(n < prev['teams'], f'{sw} fewer teams than the group stage before')
        else:
            _need(n * 2 == prev['teams'], f'{sw} {n} teams: half of the knockout before')
        if t == 'groups':
            g = x.get('groups')
            _need(isinstance(g, int) and g >= 1 and n % g == 0 and 2 <= n // g <= 24, f'{sw} groups: 2..24 per group')
            mt = x.get('meetings', 1)
            _need(meet in (None, mt) and mt in (1, 2, 3, 4), f'{sw} meetings 1..4, the same for every group stage')
            meet = mt
            cr = x.get('cross')
            if cr:
                _need(i == 0 and n % cr == 0 and n % 2 == 0 and g in (1, cr) and mt == 1,
                      f'{sw} cross k: the first stage, k equal blocks, groups 1 or k, one meeting, even teams')
                cal, days = cross_calendar(n, cr)
                fixture = (g, n // g, days, cal)
            nxt = st[i + 1]['teams'] if i + 1 < len(st) else 1
            trip.append((g, n // g, nxt))
            sb.append(0)
        else:
            _need(n & (n - 1) == 0, f'{sw} a knockout stage needs 2, 4, 8 or 16 teams')
            _need(x.get('matches') in MATCHES, f"{sw} matches: one of {', '.join(MATCHES)}")
            trip.append((0, n, n // 2))
            sb.append(MATCHES[x['matches']])
        frm = x.get('from')
        if frm is not None:
            _need(i > 0 and prev['type'] == 'groups', f'{sw} from: only on the stage after a group stage')
            g = prev['groups']
            _need(n % g == 0, f'{sw} from needs the same number of qualifiers from every group')
            labels = [f'{r}{chr(65 + k)}' for r in range(1, n // g + 1) for k in range(g)]
            _need(sorted(frm) == sorted(labels), f"{sw} from must list {' '.join(labels)} once each")
            draws.append((n, [labels.index(q) for q in frm], False))
        elif i == 0:
            draws.append((n, list(range(n)), False))     # the clubs into the groups in list order
        elif prev['type'] != 'groups' and n > 2:
            draws.append((n, list(range(n)), True))      # tie k = the winners of ties 2k-1, 2k (their contest order)
        prev = dict(x, teams=n)
    _need(st[-1]['type'] == 'knockout' and st[-1]['teams'] == 2, f'{w} the last stage must be the final (2)')
    ns = [d[0] for d in draws]
    _need(len(set(ns)) == len(ns), f'{w} two stages with {ns} teams: a fixed order needs different team counts')
    return {'stages': trip, 'stage_bytes': sb, 'meetings': meet or 1, 'points': c['win_points'],
            'months': (8 * (m1 - 1), 8 * (m2 - 1)), 'draws': [(pm, srt) for _, pm, srt in draws], 'fixture': fixture}
