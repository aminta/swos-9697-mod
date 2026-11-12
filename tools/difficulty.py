"""4.2 selectable difficulty + DRIBBLING folded in (Davide 12/11; design internal/handoff/difficulty-fable.md, build plan
internal/handoff/difficulty-plan.md). Branch 42-diff, beta for Davide + Gianfranco.

Who: a level other than NORMAL changes only a pure computer team facing a human (TeamFile.teamControls 1 v 2 at the
kick-off knobs; in the match TeamGeneralInfo playerNumber / playerCoachNumber both 0 against a playerNumber != 0) and,
for the dribbling rows, that human's own side. Two humans, computer v computer, coach teams, training games, SWOS++ and
simulated results (CalculateViewResult never runs the engine) keep the original game at every level.

Levels: a 5-row table (L1..L5, L3 = NORMAL = every value the exe's own); the screen shows L1 / L3 / L5 as EASY /
NORMAL / HARD. DF_W (the option, saved later as engine item 'DF') 0 = NORMAL, 1 = L1, 2 = L5, 3 = L2, 4 = L4. DF_ACT
(set at every kick-off, InitializeInGameTeamsAndStartGame's @@init_in_game_teams) = the level 1..5, or 0 = off (NORMAL,
SWOS++, a training game): every stub's first test, so with 0 every stub does the original instruction(s) only.

Knobs (sites found by bytes in obj1, every language; each overwritten instruction's fixups dropped, the stub redoes it):
- K1 opposition skills % (ScaleSkill: `mov ax, D2 / mul word D3` -> D3 *= K1 / 100 first);
- K2 opposition keeper +-points, clamped 0..7 (AdjustPlayerSkills @@set_goalie_skill);
- K2b opposition keeper close-shot index shift (UpdatePlayers' `add D1, 7` before goalScoredChances: index - shift,
  clamped 0..14; one step = 1/16 of goal chance);
- K3 opposition pass-error table (DoPass `mov A1, offset kAIFailedPassChance`);
- K4 ball carrier slowdown speed -= speed * k >> 5 per side (UpdatePlayerSpeed; k 4 = the original shr 3; dribble.py's A);
- K8 second-chaser hold-back radius per side (UpdatePlayers' two `cmp ballDistance, 3200`; dribble.py's B);
- K5 CPU slide radius per side (CpuPlayerAttemptTackle `cmp ballDistance, 200`);
- K9 won-the-ball protection per side (the two `wonTheBallTimer = 12`; dribble.py's C);
- K10 sharp-turn run-ahead of the ball per side (CalculateIfPlayerWinsBall `add ball speed, 256`; calm study's I).
No stub calls Rand / Rand2; at DF_ACT 0 (and at L3) every register, flag that is read later and memory word ends as the
original's.

Test switches (modver TEST_VARS, never in a release build): DIFF_TEST=1..5 = the stubs in + DF_W's start level (until the
OPTIONS row exists); DIFF_FORCE=1 = the proxy match: a coach team (TEAM_COACH / playerCoachNumber) counts as the human.
Harness: the data block's tag 'DIFF' (DF_W, DF_ACT, counters).
"""
import os
import re
import struct

import nasmcave

TAG = b'DIFF'
LVMAP = (3, 1, 5, 2, 4)                 # DF_W -> level
#              L1      L2      L3      L4      L5
K1 = (80, 90, 100, 105, 110)            # opposition skills %
K2 = (-2, -1, 0, 1, 2)                  # opposition keeper points
K2B = (-1, 0, 0, 1, 2)                  # opposition keeper close-shot index shift
K3 = ((9, 7, 6, 5, 4, 3, 2, 1), (7, 5, 4, 3, 2, 1, 1, 0), (6, 4, 3, 2, 1, 0, 0, 0), (5, 3, 2, 1, 1, 0, 0, 0),
      (4, 3, 2, 1, 0, 0, 0, 0))         # opposition pass errors of 16, by passing 0..7 (L3 = kAIFailedPassChance)
