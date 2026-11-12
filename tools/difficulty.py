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
LABEL = {'it': "DIFFICOLTA'", 'en': 'DIFFICULTY', 'fr': 'DIFFICULTE', 'de': 'SCHWIERIGKEIT'}
VALUES = {'it': ('NORMALE', 'FACILE', 'DIFFICILE'), 'en': ('NORMAL', 'EASY', 'HARD'),
          'fr': ('NORMAL', 'FACILE', 'DIFFICILE'), 'de': ('NORMAL', 'LEICHT', 'SCHWER')}   # (DF_W 0, 1, 2; 3 / 4 = L2 / L4,
PITCH, HEIGHT, TOP = 9, 8, 18           # test values only: 'L2' / 'L4'); the 14 rows: y 18 + 9 k, 8 high (EXIT TO DOS 151)
LVMAP = (3, 1, 5, 2, 4)                 # DF_W -> level
#              L1      L2      L3      L4      L5
K1 = (80, 90, 100, 105, 110)            # opposition skills %
K2 = (-2, -1, 0, 1, 2)                  # opposition keeper points
K2B = (-1, 0, 0, 1, 2)                  # opposition keeper close-shot index shift
K3 = ((9, 7, 6, 5, 4, 3, 2, 1), (7, 5, 4, 3, 2, 1, 1, 0), (6, 4, 3, 2, 1, 0, 0, 0), (5, 3, 2, 1, 1, 0, 0, 0),
      (4, 3, 2, 1, 0, 0, 0, 0))         # opposition pass errors of 16, by passing 0..7 (L3 = kAIFailedPassChance)
# DRIBBLING (Davide 12/11: a second option, independent of the difficulty; CLASSIC = the original game). One block per
# side: BLK_N (the original values: CLASSIC, two humans, CPU v CPU), BLK_U (NEW, the human), BLK_O (NEW, the CPU team).
#   k     carrier slowdown speed -= speed * k >> 5 (4 = the original shr 3; v1 0a88fa5: 2 for both teams)
#   lockw wonTheBallTimer written on the WINNER of a contact (CalculateIfPlayerWinsBall; Panchina: the opponent of a
#         team with a running timer cannot take the ball back): 16 when the human wins it
#   lockl wonTheBallTimer written on the LOSER of a strong tackle (A0 = the tackler's opponent): 16 when the CPU lost it
#   turn  the ball's run-ahead on a sharp turn (256 = the original; lower = the ball stays closer)
#   box   CPU slide gate: no slide while the carrier is inside the CPU's own penalty area + box px (0 = off; Davide's
#         playtest 12/11: a penalty after every dribble in the box). Every foul in the area is a penalty.
#   hold  second-chaser hold-back radius (sq px), slide the CPU slide radius (sq px)
FIELDS = ('k', 'lockw', 'lockl', 'turn', 'box', 'hold', 'slide')
NORM = dict(k=4, lockw=12, lockl=12, turn=256, box=0, hold=3200, slide=200)
USER = dict(NORM, k=2, lockw=16, turn=224)
OPP = dict(NORM, lockl=16, box=16, hold=4400, slide=160)
DRLABEL = {'it': 'DRIBBLING', 'en': 'DRIBBLING', 'fr': 'DRIBBLE', 'de': 'DRIBBLING'}
DRVALUES = {'it': ('CLASSICO', 'NUOVO'), 'en': ('CLASSIC', 'NEW'), 'fr': ('CLASSIQUE', 'NOUVEAU'),
            'de': ('KLASSISCH', 'NEU')}
assert K1[2] == 100 and K2[2] == 0 and K2B[2] == 0 and K3[2] == (6, 4, 3, 2, 1, 0, 0, 0)

