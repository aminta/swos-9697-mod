"""N7 piece 3 (Panchina 10/11, MC's GO): the club registry's code (sreg.c: the engine's sr_reg + sr_regsave) at
obj4+swreg.SREG_AT, under lrank.LR_AT, and its SWC1 section 'IT' (swe.c it_save / it_load; n7-s7-clubmap.md §2).

DORMANT until a world has a registry shape (S7: Italy's files 102 + 144, piece 4's pack data): shape() is None, sreg.c
is not linked, swe.c's SREG_FN stays 0, no 'IT' is written and SWC1 keeps its 32 B - a save is byte-identical to one
of the build before. SREG_FORCE=1 (test builds only, host tests): sreg.c linked with an empty shape the host test
pokes (S7's, MC 11/11), SWC1 sized for ITALY_ROWS, SREG_WORLD FORCE_WORLD.

Piece 4 (n7-p4.md §1-§3, §6b): shape() from the pack (the files' 'divisions' / 'pool_rows', clubs.csv's order and
divisions), checked at build; patch() puts SREG_NF / SREG_NCLUB / SREG_SPEC / SREG_DIV and SREG_WORLD (the pack's world:
only its careers' saves carry 'IT', sreg.c's gate on SWC1's world byte); the section's flags = sreg.c's SREG_FLAGS."""
import os
import re
import struct

ITALY_ROWS = 262               # S7 (MC 11/11): 102 = 100 + 144 = 9 x 18, the stand-ins off-file (the map's size in a shaped save)
SECTION = 0x5449               # 'IT'
LABELS = {}                    # (hosttest: sreg.c's symbols)


POOL, OUT = 0xFE, 0xFF          # (swosrules.h SR_REG_POOL / SR_REG_OUT: a pool row's division, a club off the files)
FORCE_WORLD = 5                # (SREG_FORCE test builds: World 2026-27's world byte, as its pack's 'world')


def shape():
    """(world, files, divisions) of the build's registry, or None (dormant: no pack has one before S7).

    The pack (swc/1.4 countries.<c>.files, n7-p4.md §1): a career-world pack whose 'files' has 2+ roles with
    'divisions' - {role: {file, base, divisions: [the league's division indices in the file's order], pool_rows}}.
    Its clubs.csv, in order, is the ident order (append-only): a club's 'file' names its role, its 'division' the
    division (int) or 'pool' (one of the role's pool rows); a club of a role without 'divisions' is off the files.
    files: [(file, [(div, size)], pool)], size = the clubs with that division; divisions: each club's byte (POOL /
    OUT). Checks (the club key on failure, not a -1 in the game): within each role the clubs in its division order,
    pool rows last (= the team file's ordinals mkseason writes); pool_rows = its pool clubs; rows <= 256; one such
    pack per build (one 'IT' section)."""
    if hasattr(shape, 'cache'):
        return shape.cache
    import mkseason
    found = [pk for pk in mkseason.packs()
             if sum('divisions' in v for v in pk.meta.get('files', {}).values()) >= 2]
    assert len(found) <= 1, ('sreg: two packs with a registry shape (one SWC1 \'IT\')', [pk.path for pk in found])
    shape.cache = shape_of(found[0]) if found else None
    return shape.cache


