"""4.2.y T3 "mini primavera" (Davide 12/11 via Regia): a PRIMAVERA / YOUTH / JEUNES / JUGEND button in ACQUISTA
GIOCATORE, right of VIS. SQUADRA, opens a page of six boys 17-19 of the club's youth team; fire on one signs him, one
signing a month. What is drawn and how a boy is signed: tools/t3.c.

Room (MC 12/11, CONVENTIONS 23bis): obj4 page 14, swreg.T3_AT 0xD000 .. T3_END 0xE000 (patch.py raises
swe.OBJ4_PAGES to 14): t3.c's code from T3_AT, then the glue below (T3_MENU, the game's packed menu as usmenu's
US_MENU), the language's strings at STR_AT, t3.c's .bss at BSS_AT (the boys' records and the rows' texts, written on
every open). obj3 grows only by the button's menu entry (cpurefill.EXTRA, after trial's two): no trampoline; its
text and function pointers point into obj4 (fixups). No obj4 address goes into a save.

Save: engine item 'T3' (1 B, t3.c T3_ITEM): the period code of the last signing (0 = none: an older save, a new
career). The harness: t3.c's T3_* symbols (T3_STATE, T3_CODE, T3_SIGNED, T3_REC, T3_LBL), the data tag 'T3PG'.
"""
import os
import re
import struct

LABEL = {'it': 'PRIMAVERA', 'en': 'YOUTH', 'fr': 'JEUNES', 'de': 'JUGEND'}
TITLE = {'it': 'PRIMAVERA', 'en': 'YOUTH TEAM', 'fr': 'EQUIPE DES JEUNES', 'de': 'JUGENDMANNSCHAFT'}
S_OPEN = {'it': 'UN GIOVANE AL MESE: SCEGLI', 'en': 'ONE YOUNGSTER A MONTH: PICK', 'fr': 'UN JEUNE PAR MOIS: CHOISIS',
          'de': 'EIN JUGENDSPIELER PRO MONAT'}
S_DONE = {'it': "GIOVANE GIA' FIRMATO QUESTO MESE", 'en': 'YOUNGSTER SIGNED THIS MONTH',
          'fr': 'JEUNE DEJA SIGNE CE MOIS', 'de': 'DIESEN MONAT SCHON UNTERSCHRIEBEN'}
S_FULL = {'it': 'ROSA PIENA', 'en': 'SQUAD FULL', 'fr': 'EFFECTIF COMPLET', 'de': 'KADER VOLL'}
BUTTON = (203, 155, 101, 15)            # right of VIS. SQUADRA (entry 6: x 102, w 100), the mirror of trial's QUALITA'+
COLOR = 0x0E
NB = 6
ROW_X, ROW_Y, ROW_W, ROW_P = 12, 40, 280, 20
STR_AT = 0xB00                          # (offsets in the page)
BSS_AT = 0xC00
LABELS = {}
DESC = ('STATE', 'CODE', 'SIGNED', 'ITEM', 'REC', 'LBL', 'MSG', 'AGE', 'CAL', 'CAL_CUR', 'CSN', 'CNP', 'CMP', 'CT')

ASM = r"""
t3_open:                                ; the button (fire): the list, then T3_MENU (the cursor: the first boy, or ESCI)
    pushad
    push es
    push ds
    pop es
    cld
    call T3_LIST
    mov eax, 2
    cmp dword [T3_STATE], 0
    je .c
    mov eax, 2 + NB_
.c: mov [T3_MENU + 12], eax
    pop es
    popad
    mov dword [A6], T3_MENU
    jmp SHOW_MENU

t3_init:                                ; onInit (and back to it): rows hidden when closed, the links
    pushad
    push es
    push ds
    pop es
    cld
    call T3_MINIT
    pop es
    popad
    ret

T3_STUBS
t3_go:                                  ; fire on boy eax: signed (or not: the state's message), redrawn, cursor on ESCI
    pushad
    push es
    push ds
    pop es
    cld
    push eax
    call T3_SIGN
    add esp, 4
    call T3_MINIT
    pop es
    popad
    cmp dword [T3_STATE], 0
    je .k
    mov dword [D0], 2 + NB_
    call SETCUR
.k: jmp DRAWMENU

align 4
    db 'T3PG'                           ; (harness: the descriptor, linear addresses once loaded)
    dd T3_STATE, T3_CODE, T3_SIGNED, T3_ITEM, T3_REC, T3_LBL, T3_MSG, T3_AGE, CAL, CAL_CUR, CSN, CNP, CMP, CT
T3_MENU:                                ; title, the message, the six boys, ESCI
    dd t3_init, 0, 0, 2
    dw 0, 0, 304, 14
    dw 4, 17h
    dw 8, 0
    dd T3_TTL
    dw 0
    dw 0, 20, 304, 12
    dw 8, 0
    dd T3_MSG
    dw 0
T3_ROWS
    dw ESCX_, 185, 60, 15
    dw 2
    db 0FFh, 0FFh, 1 + NB_, 0FFh
    dw 4, 0Ch
    dw 8, 0
    dd EXIT_T
    dw 13
    dd EXIT_F
    dw 0
    dw -999
"""

