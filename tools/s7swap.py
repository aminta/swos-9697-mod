"""4.2 S7: the season-end swap builder (s7swap.c; internal/handoff/s7-swap-plan.md, MC 13/11) at obj4+swreg.S7SWAP_AT,
linked only with a registry shape (sreg.shape(): MC 13/11, = gplay.gp_s7(), asserted). Dormant: no byte. The registry
library (sr_reg_season + fill, sr_reg_ident / div / size, sr_wmap_*) lives here ONCE: the old-save import (SREG2, Panchina)
calls it here (LABELS) and never links its own copy.

Fills s7swap.c's tables from the shaped pack: S7_FA / S7_FB (the upper / lower struct's file), the boundary levels'
divisions (S7_UP: the upper struct's last level, S7_LO: the lower's first; group order), the two files' global runs
(S7_GB: base, the second run's first ordinal and base - G144), and S7_AREA per ident (sreg's ident order = clubs.csv):
low nibble the upper level's group, high nibble the lower level's (clubs.csv 'area', one entry per level of groups;
else the club's own group on that level; else F = none). pg_fix's S7_PTR (pgroups.py) -> s7_season.

Piece 3 (the load apply): S7_HRUN (runs of S7_HOME words) per ident (its home team word as shipped: its role's file, its rank among the role's
clubs in clubs.csv order = the ordinal mkseason writes = the spec registry's first word), the two files' names (the
world's stem, mkseason.ns_stem), their record counts and ORIG offsets (swe.c S7_ORIG, swreg.S7_ORIG_SZ); ri_load's
S7_LPTR (ripool.py) -> s7_load; the engine's file layer (swefile.c) linked for it (patch.py sets swe.SWEFILE)."""
import os
import struct

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7swap.c')
SRC_GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7geo.c')
NID = 320                       # (s7swap.c S7_NID: S7_AREA's room)
LABELS = {}


LIB = ['sr_reg_season', 'sr_reg_ident', 'sr_reg_div', 'sr_reg_word', 'sr_reg_size', 'sr_reg_work_size', 'sr_wmap_build',
       'sr_wmap_get', 'sr_wmap_import', 'sreg_walk_site']


def on():
    import gplay
    import sreg
    s = sreg.shape() is not None
    assert s == bool(gplay.gp_s7()), ('S7: a registry shape and GP_S7 (cross-struct play-offs) must come together',
                                      s, gplay.gp_s7())
    return s


def page_end():
    import swreg
    return (swreg.S7GEO_END + 0xFFF) & ~0xFFF           # (4.2 geography: the S7GEO band is the last of the S7 bands)


def tables(pk):
    """(fa, fb, up divisions, low divisions, [(base, split ordinal, base2)] x 2, area bytes per ident)."""
    import globnum
    import mkseason
    fs = sorted({pk.div_key(d)[0] for d in range(len(pk.divisions()))}, key=lambda f: min(pk.struct_divs(f)))
    assert len(fs) == 2, ('s7swap: two league structs', fs)
    fa, fb = fs
    lv = pk.levels()
    up = [x for x in lv if pk.div_key(x[0])[0] == fa][-1]
    lo = [x for x in lv if pk.div_key(x[0])[0] == fb][0]
    assert lv.index(lo) == lv.index(up) + 1, 's7swap: the boundary levels are not adjacent'
    assert 1 <= len(up) <= 15 and 1 <= len(lo) <= 15, ('s7swap: groups per level', len(up), len(lo))
    glevels = [x for x in lv if len(x) > 1]             # (clubs.csv 'area': one entry per level of groups)

    def nib(k, level):
        c = pk.clubs[k]
        a = (c.get('area') or '').split('/')
        i = glevels.index(level) if level in glevels else -1
        if 0 <= i < len(a) and a[i]:
            return mkseason.area_byte(a[i]) & 0xF
        d = pk.division.get(k)
        return level.index(d) if d in level else 0xF
    area = bytes(nib(k, up) | nib(k, lo) << 4 for k in pk.clubs)
    gb = []
    for f in fs:
        runs = globnum.runs_of(pk, f)
        assert 1 <= len(runs) <= 2, ('s7swap: global runs', f, runs)
        gb.append((runs[0][0], runs[0][1] if len(runs) == 2 else 0, runs[1][0] if len(runs) == 2 else 0))
    return fa, fb, up, lo, gb, area


