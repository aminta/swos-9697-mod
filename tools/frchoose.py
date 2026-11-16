"""4.2 preseason friendlies, the chooser page (Davide 16/11; owner Friends Choice). What the page is and does:
tools/frchoose.c (the page) and tools/frcsel.h (its state over fr_pick). This file: the 4 languages' texts, the packed
menu, the glue and the link into obj4's FRCH band (CONVENTIONS 23bis; MC 16/11: swreg.FRCH_AT 0x1FF00 .. FRCH_END
0x20F00, patch.py raises swe.OBJ4_PAGES).

Band layout: two fixed slots (FRCH_AT: jmp fc_show, the C's way to the glue; FRCH_AT + 8: jmp frc_choose, the ENGINE's
call target - a fixed address, so FRND links first and needs no symbol of this band), frchoose.c (+ frcsel.c) from
FRCH_AT + 16, then the glue below (handlers, FC_MENU), the language's strings at
END - STR_BACK, the C .bss at END - BSS_BACK (written by frc_choose before it is read), the last 256 B free (floor).
The game is touched in ONE place: chooseTeamsFriendlyMenu's header (obj2), whose initFunc and onReturn - both the
game's ChooseTeamsFriendlyInitFinish, or whatever a module before this one put there: chained - become fc_lhook = the
old routine, then fc_list (the club list's colours while the page browses for a row; nothing otherwise).
The engine (Motore's FRND) calls (4, FRCH_AT + 8) = LABELS['FRC_CHOOSE_SLOT']; without this band it skips the call.
SWOS++: frc_choose returns at once (no page, the plain automatic pick). No obj4 address goes into a save.

Until FRND is on this branch the pick is linked HERE too (FRC_OWN_PICK, a bigger interim band in the 4.3 reservation's
room): `pick` = FRND's {'fr_pick': (obj, off), 'fr_level': ...} switches to the one copy and the real band.
"""
import os
import re
import struct

TITLE = {'it': 'AMICHEVOLI ESTIVE', 'en': 'PRESEASON FRIENDLIES', 'fr': 'MATCHS AMICAUX', 'de': 'TESTSPIELE'}
LVLL = {'it': 'AUTOMATICHE', 'en': 'AUTOMATIC', 'fr': 'AUTOMATIQUES', 'de': 'AUTOMATISCH'}
LVL = {'it': ('MISTE', 'FACILI', 'MEDIE', 'DIFFICILI'), 'en': ('MIXED', 'EASY', 'MEDIUM', 'HARD'),
       'fr': ('MIXTES', 'FACILES', 'MOYENS', 'DIFFICILES'), 'de': ('GEMISCHT', 'LEICHT', 'MITTEL', 'SCHWER')}
BAND = {'it': ('SUPERIORE', 'PARI', 'INFERIORE'), 'en': ('STRONGER', 'EVEN', 'WEAKER'),
        'fr': ('SUPERIEUR', 'EGAL', 'INFERIEUR'), 'de': ('STAERKER', 'GLEICH', 'SCHWAECHER')}
VEN = {'it': ('C', 'F'), 'en': ('H', 'A'), 'fr': ('D', 'E'), 'de': ('H', 'A')}      # home, away (the calendar's letters)
MSG = {'it': ('', 'SQUADRA NON DISPONIBILE', 'SQUADRA SCELTA DUE VOLTE', 'TROPPE SQUADRE IN MEMORIA',
              'NESSUNA AVVERSARIA DISPONIBILE'),
       'en': ('', 'CLUB NOT AVAILABLE', 'CLUB CHOSEN TWICE', 'TOO MANY CLUBS IN MEMORY', 'NO OPPONENTS AVAILABLE'),
       'fr': ('', 'CLUB NON DISPONIBLE', 'CLUB CHOISI DEUX FOIS', 'TROP DE CLUBS EN MEMOIRE',
              'AUCUN ADVERSAIRE DISPONIBLE'),
       'de': ('', 'KLUB NICHT VERFUEGBAR', 'KLUB DOPPELT GEWAEHLT', 'ZU VIELE KLUBS IM SPEICHER',
              'KEINE GEGNER VERFUEGBAR')}
