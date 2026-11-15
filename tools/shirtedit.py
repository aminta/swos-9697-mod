"""Editable shirt numbers (4.0.2; Marco's SWOS 2020 video, Nicola's request): on the team screen before a match
(playMatchMenu: each player row is an entry drawn by DrawPlayerEntries), LEFT on one of your players' rows lights his
number box (once the cursor has been on that row ~0.3 s: a LEFT that just brought it there, or a held one, still only
moves); then
  - UP / DOWN: the next / previous number of 1..99 that no other player of the team has (held = the menu's repeat);
  - digits (the keyboard's top row, by scan code: any layout): one or two digits, the second within ~1 s; a number
    another player has is swapped with him (he gets the old one): never two players with one number;
  - FIRE, ENTER, LEFT, RIGHT: done; ESC: the numbers as they were before this edit.
  - 4.2 (row 32 A, MC 15/11): the numpad's digits too while the box is lit (not E0-prefixed: g_prevScanCode != E0;
    the grey arrows / Home / PgUp... still are what they were), and the direction a held numpad digit key also makes
    (numpad 8 = up) is no move; outside the box the numpad moves the cursor as before. Off under SWOS++.
Not on the opponent's / the computer's squads (VIEW OPPO, showingCpuTeams). The number is the player record's own
shirtNumber byte, so it goes wherever the game keeps that team (career: careerTeam in the .CAR; seasons / competitions:
their saves; a friendly: that session only).

The game binds numbers to line-up places (benchnum.py: the bench gets 12..16, a starter swapped with a bench player
swaps numbers). The first edit sets bit 7 of the team record's byte 23 (benchnum.PIN_BIT: bit 0 is the game's
training-match flag, the other bits are 0 in every team file and TeamInit clears bit 0 only): from then on benchnum's
hooks treat that team as a squad-number world's (numbers stay with the players; a purchase / new player of a pinned
career club gets a free number).

Hooks: MenuProc's `call MenuCheckControls` -> `call se_ctl` (which calls it first; the controls are consumed while the
box is lit, so the cursor does not move and fire does not swap players); in DrawPlayerEntries the number entry's
(entry 32) `mov word [esi + isInvisible], 0` -> `call se_hl; nop` (the lit box: a coloured background on that row).
4.2 (Marco 11/11): the lit box covers the whole number column (x - 2, 14 px: a two-digit number is 12 px from x - 1),
and se_unsh (the entry's afterDraw while lit) paints the font's black shadow pixels (DrawChar's nibble 8) inside it in
the box's own colour: the number in white on a solid square. se_unsh is in obj4 at swreg.BOX_AT (MC 12/11: the career
cave is full), the number entry's own afterDraw is chained (se_ad). squadnum.py's squad screen gets the same box.
"""
import re
import struct

import nasmcave

HL_COLOR = 0x0E                 # the lit number box's background colour (menu palette)
WAIT = 28                       # menu frames for a second digit (~1 s)
DWELL = 8                       # menu frames on a row before LEFT lights its number (~0.3 s)
INFO = {}                       # patch()'s labels and sites for squadnum.py (4.0.6: the squad screen) and edteam.py

BOX_ASM = r"""
se_unsh:                                ; 4.2: the lit box's afterDraw. DrawChar draws a font's shadow pixels (nibble 8)
    pushad                              ; in black: inside the box they become the box's own colour (its top-left
    mov esi, [A5]                       ; pixel, left of the number), so the digits sit on a solid square
    movzx eax, word [esi + 16h]
    movzx ebx, word [CAMY]              ; (DrawChar's rows: y + (g_cameraY & 15))
    and ebx, 0Fh
    add eax, ebx
    imul eax, eax, 320
    movsx ebx, word [esi + 14h]
    add eax, ebx
    add eax, [LINADR]
    mov edi, eax
    mov dl, [edi]
    movzx ebp, word [esi + 1Ah]
.r: push edi
    movzx ecx, word [esi + 18h]
.c: cmp byte [edi], 8
    jne .n
    mov [edi], dl
.n: inc edi
    dec ecx
    jnz .c
    pop edi
    add edi, 320
    dec ebp
    jnz .r
    popad
    mov eax, [se_ad]                    ; (the entry's own afterDraw, if it had one)
    or eax, eax
    jz .x
    jmp eax
.x: ret

se_ad: dd 0                             ; (the number entry's afterDraw before se_unsh, set by se_hl)
"""

