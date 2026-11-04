"""COPPE CONTINENTALI / CONTINENTAL CUPS (4.0.6, Gianmarco's ask; Davide GO 02/11): the other confederations' club
cups of a world career, viewed without taking part. VISUAL. COMPETIZ.'s entry 9 (World 2026-27 careers) -> a menu of
the confederations (the career club's first) -> fmtpage's page: each cup of that confederation from a new page, its
holder, every round in calendar order (ties with '>' before the club that went through, groups by final place), the
winner; a round not yet drawn, or drawn and not yet over, TO BE PLAYED. No scores: the conti matches have no goals.

ctview.c (obj3) replays the edition in progress (conti.c ct_resume: the run a load does, nothing changed) and writes
the page's text; this module builds its table (CV_TAB: texts in the exe's language, font widths, the associations'
files and confederations, cup and round names) and the native test.

    python3 tools/ctview.py --test [lang]      # the pages along conti's test seasons (career club CONTI_TEST_MANAGER)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conti        # noqa: E402

TEXTS = {   # holder, to be played, winner, group, earlier rounds (season 1), none; the menu entry
    'it': (b'DETENTORE', b'DA GIOCARE', b'VINCITORE', b'GRUPPO', b'TURNI PRECEDENTI GIOCATI PRIMA DELLA STAGIONE',
           b'NESSUNA COPPA IN CORSO', b'COPPE CONTINENTALI', b'RIEPILOGO'),
    'en': (b'HOLDER', b'TO BE PLAYED', b'WINNER', b'GROUP', b'EARLIER ROUNDS PLAYED BEFORE THE SEASON',
           b'NO CUP IN PROGRESS', b'CONTINENTAL CUPS', b'SUMMARY'),
    'fr': (b'TENANT', b'A JOUER', b'VAINQUEUR', b'GROUPE', b'TOURS PRECEDENTS JOUES AVANT LA SAISON',
           b'AUCUNE COUPE EN COURS', b'COUPES CONTINENTALES', b'RESUME'),
    'de': (b'TITELVERTEIDIGER', b'NOCH OFFEN', b'SIEGER', b'GRUPPE', b'FRUHERE RUNDEN VOR DER SAISON GESPIELT',
           b'KEIN POKAL IM GANGE', b'KONTINENTALPOKALE', b'UBERSICHT'),
}
CONF_NAMES = {'conmebol': b'CONMEBOL', 'concacaf': b'CONCACAF', 'afc': b'AFC', 'caf': b'CAF', 'ofc': b'OFC',
              'fifa': b'FIFA'}


def round_name(r, lang):
    """A format round's long name in the exe's language (rnames: its own names, else CT_NEW, else the game's)."""
    import rnames
    own = r.get('names')
    if own:
        return (own.get(lang) or own['en'])[0].upper()
    if r['key'] in rnames.CT_NEW[lang]:
        return rnames.CT_NEW[lang][r['key']][0]
    return rnames.NAMES[lang][rnames.CT_KEYS[r['key']] - rnames.N_OLD][0]


CR_N, CR_W, CR_LW = 16, 150, 30         # P3's rounds menu: buttons, their width, a label's bytes (NUL-ended)
CR_X = (0, 154)                         # its two columns (the bottom pair too): centred in the menu's 304 px frame
                                        # (screen x + 8, the title 0..304), 8 px both sides, 4 between (Davide 05/11)
CR_SCR_AT = 0x3000                      # (ctgame's scratch: its CG_END; CR_SCR_N bytes there, ctgame.CG_BSS covers them)
CR_SCR_N = 0x280                        # (labels 16 x 30, nav, title)
CR_PTRS = {}                            # its pointers into ctgame (cg_view, cg_close, the scratch): ctgame.patch sets them


def round_short(r, lang):
    """A format round's medium name (the career game list's) in the exe's language."""
    import rnames
    own = r.get('names')
    if own:
        n = own.get(lang) or own['en']
        return n[1 if len(n) > 1 else 0].upper()
    if r['key'] in rnames.CT_NEW[lang]:
        return rnames.CT_NEW[lang][r['key']][1]
    return rnames.NAMES[lang][rnames.CT_KEYS[r['key']] - rnames.N_OLD][1]


def round_long(r, lang):
    """A format round's long name (its own, else rnames'), upper case."""
    import rnames
    own = r.get('names')
    if own:
        return (own.get(lang) or own['en'])[0].upper()
    if r['key'] in rnames.CT_NEW[lang]:
        return rnames.CT_NEW[lang][r['key']][0].upper()
    return rnames.NAMES[lang][rnames.CT_KEYS[r['key']] - rnames.N_OLD][0].upper()


def round_labels(lang, cupkeys):
    """P3: the rounds' button labels '<cup short> <round>' (each cup's short name cut so that its longest round fits
    CR_W - 6 px in the menu font), pooled: (strings, u16 offsets of the cups' names [16], u16 offsets of every round's
    name in the spec's order, the cups' first round indices [16])."""
    import complist
    fmt = {(conf, c['key']): c for conf in {k for k, _ in cupkeys} for c in conti._read(conf, 'format')['cups']}
    pool, at = bytearray(), {}

    def put(t):
        if t not in at:
            assert set(t) <= complist.FONT, ('round label charset', t)
            at[t] = len(pool)
            pool.extend(t.encode('latin1') + b'\0')
        return at[t]
    co, ro, first, lo = [], [], [], []
    for k in cupkeys:
        c = fmt[k]
        cs = (c['names'].get(lang) or c['names']['en'])[1].upper()
        rns = [round_short(r, lang) for r in c['rounds']]
        fits = lambda a: all(complist.px(f'{a} {rn}') <= CR_W - 6 and len(f'{a} {rn}') < CR_LW for rn in rns)
        a = cs
        while not fits(a) and len(a) > 4:
            a = a[:-2].rstrip(' .') + '.'
        assert fits(a), ('round label over its button', lang, cs, rns)
        first.append(len(ro))
        co.append(put(a))
        ro += [put(rn) for rn in rns]
        for r, rn in zip(c['rounds'], rns):             # (VIEW WORLD's one cup: the round alone - its long name when
            ln = round_long(r, lang)                    #  it fits the button, else the medium one)
            lo.append(put(ln if complist.px(ln) <= CR_W - 6 and len(ln) < CR_LW and set(ln) <= complist.FONT else rn))
    assert len(co) <= 16 and len(ro) < 256
    return bytes(pool), struct.pack(f'<{16}H', *(co + [0] * (16 - len(co)))), struct.pack(f'<{len(ro)}H', *ro), \
        bytes(first).ljust(16, b'\0'), struct.pack(f'<{len(lo)}H', *lo)


def _spec_access(spec):
    """(nrd per cup, [(assoc, cup)] of the access entries) from conti.load()'s spec (conti.c parse())."""
    ncup, p = spec[0], 4
    nrd = []
    for _ in range(ncup):
        nrd.append(spec[p])
        p += 4 + spec[p] * conti.RB
    nacc = struct.unpack_from('<H', spec, p)[0]
    acc = [(spec[p + 2 + 4 * i], spec[p + 3 + 4 * i]) for i in range(nacc)]
    return nrd, acc


def table(lang, confs, files=None, words=None):
    """CV_TAB's bytes (ctview.c's layout) and the cups' (conf, key) in the spec's order."""
    import complist
    spec, assocs, cups = conti.load(list(confs), files, words)
    nrd, acc = _spec_access(spec)
    fmt = {}
    for conf in confs:
        for c in conti._read(conf, 'format')['cups']:
            fmt[conf, c['key']] = c
    cnum = {conf: i for i, conf in enumerate(conti.CONFS)}
    aconf = [0xFF] * len(assocs)
    for a, ci in acc:
        if a < len(assocs) and aconf[a] == 0xFF:
            aconf[a] = cnum[cups[ci][0]]
    afile = [0 if a.startswith('g:') else (files or {}).get(a, 100 + i) & 0xFF for i, a in enumerate(assocs)]
    strs, body = bytearray(), []
    pool = {}

    def s(t):                           # a string's offset (shared), filled in below
        if t not in pool:
            pool[t] = len(strs)
            strs.extend(t + b'\0')
        return pool[t]
    tx = TEXTS[lang]
    toff = [s(t) for t in tx[:6]] + [0, 0]
    for ci, (conf, key) in enumerate(cups):
        c = fmt[conf, key]
        rounds = c['rounds']
        assert len(rounds) == nrd[ci], (conf, key, len(rounds), nrd[ci])
        nm = (c['names'].get(lang) or c['names']['en'])[0].upper().encode('latin1')
        for t in [nm] + [round_name(r, lang).encode('latin1') for r in rounds]:
            assert complist.px(t.decode('latin1')) <= 298 and all(ch in complist.FONT for ch in t.decode('latin1')), (lang, t)
        body.append((cnum[conf], nrd[ci], s(nm), [s(round_name(r, lang).encode('latin1')) for r in rounds]))
    for t in tx:
        assert all(ch in complist.FONT for ch in t.decode('latin1')), (lang, t)
    head = 16 + 64 + 2 + 2 * len(assocs) + sum(4 + 2 * n for _, n, _, _ in body)
    out = bytearray(struct.pack('<8H', *[head + o for o in toff[:6]] + [0, 0]))
    out += bytes(min(255, complist.px(chr(0x20 + k))) if chr(0x20 + k) in complist.FONT else 6 for k in range(64))
    out += bytes((len(assocs), len(cups))) + bytes(afile) + bytes(aconf)
    for cf, n, nmo, ro in body:
        out += bytes((cf, n)) + struct.pack('<H', head + nmo) + b''.join(struct.pack('<H', head + o) for o in ro)
    assert len(out) == head
    CUPKEYS[:] = cups
    return bytes(out + strs), spec


CAP = 0x2900                            # obj3 room (the Integratore, 03/11; +0x100 4.0.6 B2's season 1, MC 04/11; P3's rounds menu + VIEW WORLD's cups:
                                        # OBJ3_PAGES 13, the chain's end <= LT3_AT)
CUPKEYS = []                            # table()'s cups: (conf, key) in the spec's order

ASM = r"""
cv_vis:                                 ; gplay's VISUAL. COMPETIZ. entry 9 check: ZF = 1 in a World 2026-27 career
    pushad                              ; (a league-phase world: careerworld w_lpw)
    call W_LPW
    popad
    ret

cv_go:                                  ; entry 9 (fire): the confederations menu
    mov dword [A6], CV_MENU
    jmp SHOW_MENU

cv_init:                                ; its onInit: the buttons in cv_confs' order (the career club's first)
    pushad
    push es
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    push dword CV_ORD
    movzx eax, word [CAREERTEAM]
    push eax
    call CV_CONFS
    add esp, 8
    xor ebx, ebx
.l: movzx esi, byte [CV_ORD + ebx]
    imul esi, esi, 12
    add esi, CV_CN
    imul edi, ebx, 12
    add edi, CV_LBL
    mov ecx, 12
    rep movsb
    inc ebx
    cmp ebx, 6
    jb .l
    pop es
    popad
    ret

cv_s0: mov eax, 0
    jmp cv_open
cv_s1: mov eax, 1
    jmp cv_open
cv_s2: mov eax, 2
    jmp cv_open
cv_s3: mov eax, 3
    jmp cv_open
cv_s4: mov eax, 4
    jmp cv_open
cv_s5: mov eax, 5

cv_open:                                ; button eax: that confederation (P3): its rounds menu, none (season 1) the page
    pushad
    push es
    push ds
    pop es
    cld
    movzx eax, byte [CV_ORD + eax]
    mov [CV_CUR], eax
    mov dword [CT_SPEC], SPEC
    call CT_LPF                         ; (conti's ct_lp: CT_LP, empty after a load - season 1's draws)
    call cv_week
    push dword CR_LIST
    push ecx
    push dword [CV_CUR]
    call CV_ROUNDS
    add esp, 12
    mov [CR_CNT], eax
    pop es
    popad
    cmp dword [CR_CNT], 0
    je cv_page
    mov dword [A6], CR_MENU
    jmp SHOW_MENU

cw_title:                               ; edi = a title: VIEW WORLD's one cup (CV_ONLY) -> its name copied, CF = 0;
    cmp dword [CV_ONLY_], 0FFh          ; every cup -> CF = 1 (the caller's 'COPPE CONTINENTALI - conf')
    stc
    je .r
    mov eax, [CV_ONLY_]
    mov esi, [CW_NAME + 4 * eax]
.c: lodsb
    stosb
    test al, al
    jnz .c
    clc
.r: ret

cw_after:                               ; careerworld w_choose (VIEW WORLD's picker returned): one of our cup buttons
    pushad                              ; (selectedContest = a CW_MARK) -> that cup's rounds menu (no round yet: its
    cmp word [CTRES], 0                 ; page part), chooseTeamsResult cleared (ViewWorldMenu then goes out)
    je .x
    mov eax, [SELCONT]
    xor ebx, ebx
.f: cmp ebx, CW_N_
    jae .x
    cmp eax, [CW_MARK + 4 * ebx]
    je .h
    inc ebx
    jmp .f
.h: mov word [CTRES], 0
    mov [CV_ONLY_], ebx
    movzx eax, byte [CW_CONF + ebx]
    mov [CV_CUR], eax
    push es
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    call CT_LPF
    call cv_week
    push dword CR_LIST
    push ecx
    push dword [CV_CUR]
    call CV_ROUNDS
    add esp, 12
    mov [CR_CNT], eax
    pop es
    test eax, eax
    jnz .m
    call cv_page
    jmp .e
.m: mov dword [A6], CR_MENU
    call SHOW_MENU
.e: mov dword [CV_ONLY_], 0FFh
.x: popad
    ret

cw_on:                                  ; VIEW WORLD's picker: each CW_SW slot holding its plain list -> the list with
    pushad                              ; the cup buttons (a continent's competitionsTable entry; COMP254 / COMP99 =
    mov esi, CW_SW                      ; the world's MONDO table, careerworld W_SWAP); cw_off puts the plain ones back
    mov ecx, CW_SW_N
.l: mov edi, [esi]
    mov eax, [esi + 4]
    cmp [edi], eax
    jne .n
    mov eax, [esi + 8]
    mov [edi], eax
.n: add esi, 12
    loop .l
    popad
    ret

cw_off:
    pushad
    mov esi, CW_SW
    mov ecx, CW_SW_N
.l: mov edi, [esi]
    mov eax, [esi + 8]
    cmp [edi], eax
    jne .n
    mov eax, [esi + 4]
    mov [edi], eax
.n: add esi, 12
    loop .l
    popad
    ret

cv_week:                                ; ecx = the career calendar's week (as gplay's O_WEEK)
    movzx ecx, word [CAL_CUR]
    movzx ecx, byte [CAL + ecx + 1]
    ret

cv_page:                                ; CV_CUR's cups on fmtpage's page (the summary: version A)
    pushad
    push es
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    call CT_LPF
    call cv_week
    push dword TXTMAX_
    push dword TXT
    push ecx
    push dword [CV_CUR]
    call CV_TEXT
    add esp, 16
    mov edi, TITLE                      ; 'COPPE CONTINENTALI - CONMEBOL'
    call cw_title
    jnc .t3
    mov esi, CV_LABEL
.t: lodsb
    test al, al
    jz .t1
    stosb
    jmp .t
.t1:mov eax, 202D20h
    stosd
    dec edi
    imul esi, [CV_CUR], 12
    add esi, CV_CN
.t2:lodsb
    stosb
    test al, al
    jnz .t2
.t3:mov byte [FOUND], 1
    mov dword [PAGE], 0
    call FP_FILL
    pop es
    popad
    mov dword [A6], FMTMENU
    jmp SHOW_MENU

cr_init:                                ; the rounds menu's onInit: title, labels, links; the unused buttons hidden
    pushad
    push es
    push ds
    pop es
    cld
    mov edi, CR_TITLE                   ; 'COPPE CONTINENTALI - CONMEBOL'
    call cw_title                       ; (VIEW WORLD's one cup: its name)
    jnc .t3
    mov esi, CV_LABEL
.t: lodsb
    test al, al
    jz .t1
    stosb
    jmp .t
.t1:mov eax, 202D20h
    stosd
    dec edi
    imul esi, [CV_CUR], 12
    add esi, CV_CN
.t2:lodsb
    stosb
    test al, al
    jnz .t2
.t3:xor ebx, ebx
.l: cmp ebx, [CR_CNT]
    jae .l1
    movzx eax, byte [CR_LIST + ebx]
    mov edx, eax
    shr edx, 4
    and eax, 15
    movzx ecx, byte [CR_FIRST + edx]
    add ecx, eax                        ; (ecx: the round's label - lodsb below takes al)
    imul edi, ebx, CR_LW_
    add edi, CR_LBL
    movzx esi, word [CR_CUPS + 2 * edx]
    add esi, CR_STR
    cmp dword [CV_ONLY_], 0FFh          ; (one cup: the round's name alone, CR_RNDL)
    jne .c3
.c: lodsb
    test al, al
    jz .c1
    stosb
    jmp .c
.c1:mov al, ' '
    stosb
    movzx esi, word [CR_RNDS + 2 * ecx]
    jmp .c4
.c3:movzx esi, word [CR_RNDL + 2 * ecx]
.c4:
    add esi, CR_STR
.r: lodsb
    stosb
    test al, al
    jnz .r
    inc ebx
    jmp .l
.l1:push dword CR_NAV
    push dword [CR_CNT]
    call CR_LAYOUT
    add esp, 8
    mov ebx, 1
.e: mov [D0R], ebx                      ; entry ebx (CalcMenuEntryAddress -> A0)
    pushad
    call VC_CALC
    popad
    mov edi, [A0R]
    cmp ebx, CR_N_
    ja .e2
    lea eax, [ebx - 1]
    cmp eax, [CR_CNT]
    jb .e1
    mov word [edi + 4], 1
    jmp .e3
.e1:mov eax, [CR_NAV + 4 * ebx - 4]
    mov [edi + 8], eax
    jmp .e3
.e2:mov al, [CR_NAV + 4 * CR_N_ + ebx - CR_N_ - 1]
    mov [edi + 0Ah], al
.e3:inc ebx
    cmp ebx, CR_N_ + 2
    jbe .e
    pop es
    popad
    ret

cr_sum:                                 ; RIEPILOGO: the summary page, then the rounds menu's labels and links again
    call cv_page
    jmp cr_init

CR_STUBS
cr_go:                                  ; round button eax: the game's own screen of that round (ctgame cg_view), the
    pushad                              ; career club's group stage in progress the real one (slot 3); a round the
    push es                             ; screens can't show (cg_view 0) -> the summary page
    push ds
    pop es
    cld
    movzx eax, byte [CR_LIST + eax]
    mov ebx, eax
    shr ebx, 4
    and eax, 15
    mov [CR_C], ebx
    mov [CR_R], eax
    cmp byte [CT_SEG_ + 2], 0FFh
    je .b
    cmp [CT_SEG_], bl
    jne .b
    cmp [CT_SEG_ + 1], al
    jne .b
    test byte [CT_SEG_ + 2], 1
    jz .b
    mov dword [A0R], SLOT3
    call VC_VIEW
    jmp .x
.b: call cv_week
    push ecx
    push dword -1
    push dword [CR_R]
    push dword [CR_C]
    call [CR_VIEW]
    add esp, 16
    test eax, eax
    jz .t
    mov eax, [CR_SCR]
    mov [A0R], eax
    call VC_VIEW
    call [CR_CLOSE]
.x: call cr_init                        ; (the menu as it came back: its labels and links again)
    pop es
    popad
    ret
.t: pop es
    popad
    call cv_page                        ; (the summary page, then the menu as it came back: labels and links again)
    jmp cr_init

align 4
CR_VIEW: dd 0                           ; (ctgame.patch: cg_view, cg_close, its scratch)
CR_CLOSE: dd 0
CR_SCR: dd 0
CR_CNT: dd 0
CR_C: dd 0
CR_R: dd 0
CR_LIST: times 16 db 0
align 4
CW_MARK: CW_MARK_DD
CW_NAME: CW_NAME_DD
CW_CONF: CW_CONF_DB
align 4
CW_SW: CW_SW_DD
CR_FIRST: CR_FIRST_DB
CR_CUPS: CR_CUPS_DB
CR_RNDS: CR_RNDS_DB
CR_RNDL: CR_RNDL_DB
CR_STR: CR_STR_DB
align 4
CR_MENU:                                ; title, the round buttons (two columns), RIEPILOGO, ESCI
    dd cr_init, 0, 0, 1
    dw 0, 0, 304, 14
    dw 4, 17h
    dw 8, 0
    dd CR_TITLE
    dw 0
CR_BUTTONS
    dw -999

align 4
CV_TRACE: db 'CVTRPTR', 0             ; (the harness: CT_SEG, CT_ED, CT_OUT, the calendar, its entry)
    dd CT_SEG_, CT_ED_, CT_OUT_, CAL, CAL_CUR
CV_CUR: dd 0
CV_ORD: db 0, 1, 2, 3, 4, 5, 0, 0
CV_LABEL: CV_LABEL_DB
CV_CN: CV_CN_DB
CV_LBL: times 72 db 0
align 4
CV_MENU:                                ; title, the 6 confederations, ESCI (fmtpage's packed menu format)
    dd cv_init, 0, 0, 1
    dw 0, 0, 304, 14
    dw 4, 17h
    dw 8, 0
    dd CV_LABEL
    dw 0
CV_BUTTONS
    dw 72, 180, 160, 15
    dw 2
    db 0FFh, 0FFh, 6, 0FFh
    dw 4, 0Ch
    dw 8, 0
    dd EXIT_T
    dw 13
    dd EXIT_F
    dw 0
    dw -999
"""


def patch(p, at, lang, scr_at):
    """The view at obj3:at (the end of the obj3 chain): CV_TAB, ctview.c, the glue; gplay's entry 9 pointed at it.
    Returns the end (asserted within CAP)."""
    import careerworld
    import cobj
    import complist
    import fmtpage
    import gplay
    import nasmcave
    cl, wn = conti.LABELS, fmtpage.WN
    assert cl.get('syms') and wn and 'CV9_VIS' in gplay.LABELS, 'ctview: conti, fmtpage VINCITORI and gplay vc5 first'
    files, words = conti._world_maps(conti.ready())
    tab, _ = table(lang, conti.ready(), files, words)
    t0 = at = (at + 15) & ~15
    p.put(3, at, tab)
    tab_at, at = at, (at + len(tab) + 15) & ~15
    cs = cl['syms']
    ext = {k: cs[k] for k in ('CT_SPEC', 'CT_LP', 'CT_IN', 'CT_ST', 'CT_OUT', 'CT_ED', 'CT_SEG', 'ct_resume')}
    ext['CV_TAB'] = (3, tab_at)
    import guests
    import mkseason
    stem = mkseason.ns_stem(guests.world()) if guests.world() is not None else 'team'   # (4.0.6: a release's world
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctview.c'),   # 2026-27 is TMW5.nnn)
                         ['-fno-zero-initialized-in-bss', f'-DCV_STEM="{stem}"'])
    c0 = at
    syms, at, bss = cobj.link(p, obj, at, (3, 0), externs=ext, text_obj=3)
    c1 = at
    assert bss == 0, ('ctview.c: no .bss (statics in its data)', bss)
    at = (at + 15) & ~15
    order = [k for k in conti.CONFS]
    assert len(order) == 6, order
    at, cw = world_cups(p, at)                          # (P3: VIEW WORLD's green cup buttons)
    T = TEXTS[lang]
    assert complist.px(T[6].decode('latin1')) <= complist.VC_PX, ('ctview menu entry over VISUAL. COMPETIZ.', T[6])
    btn = []
    for i in range(6):
        nav = f'0FFh, 0FFh, {i if i else 0xFF}, {i + 2 if i < 5 else 7}'
        btn += [f'    dw 72, {40 + 22 * i}, 160, 15', '    dw 2', f'    db {nav}', '    dw 4, 0Eh', '    dw 8, 0',
                f'    dd CV_LBL + {12 * i}', '    dw 13', f'    dd cv_s{i}', '    dw 0']
    src = nasmcave.sub(ASM, 'CV_BUTTONS\n', '\n'.join(btn) + '\n')
    pool, cups_o, rnds_o, first, rndl_o = round_labels(lang, CUPKEYS)
    h = CR_N // 2
    rb = []
    for k in range(CR_N):
        rb += [f'    dw {CR_X[k // h]}, {22 + 18 * (k % h)}, {CR_W}, 15', '    dw 2', '    db 0FFh, 0FFh, 0FFh, 0FFh',
               '    dw 4, 0Eh', '    dw 8, 0', f'    dd CR_LBL + {CR_LW * k}', '    dw 13', f'    dd cr_s{k}', '    dw 0']
    rb += [f'    dw {CR_X[0]}, 172, {CR_W}, 15', '    dw 2', f'    db 0FFh, {CR_N + 2}, 0FFh, 0FFh', '    dw 4, 0Eh', '    dw 8, 0',
           '    dd CR_SUMT', '    dw 13', '    dd cr_sum', '    dw 0',
           f'    dw {CR_X[1]}, 172, {CR_W}, 15', '    dw 2', f'    db {CR_N + 1}, 0FFh, 0FFh, 0FFh', '    dw 4, 0Ch', '    dw 8, 0',
           '    dd EXIT_T', '    dw 13', '    dd EXIT_F', '    dw 0']
    src = nasmcave.sub(src, 'CR_BUTTONS\n', '\n'.join(rb) + '\n')
    src = nasmcave.sub(src, 'CR_STUBS\n', ''.join(f'cr_s{k}: mov eax, {k}\n    jmp cr_go\n' for k in range(CR_N))
                       + 'CR_SUMT: db ' + ', '.join(str(b) for b in T[7] + b'\0') + '\n')
    src = nasmcave.sub(src, 'CR_FIRST_DB', 'db ' + ', '.join(str(b) for b in first))
    src = nasmcave.sub(src, 'CW_MARK_DD', 'dd ' + ', '.join(f'CW_M{c}' for c in range(len(cw['marks']))))
    src = nasmcave.sub(src, 'CW_NAME_DD', 'dd ' + ', '.join(f'CW_S{c}' for c in range(len(cw['marks']))))
    src = nasmcave.sub(src, 'CW_CONF_DB', 'db ' + ', '.join(str(x) for x in cw['conf']))
    assert cw['swaps'], 'VIEW WORLD: no list to swap'
    src = nasmcave.sub(src, 'CW_SW_DD', 'dd ' + ', '.join(f'CW_W{k}{x}' for k in range(len(cw['swaps'])) for x in 'SOA'))
    for k, b in (('CR_CUPS_DB', cups_o), ('CR_RNDS_DB', rnds_o), ('CR_RNDL_DB', rndl_o), ('CR_STR_DB', pool)):
        src = nasmcave.sub(src, k, 'db ' + ', '.join(str(x) for x in b))
    assert complist.px(T[7].decode('latin1')) <= CR_W - 6, ('summary button', T[7])
    src = nasmcave.sub(src, 'CV_LABEL_DB', 'db ' + ', '.join(str(b) for b in T[6] + b'\0'))
    src = nasmcave.sub(src, 'CV_CN_DB', 'db ' + ', '.join(str(b) for k in order
                                                          for b in CONF_NAMES[k].ljust(12, b'\0')))
    ws = wn['sym']
    sym = {k: ws[k] for k in ('A6', 'SHOW_MENU', 'TITLE', 'PAGE', 'FOUND', 'TXT', 'TXTMAX_', 'FMTMENU')}
    sym.update(FP_FILL=(1, wn['fill']), EXIT_T=wn['exit'][0], EXIT_F=wn['exit'][1], CT_SPEC=cs['CT_SPEC'],
               SPEC=cl['SPEC'], CT_LPF=(1, cl['ct_lp']), CV_CONFS=syms['cv_confs'], CV_TEXT=syms['cv_text'],
               CAREERTEAM=gplay.LABELS['CAREERTEAM'], CAL=gplay.LABELS['CAL'], CAL_CUR=gplay.LABELS['CAL_CUR'],
               W_LPW=(1, careerworld.LABELS['w_lpw']), CT_SEG_=cs['CT_SEG'], CT_ED_=cs['CT_ED'],
               CT_OUT_=cs['CT_OUT'], CV_ROUNDS=syms['cv_rounds'], CR_LAYOUT=syms['cr_layout'], VC_CALC=gplay.LABELS['VC_CALC'],
               VC_VIEW=gplay.LABELS['VC_VIEW'], SLOT3=__import__('uefaq').SYMS['SLOT3'], D0R=__import__('uefaq').SYMS['D0R'],
               A0R=__import__('uefaq').SYMS['A0R'], CR_N_=(0, CR_N), CR_LW_=(0, CR_LW))
    sym.update({f'CW_M{c}': (3, m) for c, m in enumerate(cw['marks'])})
    sym.update({f'CW_W{k}{x}': v for k, w in enumerate(cw['swaps']) for x, v in zip('SOA', w)})
    sym.update(CW_SW_N=(0, len(cw['swaps'])))
    sym.update({f'CW_S{c}': nm for c, nm in enumerate(cw['names'])})
    sym.update(CW_N_=(0, len(cw['marks'])), CV_ONLY_=syms['CV_ONLY'], CTRES=careerworld.LABELS['sites']['ctres'],
               SELCONT=careerworld.LABELS['sites']['selcont'])
    assert CR_N * CR_LW + 4 * CR_N + 4 + 48 <= CR_SCR_N, 'rounds menu buffers over CR_SCR_N'   # (48: the title)
    scr = scr_at + CR_SCR_AT                            # (the menu's buffers: ctgame's zero-fill scratch, past its own)
    sym.update(CR_LBL=(3, scr), CR_NAV=(3, scr + CR_N * CR_LW), CR_TITLE=(3, scr + CR_N * CR_LW + 4 * CR_N + 4))
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    end = at + len(code)
    assert end - t0 <= CAP, ('ctview over its obj3 room', hex(end - t0), hex(CAP))
    gl = gplay.LABELS                                   # gplay's entry 9: its check, on-select and text -> obj3
    p.add_ptr(1, gl['CV9_VIS'], 3, lab['cv_vis'])
    p.add_ptr(1, gl['CV9_GO'], 3, lab['cv_go'])
    p.add_ptr(1, careerworld.LABELS['WV_AFTER'], 3, lab['cw_after'])   # (careerworld w_choose -> cw_after, the
    p.add_ptr(1, careerworld.LABELS['WV_ON'], 3, lab['cw_on'])         #  cup-button lists in / out around its picker)
    p.add_ptr(1, careerworld.LABELS['WV_OFF'], 3, lab['cw_off'])
    CR_PTRS.clear()
    CR_PTRS.update(view=lab['CR_VIEW'], close=lab['CR_CLOSE'], scr=lab['CR_SCR'])
    p.retarget(1, gl['VC9_TXTP'], 3, lab['CV_LABEL'])
    p.put(1, gl['VC9_TXTP'], struct.pack('<I', lab['CV_LABEL']))
    print(f'exe: COPPE CONTINENTALI view (ctview): obj3+{t0:#x}..{end:#x} ({end - t0} B of {CAP}: table {len(tab)}, '
          f'C {c1 - c0}, glue {len(code)})')
    return end


