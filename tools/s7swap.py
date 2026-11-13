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
    return (swreg.S7SWAP_END + 0xFFF) & ~0xFFF


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
    rows = wsites.rows()
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
        elif iid == wsites.WI_CFB:
            size = trailer.INFO['FIXED'][1]
        else:
            assert iid in names, ('s7swap: WSITES row on an engine item this build does not save', k, item)
            size = engine.SAVE_ITEMS[names[iid]][0]
        assert off + max(count - 1, 0) * stride + 2 <= size, ('s7swap: WSITES row past its item', k, item, size)
    if 'ST' in engine.ITEM_AT:
        LABELS['ST_ITEM'] = engine.ITEM_AT['ST']          # (host tests: the TEST rows' engine item)
    print(f's7swap: WSITES {len(rows)} rows{" (TEST rows: S7_WSITES_TEST)" if wsites.TEST else ""}')


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
    lay = orig_layout([nrec[fa], nrec[fb]])
    built = pk.team_files()                             # (MC 13/11: S7_ORIG_SZ against the files as built)
    for f in (fa, fb):
        d = built[f]
        assert len(d) == 2 + 684 * nrec[f] and d[0] << 8 | d[1] == nrec[f], ('s7swap: team file as built', f, len(d), nrec[f])
    stem = mkseason.ns_stem(pk.world).upper()
    names = [f'DATA\\{stem}.{f:03d}' for f in (fa, fb)]
    ext = {'S7X': gsyms['S7X'], 'SREG_REG': rsyms['SREG_REG'], 'sreg_get': rsyms['sreg_get'],
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
    import xleft
    if 'xlbt' in xleft.LABELS:                          # (xl_find's cached block: the same)
        flags += ('-DS7_XLB=1',)
        ext['S7_XLBT'] = (3, xleft.LABELS['xlbt'])
    obj = cobj.compile_c(SRC, flags, sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.S7SWAP_AT, (4, 0), externs=ext, limit=swreg.S7SWAP_END, text_obj=4,
                               roots=['s7_season', 's7_load', 's7_home_word', 'S7_HRUN', 'S7_FNV', 'S7_WLOG', 'S7_CLOG', 'WSITES', 'WS_KEYS', 'S7_ENN', 'S7_CFBLEN', 'S7_NAME', 'S7_OAT', 'S7_ONREC', 'S7_LD', 'S7_FA', 'S7_FB', 'S7_NUP', 'S7_NLO', 'S7_UP', 'S7_LO', 'S7_GB',
                                      'S7_AREA', 'S7_LOG'] + LIB)
    assert not bss, ('s7swap.c: no .bss (it would land on swe.c\'s)', bss)
    p.put(*syms['S7_FA'], bytes((fa,)))
    p.put(*syms['S7_FB'], bytes((fb,)))
    p.put(*syms['S7_NUP'], bytes((len(up),)))
    p.put(*syms['S7_NLO'], bytes((len(lo),)))
    p.put(*syms['S7_UP'], bytes(up))
    p.put(*syms['S7_LO'], bytes(lo))
    p.put(*syms['S7_GB'], b''.join(struct.pack('<3H', *x) for x in gb))
    p.put(*syms['S7_AREA'], area)
    hr = home_runs(home)
    p.put(*syms['S7_HRUN'], b''.join(struct.pack('<HHBB2x', *r) for r in hr))
    for s, nm in enumerate(names):
        assert len(nm) < 16
        p.put(syms['S7_NAME'][0], syms['S7_NAME'][1] + 16 * s, nm.encode() + b'\0')
    p.put(*syms['S7_OAT'], struct.pack('<II', lay[0][0], lay[1][0]))
    p.put(*syms['S7_ONREC'], struct.pack('<HH', lay[0][1], lay[1][1]))
    cobj.add_ptr(p, risyms['S7_LPTR'][1], *syms['s7_load'], 1)     # (ri_load's dword in obj1 -> obj4)
    cobj.add_ptr(p, pgsyms['S7_PTR'][1], *syms['s7_season'], 1)   # (pg_fix's dword in obj1 -> obj4)
    if 'S7_HPTR' in risyms:                             # (ri_home, xtra_readto's hook: a crossed club's XTRA block)
        cobj.add_ptr(p, risyms['S7_HPTR'][1], *syms['s7_home_word'], 1)
    import stadium
    if 'st_hptr' in stadium.LABELS:                     # (st_find: a crossed club's stadium by its home word, obj3)
        cobj.add_ptr(p, stadium.LABELS['st_hptr'][1], *syms['s7_home_word'], stadium.LABELS['st_hptr'][0])
    LABELS.clear()
    LABELS.update(syms)
    if 'st_cur' in stadium.LABELS:
        LABELS.update(ST_FIND=stadium.LABELS['st_find'], ST_GT1=stadium.LABELS['GT1'], ST_TOP=stadium.LABELS['TOP'])
        LABELS['ST_CUR'] = stadium.LABELS['st_cur']    # (world_s7cross_*: the versus screen's current / home word pair)
    LABELS.update({k: ext[k] for k in ('S7_NUMSEL', 'S7_SELBASE', 'S7_CFB', 'S7_ENI', 'S7_SELTEAM', 'S7_CTLEAGUE', 'S7_CTEAM')})   # (host tests)
    print(f'exe: S7 swap builder (s7swap.c) obj4+{swreg.S7SWAP_AT:#x}..{end:#x} of {swreg.S7SWAP_END:#x}: structs '
          f'{fa} / {fb}, boundary levels {up} / {lo}, globals {gb}, {len(area)} idents (homes {hr}); S7_LOG obj4+{syms["S7_LOG"][1]:#x}; load apply: {names[0]} / {names[1]} '
          f'({nrec[fa]} / {nrec[fb]} records) in S7_ORIG, S7_LD obj4+{syms["S7_LD"][1]:#x}')
    return end
