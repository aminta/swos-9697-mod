"""4.0.6 (Davide): goalkeeper injuries - an OPTIONS row INFORTUNI PORTIERI, ON by default: after every match a 1 in 25
roll per team for its keeper; a hit keeps him out of the next one or two matches (50 / 50), through the game's own
injury level (the cardsInjuries bits E0h of his record) and the game's own countdown. No in-match event; our own RNG
(xorshift32, seeded once from the BIOS tick), so the game's Rand sequence is not shifted.

The keeper: a match played for real - the in-game team's PlayerInfo slot 0 at the final whistle (a substitution swaps
the whole PlayerInfo, so slot 0 is the keeper on the pitch then), rolled after each of InitializeInGameTeamsAndStartGame's
`call UpdatePlayerInjuries` (chained on its current target; training games skipped, as the game skips them), his record
found by the game's GetPlayer as UpdatePlayerInjuries does; not rolled when that slot was substituted (.substituted)
or injured in the match (.isInjured: the game wrote his level) - gk_upi keeps the PlayerInfo / file pointers, so a
subbed-off keeper (a later option) is one more slot to roll. A simulated result (CalculateViewResult: CPU - CPU, the
human's VIEW RESULT) - after its cseg_903B1 (chained after cpucards' cb_903), the keeper = the team's line-up slot 0
(currentMatchPlayers for the career club, the file's order at +3Ch for any other). Never a keeper whose record already
has an injury level (20h included).

Who: human teams always (row ON); a computer team only in a season or a career and when INFORTUNI ALLA CPU is ON too
(cpucards' CC_I = 0: the CPU's injuries are then kept and counted down by cpucards step B, cb_day - on the calendar days
of the PLAY MATCH menu, seasons and careers: harness cpu_inj_season; a DIY / preset competition has no such day, so a
CPU keeper there would never heal). Off under SWOS++ (controls' rule: its own options).

The levels (cseg_2CED3, one tick per match day before the line-up's check... measured by the harness): LVL1 = out of
the next match, LVL2 = out of the next two.

The option: the word GI_W (0 = ON, 1 = OFF; the string table lists ON first), saved with a career as the engine item
'GI' (2 bytes; a save without it loads 0 = ON); GI_SH keeps the session's value for a new career (engine.after_new).
The row: OPTIONS entries 24 / 25 (after cpucards' 20..23), copies of its ROSSI ALLA CPU row 12 px above it - order
INFORTUNI PORTIERI / ROSSI ALLA CPU / INFORTUNI ALLA CPU over the game length - by the menu's init / on-return
functions chained after cpucards' cc_init / cc_ret.

GKINJ_FORCE (test builds only, modver TEST_VARS): 1 = every roll hits (the level still 50 / 50), 1m / 2m = every roll
hits at LVL1 / LVL2. The harness finds the data block by its tag 'GKIJ' (GK_ROLLS, GK_HITS, GK_LAST, GK_SEED, GI_W).
"""
import os
import re
import struct

import nasmcave

LABEL = {'it': 'INFORTUNI PORTIERI', 'en': 'GOALKEEPER INJURIES', 'fr': 'BLESSURES DES GARDIENS',
         'de': 'TORWARTVERLETZUNGEN'}
ODDS = 25                               # 1 in 25 per team per match
LVL1, LVL2 = 0x40, 0x60                 # out of the next match / the next two (the harness measures them)
TAG = b'GKIJ'

