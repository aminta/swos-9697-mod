"""UEFA qualifying rounds of a league-phase career world: the season end's glue around tools/uefaq.c.

Season end (cseg_91428): the qualifiers run country by country (cseg_93974). In a league-phase world the first one
closes the season's coefficients (uefacoef uc_final: the ranking of the world's UEFA associations), then for every
country uq_country (careerworld w_q_cq) copies its top 9 (the standings records) and its cup winner (record, club
coefficient = 5 seasons, strength = the 16 players' prices) into the C input; nothing is added to the cup lists.
Before the record count check (careerworld w_chk_tot0q -> w_q_fill) uq_fill: the title holders, the 2 European Performance Spots (the
best two associations of the season just ended), a seed, uq_season() (C), then the three league phases' clubs into
the CC / CWC / UEFA lists (+ their records) except the holders, which w_holders appends as before (36 / 36 / 36).
"""
import os
import re
import struct

ASM = '''
uq_country:                             ; careerworld w_q_cq (w_q_cl in a league-phase world): CF = 1
    pushad
    push es                             ; (string instructions below: ES may differ from DS)
    push ds
    pop es
    cmp byte [W_QON], 0
    jne .on
    mov byte [W_QON], 1                 ; the first country of this season end: a fresh input
    mov edi, UQ_IN
    mov ecx, IN_SIZE / 4
    xor eax, eax
    cld
    rep stosd
.on:
    xor ebx, ebx                        ; the country = the file of the first club of its standings
.f:
    cmp ebx, 9
    jae .x
    imul esi, ebx, 2ACh
    mov ax, [STAND + esi]
    inc ebx
    test ax, ax
    jz .f
    cmp ax, 0FFFFh
    je .f
    xor ecx, ecx
.r:
    cmp ecx, [UC_N]
    jae .x                              ; (not one of the world's UEFA associations)
    cmp al, [UC_C + ecx]
    je .rk
    inc ecx
    jmp .r
.rk:
    lea ebp, [ecx + 1]                  ; ebp = rank (1..)
    cmp ebp, 55
    ja .x
    mov byte [UQ_IN + L_PRESENT + ebp], 1
    xor ebx, ebx                        ; ebx = standings index, edx = league slot
    xor edx, edx
.l:
    imul esi, ebx, 2ACh
    add esi, STAND
    mov ax, [esi]
    test ax, ax
    jz .l1
    cmp ax, 0FFFFh
    je .l1
    imul edi, ebp, 10                   ; club index (rank - 1) * 10 + slot
    lea edi, [edi + edx - 10]
    call .club
    imul ecx, ebp, 18
    mov [UQ_IN + L_LEAGUE + ecx + edx*2], ax
    inc edx
.l1:
    inc ebx
    cmp ebx, 9
    jb .l
    mov esi, CUPREC + 2ACh              ; the cup winner (a league club already: the same index)
    mov ax, [esi]
    test ax, ax
    jz .x
    cmp ax, 0FFFFh
    je .x
    xor ecx, ecx
.c:
    cmp ecx, edx
    jae .cn
    imul edi, ebp, 10
    lea edi, [edi + ecx - 10]
    imul edi, edi, CSZ
    cmp ax, [UQ_IN + L_CLUB + edi]
    je .cs
    inc ecx
    jmp .c
.cs:
    imul eax, ebp, 10
    lea eax, [eax + ecx - 9]
    jmp .cw
.cn:
    imul edi, ebp, 10                   ; slot 9
    dec edi
    call .club
.cw:
    mov [UQ_IN + L_CUP + ebp*2], ax
.x:
    pop es
    popad
    stc
    ret
.club:                                  ; esi = record, edi = club index, ebp = rank -> eax = index + 1
    push ebx
    push ecx
    push edx
    push esi
    push edi
    mov ebx, edi
    imul edi, edi, 2ACh
    add edi, UQREC
    mov ecx, 171
    cld
    rep movsd
    mov esi, [esp + 4]
    imul edi, ebx, CSZ
    add edi, UQ_IN + L_CLUB
    mov ax, [esi]
    mov [edi], ax
    mov ecx, ebp
    mov [edi + 2], cl
    xor eax, eax                        ; strength: the 16 players' prices
    xor ecx, ecx
.s:
    movzx edx, byte [esi + 76 + 32]
    add eax, edx
    add esi, 38
    inc ecx
    cmp ecx, 16
    jb .s
    mov [edi + 8], eax
    mov esi, [esp + 4]
    movzx eax, word [esi]               ; club coefficient (5 seasons, units; the association floor included)
    call UC_KC
    mov [edi + 4], eax
    lea eax, [ebx + 1]
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

uq_fill:                                ; careerworld w_q_fill (before the season end's record check)
    cmp byte [W_QON], 0
    je .r0
    pushad
    push es                             ; (the C code assumes ES = DS)
    push ds
    pop es
    mov byte [W_QON], 0
    mov word [UQ_IN + L_NCLUB], 553
    xor ebx, ebx                        ; the holders: their club index (a club not seen: 550 + cup)
.h:
    mov esi, [UQ_HP + ebx*4]
    mov ax, [esi]
    test ax, ax
    jz .hn
    cmp ax, 0FFFFh
    je .hn
    xor ecx, ecx
.hs:
    imul edi, ecx, CSZ
    cmp ax, [UQ_IN + L_CLUB + edi]
    je .hf
    inc ecx
    cmp ecx, 550
    jb .hs
    lea ecx, [ebx + 550]
    imul edi, ecx, CSZ
    mov [UQ_IN + L_CLUB + edi], ax
    xor edx, edx
.hr:
    cmp edx, [UC_N]
    jae .hf
    cmp al, [UC_C + edx]
    je .hr1
    inc edx
    jmp .hr
.hr1:
    inc edx
    mov [UQ_IN + L_CLUB + edi + 2], dl
.hf:
    inc ecx
    mov [UQ_IN + L_HOLD + ebx*2], cx
.hn:
    inc ebx
    cmp ebx, 3
    jb .h
    movzx eax, byte [CB + RING]         ; EPS: the 2 best associations of the season just ended (ring - 1)
    add eax, 4
    cmp eax, 5
    jb .e0
    sub eax, 5
.e0:
    shl eax, 10
    lea ebp, [CB + CHIST + eax]
    mov dword [UQ_V], -1
    mov dword [UQ_V + 4], -1
    mov word [UQ_E], 0
    xor ecx, ecx
.e:
    cmp ecx, [UC_N]
    jae .ed
    cmp ecx, 55
    jae .ed
    movzx eax, byte [UC_C + ecx]
    mov eax, [ebp + eax*4]
    lea edx, [ecx + 1]
    cmp eax, [UQ_V]
    jg .e1
    cmp eax, [UQ_V + 4]
    jle .en
    mov [UQ_V + 4], eax
    mov [UQ_E + 1], dl
    jmp .en
.e1:
    mov ebx, [UQ_V]
    mov [UQ_V + 4], ebx
    mov bl, [UQ_E]
    mov [UQ_E + 1], bl
    mov [UQ_V], eax
    mov [UQ_E], dl
.en:
    inc ecx
    jmp .e
.ed:
    mov ax, [UQ_E]
    mov [UQ_IN + L_EPS], ax
    xor eax, eax                        ; the seed: the clubs seen (a save gives the same draws)
    xor ecx, ecx
.sd:
    imul eax, eax, 31
    imul edi, ecx, CSZ
    movzx edx, word [UQ_IN + L_CLUB + edi]
    add eax, edx
    add eax, [UQ_IN + L_CLUB + edi + 8]
    inc ecx
    cmp ecx, 553
    jb .sd
    mov [UQ_IN], eax
    mov ax, [SEL]                       ; the career club (its index, if seen) and the test builds' forced round
    xor ecx, ecx
.ms:
    imul edi, ecx, CSZ
    cmp ax, [UQ_IN + L_CLUB + edi]
    je .mf
    inc ecx
    cmp ecx, 550
    jb .ms
    cmp byte [UQ_FORCE], 0              ; (test builds: a club outside the top 9 / cup winners is put in as an extra
    je .mn                              ; club 553, no record: it never reaches the lists while its ties are open)
    mov ecx, 553
    imul edi, ecx, CSZ
    mov [UQ_IN + L_CLUB + edi], ax
    mov dword [UQ_IN + L_CLUB + edi + 8], 1000
    xor edx, edx
.mr:
    cmp edx, [UC_N]
    jae .mr1
    cmp al, [UC_C + edx]
    je .mr0
    inc edx
    jmp .mr
.mr0:
    inc edx
    mov [UQ_IN + L_CLUB + edi + 2], dl
.mr1:
    mov word [UQ_IN + L_NCLUB], 554
.mf:
    inc ecx
    mov [UQ_IN + L_MANAGER], cx
.mn:
    mov al, [UQ_FORCE]
    mov [UQ_IN + L_FORCE], al
    mov dword [UQ_S], STATE             ; the bracket and the lists, kept in the save
    cld
    call uq_season
.ran:
    xor ebx, ebx                        ; the three league phases into the CC / CWC / UEFA lists
.o:
    xor edx, edx
.o1:
    cmp dl, [UQ_OUT + O_GN + ebx]
    jae .on
    imul eax, ebx, 80
    movzx eax, word [UQ_OUT + O_GL + eax + edx*2]
    dec eax
    cmp eax, 550
    jae .o2                             ; (a holder not seen: w_holders adds it)
    imul esi, eax, CSZ
    mov si, [UQ_IN + L_CLUB + esi]
    mov edi, [UQ_HP]                    ; the holders: w_holders appends them
    cmp si, [edi]
    je .o2
    mov edi, [UQ_HP + 4]
    cmp si, [edi]
    je .o2
    mov edi, [UQ_HP + 8]
    cmp si, [edi]
    je .o2
    pushad
    mov ecx, ebx
    shl ecx, 4
    mov edi, [HOLDTAB + ecx + 4]        ; (the 1996-97 table: CC, CWC, UEFA Cup rows)
    mov edi, [edi]
    mov ecx, [HOLDTAB + ecx + 8]
    movzx ebp, word [ecx]
    mov [edi + ebp*2], si
    inc word [ecx]
    imul eax, eax, 2ACh
    add eax, UQREC
    mov [A0R], eax
    call ADDREC
    popad
.o2:
    inc edx
    jmp .o1
.on:
    inc ebx
    cmp ebx, 3
    jb .o
.done:
    xor ebx, ebx                        ; the qualifying ties' contests: no tie (their lists are scanned by the
.q0:                                    ; slot-3 chain at the season start)
    mov edi, [UQ_QS + ebx*4]
    mov dword [edi + Q_LIST], 0
    inc ebx
    cmp ebx, 3
    jb .q0
    cmp byte [UQ_OUT + O_MT_N], 0
    je .qx
    movzx eax, byte [UQ_OUT + O_MT_ROUND]       ; the first tie of the career club
    xor ebx, ebx                        ; its competition: CL rounds 0..7, EL 8..13, UECL 14..
    cmp eax, 8
    jb .q1
    inc ebx
    cmp eax, 14
    jb .q1
    inc ebx
.q1:
    mov edi, [UQ_QS + ebx*4]
    mov dl, [UQ_WIN + eax]              ; the two legs' dates (eighths of a month)
    mov [edi + 3], dl
    add dl, 2
    mov [edi + 4], dl
    mov ax, [SEL]
    mov [edi + Q_LIST], ax
    movzx eax, word [UQ_OUT + O_MT_OPP]
    dec eax
    imul esi, eax, CSZ
    mov si, [UQ_IN + L_CLUB + esi]
    mov [edi + Q_LIST + 2], si
    mov byte [UQ_PEND], 1               ; (w_q_post: the records of every opponent it may meet)
.qx:
    pop es
    popad
.r0:
    ret

uq_post:                                ; careerworld w_q_post (after the season end's last record count check):
    cmp byte [UQ_PEND], 0               ; the records of every club the career club may meet in its ties (not in
    je .r                               ; a list already; a club outside the top 9 / cup winners has none)
    pushad
    mov byte [UQ_PEND], 0
    xor ebx, ebx
.p:
    cmp bl, [UQ_R + R_NPOT]
    jae .px
    mov ax, [UQ_R + R_POT + ebx*2]
    xor ecx, ecx                        ; in a list?
.p1:
    movzx edx, byte [UQ_OUT + O_GN + ecx]
    imul esi, ecx, 80
    lea esi, [UQ_OUT + O_GL + esi]
.p2:
    test edx, edx
    jz .p3
    movzx edi, word [esi]
    dec edi
    imul edi, edi, CSZ
    cmp ax, [UQ_IN + L_CLUB + edi]
    je .pn
    add esi, 2
    dec edx
    jmp .p2
.p3:
    inc ecx
    cmp ecx, 3
    jb .p1
    xor ecx, ecx                        ; its record
.p4:
    imul edi, ecx, CSZ
    cmp ax, [UQ_IN + L_CLUB + edi]
    je .p5
    inc ecx
    cmp ecx, 550
    jb .p4
    jmp .pn
.p5:
    imul eax, ecx, 2ACh
    add eax, UQREC
    mov [A0R], eax
    push ebx
    call ADDREC
    pop ebx
.pn:
    inc ebx
    jmp .p
.px:
    popad
.r:
    ret

uq_daily:                               ; replaces `call cseg_8EA56` at the start of cseg_8E3DA (the next match, between
    pushad                              ; matches): the career club's finished qualifying tie -> its next tie, or the
    mov esi, STATE                      ; league phase it reached (or none) into slot 3
    cmp word [esi], 5155h
    jne .x
    mov ax, [SEL]
    cmp ax, [esi + S_M]
    jne .x
    mov al, [SLOT3 + 2Dh]
    cmp al, QID0
    jb .x
    cmp al, QID0 + 2
    ja .x
    mov ax, [SLOT3 + 39h]               ; the tie's winner (FFFF until the second leg)
    cmp ax, 0FFFFh
    je .x
    movzx ecx, byte [esi + S_K]
    cmp ax, [esi + S_M]
    jne .lost
    mov dl, 1
    shl dl, cl
    or [esi + S_RES], dl
.lost:
    inc byte [esi + S_K]
    mov dword [UQ_S], STATE
    push es
    push ds
    pop es
    cld
    call uq_resolve
    pop es
    cmp byte [UQ_R + R_DONE], 0
    jne .final
    movzx eax, byte [UQ_R + R_R]        ; the next tie: its competition's contest, dates, the two clubs
    xor ebx, ebx
    cmp eax, 8
    jb .n1
    inc ebx
    cmp eax, 14
    jb .n1
    inc ebx
.n1:
    mov edi, [UQ_QS + ebx*4]
    mov dl, [UQ_WIN + eax]
    mov [edi + 3], dl
    add dl, 2
    mov [edi + 4], dl
    mov ax, [STATE + S_M]
    mov [edi + Q_LIST], ax
    mov ax, [UQ_R + R_OPP]
    mov [edi + Q_LIST + 2], ax
    mov [A0R], edi
    lea eax, [ebx + D7_BASE]
    push eax
    call .build
    pop eax
    mov [E092F], ax
    mov [CUP_KIND], bx
    jmp .x
.final:
    mov word [esi], 0                   ; (no tie left)
    xor ebx, ebx                        ; the final lists into the season's three league-phase cups
.f1:
    mov edi, [UQ_WC + ebx*4]
    imul esi, ebx, 72
    xor ecx, ecx
.f2:
    cmp cl, [STATE + S_GN + ebx]
    jae .f3
    mov ax, [UQ_R + R_GL + esi + ecx*2]
    mov [edi + 30h + ecx*2], ax
    inc ecx
    jmp .f2
.f3:
    inc ebx
    cmp ebx, 3
    jb .f1
    movzx ebx, byte [UQ_R + R_DEST]
    cmp ebx, 3
    jae .none
    mov edi, [UQ_WC + ebx*4]            ; the league phase reached: slot 3, as at a season start
    mov [A0R], edi
    call .build
    mov [E092F], bx
    mov [CUP_KIND], bx
    jmp .x
.none:
    mov word [E092F], -1                ; (out of Europe: the finished tie stays in slot 3, not reloaded)
.x:
    popad
    jmp C8EA56
.build:                                 ; [A0] = contest -> slot 3 (cseg_8B2D3: buffer + calendar). The calendar
    pushad                              ; entries already played of slot 3 get round FFh: cseg_8BC06 puts a round's
    mov esi, CAL                        ; matches into the FIRST entry of (slot, round, leg) from the calendar's
    movzx ecx, word [CAL_CUR]           ; start, which would be the finished tie's (the new one's stay empty and
    add ecx, esi                        ; are played as computer ties)
.c0:
    cmp esi, ecx
    jae .c1
    cmp byte [esi], 3
    jne .c2
    mov byte [esi + 7], 0FFh
.c2:
    movzx eax, word [esi + 2]
    test eax, eax
    jz .c1
    add esi, eax
    jmp .c0
.c1:
    popad
    pushad                              ; the slot buffer is cleared, as a never-used slot: cseg_8B2D3 starts from the old one
    push es                             ; and the finished tie's state (+55h, +149h ...) would keep cseg_8BC06 from
    push ds                             ; putting the new round's matches into the calendar (they would be simulated)
    pop es
    mov edi, SLOT3
    mov ecx, 0B52h
    xor eax, eax
    cld
    rep stosb
    pop es
    popad
    mov word [STAGE_G], 0               ; dseg_10EADD: the type-2 stage cseg_8BC06 fills the calendar for (stale
    mov word [D0R], 3                   ; from the last type-2 contest, the finished tie: its matches never got in)
    mov word [D1R], 0
    mov word [D2R], 0
    pushad
    call C8B2D3
    popad
    mov word [SLOT3 + 39h], 0FFFFh      ; (no winner yet)
    ret

uq_rn1:                                 ; the first instruction of cseg_280C0 (round name index, D0): our ties are
    call uq_tie_round                   ; named by their qualifying round, not 'final' (a 2-club stage)
    jc .r
    sub word [D1R], 1
    jmp R280C0 + 8
.r:
    ret
uq_rn2:                                 ; the same, cseg_283BD (also the calendar entries' round name)
    call uq_tie_round
    jc .r
    sub word [D2R], 1
    jmp R283BD + 8
.r:
    ret
uq_tie_round:                           ; CF = 1 and D0 = 0..3 (FIRST .. FOURTH ROUND = Q1, Q2, Q3, play-off) when
    push eax                            ; the contest loaded is one of our ties (diyFileBufferCopy +2Dh; DIY +2Dh the
    mov al, [DIYCOPY + 2Dh]             ; same, or 0 while it is being built: not a type-1 cup loaded since)
    sub al, QID0
    cmp al, 2
    ja .no
    mov al, [DIY + 2Dh]
    test al, al
    jz .y
    sub al, QID0
    cmp al, 2
    ja .no
.y:
    mov al, [DIYCOPY + 37h]             ; its first leg's date: the round
    xor ah, ah
    cmp al, 35h
    jb .d
    inc ah
    cmp al, 39h
    jb .d
    inc ah
    cmp al, 3Ch
    jb .d
    inc ah
.d:
    movzx eax, ah
    mov [D0R], ax
    pop eax
    stc
    ret
.no:
    pop eax
    clc
    ret

UQ_HP: dd HOLD_CC, HOLD_CWC, HOLD_UEFA
UQ_QS: dd QS0, QS1, QS2
UQ_PEND: db 0
UQ_WC: dd WCC, WCWC, WUEFA
UQ_FORCE: db FORCE
UQ_WIN: WIN_BYTES
UQ_V: dd 0, 0
UQ_E: dw 0
'''


