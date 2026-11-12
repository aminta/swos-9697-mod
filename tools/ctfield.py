"""Root fix C (MC 11/11): the continental cups' field invariants, read from an edition's CT_IN / CT_OUT.

check(ib, o, lay, st) -> [violation, ...] for the edition in CT_OUT (built from CT_IN at the season end):
  1. per round, per association: entrants <= the data's direct places of that association in that round + the
     round's holder places of that association (CT_ST.hold; a vacant one: any association) + its 'outside' places (any association: conti.py fields()) + a group stage's unfed places
     (draw_groups' fill: any association) + the clubs of that association the round's feeder rounds actually hold (a
     knockout's winners, a group's places, another cup's losers - the spec's targets). A forced extra entrant, or
     anything else adding a club the data cannot give, shows here.
  2. no club twice in one round;
  3. the career club (CT_IN.manager) enters each cup once: in a round it is either the round of its entry or it was
     in a round feeding it;
  4. (4.2 root fix b) an association with a table holds at least as many clubs in CT_IN as the data's places it fills,
     and access() never ran out of an association's clubs (CT_OUT.pad[1]): the violation names the association.
The bound is checked on every edition the access built (CT_ST.season >= 1). Season 1's edition is built from the data's
own real entrant lists (the S1 block, not the access), so only checks 2 and 3 apply to it. The Intercontinental
(stepladder: the confederations' holders by slot) gets checks 2 and 3 only. Pure: no exe, no DOSBox. The harness calls
it at the end of every session (swostest field_check: the edition in memory then) and test_field() on native
natural and forced seasons (python3 tools/ctfield.py)."""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conti  # noqa: E402

_PLAN = {}


def plan(confs=None):
    """{'cups', 'assocs', 'spec', 'direct': {(ci, j): Counter}, 'extra': {(ci, j): n}, 'feed': {(ci, j): [(cf, jf)]},
    'step': {ci}} from the competition data - the same load() as the exe's build (rounds, targets, sizes)."""
    confs = tuple(confs or conti.CONFS)
    if confs in _PLAN:
        return _PLAN[confs]
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        spec, assocs, cups = conti.load(list(confs))
    direct, extra, feed, step, gsend, hold = {}, {}, {}, set(), {}, {}
    for ci, (conf, ck) in enumerate(cups):
        c = next(x for x in conti._read(conf, 'format')['cups'] if x['key'] == ck)
        conti._norm(c)
        if c.get('stepladder'):
            step.add(ci)
        rk = {r['key']: j for j, r in enumerate(c['rounds'])}
        a = next((x for x in (conti._read(conf, 'access') or {}).get('cups', []) if x['key'] == ck), {})
        for ak, entries in (a.get('access') or {}).items():
            if ak == 'holders':                         # (a holder place: its holder's association - CT_ST.hold)
                for hk, r in entries.items():
                    j = rk[r if r in rk else conti.ALIAS.get(r, r)]
                    hc = next((i for i, x in enumerate(cups) if x == (conf, hk)), None)
                    hold.setdefault((ci, j), []).append(hc)
            elif ak not in ('from', 'outside'):
                for r, _ in entries:
                    j = rk[r if r in rk else conti.ALIAS.get(r, r)]
                    direct.setdefault((ci, j), Counter())[ak] += 1
        size, outside, _ = conti.FIELDS.get((conf, ck), ([], [], []))
        for j, n in enumerate(outside):
            if n:
                extra[(ci, j)] = extra.get((ci, j), 0) + n
        gs1 = ((__import__('guests').load(conf) or {}).get('season1') or {}).get(ck) or {}
        for r, keys in gs1.items():                     # (the guests' real places: their own 'g:' associations)
            j = rk[r if r in rk else conti.ALIAS.get(r, r)]
            extra[(ci, j)] = extra.get((ci, j), 0) + len(keys)
        for j in range(len(c['rounds'])):
            R = conti.rbytes(spec, ci, j)
            ts = {R[10], R[11], *R[12:16]} | ({R[20]} if R[19] else set())
            for t in ts:
                if t not in (conti.OUT, conti.CHAMP):
                    feed.setdefault((t >> 4, t & 15), []).append((ci, j))
            if R[0] == conti.K['groups']:               # (what a group stage sends to each target: its places)
                for q in range(4):
                    if R[12 + q] not in (conti.OUT, conti.CHAMP):
                        gsend[(ci, j, R[12 + q])] = gsend.get((ci, j, R[12 + q]), 0) + R[6]
                if R[19]:
                    gsend[(ci, j, R[20])] = gsend.get((ci, j, R[20]), 0) + R[6] * R[19]
    cupdirect = [sum(sum(v.values()) for (c, _), v in direct.items() if c == ci) for ci in range(len(cups))]
    _PLAN[confs] = p = {'cupdirect': cupdirect, 'cups': cups, 'assocs': assocs, 'spec': spec, 'direct': direct, 'extra': extra,
                        'feed': feed, 'step': step, 'gsend': gsend, 'hold': hold}
    return p


