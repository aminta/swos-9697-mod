"""S7 data (Panchina 10/11): World 2026-27's Italy pack over two team files, tools/s7pack.py from the one-file pack
(internal/world2526/world5tm-h2/ita) and the 2026-27 Serie D groups (internal/n7/s7-groups.csv), read by mkseason.

- the shaped pack loads (Pack.shaped) and sreg.shape_of gives 102 = Serie A, B, C (5 x 20), 144 = Serie D 9 x 18, no
  pool rows (MC 11/11); ident order = clubs.csv: the 100, the groups A..I, the 36 stand-ins (off the files);
- TEAM.102: the one-file pack's first 100 records, byte for byte (Serie A, B, C do not move);
- TEAM.144: 162 records, file byte 144, ordinals 0..161, global numbers base + ordinal (a test base until globnum),
  division byte = the group's local one (0..8, struct B: 42-s7ctry); every other byte the club's one-file record (its TEAM.102 row, or its off-file
  pool record for the 6 that join Serie D); an XTRA.102 and an XTRA.144 (the extra players);
- the off-file pool: 36 RS records (the stand-ins in clubs.csv order, each its one-file pool record), on file 144
  (RS5144); newpool41.csv / sreg.new_pool: the 42 4.1 pool records -> their S7 RS index, 255 for the 6;
- refused: a division in two roles,
  stand-ins without an off-file reserve, s7pack over an existing folder."""
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
ROOT = os.path.join(TOOLS, '..')
sys.path.insert(0, TOOLS)
SRC = os.environ.get('S7_SRC') or os.path.join(ROOT, 'internal', 'world2526', 'world5tm-h2', 'ita')
GROUPS = os.environ.get('S7_GROUPS') or os.path.join(ROOT, 'internal', 'n7', 's7-groups.csv')
BASE = None                                     # (--base: from globnum, S7-G; the test checks glob())


def _recs(data):
    from mkseason import TEAM_SIZE as TS
    n = struct.unpack('>H', data[:2])[0]
    return [data[2 + i * TS:2 + (i + 1) * TS] for i in range(n)]


def _strip(r):
    """A record without its place: file, ordinal, global number, division byte."""
    r = bytearray(r)
    r[0:4] = bytes(4)
    r[25] = 0
    return bytes(r)


def test_s7pack():
    import test_globnum                     # (World 2026-27's packs enabled: globnum.split sees the world's files)
    prev = os.environ.get('SEASON_PACKS')
    test_globnum._env()
    try:
        return _test()
    finally:
        if prev is None:
            os.environ.pop('SEASON_PACKS', None)
        else:
            os.environ['SEASON_PACKS'] = prev


