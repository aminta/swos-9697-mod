"""The in-match bench menu's rows 18 px wider (4.0.6, Marco: the B2 layout, "symmetry!"): the card left of the face, the
injury cross in a column of its own before the position.

DrawSubstitutesMenuEntry draws every row of the bench menus (the substitutes list, FORMATION, oppl.py's opponent list,
benchx's long-bench pages): x = the row's left edge (subsMenuX - g_cameraX, 100 on the screen), the shadow at x
(126 x 11), the frame at x - 2 (126 x 11), the background at x - 1 (124 x 9), the face x..x+8, the card at x+9 (drawn
after the number: it hid the number's first digit, a one-digit number with the game's centred numbers), the number
ending at x+22 (subsnum.py), the name from x+24 (to x+108 at most), the injury-record cross at x+101 (over the end of a
13-14 letter name since subsnum's +6 px), the position centred at x+116; the FORMATION header text centred at x+63.
The small cards are 7 px + a 1 px shadow (measured on the screen: x-6 hid the face's first pixels). Now (LEFT 9,
RIGHT 9):
- the box from x-11 to x+132: the shadow's / frame's x (fw_x0, replacing `sub word [D0], ax` = subsMenuX - g_cameraX)
  and the background's (fw_x1, replacing `sub word [D0], 1`) LEFT px left, the widths (the immediates 126 / 124: the
  shadow / frame 144, the background 142) LEFT + RIGHT wider;
- the card at x-LEFT: one background pixel between the frame and the card, one between the card's shadow and the face;
- the record cross at x+CROSS (fw_cross, replacing `add word [D1], 101`; 7 px + shadow), its own column between the name
  (to x+108) and the position, now centred at x+125;
- LEFT = RIGHT: the box's centre stays, the FORMATION text (x+63) and DrawSubstitutesMenu's picture box (x+43) too.
SWOS++ (English) writes four of these immediates itself when it starts (its own rows, 6 px wider to the right: the
shadow 132, the background 130, the card x+12, the position x+122) and hooks the number's text (+0x53b from the
shadow): the four stay plain immediates (it overwrites ours: its layout), and the three hooks keep the game's
geometry while it runs (menunum's SWOS++ byte, as oppl.py). The first build hooked the shadow's width instruction:
SWOS++'s byte landed in its nops (0x84, a `test` eating the next instruction).
oppl.py's opponent-name header row (op_ttl, the same box drawn by hand) uses LEFT / WIDE too.
"""
import re
import struct

import nasmcave

LEFT, RIGHT = 9, 9
WIDE = LEFT + RIGHT
CROSS = 111                     # the injury-record cross's x (the game's 101): 2 px after the name, 2 before the position

ASM = r"""
fw_x0:                                  ; the shadow's x: replaces `sub word [D0], ax` (subsMenuX - g_cameraX)
    sub [D0], ax
    jmp fw_left
fw_x1:                                  ; the background's x: replaces `sub word [D0], 1`
    sub word [D0], 1
fw_left:
    cmp byte [SWOSPP], 0FFh
    jne .r                              ; SWOS++ running: its own rows
    sub word [D0], FW_LEFT
.r:
    ret
fw_cross:                               ; the record cross's x: replaces `add word [D1], 101`
    add word [D1], 101
    cmp byte [SWOSPP], 0FFh
    jne .r
    add word [D1], FW_CROSS - 101
.r:
    ret
"""


