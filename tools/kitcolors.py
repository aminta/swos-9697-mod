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
# WIP, NOT ENABLED (playtest 2026-10-10): entries 3/4 are NOT unused. Code moves them at run time to the
# "GIOCA : <coach>" line (entry 4 = coach name), so the copied button appeared there over the coach name and the
# top-left corner stayed empty. Next attempt: a real extra entry (relocate playMatchMenu with one more entry), tested
# with the automated DOSBox-X harness (tools/swostest.py, other session) instead of manual playtests.
# The packed menu has two "COACH:" entries (3, 4) at y 221, below the screen, that no code touches. Every time
# SetVariableButtons runs (menu init and reinit, after each change) entry 4 becomes a copy of entry 5 ("USE MATCH TEAM",
# training only) moved to the free top-left corner, left of the team name (entry 1) and right of the check/X sprite
# (entry 0). Fire cycles AUTO -> home-home -> home-away -> away-home -> away-away (D7 0..3 of SetInGameTeamColors:
# bit 1 = first team in its away kit, bit 0 = second team). SetInGameTeamsPrimaryColors uses a forced choice once and
# resets it to AUTO, so the choice survives the second human player's screen but never leaks into a later match.
LABELS = {
    'it': (b'MAGLIE AUTO', b'MAGLIE C-C', b'MAGLIE C-T', b'MAGLIE T-C', b'MAGLIE T-T'),
    'en': (b'KITS AUTO', b'KITS H-H', b'KITS H-A', b'KITS A-H', b'KITS A-A'),
    'fr': (b'TENUES AUTO', b'TENUES D-D', b'TENUES D-E', b'TENUES E-D', b'TENUES E-E'),
    'de': (b'TRIKOT AUTO', b'TRIKOT H-H', b'TRIKOT H-A', b'TRIKOT A-H', b'TRIKOT A-A'),
}
BUTTON_DX = 58          # entry 4 x = team name x - 58 (screen x 32..86; check/X sprite at 11..27, name from 90)
BUTTON_W, BUTTON_H = 54, 10

BUTTON_ASM = r'''
kit_setup:                              ; replaces `call ShowUseMatchTeamIfTraining` in SetVariableButtons
    call SHOW_USE
    pushad
    push dword [D0]
    push dword [A0]
    mov dword [D0], 1                   ; team name
    call CALC
    push dword [A0]
    mov dword [D0], 5                   ; use match team (template)
    call CALC
    push dword [A0]
    mov dword [D0], 4                   ; unused "COACH:" entry -> KITS button
    call CALC
    mov edi, [A0]
    pop esi
    pop ebx
    mov dx, [edi + 2]                   ; keep its ordinal
    push edi
    mov ecx, 14                         ; 56-byte MenuEntry
    cld
    rep movsd
    pop edi
    mov [edi + 2], dx
    mov dword [edi + 4], 0              ; visible, enabled
    mov dword [edi + 8], 0x0DFFFFFF     ; left/right/up none, down = first player (13)
    mov ax, [ebx + 14h]
    sub ax, DX_
    mov [edi + 14h], ax                 ; x
    mov ax, [ebx + 16h]
    mov [edi + 16h], ax                 ; y
    mov word [edi + 18h], W_
    mov word [edi + 1Ah], H_
    movzx eax, byte [kit_force]
    mov eax, [kit_labels + eax * 4]
    mov [edi + 26h], eax                ; string
    mov dword [edi + 2Ah], kit_select   ; onSelect (fire only, from the template)
    mov dword [D0], 13
    call CALC
    mov esi, [A0]
    mov byte [esi + 0Ah], 4             ; first player: up -> KITS
    pop dword [A0]
    pop dword [D0]
    popad
    ret

kit_select:
    movzx eax, byte [kit_force]
    inc eax
    cmp eax, 5
    jb .s
    xor eax, eax
.s: mov [kit_force], al
    call SET_VAR_BUTTONS
    jmp DRAW_MENU

kit_colors:                             ; replaces `mov eax, [A2]` at the start of SetInGameTeamsPrimaryColors
    movzx eax, byte [kit_force]
    or eax, eax
    jz .auto
    mov byte [kit_force], 0             ; one match only
    dec eax
    mov [D7], eax
    jmp SET_COLORS
.auto:
    mov eax, [A2]
    jmp SITPC + 5

kit_force: db 0
align 4
kit_labels: dd l0, l1, l2, l3, l4
l0: db LABEL0, 0
l1: db LABEL1, 0
l2: db LABEL2, 0
l3: db LABEL3, 0
l4: db LABEL4, 0
'''


