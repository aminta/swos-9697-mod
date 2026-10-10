"""Automatic home/away kit choice (SetInGameTeamsPrimaryColors / GetTeamKitsSimilarityFactor).

The game scores how alike two kits look (5 or 2 points for each pair of clashing colours) and uses the first of
home-home, home-away, away-home, away-away that scores below 11. Many classic pairings never met in home kits
(Juventus-Milan, Milan-Inter, Inter-Juventus, Chelsea against Juventus, Newcastle or Manchester City).
Analysis of the colour adjacency graph: Daniele Bordes (DaniSwos), SWOS United forum thread "Home-Away kit
automatic selection". Variants tested on every same-country pairing with tools/kitsim.py (variant 'C').

Changes (all four languages, found by byte content):
 1. conflict tables (conflictingBasicTeamColorsTable, conflictingShortsTeamColorsTable): black no longer clashes
    with blue or green, blue no longer with light blue (far apart in the in-game palette, pal.256);
 2. GetTeamKitsSimilarityFactor bug: after the stripe-merge pass (a striped shirt checked again as its blended
    colour, e.g. red+black -> maroon) the loop start tests D0/D4, which then hold the 'converted' flags, not the
    shirt types, so the other striped team lost its stripes (Inter became all black). The two tests now read
    shirtType1/shirtType2 (same on the first pass);
 3. same-coloured shorts on both teams weigh 3 instead of 5.
"""
import re
import struct

import kitsim

TABLE_BYTES = 20


def patch(p):
    # 1. conflict tables (obj2)
    d2 = p.le.obj_bytes(2)
    new = kitsim.variants()['C']
    for old, rows in ((kitsim.BASIC, new.basic), (kitsim.SHORTS, new.shorts)):
        b = struct.pack('<10H', *old)
        at = d2.find(b)
        assert at >= 0 and d2.count(b) == 1, 'kit colour table'
        assert p.get(2, at, TABLE_BYTES) == b
        p.put(2, at, struct.pack('<10H', *rows))

    # 2. GetTeamKitsSimilarityFactor prologue:
    #    mov al,[D0]; mov [shirtType1],al; mov al,[D4]; mov [shirtType2],al
    #    cmp byte [D0],0; jnz; mov al,[D1]; mov [D2],al; cmp byte [D4],0; jnz
    d1 = p.le.obj_bytes(1)
    pat = re.compile(rb'\xA0....\xA2....\xA0....\xA2....\x80\x3D....\x00\x75.\xA0....\xA2....\x80\x3D....\x00\x75', re.S)
    hits = [m.start() for m in pat.finditer(d1)]
    assert len(hits) == 1, 'GetTeamKitsSimilarityFactor'
    o = hits[0]
    assert p.get(1, o, 4) == d1[o:o + 4]
    for cmp_at, st_at, d_at in ((o + 22, o + 6, o + 1), (o + 41, o + 16, o + 11)):
        assert p.target(1, cmp_at) == p.target(1, d_at)            # cmp byte [D0|D4], 0
        tobj, toff = p.target(1, st_at)                           # shirtType1|2
        p.retarget(1, cmp_at, tobj, toff)
        p.put(1, cmp_at, struct.pack('<I', toff))

    # 3. the last 'add similarityFactor, n' of the no-conflict sum (D3 vs D7: shorts vs shorts)
    sim = None
    adds = []
    for m in re.finditer(rb'\x66\xC7\x05....\x63\x00', d1[o:o + 0x200], re.S):   # mov similarityFactor, 99
        sim = p.target(1, o + m.start() + 3)
        break
    assert sim
    for m in re.finditer(rb'\x66\x83\x05....(.)', d1[o:o + 0x600], re.S):
        at = o + m.start()
        try:
            t = p.target(1, at + 3)
        except AssertionError:      # look-alike bytes without a fixup
            continue
        if t == sim:
            adds.append(at)
    imms = [d1[a + 7] for a in adds]
    assert imms == [1, 5, 5, 2, 5, 5, 2, 2, 2, 5], imms
    p.put(1, adds[-1] + 7, bytes([new.wshorts]))


