"""4.2 POSITION TRAITS (1)-(3) (Marco; Davide 15/11; design internal/handoff/trhead-design.md): the TRHD band.

With RUOLI SI (and not SWOS++ / a plain training game: tr_live, the conditions of setpieces' sp_on):
(1) a jump header goes DOWN only in the header's ATTACKING box (penalty area of the goal his team attacks), by
    setpieces' own formula (JZ_NEW - HEADING x JZ_STEP; the flying header FZ_NEW), whatever CALCI PIAZZATI says;
    everywhere else it is the original header (up and away), also under CALCI PIAZZATI NUOVI. Any outfield file
    position (TR_HMASK, a bit per position; 0x80 = file attackers only). A header on a live whipped cross (TR_WF, set
    by (2)) counts TR_WHB more deltaZ down and TR_WHS more ball speed.
(3) a file defender (TR_DMASK: position 3) in his OWN box reaches the ball for a header from further: the contact
    limit ballDistance <= 64 (8 px, squared) becomes 64 + TR_RST x HEADING (HEADING 7: 10.95 px).
(2) the whipped cross (side-agnostic: whoever plays it, human or computer): a kick (PlayerKickingBall) by a file RW /
    LW (position 4 / 5) with the BALL in the wide attacking zone, the kicker facing the pitch's centre line (direction
    1..3 from the left half, 5..7 from the right) and no setpieces free kick in flight (FK_ST 0: under CALCI PIAZZATI
    CLASSICI wide free kicks and corners whip too) is armed by tr_kick (TR_ZK); if that kick's after-touch is 'back'
    (the game's high kick, ApplyBallAfterTouch at spinTimer 4), tr_hk makes it the whip: deltaZ TR_WDZ, speed TR_WSP
    in place of kHighKickDeltaZ / kHighKickBallSpeed (the game's own x 0.75 / x 0.875 follows), and the whip goes live
    for tr_head (TR_WF / TR_WK / TR_WT). Everyone and everywhere else: the high ball as it was.
RUOLI NO: tr_hdown tail-answers setpieces' sp_on, tr_dist does the original compare, tr_kick does nothing and tr_hk
gives the original speed: today's exe behaviour.

Shape: asm (nasmcave), obj4 swreg.TRHD_AT..TRHD_END, no fixup of its own (obj2's base = setpieces' SPB dword, read
PC-relative; ebp = SPB everywhere, from setpieces' sp_base). A jump table at TRHD_AT + 5 x slot (JT): setpieces' header
stubs call slots 0 / 1 and sp_kick slot 2 (`%if TRHD_ON`, its only edits); this module hooks three obj1 sites, one
fixup dropped and one call added each: the two distance compares (DIST0 the static header, DIST1 the jump header:
`mov esi, A1` / `cmp [esi + ballDistance], 64`, 10 B, then `ja`) and HK (`mov ax, kHighKickBallSpeed`, 6 B).

The switch: until GP_RUOLI lands on the integration branch (Panchina, gameplay.gp_ruoli()), a branch-only build
constant TRHD_RUOLI=0 / 1 = the start value of the band's own byte TR_RU (unset = nothing linked: today's exe, byte for
byte). tr_live reads the switch in ONE place (the RU_REF define): the swap to GP_RUOLI is that line + on().

Zones (tr_zone; d = the man's distance from his OWN goal line: y - 129 for the top structure's team, 769 - y for the
bottom's - topTeamData defends the top goal in both halves, the clubs swap inside the structures):
  bit 0 own box (d 0..87, x 193..478), bit 1 attacking box (d 553..640, x 193..478), bit 2 the wide attacking zone
  (d >= 640 - TR_WZ, x <= 183 or >= 488: Marco's zones 16 / 20 and 1 / 5; no far bound, a corner's ball is on or
  just past the line), bit 3 the left half (x < 336).

Test switches (modver TEST_VARS): TR_HMASK, TR_DMASK, TR_RST, TR_WHB, TR_WHS, TR_WZ, TR_WDZ, TR_WSP.
Host tests: tools/hosttest/trhd_check.py (the rules against a Python model), trhd_structural.py (RUOLI NO = REF).
"""
import os
import re
import struct

import nasmcave