STRUCTS_AT = 0x2F00             # the 3 contests (obj1, after the C code and the glue in uefaq's three pages)
QIDS = (0x7C, 0x7D, 0x7E)       # contest ids (mkseason.RESERVED_IDS): CL / EL / UECL qualifying tie
Q_NAME, Q_LIST = 0x28, 0x30     # offsets in a contest: its 2 name dwords, its 2-club list
NAMES = {'it': 'PRELIM. ', 'en': 'QUAL. ', 'fr': 'QUALIF. ', 'de': 'QUALI. '}
CUPS = (b'CHAMPIONS LEAGUE', b'EUROPA LEAGUE', b'CONFERENCE LEAGUE')
STRUCTS = []
D7_BASE = [None]                # sacups' chain value of the first contest (patch.py)
# the legs' dates per round (eighths of a month from January; the second leg 2 later): Q1 early July, Q2 late
# July, Q3 early August, play-off late August (the league phases start in September)
WIN = {'Q1': 0x31, 'Q2': 0x35, 'Q3': 0x39, 'PO': 0x3C}
ROUNDS = ['CL LS', 'CL PO', 'CL POnc', 'CL Q3', 'CL Q3nc', 'CL Q2', 'CL Q2nc', 'CL Q1', 'EL LS', 'EL PO', 'EL Q3',
          'EL Q3ch', 'EL Q2', 'EL Q1', 'CO LS', 'CO PO', 'CO POch', 'CO Q3', 'CO Q3ch', 'CO Q2', 'CO Q2ch', 'CO Q1']


