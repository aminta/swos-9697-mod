"""4.0.5 the international cups' goals on CAPO CANNONIERI NAZIONALE (Luigi's report, Davide 31/10: TOT larger than
LEGA + COP1 + COP2). A player record has four goal counters (+33..+36: league, cup 1, cup 2, the international cups;
a match adds its goals at +33 + the contest's DIY +2Bh) and InitHighestScorersTable's total is their sum, but the
game's screen (topGoalScorersMenu, TopGoalScorersBeforeDrawCommon) draws only the first three - so the European /
continental goals were in TOT without a column (the original game's behaviour). Now a fifth column INT between COP2 and
TOT, headed with the game's own word for them (the squad screens' INT / DE 'INT.').

- The menu (obj2, packed, frozen pages: bytes changed in place only): the columns 14 px apart instead of 15 - LEGA /
  COP1 / COP2 headers and row entries at x 236 / 250 / 264, TOT stays at 292, INT drawn at 278 -, the team entry 4 px
  narrower (139 + 96 = 235).
- The rows: one 6-entry template (name, team, LEGA, COP1, COP2, TOT) that the before-draw function fills and draws
  for each row with a tail `jmp DrawMultipleItems` (A5 = its first entry, D0 = 6). That jump -> sc_draw: the row, then
  the TOT entry drawn once more at INT's x with INT = TOT - LEGA - the cup columns shown (a hidden cup column: the
  country has no such cup, its counter is 0), then the TOT header entry the same way with the INT text; both entries
  restored, the game's D0..A6 kept.
"""
import re
import struct

import nasmcave
import sacups

X_LEGA, X_COP1, X_COP2, X_INT, X_TOT = 236, 250, 264, 278, 292
HDR = {'de': b'INT.'}                   # (the game's own word: the squad screen's column, per exe language)
LOG = []

ASM = r"""
sc_draw:                                ; TopGoalScorersBeforeDrawCommon's `jmp DrawMultipleItems` (A5 = the row's first
    mov eax, [A5_]                      ; entry - name, team, LEGA, COP1, COP2, TOT - D0 = 6)
    mov [sc_ent], eax
    call DRAWMULTI
    pushad
    sub esp, 60                         ; the game's D0..D7, A0..A6 are memory: keep them
    mov esi, D0_
    mov edi, esp
    mov ecx, 15
    rep movsd
    mov ebx, [sc_ent]
    lea esi, [ebx + 5 * 38h]            ; TOT
    mov ax, [esi + 26h]
    sub ax, [ebx + 2 * 38h + 26h]       ; - LEGA
    cmp word [ebx + 3 * 38h + 4], 0
    jne .c1
    sub ax, [ebx + 3 * 38h + 26h]       ; - COP1 (shown)
.c1:
    cmp word [ebx + 4 * 38h + 4], 0
    jne .c2
    sub ax, [ebx + 4 * 38h + 26h]       ; - COP2 (shown)
.c2:
    jns .v
    xor eax, eax
.v:
    push word [esi + 14h]
    push word [esi + 26h]
    mov [esi + 26h], ax
    sub word [esi + 14h], XD_          ; (relative: the unpacked x holds the menu's offset)
    mov [A5_], esi
    call DRAWITEM
    mov esi, [sc_ent]
    lea esi, [esi + 5 * 38h]
    pop word [esi + 26h]
    pop word [esi + 14h]
    mov esi, [sc_ent]                   ; the header: TOT's (entry 4 = the row's first - 17), INT's text
    sub esi, 17 * 38h
    push word [esi + 14h]
    push dword [esi + 26h]
    sub word [esi + 14h], XD_          ; (relative: the unpacked x holds the menu's offset)
    mov dword [esi + 26h], SC_HDR
    mov [A5_], esi
    call DRAWITEM
    mov esi, [sc_ent]
    sub esi, 17 * 38h
    pop dword [esi + 26h]
    pop word [esi + 14h]
    mov esi, esp
    mov edi, D0_
    mov ecx, 15
    rep movsd
    add esp, 60
    popad
    ret
sc_ent: dd 0
"""


