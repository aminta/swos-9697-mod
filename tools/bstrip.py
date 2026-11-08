"""The bench info strip (4.0.6, Francesco): in the in-match bench menus each player's three best skills and his value,
as the squad screens show them (FormTopSkillsString's letters, cseg_247C8's price in the exe's own format).

- The bench (g_subsState 0, the cursor on a bench place, the game's arrow drawn): the menu's header row for that
  player in the header's place (DrawSubstitutesMenuEntry, the colours DrawSubstitutesMenu would pick for this bench)
  and a box under it, left of where the substitutes picture goes: his skills over his value.
- The substitutes menu (state 1, the player going in on top, the 11 to choose the one going out): the same box for
  the player going in (left of the picture) and one for the highlighted row (right of it): the two compared.
- Both boxes sit beside the picture box (y 23..55, the rows' own frame / background / shadow colours), clear of the
  bottom score panel; a box per player, so the long bench (places 12..26, benchx) needs nothing more.
- A goalkeeper has no skill letters (FormTopSkillsString writes none): his box shows the value only. The price's
  '*' padding (the exes' fixed-width format strings) is cut.
Drawn after DrawBenchAndSubsMenu (GameLoop's call, chained on its current target), only while the bench menu is
open (g_inSubstitutesMenu), not in oppl's opponent list (state 5) or the other states. The record is the game's own
(GetPlayer on the in-match team's file - gameTeam1 for topTeamInGame, gameTeam2 for the bottom one - and the
PlayerInfo's playerIndex, as UpdatePlayerInjuries reads it; xtra's gp_wide serves a CPU club's places 16..).
Off under SWOS++ (it draws these menus with its own geometry; menunum's SWOS++ byte, as oppl.py / formwide.py).
The harness reads the last boxes drawn by the tag 'BSTR' (bench_strip).
Code in obj3 at the chain's end (CONVENTIONS 23).
"""
import re
import struct

import nasmcave

BW = 44                         # a box's width (frame); the rows' frame is 126 + formwide.WIDE
BOX_Y, BOX_H = 23, 33           # the picture box's frame: y 23, 33 high (DrawSubstitutesMenu)
LINE1, LINE2 = 28, 40           # the two text lines' y
SLOT = 64                       # a mirror slot: +0 record ptr, +4 PlayerInfo ptr, +8 skills (8), +16 price (24),
                                # +40 the PlayerInfo's short name (16), +56 the place / row, +58 drawn frames

