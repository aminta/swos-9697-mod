"""N7 piece 3 (Panchina 10/11, MC's GO): the club registry's code (sreg.c: the engine's sr_reg + sr_regsave) at
obj4+swreg.SREG_AT, under lrank.LR_AT, and its SWC1 section 'IT' (swe.c it_save / it_load; n7-s7-clubmap.md §2).

DORMANT until a world has a registry shape (S7: Italy's files 102 + 144, piece 4's pack data): shape() is None, sreg.c
is not linked, swe.c's SREG_FN stays 0, no 'IT' is written and SWC1 keeps its 32 B - a save is byte-identical to one
of the build before. SREG_FORCE=1 (test builds only, host tests): sreg.c linked with an empty shape the host test
pokes (italy42's), SWC1 sized for ITALY_ROWS."""
import os
import re

ITALY_ROWS = 298               # italy42 §2: files 102 + 144, every row (the identity map's size in a shaped save)
SECTION = 0x5449               # 'IT'
LABELS = {}                    # (hosttest: sreg.c's symbols)


def shape():
    """(files, divisions) of the world's registry, or None (no world has one before S7). files: [(file, [(div, size)],
    pool)]; divisions: each club's division byte in pack order (its ident)."""
    return None


def rows():
    s = shape()
    if s:
        return sum(sum(n for _, n in divs) + pool for _, divs, pool in s[0])
    return ITALY_ROWS if os.environ.get('SREG_FORCE') else 0


def section_bytes():
    """SWC1's room for 'IT' (its 4 B section header + sr_reg_save_size), 0 dormant."""
    n = rows()
    return 4 + 12 + (10 * n + 7) // 8 if n else 0


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
    roots = ['sreg_build', 'sreg_size', 'sreg_save', 'sreg_load', 'sreg_new', 'SREG_NF', 'SREG_NCLUB', 'SREG_SPEC',
             'SREG_REG', 'SREG_LAST']
    with open(os.path.join(os.path.dirname(src), 'swce', 'swosrules.h')) as h:
        ndiv = int(re.search(r'#define SR_REG_CLUBS (\d+)', h.read()).group(1))    # (SREG_DIV's bytes)
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
    syms, end, bss = cobj.link(p, obj, swreg.SREG_AT, (4, 0), externs={'SREG_DIV': (4, swreg.SREG_DIV_AT)},
                               limit=lrank.LR_AT, text_obj=4, roots=roots)
    syms['SREG_DIV'] = (4, swreg.SREG_DIV_AT)
    assert not bss and end <= lrank.LR_AT, ('sreg: code + data past LR_AT', hex(end), bss)
    cobj.add_ptr(p, syms['SREG_REG'][1], *syms_swe['SWE_ARENA_AT'], 4)   # (the registry: the engine arena's start)
    LABELS.clear()
    LABELS.update(syms)
    s = shape()
    assert not s, 'N7 piece 4: SREG_NF / SREG_NCLUB / SREG_SPEC / SREG_DIV (at SREG_DIV_AT) from the S7 shape'
    fn = syms_swe['SREG_FN']
    for k, nm in enumerate(('sreg_size', 'sreg_save', 'sreg_load', 'sreg_new', 'sreg_build')):
        cobj.add_ptr(p, fn[1] + 4 * k, *syms[nm], 4)
    print(f'exe: club registry (N7, sreg.c) obj4+{swreg.SREG_AT:#x}..{end:#x} of {lrank.LR_AT:#x}, SREG_DIV '
          f'obj4+{swreg.SREG_DIV_AT:#x}..{swreg.SREG_DIV_AT + ndiv:#x}; SWC1 \'IT\' '
          f'{section_bytes()} B ({rows()} rows{"" if s else ", SREG_FORCE: an empty shape"})')
    return end
