"""4.2 DRIBBLING NUOVO: the CPU build-up game v1 "MIX" (Davide 12/11 "Prima mix"; design internal/handoff/
cpu-buildup-fable.md; difficulty.py has the option, DF_DACT and df_who).

Only a pure computer team facing a human (df_who = 2) with DRIBBLING NEW on at the kick-off (DF_DACT); every other team,
CLASSIC, SWOS++ and training games run the original instruction only. No stub calls Rand / Rand2 (AI_rand, already drawn
this update, and currentGameTick bits only).
- G1 the keeper's ball (@@keepers_ball `mov ax, AI_rand`): a free teammate (no opponent within FREE px) in his cone
  within G1_DIST -> the pass branch (AI_rand bit 0 cleared); no teammate in the cone and stoppageTimerActive < G1_LOOK
  on 3 updates in 4 -> the pass branch too, which then turns him (the original turns when the cone has no teammate);
  otherwise the original coin.
- H1 the pressure hoof (cseg_84C00 `cmp D6, 180000` / ja hoof): between 180000 and H1_DEEP (squared px from the
  opponents' goal) the hoof only when AI_rand & 3 = 0; deeper the original clearance.
- P1 the unpressed pass (cseg_84B5B `cmp D6, 9800` / jb run at goal): D6 in P1_NEAR..P1_FAR, currentGameTick & 18h = 0,
  AI_rand < P1_P, AI_resumePlayTimer 0, the cone's closest man a free teammate (not the keeper) at ballDistance
  P1_MIN..P1_MAX -> return into @@our_player_closest (the original's own pass: AI_resumePlayTimer 15, quickFire).
FindClosestPlayerToBallFacing (both teams, the cone of D7) is called with D0..A3 saved and restored around it.
"""
import os
import re
import struct

import nasmcave

G1_DIST, G1_LOOK, FREE = 40000, 230, 30         # 200 px; stoppage ticks; px
H1_DEEP = 270000                                # 520 px from the opponents' goal: about the own penalty area
P1_NEAR, P1_FAR, P1_P, P1_MIN, P1_MAX = 40000, 250000, 48, 1600, 22500