def rounds_of(ib, o, lay, ci, j):
    """the round's entrants as CT_IN club indices (1-based; 0 = an empty slot)"""
    o_nent, o_ent, NRD, NE = lay[11], lay[12], lay[18], lay[19]
    n = o[o_nent + ci * NRD + j]
    return list(struct.unpack_from(f'<{n}H', o, o_ent + 2 * (ci * NRD * NE + j * NE))) if n else []


def fill(p, ent, ci, j):
    """a group stage's places nobody feeds (conti.c draw_groups' fill: the best club with no cup, any association,
    e.g. an earlier round's loser): its size - direct places - holder / outside places - what its feeders send (a
    knockout's winners or losers: half its clubs, odd ones up; a group stage: its places)"""
    R = conti.rbytes(p['spec'], ci, j)
    if not R or R[0] != conti.K['groups']:
        return 0
    t = ci << 4 | j
    sent = 0
    for f in p['feed'].get((ci, j), []):
        F = conti.rbytes(p['spec'], *f)
        n = len([x for x in ent.get(f, []) if x])
        if F[0] == conti.K['groups']:
            sent += p['gsend'].get((*f, t), 0)
        else:
            sent += ((n + 1) // 2 if F[10] == t else 0) + (n // 2 if F[11] == t else 0)
    want = R[6] * R[7] - sum(p['direct'].get((ci, j), {}).values()) - p['extra'].get((ci, j), 0) - \
        len(p['hold'].get((ci, j), []))
    return max(0, want - sent)


def check(ib, o, lay, st, confs=None, forced=False, notes=None):
    """ib, o, st: CT_IN, CT_OUT, CT_ST bytes (CT_ST: the season counter, the holders the access used). forced: a
    CONTI_FORCE / CONTI_FORCE2 test build - in a holders' cup (no access place: root fix D replaces the entrant sharing
    the most cups, another association by design) the career club is not counted against its association, a note
    instead (notes: a list to append to)"""
    p = plan(confs)
    season = struct.unpack_from('<H', st, 2)[0]
    hold_a = lambda c: st[4 + 12 * c + 2] if c is not None and struct.unpack_from('<H', st, 4 + 12 * c)[0] else None
    o_club, NRD = lay[7], lay[18]
    mgr = struct.unpack_from('<H', ib, 6)[0]
    nclub = struct.unpack_from('<H', ib, 4)[0]
    an = lambda x: p['assocs'][ib[o_club + 12 * (x - 1) + 2]] if 0 < x <= nclub and \
        ib[o_club + 12 * (x - 1) + 2] < len(p['assocs']) else f'#{x}'
    word = lambda x: struct.unpack_from('<H', ib, o_club + 12 * (x - 1))[0] if 0 < x <= nclub else 0
    ent = {(ci, j): rounds_of(ib, o, lay, ci, j) for ci in range(len(p['cups'])) for j in range(NRD)}
    bad = []
    for (ci, j), es in ent.items():
        if not es:
            continue
        name = f'{p["cups"][ci][0]}:{p["cups"][ci][1]} round {j}'
        clubs = [x for x in es if x]
        dup = [x for x, k in Counter(clubs).items() if k > 1]
        if dup:
            bad.append(f'{name}: club(s) twice {[hex(word(x)) for x in dup]}')
        if season >= 1 and ci not in p['step']:
            have = Counter(an(x) for x in clubs)
            if forced and mgr in clubs and p['cupdirect'][ci] == 0:
                have[an(mgr)] -= 1
                if notes is not None:
                    notes.append(f'{name}: the forced career club ({an(mgr)}) in a holders\' cup, not counted')
            fed = Counter()
            for f in p['feed'].get((ci, j), []):
                fed.update(an(x) for x in set(ent.get(f, [])) if x)
            hl = [hold_a(c) for c in p['hold'].get((ci, j), [])]
            slack = p['extra'].get((ci, j), 0) + fill(p, ent, ci, j) + hl.count(None)   # (a vacant holder place:
                                                # access()'s stand-in, the best ranked club not yet in - any association)
            hs = Counter(p['assocs'][x] if x < len(p['assocs']) else f'#{x:#x}'
                         for x in hl if x is not None)
            for a, k in have.items():
                lim = p['direct'].get((ci, j), Counter())[a] + fed[a] + slack + hs[a]
                if k > lim:
                    bad.append(f'{name}: {a} {k} clubs, the data gives at most {lim} (direct '
                               f'{p["direct"].get((ci, j), Counter())[a]}, fed {fed[a]}, holders {hs[a]}, outside/fill {slack})')
    if season >= 1:                     # 4. (4.2 root fix b) every association with a table holds at least as many
        o_lg, o_cup, NA, NL = lay[3], lay[4], lay[14], lay[15]   # clubs as the data's places it fills (league codes,
        want = Counter()                                         # its cup winner) - a career country cut to its top 9
        for v in p['direct'].values():                           # records (ct_begin cleared its table) shows here
            want.update(v)
        for i, a in enumerate(p['assocs'][:NA]):
            lg = struct.unpack_from(f'<{NL}H', ib, o_lg + 2 * NL * i)
            held = {x for x in lg if x} | ({struct.unpack_from('<H', ib, o_cup + 2 * i)[0]} - {0})
            if lg[0] and want[a] > len(held):
                bad.append(f'{a}: the data gives it {want[a]} places, CT_IN holds {len(held)} of its clubs')
        if o[2]:                        # (conti.c access(): CT_OUT.pad[1], the first association whose table ran out)
            a = p['assocs'][o[2] - 1] if o[2] - 1 < len(p['assocs']) else f'#{o[2] - 1}'
            ai = o[2] - 1                # (MC 12/11, class D: the association's table as CT_IN holds it, for the diagnosis)
            lg = struct.unpack_from(f'<{NL}H', ib, o_lg + 2 * NL * ai) if ai < NA else ()
            cw = struct.unpack_from('<H', ib, o_cup + 2 * ai)[0] if ai < NA else 0
            nlg = sum(1 for x in lg if x)
            bad.append(f'{a}: access() found no club left for one of its places (CT_IN: {nlg} league clubs, cup '
                       f'winner {"none" if not cw else "in the league" if cw in lg else "not in the league"}, the data '
                       f'{want[a]} places)')
    if mgr:
        for ci in range(len(p['cups'])):
            entries = [j for j in range(NRD) if mgr in ent[(ci, j)]
                       and not any(mgr in ent.get(f, []) for f in p['feed'].get((ci, j), []))]
            if len(entries) > 1:
                bad.append(f'{p["cups"][ci][0]}:{p["cups"][ci][1]}: the career club entered {len(entries)} times '
                           f'(rounds {entries})')
    return bad


def test_field(seasons=6, seeds=(7, 3)):
    """natural seasons of every confederation (a career club; CONCACAF none: native conti.test's own ccc ct_gamein
    assert with one) and a forced one (CONTI_FORCE rec:final + FORCE2 lib:groups, a Brazilian): 0 violations"""
    import contextlib
    import ctypes
    import io
    runs = [(c, sd, {'CONTI_TEST_MANAGER': '0' if c == 'concacaf' else '19'}) for c in
            ('conmebol', 'afc', 'caf', 'concacaf', 'ofc') for sd in seeds]
    runs += [('conmebol', sd, {'CONTI_TEST_MANAGER': '19', 'CONTI_FORCE': 'rec:final', 'CONTI_FORCE2': 'lib:groups',
                               'CONTI_GPLACE': '1', 'CONTI_KOWIN': '1'}) for sd in seeds]
    fails = 0
    for conf, sd, env in runs:
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        bad, n = [], [0]
        forced = 'CONTI_FORCE' in env

        def hook(L, names, step):
            lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
            g = lambda k, i: bytes((ctypes.c_ubyte * lay[i]).in_dll(L, k))
            bad.extend(x for x in check(g('CT_IN', 0), g('CT_OUT', 2), lay, g('CT_ST', 1), confs=(conf,),
                                        forced=forced) if x not in bad)
            n[0] += 1
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                conti.test((conf,), seasons=seasons, seed=sd, hook=hook)
        finally:
            for k, v in old.items():
                os.environ.pop(k) if v is None else os.environ.__setitem__(k, v)
        fails += bool(bad)
        print(f'{"FAIL" if bad else "ok"} {conf} seed {sd}{" forced" if forced else ""}: {n[0]} checks', bad[:3])
    assert not fails, f'ctfield: {fails} run(s) with violations'
    print('ctfield: all OK')


if __name__ == '__main__':
    test_field()
