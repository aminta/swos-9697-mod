"""4.0.5 the mod's slot-3 / slot-4 goals in the right counter (scorers report, Davide 31/10). After a match cseg_2F3AB
adds every scorer's goals to his record's counter +33 + the contest's DIY slot (+2Bh: 0 league, 1 cup 1, 2 cup 2, 3
the international cups; `movzx ebx, word [D7]; add [esi+ebx+6Dh], al`). The game never plays a slot-4 contest, the mod
does (dplay's / gplay's play-offs, play-outs, title play-offs, the NZ Grand Final, the national supercups, the Coppa
Italia Serie D): their goals went to +37 - not a goal counter but the player's form / reserve / trial mark
(PlayerFile.someFlag) - and were in no column and not in TOT. gplay's domestic slot-3 contests (the NZ championship
group, the Poule Scudetto: ids FC..FE, mkseason.RESERVED_IDS' dplay / gplay ones) went to INT.

gs_add replaces the two instructions (and gs_add1 the same in cseg_1C39F, a simulated result: one goal at a time,
the slot from [5FA18h]): slot 4 -> COP1 for a supercup, COP2 for the Coppa D (the current contest's
title, DIY+4, holds one of their names: build-time tables per exe language), else LEGA; slot 3 with id FC..FE ->
LEGA; any other slot as the game. Every remapped write (slot 4, slot 3 FC..FE) is kept in a 16-entry ring (GS_LOG, obj1: the harness reads it, no
test switch; gs_t counts all writes): db the slot, the counter used, the goals, the class (0 slot 4 -> LEGA, 1 supercup, 2 Coppa D, 3 slot 3 FC..FE,
4 as the game), +37 before / after, the counter before / after.
"""
import json
import os
import re
import struct

import nasmcave
import sacups

LOG = []
CD_NAMES = ('COPPA ITALIA SERIE D',)    # (cupd's default title; the pack's own names added at build time)

ASM = r"""
gs_add1:                                ; a simulated result's goal (cseg_1C39F): replaces `movzx ebx, word [D0];
    pushad                              ; add byte [esi+ebx+6Dh], 1` (D0 = the contest's slot)
    mov byte [gs_g], 1
    movzx ebx, word [D0_]
    jmp gs_slot
gs_add:                                 ; cseg_2F3AB (a match played): replaces `movzx ebx, word [D7]; add [esi+ebx+
    pushad                              ; 6Dh], al` (esi = [A0]: the scorer's record - 76, al = his goals)
    mov [gs_g], al
    movzx ebx, word [D7_]
gs_slot:
    mov [gs_g + 1], bl
    mov dl, 4
    cmp ebx, 4
    je .s4
    cmp ebx, 3
    jne .add
    mov cl, [DIY_ + 2Dh]                ; slot 3: dplay / gplay's domestic ids FC..FE -> LEGA
    cmp cl, 0FCh
    jb .add
    cmp cl, 0FEh
    ja .add
    xor ebx, ebx
    mov dl, 3
    jmp .add
.s4:
    xor ebx, ebx                        ; slot 4: LEGA, a supercup COP1, the Coppa D COP2
    xor edx, edx
    mov edi, GS_SC
    call gs_find
    jnz .ncd0
    inc ebx
    inc edx
    jmp .add
.ncd0:
    mov edi, GS_CD
    call gs_find
    jnz .add
    mov bl, 2
    mov dl, 2
.add:
    inc dword [gs_t]
    cmp dl, 4                           ; (the ring: the remapped writes only - a world's results day writes thousands)
    jne .log
    mov al, [gs_g]                      ; (the goals: al is not kept on the way here)
    add [esi + ebx + 6Dh], al
    popad
    ret
.log:
    mov edi, [gs_n]
    and edi, 15
    lea edi, [GS_LOG + edi * 8]
    mov cl, [gs_g + 1]
    mov [edi], cl
    mov [edi + 1], bl
    mov al, [gs_g]
    mov [edi + 2], al
    mov [edi + 3], dl
    mov cl, [esi + 6Dh + 4]
    mov [edi + 4], cl
    mov cl, [esi + ebx + 6Dh]
    mov [edi + 6], cl
    add [esi + ebx + 6Dh], al
    mov cl, [esi + 6Dh + 4]
    mov [edi + 5], cl
    mov cl, [esi + ebx + 6Dh]
    mov [edi + 7], cl
    inc dword [gs_n]
    popad
    ret
gs_find:                                ; ZF: the current contest's title holds one of the strings at edi (each NUL-
    push esi                            ; terminated, an empty one ends them)
.t: cmp byte [edi], 0
    je .no
    mov esi, DIYNAME
.p: xor ecx, ecx
.c: mov al, [edi + ecx]
    test al, al
    jz .yes
    cmp al, [esi + ecx]
    jne .np
    inc ecx
    jmp .c
.np:
    cmp byte [esi], 0
    je .ns
    inc esi
    jmp .p
.ns:
    inc edi
    cmp byte [edi - 1], 0
    jne .ns
    jmp .t
.no:
    or esp, esp
    pop esi
    ret
.yes:
    xor eax, eax
    pop esi
    ret
gs_g: db 0, 0, 0, 0
gs_t: dd 0
gs_n: dd 0
GS_LOG: times 128 db 0
"""


