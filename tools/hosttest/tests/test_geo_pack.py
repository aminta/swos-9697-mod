"""4.2 Serie D geography (MC 14/11): s7swap.geo_table - the pack's geo.neighbours is REQUIRED and checked: missing key, a girone
missing / unknown, a girone listing itself or twice, an asymmetric list, an unreachable girone: each refuses the build
(SystemExit), never an empty table; the shipped source (tools/s7pack_geo.json) and the real pack give the same 9 x 9 table."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import s7swap  # noqa: E402

TOOLS = os.path.join(os.path.dirname(__file__), '..', '..')
SRC = json.load(open(os.path.join(TOOLS, 's7pack_geo.json'), encoding='utf-8'))


def refuses(meta, n=9):
    try:
        s7swap.geo_table(meta, n)
    except SystemExit as e:
        return str(e)
    return None


def test_geo_table():
    errs = []
    good = {'geo': {'neighbours': SRC['neighbours']}}
    tab = s7swap.geo_table(good, 9)
    if len(tab) != 81 or tab[:3] != bytes((1, 3, 0xFF)) or tab[9 * 8:9 * 8 + 2] != bytes((7, 0xFF)):   # A: B D ; I: H
        errs.append(f'table {tab[:12].hex()} ...')
    bad = {
        'missing key': {},
        'empty': {'geo': {'neighbours': {}}},
        'a girone missing': {'geo': {'neighbours': {k: v for k, v in SRC['neighbours'].items() if k != 'I'}}},
        'asymmetric': {'geo': {'neighbours': dict(SRC['neighbours'], A='BDE')}},
        'self': {'geo': {'neighbours': dict(SRC['neighbours'], A='ABD')}},
        'twice': {'geo': {'neighbours': dict(SRC['neighbours'], A='BBD')}},
        'unknown': {'geo': {'neighbours': dict(SRC['neighbours'], A='BDZ')}},
        'unreachable': {'geo': {'neighbours': dict(SRC['neighbours'], H='G', I='')}},      # (I listed by nobody now: H no longer lists I)
    }
    for what, meta in bad.items():
        m = refuses(copy.deepcopy(meta))
        if m is None:
            errs.append(f'{what}: not refused')
    p = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita', 'pack.json')
    if os.path.exists(p):
        real = json.load(open(p, encoding='utf-8'))
        if s7swap.geo_table(real, len(real['files']['league_b']['divisions'])) != tab:
            errs.append('the real pack\'s table differs from tools/s7pack_geo.json')
    assert not errs, '; '.join(errs)


class FakePk:
    def __init__(self, rows):
        self.clubs = {r['key']: r for r in rows}


def test_geo_coords():
    """s7swap.geo_coords: no lat/lon columns = REFUSED (MC 14/11; only the test switch S7_GEO_NOCOORD gives None = lowest row); with them every Serie D / pool club needs one inside Italy's
    box, else the build is refused (missing, outside the box, not a number); other clubs' may be empty."""
    errs = []
    ok = [{'key': 'a', 'file': 'league_b', 'lat': '44.27', 'lon': '9.39'}, {'key': 'b', 'file': 'pool', 'lat': '37.50', 'lon': '15.09'},
          {'key': 'c', 'file': 'league', 'lat': '', 'lon': ''}]
    try:
        s7swap.geo_coords(FakePk([{'key': 'a', 'file': 'league_b'}]))
        errs.append('no columns: not refused')
    except SystemExit:
        pass
    os.environ['S7_GEO_NOCOORD'] = '1'                       # (the test switch: lowest-row control; modver.is_test() must hold in a test build)
    try:
        if s7swap.geo_coords(FakePk([{'key': 'a', 'file': 'league_b'}])) is not None:
            errs.append('switch: not None')
    finally:
        del os.environ['S7_GEO_NOCOORD']
    if s7swap.geo_coords(FakePk(ok)) != [(4427, 939), (3750, 1509), (0, 0)]:
        errs.append(f'values {s7swap.geo_coords(FakePk(ok))}')
    bads = {
        'missing for a Serie D club': [dict(ok[0], lat='', lon='')] + ok[1:],
        'missing for a pool club': [ok[0], dict(ok[1], lat='', lon='')],
        'outside Italy (Paris)': [dict(ok[0], lat='48.85', lon='2.35')] + ok[1:],
        'swapped lat/lon': [dict(ok[0], lat='9.39', lon='44.27')] + ok[1:],
        'not a number': [dict(ok[0], lat='x')] + ok[1:],
    }
    for what, rows in bads.items():
        try:
            s7swap.geo_coords(FakePk(rows))
            errs.append(f'{what}: not refused')
        except SystemExit:
            pass
    assert not errs, '; '.join(errs)
