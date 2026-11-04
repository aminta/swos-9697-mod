"""4.0.6 (Davide 03/11, after Nicola's MILAN purchases): the CPU replacements switch, World 2026-27 only.

What the game does: a player bought from a CPU club's 16-player record leaves a hole that the game fills at once with an
INVENTED player (cseg_56379's last call, cseg_56615: the first name of one random player + the surname of another
(cseg_52B6A over random clubs, cseg_52D40), the sold player's position, skills from the club's squad (cseg_567B5), price),
stored in the CPU squads' change list (AddCareerPoolPlayer -> careerForeignMarketPlayers: dw team, db index, db ext,
the 38-byte player; reapplied by GetTeamPointer, cseg_243BD, at every load of the club). A bought XTRA player (places
17+, xtra.py) gets no replacement. Nicola: CAMARDA (place 11) -> 'GUSTAVO MANCINI'; the harness, 4.0.5: 'BILLY CUNHA'.

The switch (ACQUISTA GIOCATORE, the bottom row right of ESCI: 'RIMP. CPU: INVENTATI' / 'RIMP. CPU: DALLA ROSA'):
  - INVENTED (0, the default: a new career, an older save, any other world) = the game as before;
  - FROM SQUAD (1): after the game's tail (the invented player in the slot and in the change list, xtra / xleft's
    bookkeeping done), one of the seller's own XTRA players still there takes the slot instead: the 38 bytes of his
    XTRA record go into the record slot AND into the change list's entry (so the club keeps him at every reload), and
    he is listed as gone from places 17+ (xleft's xl_add: XS, then XL) and blanked in the market's block cache.
    Pick (deterministic): a goalkeeper only for a goalkeeper and never for an outfield player; the same role group
    first (P / TD TS D / MD MS M / A: positionAndFace >> 5 = 0 / 1-3 / 4-6 / 7), then any outfield player; the highest
    price, the lowest place on a tie. Skipped: a player listed on the home market (homeMarketPlayers: he is for sale), a
    name already in the club's 16, and every candidate when XS and XL are both full (no ring overwrite from here).
    No candidate: the invented player stays.
The button is hidden outside World 2026-27 (xtra's XTRA file name is data\\xtw5.nnn only while that world is current).
The value is saved with the career (engine item 'CR', 1 byte, world_only; a new career zeroes it = INVENTED).
buyPlayerMenu (obj2, frozen) is copied into obj3 with the button appended (entry 8; ESCI's right link -> it), its one
user (BuyPlayerMenu's `mov [A6], buyPlayerMenu`) retargeted; the copy's init / on-return (BuyPlayerInit) become cr_init.
"""
import re
import struct

import nasmcave
import sacups
import xbrowse
import xleft
import xtra

TEXTS = {   # (INVENTED, FROM SQUAD): the small font, <= 113 px (button 121)
    'it': ('RIMP. CPU: INVENTATI', 'RIMP. CPU: DALLA ROSA'),
    'en': ('CPU REPL.: INVENTED', 'CPU REPL.: FROM SQUAD'),
    'fr': ('REMPL. CPU: INVENTES', 'REMPL. CPU: EFFECTIF'),
    'de': ('ERSATZ CPU: ERFUNDEN', 'ERSATZ CPU: KADER'),
}
BUTTON = (183, 185, 121, 15)           # x, y, width, height: right of ESCI (x 122, w 60), as TAKE OFF MARKET
COLOR = 0x0E
NEWENT = 8
LABELS = {}