def _test():
    import globnum
    import mkseason
    import s7pack
    import sreg
    if not (os.path.isdir(SRC) and os.path.isfile(GROUPS)):
        return True, f'SKIP: no {SRC} / {GROUPS}'
    tmp = tempfile.mkdtemp(prefix='s7pack')
    errs = []
    try:
        out = os.path.join(tmp, 'ita')
        s = s7pack.build(SRC, GROUPS, out, BASE)
        pk = mkseason.Pack(out)
        one = mkseason.Pack(SRC)
        w, files, divs = sreg.shape_of(pk)
        want = [(102, [(d, 20) for d in range(5)], 0), (144, [(d, 18) for d in range(5, 14)], 0)]
        if not pk.shaped or files != want or len(divs) != 298:
            errs.append(f'shape {files} ({len(divs)} clubs)')
        if divs != [d for _, ds, pool in want for d, n in ds for _ in range(n)] + [sreg.OUT] * 36:
            errs.append('ident order: not the 100, the groups in order, the stand-ins')
        t1 = one.team_files()
        t2 = pk.team_files()
        a = _recs(t1[102])
        if _recs(t2[102]) != a[:100]:
            errs.append('TEAM.102: Serie A, B, C records differ from the one-file pack')
        old = {r[5:22].split(b'\0')[0]: r for r in a}            # (the one-file records by name: the pack's names are
        for r in _recs(one.pool_data):                           #  unique, clubs.csv checks)
            old.setdefault(r[5:22].split(b'\0')[0], r)
        b = _recs(t2[144])
        g144 = [struct.unpack('>H', r[2:4])[0] for r in b]
        if (pk.files['league_b'][1], g144[0], g144[155], g144[156], g144[161]) != (192, 192, 347, 2283, 2288):
            errs.append(f"144 globals: base {pk.files['league_b'][1]}, rows 0/155/156/161 "
                        f"{[g144[i] for i in (0, 155, 156, 161) if i < len(g144)]} (globnum: 192 / 347 / 2283 / 2288)")
        keys = [k for k, c in pk.clubs.items() if c['file'] == 'league_b']
        if len(b) != 162 or len(keys) != 162:
            errs.append(f'TEAM.144: {len(b)} records')
        for i, (k, r) in enumerate(zip(keys, b)):
            d = pk.division[k]
            want_d = int(pk.clubs[k]['division'])       # (+25: the LOCAL division of struct B, 0..8 - 42-s7ctry's B5)
            if (r[0], r[1], struct.unpack('>H', r[2:4])[0], r[25]) != (144, i, globnum.glob(pk, 144, i),
                                                                     pk.div_key(want_d)[1]) or d != want_d:
                errs.append(f'TEAM.144 {k}: place {(r[0], r[1], struct.unpack(">H", r[2:4])[0], r[25])}')
                break
            o = old.get(r[5:22].split(b'\0')[0])
            if o is None or _strip(o) != _strip(r):
                errs.append(f'TEAM.144 {k}: record differs from its one-file record')
                break
        joined = [k for k in keys if one.clubs[k]['file'] == 'pool']
        if sorted(joined) != sorted(s['join']) or len(joined) != 6:
            errs.append(f'the 6: {joined}')
        # the off-file pool: the stand-ins' records on file 144; newpool: 4.1 pool index -> S7 RS index / 255
        sk = [k for k, c in pk.clubs.items() if c['file'] == 'pool']
        p1 = [k for k, c in one.clubs.items() if c['file'] == 'pool']
        rs = _recs(pk.pool_data)
        r1 = dict(zip(p1, _recs(one.pool_data)))
        if len(sk) != 36 or len(rs) != 36 or any(_strip(r) != _strip(r1[k]) for k, r in zip(sk, rs)):
            errs.append(f'the RS pool: {len(rs)} records, not the stand-ins\' one-file records')
        if pk.pool_file != 144 or one.pool_file != 102:     # (rs_files: RS<world><pool_file>.DAT = RS5144 / RS5102)
            errs.append(f'the pool\'s file {pk.pool_file} (want 144)')
        npl = sreg.new_pool(pk)
        if len(npl) != 42 or [p1[i] for i in range(42) if npl[i] == 255] != [k for k in p1 if k in s['join']] or \
                [npl[p1.index(k)] for k in sk] != list(range(36)):
            errs.append(f'newpool: {list(npl)}')
        if 144 not in pk.xtra or 102 not in pk.xtra:
            errs.append(f'XTRA files {sorted(pk.xtra)}')

        # old_ord: each ident's 4.1 identity (a 102 row, or 256 + its off-file pool index), by key
        oo = sreg.old_ord(pk)
        rows1 = [k for k, c in one.clubs.items() if c['file'] == 'league']
        pool1 = [k for k, c in one.clubs.items() if c['file'] == 'pool']
        want_oo = [rows1.index(k) if k in rows1 else 256 + pool1.index(k) for k in pk.clubs]
        if oo != want_oo or sorted(oo) != list(range(298)) or oo[:100] != list(range(100)):
            errs.append('old_ord: not the one-file rows / pool indices by key')
        if [oo[list(pk.clubs).index(k)] >= 256 for k in s['join']] != [True] * 6:
            errs.append('old_ord: the 6 not from the pool')
        if len(sreg.old_ord_bytes(oo)) != 596:
            errs.append('old_ord bytes')
        dup = os.path.join(tmp, 'dup')
        shutil.copytree(out, dup)
        t = open(os.path.join(dup, 'import41.csv'), encoding='utf-8').read().splitlines()
        t[2] = t[2].split(',')[0] + ',' + t[1].split(',')[1]
        open(os.path.join(dup, 'import41.csv'), 'w', encoding='utf-8').write('\n'.join(t) + '\n')
        try:
            sreg.old_ord(mkseason.Pack(dup))
            errs.append('old_ord: an identity twice accepted')
        except AssertionError as e:
            if 'twice' not in str(e):
                errs.append(f'old_ord dup: {e}')

        # (refused: bad shapes. mkseason.patch() with a shaped pack is no longer refused: 42-s7ctry's struct B is the
        #  exe side - the guard dropped at the 42-n7reg -> 42-int merge, Shaved 13/11)
        def bad(tag, edit, want):
            d = os.path.join(tmp, tag.replace(' ', '_'))
            shutil.copytree(out, d)
            m = json.load(open(os.path.join(d, 'pack.json'), encoding='utf-8'))
            edit(m, d)
            json.dump(m, open(os.path.join(d, 'pack.json'), 'w', encoding='utf-8'))
            try:
                mkseason.Pack(d)
                errs.append(f'{tag}: accepted')
            except mkseason.PackError as e:
                if want not in str(e):
                    errs.append(f'{tag}: {e}')

        def lg(m):
            return next(c for c in m['competitions'] if c['key'] == m['season']['league'])

        def twice(m, d):
            m['files']['league']['divisions'] = [0, 1, 2, 3, 4, 5]
        bad('division in two roles', twice, 'once')

        def offf(m, d):
            lg(m)['reserve'].pop('off_file')
        bad('stand-ins without an off-file reserve', offf, 'off the team files')
        try:
            s7pack.build(SRC, GROUPS, out, BASE)
            errs.append('s7pack over an existing folder: accepted')
        except FileExistsError:
            pass
        try:
            s7pack.build(SRC, GROUPS, os.path.join(tmp, 'b160'), 160)
            errs.append('--base 160 (not globnum\'s 192): accepted')
        except SystemExit:
            if os.path.exists(os.path.join(tmp, 'b160')):
                errs.append('--base refused: its folder left')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return not errs, '; '.join(errs) or (f"S7 Italy: 102 = 100 (as the one-file pack), 144 = 9 x 18, 36 stand-ins off-file (RS5144, newpool), "
                                         f"144 globals from globnum (192.., rows 155 / 156 / 161 = 347 / 2283 / 2288), "
                                         f"the 6 = {' '.join(s['join'])}; refused: bad shapes, a --base not globnum's")