def homes(pk):
    """(S7_HOME words per ident, {file: records}) from the pack's roles: a club of a role with divisions has its role's
    file and its rank among the role's clubs (clubs.csv order); the rest FFFF."""
    fs = pk.meta['files']
    roles = {k: v for k, v in fs.items() if 'divisions' in v}
    n, out = {}, []
    for c in pk.clubs.values():
        r = c['file']
        if r not in roles:
            out.append(0xFFFF)
            continue
        o = n.get(r, 0)
        n[r] = o + 1
        out.append(roles[r]['file'] | o << 8)
    return out, {roles[r]['file']: k for r, k in n.items()}


def check_pool_names(pk, home):
    """MC 13/11 (case 3 = marker in ri's queue): the registry's pool rows (idents whose home is FFFF) are exactly the clubs
    of the off-file pool's RS file, by NAME, both ways and without repeats - so a future pack edit cannot silently break
    the queue marker 0x4000 | registry ident (Name-level is enough: not the records' bytes)."""
    if not hasattr(pk, 'pool_data'):                    # (the RS file's records: mkseason.rs_files' source)
        pk.team_files()
    rs = getattr(pk, 'pool_data', None)
    assert rs, ('s7swap: no RS file for the pack\'s pool', pk.world, pk.pool_file)
    n = rs[0] << 8 | rs[1]
    rsn = [rs[2 + 684 * k + 5:2 + 684 * k + 22].split(b'\0')[0].decode('latin1') for k in range(n)]
    regn = [c['name'] for c, h in zip(pk.clubs.values(), home) if h == 0xFFFF]
    assert len(set(rsn)) == len(rsn) and len(set(regn)) == len(regn), ('s7swap: repeated pool club names',)
    miss = sorted(set(regn) - set(rsn)), sorted(set(rsn) - set(regn))
    assert not miss[0] and not miss[1], ('s7swap: registry pool rows != the RS file\'s clubs: only in the registry',
                                        miss[0][:5], 'only in RS', miss[1][:5])
    return n


def pool_order(pk, home):
    """S7 x pool (MC 13/11, one registry): (first pool ident, pool size). The pool idents (home FFFF) are consecutive and
    pool ident first + j is the RS file's record j, by name, in order: s7_load gives that ident RI_POOL's record j,
    the seed queues the RS order's records as these idents (s7swap.c s7_poolk). check_pool_names first (the sets)."""
    ids = [i for i, h in enumerate(home) if h == 0xFFFF]
    if not ids and getattr(pk, 'pool_file', None) is None:
        return 0xFFFF, 0                                # (no off-file pool: the s7t test pack)
    n = check_pool_names(pk, home)
    rs = pk.pool_data
    rsn = [rs[2 + 684 * k + 5:2 + 684 * k + 22].split(b'\0')[0].decode('latin1') for k in range(n)]
    assert ids == list(range(ids[0], ids[0] + len(ids))), ('s7swap: pool idents not consecutive', ids[:3], ids[-3:])
    regn = [c['name'] for c, h in zip(pk.clubs.values(), home) if h == 0xFFFF]
    bad = [(j, a, b) for j, (a, b) in enumerate(zip(regn, rsn)) if a != b]
    assert len(regn) == n and not bad, ('s7swap: pool ident first + j is not RS record j (by name)', bad[:3])
    return ids[0], n


def home_runs(home):
    """S7_HRUN: [(first ident, n, file, first ordinal)] - home's words as runs (consecutive idents, consecutive
    ordinals of one file); FFFF entries in none"""
    runs = []
    for i, w in enumerate(home):
        if w == 0xFFFF:
            continue
        f, o = w & 0xFF, w >> 8
        r = runs[-1] if runs else None
        if r and r[2] == f and r[0] + r[1] == i and r[3] + r[1] == o:
            r[1] += 1
        else:
            runs.append([i, 1, f, o])
    assert len(runs) <= 8, ('s7swap: S7_HRUN past 8 runs', runs)
    return [tuple(r) for r in runs]


