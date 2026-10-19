"""Copa Libertadores 1996-97 with the real 1997 format (session 27).

21 clubs: 20 in 5 groups of 4 (two countries per group, home and away, real 1997 calendar), the holder (River Plate)
straight into the round of 16. Top 3 of every group + the holder = 16. Two-leg round of 16, quarter-finals,
semi-finals and final on the real fixed bracket; aggregate, no away goals, no extra time, penalties.
Sources: RSSSF "Copa Libertadores 1997" (sacups/copa97), Wikipedia "1997 Copa Libertadores".

Engine (notes/STATUS.md session 27):
- the contest struct's first-stage team count is its total ([0Fh]) -> 21; lib_bye (replaces the `call cseg_2573C` at
  the end of cseg_24DFA, preset and career) sets round 1 [161h] to 20: the groups take the first 20 clubs of the list
  A2+59h (contest order), the 21st (holder) plays no group and its team-table index stays in A2+59h[20].
- lib_pre (called by historic.hist_draw before the fixed permutation of the round of 16): A2+59h[15] (the best 4th,
  picked because 16/5 leaves 1) := A2+59h[20] (holder); the 3rd of group 2 and the 3rd of the holder's country group
  swap places (Davide: the holder always meets the 3rd of its own group, as in 1996 and 1997).
- lib_cal (replaces `mov esi, [A0]` at @@european_championships in cseg_89758): our 4-team groups take their matches
  from LIB_CAL (per group 12 (home, away) slot pairs: first cycle as played, second cycle stored reversed because the
  engine swaps home and away when [5Fh] (cycles left) is odd) instead of the game's 4-team table.
Both run only for contest id LIB_ID with 21 clubs (diyFileBufferCopy [31h]): an old 1.3 contest in a saved career keeps
the old behaviour until its season ends.
"""
import re
import struct

import nasmcave
import sacups

LIB_GROUPS = sacups.LIB_GROUPS     # clubs in the group stage; the 21st (last of sacups.LIBERTADORES) is the holder

# group slots = sacups.LIBERTADORES order: (country A champion, country B champion, A runner-up, B runner-up)
GROUPS = [['Bolivar', 'Guarani', 'Oriente', 'Cerro'],
          ['Velez', 'ElNacional', 'Racing', 'Emelec'],
          ['ColoColo', 'Minerven', 'UCatolica', 'Mineros'],
          ['Gremio', 'SCristal', 'Cruzeiro', 'Alianza'],
          ['Penarol', 'Millonarios', 'Nacional', 'Cali']]
# real 1997 matchdays (home-away). Each day = two matches covering the group; days ordered by their first match date
# (RSSSF). Groups 1-4: days 4-6 mirror days 1-3 as played; group 5 (an irregular calendar) gets the closest fit.
CALENDAR = [
    ['Guarani-Cerro Oriente-Bolivar', 'Oriente-Guarani Bolivar-Cerro', 'Bolivar-Guarani Oriente-Cerro',
     'Cerro-Guarani Bolivar-Oriente', 'Guarani-Oriente Cerro-Bolivar', 'Cerro-Oriente Guarani-Bolivar'],
    ['Emelec-ElNacional Racing-Velez', 'ElNacional-Velez Emelec-Racing', 'ElNacional-Racing Emelec-Velez',
     'ElNacional-Emelec Velez-Racing', 'Velez-ElNacional Racing-Emelec', 'Racing-ElNacional Velez-Emelec'],
    ['Mineros-Minerven UCatolica-ColoColo', 'UCatolica-Mineros ColoColo-Minerven', 'ColoColo-Mineros UCatolica-Minerven',
     'ColoColo-UCatolica Minerven-Mineros', 'Mineros-UCatolica Minerven-ColoColo', 'Minerven-UCatolica Mineros-ColoColo'],
    ['Cruzeiro-Gremio SCristal-Alianza', 'Alianza-Cruzeiro SCristal-Gremio', 'SCristal-Cruzeiro Alianza-Gremio',
     'Gremio-Cruzeiro Alianza-SCristal', 'Cruzeiro-Alianza Gremio-SCristal', 'Gremio-Alianza Cruzeiro-SCristal'],
    ['Cali-Millonarios Nacional-Penarol', 'Nacional-Millonarios Cali-Penarol', 'Penarol-Millonarios Cali-Nacional',
     'Millonarios-Penarol Nacional-Cali', 'Penarol-Nacional Millonarios-Cali', 'Millonarios-Nacional Penarol-Cali'],
]

