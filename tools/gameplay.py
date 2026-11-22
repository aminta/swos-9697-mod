"""4.2 GAMEPLAY = ORIGINALE / PERSONALIZZATO (Davide 15/11; design internal/handoff/gameplay-menu-design.md, MC). Host-side part P1:
the row table, the strings (4 languages, font-safe) and the save item's constants. No exe code yet (the page code goes into
the GAMEPLAY reserve of obj4pack, 0x400, after Shaved's commit is in 42-int).

OPTIONS gets ONE row GAMEPLAY (ORIGINALE / PERSONALIZZATO; FIRE on PERSONALIZZATO opens the page). The page holds the mod's
match-play switches as a TABLE of rows, each with a 'present' flag: a row that is not in yet (TIRATORI; RUOLI is in
since 16/11, below) is simply absent - no empty line, no placeholder text; adding one later = one table entry + its module's mask hook,
inside the reserve (asserted: room for 2 more rows).
ORIGINALE is a MASK applied at kick-off (every switch acts as its original value; the sub-values are kept). GM_W, the engine
item 'GM' (1 B): 0 = PERSONALIZZATO (default, today's defaults), 1 = ORIGINALE; a save without GM loads PERSONALIZZATO.
SWOS++: the row is hidden and everything original (as every other row of ours).

RUOLI (Marco's position traits; internal/handoff/traits-split.md) is the page's 7th row: SI / NO, default NO (RUOLI_DEFAULT,
the ONE constant: Davide 16/11 - the traits are off until the player switches them on; it may become SI later). Every traits piece
reads ONE byte, GP_RUOLI = obj4 + swreg.GAMEPLAY_AT + GP_RUOLI_OFF (gp_ruoli() gives the (obj, offset) pair):
    1 = RUOLI SI and GAMEPLAY PERSONALIZZATO: the traits apply;   0 = RUOLI NO or GAMEPLAY ORIGINALE: today's game, exactly.
A consumer tests `cmp byte [GP_RUOLI], 0` (asm: GP_RUOLI in its symbols, one absolute fixup per site, none from obj4 code that
reaches it PC-relative from its own band base) or `*(const unsigned char *)GP_RUOLI` (C) and does the original thing on 0; it
never reads GM_R / GM_W itself. The byte is kept in step by this module at every change (the page's row, the OPTIONS row,
PREDEFINITI, a career load, a new career); it is 0 at the program's start (RUOLI_DEFAULT = NO; a GM_RUOLI_SI=1 TEST build starts
with SI / 1, see RUOLI_START).
GP_RUOLI HAS NO SWOS++ GATE AND NO TRAINING-GAME GATE: it is the row's state and nothing else (under SWOS++ the row is hidden and
the byte keeps its start value or a loaded career's). EACH CONSUMER KEEPS ITS OWN gates - `cmp byte [SWOSPP], 0FFh` and the
training-game word (TRG) - in front of its GP_RUOLI test, as every stub of ours does.
The user's choice is the word GM_R (0 SI / 1 NO), kept while ORIGINALE (GP_RUOLI is then 0: nothing to park), saved with the
career as bit 7 of the GM item's byte 2 (the first parked byte, whose values are 0 / 1): set = SI, clear = NO, absolutely
(never relative to RUOLI_DEFAULT). The item stays 5 B, the save format does not change, and a save without the bit or the item
(4.1, an earlier 4.2 beta) loads RUOLI NO = the original game. A new career keeps the session's choice (the session copy), which
at the program's start is the default.
Room: the band had 257 B free with six rows (IT; the floor is 256) and the row costs ~180 B (58 B of page image, the rest
tables + code), so with the row the PAGE IMAGE (data only: the packed menu + RUOLI's string table, 550 B) lives in obj3, in the
chain right after gkinj (the CPU rows' tables are there already; reached through GM3, the band's one obj3 base: no new fixup).
The band then keeps the code, the strings and the fill table (~1.05 KB, ~600 B free).
GM_NOROLES=1 (a build switch, cleared by buildrel.sh): the row absent, the image in the band, the exe byte for byte the one
before the row existed."""
import os
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
TITLE = {'it': 'GAMEPLAY PERSONALIZZATO', 'en': 'CUSTOM GAMEPLAY', 'fr': 'GAMEPLAY PERSONNALISE', 'de': 'SPIELWEISE INDIVIDUELL'}
YESNO = {'it': ('SI', 'NO'), 'en': ('YES', 'NO'), 'fr': ('ACTIVE', 'DESACTIVE'), 'de': ('EIN', 'AUS')}   # (0 = the first word. NOMINAL: the exe's
#  YES / NO rows - CPU cards, CPU injuries, keeper injuries, RUOLI - draw the game's OWN two switch strings, read from its OPTIONS menu by
#  cpucards.strings(); this table only names them for page() and the tests. fr / de = the game's switch words, Regia's audit 19/11)
PRACTICE = {'it': 'GAMEPLAY: ORIGINALE', 'en': 'GAMEPLAY: ORIGINAL', 'fr': 'GAMEPLAY: ORIGINAL', 'de': 'SPIELWEISE: ORIGINAL'}
LEG = {'it': 'SINISTRA/DESTRA CAMBIA FUOCO: AVANTI', 'en': 'LEFT/RIGHT CHANGE FIRE: NEXT',
       'fr': 'GAUCHE/DROITE: CHANGER  FEU: SUIVANT', 'de': 'LINKS/RECHTS: AENDERN  FEUER: WEITER'}
