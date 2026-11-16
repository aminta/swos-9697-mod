"""4.2 set-piece PRACTICE modes (Davide GO 14/11; Difficoltà's design, internal/handoff/42-sp-s3-freekicks.md; MC 14/11).

Step 1, the page: the career squad screen's TRAINING (squadMenu entry 6, its on-select dword an obj2 fixup) opens a
page of our own in obj4 (swreg.PRACTICE_AT..PRACTICE_END, MC's band): TRAINING / FREE KICK PRACTICE / PENALTY PRACTICE /
CORNER PRACTICE / ATTACK-DEFENCE (a switch) / BACK, 4 languages. pr_open shows it (A6 = PR_MENU, ShowMenu - the
fmtpage / DP page pattern; bteam's run-time squadMenu copy copies the retargeted entry); a row sets PR_GO and leaves
the page (g_exitMenu); back in pr_open:
- TRAINING -> entry 6's previous target, read from its fixup at patch time (SelectTraining or a known hook: MC 14/11
  rule 1, asserted), the training game as before; FREE KICK / PENALTY / CORNER -> PR_KIND 1 / 2 / 3 around the same
  call (step 2's engine reads it; 0 outside a practice);
- the switch flips PR_DEF (0 ATTACK: the human takes, 1 DEFENCE: the CPU takes) and shows the page again on its row;
- BACK -> nothing: ShowMenu's caller, the squad screen, with its cursor still on TRAINING.
Work state (PR_GO, PR_KIND, PR_DEF) in swe.c's .bss (PR_WORK: MC 14/11, not in the band).

Step 2, the engine (release code, its own frame hook; the forcing ported from 42-sp spmeter's test-only meter, MC 14/11
rule 1): GameLoop's per-pass `call nullsub_F10` (GameLoop+0x416, after MainKeysCheck: the live match only, between two
whole game steps - no match code in flight; the routine is a bare ret, SWOS++ hooks none of it) goes to pr_frame,
which returns at once unless PR_KIND != 0 inside the training game (g_trainingGame): practice off = the same match.
pr_frame's state machine (PR_WORK +3 ST, +4 TMR frames in the state):
- 0 idle: WAITF frames of live play (gameStatePl = gameState = ST_GAME_IN_PROGRESS) -> pick the side: the human team
  (TeamGeneralInfo.playerNumber != 0, top first) attacks (ATTACK) or the other one (DEFENCE); a stopped game is
  forced at once, except a goal's own sequence (Davide 16/11): goalCameraMode until the stoppage's breakCameraMode
  2 (the ball at rest in the net), then the auto replay (instantReplayFlag / replayState) - the game's own replay;
- 1 forcing: FREE KICK / PENALTY: once, a foul through the game's own TestFoulForPenaltyAndFreeKick (A6 = the
  defending team, A2 = the attacking team's ordinal-10 player put at the foul point; the 15 pseudo registers saved
  around it): free kicks cycle x 336 / 290 / 382 (CENTRE, the two side bands) x 100 / 125 / 150 / 175 px from the goal
  line (the wall zone), penalties 40 px (inside the area); CORNER: the ball past the goal line wide of the posts (x 150
  / 520 alternating, z / speed / deltas 0) with lastTeamPlayed = the defending team, each frame until the game awards
  the corner itself (CheckIfBallOutOfPlay). Awarded = gameState 4 / 5 (corner) or 6..14 (free kick / foul / penalty);
  not in 30 frames: NFAIL + 1, idle again;
- 2 awarded: until the kick (gameState back to play): attempts (NT) + 1;
- 3 live: the attempt ends on a goal (NG + 1), the ball out of play / a stoppage (gameState != play: 4 settles the
  goal count SETTLE frames), the ball cleared CLEAR px from the attacked goal line, or ATTF frames; then the cycle
  index (CY) + 1, idle.
The way out (Davide 14/11, A + B): ESC any time (the game's own, MainKeysCheck: playGame 0), or by itself after PR_N
attempts (playGame 0 at the PR_N-th attempt's end, without ESC's abandonment branch). Then, back in pr_open, a result
page (pr_result: the kind's name, TIRI n, GOL m, OK) when there was an attempt, and the squad screen.
Step 3 (Davide 15/11): no clock (pr_time), no pre-match screen (pr_pmm), no score bar at the restarts (pr_rbar:
UpdateGameTimersAndCameraBreakMode's `mov word [resultTimer], 31000`, its only restart store, gated on PR_KIND)."""
import os
import re
import struct

import nasmcave

LABELS = {}
WORK_SZ = 112                           # (swe.c PR_WORK: WK below, then the text buffers BUF - .bss, not band bytes)
WK = dict(GO=0, KIND=1, DEF=2, ST=3, TMR=4, CY=6, ATK=7, NT=8, NG=10, NFAIL=12, PG=14, NFR=16, HUM=20, LGS=21,
          RST=22, MAXR=24, STS=26, STN=27, BRS=28, SWP=29, END=30, NSEL=30, HALF=31)
# (item 2, Davide 15/11: NSEL / HALF after END - kept across practices and RIPROVA, the session's settings; .bss 0 =
#  the defaults: NSEL 0 = 10 attempts, HALF 0 = CASUALE, the match's own random end - Davide 16/11)
BUF = dict(MTXT=(32, 24), RT=(56, 24), R1=(80, 16), R2=(96, 16))   # (written before each page is shown)
WAITF, ATTF, SETTLE, CLEAR = 20, 560, 25, 240   # frames of play before forcing; an attempt's 8 s (70 Hz); frames after a
                                                # stoppage that still count a goal; px from the goal line = cleared (~40 m)
FKD, FKX, FKORD, PEN_D = (100, 125, 150, 175), (336, 290, 382), 10, 40
PR_N = 10                               # (Davide 14/11, A + B: a practice ends by itself after 10 attempts; ESC any time)
NTAB = (10, 20, 50, 0, 5)               # (item 2, Davide 15/11: the attempts selector - index 0 the default, 0 = INFINITO:
                                        #  only ESC, the game's own way out of a drill, ends it; cycled 10 20 50 INF 5)
SEL = {       # (item 2: the selectors' texts - attempts NTAB order, then the half: top / bottom / alternating)
    'it': (('TIRI: 10', 'TIRI: 20', 'TIRI: 50', 'TIRI: INFINITI', 'TIRI: 5'),
           ("META' CAMPO: CASUALE", "META' CAMPO: ALTA", "META' CAMPO: BASSA", "META' CAMPO: ALTERNATA")),
    'en': (('SHOTS: 10', 'SHOTS: 20', 'SHOTS: 50', 'SHOTS: UNLIMITED', 'SHOTS: 5'),
           ('HALF: RANDOM', 'HALF: TOP', 'HALF: BOTTOM', 'HALF: ALTERNATING')),
    'fr': (('TIRS: 10', 'TIRS: 20', 'TIRS: 50', 'TIRS: ILLIMITES', 'TIRS: 5'),
           ('MOITIE: AU HASARD', 'MOITIE: HAUTE', 'MOITIE: BASSE', 'MOITIE: ALTERNEE')),
    'de': (('SCHUESSE: 10', 'SCHUESSE: 20', 'SCHUESSE: 50', 'SCHUESSE: ENDLOS', 'SCHUESSE: 5'),
           ('HAELFTE: ZUFALL', 'HAELFTE: OBEN', 'HAELFTE: UNTEN', 'HAELFTE: WECHSELND')),
}
RES = {'it': ('TIRI ', 'GOL ', 'OK', 'RIPROVA'), 'en': ('SHOTS ', 'GOALS ', 'OK', 'TRY AGAIN'),
       'fr': ('TIRS ', 'BUTS ', 'OK', 'REJOUER'), 'de': ('SCHUESSE ', 'TORE ', 'OK', 'NOCHMAL')}
