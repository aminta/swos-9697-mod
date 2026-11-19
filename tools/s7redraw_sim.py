"""S7 redraw long-career probe (MC / Panchina 15/11): the FROZEN rule run for 20 seasons on the h3s7r clubs, with seeded season-end crossings, against
the baseline 'no continuing club ever moves' (continuing clubs keep their group, the newcomers fill the places left by the Hungarian algorithm).
`python3 tools/s7redraw_sim.py [seasons] [local|random]` prints per season (summed over 3 seeds): continuing clubs moved (C / D) by the rule, mean / max km to
the group centroid for the rule and for the baseline.

The crossings (same numbers each season; the membership evolves identically for rule and baseline: the leavers are picked by random index over the sorted idents):
  Serie C (60, 3 x 20): 4 up to B, 4 down from B (a pool of 40 clubs above), 6 down to D, 6 up from D.   Serie D (162, 9 x 18): 6 up to C, 6 down from C,
  9 down to Eccellenza (a pool of 36 below), 9 up from it. The 3 Serie C second teams and Serie D's Milan Futuro never cross (the second teams rotate by the rule).
mode 'local': an arrival replaces a leaver in its own area (one of the 3 pool clubs nearest to the leaver: the real promotions are regional);
mode 'random': the arrivals are random clubs of the pool (a stress test: arrivals far from the places they fill)."""
import csv
import os
import random
import sys

import s7redraw as R

SEEDS = (1, 2, 3)


def universe():
    """{ident: (name, point, second, file, division)} of all 298 clubs (travel points), pools: 'up' = Serie A / B (file 102 divisions 0..1), 'down' = the 36 pool clubs."""
    towns = {r['key']: (float(r['lat']), float(r['lon'])) for r in csv.DictReader(open(R.TOWNS, encoding='utf-8'))}
    out = {}
    for i, r in enumerate(csv.DictReader(open(os.path.join(R.DATA, 'clubs.csv'), encoding='utf-8'))):
        out[i] = dict(name=r['name'], pt=R.travel(*towns[r['key']]), second=bool(r['second_of']), file=r['file'],
                      div=int(r['division']) if r['division'].isdigit() else None)
    return out


def start():
    u = universe()
    lv = {'C': {i: 'ABC'[c['div'] - 2] for i, c in u.items() if c['file'] == 'league' and c['div'] in (2, 3, 4)},
          'D': {i: 'ABCDEFGHI'[c['div'] - 5] for i, c in u.items() if c['file'] == 'league_b'}}
    up = sorted(i for i, c in u.items() if c['file'] == 'league' and c['div'] in (0, 1))
    down = sorted(i for i, c in u.items() if c['file'] == 'pool')
    return u, lv, up, down


def pick(rng, ids, k):
    ids = sorted(ids)
    return [ids.pop(rng.randrange(len(ids))) for _ in range(k)]


def nearest_replace(rng, u, leavers, pool):
    """For each leaver, one of the 3 pool clubs nearest to it (without replacement)."""
    out, pool = [], sorted(pool)
    for l in leavers:
        pool.sort(key=lambda i: (R.idist(u[l]['pt'], u[i]['pt']), i))
        out.append(pool.pop(rng.randrange(min(3, len(pool)))))
    return out


def crossings(rng, u, members, up, down, mode):
    """One season's crossings. members {'C': set, 'D': set}; returns the new sets and pools."""
    C, D = set(members['C']), set(members['D'])
    fixedC = {i for i in C if u[i]['second']}
    fixedD = {i for i in D if u[i]['second']}
    cand_c = sorted(C - fixedC)
    cand_d = sorted(D - fixedD)
    c_up = pick(rng, cand_c, 4)
    c_down = pick(rng, [i for i in cand_c if i not in c_up], 6)
    d_up = pick(rng, cand_d, 6)
    d_down = pick(rng, [i for i in cand_d if i not in d_up], 9)
    b_down = pick(rng, up, 4) if mode == 'random' else nearest_replace(rng, u, c_up, up)
    from_d = d_up
    to_c = b_down + from_d                                  # (arrivals in C: 4 relegated from B, 6 promoted from D)
    e_up = pick(rng, down, 9) if mode == 'random' else nearest_replace(rng, u, d_down, down)
    to_d = c_down + e_up                                    # (arrivals in D: 6 relegated from C, 9 promoted from Eccellenza)
    C = (C - set(c_up) - set(c_down)) | set(to_c)
    D = (D - set(d_up) - set(d_down)) | set(to_d)
    up = sorted((set(up) - set(b_down)) | set(c_up))
    down = sorted((set(down) - set(e_up)) | set(d_down))
    return {'C': C, 'D': D}, up, down