TAG = b'TRHD'
POS = 0x2E                               # PlayerInfoHeader.position (file byte >> 5: 0 GK 1 RB 2 LB 3 D 4 RW 5 LW 6 M 7 A)
JT = ('tr_hdown', 'tr_head', 'tr_kick', 'tr_hk', 'tr_dist', 'tr_live', 'tr_rec', 'tr_zone')
GOAL_TOP, GOAL_BOT, BOX_X0, BOX_X1, BOX_D, WIDE_X0, WIDE_X1, MID_X = 129, 769, 193, 478, 87, 183, 488, 336


def _iv(k, d):
    v = os.environ.get(k)
    return int(v, 0) if v else d


def knobs():
    return dict(HMASK=_iv('TR_HMASK', 0xFE), DMASK=_iv('TR_DMASK', 1 << 3), RST=_iv('TR_RST', 8),
                WHB=_iv('TR_WHB', 0x800), WHS=_iv('TR_WHS', 256), WZ=_iv('TR_WZ', 160),
                WDZ=_iv('TR_WDZ', 0x10000), WSP=_iv('TR_WSP', 4096))


def _gameplay():
    """The integration branch's gameplay module when it has GP_RUOLI (gameplay.gp_ruoli), else None."""
    try:
        import gameplay
    except ImportError:
        return None
    return gameplay if getattr(gameplay, 'gp_ruoli', None) else None


def gp_ruoli():
    """(obj, offset) of GP_RUOLI when THIS build links it (the GAMEPLAY band on, with its RUOLI row), else None."""
    g = _gameplay()
    if g is None or not g.on() or not g.roles():
        return None
    return g.gp_ruoli()


def ruoli():
    """TRHD_RUOLI: None (unset: nothing linked) / 0 (linked, RUOLI NO) / 1 (RUOLI SI). Branch-only: refused in a tree
    that has GP_RUOLI (MC 16/11: one switch, never its own; the gates start RUOLI SI with gameplay's GM_RUOLI_SI)."""
    v = os.environ.get('TRHD_RUOLI')
    assert v in (None, '', '0', '1'), 'TRHD_RUOLI=0 (RUOLI NO) / 1 (RUOLI SI)'
    assert not (v and _gameplay()), 'TRHD_RUOLI: this tree has GP_RUOLI - the switch is OPTIONS -> GAMEPLAY -> RUOLI (GM_RUOLI_SI=1 for a test build)'
    return int(v) if v else None


def on():
    """The traits are linked: with GP_RUOLI in the tree, whenever this build links GP_RUOLI (the GAMEPLAY band with its
    RUOLI row: every release build; GM_NOROLES = not linked; TRHD_NOLINK=1, a test build switch = not linked: the
    structural gate's REF); before it, only with TRHD_RUOLI set."""
    if _gameplay() is not None:
        if gp_ruoli() is None or os.environ.get('TRHD_NOLINK'):
            return False
    elif ruoli() is None:
        return False
    import setpieces
    assert setpieces.on(), 'trhead: needs the SETPIECE band (its header stubs call the TRHD jump table)'
    return True