RW = 96                                 # (item 6, Davide 15/11: OK and RIPROVA side by side, each RW px wide)  # (the result page: 'TIRI 10', 'GOL 3', OK - the counts drawn up to 3 digits)
ROWS = {      # TRAINING, FREE KICK, PENALTY, CORNER, ATTACK, DEFENCE, BACK (the title = the squad screen's button)
    'it': ('ALLENAMENTO', 'PROVA PUNIZIONI', 'PROVA RIGORI', "PROVA CALCI D'ANGOLO", 'GIOCA IN ATTACCO', 'GIOCA IN DIFESA', 'INDIETRO'),
    'en': ('TRAINING MATCH', 'FREE KICK PRACTICE', 'PENALTY PRACTICE', 'CORNER PRACTICE', 'PLAY IN ATTACK', 'PLAY IN DEFENCE', 'BACK'),
    'fr': ('MATCH D ENTRAINEMENT', 'COUPS FRANCS', 'PENALTYS', 'CORNERS', 'JOUER EN ATTAQUE', 'JOUER EN DEFENSE', 'RETOUR'),
    'de': ('TRAININGSSPIEL', 'FREISTOESSE', 'ELFMETER', 'ECKBAELLE', 'ANGRIFF SPIELEN', 'ABWEHR SPIELEN', 'ZURUECK'),
}
TITLE = {'it': 'PRATICA', 'en': 'TRAINING', 'fr': 'ENTRAINEMENT', 'de': 'TRAINING'}
X, W, H, Y0, DY = 52, 200, 15, 40, 22   # the rows (menu coordinates), title at y 12
R_TRAIN, R_MODE, R_BACK = 1, 5, 6       # entry numbers (0 the title)
R_NS = 7                                # (item 2: the selectors, entries 7 / 8, drawn on rows 5 / 6 above BACK - row 7)
DYP = 19                                # (item 2: the PRACTICE page's row step - 8 rows; the result page keeps DY)

