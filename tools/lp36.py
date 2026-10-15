"""UEFA league phase (2024-25 format onward) in the DIY group engine — prototype (world 2025-26, phase 1, step 3).

36 clubs, 4 pots of 9 (contest order = pot order). Every club plays 8 matches: one home and one away opponent from
every pot, never a club of its own country, at most 2 opponents of one country. 8 matchdays of 18 matches, a single
table of 36; 1-8 to the round of 16, 9-24 knockout play-offs, 25-36 out.

The engine runs it as a type-2 group stage of 2 groups of 18 (it handles <= 24 per group; the career slot buffer of
a type-2 contest is 0xB52 = diyFileBufferCopy 0x41F + DIY_competitionStart 0x733: 64 team rows, 6 stages, saved):
- lp_days (in cseg_2573C, before cseg_260A9 spreads the days over the months): stage 1 has 8 days, not 17.
- lp_start (after cseg_2653B, league start of the stage): 72 pair indices x 2 groups = 144 matches in one cycle
  ([69h] = [6Bh] = 72), 8 days ([1C3h]); clears the away records.
- lp_pair (entry of cseg_89758, the pairing of match [1CBh] of group [5Bh]): match m = 2 * [1CBh] + [5Bh] of LP_CAL
  (day = m / 18) -> A1 = home row, A2 = away row (team-table rows: DIY + row * 18, fields +2B3h team .. +2C3h points).
  The fixture builder of the career calendar (cseg_8B8D9) goes through the same routine.
- lp_res (cseg_88A12, where the result is added): away goals and away wins per row (tie-breakers) in rows 44+ of the
  team table (unused rows; the slot buffer saves them).
- lp_sort (entry of cseg_883DD, the per-group standings sort into DIY+6Dh): ONE ranking of the 36 by points, goal
  difference, goals, away goals, wins, away wins, opponents' points, goal difference, goals, contest order (UEFA
  regulations 2025-26 art. 18; discipline skipped) written over both groups: group A = places 1-18, group B = 19-36,
  so the game's own group tables show the league table on two pages.
- lp_gend (around cseg_8A2CE, end of the group stage): the final ranking first (cseg_8A2CE re-sorts DIY+6Dh per
  group), then contest list A2+59h[0..15] = the play-off ties (seeded, in the order of the round-of-16 bracket),
  places 1-8 parked at A2+59h[16..23] (the play-off round puts its winners in [0..7] in tie order, leaves [16..23]).
- lp_draw (from historic.hist_draw for this contest): every draw keeps the order (fixed bracket), except the round
  of 16: tie k = (play-off winner k, seeded club k), seeded order 1 8 3 5 | 2 7 4 6 (2024-25 bracket shape: QF 1v8,
  3v5, 2v7, 4v6; SF top half / bottom half).
Prototype limits: the draw (LP_CAL) is made at build time for the pack's 36 clubs (a career needs it at run time,
stored in the DIY state); seeded pairs and home legs are fixed, not drawn.
"""
import random
import re
import struct

N, POT, DAYS = 36, 9, 8
ROW = 0x2B3                     # team row r = DIY + ROW + 18 * r (+0 team dword, +4 played .. +16 points)
AWAY_GF = ROW + 18 * 44         # 36 bytes, then AWAY_W 36 bytes (rows 44..47: unused by a 36-club stage)


def draw(countries, seed=2025):
    """countries[i] of the 36 clubs in pot order -> [(home, away)] * 144, 8 days of 18 (day d = [18d, 18d + 18))."""
    rng = random.Random(seed)
    pots = [list(range(p * POT, (p + 1) * POT)) for p in range(4)]
    for attempt in range(100000):
        home = {}                                   # (P, Q) -> {p: q}: p (pot P) hosts q (pot Q)
        opp = {c: [] for c in range(N)}
        ok = True
        order = [(P, Q) for P in range(4) for Q in range(4)]
        rng.shuffle(order)
        for P, Q in order:
            f = _bijection(rng, pots[P], pots[Q], P == Q, home.get((Q, P), {}), countries, opp)
            if f is None:
                ok = False
                break
            home[(P, Q)] = f
            for p, q in f.items():
                opp[p].append(q)
                opp[q].append(p)
        if not ok:
            continue
        matches = [(p, q) for f in home.values() for p, q in f.items()]
        days = _schedule(rng, matches)
        if days:
            return [m for d in days for m in d]
    raise RuntimeError('no draw')


