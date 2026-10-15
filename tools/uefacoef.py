"""Simulated UEFA coefficients in a league-phase career world (world 2025-26; rules of 2024-25 .. 2026-27).

Points in eighths (units): a win 16, a draw 8 (league phase); Champions League league-phase participation 48;
league-phase ranking bonus (place 24 up: CL / EL 0.25 a place = 2 units; Conference League 0.125 for places 9-24,
then 0.25); each knockout round reached from the round of 16: CL 1.5, EL 1, UECL 0.5 (12 / 8 / 4 units).
Knockout matches are not seen one by one: a tie gives its winner 3 points and its loser 1 (two legs), the final's
winner 2. A club's coefficient = its points of the last 5 seasons; an association's season = its clubs' points /
its clubs (in thousandths, truncated), its coefficient = 5 seasons.

Block (saved: the .CAR fixed part's 80-record area, unused by a big world after the W1 block): CB = tmdFileBuffer +
0x3800. Season end (cseg_91428: cseg_936C0 expands the place lists, then the three cups end, simulations included,
then the qualifiers country by country): at the first qualifier (careerworld w_q_cb) the finals, the season values,
the 5-season ring, the ranking of the world's UEFA countries (those of the UEFA-slot place list) and the three
working place lists rewritten by rank (LP_CLN / LP_ELN / LP_UEN places per rank). Pots (lp36 lp_mkdraw): the clubs'
coefficients (the squad value breaks ties), the Champions League holder first. Seeds at career start: the real
association coefficients (5 seasons) and the clubs' coefficients at the 2025-26 draws (pack.json uefa_coef).
"""
import struct

CB_OFF = 0x3800                 # in tmdFileBuffer (the W1 block ends at 0x3482)
MARK, RING, DONE = 0, 2, 3
CTEAMS, CPTS, CHIST = 0x10, 0x110, 0x510               # 256 B, 256 dd, 5 x 256 dd (thousandths of points)
KPTS, KHIST = 0x1910, 0x28B0                           # 2000 dw, 5 x 2000 dw (units)
PREV, FIN = 0x76D0, 0x773C                             # 3 x (dd count + 16 dw), 3 x 2 dw
SIZE = 0x7748
assert CB_OFF + SIZE <= 80 * 684

LP_CLN = [5, 5, 4, 4, 3, 2, 2, 2] + [1] * 7            # places per rank: Champions League (34 + its holder + the EL winner)
LP_ELN = [2] * 12 + [1] * 11                           # Europa League (35 + the Conference League winner)
LP_UEN = [1] * 36                                      # Conference League (36)

