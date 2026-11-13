"""4.2 C (calendar contract, MC 13/11; internal/handoff/c-calendar-contract.md): the career calendar model, ONE entry
point for every piece that needs career weeks - the fixture port (reserved windows), the CPU market (transfer windows),
the national teams (FIFA windows, 4.5).

Weeks are the career calendar's week bytes (split.week_of: 8 a month from January of the season's first year, a year
= 96). The week maths lives in fport.py (league units, reserved windows: Motore's P3) and is never copied here; cal.py
adds the windows the game itself does not have:

- transfer windows, per country (the CPU market acts every career week of [B, E]: sm_window_begin at B, then
  sm_window_step at each week end; Mercato CPU 13/11):
  - from the pack's data when it has them - pack.json "transfer_windows": {"summer": {"from": "dd/mm", "to": "dd/mm"},
    "winter": {...}} with the real dates (FIFA TMS registration periods), "+1" for the next calendar year as in
    split.week_of;
  - otherwise the default: summer from the season's first career week S for W_SUMMER weeks, winter from S + 40 (five months
    later: January for an August start, July for a February one) for W_WINTER weeks. The defaults are Davide's open W decision (Regia),
    marked 'default' in the output so a world can be audited for missing data.
- FIFA windows: none yet (4.5), the kind exists so the table layout does not change.

A window is (kind, B, E, source): B the first week the window is open, E its last (inclusive), source 'data' /
'default'. window_at(windows, week) -> (kind, w) with w = week - B, or None.
"""
import json
import os

import fport

W_SUMMER = 8                                    # (career weeks; Davide's W, default until his decision - Regia)
W_WINTER = 4
KINDS = ('summer', 'winter', 'fifa')


def season_start(pk, exe=None):
    """S: the season's first career week = the earliest league unit of any division (the career's first advance)"""
    lg = fport._league(pk)
    if not lg:
        return None
    divs = fport._divisions(pk, lg)
    if not divs or not all(dv['teams'] >= 2 for dv in divs):
        return None
    return min(fport.league_weeks(lg, divs, d, exe)[0] for d in range(len(divs)))


def league_units(pk, exe=None):
    """{division: [week of each match day]} (fport.league_weeks)"""
    lg = fport._league(pk)
    if not lg:
        return {}
    divs = fport._divisions(pk, lg)
    return {d: fport.league_weeks(lg, divs, d, exe) for d in range(len(divs)) if divs[d]['teams'] >= 2}


def reserved(pk, exe=None):
    """the slot-4 reserved windows (fport.windows: {division: [(B, E, user, cond)]}), unchanged"""
    return fport.windows(pk, exe)


def transfer_windows(pk, exe=None):
    """[(kind, B, E, source)] for one country pack, summer first"""
    import split
    tw = pk.get('transfer_windows') or {}
    s = season_start(pk, exe)
    out = []
    for kind, w, off in (('summer', W_SUMMER, 0), ('winter', W_WINTER, 40)):
        d = tw.get(kind)
        if d:
            b, e = split.week_of(d['from']), split.week_of(d['to'])
            assert e >= b, f"{pk.get('id')}: transfer window {kind} ends before it starts ({d})"
            out.append((kind, b, e, 'data'))
        elif s is not None:
            out.append((kind, s + off, s + off + w - 1, 'default'))
    if len(out) == 2:
        assert out[0][2] < out[1][1], f"{pk.get('id')}: summer and winter windows overlap {out}"
    return out


def window_at(wins, week):
    """(kind, w) when career week `week` is inside a window of wins ([(kind, B, E, source)]), w = week - B; else None"""
    for kind, b, e, _ in wins:
        if b <= week <= e:
            return kind, week - b
    return None


def country(pk, exe=None):
    """the whole model of one country: {'S', 'league', 'reserved', 'transfer'}"""
    return {'S': season_start(pk, exe), 'league': league_units(pk, exe), 'reserved': reserved(pk, exe),
            'transfer': transfer_windows(pk, exe)}


def world(src, exe=None):
    """{country id: country model} for a world snapshot dir (packs as <cc>/pack.json), as fport.world"""
    out = {}
    for cc in sorted(os.listdir(src)):
        f = os.path.join(src, cc, 'pack.json')
        if os.path.isfile(f):
            pk = json.load(open(f))
            pk['dir'] = os.path.join(src, cc)
            out[cc] = country(pk, exe)
    return out


if __name__ == '__main__':
    import sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = args[0] if args else os.path.join(os.path.dirname(HERE), 'internal', 'world2526', 'world5tm-h2')
    w = world(src)
    if '--reserved-json' in sys.argv:            # (= fport.py --json: the cross-check, one source)
        print(json.dumps(fport.canonical({cc: m['reserved'] for cc, m in w.items()}), indent=1, sort_keys=True))
        sys.exit(0)
    nd = sum(1 for m in w.values() for t in m['transfer'] if t[3] == 'default')
    for cc, m in w.items():
        print(cc, 'S', m['S'], ' '.join(f'{k}[{b},{e}]{"*" if s == "default" else ""}' for k, b, e, s in m['transfer']))
    print(f'{len(w)} countries, {nd} default transfer windows (* = no data yet)')