def fnv(b):
    """FNV-1a 32 (s7swap.c fnv)"""
    h = 2166136261
    for x in b:
        h = (h ^ x) * 16777619 & 0xFFFFFFFF
    return h


def orig_layout(nrec):
    """[(offset, records)] for (fa, fb): each 2 + 684 n bytes, 16-aligned"""
    import swreg
    at, out = 0, []
    for k in nrec:
        out.append((at, k))
        at = (at + 2 + 684 * k + 15) & ~15
    assert at <= swreg.S7_ORIG_SZ, ('s7swap: ORIG buffers past swreg.S7_ORIG_SZ', at, hex(swreg.S7_ORIG_SZ))
    return out


def late(p):
    """End of patch_exe (after trailer.late: every engine item bound): WSITES from wsites.rows(), S7_ENN (trailer's
    EN_ITEMS count), S7_CFBLEN (careerFileBuffer's fixed part). Rows resolve at each season end (s7swap.c wcheck,
    S7_WRES in the arena: MC 13/11); here each row's item is checked to be one this build saves, and in its bytes."""
    if 'WSITES' not in LABELS:
        return
    import engine
    import trailer
    import wsites
    wsites.check_layout()
    import gplay
    wsites.CD_FILE[0] = p.get(1, gplay.LABELS['CD_TAB'] + 2, 1)[0] if 'CD_TAB' in gplay.LABELS else None   # (gplay's lf)
    rows = wsites.rows()
    import re                                           # (MC 15/11: the C table's room = the Python one; rows + WS_END fit)
    hmax = int(re.search(r'#define WS_MAX\s+(\d+)', open(os.path.join(os.path.dirname(SRC), 'sreg_walk.h')).read()).group(1))
    assert hmax == wsites.WS_MAX and len(rows) + 1 <= wsites.WS_MAX, ('s7swap: WSITES rows / WS_MAX', len(rows), hmax, wsites.WS_MAX)
    p.put(*LABELS['WSITES'], wsites.table(rows))
    en = trailer.INFO['en_n']
    p.put(*LABELS['S7_ENN'], struct.pack('<I', en))
    p.put(*LABELS['S7_CFBLEN'], struct.pack('<I', trailer.INFO['FIXED'][1]))
    names = {engine.item_id(n): n for n in engine.SAVE_ITEMS}
    for k, (item, off, stride, count, form, aux) in enumerate(rows):
        iid = engine.item_id(item) if isinstance(item, str) else item
        assert iid != wsites.WI_MAIN, ('s7swap: WSITES WI_MAIN rows are not walked yet', k)
        if iid == wsites.WI_CACHE:
            size = 684
        elif iid == wsites.WI_CFBH:
            size = trailer.INFO['FIXED'][1] - 0x10000
        elif iid == wsites.WI_CFB:
            size = trailer.INFO['FIXED'][1]
        else:
            assert iid in names, ('s7swap: WSITES row on an engine item this build does not save', k, item)
            size = engine.SAVE_ITEMS[names[iid]][0]
        span = count if form == wsites.WS_R else stride if form == wsites.WS_D else max(count - 1, 0) * stride + 2   # (WS_R: stride = fill | file << 8; WS_D: stride = the room)
        assert off + span <= size, ('s7swap: WSITES row past its item', k, item, size)
    if 'ST' in engine.ITEM_AT:
        LABELS['ST_ITEM'] = engine.ITEM_AT['ST']          # (host tests: the TEST rows' engine item)
    print(f's7swap: WSITES {len(rows)} rows{" (TEST rows: S7_WSITES_TEST)" if wsites.TEST else ""}')


