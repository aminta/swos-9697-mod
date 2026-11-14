"""4.2 set pieces M3 (MC GO 14/11): the corner meter - TEST BUILDS ONLY (SP_METER=1, needs DIFF_TRACE).

Design: internal/handoff/setpieces-wingplay-design.md section 6. The meter runs once per live frame from difficulty's
df_frame (DIFF_TRACE: every frame = one tick, both random generators pinned at the kick-off, so a (build, pairing,
seed) is one deterministic match). It forces corners through the game's own path and logs what follows:

- Forcing: when play is live (gameStatePl = gameState = ST_GAME_IN_PROGRESS), SM_GAP frames after the last window and
  fewer than SM_MAXC corners so far, the ball is put past a goal line, wide of the posts, with lastTeamPlayed = the
  team defending that goal: CheckIfBallOutOfPlay then awards the corner itself (gameState ST_CORNER_LEFT / RIGHT,
  cornersWon + 1, the break, the CPU taker). Corner k: bit 0 = the goal (0 top, 1 bottom), bit 1 = the side (0 left x
  150, 1 right x 520), so both teams take corners from both flags in both halves. The poke is repeated each frame
  until the corner state shows (a dribbler may drag the ball back for a frame), at most 30 frames (then a FAIL entry).
- Window: SM_WIN frames of play from the corner kick (gameState back to ST_GAME_IN_PROGRESS; entry 11). Inside it every change is logged (16 B entries, SM_LOG..):
  gameState (with the ball's previous-frame x / y / z: where it crossed a line), gameStatePl, lastPlayerPlayed (a
  touch: the sprite's team / ordinal / playerState + the ball's x / y / z), lastKeeperPlayed, the goals, and any
  player sprite entering a keeper or header state (4 catching, 6 / 7 diving, 8 / 9 heading, 11 claimed).
- tools/sp_corners.py classifies each corner offline from the log (goal, over the bar, wide, keeper catch / claim,
  cleared ...) - the rules live in Python, the exe only records.

The meter changes the match (the forced corners): its numbers compare builds on the same forced situations (CLASSICI
vs NUOVI), never a normal match. Room: obj4 SPM_AT..SPM_END (4 pages past every 4.2 band), linked only with SP_METER.
"""
import os
import re
import struct

import nasmcave

SPM_AT = 0x30000                         # (MC 14/11: the high test region 0x30000.., clear of every live 4.2 band)
SPM_END = 0x34000
LOG_AT = 0x1000                         # (from SPM_AT: 3 pages = 768 entries of 16 B)
LOGMAX = (SPM_END - SPM_AT - LOG_AT) // 16
TAG = b'SPMT'
# the block's fields, from the tag (the harness reads / pokes them)
OFF = dict(ST=4, FK=5, NC=6, NF=8, NFAIL=10, T0=12, LAST=16, LN=20, LDROP=24, GAP=28, WIN=30, MAXC=32, MODE=34,
           FKORD=35, FKD=36, FKX=44, FKSH=50)


def on():
    return bool(os.environ.get('SP_METER'))