ASM = r"""
gk_init:                                ; OPTIONS' init: the previous one (cpucards), then our row
    call PREV_INIT
    jmp gk_add
gk_ret:                                 ; (and on return to OPTIONS)
    call PREV_RET
gk_add:
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no row
    jne .x
    mov ebx, MENU_
    cmp word [ebx + 10h], 24            ; (cpucards' 24 entries, nothing after them)
    jne .x
    lea eax, [ebx + 16h + 24 * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries 24 / 25 = copies of cpucards' red-cards row (20 / 21)
    lea esi, [ebx + 16h + 20 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], 24              ; 12 px above it
    sub word [edi + 16h], 12
    mov dword [edi + 26h], S_LG
    mov word [edi + 38h + 2], 25
    sub word [edi + 38h + 16h], 12
    mov dword [edi + 38h + 26h], TAB_G
    mov dword [edi + 38h + 2Ah], gk_tog
    mov word [edi + 38h + 0Ah], 15FFh   ; (up: none, down: 21 - and 21's up: 25)
    mov word [edi + 38h + 12h], 15FFh
    mov byte [ebx + 16h + 21 * 38h + 0Ah], 25
    mov byte [ebx + 16h + 21 * 38h + 12h], 25
    mov word [ebx + 10h], 26
    add dword [ebx + 12h], 2 * 38h
.x: popad
    ret

gk_tog:                                 ; the value (fire): toggled, to the session copy too
    xor word [GI_W], 1
    mov ax, [GI_W]
    mov [GI_SH], ax
    jmp DRAWITEM

gk_load:                                ; after a career load: the save's value (0 = ON when the save has no 'GI')
    mov ax, [GI_W]
    mov [GI_SH], ax
    ret
gk_new:                                 ; after a new career's defaults (its items zeroed): the session's value back
    mov ax, [GI_SH]
    mov [GI_W], ax
    ret

gk_rng:                                 ; eax = the next xorshift32 (seeded at the first roll from the BIOS tick)
    mov eax, [GK_SEED]
    test eax, eax
    jnz .s
    mov eax, [46Ch]
    xor eax, 9E3779B9h
    jnz .s
    inc eax
.s: mov edx, eax
    shl edx, 13
    xor eax, edx
    mov edx, eax
    shr edx, 17
    xor eax, edx
    mov edx, eax
    shl edx, 5
    xor eax, edx
    mov [GK_SEED], eax
    ret

gk_apply:                               ; ebx = the keeper's record, esi = his team file: the roll
    cmp word [GI_W], 0
    jne .x
    cmp byte [SWOSPP], 0FFh
    jne .x
    cmp byte [esi + 4], 1               ; (a computer team: only with INFORTUNI ALLA CPU ON, in a season or a
    jne .h                              ;  career - the modes whose calendar days run cpucards' cb_day, the CPU's
    cmp word [CC_I], 0                  ;  countdown: GT 3 / 4; DIY and preset competitions, friendlies none)
    jne .x
    cmp word [GT], 3
    jb .x
.h: test byte [ebx + 1Bh], 0E0h         ; (already injured: no roll)
    jnz .x
    inc dword [GK_ROLLS]
    call gk_rng
%if FORCE == 0
    xor edx, edx
    mov ecx, ODDS
    div ecx
    test edx, edx
    jnz .x
%endif
    call gk_rng
    mov dl, LVL1
%if FORCE == 2
    mov dl, LVL2
%elif FORCE < 2
    test eax, 10000h
    jz .l
    mov dl, LVL2
%endif
.l: and byte [ebx + 1Bh], 1Fh
    or [ebx + 1Bh], dl
    inc dword [GK_HITS]
    mov [GK_LAST], ebx
.x: ret

gk_upi:                                 ; replaces InitializeInGameTeamsAndStartGame's `call UpdatePlayerInjuries`
    push eax                            ; (A1 = the in-game team, A2 = its file; the caller keeps D0 .. A6 itself)
    mov eax, [A1_]
    mov [GK_A1], eax
    mov eax, [A2_]
    mov [GK_A2], eax
    pop eax
    call UPI
    pushad
    cmp word [TRG], 0                   ; (a training game: no roll, as the game's own injuries)
    jne .x
    mov esi, [GK_A1]
    add esi, 2Ah                        ; (PlayerInfo slot 0: the keeper at the final whistle)
    call gk_slot
.x: popad
    ret

gk_slot:                                ; esi = an in-game PlayerInfo of team file [GK_A2]: its player rolled
    cmp byte [esi], 0                   ; (.substituted: out of the match)
    jne .r
    cmp byte [esi + 6], 0               ; (.isInjured: the game wrote his level)
    jne .r
    push esi
    lea esi, [D0_]                      ; (the game's memory registers D0 .. A6 kept around GetPlayer)
    lea edi, [REGSAV]
    mov ecx, 15
    rep movsd
    pop esi
    mov edi, [GK_A2]
    mov ax, [edi]                       ; (D0 = TeamFile.countryNumber, D1 = .playerIndex: as UpdatePlayerInjuries)
    mov [D0_], ax
    movsx ax, byte [esi + 1]
    mov [D1_], ax
    call GETPLAYER
    mov ebx, [A0_]
    add ebx, 4Ch
    mov esi, [GK_A2]
    call gk_apply
    lea esi, [REGSAV]
    lea edi, [D0_]
    mov ecx, 15
    rep movsd
.r: ret

gk_903:                                 ; replaces CalculateViewResult's `call cseg_903B1` (cpucards' cb_903 now;
    push dword [A0_]                    ; A0 = the team file): a simulated result's keeper
    call F903
    pushad
    mov esi, [esp + 32]
    cmp word [TRG], 0
    jne .x
    movzx eax, byte [esi + 3Ch]         ; (line-up slot 0: the file's order, the career club's currentMatchPlayers)
    cmp esi, CAREER
    jne .r
    movzx eax, byte [CMPL]
.r: imul eax, eax, 26h
    lea ebx, [esi + eax + 4Ch]
    call gk_apply
.x: popad
    add esp, 4
    ret

align 4
GK_TAG: db 'GKIJ'
GK_ROLLS: dd 0                          ; (rolls / hits so far, the last record hit, the RNG: read by the harness)
GK_HITS: dd 0
GK_LAST: dd 0
GK_SEED: dd 0
GI_W: dw 0                              ; (the engine item 'GI': 0 = ON)
GI_SH: dw 0                             ; (the session's value: a new career zeroes the item)
GK_A1: dd 0
GK_A2: dd 0
TAB_G: dd GI_W                          ; (the game's string table: variable, first index, its strings)
    dw 0
    dd S_ON, S_OFF
REGSAV: times 15 dd 0
"""


