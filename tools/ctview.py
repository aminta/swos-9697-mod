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
           b'NESSUNA COPPA IN CORSO', b'COPPE CONTINENTALI'),
    'en': (b'HOLDER', b'TO BE PLAYED', b'WINNER', b'GROUP', b'EARLIER ROUNDS PLAYED BEFORE THE SEASON',
           b'NO CUP IN PROGRESS', b'CONTINENTAL CUPS'),
    'fr': (b'TENANT', b'A JOUER', b'VAINQUEUR', b'GROUPE', b'TOURS PRECEDENTS JOUES AVANT LA SAISON',
           b'AUCUNE COUPE EN COURS', b'COUPES CONTINENTALES'),
    'de': (b'TITELVERTEIDIGER', b'NOCH OFFEN', b'SIEGER', b'GRUPPE', b'FRUHERE RUNDEN VOR DER SAISON GESPIELT',
           b'KEIN POKAL IM GANGE', b'KONTINENTALPOKALE'),
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
    """CV_TAB's bytes (ctview.c's layout) and the confederations' order numbers."""
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
    return bytes(out + strs), spec


CAP = 0x1800                            # obj3 room (the Integratore, 03/11)

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

cv_open:                                ; button eax: that confederation's cups on fmtpage's page
    pushad
    push es
    push ds
    pop es
    cld
    movzx eax, byte [CV_ORD + eax]
    mov [CV_CUR], eax
    mov dword [CT_SPEC], SPEC
    call CT_LPF                         ; (conti's ct_lp: CT_LP, empty after a load - season 1's draws)
    movzx ecx, word [CAL_CUR]           ; the career calendar's week (as gplay's O_WEEK)
    movzx ecx, byte [CAL + ecx + 1]
    push dword TXTMAX_
    push dword TXT
    push ecx
    push dword [CV_CUR]
    call CV_TEXT
    add esp, 16
    mov edi, TITLE                      ; 'COPPE CONTINENTALI - CONMEBOL'
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
    mov byte [FOUND], 1
    mov dword [PAGE], 0
    call FP_FILL
    pop es
    popad
    mov dword [A6], FMTMENU
    jmp SHOW_MENU

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


def patch(p, at, lang):
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
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctview.c'),
                         ['-fno-zero-initialized-in-bss'])
    c0 = at
    syms, at, bss = cobj.link(p, obj, at, (3, 0), externs=ext, text_obj=3)
    c1 = at
    assert bss == 0, ('ctview.c: no .bss (statics in its data)', bss)
    at = (at + 15) & ~15
    order = [k for k in conti.CONFS]
    assert len(order) == 6, order
    T = TEXTS[lang]
    assert complist.px(T[6].decode('latin1')) <= complist.VC_PX, ('ctview menu entry over VISUAL. COMPETIZ.', T[6])
    btn = []
    for i in range(6):
        nav = f'0FFh, 0FFh, {i if i else 0xFF}, {i + 2 if i < 5 else 7}'
        btn += [f'    dw 72, {40 + 22 * i}, 160, 15', '    dw 2', f'    db {nav}', '    dw 4, 0Eh', '    dw 8, 0',
                f'    dd CV_LBL + {12 * i}', '    dw 13', f'    dd cv_s{i}', '    dw 0']
    src = nasmcave.sub(ASM, 'CV_BUTTONS\n', '\n'.join(btn) + '\n')
    src = nasmcave.sub(src, 'CV_LABEL_DB', 'db ' + ', '.join(str(b) for b in T[6] + b'\0'))
    src = nasmcave.sub(src, 'CV_CN_DB', 'db ' + ', '.join(str(b) for k in order
                                                          for b in CONF_NAMES[k].ljust(12, b'\0')))
    ws = wn['sym']
    sym = {k: ws[k] for k in ('A6', 'SHOW_MENU', 'TITLE', 'PAGE', 'FOUND', 'TXT', 'TXTMAX_', 'FMTMENU')}
    sym.update(FP_FILL=(1, wn['fill']), EXIT_T=wn['exit'][0], EXIT_F=wn['exit'][1], CT_SPEC=cs['CT_SPEC'],
               SPEC=cl['SPEC'], CT_LPF=(1, cl['ct_lp']), CV_CONFS=syms['cv_confs'], CV_TEXT=syms['cv_text'],
               CAREERTEAM=gplay.LABELS['CAREERTEAM'], CAL=gplay.LABELS['CAL'], CAL_CUR=gplay.LABELS['CAL_CUR'],
               W_LPW=(1, careerworld.LABELS['w_lpw']), CT_SEG_=cs['CT_SEG'], CT_ED_=cs['CT_ED'],
               CT_OUT_=cs['CT_OUT'])
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
    p.retarget(1, gl['VC9_TXTP'], 3, lab['CV_LABEL'])
    p.put(1, gl['VC9_TXTP'], struct.pack('<I', lab['CV_LABEL']))
    print(f'exe: COPPE CONTINENTALI view (ctview): obj3+{t0:#x}..{end:#x} ({end - t0} B of {CAP}: table {len(tab)}, '
          f'C {c1 - c0}, glue {len(code)})')
    return end


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
