"""Menu music with SWOS++ (3.3.6; Marco): the music starts when the main menu opens with MENU MUSIC on.

The game starts the menu music (TryMidiPlay: menu.xmi through the MDI driver) only in LoadTitleAndStartMusic, before
the main menu, and only if g_menuMusic is on. SWOS++ loads the game's options from its SWOSPP.XML later, inside
InitMainMenuStuff (its hook at +0x114): at that check g_menuMusic is still 0, so the music stays off although the
option shows ON (it started after a match, when the game restarts it). InitMainMenu, after InitMainMenuStuff, already
tests g_menuMusic on and g_musicOff off before starting the CD track: its `mov al, 2 / call CDROM_Seek` becomes
`call mm_cd`: TryMidiPlay, then the same CDROM_Seek. TryMidiPlay does nothing when the music is already playing
(g_midiPlaying): without SWOS++ nothing changes. Relative calls only: no fixup (the LE header padding is short).
"""
import re
import struct

import nasmcave

ASM = r"""
mm_cd:                                  ; replaces `mov al, 2 / call CDROM_Seek` in InitMainMenu (menu music on)
    call TRY_MIDI                       ; (no-op when already playing)
    mov al, 2
    jmp CD_SEEK
"""


def _rel(d, c):
    return c + 5 + struct.unpack('<i', d[c + 1:c + 5])[0]


def patch(p, at):
    """Code at obj1:at; returns its end."""
    d = p.le.obj_bytes(1)
    # InitMainMenu: ... call InitMainMenuStuff / mov ax, [g_menuMusic] / or ax, ax / jz / cmp word [g_musicOff], 1 / jz /
    # mov al, 2 / call CDROM_Seek / mov al, 2 / call CDROM_PlayAudio
    m = [x.start() for x in re.finditer(rb'\xe8....\x66\xa1....\x66\x0b\xc0\x74.\x66\x83\x3d....\x01\x74.'
                                        rb'\xb0\x02\xe8....\xb0\x02\xe8', d, re.S)]
    assert len(m) == 1, m
    site = m[0] + 26                                    # mov al, 2 / call CDROM_Seek (7 bytes)
    assert d[site:site + 2] == b'\xb0\x02' and p.get(1, site, 7) == d[site:site + 7]
    seek = _rel(d, site + 2)
    # TryMidiPlay: cmp word [g_musicOff], 1 / jz / mov ax, [g_midiPlaying] / or ax, ax / jnz / mov eax, [buf] / call
    t = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x01\x74.\x66\xa1....\x66\x0b\xc0\x75.\xa1....\xe8', d, re.S)]
    assert len(t) == 1, t
    at = (at + 15) & ~15
    sym = {'CD_SEEK': (1, seek), 'TRY_MIDI': (1, t[0])}
    code, cfix = nasmcave.assemble(ASM, at, sym)
    assert not cfix, cfix
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    p.put(1, site, b'\xE8' + struct.pack('<i', at - (site + 5)) + b'\x90\x90')
    print(f'exe: menu music at the main menu (InitMainMenu obj1+{site:#x}, code obj1+{at:#x})')
    return at + len(code)
