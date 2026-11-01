"""4.0.6 (Davide): the computer's teams by the human rules - two OPTIONS rows, ON by default: ROSSI ALLA CPU (cards)
and INFORTUNI ALLA CPU (injuries carried over: step B, the row only for now).

The original game never sends off a computer team's player (a team with no player and no coach controlling it,
TeamGeneralInfo +4 / +6 both 0): TrySendingOffThePlayer (the straight red) returns 'no card' for it, so a last-man foul
(87.5% a straight red for a human team) is a plain free kick; TryBookingThePlayer (the yellow) does not book it at all
when plg_D3_param is 0 (a friendly: PlayFriendly passes D3 = 0) and otherwise books its player only while his Sprite.cards
is 0 - one yellow each, never the second ('don't book cheating scum CPU'). ON: the three CPU exits go the human way (same
odds, same budget team1/2NumAllowedInjuries, same card tables); OFF: the original.

The options: the words CC_W (cards) and CC_I (injuries), 0 = ON, 1 = OFF (each row's string table lists ON first), 0 at
every start (the game's own options are not saved either: SetDefaultOptions at start, a career file brings its own);
saved with a career as the engine item 'CC' (4 bytes; a save without it - older, or any other build's - loads them 0 =
ON); CC_SH keeps the session's values for a new career (trailer's new_career_defaults zeroes the items: engine.after_new
puts them back). The OPTIONS menu's 20 entries are all used (19 = the CONTROLS button): the rows are added to the
unpacked menu (g_currentMenu, 6500 bytes; no STDMENUTEXT in it, so its end pointer is the entries' end) as entries
20 / 21 and 22 / 23, copies of the game-length row (1 / 2) 24 and 12 px above it, in the free space under the title, by
the menu's init / on-return functions (after controls' ct_optinit / ct_optret). Not under SWOS++ (controls' rule: its
own options; both rules stay ON there).

CARDS_FORCE=red / yellow (test builds only, modver TEST_VARS): see force().
"""
import os
import re
import struct

import nasmcave

LABEL = {'it': 'ROSSI ALLA CPU', 'en': 'CPU RED CARDS', 'fr': 'ROUGES A LA CPU', 'de': 'ROTE KARTEN CPU'}
LABEL_I = {'it': 'INFORTUNI ALLA CPU', 'en': 'CPU INJURIES', 'fr': 'BLESSURES A LA CPU', 'de': 'VERLETZUNGEN CPU'}