REF = os.environ.get('S7_DECIDERS') or os.path.join(ROOT, 'internal', 'world2526', 'world5tm-s1rank-int3', 'ita')


def test_s7pack_deciders():
    """Panchina 13/11 (backlog row 76): s7pack --deciders REF adds Serie D girone A's promotion decider (dA_title, before
    dA_playoff) and relegation tie (dA_reltie, before dA_playout) from the data session's dataset (world5tm-s1rank-int3)
    and takes girone A's promoted / relegated from it (0 / 1: the deciders give the other place), the release world's
    h2 lacking them; every other ko_playoffs entry and division as in the source; the pack still loads (Pack, shape);
    without --deciders the pack is as before (no dA_title / dA_reltie, girone A 1 / 2)."""
    import test_globnum
    prev = os.environ.get('SEASON_PACKS')
    test_globnum._env()
    try:
        import mkseason
        import s7pack
        import sreg
        if not (os.path.isdir(SRC) and os.path.isfile(GROUPS) and os.path.isdir(REF)):
            return True, f'SKIP: no {SRC} / {GROUPS} / {REF}'
        tmp = tempfile.mkdtemp(prefix='s7pack')
        errs = []
        try:
            def league(o):
                m = json.load(open(os.path.join(o, 'pack.json')))
                return next(c for c in m['competitions'] if c['key'] == m['season']['league'])
            src = league(SRC)
            s7pack.build(SRC, GROUPS, os.path.join(tmp, 'plain'), BASE)
            s7pack.build(SRC, GROUPS, os.path.join(tmp, 'dec'), BASE, deciders=REF)
            p0, p1 = league(os.path.join(tmp, 'plain')), league(os.path.join(tmp, 'dec'))
            k0, k1 = [k['key'] for k in p0['ko_playoffs']], [k['key'] for k in p1['ko_playoffs']]
            if 'dA_title' in k0 or 'dA_reltie' in k0 or p0['divisions'][5]['promoted'] != src['divisions'][5]['promoted']:
                errs.append('without --deciders the pack changed')
            want = [k for k in k1 if k not in ('dA_title', 'dA_reltie')]
            if want != k0 or k1.index('dA_title') + 1 != k1.index('dA_playoff') or k1.index('dA_reltie') + 1 != k1.index('dA_playout'):
                errs.append(f'ko_playoffs order {k1}')
            d5 = p1['divisions'][5]
            if (d5['promoted'], d5['relegated']) != (0, 1):
                errs.append(f'girone A promoted / relegated {d5["promoted"]} / {d5["relegated"]} (want 0 / 1)')
            if [d for i, d in enumerate(p1['divisions']) if i != 5] != [d for i, d in enumerate(p0['divisions']) if i != 5]:
                errs.append('another division changed')
            pk = mkseason.Pack(os.path.join(tmp, 'dec'))
            if not pk.shaped or len(sreg.shape_of(pk)[2]) != 298:
                errs.append('the pack with the deciders does not load shaped')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return not errs, '; '.join(errs) or 'dA_title / dA_reltie in place (before dA_playoff / dA_playout), girone A 0 / 1, the rest unchanged, loads shaped; without --deciders as before'
    finally:
        if prev is None:
            os.environ.pop('SEASON_PACKS', None)
        else:
            os.environ['SEASON_PACKS'] = prev