ASM = r"""
    jmp bu_frame                        ; (BU_AT + 0: difficulty's df_frame calls it in DIFF_TRACE builds)
; ---- in: the cone D7 << 5; out esi = the closest man in it when he is a teammate of A5 and not the keeper (else 0),
;      edx = his ballDistance. D0..A3 (and every register but esi / edx) as before.
bu_find:
    pushad
    mov esi, D0_
    mov edi, BU_SV
    mov ecx, 12
    rep movsd
    mov ax, [D7_]
    shl ax, 5
    mov [D0_], ax
    call FCP
    xor ebx, ebx
    xor edx, edx
    mov esi, [A0_]
    cmp esi, -1
    je .s
    mov ecx, [A5_]
    test ecx, ecx
    jz .s
    mov ax, [ecx]                       ; (Sprite.teamNumber)
    cmp ax, [esi]
    jne .s
    cmp word [esi + 2], 1               ; (Sprite.playerOrdinal: the keeper)
    je .s
    mov ebx, esi
    mov edx, [esi + 4Ah]                ; (Sprite.ballDistance)
.s: mov [BU_R], ebx
    mov [BU_D], edx
    mov esi, BU_SV
    mov edi, D0_
    mov ecx, 12
    rep movsd
    popad
    mov esi, [BU_R]
    mov edx, [BU_D]
    ret

; ---- in esi = a sprite; out al = 1 when no opponent (of A6) stands within FREE px of him
bu_free:
    push ebx
    push ecx
    push edx
    push edi
    mov ebx, [A6_]
    mov ebx, [ebx]                      ; (opponentsTeam)
    mov edi, [ebx + 14h]                ; (spritesTable)
    mov ecx, 11
.l: mov ebx, [edi]
    add edi, 4
    movsx eax, word [ebx + 20h]
    movsx edx, word [esi + 20h]
    sub eax, edx
    imul eax, eax
    push eax
    movsx eax, word [ebx + 24h]
    movsx edx, word [esi + 24h]
    sub eax, edx
    imul eax, eax
    pop edx
    add eax, edx
    cmp eax, FREE * FREE
    jb .m
    loop .l
    mov al, 1
    jmp .x
.m: xor eax, eax
.x: pop edi
    pop edx
    pop ecx
    pop ebx
    ret

; ---- ZF = 0 unless A6 is the opposition with DRIBBLING NEW on (ZF = 1: act)
bu_opp:
    cmp byte [DF_DACT], 0
    je .n
    push eax
    push ebx
    mov ebx, [A6_]
    call df_who
    cmp al, 2
    pop ebx
    pop eax
    ret
.n: cmp esp, 0                          ; (ZF = 0)
    ret

; ---- G1 (replaces `mov ax, AI_rand` at @@keepers_ball; then `mov D0, ax / and D0, 1 / jz pass`)
bu_g1:
    mov ax, [AIRAND]
    call bu_opp
    jne .o
    push esi
    push edx
    push eax
    call bu_find
    test esi, esi
    jz .look
    cmp edx, G1_DIST
    ja .k
    call bu_free
    test al, al
    jz .k
    inc dword [BU_G1]
    pop eax
    and ax, 0FFFEh                      ; the pass
    jmp .p
.look:
    pop eax
    cmp word [STOPT], G1_LOOK
    jae .p
    test byte [CGT], 3
    jz .p
    and ax, 0FFFEh                      ; no teammate in the cone: the pass branch turns him
    jmp .p
.k: pop eax
.p: pop edx
    pop esi
.o: ret

; ---- H1 (replaces `cmp dword [D6], 180000`; then `ja hoof`)
bu_h1:
    push eax
    mov eax, 180000
    cmp [D6_], eax
    jbe .c
    call bu_opp
    jne .c
    test byte [AIRAND], 3
    jz .c
    mov eax, H1_DEEP
    cmp [D6_], eax
    ja .c
    inc dword [BU_H1]
.c: cmp [D6_], eax
    pop eax
    ret

; ---- P1 (replaces `cmp dword [D6], 9800`; then `jb run at the goal`)
bu_p1:
    cmp dword [D6_], P1_NEAR
    jb .o
    cmp dword [D6_], P1_FAR
    ja .o
    test byte [CGT], 18h
    jnz .o
    cmp byte [AIRAND], P1_P
    jae .o
    cmp word [AIRPT], 0
    jne .o
    call bu_opp
    jne .o
    push esi
    push edx
    push eax
    call bu_find
    test esi, esi
    jz .n
    cmp edx, P1_MIN
    jb .n
    cmp edx, P1_MAX
    ja .n
    call bu_free
    test al, al
    jz .n
    inc dword [BU_P1]
    pop eax
    pop edx
    pop esi
    mov dword [esp], OPC                ; the original's own pass (@@our_player_closest)
    ret
.n: pop eax
    pop edx
    pop esi
.o: cmp dword [D6_], 9800
    ret

; ---- DIFF_TRACE: per frame, both teams: a release = passKickTimer turning 25; passInProgress 1 = a pass (DoPass),
;      0 = a kick; the keeper's (ordinal 1) counted apart. Counters: BU_CNT (words) [team][pass, kick, gk pass, gk kick]
bu_frame:
%if DIFF_TRACE
    pushad
    mov esi, TOPT
    xor ebx, ebx
.t: mov ax, [esi + 66h]                 ; (passKickTimer)
    mov dx, [BU_PKT + ebx * 2]
    mov [BU_PKT + ebx * 2], ax
    cmp ax, 25
    jne .n
    cmp dx, 25
    je .n
    lea edi, [BU_CNT + ebx * 8]
    cmp word [esi + 80h], 0             ; (passInProgress)
    jne .p
    add edi, 2
.p: inc word [edi]
    mov ecx, [esi + 68h]                ; (passingKickingPlayer)
    test ecx, ecx
    jz .n
    cmp word [ecx + 2], 1
    jne .n
    inc word [edi + 4]
.n: add esi, 91h
    inc ebx
    cmp ebx, 2
    jb .t
    popad
%endif
    ret

align 4
BU_TAG: db 'BUP1'                       ; (the harness: counters from here)
BU_G1: dd 0                             ; +4 keeper short passes chosen
BU_H1: dd 0                             ; +8 hoofs turned into a pass look
BU_P1: dd 0                             ; +12 unpressed passes
BU_CNT: times 8 dw 0                    ; +16 DIFF_TRACE [top, bottom][pass, kick, keeper pass, keeper kick]
BU_PKT: dw 0, 0                         ; +32
BU_R: dd 0
BU_D: dd 0
BU_SV: times 12 dd 0
"""


def _one(pat, d, name, keep):
    m = [x.start() for x in re.finditer(pat, d, re.S)]
    m = [o for o in m if keep(o)]
    assert len(m) == 1, (name, [hex(x) for x in m])
    return m[0]


