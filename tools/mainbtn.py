"""4.0: a green CARRIERA 2026-27 button on the main menu (Davide): CAREER's row split in two, CAREER on the left half
and the button on the right half (the two columns of the rows above), in every state of the menu (no contest, or
CONTINUE / SAVE shown: no room under LOAD OLD COMPETITION then, so not under it).

The main menu's entry 4 (SAVE DISK FILING: defined, always invisible, its string used nowhere else) becomes the button
at run time, set at both ends of CommonMenuExit: shown, at x 154 (as the right column) and CAREER's y, 150 x 16, in the
menus' green (colour 14, as CONTINUE ... and the game's green buttons), with its label, the links CAREER <-> button,
SEASON above, CONTINUE / LOAD OLD COMPETITION below, and its on-select function. CAREER moves to x 0 (the left column).
Builds without the World 2026-27 do not get it.
SWOS++ (English) also uses entry 4 for its own SWOS++ entry (shown at the top: x 93, y 21) and the main menu has no other
free entry (13: 10 / 11 are CONTINUE / SAVE). The button always keeps entry 4 (Davide, 30/10: the green rectangle stays
where it is in every case); SWOS++'s entry (copied from entry 4 the first time it is seen there, shown at another x) is
shown through entry 11 (SAVE) while no contest is loaded, at SWOS++'s place (top, x 93 y 21; FRIENDLY's up and its
down link to each other, CONTINUE's down -> LOAD OLD, LOAD OLD's up -> CAREER); with a contest CONTINUE / SAVE get 10 / 11
back (the game's entry 11 as copied, the game's links) - Davide's option 2."""
import re
import struct

import nasmcave

LABEL = {'it': b'CARRIERA 2026-27', 'en': b'CAREER 2026-27', 'fr': b'CARRIERE 2026-27', 'de': b'KARRIERE 2026-27'}
FLAG = [None]                                # (obj, offset) of mb_flag (1: the career came from the button)
X, W, H, GAP, GREEN = 162, 150, 16, 18, 14   # (x as the menu stores it: definition + 8)

SRC = """
mb_on:  mov [esi + 16h], ax             ; (replaced: LOAD OLD COMPETITION's y = CONTINUE's)
        jmp mb_set
mb_off: mov word [esi + 4], 0           ; (replaced: CONTINUE shown)
mb_set: pushad
        call .f
.f:     pop eax
        mov byte [eax + mb_flag - .f], 0   ; (back on the main menu: SELECT TEAM TO MANAGE opens at the top again)
        mov word [D0], 9                ; CAREER: the row's left half, its right link -> the button
        call CALC
        mov edi, [A0]
        cmp dword [edi + 2Ah], ONSELF   ; (only the main menu: its entry 9 is CAREER)
        jne .out
        call mb_spp_get                 ; (SWOS++'s own entry 4, before the button takes it)
        mov word [D0], 9
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
        add eax, mb_go - mb_lab
        mov [edi + 2Ah], eax
        call mb_spp_put                 ; (SWOS++'s entry through entry 11, or entry 11 back to SAVE)
.out:   popad
        ret

; 4.0.5 (Davide 30/10, option 2): under SWOS++ (English) its own entry 4 (the button's) is shown through entry 11
; (SAVE) while no contest is loaded - at SWOS++'s own place (top, x 93 y 21); with a contest CONTINUE / SAVE take 10 / 11
; back. Entry = 38h bytes: +2 its number, +4 invisible, +8 links (left, right, up, down), +14h x y w h, +26h label,
; +2Ah on-select.
mb_spp_get:                             ; entry 4 shown at another x than the button's = SWOS++'s: copy it once,
        push ebp                        ; with the game's entry 11 (SAVE) as it is (ebp: CalcMenuEntryAddress
        call .b                         ; clobbers eax, bx, dx)
.b:     pop ebp
        sub ebp, .b - mb_spp
        cmp byte [ebp + 70h], 0
        jne .r
        mov word [D0], 4
        call CALC
        mov esi, [A0]
        cmp word [esi + 4], 0
        jne .r
        cmp word [esi + 14h], X_
        je .r
        mov edi, ebp
        mov ecx, 0Eh
        rep movsd
        mov word [D0], 11
        call CALC
        mov esi, [A0]
        lea edi, [ebp + 38h]
        mov ecx, 0Eh
        rep movsd
        mov byte [ebp + 70h], 1
.r:     pop ebp
        ret

mb_spp_put:
        push ebp
        call .b
.b:     pop ebp
        sub ebp, .b - mb_spp
        cmp byte [ebp + 70h], 0
        je .r
        mov word [D0], 10
        call CALC
        mov eax, [A0]
        mov byte [ebp + 71h], 4         ; (a contest: CONTINUE shown - entry 11 = SAVE, FRIENDLY's up = the button)
        cmp word [eax + 4], 0
        je .on
        mov byte [ebp + 71h], 11        ; (none: entry 11 = SWOS++'s entry, FRIENDLY's up = it)
.on:    mov word [D0], 11
        call CALC
        mov edi, [A0]
        lea esi, [ebp + 38h]
        cmp byte [ebp + 71h], 11
        jne .copy
        mov esi, ebp
.copy:  push edi
        mov ecx, 0Eh
        rep movsd
        pop edi
        mov word [edi + 2], 11
        mov word [edi + 4], 0
        cmp byte [ebp + 71h], 11
        jne .f
        mov dword [edi + 8], 05FFFFFFh  ; (left, right, up: none; down: FRIENDLY)
.f:     mov word [D0], 5
        call CALC
        mov edi, [A0]
        mov al, [ebp + 71h]
        mov [edi + 0Ah], al
        mov word [D0], 12               ; LOAD OLD COMPETITION's up: SAVE (the game's) / CAREER under SWOS++'s entry
        call CALC
        mov edi, [A0]
        mov byte [edi + 0Ah], 11
        mov word [D0], 10               ; CONTINUE's down (followed while it is hidden: CAREER / the button go down
        call CALC                       ; through it): SAVE (the game's) / LOAD OLD COMPETITION under SWOS++'s entry
        mov esi, [A0]
        mov byte [esi + 0Bh], 11
        cmp byte [ebp + 71h], 11
        jne .r
        mov byte [edi + 0Ah], 9
        mov byte [esi + 0Bh], 12
.r:     pop ebp
        ret

mb_spp: times 72h db 0                  ; (SWOS++'s entry 4, the game's entry 11, +70h: copied, +71h: scratch)

mb_go:  push eax                         ; the button: CAREER's menu, its team choice opening in the World 2026-27
        call .g
.g:     pop eax
        mov byte [eax + mb_flag - .g], 1
        pop eax
        jmp ONSELF

mb_d0:  mov byte [D0], 0FFh             ; (replaced: SelectTeamsFinalMenu from the top list)
        push eax
        call .g
.g:     pop eax
        cmp byte [eax + mb_flag - .g], 0
        pop eax
        je .r
        cmp dword [HDR], STR            ; only SELECT TEAM TO MANAGE (not a player purchase's team choice)
        jne .r
        mov byte [D0], WID_             ; the world's list (CLASSIC CAREERS > WORLD 2026-27): its continents
.r:     ret

mb_flag: db 0
mb_lab: db LABEL_, 0
"""