GO = {'it': 'CONTINUA', 'en': 'CONTINUE', 'fr': 'CONTINUER', 'de': 'WEITER'}     # (the game's own button, rule 2)
PICK = {'it': 'SCEGLI AVVERSARIA', 'en': 'CHOOSE OPPONENT', 'fr': 'CHOISIR ADVERSAIRE', 'de': 'GEGNER WAEHLEN'}
LANGS = ('it', 'en', 'fr', 'de')

# the page's geometry (x, y, w, h)
G_TITLE = (0, 0, 304, 14)
G_LEG = (8, 20, 62, 9)                  # the legend boxes: the row above the rows, top left; + (w + 2) each
G_LVLL = (8, 36, 110, 11)
G_LVL = (122, 36, 174, 11)
G_ROW_Y, G_ROW_DY, G_ROW_H = 54, 16, 11
G_VEN = (8, 20)                         # a row's cells: (x, w)
G_CLUB = (32, 152)
G_BAND = (188, 84)
G_LV = (276, 20)
G_MSG = (8, 124, 288, 11)
G_GO = (112, 144, 80, 15)

STR_BACK = 0x3C0                        # (from the band's end: the strings, 448 B)
BSS_BACK = 0x200                        # (the .bss, 256 B; then the 256 B floor)
OWN_SIZE = 0x1C00                       # the interim band with the pick linked here (FRC_OWN_PICK)
PROBE_SIZE = 0x1000                     # + the test caller's room (FRC_PROBE: its code, FrcCtx and the embedded table)
LABELS = {}


def on():
    return os.environ.get('FRCHOOSE', '1') != '0'


def probing():
    """FRC_PROBE=1 (test builds of this branch alone): a season-start caller of frc_choose, PROBE below"""
    return os.environ.get('FRC_PROBE', '0') != '0'


def band(own):
    """(FRCH_AT, FRCH_END): swreg's; the interim band of a build with its own pick (+ the probe's room)"""
    import swreg
    assert own or not probing(), 'FRC_PROBE: only without FRND (the engine is the caller there)'
    return swreg.FRCH_AT, (swreg.FRCH_AT + OWN_SIZE + (PROBE_SIZE if probing() else 0) if own else swreg.FRCH_END)


def page_end(own=True):
    return (band(own)[1] + 0xFFF) & ~0xFFF


def cdefs():
    """frchoose.c's and frcsel.h's #defines the page's layout and strings follow (one place for the numbers)"""
    d = {}
    here = os.path.dirname(os.path.abspath(__file__))
    for f in ('frchoose.c', 'frcsel.h'):
        for m in re.finditer(r'^#define (F\w+)\s+(0x[0-9A-Fa-f]+|\d+)\b', open(os.path.join(here, f)).read(), re.M):
            d[m.group(1)] = int(m.group(2), 0)
    return d


def texts(lang):
    """one language's strings as the C reads them: {symbol: bytes}; asserts charset, width and room"""
    from complist import px, font_odd
    d = cdefs()
    assert d['FRC_LEVELS'] == len(LVL[lang]) == 4 and d['FRC_M_COUNT'] == len(MSG[lang]) == 5, lang
    alls = (TITLE[lang], LVLL[lang], GO[lang], PICK[lang]) + LVL[lang] + BAND[lang] + VEN[lang] + MSG[lang]
    for x in alls:
        assert re.fullmatch(r'[A-Z ]*', x) and not font_odd(x), (lang, x)       # (small font: no umlaut bytes, rule 2)
    fit = [(TITLE[lang], 300), (LVLL[lang], G_LVLL[2] - 4), (GO[lang], G_GO[2] - 6), (PICK[lang], 200)]
    fit += [(x, G_LVL[2] - 4) for x in LVL[lang]] + [(x, G_BAND[1] - 4) for x in BAND[lang]]
    fit += [(x, G_LEG[2] - 2) for x in BAND[lang]] + [(x, G_VEN[1] - 4) for x in VEN[lang]]
    fit += [(x, G_MSG[2] - 4) for x in MSG[lang]]
    for x, w in fit:
        assert px(x) <= w, (lang, x, px(x), w)
    fixed = lambda xs, n: b''.join(_fx(x, n) for x in xs)
    return {'FC_S_LVL': fixed(LVL[lang], 16), 'FC_S_BAND': fixed(BAND[lang], 12), 'FC_S_VEN': fixed(VEN[lang], 4),
            'FC_S_MSG': fixed(MSG[lang], 40), 'FC_S_TTL': TITLE[lang].encode() + b'\0',
            'FC_S_LVLL': LVLL[lang].encode() + b'\0', 'FC_S_GO': GO[lang].encode() + b'\0',
            'FC_S_PICK': PICK[lang].encode() + b'\0'}


