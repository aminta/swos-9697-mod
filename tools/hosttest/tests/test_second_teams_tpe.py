"""4.2 Taiwan's reserve sides (CTFA 2025/26 TFPL competition regulations Art. 27.2.3: a B team may not be promoted nor play the
promotion play-off; the next eligible clubs fill the place by ranking): the World 2026-27 data's tpe pack flags
TAIPEI RESERVES (first team TAIPEI) and TAICHUNG ROCK 2 (first team TAICHUNG ROCK), rules 'tpe' = never into the first team's
division (top 0xFF), no play-off; the President FA Cup keeps them (the 2025 cup had both: Sunny Bank AC Taipei Reserves,
Taichung Rock B); the engine's second-team table (mkseason.second_table) and zones' B-team table carry them, bteam knows the
rules code, and the world's B-team count stays inside gplay.c's BQ_N (24: SEC_BQ[0] is the season byte).
Data: W2627REL_DATA, else internal/world2526/world5tm-h3s7rl3 (and world5tm-h3s when present)."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..')))
MAIN = os.path.expanduser('~/swos-mod')
DATA = [os.environ['W2627REL_DATA']] if os.environ.get('W2627REL_DATA') else \
    [d for d in (os.path.join(MAIN, 'internal', 'world2526', n) for n in ('world5tm-h3s', 'world5tm-h3s7rl3')) if os.path.isdir(d)]
SECOND = {'taipeireserves': 'taipei', 'taichungrock2': 'taichungrock'}


def _clubs(d):
    return {r['key']: r for r in csv.DictReader(open(os.path.join(d, 'tpe', 'clubs.csv'), encoding='utf-8'))}


def test_reserve_sides_flagged():
    for d in DATA:
        cl = _clubs(d)
        assert {k: r['second_of'] for k, r in cl.items() if r['second_of']} == SECOND, d
        for k, f in SECOND.items():
            assert cl[k]['division'] == '1' and cl[f]['division'] == '0', (d, k)   # B in Div 2, A in the TFPL


def test_president_fa_cup_keeps_them():
    for d in DATA:
        ties = list(csv.DictReader(open(os.path.join(d, 'tpe', 'ties.csv'), encoding='utf-8')))
        ent = {c for r in ties for c in (r['home'], r['away']) if c}
        assert set(SECOND) <= ent, (d, sorted(set(SECOND) - ent))


def test_engine_tables_and_rules():
    import bteam
    import mkseason
    assert mkseason.SECOND_RULES['tpe'] == (0xFF, False) and 'tpe' in bteam.RULES
    for d in DATA:
        pk = mkseason.Pack(os.path.join(d, 'tpe'))
        assert {k for k, c in pk.clubs.items() if c.get('second_of')} == set(SECOND), d
        assert pk.league['second_teams']['rules'] == 'tpe'
        n = 0                                           # the world's B teams (every country with 'second_of'): gplay.c BQ_N = 24, [0] is
        for cc in sorted(os.listdir(d)):                #  the season byte: at most 23 (zones.bskip_entries asserts the same)
            f = os.path.join(d, cc, 'clubs.csv')
            if os.path.isfile(f):
                n += sum(1 for r in csv.DictReader(open(f, encoding='utf-8')) if r.get('second_of'))
        assert 19 <= n <= 23, (d, n)                    # (17 before Taiwan: IT 4, ES 2, DE 2, NL 4, PT 3, NZ 2 + the 2 Taiwanese)


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
    print('ok', DATA)
