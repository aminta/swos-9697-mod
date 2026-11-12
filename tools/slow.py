"""4.2 EXPERIMENTAL (Davide 12/11, way A of internal/handoff/slowspeed-estimate.md): a slower match - an OPTIONS row
MATCH SPEED 100% / 90% / 80% / 70%, 100% by default (no change).

How the game paces a match: TimerProc (AIL, PIT divisor 17045 = 70 Hz) increments currentTick and, when not paused,
currentGameTick; GameLoop makes one whole step per pass (controls, ball, players, referee, sprites) and ends with
`@@flip_it: call Flip`, which waits for the VGA vertical retrace (70 Hz in mode 13h). The match clock and every timer
read real time: ReadTimerDelta (each pass) gives lastFrameTicks = currentGameTick - lastGameTick (at least 1), which
UpdateTime, the stoppage / stats / result timers add or subtract. So the speed = the frame rate.

The slowdown: GameLoop's own `call Flip` (@@flip_it, GameLoop+0x571: the live match only - the instant replay and the
highlights have their own Flip calls and keep the normal speed, Davide 12/11) goes to sl_flip: Flip, then on some
frames one more vertical retrace (the same picture shown twice), and the ticks that passed meanwhile are taken off
currentGameTick (one `sub [mem], reg`: atomic against the timer IRQ). Every frame still sees +1 tick and makes one step,
so every rule is identical; there are fewer steps a real second, and the clock, the players, the ball, the AI timers
and the currentGameTick-based randomness / blinking all slow down together. Which frames: an accumulator (Bresenham)
adds 100 - level each step and stalls when it reaches the level: steps / (steps + stalls) = level / 100 (90: 1 in 10,
80: 1 in 5 frames, 70: 3 in 10). Not while paused (the game's paused word), not under SWOS++ (no row: SWOS++ has its
own options, controls' rule; its Flip / UpdateTime hooks are other sites).

The option: the word SL_W (0 = 100%, 1 = 90%, 2 = 80%, 3 = 70%; the string table lists them in that order), kept
across restarts (Davide 12/11) in SPEED.CFG beside the exe: one byte, SL_W, written by sl_tog on every change (create /
truncate, write, close; an error is silent: not kept), read at boot by sl_boot (chained on controls' ct_boot, joyfix's
`call ReadSetupDat`): missing / short / > 3 = 100%. Not in SETUP.DAT: its 105 bytes are all fields (+101..+104 the
sticks' fire bytes) and ReadSetupDat reads the whole file over the variables after setupDatBuffer. The game makes the
file, the patcher never ships nor touches it (no DATA entry). Under SWOS++ (no row) the file is not read: 100%.
A career file brings no speed: a player's preference, not a career rule. The row: OPTIONS entries 26 / 27, copies of the bottom row (CHAIRMAN SCENES, 15 / 16)
12 px below it, after gkinj's rows (24 / 25). The OPTIONS screen has no 13th row of room at the game's 12 px pitch
(unpacked rows at y 18 + 12 * k, EXIT TO DOS at 151): sl_add puts every row at 11 px (height 10, a 1 px gap),
18 + 11 * k, so the 12 rows end at 149. Chained after gkinj's gk_init / gk_ret.

Room (MC 12/11, CONVENTIONS 23bis exception for 4.2 slow): obj4's 13th page, swreg.SLOW_AT 0xC000..SLOW_END 0xD000
(0xB000 = SREG2's; patch.py raises swe.OBJ4_PAGES to 13); obj3 closed. Calls into obj1 / obj3 and the obj1 / obj2 sites into it: type-8
self-relative fixups. No obj4 address goes into a save or into SPEED.CFG.

Harness: the data block's tag 'SLOW' (SL_W, SL_ACC, SL_FLIPS: sl_flip calls, SL_STALLS: extra retraces).
SLOW_LEVEL=0..3 (test builds only, modver TEST_VARS): SL_W's start value.
"""
import os
import re
import struct

