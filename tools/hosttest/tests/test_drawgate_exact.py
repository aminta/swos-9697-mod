"""4.2 AFC mode (MC 11/11 check 2): drawgate's same_assoc_pairs refinement, brute-forced on small instances (<= 16
entrants; no build: conti.draw_bound + drawgate.rounds on synthetic specs, pure Python).

Each instance: one cup, knockout round(s) feeding a group stage (winners and / or losers routes), direct places of
2..4 associations. The simulation plays every route combination: each knockout's every distinct entrant order
through conti.c draw_ko's D_SAMEPAIRS (a club v the next unused one of its association, else an odd one listed
alone: the consecutive pairs as the tie loop reads them) - an 'order' knockout: every pairing (a superset) - and
every tie's winner. Its reachable group-stage association multisets S against drawgate's enumerated set E
(direct + exact halves, + every multiset within the variable bound):
- every source exact (drawgate's precondition) -> S == E;
- else S <= E (the loose bound sound), and drawgate names each same_assoc_pairs source it left loose and why;
- the precondition's classification = an independent one (holder slot, short of clubs, odd counts, routes in)."""
import itertools
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)

N = int(os.environ.get('HT_DGX_N') or 400)


def perms(counts):
    """distinct sequences of association labels"""
    tot = sum(counts.values())
    cur = []

    def rec(left):
        if not left:
            yield tuple(cur)
            return
        for a in sorted(counts):
            if counts[a]:
                counts[a] -= 1
                cur.append(a)
                yield from rec(left - 1)
                cur.pop()
                counts[a] += 1
    yield from rec(tot)


def sap_pairs(seq):
    """conti.c draw_ko D_SAMEPAIRS on a shuffled order -> the tie loop's pairs"""
    used, D = [0] * len(seq), []
    for i in range(len(seq)):
        if used[i]:
            continue
        used[i] = 1
        for j in range(i + 1, len(seq)):
            if not used[j] and seq[j] == seq[i]:
                used[j] = 1
                D += [seq[j], seq[i]]
                break
        else:
            D.append(seq[i])
    return tuple(sorted(tuple(sorted(D[k:k + 2])) for k in range(0, len(D) - 1, 2)))


def all_pairings(seq):
    seq = sorted(seq)
    if not seq:
        yield ()
        return
    a = seq[0]
    seen = set()
    for i in range(1, len(seq)):
        if seq[i] in seen:
            continue
        seen.add(seq[i])
        for p in all_pairings(seq[1:i] + seq[i + 1:]):
            yield ((a, seq[i]),) + p


def ko_outcomes(entrants, sap):
    """{(winners multiset, losers multiset)} over every draw and every result"""
    cnt = {}
    for a in entrants:
        cnt[a] = cnt.get(a, 0) + 1
    pairings = {sap_pairs(s) for s in perms(cnt)} if sap else set(all_pairings(list(entrants)))
    out = set()
    for pr in pairings:
        for res in itertools.product((0, 1), repeat=len(pr)):
            w = tuple(sorted(p[r] for p, r in zip(pr, res)))
            l_ = tuple(sorted(p[1 - r] for p, r in zip(pr, res)))
            out.add((w, l_))
    return out