def patch(p, at, lang, wid, onsel=None, obj=1):
    """The button's code at obj offset at (4.0.6: obj3's last page, else obj1); wid = the world's list id (mkseason.WMENU + its number); onsel = (1, obj1 offset) of its on-select function (None: CAREER's).
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
    src = nasmcave.sub(SRC, 'LABEL_', '"' + LABEL[lang].decode('latin-1') + '"')
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
    cs = [m.start() for m in re.finditer(rb'\xc6\x05....\xff\xe8....\x66\xa1', c, re.S)]   # ChooseTeamsDialog:
    assert len(cs) == 1, cs                                          # `mov byte [D0], 255; call SelectTeamsFinalMenu`
    cs = cs[0]
    hdr = [fx[cs - 0xd0 + k.start() + 6] for k in re.finditer(rb'\xa1....\xa3', c[cs - 0xd0:cs], re.S)][0]
    st = [fx[m.start() + 6] for m in re.finditer(rb'\xc7\x05........\xc7\x05....\x00\x00\x00\x00\x66\xc7\x05....'
                                                 rb'\x01\x00\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00\xe8', c, re.S)]
    st = [x for x in st if p.le.obj_bytes(2)[x[1]:x[1] + 1] != b'\0']
    sym.update({'HDR': hdr, 'STR': st[0], 'WID_': (0, wid)})
    import zones
    code = zones._put_obj(p, src, at, sym, obj)
    lab = nasmcave.labels(src, at, sym)
    p.branch(1, on + 6, 0xE9, obj, lab['mb_on'])
    p.branch(1, off + 6, 0xE9, obj, lab['mb_off'], n=7)
    p.remove(1, cs + 2)                              # (the overwritten instruction's fixup: [D0])
    p.branch(1, cs, 0xE8, obj, lab['mb_d0'], n=7)
    FLAG[0] = (obj, lab['mb_flag'])                  # (4.0.3: careerworld's nat_init reads it: the coach's list)
    print(f'exe: main menu button {LABEL[lang].decode()} at obj{obj}+{at:#x} (hooks {on + 6:#x}, {off + 6:#x})')
    return at + len(code)
