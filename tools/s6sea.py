"""S6a (4.2, MC 16/11; was 4.3): world SEASONs' picker (s6sea.c), its own obj4 band swreg.S6_AT..S6_END after TKUI; swe.c keeps
the picker's mode rules only. Linked when the registry gives worlds M_SEASON (swreg.SEASON_WORLDS) and the build has
worlds; historic.CALLS[1] (SeasonMenu's picker call) is re-pointed from swe.c's swe_sea_tramp to s6_sea_tramp."""
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 's6sea.c')
FLOOR = 256                             # (MC 15/11: every release band >= 256 B left)
EXT = ('SEL_ON', 'SEL_DW', 'SEL_MODE', 'NS_LEFT', 'av_world', 'reg_world', 'sel_restore', 'swe_sel_pre', 'swe_sea_tramp')
LABELS = {}


def on():
    import mkseason
    import swreg
    return bool(swreg.SEASON_WORLDS and mkseason.worlds())


def page_end():
    import swreg
    return (swreg.S6_END + 0xFFF) & ~0xFFF


def patch(p, syms):
    """s6sea.c at obj4+S6_AT against swe.c's symbols (syms); the SeasonMenu picker call -> s6_sea_tramp"""
    import careerworld
    import cobj
    import historic
    import swreg
    assert historic.CALLS and 'W_SEAW' in careerworld.LABELS, 's6sea: SeasonMenu picker call / careerworld W_SEAW'
    assert p.le.obj(4).npages * 0x1000 >= swreg.S6_END, 's6sea: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.S6_AT, swreg.S6_END - swreg.S6_AT)), 's6sea: obj4 band not free'
    ext = {k: syms[k] for k in EXT}
    ext['SWE_SELECT'] = (1, historic._calls(p)[2])
    ext['CW_SEAW'] = (1, careerworld.LABELS['W_SEAW'])
    xs, end, bss = cobj.link(p, cobj.compile_c(SRC, ['-Oz']), swreg.S6_AT, (4, swreg.S6_END), externs=ext,
                             limit=swreg.S6_END - FLOOR, text_obj=4)
    assert bss == 0, 's6sea.c holds no state (no .bss: swe.c\'s)'
    cs = historic.CALLS[1]
    assert p.rel_target(1, cs + 1) and p.call_target(1, cs) == syms['swe_sea_tramp'], 's6sea: the call is swe_sea_tramp\'s'
    p.remove(1, cs + 1)
    p.add_rel(1, cs + 1, *xs['s6_sea_tramp'])
    LABELS.clear()
    LABELS.update(xs)
    LABELS['S6'] = (swreg.S6_AT, end)
    print(f'exe: world seasons (s6sea.c) obj4+{swreg.S6_AT:#x}..{end:#x} ({end - swreg.S6_AT} B of '
          f'{swreg.S6_END - swreg.S6_AT}, {swreg.S6_END - end} B left, floor {FLOOR}); SeasonMenu call obj1+{cs:#x}')
    return end
