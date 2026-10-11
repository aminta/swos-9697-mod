"""Automatic home/away kit choice (SetInGameTeamsPrimaryColors / GetTeamKitsSimilarityFactor).

The game scores how alike two kits look (5 or 2 points for each pair of clashing colours) and uses the first of
home-home, home-away, away-home, away-away that scores below 11. Many classic pairings never met in home kits
(Juventus-Milan, Milan-Inter, Inter-Juventus, Chelsea against Juventus, Newcastle or Manchester City).
Analysis of the colour adjacency graph: DaniSwos, SWOS United forum thread "Home-Away kit
automatic selection". Variants tested on every same-country pairing with tools/kitsim.py (variant 'C').

Changes (all four languages, found by byte content):
 1. conflict tables (conflictingBasicTeamColorsTable, conflictingShortsTeamColorsTable): black no longer clashes
    with blue or green, blue no longer with light blue (far apart in the in-game palette, pal.256);
 2. GetTeamKitsSimilarityFactor bug: after the stripe-merge pass (a striped shirt checked again as its blended
    colour, e.g. red+black -> maroon) the loop start tests D0/D4, which then hold the 'converted' flags, not the
    shirt types, so the other striped team lost its stripes (Inter became all black). The two tests now read
    shirtType1/shirtType2 (same on the first pass);
 3. same-coloured shorts on both teams weigh 3 instead of 5.
"""
import re
import struct

import kitsim

TABLE_BYTES = 20


def patch(p):
    # 1. conflict tables (obj2)
    d2 = p.le.obj_bytes(2)
    new = kitsim.variants()['C']
    for old, rows in ((kitsim.BASIC, new.basic), (kitsim.SHORTS, new.shorts)):
        b = struct.pack('<10H', *old)
        at = d2.find(b)
        assert at >= 0 and d2.count(b) == 1, 'kit colour table'
        assert p.get(2, at, TABLE_BYTES) == b
        p.put(2, at, struct.pack('<10H', *rows))

    # 2. GetTeamKitsSimilarityFactor prologue:
    #    mov al,[D0]; mov [shirtType1],al; mov al,[D4]; mov [shirtType2],al
    #    cmp byte [D0],0; jnz; mov al,[D1]; mov [D2],al; cmp byte [D4],0; jnz
    d1 = p.le.obj_bytes(1)
    pat = re.compile(rb'\xA0....\xA2....\xA0....\xA2....\x80\x3D....\x00\x75.\xA0....\xA2....\x80\x3D....\x00\x75', re.S)
    hits = [m.start() for m in pat.finditer(d1)]
    assert len(hits) == 1, 'GetTeamKitsSimilarityFactor'
    o = hits[0]
    assert p.get(1, o, 4) == d1[o:o + 4]
    for cmp_at, st_at, d_at in ((o + 22, o + 6, o + 1), (o + 41, o + 16, o + 11)):
        assert p.target(1, cmp_at) == p.target(1, d_at)            # cmp byte [D0|D4], 0
        tobj, toff = p.target(1, st_at)                           # shirtType1|2
        p.retarget(1, cmp_at, tobj, toff)
        p.put(1, cmp_at, struct.pack('<I', toff))

    # 3. the last 'add similarityFactor, n' of the no-conflict sum (D3 vs D7: shorts vs shorts)
    sim = None
    adds = []
    for m in re.finditer(rb'\x66\xC7\x05....\x63\x00', d1[o:o + 0x200], re.S):   # mov similarityFactor, 99
        sim = p.target(1, o + m.start() + 3)
        break
    assert sim
    for m in re.finditer(rb'\x66\x83\x05....(.)', d1[o:o + 0x600], re.S):
        at = o + m.start()
        try:
            t = p.target(1, at + 3)
        except AssertionError:      # look-alike bytes without a fixup
            continue
        if t == sim:
            adds.append(at)
    imms = [d1[a + 7] for a in adds]
    assert imms == [1, 5, 5, 2, 5, 5, 2, 2, 2, 5], imms
    p.put(1, adds[-1] + 7, bytes([new.wshorts]))




