"""S7-D (MC 11/11, mc-s7-glue.md §1): the division sites through Pack.div_file / div_key - World 2026-27's Italy (the
release recipe's world data, HT_GLOB_WORLD, default world5tm-s1rank-int3) shaped in memory as s7pack.py writes it:
'files' league {102, divisions 0-4}, league_b {144, divisions 5-13}; option (a): one league struct per file, local
divisions (file 144's struct: LEAGUE_AT[(5, 144)] faked here until MC's §3 exe glue).
- dormant: div_file(d) = (102, 92), div_key(d) = (102, d) for every division;
- shaped: div_file / div_key; dplay = file 102; lrank = two tables (102: local 0..4, 144: local 0..8 = Serie D A..I);
  ko spec = two specs, 144's = compile_spec of the Serie D entries renumbered by hand; split key (5, 144, local);
  lrank.table with the fake 144 struct;
- refusals, one per site: div_file (a division in two roles / out of range), dplay (Serie C group on file 144), lrank
  (no struct for 144), ko spec (entrants over both structs),
  split (a division in two structs' 'divisions'); ko spec: entrants over both structs refused, an absent destination in struct 144 refused (a placement's
  absent winner_div = its own division, explicit: gplay.c never moves a kind 3 - ok = 0), a destination over
  them = gplay.EXTERNAL + Pack.ko_external (the 4 Italian entries: cA/cB/cC play-outs -> (144, 0), dA_title ->
  (102, 2))."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))


CROSS = ('cA_playout', 'cB_playout', 'cC_playout')     # (Serie C play-outs whose losers go to Serie D: EXTERNAL)


def _key(lg, it, f, i):
    """The ko_playoffs key of struct f's spec entry i (the entries in pack order, by struct)."""
    return [po['key'] for po in lg['ko_playoffs'] if it.po_local(po)[0] == f][i]


def _drop_tools():
    """Drop the tools/ modules already imported (mkseason reads SEASON_PACKS at import and caches its packs: a test run
    before this one under another SEASON_PACKS left them - the full suite's ko_external without dA_title, Integratore
    12/11; the same class as test_ctcountry's 6efdcf4)."""
    tools = os.path.realpath(os.path.dirname(os.path.dirname(HERE)))
    for k, m in list(sys.modules.items()):
        f = getattr(m, '__file__', None) or ''
        if os.path.dirname(os.path.realpath(f)) == tools:
            del sys.modules[k]


def test_s7div():
    import test_globnum
    prev = os.environ.get('SEASON_PACKS')
    _drop_tools()                               # (fresh imports under test_globnum's SEASON_PACKS, before and after)
    test_globnum._env()
    try:
        return _test()
    finally:
        _drop_tools()
        if prev is None:
            os.environ.pop('SEASON_PACKS', None)
        else:
            os.environ['SEASON_PACKS'] = prev


def _shape(it, a=range(5), b=range(5, 14)):
    it.meta['files'] = {'league': dict(it.meta['files']['league'], divisions=list(a)),
                        'league_b': {'file': 144, 'base': 192, 'divisions': list(b)},
                        'pool': it.meta['files']['pool']}
    it.files['league_b'] = (144, 192)
    it.count['league'], it.count['league_b'] = 100, 162


def _refused(f):
    import mkseason
    try:
        f()
    except mkseason.PackError as e:
        return str(e)
    return None


