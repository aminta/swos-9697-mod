"""4.0.1 quiet season end (World 2026-27): the other countries' competitions are simulated without being shown.

At CONTINUA CARRIERA the season end (cseg_91428) walks the season-end list: the career club's own country first
(`call cseg_9153F` before the loop), then every other listed country (the loop's `call cseg_9153F`). cseg_9153F
simulates the country's league divisions (cseg_91D4D -> cseg_915ED -> cseg_3ABB2) and cups (cseg_91857 ->
cseg_916C2 -> cseg_3ACAB), and each simulation ends by showing the competition through ShowMenu
(ShowDiyLeaguesTournamentMenu / cseg_45B51): one full menu per competition, frame-paced. A world of 91 countries
shows ~260 of them (Davide's ao486: minutes).

The game's own switch: dseg_10E846 = 1 (cseg_8ECAE sets it around its own cseg_3ABB2) makes cseg_3AE87 / cseg_3B18F
return before the show (`cmp dseg_10E846, 0 / jnz ret`); every other test of the flag is or'ed with dseg_10E848,
which cseg_91428 already sets for the whole season end, so the simulation itself is unchanged.

qe_call replaces the loop's `call cseg_9153F`: in a career (g_gameType 4) of the World 2026-27 (world byte W27) it
calls cseg_9153F with dseg_10E846 = 1 and restores the old value; anywhere else it is the plain call. The career
club's own country (the call before the loop) is not touched: its tables and cups still show as in the original.
"""
import re
import struct

import nasmcave

ASM = r"""
qe_call:                                ; replaces the season-end loop's `call cseg_9153F` (cseg_91428)
    cmp word [GAMETYPE], 4
    jne .plain
    cmp byte [SLT + WORLD_BYTE_], W27_
    jne .plain
    call qe_show                        ; (4.0.1: a progress line, the screen would look frozen on a real 486)
    push dword [QFLAG]                  ; (the word and its neighbour, restored as they were)
    mov word [QFLAG], 1
    call C9153F
    pop dword [QFLAG]
    ret
.plain:
    jmp C9153F

qe_show:                                ; 'SIMULAZIONE ALTRE NAZIONI... n/N' on the screen's bottom strip (rows 190-199):
    pushad                              ; drawn into the virtual screen by the game's DrawMenuText (small font), then
    push es                             ; only that strip copied to the video memory (FlipInMenu's copy, 10 rows)
    push ds
    pop es
    cld
    mov esi, REGS_                      ; (the pseudo registers: the loop's A6 / D0 and DrawMenuText's own)
    mov edi, qe_regs
    mov ecx, 15
    rep movsd
    mov esi, [A6R]                      ; the countries still to come: the list's bytes up to FFh, but the career
    xor ecx, ecx                        ; club's own (the loop skips it)
.r: mov al, [esi]
    inc esi
    cmp al, 0FFh
    je .rd
    cmp al, [SELTEAM]
    je .r
    inc ecx
    cmp ecx, 255
    jb .r
.rd:
    mov eax, [qe_n]
    inc eax
    mov [qe_n], eax                     ; this country's number
    lea edx, [eax + ecx]                ; of all
    test ecx, ecx
    jnz .t
    mov dword [qe_n], 0                 ; (the last one: the next season end counts from 1 again)
.t: mov edi, qe_txt
    mov esi, qe_prefix
    push eax                            ; (the copy runs through al)
.c: lodsb
    test al, al
    jz .cd
    stosb
    jmp .c
.cd:
    pop eax
    call qe_num
    mov al, '/'
    stosb
    mov eax, edx
    call qe_num
    mov byte [edi], 0
    mov edi, [LINADR]                   ; the strip cleared (colour 0)
    add edi, 190 * 320
    mov ecx, 10 * 320 / 4
    xor eax, eax
    rep stosd
    mov dword [A0R], qe_txt
    mov dword [A1R], SMALLT
    mov word [REGS_ + 4], 8             ; D1 = x
    mov word [REGS_ + 8], 192           ; D2 = y
    mov word [REGS_ + 12], 2            ; D3 = colour
    mov byte [DELTA], 0
    call DRAWTEXT
    mov esi, [LINADR]
    add esi, 190 * 320
    mov edi, 0A0000h + 190 * 320
    mov ecx, 10 * 320 / 4
    rep movsd
    mov esi, qe_regs
    mov edi, REGS_
    mov ecx, 15
    rep movsd
    pop es
    popad
    ret

qe_num:                                 ; eax -> its decimal digits at edi (edi after them)
    push ebx
    push ecx
    push edx
    mov ebx, 10
    xor ecx, ecx
.d: xor edx, edx
    div ebx
    push edx
    inc ecx
    test eax, eax
    jnz .d
.o: pop eax
    add al, '0'
    stosb
    loop .o
    pop edx
    pop ecx
    pop ebx
    ret

align 4
qe_n: dd 0
qe_regs: times 15 dd 0
qe_txt: times 64 db 0
qe_prefix: db PREFIX, 0
"""


