"""4.2 GAMEPLAY = ORIGINALE / PERSONALIZZATO (Davide 15/11; design internal/handoff/gameplay-menu-design.md, MC). Host-side part P1:
the row table, the strings (4 languages, font-safe) and the save item's constants. No exe code yet (the page code goes into
the GAMEPLAY reserve of obj4pack, 0x400, after Shaved's commit is in 42-int).

OPTIONS gets ONE row GAMEPLAY (ORIGINALE / PERSONALIZZATO; FIRE on PERSONALIZZATO opens the page). The page holds the mod's
match-play switches as a TABLE of rows, each with a 'present' flag: a row that is not in yet (TIRATORI, RUOLI: after the
freeze) is simply absent - no empty line, no placeholder text; adding one later = one table entry + its module's mask hook,
inside the reserve (asserted: room for 2 more rows).
ORIGINALE is a MASK applied at kick-off (every switch acts as its original value; the sub-values are kept). GM_W, the engine
item 'GM' (1 B): 0 = PERSONALIZZATO (default, today's defaults), 1 = ORIGINALE; a save without GM loads PERSONALIZZATO.
SWOS++: the row is hidden and everything original (as every other row of ours)."""
import re
import struct

import cpucards
import difficulty
import gkinj
import nasmcave
import setpieces

GM_TAG = 'GM'
GM_SIZE = 5                             # engine item 'GM': GM_W (a word: the OPTIONS row's string table; 0 = PERSONALIZZATO, default,
                                        # 1 = ORIGINALE) + 3 bytes parking the user's CPU cards / injuries / keeper injuries
                                        # while ORIGINALE (the live words are then 1 = OFF = the original game)
GM_PERSONALIZZATO, GM_ORIGINALE = 0, 1

LABEL = {'it': 'GAMEPLAY', 'en': 'GAMEPLAY', 'fr': 'GAMEPLAY', 'de': 'SPIELWEISE'}
VALUES = {'it': ('PERSONALIZZATO', 'ORIGINALE'), 'en': ('CUSTOM', 'ORIGINAL'),          # (value 0 first = GM_W's 0)
          'fr': ('PERSONNALISE', 'ORIGINAL'), 'de': ('INDIVIDUELL', 'ORIGINAL')}
TITLE = {'it': 'GAMEPLAY PERSONALIZZATO', 'en': 'CUSTOM GAMEPLAY', 'fr': 'GAMEPLAY PERSONNALISE', 'de': 'INDIVIDUELLE SPIELWEISE'}
YESNO = {'it': ('SI', 'NO'), 'en': ('YES', 'NO'), 'fr': ('OUI', 'NON'), 'de': ('JA', 'NEIN')}     # (the CPU rows: 0 = SI, today's default)
PRACTICE = {'it': 'GAMEPLAY: ORIGINALE', 'en': 'GAMEPLAY: ORIGINAL', 'fr': 'GAMEPLAY: ORIGINAL', 'de': 'SPIELWEISE: ORIGINAL'}
LEG = {'it': 'SIN/DES CAMBIA FUOCO: AVANTI', 'en': 'LEFT/RIGHT CHANGE FIRE: NEXT',
       'fr': 'GAUCHE/DROITE CHANGE FEU: SUITE', 'de': 'LINKS/RECHTS AENDERT FEUER: WEITER'}
# rows not in yet (after the freeze: takers, Marco's traits) - their texts are ready, the 'present' flag off
TAKERS = {'it': 'TIRATORI', 'en': 'TAKERS', 'fr': 'TIREURS', 'de': 'SCHUETZEN'}
TAKERS_V = {'it': ('AUTOMATICI', 'SCELTI'), 'en': ('AUTO', 'CHOSEN'), 'fr': ('AUTO', 'CHOISIS'), 'de': ('AUTO', 'GEWAEHLT')}
ROLES = {'it': 'RUOLI', 'en': 'ROLES', 'fr': 'ROLES', 'de': 'ROLLEN'}      # (Marco's position traits; fr / de to be confirmed)