ASM = r"""
se_ctl:                                 ; MenuProc: replaces `call MenuCheckControls`
    call MCC
    pushad
    push dword [D0]
    push dword [D1]
    push dword [A0]
    mov ebx, [CURMENU + 0Ch]            ; the selected entry
    cmp ebx, [se_last]                  ; frames on this entry (LEFT just after arriving on a row is a move that
    je .same                            ; overshot, not an edit: the harness's paths, a held key)
    mov [se_last], ebx
    mov byte [se_dwell], 0
    jmp .counted
.same:
    cmp byte [se_dwell], 255
    je .counted
    inc byte [se_dwell]
.counted:
    cmp byte [se_on], 0
    jne .editing
    cmp byte [se_hold], 0               ; after an edit: wait until fire / left / right are released
    je .idle
    cmp word [FIRE], 0
    jne .swallow
    cmp byte [LEFT], 0
    jne .swallow
    cmp byte [RIGHT], 0
    jne .swallow
    mov byte [se_hold], 0
    jmp .idle
.swallow:
    call se_clear
    jmp .out
.idle:
    cmp word [MCD], 6                   ; left (MenuProc: 0 up, 2 right, 4 down, 6 left)
    jne .out
    cmp byte [se_dwell], DWELL
    jb .out
    test ebx, ebx
    jz .out
    mov byte [se_skip], 0               ; (4.2 B1: edteam's et_row sets it - the custom-teams editor skips taken numbers)
    call se_row
    jc .out
    mov [se_rec], edi
    mov [se_team], ebp
    mov [se_ent], ebx
    mov al, [edi + 2]
    mov [se_old], al
    test byte [ebp + PIN_AT], PIN_BIT
    jnz .pinned
    call se_unique                      ; (first edit of this team: one number per player first)
.pinned:
    mov byte [se_on], 1
    mov byte [se_dig], 0
    mov dword [se_prec], 0
    call se_clear
    jmp .out
.editing:
    cmp ebx, [se_ent]
    jne .stop
    movzx eax, word [LASTKEY]
    cmp eax, 1                          ; ESC
    je .esc
    cmp eax, 1Ch                        ; ENTER
    je .done
    call se_np                          ; 4.2 (row 32 A): a numpad digit key (not E0) -> its digit
    jnc .digit
    cmp eax, 2                          ; '1' .. '9' = 2 .. 10, '0' = 11
    jb .nokey
    cmp eax, 11
    ja .nokey
    dec eax
    cmp eax, 10
    jb .digit
    xor eax, eax
.digit:
    cmp byte [se_dig], 0
    je .first
    movzx ecx, byte [se_first]
    imul ecx, ecx, 10
    add ecx, eax
    mov byte [se_dig], 0
    call se_commit
    jmp .eaten
.first:
    test eax, eax
    jz .eaten                           ; (a leading 0)
    mov [se_first], al
    mov byte [se_dig], 1
    mov byte [se_timer], WAIT
    mov edi, [se_rec]
    cmp byte [se_cand], 0               ; (4.2 B1: typing drops a stepped candidate - back to the number before it)
    je .nc
    mov byte [se_cand], 0
    mov cl, [se_cbase]
    mov [edi + 2], cl
    call se_soff
.nc:
    mov al, [edi + 2]
    mov [se_base], al                   ; the number before this typing (for the swap)
    mov al, [se_first]
    mov [edi + 2], al                   ; shown at once; committed by the timer / a second digit / done
    jmp .eaten
.nokey:
    cmp byte [se_dig], 0
    je .dirs
    dec byte [se_timer]
    jnz .dirs
    call se_first_commit
.dirs:
    movsx eax, word [MCD]
    test eax, eax
    js .fire
    call se_nph                         ; (a numpad digit key held: its direction is not a move - the digit it
    jnc .eaten                          ;  typed stays)
    test eax, eax
    jz .up
    cmp eax, 4
    je .down
    cmp eax, 2
    je .done
    cmp eax, 6
    je .done
    jmp .eaten                          ; diagonals: nothing
.fire:
    cmp word [FIRE], 0
    jne .done
    cmp word [SHORTFIRE], 0
    jne .done
    jmp .out
.up:
    call se_first_commit
    mov edx, 1
    call se_step
    jmp .eaten
.down:
    call se_first_commit
    mov edx, -1
    call se_step
    jmp .eaten
.esc:
    mov byte [se_cand], 0               ; (4.2 B1: a stepped candidate is dropped - the holder never changed)
    call se_soff
    mov byte [se_dig], 0
    mov edi, [se_rec]
    mov al, [se_old]
    mov [edi + 2], al
    mov esi, [se_prec]
    test esi, esi
    jz .done
    mov al, [se_pold]
    mov [esi + 2], al
.done:
    call se_first_commit
    call se_cconf                       ; (4.2 B1: every exit but ESC confirms a stepped candidate - the swap)
    mov byte [se_on], 0
    mov byte [se_hold], 1
.eaten:
    mov word [LASTKEY], 0
    call se_clear
    jmp .out
.stop:
    call se_first_commit
    call se_cconf
    mov byte [se_on], 0
.out:
    pop dword [A0]
    pop dword [D1]
    pop dword [D0]
    popad
    ret

se_np:                                  ; eax = lastKey: a numpad digit key (47h..52h, its make or a repeat, not
    cmp eax, 47h                        ; E0-prefixed: g_prevScanCode != E0 - the grey arrows / Home / PgUp... are)
    jb .no                              ; -> CF clear, eax = 0..9; else CF set, eax kept. Off under SWOS++
    cmp eax, 52h
    ja .no
    cmp byte [SWOSPP], 0FFh
    jne .no
    cmp byte [PREV], 0E0h
    je .no
    cmp byte [se_npt + eax - 47h], 0FFh
    je .no
    movzx eax, byte [se_npt + eax - 47h]
    clc
    ret
.no:stc
    ret

se_nph:                                 ; the last key event a numpad digit key's make (held; not E0): CF clear
    push eax
    movzx eax, byte [SCAN]
    cmp al, 47h
    jb .no
    cmp al, 52h
    ja .no
    cmp byte [se_npt + eax - 47h], 0FFh
    je .no
    cmp byte [SWOSPP], 0FFh
    jne .no
    cmp byte [PREV], 0E0h
    je .no
    pop eax
    clc
    ret
.no:pop eax
    stc
    ret

se_npt: db 7, 8, 9, 0FFh, 4, 5, 6, 0FFh, 1, 2, 3, 0   ; 47h..52h: Home 8 PgUp - 4 5 6 + End 2 PgDn Ins

se_cconf:                               ; 4.2 B1: a stepped candidate confirmed: its holder gets the number before
    cmp byte [se_cand], 0               ; the stepping (one number per player, always)
    je .r
    mov byte [se_cand], 0
    pushad
    mov edi, [se_rec]
    mov al, [edi + 2]
    cmp al, [se_cbase]
    je .p
    call se_used
    test esi, esi
    jz .p
    mov al, [se_cbase]
    mov [esi + 2], al
.p: call se_pin
    call se_soff
    popad
.r: ret

se_clear:                               ; no move, no fire this frame
    mov word [MCD], -1
    mov word [FIRE], 0
    mov word [SHORTFIRE], 0
    ret

se_first_commit:                        ; a single typed digit pending: commit it
    cmp byte [se_dig], 0
    je .r
    mov byte [se_dig], 0
    movzx ecx, byte [se_first]
    call se_commit
.r:
    ret

se_commit:                              ; ecx = typed number 1..99: the player holding it gets se_base
    mov edi, [se_rec]
    mov eax, ecx
    call se_used                        ; esi = another record with that number, or 0
    test esi, esi
    jz .set
    cmp dword [se_prec], 0
    jne .swap
    mov [se_prec], esi
    mov al, [esi + 2]
    mov [se_pold], al
.swap:
    mov al, [se_base]
    mov [esi + 2], al
.set:
    mov [edi + 2], cl
    jmp se_pin

se_step:                                ; edx = +1 / -1: 4.2 B1 (Davide 15/11): the next number of 1..99, taken or
    cmp byte [se_skip], 0               ; not (a taken one: the strip, swapped on confirm - se_cconf); EDIT CUSTOM
    jne .old                            ; TEAMS (se_skip): the next one nobody else has, as before
    mov edi, [se_rec]
    cmp byte [se_cand], 0
    jne .b1
    mov al, [edi + 2]
    mov [se_cbase], al                  ; (the number before the stepping: the holder's on confirm)
    mov byte [se_cand], 1
.b1:movzx eax, byte [edi + 2]
    add eax, edx
    cmp eax, 99
    jle .b1lo
    mov eax, 1
.b1lo:
    cmp eax, 1
    jge .b1s
    mov eax, 99
.b1s:
    mov [edi + 2], al
    jmp se_supd
.old:
    mov edi, [se_rec]
    movzx eax, byte [edi + 2]
    mov ecx, 99
.n:
    add eax, edx
    cmp eax, 99
    jle .lo
    mov eax, 1
.lo:
    cmp eax, 1
    jge .chk
    mov eax, 99
.chk:
    push eax
    call se_used
    pop eax
    test esi, esi
    jz .set
    loop .n
    ret
.set:
    mov [edi + 2], al
se_pin:
    mov ebp, [se_team]
    or byte [ebp + PIN_AT], PIN_BIT     ; numbers stay with the players from now on (benchnum)
    ret

se_count:                               ; ebp = team -> edx = its players (the career club: careerNumPlayers)
    mov edx, 16
    cmp ebp, CT
    jne .r
    movzx edx, word [CNP]
.r:
    ret

se_recn:                                ; ebp = team, ecx = squad index -> esi = his record (the line-up order: the
    movzx esi, cl                       ; career club's CMP; 4.0.5 another team's playerNumbers at +60 for places
    cmp ebp, CT                         ; 0..15 - Marco: se_unique walked the file's record order, so a bench player
    je .ct                              ; kept a number a starter had)
    cmp ecx, 16
    jae .rec
    movzx esi, byte [ebp + 60 + ecx]
    and esi, 0Fh
    jmp .rec
.ct:
    movzx esi, byte [CMP + ecx]
.rec:
    imul esi, esi, 38
    lea esi, [ebp + 76 + esi]
    ret

se_unique:                              ; ebp = team: duplicates / 0 / 100+ get free numbers (the first holder in
    pushad                              ; squad order keeps his: starters first), the lowest free of 2..99 (1 too
    mov edi, se_seen                    ; for a keeper), as benchnum's purchases
    xor eax, eax
    mov ecx, 100 + 32
.z:
    mov [edi], al
    inc edi
    loop .z
    call se_count
    xor ecx, ecx
.p1:
    cmp ecx, edx
    jae .p2s
    call se_recn
    movzx eax, byte [esi + 2]
    inc ecx
    test eax, eax
    jz .p1
    cmp eax, 100
    jae .p1
    cmp byte [se_seen + eax], 0
    jne .p1
    mov byte [se_seen + eax], 1
    mov byte [se_seen + 100 + ecx - 1], 1   ; keeps his number
    jmp .p1
.p2s:
    xor ecx, ecx
.p2:
    cmp ecx, edx
    jae .done
    cmp byte [se_seen + 100 + ecx], 0
    jne .next
    call se_recn
    mov bl, [esi + 26]
    shr bl, 5                           ; position: 0 = keeper
    mov eax, 1
    test bl, bl
    jz .try
    inc eax
.try:
    cmp byte [se_seen + eax], 0
    je .set
    inc eax
    cmp eax, 100
    jb .try
    jmp .next
.set:
    mov [esi + 2], al
    mov byte [se_seen + eax], 1
.next:
    inc ecx
    jmp .p2
.done:
    popad
    ret

se_used:                                ; al = number, edi = this record -> esi = another record of the team with it
    push ebx
    push ecx
    push edx
    mov ebp, [se_team]
    xor ecx, ecx
    mov edx, 16
    cmp ebp, CT
    jne .loop
    movzx edx, word [CNP]               ; the career club: its squad order, all its players
.loop:
    cmp ecx, edx
    jae .none
    movzx esi, cl
    cmp ebp, CT
    jne .rec
    movzx esi, byte [CMP + ecx]
.rec:
    imul esi, esi, 38
    lea esi, [ebp + 76 + esi]
    inc ecx
    cmp esi, edi
    je .loop
    cmp [esi + 2], al
    jne .loop
    jmp .r
.none:
    xor esi, esi
.r:
    pop edx
    pop ecx
    pop ebx
    ret

se_row:                                 ; ebx = entry: one of your players' rows? -> CF clear, edi = his record, ebp = team
    cmp dword [ebx + 34h], DPE          ; (its afterDraw)
    jne .no
    cmp byte [ebx + 8], 0FFh            ; LEFT goes nowhere from it (else LEFT is the menu's move)
    jne .no
    cmp word [VOPP], 0
    jne .no
    cmp word [SCPU], 0
    jne .no
    mov ebp, [PM1]
    test ebp, ebp
    jz .no
    movzx eax, word [ebx + 2]           ; ordinal: 13.. = the rows (16 = the last substitute's, as OnSwapPlayer)
    sub eax, 13
    jb .no
    cmp eax, 16
    ja .no
    jne .idx
    sub eax, 5
    add ax, [MAXSUB]
.idx:
    mov [A0], ebp
    mov [D1], ax
    push ebp
    push ebx
    call GPIBP                          ; -> [A0] + 4Ch = his record
    pop ebx
    pop ebp
    mov edi, [A0]
    add edi, 76
    mov eax, edi
    sub eax, ebp
    sub eax, 76
    cmp eax, 38 * 32
    jae .no
    clc
    ret
.no:
    stc
    ret

se_hl:                                  ; DrawPlayerEntries, number entry: replaces `mov word [esi + 4], 0`
    mov word [esi + 4], 0
    push eax
    cmp byte [se_on], 0
    je .plain
    mov eax, [A6]
    add eax, 76
    cmp eax, [se_rec]
    jne .plain
    mov word [esi + 1Ch], 2             ; a coloured background
    mov word [esi + 1Eh], HL
    cmp word [esi + 18h], 14            ; 4.2 (Marco 11/11: 28 looked bad - a two-digit number is 12 px from x - 1,
    je .w                               ; past the 11 px box on both sides): the box = the whole number column,
    sub word [esi + 14h], 2             ; x - 2 .. x + 11 (14 px, between the face and the name bar), the number
    mov word [esi + 18h], 14            ; centred as before (x - 2 + 7 = x + 5), a 1 px margin each side
.w: cmp dword [esi + 34h], se_unsh      ; and the digits without their black shadow (se_unsh, afterDraw)
    je .d
    mov eax, [esi + 34h]
    mov [se_ad], eax
    mov dword [esi + 34h], se_unsh
.d: pop eax
    ret
.plain:
    mov word [esi + 1Ch], 0
    cmp word [esi + 18h], 14            ; (the entry is the rows' one template: x, width, afterDraw back)
    jne .p
    add word [esi + 14h], 2
.p: mov word [esi + 18h], 10
    cmp dword [esi + 34h], se_unsh
    jne .q
    mov eax, [se_ad]
    mov [esi + 34h], eax
.q: pop eax
    ret

align 4
se_seen: times 100 + 32 db 0
align 4
se_rec: dd 0
se_last: dd 0
se_dwell: db 0
se_team: dd 0
se_ent: dd 0
se_prec: dd 0
se_on: db 0
se_cand: db 0
se_cbase: db 0
se_skip: db 0
se_hold: db 0
se_dig: db 0
se_first: db 0
se_timer: db 0
se_old: db 0
se_pold: db 0
se_base: db 0
"""


