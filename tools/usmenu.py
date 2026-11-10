"""4.1 RC2 (Davide 09/11, option A + a): STAT > RIEPILOGO of a world's UEFA cup as a menu of green boxes, one per
phase (usmenu.c: the list, the views). obj4's 4th page (swreg.USMENU_AT): usmenu.c, then the glue (US_MENU, the
game's packed menu format as ctview's CR_MENU). obj3 grows by 0 B: ctview's CV_UST (cv_sum's UEFA branch, `call
[CV_UST]` inside its pushad / push es, then cv_page's tail) points at us_open, which drops that call's return and
the saved registers and shows US_MENU as cv_page shows its page. uesum.us_text stays the RIEPILOGO button's page."""
import os
import struct

LABELS = {}
NPH = 6                                         # (usmenu.c NPH, LW)
LW = 32

ASM = """
us_open:                                ; CV_UST (cv_sum: pushad, push es, call [CV_UST]): the phases, then US_MENU
    add esp, 4                          ; instead of the page (cv_page's tail: pop es, popad, A6, SHOW_MENU)
    call US_LIST
    mov eax, [US_SEL]
    inc eax
    mov [US_MENU + 12], eax             ; (the cursor: the current stage)
    pop es
    popad
    mov dword [A6], US_MENU
    jmp SHOW_MENU

us_init:                                ; onInit, and back from a phase's view / page
    pushad
    push es
    push ds
    pop es
    cld
    call US_MINIT
    pop es
    popad
    ret

US_STUBS
us_go:                                  ; entry eax + 1: its view (the game's screens) or the league phase's page
    call us_view
    jmp us_init

us_view:
    pushad
    push es
    push ds
    pop es
    cld
    push eax
    call US_PREP
    add esp, 4
    test eax, eax
    jnz us_pg
    call VC_VIEW                        ; (A0 = the copy, us_prep)
    call US_DONE
    pop es
    popad
    ret

us_sum:                                 ; RIEPILOGO: the whole text page (uesum us_text)
    call us_sumv
    jmp us_init

us_sumv:
    pushad
    push es
    push ds
    pop es
    cld
    call US_TEXT
    jmp us_pg

us_pg:                                  ; (pushad, push es above: cv_page's tail)
    mov byte [FOUND], 1
    mov dword [PAGE], 0
    call FP_FILL
    pop es
    popad
    mov dword [A6], FMTMENU
    jmp SHOW_MENU

align 4
US_MENU:                                ; title, the phases (one column), RIEPILOGO, ESCI
    dd us_init, 0, 0, 1
    dw 0, 0, 304, 14
    dw 4, 17h
    dw 8, 0
    dd US_TTL
    dw 0
US_BUTTONS
    dw -999
"""


def patch(p, lang, ext, sumt):
    """usmenu.c + the glue at obj4:swreg.USMENU_AT; ext: uesum's symbols (UC, US_IN, us_cur, us_stname, us_lpt,
    us_text) and the game's; sumt = the RIEPILOGO label (ctview's CR_SUMT). CV_UST -> us_open. Returns the end."""
    import cobj
    import complist
    import ctgame
    import ctview
    import fmtpage
    import gplay
    import nasmcave
    import rnames
    import swe
    import swreg
    import uefaq
    import uesum
    room = 0x1000 * swe.OBJ4_PAGES
    assert swreg.UESUM_AT < swreg.USMENU_AT < room == p.le.obj(4).npages * 0x1000, ('usmenu: obj4', hex(room))
    assert ctgame.LABELS.get('scr'), 'usmenu: ctgame (its scratch) first'
    t0 = at = swreg.USMENU_AT
    u = uefaq.SYMS
    ext = dict(ext, SCR=ctgame.LABELS['scr'], DREG=u['D0R'], A0R=u['A0R'], VC_CALC=gplay.LABELS['VC_CALC'])
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'usmenu.c'),
                         ['-Oz', '-fno-zero-initialized-in-bss'])
    syms, at, bss = cobj.link(p, obj, at, (4, 0), externs=ext, limit=room, text_obj=4)
    assert bss == 0, ('usmenu.c: no .bss', bss)
    c_end = at
    at = (at + 15) & ~15
    names = [rnames.NAMES[lang][k][0] for k in uesum.STAGES]
    wmax = max(complist.px(n) for n in names)
    w = max(160, (wmax + 16 + 1) & ~1)                  # (one column, centred in the 304 px frame as CV_MENU's)
    assert w <= 300 and all(len(n) < LW for n in names), (lang, wmax)
    x = (304 - w) // 2
    btn = []
    for k in range(NPH):
        btn += [f'    dw {x}, {40 + 22 * k}, {w}, 15', '    dw 2', '    db 0FFh, 0FFh, 0FFh, 0FFh', '    dw 4, 0Eh',
                '    dw 8, 0', f'    dd US_LBL + {LW * k}', '    dw 13', f'    dd us_s{k}', '    dw 0']
    cx = ctview.CR_X
    btn += [f'    dw {cx[0]}, 172, {ctview.CR_W}, 15', '    dw 2', f'    db 0FFh, {NPH + 2}, 0FFh, 0FFh', '    dw 4, 0Eh',
            '    dw 8, 0', '    dd SUMT', '    dw 13', '    dd us_sum', '    dw 0',
            f'    dw {cx[1]}, 172, {ctview.CR_W}, 15', '    dw 2', f'    db {NPH + 1}, 0FFh, 0FFh, 0FFh', '    dw 4, 0Ch',
            '    dw 8, 0', '    dd EXIT_T', '    dw 13', '    dd EXIT_F', '    dw 0']
    src = nasmcave.sub(ASM, 'US_BUTTONS\n', '\n'.join(btn) + '\n')
    src = nasmcave.sub(src, 'US_STUBS\n', ''.join(f'us_s{k}: mov eax, {k}\n    jmp us_go\n' for k in range(NPH)))
    wn = fmtpage.WN
    ws = wn['sym']
    sym = {k: ws[k] for k in ('A6', 'SHOW_MENU', 'PAGE', 'FOUND', 'FMTMENU')}
    sym.update(FP_FILL=(1, wn['fill']), EXIT_T=wn['exit'][0], EXIT_F=wn['exit'][1], SUMT=sumt,
               VC_VIEW=gplay.LABELS['VC_VIEW'], US_TEXT=ext['US_TEXT'])
    for k in ('us_list', 'us_minit', 'us_prep', 'us_done', 'US_SEL', 'US_LBL', 'US_TTL'):
        sym[k.upper() if k.islower() else k] = syms[k]
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(4, at, len(code)))
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    end = at + len(code)
    assert end <= room, ('usmenu past obj4', hex(end))
    cu = ctview.CR_PTRS['ust']
    p.add_ptr(3, cu, 4, lab['us_open'])
    p.put(3, cu, struct.pack('<I', lab['us_open']))
    LABELS.clear()
    LABELS.update(syms, **{k: (4, v) for k, v in lab.items()})
    print(f'exe: UEFA RIEPILOGO phase menu (usmenu, 4.1 RC2): obj4+{t0:#x}..{end:#x} ({end - t0} B: C {c_end - t0}, '
          f'glue {len(code)}, column {w} px); obj4 left {room - end} B')
    return end
