"""4.2 fixture port P3 (motore-fixport-plan.md): tools/fport.py's slot-4 reserved windows, checked against the
slot-4 DOSBox probe's runs (12/11, 42-fprobe) and against themselves. Host-only (the original exe + the world
snapshot internal/world2526/world5tm-h2; no build, no DOSBox)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
import fport  # noqa: E402

MAIN = os.path.dirname(os.path.abspath(TOOLS))
H2 = os.environ.get('HT_FPORT_WORLD') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-h2')
EXE = os.path.join(MAIN, 'orig', 'ITALIAN.EXE')
_W = {}


def _world():
    if 'w' not in _W:
        _W['w'] = fport.world(H2, EXE)
    return _W['w']


def _skip():
    if not os.path.isdir(H2) or not os.path.isfile(EXE):
        return True, f'SKIP: {H2} or {EXE} missing'
    return None


def _win(cc, div, user):
    return next(w for w in _world()[cc][div] if w[2].startswith(user))


def test_fport_league_days():
    """cseg_2730A's spread = the probe's Serie A calendar (fprobe-lead [cal]: 56 57 59 ... 91 92 94 ... last 128)"""
    s = _skip()
    if s:
        return s
    import json
    pk = json.load(open(os.path.join(H2, 'ita', 'pack.json')))
    lg = fport._league(pk)
    wk = fport.league_weeks(lg, lg['divisions'], 0, EXE)
    seen = [56, 57, 59, 61, 63, 65, 67, 69, 71, 73, 75, 77, 79, 81, 83, 85, 87, 89, 91, 92, 94, 96, 98, 100, 102,
            104, 106, 108, 110, 112]
    ok = wk[:30] == seen and wk[-1] == 128 and len(wk) == 38
    return ok, f'Serie A: {len(wk)} days, {wk[:6]}..{wk[-3:]}'


def test_fport_probe_q6():
    """Serie B's play-off window [128, END] (dplay): the probe's fixture at 130 (fprobe-send3: play-off skipped) is
    refused; the boundary unit2 = L - 1 = 127 is accepted (rule 6's positive boundary, MC)"""
    s = _skip()
    if s:
        return s
    ws = _world()['ita'][1]
    w = _win('ita', 1, 'dplay')
    bad = fport.check((130, 130, 122), ws)
    good = fport.check((127, 127, 119), ws)
    return w[:2] == (128, fport.NONE) and bad == w and good is None, f'window {w}; 130 -> {bad}; 127 -> {good}'


def test_fport_probe_supercup():
    """the Supercoppa's early window [56, 93] (supercups2627 'early', 22/12): the probe's fixture at 65 (clash65:
    missed while the real Supercoppa held slot 4 57..93) is refused; the one at 98 installed at 93 (clash98: played)
    is accepted - an install at the advance from E comes after E's match"""
    s = _skip()
    if s:
        return s
    ws = _world()['ita'][0]
    w = _win('ita', 0, 'supercup:ita')
    r65 = fport.check((65, 65, 57), ws)
    r98 = fport.check((98, 98, 93), ws)
    off = fport.check((65, 65, 57), ws, live=lambda c: c != 'entrant')     # (not an entrant: no window)
    return w[:2] == (56, 93) and r65 == w and r98 is None and off is None, \
        f'window {w}; 65 -> {r65}; 98@93 -> {r98}; 65 not entrant -> {off}'


def test_fport_stage_window():
    """a mid-season stage title (ARG Clausura's knockout, then_build Trofeo): inside refused, fully before B / at E
    accepted; the chain's next window starts at the previous one's E"""
    s = _skip()
    if s:
        return s
    ws = _world()['arg'][0]
    cl = _win('arg', 0, 'stage:arg_cl_ko')
    tr = _win('arg', 0, 'stage:arg_trofeo')
    b, e = cl[:2]
    r_in = fport.check((b + 1, b + 1, b), ws)
    r_before = fport.check((b - 3, b - 1, b - 4), [cl])
    r_after = fport.check((tr[1] + 1, tr[1] + 1, tr[1]), ws)
    ok = r_in is not None and r_before is None and r_after is None and tr[0] == e and b < e
    return ok, f'{cl} -> {tr}; inside {r_in}; before {r_before}; after {r_after}'


def test_fport_cupd_alive():
    """Coppa Italia Serie D rounds: a window per round on every Serie D group, conditional on the club still in the
    cup; the final (06/05+1 etc.) inside the league"""
    s = _skip()
    if s:
        return s
    ws = _world()['ita'][5]
    cd = [w for w in ws if w[2].startswith('cupd:')]
    f = cd[-1]
    on = fport.check((f[1], f[1], f[0]), ws)
    off = fport.check((f[1], f[1], f[0]), [w for w in ws if w[3]], live=lambda c: c != 'alive')
    return len(cd) >= 6 and all(w[3] == 'alive' for w in cd) and on is not None and off is None, \
        f'{len(cd)} rounds, final {f}; alive -> {on}; out -> {off}'


def test_fport_world_sane():
    """every country: B <= E, B within the season (<= 255), no unresolved stage title, the same table twice"""
    s = _skip()
    if s:
        return s
    w = _world()
    bad, n = [], 0
    for cc, ds in w.items():
        if 'unresolved' in ds:
            bad.append((cc, ds['unresolved']))
        for d, ws in ds.items():
            if d == 'unresolved':
                continue
            for x in ws:
                n += 1
                if not (0 <= x[0] <= x[1] and x[0] <= 255):
                    bad.append((cc, d, x))
    again = fport.world(H2, EXE)
    return not bad and again == w and n > 100, f'{len(w)} countries, {n} windows; bad {bad[:5]}'


def test_fport_stage_cap():
    """forced: a stage title whose B + days + 1 passes 255 (ARG's Clausura knockout given 60 two-leg rounds of gap 2)
    -> E clamps at 255 (the season's byte range; END = 65535 stays the season end). Pins the cap for the swcc
    cross-check (OpenSWOS 12/11), which h2 alone never reaches"""
    s = _skip()
    if s:
        return s
    import copy
    import json
    pk = json.load(open(os.path.join(H2, 'arg', 'pack.json')))
    pk['dir'] = os.path.join(H2, 'arg')
    pk = copy.deepcopy(pk)
    po = next(p for p in fport._league(pk)['ko_playoffs'] if p.get('key') == 'arg_cl_ko')
    po['rounds'] = [{'legs': 2, 'gap': 2}] * 60
    w = next(x for x in fport.windows(pk, EXE)[0] if x[2] == 'stage:arg_cl_ko')
    tr = next(x for x in fport.windows(pk, EXE)[0] if x[2] == 'stage:arg_trofeo')
    ok = w[1] == 255 and w[0] + fport.po_days(po) + 1 > 255 and tr[0] == 255 and tr[1] == 255
    return ok, f'cl_ko {w}, trofeo {tr} (days {fport.po_days(po)})'