ASM = r"""
; ---- the jump table (slot n at TRAT + 5 n)
tr_hdownj: jmp near tr_hdown           ; +0   setpieces: sp_jz / sp_fz / sp_head instead of sp_on
tr_headj:  jmp near tr_head            ; +5   setpieces: sp_head, after the HEADING placement
tr_kickj:  jmp near tr_kick            ; +10  setpieces: sp_kick's end (PlayerKickingBall)
tr_hkj:    jmp near tr_hk              ; +15  obj1 HK (the 'back' after-touch's speed)
tr_distj:  jmp near tr_dist            ; +20  obj1 DIST0 / DIST1
tr_livej:  jmp near tr_live            ; +25  the helpers, for a later trait (ebp = SPB: setpieces' sp_base)
tr_recj:   jmp near tr_rec             ; +30
tr_zonej:  jmp near tr_zone            ; +35

    db 'TRHD'
TR_RU: db RU_START                      ; the switch's stand-in in a tree without GP_RUOLI (RU_REF): 1 = RUOLI SI; 0 with GP_RUOLI
TR_ZK: db 0                             ; (2) 1 = the last kick may whip (tr_kick), until its after-touch or the next kick
TR_WF: db 0                             ; (2) 1 = a whipped cross is live
TR_WK: dw 0                             ; (2) its tick (currentGameTick)
TR_WT: dd 0                             ; (2) the armed kick's / the whip's team (TeamGeneralInfo)
TR_HM: dd HMASK                         ; (1) file positions that head down in the attacking box (bit = position)
TR_DM: dd DMASK                         ; (3) file positions with the own-box reach

%define RU_REF RU_SRC                 ; THE switch read: GP_RUOLI (dword ebp + GP_RUOLI_ - SPB_), else TR_RU

; ---- ebp = SPB. ZF = 1: the traits are off (RUOLI NO; SWOS++; a training game that is no practice - sp_on's own
;      reads, through setpieces' labels). Every register kept.
tr_live:
    cmp byte [RU_REF], 0
    je .x
    push ecx
    mov ecx, [ebp]
    cmp word [ecx + TRG_O], 0
    je .c
    mov ecx, [dword ebp + PR_D_ - SPB_]
    test ecx, ecx
    jz .p
    cmp byte [ebp + ecx], 0
    je .p
.c: test byte [dword ebp + SP_OK_ - SPB_], 1
.p: pop ecx
.x: ret

; ---- esi = a player's sprite, edi = his TeamGeneralInfo -> eax = his record (PlayerInfoHeader base: the game's
;      GetPlayerPointerFromShirtNumber: inGameTeamPtr + inGameTeamPlayerOffsets[ordinal - 1], a table of 61 x i).
;      After a substitution too: SubstitutePlayer swaps the two 61-byte records, so the pitch slot holds the new man's
;      own file position (and the man who left carries position -1 on the bench)
tr_rec:
    movzx eax, word [esi + 2]
    dec eax
    imul eax, eax, 61
    add eax, [edi + 0Ah]
    ret

; ---- esi = a sprite, edi = a TeamGeneralInfo, ebp = SPB -> eax = the zone bits of the sprite's place for that team:
;      1 own box, 2 attacking box, 4 wide attacking zone, 8 left half. Every other register kept.
tr_zone:
    push ecx
    push edx
    movsx ecx, word [esi + 20h]         ; x
    movsx edx, word [esi + 24h]         ; y
    mov eax, [ebp]
    add eax, TOP_O
    cmp edi, eax
    jne .b
    sub edx, GOAL_TOP                   ; the top structure's team: its own line is the top one
    jmp .d
.b: neg edx
    add edx, GOAL_BOT
.d: xor eax, eax                        ; edx = d, the distance from his own goal line
    cmp ecx, MID_X
    jge .r
    or al, 8
.r: cmp ecx, BOX_X0
    jl .w
    cmp ecx, BOX_X1
    jg .w
    test edx, edx
    js .o
    cmp edx, 640
    jg .o
    cmp edx, BOX_D
    jg .a
    or al, 1
    jmp .o
.a: cmp edx, 640 - BOX_D
    jl .o
    or al, 2
    jmp .o
.w: cmp ecx, WIDE_X0
    jle .z
    cmp ecx, WIDE_X1
    jl .o
.z: cmp edx, 640 - WZ
    jl .o
    or al, 4
.o: pop edx
    pop ecx
    ret

; ---- (1) "does this header go down?" for setpieces' sp_jz / sp_fz / sp_head, in sp_on's place and with its
;      contract: ebp = SPB, ZF = 1 the original header, every other register kept. Traits off: a tail jump to sp_on.
;      Traits on: down only for a TR_HM position in his attacking box (A1 the header's sprite, A6 his team); an
;      "original" answer under CALCI PIAZZATI NUOVI still ends a free kick's dip (sp_jz's FK_ST reset).
tr_hdown:
    call near SP_BASE_                  ; (ebp = SPB: the caller's ebp is on its stack already, sp_on sets it too)
    call tr_live
    jnz .t
    jmp near SP_ON_                     ; traits off: sp_on itself, on the caller's frame (every register but ebp as
.t:                                     ;  it came; sp_on reads no flag and sets ebp first)
    push eax
    push esi
    push edi
    mov eax, [ebp]
    mov esi, [eax + A1_O]
    mov edi, [eax + A6T_O]
    call tr_rec
    movzx eax, byte [eax + POS]
    cmp eax, 7
    ja .u
    bt [dword ebp + TR_HM - SPB_], eax
    jnc .u
    call tr_zone
    test al, 2
    jz .u
    pop edi
    pop esi
    pop eax
    test esp, esp                       ; (ZF = 0: down)
    ret
.u: cmp word [dword ebp + SP_W_ - SPB_], 0
    je .v
    mov byte [dword ebp + FK_ST_ - SPB_], 0
.v: pop edi
    pop esi
    pop eax
    cmp eax, eax                        ; (ZF = 1: the original header)
    ret

; ---- (1) the whipped cross's header (setpieces' sp_head, after its HEADING placement of a straight jump header going
;      down: ebx = the ball, ebp = SPB): a live whip of the header's own team, at most 100 ticks old -> TR_WHB more
;      down, TR_WHS more speed; the whip is spent. Every register and the flags kept.
tr_head:
    pushfd
    cmp byte [dword ebp + TR_WF - SPB_], 0
    je .x
    push eax
    push ecx
    mov byte [dword ebp + TR_WF - SPB_], 0
    mov ecx, [ebp]
    mov eax, [ecx + A6T_O]
    cmp eax, [dword ebp + TR_WT - SPB_]
    jne .n
    mov ax, [ecx + CGT_O]
    sub ax, [dword ebp + TR_WK - SPB_]
    cmp ax, 100
    ja .n
    sub dword [ebx + DZO], WHB
    add word [ebx + 2Ch], WHS
.n: pop ecx
    pop eax
.x: popfd
    ret

; ---- (2) the kick's record (setpieces' sp_kick, at its end: ebp = SPB, A1 = the kicker, A6 = his team, FK_ST already
;      set for this kick on sp_on's path; with setpieces off (sp_kick's `jz .x`) it keeps the last kick's value, so a
;      stale non-zero FK_ST can only drop a record, never invent one - Difficolta's review 19/11). Traits on: the old
;      record and any live whip end; TR_ZK = 1 for a file RW / LW with the ball
;      in the wide attacking zone, facing the centre line, no setpieces free kick. Every register and the flags kept.
tr_kick:
    pushfd
    call tr_live
    jz .x
    pushad
    mov word [dword ebp + TR_ZK - SPB_], 0  ; (TR_ZK and TR_WF)
    cmp byte [dword ebp + FK_ST_ - SPB_], 0
    jne .n
    mov ebx, [ebp]
    mov esi, [ebx + A1_O]
    mov edi, [ebx + A6T_O]
    call tr_rec
    mov al, [eax + POS]
    sub al, 4
    cmp al, 1
    ja .n
    lea esi, [ebx + BALL_O]
    call tr_zone
    test al, 4
    jz .n
    movzx edx, word [edi + 38h]         ; controlledPlDirection = the kicker's direction (0 up, clockwise)
    and edx, 7
    test al, 8
    jz .r
    dec edx                             ; from the left half: 1 / 2 / 3 (toward +x)
    jmp .c
.r: sub edx, 5                          ; from the right half: 5 / 6 / 7
.c: cmp edx, 2
    ja .n
    mov byte [dword ebp + TR_ZK - SPB_], 1
    mov [dword ebp + TR_WT - SPB_], edi
.n: popad
.x: popfd
    ret

; ---- (2) the 'back' after-touch's speed (replaces `mov ax, kHighKickBallSpeed` in ApplyBallAfterTouch; the ball's
;      deltaZ = kHighKickDeltaZ is stored just before, A6 = the kicking team): an armed kick of that team -> the ball's
;      deltaZ = WDZ, ax = WSP, the whip live from this tick. ax out, every other register and the flags kept.
tr_hk:
    push ebp
    pushfd
    call near SP_BASE_
    push ecx
    mov ecx, [ebp]
    mov ax, [ecx + KHS_O]
    call tr_live
    jz .x
    cmp byte [dword ebp + TR_ZK - SPB_], 0
    je .x
    mov byte [dword ebp + TR_ZK - SPB_], 0
    push edx
    mov edx, [ecx + A6T_O]
    cmp edx, [dword ebp + TR_WT - SPB_]
    jne .n
    mov dword [ecx + BALL_O + DZO], WDZ
    mov ax, WSP
    mov byte [dword ebp + TR_WF - SPB_], 1
    mov dx, [ecx + CGT_O]
    mov [dword ebp + TR_WK - SPB_], dx
.n: pop edx
.x: pop ecx
    popfd
    pop ebp
    ret

; ---- (3) the header contact distance (replaces `mov esi, A1` / `cmp [esi + ballDistance], 64`, then `ja`): a TR_DM
;      position in his own box: 64 + RST x HEADING (0..7). esi = A1 and the compare's flags out, every other register kept.
tr_dist:
    push ebp
    call near SP_BASE_
    mov esi, [ebp]
    mov esi, [esi + A1_O]
    call tr_live
    jz .o
    push eax
    push edi
    mov edi, [ebp]
    mov edi, [edi + A6T_O]
    call tr_rec
    push eax
    movzx eax, byte [eax + POS]
    cmp eax, 7
    ja .m
    bt [dword ebp + TR_DM - SPB_], eax
    jnc .m
    call tr_zone
    test al, 1
    jz .m
    pop eax
    movsx eax, byte [eax + HDO]
    test eax, eax
    jns .h
    xor eax, eax
.h: cmp eax, 7
    jbe .k
    mov eax, 7
.k: imul eax, eax, RST
    add eax, 64
    cmp [esi + 4Ah], eax
    pop edi
    pop eax
    pop ebp
    ret
.m: pop eax
    pop edi
    pop eax
.o: cmp dword [esi + 4Ah], 64
    pop ebp
    ret
"""


