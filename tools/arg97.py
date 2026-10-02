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
; The Primera is recognised by its name pointer DIY+27h (TORNEO APERTURA / TORNEO CLAUSURA: no other league has them).
; The struct's names (long, short: the career game list shows the short one) change only at three moments: the switch
; (arg_round), every new season (arg_prebuild: APERTURA) and a career load (arg_load -> arg_names, phase of the saved
; league). T16/T17 also synced after every match: during career creation that showed CLAUSURA once.
arg_ours:                               ; ebp = league buffer; ZF = 1 if it is the Argentine Primera
    cmp dword [ebp + 27h], AP_LONG
    je .r
    cmp dword [ebp + 27h], CL_LONG
.r:
    ret

arg_names:                              ; ebp = league buffer (DIY during a matchday, the career slot 0 after a load)
    call arg_ours
    jne .r
    pushad
    mov eax, AP_LONG_OFF
    mov edx, AP_SHORT_OFF
    movzx ecx, word [ebp + 31h]         ; full = every club has played n-1 matches
    jecxz .set                          ; empty buffer
    lea edi, [ecx - 1]
    xor ebx, ebx
.chk:
    movzx esi, word [ebp + 6Dh + ebx * 2]
    cmp [ebp + esi + 2B7h], di
    jne .notfull
    inc ebx
    cmp ebx, ecx
    jb .chk
    cmp word [ebp + 5Fh], 0             ; full: no cycle left = Clausura over; one left = Apertura just over
    je .cl
    jmp .set
.notfull:                               ; not full: one cycle left = Clausura running; two (or a league not started
    cmp word [ebp + 5Fh], 1             ; yet, 0 at career creation) = Apertura
    jne .set
.cl:
    mov eax, CL_LONG_OFF
    mov edx, CL_SHORT_OFF
.set:
    mov [NAME_DW], eax
    mov [NAME_DW + 4], edx
    popad
.r:
    ret

; arg_round: replaces `mov dword [A0], offset DIY_competitionStart` at the start of cseg_8922B, the per-match counters of a
; league (every match of the division goes through it, played or simulated). The first match of the second cycle (one
; cycle left, matchday 0, no match counted yet in it) = the start of the Clausura: the table still holds the final Apertura.
arg_round:
    mov dword [A0], DIY
    push ebp
    mov ebp, DIY
    call arg_ours
    jne .r
    pushad
    cmp word [DIY + 5Fh], 1             ; one cycle left
    jne .x
    cmp word [DIY + 5Bh], 0             ; first match of a matchday
    jne .x
    cmp word [DIY + 1CBh], 0            ; first matchday of the cycle
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
    movzx eax, word [DIY + 6Dh]         ; Apertura champion (top of the sorted table)
    mov esi, [DIY + eax + 2B3h]
    add esi, [SELTEAMS]
    mov ax, [esi]
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
    mov dword [DIY + 27h], CL_LONG
    mov eax, 'APER'
    mov edx, 'TURA'
    mov ebx, 'CLAU'
    mov edi, 'SURA'
    call arg_text                       ; the name text the game shows
    push dword [A0]                     ; the manager's record of this season (if his club plays the Primera)
    push dword [D0]                     ; (A0 = DIY for the rest of cseg_8922B; D0 used by GetCurrentSeasonPointer)
    call GETSEASON
    mov esi, [A0]
    cmp dword [esi + 16h], AP_LONG_OFF  ; leagueStringOffset
    jne .p
    mov dword [esi + 16h], CL_LONG_OFF
.p:
    pop dword [D0]
    pop dword [A0]
    mov dword [NAME_DW], CL_LONG_OFF    ; the names the struct gives (career game list: the short one)
    mov dword [NAME_DW + 4], CL_SHORT_OFF
.x:
    popad
.r:
    pop ebp
    ret

arg_text:                               ; in DIY+4.. (name text, maybe country first): eax:edx -> ebx:edi (8 letters)
    lea esi, [DIY + 4]
    mov ecx, 23h - 8
.f:
    cmp [esi], eax
    jne .n
    cmp [esi + 4], edx
    jne .n
    mov [esi], ebx
    mov [esi + 4], edi
    ret
.n:
    inc esi
    loop .f
    ret

; arg_prebuild: replaces the `call cseg_8B2D3` that builds the player's league in InitializeNewSeason (right before the
; GetCurrentSeasonPointer call that stores its name in the season record). A new season starts with the Apertura: the
; struct names go back to TORNEO APERTURA / APERTURA before the build copies them (into DIY+4, DIY+27h, the slot buffer
; and the season record). (T15 renamed after the build: the slot copy kept CLAUSURA.)
arg_prebuild:
    mov dword [NAME_DW], AP_LONG_OFF
    mov dword [NAME_DW + 4], AP_SHORT_OFF
    jmp BUILD

