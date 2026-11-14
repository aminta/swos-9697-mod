"""4.2 set pieces 1+2 (Davide GO 14/11; design internal/handoff/setpieces-wingplay-design.md sections 1, 2): an
OPTIONS switch CALCI PIAZZATI / SET PIECES: CLASSICI (the original game) / NUOVI, for every match (physics and keeper
rules, both sides; SWOS++ keeps the original).

NUOVI:
- headers go down: the jump header's ball deltaZ (kBallJumpHeaderDeltaZ 0xA000, up) -> SP_JZ minus HEADING x SP_JST
  (HEADING = placement: a good header keeps the ball under the bar from further out); the flying header's
  (kFlyingHeaderBallDeltaZ 0x20000) -> SP_FZ;
- the header contact window's ceiling (ball z <= 15, the jump and the static header) -> SP_CEIL;
- the keeper: catch band ballDefensiveZ 13..27 -> 13..SP_BAND; no 6-yard-box bypass of the word29 gate (he comes for a
  ball in his 6-yard box only with rand16 < word29, as elsewhere in the box; both sites: the run to the landing spot and
  the catch);
- the CPU header gate (DecideWhetherCpuPlayerFires): ball within 900 instead of 648 (squared) when the ball is in the
  air (z >= 8), and facing right / left (2 / 6) accepted with the ball wide (x outside the penalty area's 193..478).

CLASSICI (SP_W 0): every stub does the original instruction(s) only (tools/hosttest/diff_structural.py proves it).

Room (MC 14/11): obj4 SETPIECE_AT..SETPIECE_END (swreg). LE padding (DE): every obj1 hook region swallows an
instruction with an absolute operand (1 fixup removed : 1 added), and the stubs reach obj2 through two base dwords (SPB:
obj2's and obj1's, the band's only fixups), read PC-relative: [ebp] = obj2's base, then [reg + constant offset].

Test switches (modver TEST_VARS, never in a release build): SP_TEST=0 / 1 (the stubs in, SP_W's start value until the
OPTIONS row exists); SP_JZ / SP_JST / SP_FZ / SP_CEIL / SP_BAND / SP_CPU (tuning, M3).
"""
import os
import re
import struct

import nasmcave

TAG = b'SETP'


LABEL = {'it': 'CALCI PIAZZATI', 'en': 'SET PIECES', 'fr': 'PHASES ARRETEES', 'de': 'STANDARDS'}
VALUES = {'it': ('CLASSICI', 'REALISTICI', 'ARCADE'), 'en': ('CLASSIC', 'REALISTIC', 'ARCADE'),
          'fr': ('CLASSIQUES', 'REALISTES', 'ARCADE'), 'de': ('KLASSISCH', 'REALISTISCH', 'ARCADE')}   # (Davide 14/11)


def on():
    """The band and the row: whenever difficulty.py's OPTIONS rows are in (DIFF_TEST; MC 14/11). SP_TEST = SP_W's start
    value only (0 CLASSICI, the default; 1 NUOVI), and needs DIFF_TEST."""
    import difficulty as df
    assert df.knobs() or not os.environ.get('SP_TEST'), 'SP_TEST needs DIFF_TEST (the OPTIONS rows)'
    return df.knobs()


def _iv(k, d):
    v = os.environ.get(k)
    return int(v, 0) if v else d


def knobs():
    return dict(JZ=_iv('SP_JZ', -0x800), JST=_iv('SP_JST', 0x400), FZ=_iv('SP_FZ', 0x8000), CEIL=_iv('SP_CEIL', 17),
                BAND=_iv('SP_BAND', 22), CPU=_iv('SP_CPU', 900), FKT=_iv('SP_FKT', 11 << 16), BLO=_iv('SP_BLO', 13),
                FKW=[int(x) for x in (os.environ.get('SP_FKW') or '10,9,8,7,6,4,3,2').split(',')],          # REALISTICI
                FKW2=[int(x) for x in (os.environ.get('SP_FKW2') or '6,5,5,4,4,3,2,1').split(',')],        # ARCADE
                FKC2=_iv('SP_FKC2', 0),
                FKC=_iv('SP_FKC', 1), FKMAX=_iv('SP_FKMAX', 0x3000), FKMIN=_iv('SP_FKMIN', -0x1000),
                FKWALL=_iv('SP_FKWALL', 40), FKCLR=_iv('SP_FKCLR', 15),
                AFP=_iv('SP_AFP', 21845), AFD0=_iv('SP_AFD0', 88), AFD1=_iv('SP_AFD1', 170),      # ARCADE fouls: 1 in 3,
                AFX0=_iv('SP_AFX0', 150), AFX1=_iv('SP_AFX1', 520),
                FKXI=_iv('SP_FKXI', 8), FKXC=_iv('SP_FKXC', 3))                                  # §3 sideways steer                                 #  the FK zone


def _one(d, pat, name, n=1):
    m = [x.start() for x in re.finditer(pat, d, re.S)]
    assert n is None or len(m) == n, (name, [hex(x) for x in m])
    return m