# the page's rows in order: (key, present, label, values, module whose mask hook reads GM_W at kick-off)
ROWS = (
    ('difficulty', True, difficulty.LABEL, difficulty.VALUES, 'difficulty'),
    ('dribbling', True, difficulty.DRLABEL, difficulty.DRVALUES, 'difficulty'),      # (PERSONALIZZATO opens the dribbling page: nested)
    ('setpieces', True, setpieces.LABEL, setpieces.VALUES, 'setpieces'),
    ('takers', False, TAKERS, TAKERS_V, 'setpieces'),
    ('cpucards', True, cpucards.LABEL, YESNO, 'cpucards'),
    ('cpuinj', True, cpucards.LABEL_I, YESNO, 'cpucards'),
    ('gkinj', True, gkinj.LABEL, YESNO, 'gkinj'),
    ('roles', False, ROLES, YESNO, 'traits'),
)
PAGE_MAX_ROWS = len(difficulty.DP_ROWS)  # the dribbling page's 8 rows: the same page code (title, rows, legend, PREDEFINITI / INDIETRO)


def present():
    return [r for r in ROWS if r[1]]


def page(lang):
    """[(label, values)] of the present rows, in order, for a language."""
    return [(r[2][lang], tuple(r[3][lang])) for r in present()]


difficulty._font_guard(LABEL, VALUES, TITLE, YESNO, PRACTICE, LEG, TAKERS, TAKERS_V, ROLES)
assert len(present()) + 2 <= PAGE_MAX_ROWS, 'gameplay: no room for takers + roles on the page'
assert len({r[0] for r in ROWS}) == len(ROWS)
assert all(set(r[2]) == set(r[3]) == {'it', 'en', 'fr', 'de'} for r in ROWS), 'gameplay: a row misses a language'
assert all(len(VALUES[k]) == 2 and VALUES[k][GM_PERSONALIZZATO] and VALUES[k][GM_ORIGINALE] for k in LABEL)


def on():
    """GAMEPLAY mode: the six mod switches live on the GAMEPLAY page (every build that has difficulty.py's OPTIONS rows)."""
    return difficulty.GMODE and difficulty.knobs()


# ---- the exe side: the GAMEPLAY band (swreg.GAMEPLAY_AT). Every reference to the other bands is PC-relative (ebp = the band's
#      start, label differences are assemble-time constants): the only fixups are the obj2 / obj3 bases and the two obj1 calls.
#      The page is built in the band from a byte image (the packed menu, its pointers zero) + a fill table at each opening.
GM_W_OFF, GM_U_OFF, GM_SH_OFF, GM3_OFF = 0x12, 0x14, 0x1A, 0x1F   # the data's offsets in the band (asserted at the build; the harness reads them)
GM_Y, GM_DY, GM_BACK_X, GM_RESET_X, GM_BACK_Y, GM_LEG_Y = difficulty.DP_Y, difficulty.DP_DY, difficulty.DP_BACK_X, \
    difficulty.DP_RESET_X, difficulty.DP_BACK_Y, difficulty.DP_LEG_Y


def _rows(sdf, ssp, scc, sgk):
    """the page's 6 rows: (label, table) as (kind, offset): kind 0 = obj4 offset, 1 = obj3 offset. Their handler is gm_pg."""
    d, s = sdf, ssp
    return [((0, d['S_LBL']), (0, d['TAB_D'])), ((0, d['S_RLBL']), (0, d['TAB_R'])), ((0, s['S_PLBL']), (0, s['TAB_P'])),
            ((1, scc['S_LR']), (1, scc['TAB_R'])), ((1, scc['S_LI']), (1, scc['TAB_I'])), ((1, sgk['S_LG']), (1, sgk['TAB_G']))]


