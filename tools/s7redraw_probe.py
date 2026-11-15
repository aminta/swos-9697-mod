"""The 2 h probe (MC / Davide 15/11): how much of the real Serie D groups' change from one summer to the next is explainable?
`python3 tools/s7redraw_probe.py` prints, for the transitions 2023-24 -> 2024-25 -> 2025-26 -> 2026-27 (the last: our h3s7 clubs):
1. the errors of the frozen rule split: continuing clubs (in last season's Serie D) vs new arrivals (from Eccellenza / from Serie C);
2. for the arrivals: the share that went to the group their NEIGHBOURS were in (the 3 nearest last-season clubs' majority: the 'province habit');
3. the block moves: continuing clubs that changed group, as (from -> to) flows with the clubs, per transition."""
import collections
import difflib
import sys

import s7redraw as R
import s7redraw_src as S

SEASONS = ['2023-2024', '2024-2025', '2025-2026']


def members(season, level='D'):
    """[(group, name, (lat, lon))] of a season's level (clubs with a point)."""
    return [(g, m[0], (m[2], m[3])) for g, ms in S.groups(season, level).items() for m in ms if m[2] is not None]


def find(name, pos, pool, rmin=0.7, dmax=5.0):
    """The pool entry (group, name, pos) the club is (name similarity and distance), or None."""
    best = None
    for g, n, p in pool:
        r = difflib.SequenceMatcher(None, R.norm(name), R.norm(n)).ratio()
        d = R.km(pos, p)
        if d <= dmax and r >= rmin and (best is None or r > best[0]):
            best = (r, (g, n, p))
    return best[1] if best else None


def habit(pos, last, k=3):
    """The group most of the k nearest last-season clubs were in (the 'province habit')."""
    near = sorted(last, key=lambda m: R.km(pos, m[2]))[:k]
    return collections.Counter(m[0] for m in near).most_common(1)[0][0]


def transition(s0, s1=None, ours=None, bonus=None):
    """One transition s0 -> s1 (s1 None: 2026-27 = our h3s7 clubs). Returns a dict of the numbers and the lists."""
    last = members(s0)
    try:
        lastC = members(s0, 'C')                     # (arrivals from Serie C: clubs that were in C that season)
    except FileNotFoundError:
        lastC = []                                   # (2023-24's Serie C page is not among the downloads: its arrivals count as 'new')
    if ours is None:
        if s1 is None:
            cur = [(g, n, p, False) for k, n, g, p, s in R.load_ours('D')]
        else:
            cur = [(g, n, p, False) for g, n, p in members(s1)]
    clubs, real, name, lastg, kind, deg = {}, {}, {}, {}, {}, {}
    ml = R.match_last(R.load_ours('D'), S.groups(s0, 'D')) if s1 is None else None     # (2026-27: the oracle's own matching, as validate())
    okeys = [k for k, n, g, p, s in R.load_ours('D')] if s1 is None else None
    for i, (g, n, p, _s) in enumerate(cur):
        k = f'{i}:{n}'
        clubs[k], real[k], name[k], deg[k] = R.travel(*p), g, n, p
        f = (ml[okeys[i]][0],) if ml is not None and ml[okeys[i]] else (find(n, p, last, dmax=5) if ml is None else None)    # (p: degrees)
        lastg[k] = f[0] if f else None
        kind[k] = 'cont' if f else ('fromC' if find(n, p, lastC, dmax=25 if s1 is None else 5) else 'new')
    anchors = {g: R.centroid(R.travel(*q) for g2, n2, q in last if g2 == g) for g in sorted({m[0] for m in last})}
    sizes = {g: sum(1 for k in real if real[k] == g) for g in anchors}
    if bonus is not None:
        R.STAY = bonus
    got = R.rule(clubs, anchors, sizes, lastg)
    out = {'n': len(clubs), 'wrong': sum(1 for k in clubs if got[k] != real[k]), 'kind': collections.Counter(kind.values()), 'detail': {}}
    for kd in ('cont', 'fromC', 'new'):
        ks = [k for k in clubs if kind[k] == kd]
        h = sum(1 for k in ks if habit(deg[k], [(g, n, q) for g, n, q in last]) == real[k]) if kd != 'cont' else None
        out['detail'][kd] = (len(ks), sum(1 for k in ks if got[k] != real[k]), h, sum(1 for k in ks if lastg[k] == real[k]))
    flows = collections.defaultdict(list)
    for k in clubs:
        if lastg[k] and lastg[k] != real[k]:
            flows[(lastg[k], real[k])].append(name[k])
    out['flows'] = dict(flows)
    return out


def main():
    rows = [('2023-24 -> 2024-25', SEASONS[0], SEASONS[1]), ('2024-25 -> 2025-26', SEASONS[1], SEASONS[2]), ('2025-26 -> 2026-27', SEASONS[2], None)]
    for label, s0, s1 in rows:
        t = transition(s0, s1)
        print(f'== Serie D {label}: {t["n"]} clubs, frozen rule wrong on {t["wrong"]} = {100 * (t["n"] - t["wrong"]) / t["n"]:.1f}% right; arrivals/continuing: {dict(t["kind"])}')
        for kd, (n, w, h, st) in t['detail'].items():
            lab = {'cont': 'continuing', 'fromC': 'arrivals from Serie C', 'new': 'arrivals (Eccellenza / other)'}[kd]
            extra = f'; stay-put right {st}/{n}' if kd == 'cont' else f'; neighbours\' group (habit) right {h}/{n}'
            print(f'   {lab:32s} rule wrong {w}/{n}{extra}')
        print('   group changes of continuing clubs (from->to: clubs):')
        for (a, b), cl in sorted(t['flows'].items(), key=lambda x: -len(x[1])):
            print(f'     {a}->{b} {len(cl):>2}: {", ".join(sorted(cl))}')


if __name__ == '__main__':
    main()