# Knockout (hist_draw permutations, new[k] = old[perm[k]]; consecutive pairs, first club = first leg at home).
# Round of 16 input: 1st of groups 1-5 (0-4), 2nd (5-9), 3rd (10-14), holder (15). Real 1997 ties, bracket order:
# Racing 3G2 - River H | Millonarios 2G5 - Penarol 1G5 | S.Cristal 3G4 - Velez 1G2 | Minerven 3G3 - Bolivar 1G1 |
# El Nacional 2G2 - Cruzeiro 2G4 | Guarani 3G1 - Gremio 1G4 | Nacional 3G5 - Colo Colo 1G3 | U.Catolica 2G3 - Oriente 2G1
R16 = [11, 15, 9, 4, 13, 1, 12, 0, 6, 8, 10, 3, 14, 2, 7, 5]
QF = [1, 0, 3, 2, 4, 5, 7, 6]       # Penarol-Racing, Bolivar-S.Cristal, Cruzeiro-Gremio, U.Catolica-Colo Colo
SF = [0, 1, 2, 3]                   # Racing-S.Cristal, Cruzeiro-Colo Colo
FINAL = [0, 1]                      # S.Cristal-Cruzeiro
DRAWS = [(sacups.LIB_ID, R16), (sacups.LIB_ID, QF), (sacups.LIB_ID, SF), (sacups.LIB_ID, FINAL)]


def calendar_bytes():
    out = bytearray()
    for g, (names, days) in enumerate(zip(GROUPS, CALENDAR)):
        slot = {n: k for k, n in enumerate(names)}
        pairs = [tuple(slot[t] for t in m.split('-')) for day in days for m in day.split()]
        assert len(pairs) == 12 and len(set(pairs)) == 12
        for d in range(6):
            assert sorted(pairs[2 * d] + pairs[2 * d + 1]) == [0, 1, 2, 3], (g, d)
        first, second = pairs[:6], pairs[6:]
        assert {frozenset(p) for p in first} == {frozenset(p) for p in second} and len({frozenset(p) for p in first}) == 6
        assert {(b, a) for a, b in first} == set(second), g          # second cycle = return matches
        for h, a in first:
            out += bytes((h, a))
        for h, a in second:
            out += bytes((a, h))                                      # the engine swaps them back
    return bytes(out)


