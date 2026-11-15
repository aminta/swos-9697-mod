"""4.2 set-piece TAKERS (Davide 15/11: (A) + (B) + (C) approved; MC 15/11 storage option (1); band TAKERS, obj4
swreg.TAKERS_AT..TAKERS_END, 42-obj4freeze). Study: internal/handoff/setpiece-takers-study.md section 7 (1).

The game has no taker: a position table per gameState puts one lineup slot N next to the ball (corner L 5, R 2; free
kick LEFT1..3 9, CENTER 10, RIGHT1..3 6; penalty 10) and the nearest player becomes the controlled one, who kicks.
The hook (UpdatePlayers @@not_in_free_kick_state: `mov esi, A1` / `mov ax, [esi + playerOrdinal]` / `mov D0, ax`,
the kicking team's per-player position lookup) swaps the chosen taker's ordinal T with N, so T walks to the ball and
the whole original chain (controlled player, CPU fire, human kick) is unchanged, for human and CPU teams.

Who is T: per team side (the in-match team, topTeamInGame / bottomTeamInGame) and role (0 free kicks, 1 penalties,
2 corners) an ordered list of 3 file player indexes (PlayerInfo.playerIndex, the TeamFile slot: it follows the player
through substitutions and formation changes); T = the first of the list on the pitch (ordinal 2..11, not sent away),
else the original slot. 0xFF = an empty pick.

Gate: TK_W (TIRATORI AUTOMATICI 0 = the original game / SCELTI 1; the GAMEPLAY page's row, Panchina), a kick-off
without SWOS++ (setpieces SP_OK), not a training game unless a set-piece practice (setpieces PR_D). TK_W 0: the stub
does the original three instructions only.

Test switches (modver TEST_VARS): TAKERS_TEST=1 (TK_W starts at 1) and TAKERS_LIST='fk:a,b,c;pen:a,b,c;cor:a,b,c'
(file player indexes, the same list for both sides) - the harness also pokes TK_TAB through the 'TAKR' tag.
"""
import os
import re
import struct

import nasmcave

TAG = b'TAKR'
ROLES = ('fk', 'pen', 'cor')
# nearest kicking-team ordinal per gameState 4..14 (study sections 2, 3, 5); 13 = ST_FOUL (no table): 0 = no swap
NEAR = (5, 2, 9, 9, 9, 10, 6, 6, 6, 0, 10)
ROLE = (2, 2, 0, 0, 0, 0, 0, 0, 0, 0xFF, 1)
TK_SV_SIZE = 27         # the save item 'TK' (MC 15/11: index + 16-bit name hash per pick)
TK_NS = 8               # session table entries (friendlies / cups / careers in one session; the career club's goes to
                        # the save item 'TK')


def on():
    """Linked with the set-piece band (the OPTIONS rows: DIFF_TEST builds and the release)."""
    import setpieces
    return setpieces.on()


def test_start():
    v = os.environ.get('TAKERS_TEST')
    return int(v) if v else 0


def test_list():
    """TAKERS_LIST -> 2 sides x 3 roles x 3 picks (bytes, 0xFF = none)."""
    t = [[[0xFF] * 3 for _ in ROLES] for _ in range(2)]
    for part in filter(None, (os.environ.get('TAKERS_LIST') or '').split(';')):
        k, v = part.split(':')
        picks = [int(x) for x in v.split(',') if x != '']
        assert k in ROLES and len(picks) <= 3 and all(0 <= x < 16 for x in picks), ('TAKERS_LIST', part)
        for side in t:
            side[ROLES.index(k)][:len(picks)] = picks
    return t


