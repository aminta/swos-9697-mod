"""5.0 NT piece (1) (Nazionali exe, MC 15/11, D1 Option A / D2 G1'): the BUILD side of the national teams' global numbers - a
synthetic 211-NT national pack (ntfixture: 55 / 53 / 10 / 35 / 47 / 11 teams, explicit bases 2409 / 2464 / 2517 / 2527 / 2562 /
2609, the layout of nt-layout-42nats9.json) through mkseason.NationalPack and bigtables.nt_files / limit_all:
- test_nt_bases:      the §4.1 numbering: bases = tcn[80..85], contiguous, count = next base - base, globals 2409..2619 each once,
                      LIMIT_ALL 2620 over LIMIT_CLUBS 2409;
- test_nt_dormant:    no NT data (no national pack; the 1984-85 national pack with its game bases): LIMIT_ALL == LIMIT_CLUBS, no NT file;
- test_nt_refusals:   a file of 256 ordinals, bases not contiguous, globals past 4096, an NT pack with a missing file: each refused;
- test_nt_split_users: the saved-range users take LIMIT_CLUBS (uefacoef NG, guests, globnum, pgroups / gplay NSUM, patch.py's club-file
                      assert), none the bare LIMIT; the per-global C arrays (gplay.c pg_pend, ctgame.c CG_TAB) hold LIMIT_ALL_MAX.
The runtime tests of the same list (LoadTeamFile's +2 words, SetLeagueNumbers' league byte, the save round trip, the UEFA guard)
need an exe built WITH the NT data: with pieces (2) / (3) - the squads of the 68 appended NTs are not built yet."""
# TODO (piece 2, MC 15/11): the RUNTIME tests of §11 are NOT here - 2 (SetLeagueNumbers' league byte), 3 (no table write past 2409),
# 4 (bt_save / bt_load round trip) and 5 (the UEFA guard) come with piece (2) on a fixture-world build: 4/4 below is not tests 1-6.
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, TOOLS)
import bigtables  # noqa: E402
import ntfixture  # noqa: E402


def _pack(**kw):
    d = tempfile.mkdtemp(prefix='ntfx')
    return ntfixture.make(os.path.join(d, 'nt'), **kw)


def test_nt_bases():
    pk = _pack()
    nt = bigtables.nt_files([pk])
    assert [b for _, b, _ in nt] == [2409, 2464, 2517, 2527, 2562, 2609], nt
    assert [c for _, _, c in nt] == [55, 53, 10, 35, 47, 11], nt
    assert all(nt[i][1] + nt[i][2] == nt[i + 1][1] for i in range(5)), nt            # base + count = the next file's base
    g = [b + k for _, b, c in nt for k in range(c)]
    assert g == list(range(2409, 2620)) and len(set(g)) == 211, (g[0], g[-1], len(g))
    assert bigtables.limit_all([pk]) == 2620 and bigtables.LIMIT_CLUBS == 2409 and bigtables.LIMIT == 2409
    assert [pk.as_file[f] for f, _, _ in nt] == [80, 81, 82, 83, 84, 85]              # the files stand for the game's 80..85


def test_nt_dormant():
    assert bigtables.limit_all([]) == bigtables.LIMIT_CLUBS == 2409 and bigtables.nt_files([]) == []
    import mkseason
    old = mkseason.NationalPack(os.path.join(TOOLS, '..', 'packs', 'europe-1984-85', 'national'))   # the 3.1 national pack: bases 0
    assert bigtables.nt_files([old]) == [] and bigtables.limit_all([old]) == 2409


def _refused(frag, **kw):
    try:
        _pack(**kw)
    except Exception as e:
        assert frag in str(e), (frag, str(e)[:200])
        return
    raise AssertionError(f'accepted, expected a refusal with {frag!r}: {kw}')


def test_nt_refusals():
    _refused('at most 255 ordinals', counts=(256, 53, 10, 35, 47, 11), bases=(2409, 2665, 2718, 2728, 2763, 2810))
    _refused('contiguous', bases=(2409, 2465, 2518, 2528, 2563, 2610))               # a hole after the first file
    _refused('contiguous', bases=(2409, 2464, 2517, 2527, 2562, 2600))               # overlap at the last
    _refused('4096', bases=(4000, 4055, 4108, 4118, 4153, 4200))                     # globals past the per-global arrays
    import json
    d = tempfile.mkdtemp(prefix='ntfx')
    ntfixture.make(os.path.join(d, 'nt'))
    f = os.path.join(d, 'nt', 'pack.json')
    m = json.load(open(f))
    m['files'].pop('nat85')
    m['squads'][0]['files'] = list(m['files'])
    json.dump(m, open(f, 'w'))
    import mkseason
    try:
        mkseason.NationalPack(os.path.join(d, 'nt'))
    except Exception as e:
        assert '80..85' in str(e) or 'files must stand' in str(e), str(e)[:200]
    else:
        raise AssertionError('a national pack of five files accepted')


def test_nt_split_users():
    src = lambda n: open(os.path.join(TOOLS, n), encoding='utf-8').read()
    bare = re.compile(r'bigtables\.LIMIT\b(?!_)')
    for n in ('guests.py', 'globnum.py', 'pgroups.py', 'gplay.py', 'uefacoef.py', 'patch.py', 'mkseason.py', 'ctgame.py'):
        code = '\n'.join(l.split('#')[0] for l in src(n).split('\n'))
        assert not bare.search(code), f'{n}: the bare bigtables.LIMIT (use LIMIT_CLUBS: the saved range, or limit_all())'
    assert 'bigtables.LIMIT_CLUBS if bigtables.ON[0]' in src('uefacoef.py') and 'NG == ' in src('uefacoef.py')
    assert 'limit_all() <= 4096' in src('gplay.py') and 'limit_all() <= 4096' in src('ctgame.py')
    assert re.search(r'pg_pend\[4096 / 8\]', src('gplay.c')) and re.search(r'CG_TAB\[4096\]', src('ctgame.c'))
    assert bigtables.LIMIT_ALL_MAX == 4096