ASM = r"""
cr_w5:                                  ; ZF = 1: the current world is World 2026-27 (xtra's file name data\xtw5.nnn)
    push eax
    mov eax, [XNAMEP]
    cmp dword [eax + 5], 'xtw5'
    pop eax
    ret

cr_label:                               ; the button's label for cr_mode -> cr_buf
    pushad
    mov esi, cr_t0
    cmp byte [cr_mode], 0
    je .c
    mov esi, cr_t1
.c: mov edi, cr_buf
.l: lodsb
    stosb
    test al, al
    jnz .l
    popad
    ret

cr_vis:                                 ; entry NEWENT_ hidden outside World 2026-27
    mov eax, [D0]
    mov [cr_d0], eax
    mov eax, [A0]
    mov [cr_a0], eax
    mov dword [D0], NEWENT_
    call CALC
    mov edi, [A0]
    xor eax, eax
    call cr_w5
    setne al
    mov [edi + 4], ax                   ; isInvisible
    mov eax, [cr_d0]
    mov [D0], eax
    mov eax, [cr_a0]
    mov [A0], eax
    ret

cr_init:                                ; the copy's init and on-return: the game's BuyPlayerInit, then the button
    call BPINIT
    pushad
    call cr_label
    call cr_vis
    popad
    ret

cr_toggle:                              ; fire on the button: the other value, redrawn, the cursor stays on it
    xor byte [cr_mode], 1
    call cr_label
    mov dword [D0], NEWENT_
    call SETCUR
    jmp DRAWMENU

cr_sold:                                ; cseg_56379's tail call (D0 seller, D1 index): the chain (xleft -> xtra -> the
    pushad                              ; game's tail: the invented player), then FROM SQUAD: one of the seller's extras
    mov eax, [D0]
    mov [cr_d0], eax
    mov eax, [D1]
    mov [cr_d1], eax
    popad
    call PREV_SOLD
    pushad
    cmp byte [cr_mode], 0
    je .out
    call cr_w5
    jne .out
    mov ax, [cr_d0]
    cmp ax, [SEL]
    je .out
    movzx ecx, word [cr_d1]
    cmp ecx, 16
    jae .out
    movzx edx, word [XSOLD]             ; XS and XL both full: no promotion (the oldest XL entry would be overwritten)
    cmp edx, XSOLD_
    jb .room
    cmp byte [XL], 0
    je .room
    cmp word [XL + 1], XLMAX_
    jae .out
.room:
    movzx edx, word [NFM2]              ; the game's tail added the invented player as the change list's last entry
    test edx, edx
    jz .out
    dec edx
    imul edx, edx, 42
    add edx, CFMP
    cmp [edx], ax
    jne .out
    cmp [edx + 2], cl
    jne .out
    mov [cr_ent], edx
    mov esi, REGS                       ; the record slot (GetTeamPointer: D0 -> A0), the game's registers kept
    mov edi, cr_regs
    mov ecx, 15
    rep movsd
    movzx eax, word [cr_d0]
    mov [D0], eax
    call GTP
    mov eax, [A0]
    mov [cr_rec], eax
    mov esi, cr_regs
    mov edi, REGS
    mov ecx, 15
    rep movsd
    mov esi, [cr_rec]
    movzx ecx, word [cr_d1]
    imul ecx, ecx, PLAYER_
    lea esi, [esi + 76 + ecx]
    mov [cr_slot], esi
    movzx eax, byte [esi + 1Ah]
    shr eax, 5
    mov [cr_pos], al
    mov ax, [cr_d0]
    call XT_BLOCK                       ; the seller's extras still there (XS / XL blanked)
    test eax, eax
    jz .out
    add eax, 4
    mov [cr_blk], eax
    mov dword [cr_best], -1
    mov dword [cr_key], -1
    xor ebx, ebx                        ; k
.k:
    imul edi, ebx, PLAYER_
    add edi, [cr_blk]
    cmp byte [edi + 3], 0
    je .kn
    movzx eax, byte [edi + 1Ah]
    shr eax, 5
    mov dl, [cr_pos]
    test dl, dl                         ; a goalkeeper for a goalkeeper only, never for an outfield player
    jnz .of
    test al, al
    jnz .kn
    jmp .grp
.of:
    test al, al
    jz .kn
.grp:
    call cr_group
    mov ah, al
    mov al, dl
    call cr_group
    xor edx, edx
    cmp al, ah
    jne .key
    mov edx, 100h                       ; the same role group first
.key:
    movzx eax, byte [edi + 20h]         ; price
    add edx, eax
    cmp edx, [cr_key]
    jle .kn
    lea ecx, [ebx + 16]                 ; on the home market: for sale, skipped
    mov ax, [cr_d0]
    call cr_onmarket
    jnz .kn
    lea esi, [edi + 3]                  ; a name already in the club's 16: skipped
    call cr_inrec
    jnz .kn
    mov [cr_key], edx
    mov [cr_best], ebx
.kn:
    inc ebx
    cmp ebx, MAXE_
    jb .k
    mov ebx, [cr_best]
    test ebx, ebx
    js .out
    imul esi, ebx, PLAYER_
    add esi, [cr_blk]
    push esi
    mov edi, [cr_slot]                  ; the record slot
    mov ecx, PLAYER_
    rep movsb
    pop esi
    push esi
    mov edi, [cr_ent]                   ; the change list's entry: kept at every reload of the club
    add edi, 4
    mov ecx, PLAYER_
    rep movsb
    pop esi
    mov byte [esi + 3], 0               ; out of the cached block (places 17+)
    lea ecx, [ebx + 16]
    mov ax, [cr_d0]
    call XL_ADD                         ; and listed as gone (XS, then XL): never back on page 2 nor with a new job
    inc dword [cr_count]
.out:
    popad
    ret

cr_group:                               ; al = position 0..7 -> al = role group (0 P, 1 TD TS D, 2 MD MS M, 3 A)
    test al, al
    jz .r
    cmp al, 3
    ja .m
    mov al, 1
    ret
.m: cmp al, 6
    ja .a
    mov al, 2
    ret
.a: mov al, 3
.r: ret

cr_onmarket:                            ; ax team, cl index -> ZF = 0 when (team, index) is on the home market
    push ecx
    push edx
    push esi
    movzx edx, word [NHM]
    cmp edx, 25
    jbe .n
    mov edx, 25
.n: mov esi, HMP
.e: test edx, edx
    jz .no
    cmp [esi], ax
    jne .en
    cmp [esi + 2], cl
    je .yes
.en:
    add esi, 4
    dec edx
    jmp .e
.yes:
    or edx, edx                         ; (edx > 0: ZF = 0)
    jmp .r
.no:
    xor edx, edx                        ; ZF = 1
.r: pop esi
    pop edx
    pop ecx
    ret

cr_inrec:                               ; esi -> a name -> ZF = 0 when one of [cr_rec]'s 16 has it
    push ecx
    push edx
    push esi
    push edi
    xor edx, edx
.q:
    imul edi, edx, PLAYER_
    add edi, [cr_rec]
    add edi, 76 + 3
    push esi
    mov ecx, 23
    repe cmpsb
    pop esi
    je .yes
    inc edx
    cmp edx, 16
    jb .q
    xor edx, edx                        ; ZF = 1
    jmp .r
.yes:
    or edx, 1                           ; ZF = 0
.r: pop edi
    pop esi
    pop edx
    pop ecx
    ret

align 4
cr_d0: dd 0
cr_d1: dd 0
cr_a0: dd 0
cr_rec: dd 0
cr_slot: dd 0
cr_ent: dd 0
cr_blk: dd 0
cr_best: dd 0
cr_key: dd 0
cr_count: dd 0                          ; (promotions this session: the harness reads it)
cr_regs: times 15 dd 0
cr_mark: db 'CRFL'                      ; (the harness finds cr_mode by this)
cr_mode: db 0                           ; 0 INVENTED, 1 FROM SQUAD: engine item 'CR'
cr_pos: db 0
cr_buf: times 32 db 0
"""