def find(p):
    """The hook site (obj1) and the obj2 offsets: `mov esi, A1` / `mov ax, [esi + 2]` / `mov D0, ax` / `sub D0, 1`,
    and the `mov eax, lastTeamPlayedBeforeBreak` / `cmp A6, eax` / `jz` to it just before."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    t = lambda o: df._t(p, o)
    sym = df.SYMS                       # (difficulty's hooks are in: its find() needs the original bytes)
    a1 = (2, sym['D0_'][1] + 4 * 9)
    d0 = sym['D0_']
    a6 = sym['A6_']
    m = [x.start() for x in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x02\x66\xa3....\x66\x83\x2d....\x01', d, re.S)]
    m = [o for o in m if t(o + 2) == a1 and t(o + 12) == d0 and t(o + 19) == d0]

    def lts(site):                      # (`mov eax, lastTeamPlayedBeforeBreak` / `cmp A6, eax` / `jz site`)
        w = d[site - 0x200:site]
        return [site - 0x200 + x.start() for x in re.finditer(rb'\xa1....\x39\x05....\x0f\x84', w, re.S)
                if t(site - 0x200 + x.start() + 7) == a6
                and site - 0x200 + x.start() + 17 + struct.unpack_from('<i', w, x.start() + 13)[0] == site]
    m = [(o, lts(o)) for o in m]
    m = [(o, lt) for o, lt in m if len(lt) == 1]
    assert len(m) == 1, ('takers: @@not_in_free_kick_state', [hex(x) for x, _ in m])
    site, lt = m[0]
    ltp = t(lt[0] + 1)
    assert ltp and ltp[0] == 2, ltp
    # @@check_for_penalty_shootout: `cmp A6, offset bottomTeamData` / jnz (topTeamData = bottom - sizeof 91h)
    bt = [site - 0x200 + x.start() for x in re.finditer(rb'\x81\x3d........\x75', d[site - 0x200:lt[0]], re.S)]
    bt = [t(o + 6) for o in bt if t(o + 2) == a6]
    assert len(bt) == 1 and bt[0][0] == 2, ('takers: bottomTeamData', bt)
    # InitializeInGameTeamsAndStartGame: mov eax, A1 / mov gameTeam1, eax / mov eax, A2 / mov gameTeam2, eax /
    # mov eax, A1 / mov A0, eax (gameTeam1 = topTeamInGame's file)
    a2, a0 = (2, d0[1] + 4 * 10), (2, d0[1] + 4 * 8)
    # (raw operands, obj_bytes = the original exe: another module may hook this place before us)
    dw = lambda v: re.escape(struct.pack('<I', v))
    gt = [x for x in re.finditer(rb'\xa1' + dw(a1[1]) + rb'\xa3(....)\xa1' + dw(a2[1]) + rb'\xa3(....)\xa1' + dw(a1[1])
                                 + rb'\xa3' + dw(a0[1]), d, re.S)]
    assert len(gt) == 1, ('takers: gameTeam1 / 2', gt)
    g1, g2 = [(2, struct.unpack('<I', gt[0].group(k))[0]) for k in (1, 2)]
    assert g1[0] == 2 and g2 == (2, g1[1] + 4), (g1, g2)
    # PlayTrainingGame: mov g_trainingGame, 1 / mov A0, offset careerTeam / mov D0, 1 / mov D1, 2 / call
    ct = [x for x in re.finditer(rb'\x66\xc7\x05' + dw(sym['TRG'][1]) + rb'\x01\x00\xc7\x05' + dw(a0[1])
                                 + rb'(....)\x66\xc7\x05' + dw(d0[1]) + rb'\x01\x00\x66\xc7\x05', d, re.S)]
    assert len(ct) == 1, ('takers: careerTeam', ct)
    import blond
    tig = blond.topteam(p)
    assert tig[0] == 2, tig
    return site, dict(A1_O=a1[1], D0_O=d0[1], A6_O=a6[1], LTP_O=ltp[1], TOPT_O=bt[0][1] - 0x91, GT1_O=g1[1], TOPIG_O=tig[1],
                      CTEAM_O=struct.unpack('<I', ct[0].group(1))[0])


def find_ctl(p):
    """UpdateControlledPlayer @@check_closest_active_player: `cmp A3, 0` / `jz` / `mov esi, A6` /
    `mov ax, [esi + ballOutOfPlay]` / `or ax, ax` / `jz` / `mov esi, A6` / `mov eax, [esi + controlledPlayer]` /
    `cmp A3, eax` -> the hook site (the `mov esi, A6`, 10 B), A3's offset, ballOutOfPlay."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    d0 = df.SYMS['D0_'][1]
    a3, a6 = d0 + 4 * 11, df.SYMS['A6_'][1]
    dw = lambda v: re.escape(struct.pack('<I', v))
    m = [x for x in re.finditer(rb'\x83\x3d' + dw(a3) + rb'\x00\x0f\x84....\x8b\x35' + dw(a6) + rb'\x66\x8b\x46(.)'
                                rb'\x66\x0b\xc0\x0f\x84....\x8b\x35' + dw(a6) + rb'\x8b\x46\x20\x39\x05' + dw(a3), d, re.S)]
    assert len(m) == 1, ('takers: @@check_closest_active_player', m)
    return m[0].start() + 13, dict(A3_O=a3, BOOP=m[0].group(1)[0])


