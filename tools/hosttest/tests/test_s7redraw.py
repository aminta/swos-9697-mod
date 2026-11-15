"""S7 redraw oracle (tools/s7redraw.py, Panchina 15/11): its goldens (tools/s7redraw_golden.json, the cases Shaved's C redraw must reproduce byte for byte)
and the rule's invariants: every group exactly `size` clubs, no club lost or twice, the second teams in distinct groups and none in last season's
group (the written constraints), the same input twice gives the same groups (determinism)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))

import s7redraw as R


def _cases():
    return json.load(open(R.GOLDEN))


def _run(c):
    clubs = {k: tuple(v) for k, v in c['clubs'].items()}
    anchors = {g: tuple(v) for g, v in c['anchors'].items()}
    return R.rule(clubs, anchors, c['size'], c['last'], set(c['second']), c['prev_second'], c['seed'])


def test_s7redraw_golden():
    cs = _cases()
    assert len(cs) >= 27
    for c in cs:
        assert _run(c) == c['out'], c['name']


def test_s7redraw_invariants():
    for c in _cases():
        out = c['out']
        assert set(out) == set(c['clubs']), ('a club lost or invented', c['name'])
        for g in c['anchors']:
            assert sum(1 for v in out.values() if v == g) == c['size'], (c['name'], g)
        sec = c['second']
        assert len({out[k] for k in sec}) == len(sec), ('two second teams in one group', c['name'])
        assert all(out[k] != c['prev_second'].get(k) for k in sec), ('a second team in last season\'s group', c['name'])


def test_s7redraw_deterministic():
    for c in _cases():
        assert _run(c) == _run(c), c['name']


def test_s7redraw_seed_draw():
    """The second teams' arrangement is the seed's pick among the allowed ones: all allowed arrangements occur over the seeds."""
    by = {}
    for c in _cases():
        if c['name'] == 'real_C' or c['name'].startswith('C_seed'):
            by[c['seed']] = tuple(c['out'][k] for k in sorted(c['second']))
    assert len(set(by.values())) == 2, by          # (Inter U23 A / Juventus NG B / Atalanta C last season: 2 derangements)