def sites(p):
    """buyPlayerMenu (obj2) + its user (BuyPlayerMenu: mov word [flag], 0; mov [A6], buyPlayerMenu; call ShowMenu;
    cmp word [flag], 1) + BuyPlayerInit; homeMarketPlayers + numHomeMarketPlayers (AddPlayerToCareerContest:
    cmp word [num], 25; jz; mov [A1], homeMarketPlayers; mov ax, [num])."""
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    A1, A6 = r['A0'] + 4, r['A0'] + 24
    ptr = lambda a: re.escape(struct.pack('<I', a))
    m = [x for x in re.finditer(rb'\x66\xc7\x05(....)\x00\x00\xc7\x05' + ptr(A6) + rb'(....)\xe8....\x66\x83\x3d\1\x01', d1, re.S)]
    assert len(m) == 1, ('BuyPlayerMenu', len(m))
    user = m[0].start(2)
    obj, menu = p.target(1, user)
    assert obj == 2, obj
    d2 = p.le.obj_bytes(2)
    hdr = {f[1] - menu: (f[3], f[4]) for f in p.le.fixups() if f[0] == 2 and menu <= f[1] < menu + 16}
    assert hdr.get(0) == hdr.get(4) and hdr[0][0] == 1 and struct.unpack_from('<I', d2, menu + 12)[0] == 2, hdr
    m = [x for x in re.finditer(rb'\x66\x83\x3d(....)\x19\x74.\xc7\x05' + ptr(A1) + rb'(....)\x66\xa1\1', d1, re.S)]
    assert len(m) == 1, ('AddPlayerToCareerContest', len(m))
    nhm, hmp = p.target(1, m[0].start(1)), p.target(1, m[0].start(2))
    assert nhm[0] == 2 and hmp[0] == 2, (nhm, hmp)
    return {'user': user, 'menu': menu, 'init': hdr[0][1], 'nhm': nhm[1], 'hmp': hmp[1]}