def structs(p, area, lang, at):
    """The career club's qualifying tie, one contest per competition: a type-2 cup (the layout of careerworld's
    league-phase cups: built in slot 3 during a season, its matches reach the calendar; a type-1 cup's do not) with
    one knockout stage of 2 clubs, two legs, extra time and penalties, no away goals (abolished in 2021); its
    2-club list empty until a season end puts the club and its opponent in."""
    import sacups
    out = []
    for cid, cup in zip(QIDS, CUPS):
        h = bytearray(Q_NAME)
        h[0], h[1], h[2], h[3], h[4] = cid, 2, 0xFF, WIN['Q1'], WIN['Q1'] + 2
        h[5], h[7] = Q_NAME - 5, Q_LIST - 7
        h[8], h[9], h[10], h[11], h[12], h[13] = 1, 0, 0, 1, 3, 0x35
        stages = bytes([1, 2, 0, 2, 1])
        h[0x0E:0x28] = stages + bytes(20 - len(stages)) + bytes([0x94]) + bytes(5)
        rel = area.add(NAMES[lang].encode() + cup + b'\0') - sacups.STR_BASE
        p.put(1, at, bytes(h) + struct.pack('<II', rel, rel) + bytes(4))
        out.append(at)
        at += Q_LIST + 4
    STRUCTS[:] = out
    return out