CONT_CONF = {'south_america': 'conmebol', 'north_america': 'concacaf', 'asia': 'afc', 'africa': 'caf',
             'oceania': 'ofc'}                  # (mkseason's continents -> their confederation; FIFA: the world's MONDO)
CW = {}                                         # world_cups' result (the harness: the cup buttons it put where)


def world_cups(p, at):
    """4.0.6 P3 (Davide, 03/11): VIEW WORLD's confederation screens as the MONDO one - the confederation's cups as
    green buttons above its nations (EUROPA: the world's UEFA cups, moved from MONDO - Davide 03/11), FIFA's on MONDO. A marker contest per cup at obj3:at (conti's ties
    contest header with the cup's names: the picker draws its name; cw_after knows it by its address); each continent
    list of a world (mkseason WCONT_IDS, top level) with cups: a new table [markers, -1, its countries] in obj3; the
    world record's MONDO table (careerworld W<n>_CONT): FIFA's marker + the continents. The game's pointers stay as they are (the
    new career's club picker, the foreign market: the plain lists): cw_on / cw_off swap them in only around VIEW
    WORLD's picker. Returns (at, {'marks': obj3 offsets per cup, 'names': (obj, off) of each cup's name, 'conf': its
    CONFS index, 'swaps': [(slot, plain list, list with the buttons)] as (obj, off)})."""
    import careerworld
    import mkseason
    import sacups
    assert len(conti.NAMES) == len(CUPKEYS) and conti.TIE[0], (len(conti.NAMES), len(CUPKEYS))
    tie = bytearray(p.get(1, conti.TIE[0], 28))
    assert tie[5] + 5 == 16, tie[:8].hex()
    marks, names, conf, swaps = [], [], [], []
    for c, (cf, key) in enumerate(CUPKEYS):
        b = bytearray(tie)
        struct.pack_into('<II', b, 16, conti.NAMES[c], conti.SNAMES[c])
        p.put(3, at, bytes(b))
        marks.append(at)
        names.append((2, sacups.STR_BASE + conti.NAMES[c]))
        conf.append(conti.CONFS.index(cf))
        at += 28
    comp = sacups.COMP_TABLE[0]
    CW.clear()

    def table(cups, head, tail):                # [head pointers, markers, -1, tail bytes]
        nonlocal at
        t = at
        for i, tg in enumerate(head + [(3, marks[c]) for c in cups]):
            p.add_ptr(3, at + 4 * i, *tg)
        at += 4 * (len(head) + len(cups))
        p.put(3, at, b'\xff' * 4 + tail)
        at = (at + 4 + len(tail) + 3) & ~3
        return t
    for n, ids in sorted(mkseason.WCONT_IDS.items()):
        wc = careerworld.LABELS.get(f'W{n}_CONT')
        uefa = []                                       # (Davide 03/11: the world's UEFA cups - MONDO's head in the
        while wc is not None and p.get(1, wc + 4 * len(uefa), 4) != b'\xff' * 4:   # record - on EUROPA's screen)
            uefa.append(p.target(1, wc + 4 * len(uefa)))
        for lid, _, top in ids:
            key = mkseason.WCONT_KEY.get(lid)
            k = CONT_CONF.get(key)
            cups = [c for c, (cf, _) in enumerate(CUPKEYS) if cf == k]
            head = uefa if key == 'europe' else []
            if not top or not (cups or head):
                continue
            o = p.target(2, comp + 4 * lid)
            old = p.get(*o, 4 + 256)
            assert old[:4] == b'\xff' * 4, (lid, old[:8].hex())
            t = table(cups, head, old[4:old.index(0xFF, 4) + 1])
            swaps.append(((2, comp + 4 * lid), o, (3, t)))
            CW.setdefault(n, {})[lid] = [CUPKEYS[c][1] for c in cups] + (['uefa'] * len(head))
        fifa = [c for c, (cf, _) in enumerate(CUPKEYS) if cf == 'fifa']
        if wc is None or not fifa:
            continue
        old = p.get(1, wc + 4 * len(uefa), 4 + 64)
        t = table(fifa, [], old[4:old.index(0xFF, 4) + 1])
        wp = careerworld.LABELS[f'W{n}_CONTP']          # (the record's MONDO pointer: W_SWAP puts it in both)
        assert p.target(1, wp) == (1, wc), (n, p.target(1, wp))
        swaps += [((2, comp + 4 * k), (1, wc), (3, t)) for k in (254, careerworld.WCONT)]
        CW.setdefault(n, {})['MONDO'] = [CUPKEYS[c][1] for c in fifa]
    print(f'exe: VIEW WORLD cup buttons: {len(marks)} cups, {CW}')
    return at, {'marks': marks, 'names': names, 'conf': conf, 'swaps': swaps}