def shape_of(pk):
    """shape()'s (world, files, divisions) of one pack (meta, clubs, world, path: mkseason.Pack's)."""
    fs = pk.meta['files']
    roles = [k for k, v in fs.items() if 'divisions' in v]
    assert len(roles) <= 8 and len(pk.clubs) <= 1024, ('sreg: files / clubs past the library', pk.path)
    files, divs, last, count = [], [], {r: -1 for r in roles}, {}
    for key, c in pk.clubs.items():
        r = c['file']
        if r not in roles:
            divs.append(OUT)
            continue
        order = fs[r]['divisions']
        dv = (c.get('division') or '').strip()
        assert dv == 'pool' or dv.isdigit(), ('sreg: a club of a registry file needs a division (or \'pool\')', key, r)
        d = POOL if dv == 'pool' else int(dv)
        k = len(order) if d == POOL else order.index(d) if d in order else None
        assert k is not None, ('sreg: club in a division its file does not hold', key, r, d)
        assert k >= last[r], ('sreg: clubs.csv not in the file\'s division order (pool rows last)', key, r)
        last[r] = k
        count[r, d] = count.get((r, d), 0) + 1
        divs.append(d)
    for r in roles:
        v = fs[r]
        sizes = [(d, count.get((r, d), 0)) for d in v['divisions']]
        pool = count.get((r, POOL), 0)
        assert pool == v.get('pool_rows', 0), ('sreg: pool_rows not its pool clubs', r, pool, v.get('pool_rows'))
        assert all(n for _, n in sizes) and sum(n for _, n in sizes) + pool <= 256 and len(sizes) <= 16, \
            ('sreg: a file\'s rows', r, sizes, pool)
        files.append((v['file'], sizes, pool))
    assert sum(1 for _, _, pool in files if pool) <= 1, ('sreg: pool rows in two files', pk.path)
    return pk.world, files, divs


OLD_NONE = 0xFFFF                               # (old_ord: a club the one-file layout did not have)


def old_ord(pk):
    """The old-save import's table (n7-p4.md §4 step 1): u16 per ident (clubs.csv order), the club's 4.1 identity in
    gplay's RI space - a TEAM.102 row 0..255, or RIS (256) + its off-file pool index - or OLD_NONE. From the shaped
    pack's import41.csv (tools/s7pack.py), matched by key. u16, not the note's u8: 4.1's file 102 already uses rows
    0..255, and the 42 pool clubs need 256 + i. The C side: old_word[i] = the 102 slot x whose identity
    (RI_STATE.maps[x] ? maps[x] - 1 : x) is old_ord[i], else SR_REG_NONE. Checks: every key a club of the pack, no
    identity twice, rows < 256, pool indices < the 4.1 pool's size."""
    import csv
    path = os.path.join(pk.path, 'import41.csv')
    with open(path, encoding='utf-8', newline='') as f:
        rows = {r['key']: int(r['ident41']) for r in csv.DictReader(f)}
    assert set(rows) <= set(pk.clubs), ('sreg: import41.csv: keys not in clubs.csv', sorted(set(rows) - set(pk.clubs))[:5])
    vals = list(rows.values())
    assert len(vals) == len(set(vals)), ('sreg: import41.csv: an identity twice', path)
    npool = sum(1 for v in vals if v >= 256)
    assert all(0 <= v < 256 + npool for v in vals), ('sreg: import41.csv: an identity past rows / pool', path)
    return [rows.get(k, OLD_NONE) for k in pk.clubs]


def old_ord_bytes(table):
    return struct.pack(f'<{len(table)}H', *table)


def spec_bytes(files, nf=8, ndivs=16):
    """SREG_SPEC's bytes: sr_reg_file[nf] (u8 file, u8 ndiv, u8 div[ndivs], u8 size[ndivs], u16 pool)."""
    import struct
    out = b''
    for num, divs, pool in files:
        out += (bytes([num, len(divs)]) + bytes(d for d, _ in divs).ljust(ndivs, b'\0') +
                bytes(n for _, n in divs).ljust(ndivs, b'\0') + struct.pack('<H', pool))
    return out.ljust(nf * (4 + 2 * ndivs), b'\0')


def rows():
    s = shape()
    if s:
        return sum(sum(n for _, n in divs) + pool for _, divs, pool in s[1])
    return ITALY_ROWS if os.environ.get('SREG_FORCE') else 0


def section_bytes():
    """SWC1's room for 'IT' (its 4 B section header + sr_reg_save_size), 0 dormant."""
    n = rows()
    return 4 + 12 + (10 * n + 7) // 8 if n else 0