ASM = r"""
; ---- the kick-off: DF_ACT for this match (replaces `mov A6, offset team1AppPercent` at @@init_in_game_teams)
df_kick:
%if DIFF_TRACE
    call df_tkick
%endif
    push eax
    xor eax, eax
    cmp byte [SWOSPP], 0FFh             ; (0FFh = no SWOS++)
    jne .s
    cmp word [TRG], 0                   ; a training game
    jne .s
    mov ax, [DF_W]
    cmp ax, 4
    ja .z
    mov al, [LVMAP + eax]
    cmp al, 3
    jne .s
.z: xor eax, eax
.s: mov [DF_ACT], al
    xor eax, eax                        ; DRIBBLING: the same gates (SWOS++, a training game)
    cmp byte [SWOSPP], 0FFh
    jne .d
    cmp word [TRG], 0
    jne .d
    mov ax, [DF_DR]
    cmp ax, 1
    jbe .d
    xor eax, eax
.d: mov [DF_DACT], al
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

; ---- in ebx = TeamGeneralInfo; out ebx = its side's DRIBBLING block (BLK_N; NEW: BLK_U the human, BLK_O the CPU)
df_blk:
    cmp byte [DF_DACT], 0
    je .n
    push eax
    call df_who
    test al, al
    jz .n0
    mov ebx, BLK_U
    cmp al, 2
    jne .u
    mov ebx, BLK_O
.u: pop eax
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
    movsx ax, byte [K2BT - 1 + ebx]     ; (the index clamped to goalScoredChances' 15 bytes, 0..14)
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
    mov ebx, [ebx + 12]
    cmp [esi + 4Ah], ebx
    pop ebx
    ret

; ---- K5: the CPU slide (replaces `cmp dword [esi + Sprite.ballDistance], 200`, then `ja @@out`; A6 the tackler's
;      team, esi = A1 the tackler). K11: no slide while the carrier is in this team's own penalty area (+ box px):
;      every foul there is a penalty (PlayerTacklingTestFoul's area: x 193..478, y <= 216 top team / >= 682 bottom).
df_slide:
    push ebx
    mov ebx, [A6_]
    call df_blk
    cmp word [ebx + 8], 0
    jne .g
.c: mov ebx, [ebx + 16]
    cmp [esi + 4Ah], ebx
    pop ebx
    ret
.g: push eax
    push ecx
    push edx
    push edi
    mov eax, [ebx + 16]                 ; (outside the radius: no slide anyway, not counted)
    cmp [esi + 4Ah], eax
    ja .gn
    movzx edx, word [ebx + 8]
    mov ecx, [A6_]
    mov edi, [ecx]                      ; (opponentsTeam)
    cmp word [edi + 28h], 0             ; (playerHasBall)
    je .gn
    mov edi, [edi + 20h]                ; (controlledPlayer)
    test edi, edi
    jz .gn
    movsx eax, word [edi + 20h]         ; (Sprite.x + 2)
    mov ecx, 193
    sub ecx, edx
    cmp eax, ecx
    jl .gn
    lea ecx, [478 + edx]
    cmp eax, ecx
    jg .gn
    movsx eax, word [edi + 24h]         ; (Sprite.y + 2)
    mov ecx, [A6_]
    cmp ecx, [ecx]                      ; top team (topTeamData < bottomTeamData = its opponent)?
    ja .bt
    lea ecx, [216 + edx]
    cmp eax, ecx
    jg .gn
    jmp .gy
.bt:mov ecx, 682
    sub ecx, edx
    cmp eax, ecx
    jl .gn
.gy:inc dword [DF_NOSL]
    pop edi
    pop edx
    pop ecx
    pop eax
    pop ebx
    push eax
    mov eax, 1
    cmp eax, 0                          ; (CF = ZF = 0: `ja @@out` taken)
    pop eax
    ret
.gn:pop edi
    pop edx
    pop ecx
    pop eax
    jmp .c

; ---- K9: the won-the-ball protection (replaces `mov word [esi + TeamGeneralInfo.wonTheBallTimer], 12`; esi the team:
;      df_lockw the contact's winner (CalculateIfPlayerWinsBall), df_lockl a strong tackle's loser)
df_lockw:
    push ebx
    mov ebx, esi
    call df_blk
    mov bx, [ebx + 2]
    mov [esi + 8Ah], bx
    pop ebx
    ret
df_lockl:
    push ebx
    mov ebx, esi
    call df_blk
    mov bx, [ebx + 4]
    mov [esi + 8Ah], bx
    pop ebx
    ret

; ---- K10: the sharp turn (replaces `add word [esi + Sprite.speed], 256` on the ball; A6 the carrier's team)
df_turn:
    push ebx
    mov ebx, [A6_]
    call df_blk
    mov bx, [ebx + 6]
    add [esi + 2Ch], bx
    pop ebx
    ret

align 4
TAGW: db 'DIFF'                         ; (+0; the harness finds the block by this tag - offsets below from it)
DF_W: dw DF_START                       ; +4 the option: 0 NORMAL, 1 L1, 2 L5, 3 L2, 4 L4 (a word: the game's string
                                        ;    table reads one; the save item 'DF' = its low byte)
DF_ACT: db 0                            ; +6 this match's level, 0 = off
DF_SH: db DF_START | (DR_START << 4)    ; +7 the session's DF_SV (a new career zeroes the item)
DF_KICKS: dd 0                          ; +8 kick-offs seen
DF_SEED: db 0, 0, 0, 0, 0, 0            ; +12 DIFF_TRACE: both random generators' states at the kick-off (Rand, Rand2)
DF_CTL: db 0, 0                         ; +18 DIFF_TRACE: teamControls forced on team 1 / 2 at the kick-off (0 = as is)
DF_FRAMES: dd 0                         ; +20 DIFF_TRACE: live-match frames since the kick-off
DF_HASH: dd 0                           ; +24 DIFF_TRACE: FNV-1a of every frame's 23 sprites' x / y / z + the RNG states
DF_DR: dw DR_START                      ; +28 the DRIBBLING option: 0 CLASSIC, 1 NEW (a word: the string table)
DF_DACT: db 0                           ; +30 this match's DRIBBLING, 0 = off
DF_SV: db DF_START | (DR_START << 4)    ; +31 the save item 'DF': DIFFICULTY | DRIBBLING << 4
DF_NOSL: dd 0                           ; +32 K11: CPU slides skipped in the own area (counter)
DF_PP: dw 0                             ; +36 DIFF_TRACE: the previous frame's `penalty`
DF_PENS: dw 0                           ; +38 DIFF_TRACE: penalties awarded since the kick-off (rising edges)
DF_CK: times 8 dd 0                     ; +40 DIFF_TRACE: DF_HASH every 2048 frames (ring of 8: 16384 frames)
LVMAP: db 3, 1, 5, 2, 4
align 2
"""