# --- manual choice: a KITS button in the pre-match screen opens a SELECT KITS editor (this match only) ----------------
# 1. The packed playMatchMenu (obj2, ends with dw -999) is copied into the obj1 cave with one more entry, 68, appended
#    (the game's indices do not change; its fixups are replicated). ShowPlayMatchMenu's `call ShowMenu` goes through
#    pm_show, which refreshes the copy from the original first (SWOS++ patches the original in memory at start-up: its
#    onReturn and an entry pointer, swospp.bin+0x10eee/+0x10f67) and shows the copy. Entry 68: screen x 30..88, y 1..11, the free top-left corner between the check/X sprite (entry 0) and
#    the team name (entry 1); entry 13 (first player) gets up -> 68. Its text is a fixed buffer (KITS AUTO / KITS SET),
#    so a re-unpacked menu keeps it. (A first attempt recycled the "COACH:" entry 4: it is the coach name at run time.)
# 2. Fire on 68 opens a new menu built around the game's own kit editor: entries 4..19 of editTeamsMenu (first and
#    second kit: big shirt, shorts, socks, the four shirt types), copied byte for byte at the SAME indices, because
#    their routines (EditTeamsChange*, EditTeamsSelect*ShirtType, *KitColorConversion, Mark*KitShirt) redraw by index
#    and work on editTeamsTeam (684-byte buffer used only by the Edit Teams menu). Around them: 0 title, 1 team name
#    (fire = the other team), 2 which kit it wears (fire = toggle), 3 the other team's choice, 20 cancel, 21 OK,
#    22 reset (the team file's kits). Two slots (one per team: name, both kits, kit worn, team pointer) live in obj2.
# 3. OK arms the choice. The jump at the start of SetInGameTeamsPrimaryColors finds each team's slot by name (A2 top,
#    A3 bottom), loads the kit it wears into topTeamInGame / bottomTeamInGame with ConvertTeamKitColors, skips the
#    automatic choice and disarms (one match only; the button shows AUTO again). Nothing is written to the team files.
TEXTS = {
    'it': dict(auto=b'MAGLIE AUTO', set=b'MAGLIE FISSE', title=b'SELEZIONA MAGLIE', wears=b'IN CAMPO: ',
               k1=b'PRIMA TENUTA', k2=b'SECONDA TENUTA', cancel=b'ESCI', ok=b'OK', reset=b'RESET'),
    'en': dict(auto=b'KITS AUTO', set=b'KITS SET', title=b'SELECT KITS', wears=b'WEARS: ',
               k1=b'FIRST KIT', k2=b'SECOND KIT', cancel=b'CANCEL', ok=b'OK', reset=b'RESET'),
    'fr': dict(auto=b'TENUES AUTO', set=b'TENUES FIXES', title=b'CHOIX DES TENUES', wears=b'PORTE: ',
               k1=b'1ERE TENUE', k2=b'2EME TENUE', cancel=b'ANNULER', ok=b'OK', reset=b'RESET'),
    'de': dict(auto=b'TRIKOT AUTO', set=b'TRIKOT FEST', title=b'TRIKOTWAHL', wears=b'TRAEGT: ',
               k1=b'HEIMTRIKOT', k2=b'AUSWAERTS', cancel=b'ABBRUCH', ok=b'OK', reset=b'RESET'),
}
KITS_ENTRY = 68
BUTTON = (22, 21, 58, 10)       # packed x, y, width, height (screen = x + 8, y - 20): x 30..88
BUTTON_COLOR = 8                # as USE MATCH TEAM: blue to black, grey frame
SLOT = 36                       # name 18, kits 10 (+18), worn kit (+28), team pointer (+32)

PM_MENU_HEAD = struct.pack('<IIhhhhhhh', 0, 9, -998, 0, -20, 3, 20, 16, 13)  # after the init/return pointers
PM_MENU_TAIL = struct.pack('<hhhh', 0x42, 6, 0, 3)                           # sidePitchPositionsDefault follows
PM_ENTRY13 = struct.pack('<hhhhh', 23, 33, 82, 8, 2) + bytes((0xFF, 38, 0xFF, 14)) + b'\0\0'
ET_KITS = struct.pack('<hhhhhhhhh', -998, 211, 21, 23, 0, 0, 6, 8, 0)        # editTeamsMenu: before entry 4
ET_AFTER = struct.pack('<hhhhhhh', -998, 0, 0, 164, 185, 40, 15)             # before entry 20 (IMPORT)
# payload bytes of each packed record type (UnpackMenu's menuTypesJumpTable) met in the copied entries
PAYLOAD = {1: 0, 2: 4, 4: 2, 8: 6, 9: 2, 12: 4, 13: 4, 14: 6, 15: 4, 16: 4, 17: 2, 18: 2, 19: 2, 20: 2, 21: 4}

