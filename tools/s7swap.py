"""4.2 S7: the season-end swap builder (s7swap.c; internal/handoff/s7-swap-plan.md, MC 13/11) at obj4+swreg.S7SWAP_AT,
linked only with a registry shape (sreg.shape(): MC 13/11, = gplay.gp_s7(), asserted). Dormant: no byte. The registry
library (sr_reg_season + fill, sr_reg_ident / div / size, sr_wmap_*) lives here ONCE: the old-save import (SREG2, Panchina)
calls it here (LABELS) and never links its own copy.

Fills s7swap.c's tables from the shaped pack: S7_FA / S7_FB (the upper / lower struct's file), the boundary levels'
divisions (S7_UP: the upper struct's last level, S7_LO: the lower's first; group order), the two files' global runs
(S7_GB: base, the second run's first ordinal and base - G144), and S7_AREA per ident (sreg's ident order = clubs.csv):
low nibble the upper level's group, high nibble the lower level's (clubs.csv 'area', one entry per level of groups;
else the club's own group on that level; else F = none). pg_fix's S7_PTR (pgroups.py) -> s7_season."""
import os
import struct

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's7swap.c')
NID = 320                       # (s7swap.c S7_NID: S7_AREA's room)
LABELS = {}


LIB = ['sr_reg_season', 'sr_reg_ident', 'sr_reg_div', 'sr_reg_word', 'sr_reg_size', 'sr_reg_work_size', 'sr_wmap_build',
       'sr_wmap_get', 'sr_wmap_import']


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


def patch(p, ssyms, rsyms, gsyms, pgsyms):
    """links s7swap.c at obj4+S7SWAP_AT (ssyms swe.c's, rsyms sreg.c's, gsyms gplay's, pgsyms pgroups'); returns the
    end, or None (dormant)."""
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
    ext = {'S7X': gsyms['S7X'], 'SREG_REG': rsyms['SREG_REG'], 'sreg_get': rsyms['sreg_get'],
           'SWE_ARENA_AT': ssyms['SWE_ARENA_AT'], 'cstack_call': ssyms['cstack_call']}
    obj = cobj.compile_c(SRC, (f'-DS7_NID={NID}',), sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.S7SWAP_AT, (4, 0), externs=ext, limit=swreg.S7SWAP_END, text_obj=4,
                               roots=['s7_season', 'S7_FA', 'S7_FB', 'S7_NUP', 'S7_NLO', 'S7_UP', 'S7_LO', 'S7_GB',
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
    cobj.add_ptr(p, pgsyms['S7_PTR'][1], *syms['s7_season'], 1)   # (pg_fix's dword in obj1 -> obj4)
    LABELS.clear()
    LABELS.update(syms)
    print(f'exe: S7 swap builder (s7swap.c) obj4+{swreg.S7SWAP_AT:#x}..{end:#x} of {swreg.S7SWAP_END:#x}: structs '
          f'{fa} / {fb}, boundary levels {up} / {lo}, globals {gb}, {len(area)} idents; S7_LOG obj4+{syms["S7_LOG"][1]:#x}')
    return end