NORM = dict(k=4, lock=12, turn=256, hold=3200, slide=200)
USER = dict(k=(2, 3, 4, 3, 3), lock=(16, 16, 12, 14, 14), turn=(192, 224, 256, 224, 224), hold=(3200,) * 5,
            slide=(200,) * 5)           # the human's side
OPP = dict(k=(4,) * 5, lock=(12,) * 5, turn=(256,) * 5, hold=(4400, 4400, 3200, 4400, 4400),
           slide=(120, 160, 200, 160, 160))   # the opposition's side
for _t in (USER, OPP):
    assert all(_t[f][2] == NORM[f] for f in NORM), 'L3 must be the original game'
assert K1[2] == 100 and K2[2] == 0 and K2B[2] == 0 and K3[2] == (6, 4, 3, 2, 1, 0, 0, 0)

ASM = r"""
; ---- the kick-off: DF_ACT for this match (replaces `mov A6, offset team1AppPercent` at @@init_in_game_teams)
df_kick:
    push eax
    xor eax, eax
    cmp byte [SWOSPP], 0FFh             ; (0FFh = no SWOS++)
    jne .s
    cmp word [TRG], 0                   ; a training game
    jne .s
    mov al, [DF_W]
    cmp al, 4
    ja .z
    mov al, [LVMAP + eax]
    cmp al, 3
    jne .s
.z: xor eax, eax
.s: mov [DF_ACT], al
    inc dword [DF_KICKS]
    pop eax
    mov dword [A6_], T1APP
    ret

; ---- ZF = 1: the team file in A2 is the opposition (computer) and A3's a human (player-coach; DIFF_FORCE: a coach too)
df_oppfile:
    push esi
    mov esi, [A2_]
    cmp byte [esi + 4], 1
    jne .x
    mov esi, [A3_]
    cmp byte [esi + 4], 2
%if DIFF_FORCE
    je .x
    cmp byte [esi + 4], 3
%endif
.x: pop esi
    ret

; ---- K1: ScaleSkill (replaces `mov ax, D2` / `mul word D3`)
df_scale:
    cmp byte [DF_ACT], 0
    je .o
    call df_oppfile
    jne .o
    push ebx
    push edx
    movzx ebx, byte [DF_ACT]
    mov bx, [K1T - 2 + ebx * 2]
    cmp bx, 100
    je .p
    mov ax, [D3_]
    mul bx
    mov bx, 100
    div bx
    mov [D3_], ax
.p: pop edx
    pop ebx
.o: mov ax, [D2_]
    mul word [D3_]
    ret

; ---- K2: the keeper's skill (replaces `mov al, D0` / `mov esi, A6` at @@set_goalie_skill)
df_gk:
    cmp byte [DF_ACT], 0
    je .o
    call df_oppfile
    jne .o
    push eax
    movzx eax, byte [DF_ACT]
    movsx ax, byte [K2T - 1 + eax]
    add ax, [D0_]
    jns .n
    xor eax, eax
.n: cmp ax, 7
    jle .c
    mov ax, 7
.c: mov [D0_], ax
    pop eax
.o: mov al, [D0_]
    mov esi, [A6_]
    ret

; ---- who: in ebx = TeamGeneralInfo; out al = 0 (the original game), 1 (the human facing the opposition),
;      2 (the opposition: a computer team facing a human). Other registers kept.
df_who:
    push ecx
    xor eax, eax
    mov ecx, [ebx]                      ; (opponentsTeam)
    test ecx, ecx
    jz .x
    cmp word [ebx + 4], 0
    jne .meu
%if DIFF_FORCE
    cmp word [ebx + 6], 0
    jne .meu
%endif
    cmp word [ebx + 6], 0               ; me: a computer team?
    jne .x
    cmp word [ecx + 4], 0               ; ... facing a human
%if DIFF_FORCE
    jne .two
    cmp word [ecx + 6], 0
%endif
    je .x
.two:
    mov al, 2
    jmp .x
.meu:                                   ; me: the human; the opponent a computer team?
    cmp word [ecx + 4], 0
    jne .x
    cmp word [ecx + 6], 0
    jne .x
    mov al, 1
.x: pop ecx
    ret

; ---- in ebx = TeamGeneralInfo; out ebx = its side's block (BLK_N, or the level's human / opposition row)
df_blk:
    cmp byte [DF_ACT], 0
    je .n
    push eax
    call df_who
    test al, al
    jz .n0
    movzx ebx, byte [DF_ACT]
    dec ebx
    cmp al, 2
    jne .u
    add ebx, 5
.u: shl ebx, 4
    add ebx, BLK_U
    pop eax
    ret
.n0:
    pop eax
.n: mov ebx, BLK_N
    ret

; ---- K3: DoPass (replaces `mov A1, offset kAIFailedPassChance`)
df_pass:
    mov dword [A1_], KFAIL
    cmp byte [DF_ACT], 0
    je .o
    push eax
    push ebx
    mov ebx, [A6_]
    call df_who
    cmp al, 2
    jne .p
    movzx ebx, byte [DF_ACT]
    dec ebx
    shl ebx, 4
    add ebx, K3T
    mov [A1_], ebx
.p: pop ebx
    pop eax
.o: ret

; ---- K2b: the close shot (replaces `add word D1, 7` before goalScoredChances; A6 = the keeper's team)
df_goal:
    add word [D1_], 7
    cmp byte [DF_ACT], 0
    je .o
    push eax
    push ebx
    mov ebx, [A6_]
    call df_who
    cmp al, 2
    jne .p
    movzx ebx, byte [DF_ACT]
    movsx ax, byte [K2BT - 1 + ebx]
    test ax, ax
    jz .p
    sub [D1_], ax
    jns .h
    mov word [D1_], 0
.h: cmp word [D1_], 14
    jle .p
    mov word [D1_], 14
.p: pop ebx
    pop eax
.o: ret

; ---- K4: the carrier (replaces UpdatePlayerSpeed's 37 B `D0 = speed >> 3; speed -= D0`; esi = A1, A6 his team)
df_carrier:
    push ebx
    push edx
    mov ebx, [A6_]
    call df_blk
    movzx edx, word [esi + 2Ch]
    movzx ebx, word [ebx]
    imul edx, ebx
    shr edx, 5
    mov ax, dx
    mov [D0_], ax
    pop edx
    pop ebx
    mov esi, [A1_]
    sub [esi + 2Ch], ax
    ret

; ---- K8: the second chaser's hold-back (replaces `cmp dword [esi + Sprite.ballDistance], 3200`; A6 his team)
df_hold:
    push ebx
    mov ebx, [A6_]
    call df_blk
    mov ebx, [ebx + 8]
    cmp [esi + 4Ah], ebx
    pop ebx
    ret

; ---- K5: the CPU slide (replaces `cmp dword [esi + Sprite.ballDistance], 200`; A6 the tackler's team)
df_slide:
    push ebx
    mov ebx, [A6_]
    call df_blk
    mov ebx, [ebx + 12]
    cmp [esi + 4Ah], ebx
    pop ebx
    ret

; ---- K9: the won-the-ball protection (replaces `mov word [esi + TeamGeneralInfo.wonTheBallTimer], 12`; esi the team)
df_lock:
    push ebx
    mov ebx, esi
    call df_blk
    mov bx, [ebx + 2]
    mov [esi + 8Ah], bx
    pop ebx
    ret

; ---- K10: the sharp turn (replaces `add word [esi + Sprite.speed], 256` on the ball; A6 the carrier's team)
df_turn:
    push ebx
    mov ebx, [A6_]
    call df_blk
    mov bx, [ebx + 4]
    add [esi + 2Ch], bx
    pop ebx
    ret

align 4
TAGW: db 'DIFF'
DF_W: db DF_START                       ; (the option: 0 NORMAL, 1 L1, 2 L5, 3 L2, 4 L4)
DF_ACT: db 0                            ; (this match's level, 0 = off)
DF_SH: db DF_START                      ; (the session's value: a new career zeroes the item)
db 0
DF_KICKS: dd 0                          ; (kick-offs seen: harness)
LVMAP: db 3, 1, 5, 2, 4
align 2
"""