ASM = '''
lib_bye:                                ; replaces `call cseg_2573C` at the end of cseg_24DFA
    pushad
    mov al, [DIYCOPY + 2Dh]             ; a cup with first-round byes (BYE_TAB: season / world packs with byes in
    mov cx, [DIYCOPY + 161h]            ; ties.csv, FA Cup 1871-72): round 1 = its clubs but the b last ones
    call bye_find
    jc .nb
    movzx eax, byte [esi + 3]
    sub [DIYCOPY + 161h], ax
.nb:
    popad
    cmp byte [DIYCOPY + 2Dh], LIB_ID
    jne .go
    cmp word [DIYCOPY + 161h], LIB_N    ; round 1 = every club of the contest...
    jne .go
    mov word [DIYCOPY + 161h], LIB_GROUPS   ; ... but the holder plays no group
.go:
    jmp CSEG_2573C

nc_bye:                                 ; replaces `mov esi, [A5]` before the round-1 draw of a national cup (obj1
    pushad                              ; 0x77BF4, contest type 1: careers and seasons; not cseg_24DFA): with byes,
    mov al, [NCW + 2Dh]                 ; round 1 = (N - b) / 2 matches between the first N - b clubs (the draw
    mov cx, [NCW + 31h]                 ; cseg_27F84 shuffles only those); the b others wait in the list for lib_pre
    call bye_find
    jc .x
    movzx eax, byte [esi + 2]
    movzx ebx, byte [esi + 3]
    sub eax, ebx
    shr eax, 1
    mov [NCW + 4Fh], ax                 ; round 1's matches ([4Fh], [51h], as obj1 0x16711 sets N / 2)
    mov [NCW + 51h], ax
    add eax, ebx                        ; round 2's clubs: rounds = 1 + log2 of it rounded up ([59h]; a power of 2
    dec eax                             ; as the game's cups, else a later bracket of the hook's: dplay's Serie C)
    mov ecx, 1
.r:
    inc ecx
    shr eax, 1
    jnz .r
    cmp byte [esi + 1], 0FFh            ; (a hook's entry, gplay's contest: its rounds at +4)
    jne .rn
    movzx ecx, byte [esi + 4]
.rn:
    mov [NCW + 59h], cx
    mov esi, [A5]                       ; the rounds' legs / extra time / penalties words from the header's round
    xor edx, edx                        ; bytes (+0Eh) for all of them: the game decodes as many as its halving of
.rb:                                    ; the clubs gives (6 clubs: 2 of 3)
    mov al, [esi + 0Eh + edx]
    test al, al
    jz .rbx
    movzx ebx, al
    shr ebx, 6
    mov [NCW + 65h + edx * 2], bx
    movzx ebx, al
    shr ebx, 4
    and ebx, 3
    mov [NCW + 71h + edx * 2], bx
    movzx ebx, al
    shr ebx, 2
    and ebx, 3
    mov [NCW + 7Dh + edx * 2], bx
    inc edx
    cmp edx, ecx
    jb .rb
.rbx:
    mov ecx, 12                         ; the cup's dates ([333h], the table +337h) again for those rounds
    mov esi, PREG                       ; (cseg_2740F, which uses the game's D0..A3: kept)
.p:
    push dword [esi]
    add esi, 4
    loop .p
    call C1740F
    mov ecx, 12
    mov esi, PREG + 44
.q:
    pop dword [esi]
    sub esi, 4
    loop .q
.x:
%if FD_ON
    call nc_first                       ; a world's fixed round 1 (its draw table has the round: the contest order =
    sbb bl, bl                          ; ties.csv's) in the career's first season: header byte 8 = 1 = no draw;
    not bl                              ; 0 = the game's random draw (every later season)
    and bl, 1
    mov al, [NCW + 2Dh]
    movzx ecx, word [NCW + 4Fh]
    shl ecx, 1                          ; (round 1's clubs: 2 x its matches, byes left out)
    mov ah, 0
    call dt_find
    jc .y
    mov esi, [A5]
    mov [esi + 8], bl
.y:
%endif
    popad
    mov esi, [A5]
    ret

%if FD_ON
nc_first:                               ; CF = 0: a world career in its first season
    push eax
    push ebx
    call [NC_WREC]                      ; (careerworld.w_rec, set by chain_adv)
    jz .no
    mov al, [ebx + 42]
    cmp al, [SEASONPLAYING]
    jne .no
    pop ebx
    pop eax
    clc
    ret
.no:
    pop ebx
    pop eax
    stc
    ret

dt_find:                                ; al = contest id, ecx = clubs of the round, ah = the round (0 = round 1)
    push ebx                            ; -> CF = 0, edx = its fixed permutation (historic's draw table: a cup's
    mov [NC_RD], ah                     ; rounds in order, world filter records [1, 0, w])
    mov edx, [NC_DTAB]
    mov byte [NC_DW], 0
.f:
    cmp byte [edx], 0
    je .no
    cmp byte [NC_WDON], 0
    je .rec
    cmp byte [edx], 1
    jne .rec
    mov bl, [edx + 2]
    mov [NC_DW], bl
    add edx, 3
    jmp .f
.rec:
    movzx ebx, byte [edx + 1]
    and bl, 7Fh
    cmp [edx], al
    jne .n
    cmp byte [NC_DW], 0
    je .w
    push eax
    mov al, [NC_DW]
    cmp al, [WORLDB]
    pop eax
    jne .n
.w:
    cmp byte [NC_RD], 0                 ; this cup's k-th entry = its round k
    je .k
    dec byte [NC_RD]
    jmp .n
.k:
    cmp ebx, ecx
    jne .no
    add edx, 2
    pop ebx
    clc
    ret
.n:
    lea edx, [edx + ebx + 2]
    jmp .f
.no:
    pop ebx
    stc
    ret
%endif

nc_adv:                                 ; replaces `call 0x194A4` in the knockout round advance (obj1 0x18376; it
    call nc_adv_call                    ; compacts the round's w winners to the list +2CDh in tie order and draws
    pushad                              ; them: list[k] = winners[perm[k]], perm at +30Dh); then:
    mov al, [NCW + 2Dh]                 ; - a cup with byes leaving round 1: its b clubs (list[N - b ..], untouched)
    mov cx, [NCW + 31h]                 ;   join the w winners; [4Fh] = w + b (the advance halves it);
    xor ebx, ebx                        ; - a world's fixed draw for the round (first season): the winners back in
    cmp word [NCW + 57h], 0             ;   tie order (+ the byes) through that permutation; else (byes) the
    jne .nb                             ;   game's draw cseg_27F84 over the w + b
    call bye_find
    jc .nb
    movzx ebx, byte [esi + 3]           ; b
    movzx eax, byte [esi + 2]
    sub eax, ebx
    shr eax, 1
    cmp [NCW + 4Fh], ax
    je .nb
    xor ebx, ebx                        ; (not round 1's w: no byes)
.nb:
    mov [NC_B], ebx
    movzx edx, word [NCW + 4Fh]         ; w
    mov [NC_W], edx
    xor ecx, ecx                        ; tie-order winners: T[perm[k]] = list[k]
.t:
    cmp ecx, edx
    jae .tb
    movzx eax, byte [NCW + 30Dh + ecx]
    mov bl, [NCW + 2CDh + ecx]
    mov [NC_T + eax], bl
    inc ecx
    jmp .t
.tb:
    mov ebx, [NC_B]                     ; + the byes: T[w ..] = list[N - b ..]
    movzx eax, word [NCW + 31h]
    sub eax, ebx
    xor ecx, ecx
.tc:
    cmp ecx, ebx
    jae .fx
    mov dl, [NCW + 2CDh + eax + ecx]
    mov esi, [NC_W]
    add esi, ecx
    mov [NC_T + esi], dl
    inc ecx
    jmp .tc
.fx:
    mov ecx, [NC_W]
    add ecx, [NC_B]                     ; the next round's clubs
    cmp dword [NC_DPP], 0               ; dplay's play-off: its own bracket (dplay.dp_perm)
    je .ndp
    call [NC_DPP]
    jnc .set
.ndp:
%if FD_ON
    call nc_first
    jc .rnd
    mov al, [NCW + 2Dh]
    mov ah, [NCW + 57h]                 ; (the round just played: the next one's index = + 1)
    inc ah
    call dt_find
    jc .rnd
    xor eax, eax                        ; list[k] = T[fixed[k]]
.fk:
    movzx ebx, byte [edx + eax]
    mov bl, [NC_T + ebx]
    mov [NCW + 2CDh + eax], bl
    inc eax
    cmp eax, ecx
    jb .fk
    jmp .set
.rnd:
%endif
    cmp dword [NC_B], 0
    je .x
    xor eax, eax                        ; byes, no fixed draw: T (winners + byes) drawn by the game
.ck:
    mov bl, [NC_T + eax]
    mov [NCW + 2CDh + eax], bl
    inc eax
    cmp eax, ecx
    jb .ck
    push ecx
    shr ecx, 1
    mov [NCW + 4Fh], cx                 ; (cseg_27F84 shuffles 2 x [4Fh] entries)
    mov ecx, 12
    mov esi, PREG
.p:
    push dword [esi]
    add esi, 4
    loop .p
    call C27F84
    mov ecx, 12
    mov esi, PREG + 44
.q:
    pop dword [esi]
    sub esi, 4
    loop .q
    pop ecx
.set:
    mov [NCW + 4Fh], cx                 ; w + b (the advance halves it)
.x:
    popad
    ret
st_ko:                                  ; replaces `call 0x16711` (the round's ties from its clubs) at the end of a
    call C16711                         ; type-2 contest's knockout-stage start (cseg_2572F; DIY = NCW, its id still
    cmp dword [ST_REC], 0               ; (statespec.st_rec: the state's final group-stage order, EN item 'SR')
    je .nr
    call [ST_REC]
.nr:
%if ST_NB                               ; FFh: the copy's; the stage's clubs in the copy's +59h order): a state's
    pushad                              ; fixed draw (ST_TAB: id, first club word, N, b, g, size, code[N]).
    mov ebx, ST_TAB                     ; g > 0: the copy's list comes in bands of g (the 1sts, the 2nds ...: merit
    mov edx, ST_NB                      ; order inside a band); code = band * g + group: list[k] = the club of that
.st:                                    ; band whose team index / size = group (groups = team-list blocks of size);
    mov al, [DIYCOPY + 2Dh]             ; b > 0: the b last wait, the N - b first play (N - b) / 2 ties (the list
    cmp [ebx], al                       ; kept in SB). g = 0: the stage after it, b = its ties k: code < k = the
    jne .stn                            ; winner of that tie, else a bye (the game's list there: winners, losers,
    mov ax, [DIYCOPY + 99h]             ; byes). (States share one id: told apart by their first club.)
    cmp [ebx + 1], ax
    jne .stn
    movzx ecx, byte [ebx + 3]
    cmp [NCW + 31h], cx
    je .sth
.stn:
    movzx ecx, byte [ebx + 3]
    lea ebx, [ebx + ecx + 7]
    dec edx
    jnz .st
.sx:
    popad
%endif
    ret
%if ST_NB
.sth:
    cmp byte [ebx + 5], 0               ; g = 0: the stage after one with byes ('pairs')
    je .pairs
    xor edi, edi                        ; k
.sk:
    movzx eax, byte [ebx + 7 + edi]     ; code -> band (al), group (ah)
    div byte [ebx + 5]
    mov dh, ah
    mul byte [ebx + 5]                  ; band * g: the band's first position
    mov esi, eax
    movzx ebp, byte [ebx + 5]           ; g candidates
.sj:
    movzx eax, byte [DIYCOPY + 59h + esi]
    div byte [ebx + 6]                  ; team index / size = its group
    cmp al, dh
    je .sf
    inc esi
    dec ebp
    jnz .sj
    jmp .sx                             ; (not found: the game's order - never in a built table)
.sf:
    mov al, [DIYCOPY + 59h + esi]
    mov [NC_T + edi], al
    inc edi
    cmp edi, ecx
    jb .sk
    call .put
    movzx edx, byte [ebx + 4]
    test edx, edx
    jz .sx
    sub ecx, edx
    shr ecx, 1
    mov [NCW + 4Fh], cx
    mov [NCW + 51h], cx
    jmp .sx
.pairs:                                 ; [ebx + 4] = the stage before's ties k, [ebx + 6] its clubs N'; code c < k:
    xor edi, edi                        ; the winner of tie c, else
.pk:                                    ; bye c - k
    movzx eax, byte [ebx + 7 + edi]
    movzx edx, byte [ebx + 4]
    cmp eax, edx
    jae .pb
    mov al, [ST_SB + 16 + eax]          ; the winner of tie c (st_kend, at the stage before's end)
    jmp .pf
.pb:
    add eax, edx                        ; bye c - k at SB[2k + c - k]: the byes follow the 2k clubs of the ties
    mov al, [ST_SB + eax]
.pf:
    mov [NC_T + edi], al
    inc edi
    cmp edi, ecx
    jb .pk
    call .put
    jmp .sx
.put:                                   ; NC_T[0..ecx) -> the round's list, and kept with the career (EN item
    xor eax, eax                        ; 'SB'): the next stage finds its winners by their ties, the byes by their
.pu:                                    ; places
    mov dl, [NC_T + eax]
    mov [NCW + 2CDh + eax], dl
    mov [ST_SB + eax], dl
    inc eax
    cmp eax, ecx
    jb .pu
    ret
%endif

st_kend:                                ; replaces `call 0x7A613` (a stage's end, not a group stage: the round's
%if ST_NB                               ; winners first into the copy's +59h, unless [163h] = 1 and [57h] says
    pushad                              ; otherwise): a state contest with fixed draws -> SB[16 + k] = the winner of
    mov ebx, ST_TAB                     ; tie k, from the round's list and its result bits (DIY+89h + k, bit 0:
    mov edx, ST_NB                      ; the second club won; as 0x1AAF9 reads them)
.k:
    mov al, [DIYCOPY + 2Dh]
    cmp [ebx], al
    jne .n
    mov ax, [DIYCOPY + 99h]
    cmp [ebx + 1], ax
    je .w
.n:
    movzx ecx, byte [ebx + 3]
    lea ebx, [ebx + ecx + 7]
    dec edx
    jnz .k
    jmp .x
.w:
    movzx ecx, word [NCW + 4Fh]
    cmp ecx, 8
    ja .x
    xor ebx, ebx
.t:
    test ecx, ecx
    jz .x
    movzx eax, byte [NCW + 89h + ebx]
    and eax, 1
    lea eax, [eax + ebx * 2]
    mov al, [NCW + 2CDh + eax]          ; tie k's winner -> SB[16 + c], c = its tie in SB (the list may have
    xor edx, edx                        ; changed order since: second legs swap the clubs)
.c:
    cmp al, [ST_SB + edx * 2]
    je .f
    cmp al, [ST_SB + edx * 2 + 1]
    je .f
    inc edx
    cmp edx, 8
    jb .c
    jmp .nx
.f:
    mov [ST_SB + 16 + edx], al
.nx:
    inc ebx
    dec ecx
    jmp .t
.x:
    popad
%endif
    jmp C7A613

nc_adv_call:
    jmp C194A4                          ; (chain_adv: the call's target after careerworld.euro_draw hooked it)

bye_find:                               ; al = contest id, cx = its clubs -> CF = 0, esi = its BYE_TAB entry
    cmp dword [NC_BYEP], 0              ; (gplay.gp_bye first: a running play-off of its own)
    je .tab
    call [NC_BYEP]
    jnc .r
.tab:
    mov esi, BYE_TAB                    ; (id, world, clubs, byes); world 0 = any (one-world builds: ids unique)
    mov edx, BYE_NT
.l:
    test edx, edx
    jz .no
    cmp [esi], al
    jne .n
    test ch, ch
    jnz .n
    cmp [esi + 2], cl
    jne .n
%if BW_ON
    cmp byte [esi + 1], 0
    je .ok
    push eax
    mov al, [WORLDB]                    ; the running career's world (several worlds: cup ids per world)
    cmp [esi + 1], al
    pop eax
    jne .n
%endif
.ok:
    clc
.r:
    ret
.n:
    add esi, 4
    dec edx
    jmp .l
.no:
    stc
    ret

lib_pre:                                ; hist_draw, before the permutation: esi = DIY buffer, ecx = clubs in the round
    call FIN_PRE                        ; 2.1: NSL / NSSL finals series (finals97.fin_pre)
    pushad                              ; a cup with byes, round 2 (its (N - b) / 2 winners + b): the b clubs left
    mov ebp, esi                        ; out of round 1 (list[N - b ..], untouched) follow the winners (the fixed
    mov edi, ecx                        ; draw then puts them in their bracket slots)
    mov al, [ebp + 2Dh]
    mov cx, [ebp + 31h]
    call bye_find
    jc .nb
    movzx ebx, byte [esi + 3]
    movzx eax, byte [esi + 2]
    sub eax, ebx                        ; N - b: the first one left out
    mov edx, eax
    shr edx, 1                          ; the winners
    lea ecx, [edx + ebx]
    cmp ecx, edi
    jne .nb
.c:
    mov cl, [ebp + 59h + eax]           ; (target < source: an ascending copy is safe)
    mov [ebp + 59h + edx], cl
    inc eax
    inc edx
    dec ebx
    jnz .c
.nb:
    popad
.lib:
    cmp byte [esi + 2Dh], LIB_ID
    jne .r
    cmp ecx, 16
    jne .r
    cmp word [esi + 31h], LIB_N
    jne .r
    pushad
    lea edi, [esi + 59h]
    movzx ebx, byte [edi + LIB_GROUPS]  ; holder's team-table index (no group)
    mov [edi + 15], bl                  ; in place of the best 4th
    mov al, [esi + 99h + ebx*2]         ; its country (team word = country, ordinal)
    movzx ecx, word [esi + 31h]
    xor edx, edx
.f:
    cmp edx, ebx
    je .n
    cmp [esi + 99h + edx*2], al
    je .g
.n:
    inc edx
    cmp edx, ecx
    jb .f
    jmp .done
.g:
    movzx edx, byte [esi + 119h + edx]  ; group of a club of the same country (0-based)
    cmp edx, 5
    jae .done
    mov al, [edi + 11]                  ; 3rd of group 2 <-> 3rd of the holder's group
    xchg al, [edi + 10 + edx]
    mov [edi + 11], al
.done:
    popad
.r:
    ret

lib_cal:                                ; replaces `mov esi, [A0]` in cseg_89758 (A3 = 4-team table)
    mov esi, [A0]
    cmp byte [esi + 2Dh], LIB_ID
    jne .r
    cmp word [esi + 51h], 4
    jne .r
    cmp word [DIYCOPY + 31h], LIB_N
    jne .r
    movzx eax, word [esi + 5Bh]         ; group
    cmp eax, 5
    jae .r
    imul eax, eax, 24
    test byte [esi + 5Fh], 1            ; second cycle: return matches
    jz .a
    add eax, 12
.a:
    add eax, LIB_CAL
    mov [A3], eax
.r:
    ret

LIB_CAL: CAL_BYTES
BYE_TAB: BYE_BYTES
%if ST_NB
ST_TAB: ST_BYTES
%endif
NC_B: dd 0
NC_W: dd 0
NC_T: times 64 db 0
NC_DTAB: dd 0                           ; (chain_adv: historic's draw table)
NC_DPP: dd 0                            ; (dplay.dp_perm, or 0)
NC_BYEP: dd 0                           ; (gplay.gp_bye, or 0)
NC_WREC: dd 0                           ; (chain_adv: careerworld.w_rec)
NC_WDON: db 0
ST_SB: times 32 db 0                    ; (EN item 'SB': st_ko's last fixed round [0..16), st_kend's winners [16..24))
ST_REC: dd 0                            ; (statespec.st_rec, or 0)
NC_DW: db 0
NC_RD: db 0
'''


