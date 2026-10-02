"""Argentina 1996-97: Torneo Apertura 1996 and Torneo Clausura 1997 (session 28p, for 2.1).

Davide's decisions (notes/STATUS.md 28p): two tournaments in one season, relegation by "promedio", Nacional B unchanged,
SA cup qualifiers from the aggregate table. The engine has one league per division, so the Primera's double round-robin is
shown as two tournaments: division 0 is named TORNEO APERTURA; when its first cycle ends (19 rounds: every club has played
n - 1 matches and one cycle is left, DIY [5Fh] == 1) arg_after records the Apertura champion, zeroes the 20 table entries and
renames the running league TORNEO CLAUSURA (at the first match of the second cycle, session 28p T12). Steps still to come: aggregate + promedio + save trailer + message/history.
Sources: RSSSF arg97 (Apertura 1996, Clausura 1997), es.wikipedia "Campeonato de Primera Division 1996-97 (Argentina)".
"""
import re
import struct

import nasmcave

FILE = 43
LEAGUE_SIG = bytes((0x56, 0, 0x2B, 0x40, 0x20, 0, 0, 0, 0, 2, 2, 3, 0x35))
NAMES = [(b'TORNEO APERTURA', b'APERTURA'), (b'NACIONAL B', b'NACIONAL B')]
CLAUSURA = b'TORNEO CLAUSURA'

ASM = r'''
; arg_round: replaces `mov dword [A0], offset DIY_competitionStart` at the start of cseg_8922B, the per-match counters of a
; league (every match of the division goes through it, played or simulated). The first match of the second cycle (one
; cycle left, matchday 0, no match counted yet in it) = the start of the Clausura: the table still holds the final Apertura.
arg_round:
    mov dword [A0], DIY
    pushad
    cmp byte [DIY + 2Dh], ARG_ID        ; the Argentine league...
    jne .x
    cmp word [DIY + 5Fh], 1             ; one cycle left
    jne .x
    cmp word [DIY + 5Bh], 0             ; first match of a matchday
    jne .x
    cmp word [DIY + 1CBh], 0            ; first matchday of the cycle
    jne .x
    movzx eax, word [DIY + 6Dh]         ; top of the sorted table: its team must be a Primera club (division 0)
    mov esi, [DIY + eax + 2B3h]
    add esi, [SELTEAMS]
    cmp byte [esi], ARG_FILE
    jne .x
    cmp byte [esi + 25], 0
    jne .x
    movzx ecx, word [DIY + 31h]         ; clubs
    lea edx, [ecx - 1]                  ; matches of a cycle
    xor ebx, ebx
.chk:
    movzx eax, word [DIY + 6Dh + ebx * 2]
    cmp [DIY + eax + 2B7h], dx          ; every club has played the Apertura (not reset yet)
    jne .x
    inc ebx
    cmp ebx, ecx
    jb .chk
    mov ax, [esi]                       ; Apertura champion
    mov [APERTURA_CHAMP], ax
    xor ebx, ebx
.zero:
    movzx eax, word [DIY + 6Dh + ebx * 2]
    lea edi, [DIY + eax + 2B7h]         ; played, won, drawn, lost, for, against, points
    push ecx
    mov ecx, 7
    xor eax, eax
    rep stosw
    pop ecx
    inc ebx
    cmp ebx, ecx
    jb .zero
    mov dword [DIY + 27h], CLAUSURA_NAME
    lea esi, [DIY + 4]                  ; the name text the game shows (built at season start from the struct name, maybe
    mov ecx, 23h - 8                    ; with the country before it): APERTURA -> CLAUSURA, same length
.find:
    cmp dword [esi], 'APER'
    jne .next
    cmp dword [esi + 4], 'TURA'
    jne .next
    mov dword [esi], 'CLAU'
    mov dword [esi + 4], 'SURA'
    jmp .rec
.next:
    inc esi
    loop .find
.rec:                                   ; the manager's record of this season (if his club plays the Primera)
    push dword [A0]                     ; (A0 = DIY for the rest of cseg_8922B; D0 used by GetCurrentSeasonPointer)
    push dword [D0]
    call GETSEASON
    mov esi, [A0]
    cmp dword [esi + 16h], APERTURA_OFF ; leagueStringOffset
    jne .r
    mov dword [esi + 16h], CLAUSURA_OFF
.r:
    pop dword [D0]
    pop dword [A0]
.x:
    popad
    ret
align 2
APERTURA_CHAMP: dw 0FFFFh
'''