ASM = '''
uc_ok:                                  ; al = contest id: ZF = 1 for a cup (0..2) of a league-phase world career
    cmp al, 2
    ja .no
    call W_LPW
    jne .r
    push ebp
    mov ebp, CB
    cmp word [ebp + MARK], 4355h        ; 'UC': the block is there (an older save of the world gets one now)
    pop ebp
    je .r
    call uc_init
    cmp eax, eax
.r:
    ret
.no:
    cmp esp, 0
    ret

uc_g:                                   ; eax = team word (file, ordinal) -> eax = global number
    push edx
    movzx edx, al
    movzx eax, ah
    add ax, [TCN + edx*2]
    pop edx
    ret

uc_add:                                 ; eax = team word, ecx = units: this season's club and country points
    pushad
    mov ebp, CB
    movzx edx, al
    add [ebp + CPTS + edx*4], ecx
    call uc_g
    cmp eax, 2000
    jae .x
    add [ebp + KPTS + eax*2], cx
.x:
    popad
    ret

uc_init:                                ; zero the block, the seeds (5 seasons of the associations, the clubs)
    pushad
    mov edi, CB
    mov ecx, SIZE
    xor eax, eax
.z:
    mov [edi], al
    inc edi
    dec ecx
    jnz .z
    mov ebp, CB
    mov word [ebp + MARK], 4355h
    mov esi, UC_SEEDC
.c:
    movzx edx, byte [esi]               ; country file, 0 = end
    test edx, edx
    jz .k
    xor ecx, ecx
.c1:
    mov eax, [esi + 1 + ecx*4]
    imul ebx, ecx, 1024
    add ebx, edx
    mov [ebp + CHIST + ebx*4 - 0], eax  ; (CHIST + s*1024 + c*4)
    inc ecx
    cmp ecx, 5
    jb .c1
    add esi, 21
    jmp .c
.k:
    mov esi, UC_SEEDK
.k1:
    movzx eax, word [esi]               ; team word, 0 = end
    test eax, eax
    jz .x
    call uc_g
    cmp eax, 2000
    jae .k3
    mov dx, [esi + 2]                   ; units per season
    xor ecx, ecx
.k2:
    imul ebx, ecx, 4000
    add ebx, ebp
    mov [ebx + KHIST + eax*2], dx
    inc ecx
    cmp ecx, 5
    jb .k2
.k3:
    add esi, 4
    jmp .k1
.x:
    popad
    ret
'''
# (CHIST + s*1024 + c*4: ebx = s*1024 + c, so [ebp + CHIST + ebx*4] would be s*4096: fixed below in Python by the
# layout constant CHS = 1024 dwords per season)
ASM = ASM.replace("""    imul ebx, ecx, 1024
    add ebx, edx
    mov [ebp + CHIST + ebx*4 - 0], eax  ; (CHIST + s*1024 + c*4)""", """    imul ebx, ecx, 256
    add ebx, edx
    mov [ebp + CHIST + ebx*4], eax      ; CHIST + (s * 256 + c) * 4""")