def names(lang):
    """(supercup names, Coppa D names) for the exe language: long and short, latin-1."""
    sc = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supercups2627.json')))
    s = []
    for k, v in sc.items():
        if not k.startswith('_'):
            s += (v['names'].get(lang) or v['names']['en'])
    cd = list(CD_NAMES)
    import mkseason
    for c in (mkseason.cupd_tables() if mkseason.worlds() else []):
        import gplay
        cd += list(gplay._name(c[5], lang, 'cup_d'))
    uniq = lambda xs: [x for i, x in enumerate(xs) if x and x not in xs[:i]]
    enc = lambda x: x if isinstance(x, bytes) else x.encode('latin-1')
    return [enc(x) for x in uniq(s)], [enc(x) for x in uniq(cd)]


def find(p):
    """The original exe's site in cseg_2F3AB: mov esi, [A0]; movzx ebx, word [D7]; add [esi+ebx+6Dh], al."""
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    P = lambda a: re.escape(struct.pack('<I', a))
    m = [x.start() for x in re.finditer(rb'\x8b\x35' + P(r['A0']) + rb'\x0f\xb7\x1d' + P(r['D7']) + rb'\x00\x44\x1e\x6d',
                                        d1, re.S)]
    assert len(m) == 1, ('cseg_2F3AB goals write-back', m)
    D0, A4 = r['D7'] - 28, r['A0'] + 16
    # cseg_1C39F (a simulated result, one goal): mov ax, [slot]; mov [D0], ax; mov esi, [A4]; movzx ebx, word [D0];
    # add byte [esi+ebx+6Dh], 1
    m1 = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\xa3' + P(D0) + rb'\x8b\x35' + P(A4) + rb'\x0f\xb7\x1d' +
                                         P(D0) + rb'\x80\x44\x1e\x6d\x01', d1, re.S)]
    assert len(m1) == 1, ('cseg_1C39F goal write-back', m1)
    import lp36
    return dict(at=m[0] + 6, at1=m1[0] + 18, D7=r['D7'], D0=D0, DIY=lp36._sites(p)['DIY'])


def patch(p, at, lang):
    """Code + tables at obj1:at; returns the end."""
    import lepatch
    s = find(lepatch.LEPatch(bytes(p.le.data)))
    a = s['at']
    assert bytes(p.get(1, a, 11))[:3] == b'\x0f\xb7\x1d' and bytes(p.get(1, a + 7, 4)) == b'\x00\x44\x1e\x6d', 'gs site'
    sc, cd = names(lang)
    tab = lambda xs: ', '.join(str(b) for x in xs for b in x + b'\0') + ', 0'
    a1 = s['at1']
    assert bytes(p.get(1, a1, 12))[:3] == b'\x0f\xb7\x1d' and bytes(p.get(1, a1 + 7, 5)) == b'\x80\x44\x1e\x6d\x01', 'gs site 1'
    sym = {'D7_': (2, s['D7']), 'D0_': (2, s['D0']), 'DIY_': (2, s['DIY']), 'DIYNAME': (2, s['DIY'] + 4)}
    src = ASM + f'GS_SC: db {tab(sc)}\nGS_CD: db {tab(cd)}\n'
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, a + 3)                                   # (movzx's D7 fixup)
    p.put(1, a, b'\xe8' + struct.pack('<i', lab['gs_add'] - (a + 5)) + b'\x90' * 6)
    p.remove(1, a1 + 3)
    p.put(1, a1, b'\xe8' + struct.pack('<i', lab['gs_add1'] - (a1 + 5)) + b'\x90' * 7)
    LABELS.update(lab)
    LOG.append(f'goalslot: slot-4 / domestic slot-3 goals -> LEGA / COP1 ({len(sc)} supercup names) / COP2 '
               f'({len(cd)} Coppa D names): gs_add obj1+{at:#x} ({len(code)} B), sites obj1+{a:#x} / +{a1:#x}, log obj1+{lab["GS_LOG"]:#x}')
    print('exe: ' + LOG[-1])
    return at + len(code)


LABELS = {}
