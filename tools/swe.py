"""The competition engine's object, obj4 (engine step O, PLAN §19; CONVENTIONS 23bis). obj4 is the engine's alone: the
4.0.x minors keep obj3 (rule 23), so the engine's layout never races their chain.

    obj4+0     header: 'SWOS-ENG', u32 version, u32 -> obj4+0 (a self pointer: the harness finds obj4 in memory by
               the magic and checks it), u32 -> swe_init, u32 -> the arena, u32 the .bss size, u32 -> SWE_STATE
    obj4+0x40  swe.c's code + data (OBJ4_PAGES file pages)
    tail       swe.c's .bss (the arena): zero-filled vsize; DOS/4GW does not zero it, swe_init does

patch.py adds the object (lepatch.add_object + OBJ4_PAGES pages) after obj3's; patch(p) links swe.c, sizes obj4 and
puts its base above obj3's end. Nothing in the game calls the engine yet (step W)."""
import os
import struct

OBJ4_PAGES = 1
MAGIC = b'SWOS-ENG'
VERSION = 1
CODE_AT = 0x40
ARENA = 0x8000                 # (swe.c SWE_ARENA)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swe.c')
LABELS = {}


def patch(p):
    """links swe.c into obj4 (after obj3's vsize / base are final); returns the code's end"""
    import cobj
    assert len(p.le.objs) == 4 and p.le.obj(4).npages == OBJ4_PAGES, 'obj4 not added (patch.py)'
    room = 0x1000 * OBJ4_PAGES
    syms, end, bss = cobj.link(p, cobj.compile_c(SRC), CODE_AT, (4, room), limit=room, text_obj=4)
    arena = syms['SWE_ARENA_AT']
    assert arena[0] == 4 and bss >= ARENA
    p.put(4, 0, MAGIC + struct.pack('<I', VERSION))
    cobj.add_ptr(p, 12, 4, 0, 4)
    cobj.add_ptr(p, 16, *syms['swe_init'], 4)
    cobj.add_ptr(p, 20, *arena, 4)
    p.put(4, 24, struct.pack('<I', bss))
    cobj.add_ptr(p, 28, *syms['SWE_STATE'], 4)
    p.set_vsize(4, room + bss, bss=bss)
    p.set_base_after(4)
    LABELS.clear()
    LABELS.update({k: v for k, v in syms.items()})
    print(f'exe: obj4 (engine) code obj4+{CODE_AT:#x}..{end:#x} of {room:#x}, arena {bss:#x} B')
    return end