def obj4_pages(cur):
    """obj4's file pages with the old-save import's band (swreg.SREG2_AT..SREG2_END): cur, raised to it only when the
    import links (import_on: a shaped S7 build; dormant builds: cur, their bytes unchanged)."""
    import swreg
    return max(cur, swreg.SREG2_END // 0x1000) if import_on() else cur


def sreg2_check(p):
    """The import's band (swreg.SREG2_AT..SREG2_END, two pages since 42-s7import, MC 15/11) is obj4's and free."""
    import swreg
    assert swreg.SREG2_AT % 0x1000 == 0 and swreg.SREG2_END > swreg.SREG2_AT, ('sreg: SREG2', hex(swreg.SREG2_AT))
    assert p.le.obj(4).npages * 0x1000 >= swreg.SREG2_END, ('sreg: obj4 has no SREG2 pages (obj4_pages)',
                                                            p.le.obj(4).npages)
    assert not any(p.get(4, swreg.SREG2_AT, swreg.SREG2_END - swreg.SREG2_AT)), ('sreg: obj4+SREG2_AT not free',
                                                                                hex(swreg.SREG2_AT))


def patch(p, syms_swe):
    """sreg.c at obj4+SREG_AT and swe.c's SREG_FN; returns the end (or None, dormant)."""
    if not section_bytes():
        return None
    import cobj
    import lrank
    import swreg
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sreg.c')
    with open(os.path.join(os.path.dirname(src), 'swe.c')) as h:            # (sreg.c: the registry fits the arena)
        arena = re.search(r'#define SWE_ARENA (0x[0-9A-Fa-f]+|\d+)', h.read()).group(1)
    obj = cobj.compile_c(src, (f'-DSWE_ARENA={arena}',), sections=True)
    roots = ['sreg_build', 'sreg_size', 'sreg_save', 'sreg_load', 'sreg_new', 'SREG_CHG', 'SREG_NF', 'SREG_NCLUB', 'SREG_SPEC',
             'SREG_REG', 'SREG_LAST', 'SREG_WORLD', 'SREG_FLAGS'] + (['sreg_get'] if shape() else [])
    with open(os.path.join(os.path.dirname(src), 'swce', 'swosrules.h')) as h:
        hdr = h.read()
    ndiv, nfiles, ndivs = (int(re.search(rf'#define {k}\s+(\d+)', hdr).group(1))
                           for k in ('SR_REG_CLUBS', 'SR_REG_FILES', 'SR_DIVS'))  # (SREG_DIV's bytes; SREG_SPEC's shape)
    top = getattr(swreg, 'CONTI4_AT', swreg.ST_AT)      # (conti's data once 4.1 is merged into 4.2, ST before)
    if hasattr(swreg, 'UPRIZE2_AT'):                    # (4.1 merged: uprize2 links below SREG_DIV_AT whatever the
        assert hasattr(swreg, 'UPRIZE2_END') and swreg.UPRIZE2_END <= swreg.SREG_DIV_AT, \
            ('4.1 -> 4.2 merge: swreg.UPRIZE2_END (uprize part 2\'s link limit, today UPRIZE2_AT + 0x1000) must end '
             'at or under SREG_DIV_AT', hex(swreg.SREG_DIV_AT))                # order: uprize2 placed after us)
    assert swreg.SREG_DIV_AT + ndiv <= top and not any(p.get(4, swreg.SREG_DIV_AT, ndiv)), \
        ('sreg: obj4+SREG_DIV_AT not free / past conti', hex(swreg.SREG_DIV_AT), hex(top))
    assert p.le.obj(4).npages * 0x1000 >= lrank.LR_AT, ('sreg: obj4 has no page at SREG_AT (a world build: lrank)',
                                                         p.le.obj(4).npages)
    assert not any(p.get(4, swreg.SREG_AT, lrank.LR_AT - swreg.SREG_AT)), 'sreg: obj4+SREG_AT not free'
    syms, end, bss = cobj.link(p, obj, swreg.SREG_AT, (4, 0), externs={'SREG_DIV': (4, swreg.SREG_DIV_AT), 'SREG_SWC1': syms_swe['SWC1']},
                               limit=lrank.LR_AT, text_obj=4, roots=roots)
    syms['SREG_DIV'] = (4, swreg.SREG_DIV_AT)
    assert not bss and end <= lrank.LR_AT, ('sreg: code + data past LR_AT', hex(end), bss)
    cobj.add_ptr(p, syms['SREG_REG'][1], *syms_swe['SWE_ARENA_AT'], 4)   # (the registry: the engine arena's start)
    LABELS.clear()
    LABELS.update(syms)
    s = shape()
    if s:                                               # (S7: the pack's shape; SREG_FORCE: an empty one, world 5)
        world, files, divs = s
        assert len(divs) <= ndiv and len(files) <= nfiles, ('sreg: the shape past swosrules.h', len(divs), len(files))
        p.put(*syms['SREG_NF'], struct.pack('<i', len(files)))
        p.put(*syms['SREG_NCLUB'], struct.pack('<i', len(divs)))
        p.put(*syms['SREG_SPEC'], spec_bytes(files, nfiles, ndivs))
        p.put(4, swreg.SREG_DIV_AT, bytes(divs))
    p.put(*syms['SREG_WORLD'], struct.pack('<I', s[0] if s else FORCE_WORLD))
    fn = syms_swe['SREG_FN']
    for k, nm in enumerate(('sreg_size', 'sreg_save', 'sreg_load', 'sreg_new', 'sreg_build')):
        if k == 4 and import_on():                      # (the absent case: patch_import's sreg_absent, after s7swap)
            continue
        cobj.add_ptr(p, fn[1] + 4 * k, *syms[nm], 4)
    print(f'exe: club registry (N7, sreg.c) obj4+{swreg.SREG_AT:#x}..{end:#x} of {lrank.LR_AT:#x}, SREG_DIV '
          f'obj4+{swreg.SREG_DIV_AT:#x}..{swreg.SREG_DIV_AT + ndiv:#x}; SWC1 \'IT\' '
          f'{section_bytes()} B ({rows()} rows{"" if s else ", SREG_FORCE: an empty shape"})')
    return end


def import_on():
    """42-s7import (MC 15/11): the old-save import is linked (SREG2) in a shaped S7 build; else SREG_FN[4] = sreg_build."""
    import s7swap
    return bool(shape()) and s7swap.on() and not os.environ.get('SREG_FORCE')


IMPORT = {}                    # (hosttest / harness: sreg2.c's symbols)


def patch_import(p, syms_swe, s7l):
    """sreg2.c + sreg_import.c at obj4+SREG2_AT (42-s7import, MC 15/11): the absent-'IT' import (SREG_FN[4] =
    sreg_absent). After sreg.patch and s7swap.patch: the library's copies are theirs (sr_reg_build / check: sreg.c's;
    sr_reg_season / sr_wmap_import: s7swap.c's), the walk is s7swap.c's s7_imp_walk. The tables: the shaped pack's
    old_ord / newpool, tools/import41_fixed.json (the 4.1 side), the S7 build's RI layout and globals."""
    if not import_on():
        return None
    import bigtables
    import careerworld
    import cobj
    import globnum
    import gplay
    import import41
    import mkseason
    import swreg
    pk = next(pk for pk in mkseason.packs() if sum('divisions' in v for v in pk.meta.get('files', {}).values()) >= 2)
    world, files, divs = shape()
    fx = import41.fixed()
    old, newpool = old_ord(pk), new_pool(pk)
    lay41, lay7 = fx['ri_layout'], ri_layout(mkseason.off_pools())
    gl41 = import41.glob_bytes(fx['glob'])
    gl7 = import41.glob_bytes([(f, globnum.runs_of(pk, f)) for f, _, _ in files])
    ndiv = 1 + max(d for _, ds, _ in files for d, _ in ds)
    fb = s7l['S7_FB']
    ri_file = p.get(*fb, 1)[0]
    e41, e7 = import41.ri_entry(lay41, world, fx['file']), import41.ri_entry(lay7, world, ri_file)
    assert e41 and e41[1] == 256 and len(e41[4]) == 1 and e7, ('sreg2: the 4.1 / S7 RI entries of Italy', e41, e7)
    pd = import41.pool_diff(lay41, lay7, world, fx['file'], ri_file)
    assert not pd, ('sreg2: the RI pools moved between the 4.1 and S7 tables: st_ovr (before the import) would read '
                    'the wrong overrides', pd[:3])
    assert len(newpool) == e41[4][0], ('sreg2: newpool41.csv vs 4.1\'s Italy pool', len(newpool), e41[4])
    pool0 = struct.unpack('<H', p.get(*s7l['S7_POOL0'], 2))[0]           # (S7 RI's queue holds idents, pool ident j <->
    bad = [(pk_k, k, c) for c, (pk_k, v) in enumerate(zip(pk.clubs, old)) if v != OLD_NONE and v >= 256   # RS record j:
           for k in (v - 256,) if newpool[k] != 0xFF and c != pool0 + newpool[k]]   # a stand-in's ident = its RS index's)
    assert not bad, ('sreg2: a 4.1 stand-in whose S7 ident is not S7_POOL0 + its newpool41 RS index', bad[:3])
    assert bigtables.ON[0] and 'SOME' in bigtables.LABELS, 'sreg2: someLeaguesTable not moved (bigtables)'
    nslt = bigtables.LABELS['LIMIT_ALL'][1]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swe.c')) as h:
        arena = re.search(r'#define SWE_ARENA (0x[0-9A-Fa-f]+|\d+)', h.read()).group(1)
    layn, gln = max(len(lay41), len(lay7)), max(len(gl41), len(gl7))
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sreg2.c')
    obj = cobj.compile_c(src, ('-Oz', f'-DIMP_NCLUB={len(divs)}', f'-DIMP_NPOOL41={len(newpool)}', f'-DIMP_LAYN={layn}',
                               f'-DIMP_GLN={gln}', f'-DIMP_NSLT={nslt}', f'-DSWE_ARENA={arena}'), sections=True)
    sel = careerworld.SITES['nc']['selteam']
    import countries
    if countries.COMP[0] is None:
        countries.tables(p)
    comp = countries.COMP[0]                    # (competitionsTable, in place in obj2)
    ext = {k: LABELS[k] for k in ('SREG_REG', 'SREG_NF', 'SREG_NCLUB', 'SREG_SPEC', 'SREG_WORLD', 'SREG_FLAGS', 'sreg_build',
                                  'sr_reg_build', 'sr_reg_check')}
    ext.update({'SREG_DIV': (4, swreg.SREG_DIV_AT), 'SREG_SWC1': syms_swe['SWC1'], 'SWE_ARENA_AT': syms_swe['SWE_ARENA_AT'],
                'cstack_call': syms_swe['cstack_call'], 'swe_ready': syms_swe['swe_ready'],
                'IMP_RI': gplay.LABELS['RI_STATE'], 'IMP_SLT': bigtables.LABELS['SOME'],
                'IMP_SEASON': (2, careerworld.SITES['season']), 'IMP_D6CDC': (sel[0], sel[1] + 6), 'IMP_D6CB8': (sel[0], sel[1] - 0x1E),
                'IMP_CCN': (sel[0], sel[1] + 0x9C58), 'IMP_D8': (sel[0], sel[1] + 0x1FD4),     # (IDA E092E / D8CAA - selTeamNumber D6CD6)
                'IMP_COMPTAB': (2, comp),
                'IMP_DIY': (sel[0], sel[1] + 0x8820)})        # (IDA DF4F6 competitionFileBuffer - D6CD6)
    ext.update({k: s7l[k] for k in ('S7_AREG', 'S7_CLOG', 's7_imp_walk', 's7_flush', 'sr_reg_season', 'sr_wmap_import')})
    sreg2_check(p)
    syms, end, bss = cobj.link(p, obj, swreg.SREG2_AT, (4, 0), externs=ext, limit=swreg.SREG2_END, text_obj=4,
                               roots=['sreg_absent', 'SREG_IMP', 'IMP_OLD', 'IMP_NEWPOOL', 'IMP_BASE', 'IMP_LAY41', 'IMP_LAY7',
                                      'IMP_GL41', 'IMP_GL7', 'IMP_FILES', 'IMP_NDIV'])
    assert not bss and end <= swreg.SREG2_END, ('sreg2: past SREG2_END / .bss', hex(end), bss)
    p.put(*syms['IMP_OLD'], old_ord_bytes(old))
    p.put(*syms['IMP_NEWPOOL'], newpool)
    p.put(*syms['IMP_BASE'], fx['base'])
    p.put(*syms['IMP_LAY41'], lay41)
    p.put(*syms['IMP_LAY7'], lay7)
    p.put(*syms['IMP_GL41'], gl41)
    p.put(*syms['IMP_GL7'], gl7)
    p.put(*syms['IMP_FILES'], bytes((fx['file'], ri_file)))
    p.put(*syms['IMP_NDIV'], bytes((ndiv,)))
    cobj.add_ptr(p, syms_swe['SREG_FN'][1] + 16, *syms['sreg_absent'], 4)
    IMPORT.clear()
    IMPORT.update(syms)
    LABELS['IMP'] = dict(syms)                         # (syms.json: sreg 'IMP.SREG_IMP' ...)
    print(f'exe: engine item SREG2 old-save import (sreg2.c + sreg_import.c, 42-s7import) obj4+{swreg.SREG2_AT:#x}..{end:#x} '
          f'of {swreg.SREG2_END:#x} ({swreg.SREG2_END - end} B left): {len(divs)} idents, 4.1 Italy RI {e41[:2]} pool {e41[4]}, '
          f'S7 RI {e7[:2]} pool {e7[4]}, someLeaguesTable {nslt} B, {ndiv} divisions; SREG_IMP obj4+{syms["SREG_IMP"][1]:#x}')
    return end


def ri_layout(tabs):
    """sreg_ri_import's layout bytes of an RI table (ripool / mkseason.off_pools tabs): db files; per file db world,
    db file, dw map offset, dw slots (its records), db pools, pools x db n (each pool's records = its queue's length).
    The import needs two: the 4.1 table's (Italy on file 102) and the S7 build's (Italy on file 144)."""
    import ripool
    out = bytearray([len(tabs)])
    for (world, fl, pools, *_), (moff, nmap, *_r) in zip(tabs, ripool.layout(tabs)[0]):
        ns = [len(pl[4] if pl[0] == 'league' else pl[5]) for pl in pools]
        assert all(n < 256 for n in ns) and len(ns) < 256
        out += bytes((world, fl)) + struct.pack('<HH', moff, nmap) + bytes([len(ns)]) + bytes(ns)
    return bytes(out)


def new_pool(pk):
    """sreg_ri_import's newpool (MC 11/11): u8 per 4.1 off-file pool record (its index, import41.csv's 256 + k), its S7
    RS index or 255 (it left the pool: one of the clubs that join Serie D). From the shaped pack's newpool41.csv
    (tools/s7pack.py). Checks: every 4.1 index once, the kept ones a permutation of 0 .. n - 1."""
    import csv
    path = os.path.join(pk.path, 'newpool41.csv')
    with open(path, encoding='utf-8', newline='') as f:
        rows = [(int(r['pool41']), int(r['pool'])) for r in csv.DictReader(f)]
    assert sorted(k for k, _ in rows) == list(range(len(rows))), ('sreg: newpool41.csv: 4.1 indices', path)
    kept = sorted(v for _, v in rows if v != 255)
    assert kept == list(range(len(kept))), ('sreg: newpool41.csv: S7 indices not 0 .. n - 1', path)
    return bytes(v for _, v in sorted(rows))
