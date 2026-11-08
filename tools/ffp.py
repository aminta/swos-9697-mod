"""4.0.6 (Marco via Davide): financial fair play - a career rule, ON for a new career, OFF for an older save (no 'FF'
item), switchable any time.

The ratio: W / I, W = the season's wage bill of the squad at the season start (dseg_D6B9E, the wages per match
charge, x dseg_D6CA2, the season's charges: what cseg_3D204 stores as dseg_D6BA2), I = the income of the season just
ended: its gate receipts (finance.py's fi_gate adds them to FF_INC: the game's gateReceipts is reset with every weekly
statement, cseg_5E2E0) + its sponsorship (sensisoftPlcSponsorship: the season-start deal + finance's TV / commercial
credit of every match charge; reset only by cseg_5DEB9) less that credit's wage-linked share (1.1 x the wages: it
grows with every purchase, so W / I would hardly move - Davide 04/11, option B; FF_TVW counts it) + the competition bonuses and the chairman's money
(dseg_D6B88 = startingBalance) that cseg_5DEB9 pays for it. The limit: W x 100 > LIMIT x I.

The season start (InitializeNewSeason's `call cseg_5DEB9`, chained): the sponsorship is read before the call, the rest
after it (the new wages and bonuses computed). A club that played the season behind it (stayingInOldClub > 0) with a
whole season counted (FF_VALID) and the rule ON: over the limit = FF_BLOCK (the season's purchases refused while still
over) + the fine 0.5 x (W - LIMIT / 100 x I) (Davide 02/11, rounded down to 1000) off newBalance and old_balance (the
season-start statement stays old + rows = new), and the chairman's memo: the game's ShowChairmanMessage with message
1's two line pointers swapped for ours for the call (%b = the fine, the game's Int2Pounds), then put back. Under the
limit: no block, nothing. A new career / club (stayingInOldClub 0) or a save loaded mid-season (FF_VALID 0): no
evaluation, the count starts now. OFF: the same counts, no block, no fine, no memo.

The purchases (BuyPlayerMenu's `cmp word [D2], 2 / jnb`: the game's own refusal, 'unwilling to make any further
player purchases this season' - message 1 in every language): also when FF_BLOCK and the current squad's W is over
the limit of FF_IPREV (sold back under it: buying again).

State: finance.py's FF_ST (FF_ON, FF_BLOCK, FF_VALID, FF_INC, FF_IPREV, FF_FINE, FF_TVW, FF_NCH), the engine item 'FF' (21 bytes).
FFP_FORCE=over (test builds only, modver TEST_VARS): the limit 0 (every evaluated season over).
"""
import os
import re
import struct

import nasmcave

LIMIT = 40                                   # W / I > 40 % (Davide 05/11; 35 % sanctioned one star at a big club)
# the memo: two lines, as message 1 (%a = the manager, %b = the fine); the game's own font (German umlauts as its strings)
# ANDAMENTO CLUB's row (ratio W / last season's I) and the season-start statement's fine row (Davide 04/11)
RATIO = {'it': 'STIPENDI/RICAVI ', 'en': 'WAGES/INCOME ', 'fr': 'SALAIRES/RECETTES ', 'de': 'GEH\x8eLTER/EINNAHMEN '}
FINE = {'it': 'MULTA FAIR PLAY FINANZ.:', 'en': 'FINANCIAL FAIR PLAY FINE:', 'fr': 'AMENDE FAIR-PLAY FINANCIER:',
        'de': 'STRAFE FINANZ. FAIRPLAY:'}
MEMO = {'it': ('SPIACENTE %a, GLI STIPENDI SUPERANO IL 40 PER CENTO',
               'DEI RICAVI: MULTA DI %b E STOP AGLI ACQUISTI'),
        'en': ('SORRY %a, OUR WAGES ARE OVER 40 PER CENT OF',
               'INCOME: WE ARE FINED %b AND CANNOT BUY PLAYERS'),
        'fr': ('DESOLE %a, LES SALAIRES DEPASSENT 40 POUR CENT',
               "DES RECETTES: AMENDE DE %b ET PLUS D'ACHATS"),
        'de': ('%a, DIE GEH\x8eLTER LIEGEN \x9aBER 40 PROZENT DER',
               'EINNAHMEN: %b STRAFE UND KEINE NEUEN SPIELER')}

