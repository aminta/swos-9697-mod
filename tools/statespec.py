"""State championships of a career world (pack.json competitions of type 'state'): the spec compiler for statecup.py.

A state championship is a type-2 contest (the Champions Cup layout: groups, then knockout stages) played in career
slot 1 by the clubs of its state (statecup's picker). pack.json, in the country's pack (one per country: every club of
the country is a key of it, the state-only clubs in a shared-base file):

  {"key": "pr", "type": "state", "id": "C4", "names": {"*": ["CAMPEONATO PARANAENSE", "PARANAENSE"]},
   "win_points": 3, "months": [1, 4],
   "clubs": [club keys in group order: group A first],
   "stages": [{"type": "groups", "teams": 12, "groups": 2, "meetings": 1, "cross": 2},
              {"type": "knockout", "teams": 8, "matches": "two_legs", "from": ["4A", "1A", "3A", "2A", ...]},
              {"type": "knockout", "teams": 4, "matches": "two_legs"},
              {"type": "knockout", "teams": 2, "matches": "two_legs"}]}

- the stage syntax is the tourney packs' (packs/TOURNEYS.md): 'groups' (teams, groups), 'knockout' (teams, matches,
  'from' after a group stage: 1A = winner of group A; tie k = the k-th pair, the first listed at home in a single
  match, at home in the FIRST leg of two), the last stage the final; fixed brackets (tie k = winners of 2k-1, 2k);
- 'meetings' (a group stage): 1 or 2 matches per pair (one value for every group stage of a contest: the header's);
- 'cross': k on the first group stage = the clubs are k blocks of equal size in list order and play only the clubs of
  the OTHER blocks, once (a fixed calendar: lp36.FIXTURES); groups = cross: each block is a group (its own table:
  Paranaense, Catarinense), groups = 1: one table for all (Goiano, Paraense);
- 'fixtures' (the first stage, groups 1, no cross): a drawn league phase (Paulista 2026: 8 matches each) = days of
  [home, away] club indices (the clubs list), every club once a day (lp36.FIXTURES, one table);
- 'byes' (a knockout after a group stage, with 'from'): labels that skip this round (Pernambucano / Mato-Grossense:
  "from": ["6A", "3A", "5A", "4A"], "byes": ["1A", "2A"]); the next stage's 'pairs' lists its ties by W<k> (the
  winner of tie k) and B<k> (bye k): "pairs": ["W2", "B1", "W1", "B2"];
- 'months': first and last month of the contest (1 = January).
The contest's champion = its final's winner (the game's national-cup trophy line).

Careers: the knockout draws ('from', 'byes', 'pairs', the fixed brackets after them) are st_ko's (ko_patch) at each
knockout stage's start (ST_TAB, keyed by contest id + first club; historic.hist_draw is tourney mode only):
- the copy's +59h at that point = the clubs best first, in bands of g groups (the 1sts, the 2nds ...; merit order
  inside a band): a label kX = the club of band k whose team index lies in group X's block (groups = blocks of the
  team list: only the FIRST group stage; a later group stage's 'from' / a draw after it stay the game's);
- byes: the round's (N - b) / 2 ties, the b last clubs wait; the round's list is kept with the career (EN item 'SB')
  and st_kend reads each tie's winner at the stage's end (DIY+89h result bits, as 0x1AAF9) for the next stage;
- st_ko also freezes the first stage's final order (st_rec -> ST_RANK, EN item 'SR', ripool's pools).
"""
import random
import re
import struct

from mkseason import MATCHES, _need