def patch(p, at, lang):
    """Code + the menu copy at obj3:at (the obj3 chain's end; World 2026-27 builds: xtra + xleft first); returns the end."""
    s = sites(p)
    import lepatch
    xb = xbrowse.find(lepatch.LEPatch(bytes(p.le.data)))   # (the exe as read: this one's fixups are retargeted by now)
    xs = xleft.sites(p, sacups.regs(p.le.obj_bytes(1)))
    X, L = xtra.LABELS, xleft.LABELS
    d2 = p.le.obj_bytes(2)
    end, ents = xbrowse.menu_parse(d2, s['menu'])
    assert len(ents) == NEWENT, len(ents)
    esci = ents[NEWENT - 1][1]
    assert d2[esci:esci + 4] == bytes((0xFF, 0xFF, 6, 0xFF)), d2[esci:esci + 4].hex()
    prev = p.call_target(1, X['SOLD_SITE'])
    assert prev == (3, L['xl_sold']), prev
    t0, t1 = TEXTS[lang]
    assert all(xbrowse_px(t) <= 113 for t in (t0, t1)), (t0, t1)
    at = (at + 15) & ~15
    sym = {'XNAMEP': (1, X['XTRA_NAMEP']), 'XT_BLOCK': (1, X['xt_block']), 'XSOLD': (1, X['xsold']), 'GTP': (1, X['GTP']),
           'XL': (3, L['XL']), 'XL_ADD': (3, L['xl_add']), 'PREV_SOLD': prev, 'BPINIT': (1, s['init']),
           'CALC': (1, xb['calc']), 'SETCUR': (1, xb['setcur']), 'DRAWMENU': (1, xb['drawmenu']),
           'SEL': (2, xs['sel']), 'REGS': (2, xs['D0']), 'D0': (2, xs['D0']), 'D1': (2, xs['D1']), 'A0': (2, xs['A0']),
           'NFM2': (2, xs['nfm2']), 'CFMP': (2, xs['cfmp']), 'NHM': (2, s['nhm']), 'HMP': (2, s['hmp']),
           'PLAYER_': (0, xtra.PLAYER), 'MAXE_': (0, xtra.MAX_EXTRA), 'XSOLD_': (0, xtra.XSOLD),
           'XLMAX_': (0, xleft.XLMAX), 'NEWENT_': (0, NEWENT)}
    src = ASM + f"cr_t0: db '{t0}', 0\ncr_t1: db '{t1}', 0\n"
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    # the menu copy: the original (init / on-return -> cr_init, ESCI's right -> the button) + the button + the end mark
    x, y, w, h = BUTTON
    ent = struct.pack('<hhh', -998, 0, 0) + struct.pack('<hhhhH', x, y, w, h, 2) + bytes((NEWENT - 1, 0xFF, NEWENT - 2, 0xFF))
    ent += struct.pack('<HHHH', 4, COLOR, 8, 0)
    buf_at = len(ent)
    ent += struct.pack('<IH', 0, 13)
    sel_at = len(ent)
    ent += struct.pack('<IH', 0, 0)
    mc = bytearray(d2[s['menu']:end])
    mc[esci - s['menu'] + 1] = NEWENT
    copy = bytes(mc) + ent + struct.pack('<h', -999)
    ptrs = [(o - s['menu'], t_obj, t_off) for (s_obj, o, _, t_obj, t_off, *_r) in p.le.fixups()
            if s_obj == 2 and s['menu'] <= o < end and o - s['menu'] not in (0, 4)]
    ptrs += [(0, 3, lab['cr_init']), (4, 3, lab['cr_init']),
             (len(mc) + buf_at, 3, lab['cr_buf']), (len(mc) + sel_at, 3, lab['cr_toggle'])]
    mat = (at + len(code) + 15) & ~15
    while any((mat + o) // 0x1000 != (mat + o + 3) // 0x1000 for o, _, _ in ptrs):
        mat += 4
    assert not any(p.get(3, mat, len(copy)))
    p.put(3, mat, copy)
    for o, t_obj, t_off in ptrs:
        p.add_ptr(3, mat + o, t_obj, t_off)
    p.retarget(1, s['user'], 3, mat)
    p.put(1, s['user'], struct.pack('<I', mat))
    p.branch(1, X['SOLD_SITE'], 0xE8, 3, lab['cr_sold'])
    import engine
    engine.ITEM_AT['CR'] = (3, lab['cr_mode'])
    LABELS.update(lab)
    LABELS['MENU'] = mat
    print(f'exe: CPU replacements switch: code obj3+{at:#x} ({len(code)} B), menu copy obj3+{mat:#x} ({len(copy)} B), '
          f'sold {X["SOLD_SITE"]:#x}, buyPlayerMenu obj2+{s["menu"]:#x}')
    return mat + len(copy)


def xbrowse_px(s):
    import complist
    return complist.px(s)
