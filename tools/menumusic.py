"""Menu music with SWOS++ (3.3.6; Marco): the music starts when the main menu opens with MENU MUSIC on.

The game starts the menu music (TryMidiPlay: menu.xmi through the MDI driver) only in LoadTitleAndStartMusic, before
the main menu, and only if g_menuMusic is on. SWOS++ loads the game's options from its SWOSPP.XML later, inside
InitMainMenuStuff (its hook at +0x114): at that check g_menuMusic is still 0, so the music stays off although the
option shows ON (it started after a match, when the game restarts it). InitMainMenu's `call InitMainMenuStuff` becomes
`call mm_init`: the same call, then TryMidiPlay when g_menuMusic is on. TryMidiPlay does nothing when the music is
already playing (g_midiPlaying) or the sound driver is off (g_musicOff): without SWOS++ nothing changes.
"""
import re
import struct

import nasmcave

ASM = r"""
mm_init:                                ; replaces `call InitMainMenuStuff` in InitMainMenu
    call MAIN_STUFF
    cmp word [MENU_MUSIC], 0
    je .out
    call TRY_MIDI                       ; (no-op when already playing or the driver is off)
.out:
    ret
"""


def _rel(d, c):
    return c + 5 + struct.unpack('<i', d[c + 1:c + 5])[0]


def patch(p, at):
    """Code at obj1:at; returns its end."""
    d = p.le.obj_bytes(1)
    # InitMainMenu: mov word [cdAudioPlaying], 0 / call InitMenuMusic / call nullsub / call InitMainMenuStuff /
    # mov ax, [g_menuMusic] / or ax, ax / jz
    m = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x00\x00\xe8....\xe8....\xe8....\x66\xa1....\x66\x0b\xc0\x74',
                                        d, re.S)]
    assert len(m) == 1, m
    site = m[0] + 19                                    # call InitMainMenuStuff
    menu_music = p.target(1, m[0] + 26)
    # TryMidiPlay: cmp word [g_musicOff], 1 / jz / mov ax, [g_midiPlaying] / or ax, ax / jnz / mov eax, [buf] / call
    t = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x01\x74.\x66\xa1....\x66\x0b\xc0\x75.\xa1....\xe8', d, re.S)]
    assert len(t) == 1, t
    assert p.get(1, site, 5) == d[site:site + 5] and d[site] == 0xE8
    at = (at + 15) & ~15
    sym = {'MAIN_STUFF': (1, _rel(d, site)), 'MENU_MUSIC': menu_music, 'TRY_MIDI': (1, t[0])}
    code, cfix = nasmcave.assemble(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.put(1, site, b'\xE8' + struct.pack('<i', at - (site + 5)))
    print(f'exe: menu music at the main menu (InitMainMenu obj1+{site:#x}, code obj1+{at:#x})')
    return at + len(code)