def test(lang='it', confs=('conmebol',)):
    import ctypes
    L = conti._native(('ctview.c',))
    tab, _ = table(lang, confs)
    ctypes.memmove(ctypes.addressof(ctypes.c_ubyte.in_dll(L, 'CV_TAB')), tab, len(tab))
    names = {}
    NAMEF = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_uint32)
    keep = []

    def nm(w):
        b = ctypes.create_string_buffer(names.get(w, f'C{w:04X}').upper().encode()[:17])
        keep.append(b)
        return ctypes.addressof(b)
    cb = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)(nm)
    ctypes.c_void_p.in_dll(L, 'cv_native_name').value = ctypes.cast(cb, ctypes.c_void_p).value
    SEG = (ctypes.c_ubyte * 72).in_dll(L, 'CT_SEG')
    OUTB = (ctypes.c_ubyte * (ctypes.c_uint32 * 3).in_dll(L, 'CT_LAYOUT')[2]).in_dll(L, 'CT_OUT')
    buf = ctypes.create_string_buffer(0x2000)
    L.cv_text.restype = ctypes.c_uint32
    weeks = [int(w) for w in os.environ.get('CTVIEW_WEEKS', '64,80,104,140').split(',')]

    def hook(L2, nms, step):
        names.update(nms)
        for w in weeks:
            snap = bytes(SEG), bytes(OUTB)
            n = L.cv_text(conti.CONFS.index(confs[0]), w, buf, len(buf))
            assert (bytes(SEG), bytes(OUTB)) == snap, f'the view changed the state ({step}, week {w})'
            assert n < len(buf) - 1, 'page text full'
            if os.environ.get('CTVIEW_SHOW') in (step, 'all') or (w == weeks[-1] and step.endswith('start')):
                print(f'=== {step}, week {w} ({n} B)')
                for pg in buf.raw[:n].decode('latin1').split('\f'):
                    print('\n'.join('  | ' + x for x in pg.split('\n')))
                    print('  +' + '-' * 40)
    conti.test(confs, seasons=int(os.environ.get('CTVIEW_SEASONS', 2)), L=L, hook=hook)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        test(*(sys.argv[2:3] or ['it']), confs=tuple(sys.argv[3:]) or ('conmebol',))
