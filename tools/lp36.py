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
Also: lp_mkdraw (from lp_start) = the draw made by the game at every stage start (the model of rt draw below:
one-to-one per pot pair with backtracking, then 8 perfect matchings), written into DIY + CAL_OFF (saved with the
slot; the build's draw only as a fallback); lp_gend draws the seeded pairs of the play-offs and the halves of the
seeded pairs; lp_rank uses only criteria 1-5 + the names while the phase runs (UEFA); lp_hdr / lp_num / lp_col turn
the two group pages into one table 1-36 ('CLASSIFICA 1-18' / '19-36', 1-8 light blue, 9-24 green, 25-36 plain).
"""
import random
import re
import struct

N, POT, DAYS = 36, 9, 8
DC_CLUB = 0x99                  # diyFileBufferCopy: its team list's first club (file, ordinal; measured in a career)
FIXTURES = {}                   # (contest id, first club) -> (groups, clubs per group, days, [(home row, away row)]): a
                                # type-2 contest's first group stage played from a fixed calendar (e.g. a state
                                # championship's cross-group round robin); the game's own per-group tables
LABELS = {}                     # lp36 labels (uefacoef.py patches the lp_cb_* callbacks)
ROW = 0x2B3                     # team row r = DIY + ROW + 18 * r (+0 team dword, +4 played .. +16 points)
CAL_OFF = ROW + 18 * 36         # the season's draw: 144 (home row, away row), matchday order (rows 36..51: unused by a
AWAY_GF = CAL_OFF + 288         # 36-club stage, saved with the slot); then away goals (36 bytes), away wins (36 bytes)
DISC = AWAY_GF + 72             # then disciplinary points (36 bytes, criterion 9: yellow 1, expulsion 3; rows 56+)
# Cards of a match the engine did not play (simulated): Poisson per club and match, UEFA Champions League 2025-26 (189
# matches, 718 yellow cards, 45 red cards; kickoff.co.uk referee tables): 1.90 yellows and 0.119 expulsions per club.
YELLOW_RATE, RED_RATE = 718 / 189 / 2, 45 / 189 / 2


def poisson_cum(lam, n):
    """Thresholds in 1/256 (a random byte below t[k] -> k events), for k = 0 .. n - 1; above the last: n."""
    import math
    out, acc = [], 0.0
    for k in range(n):
        acc += math.exp(-lam) * lam ** k / math.factorial(k)
        out.append(min(255, round(acc * 256)))
    return out


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


def draw6(countries, seed=2025):
    """Conference League: 36 clubs in 6 pots of 6, one opponent from every pot (own pot included), 3 home / 3 away,
    the country rules; 6 matchdays of 18. Model of the asm (lp_mkdraw, 6-pot branch)."""
    rng = random.Random(seed)
    for attempt in range(1000):
        adj = [[0] * N for _ in range(N)]
        opp = {c: [] for c in range(N)}

        def fits(p, q):
            return (p != q and not adj[p][q] and countries[p] != countries[q]
                    and sum(countries[x] == countries[q] for x in opp[p]) < 2
                    and sum(countries[x] == countries[p] for x in opp[q]) < 2)

        def link(p, q, on):
            adj[p][q] = adj[q][p] = on
            if on:
                opp[p].append(q); opp[q].append(p)
            else:
                opp[p].remove(q); opp[q].remove(p)

        def match(P, Q):                    # a perfect matching P x Q (P == Q: inside the pot)
            free = [x for x in range(6 * P, 6 * P + 6)]
            used = set()

            def go():
                left = [x for x in free if x not in used]
                if not left:
                    return True
                p = left[0]
                cand = [q for q in range(6 * Q, 6 * Q + 6) if q not in used and q != p and fits(p, q)]
                if P == Q:
                    cand = [q for q in cand if q in left]
                rng.shuffle(cand)
                for q in cand:
                    used.update((p, q)) if P == Q else used.add(p)
                    if P != Q:
                        usedq.add(q)
                    link(p, q, 1)
                    if go():
                        return True
                    link(p, q, 0)
                    used.discard(p)
                    if P == Q:
                        used.discard(q)
                    else:
                        usedq.discard(q)
                return False
            usedq = set()
            if P != Q:                          # q must also be unused on the Q side
                old_fits = fits

                def go2():
                    left = [x for x in free if x not in used]
                    if not left:
                        return True
                    p = left[0]
                    cand = [q for q in range(6 * Q, 6 * Q + 6) if q not in usedq and old_fits(p, q)]
                    rng.shuffle(cand)
                    for q in cand:
                        used.add(p); usedq.add(q); link(p, q, 1)
                        if go2():
                            return True
                        link(p, q, 0); used.discard(p); usedq.discard(q)
                    return False
                return go2()
            return go()

        pairs = [(P, Q) for P in range(6) for Q in range(P, 6)]
        rng.shuffle(pairs)
        if not all(match(P, Q) for P, Q in pairs):
            continue
        rem = [row[:] for row in adj]           # Euler walks: every club 3 home, 3 away
        home = []
        for v in range(N):
            while any(rem[v]):
                cur = v
                while True:
                    ws = [w for w in range(N) if rem[cur][w]]
                    if not ws:
                        break
                    w = ws[0]
                    rem[cur][w] = rem[w][cur] = 0
                    home.append((cur, w))
                    cur = w
        days = None
        for _ in range(50):
            left, days = home[:], []
            for d in range(6):
                day = _matching(rng, left)
                if day is None:
                    break
                days.append(day)
                left = [m for m in left if m not in day]
            if len(days) == 6:
                return [m for d in days for m in d]
    raise RuntimeError('no draw')


def check6(cal, countries):
    assert len(cal) == 108
    for d in range(6):
        day = cal[18 * d:18 * d + 18]
        assert sorted(x for m in day for x in m) == list(range(N)), d
    for c in range(N):
        h = [a for x, a in cal if x == c]
        a = [x for x, y in cal if y == c]
        assert len(h) == 3 and len(a) == 3, c
        opps = h + a
        assert sorted(o // 6 for o in opps) == list(range(6)), c
        assert len(set(opps)) == 6
        assert all(countries[o] != countries[c] for o in opps)
        assert max(sum(countries[o] == k for o in opps) for k in set(countries)) <= 2


ASM = '''
%macro LP_IDS 1                        ; ZF = 1 if the contest id byte %1 is one of the league-phase ids
%if LP_TID
    cmp byte %1, LP_ID                  ; (a tourney pack's)
    je %%r
%endif
%if LP_W0
    cmp byte %1, 0                      ; (a world's Champions Cup)
    je %%r
%endif
%if LP_W1
    cmp byte %1, 1                      ; (a world's Cup Winners' Cup slot: Europa League)
    je %%r
%endif
%if LP_W2
    cmp byte %1, 2                      ; (a world's UEFA Cup slot: Conference League)
    je %%r
%endif
    cmp esp, 0                          ; ZF = 0
%%r:
%endmacro

lp_fmt:                                 ; al = contest id -> the format: Champions / Europa League 144 matches, 8 days,
    mov dword [W_NM], 144               ; 4 pots of 9 (at most 3 clubs of a country per pot); Conference League (id 2 of
    mov dword [W_ND], 8                 ; a world) 108 matches, 6 days, 6 pots of 6 (at most 2 per pot)
    mov dword [W_PS], 9
    mov dword [W_CAP], 3
%if LP_W2
    cmp al, 2
    jne .r
    mov dword [W_NM], 108
    mov dword [W_ND], 6
    mov dword [W_PS], 6
    mov dword [W_CAP], 2
.r:
%endif
    ret

lp_info1:                               ; DesignDIYTournamentOnDraw (STAT > INFO SU COMPETIZIONE): replaces `mov [A0],
    mov eax, INFO_GROUPS                ; offset '%0 GROUPS OF %1'`: the league phase's stage = 1 group of 36
    push LP_INFO1
    jmp lp_info2.s

lp_info2:                               ; replaces `mov [A0], offset '(TOP %0 IN EACH GROUP QUALIFY)'`: its qualifiers
    mov eax, INFO_TOP                   ; (eax is free at both sites: the game loads it next)
    push LP_INFO2
.s:
    call lp_info_ours
    jne .k
    mov eax, [esp]
.k:
    mov [A0], eax
    pop eax
    ret

lp_info3:                               ; replaces `mov ax, [esi+165h]` (esi = [A2], a group stage: the times each
    mov ax, [esi + 165h]                ; club meets each other, = 1 here: the index of the row's string table
    push esi                            ; 'AFFRONTA SQUAD. X 1..4'): a league phase of ours shows '8 AVVERSARIE X 1'
    mov esi, [AENT]                     ; the row's menu entry -> +26h its string table (var, first, strings)
    mov esi, [esi + 26h]
    mov dword [esi + 6], INFO_X1        ; (the game's own first string for any other contest)
    call lp_info_ours
    jne .r
    mov dword [esi + 6], LP_INFO3
.r:
    pop esi
    ret

lp_info_ours:                           ; ZF = 1: the stage shown ([A2]) is a league phase of ours: 2 groups of 18
    push esi
    LP_IDS [DIYCOPY + 2Dh]
    jne .r
    mov esi, [A2]
    cmp word [esi + 169h], 2
    jne .r
    cmp word [esi + 16Bh], 18
.r:
    pop esi
    ret

lp_copy_ours:                           ; ZF = 1: diyFileBufferCopy is a league-phase contest (any stage)
    LP_IDS [DIYCOPY + 2Dh]
    jne .r
    cmp word [DIYCOPY + 15Dh], 2        ; stage 1: 2 groups ...
    jne .r
    cmp word [DIYCOPY + 16Bh], 18       ; ... of 18
.r:
    ret

lp_days:                                ; replaces `call cseg_260A9` in cseg_2573C (stage days -> months)
    call [FX_COPY_V]                    ; (a fixture contest: lp36.fx_patch, else ZF = 0)
    jne .lp
    push eax
    mov eax, [esi + 8]
    mov [DIYCOPY + 173h], ax            ; a fixture contest: its days
    pop eax
    jmp .go
.lp:
    call lp_copy_ours
    jne .go
    push eax
    mov al, [DIYCOPY + 2Dh]
    call lp_fmt
    mov eax, [W_ND]
    mov [DIYCOPY + 173h], ax            ; 8 (6) matchdays, not 17
    pop eax
.go:
    jmp C260A9

lp_ours:                                ; ZF = 1: DIY_competitionStart is our league phase
    LP_IDS [DIY + 2Dh]
    jne .r
    cmp word [DIY + 4Fh], 2
    jne .r
    cmp word [DIY + 51h], 18
.r:
    ret

lp_start:                               ; replaces `call cseg_2653B` in cseg_258E4 (league start of a group stage)
    call C2653B
    call [FX_START_V]
    call lp_copy_ours                   ; (cseg_258E4 copies the id into DIY+2Dh only at its end)
    jne .r
    cmp word [DIY + 4Fh], 2
    jne .r
    cmp word [DIY + 51h], 18
    jne .r
    push eax
    mov al, [DIYCOPY + 2Dh]
    call lp_fmt
    mov eax, [W_NM]
    shr eax, 1
    mov [DIY + 69h], ax                 ; pair indices per cycle (2 groups: 144 or 108 matches)
    mov [DIY + 6Bh], ax
    mov eax, [W_ND]
    mov [DIY + 1C3h], ax                ; matchdays
    pop eax
    pushad
    call C2730A                         ; the month of each matchday again (cseg_2653B spread 17 of them)
    popad
    push edi
    push ecx
    push eax
    lea edi, [DIY + AWAY_GF]
    mov ecx, 108                        ; away goals, away wins, disciplinary points
    xor eax, eax
    rep stosb
    pop eax
    pop ecx
    pop edi
    call lp_mkdraw                      ; this season's draw into DIY + CAL_OFF
    call lp_cb_start                    ; (UEFA coefficients: participation)
.r:
    ret

lp_pair:                                ; replaces the first instruction of cseg_89758 (mov [A0], offset DIY)
    mov dword [A0], DIY
    call [FX_PAIR_V]
    jz .done
    call lp_ours
    jne .orig
    push eax
    push edx
    movzx eax, word [DIY + 1CBh]
    add eax, eax
    movzx edx, word [DIY + 5Bh]
    add eax, edx
    push eax
    mov al, [DIY + 2Dh]
    call lp_fmt
    pop eax
    cmp eax, [W_NM]
    jae .bad
    movzx edx, byte [DIY + CAL_OFF + eax*2]
    call lp_fresh
    movzx edx, byte [DIY + CAL_OFF + eax*2 + 1]
    call lp_fresh
    movzx edx, byte [DIY + CAL_OFF + eax*2]  ; home row
    imul edx, edx, 18
    add edx, DIY
    mov [A1], edx
    movzx edx, byte [DIY + CAL_OFF + eax*2 + 1]
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
.done:
    ret

fx_none:                                ; the fixture vectors' default: no fixture contests (ZF = 0)
    cmp esp, 0
    ret
align 4
ST_SORT_V: dd 0                         ; (statespec: st_isstate / st_resort, or 0)
ST_RESORT_V: dd 0
FX_COPY_V: dd fx_none
FX_START_V: dd fx_none
FX_PAIR_V: dd fx_none

lp_fresh:                               ; the team pointer of row edx again (VerifyTeamLoaded, as cseg_27227 does at the
    pushad                              ; stage start): 72 European clubs + a world's league and cup overflow the team
    mov esi, D0                         ; cache, so the pointers of the stage start go stale (the career calendar showed
    mov edi, LP_SAVE                    ; wrong opponents). The game's pseudo registers D0..A6 are kept.
    mov ecx, 15
.s:
    mov eax, [esi]
    mov [edi], eax
    add esi, 4
    add edi, 4
    dec ecx
    jnz .s
    mov [LP_ROW], edx
    movzx eax, word [DIY + 12Dh + edx*2]    ; team number of index edx
    mov [D0], eax
    call VERIFY
    mov eax, [A0]
    sub eax, [SELTEAMS]
    imul edx, [LP_ROW], 18
    mov [DIY + edx + 2B3h], eax
    mov esi, LP_SAVE
    mov edi, D0
    mov ecx, 15
.r:
    mov eax, [esi]
    mov [edi], eax
    add esi, 4
    add edi, 4
    dec ecx
    jnz .r
    popad
    ret

lp_res:                                 ; replaces `mov ax, [D1]; mov esi, [A3]` before the goals are added in cseg_88A12
    call lp_ours
    jne .r
    pushad
    call lp_cb_res                      ; (UEFA coefficients: A3 home row, A4 away row, D1 / D2 goals)
    mov eax, [A4]                       ; away row
    sub eax, DIY
    xor edx, edx
    mov ecx, 18
    div ecx
    cmp eax, 36
    jae .x
    mov ebx, eax                        ; away row
    mov dl, [D2]                        ; away goals
    add [DIY + AWAY_GF + eax], dl
    mov cx, [D2]
    cmp cx, [D1]
    jbe .d
    inc byte [DIY + AWAY_GF + 36 + eax] ; away win
.d:
    mov eax, [A3]                       ; home row
    sub eax, DIY
    xor edx, edx
    mov ecx, 18
    div ecx
    cmp eax, 36
    jae .x
    call lp_disc
.x:
    popad
.r:
    mov ax, [D1]
    mov esi, [A3]
    ret

lp_disc:                                ; eax = home row, ebx = away row: the match's disciplinary points (criterion 9)
    mov esi, eax
    cmp byte [LP_GPLAY], 0              ; the engine played a match: are these its two clubs?
    je .sim
    mov ecx, esi
    call lp_tptr
    mov edx, eax                        ; home team
    mov ecx, ebx
    call lp_tptr                        ; eax = away team
    mov edi, T1STATS
    mov ecx, T2STATS
    cmp edx, [LP_G1]
    jne .sw
    cmp eax, [LP_G2]
    je .pl
.sw:
    xchg edi, ecx
    cmp edx, [LP_G2]
    jne .sim
    cmp eax, [LP_G1]
    jne .sim
.pl:                                    ; statistics of the played match: bookings = yellow cards that were not a
    mov byte [LP_GPLAY], 0              ; second one, sendingsOff = expulsions (second yellow or red): 1 and 3 points
    movzx eax, word [edi + 6]
    movzx edx, word [edi + 8]
    lea eax, [eax + edx*2]
    add eax, edx
    mov edx, esi
    call lp_dadd
    movzx eax, word [ecx + 6]
    movzx edx, word [ecx + 8]
    lea eax, [eax + edx*2]
    add eax, edx
    mov edx, ebx
    jmp lp_dadd
.sim:                                   ; a simulated match: cards drawn with the real rates
    mov edx, esi
    call .one
    mov edx, ebx
.one:
    push edx
    mov ecx, 256
    call lp_rand
    mov edi, LP_YCUM                    ; yellows: k = the first threshold above the random byte
    call .cnt
    push eax
    mov ecx, 256
    call lp_rand
    mov edi, LP_RCUM
    call .cnt
    lea edx, [eax + eax*2]              ; 3 points per expulsion
    pop eax
    add eax, edx
    pop edx
    jmp lp_dadd
.cnt:                                   ; eax = random byte, edi = thresholds (FF-ended) -> eax = their count below it
    xor edx, edx
.c1:
    cmp byte [edi + edx], 0FFh
    je .c2
    cmp al, [edi + edx]
    jb .c2
    inc edx
    jmp .c1
.c2:
    mov eax, edx
    ret

lp_dadd:                                ; DISC[edx] += eax (at most 255)
    add al, [DIY + DISC + edx]
    jnc .s
    mov al, 0FFh
.s:
    mov [DIY + DISC + edx], al
    ret

lp_tptr:                                ; ecx = row -> eax = its team record
    imul eax, ecx, 18
    mov eax, [DIY + eax + 2B3h]
    add eax, [SELTEAMS]
    ret

lp_game:                                ; replaces `mov eax, [A1]; mov [gameTeam1], eax` in InitializeInGameTeamsAndStartGame:
    mov eax, [A2]                       ; the engine plays a match between these two clubs (lp_disc takes its
    mov [LP_G2], eax                    ; statistics when the result is added)
    mov eax, [A1]
    mov [LP_G1], eax
    mov byte [LP_GPLAY], 1
    mov [GAMET1], eax
    ret

; key per row (4 dwords, compared from the first): points | goal difference; goals | away goals | wins | away
; wins; opponents' points | opponents' goal difference | opponents' goals; 255 - disciplinary points | club coefficient
; (uefacoef; else 255 - contest order). UEFA 2026-27 art. 18.01, criteria 1-10. Then the row.
lp_sort:                                ; replaces the first instruction of cseg_883DD (mov [A4], offset DIY)
    mov dword [A4], DIY
    call lp_ours
    je lp_rank
    cmp dword [ST_SORT_V], 0            ; a state championship (statespec.st_isstate, ZF = 1): the game's sort, then
    je .g                               ; its tie-breaks (st_resort: points, wins, goal difference, goals)
    call [ST_SORT_V]
    jne .g
    push dword [ST_RESORT_V]            ; (the game's ret goes there, st_resort's to the caller)
.g:
    jmp C883DD_NEXT

lp_rank:                                ; LP_ORD = rows best first, written into DIY+6Dh
    pushad
    mov al, [DIY + 2Dh]
    call lp_fmt
    xor ecx, ecx
.z:
    mov dword [LP_OPP + ecx*4], 0       ; opponents' points / GD / GF (3 x 36 dwords)
    inc ecx
    cmp ecx, 108
    jb .z
    xor ecx, ecx
.m:                                     ; every match of the draw (played or not): add each side's figures to the other
    movzx esi, byte [DIY + CAL_OFF + ecx*2]
    movzx edi, byte [DIY + CAL_OFF + ecx*2 + 1]
    call .acc
    xchg esi, edi
    call .acc
    inc ecx
    cmp ecx, [W_NM]
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
    sub eax, ecx                        ; criterion 10: the club coefficient (uefacoef), else the contest order
    cmp word [DIY + 5Fh], 0             ; phase still running (UEFA: only criteria 1-5, then the names)
    je .fin
    mov dword [edi + 8], 0
    call .alpha
    jmp .k3
.fin:
    mov edx, ecx
    call lp_cb_coef
    cmp eax, 0FFFFFFh
    jbe .f1
    mov eax, 0FFFFFFh
.f1:
    movzx edx, byte [DIY + DISC + ecx]  ; criterion 9: fewer disciplinary points first
    not dl
    shl edx, 24
    or eax, edx
.k3:
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
.alpha:                                 ; eax = 255 - clubs whose name sorts before row ecx's
    push ebx
    push ecx
    push edx
    push esi
    push edi
    mov ebx, ecx
    xor edx, edx                        ; count
    xor ecx, ecx
.a1:
    imul esi, ecx, 18                   ; name of row ecx (team record + 5) vs name of row ebx
    mov esi, [DIY + esi + 2B3h]
    add esi, [SELTEAMS]
    add esi, 5
    imul edi, ebx, 18
    mov edi, [DIY + edi + 2B3h]
    add edi, [SELTEAMS]
    add edi, 5
.a2:
    mov al, [esi]
    cmp al, [edi]
    jb .a4                              ; row ecx first
    ja .a5
    test al, al
    jz .a5
    inc esi
    inc edi
    jmp .a2
.a4:
    inc edx
.a5:
    inc ecx
    cmp ecx, 36
    jb .a1
    mov eax, 255
    sub eax, edx
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
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
.t:                                     ; list[0..15]: play-off ties (unseeded club first: first leg at home)
    movzx eax, byte [LP_PO + ecx]
    mov al, [LP_ORD + eax]
    mov [DIYCOPY + 59h + ecx], al
    inc ecx
    cmp ecx, 16
    jb .t
    xor ecx, ecx
.s:                                     ; list[16..23]: the seeded club of round-of-16 tie k (the play-off round
    movzx eax, byte [LP_R16 + ecx]      ; puts its winners in list[0..7] in tie order, leaves [16..23] alone)
    mov al, [LP_ORD + eax]
    mov [DIYCOPY + 59h + 16 + ecx], al
    inc ecx
    cmp ecx, 8
    jb .s
    xor ebx, ebx                        ; the draws: in each play-off pair (9/10 v 23/24 ...) which seeded club
.d:                                     ; meets which; in each seeded pair (1/2, 8/7, 3/4, 5/6) which half
    mov ecx, 2
    call lp_rand
    test eax, eax
    jz .d2
    mov al, [DIYCOPY + 59h + ebx*2 + 1]
    xchg al, [DIYCOPY + 59h + ebx*2 + 9]
    mov [DIYCOPY + 59h + ebx*2 + 1], al
.d2:
    mov ecx, 2
    call lp_rand
    test eax, eax
    jz .d3
    mov al, [DIYCOPY + 59h + 16 + ebx]
    xchg al, [DIYCOPY + 59h + 20 + ebx]
    mov [DIYCOPY + 59h + 16 + ebx], al
.d3:
    inc ebx
    cmp ebx, 4
    jb .d
    call lp_cb_gend                     ; (UEFA coefficients: the ranking in LP_ORD)
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
    mov [esi + 59h + ecx*2], al         ; tie k: winner k (first leg at home) - seeded club k (lp_gend)
    mov al, [esi + 59h + 16 + ecx]
    mov [esi + 59h + ecx*2 + 1], al
    inc ecx
    cmp ecx, 8
    jb .p
    popad
.r:
    jmp lp_cb_draw                      ; (UEFA coefficients: every knockout round's clubs, esi / ecx)

; ---- The draw at the stage start (positions p = places in the contest list = pots of 9; team rows = list[p]) ----
; Model: tools/lp36.py rt_draw. For each ordered pot pair (P, Q), in a random rotation of the 16: a one-to-one
; 'p hosts q' (backtracking, random rotations), q != p, no rematch, no club of the same country, at most 2 opponents
; of one country. Then 8 matchdays: perfect matchings of the 144 matches (backtracking, first free club).
; Countries: LP_CTRYS (a tourney pack's own list, by position) or the team word's file byte (careers).
lp_rand:                                ; eax = random 0..ecx-1 (ecx <= 256); the game's Rand2 (D0 kept)
    push dword [D0]
    pushad
    call RAND2
    popad
    movzx eax, byte [D0]
    imul eax, ecx
    shr eax, 8
    pop dword [D0]
    ret

lp_mkdraw:
    pushad
    mov al, [DIYCOPY + 2Dh]
    call lp_fmt
    xor ecx, ecx                        ; W_CP[p] = country of list position p
.cp:
    movzx ebx, byte [DIYCOPY + 59h + ecx]
    mov al, [DIY + 12Dh + ebx*2]        ; a career: the club's team file = its country (DIY's team numbers, as
                                        ; cseg_27227 reads them: diyFileBufferCopy+99h is not kept in a career)
%if LP_TID
    cmp byte [DIYCOPY + 2Dh], LP_ID     ; a tourney pack (one team file): its clubs' countries
    jne .cp1
    mov al, [LP_CTRYS + ecx]
.cp1:
%endif
    mov [W_CP + ecx], al
    inc ecx
    cmp ecx, 36
    jb .cp
    xor ecx, ecx                        ; W_POS[q] = the list position drawn as q (pots = q / 9)
.i:
    mov [W_POS + ecx], cl
    inc ecx
    cmp ecx, 36
    jb .i
%if LP_TID
    cmp byte [DIYCOPY + 2Dh], LP_ID     ; a tourney pack: the list is in pot order
    je .sorted
%endif
    xor ecx, ecx                        ; a career: pots by strength (the 16 players' value; the club coefficients
.v:                                     ; later), the list comes country by country from the season end
    movzx edx, byte [DIYCOPY + 59h + ecx]
    call lp_fresh
    imul eax, edx, 18
    mov esi, [DIY + eax + 2B3h]
    add esi, [SELTEAMS]
    xor eax, eax
    xor ebx, ebx
.pv:
    movzx edi, byte [esi + 76 + 32]     ; player price byte
    add eax, edi
    add esi, 38
    inc ebx
    cmp ebx, 16
    jb .pv
    call lp_cb_str                      ; (UEFA coefficients: eax = the pot key of team edx)
    mov [W_STR + ecx*4], eax
    inc ecx
    cmp ecx, 36
    jb .v
    mov ecx, 1                          ; insertion sort, strongest first (stable)
.s1:
    cmp ecx, 36
    jae .cap
    mov bl, [W_POS + ecx]
    mov edx, ecx
.s2:
    test edx, edx
    jz .s3
    movzx esi, byte [W_POS + edx - 1]
    movzx edi, bl
    mov eax, [W_STR + esi*4]
    cmp eax, [W_STR + edi*4]
    jae .s3
    mov al, [W_POS + edx - 1]
    mov [W_POS + edx], al
    dec edx
    jmp .s2
.s3:
    mov [W_POS + edx], bl
    inc ecx
    jmp .s1
.cap:                                   ; pots in strength order with at most 3 clubs of a country per pot (a pot
    mov edi, W_USED2                    ; of 5 English clubs would make the draw impossible)
    mov ecx, 36
    xor eax, eax
    rep stosb
    xor ebx, ebx                        ; q
.pot:
    mov edi, W_CNT
    mov ecx, 256
    xor eax, eax
    rep stosb
.slot:
    xor ecx, ecx
.find:
    cmp ecx, 36
    jae .any
    cmp byte [W_USED2 + ecx], 0
    jne .nf
    movzx eax, byte [W_POS + ecx]
    movzx eax, byte [W_CP + eax]
    movzx eax, byte [W_CNT + eax]
    cmp eax, [W_CAP]
    jb .take
.nf:
    inc ecx
    jmp .find
.any:                                   ; (only clubs of full countries left: the strongest of them)
    xor ecx, ecx
.a1:
    cmp byte [W_USED2 + ecx], 0
    je .take
    inc ecx
    jmp .a1
.take:
    mov byte [W_USED2 + ecx], 1
    movzx eax, byte [W_POS + ecx]
    mov [W_POS2 + ebx], al
    movzx eax, byte [W_CP + eax]
    inc byte [W_CNT + eax]
    inc ebx
    cmp ebx, 36
    jae .capped
    mov eax, ebx
    xor edx, edx
    div dword [W_PS]
    test edx, edx
    jnz .slot
    jmp .pot
.capped:
    xor ecx, ecx
.c2:
    mov al, [W_POS2 + ecx]
    mov [W_POS + ecx], al
    inc ecx
    cmp ecx, 36
    jb .c2
.sorted:
    xor ecx, ecx
.ct:
    movzx ebx, byte [W_POS + ecx]
    mov al, [W_CP + ebx]
    mov [W_CTRY + ecx], al
    inc ecx
    cmp ecx, 36
    jb .ct
    mov dword [W_TRY], 60
.att:
    dec dword [W_TRY]
    js .fallback
    mov edi, W_ADJ                      ; no matches yet
    mov ecx, 36 * 36
    xor eax, eax
    rep stosb
    mov dword [W_NE], 0
    mov dword [W_STEPS], 0
    cmp dword [W_PS], 6
    je .six
    mov ecx, 16
    call lp_rand
    mov [W_R0], eax
    mov dword [W_T], 0
.pair:
    mov eax, [W_T]
    add eax, [W_R0]
    and eax, 15
    mov edx, eax
    shr eax, 2
    imul eax, eax, 9
    mov [W_P], eax                      ; first position of pot P
    and edx, 3
    imul edx, edx, 9
    mov [W_Q], edx
    mov edi, W_USED
    mov ecx, 36
    xor eax, eax
    rep stosb
    mov ecx, 9
    call lp_rand
    mov [W_ROT], eax
    xor ebx, ebx
    call lp_bij
    jnc .att                            ; CF = 1: done
    inc dword [W_T]
    cmp dword [W_T], 16
    jb .pair
.sched:
    mov dword [W_STRY], 20              ; 144 (108) matches: now the matchdays
.sch:
    dec dword [W_STRY]
    js .att
    mov edi, W_DAY
    mov ecx, 144
    mov al, 0FFh
    rep stosb
    mov dword [W_D], 0
.day:
    mov edi, W_FREE
    mov ecx, 36
    mov al, 1
    rep stosb
    mov dword [W_STEPS], 0
    call lp_match
    jnc .sch
    inc dword [W_D]
    mov eax, [W_D]
    cmp eax, [W_ND]
    jb .day
    xor edx, edx                        ; write the calendar: matchday 1 first, rows = list[position]
    xor ecx, ecx
.w0:
    xor ebx, ebx
.w1:
    cmp [W_DAY + ebx], cl
    jne .w2
    movzx eax, byte [W_EH + ebx]
    movzx eax, byte [W_POS + eax]
    mov al, [DIYCOPY + 59h + eax]
    mov [DIY + CAL_OFF + edx*2], al
    movzx eax, byte [W_EA + ebx]
    movzx eax, byte [W_POS + eax]
    mov al, [DIYCOPY + 59h + eax]
    mov [DIY + CAL_OFF + edx*2 + 1], al
    inc edx
.w2:
    inc ebx
    cmp ebx, [W_NM]
    jb .w1
    inc ecx
    cmp ecx, [W_ND]
    jb .w0
    popad
    ret
.fallback:                              ; (never seen in tests) the build's draw, by position
    mov esi, LP_CAL
    cmp dword [W_PS], 6
    jne .f0
    mov esi, LP_CAL6
.f0:
    mov edx, [W_NM]
    add edx, edx
    xor ecx, ecx
.f1:
    movzx eax, byte [esi + ecx]
    movzx eax, byte [W_POS + eax]
    mov al, [DIYCOPY + 59h + eax]
    mov [DIY + CAL_OFF + ecx], al
    inc ecx
    cmp ecx, edx
    jb .f1
    popad
    ret
.six:                                   ; Conference League: a perfect matching for each of the 21 pot pairs
    mov ecx, 21                         ; (own pot included: one opponent per pot), then home / away by Euler
    call lp_rand                        ; walks (every club 3 home, 3 away)
    mov [W_R0], eax
    mov dword [W_T], 0
.p6:
    mov eax, [W_T]
    add eax, [W_R0]
    xor edx, edx
    mov ecx, 21
    div ecx
    movzx eax, byte [LP_PAIRS6 + edx*2]
    imul eax, eax, 6
    mov [W_P], eax
    movzx eax, byte [LP_PAIRS6 + edx*2 + 1]
    imul eax, eax, 6
    mov [W_Q], eax
    mov edi, W_USED
    mov ecx, 36
    xor eax, eax
    rep stosb
    call lp_m6
    jnc .att
    inc dword [W_T]
    cmp dword [W_T], 21
    jb .p6
    mov dword [W_NE], 0                 ; Euler walks over W_ADJ (consumed): cur -> w = cur at home
    xor ebx, ebx                        ; v
.e0:
    imul esi, ebx, 36
    xor ecx, ecx
.e1:
    cmp byte [W_ADJ + esi + ecx], 0
    jne .e2
    inc ecx
    cmp ecx, 36
    jb .e1
    inc ebx                             ; v has no edge left
    cmp ebx, 36
    jb .e0
    jmp .sched
.e2:
    mov edx, ebx                        ; cur = v
.e3:
    imul esi, edx, 36
    xor ecx, ecx
.e4:
    cmp byte [W_ADJ + esi + ecx], 0
    jne .e5
    inc ecx
    cmp ecx, 36
    jb .e4
    jmp .e0                             ; the walk is back at v (even degrees)
.e5:
    mov byte [W_ADJ + esi + ecx], 0
    imul eax, ecx, 36
    mov byte [W_ADJ + eax + edx], 0
    mov eax, [W_NE]
    mov [W_EH + eax], dl
    mov [W_EA + eax], cl
    inc dword [W_NE]
    mov edx, ecx
    jmp .e3

lp_fits:                                ; CF = 1 if position esi may host / meet edi
    cmp esi, edi
    je .no
    imul eax, esi, 36
    cmp byte [W_ADJ + eax + edi], 0
    jne .no
    mov al, [W_CTRY + esi]
    cmp al, [W_CTRY + edi]
    je .no
    push esi
    push edi
    call .cnt                           ; opponents of esi from the country of edi
    pop edi
    pop esi
    cmp ecx, 2
    jae .no
    push esi
    push edi
    xchg esi, edi
    call .cnt
    pop edi
    pop esi
    cmp ecx, 2
    jae .no
    stc
    ret
.no:
    clc
    ret
.cnt:                                   ; ecx = opponents of esi with the country of edi
    mov dl, [W_CTRY + edi]
    imul esi, esi, 36
    xor ecx, ecx
    xor eax, eax
.c1:
    cmp byte [W_ADJ + esi + eax], 0
    je .c2
    cmp [W_CTRY + eax], dl
    jne .c2
    inc ecx
.c2:
    inc eax
    cmp eax, 36
    jb .c1
    ret

lp_bij:                                 ; ebx = i (0..9); CF = 1: the rest of the one-to-one P -> Q found
    cmp ebx, 9
    jb .go
    stc
    ret
.go:
    inc dword [W_STEPS]
    cmp dword [W_STEPS], 20000
    ja .fail
    mov eax, ebx                        ; p = P + (i + rot) mod 9
    add eax, [W_ROT]
    xor edx, edx
    mov ecx, 9
    div ecx
    mov esi, edx
    add esi, [W_P]
    mov ecx, 9
    call lp_rand
    push eax                            ; [esp+4] = r, [esp] = k
    push dword 0
.k:
    mov eax, [esp]
    add eax, [esp + 4]
    xor edx, edx
    mov ecx, 9
    div ecx
    mov edi, edx
    add edi, [W_Q]                      ; q
    cmp byte [W_USED + edi], 0
    jne .next
    call lp_fits
    jnc .next
    mov byte [W_USED + edi], 1
    imul eax, esi, 36
    mov byte [W_ADJ + eax + edi], 1
    imul eax, edi, 36
    mov byte [W_ADJ + eax + esi], 1
    mov eax, [W_NE]
    mov ecx, esi
    mov [W_EH + eax], cl
    mov ecx, edi
    mov [W_EA + eax], cl
    inc dword [W_NE]
    push esi
    push edi
    push ebx
    inc ebx
    call lp_bij
    pop ebx
    pop edi
    pop esi
    jc .ok
    dec dword [W_NE]
    mov byte [W_USED + edi], 0
    imul eax, esi, 36
    mov byte [W_ADJ + eax + edi], 0
    imul eax, edi, 36
    mov byte [W_ADJ + eax + esi], 0
.next:
    inc dword [esp]
    cmp dword [esp], 9
    jb .k
    add esp, 8
.fail:
    clc
    ret
.ok:
    add esp, 8
    stc
    ret

lp_m6:                                  ; Conference League: matching of pot W_P with pot W_Q (the same pot too):
    inc dword [W_STEPS]                 ; CF = 1 when every club of W_P has its opponent of W_Q
    cmp dword [W_STEPS], 20000
    ja .fail
    mov esi, [W_P]                      ; first free club of pot P
    mov ecx, 6
.f:
    cmp byte [W_USED + esi], 0
    je .got
    inc esi
    dec ecx
    jnz .f
    stc
    ret
.got:
    mov ecx, 6
    call lp_rand
    push eax                            ; [esp+4] = r, [esp] = k
    push dword 0
.k:
    mov eax, [esp]
    add eax, [esp + 4]
    xor edx, edx
    mov ecx, 6
    div ecx
    mov edi, edx
    add edi, [W_Q]                      ; q
    cmp byte [W_USED + edi], 0
    jne .next
    call lp_fits
    jnc .next
    mov byte [W_USED + esi], 1
    mov byte [W_USED + edi], 1
    imul eax, esi, 36
    mov byte [W_ADJ + eax + edi], 1
    imul eax, edi, 36
    mov byte [W_ADJ + eax + esi], 1
    push esi
    push edi
    call lp_m6
    pop edi
    pop esi
    jc .ok
    mov byte [W_USED + esi], 0
    mov byte [W_USED + edi], 0
    imul eax, esi, 36
    mov byte [W_ADJ + eax + edi], 0
    imul eax, edi, 36
    mov byte [W_ADJ + eax + esi], 0
.next:
    inc dword [esp]
    cmp dword [esp], 6
    jb .k
    add esp, 8
.fail:
    clc
    ret
.ok:
    add esp, 8
    stc
    ret

lp_match:                               ; one matchday W_D: CF = 1 if every free club got a match
    inc dword [W_STEPS]
    cmp dword [W_STEPS], 5000
    ja .fail
    xor esi, esi                        ; first free club
.f:
    cmp byte [W_FREE + esi], 0
    jne .got
    inc esi
    cmp esi, 36
    jb .f
    stc
    ret
.got:
    mov ecx, [W_NM]
    call lp_rand
    push eax                            ; [esp+4] = r, [esp] = k
    push dword 0
.k:
    mov eax, [esp]
    add eax, [esp + 4]
    cmp eax, [W_NM]
    jb .e
    sub eax, [W_NM]
.e:
    mov ebx, eax                        ; match e
    cmp byte [W_DAY + ebx], 0FFh
    jne .next
    movzx edi, byte [W_EA + ebx]
    movzx eax, byte [W_EH + ebx]
    cmp eax, esi
    je .o
    movzx edi, byte [W_EH + ebx]
    movzx eax, byte [W_EA + ebx]
    cmp eax, esi
    jne .next
.o:
    cmp byte [W_FREE + edi], 0
    je .next
    mov byte [W_FREE + esi], 0
    mov byte [W_FREE + edi], 0
    mov al, [W_D]
    mov [W_DAY + ebx], al
    push esi
    push edi
    push ebx
    call lp_match
    pop ebx
    pop edi
    pop esi
    jc .ok
    mov byte [W_FREE + esi], 1
    mov byte [W_FREE + edi], 1
    mov byte [W_DAY + ebx], 0FFh
.next:
    inc dword [esp]
    mov eax, [W_NM]
    cmp [esp], eax
    jb .k
    add esp, 8
.fail:
    clc
    ret
.ok:
    add esp, 8
    stc
    ret

; The table screen (DIYLeagueTournament16BeforeDraw, also the career's group tables): one table of 36 on two pages.
lp_hdr:                                 ; replaces `mov [A0], offset cseg_49E7A` (the 'GROUP A..H' names)
    mov dword [A0], C49E7A
    call lp_ours
    jne .r
    mov dword [A0], LP_HDR              ; 'CLASSIFICA 1-18' / 'CLASSIFICA 19-36'
.r:
    ret

lp_num:                                 ; replaces `mov ax, [D5]` (row number on the page, 1..18)
    mov ax, [D5]
    call lp_ours
    jne .r
    mov ax, [D7]                        ; offset of the row in DIY+6Dh = 2 x place (0-based, both groups)
    shr ax, 1
    inc ax
.r:
    ret

lp_col:                                 ; replaces `mov ax, [dseg_11F41C]` at cseg_49B65 (row colour D3 final)
    call lp_ours
    jne .r
    push eax
    push edx
    push esi
    movzx eax, word [D7]
    shr eax, 1                          ; place 0..35
    mov dx, 0Dh                         ; 1-8: round of 16 (light blue)
    cmp eax, 8
    jb .c
    mov dx, 0Eh                         ; 9-24: play-offs (green)
    cmp eax, 24
    jb .c
    mov word [D3], 7                    ; 25-36: out (the game's plain row, computer clubs' names red)
    mov dx, 10
    jmp .n
.c:
    mov [D3], dx
.n:
    mov esi, [A1]                       ; club (team file record): computer club -> name in the row colour
    cmp byte [esi + 4], 1
    jne .x
    mov esi, [A5]
    mov [esi + 1Eh], dx
.x:
    pop esi
    pop edx
    pop eax
.r:
    mov ax, [C11F41C]
    ret

LP_HDR: dd LP_S1, LP_S2

; callbacks of tools/uefacoef.py (UEFA coefficients in a league-phase world): `ret` until it patches them to `jmp`
lp_cb_start:
    ret
    times 4 nop
lp_cb_res:
    ret
    times 4 nop
lp_cb_gend:
    ret
    times 4 nop
lp_cb_draw:
    ret
    times 4 nop
lp_cb_str:
    ret
    times 4 nop
lp_cb_coef:                             ; edx = row, eax = fallback -> eax = its club coefficient
    ret
    times 4 nop

LP_YCUM: YCUM_BYTES
LP_RCUM: RCUM_BYTES

LP_PAIRS6: PAIRS6_BYTES
LP_PO: PO_BYTES
LP_R16: R16_BYTES
'''
WORK = 36 * 16 + 108 * 4 + 36           # LP_KEY, LP_OPP, LP_ORD: work buffers in obj2 (the obj1 page is full)
W_LAYOUT, _at = {}, 0                   # the draw's work area (obj2, not saved: the result is in DIY + CAL_OFF)
for _n, _sz in (('W_TRY', 4), ('W_NE', 4), ('W_STEPS', 4), ('W_R0', 4), ('W_T', 4), ('W_P', 4), ('W_Q', 4), ('W_ROT', 4),
                ('W_STRY', 4), ('W_D', 4), ('LP_SAVE', 60), ('LP_ROW', 4), ('W_STR', 144), ('W_POS', 36), ('W_POS2', 36), ('W_CP', 36), ('W_USED2', 36),
                ('W_CNT', 256), ('W_NM', 4), ('W_ND', 4), ('W_PS', 4), ('W_CAP', 4), ('W_CTRY', 36), ('W_ADJ', 36 * 36), ('W_USED', 36), ('W_FREE', 36),
                ('W_DAY', 144), ('W_EH', 144), ('W_EA', 144), ('LP_G1', 4), ('LP_G2', 4), ('LP_GPLAY', 4)):
    W_LAYOUT[_n], _at = _at, _at + _sz
WORK_DRAW = _at

# play-off ties, R16 bracket order: tie k of the play-off feeds R16 tie k. Seeded order (places 0-based) 0 7 2 4 1 6 3 5
# = 1 8 3 5 | 2 7 4 6; their play-off groups: 1/2 <- 15/16 v 17/18, 3/4 <- 13/14 v 19/20, 5/6 <- 11/12 v 21/22,
# 7/8 <- 9/10 v 23/24. Top half takes 'pair 1' of each group (9-24, 11-22, 13-20, 15-18), bottom half 'pair 2'.
R16_SEEDS = [0, 7, 2, 4, 1, 6, 3, 5]
_GROUP = {0: 3, 1: 3, 2: 2, 3: 2, 4: 1, 5: 1, 6: 0, 7: 0}     # seeded place -> play-off group j (9+2j/10+2j v 24-2j/23-2j)


FX_ASM = '''
; --- fixture contests (FIXTURES): FX_TAB entries of 20 bytes: db id, groups, clubs per group, 0; dd matches; dd days;
; dd calendar (obj2: (home row, away row) bytes in day order); dw first club (file, ordinal: several state championships
; share one contest id), 0
fx_find:                                ; al = id, cx = groups, dx = clubs per group, bx = first club -> esi, ZF = 1
    mov esi, FX_TAB
.l:
    cmp esi, FX_END
    jae .no
    cmp al, [esi]
    jne .n
    cmp cl, [esi + 1]
    jne .n
    cmp dl, [esi + 2]
    jne .n
    cmp word [esi + 16], 0FFFFh         ; (any first club)
    je .r
    cmp bx, [esi + 16]
    je .r
.n:
    add esi, 20
    jmp .l
.no:
    cmp esp, 0                          ; ZF = 0
.r:
    ret

fx_copy:                                ; diyFileBufferCopy's first stage -> esi = its fixture entry, ZF = 1
    push eax
    push ebx
    push ecx
    push edx
    mov al, [DIYCOPY + 2Dh]
    mov bx, [DIYCOPY + DC_CLUB]         ; (its team list's first club)
    mov cx, [DIYCOPY + 15Dh]
    mov dx, [DIYCOPY + 16Bh]
    call fx_find
    pop edx
    pop ecx
    pop ebx
    pop eax
    ret

fx_ours:                                ; the running stage (DIY_competitionStart) -> esi = its entry, ZF = 1
    push eax                            ; (fx_start: the id still in DIYCOPY, cseg_258E4 copies it at its end)
    push ebx
    push ecx
    push edx
    mov al, [DIY + 2Dh]
    cmp byte [DIY], 0                   ; (a league layout: a group stage running)
    jne .x
.id:
    mov bx, [DIY + 12Dh]                ; the team table's row 0
    mov cx, [DIY + 4Fh]
    mov dx, [DIY + 51h]
    call fx_find
.x:
    pop edx
    pop ecx
    pop ebx
    pop eax
    ret

fx_start_find:                          ; as fx_ours, the id from DIYCOPY
    push eax
    mov al, [DIYCOPY + 2Dh]
    push ebx
    push ecx
    push edx
    jmp fx_ours.id

fx_start:                               ; (after cseg_2653B) a fixture contest's stage: pair indices per cycle =
    pushad                              ; matches / groups, its days, the months again
    call fx_start_find                  ; (the id is in DIYCOPY: cseg_258E4 copies it into DIY+2Dh at its end)
    jne .r
    mov eax, [esi + 4]
    xor edx, edx
    movzx ecx, byte [esi + 1]
    div ecx
    mov [DIY + 69h], ax
    mov [DIY + 6Bh], ax
    mov eax, [esi + 8]
    mov [DIY + 1C3h], ax
    call C2730A
.r:
    popad
    ret

fx_pair:                                ; ZF = 1: the pairing done from the calendar (A1 = home row, A2 = away row)
    call fx_ours
    jne .r
    push eax
    push ecx
    push edx
    movzx eax, word [DIY + 1CBh]        ; match m = groups * pair index + group
    movzx ecx, byte [esi + 1]
    mul ecx
    movzx edx, word [DIY + 5Bh]
    add eax, edx
    cmp eax, [esi + 4]
    jae .bad
    mov ecx, [esi + 12]
    lea ecx, [ecx + eax * 2]
    movzx edx, byte [ecx]
    call LP_FRESH
    movzx edx, byte [ecx + 1]
    call LP_FRESH
    movzx edx, byte [ecx]
    imul edx, edx, 18
    add edx, DIY
    mov [A1], edx
    movzx edx, byte [ecx + 1]
    imul edx, edx, 18
    add edx, DIY
    mov [A2], edx
    pop edx
    pop ecx
    pop eax
    cmp eax, eax                        ; ZF = 1
    ret
.bad:
    pop edx
    pop ecx
    pop eax
    cmp esp, 0
.r:
    ret

'''


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
    _, bye_call, c2573c, diycopy, _, _, _, _, _, _ = lib97._sites(p)
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
    s['C2730A'] = call_to(s['C2653B'] + 0x217 - 0x10000 + 0x10000) if d1[s['C2653B'] + 0x217] == 0xE8 else None
    if s['C2730A'] is None:            # (ITA offsets differ a little: the last call before the 2 words stored)
        k = [x for x in range(s['C2653B'], s['C2653B'] + 0x300) if d1[x] == 0xE8]
        s['C2730A'] = [call_to(x) for x in k if d1[call_to(x):call_to(x) + 2] == b'\xc7\x05'
                       and d1[call_to(x) + 2:call_to(x) + 6] == A(a0) and d1[call_to(x) + 6:call_to(x) + 10] == A(diy)][0]
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
    # selTeamsPtr: mov eax, [esi+2B3h]; mov [A1], eax; mov eax, [selTeamsPtr]; add [A1], eax (table screen)
    s['selteams'] = [x.start() for x in re.finditer(rb'\x8b\x86\xb3\x02\x00\x00\xa3' + re.escape(A(a0 + 4)) + rb'\xa1.{4}\x01\x05'
                                                   + re.escape(A(a0 + 4)), d1, re.S)][0] + 12
    # table screen (DIYLeagueTournament16BeforeDraw): cmp word [esi+4Fh], 1; jz; mov [A0], offset cseg_49E7A
    s['hdr'] = one(rb'\x66\x83\x7e\x4f\x01\x74.\xc7\x05' + re.escape(A(a0)), 'group names') + 7
    # row loop: mov ax, [D2]; mov esi, [A5]; mov [esi+16h], ax; mov ax, [D5]; mov esi, [A5]; mov [esi+26h], ax
    s['num'] = one(rb'\x66\xa1' + re.escape(A(a0 - 24)) + rb'\x8b\x35' + re.escape(A(a0 + 20)) + rb'\x66\x89\x46\x16\x66\xa1'
                   + re.escape(A(a0 - 12)) + rb'\x8b\x35' + re.escape(A(a0 + 20)) + rb'\x66\x89\x46\x26', 'row number') + 16
    # mov [D3], 7; test [D5], 1; jz +9; mov [D3], 9; then cseg_49B65: mov ax, [dseg_11F41C]
    s['col'] = one(rb'\x66\xc7\x05' + re.escape(A(a0 - 20)) + rb'\x07\x00\x66\xf7\x05' + re.escape(A(a0 - 12))
                   + rb'\x01\x00\x74\x09\x66\xc7\x05' + re.escape(A(a0 - 20)) + rb'\x09\x00\x66\xa1', 'row colour') + 29
    return s


HEADERS = {'it': 'CLASSIFICA', 'en': 'STANDINGS', 'fr': 'CLASSEMENT', 'de': 'TABELLE'}
# STAT > INFO SU COMPETIZIONE (DesignDIYTournamentOnDraw): the league phase's stage line (the exe's own '1 GROUP OF %1'
# with 36) and its qualifiers (<= 40 columns)
INFO_Q = {'it': '(1-8 AGLI OTTAVI, 9-24 AGLI SPAREGGI)', 'en': '(TOP 8 TO THE LAST 16, 9-24 PLAY-OFFS)',
          'fr': '(8 PREMIERS EN 8ES, 9-24 EN BARRAGES)', 'de': '(TOP 8 ACHTELFINALE, 9-24 PLAYOFFS)'}
# ... and its 'plays each team x 1' column (the row's string table, <= 19 columns): 8 opponents, once each
INFO_X = {'it': '8 AVVERSARIE X 1', 'en': '8 OPPONENTS, ONCE', 'fr': '8 ADVERSAIRES X 1', 'de': '8 GEGNER, EINMAL'}


def _info_sites(p, a0):
    """DesignDIYTournamentOnDraw: `mov [A0], offset '%0 GROUPS OF %1'` before `mov esi, [A2]; mov ax, [esi+169h]`,
    the 1-group string set just after it, and `mov [A0], offset '(TOP %0 IN EACH GROUP QUALIFY)'` before `mov ax, [D1];
    or ax, ax; jz`."""
    d1 = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    s1 = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'.{4}\x8b\x35' + pk(a0 + 8) + rb'\x66\x8b\x86\x69\x01'
                                         rb'\x00\x00', d1, re.S)]
    s2 = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'.{4}\x66\xa1' + pk(a0 - 28) + rb'\x66\x0b\xc0\x74', d1,
                                         re.S)]
    assert len(s1) == 1 and len(s2) == 1, (s1, s2)
    one = [s1[0] + x.start() for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'.{4}', d1[s1[0] + 10:s1[0] + 0x60], re.S)]
    assert len(one) == 1, one
    # the group rows' 'plays each team x 1..4' string table: after the six 'points for a win' tables (initial 2)
    x1 = [m.end() - 4 for m in re.finditer(rb'(?:.{4}\x02\x00(.{8})){6}.{4}\x01\x00(.{4})', d1, re.S)
          if len({d1[m.start() + 6 + 14 * k:m.start() + 14 + 14 * k] for k in range(6)}) == 1]
    assert len(x1) == 1, x1
    # a group row's `mov esi, [A2]; mov ax, [esi+165h]; mov esi, [A0]; mov [esi], ax` (its 'plays each team x n')
    s3 = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(a0 + 8) + rb'\x66\x8b\x86\x65\x01\x00\x00\x8b\x35' + pk(a0) +
                                         rb'\x66\x89\x06', d1, re.S)]
    assert len(s3) == 1, s3
    return s1[0], s2[0], one[0] + 10, s3[0] + 6, x1[0]


def _game_sites(p, a0):
    """(InitializeInGameTeamsAndStartGame's `mov eax, [A1]; mov [gameTeam1], eax`, (team1StatsData, team2StatsData,
    gameTeam1)): the stats from InitGameRestoreTeams' resets (mov [A0], offset tNStatsData; mov esi, [A0]; three
    word fields cleared)."""
    d1 = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xa1' + pk(a0 + 4) + rb'\xa3(.{4})\xa1' + pk(a0 + 8) + rb'\xa3.{4}\xa1' + pk(a0 + 4)
                                + rb'\xa3' + pk(a0), d1, re.S)]
    assert len(m) == 1, len(m)
    game = m[0].start()
    st = [x.start(1) for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'(.{4})\x8b\x35' + pk(a0)
                                          + rb'\x66\xc7\x06\x00\x00\x66\xc7\x46\x02\x00\x00', d1, re.S)]
    assert len(st) == 2, len(st)
    return game, (p.target(1, st[0]), p.target(1, st[1]), p.target(1, game + 6))


def patch(p, cave, cups, area, lang='it', world_ids=()):
    """cups = [(contest id, countries in contest order)]: at most one tourney pack (CLASSIC TOURNEYS test); world_ids =
    the game's cups (0 Champions Cup, 1 Cup Winners' Cup) some career world plays as a league phase.
    Returns (end, lp_copy_ours, lp_draw): historic.hist_draw calls lp_draw when lp_copy_ours gives ZF = 1."""
    import nasmcave
    assert len(cups) <= 1 and (cups or world_ids or FIXTURES), (cups, world_ids)
    lp_id, countries = cups[0] if cups else (0xFF, [f'c{i}' for i in range(N)])
    assert len(countries) == N, len(countries)
    cal = draw(countries)                       # the fallback draw (the game draws at every stage start)
    check(cal, countries)
    s = _sites(p)
    a0 = s['A0']
    db = lambda b: 'db ' + ', '.join(str(x) for x in b)
    symbols = {'DIYCOPY': (2, s['DIYCOPY']), 'DIY': (2, s['DIY']), 'A0': (2, a0), 'A1': (2, a0 + 4), 'A2': (2, a0 + 8),
               'A3': (2, a0 + 12), 'A4': (2, a0 + 16), 'D1': (2, s['D1']), 'D2': (2, s['D2']),
               'LP_ID': (0, lp_id), 'AWAY_GF': (0, AWAY_GF), 'DISC': (0, DISC), 'CAL_OFF': (0, CAL_OFF), 'LP_TID': (0, int(bool(cups))),
               'LP_W0': (0, int(0 in world_ids)), 'LP_W1': (0, int(1 in world_ids)),
               'C260A9': (1, s['C260A9']), 'C2653B': (1, s['C2653B']), 'C8A2CE': (1, s['C8A2CE']),
               'C2730A': (1, s['C2730A']),
               'C89758_NEXT': (1, s['pair'] + 10), 'C883DD_NEXT': (1, s['sort'] + 10),
               'PO_BYTES': (0, db(playoff_slots())),
               'PAIRS6_BYTES': (0, db(b for P in range(6) for Q in range(P, 6) for b in (P, Q))),
               'LP_W2': (0, int(2 in world_ids)),
               'R16_BYTES': (0, db(R16_SEEDS)),
               'YCUM_BYTES': (0, db(poisson_cum(YELLOW_RATE, 7) + [255])),
               'RCUM_BYTES': (0, db(poisson_cum(RED_RATE, 2) + [255]))}
    for k, t in enumerate(('1-18', '19-36')):
        symbols[f'LP_S{k + 1}'] = (2, area.add(f'{HEADERS[lang]} {t}'.encode() + b'\0'))
    symbols.update(C49E7A=p.target(1, s['hdr'] + 6), C11F41C=p.target(1, s['col'] + 2),
                   D3=(2, a0 - 20), D5=(2, a0 - 12), D7=(2, a0 - 4), A5=(2, a0 + 20))
    import historic
    _, draw_orig = historic._draw_call(p)
    symbols['RAND2'] = (1, historic._coin_sites(p, draw_orig)['rand2'])
    symbols['SELTEAMS'] = p.target(1, s['selteams'])
    symbols['D0'] = (2, a0 - 32)
    c27227 = s['C2653B'] + 5 + struct.unpack_from('<i', p.le.obj_bytes(1), s['C2653B'] + 1)[0]
    d1 = p.le.obj_bytes(1)
    vcall = [x for x in range(c27227, c27227 + 0x200) if d1[x] == 0xE8][0]   # its first call: VerifyTeamLoaded
    symbols['VERIFY'] = (1, vcall + 5 + struct.unpack_from('<i', d1, vcall + 1)[0])
    symbols['LP_CAL'] = (2, area.add(bytes(b for m in cal for b in m)))      # fallback draws (by position)
    cal6 = draw6([f'c{i}' for i in range(N)])
    check6(cal6, [f'c{i}' for i in range(N)])
    symbols['LP_CAL6'] = (2, area.add(bytes(b for m in cal6 for b in m)))
    codes = sorted(set(countries))
    symbols['LP_CTRYS'] = (2, area.add(bytes(codes.index(c) for c in countries)))
    w = area.add(bytes(WORK_DRAW + 4))
    w = (w + 3) & ~3
    for name, off in W_LAYOUT.items():
        symbols[name] = (2, w + off)
    work = area.add(bytes(WORK + 4))
    work = (work + 3) & ~3
    symbols.update(LP_KEY=(2, work), LP_OPP=(2, work + 576), LP_ORD=(2, work + 576 + 432))
    game, st = _game_sites(p, a0)                       # criterion 9: the engine's played match and its statistics
    symbols.update(GAMET1=st[2], T1STATS=st[0], T2STATS=st[1])
    i1, i2, i_one, i3, x1 = _info_sites(p, a0)          # STAT > INFO SU COMPETIZIONE of a league phase
    symbols.update(INFO_GROUPS=p.target(1, i1 + 6), INFO_TOP=p.target(1, i2 + 6), AENT=(2, a0 + 16), INFO_X1=p.target(1, x1))
    o, off = p.target(1, i_one + 6)
    one = p.le.obj_bytes(o)[off:p.le.obj_bytes(o).index(b'\0', off)]
    assert b'%1' in one, one
    q = INFO_Q[lang].encode()
    assert len(q) <= 40, q
    symbols.update(LP_INFO1=(2, area.add(one.replace(b'%1', b'36').rstrip(b'* ') + b'\0')), LP_INFO2=(2, area.add(q + b'\0')),
                   LP_INFO3=(2, area.add(INFO_X[lang].encode() + b'\0')))
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
    p.remove(1, s['hdr'] + 2)                                    # mov [A0], offset (10 B) -> call; nops
    p.remove(1, s['hdr'] + 6)
    p.put(1, s['hdr'], b'\xe8' + rel(s['hdr'], lab['lp_hdr']) + b'\x90' * 5)
    for site, name in ((s['num'], 'lp_num'), (s['col'], 'lp_col')):  # mov ax, [mem] (6 B) -> call; nop
        p.remove(1, site + 2)
        p.put(1, site, b'\xe8' + rel(site, lab[name]) + b'\x90')
    p.remove(1, s['res'] + 2)                                    # mov ax, [D1]; mov esi, [A3] (12 B) -> call; nops
    p.remove(1, s['res'] + 8)
    p.put(1, s['res'], b'\xe8' + rel(s['res'], lab['lp_res']) + b'\x90' * 7)
    for site, name in ((i1, 'lp_info1'), (i2, 'lp_info2')):     # mov [A0], offset (10 B) -> call; nops
        p.remove(1, site + 2)
        p.remove(1, site + 6)
        p.put(1, site, b'\xe8' + rel(site, lab[name]) + b'\x90' * 5)
    p.put(1, i3, b'\xe8' + rel(i3, lab['lp_info3']) + b'\x90' * 2)      # mov ax, [esi+165h] (7 B) -> call; nops
    p.remove(1, game + 1)                                        # mov eax, [A1]; mov [gameTeam1], eax (10 B) -> call
    p.remove(1, game + 6)
    p.put(1, game, b'\xe8' + rel(game, lab['lp_game']) + b'\x90' * 5)
    days = [cal[18 * d:18 * d + 18] for d in range(DAYS)]
    print(f'exe: league phase {lp_id:#x}: code obj1+{cave:#x}..{cave + len(code):#x}, sites ' +
          ', '.join(f'{k} {v:#x}' for k, v in s.items() if k in ('days', 'start', 'pair', 'sort', 'res')) +
          f"; day 1 {days[0][:3]}...; labels " + ' '.join(f'{k} {v:#x}' for k, v in lab.items() if k.startswith('lp_')))
    LABELS.update(lab)
    LABELS['LP_ORD'] = symbols['LP_ORD']
    LABELS['symbols'] = {k: symbols[k] for k in ('DIY', 'DIYCOPY', 'A0', 'A1', 'A2', 'C2730A')}
    return cave + len(code), lab['lp_copy_ours'], lab['lp_draw']


def fx_patch(p, at, area):
    """The fixture contests (FIXTURES) on a page of their own (statecup's): fx_copy / fx_start / fx_pair + FX_TAB, and
    lp36's three vectors pointed at them. After lp36.patch. Returns the end."""
    import nasmcave
    if not FIXTURES:
        return at
    symbols = dict(LABELS['symbols'], LP_FRESH=(1, LABELS['lp_fresh']))
    rows = []
    symbols['DC_CLUB'] = (0, DC_CLUB)
    for k, ((cid, first), (ng, size, nd, cal_)) in enumerate(sorted(FIXTURES.items())):
        assert len(cal_) % ng == 0 and len(cal_) % nd == 0 and all(max(m) < ng * size for m in cal_), cid
        symbols[f'FXC{k}'] = (2, area.add(bytes(b for m in cal_ for b in m)))
        rows.append(f'    db {cid}, {ng}, {size}, 0\n    dd {len(cal_)}, {nd}, FXC{k}\n    dw {first[0] | first[1] << 8}, 0')
    asm = FX_ASM + 'align 4\nFX_TAB:\n' + '\n'.join(rows) + '\nFX_END:\n'
    code, fix = nasmcave.assemble(asm, at, symbols)
    lab = nasmcave.labels(asm, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    for vec, fn in (('FX_COPY_V', 'fx_copy'), ('FX_START_V', 'fx_start'), ('FX_PAIR_V', 'fx_pair')):
        p.retarget(1, LABELS[vec], 1, lab[fn])
        p.put(1, LABELS[vec], struct.pack('<I', lab[fn]))
    LABELS['FX_ROWS'] = {k: lab['FX_TAB'] + 20 * i + 16 for i, k in enumerate(sorted(FIXTURES))}   # (statespec's
                                                                    # overrides: a state's first club changes)
    print(f'exe: fixture contests {[(hex(c), f) for c, f in sorted(FIXTURES)]}: obj1+{at:#x}..{at + len(code):#x}')
    return (at + len(code) + 3) & ~3
