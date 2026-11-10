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
back (the game's entry 11 as copied, the game's links) - Davide's option 2.

W-modes M1 (Davide 04/11): the button no longer starts a career. It is the default-world switch: its label is the
setting (MONDO: 2026-27 / MONDO: 1996-97 / EUROPA 1984-85, per language), fire cycles it and writes SETUP.DAT +105 at
once (only that byte: the controls stay as on disk; no file or a short one: the game's buffer, 106 B). CAREER's
on-select (entry 9) becomes mb_car: its team choice opens in the default world's list (World 2026-27 / Europe 1984-85
in CLASSIC CAREERS) or, with 1996-97, at the top as the game's.

4.1 (Marco, Davide 06/11): the patcher's 'Original main menu' option sets mb_omm (after the OMM_MARK marker) in the
output exes: the button is not set up (the game's main menu, SWOS++'s entry 4 as SWOS++ shows it, CAREER the game's),
modver's 'MOD x.y' line is not drawn, and the default world reads as the 1996-97 game whatever SETUP.DAT +105 holds
(swe.c set_w; the file is not touched, so the option OFF again gives back the saved default)."""
import re
import struct

import nasmcave

# W-modes M1 (Davide 04/11): the button is the default-world switch; its label = the setting (SETUP.DAT +105: 0 World
# 2026-27 - also a 105-B file / a fresh install -, 1 the 1996-97 game, 2 Europe 1984-85). A partial world is named by
# its real scope (EUROPA, not MONDO).
WORLD = {'it': (b'MONDO: 2026-27', b'MONDO: 1996-97', b'EUROPA 1984-85'),
         'en': (b'WORLD: 2026-27', b'WORLD: 1996-97', b'EUROPE 1984-85'),
         'fr': (b'MONDE: 2026-27', b'MONDE: 1996-97', b'EUROPE 1984-85'),
         'de': (b'WELT: 2026-27', b'WELT: 1996-97', b'EUROPA 1984-85')}
SET_OFF = 105                                # the default world's byte in SETUP.DAT / setupDatBuffer
LAB_W = 17                                   # (a label's slot: 16 chars + 0)
CHOOSE = [None]                              # (W-modes M3) {'site': obj1 offset of ChooseTeamsDialog's picker call,
                                             # 'HDR' / 'STR': (obj, off) as mb_d0's check} (swe.py)
FLAG = [None]                                # (obj, offset) of mb_flag (the career's world: 0 the game's, 1 World
SETTING = [None]                             # 2026-27, 2 Europe 1984-85); SETTING: (obj, offset) of the byte
OMM = [None]                                 # (obj, offset) of mb_omm, the patcher's 'Original main menu' byte
OMM_MARK = b'SWOSMOD-OMM'                    # (right before it in the exe: mkpatcher finds it there)
X, W, H, GAP, GREEN = 162, 150, 16, 18, 14   # (x as the menu stores it: definition + 8)

SRC = """
mb_on:  mov [esi + 16h], ax             ; (replaced: LOAD OLD COMPETITION's y = CONTINUE's)
        jmp mb_set
mb_off: mov word [esi + 4], 0           ; (replaced: CONTINUE shown)
mb_set: pushad
        call .f
.f:     pop eax
        mov byte [eax + mb_flag - .f], 0   ; (back on the main menu: SELECT TEAM TO MANAGE opens at the top again)
        cmp byte [eax + mb_omm - .f], 0    ; the patcher's 'Original main menu': the game's menu as it is
        jne .out
        mov word [D0], 9                ; CAREER: the row's left half, its right link -> the button
        call CALC
        mov edi, [A0]
        cmp dword [edi + 2Ah], ONSELF   ; (only the main menu: its entry 9 is CAREER, its on-select the game's or
        je .main                        ; ours, mb_car)
        call .k
.k:     pop eax
        add eax, mb_car - .k
        cmp [edi + 2Ah], eax
        jne .out
.main:
        call mb_spp_get                 ; (SWOS++'s own entry 4, before the button takes it)
        mov word [D0], 9
        call CALC
        mov edi, [A0]
        mov word [edi + 14h], 8
        call .h
.h:     pop eax
        add eax, mb_car - .h
        mov [edi + 2Ah], eax            ; (CAREER: the default world's career)
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
        call mb_wsel
        call mb_lbl
        mov [edi + 26h], eax            ; (the default world's name)
        call .g
.g:     pop eax
        add eax, mb_go - .g
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

mb_car: pushad                          ; CAREER: its team choice opens in the default world (mb_d0)
        call mb_wsel
        cmp al, 1
        ja .f
        xor al, 1                       ; (setting 0 World 2026-27 -> flag 1, setting 1 the game's -> 0; 2 stays)
.f:     call .g
.g:     pop edx
        mov [edx + mb_flag - .g], al
        popad
        jmp ONSELF

mb_go:  pushad                          ; the button: the next world, written to SETUP.DAT at once, its label shown
        call mb_wsel
        inc eax
        cmp eax, MAXW_
        jbe .s
        xor eax, eax
.s:     mov [BUF + SET_OFF_], al
        call mb_wfile
        call mb_wsel
        call mb_lbl
        push eax
        mov word [D0], 4
        call CALC
        mov edi, [A0]
        pop dword [edi + 26h]
        popad
        ret

mb_wsel:                                ; eax = the setting (one the build does not have: 0, World 2026-27)
        movzx eax, byte [BUF + SET_OFF_]
        cmp eax, MAXW_
        jbe .r
        xor eax, eax
.r:     ret

mb_lbl: call .g                         ; eax = the setting's label
.g:     pop edx
        imul eax, eax, LAB_W_
        lea eax, [edx + eax + mb_labs - .g]
        ret

mb_wfile:                               ; SETUP.DAT +105 = the byte (the rest as on disk); no file, or one shorter
        mov edx, FNAME                  ; than the setup's 105 B: the game's buffer, 106 B (as controls' SAVE)
        mov eax, 3D02h
        int 21h
        jc .new
        mov ebx, eax
        mov eax, 4202h                  ; (its size: lseek to the end)
        xor ecx, ecx
        xor edx, edx
        int 21h
        jc .close
        test dx, dx
        jnz .put
        cmp ax, SET_OFF_
        jb .short
.put:   mov eax, 4200h
        xor ecx, ecx
        mov edx, SET_OFF_
        int 21h
        jc .close
        mov edx, BUF + SET_OFF_
        mov ecx, 1
        mov ah, 40h
        int 21h
.close: mov ah, 3Eh
        int 21h
        ret
.short: mov ah, 3Eh
        int 21h
.new:   mov edx, FNAME
        xor ecx, ecx
        mov ah, 3Ch                     ; create / truncate
        int 21h
        jc .r
        mov ebx, eax
        mov edx, BUF
        mov ecx, SET_OFF_ + 1
        mov ah, 40h
        int 21h
        mov ah, 3Eh
        int 21h
.r:     ret

mb_d0:  mov byte [D0], 0FFh             ; (replaced: SelectTeamsFinalMenu from the top list)
        cmp dword [HDR], STR            ; only SELECT TEAM TO MANAGE (not a player purchase's team choice)
        jne .r
        push eax
        call .g
.g:     pop eax
        mov al, [eax + mb_flag - .g]
        cmp al, 1
        jne .n1
        mov byte [D0], WID_             ; the world's list (CLASSIC CAREERS > WORLD 2026-27): its continents
.n1:    cmp al, 2
        jne .n2
        mov byte [D0], WID84_           ; (CLASSIC CAREERS > EUROPA 1984-85: its countries)
.n2:    pop eax
.r:     ret

mb_flag: db 0
mb_ommk: db "SWOSMOD-OMM"               ; (the patcher finds the option byte by this marker, OMM_MARK)
mb_omm:  db 0                           ; 1 = 'Original main menu' (set by the patcher only)
mb_labs:
LABELS_
"""


def choose_sites(p):
    """ChooseTeamsDialog's `mov byte [D0], 255; call SelectTeamsFinalMenu` (obj1 offset, the game's bytes), the title
    pointer it reads (HDR) and SELECT TEAM TO MANAGE's string (STR): (cs, (obj, off), (obj, off))."""
    c = p.le.obj_bytes(1)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    cs = [m.start() for m in re.finditer(rb'\xc6\x05....\xff\xe8....\x66\xa1', c, re.S)]
    assert len(cs) == 1, cs
    cs = cs[0]
    hdr = [fx[cs - 0xd0 + k.start() + 6] for k in re.finditer(rb'\xa1....\xa3', c[cs - 0xd0:cs], re.S)][0]
    st = [fx[m.start() + 6] for m in re.finditer(rb'\xc7\x05........\xc7\x05....\x00\x00\x00\x00\x66\xc7\x05....'
                                                 rb'\x01\x00\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00\xe8', c, re.S)]
    st = [x for x in st if p.le.obj_bytes(2)[x[1]:x[1] + 1] != b'\0']
    return cs, hdr, st[0]


def patch(p, at, lang, wid, onsel=None, obj=1, wid84=None):
    """The button's code at obj offset at (4.0.6: obj3's last page, else obj1); wid = the World 2026-27's list id
    (mkseason.WMENU + its number), wid84 = Europe 1984-85's (None: not in the build, the switch has two worlds); onsel =
    (1, obj1 offset) of CAREER's on-select function (None: found in obj2). Returns the end of the code."""
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
    labs = WORLD[lang][:3 if wid84 else 2]
    import complist
    assert all(len(t) < LAB_W and set(t.decode('latin-1')) <= complist.FONT for t in labs), labs   # (the menu fonts' chars)
    src = nasmcave.sub(SRC, 'LABELS_', '\n'.join(f'        db "{t.decode("latin-1")}"\n        times {LAB_W - len(t)} db 0'
                                                  for t in labs))
    import joyfix
    rs = [m.start() for m in re.finditer(joyfix.RSD_PAT, c, re.S)]  # ReadSetupDat: "SETUP.DAT", setupDatBuffer
    assert len(rs) == 1, rs
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
    cs, hdr, st = choose_sites(p)
    sym.update({'HDR': hdr, 'STR': st, 'WID_': (0, wid), 'WID84_': (0, wid84 or wid), 'FNAME': fx[rs[0] + 1],
                'BUF': fx[rs[0] + 17], 'SET_OFF_': (0, SET_OFF), 'MAXW_': (0, len(labs) - 1), 'LAB_W_': (0, LAB_W)})
    import zones
    code = zones._put_obj(p, src, at, sym, obj)
    lab = nasmcave.labels(src, at, sym)
    p.branch(1, on + 6, 0xE9, obj, lab['mb_on'])
    p.branch(1, off + 6, 0xE9, obj, lab['mb_off'], n=7)
    p.remove(1, cs + 2)                              # (the overwritten instruction's fixup: [D0])
    p.branch(1, cs, 0xE8, obj, lab['mb_d0'], n=7)
    CHOOSE[0] = {'site': cs + 7, 'HDR': hdr, 'STR': st}
    FLAG[0] = (obj, lab['mb_flag'])                  # (4.0.3: careerworld's nat_init reads it: the coach's list)
    SETTING[0] = (sym['BUF'][0], sym['BUF'][1] + SET_OFF)   # (W-modes: the registry's pointer, swreg)
    OMM[0] = (obj, lab['mb_omm'])                    # (modver's line and swe's default world read it too)
    print(f'exe: main menu world switch {" / ".join(t.decode() for t in labs)} at obj{obj}+{at:#x} '
          f'(hooks {on + 6:#x}, {off + 6:#x}; setting obj{SETTING[0][0]}+{SETTING[0][1]:#x})')
    return at + len(code)