def find(p):
    """DIST0 / DIST1 (obj1, from setpieces' CEIL sites: the distance compare is 33 B above each ceiling), HK (obj1:
    ApplyBallAfterTouch's `mov ax, kHighKickBallSpeed`, after the kHighKickDeltaZ store) and the top team's structure (obj2: the lower of the two `cmp A6, offset <team>` operands, 0x91 apart)."""
    import difficulty as df
    import setpieces as sp
    s, c = sp.FOUND.get(id(p)) or sp.find(p)
    d = p.le.obj_bytes(1)
    t = lambda o: df._t(p, o)
    a6 = df.SYMS.get('A6_') or df.find(p)[1]['A6_']     # (a patch run: difficulty's hooks are in, its find would not pass)
    a1 = (2, c['A1_O'])
    out = {}
    for k, ck in (('DIST0', 'CEIL0'), ('DIST1', 'CEIL1')):
        o = s[ck] - 33
        assert d[o:o + 2] == b'\x8b\x35' and t(o + 2) == a1 and d[o + 6:o + 12] == b'\x83\x7e\x4a\x40\x0f\x87', \
            (k, d[o:o + 16].hex())
        out[k] = o
    o2 = p.le.obj_bytes(2)
    val = lambda o, f: struct.unpack_from(f, o2, t(o)[1])[0] if t(o) and t(o)[0] == 2 else None
    hk = [m.start() for m in re.finditer(rb'\xa1....\x8b\x35....\x89\x46\x36\x66\xa1....\x8b\x35....\x66\x89\x46\x2c', d, re.S)
          if val(m.start() + 1, '<I') == 0x20000 and val(m.start() + 16, '<H') == 2688]
    assert len(hk) == 1, ('ApplyBallAfterTouch: kHighKickDeltaZ / kHighKickBallSpeed', hk)
    out['HK'] = hk[0] + 14
    khs = t(out['HK'] + 2)[1]
    tg = {}
    for m in re.finditer(rb'\x81\x3d', d):
        o = m.start()
        if t(o + 2) == a6 and t(o + 6) and t(o + 6)[0] == 2:
            tg[t(o + 6)[1]] = tg.get(t(o + 6)[1], 0) + 1
    pair = [x for x in tg if x + 0x91 in tg and tg[x] >= 8 and tg[x + 0x91] >= 8]
    assert len(pair) == 1, ('topTeamData / bottomTeamData', {hex(k): v for k, v in tg.items()})
    return out, dict(TOP_O=pair[0], KHS_O=khs)


