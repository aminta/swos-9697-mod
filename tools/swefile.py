"""4.2: the engine's file layer (swefile.h / swefile.c; internal/handoff/swe-file-layer.md), its own obj4 range
swreg.SWEFILE_AT..SWEFILE_END (page 18, MC 12/11). Dormant until a consumer sets swe.SWEFILE: no page, no byte (the
exe as without it). SWEFILE_TEST=1 builds link it with swef_selftest (past SWEFILE_END on page 18: test bytes) and
swe.c's buffers / SWEF_HOOK (swe_sel_pre calls it once: harness swefile_layer)."""
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swefile.c')
TEST = os.environ.get('SWEFILE_TEST') == '1'
MARGIN = 256                    # (MC 12/11: the release shape ends at least this far below SWEFILE_END)
LABELS = {}


def on():
    import swe
    return swe.SWEFILE or TEST


def page_end():
    """obj4's size with the range (patch.py's OBJ4_PAGES max line)"""
    import swreg
    return (swreg.SWEFILE_END + 0xFFF) & ~0xFFF


class _Rec:
    """a throwaway target for the release shape's link (its size only)"""
    class le:
        page_size = 0x1000

    def put(self, *a):
        pass

    def add_ptr(self, *a):
        pass

    def add_rel(self, *a):
        pass


def patch(p, ssyms):
    """links swefile.c at obj4+SWEFILE_AT (ssyms: swe.c's symbols, for the test build's buffers / hook); returns the
    release shape's end"""
    import cobj
    import swreg
    import modver
    at = swreg.SWEFILE_AT
    assert getattr(swreg, 'KITS_END', at) <= at < swreg.SWEFILE_END, 'swreg: KITS_END <= SWEFILE_AT < SWEFILE_END'
    assert p.le.obj(4).npages * 0x1000 >= page_end(), 'swefile: obj4 pages (patch.py)'
    _, rel_end, rel_bss = cobj.link(_Rec(), cobj.compile_c(SRC), at, (4, 0), limit=swreg.SWEFILE_END - MARGIN, text_obj=4)
    assert not rel_bss, 'swefile.c: no .bss (it would land on swe.c\'s)'
    if TEST:
        assert modver.is_test(), 'SWEFILE_TEST: test builds only'
        ext = {k: ssyms[k] for k in ('SWEF_BIG', 'SWEF_RB')}
        syms, end, bss = cobj.link(p, cobj.compile_c(SRC, ('-DSWEFILE_TEST',)), at, (4, 0), externs=ext,
                                   limit=page_end(), text_obj=4)
        assert not bss
        cobj.add_ptr(p, ssyms['SWEF_HOOK'][1], *syms['swef_selftest'], 4)
    else:
        syms, end, bss = cobj.link(p, cobj.compile_c(SRC), at, (4, 0), limit=swreg.SWEFILE_END - MARGIN, text_obj=4)
        assert end == rel_end
    LABELS.clear()
    LABELS.update(syms)
    print(f'exe: engine file layer (swefile.c): obj4+{at:#x}..{rel_end:#x} ({rel_end - at} B, '
          f'{swreg.SWEFILE_END - rel_end} B left to SWEFILE_END {swreg.SWEFILE_END:#x})'
          + (f'; SWEFILE_TEST self-test to obj4+{end:#x}, hook SWEF_HOOK obj4+{ssyms["SWEF_HOOK"][1]:#x}' if TEST else ''))
    return rel_end