def menu_image(rows, fill_for):
    """The packed page (bytes, pointers 0) and its fill table [(menu offset, kind, target)]. fill_for(name) -> (kind, offset)
    for the band's own strings."""
    n = len(rows)
    v0 = n + 1
    out, fill = bytearray(), []

    def ptr(t):
        fill.append((len(out), t[0], t[1]))
        out.extend(b'\0\0\0\0')
    out += struct.pack('<4I', 0, 0, 0, v0)
    out += struct.pack('<8H', 12, 0, 280, 15, 4, 0x17, 8, 0)
    ptr(fill_for('S_GT'))
    out += struct.pack('<H', 0)
    for i in range(n):
        out += struct.pack('<8H', 10, GM_Y + GM_DY * i, 140, 11, 4, 9, 8, 0)
        ptr(rows[i][0])
        out += struct.pack('<H', 0)
    h0 = stride = vstart = 0
    for i in range(n):
        if i == 0:
            vstart = len(out)
        up = v0 + i - 1 if i else 255
        dn = v0 + i + 1 if i < n - 1 else 2 * n + 1
        out += struct.pack('<5H4B4H', 154, GM_Y + GM_DY * i, 140, 11, 2, 255, 255, up, dn, 4, 13, 10, 0)
        ptr(rows[i][1])
        out += struct.pack('<2H', 14, 0xE0)
        h0 = h0 or len(out)
        stride = len(out) + 4 + 2 - vstart if i == 0 else stride
        out += b'\0\0\0\0' + struct.pack('<H', 0)
    for x, quad, strn, hn in ((GM_BACK_X, (2 * n + 2, 255, v0 + n - 1, 255), 'S_BK', 'dp_back'),
                              (GM_RESET_X, (255, 2 * n + 1, v0 + n - 1, 255), 'S_RS', 'gm_reset')):
        out += struct.pack('<5H4B4H', x, GM_BACK_Y, 120, 15, 2, *quad, 4, 0x0E, 8, 0)
        ptr(fill_for(strn))
        out += struct.pack('<H', 13)
        ptr(fill_for(hn))
        out += struct.pack('<H', 0)
    out += struct.pack('<8H', 12, GM_LEG_Y, 280, 11, 4, 9, 8, 0)
    ptr(fill_for('S_GLG'))
    out += struct.pack('<Hh', 0, -999)
    return bytes(out), fill, h0, stride