ASM = r"""
spm_frame:                              ; difficulty's df_frame calls this once per live frame (inside its pushad)
    call .n
.n: pop ebp
    sub ebp, .n - SPB
    mov edi, [ebp]                      ; edi = obj2's base (the only fixup)
    lea edx, [dword ebp + CURB - SPB]   ; this frame's ball x / y / z (the words above the fractions)
    lea esi, [edi + BALL_O]
    mov ax, [esi + 20h]
    mov [edx], ax
    mov ax, [esi + 24h]
    mov [edx + 2], ax
    mov ax, [esi + 28h]
    mov [edx + 4], ax
    call spm_watch
    mov al, [dword ebp + ST - SPB]
    cmp al, 1
    je .forcing
    cmp al, 2
    je .window
    cmp word [edi + GSP_O], 100         ; idle: play live, the gap over, corners left
    jne .done
    cmp word [edi + GS_O], 100
    jne .done
    mov eax, [dword ebp + DF_FRAMES - SPB]
    sub eax, [dword ebp + LAST - SPB]
    movzx ecx, word [dword ebp + GAP - SPB]
    cmp eax, ecx
    jb .done
    mov ax, [dword ebp + NC - SPB]
    cmp ax, [dword ebp + MAXC - SPB]
    jae .done
    mov byte [dword ebp + ST - SPB], 1
    mov byte [dword ebp + FK - SPB], 0
    inc word [dword ebp + NF - SPB]
    mov al, 1                           ; (entry 1: forcing starts; its ord byte = the corner's index)
    xor esi, esi
    call spm_log
.forcing:
    mov ax, [edi + GS_O]
    cmp byte [dword ebp + MODE - SPB], 0
    jne .fkw
    cmp ax, 4                           ; ST_CORNER_LEFT / RIGHT: awarded by the game
    je .got
    cmp ax, 5
    je .got
    jmp .fk0
.fkw:cmp ax, 6                          ; MODE 1: a wall free kick (ST_FREE_KICK_LEFT1 .. RIGHT3), a penalty or a foul
    jb .fk1
    cmp ax, 14
    jbe .got
.fk1:inc byte [dword ebp + FK - SPB]
    cmp byte [dword ebp + FK - SPB], 1
    jne .fk2
    call spm_foul                       ; (once: the game's TestFoulForPenaltyAndFreeKick sets the state)
    jmp .done
.fk2:cmp byte [dword ebp + FK - SPB], 30
    jb .done
    jmp .fail
.fk0:
    cmp byte [dword ebp + FK - SPB], 30
    jb .poke
.fail:
    inc word [dword ebp + NFAIL - SPB]
    mov al, 10                          ; (entry 10: not awarded in 30 frames)
    xor esi, esi
    call spm_log
    jmp .end
.poke:
    inc byte [dword ebp + FK - SPB]
    movzx ecx, word [dword ebp + NC - SPB]
    lea esi, [edi + BALL_O]
    mov eax, 150 << 16
    test cl, 2
    jz .xl
    mov eax, 520 << 16
.xl:mov [esi + 1Eh], eax
    mov eax, 120 << 16
    lea ebx, [edi + TOPT_O]
    test cl, 1
    jz .yt
    mov eax, 778 << 16
    lea ebx, [edi + BOTT_O]
.yt:mov [esi + 22h], eax
    xor eax, eax
    mov [esi + 26h], eax                ; z 0
    mov [esi + 2Ch], ax                 ; speed 0
    mov [esi + 2Eh], eax                ; deltaX / deltaY / deltaZ 0
    mov [esi + 32h], eax
    mov [esi + 36h], eax
    mov [edi + LTP_O], ebx              ; lastTeamPlayed = the team defending that goal
    jmp .done
.got:
    mov byte [dword ebp + ST - SPB], 2
    mov eax, [dword ebp + DF_FRAMES - SPB]
    mov [dword ebp + T0 - SPB], eax
    inc word [dword ebp + NC - SPB]
    jmp .done
.window:
    mov eax, [dword ebp + DF_FRAMES - SPB]
    cmp word [edi + GS_O], 100          ; (until the corner is kicked - gameState back to play - T0 follows the frame:
    jne .t0                             ;  the window counts SM_WIN frames of play after the kick)
    cmp byte [dword ebp + FK - SPB], 0FFh
    je .wk
    mov byte [dword ebp + FK - SPB], 0FFh
    push eax
    mov al, 11                          ; (entry 11: the kick - play restarts)
    xor esi, esi
    call spm_log
    pop eax
    jmp .wk
.t0:mov [dword ebp + T0 - SPB], eax
    jmp .done
.wk:sub eax, [dword ebp + T0 - SPB]
    movzx ecx, word [dword ebp + WIN - SPB]
    cmp eax, ecx
    jb .done
    mov al, 6                           ; (entry 6: the window's end)
    xor esi, esi
    call spm_log
.end:
    mov byte [dword ebp + ST - SPB], 0
    mov eax, [dword ebp + DF_FRAMES - SPB]
    mov [dword ebp + LAST - SPB], eax
.done:
    cld
    lea esi, [dword ebp + CURB - SPB]   ; (this frame's ball = the next frame's previous one)
    lea edi, [dword ebp + PREVB - SPB]
    movsd
    movsw
    ret

; ---- MODE 1: a foul on the attacking team's FKORD player, put at FKX[k / 4 % 3], FKD[k % 4 >> ...] px from the goal
;      line: kick k = NC; bit 0 = the goal (0 top: topTeamData fouls), (k >> 1) % 4 = the distance, (k >> 3) % 3 = x.
;      The game's pseudo registers are saved around the call (we run at the frame's end).
spm_foul:
    pushad
    lea esi, [edi + D0_O]
    lea ebx, [dword ebp + RSAVE - SPB]
    mov ecx, 15
.sv:mov eax, [esi]
    mov [ebx], eax
    add esi, 4
    add ebx, 4
    loop .sv
    movzx ecx, word [dword ebp + NC - SPB]
    lea edx, [edi + TOPT_O]             ; the fouling team
    lea eax, [edi + BOTT_O]             ; the attacking team
    test cl, 1
    jz .t
    xchg eax, edx
.t: mov [edi + A6_O], edx
    cmp byte [dword ebp + FKSH - SPB], 0FFh
    je .ns
    push edx                            ; (SP_METER_SH: the attacking team's outfielders' SHOOTING = FKSH - whoever
    push ecx                            ;  takes the kick)
    mov edx, [eax + 0Ah]                ; (inGameTeamPtr + (ordinal - 1) x 61: ordinals 2..11)
    add edx, 61 + SHO
    mov ecx, 10
.sh:mov bl, [edx]
    and bl, 0F8h
    or bl, [dword ebp + FKSH - SPB]
    mov [edx], bl
    add edx, 61
    loop .sh
    pop ecx
    pop edx
.ns:
    mov bx, [eax + 12h]                 ; its TeamGeneralInfo.teamNumber
    push ecx
    lea esi, [edi + SPR0_O]
    mov ecx, 22
.f: cmp [esi], bx
    jne .fn
    mov al, [dword ebp + FKORD - SPB]
    cmp [esi + 2], al
    je .ff
.fn:add esi, 6Eh
    loop .f
    pop ecx
    jmp .r
.ff:pop ecx
    mov eax, ecx
    shr eax, 1
    and eax, 3
    movzx edx, word [dword ebp + FKD - SPB + eax * 2]
    test cl, 1
    jnz .bt
    add edx, 129
    jmp .y
.bt:neg edx
    add edx, 769
.y: shl edx, 16
    mov [esi + 22h], edx
    mov eax, ecx
    shr eax, 3
    xor edx, edx
    push ecx
    mov ecx, 3
    div ecx
    pop ecx
    movzx eax, word [dword ebp + FKX - SPB + edx * 2]
    shl eax, 16
    mov [esi + 1Eh], eax
    mov [edi + A2_O], esi
    call near TESTFOUL
.r: lea esi, [dword ebp + RSAVE - SPB]
    lea ebx, [edi + D0_O]
    mov ecx, 15
.rs:mov eax, [esi]
    mov [ebx], eax
    add esi, 4
    add ebx, 4
    loop .rs
    popad
    ret

; ---- every frame: the watched values; a change is logged while ST != 0 (and always remembered)
spm_watch:
    mov ax, [edi + GS_O]                ; gameState: logged with the previous frame's ball (where it left play)
    cmp ax, [dword ebp + PGS - SPB]
    je .w1
    mov [dword ebp + PGS - SPB], ax
    lea edx, [dword ebp + PREVB - SPB]
    mov al, 2
    xor esi, esi
    call spm_logw
    lea edx, [dword ebp + CURB - SPB]
.w1:mov ax, [edi + GSP_O]
    cmp ax, [dword ebp + PGSP - SPB]
    je .w2
    mov [dword ebp + PGSP - SPB], ax
    mov al, 5
    xor esi, esi
    call spm_logw
.w2:mov esi, [edi + LPP_O]              ; lastPlayerPlayed: a touch
    cmp esi, [dword ebp + PLPP - SPB]
    je .w3
    mov [dword ebp + PLPP - SPB], esi
    test esi, esi
    jz .w3
    mov al, 3
    call spm_logw
.w3:mov esi, [edi + LKP_O]              ; lastKeeperPlayed
    cmp esi, [dword ebp + PLKP - SPB]
    je .w4
    mov [dword ebp + PLKP - SPB], esi
    test esi, esi
    jz .w4
    mov al, 7
    call spm_logw
.w4:mov ax, [edi + G1_O]                ; the goals
    mov cx, [edi + G2_O]
    cmp ax, [dword ebp + PG1 - SPB]
    jne .g
    cmp cx, [dword ebp + PG2 - SPB]
    je .w5
.g: mov [dword ebp + PG1 - SPB], ax
    mov [dword ebp + PG2 - SPB], cx
    mov al, 4
    xor esi, esi
    call spm_logw
.w5:lea esi, [edi + SPR0_O]             ; the 22 player sprites' playerState
    xor ecx, ecx
.s: mov al, [esi + 0Ch]
    cmp al, [dword ebp + PST - SPB + ecx]
    je .sn
    mov [dword ebp + PST - SPB + ecx], al
    cmp al, 4
    je .sl
    cmp al, 6
    je .sl
    cmp al, 7
    je .sl
    cmp al, 8
    je .sl
    cmp al, 9
    je .sl
    cmp al, 11
    jne .sn
.sl:push ecx
    mov al, 8
    call spm_logw
    pop ecx
.sn:add esi, 6Eh
    inc ecx
    cmp ecx, 22
    jb .s
    ret

spm_logw:                               ; spm_log only inside a forcing / window (ST != 0)
    cmp byte [dword ebp + ST - SPB], 0
    jne spm_log
    ret

; ---- one 16-byte entry: al = type, esi = a sprite or 0, edx -> the ball's x / y / z words
;      [frame w][type][gameState][gameStatePl][team][ordinal][playerState][x w][y w][z w][goals 1][goals 2]
spm_log:
    push ecx
    push ebx
    mov ecx, [dword ebp + LN - SPB]
    cmp ecx, LOGMAX
    jb .ok
    inc dword [dword ebp + LDROP - SPB]
    jmp .x
.ok:inc dword [dword ebp + LN - SPB]
    shl ecx, 4
    lea ebx, [dword ebp + LOG - SPB]
    add ebx, ecx
    mov cx, [dword ebp + DF_FRAMES - SPB]
    mov [ebx], cx
    mov [ebx + 2], al
    mov cl, [edi + GS_O]
    mov [ebx + 3], cl
    mov cl, [edi + GSP_O]
    mov [ebx + 4], cl
    xor ecx, ecx
    test esi, esi
    jz .ns
    mov cl, [esi]                       ; Sprite.teamNumber
    mov ch, [esi + 2]                   ; Sprite.playerOrdinal
    mov [ebx + 5], cx
    mov cl, [esi + 0Ch]                 ; Sprite.playerState
    mov [ebx + 7], cl
    jmp .p
.ns:mov cl, [dword ebp + NC - SPB]      ; (no sprite: the corner index in the ordinal byte)
    mov [ebx + 5], ch
    mov [ebx + 6], cl
    mov [ebx + 7], ch
.p: mov cx, [edx]
    mov [ebx + 8], cx
    mov cx, [edx + 2]
    mov [ebx + 10], cx
    mov cx, [edx + 4]
    mov [ebx + 12], cx
    mov cl, [edi + G1_O]
    mov [ebx + 14], cl
    mov cl, [edi + G2_O]
    mov [ebx + 15], cl
.x: pop ebx
    pop ecx
    ret

align 4
SPB: dd O2BASE
TAGM: db 'SPMT'                         ; (+0: the harness finds the block by its tag; OFF in spmeter.py from here)
ST: db 0                                ; +4 0 idle, 1 forcing, 2 window
FK: db 0                                ; +5 forcing frames
NC: dw 0                                ; +6 corners awarded
NF: dw 0                                ; +8 forcings started
NFAIL: dw 0                             ; +10 forcings with no corner in 30 frames
T0: dd 0                                ; +12 the window's first frame
LAST: dd 0                              ; +16 the last window's end
LN: dd 0                                ; +20 log entries
LDROP: dd 0                             ; +24 entries dropped (log full)
GAP: dw SM_GAP                          ; +28 frames of play between two corners
WIN: dw SM_WIN                          ; +30 frames of play logged after the corner kick
MAXC: dw SM_MAXC                        ; +32 corners per match
MODE: db SM_MODE                        ; +34 0 corners, 1 free kicks (spm_foul)
FKORD: db 10                            ; +35 MODE 1: the fouled attacker's ordinal (he is put at the foul point)
FKD: dw 100, 125, 150, 175              ; +36 MODE 1: px from the goal line (the wall zone 87..202)
FKX: dw 336, 290, 382                   ; +44 MODE 1: x (CENTER, LEFT3 / RIGHT1 side bands)
FKSH: db SM_SH                          ; +50 MODE 1: the attackers' SHOOTING (0..7), 0FFh = their own
align 4
RSAVE: times 15 dd 0
PGS: dw 0FFFFh
PGSP: dw 0FFFFh
PG1: dw 0
PG2: dw 0
PLPP: dd 0
PLKP: dd 0
CURB: dw 0, 0, 0
PREVB: dw 0, 0, 0
PST: times 22 db 0FFh
LOG equ $$ + LOG_AT
"""


