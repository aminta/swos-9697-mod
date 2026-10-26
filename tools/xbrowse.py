"""4.0.2: the extras (XTRA players 17-30) of a club in the game's own club browse (TRASFERIMENTI > ACQUISTA GIOCATORE >
ACQ. ALTRO GIOCAT. NAZION. / STRANIERO > ... > club): `buyOtherPlayersMenu` lists the 16 players of the club's record (16 rows,
y 27 + 9 r, ESCI below); a club with extras gets a second page.

The menu is copied into the obj1 cave with one more entry (31, after the template's cells): a button PAG. SUCC. / PAG. PREC.
at the right of ESCI (ESCI's right link -> it). The two users of the menu (BuyOtherDomesticPlayer, BuyOtherForeignPlayer:
`mov [A6], buyOtherPlayersMenu`) are retargeted to the copy. BuyOtherPlayersInit starts with xb_init: page 0, the label NEXT.
The first row's draw (xb_row_draw) hides the button (isInvisible) for a club without extras. The button (xb_page) flips the page
and redraws. On page 2 the two calls of GetPlayerInfoBreakPosition (the row's draw in BuyOtherPlayersAfterDrawCommon, the pick in
BuyOtherPlayersCommon) become xb_row_draw / xb_row_pick: row r = the r-th extra still there (xtra.py's cache, the sold ones
skipped): D1 = 16 + its slot, A0 = the player - 4Ch, the shown number + 16; a row past the last extra draws / picks nothing (and
page 2 of a club whose last extra was just bought falls back to page 1). The offer flow after the pick (cseg_54C1E -> GetPlayer)
already takes an index >= 16 (xtra.py gp_wide).
"""
import re
import struct

import nasmcave
import sacups
import xtra

TEXTS = {   # (next, previous)
    'it': (b'PAG. SUCC.', b'PAG. PREC.'),
    'en': (b'NEXT PAGE', b'PREV. PAGE'),
    'fr': (b'PAGE SUIV.', b'PAGE PREC.'),
    'de': (b'WEITER', b'VORIGE SEITE'),
}
PAYLOAD = {1: 0, 2: 4, 4: 2, 8: 6, 9: 2, 12: 4, 13: 4, 14: 6, 15: 4, 16: 4, 17: 2, 18: 2, 19: 2, 20: 2, 21: 4}
BUTTON = (196, 185, 90, 15)            # x, y (menu coordinates; the screen adds 8), width, height: right of ESCI (x 122, w 60)
COLOR = 0x0E

ASM = r"""
xb_init:                                ; BuyOtherPlayersInit's first instruction `mov ax, [teamOffering]`
    mov byte [xb_pg], 0
    pushfd
    pushad
    call xb_label
    popad
    popfd
    mov ax, [TEAMOFF]
    ret

xb_vis:                                 ; the button is there only for a club with extras: [A0] = the club's record -> eax = extras
    pushad
    mov esi, [A0]
    movzx eax, word [esi]
    call XT_BLOCK
    xor ebx, ebx
    test eax, eax
    jz .n
    lea esi, [eax + 4]
    mov ecx, MAXE_
.c:
    cmp byte [esi + 3], 0
    je .s
    inc ebx
.s:
    add esi, PLAYER_
    dec ecx
    jnz .c
.n:
    mov [xb_n], ebx                     ; (CalcMenuEntryAddress clobbers ebx)
    mov dword [D0], NEWENT_
    call CALC
    mov edi, [A0]
    xor eax, eax
    cmp dword [xb_n], 0
    sete al
    mov [edi + 4], ax                   ; isInvisible
    popad
    mov eax, [xb_n]
    ret

xb_label:                               ; the button's label: next (page 0) / previous (page 1)
    mov edi, xb_buf
    mov esi, [xb_txt]
    cmp byte [xb_pg], 0
    je .c
    mov esi, [xb_txt + 4]
.c:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    test al, al
    jnz .c
    ret

xb_page:                                ; fire on the button: the other page, redrawn, the cursor stays on it
    xor byte [xb_pg], 1
    pushad
    call xb_label
    popad
    mov dword [D0], NEWENT_
    call SETCUR
    jmp DRAWMENU

xb_row_draw:                            ; replaces `call GetPlayerInfoBreakPosition` in BuyOtherPlayersAfterDrawCommon
    cmp word [D1], 0
    jne .rows
    pushad                              ; row 0: the button's visibility (the list's first row is drawn before it)
    mov eax, [A0]                       ; (D0 / A0 are the game's: A0 = the club's record here, saved around the call)
    mov [xb_a0], eax
    mov eax, [D0]
    mov [xb_d0], eax
    call xb_vis
    mov eax, [xb_a0]
    mov [A0], eax
    mov eax, [xb_d0]
    mov [D0], eax
    popad
.rows:
    cmp byte [xb_pg], 0
    jne .p2
    jmp GPIBP
.p2:
    call xb_pick
    jnc .ok
    cmp word [D1], 0
    jne .none
    mov byte [xb_pg], 0                 ; the last extra was bought: back to page 1, drawn as such
    pushad
    call xb_label
    popad
    jmp GPIBP
.none:
    add esp, 4                          ; no such extra: nothing to draw, out of the draw function
.ok:
    ret

xb_row_pick:                            ; replaces it in BuyOtherPlayersCommon
    cmp byte [xb_pg], 0
    jne .p2
    jmp GPIBP
.p2:
    call xb_pick
    jnc .ok
    add esp, 4                          ; an empty row: nothing is picked
.ok:
    ret

xb_pick:                                ; D1 = row, A0 = the club's record -> CF = no such extra; else D1 = 16 + the slot of
    pushad                              ; the row's extra, A0 = the player - 4Ch, D6 (the shown number) + 16
    movzx edx, word [D1]
    mov esi, [A0]
    movzx eax, word [esi]
    call XT_BLOCK
    test eax, eax
    jz .none
    lea esi, [eax + 4]
    xor ecx, ecx
.f:
    cmp ecx, MAXE_
    jae .none
    cmp byte [esi + 3], 0
    je .skip
    test edx, edx
    jz .hit
    dec edx
.skip:
    add esi, PLAYER_
    inc ecx
    jmp .f
.hit:
    lea eax, [ecx + 16]
    mov [D1], ax
    sub esi, 76
    mov [A0], esi
    add word [D6], 16
    clc
    popad
    ret
.none:
    stc
    popad
    ret

align 4
xb_pg: db 0
align 4
xb_mark: db 'XBRW'
xb_n: dd 0
xb_a0: dd 0
xb_d0: dd 0
xb_txt: dd 0, 0
xb_buf: times 16 db 0
"""


