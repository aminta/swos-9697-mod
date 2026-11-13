"""4.2 fixture port, piece P3 (motore-fixport-plan.md): the slot-4 reserved windows of a career world.

Rule 6 (engine docs/fixture-port.md; sr_port cda25d4 slot4_windows): every exe user of slot 4 reserves, for the
career club's division, a window [B, E]. B is the unit whose calendar advance builds its contest, E the unit of its
last match (NONE = up to the season end). A port fixture (unit1, unit2, installed at `inst`) is outside a window
when unit2 < B or inst >= E (the advance from E runs after E's matches: probe clash98). Slot 4 is never cleared: the next install overwrites it (probe Q2 / Q3).

The windows come from the pack data and the original exe, never by hand. This is host-only Python with no build and
no DOSBox:
- L = the division's last league unit:
  - for a split league with 'weeks', the last date (split.week_of);
  - otherwise the league struct copied from country `dates_from` in the original exe (mkseason._league_body: header
    bytes 3 / 4 = first / last week). cseg_2730A spreads the days linearly from first to last; last < first means
    +96, a year later. Every division of a league ends at L.
- season end, [L, NONE]:
  - dplay 'ita' (dp_lend: Serie B's play-off / play-out in slot 4, and the parallel groups', conservatively);
  - gplay ko_playoffs built by gp_lend (promotion / playout / placement / title / europe / continental), for
    their entrant divisions. 'promedio' plays no match.
- stage titles (gp_build, mid-season): B = the week of the split stage's last day, which comes before the stage's
  'then' play-off. E = B + the play-off's days (gplay.c: d1 = week + 1, d2 = week + days + 1; each knockout round is
  its legs x its gap, each group round robin is its rounds x its legs). A then_build chain continues from E.
- national supercups and the UEFA Super Cup (supercups2627.json; gplay.c sc_step_c):
  - 'early': B = the league's first unit (built at the season's first advance), E = its date (the final's, when 4);
  - otherwise: B = the league unit before its date, E = its date.
  - Conditional: they apply only to an entrant (cond 'entrant'), and the runtime poll reads that live.
- Coppa Italia Serie D (cupd.json; gplay.c cd_step: built at the advance where GP_WK + 1 >= week1): per round,
  B = the last league unit before week1, E = week2 (or week1 for one leg). The window is on the Serie D divisions,
  cond 'alive' (the career club still in the cup).
The static table is a superset: B is the league day before a build, never later than the real build advance (other
calendar entries can only be later), so a fixture it accepts is accepted at run time too.
"""
import json
import os
import struct

NONE = 0xFFFF
SEASON_END = ('dplay', 'promotion', 'playout', 'placement', 'title', 'europe', 'continental')
HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(HERE)
SC_DATA = os.path.join(HERE, 'supercups2627.json')

_HDR = {}


def league_header_weeks(country, exe=None):
    """(first, last) week bytes of the original league struct of `country` (mkseason._league_body's lg[3] / lg[4])"""
    exe = exe or os.path.join(MAIN, 'orig', 'ITALIAN.EXE')
    if exe not in _HDR:
        import countries
        import lepatch
        p = lepatch.LEPatch(exe)
        countries.tables(p)
        _HDR[exe] = (p, countries.COMP[0])
    p, comp = _HDR[exe]
    gobj, gtab = p.target(2, comp + 4 * country)
    lobj, glg = p.target(gobj, gtab)
    lg = p.le.obj_bytes(lobj)[glg:glg + 13]
    assert lg[2] == country, lg.hex()
    return lg[3], lg[4]