ASM = r"""
pr_open:                                ; squadMenu entry 6 (TRAINING), on select: the practice page
    mov dword [PR_MENU + 12], R_TRAIN_  ; (the default entry: the first row)
.show:
    call pr_seltx                       ; (the selectors' and the switch's texts)
    mov byte [GO], 0
    mov dword [A6], PR_MENU
    call SHOW_MENU
    movzx eax, byte [GO]
    cmp al, 80h                         ; the switch: the page again, on its row
    jne .g2
    mov dword [PR_MENU + 12], R_MODE_
    jmp .show
.g2:call pr_cyc                         ; (item 2: a selector - cycled, the page again on its row)
    jnc .go
    add edx, R_NS_
    mov [PR_MENU + 12], edx
    jmp .show
.go:
    test eax, eax                       ; BACK (or the menu left otherwise): the squad screen
    jz .x
    dec eax
    mov [KIND], al                      ; 0 training, 1 free kicks, 2 penalties, 3 corners
.again:
    push edi                            ; (the engine's state and counters from zero: W_ST .. W_END)
    push ecx
    mov edi, KIND + 2
    mov ecx, W_END_ - 3
    xor al, al
    rep stosb
    pop ecx
    pop edi
    call OLD_SEL                        ; entry 6's previous target (SelectTraining: the game, the squad screen)
    cmp byte [KIND], 0                  ; a practice with attempts: the result page (the kind, TIRI n, GOL m, OK)
    je .x0
    cmp word [KIND - 1 + W_NT_], 0
    je .x0
    mov dword [PR_RES + 12], 3          ; (OK the default)
.res:
    mov byte [GO], 0
    call pr_result
    cmp byte [GO], 81h                  ; (item 6: RIPROVA - the same KIND / DEF, the counters from zero)
    je .again
    mov al, [GO]                        ; (item 2: a selector on the result page - cycled, the page again)
    call pr_cyc
    jnc .x0
    add edx, 5
    mov [PR_RES + 12], edx
    jmp .res
.x0:movzx eax, byte [KIND]              ; (bug 3, Davide 15/11: after a practice the PRACTICE page again, on its row;
    mov byte [KIND], 0                  ;  the training match: the squad screen as before)
    test eax, eax
    jz .x
    add eax, R_TRAIN_
    mov [PR_MENU + 12], eax
    jmp .show
.x: ret

pr_back:
    xor eax, eax
pr_go:                                  ; a row: al = PR_GO; leave the page
    mov [GO], al
    mov byte [EXITM], 1                 ; (g_exitMenu: only 0 / 1 word stores in the game - its high byte 0)
    ret
pr_r1: mov al, 1
    jmp pr_go
pr_r2: mov al, 2
    jmp pr_go
pr_r3: mov al, 3
    jmp pr_go
pr_r4: mov al, 4
    jmp pr_go
pr_mode:
    xor byte [DEF], 1
    mov al, 80h
    jmp pr_go
pr_again:                               ; (item 6: the result page's RIPROVA - the same drill and side again)
    mov al, 81h
    jmp pr_go
pr_ns:                                  ; (item 2: the attempts selector)
    mov al, 82h
    jmp pr_go
pr_hf:                                  ; (item 2: the half selector)
    mov al, 83h
    jmp pr_go

pr_cyc:                                 ; al = GO: 82h attempts / 83h half -> the next value, CF, edx = its
    mov dl, al                          ;  index (0 / 1: entries R_NS / R_NS + 1 here, 5 / 6 on the result page);
    sub dl, 82h                         ;  else NC (al kept)
    cmp dl, 1
    ja .r
    movzx edx, dl
    mov cl, [KIND - 1 + W_NSEL_ + edx]
    inc cl
    cmp cl, [LIM + edx]
    jb .n
    xor cl, cl
.n: mov [KIND - 1 + W_NSEL_ + edx], cl
    stc
.r: ret
LIM: db 5, 4

pr_seltx:                               ; the selectors' texts (both pages) from NSEL / HALF, the switch's from DEF
    movzx ecx, byte [DEF]               ;  (S_ATT, S_DEF back to back; eax ecx edi lost)
    mov edi, S_ATT
    call pr_nth
    mov [MODEP], edi
    movzx ecx, byte [KIND - 1 + W_NSEL_]
    mov edi, S_SN0
    call pr_nth
    mov [SELN1], edi
    mov [SELN2], edi
    movzx ecx, byte [KIND - 1 + W_HALF_]
    mov edi, S_SH0
    call pr_nth
    mov [SELH1], edi
    mov [SELH2], edi
    ret
pr_nth:                                 ; edi = the ecx-th of the 0-terminated strings from edi
    xor eax, eax
    jecxz .r
.l: push ecx
    or ecx, -1
    repne scasb
    pop ecx
    loop .l
.r: ret

pr_result:                              ; after a practice: the result page (the kind's name, TIRI n, GOL m, OK)
    pushad
    movzx eax, byte [KIND]
    mov esi, [KTAB + eax * 4 - 4]
    mov edi, RT
    call pr_cpy
    mov esi, S_SH                       ; (TIRI n, then GOL m: S_GL right after S_SH, NG after NT)
    mov edi, R1
    mov ebp, KIND - 1 + W_NT_
    call pr_one
    mov edi, R2
    call pr_one
    call pr_seltx
    popad
    mov dword [A6], PR_RES
    jmp SHOW_MENU                       ; (OK: pr_back, the page left; then the squad screen)

pr_cpy:                                 ; esi -> edi with its 0; edi past the 0
    lodsb
    stosb
    test al, al
    jnz pr_cpy
    ret

pr_one:                                 ; esi's text at edi (esi past it), then the word at ebp (ebp += 2)
    call pr_cpy
    dec edi
    movzx eax, word [ebp]
    inc ebp
    inc ebp
pr_num:                                 ; eax (< 1000) in decimal at edi, then a 0
    push 10
    pop ecx
    xor ebx, ebx
.d: xor edx, edx
    div ecx
    push edx
    inc ebx
    test eax, eax
    jnz .d
.p: pop eax
    add al, '0'
    stosb
    dec ebx
    jnz .p
    mov byte [edi], 0
    ret

; ---- step 2: the engine. GameLoop's per-pass call (nullsub_F10, a bare ret) comes here
pr_frame:
    cmp byte [KIND], 0
    jne .on
    ret
.on:pushad
    mov ebx, KIND - 1                   ; ebx = PR_WORK, ebp = obj2's base (the game's variables: constants from it)
    mov ebp, O2BASE
    cmp word [ebp + GTR_O], 0           ; (only inside the training game)
    je .x
    cmp word [ebp + PLAYG_O], 0         ; (the match left this pass - ESC: its abandonment goals are not ours)
    je .x
    inc dword [ebx + W_NFR_]
    mov dword [ebp + GT_O], 0           ; (gameTime: the clock held at 0 - no half time in a practice)
    mov al, [ebx + W_ST_]
    dec al                              ; (1 forcing / 2 awarded: the formation at once - pr_tele)
    cmp al, 1
    ja .r1
    call pr_tele
.r1:mov al, [ebx + W_ST_]
    cmp al, 1
    je .force
    cmp al, 2
    je .award
    cmp al, 3
    je .live
    cmp al, 4
    je .settle
    mov ax, [ebp + GS_O]                ; ---- 0 idle. A stopped game (the walk-on ST_STARTING_GAME, a goal's kick-off,
    cmp ax, 100                         ;  a goal kick / throw-in / corner after an attempt): no restart of its own
    je .i0                              ;  (Davide 15/11) - the game live at once and the next set piece forced this
    cmp ax, 23                          ;  pass (stoppageEventTimer 0); half / full time states (23..): the game's
    jae .z                              ;  (22: our own end swap - item 2 - the walk-on as 21)
    cmp word [ebp + IRF_O], 0           ; (a goal - gameState 0 at once, goalCameraMode 1 - Davide 16/11: its own
    jne .z                              ;  sequence first: the ball rests in the net, the stoppage (breakCameraMode
    cmp word [ebp + RPS_O], 0           ;  -1 / 0 / 1), the auto replay (instantReplayFlag, replayState). Forced
    jne .z                              ;  before, the foul's stoppage replayed the goal - the ball out of the net
    cmp word [ebp + GCM_O], 0           ;  at once, a 'save' - and the keeper went missing after it)
    je .i1
    cmp word [ebp + BCM_O], 2
    jl .z
.i1:
    mov word [ebp + SET_O], 0
    mov ax, 100
    mov [ebp + GSP_O], ax
    mov [ebp + GS_O], ax
    jmp .side
.i0:cmp word [ebp + GSP_O], 100         ; live play: WAITF frames of it
    jne .z
    cmp word [ebp + GS_O], 100
    jne .z
    inc word [ebx + W_TMR_]
    cmp word [ebx + W_TMR_], WAITF_
    jb .x
.side:
    xor ecx, ecx                        ; the side: the human team (playerNumber != 0, the top one first)
    cmp word [ebp + TOPT_O + 4], 0
    jne .h
    inc ecx                             ; (ecx 0 the top team human, 1 the bottom one)
.h: mov [ebx + W_HUM_], cl
    xor cl, 1                           ; ATTACK: the human attacks (ATK 1 = the top team attacks the bottom goal)
    cmp byte [ebx + W_DEF_], 0
    je .a
    xor cl, 1                           ; DEFENCE: the other team
.a: mov [ebx + W_ATK_], cl
    cmp byte [ebx + W_SWP_], 0          ; (item 2: the attacked half - ATK 0 the top goal, 1 the bottom one - as
    jne .a1                             ;  chosen: ALTA 0, BASSA 1, ALTERNATA by the attempt (CY's parity); else the
    mov al, [ebx + W_HALF_]             ;  teams change ends - the game's own half-time swap - once an attempt)
    dec al                              ; (Davide 16/11: HALF 0 = CASUALE, the default - the match's own random end,
    js .a1                              ;  no swap; 1 ALTA, 2 BASSA, 3 ALTERNATA)
    cmp al, 2
    jb .a0
    mov al, [ebx + W_CY_]
    and al, 1
.a0:cmp al, cl
    je .a1
    inc byte [ebx + W_SWP_]
    call pr_swap
    jmp .z
.a1:mov byte [ebx + W_ST_], 1
    mov word [ebx + W_TMR_], 0
.force:                                 ; ---- 1 forcing
    inc word [ebx + W_TMR_]
    mov ax, [ebp + GS_O]
    cmp byte [ebx + W_KIND_], 3
    je .corner
    cmp ax, 6                           ; a free kick (6..12), a foul (13), a penalty (14)
    jb .f1
    cmp ax, 14
    jbe .got
.f1:cmp word [ebx + W_TMR_], 1
    jne .f2
    call pr_foul                        ; (once: the game's TestFoulForPenaltyAndFreeKick sets the state)
    jmp .x
.f2:cmp word [ebx + W_TMR_], 30
    jb .x
    jmp .fail
.corner:
    cmp ax, 4                           ; ST_CORNER_LEFT / RIGHT: awarded by the game
    je .got
    cmp ax, 5
    je .got
    cmp word [ebx + W_TMR_], 30
    ja .fail
    call pr_poke                        ; (each frame: a dribbler may drag the ball back for a frame)
    jmp .x
.fail:
    inc word [ebx + W_NFAIL_]
    jmp .z
.got:
    mov byte [ebx + W_SWP_], 0
    mov byte [ebx + W_ST_], 2
    mov [ebx + W_LGS_], al              ; (the state awarded)
    jmp .t0
.award:                                 ; ---- 2 awarded: until the kick
    cmp word [ebp + BCM_O], 7           ; (the hand-over's state 7 waits for the restart team's controlled player -
    jne .aw                             ;  none for 50 frames: the game's own dead stall, its CPU penalty taker never
    call pr_teams                       ;  chosen; the attackers' passTo (the fouled player, at the spot) takes it)
    cmp dword [eax + 20h], 0
    jne .aw
    inc word [ebx + W_TMR_]
    cmp word [ebx + W_TMR_], 50
    jb .aw
    mov ecx, [eax + 24h]
    jecxz .aw
    mov [eax + 20h], ecx
.aw:mov ax, [ebp + GS_O]
    cmp ax, 100
    je .kick
    cmp al, [ebx + W_LGS_]              ; (another stoppage instead - a throw-in from a corner's ball: not an attempt,
    je .x                               ;  idle: forced again at once)
    jmp .z
.kick:
    inc word [ebx + W_NT_]
    mov ax, [ebp + G1_O]
    add ax, [ebp + G2_O]
    mov [ebx + W_PG_], ax
    mov byte [ebx + W_ST_], 3
.t0:mov word [ebx + W_TMR_], 0
    jmp .x
.live:                                  ; ---- 3 the attempt
    inc word [ebx + W_TMR_]
    call pr_goal
    jc .over
    cmp word [ebp + GS_O], 100
    jne .stop
    cmp word [ebx + W_TMR_], ATTF_
    jae .over
    movsx eax, word [ebp + BALL_O + 24h]    ; the ball's y: CLEAR px from the attacked goal line = cleared
    cmp byte [ebx + W_ATK_], 0
    je .up
    neg eax
    add eax, 769
    jmp .cl
.up:sub eax, 129
.cl:cmp eax, CLEAR_
    jg .over
    jmp .x
.stop:
    mov byte [ebx + W_ST_], 4
    jmp .t0
.settle:                                ; ---- 4 a stoppage: a goal still counts for SETTLE frames
    inc word [ebx + W_TMR_]
    call pr_goal
    jc .over
    cmp word [ebx + W_TMR_], SETTLE_
    jb .x
.over:
    inc byte [ebx + W_CY_]
    movzx eax, byte [ebx + W_NSEL_]     ; the chosen attempts (item 2; NTAB, 0 = INFINITO: only ESC): the game over
    mov ax, [NTAB + eax * 2]            ;  (playGame 0, what ESC does, without its abandonment branch): GameLoop's
    test ax, ax                         ;  next pass leaves the match
    jz .z
    cmp [ebx + W_NT_], ax
    jb .z
    mov word [ebp + PLAYG_O], 0
.z: mov byte [ebx + W_ST_], 0
    mov word [ebx + W_TMR_], 0
.x: popad
    ret

pr_tele:                                ; the restart's formation at once: every player armed for it (destReachedState
    lea esi, [ebp + SPR0_O]             ;  1 / 2, the hand-over's state 2 on) put on his destination - movePlayer
    mov ecx, 22                         ;  sees him there (3): no walk to the spot
.l: mov ax, [esi + 64h]
    dec ax
    cmp ax, 1
    ja .n
    mov ax, [esi + 3Ah]                 ; (x / y: integer parts = destX / destY)
    cmp ax, 800                         ; (a destination off the pitch - the hand-over's keeper gets destX = x +
    jae .n                              ;  1000, a sentinel, not a place: left to the game; teleported, the keeper
    mov dx, [esi + 3Ch]                 ;  vanished after a goal's replay until the restart, Davide 16/11)
    cmp dx, 1000
    jae .n
    mov [esi + 20h], ax
    mov [esi + 24h], dx
.n: add esi, 6Eh
    loop .l
    ret

pr_time:                                ; UpdateTime's `mov currentTimeSprite.visible, 1 / call InitDisplaySprites`:
    cmp byte [KIND], 0                  ;  no clock in a practice (Davide 15/11)
    jne .r
    mov word [TVIS], 1
    jmp near INITDS
.r: ret

pr_rbar:                                ; UpdateGameTimersAndCameraBreakMode's restart `mov word [resultTimer], 31000`
    cmp byte [KIND], 0                  ;  (every restart after a stoppage's camera break): no score bar in a practice
    jne .r                              ;  (Davide 15/11, "La togliamo certo"); off: the same store, then its retn
    mov word [RTIM], 31000
.r: ret

pr_stad:                                ; GameLoop's `mov [A6], offset stadiumMenu / call ShowMenu`: no presentation
    cmp byte [KIND], 0                  ;  (stadium, teams, line-ups) before a practice (bug 4, Davide 15/11); the
    jne .r                              ;  training match keeps it. ShowStadiumInit leaves nothing the match reads
    inc byte [KIND - 1 + W_STN_]        ;  (stad.256 in title memory, the little players' colours, mouseInstalled)
    mov dword [A6], STADM               ;  (the harness: STN screens shown, STS skipped)
    jmp near STADSHOW
.r: inc byte [KIND - 1 + W_STS_]
    ret

pr_vs:                                  ; InitializeInGameTeamsAndStartGame's `mov [A6], offset versusMenu / call
    cmp byte [KIND], 0                  ;  ShowMenu`: no versus screen (competition, teams, stadium name) before a
    jne .r                              ;  practice either (Davide on i62 15/11: PRATICA / INTER A c INTER B / the
    mov dword [A6], VSM                 ;  stadium); the training match keeps it. VersusInit leaves nothing the
    jmp near VSSHOW                     ;  match reads (stad.256 in title memory, mouseInstalled: as ShowStadiumInit)
.r: ret

pr_pmm:                                 ; ShowPlayMatchMenu's `mov [A6], offset playMatchMenu / call ShowMenu`: no
    cmp byte [KIND], 0                  ;  pre-match screen in a practice (Davide 15/11) - what the screen leaves:
    jne .p                              ;  its init's bench numbers (SetBenchPlayersNumbers, team 1; game data), then
    mov dword [A6], PMMENU              ;  PLAY by player 1 (PlayMatchSelected: playerNumThatStarted 1)
    jmp near SHOWMENU
.p: mov byte [KMA], 0                ; a kit choice left by a pre-match screen exited without playing is dropped
    mov dword [KSL], 0                  ;  (MC 15/11: kitcolors' km_cancel for another match - KM_ACTIVE, the
    pushad                              ;  SELECT KITS edits, the keepers' choice, the button back to AUTO): the
    db 0Fh, 1Fh, 44h, 0, 0D8h           ;  practice plays the A / B training kits (link_kits: kits.py's kg_cancel)
    mov esi, TXTA
    call near SETBTN
    popad
    mov eax, [PMT1]
    mov [A6 - 24], eax                  ; (A0 = A6 - 24)
    call near SETBENCH
    mov word [PNTS], 1
    ret

pr_goal:                                ; CF = a goal since the kick (NG + 1)
    mov ax, [ebp + G1_O]
    add ax, [ebp + G2_O]
    cmp ax, [ebx + W_PG_]
    je .n
    mov [ebx + W_PG_], ax
    inc word [ebx + W_NG_]
    stc
    ret
.n: clc
    ret

pr_teams:                               ; eax = the attacking team, edx = the defending one (TeamGeneralInfo)
    lea eax, [ebp + TOPT_O]
    lea edx, [ebp + BOTT_O]
    cmp byte [ebx + W_ATK_], 0
    jne .r
    xchg eax, edx
.r: ret

pr_swap:                                ; (item 2) the teams change ends: SetCameraMovingToShowerState, the game's own
    mov edi, SWAPH                      ;  half-time swap (teamPlayingUp, InitTeamsData, the walk-on - state 22,
                                        ;  forced at once as 21)
pr_sv:                                  ; edi = a routine run with the game's 15 pseudo registers D0..A6 saved around
    lea esi, [ebp + D0_O]               ;  it (we run between two game steps); ebx / ebp kept
    mov ecx, 15
.sv:push dword [esi]
    add esi, 4
    loop .sv
    push ebx
    push ebp
    call edi
    pop ebp
    pop ebx
    lea esi, [ebp + D0_O + 14 * 4]
    mov ecx, 15
.rs:pop dword [esi]
    sub esi, 4
    loop .rs
    ret

pr_poke:                                ; CORNER: the ball past the attacked goal line, wide of the posts
    call pr_teams
    lea esi, [ebp + BALL_O]
    mov eax, 150 << 16
    test byte [ebx + W_CY_], 1
    jz .xl
    mov eax, 520 << 16
.xl:mov [esi + 1Eh], eax
    mov eax, 120 << 16
    cmp byte [ebx + W_ATK_], 0
    je .yt
    mov eax, 778 << 16
.yt:mov [esi + 22h], eax
    xor eax, eax
    mov [esi + 26h], eax                ; z 0
    mov [esi + 2Ch], ax                 ; speed 0
    mov [esi + 2Eh], eax                ; deltaX / deltaY / deltaZ 0
    mov [esi + 32h], eax
    mov [esi + 36h], eax
    mov [ebp + LTP_O], edx              ; lastTeamPlayed = the team defending that goal
    ret

pr_foul:                                ; FREE KICK / PENALTY: a foul on the attackers' FKORD player at the point
    mov edi, pr_foul1                   ; (the game's 15 pseudo registers saved around it: pr_sv)
    jmp pr_sv
pr_foul1:
    call pr_teams
    mov [ebp + A6_O], edx               ; A6 = the fouling team
    mov cx, [eax + 12h]                 ; the attackers' TeamGeneralInfo.teamNumber
    lea esi, [ebp + SPR0_O]
    mov edi, 22
.f: cmp [esi], cx                       ; Sprite.teamNumber, .playerOrdinal
    jne .fn
    cmp byte [esi + 2], FKORD_
    je .ff
.fn:add esi, 6Eh
    dec edi
    jnz .f
    jmp .r                              ; (not found: no foul, the forcing gives up after 30 frames)
.ff:mov ecx, PEN_D_                     ; ecx = px from the goal line, edi = x
    mov edi, 336
    cmp byte [ebx + W_KIND_], 2
    je .y
    movzx eax, byte [ebx + W_CY_]       ; free kicks: x FKX[CY % 3], distance FKD[CY / 3 % 4]
    xor edx, edx
    mov ecx, 3
    div ecx
    and eax, 3
    imul ecx, eax, FKD_STEP_
    add ecx, FKD0_
    cmp edx, 1
    jb .y
    mov edi, FKX1_
    je .y
    mov edi, FKX2_
.y: mov eax, 129                        ; the attacked goal line: top 129 (+ d), bottom 769 (- d)
    add eax, ecx
    cmp byte [ebx + W_ATK_], 0
    je .yy
    mov eax, 769
    sub eax, ecx
.yy:shl eax, 16
    mov [esi + 22h], eax
    shl edi, 16
    mov [esi + 1Eh], edi
    mov [ebp + A2_O], esi
    push esi
    push ebx
    push ebp
    call near TESTFOUL
    pop ebp
    pop ebx
    pop esi
    movzx eax, word [ebp + GS_O]        ; (item 5, Davide 15/11: a foul awarded - gameState 6..14 - the ball at once on
    cmp eax, 6                          ;  the ground at the foul point, still: a ball the keeper held or parried no
    jb .r                               ;  longer hangs in the air by the goal while the wall forms)
    cmp eax, 14
    ja .r
    lea edi, [ebp + BALL_O]
    mov eax, [esi + 1Eh]
    mov [edi + 1Eh], eax
    mov eax, [esi + 22h]
    mov [edi + 22h], eax
    xor eax, eax
    mov [edi + 26h], eax                ; z 0
    mov [edi + 2Ch], ax                 ; speed 0
    mov [edi + 2Eh], eax                ; deltaX / deltaY / deltaZ 0
    mov [edi + 32h], eax
    mov [edi + 36h], eax
    inc byte [ebx + W_BRS_]             ; (the harness: balls reset)
.r: ret
"""