def sites(p):
    """(the loop's call site, cseg_9153F, dseg_10E846) in obj1 / obj2 offsets, from the original exe's bytes."""
    d = p.le.obj_bytes(1)
    pat = rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0\x75.' \
          rb'\x66\xa1(....)\x66\x0b\xc0\x74'
    m = [x.start() for x in re.finditer(pat, d, re.S)]           # cseg_3AE87 / cseg_3B18F: 11F9CC, 10E848, 10E846
    assert len(m) == 2, m
    flags = {p.target(1, x + 2 + 11 * 2) for x in m}
    assert len(flags) == 1, flags
    qflag = flags.pop()
    import careerworld
    s = careerworld.SITES or careerworld.sites(p)
    tail = d[s['list']:s['list'] + 0x80]                          # the loop: ... cmp [D0], al / jz / call 9153F
    loop = [x.start() for x in re.finditer(rb'\x38\x05....\x74.\xe8', tail, re.S)]
    assert len(loop) == 1, loop
    site = s['list'] + loop[0] + 8
    target = site + 5 + struct.unpack_from('<i', d, site + 1)[0]
    first = [x.start() for x in re.finditer(rb'\xe8' , d[s['list'] - 0x30:s['list']])]
    calls = {s['list'] - 0x30 + x + 5 + struct.unpack_from('<i', d, s['list'] - 0x30 + x + 1)[0] for x in first}
    assert target in calls, ('the loop calls the function the career country gets', hex(target))
    return site, target, qflag


TEXT = {'it': b'SIMULAZIONE ALTRE NAZIONI... ', 'en': b'SIMULATING OTHER COUNTRIES... ',
        'fr': b'SIMULATION DES AUTRES PAYS... ', 'de': b'SIMULATION ANDERER LAENDER... '}


def draw_sites(p):
    """(DrawMenuText, smallCharsTable, g_deltaColor, linAdr384k) from the original exe's bytes: DrawMenuItem's
    `mov byte [g_deltaColor], 0 / push [A5] / call DrawMenuText` (the callee starting `mov eax, [A1] / mov [A5], eax`),
    ContinueAbortInit's `mov [A1], smallCharsTable / call GetTextWidth / add word [D7], 20`, FlipInMenu's copy."""
    import sacups
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    a0 = r['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xc6\x05(....)\x00\xff\x35' + A(a0 + 20) + rb'\xe8(....)', d, re.S)]
    dmt = {(x.end() + struct.unpack('<i', x.group(2))[0], x.start() + 2) for x in m}
    dmt = {(t, dc) for t, dc in dmt if d[t] == 0xA1 and d[t + 1:t + 5] == struct.pack('<I', a0 + 4)
           and d[t + 5] == 0xA3 and d[t + 6:t + 10] == struct.pack('<I', a0 + 20)}
    assert len({t for t, _ in dmt}) == 1, dmt
    drawtext, dcsite = sorted(dmt)[0]
    sm = {x.start() + 6 for x in re.finditer(rb'\xc7\x05' + A(a0 + 4) + rb'(....)\xe8....\x66\x83\x05' + A(r['D7']) + rb'\x14', d, re.S)}
    assert len(sm) == 1, sm
    fl = [x.start() + 2 for x in re.finditer(rb'\x8b\x35(....)\xbf\x00\x00\x0a\x00\xb9\x80\x3e\x00\x00\xf3\xa5\xc3', d, re.S)]
    assert len(fl) == 1, fl
    return drawtext, p.target(1, sm.pop()), p.target(1, dcsite), p.target(1, fl[0]), a0


def patch(p, at, w27, lang='it'):
    """qe_call at obj1:at; returns its end. w27: the World 2026-27's world byte."""
    import careerworld
    site, c9153f, qflag = sites(p)
    assert p.get(1, site, 5) == p.le.obj_bytes(1)[site:site + 5], ('the loop call already patched', hex(site))
    cs = careerworld.SITES or careerworld.sites(p)
    sobj, slt = cs['slt']
    gt = cs['gametype']
    drawtext, smallt, delta, linadr, a0 = draw_sites(p)
    sym = {'GAMETYPE': gt, 'SLT': (sobj, slt), 'WORLD_BYTE_': (0, careerworld.WORLD_BYTE), 'W27_': (0, w27),
           'QFLAG': qflag, 'C9153F': (1, c9153f), 'DRAWTEXT': (1, drawtext), 'SMALLT': smallt, 'DELTA': delta,
           'LINADR': linadr, 'SELTEAM': cs['nc']['selteam'], 'REGS_': (2, a0 - 32), 'A0R': (2, a0), 'A1R': (2, a0 + 4), 'A6R': (2, a0 + 24)}

    src = ASM.replace('PREFIX', "'" + TEXT[lang].decode() + "'")
    import os
    if os.environ.get('QE_NOPROG'):              # (build-time only: the control exe without the progress line)
        src = src.replace('    call qe_show ', '    times 5 nop ')     # (single-byte NOPs: 0F 1F is not a 486 opcode)
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site, b'\xe8' + struct.pack('<i', lab['qe_call'] - (site + 5)))
    print(f'exe: quiet season end (World 2026-27, world {w27}): the loop call obj1+{site:#x} -> qe_call obj1+{at:#x} '
          f'({len(code)} B), dseg_10E846 obj2+{qflag[1]:#x}, progress line by obj1+{lab["qe_show"]:#x}')
    return at + len(code)