STRIP_ASM = r"""
se_supd:                                ; 4.2 B1: the strip for the candidate - on while another player holds it
    pushad
    cmp byte [se_cand], 0
    je .off
    mov edi, [se_rec]
    mov al, [edi + 2]
    cmp al, [se_cbase]
    je .off
    call se_used
    test esi, esi
    jz .off
    movzx eax, byte [edi + 2]           ; the text: '20 Z. SAVICEVIC SCAMBIO' (the number, the holder's short name
    mov edi, se_sbuf                    ;  as the team screen's rows: initial + surname, at most SNMAX characters
    cmp eax, 10                         ;  after the initial - the verb never cut, MC 15/11)
    jb .one
    xor edx, edx
    mov ecx, 10
    div ecx
    add al, '0'
    stosb
    mov eax, edx
.one:
    add al, '0'
    stosb
    mov al, ' '
    stosb
    lea ebx, [esi + 3]                  ; (the record's name)
    xor edx, edx
.f: mov al, [ebx + edx]
    test al, al
    jz .whole
    cmp al, ' '
    je .sp
    inc edx
    cmp edx, 22
    jb .f
.whole:
    mov esi, ebx
    jmp .cp
.sp:test edx, edx
    jz .whole
    mov al, [ebx]
    mov ah, '.'
    stosw
    mov al, ' '
    stosb
    lea esi, [ebx + edx + 1]
.cp:mov ecx, SNMAX
.c2:lodsb
    test al, al
    jz .vb
    stosb
    loop .c2
.vb:mov al, ' '
    stosb
    mov esi, se_verb
.c3:lodsb
    stosb
    test al, al
    jnz .c3
    call se_sshow
    popad
    ret
.off:
    call se_soff
    popad
    ret

se_sshow:                               ; the coach line (bottom left: its label entry, x <= 10 y >= 160 h 8, and the
    cmp byte [se_son], 0                ; name entry right after it) becomes the strip: one bar in the lit box's
    jne .r                              ; colour over both, the text se_sbuf (the menu draws it every frame)
    movzx ecx, word [CURMENU + 10h]
    lea ebx, [CURMENU + 16h]
.l: test ecx, ecx
    jz .r
    cmp word [ebx + 4], 0
    jne .n
    cmp word [ebx + 1Ah], 8
    jne .n
    cmp word [ebx + 16h], 160           ; (team screen y 172, squad screen 192; x 8 both - the rows' number column
    jl .n                               ;  is at x 14 / 20; the team screen's ALLENA: button is 15 px high)
    cmp word [ebx + 14h], 10
    jg .n
    cmp dword [ebx + 26h], 0
    jne .got
.n: add ebx, 38h
    dec ecx
    jmp .l
.got:
    mov [se_slab], ebx
    mov eax, [ebx + 26h]
    mov [se_stxt], eax
    mov eax, [ebx + 18h]                ; (width + height)
    mov [se_swh], eax
    mov eax, [ebx + 1Ch]                ; (background type + colour)
    mov [se_sbg], eax
    lea edx, [ebx + 38h]                ; the name entry: the next one, on the same line, right of the label
    mov dword [se_snam], 0
    dec ecx
    jz .set
    mov ax, [edx + 16h]
    cmp ax, [ebx + 16h]
    jne .set
    mov ax, [edx + 14h]
    cmp ax, [ebx + 14h]
    jle .set
    mov [se_snam], edx
    add ax, [edx + 18h]
    sub ax, [ebx + 14h]
    mov [ebx + 18h], ax                 ; (the bar: the label's x .. the name's right end)
    mov word [edx + 4], 1
.set:
    mov word [ebx + 1Ch], 2
    mov word [ebx + 1Eh], HL
    mov dword [ebx + 26h], se_sbuf
    mov byte [se_son], 1
.r: ret

se_soff:                                ; the coach line back (only if this menu still shows the strip)
    cmp byte [se_son], 0
    je .r
    mov byte [se_son], 0
    push ebx
    push eax
    mov ebx, [se_slab]
    cmp dword [ebx + 26h], se_sbuf
    jne .x
    mov eax, [se_stxt]
    mov [ebx + 26h], eax
    mov eax, [se_swh]
    mov [ebx + 18h], eax
    mov eax, [se_sbg]
    mov [ebx + 1Ch], eax
    mov ebx, [se_snam]
    test ebx, ebx
    jz .x
    mov word [ebx + 4], 0
.x: pop eax
    pop ebx
.r: ret

align 4
se_slab: dd 0
se_snam: dd 0
se_stxt: dd 0
se_swh: dd 0
se_sbg: dd 0
se_son: db 0
se_sbuf: times 48 db 0
"""
# (4.2 B1, MC 15/11: the strip block in its own obj4 band SESTRIP; se_verb appended per language)