def find(p):
    """The sites (obj1 offsets, from the exe's own bytes) and the obj2 offsets the stubs read."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    o2 = p.le.obj_bytes(2)
    t = lambda o: df._t(p, o)
    _, sym = df.find(p)
    a2, a4 = sym['A2_'], sym['A4_']
    a5 = (2, sym['D0_'][1] + 4 * 13)
    d7 = (2, sym['D0_'][1] + 4 * 7)
    val = lambda o: struct.unpack_from('<I', o2, t(o + 1)[1])[0] if t(o + 1) and t(o + 1)[0] == 2 else None
    hz = [o for o in _one(d, rb'\xa1....\x8b\x35....\x89\x46.', 'mov eax, deltaZ', None) if t(o + 7) == a2]
    jz = [o for o in hz if val(o) == 0xA000]
    assert len(jz) == 1, ('kBallJumpHeaderDeltaZ', jz)
    jz = jz[0]
    assert d[jz - 10:jz - 8] == b'\xc7\x05' and t(jz - 8) == a2, 'PlayerHittingJumpHeader: mov A2, offset ballSprite'
    ball = t(jz - 4)
    fz = [o for o in hz if val(o) == 0x20000 and jz < o < jz + 0x600]
    assert len(fz) == 1, ('kFlyingHeaderBallDeltaZ', fz)
    fz = fz[0]
    dz = d[jz + 13]
    assert d[fz + 13] == dz, 'deltaZ offset'
    hd = [o + 10 for o in _one(d, rb'\xc7\x05........\x8b\x35....\x8a\x46', 'mov esi, A4 / mov al, heading', None)
          if jz < o < fz and t(o + 12) == a4]
    assert len(hd) == 1, ('PlayerHittingJumpHeader: heading', hd)
    hd = hd[0]
    ceil = [o for o in _one(d, rb'\x8b\x35....\x66\x83\x7e.\x0f\x0f\x87', 'contact ceiling', 2) if t(o + 2) == a2]
    assert len(ceil) == 2 and d[ceil[0] + 9] == d[ceil[1] + 9], 'the two contact ceilings'
    zo = d[ceil[0] + 9]
    band = _one(d, rb'\x66\x83\x3d....\x1b\x0f\x8f', 'catch band')[0]
    assert d[band + 14:band + 17] == b'\x66\x83\x3d' and t(band + 17) == t(band + 3) and d[band + 21] == 12, 'band low 12'
    gka = _one(d, rb'\x66\xa1....\x66\x0b\xc0\x75.\x8b\x35....\x8b\x46', '6-yard bypass', 2)
    assert t(gka[0] + 2) == t(gka[1] + 2), 'ballInGoalkeeperArea'
    cpu = _one(d, rb'\x8b\x35....\x81\x7e\x4a\x88\x02\x00\x00\x0f\x87', 'CPU header gate')[0]
    assert t(cpu + 2) == a5, 'mov esi, A5'
    fb = _one(d, rb'\x66\x83\x3d....\x05\x74.\xe9', 'facing bottom')[0]
    ft = [o for o in _one(d, rb'\x66\x83\x3d....\x01\x0f\x85', 'facing top', None) if cpu - 0x40 < o < cpu]
    assert len(ft) == 1 and fb < ft[0] < cpu and t(fb + 3) == t(ft[0] + 3) == d7, ('facing top', ft)
    ft = ft[0]
    # §3 free kicks: PlayerKickingBall's `mov eax, kBallKickingDeltaZ` (then mov esi, A2 / mov [esi + deltaZ], eax /
    # call ResetBothTeamSpinTimers / cmp gameStatePl, 100 / jz / cmp gameState, 15); UpdateBall's `mov eax,
    # kBallAirFriction` (then sub D3, eax / or D3, 1); ApplyBallAfterTouch's head (mov esi, A6 / mov ax, [esi +
    # passInProgress]); the catch band's low bound (cmp ballDefensiveZ, 12 / jle)
    kd = [o for o in _one(d, rb'\xa1....\x8b\x35....\x89\x46\x36\xe8....\x66\x83\x3d....\x64\x74.\x66\x83\x3d....\x0f',
                          'PlayerKickingBall: kBallKickingDeltaZ', None) if t(o + 7) == a2 and val(o) == 0x14000]
    assert len(kd) == 1, ('kBallKickingDeltaZ', kd)
    kd = kd[0]
    d3 = (2, sym['D0_'][1] + 4 * 3)
    gr = [o for o in _one(d, rb'\xa1....\x29\x05....\x83\x0d....\x01', 'UpdateBall: kBallAirFriction', None)
          if val(o) == 3291 and t(o + 7) == d3 and t(o + 13) == d3]
    assert len(gr) == 1, ('kBallAirFriction', gr)
    gr = gr[0]
    a6 = sym['A6_']
    at = [o for o in _one(d, rb'\x8b\x35....\x66\x8b\x86\x80\x00\x00\x00\x66\x0b\xc0\x0f\x85', 'ApplyBallAfterTouch', None)
          if t(o + 2) == a6]
    assert len(at) == 1, ('ApplyBallAfterTouch', at)
    at = at[0]
    blo = band + 14
    assert d[blo + 7:blo + 9] == b'\x0c\x7e', 'band low: cmp 12 / jle'
    for k in (ball, a2, a4, a5, d7, t(band + 3), t(gka[0] + 2), t(jz + 1), t(fz + 1), t(kd + 1), t(kd + 22), t(kd + 32),
              t(gr + 1), a6):
        assert k and k[0] == 2, k
    # ARCADE fouls (Davide GO 14/11): PlayerTacklingTestFoul's `mov esi, A1 / mov ax, [esi + tackleState] / or ax, ax /
    # jz foul / mov esi, A1 / cmp [esi + tackleState], TS_GOOD_TACKLE / jz comment`; the hook = the second mov + cmp + jz
    a1 = (2, sym['D0_'][1] + 4 * 9)
    af = [m for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46(.)\x66\x0b\xc0\x74(.)\x8b\x35....\x66\x83\x7e(.)\x02\x0f\x84',
                                 d, re.S) if t(m.start() + 2) == a1 and t(m.start() + 17) == a1 and m.group(1) == m.group(3)]
    assert len(af) == 1, ('PlayerTacklingTestFoul: the clean-tackle test', [hex(m.start()) for m in af])
    tks = af[0].group(1)[0]
    af_foul = af[0].start() + 15 + struct.unpack_from('<b', d, af[0].start() + 14)[0]
    af = af[0].start() + 15
    af_cmt = af + 17 + struct.unpack_from('<i', d, af + 13)[0]
    assert d[af_foul:af_foul + 2] == b'\x8b\x35' and t(af_foul + 2) == a6, 'foul_concedeed: mov esi, A6'
    s = dict(JZ=jz, FZ=fz, HD=hd, CEIL0=ceil[0], CEIL1=ceil[1], BAND=band, GKA0=gka[0], GKA1=gka[1], CPU=cpu, FB=fb,
             FT=ft, KD=kd, GR=gr, AT=at, BLO=blo, AF=af, AF_FOUL=af_foul, AF_CMT=af_cmt)
    c = dict(KDZ_O=t(kd + 1)[1], GSP_O=t(kd + 22)[1], GS_O=t(kd + 32)[1], KAF_O=t(gr + 1)[1], A6T_O=a6[1],
             A1_O=sym['D0_'][1] + 4 * 9, BALL_O=ball[1], A2_O=a2[1], A4_O=a4[1], A5_O=a5[1], D7_O=d7[1], BDZ_O=t(band + 3)[1],
             GKA_O=t(gka[0] + 2)[1], KJZ_O=t(jz + 1)[1], KFZ_O=t(fz + 1)[1], DZO=dz, ZO=zo, HDO=d[hd + 8], TKS=tks)
    return s, c


# (region length, stub) per site; FB / FT keep their own branches after the call
HOOKS = (('JZ', 5, 'sp_jz'), ('FZ', 5, 'sp_fz'), ('HD', 9, 'sp_head'), ('CEIL0', 11, 'sp_ceil'),
         ('CEIL1', 11, 'sp_ceil'), ('BAND', 8, 'sp_band'), ('GKA0', 9, 'sp_gka'), ('GKA1', 9, 'sp_gka'),
         ('CPU', 13, 'sp_cpu'), ('FB', 15, 'sp_fb'), ('FT', 14, 'sp_ft'), ('KD', 5, 'sp_kick'), ('GR', 5, 'sp_grav'),
         ('AT', 13, 'sp_at'), ('BLO', 8, 'sp_blo'), ('AF', 17, 'sp_af'))

ASM = r"""
; ---- the base: ebp = SPB (PC-relative: no fixup); [ebp] = obj2's base (the band's only fixup). The DIFFICULTY /
;      DRIBBLING data (difficulty.py, page 15) is in this object too: [dword ebp + X - SPB], no fixup either
align 4
SPB: dd O2BASE
TAGS: db 'SETP'
SP_W: dw SP_START                       ; the option: 0 CLASSICI, 1 REALISTICI, 2 ARCADE (a word: the string table)
SP_OK: db 0                             ; 1 = a kick-off without SWOS++ seen (df_kick: sp_set; SWOS++ never changes)
    db 0