# takers: not in yet (its texts are ready, the 'present' flag off); RUOLI (Marco's traits): in, GM_NOROLES takes it out
TAKERS = {'it': 'TIRATORI', 'en': 'TAKERS', 'fr': 'TIREURS', 'de': 'SCHUETZEN'}
TAKERS_V = {'it': ('AUTOMATICI', 'SCELTI'), 'en': ('AUTO', 'CHOSEN'), 'fr': ('AUTO', 'CHOISIS'), 'de': ('AUTO', 'GEWAEHLT')}
ROLES = {'it': 'RUOLI', 'en': 'ROLES', 'fr': 'APTITUDES PAR POSTE', 'de': 'SPIELERTYPEN'}      # (Marco's position traits; fr / de: Regia's audit 19/11)

# the page's rows in order: (key, present, label, values, module whose mask hook reads GM_W at kick-off)
ROWS = (
    ('difficulty', True, difficulty.LABEL, difficulty.VALUES, 'difficulty'),
    ('dribbling', True, difficulty.DRLABEL, difficulty.DRVALUES, 'difficulty'),      # (PERSONALIZZATO opens the dribbling page: nested)
    ('setpieces', True, setpieces.LABEL, setpieces.VALUES, 'setpieces'),
    ('takers', False, TAKERS, TAKERS_V, 'setpieces'),
    ('cpucards', True, cpucards.LABEL, YESNO, 'cpucards'),
    ('cpuinj', True, cpucards.LABEL_I, YESNO, 'cpucards'),
    ('gkinj', True, gkinj.LABEL, YESNO, 'gkinj'),
    ('roles', not os.environ.get('GM_NOROLES'), ROLES, YESNO, 'traits'),   # (no mask hook: GP_RUOLI, see the module's text)
)
PAGE_MAX_ROWS = len(difficulty.DP_ROWS)  # the dribbling page's 8 rows: the same page code (title, rows, legend, PREDEFINITI / INDIETRO)


def present():
    return [r for r in ROWS if r[1]]


def page(lang):
    """[(label, values)] of the present rows, in order, for a language."""
    return [(r[2][lang], tuple(r[3][lang])) for r in present()]


difficulty._font_guard(LABEL, VALUES, TITLE, YESNO, PRACTICE, LEG, TAKERS, TAKERS_V, ROLES)
assert len(ROWS) <= PAGE_MAX_ROWS, 'gameplay: no room for takers + roles on the page'
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
GM_R_OFF, GP_RUOLI_OFF = 0x17, 0x19     # RUOLI: the row's word (0 SI / 1 NO) and THE byte the traits pieces read (1 = traits on)
RUOLI_DEFAULT = 0 if os.environ.get('GM_RUOLI_D0') else 1   # THE default of the row (0 SI / 1 NO; Davide 16/11: NO, the traits are switched on by the player):
                                        # the program's start (GM_R, GP_RUOLI = 1 - it, the item's / session copy's bit) and PREDEFINITI.
                                        # NOT the saves: their bit is absolute (MC 16/11: set = SI, clear = NO in every version, so a
                                        # change of this constant never flips a career; a save without the bit / the item = NO).