def _t(p, o):
    try:
        return p.target(1, o)
    except AssertionError:
        return None


def find(p):
    """The obj2 offsets the meter reads, from the exe's own bytes (any language)."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    sym = df.SYMS
    a0 = (2, sym['D0_'][1] + 4 * 8)
    a6 = sym['A6_']
    # CheckIfBallOutOfPlay: mov eax, [lastPlayerPlayed] / mov [A0], eax / mov eax, [lastKeeperPlayed] / or / jz /
    # cmp [A0], offset goalie1Sprite
    m = [x.start() for x in re.finditer(rb'\xa1....\xa3....\xa1....\x0b\xc0\x74.\x81\x3d', d, re.S)]
    m = [o for o in m if _t(p, o + 6) == a0 and _t(p, o + 21) == a0]
    assert len(m) == 1, ('lastPlayerPlayed', m)
    lpp, lkp = _t(p, m[0] + 1), _t(p, m[0] + 11)
    # its head: cmp [gameStatePl], ST_STOPPED / ... / mov [A6], offset ballSprite / mov esi, [A6] / mov ax, [esi + x + 2]
    b = [x.start() for x in re.finditer(rb'\xc7\x05........\x8b\x35....\x66\x8b\x46\x20', d, re.S)]
    b = [o for o in b if _t(p, o + 2) == a6 and _t(p, o + 12) == a6]
    g = [o for o in b if any(d[k:k + 3] == b'\x66\x83\x3d' and d[k + 7] == 0x65 for k in range(o - 0x30, o))]
    assert g, 'CheckIfBallOutOfPlay head'
    o = g[0]
    k = [k for k in range(o - 0x30, o) if d[k:k + 3] == b'\x66\x83\x3d' and d[k + 7] == 0x65]
    gsp = _t(p, k[-1] + 3)
    ball = _t(p, o + 6)
    assert ball == (2, sym['SPR0'][1] + 22 * 0x6E), ('ballSprite', ball, sym['SPR0'])
    # CheckIfBallOutOfPlay's corners: mov [A6], offset topTeamData / cmp word [D2], 129 / jge / mov eax, [lastTeamPlayed]
    # / cmp [A6], eax / jnz / mov [A6], offset bottomTeamData
    lt = [x.start() for x in re.finditer(rb'\xc7\x05........\x66\x81\x3d....\x81\x00\x7d.\xa1....\x39\x05....'
                                         rb'\x0f\x85....\xc7\x05', d, re.S)]
    lt = [o for o in lt if _t(p, o + 2) == a6 and _t(p, o + 28) == a6 and _t(p, o + 40) == a6]
    assert len(lt) == 1, ('lastTeamPlayed', lt)
    topt, ltp, bott = _t(p, lt[0] + 6), _t(p, lt[0] + 22), _t(p, lt[0] + 44)
    assert topt and bott and bott[1] - topt[1] == 0x91, ('top / bottomTeamData', topt, bott)
    # BenchMenuHandleControls: cmp gameState, ST_KEEPER_HOLDS_BALL / jz / mov [subsBlockDirections], 1 / cmp
    gs = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x03\x0f\x84....\x66\xc7\x05....\x01\x00\x66\x83\x3d', d, re.S)]
    assert len(gs) == 1, ('gameState', gs)
    gstate = _t(p, gs[0] + 3)
    # the goals: mov ax, g1 / sub ax, g2 ... mov dx, g1 / add dx, g2
    gg = set()
    for x in re.finditer(rb'\x66\xa1....\x66\x2b\x05....', d, re.S):
        o = x.start()
        g1, g2 = _t(p, o + 2), _t(p, o + 9)
        y = re.compile(rb'\x66\x8b\x15....\x66\x03\x15....', re.S).search(d, o + 13, o + 0x40)
        if g1 and g2 and y and _t(p, y.start() + 3) == g1 and _t(p, y.start() + 10) == g2:
            gg.add((g1, g2))
    assert len(gg) == 1, ('statsTeamGoals', gg)
    g1, g2 = gg.pop()
    tf = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x65\x0f\x84....\xe8....\x8b\x35....\x66\x8b\x46\x20\x66\xa3',
                                         d, re.S)]
    tf = [o for o in tf if _t(p, o + 3) == gsp and _t(p, o + 21) == (2, sym['D0_'][1] + 4 * 10)]
    assert len(tf) == 1, ('TestFoulForPenaltyAndFreeKick', tf)
    for v in (lpp, lkp, gsp, ball, ltp, bott, gstate, g1, g2):
        assert v and v[0] == 2, v
    return dict(LPP_O=lpp[1], LKP_O=lkp[1], GSP_O=gsp[1], BALL_O=ball[1], LTP_O=ltp[1], TOPT_O=topt[1],
                BOTT_O=bott[1], GS_O=gstate[1], G1_O=g1[1], G2_O=g2[1], SPR0_O=sym['SPR0'][1], D0_O=sym['D0_'][1],
                A2_O=sym['D0_'][1] + 4 * 10, A6_O=sym['A6_'][1], TESTFOUL=tf[0])


def _sho(p):
    """SHOOTING's offset in the in-game player record: just before HEADING (PlayerHittingJumpHeader's operand)."""
    import setpieces
    return (setpieces.FOUND.get(id(p)) or setpieces.find(p))[1]['HDO'] - 1


def patch(p, lang):
    if not on():
        return None
    import difficulty as df
    import modver
    assert modver.is_test() and df.trace(), 'SP_METER: test builds only, with DIFF_TRACE (its frame hook)'
    assert df.LABELS.get('df_frame'), 'SP_METER: after difficulty (DIFF_TRACE)'
    assert p.le.obj(4).npages * 0x1000 >= SPM_END, 'spmeter: obj4 pages (patch.py)'
    assert not any(p.get(4, SPM_AT, SPM_END - SPM_AT)), 'spmeter: pages not free'
    c = find(p)
    iv = lambda k, v: int(os.environ.get(k) or str(v), 0)
    sym = {**{k: (0, v) for k, v in c.items() if k != 'TESTFOUL'}, 'TESTFOUL': (1, c['TESTFOUL']), 'O2BASE': (2, 0),
           'SM_MODE': (0, iv('SP_METER_MODE', 0)), 'DF_FRAMES': (4, df.LABELS['DF_FRAMES']),
           'LOG_AT': (0, LOG_AT), 'LOGMAX': (0, LOGMAX), 'SM_GAP': (0, iv('SP_METER_GAP', 120)),
           'SM_WIN': (0, iv('SP_METER_WIN', 420)), 'SM_MAXC': (0, iv('SP_METER_MAXC', 200)),
           'SM_SH': (0, iv('SP_METER_SH', 0xFF)), 'SHO': (0, _sho(p))}
    code, fix, rel = nasmcave.assemble_obj(ASM, SPM_AT, sym, 4)
    lab = nasmcave.labels(ASM, SPM_AT, sym)
    assert lab['spm_frame'] == SPM_AT, 'spm_frame first (difficulty calls SPM_AT)'
    assert len(fix) == 1 and len(rel) == 1, ('spmeter: SPB + the TestFoul call only', fix, rel)
    assert SPM_AT + len(code) <= SPM_AT + LOG_AT, 'spmeter: code + block under the log'
    p.put(4, SPM_AT, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, SPM_AT + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, SPM_AT + o, t_obj, t_off)
    blk = lab['TAGM']
    assert p.get(4, blk, 4) == TAG
    print(f'exe: SP_METER corner meter obj4+{SPM_AT:#x} ({len(code)} B, block +{blk - SPM_AT:#x}, log {LOGMAX} entries)')
    return SPM_AT + len(code)