def _fx(x, n):
    assert len(x) < n, (x, n)
    return x.encode().ljust(n, b'\0')


ASM = r"""
%macro C_IN 0
    pushad
    push es
    push ds
    pop es
    cld
%endmacro
%macro C_OUT 0
    pop es
    popad
%endmacro

fc_show:                                ; frchoose.c show(): the page, A6 kept (the engine keeps D0..A6 around frc_choose)
    push dword [A6]
    mov dword [A6], FC_MENU
    call SHOW_MENU
    pop dword [A6]
    ret

fc_init:                                ; onInit and onReturn (the game re-unpacks the menu after the club browser)
    C_IN
    call FC_PAINT
    C_OUT
    ret

fc_hl:                                  ; the AUTOMATIC row: LEFT / RIGHT / FIRE (D7)
    C_IN
    call FC_LEVEL
    C_OUT
    jmp DRAWMENU

FC_STUBS
fc_hv:                                  ; FIRE on row eax's venue
    C_IN
    push eax
    call FC_VENUE
    add esp, 4
    C_OUT
    jmp DRAWMENU

fc_hc:                                  ; FIRE on row eax's club: cleared, or the game's club browser
    C_IN
    push eax
    call FC_CLUB
    add esp, 4
    test eax, eax
    C_OUT
    jnz .b
    jmp DRAWMENU
.b: mov dword [A0], FC_S_PICK           ; as BuyOtherForeignPlayer: clubs only, one club, nothing added to the cache
    mov dword [A1], 0
    mov word [D2], 1
    mov word [D3], 0
    mov word [D4], 0
    call BROWSE                         ; -> word D0 = FFFFh (ESCI) or A0 = the club's record in teamFileBuffer
    C_IN
    call FC_PICKED
    C_OUT
    jmp DRAWMENU

fc_go:                                  ; CONTINUE: the page's state is the choice
    mov word [EXITM], 1
    ret

fc_lhook:                               ; chooseTeamsFriendlyMenu's initFunc / onReturn: the list, then its colours
    call LIST_PREV
    C_IN
    call FC_LIST
    C_OUT
    ret

align 4
    db 'FCPG'                           ; (harness: the descriptor, linear addresses once loaded)
    dd FC_SEL, FC_TRACE, FC_NAME, FC_K, FC_MENU
FC_MENU:
    dd fc_init, fc_init, 0, E_GO
FC_ENTRIES
    dw -999
"""