def run(seasons, mode, seed):
    u, lv, up, down = start()
    size = {'C': 20, 'D': 18}
    rng = random.Random(seed)
    grp = {k: dict(v) for k, v in lv.items()}               # (rule's groups)
    base = {k: dict(v) for k, v in lv.items()}              # (baseline's groups)
    rows = []
    for s in range(1, seasons + 1):
        members, up, down = crossings(rng, u, {k: set(v) for k, v in grp.items()}, up, down, mode)
        row = {}
        for lvl in ('C', 'D'):
            ids = sorted(members[lvl])
            pts = {i: u[i]['pt'] for i in ids}
            sec = {i for i in ids if u[i]['second']} if lvl == 'C' else set()
            # --- the frozen rule
            anc = {g: R.centroid(u[i]['pt'] for i, gg in grp[lvl].items() if gg == g) for g in sorted(set(grp[lvl].values()))}
            last = {i: grp[lvl].get(i) for i in ids}
            prev = {i: grp[lvl][i] for i in sec}
            new = R.rule(pts, anc, size[lvl], last, sec, prev, s + 100 * seed)
            moved = sum(1 for i in ids if last[i] and new[i] != last[i] and i not in sec)
            # --- the baseline: continuing clubs keep their group (the second teams rotate by the same alternation: they are 'new' for the Hungarian but fixed by the rule's draw)
            banc = {g: R.centroid(u[i]['pt'] for i, gg in base[lvl].items() if gg == g) for g in sorted(set(base[lvl].values()))}
            fixed = {i: base[lvl][i] for i in ids if i in base[lvl] and i not in sec}
            if sec:
                sp = {i: base[lvl][i] for i in sec}
                import itertools
                allowed = [a for a in itertools.permutations(sorted(banc), len(sec)) if not any(sp.get(i) == g for i, g in zip(sorted(sec), a))]
                fixed.update(dict(zip(sorted(sec), allowed[(s + 100 * seed) % len(allowed)])))
            bnew = R.assign(pts, banc, size[lvl], {}, fixed=fixed)
            row[lvl] = dict(moved=moved, rule=R.compactness(pts, new), base=R.compactness(pts, bnew))
            grp[lvl] = new
            base[lvl] = bnew
        rows.append(row)
    return rows


def main():
    seasons = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for mode in (sys.argv[2:3] or ['local', 'random']):
        runs = [run(seasons, mode, sd) for sd in SEEDS]
        print(f'== mode {mode}: {seasons} seasons x {len(SEEDS)} seeds (sums / means over the seeds)')
        print('season | moved C  moved D | C mean/max km rule | base | D mean/max km rule | base')
        tot = {'C': 0, 'D': 0}
        for s in range(seasons):
            cells = []
            for lvl in ('C', 'D'):
                mv = sum(r[s][lvl]['moved'] for r in runs)
                tot[lvl] += mv
                cells.append(mv)
            f = lambda lvl, k: (sum(r[s][lvl][k][0] for r in runs) / len(runs), max(r[s][lvl][k][1] for r in runs))
            cr, cb, dr, db = f('C', 'rule'), f('C', 'base'), f('D', 'rule'), f('D', 'base')
            print(f'{s + 1:>6} | {cells[0]:>7} {cells[1]:>8} | {cr[0]:>6.0f}/{cr[1]:<5.0f} {cb[0]:>6.0f}/{cb[1]:<5.0f} | {dr[0]:>6.0f}/{dr[1]:<5.0f} {db[0]:>6.0f}/{db[1]:<5.0f}')
        print(f'total continuing clubs moved by the rule (3 seeds): C {tot["C"]}, D {tot["D"]}')


if __name__ == '__main__':
    main()