assert RUOLI_DEFAULT in (0, 1)
# (GM_RUOLI_D0=1: a TEST build switch, modver TEST_VARS, cleared by buildrel.sh - the exe with the OTHER default, test_gameplay's
#  ALT fixture HTGPD0 (mkfixtures.sh), that proves the saved bit absolute; unset = 1, the release value)
RUOLI_START = 0 if os.environ.get('GM_RUOLI_SI') else RUOLI_DEFAULT    # GM_RUOLI_SI=1 (a TEST build switch, modver TEST_VARS: 'MOD .. TEST',
                                        # cleared by buildrel.sh): the program STARTS with RUOLI SI (GM_R 0, GP_RUOLI 1, the item's /
                                        # session copy's bit set, so the first new career keeps it) - for the traits pieces' gates.
                                        # Nothing else changes: PREDEFINITI still gives RUOLI_DEFAULT, the saved bit stays absolute.
GM_R_BIT = 0x80                         # (the save: bit 7 of the item's byte 2 = GM_U[0]; set = RUOLI SI)


def roles():
    return any(r[0] == 'roles' for r in present())


def gp_ruoli():
    """(obj, offset) of GP_RUOLI: one byte, 1 = RUOLI SI and GAMEPLAY PERSONALIZZATO, else 0 (the module's text: how to read it)."""
    import swreg
    assert roles(), 'gameplay: GP_RUOLI needs the RUOLI row (GM_NOROLES set?)'
    return 4, swreg.GAMEPLAY_AT + GP_RUOLI_OFF
GM_Y, GM_DY, GM_BACK_X, GM_RESET_X, GM_BACK_Y, GM_LEG_Y = difficulty.DP_Y, difficulty.DP_DY, difficulty.DP_BACK_X, \
    difficulty.DP_RESET_X, difficulty.DP_BACK_Y, difficulty.DP_LEG_Y


def _rows(sdf, ssp, scc, sgk, own=None, tab_ru=0):
    """the page's rows: (label, table) as (kind, offset): kind 0 = obj4 offset, 1 = obj3 offset. Their handler is gm_pg.
    own: the band's own labels (RUOLI's label; None = the probe pass, its place not known yet); tab_ru: RUOLI's string table (obj3)."""
    d, s = sdf, ssp
    ru = [((0, own['S_RUL'] if own else 0), (1, tab_ru))] if roles() else []
    return [((0, d['S_LBL']), (0, d['TAB_D'])), ((0, d['S_RLBL']), (0, d['TAB_R'])), ((0, s['S_PLBL']), (0, s['TAB_P'])),
            ((1, scc['S_LR']), (1, scc['TAB_R'])), ((1, scc['S_LI']), (1, scc['TAB_I'])), ((1, sgk['S_LG']), (1, sgk['TAB_G']))] + ru


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
%if ROLES                               ;       the user's CPU cards / injuries / keeper injuries while ORIGINALE
GM_U: db (1 - RU_START) << 7, 0, 0      ;       (RUOLI saved in bit 7 of the first, set = SI: gm_rs; here the start value's)
GM_R: dw RU_START                       ; +17h  RUOLI, the row's word: 0 SI / 1 NO (starts at RU_START = RUOLI_DEFAULT; a GM_RUOLI_SI test build: 0) - the user's choice, kept while ORIGINALE
GP_RUOLI: db 1 - RU_START               ; +19h  THE traits switch: 1 = RUOLI SI and PERSONALIZZATO, else 0 (gm_rs keeps it)
%else
GM_U: db 0, 0, 0
    db 0, 0, 0
%endif
GM_SH: dd (ROLES * (1 - RU_START)) << 23 ; the session's copy (a new career zeroes the item); its RUOLI bit as GM_U's
    db 0
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
%if ROLES
    call gm_ru
%endif
    jmp gm_keep
gm_new:                                 ; after a new career's defaults (the item zeroed): the session's state back
    call gm_base
    mov eax, [ebp + GMO_SH]
    mov [ebp + GMO_W], eax
    mov al, [ebp + GMO_SH + 4]
    mov [ebp + GMO_W + 4], al
%if ROLES
gm_ru:                                  ; ebp = the band: the item's RUOLI bit -> GM_R (a load, a new career), then gm_rs
    movzx eax, byte [ebp + GMO_U]       ;  (the bit is ABSOLUTE, whatever RU_DEF: set = SI, clear = NO; a zeroed item - an
    shr eax, 7                          ;   older save - is NO, the original game)
    xor eax, 1
    mov [ebp + GMO_R], ax
gm_rs:                                  ; ebp = the band: GM_R -> the item's bit (set = SI; and the session copy's);
    mov al, [ebp + GMO_R]               ;  GP_RUOLI = 1 when GM_W = 0 (PERSONALIZZATO) and GM_R = 0 (SI), else 0. eax used
    xor al, 1
    shl al, 7
    and byte [ebp + GMO_U], 7Fh
    or al, [ebp + GMO_U]
    mov [ebp + GMO_U], al
    mov [ebp + GMO_SH + 2], al
    mov al, [ebp + GMO_W]
    or al, [ebp + GMO_R]
    setz byte [ebp + GMO_GP]