ASM += '''
uc_new:                                 ; replaces `call w_cups` (career start in a world): a fresh block
    call W_CUPS
    pushad
    call W_LPW
    jne .x
    call uc_init
.x:
    popad
    ret

uc_start:                               ; lp36 lp_cb_start (league start, after the draw)
    pushad
    mov al, [DIYCOPY + 2Dh]
    call uc_ok
    jne .r
    movzx ebx, al
    mov ebp, CB
    imul eax, ebx, 36
    mov dword [ebp + PREV + eax], 0     ; no knockout round of this cup yet
    mov byte [ebp + DONE], 0            ; (a season is running: its end will be counted)
    xor ecx, ecx
.l:
    movzx eax, word [DIY + 12Dh + ecx*2]
    movzx edx, al
    inc byte [ebp + CTEAMS + edx]       ; the association's clubs this season
    test ebx, ebx
    jnz .n
    push ecx
    mov ecx, 48                         ; Champions League league phase: 6 points
    call uc_add
    pop ecx
.n:
    inc ecx
    cmp ecx, 36
    jb .l
.r:
    popad
    ret

uc_res:                                 ; lp36 lp_cb_res (a league-phase result: A3 home row, A4 away row, D1 / D2)
    mov al, [DIY + 2Dh]
    call uc_ok
    jne .r
    mov eax, [A3R]
    sub eax, DIY
    xor edx, edx
    mov ecx, 18
    div ecx
    movzx esi, word [DIY + 12Dh + eax*2]    ; home team word
    mov eax, [A4R]
    sub eax, DIY
    xor edx, edx
    div ecx
    movzx edi, word [DIY + 12Dh + eax*2]    ; away team word
    mov ax, [D1R]
    cmp ax, [D2R]
    je .d
    ja .h
    mov eax, edi
    mov ecx, 16
    jmp uc_add
.h:
    mov eax, esi
    mov ecx, 16
    jmp uc_add
.d:
    mov eax, esi
    mov ecx, 8
    call uc_add
    mov eax, edi
    jmp uc_add
.r:
    ret

uc_gend:                                ; lp36 lp_cb_gend (end of the league phase: LP_ORD = rows, best first)
    pushad
    mov al, [DIYCOPY + 2Dh]
    call uc_ok
    jne .r
    movzx ebx, al
    xor ecx, ecx                        ; place p (0-based)
.l:
    mov edx, 24
    sub edx, ecx                        ; 24 - p
    jle .n
    cmp ebx, 2
    je .ue
    add edx, edx                        ; CL / EL: 0.25 a place
    jmp .a
.ue:
    cmp ecx, 8                          ; UECL: 0.125 for places 9-24, then 0.25
    jae .a
    mov edx, 8
    sub edx, ecx
    add edx, edx
    add edx, 16
.a:
    movzx eax, byte [LP_ORD + ecx]
    movzx eax, word [DIYCOPY + 99h + eax*2]
    push ecx
    mov ecx, edx
    call uc_add
    pop ecx
.n:
    inc ecx
    cmp ecx, 36
    jb .l
.r:
    popad
    ret

uc_draw:                                ; lp36 lp_cb_draw (jumped to at lp_draw's end: esi = DIY buffer, ecx = clubs)
    pushad
    cmp ecx, 16
    ja .r
    mov al, [esi + 2Dh]
    call uc_ok
    jne .r
    movzx ebx, al
    mov ebp, CB
    imul edi, ebx, 36
    lea edi, [ebp + PREV + edi]         ; this cup's previous round: dd count, 16 team words
    mov [UC_N], ecx
    xor ecx, ecx                        ; the previous round's ties: winner (in this round) 3 points, loser 1
.p:
    cmp ecx, [edi]
    jae .b
    movzx eax, word [edi + 4 + ecx*2]
    mov edx, 8
    push ecx
    xor ecx, ecx
.p1:
    cmp ecx, [UC_N]
    jae .p2
    push eax
    movzx eax, byte [esi + 59h + ecx]
    mov ax, [esi + 99h + eax*2]
    cmp ax, [esp]
    pop eax
    je .p3
    inc ecx
    jmp .p1
.p3:
    mov edx, 24
.p2:
    mov ecx, edx
    call uc_add
    pop ecx
    inc ecx
    jmp .p
.b:
    mov eax, [UC_N]                     ; this round's clubs: the reach bonus from the round of 16 (stage 3)
    mov [edi], eax
    xor ecx, ecx
.b1:
    movzx eax, byte [esi + 59h + ecx]
    mov ax, [esi + 99h + eax*2]
    mov [edi + 4 + ecx*2], ax
    cmp word [esi + 53h], 2
    jb .b2
    push ecx
    movzx ecx, byte [UC_RB + ebx]
    call uc_add
    pop ecx
.b2:
    inc ecx
    cmp ecx, [UC_N]
    jb .b1
    cmp dword [UC_N], 2                 ; the final: its two clubs (the winner gets its 2 points at the season end)
    jne .r
    mov eax, [edi + 4]
    mov [ebp + FIN + ebx*4], eax
.r:
    popad
    ret

uc_str:                                 ; lp36 lp_cb_str: eax = squad value, edx = team index -> eax = the pot key
    push edx
    push ebx
    push ecx
    push esi
    push ebp
    mov esi, eax
    mov al, [DIYCOPY + 2Dh]
    call uc_ok
    jne .plain
    movzx ebx, al
    movzx eax, word [DIY + 12Dh + edx*2]
    test ebx, ebx
    jnz .c
    cmp ax, [HOLD_CC]                   ; the Champions League holder: pot 1
    jne .c
    mov eax, 0FFFFFFFFh
    jmp .x
.c:
    call uc_g
    cmp eax, 2000
    jae .plain
    mov ebp, CB
    xor ecx, ecx
    xor ebx, ebx
.s:
    imul edx, ecx, 4000
    add edx, ebp
    movzx edx, word [edx + KHIST + eax*2]
    add ebx, edx
    inc ecx
    cmp ecx, 5
    jb .s
    shl ebx, 10
    cmp esi, 1023
    jbe .v
    mov esi, 1023
.v:
    lea eax, [ebx + esi]
    jmp .x
.plain:
    mov eax, esi
.x:
    pop ebp
    pop esi
    pop ecx
    pop ebx
    pop edx
    ret

uc_final:                               ; careerworld w_q_cb: the first qualifier of the season end (cseg_93974: the
    pushad                              ; cups are over, simulations included; cseg_936C0 has expanded the place lists
    mov al, 0                           ; into the working lists, nothing taken yet)
    call uc_ok
    jne .x
    mov ebp, CB
    cmp byte [ebp + DONE], 0
    jne .x
    mov byte [ebp + DONE], 1
    xor ebx, ebx                        ; the finals' winners: 2 points
.f:
    mov eax, [ebp + FIN + ebx*4]
    test eax, eax
    jz .f2
    mov dx, [UC_HOLD + ebx*2]           ; (the holder variables' offsets, relative to HOLD_CC)
    movzx edx, dx
    mov dx, [HOLD_CC + edx]
    cmp ax, dx
    je .f1
    shr eax, 16
    cmp ax, dx
    jne .f2
.f1:
    mov ecx, 16
    call uc_add
.f2:
    mov dword [ebp + FIN + ebx*4], 0
    inc ebx
    cmp ebx, 3
    jb .f
    movzx ebx, byte [ebp + RING]        ; the season's values into the ring
    xor ecx, ecx
.c:
    movzx esi, byte [ebp + CTEAMS + ecx]
    xor eax, eax
    test esi, esi
    jz .c1
    mov eax, [ebp + CPTS + ecx*4]
    imul eax, eax, 125                  ; units / 8 * 1000
    xor edx, edx
    div esi
.c1:
    imul edx, ebx, 256
    add edx, ecx
    mov [ebp + CHIST + edx*4], eax
    mov dword [ebp + CPTS + ecx*4], 0
    mov byte [ebp + CTEAMS + ecx], 0
    inc ecx
    cmp ecx, 256
    jb .c
    imul edi, ebx, 4000
    add edi, ebp
    xor ecx, ecx
.k:
    mov ax, [ebp + KPTS + ecx*2]
    mov [edi + KHIST + ecx*2], ax
    mov word [ebp + KPTS + ecx*2], 0
    inc ecx
    cmp ecx, 2000
    jb .k
    inc ebx
    cmp ebx, 5
    jb .rg
    xor ebx, ebx
.rg:
    mov [ebp + RING], bl
    call W_REC                          ; ebx = the world record: [[ebx+28]] = the UEFA-slot place list (its countries)
    mov esi, [ebx + 28]
    mov esi, [esi]
    xor ecx, ecx                        ; the UEFA countries (each once in the UEFA-slot list), in its order
.u:
    mov al, [esi + ecx]
    cmp al, 0FFh
    je .u1
    mov [UC_C + ecx], al
    inc ecx
    jmp .u
.u1:
    mov [UC_N], ecx
    xor ecx, ecx                        ; their coefficients (5 seasons)
.t:
    movzx edx, byte [UC_C + ecx]
    xor eax, eax
    xor edi, edi
.t1:
    imul esi, edi, 256
    add esi, edx
    add eax, [ebp + CHIST + esi*4]
    inc edi
    cmp edi, 5
    jb .t1
    mov [UC_T + ecx*4], eax
    inc ecx
    cmp ecx, [UC_N]
    jb .t
    mov ecx, 1                          ; insertion sort, best first (stable)
.s1:
    cmp ecx, [UC_N]
    jae .w
    mov al, [UC_C + ecx]
    mov esi, [UC_T + ecx*4]
    mov edx, ecx
.s2:
    test edx, edx
    jz .s3
    cmp esi, [UC_T + edx*4 - 4]
    jbe .s3
    mov edi, [UC_T + edx*4 - 4]
    mov [UC_T + edx*4], edi
    mov ah, [UC_C + edx - 1]
    mov [UC_C + edx], ah
    dec edx
    jmp .s2
.s3:
    mov [UC_C + edx], al
    mov [UC_T + edx*4], esi
    inc ecx
    jmp .s1
.w:
    mov esi, UC_CLN                     ; places per rank and cup (UC_A: CL, EL, UECL x 64 ranks)
    mov edi, UC_A
    mov ecx, 192
.w0:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .w0
    xor ecx, ecx                        ; capacity per rank: the top 9 of a league minus its clubs among the
.cp:                                    ; three holders (they are skipped by the qualifiers)
    mov al, [UC_C + ecx]
    mov dl, 9
    xor ebx, ebx
.cp1:
    mov si, [UC_HOLD + ebx*2]
    movzx esi, si
    cmp al, [HOLD_CC + esi]             ; (the holder word's low byte = its country file)
    jne .cp2
    dec dl
.cp2:
    inc ebx
    cmp ebx, 3
    jb .cp1
    mov [UC_CAP + ecx], dl
    inc ecx
    cmp ecx, 64
    jb .cp
    xor ecx, ecx                        ; too many places for a country: the excess (UECL first, then EL, CL)
.x0:                                    ; goes to the next ranked country with room, same cup
    cmp ecx, [UC_N]
    jae .xd
.x1:
    movzx eax, byte [UC_A + ecx]
    movzx edx, byte [UC_A + 64 + ecx]
    add eax, edx
    movzx edx, byte [UC_A + 128 + ecx]
    add eax, edx
    movzx edx, byte [UC_CAP + ecx]
    cmp eax, edx
    jbe .x5
    mov ebx, 128                        ; take one place from the last cup that has one
.x2:
    cmp byte [UC_A + ebx + ecx], 0
    jne .x3
    sub ebx, 64
    jns .x2
    jmp .x5
.x3:
    dec byte [UC_A + ebx + ecx]
    lea edi, [ecx + 1]
.x4:
    cmp edi, [UC_N]
    jae .x1                             ; (no room anywhere: the place is lost)
    movzx eax, byte [UC_A + edi]
    movzx edx, byte [UC_A + 64 + edi]
    add eax, edx
    movzx edx, byte [UC_A + 128 + edi]
    add eax, edx
    movzx edx, byte [UC_CAP + edi]
    cmp eax, edx
    jb .x4a
    inc edi
    jmp .x4
.x4a:
    inc byte [UC_A + ebx + edi]
    jmp .x1
.x5:
    inc ecx
    jmp .x0
.xd:
    mov esi, WORK_CC                    ; rewrite the working lists: places per rank (same lengths, FF-terminated)
    mov edi, UC_A
    call .fill
    mov esi, WORK_CWC
    mov edi, UC_A + 64
    call .fill
    mov esi, WORK_UEFA
    mov edi, UC_A + 128
    call .fill
.x:
    popad
    ret
.fill:                                  ; esi = place list (FF-terminated), edi = places per rank
    xor ecx, ecx                        ; rank
.f3:
    cmp byte [esi], 0FFh
    je .f5
    cmp ecx, 64
    jae .f5
    movzx edx, byte [edi + ecx]
    test edx, edx
    jnz .f3a
    inc ecx                             ; (a rank without places in this cup: the next one)
    jmp .f3
.f3a:
    mov al, [UC_C + ecx]
.f4:
    cmp byte [esi], 0FFh
    je .f5
    mov [esi], al
    inc esi
    dec edx
    jnz .f4
    inc ecx
    jmp .f3
.f5:
    ret

UC_RB: db 12, 8, 4                      ; knockout round reached (units)
UC_HOLD: dw 0, HOLD_CWC - HOLD_CC, HOLD_UEFA - HOLD_CC
UC_CLN: CLN_BYTES                       ; (64 ranks each, contiguous: copied into UC_A)
UC_ELN: ELN_BYTES
UC_UEN: UEN_BYTES
UC_A: times 192 db 0
UC_CAP: times 64 db 0
align 4
UC_N: dd 0
UC_T: times 64 dd 0
UC_C: times 64 db 0
UC_SEEDC: SEEDC_BYTES
UC_SEEDK: SEEDK_BYTES
'''