def _fits(c, o, countries, opp):
    if countries[c] == countries[o] or o in opp[c]:
        return False
    return sum(countries[x] == countries[o] for x in opp[c]) < 2 and sum(countries[x] == countries[c] for x in opp[o]) < 2


def _bijection(rng, P, Q, same, rev, countries, opp):
    """p -> q (p hosts q), one-to-one; no rematch of rev (q hosts p); same pot: no p -> p, no 2-cycles."""
    P = P[:]
    rng.shuffle(P)
    f, used = {}, set()

    def go(i):
        if i == len(P):
            return True
        p = P[i]
        cand = [q for q in Q if q not in used and rev.get(q) != p and _fits(p, q, countries, opp)
                and not (same and (q == p or f.get(q) == p))]
        rng.shuffle(cand)
        for q in cand:
            f[p] = q
            used.add(q)
            opp[p].append(q)
            opp[q].append(p)
            if go(i + 1):
                for x in (p, q):                    # (the caller adds them for good)
                    opp[x].pop()
                return True
            opp[p].pop()
            opp[q].pop()
            used.discard(q)
            del f[p]
        return False

    return dict(f) if go(0) else None


def _schedule(rng, matches, tries=200):
    """144 matches -> 8 perfect matchings of 18 (every club once a day), or None."""
    for _ in range(tries):
        left = matches[:]
        days = []
        for d in range(DAYS):
            day = _matching(rng, left)
            if day is None:
                break
            days.append(day)
            left = [m for m in left if m not in day]
        if len(days) == DAYS:
            return days
    return None


def _matching(rng, edges, limit=20000):
    adj = {c: [] for c in range(N)}
    for e in edges:
        adj[e[0]].append(e)
        adj[e[1]].append(e)
    for c in adj:
        rng.shuffle(adj[c])
    free, out, steps = set(range(N)), [], [0]

    def go():
        if not free:
            return True
        steps[0] += 1
        if steps[0] > limit:
            return False
        c = min(free, key=lambda x: sum(1 for e in adj[x] if e[0] in free and e[1] in free))
        for e in adj[c]:
            if e[0] in free and e[1] in free:
                free.difference_update(e)
                out.append(e)
                if go():
                    return True
                out.pop()
                free.update(e)
        return False

    return out[:] if go() else None