ASM = r"""
ff_season:                              ; replaces InitializeNewSeason's `call cseg_5DEB9`
    push dword [SPONS]                  ; (the ending season's sponsorship: cseg_5DEB9 resets it)
    pushad                              ; W = the wage bill at the season's end, before cseg_5DEB9 prices the squad again
    movzx ecx, word [FF_NCH]            ; (Davide 04/11, C): its wages per charge x ITS charges (D6CA2 is the new season's
    test ecx, ecx                       ; by now; an older save: no count kept - the new one)
    jnz .nch
    movzx ecx, word [D6CA2]
.nch:
    mov eax, [D6B9E]
    mul ecx
    test edx, edx
    jz .wend
    mov eax, 7FFFFFFFh
.wend:
    mov [FF_WEND], eax
    popad
    call PREV5DEB9
    pushad
    mov esi, REGS
    mov edi, FF_REGS
    mov ecx, 15
    rep movsd                           ; (the game's D0..A6 kept: the memo's menu uses them)
    mov ebx, [esp + 32]
    add ebx, [FF_INC]
    sub ebx, [FF_TVW]                   ; (Davide 04/11, B: not the TV share that pays for the wages)
    add ebx, [CBON]
    add ebx, [D6B88]                    ; ebx = I
    xor ecx, ecx
    mov [FF_INC], ecx
    mov [FF_TVW], ecx
    mov [FF_FINE], ecx
    mov byte [FF_BLOCK], 0
    cmp word [STAY], 0
    jle .none                           ; a new career / club: no season of ours behind
    cmp byte [FF_VALID], 0
    je .none                            ; (an older save: its season not counted in full)
    mov [FF_IPREV], ebx
    cmp byte [FF_ON], 0
    je .done
    mov eax, [FF_WEND]
    call ff_overw
    jle .done
    mov byte [FF_BLOCK], 1
    shr eax, 1                          ; the fine: half the wages over the limit, in thousands
    xor edx, edx
    mov ecx, 1000
    div ecx
    imul eax, eax, 1000
    mov [FF_FINE], eax
    sub [NEWBAL], eax                   ; (the season-start statement's own row: ff_biz)
    call ff_memo
    jmp .done
.none:
    mov [FF_IPREV], ecx
.done:
    mov byte [FF_VALID], 1
    mov ax, [D6CA2]                     ; (this season's charges: next season start's W)
    mov [FF_NCH], ax
    mov esi, FF_REGS
    mov edi, REGS
    mov ecx, 15
    rep movsd
    popad
    add esp, 4
    ret

ff_over:                                ; eax = W - LIMIT / 100 x FF_IPREV, flags: jg = over (W = the squad's wages now)
    mov eax, [D6B9E]
    movzx ecx, word [D6CA2]
    mul ecx
    test edx, edx
    jnz ff_big
ff_overw:                               ; (W given in eax)
    cmp eax, 7FFFFFFFh
    ja ff_big
    mov esi, eax
    mov eax, [FF_IPREV]
    mov ecx, LIMIT_
    mul ecx
    mov ecx, 100
    div ecx
    sub esi, eax
    mov eax, esi
    test eax, eax
    ret
ff_big:
    mov eax, 7FFFFFFFh
    test eax, eax
    ret

ff_memo:                                ; the chairman's memo: message 1 with our lines for this one call
    mov dword [A1_], FF_AMT
    mov eax, [FF_FINE]
    mov [D0_], eax
    call INT2POUNDS
    push dword [TBL]
    push dword [TBL + 4]
    push dword [PLNAME]
    movzx eax, word [CURMSG]
    push eax
    mov dword [TBL], FF_L1
    mov dword [TBL + 4], FF_L2
    mov dword [PLNAME], FF_AMT
    mov word [CURMSG], 1
    call SCM
    pop eax
    mov [CURMSG], ax
    pop dword [PLNAME]
    pop dword [TBL + 4]
    pop dword [TBL]
    ret

ff_buy:                                 ; replaces BuyPlayerMenu's `cmp word [D2], 2 / jnb ok`
    cmp word [D2_], 2
    jb UNWILLING                        ; (the game's: no room in the squad)
    cmp byte [FF_ON], 0
    je BUYOK
    cmp byte [FF_BLOCK], 0
    je BUYOK
    pushad
    call ff_over
    popad                               ; (flags kept)
    jg UNWILLING
    jmp BUYOK

ff_new:                                 ; a new career (engine.after_new, its items zeroed): the rule ON, counted
    mov byte [FF_ON], 1                 ; from its first season
    mov byte [FF_VALID], 1
    ret

ff_biz:                                 ; clubBusinessMenu's init (ANDAMENTO CLUB, every statement): the game's, then ours
    call BIZINIT
    pushad
    mov ebx, MENU_
    cmp word [ebx + 10h], 22            ; (the game's 22 entries, then their texts - STDMENUTEXT - up to the end pointer)
    jne .x
    lea eax, [ebx + 16h + 22 * 38h]
    mov edx, [ebx + 12h]
    cmp edx, eax
    jb .x
    add edx, 2 * 38h
    lea ecx, [ebx + MENUSZ_]
    cmp edx, ecx
    ja .x                               ; (no room for two more entries)
    cmp word [D6CA0], 0                 ; a season-start statement of the club staying, with a fine: its row
    jne .row
    cmp word [STAY], 0
    je .row
    cmp dword [FF_FINE], 0
    je .row
    lea esi, [ebx + 16h + 9 * 38h]      ; entries 9 / 19 (the wages, hidden here): the fine, a row under the purchases
    mov word [esi + 4], 0
    mov dword [esi + 26h], FF_FL
    mov ax, [ebx + 16h + 8 * 38h + 16h]
    add ax, 15
    mov [esi + 16h], ax
    lea esi, [ebx + 16h + 19 * 38h]
    mov word [esi + 4], 0
    mov ax, [ebx + 16h + 18 * 38h + 16h]
    add ax, 15
    mov [esi + 16h], ax
    mov eax, [esi + 26h]
    mov [A1_], eax
    mov eax, [FF_FINE]
    neg eax
    mov [D0_], eax
    call WRITEBAL
    mov ebx, MENU_
    add word [ebx + 16h + 10 * 38h + 16h], 10    ; the total and the new balance 10 px down
    add word [ebx + 16h + 11 * 38h + 16h], 10
    add word [ebx + 16h + 20 * 38h + 16h], 10
    add word [ebx + 16h + 21 * 38h + 16h], 10
    mov eax, [NEWBAL]                   ; the total with the fine: new - old
    sub eax, [OLDBAL]
    jns .tot
    mov dword [ebx + 16h + 10 * 38h + 26h], TOTLOSS
.tot:
    mov ecx, [ebx + 16h + 20 * 38h + 26h]
    mov [A1_], ecx
    mov [D0_], eax
    call WRITEBAL
    mov ebx, MENU_
.row:
    lea eax, [ebx + 16h + 22 * 38h]     ; the texts 2 entries further: room for entries 22 / 23
    mov ecx, [ebx + 12h]
    sub ecx, eax
    jz .moved
    mov esi, [ebx + 12h]
    dec esi
    lea edi, [esi + 2 * 38h]
    std
    rep movsb
    cld
    lea esi, [ebx + 16h]                ; (the entries' text pointers into the moved area: moved too)
    mov ecx, 22
.fix:
    mov edx, [esi + 26h]
    cmp edx, eax
    jb .nf
    cmp edx, [ebx + 12h]
    jae .nf
    add dword [esi + 26h], 2 * 38h
.nf:
    add esi, 38h
    loop .fix
.moved:
    lea edi, [ebx + 16h + 22 * 38h]     ; entry 22: the ratio (a copy of the old balance's label, 15 px above it)
    lea esi, [ebx + 16h + 2 * 38h]
    mov ecx, 38h
    rep movsb
    lea edi, [ebx + 16h + 22 * 38h]
    mov word [edi + 2], 22
    mov word [edi + 4], 0
    sub word [edi + 16h], 15
    mov dword [edi + 26h], FF_RATIO
    lea edi, [ebx + 16h + 23 * 38h]     ; entry 23: the switch (a copy of CONTINUA, in the new balance's box)
    lea esi, [ebx + 16h + 1 * 38h]
    mov ecx, 38h
    rep movsb
    lea edi, [ebx + 16h + 23 * 38h]
    mov word [edi + 2], 23
    mov word [edi + 4], 0
    mov ax, [ebx + 16h + 21 * 38h + 14h]
    mov [edi + 14h], ax
    mov ax, [ebx + 16h + 22 * 38h + 16h]
    dec ax
    mov [edi + 16h], ax
    mov ax, [ebx + 16h + 21 * 38h + 18h]
    mov [edi + 18h], ax
    mov ax, [ebx + 16h + 21 * 38h + 1Ah]
    mov [edi + 1Ah], ax
    mov dword [edi + 2Ah], ff_tog
    mov word [edi + 0Ah], 01FFh         ; (up: none, down: CONTINUA)
    mov word [edi + 12h], 01FFh
    mov byte [ebx + 16h + 1 * 38h + 0Ah], 23    ; (CONTINUA's up: the switch)
    mov byte [ebx + 16h + 1 * 38h + 12h], 23
    call ff_sval
    mov word [ebx + 10h], 24
    add dword [ebx + 12h], 2 * 38h
    call ff_ratio
.x: popad
    ret

ff_sval:                                ; the switch's text: the game's ON / OFF
    mov eax, S_OFF
    cmp byte [FF_ON], 0
    je .s
    mov eax, S_ON
.s: mov [MENU_ + 16h + 23 * 38h + 26h], eax
    ret

ff_tog:                                 ; fire on the switch: the rule ON / OFF for this career
    xor byte [FF_ON], 1
    pushad
    call ff_sval
    popad
    jmp DRAWITEM

ff_ratio:                               ; FF_RATIO = RATIO[lang] + W x 100 / last season's I '%' (or '--') + ' (MAX nn%)'
    mov edi, FF_RATIO
    mov esi, FF_RPRE
.p: lodsb
    test al, al
    jz .n
    stosb
    jmp .p
.n: mov ecx, [FF_IPREV]
    test ecx, ecx
    jz .none
    mov eax, [D6B9E]
    movzx ebx, word [D6CA2]
    mul ebx
    mov ebx, 100
    test edx, edx
    jnz .cap
    mul ebx                             ; edx:eax = W x 100
    cmp edx, ecx
    jae .cap
    div ecx
    cmp eax, 999
    jbe .num
.cap:
    mov eax, 999
.num:
    xor ecx, ecx                        ; the digits, most significant first
    mov ebx, 10
.d: xor edx, edx
    div ebx
    push edx
    inc ecx
    test eax, eax
    jnz .d
.o: pop eax
    add al, '0'
    stosb
    loop .o
    mov al, '%'
    stosb
    jmp .suf
.none:
    mov ax, '--'
    stosw
.suf:
    mov esi, FF_RSUF
.q: lodsb
    stosb
    test al, al
    jnz .q
    ret

align 4
FF_WEND: dd 0                           ; (the season-end W, between ff_season's two halves)
FF_REGS: times 15 dd 0
FF_AMT: times 24 db 0
FF_L1: L1_DB
FF_L2: L2_DB
FF_FL: FL_DB
FF_RPRE: RP_DB
FF_RSUF: RS_DB
FF_RATIO: times 48 db 0
"""