ASM = r"""
    jmp tk_kick                         ; (TAKERS_AT + 0: setpieces' sp_set calls it at every kick-off)
align 4
TKB: dd 0                               ; (anchor; obj2's base = setpieces' [SPB]: no fixup of its own, MC padding 15/11)
TAGS: db 'TAKR'
TK_TABP: dd TK_TAB - TKB                ; (the harness: TAKR tag + 4 = TK_TAB's offset from TKB)
TK_W: db TK_START                       ; TIRATORI: 0 AUTOMATICI (the original game) / 1 SCELTI
TK_LAST: db 0                           ; (harness: the last swap, T | N << 4; 0 none)
TK_NSW: dw 0                            ; (harness: swaps done, wraps)
TK_CT: db 0                             ; the resolved taker T of this break (0 none): tk_ctl keeps him controlled
TK_CG: db 0                             ; (its gameState - 4)
TK_NCT: dw 0                            ; (harness: tk_ctl overrides, wraps)
align 4
TK_CTT: dd 0                            ; (its team: TeamGeneralInfo)
align 4
TK_SIDE: dd 0, 0                        ; the in-match team (inGameTeamPtr) of side 0 / 1; 0 = any (TAKERS_LIST)
TK_TAB: db @TKL@                          ; side x role x pick: file player index, 0FFh = none
TK_NEAR: db @NEARL@
TK_ROLE: db @ROLEL@
align 4
TK_SES: times TK_NS * 11 db 0           ; the session table: TK_NS x {u16 globalTeamNumber + 1 (0 free), 9 picks + 1}
TK_SNX: db 0                            ; (the next slot to reuse when full)
TK_RS: db 0, 0, 0, 3, 3, 3, 6, 6, 6     ; (a slot's role start)
TK_BS: db 0
TK_BI: db 0
TK_SO: db 0
align 4
TK_SPR: dd 0
TK_SV: times 27 db 0                    ; the career save item 'TK': 9 x {u8 file index + 1 (0 none), u16 name hash}
align 4

; ---- eax = key (globalTeamNumber + 1) -> edi = its session entry, or 0 (tk_ent); tk_alloc: found or a new one
;      (TK_SNX's slot when full; picks cleared). ebp = TKB; ecx kept
tk_ent:
    push ecx
    lea edi, [ebp + TK_SES - TKB]
    mov ecx, TK_NS
.l: cmp [edi], ax
    je .x
    add edi, 11
    dec ecx
    jnz .l
    xor edi, edi
.x: pop ecx
    ret
; ---- the kick-off (setpieces sp_set, past df_kick's SWOS++ gate): each side's in-match team and its 9 picks -
;      a human team (playerNumber / playerCoachNumber) = its session entry (none: no picks = the original slots), a
;      CPU team = AUTOMATICO: its 3 best SHOOTING outfielders on the pitch for free kicks and penalties, PASSING for
;      corners. TK_W 0 or a TAKERS_LIST build: nothing (the static list, both sides).
tk_kick:                                ; (sp_set's tail: every register and flag as its own `ret` left them)
    pushfd
    push ebp
    call .n
.n: pop ebp
    sub ebp, .n - TKB
    mov byte [ebp + TK_CT - TKB], 0     ; (no taker carried over from an earlier match)
%if TK_STATIC = 0
    and dword [ebp + TK_SIDE - TKB], 0  ; (the sides are filled at the match's first set piece: tk_fill)
    and dword [ebp + TK_SIDE + 4 - TKB], 0
%endif
    pop ebp
    popfd
    ret

; ---- esi -> the kicking team's TeamGeneralInfo, ecx = obj2's base, ebp = TKB -> eax = its side (0 / 1; its 9 picks
;      in TK_TAB filled now), -1 = none free (TK_W 1 only). A human team (playerNumber / playerCoachNumber) = its
;      session entry (none: no picks = the original slots), a CPU team = AUTOMATICO: its 3 best SHOOTING outfielders
;      on the pitch for free kicks and penalties, PASSING for corners. Every other register kept.
tk_fill:
    push ebx
    push ecx
    push edx
    push esi
    push edi
    mov edx, esi
    mov edi, [edx + IGT]
    xor esi, esi                        ; esi = the free side
    cmp dword [ebp + TK_SIDE - TKB], 0
    je .fr
    inc esi
    cmp dword [ebp + TK_SIDE + 4 - TKB], 0
    je .fr
    mov esi, -1
    jmp .ret
.fr:
    mov [ebp + TK_SIDE - TKB + esi * 4], edi
    lea eax, [esi + esi * 8]
    lea ebx, [ebp + TK_TAB - TKB + eax] ; ebx -> this side's 9 picks
    mov dword [ebx], -1
    mov dword [ebx + 4], -1
    mov byte [ebx + 8], -1
    mov ax, [edx + 4]
    or ax, [edx + 6]
    jz .cpu
    lea eax, [ecx + TOPIG_O]            ; the team's file: gameTeam1 = topTeamInGame's, gameTeam2 the other
    cmp edi, eax
    mov eax, [ecx + GT1_O]
    je .gf
    mov eax, [ecx + GT1_O + 4]
.gf:test eax, eax
    jz .nx
    movzx eax, word [eax + 2]
    inc eax
    call tk_ent
    test edi, edi
    jz .nx
    xor ecx, ecx
.cp: mov al, [edi + 2 + ecx]
    dec al                              ; (stored + 1: 0 = none -> 0FFh)
    mov [ebx + ecx], al
    inc ecx
    cmp ecx, 9
    jb .cp
    jmp .nx
.cpu:                                   ; edi -> the in-match team, ebx -> the side's 9 picks
    mov eax, [edx + SPRT]
    mov [ebp + TK_SPR - TKB], eax
    xor ecx, ecx                        ; ecx = slot (role * 3 + k)
.slot:
    mov byte [ebp + TK_BS - TKB], -1    ; the best skill so far (signed: -1 = none)
    mov byte [ebp + TK_BI - TKB], 0FFh  ; its file index
    mov byte [ebp + TK_SO - TKB], SHOOT
    cmp ecx, 6
    jb .s1
    mov byte [ebp + TK_SO - TKB], PASS
.s1:
    push esi
    mov esi, 1                          ; ordinal - 1: the outfielders 2..11
.i: mov eax, [ebp + TK_SPR - TKB]
    mov eax, [eax + esi * 4]
    cmp word [eax + SENT], 0
    jne .ni
    imul eax, esi, 61
    lea eax, [edi + 42 + eax]           ; eax -> PlayerInfo
    movzx edx, byte [ebp + TK_RS - TKB + ecx]
.d: cmp edx, ecx                        ; (not already picked for this role)
    jae .nd
    push ecx
    mov cl, [eax + 1]
    cmp cl, [ebx + edx]
    pop ecx
    je .ni
    inc edx
    jmp .d
.nd: movzx edx, byte [ebp + TK_SO - TKB]
    mov dl, [eax + edx]                 ; the skill
    cmp dl, [ebp + TK_BS - TKB]
    jle .ni                             ; (ties: the lower ordinal stays)
    mov [ebp + TK_BS - TKB], dl
    mov dl, [eax + 1]
    mov [ebp + TK_BI - TKB], dl
.ni: inc esi
    cmp esi, 11
    jb .i
    pop esi
    mov al, [ebp + TK_BI - TKB]
    mov [ebx + ecx], al
    inc ecx
    cmp ecx, 9
    jb .slot
.nx:
.ret:
    mov eax, esi
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

; ---- ebp = TKB, ecx = obj2's base -> ZF set = takers off: TK_W 0 (AUTOMATICI, the original game), a training game
;      that is no set-piece practice, SWOS++ (SP_OK clear). Every register kept
tk_gate:
    cmp byte [ebp + TK_W - TKB], 0
    je .x
    cmp word [ecx + TRG_O], 0           ; (a training game: only a set-piece practice)
    je .c
    push esi
    mov esi, [dword ebp + PR_D - TKB]
    test esi, esi
    jz .y
    cmp byte [dword ebp + SPB - TKB + esi], 0
.y: pop esi
    je .x
.c: test byte [dword ebp + SP_OK - TKB], 1    ; (SWOS++: the original game)
.x: ret

; ---- replaces `mov esi, A1` / `mov ax, [esi + playerOrdinal]` / `mov D0, ax` (eax, esi free after: the next
;      instruction is `sub D0, 1`); every other register kept
tk_ord:
    push ebp
    push ecx
    call .n
.n: pop ebp
    sub ebp, .n - TKB
    mov ecx, [dword ebp + SPB - TKB]
    mov esi, [ecx + A1_O]
    mov ax, [esi + 2]
    mov [ecx + D0_O], ax
    call tk_gate
    jz .x
    mov esi, [ecx + A6_O]
    cmp esi, [ecx + LTP_O]              ; (the kicking team only)
    jne .x
    push ebx
    push edx
    push edi
    mov byte [ebp + TK_CT - TKB], 0
    movzx ebx, word [ecx + GS_O]
    sub ebx, 4
    cmp ebx, 10
    ja .p                               ; (gameState 4..14 only)
    mov [ebp + TK_CG - TKB], bl
    movzx edx, byte [ebp + TK_NEAR - TKB + ebx]
    test edx, edx
    jz .p                               ; (ST_FOUL)
    movzx ebx, byte [ebp + TK_ROLE - TKB + ebx]
    ; side: TK_SIDE[0] / [1] == the team's inGameTeamPtr, else filled now (tk_fill); TAKERS_LIST: side 0
    xor eax, eax
%if TK_STATIC = 0
    mov edi, [esi + IGT]
    cmp edi, [ebp + TK_SIDE - TKB]
    je .sk
    inc eax
    cmp edi, [ebp + TK_SIDE + 4 - TKB]
    je .sk
    call tk_fill
    test eax, eax
    js .p
.sk:
%endif
    imul eax, eax, 9
    lea eax, [eax + ebx * 2]
    add eax, ebx                        ; side * 9 + role * 3
.s0:
    lea ebx, [ebp + TK_TAB - TKB + eax] ; ebx -> the 3 picks
    push edx                            ; (N)
    mov dl, 3
.pk:
    mov al, [ebx]
    cmp al, 0FFh
    je .nx
    ; find the pick among ordinals 2..11: PlayerInfo i at edi + 42 + 61 * i, playerIndex at +1
    push ecx
    push esi
    push edx
    mov dl, al
    mov ecx, 1
.f: imul eax, ecx, 61
    cmp dl, [edi + 42 + 1 + eax]
    jne .fn
    mov eax, [esi + SPRT]               ; spritesTable -> sprite i: sent away?
    mov eax, [eax + ecx * 4]
    cmp word [eax + SENT], 0
    jne .fn
    lea eax, [ecx + 1]                  ; T = ordinal
    pop edx
    pop esi
    pop ecx
    jmp .got
.fn: inc ecx
    cmp ecx, 11
    jb .f
    pop edx
    pop esi
    pop ecx
.nx: inc ebx
    dec dl
    jnz .pk
    pop edx
    jmp .p
.got:
    pop edx                             ; edx = N, eax = T
    cmp eax, edx
    je .p
    mov [ebp + TK_CT - TKB], al         ; (tk_ctl)
    mov [ebp + TK_CTT - TKB], esi
    mov bx, [ecx + D0_O]
    cmp bx, ax
    jne .t2
    mov [ecx + D0_O], dx                ; T takes N's place
    jmp .cnt
.t2: cmp bx, dx
    jne .p
    mov [ecx + D0_O], ax                ; N takes T's
.cnt:
    shl dl, 4
    or al, dl
    mov [ebp + TK_LAST - TKB], al
    inc word [ebp + TK_NSW - TKB]
.p: pop edi
    pop edx
    pop ebx
.x: pop ecx
    pop ebp
    ret
"""