ASM_ROW = r"""
; ---- the OPTIONS rows DIFFICULTY (entries 28 / 29) and DRIBBLING (30 / 31) after slow's 26 / 27; 14 rows at PITCH
df_init:
    call PREV_INIT
    jmp df_add
df_ret:
    call PREV_RET
df_add:
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no rows (both options stay off there: df_kick)
    jne .x
    mov ebx, MENU_
    cmp word [ebx + 10h], 28            ; (slow's 28 entries, nothing after them)
    jne .x
    lea eax, [ebx + 16h + 28 * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries 28 / 29 and 30 / 31 = copies of slow's row (26 / 27)
    lea esi, [ebx + 16h + 26 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    lea esi, [ebx + 16h + 26 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], 28
    mov dword [edi + 26h], S_LBL
    mov word [edi + 38h + 2], 29
    mov dword [edi + 38h + 26h], TAB_D
    mov dword [edi + 38h + 2Ah], df_tog
    mov word [edi + 2 * 38h + 2], 30
    mov dword [edi + 2 * 38h + 26h], S_RLBL
    mov word [edi + 3 * 38h + 2], 31
    mov dword [edi + 3 * 38h + 26h], TAB_R
    mov dword [edi + 3 * 38h + 2Ah], df_rtog
    movzx ecx, byte [ebx + 16h + 27 * 38h + 0Bh]   ; (27's down: EXIT TO DOS - now 31's)
    mov byte [edi + 38h + 0Ah], 27      ; 27 -> 29 -> 31 -> EXIT TO DOS
    mov byte [edi + 38h + 0Bh], 31
    mov byte [edi + 38h + 12h], 27
    mov byte [edi + 38h + 13h], 31
    mov byte [edi + 3 * 38h + 0Ah], 29
    mov [edi + 3 * 38h + 0Bh], cl
    mov byte [edi + 3 * 38h + 12h], 29
    mov [edi + 3 * 38h + 13h], cl
    mov byte [ebx + 16h + 27 * 38h + 0Bh], 29
    mov byte [ebx + 16h + 27 * 38h + 13h], 29
    cmp cl, 0FFh
    je .n
    imul ecx, ecx, 38h                  ; (and the entry below: up 27 -> 31)
    lea ecx, [ebx + 16h + ecx]
    cmp byte [ecx + 0Ah], 27
    jne .u
    mov byte [ecx + 0Ah], 31
.u: cmp byte [ecx + 12h], 27
    jne .n
    mov byte [ecx + 12h], 31
.n: mov word [ebx + 10h], 32
    add dword [ebx + 12h], 4 * 38h
    lea esi, [ebx + 16h]                ; every row at slow's pitch (y TOP + 11 * k, 140 wide; ours at k = 12 / 13
    mov ecx, 32                         ; once copied: 26's y + 11 / + 22) -> y TOP + PITCH * k, HEIGHT high
    add word [ebx + 16h + 28 * 38h + 16h], 11
    add word [ebx + 16h + 29 * 38h + 16h], 11
    add word [ebx + 16h + 30 * 38h + 16h], 22
    add word [ebx + 16h + 31 * 38h + 16h], 22
.c: cmp word [esi + 18h], 140
    jne .cn
    movzx eax, word [esi + 16h]
    sub eax, TOP
    jb .cn
    cmp eax, 13 * 11
    ja .cn
    xor edx, edx
    mov edi, 11
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

df_tog:                                 ; DIFFICULTY (fire): NORMAL -> HARD -> EASY -> NORMAL (L2 / L4: back to NORMAL)
    mov ax, [DF_W]
    cmp ax, 0
    jne .a
    mov ax, 2
    jmp .s
.a: cmp ax, 2
    jne .b
    mov ax, 1
    jmp .s
.b: xor eax, eax
.s: mov [DF_W], ax
    call df_pack
    jmp DRAWITEM
df_rtog:                                ; DRIBBLING (fire): CLASSIC <-> NEW
    mov ax, [DF_DR]
    xor ax, 1
    and ax, 1
    mov [DF_DR], ax
    call df_pack
    jmp DRAWITEM
df_pack:                                ; DF_SV = DF_SH = DIFFICULTY | DRIBBLING << 4
    push eax
    mov al, [DF_DR]
    shl al, 4
    or al, [DF_W]
    mov [DF_SV], al
    mov [DF_SH], al
    pop eax
    ret

df_load:                                ; after a career load: the save's options (0 = NORMAL + CLASSIC without 'DF')
    mov al, [DF_SV]
    jmp df_unp
df_new:                                 ; after a new career's defaults (its items zeroed): the session's options back
    mov al, [DF_SH]
df_unp:
    push eax
    and eax, 0Fh
    cmp al, 4
    jbe .w
    xor eax, eax
.w: mov [DF_W], ax
    pop eax
    shr al, 4
    and eax, 1
    mov [DF_DR], ax
    jmp df_pack
"""

