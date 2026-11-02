"""The market list keeps its page after an offer (4.0.6, Enzo on 4.0.5): TRASFERIMENTI > ACQUISTA GIOCATORE > VISUAL.
MERCATO NAZIONALE / ESTERO (showPlayerMarketMenu) lists the players found by its filters ten a page (ELENCA, then ALTRI
pages on). Picking a row opens the offer (cseg_54C1E); back from it (FAI UN'OFFERTA > ESCI) the row handler
(cseg_59F61) put the cursor on ELENCA and called cseg_59E31, which empties the list (found 0, page 0): the next ELENCA
started again at page 1. The filters stayed.
- the row handler's `call cseg_54C1E` -> mk_pick: the picked row's entry first (the offer flow keeps no A5);
- its `call cseg_59E31` -> mk_keep: the list again from the same page (cseg_5A227, ELENCA's own builder: the same
  filters; a player gone in the meantime is no longer there), the page before when that page is now empty, ALTRI /
  ELENCA's label (cseg_59D28), the cursor back on the picked row while it still has a player, the redraw.
A purchase that closes the menu (dseg_17A6DE) leaves it before both, as the game did.
Code in obj3 after squadnum (CONVENTIONS 23).
"""
import re
import struct

import nasmcave
import sacups

PAGE = 10                               # rows a page (entries 10..19)

ASM = r"""
mk_pick:                                ; the row handler's `call cseg_54C1E` (A5 = the picked row's entry)
    mov esi, [A5]
    mov ax, [esi + 2]
    mov [mk_row], ax
    jmp OFFER

mk_keep:                                ; the row handler's `call cseg_59E31` (back from the offer, cursor on ELENCA)
    cmp word [FOUND], 0
    je .r                               ; (nothing listed: nothing to keep)
    call LIST                           ; the list again from [PG]
    cmp word [ONPAGE], 0
    jne .ok
    cmp word [PG], PAGE_
    jb .ok
    sub word [PG], PAGE_                ; that page emptied: the one before
    call LIST
.ok:
    call LABEL                          ; ALTRI / ELENCA
    movzx eax, word [mk_row]
    sub eax, ROW0_
    jb .d
    cmp ax, [ONPAGE]
    jae .d
    mov ax, [mk_row]
    mov [D0], ax
    call SETCUR                         ; the picked row
.d: jmp DRAWMENU
.r: ret

mk_row: dw 0
"""


def sites(p):
    """The row handler's two calls and the market menu's state (original bytes)."""
    d1 = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    pk = lambda a: re.escape(struct.pack('<I', a))
    rel = lambda o: o + 5 + struct.unpack('<i', d1[o + 1:o + 5])[0]
    # call cseg_54C1E; mov ax,[dseg_17A6DE]; or ax,ax; jz +5; jmp SetExitMenuFlag; mov word [D0],7; call SetCurrentEntry;
    #   call cseg_59E31; ret
    m = [x for x in re.finditer(rb'(\xe8....)\x66\xa1....\x66\x0b\xc0\x74\x05\xe9....\x66\xc7\x05' + pk(D0) +
                                rb'\x07\x00(\xe8....)(\xe8....)\xc3', d1, re.S)]
    assert len(m) == 1, ('market row handler', len(m))
    m = m[0]
    offer, setcur, clear = m.start(1), m.start(2), m.start(3)
    c = rel(clear)
    # cseg_59E31: mov ax,[found]; or ax,ax; jz; mov [found],0; mov [onpage],0; mov [page],0; call cseg_59D28; jmp DrawMenu
    assert re.fullmatch(rb'\x66\xa1....\x66\x0b\xc0\x74.(\x66\xc7\x05....\x00\x00){3}\xe8....\xe9....', d1[c:c + 48], re.S), \
        d1[c:c + 48].hex()
    found, onpage, page = (p.target(1, c + 2), p.target(1, c + 23), p.target(1, c + 32))
    assert p.target(1, c + 14) == found and onpage != page, (found, onpage, page)
    label, drawmenu = rel(c + 38), rel(c + 43)
    # ELENCA / ALTRI (cseg_59CC7): mov [page],ax; call cseg_5A227; call cseg_59D28; jmp DrawMenu
    n = [x.start(1) for x in re.finditer(rb'\x66\xa3' + re.escape(d1[c + 32:c + 36]) + rb'(\xe8....)\xe8....\xe9', d1, re.S)
         if rel(x.start(1) + 5) == label and rel(x.start(1) + 10) == drawmenu]
    assert len(n) == 1, ('ELENCA', n)
    return {'offer': offer, 'clear': clear, 'c59e31': c, 'LIST': (1, rel(n[0])), 'LABEL': (1, label),
            'DRAWMENU': (1, drawmenu), 'SETCUR': (1, rel(setcur)), 'FOUND': found, 'ONPAGE': onpage, 'PG': page,
            'D0': (2, D0), 'A5': (2, r['A0'] + 20)}


def patch(p, at):
    """mk_* at obj3:at (after squadnum); returns the end."""
    s = sites(p)
    sym = {k: s[k] for k in ('LIST', 'LABEL', 'DRAWMENU', 'SETCUR', 'FOUND', 'ONPAGE', 'PG', 'D0', 'A5')}
    assert p.call_target(1, s['clear']) == (1, s['c59e31']), hex(s['clear'])
    sym.update(OFFER=p.call_target(1, s['offer']), PAGE_=(0, PAGE), ROW0_=(0, PAGE))   # (rows = entries 10..19)
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['offer'], 0xE8, 3, lab['mk_pick'])
    p.branch(1, s['clear'], 0xE8, 3, lab['mk_keep'])
    print(f'exe: mklist: the market list keeps its page after an offer, obj3+{at:#x} ({len(code)} B), '
          f'row handler obj1+{s["offer"]:#x}')
    return at + len(code)