ASM_UI = r"""
    jmp near tk_load                    ; (TKUI_AT + 0: setpieces' sp_load_j calls it after a career load - no engine
                                        ;  after_load entry of its own: MC padding 15/11)
; ---- UpdateControlledPlayer @@check_closest_active_player: replaces `mov esi, A6` / `mov ax, [esi + ballOutOfPlay]`
;      (then `or ax, ax` / `jz @@out`). In a break of the kicking team whose taker T was swapped in (tk_ord: TK_CT),
;      A3 (the closest active player) = T's sprite: T stays the controlled player while he walks to the ball, so
;      neither the CPU nor the nearest man takes the kick before he is there (penalties: the CPU shot at once).
;      eax / esi as the original; every other register kept
tk_ctl:
    push ebp
    push ecx
    call .n
.n: pop ebp
    sub ebp, .n - TKB
    mov ecx, [dword ebp + SPB - TKB]
    mov esi, [ecx + A6_O]
    mov ax, [esi + BOOP]
    test ax, ax
    jz .x
    push eax
    movzx eax, byte [ebp + TK_CT - TKB]
    test eax, eax
    jz .y
    call tk_gate                        ; (off: never - TK_CT may be an earlier match's, TK_W 1 then)
    mov esi, [ecx + A6_O]
    jz .y
    cmp esi, [ebp + TK_CTT - TKB]
    jne .y
    cmp esi, [ecx + LTP_O]
    jne .y
    push edx
    movzx edx, word [ecx + GS_O]
    sub edx, 4
    cmp dl, [ebp + TK_CG - TKB]
    jne .z
    mov edx, [esi + SPRT]
    mov eax, [edx + eax * 4 - 4]        ; T's sprite
    cmp word [eax + SENT], 0
    jne .z
    mov [ecx + A3_O], eax
    inc word [ebp + TK_NCT - TKB]       ; (harness)
.z: pop edx
.y: pop eax
.x: pop ecx
    pop ebp
    ret

; ---- the TKUI band (Shaved 15/11, 42-tkui): the session / save code and the UI; ebp = TKB as in the TAKERS band
;      (TKB, TK_SES, TK_SV, tk_ent: symbols of that band, same object: constant displacements, no fixup)
tk_alloc:
    call tk_ent
    test edi, edi
    jnz .x
    push ecx
    lea edi, [ebp + TK_SES - TKB]       ; (a free slot first)
    mov ecx, TK_NS
.f: cmp word [edi], 0
    je .n
    add edi, 11
    dec ecx
    jnz .f
    movzx ecx, byte [ebp + TK_SNX - TKB]
    imul ecx, ecx, 11
    lea edi, [ebp + TK_SES - TKB + ecx]
    movzx ecx, byte [ebp + TK_SNX - TKB]
    inc ecx
    cmp ecx, TK_NS
    jb .s
    xor ecx, ecx
.s: mov [ebp + TK_SNX - TKB], cl
.n: mov [edi], ax
    xor ecx, ecx
.z: mov byte [edi + 2 + ecx], 0
    inc ecx
    cmp ecx, 9
    jb .z
    pop ecx
.x: ret

; ---- esi -> a TeamFile, eax = file index -> ax = the 16-bit hash of that player's name (22 bytes or to its 0)
tk_hash:
    push ecx
    push edx
    push esi
    imul eax, eax, 38
    lea esi, [esi + 76 + 3 + eax]
    xor eax, eax
    mov ecx, 22
.l: movzx edx, byte [esi]
    test edx, edx
    jz .x
    imul eax, eax, 31
    add eax, edx
    inc esi
    dec ecx
    jnz .l
.x: and eax, 0FFFFh
    pop esi
    pop edx
    pop ecx
    ret

; ---- engine before_save: the career club's session entry -> TK_SV (with each pick's name hash)
tk_save:
    pushad
    call .n
.n: pop ebp
    sub ebp, .n - TKB
    lea ebx, [ebp + TK_SV - TKB]
    xor ecx, ecx
.z: mov byte [ebx + ecx], 0
    inc ecx
    cmp ecx, 27
    jb .z
    mov esi, [dword ebp + SPB - TKB]
    add esi, CTEAM_O                    ; esi -> careerTeam
    movzx eax, word [esi + 2]
    inc eax
    call tk_ent
    test edi, edi
    jz .out
    xor ecx, ecx
.l: movzx eax, byte [edi + 2 + ecx]
    test eax, eax
    jz .nx
    cmp eax, 16
    ja .nx
    lea edx, [ecx + ecx * 2]
    mov [ebx + edx], al
    dec eax
    call tk_hash
    mov [ebx + edx + 1], ax
.nx: inc ecx
    cmp ecx, 9
    jb .l
.out:
    popad
    ret

; ---- engine after_load: TK_SV -> the career club's session entry; a pick whose name hash no longer matches the
;      player at that file slot (sold, moved) is dropped (= the original taker). A save without 'TK': all zero.
tk_load:
    pushad
    call .n
.n: pop ebp
    sub ebp, .n - TKB
    mov esi, [dword ebp + SPB - TKB]
    add esi, CTEAM_O
    movzx eax, word [esi + 2]
    inc eax
    lea ebx, [ebp + TK_SV - TKB]
    xor ecx, ecx                        ; (any pick saved?)
.a: cmp byte [ebx + ecx], 0
    jne .y
    add ecx, 3
    cmp ecx, 27
    jb .a
    call tk_ent                         ; (none: the club's session entry, if any, cleared)
    test edi, edi
    jz .out
    mov word [edi], 0
    jmp .out
.y: call tk_alloc
    xor ecx, ecx
.l: lea edx, [ecx + ecx * 2]
    movzx eax, byte [ebx + edx]
    mov byte [edi + 2 + ecx], 0
    test eax, eax
    jz .nx
    cmp eax, 16
    ja .nx
    push eax
    dec eax
    call tk_hash
    cmp ax, [ebx + edx + 1]
    pop eax
    jne .nx
    mov [edi + 2 + ecx], al
.nx: inc ecx
    cmp ecx, 9
    jb .l
.out:
    popad
    ret

"""


