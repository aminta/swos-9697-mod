"""The opponent's squad, read only, in the in-match bench menu (4.0.6, Davide's option b): the game shows the opponent
only as the 5 figures of its dugout. In the bench (g_subsState 0), UP on the coach (g_benchPlayerIndex 0) - nothing
in a real match, the other half of the bench in a training game - opens a new state 5: the opponent's list, drawn by
the game's own substitutes menu (DrawSubstitutesMenu in its header-less state 3, the opponent's kit colours): page 0
= its 11 on the pitch in formation order (shirt number, face, name, position, small yellow / red card, injury cross),
DOWN / UP = the pages of its bench (the places 12.. still available: no one replaced, sent off or left out), FIRE /
LEFT / RIGHT = back to the bench (SubsBenchOff, the cursor on the coach). Every page has the opponent's name on top
(Davide's look review), in the header row's place and style (the menu's frame / background, white small font).
The match stands still as in the game's other bench menus (bench mode = g_inSubstitutesMenu; no g_subsState reader
takes 5 for 1..4, 4.0.6 research).
Read only: state 5 has its own control handler (BenchMenuHandleControls' chain `cmp [g_subsState], 4` -> op_ctl) and
draw (DrawBenchAndSubsMenu's chain -> op_dsp); they write g_subsState, the page and, around the draw only, the
pointers the menu reads (benchTeam / benchTeamGame -> the opponent or, for a bench page, a copy of its
TeamGeneralInfo with a sprites table of zeroed sprites: no card / injury marks; plToBeSubstitutedPos -1; the first 11
of benchx's offsets table = that page's places, in the order the formation's ordinals read them; the rows count
op_rows, DrawSubstitutesMenu's `cmp word [D7], 11` -> op_cnt, 11 outside a bench page), all restored after it. The
opponent's data is only read. Not in a training game (UP keeps swapping the halves), not under SWOS++ (it patches
DrawSubstitutesMenuEntry; no reliable online flag: menunum's SWOS++ byte).
Code in obj3 after mk_keep (CONVENTIONS 23).
"""
import re
import struct

import benchx
import nasmcave
import sacups

GI_SIZE = 0x91                          # TeamGeneralInfo
SPR_SIZE = 0x6E                         # Sprite
PI = 61                                 # PlayerInfo (in-match)

