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
    movzx eax, word [esi]               ; club coefficient: 5 seasons (units)
    call UC_G
    xor edx, edx
    cmp eax, 2000
    jae .k2
    xor ecx, ecx
.k:
    imul esi, ecx, 4000
    movzx esi, word [CB + KHIST + esi + eax*2]
    add edx, esi
    inc ecx
    cmp ecx, 5
    jb .k
.k2:
    mov [edi + 4], edx
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
    jmp .mn
.mf:
    inc ecx
    mov [UQ_IN + L_MANAGER], cx
.mn:
    mov al, [UQ_FORCE]
    mov [UQ_IN + L_FORCE], al
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
    inc eax                             ; its record after the season end's checks (w_q_post), unless the
    xor ebx, ebx                        ; opponent is in a league phase already
.q2:
    movzx ecx, byte [UQ_OUT + O_N + ebx]
    imul esi, ebx, 80
    lea esi, [UQ_OUT + O_LS + esi]
.q3:
    test ecx, ecx
    jz .q4
    cmp ax, [esi]
    je .qx
    add esi, 2
    dec ecx
    jmp .q3
.q4:
    inc ebx
    cmp ebx, 3
    jb .q2
    mov [UQ_PEND], ax
.qx:
    pop es
    popad
.r0:
    ret

uq_post:                                ; careerworld w_q_post (after the season end's last record count check):
    cmp word [UQ_PEND], 0               ; the record of the career club's first opponent
    je .r
    pushad
    movzx eax, word [UQ_PEND]
    mov word [UQ_PEND], 0
    dec eax
    imul eax, eax, 2ACh
    add eax, UQREC
    mov [A0R], eax
    call ADDREC
    popad
.r:
    ret

UQ_HP: dd HOLD_CC, HOLD_CWC, HOLD_UEFA
UQ_QS: dd QS0, QS1, QS2
UQ_PEND: dw 0
UQ_FORCE: db FORCE
UQ_WIN: WIN_BYTES
UQ_V: dd 0, 0
UQ_E: dw 0
'''


STRUCTS_AT = 0x1F00             # the 3 contests (obj1, after the C code and the glue in uefaq's two pages)
QIDS = (0x7C, 0x7D, 0x7E)       # contest ids (mkseason.RESERVED_IDS): CL / EL / UECL qualifying tie
Q_NAME, Q_LIST = 16, 24         # offsets in a contest: its 2 name dwords, its 2-club list
NAMES = {'it': 'PRELIM. ', 'en': 'QUAL. ', 'fr': 'QUALIF. ', 'de': 'QUALI. '}
CUPS = (b'CHAMPIONS LEAGUE', b'EUROPA LEAGUE', b'CONFERENCE LEAGUE')
STRUCTS = []
# the legs' dates per round (eighths of a month from January; the second leg 2 later): Q1 early July, Q2 late
# July, Q3 early August, play-off late August (the league phases start in September)
WIN = {'Q1': 0x31, 'Q2': 0x35, 'Q3': 0x39, 'PO': 0x3C}
ROUNDS = ['CL LS', 'CL PO', 'CL POnc', 'CL Q3', 'CL Q3nc', 'CL Q2', 'CL Q2nc', 'CL Q1', 'EL LS', 'EL PO', 'EL Q3',
          'EL Q3ch', 'EL Q2', 'EL Q1', 'CO LS', 'CO PO', 'CO POch', 'CO Q3', 'CO Q3ch', 'CO Q2', 'CO Q2ch', 'CO Q1']


def structs(p, area, lang, at):
    """The career club's qualifying tie, one contest per competition: a type-1 cup of 2 clubs, one round of two
    legs (as sacups' Intercontinental), list empty until a season end puts the club and its opponent in."""
    import sacups
    d2 = p.le.obj_bytes(2)
    cwc = sacups.unique(d2, sacups.CWC_HDR)
    out = []
    for cid, cup in zip(QIDS, CUPS):
        body = sacups.knockout16(d2[cwc:cwc + 28], cid, 2, (0x94,))
        body[3], body[4] = WIN['Q1'], WIN['Q1'] + 2
        assert len(body) == Q_NAME and body[5] + 5 == Q_NAME and body[7] + 7 == Q_LIST
        rel = area.add(NAMES[lang].encode() + cup + b'\0') - sacups.STR_BASE
        p.put(1, at, bytes(body) + struct.pack('<II', rel, rel) + bytes(4))
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
    q = sites['qual']
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update({'UQ_IN': syms['UQ_IN'], 'UQ_OUT': syms['UQ_OUT'], 'uq_season': syms['uq_season'],
                    'UQREC': (2, bss_at + cw.UQ_BSS), 'STAND': q['STAND'], 'CUPREC': q['CUPREC'],
                    'HOLD_CC': q['HOLD_CC'], 'HOLD_CWC': q['HOLD_CWC'], 'HOLD_UEFA': q['HOLD_UEFA'],
                    'A0R': q['A0R'], 'HOLDTAB': (1, cw.LABELS['HOLDTAB']),
                    'ADDREC': (1, cw.LABELS['sites']['addrec']), 'W_QON': (1, cw.LABELS['w_qon']),
                    'UC_N': (1, uc.LABELS['UC_N']), 'UC_C': (1, uc.LABELS['UC_C']), 'UC_G': (1, uc.LABELS['uc_g']),
                    'CB': (2, sites['tmd'] + uc.CB_OFF), 'KHIST': (0, uc.KHIST), 'CHIST': (0, uc.CHIST),
                    'RING': (0, uc.RING), 'SEL': (2, sites['sel']), 'Q_LIST': (0, Q_LIST),
                    'QS0': (1, STRUCTS[0]), 'QS1': (1, STRUCTS[1]), 'QS2': (1, STRUCTS[2]),
                    'FORCE': (0, ROUNDS.index(os.environ['UEFAQ_FORCE']) if os.environ.get('UEFAQ_FORCE') else 0),
                    'WIN_BYTES': (0, 'db ' + ', '.join(str(WIN.get(r.split()[1][:2], 0)) for r in ROUNDS))})
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