def sites(p):
    """Variables and sites on the original bytes."""
    import sacups
    import xtra
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['A0']
    pk = lambda x: re.escape(struct.pack('<I', x))
    t = lambda o: p.target(1, o)
    rel = lambda o: o + 4 + struct.unpack_from('<i', d1, o)[0]
    d7, d0, d1v, d5, a1, a5, a6 = a0 - 4, a0 - 32, a0 - 28, a0 - 12, a0 + 4, a0 + 20, a0 + 24
    out = {}
    # OnSwapPlayer: mov eax,[playMatchTeam1Ptr]; mov [A1],eax; mov ax,[viewingOpponentTeam]; or ax,ax; jnz;
    #               mov ax,[showingCpuTeams]; or ax,ax; jnz; jmp
    m = [x for x in re.finditer(rb'\xa1(....)\xa3' + pk(a1) + rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0'
                                rb'\x75.\xe9', d1, re.S)]
    assert len(m) == 1, ('OnSwapPlayer', len(m))
    sw = m[0].start()
    out.update(PM1=t(sw + 1), VOPP=t(sw + 12), SCPU=t(sw + 23))
    # its no-cpu path: mov ax,[maxSubstitutesEntries]; add [D6],ax ... mov eax,[PM1]; mov [A0],eax; mov ax,[D6];
    # mov [D1],ax; call GetPlayerInfoBreakPosition
    pm1 = d1[sw + 1:sw + 5]
    g = [x for x in re.finditer(rb'\x66\xa1(....)\x66\x01\x05(....)\xa1' + re.escape(pm1) + rb'\xa3' + pk(a0) +
                                rb'\x66\xa1\2\x66\xa3' + pk(d1v) + rb'\xe8', d1[sw:sw + 0x400], re.S)]
    assert len(g) == 1, ('GetPlayerInfoBreakPosition', len(g))
    out['MAXSUB'] = t(sw + g[0].start(1))
    out['GPIBP'] = (1, rel(sw + g[0].end()))
    # MenuProc: call ReadTimerDelta; call DrawMenu; mov ax, 4; cmp word [g_videoSpeedIndex], 50
    m = [x.start() for x in re.finditer(rb'\xe8....\xe8....\x66\xb8\x04\x00\x66\x83\x3d....\x32\x7f', d1, re.S)]
    assert len(m) == 1, ('MenuProc', m)
    mp = m[0]
    c = [x for x in re.finditer(rb'\xe8(....)\x66\xc7\x05(....)\x00\x00\xe8(....)', d1[mp:mp + 0x100], re.S)]
    assert len(c) == 1, ('MenuCheckControls call', len(c))
    out['MCC_SITE'] = mp + c[0].start(3) - 1
    out['MCC'] = (1, rel(mp + c[0].start(3)))
    mcc = out['MCC'][1]
    k = re.match(rb'\xe8....\x66\xa1(....)\x66\xa3' + pk(d0), d1[mcc:mcc + 24], re.S)
    assert k, 'lastKey'
    out['LASTKEY'] = t(mcc + 7)
    q = mp + 0x40
    sf = re.search(rb'\x66\xa1(....)\x66\x0b\xc0\x74.\x80\x0d' + pk(d7) + rb'\x20\x66\xa1(....)\x66\x0b\xc0\x74.\x80\x0d'
                   + pk(d7) + rb'\x01\xa0(....)\x0a\xc0\x74.\x80\x0d' + pk(d7) + rb'\x02\xa0(....)\x0a\xc0\x74.\x80\x0d'
                   + pk(d7) + rb'\x04', d1[q:q + 0x200], re.S)
    assert sf, 'fire / shortFire / left / right'
    out.update(SHORTFIRE=t(q + sf.start(1)), FIRE=t(q + sf.start(2)), LEFT=t(q + sf.start(3)), RIGHT=t(q + sf.start(4)))
    md = re.search(rb'\x66\xa1(....)\x66\xa3' + pk(d0) + rb'\x66\x0b\xc0\x78', d1[q:q + 0x300], re.S)
    assert md, 'menuControlsDirection'
    out['MCD'] = t(q + md.start(1))
    cm = re.search(rb'\xc7\x05' + pk(a6) + rb'(....)\x8b\x35' + pk(a6) + rb'\x8b\x46\x0c', d1[mp:mp + 0x200], re.S)
    assert cm, 'g_currentMenu'
    out['CURMENU'] = t(mp + cm.start(1))
    # DrawPlayerEntries: mov esi,[A5]; mov ax,[esi+2]; mov [D7],ax; sub word [D7],13; cmp word [D7],16
    m = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(a5) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d7) + rb'\x66\x83\x2d'
                                        + pk(d7) + rb'\x0d\x66\x83\x3d' + pk(d7) + rb'\x10', d1, re.S)]
    assert len(m) == 1, ('DrawPlayerEntries', m)
    out['DPE'] = (1, m[0])
    # its number entry: mov esi,[A0]; mov word [esi+4],1; mov ax,[D5]; or ax,ax; jnz; mov word [D0],0; mov esi,[A6];
    # mov al,[esi+4Eh]; mov [D0],al; mov ax,[D0]; mov esi,[A0]; mov [esi+26h],ax; mov esi,[A0]; mov word [esi+4],0
    m = [x.end() - 6 for x in re.finditer(rb'\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x01\x00\x66\xa1' + pk(d5) +
                                          rb'\x66\x0b\xc0\x75.\x66\xc7\x05' + pk(d0) + rb'\x00\x00\x8b\x35' + pk(a6) +
                                          rb'\x8a\x46\x4e\xa2' + pk(d0) + rb'\x66\xa1' + pk(d0) + rb'\x8b\x35' + pk(a0) +
                                          rb'\x66\x89\x46\x26\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x00\x00',
                                          d1[out['DPE'][1]:out['DPE'][1] + 0x1000], re.S)]
    assert len(m) == 1, ('number entry', m)
    out['HL_SITE'] = out['DPE'][1] + m[0]
    _, cnp, ct, cmp, _ = xtra.sites(p)
    out.update(CNP=(2, cnp), CT=(2, ct), CMP=(2, cmp), A0=(2, a0), D0=(2, d0), D1=(2, d1v), A6=(2, a6))
    return out