def _u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def _rel(d, c):
    return c + 5 + struct.unpack_from('<i', d, c + 1)[0]


def find(p):
    """The sites of the club browse in the original exe."""
    d1, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    A0 = r['A0']
    ptr = lambda a: re.escape(struct.pack('<I', a))
    # BuyOtherPlayersInit: mov ax,[teamOffering]; mov [D0],ax; call GetTeamPointer; mov eax,[A0]; mov [teamPtr],eax
    m = [x for x in re.finditer(rb'\x66\xa1(....)\x66\xa3' + ptr(D0) + rb'\xe8....\xa1' + ptr(A0) + rb'\xa3(....)', d1, re.S)]
    m = [x for x in m if p.target(1, x.start() + 2)[0] == 2]
    inits = []
    for x in m:                                     # the one whose function is the menu's init (a fixup in obj2 points to it)
        if any(f[0] == 2 and (f[3], f[4]) == (1, x.start()) for f in p.le.fixups()):
            inits.append(x)
    assert len(inits) == 1, len(inits)
    init = inits[0]
    teamoff, teamptr = _u32(d1, init.start() + 2), _u32(d1, init.end() - 4)
    # BuyOtherPlayersAfterDrawCommon / Common: mov eax,[teamPtr]; mov [A0],eax; call GetPlayerInfoBreakPosition; ...
    head = rb'\xa1' + ptr(teamptr) + rb'\xa3' + ptr(A0) + rb'(\xe8....)'
    draw = [x for x in re.finditer(head + rb'\xa1' + ptr(A0) + rb'\xa3' + ptr(A0 + 24), d1, re.S)]
    pick = [x for x in re.finditer(head + rb'\x66\xa1' + ptr(teamoff) + rb'\x66\xa3' + ptr(D0) + rb'\xe8', d1, re.S)]
    assert len(draw) == 1 and len(pick) == 1, (len(draw), len(pick))
    gp = _rel(d1, draw[0].start(1))
    assert gp == _rel(d1, pick[0].start(1))
    # Common's tail: mov [D0], 2; call SetCurrentEntry; jmp DrawMenu; the entry address function: mov [D0], 3; call CalcMenuEntryAddress
    t = re.compile(rb'\x66\xc7\x05' + ptr(D0) + rb'\x02\x00(\xe8....)(\xe9....)', re.S).search(d1, pick[0].start(), pick[0].start() + 0x80)
    c = re.compile(rb'\xc7\x05' + ptr(D0) + rb'\x03\x00\x00\x00(\xe8....)', re.S).search(d1, pick[0].start() - 0xC0, pick[0].start())
    assert t and c, (bool(t), bool(c))
    # the menu: obj2 data whose first dword is the init function
    refs = [f for f in p.le.fixups() if f[0] == 2 and (f[3], f[4]) == (1, init.start())]
    assert len(refs) == 1
    start = refs[0][1]
    users = [f[1] for f in p.le.fixups() if f[0] == 1 and (f[3], f[4]) == (2, start)]
    assert len(users) == 2, users
    return dict(D0=D0, A0=A0, teamoff=teamoff, teamptr=teamptr, init=init.start(), draw=draw[0].start(1), pick=pick[0].start(1),
                gpibp=gp, setcur=_rel(d1, t.start(1)), drawmenu=_rel(d1, t.start(2)), calc=_rel(d1, c.start(1)),
                menu=start, users=users)


