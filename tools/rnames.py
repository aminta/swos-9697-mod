"""Real round names in a league-phase career world (World 2026-27): the game names a round from a fixed table (long
'PRIMO TURNO' .. 'FINALE', medium 'TURNO 1' .. for the career game list and the calendar, short 'T 1' ..), indexed
by cseg_280C0 (type-1 cups: rounds left 1 / 2 / 3 = final / semi / quarter, else the round's number) and
cseg_283BD (type-2 stages: the stage's number, or quarter / semi / final by the stage's clubs). The three tables
(12 dwords each, contiguous in obj2) move to obj1 with 9 more entries per language: league phase, knockout
play-offs, round of 16, the qualifying play-off round, the preliminary round, the Serie C play-off's 4 rounds. rn_round (through uefaq's uq_rn1 /
uq_rn2, which call it instead of uq_tie_round) picks them in a league-phase world only (careerworld w_lpw):
- the world's UEFA cups (type 2, the league-phase layout of lp36): stage 0 = LEAGUE PHASE, 1 = KNOCKOUT PLAY-OFFS,
  2 = ROUND OF 16 (then the game's quarter / semi / final);
- uefaq's qualifying ties: its play-off round (D0 = 3) = PLAY-OFF ROUND (Q1-Q3 keep FIRST / SECOND / THIRD ROUND
  after 'PRELIM. <cup>');
- dplay's Serie B play-off: round 0 = PRELIMINARY ROUND; the play-out = the game's FINAL; its Serie C play-off: rounds
  0-3 = GROUP PHASE ROUND 1 / 2, NATIONAL ROUND 1 / 2 (then the game's SEMI-FINAL / FINAL);
- any other cup of the world: the round with 16 clubs (4 rounds left) = ROUND OF 16, except the cups of
  NUMBERED (pack.json cup 'round_names': 'numbered': England's FA Cup fifth round ...).
"""
import re
import struct