def sites(p):
    """obj1 offsets of the bytes patched (the original exe's layout, every language: the same routine)."""
    import sacups
    d = p.le.obj_bytes(1)
    a0 = sacups.regs(d)['A0']
    D = {k: a0 - 32 + 4 * i for i, k in enumerate(('D0', 'D1', 'D2', 'D3', 'D4'))}
    pk = lambda x: re.escape(struct.pack('<I', x))
    one = lambda what, ms: (ms if len(ms) == 1 else (_ for _ in ()).throw(AssertionError((what, len(ms)))))[0]
    sh = one('shadow', [m.start() for m in re.finditer(rb'\x66\xc7\x05' + pk(D['D2']) + rb'\x7e\x00\x66\xc7\x05' + pk(D['D3'])
                                                       + rb'\x0b\x00\x66\xc7\x05' + pk(D['D4']) + rb'\x08\x00', d, re.S)])
    r = d[sh:sh + 0xA00]
    g = lambda what, pat: sh + one(what, [m.start() for m in re.finditer(pat, r, re.S)])
    s = {'SHADOW': sh,
         'BGX': g('bg x', rb'\x66\x83\x2d' + pk(D['D0']) + rb'\x01') + 7,
         'BGW': g('bg width', rb'\x66\xc7\x05' + pk(D['D2']) + rb'\x7c\x00\x66\xc7\x05' + pk(D['D3']) + rb'\x09\x00') + 7,
         'HDR': g('header text', rb'\x66\x83\x05' + pk(D['D1']) + rb'\x3f') + 7,
         'CARD': g('card x', rb'\x66\x83\x2d' + pk(D['D2']) + rb'\x01\x66\xa1....\x66\xa3' + pk(D['D1']) + rb'\x66\xa1....'
                   rb'\x66\x29\x05' + pk(D['D1']) + rb'\x66\xa1....\x66\x0b\xc0\x74.\x66\x83\x05' + pk(D['D1']) + rb'\x09') + 0x33,
         'CROSS': g('cross x', rb'\x66\x83\x05' + pk(D['D1']) + rb'\x65') + 7,
         'POS': g('position x', rb'\x66\x83\x05' + pk(D['D1']) + rb'\x74') + 7}
    s['PIC'] = one('picture box', [m.start() for m in re.finditer(rb'\x66\x83\x05' + pk(D['D0']) + rb'\x2b\x66\xa1' + pk(D['D2'])
                                                                  + rb'\x66\xa3' + pk(D['D1']) + rb'\x66\xc7\x05' + pk(D['D2'])
                                                                  + rb'\x29\x00', d, re.S)]) + 7
    x0 = sh - 19
    assert d[x0:x0 + 7] == b'\x66\x29\x05' + struct.pack('<I', D['D0']), 'formwide: the shadow x'
    s['X0'] = x0
    tac = [m.start() for m in re.finditer(rb'\x66\x81\x05' + pk(D['D0']) + rb'\xa1\x00\x66\x83\x2d' + pk(D['D2']) + rb'\x09'
                                         rb'(?:\xff\x35....){3}\xff\x35' + pk(a0 + 16), d, re.S)]
    s['SWOSPP'] = (1, one('tactics pitch', tac) + 0x23)        # (menunum / oppl: the byte SWOS++ rewrites)
    s['D0'], s['D1'] = (2, D['D0']), (2, D['D1'])
    return s


# (site, original byte, new byte): the immediates (SWOS++ rewrites all four)
def _bytes(s):
    return [(s['SHADOW'] + 7, 126, 126 + WIDE), (s['BGW'], 124, 124 + WIDE), (s['CARD'], 9, (-LEFT) & 0xff),
            (s['POS'], 116, 116 + RIGHT)]


def patch(p, at):
    """fw_x0 / fw_x1 / fw_cross at obj3:at; returns the end."""
    assert LEFT == RIGHT, 'the FORMATION text / picture box would need moving (HDR / PIC sites)'
    s = sites(p)
    d = p.le.obj_bytes(1)
    for site, old, new in _bytes(s):
        assert p.get(1, site, 1) == bytes([old]) == d[site:site + 1], ('formwide: byte already patched', hex(site))
        p.put(1, site, bytes([new]))
    sym = {'D0': s['D0'], 'D1': s['D1'], 'SWOSPP': s['SWOSPP'], 'FW_LEFT': (0, LEFT), 'FW_CROSS': (0, CROSS)}
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    assert not rel and not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    lab = nasmcave.labels(ASM, at, sym)
    for site, n, name in ((s['X0'], 7, 'fw_x0'), (s['BGX'] - 7, 8, 'fw_x1'), (s['CROSS'] - 7, 8, 'fw_cross')):
        assert bytes(p.get(1, site, n)) == d[site:site + n], ('formwide: site already patched', name, hex(site))
        p.remove(1, site + 3)
        p.branch(1, site, 0xE8, 3, lab[name], n)
    print(f'exe: formwide: bench menu rows {WIDE} px wider (card x-{LEFT}, cross x+{CROSS}, position x+{116 + RIGHT}; '
          f'the game\'s under SWOS++), obj1+{s["X0"]:#x}, obj3+{at:#x} ({len(code)} B)')
    return at + len(code)