def menu_parse(d2, start):
    """(end offset of the packed menu at obj2:start (its -999), {entry number: (entry offset, links offset)}); entry 0 is the
    first record after the 16-byte header."""
    k, n, out = start + 16, 0, {}
    while True:
        w = struct.unpack_from('<h', d2, k)[0]
        if w == -999:
            return k, out
        if w == -998:
            k += 6
            continue
        if w == -996:                                    # reset the template entry
            k += 2
            continue
        tmpl = w == -997                                 # the next record defines the template, not an entry
        if tmpl:
            k += 2
        e, links = k, None
        k += 8
        while True:
            t = struct.unpack_from('<H', d2, k)[0]
            k += 2
            if t == 0:
                break
            assert t in PAYLOAD, (n, t)
            if t == 2:
                links = k
            k += PAYLOAD[t]
        if not tmpl:
            out[n] = (e, links)
            n += 1


def patch(p, at, lang):
    """Code + menu copy at obj1:at; returns the end."""
    s = find(p)
    d1, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    end, ents = menu_parse(d2, s['menu'])
    new = len(ents)
    assert new == 31, new
    esci_links = ents[2][1]
    assert d2[esci_links:esci_links + 4] == bytes((0xFF, 0xFF, 0x12, 0xFF)), d2[esci_links:esci_links + 4].hex()
    xl = xtra.LABELS
    at = (at + 15) & ~15
    sym = {'D0': (2, s['D0']), 'D1': (2, s['D0'] + 4), 'D6': (2, s['D0'] + 24), 'A0': (2, s['A0']), 'TEAMOFF': (2, s['teamoff']),
           'CALC': (1, s['calc']), 'SETCUR': (1, s['setcur']), 'DRAWMENU': (1, s['drawmenu']), 'GPIBP': (1, s['gpibp']),
           'XT_BLOCK': (1, xl['xt_block']), 'PLAYER_': (0, xtra.PLAYER), 'MAXE_': (0, xtra.MAX_EXTRA), 'NEWENT_': (0, new)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    nxt, prv = TEXTS[lang]
    base_txt = (at + len(code) + 15) & ~15
    txt = nxt + b'\0' + prv + b'\0'
    p.put(1, base_txt, txt)
    p.add_ptr(1, lab['xb_txt'], 1, base_txt)
    p.add_ptr(1, lab['xb_txt'] + 4, 1, base_txt + len(nxt) + 1)
    # the menu copy: the original + the button (a new origin record, entry 19) + the end mark
    x, y, w, h = BUTTON
    ent = struct.pack('<hhh', -998, 0, 0) + struct.pack('<hhhhH', x, y, w, h, 2) + bytes((2, 0xFF, 18, 0xFF))
    ent += struct.pack('<HHHH', 4, COLOR, 8, 0)
    buf_at = len(ent)
    ent += struct.pack('<IH', 0, 13)
    sel_at = len(ent) - 0
    ent += struct.pack('<IH', 0, 0)
    mc = bytearray(d2[s['menu']:end])
    mc[esci_links - s['menu'] + 1] = new          # ESCI: right -> the button
    copy = bytearray(mc) + ent + struct.pack('<h', -999)
    ptrs = [(o - s['menu'], t_obj, t_off) for (s_obj, o, _, t_obj, t_off, *_r) in p.le.fixups()
            if s_obj == 2 and s['menu'] <= o < end]
    ptrs += [(len(mc) + buf_at, 1, lab['xb_buf']), (len(mc) + sel_at, 1, lab['xb_page'])]
    mat = (base_txt + len(txt) + 15) & ~15
    while any((mat + o) // 0x1000 != (mat + o + 3) // 0x1000 for o, _, _ in ptrs):
        mat += 4
    assert not any(d1[mat:mat + len(copy)]) and mat + len(copy) < 0x7FFFFFFF
    p.put(1, mat, bytes(copy))
    for o, t_obj, t_off in ptrs:
        p.add_ptr(1, mat + o, t_obj, t_off)
    for u in s['users']:                                 # mov [A6], offset buyOtherPlayersMenu: the copy
        p.retarget(1, u, 1, mat)
        p.put(1, u, struct.pack('<I', mat))
    # the hooks
    def call(o, tgt, size, fixup=None):
        if fixup:
            p.remove(1, o + fixup)
        p.put(1, o, b'\xE8' + struct.pack('<i', tgt - (o + 5)) + b'\x90' * (size - 5))
    call(s['init'], lab['xb_init'], 6, 2)                # mov ax, [teamOffering]  (66 A1 addr)
    call(s['draw'], lab['xb_row_draw'], 5)
    call(s['pick'], lab['xb_row_pick'], 5)
    print(f'exe: club browse pages: menu copy obj1+{mat:#x} ({len(copy)} B), code obj1+{at:#x} ({len(code)} B)')
    return (mat + len(copy) + 15) & ~15