def texts(lang):
    return (TITLE[lang],) + ROWS[lang]


def res_texts(lang):
    """The result page's lines as drawn (the widest counts: 999)."""
    return (RES[lang][0] + '999', RES[lang][1] + '999', RES[lang][2], RES[lang][3])


def check_texts():
    """Width + font in all 4 languages (MC 14/11: no stray characters)."""
    from complist import px, font_odd
    bad = []
    for lang in ROWS:
        for t in texts(lang) + res_texts(lang) + SEL[lang][0] + SEL[lang][1]:
            if px(t) > W - 12 or font_odd(t):
                bad.append((lang, t, px(t), font_odd(t)))
    bad += [(lang, t, px(t)) for lang in RES for t in RES[lang][2:] if px(t) > RW - 12]
    assert not bad, ('practice: texts', bad)


def old_target(p, sel_fix):
    """Entry 6's current on-select target (MC rule 1: SelectTraining or a known hook, else the build stops)."""
    t = [(to, oo) for so, s, _, to, oo, *_ in p.le.fixups() if so == 2 and s == sel_fix]
    assert len(t) == 1, ('practice: squadMenu entry 6 on-select fixup', t)
    tobj, toff = t[0]
    assert tobj == 1, ('practice: entry 6 targets obj', tobj)
    d1 = p.le.obj_bytes(1)
    head = d1[toff:toff + 5]
    ptg = toff + 5 + struct.unpack('<i', head[1:5])[0] if head[:1] == b'\xe8' else None
    # SelectTraining: call PlayTrainingGame (mov word [g_trainingGame], 1 at its head)
    ok = ptg is not None and d1[ptg:ptg + 3] == b'\x66\xc7\x05' and d1[ptg + 7:ptg + 9] == b'\x01\x00'
    assert ok, ('practice: entry 6 no longer targets SelectTraining (a new hook: add it to old_target)', hex(toff),
                head.hex())
    return tobj, toff