def texts(lang):
    """(the button's label, the title, the 3 messages)"""
    return LABEL[lang], TITLE[lang], (S_OPEN[lang], S_DONE[lang], S_FULL[lang])


def sites(p):
    """the game's routines and variables t3.c uses (obj1 / obj2 offsets; the original exe's bytes)."""
    import bteam
    import sacups
    import trial
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    assert r['A0'] == D0 + 32, 'D0..D7, A0..A6 contiguous'
    s = bteam.sites(p)
    pk = lambda a: re.escape(struct.pack('<I', a))
    u32 = lambda o: struct.unpack_from('<I', d1, o)[0]
    rel = lambda o: o + 5 + struct.unpack_from('<i', d1, o + 1)[0]
    c = s['c56615']                                 # cseg_56615: call GetPlayer ... call cseg_52B6A
    assert d1[c + 36] == 0xE8 and rel(c + 36) == s['gp'], 'cseg_56615: GetPlayer first'
    m = re.match(rb'.{41}\xa1.{4}\xa3.{4}\x66\xa1.{4}\x32\xe4\x66\xa3' + pk(D0) + rb'\x66\xa1.{4}\x66\xa3' + pk(D0 + 12)
                 + rb'((?:\xff\x35.{4})*)\xe8', d1[c:c + 0x100], re.S)
    assert m, ('cseg_56615: call cseg_52B6A', d1[c:c + 0x100].hex())
    b6a = rel(c + m.end() - 1)
    m = re.match(rb'\x66\xa1' + pk(D0) + rb'\x66\xa3' + pk(r['D7']) + rb'\x66\xa1' + pk(D0 + 12) + rb'\x66\xa3'
                 + pk(D0 + 24) + rb'\xc7\x05' + pk(r['A0'] + 8) + rb'(....)\xe8(....)\xe8(....)', d1[b6a:b6a + 48], re.S)
    assert m, ('cseg_52B6A head', d1[b6a:b6a + 48].hex())
    nbuf = struct.unpack('<I', m.group(1))[0]
    d40, rand2 = rel(b6a + 34), rel(b6a + 39)
    m = re.match(rb'\x66\xc7\x05' + pk(D0 + 4) + rb'\x64\x00\x66\xa1(....)\x66\x0b\xc0\x0f\x84', d1[d40:d40 + 20], re.S)
    assert m, ('cseg_52D40 head', d1[d40:d40 + 20].hex())
    cfb = struct.unpack('<I', m.group(1))[0]
    m = re.search(rb'\x66\xf7\x25' + pk(cfb) + rb'.{0,60}?\xc7\x05' + pk(r['A0']) + rb'(....)', d1[d40:d40 + 0x80], re.S)
    assert m, 'cseg_52D40 tmdFileBuffer'
    tmd = struct.unpack('<I', m.group(1))[0]
    m = re.search(rb'\xa0(....)\xa2' + pk(D0) + rb'\x66\x81\x25' + pk(D0) + rb'\xff\x00\x75.\x80\x05(....)\x01\xa0(....)'
                  rb'.{0,40}?\x8a\x04\x06\xa2(....)', d1[rand2:rand2 + 0x60], re.S)
    assert m and m.group(2) == m.group(3), ('Rand2', d1[rand2:rand2 + 0x60].hex())
    r2 = [struct.unpack('<I', m.group(k))[0] for k in (1, 2, 4)]
    t = trial.SITES or trial.sites(p)                              # cseg_567B5's tail after the clamp: the templates, the base bits
    a0s = [struct.unpack('<I', x.group(1))[0] for x in
           re.finditer(rb'\xc7\x05' + pk(r['A0']) + rb'(....)', d1[t['clamp']:t['clamp'] + 0x100], re.S)]
    assert len(a0s) >= 3, a0s
    tpl, tpb = a0s[0], a0s[1]
    # cseg_8EA56 (the current calendar entry): mov [A0], offset calendar; mov ax, [current offset] (dplay's)
    m = list(re.finditer(rb'\xc7\x05' + pk(r['A0']) + rb'(.{4})\x66\xa1(.{4})\x66\xa3' + pk(D0) + rb'\x81\x25', d1, re.S))
    assert len(m) >= 1, 'the career calendar'
    cal, cal_cur = struct.unpack('<I', m[0].group(1))[0], struct.unpack('<I', m[0].group(2))[0]
    return dict(D0=D0, b6a=b6a, nbuf=nbuf, cfb=cfb, tmd=tmd, r2=r2, tpl=tpl, tpb=tpb, cal=cal, cal_cur=cal_cur,
                c63919=s['c63919'], setbench=s['setbench'], wage=s['wage'], compfb=s['compfb'], ct=s['ct'],
                cnp=s['cnp'], isnat=s['isnat'], csn=s['csn'])


