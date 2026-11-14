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
SLOW_ROW = False                        # = patch.SLOW (Davide 13/11: MATCH SPEED out of every build; asserted at the build).
NB, BR, SRCP, KMAX = (28, 26, 11, 13) if SLOW_ROW else (26, 15, 12, 12)   # our first entry, the bottom row's (the game's
# CHAIRMAN SCENES 15 / 16, or slow's 26 / 27), the rows' pitch before us, the last row k
if not SLOW_ROW:                        # (without slow: gkinj's 11 rows at 12 px + ours = 13 rows: y 18 + 10 k, 9 high)
    PITCH, HEIGHT = 10, 9
SP_ROW = True                           # (setpieces.py, MC 14/11: the CALCI PIAZZATI row under DRIBBLING whenever the
if SP_ROW:                              #  OPTIONS rows are in - the SETPIECE band linked; 14 rows: 9 px, 8 high)
    assert not SLOW_ROW, 'CALCI PIAZZATI + MATCH SPEED: 15 rows'
    PITCH, HEIGHT, KMAX = 9, 8, 13
NROWS = KMAX + 1
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
FIELDS = ('k', 'lockw', 'lockl', 'turn', 'box', 'hold', 'slide', 'wait')
NORM = dict(k=4, lockw=12, lockl=12, turn=256, box=0, hold=3200, slide=200, wait=0)
USER = dict(NORM, k=2, lockw=16, turn=224)
OPP = dict(NORM, lockl=16, box=16, hold=4400, slide=160)
DRLABEL = {'it': 'DRIBBLING', 'en': 'DRIBBLING', 'fr': 'DRIBBLE', 'de': 'DRIBBLING'}
DRVALUES = {'it': ('CLASSICO', 'NUOVO', 'PERSONALIZZATO'), 'en': ('CLASSIC', 'NEW', 'CUSTOM'),
            'fr': ('CLASSIQUE', 'NOUVEAU', 'PERSONNALISE'), 'de': ('KLASSISCH', 'NEU', 'INDIVIDUELL')}
# 4.2 DRIBBLING PERSONALIZZATO (Davide 13/11, "GO A"; numeric rows 13/11 evening): DRIBBLING's third value opens a
# page of 8 rows. The 6 value rows move the knob's raw value in steps (LEFT / RIGHT clamped, FIRE the next, wrapping)
# from the original (step 0, CLASSICO) one way only (easier for the human); shown as % of the original game:
# ballDistance compares (K5 slide, K8 hold) are squared distances - their % is of the distance; K4 (the carrier's
# slowdown speed * k / 32) as % of the original speed. The two switch rows ON / OFF (the exe's own strings). At the
# kick-off with DRIBBLING 2 the blocks BLK_CU / BLK_CO (copies of BLK_U / BLK_O) take the rows' values; the values live
# in the session only (DP_K; the beta). Default = DRIBBLING NEW's value (asserted below).
def _prog(lo, step, n):
    return tuple(lo + i * step for i in range(n))


#        (label it, en, fr, de)                                                block field size  raw values (step 0 = CLASSICO)
DP_ROWS = (
    (('VELOCITA CON PALLA', 'SPEED WITH BALL', 'VITESSE AVEC BALLE', 'TEMPO AM BALL'), 'U', 0, 2, _prog(4, -1, 5)),        # K4
    (('PALLA INCOLLATA', 'BALL CLOSE ON TURNS', 'BALLE COLLEE', 'BALLNAH BEIM HAKEN'), 'U', 6, 2, _prog(256, -8, 11)),   # K10
    (('PROTEZIONE PALLA', 'BALL SHIELDING', 'PROTECTION BALLE', 'BALLSCHUTZ'), 'U', 2, 2, _prog(12, 1, 13)),            # K9w
    (('MENO SCIVOLATE CPU', 'FEWER CPU SLIDES', 'MOINS TACLES CPU', 'WENIGER GRAETSCHEN'), 'O', 16, 4, _prog(200, -10, 16)),  # K5
    (('MENO RADDOPPI CPU', 'LESS CPU DOUBLING', 'MOINS DE DOUBLEMENTS', 'CPU DOPPELT WENIGER'), 'O', 12, 4,
     _prog(3200, 400, 16)),                                                                                          # K8
    (('CPU LENTA A RIPRENDERE', 'CPU WIN BACK DELAY', 'DELAI REPRISE CPU', 'CPU WARTET LAENGER'), 'O', 4, 2,
     _prog(12, 1, 13)),                                                                                              # K9l
    (('AREA SENZA SCIVOLATE', 'NO SLIDES IN BOX', 'SURFACE SANS TACLE', 'STRAFRAUM SCHUTZ'), 'O', 8, 2, (16, 0)),  # K11
    (('DIFENSORI CPU', 'CPU DEFENDERS', 'DEFENSEURS CPU', 'CPU VERTEIDIGER'), 'O', 20, 2, (0, 1)),               # W1 1-v-1
    (('COSTRUZIONE CPU', 'CPU BUILD UP', 'CONSTRUCTION CPU', 'CPU AUFBAU'), None, 0, 0, (1, 0)),            # MIX
)
# (switch rows' own value strings; the others ON / OFF, the exe's): W1 0 = today's engine, 1 = the 1-v-1 knob
DP_SW = {7: {'it': ('INSEGUONO', 'ASPETTANO'), 'en': ('CHASE', 'WAIT'), 'fr': ('POURSUIVENT', 'ATTENDENT'),
             'de': ('JAGEN', 'WARTEN')}}
DP_MIX = 8                              # (buildup.py bu_opp reads DP_K + 2 * DP_MIX)
DP_NNUM = 6                             # the value rows (then the two switches)
_PCT = {0: lambda v: 100 * (32 - v) / 28, 6: lambda v: 100 * v / 256, 2: lambda v: 100 * v / 12,
        4: lambda v: 100 * v / 12, 16: lambda v: 100 * (v / 200) ** 0.5, 12: lambda v: 100 * (v / 3200) ** 0.5}
DP_PCT = tuple(tuple(int(_PCT[r[2]](v) + 0.5) for v in r[4]) for r in DP_ROWS[:DP_NNUM])   # (the shown %)
DP_TITLE = {'it': 'DRIBBLING PERSONALIZZATO', 'en': 'CUSTOM DRIBBLING', 'fr': 'DRIBBLE PERSONNALISE',
            'de': 'DRIBBLING INDIVIDUELL'}
DP_BACK = {'it': 'INDIETRO', 'en': 'BACK', 'fr': 'RETOUR', 'de': 'ZURUECK'}
DP_RESET = {'it': 'PREDEFINITI', 'en': 'DEFAULTS', 'fr': 'PAR DEFAUT', 'de': 'STANDARD'}   # (every row: DRIBBLING NEW's value)
DP_LEG = {'it': '0: CLASSICO  DESTRA: PIU AIUTO', 'en': '0: CLASSIC  RIGHT: MORE HELP',     # (no '=': not a glyph,
          'fr': '0: CLASSIQUE  DROITE: PLUS D AIDE', 'de': '0: KLASSISCH  RECHTS: MEHR HILFE'}  #  Davide's MiSTer 14/11)
_FOFF = {0: 'k', 2: 'lockw', 4: 'lockl', 6: 'turn', 8: 'box', 12: 'hold', 16: 'slide', 20: 'wait'}
DP_DEFAULT = tuple(r[4].index((USER if r[1] == 'U' else OPP)[_FOFF[r[2]]]) if r[1] else 0 for r in DP_ROWS)  # NUOVO; MIX ON
for _r, _p in zip(DP_ROWS, DP_PCT + ((),) * 2):     # (step 0 = the original; every row fits 4 bits; % shown 3 digits)
    assert not _p or _r[4][0] == NORM[_FOFF[_r[2]]], _r
    assert 2 <= len(_r[4]) <= 16 and all(0 < x < 256 for x in _p) and (not _p or _p[0] == 100), (_r, _p)