def _blk(t, i):
    g = (lambda f: t[f][i]) if i is not None else (lambda f: t[f])
    return struct.pack('<HHHHII', g('k'), g('lock'), g('turn'), 0, g('hold'), g('slide'))


def data_asm():
    db = lambda bs: 'db ' + ', '.join(str(b) for b in bs) + '\n'
    out = 'K1T: dw ' + ', '.join(map(str, K1)) + '\n'
    out += 'K2T: db ' + ', '.join(str(v & 0xff) for v in K2) + '\n'
    out += 'K2BT: db ' + ', '.join(str(v & 0xff) for v in K2B) + '\n'
    out += 'align 16\nBLK_N: ' + db(_blk(NORM, None))
    out += 'BLK_U: ' + ''.join(db(_blk(USER, i)) for i in range(5))      # (BLK_U + 16 * (level - 1); the opposition's
    out += ''.join(db(_blk(OPP, i)) for i in range(5))                  # rows follow: + 80)
    out += 'K3T: ' + ''.join('dw ' + ', '.join(map(str, r)) + '\n' for r in K3)
    return out


def on():
    return bool(os.environ.get('DIFF_TEST'))


def start_w():
    lv = int(os.environ.get('DIFF_TEST', '3') or '3')
    assert 1 <= lv <= 5, 'DIFF_TEST=1..5'
    return LVMAP.index(lv)