ASM = r"""
op_up:                                  ; BenchMenuHandleControls, UP on the coach: `mov ax, [g_trainingGame]`
    mov ax, [TRAIN]
    or ax, ax
    jnz .r                              ; a training game: the other half, as before
    cmp byte [SWOSPP], 0FFh
    jne .z                              ; SWOS++ running: nothing, as before
    mov word [SUBST], 5
    mov word [op_pg], 0
    mov word [BFIRE], 1
.z: xor eax, eax                        ; (-> jz @@out)
.r: ret

op_ctl:                                 ; BenchMenuHandleControls' chain: `cmp word [g_subsState], 4`
    cmp word [SUBST], 5
    je .mine
    cmp word [SUBST], 4
    ret
.mine:
    add esp, 4                          ; (BenchMenuHandleControls returns from here)
    mov al, [SFIRE]
    or al, al
    jnz .off
    mov ax, [SDIR]
    cmp ax, 2
    je .off
    cmp ax, 6
    je .off
    or ax, ax
    je .up
    cmp ax, 4
    je .down
    ret
.off:
    jmp SUBSOFF                         ; state 0, the cursor on the coach
.up:
    mov word [BDIR], 1
    cmp word [op_pg], 0
    je .r
    dec word [op_pg]
.r: ret
.down:
    mov word [BDIR], 1
    call op_opp
    call op_nb                          ; eax = the bench players listed
    movzx ecx, word [op_pg]
    imul ecx, ecx, 11
    cmp ecx, eax
    jae .r                              ; (page k >= 1 lists bench rows 11 (k - 1) ..)
    inc word [op_pg]
    ret

op_dsp:                                 ; DrawBenchAndSubsMenu's chain: `cmp word [g_subsState], 4`
    cmp word [SUBST], 5
    je .mine
    cmp word [SUBST], 4
    ret
.mine:
    add esp, 4                          ; (DrawBenchAndSubsMenu returns from here)
    pushad
    call op_opp                         ; esi -> its TeamGame, edi -> its TeamGeneralInfo
    push dword [BT]
    push dword [BTG]
    push word [PTSP]
    mov word [SUBST], 3                 ; the menu without its header
    mov word [PTSP], -1                 ; no row lit
    mov [BTG], esi
    cmp word [op_pg], 0
    jne .bench
    mov [BT], edi                       ; page 0: the 11 on the pitch, as the game lists ours
    call DSM
    jmp .done
.bench:
    push esi
    mov esi, edi                        ; a copy of its TeamGeneralInfo: zeroed sprites (no marks on the bench)
    mov edi, op_gi
    mov ecx, GI_
    rep movsb
    pop esi
    mov dword [op_gi + 14h], op_spr
    mov dword [BT], op_gi
    call op_nb
    movzx ecx, word [op_pg]
    dec ecx
    imul ecx, ecx, 11                   ; ecx = the page's first bench row
    sub eax, ecx
    cmp eax, 11
    jbe .n
    mov eax, 11
.n: mov [op_rows], ax
    mov ebx, TABLE                      ; benchx's offsets: the first 11 saved, then the page's places
    mov edx, [ebx]
    mov [op_tsv], edx
    mov edx, [ebx + 4]
    mov [op_tsv + 4], edx
    mov edx, [ebx + 8]
    mov [op_tsv + 8], edx
    mov edx, [ebx + 12]
    mov [op_tsv + 12], edx
    mov edx, [ebx + 16]
    mov [op_tsv + 16], edx
    mov dx, [ebx + 20]
    mov [op_tsv + 20], dx
    movzx edx, word [PL1T]              ; its formation's ordinals (GetBenchPlayerPointer's own choice)
    cmp word [op_gi + 12h], 1
    je .t
    movzx edx, word [PL2T]
.t: mov edx, [POSTAB + edx * 4]
    xor esi, esi                        ; row
.row:
    cmp si, [op_rows]
    jae .draw
    movzx eax, byte [op_list + ecx + esi]
    imul eax, eax, PI_
    movzx edi, byte [edx + esi]
    dec edi
    mov [ebx + edi * 2], ax
    inc esi
    jmp .row
.draw:
    call DSM
    mov ebx, TABLE                      ; restored
    mov edx, [op_tsv]
    mov [ebx], edx
    mov edx, [op_tsv + 4]
    mov [ebx + 4], edx
    mov edx, [op_tsv + 8]
    mov [ebx + 8], edx
    mov edx, [op_tsv + 12]
    mov [ebx + 12], edx
    mov edx, [op_tsv + 16]
    mov [ebx + 16], edx
    mov dx, [op_tsv + 20]
    mov [ebx + 20], dx
    mov word [op_rows], 11
.done:
    call op_ttl                         ; its name on top, in the header's place
    pop word [PTSP]
    pop dword [BTG]
    pop dword [BT]
    mov word [SUBST], 5
    popad
    ret

op_ttl:                                 ; the opponent's name in the header's place (y 10), the menu's colours and
    push dword [D7]                     ;   style (DrawSubstitutesMenuEntry's FORMATION row of state 4)
    push dword [A0]
    push dword [A1]
    mov ax, [SMX]
    sub ax, [CAMX]
    mov [D0], ax
    mov word [D1], 10
    mov word [D2], 126
    mov word [D3], 11
    mov word [D4], 8                    ; the shadow
    call FILL                           ; (FillRectangle wrecks D0..D3: all set again for each)
    mov ax, [SMX]
    sub ax, [CAMX]
    sub ax, 2
    mov [D0], ax
    mov word [D1], 8
    mov word [D2], 126
    mov word [D3], 11
    mov ax, [FRAMEC]
    mov [D4], ax                        ; the frame
    call FILL
    mov ax, [SMX]
    sub ax, [CAMX]
    dec ax
    mov [D0], ax
    mov word [D1], 9
    mov word [D2], 124
    mov word [D3], 9
    mov ax, [BGC]
    mov [D4], ax                        ; the background
    call FILL
    mov ax, [SMX]
    sub ax, [CAMX]
    add ax, 63
    mov [D1], ax
    mov word [D2], 11
    mov word [D3], 2
    mov eax, [BTG]
    add eax, 22                         ; TeamGame.teamName
    mov [A0], eax
    mov dword [A1], SCH
    call PCS
    pop dword [A1]
    pop dword [A0]
    pop dword [D7]
    ret

op_cnt:                                 ; DrawSubstitutesMenu's `cmp word [D7], 11` (11 outside a bench page)
    push eax
    mov ax, [op_rows]
    cmp [D7], ax
    pop eax
    ret

op_opp:                                 ; -> esi = the opponent's TeamGame, edi = its TeamGeneralInfo (DrawOpponentsBench's)
    mov edi, [BT]
    mov edi, [edi]                      ; benchTeam's opponentsTeam
    mov esi, TOP
    cmp dword [BTG], BOTTOM
    je .r
    mov esi, BOTTOM
.r: ret

op_nb:                                  ; esi = TeamGame -> eax = its bench places still available, op_list = them
    push ebx
    push ecx
    push edx
    xor eax, eax
    mov cx, [GMAX]
    cmp cx, 5
    jae .m
    mov cx, 5
.m: movzx ecx, cx
    add ecx, 11                         ; the places 11 .. 10 + max(5, bench)
    mov ebx, 11
.l: cmp ebx, ecx
    jae .e
    imul edx, ebx, PI_
    cmp byte [esi + 42 + edx], 0        ; substituted (replaced, empty, left out)
    jne .x
    cmp byte [esi + 42 + edx + 4], 0    ; position -1
    jl .x
    cmp byte [esi + 42 + edx + 10], 2   ; sent off
    jae .x
    mov [op_list + eax], bl
    inc eax
.x: inc ebx
    jmp .l
.e: pop edx
    pop ecx
    pop ebx
    ret

db 'OPPL'                               ; (the harness finds op_pg after it)
op_pg: dw 0                             ; the page: 0 = the pitch, 1.. = the bench, 11 a page
op_rows: dw 11
align 4
op_tsv: times 22 db 0
op_list: times 16 db 0
op_gi: times GI_ db 0
align 4
op_spr: times 11 dd op_dummy
op_dummy: times SPR_ db 0
"""


