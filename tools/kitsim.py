#!/usr/bin/env python3
"""Offline simulator of SWOS automatic home/away kit selection.

Mirrors SetInGameTeamsPrimaryColors / MeasureTeamKitsSimilarity /
GetTeamKitsSimilarityFactor / IsSingleColorKitSimilar /
ResolveTeamKitColorConflict (ref/swos.asm) register by register, so that
changes to the two conflict tables (or the threshold) can be tested on all
pairings of real teams before building an exe.

Analysis of the colour adjacency graph: Daniele Bordes (DaniSwos), SWOS
United forum thread "Home-Away kit automatic selection".

Usage:
  kitsim.py match TEAM.020:MILAN TEAM.020:INTER
  kitsim.py stats [--variant NAME] TEAM.020 TEAM.008 ...
  kitsim.py diff  --variant NAME TEAM.020 TEAM.008 ...
"""
import argparse, os, sys

ORD, SLEEVES, VSTRIPES, HSTRIPES = 0, 1, 2, 3
SHIRT = {0: 'plain', 1: 'sleeves', 2: 'v-stripes', 3: 'h-stripes'}
COLOR = ['grey', 'white', 'black', 'orange', 'red', 'blue', 'brown', 'lblue',
         'green', 'yellow']

# original tables (ENGLISH.EXE, conflictingBasicTeamColorsTable /
# conflictingShortsTeamColorsTable): row = colour, bit n = clashes with n
BASIC = [0x1A1, 0x002, 0x164, 0x218, 0x058, 0x0A5, 0x054, 0x0A1, 0x105, 0x208]
SHORTS = [0x1A3, 0x283, 0x164, 0x218, 0x058, 0x0E5, 0x074, 0x0A3, 0x105, 0x20A]
# dseg_130942: stripe pair -> single colour used for a second check
MERGE = [1, 5, 7, 1, 2, 0, 4, 5, 6, 4, 9, 3, 1, 9, 9, 1, 7, 7, 1, 0, 0, 4, 3,
         3, 4, 6, 6, 4, 2, 6, 0, 5, 7, 6, 3, 4, 2, 7, 5, 9, 5, 8, 9, 7, 8]
TIEBREAK = [4, 5, 1, 7, 9, 0, 3, 6, 8, 2]
THRESHOLD = 11


class Rules:
    def __init__(self, basic=BASIC, shorts=SHORTS, threshold=THRESHOLD,
                 fixflat=False, wshorts=5):
        self.basic, self.shorts, self.threshold = list(basic), list(shorts), threshold
        # fixflat: test shirtType1/2 instead of D0/D4 at the loop start, so a
        # striped kit that the merge pass did not convert keeps its stripes
        self.fixflat, self.wshorts = fixflat, wshorts

    def c(self, a, b):
        return (self.basic[a] >> b) & 1

    def s(self, a, b):
        return (self.shorts[a] >> b) & 1

    def factor(self, k1, k2):
        """GetTeamKitsSimilarityFactor: k = (type, stripes, basic, shorts)."""
        D0, D1, D2, D3 = k1
        D4, D5, D6, D7 = k2
        st1, st2 = D0, D4
        C, S = self.c, self.s
        while True:
            # on re-entry D0/D4 hold the "converted" flags, not shirt types:
            # an unconverted team gets basic := stripes (asm behaviour)
            if (st1 if self.fixflat else D0) == ORD:
                D2 = D1
            if (st2 if self.fixflat else D4) == ORD:
                D6 = D5
            f = None
            if C(D1, D5) and C(D2, D6):
                f = 99
            elif C(D1, D6) and C(D2, D5):
                f = 99
            elif ((st1 == SLEEVES and st2 == ORD) or (st1 == ORD and st2 == SLEEVES)) \
                    and S(D1, D7) and S(D3, D5):
                f = 88
            elif st1 in (VSTRIPES, HSTRIPES) and st2 in (VSTRIPES, HSTRIPES) \
                    and (C(D3, D5) or C(D3, D6)) and (C(D7, D1) or C(D7, D2)):
                f = 77
            elif st1 == SLEEVES and st2 == SLEEVES and C(D1, D5):
                f = 66
            else:
                f = 0
                if st1 != st2:
                    f -= 4
                if st1 == ORD:
                    f -= 2
                    if st2 == SLEEVES and D2 == D1 and D3 == D1:
                        f -= 6
                if st2 == ORD:
                    f -= 2
                    if st1 == SLEEVES and D6 == D5 and D7 == D5:
                        f -= 6
                if (st1 == ORD and st2 == SLEEVES) or (st1 == SLEEVES and st2 == ORD):
                    f += 1
                f += 5 * C(D1, D5) + 5 * C(D1, D6) + 2 * C(D1, D7)
                f += 5 * C(D2, D5) + 5 * C(D2, D6) + 2 * C(D2, D7)
                f += 2 * C(D3, D5) + 2 * C(D3, D6) + self.wshorts * C(D3, D7)
            # cmp similarityFactor, 11 / jnb: unsigned word compare, so a
            # negative factor also skips the stripe-merge pass
            if f < 0 or f >= 11:
                return max(f, 0)
            D0 = D4 = 0
            for i in range(0, len(MERGE), 3):
                a, b, m = MERGE[i:i + 3]
                if D0 == 0 and st1 in (VSTRIPES, HSTRIPES) and \
                        ((D1 == a and D2 == b) or (D1 == b and D2 == a)):
                    D0, st1, D1, D2 = 1, ORD, m, m
                if D4 == 0 and st2 in (VSTRIPES, HSTRIPES) and \
                        ((D5 == a and D6 == b) or (D5 == b and D6 == a)):
                    D4, st2, D5, D6 = 1, ORD, m, m
            if not (D0 or D4):
                return f

    def choose(self, t1, t2):
        """SetInGameTeamsPrimaryColors. t = Team. Returns (outcome, sims).
        outcome: ('kits', d7) with bit1 = team1 away kit, bit0 = team2 away
        kit; ('mono', c) = team2 in a plain colour-c kit; ('fixed',) =
        red vs blue."""
        sims = [self.factor(t1.pr, t2.pr), self.factor(t1.pr, t2.sec),
                self.factor(t1.sec, t2.pr), self.factor(t1.sec, t2.sec)]
        th = self.threshold
        for d7, v in enumerate(sims):
            if v < th:
                return ('kits', d7), sims
        mono = lambda c: self.factor((ORD, c, c, c), t1.pr) < th
        cands = [t2.pr[1]]
        if t2.pr[1] != 0:   # asm tests the stripes colour, not the shirt type
            cands.append(t2.pr[2])
        cands += [t2.pr[3], t2.sec[1]]
        if t2.sec[1] != 0:
            cands.append(t2.sec[2])
        cands.append(t2.sec[3])
        for c in cands + TIEBREAK:
            if mono(c):
                return ('mono', c), sims
        return ('fixed',), sims