align 2
APERTURA_CHAMP: dw 0FFFFh
'''
LOAD_ASM = r'''
; arg_load: wraps the call that processes a loaded career (trailer.load_trailer): names in step with the saved league.
arg_load:
    call LOADER
    pushfd
    push ebp
    mov ebp, SLOT0                      ; the player's league as loaded from the .CAR
    call ARG_NAMES
    pop ebp
    popfd
    ret
'''
LABELS = {}
ROUND_HOOK = False      # T20 experiment: the switch hook off
SLOT0 = None


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
    ap, cl = [], []                                     # (long, short) obj2 string offsets
    for k, (long, short) in enumerate(NAMES):
        lp, sp = area.add(long + b'\0'), area.add(short + b'\0')
        body += struct.pack('<II', lp - str_base, sp - str_base)
        if k == 0:
            ap = [lp, sp]
    cl = [area.add(CLAUSURA + b'\0'), area.add(b'CLAUSURA\0')]
    names_at = 13 + 6 * nd + 1
    new = area.add(bytes(body))
    refs = _refs(p, lo)
    assert refs
    for objn, off in refs:
        p.retarget(objn, off, 2, new)
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
    season_site = m[0].start()
    getseason = season_site + 5 + struct.unpack('<i', m[0].group(1))[0]
    # ... preceded by: push dword [A6]; call cseg_8B2D3; pop dword [A6]
    build_site = season_site - 6 - 5
    assert d1[build_site] == 0xE8 and d1[build_site - 6:build_site - 4] == b'\xff\x35' and d1[season_site - 6:season_site - 4] == b'\x8f\x05'
    build = build_site + 5 + struct.unpack_from('<i', d1, build_site + 1)[0]
    global SLOT0
    SLOT0 = struct.unpack('<I', m[0].group(2))[0] - 0x27        # the player's league buffer (its +27h = name pointer)
    symbols = {'DIY': (2, diy), 'A0': (2, A['A0']), 'SELTEAMS': (2, sel), 'D0': (2, regs['D7'] - 28),
               'GETSEASON': (1, getseason), 'BUILD': (1, build), 'NAME_DW': (2, new + names_at),
               'AP_LONG': (2, ap[0]), 'CL_LONG': (2, cl[0]),
               'AP_LONG_OFF': (0, ap[0] - str_base), 'AP_SHORT_OFF': (0, ap[1] - str_base),
               'CL_LONG_OFF': (0, cl[0] - str_base), 'CL_SHORT_OFF': (0, cl[1] - str_base)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    if ROUND_HOOK:
        p.remove(1, site + 2)                           # the replaced mov holds two absolute addresses
        p.remove(1, site + 6)
        p.put(1, site, b'\xe8' + struct.pack('<i', labels['arg_round'] - (site + 5)) + b'\x90' * 5)
    p.put(1, build_site + 1, struct.pack('<i', labels['arg_prebuild'] - (build_site + 5)))   # relative call: no fixup
    LABELS.update(labels)
    print(f'exe: Argentina Apertura/Clausura: struct obj2+{new:#x}, counters obj1+{site:#x}, new season obj1+{build_site:#x}, '
          f'code obj1+{at:#x} ({len(code)} B)')
    return (at + len(code) + 15) & ~15


def load_hook(p, at):
    """After trailer.patch: wrap the LoadCareerFile -> ProcessCareerFile call (now trailer's load_trailer)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a1 = sacups.regs(d1)['A1']
    m = [x for x in re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', a1)) + rb'(.{4})\xe8.{4}\x75.\xe8.{4}\x75.\xe8(.{4})',
                                d1, re.S)]
    m = [x for x in m if sum(y.group(1) == x.group(1) for y in m) == 1]
    assert len(m) == 1, len(m)
    call = m[0].end() - 5
    loader = m[0].end() + struct.unpack('<i', p.get(1, call + 1, 4))[0]     # trailer's load_trailer (patched bytes)
    assert loader != m[0].end() + struct.unpack('<i', m[0].group(2))[0], 'trailer not applied yet'
    symbols = {'LOADER': (1, loader), 'ARG_NAMES': (1, LABELS['arg_names']), 'SLOT0': (2, SLOT0)}
    code, fix = nasmcave.assemble(LOAD_ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, call + 1, struct.pack('<i', at - (call + 5)))
    print(f'exe: Argentina: career load call obj1+{call:#x} -> obj1+{at:#x}')
    return (at + len(code) + 15) & ~15