def sites(p):
    """The original obj1's sites and variables."""
    d = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d)
    D0, D1, D7, A0, A1 = r['D7'] - 28, r['D7'] - 24, r['D7'], r['A0'], r['A1']
    pk = lambda x: re.escape(struct.pack('<I', x))
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    rel6 = lambda o: o + 6 + struct.unpack('<i', d[o + 2:o + 6])[0]
    v = benchx.INFO if 'SUBST' in benchx.INFO else benchx.sites2(p, r)[1]     # (a probe of the original: no INFO)
    subst, idx, train = v['SUBST'][1], v['IDX'][1], v['TRAIN'][1]
    S = pk(subst)
    # the two state chains: cmp [S],1 / jz / cmp [S],3 / jz / cmp [S],2 / jz / cmp [S],4 / jz / retn
    ch = [m.start() for m in re.finditer(rb'\x66\x83\x3d' + S + rb'\x01\x0f\x84....\x66\x83\x3d' + S + rb'\x03\x0f\x84....'
                                         rb'\x66\x83\x3d' + S + rb'\x02\x0f\x84....\x66\x83\x3d' + S + rb'\x04\x0f\x84....\xc3',
                                         d, re.S)]
    assert len(ch) == 2, ('g_subsState chains', ch)
    draw = [c for c in ch if rel6(c + 8) == rel6(c + 50)]          # the draw chain: 1 and 4 -> DrawSubstitutesMenu
    assert len(draw) == 1, ('draw chain', draw)
    dch, = draw
    cch, = [c for c in ch if c != dch]
    dsm = rel6(dch + 8)
    # UP on the coach: mov ax,[IDX] / or ax,ax / jnz / mov ax,[TRAIN] / or ax,ax / jz +5 / call TrainingSwapBenchTeams
    up = [m.start() + 11 for m in re.finditer(rb'\x66\xa1' + pk(idx) + rb'\x66\x0b\xc0\x75.\x66\xa1' + pk(train) +
                                              rb'\x66\x0b\xc0\x74\x05\xe8', d, re.S)]
    assert len(up) == 1, ('UP on the coach', up)
    # DrawSubstitutesMenu's loop end: add word [D7],1 / cmp word [D7],11 / jnz
    cnt = [m.start() + 8 for m in re.finditer(rb'\x66\x83\x05' + pk(D7) + rb'\x01\x66\x83\x3d' + pk(D7) + rb'\x0b\x0f\x85',
                                              d[dsm:dsm + 0x800], re.S)]
    assert len(cnt) == 1, ('DrawSubstitutesMenu loop', cnt)
    cnt = dsm + cnt[0]
    # its highlight: mov ax,[plToBeSubstitutedPos] / cmp [D7],ax / jnz
    hl = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\x39\x05' + pk(D7) + rb'\x75', d[dsm:cnt], re.S)]
    assert len(hl) == 2 and d[dsm + hl[1] - 3:dsm + hl[1] - 1] == b'\x04\x75', ('plToBeSubstitutedPos', hl)   # (2nd: state 4's
    ptsp = p.target(1, dsm + hl[0] + 2)[1]                                                    #  selectedPlayerInSubs)
    # SubsBenchOff: g_subsState 0, subsBlockDirections 1, subsBlockFire 1, subsWriteOnly 2, retn
    off = [m.start() for m in re.finditer(rb'\x66\xc7\x05' + S + rb'\x00\x00\x66\xc7\x05(....)\x01\x00\x66\xc7\x05(....)'
                                          rb'\x01\x00\x66\xc7\x05....\x02\x00\xc3', d, re.S)]
    assert len(off) == 1, ('SubsBenchOff', off)
    off = off[0]
    bdir, bfire = p.target(1, off + 12)[1], p.target(1, off + 21)[1]
    # BenchMenuHandleControls' @@check_left_right: cmp [D0],2 / jz / cmp [D0],6 / jz / mov al,[subsFire] / or al,al / jnz
    lr = [m.start() for m in re.finditer(rb'\x66\x83\x3d' + pk(D0) + rb'\x02\x0f\x84....\x66\x83\x3d' + pk(D0) +
                                         rb'\x06\x0f\x84....\xa0(....)\x0a\xc0\x0f\x85', d, re.S)]
    assert len(lr) == 1, ('@@check_left_right', lr)
    sfire = p.target(1, lr[0] + 29)[1]
    # @@check_directions: mov ax,[subsDirection] / mov [D0],ax (just before, within 0x60)
    sd = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\xa3' + pk(D0), d[lr[0] - 0x60:lr[0]], re.S)]
    assert len(sd) == 1, ('subsDirection', sd)
    sdir = p.target(1, lr[0] - 0x60 + sd[0] + 2)[1]
    # DrawOpponentsBench: cmp [benchTeamGame], offset bottomTeamInGame / jz / mov [A0], ... / mov eax,[benchTeam] / mov [A1],eax
    ob = [m.start() for m in re.finditer(rb'\x81\x3d........\x74.\xc7\x05' + pk(A0) + rb'....\xa1....\xa3' + pk(A1), d, re.S)]
    assert len(ob) == 1, ('DrawOpponentsBench', ob)
    btg, bt = p.target(1, ob[0] + 2)[1], p.target(1, ob[0] + 23)[1]
    top, bottom = p.target(1, ob[0] - 4), p.target(1, ob[0] + 6)        # (mov [A0], topTeamInGame just before)
    assert d[ob[0] - 10:ob[0] - 4] == b'\xc7\x05' + struct.pack('<I', A0), 'topTeamInGame'
    # GetBenchPlayerPointer: mov ax,[pl1Tactics] / mov [D1],ax / mov eax,[benchTeam] / ... / mov ax,[pl2Tactics] / ...
    #   shl word [D1],2 / mov dword [A0], positionsTable
    gb = [m.start() for m in re.finditer(rb'\x66\xa1(....)\x66\xa3' + pk(D1) + rb'\xa1' + pk(bt) + rb'.{10,24}?\x66\xa1(....)\x66\xa3'
                                         + pk(D1) + rb'\x66\xc1\x25' + pk(D1) + rb'\x02\xc7\x05' + pk(A0), d, re.S)]
    assert len(gb) == 1, ('GetBenchPlayerPointer', gb)
    m = re.match(rb'\x66\xa1(....)\x66\xa3' + pk(D1) + rb'\xa1' + pk(bt) + rb'.{10,24}?\x66\xa1(....)\x66\xa3' + pk(D1) +
                 rb'\x66\xc1\x25' + pk(D1) + rb'\x02\xc7\x05' + pk(A0), d[gb[0]:], re.S)
    pl1, pl2 = p.target(1, gb[0] + 2)[1], p.target(1, gb[0] + m.start(2))[1]
    postab = p.target(1, gb[0] + m.end())
    # menunum's SWOS++ byte: DrawLittlePlayersAndBall's `push [A4]` (+0x23), 0FFh unless SWOS++ hooked it
    tac = [m.start() for m in re.finditer(rb'\x66\x81\x05' + pk(D0) + rb'\xa1\x00\x66\x83\x2d' + pk(A0 - 24) + rb'\x09'
                                         rb'(?:\xff\x35....){3}\xff\x35' + pk(A0 + 16), d, re.S)]
    assert len(tac) == 1, ('tactics pitch', tac)
    swospp = tac[0] + 0x23
    # the header's tools: the menu's colours (mov ax,[D1] / mov [bg],ax / mov ax,[D2] / mov [hl],ax; mov ax,[D3] /
    #   mov [frame],ax), mov [A1], smallCharsTable / mov [A4], ..., the sprite shadow's x (subsMenuX - g_cameraX + 43)
    #   and FillRectangle, DrawSubstitutesMenuEntry (mov word [D7],-1 / call) and its FORMATION PrintCenteredStringInColor
    Dk = lambda k: pk(D7 - 28 + 4 * k)
    seg = d[dsm:dsm + 0x700]

    def one(pat, b):
        m = list(re.finditer(pat, b, re.S))
        assert len(m) == 1, ('oppl header site', len(m), pat[:24])
        return m[0]

    bgc = one(rb'\x66\xa1' + Dk(1) + rb'\x66\xa3(....)\x66\xa1' + Dk(2) + rb'\x66\xa3....', seg)
    frm = one(rb'\x66\xa1' + Dk(3) + rb'\x66\xa3(....)\xa1', seg)
    sch = one(rb'\xc7\x05' + pk(A1) + rb'(....)\xc7\x05' + pk(A0 + 16), seg)
    mx = one(rb'\x66\xa1(....)\x66\xa3' + Dk(0) + rb'\x66\xa1(....)\x66\x29\x05' + Dk(0) + rb'\x66\x83\x05' + Dk(0) +
             rb'\x2b', seg)
    fill = rel(dsm + seg.index(b'\xe8', mx.end()))
    dsme = rel(dsm + one(rb'\x66\xc7\x05' + pk(D7) + rb'\xff\xff\xe8', seg).end() - 1)
    e = d[dsme:dsme + 0x300]
    assert rel(dsme + e.index(b'\xe8')) == fill, 'FillRectangle'
    pcs = rel(dsme + e.index(b'\xe8', one(rb'\x66\xc7\x05' + Dk(3) + rb'\x02\x00\x66\x83\x05' + Dk(2) + rb'\x01', e).end()))
    hdr = {'BGC': p.target(1, dsm + bgc.start(1)), 'FRAMEC': p.target(1, dsm + frm.start(1)),
           'SCH': p.target(1, dsm + sch.start(1)), 'SMX': p.target(1, dsm + mx.start(1)),
           'CAMX': p.target(1, dsm + mx.start(2)), 'FILL': (1, fill), 'PCS': (1, pcs),
           'D0': (2, D7 - 28), 'D1': (2, D7 - 24), 'D2': (2, D7 - 20), 'D3': (2, D7 - 16), 'D4': (2, D7 - 12),
           'A0': (2, A0), 'A1': (2, A1)}
    return {'UP': up[0], 'CCH': cch + 42, 'DCH': dch + 42, 'CNT': cnt, 'DSM': (1, dsm), 'SUBSOFF': (1, off),
            'SUBST': (2, subst), 'IDX': (2, idx), 'TRAIN': (2, train), 'PTSP': (2, ptsp), 'BDIR': (2, bdir),
            'BFIRE': (2, bfire), 'SFIRE': (2, sfire), 'SDIR': (2, sdir), 'BTG': (2, btg), 'BT': (2, bt),
            'PL1T': (2, pl1), 'PL2T': (2, pl2), 'POSTAB': postab, 'SWOSPP': (1, swospp), 'D7': (2, D7),
            'TOP': top, 'BOTTOM': bottom, **hdr}