def _one(pat, d, name, n=1):
    m = [x.start() for x in re.finditer(pat, d, re.S)]
    assert len(m) == n, (name, [hex(x) for x in m])
    return m


def find(p):
    """Every site (obj1 offsets) and the game's symbols, from the exe's own bytes (any language)."""
    import dribble
    d = p.le.obj_bytes(1)
    t = lambda o: p.target(1, o)
    sc = _one(rb'\x66\xa1....\x66\xa3....\x81\x3d........\x74\x0c\x66\xa1....\x66\xa3....\x66\xa1....\x66\xf7\x25....'
              rb'\x66\xa3', d, 'ScaleSkill')[0]
    gk = _one(rb'\x66\x83\x3d....\x07\x7e\x09\x66\xc7\x05....\x07\x00\x66\xa1....\x66\x0b\xc0\x79\x09\x66\xc7\x05....'
              rb'\x00\x00\xa0....\x8b\x35....\x88\x46\x4c\xc3', d, 'set_goalie_skill')[0]
    ps = _one(rb'\xc7\x05........\x66\xa1....\x66\xa3....\x66\x83\x25....\x1e\x66\xd1\x2d', d, 'DoPass')[0]
    gl = _one(rb'\x66\x83\x05....\x07\xc7\x05........\x66\xa1....\x66\xa3....\x66\xd1\x2d....\x66\x83\x25....\x0f',
              d, 'goalScoredChances')[0]
    sl = _one(rb'\x81\x7e\x4a\xc8\x00\x00\x00\x0f\x87', d, 'CpuPlayerAttemptTackle')[0]
    tu = _one(rb'\x8b\x35....\x66\x81\x46\x2c\x00\x01', d, 'sharp turn')[0] + 6
    car = _one(dribble.A, d, 'carrier')[0]
    hold = _one(dribble.B, d, 'hold-back', 2)
    lock = _one(dribble.C, d, 'wonTheBallTimer', 2)
    s = dict(SC=sc + 36, GK=gk + 39, PS=ps, GL=gl, SL=sl, TU=tu, CAR=car, HOLD=hold, LOCK=lock)
    d0 = t(gk + 40)
    var = lambda k: (2, d0[1] + 4 * k)                  # D0..D7, A0..A6: consecutive dwords
    sym = dict(D0_=d0, D1_=var(1), D2_=var(2), D3_=var(3), A1_=var(9), A2_=var(10), A3_=var(11), A4_=var(12),
               A6_=var(14), T1APP=t(sc + 2), KFAIL=t(ps + 6))
    assert t(sc + 38) == sym['D2_'] and t(sc + 45) == sym['D3_'] and t(sc + 14) == sym['A4_'], 'ScaleSkill vars'
    assert t(gk + 46) == sym['A6_'] and t(ps + 2) == sym['A1_'] and t(gl + 3) == sym['D1_'], 'vars'
    assert t(car + 6) == d0 and t(car + 29) == sym['A1_'], 'carrier vars'
    ki = [m.start() for m in re.finditer(rb'\xc7\x05', d) if m.start() + 10 <= len(d)]
    ki = [o for o in ki if _t(p, o + 2) == sym['A6_'] and _t(p, o + 6) == sym['T1APP']]
    assert len(ki) == 1, ('@@init_in_game_teams', ki)
    s['KICK'] = ki[0]
    return s, sym