ASM = r"""
GMB0:
    jmp near gm_row                     ; +0  (df_add: the OPTIONS row)
gm_chk:                                 ; +5  (the kick-off masks: ZF = 1 PERSONALIZZATO, 0 ORIGINALE; eax kept)
    push ebp
    call gm_base
    cmp word [ebp + GMO_W], 0
    pop ebp
    ret
GM_W: dw 0                              ; +0Ah  the item 'GM': 0 PERSONALIZZATO / 1 ORIGINALE (a word: the string table's variable)
GM_U: db 0, 0, 0                        ;       the user's CPU cards / injuries / keeper injuries while ORIGINALE
    db 0, 0, 0
GM_SH: dd 0
    db 0                          ; the session's copy (a new career zeroes the item)
GM3: dd GM3S                            ; obj3's base (cpucards / gkinj: CC_W, CC_I, GI_W, their session copies)

gm_dri:                                 ; (one rel32 fixup each into the game: every call / jump goes through these)
    jmp DRAWITEM
gm_shm:
    jmp SHOW_MENU

gm_base:                                ; ebp = the band's start (PC-relative: no fixups)
    call .n
.n: pop ebp
    sub ebp, .n - GMB0
    ret

gm_row:                                 ; df_add: edi = the OPTIONS entry NB (label), NB+1 the value; ebx, edi kept
    call gm_base
    lea eax, [ebp + S_GLBL - GMB0]
    mov [edi + 26h], eax
    lea edx, [ebp + TAB_GM - GMB0]
    mov [edi + 38h + 26h], edx
    lea eax, [ebp + gm_tog - GMB0]
    mov [edi + 38h + 2Ah], eax
    mov word [edi + 38h + 2Eh], 0E0h    ; the value answers LEFT / RIGHT / FIRE (gm_tog tells them apart)
    lea eax, [ebp + GMO_W]        ; (the string table: the word, the first index, the two strings)
    mov [edx], eax
    lea eax, [ebp + S_GV0 - GMB0]
    mov [edx + 6], eax
    lea eax, [ebp + S_GV1 - GMB0]
    mov [edx + 10], eax
    ret

gm_keep:                                ; ebp = the band: the item -> the session's copy
    mov eax, [ebp + GMO_W]
    mov [ebp + GMO_SH], eax
    mov al, [ebp + GMO_W + 4]
    mov [ebp + GMO_SH + 4], al
    ret
gm_load:                                ; after a career load (engine, pushad around): the save's state is the session's
    call gm_base
    jmp gm_keep
gm_new:                                 ; after a new career's defaults (the item zeroed): the session's state back
    call gm_base
    mov eax, [ebp + GMO_SH]
    mov [ebp + GMO_W], eax
    mov al, [ebp + GMO_SH + 4]
    mov [ebp + GMO_W + 4], al
    ret

gm_var:                                 ; esi = a GM_RT entry: ebx = the variable's address (obj4: band-relative, obj3: + GM3)
    mov ebx, [esi]
    cmp byte [esi + 5], 0
    jne .o
    add ebx, ebp
    ret
.o: add ebx, [ebp + GMO_3]
    ret

gm_sync:                                ; the save byte (df_pack) + the CPU rows' session copies
    call DF_PACK
    mov ecx, [ebp + GMO_3]
    mov eax, [ecx + CC_W_O]
    mov [ecx + CC_SH_O], eax
    mov ax, [ecx + GI_W_O]
    mov [ecx + GI_SH_O], ax
    ret

gm_apply:                               ; ebp = the band, ax = the new GM_W (0 / 1): the swap of CPU cards / injuries / keeper
    cmp ax, [ebp + GMO_W]               ; injuries (the rows 3..5: live words <-> the parked bytes), the session copies in step
    je .x
    mov [ebp + GMO_W], ax
    lea esi, [ebp + GM_RT - GMB0 + 18]
    lea edi, [ebp + GMO_U]
    mov ecx, 3
.l: call gm_var
    cmp word [ebp + GMO_W], 0
    jne .p
    movzx edx, byte [edi]               ; PERSONALIZZATO: the parked value back
    mov [ebx], dx
    jmp .n
.p: mov dl, [ebx]                       ; ORIGINALE: parked, the word = 1 (OFF: the original game)
    mov [edi], dl
    mov word [ebx], 1
.n: add esi, 6
    inc edi
    loop .l
    call gm_sync
    jmp gm_keep
.x: ret

gm_tog:                                 ; the OPTIONS row: LEFT / RIGHT toggle PERSONALIZZATO <-> ORIGINALE; FIRE on PERSONALIZZATO
    push ebp                            ;  opens the page, FIRE on ORIGINALE switches to PERSONALIZZATO
    call gm_base
    mov ecx, [ebp + GMO_2 - GMB0]
    cmp word [ebp + GMO_W], 0
    jne .t
    test byte [ecx + D7_O], 20h
    jnz .p
.t: mov ax, [ebp + GMO_W]
    xor ax, 1
    call gm_apply
    pop ebp
    jmp gm_dri
.p: lea eax, [ebp + GM_MENU - GMB0]
    mov [ecx + A6_O], eax               ; the page (OPTIONS comes back unpacked: df_ret re-adds its row)
    call gm_fill
    call SP_TABG                        ; (CALCI PIAZZATI's table pointers)
    pop ebp
    jmp gm_shm

gm_pg:                                  ; the page's value rows (mask 0E0h, as the DRIBBLING page's dp_tog): LEFT / RIGHT = the row's
    call gm_base                        ;  previous / next value, clamped; FIRE = the next, wrapping (D7: 40h / 80h / 20h)
    mov ecx, [ebp + GMO_2 - GMB0]
    mov dl, [ecx + D7_O]
    mov eax, [ecx + MENU_O + 0Ch]       ; the selected entry: its ordinal - GM_V0 = the row
    movzx edi, word [eax + 2]
    sub edi, GM_V0
    lea esi, [edi * 2 + edi]
    lea esi, [ebp + esi * 2 + GM_RT - GMB0]
    call gm_var
    movzx eax, word [ebx]
    movzx ecx, byte [esi + 4]
    test dl, 40h
    jz .r
    test eax, eax
    jz .w
    dec eax
    jmp .w
.r: inc eax
    cmp eax, ecx
    jbe .w
    xor eax, eax                        ; (FIRE wraps, RIGHT stays at the last)
    test dl, 20h
    jnz .w
    mov eax, ecx
.w: mov [ebx], ax
    call gm_sync
    cmp edi, 1                          ; DRIBBLING on PERSONALIZZATO: its page (INDIETRO comes back to this one)
    jne .d
    cmp word [ebp + DF_DR - GMB0], 2
    jne .d
    call DP_FALL
    lea eax, [ebp + DP_MENU - GMB0]
    mov ecx, [ebp + GMO_2 - GMB0]
    mov [ecx + A6_O], eax
    jmp gm_shm
.d: jmp gm_dri

gm_fill:                                ; the page's pointers (ebp = the band)
    mov edx, [ebp + GMO_3]
    lea edi, [ebp + GM_MENU - GMB0]
    lea esi, [ebp + GM_FT - GMB0]
    mov ecx, GM_NFT
.l: movzx eax, word [esi]
    mov ebx, [esi + 2]
    test ah, 80h
    jnz .o
    add ebx, ebp
    jmp .s
.o: and ah, 7Fh
    add ebx, edx
.s: mov [edi + eax], ebx
    add esi, 6
    loop .l
    lea edi, [ebp + GM_MENU - GMB0 + GM_H0] ; the value rows' fire / LEFT / RIGHT handler: gm_pg
    lea eax, [ebp + gm_pg - GMB0]
    mov ecx, GM_N
.h: mov [edi], eax
    add edi, GM_VSTRIDE
    loop .h
    ret

gm_reset:                               ; PREDEFINITI: every switch back to its default (while ORIGINALE: the parked values)
    pushad
    call gm_base
    cmp word [ebp + GMO_W], 0
    jne .p
    lea esi, [ebp + GM_RT - GMB0]
    mov ecx, 6
.l: call gm_var
    mov word [ebx], 0
    add esi, 6
    loop .l
    jmp .k
.p: xor eax, eax
    mov [ebp + GMO_U], eax
.k: call gm_sync
    call gm_keep
    mov edx, [ebp + GMO_2 - GMB0]       ; the rows redrawn (as dp_reset: A5 = the entry, DrawMenuItem)
    mov eax, [edx + MENU_O + 0Ch]
    push eax
    movzx ecx, word [eax + 2]
    imul ecx, ecx, 38h
    sub eax, ecx
    add eax, GM_V0 * 38h
    mov ecx, GM_N
.m: mov [edx + A5_O], eax
    push eax
    push ecx
    push edx
    call gm_dri
    pop edx
    pop ecx
    pop eax
    add eax, 38h
    loop .m
    pop eax
    mov [edx + A5_O], eax
    popad
    ret

TAB_GM: dd 0
    dw 0
    dd 0, 0
"""


