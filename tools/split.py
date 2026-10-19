"""Mid-season split of a career world's league division (World 2026-27: Scotland, Austria, Greece, Romania ...).

pack.json, a division of the league competition:
  "split": {"games": 3, "groups": [6, 6], "rounds": [1, 1], "points": ["full", "full"], "home": "balance"}
- games: how many times each pair meets before the split (the division's own; the league struct has one 'games' for
  every division). Alone (no groups) it only sets that division's meetings (Scotland's lower divisions: 4).
- groups: sizes, top to bottom (the table at the split, places in order); rounds: 0 (no more matches: Czech middle
  group), 1 (single round robin), 2 (double), 3 (triple) or 4 (quadruple: Latvia 1996) per group; points: "full", "half_up" (Romania, Greece 5-8),
  "half_down" per group;
- home (single round robin after the split): "balance" = the club that hosted the other fewer times before the
  split (Scotland, Switzerland, Korea: every pair ends 2 + 2), "reverse3" = the club that was away in their 3rd
  meeting (Northern Ireland's written rule), "seeded" (default) = a balanced calendar where the extra home game goes
  to the better placed clubs. A double round robin after the split: the same balanced calendar, mirrored.

The engine (swos.asm): a league runs in DIY_competitionStart. cseg_8F1F2 (a league struct's division -> DIY, career
and season-end simulation alike) ends with cseg_2653B: [5Dh] meetings, [5Fh] cycles left, [1C3h] days, then
cseg_2730A spreads the days' weeks linearly over the season (+1CDh, a byte per day). Every match = cseg_89758 (the
pairing of [1CBh] in the per-size table dseg_11F356[n-2], slots -> rows by the slot list +0EDh, [5Fh] odd swaps
home / away) + cseg_8922B (counters: [1C9h] matches today vs [1C7h] -> [1BFh] day done, [1C1h] day, [2Eh] its week;
[5Fh] = 0: the stage is over) + cseg_883DD (sort into +6Dh). The career calendar (cseg_8B8D9) and the season-end
simulation (cseg_3AE87) go through the same routines.
Hooks:
- sp_init (8F1F2's `call cseg_2653B`): a division of SP_TAB gets [5Dh] = [5Fh] = games + 1 (one more cycle, so the
  stage does not end at the split), [1C3h] = days before + after, the weeks again (cseg_2730A); the state at DIY+ST
  (rows 48-63, unused by a league of <= 24 clubs, saved with the slot): magic, the entry, frozen.
- sp_pair (cseg_89758, `mov esi, [A0]` before its home / away test): from day d1 on, the match [1C9h] of the day from
  our calendar (places -> rows of the table frozen at the split); the first such call (not the calendar builder's)
  freezes the groups, halves the points (the points before rounding kept: the first tie-break), sorts, and rewrites
  the career calendar's blocks of the days after the split (the career club's next fixtures);
- sp_count (cseg_8922B, `mov esi, [A0]` after the played counts): the day counters of our calendar (any number of
  matches a day: groups of different sizes, byes), the stage over after its last day;
- sp_sort (cseg_883DD's last `jns`): after the engine's sort (points, goal difference, goals, name), a stable
  partition into the groups (the bottom group never above the top one) + the 'points before rounding' tie-break:
  +6Dh is always the final table in place order (dplay reads it unchanged).
"""
import re
import struct

WEEKS = 0x1CD                   # DIY: the match days' weeks, a byte per day (cseg_2730A), up to +2B3h (the rows)
import os as _os
NMAX = int(_os.environ.get("SPLIT_NMAX", 30))   # (the state's layout follows it: 30 = Argentina's 30 rows, MAXDAYS 40)
OFF = dict(magic=0, entry=2, frozen=4, kept=5, p2r=6, grp=6 + NMAX, pre=6 + 2 * NMAX, h2h=6 + 4 * NMAX)
ST_SIZE = OFF['h2h'] + 64       # (24: 166)
ST = 0x2B3 - ST_SIZE            # our state: the end of the weeks table (a split league has at most MAXDAYS days);
MAXDAYS = ST - WEEKS            # 64     never in the rows (some routines walk all 64 rows by their team dword)
MAGIC = 0x50FE                  # (FEh: never a week)
POINTS = {'full': 0, 'half_up': 1, 'half_down': 2, 'reset': 3, 'h2h_half': 4, 'half_down_h2h': 4}
H2H_NMAX = 8                    # head-to-head points: n x n bytes after the state (rows 48-63 end at ST + 288)