# per language: (long, medium, short) for LP, KO play-offs, R16, qualifying play-off round, preliminary round
NAMES = {
    'it': [('FASE CAMPIONATO', 'FASE CAMP.', 'F CMP'), ('SPAREGGI', 'SPAREGGI', 'SPR'),
           ('OTTAVI DI FINALE', 'OTTAVI', 'O F'), ('SPAREGGI', 'SPAREGGI', 'SPR'),
           ('TURNO PRELIMINARE', 'T. PRELIM.', 'T P'),
           ('PRIMO TURNO GIRONE', 'T. GIRONE 1', 'G 1'), ('SECONDO TURNO GIRONE', 'T. GIRONE 2', 'G 2'),
           ('PRIMO TURNO NAZIONALE', 'T. NAZ. 1', 'N 1'), ('SECONDO TURNO NAZIONALE', 'T. NAZ. 2', 'N 2'),
           ('PRIMO TURNO', 'T. 1', 'T 1'), ('TRENTADUESIMI DI FINALE', 'TRENTADUES.', '1/32'),
           ('SEDICESIMI DI FINALE', 'SEDICESIMI', '1/16'), ('QUARTI DI FINALE', 'QUARTI', 'Q F'),
           ('SEMIFINALE', 'SEMIFINALE', 'S F'), ('FINALE', 'FINALE', 'F')],
    'en': [('LEAGUE PHASE', 'LEAGUE PH.', 'LP'), ('KNOCKOUT PLAY-OFFS', 'PLAY-OFFS', 'P/O'),
           ('ROUND OF 16', 'LAST 16', 'R16'), ('PLAY-OFF ROUND', 'PLAY-OFF', 'P/O'),
           ('PRELIMINARY ROUND', 'PRELIMINARY', 'PRE'),
           ('GROUP PHASE ROUND 1', 'GROUP RND 1', 'GR1'), ('GROUP PHASE ROUND 2', 'GROUP RND 2', 'GR2'),
           ('NATIONAL ROUND 1', 'NAT. RND 1', 'NR1'), ('NATIONAL ROUND 2', 'NAT. RND 2', 'NR2'),
           ('FIRST ROUND', 'ROUND 1', 'R1'), ('ROUND OF 64', 'LAST 64', 'R64'), ('ROUND OF 32', 'LAST 32', 'R32'),
           ('QUARTER-FINAL', 'QUARTER-F.', 'QF'), ('SEMI-FINAL', 'SEMI-FINAL', 'SF'), ('FINAL', 'FINAL', 'F')],
    'fr': [('PHASE DE LIGUE', 'PH. LIGUE', 'LIG'), ('BARRAGES', 'BARRAGES', 'BAR'),
           ('HUITIEMES DE FINALE', '1/8 FINALE', '1/8'), ('BARRAGES', 'BARRAGES', 'BAR'),
           ('TOUR PRELIMINAIRE', 'T. PRELIM.', 'T P'),
           ('1ER TOUR DE GROUPE', 'T1 GROUPE', 'G 1'), ('2E TOUR DE GROUPE', 'T2 GROUPE', 'G 2'),
           ('1ER TOUR NATIONAL', 'T1 NATIONAL', 'N 1'), ('2E TOUR NATIONAL', 'T2 NATIONAL', 'N 2'),
           ('PREMIER TOUR', '1ER TOUR', 'T1'), ('TRENTE-DEUXIEMES', '1/32 FINALE', '1/32'),
           ('SEIZIEMES DE FINALE', '1/16 FINALE', '1/16'), ('QUARTS DE FINALE', '1/4 FINALE', '1/4'),
           ('DEMI-FINALE', '1/2 FINALE', '1/2'), ('FINALE', 'FINALE', 'F')],
    'de': [('LIGAPHASE', 'LIGAPHASE', 'LIGA'), ('K.O.-PLAYOFFS', 'PLAYOFFS', 'P/O'),
           ('ACHTELFINALE', 'ACHTELF.', 'A/F'), ('PLAYOFF-RUNDE', 'PLAYOFFS', 'P/O'),
           ('VORRUNDE', 'VORRUNDE', 'VR'),
           ('GRUPPENRUNDE 1', 'GR.-RUNDE 1', 'GR1'), ('GRUPPENRUNDE 2', 'GR.-RUNDE 2', 'GR2'),
           ('NATIONALE RUNDE 1', 'NAT. RUNDE 1', 'NR1'), ('NATIONALE RUNDE 2', 'NAT. RUNDE 2', 'NR2'),
           ('ERSTE RUNDE', '1. RUNDE', 'R1'), ('1/32-FINALE', '1/32-FIN.', '1/32'), ('1/16-FINALE', '1/16-FIN.', '1/16'),
           ('VIERTELFINALE', 'VIERTELF.', 'V F'), ('HALBFINALE', 'HALBFINALE', 'H F'), ('FINALE', 'FINALE', 'F')],
}
N_OLD = 12
LP, KO, R16, QPO, PRE, CG1, CG2, CN1, CN2, CD1, CD2, CD3, CD5, CD6, CD7 = range(N_OLD, N_OLD + 15)
CD_NAMES = (PRE, CD1, CD2, CD3, R16, CD5, CD6, CD7)   # (the Coppa Italia Serie D's rounds 0-7: gplay's cd_rname)

LABELS = {}