def check(cal, countries):
    """The draw rules, asserted."""
    assert len(cal) == 144
    for d in range(DAYS):
        day = cal[18 * d:18 * d + 18]
        assert sorted(x for m in day for x in m) == list(range(N)), d
    for c in range(N):
        h = [a for x, a in cal if x == c]
        a = [x for x, y in cal if y == c]
        assert len(h) == 4 and len(a) == 4, c
        for p in range(4):
            assert sum(o // POT == p for o in h) == 1 and sum(o // POT == p for o in a) == 1, (c, p)
        opps = h + a
        assert len(set(opps)) == 8
        assert all(countries[o] != countries[c] for o in opps)
        assert max(sum(countries[o] == k for o in opps) for k in set(countries)) <= 2


ASM = '''
lp_days:                                ; replaces `call cseg_260A9` in cseg_2573C (stage days -> months)
    cmp byte [DIYCOPY + 2Dh], LP_ID
    jne .go
    cmp word [DIYCOPY + 15Dh], 2        ; stage 1: 2 groups ...
    jne .go
    cmp word [DIYCOPY + 16Bh], 18       ; ... of 18
    jne .go
    mov word [DIYCOPY + 173h], 8        ; 8 matchdays (not 17)
.go:
    jmp C260A9

lp_ours:                                ; ZF = 1: DIY_competitionStart is our league phase
    cmp byte [DIY + 2Dh], LP_ID
    jne .r
    cmp word [DIY + 4Fh], 2
    jne .r
    cmp word [DIY + 51h], 18
.r:
    ret

lp_start:                               ; replaces `call cseg_2653B` in cseg_258E4 (league start of a group stage)
    call C2653B
    cmp byte [DIYCOPY + 2Dh], LP_ID     ; (cseg_258E4 copies the id into DIY+2Dh only at its end)
    jne .r
    cmp word [DIY + 4Fh], 2
    jne .r
    cmp word [DIY + 51h], 18
    jne .r
    mov word [DIY + 69h], 72            ; pair indices per cycle (2 groups: 144 matches)
    mov word [DIY + 6Bh], 72
    mov word [DIY + 1C3h], 8            ; matchdays
    push edi
    push ecx
    push eax
    lea edi, [DIY + AWAY_GF]
    mov ecx, 72
    xor eax, eax
    rep stosb
    pop eax
    pop ecx
    pop edi
.r:
    ret

lp_pair:                                ; replaces the first instruction of cseg_89758 (mov [A0], offset DIY)
    mov dword [A0], DIY
    call lp_ours
    jne .orig
    push eax
    push edx
    movzx eax, word [DIY + 1CBh]
    add eax, eax
    movzx edx, word [DIY + 5Bh]
    add eax, edx
    cmp eax, 144
    jae .bad
    movzx edx, byte [LP_CAL + eax*2]    ; home row
    imul edx, edx, 18
    add edx, DIY
    mov [A1], edx
    movzx edx, byte [LP_CAL + eax*2 + 1]
    imul edx, edx, 18
    add edx, DIY
    mov [A2], edx
    pop edx
    pop eax
    ret
.bad:
    pop edx
    pop eax
.orig:
    jmp C89758_NEXT

lp_res:                                 ; replaces `mov ax, [D1]; mov esi, [A3]` before the goals are added in cseg_88A12
    call lp_ours
    jne .r
    pushad
    mov eax, [A4]                       ; away row
    sub eax, DIY
    xor edx, edx
    mov ecx, 18
    div ecx
    cmp eax, 36
    jae .x
    mov dl, [D2]                        ; away goals
    add [DIY + AWAY_GF + eax], dl
    mov cx, [D2]
    cmp cx, [D1]
    jbe .x
    inc byte [DIY + AWAY_GF + 36 + eax] ; away win
.x:
    popad
.r:
    mov ax, [D1]
    mov esi, [A3]
    ret

; key per row (4 dwords, compared from the first): points | goal difference; goals | away goals | wins | away
; wins; opponents' points | opponents' goal difference | opponents' goals; 255 - contest order. Then the row.
lp_sort:                                ; replaces the first instruction of cseg_883DD (mov [A4], offset DIY)
    mov dword [A4], DIY
    call lp_ours
    je lp_rank
    jmp C883DD_NEXT

lp_rank:                                ; LP_ORD = rows best first, written into DIY+6Dh
    pushad
    xor ecx, ecx
.z:
    mov dword [LP_OPP + ecx*4], 0       ; opponents' points / GD / GF (3 x 36 dwords)
    inc ecx
    cmp ecx, 108
    jb .z
    xor ecx, ecx
.m:                                     ; every match of the draw (played or not): add each side's figures to the other
    movzx esi, byte [LP_CAL + ecx*2]
    movzx edi, byte [LP_CAL + ecx*2 + 1]
    call .acc
    xchg esi, edi
    call .acc
    inc ecx
    cmp ecx, 144
    jb .m
    xor ecx, ecx                        ; keys
.k:
    imul ebx, ecx, 18
    add ebx, DIY
    mov edi, ecx
    shl edi, 4
    add edi, LP_KEY
    movzx eax, word [ebx + 2C3h]        ; points
    shl eax, 16
    movzx edx, word [ebx + 2BFh]
    sub dx, [ebx + 2C1h]
    add dx, 8000h
    mov ax, dx
    mov [edi], eax
    movzx eax, byte [ebx + 2BFh]        ; goals (< 256)
    shl eax, 8
    mov al, [DIY + AWAY_GF + ecx]
    shl eax, 4
    movzx edx, word [ebx + 2B9h]        ; wins
    or al, dl
    shl eax, 4
    or al, [DIY + AWAY_GF + 36 + ecx]
    mov [edi + 4], eax
    mov eax, [LP_OPP + ecx*4]           ; opponents' points (< 256)
    shl eax, 12
    mov edx, [LP_OPP + 144 + ecx*4]
    add edx, 800h
    and edx, 0FFFh
    or eax, edx
    shl eax, 12
    mov edx, [LP_OPP + 288 + ecx*4]
    and edx, 0FFFh
    or eax, edx
    mov [edi + 8], eax
    mov eax, 255
    sub eax, ecx
    mov [edi + 12], eax
    mov [LP_ORD + ecx], cl
    inc ecx
    cmp ecx, 36
    jb .k
    mov ecx, 1                          ; insertion sort of LP_ORD, best first
.s1:
    cmp ecx, 36
    jae .w
    mov bl, [LP_ORD + ecx]
    mov edx, ecx
.s2:
    test edx, edx
    jz .s3
    movzx esi, byte [LP_ORD + edx - 1]
    movzx edi, bl
    call .less                          ; CF = 1: key[esi] < key[edi] -> move esi down
    jnc .s3
    mov al, [LP_ORD + edx - 1]
    mov [LP_ORD + edx], al
    dec edx
    jmp .s2
.s3:
    mov [LP_ORD + edx], bl
    inc ecx
    jmp .s1
.w:
    xor ecx, ecx                        ; DIY+6Dh: group A = places 1-18, group B = 19-36 (row offsets)
.w1:
    movzx eax, byte [LP_ORD + ecx]
    imul eax, eax, 18
    mov [DIY + 6Dh + ecx*2], ax
    inc ecx
    cmp ecx, 36
    jb .w1
    popad
    ret
.acc:                                   ; LP_OPP[esi] += figures of row edi
    imul eax, edi, 18
    movzx edx, word [DIY + eax + 2C3h]
    add [LP_OPP + esi*4], edx
    movzx edx, word [DIY + eax + 2BFh]
    add [LP_OPP + 288 + esi*4], edx
    movsx edx, word [DIY + eax + 2BFh]
    movsx eax, word [DIY + eax + 2C1h]
    sub edx, eax
    add [LP_OPP + 144 + esi*4], edx
    ret
.less:                                  ; CF = key[esi] < key[edi] (unsigned, 4 dwords)
    push esi
    push edi
    push ecx
    shl esi, 4
    shl edi, 4
    mov ecx, 4
.l1:
    mov eax, [LP_KEY + esi]
    cmp eax, [LP_KEY + edi]
    jne .l2
    add esi, 4
    add edi, 4
    dec ecx
    jnz .l1
    clc
.l2:
    pop ecx
    pop edi
    pop esi
    ret

lp_gend:                                ; replaces `call cseg_8A2CE` (group stage end: qualifiers into A2+59h)
    call lp_ours                        ; (before: cseg_8A2CE changes the DIY fields lp_ours reads and re-sorts
    jne .plain                          ; DIY+6Dh per group)
    call lp_rank                        ; the final ranking in LP_ORD
    call C8A2CE
    pushad
    xor ecx, ecx
.t:
    movzx eax, byte [LP_PO + ecx]       ; place (0-based) of the play-off slot
    mov al, [LP_ORD + eax]
    mov [DIYCOPY + 59h + ecx], al
    inc ecx
    cmp ecx, 24
    jb .t
    popad
    ret
.plain:
    jmp C8A2CE

lp_draw:                                ; called by hist_draw for this contest (esi = DIY buffer, ecx = clubs)
    cmp ecx, 16                         ; esi + 59h: the list; the round of 16 = stage 3 ([53h] = 2)
    jne .r
    cmp word [esi + 53h], 2
    jne .r
    pushad
    xor ecx, ecx
.c:
    mov al, [esi + 59h + ecx]           ; play-off winners (tie order)
    mov [LP_ORD + ecx], al
    inc ecx
    cmp ecx, 8
    jb .c
    xor ecx, ecx
.p:
    mov al, [LP_ORD + ecx]
    mov [esi + 59h + ecx*2], al         ; tie k: winner k (first leg at home) - seeded club k
    movzx eax, byte [LP_R16 + ecx]
    mov al, [esi + 59h + 16 + eax]      ; places 1-8 (lp_gend; the play-off round leaves list[16..23] alone)
    mov [esi + 59h + ecx*2 + 1], al
    inc ecx
    cmp ecx, 8
    jb .p
    popad
.r:
    ret

LP_CAL: CAL_BYTES
LP_PO: PO_BYTES
LP_R16: R16_BYTES
'''
WORK = 36 * 16 + 108 * 4 + 36           # LP_KEY, LP_OPP, LP_ORD: work buffers in obj2 (the obj1 page is full)

# play-off ties, R16 bracket order: tie k of the play-off feeds R16 tie k. Seeded order (places 0-based) 0 7 2 4 1 6 3 5
# = 1 8 3 5 | 2 7 4 6; their play-off groups: 1/2 <- 15/16 v 17/18, 3/4 <- 13/14 v 19/20, 5/6 <- 11/12 v 21/22,
# 7/8 <- 9/10 v 23/24. Top half takes 'pair 1' of each group (9-24, 11-22, 13-20, 15-18), bottom half 'pair 2'.
R16_SEEDS = [0, 7, 2, 4, 1, 6, 3, 5]
_GROUP = {0: 3, 1: 3, 2: 2, 3: 2, 4: 1, 5: 1, 6: 0, 7: 0}     # seeded place -> play-off group j (9+2j/10+2j v 24-2j/23-2j)


def playoff_slots():
    """LP_PO: 24 places (0-based): 16 play-off clubs (tie k = unseeded first: first leg at home), then places 1-8."""
    out = []
    for k, s in enumerate(R16_SEEDS):
        j = _GROUP[s]
        pair = 0 if k < 4 else 1
        seeded, unseeded = 8 + 2 * j + pair, 23 - 2 * j - pair
        out += [unseeded, seeded]
    return out + list(range(8))


def _sites(p):
    import lib97
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['A0']
    _, bye_call, c2573c, diycopy, _ = lib97._sites(p)
    diy = diycopy + 0x41F
    A = lambda x: struct.pack('<I', x)

    def one(pat, what):
        m = [x.start() for x in re.finditer(pat, d1, re.S)]
        assert len(m) == 1, (what, [hex(x) for x in m])
        return m[0]

    def call_to(at):
        assert d1[at] == 0xE8, hex(at)
        return at + 5 + struct.unpack_from('<i', d1, at + 1)[0]

    s = {'A0': a0, 'DIYCOPY': diycopy, 'DIY': diy}
    s['days'] = c2573c + 0x171                              # cseg_2573C+171h: call cseg_260A9
    s['C260A9'] = call_to(s['days'])
    assert d1[s['C260A9']:s['C260A9'] + 6] == b'\xc7\x05' + A(a0 + 4)
    c258e4 = call_to(bye_call + 5)
    # call cseg_27227; mov [A2], DIY; mov esi, [A2]; mov ax, [esi+49] (cseg_2653B and cseg_268C6): the one cseg_258E4
    # calls at +2E7h
    cand = [x.start() for x in re.finditer(rb'\xe8.{4}\xc7\x05' + re.escape(A(a0 + 8) + A(diy)) + rb'\x8b\x35'
                                           + re.escape(A(a0 + 8)) + rb'\x66\x8b\x46\x31', d1, re.S)]
    st = [x for x in range(c258e4, c258e4 + 0x800) if d1[x] == 0xE8 and call_to(x) in cand]
    assert [x - c258e4 for x in st][:1] == [0x2E7], ([hex(x - c258e4) for x in st], cand)   # (+635h: the cup one)
    s['start'], s['C2653B'] = st[0], call_to(st[0])
    s['pair'] = one(rb'\xc7\x05' + re.escape(A(a0) + A(diy)) + rb'\x8b\x35' + re.escape(A(a0)) + rb'\x66\x8b\x46\x5b',
                    'cseg_89758')
    s['sort'] = one(rb'\xc7\x05' + re.escape(A(a0 + 16) + A(diy)) + rb'\x8b\x35' + re.escape(A(a0 + 16))
                    + rb'\x66\x8b\x46\x4f', 'cseg_883DD')
    d1r, d2r = a0 - 28, a0 - 24
    s['res'] = one(rb'\x66\xa1' + re.escape(A(d1r)) + rb'\x8b\x35' + re.escape(A(a0 + 12)) + rb'\x66\x01\x86\xbf\x02\x00\x00'
                   + rb'\x66\xa1' + re.escape(A(d2r)) + rb'\x8b\x35' + re.escape(A(a0 + 12)) + rb'\x66\x01\x86\xc1\x02\x00\x00',
                   'cseg_88DA2')
    # cseg_8A2CE: mov esi, [A2]; mov al, [esi+2Dh]; mov [D0], al; mov al, [worldCup]... (4 such starts: the one
    # called from 2 sites, preceded by int 3; jmp $ / padding of the previous routine)
    starts = {x.start() for x in re.finditer(rb'\x8b\x35' + re.escape(A(a0 + 8)) + rb'\x8a\x46\x2d\xa2'
                                             + re.escape(A(a0 - 32)), d1, re.S)}
    calls = {}
    for x in range(len(d1) - 5):
        if d1[x] == 0xE8:
            t = x + 5 + struct.unpack_from('<i', d1, x + 1)[0]
            if t in starts:
                calls.setdefault(t, []).append(x)
    two = [t for t, c in calls.items() if len(c) == 2 and t > 0x70000]
    assert len(two) == 1, {hex(t): len(c) for t, c in calls.items()}
    c8a2ce = two[0]
    s['gend'] = calls[c8a2ce]
    s['C8A2CE'] = c8a2ce
    s.update(D1=d1r, D2=d2r)
    return s


def patch(p, cave, cups, area):
    """cups = [(contest id, countries in contest order)] (one prototype contest). Returns (end, lp_draw, id)."""
    import nasmcave
    assert len(cups) == 1, cups
    lp_id, countries = cups[0]
    assert len(countries) == N, len(countries)
    cal = draw(countries)
    check(cal, countries)
    s = _sites(p)
    a0 = s['A0']
    db = lambda b: 'db ' + ', '.join(str(x) for x in b)
    symbols = {'DIYCOPY': (2, s['DIYCOPY']), 'DIY': (2, s['DIY']), 'A0': (2, a0), 'A1': (2, a0 + 4), 'A2': (2, a0 + 8),
               'A3': (2, a0 + 12), 'A4': (2, a0 + 16), 'D1': (2, s['D1']), 'D2': (2, s['D2']),
               'LP_ID': (0, lp_id), 'AWAY_GF': (0, AWAY_GF),
               'C260A9': (1, s['C260A9']), 'C2653B': (1, s['C2653B']), 'C8A2CE': (1, s['C8A2CE']),
               'C89758_NEXT': (1, s['pair'] + 10), 'C883DD_NEXT': (1, s['sort'] + 10),
               'CAL_BYTES': (0, db(b for m in cal for b in m)), 'PO_BYTES': (0, db(playoff_slots())),
               'R16_BYTES': (0, db(R16_SEEDS))}
    work = area.add(bytes(WORK + 4))
    work = (work + 3) & ~3
    symbols.update(LP_KEY=(2, work), LP_OPP=(2, work + 576), LP_ORD=(2, work + 576 + 432))
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    lab = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    rel = lambda at, to: struct.pack('<i', to - (at + 5))
    p.put(1, s['days'] + 1, rel(s['days'], lab['lp_days']))
    p.put(1, s['start'] + 1, rel(s['start'], lab['lp_start']))
    for g in s['gend']:
        p.put(1, g + 1, rel(g, lab['lp_gend']))
    for site, name in ((s['pair'], 'lp_pair'), (s['sort'], 'lp_sort')):   # mov [Ax], offset DIY (10 B) -> jmp; nops
        p.remove(1, site + 2)
        p.remove(1, site + 6)
        p.put(1, site, b'\xe9' + rel(site, lab[name]) + b'\x90' * 5)
    p.remove(1, s['res'] + 2)                                    # mov ax, [D1]; mov esi, [A3] (12 B) -> call; nops
    p.remove(1, s['res'] + 8)
    p.put(1, s['res'], b'\xe8' + rel(s['res'], lab['lp_res']) + b'\x90' * 7)
    days = [cal[18 * d:18 * d + 18] for d in range(DAYS)]
    print(f'exe: league phase {lp_id:#x}: code obj1+{cave:#x}..{cave + len(code):#x}, sites ' +
          ', '.join(f'{k} {v:#x}' for k, v in s.items() if k in ('days', 'start', 'pair', 'sort', 'res')) +
          f"; day 1 {days[0][:3]}...; labels " + ' '.join(f'{k} {v:#x}' for k, v in lab.items() if k.startswith('lp_')))
    return cave + len(code), lab['lp_draw'], lp_id
