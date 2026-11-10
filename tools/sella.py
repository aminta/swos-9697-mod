"""4.0.6 (Davide, Francesco's report: his Serie D 50k player bought by ROMA): outgoing transfers rule A - a club bids
for one of the career club's players only if he would be one of its own.

The game's offer for one of our players (cseg_5AB36, from the weekly scan cseg_5A90B: per player a Rand2 < 1 or 11
in 256): its buyer pool is the loaded clubs of our own country (Rand2 >= 8, ~97%: selTeamsPtr / g_numSelectedTeams) or
the team file's clubs of other countries (Rand2 < 8, ~3%: tmdFileBuffer); each candidate goes through cseg_5B3B5 (not
our club, not a cup-only club - league byte +19h = 4 -, and among its 16 players one with the player's value byte or
both a cheaper and a pricier one), then one of the eligible at random, 85-119 % of his value. So any club with one
cheap youngster among its 16 bid for a Serie D player: ROMA did.

Rule A, chained on cseg_5B3B5's two calls (the original test first, unchanged): an eligible candidate stays only if
fewer than N of its 16 players are priced above the player's value byte + MARGIN - i.e. he would be at least its
N-th most valuable player, give or take MARGIN value steps. Team-record bytes only: every world (historic ones too),
no division table; it leaves the post-engine CPU market alone.

SELLOFF_FORCE (test builds only, modver TEST_VARS): 1 = cseg_5A90B tries an offer for every player it scans (its
`Rand2 < D3` skipped) - an offer a week while the list has room. The harness / host tests find the data block by its
tag 'SELA': counters (scan tries, candidates the rule dropped, offers made) and a ring of the last RING offers (buyer
team number, player index, amount, the player's value byte, the buyer's count above value + MARGIN, the first 8
letters of its name).
"""
import os
import re
import struct

import nasmcave

N = int(os.environ.get('SELLA_N', 12))          # (tuning: SELLA_N / SELLA_MARGIN, balance runs only)
MARGIN = int(os.environ.get('SELLA_MARGIN', 2))
RING = 32
TAG = b'SELA'

ASM = r"""
sl_chk:                                 ; replaces cseg_5AB36's two `call cseg_5B3B5` (A0 = the candidate's record,
    call PREV_CHK                       ; D7 = the player's value byte): ZF = 1 eligible, as the original
    jnz .r
%if RULE
    pushad
    mov esi, [A0_]
    call sl_cnt
    cmp ecx, N
    jb .ok
    inc dword [SL_DROP]                 ; dropped: ZF = 0 and D0 = 1, as the original's own refusal
    mov word [D0_], 1
    popad
    test esp, esp
    ret
.ok:popad
    cmp eax, eax
%endif
.r: ret

sl_cnt:                                 ; esi = a team record: ecx = its 16 players priced above [D7] + MARGIN
    movzx edx, byte [D7_]
    add edx, MARGIN
    xor ecx, ecx
    lea ebx, [esi + 6Ch]
    mov edi, 16
.l: movzx eax, byte [ebx]
    cmp eax, edx
    jbe .n
    inc ecx
.n: add ebx, 26h
    dec edi
    jnz .l
    ret

sl_try:                                 ; replaces cseg_5A90B's `call cseg_5AB36`: counted, and an offer it made logged
    inc dword [SL_TRY]
    push eax
    mov ax, [NOFF]
    mov [SL_N0], ax
    pop eax
    call PREV_TRY
    pushad
    mov ax, [NOFF]
    cmp ax, [SL_N0]
    jbe .x
    inc dword [SL_MADE]
    mov ecx, [SL_MADE]
    dec ecx
    and ecx, RING - 1
    shl ecx, 4
    lea edi, [SL_RING + ecx]
    mov ax, [TOFF]
    mov [edi], ax
    mov ax, [PIDX]
    mov [edi + 2], ax
    mov ax, [AMT]
    mov [edi + 4], ax
    mov al, [D7_]
    mov [edi + 6], al
    mov esi, [A6_]                      ; (A6 = the buyer's record, as cseg_5AB36 left it: its count, its name)
    push edi
    call sl_cnt
    pop edi
    mov [edi + 7], cl
    lea esi, [esi + 5]
    add edi, 8
    movsd
    movsd
.x: popad
    ret

align 4
SL_TAG: db 'SELA'
SL_TRY: dd 0                            ; (offer attempts, candidates rule A dropped, offers made: read by the harness)
SL_DROP: dd 0
SL_MADE: dd 0
SL_N0: dw 0
SL_PARM: db N, MARGIN, RING, RULE
SL_RING: times RING * 16 db 0
"""