ASM = r"""
cc_init:                                ; OPTIONS' init: the previous one (controls), then our rows
    call PREV_INIT
    jmp cc_add
cc_ret:                                 ; (and on return to OPTIONS: the menu is unpacked again)
    call PREV_RET
cc_add:
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no rows
    jne .x
    mov ebx, MENU_
    cmp word [ebx + 10h], 20            ; (the game's 20 entries, nothing after them)
    jne .x
    lea eax, [ebx + 16h + 20 * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries 20 / 21 and 22 / 23 = copies of the game-length row (1 / 2)
    lea esi, [ebx + 16h + 1 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    lea esi, [ebx + 16h + 1 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], 20              ; red cards: 24 px above the game length
    sub word [edi + 16h], 24
    mov dword [edi + 26h], S_LR
    mov word [edi + 38h + 2], 21
    sub word [edi + 38h + 16h], 24
    mov dword [edi + 38h + 26h], TAB_R
    mov dword [edi + 38h + 2Ah], cc_tog_r
    mov word [edi + 38h + 0Ah], 17FFh   ; (up: none, down: 23)
    mov word [edi + 38h + 12h], 17FFh
    mov word [edi + 70h + 2], 22        ; injuries: 12 px above it
    sub word [edi + 70h + 16h], 12
    mov dword [edi + 70h + 26h], S_LI
    mov word [edi + 0A8h + 2], 23
    sub word [edi + 0A8h + 16h], 12
    mov dword [edi + 0A8h + 26h], TAB_I
    mov dword [edi + 0A8h + 2Ah], cc_tog_i
    mov word [edi + 0A8h + 0Ah], 0215h  ; (up: 21, down: the game length's value 2 - and its up: 23)
    mov word [edi + 0A8h + 12h], 0215h
    mov byte [ebx + 16h + 2 * 38h + 0Ah], 23
    mov byte [ebx + 16h + 2 * 38h + 12h], 23
    mov word [ebx + 10h], 24
    add dword [ebx + 12h], 4 * 38h
.x: popad
    ret

cc_tog_r:                               ; a value (fire), as ChangeChairmanScenes; both words to the session copy
    mov eax, CC_W
    jmp cc_tog
cc_tog_i:
    mov eax, CC_I
cc_tog:
    xor word [eax], 1
    mov eax, [CC_W]
    mov [CC_SH], eax
    jmp DRAWITEM

cc_load:                                ; after a career load (engine.after_load): the save's values, 0 = ON when the
    mov eax, [CC_W]                     ; save has no 'CC'
    mov [CC_SH], eax
    ret
cc_new:                                 ; after a new career's defaults (engine.after_new, its items zeroed): the
    mov eax, [CC_SH]                    ; session's values back
    mov [CC_W], eax
    ret

cc_b:                                   ; TryBookingThePlayer, plg_D3_param != 0, a CPU player: replaces `jnz no card`
    jz PCT                              ; after `or ax, ax` (his Sprite.cards): none yet - the game books him too
cc_a:                                   ; plg_D3_param 0, a CPU team: the original `jmp no card`
    cmp word [CC_W], 0
    jne NOCARD
    jmp PCT
cc_c:                                   ; TrySendingOffThePlayer: replaces `jz no red` after the coach test
    jnz SENDOFF                         ; (a human team)
    cmp word [CC_W], 0
    jne NORED
    jmp SENDOFF

align 4
CC_W: dw 0                              ; (the engine item 'CC': red cards, injuries - 0 = ON)
CC_I: dw 0
CC_SH: dd 0                             ; (the session's values: a new career zeroes the item)
CB_SWAPS: dd 0                          ; (step B: starters swapped out so far - read by the harness)
CB_DAYS: dd 0                           ; (step B: calendar days counted down so far - read by the harness)
CB_DAY: db 0                            ; (1 while cb_day runs the countdowns)
TAB_R: dd CC_W                          ; (the game's string tables: variable, first index, its strings)
    dw 0
    dd S_ON, S_OFF
TAB_I: dd CC_I
    dw 0
    dd S_ON, S_OFF
"""