# --- manual choice: a KITS button in the pre-match screen (playMatchMenu) ----------------------------------------------
# The packed playMatchMenu (obj2, ends with dw -999) is copied into the obj1 cave with one more entry, 68, appended
# (indices of the game's entries unchanged), and every reference to the original is retargeted to the copy. Entry 68:
# origin (0, -20) like the menu start (-998), screen x 30..88, y 1..11: the free top-left corner, right of the check/X
# sprite (entry 0, x 11..27) and left of the team name (entry 1, from x 90). Its text points at a fixed buffer, so a
# re-unpacked menu (back from VIEW OPPO / EDIT TACTICS) still shows the current choice. Entry 13 (first player) gets
# up -> 68; 68 has down -> 13. Fire cycles AUTO -> home-home -> home-away -> away-home -> away-away (D7 0..3 of
# SetInGameTeamColors: bit 1 = first team in its away kit, bit 0 = second team). SetInGameTeamsPrimaryColors uses a
# forced choice once and resets it to AUTO, so it survives the second human player's screen but never leaks into a
# later match. (First attempt, recycling the "COACH:" entry 4, failed: it is the coach name of the GIOCA line.)
LABELS = {
    'it': (b'MAGLIE AUTO', b'MAGLIE C-C', b'MAGLIE C-T', b'MAGLIE T-C', b'MAGLIE T-T'),
    'en': (b'KITS AUTO', b'KITS H-H', b'KITS H-A', b'KITS A-H', b'KITS A-A'),
    'fr': (b'TENUES AUTO', b'TENUES D-D', b'TENUES D-E', b'TENUES E-D', b'TENUES E-E'),
    'de': (b'TRIKOT AUTO', b'TRIKOT H-H', b'TRIKOT H-A', b'TRIKOT A-H', b'TRIKOT A-A'),
}
KITS_ENTRY = 68
BUTTON = (22, 21, 58, 10)       # packed x, y, width, height (screen = x + 8, y - 20): x 30..88
BUTTON_COLOR = 8                # as USE MATCH TEAM: blue to black, grey frame
ADD_ENTRY = True                # False: copy the menu unchanged (debugging)

BUTTON_ASM = r"""
kit_select:                             ; onSelect of entry 68 (fire)
    movzx eax, byte [kit_force]
    inc eax
    cmp eax, 5
    jb .s
    xor eax, eax
.s: mov [kit_force], al
    call set_label
    jmp DRAW_MENU

set_label:                              ; eax = choice: copy its label into kit_buf
    push esi
    push edi
    mov esi, [kit_labels + eax * 4]
    mov edi, kit_buf
.c: lodsb
    stosb
    or al, al
    jnz .c
    pop edi
    pop esi
    ret

kit_colors:                             ; replaces `mov eax, [A2]` at the start of SetInGameTeamsPrimaryColors
    movzx eax, byte [kit_force]
    or eax, eax
    jz .auto
    mov byte [kit_force], 0             ; one match only
    push eax
    xor eax, eax
    call set_label
    pop eax
    dec eax
    mov [D7], eax
    jmp SET_COLORS
.auto:
    mov eax, [A2]
    jmp SITPC + 5

kit_force: db 0
kit_buf: db LABEL0, 0
    times 12 - ($ - kit_buf) db 0
align 4
kit_labels: dd l0, l1, l2, l3, l4
l0: db LABEL0, 0
l1: db LABEL1, 0
l2: db LABEL2, 0
l3: db LABEL3, 0
l4: db LABEL4, 0
"""

MENU_HEAD = struct.pack('<IIhhhhhhh', 0, 9, -998, 0, -20, 3, 20, 16, 13)    # after the init/return pointers
MENU_TAIL = struct.pack('<hhhh', 0x42, 6, 0, 3)                             # sidePitchPositionsDefault follows
ENTRY13 = struct.pack('<hhhhh', 23, 33, 82, 8, 2) + bytes((0xFF, 38, 0xFF, 14)) + b'\0\0'


def _rel(d, c):
    return c + 5 + struct.unpack('<i', d[c + 1:c + 5])[0]