KITS_ASM = r"""
km_open:                                ; fire on the KITS button (playMatchMenu entry 68)
    pushad
    mov eax, [PM_TEAM1]
    mov edx, [PM_TEAM2]
    cmp eax, [SLOTS + 32]
    jne .fill
    cmp edx, [SLOTS + SLOT_ + 32]
    je .show                            ; same match: keep the edits
.fill:
    mov byte [KM_ACTIVE], 0
    mov byte [KM_TEAM], 0
    mov esi, eax
    mov edi, SLOTS
    call fill_slot
    mov esi, [PM_TEAM2]
    mov edi, SLOTS + SLOT_
    call fill_slot
.show:
    popad
    push dword [A6]
    mov dword [A6], KITS_MENU
    call SHOW_MENU
    pop dword [A6]
    ret

fill_slot:                              ; esi -> TeamFile, edi -> slot
    mov [edi + 32], esi
    push esi
    push edi
    add esi, 5                          ; teamName
    mov ecx, 17
    rep movsb
    mov byte [edi], 0
    pop edi
    pop esi
reset_kits:                             ; slot edi <- kits of its team file, first kit worn
    push esi
    push edi
    mov esi, [edi + 32]
    add esi, 26                         ; prShirtType .. secSocksColor
    add edi, 18
    mov ecx, 10
    rep movsb
    pop edi
    pop esi
    mov byte [edi + 28], 0
    ret

cur_slot:                               ; edi -> slot being edited, ebx -> the other one
    movzx eax, byte [KM_TEAM]
    imul edi, eax, SLOT_
    add edi, SLOTS
    xor eax, 1
    imul ebx, eax, SLOT_
    add ebx, SLOTS
    ret

km_init:                                ; SELECT KITS menu: init, and after every change
    pushad
    call cur_slot
    lea esi, [edi + 18]                 ; slot kits -> editTeamsTeam
    mov edi, EDIT_TEAM + 26
    mov ecx, 10
    rep movsb
    call PRIM_CONV
    call SEC_CONV
    call MARK1
    call MARK2
    push dword [D0]
    push dword [A0]
    call cur_slot                       ; CalcMenuEntryAddress clobbers eax, ebx, edx (mul bx)
    push ebx
    push edi
    mov dword [D0], 1                   ; team name
    call CALC
    mov esi, [A0]
    mov edi, [esp]
    mov [esi + 26h], edi
    mov dword [D0], 2                   ; kit worn
    call CALC
    mov esi, [A0]
    mov edi, [esp]
    movzx eax, byte [edi + 28]
    mov eax, [wear_text + eax * 4]
    mov [esi + 26h], eax
    mov dword [D0], 3                   ; the other team
    call CALC
    mov esi, [A0]
    mov dword [esi + 26h], OTHER_BUF
    pop edi
    pop ebx
    mov esi, ebx                        ; "NAME: KIT"
    mov edi, OTHER_BUF
.n: lodsb
    or al, al
    jz .e
    stosb
    jmp .n
.e: mov ax, ' :'
    xchg al, ah
    stosw
    movzx eax, byte [ebx + 28]
    mov esi, [kit_text + eax * 4]
.k: lodsb
    stosb
    or al, al
    jnz .k
    pop dword [A0]
    pop dword [D0]
    popad
    ret

save_kits:                              ; editTeamsTeam kits -> slot being edited
    call cur_slot
    lea edi, [edi + 18]
    mov esi, EDIT_TEAM + 26
    mov ecx, 10
    rep movsb
    ret

km_switch:                              ; entry 1: edit the other team
    pushad
    call save_kits
    xor byte [KM_TEAM], 1
    popad
    call km_init
    jmp DRAW_MENU

km_wear:                                ; entry 2: first / second kit
    pushad
    call save_kits
    call cur_slot
    xor byte [edi + 28], 1
    popad
    call km_init
    jmp DRAW_MENU

km_reset:                               ; entry 22: this team's kits from its team file
    pushad
    call cur_slot
    call reset_kits
    popad
    call km_init
    jmp DRAW_MENU

km_ok:                                  ; entry 21
    pushad
    call save_kits
    mov byte [KM_ACTIVE], 1
    mov esi, TXT_SET
    call set_button
    popad
    jmp SET_EXIT

km_cancel:                              ; entry 20
    pushad
    mov byte [KM_ACTIVE], 0
    mov dword [SLOTS + 32], 0           ; edits discarded
    mov esi, TXT_AUTO
    call set_button
    popad
    jmp SET_EXIT

set_button:                             ; esi -> text of the pre-match button
    mov edi, BTN_BUF
.c: lodsb
    stosb
    or al, al
    jnz .c
    ret

find_slot:                              ; esi -> TeamFile; out: edi -> slot with its name, or 0
    push ecx
    mov edi, SLOTS
    call .cmp
    je .ok
    mov edi, SLOTS + SLOT_
    call .cmp
    je .ok
    xor edi, edi
.ok:
    pop ecx
    ret
.cmp:
    push esi
    push edi
    add esi, 5
    mov ecx, 17
    repe cmpsb
    pop edi
    pop esi
    ret

apply_kit:                              ; edi -> slot, ecx -> topTeamInGame / bottomTeamInGame
    pushad
    movzx eax, byte [edi + 28]
    imul eax, eax, 5
    lea esi, [edi + 18 + eax]
    xor eax, eax
    lodsb
    mov [D0], eax
    lodsb
    mov [D0 + 4], eax
    lodsb
    mov [D0 + 8], eax
    lodsb
    mov [D0 + 12], eax
    lodsb
    mov [D0 + 16], eax
    mov [A0 + 4], ecx                   ; A1
    call CONVERT_KIT
    popad
    ret

pm_show:                                ; replaces `call ShowMenu` in ShowPlayMatchMenu ([A6] = playMatchMenu)
    pushad                              ; copy it now: SWOS++ patches the original in memory at start-up
    mov esi, [A6]
    mov edi, PM_COPY
    mov ecx, PM_LEN
    rep movsb
    mov byte [PM_COPY + E13_UP], KITS_
    mov dword [A6], PM_COPY
    popad
    jmp SHOW_MENU

kit_colors:                             ; replaces `mov eax, [A2]` at the start of SetInGameTeamsPrimaryColors
    cmp byte [KM_ACTIVE], 0
    je .auto
    pushad
    mov byte [KM_ACTIVE], 0             ; one match only
    mov dword [SLOTS + 32], 0           ; next KITS: start again from the team files
    mov esi, TXT_AUTO
    call set_button
    mov esi, [A2]
    call find_slot
    mov ebx, edi
    mov esi, [A2 + 4]                   ; A3
    call find_slot
    test ebx, ebx
    jz .none
    test edi, edi
    jz .none
    push edi
    mov edi, ebx
    mov ecx, TOP_TEAM
    call apply_kit
    pop edi
    mov ecx, BOTTOM_TEAM
    call apply_kit
    popad
    ret
.none:
    popad
.auto:
    mov eax, [A2]
    jmp SITPC + 5

align 4
wear_text: dd TXT_WEAR1, TXT_WEAR2
kit_text: dd TXT_K1, TXT_K2
"""


