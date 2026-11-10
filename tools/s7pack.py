#!/usr/bin/env python3
"""S7: World 2026-27's Italy pack over two team files (n7-p4.md §1), from the one-file pack + the Serie D groups.

    python3 tools/s7pack.py SRC_PACK GROUPS_CSV OUT_DIR --base N [--file 144]

SRC_PACK   the one-file Italy pack (e.g. internal/world2526/world5tm-h2/ita): TEAM.102 = Serie A, B, C (100) + Serie D
           (156, 6 groups of 17 + 3 of 18), the 42 reserve clubs off the files (file 'pool', RI swaps).
GROUPS_CSV internal/n7/s7-groups.csv: the 162 Serie D clubs of 2026-27, 9 x 18 (key, group, division, ...), the 6
           missing from the one-file pack among them (now 'pool ...').
OUT_DIR    the shaped pack (a new folder; refused if it exists): the same files, with
           - pack.json 'files': league {102, its base, divisions 0-4}, league_b {FILE, --base, divisions 5-13,
             pool_rows = the reserve clubs left}; no 'pool' role (every club on a team file's rows);
           - the league's Serie D divisions 'teams' = their groups' sizes, its reserve = the pool rows (no 'off_file':
             the registry replaces RI's swaps), 'first' kept in its order without the 6;
           - squads 'files' with league_b for 'pool';
           - clubs.csv in ident order (append-only from the first S7 release, n7-p4.md §1): Serie A, B, C as in the
             source, then the groups A..I in s7-groups.csv order, then the reserve rows in the source order;
           - import41.csv (key, ident41): each club's place in the one-file layout, in gplay's RI identity space (a
             TEAM.102 row, or 256 + its off-file pool index) - the old-save import's table (sreg.old_ord).
--base     file 144's first global number (n7-s7-clubmap §7.3: after XW's six; MC's S7 glue fixes it). Required.

Data only: mkseason builds this pack's TEAM.102 / TEAM.144 (Pack.team_files()), but patch() refuses it until MC's S7
glue gives the exe a league over two files (data after engine). Not for SEASON_PACKS before then.
"""
import argparse
import csv
import io
import json
import os
import shutil
import sys

RIS = 256                                       # (gplay.c RIS: RI's identities, a row or RIS + pool)
SERIE_D = list(range(5, 14))                    # the league's divisions 5..13 = Serie D groups A..I