def _sites(p):
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['D7'] + 4
    # end of cseg_24DFA: mov [esi+161h], ax; call cseg_2573C; call cseg_258E4; retn; int 3; jmp $
    m = [x for x in re.finditer(rb'\x66\x89\x86\x61\x01\x00\x00\xe8(.{4})\xe8.{4}\xc3\xcc\xeb\xfe', d1, re.S)]
    assert len(m) == 1, len(m)
    bye_call = m[0].start() + 7
    c2573c = bye_call + 5 + struct.unpack('<i', m[0].group(1))[0]
    # cseg_2573C: mov byte/word [...], 1; call nullsub; ... mov [A0], offset diyFileBufferCopy
    k = d1.find(b'\xc7\x05' + struct.pack('<I', a0), c2573c)
    assert 0 < k - c2573c < 0x60, hex(k - c2573c)
    diycopy = struct.unpack_from('<I', d1, k + 6)[0]
    # cseg_89758 @@european_championships: mov esi,[A0]; mov ax,[esi+1CBh]; mov [D0],ax; shl [D0],1
    m = [x.start() for x in re.finditer(re.escape(b'\x8b\x35' + struct.pack('<I', a0) + b'\x66\x8b\x86\xcb\x01\x00\x00'), d1)]
    m = [x for x in m if d1[x + 13:x + 15] == b'\x66\xa3']
    assert len(m) == 1, [hex(x) for x in m]
    # national cup set-up (obj1 0x77BF4, type 1), its end: mov esi, [A5]; mov al, [esi+8]; or al, al; jnz +5;
    # call cseg_27F84 (round-1 draw); ret
    a5 = struct.pack('<I', r['A0'] + 20)
    m2 = [x for x in re.finditer(rb'\x8b\x35' + re.escape(a5) + rb'\x8a\x46\x08\x0a\xc0\x75\x05\xe8(.{4})\xc3', d1, re.S)]
    assert len(m2) == 1, [hex(x.start()) for x in m2]
    c27f84 = m2[0].end() - 1 + struct.unpack('<i', m2[0].group(1))[0]
    m2 = [m2[0].start()]
    # knockout round advance (obj1 0x18376): mov ax, [esi+32Dh]; or ax, ax; jnz ...; call 0x194A4 (round 1's winners
    # -> the next round's draw)
    m3 = [x for x in re.finditer(rb'\x66\x8b\x86\x2d\x03\x00\x00\x66\x0b\xc0\x0f\x85.{4}\xe8(.{4})', d1, re.S)]
    assert len(m3) == 1, [hex(x.start()) for x in m3]
    c194a4 = m3[0].end() + struct.unpack('<i', m3[0].group(1))[0]
    m3 = [m3[0].end() - 5]
    # the cup's dates (obj1 0x1740F, called once from the round set-up 0x16711): mov [A0], NCW; mov eax, [A0];
    # add eax, 65h; mov [A1], eax; mov eax, [A0]; add eax, 7Dh
    pk = lambda x: re.escape(struct.pack('<I', x))
    m4 = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(a0) + pk(diycopy + 0x41F) + rb'\xa1' + pk(a0) +
                                         rb'\x83\xc0\x65\xa3' + pk(a0 + 4) + rb'\xa1' + pk(a0) + rb'\x83\xc0\x7d', d1)]
    assert len(m4) == 1, [hex(x) for x in m4]
    return a0, bye_call, c2573c, diycopy, m[0], m2[0], m3[0], c194a4, m4[0], c27f84