def find(p, sym):
    """The three sites + the game's symbols (obj1 offsets / (obj, off)), every language."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    t = lambda o: df._t(p, o)
    var = lambda k: (2, sym['D0_'][1] + 4 * k)
    s = dict(D6_=var(6), D7_=var(7), A0_=var(8), A5_=var(13))
    h1 = _one(rb'\x81\x3d....\x20\xbf\x02\x00\x0f\x87', d, 'H1 cmp D6, 180000', lambda o: t(o + 2) == s['D6_'])
    p1 = _one(rb'\x81\x3d....\x48\x26\x00\x00\x0f\x82', d, 'P1 cmp D6, 9800', lambda o: t(o + 2) == s['D6_'])
    g1 = _one(rb'\x66\xa1....\x66\xa3....\x66\x83\x25....\x01\x0f\x84....\x66\xa1....\x66\x39\x05', d, '@@keepers_ball',
              lambda o: t(o + 8) == sym['D0_'] and t(o + 35) == s['D7_'])
    assert d[h1 + 0x24] == 0xE8, 'H1: call FindClosestPlayerToBallFacing'
    s['FCP'] = p.call_target(1, h1 + 0x24)
    k = h1 + 0x29
    m = re.compile(rb'\x66\x39\x05....\x0f\x84', re.S).search(d, k, k + 0x40)
    assert m and t(m.start() + 3) == sym['D0_'], 'H1: jz @@our_player_closest'
    opc = m.start() + 13 + struct.unpack_from('<i', d, m.start() + 9)[0]
    assert d[opc:opc + 2] == b'\x8b\x35' and t(opc + 2) == sym['A6_'] and \
        d[opc + 6:opc + 15] == b'\x66\xc7\x86\x84\x00\x00\x00\x00\x00' and d[opc + 15:opc + 17] == b'\x66\xa1', \
        ('@@our_player_closest', hex(opc))
    s['OPC'] = (1, opc)
    s['AIRPT'] = t(opc + 17)
    m = re.compile(rb'\x66\xa1....\x66\x39\x05', re.S).search(d, opc + 0x30, opc + 0x80)
    assert m and t(m.start() + 9) == sym['D0_'], 'stoppageTimerActive'
    s['STOPT'] = t(m.start() + 2)
    s['AIRAND'] = t(g1 + 2)
    assert p.target(1, p1 + 2) == s['D6_'] and s['AIRPT'] and s['AIRAND'] and s['STOPT']
    return dict(G1=g1, H1=h1, P1=p1), s


def patch(p, lang, sym, lab_df, at, end):
    """Assemble at obj4 at..end (room from MC) and hook the three sites. sym: difficulty's symbols; lab_df its labels."""
    import slow
    sites, s = find(p, sym)
    s.update(D0_=sym['D0_'], A6_=sym['A6_'], CGT=slow.find(p)['CGT'], DF_DACT=(4, lab_df['DF_DACT']),
             df_who=(4, lab_df['df_who']))
    orig = {k: p.get(1, sites[k], n) for k, n in (('G1', 6), ('H1', 10), ('P1', 10))}
    assert orig['G1'][:2] == b'\x66\xa1' and orig['H1'][:2] == orig['P1'][:2] == b'\x81\x3d', ('sites patched', orig)
    import difficulty as df0
    m = re.compile(rb'\xc7\x05........', re.S)
    fcp = s['FCP'][1]
    tops = [x.start() for x in m.finditer(p.le.obj_bytes(1), fcp, fcp + 0x80)
            if df0._t(p, x.start() + 2) == (2, sym['D0_'][1] + 4 * 11)]
    assert tops, 'FindClosestPlayerToBallFacing: mov A3, offset topTeamData'
    s['TOPT'] = p.target(1, tops[0] + 6)
    defs = f'%define DIFF_TRACE {int(df0.trace())}\n' + ''.join(f'%define {k} {v}\n' for k, v in (('G1_DIST', G1_DIST), ('G1_LOOK', G1_LOOK), ('FREE', FREE),
                                                         ('H1_DEEP', H1_DEEP), ('P1_NEAR', P1_NEAR), ('P1_FAR', P1_FAR),
                                                         ('P1_P', P1_P), ('P1_MIN', P1_MIN), ('P1_MAX', P1_MAX)))
    src = defs + ASM
    code, fix, rel = nasmcave.assemble_obj(src, at, s, 4)
    lab = nasmcave.labels(src, at, s)
    assert at + len(code) <= end, ('build-up: past its obj4 room', hex(at + len(code)))
    assert not any(p.get(4, at, end - at)), 'build-up: obj4 room not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    import difficulty as df
    for key, n, l in (('G1', 6, 'bu_g1'), ('H1', 10, 'bu_h1'), ('P1', 10, 'bu_p1')):
        df._hook(p, sites[key], n, n, lab[l])
    LABELS.clear()
    LABELS.update(lab)
    SITES.clear()
    SITES.update(sites)
    print(f'exe: build-up v1 (DRIBBLING NEW): code obj4+{at:#x} ({len(code)} B), 3 obj1 sites')
    return at + len(code)


LABELS = {}
SITES = {}