def _rel(d, c):
    return c + 5 + struct.unpack('<i', d[c + 1:c + 5])[0]


def button(p, at, lang):
    """KITS button + forced choice; cave code at obj1:at, returns the new cave end."""
    import nasmcave
    d = p.le.obj_bytes(1)
    calls = {}
    for c in range(len(d) - 5):
        if d[c] == 0xE8:
            calls.setdefault(_rel(d, c), []).append(c)
    # ShowUseMatchTeamIfTraining: mov word [D0], 5; call CalcMenuEntryAddress; mov esi, [A0]; mov word [esi+4], 1;
    # mov ax, [g_trainingGame]. Its call in SetVariableButtons follows `call SetGameStartButtonText` and precedes
    # push [D0]; mov dword [D0], 7 (view opponent).
    hits = []
    for m in re.finditer(rb'\x66\xC7\x05....\x05\x00\xE8....\x8B\x35....\x66\xC7\x46\x04\x01\x00\x66\xA1', d, re.S):
        for c in calls.get(m.start(), []):
            if d[c - 5] == 0xE8 and d[c + 5:c + 7] == b'\xff\x35' and d[c + 11:c + 13] == b'\xc7\x05' \
                    and d[c + 17:c + 21] == b'\x07\0\0\0':
                hits.append((m.start(), c))
    assert len(hits) == 1, hits
    show_use, hook = hits[0]
    svb = hook - 5
    d0, a0 = p.target(1, show_use + 3), p.target(1, show_use + 16)
    calc = _rel(d, show_use + 9)
    draw = {_rel(d, c + 5) for c in calls.get(svb, []) if d[c + 5] == 0xE9}     # TogglePlayerCoach: call SVB; jmp DrawMenu
    assert len(calls.get(svb, [])) == 6 and len(draw) == 1, (len(calls.get(svb, [])), draw)
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
    sym = {'SHOW_USE': (1, show_use), 'CALC': (1, calc), 'SET_VAR_BUTTONS': (1, svb), 'DRAW_MENU': (1, draw.pop()),
           'SET_COLORS': (1, set_colors), 'SITPC': (1, sitpc), 'D0': d0, 'A0': a0, 'D7': d7, 'A2': a2,
           'DX_': (0, BUTTON_DX), 'W_': (0, BUTTON_W), 'H_': (0, BUTTON_H)}
    for i, t in enumerate(labels):
        sym['LABEL%d' % i] = (0, "'%s'" % t.decode('ascii'))
    code, fix = nasmcave.assemble(BUTTON_ASM, at, sym)
    lab = nasmcave.labels(BUTTON_ASM, at, sym)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, hook + 1, struct.pack('<i', lab['kit_setup'] - (hook + 5)))
    assert p.get(1, sitpc, 1) == b'\xA1'
    p.remove(1, sitpc + 1)
    p.put(1, sitpc, b'\xE9' + struct.pack('<i', lab['kit_colors'] - (sitpc + 5)))
    print(f'exe: KITS button: SetVariableButtons call obj1+{hook:#x}, SetInGameTeamsPrimaryColors obj1+{sitpc:#x}, '
          f'code obj1+{at:#x} ({len(code)} B)')
    return (at + len(code) + 15) & ~15