%endif
    ret

gm_var:                                 ; esi = a GM_RT entry: ebx = the variable's address (obj4: band-relative, obj3: + GM3)
    mov ebx, [esi]
    cmp byte [esi + 5], 0
    jne .o
    add ebx, ebp
    ret
.o: add ebx, [ebp + GMO_3]
    ret

gm_sync:                                ; the save byte (df_pack) + the CPU rows' session copies (+ RUOLI: gm_rs)
%if ROLES
    call gm_rs
%endif
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
%if ROLES
    and edx, 1                          ; (bit 7 of the first parked byte = RUOLI)
%endif
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
.p:
%if ROLES
    mov eax, [ebp + GMO_3]              ; (with RUOLI the page image is in obj3)
    add eax, GM_IMG_O
%else
    lea eax, [ebp + GM_MENU - GMB0]
%endif
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
%if ROLES
    lea edi, [edx + GM_IMG_O]
%else
    lea edi, [ebp + GM_MENU - GMB0]
%endif
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
%if ROLES
    lea edi, [edx + GM_IMG_O + GM_H0]
%else
    lea edi, [ebp + GM_MENU - GMB0 + GM_H0] ; the value rows' fire / LEFT / RIGHT handler: gm_pg
%endif
    lea eax, [ebp + gm_pg - GMB0]
    mov ecx, GM_N
.h: mov [edi], eax
    add edi, GM_VSTRIDE
    loop .h