def _rel(d, c):
    return c + 5 + struct.unpack('<i', d[c + 1:c + 5])[0]


def _entries(menu, start, end):
    """Offsets of the packed entries in menu[start:end] (no -999 inside): {entry number: (entry offset, positions
    record offset or None)}, numbered from 0 at start."""
    out, k, n = {}, start, 0
    while k < end:
        w = struct.unpack_from('<h', menu, k)[0]
        if w == -998:
            k += 6
            continue
        assert w not in (-997, -996, -999), (k, w)
        e, pos = k, None
        k += 8
        while True:
            t = struct.unpack_from('<H', menu, k)[0]
            k += 2
            if t == 0:
                break
            assert t in PAYLOAD, (n, t)
            if t == 2:
                pos = k
            k += PAYLOAD[t]
        out[n] = (e, pos)
        n += 1
    assert k == end
    return out


def _fix_targets(p, obj, lo, hi):
    return [(o, t_obj, t_off) for (s_obj, o, _, t_obj, t_off, *_r) in p.le.fixups()
            if s_obj == obj and lo <= o < hi]


def button(p, at, lang, area):
    """KITS button + SELECT KITS menu; code and the playMatchMenu copy at obj1:at, data in obj2 area."""
    import nasmcave
    d = p.le.obj_bytes(1)
    d2 = p.le.obj_bytes(2)
    calls = {}
    for c in range(len(d) - 5):
        if d[c] == 0xE8:
            calls.setdefault(_rel(d, c), []).append(c)
    u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]
    # CalcMenuEntryAddress, D0/A0: from ShowUseMatchTeamIfTraining (mov word [D0], 5; call Calc; mov esi, [A0];
    # mov word [esi+4], 1; mov ax, [g_trainingGame]), the one called by SetVariableButtons after
    # SetGameStartButtonText; DrawMenu: TogglePlayerCoach ends with `call SetVariableButtons; jmp DrawMenu`.
    hits = []
    for m in re.finditer(rb'\x66\xC7\x05....\x05\x00\xE8....\x8B\x35....\x66\xC7\x46\x04\x01\x00\x66\xA1', d, re.S):
        for c in calls.get(m.start(), []):
            if d[c - 5] == 0xE8 and d[c + 5:c + 7] == b'\xff\x35' and d[c + 11:c + 13] == b'\xc7\x05' \
                    and d[c + 17:c + 21] == b'\x07\0\0\0':
                hits.append((m.start(), c - 5))
    assert len(hits) == 1, hits
    show_use, svb = hits[0]
    D0, A0 = u32(d, show_use + 3), u32(d, show_use + 16)
    assert p.target(1, show_use + 3) == (2, D0) and p.target(1, show_use + 16) == (2, A0)
    calc = _rel(d, show_use + 9)
    draw = {_rel(d, c + 5) for c in calls.get(svb, []) if d[c + 5] == 0xE9}
    assert len(calls[svb]) == 6 and len(draw) == 1, (len(calls[svb]), draw)
    # SetInGameTeamsPrimaryColors: mov eax,[A2]; mov [A0],eax; mov eax,[A3]; mov [A1],eax; 6 x push; call Measure...;
    # ... mov word [D7], 0; mov esi, [A6]; cmp byte [esi], 11; inc dword [A6]; jb SetInGameTeamColors
    m = [x.start() for x in re.finditer(rb'\xA1....\xA3....\xA1....\xA3....(\xFF\x35....){6}\xE8', d, re.S)]
    assert len(m) == 1, m
    sitpc = m[0]
    A2 = u32(d, sitpc + 1)
    assert A2 == A0 + 8 and u32(d, sitpc + 6) == A0
    j = re.compile(rb'\x66\xC7\x05(....)\x00\x00\x8B\x35(....)\x80\x3E\x0B\xFF\x05....\x0F\x82', re.S).search(d, sitpc, sitpc + 0x100)
    assert u32(d, j.start() + 3) == D0 + 28 and u32(d, j.start() + 11) == A0 + 24    # D7, A6
    set_colors = j.end() + 4 + struct.unpack('<i', d[j.end():j.end() + 4])[0]
    # SetInGameTeamColors: ... mov dword [A1], topTeamInGame; call ConvertTeamKitColors; ... mov [A1], bottomTeamInGame
    a1 = re.compile(rb'\xC7\x05' + re.escape(struct.pack('<I', A0 + 4)) + rb'(....)\xE8', re.S)
    tb = list(a1.finditer(d, set_colors, set_colors + 0x200))[:2]
    top, bottom = (p.target(1, x.start() + 6) for x in tb)
    convert = _rel(d, tb[0].end() - 1)
    assert convert == _rel(d, tb[1].end() - 1)
    # ShowPlayMatchMenu: mov eax,[A1]; mov [playMatchTeam1Ptr],eax; mov eax,[A2]; mov [playMatchTeam2Ptr],eax; ...
    # mov dword [A6], playMatchMenu; call ShowMenu
    pm = [x for x in re.finditer(rb'\xA1' + re.escape(struct.pack('<I', A0 + 4)) + rb'\xA3(....)\xA1'
                                 + re.escape(struct.pack('<I', A2)) + rb'\xA3(....)', d, re.S)]
    pm_menu_hs = [x.start() - 8 for x in re.finditer(re.escape(PM_MENU_HEAD), d2)]
    assert len(pm_menu_hs) == 1, pm_menu_hs
    start = pm_menu_hs[0]
    refs = [(f[0], f[1]) for f in p.le.fixups() if (f[3], f[4]) == (2, start)]
    assert len(refs) == 1 and refs[0][0] == 1, refs
    a6site = refs[0][1]
    assert u32(d, a6site - 4) == A0 + 24 and d[a6site + 4] == 0xE8
    show_menu = _rel(d, a6site + 4)
    pm = [x for x in pm if 0 < a6site - x.start() < 0x80]
    assert len(pm) == 1, pm
    pm1, pm2 = p.target(1, pm[0].start() + 6), p.target(1, pm[0].start() + 16)
    # SetExitMenuFlag: mov word [g_exitMenu], 1; ret (g_exitMenu: ShowMenu's `push [g_currentMenuPtr];
    # mov word [g_exitMenu], 0; call ActivateMenu`)
    x = re.compile(rb'\xFF\x35....\x66\xC7\x05(....)\x00\x00\xE8', re.S).search(d, show_menu, show_menu + 0x60)
    exit_flag = x.group(1)
    se = [y.start() for y in re.finditer(rb'\x66\xC7\x05' + re.escape(exit_flag) + rb'\x01\x00\xC3', d)]
    assert len(se) == 1, se
    set_exit = se[0]
    # editTeamsMenu: the kit entries 4..19 start with ET_KITS and end before ET_AFTER; entry 5's input function is
    # EditTeamsChangeShirtsPrimary (mov dword [A6], editTeamsTeam; ...). InitEditTeamsMenu calls
    # PrimaryKitColorConversion, SecondaryKitColorConversion, MarkFirstKitShirt, MarkSecondKitShirt in a row.
    ks = [x.start() for x in re.finditer(re.escape(ET_KITS), d2)]
    assert len(ks) == 1, ks
    k0 = ks[0]
    k1 = d2.find(ET_AFTER, k0)
    assert k0 < k1 < k0 + 0x400
    et_entries = _entries(d2, k0, k1)
    assert sorted(et_entries) == list(range(16))                        # = editTeamsMenu entries 4..19
    e5, pos5 = et_entries[1]
    in5 = pos5 + 4 + 2 + 2                                              # type 14: mask, function
    assert struct.unpack_from('<hH', d2, pos5 + 4) == (14, 0x3C1)
    change1 = p.target(2, in5)[1]
    assert d[change1:change1 + 6] == b'\xC7\x05' + struct.pack('<I', A0 + 24)
    edit_team = p.target(1, change1 + 6)
    starts_et = lambda t: d[t:t + 6] == b'\xC7\x05' + struct.pack('<I', A0 + 24) and \
        u32(d, t + 6) == edit_team[1]
    seq = [c for c in range(len(d) - 20) if all(d[c + 5 * i] == 0xE8 and starts_et(_rel(d, c + 5 * i)) for i in range(4))]
    assert len(seq) == 1, seq
    prim, sec, mark1, mark2 = (_rel(d, seq[0] + 5 * i) for i in range(4))
    T = TEXTS[lang]
    assert len(T['auto']) <= 12 and len(T['set']) <= 12

    # obj2 data: variables, slots, buffers, texts, then the SELECT KITS packed menu
    data = bytearray(4 + 2 * SLOT)                                      # active, team; two slots
    off = {}
    def put(name, b, size=None):
        off[name] = len(data)
        data.extend(b + b'\0' * ((size or len(b) + 1) - len(b)))
    put('btn', T['auto'], 16)
    put('other', b'', 40)
    put('empty', b'')
    for k in ('title', 'cancel', 'ok', 'reset', 'k1', 'k2', 'auto', 'set'):
        put(k, T[k])
    put('wear1', T['wears'] + T['k1'])
    put('wear2', T['wears'] + T['k2'])
    while len(data) % 4:
        data.append(0)
    menu_at = len(data)
    ptrs = []                                    # (offset in data, obj, target) — obj 1 targets filled after asm
    menu = bytearray(struct.pack('<IIII', 0, 0, 0, 1))                 # init (km_init), return, draw, default entry 1
    ptrs.append((menu_at + 0, 1, 'km_init'))
    def entry(x, y, w, h, nav=None, color=None, text=None, flags=0, select=None):
        b = bytearray(struct.pack('<hhhh', x, y, w, h))
        if nav:
            b += struct.pack('<H', 2) + bytes(v & 0xFF for v in nav)
        if color is not None:
            b += struct.pack('<HH', 4, color)
        if text is not None:
            b += struct.pack('<HH', 8, flags)
            ptrs.append((menu_at + len(menu) + len(b), 2, text))
            b += b'\0\0\0\0'
        if select is not None:
            b += struct.pack('<H', 13)
            ptrs.append((menu_at + len(menu) + len(b), 1, select))
            b += b'\0\0\0\0'
        menu.extend(b + b'\0\0')
    entry(0, 0, 193, 12, color=0x0A, text='title', flags=0x10)                                       # 0
    entry(0, 26, 193, 12, nav=(-1, 5, -1, 2), color=0x0B, text='empty', flags=0x10, select='km_switch')  # 1
    entry(0, 46, 193, 12, nav=(-1, 9, 1, 20), color=0x0E, text='empty', select='km_wear')             # 2
    entry(0, 66, 193, 10, text='empty')                                                              # 3
    kits = bytearray(d2[k0:k1])
    for o, t_obj, t_off in _fix_targets(p, 2, k0, k1):
        ptrs.append((menu_at + len(menu) + o - k0, t_obj, t_off))
    navfix = {1: (1, None, 1, None), 2: (2, None, None, None), 3: (2, None, None, None), 5: (2, None, None, None),
              6: (2, None, None, None), 7: (2, None, None, None), 8: (None, None, 1, None)}  # entries 5,6,7,9,10,11,12
    for n, (l, r, up, dn) in navfix.items():
        pos = et_entries[n][1]
        for i, v in enumerate((l, r, up, dn)):
            if v is not None:
                kits[pos - k0 + i] = v
    menu.extend(kits)
    menu.extend(struct.pack('<hhh', -998, 0, 0))
    entry(164, 185, 40, 15, nav=(-1, 22, 2, -1), color=0x0E, text='cancel', select='km_cancel')      # 20
    entry(264, 185, 40, 15, nav=(22, -1, 19, -1), color=0x0E, text='ok', select='km_ok')             # 21
    entry(214, 185, 40, 15, nav=(20, 21, 11, -1), color=0x0C, text='reset', select='km_reset')       # 22
    menu.extend(struct.pack('<h', -999))
    data.extend(menu)
    assert _entries(menu, 16, len(menu) - 2) is not None or True
    base = area.add(bytes(data))
    while any((base + o) // 0x1000 != (base + o + 3) // 0x1000 for o, _, _ in ptrs):
        raise AssertionError('KITS data: a pointer straddles a page')

    # playMatchMenu copy with entry 68 (text: the button buffer, fire: km_open), placed first in the cave. pm_show
    # refreshes its first PM_LEN bytes from the original at every pre-match screen (keeps SWOS++'s run-time patches of
    # the original: its onReturn and an entry pointer); the build-time copy and its fixups make it valid without that.
    end = d2.find(b'\0\0\x19\xfc' + PM_MENU_TAIL, start) + 2
    assert start < end < start + 0x1000
    pmc = bytearray(d2[start:end])
    e13 = pmc.find(PM_ENTRY13)
    assert e13 > 0 and pmc.count(PM_ENTRY13) == 1
    pmc[e13 + 12] = KITS_ENTRY                                           # first player: up -> KITS
    x_, y_, w_, h_ = BUTTON
    ent = struct.pack('<hhh', -998, 0, -20) + struct.pack('<hhhhH', x_, y_, w_, h_, 2) + bytes((0xFF, 0xFF, 0xFF, 13))
    ent += struct.pack('<HHHH', 4, BUTTON_COLOR, 8, 0)
    buf_at = len(pmc) + len(ent)
    ent += struct.pack('<IH', 0, 13)
    sel_at = len(pmc) + len(ent)
    ent += struct.pack('<IH', 0, 0)
    pm_len = end - start
    pmc += ent + struct.pack('<h', -999)
    pptrs = [(o - start, t_obj, t_off) for o, t_obj, t_off in _fix_targets(p, 2, start, end)]
    pptrs += [(buf_at, 2, 'btn'), (sel_at, 1, 'km_open')]
    mat = (at + 15) & ~15
    while any((mat + o) // 0x1000 != (mat + o + 3) // 0x1000 for o, _, _ in pptrs):
        mat += 4
    assert not any(d[mat:mat + len(pmc)])
    p.put(1, mat, bytes(pmc))
    at = (mat + len(pmc) + 15) & ~15

    sym = {'D0': (2, D0), 'A0': (2, A0), 'A2': (2, A2), 'A6': (2, A0 + 24), 'CALC': (1, calc), 'DRAW_MENU': (1, draw.pop()),
           'SET_COLORS': (1, set_colors), 'SITPC': (1, sitpc), 'TOP_TEAM': top, 'BOTTOM_TEAM': bottom,
           'CONVERT_KIT': (1, convert), 'PM_TEAM1': pm1, 'PM_TEAM2': pm2, 'SHOW_MENU': (1, show_menu),
           'SET_EXIT': (1, set_exit), 'EDIT_TEAM': edit_team, 'PRIM_CONV': (1, prim), 'SEC_CONV': (1, sec),
           'MARK1': (1, mark1), 'MARK2': (1, mark2), 'KM_ACTIVE': (2, base), 'KM_TEAM': (2, base + 1),
           'SLOTS': (2, base + 4), 'SLOT_': (0, SLOT), 'BTN_BUF': (2, base + off['btn']),
           'OTHER_BUF': (2, base + off['other']), 'KITS_MENU': (2, base + menu_at),
           'TXT_AUTO': (2, base + off['auto']), 'TXT_SET': (2, base + off['set']),
           'TXT_WEAR1': (2, base + off['wear1']), 'TXT_WEAR2': (2, base + off['wear2']),
           'TXT_K1': (2, base + off['k1']), 'TXT_K2': (2, base + off['k2']),
           'PM_COPY': (1, mat), 'PM_LEN': (0, pm_len), 'E13_UP': (0, e13 + 12), 'KITS_': (0, KITS_ENTRY)}
    code, fix = nasmcave.assemble(KITS_ASM, at, sym)
    lab = nasmcave.labels(KITS_ASM, at, sym)
    assert not any(d[at:at + len(code)])
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for o, t_obj, t in ptrs:
        if isinstance(t, str):
            t = lab[t] if t_obj == 1 else base + off[t]
        p.add_ptr(2, base + o, t_obj, t)
    for o, t_obj, t in pptrs:
        if isinstance(t, str):
            t = lab[t] if t_obj == 1 else base + off[t]
        p.add_ptr(1, mat + o, t_obj, t)
    assert d[a6site + 4] == 0xE8 and _rel(d, a6site + 4) == show_menu
    p.put(1, a6site + 5, struct.pack('<i', lab['pm_show'] - (a6site + 9)))
    assert p.get(1, sitpc, 1) == b'\xA1'
    p.remove(1, sitpc + 1)
    p.put(1, sitpc, b'\xE9' + struct.pack('<i', lab['kit_colors'] - (sitpc + 5)))

    print(f'exe: KITS: playMatchMenu obj2+{start:#x} -> obj1+{mat:#x} (+entry {KITS_ENTRY}, refreshed by pm_show), '
          f'SELECT KITS menu + data obj2+{base:#x} ({len(data)} B), code obj1+{at:#x} ({len(code)} B), '
          f'kit entries from obj2+{k0:#x}')
    return (at + len(code) + 15) & ~15