def find(p):
    """BuyPlayerMenu's squad-room test, InitializeNewSeason's `call cseg_5DEB9` (before `call cseg_3D204`),
    stayingInOldClub, ShowChairmanMessage, currentMessage, clubMessagesTable, plNameForMessage, Int2Pounds."""
    import finance
    import sacups
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    s = finance.SITES or finance.find(p)
    bp = [m.start() for m in re.finditer(rb'\xe8....\x66\x83\x3d....\x02\x73.\x66\xc7\x05....\x01\x00\xe9', d, re.S)]
    assert len(bp) == 1, bp
    b = bp[0]
    out = {'buy': b + 5, 'D2_': p.target(1, b + 7 + 1), 'UNWILLING': (1, b + 15), 'BUYOK': (1, b + 15 + d[b + 14]),
           'CURMSG': p.target(1, b + 18)}
    assert d[b + 14] < 0x80
    scm = b + 29 + struct.unpack_from('<i', d, b + 25)[0]
    out['SCM'] = (1, scm)
    cf = [i for i in range(len(d)) if d.startswith(bytes.fromhex('66bbcf0066f7e3'), i)]
    assert len(cf) == 1, cf
    st = next(i for i in range(cf[0], cf[0] - 0x300, -1) if all(d[i + 6 * k:i + 6 * k + 2] == b'\xff\x35' for k in range(15)))
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    calls = [i for i in range(len(d) - 5) if d[i] == 0xE8 and rel(i) == st]
    assert len(calls) == 1 and d[calls[0] - 5] == 0xE8, calls      # cseg_3D204's one caller, cseg_5DEB9 just before
    out['season'] = calls[0] - 5
    out['F5DEB9'] = rel(calls[0] - 5)
    b88 = struct.pack('<I', s['D6B88'][1])
    sy = [m for m in re.finditer(rb'\x66\xa1(....)\x66\x0b\xc0\x75.\xa1', d[st:st + 0x400], re.S)
          if p.target(1, st + m.end()) == s['D6B88']]
    assert len(sy) == 1, len(sy)                            # `mov ax, [stayingInOldClub] / or / jnz / mov eax, [D6B88]`
    out['STAY'] = p.target(1, st + sy[0].start() + 2)
    A2, A3, A5 = r['A0'] + 8, r['A0'] + 12, r['A0'] + 20
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', A2)) + rb'....\xa1....\xa3' +
                                        re.escape(struct.pack('<I', A3)), d, re.S) if scm < x.start() < scm + 0x300]
    assert len(m) == 2, m                                   # ChairmanMemosOnReturn's two lines
    out['PLNAME'] = p.target(1, m[0] + 11)
    t = [x.start() for x in re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', A5)), d[scm:m[0]])]
    out['TBL'] = p.target(1, scm + t[-1] + 6)
    wb = s['WRITEBAL'][1]
    assert d[wb] == 0xA1 and d[wb + 5:wb + 7] == b'\x0b\xc0' and d[wb + 7] == 0x78 and d[wb + 9] == 0x74, d[wb:wb + 12].hex()
    out['INT2POUNDS'] = (1, wb + 11 + struct.unpack_from('<b', d, wb + 10)[0])   # (before it: a negative rel8)
    out.update({'D0_': s['D0'], 'A1_': s['A1'], 'REGS': (2, r['D7'] - 28)})
    assert r['A0'] == r['D7'] + 4, 'D0 .. D7, A0 .. A6 contiguous'
    nb = s['NEWBAL']
    out.update({'NEWBAL': nb, 'OLDBAL': (2, nb[1] + 4), 'D6B88': s['D6B88'], 'CBON': (2, s['D6B88'][1] + 4),
                'SPONS': s['SPONS'], 'D6B9E': s['D6B9E'], 'D6CA2': s['D6CA2']})
    stay = struct.pack('<I', out['STAY'][1])
    bz = [m.start() for m in re.finditer(rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1' + re.escape(stay) +
                                         rb'\x66\x0b\xc0\x0f\x84', d, re.S)]
    bz = [x for x in bz if p.target(1, x + 13) == out['STAY']]
    assert len(bz) == 1, bz                              # ClubBusinessInit: `mov ax, [D6CA0] / or / jnz / mov ax,
    out['BIZINIT'] = (1, bz[0])                          # [stayingInOldClub] / or / jz new club`
    out['D6CA0'] = p.target(1, bz[0] + 2)
    hdr = [s_ for so, s_, _, t, o, *_ in p.le.fixups() if so == 2 and t == 1 and o == bz[0]]
    assert len(hdr) == 1, hdr                            # clubBusinessMenu's init pointer
    out['bizhdr'] = hdr[0]
    tl = [i for i in range(bz[0], bz[0] + 0x300) if d[i:i + 3] == b'\xc7\x46\x26']
    out['TOTLOSS'] = p.target(1, tl[0] + 3)              # (the first `mov [esi+38], offset aTotalLoss`)
    return out


def message(p, k):
    """The game's chairman message k (1 = 'unwilling to make any further player purchases'): its two lines, without the
    '*' room marks (an original exe)."""
    t = find(p)['TBL'][1]
    fx = {(so, s_): o for so, s_, _, tt, o, *_ in p.le.fixups()}
    d2 = p.le.obj_bytes(2)
    return [d2[o:d2.index(b'\0', o)].decode('latin-1').rstrip('*') for o in (fx[(2, t + 8 * (k - 1) + j)] for j in (0, 4))]


def patch(p, at, lang):
    """Code at obj3:at (finance.py, already patched, holds the state); returns the end."""
    import engine
    import finance
    from complist import px
    s = find(p)
    d = p.le.obj_bytes(1)
    assert p.get(1, s['buy'], 10) == d[s['buy']:s['buy'] + 10], 'BuyPlayerMenu site already patched'
    l1, l2 = MEMO[lang]
    db = lambda x: 'db ' + ', '.join(str(c) for c in x.encode('latin1') + b'\0')
    src = nasmcave.sub(nasmcave.sub(ASM, 'L1_DB', db(l1)), 'L2_DB', db(l2))
    for k, t in (('FL_DB', FINE[lang]), ('RP_DB', RATIO[lang]), ('RS_DB', f' (MAX {LIMIT}%)')):
        src = nasmcave.sub(src, k, db(t))
    sym = {k: s[k] for k in ('D2_', 'UNWILLING', 'BUYOK', 'CURMSG', 'SCM', 'STAY', 'PLNAME', 'TBL', 'INT2POUNDS', 'D0_',
                             'A1_', 'REGS', 'NEWBAL', 'OLDBAL', 'D6B88', 'CBON', 'SPONS', 'D6B9E', 'D6CA2', 'BIZINIT',
                             'D6CA0', 'TOTLOSS')}
    import controls
    import cpucards
    import zones
    sym['WRITEBAL'] = finance.SITES['WRITEBAL']
    sym['MENU_'] = zones._current_menu(p)
    sym['MENUSZ_'] = (0, 6500)                           # (g_currentMenu's size: cpucards)
    sym['DRAWITEM'] = (1, cpucards.find(p)['DRAWITEM'])
    sym['S_OFF'], sym['S_ON'] = cpucards.strings(p, controls.menu_header(p, controls.locate(p)['OMBD'][1]))
    assert p.target(2, s['bizhdr']) == s['BIZINIT'], ('clubBusinessMenu init already hooked', p.target(2, s['bizhdr']))
    for t in (RATIO[lang], FINE[lang]):
        assert re.fullmatch(r"[A-Z0-9 /.:'\x8e\x99\x9a-]+" if lang == 'de' else r"[A-Z0-9 /.:'-]+", t), t   # (DE umlauts)
    sym['PREV5DEB9'] = p.call_target(1, s['season'])
    assert sym['PREV5DEB9'] == (1, s['F5DEB9']), ('InitializeNewSeason: cseg_5DEB9 call already hooked', sym['PREV5DEB9'])
    sym['LIMIT_'] = (0, 0 if os.environ.get('FFP_FORCE') == 'over' else LIMIT)
    for k in ('FF_ON', 'FF_BLOCK', 'FF_VALID', 'FF_INC', 'FF_IPREV', 'FF_FINE', 'FF_TVW', 'FF_NCH'):
        sym[k] = (3, finance.LABELS[k])
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['buy'] + 3)                            # (the overwritten `cmp word [D2], 2`'s fixup)
    p.branch(1, s['buy'], 0xE9, 3, lab['ff_buy'], 10)
    p.branch(1, s['season'], 0xE8, 3, lab['ff_season'])
    p.retarget(2, s['bizhdr'], 3, lab['ff_biz'])
    p.put(2, s['bizhdr'], struct.pack('<I', lab['ff_biz']))
    engine.ITEM_AT['FF'] = (3, finance.LABELS['FF_ST'])
    engine.CALL_AT['ff_new'] = (3, lab['ff_new'])
    LABELS.clear()
    LABELS.update(lab)
    print(f'exe: financial fair play (W/I > {sym["LIMIT_"][1]} %: purchases blocked + fine; memo {px(l1.replace("%a", ""))}/'
          f'{px(l2.replace("%b", ""))} px): code obj3+{at:#x} ({len(code)} B), state FF_ST obj3+{finance.LABELS["FF_ST"]:#x}, sites obj1+{s["buy"]:#x} / +{s["season"]:#x}')
    return at + len(code)


LABELS = {}
