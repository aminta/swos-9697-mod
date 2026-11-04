"""The competition engine's object, obj4 (engine step O, PLAN §19; CONVENTIONS 23bis). obj4 is the engine's alone: the
4.0.x minors keep obj3 (rule 23), so the engine's layout never races their chain.

    obj4+0     header: 'SWOS-ENG', u32 version, u32 -> obj4+0 (a self pointer: the harness finds obj4 in memory by
               the magic and checks it), u32 -> swe_init, u32 -> the arena, u32 the .bss size, u32 -> SWE_STATE
    obj4+0x40  swe.c's code + data (OBJ4_PAGES file pages)
    +32        (step W) u32 -> the world registry (swreg.py, obj4+REG_AT), u32 -> reg_enter, u32 -> reg_leave,
               u32 -> SEL_MODE, u32 -> REG_PREV
    tail       swe.c's .bss (the arena): zero-filled vsize; DOS/4GW does not zero it, swe_init does

patch.py adds the object (lepatch.add_object + OBJ4_PAGES pages) after obj3's; patch(p) links swe.c, sizes obj4 and
puts its base above obj3's end.

Step W: the game's first call into the engine. GoGetTeamsForPlay (FRIENDLY and the 3 DIY editors: one picker) calls
SelectTeamsFinalMenu; that call (chained: whatever it reaches now) goes to swe_sel_tramp in obj4, which calls
swe_sel_pre(M_FRIENDLY), the picker, swe_sel_post. In step W they only keep competitionsTable[254] as it was: the
picker lists what it listed before (W-modes adds World 2026-27). obj1 changes by that call's rel32 only."""
import os
import struct

OBJ4_PAGES = 1
MAGIC = b'SWOS-ENG'
VERSION = 2                    # (swe.c SWE_VERSION; 2 = step W, the registry)
CODE_AT = 0x40
ARENA = 0x8000                 # (swe.c SWE_ARENA)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swe.c')
LABELS = {}


def pick_site(p):
    """obj1 offset of GoGetTeamsForPlay's `call SelectTeamsFinalMenu`: `mov byte [D0], 255; call ...; mov dword [A0], 0;
    call SetZeroFlag` (the one picker of FRIENDLY and the DIY tournament / cup / league editors)"""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    rg = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    ms = [m.start() + 7 for m in re.finditer(rb'\xc6\x05' + pk(rg['D7'] - 28) + rb'\xff\xe8.{4}\xc7\x05' + pk(rg['A0'])
                                             + rb'\x00\x00\x00\x00\xe8', d1, re.S)]
    assert len(ms) == 1, ms
    return ms[0]


def patch(p):
    """links swe.c into obj4 (after obj3's vsize / base are final), the world registry (swreg.py) and the picker's
    trampoline; returns the code's end"""
    import cobj
    import careerworld
    import swreg
    assert len(p.le.objs) == 4 and p.le.obj(4).npages == OBJ4_PAGES, 'obj4 not added (patch.py)'
    room = 0x1000 * OBJ4_PAGES
    site = pick_site(p)
    pick = p.call_target(1, site)                   # (chained: the picker call as earlier patches left it)
    ns = 'w_ns_set' in careerworld.LABELS and careerworld.NS.get('info')
    ext = {'SWE_REG': (4, swreg.REG_AT), 'SWE_PICK': pick}
    if ns:
        ext['w_ns_set'] = (1, careerworld.LABELS['w_ns_set'])
    flags = ('-DNS',) if ns else ()
    syms, end, bss = cobj.link(p, cobj.compile_c(SRC, flags), CODE_AT, (4, room), externs=ext, limit=swreg.REG_AT,
                               text_obj=4)
    arena = syms['SWE_ARENA_AT']
    assert arena[0] == 4 and bss >= ARENA
    p.put(4, 0, MAGIC + struct.pack('<I', VERSION))
    cobj.add_ptr(p, 12, 4, 0, 4)
    cobj.add_ptr(p, 16, *syms['swe_init'], 4)
    cobj.add_ptr(p, 20, *arena, 4)
    p.put(4, 24, struct.pack('<I', bss))
    cobj.add_ptr(p, 28, *syms['SWE_STATE'], 4)
    cobj.add_ptr(p, 32, 4, swreg.REG_AT, 4)
    for k, nm in enumerate(('reg_enter', 'reg_leave', 'SEL_MODE', 'REG_PREV')):
        cobj.add_ptr(p, 36 + 4 * k, *syms[nm], 4)
    swreg.patch(p, lambda off, tobj, toff: cobj.add_ptr(p, off, tobj, toff, 4))
    if p.rel_target(1, site + 1):
        p.remove(1, site + 1)
    p.add_rel(1, site + 1, *syms['swe_sel_tramp'])
    p.set_vsize(4, room + bss, bss=bss)
    p.set_base_after(4)
    LABELS.clear()
    LABELS.update({k: v for k, v in syms.items()})
    print(f'exe: obj4 (engine) code obj4+{CODE_AT:#x}..{end:#x} of {swreg.REG_AT:#x}, arena {bss:#x} B; the picker '
          f'call obj1+{site:#x} -> swe_sel_tramp obj4+{syms["swe_sel_tramp"][1]:#x} -> {pick[0]}:{pick[1]:#x}')
    return end