%if ROLES
    mov eax, [edx + CC_TABR_O + 6]      ; RUOLI's string table (after the image; its word: the fill table): the CPU rows' two
    mov [edx + GM_IMG_O + GM_TABRU + 6], eax    ; value strings (obj3 TAB_R: the game's own)
    mov eax, [edx + CC_TABR_O + 10]
    mov [edx + GM_IMG_O + GM_TABRU + 10], eax
%endif
    ret

gm_reset:                               ; PREDEFINITI: every switch back to its default (while ORIGINALE: the parked values)
    pushad
    call gm_base
    cmp word [ebp + GMO_W], 0
    jne .p
    lea esi, [ebp + GM_RT - GMB0]
    mov ecx, GM_N
.l: call gm_var
    mov word [ebx], 0
    add esi, 6
    loop .l
    jmp .k
.p: xor eax, eax
    mov [ebp + GMO_U], eax
.k:
%if ROLES && RU_DEF
    mov word [ebp + GMO_R], RU_DEF      ; (RUOLI's default is not 0: both paths above left it 0; gm_sync sets the bit)
%endif
    call gm_sync
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
    src = f'%define GM_H0 {h0}\n%define GM_VSTRIDE {stride}\n%define GMO_W {GM_W_OFF}\n%define GMO_U {GM_U_OFF}\n%define GMO_SH {GM_SH_OFF}\n%define GMO_3 {GM3_OFF}\n%define ROLES {int(roles())}\n%define RU_DEF {RUOLI_DEFAULT}\n%define RU_START {RUOLI_START}\n%define GMO_R {GM_R_OFF}\n%define GMO_GP {GP_RUOLI_OFF}\n%define GM_NFT {len(ft)}\n%define GM_N {len(rows)}\n%define GM_V0 {len(rows) + 1}\n' + ASM
    src += f'S_GLBL: db {db(LABEL[lang])}\nS_GV0: db {db(VALUES[lang][0])}\nS_GV1: db {db(VALUES[lang][1])}\n'
    src += ('GM_RT:\n    dd DF_W - GMB0\n    db 2, 0\n    dd DF_DR - GMB0\n    db 2, 0\n    dd SP_W - GMB0\n    db 2, 0\n'
            '    dd CC_W_O\n    db 1, 1\n    dd CC_I_O\n    db 1, 1\n    dd GI_W_O\n    db 1, 1\n')
    if roles():
        src += f'    dd GM_R - GMB0\n    db 1, 0\nS_RUL: db {db(ROLES[lang])}\n'
    src += f'S_GT: db {db(TITLE[lang])}\nS_GLG: db {db(LEG[lang])}\nGM_FT:\n'
    return src, db


TAB_RU_SIZE = 14                        # (a string table: dd the word, dw the first index, dd the two strings)


def patch(p, lang, at3=None):
    """The GAMEPLAY band: after difficulty.patch and setpieces.patch (their labels), before the engine items are bound.
    at3: the obj3 chain's next free place (the page image goes there with the RUOLI row). Returns the obj3 end when it used
    obj3, else None."""
    if not on():
        return None
    import controls
    import engine
    import swreg
    df, sp, cc, gk = difficulty, setpieces, cpucards, gkinj
    dfl, spl = df.LABELS, sp.LABELS
    if df.trace():                               # (DIFF_TRACE builds have no PERSONALIZZATO page - difficulty dp_asm page=False -:
        dfl = {**{n: dfl['DF_W'] for n in ('DP_MENU', 'dp_fall', 'S_BK', 'S_RS', 'dp_back')}, **dfl}   # as setpieces: at DF_W,
                                                 #  never reached - a traced match never opens OPTIONS)
    assert dfl.get('df_add') and spl.get('sp_tabg'), 'gameplay: after difficulty + setpieces'
    at = swreg.GAMEPLAY_AT
    rows = _rows(dfl, spl, cc.LABELS, gk.LABELS)
    assert [r[0] for r in present()] == ['difficulty', 'dribbling', 'setpieces', 'cpucards', 'cpuinj', 'gkinj'] + ['roles'] * roles()
    if roles():
        from complist import px
        assert px(ROLES[lang]) <= 138 and re.fullmatch(r'[A-Z ]+', ROLES[lang]), ('gameplay: the RUOLI label (the row box, as cpucards)', ROLES[lang])
    syms = df.SYMS
    for k in ('A6_', 'A5_', 'MENU_', 'D7_'):
        assert syms[k][0] == 2, ('gameplay: obj2 variable', k, syms[k])
    # pass 1: the label offsets (the page image's own strings: the band's labels), then the image
    base = {'GM3S': (3, 0), 'GMO_2': (4, spl['SPB']), 'DRAWITEM': syms['DRAWITEM'], 'SHOW_MENU': syms['SHOW_MENU'],
            'A6_O': (0, syms['A6_'][1]), 'A5_O': (0, syms['A5_'][1]), 'D7_O': (0, syms['D7_'][1]), 'MENU_O': (0, syms['MENU_'][1]),
            'CC_W_O': (0, cc.LABELS['CC_W']), 'CC_I_O': (0, cc.LABELS['CC_I']), 'CC_SH_O': (0, cc.LABELS['CC_SH']), 'CC_TABR_O': (0, cc.LABELS['TAB_R']),
            'GI_W_O': (0, gk.LABELS['GI_W']), 'GI_SH_O': (0, gk.LABELS['GI_SH']),
            'DF_W': (4, dfl['DF_W']), 'DF_DR': (4, dfl['DF_DR']), 'SP_W': (4, spl['SP_W']), 'DF_PACK': (4, spl['df_pack']),
            'SP_TABG': (4, spl['sp_tabg']), 'DP_FALL': (4, dfl['dp_fall']), 'DP_MENU': (4, dfl['DP_MENU'])}
    img_probe, ft_probe, h0, stride = menu_image(rows, lambda n: (0, 0))
    ext = roles()                       # (the image + RUOLI's table in obj3, their fill entries after the image's)
    if ext:
        assert at3 is not None and at3 % 16 == 0, 'gameplay: the RUOLI row needs its obj3 place (patch.py: the chain after gkinj)'
        base['GM_IMG_O'] = (0, at3)
        ft_x = [(len(img_probe), 0, 0)]
    else:
        ft_x = []
    src0, db = _src(lang, rows, ft_probe + ft_x, h0, stride)
    src0 = f'%define GM_TABRU {len(img_probe)}\n' + src0
    ftsrc = ''.join(f'    dw {o | (k << 15)}\n    dd 0\n' for o, k, _ in ft_probe + ft_x)
    tail = lambda im: '' if ext else 'GM_MENU:\n    ' + im + '\n'
    lab0 = nasmcave.labels(src0 + ftsrc + tail('times %d db 0' % len(img_probe)), at, base)
    own = {'S_GT': lab0['S_GT'], 'S_GLG': lab0['S_GLG'], 'S_BK': dfl['S_BK'], 'S_RS': dfl['S_RS'], 'dp_back': dfl['dp_back'],
           'gm_reset': lab0['gm_reset'], 'gm_pg': lab0['gm_pg']}
    rows = _rows(dfl, spl, cc.LABELS, gk.LABELS, lab0, (at3 or 0) + len(img_probe))
    img, ft, h0, stride = menu_image(rows, lambda n: (0, own[n]))
    assert len(img) == len(img_probe) and [(o, k) for o, k, _ in ft] == [(o, k) for o, k, _ in ft_probe]
    if ext:
        ft = ft + [(len(img), 0, lab0['GM_R'])]                # (RUOLI's table: its word; the two strings: gm_fill)
    ftsrc = ''.join(f'    dw {o | (k << 15)}\n    dd {(t - at) if k == 0 else t}\n' for o, k, t in ft)
    src = src0 + ftsrc + tail('db ' + ', '.join(map(str, img)))
    code, fix, rel = nasmcave.assemble_obj(src, at, base, 4)
    lab = nasmcave.labels(src, at, base)
    assert all(lab[k] == v for k, v in lab0.items() if k in lab and k != 'GM_MENU'), 'gameplay: labels moved between passes'
    assert (lab['GM_W'] - at, lab['GM_U'] - at, lab['GM_SH'] - at, lab['GM3'] - at) == (GM_W_OFF, GM_U_OFF, GM_SH_OFF, GM3_OFF), \
        ('gameplay: data offsets (the harness reads them)', hex(lab['GM_W'] - at), hex(lab['GM_U'] - at), hex(lab['GM_SH'] - at))
    if roles():
        assert (lab['GM_R'] - at, lab['GP_RUOLI'] - at) == (GM_R_OFF, GP_RUOLI_OFF) and (4, lab['GP_RUOLI']) == gp_ruoli(), \
            ('gameplay: GM_R / GP_RUOLI offsets (the traits pieces read GP_RUOLI there)', hex(lab['GM_R'] - at), hex(lab['GP_RUOLI'] - at))
        assert code[GP_RUOLI_OFF] == 1 - RUOLI_START and code[GM_R_OFF:GM_R_OFF + 2] == bytes([RUOLI_START, 0]) and \
            code[GM_U_OFF] == code[GM_SH_OFF + 2] == (1 - RUOLI_START) * GM_R_BIT, 'gameplay: RUOLI starts at RUOLI_START (word, GP_RUOLI, the item / session bit)'
        if RUOLI_START != RUOLI_DEFAULT:
            import modver
            assert modver.is_test(), 'gameplay: GM_RUOLI_SI is a TEST build switch'
            print('exe: TEST build: GM_RUOLI_SI - the program starts with RUOLI SI (GP_RUOLI 1); the default stays ' + ('NO' if RUOLI_DEFAULT else 'SI'))
    assert lab['gm_chk'] == at + 5, ('gameplay: gm_chk is the jump table slot 2', hex(lab['gm_chk']))
    assert len(fix) == 1 and len(rel) == 2, ('gameplay: fixups (GM3, DRAWITEM, SHOW_MENU only: 3 records)', fix, rel)
    left = swreg.GAMEPLAY_END - at - len(code)
    assert left >= 256, ('gameplay: band room (floor 256)', left)
    assert p.le.obj(4).npages * 0x1000 >= swreg.GAMEPLAY_END, 'gameplay: obj4 pages'
    assert not any(p.get(4, at, swreg.GAMEPLAY_END - at)), 'gameplay: band not free'
    p.put(4, at, code)
    end3 = None
    if ext:
        end3 = at3 + len(img) + TAB_RU_SIZE
        assert not any(p.get(3, at3, end3 - at3)), 'gameplay: obj3 place not free'
        p.put(3, at3, img + bytes(TAB_RU_SIZE))
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    engine.ITEM_AT['GM'] = (4, lab['GM_W'])
    engine.CALL_AT['gm_load'] = (4, lab['gm_load'])
    engine.CALL_AT['gm_new'] = (4, lab['gm_new'])
    LABELS.clear()
    LABELS.update(lab)
    if ext:
        LABELS.update(GM_IMG3=at3, GM_TABRU3=at3 + len(img))        # (obj3 offsets: the hosttest reads them)
    print(f'exe: GAMEPLAY band obj4+{at:#x}: {len(code)} B, {left} B left (page image {len(img)} B' +
          (f' + RUOLI table in obj3+{at3:#x}..{end3:#x}; GP_RUOLI obj4+{lab["GP_RUOLI"]:#x})' if ext else ')'))
    return end3


LABELS = {}