# TEST ONLY (FRC_PROBE=1, a build without FRND): the engine's season-start call as friendlies-a-interface.md words it,
# so the page can be run in the game before Motore's fr_season exists. InitializeNewSeason's `call cseg_3D204` (the
# call after cseg_5DEB9, ffp.find's 'season' + 5; E8 kept, chained on whatever is there) becomes fc_probe: the old
# call first, the game's D0..A6 saved and put back (as ffp's ff_season), then frc_choose(ctx, given, venues) through
# the engine's slot. ctx: world 0's table (tools/frdata/frstr_w0.bin, embedded), self = selTeamNumber, no B team, no
# avoid list, room NULL, season / seed 0, nhome 2, a scratch FR_ST. Before the call the stack below esp is filled
# with A5h down to the C runtime's _STACKLOW: the harness reads the low-water mark with the page / the club list open.
# 'FCPB' descriptor: FCP_ESP (esp at the fill), FCP_DONE (returns of frc_choose), _STACKLOW's address, then given[4],
# venues, FR_ST (16 B).
PROBE = r"""
fc_probe:
    call FCP_PREV
    pushad
    push es
    push ds
    pop es
    cld
    mov [FCP_ESP], esp
    mov edi, [STACKLOW]
    mov ecx, esp
    sub ecx, 64
    sub ecx, edi
    jbe .f
    mov al, 0A5h
    rep stosb
.f: mov esi, REGS
    mov edi, FCP_REGS
    mov ecx, 15
    rep movsd
    mov ax, [SELTEAM]
    mov [FCP_CTX + 10], ax
    mov dword [FCP_GIVEN], -1
    mov dword [FCP_GIVEN + 4], -1
    mov byte [FCP_VEN], 0FFh
    push FCP_VEN
    push FCP_GIVEN
    push FCP_CTX
    call FRC_SLOT
    add esp, 12
    inc dword [FCP_DONE]
    mov esi, FCP_REGS
    mov edi, REGS
    mov ecx, 15
    rep movsd
    pop es
    popad
    ret

align 4
    db 'FCPB'
FCP_ESP: dd 0
FCP_DONE: dd 0
    dd STACKLOW
FCP_GIVEN: dw 0, 0, 0, 0
FCP_VEN: dd 0
FCP_FRST: times 16 db 0
FCP_REGS: times 15 dd 0
FCP_CTX:                                ; FrcCtx (frnd.h; frcsel.h asserts these offsets)
    dd FCP_BLOB, FCP_BLOB_LEN           ; +0 frss, +4 len
    dw 0, 0, 0FFFFh, 0                  ; +8 world 0, +10 self, +12 self2 (none)
    dd 0, 0, 0                          ; +16 avoid, +20 navoid, +24 room
    dd 0, 0, 2                          ; +28 season, +32 seed, +36 nhome
    dd FCP_FRST                         ; +40 frst
FCP_BLOB:
FCP_BLOB_DB
"""


def probe_sites(p):
    """the probe's call site (1, off), _STACKLOW, selTeamNumber"""
    import careerworld
    import ffp
    d1 = p.le.obj_bytes(1)
    site = ffp.find(p)['season'] + 5
    assert d1[site] == 0xE8 and p.get(1, site, 1) == b'\xE8', 'frchoose probe: InitializeNewSeason call cseg_3D204'
    m = list(re.finditer(rb'\x89\xe0\x2b\x05.{4}\xc3', d1, re.S))       # stackavail_: mov eax, esp; sub eax, _STACKLOW
    assert len(m) == 1, ('stackavail_', len(m))
    sel = (careerworld.SITES.get('nc') or {}).get('selteam')
    assert sel and sel[0] == 2, ('frchoose probe: selTeamNumber (careerworld.SITES)', sel)
    return site, p.target(1, m[0].start() + 4), sel