import nasmcave

LABEL = {'it': "VELOCITA' PARTITA", 'en': 'MATCH SPEED', 'fr': 'VITESSE DU MATCH', 'de': 'SPIELTEMPO'}
LEVELS = (100, 90, 80, 70)
TAG = b'SLOW'
FILE = 'SPEED.CFG'                      # beside the exe, made by the game (sl_tog), read at boot (sl_boot)
PITCH, HEIGHT, TOP = 11, 10, 18         # the rows (unpacked y): 18 + 11 * k, 10 high (12 rows end at 149; EXIT TO
                                        # DOS at 151); the game's own rows: 18 + 12 * k, 11 high

ASM = r"""
sl_init:                                ; OPTIONS' init: the previous one (gkinj), then our row
    call PREV_INIT
    jmp sl_add
sl_ret:                                 ; (and on return to OPTIONS: the menu is unpacked again)
    call PREV_RET
sl_add:
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no row
    jne .x
    mov ebx, MENU_
    cmp word [ebx + 10h], 26            ; (gkinj's 26 entries, nothing after them)
    jne .x
    lea eax, [ebx + 16h + 26 * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries 26 / 27 = copies of the bottom row (15 / 16), 12 px below it
    lea esi, [ebx + 16h + 15 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], 26
    add word [edi + 16h], 12
    mov dword [edi + 26h], S_LBL
    mov word [edi + 38h + 2], 27
    add word [edi + 38h + 16h], 12
    mov dword [edi + 38h + 26h], TAB_S
    mov dword [edi + 38h + 2Ah], sl_tog
    movzx ecx, byte [ebx + 16h + 16 * 38h + 0Bh]   ; (16's down: EXIT TO DOS - now 27's)
    mov byte [edi + 38h + 0Ah], 16
    mov [edi + 38h + 0Bh], cl
    mov byte [edi + 38h + 12h], 16
    mov [edi + 38h + 13h], cl
    mov byte [ebx + 16h + 16 * 38h + 0Bh], 27
    mov byte [ebx + 16h + 16 * 38h + 13h], 27
    cmp cl, 0FFh
    je .n
    imul ecx, ecx, 38h                  ; (and the entry below: up 16 -> 27)
    lea ecx, [ebx + 16h + ecx]
    cmp byte [ecx + 0Ah], 16
    jne .u
    mov byte [ecx + 0Ah], 27
.u: cmp byte [ecx + 12h], 16
    jne .n
    mov byte [ecx + 12h], 27
.n: mov word [ebx + 10h], 28
    add dword [ebx + 12h], 2 * 38h
    lea esi, [ebx + 16h]                ; every row (140 wide, y TOP + 12 * k, k 0..11): y TOP + 11 * k, 10 high
    mov ecx, 28
.c: cmp word [esi + 18h], 140
    jne .cn
    movzx eax, word [esi + 16h]
    sub eax, TOP
    jb .cn
    cmp eax, 12 * 11
    ja .cn
    xor edx, edx
    mov edi, 12
    div edi
    test edx, edx
    jnz .cn
    imul eax, eax, PITCH
    add eax, TOP
    mov [esi + 16h], ax
    mov word [esi + 1Ah], HEIGHT
.cn: add esi, 38h
    loop .c
.x: popad
    ret

sl_tog:                                 ; the value (fire): 100 -> 90 -> 80 -> 70 -> 100 %, then SPEED.CFG
    mov ax, [SL_W]
    inc ax
    cmp ax, 4
    jb .s
    xor ax, ax
.s: mov [SL_W], ax
    mov word [SL_ACC], 0
    pushad
    mov edx, S_FILE
    xor ecx, ecx
    mov ah, 3Ch                         ; create / truncate (an error: silent, the value not kept)
    int 21h
    jc .w
    mov ebx, eax
    mov edx, SL_W
    mov ecx, 1
    mov ah, 40h
    int 21h
    mov ah, 3Eh
    int 21h
    inc dword [SL_WRITES]
.w: popad
    jmp DRAWITEM

sl_boot:                                ; controls' ct_boot (joyfix's `call ReadSetupDat`), then SPEED.CFG -> SL_W
    call PREV_BOOT
    pushad
    cmp byte [SWOSPP], 0FFh             ; (SWOS++: no row, so no speed either)
    jne .x
    mov edx, S_FILE
    mov eax, 3D00h
    int 21h
    jc .x
    mov ebx, eax
    mov byte [SL_FB], 0FFh
    mov edx, SL_FB
    mov ecx, 1
    mov ah, 3Fh
    int 21h
    mov ah, 3Eh
    int 21h
    movzx eax, byte [SL_FB]
    cmp eax, 4                          ; (short / empty: FFh; anything > 3: 100 %)
    jb .s
    xor eax, eax
.s: mov [SL_W], ax
    inc dword [SL_READS]
.x: popad
    ret

sl_flip:                                ; GameLoop's @@flip_it: Flip, then maybe one more retrace off the game clock
    call FLIP
    pushad
    inc dword [SL_FLIPS]
    movzx eax, word [SL_W]
    test eax, eax
    jz .x
    cmp word [PAUSED], 0
    jne .x
    movzx edx, byte [SL_LVL + eax]      ; the level (90 / 80 / 70)
    mov ecx, 100
    sub ecx, edx
    add cx, [SL_ACC]                    ; acc += 100 - level; >= level: one stall, acc -= level
    cmp cx, dx
    jb .k
    sub cx, dx
    mov [SL_ACC], cx
    inc dword [SL_STALLS]
    mov bx, [CGT]
    mov dx, 3DAh
.a: in al, dx                           ; (Flip's own wait: out of this retrace, then the next one starts)
    test al, 8
    jnz .a
.b: in al, dx
    test al, 8
    jz .b
    mov ax, [CGT]
    sub ax, bx                          ; the ticks of the extra retrace, taken off the game clock
    sub [CGT], ax
    jmp .x
.k: mov [SL_ACC], cx
.x: popad
    ret

    align 4
    db 'SLOW'
SL_W: dw SLOW_START
SL_ACC: dw 0
SL_FLIPS: dd 0
SL_STALLS: dd 0
SL_LVL: db 100, 90, 80, 70
SL_READS: dd 0                          ; (harness: SPEED.CFG opened at boot / written)
SL_WRITES: dd 0
SL_FB: db 0, 0, 0, 0
TAB_S: dd SL_W                          ; (the game's string table: variable, first index, its strings)
    dw 0
    dd S100, S90, S80, S70
"""