def _test():
    import globnum
    import gplay
    import lrank
    import mkseason
    out, bad = [], []
    it = next(pk for pk in mkseason.packs() if pk.world == 5 and pk.files.get('league', (0,))[0] == 102)
    if 'dA_title' not in [po['key'] for po in it.league.get('ko_playoffs') or []]:
        return True, ('SKIP: the data has no dA_title (a pre-10/11 snapshot, e.g. world5tm-h2): '
                      f"HT_GLOB_WORLD={os.environ.get('HT_GLOB_WORLD') or 'default'}")
    nd = len(it.divisions())
    if nd != 14:
        return False, f'dormant Italy: {nd} divisions'
    d0 = [it.div_file(d) for d in range(nd)], [it.div_key(d) for d in range(nd)]
    if d0 != ([(102, 92)] * nd, [(102, d) for d in range(nd)]):
        bad.append(f'dormant div_file / div_key {d0}')
    lr0, gp0, dp0 = it.lrank(), it.gplay(), it.dplay()
    if [t[1] for t in lr0] != [102] or [t[1] for t in gp0] != [102] or dp0[5] != 102:
        bad.append('dormant tables not one file-102 entry each')
    saved = copy.deepcopy(it.meta), dict(it.files), dict(it.count)
    lat = dict(mkseason.LEAGUE_AT)
    globnum._split_cached.cache_clear()
    pk_prev = mkseason.packs
    try:
        _shape(it)
        globnum._split_cached.cache_clear()
        df = [it.div_file(d) for d in range(nd)]
        dk = [it.div_key(d) for d in range(nd)]
        if df != [(102, 92)] * 5 + [(144, 192)] * 9 or dk != [(102, d) for d in range(5)] + [(144, d) for d in range(9)]:
            bad.append(f'shaped div_file {df} div_key {dk}')
        if it.dplay()[5] != 102:
            bad.append(f'dplay {it.dplay()}')
        lr = it.lrank()
        got = {f: [e[0] for e in es] for _, f, es in lr}
        if got != {102: list(range(5)), 144: list(range(9))} or [e[3] for e in lr[1][2]] != \
                [it.divisions()[d]['teams'] for d in range(5, 14)]:
            bad.append(f'lrank {got}')
        mkseason.LEAGUE_AT.clear()
        mkseason.LEAGUE_AT[(5, 102)] = 0x1000
        r = _refused(lambda: lrank.table(None, lr))
        bad.append('lrank: no struct for 144 not refused') if not r else out.append(f'lrank refused ({r})')
        mkseason.LEAGUE_AT[(5, 144)] = 0x2000           # (the fake second struct)
        tab, ptrs = lrank.table(None, lr)
        if len(ptrs) != 14 or tab[24 * 5 + 5] != 0 or tab[24 * 13 + 5] != 8:
            bad.append('lrank.table: local divisions')
        # ko spec (MC 11/11): the entrants decide the struct; a destination in the other struct = gplay.EXTERNAL + the
        # side list (the 4 Italian entries: Serie C play-outs relegating into Serie D, Serie D A's promotion decider)
        lg = it.league
        gp = it.gplay()
        ext = {f: [(_key(lg, it, f, i), o, t) for i, o, t in es] for f, es in it.ko_external.items()}
        want = {102: [('cA_playout', 'loser', (144, 0)), ('cB_playout', 'loser', (144, 0)),
                      ('cC_playout', 'loser', (144, 0))], 144: [('dA_title', 'winner', (102, 2))]}
        if ext != want:
            bad.append(f'ko_external {ext}')
        sd = [po for po in lg['ko_playoffs'] if any(isinstance(e, list) and e[0] >= 5 for e in po['entrants'])]
        hand = [dict(po, entrants=[[e[0] - 5, e[1]] for e in po['entrants']],
                     **({'winner_div': gplay.EXTERNAL} if po['key'] == 'dA_title' else
                        {'winner_div': po['entrants'][0][0] - 5} if po['kind'] == 'placement' and 'winner_div' not in po
                        else {})) for po in sd]           # (placement: no move, explicit in struct 144)
        top = [po for po in lg['ko_playoffs'] if po not in sd]
        hand_a = [dict(po, **({'loser_div': gplay.EXTERNAL} if po['key'] in CROSS else {})) for po in top]
        if [t[1] for t in gp] != [102, 144] or gp[1][2] != gplay.compile_spec(hand, 9, lg.get('names')) \
                or gp[0][2] != gplay.compile_spec(hand_a, 5, lg.get('names')):
            bad.append('gplay: per-struct specs')
        out.append(f'ko_external {ext}')
        # refusal: an absent destination in struct 144 (a Serie D play-out without loser_div)
        dpo = next(po for po in lg['ko_playoffs'] if po['key'] == 'dA_playout')
        ld = dpo.pop('loser_div')
        r = _refused(it.gplay)
        dpo['loser_div'] = ld
        bad.append('gplay: absent loser_div in struct 144 not refused') if not r or 'dA_playout' not in r else \
            out.append(f'gplay refused ({r})')
        # refusal: entrants over both structs
        lg['ko_playoffs'].append(dict(lg['ko_playoffs'][0], key='x_span', entrants=[[4, 1], [5, 1]]))
        r = _refused(it.gplay)
        lg['ko_playoffs'].pop()
        bad.append('gplay: entrants over both structs not refused') if not r or 'x_span' not in r else \
            out.append(f'gplay refused ({r})')
        # split: a Serie D group with its own meetings -> key (5, 144, local)
        lg['divisions'][7]['games'] = 2
        mkseason.packs = lambda: [it]
        sp = mkseason.splits()
        if [x[:3] for x in sp] != [(5, 144, 2)]:
            bad.append(f'split keys {[x[:3] for x in sp]}')
        # cupsf: one cup list per league file (Italy's two cups on 102, none on 144); file 144's dt (two runs) refused
        import cupsf
        c102, c144 = cupsf.pack_cups(it, 102), cupsf.pack_cups(it, 144)
        if [c[0] for c in c102[0]] != [130, 131] or c144 != ([], 144):
            bad.append(f'cupsf lists {c102} {c144}')
        try:
            cupsf.dt_bytes(it, 144)
            bad.append('cupsf: file 144 dt not refused')
        except globnum.GlobError as e:
            out.append(f'cupsf refused ({e})')
        cupsf.dt_bytes(it, 102)                         # (file A: one run, no refusal)
        cup = next(c for c in it.comps if c['type'] == 'cup')     # (a cup over both files: refused)
        k5 = it.bracket(cup)['clubs'][0]                         # (one of its clubs as if on file 144)
        w5 = it.where[k5]
        it.where[k5] = (144, 0)
        r = _refused(lambda: cupsf.pack_cups(it, 102))
        it.where[k5] = w5
        bad.append('cupsf: a cup over both files not refused') if not r else out.append(f'cupsf refused ({r})')
        # cupd: Serie D's file; its CD_DT head carries file 144's two global runs (42-n7reg bd8e5bc, GP_CD2 builds:
        # no refusal any more - was S7-G's until Panchina's two-run CD_DT)
        import cupd
        import struct
        par = it.league['parallel']
        if it.div_file(par[-1]['first'])[0] != 144:
            bad.append('cupd: Serie D file')
        runs, cd2 = globnum.runs_of(it, 144), cupd.cd2
        cupd.cd2 = lambda: True                         # (a GP_CD2 build's head; this test's packs set no exe split)
        try:
            h = cupd.head(it, 144, par[-1]['first'], par[-1]['count'])
        finally:
            cupd.cd2 = cd2
        want = bytes((par[-1]['first'], par[-1]['count'])) + struct.pack('<HHH', runs[0][0], *(
            (runs[1][0], runs[0][1]) if len(runs) == 2 else (0xFFFF, 256)))
        if h != want:
            bad.append(f'cupd: CD_DT head {h.hex()} != {want.hex()}')
        # refusals of div_file (every site goes through it) and dplay
        _shape(it, range(6), range(5, 14))
        r = _refused(lambda: it.div_file(5))
        bad.append('div_file: two roles not refused') if not r else out.append(f'div_file refused ({r})')
        r = _refused(lambda: it.div_file(14))
        bad.append('div_file: division 15 not refused') if not r else None
        r = _refused(mkseason.splits)
        bad.append('split: division 6 in two structs not refused') if not r else out.append(f'split refused ({r})')
        _shape(it, [0, 1, 3, 4], [2] + list(range(5, 14)))
        r = _refused(it.dplay)
        bad.append('dplay: Serie C group on 144 not refused') if not r else out.append(f'dplay refused ({r})')
        out.append(f'shaped: lrank {got}, ko specs {[t[1] for t in gp]}, split {[x[:3] for x in sp]}')
    finally:                                            # (one process runs every test: leave the pack as loaded)
        mkseason.packs = pk_prev
        it.meta, it.files, it.count = saved
        it.league = next(c for c in it.meta['competitions'] if c['key'] == it.meta['season']['league'])
        it.comps = it.meta['competitions']
        mkseason.LEAGUE_AT.clear()
        mkseason.LEAGUE_AT.update(lat)
        globnum._split_cached.cache_clear()
    return not bad, '; '.join(bad or out)


if __name__ == '__main__':
    ok, msg = test_s7div()
    print('PASS' if ok else 'FAIL', msg)
    sys.exit(0 if ok else 1)
