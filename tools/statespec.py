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
- the copy's +59h at that point = the clubs best first (in bands of the 1sts, the 2nds ... or in one overall merit
  order: both seen; each group's own order is kept): a label kX = the k-th club of group X in that list, X = the
  block of the team list its index lies in (only the FIRST group stage; a later group stage's 'from' / a draw after
  it stay the game's);
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
        nko = len(ko)
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
            if x['type'] != 'knockout':                  # (careers: the group stage after the first, st_grp:
                if i == 1:                               # b = FEh; later ones stay the game's)
                    ko.append((q, 0xFE, g, prev['teams'] // g, draws[-1][1]))
            elif i == 1 or g == 1:                       # (careers: groups = team-list blocks: the first stage's;
                                                         # code = place * g + group)
                ko.append((q, len(b), g, prev['teams'] // g, draws[-1][1]))
            else:
                _need(not b, f'{sw} byes after a second group stage of several groups: not in careers yet')
        elif x.get('pairs'):                             # after a stage with byes: W<k> the winner of tie k, B<k> bye k
            _need(prev.get('byes'), f'{sw} pairs: only after a stage with byes')
            k, bb = prev['teams'] // 2, len(prev['byes'])
            toks = [f'W{j + 1}' for j in range(k)] + [f'B{j + 1}' for j in range(bb)]
            _need(sorted(x['pairs']) == sorted(toks), f"{sw} pairs must list {' '.join(toks)} once each")
            draws.append((n, [toks.index(t_) for t_ in x['pairs']], False))
            ko.append((n, k, 0, prev['teams'] + bb, draws[-1][1]))   # (g = 0: winners of the k ties, then byes)
        elif x.get('pairing') == 'merit':                # after a group stage: the qualifiers in merit order (the
            _need(i > 0 and prev['type'] == 'groups' and x['type'] == 'knockout',   # engine's), 1st v last, 2nd v
                  f'{sw} pairing merit: a knockout after a group stage')            # last but one ... (Mineiro)
            pm = [v for k_ in range(n // 2) for v in (k_, n - 1 - k_)]
            draws.append((n, pm, False))
            ko.append((n, 0, 255, 0, pm))                # (g = 255: positions in the copy's +59h)
        elif i == 0:
            draws.append((n, list(range(n)), False))     # the clubs into the groups in list order
        elif prev['type'] != 'groups' and n > 2:
            draws.append((n, list(range(n)), True))      # tie k = the winners of ties 2k-1, 2k (their contest order)
            if ko and ko[-1][0] == prev['teams']:        # (careers: after a stage of ST_TAB, by the ties it kept)
                ko.append((n, prev['teams'] // 2, 0, prev['teams'], list(range(n))))
        if x.get('host') is not None:                    # the better placed of stage 1 at home (a single match) or at
            _need(x['host'] == 'better' and t == 'knockout', f"{sw} host: 'better' on a knockout stage")   # home in
            if len(ko) == nko and n == 2 and ko and ko[-1][0] == prev['teams']:   # the second leg (careers: st_ko by
                ko.append((n, prev['teams'] // 2, 0, prev['teams'], [0, 1]))      # ST_RANK; the final: the SF's
            _need(len(ko) == nko + 1, f'{sw} host: needs a fixed draw here (from / pairs / merit / after one)')   # winners)
            q_, b_, g_, sz_, pm_ = ko[-1]
            ko[-1] = (q_, b_, g_, sz_ | 0x80 | (0x40 if x['matches'].startswith('two_legs') else 0), pm_)
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
            n2 = TEST2_SPEC['stages'][0]['teams']
            sp = compile_state(dict(TEST2_SPEC, clubs=list(range(n2))), n2)
            TEST_DRAWS[:] = [(TEST_ID, pm, srt, (TEST_FILE, 0)) for pm, srt in sp['draws']]
            ST_DRAWS[:] = [(TEST_ID, 0, n, b, TEST_FILE, g, sz, pm) for n, b, g, sz, pm in sp['ko_draws']]
            if sp['fixture']:
                import lp36
                lp36.FIXTURES[(TEST_ID, (TEST_FILE, 0))] = sp['fixture']
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


TEST2 = os.environ.get('STATESPEC_TEST') in ('2', '3', '4')   # (2: byes, Pernambucano; 3: Cearense; 4: Mineiro)
TEST2_SPEC = {'key': 'test2', 'type': 'state', 'id': 'F1', 'win_points': 3, 'months': [1, 6],
              'names': {'*': ['CAMPEONATO TESTE', 'TESTE']},
              'stages': [{'type': 'groups', 'teams': 8, 'groups': 1, 'meetings': 1},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'from': ['6A', '3A', '5A', '4A'],
                          'byes': ['1A', '2A']},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'pairs': ['W2', 'B1', 'W1', 'B2']},
                         {'type': 'knockout', 'teams': 2, 'matches': 'two_legs'}]}
TEST3_SPEC = {'key': 'test3', 'type': 'state', 'id': 'F1', 'win_points': 3, 'months': [1, 6],
              'names': {'*': ['CAMPEONATO TESTE', 'TESTE']},
              'stages': [{'type': 'groups', 'teams': 10, 'groups': 2, 'meetings': 1},
                         {'type': 'groups', 'teams': 6, 'groups': 2, 'from': ['1A', '2A', '3A', '1B', '2B', '3B']},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'from': ['2B', '1A', '2A', '1B']},
                         {'type': 'knockout', 'teams': 2, 'matches': 'two_legs'}]}
TEST4_SPEC = {'key': 'test4', 'type': 'state', 'id': 'F1', 'win_points': 3, 'months': [1, 6],
              'names': {'*': ['CAMPEONATO TESTE', 'TESTE']},
              'stages': [{'type': 'groups', 'teams': 12, 'groups': 3, 'meetings': 1, 'cross': 3},
                         {'type': 'knockout', 'teams': 4, 'matches': 'two_legs', 'pairing': 'merit'},
                         {'type': 'knockout', 'teams': 2, 'matches': 'single'}]}
if os.environ.get('STATESPEC_TEST') == '3':
    TEST2_SPEC = TEST3_SPEC
if os.environ.get('STATESPEC_TEST') == '4':
    TEST2_SPEC = TEST4_SPEC


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
        n = TEST2_SPEC['stages'][0]['teams']
        sp = compile_state(dict(TEST2_SPEC, clubs=list(range(n))), n)
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
    jmp st_body

st_grp:                                 ; replaces `call 0x16C47` (a group stage's draw, cseg_2572F: the groups =
    mov byte [ST_MODE], 1               ; consecutive blocks of the copy's +59h list): a state's later group stage
    inc byte [ST_GDBG]                  ; (debug: calls, DIY [31h], copy [53h])
    push eax
    mov ax, [NCW + 31h]
    mov [ST_GDBG + 2], ax
    mov ax, [DIYCOPY + 53h]
    mov [ST_GDBG + 4], ax
    pop eax
    call st_body                        ; with 'from' (b = FEh entries): +59h reordered first (Cearense phase 2)
    mov byte [ST_MODE], 0
    jmp C16C47

st_body:
%if ST_NB                               ; FFh: the copy's; the stage's clubs in the copy's +59h order): a state's
    pushad                              ; fixed draw (ST_TAB: id, first club word, N, b, g, size, code[N]).
    mov ebx, ST_TAB                     ; g > 0: code = place * g + group: list[k] = the place-th club of that group
    mov edx, ST_NB                      ; in the copy's merit-ordered list (team index / size = group: groups =
.st:                                    ; team-list blocks of size);
    mov al, [DIYCOPY + 2Dh]             ; b > 0: the b last wait, the N - b first play (N - b) / 2 ties (the list
    cmp [ebx], al                       ; kept in SB). g = 0: the stage after it, b = its ties k: code < k = the
    jne .stn                            ; winner of that tie, else a bye (the game's list there: winners, losers,
    mov ax, [DIYCOPY + 99h]             ; byes). (States share one id: told apart by their first club.)
    cmp [ebx + 1], ax
    jne .stn
    movzx ecx, byte [ebx + 3]
    cmp [NCW + 31h], cx
    jne .stn
    cmp byte [ebx + 4], 0FEh            ; (a group-stage entry only at st_grp, the others only at st_ko)
    sete al
    cmp al, [ST_MODE]
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
    mov al, [ebx + 6]                   ; (size: bit 7 = host by stage-1 place, bit 6 = two legs)
    and al, 3Fh
    mov [ST_SZ], al
    cmp byte [ebx + 5], 0               ; g = 0: the stage after one with byes ('pairs')
    je .pairs
    cmp byte [ebx + 5], 0FFh            ; g = 255: positions in the copy's merit-ordered list ('pairing' merit)
    je .pos
    mov edi, ST_SB                      ; (SB = FFh until this round's list is known: a stage after it finds no
    push ecx                            ; winners and keeps the game's order)
    mov ecx, 32
    mov al, 0FFh
    rep stosb
    pop ecx
    xor edi, edi                        ; k
.sk:
    movzx eax, byte [ebx + 7 + edi]     ; code -> place k (al), group (ah): the k-th club of that group in the
    div byte [ebx + 5]                  ; copy's list (merit order: banded, or the overall order - the groups' own
    mov dh, ah                          ; orders are kept either way)
    movzx ebp, al
    xor esi, esi
.sj:
    cmp si, [DIYCOPY + 31h]
    jae .sx                             ; (not found: the game's order - never in a built table)
    movzx eax, byte [DIYCOPY + 59h + esi]
    div byte [ST_SZ]                    ; team index / size = its group
    cmp al, dh
    jne .sn
    test ebp, ebp
    jz .sf
    dec ebp
.sn:
    inc esi
    jmp .sj
.sf:
    mov al, [DIYCOPY + 59h + esi]
    mov [ST_T + edi], al
    inc edi
    cmp edi, ecx
    jb .sk
    cmp byte [ebx + 4], 0FEh            ; a group stage: the copy's list itself (its blocks become the groups)
    jne .kp
    inc byte [ST_GDBG + 1]
    xor eax, eax
.gp:
    mov dl, [ST_T + eax]
    mov [DIYCOPY + 59h + eax], dl
    inc eax
    cmp eax, ecx
    jb .gp
    jmp .sx
.kp:
    call .put
    movzx edx, byte [ebx + 4]
    test edx, edx
    jz .sx
    sub ecx, edx
    shr ecx, 1
    mov [NCW + 4Fh], cx
    mov [NCW + 51h], cx
    jmp .sx
.pos:
    xor edi, edi
.po:
    movzx eax, byte [ebx + 7 + edi]
    mov al, [DIYCOPY + 59h + eax]
    mov [ST_T + edi], al
    inc edi
    cmp edi, ecx
    jb .po
    call .put
    jmp .sx
.pairs:                                 ; [ebx + 4] = the stage before's ties k, [ebx + 6] its clubs N'; code c < k:
    xor edi, edi                        ; the winner of tie c, else
.pk:                                    ; bye c - k
    movzx eax, byte [ebx + 7 + edi]
    movzx edx, byte [ebx + 4]
    cmp eax, edx
    jae .pb
    mov al, [ST_SB + 16 + eax]          ; the winner of tie c (st_kend, at the stage before's end)
    cmp al, 0FFh
    je .sx                              ; (none: the game's order)
    jmp .pf
.pb:
    add eax, edx                        ; bye c - k at SB[2k + c - k]: the byes follow the 2k clubs of the ties
    mov al, [ST_SB + eax]
    cmp al, 0FFh
    je .sx
.pf:
    mov [ST_T + edi], al
    inc edi
    cmp edi, ecx
    jb .pk
    call .put
    jmp .sx
.put:                                   ; ST_T[0..ecx) -> the round's list, and kept with the career (EN item
    call .host                          ; 'SB'): the next stage finds its winners by their ties, the byes by their
    xor eax, eax                        ; places
.pu:
    mov dl, [ST_T + eax]
    mov [NCW + 2CDh + eax], dl
    mov [ST_SB + eax], dl
    inc eax
    cmp eax, ecx
    jb .pu
    ret
.host:                                  ; 'host': 'better' (size bit 7): each tie of ST_T ordered by the clubs' places
    test byte [ebx + 6], 80h            ; in ST_RANK block 0 (stage 1's final order, st_rec): a single match the
    jz .hr                              ; better placed first (at home), two legs (bit 6) the worse placed first
    pushad                              ; (at home in the first leg)
    mov edx, ecx
    mov al, [ebx + 5]
    test al, al
    jz .hn
    cmp al, 0FFh
    je .hn
    movzx eax, byte [ebx + 4]           ; (g > 0: the b last wait)
    sub edx, eax
.hn:
    shr edx, 1
    xor esi, esi
.hl:
    cmp esi, edx
    jae .hx
    movzx eax, byte [ST_T + esi * 2]
    call .rank
    mov ebp, eax
    movzx eax, byte [ST_T + esi * 2 + 1]
    call .rank
    test byte [ebx + 6], 40h
    jnz .h2
    cmp eax, ebp                        ; single: swap when the second is better placed
    jae .hk
    jmp .hs
.h2:
    cmp eax, ebp                        ; two legs: swap when the second is worse placed
    jbe .hk
.hs:
    mov al, [ST_T + esi * 2]
    mov ah, [ST_T + esi * 2 + 1]
    mov [ST_T + esi * 2], ah
    mov [ST_T + esi * 2 + 1], al
.hk:
    inc esi
    jmp .hl
.hx:
    popad
.hr:
    ret
.rank:                                  ; eax = team index -> its place in ST_RANK block 0 (FFh: not there)
    push ecx
    push edx
    mov dx, [DIYCOPY + 99h + eax * 2]
    movzx ecx, byte [ST_RANK + 2]
    xor eax, eax
.rl:
    cmp eax, ecx
    jae .rn
    cmp [ST_RANK + 4 + eax * 2], dx
    je .rf
    inc eax
    jmp .rl
.rn:
    mov eax, 0FFh
.rf:
    pop edx
    pop ecx
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
    add esi, 5
    loop .k
    jmp .x
.w:
    mov edi, ST_RANK
    mov dx, [esi + 3]                   ; (the block's key: the contest's ORIGINAL first club, RI_OVR_KEYS')
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
st_noovr:                               ; (engine.after_load 'st_ovr' without ripool's overrides)
    ret

st_isstate:                             ; lp36.lp_sort: ZF = 1 when the running group stage (DIY = NCW) is a state's
    push eax                            ; (id + its team table's row 0 = a current key of ST_KEYS)
    push ecx
    push edx
    push esi
    mov al, [NCW + 2Dh]
    mov dx, [NCW + 12Dh]
    mov esi, ST_KEYS
    mov ecx, NKEYS
.k:
    cmp [esi], al
    jne .n
    cmp [esi + 1], dx
    je .r
.n:
    add esi, 5
    loop .k
    cmp esp, 0                          ; ZF = 0
.r:
    pop esi
    pop edx
    pop ecx
    pop eax
    ret

st_resort:                              ; after the game's sort (cseg_883DD): each group's rows (DIY+6Dh: row
    pushad                              ; offsets, [51h] per group) by points, wins, goal difference, goals (Brazil's
    movzx ebp, word [NCW + 4Fh]         ; order); level clubs keep the game's order
    xor edi, edi                        ; group
.g:
    cmp edi, ebp
    jae .x
    movzx ecx, word [NCW + 51h]
    mov eax, edi
    imul eax, ecx
    lea esi, [NCW + 6Dh + eax * 2]      ; the group's first entry
    mov ebx, 1                          ; insertion sort
.i:
    cmp ebx, ecx
    jae .ng
    movzx eax, word [esi + ebx * 2]     ; the row being placed
    mov edx, ebx
.j:
    test edx, edx
    jz .put
    push ecx
    movzx ecx, word [esi + edx * 2 - 2]
    call .before                        ; CF = 1: row eax ranks before row ecx
    pop ecx
    jnc .put
    push eax
    mov ax, [esi + edx * 2 - 2]
    mov [esi + edx * 2], ax
    pop eax
    dec edx
    jmp .j
.put:
    mov [esi + edx * 2], ax
    inc ebx
    jmp .i
.ng:
    inc edi
    jmp .g
.x:
    mov esi, NCW + 6Dh                  ; (the harness: this sort's order and the rows' points / wins / for /
    mov edi, ST_RDBG                    ; against, STRDBGPT)
    mov ecx, 24
    rep movsw
    xor ecx, ecx
.dr:
    imul eax, ecx, 18
    mov dx, [NCW + eax + 2C3h]
    mov [ST_RDBG + 48 + ecx * 8], dx
    mov dx, [NCW + eax + 2B9h]
    mov [ST_RDBG + 50 + ecx * 8], dx
    mov dx, [NCW + eax + 2BFh]
    mov [ST_RDBG + 52 + ecx * 8], dx
    mov dx, [NCW + eax + 2C1h]
    mov [ST_RDBG + 54 + ecx * 8], dx
    inc ecx
    cmp ecx, 24
    jb .dr
    popad
    ret
.before:                                ; rows at NCW + eax / NCW + ecx: CF = 1 if eax's is better
    push edx
    push ebx
    mov dx, [NCW + eax + 2C3h]          ; points
    cmp dx, [NCW + ecx + 2C3h]
    jne .d
    mov dx, [NCW + eax + 2B9h]          ; wins
    cmp dx, [NCW + ecx + 2B9h]
    jne .d
    mov dx, [NCW + eax + 2BFh]          ; goal difference
    sub dx, [NCW + eax + 2C1h]
    mov bx, [NCW + ecx + 2BFh]
    sub bx, [NCW + ecx + 2C1h]
    cmp dx, bx
    jne .ds
    mov dx, [NCW + eax + 2BFh]          ; goals
    cmp dx, [NCW + ecx + 2BFh]
    jne .d
    clc
    jmp .e
.ds:
    jg .y                               ; (signed)
    clc
    jmp .e
.d:
    ja .y                               ; (unsigned counts)
    clc
    jmp .e
.y:
    stc
.e:
    pop ebx
    pop edx
    ret
ST_KEYS: KEY_BYTES
ST_RANK: times SR_SIZE db 0
ST_TAB: ST_BYTES
ST_T: times 64 db 0
    db 'STRDBGPT'
    dd ST_RDBG
ST_RDBG: times 240 db 0
ST_MODE: db 0
ST_GDBG: times 8 db 0
ST_SZ: db 0
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


def _grp_site(p):
    """cseg_2572F's group-stage branch: the `call 0x16C47` (the groups' draw) after the copy of the team words
    (obj1 0x159A9): the call right after `add eax, 12Dh ... jns` + five pushes, before `call 0x16386`."""
    d = p.le.obj_bytes(1)
    s = _st_site(p)
    m = [x.start() for x in re.finditer(rb'\x79\xd7(?:\xff\x35.{4}){5}\xe8', d[s - 0x500:s], re.S)]
    assert len(m) == 2, [hex(s - 0x500 + x) for x in m]     # (the group branch's, then the knockout's 0x168C3)
    return s - 0x500 + m[0] + 2 + 30


def _st_site(p):
    """The `call 0x16711` (a round's ties from its clubs) of cseg_2572F's knockout-stage start (obj1 0x15D64): after
    `mov al, [esi+175h]; mov esi, [x]; mov [esi+37h], al` and five pushes."""
    d = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x8a\x86\x75\x01\x00\x00\x8b\x35.{4}\x88\x46\x37(?:\xff\x35.{4}){5}\xe8',
                                       d, re.S)]
    assert len(m) == 2 and m[1] - m[0] < 0x400, [hex(x) for x in m]   # (the group-stage start, then the knockout's)
    return m[1] + 6 + 6 + 3 + 30


def lp36_rows():
    """[((contest id, first club), obj1 offset of its FX_TAB row's first-club word)] (lp36.fx_patch)."""
    import lp36
    return list(lp36.LABELS.get('FX_ROWS', {}).items())


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
                   for c in pk.comps if c['type'] == 'state' for f in [pk.state(c)['clubs'][0]]} |
                  ({(TEST_ID, TEST_FILE)} if TEST or TEST2 else set()))
    if not keys:
        return at
    diycopy = lib97._sites(p)[3]
    stc = _st_site(p)
    c16711 = stc + 5 + struct.unpack('<i', p.get(1, stc + 1, 4))[0]
    kend, _ = _kend_sites(p)
    grp_site = _grp_site(p)
    c16c47 = grp_site + 5 + struct.unpack('<i', p.get(1, grp_site + 1, 4))[0]
    cur = {k + 5 + struct.unpack('<i', p.get(1, k + 1, 4))[0] for k in kend}   # (chained: whatever they reach now)
    assert len(cur) == 1, [hex(x) for x in cur]
    sym = {'DIYCOPY': (2, diycopy), 'NCW': (2, diycopy + 0x41F), 'C16711': (1, c16711), 'C16C47': (1, c16c47), 'C7A613': (1, cur.pop()),
           'ST_NB': (0, len(st)), 'NKEYS': (0, len(keys)), 'SR_SIZE': (0, SR_SIZE),
           'ST_BYTES': (0, 'db ' + ', '.join(str(x) for i, _, n, b, f, g, sz, pm in st
                                             for x in (i, f & 255, f >> 8, n, b, g, sz, *pm)) if st else 'db 0'),
           'KEY_BYTES': (0, 'db ' + ', '.join(str(x) for i, w in keys for x in (i, w & 255, w >> 8, w & 255, w >> 8)))}
    code, fix = nasmcave.assemble(KO_ASM, at, sym)
    lab = nasmcave.labels(KO_ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, stc + 1, struct.pack('<i', lab['st_ko'] - (stc + 5)))      # (relative calls: no fixups)
    for k in kend:
        p.put(1, k + 1, struct.pack('<i', lab['st_kend'] - (k + 5)))
    p.put(1, grp_site + 1, struct.pack('<i', lab['st_grp'] - (grp_site + 5)))
    import lp36
    if 'ST_SORT_V' in lp36.LABELS:                        # (lp36 patched: the group tables' tie-breaks)
        p.add_ptr(1, lp36.LABELS['ST_SORT_V'], 1, lab['st_isstate'])
        p.add_ptr(1, lp36.LABELS['ST_RESORT_V'], 1, lab['st_resort'])
    LABELS['ST_RANK'] = (1, lab['ST_RANK'])
    LABELS['key_slots'] = {}                              # first club word -> obj1 offsets of the words keyed by it
    k_at = lab['ST_KEYS']                                 # (ST_KEYS: id, current word, original word)
    for i, w in keys:
        LABELS['key_slots'].setdefault(w, []).append(k_at + 1)
        k_at += 5
    t_at = lab['ST_TAB']                                  # (ST_TAB: id, word, N, b, g, size, codes)
    for i, _, n_, b, f, g_, sz, pm in st:
        LABELS['key_slots'].setdefault(f, []).append(t_at + 1)
        t_at += 7 + len(pm)
    for (cid, first), off in lp36_rows():
        LABELS['key_slots'].setdefault(first[0] | first[1] << 8, []).append(off)
    engine.ITEM_AT['SR'] = (1, lab['ST_RANK'])
    engine.ITEM_AT['SB'] = (1, lab['ST_SB'])
    engine.CALL_AT.setdefault('st_ovr', (1, lab['st_noovr']))   # (ov_patch: the real one)
    try:
        import ripool
        if 'RI_SR_PTR' in getattr(ripool, 'LABELS', {}):
            p.add_ptr(*ripool.LABELS['RI_SR_PTR'], 1, lab['ST_RANK'])
    except ImportError:
        pass
    print(f'exe: state knockouts: st_ko obj1+{lab["st_ko"]:#x} at obj1+{stc:#x}, st_kend at '
          f'{", ".join(f"obj1+{k:#x}" for k in kend)}, {len(st)} fixed draws, ST_RANK obj1+{lab["ST_RANK"]:#x} '
          f'({len(keys)} states), obj1+{at:#x}..{at + len(code):#x}, ST_GDBG obj1+{lab["ST_GDBG"]:#x}')
    return (at + len(code) + 3) & ~3


# --- statesim.c's table: every state of the world, its stage 1 as a match list, its relegation phase -----------------
def _code(label, g, w):
    """'5A' -> code = (place - 1) * g + group."""
    _need(isinstance(label, str) and len(label) >= 2 and label[:-1].isdigit() and 'A' <= label[-1] < chr(65 + g),
          f'{w} relegation: label {label!r} (place + group letter, {g} groups)')
    return (int(label[:-1]) - 1) * g + ord(label[-1]) - 65


def relegation_bytes(c, g, pk=None):
    """pack.json 'relegation' (with 'relegated' = how many go down) -> statesim.c's program:
      absent / {"type": "bottom"}: the last `relegated` of the stage-1 order;
      {"type": "playoffs", "ties": [["5A", "6B"], ...], "legs": 2}: each tie's loser down;
      {"type": "group", "members": ["5A", "6A", "5B", "6B"], "meetings": 1 | 2, "bonus": {"best": ["5A", "5B"],
       "points": 1}, "extra": {"place": 3, "strength": s | "club": key}}: a round robin of those, its last
       `relegated` down (+ the extra place down if it loses a two-legged tie against an outside club of strength s, or
       that pack club's own);
      {"type": "gap", "places": [10, 11], "gap": 6}: place b plays place a over two legs if within gap points (else
       down), plus the last relegated - 1."""
    w = f"{c['key']}:"
    r = c.get('relegation') or {'type': 'bottom'}
    t = r.get('type')
    if t == 'bottom':
        return bytes([0])
    if t == 'playoffs':
        ties = r.get('ties') or []
        _need(ties and r.get('legs') in (1, 2), f'{w} relegation playoffs: ties + legs 1 / 2')
        return bytes([1, r['legs'], len(ties)] + [_code(x, g, w) for a, b in ties for x in (a, b)])
    if t == 'group':
        mem = [_code(x, g, w) for x in r.get('members') or []]
        _need(2 <= len(mem) <= 8 and r.get('meetings') in (1, 2), f'{w} relegation group: members + meetings')
        bo = r.get('bonus') or {}
        bc = [_code(x, g, w) for x in bo.get('best') or []]
        ex = r.get('extra') or {}
        xs = ex.get('strength', 0)
        if ex.get('club'):                               # (a real club of the pack, e.g. the A2 runner-up: its own
            _need(pk is not None and ex['club'] in pk.prows, f"{w} relegation extra club {ex['club']!r}")   # strength)
            xs = club_strength(pk, ex['club'])
        return bytes([2, r['meetings'], len(mem), *mem, len(bc), *bc, bo.get('points', 0), ex.get('place', 0),
                      min(255, xs // 4)])
    if t == 'gap':
        a, b = r.get('places') or (0, 0)
        _need(1 <= a < b, f'{w} relegation gap: places [a, b]')
        return bytes([3, a, b, r.get('gap', 0)])
    _need(False, f'{w} relegation type {t!r}: bottom, playoffs, group or gap')


def ko_program(c):
    """statesim.c's stages after the first: db stages; group: 1, g, size, meetings, cross, q, q x code (over the
    previous order); knockout: 2, N, b, legs, mode (0 codes over the previous order, 1 pairs: W<k> = k, bye j = ties
    + j, 2 the winners in tie order), N x code. A code = place * groups + group of the order before."""
    w = f"{c['key']}:"
    st = c['stages']
    out = bytearray([len(st) - 1])
    prev = dict(st[0], teams=st[0]['teams'])
    for i, x in enumerate(st[1:], 1):
        n = x['teams']
        if x['type'] == 'groups':
            g2 = x.get('groups', 1)
            gp = prev.get('groups', 1) if prev['type'] == 'groups' else 1
            frm = x.get('from')
            _need(frm and prev['type'] == 'groups', f'{w} statesim: a later group stage needs from')
            labels = [f'{r}{chr(65 + k)}' for r in range(1, -(-n // gp) + 1) for k in range(gp)]
            out += bytes([1, g2, n // g2, x.get('meetings', c.get('meetings', 1)) or 1, int(bool(x.get('cross'))), n]
                         + [labels.index(q) for q in frm])
        else:
            legs = 2 if x.get('matches', '').startswith('two_legs') else 1
            hb = 0x80 if x.get('host') == 'better' else 0      # (statesim: the better placed of stage 1 at home)
            b = x.get('byes') or []
            q = n + len(b)
            if prev['type'] == 'groups' and not x.get('from'):   # the first q of the merit order (MG: 3 winners +
                pm = list(range(q))                                # the best 2nd), 'pairing' merit: 1st v last ...
                if x.get('pairing') == 'merit':
                    pm = [v for k_ in range(q // 2) for v in (k_, q - 1 - k_)]
                out += bytes([2, q, len(b), legs, 3 | hb] + pm)
            elif prev['type'] == 'groups':
                gp = prev.get('groups', 1)
                labels = [f'{r}{chr(65 + k)}' for r in range(1, -(-q // gp) + 1) for k in range(gp)]
                frm = x['from'] + b
                out += bytes([2, q, len(b), legs, 0 | hb] + [labels.index(t) for t in frm])
            elif x.get('pairs'):
                k, bb = prev['teams'] // 2, len(prev.get('byes') or [])
                toks = [f'W{j + 1}' for j in range(k)] + [f'B{j + 1}' for j in range(bb)]
                out += bytes([2, n, 0, legs, 1 | hb] + [toks.index(t) for t in x['pairs']])
            else:
                out += bytes([2, n, 0, legs, 2 | hb] + list(range(n)))
        prev = dict(x, teams=n)
    return bytes(out)


def club_strength(pk, key):
    """The best 11 players' prices (players.csv), at least 5."""
    pr = sorted((int(r.get('price') or 0) for r in pk.prows.get(key, [])), reverse=True)
    return max(5, min(0xFFFF, sum(pr[:11])))


SIM_LAYOUT = []                         # (original key, offset of its words in SS_TAB, original words, (world, id, first))


def sim_table(world=None):
    """statesim.c's SS_TAB bytes for every state of the career world packs (world None = all)."""
    import mkseason
    out = bytearray()
    ns = 0
    SIM_LAYOUT.clear()
    for pk in mkseason.packs():
        if pk.world is None or (world is not None and pk.world != world):
            continue
        for c in pk.comps:
            if c['type'] != 'state':
                continue
            sp = pk.state(c)
            n = len(sp['clubs'])
            _need(n <= 16, f"{c['key']}: statesim takes up to 16 clubs")
            g0, size0, _ = sp['stages'][0]
            g = g0 if not c['stages'][0].get('cross') or g0 > 1 else 1
            size = size0 if g > 1 else n
            if sp['fixture']:
                pairs = list(sp['fixture'][3])
            else:
                pairs = []
                for r in range(sp['meetings']):
                    for x in range(g0):
                        mem = list(range(x * size0, (x + 1) * size0))
                        for i in range(len(mem)):
                            for j in range(i + 1, len(mem)):
                                pairs.append((mem[j], mem[i]) if r & 1 else (mem[i], mem[j]))
            f = sp['clubs'][0]
            words = [a | b << 8 for a, b in sp['clubs']]
            strs = [club_strength(pk, k) for k in c['clubs']]
            SIM_LAYOUT.append((f[0] | f[1] << 8, 1 + len(out) + 6, words, (pk.world, int(c['id'], 16), tuple(f))))
            out += struct.pack('<HBBBB', f[0] | f[1] << 8, n, g, size, c.get('relegated', 0))
            out += struct.pack(f'<{n}H', *words) + struct.pack(f'<{n}H', *strs)
            out += struct.pack('<H', len(pairs)) + bytes(x for p in pairs for x in p)
            out += relegation_bytes(c, g, pk)
            out += ko_program(c)
            ns += 1
    return bytes([ns]) + bytes(out) if ns else b''


SIM_PAGES = 2                           # statesim.c's pages (statecup's after its own): table, code, statics
SIM_BSS = 0x400                         # (statesim.c's statics: at the end of its pages, zero-filled)


def sim_patch(p, at):
    """statesim.c + its table on its own obj1 pages at `at` (after statecup's page); ss_season is called through
    ripool's RI_PRE_PTR (pg_fix, before ri_season reads ST_RANK). Returns the end, or at when there is nothing."""
    import cobj
    tab = sim_table()
    if not tab or 'ST_RANK' not in LABELS:
        return at
    p.put(1, at, tab)
    code_at = (at + len(tab) + 15) & ~15
    bss_at = at + 0x1000 * SIM_PAGES - SIM_BSS
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statesim.c'))
    m = [x.start() for x in re.finditer(rb'\x80\x2d(.{4})\x01\xe8', p.le.obj_bytes(1), re.S)]   # (InitCareer: `sub
    assert len(m) == 1, m                                                               # byte [seasonPlaying], 1`)
    season = struct.unpack('<I', p.le.obj_bytes(1)[m[0] + 2:m[0] + 6])[0]
    syms, cend, bss = cobj.link(p, obj, code_at, (1, bss_at),
                                externs={'SS_TAB': (1, at), 'ST_RANK': LABELS['ST_RANK'], 'SEASONW': (2, season)},
                                limit=bss_at)
    assert bss <= SIM_BSS, hex(bss)
    LABELS['ss_season'] = syms['ss_season']
    LABELS['ss_ord'] = syms['ss_ord']
    LABELS['ss_champ'] = syms['ss_champ']
    ov_end = ov_patch(p, (cend + 15) & ~15, at, bss_at)
    print(f'exe: statesim: {tab[0]} states, table obj1+{at:#x} ({len(tab)} B), ss_season obj1+'
          f'{syms["ss_season"][1]:#x}, code ..{cend:#x}, overrides ..{ov_end:#x}, .bss {bss} B at obj1+{bss_at:#x}')
    return at + 0x1000 * SIM_PAGES


OV_ASM = """
ss_entry:                               ; ripool's RI_PRE_PTR (pg_fix, before ri_season): statesim.c's ss_season
    push es                             ; with es = ds, cld (as gplay's gp_c)
    push ds
    pop es
    cld
    call SS_SEASON
    pushad                              ; (the harness: a copy of this season end's SR in SS_LAST)
    mov esi, ST_RANKW
    mov edi, SS_LAST
    mov ecx, SR_SIZE
    rep movsb
    popad
    pop es
    ret

st_ovr:                                 ; ripool's RI_OVR -> each state contest's team list (+2Fh), after ri_season
    pushad                              ; (RI_POST_PTR) and after a career load (engine.after_load): entry j = the
    mov esi, OV_TAB                     ; pool's override word, or 0 = the original; a new first club also goes into
.s:                                     ; every word keyed by it (ST_KEYS, ST_TAB, FX_TAB) and statesim's table
    movzx ecx, byte [esi + 2]           ; n (0: the end)
    test ecx, ecx
    jz .x
    mov ax, [esi]                       ; the original key -> its pool p (RI_OVR_KEYS), or none
    xor ebx, ebx
.p:
    cmp ebx, RP
    jae .np
    cmp [RI_KEYS + ebx * 2], ax
    je .fp
    inc ebx
    jmp .p
.np:
    mov ebx, -1
.fp:
    mov edi, [esi + 4]                  ; the contest's team list
    mov ebp, [esi + 8]                  ; statesim's words
    xor edx, edx
.j:
    mov ax, [esi + 12 + edx * 2]        ; the original word
    cmp ebx, -1
    je .o
    push eax
    mov eax, ebx
    imul eax, eax, RO2                  ; (RO dw per pool)
    mov ax, [RI_OVR + eax + edx * 2]
    test ax, ax
    jnz .nw
    pop eax
    jmp .o
.nw:
    add esp, 4
.o:
    mov [edi + edx * 2], ax
    mov [ebp + edx * 2], ax
    test edx, edx
    jnz .nx
    push ecx                            ; entry 0: the keyed words
    push edx
    movzx ecx, byte [esi + 3]
    movzx edx, byte [esi + 2]
    lea edx, [esi + 12 + edx * 2]       ; (the slots follow the original words)
.k:
    test ecx, ecx
    jz .kx
    push ebx
    mov ebx, [edx]
    mov [ebx], ax
    pop ebx
    add edx, 4
    dec ecx
    jmp .k
.kx:
    pop edx
    pop ecx
.nx:
    inc edx
    cmp edx, ecx
    jb .j
    movzx eax, byte [esi + 3]           ; next: 12 + 2n + 4 slots
    lea esi, [esi + 12 + ecx * 2]
    lea esi, [esi + eax * 4]
    jmp .s
.x:
    popad
    ret

st_post:                                ; ripool's RI_POST_PTR (pg_fix, after ri_season): the overrides, and SR used
    call st_ovr                         ; up: void until the next played state's group stage ends (also at a
    mov word [ST_RANKW], 0              ; career's start, where pg_fix runs too; not after a load: a mid-season
    ret                                 ; save keeps block 0)
align 4
    db 'SSLASTPT'                       ; (swostest: dd ST_RANK, SS_LAST, statesim's ss_ord, ss_champ)
    dd ST_RANKW, SS_LAST, SS_ORD, SS_CHAMP
SS_LAST: times SR_SIZE db 0
OV_TAB: OV_BYTES
"""


def ov_patch(p, at, tab_at, limit):
    """st_ovr + OV_TAB at obj1:at (statesim's pages): per state dw original key, db n, db slots, dd its contest's
    team list, dd its words in SS_TAB, n x dw original words, slots x dd the words keyed by its first club. Bound
    to ripool's RI_POST_PTR and engine.after_load('st_ovr'). Returns the end."""
    import engine
    import nasmcave
    import statecup
    try:
        import ripool
        rl = getattr(ripool, 'LABELS', {})
    except ImportError:
        rl = {}
    if 'RI_OVR' not in rl or 'RI_OVR_KEYS' not in rl:
        return at
    rp = getattr(ripool, 'RP', 20)
    structs = {}
    for e in statecup.ENTRIES:
        for st in e['states']:
            if st.get('struct') and st.get('first'):
                structs[(e['world'], st['id'], tuple(st['first']))] = st['struct']
    tb, ptrs = bytearray(), []                            # (one 'db' line: nasmcave's symbols are one-line defines)
    slots = LABELS.get('key_slots', {})
    for key, woff, words, ident in SIM_LAYOUT:
        sobj, soff = structs[ident]
        ks = slots.get(key, [])
        ptrs.append((len(tb), len(words), (sobj, soff + 0x2F), (1, tab_at + woff), ks))
        tb += struct.pack('<HBBII', key, len(words), len(ks), 0, 0) + struct.pack(f'<{len(words)}H', *words) \
            + bytes(4 * len(ks))
    tb += bytes(4)                                        # (n = 0: the end)
    sym = {'SR_SIZE': (0, SR_SIZE), 'SS_SEASON': LABELS['ss_season'], 'SS_ORD': LABELS['ss_ord'], 'SS_CHAMP': LABELS['ss_champ'], 'ST_RANKW': LABELS['ST_RANK'], 'RP': (0, rp), 'RO2': (0, 2 * getattr(ripool, 'RO', 16)), 'RI_KEYS': rl['RI_OVR_KEYS'], 'RI_OVR': rl['RI_OVR'], 'OV_BYTES': (0, 'db ' + ', '.join(str(b) for b in tb))}
    code, fix = nasmcave.assemble(OV_ASM, at, sym)
    lab = nasmcave.labels(OV_ASM, at, sym)
    assert at + len(code) <= limit, (hex(at + len(code)), hex(limit))
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    for off, n_, lst, ssw, ks in ptrs:
        b = lab['OV_TAB'] + off
        p.add_ptr(1, b + 4, *lst)
        p.add_ptr(1, b + 8, *ssw)
        for i, k in enumerate(ks):
            p.add_ptr(1, b + 12 + 2 * n_ + 4 * i, 1, k)
    LABELS['st_ovr'] = (1, lab['st_ovr'])
    engine.CALL_AT['st_ovr'] = (1, lab['st_ovr'])           # (over ko_patch's bare ret)
    if 'RI_POST_PTR' in rl:
        p.add_ptr(*rl['RI_POST_PTR'], 1, lab['st_post'])
    if 'RI_PRE_PTR' in rl and not os.environ.get('STATESIM_NOPRE'):   # (STATESIM_NOPRE=1: test builds with a
        p.add_ptr(*rl['RI_PRE_PTR'], 1, lab['ss_entry'])                # fixed SR of ripool's: overrides only)
    return at + len(code)

