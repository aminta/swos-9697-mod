"""4.2 outcome gate (MC 14/11, internal/handoff/42-diff-outcome-gate.md): NORMAL = the classic game, judged by what the
matches produce, not by the frame trace (a pure per-frame delay moves the match: DIFF_DELAY test).

Input: diff_ab json lines (DIFF_AB_RECIPE ref / cal / new, DIFF_LEVELS 3 = NORMALE, 5 = DIFFICILE), one or more files
per side. Team 1 (goals[0]) is the coach side, team 2 the computer; stats rows are top / bottom team, mapped by topctl.

  python3 tools/outcome_gate.py --ref A.jsonl --cal B.jsonl --hard C.jsonl --new D.jsonl [--new ...] --out NAME

Rule per metric: |mean(X) - mean(REF)| <= max(3 x Welch SE, floor). The gate is valid only if CAL vs REF passes every
metric and DIFFICILE vs REF fails on the CPU goal difference with the CPU better; then NEW vs REF must pass every metric.
Writes internal/swostest/outcome-gate/NAME.md + .json (the table a later rc is compared with)."""
import argparse
import json
import math
import os

# (name, per-match value, floor kind, floor): floor 'abs' = the value itself, 'rel' = a share of REF's mean
METRICS = (
    ('goals', lambda m: m['g_cpu'] + m['g_coach'], 'abs', 0.3),
    ('attempts', lambda m: m['att'], 'rel', 0.15),
    ('on target', lambda m: m['ont'], 'rel', 0.15),
    ('CPU possession %', lambda m: m['poss'], 'abs', 3.0),
    ('fouls', lambda m: m['fouls'], 'rel', 0.20),
    ('bookings', lambda m: m['book'], 'rel', 0.20),
    ('corners', lambda m: m['corn'], 'rel', 0.20),
    ('penalties', lambda m: m['pens'], 'abs', 0.1),
    ('sendings off', lambda m: m['off'], 'abs', 0.1),
)
PAIRINGS = {'sw': ('BAYERN MUNICH', 'ST. PAULI'), 'eq': ('HAMBURG', 'SCHALKE'), 'ws': ('ST. PAULI', 'BAYERN MUNICH')}
POWER = ('CPU goal difference', lambda m: m['g_cpu'] - m['g_coach'], 'abs', 0.3)
SUPPORT = ('CPU shots on target', lambda m: m['ont_cpu'], 'rel', 0.15)   # (reported, not required: MC 14/11)


def load(paths):
    rows = []
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            if 'goals' not in r or 'stats' not in r:
                raise SystemExit(f'{p}: a match without a result: {r}')
            rows.append(r)
    seen = [(r['pairing'], r['seed']) for r in rows]
    if len(set(seen)) != len(seen):
        raise SystemExit(f'{paths}: a (pairing, seed) twice')
    return rows


def per_match(r):
    st = r['stats']
    home, away = PAIRINGS[r['pairing']]                 # (team 1 = home = the coach side; topctl reads 0 for a coach
    top = r.get('top') or ''                            #  team, so the side comes from the top team's name, 8 chars)
    if not top or home.startswith(top) == away.startswith(top):
        raise SystemExit(f'top team {top!r} is neither {home} nor {away}: {r}')
    coach_top = home.startswith(top)
    coach, cpu = (st[0], st[1]) if coach_top else (st[1], st[0])
    tot = [a + b for a, b in zip(st[0], st[1])]
    return dict(g_coach=r['goals'][0], g_cpu=r['goals'][1], att=tot[5], ont=tot[6], ont_cpu=cpu[6],
                poss=100.0 * cpu[0] / max(1, cpu[0] + coach[0]), fouls=tot[2], book=tot[3], corn=tot[1],
                off=tot[4], pens=r['pens'])


def stats(xs):
    n = len(xs)
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return mu, var, n


def compare(ref, oth, metric):
    name, f, kind, fl = metric
    a, b = [f(m) for m in ref], [f(m) for m in oth]
    (ma, va, na), (mb, vb, nb) = stats(a), stats(b)
    se = math.sqrt(va / na + vb / nb)
    floor = fl if kind == 'abs' else fl * abs(ma)
    thr = max(3 * se, floor)
    d = mb - ma
    return dict(metric=name, ref=ma, other=mb, se=se, delta=d, threshold=thr, ok=abs(d) <= thr, n=(na, nb))


def side(paths):
    return [per_match(r) for r in load(paths)]


def main():
    ap = argparse.ArgumentParser()
    for k in ('ref', 'cal', 'hard', 'easy', 'new'):
        ap.add_argument('--' + k, action='append', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ref, cal, hard, easy, new = side(a.ref), side(a.cal), side(a.hard), side(a.easy), side(a.new)
    res = {'cal': [compare(ref, cal, m) for m in METRICS + (POWER,)],
           'hard': [compare(ref, hard, POWER), compare(ref, hard, SUPPORT)],
           'easy': [compare(ref, easy, POWER), compare(ref, easy, SUPPORT)],
           'new': [compare(ref, new, m) for m in METRICS + (POWER,)]}
    cal_ok = all(x['ok'] for x in res['cal'])
    h, e = res['hard'][0], res['easy'][0]
    power_ok = not h['ok'] and h['delta'] > 0 and not e['ok'] and e['delta'] < 0   # (both directions, MC 14/11)
    valid = cal_ok and power_ok
    new_ok = all(x['ok'] for x in res['new'])
    verdict = ('PASS' if new_ok else 'FAIL') if valid else 'VOID'
    lines = [f'# 4.2 outcome gate: {a.out}', '',
             f'Verdict: **{verdict}** (CAL vs REF {"passes" if cal_ok else "FAILS"}; DIFFICILE vs REF on the CPU goal '
             f'difference {"fails with the CPU better and FACILE fails with the CPU worse: the gate sees one real step" if power_ok else "and/or FACILE do NOT both fail the right way: gate too weak"}).',
             f'Matches: REF {len(ref)}, CAL {len(cal)}, DIFFICILE {len(hard)}, FACILE {len(easy)}, NEW {len(new)}. '
             f'Rule: |delta| <= max(3 x Welch SE, floor). CPU shots on target in the power tables: supporting, not required.', '']
    for k, title in (('cal', 'CAL (REF + pure delay) vs REF'), ('hard', 'DIFFICILE vs REF (power check: CPU better)'),
                     ('easy', 'FACILE vs REF (power check: CPU worse)'),
                     ('new', 'NEW (NORMALE + CLASSICO) vs REF')):
        lines += [f'## {title}', '', '| metric | REF mean | other mean | delta | Welch SE | threshold | verdict |',
                  '|---|---|---|---|---|---|---|']
        for x in res[k]:
            lines.append(f'| {x["metric"]} | {x["ref"]:.3f} | {x["other"]:.3f} | {x["delta"]:+.3f} | {x["se"]:.3f} | '
                         f'{x["threshold"]:.3f} | {"ok" if x["ok"] else "OUT"} |')
        lines.append('')
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(lines))
    json.dump(dict(verdict=verdict, inputs=vars(a), **res), open(os.path.join(d, a.out + '.json'), 'w'), indent=1)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
