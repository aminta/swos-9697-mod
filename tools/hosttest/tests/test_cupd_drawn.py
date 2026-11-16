"""cupd.compile_table's guard (MC 16/11, the engine's rules 13 §3a): gplay.c cd_side reads a drawn round's pairs from
CD_ST.sd[4] - a drawn round of 3+ ties would read past it (into CD_ST.ent). The build refuses one:
- a fake bracket of 12, 6, then a drawn round of 3 ties: AssertionError naming the round;
- the same with 8, 4, then 2 ties (Italy's shape: drawn semi-finals) builds, its 2 ties DRAWN / DRAWN;
- the real Coppa Italia Serie D 2026-27 json (internal/world2526, when present) still builds."""
import json
import os
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import cupd  # noqa: E402


def _bracket(n1):                       # (rounds 0-1 as listed - 2 x n1 ties, then n1 -, round 2 drawn: n1 // 2 ties)
    m0 = [{'home_key': f'c{2 * i}', 'away_key': f'c{2 * i + 1}'} for i in range(2 * n1)]
    m1 = [{'home_from': f'W{2 * i}', 'away_from': f'W{2 * i + 1}'} for i in range(n1)]
    return {'rounds': [{'name': 'R0', 'date': '06/09', 'legs': 1, 'host': 'drawn', 'matches': m0},
                       {'name': 'R1', 'date': '13/09', 'legs': 1, 'host': 'drawn', 'matches': m1},
                       {'name': 'DRAWN', 'date': '20/09', 'legs': 1, 'host': 'drawn', 'pairing': 'draw', 'matches': []}]}


def _word(k):
    return 20 | int(k[1:]) << 8


def test_drawn_round_of_3_refused():
    try:
        cupd.compile_table(_bracket(6), _word)
    except AssertionError as e:
        assert 'drawn with 3 ties' in str(e) and 'DRAWN' in str(e), e
        return True, f'refused: {str(e)[:70]}'
    return False, 'a drawn round of 3 ties built'


def test_drawn_round_of_2_builds():
    tab, nr, nt = cupd.compile_table(_bracket(4), _word)
    assert (nr, nt) == (3, 14), (nr, nt)
    for t in (12, 13):
        x = tab[8 * nr + 6 * t:8 * nr + 6 * t + 4]
        assert x == bytes((0xFF, 0xFE, 0xFF, 0xFE)), (t, x.hex())
    return True, '8 + 4 + 2 drawn: built, the drawn ties FEFFh'


def test_italy_builds():
    js = os.path.join('world2526', 'formats', 'coppa_italia_serie_d_2627.json')    # (internal/ is live, unversioned:
    js = next((p for p in (os.path.join(TOOLS, '..', 'internal', js),                # this checkout's, else the main one)
                           os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', js)) if os.path.exists(p)), None)
    if not js:
        return True, 'SKIP: no internal/world2526 json here'
    d = json.load(open(js))
    keys = {c['key']: i for i, c in enumerate(c for c in d['clubs'] if c.get('file') == 'league')}
    tab, nr, nt = cupd.compile_table(d, lambda k: (20 | keys[k] << 8) if k in keys else None)
    assert (nr, nt) == (8, 161), (nr, nt)
    return True, 'Italy 2026-27: 8 rounds, 161 ties (drawn semi-finals: 2)'
