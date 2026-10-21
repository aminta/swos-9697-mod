"""4.0: a green CARRIERA 2026-27 button on the main menu (Davide): CAREER's row split in two, CAREER on the left half
and the button on the right half (the two columns of the rows above), in every state of the menu (no contest, or
CONTINUE / SAVE shown: no room under LOAD OLD COMPETITION then, so not under it).

The main menu's entry 4 (SAVE DISK FILING: defined, always invisible, its string used nowhere else) becomes the button
at run time, set at both ends of CommonMenuExit: shown, at x 154 (as the right column) and CAREER's y, 150 x 16, in the
menus' green (colour 14, as CONTINUE ... and the game's green buttons), with its label, the links CAREER <-> button,
SEASON above, CONTINUE / LOAD OLD COMPETITION below, and its on-select function. CAREER moves to x 0 (the left column).
Builds without the World 2026-27 do not get it."""
import re
import struct

import nasmcave

LABEL = {'it': b'CARRIERA 2026-27', 'en': b'CAREER 2026-27', 'fr': b'CARRIERE 2026-27', 'de': b'KARRIERE 2026-27'}
X, W, H, GAP, GREEN = 162, 150, 16, 18, 14   # (x as the menu stores it: definition + 8)

SRC = """
mb_on:  mov [esi + 16h], ax             ; (replaced: LOAD OLD COMPETITION's y = CONTINUE's)
        jmp mb_set
mb_off: mov word [esi + 4], 0           ; (replaced: CONTINUE shown)
mb_set: pushad
        mov word [D0], 9                ; CAREER: the row's left half, its right link -> the button
        call CALC
        mov edi, [A0]
        mov word [edi + 14h], 8
        mov byte [edi + 9], 4
        mov byte [edi + 0Ah], 3         ; (up: OPTIONS, the left column)
        mov word [D0], 8                ; SEASON: down -> the button (the right column)
        call CALC
        mov edi, [A0]
        mov byte [edi + 0Bh], 4
        mov word [D0], 9
        call CALC
        mov edi, [A0]
        mov bp, [edi + 16h]
        mov word [D0], 4
        call CALC
        mov edi, [A0]
        mov word [edi + 4], 0           ; shown
        mov word [edi + 14h], X_
        mov [edi + 16h], bp
        mov word [edi + 18h], W_
        mov word [edi + 1Ah], H_
        mov word [edi + 1Eh], GREEN_
        mov dword [edi + 8], 0A08FF09h  ; left CAREER (9), right -, up SEASON (8), down CONTINUE / LOAD OLD (10)
        call .g
.g:     pop eax
        add eax, mb_lab - .g
        mov [edi + 26h], eax
        mov dword [edi + 2Ah], ONSELF
        popad
        ret

mb_lab: db LABEL_, 0
"""


def patch(p, at, lang, onsel=None):
    """The button's code at obj1 offset at; onsel = (1, obj1 offset) of its on-select function (None: CAREER's).
    Returns the end of the code."""
    c = p.le.obj_bytes(1)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    on = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x89\x46\x16\xc3', c, re.S)
          if c.find(b'\x66\xc7\x46\x04\x01\x00', m.start() - 200, m.start()) >= 0]
    off = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\xc7\x46\x04\x00\x00\xc3', c, re.S)
           if c.find(b'\x66\xc7\x46\x04\x00\x00', m.start() - 40, m.start()) >= 0]
    assert len(on) == 1, on
    on = on[0]
    off = min(x for x in off if x > on)              # (CommonMenuExit's other end, right after)
    assert off - on < 0x200, hex(off - on)
    a0 = fx[on + 2]
    d0 = [fx[on - 200 + m.start() + 3] for m in re.finditer(rb'\x66\xc7\x05....\x0b\x00', c[on - 200:on], re.S)]
    assert d0, 'mov word [D0], 11'
    call = [m.start() + on - 80 for m in re.finditer(rb'\xe8....\x8f\x05', c[on - 80:on], re.S)][-1]   # (call; pop D0)
    calc = call + 5 + struct.unpack_from('<i', c, call + 1)[0]
    src = SRC.replace('LABEL_', '"' + LABEL[lang].decode('latin-1') + '"')
    if not onsel:                                    # (CAREER's on-select function: the main menu's entry 9 in obj2,
        d2 = p.le.obj_bytes(2)                       # `dw 13 / dd offset CareerMenu` after its string's pointer)
        f2 = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 2}
        car = {'it': b'CARRIERA', 'en': b'CAREER', 'fr': b'CARRIERE', 'de': b'KARRIERE'}[lang]
        hit = [f2[s] for s in f2 if f2[s][0] == 1 and d2[s - 2:s] == b'\x0d\x00' and s - 6 in f2 and f2[s - 6][0] == 2
               and re.match(re.escape(car) + rb'[*\0]', d2[f2[s - 6][1]:f2[s - 6][1] + len(car) + 1])]
        assert len(set(hit)) == 1, hit
        onsel = hit[0]
    sym = {'D0': d0[0], 'A0': a0, 'CALC': (1, calc), 'GAP_': (0, GAP), 'X_': (0, X), 'W_': (0, W), 'H_': (0, H),
           'GREEN_': (0, GREEN)}
    sym['ONSELF'] = onsel
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for o, tobj, toff in fix:
        p.add_ptr(1, at + o, tobj, toff)
    p.put(1, on + 6, b'\xe9' + struct.pack('<i', lab['mb_on'] - (on + 11)))
    p.put(1, off + 6, b'\xe9' + struct.pack('<i', lab['mb_off'] - (off + 11)) + b'\x90\x90')
    print(f'exe: main menu button {LABEL[lang].decode()} at obj1+{at:#x} (hooks {on + 6:#x}, {off + 6:#x})')
    return at + len(code)