def day_weeks(first, last, days):
    """cseg_2730A: the weeks of `days` match days spread from first to last (last < first: +96, a year later)"""
    if days == 1:
        return [first]
    if last < first:
        last += 96
    return [first + d * (last - first) // (days - 1) for d in range(days)]


def days_of(n, games):
    return n * (n - 1) // 2 // (n // 2) * games       # (split.days_before: cseg_2653B's days)


def _league(pk):
    return next((c for c in pk.get('competitions', []) if c.get('type') == 'league'), None)


def _divisions(pk, lg):
    """the league's divisions; a league without 'divisions' is one division of every 'league' club (clubs.csv)"""
    if lg.get('divisions'):
        return lg['divisions']
    n = 0
    f = os.path.join(pk.get('dir') or '', 'clubs.csv')
    if os.path.isfile(f):
        import csv
        n = sum(1 for r in csv.DictReader(open(f)) if r.get('file') == lg.get('clubs', 'league'))
    return [{'teams': n, 'names': lg.get('names') or {'*': ['?']}, 'split': lg.get('split')}]


def _split_divs(divs):
    return [(i, dv['split']) for i, dv in enumerate(divs) if (dv.get('split') or {}).get('weeks')]


def league_weeks(lg, divs, div, exe=None):
    """the career calendar's league units of division `div` (its match days' weeks)"""
    import split
    sp = dict(_split_divs(divs)).get(div)
    if sp:
        return [split.week_of(x) for x in sp['weeks']]
    dv = divs[div]
    first, last = league_header_weeks(lg.get('dates_from', 14), exe)
    games = (dv.get('split') or {}).get('games') or lg.get('games', 2)
    return day_weeks(first, last, days_of(dv['teams'] + dv['teams'] % 2, games))


def po_days(po):
    """a play-off's match days (gplay.c: legs per knockout round, x its gap; a group: its round robin's rounds)"""
    n = 0
    for rd in po.get('rounds') or []:
        legs, gap = int(rd.get('legs', 1)), max(1, int(rd.get('gap', 1) or 1))
        if 'group' in rd or rd.get('members'):
            m = len(rd.get('members') or [])
            n += (m - 1 + m % 2) * legs
        else:
            n += legs * gap
    return n


def _divs_of(po):
    out = set()
    for e in po.get('entrants') or []:
        if isinstance(e, list):
            out.add(e[0])
        elif isinstance(e, dict) and 'div' in e:
            out.add(e['div'])
    return out


def windows(pk, exe=None, sc=None):
    """{division: [(B, E, user, cond)]} for one country pack (its pack.json dict, + 'dir' for cupd.json)"""
    import split
    lg = _league(pk)
    if not lg:
        return {}
    divs = _divisions(pk, lg)
    nd = len(divs)
    if not nd or not all(dv['teams'] >= 2 for dv in divs):
        return {'unresolved': f'no club count for the league'} if nd else {}
    wk = {d: league_weeks(lg, divs, d, exe) for d in range(nd)}
    out = {d: [] for d in range(nd)}
    L = {d: wk[d][-1] for d in range(nd)}
    pos = lg.get('ko_playoffs') or []
    pos = pos if isinstance(pos, list) else []
    keys = {po.get('key'): po for po in pos if isinstance(po, dict)}
    # season end
    if lg.get('playoffs') == 'ita':
        par = lg.get('parallel')
        par = par[0] if isinstance(par, list) else par
        ds = {par['upper']} | set(range(par['first'], par['first'] + par['count'])) if par else {1}
        for d in sorted(ds):
            out[d].append((L[d], NONE, 'dplay', None))
    for po in pos:
        if not isinstance(po, dict) or po.get('kind') not in SEASON_END:
            continue
        for d in sorted(_divs_of(po)):
            if d < nd and (L[d], NONE, po['kind'], None) not in out[d]:
                out[d].append((L[d], NONE, po['kind'] + ':' + po.get('key', ''), None))
    # mid-season stage titles (gp_build after a split stage; then_build chains)
    after = {po.get('build_after'): po.get('key') for po in pos if isinstance(po, dict) and po.get('build_after')}
    unres = [po['key'] for po in pos if isinstance(po, dict) and po.get('kind') == 'stage_title'
             and not po.get('build_after') and not any(q.get('then_build') == po.get('key') for q in pos if isinstance(q, dict))]
    for si, sp in _split_divs(divs):
        st = sp.get('stages') or []
        ws = [split.week_of(x) for x in sp['weeks']]
        for k, s in enumerate(st):
            last = (st[k + 1]['after'] if k + 1 < len(st) else len(ws)) - 1
            b, key = ws[last], after.get(s.get('then'))
            seen = set()
            while key in keys and key not in seen:
                seen.add(key)
                po = keys[key]
                e = min(b + po_days(po) + 1, 255)
                for d in sorted(_divs_of(po) | {si}):
                    if d < nd:
                        out[d].append((b, e, 'stage:' + key, None))
                b, key = e, po.get('then_build')
    # supercups
    sc = sc if sc is not None else {k: v for k, v in json.load(open(SC_DATA)).items() if not k.startswith('_')}
    cc = str(pk.get('id', '')).split('-')[-1]
    for name in (cc, 'uefa'):
        d0 = sc.get(name)
        if not d0 or (name == 'uefa' and pk.get('continent') not in ('europe', 0, None)):
            continue
        w1 = split.week_of(d0['date'])
        e = split.week_of(d0['final_date']) if d0.get('final_date') else w1
        lw = wk[0]
        b = lw[0] if d0.get('early') else max([u for u in lw if u < w1] or [lw[0]])
        out[0].append((b, e, 'supercup:' + name, 'entrant'))
    # Coppa Italia Serie D
    cd = lg.get('cup_d')
    if cd and pk.get('dir'):
        import cupd
        sd = [i for i, dv in enumerate(divs) if 'SERIE D' in (dv['names'].get('*') or dv['names'].get('it') or [''])[0]]
        data = json.load(open(os.path.join(pk['dir'], cd['file'])))
        for r in data['rounds']:
            w1, w2 = cupd._weeks(r.get('date', ''))
            if not w1:
                continue
            if r.get('legs', 1) == 2 and not w2:
                w2 = w1 + 2
            for d in sd:
                b = max([u for u in wk[d] if u < w1] or [wk[d][0]])
                out[d].append((b, w2 if r.get('legs', 1) == 2 else w1, 'cupd:' + r.get('round', '?'), 'alive'))
    done = {w[2][6:] for ws in out.values() for w in ws if w[2].startswith('stage:')}
    unres += [po['key'] for po in pos if isinstance(po, dict) and po.get('kind') == 'stage_title'
              and po.get('build_after') and po['key'] not in done]
    if unres:
        out['unresolved'] = unres
    return out


def outside(fx, win):
    """rule 6 for one window: fx = (unit1, unit2, inst) -> True when outside [B, E]. inst = the unit whose advance
    installs it; that advance runs after the unit's matches, so an install at E itself is outside (probe clash98:
    installed at 93 = the Supercoppa's E, played at 98)"""
    u1, u2, inst = fx
    b, e = win[0], win[1]
    return u2 < b or inst >= e


def check(fx, wins, live=lambda cond: True):
    """the first window fixture fx meets ((B, E, user, cond)), or None. live(cond): is a conditional window on (the
    runtime poll's question; static = every window on)"""
    for w in wins:
        if (w[3] is None or live(w[3])) and not outside(fx, w):
            return w
    return None


def canonical(w):
    """the cross-check form (fport vs swcc, OpenSWOS milestone C): {cc: {div: [[B, E, user, cond], ...]}} with
    divisions as strings, each list sorted by (B, E, user), END = 65535, cond null / 'entrant' / 'alive'; user =
    '<kind>:<key>' ('dplay' alone), kind in dplay / promotion / playout / placement / title / europe / continental /
    stage / supercup / cupd"""
    out = {}
    for cc, ds in sorted(w.items()):
        out[cc] = {str(d): sorted([list(x) for x in ws], key=lambda x: (x[0], x[1], x[2]))
                   for d, ws in ds.items() if d != 'unresolved' and ws}
        if 'unresolved' in ds:
            out[cc]['unresolved'] = ds['unresolved']
    return out


def world(src, exe=None):
    """{country id: {division: windows}} for a world snapshot dir (packs as <cc>/pack.json)"""
    out = {}
    for cc in sorted(os.listdir(src)):
        f = os.path.join(src, cc, 'pack.json')
        if os.path.isfile(f):
            pk = json.load(open(f))
            pk['dir'] = os.path.join(src, cc)
            out[cc] = windows(pk, exe)
    return out


if __name__ == '__main__':
    import sys
    sys.path.insert(0, HERE)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = args[0] if args else os.path.join(MAIN, 'internal', 'world2526', 'world5tm-h2')
    if '--json' in sys.argv:                     # (the cross-check file: python3 tools/fport.py --json <world dir>)
        print(json.dumps(canonical(world(src)), indent=1, sort_keys=True))
        sys.exit(0)
    for cc, ds in world(src).items():
        for d, ws in ds.items():
            if d == 'unresolved':
                print(cc, 'UNRESOLVED', ws)
            elif ws:
                print(cc, d, ' '.join(f'[{b},{"END" if e == NONE else e}]{u}{"?" + c if c else ""}' for b, e, u, c in ws))