def _src(tab):
    flat = [b for side in tab for role in side for b in role]
    return ASM.replace('@TKL@', ', '.join(str(x) for x in flat)).replace('@NEARL@', ', '.join(map(str, NEAR))) \
        .replace('@ROLEL@', ', '.join(map(str, ROLE)))


def patch(p, lang):
    if not on():
        return None
    import difficulty as df
    import modver
    import setpieces as sp
    import swreg
    assert not (os.environ.get('TAKERS_TEST') or os.environ.get('TAKERS_LIST')) or modver.is_test(), \
        'TAKERS_TEST / TAKERS_LIST: test builds only'
    assert sp.LABELS.get('SPB'), 'takers: after setpieces.patch (SPB / PR_D / SP_OK)'
    site, c = find(p)
    csite, cc = find_ctl(p)
    c.update(cc)
    _, gs = sp.FOUND[id(p)] if id(p) in sp.FOUND else sp.find(p)
    assert TK_SV_SIZE == 27
    sym = {**{n: (0, v) for n, v in c.items()}, 'O2BASE': (2, 0), 'TK_START': (0, test_start()),
           'TRG_O': (0, df.SYMS['TRG'][1]), 'GS_O': (0, gs['GS_O']),
           'IGT': (0, 0x0A), 'SPRT': (0, 0x14), 'SENT': (0, 0x6C), 'SHOOT': (0, 0x1C), 'PASS': (0, 0x1B),
           'TK_NS': (0, TK_NS), 'TK_STATIC': (0, int(bool(os.environ.get('TAKERS_LIST')))),
           **{n: (4, sp.LABELS[n]) for n in ('SPB', 'PR_D', 'SP_OK')}}
    at = swreg.TAKERS_AT
    src = _src(test_list())
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    assert not fix and not rel, ('takers: no fixups (obj2 base = [SPB])', fix, rel)
    left = swreg.TAKERS_END - at - len(code)
    assert left >= 256, ('takers: band room (floor 256)', left)
    assert p.le.obj(4).npages * 0x1000 >= swreg.TAKERS_END, 'takers: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.TAKERS_END - at)), 'takers: band not free'
    p.put(4, at, code)
    lab = nasmcave.labels(src, at, sym)
    df._hook(p, site, 16, 16, lab['tk_ord'])
    usym = {**sym, **{n: (4, v) for n, v in lab.items() if '.' not in n and n not in sym}}
    uat = swreg.TKUI_AT
    ucode, ufix, urel = nasmcave.assemble_obj(ASM_UI, uat, usym, 4)
    assert not ufix and not urel, ('TKUI: no fixups', ufix, urel)
    uleft = swreg.TKUI_END - uat - len(ucode)
    assert uleft >= 256, ('TKUI: band room (floor 256)', uleft)
    assert p.le.obj(4).npages * 0x1000 >= swreg.TKUI_END, 'TKUI: obj4 pages (patch.py)'
    assert not any(p.get(4, uat, swreg.TKUI_END - uat)), 'TKUI: band not free'
    p.put(4, uat, ucode)
    lab = {**lab, **{n: v for n, v in nasmcave.labels(ASM_UI, uat, usym).items() if n not in lab}}
    df._hook(p, csite, 10, 10, lab['tk_ctl'])
    import engine
    engine.ITEM_AT['TK'] = (4, lab['TK_SV'])
    engine.CALL_AT['tk_save'] = (4, lab['tk_save'])
    LABELS.clear()
    LABELS.update({k: v for k, v in lab.items() if '.' not in k})
    SITES.clear()
    SITES['ORD'] = site
    SITES['CTL'] = csite
    print(f'exe: takers (TK_W {test_start()}): code obj4+{at:#x} ({len(code)} B, {left} B left), TKUI obj4+{uat:#x} '
          f'({len(ucode)} B, {uleft} B left), site obj1+{site:#x}')
    return at + len(code)


LABELS = {}
SITES = {}
