"""S7 data (Panchina 10/11): World 2026-27's Italy pack over two team files, tools/s7pack.py from the one-file pack
(internal/world2526/world5tm-h2/ita) and the 2026-27 Serie D groups (internal/n7/s7-groups.csv), read by mkseason.

- the shaped pack loads (Pack.shaped) and sreg.shape_of gives 102 = Serie A, B, C (5 x 20), 144 = Serie D 9 x 18 +
  36 pool rows; ident order = clubs.csv: the 100, the groups A..I, the pool rows;
- TEAM.102: the one-file pack's first 100 records, byte for byte (Serie A, B, C do not move);
- TEAM.144: 198 records, file byte 144, ordinals 0..197, global numbers base + ordinal, division byte = the group's
  (5..13), 14 (= nd, the reserve's) for the pool rows; every other byte the club's one-file record (its TEAM.102 row,
  or its off-file pool record for the 6 that join Serie D); an XTRA.102 and an XTRA.144 (the extra players);
- refused: mkseason.patch() with a shaped pack enabled (no exe side before MC's S7 glue), a division in two roles,
  an off-file reserve, a club off the team files, s7pack over an existing folder."""
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
BASE = 160                                      # (a test base: MC's S7 glue fixes file 144's, n7-s7-clubmap §7.3)


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
        want = [(102, [(d, 20) for d in range(5)], 0), (144, [(d, 18) for d in range(5, 14)], 36)]
        if not pk.shaped or files != want or len(divs) != 298:
            errs.append(f'shape {files} ({len(divs)} clubs)')
        if divs != [d for _, ds, pool in want for d, n in ds for _ in range(n)] + [sreg.POOL] * 36:
            errs.append('ident order: not the 100, the groups in order, the pool rows')
        t1 = one.team_files()
        t2 = pk.team_files()
        a = _recs(t1[102])
        if _recs(t2[102]) != a[:100]:
            errs.append('TEAM.102: Serie A, B, C records differ from the one-file pack')
        old = {r[5:22].split(b'\0')[0]: r for r in a}            # (the one-file records by name: the pack's names are
        for r in _recs(one.pool_data):                           #  unique, clubs.csv checks)
            old.setdefault(r[5:22].split(b'\0')[0], r)
        b = _recs(t2[144])
        keys = [k for k, c in pk.clubs.items() if c['file'] == 'league_b']
        if len(b) != 198 or len(keys) != 198:
            errs.append(f'TEAM.144: {len(b)} records')
        for i, (k, r) in enumerate(zip(keys, b)):
            d = pk.division[k]
            want_d = int(pk.clubs[k]['division']) if pk.clubs[k]['division'] != 'pool' else 14
            if (r[0], r[1], struct.unpack('>H', r[2:4])[0], r[25]) != (144, i, BASE + i, want_d) or d != want_d:
                errs.append(f'TEAM.144 {k}: place {(r[0], r[1], struct.unpack(">H", r[2:4])[0], r[25])}')
                break
            o = old.get(r[5:22].split(b'\0')[0])
            if o is None or _strip(o) != _strip(r):
                errs.append(f'TEAM.144 {k}: record differs from its one-file record')
                break
        joined = [k for k in keys[:162] if one.clubs[k]['file'] == 'pool']
        if sorted(joined) != sorted(s['join']) or len(joined) != 6:
            errs.append(f'the 6: {joined}')
        if 144 not in pk.xtra or 102 not in pk.xtra:
            errs.append(f'XTRA files {sorted(pk.xtra)}')

        # refused: the exe side (patch) and bad shapes
        keep = getattr(mkseason.packs, 'cache', None)
        mkseason.packs.cache = [pk]
        try:
            mkseason.patch(None, 'it', None, None)
            errs.append('patch(): a shaped pack accepted')
        except mkseason.PackError as e:
            if 'two team files' not in str(e):
                errs.append(f'patch(): {e}')
        finally:
            if keep is None:
                del mkseason.packs.cache
            else:
                mkseason.packs.cache = keep

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
            lg(m)['reserve']['off_file'] = True
        bad('off-file reserve', offf, "not 'off_file'")

        def offc(m, d):
            m['files']['pool'] = {'file': 253, 'base': 0}
            p = os.path.join(d, 'clubs.csv')
            t = open(p, encoding='utf-8').read().splitlines()
            t[-1] = t[-1].replace(',league_b,pool,', ',pool,,')
            open(p, 'w', encoding='utf-8').write('\n'.join(t) + '\n')
            lg(m)['divisions'][13]['teams'] = 18
            m['files']['league_b']['pool_rows'] = 35
        bad('club off the files', offc, 'off the team files')
        try:
            s7pack.build(SRC, GROUPS, out, BASE)
            errs.append('s7pack over an existing folder: accepted')
        except FileExistsError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return not errs, '; '.join(errs) or (f"S7 Italy: 102 = 100 (as the one-file pack), 144 = 9 x 18 + 36 pool rows, "
                                         f"the 6 = {' '.join(s['join'])}; refused: patch(), bad shapes")