ASM_T = r"""
; ---- DIFF_TRACE (test builds): a deterministic match. The kick-off pins both generators (DF_SEED) and may force the
;      teams' controls (DF_CTL); TimerProc no longer counts currentGameTick (its inc nopped): GameLoop's live-match
;      Flip does, once per frame (every frame = 1 tick, as at 70 fps), and hashes the frame.
df_tkick:
    pushad
    mov al, [DF_CTL]
    test al, al
    jz .c1
    mov esi, [GT1]
    mov [esi + 4], al
.c1:mov al, [DF_CTL + 1]
    test al, al
    jz .c2
    mov esi, [GT2]
    mov [esi + 4], al
.c2:mov esi, DF_SEED
    mov edi, RNG1
    movsw
    movsb
    mov edi, RNG2
    movsw
    movsb
    xor eax, eax
    mov [DF_FRAMES], eax
    mov [DF_PP], eax
    mov dword [DF_HASH], 2166136261
    mov edi, DF_CK
    mov ecx, 8
    rep stosd
    popad
    ret

df_frame:
    call PREV_FLIP
    pushad
    inc word [CGT]
    mov eax, [DF_HASH]
    mov esi, SPR0
    mov ecx, 23
.s: push ecx
    push esi
    add esi, 1Eh                        ; (Sprite.x, .y, .z: 3 dwords)
    mov ecx, 12
    call df_fnv
    pop esi
    pop ecx
    add esi, 6Eh
    loop .s
    mov esi, RNG1
    mov ecx, 3
    call df_fnv
    mov esi, RNG2
    mov ecx, 3
    call df_fnv
    mov [DF_HASH], eax
    mov ax, [PEN]                       ; (a penalty: `penalty` 0 -> non-zero)
    cmp ax, [DF_PP]
    je .np
    mov [DF_PP], ax
    test ax, ax
    jz .np
    inc word [DF_PENS]
.np:mov ebx, [DF_FRAMES]
    inc ebx
    mov [DF_FRAMES], ebx
    test ebx, 7FFh
    jnz .x
    shr ebx, 11
    and ebx, 7
    mov [DF_CK + ebx * 4], eax
.x: popad
    ret

df_fnv:                                 ; eax = FNV-1a(eax; esi, ecx bytes)
    movzx edx, byte [esi]
    xor eax, edx
    imul eax, eax, 16777619
    inc esi
    loop df_fnv
    ret
"""