def find(p):
    """UpdatePlayerInjuries (cpucards' guard 9 - 6) and its 4 calls, GetPlayer (its one call), g_trainingGame
    (cseg_903B1's first `mov ax`), careerTeam / currentMatchPlayers (cseg_2CDC6's `cmp A0, offset` / `mov A5, offset`)."""
    import cpucards
    d = p.le.obj_bytes(1)
    b = cpucards.find_b(p)
    rel = lambda o, n: o + n + struct.unpack_from('<i', d, o + n - 4)[0]
    upi = b['guards'][9][0] - 6
    assert d[upi:upi + 2] == b'\x8b\x35' and d[upi + 16:upi + 22] == b'\x66\xc7\x05' + d[upi + 19:upi + 22], 'UPI'
    calls = [m.start() for m in re.finditer(rb'\xe8', d) if m.start() + 5 <= len(d) and rel(m.start(), 5) == upi]
    assert len(calls) == 4, calls
    gp = [m.start() for m in re.finditer(rb'\x66\xa3....\xe8', d[upi:upi + 0xB0], re.S)]
    assert len(gp) == 1, gp
    gt = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\x04', d[b['F903']:b['F903'] + 0x80], re.S)]
    assert len(gt) == 1, gt                              # (g_gameType: cseg_903B1's `cmp g_gameType, 4`)
    c6 = b['guards'][6][0] - 6
    assert d[c6 + 16:c6 + 18] == b'\x81\x3d' and d[c6 + 26:c6 + 28] == b'\x0f\x85' and d[c6 + 32:c6 + 34] == b'\xc7\x05', \
        'cseg_2CDC6'
    return dict(UPI=upi, calls=calls, GETPLAYER=rel(upi + gp[0] + 6, 5), TRG=p.target(1, b['F903'] + 2),
                CAREER=p.target(1, c6 + 22), CMPL=p.target(1, c6 + 38), calls903=b['calls903'],
                GT=p.target(1, b['F903'] + gt[0] + 3))


