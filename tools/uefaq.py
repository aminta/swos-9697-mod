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
    cld
    call uq_season
.ran:
    xor ebx, ebx                        ; the three league phases into the CC / CWC / UEFA lists
.o:
    xor edx, edx
.o1:
    cmp dl, [UQ_OUT + O_N + ebx]
    jae .on
    imul eax, ebx, 80
    movzx eax, word [UQ_OUT + O_LS + eax + edx*2]
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
    pop es
    popad
.r0:
    ret

UQ_HP: dd HOLD_CC, HOLD_CWC, HOLD_UEFA
UQ_V: dd 0, 0
UQ_E: dw 0
'''


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
    lay = struct.unpack('<13I', p.get(1, syms['UQ_LAYOUT'][1], 52))
    keys = ('L_PRESENT', 'L_EPS', 'L_HOLD', 'L_NCLUB', 'L_LEAGUE', 'L_CUP', 'L_CLUB', 'CSZ', 'O_N', 'O_LS', 'O_STATUS',
            'IN_SIZE', 'NC')
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
                    'RING': (0, uc.RING)})
    glue = (end + 15) & ~15
    code, fix = nasmcave.assemble(ASM, glue, symbols)
    lab = nasmcave.labels(ASM, glue, symbols)
    lab.update(_locals(ASM, glue, symbols, ('uq_fill.ran', 'uq_fill.done')))
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    rel = lambda a, to: struct.pack('<i', to - (a + 5))
    for stub, target in (('w_q_cq', 'uq_country'), ('w_q_fill', 'uq_fill')):
        a = cw.LABELS[stub]
        p.put(1, a, b'\xe9' + rel(a, lab[target]))
    print('exe: uefaq labels ' + ' '.join(f'{k} {lab[k]:#x}' for k in ('uq_country', 'uq_fill', 'uq_fill.ran', 'uq_fill.done')))
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