def _src(lang, rows, ft, h0, stride):
    db = lambda x: ', '.join(str(c) for c in x.encode('latin-1') + b'\0')
    src = f'%define GM_H0 {h0}\n%define GM_VSTRIDE {stride}\n%define GMO_W {GM_W_OFF}\n%define GMO_U {GM_U_OFF}\n%define GMO_SH {GM_SH_OFF}\n%define GMO_3 {GM3_OFF}\n%define GM_NFT {len(ft)}\n%define GM_N {len(rows)}\n%define GM_V0 {len(rows) + 1}\n' + ASM
    src += f'S_GLBL: db {db(LABEL[lang])}\nS_GV0: db {db(VALUES[lang][0])}\nS_GV1: db {db(VALUES[lang][1])}\n'
    src += ('GM_RT:\n    dd DF_W - GMB0\n    db 2, 0\n    dd DF_DR - GMB0\n    db 2, 0\n    dd SP_W - GMB0\n    db 2, 0\n'
            '    dd CC_W_O\n    db 1, 1\n    dd CC_I_O\n    db 1, 1\n    dd GI_W_O\n    db 1, 1\n')
    src += f'S_GT: db {db(TITLE[lang])}\nS_GLG: db {db(LEG[lang])}\nalign 4\nGM_FT:\n'
    return src, db