def patch(p, lang, cr):
    """t3.c + the glue + the strings at obj4:swreg.T3_AT; the button appended to cpurefill's menu copy (cr.EXTRA, after
    trial's); the engine item 'T3'. Returns the code's end."""
    import cobj
    import engine
    import fmtpage
    import lepatch
    import nasmcave
    import swreg
    import trial
    import xbrowse
    import xtra
    from complist import px, font_odd
    assert p.le.obj(4).npages * 0x1000 >= swreg.T3_END, 't3: obj4 pages (patch.py)'
    at0 = swreg.T3_AT
    assert not any(p.get(4, at0, swreg.T3_END - at0)), 't3: obj4 page not free'
    s = sites(p)
    _, cnp, ct, cmp, sel = xtra.LABELS['SITES']
    assert (cnp, ct) == (s['cnp'], s['ct']), 'careerNumPlayers / careerTeam'
    label, title, msgs = texts(lang)
    posn = trial.POS[lang]
    assert px(label) <= BUTTON[2] - 8 and px(title) <= 300, (label, title)
    assert all(px(x) <= 300 for x in msgs), [(x, px(x)) for x in msgs]
    assert all(re.fullmatch(r"[A-Z0-9 :'+]+", x) and not font_odd(x) for x in (label, title) + msgs + posn)
    # the widest row: 2-letter role, age, 22 wide letters, +++++
    assert px('MM 19 ' + 'M' * 22 + ' +++++') <= ROW_W - 4, px('MM 19 ' + 'M' * 22 + ' +++++')
    # the strings (STR_AT): T3_POSN (8 x 4 B), the messages, the title, the button's label
    strs, sym_s = bytearray(), {}
    def put(nm, b):
        sym_s[nm] = (4, at0 + STR_AT + len(strs))
        strs.extend(b)
    put('T3_POSN', b''.join(x.encode().ljust(4, b'\0') for x in posn))
    for nm, x in zip(('T3_S_OPEN', 'T3_S_DONE', 'T3_S_FULL'), msgs):
        put(nm, x.encode() + b'\0')
    put('T3_TTL', title.encode() + b'\0')
    put('T3_BTN', label.encode() + b'\0')
    assert STR_AT + len(strs) <= BSS_AT, ('t3 strings', len(strs))
    xb = xbrowse.find(lepatch.LEPatch(bytes(p.le.data)))
    ext = {'CT': (2, s['ct']), 'CNP': (2, s['cnp']), 'CMP': (2, cmp), 'SELT': (2, sel), 'ISNAT': (2, s['isnat']),
           'COMPFB': (2, s['compfb']), 'CFB': (2, s['cfb']), 'TMD': (2, s['tmd']), 'CSN': (2, s['csn']),
           'CAL': (2, s['cal']), 'CAL_CUR': (2, s['cal_cur']), 'TPL': (2, s['tpl']), 'TPB': (2, s['tpb']),
           'R2S': (2, s['r2'][0]), 'R2I': (2, s['r2'][1]), 'R2K': (2, s['r2'][2]), 'NBUF': (2, s['nbuf']),
           'DREG': (2, s['D0']), 'C52B6A': (1, s['b6a']), 'C63919': (1, s['c63919']), 'SETBENCH': (1, s['setbench']),
           'WAGE': (1, s['wage']), 'CALC': (1, xb['calc'])}
    ext.update(sym_s)
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 't3.c'), ['-Oz'])
    syms, c_end, bss = cobj.link(p, obj, at0, (4, at0 + BSS_AT), externs=ext, limit=at0 + STR_AT, text_obj=4)
    assert BSS_AT + bss <= swreg.T3_END - at0, ('t3.c .bss past its page', bss)
    # the glue: the menu (rows: entries 2..7, ESCI 8) after the C code
    _, _, _, show, a6 = fmtpage.locate(p)
    import cpurefill
    d2 = p.le.obj_bytes(2)
    _, ents = xbrowse.menu_parse(d2, cpurefill.sites(p)['menu'])
    e7 = ents[cpurefill.NEWENT - 1][0]                  # the buy menu's ESCI: its text and function
    exit_t, exit_f = p.target(2, e7 + 22), p.target(2, e7 + 28)
    assert exit_t and exit_f and exit_f[0] == 1, (exit_t, exit_f)
    rows = []
    for k in range(NB):
        e = 2 + k
        rows += [f'    dw {ROW_X}, {ROW_Y + ROW_P * k}, {ROW_W}, 15', '    dw 2',
                 f'    db 0FFh, 0FFh, {e - 1 if k else 0xFF}, {e + 1}', '    dw 4, 0Eh', '    dw 8, 0',
                 f'    dd T3_LBL + {40 * k}', '    dw 13', f'    dd t3_s{k}', '    dw 0']
    src = nasmcave.sub(ASM, 'T3_ROWS\n', '\n'.join(rows) + '\n')
    src = nasmcave.sub(src, 'T3_STUBS\n', ''.join(f't3_s{k}: mov eax, {k}\n    jmp t3_go\n' for k in range(NB)))
    src = f'%define NB_ {NB}\n%define ESCX_ 122\n' + src
    sym = {'A6': a6, 'SHOW_MENU': (1, show), 'SETCUR': (1, xb['setcur']), 'DRAWMENU': (1, xb['drawmenu']),
           'D0': (2, s['D0']), 'EXIT_T': exit_t, 'EXIT_F': exit_f, 'T3_TTL': sym_s['T3_TTL']}
    sym.update({k: ext[k] for k in ('CAL', 'CAL_CUR', 'CSN', 'CNP', 'CMP', 'CT')})
    for k in ('t3_list', 't3_minit', 't3_sign', 'T3_STATE', 'T3_MSG', 'T3_LBL', 'T3_CODE', 'T3_SIGNED', 'T3_ITEM',
              'T3_REC', 'T3_AGE'):
        sym[k.upper()] = syms[k]
    at = (c_end + 15) & ~15
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    end = at + len(code)
    assert end <= at0 + STR_AT, ('t3: glue past its strings', hex(end))
    assert not any(p.get(4, at, len(code)))
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.put(4, at0 + STR_AT, bytes(strs))
    # the button: entry NEWENT + 1 + len(EXTRA) of cpurefill's copy; VIS. SQUADRA's right -> it
    me = cpurefill.NEWENT + 1 + len(cr.EXTRA)
    x, y, w, h = BUTTON
    e = struct.pack('<hhh', -998, 0, 0) + struct.pack('<hhhhH', x, y, w, h, 2) + bytes((6, 0xFF, 5, cpurefill.NEWENT - 1))
    e += struct.pack('<HHHH', 4, COLOR, 8, 0)
    b_at = len(e)
    e += struct.pack('<IH', 0, 13)
    f_at = len(e)
    e += struct.pack('<IH', 0, 0)
    cr.EXTRA.append({'bytes': e, 'ptrs': [(b_at, 4, sym_s['T3_BTN'][1]), (f_at, 4, lab['t3_open'])],
                     'links': {6: (1, me)}})
    engine.ITEM_AT['T3'] = syms['T3_ITEM']
    LABELS.clear()
    LABELS.update(syms, **{k: (4, v) for k, v in lab.items()}, ENTRY=me, EXT=dict(ext))
    print(f'exe: youth signings T3 ({label}, entry {me}): obj4+{at0:#x}..{end:#x} (C {c_end - at0} B, glue '
          f'{len(code)}), strings +{STR_AT:#x} ({len(strs)} B), .bss +{BSS_AT:#x} ({bss} B)')
    return end