ASM_B = r"""
; ---- step B: the CPU's suspensions / injuries kept between matches (the game's own records and rules)
cb_903:                                 ; replaces CalculateViewResult's `call cseg_903B1` (A0 = the team file)
    pushad
    mov esi, [A0_]
    xor edx, edx                        ; dl = the bits to put back (the OFF kind's)
    cmp byte [esi + 4], 1
    jne .go
    cmp word [CC_W], 0
    je .c
    or dl, 1Fh
.c: cmp word [CC_I], 0
    je .i
    or dl, 0E0h
.i: cmp dl, 0FFh
    je .go                              ; (both OFF: the game skips the CPU team itself)
    lea edi, [SNAP]
    mov ecx, 16
    lea ebx, [esi + 4Ch + 1Bh]
.s: mov al, [ebx]
    stosb
    add ebx, 26h
    loop .s
    mov [SNAPM], dl
    mov [SNAPT], esi
    popad
    call F903
    pushad
    mov esi, [SNAPT]
    mov dl, [SNAPM]
    lea ebx, [SNAP]
    mov ecx, 16
    lea edi, [esi + 4Ch + 1Bh]
.r: mov al, [ebx]                       ; the OFF kind's bits as before the call
    and al, dl
    mov ah, dl
    not ah
    and [edi], ah
    or [edi], al
    inc ebx
    add edi, 26h
    loop .r
    popad
    ret
.go:
    popad
    jmp F903

cb_unav:                                ; ZF = 0: player byte al (cardsInjuries) unavailable under mode [CB_MODE]
    push ecx                            ; (IsPlayerInjured's test, without its memory registers)
    mov cx, [CB_MODE]
    cmp cx, 1
    je .two
    mov ah, al
    and ah, 1Ch
    jz .ok1
    cmp ah, 4
    jne .bad
.ok1:
    test cx, cx
    jns .inj
.two:
    test al, 3
    jnz .bad
.inj:
    mov ah, al
    and ah, 0E0h
    jz .ok
    cmp ah, 20h
    je .ok
.bad:
    pop ecx
    test esp, esp                       ; (ZF = 0)
    ret
.ok:
    pop ecx
    cmp al, al
    ret

cb_swap:                                ; esi = a team file, edi = its slot (dd team, 16 B order): a CPU team's
    mov dword [edi], 0                  ; unavailable starters (order 0..10) swapped with available bench players
    test esi, esi                       ; (11..15), the same role first (goalkeeper or not), then any
    jz .r
    cmp byte [esi + 4], 1
    jne .r
    mov ax, [CC_W]
    and ax, [CC_I]
    jnz .r
    mov [edi], esi
    mov eax, [esi + 3Ch]
    mov [edi + 4], eax
    mov eax, [esi + 40h]
    mov [edi + 8], eax
    mov eax, [esi + 44h]
    mov [edi + 12], eax
    mov eax, [esi + 48h]
    mov [edi + 16], eax
    xor ecx, ecx
.i: call .rec                           ; ebx = starter ecx's record
    mov al, [ebx + 1Bh]
    call cb_unav
    jz .ni
    mov ah, [ebx + 1Ah]
    and ah, 0E0h                        ; (its role: 0 = goalkeeper)
    mov [CB_ROLE], ah
    mov byte [CB_ANY], 0
.p: mov edx, 11
.j: push ecx
    mov ecx, edx
    call .rec
    pop ecx
    mov al, [ebx + 1Bh]
    call cb_unav
    jnz .nj
    cmp byte [CB_ANY], 0
    jne .sw
    mov ah, [ebx + 1Ah]
    and ah, 0E0h
    setz al
    cmp byte [CB_ROLE], 0
    setz ah
    cmp al, ah
    jne .nj
.sw:inc dword [CB_SWAPS]
    mov al, [esi + 3Ch + ecx]
    mov ah, [esi + 3Ch + edx]
    mov [esi + 3Ch + ecx], ah
    mov [esi + 3Ch + edx], al
    jmp .ni
.nj:inc edx
    cmp edx, 16
    jb .j
    cmp byte [CB_ANY], 0
    jne .ni
    inc byte [CB_ANY]
    jmp .p
.ni:inc ecx
    cmp ecx, 11
    jb .i
.r: ret
.rec:                                   ; ebx = the record of order slot ecx
    movzx ebx, byte [esi + 3Ch + ecx]
    imul ebx, ebx, 26h
    lea ebx, [esi + ebx + 4Ch]
    ret

cb_back:                                ; edi = a slot: its team's order back
    mov esi, [edi]
    test esi, esi
    jz .r
    mov eax, [edi + 4]
    mov [esi + 3Ch], eax
    mov eax, [edi + 8]
    mov [esi + 40h], eax
    mov eax, [edi + 12]
    mov [esi + 44h], eax
    mov eax, [edi + 16]
    mov [esi + 48h], eax
    mov dword [edi], 0
.r: ret

cb_game:                                ; InitializeInGameTeamsAndStartGame's entry (A1 / A2 the teams, D3 the mode)
    pushad
    mov ax, [D3_]
    mov [CB_MODE], ax
    mov esi, [A1_]
    lea edi, [SLOTS]
    call cb_swap
    mov esi, [A2_]
    lea edi, [SLOTS + 20]
    call cb_swap
    popad
    mov word [HIL], 0                   ; (the displaced first instruction)
    call GAME5
    pushfd
    pushad
    lea edi, [SLOTS]
    call cb_back
    lea edi, [SLOTS + 20]
    call cb_back
    popad
    popfd
    ret

cb_day:                                 ; cseg_8EA82 (a career calendar day's advance): its first `cmp word [GT], 4`
    pushad                              ; replaced - every cached CPU club's card / injury countdown (cseg_2D7B7 /
    mov ax, [CC_W]                      ; cseg_2CDC6, opened for it by CB_DAY; the per-match countdown of the human's
    and ax, [CC_I]                      ; fixtures, cseg_2D64E, stays closed to CPU clubs: one countdown a day)
    jnz .x
    inc dword [CB_DAYS]
    lea esi, [D0_]                      ; (the game's memory registers D0 .. A6 kept)
    lea edi, [REGSAV]
    mov ecx, 15
    rep movsd
    mov byte [CB_DAY], 1
    movzx ecx, word [NUMSEL]
    mov ebx, [SELBASEV]
.t: test ecx, ecx
    jz .e
    cmp byte [ebx + 4], 1
    jne .n
    push ecx
    push ebx
    mov [A0_], ebx
    call C2CDC6
    mov ebx, [esp]
    mov [A0_], ebx
    mov ax, [MODE10]
    mov [D0_], ax
    call C2D7B7
    pop ebx
    pop ecx
.n: add ebx, 684
    dec ecx
    jmp .t
.e: mov byte [CB_DAY], 0
    lea esi, [REGSAV]
    lea edi, [D0_]
    mov ecx, 15
    rep movsd
.x: popad
    cmp word [GT], 4
    jmp ADV8

cb_view:                                ; CalculateViewResult's entry (A1 / A2 the teams, D3 the mode)
    pushad
    mov ax, [D3_]
    mov [CB_MODE], ax
    mov esi, [A1_]
    lea edi, [SLOTS + 40]
    call cb_swap
    mov esi, [A2_]
    lea edi, [SLOTS + 60]
    call cb_swap
    popad
    mov eax, [A0_]                      ; (the displaced first instruction)
    call VIEW5
    pushfd
    pushad
    lea edi, [SLOTS + 40]
    call cb_back
    lea edi, [SLOTS + 60]
    call cb_back
    popad
    popfd
    ret

align 4
SLOTS: times 80 db 0
SNAP: times 16 db 0
SNAPT: dd 0
SNAPM: db 0
CB_ROLE: db 0
CB_ANY: db 0
align 2
CB_MODE: dw 0
align 4
REGSAV: times 15 dd 0
"""