ASM = r"""
bs_draw:                                ; GameLoop's `call DrawBenchAndSubsMenu` (its current target)
    call PREV
    cmp byte [SWOSPP], 0FFh
    jne .r                              ; SWOS++ running: its own menus
    cmp word [INSUBS], 0
    je .r
    pushad
    mov esi, D0
    mov edi, bs_regs                    ; (the game's memory registers D0 .. A6)
    mov ecx, 15
    rep movsd
    mov word [bs_state], -1
    mov ax, [SUBST]
    cmp ax, 1
    je .s1
    or ax, ax
    jne .x
    cmp word [GOTIMER], 0               ; the game's own arrow condition (DrawBenchAndSubsMenu)
    jne .x
    cmp word [INPROG], 0
    jne .x
    movzx eax, word [IDX]
    or eax, eax
    jz .x                               ; the coach
    add eax, 10                         ; FirePressedInSubsMenu: place = cursor + 10
    cmp eax, 26
    jae .x
    mov [bs_ord], ax
    movzx ebx, word [TABLE + eax * 2]
    add ebx, [BTG]
    cmp byte [ebx + 42 + 4], 0          ; position -1: an empty / used place
    jl .x
    mov [bs_pi], ebx
    call bs_colours
    mov word [D2], 10                   ; the header row (DrawSubstitutesMenu: y 10, the background colour)
    mov ax, [BGC]
    mov [D4], ax
    mov ax, [bs_ord]
    mov [D7], ax
    mov dword [A1], SCH
    mov eax, [BTG]
    mov [A2], eax
    mov dword [A4], TABLE
    call DSME
    mov esi, [bs_pi]
    xor ebx, ebx
    movzx eax, word [bs_ord]
    call bs_box
    mov word [bs_state], 0
    jmp .x
.s1:
    movzx eax, word [PTEG]              ; the player going in (the header)
    cmp eax, 26
    jae .x
    movzx esi, word [TABLE + eax * 2]
    add esi, [BTG]
    xor ebx, ebx
    call bs_box
    mov word [bs_state], 1
    movsx eax, word [PTSP]              ; the highlighted row (GetBenchPlayerPointer's place)
    or eax, eax
    js .x
    cmp eax, 11
    jae .x
    movzx edx, word [PL1T]
    mov ecx, [BT]
    cmp word [ecx + 12h], 1             ; (TeamGeneralInfo.teamNumber)
    je .t
    movzx edx, word [PL2T]
.t: mov edx, [POSTAB + edx * 4]
    movzx edx, byte [edx + eax]
    dec edx
    movzx esi, word [TABLE + edx * 2]
    add esi, [BTG]
    mov ebx, 1
    call bs_box
.x: mov esi, bs_regs
    mov edi, D0
    mov ecx, 15
    rep movsd
    popad
.r: ret

bs_colours:                             ; DrawSubstitutesMenu's colours for this bench (the kit: background,
    mov esi, [BTG]                      ; highlight, row frame; white / yellow skipped for the first two)
    mov ax, [esi + K_SHIRT]
    mov [bs_cols], ax
    mov ax, [esi + K_STRIPES]
    mov [bs_cols + 2], ax
    mov ax, [esi + K_SHORTS]
    mov [bs_cols + 4], ax
    mov ax, [esi + K_SOCKS]
    mov [bs_cols + 6], ax
    mov esi, bs_cols
.f1: lodsw
    cmp ax, 2
    je .f1
    cmp ax, 15
    je .f1
    mov bx, ax
    mov esi, bs_cols
.f2: lodsw
    cmp ax, 2
    je .f2
    cmp ax, 15
    je .f2
    cmp ax, bx
    je .f2
    mov cx, ax
    mov esi, bs_cols
.f3: lodsw
    cmp ax, bx
    je .f3
    cmp ax, cx
    je .f3
    or ax, ax
    jns .s
    mov ax, cx
.s: mov [BGC], bx
    mov [HLC], cx
    mov [FRAMEC], ax
    ret

bs_box:                                 ; esi = the player (TeamGame + place offset), ebx = 0 left / 1 right,
    mov [bs_side], ebx                  ; eax = the place / row (the mirror)
    imul edi, ebx, SLOT_
    add edi, bs_mir
    mov [bs_slot], edi
    mov [edi + 56], ax
    inc word [edi + 58]
    mov [edi + 4], esi
    push esi
    lea esi, [esi + 42 + 12]            ; (PlayerInfo.shortName)
    lea edi, [edi + 40]
    mov ecx, 15
    rep movsb
    mov byte [edi], 0
    pop esi
    push edi
    mov edi, [bs_slot]
    pop edi
    mov eax, [GT2]                      ; GetPlayer(the file's team number, playerIndex)
    mov ecx, [BTG]
    cmp ecx, TOP
    jne .g
    mov eax, [GT1]
.g: mov ax, [eax]
    mov [D0], ax
    movsx ax, byte [esi + 42 + 1]
    mov [D1], ax
    call GETPLAYER
    mov eax, [A0]
    push edi
    mov edi, [bs_slot]
    pop edi
    mov [bs_rec], eax
    mov edi, [bs_slot]
    mov [edi], eax
    mov byte [bs_sk], 0
    mov [A6], eax
    mov dword [A1], bs_sk
    call FTSS
    push edi
    mov edi, [bs_slot]
    pop edi
    mov eax, [bs_rec]
    mov [A0], eax
    mov dword [A1], bs_pr
    call PRICE
    push edi
    mov edi, [bs_slot]
    pop edi
    mov esi, bs_pr                      ; (the format strings' '*' padding: cut)
.cut: mov al, [esi]
    or al, al
    jz .cd
    cmp al, '*'
    je .c0
    inc esi
    jmp .cut
.c0: mov byte [esi], 0
.cd: mov edi, [bs_slot]
    mov esi, bs_sk
    lea edi, [edi + 8]
    mov ecx, 8
    rep movsb
    mov esi, bs_pr
    mov ecx, 24
    rep movsb
    push edi
    mov edi, [bs_slot]
    pop edi
    mov ax, [SMX]                       ; the box's frame x: the rows' frame edge, left or right
    sub ax, [CAMX]
    sub ax, FW_LEFT + 2
    cmp dword [bs_side], 0
    je .l
    add ax, ROWW - BW_
.l: mov [bs_fx], ax
    add ax, 2                           ; shadow, frame, background: the rows' own colours (DrawSubstitutesMenuEntry)
    mov [D0], ax
    mov word [D1], BOX_Y_ + 2
    mov word [D2], BW_
    mov word [D3], BOX_H_
    mov word [D4], 8
    call FILL
    mov ax, [bs_fx]
    mov [D0], ax
    mov word [D1], BOX_Y_
    mov word [D2], BW_
    mov word [D3], BOX_H_
    mov ax, [FRAMEC]
    mov [D4], ax
    call FILL
    mov ax, [bs_fx]
    inc ax
    mov [D0], ax
    mov word [D1], BOX_Y_ + 1
    mov word [D2], BW_ - 2
    mov word [D3], BOX_H_ - 2
    mov ax, [BGC]
    mov [D4], ax
    call FILL
    mov dword [A0], bs_sk
    mov ax, [bs_fx]
    add ax, BW_ / 2
    mov [D1], ax
    mov word [D2], LINE1_
    mov word [D3], 2
    mov dword [A1], SCH
    call PCS
    mov dword [A0], bs_pr
    mov ax, [bs_fx]
    add ax, BW_ / 2
    mov [D1], ax
    mov word [D2], LINE2_
    mov word [D3], 2
    mov dword [A1], SCH
    call PCS
    push edi
    mov edi, [bs_slot]
    pop edi
    ret

align 4
bs_tag: db 'BSTR'
bs_state: dw -1                         ; (the last frame: 0 / 1 = drawn in that state, -1 = the menu open, nothing)
bs_ord: dw 0
bs_mir: times 2 * SLOT_ db 0            ; (the left / right box's last player: see bstrip.SLOT)
bs_pi: dd 0
bs_rec: dd 0
bs_side: dd 0
bs_slot: dd 0
bs_fx: dw 0
bs_cols: dw 0, 0, 0, 0, 3, 1, 3, 1, -1
bs_sk: times 8 db 0
bs_pr: times 24 db 0
bs_regs: times 15 dd 0
"""