def find(p):
    """The original exe's sites: the menu's packed entries (obj2), the hook's jump and DrawMultipleItems / DrawMenuItem
    (obj1)."""
    d1 = p.le.obj_bytes(1)
    d2 = p.le.obj_bytes(2)
    r = sacups.regs(d1)
    D0, A0 = r['D7'] - 28, r['A0']
    assert A0 == D0 + 32, (hex(D0), hex(A0))
    A5 = A0 + 20
    P = lambda a: re.escape(struct.pack('<I', a))
    hw = lambda *v: re.escape(struct.pack('<' + 'h' * len(v), *v))
    # the headers: x, 18, 12, 24, type 11 (multi-line text), flags 0, dd text, end - LEGA / COP1 / COP2 / TOT in a row
    hdr = [m.start() for m in re.finditer(hw(247, 18, 12, 24, 11, 0) + rb'....\x00\x00' + hw(262, 18, 12, 24, 11, 0) +
                                          rb'....\x00\x00' + hw(277, 18, 12, 24, 11, 0) + rb'....\x00\x00' +
                                          hw(292, 18, 12, 24, 11, 0), d2, re.S)]
    assert len(hdr) == 1, ('headers', hdr)
    # the row: team (139, 0, 100, 8, type 8, 8000h, dd -1, end), then the numbers x, 0, 12, 8, type 12, 0, n, end
    row = [m.start() for m in re.finditer(hw(139, 0, 100, 8, 8, -0x8000) + rb'\xff\xff\xff\xff\x00\x00' +
                                          hw(247, 0, 12, 8, 12, 0, 22, 0, 262, 0, 12, 8, 12, 0, 33, 0,
                                             277, 0, 12, 8, 12, 0, 44, 0, 292, 0, 12, 8, 12, 0, 77, 0), d2, re.S)]
    assert len(row) == 1, ('row', row)
    # the hook (TopGoalScorersBeforeDrawCommon lives in obj2): push [D0]; mov dword [D0], 15h; call
    # CalcMenuEntryAddress; pop [D0]; mov eax, [A0]; xchg eax, [A5]; mov [A0], eax; mov word [D0], 6; jmp
    # DrawMultipleItems (obj2 -> obj1: a self-relative fixup)
    hk = [m.start() + 46 for m in re.finditer(rb'\xc7\x05' + P(D0) + rb'\x15\x00\x00\x00\xe8....\x8f\x05' + P(D0) +
                                              rb'\xa1' + P(A0) + rb'\x87\x05' + P(A5) + rb'\xa3' + P(A0) +
                                              rb'\x66\xc7\x05' + P(D0) + rb'\x06\x00\xe9', d2, re.S)]
    assert len(hk) == 1, ('the row draw', hk)
    tobj, dm = p.target(2, hk[0] + 1)
    assert tobj == 1, tobj
    # DrawMultipleItems: push [D0]; push [A5]; call DrawBackAllItems; pop; pop; sub word [D0], 1; push [D0];
    # push [A5]; call DrawMenuItem; pop; pop; add dword [A5], 38h; dec word [D0]; jns; retn
    assert re.match(rb'\xff\x35' + P(D0) + rb'\xff\x35' + P(A5) + rb'\xe8....\x8f\x05' + P(A5) + rb'\x8f\x05' + P(D0) +
                    rb'\x66\x83\x2d' + P(D0) + rb'\x01\xff\x35' + P(D0) + rb'\xff\x35' + P(A5) + rb'\xe8....\x8f\x05' +
                    P(A5) + rb'\x8f\x05' + P(D0) + rb'\x83\x05' + P(A5) + rb'\x38\x66\xff\x0d' + P(D0) + rb'\x79.\xc3',
                    d1[dm:dm + 100], re.S), "DrawMultipleItems"
    item = dm + 54 + struct.unpack_from("<i", d1, dm + 50)[0]
    return dict(hdr=hdr[0], row=row[0], draw=dm, item=item, jmp=hk[0], D0=D0, A5=A5)


def patch(p, at, lang):
    """Code + the INT header text at obj1:at; the menu's x / width words in obj2 in place; returns the end."""
    import lepatch
    s = find(lepatch.LEPatch(bytes(p.le.data)))          # (the original bytes)
    assert bytes(p.get(2, s['jmp'], 1)) == b'\xe9', 'jmp'
    hdr = HDR.get(lang, b'INT')
    sym = {'D0_': (2, s['D0']), 'A5_': (2, s['A5']), 'DRAWMULTI': (1, s['draw']), 'DRAWITEM': (1, s['item']),
           'XD_': (0, X_TOT - X_INT)}
    src = ASM + 'SC_HDR: db ' + ', '.join(str(b) for b in bytes((len(hdr),)) + b''.join(bytes((c, 0)) for c in hdr)) + '\n'
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    j = s['jmp']                                         # jmp DrawMultipleItems -> jmp sc_draw (obj2 -> obj1: its
    p.retarget(2, j + 1, 1, lab['sc_draw'])              # self-relative fixup retargeted)
    h = s['hdr']                                         # obj2 in place: the headers' and the numbers' x, the team's
    for k, x in enumerate((X_LEGA, X_COP1, X_COP2)):     # width (entries 18 / 18 / 18 / 16 bytes apart)
        p.put(2, h + 18 * k, struct.pack('<h', x))
    r = s['row']
    p.put(2, r + 4, struct.pack('<h', 96))
    for k, x in enumerate((X_LEGA, X_COP1, X_COP2)):
        p.put(2, r + 18 + 16 * k, struct.pack('<h', x))
    LOG.append(f'scorint: INT column ({hdr.decode()}) on CAPO CANNONIERI NAZIONALE: draw obj1+{at:#x} ({len(code)} B), '
               f'hook obj2+{j:#x}, menu obj2+{h:#x} / +{r:#x}')
    print('exe: ' + LOG[-1])
    return at + len(code)
