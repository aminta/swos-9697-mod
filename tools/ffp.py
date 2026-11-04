"""4.0.6 (Marco via Davide): financial fair play - a career rule, ON for a new career, OFF for an older save (no 'FF'
item), switchable any time.

The ratio: W / I, W = the season's wage bill of the squad at the season start (dseg_D6B9E, the wages per match
charge, x dseg_D6CA2, the season's charges: what cseg_3D204 stores as dseg_D6BA2), I = the income of the season just
ended: its gate receipts (finance.py's fi_gate adds them to FF_INC: the game's gateReceipts is reset with every weekly
statement, cseg_5E2E0) + its sponsorship (sensisoftPlcSponsorship: the season-start deal + finance's TV / commercial
credit of every match charge; reset only by cseg_5DEB9) + the competition bonuses and the chairman's money
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

State: finance.py's FF_ST (FF_ON, FF_BLOCK, FF_VALID, FF_INC, FF_IPREV, FF_FINE), the engine item 'FF' (16 bytes).
FFP_FORCE=over (test builds only, modver TEST_VARS): the limit 0 (every evaluated season over).
"""
import os
import re
import struct

import nasmcave

LIMIT = 35                                   # W / I > 35 %
# the memo: two lines, as message 1 (%a = the manager, %b = the fine); the game's own font (German umlauts as its strings)
MEMO = {'it': ('SPIACENTE %a, GLI STIPENDI SUPERANO IL 35 PER CENTO',
               'DEI RICAVI: MULTA DI %b E STOP AGLI ACQUISTI'),
        'en': ('SORRY %a, OUR WAGES ARE OVER 35 PER CENT OF',
               'INCOME: WE ARE FINED %b AND CANNOT BUY PLAYERS'),
        'fr': ('DESOLE %a, LES SALAIRES DEPASSENT 35 POUR CENT',
               "DES RECETTES: AMENDE DE %b ET PLUS D'ACHATS"),
        'de': ('%a, DIE GEH\x8eLTER LIEGEN \x9aBER 35 PROZENT DER',
               'EINNAHMEN: %b STRAFE UND KEINE NEUEN SPIELER')}

ASM = r"""
ff_season:                              ; replaces InitializeNewSeason's `call cseg_5DEB9`
    push dword [SPONS]                  ; (the ending season's sponsorship: cseg_5DEB9 resets it)
    call PREV5DEB9
    pushad
    mov esi, REGS
    mov edi, FF_REGS
    mov ecx, 15
    rep movsd                           ; (the game's D0..A6 kept: the memo's menu uses them)
    mov ebx, [esp + 32]
    add ebx, [FF_INC]
    add ebx, [CBON]
    add ebx, [D6B88]                    ; ebx = I
    xor ecx, ecx
    mov [FF_INC], ecx
    mov [FF_FINE], ecx
    mov byte [FF_BLOCK], 0
    cmp word [STAY], 0
    jle .none                           ; a new career / club: no season of ours behind
    cmp byte [FF_VALID], 0
    je .none                            ; (an older save: its season not counted in full)
    mov [FF_IPREV], ebx
    cmp byte [FF_ON], 0
    je .done
    call ff_over
    jle .done
    mov byte [FF_BLOCK], 1
    shr eax, 1                          ; the fine: half the wages over the limit, in thousands
    xor edx, edx
    mov ecx, 1000
    div ecx
    imul eax, eax, 1000
    mov [FF_FINE], eax
    sub [NEWBAL], eax
    sub [OLDBAL], eax
    call ff_memo
    jmp .done
.none:
    mov [FF_IPREV], ecx
.done:
    mov byte [FF_VALID], 1
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
    jnz .big
    cmp eax, 7FFFFFFFh
    ja .big
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
.big:
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

align 4
FF_REGS: times 15 dd 0
FF_AMT: times 24 db 0
FF_L1: L1_DB
FF_L2: L2_DB
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
    sym = {k: s[k] for k in ('D2_', 'UNWILLING', 'BUYOK', 'CURMSG', 'SCM', 'STAY', 'PLNAME', 'TBL', 'INT2POUNDS', 'D0_',
                             'A1_', 'REGS', 'NEWBAL', 'OLDBAL', 'D6B88', 'CBON', 'SPONS', 'D6B9E', 'D6CA2')}
    sym['PREV5DEB9'] = p.call_target(1, s['season'])
    assert sym['PREV5DEB9'] == (1, s['F5DEB9']), ('InitializeNewSeason: cseg_5DEB9 call already hooked', sym['PREV5DEB9'])
    sym['LIMIT_'] = (0, 0 if os.environ.get('FFP_FORCE') == 'over' else LIMIT)
    for k in ('FF_ON', 'FF_BLOCK', 'FF_VALID', 'FF_INC', 'FF_IPREV', 'FF_FINE'):
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
    engine.ITEM_AT['FF'] = (3, finance.LABELS['FF_ST'])
    engine.CALL_AT['ff_new'] = (3, lab['ff_new'])
    LABELS.clear()
    LABELS.update(lab)
    print(f'exe: financial fair play (W/I > {sym["LIMIT_"][1]} %: purchases blocked + fine; memo {px(l1.replace("%a", ""))}/'
          f'{px(l2.replace("%b", ""))} px): code obj3+{at:#x} ({len(code)} B), state FF_ST obj3+{finance.LABELS["FF_ST"]:#x}, sites obj1+{s["buy"]:#x} / +{s["season"]:#x}')
    return at + len(code)


LABELS = {}