PR_D: dd 0                              ; (practice: PR_WORK + 1 - SPB, filled by setpieces.late; 0 = no practice)
TAB_P: dd 0                             ; (the row's string table, its pointers filled by sp_add: no fixups)
    dw 0
    dd 0, 0, 0
sp_base:
    call .n
.n: pop ebp
    sub ebp, .n - SPB
    ret

; ---- ebp = SPB; ZF = 1: the original game (CLASSICI, SWOS++ or a training game); every other register kept
sp_on:
    call sp_base
    push ecx
    mov ecx, [ebp]
    cmp word [ecx + TRG_O], 0           ; (a training game: original unless a practice - PR_D = PR_WORK + 1 - SPB, the
    je .c                               ;  practice's KIND, 0 = none; setpieces.late fills PR_D after swe.patch)
    mov ecx, [ebp + PR_D - SPB]
    test ecx, ecx
    jz .x
    cmp byte [ebp + ecx], 0
    je .x
.c: test byte [ebp + SP_OK - SPB], 1
    jz .x
    cmp word [ebp + SP_W - SPB], 0
.x: pop ecx
    ret

sp_set:                                 ; (df_kick, past its SWOS++ / training gates)
    push ebp
    call sp_base
    mov byte [ebp + SP_OK - SPB], 1
    pop ebp
    ret

; ---- DIFFICULTY's OPTIONS handlers and the save item's pack, moved here from page 15 (MC 14/11), PC-relative
df_tog:                                 ; DIFFICULTY (fire): NORMAL -> HARD -> EASY -> NORMAL (L2 / L4: back to NORMAL)
    push ebp
    call sp_base
    mov ax, [dword ebp + DF_W - SPB]
    cmp ax, 0
    jne .a
    mov ax, 2
    jmp .s
.a: cmp ax, 2
    jne .b
    mov ax, 1
    jmp .s
.b: xor eax, eax
.s: mov [dword ebp + DF_W - SPB], ax
    pop ebp
df_draw:
    call df_pack
    jmp near DRAWITEM
df_rtog:                                ; DRIBBLING (fire): CLASSIC -> NEW -> CUSTOM (and its page) -> CLASSIC
    push ebp
    call sp_base
    mov ax, [dword ebp + DF_DR - SPB]
    inc ax
    cmp ax, 2
    jbe .s
    xor eax, eax
.s: mov [dword ebp + DF_DR - SPB], ax
    cmp ax, 2
    je .p
    pop ebp
    jmp df_draw
.p: call df_pack
    call near DP_FALL
    call sp_base
    lea eax, [dword ebp + DP_MENU - SPB]
    mov ecx, [ebp]
    mov [ecx + A6_O], eax               ; the page (OPTIONS comes back unpacked: df_ret, CUSTOM shown)
    pop ebp
    jmp near SHOW_MENU
sp_tog:                                 ; CALCI PIAZZATI (fire): CLASSICI -> REALISTICI -> ARCADE -> CLASSICI
    push ebp
    call sp_base
    inc word [ebp + SP_W - SPB]
    cmp word [ebp + SP_W - SPB], 2
    jbe .s
    mov word [ebp + SP_W - SPB], 0
.s: pop ebp
    jmp df_draw
df_pack:                                ; DF_SV = DF_SH = DIFFICULTY | DRIBBLING << 4 | CALCI PIAZZATI << 6 (bits 6-7)
    push eax
    push ebp
    call sp_base
    mov al, [ebp + SP_W - SPB]
    shl al, 2
    or al, [dword ebp + DF_DR - SPB]
    shl al, 4
    or al, [dword ebp + DF_W - SPB]
    mov [dword ebp + DF_SV - SPB], al
    mov [dword ebp + DF_SH - SPB], al
    pop ebp
    pop eax
    ret
sp_load_j:                              ; (engine, pushad around it: after a career load - then df_load)
    call sp_base
    mov al, [dword ebp + DF_SV - SPB]
    call sp_unp
    jmp near DF_LOAD
sp_new_j:                               ; (engine: after a new career's defaults - then df_new)
    call sp_base
    mov al, [dword ebp + DF_SH - SPB]
    call sp_unp
    jmp near DF_NEW
sp_unp:                                 ; (CALCI PIAZZATI = bits 6-7 of al: 3 -> CLASSICI; a 4.2 beta's NUOVI = 1)
    shr al, 6
    and eax, 3
    cmp eax, 2
    jbe .s
    xor eax, eax
.s: mov [ebp + SP_W - SPB], ax
    ret

; ---- in ebx = the OPTIONS menu, entries NB..NB+3 in (df_add, before its layout loop): NB+4 / NB+5 = copies of
;      NB+2 / NB+3 (DRIBBLING) one row lower; NB+3 -> NB+5 -> what was below NB+3 (EXIT TO DOS)
sp_add:
    pushad
    call sp_base
    lea edi, [ebx + 16h + (NB + 4) * 38h]
    lea esi, [ebx + 16h + (NB + 2) * 38h]
    mov ecx, 2 * 38h
    rep movsb
    sub edi, 2 * 38h
    mov word [edi + 2], NB + 4
    lea eax, [ebp + S_PLBL - SPB]
    mov [edi + 26h], eax
    mov word [edi + 38h + 2], NB + 5
    lea eax, [ebp + TAB_P - SPB]
    mov [edi + 38h + 26h], eax
    lea ecx, [ebp + SP_W - SPB]         ; (the string table: the word, then the three strings)
    mov [eax], ecx
    lea ecx, [ebp + S_P0 - SPB]
    mov [eax + 6], ecx
    lea ecx, [ebp + S_P1 - SPB]
    mov [eax + 10], ecx
    lea ecx, [ebp + S_P2 - SPB]
    mov [eax + 14], ecx
    lea eax, [ebp + sp_tog - SPB]
    mov [edi + 38h + 2Ah], eax
    add word [edi + 16h], 3 * SRCP      ; (copies of the bottom row's y still: three source rows below it, one
    add word [edi + 38h + 16h], 3 * SRCP ;  below DRIBBLING once df_add moves that one; the layout loop places it)
    lea esi, [ebx + 16h + (NB + 3) * 38h]
    movzx ecx, byte [esi + 0Bh]         ; (NB+3's down: EXIT TO DOS - now NB+5's)
    mov byte [edi + 38h + 0Ah], NB + 3
    mov [edi + 38h + 0Bh], cl
    mov byte [edi + 38h + 12h], NB + 3
    mov [edi + 38h + 13h], cl
    mov byte [esi + 0Bh], NB + 5
    mov byte [esi + 13h], NB + 5
    cmp cl, 0FFh
    je .n
    imul ecx, ecx, 38h                  ; (and the entry below: up NB+3 -> NB+5)
    lea ecx, [ebx + 16h + ecx]
    cmp byte [ecx + 0Ah], NB + 3
    jne .u
    mov byte [ecx + 0Ah], NB + 5
.u: cmp byte [ecx + 12h], NB + 3
    jne .n
    mov byte [ecx + 12h], NB + 5
.n: add word [ebx + 10h], 2
    add dword [ebx + 12h], 2 * 38h
    popad
    ret

; ---- headers go down (replaces `mov eax, kBallJumpHeaderDeltaZ` / `mov eax, kFlyingHeaderBallDeltaZ`)
sp_jz:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov eax, [ebp]
    mov eax, [eax + KJZ_O]
    jz .x
    mov eax, JZ_NEW
    mov byte [ebp + FK_ST - SPB], 0     ; (a header: the free kick's dip ends)
.x: pop ebp
    ret
sp_fz:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov eax, [ebp]
    mov eax, [eax + KFZ_O]
    jz .x
    mov eax, FZ_NEW
    mov byte [ebp + FK_ST - SPB], 0     ; (a header: the free kick's dip ends)
.x: pop ebp
    ret

; ---- HEADING = placement (replaces `mov esi, A4` / `mov al, [esi + heading]` in PlayerHittingJumpHeader, after the
;      deltaZ is set): a jump header's ball deltaZ = JZ_NEW - heading x JZ_STEP
sp_head:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov esi, [ebp]
    mov esi, [esi + A4_O]
    mov al, [esi + HDO]
    jz .x
    push ebx
    push ecx
    mov ebx, [ebp]
    mov ebx, [ebx + A2_O]               ; (the ball)
    cmp dword [ebx + DZO], JZ_NEW       ; (a jump header: flying / lob headers have their own deltaZ)
    jne .y
    movzx ecx, al
    and ecx, 7
    imul ecx, ecx, JZ_STEP
    sub [ebx + DZO], ecx
.y: pop ecx
    pop ebx
.x: pop ebp
    ret

; ---- the contact window's ceiling (replaces `mov esi, A2` / `cmp word [esi + z], 15`, then `ja`)
sp_ceil:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov esi, [ebp]
    mov esi, [esi + A2_O]
    jz .c
    cmp byte [ebp + FK_ST - SPB], 1     ; (a free kick on its way to the wall: the wall heads as today, ceiling 15)
    je .c
    cmp word [esi + ZO], CEIL_NEW
    pop ebp
    ret
.c: cmp word [esi + ZO], 15
    pop ebp
    ret

; ---- the keeper's catch band top (replaces `cmp ballDefensiveZ, 27`, then `jg`)
sp_band:
    push ebp
    push eax
    push ecx
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov eax, 27
    jz .c
    mov eax, BAND_NEW
.c: mov ecx, [ebp]
    cmp [ecx + BDZ_O], ax
    pop ecx
    pop eax
    pop ebp
    ret

; ---- the 6-yard-box bypass of the word29 gate (replaces `mov ax, ballInGoalkeeperArea` / `or ax, ax`, then `jnz`)
sp_gka:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    push ecx
    mov ecx, [ebp]
    mov ax, [ecx + GKA_O]
    pop ecx
    jz .c
    xor ax, ax                          ; (NUOVI: no bypass)
.c: or ax, ax
    pop ebp
    ret

; ---- the CPU header gate (replaces `mov esi, A5` / `cmp [esi + ballDistance], 648`, then `ja`)
sp_cpu:
    push ebp
    push eax
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov esi, [ebp]
    mov eax, 648
    jz .c
    cmp word [esi + BALL_O + ZO], 8     ; (the ball in the air)
    jb .c
    mov eax, CPU_NEW
.c: mov esi, [esi + A5_O]
    cmp [esi + 4Ah], eax
    pop eax
    pop ebp
    ret

; ---- the CPU header facing (FB replaces `cmp D7, 5` before `jz facing` / `jmp no_fire`; FT `cmp D7, 1` before `jnz
;      no_fire`): NUOVI also accepts right / left (2 / 6) with the ball wide; ZF = 1 accepted
sp_fb:
    push ebp
    push eax
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov eax, [ebp]
    mov ax, [eax + D7_O]
    jz .c
    call sp_wide
    jz .x
.c: cmp ax, 5
.x: pop eax
    pop ebp
    ret
sp_ft:
    push ebp
    push eax
    call sp_on                         ; (ebp = SPB, ZF; only mov / push / pop until the jz)
    mov eax, [ebp]
    mov ax, [eax + D7_O]
    jz .c
    call sp_wide
    jz .x
.c: cmp ax, 1
.x: pop eax
    pop ebp
    ret
sp_wide:                                ; ax = direction; ZF = 1: 2 / 6 and the ball's x outside 193..478
    push ecx
    cmp ax, 2
    je .d
    cmp ax, 6
    jne .no
.d: mov ecx, [ebp]
    movsx ecx, word [ecx + BALL_O + 20h]
    cmp ecx, 193
    jl .yes
    cmp ecx, 478
    jg .yes
.no:test esp, esp                       ; (ZF = 0)
    jmp .x
.yes:cmp ecx, ecx
.x: pop ecx
    ret

; ---- §3 free kicks (NUOVI; a kick from a wall-zone free kick, states 6..12, 87..202 px from the line)
FK_ST: db 0                             ; 0 off, 1 kicked (before the wall), 2 dipping
FK_SH: db 0                             ; the taker's aim error amplitude (px at the line, by SHOOTING: FK_WT)
FK_CU: db 0                             ; the CPU curl: 0 none, 1 toward +x, 2 toward -x
FK_UP: db 0                             ; 1 = attacking the top goal (line y 129)
FK_TM: dd 0                             ; the kicking team (TeamGeneralInfo)
FK_Y0: dw 0                             ; the ball's y at the kick
FK_N: dw 0                              ; ticks since the kick
FK_E: dd 0                              ; the extra gravity per tick after the wall (16.16)
FK_TT: dd 0                             ; this kick's target z at the line (16.16): FK_T +- FK_SH px
FK_R: dd 12345                          ; (the curl's own LCG: the game's RNGs untouched)
FK_WT: db FKW0, FKW1, FKW2, FKW3, FKW4, FKW5, FKW6, FKW7         ; (REALISTICI)
    db FKX0, FKX1, FKX2, FKX3, FKX4, FKX5, FKX6, FKX7             ; (ARCADE)

; the kick record (replaces PlayerKickingBall's `mov eax, kBallKickingDeltaZ`; A6 = the team, A1 = the taker)
sp_kick:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF)
    jz .x
    pushad
    mov byte [ebp + FK_ST - SPB], 0
    mov esi, [ebp]
    cmp word [esi + GSP_O], 100         ; (a kick in play: not a free kick)
    je .d
    movzx eax, word [esi + GS_O]
    cmp eax, 6
    jb .d
    cmp eax, 12
    ja .d
    movsx eax, word [esi + BALL_O + 24h]
    mov [ebp + FK_Y0 - SPB], ax
    lea ecx, [eax - 129]                ; (to the top line)
    mov edx, 769
    sub edx, eax                        ; (to the bottom line)
    mov bl, 1
    cmp ecx, edx
    jle .u
    mov ecx, edx
    mov bl, 0
.u: cmp ecx, 87
    jl .d
    cmp ecx, 202
    jg .d
    mov [ebp + FK_UP - SPB], bl
    mov edi, [esi + A6T_O]
    mov [ebp + FK_TM - SPB], edi
    mov edx, [esi + A1_O]
    movzx eax, word [edx + 2]           ; (GetPlayerPointerFromShirtNumber: inGameTeamPtr + (ordinal - 1) x 61)
    dec eax
    imul eax, eax, 61
    add eax, [edi + 0Ah]
    movzx eax, byte [eax + HDO - 1]     ; SHOOTING (just before HEADING)
    and eax, 7
    cmp word [ebp + SP_W - SPB], 2
    jb .r
    add eax, 8                          ; (ARCADE's table)
.r: mov al, [ebp + FK_WT - SPB + eax]
    mov [ebp + FK_SH - SPB], al
    mov byte [ebp + FK_CU - SPB], 0
    cmp word [edi + 4], 0               ; (playerNumber 0: the CPU's team)
    jne .k
    mov eax, [ebp + FK_R - SPB]
    imul eax, eax, 1103515245
    add eax, 12345
    add ax, [esi + BALL_O + 1Eh]        ; (the ball's x fraction)
    mov [ebp + FK_R - SPB], eax
    shr eax, 16
    mov ecx, FK_C                       ; (REALISTICI 1 in 2: else today's kick; ARCADE FK_C2)
    cmp word [ebp + SP_W - SPB], 2
    jb .c
    mov ecx, FK_C2
.c: test eax, ecx
    jnz .k
    movsx ecx, word [esi + BALL_O + 20h]
    mov bl, 1                           ; the far post: from the left (x < 324) curl toward +x
    cmp ecx, 324
    jl .s
    mov bl, 2
    cmp ecx, 344
    jg .s
    test eax, 10h                       ; (central: either side)
    jz .s
    mov bl, 1
.s: mov [ebp + FK_CU - SPB], bl
.k: mov eax, [ebp + FK_R - SPB]       ; (the aim error: FK_T + uniform -a..+a px, a = FK_SH)
    imul eax, eax, 1103515245
    add eax, 12345
    mov [ebp + FK_R - SPB], eax
    shr eax, 16
    movzx ecx, byte [ebp + FK_SH - SPB]
    lea ebx, [ecx * 2 + 1]
    xor edx, edx
    div ebx
    sub edx, ecx
    shl edx, 16
    add edx, FK_T
    mov [ebp + FK_TT - SPB], edx
    mov word [ebp + FK_N - SPB], 0
    mov byte [ebp + FK_ST - SPB], 1
.d: popad
.x: mov eax, [ebp]
    mov eax, [eax + KDZ_O]
    pop ebp
    ret

; the CPU's curl (replaces ApplyBallAfterTouch's `mov esi, A6` / `mov ax, [esi + passInProgress]`): the direction
; held = facing + 3 or + 5 (back-diagonal: the human's high kick with spin, over the wall at ~38 px - the wall's real
; distance, meter 14/11 - then the dip), the side whose x sign is FK_CU's
sp_at:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF)
    jz .x
    cmp byte [ebp + FK_ST - SPB], 0
    je .x
    cmp byte [ebp + FK_CU - SPB], 0
    je .x
    push eax
    push ecx
    push edx
    mov esi, [ebp]
    mov esi, [esi + A6T_O]
    cmp esi, [ebp + FK_TM - SPB]
    jne .p
    cmp word [esi + 76h], 0             ; (spinTimer: the after-touch window)
    jl .p
    movzx eax, word [esi + 38h]         ; (controlledPlDirection)
    and eax, 7
    lea ecx, [eax + 3]
    and ecx, 7
    mov dl, 1                           ; x sign of direction ecx: 1..3 -> 1 (+x), 5..7 -> 2 (-x), 0 / 4 -> 0
    cmp ecx, 4
    jb .a
    mov dl, 2
    ja .a
    mov dl, 0
.a: test ecx, ecx
    jnz .b
    mov dl, 0
.b: cmp dl, [ebp + FK_CU - SPB]
    je .w
    lea ecx, [eax + 5]
    and ecx, 7
.w: mov [esi + 2Ch], cx                 ; (currentAllowedDirection)
.p: pop edx
    pop ecx
    pop eax
.x: mov esi, [ebp]
    mov esi, [esi + A6T_O]
    mov ax, [esi + 80h]
    pop ebp
    ret

; the dip (replaces UpdateBall's `mov eax, kBallAirFriction`, the ball in the air): past the wall (FK_WALL px) and over
; its head (z > FK_CLR), the extra gravity that brings the ball to FK_TT at the line (FK_T +- the taker's aim error)
sp_grav:
    push ebp
    call sp_on                         ; (ebp = SPB, ZF)
    mov eax, [ebp]
    mov eax, [eax + KAF_O]
    jz .x
    cmp byte [ebp + FK_ST - SPB], 0
    je .x
    pushad
    mov esi, [ebp]
    lea edi, [esi + BALL_O]
    inc word [ebp + FK_N - SPB]
    cmp word [ebp + FK_N - SPB], 100
    ja .off
    movsx eax, word [edi + 24h]         ; y
    movsx ecx, word [ebp + FK_Y0 - SPB]
    mov edx, [edi + 32h]                ; deltaY (16.16)
    cmp byte [ebp + FK_UP - SPB], 1
    jne .dn
    sub ecx, eax                        ; travelled (toward the top line: y falls)
    sub eax, 129                        ; remaining
    neg edx                             ; (deltaY toward the goal)
    jmp .g
.dn:sub ecx, eax
    neg ecx
    neg eax
    add eax, 769
.g: cmp byte [ebp + FK_ST - SPB], 2
    je .dip
    cmp ecx, FK_WALL
    jl .k                               ; (before the wall)
    test edx, edx
    jle .off                            ; (not toward the goal: a touch)
    cmp word [edi + 28h], FK_CLR
    jle .off                            ; (a drive: the wall's to head, no dip)
    test eax, eax
    jle .off
    shl eax, 16
    mov ebx, edx
    lea eax, [eax + ebx - 1]
    xor edx, edx
    div ebx                             ; n = the ticks to the line: ceil(remaining / deltaY) + 1 (the ball slows by
    inc eax                             ;  4 a tick and y is read whole: tools/hosttest fk_check, z 8..13 at the line)
    test eax, eax
    jz .off
    cmp eax, 200
    ja .off
    mov ebx, eax
    mov eax, [edi + 36h]
    imul eax, ebx                       ; n x deltaZ
    add eax, [edi + 26h]                ; + z
    sub eax, [ebp + FK_TT - SPB]        ; - this kick's target
    add eax, eax
    lea ecx, [ebx + 1]
    imul ecx, ebx                       ; n (n + 1)
    cdq
    idiv ecx                            ; G' = 2 (z + n dz - T) / (n (n + 1))
    mov ecx, [ebp]
    sub eax, [ecx + KAF_O]              ; e = G' - g (the full dip: SHOOTING sets the aim error, FK_TT)
    cmp eax, FK_MAX
    jle .m1
    mov eax, FK_MAX
.m1:cmp eax, FK_MIN
    jge .m2
    mov eax, FK_MIN
.m2:mov [ebp + FK_E - SPB], eax
    call SPXE + 5                       ; (sp_tx: this kick's line target x, SPX)
    mov byte [ebp + FK_ST - SPB], 2
    jmp .ad
.dip:test edx, edx
    jle .off
    cmp word [edi + 28h], 0
    jle .off                            ; (on the ground: a bounce)
.ad:call SPXE                           ; (sp_steer, SPX: the sideways steer)
    mov eax, [ebp + FK_E - SPB]
    add [esp + 28], eax                 ; (pushad's eax)
    jmp .k
.off:mov byte [ebp + FK_ST - SPB], 0
.k: popad
.x: pop ebp
    ret

; the catch band's low bound for a dipping free kick (replaces `cmp ballDefensiveZ, 12`, then `jle`)
sp_blo:
    push ebp
    push eax
    push ecx
    call sp_on                         ; (ebp = SPB, ZF)
    mov eax, 12
    jz .c
    cmp byte [ebp + FK_ST - SPB], 2
    jne .c
    mov eax, BLO_NEW
.c: mov ecx, [ebp]
    cmp [ecx + BDZ_O], ax
    pop ecx
    pop eax
    pop ebp
    ret
"""


ASM_X = r"""
; ==== SPX (MC 14/11: setpieces' overflow band 0x1A400..0x1A800, its own unit; PC-relative to SPB through sp_on's ebp:
;      no fixups)
    jmp near sp_steer                   ; SPX + 0 (the main band calls these two: assembled before SPX)
    jmp near sp_tx                      ; SPX + 5

; ---- §3 the sideways steer (14/11, fk3: the curled CPU kick crossed the line 40-60 px wide). The ball flies at its
;      dest (UpdateBall: CalculateDeltaXAndY toward destX / destY each tick; the after-touch curls by moving dest). While
;      a CPU curled kick dips (sp_grav, edi = the ball, ebp = SPB, inside its pushad): the line crossing
;      x_c = x + (destX - x) (yL - y) / (destY - y) moves toward FK_TX by at most FK_XC px a tick (destX moved to match).
FK_TX: dw 0                             ; this kick's target x at the line
    dw 0
sp_tx:                                  ; (at the dip's start) FK_TX = the open side's inside post (FK_CU 1: 366 - FK_XI,
    push eax                            ;  2: 302 + FK_XI) + uniform -a..+a, a = FK_SH (the same aim error table)
    push ecx
    push edx
    mov eax, [ebp + FK_R - SPB]
    imul eax, eax, 1103515245
    add eax, 12345
    mov [ebp + FK_R - SPB], eax
    shr eax, 16
    movzx ecx, byte [ebp + FK_SH - SPB]
    lea ecx, [ecx * 2 + 1]
    xor edx, edx
    div ecx
    movzx eax, byte [ebp + FK_SH - SPB]
    sub edx, eax                        ; (-a..+a)
    add edx, 366 - FK_XI
    cmp byte [ebp + FK_CU - SPB], 1
    je .s
    add edx, 302 + FK_XI - (366 - FK_XI)
.s: mov [ebp + FK_TX - SPB], dx
    pop edx
    pop ecx
    pop eax
    ret
sp_steer:
    cmp byte [ebp + FK_CU - SPB], 0     ; (CPU curled kicks only: the human aims his own)
    je .x
    movsx eax, word [edi + 24h]
    movsx ecx, word [edi + 3Ch]
    sub ecx, eax                        ; dy = destY - y
    mov esi, 129
    cmp byte [ebp + FK_UP - SPB], 1
    je .u
    mov esi, 769
.u: sub esi, eax                        ; ly = yL - y
    mov eax, esi
    xor eax, ecx
    js .x                               ; (dest behind the ball: leave it)
    mov eax, esi
    cdq
    xor eax, edx
    sub eax, edx
    cmp eax, 4
    jl .x                               ; (at the line)
    test ecx, ecx
    jz .x
    movsx ebx, word [edi + 20h]         ; x
    movsx eax, word [edi + 3Ah]
    sub eax, ebx
    imul eax, esi
    cdq
    idiv ecx                            ; x_c - x
    add eax, ebx
    movsx edx, word [ebp + FK_TX - SPB]
    sub edx, eax                        ; s = FK_TX - x_c
    cmp edx, FK_XC
    jle .a
    mov edx, FK_XC
.a: cmp edx, -FK_XC
    jge .b
    mov edx, -FK_XC
.b: mov eax, edx
    imul eax, ecx
    cdq
    idiv esi                            ; destX += s dy / ly
    add [edi + 3Ah], ax
.x: ret

; ARCADE fouls (Davide GO 14/11; replaces `mov esi, A1 / cmp [esi + tackleState], TS_GOOD_TACKLE`, then after the
; call: jz comment / jc foul_concedeed). A clean tackle on a victim (A2) in the free-kick zone - AF_D0..AF_D1 px from
; the fouling team's (A6) goal line, x AF_X0..AF_X1: outside the area - is a foul 1 in 3 (AF_P / 65536) in ARCADE.
; ZF = 1: a clean tackle, no foul (today); CF = 1 (ZF = 0): a foul; neither: not clean (today's direction test).
; esi = A1 on exit, as the original
sp_af:
    pushad
    call sp_on                          ; (ebp = SPB; ZF = 1 the original game)
    mov ecx, [ebp]
    mov esi, [ecx + A1_O]
    mov [esp + 4], esi
    setz bl
    cmp word [esi + TKS], 2             ; (TS_GOOD_TACKLE)
    jne .no
    or bl, [ebp + SP_W - SPB]           ; (ARCADE = 2 and not the original game: bl = 2)
    cmp bl, 2
    jne .ct
    mov edx, [ecx + A2_O]
    mov ax, [edx + 20h]
    sub ax, AF_X0
    cmp ax, AF_X1 - AF_X0
    ja .ct
    mov ax, [edx + 24h]
    mov ebx, [ecx + A6T_O]
    sub ax, 129                         ; (the top team - topTeamData < its opponentsTeam - defends y 129)
    cmp ebx, [ebx]
    jb .d
    neg ax
    add ax, 769 - 129
.d: sub ax, AF_D0
    cmp ax, AF_D1 - AF_D0
    ja .ct
    mov eax, [ebp + FK_R - SPB]
    imul eax, eax, 1103515245
    add eax, 12345
    mov [ebp + FK_R - SPB], eax
    cmp eax, AF_P << 16
    jae .ct
    popad
    test esp, esp
    stc
    ret
.ct:popad
    cmp eax, eax
    ret
.no:popad
    test esp, esp
    ret

"""


FROM_DF = ('df_tog', 'df_rtog', 'df_pack', 'sp_add', 'sp_set')     # (difficulty.py's page 15 calls / points to these)


def _src(lang):
    db = lambda x: ', '.join(str(ch) for ch in x.encode() + b'\0')
    return ASM + f'S_PLBL: db {db(LABEL[lang])}\n' + ''.join(f'S_P{i}: db {db(t)}\n' for i, t in enumerate(VALUES[lang]))


def _sym(p, start, df_lab, df_sym):
    import difficulty as df
    s, c = FOUND.get(id(p)) or find(p)             # (pass 1 runs before difficulty's hooks: df.find needs them unpatched)
    FOUND.clear()
    FOUND[id(p)] = (s, c)
    k = knobs()
    return {**{n: (0, v) for n, v in c.items()}, 'O2BASE': (2, 0), 'SP_START': (0, start),
            'NB': (0, df.NB), 'SRCP': (0, df.SRCP), 'TRG_O': (0, df_sym['TRG'][1]), 'A6_O': (0, df_sym['A6_'][1]),
            'DRAWITEM': df_sym['DRAWITEM'], 'SHOW_MENU': df_sym['SHOW_MENU'],
            **{n.upper() if n.islower() else n: (4, df_lab[n] if n in df_lab or not df.trace() else df_lab['DF_W'])
               for n in ('DF_W', 'DF_DR', 'DF_SV', 'DF_SH', 'DP_MENU', 'dp_fall', 'df_load', 'df_new')},
            # (DIFF_TRACE builds have no PERSONALIZZATO page - dp_asm page=False -: DP_MENU / dp_fall point at DF_W,
            #  never reached: a traced match never opens OPTIONS; M3 corner meter 14/11)
            'JZ_NEW': (0, k['JZ'] & 0xFFFFFFFF), 'JZ_STEP': (0, k['JST']), 'FZ_NEW': (0, k['FZ']),
            'CEIL_NEW': (0, k['CEIL']), 'BAND_NEW': (0, k['BAND']), 'CPU_NEW': (0, k['CPU']),
            'FK_T': (0, k['FKT']), 'BLO_NEW': (0, k['BLO']), 'FK_C': (0, k['FKC']), 'FK_C2': (0, k['FKC2']), 'FK_MAX': (0, k['FKMAX']),
            'AF_P': (0, k['AFP']), 'AF_D0': (0, k['AFD0']), 'AF_D1': (0, k['AFD1']), 'AF_X0': (0, k['AFX0']),
            'AF_X1': (0, k['AFX1']), 'FK_XI': (0, k['FKXI']), 'FK_XC': (0, k['FKXC']), 'SPXE': (4, __import__('swreg').SPX_AT),
            'FK_MIN': (0, k['FKMIN'] & 0xFFFFFFFF), 'FK_WALL': (0, k['FKWALL']), 'FK_CLR': (0, k['FKCLR']),
            **{f'FKW{i}': (0, w) for i, w in enumerate(k['FKW'])}, **{f'FKX{i}': (0, w) for i, w in enumerate(k['FKW2'])}}, s


def pass1(p, lang, df_sym):
    """The band's labels before difficulty.py is assembled (its data at placeholder offsets: every reference to it
    is a dword displacement / rel32, so the sizes don't move; patch() asserts the same labels)."""
    import swreg
    ph = {n: 0x2000 + 0x10 * i for i, n in enumerate(('DF_W', 'DF_DR', 'DF_SV', 'DF_SH', 'DP_MENU', 'dp_fall',
                                                         'df_load', 'df_new'))}
    sym, _ = _sym(p, 0, ph, df_sym)
    lab = nasmcave.labels(_src(lang), swreg.SETPIECE_AT, sym)
    PASS1.clear()
    PASS1.update(lab)
    return lab


def patch(p, lang):
    if not on():
        return None
    import difficulty as df
    import engine
    import modver
    import swreg
    assert modver.is_test(), 'SP_TEST: test builds only (until the OPTIONS row)'
    assert df.SP_ROW and df.LABELS.get('df_add'), 'setpieces: after difficulty with its OPTIONS rows (SP_ROW)'
    start = int(os.environ.get('SP_TEST') or 0)
    assert start in (0, 1, 2), 'SP_TEST=0 (CLASSICI) / 1 (REALISTICI) / 2 (ARCADE)'
    sym, s = _sym(p, start, df.LABELS, df.SYMS)
    at = swreg.SETPIECE_AT
    src = _src(lang)
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert all(lab[k] == v for k, v in PASS1.items()), 'setpieces: labels moved since pass 1'
    assert len(fix) == 1 and len(rel) == 2, ('setpieces: SPB + DRAWITEM / SHOW_MENU only', fix, rel)
    from complist import px
    for t in (LABEL[lang],) + VALUES[lang]:
        assert px(t) <= 138 and re.fullmatch(r"[A-Z ']+", t), t
    left = swreg.SETPIECE_END - at - len(code)
    assert left >= swreg.SETPIECE_MIN, ('setpieces: band room', left)
    assert p.le.obj(4).npages * 0x1000 >= swreg.SETPIECE_END, 'setpieces: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.SETPIECE_END - at)), 'setpieces: band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    xsym = {**sym, **{n: (4, v) for n, v in lab.items() if '.' not in n and n not in sym}}
    xcode, xfix, xrel = nasmcave.assemble_obj(ASM_X, swreg.SPX_AT, xsym, 4)
    assert not xfix and not xrel, ('SPX: no fixups', xfix, xrel)
    xleft = swreg.SPX_END - swreg.SPX_AT - len(xcode)
    assert xleft >= swreg.SETPIECE_MIN, ('SPX: band room', xleft)
    assert p.le.obj(4).npages * 0x1000 >= swreg.SPX_END, 'SPX: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.SPX_AT, swreg.SPX_END - swreg.SPX_AT)), 'SPX band not free'
    p.put(4, swreg.SPX_AT, xcode)
    xl = nasmcave.labels(ASM_X, swreg.SPX_AT, xsym)
    assert (xl['sp_steer'], xl['sp_tx']) == (xcode[1] + 5 + swreg.SPX_AT + struct.unpack_from('<i', xcode, 1)[0] - xcode[1],
                                             swreg.SPX_AT + 10 + struct.unpack_from('<i', xcode, 6)[0]), 'SPX jump table'
    lab = {**lab, **{n: v for n, v in nasmcave.labels(ASM_X, swreg.SPX_AT, xsym).items() if n not in lab}}
    assert engine.CALL_AT.get('df_load') == (4, df.LABELS['df_load']), 'engine: df_load'
    engine.CALL_AT['df_load'] = (4, lab['sp_load_j'])  # (CALCI PIAZZATI from the item's bit 6 first: same fixup count)
    engine.CALL_AT['df_new'] = (4, lab['sp_new_j'])
    d = p.le.obj_bytes(1)
    fb_f = s['FB'] + 10 + struct.unpack_from('<b', d, s['FB'] + 9)[0]          # (jz facing)
    fb_n = s['FB'] + 15 + struct.unpack_from('<i', d, s['FB'] + 11)[0]         # (jmp no_fire)
    ft_n = s['FT'] + 14 + struct.unpack_from('<i', d, s['FT'] + 10)[0]         # (jnz no_fire)
    skip = set(filter(None, os.environ.get('SP_SKIP', '').split(',')))
    for key, n, l in HOOKS:
        if key in skip:
            continue
        df._hook(p, s[key], n, n, lab[l])
    if 'FB' not in skip:                                # call sp_fb / jz facing / jmp no_fire / 3 nops
        o = s['FB']
        r8 = fb_f - (o + 7)
        assert -128 <= r8 < 128
        p.put(1, o + 5, struct.pack('<Bb', 0x74, r8) + b'\xe9' + struct.pack('<i', fb_n - (o + 12)) + b'\x90' * 3)
    if 'AF' not in skip:                                # call sp_af / jz comment / jc foul_concedeed
        o = s['AF']
        p.put(1, o + 5, b'\x0f\x84' + struct.pack('<i', s['AF_CMT'] - (o + 11)) + b'\x0f\x82'
              + struct.pack('<i', s['AF_FOUL'] - (o + 17)))
    if 'FT' not in skip:                                # call sp_ft / jnz no_fire / 3 nops
        o = s['FT']
        p.put(1, o + 5, b'\x0f\x85' + struct.pack('<i', ft_n - (o + 11)) + b'\x90' * 3)
    LABELS.clear()
    LABELS.update(lab)
    SITES.clear()
    SITES.update(s)
    print(f'exe: set pieces (SP_TEST={start}): code obj4+{at:#x} ({len(code)} B, {left} B left), SPX obj4+{swreg.SPX_AT:#x} '
          f'({len(xcode)} B, {xleft} B left), {len(HOOKS)} obj1 sites')
    return at + len(code)


def late(p):
    """After swe.patch: PR_D = the practice's KIND byte (Shaved's PR_WORK + 1, swe.LABELS, obj4) - SPB; 0 = no practice."""
    import swe
    if not LABELS:
        return
    pr = getattr(swe, 'LABELS', {}).get('PR_WORK')
    if pr is None:
        return
    assert pr[0] == 4, ('PR_WORK: obj4 (Shaved 14/11)', pr)
    p.put(4, LABELS['PR_D'], struct.pack('<i', pr[1] + 1 - LABELS['SPB']))
    print(f'exe: set pieces: practice gate PR_WORK obj4+{pr[1]:#x}')


LABELS = {}
SITES = {}
PASS1 = {}
FOUND = {}