def patch(p, at):
    """op_* at obj3:at (after mk_keep); returns the end."""
    s = sites(p)
    sym = {k: s[k] for k in ('DSM', 'SUBSOFF', 'SUBST', 'TRAIN', 'PTSP', 'BDIR', 'BFIRE', 'SFIRE', 'SDIR', 'BTG', 'BT',
                             'PL1T', 'PL2T', 'POSTAB', 'SWOSPP', 'D7', 'TOP', 'BOTTOM', 'BGC', 'FRAMEC', 'SCH', 'SMX',
                             'CAMX', 'FILL', 'PCS', 'D0', 'D1', 'D2', 'D3', 'D4', 'A0', 'A1')}
    sym.update(TABLE=benchx.INFO['TABLE'], GMAX=benchx.INFO['GMAX'], GI_=(0, GI_SIZE), SPR_=(0, SPR_SIZE), PI_=(0, PI))
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    d = p.le.obj_bytes(1)
    for site, n, lbl in ((s['UP'], 6, 'op_up'), (s['CCH'], 8, 'op_ctl'), (s['DCH'], 8, 'op_dsp'), (s['CNT'], 8, 'op_cnt')):
        assert bytes(p.get(1, site, n)) == d[site:site + n], ('oppl: site already patched', lbl, hex(site))
        p.remove(1, site + n - 4 - (1 if n == 8 else 0))      # (the operand's fixup: mov ax,[x] +2, cmp word [x],imm8 +3)
        p.branch(1, site, 0xE8, 3, lab[lbl], n)
    print(f'exe: oppl: the opponent squad in the bench menu, obj3+{at:#x} ({len(code)} B), UP on the coach obj1+{s["UP"]:#x}')
    return at + len(code)
