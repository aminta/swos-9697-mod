"""4.2 (MC 15/11): a 1996-97 SEASON after a world career runs in world 0 (careerworld sw_pick / sw_init / sw_load).

test_seaw0_sites (no build): SeasonMenu's `call InitNewSeason` and LoadOldCompetitionMenu's .SEA load call are found
once in all 8 exes (CD + GOG, 4 languages): the sites the tramps branch on.
test_seaw0_collisions: the world draws (mkseason.world_draws, historic DRAWS behind a [1,0,w] marker) and the world
byes (bye_cups, lib97 BYE_TAB world != 0) that share a cup id with a 1996-97 national cup - the cups a stale world
byte would have changed in a SEASON (Coppa Italia 94h: World 2026-27 fixed pairs for rounds of 32..2). Listed; the
test asserts the list is not empty (so the harness scenarios season_world0 / season_world0_8485 guard a real case).
test_seaw0_gates: those draws / byes apply only when WORLDB (someLeaguesTable[1845]) = their world: historic's DRAW_W
and lib97's BW compare with WORLDB; sw_init clears the live table when the byte is set, so a SEASON's InitNewSeason
(where both are read) sees 0."""
import os
import struct
import sys

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)


def _exes():
    o = os.path.join(ROOT, 'orig')
    return [os.path.join(o, d, f'{x}.EXE') for d in ('', 'gog') for x in ('ITALIAN', 'ENGLISH', 'FRENCH', 'GERMAN')]


def test_seaw0_sites():
    import careerworld
    import lepatch
    got = []
    for f in _exes():
        if not os.path.exists(f):
            return True, f'SKIP: {f} missing'
        p = lepatch.LEPatch(f)
        sea = careerworld.sea_sites(p, careerworld.sites(p)['regs'])
        d1 = p.le.obj_bytes(1)
        for k in ('init', 'load'):
            assert d1[sea[k]] == 0xE8, (f, k, hex(sea[k]))
        got.append(f"{os.path.relpath(f, ROOT)} {sea['init']:#x}/{sea['load']:#x}")
    return True, '; '.join(got)


def _cups96():
    """{cup id: [country]} - the 1996-97 national cups (competitionsTable: the entries after the -2 marker)."""
    import countries
    import lepatch
    p = lepatch.LEPatch(os.path.join(ROOT, 'orig', 'ITALIAN.EXE'))
    d = p.le.obj_bytes(2)
    countries.tables(p)

    def tgt(off):
        try:
            return p.target(2, off)
        except AssertionError:
            return None
    cups = {}
    for c in range(256):
        t = tgt(countries.COMP[0] + 4 * c)
        if not t:
            continue
        seen = False
        for k in range(12):
            v = struct.unpack_from('<i', d, t[1] + 4 * k)[0]
            if v == -1:
                break
            if v == -2:
                seen = True
                continue
            x = tgt(t[1] + 4 * k)
            if seen and x:
                cups.setdefault(d[x[1]], []).append(c)
    return cups


W5 = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'world2526', 'world5tm-h3p')


def _release_packs():
    """SEASON_PACKS as the release recipe sets it (bit_it.sh / buildrel: the world packs of world5tm-h3p), unless set."""
    if os.environ.get('SEASON_PACKS') or not os.path.exists(W5 + '.txt'):
        return
    eu = sorted(os.path.join(ROOT, 'packs', 'europe-1984-85', d) for d in os.listdir(os.path.join(ROOT, 'packs', 'europe-1984-85'))
                if os.path.isdir(os.path.join(ROOT, 'packs', 'europe-1984-85', d)))
    w = [W5 + '/' + ln.split()[0].lower() for ln in open(W5 + '.txt') if ' file ' in ln]
    os.environ['SEASON_PACKS'] = ','.join(['ddr-1988-89', 'italia-1947-48', 'world-cup-1934'] + eu + w)


def test_seaw0_collisions():
    _release_packs()
    if not os.environ.get('SEASON_PACKS'):
        return True, f'SKIP: no SEASON_PACKS and no {W5}.txt (the world packs)'
    import mkseason
    cups = _cups96()
    draws = []
    for w, ds in mkseason.world_draws().items():
        for e in ds:
            if e[0] in cups:
                draws.append((w, e[0], len(e[1])))
    byes = sorted({(w, i, n) for i, w, n, _ in mkseason.bye_cups() if w and i in cups})
    assert draws, 'no world draw shares a 1996-97 cup id'
    sz = {}
    for w, i, n in draws:
        sz.setdefault((w, i), []).append(n)
    return True, (f'{len(cups)} 1996-97 national cups; world draws on their ids: '
                  + ', '.join(f'w{w} {i:#x} rounds {sorted(set(v), reverse=True)}' for (w, i), v in sorted(sz.items()))
                  + f'; world byes on their ids: {[(w, hex(i), n) for w, i, n in byes]}')


def test_seaw0_gates():
    import careerworld
    import historic
    import lib97
    src = {m.__name__: open(m.__file__).read() for m in (historic, lib97, careerworld)}
    h = src['historic']
    i = h.index('cmp byte [DRAW_W], 0')
    assert 'cmp al, [WORLDB]' in h[i:i + 200], 'historic: DRAW_W not compared with WORLDB'
    lb = src['lib97']
    i = lb.index('%if BW_ON\n    cmp byte [esi + 1], 0')
    assert 'mov al, [WORLDB]' in lb[i:i + 200] and 'cmp [esi + 1], al' in lb[i:i + 250], 'lib97: BYE world not vs WORLDB'
    c = src['careerworld']
    for k in ('sw_pick:', 'sw_init:', 'sw_load:', "p.branch(1, sea[k], 0xE8, 1, labels[stub])"):
        assert k in c, k
    i = c.index('sw_init:')
    assert 'cmp byte [SLTW], 0' in c[i:i + 400] and 'mov edi, SLTB' in c[i:i + 900], 'sw_init: no table clear'
    return True, 'historic DRAW_W / lib97 BW gated on WORLDB; sw_pick / sw_init / sw_load branched'