ASM = '''
rn_round:                               ; uq_rn1 / uq_rn2: CF = 1 and D0 = the name index, else CF = 0 (the game's)
    push eax
    push ebx
    call W_LPW                          ; (a league-phase world only)
    jne .game
    mov al, [DIY + 2Dh]                 ; the contest: in DIY, or (while a calendar is built) its copy
    test al, al
    jnz .id
    mov al, [DIYCOPY + 2Dh]
.id:
    cmp al, DPID_PO
    je .pre
    cmp al, DPID_OUT
    je .out
    cmp al, DPID_CPO                    ; dplay's Serie C play-off: group rounds 1 / 2, national rounds 1 / 2
    jne .nc
    movzx eax, word [D0R]
    cmp eax, 4
    jae .game
    add eax, CG1_I
    jmp .set
.nc:
    mov ebx, RN_LPIDS                   ; the world's three UEFA cups (type 2; ids 0 .. 2 in the game)
.l:
    cmp ebx, RN_LPIDS + 3
    je .q
    cmp [ebx], al
    je .lp
    inc ebx
    jmp .l
.lp:
    movzx eax, word [D0R]               ; (a type-2 contest: the stage)
    cmp eax, 3
    jae .game
    mov al, [RN_LPMAP + eax]
    jmp .set
.pre:
    cmp word [D0R], 0
    jne .game
    mov al, PRE_I
    jmp .set
.q:
    pop ebx                             ; uefaq's qualifying ties
    pop eax
    call UQ_TIE_ROUND
    jnc .cup
    cmp word [D0R], 3
    jne .yes
    mov word [D0R], QPO_I               ; (its play-off round)
.yes:
    stc
    ret
.cup:                                   ; another cup (cseg_280C0 only: D1 = its rounds): 4 rounds left = 16 clubs
    push eax
    push ebx
    cmp dword [esp + 8], R280C0_RET     ; (called from uq_rn1)
    jne .game
    movzx eax, word [D1R]
    sub ax, [D0R]
    cmp eax, 4
    jne .game
    mov al, [DIY + 2Dh]
    test al, al
    jnz .nb
    mov al, [DIYCOPY + 2Dh]
.nb:
    mov ebx, RN_NUMB
.n:
    cmp byte [ebx], 0
    je .r16
    cmp [ebx], al
    je .game
    inc ebx
    jmp .n
.r16:
    mov al, R16_I
.set:
    movzx eax, al
    mov [D0R], ax
    pop ebx
    pop eax
    stc
    ret
.out:                                   ; (FE: gplay's slot-4 contests; a Coppa Italia Serie D tie: its round's name)
    cmp dword [RN_CDP], 0
    je .game
    call [RN_CDP]                       ; (gplay cd_rname: CF = 1, al = the name index)
    jc .set
.game:
    pop ebx
    pop eax
    clc
    ret
align 4
RN_CDP: dd 0                            ; (gplay.cd_rname, or 0)

; Titles (cseg_45D92: '<contest name> <round> [<leg>]' into a menu entry's text, which shows 40 characters): when
; longer, a national contest drops its country prefix first ('ITALIA PLAY-OFF SERIE B' -> 'PLAY-OFF SERIE B'), then
; the medium round name ('OTTAVI', 'T. PRELIM.') is used; still longer, the first word goes and then the end is cut.
rn_t1:                                  ; its `call cseg_284AB` (type-2 rounds)
    call C284AB
    jmp rn_tfit
rn_t2:                                  ; its two `call cseg_28049` (type-1 rounds)
    call C28049
rn_tfit:                                ; A0 = the round's long name, D0 = its index x 4, A1 = after '<name> '
    pushad
    mov esi, DIY + 4                    ; (the contest's name, copied first)
    call rn_len
    lea edx, [ecx + 1]
    mov eax, [A1R]
    sub eax, edx
    mov [RN_TS], eax                    ; the title's start
    mov esi, [A0R]
    call rn_len
    add edx, ecx
    cmp word [DIY + 14Bh], 2            ; (+ ' <leg>' of a two-legged round, or ' DRAW')
    jne .w
    add edx, 8
.w:
    cmp edx, 40
    jbe .x
    mov al, [DIY + 2Dh]                 ; a national contest ('<country> <name>'): its country prefix goes first
    mov ebx, RN_LPIDS                   ; (not the UEFA cups nor their qualifying ties)
.u:
    cmp [ebx], al
    je .med
    inc ebx
    cmp ebx, RN_LPIDS + 3
    jb .u
    cmp al, QID_LO
    jb .nat
    cmp al, QID_HI
    jbe .med
.nat:
    mov byte [RN_DROP], 1
    mov esi, DIY + 4                    ; (its first word + the space)
.fw:
    lodsb
    test al, al
    jz .med
    dec edx
    cmp al, ' '
    jne .fw
    cmp edx, 40
    jbe .x
.med:
    movzx eax, word [D0R]
    mov eax, [MEDTAB + eax]
    mov [A0R], eax
.x:
    popad
    ret

rn_len:                                 ; esi = a string -> ecx = its shown characters (the '*' fill is not shown)
    xor ecx, ecx
.l:
    mov al, [esi]
    inc esi
    test al, al
    jz .r
    cmp al, '*'
    je .l
    inc ecx
    jmp .l
.r:
    ret

rn_tend:                                ; replaces `mov esi, [A1]` at cseg_45D92's end (then `mov byte [esi], 0`)
    pushad
    mov ebx, [RN_TS]
    test ebx, ebx
    jz .x
    mov dword [RN_TS], 0
    mov edi, [A1R]
    mov byte [edi], 0
    mov esi, ebx
    call rn_len
    cmp byte [RN_DROP], 0
    mov byte [RN_DROP], 0
    jne .d
    cmp ecx, 40
    jbe .x
.d:
    mov esi, ebx                        ; drop the first word
.f:
    cmp esi, edi
    jae .x
    lodsb
    cmp al, ' '
    jne .f
    mov edx, ebx
.c:
    mov al, [esi]
    mov [edx], al
    inc esi
    inc edx
    test al, al
    jnz .c
    dec edx
    mov [A1R], edx
    mov esi, ebx
    call rn_len
    cmp ecx, 40
    jbe .x
    xor ecx, ecx                        ; still longer: cut after 40 shown characters
    mov esi, ebx
.k:
    mov al, [esi]
    cmp al, '*'
    je .n
    inc ecx
    cmp ecx, 40
    ja .cut
.n:
    inc esi
    jmp .k
.cut:
    mov [A1R], esi
.x:
    popad
    mov esi, [A1R]
    ret
RN_TS: dd 0
RN_DROP: db 0

RN_LPMAP: db LP_I, KO_I, R16_I
RN_LPIDS: LPID_BYTES
RN_NUMB: NUMB_BYTES
'''