def geo_table(meta, ngroups):
    """4.2 Serie D geography (MC 14/11): the pack's pack.json 'geo.neighbours' as the 9 x 9 byte table of s7geo.c (a girone's
    neighbours in list order, 0xFF-terminated). REFUSED (never an empty table) when the key is missing, or the table does not
    name all `ngroups` gironi A.., lists a girone itself or twice, is not symmetric (x lists y <=> y lists x) or leaves a
    girone unreachable from A."""
    geo = (meta.get('geo') or {}).get('neighbours')
    if not geo:
        raise SystemExit("s7swap: the pack has no 'geo.neighbours' (4.2 Serie D geography): a GP_S7 build is refused, never linked "
                         "with an empty table (tools/s7pack_geo.json is copied in by s7pack.py)")
    letters = [chr(65 + i) for i in range(ngroups)]
    if sorted(geo) != letters or ngroups > 9:
        raise SystemExit(f"s7swap: geo.neighbours must name exactly the gironi {letters}: {sorted(geo)}")
    for L in letters:
        nb = list(geo[L])
        if len(set(nb)) != len(nb) or L in nb or any(c not in letters for c in nb):
            raise SystemExit(f"s7swap: geo.neighbours[{L}] = {geo[L]!r}: a girone itself, twice or unknown")
        for c in nb:
            if L not in geo[c]:
                raise SystemExit(f"s7swap: geo.neighbours is not symmetric: {L} lists {c} but {c} does not list {L}")
    seen, todo = {'A'}, ['A']
    while todo:
        for c in geo[todo.pop()]:
            if c not in seen:
                seen.add(c)
                todo.append(c)
    if len(seen) != ngroups:
        raise SystemExit(f"s7swap: geo.neighbours leaves {sorted(set(letters) - seen)} unreachable from A")
    tab = bytearray(b'\xff' * 81)
    for i, L in enumerate(letters):
        nb = [ord(c) - 65 for c in geo[L]]
        tab[9 * i:9 * i + len(nb)] = bytes(nb)
    return bytes(tab)


GEO_BOX = (35.4, 47.2, 6.5, 18.6)         # (Italy's bounding box: lat min / max, lon min / max, with Sicily, Sardinia and Lampedusa)


def geo_coords(pk):
    """4.2 Serie D geography, town coordinates (MC / Davide 14/11): clubs.csv 'lat' / 'lon' (decimal degrees of the club's town) ->
    [(lat, lon) in 0.01 degree, (0, 0) = none] per ident. No such columns: REFUSED (MC 14/11), except under the test switch S7_GEO_NOCOORD (None: the movers stay the lowest row).
    With the columns, EVERY club of the Serie D file and of the pool must have one inside GEO_BOX: refused otherwise."""
    rows = list(pk.clubs.values())
    if not any('lat' in r or 'lon' in r for r in rows):
        if os.environ.get('S7_GEO_NOCOORD'):             # (test builds only - modver.BUILD_SWITCHES: buildrel clears it: the lowest-row control)
            import modver
            assert modver.is_test()
            return None
        raise SystemExit("s7swap: clubs.csv has no lat / lon columns (4.2 Serie D geography: the town coordinates are required, Davide "
                         "14/11): a GP_S7 build is refused; regenerate the pack with tools/s7pack.py (tools/s7pack_towns.csv)")
    out, bad = [], []
    for r in rows:
        la, lo = (r.get('lat') or '').strip(), (r.get('lon') or '').strip()
        need = r.get('file') in ('league_b', 'pool')
        if not la and not lo:
            out.append((0, 0))
            if need:
                bad.append((r['key'], 'no coordinate'))
            continue
        try:
            fla, flo = float(la), float(lo)
        except ValueError:
            raise SystemExit(f"s7swap: clubs.csv {r['key']}: lat / lon not numbers ({la!r}, {lo!r})")
        if not (GEO_BOX[0] <= fla <= GEO_BOX[1] and GEO_BOX[2] <= flo <= GEO_BOX[3]):
            bad.append((r['key'], f'{fla}, {flo} outside Italy'))
        out.append((round(fla * 100), round(flo * 100)))
    if bad:
        raise SystemExit(f"s7swap: clubs.csv coordinates refused ({len(bad)}): {bad[:8]}")
    return out