def _t(p, o):
    try:
        return p.target(1, o)
    except AssertionError:
        return None


def hook_site(p):
    """GameLoop's per-pass `call nullsub_F10` (@@clear_background_check_keys: call ClearBackground / GetKey /
    MainKeysCheck / nullsub_F10, then mov ax, playGame / or / jz @@end_of_game): (its obj1 offset, its target)."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xe8....\xe8....\xe8....\xe8....\x66\xa1....\x66\x0b\xc0\x0f\x84....'
                                        rb'\x66\xa1....\x66\x0b\xc0\x74.\xe8', d, re.S)]
    assert len(m) == 1, ('practice: GameLoop @@clear_background_check_keys', [hex(x) for x in m])
    at = m[0] + 15
    t = p.call_target(1, at)
    assert t[0] == 1 and d[t[1]] == 0xC3, ('practice: GameLoop\'s nullsub call hooked already (a new chain: add it)', t)
    return at, t


def find_game(p, a6, ptg):
    """The obj2 offsets the engine reads (any language): D0 = A6 - 14 x 4 (A6 from bteam's ui_sites), g_trainingGame
    (PlayTrainingGame's head, ptg); the rest as 42-sp spmeter.find (its regexes; SPR0 = ballSprite - 22 x 6Eh)."""
    d = p.le.obj_bytes(1)
    assert a6[0] == 2, a6
    d0 = (2, a6[1] - 14 * 4)
    a0 = (2, d0[1] + 4 * 8)
    gtr = _t(p, ptg + 3)
    # CheckIfBallOutOfPlay: mov eax, [lastPlayerPlayed] / mov [A0], eax / mov eax, [lastKeeperPlayed] / or / jz /
    # cmp [A0], offset goalie1Sprite
    m = [x.start() for x in re.finditer(rb'\xa1....\xa3....\xa1....\x0b\xc0\x74.\x81\x3d', d, re.S)]
    m = [o for o in m if _t(p, o + 6) == a0 and _t(p, o + 21) == a0]
    assert len(m) == 1, ('practice: lastPlayerPlayed (A0 = D0 + 32)', m)
    # its head: cmp [gameStatePl], ST_STOPPED / ... / mov [A6], offset ballSprite / mov esi, [A6] / mov ax, [esi + x + 2]
    b = [x.start() for x in re.finditer(rb'\xc7\x05........\x8b\x35....\x66\x8b\x46\x20', d, re.S)]
    b = [o for o in b if _t(p, o + 2) == a6 and _t(p, o + 12) == a6]
    g = [o for o in b if any(d[k:k + 3] == b'\x66\x83\x3d' and d[k + 7] == 0x65 for k in range(o - 0x30, o))]
    assert g, 'practice: CheckIfBallOutOfPlay head'
    o = g[0]
    k = [k for k in range(o - 0x30, o) if d[k:k + 3] == b'\x66\x83\x3d' and d[k + 7] == 0x65]
    gsp = _t(p, k[-1] + 3)
    ball = _t(p, o + 6)
    # its corners: mov [A6], offset topTeamData / cmp word [D2], 129 / jge / mov eax, [lastTeamPlayed] / cmp [A6], eax
    # / jnz / mov [A6], offset bottomTeamData
    lt = [x.start() for x in re.finditer(rb'\xc7\x05........\x66\x81\x3d....\x81\x00\x7d.\xa1....\x39\x05....'
                                         rb'\x0f\x85....\xc7\x05', d, re.S)]
    lt = [o for o in lt if _t(p, o + 2) == a6 and _t(p, o + 28) == a6 and _t(p, o + 40) == a6]
    assert len(lt) == 1, ('practice: lastTeamPlayed', lt)
    topt, ltp, bott = _t(p, lt[0] + 6), _t(p, lt[0] + 22), _t(p, lt[0] + 44)
    assert topt and bott and bott[1] - topt[1] == 0x91, ('practice: top / bottomTeamData', topt, bott)
    # BenchMenuHandleControls: cmp gameState, ST_KEEPER_HOLDS_BALL / jz / mov [subsBlockDirections], 1 / cmp
    gs = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x03\x0f\x84....\x66\xc7\x05....\x01\x00\x66\x83\x3d',
                                         d, re.S)]
    assert len(gs) == 1, ('practice: gameState', gs)
    gstate = _t(p, gs[0] + 3)
    gg = set()                          # the goals: mov ax, g1 / sub ax, g2 ... mov dx, g1 / add dx, g2
    for x in re.finditer(rb'\x66\xa1....\x66\x2b\x05....', d, re.S):
        o = x.start()
        g1, g2 = _t(p, o + 2), _t(p, o + 9)
        y = re.compile(rb'\x66\x8b\x15....\x66\x03\x15....', re.S).search(d, o + 13, o + 0x40)
        if g1 and g2 and y and _t(p, y.start() + 3) == g1 and _t(p, y.start() + 10) == g2:
            gg.add((g1, g2))
    assert len(gg) == 1, ('practice: statsTeamGoals', gg)
    g1, g2 = gg.pop()
    a2 = (2, d0[1] + 4 * 10)
    tf = [x.start() for x in re.finditer(rb'\x66\x83\x3d....\x65\x0f\x84....\xe8....\x8b\x35....\x66\x8b\x46\x20'
                                         rb'\x66\xa3', d, re.S)]
    tf = [o for o in tf if _t(p, o + 3) == gsp and _t(p, o + 21) == a2]
    assert len(tf) == 1, ('practice: TestFoulForPenaltyAndFreeKick', tf)
    # StartingMatch: call InitTeamsData / mov stoppageEventTimer, 100 / mov gameState, ST_STARTING_GAME / mov
    # breakCameraMode, -1 / mov gameStatePl, ST_STOPPED
    sm = [x.start() for x in re.finditer(rb'\xe8....\x66\xc7\x05....\x64\x00\x66\xc7\x05....\x15\x00\x66\xc7\x05'
                                         rb'....\xff\xff\x66\xc7\x05....\x65\x00', d, re.S)]
    sm = [o for o in sm if _t(p, o + 17) == gstate and _t(p, o + 35) == gsp]
    assert len(sm) == 1, ('practice: StartingMatch', sm)
    sev = _t(p, sm[0] + 8)
    bc = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x0e\x00\x66\xc7\x05....\xff\xff', d, re.S)]
    bc = [o for o in bc if _t(p, o + 3) == gstate]
    assert bc and len({_t(p, o + 12) for o in bc}) == 1, ('practice: breakCameraMode', bc)
    bcm = _t(p, bc[0] + 12)
    # ResetTime: mov gameSeconds, 0 / mov gameTime, 0 (dword) / mov secondsSwitchAccumulator, 0 / mov copyTimeSprite, 1
    # (a mod hook may have replaced the gameTime store with a call + 5 nops: gameTime = gameSeconds + 2, as the original)
    rt = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x00\x00(?:\xc7\x05....\x00\x00\x00\x00|\xe8....\x90{5})'
                                         rb'\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x01\x00', d, re.S)]
    rt = [o for o in rt if _t(p, o + 3) and _t(p, o + 3)[0] == 2]
    assert len(rt) == 1, ('practice: ResetTime', rt)
    gsec = _t(p, rt[0] + 3)
    gt = (2, gsec[1] + 2)
    assert _t(p, rt[0] + 11) in (None, gt), ('practice: gameTime', _t(p, rt[0] + 11), gt)
    # GameLoop: mov ax, [replayState] / or / jz @@main_game_action / call FadeOutToBlack / cmp [loadCrowdChantSampleFlag],
    # 1 / jnz; then its @@check_for_instant_replay: call HandleInstantReplayStateSwitch / mov instantReplayFlag, 0 /
    # mov goalCameraMode, 0 / call Flip (the goal's sequence: pr_frame's idle waits for it - Davide 16/11)
    rs = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x74.\xe8....\x66\x83\x3d....\x01\x75', d, re.S)]
    assert len(rs) == 1, ('practice: GameLoop replayState', rs)
    ir = [x.start() for x in re.finditer(rb'\xe8....\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00\xe8', d, re.S)]
    ir = [o for o in ir if rs[0] < o < rs[0] + 0x200]
    assert len(ir) == 1, ('practice: GameLoop instantReplayFlag / goalCameraMode', ir)
    rps, irf, gcm = _t(p, rs[0] + 2), _t(p, ir[0] + 8), _t(p, ir[0] + 17)
    for v in (gtr, _t(p, m[0] + 1), gsp, ball, ltp, topt, bott, gstate, g1, g2, sev, gt, bcm, rps, irf, gcm):
        assert v and v[0] == 2, ('practice: an obj2 variable', v)
    return dict(GTR_O=gtr[1], GSP_O=gsp[1], GS_O=gstate[1], BALL_O=ball[1], LTP_O=ltp[1], TOPT_O=topt[1],
                BOTT_O=bott[1], G1_O=g1[1], G2_O=g2[1], SPR0_O=ball[1] - 22 * 0x6E, D0_O=d0[1], A2_O=a2[1],
                A6_O=a6[1], SET_O=sev[1], GT_O=gt[1], BCM_O=bcm[1], RPS_O=rps[1], IRF_O=irf[1], GCM_O=gcm[1],
                TESTFOUL=tf[0])