def trace():
    return bool(os.environ.get('DIFF_TRACE'))


def _blk(t):
    """32 B: k +0, lockw +2, lockl +4, turn +6, box +8, hold +12, slide +16."""
    return struct.pack('<HHHHIII12x', *(t[f] for f in FIELDS))


def data_asm():
    db = lambda bs: 'db ' + ', '.join(str(b) for b in bs) + '\n'
    out = 'K1T: dw ' + ', '.join(map(str, K1)) + '\n'
    out += 'K2T: db ' + ', '.join(str(v & 0xff) for v in K2) + '\n'
    out += 'K2BT: db ' + ', '.join(str(v & 0xff) for v in K2B) + '\n'
    out += 'align 16\nBLK_N: ' + db(_blk(NORM)) + 'BLK_U: ' + db(_blk(USER)) + 'BLK_O: ' + db(_blk(OPP))
    out += 'K3T: ' + ''.join('dw ' + ', '.join(map(str, r)) + '\n' for r in K3)
    return out


def on():
    return bool(os.environ.get('DIFF_TEST') or os.environ.get('DIFF_TRACE'))


def knobs():
    return bool(os.environ.get('DIFF_TEST'))


def start_w():
    lv = int(os.environ.get('DIFF_TEST', '3') or '3')
    assert 1 <= lv <= 5, 'DIFF_TEST=1..5'
    return LVMAP.index(lv)


def start_dr():
    v = int(os.environ.get('DIFF_DRIB', '0') or '0')
    assert v in (0, 1), 'DIFF_DRIB=0 (CLASSIC) / 1 (NEW)'
    return v