def patch(p, ssyms, rsyms, gsyms, pgsyms, fsyms, risyms):
    """links s7swap.c at obj4+S7SWAP_AT (ssyms swe.c's, rsyms sreg.c's, gsyms gplay's, pgsyms pgroups', fsyms swefile's,
    risyms ripool's); returns the end, or None (dormant)."""
    if not on():
        return None
    import cobj
    import mkseason
    import swreg
    pk = next(pk for pk in mkseason.packs() if getattr(pk, 'ko_external', None))
    fa, fb, up, lo, gb, area = tables(pk)
    assert len(area) <= NID, ('s7swap: idents past S7_NID', len(area))
    assert 'S7_PTR' in pgsyms, 's7swap: pg_fix without its S7 call (pgroups.py S7_ON)'
    assert p.le.obj(4).npages * 0x1000 >= page_end(), 's7swap: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.S7SWAP_AT, swreg.S7SWAP_END - swreg.S7SWAP_AT)), 's7swap: obj4+S7SWAP_AT not free'
    assert 'S7_LPTR' in risyms, 's7swap: ri_load without its S7 call (ripool.py S7_ON)'
    assert 'S7_ORIG' in ssyms, 's7swap: swe.c without S7_ORIG (swe.py S7_ORIG_SZ)'
    home, nrec = homes(pk)
    assert len(home) == len(area) and set(nrec) == {fa, fb}, ('s7swap: homes', len(home), nrec)
    pool0, npool = pool_order(pk, home)
    assert not npool or (npool <= 255 and pool0 + npool <= len(home)), ('s7swap: pool', pool0, npool)
    pk_ri = [k for k in range(8) if risyms.get(f'RI_F{k}') and risyms[f'RI_F{k}'][1] == fb]
    assert len(pk_ri) == (1 if npool else len(pk_ri)) and not [k for k in range(8) if risyms.get(f'RI_F{k}') and risyms[f'RI_F{k}'][1] == fa], \
        ('s7swap: ripool must pool the lower file only (s7_load: RI_POOL of FB)', pk_ri)
    lay = orig_layout([nrec[fa], nrec[fb]])
    built = pk.team_files()                             # (MC 13/11: S7_ORIG_SZ against the files as built)
    for f in (fa, fb):
        d = built[f]
        assert len(d) == 2 + 684 * nrec[f] and d[0] << 8 | d[1] == nrec[f], ('s7swap: team file as built', f, len(d), nrec[f])
    stem = mkseason.ns_stem(pk.world).upper()
    names = [f'DATA\\{stem}.{f:03d}' for f in (fa, fb)]
    ext = {'S7X': gsyms['S7X'], 'SREG_REG': rsyms['SREG_REG'], 'sreg_get': rsyms['sreg_get'], 'SREG_FLAGS': rsyms['SREG_FLAGS'],
           'SWE_ARENA_AT': ssyms['SWE_ARENA_AT'], 'cstack_call': ssyms['cstack_call'], 'S7_ORIG': ssyms['S7_ORIG']}
    ext.update({k: fsyms[k] for k in ('swe_fopen_r', 'swe_fread', 'swe_fclose')})
    import trailer
    ext.update({'S7_NUMSEL': trailer.INFO['NUMSEL'], 'S7_SELBASE': (1, trailer.INFO['selbasev']),
                'S7_ENI': (1, trailer.INFO['en_items']), 'S7_CFB': trailer.INFO['CAREER']})
    import careerworld
    import dplay
    import gplay
    sel = careerworld.SITES['nc']['selteam']
    assert sel[0] == 2 and gplay._cardiv(p) == sel[1] + 6, ('s7swap: selTeamNumber / careerTeamLeague / D6CDC not '
                                                            'adjacent (obj2 +0 / +4 / +6)', sel, hex(gplay._cardiv(p)))
    ext.update({'S7_SELTEAM': sel, 'S7_CTLEAGUE': (2, sel[1] + 4), 'S7_CTEAM': (2, dplay._sites(p)[5])})
    flags = (f'-DS7_NID={NID}',)
    if os.environ.get('S7_LDFAIL'):                     # (test builds: the n-th s7_load's ORIG read fails once)
        import modver
        assert modver.is_test()
        flags += (f"-DS7_LDFAIL={int(os.environ['S7_LDFAIL'])}",)
    if os.environ.get('S7_NOSWAP'):                     # (test builds: the season end swaps nothing - the control career)
        import modver
        assert modver.is_test()
        flags += ('-DS7_NOSWAP=1',)
    import xtra
    if 'xcache' in xtra.LABELS:                         # (the market's XTRA cache: flushed when the registry moved clubs)
        flags += (f'-DS7_XNC={xtra.NC}', f'-DS7_XENT={xtra.ENT}')
        ext['S7_XCACHE'] = (1, xtra.LABELS['xcache'])
        flags += ('-DS7_XT=1',)
        ext['S7_XTEAM'] = (1, xtra.LABELS['xteam'])
    import xleft
    if 'xlbt' in xleft.LABELS:                          # (xl_find's cached block: the same)
        flags += ('-DS7_XLB=1',)
        ext['S7_XLBT'] = (3, xleft.LABELS['xlbt'])
    import cupd                                         # (S7 cd_str: the other league file's strengths, s7ri.c S7RI_STR - Panchina 4a27315)
    sfo, srows = cupd.other_strengths(pk, fb)
    assert sfo == fa and 0 < len(srows) <= 256, ('s7swap: other_strengths', sfo, fa, len(srows))
    flags += (f'-DS7RI_NSTR={len(srows)}',)
    gobj = cobj.compile_c(SRC_GEO, (), sections=True)    # (4.2 geography: its own band, linked first: s7ri.c's reset of the log is an extern)
    gsy, gend, gbss = cobj.link(p, gobj, swreg.S7GEO_AT, (4, 0), limit=swreg.S7GEO_END - 256, text_obj=4,
                                roots=['s7geochain', 's7geo_ll', 's7rd_near', 'S7GEO_NEIGH', 'S7GEO_ON', 'S7GEO_LOG', 'S7GEO_NLOG', 'S7GEO_BAD', 'S7GEO_XY', 'S7GEO_HAVE',
                                       'S7GEO_FILE', 'S7GEO_BASE', 'S7GEO_IDENT'])
    assert not gbss, ('s7geo.c: no .bss', gbss)
    ext['S7GEO_NLOG'] = gsy['S7GEO_NLOG'][:2]
    obj = cobj.compile_c(SRC, flags, sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.S7SWAP_AT, (4, 0), externs=ext, limit=swreg.S7SWAP_END, text_obj=4,
                               roots=['s7_season', 's7_load', 's7_home_word', 's7_ident', 's7_poolk', 's7ri_pool', 's7ri_cdstr', 'S7RI_STR', 'S7RI_STRF', 's7_snap', 'S7_DIR', 'S7_NDIR', 'RI_MOVES', 'RI_NMOVES', 'RI_S7_BAD', 'RI_HINTN', 'RI_HINTMAP', 'RI_FRESH', 'S7_POOL0', 'S7_NPOOL', 'S7_RIPOOL', 'S7_RSNAME', 'S7_RIMV', 's7_flush', 'S7_HRUN', 'S7_FNV', 'S7_WLOG', 'S7_CLOG', 'WSITES', 'WS_KEYS', 'S7_ENN', 'S7_CFBLEN', 'S7_NAME', 'S7_OAT', 'S7_ONREC', 'S7_LD', 'S7_FA', 'S7_FB', 'S7_NUP', 'S7_NLO', 'S7_UP', 'S7_LO', 'S7_GB',
                                      'S7_AREA', 'S7_LOG', 's7_imp_walk', 'S7_AREG'] + LIB)
    assert not bss, ('s7swap.c: no .bss (it would land on swe.c\'s)', bss)
    p.put(*syms['S7_FA'], bytes((fa,)))
    p.put(*syms['S7RI_STRF'], struct.pack('<H', sfo))
    p.put(*syms['S7RI_STR'], b''.join(struct.pack('<H', x) for x in srows))
    p.put(*syms['S7_FB'], bytes((fb,)))
    p.put(*syms['S7_NUP'], bytes((len(up),)))
    p.put(*syms['S7_NLO'], bytes((len(lo),)))
    p.put(*syms['S7_UP'], bytes(up))
    p.put(*syms['S7_LO'], bytes(lo))
    p.put(*syms['S7_GB'], b''.join(struct.pack('<3H', *x) for x in gb))
    p.put(*syms['S7_AREA'], area)
    p.put(*syms['S7_POOL0'], struct.pack('<H', pool0))
    p.put(*syms['S7_NPOOL'], struct.pack('<H', npool))
    if npool:
        cobj.add_ptr(p, syms['S7_RIPOOL'][1], *risyms[f'RI_POOL{pk_ri[0]}'], 4)   # (obj4 dword -> ripool's RS records, obj2)
    assert not npool or risyms[f'RI_PSZ{pk_ri[0]}'][1] >= 2 + 684 * npool, ('s7swap: RI_POOL room', risyms[f'RI_PSZ{pk_ri[0]}'], npool)
    rsn = risyms[f'RI_RSNAME{pk_ri[0]}'][1].upper().replace('/', '\\') if npool else ''
    assert len(rsn) < 16, rsn
    p.put(*syms['S7_RSNAME'], rsn.encode() + b'\0')
    hr = home_runs(home)
    p.put(*syms['S7_HRUN'], b''.join(struct.pack('<HHBB2x', *r) for r in hr))
    for s, nm in enumerate(names):
        assert len(nm) < 16
        p.put(syms['S7_NAME'][0], syms['S7_NAME'][1] + 16 * s, nm.encode() + b'\0')
    p.put(*syms['S7_OAT'], struct.pack('<II', lay[0][0], lay[1][0]))
    p.put(*syms['S7_ONREC'], struct.pack('<HH', lay[0][1], lay[1][1]))
    cobj.add_ptr(p, risyms['S7_LPTR'][1], *syms['s7_load'], 1)     # (ri_load's dword in obj1 -> obj4)
    cobj.add_ptr(p, pgsyms['S7_PTR'][1], *syms['s7_season'], 1)   # (pg_fix's dword in obj1 -> obj4)
    cobj.add_ptr(p, rsyms['SREG_CHG'][1], *syms['s7_flush'], rsyms['SREG_CHG'][0])   # (a load / new career: the word caches)
    if 'S7_HPTR' in risyms:                             # (ri_home, xtra_readto's hook: a crossed club's XTRA block)
        cobj.add_ptr(p, risyms['S7_HPTR'][1], *syms['s7_home_word'], 1)
    import gplay
    dirs = pk.s7_direct()                               # (s7_snap's direct crossings: gplay.c's S7_DIRS before)
    assert 0 < len(dirs) <= 16 and all(len(z) == 4 for z in dirs), ('s7swap: S7_DIR', dirs)
    p.put(*syms['S7_DIR'], b''.join(bytes(z) for z in dirs))
    p.put(*syms['S7_NDIR'], bytes((len(dirs),)))
    geotab = geo_table(pk.meta, len(pk.meta['files']['league_b']['divisions']))   # (4.2 geography, MC 14/11: required, checked)
    p.put(*gsy['S7GEO_NEIGH'], geotab)
    p.put(*gsy['S7GEO_ON'], b'\x01')
    xy = geo_coords(pk)
    cobj.add_ptr(p, gsy['S7GEO_IDENT'][1], *syms['s7_ident'][:2], 4)       # (the registry ident of a club by its team word)
    p.put(*gsy['S7GEO_FILE'], struct.pack('<H', fb))
    p.put(*gsy['S7GEO_BASE'], struct.pack('<i', gb[1][0]))
    if xy is not None:
        assert len(xy) <= NID, ('s7swap: coordinates past S7_NID', len(xy))
        p.put(*gsy['S7GEO_XY'], b''.join(struct.pack('<hh', *v) for v in xy))
        p.put(*gsy['S7GEO_HAVE'], b'\x01')
    for k, f in (('GP_RIPOOL', 's7ri_pool'), ('GP_CDSTR', 's7ri_cdstr'), ('GP_S7SNAP', 's7_snap')):   # (gplay.c's two S7 hooks -> s7ri.c, Panchina's:
        assert k in gplay.LABELS, ('s7swap: gplay.c without', k)       # MC ruling (b), S7-only logic in obj4)
        cobj.add_ptr(p, gplay.LABELS[k][1], *syms[f], gplay.LABELS[k][0])
    assert 'GP_GEOCH' in gplay.LABELS, 's7swap: gplay.c without GP_GEOCH'     # (4.2 geography: gplay.c's pg_one hook -> the S7GEO band)
    cobj.add_ptr(p, gplay.LABELS['GP_GEOCH'][1], *gsy['s7geochain'][:2], gplay.LABELS['GP_GEOCH'][0])
    import stadium
    if 'st_hptr' in stadium.LABELS:                     # (st_find: a crossed club's stadium by its home word, obj3)
        cobj.add_ptr(p, stadium.LABELS['st_hptr'][1], *syms['s7_home_word'], stadium.LABELS['st_hptr'][0])
    import winners
    wnoff = bool(os.environ.get('S7_WNOFF'))            # (test builds: wn_disk left native - world_s7cross_winners' control)
    if wnoff:
        import modver
        assert modver.is_test()
    if 'wn_disk' in winners.LABELS and not wnoff:       # (the WINNERS page's disk names by the home word - MC 13/11)
        assert 'ri_wnhome' in risyms, 's7swap: a WINNERS page without ripool\'s ri_wnhome (S7 + XTRA)'
        wo, o = winners.LABELS['wn_disk']
        want = b'\x60\x89\xC6\x0F\xB6\xC0'           # pushad / mov esi, eax / movzx eax, al (p.get: chained hooks)
        assert p.get(wo, o, 6) == want, ('s7swap: wn_disk entry', p.get(wo, o, 6).hex())
        ro, ra = risyms['ri_wnhome']
        if wo == ro:
            p.put(wo, o, b'\xE8' + struct.pack('<i', ra - (o + 5)) + b'\x90')
        else:                                          # (4.2 OBJ1MV: winners in obj4, ri_wnhome in obj1: a rel32 fixup)
            p.put(wo, o, b'\xE8\0\0\0\0\x90')
            p.add_rel(wo, o + 1, ro, ra)
        WNL = {'WN_DISK': winners.LABELS['wn_disk'], 'WN_FN': winners.LABELS['WN_FN']}   # (host tests)
    else:
        WNL = {}
    LABELS.clear()
    LABELS.update(syms)
    LABELS.update({k: v for k, v in gsy.items() if k.startswith('S7GEO_')})   # (the S7GEO band's data: the harness's chain log)
    LABELS['S7GEO_NEAR'] = gsy['s7rd_near']             # (42-s7trap: sreg2.c's call; not 's7geo_ll' - cdkn.py would start reading that key)
    LABELS.update(WNL)
    if 'st_cur' in stadium.LABELS:
        LABELS.update(ST_FIND=stadium.LABELS['st_find'], ST_GT1=stadium.LABELS['GT1'], ST_TOP=stadium.LABELS['TOP'])
        LABELS['ST_CUR'] = stadium.LABELS['st_cur']    # (world_s7cross_*: the versus screen's current / home word pair)
    LABELS.update({k: ext[k] for k in ('S7_NUMSEL', 'S7_SELBASE', 'S7_CFB', 'S7_ENI', 'S7_SELTEAM', 'S7_CTLEAGUE', 'S7_CTEAM')})   # (host tests)
    print(f'exe: S7 swap builder (s7swap.c) obj4+{swreg.S7SWAP_AT:#x}..{end:#x} of {swreg.S7SWAP_END:#x}: structs '
          f'{fa} / {fb}, boundary levels {up} / {lo}, globals {gb}, {len(area)} idents (homes {hr}); S7_LOG obj4+{syms["S7_LOG"][1]:#x}; load apply: {names[0]} / {names[1]} '
          f'({nrec[fa]} / {nrec[fb]} records) in S7_ORIG, S7_LD obj4+{syms["S7_LD"][1]:#x}')
    return end