def swap_site(p, g):
    """(item 2) SetCameraMovingToShowerState: mov halfNumber, 2 / neg teamPlayingUp / add teamPlayingUp, 3 / neg
    teamStarting / add teamStarting, 3 ... mov gameState, ST_CAMERA_GOING_TO_SHOWERS (22) - EndFirstExtraTime opens
    the same way, its state another: the one with gameState 22 within 0x60 bytes. Its obj1 offset."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x02\x00\x66\xf7\x1d....\x66\x83\x05....\x03'
                                        rb'\x66\xf7\x1d....\x66\x83\x05....\x03', d, re.S)]
    m = [o for o in m if _t(p, o + 12) == _t(p, o + 19) and _t(p, o + 27) == _t(p, o + 34)]
    gs = [o for o in m if any(d[k:k + 3] == b'\x66\xc7\x05' and _t(p, k + 3) == (2, g['GS_O'])
                              and d[k + 7:k + 9] == b'\x16\x00' for k in range(o, o + 0x60))]
    assert len(m) == 2 and len(gs) == 1, ('practice: SetCameraMovingToShowerState', m, gs)
    return gs[0]


def pm_site(p, a6):
    """ShowPlayMatchMenu's tail: mov [A6], offset playMatchMenu / call ShowMenu (kitcolors: call pm_show) / mov ax,
    [playerNumThatStarted] (benchx: call fr_pmend) / mov [D0], ax / ret - (its obj1 offset, playMatchMenu, the call's
    target, playerNumThatStarted (PlayMatchSelected's `mov [..], 1 / 2`), playMatchTeam1Ptr, SetBenchPlayersNumbers
    as its init calls it)."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xc7\x05........\xe8....(?:\x66\xa1....|\xe8....\x90)\x66\xa3....\xc3',
                                        d, re.S)]
    m = [o for o in m if _t(p, o + 2) == a6 and any(_t(p, k + 1) == (2, a6[1] - 20) for k in range(o - 0x100, o)
                                                    if d[k] == 0xA1 and d[k + 5] == 0xA3)]
    assert len(m) == 1, ('practice: ShowPlayMatchMenu', [hex(x) for x in m])
    o = m[0]
    menu, show = _t(p, o + 6), p.call_target(1, o + 10)
    k = [k for k in range(o - 0x100, o) if d[k] == 0xA1 and d[k + 5] == 0xA3 and _t(p, k + 1) == (2, a6[1] - 20)]
    t1 = _t(p, k[-1] + 6)
    ps = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x01\x00\x66\xc7\x05....\x00\x00\x66\xc7\x05....\x00\x00'
                                         rb'\xe9', d, re.S)]
    ps = [q for q in ps if _t(p, q + 3) and re.match(rb'\x66\xc7\x05....\x02\x00', d[q + 32:q + 41], re.S)
          and _t(p, q + 35) == _t(p, q + 3)]
    assert len(ps) == 1, ('practice: PlayMatchSelected', [hex(x) for x in ps])
    pnts = _t(p, ps[0] + 3)
    init = p.target(2, menu[1])
    assert init[0] == 1, ('practice: PlayMatchMenuInit hooked (a new chain: add it)', init)
    sb = [init[1] + x.start() for x in re.finditer(rb'\xa1....\xa3....\xe8....\x66\xc7\x05....\x00\x00',
                                                   d[init[1]:init[1] + 0x400], re.S)]
    sb = [q for q in sb if _t(p, q + 1) == t1 and _t(p, q + 6) == (2, a6[1] - 24)]
    assert len(sb) == 1, ('practice: SetBenchPlayersNumbers', sb)
    for v in (menu, pnts, t1):
        assert v and v[0] == 2, ('practice: a ShowPlayMatchMenu variable', v)
    return o, menu[1], show, pnts[1], t1[1], p.call_target(1, sb[0] + 10)


def stad_site(p, a6, playg):
    """GameLoop's `mov [A6], offset stadiumMenu / call ShowMenu` (after `mov playGame, 1`; ShowHighlights has the same
    pair): (its obj1 offset, stadiumMenu's obj2 offset, the call's target)."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xc7\x05........\xe8', d, re.S)]
    m = [o for o in m if _t(p, o + 2) == a6 and _t(p, o + 6) and _t(p, o + 6)[0] == 2
         and any(d[k:k + 3] == b'\x66\xc7\x05' and d[k + 7:k + 9] == b'\x01\x00' and _t(p, k + 3) == (2, playg)
                 for k in range(o - 0xA0, o))]
    assert len(m) == 1, ('practice: GameLoop stadiumMenu', [hex(x) for x in m])
    st = _t(p, m[0] + 6)
    ini = p.target(2, st[1])
    assert ini[0] == 1 and d[ini[1]:ini[1] + 2] == b'\x66\xc7', ('practice: stadiumMenu -> ShowStadiumInit', ini)
    return m[0], st[1], p.call_target(1, m[0] + 10)


def vs_site(p, a6):
    """InitializeInGameTeamsAndStartGame's `mov [A6], offset versusMenu / call ShowMenu` (inside 15 pushes / pops):
    versusMenu = the menu whose init is VersusInit (stadium.sites' vs in it) -> (obj1 offset, versusMenu, the call's
    target)."""
    d = p.le.obj_bytes(1)
    # (VersusInit's end as stadium.sites finds it - not its call: stadium.py has hooked that place by now)
    vs = [x.start() for x in re.finditer(rb'\xe8....\xe8....\xe8....\xe8....\xb9\x64\x00\x00\x00\x51\xe8', d, re.S)]
    assert len(vs) == 1, ('practice: VersusInit end', vs)
    vs = vs[0]
    m = []
    for x in re.finditer(rb'\xff\x35....\xc7\x05........\xe8....\x8f\x05', d, re.S):
        o = x.start() + 6
        mt = _t(p, o + 6)
        if _t(p, o + 2) != a6 or not mt or mt[0] != 2:
            continue
        ini = p.target(2, mt[1])
        if ini and ini[0] == 1 and ini[1] <= vs < ini[1] + 0x400:
            m.append((o, mt[1]))
    assert len(m) == 1, ('practice: versusMenu ShowMenu', m)
    return m[0][0], m[0][1], p.call_target(1, m[0][0] + 10)


def time_site(p):
    """UpdateTime's @@make_time_visible: mov ax, [currentTimeSprite.visible] / or / jnz / mov word [..visible], 1 / call
    InitDisplaySprites: (the mov's obj1 offset, visible's obj2 offset, InitDisplaySprites' obj1 offset)."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x75.\x66\xc7\x05....\x01\x00\xe8', d, re.S)]
    m = [o for o in m if _t(p, o + 2) and _t(p, o + 2) == _t(p, o + 14)]
    assert len(m) == 1, ('practice: UpdateTime @@make_time_visible', [hex(x) for x in m])
    vis, ids = _t(p, m[0] + 2), p.call_target(1, m[0] + 20)
    assert vis[0] == 2 and ids[0] == 1, ('practice: currentTimeSprite / InitDisplaySprites', vis, ids)
    return m[0] + 11, vis[1], ids[1]


