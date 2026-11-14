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