def cross_calendar(n, blocks, seed=2026):
    """n clubs in `blocks` equal blocks (list order): every pair of different blocks once, in rounds where every club
    plays (n even); home sides balanced (each club home ceil / floor of half its matches). [(home, away)] by day."""
    size = n // blocks
    blk = [i // size for i in range(n)]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if blk[i] != blk[j]]
    per = n // 2
    rng = random.Random(seed + n * 31 + blocks)
    days_n = len(pairs) // per
    for attempt in range(2000):                 # perfect matchings, greedy with backtracking over shuffled edges
        left = set(pairs)
        days = []
        ok = True
        for d in range(days_n):
            m = _matching(rng, n, left)
            if m is None:
                ok = False
                break
            days.append(m)
            left -= set(m)
        if ok and not left:
            break
    else:
        raise ValueError(f'cross calendar {n} / {blocks}: no rounds found')
    out = [list(m) for day in days for m in day]
    for k, m in enumerate(out):                 # alternate, then flip until every club hosts half (+- 1/2)
        if k % 2:
            m.reverse()
    games = [sum(1 for m in out if v in m) for v in range(n)]
    for _ in range(10000):
        home = [sum(1 for m in out if m[0] == v) for v in range(n)]
        bad = [v for v in range(n) if abs(2 * home[v] - games[v]) > 1]
        if not bad:
            break
        v = bad[0]
        hi = 2 * home[v] > games[v]
        cand = [m for m in out if (m[0] if hi else m[1]) == v]
        rng.shuffle(cand)
        o = lambda m: m[1] if hi else m[0]
        m = min(cand, key=lambda m: (2 * home[o(m)] - games[o(m)]) * (1 if hi else -1))
        m.reverse()
    return [tuple(m) for m in out], days_n


def _matching(rng, n, edges):
    """A perfect matching of n vertices from `edges` (DFS on the lowest free vertex), or None."""
    adj = {v: [] for v in range(n)}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    for v in adj:
        rng.shuffle(adj[v])
    used, out = set(), []

    def go():
        free = next((v for v in range(n) if v not in used), None)
        if free is None:
            return True
        used.add(free)
        for w in adj[free]:
            if w not in used:
                used.add(w)
                out.append((min(free, w), max(free, w)))
                if go():
                    return True
                out.pop()
                used.discard(w)
        used.discard(free)
        return False
    return out if go() else None


def compile_state(c, n_clubs):
    """pack.json 'state' comp -> {'stages': [(groups, per group, qualifiers)], 'stage_bytes', 'meetings', 'points',
    'months': (b3, b4), 'draws': [(perm, sort)], 'fixture': (groups, per group, days, calendar) or None}."""
    w = f"{c['key']}:"
    st = c.get('stages') or []
    _need(2 <= len(st) <= 5, f'{w} 2 to 5 stages (the last one the final)')
    _need(isinstance(c.get('win_points'), int) and 1 <= c['win_points'] <= 9, f'{w} win_points 1..9')
    m1, m2 = c.get('months', [1, 6])
    _need(1 <= m1 <= m2 <= 12, f'{w} months [first, last], 1..12')
    trip, sb, draws, meet, fixture, prev, byes, ko = [], [], [], None, None, None, [], []
    for i, x in enumerate(st):
        t, n = x.get('type'), x.get('teams')
        sw = f'{w} stage {i + 1}:'
        _need(t in ('groups', 'knockout'), f'{sw} type groups or knockout')
        _need(isinstance(n, int) and n >= 2, f'{sw} teams')
        if i == 0:
            _need(n == n_clubs, f'{sw} {n} teams, {n_clubs} clubs')
        elif prev['type'] == 'groups':
            _need(n < prev['teams'], f'{sw} fewer teams than the group stage before')
        elif prev.get('byes'):
            _need(n == prev['teams'] // 2 + len(prev['byes']), f'{sw} {n} teams: the winners + the byes before')
        else:
            _need(n * 2 == prev['teams'], f'{sw} {n} teams: half of the knockout before')
        if t == 'groups':
            g = x.get('groups')
            _need(isinstance(g, int) and g >= 1 and n % g == 0 and 2 <= n // g <= 24, f'{sw} groups: 2..24 per group')
            mt = x.get('meetings', 1)
            _need(meet in (None, mt) and mt in (1, 2, 3, 4), f'{sw} meetings 1..4, the same for every group stage')
            meet = mt
            cr = x.get('cross')
            if cr:
                _need(i == 0 and n % cr == 0 and n % 2 == 0 and g in (1, cr) and mt == 1,
                      f'{sw} cross k: the first stage, k equal blocks, groups 1 or k, one meeting, even teams')
                cal, days = cross_calendar(n, cr)
                fixture = (g, n // g, days, cal)
            fx = x.get('fixtures')
            if fx:
                _need(i == 0 and not cr and g == 1 and mt == 1 and n % 2 == 0,
                      f'{sw} fixtures: the first stage, one group, one meeting, even teams, no cross')
                seen = set()
                for d, day in enumerate(fx):
                    clubs = [v for pr in day for v in pr]
                    _need(sorted(clubs) == list(range(n)), f'{sw} fixtures day {d + 1}: every club once')
                    for a, b in day:
                        _need((min(a, b), max(a, b)) not in seen, f'{sw} fixtures: {a} v {b} twice')
                        seen.add((min(a, b), max(a, b)))
                fixture = (1, n, len(fx), [(a, b) for day in fx for a, b in day])
            nxt = st[i + 1]['teams'] + len(st[i + 1].get('byes') or []) if i + 1 < len(st) else 1
            trip.append((g, n // g, nxt))
            sb.append(0)
        else:
            _need(n & (n - 1) == 0, f'{sw} a knockout stage needs 2, 4, 8 or 16 teams')
            _need(x.get('matches') in MATCHES, f"{sw} matches: one of {', '.join(MATCHES)}")
            b = x.get('byes') or []
            _need(not b or (i > 0 and prev['type'] == 'groups' and x.get('from')),
                  f'{sw} byes: on the knockout after a group stage, with from')
            trip.append((0, n + len(b), n // 2 + len(b)))    # (the round has n + b clubs: the b wait, lib97 nc_adv)
            if b:
                byes.append((n + len(b), len(b)))
            sb.append(MATCHES[x['matches']])
        frm = x.get('from')
        if frm is not None:
            _need(i > 0 and prev['type'] == 'groups', f'{sw} from: only on the stage after a group stage')
            g = prev['groups']
            _need(n % g == 0, f'{sw} from needs the same number of qualifiers from every group')
            b = x.get('byes') or []
            q = n + len(b)
            labels = [f'{r}{chr(65 + k)}' for r in range(1, q // g + 1) for k in range(g)]
            _need(sorted(frm + b) == sorted(labels), f"{sw} from + byes must list {' '.join(labels)} once each")
            draws.append((q, [labels.index(x_) for x_ in frm + b], False))   # (the byes at the end: they wait)
            if x['type'] != 'knockout':                  # (careers: a later group stage's draw is the game's:
                pass                                     # historic.hist_draw is tourney mode only)
            elif i == 1 or g == 1:                       # (careers: groups = team-list blocks: the first stage's)
                ko.append((q, len(b), g, prev['teams'] // g, draws[-1][1]))
            else:
                _need(not b, f'{sw} byes after a second group stage of several groups: not in careers yet')   # (codes = band * g + group: the groups are
                                                                              # team-list blocks, a band is in merit order)
        elif x.get('pairs'):                             # after a stage with byes: W<k> the winner of tie k, B<k> bye k
            _need(prev.get('byes'), f'{sw} pairs: only after a stage with byes')
            k, bb = prev['teams'] // 2, len(prev['byes'])
            toks = [f'W{j + 1}' for j in range(k)] + [f'B{j + 1}' for j in range(bb)]
            _need(sorted(x['pairs']) == sorted(toks), f"{sw} pairs must list {' '.join(toks)} once each")
            draws.append((n, [toks.index(t_) for t_ in x['pairs']], False))
            ko.append((n, k, 0, prev['teams'] + bb, draws[-1][1]))   # (g = 0: winners of the k ties, then byes)
        elif i == 0:
            draws.append((n, list(range(n)), False))     # the clubs into the groups in list order
        elif prev['type'] != 'groups' and n > 2:
            draws.append((n, list(range(n)), True))      # tie k = the winners of ties 2k-1, 2k (their contest order)
            if ko and ko[-1][0] == prev['teams']:        # (careers: after a stage of ST_TAB, by the ties it kept)
                ko.append((n, prev['teams'] // 2, 0, prev['teams'], list(range(n))))
        prev = dict(x, teams=n)
    _need(st[-1]['type'] == 'knockout' and st[-1]['teams'] == 2, f'{w} the last stage must be the final (2)')
    ns = [d[0] for d in draws]
    _need(len(set(ns)) == len(ns), f'{w} two stages with {ns} teams: a fixed order needs different team counts')
    return {'stages': trip, 'stage_bytes': sb, 'meetings': meet or 1, 'points': c['win_points'],
            'months': (8 * (m1 - 1), 8 * (m2 - 1)), 'draws': [(pm, srt) for _, pm, srt in draws], 'fixture': fixture,
            'byes': byes, 'ko_draws': ko}     # (careers: lib97.st_draw; tourney mode: historic.hist_draw)


# --- harness test (STATESPEC_TEST=1 builds only): world 0's Brazil (TEAM.046) gets a Paranaense-shaped test state ----
import os
TEST = os.environ.get('STATESPEC_TEST') == '1'
TEST_ID, TEST_FILE = 0xF1, 46           # (world 0: never with statecup's own STATECUP_TEST, the same id)
TEST_SPEC = {'key': 'test', 'type': 'state', 'id': 'F1', 'win_points': 3, 'months': [1, 6],
             'names': {'*': ['CAMPEONATO TESTE', 'TESTE']},
             'stages': [{'type': 'groups', 'teams': 12, 'groups': 2, 'meetings': 1, 'cross': 2},
                        {'type': 'knockout', 'teams': 8, 'matches': 'two_legs',
                         'from': ['4A', '1A', '3A', '2A', '4B', '1B', '3B', '2B']},
                        {'type': 'knockout', 'teams': 4, 'matches': 'two_legs'},
                        {'type': 'knockout', 'teams': 2, 'matches': 'two_legs'}]}


def register_test():
    if TEST2:
        import statecup
        if not any(e['world'] == 0 and e['cup1'] == TEST_ID for e in statecup.ENTRIES):
            statecup.register(0, TEST_ID, TEST_FILE, [{'id': TEST_ID, 'members': list(range(24)), 'struct': None,
                                                       'first': (TEST_FILE, 0)}])
            sp = compile_state(dict(TEST2_SPEC, clubs=list(range(8))), 8)
            TEST_DRAWS[:] = [(TEST_ID, pm, srt, (TEST_FILE, 0)) for pm, srt in sp['draws']]
            ST_DRAWS[:] = [(TEST_ID, 0, n, b, TEST_FILE, g, sz, pm) for n, b, g, sz, pm in sp['ko_draws']]
        return
    if not TEST:
        return
    import statecup
    import lp36
    assert not statecup.TEST, 'STATESPEC_TEST and STATECUP_TEST share the test id'
    if any(e['world'] == 0 and e['cup1'] == TEST_ID for e in statecup.ENTRIES):
        return
    sp = compile_state(dict(TEST_SPEC, clubs=list(range(12))), 12)
    statecup.register(0, TEST_ID, TEST_FILE, [{'id': TEST_ID, 'members': list(range(24)), 'struct': None,
                                               'first': (TEST_FILE, 0)}])
    g, size, days, cal = sp['fixture']
    lp36.FIXTURES[(TEST_ID, (TEST_FILE, 0))] = (g, size, days, cal)
    TEST_DRAWS[:] = [(TEST_ID, pm, srt, (TEST_FILE, 0)) for pm, srt in sp['draws']]
    ST_DRAWS[:] = [(TEST_ID, 0, n, b, TEST_FILE, g, sz, pm) for n, b, g, sz, pm in sp['ko_draws']]


TEST_DRAWS = []                         # historic.DRAWS entries of the test state (patch.py adds them)
ST_DRAWS = []                           # (id, world, N, b, first club word, perm): the test state's knockout
                                        # draws in careers (mkseason.state_draws adds the packs' own)


TEST2 = os.environ.get('STATESPEC_TEST') == '2'    # (byes: a Pernambucano shape)
TEST2_SPEC = {'key': 'test2', 'type': 'state', 'id': 'F1', 'win_points': 3, 'months': [1, 6],
              'names': {'*': ['CAMPEONATO TESTE', 'TESTE']},
              'stages': [{'type': 'groups', 'teams': 8, 'groups': 1, 'meetings': 1},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'from': ['6A', '3A', '5A', '4A'],
                          'byes': ['1A', '2A']},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'pairs': ['W2', 'B1', 'W1', 'B2']},
                         {'type': 'knockout', 'teams': 2, 'matches': 'two_legs'}]}


def test_contest(p, at):
    """The test state at obj1 at and Brazil's world-0 competitionsTable entry [league, -2, it, -1]. Returns the end."""
    import countries
    import sacups
    import statecup
    d2 = p.le.obj_bytes(2)
    cc = bytes(d2[sacups.unique(d2, sacups.EUROCUP_HDR):][:0x27])
    sp = compile_state(dict(TEST_SPEC, clubs=list(range(12))), 12)
    sup = sacups.NAME_SITES[1][1] if len(sacups.NAME_SITES) > 1 else None
    names = bytes(p.get(1, sup, 8)) if sup else bytes(8)
    n = 12
    if TEST2:                           # Pernambucano shape: 8 clubs; 3rd-6th QF, 1st-2nd wait; SF; final
        n = 8
        sp = compile_state(dict(TEST2_SPEC, clubs=list(range(8))), 8)
    body = statecup.contest_bytes(cc, TEST_ID, TEST_FILE, sp['months'], sp['meetings'], sp['points'], sp['stages'],
                                  sp['stage_bytes'], [(TEST_FILE, i) for i in range(n)], names)
    p.put(1, at, body)
    statecup.set_struct(0, TEST_ID, (1, at), first=(TEST_FILE, 0))
    comp = countries.COMP[0]
    tobj, t = p.target(2, comp + 4 * TEST_FILE)
    league = p.target(tobj, t)
    tab = (at + len(body) + 3) & ~3
    p.add_ptr(1, tab, *league)
    p.put(1, tab + 4, struct.pack('<i', -2))
    p.add_ptr(1, tab + 8, 1, at)
    p.put(1, tab + 12, struct.pack('<i', -1))
    p.retarget(2, comp + 4 * TEST_FILE, 1, tab)
    p.put(2, comp + 4 * TEST_FILE, struct.pack('<I', tab))
    print(f'exe: STATESPEC_TEST: test state {TEST_ID:#x} (12 Brazilian clubs, cross groups, knockout) obj1+{at:#x}')
    return tab + 16


# --- the played state's final group-stage ranking (EN item 'SR', read by ripool at the season end) ------------------
SR_SIZE = 13 * (4 + 16 * 2) + 2         # blocks: dw key (first club word), db n, db 0, n x dw team words; dw 0
LABELS = {}
KO_ASM = """
st_ko:                                  ; replaces `call 0x16711` (the round's ties from its clubs) at the end of a
    call C16711                         ; type-2 contest's knockout-stage start (cseg_2572F; DIY = NCW, its id still
    call st_rec                         ; (the state's final group-stage order, EN item 'SR')
%if ST_NB                               ; FFh: the copy's; the stage's clubs in the copy's +59h order): a state's
    pushad                              ; fixed draw (ST_TAB: id, first club word, N, b, g, size, code[N]).
    mov ebx, ST_TAB                     ; g > 0: the copy's list comes in bands of g (the 1sts, the 2nds ...: merit
    mov edx, ST_NB                      ; order inside a band); code = band * g + group: list[k] = the club of that
.st:                                    ; band whose team index / size = group (groups = team-list blocks of size);
    mov al, [DIYCOPY + 2Dh]             ; b > 0: the b last wait, the N - b first play (N - b) / 2 ties (the list
    cmp [ebx], al                       ; kept in SB). g = 0: the stage after it, b = its ties k: code < k = the
    jne .stn                            ; winner of that tie, else a bye (the game's list there: winners, losers,
    mov ax, [DIYCOPY + 99h]             ; byes). (States share one id: told apart by their first club.)
    cmp [ebx + 1], ax
    jne .stn
    movzx ecx, byte [ebx + 3]
    cmp [NCW + 31h], cx
    je .sth
.stn:
    movzx ecx, byte [ebx + 3]
    lea ebx, [ebx + ecx + 7]
    dec edx
    jnz .st
.sx:
    popad
%endif
    ret
%if ST_NB
.sth:
    cmp byte [ebx + 5], 0               ; g = 0: the stage after one with byes ('pairs')
    je .pairs
    xor edi, edi                        ; k
.sk:
    movzx eax, byte [ebx + 7 + edi]     ; code -> band (al), group (ah)
    div byte [ebx + 5]
    mov dh, ah
    mul byte [ebx + 5]                  ; band * g: the band's first position
    mov esi, eax
    movzx ebp, byte [ebx + 5]           ; g candidates
.sj:
    movzx eax, byte [DIYCOPY + 59h + esi]
    div byte [ebx + 6]                  ; team index / size = its group
    cmp al, dh
    je .sf
    inc esi
    dec ebp
    jnz .sj
    jmp .sx                             ; (not found: the game's order - never in a built table)
.sf:
    mov al, [DIYCOPY + 59h + esi]
    mov [ST_T + edi], al
    inc edi
    cmp edi, ecx
    jb .sk
    call .put
    movzx edx, byte [ebx + 4]
    test edx, edx
    jz .sx
    sub ecx, edx
    shr ecx, 1
    mov [NCW + 4Fh], cx
    mov [NCW + 51h], cx
    jmp .sx
.pairs:                                 ; [ebx + 4] = the stage before's ties k, [ebx + 6] its clubs N'; code c < k:
    xor edi, edi                        ; the winner of tie c, else
.pk:                                    ; bye c - k
    movzx eax, byte [ebx + 7 + edi]
    movzx edx, byte [ebx + 4]
    cmp eax, edx
    jae .pb
    mov al, [ST_SB + 16 + eax]          ; the winner of tie c (st_kend, at the stage before's end)
    jmp .pf
.pb:
    add eax, edx                        ; bye c - k at SB[2k + c - k]: the byes follow the 2k clubs of the ties
    mov al, [ST_SB + eax]
.pf:
    mov [ST_T + edi], al
    inc edi
    cmp edi, ecx
    jb .pk
    call .put
    jmp .sx
.put:                                   ; ST_T[0..ecx) -> the round's list, and kept with the career (EN item
    xor eax, eax                        ; 'SB'): the next stage finds its winners by their ties, the byes by their
.pu:                                    ; places
    mov dl, [ST_T + eax]
    mov [NCW + 2CDh + eax], dl
    mov [ST_SB + eax], dl
    inc eax
    cmp eax, ecx
    jb .pu
    ret
%endif

st_kend:                                ; replaces `call 0x7A613` (a stage's end, not a group stage: the round's
%if ST_NB                               ; winners first into the copy's +59h, unless [163h] = 1 and [57h] says
    pushad                              ; otherwise): a state contest with fixed draws -> SB[16 + k] = the winner of
    mov ebx, ST_TAB                     ; tie k, from the round's list and its result bits (DIY+89h + k, bit 0:
    mov edx, ST_NB                      ; the second club won; as 0x1AAF9 reads them)
.k:
    mov al, [DIYCOPY + 2Dh]
    cmp [ebx], al
    jne .n
    mov ax, [DIYCOPY + 99h]
    cmp [ebx + 1], ax
    je .w
.n:
    movzx ecx, byte [ebx + 3]
    lea ebx, [ebx + ecx + 7]
    dec edx
    jnz .k
    jmp .x
.w:
    movzx ecx, word [NCW + 4Fh]
    cmp ecx, 8
    ja .x
    xor ebx, ebx
.t:
    test ecx, ecx
    jz .x
    movzx eax, byte [NCW + 89h + ebx]
    and eax, 1
    lea eax, [eax + ebx * 2]
    mov al, [NCW + 2CDh + eax]          ; tie k's winner -> SB[16 + c], c = its tie in SB (the list may have
    xor edx, edx                        ; changed order since: second legs swap the clubs)
.c:
    cmp al, [ST_SB + edx * 2]
    je .f
    cmp al, [ST_SB + edx * 2 + 1]
    je .f
    inc edx
    cmp edx, 8
    jb .c
    jmp .nx
.f:
    mov [ST_SB + 16 + edx], al
.nx:
    inc ebx
    dec ecx
    jmp .t
.x:
    popad
%endif
    jmp C7A613


st_rec:                                 ; lib97.st_ko calls it at a knockout-stage start: after a state contest's
    pushad                              ; first stage (id and first club in ST_KEYS; [53h] = 1), the copy's +59h =
    cmp word [DIYCOPY + 53h], 1         ; its clubs in final order -> ST_RANK block 0 (ripool takes the bottom
    jne .x                              ; ones; statesim adds the other states' blocks). (At the group stage's end
    mov al, [DIYCOPY + 2Dh]             ; the list is not sorted yet.)
    mov dx, [DIYCOPY + 99h]
    mov esi, ST_KEYS
    mov ecx, NKEYS
.k:
    cmp [esi], al
    jne .n
    cmp [esi + 1], dx
    je .w
.n:
    add esi, 3
    loop .k
    jmp .x
.w:
    mov edi, ST_RANK
    mov [edi], dx
    movzx ecx, word [DIYCOPY + 31h]
    cmp ecx, 16
    jbe .c
    mov ecx, 16
.c:
    mov [edi + 2], cl
    mov byte [edi + 3], 0
    add edi, 4
    xor ebx, ebx
.r:
    movzx eax, byte [DIYCOPY + 59h + ebx]
    mov ax, [DIYCOPY + 99h + eax * 2]
    mov [edi], ax
    add edi, 2
    inc ebx
    cmp ebx, ecx
    jb .r
    mov word [edi], 0
.x:
    popad
    ret
ST_KEYS: KEY_BYTES
ST_RANK: times SR_SIZE db 0
ST_TAB: ST_BYTES
ST_T: times 64 db 0
ST_SB: times 32 db 0                    ; (EN item 'SB': st_ko's last fixed round [0..16), st_kend's winners [16..24))
"""


def _kend_sites(p):
    """The two calls of a stage's end for a contest stage that is not a group stage (0x7A613: the game's two
    callers next to cseg_8A2CE's, both after `mov ax, [esi+15Dh]; or ax, ax; jz`)."""
    import lp36
    d = p.le.obj_bytes(1)
    c8a2ce = lp36._sites(p)['C8A2CE']
    out, tgt = [], set()
    for g in lp36._sites(p)['gend']:
        j = d.find(b'\xe8', g + 5, g + 0x60)
        while j > 0:
            t = j + 5 + struct.unpack_from('<i', d, j + 1)[0]
            if t != c8a2ce and 0x70000 < t < 0x90000:
                out.append(j)
                tgt.add(t)
                break
            j = d.find(b'\xe8', j + 1, g + 0x60)
    assert len(out) == 2 and len(tgt) == 1, ([hex(x) for x in out], [hex(x) for x in tgt])
    return out, tgt.pop()


def _st_site(p):
    """The `call 0x16711` (a round's ties from its clubs) of cseg_2572F's knockout-stage start (obj1 0x15D64): after
    `mov al, [esi+175h]; mov esi, [x]; mov [esi+37h], al` and five pushes."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x8a\x86\x75\x01\x00\x00\x8b\x35.{4}\x88\x46\x37(?:\xff\x35.{4}){5}\xe8',
                                       d, re.S)]
    assert len(m) == 2 and m[1] - m[0] < 0x400, [hex(x) for x in m]   # (the group-stage start, then the knockout's)
    return m[1] + 6 + 6 + 3 + 30


def ko_patch(p, at):
    """The states' career knockout code at obj1:at (statecup's page): st_ko on cseg_2572F's knockout-stage start,
    st_kend on both calls of 0x7A613, st_rec + ST_RANK (EN items 'SB', 'SR'; ripool's RI_SR_PTR). Returns the end."""
    import engine
    import lib97
    import mkseason
    import nasmcave
    st = mkseason.state_draws()                             # [(id, world, N, b, first club word, g, size, codes)]
    keys = sorted({(i, f) for i, _, _, _, f, _, _, _ in st} |
                  {(int(c['id'], 16), f[0] | f[1] << 8) for pk in mkseason.packs() if pk.world is not None
                   for c in pk.comps if c['type'] == 'state' for f in [pk.state(c)['clubs'][0]]})
    if not keys:
        return at
    diycopy = lib97._sites(p)[3]
    stc = _st_site(p)
    c16711 = stc + 5 + struct.unpack('<i', p.get(1, stc + 1, 4))[0]
    kend, _ = _kend_sites(p)
    cur = {k + 5 + struct.unpack('<i', p.get(1, k + 1, 4))[0] for k in kend}   # (chained: whatever they reach now)
    assert len(cur) == 1, [hex(x) for x in cur]
    sym = {'DIYCOPY': (2, diycopy), 'NCW': (2, diycopy + 0x41F), 'C16711': (1, c16711), 'C7A613': (1, cur.pop()),
           'ST_NB': (0, len(st)), 'NKEYS': (0, len(keys)), 'SR_SIZE': (0, SR_SIZE),
           'ST_BYTES': (0, 'db ' + ', '.join(str(x) for i, _, n, b, f, g, sz, pm in st
                                             for x in (i, f & 255, f >> 8, n, b, g, sz, *pm)) if st else 'db 0'),
           'KEY_BYTES': (0, 'db ' + ', '.join(str(x) for i, w in keys for x in (i, w & 255, w >> 8)))}
    code, fix = nasmcave.assemble(KO_ASM, at, sym)
    lab = nasmcave.labels(KO_ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, stc + 1, struct.pack('<i', lab['st_ko'] - (stc + 5)))      # (relative calls: no fixups)
    for k in kend:
        p.put(1, k + 1, struct.pack('<i', lab['st_kend'] - (k + 5)))
    LABELS['ST_RANK'] = (1, lab['ST_RANK'])
    engine.ITEM_AT['SR'] = (1, lab['ST_RANK'])
    engine.ITEM_AT['SB'] = (1, lab['ST_SB'])
    try:
        import ripool
        if 'RI_SR_PTR' in getattr(ripool, 'LABELS', {}):
            p.add_ptr(*ripool.LABELS['RI_SR_PTR'], 1, lab['ST_RANK'])
    except ImportError:
        pass
    print(f'exe: state knockouts: st_ko obj1+{lab["st_ko"]:#x} at obj1+{stc:#x}, st_kend at '
          f'{", ".join(f"obj1+{k:#x}" for k in kend)}, {len(st)} fixed draws, ST_RANK obj1+{lab["ST_RANK"]:#x} '
          f'({len(keys)} states), obj1+{at:#x}..{at + len(code):#x}')
    return (at + len(code) + 3) & ~3