GUARDS = {5: 'inj', 6: 'day', 7: 'day', 8: 'cards', 9: 'inj', 13: 'any'}   # the 14 `cmp byte [esi + 4], 1 / jz` (a
# team file's controls = TEAM_COMPUTER): 5 cseg_2C9D9 pre-match injuries, 6 cseg_2CDC6 injury countdown, 7 cseg_2D7B7
# card countdown, 8 cseg_2F194 the match's cards into the records, 9 UpdatePlayerInjuries, 13 cseg_903B1 a simulated
# result's cards / injuries (the same order in the 4 exes)
STUB = {'day': "    cmp byte [CB_DAY], 0\n    jne CONT{k}\n    jmp OUT{k}\n",
        'cards': "    cmp word [CC_W], 0\n    jne OUT{k}\n    jmp CONT{k}\n",
        'inj': "    cmp word [CC_I], 0\n    jne OUT{k}\n    jmp CONT{k}\n",
        'any': "    push eax\n    mov ax, [CC_W]\n    and ax, [CC_I]\n    pop eax\n    jnz OUT{k}\n    jmp CONT{k}\n"}


def find_b(p):
    """Step B's sites: the guards, cseg_903B1 and its two calls, InitializeInGameTeamsAndStartGame /
    CalculateViewResult's entries."""
    d = p.le.obj_bytes(1)
    g = [m.start() for m in re.finditer(rb'\x80\x7e\x04\x01\x0f\x84', d)]
    assert len(g) == 14, len(g)
    rel = lambda o, n: o + n + struct.unpack_from('<i', d, o + n - 4)[0]
    s = {'guards': {k: (g[k], rel(g[k] + 4, 6)) for k in GUARDS}}
    f903 = g[13] - 21
    assert d[f903:f903 + 2] == b'\x66\xa1' and d[f903 + 9:f903 + 11] == b'\x0f\x85', 'cseg_903B1'
    s['F903'] = f903
    s['calls903'] = [m.start() for m in re.finditer(rb'\xe8', d) if m.start() + 5 <= len(d) and rel(m.start(), 5) == f903]
    assert len(s['calls903']) == 2, s['calls903']
    ge = [m.start() for m in re.finditer(rb'\x66\xc7\x05....\x00\x00(?:\x66\xa1....\x66\xa3....){4}\xa1....\xa3', d, re.S)]
    assert len(ge) == 1, ge
    s['GAME'] = ge[0]
    cv = [m.start() for m in re.finditer(rb'\xa1....\xa3....\x8b\x35....\x66\x8b\x46\x3b\x66\xa3', d, re.S)]
    assert len(cv) == 1, cv
    s['VIEW'] = cv[0]
    c7 = g[7] - 21                                       # cseg_2D7B7 (its callers pass D0 = dseg_10EEE4, the mode)
    assert d[c7:c7 + 2] == b'\x66\xa1' and d[g[6] - 6:g[6] - 4] == b'\x8b\x35', 'cseg_2D7B7 / cseg_2CDC6 starts'
    calls = [m.start() for m in re.finditer(rb'\xe8', d) if m.start() + 5 <= len(d) and rel(m.start(), 5) == c7]
    modes = set()
    for c in calls:
        w = d[c - 0x60:c]
        i = w.rfind(b'\x66\xa1')
        if i >= 0 and w[i + 6:i + 8] == b'\x66\xa3':
            modes.add(p.target(1, c - 0x60 + i + 2))
    assert len(modes) == 1, modes
    s['MODE10'] = modes.pop()
    import gplay
    s['ADV'] = gplay._adv_sites(p)[0]                    # cseg_8EA82: `cmp word [gameType], 4 / jnz`
    assert d[s['ADV']:s['ADV'] + 3] == b'\x66\x83\x3d' and d[s['ADV'] + 7] == 4, 'cseg_8EA82'
    return s


