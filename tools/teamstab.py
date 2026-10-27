"""teamsTable with room for every team ordinal (4.0.2, Davide: stray colours on the Serie D team choice).

The team choice lists (ChooseTeamsFriendlyInitFinish: the friendly / career choice, SelectTeamToManage, the domestic
buy's club list) colour a club's button by teamsTable[its record's teamOrdinal] (0 default, 1 red computer, 2 purple
player-coach, else blue coach; ChooseTeamsFriendlyCommon2 writes it when a team is picked). The table is 100 bytes
(cleared by a loop of 63h + 1), as no original team file holds 100 records; the mod's do (Italy 2026-27 TMW5.102: 256,
Brazil TMW5.162: 119): ordinals 100+ read teamsIndex, the list's own index bytes after it (CHISOLA red, CELLE VARAZZE
purple, MILAN FUTURO blue), and a friendly pick would write into it. The four `mov [Ax], offset teamsTable` (no other
reference, all four exes) point to a 256-byte zero-filled block in obj2's tail instead; the clear loop counts FFh.
"""
import re

BSS_SIZE = 0x100


def patch(p, bss):
    """Repoint teamsTable to obj2:bss (BSS_SIZE zero bytes)."""
    d1 = p.le.obj_bytes(1)
    clr = [m.start() for m in re.finditer(rb'\xc7\x05....(....)\x66\xc7\x05....\x63\x00', d1, re.S)]
    assert len(clr) == 1, clr                   # mov [A0], offset teamsTable / mov word [D0], 63h
    tobj, tt = p.target(1, clr[0] + 6)
    assert tobj == 2
    refs = [off for so, off, ty, to, toff, *_ in p.le.fixups() if to == 2 and toff is not None and tt <= toff < tt + 100]
    assert len(refs) == 4, refs
    assert all(p.target(1, o) == (2, tt) for o in refs), refs
    for o in refs:
        p.retarget(1, o, 2, bss)
        p.put(1, o, bss.to_bytes(4, 'little'))
    p.put(1, clr[0] + 17, b'\xff')              # 100 -> 256 bytes cleared
    print(f'exe: teamsTable obj2+{tt:#x} (100 B) -> obj2+{bss:#x} (256 B), {len(refs)} references')