def _one(pat, d, name, n=1):
    m = [x.start() for x in re.finditer(pat, d, re.S)]
    assert n is None or len(m) == n, (name, [hex(x) for x in m])
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
    assert modver.is_test(), 'DIFF_TEST / DIFF_TRACE: test builds only (until the OPTIONS row)'
    s, sym = find(p)
    sym['SWOSPP'] = controls.locate(p)['SWOSPP']
    g = gkinj.find(p)
    sym['TRG'] = g['TRG']
    tr = trace()
    row = knobs()
    if row:
        import cpucards
        import slow
        import zones
        from complist import px
        sym0 = controls.locate(p)
        hdr = controls.menu_header(p, sym0['OMBD'][1])
        prev = [p.target(2, hdr + k) for k in (0, 4)]
        assert prev == [(4, slow.LABELS['sl_init']), (4, slow.LABELS['sl_ret'])], ('OPTIONS init / return', prev)
        sym.update(PREV_INIT=prev[0], PREV_RET=prev[1], MENU_=zones._current_menu(p),
                   DRAWITEM=(1, cpucards.find(p)['DRAWITEM']))
        for t in (LABEL[lang], DRLABEL[lang]) + VALUES[lang] + DRVALUES[lang]:
            assert px(t) <= 138 and re.fullmatch(r"[A-Z ']+", t), t
    if tr:
        import slow
        d = p.le.obj_bytes(1)
        sl = slow.find(p)
        sym['CGT'] = sl['CGT']
        sym['PREV_FLIP'] = p.call_target(1, sl['FLIP_AT'])
        sym['RNG1'], sym['RNG2'] = g['RNG1'], g['RNG2']
        tp = _one(rb'\x50\x66\xc7\x05....\xff\xff\x66\xff\x05....\x66\xff\x05....\x66\xa1....\x66\x0b\xc0\x75.'
                  rb'\x66\xff\x05', d, 'TimerProc')[0] + 35
        assert p.target(1, tp + 3) == sl['CGT'], 'TimerProc inc currentGameTick'
        gt = [m.start() for m in re.finditer(rb'\xa1....\xa3....\xa1....\xa3', d[s['KICK'] - 0x600:s['KICK']], re.S)]
        gt = [s['KICK'] - 0x600 + o for o in gt]
        gt = [o for o in gt if p.target(1, o + 1) == sym['A1_'] and p.target(1, o + 11) == sym['A2_']]
        assert len(gt) == 1, ('gameTeam1 / gameTeam2', gt)
        sym['GT1'], sym['GT2'] = p.target(1, gt[0] + 6), p.target(1, gt[0] + 16)
        bs = [m.start() for m in re.finditer(rb'\xc7\x05', d[s['PS'] + 10:s['PS'] + 0x80])]
        bs = [s['PS'] + 10 + o for o in bs if _t(p, s['PS'] + 12 + o) == sym['A1_']]
        assert bs, 'mov A1, offset ballSprite'
        ball = p.target(1, bs[0] + 6)
        sym['SPR0'] = (ball[0], ball[1] - 22 * 0x6E)         # (goalie1Sprite .. team2Player11Sprite, ballSprite)
        pn = _one(rb'\x66\xa1....\x66\x0b\xc0\x74.\x66\xc7\x05....\x01\x00', d, 'GoalScored penalty', None)
        pn = [o for o in pn if _t(p, o + 14) == sym['D1_'] and d[o - 9:o - 6] == b'\x66\xc7\x05'
              and d[o - 2:o] == b'\x02\x00' and _t(p, o - 6) == sym['D1_']]   # (after D1 = GT_OWN_GOAL)
        assert len(pn) == 1, ('penalty', pn)
        sym['PEN'] = p.target(1, pn[0] + 2)
    orig = {k: p.get(1, s[k], n) for k, n in (('SC', 13), ('GK', 11), ('PS', 10), ('GL', 8), ('SL', 7), ('TU', 6),
                                              ('CAR', 37), ('KICK', 10))}
    assert orig['GL'][:3] == b'\x66\x83\x05' and orig['TU'] == b'\x66\x81\x46\x2c\x00\x01', 'sites already patched'
    at = swreg.DIFF_AT
    db = lambda x: ', '.join(str(c) for c in x.encode() + b'\0')
    strs = ''
    if row:
        v = VALUES[lang] + ('L2', 'L4')
        strs = (f'S_LBL: db {db(LABEL[lang])}\n' + ''.join(f'S_V{i}: db {db(t)}\n' for i, t in enumerate(v))
                + 'align 4\nTAB_D: dd DF_W\n    dw 0\n    dd ' + ', '.join(f'S_V{i}' for i in range(5)) + '\n'
                + f'S_RLBL: db {db(DRLABEL[lang])}\n' + ''.join(f'S_R{i}: db {db(t)}\n' for i, t in enumerate(DRVALUES[lang]))
                + 'align 4\nTAB_R: dd DF_DR\n    dw 0\n    dd S_R0, S_R1\n')
    src = (f'%define DIFF_FORCE {int(force)}\n%define DIFF_TRACE {int(tr)}\n%define DF_START {start_w()}\n%define DR_START {start_dr()}\n'
           f'%define TOP {TOP}\n%define PITCH {PITCH}\n%define HEIGHT {HEIGHT}\n' + ASM
           + (ASM_ROW if row else '') + (ASM_T if tr else '') + data_asm() + strs)
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
    hooks = [('KICK', 10, 'df_kick')]
    if knobs():
        hooks += [('SC', 13, 'df_scale'), ('GK', 11, 'df_gk'), ('PS', 10, 'df_pass'), ('GL', 8, 'df_goal'),
                  ('SL', 7, 'df_slide'), ('TU', 6, 'df_turn'), ('CAR', 37, 'df_carrier')]
    for key, n, l in hooks:
        _hook(p, s[key], n, n, lab[l])
    if knobs():
        for o in s['HOLD']:
            _hook(p, o, 7, 7, lab['df_hold'])
        for o, l in zip(s['LOCK'], ('df_lockw', 'df_lockl')):
            _hook(p, o, 9, 9, lab[l])
    if row:
        for k, l in ((0, 'df_init'), (4, 'df_ret')):
            p.retarget(2, hdr + k, 4, lab[l])
            p.put(2, hdr + k, struct.pack('<I', lab[l]))
        import engine
        engine.ITEM_AT['DF'] = (4, lab['DF_SV'])
        engine.CALL_AT['df_load'] = (4, lab['df_load'])
        engine.CALL_AT['df_new'] = (4, lab['df_new'])
    if tr:
        p.branch(1, sl['FLIP_AT'], 0xE8, 4, lab['df_frame'])
        p.remove(1, tp + 3)
        p.put(1, tp, b'\x90' * 7)
    LABELS.clear()
    LABELS.update(lab)
    SITES.clear()
    SITES.update(s)
    print(f'exe: difficulty test (DIFF_TEST={os.environ.get("DIFF_TEST", "")}{", DIFF_FORCE" if force else ""}'
          f'{", DIFF_TRACE" if tr else ""}): code obj4+{at:#x} ({len(code)} B), '
          f'{len(hooks) + (4 if knobs() else 0)} obj1 sites{" + Flip / TimerProc" if tr else ""}')
    return at + len(code)


LABELS = {}
SITES = {}