LABELS = {}


def _kend_sites(p):
    """The two calls of a stage's end for a contest stage that is not a group stage (0x7A613: the game's two
    callers next to cseg_8A2CE's, both after `mov ax, [esi+15Dh]; or ax, ax; jz`)."""
    import lp36
    d = p.le.obj_bytes(1)
    c8a2ce = lp36._sites(p)['C8A2CE']
    out, tgt = [], set()
    for g in lp36._sites(p)['gend']:
        j = d.find(b'\xe8', g + 5, g + 0x60)
        while j > 0:
            t = j + 5 + struct.unpack_from('<i', d, j + 1)[0]
            if t != c8a2ce and 0x70000 < t < 0x90000:
                out.append(j)
                tgt.add(t)
                break
            j = d.find(b'\xe8', j + 1, g + 0x60)
    assert len(out) == 2 and len(tgt) == 1, ([hex(x) for x in out], [hex(x) for x in tgt])
    return out, tgt.pop()


def _st_site(p):
    """The `call 0x16711` (a round's ties from its clubs) of cseg_2572F's knockout-stage start (obj1 0x15D64): after
    `mov al, [esi+175h]; mov esi, [x]; mov [esi+37h], al` and five pushes."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x8a\x86\x75\x01\x00\x00\x8b\x35.{4}\x88\x46\x37(?:\xff\x35.{4}){5}\xe8',
                                       d, re.S)]
    assert len(m) == 2 and m[1] - m[0] < 0x400, [hex(x) for x in m]   # (the group-stage start, then the knockout's)
    return m[1] + 6 + 6 + 3 + 30


def chain_adv(p):
    """After careerworld.euro_draw (it hooks the same `call 0x194A4`): the round advance calls nc_adv (byes),
    which then jumps to whatever that call reached."""
    site, j = LABELS['adv_site'], LABELS['nc_adv_call']
    t = site + 5 + struct.unpack('<i', p.get(1, site + 1, 4))[0]
    p.put(1, j + 1, struct.pack('<i', t - (j + 5)))
    p.put(1, site + 1, struct.pack('<i', LABELS['nc_adv'] - (site + 5)))   # (relative call and jmp: no fixups)
    import historic
    tobj, toff = historic.TABLE[0]                    # the fixed draws (nc_bye / nc_adv, a world's first season)
    p.add_ptr(1, LABELS['NC_DTAB'], tobj, toff)
    p.put(1, LABELS['NC_WDON'], bytes((int(historic.TABLE[1]),)))
    if LABELS['fd']:
        import careerworld
        p.add_ptr(1, LABELS['NC_WREC'], 1, careerworld.LABELS['w_rec'])


def patch(p, cave, fin_pre):
    import mkseason
    import dplay
    bc = [(0xC3, 0, 15, 1)] + mkseason.bye_cups()           # historic.FA_ID: FA Cup 1871-72 (15 clubs, 1 bye)
    if mkseason.worlds():
        bc += dplay.bye_cups(mkseason.dplay_tables())        # the Serie B play-off (the 3rd and 4th wait)
    st = mkseason.state_draws()                             # [(id, world, N, b, first club word, perm)]
    if st:
        import engine
        engine.save_item('SB', 32)
    assert all(0 < b and n <= 255 and (n - b) % 2 == 0 for _, _, n, b in bc), bc
    bw = mkseason.multi_ns() and any(w for _, w, _, _ in bc)  # several worlds: a world's cup ids are its own
    fd = bool(mkseason.worlds())                             # career worlds: their cups' fixed draws (first season)
    if bw or fd:
        import careerworld
        cws = careerworld.sites(p)                           # (careerworld.patch runs after: its patterns intact)
        slt = cws['slt']
    """Returns (cave end, lib_pre offset) — lib_pre is called by historic.hist_draw."""
    a0, bye_call, c2573c, diycopy, cal_site, nc_site, adv_site, c194a4, c1740f, c27f84 = _sites(p)
    stc = _st_site(p)
    c16711 = stc + 5 + struct.unpack('<i', p.get(1, stc + 1, 4))[0]
    kend, _ = _kend_sites(p)
    cur = {k + 5 + struct.unpack('<i', p.get(1, k + 1, 4))[0] for k in kend}   # (chained: whatever they reach now)
    assert len(cur) == 1, [hex(x) for x in cur]
    c7a613 = cur.pop()
    symbols = {'DIYCOPY': (2, diycopy), 'LIB_ID': (0, sacups.LIB_ID), 'LIB_N': (0, sacups.LIB_N),
               'LIB_GROUPS': (0, LIB_GROUPS), 'CSEG_2573C': (1, c2573c), 'A0': (2, a0), 'A3': (2, a0 + 12),
               'BYE_NT': (0, len(bc)), 'BYE_BYTES': (0, 'db ' + ', '.join(str(x) for e in bc for x in e)),
               'A5': (2, a0 + 20), 'NCW': (2, diycopy + 0x41F),     # the contest work buffer (DIY layout)
               'C16711': (1, c16711), 'C7A613': (1, c7a613),
               'C194A4': (1, c194a4), 'C1740F': (1, c1740f), 'PREG': (2, a0 - 32), 'C27F84': (1, c27f84),
               'BW_ON': (0, int(bw)), 'WORLDB': (slt[0], slt[1] + careerworld.WORLD_BYTE) if bw or fd else (0, 0),
               'FD_ON': (0, int(fd)), 'SEASONPLAYING': (2, cws['season']) if fd else (0, 0),
               'FIN_PRE': (1, fin_pre),
               'ST_NB': (0, len(st)), 'ST_BYTES': (0, 'db ' + ', '.join(
                   str(x) for i, _, n, b, f, g, sz, pm in st for x in (i, f & 255, f >> 8, n, b, g, sz, *pm))
                   if st else 'db 0'),
               'CAL_BYTES': (0, 'db ' + ', '.join(str(b) for b in calendar_bytes()))}
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    labels = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.put(1, bye_call + 1, struct.pack('<i', labels['lib_bye'] - (bye_call + 5)))
    LABELS.update(nc_adv=labels['nc_adv'], nc_adv_call=labels['nc_adv_call'], adv_site=adv_site,   # (chain_adv)
                  NC_DTAB=labels['NC_DTAB'], NC_WDON=labels['NC_WDON'], NC_WREC=labels['NC_WREC'], fd=fd,
                  NC_T=labels['NC_T'], NC_DPP=labels['NC_DPP'], NC_BYEP=labels['NC_BYEP'], ST_SB=labels['ST_SB'],
                  ST_REC=labels['ST_REC'])
    if st:
        import engine
        engine.ITEM_AT['SB'] = (1, labels['ST_SB'])
    p.put(1, stc + 1, struct.pack('<i', labels['st_ko'] - (stc + 5)))   # (relative call: no fixup)
    if st:
        for k in kend:
            p.put(1, k + 1, struct.pack('<i', labels['st_kend'] - (k + 5)))
    p.remove(1, nc_site + 2)                                      # mov esi, [A5] (6 B) -> call nc_bye; nop
    p.put(1, nc_site, b'\xe8' + struct.pack('<i', labels['nc_bye'] - (nc_site + 5)) + b'\x90')
    p.remove(1, cal_site + 2)                                     # mov esi, [A0] (6 B) -> call lib_cal; nop
    p.put(1, cal_site, b'\xe8' + struct.pack('<i', labels['lib_cal'] - (cal_site + 5)) + b'\x90')
    print(f"exe: state knockout draws: st_ko obj1+{labels['st_ko']:#x} at obj1+{stc:#x}, st_kend at "
          f"{', '.join(f'obj1+{k:#x}' for k in kend)}, {len(st)} entries")
    print(f'exe: Libertadores 1997: bye call obj1+{bye_call:#x} (lib_bye {labels["lib_bye"]:#x}, BYE_TAB {len(bc)}, '
          f'national cups obj1+{nc_site:#x}, round advance obj1+{adv_site:#x}), '
          f'calendar obj1+{cal_site:#x}, code @ obj1+{cave:#x} '
          f'(diyFileBufferCopy obj2+{diycopy:#x})')
    return (cave + len(code) + 3) & ~3, labels['lib_pre']