def patch(p, at, lang):
    """Code + data at obj3:at (the obj3 chain's end); returns the end. Chained on the UpdatePlayerInjuries calls'
    current targets, cpucards' cb_903 hooks and cc_init / cc_ret (p.call_target / the header pointers)."""
    import controls
    import cpucards
    import engine
    import sacups
    import zones
    from complist import px
    s = find(p)
    d = p.le.obj_bytes(1)
    sym0 = controls.locate(p)
    hdr = controls.menu_header(p, sym0['OMBD'][1])
    prev = [p.target(2, hdr + k) for k in (0, 4)]
    assert prev == [(3, cpucards.LABELS['cc_init']), (3, cpucards.LABELS['cc_ret'])], ('OPTIONS init / return', prev)
    label = LABEL[lang]
    assert px(label) <= 138 and re.fullmatch(r'[A-Z ]+', label), label
    off, on = cpucards.strings(p, hdr)
    force = {'': 0, '1': 1, '1m': 3, '2m': 2}[os.environ.get('GKINJ_FORCE', '')]
    lv1 = LVL2 if force == 2 else LVL1
    db = lambda x: ', '.join(str(c) for c in x.encode() + b'\0')
    src = f'%define FORCE {force}\n%define ODDS {ODDS}\n%define LVL1 {lv1:#x}\n%define LVL2 {LVL2:#x}\n' + ASM \
        + f'S_LG: db {db(label)}\n'
    regs = sacups.regs(d)
    d0 = regs['D7'] - 28
    assert regs['A0'] == d0 + 32, 'D0 .. D7, A0 .. A6 contiguous'
    tg = [p.call_target(1, c) for c in s['calls903']]
    assert len(set(tg)) == 1 and tg[0] == (3, cpucards.LABELS['cb_903']), ('cseg_903B1 calls', tg)
    tu = [p.call_target(1, c) for c in s['calls']]
    assert len(set(tu)) == 1, ('UpdatePlayerInjuries calls', tu)
    sym = {'PREV_INIT': prev[0], 'PREV_RET': prev[1], 'SWOSPP': sym0['SWOSPP'], 'MENU_': zones._current_menu(p),
           'DRAWITEM': (1, cpucards.find(p)['DRAWITEM']), 'S_ON': on, 'S_OFF': off, 'CC_I': (3, cpucards.LABELS['CC_I']),
           'A0_': (2, regs['A0']), 'A1_': (2, regs['A0'] + 4), 'A2_': (2, regs['A0'] + 8), 'D0_': (2, d0),
           'D1_': (2, d0 + 4), 'UPI': tu[0], 'GETPLAYER': (1, s['GETPLAYER']), 'TRG': s['TRG'], 'F903': tg[0],
           'CAREER': s['CAREER'], 'CMPL': s['CMPL'], 'GT': s['GT']}
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    for c in s['calls']:
        p.branch(1, c, 0xE8, 3, lab['gk_upi'])
    for c in s['calls903']:
        p.branch(1, c, 0xE8, 3, lab['gk_903'])
    for k, l in ((0, 'gk_init'), (4, 'gk_ret')):
        p.retarget(2, hdr + k, 3, lab[l])
        p.put(2, hdr + k, struct.pack('<I', lab[l]))
    engine.ITEM_AT['GI'] = (3, lab['GI_W'])
    engine.CALL_AT['gk_load'] = (3, lab['gk_load'])
    engine.CALL_AT['gk_new'] = (3, lab['gk_new'])
    LABELS.update(lab)
    print(f'exe: goalkeeper injuries (OPTIONS: {label}, 1/{ODDS}, levels {LVL1:#x} / {LVL2:#x}'
          f'{", GKINJ_FORCE=" + os.environ["GKINJ_FORCE"] if force else ""}): code obj3+{at:#x} ({len(code)} B), '
          f'UpdatePlayerInjuries calls {[hex(c) for c in s["calls"]]}')
    return at + len(code)


LABELS = {}