def button(p, at, lang):
    """KITS button + forced choice; cave code and the menu copy at obj1:at, returns the new cave end."""
    import nasmcave
    d = p.le.obj_bytes(1)
    d2 = p.le.obj_bytes(2)
    # DrawMenu: TogglePlayerCoach ends with `call SetVariableButtons; jmp DrawMenu`; SetVariableButtons is the caller of
    # ShowUseMatchTeamIfTraining right after `call SetGameStartButtonText` and before push [D0]; mov dword [D0], 7.
    calls = {}
    for c in range(len(d) - 5):
        if d[c] == 0xE8:
            calls.setdefault(_rel(d, c), []).append(c)
    hits = []
    for m in re.finditer(rb'\x66\xC7\x05....\x05\x00\xE8....\x8B\x35....\x66\xC7\x46\x04\x01\x00\x66\xA1', d, re.S):
        for c in calls.get(m.start(), []):
            if d[c - 5] == 0xE8 and d[c + 5:c + 7] == b'\xff\x35' and d[c + 11:c + 13] == b'\xc7\x05' \
                    and d[c + 17:c + 21] == b'\x07\0\0\0':
                hits.append(c - 5)
    assert len(hits) == 1, hits
    svb = hits[0]
    draw = {_rel(d, c + 5) for c in calls.get(svb, []) if d[c + 5] == 0xE9}
    assert len(calls[svb]) == 6 and len(draw) == 1, (len(calls[svb]), draw)
    # SetInGameTeamsPrimaryColors: mov eax,[A2]; mov [A0],eax; mov eax,[A3]; mov [A1],eax; 6 x push; call Measure...;
    # ... mov word [D7], 0; mov esi, [A6]; cmp byte [esi], 11; inc dword [A6]; jb SetInGameTeamColors
    m = [x.start() for x in re.finditer(rb'\xA1....\xA3....\xA1....\xA3....(\xFF\x35....){6}\xE8', d, re.S)]
    assert len(m) == 1, m
    sitpc = m[0]
    j = re.compile(rb'\x66\xC7\x05(....)\x00\x00\x8B\x35....\x80\x3E\x0B\xFF\x05....\x0F\x82', re.S).search(d, sitpc, sitpc + 0x100)
    d7 = p.target(1, j.start() + 3)
    set_colors = j.end() + 4 + struct.unpack('<i', d[j.end():j.end() + 4])[0]
    a2 = p.target(1, sitpc + 1)
    labels = LABELS[lang]
    assert all(len(t) <= 11 for t in labels)
    sym = {'DRAW_MENU': (1, draw.pop()), 'SET_COLORS': (1, set_colors), 'SITPC': (1, sitpc), 'D7': d7, 'A2': a2}
    for i, t in enumerate(labels):
        sym['LABEL%d' % i] = (0, "'%s'" % t.decode('ascii'))
    code, fix = nasmcave.assemble(BUTTON_ASM, at, sym)
    lab = nasmcave.labels(BUTTON_ASM, at, sym)
    assert not any(d[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    assert p.get(1, sitpc, 1) == b'\xA1'
    p.remove(1, sitpc + 1)
    p.put(1, sitpc, b'\xE9' + struct.pack('<i', lab['kit_colors'] - (sitpc + 5)))

    # packed playMatchMenu: [init, return] + MENU_HEAD ... dw 0, dw -999, then sidePitchPositionsDefault
    hs = [x.start() - 8 for x in re.finditer(re.escape(MENU_HEAD), d2)]
    assert len(hs) == 1, hs
    start = hs[0]
    end = d2.find(b'\0\0\x19\xfc' + MENU_TAIL, start) + 2                   # the dw -999
    assert start < end < start + 0x1000
    menu = bytearray(d2[start:end])
    e13 = menu.find(ENTRY13)
    assert e13 > 0 and menu.count(ENTRY13) == 1
    if ADD_ENTRY:
        menu[e13 + 12] = KITS_ENTRY                                        # up -> KITS
    x, y, w, h = BUTTON
    entry = struct.pack('<hhh', -998, 0, -20) + struct.pack('<hhhhh', x, y, w, h, 2) + bytes((0xFF, 0xFF, 0xFF, 13))
    entry += struct.pack('<hhhh', 4, BUTTON_COLOR, 8, 0)                   # colour; text type, flags (white small centre)
    buf_at = len(menu) + len(entry)
    entry += struct.pack('<Ih', 0, 13)                                     # text = kit_buf; onSelect, fire only
    sel_at = len(menu) + len(entry)
    entry += struct.pack('<Ih', 0, 0)                                      # = kit_select; end of entry
    menu += (entry if ADD_ENTRY else b'') + struct.pack('<h', -999)
    assert menu.count(b'\x19\xfc') >= 1 and len(menu) % 2 == 0
    ptrs = [(o - start, t_obj, t_off) for (s_obj, o, _, t_obj, t_off, *_r) in p.le.fixups()
            if s_obj == 2 and start <= o < end]
    if ADD_ENTRY:
        ptrs += [(buf_at, 1, lab['kit_buf']), (sel_at, 1, lab['kit_select'])]
    mat = (at + len(code) + 15) & ~15
    while any((mat + o) // 0x1000 != (mat + o + 3) // 0x1000 for o, _, _ in ptrs):
        mat += 4                                                           # no pointer may straddle a page
    assert not any(d[mat:mat + len(menu)])
    p.put(1, mat, bytes(menu))
    for o, t_obj, t_off in ptrs:
        p.add_ptr(1, mat + o, t_obj, t_off)
    refs = [(f[0], f[1]) for f in p.le.fixups() if (f[3], f[4]) == (2, start)]
    inner = [f for f in p.le.fixups() if f[3] == 2 and f[4] is not None and start < f[4] < end]
    assert refs and not inner, (refs, inner)
    for s_obj, s_off in refs:
        p.retarget(s_obj, s_off, 1, mat)
        p.put(s_obj, s_off, struct.pack('<I', mat))
    print(f'exe: KITS button: entry {KITS_ENTRY} of playMatchMenu (obj2+{start:#x}, {end - start} B) copied to '
          f'obj1+{mat:#x} ({len(refs)} refs), SetInGameTeamsPrimaryColors obj1+{sitpc:#x}, code obj1+{at:#x} ({len(code)} B)')
    return (mat + len(menu) + 15) & ~15