def find(p):
    """GameLoop's @@flip_it (call Flip; the fadeState check; call FadeIn; fadeState = -1; currentGameTick = 0;
    lastGameTick = 0) and TimerProc (its `mov ax, paused` before `inc currentGameTick`): the same currentGameTick."""
    d = p.le.obj_bytes(1)
    fl = [m.start() for m in re.finditer(rb'\xe8....\x66\xa1....\x66\x0b\xc0\x75.\xe8....\x66\xc7\x05....\xff\xff'
                                         rb'\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00', d, re.S)]
    assert len(fl) == 1, ('GameLoop @@flip_it', fl)
    tp = [m.start() for m in re.finditer(rb'\x50\x66\xc7\x05....\xff\xff\x66\xff\x05....\x66\xff\x05....\x66\xa1....'
                                         rb'\x66\x0b\xc0\x75.\x66\xff\x05', d, re.S)]
    assert len(tp) == 1, ('TimerProc', tp)
    cgt = p.target(1, fl[0] + 33)
    assert cgt == p.target(1, tp[0] + 38), ('currentGameTick', cgt, p.target(1, tp[0] + 38))
    return dict(FLIP_AT=fl[0], CGT=cgt, PAUSED=p.target(1, tp[0] + 26))


def patch(p, lang):
    """Code + data at obj4+swreg.SLOW_AT (its own page, MC 12/11); returns the end. Chained on gkinj's gk_init / gk_ret
    (the OPTIONS menu header's pointers), on @@flip_it's current target and on controls' ct_boot (joyfix's call)."""
    import controls
    import cpucards
    import gkinj
    import swreg
    import zones
    from complist import px
    s = find(p)
    sym0 = controls.locate(p)
    hdr = controls.menu_header(p, sym0['OMBD'][1])
    prev = [p.target(2, hdr + k) for k in (0, 4)]
    assert prev == [(3, gkinj.LABELS['gk_init']), (3, gkinj.LABELS['gk_ret'])], ('OPTIONS init / return', prev)
    label = LABEL[lang]
    assert px(label) <= 138 and re.fullmatch(r"[A-Z ']+", label), label
    start = int(os.environ.get('SLOW_LEVEL', '0'))
    assert 0 <= start < len(LEVELS)
    if start:
        import modver
        assert modver.is_test(), 'SLOW_LEVEL: test builds only'
    db = lambda x: ', '.join(str(c) for c in x.encode() + b'\0')
    src = f'%define SLOW_START {start}\n%define TOP {TOP}\n%define PITCH {PITCH}\n%define HEIGHT {HEIGHT}\n' + ASM \
        + f'S_LBL: db {db(label)}\nS_FILE: db {db(FILE)}\n' + ''.join(f'S{v}: db {db(f"{v}%")}\n' for v in LEVELS)
    flip = p.call_target(1, s['FLIP_AT'])
    vj = controls.LAST['lab']['ct_boot']               # (controls' ct_boot: the site that calls it, joyfix's first)
    boot_at = [o for o in (controls.LAST['sym_vj'],) if p.call_target(1, o) == (1, vj)]
    assert boot_at, 'ct_boot call site'
    at = swreg.SLOW_AT
    sym = {'PREV_INIT': prev[0], 'PREV_RET': prev[1], 'SWOSPP': sym0['SWOSPP'], 'MENU_': zones._current_menu(p),
           'DRAWITEM': (1, cpucards.find(p)['DRAWITEM']), 'FLIP': flip, 'CGT': s['CGT'], 'PAUSED': s['PAUSED'],
           'PREV_BOOT': (1, vj)}
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    top = getattr(swreg, 'TRIAL_AT', getattr(swreg, 'BOX_AT', swreg.SLOW_END))   # (4.2 MC 12/11: trial.py TRIAL_AT 0xC800..
    assert swreg.SLOW_AT <= top and getattr(swreg, 'BOX_END', top) <= swreg.SLOW_END   # 0xCF00, shirtbox BOX_AT..0xD000)
    assert at + len(code) <= top, ('slow: past its obj4 room', hex(at + len(code)), hex(top))
    assert p.le.obj(4).npages * 0x1000 >= swreg.SLOW_END, 'slow: obj4 pages (patch.py)'
    assert not any(p.get(4, at, top - at)), 'slow: obj4 room not free'     # (SLOW_AT..TRIAL_AT: trial's and the box's not ours)
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.branch(1, s['FLIP_AT'], 0xE8, 4, lab['sl_flip'])
    p.branch(1, boot_at[0], 0xE8, 4, lab['sl_boot'])
    for k, l in ((0, 'sl_init'), (4, 'sl_ret')):
        p.retarget(2, hdr + k, 4, lab[l])
        p.put(2, hdr + k, struct.pack('<I', lab[l]))
    LABELS.update(lab)
    print(f'exe: match speed (OPTIONS: {label}, {"/".join(f"{v}%" for v in LEVELS)}'
          f'{", SLOW_LEVEL=" + str(start) if start else ""}): code obj4+{at:#x} ({len(code)} B), '
          f'@@flip_it obj1+{s["FLIP_AT"]:#x} (was {flip})')
    return at + len(code)


LABELS = {}