ASM = r"""
%define S_MAGIC  ST_
%define S_ENTRY  ST_ + 2
%define S_FROZEN ST_ + 4
%define S_KEPT   ST_ + 5                ; 1 = a 'keep' stage's table is in S_KEEP (gplay's gp_cap: GP_IN.st)
%define S_P2R    ST_ + 6
%define S_GRP    ST_ + O_GRP
%define S_PRE    ST_ + O_PRE
%define S_H2H    ST_ + O_H2H

%define S_KEEP   ST_ + O_H2H              ; (the head-to-head bytes: never in one league with a 'keep' stage)
%define E_CNT    8
%define E_FIRST  10
%define E_PAIRS  12
%define E_LEN    14
%define E_STG    16
%define SR_      28

; entry: +0 world, +1 team file, +2 division, +3 clubs, +4 cycles, +5 days before, +6 days after, +7 stages,
;        +8 word days' counts, +10 word days' first pair, +12 word pairs, +14 word entry length (offsets from the
;        entry), +16 the stages, 20 bytes each: first day after the split, groups, flags (1 reset, 2 keep), -,
;        (first place, size, points) x 4, word matrix (0 = none), word -, word members (0 = groups by places),
;        db callback (1+: SP_CB, after the stage's last day; not in a simulation), db table (1+: GP_SS index,
;        gplay.c gp_stage), db annual, -, word weeks (stage 0 only: a byte per day, the days' weeks; 0 = the
;        game's spread); flags 1 reset, 2 keep, 4 rows (pairs are table rows: a fixture list), 8 members

sp_init:                                ; replaces `call cseg_2653B` at the end of cseg_8F1F2 (A5 struct; the division
                                        ; from its start, sp_div8f)
    call C2653B
    pushad
    cmp word [DIY + S_MAGIC], MAGIC_    ; every league init: no mark of a previous split league (its weeks may
    jne .clean                          ; cover the block: only our mark is cleared)
    mov word [DIY + S_MAGIC], 0
.clean:
    mov esi, [A5]
    mov ah, [esi + 2]                   ; the struct's team file
    xor al, al                          ; a season (one division, one year: 4.0) -> world 0, the original one
    cmp word [GAMETYPE], 3
    je .w
    cmp word [GAMETYPE], 4              ; a career: its world byte
    jne .x
    mov al, [SLT + WORLD_BYTE]
.w:
    mov dl, [sp_div]
    mov edi, SP_TAB
.find:
    cmp word [edi + E_LEN], 0           ; (the table ends with a zero length: world 0 is a world)
    je .x
    cmp [edi], ax
    jne .next
    cmp [edi + 2], dl
    je .found
.next:
    movzx ecx, word [edi + E_LEN]
    add edi, ecx
    jmp .find
.found:
    mov ebx, DIY
    movzx ecx, byte [edi + 3]
    cmp [ebx + 31h], cx
    jne .x
    push edi
    lea edi, [ebx + ST_]                ; a fresh state
    mov ecx, ST_SIZE
    xor eax, eax
    rep stosb
    pop edi
    mov word [ebx + S_MAGIC], MAGIC_
    mov eax, edi
    sub eax, SP_TAB
    mov [ebx + S_ENTRY], ax
    mov byte [ebx + S_FROZEN], 0
    movzx eax, byte [edi + 4]
    mov [ebx + 5Dh], ax
    mov [ebx + 5Fh], ax
    movzx eax, byte [edi + 5]
    movzx ecx, byte [edi + 6]
    add eax, ecx
    mov [ebx + 1C3h], ax
    call sp_saveregs
    call C2730A                         ; the days' weeks again
    call sp_restregs
    cmp byte [edi + 7], 0               ; (no stages: a meetings-only entry has no stage record)
    je .x
    movzx esi, word [edi + E_STG + 26]  ; our own weeks (a calendar with breaks: Argentina's knockout weeks)
    test esi, esi
    jz .x
    add esi, edi
    movzx ecx, word [ebx + 1C3h]
    xor eax, eax
.wk:
    mov dl, [esi + eax]
    mov [ebx + 1CDh + eax], dl
    inc eax
    cmp eax, ecx
    jb .wk
.x:
    popad
    ret

sp_div8f:                               ; replaces `mov ax, [D0]` at the start of cseg_8F1F2: its division (D7 is a
    mov ax, [D0]                        ; loop counter by the end)
    mov [sp_div], ax
    ret

sp_saveregs:                            ; the pseudo registers D0..A6 (the game's routines we call use them)
    push esi
    push edi
    push ecx
    mov esi, REGS
    mov edi, sp_regs
    mov ecx, 15
    rep movsd
    pop ecx
    pop edi
    pop esi
    ret
sp_restregs:
    push esi
    push edi
    push ecx
    mov esi, sp_regs
    mov edi, REGS
    mov ecx, 15
    rep movsd
    pop ecx
    pop edi
    pop esi
    ret

sp_entry:                               ; -> edx = the DIY league's entry, esi = DIY; ZF = 1 when none / no split
    mov esi, DIY
    xor edx, edx
    cmp word [esi + S_MAGIC], MAGIC_
    jne .no
    cmp word [esi], 0                   ; a league (a cup copied over it leaves our rows: 443h bytes)
    jne .no
    movzx edx, word [esi + S_ENTRY]
    add edx, SP_TAB
    cmp byte [edx + 6], 0
    je .no
    or esi, esi                         ; (ZF = 0)
    ret
.no:
    xor eax, eax                        ; (ZF = 1)
    ret

sp_stage:                               ; ecx = day after the split -> eax = its stage, ebp = the stage's record
    movzx eax, byte [edx + 7]
.l:
    dec eax
    js .first
    imul ebp, eax, SR_
    lea ebp, [edx + E_STG + ebp]
    cmp cl, [ebp]
    jb .l
    ret
.first:
    xor eax, eax
    lea ebp, [edx + E_STG]
    ret

sp_rows:                                ; ecx = day after the split, ebx = match of the day -> eax = home row,
    push esi                            ; ebx = away row (esi = DIY, edx = entry); the places of the table frozen
    push edi                            ; for that day's stage (else, in the calendar builder: places = rows)
    push ebp
    call sp_stage
    push eax
    movzx edi, word [edx + E_FIRST]
    add edi, edx
    movzx eax, word [edi + ecx * 2]     ; the day's first pair
    add ebx, eax
    lea ebx, [ebx + ebx * 2]
    movzx edi, word [edx + E_PAIRS]
    add edi, edx
    add edi, ebx                        ; the pair: home place, away place, flags
    pop ebx
    inc ebx
    movzx eax, byte [edi]
    cmp [esi + S_FROZEN], bl
    movzx ebx, byte [edi + 1]
    jne .places
    test byte [ebp + 2], 4              ; a fixture list: the pairs are rows already
    jnz .places
    movzx eax, byte [esi + S_P2R + eax]
    movzx ebx, byte [esi + S_P2R + ebx]
.places:
    test byte [edi + 2], 1
    jz .r
    movzx edi, word [ebp + 16]          ; this stage's matrix of the slots (the fixtures before the split)
    push ecx
    push ebp
    call sp_slot                        ; ebp = slot of the first row
    mov ecx, ebp
    xchg eax, ebx
    call sp_slot                        ; ebp = slot of the second row
    xchg eax, ebx
    push eax
    movzx eax, byte [edx + 3]
    imul eax, ecx
    add eax, ebp
    add eax, edi
    mov cl, [edx + eax]                 ; 1 = the first at home, 0 = the second, 2 = the calendar's
    pop eax
    test cl, cl
    jnz .k
    xchg eax, ebx
.k:
    pop ebp
    pop ecx
.r:
    pop ebp
    pop edi
    pop esi
    ret

sp_slot:                                ; eax = row -> ebp = its slot in the slot list (+0EDh, group 0)
    push ecx
    movzx ecx, byte [edx + 3]
    xor ebp, ebp
.l:
    cmp [esi + 0EDh + ebp], al
    je .r
    inc ebp
    cmp ebp, ecx
    jb .l
    xor ebp, ebp
.r:
    pop ecx
    ret

sp_pair:                                ; replaces `mov esi, [A0]` before cseg_89758's home / away test
    pushad
    call sp_entry
    jz .game
    movzx ecx, word [esi + 1C1h]
    movzx eax, byte [edx + 5]
    sub ecx, eax
    jae .after
    mov byte [esi + S_FROZEN], 0        ; before the split (a new season, the calendar builder's reset)
    jmp .game
.after:
    cmp cl, [edx + 6]
    jae .game                           ; (the stage is over)
    push ecx
    call sp_stage                       ; this day's stage: its table frozen?
    inc eax
    cmp [esi + S_FROZEN], al
    je .fz
    cmp dword [esp + 40], BUILDER_RET   ; the calendar builder at the season start: no freeze
    je .fz
    dec eax
    call sp_freeze
.fz:
    pop ecx
.frozen:
    xor ebx, ebx
    cmp word [esi + 1BFh], 0            ; (the day just done: the next match is the next day's first)
    jne .m
    movzx ebx, word [esi + 1C9h]
.m:
    call sp_rows
    imul eax, eax, 18
    add eax, DIY
    mov [A1], eax
    imul ebx, ebx, 18
    add ebx, DIY
    mov [A2], ebx
    popad
    add esp, 4                          ; return from cseg_89758 itself
    ret
.game:
    popad
    mov esi, [A0]
    ret

sp_freeze:                              ; esi = DIY, edx = entry, eax = stage, ebp = its record: the groups
    pushad                              ; from the table now, its points rules. The table sorted first: the last
    call sp_saveregs                    ; day's last results may not be in its order yet (Malta: the kept table and
    call C883DD                         ; the groups a match behind); the previous stage's groups still partition it
    call sp_restregs
    popad
    mov [sp_rec], ebp
    mov [sp_stg], al
    movzx ecx, byte [edx + 3]
    mov [sp_n], ecx
    test byte [ebp + 2], 2              ; keep: the table before this stage (row by place, then its points)
    jz .nokeep
    mov byte [esi + S_KEPT], 1
    xor ecx, ecx
.keep:
    movzx eax, word [esi + 6Dh + ecx * 2]
    mov bx, [esi + eax + 2C3h]
    mov [esi + S_KEEP + 22 + ecx * 2], bx
    push edx
    push ecx
    xor edx, edx
    mov ecx, 18
    div ecx
    pop ecx
    pop edx
    mov [esi + S_KEEP + ecx], al
    inc ecx
    cmp ecx, [sp_n]
    jb .keep
.nokeep:
    test byte [ebp + 2], 1              ; reset: every figure from 0 (played .. points)
    jz .p2r
    xor ecx, ecx
.zero:
    imul eax, ecx, 18
    lea edi, [esi + eax + 2B7h]
    mov dword [edi], 0
    mov dword [edi + 4], 0
    mov dword [edi + 8], 0
    mov word [edi + 12], 0
    inc ecx
    cmp ecx, [sp_n]
    jb .zero
.p2r:
    xor ecx, ecx
.pr:
    movzx eax, word [esi + 6Dh + ecx * 2]
    push edx
    xor edx, edx
    mov ebx, 18
    div ebx
    pop edx
    mov [esi + S_P2R + ecx], al
    inc ecx
    cmp ecx, [sp_n]
    jb .pr
    lea edi, [esi + S_GRP]
    mov ecx, NMAX_
    mov al, 0FFh
    rep stosb
    mov ebp, [sp_rec]
    test byte [ebp + 2], 8              ; groups by membership (Argentina's zones): the row's group from the entry
    jz .byplace
    movzx edi, word [ebp + 20]
    add edi, edx
    xor ecx, ecx
.mb:
    mov al, [edi + ecx]
    mov [esi + S_GRP + ecx], al
    imul eax, ecx, 18
    mov ax, [esi + eax + 2C3h]
    mov [esi + S_PRE + ecx * 2], ax
    inc ecx
    cmp ecx, [sp_n]
    jb .mb
    jmp .done
.byplace:
    xor ebx, ebx                        ; group
.g:
    mov ebp, [sp_rec]
    cmp bl, [ebp + 1]
    jae .done
    lea eax, [ebx + ebx * 2]
    movzx ecx, byte [ebp + 4 + eax]     ; its first place
    mov [sp_first], ecx
    movzx edi, byte [ebp + 5 + eax]
    add edi, ecx                        ; its end
    mov al, [ebp + 6 + eax]
    mov [sp_rule], al
    push edi
.pl:
    cmp ecx, [esp]
    jae .gn
    movzx eax, byte [esi + S_P2R + ecx] ; the place's row
    mov [esi + S_GRP + eax], bl
    imul edi, eax, 18
    movzx ebp, word [esi + edi + 2C3h]  ; its points
    mov [esi + S_PRE + eax * 2], bp     ; (the first tie-break)
    mov al, [sp_rule]
    cmp al, 1
    jne .down
    inc ebp                             ; half_up
    shr ebp, 1
    jmp .set
.down:
    cmp al, 2
    jne .reset
    shr ebp, 1                          ; half_down
    jmp .set
.reset:
    cmp al, 3
    jne .h2h
    xor ebp, ebp                        ; reset (points only; a stage's reset flag clears every figure)
    movzx eax, byte [esi + S_P2R + ecx]
    mov word [esi + S_PRE + eax * 2], 0
    jmp .set
.h2h:
    cmp al, 4
    jne .next
    push ecx                            ; h2h_half: half the points won against the group's clubs, rounded down
    push edx
    movzx eax, byte [esi + S_P2R + ecx]
    imul eax, [sp_n]                    ; its line of the head-to-head table
    xor ebp, ebp
    mov ecx, [sp_first]
.hq:
    cmp ecx, [esp + 8]
    jae .hd
    movzx edx, byte [esi + S_P2R + ecx]
    add edx, eax
    movzx edx, byte [esi + S_H2H + edx]
    add ebp, edx
    inc ecx
    jmp .hq
.hd:
    pop edx
    pop ecx
    movzx eax, byte [esi + S_P2R + ecx]
    mov [esi + S_PRE + eax * 2], bp     ; (tie-break: the head-to-head points before rounding)
    shr ebp, 1
.set:
    mov [esi + edi + 2C3h], bp
.next:
    inc ecx
    jmp .pl
.gn:
    pop edi
    inc ebx
    jmp .g
.done:
    mov al, [sp_stg]
    inc al
    mov [esi + S_FROZEN], al
    pushad                              ; (the game's sort uses every register)
    call sp_saveregs
    call C883DD                         ; the table with the groups (and the points rules) now
    call sp_restregs
    popad
    cmp word [SIMFLAG], 0               ; the season-end simulation (cseg_3ABB2): no calendar
    jne .r
    call sp_calendar
.r:
    ret

sp_calendar:                            ; the career calendar's blocks of the days after the split: the career
    pushad                              ; club's match of each day (cseg_8B8D9's record), or none
    mov edi, CAL
    movzx ebp, word [CALN]
    xor ecx, ecx                        ; the league's block count
.b:
    dec ebp
    js .x
    mov al, [esi + 2Bh]
    cmp [edi], al
    jne .nb
    push ecx
    movzx eax, byte [edx + 5]
    sub ecx, eax
    jb .skip
    cmp cl, [edx + 6]
    jae .skip
    mov eax, [sp_rec]
    cmp cl, [eax]                       ; (from this stage's first day)
    jb .skip
    call sp_block
.skip:
    pop ecx
    inc ecx
.nb:
    movzx eax, word [edi + 2]
    add edi, eax
    jmp .b
.x:
    popad
    ret

sp_block:                               ; edi = block, ecx = day after the split
    mov byte [edi + 5], 0
    mov byte [edi + 6], 0
    movzx eax, word [edx + E_CNT]
    add eax, edx
    movzx eax, byte [eax + ecx]         ; matches that day
    push eax
    xor ebx, ebx
.m:
    cmp ebx, [esp]
    jae .r
    push ebx
    push ecx
    call sp_rows                        ; eax home row, ebx away row
    imul eax, eax, 18
    mov eax, [esi + eax + 2B3h]
    add eax, [SELTEAMS]
    imul ebx, ebx, 18
    mov ebx, [esi + ebx + 2B3h]
    add ebx, [SELTEAMS]
    mov cl, 1                           ; (cseg_8B8D9: teamControls 1 = the computer's; a match with another
    cmp byte [eax + 4], 1               ; club is the career club's: 1 = it plays at home, 2 = away)
    jne .rec
    mov cl, 2
    cmp byte [ebx + 4], 1
    jne .rec
    pop ecx
    pop ebx
    inc ebx
    jmp .m
.rec:
    mov [edi + 0Ah], cl
    mov byte [edi + 0Bh], 0
    mov ax, [eax]
    mov [edi + 0Ch], ax
    mov ax, [ebx]
    mov [edi + 0Eh], ax
    mov byte [edi + 5], 1
    mov byte [edi + 6], 1
    pop ecx
    pop ebx
.r:
    pop eax
    ret

sp_count:                               ; replaces `mov esi, [A0]` in cseg_8922B after the played counts
    pushad
    call sp_entry
    jz .game
    movzx ecx, word [esi + 1C1h]
    movzx eax, byte [edx + 5]
    sub ecx, eax
    jb .game
    cmp cl, [edx + 6]
    jae .game
    cmp word [esi + 1BFh], 0
    je .c
    mov word [esi + 1BFh], 0
    mov word [esi + 1C9h], 0
.c:
    inc word [esi + 1C9h]
    movzx eax, word [edx + E_CNT]
    add eax, edx
    movzx eax, byte [eax + ecx]
    cmp [esi + 1C9h], ax
    jb .ret
    mov word [esi + 1BFh], 1            ; the day is over
    inc word [esi + 1C1h]
    movzx eax, word [esi + 1C1h]
    mov al, [esi + 1CDh + eax]
    mov [esi + 2Eh], al
    mov [WEEK], al
    call sp_stage_end
    inc ecx
    cmp cl, [edx + 6]
    jb .ret
    mov word [esi + 5Fh], 0             ; the last day: the stage is over
.ret:
    popad
    add esp, 4                          ; return from cseg_8922B itself
    ret
.game:
    popad
    mov esi, [A0]
    ret

sp_stage_end:                           ; ecx = the day just over (after the split), esi = DIY, edx = entry: the last
    pushad                              ; day of its stage -> its table into GP_SS (gplay.c gp_stage), its callback
    call sp_stage                       ; eax = stage, ebp = its record
    lea ebx, [eax + 1]
    movzx edi, byte [edx + 7]
    cmp ebx, edi
    jae .last
    imul ebx, ebx, SR_
    movzx ebx, byte [edx + E_STG + ebx] ; the next stage's first day
    jmp .cmp
.last:
    movzx ebx, byte [edx + 6]
.cmp:
    lea edi, [ecx + 1]
    cmp edi, ebx
    jne .r
    movzx eax, byte [ebp + 23]
    test eax, eax
    jz .cb
    pushad
    call sp_saveregs
    call C883DD                         ; (the last results in the table's order)
    call sp_restregs
    popad
    pushad
    dec eax
    movzx ebx, byte [ebp + 24]
    push es                             ; (es first: the C code's arguments must be right above the return address)
    push ds
    pop es
    cld
    push ebx
    push eax
    push dword [SELTEAMS]
    push dword DIY
    call GP_STAGE
    add esp, 16
    pop es
    popad
.cb:
    movzx eax, byte [ebp + 22]
    test eax, eax
    jz .r
    cmp word [SIMFLAG], 0               ; (the season-end simulation of a league: tables only)
    jne .r
    call sp_saveregs
    call [SP_CB + eax * 4 - 4]
    call sp_restregs
.r:
    popad
    ret

sp_cpu:                                 ; replaces cseg_8EF7B's first `call cseg_89758` (the computer's matches up to
    pushad                              ; the career club's): when the career club plays no more on this day after
    call sp_entry                       ; the split (byes of odd groups, shorter groups), only the rest of this day
    jz .game                            ; (else the next day's matches up to its own: its block then played twice)
    movzx ecx, word [esi + 1C1h]
    movzx eax, byte [edx + 5]
    sub ecx, eax
    jb .game
    cmp cl, [edx + 6]
    jae .game
    xor ebx, ebx
    cmp word [esi + 1BFh], 0
    jne .first
    movzx ebx, word [esi + 1C9h]
.first:
    movzx eax, word [edx + E_CNT]
    add eax, edx
    movzx eax, byte [eax + ecx]
    push eax                            ; the day's matches
.m:
    cmp ebx, [esp]
    jae .idle
    push ebx
    push ecx
    call sp_rows
    imul eax, eax, 18
    mov eax, [esi + eax + 2B3h]
    add eax, [SELTEAMS]
    imul ebx, ebx, 18
    mov ebx, [esi + ebx + 2B3h]
    add ebx, [SELTEAMS]
    cmp byte [eax + 4], 1
    jne .plays
    cmp byte [ebx + 4], 1
    jne .plays
    pop ecx
    pop ebx
    inc ebx
    jmp .m
.plays:
    pop ecx
    pop ebx
    pop eax
.game:
    popad
    jmp C89758                          ; (the game's: its call returns to cseg_8EF7B)
.idle:
    pop eax
    popad
.loop:                                  ; the rest of the day, then out of cseg_8EF7B
    mov word [D7], 0
    call C88A12
    mov esi, DIY
    cmp word [esi + 1BFh], 0
    je .loop
    add esp, 4
    ret

sp_res:                                 ; replaces `add word [esi+1BDh], 1` in cseg_88A12 (a result into the rows):
    add word [esi + 1BDh], 1            ; before the split, the points of each pair (head-to-head groups only)
    pushad
    call sp_entry
    jz .x
    cmp byte [esi + S_FROZEN], 0
    jne .x
    xor ecx, ecx
.g:
    cmp cl, [edx + E_STG + 1]           ; (the first stage's groups)
    jae .x
    lea eax, [ecx + ecx * 2]
    cmp byte [edx + E_STG + 6 + eax], 4
    je .rec
    inc ecx
    jmp .g
.rec:
    mov eax, [A3]
    sub eax, DIY
    xor edx, edx
    mov ecx, 18
    div ecx
    mov edi, eax                        ; home row
    mov eax, [A4]
    sub eax, DIY
    xor edx, edx
    div ecx
    mov ebx, eax                        ; away row
    call sp_entry
    movzx ecx, byte [edx + 3]
    mov eax, edi
    imul eax, ecx
    add eax, ebx
    lea eax, [esi + S_H2H + eax]        ; home's points against away
    imul ebx, ecx
    add ebx, edi
    lea ebx, [esi + S_H2H + ebx]        ; away's against home
    mov cx, [D1]
    cmp cx, [D2]
    je .draw
    mov dl, [esi + 61h]                 ; (the win points)
    ja .home
    add [ebx], dl
    jmp .x
.home:
    add [eax], dl
    jmp .x
.draw:
    inc byte [eax]
    inc byte [ebx]
.x:
    popad
    ret

sp_sort:                                ; replaces cseg_883DD's last `jns` (the group loop)
    jns .loop
    pushad
    call sp_entry
    jz .x
    movzx eax, byte [esi + S_FROZEN]
    dec eax
    js .x
    imul eax, eax, SR_
    mov al, [edx + E_STG + 1 + eax]     ; the frozen stage's groups
    mov [sp_G], al
    xor ebx, ebx                        ; group
    xor edi, edi                        ; out count
.g:
    cmp bl, [sp_G]
    jae .copy
    xor ecx, ecx
.p:
    movzx eax, word [esi + 6Dh + ecx * 2]
    push eax
    push edx
    xor edx, edx
    mov ebp, 18
    div ebp
    pop edx
    cmp [esi + S_GRP + eax], bl
    pop eax
    jne .np
    mov [sp_tmp + edi * 2], ax
    inc edi
.np:
    inc ecx
    cmp cl, [edx + 3]
    jb .p
    inc ebx
    jmp .g
.copy:
    xor ecx, ecx
.c:
    cmp ecx, edi
    jae .tie
    mov ax, [sp_tmp + ecx * 2]
    mov [esi + 6Dh + ecx * 2], ax
    inc ecx
    jmp .c
.tie:                                   ; equal points in one group: more points before rounding first
    mov ebp, NMAX_
.pass:
    xor ecx, ecx
.t:
    lea eax, [ecx + 1]
    cmp al, [edx + 3]
    jae .tn
    movzx eax, word [esi + 6Dh + ecx * 2]
    movzx ebx, word [esi + 6Fh + ecx * 2]
    push ecx
    mov cx, [esi + eax + 2C3h]
    cmp cx, [esi + ebx + 2C3h]
    jne .tk
    push edx
    push eax
    xor edx, edx
    mov ecx, 18
    div ecx
    mov ecx, eax                        ; row a
    mov eax, ebx
    xor edx, edx
    push ebx
    mov ebx, 18
    div ebx
    pop ebx                             ; eax = row b
    mov dl, [esi + S_GRP + ecx]
    cmp dl, [esi + S_GRP + eax]
    jne .tp
    mov dx, [esi + S_PRE + ecx * 2]
    cmp dx, [esi + S_PRE + eax * 2]
    jae .tp
    pop eax
    pop edx
    pop ecx
    mov [esi + 6Dh + ecx * 2], bx       ; swap
    mov [esi + 6Fh + ecx * 2], ax
    jmp .tn2
.tp:
    pop eax
    pop edx
.tk:
    pop ecx
.tn2:
    inc ecx
    jmp .t
.tn:
    dec ebp
    jnz .pass
.x:
    popad
    ret
.loop:
    mov dword [esp], C88420
    ret

sp_regs: times 15 dd 0
sp_rec: dd 0
sp_n: dd 0
sp_first: dd 0
sp_stg: db 0
sp_rule: db 0
sp_G: db 0
sp_div: dd 0
sp_tmp: times NMAX_ dw 0
align 4
SP_CB: SP_CB_ENTRIES
sp_nostage:
    ret
align 4
SP_TAB:
"""


MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def week_of(date):
    """'dd/mm' (or 'dd/mm+1': the next calendar year) -> the career calendar's week byte: 8 a month from January of
    the season's first year (cseg_2730A spreads a contest's days between its header weeks; a year = 96)."""
    d, m = date.split('+')[0].split('/')
    y = int(date.split('+')[1]) if '+' in date else 0
    d, m = int(d), int(m)
    return 96 * y + 8 * (m - 1) + (d - 1) * 8 // MONTH_DAYS[m - 1]


def days_before(n, games):
    """cseg_2653B's days: pairs per cycle / (n / 2) x meetings."""
    return n * (n - 1) // 2 // (n // 2) * games


def _round_robin(m):
    """Circle-method rounds of m clubs (local places 0..m-1; a bye for odd m): [[(a, b), ...] per round]."""
    k = m + (m & 1)
    lst = list(range(k))
    out = []
    for r in range(k - 1):
        out.append([(lst[i], lst[k - 1 - i]) for i in range(k // 2) if max(lst[i], lst[k - 1 - i]) < m])
        lst = [lst[0]] + [lst[-1]] + lst[1:-1]
    return out


def _orient(m, rounds):
    """Home / away of a single round robin: every club ceil or floor of its games at home, the extra home games to
    the best placed, no club 3 times running at home or away when avoidable. Returns rounds of (home, away)."""
    games = m - 1
    total = m * games // 2
    lo = games // 2
    extra = total - m * lo
    want = [lo + (1 if p < extra else 0) for p in range(m)]
    flat = [pr for rd in rounds for pr in rd]
    rnd = [r for r, rd in enumerate(rounds) for _ in rd]
    best, nodes = [None], [0]

    def dfs(i, home, last, run, cost, out):
        nodes[0] += 1
        if best[0] is not None and (cost >= best[0][0] or nodes[0] > 300000):   # 11+ clubs: no exhaustive search,
            return                                                               # the best orientation found so far
        if i == len(flat):
            best[0] = (cost, list(out))
            return
        a, b = flat[i]
        left = {p: sum(1 for x in flat[i:] if p in x) for p in (a, b)}
        opts = []
        for h, v in ((a, b), (b, a)):
            if home[h] + 1 > want[h] or (left[v] - 1) < want[v] - home[v]:
                continue
            c = cost
            nl, nr = dict(last), dict(run)
            for t, side in ((h, 1), (v, 0)):
                nr[t] = nr.get(t, 0) + 1 if last.get(t) == side else 1
                nl[t] = side
                if nr[t] >= 3:
                    c += 1
            opts.append((c, sum(nr[t] for t in (h, v)), h, v, nl, nr))
        for c, _, h, v, nl, nr in sorted(opts, key=lambda o: o[:2] if m > 10 else 0):   # 11+: the cheaper side first
            home[h] += 1
            out.append((h, v))
            dfs(i + 1, home, nl, nr, c, out)
            out.pop()
            home[h] -= 1
            if best[0] is not None and best[0][0] == 0:
                return

    dfs(0, [0] * m, {}, {}, 0, [])
    assert best[0] is not None, m
    res, k = [[] for _ in rounds], 0
    for r in rnd:
        res[r].append(best[0][1][k])
        k += 1
    return res


def schedule(groups, rounds):
    """The calendar after the split: [[(home place, away place, group), ...] per day], places 0-based global."""
    days, start = [], 0
    for g, (m, r) in enumerate(zip(groups, rounds)):
        one = _orient(m, _round_robin(m)) if r else []
        back = [[(b, a) for a, b in rd] for rd in one]
        plan = [rd for k in range(r) for rd in (one if k % 2 == 0 else back)]   # r round robins, home / away
        #                                                                         alternating (4: Latvia 1996)
        for d, rd in enumerate(plan):
            while len(days) <= d:
                days.append([])
            days[d] += [(start + a, start + b, g) for a, b in rd]
        start += m
    return days


def phase1_hosts(table, n, games, cycles):
    """{(slot a, slot b): [meetings where a hosted b]} of the engine's fixtures before the split: the pair table
    dseg_11F356[n-2] once per cycle, home / away swapped when the cycles left ([5Fh], from `cycles`) are odd."""
    hosts = {}
    for c in range(games):
        swap = (cycles - c) & 1
        for a, b in table:
            if swap:
                a, b = b, a
            hosts.setdefault((a, b), []).append(c)
    return hosts


def matrix(table, n, games, cycles, home):
    """n x n bytes: [a * n + b] = 1 when slot a is at home against b after the split, 0 when b is, 2 = the
    calendar's own (a balance tie)."""
    h = phase1_hosts(table, n, games, cycles)
    out = bytearray(n * n)
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            ha, hb = h.get((a, b), []), h.get((b, a), [])
            if home == 'balance':
                out[a * n + b] = 1 if len(ha) < len(hb) else 0 if len(ha) > len(hb) else 2
            else:                                   # reverseK: the club away in the K-th meeting hosts
                k = int(home[7:]) - 1
                assert games > k, f'{home} needs {k + 1} meetings before the split'
                out[a * n + b] = 1 if k in hb else 0
    return bytes(out)


HOMES = ('seeded', 'balance', 'reverse1', 'reverse3')
SR = 28                                             # a stage's record (ASM SR_)


CALLBACKS = []          # after-stage routines by name (engine.after_stage; their addresses bound by late())
LATE = []               # (name, obj1 offset of its SP_CB dword) still to bind


def late(p):
    """End of patch_exe: bind the after-stage routines set in engine.CALL_AT after split.patch."""
    import engine
    for name, off, nostage in LATE:
        at = engine.CALL_AT.get(name)
        if at is None:                              # (its owner's code not in this build: a no-op routine)
            print(f'split: after-stage {name}: no routine in this build (engine.CALL_AT): skipped')
            at = (1, nostage)
        p.retarget(1, off, at[0], at[1])
        p.put(1, off, struct.pack('<I', at[1]))
    LATE.clear()


def entry(world, file, div, n, spec, table):
    """One SP_TAB entry (see ASM). spec: games, stages [{after, groups, rounds, points, home, reset, keep}], or a
    fixture stage {after, fixtures: [[(home row, away row), ...] per day], members: [group of each row] (optional),
    reset, then: callback name, table: GP_SS index, annual}; weeks: [week byte per day] (optional, all the days)."""
    games = spec['games']
    stages = spec.get('stages') or []
    assert n <= NMAX and len(stages) <= 8, (n, len(stages))
    d1 = days_before(n, games)
    cycles = games + (1 if stages else 0)
    days, recs = [], []
    for st in stages:
        extra = (st.get('members'), CALLBACKS.index(st['then']) + 1 if st.get('then') else 0,
                 st['table'] + 1 if st.get('table') is not None else 0, int(bool(st.get('annual'))))
        if 'fixtures' in st:                        # a fixture list by rows (Argentina: zones + clasicos)
            mem = st.get('members')
            assert st['after'] - d1 == len(days), f"stage at {st['after']}: day {d1 + len(days)} expected"
            assert mem is None or len(mem) == n, (len(mem), n)
            groups = [mem.count(g) for g in range(max(mem) + 1)] if mem else [n]
            assert len(groups) <= 4 and all(groups), groups
            for d in st['fixtures']:
                assert len({x for pr in d for x in pr}) == 2 * len(d) and all(0 <= x < n for pr in d for x in pr), d
            flags = (1 if st.get('reset') else 0) | 4 | (8 if mem else 0)
            recs.append((len(days), groups, ['full'] * len(groups), flags, b'') + extra)
            days += [[(a, b, 0) for a, b in d] for d in st['fixtures']]
            continue
        groups, rounds = st['groups'], st['rounds']
        points = st.get('points') or ['full'] * len(groups)
        assert len(groups) <= 4 and sum(groups) == n, (n, groups)
        assert st['after'] - d1 == len(days), f"stage at {st['after']}: day {d1 + len(days)} expected"
        assert n <= H2H_NMAX or all(POINTS[x] != 4 for x in points), 'head-to-head points: at most 8 clubs'
        assert not st.get('keep') or 3 * n <= 64, "'keep': at most 21 clubs"
        single = {g for g, r in enumerate(rounds) if r == 1}
        home = st.get('home', 'seeded')
        mat = matrix(table, n, games, cycles, home) if home != 'seeded' and single else b''
        sd = schedule(groups, rounds)
        recs.append((len(days), groups, points, (1 if st.get('reset') else 0) | (2 if st.get('keep') else 0), mat)
                    + extra)
        days += [[(a, b, 1 if mat and g in single else 0) for a, b, g in d] for d in sd]
    assert not any(r[3] & 2 for r in recs) or all(POINTS[x] != 4 for st in stages for x in st.get('points') or []), \
        "'keep' and head-to-head points share their bytes"
    d2 = len(days)
    counts = bytes(len(d) for d in days)
    firsts, pairs, k = b'', b'', 0
    for d in days:
        firsts += struct.pack('<H', k)
        for a, b, f in d:
            pairs += bytes((a, b, f))
            k += 1
    o_counts = 16 + SR * len(recs)
    o_firsts = o_counts + len(counts) + (len(counts) & 1)
    o_pairs = o_firsts + len(firsts)
    o = o_pairs + len(pairs)
    srec, mats = b'', b''
    weeks = bytes(spec['weeks']) if spec.get('weeks') else b''
    assert not weeks or len(weeks) == d1 + d2, (len(weeks), d1 + d2)
    for k, (j0, groups, points, flags, mat, mem, cb, tb, ann) in enumerate(recs):
        g, start = b'', 0
        for i in range(4):
            if i < len(groups):
                g += bytes((start, groups[i], POINTS[points[i]]))
                start += groups[i]
            else:
                g += b'\0\0\0'
        srec += bytes((j0, len(groups), flags, 0)) + g + struct.pack('<HH', o + len(mats) if mat else 0, 0)
        mats += mat
        mo = o + len(mats) if mem else 0
        mats += bytes(mem) if mem else b''
        wo = o + len(mats) if weeks and k == 0 else 0
        mats += weeks if weeks and k == 0 else b''
        srec += struct.pack('<HBBBBH', mo, cb, tb, ann, 0, wo)
    length = o + len(mats)
    length += -length & 3
    head = bytes((world, file, div, n, cycles, d1, d2, len(recs)))
    body = (head + struct.pack('<4H', o_counts, o_firsts, o_pairs, length) + srec + counts
            + b'\0' * (len(counts) & 1) + firsts + pairs + mats)
    assert len(body) <= length and d1 + d2 <= MAXDAYS, (len(body), length, d1, d2)
    return body + b'\0' * (length - len(body)), d1, d2


def pages(splits):
    """obj1 pages for the code + SP_TAB (0 without splits)."""
    if not splits:
        return 0
    size = 0x900                                   # the code (~1.8 KB)
    for world, file, div, n, spec in splits:
        size += len(entry(world, file, div, n, spec, [(a, b) for a in range(n) for b in range(a + 1, n)])[0])
    return (size + 0xFFF) // 0x1000


def sites(p):
    """Sites on the original bytes (obj1 offsets) and variables (obj2)."""
    import lib97
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    diy = lib97._sites(p)[3] + 0x41F
    A = lambda x: re.escape(struct.pack('<I', x))

    def one(pat, what):
        m = [x for x in re.finditer(pat, d1, re.S)]
        assert len(m) == 1, (what, [hex(x.start()) for x in m])
        return m[0]

    def calls_to(t):
        return [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]

    s = {'A0': a0, 'DIY': diy}
    pair = one(rb'\xc7\x05' + A(a0) + A(diy) + rb'\x8b\x35' + A(a0) + rb'\x66\x8b\x46\x5b', 'cseg_89758').start()
    s['pair'] = pair
    s['swap'] = one(rb'\x8b\x35' + A(a0) + rb'\xf6\x46\x5f\x01\x74.\xa1' + A(a0 + 4), 'cseg_89758 swap').start()
    assert 0 < s['swap'] - pair < 0x300
    tab = [x for x in re.finditer(rb'\xc7\x05' + A(a0 + 12), d1[pair:s['swap']])]
    assert len(tab) == 2, 'pairing tables'
    s['table'] = pair + tab[1].start() + 6               # mov [A3], offset dseg_11F356
    s['count'] = one(rb'\x8b\x35' + A(a0 + 4) + rb'\x66\x83\x86\xb7\x02\x00\x00\x01\x8b\x35' + A(a0 + 8)
                     + rb'\x66\x83\x86\xb7\x02\x00\x00\x01\x8b\x35' + A(a0) + rb'\x66\x8b\x86\xbf\x01\x00\x00',
                     'cseg_8922B').start() + 28
    sort = one(rb'\xc7\x05' + A(a0 + 16) + A(diy) + rb'\x8b\x35' + A(a0 + 16) + rb'\x66\x8b\x46\x4f', 'cseg_883DD').start()
    se = [x for x in re.finditer(rb'\x66\xff\x0d' + A(a0 - 4) + rb'\x0f\x89(....)\xc3', d1, re.S) if 0 < x.start() - sort < 0x400]
    assert len(se) == 1, 'cseg_883DD end'
    s['sort'] = se[0].start() + 7
    s['sort_start'] = sort
    s['C88420'] = s['sort'] + 6 + struct.unpack('<i', se[0].group(1))[0]
    # cseg_88CBB: mov [A0], offset DIY; mov esi, [A0]; add word [esi+1BDh], 1 (then the result into the rows)
    # cseg_8EF7B: call cseg_89758; mov esi, [A1]; mov eax, [esi+2B3h]; mov [A0], eax ... mov word [D7], 0;
    # call cseg_88A12; jmp short cseg_8EF7B
    cpu = [x.start() for x in re.finditer(rb'\xe8(....)\x8b\x35' + A(a0 + 4) + rb'\x8b\x86\xb3\x02\x00\x00\xa3' + A(a0),
                                         d1, re.S) if x.start() + 5 + struct.unpack('<i', x.group(1))[0] == pair]
    tails = [(x, re.search(rb'\x66\xc7\x05' + A(a0 - 4) + rb'\x00\x00\xe8(....)\xeb(.)', d1[x:x + 0x80], re.S))
             for x in cpu]
    tails = [(x, m) for x, m in tails if m and x + m.end() + struct.unpack('b', m.group(2))[0] == x]
    assert len(tails) == 1, 'cseg_8EF7B'
    x, m = tails[0]
    s['cpu'], s['C88A12'] = x, x + m.start() + 11 + struct.unpack('<i', m.group(1))[0]
    c = [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == x]
    assert len(c) == 1, 'cseg_8E796'                # (its mov [A0], offset arrayOfPointers: the contests' slot
    k = d1.rfind(b'\xc7\x05' + struct.pack('<I', a0), c[0] - 0x80, c[0])   # buffers, 0 = the league; the harness)
    s['SLOTS'] = p.target(1, k + 6)[1]
    s['res'] = one(rb'\xc7\x05' + A(a0) + A(diy) + rb'\x8b\x35' + A(a0) + rb'\x66\x83\x86\xbd\x01\x00\x00\x01',
                   'cseg_88CBB').start() + 16
    # calendar builder cseg_8B8D9: push [A6]; call cseg_89758 (the return address is on the stack in sp_pair)
    bl = [x for x in calls_to(pair) if d1[x - 6:x] == b'\xff\x35' + struct.pack('<I', a0 + 24)]
    assert len(bl) == 1, 'calendar builder'
    s['BUILDER_RET'] = bl[0] + 5
    m = [x for x in re.finditer(rb'\xc7\x05' + A(a0 + 16) + rb'(.{4})\x66\xa1(.{4})\x66\xa3' + A(a0 - 4), d1, re.S)
         if 0 < bl[0] - x.start() < 0x100]
    assert len(m) == 1, 'calendar'
    s['CAL'], s['CALN'] = (struct.unpack('<I', m[0].group(k))[0] for k in (1, 2))
    m = [x for x in re.finditer(rb'\x8b\x86\xb3\x02\x00\x00\xa3' + A(a0 + 4) + rb'\xa1(.{4})\x01\x05' + A(a0 + 4), d1, re.S)
         if 0 < x.start() - bl[0] < 0x200]
    assert m, 'selTeamsPtr'
    s['SELTEAMS'] = struct.unpack('<I', m[0].group(1))[0]
    # cseg_2653B (call cseg_27227; mov [A2], DIY; mov esi, [A2]; mov ax, [esi+49]) called by cseg_8F1F2's tail:
    # call cseg_2653B; call cseg_28243; retn
    st = [x.start() for x in re.finditer(rb'\xe8.{4}\xc7\x05' + A(a0 + 8) + A(diy) + rb'\x8b\x35' + A(a0 + 8)
                                         + rb'\x66\x8b\x46\x31', d1, re.S)]
    init = [(t, c) for t in st for c in calls_to(t) if d1[c + 5] == 0xE8 and d1[c + 10] == 0xC3]
    assert len(init) == 1, ('cseg_8F1F2 tail', init)
    s['C2653B'], s['init'] = init[0]
    st = [x.start() for x in re.finditer(rb'\x66\xa1' + A(a0 - 32) + rb'\x66\xbb\x06\x00\x66\xf7\xe3', d1, re.S)
          if 0 < s['init'] - x.start() < 0x600]
    assert len(st) == 2 and d1[st[0] + 13:st[0] + 15] == b'\x66\xa3', ('cseg_8F1F2 start', st)   # (the 2nd: +153h)
    s['div'] = st[0]
    k = [x for x in range(s['C2653B'], s['C2653B'] + 0x300) if d1[x] == 0xE8]
    c2730a = [x + 5 + struct.unpack_from('<i', d1, x + 1)[0] for x in k]
    c2730a = [t for t in c2730a if d1[t:t + 10] == b'\xc7\x05' + struct.pack('<I', a0) + struct.pack('<I', diy)]
    assert c2730a, 'cseg_2730A'
    s['C2730A'] = c2730a[0]
    # cseg_8922B's week: mov al, [esi+2Eh]; mov [dseg_E0048], al
    m = [x for x in re.finditer(rb'\x8b\x35' + A(a0) + rb'\x8a\x46\x2e\xa2(.{4})', d1, re.S)
         if 0 < x.start() - s['count'] < 0x100]
    assert len(m) == 1, 'week'
    s['WEEK'] = struct.unpack('<I', m[0].group(1))[0]
    # cseg_3ABB2: mov word [E0052], 1; mov ax, [10E848]; or ax, ax; jnz; mov ax, [10E846]; or ax, ax; jnz
    # (3 simulation routines start so, all with the same flag)
    m = {x.group(1) for x in re.finditer(rb'\x66\xc7\x05(.{4})\x01\x00\x66\xa1.{4}\x66\x0b\xc0\x75\x14\x66\xa1.{4}'
                                         rb'\x66\x0b\xc0\x75\x09', d1, re.S)}
    assert len(m) == 1, 'cseg_3ABB2'
    s['SIMFLAG'] = struct.unpack('<I', m.pop())[0]
    sl = {p.target(1, x.start() + 15) for x in re.finditer(rb'\x66\xc7\x05' + A(a0 - 32) + rb'\xcf\x07\xc7\x05' + A(a0)
                                                            + rb'.{4}\xc7\x05' + A(a0 + 4), d1, re.S)}
    assert len(sl) == 1, ('someLeaguesTable', sl)
    s['SLT'] = sl.pop()
    gt = {p.target(1, x.start() + 14) for x in
          re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d.{4}\x04\x75', d1, re.S)}
    assert len(gt) == 1, ('gameType', gt)
    s['GAMETYPE'] = gt.pop()
    return s


def pair_table(p, s, n):
    """The engine's pairs of an n-club group: dseg_11F356[n - 2] -> [(slot, slot)] x n(n-1)/2."""
    tobj, toff = p.target(1, s['table'])
    eobj, eoff = p.target(tobj, toff + 4 * (n - 2))
    raw = p.get(eobj, eoff, n * (n - 1))               # (as patched: oddtables rewrites the odd sizes)
    return [(raw[2 * i], raw[2 * i + 1]) for i in range(n * (n - 1) // 2)]


def patch(p, cave, nasmcave, splits):
    """splits: [(world, team file, division, clubs, spec)]. Returns the cave end (nothing without splits)."""
    import careerworld
    if not splits:
        return cave
    s = sites(p)
    tab = b''
    log = []
    for world, file, div, n, spec in splits:
        body, d1, d2 = entry(world, file, div, n, spec, pair_table(p, s, n) if n <= 24 else [])
        tab += body
        log.append(f'w{world} f{file} d{div}: {n} clubs, {d1} + {d2} days, '
                   + ' / '.join(str(st.get('groups', 'fixtures')) for st in spec.get('stages') or []))
    tab += b'\0' * 16                          # (end: an entry of length 0)
    src = ASM + ''.join(f'    db {", ".join(str(b) for b in tab[i:i + 32])}\n' for i in range(0, len(tab), 32))
    sym = {'D0': (2, s['A0'] - 32), 'A0': (2, s['A0']), 'A1': (2, s['A0'] + 4), 'A2': (2, s['A0'] + 8), 'A5': (2, s['A0'] + 20),
           'A3': (2, s['A0'] + 12), 'A4': (2, s['A0'] + 16), 'D1': (2, s['A0'] - 28), 'D2': (2, s['A0'] - 24),
           'D7': (2, s['A0'] - 4), 'REGS': (2, s['A0'] - 32), 'DIY': (2, s['DIY']), 'ST_': (0, ST), 'ST_SIZE': (0, ST_SIZE), 'O_GRP': (0, OFF['grp']), 'O_PRE': (0, OFF['pre']), 'O_H2H': (0, OFF['h2h']),
           'MAGIC_': (0, MAGIC), 'NMAX_': (0, NMAX), 'GAMETYPE': s['GAMETYPE'], 'SLT': s['SLT'],
           'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'C2653B': (1, s['C2653B']), 'C2730A': (1, s['C2730A']),
           'C883DD': (1, s['sort_start']), 'C88420': (1, s['C88420']), 'BUILDER_RET': (1, s['BUILDER_RET']),
           'CAL': (2, s['CAL']), 'CALN': (2, s['CALN']), 'SELTEAMS': (2, s['SELTEAMS']), 'WEEK': (2, s['WEEK']),
           'SIMFLAG': (2, s['SIMFLAG']), 'C89758': (1, s['pair']), 'C88A12': (1, s['C88A12'])}
    import engine
    import gplay
    if gplay.LABELS.get('gp_stage'):                # the stage tables (GP_SS): gplay.c, built before us
        sym['GP_STAGE'] = gplay.LABELS['gp_stage']
    else:
        src = src.replace('call GP_STAGE', 'call sp_nostage')
    late = []
    for k, name in enumerate(CALLBACKS):            # after-stage routines (engine.after_stage)
        at = engine.CALL_AT.get(name)
        sym[f'CB{k}'] = at or (1, cave)
        if at is None:
            late.append((name, 4 * k))
    src = src.replace('SP_CB_ENTRIES', 'dd ' + ', '.join(f'CB{k}' for k in range(len(CALLBACKS))) if CALLBACKS else 'dd 0')
    cave = (cave + 3) & ~3
    code, fix = nasmcave.assemble(src, cave, sym)
    lab = nasmcave.labels(src, cave, sym)
    LATE[:] = [(name, lab['SP_CB'] + off, lab['sp_nostage']) for name, off in late]
    assert not any(p.get(1, cave, len(code)))
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    hooks = [(s['div'], 'sp_div8f', 6), (s['init'], 'sp_init', 5), (s['cpu'], 'sp_cpu', 5), (s['swap'], 'sp_pair', 6), (s['count'], 'sp_count', 6), (s['sort'], 'sp_sort', 6)]
    if any(POINTS[x] == 4 for _, _, _, _, sp in splits for x in sp.get('points') or []):
        hooks.append((s['res'], 'sp_res', 8))              # (only with head-to-head groups: the result path)
    for site, label, n in hooks:
        assert p.get(1, site, n) == p.le.obj_bytes(1)[site:site + n], f'split: {label} site already patched'
        if label in ('sp_pair', 'sp_count', 'sp_div8f'):
            p.remove(1, site + 2)                    # mov esi, [A0] / mov ax, [D0] (the others: no address)
        p.put(1, site, b'\xe8' + struct.pack('<i', lab[label] - (site + 5)) + b'\x90' * (n - 5))
    print(f'exe: mid-season splits ({"; ".join(log)}), code obj1+{cave:#x}..{cave + len(code):#x} '
          f'(' + ', '.join(f'{k} {lab[k]:#x}' for k in ('sp_init', 'sp_pair', 'sp_freeze', 'sp_calendar', 'sp_count',
                                                       'sp_sort')) + ')')
    return (cave + len(code) + 3) & ~3