def find(p):
    """TryBookingThePlayer / TrySendingOffThePlayer's CPU exits, the OFF / ON strings, CallDrawMenuItem."""
    d = p.le.obj_bytes(1)
    tb = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x75\x23\x8b\x35....\x66\x8b\x46\x04\x66\x0b\xc0'
                                         rb'\x75\x45\x8b\x35....\x66\x8b\x46\x06\x66\x0b\xc0\x75\x36\xe9', d, re.S)]
    ts = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x04\x66\x0b\xc0\x75\x13\x8b\x35....\x66\x8b\x46\x06'
                                         rb'\x66\x0b\xc0\x0f\x84', d, re.S)]
    assert len(tb) == 1 and len(ts) == 1, (tb, ts)
    tb, ts = tb[0], ts[0]
    rel = lambda o, n: o + n + struct.unpack_from('<i', d, o + n - 4)[0]
    s = dict(a=tb + 0x29, b=tb + 0x59, c=ts + 0x1C)
    pct, nocard = tb + 0x5F, rel(tb + 0x29, 5)
    assert d[s['b']:s['b'] + 2] == b'\x0f\x85' and rel(s['b'], 6) == nocard and s['b'] + 6 == pct, 'TryBooking'
    assert d[s['c']:s['c'] + 2] == b'\x0f\x84', 'TrySendingOff'
    s.update(PCT=pct, NOCARD=nocard, SENDOFF=s['c'] + 6, NORED=rel(s['c'], 6))
    tg = [rel(m.start() + 8, 5) for m in re.finditer(rb'\x66\x83\x35....\x01\xe9', d, re.S)]   # ChangeAutoReplays...
    assert len(set(tg)) == 1 and len(tg) >= 5, tg
    s['DRAWITEM'] = tg[0]
    return s