def _title_sites(p, r):
    """cseg_45D92 (a cup round's title): its `call cseg_284AB`, its two `call cseg_28049` (each followed by `call
    StringCopy`), its end `mov esi, [A1]; mov byte [esi], 0; retn`; cseg_28049 and cseg_284AB."""
    d1 = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    fs = [m.start() for m in re.finditer(rb'\xe8.{4}\x66\xc1\x25' + pk(r['A0'] - 32) + rb'\x02\xc7\x05' + pk(r['A0']), d1, re.S)]
    assert len(fs) == 2, fs
    tgt = lambda a: a + 5 + struct.unpack_from('<i', d1, a + 1)[0]
    c28049, c284ab = sorted(fs, key=lambda f: d1[tgt(f):tgt(f) + 3] != b'\x66\x83\x2d')   # (280C0: sub word [D1], 1)
    ends = [m.start() for m in re.finditer(rb'\x8b\x35' + pk(r['A0'] + 4) + rb'\xc6\x06\x00\xc3', d1)]
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and tgt(i) == t]
    for e in ends:                              # the end with one 284AB call and two 28049 calls before it
        a = [c for c in calls(c284ab) if 0 < e - c < 0x200]
        b = [c for c in calls(c28049) if 0 < e - c < 0x200]
        if len(a) == 1 and len(b) == 2:
            for c in a + b:
                assert d1[c + 5] == 0xE8, hex(c)
            return e, a[0], b, c28049, c284ab
    raise AssertionError('cseg_45D92 not found')