def menu(d):
    """FC_MENU's entries (nasm lines) in frchoose.c's order: FC_E_*"""
    E = d['FC_E_ROW']
    ven, club = (lambda k: E + 4 * k), (lambda k: E + 4 * k + 1)
    L = []

    def ent(g, links=None, col=None, text=None, sel=None, mask=None):
        L.append('    dw %d, %d, %d, %d' % g)
        if links:
            L.append('    dw 2\n    db ' + ', '.join('0FFh' if v is None else str(v) for v in links))
        if col is not None:
            L.append(f'    dw 4, {col}')
        if text:
            L.append(f'    dw 8, 0\n    dd {text}')
        if sel and mask:
            L.append(f'    dw 14, {mask}\n    dd {sel}')
        elif sel:
            L.append(f'    dw 13\n    dd {sel}')
        L.append('    dw 0')
    ent(G_TITLE, col=0x17, text='FC_S_TTL')
    for k in range(3):
        ent((G_LEG[0] + k * (G_LEG[2] + 2),) + G_LEG[1:], col=(d['FC_C_STRONG'], d['FC_C_SIMIL'], d['FC_C_WEAK'])[k],
            text=f'FC_S_BAND + {12 * k}')
    ent(G_LVLL, col=9, text='FC_S_LVLL')
    ent(G_LVL, links=(None, None, None, club(0)), col=13, text='FC_S_LVL', sel='fc_hl', mask='0E0h')
    for k in range(4):
        y = G_ROW_Y + G_ROW_DY * k
        up, dn = (lambda f: f(k - 1) if k else d['FC_E_LVL']), (lambda f: f(k + 1) if k < 3 else d['FC_E_GO'])
        ent((G_VEN[0], y, G_VEN[1], G_ROW_H), links=(None, club(k), up(ven), dn(ven)), col=13, text='FC_S_VEN',
            sel=f'fc_v{k}')
        ent((G_CLUB[0], y, G_CLUB[1], G_ROW_H), links=(ven(k), None, up(club), dn(club)), col=d['FC_C_AUTO'],
            text=f'FC_NAME + {d["FC_NL"] * k}', sel=f'fc_c{k}')
        ent((G_BAND[0], y, G_BAND[1], G_ROW_H), col=d['FC_C_SIMIL'], text='FC_S_BAND')
        ent((G_LV[0], y, G_LV[1], G_ROW_H), col=d['FC_C_SIMIL'], text=f'FC_LV + {2 * k}')
    ent(G_MSG, text='FC_S_MSG')
    ent(G_GO, links=(None, None, club(3), None), col=0x0E, text='FC_S_GO', sel='fc_go')
    n = sum(1 for x in L if x == '    dw 0')
    assert n == d['FC_NE'] and (d['FC_E_LEG'], d['FC_E_LVLL'], d['FC_E_LVL'], E, d['FC_E_MSG'], d['FC_E_GO']) == \
        (1, 4, 5, 6, 22, 23), (n, d)
    return '\n'.join(L) + '\n'


def sites(p):
    """the game's routines and variables the page uses (the original exe's bytes; the header's current targets)"""
    import controls
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    assert r['A0'] == D0 + 32, 'D0..D7, A0..A6 contiguous'
    pk = lambda a: re.escape(struct.pack('<I', a))
    c = controls.locate(p)
    # DrawMenu: mov esi, [linAdr384k]; add esi, 65536 (x 2); mov edi, [linAdr384k]; mov ecx, 16000; rep movsd;
    # mov drawSpritesWriteOnly, 80; mov menuStatus, 0; mov A6, offset g_currentMenu
    m = list(re.finditer(rb'\x8b\x35(.{4})(?:\x81\xc6\x00\x00\x01\x00){2}\x8b\x3d\1\xb9\x80\x3e\x00\x00\xf3\xa5\xc7\x05.{4}\x50\x00\x00\x00\x66\xc7\x05.{4}\x00\x00\xc7\x05', d1, re.S))
    assert len(m) == 1, ('DrawMenu', len(m))
    drawmenu = m[0].start()
    # GetTeamPointer: push D0; push D1; push D2; push D0; call FindTeamInCache; pop D0; jz
    m = list(re.finditer(rb'\xff\x35' + pk(D0) + rb'\xff\x35' + pk(D0 + 4) + rb'\xff\x35' + pk(D0 + 8) + rb'\xff\x35'
                         + pk(D0) + rb'\xe8.{4}\x8f\x05' + pk(D0) + rb'\x0f\x84', d1, re.S))
    assert len(m) == 1, ('GetTeamPointer', len(m))
    gtp = m[0].start()
    # chooseTeamsFriendlyMenu: the one packed menu (obj2) whose initFunc and onReturn are the same obj1 routine and
    # that routine is the list builder (its last entry test: cmp word [esi+2], 37h)
    fx = {s: o for so, s, _, t, o, *_ in p.le.fixups() if so == 2 and t == 1}
    hdr = [s for s, o in fx.items() if fx.get(s + 4) == o and b'\x66\x83\x7e\x02\x37' in d1[o:o + 0x900]
           and fx.get(s - 4) != o]
    assert len(hdr) == 1, ('chooseTeamsFriendlyMenu', [hex(x) for x in hdr])
    return dict(D0=D0, show=c['SHOW_MENU'], a6=c['A6'], exitm=c['EXITM'], swospp=c['SWOSPP'], menu=c['MENU_'],
                drawmenu=drawmenu, gtp=gtp, hdr=hdr[0], ctfif=fx[hdr[0]])