def strings(p, hdr):
    """The exe's OFF / ON strings: the last OFF / ON row's string table (chairmanScenesStrTable: dd variable, dw 0,
    dd OFF, dd ON) among the tables the packed OPTIONS menu (obj2:hdr) points to."""
    fx = {(so, s): (t, o) for so, s, _, t, o, *_ in p.le.fixups()}
    d2 = p.le.obj_bytes(2)
    tabs = sorted({o for (so, s), (t, o) in fx.items() if so == 2 and hdr <= s < hdr + 0x400 and t == 2
                   and (2, o) in fx and (2, o + 6) in fx and (2, o + 10) in fx and (2, o + 14) not in fx
                   and d2[o + 4:o + 6] == b'\0\0'})
    assert len(tabs) == 1, [hex(x) for x in tabs]          # (the tables follow each other: only the last one has
    return fx[(2, tabs[0] + 6)], fx[(2, tabs[0] + 10)]     # no pointer after its ON - chairman's)


def patch(p, at, lang):
    """Code + data at obj3:at (4.0.6, CONVENTIONS 23; after benchx); returns the end. The game's sites jump / call into
    obj3 through self-relative fixups (p.branch), obj3's references back are absolute / self-relative fixups too."""
    import controls
    import engine
    import zones
    from complist import px
    s = find(p)
    d = p.le.obj_bytes(1)
    for k in 'abc':
        assert p.get(1, s[k], 6) == d[s[k]:s[k] + 6], ('cpucards site already patched', k)
    sym0 = controls.locate(p)
    hdr = controls.menu_header(p, sym0['OMBD'][1])
    prev = [struct.unpack('<I', bytes(p.get(2, hdr + k, 4)))[0] for k in (0, 4)]
    assert all(p.target(2, hdr + k) == (1, v) for k, v in zip((0, 4), prev)), 'OPTIONS init / return in obj1'
    off, on = strings(p, hdr)
    label, label_i = LABEL[lang], LABEL_I[lang]
    for x in (label, label_i):
        assert px(x) <= 138 and re.fullmatch(r'[A-Z ]+', x), x
    db = lambda x: ', '.join(str(b) for b in x.encode() + b'\0')
    src = ASM + f'S_LR: db {db(label)}\nS_LI: db {db(label_i)}\n'
    import sacups
    import trailer
    b = find_b(p)
    regs = sacups.regs(d)
    d0 = regs['D7'] - 28
    assert p.target(1, b['GAME'] + 9 + 2) == (2, d0) and p.target(1, b['GAME'] + 9 + 3 * 12 + 2) == (2, d0 + 12), \
        'InitializeInGameTeamsAndStartGame: D0 .. D3 first'
    src += ASM_B + ''.join(f'cb_s{k}:\n    jne CONT{k}\n' + STUB[kind].format(k=k) for k, kind in GUARDS.items())
    sym = {'PREV_INIT': (1, prev[0]), 'PREV_RET': (1, prev[1]), 'SWOSPP': sym0['SWOSPP'], 'MENU_': zones._current_menu(p),
           'DRAWITEM': (1, s['DRAWITEM']), 'S_ON': on, 'S_OFF': off,
           'A0_': (2, regs['A0']), 'A1_': (2, regs['A0'] + 4), 'A2_': (2, regs['A0'] + 8), 'D3_': (2, d0 + 12),
           'HIL': p.target(1, b['GAME'] + 3), 'GAME5': (1, b['GAME'] + 9), 'VIEW5': (1, b['VIEW'] + 5),
           'F903': (1, b['F903']), 'D0_': (2, d0), 'C2CDC6': (1, b['guards'][6][0] - 6),
           'C2D7B7': (1, b['guards'][7][0] - 21), 'MODE10': b['MODE10'], 'GT': p.target(1, b['ADV'] + 3),
           'ADV8': (1, b['ADV'] + 8), 'NUMSEL': trailer.INFO['NUMSEL'], 'SELBASEV': (1, trailer.INFO['selbasev'])}
    assert regs['A0'] == d0 + 32, 'D0 .. D7, A0 .. A6 contiguous'
    for k, (site, out) in b['guards'].items():
        sym[f'CONT{k}'], sym[f'OUT{k}'] = (1, site + 10), (1, out)
    sym.update({k: (1, s[k]) for k in ('PCT', 'NOCARD', 'SENDOFF', 'NORED')})
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['a'], 0xE9, 3, lab['cc_a'])
    for k in 'bc':
        p.branch(1, s[k], 0xE9, 3, lab['cc_' + k], 6)
    for k, (site, _) in b['guards'].items():           # step B: the CPU guards' `jz` -> our stubs
        assert p.get(1, site + 4, 6) == d[site + 4:site + 10], ('cpucards B guard already patched', k)
        p.branch(1, site + 4, 0xE9, 3, lab[f'cb_s{k}'], 6)
    for c in b['calls903']:
        assert p.call_target(1, c) == (1, b['F903']), ('cseg_903B1 call already hooked', hex(c))
        p.branch(1, c, 0xE8, 3, lab['cb_903'])
    for at_, lb, n, fx in ((b['GAME'], 'cb_game', 9, 3), (b['VIEW'], 'cb_view', 5, 1), (b['ADV'], 'cb_day', 8, 3)):
        assert p.get(1, at_, n) == d[at_:at_ + n], ('cpucards B entry already patched', lb)
        p.remove(1, at_ + fx)
        p.branch(1, at_, 0xE9, 3, lab[lb], n)
    for k, l in ((0, 'cc_init'), (4, 'cc_ret')):
        p.retarget(2, hdr + k, 3, lab[l])
        p.put(2, hdr + k, struct.pack('<I', lab[l]))
    engine.ITEM_AT['CC'] = (3, lab['CC_W'])
    engine.CALL_AT['cc_load'] = (3, lab['cc_load'])
    engine.CALL_AT['cc_new'] = (3, lab['cc_new'])
    LABELS.update(lab)
    print(f'exe: CPU cards / injuries by the human rules (OPTIONS: {label} / {label_i}): code obj3+{at:#x} ({len(code)} B), sites '
          f'{[hex(s[k]) for k in "abc"]}')
    return at + len(code)