class Team:
    def __init__(self, rec, src):
        self.name = rec[5:22].split(b'\0')[0].decode('latin1')
        self.src = src
        self.pr = tuple(rec[26:30])
        self.prsocks = rec[30]
        self.sec = tuple(rec[31:35])
        self.secsocks = rec[35]


def kit_str(k, socks=None):
    t, s, b, sh = k
    if t == ORD:
        txt = COLOR[s]
    else:
        txt = '%s %s/%s' % (SHIRT[t], COLOR[s], COLOR[b])
    return txt + ', ' + COLOR[sh] + ' shorts'


def load(path):
    d = open(path, 'rb').read()
    n = (len(d) - 2) // 684
    return [Team(d[2 + i * 684:2 + (i + 1) * 684], os.path.basename(path))
            for i in range(n)]


def find_team(spec, datadir):
    f, name = spec.split(':', 1)
    path = f if os.path.exists(f) else os.path.join(datadir, f)
    for t in load(path):
        if t.name == name.upper():
            return t
    hits = [t for t in load(path) if name.upper() in t.name]
    if len(hits) == 1:
        return hits[0]
    sys.exit('team %s not found (or ambiguous) in %s' % (name, path))


def outcome_str(o, t1, t2):
    if o[0] == 'kits':
        d7 = o[1]
        a = 'away' if d7 & 2 else 'home'
        b = 'away' if d7 & 1 else 'home'
        return '%s-%s' % (a, b)
    if o[0] == 'mono':
        return 'home-plain %s' % COLOR[o[1]]
    return 'red-blue'


# --- variants proposed for the mod ----------------------------------------

def table_from_edges(edges, base):
    t = list(base)
    for a, b, on in edges:
        for x, y in ((a, b), (b, a)):
            if on:
                t[x] |= 1 << y
            else:
                t[x] &= ~(1 << y)
    return t


def variants():
    G, W, K, O, R, B, N, L, V, Y = range(10)   # V = green
    v = {'orig': Rules()}
    kb = [(K, B, 0)]
    far = [(K, B, 0), (K, V, 0), (B, L, 0)]
    mk = lambda e, **kw: Rules(table_from_edges(e, BASIC), table_from_edges(e, SHORTS), **kw)
    v['noKB'] = mk(kb)
    v['fix'] = Rules(fixflat=True)
    v['A'] = mk(kb, fixflat=True)            # black/blue + flatten fix
    v['B'] = mk(far, fixflat=True)           # + black/green, blue/lblue
    v['C'] = mk(far, fixflat=True, wshorts=3)  # + shorts vs shorts weight 3
    v['th13'] = Rules(threshold=13)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['match', 'stats', 'diff'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--variant', default='orig')
    ap.add_argument('--data', default=os.path.join(
        os.path.dirname(__file__), '..', 'orig', 'DATA'))
    a = ap.parse_args()
    V = variants()
    if a.cmd == 'match':
        t1, t2 = (find_team(s, a.data) for s in a.args[:2])
        for name in ([a.variant] if a.variant != 'all' else V):
            o, sims = V[name].choose(t1, t2)
            print('%-10s %s (%s) vs %s (%s): sims %s -> %s' % (
                name, t1.name, kit_str(t1.pr), t2.name, kit_str(t2.pr),
                sims, outcome_str(o, t1, t2)))
        return
    teams = []
    for f in a.args:
        teams += load(f if os.path.exists(f) else os.path.join(a.data, f))
    # league-like pairings: both teams from the same TEAM file
    pairs = [(x, y) for x in teams for y in teams if x is not y and x.src == y.src]
    if a.cmd == 'stats':
        for name in ([a.variant] if a.variant != 'all' else V):
            cnt = {}
            for x, y in pairs:
                k = outcome_str(V[name].choose(x, y)[0], x, y)
                k = k.split(' ')[0] if k.startswith('home-plain') else k
                cnt[k] = cnt.get(k, 0) + 1
            print('%-10s' % name, ', '.join('%s %.1f%%' % (k, 100 * n / len(pairs))
                                             for k, n in sorted(cnt.items(), key=lambda x: -x[1])))
        return
    base, new = V['orig'], V[a.variant]
    for x, y in pairs:
        o1 = outcome_str(base.choose(x, y)[0], x, y)
        o2, sims = new.choose(x, y)
        o2 = outcome_str(o2, x, y)
        if o1 != o2:
            print('%-18s %-34s | %-18s %-34s : %s -> %s' % (
                x.name, kit_str(x.pr), y.name, kit_str(y.pr), o1, o2))


if __name__ == '__main__':
    main()
