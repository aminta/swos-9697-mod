#!/usr/bin/env python3
"""S7: World 2026-27's Italy pack over two team files (n7-p4.md §1), from the one-file pack + the Serie D groups.

    python3 tools/s7pack.py SRC_PACK GROUPS_CSV OUT_DIR [--base N] [--file 144] [--deciders REF_PACK]

SRC_PACK   the one-file Italy pack (e.g. internal/world2526/world5tm-h2/ita): TEAM.102 = Serie A, B, C (100) + Serie D
           (156, 6 groups of 17 + 3 of 18), the 42 reserve clubs off the files (file 'pool', RI swaps).
GROUPS_CSV internal/n7/s7-groups.csv: the 162 Serie D clubs of 2026-27, 9 x 18 (key, group, division, ...), the 6
           missing from the one-file pack among them (now 'pool ...').
OUT_DIR    the shaped pack (a new folder; refused if it exists): the same files, with
           - pack.json 'files': league {102, its base, divisions 0-4}, league_b {FILE, --base, divisions 5-13} (no pool
             rows: MC 11/11, file 144 = the 9 groups), 'pool' kept: the 36 stand-ins stay off-file, as in 4.1 (RI's
             identity swaps, now on FILE);
           - the league's Serie D divisions 'teams' = their groups' sizes, its reserve kept ('off_file'), 'pool' and
             'first' in their order without the 6;
           - clubs.csv in ident order (append-only from the first S7 release, n7-p4.md §1): Serie A, B, C as in the
             source, then the groups A..I in s7-groups.csv order, then the stand-ins in the source order;
           - import41.csv (key, ident41): each club's place in the one-file layout, in gplay's RI identity space (a
             TEAM.102 row, or 256 + its off-file pool index) - the old-save import's table (sreg.old_ord);
           - newpool41.csv (key, pool41, pool): every 4.1 pool record's S7 RS index (the stand-ins' order in
             clubs.csv), 255 for the 6 that join Serie D - sreg_ri_import's newpool (sreg.new_pool).
--base     optional: file 144's run 1 first global number, checked against globnum (S7-G, MC 11/11): pack.json's
           league_b 'base' = globnum.base(pk, FILE), its run 1 (192 in World 2026-27; rows 156..161 in run 2,
           globnum.split); every global of the pack's records comes from globnum.glob. Refused if --base differs.

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


def build(src, groups, out, base=None, fileno=144, deciders=None):
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
    left = [c for c in clubs if c['file'] == 'pool' and c['key'] not in join]     # (the stand-ins: off-file, as 4.1)
    rest = [c for c in clubs if c['file'] not in ('league', 'pool')]
    assert not rest, ('s7pack: clubs of other files', [c['key'] for c in rest][:5])
    new = top + sd + left
    assert len(new) == len(clubs), 's7pack: a club lost'
    size = {d: sum(1 for c in sd if c['division'] == str(d)) for d in SERIE_D}

    fs2 = {'league': dict(fs['league'], divisions=list(range(5))),
           'league_b': {'file': fileno, 'base': 0, 'divisions': SERIE_D}, 'pool': fs['pool']}   # ('base': below)
    geo = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7pack_geo.json'), encoding='utf-8'))
    m2 = dict(m, files=fs2, geo={'note': geo['_note'], 'neighbours': geo['neighbours']})   # (4.2 geography: s7swap.geo_table checks it)
    for sq in m2['squads']:
        if 'league' in sq['files'] and 'league_b' not in sq['files']:
            sq['files'] = sq['files'] + ['league_b']   # (Serie D's squads: now file 144's)
    lg2 = next(c for c in m2['competitions'] if c is lg)
    for d in SERIE_D:
        lg2['divisions'][d]['teams'] = size[d]
    pool = [c['key'] for c in left]
    lg2['reserve'] = dict(rs)
    lg2['reserve']['pool'] = [k for k in rs['pool'] if k in pool]
    lg2['reserve']['first'] = [k for k in rs.get('first', []) if k in pool]
    if deciders:                                # (dA_title / dA_reltie: Serie D girone A's promotion / relegation deciders, in
        ref = json.load(open(os.path.join(deciders, 'pack.json'), encoding='utf-8'))     # the data session's dataset
        rl = next((c for c in ref['competitions'] if c['key'] == ref['season']['league']), None)  # world5tm-s1rank-int3, not in
        assert rl is not None, ('s7pack --deciders: no league competition in', deciders)           # the release world5tm-h2)
        ko = lg2['ko_playoffs']
        have = {k['key'] for k in ko}
        for key, before in (('dA_title', 'dA_playoff'), ('dA_reltie', 'dA_playout')):
            if key in have:
                continue
            e = next((k for k in rl['ko_playoffs'] if k['key'] == key), None)
            assert e is not None, (f"s7pack --deciders: {deciders} has no ko_playoffs '{key}'", [k['key'] for k in rl['ko_playoffs']])
            at = next((i for i, k in enumerate(ko) if k['key'] == before), None)
            assert at is not None, (f"s7pack: the source pack has no ko_playoffs '{before}' to put '{key}' before", [k['key'] for k in ko])
            ko.insert(at, e)
        GA = 'SERIE D GIRONE A'                 # (girone A: promoted 0 / relegated 1 - the deciders take the other place;
        d5, dd = rl['divisions'][5], lg2['divisions'][5]       # found by name in BOTH packs, not trusted by index)
        for tag, d in ((deciders, d5), ('the source pack', dd)):
            nm = [n for v in d.get('names', {}).values() for n in v]
            assert nm and all(n == GA for n in nm), (f"s7pack --deciders: divisions[5] of {tag} is not '{GA}'", nm)
        for f in ('promoted', 'relegated'):
            dd[f] = d5[f]
    assert sorted(lg2['reserve']['pool']) == sorted(pool), 's7pack: reserve pool != the stand-ins'

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
    import globnum
    import mkseason
    gb = globnum.base(mkseason.Pack(out), fileno)       # (globnum.split ignores a split file's own 'base')
    if base is not None and base != gb:
        shutil.rmtree(out)
        raise SystemExit(f's7pack: --base {base} != globnum\'s {gb} (file {fileno} run 1)')
    fs2['league_b']['base'] = gb
    with open(os.path.join(out, 'pack.json'), 'w', encoding='utf-8') as f:
        json.dump(m2, f, ensure_ascii=False, indent=1)
        f.write('\n')
    rid, nr, npool = {}, 0, 0                   # import41.csv: every club's place in the one-file layout (4.1's), in
    for c in clubs:                             # gplay's RI identity space: a TEAM.102 row 0..255, or RIS (256) + its
        if c['file'] == 'league':               # index among the off-file pool's records (clubs.csv order) - what
            rid[c['key']], nr = nr, nr + 1      # RI_STATE.maps holds (+1); sreg.old_ord's input
        else:
            rid[c['key']], npool = RIS + npool, npool + 1
    assert nr <= RIS, 's7pack: the one-file layout past 256 rows'
    with open(os.path.join(out, 'import41.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('key,ident41\n' + ''.join(f"{c['key']},{rid[c['key']]}\n" for c in new))
    p41 = [c['key'] for c in clubs if c['file'] == 'pool']             # (4.1's RS order: its clubs.csv's; S7's the same
    p7 = [c['key'] for c in left]                                       #  rule on the new clubs.csv: the stand-ins)
    with open(os.path.join(out, 'newpool41.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('key,pool41,pool\n' + ''.join(f"{k},{i},{p7.index(k) if k in p7 else 255}\n" for i, k in enumerate(p41)))
    return {'league': len(top), 'league_b': len(sd), 'pool': len(left), 'join': join, 'sizes': size}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src')
    ap.add_argument('groups')
    ap.add_argument('out')
    ap.add_argument('--base', type=int)
    ap.add_argument('--file', type=int, default=144)
    ap.add_argument('--deciders', help='a one-file pack folder with dA_title / dA_reltie (internal/world2526/world5tm-s1rank-int3/ita)')
    a = ap.parse_args(argv)
    s = build(a.src, a.groups, a.out, a.base, a.file, a.deciders)
    print(f"s7pack: {a.out}: league {s['league']} + league_b {s['league_b']} (groups {sorted(set(s['sizes'].values()))}) "
          f"+ {s['pool']} stand-ins off-file; joining: {' '.join(s['join'])}")


if __name__ == '__main__':
    main(sys.argv[1:])