def _rows(path):
    with open(path, encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def build(src, groups, out, base, fileno=144):
    """Write the shaped pack to out; returns its summary (clubs per role, the 6 that join, pool rows)."""
    m = json.load(open(os.path.join(src, 'pack.json'), encoding='utf-8'))
    cols, clubs = _rows(os.path.join(src, 'clubs.csv'))
    _, grp = _rows(groups)
    by = {c['key']: c for c in clubs}
    fs = m['files']
    assert set(fs) == {'league', 'pool'} and not any('divisions' in v for v in fs.values()), \
        ('s7pack: the source is the one-file pack (files league + pool, no divisions)', fs)
    lg = next(c for c in m['competitions'] if c['key'] == m['season']['league'])
    divs, rs = lg['divisions'], lg['reserve']
    assert len(divs) == 14 and rs.get('off_file'), 's7pack: the source league: 14 divisions, an off-file reserve'
    keys = [g['key'] for g in grp]
    assert len(keys) == len(set(keys)) and all(k in by for k in keys), \
        ('s7pack: groups: unknown or repeated keys', [k for k in keys if k not in by])
    assert {int(g['division']) for g in grp} == set(SERIE_D), 's7pack: groups: divisions 5..13'
    top = [c for c in clubs if c['file'] == 'league' and int(c['division']) < 5]
    sd_old = {c['key'] for c in clubs if c['file'] == 'league' and int(c['division']) >= 5}
    assert sd_old <= set(keys), ('s7pack: Serie D clubs of the source missing from the groups', sorted(sd_old - set(keys)))
    join = [k for k in keys if k not in sd_old]
    assert all(by[k]['file'] == 'pool' for k in join), ('s7pack: a joining club not from the reserve', join)
    for g in grp:
        assert by[g['key']]['name'] == g['name'], ('s7pack: name differs from the pack', g['key'], g['name'])
    sd = []
    for d in SERIE_D:                           # groups in division order, clubs in s7-groups.csv order
        for g in grp:
            if int(g['division']) == d:
                sd.append(dict(by[g['key']], file='league_b', division=str(d)))
    left = [dict(c, file='league_b', division='pool') for c in clubs if c['file'] == 'pool' and c['key'] not in join]
    rest = [c for c in clubs if c['file'] not in ('league', 'pool')]
    assert not rest, ('s7pack: clubs of other files', [c['key'] for c in rest][:5])
    new = top + sd + left
    assert len(new) == len(clubs), 's7pack: a club lost'
    size = {d: sum(1 for c in sd if c['division'] == str(d)) for d in SERIE_D}

    fs2 = {'league': dict(fs['league'], divisions=list(range(5))),
           'league_b': {'file': fileno, 'base': base, 'divisions': SERIE_D, 'pool_rows': len(left)}}
    m2 = dict(m, files=fs2)
    for sq in m2['squads']:
        sq['files'] = ['league_b' if f == 'pool' else f for f in sq['files']]
    lg2 = next(c for c in m2['competitions'] if c is lg)
    for d in SERIE_D:
        lg2['divisions'][d]['teams'] = size[d]
    pool = [c['key'] for c in left]
    lg2['reserve'] = {k: v for k, v in rs.items() if k != 'off_file'}
    lg2['reserve']['pool'] = [k for k in rs['pool'] if k in pool]
    lg2['reserve']['first'] = [k for k in rs.get('first', []) if k in pool]
    assert sorted(lg2['reserve']['pool']) == sorted(pool), 's7pack: reserve pool != the pool rows'

    os.makedirs(out)                            # (refused if it exists: never over another folder)
    for f in sorted(os.listdir(src)):
        if f not in ('pack.json', 'clubs.csv') and os.path.isfile(os.path.join(src, f)):
            shutil.copy2(os.path.join(src, f), os.path.join(out, f))
    with open(os.path.join(out, 'pack.json'), 'w', encoding='utf-8') as f:
        json.dump(m2, f, ensure_ascii=False, indent=1)
        f.write('\n')
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n')
    w.writeheader()
    w.writerows(new)
    with open(os.path.join(out, 'clubs.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write(buf.getvalue())
    rid, nr, npool = {}, 0, 0                   # import41.csv: every club's place in the one-file layout (4.1's), in
    for c in clubs:                             # gplay's RI identity space: a TEAM.102 row 0..255, or RIS (256) + its
        if c['file'] == 'league':               # index among the off-file pool's records (clubs.csv order) - what
            rid[c['key']], nr = nr, nr + 1      # RI_STATE.maps holds (+1); sreg.old_ord's input
        else:
            rid[c['key']], npool = RIS + npool, npool + 1
    assert nr <= RIS, 's7pack: the one-file layout past 256 rows'
    with open(os.path.join(out, 'import41.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('key,ident41\n' + ''.join(f"{c['key']},{rid[c['key']]}\n" for c in new))
    return {'league': len(top), 'league_b': len(sd), 'pool_rows': len(left), 'join': join, 'sizes': size}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('groups')
    ap.add_argument('out')
    ap.add_argument('--base', type=int, required=True)
    ap.add_argument('--file', type=int, default=144)
    a = ap.parse_args(argv)
    s = build(a.src, a.groups, a.out, a.base, a.file)
    print(f"s7pack: {a.out}: league {s['league']} + league_b {s['league_b']} (groups {sorted(set(s['sizes'].values()))}) "
          f"+ {s['pool_rows']} pool rows; joining: {' '.join(s['join'])}")


if __name__ == '__main__':
    main(sys.argv[1:])