def patch(p, at, limit, sites):
    """sites: careerworld LABELS / _qual_sites, uefacoef LABELS, the obj2 BSS base. Returns the end."""
    import cobj
    import nasmcave
    import careerworld as cw
    import uefacoef as uc
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uefaq.c'))
    bss_at = sites['bss'] + cw.B_UQ
    syms, end, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= cw.UQ_BSS, hex(bss)
    lay = struct.unpack('<22I', p.get(1, syms['UQ_LAYOUT'][1], 88))
    keys = ('L_PRESENT', 'L_EPS', 'L_HOLD', 'L_NCLUB', 'L_LEAGUE', 'L_CUP', 'L_CLUB', 'CSZ', 'O_N', 'O_LS', 'O_STATUS',
            'IN_SIZE', 'NC', 'L_MANAGER', 'L_FORCE', 'O_MT_N', 'O_MT_ROUND', 'O_MT_OPP', 'O_MT_WIN', 'O_STANDIN', 'O_GN',
            'O_GL')
    lay = dict(zip(keys, lay))
    assert lay['IN_SIZE'] % 4 == 0 and lay['CSZ'] == 12 and lay['NC'] >= 553, lay
    slay = dict(zip(('S_M', 'S_K', 'S_RES', 'S_GN', 'S_GL', 'S_SIZE', 'R_DONE', 'R_R', 'R_OPP', 'R_DEST', 'R_GL',
                     'R_NPOT', 'R_POT'), struct.unpack('<13I', p.get(1, syms['UQ_SLAYOUT'][1], 52))))
    assert uc.CB_OFF + uc.SIZE + slay['S_SIZE'] <= 80 * 684, slay
    d1 = p.le.obj_bytes(1)                      # cseg_8E3DA: `call cseg_8EA56` after the careerFinished test
    hits = [m.start() + 9 for m in re.finditer(
        rb'\x66\x0b\xc0\x0f\x85.{4}\xe8.{4}\x8b\x35.{4}\x8a\x46\x06\x0a\xc0\x78.\x75.', d1, re.S)]
    assert len(hits) == 1, hits
    site = hits[0]
    c8ea56 = site + 5 + struct.unpack_from('<i', d1, site + 1)[0]
    assert d1[c8ea56:c8ea56 + 2] == b'\xc7\x05' and d1[c8ea56 + 10:c8ea56 + 12] == b'\x66\xa1', d1[c8ea56:c8ea56 + 12].hex()
    cal, cal_cur = struct.unpack_from('<II', d1, c8ea56 + 6)[0], struct.unpack_from('<I', d1, c8ea56 + 12)[0]
    import sacups
    D = [sites['a0'] - 32 + 4 * i for i in range(8)]   # cseg_280C0 / cseg_283BD (round name index): their entries
    r1 = [m.start() for m in re.finditer(re.escape(b'\x66\x83\x2d' + struct.pack('<I', D[1]) + b'\x01\x66\xa1'
                                                    + struct.pack('<I', D[0])), d1)]
    r2 = [m.start() for m in re.finditer(re.escape(b'\x66\x83\x2d' + struct.pack('<I', D[2]) + b'\x01\x66\xa1'
                                                    + struct.pack('<I', D[1]) + b'\x66\x0b\xc0\x74'), d1)]
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]
    r1 = [x for x in r1 if calls(x)]
    assert len(r1) == 1 and len(r2) == 1 and calls(r2[0]), (r1, r2)
    r280c0, r283bd = r1[0], r2[0]
    hits = [m.group(1) for m in re.finditer(          # cseg_2573C: 10EA8C = 1; call; 10EAE1 = 0; 10EADD = 0; 10EEAB = 0
        rb'\x66\xc7\x05.{4}\x01\x00\xe8.{4}\x66\xc7\x05.{4}\x00\x00\x66\xc7\x05(.{4})\x00\x00\x66\xc7\x05.{4}\x00\x00', d1, re.S)]
    stage_g = struct.unpack('<I', hits[0])[0]          # (the first of two: cseg_2573C precedes the other one)
    q = sites['qual']
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update({'UQ_IN': syms['UQ_IN'], 'UQ_OUT': syms['UQ_OUT'], 'uq_season': syms['uq_season'],
                    'UQREC': (2, bss_at + cw.UQ_BSS), 'STAND': q['STAND'], 'CUPREC': q['CUPREC'],
                    'HOLD_CC': q['HOLD_CC'], 'HOLD_CWC': q['HOLD_CWC'], 'HOLD_UEFA': q['HOLD_UEFA'],
                    'A0R': q['A0R'], 'HOLDTAB': (1, cw.LABELS['HOLDTAB']),
                    'ADDREC': (1, cw.LABELS['sites']['addrec']), 'W_QON': (1, cw.LABELS['w_qon']),
                    'UC_N': (1, uc.LABELS['UC_N']), 'UC_C': (1, uc.LABELS['UC_C']), 'UC_G': (1, uc.LABELS['uc_g']), 'UC_KC': (1, uc.LABELS['uc_kc']),
                    'CB': (2, sites['tmd'] + uc.CB_OFF), 'KHIST': (0, uc.KHIST), 'CHIST': (0, uc.CHIST),
                    'RING': (0, uc.RING), 'SEL': (2, sites['sel']), 'Q_LIST': (0, Q_LIST),
                    'QS0': (1, STRUCTS[0]), 'QS1': (1, STRUCTS[1]), 'QS2': (1, STRUCTS[2]),
                    'FORCE': (0, ROUNDS.index(os.environ['UEFAQ_FORCE']) if os.environ.get('UEFAQ_FORCE') else 0),
                    'WIN_BYTES': (0, 'db ' + ', '.join(str(WIN.get(r.split()[1][:2], 0)) for r in ROUNDS)),
                    'UQ_S': syms['UQ_S'], 'UQ_R': syms['UQ_R'], 'uq_resolve': syms['uq_resolve'],
                    'STATE': (2, sites['tmd'] + uc.CB_OFF + uc.SIZE), 'SLOT3': (2, sites['slot3']),
                    'E092F': (2, sites['e092f']), 'CUP_KIND': (2, sites['cup_kind']), 'C8B2D3': (1, sites['c8b2d3']),
                    'D0R': (2, sites['a0'] - 32), 'D1R': (2, sites['a0'] - 28), 'D2R': (2, sites['a0'] - 24),
                    'QID0': (0, QIDS[0]), 'D7_BASE': (0, D7_BASE[0]),
                    'WCC': (2, sites['bss'] + cw.B_CUPS), 'WCWC': (2, sites['bss'] + cw.B_CUPS + 160),
                    'WUEFA': (2, sites['bss'] + cw.B_CUPS + 320), 'C8EA56': (1, c8ea56), 'STAGE_G': (2, stage_g), 'CAL': (2, cal), 'CAL_CUR': (2, cal_cur),
                    'R280C0': (1, r280c0), 'R283BD': (1, r283bd), 'DIY': (2, sites['diy']),
                    'DIYCOPY': (2, sites['diycopy'])})
    symbols.update({k: (0, v) for k, v in slay.items()})
    glue = (end + 15) & ~15
    code, fix = nasmcave.assemble(ASM, glue, symbols)
    lab = nasmcave.labels(ASM, glue, symbols)
    lab.update(_locals(ASM, glue, symbols, ('uq_fill.ran', 'uq_fill.done')))
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    rel = lambda a, to: struct.pack('<i', to - (a + 5))
    for stub, target in (('w_q_cq', 'uq_country'), ('w_q_fill', 'uq_fill'), ('w_q_post', 'uq_post')):
        a = cw.LABELS[stub]
        p.put(1, a, b'\xe9' + rel(a, lab[target]))
    p.put(1, site + 1, rel(site, lab['uq_daily']))     # (a relative call: no fixup to move)
    for hk, stub in ((r280c0, 'uq_rn1'), (r283bd, 'uq_rn2')):     # `sub word [Dn], 1` (8 B, a fixup) -> jmp
        p.remove(1, hk + 3)
        p.put(1, hk, b'\xe9' + rel(hk, lab[stub]) + b'\x90' * 3)
    print(f"exe: uefaq state obj2+{symbols['STATE'][1]:#x} (k +{slay['S_K']:#x}, res +{slay['S_RES']:#x}), slot 3 "
          f"obj2+{sites['slot3']:#x}, uq_daily {lab['uq_daily']:#x}")
    print('exe: uefaq labels ' + ' '.join(f'{k} {lab[k]:#x}' for k in ('uq_country', 'uq_fill', 'uq_fill.ran', 'uq_fill.done', 'uq_post')))
    print(f'exe: UEFA qualifying rounds: C obj1+{at:#x}..{end:#x}, glue ..{glue + len(code):#x}, '
          f'bss obj2+{bss_at:#x} ({bss} B + {cw.UQ_RECS} records)')
    return glue + len(code)


def _locals(src, org, symbols, names):
    """Addresses of local labels (nasmcave.labels lists global ones only): for the harness's breakpoints."""
    import re
    import subprocess
    import tempfile
    head = ['bits 32', f'org {org:#x}']
    for name, (obj, off) in symbols.items():
        head.append(f'%define {name} {off}' if obj == 0 else f'%define {name} {off:#x}')
    with tempfile.TemporaryDirectory() as t:
        asm, out, mp = (os.path.join(t, n) for n in ('c.asm', 'c.bin', 'c.map'))
        open(asm, 'w').write('\n'.join(head) + f'\n[map symbols {mp}]\n' + src)
        subprocess.run(['nasm', '-f', 'bin', '-o', out, asm], check=True, capture_output=True)
        text = open(mp).read()
    found = {m.group(2): int(m.group(1), 16) for m in re.finditer(r'^\s*([0-9A-F]+)\s+[0-9A-F]+\s+(\S+)\s*$', text, re.M)}
    return {n: found[n] for n in names}