LABELS = {}


def force(p):
    """CARDS_FORCE=red / yellow (test builds only): every tackle that reaches its man is a foul, every foul outside the
    penalty area takes PlayerTacklingTestFoul's last-man branch (cseg_79444: no card-chance test) and its card is always the straight red / the yellow."""
    mode = os.environ.get('CARDS_FORCE')
    if not mode:
        return
    assert mode in ('red', 'yellow'), mode
    d = p.le.obj_bytes(1)
    m = [x for x in re.finditer(rb'\x66\x39\x05....\x73.\xe8....\x66\x83\x3d....\x20\x72.\xe8....\x75.\xe8....\xff\x35'
                                rb'....\xe8....\x8f\x05....\xc3(\xe8....\x66\x83\x3d....\x20)\x72', d, re.S)]
    assert len(m) == 1, len(m)
    lm = m[0].start(1)                                   # cseg_79444
    jz = [i for i in range(lm - 0x80, lm) if d[i] == 0x74 and i + 2 + struct.unpack_from('<b', d, i + 1)[0] == lm]
    assert len(jz) == 1, jz
    jb = m[0].end()                                      # `jb yellow`
    p.put(1, jz[0], b'\xeb')
    p.put(1, jb - 1, b'\xeb' if mode == 'yellow' else b'\x90')
    if mode == 'red':
        p.put(1, jb, b'\x90')
    t = [x for x in re.finditer(rb'\x81\x7e\x4a\x20\x03\x00\x00\x0f\x87....\x8b\x35....\x66\x8b\x46\x60\x66\x0b\xc0\x74(.)',
                                d, re.S)]                # (the tackled player's ball distance > 800: out; the tackle
    assert len(t) == 1, len(t)                           #  state 0: a foul, else the good-tackle / direction tests)
    ja = t[0].start() + 7
    foul = t[0].end() + struct.unpack('<b', t[0].group(1))[0]
    p.put(1, ja, b'\xe9' + struct.pack('<i', foul - (ja + 5)) + b'\x90')   # every tackle that touches: a foul
    print(f'exe: CARDS_FORCE={mode} (test build: every tackle a foul, every foul outside the box a last-man foul, its '
          f'card the {mode}) obj1+{ja:#x} / +{jz[0]:#x} / +{jb - 1:#x}')