def _t(p, o):
    try:
        return p.target(1, o)
    except AssertionError:
        return None


def _hook(p, at, n, orig_len, label_off):
    """Drop the fixups inside obj1 at..at+n, then `call obj4:label_off` + nops."""
    for o in range(at, at + n):
        if _t(p, o) is not None:
            p.remove(1, o)
    p.branch(1, at, 0xE8, 4, label_off, n=n)


def patch(p, lang):
    if not on():
        return None
    import controls
    import dribble
    import gkinj
    import swreg
    assert not dribble.on(), 'DIFF_TEST and DRIBBLE_TEST: the carrier site is one (difficulty has the DRIBBLING rows)'
    force = bool(os.environ.get('DIFF_FORCE'))
    import modver
    assert modver.is_test(), 'DIFF_TEST: test builds only (until the OPTIONS row)'
    s, sym = find(p)
    sym['SWOSPP'] = controls.locate(p)['SWOSPP']
    sym['TRG'] = gkinj.find(p)['TRG']
    orig = {k: p.get(1, s[k], n) for k, n in (('SC', 13), ('GK', 11), ('PS', 10), ('GL', 8), ('SL', 7), ('TU', 6),
                                              ('CAR', 37), ('KICK', 10))}
    assert orig['GL'][:3] == b'\x66\x83\x05' and orig['TU'] == b'\x66\x81\x46\x2c\x00\x01', 'sites already patched'
    at = swreg.DIFF_AT
    src = f'%define DIFF_FORCE {int(force)}\n%define DF_START {start_w()}\n' + ASM + data_asm()
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert at + len(code) <= swreg.DIFF_END, ('difficulty: past its obj4 room', hex(at + len(code)))
    assert p.le.obj(4).npages * 0x1000 >= swreg.DIFF_END, 'difficulty: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.DIFF_END - at)), 'difficulty: obj4 room not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    for key, n, l in (('KICK', 10, 'df_kick'), ('SC', 13, 'df_scale'), ('GK', 11, 'df_gk'), ('PS', 10, 'df_pass'),
                      ('GL', 8, 'df_goal'), ('SL', 7, 'df_slide'), ('TU', 6, 'df_turn'), ('CAR', 37, 'df_carrier')):
        _hook(p, s[key], n, n, lab[l])
    for o in s['HOLD']:
        _hook(p, o, 7, 7, lab['df_hold'])
    for o in s['LOCK']:
        _hook(p, o, 9, 9, lab['df_lock'])
    LABELS.clear()
    LABELS.update(lab)
    SITES.clear()
    SITES.update(s)
    print(f'exe: difficulty test (DIFF_TEST={os.environ["DIFF_TEST"]}{", DIFF_FORCE" if force else ""}): code '
          f'obj4+{at:#x} ({len(code)} B), 14 obj1 sites')
    return at + len(code)


LABELS = {}
SITES = {}
