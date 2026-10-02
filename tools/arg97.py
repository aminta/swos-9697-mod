"""Argentina 1996-97: Torneo Apertura 1996 and Torneo Clausura 1997 (session 28p, for 2.1).

Davide's decisions (notes/STATUS.md 28p): two tournaments in one season, relegation by "promedio", Nacional B unchanged,
SA cup qualifiers from the aggregate table. The engine has one league per division, so the Primera's double round-robin is
shown as two tournaments: division 0 is named TORNEO APERTURA; when its first cycle ends (19 rounds: every club has played
n - 1 matches and one cycle is left, DIY [5Fh] == 1) arg_after records the Apertura champion, zeroes the 20 table entries and
renames the running league TORNEO CLAUSURA. Steps still to come: aggregate + promedio + save trailer + message/history.
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
; arg_after: replaces `call cseg_883DD` (table sort) at the end of a match in cseg_88A12. A1 = home team record.
arg_after:
    call SORT
    pushad
    cmp byte [DIY + 2Dh], ARG_ID        ; the Argentine league...
    jne .x
    mov esi, [A1]
    cmp byte [esi], ARG_FILE
    jne .x
    cmp byte [esi + 25], 0              ; ... division 0 (Primera)
    jne .x
    cmp word [DIY + 5Fh], 1             ; one cycle left = the Clausura (or the Apertura just ended)
    jne .x
    movzx ecx, word [DIY + 31h]         ; clubs
    lea edx, [ecx - 1]                  ; matches of a cycle
    xor ebx, ebx
.chk:
    movzx eax, word [DIY + 6Dh + ebx * 2]
    cmp [DIY + eax + 2B7h], dx          ; every club has played n - 1: the Apertura is over, not reset yet
    jne .x
    inc ebx
    cmp ebx, ecx
    jb .chk
    movzx eax, word [DIY + 6Dh]         ; Apertura champion (top of the sorted table)
    mov eax, [DIY + eax + 2B3h]
    add eax, [SELTEAMS]
    mov ax, [eax]
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
    """Named Argentine struct (new obj2 page) + arg_after at obj1:at; site_b = nz97's draw site (the sort call follows it)."""
    import sacups
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1
    nd = d2[lo + 9]
    body = bytearray(d2[lo:lo + 13 + 6 * nd + 1])
    body[5] = 13 + 6 * nd + 1 - 5                       # names right after the divisions
    for long, short in NAMES:
        body += struct.pack('<II', area.add(long + b'\0') - str_base, area.add(short + b'\0') - str_base)
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
    sort, diy = m[0].start(), struct.unpack('<I', m[0].group(1))[0]
    calls = [k for k in range(site_b, site_b + 0x200) if d1[k] == 0xE8 and k + 5 + struct.unpack_from('<i', d1, k + 1)[0] == sort]
    assert len(calls) == 1, calls
    site = calls[0]
    m = {struct.unpack('<I', x.group(1))[0] for x in re.finditer(rb'\x8b\x35' + e(A['A1']) + rb'\x8b\x86\xb3\x02\x00\x00\xa3'
                                                                  + e(A['A1']) + rb'\xa1(.{4})\x01\x05' + e(A['A1']), d1, re.S)}
    assert len(m) == 1
    sel = m.pop()
    symbols = {'SORT': (1, sort), 'DIY': (2, diy), 'A1': (2, A['A1']), 'SELTEAMS': (2, sel), 'ARG_ID': (0, LEAGUE_SIG[0]),
               'ARG_FILE': (0, FILE), 'CLAUSURA_NAME': (2, clausura)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', labels['arg_after'] - (site + 5)))     # relative call: no fixup
    print(f'exe: Argentina Apertura/Clausura: struct obj2+{new:#x}, sort call obj1+{site:#x}, code obj1+{at:#x} '
          f'({len(code)} B)')
    return (at + len(code) + 15) & ~15