def _sym(p):
    import difficulty as df
    import setpieces as sp
    import swreg
    s, c = find(p)
    _, spc = sp.FOUND.get(id(p)) or sp.find(p)
    L = sp.LABELS
    k = knobs()
    assert not k['HMASK'] & ~0xFE and not k['DMASK'] & ~0xFE, 'TR_HMASK / TR_DMASK: outfield positions 1..7'
    assert 0 < k['WZ'] <= 320 and 0 <= k['RST'] <= 64 and 0 < k['WDZ'] <= 0x20000 and 0 < k['WSP'] <= 0x7FFF, k
    sym = {**{n: (0, spc[n]) for n in ('A1_O', 'A6T_O', 'CGT_O', 'DZO', 'HDO', 'BALL_O')}, 'TOP_O': (0, c['TOP_O']),
           'KHS_O': (0, c['KHS_O']), 'WDZ': (0, k['WDZ']), 'WSP': (0, k['WSP']),
           'TRG_O': (0, df.SYMS['TRG'][1]), 'POS': (0, POS), 'RU_START': (0, ruoli() or 0),
           **{n + '_': (4, L[n]) for n in ('SPB', 'SP_OK', 'PR_D', 'SP_W', 'FK_ST')},
           'SP_ON_': (4, L['sp_on']), **({'GP_RUOLI_': gp_ruoli()} if gp_ruoli() else {}), 'SP_BASE_': (4, L['sp_base']),
           'HMASK': (0, k['HMASK']), 'DMASK': (0, k['DMASK']), 'RST': (0, k['RST']), 'WHB': (0, k['WHB']),
           'WHS': (0, k['WHS']), 'WZ': (0, k['WZ']),
           **{n: (0, v) for n, v in dict(GOAL_TOP=GOAL_TOP, GOAL_BOT=GOAL_BOT, BOX_X0=BOX_X0, BOX_X1=BOX_X1, BOX_D=BOX_D,
                                         WIDE_X0=WIDE_X0, WIDE_X1=WIDE_X1, MID_X=MID_X).items()}}
    return s, sym


