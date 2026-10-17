"""Real round names in a league-phase career world (World 2026-27): the game names a round from a fixed table (long
'PRIMO TURNO' .. 'FINALE', medium 'TURNO 1' .. for the career game list and the calendar, short 'T 1' ..), indexed
by cseg_280C0 (type-1 cups: rounds left 1 / 2 / 3 = final / semi / quarter, else the round's number) and
cseg_283BD (type-2 stages: the stage's number, or quarter / semi / final by the stage's clubs). The three tables
(12 dwords each, contiguous in obj2) move to obj1 with 5 more entries per language: league phase, knockout
play-offs, round of 16, the qualifying play-off round, the preliminary round. rn_round (through uefaq's uq_rn1 /
uq_rn2, which call it instead of uq_tie_round) picks them in a league-phase world only (careerworld w_lpw):
- the world's UEFA cups (type 2, the league-phase layout of lp36): stage 0 = LEAGUE PHASE, 1 = KNOCKOUT PLAY-OFFS,
  2 = ROUND OF 16 (then the game's quarter / semi / final);
- uefaq's qualifying ties: its play-off round (D0 = 3) = PLAY-OFF ROUND (Q1-Q3 keep FIRST / SECOND / THIRD ROUND
  after 'PRELIM. <cup>');
- dplay's Serie B play-off: round 0 = PRELIMINARY ROUND; the play-out = the game's FINAL;
- any other cup of the world: the round with 16 clubs (4 rounds left) = ROUND OF 16, except the cups of
  NUMBERED (pack.json cup 'round_names': 'numbered': England's FA Cup fifth round ...).
"""
import re
import struct

# per language: (long, medium, short) for LP, KO play-offs, R16, qualifying play-off round, preliminary round
NAMES = {
    'it': [('FASE CAMPIONATO', 'FASE CAMP.', 'F CMP'), ('SPAREGGI', 'SPAREGGI', 'SPR'),
           ('OTTAVI DI FINALE', 'OTTAVI', 'O F'), ('SPAREGGI', 'SPAREGGI', 'SPR'),
           ('TURNO PRELIMINARE', 'T. PRELIM.', 'T P')],
    'en': [('LEAGUE PHASE', 'LEAGUE PH.', 'LP'), ('KNOCKOUT PLAY-OFFS', 'PLAY-OFFS', 'P/O'),
           ('ROUND OF 16', 'LAST 16', 'R16'), ('PLAY-OFF ROUND', 'PLAY-OFF', 'P/O'),
           ('PRELIMINARY ROUND', 'PRELIMINARY', 'PRE')],
    'fr': [('PHASE DE LIGUE', 'PH. LIGUE', 'LIG'), ('BARRAGES', 'BARRAGES', 'BAR'),
           ('HUITIEMES DE FINALE', '1/8 FINALE', '1/8'), ('BARRAGES', 'BARRAGES', 'BAR'),
           ('TOUR PRELIMINAIRE', 'T. PRELIM.', 'T P')],
    'de': [('LIGAPHASE', 'LIGAPHASE', 'LIGA'), ('K.O.-PLAYOFFS', 'PLAYOFFS', 'P/O'),
           ('ACHTELFINALE', 'ACHTELF.', 'A/F'), ('PLAYOFF-RUNDE', 'PLAYOFFS', 'P/O'),
           ('VORRUNDE', 'VORRUNDE', 'VR')],
}
N_OLD = 12
LP, KO, R16, QPO, PRE = range(N_OLD, N_OLD + 5)

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
    je .game
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
.game:
    pop ebx
    pop eax
    clc
    ret

RN_LPMAP: db LP_I, KO_I, R16_I
RN_LPIDS: LPID_BYTES
RN_NUMB: NUMB_BYTES
'''


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
           'UQ_TIE_ROUND': (1, ul['uq_tie_round']), 'R280C0_RET': (1, ul['uq_rn1'] + 5),
           'LP_I': (0, LP), 'KO_I': (0, KO), 'R16_I': (0, R16), 'QPO_I': (0, QPO), 'PRE_I': (0, PRE),
           'LPID_BYTES': (0, 'db ' + ', '.join(str(x) for x in lp_ids)),
           'NUMB_BYTES': (0, 'db ' + ', '.join(str(x) for x in list(numbered) + [0]))}
    code, fix = nasmcave.assemble(ASM, code_at, sym)
    lab = nasmcave.labels(ASM, code_at, sym)
    assert code_at + len(code) <= limit, hex(code_at + len(code))
    p.put(1, code_at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, code_at + off, tobj, toff)
    for rn in ('uq_rn1', 'uq_rn2'):             # their `call uq_tie_round` (dplay may have moved it) -> rn_round
        a = ul[rn]
        assert p.get(1, a, 1) == b'\xe8'
        p.put(1, a + 1, struct.pack('<i', lab['rn_round'] - (a + 5)))
    print(f'exe: round names: tables obj2+{base:#x} -> obj1+{tab:#x} ({n} x 3, {len(fx)} references), rn_round '
          f'obj1+{lab["rn_round"]:#x}, UEFA cups {[hex(x) for x in lp_ids]}, numbered {len(numbered)}')
    return code_at + len(code)