def _tables(p):
    """obj2 offset of the long table (cseg_28049: call cseg_280C0; shl word [D0], 2; mov [A0], offset table) and
    the obj1 fixup sites pointing at the three tables."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xe8.{4}\x66\xc1\x25' + pk(r['A0'] - 32) + rb'\x02\xc7\x05' + pk(r['A0']) + rb'(.{4})',
                                d1, re.S)]
    bases = {struct.unpack('<I', x.group(1))[0] for x in m}
    assert len(bases) == 1, bases
    base = bases.pop()
    fx = [f for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] in (base, base + 48, base + 96)]
    assert len(fx) >= 4, fx
    return base, fx


def patch(p, at, limit, lang, area, lp_ids, numbered):
    """Tables + rn_round in obj1 at..limit; lp_ids: the world's UEFA cups' contest ids; numbered: cup ids keeping
    numbered rounds. Returns the end."""
    import careerworld
    import dplay
    import nasmcave
    import sacups
    import uefaq
    assert len(lp_ids) == 3, lp_ids
    base, fx = _tables(p)
    d2 = p.le.obj_bytes(2)
    ptrs = {}                                   # obj2 offset of each old entry's string, from its fixup
    for f in p.le.fixups():
        if f[0] == 2 and f[3] == 2 and base <= f[1] < base + 144 and (f[1] - base) % 4 == 0:
            ptrs[f[1] - base] = f[4]
    assert all(4 * k in ptrs for k in range(N_OLD)) and all(48 + 4 * k in ptrs for k in range(N_OLD)), sorted(ptrs)
    new = [[area.add(nm[t].encode('latin1') + b'\0') for nm in NAMES[lang]] for t in range(3)]
    tab = (at + 3) & ~3
    n = N_OLD + len(NAMES[lang])
    for t in range(3):
        for k in range(n):
            a = tab + 4 * (t * n + k)
            if k < N_OLD:
                tgt = ptrs.get(48 * t + 4 * k)
                if tgt is None:                 # (the short table may hold fewer: its last old string)
                    tgt = ptrs[48 * t + 4 * max(j for j in range(N_OLD) if 48 * t + 4 * j in ptrs)]
            else:
                tgt = new[t][k - N_OLD]
            p.add_ptr(1, a, 2, tgt)
    for f in fx:                                # every reference to the old tables -> ours
        t = (f[4] - base) // 48
        p.retarget(1, f[1], 1, tab + 4 * n * t)
    code_at = tab + 12 * n
    ul = uefaq.LABELS
    diy, a0 = dplay._sites(p)[4], sacups.regs(p.le.obj_bytes(1))['A0']
    sym = {'W_LPW': (1, careerworld.LABELS['w_lpw']), 'DIY': (2, diy), 'DIYCOPY': (2, diy - 0x41F),
           'D0R': (2, a0 - 32), 'D1R': (2, a0 - 28), 'DPID_PO': (0, dplay.DP_PO), 'DPID_OUT': (0, dplay.DP_OUT),
           'DPID_CPO': (0, dplay.DP_CPO), 'CG1_I': (0, CG1),
           'UQ_TIE_ROUND': (1, ul['uq_tie_round']), 'R280C0_RET': (1, ul['uq_rn1'] + 5),
           'LP_I': (0, LP), 'KO_I': (0, KO), 'R16_I': (0, R16), 'QPO_I': (0, QPO), 'PRE_I': (0, PRE),
           'LPID_BYTES': (0, 'db ' + ', '.join(str(x) for x in lp_ids)),
           'NUMB_BYTES': (0, 'db ' + ', '.join(str(x) for x in list(numbered) + [0]))}
    end, s284, s280, c28049, c284ab = _title_sites(p, sacups.regs(p.le.obj_bytes(1)))
    sym.update({'QID_LO': (0, min(uefaq.QIDS)), 'QID_HI': (0, max(uefaq.QIDS)), 'C28049': (1, c28049), 'C284AB': (1, c284ab), 'MEDTAB': (1, tab + 4 * n), 'A0R': (2, a0),
                'A1R': (2, a0 + 4)})
    code, fix = nasmcave.assemble(ASM, code_at, sym)
    lab = nasmcave.labels(ASM, code_at, sym)
    assert code_at + len(code) <= limit, hex(code_at + len(code))
    p.put(1, code_at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, code_at + off, tobj, toff)
    rel = lambda a, t: struct.pack('<i', lab[t] - (a + 5))
    p.put(1, s284 + 1, rel(s284, 'rn_t1'))      # (relative calls: no fixups)
    for c in s280:
        p.put(1, c + 1, rel(c, 'rn_t2'))
    p.remove(1, end + 2)                        # mov esi, [A1] (6 B) -> call rn_tend; nop
    p.put(1, end, b'\xe8' + rel(end, 'rn_tend') + b'\x90')
    for rn in ('uq_rn1', 'uq_rn2'):             # their `call uq_tie_round` (dplay may have moved it) -> rn_round
        a = ul[rn]
        assert p.get(1, a, 1) == b'\xe8'
        p.put(1, a + 1, struct.pack('<i', lab['rn_round'] - (a + 5)))
    LABELS['RN_CDP'] = lab['RN_CDP']
    print(f'exe: round names: tables obj2+{base:#x} -> obj1+{tab:#x} ({n} x 3, {len(fx)} references), rn_round '
          f'obj1+{lab["rn_round"]:#x}, UEFA cups {[hex(x) for x in lp_ids]}, numbered {len(numbered)}')
    return code_at + len(code)