def instance(rnd):
    """-> dict: na, rounds [{kind, sap, direct [assocs], win, lose}], ng, gs, holder, short"""
    na = rnd.randint(2, 4)
    shape = rnd.choice(('one', 'one', 'chain', 'two'))
    ng = rnd.choice((2, 3, 4))
    size = ng * 4

    def ko_direct(n, even):
        while True:
            d = [rnd.randrange(na) for _ in range(n)]
            odd = any(d.count(a) % 2 for a in range(na))
            if even is None or odd != even:
                return d
    even = rnd.random() < 0.6
    kos = []
    if shape == 'one':
        n = rnd.choice((2, 4, 6, 8))
        kos.append(dict(sap=True, direct=ko_direct(n, even), into='G', lose=rnd.random() < 0.4))
    elif shape == 'two':
        for _ in range(2):
            n = rnd.choice((2, 4, 6))
            kos.append(dict(sap=rnd.random() < 0.8, direct=ko_direct(n, rnd.random() < 0.6 or None), into='G',
                            lose=rnd.random() < 0.3))
    else:                                               # (a knockout into a same_assoc_pairs one: routes in)
        n0 = rnd.choice((2, 4))
        kos.append(dict(sap=rnd.random() < 0.5, direct=ko_direct(n0, None), into='K1', lose=False))
        kos.append(dict(sap=True, direct=ko_direct(rnd.choice((0, 2, 4)), None), into='G', lose=rnd.random() < 0.3))
    routed = 0
    for i, k in enumerate(kos):
        n = len(k['direct']) + (len(kos[0]['direct']) // 2 if shape == 'chain' and i == 1 else 0)
        k['size'] = n
        if k['into'] == 'G':
            routed += n // 2 + (n // 2 if k['lose'] else 0)
    if routed > size:
        return None
    gdirect = [rnd.randrange(na) for _ in range(size - routed)]
    holder = rnd.random() < 0.08
    short = rnd.random() < 0.08
    if any(k['size'] == 0 or k['size'] % 2 for k in kos):
        return None
    return dict(na=na, shape=shape, kos=kos, ng=ng, gs=4, gdirect=gdirect, holder=holder, short=short)


def spec(I):
    import conti
    nk = len(I['kos'])
    gj = nk
    body = bytearray((nk + 1, 0, 0, 0))
    access = []
    for j, k in enumerate(I['kos']):
        b = bytearray(conti.RB)
        b[0], b[4], b[18] = conti.K['ko'], conti.DRAW['same_assoc_pairs' if k['sap'] else 'order'], k['size']
        b[10] = (gj if k['into'] == 'G' else 1)
        b[11] = gj if k['lose'] else conti.OUT
        for q in range(4):
            b[12 + q] = conti.OUT
        body += b
        access += [(a, 0, j, 0) for a in k['direct']]
    b = bytearray(conti.RB)
    b[0], b[4], b[5], b[6], b[7], b[18] = conti.K['groups'], conti.DRAW['groups'], 1, I['ng'], I['gs'], I['ng'] * 4
    b[10] = b[11] = conti.OUT
    for q in range(4):
        b[12 + q] = conti.OUT
    b[23] = 1
    body += b
    access += [(a, 0, gj, 0) for a in I['gdirect']]
    places = {}
    for a, *_ in access:
        places[a] = places.get(a, 0) + 1
    clubs = {a: 32 for a in range(I['na'])}
    if I['short']:                                      # (the first knockout's first association: one club short)
        a0 = I['kos'][0]['direct'][0]
        clubs[a0] = places[a0] - 1
    holders = [(0xFF, 0, len(I['kos']) - 1, 0)] if I['holder'] else []
    return bytes(body), access, holders, [], [f'A{a}' for a in range(I['na'])], clubs


def expect_exact(I, i):
    k = I['kos'][i]
    if not k['sap'] or k['into'] != 'G':
        return False
    if I['shape'] == 'chain':
        return False
    if I['holder'] and i == len(I['kos']) - 1:
        return False
    if I['short'] and any(a == I['kos'][0]['direct'][0] for a in k['direct']):
        return False
    return all(k['direct'].count(a) % 2 == 0 for a in set(k['direct']))


def simulate(I):
    """the group stage's reachable association count tuples"""
    na = I['na']
    states = {((), ())}                                # (into K1, into G) as sorted label tuples
    for i, k in enumerate(I['kos']):
        nxt = set()
        for k1, g in states:
            ent = tuple(k['direct']) + (k1 if (I['shape'] == 'chain' and i == 1) else ())
            for w, l_ in ko_outcomes(ent, k['sap']):
                if k['into'] == 'G':
                    nxt.add((k1, tuple(sorted(g + w + (l_ if k['lose'] else ())))))
                else:
                    nxt.add((tuple(sorted(k1 + w)), g))
        states = nxt
    out = set()
    for _, g in states:
        t = [0] * na
        for a in tuple(I['gdirect']) + g:
            t[a] += 1
        out.add(tuple(t))
    return out


def enumerated(r, na):
    import drawgate
    names = sorted(r['avail'])
    out = set()
    for t in drawgate.every([r['avail'][a] for a in names], r['nvar']):
        c = [r['direct'].get(a, 0) for a in range(na)]
        for a, x in zip(names, t):
            c[a] += x
        out.add(tuple(c))
    return out


def test_drawgate_exact_bruteforce():
    import conti
    import drawgate
    rnd = random.Random(0x5A9)
    n = eq = sub = 0
    kinds = {}
    while n < N:
        I = instance(rnd)
        if I is None:
            continue
        sp = spec(I)
        conti.BOUND_IN[0] = sp
        conti.draw_bound(*sp)
        conti.AREG[0] = bytes(I['na'])
        rs = drawgate.rounds(None)
        assert len(rs) == 1, rs
        r = rs[0]
        exp = {f'0.{i}{"wl"[q]}' for i, k in enumerate(I['kos']) if expect_exact(I, i)
               for q in ((0, 1) if k['lose'] else (0,))}
        got = set(r['exact'])
        if got != exp:
            return False, f'classification: drawgate exact {sorted(got)} != expected {sorted(exp)}: {I}'
        nsap_loose = sum((1 + k['lose']) for i, k in enumerate(I['kos'])
                         if k['sap'] and k['into'] == 'G' and not expect_exact(I, i))
        if len(r['loose']) != nsap_loose:
            return False, f'loose list {r["loose"]} != {nsap_loose} expected: {I}'
        for why in r['loose']:
            kinds[why.split(': ', 1)[1]] = kinds.get(why.split(': ', 1)[1], 0) + 1
        if I['short']:                                  # (the game leaves a bye there: no simulation, drawgate's
            n += 1                                      #  classification only - draw_bound's own test covers it)
            continue
        S, E = simulate(I), enumerated(r, I['na'])
        all_exact = all(expect_exact(I, i) for i, k in enumerate(I['kos']) if k['into'] == 'G')
        if all_exact:
            if S != E:
                return False, f'exact sources: S {sorted(S)} != E {sorted(E)}: {I}'
            eq += 1
        else:
            if not S <= E:
                return False, f'loose bound unsound: S - E = {sorted(S - E)[:6]}: {I}'
            sub += 1
        n += 1
    return True, (f'{n} instances: {eq} all-exact S == E, {sub} loose S <= E; loose reasons '
                  + ', '.join(f'{k} {v}' for k, v in sorted(kinds.items())))


if __name__ == '__main__':
    ok, msg = test_drawgate_exact_bruteforce()
    print('PASS' if ok else 'FAIL', msg)
    sys.exit(0 if ok else 1)