def rbar_site(p):
    """UpdateGameTimersAndCameraBreakMode's restart score bar: mov ax, [g_inSubstitutesMenu] / or ax, ax / jnz @@out /
    mov word [resultTimer], 31000 / retn - (the mov's obj1 offset, resultTimer's obj2 offset); the only 31000 store
    followed by a retn (30000: GoToHalftime / GameOver, never in a practice: the clock held at 0)."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x75.\x66\xc7\x05....\x18\x79\xc3', d, re.S)]
    assert len(m) == 1, ('practice: the restart score bar (resultTimer = 31000)', [hex(x) for x in m])
    at = m[0] + 11
    rt = _t(p, at + 3)
    assert rt and rt[0] == 2, ('practice: resultTimer', rt)
    cur = p.get(1, at, 9)
    assert cur == d[at:at + 9], ('practice: the score bar store hooked already (a new chain: add it)', cur.hex())
    return at, rt[1]


def km_site(p):
    """kitcolors' km_cancel (pushad / mov byte [KM_ACTIVE], 0 / mov dword [SLOTS + 32], 0 / its kg_cancel1 5-byte site /
    mov esi, TXT_AUTO / call set_button): (KM_ACTIVE, SLOTS + 32, TXT_AUTO, set_button, the 5-byte site's obj1 offset)"""
    d = p.get(1, 0, p.le.obj(1).npages * p.le.page_size)     # (mod code: the patched bytes, not obj_bytes)
    m = [x.start() for x in re.finditer(rb'\x60\xc6\x05....\x00\xc7\x05....\x00\x00\x00\x00(?:\x0f\x1f\x44\x00\xc8|\xe8....)'
                                        rb'\xbe....\xe8....\x61\xe9', d, re.S)]
    assert len(m) == 1, ('practice: kitcolors km_cancel', [hex(x) for x in m])
    o = m[0]
    kma, ksl, txta = _t(p, o + 3), _t(p, o + 10), _t(p, o + 24)
    assert all(v and v[0] == 2 for v in (kma, ksl, txta)), ('practice: km_cancel variables', kma, ksl, txta)
    return kma[1], ksl[1], txta[1], p.call_target(1, o + 28), o + 18


def link_kits(p):
    """after kits.py: pr_pmm's 5-byte site (0F 1F 44 00 D8) -> the call km_cancel's kg_cancel1 site now makes"""
    if 'KG_PR' not in LABELS:
        return
    at, ks = LABELS['KG_PR'], LABELS['KG_SITE']
    assert p.get(4, at, 5) == b'\x0f\x1f\x44\x00\xd8', 'practice: pr_pmm kg site'
    if p.get(1, ks, 1) == b'\xe8':
        t = p.call_target(1, ks)
        p.branch(4, at, 0xE8, t[0], t[1])


TAG = 'PRWK'                            # (the harness finds PR_WORK by it: the tag, then a pointer)
SITES = {}


def sites(p):
    """Before bteam (its ui_sites finds squadMenu by the two `mov dword [A6], squadMenu` bteam replaces): the page's
    game sites and squadMenu entry 6's on-select dword + its current target (SITES)."""
    import bteam
    import xbrowse
    u = bteam.ui_sites(p)
    pay = dict(xbrowse.PAYLOAD)
    pay[7] = 4
    d2 = p.le.obj_bytes(2)
    saved, xbrowse.PAYLOAD = xbrowse.PAYLOAD, pay
    try:
        _, ents = xbrowse.menu_parse(d2, u['menu'])
    finally:
        xbrowse.PAYLOAD = saved
    k, sel = ents[6][0] + 8, None           # the entry's typed fields: its type 13 dword
    while True:
        t = struct.unpack_from('<H', d2, k)[0]
        k += 2
        if t == 0:
            break
        if t == 13:
            sel = k
        k += pay[t]
    assert sel is not None, 'practice: squadMenu entry 6 has no on-select'
    SITES.clear()
    SITES.update(u, sel=sel, old=old_target(p, sel))


def patch(p, lang):
    """The page + code at obj4 swreg.PRACTICE_AT; squadMenu entry 6's on-select -> pr_open (sites() first; swe.c's
    PR_WORK from swe.LABELS: after swe.patch)."""
    import swe
    import swreg
    check_texts()
    u, sel = SITES, SITES['sel']
    old = old_target(p, sel)                # (MC rule 1: still the target read at sites(), nothing hooked it since)
    assert old == SITES['old'], ('practice: entry 6 retargeted between sites() and patch()', old, SITES['old'])
    work = swe.LABELS['PR_WORK']
    assert work[0] == 4, work
    at = swreg.PRACTICE_AT
    q = lambda s: ', '.join(str(c) for c in s.encode('latin-1')) + ', 0'
    tx = texts(lang)
    data = 'align 4\nPR_MENU:\n    dd 0, 0, 0, R_TRAIN_\n'
    data += f'    dw 0, 12, 304, 14\n    dw 4, 17h, 8, 0\n    dd S_T\n    dw 0\n'
    sels = ('pr_r1', 'pr_r2', 'pr_r3', 'pr_r4', 'pr_mode', 'pr_back', 'pr_ns', 'pr_hf')
    # (entry i + 1 = sels[i]; rows: entries 1..5 rows 0..4, the selectors 7 / 8 rows 5 / 6, BACK (6) row 7 - item 2)
    row = (0, 1, 2, 3, 4, 7, 5, 6)
    nav = {1: (0xFF, 2), 2: (1, 3), 3: (2, 4), 4: (3, 5), 5: (4, 7), 7: (5, 8), 8: (7, 6), 6: (8, 0xFF)}
    for i in range(8):
        up, dn = nav[i + 1]
        txt = 'S_ATT' if i == 4 else f'S_{i}' if i < 6 else ('S_SN0', 'S_SH0')[i - 6]
        col = '0Ch' if i == 5 else '0Bh' if i in (4, 6, 7) else '0Eh'   # (C, Davide 15/11: the switch in its own colour)
        lab = ('', 'SELN1: ', 'SELH1: ')[0 if i < 6 else i - 5] if i != 4 else 'MODEP: '
        data += (f'    dw {X}, {Y0 + DYP * row[i]}, {W}, {H}, 2\n    db 255, 255, {up}, {dn}\n'
                 f'    dw 4, {col}, 8, 0\n    {lab}dd {txt}\n    dw 13\n    dd {sels[i]}\n    dw 0\n')
    data += '    dw -999\n'
    sl = SEL[lang]
    data += ''.join(f'S_SN{k}: db {q(t)}\n' for k, t in enumerate(sl[0]))
    data += ''.join(f'S_SH{k}: db {q(t)}\n' for k, t in enumerate(sl[1]))   # (pr_nth: the strings back to back)
    data += 'NTAB: dw ' + ', '.join(str(n) for n in NTAB) + '\n'
    data += f'S_T: db {q(tx[0])}\n' + ''.join(f'S_{i}: db {q(tx[1 + i])}\n' for i in range(4))
    data += f'S_ATT: db {q(tx[5])}\nS_DEF: db {q(tx[6])}\nS_5: db {q(tx[7])}\n'
    rs = RES[lang]
    data += 'align 4\nPR_RES:\n    dd 0, 0, 0, 3\n'                     # (the result page: its OK row the default)
    data += '    dw 0, 12, 304, 14\n    dw 4, 17h, 8, 0\n    dd RT\n    dw 0\n'
    for i, b in ((1, 'R1'), (2, 'R2')):
        data += f'    dw {X}, {Y0 + DY * (i - 1)}, {W}, {H}\n    dw 4, 0Eh, 8, 0\n    dd {b}\n    dw 0\n'
    data += (f'    dw {X}, {Y0 + DY * 3}, {RW}, {H}, 2\n    db 255, 4, 255, 5\n'
             f'    dw 4, 0Ch, 8, 0\n    dd S_OK\n    dw 13\n    dd pr_back\n    dw 0\n'
             f'    dw {X + W - RW}, {Y0 + DY * 3}, {RW}, {H}, 2\n    db 3, 255, 255, 5\n'
             f'    dw 4, 0Eh, 8, 0\n    dd S_AG\n    dw 13\n    dd pr_again\n    dw 0\n'
             # (item 2: the selectors under OK / RIPROVA, entries 5 / 6 - the next practice's attempts and half)
             f'    dw {X}, {Y0 + DY * 4}, {W}, {H}, 2\n    db 255, 255, 3, 6\n'
             f'    dw 4, 0Bh, 8, 0\n    SELN2: dd S_SN0\n    dw 13\n    dd pr_ns\n    dw 0\n'
             f'    dw {X}, {Y0 + DY * 5}, {W}, {H}, 2\n    db 255, 255, 5, 255\n'
             f'    dw 4, 0Bh, 8, 0\n    SELH2: dd S_SH0\n    dw 13\n    dd pr_hf\n    dw 0\n    dw -999\n')
    data += f'S_SH: db {q(rs[0])}\nS_GL: db {q(rs[1])}\nS_OK: db {q(rs[2])}\nS_AG: db {q(rs[3])}\n'
    data += 'align 4\nKTAB: dd S_1, S_2, S_3\n'
    assert max(len(t) for t in tx[2:5]) < 24 and max(len(t) for t in res_texts(lang)) < 16
    data += f'align 4\nPRTAG: db {q(TAG)[:-3]}\n    dd KIND - 1\n'   # (the harness: the tag, then PR_WORK)
    assert max(len(tx[5]), len(tx[6])) < 24
    d1 = p.le.obj_bytes(1)
    ptg = old[1] + 5 + struct.unpack('<i', d1[old[1] + 1:old[1] + 5])[0]     # (SelectTraining's call PlayTrainingGame)
    g = find_game(p, u['a6'], ptg)
    hk, hk_old = hook_site(p)
    tm, tvis, ids = time_site(p)
    rb, rtim = rbar_site(p)
    pm, pmmenu, pmshow, pnts, pmt1, sbench = pm_site(p, u['a6'])
    kma, ksl, txta, setbtn, kgsite = km_site(p)
    pg = _t(p, hk + 7)                  # (the site's next instruction: mov ax, [playGame])
    assert pg and pg[0] == 2, ('practice: playGame', pg)
    g = dict(g, PLAYG_O=pg[1])
    sd, stadm, stshow = stad_site(p, u['a6'], pg[1])
    vsd, vsm, vshow = vs_site(p, u['a6'])
    assert FKD == tuple(FKD[0] + (FKD[1] - FKD[0]) * k for k in range(4)) and FKX[0] == 336
    assert work[1] % 4 == 0 and WORK_SZ >= WK['END'], 'practice: PR_WORK (swe.c u8 PR_WORK[WORK_SZ], aligned 4)'
    assert WK['END'] <= min(o for o, _ in BUF.values()) and max(o + n for o, n in BUF.values()) <= WORK_SZ
    assert WK['NG'] == WK['NT'] + 2, 'practice: pr_one reads NT then NG'
    assert WK['END'] <= WK['NSEL'] < WK['HALF'] < min(o for o, _ in BUF.values()), 'practice: NSEL / HALF kept (after END)'
    defs = {f'W_{k}_': v for k, v in WK.items()}
    defs.update(R_TRAIN_=R_TRAIN, R_MODE_=R_MODE, R_NS_=R_NS, WAITF_=WAITF, ATTF_=ATTF, SETTLE_=SETTLE, CLEAR_=CLEAR,
                FKORD_=FKORD, PEN_D_=PEN_D, PR_N_=PR_N, FKD0_=FKD[0], FKD_STEP_=FKD[1] - FKD[0], FKX1_=FKX[1], FKX2_=FKX[2])
    src = ''.join(f'%define {k} {v}\n' for k, v in defs.items()) + ASM + data
    sym = {'A6': u['a6'], 'SHOW_MENU': (1, u['show']), 'EXITM': u['exitm'], 'OLD_SEL': old,
           'GO': (4, work[1]), 'KIND': (4, work[1] + 1), 'DEF': (4, work[1] + 2), 'O2BASE': (2, 0),
           'TESTFOUL': (1, g['TESTFOUL']), 'TVIS': (2, tvis), 'RTIM': (2, rtim), 'INITDS': (1, ids), 'PMMENU': (2, pmmenu), 'STADM': (2, stadm), 'STADSHOW': stshow,
           'VSM': (2, vsm), 'VSSHOW': vshow, 'SWAPH': (1, swap_site(p, g)),
           'SHOWMENU': pmshow, 'PNTS': (2, pnts), 'PMT1': (2, pmt1), 'SETBENCH': sbench,
           'KMA': (2, kma), 'KSL': (2, ksl), 'TXTA': (2, txta), 'SETBTN': setbtn,
           **{k: (4, work[1] + o) for k, (o, _) in BUF.items()},
           **{k: (0, v) for k, v in g.items() if k != 'TESTFOUL'}}
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert p.le.obj(4).npages * 0x1000 >= swreg.PRACTICE_END, 'practice: obj4 pages (patch.py)'
    left = swreg.PRACTICE_END - at - len(code)
    floor = int(os.environ.get('PRACTICE_BAND_FLOOR', '256'))     # (MC's floor; a test build may lower it)
    assert left >= floor, ('practice: past its obj4 band (MC: >= 256 B left; ask MC before more)', left)
    assert not any(p.get(4, at, swreg.PRACTICE_END - at)), 'practice: obj4 band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.remove(2, sel)                                    # squadMenu entry 6's on-select: SelectTraining -> pr_open
    p.add_ptr(2, sel, 4, lab['pr_open'])
    p.branch(1, hk, 0xE8, 4, lab['pr_frame'])           # GameLoop's per-pass nullsub call -> pr_frame (step 2)
    p.remove(1, tm + 3)                                 # UpdateTime's mov visible, 1 + call InitDisplaySprites (14 B)
    p.branch(1, tm, 0xE8, 4, lab['pr_time'], n=14)      #  -> call pr_time (no clock in a practice)
    p.remove(1, rb + 3)                                 # the restart's mov word [resultTimer], 31000 (9 B, its
    p.branch(1, rb, 0xE8, 4, lab['pr_rbar'], n=9)       #  fixup removed) -> call pr_rbar + 4 nop (no score bar)
    assert _t(p, rb + 3) is None and p.rel_target(1, rb + 1) == (4, lab['pr_rbar']), 'practice: pr_rbar fixups'
    p.remove(1, pm + 2)                                 # ShowPlayMatchMenu's mov [A6], playMatchMenu + call ShowMenu
    p.remove(1, pm + 6)                                 #  (15 B) -> call pr_pmm (no pre-match screen in a practice)
    if p.rel_target(1, pm + 11):
        p.remove(1, pm + 11)
    p.branch(1, pm, 0xE8, 4, lab['pr_pmm'], n=15)
    p.remove(1, sd + 2)                                 # GameLoop's mov [A6], stadiumMenu + call ShowMenu (15 B)
    p.remove(1, sd + 6)                                 #  -> call pr_stad (no presentation before a practice)
    if p.rel_target(1, sd + 11):
        p.remove(1, sd + 11)
    p.branch(1, sd, 0xE8, 4, lab['pr_stad'], n=15)
    p.remove(1, vsd + 2)                                # InitializeInGameTeamsAndStartGame's mov [A6], versusMenu +
    p.remove(1, vsd + 6)                                #  call ShowMenu (15 B) -> call pr_vs (no versus screen either)
    if p.rel_target(1, vsd + 11):
        p.remove(1, vsd + 11)
    p.branch(1, vsd, 0xE8, 4, lab['pr_vs'], n=15)
    LABELS.clear()
    LABELS.update(lab)
    LABELS['STAD'] = (1, sd)
    LABELS['VS'] = (1, vsd)
    LABELS['PR_WORK'] = work
    kg = code.find(b'\x0f\x1f\x44\x00\xd8')
    assert kg > 0 and code.count(b'\x0f\x1f\x44\x00\xd8') == 1
    LABELS['KG_PR'], LABELS['KG_SITE'] = at + kg, kgsite
    LABELS['ENT6_SEL'] = (2, sel)
    LABELS['HOOK'] = (1, hk)
    LABELS['RBAR'] = (1, rb)
    LABELS['GAME'] = g
    print(f'exe: practice page (squadMenu entry 6 obj2+{sel:#x} -> obj4 pr_open; its old target obj1+{old[1]:#x}): '
          f'obj4+{at:#x} ({len(code)} B, {left} B left), work PR_WORK obj4+{work[1]:#x}; engine: GameLoop obj1+{hk:#x} '
          f'(was obj1+{hk_old[1]:#x}, a ret) -> pr_frame obj4+{lab["pr_frame"]:#x}, {len(fix)} fixups + {len(rel)} rel')