assert DP_ROWS[6][4][0] == OPP['box'] and DP_DEFAULT[6:] == (0, 0, 0) and DP_ROWS[DP_MIX][1] is None
assert all(r[1] for r in DP_ROWS[:DP_MIX]), 'the block rows first (dp_build)'
assert K1[2] == 100 and K2[2] == 0 and K2B[2] == 0 and K3[2] == (6, 4, 3, 2, 1, 0, 0, 0)

def _font_guard(*tabs):
    """Every menu text (str, tuple / dict of them) only in characters the game's menu fonts draw (complist.FONT): a
    stray char is a box glyph on screen ('=' in DP_LEG, Davide's MiSTer 14/11) - fail the build, all four languages."""
    import complist
    out = []

    def walk(x):
        if isinstance(x, str):
            out.extend(f'{x!r}: {complist.font_odd(x)}' for _ in [0] if complist.font_odd(x))
        elif isinstance(x, (tuple, list)):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            for y in x.values():
                walk(y)
    for t in tabs:
        walk(t)
    assert not out, 'menu texts outside the font: ' + '; '.join(out)


_font_guard(LABEL, VALUES, DRLABEL, DRVALUES, DP_TITLE, DP_BACK, DP_RESET, DP_LEG, [r[0] for r in DP_ROWS], DP_SW)

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
%if SP
    call sp_set                         ; (setpieces: no SWOS++ seen, training games too - sp_on keeps a training game
%endif                                  ;  original unless it is a practice: PR_WORK's KIND, Shaved 14/11)
    cmp word [TRG], 0
    jne .d
    mov ax, [DF_DR]
    cmp ax, 2                           ; (2 = PERSONALIZZATO: the page's values, dp_build)
    jbe .d
    xor eax, eax
.d: mov [DF_DACT], al
%if ROW
    cmp al, 2
    jne .e
    call dp_build
.e:
%endif
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
%if DIFF_FORCE
    cmp word [ebx + 4], 0               ; the proxy: no human at all -> team 1 (teamNumber 1) is "the human"
    jne .o
    cmp word [ecx + 4], 0
    jne .o
    mov al, 2
    cmp word [ebx + 12h], 1
    jne .x
    mov al, 1
    jmp .x
.o:
%endif
    cmp word [ebx + 4], 0
    jne .meu
    cmp word [ebx + 6], 0               ; me: a computer team?
    jne .x
    cmp word [ecx + 4], 0               ; ... facing a human
    je .x
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
.u: cmp byte [DF_DACT], 2             ; (PERSONALIZZATO: BLK_CU / BLK_CO, 64 B on)
    jne .v
    add ebx, 64
.v: pop eax
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

%macro TCN 1                          ; (DIFF_TC trace builds: count site %1 per block, ebx = the block; flags kept)
%if TC
    pushfd
    push eax
    mov eax, ebx
    sub eax, BLK_N
    shr eax, 5
    inc dword [DF_TC + %1 * 20 + eax * 4]
    pop eax
    popfd
%endif
%endmacro

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
%if TC
    push eax
    mov eax, [ebx + 12]
    cmp [esi + 4Ah], eax
    ja .t
    TCN 1
.t: pop eax
%endif
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
.c:
%if TC
    push eax
    mov eax, [ebx + 16]
    cmp [esi + 4Ah], eax
    ja .t
    TCN 0
    pushfd
    pushad
    cmp word [esi], 2                   ; (a team-2 tackler on team 1's carrier: its angle / zone, DF_TS)
    jne .tx
    mov edi, [A6_]
    mov edi, [edi]
    cmp word [edi + 28h], 0
    je .tx
    mov edi, [edi + 20h]
    test edi, edi
    jz .tx
    mov ebp, DF_TS
    call tc_cls
.tx:popad
    popfd
.t: pop eax
%endif
    mov ebx, [ebx + 16]
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

%if TC
; ---- DIFF_TC: esi = a team-2 player, edi = team 1's carrier, ebp = 9 counters [zone own half / opp half / box]
;      [front / side / behind] (the angle between the carrier's direction and the player, 45 degree cones); team 1's
;      goalie (SPR0) gives the end it defends
tc_cls:
    pushad
    movsx eax, word [edi + 24h]
    movsx ecx, word [edi + 20h]
    movsx edx, word [SPR0 + 24h]
    cmp edx, 449
    jl .dn
    neg eax
    add eax, 898
.dn:xor ebx, ebx
    cmp eax, 449
    jl .zd
    inc ebx
    cmp eax, 682
    jl .zd
    cmp ecx, 193
    jl .zd
    cmp ecx, 478
    jg .zd
    inc ebx
.zd:imul ebx, 12
    add ebp, ebx
    movsx eax, word [esi + 20h]
    movsx ecx, word [edi + 20h]
    sub eax, ecx
    movsx edx, word [esi + 24h]
    movsx ecx, word [edi + 24h]
    sub edx, ecx
    movzx ecx, word [edi + 2Ah]
    and ecx, 7
    movsx ebx, byte [TC_VX + ecx]
    movsx ecx, byte [TC_VY + ecx]
    mov esi, eax
    imul esi, ebx
    mov edi, edx
    imul edi, ecx
    add esi, edi
    imul edx, ebx
    imul eax, ecx
    sub edx, eax
    mov eax, edx
    cdq
    xor eax, edx
    sub eax, edx
    mov ecx, 4
    cmp esi, eax
    jle .b
    xor ecx, ecx
    jmp .k
.b: neg esi
    cmp esi, eax
    jle .k
    mov ecx, 8
.k: inc dword [ebp + ecx]
    popad
    ret
; ---- every live frame: team 1's player nearest the ball (< 10 px: the carrier) and team 2's nearest to it (< 40 px)
tc_frame:
    mov esi, SPR0
    xor edi, edi
    mov edx, 100
    mov ecx, 11
.a: cmp [esi + 4Ah], edx
    jae .an
    mov edx, [esi + 4Ah]
    mov edi, esi
.an:add esi, 6Eh
    loop .a
    test edi, edi
    jz .x
    inc dword [DF_TF]
    xor ebx, ebx
    mov edx, 1600
    mov ecx, 11
.c: cmp [esi + 4Ah], edx
    jae .cn
    mov edx, [esi + 4Ah]
    mov ebx, esi
.cn:add esi, 6Eh
    loop .c
    test ebx, ebx
    jz .x
    mov esi, ebx
    mov ebp, DF_TP
    call tc_cls
.x: ret
TC_VX: db 0, 1, 1, 1, 0, -1, -1, -1
TC_VY: db -1, -1, 0, 1, 1, 1, 0, -1
%endif

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
%if TC
DF_TC: times 10 dd 0                    ; +72 DIFF_TC: [site slide-in-radius, hold-in-radius][block N U O CU CO]
DF_TP: times 9 dd 0                     ; +112 team 2's nearest to team 1's carrier, frames [zone][front side behind]
DF_TS: times 9 dd 0                     ; +148 team 2's slides in radius on team 1's carrier [zone][front side behind]
DF_TF: dd 0                             ; +184 frames with team 1 on the ball
%endif
LVMAP: db 3, 1, 5, 2, 4
align 2
"""

ASM_ROW = r"""
; ---- the OPTIONS rows DIFFICULTY (entries NB / NB+1) and DRIBBLING (NB+2 / NB+3) after the bottom row BR / BR+1 (the game's
;      15 / 16 with NB 26; slow's 26 / 27, NB 28 when patch.SLOW); NROWS rows at PITCH
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
    cmp word [ebx + 10h], NB            ; (gkinj's 26 entries, or slow's 28: nothing after them)
    jne .x
    lea eax, [ebx + 16h + NB * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries NB..NB+3 = copies of the bottom row (BR / BR+1)
    lea esi, [ebx + 16h + BR * 38h]
    mov ecx, 2 * 38h
    rep movsb
    lea esi, [ebx + 16h + BR * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], NB
    mov dword [edi + 26h], S_LBL
    mov word [edi + 38h + 2], NB + 1
    mov dword [edi + 38h + 26h], TAB_D
    mov dword [edi + 38h + 2Ah], df_tog
    mov word [edi + 2 * 38h + 2], NB + 2
    mov dword [edi + 2 * 38h + 26h], S_RLBL
    mov word [edi + 3 * 38h + 2], NB + 3
    mov dword [edi + 3 * 38h + 26h], TAB_R
    mov dword [edi + 3 * 38h + 2Ah], df_rtog
    movzx ecx, byte [ebx + 16h + (BR + 1) * 38h + 0Bh]   ; (BR+1's down: EXIT TO DOS - now NB+3's)
    mov byte [edi + 38h + 0Ah], BR + 1  ; BR+1 -> NB+1 -> NB+3 -> EXIT TO DOS
    mov byte [edi + 38h + 0Bh], NB + 3
    mov byte [edi + 38h + 12h], BR + 1
    mov byte [edi + 38h + 13h], NB + 3
    mov byte [edi + 3 * 38h + 0Ah], NB + 1
    mov [edi + 3 * 38h + 0Bh], cl
    mov byte [edi + 3 * 38h + 12h], NB + 1
    mov [edi + 3 * 38h + 13h], cl
    mov byte [ebx + 16h + (BR + 1) * 38h + 0Bh], NB + 1
    mov byte [ebx + 16h + (BR + 1) * 38h + 13h], NB + 1
    cmp cl, 0FFh
    je .n
    imul ecx, ecx, 38h                  ; (and the entry below: up BR+1 -> NB+3)
    lea ecx, [ebx + 16h + ecx]
    cmp byte [ecx + 0Ah], BR + 1
    jne .u
    mov byte [ecx + 0Ah], NB + 3
.u: cmp byte [ecx + 12h], BR + 1
    jne .n
    mov byte [ecx + 12h], NB + 3
.n: mov word [ebx + 10h], NB + 4
    add dword [ebx + 12h], 4 * 38h
%if SP
    call sp_add                         ; (setpieces: CALCI PIAZZATI, entries NB + 4 / NB + 5)
%endif
    lea esi, [ebx + 16h]                ; every row at the source pitch SRCP (12: gkinj's; 11: slow's; ours one / two
    mov ecx, NB + 4 + 2 * SP            ; rows below the bottom once copied) -> y TOP + PITCH * k, HEIGHT high
    add word [ebx + 16h + NB * 38h + 16h], SRCP
    add word [ebx + 16h + (NB + 1) * 38h + 16h], SRCP
    add word [ebx + 16h + (NB + 2) * 38h + 16h], 2 * SRCP
    add word [ebx + 16h + (NB + 3) * 38h + 16h], 2 * SRCP
.c: cmp word [esi + 18h], 140
    jne .cn
    movzx eax, word [esi + 16h]
    sub eax, TOP
    jb .cn
    cmp eax, KMAX * SRCP
    ja .cn
    xor edx, edx
    mov edi, SRCP
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

%if SP == 0                             ; (with CALCI PIAZZATI: df_tog / df_rtog / df_pack in setpieces.py's band, MC
                                        ;  14/11 - page 15's margin)
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
df_rtog:                                ; DRIBBLING (fire): CLASSIC -> NEW -> CUSTOM (and its page) -> CLASSIC
    mov ax, [DF_DR]
    inc ax
    cmp ax, 2
    jbe .s
    xor eax, eax
.s: mov [DF_DR], ax
    call df_pack
    cmp ax, 2
    je .p
    jmp DRAWITEM
.p: call dp_fall
    mov dword [A6_], DP_MENU            ; the page (OPTIONS comes back unpacked: df_ret, CUSTOM shown)
    jmp SHOW_MENU
%endif


; ---- the kick-off with DRIBBLING 2: BLK_CU / BLK_CO = BLK_U / BLK_O with the page's steps (DP_TAB: 7 rows of
;      block offset (0 CU, 32 CO), field, size 2 / 4, 0, the raw value at step 0 and the step as words: lo + k * step)
dp_build:
    pushad
    mov esi, BLK_U
    mov edi, BLK_CU
    mov ecx, 16
    rep movsd
    xor ebx, ebx
    mov esi, DP_TAB
.r: movzx edi, byte [esi]
    movzx eax, byte [esi + 1]
    add edi, eax
    add edi, BLK_CU
    movzx eax, word [DP_K + ebx * 2]
    movsx edx, word [esi + 6]
    imul eax, edx
    movzx edx, word [esi + 4]
    add eax, edx
    cmp byte [esi + 2], 4
    jne .w
    mov [edi], eax
    jmp .n
.w: mov [edi], ax
.n: add esi, 8
    inc ebx
    cmp ebx, DP_NTAB
    jb .r
    popad
    ret
%if SP == 0
df_pack:                                ; DF_SV = DF_SH = DIFFICULTY | DRIBBLING << 4
    push eax
    mov al, [DF_DR]
    shl al, 4
    or al, [DF_W]
    mov [DF_SV], al
    mov [DF_SH], al
    pop eax
    ret
%endif

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
    and eax, 3                          ; (bits 4-5: 0 CLASSIC, 1 NEW, 2 CUSTOM; 3 -> CLASSIC)
    cmp al, 2
    jbe .d
    xor eax, eax
.d: mov [DF_DR], ax
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
    mov [CGT], ax                       ; (currentGameTick: the AI reads its bits - pinned too)
    mov [CT], ax                        ; (currentTick: CalculateIfPlayerWinsBall reads it - pinned too)
    mov [LGT], ax                       ; (lastGameTick: else the first lastFrameTicks = 0 - the old one, any value)
    mov word [MUTEC], -1                ; (g_muteCommentary: no Rand call timed by the audio)
    mov [DF_FRAMES], eax
    mov [DF_PP], eax
    mov dword [DF_HASH], 2166136261
    mov edi, DF_CK
    mov ecx, 8
    rep stosd
%if STKZ
    lea edi, [esp - STKZ]               ; (DIFF_STKZ=n, MC 13/11 test: the n bytes under the stack zeroed at the
    mov ecx, STKZ / 4                   ;  kick-off - left-over locals the game reads would differ REF / NEW)
    cld
    rep stosd
%endif
    popad
    ret

df_tpre2:                               ; InitGameRestoreTeams' first Rand (playerCardChance...): pinned again here
    call df_pin
    jmp RAND
df_tpre:                                ; InitGameRestoreTeams' first call (before 0x61aa5's / 0x73ed3's Rands): pinned here
    call df_pin
    jmp PRET                            ; (the hooked call's own target)
df_pin:
    pushad                              ; (teamPlayingUp / teamStarting / gameRandValue / playerCardChance come
    mov esi, DF_SEED                    ;  before the kick-off; the menus' Rand calls follow real time)
    mov edi, RNG1
    movsw
    movsb
    mov edi, RNG2
    movsw
    movsb
    mov word [MUTEC], -1                ; (and the commentary already muted: no audio-timed Rand before the kick-off)
    popad
    ret

df_frame:
    call PREV_FLIP
%if BUF
    call BU_ENTRY                       ; (buildup.py's counters)
%endif
    pushad
%if SPM
    call SPM_ENTRY                      ; (spmeter.py: the M3 corner meter, SP_METER test builds)
%endif
%if DELAY                               ; (DIFF_DELAY=n, MC 14/11 CPU-cost control: a pure n-iteration loop per frame,
    mov ecx, DELAY                      ;  no logic - does REF+delay drift from REF like NEW does?)
.dl:loop .dl
%endif
%if TC
    call tc_frame
%endif
    inc word [CGT]
    cmp word [TGATE], 0                 ; (TimerProc's gate for bumpBigSFrame)
    jne .ng
    mov word [BUMPF], -1                ; (bumpBigSFrame once per frame, not every 2nd timer tick: cc hunt 13/11)
.ng:inc word [CT]
    mov byte [DF_LIVE], 250             ; (TimerProc leaves currentTick alone for 250 ticks: df_tick; 8 was too
                                        ;  short for a slow frame under load, 13/11 hunt)
%if TC = 0                              ; (DIFF_TC builds: no frame hash - no room beside the counters)
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
%endif
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
%if STOPF
    cmp ebx, STOPF                      ; (DIFF_STOPF, the 13/11 hunt: halt at that frame, the harness dumps memory)
    jne .ns
    int 3
    jmp $
.ns:
%endif
%if TC = 0
    test ebx, (1 << CKSH) - 1
    jnz .x
    shr ebx, CKSH
    cmp ebx, 8                          ; (no wrap: checkpoints 1..7 = frames 1..7 << CKSH)
    jae .x
    mov [DF_CK + ebx * 4], eax
%endif
.x: popad
    ret

df_tick:                                ; TimerProc's `inc currentTick`, skipped while frames come (DF_LIVE)
    cmp byte [DF_LIVE], 0
    je .i
    dec byte [DF_LIVE]
    ret
.i: inc word [CT]
    ret
DF_LIVE: db 0

%if TC = 0
df_fnv:                                 ; eax = FNV-1a(eax; esi, ecx bytes)
    movzx edx, byte [esi]
    xor eax, edx
    imul eax, eax, 16777619
    inc esi
    loop df_fnv
    ret
%endif
"""



ASM_B = r"""
%macro W1C 1
%if TC
    inc dword [W1_TC + %1 * 4]
%endif
%endmacro
; ==== 42-drp band (MC 14/11: DRIB1V1_AT, MATCH SPEED's parked room on page 13): the PERSONALIZZATO page's code and
;      strings, and W1, the 1-v-1 knob (CPU defenders wait goal-side instead of all chasing). Page 15 keeps DP_K / DP_N /
;      DP_TAB / DP_DEF, dp_build and the packed menu DP_MENU.
; ---- the page's rows (type 14, mask 0E0h) get MenuProc's controls in D7: 40h LEFT = the step before, 80h RIGHT = the
;      next (both clamped), 20h FIRE = the next, wrapping. Step 0 = CLASSICO, RIGHT = more help for the human.
dp_tog:                                 ; (the row: the selected entry's ordinal - DP_V0; Menu.selectedEntry +0Ch)
    mov ebx, [MENU_ + 0Ch]
    movzx ebx, word [ebx + 2]
    sub ebx, DP_V0
    movzx eax, word [DP_K + ebx * 2]
    test byte [D7_], 40h
    jz .r
    dec eax
    jns .s
    inc eax
    jmp .s
.r: inc eax
    cmp al, [DP_N + ebx]
    jb .s
    dec eax
    test byte [D7_], 20h
    jz .s
    xor eax, eax
.s: mov [DP_K + ebx * 2], ax
    call dp_fmt
    jmp DRAWITEM
dp_fall:                                ; every value row's text (the page opens, PREDEFINITI)
    push ebx
    mov ebx, DP_NNUM
.l: dec ebx
    call dp_fmt
    jnz .l
    pop ebx
    ret
dp_fmt:                                 ; ebx = the row: a value row's text DP_S + 6 * row = 'step/last' (0 = CLASSICO);
    pushad                              ; ZF = (ebx = 0)
    cmp ebx, DP_NNUM
    jae .x
    lea edi, [ebx * 2 + ebx]
    lea edi, [edi * 2 + DP_S]
    mov al, [DP_K + ebx * 2]
    call .n
    mov al, '/'
    stosb
    mov al, [DP_N + ebx]
    dec eax
    call .n
    mov byte [edi], 0
.x: popad
    test ebx, ebx
    ret
.n: cmp al, 10
    jb .o
    aam
    xchg al, ah
    add ax, 3030h
    stosw
    ret
.o: add al, '0'
    stosb
    ret
dp_back:
    mov word [EXITM], 1
    ret
dp_reset:                               ; PREDEFINITI: every row back to DRIBBLING NEW's value (DP_DEF), the rows redrawn
    mov esi, DP_DEF                     ;  (DrawMenuItem: A5 = the entry; entries 38h B, the first value row DP_V0)
    mov edi, DP_K
    mov ecx, DP_NR
    rep movsw
    call dp_fall
    mov eax, [MENU_ + 0Ch]
    push eax
    movzx ecx, word [eax + 2]
    imul ecx, ecx, 38h
    sub eax, ecx
    add eax, DP_V0 * 38h
    mov ecx, DP_NR
.l: mov [A5_], eax
    push eax
    push ecx
    call DRAWITEM
    pop ecx
    pop eax
    add eax, 38h
    loop .l
    pop eax
    mov [A5_], eax
    ret

; ---- W1 (the DIFENSORI CPU row, block field +20): ebx = a team; ZF = 0 when the knob acts for it (its DRIBBLING block's
;      wait - only BLK_CO, the CPU facing a human, with the page's row on - and the opponent on the ball)
w1_on:
    push ebx
    push eax
    mov eax, [ebx]                      ; (opponentsTeam)
    call df_blk
    cmp word [ebx + 20], 0
    je .x
    cmp word [eax + 28h], 0             ; (playerHasBall)
.x: pop eax
    pop ebx
    ret
w1_gs:                                  ; esi = a player of team ebx: CF = 1 goal-side (between the ball and his goal)
    push eax
    mov ax, [esi + 24h]
    cmp ebx, [ebx]                      ; (topTeamData < bottomTeamData: the top team defends y small)
    ja .b
    cmp ax, [BALLY]
    pop eax
    ret
.b: cmp [BALLY], ax
    pop eax
    ret
w1_pt:                                  ; ebx = the team: eax = y << 16 | x, the point W1_D px goal-side of the ball,
    push edx                            ;  an eighth of the way to the pitch's centre line x
    movsx eax, word [ebx + 62h]
    mov edx, 336
    sub edx, eax
    sar edx, 3
    add eax, edx
    movsx edx, word [ebx + 64h]
    cmp ebx, [ebx]
    ja .b
    sub edx, W1_D
    jmp .c
.b: add edx, W1_D
.c: shl edx, 16
    mov dx, ax
    mov eax, edx
    pop edx
    ret
w1_dir:                                 ; edx = dx, eax = dy: eax = the 8-way direction (0 up, 2 right; 26.6 degree cuts)
    push ebx
    push ecx
    mov ebx, edx
    test ebx, ebx
    jns .p1
    neg ebx
.p1:mov ecx, eax
    test ecx, ecx
    jns .p2
    neg ecx
.p2:lea ebx, [ebx * 2]
    cmp ebx, ecx
    jae .nv
    test eax, eax                       ; vertical
    mov eax, 0
    js .x
    mov eax, 4
    jmp .x
.nv:shr ebx, 1
    add ecx, ecx
    cmp ecx, ebx
    jae .dg
    test edx, edx                       ; horizontal
    mov eax, 2
    jns .x
    mov eax, 6
    jmp .x
.dg:test edx, edx
    js .l
    test eax, eax
    mov eax, 1
    js .x
    mov eax, 3
    jmp .x
.l: test eax, eax
    mov eax, 7
    js .x
    mov eax, 5
.x: pop ecx
    pop ebx
    ret

; ---- W1 A: the presser's choice (replaces `mov eax, D5` / `cmp D1, eax` in UpdateControlledPlayer and twice in
;      UpdatePlayerBeingPassedTo; A2 the candidate, A6 his team): a player not goal-side counts 4x his squared
;      distance (2x the distance) - a goal-side defender up to twice as far presses first
w1_pick:
    push ebx
    push esi
    mov ebx, [A6_]
    call w1_on
    jz .o
    mov esi, [A2_]
    call w1_gs
    jc .o
    shl dword [D1_], W1_SH
    W1C 0
.o: pop esi
    pop ebx
    mov eax, [D5_]
    cmp [D1_], eax
    ret

; ---- W1 B: the second presser's target (replaces UpdatePlayers' @@player_chase_ball dest = TeamGeneralInfo.ballX / Y;
;      A1 the player, A6 his team): the goal-side point instead of the ball
w1_dest:
    mov esi, [A6_]
    mov ax, [esi + 62h]
    mov esi, [A1_]
    mov [esi + 3Ah], ax
    mov esi, [A6_]
    mov ax, [esi + 64h]
    mov esi, [A1_]
    mov [esi + 3Ch], ax
    push ebx
    mov ebx, [A6_]
    call w1_on
    jz .x
    push eax
    call w1_pt
    mov [esi + 3Ah], eax                ; (destX, destY)
    W1C 1
    pop eax
.x: pop ebx
    ret

; ---- W1 C: the CPU presser's aim (replaces UpdateCpuPlayerControls' @@decide_if_flipping_direction head; A5 the
;      player, A6 his team): not goal-side -> run to the goal-side point; goal-side and W1_IN..W1_OUT from the ball ->
;      wait there (direction -1); closer -> the game's own chase
w1_aim:
    push ebx
    mov ebx, [A6_]
    call w1_on
    jz .o
    push esi
    mov esi, [A5_]
    call w1_gs
    jnc .g
    mov eax, [esi + 4Ah]                ; (ballDistance, squared)
    cmp eax, W1_IN
    jb .op
    cmp eax, W1_OUT
    jae .g
    W1C 2
    mov eax, -1
    jmp .set
.g: W1C 3
    push ecx
    push edx
    call w1_pt
    movsx edx, ax
    movsx ecx, word [esi + 20h]
    sub edx, ecx
    sar eax, 16
    movsx ecx, word [esi + 24h]
    sub eax, ecx
    call w1_dir
    pop edx
    pop ecx
.set:pop esi
    pop ebx
    mov esi, [A6_]
    mov [esi + 2Ch], ax                 ; (currentAllowedDirection)
    or ax, ax
    lea esp, [esp + 4]                  ; (our return dropped: back to the routine's own caller, as its retn)
    ret
.op:pop esi
.o: pop ebx
    mov esi, [A5_]
    mov ax, [esi + 52h]
    mov [D0_], ax
    ret

; ---- W1 D: the standing ball win from behind (replaces `call CalculateIfPlayerWinsBall` in UpdatePlayers; A6 the
;      team going for the ball): a CPU presser in the carrier's back 135 degrees gets 1 contact in 4
w1_win:
    push ebx
    mov ebx, [A6_]
    call w1_on
    jz .g
    pushad
    mov esi, [ebx + 20h]                ; (controlledPlayer: the tackler)
    mov edi, [ebx]
    mov edi, [edi + 20h]                ; (the carrier)
    test esi, esi
    jz .n
    test edi, edi
    jz .n
    movsx edx, word [esi + 20h]
    movsx eax, word [edi + 20h]
    sub edx, eax
    movsx eax, word [esi + 24h]
    movsx ecx, word [edi + 24h]
    sub eax, ecx
    call w1_dir                         ; (the tackler's octant seen from the carrier)
    sub ax, [edi + 2Ah]
    and eax, 7
    sub eax, 3
    cmp eax, 3                          ; (3..5 off his direction: behind -> CF = 1)
    jnc .n
    inc byte [W1_CNT]
    test byte [W1_CNT], 3
    jz .n
    W1C 4
    popad
    pop ebx
    ret                                 ; (no contact this time)
.n: popad
.g: pop ebx
    jmp CIPWB
W1_CNT: db 0
%if TC
align 4
W1_TCT: db 'W1TC'                       ; DIFF_TC: W1's acts - [A biased, B dest, C wait, C aim, D refused]
W1_TC: times 5 dd 0
%endif
"""

def trace():
    return bool(os.environ.get('DIFF_TRACE'))


def _blk(t):
    """32 B: k +0, lockw +2, lockl +4, turn +6, box +8, hold +12, slide +16, wait +20 (W1, the 1-v-1 knob)."""
    return struct.pack('<HHHHIIIH10x', *(t[f] for f in FIELDS))


def data_asm():
    db = lambda bs: 'db ' + ', '.join(str(b) for b in bs) + '\n'
    out = 'K1T: dw ' + ', '.join(map(str, K1)) + '\n'
    out += 'K2T: db ' + ', '.join(str(v & 0xff) for v in K2) + '\n'
    out += 'K2BT: db ' + ', '.join(str(v & 0xff) for v in K2B) + '\n'
    out += 'align 16\nBLK_N: ' + db(_blk(NORM)) + 'BLK_U: ' + db(_blk(USER)) + 'BLK_O: ' + db(_blk(OPP))
    out += 'BLK_CU: ' + db(_blk(USER)) + 'BLK_CO: ' + db(_blk(OPP))   # (PERSONALIZZATO: dp_build, df_blk = U / O + 64)
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
    assert v in (0, 1, 2), 'DIFF_DRIB=0 (CLASSIC) / 1 (NEW) / 2 (CUSTOM)'
    return v


DP_BACK_X, DP_RESET_X, DP_LEG_Y = 172, 22, 176   # (INDIETRO right, PREDEFINITI left, the legend under them)
DP_Y, DP_DY, DP_BACK_Y = 26, 14, 156    # the page: row k at y DP_Y + DP_DY * k (labels x 10, values x 154, 140 x 11)


def dp_asm(lang, page=True):
    """The DRIBBLING PERSONALIZZATO page's data (nasm), as (page 15's, the band's). Page 15: DP_K / DP_N / DP_DEF /
    DP_TAB and the packed menu DP_MENU (entries: 0 title, 1..n labels, n+1..2n values, 2n+1 INDIETRO, 2n+2 PREDEFINITI,
    2n+3 the legend). The band (DRIB1V1_AT): the strings, the value rows' texts DP_S (6 B each: 'k/max'), the switch
    rows' string tables. page=False (DIFF_TRACE test builds: never opened in a traced match): no menu, no strings."""
    li = ('it', 'en', 'fr', 'de').index(lang)
    db = lambda x: ', '.join(str(c) for c in x.encode('latin-1') + b'\0')
    n = len(DP_ROWS)
    tab = [r for r in DP_ROWS if r[1]]
    assert DP_ROWS[:len(tab)] == tuple(tab), 'the block rows first (dp_build: row = knob index)'
    core = 'DP_K: dw ' + ', '.join(map(str, DP_DEFAULT)) + '\n'
    core += 'DP_N: db ' + ', '.join(str(len(r[4])) for r in DP_ROWS) + '\n'
    core += 'DP_DEF: dw ' + ', '.join(map(str, DP_DEFAULT)) + '\n'
    core += f'DP_NTAB equ {len(tab)}\nDP_NNUM equ {DP_NNUM}\nDP_NR equ {n}\nDP_V0 equ {n + 1}\nDP_TAB:\n'
    for r in tab:
        v = r[4]
        st = v[1] - v[0]
        assert v == _prog(v[0], st, len(v)) and 0 <= v[0] < 65536 and -32768 <= st < 32768, r
        core += f'    db {0 if r[1] == "U" else 32}, {r[2]}, {r[3]}, 0\n    dw {v[0]}, {st}\n'
    if not page:
        return 'DP_MENU equ 0\n' + core, 'DP_S equ 0\n'
    strs = f'S_PT: db {db(DP_TITLE[lang])}\nS_BK: db {db(DP_BACK[lang])}\nS_RS: db {db(DP_RESET[lang])}\n'
    strs += f'S_LG: db {db(DP_LEG[lang])}\n'
    strs += ''.join(f'S_L{i}: db {db(r[0][li])}\n' for i, r in enumerate(DP_ROWS))
    band = 'DP_S:\n' + ''.join(f'    db {", ".join(str(c) for c in f"{DP_DEFAULT[i]}/{len(DP_ROWS[i][4]) - 1}".encode().ljust(6, bytes(1)))}\n'
                                 for i in range(DP_NNUM))
    for i in range(DP_NNUM, n):
        if i in DP_SW:
            w = DP_SW[i][lang]
            band += f'S_W{i}a: db {db(w[0])}\nS_W{i}b: db {db(w[1])}\n'
    band += 'align 4\n'
    for i in range(DP_NNUM, n):
        st = f'S_W{i}a, S_W{i}b' if i in DP_SW else 'S_ON, S_OFF'
        band += f'TAB_K{i}: dd DP_K + {2 * i}\n    dw 0\n    dd {st}\n'
    v0, bk, rs = n + 1, 2 * n + 1, 2 * n + 2
    out = core + strs + f'align 4\nDP_MENU:\n    dd 0, 0, 0, {v0}\n'
    out += '    dw 12, 0, 280, 15, 4, 17h, 8, 0\n    dd S_PT\n    dw 0\n'
    for i in range(n):
        out += f'    dw 10, {DP_Y + DP_DY * i}, 140, 11, 4, 9, 8, 0\n    dd S_L{i}\n    dw 0\n'
    for i in range(n):
        up = v0 + i - 1 if i else 255
        dn = v0 + i + 1 if i < n - 1 else bk
        txt = f'8, 0\n    dd DP_S + {6 * i}' if i < DP_NNUM else f'10, 0\n    dd TAB_K{i}'
        out += (f'    dw 154, {DP_Y + DP_DY * i}, 140, 11, 2\n    db 255, 255, {up}, {dn}\n    dw 4, 13, {txt}\n'
                f'    dw 14, 0E0h\n    dd dp_tog\n    dw 0\n')
    out += (f'    dw {DP_BACK_X}, {DP_BACK_Y}, 120, 15, 2\n    db {rs}, 255, {v0 + n - 1}, 255\n    dw 4, 0Eh, 8, 0\n    dd S_BK\n'
            '    dw 13\n    dd dp_back\n    dw 0\n')
    out += (f'    dw {DP_RESET_X}, {DP_BACK_Y}, 120, 15, 2\n    db 255, {bk}, {v0 + n - 1}, 255\n    dw 4, 0Eh, 8, 0\n'
            '    dd S_RS\n    dw 13\n    dd dp_reset\n    dw 0\n')
    out += f'    dw 12, {DP_LEG_Y}, 280, 11, 4, 9, 8, 0\n    dd S_LG\n    dw 0\n    dw -999\n'
    return out, band


PRE_AT = [None, None]


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
    sym = dict(D0_=d0, D1_=var(1), D2_=var(2), D3_=var(3), D7_=var(7), A1_=var(9), A2_=var(10), A3_=var(11), A4_=var(12),
               A6_=var(14), T1APP=t(sc + 2), KFAIL=t(ps + 6))
    assert t(sc + 38) == sym['D2_'] and t(sc + 45) == sym['D3_'] and t(sc + 14) == sym['A4_'], 'ScaleSkill vars'
    assert t(gk + 46) == sym['A6_'] and t(ps + 2) == sym['A1_'] and t(gl + 3) == sym['D1_'], 'vars'
    assert t(car + 6) == d0 and t(car + 29) == sym['A1_'], 'carrier vars'
    ki = [m.start() for m in re.finditer(rb'\xc7\x05', d) if m.start() + 10 <= len(d)]
    ki = [o for o in ki if _t(p, o + 2) == sym['A6_'] and _t(p, o + 6) == sym['T1APP']]
    assert len(ki) == 1, ('@@init_in_game_teams', ki)
    s['KICK'] = ki[0]
    return s, sym


W1_SH = 4                               # W1 A: a player not goal-side counts his squared distance << W1_SH (test: DIFF_W1SH)
W1_D, W1_IN, W1_OUT = 16, 144, 576      # W1: the goal-side point 16 px from the ball; a goal-side presser waits 12..24 px


def w1_find(p, sym):
    """W1's sites (obj1 offsets, any language): A = UpdateControlledPlayer's / UpdatePlayerBeingPassedTo's `mov eax, D5`
    / `cmp D1, eax` (11 B, 3), B = UpdatePlayers' @@player_chase_ball dest = ballX / ballY (40 B), C =
    UpdateCpuPlayerControls' @@decide_if_flipping_direction head (16 B), D = the `call CalculateIfPlayerWinsBall`
    (5 B); BALLY (ballSprite.y + 2), CIPWB."""
    d = p.le.obj_bytes(1)
    t = lambda o: _t(p, o)
    d0 = sym['D0_']
    var = lambda k: (2, d0[1] + 4 * k)
    a = [m.start() for m in re.finditer(rb'\xa1....\x39\x05....\x73.\xa1....\xa3....\xa1....\xa3....', d, re.S)]
    a = [o for o in a if t(o + 1) == var(5) and t(o + 7) == var(1) and t(o + 19) == var(5) and t(o + 24) == var(10)]
    assert len(a) == 3, ('W1 A: closest-player compares', [hex(x) for x in a])
    b = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x62\x8b\x35....\x66\x89\x46\x3a\x8b\x35....'
                                        rb'\x66\x8b\x46\x64\x8b\x35....\x66\x89\x46\x3c', d, re.S)]
    b = [o for o in b if t(o + 2) == var(14) and t(o + 12) == var(9) and t(o + 22) == var(14) and t(o + 32) == var(9)]
    assert len(b) == 1, ('W1 B: @@player_chase_ball', b)
    c = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x52\x66\xa3....\x80\x05....\x80\x66\x83\x05'
                                        rb'....\x10', d, re.S)]
    c = [o for o in c if t(o + 2) == var(13) and t(o + 12) == var(0) and d[o + 48:o + 50] == b'\x8b\x35'
         and d[o + 54:o + 58] == b'\x66\x8b\x46\x2a']
    assert len(c) == 1, ('W1 C: @@decide_if_flipping_direction', c)
    k = [m.start() for m in re.finditer(rb'\xff\x35....\xff\x35....\xff\x35....\xff\x35....\xff\x35....\xe8', d, re.S)]
    k = [o + 30 for o in k if [t(o + 2 + 6 * j) for j in range(5)] == [var(0), var(8), var(9), var(10), var(11)]]
    tg = {o: p.call_target(1, o)[1] for o in k}
    cw = [o for o, x in tg.items() if d[x:x + 2] == b'\x8b\x35' and t(x + 2) == var(14)
          and d[x + 6:x + 9] == b'\x66\xc7\x86']
    assert len(cw) == 1, ('W1 D: call CalculateIfPlayerWinsBall', cw)
    bs = [o for o in range(a[0] - 0x200, a[0]) if d[o:o + 2] == b'\xc7\x05' and t(o + 2) == var(10)]
    ball = t(bs[-1] + 6)                                # (UpdateControlledPlayer: mov A2, offset ballSprite)
    for o in a + b + c + cw:
        assert bytes(p.get(1, o, 5)) == d[o:o + 5], ('W1: site already patched', hex(o))
    return dict(A=a, B=b[0], C=c[0], D=cw[0], CIPWB=(1, tg[cw[0]]), BALLY=(ball[0], ball[1] + 0x24))


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
        import patch as _pt
        assert getattr(_pt, 'SLOW', True) == SLOW_ROW, ('difficulty.SLOW_ROW != patch.SLOW', SLOW_ROW)
        want = [(4, slow.LABELS['sl_init']), (4, slow.LABELS['sl_ret'])] if SLOW_ROW else \
            [(3, gkinj.LABELS['gk_init']), (3, gkinj.LABELS['gk_ret'])]
        assert prev == want, ('OPTIONS init / return', prev, want)
        sym.update(PREV_INIT=prev[0], PREV_RET=prev[1], MENU_=zones._current_menu(p),
                   DRAWITEM=(1, cpucards.find(p)['DRAWITEM']))
        sym['S_OFF'], sym['S_ON'] = cpucards.strings(p, hdr)          # (the exe's own OFF / ON)
        sym['SHOW_MENU'], sym['EXITM'] = sym0['SHOW_MENU'], sym0['EXITM']
        li = ('it', 'en', 'fr', 'de').index(lang)
        for t in ((LABEL[lang], DRLABEL[lang]) + VALUES[lang] + DRVALUES[lang] + (DP_BACK[lang],)
                  + tuple(r[0][li] for r in DP_ROWS)):
            assert px(t) <= 138 and re.fullmatch(r"[A-Z ']+", t), t
        assert px(DP_TITLE[lang]) <= 278, DP_TITLE[lang]
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
        assert d[tp - 25:tp - 22] == b'\x66\xff\x05', 'TimerProc inc currentTick'
        sym['CT'] = p.target(1, tp - 22)
        assert d[tp - 11:tp - 9] == b'\x66\xa1' and d[tp + 7:tp + 10] == b'\x66\x83\x05' and \
            d[tp + 15:tp + 18] == b'\x66\x83\x25' and d[tp + 23] == 0x75 and d[tp + 25:tp + 28] == b'\x66\xc7\x05', \
            'TimerProc: timerBoolean / bumpBigSFrame'   # (cc hunt 13/11: every 2nd tick sets bumpBigSFrame, which
        sym['TGATE'] = p.target(1, tp - 9)              #  steps an animation index (IT 0x65109 -> 0xbdfe6) that a
        sym['BUMPF'] = p.target(1, tp + 28)             #  sprite's picture follows: real time; set per frame instead)
        rt = [o for o in _one(rb'\x66\xa1....\x66\xa3....\x66\xa1....\x66\x29\x05', d, 'ReadTimerDelta', None)
              if _t(p, o + 2) == sl['CGT']]
        rt = [o for o in rt if p.target(1, o + 14) == (sl['CGT'][0], sl['CGT'][1] - 2)]   # (lastGameTick: the word
        assert len(rt) == 1, ('ReadTimerDelta', rt)     #  before currentGameTick; the other copy reads a replay counter)
        sym['LGT'] = p.target(1, rt[0] + 14)
        mc = _one(rb'\x66\x83\x3d....\x00\x0f\x85....\x66\x83\x3d....\x01\x0f\x84....\x66\x83\x3d....\xff\x74.'
                  rb'\x90\x90\x90\x90\x66\x83\x3d....\xff\x74.', d, 'PlayCommentarySample')[0]
        pre = [o for o in _one(rb'\xe8....\x66\x83\x25....\x1e', d, 'InitGameRestoreTeams Rand', None)
               if _t(p, o + 8) == sym['D0_']]
        assert len(pre) == 1, ('InitGameRestoreTeams: Rand / and D0, 1Eh', pre)
        PRE_AT[0] = pre[0]                              # (its first Rand: playerCardChance, then gameRandValue,
        sym['RAND'] = p.call_target(1, pre[0])          #  teamPlayingUp, teamStarting - before the kick-off pin)
        e0 = [m.start() + 17 for m in re.finditer(rb'\xbe....\xbf....\xb9\x30\x00\x00\x00\xf3\xa4\xe8',
                                                 d[pre[0] - 0x200:pre[0]], re.S)]
        assert len(e0) == 1, ('InitGameRestoreTeams: first call', e0)   # (hc 13/11: the Rands of the calls before
        PRE_AT[0] = pre[0] - 0x200 + e0[0]              #  the old pin (0x61aa5, 0x73ed3 in IT) followed the menus' time)
        PRE_AT[1] = pre[0]                              # (and again at that first Rand: the calls between read menu state)
        sym['PRET'] = p.call_target(1, PRE_AT[0])
        sym['MUTEC'] = p.target(1, mc + 45)             # (g_muteCommentary: the commentary picks its sample by Rand
        #  when AIL says the last one stopped - audio time, not frames: muted in trace builds, 13/11 hunt)            # (lastGameTick: pinned with currentGameTick, 13/11 hunt)
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
    dp15, dpb = dp_asm(lang, not tr) if row else ('', '')
    if row:
        v = VALUES[lang] + ('L2', 'L4')
        strs = (f'S_LBL: db {db(LABEL[lang])}\n' + ''.join(f'S_V{i}: db {db(t)}\n' for i, t in enumerate(v))
                + 'align 4\nTAB_D: dd DF_W\n    dw 0\n    dd ' + ', '.join(f'S_V{i}' for i in range(5)) + '\n'
                + f'S_RLBL: db {db(DRLABEL[lang])}\n' + ''.join(f'S_R{i}: db {db(t)}\n' for i, t in enumerate(DRVALUES[lang]))
                + 'align 4\nTAB_R: dd DF_DR\n    dw 0\n    dd S_R0, S_R1, S_R2\n' + dp15)
    skips = set(os.environ.get('DIFF_SKIP', '').split(','))   # (a set: 'BU' in 'BUFRAME' as a string is True)
    bu = knobs() and os.environ.get('DIFF_BU', '1') != '0' and 'BU' not in skips
    sym['BU_ENTRY'] = (4, swreg.BU_AT)
    import spmeter
    sym['SPM_ENTRY'] = (4, spmeter.SPM_AT)
    bf = bu and 'BUFRAME' not in skips
    src = (f'%define BUF {int(bf)}\n%define CKSH {int(os.environ.get("DIFF_CKSH", "11"))}\n%define STKZ {int(os.environ.get("DIFF_STKZ", "0") or 0)}\n%define DELAY {int(os.environ.get("DIFF_DELAY", "0") or 0)}\n%define STOPF {int(os.environ.get("DIFF_STOPF", "0"))}\n%define BU {int(bu)}\n%define DIFF_FORCE {int(force)}\n%define ROW {int(row)}\n%define DIFF_TRACE {int(tr)}\n%define SPM {int(bool(tr and os.environ.get("SP_METER")))}\n%define TC {int(bool(tr and os.environ.get("DIFF_TC")))}\n%define DF_START {start_w()}\n%define DR_START {start_dr()}\n'
           f'%define SP {int(SP_ROW and row)}\n%define TOP {TOP}\n%define PITCH {PITCH}\n%define HEIGHT {HEIGHT}\n%define NB {NB}\n%define BR {BR}\n%define SRCP {SRCP}\n%define KMAX {KMAX}\n' + ASM
           + (ASM_ROW if row else '') + (ASM_T if tr else '') + data_asm() + strs)
    if SP_ROW and row:                                  # (setpieces.py's band: its labels from a first pass)
        import setpieces
        sym.update({k: (4, v) for k, v in setpieces.pass1(p, lang, sym).items() if k in setpieces.FROM_DF})
    band = None
    if row:                                             # (42-drp, MC 14/11: the page's code + strings and W1 in the
        import patch as _pt                             #  band DRIB1V1_AT, MATCH SPEED's parked room - never both)
        assert not getattr(_pt, 'SLOW', True), 'slow and 1-v-1 share 0xC000: MC'
        import buildup
        assert 'DP_K + %d]' % (2 * DP_MIX) in buildup.ASM, 'buildup bu_opp: DP_K + 2 * DP_MIX'
        w1 = w1_find(p, sym)
        sym.update(A5_=(2, sym['D0_'][1] + 4 * 13),
                   D5_=(2, sym['D0_'][1] + 4 * 5), BALLY=w1['BALLY'], CIPWB=w1['CIPWB'])
        bsrc = f'%define TC {int(bool(tr and os.environ.get("DIFF_TC")))}\n%define W1_SH {int(os.environ.get("DIFF_W1SH") or W1_SH)}\n%define W1_D {W1_D}\n%define W1_IN {W1_IN}\n%define W1_OUT {W1_OUT}\n' + ASM_B + dpb
        bat = swreg.DRIB1V1_AT
        bnames = re.findall(r'^([A-Za-z_][A-Za-z0-9_]*):', bsrc, re.M)
        lab0 = nasmcave.labels(src, at, {**sym, **{k: (4, bat) for k in bnames}})     # (pass 1: the band's at a
        symb = {**sym, **{k: (4, v) for k, v in lab0.items() if '.' not in k and k not in sym}}   #  placeholder)
        symb.update(DP_V0=(0, len(DP_ROWS) + 1), DP_NNUM=(0, DP_NNUM), DP_NR=(0, len(DP_ROWS)))
        bcode, bfix, brel = nasmcave.assemble_obj(bsrc, bat, symb, 4)
        labb = nasmcave.labels(bsrc, bat, symb)
        sym = {**sym, **{k: (4, labb[k]) for k in bnames if k in labb}}
        band = (bat, bcode, bfix, brel, labb, w1, lab0)
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    pad = [int(x) for x in os.environ.get('DIFF_PAD', '').split(',') if x]   # (test only, MC 13/11 REF+PAD control:
    if pad and pad[0] > len(code):                      #  a REF build whose obj4 band has NEW's sizes, all nops)
        src += f'\ntimes {pad[0] - len(code)} db 90h\n'
        code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    if band:
        bat, bcode, bfix, brel, labb, w1, lab0 = band
        assert all(lab[k] == v for k, v in lab0.items() if k in lab), 'page 15 moved between the passes'
        assert bat + len(bcode) <= swreg.DRIB1V1_END, ('42-drp band: past its room', hex(bat + len(bcode)))
        assert p.le.obj(4).npages * 0x1000 >= swreg.DRIB1V1_END, '42-drp band: obj4 pages'
        assert not any(p.get(4, bat, swreg.DRIB1V1_END - bat)), '42-drp band (0xC000) not free: slow linked?'
        p.put(4, bat, bcode)
        for o, t_obj, t_off in bfix:
            p.add_ptr(4, bat + o, t_obj, t_off)
        for o, t_obj, t_off in brel:
            p.add_rel(4, bat + o, t_obj, t_off)
        print(f'exe: 42-drp band obj4+{bat:#x}: {len(bcode)} B (room {swreg.DRIB1V1_END - bat - len(bcode)} B)')
        lab = {**labb, **lab}
    assert at + len(code) <= swreg.BU_AT, ('difficulty: past its obj4 room', hex(at + len(code)))
    assert p.le.obj(4).npages * 0x1000 >= swreg.DIFF_END, 'difficulty: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.DIFF_END - at)), 'difficulty: obj4 room (page 15) not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    hooks = [('KICK', 10, 'df_kick')]
    if knobs():
        hooks += [('SC', 13, 'df_scale'), ('GK', 11, 'df_gk'), ('PS', 10, 'df_pass'), ('GL', 8, 'df_goal'),
                  ('SL', 7, 'df_slide'), ('TU', 6, 'df_turn'), ('CAR', 37, 'df_carrier')]
    skip = set(filter(None, os.environ.get('DIFF_SKIP', '').split(',')))   # (test bisection: sites left original)
    for key, n, l in hooks:
        if key not in skip:
            _hook(p, s[key], n, n, lab[l])
    if knobs():
        for o in s['HOLD'] * ('HOLD' not in skip):
            _hook(p, o, 7, 7, lab['df_hold'])
        for o, l in zip(s['LOCK'] * ('LOCK' not in skip), ('df_lockw', 'df_lockl')):
            _hook(p, o, 9, 9, lab[l])
    if band and 'W1' not in skip:                     # W1, the 1-v-1 knob's four sites
        for o in w1['A']:
            _hook(p, o, 11, 11, lab['w1_pick'])
        _hook(p, w1['B'], 40, 40, lab['w1_dest'])
        _hook(p, w1['C'], 16, 16, lab['w1_aim'])
        _hook(p, w1['D'], 5, 5, lab['w1_win'])
    if row and 'ROW' not in skip:
        for k, l in ((0, 'df_init'), (4, 'df_ret')):
            p.retarget(2, hdr + k, 4, lab[l])
            p.put(2, hdr + k, struct.pack('<I', lab[l]))
        import engine
        engine.ITEM_AT['DF'] = (4, lab['DF_SV'])
        engine.CALL_AT['df_load'] = (4, lab['df_load'])
        engine.CALL_AT['df_new'] = (4, lab['df_new'])
    if bu:
        import buildup                                  # DRIBBLING NEW's build-up v1 (provisional room)
        bu_end = buildup.patch(p, lang, sym, lab, swreg.BU_AT, swreg.BU_END)
    else:
        bu_end = swreg.BU_AT
        if len(pad) > 1 and pad[1]:
            p.put(4, swreg.BU_AT, b'\x90' * pad[1])
            bu_end = swreg.BU_AT + pad[1]
    used = (at + len(code) - swreg.DIFF_AT) + (bu_end - swreg.BU_AT)
    margin = swreg.DIFF_END - swreg.DIFF_AT - used
    shape = 'test (TRACE / FORCE)' if tr or force else 'release'
    print(f'exe: difficulty page 15: {used} B used, margin {margin} B ({shape} shape)')
    floor = swreg.DIFF_MARGIN
    mb = os.environ.get('DIFF_MARGIN_BETA')             # (MC 13/11: a BETA-only floor - the PERSONALIZZATO value rows.
    if mb:                                              #  A build switch: buildrel.sh clears it; a beta tag needed; never
        assert os.environ.get('MODVER_TAG'), 'DIFF_MARGIN_BETA: beta builds only (MODVER_TAG), never the release'
        floor = int(mb)                                 #  under 256 B; this exe is never a merge base)
        assert floor >= 256, ('DIFF_MARGIN_BETA under the 256 B floor (MC)', floor)
        print('\n' + '!' * 78 + f'\n!!! BETA ONLY: page 15 margin {margin} B (release floor {swreg.DIFF_MARGIN} B, '
              f'DIFF_MARGIN_BETA {floor} B) - NOT A RELEASE, NOT A MERGE BASE !!!\n' + '!' * 78)
    assert shape != 'release' or margin >= floor, ('difficulty page 15: release margin under '
                                                   f'{floor} B (MC)', margin)
    if tr:
        _hook(p, PRE_AT[0], 5, 5, lab['df_tpre'])
        _hook(p, PRE_AT[1], 5, 5, lab['df_tpre2'])
        p.branch(1, sl['FLIP_AT'], 0xE8, 4, lab['df_frame'])
        p.remove(1, tp + 3)
        p.put(1, tp, b'\x90' * 7)
        for o in (tp + 10, tp + 18, tp + 28):           # (timerBoolean / bumpBigSFrame out of TimerProc: df_frame)
            p.remove(1, o)
        p.put(1, tp + 7, b'\x90' * 27)
        p.remove(1, tp - 22)                            # (and currentTick: one per frame while the match is
        p.branch(1, tp - 25, 0xE8, 4, lab['df_tick'], n=7)   #  live, else TimerProc's own: df_tick)
    LABELS.clear()
    LABELS.update(lab)
    SYMS.clear()
    SYMS.update(sym)
    SITES.clear()
    SITES.update(s)
    print(f'exe: difficulty test (DIFF_TEST={os.environ.get("DIFF_TEST", "")}{", DIFF_FORCE" if force else ""}'
          f'{", DIFF_TRACE" if tr else ""}): code obj4+{at:#x} ({len(code)} B), '
          f'{len(hooks) + (4 if knobs() else 0)} obj1 sites{" + Flip / TimerProc" if tr else ""}')
    return at + len(code)


LABELS = {}
SYMS = {}
SITES = {}