def patch(p, cave, worlds, sites):
    """worlds: mkseason.world_defs() (the league-phase ones are used); sites: careerworld LABELS / _qual_sites dict and
    the lp36 / careerworld addresses. Returns the cave end."""
    import nasmcave
    import lp36
    import careerworld as cw
    lpw = [w for w in worlds if any(w['cups'][k][0] == cw.LP_ROUNDS for k in ('cc', 'cwc', 'uefa'))]
    assert len(lpw) == 1, len(lpw)
    w = lpw[0]
    # the converter's places = the rank tables applied to the countries' initial order
    order = []
    for c in w['places']['uefa']:
        if c not in order:
            order.append(c)
    for key, tab in (('cc', LP_CLN), ('cwc', LP_ELN), ('uefa', LP_UEN)):
        want = [c for r, c in enumerate(order) for _ in range(tab[r] if r < len(tab) else 0)]
        assert w['places'][key] == want, (key, w['places'][key][:12], want[:12])
    seedc = b''
    for f, vals in w['coef']['countries']:
        seedc += bytes((f,)) + b''.join(struct.pack('<I', int(round(v * 1000))) for v in vals)
    seedc += b'\0'
    seedk = b''
    for (f, o), v in w['coef']['clubs']:
        seedk += struct.pack('<HH', f | o << 8, int(round(v * 8 / 5)))
    seedk += b'\0\0\0\0'
    db = lambda b: 'db ' + ', '.join(str(x) for x in b)
    q = sites['qual']
    a0 = sites['a0']
    symbols = {'CB': (2, sites['tmd'] + CB_OFF), 'TCN': (2, sites['tcn']), 'DIY': (2, sites['diy']),
               'DIYCOPY': (2, sites['diycopy']), 'HOLD_CC': q['HOLD_CC'], 'HOLD_CWC': q['HOLD_CWC'],
               'HOLD_UEFA': q['HOLD_UEFA'], 'A3R': (2, a0 + 12), 'A4R': (2, a0 + 16), 'D1R': (2, a0 - 28),
               'D2R': (2, a0 - 24), 'LP_ORD': sites['lp_ord'], 'W_LPW': (1, cw.LABELS['w_lpw']),
               'W_REC': (1, cw.LABELS['w_rec']), 'W_CUPS': (1, cw.LABELS['w_cups']),
               'MARK': (0, MARK), 'RING': (0, RING), 'DONE': (0, DONE), 'WORK_CC': q['WORK_CC'],
               'WORK_CWC': q['WORK_CWC'], 'WORK_UEFA': q['WORK_UEFA'], 'CTEAMS': (0, CTEAMS), 'CPTS': (0, CPTS), 'CHIST': (0, CHIST),
               'KPTS': (0, KPTS), 'KHIST': (0, KHIST), 'PREV': (0, PREV), 'FIN': (0, FIN), 'SIZE': (0, SIZE),
               'CLN_BYTES': (0, db((LP_CLN + [0] * 64)[:64])), 'ELN_BYTES': (0, db((LP_ELN + [0] * 64)[:64])),
               'UEN_BYTES': (0, db((LP_UEN + [0] * 64)[:64])), 'SEEDC_BYTES': (0, db(seedc)), 'SEEDK_BYTES': (0, db(seedk))}
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    lab = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    rel = lambda at, to: struct.pack('<i', to - (at + 5))
    for cb, target in (('lp_cb_start', 'uc_start'), ('lp_cb_res', 'uc_res'), ('lp_cb_gend', 'uc_gend'),
                       ('lp_cb_draw', 'uc_draw'), ('lp_cb_str', 'uc_str')):
        at = lp36.LABELS[cb]
        p.put(1, at, b'\xe9' + rel(at, lab[target]))
    d1 = bytes(p.get(1, 0, len(p.le.obj_bytes(1))))
    n = 0
    at = cw.LABELS['w_q_cb']
    p.put(1, at, b'\xe9' + rel(at, lab['uc_final']))
    for target, stub in ((cw.LABELS['w_cups'], 'uc_new'),):
        calls = [i for i in range(len(d1) - 5) if d1[i] == 0xE8
                 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == target and not cave <= i < cave + len(code)]
        assert len(calls) == 1, (stub, [hex(c) for c in calls])
        p.put(1, calls[0] + 1, rel(calls[0], lab[stub]))
        n += 1
    print(f'exe: UEFA coefficients: code obj1+{cave:#x}..{cave + len(code):#x}, block tmdFileBuffer+{CB_OFF:#x} '
          f'({SIZE} B), seeds {len(w["coef"]["countries"])} associations / {len(w["coef"]["clubs"])} clubs')
    return cave + len(code)