VERB = {'it': 'SCAMBIO', 'en': 'SWAP', 'fr': 'ECHANGE', 'de': 'TAUSCH'}   # 4.2 B1: the strip's swap word
SNMAX = 16                      # the holder's name in the strip: at most 16 characters after the initial (MC 15/11:
                                # the name is cut, never the verb; the harness checks the widest release name)


def patch(p, cave, obj=1, lang='it'):
    """Code at obj:cave (the career cave in obj1; 4.2 OBJ1MV: obj4's band, MC 13/11); returns its end."""
    import benchnum
    s = sites(p)
    sym = {k: v for k, v in s.items() if not k.endswith('_SITE')}
    import quietend
    _, _, _, linadr, a0 = quietend.draw_sites(p)
    cy = [m.start() + 2 for m in re.finditer(rb'\x66\xa1....\x83\xe0\x0f\x03\xf8\xc1\xe7\x06', p.le.obj_bytes(1), re.S)]
    assert len(cy) == 1, ('DrawChar g_cameraY', cy)
    sym.update(LINADR=linadr, CAMY=p.target(1, cy[0]), A5=(sym['A0'][0], sym['A0'][1] + 20))
    import controls
    import keytext
    cs, kv = controls.locate(p), keytext.find(p)[1]       # 4.2 row 32 A: the numpad digits (se_np / se_nph)
    sym.update(SWOSPP=cs['SWOSPP'], SCAN=cs['SCAN'], PREV=kv['PREV'])
    sym.update(PIN_AT=(0, benchnum.PIN_AT), PIN_BIT=(0, benchnum.PIN_BIT), HL=(0, HL_COLOR), WAIT=(0, WAIT),
               DWELL=(0, DWELL), SNMAX=(0, SNMAX))
    cave = (cave + 3) & ~3
    import swreg
    at = swreg.BOX_AT                   # 4.2 (MC 12/11): se_unsh in obj4 0xCF00..0xD000 (the career cave is full)
    bsym = {k: sym[k] for k in ('LINADR', 'CAMY', 'A5')}
    bcode, bfix, brel = nasmcave.assemble_obj(BOX_ASM, at, bsym, 4)
    blab = nasmcave.labels(BOX_ASM, at, bsym)
    assert at + len(bcode) <= swreg.BOX_END, ('shirtbox: past its obj4 room', hex(at + len(bcode)))
    assert p.le.obj(4).npages * 0x1000 >= swreg.BOX_END, 'shirtbox: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.BOX_END - at)), 'shirtbox: obj4 room not free'
    p.put(4, at, bcode)
    for o, t_obj, t_off in bfix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in brel:
        p.add_rel(4, at + o, t_obj, t_off)
    sym.update(se_unsh=(4, blab['se_unsh']), se_ad=(4, blab['se_ad']))
    # 4.2 B1 (MC 15/11): the strip (se_supd / se_sshow / se_soff, its buffer, the verb) in obj4's SESTRIP band; the
    # main block calls it and it reads the main block's state: main first with the strip at the band's start (rel32 /
    # absolute encodings do not depend on the value), the strip on the main labels, then main again on the real ones
    assert obj == 4, 'shirtedit: the B1 strip lives in obj4 (SESTRIP)'
    assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in VERB[lang]), VERB[lang]
    ssrc = STRIP_ASM + 'se_verb: db ' + ', '.join(str(c) for c in VERB[lang].encode()) + ', 0\n'
    sa = swreg.SESTRIP_AT
    lab0 = nasmcave.labels(ASM, cave, {**sym, 'se_supd': (4, sa), 'se_soff': (4, sa)})
    ssym = {k: sym[k] for k in ('CURMENU', 'HL', 'SNMAX')}
    ssym.update({k: (4, lab0[k]) for k in ('se_cand', 'se_rec', 'se_cbase', 'se_used')})
    scode, sfix, srel = nasmcave.assemble_obj(ssrc, sa, ssym, 4)
    slab = nasmcave.labels(ssrc, sa, ssym)
    sleft = swreg.SESTRIP_END - sa - len(scode)
    assert sleft >= 256, ('shirtedit strip: SESTRIP band (MC: >= 256 B left)', sleft)
    assert p.le.obj(4).npages * 0x1000 >= swreg.SESTRIP_END, 'shirtedit strip: obj4 pages (patch.py OBJ1MV_ON)'
    assert not any(p.get(4, sa, swreg.SESTRIP_END - sa)), 'shirtedit strip: SESTRIP band not free'
    p.put(4, sa, scode)
    for off, tobj, toff in sfix:
        p.add_ptr(4, sa + off, tobj, toff)
    for off, tobj, toff in srel:
        p.add_rel(4, sa + off, tobj, toff)
    sym.update(se_supd=(4, slab['se_supd']), se_soff=(4, slab['se_soff']))
    src = ASM
    code, fix, rel = nasmcave.assemble_obj(src, cave, sym, obj)
    lab = nasmcave.labels(src, cave, sym)
    assert all(lab[k] == lab0[k] for k in lab0), 'shirtedit: main block moved between passes'
    left = swreg.OBJ1MV_END - cave - len(code)
    assert swreg.OBJ1MV_CC <= cave and left >= 0, ('shirtedit: outside OBJ1MV', hex(cave))
    assert p.le.obj(4).npages * 0x1000 >= swreg.OBJ1MV_END, 'shirtedit: obj4 pages (patch.py OBJ1MV_ON)'
    assert not any(p.get(obj, cave, len(code)))
    p.put(obj, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(obj, cave + off, tobj, toff)
    for off, tobj, toff in rel:
        p.add_rel(obj, cave + off, tobj, toff)
    mc = s['MCC_SITE']
    assert p.call_target(1, mc) == s['MCC'], 'MenuProc call'
    p.branch(1, mc, 0xE8, obj, lab['se_ctl'])
    hl = s['HL_SITE']
    assert p.get(1, hl, 6) == b'\x66\xc7\x46\x04\x00\x00'
    p.branch(1, hl, 0xE8, obj, lab['se_hl'], 6)
    rc = [cave + m.start() for m in re.finditer(rb'\xe8', code)
          if cave + m.start() + 5 + struct.unpack_from('<i', code, m.start() + 1)[0] == lab['se_row']]
    assert len(rc) == 1, ('call se_row', rc)
    dc = [cave + m.start() for m in re.finditer(re.escape(b'\x66\x83\x3d' + struct.pack('<I', sym['MCD'][1]) + b'\x06'),
                                                 code)]
    assert len(dc) == 1, ('cmp word [MCD], 6', dc)     # (se_ctl's idle: the direction that opens the box - edteam's)
    INFO.update(obj=obj, se_row=lab['se_row'], se_hl=lab['se_hl'], row_call=rc[0], GPIBP=s['GPIBP'], se_on=lab['se_on'],
                se_rec=lab['se_rec'], se_ent=lab['se_ent'], dir_at=dc[0], se_skip=lab['se_skip'],
                se_unsh=(4, blab['se_unsh']), se_ad=(4, blab['se_ad']),
                **{k: sym[k] for k in ('CT', 'A0', 'D1', 'MCD', 'CURMENU')})
    print(f'exe: editable shirt numbers (MenuProc obj1+{mc:#x}, DrawPlayerEntries number obj1+{hl:#x}, '
          f'code obj{obj}+{cave:#x}..{cave + len(code):#x}, strip obj4+{sa:#x}..{sa + len(scode):#x}, {sleft} B left in SESTRIP)')
    return (cave + len(code) + 3) & ~3