def find(p):
    """cseg_5B3B5 (`cmp byte [esi+19h], 4; jz; 4 nops`, the one called twice 0xA1 apart), cseg_5AB36 (0xF0 before
    the first call), its one call in cseg_5A90B and that scan's `mov ax,[D3]; cmp [D0],ax; jnb` (SELLOFF_FORCE),
    numOffers (the scan's `cmp numOffers, 5`), dseg_17A6CE (5AB36's first store), teamOffering and the amount; for
    the host tests: the candidate list dseg_175036 (116 B, byte indices), g_numSelectedTeams / careerFileBuffer (the
    two pools' counts), selTeamsPtr, tmdFileBuffer and the pool draw's jb (obj1: Rand2 < 8 -> the foreign pool)."""
    import sacups
    d = p.le.obj_bytes(1)
    d0 = sacups.regs(d)['D7'] - 28
    pt = lambda a: re.escape(struct.pack('<I', a))
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    callers = lambda t: [m.start() for m in re.finditer(rb'\xe8', d) if m.start() + 5 <= len(d) and rel(m.start()) == t]
    chk = []
    for m in re.finditer(rb'\x80\x7e\x19\x04\x74.\x90\x90\x90\x90', d, re.S):
        s = m.start() - 40
        c = callers(s)
        if d[s:s + 2] == b'\x8b\x35' and len(c) == 2 and c[1] - c[0] == 0xA1:
            chk.append((s, c))
    assert len(chk) == 1, chk
    chk, calls = chk[0]
    a = calls[0] - 0xF0
    assert d[a:a + 2] == b'\x66\xa1' and d[a + 6:a + 8] == b'\x66\xa3', 'cseg_5AB36'
    tc = callers(a)
    assert len(tc) == 1, tc
    f = [m.start() for m in re.finditer(rb'\x66\xa1' + pt(d0 + 12) + rb'\x66\x39\x05' + pt(d0) + rb'\x0f\x83', d[tc[0] - 0x80:tc[0]])]
    assert len(f) == 1, f
    nf = [m for m in re.finditer(rb'\x66\x83\x3d(....)\x05\x0f\x84', d[tc[0] - 0x180:tc[0]], re.S)]
    assert len(nf) == 1, nf
    to = [m for m in re.finditer(rb'\x66\xa1' + pt(d0) + rb'\x66\xa3(....)\x66\xc7\x05....\xff\xff\x66\xc7\x05....\xff\xff\xe8',
                                 d[a:a + 0x400], re.S)]
    assert len(to) == 1, to
    am = [m for m in re.finditer(rb'\x66\xa3(....)\x66\xc7\x05....\x00\x00\x66\xc7\x05....\xff\xff\x66\xc7\x05....\xff\xff',
                                 d[a:a + 0x500], re.S)]
    assert len(am) == 1, am
    a0 = sacups.regs(d)['A0']
    hit = lambda rx: [a + m.start() for m in re.finditer(rx, d[a:a + 0x200], re.S)]
    buf, nsel, selp = hit(rb'\xc7\x05' + pt(a0 + 8) + rb'....'), hit(rb'\x66\xa1....\x66\x39\x05' + pt(d0 + 16)), \
        hit(rb'\xa1....\xa3' + pt(a0 + 20))
    tmd, pool = hit(rb'\xc7\x05' + pt(a0 + 20) + rb'....'), hit(rb'\x66\x83\x3d' + pt(d0) + rb'\x08\x0f\x82')
    assert len(buf) == 2 and len(nsel) == 2 and len(selp) == 1 and len(tmd) == 1 and len(pool) == 1, \
        (buf, nsel, selp, tmd, pool)
    host = dict(BUF=buf[0] + 6, NSEL=nsel[0] + 2, NTMD=nsel[1] + 2, SELP=selp[0] + 1, TMD=tmd[0] + 6,
                POOL_JB=pool[0] + 8)            # (obj1 sites of their absolute addresses: careerworld moves some)
    return dict(host, CHK=chk, calls=calls, TRY=a, try_call=tc[0], force=tc[0] - 0x80 + f[0] + 13, d0=d0,
                NOFF=p.target(1, tc[0] - 0x180 + nf[0].start() + 3), PIDX=p.target(1, a + 8),
                TOFF=p.target(1, a + to[0].start() + 8), AMT=p.target(1, a + am[0].start() + 2))


def patch(p, at, dry=False):
    """Code + data at obj3:at (the obj3 chain's end); returns the end. Chained on the current targets of the two
    cseg_5B3B5 calls and of the cseg_5AB36 call (p.call_target). dry: the code's size only, nothing written."""
    import sacups
    s = find(p)
    d = p.le.obj_bytes(1)
    regs = sacups.regs(d)
    force = os.environ.get('SELLOFF_FORCE', '') == '1'
    rule = os.environ.get('SELLA_OFF', '') != '1'       # (balance runs: the original's offers, same counters)
    tc = [p.call_target(1, c) for c in s['calls']]
    assert len(set(tc)) == 1, ('cseg_5B3B5 calls', tc)
    src = f'%define N {N}\n%define MARGIN {MARGIN}\n%define RING {RING}\n%define RULE {int(rule)}\n' + ASM
    sym = {'PREV_CHK': tc[0], 'PREV_TRY': p.call_target(1, s['try_call']), 'A0_': (2, regs['A0']), 'A6_': (2, regs['A0'] + 24),
           'D7_': (2, regs['D7']), 'D0_': (2, s['d0']), 'NOFF': s['NOFF'], 'TOFF': s['TOFF'], 'PIDX': s['PIDX'],
           'AMT': s['AMT']}
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    if dry:
        return len(code)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    for c in s['calls']:
        p.branch(1, c, 0xE8, 3, lab['sl_chk'])
    p.branch(1, s['try_call'], 0xE8, 3, lab['sl_try'])
    if force:
        o = s['force']
        assert bytes(p.get(1, o, 2)) == b'\x0f\x83', 'SELLOFF_FORCE site already patched'
        p.put(1, o, b'\x90' * 6)
    LABELS.update({k: (3, v) for k, v in lab.items()})   # (obj3: hosttest's syms; TRY_AT, the scan's call
    TRY_AT[:] = [s['try_call']]                           #  into the offer, = snapshot.py's obj1 breakpoint)
    print(f'exe: outgoing offers rule A ({"N " + str(N) + ", margin " + str(MARGIN) if rule else "OFF (SELLA_OFF)"}'
          f'{", SELLOFF_FORCE" if force else ""}): code obj3+{at:#x} ({len(code)} B), cseg_5B3B5 calls '
          f'{[hex(c) for c in s["calls"]]}, cseg_5AB36 call {s["try_call"]:#x}')
    return at + len(code)


LABELS = {}
TRY_AT = []