def _refs(p, lo):
    import finals97
    return finals97._refs(p, lo)


def patch(p, area, str_base, at, site_b):
    """Named Argentine struct (new obj2 page) + arg_round at obj1:at (hook at the start of cseg_8922B); site_b unused."""
    import sacups
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1
    nd = d2[lo + 9]
    body = bytearray(d2[lo:lo + 13 + 6 * nd + 1])
    body[5] = 13 + 6 * nd + 1 - 5                       # names right after the divisions
    offs = []
    for long, short in NAMES:
        offs.append(area.add(long + b'\0') - str_base)
        body += struct.pack('<II', offs[-1], area.add(short + b'\0') - str_base)
    new = area.add(bytes(body))
    refs = _refs(p, lo)
    assert refs
    for objn, off in refs:
        p.retarget(objn, off, 2, new)
    clausura = area.add(CLAUSURA + b'\0')
    d1 = p.le.obj_bytes(1)
    regs = sacups.regs(d1)
    a0 = regs['D7'] + 4
    A = {n: a0 + 4 * i for i, n in enumerate(('A0', 'A1', 'A2', 'A3', 'A4'))}
    e = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xc7\x05' + e(A['A4']) + rb'(.{4})\x8b\x35' + e(A['A4']) + rb'\x66\x8b\x46\x4f', d1, re.S)]
    assert len(m) == 1
    diy = struct.unpack('<I', m[0].group(1))[0]
    # cseg_8922B: mov [A0], offset DIY; mov esi,[A1]; add word [esi+2B7h],1; mov esi,[A2]; add word [esi+2B7h],1
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + e(A['A0']) + e(diy) + rb'\x8b\x35' + e(A['A1'])
                                        + rb'\x66\x83\x86\xb7\x02\x00\x00\x01\x8b\x35' + e(A['A2']), d1)]
    assert len(m) == 1, m
    site = m[0]
    m = {struct.unpack('<I', x.group(1))[0] for x in re.finditer(rb'\x8b\x35' + e(A['A1']) + rb'\x8b\x86\xb3\x02\x00\x00\xa3'
                                                                  + e(A['A1']) + rb'\xa1(.{4})\x01\x05' + e(A['A1']), d1, re.S)}
    assert len(m) == 1
    sel = m.pop()
    # InitializeNewSeason: call GetCurrentSeasonPointer; mov eax,[DIY+27h]; sub eax, offset aChairmanScenes;
    # mov esi,[A0]; mov [esi+16h] (leagueStringOffset), eax
    m = [x for x in re.finditer(rb'\xe8(.{4})\xa1(.{4})\x2d(.{4})\x8b\x35' + e(A['A0']) + rb'\x89\x46\x16', d1, re.S)]
    assert len(m) == 1
    getseason = m[0].start() + 5 + struct.unpack('<i', m[0].group(1))[0]
    symbols = {'DIY': (2, diy), 'A0': (2, A['A0']), 'SELTEAMS': (2, sel), 'ARG_ID': (0, LEAGUE_SIG[0]),
               'D0': (2, regs['D7'] - 28), 'GETSEASON': (1, getseason), 'APERTURA_OFF': (0, offs[0]),
               'CLAUSURA_OFF': (0, clausura - str_base),
               'ARG_FILE': (0, FILE), 'CLAUSURA_NAME': (2, clausura)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.remove(1, site + 2)                               # the replaced mov holds two absolute addresses
    p.remove(1, site + 6)
    p.put(1, site, b'\xe8' + struct.pack('<i', labels['arg_round'] - (site + 5)) + b'\x90' * 5)
    print(f'exe: Argentina Apertura/Clausura: struct obj2+{new:#x}, counters obj1+{site:#x}, code obj1+{at:#x} '
          f'({len(code)} B)')
    return (at + len(code) + 15) & ~15
