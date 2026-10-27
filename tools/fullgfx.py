"""Full graphics always (4.0.2, Davide's MiSTer 27/10): no automatic half / EGA mode from SETUP.DAT's video speed.

Initialization, right after ReadSetupDat: `mov setupDatBuffer, 0 / cmp g_videoSpeedIndex, 85 / ja +9 / mov
setupDatBuffer, -1`: setupDatBuffer = EGA_graphics in the match, -1 = the half mode (16-colour planar sprites, fewer
details). INSTALL.EXE measured the speed on the PCs of 1996; GOG's factory SETUP.DAT has 10 and a slow core can measure
little, so today's machines played the half mode (and met the mod's half-mode bugs: MALEN, numbers 17..99, 4.0.2).
The `ja` becomes `jmp`: the speed byte stays as read (the menus' frame delay uses it), the /H and /F switches
(ReadCommandLineParameters, after this) and the low-memory rule (< 4.1 MB in the largest block -> half) are unchanged.
"""
import re

PAT = rb'\x66\xc7\x05....\x00\x00\x66\x83\x3d....\x55\x77.\x66\xc7\x05....\xff\xff'


def patch(p):
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(PAT, d1, re.S)]
    assert len(m) == 1, m
    site = m[0] + 17
    buf = p.target(1, m[0] + 3)
    assert p.target(1, m[0] + 22) == buf, 'the same setupDatBuffer'
    assert p.get(1, site, 1) == b'\x77'
    p.put(1, site, b'\xeb')
    print(f'exe: full graphics always (the speed <= 85 half mode skipped at obj1+{site:#x}; /H still half)')
    return buf
