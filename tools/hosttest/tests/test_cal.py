"""4.2 C1 (calendar contract, MC 13/11): tools/cal.py, the one calendar model. Host-only (the original exe + the world
snapshot internal/world2526/world5tm-h2; no build, no DOSBox)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)

MAIN = os.path.dirname(os.path.abspath(TOOLS))
H2 = os.environ.get('HT_FPORT_WORLD') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-h2')
EXE = os.path.join(MAIN, 'orig', 'ITALIAN.EXE')


def _skip():
    if not os.path.isdir(H2) or not os.path.isfile(EXE):
        return True, f'SKIP: {H2} or {EXE} missing'
    return None


def test_cal_reserved_is_fport():
    """cal.py's reserved windows = fport's, byte for byte in the canonical JSON (one source, no copied maths)"""
    s = _skip()
    if s:
        return s
    import cal
    import fport
    a = json.dumps(fport.canonical({cc: m['reserved'] for cc, m in cal.world(H2, EXE).items()}), sort_keys=True)
    b = json.dumps(fport.canonical(fport.world(H2, EXE)), sort_keys=True)
    return a == b, f'{len(json.loads(a))} countries, reserved == fport' if a == b else 'cal reserved != fport --json'


def test_cal_world_transfer():
    """every shipped country: S known, a summer and a winter window, summer before winter, both inside the season's
    96 weeks from S, no transfer week inside the league's own first unit range before S"""
    s = _skip()
    if s:
        return s
    import cal
    bad, nd = [], 0
    w = cal.world(H2, EXE)
    for cc, m in w.items():
        t = m['transfer']
        if m['S'] is None:
            continue
        if [k for k, *_ in t] != ['summer', 'winter']:
            bad.append(f'{cc}: windows {t}')
            continue
        (_, b1, e1, _), (_, b2, e2, _) = t
        if not (m['S'] <= b1 <= e1 < b2 <= e2 < m['S'] + 96):
            bad.append(f'{cc}: S {m["S"]} {t}')
        nd += sum(1 for x in t if x[3] == 'default')
    return not bad, '; '.join(bad[:5]) or f'{len(w)} countries, {nd} default windows (no data yet)'


def test_cal_window_at_and_data():
    """window_at: B and E inclusive, w = week - B, None outside; pack data overrides the default; a window ending
    before it starts, or summer overlapping winter, is refused"""
    import cal
    wins = [('summer', 56, 63, 'default'), ('winter', 96, 99, 'default')]
    cases = [(55, None), (56, ('summer', 0)), (63, ('summer', 7)), (64, None), (96, ('winter', 0)), (99, ('winter', 3)),
             (100, None)]
    bad = [f'week {x}: {cal.window_at(wins, x)} != {want}' for x, want in cases if cal.window_at(wins, x) != want]
    pk = {'id': 'zz', 'transfer_windows': {'summer': {'from': '01/07', 'to': '01/09'},
                                           'winter': {'from': '02/01+1', 'to': '02/02+1'}}}
    cal_s = cal.season_start
    cal.season_start = lambda pk, exe=None: 56
    try:
        t = cal.transfer_windows(pk)
        if t != [('summer', 48, 64, 'data'), ('winter', 96, 104, 'data')]:
            bad.append(f'data windows {t}')
        for tw in ({'summer': {'from': '01/09', 'to': '01/07'}},
                   {'summer': {'from': '01/07', 'to': '01/03+1'}, 'winter': {'from': '02/01+1', 'to': '02/02+1'}}):
            try:
                cal.transfer_windows({'id': 'zz', 'transfer_windows': tw})
                bad.append(f'not refused: {tw}')
            except AssertionError:
                pass
        d = cal.transfer_windows({'id': 'zz'})
        if d != [('summer', 56, 56 + cal.W_SUMMER - 1, 'default'), ('winter', 96, 96 + cal.W_WINTER - 1, 'default')]:
            bad.append(f'defaults {d}')
    finally:
        cal.season_start = cal_s
    return not bad, '; '.join(bad) or f'{len(cases)} lookups, data override, 2 refusals, defaults'