def sites(p):
    """oppl.sites + the strip's own (the original obj1's layout)."""
    import oppl
    s = oppl.sites(p)
    d = bytes(p.le.obj_bytes(1))
    pk = lambda x: re.escape(struct.pack('<I', x))
    u = lambda o: struct.unpack('<I', d[o:o + 4])[0]
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    D0, D1, D2, D3, D7, A0, A1 = (s[k][1] for k in ('D0', 'D1', 'D2', 'D3', 'D7', 'A0', 'A1'))
    A2, A6 = A0 + 8, A0 + 24

    def one(what, pat, b=d):
        m = list(re.finditer(pat, b, re.S))
        assert len(m) == 1, ('bstrip', what, len(m))
        return m[0]
    dsm = s['DSM'][1]
    seg = d[dsm:dsm + 0x700]
    dsme = rel(dsm + one('DrawSubstitutesMenuEntry', rb'\x66\xc7\x05' + pk(D7) + rb'\xff\xff\xe8', seg).end() - 1)
    kit = [d[dsm + m.start() + 3] for m in re.finditer(rb'\x66\x8b\x46.', d[dsm:dsm + 0x80], re.S)]
    assert len(kit) == 4, ('bstrip: the kit colours', kit)
    hl = one('highlight colour', rb'\x66\xa1' + pk(D1) + rb'\x66\xa3(....)\x66\xa1' + pk(D2) + rb'\x66\xa3(....)', seg)
    assert p.target(1, dsm + hl.start(1)) == s['BGC'], 'bstrip: subsMenuBackgroundColor'
    # FirePressedInSubsMenu: add word [D0],10 / mov ax,[D0] / mov [plToEnterGameIndex],ax
    pt = one('plToEnterGameIndex', rb'\x66\x83\x05' + pk(D0) + rb'\x0a\x66\xa1' + pk(D0) + rb'\x66\xa3(....)')
    # InitializeInGameTeamsAndStartGame: ... mov [gameMaxSubstitutes],ax / mov ax,[D3] / mov [..],ax / gameTeam1 / 2
    import benchx
    gts = [m for m in re.finditer(rb'\x66\xa1' + pk(D2) + rb'\x66\xa3(....)\x66\xa1' + pk(D3) + rb'\x66\xa3....\xa1'
                                  + pk(A1) + rb'\xa3(....)\xa1' + pk(A2) + rb'\xa3(....)', d, re.S)
           if (2, u(m.start(1))) == benchx.INFO['GMAX']]   # (raw operands: benchx rewrote the store)
    assert len(gts) == 1, ('bstrip: gameTeam1 / 2', len(gts))
    gt = gts[0]
    price = one('cseg_247C8', rb'\x8b\x35' + pk(A0) + rb'\x80\x7e\x71\x9b\x75.\xc7\x05' + pk(A0) + rb'....\xe9....\x8b\x35'
                + pk(A0) + rb'\x80\x7e\x71\x9a').start()
    ftss = one('FormTopSkillsString', rb'\x8b\x35' + pk(A6) + rb'\x8a\x46\x66\xa2' + pk(D0) + rb'\x66\x81\x25' + pk(D0)
               + rb'\xe0\x00\x66\xc1\x2d' + pk(D0) + rb'\x05\x66\x83\x3d' + pk(D0) + rb'\x00\x0f\x84....\x66\x83\x2d'
               + pk(D0) + rb'\x01\x66\xc1\x25' + pk(D0) + rb'\x02\xc7\x05' + pk(A2)).start()
    regs = {struct.pack('<I', D7 - 28 + 4 * k) for k in range(15)}

    def entry(o):                       # a routine's start: back over its `push dword [Dn / An]` prologue
        while d[o - 6:o - 4] == b'\xff\x35' and d[o - 4:o] in regs:
            o -= 6
        return o
    ftss = entry(ftss)
    price = entry(price)
    gp = one('GetPlayer', rb'\x66\xa1....\x66\x39\x05' + pk(D0) + rb'\x75.\xc7\x05' + pk(A0) + rb'....\xeb.\x66\xa1....'
             rb'\x66\x39\x05' + pk(D0) + rb'\x75.\xc7\x05' + pk(A0)).start()
    gp = entry(gp)
    assert d[gp:gp + 6] == b'\xff\x35' + struct.pack('<I', D1), 'bstrip: GetPlayer starts with push [D1]'
    assert d[ftss:ftss + 6] == b'\xff\x35' + struct.pack('<I', D0), 'bstrip: FormTopSkillsString starts with push [D0]'
    # DrawBenchAndSubsMenu: mov ax,[g_inSubstitutesMenu] / or ax,ax / jnz / mov ax,[g_leavingSubsMenu] / or / jz
    dch = s['DCH']
    st = one('DrawBenchAndSubsMenu', rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1....\x66\x0b\xc0\x0f\x84', d[dch - 0x400:dch])
    dbm = dch - 0x400 + st.start()
    calls = [o for o in range(len(d) - 5) if d[o] == 0xE8 and rel(o) == dbm]
    assert len(calls) == 1, ('bstrip: DrawBenchAndSubsMenu calls', calls)
    # its arrow: mov ax,[g_goToSubsTimer] / or / jnz / mov ax,[g_substituteInProgress] / or / jnz / mov ax,[g_subsState]
    S = pk(s['SUBST'][1])
    ar = one('the arrow condition', rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1' + S
             + rb'\x66\x0b\xc0\x75.\x66\xc7\x05' + pk(D0) + rb'\x04\x05', d[dbm:dch])
    return dict(s, DSME=(1, dsme), K=kit, HLC=p.target(1, dsm + hl.start(2)), PTEG=p.target(1, pt.start(1)),
                GT1=(2, u(gt.start(2))), GT2=(2, u(gt.start(3))), PRICE=(1, price), FTSS=(1, ftss),
                GETPLAYER=(1, gp), CALL=calls[0], INSUBS=p.target(1, dbm + 2),
                GOTIMER=p.target(1, dbm + ar.start(1)), INPROG=p.target(1, dbm + ar.start(2)),
                A2=(2, A2), A4=(2, A0 + 16), A6=(2, A6))


def _asm(p, at):
    import benchx
    import formwide
    s = sites(p)
    prev = p.call_target(1, s['CALL'])
    sym = {k: s[k] for k in ('SWOSPP', 'SUBST', 'IDX', 'BTG', 'BT', 'PL1T', 'PL2T', 'POSTAB', 'TOP', 'BGC', 'HLC',
                             'FRAMEC', 'SCH', 'SMX', 'CAMX', 'FILL', 'PCS', 'DSME', 'PTEG', 'PTSP', 'GT1', 'GT2', 'PRICE',
                             'FTSS', 'GETPLAYER', 'INSUBS', 'GOTIMER', 'INPROG', 'D0', 'D1', 'D2', 'D3', 'D4', 'D7',
                             'A0', 'A1', 'A2', 'A4', 'A6')}
    sym.update(PREV=prev, TABLE=benchx.INFO['TABLE'], SLOT_=(0, SLOT), BW_=(0, BW), BOX_Y_=(0, BOX_Y),
               BOX_H_=(0, BOX_H), LINE1_=(0, LINE1), LINE2_=(0, LINE2), FW_LEFT=(0, formwide.LEFT),
               ROWW=(0, 126 + formwide.WIDE),
               **{f'K_{n}': (0, k) for n, k in zip(('SHIRT', 'STRIPES', 'SHORTS', 'SOCKS'), s['K'])})
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    return s, prev, code, fix, rel, nasmcave.labels(ASM, at, sym)


def size(p):
    """The code's size (nothing written)."""
    return len(_asm(p, 0)[2])


def patch(p, at):
    """bs_* at obj3:at (the chain's end); returns the end."""
    s, prev, code, fix, rel, lab = _asm(p, at)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['CALL'], 0xE8, 3, lab['bs_draw'])
    print(f'exe: bstrip: the bench info strip (skills + value), obj3+{at:#x} ({len(code)} B), GameLoop call '
          f'obj1+{s["CALL"]:#x} (was {prev[0]}:{prev[1]:#x})')
    return at + len(code)