def asm_src():
    """ASM with RU_SRC: GP_RUOLI's byte (obj4, PC-relative to SPB like every other band read) when linked, else TR_RU."""
    gp = gp_ruoli()
    src = 'dword ebp + GP_RUOLI_ - SPB_' if gp else 'dword ebp + TR_RU - SPB_'
    return f'%define RU_SRC {src}\n' + ASM


def patch(p, lang):
    if not on():
        return None
    import difficulty as df
    import setpieces as sp
    import swreg
    assert sp.LABELS.get('sp_on'), 'trhead: after setpieces.patch'
    at = swreg.TRHD_AT
    s, sym = _sym(p)
    asm = asm_src()
    code, fix, rel = nasmcave.assemble_obj(asm, at, sym, 4)
    lab = nasmcave.labels(asm, at, sym)
    assert not fix and not rel, ('TRHD: no fixups (obj2 through setpieces\' SPB)', fix, rel)
    assert [lab[n + 'j'] for n in JT] == [at + 5 * i for i in range(len(JT))], 'TRHD: the jump table'
    left = swreg.TRHD_END - at - len(code)
    assert left >= 256, ('TRHD: floor 256 B', len(code))
    assert p.le.obj(4).npages * 0x1000 >= swreg.TRHD_END, 'TRHD: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.TRHD_END - at)), 'TRHD band not free'
    p.put(4, at, code)
    for k in ('DIST0', 'DIST1'):
        o = s[k]
        g = p.get(1, o, 12)                             # (the bytes as patched so far: nobody else hooks this compare)
        assert g[:2] == b'\x8b\x35' and g[6:12] == b'\x83\x7e\x4a\x40\x0f\x87', (k, bytes(g).hex())
        df._hook(p, o, 10, 10, lab['tr_dist'])
    o = s['HK']
    g = p.get(1, o, 6)
    assert g[:2] == b'\x66\xa1' and df._t(p, o + 2) == (2, sym['KHS_O'][1]), ('HK', bytes(g).hex())
    df._hook(p, o, 6, 6, lab['tr_hk'])
    LABELS.clear()
    LABELS.update(lab)
    gp = gp_ruoli()
    LABELS['RU'] = gp[1] if gp else lab['TR_RU']       # (obj4: THE switch byte the code reads - hosttests poke it)
    SYMS.clear()
    SYMS.update({k: (1, v) for k, v in s.items()})
    SYMS['TOP'] = (2, sym['TOP_O'][1])
    print(f'exe: position traits (1)-(3) ({'GP_RUOLI' if gp_ruoli() else 'TRHD_RUOLI=' + str(ruoli())}): code obj4+{at:#x} ({len(code)} B, {left} B left), '
          f'3 obj1 sites (DIST0 {s["DIST0"]:#x}, DIST1 {s["DIST1"]:#x}, HK {s["HK"]:#x}); setpieces\' header stubs ask '
          f'tr_hdown, sp_kick calls tr_kick')
    return at + len(code)


LABELS = {}
SYMS = {}                                # (hosttest: DIST0 / DIST1 obj1, the top team's structure obj2)
