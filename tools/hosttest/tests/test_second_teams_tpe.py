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


def test_promotion_playoff():
    """Taiwan Div. 2 2nd v TFPL 7th (CTFA 2025/26 TFPL regulations Art. 4.6 / 7.3 / 8: the Div. 2 champion goes up directly, the TFPL
    8th down directly, the 7th and the runner-up play ONE match at the TFPL 7th's ground (7.3.2), 2 x 15 min extra time, then penalties
    (8.1, 8.5); a licence-less runner-up is replaced by the next eligible club = the reserve rule, Art. 27.2.2-3). The data: the live
    dirs once tpe-fix-20261116/REAPPLY.txt has run, and always the patched copies kept next to it."""
    import json
    import mkseason
    sys.path.insert(0, os.path.join(MAIN, 'internal', 'world2526'))
    import formats_data
    po = formats_data.KO['TPE']
    assert len(po) == 1 and po[0]['entrants'] == [[0, 7], [1, 2]] and po[0]['kind'] == 'promotion'
    assert po[0]['rounds'] == [formats_data.R([[0, 1]], 1, 'listed')] and (po[0]['winner_div'], po[0]['loser_div']) == (0, 1)
    assert formats_data.DIRECT['TPE'] == {0: (0, 1), 1: (1, 0)}
    import shutil
    import tempfile
    fix = os.path.join(MAIN, 'internal', 'world2526', 'tpe-fix-20261116', 'patched')
    dirs = []
    for n in (sorted(os.listdir(fix)) if os.path.isdir(fix) else []):        # (the patched clubs.csv + pack.json over the live tpe dir)
        live = os.path.join(MAIN, 'internal', 'world2526', n, 'tpe')
        if os.path.isdir(live):
            t = os.path.join(tempfile.mkdtemp(), 'tpe')
            shutil.copytree(live, t)
            for f in ('clubs.csv', 'pack.json'):
                shutil.copy(os.path.join(fix, n, f), t)
            dirs.append(t)
    dirs += [os.path.join(d, 'tpe') for d in DATA
             if any(c.get('ko_playoffs') for c in json.load(open(os.path.join(d, 'tpe', 'pack.json')))['competitions'])]
    assert dirs, 'no patched Taiwan data'
    for d in dirs:
        pk = mkseason.Pack(d)
        lg = pk.league
        assert [{k: v for k, v in x.items() if k != 'names'} for x in lg['ko_playoffs']] == \
            [{k: v for k, v in x.items() if k != 'names'} for x in po], d     # (names: shortened by the font guard on load)
        assert lg['ko_playoffs'][0]['rounds'][0]['level'] == 'et_pens'      # (Art. 8.1 / 8.5: extra time, then penalties)
        assert [(x['promoted'], x['relegated']) for x in lg['divisions']] == [(0, 1), (1, 0)], d
        assert [x['teams'] for x in lg['divisions']] == [8, 7], d
        pk._balance(lg['divisions'])                  # (each level keeps its size: the play-off swaps one club each way)


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
    print('ok', DATA)