def patch(p, lang):
    """The GAMEPLAY band: after difficulty.patch and setpieces.patch (their labels), before the engine items are bound."""
    if not on():
        return None
    import controls
    import engine
    import swreg
    df, sp, cc, gk = difficulty, setpieces, cpucards, gkinj
    dfl, spl = df.LABELS, sp.LABELS
    assert dfl.get('df_add') and spl.get('sp_tabg'), 'gameplay: after difficulty + setpieces'
    at = swreg.GAMEPLAY_AT
    rows = _rows(dfl, spl, cc.LABELS, gk.LABELS)
    assert [r[0] for r in present()] == ['difficulty', 'dribbling', 'setpieces', 'cpucards', 'cpuinj', 'gkinj']
    syms = df.SYMS
    for k in ('A6_', 'A5_', 'MENU_', 'D7_'):
        assert syms[k][0] == 2, ('gameplay: obj2 variable', k, syms[k])
    # pass 1: the label offsets (the page image's own strings: the band's labels), then the image
    base = {'GM3S': (3, 0), 'GMO_2': (4, spl['SPB']), 'DRAWITEM': syms['DRAWITEM'], 'SHOW_MENU': syms['SHOW_MENU'],
            'A6_O': (0, syms['A6_'][1]), 'A5_O': (0, syms['A5_'][1]), 'D7_O': (0, syms['D7_'][1]), 'MENU_O': (0, syms['MENU_'][1]),
            'CC_W_O': (0, cc.LABELS['CC_W']), 'CC_I_O': (0, cc.LABELS['CC_I']), 'CC_SH_O': (0, cc.LABELS['CC_SH']),
            'GI_W_O': (0, gk.LABELS['GI_W']), 'GI_SH_O': (0, gk.LABELS['GI_SH']),
            'DF_W': (4, dfl['DF_W']), 'DF_DR': (4, dfl['DF_DR']), 'SP_W': (4, spl['SP_W']), 'DF_PACK': (4, spl['df_pack']),
            'SP_TABG': (4, spl['sp_tabg']), 'DP_FALL': (4, dfl['dp_fall']), 'DP_MENU': (4, dfl['DP_MENU'])}
    img_probe, ft_probe, h0, stride = menu_image(rows, lambda n: (0, 0))
    src0, db = _src(lang, rows, ft_probe, h0, stride)
    ftsrc = ''.join(f'    dw {o | (k << 15)}\n    dd 0\n' for o, k, _ in ft_probe)
    lab0 = nasmcave.labels(src0 + ftsrc + 'GM_MENU:\n    times %d db 0\n' % len(img_probe), at, base)
    own = {'S_GT': lab0['S_GT'], 'S_GLG': lab0['S_GLG'], 'S_BK': dfl['S_BK'], 'S_RS': dfl['S_RS'], 'dp_back': dfl['dp_back'],
           'gm_reset': lab0['gm_reset'], 'gm_pg': lab0['gm_pg']}
    img, ft, h0, stride = menu_image(rows, lambda n: (0, own[n]))
    assert [(o, k) for o, k, _ in ft] == [(o, k) for o, k, _ in ft_probe]
    ftsrc = ''.join(f'    dw {o | (k << 15)}\n    dd {(t - at) if k == 0 else t}\n' for o, k, t in ft)
    src = src0 + ftsrc + 'GM_MENU:\n    db ' + ', '.join(map(str, img)) + '\n'
    code, fix, rel = nasmcave.assemble_obj(src, at, base, 4)
    lab = nasmcave.labels(src, at, base)
    assert all(lab[k] == v for k, v in lab0.items() if k in lab and k != 'GM_MENU'), 'gameplay: labels moved between passes'
    assert (lab['GM_W'] - at, lab['GM_U'] - at, lab['GM_SH'] - at, lab['GM3'] - at) == (GM_W_OFF, GM_U_OFF, GM_SH_OFF, GM3_OFF), \
        ('gameplay: data offsets (the harness reads them)', hex(lab['GM_W'] - at), hex(lab['GM_U'] - at), hex(lab['GM_SH'] - at))
    assert lab['gm_chk'] == at + 5, ('gameplay: gm_chk is the jump table slot 2', hex(lab['gm_chk']))
    assert len(fix) == 1 and len(rel) == 2, ('gameplay: fixups (GM3, DRAWITEM, SHOW_MENU only: 3 records)', fix, rel)
    left = swreg.GAMEPLAY_END - at - len(code)
    assert left >= 256, ('gameplay: band room (floor 256)', left)
    assert p.le.obj(4).npages * 0x1000 >= swreg.GAMEPLAY_END, 'gameplay: obj4 pages'
    assert not any(p.get(4, at, swreg.GAMEPLAY_END - at)), 'gameplay: band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    engine.ITEM_AT['GM'] = (4, lab['GM_W'])
    engine.CALL_AT['gm_load'] = (4, lab['gm_load'])
    engine.CALL_AT['gm_new'] = (4, lab['gm_new'])
    LABELS.clear()
    LABELS.update(lab)
    print(f'exe: GAMEPLAY band obj4+{at:#x}: {len(code)} B, {left} B left (page image {len(img)} B)')
    return at + len(code)


LABELS = {}