def _probe(p, src, at, sym, s):
    """the glue with PROBE appended, assembled again: (code, fix, rel, labels); the call site kept for patch()"""
    import nasmcave
    site, low, sel = probe_sites(p)
    rt = p.rel_target(1, site + 1)                          # (a module before this one may have hooked the call)
    prev = rt if rt else (1, site + 5 + struct.unpack('<i', p.get(1, site + 1, 4))[0])
    here = os.path.dirname(os.path.abspath(__file__))
    blob = open(os.path.join(here, 'frdata', 'frstr_w0.bin'), 'rb').read()
    assert blob[:4] == b'FRSS' and len(blob) < PROBE_SIZE - 0x100, len(blob)
    db = ''.join('    db ' + ', '.join(str(x) for x in blob[i:i + 32]) + '\n' for i in range(0, len(blob), 32))
    src = src + nasmcave.sub(PROBE, 'FCP_BLOB_DB\n', db)
    src = f'%define FCP_BLOB_LEN {len(blob)}\n' + src
    sym.update(FCP_PREV=prev, STACKLOW=low, SELTEAM=sel, REGS=(2, s['D0']))
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    LABELS['PROBE_SITE'] = site
    return code, fix, rel, nasmcave.labels(src, at, sym)


def patch(p, lang, pick=None):
    """frchoose.c + the glue + the strings into FRCH; the club list's hook. pick = FRND's fr_pick / fr_level symbols
    (None: the interim own copy). Returns the code's end."""
    import careerworld
    import cobj
    import nasmcave
    own = pick is None
    at0, end0 = band(own)
    assert p.le.obj(4).npages * 0x1000 >= end0, 'frchoose: obj4 pages (patch.py)'
    assert not any(p.get(4, at0, end0 - at0)), 'frchoose: the FRCH band is not free'
    d, s = cdefs(), sites(p)
    str_at, bss_at = end0 - STR_BACK, end0 - BSS_BACK
    strs, sym_s = bytearray(), {}
    for nm, b in texts(lang).items():
        sym_s[nm] = (4, str_at + len(strs))
        strs.extend(b)
    assert str_at + len(strs) <= bss_at, ('frchoose strings', len(strs))
    here = os.path.dirname(os.path.abspath(__file__))
    ext = {'DREG': (2, s['D0']), 'SWOSPP': s['swospp'], 'MENU': s['menu'], 'GTP': (1, s['gtp'])}
    ext.update({k: sym_s[k] for k in ('FC_S_LVL', 'FC_S_BAND', 'FC_S_VEN', 'FC_S_MSG')})
    if not own:
        ext.update({k: pick[k] for k in ('fr_pick', 'fr_level', 'fr_given')})
    # FC_SHOW is the glue's, laid after the C: its address is known only after the link - the C calls it through a
    # fixed slot at the band's start (jmp near fc_show), as takers' band-start table
    ext['FC_SHOW'] = (4, at0)
    obj = cobj.compile_c(os.path.join(here, 'frchoose.c'),
                         ['-Oz', '-fno-zero-initialized-in-bss'] + (['-DFRC_OWN_PICK'] if own else []))
    syms, c_end, bss = cobj.link(p, obj, at0 + 16, (4, bss_at), externs=ext, limit=str_at, text_obj=4)
    assert bss <= BSS_BACK - 256, ('frchoose .bss', bss)
    # the club browser: the world's wrapper (careerworld's w_buy, as the foreign market) when a world is built
    wbuy = careerworld.LABELS.get('w_buy')
    browse = (1, wbuy) if isinstance(wbuy, int) else (1, careerworld.LABELS['sites']['chooseteams']) \
        if careerworld.LABELS.get('sites') else None
    assert browse, 'frchoose: ChooseTeamsDialog not located (careerworld.sites)'
    prev = p.target(2, s['hdr'])
    assert prev == p.target(2, s['hdr'] + 4) and prev[0] in (1, 3, 4), prev
    src = nasmcave.sub(ASM, 'FC_ENTRIES\n', menu(d))
    src = nasmcave.sub(src, 'FC_STUBS\n', ''.join(f'fc_v{k}: mov eax, {k}\n    jmp fc_hv\nfc_c{k}: mov eax, {k}\n'
                                                  f'    jmp fc_hc\n' for k in range(4)))
    src = f'%define E_GO {d["FC_E_GO"]}\n' + src
    sym = {'A6': s['a6'], 'SHOW_MENU': s['show'], 'DRAWMENU': (1, s['drawmenu']), 'EXITM': s['exitm'],
           'D2': (2, s['D0'] + 8), 'D3': (2, s['D0'] + 12), 'D4': (2, s['D0'] + 16), 'A0': (2, s['D0'] + 32),
           'A1': (2, s['D0'] + 36), 'BROWSE': browse, 'LIST_PREV': prev}
    sym.update(sym_s)
    for k in ('fc_paint', 'fc_level', 'fc_venue', 'fc_club', 'fc_picked', 'fc_list', 'FC_SEL', 'FC_TRACE', 'FC_NAME',
              'FC_K', 'FC_LV'):
        sym[k.upper()] = syms[k]
    at = (c_end + 15) & ~15
    sym['FRC_SLOT'] = (4, at0 + 8)
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    if probing():
        code, fix, rel, lab = _probe(p, src, at, sym, s)
    end = at + len(code)
    assert end <= str_at, ('frchoose: code + glue past the strings', hex(end), hex(str_at))
    assert not any(p.get(4, at, len(code)))
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.put(4, str_at, bytes(strs))
    p.put(4, at0, b'\xE9' + struct.pack('<i', lab['fc_show'] - (at0 + 5)))      # the band-start slots: jmp fc_show,
    p.put(4, at0 + 8, b'\xE9' + struct.pack('<i', syms['frc_choose'][1] - (at0 + 13)))   # +8 jmp frc_choose (the engine's
    assert syms['frc_choose'][0] == 4                   # call target: FRND links BEFORE this band - it gives the pick's
                                                        # symbols - and calls (4, FRCH_AT + 8), a fixed address)
    for o in (s['hdr'], s['hdr'] + 4):                                          # the club list's hook (chained)
        p.remove(2, o)
        p.add_ptr(2, o, 4, lab['fc_lhook'])
        assert p.target(2, o) == (4, lab['fc_lhook']) and \
            struct.unpack('<I', p.get(2, o, 4))[0] == lab['fc_lhook'], 'frchoose: the club list hook (MC 16/11)'
    if probing():
        p.branch(1, LABELS.pop('PROBE_SITE'), 0xE8, 4, lab['fc_probe'])
    LABELS.clear()
    LABELS.update(syms, **{k: (4, v) for k, v in lab.items()}, AT=(4, at0), END=(4, end0), OWN=own, FRC_CHOOSE_SLOT=(4, at0 + 8),
                  LIST_PREV=prev, HDR=(2, s['hdr']))
    print(f'exe: friendlies chooser (FRCH{" interim, own pick" if own else ""}): obj4+{at0:#x}..{end:#x} (C '
          f'{c_end - at0 - 16} B, glue + menu {len(code)}), strings +{str_at - at0:#x} ({len(strs)} B), .bss '
          f'+{bss_at - at0:#x} ({bss} B), {end0 - 256 - max(end, 0):#x}.. left {str_at - end} B before the strings; '
          f'club list hook obj2+{s["hdr"]:#x} (was {prev[0]}:{prev[1]:#x})')
    return end
