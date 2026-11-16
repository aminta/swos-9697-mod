"""4.2 Supercoppa Serie C - the fixture port's MINI-LEAGUE harness (lane 3; design: internal/handoff/
supercoppa-c-design-20261116.md (e), interface: tools/fpml.h, frozen baf49ca). Registered by swostest (register(mod), as
fpgate) or run alone: python3 tools/fpmlgate.py <scenario>.

Three parts:
1. THE MODEL (pure Python, from the spec supercoppa-c-spec.md 1 rows 2-5 + the venue rule): the md1 draw from the seed,
   md2 / md3 from md1's result (WINNER_RESTS), the table (3 / 1 / 0; points, goal difference, goals for, away goals
   for, lots). It is the oracle of the DOSBox scenarios; the host scenarios prove it equal to the engine's
   sr_mini_sched / sr_rr_table on every md1 draw x every score 0..3 of the three matches.
2. HOST scenarios fpml_host_* (C compiled on the host, no DOSBox): the engine's rules (rules/sr_stage.c with
   sr_mini_sched: tools/swce once vendored, else FPML_ENGINE, else the minilg worktree) against the model, the
   three-club tie-break cases by hand, fpml.h's layout, the test switches' plumbing, the calendar units.
3. DOSBox scenarios world_supc_* (World 2026-27 career, FPORT=1 builds; they SKIP while the checkout has no producer -
   no fp_ml_open in tools/*.c - or the data has no 'mini_leagues' row, BEFORE any build).

Test switches (modver TEST_VARS / BUILD_SWITCHES; fpad.ml_test_flags -> -DFP_MLF_INIT / -DFP_MLSEED_INIT):
  FPML_FORCE='md:hg:ag,...'  the match of matchday md (1..3) ends hg-ag (home first) whoever plays it: fp_ml_sim's
                             simulated ones AND the career club's own (fp_leg, FPORT_TEST builds)
  FPML_SEED=n                the md1 draw's seed (n != 0)
  GPLAY_FORCE=k + DPLAY_FORCE=100+k   (existing) the career club k-th of its group: 1 = an entrant, 12 = neither an
                             entrant nor in the play-off / play-out
State read: FP_ML (2 x 56 B; ITALIAN.syms.json fpad / fpml / swe 'FP_ML', obj4), FP_ST's log (codes 15..18 =
FL_MLOPEN, FL_MLSIM, FL_MLADD, FL_MLDONE after fpad.c's FL_PLOAD 14), the career calendar, the FP item's ML block in a
.CAR (item + 36: 'ML', version 1, count, 2 instances)."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = None
NAME = 'SUPERCOPPA SERIE C'
TEAM = os.environ.get('FPML_TEAM') or 'EUROPA,ITALIA,SERIE C GIRONE B,CAMPOBASSO'
ME = int(os.environ.get('FPML_ME') or 1)    # (the career club's index in fp_ml.club[]: the entrants in FP_MLT.ent order,
#   divisions 2, 3, 4 = groups A, B, C; CAMPOBASSO = group B)
L_UNIT, OFF = 128, (1, 2, 3)                # (the league's last unit; the row's "units": 129, 130, 131)
PTS = (3, 1, 0)
ML_SIZE, ML_N, ML_AT = 56, 2, 36            # (struct fp_ml; FP_ML_N; the ML block's offset in the FP item)
ST_SIZE, MAGIC = 420, 0x50504631            # (fpad.ST_SIZE; FP_MAGIC)
FL = {1: 'ADD', 2: 'INST', 3: 'RES', 4: 'REFUSED', 5: 'MISSED', 6: 'REVAL', 7: 'SIM', 8: 'ORPHAN', 9: 'NEW', 10: 'LOAD',
      11: 'SEASON', 12: 'LEG', 13: 'LEGX', 14: 'PLOAD', 15: 'MLOPEN', 16: 'MLSIM', 17: 'MLADD', 18: 'MLDONE'}
SLOT_PORT = 4                               # (the calendar entries' slot byte of gplay's ko[0])
CAL_BYTES = 1604
M32 = 0xFFFFFFFF


# ---------------------------------------------------------------- the model

def mix(h, v):
    h ^= (v + 0x9E3779B9 + (h << 6) + (h >> 2)) & M32
    h ^= h >> 16
    h = h * 0x7FEB352D & M32
    h ^= h >> 15
    h = h * 0x846CA68B & M32
    return h ^ (h >> 16)


def md1(seed):
    """the draw: (home, away, the club that rests) - spec row 2"""
    rest = mix(seed, 0x7E570000) % 3
    o1, o2 = (rest + 1) % 3, (rest + 2) % 3
    return (o2, o1, rest) if mix(seed, 0x40BE0000) & 1 else (o1, o2, rest)


def later(seed, hg, ag):
    """md2 and md3 as (home, away) once md1 ended hg-ag - spec rows 3, 4 and the venue rule (each club hosts once)"""
    h, a, rest = md1(seed)
    r2 = h if hg > ag else a                # (md2's resting club: md1's winner, on a draw its away side)
    other = a if r2 == h else h
    h2 = other if other == a else rest      # (md1's away side hosts md2 when it plays it, else md1's resting club)
    return ((h2, other if h2 == rest else rest), (r2, rest) if h2 == rest else (rest, r2))


def table(ms, seed, n=3, pts=PTS):
    """ms [(home, away, hg, ag)] played -> the rows best first: dicts club, pts, gd, gf, agf (spec row 5; the lots from
    the seed and the club)"""
    r = [dict(club=c, pts=0, gd=0, gf=0, agf=0, pl=0) for c in range(n)]
    for h, a, hg, ag in ms:
        r[h]['pl'] += 1
        r[a]['pl'] += 1
        r[h]['gf'] += hg
        r[a]['gf'] += ag
        r[a]['agf'] += ag
        r[h]['gd'] += hg - ag
        r[a]['gd'] += ag - hg
        r[h]['pts'] += pts[0] if hg > ag else pts[1] if hg == ag else pts[2]
        r[a]['pts'] += pts[0] if ag > hg else pts[1] if hg == ag else pts[2]
    return sorted(r, key=lambda x: (x['pts'], x['gd'], x['gf'], x['agf'], mix(seed, 0x51A6E000 + x['club']) >> 1),
                  reverse=True)


def level(a, b):
    return all(a[k] == b[k] for k in ('pts', 'gd', 'gf', 'agf'))


def stage(seed, sc):
    """sc {md 1..3: (hg, ag)} -> (matches [(md 0.., home, away, hg, ag)], rows)"""
    h, a, _ = md1(seed)
    m2, m3 = later(seed, *sc[1])
    ms = [(0, h, a, *sc[1]), (1, *m2, *sc[2]), (2, *m3, *sc[3])]
    return ms, table([x[1:] for x in ms], seed)


def seed_for(home, away):
    """the smallest seed >= 1 whose md1 is home v away"""
    return next(s for s in range(1, 100000) if md1(s)[:2] == (home, away))


def ml_decode(b):
    """struct fp_ml (56 B) -> dict; m: [(md, home, away, played, hg, ag)] x 6"""
    i, st, n, have, seed = struct.unpack_from('<BBBBI', b, 0)
    winner, season, flags = struct.unpack_from('<HBB', b, 52)
    return dict(id=i, state=st, n=n, have=have, seed=seed, club=struct.unpack_from('<4H', b, 8),
                m=[tuple(b[16 + 6 * k:22 + 6 * k]) for k in range(6)], winner=winner, season=season, flags=flags,
                raw=bytes(b[:ML_SIZE]))


# ---------------------------------------------------------------- host: the engine's rules

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include "swosrules.h"
#include "fpml.h"
static const uint8_t TB[] = { SR_TB_POINTS, SR_TB_GOAL_DIFFERENCE, SR_TB_GOALS_FOR, SR_TB_AWAY_GOALS_FOR, SR_TB_DRAW_LOTS, 0 };
#define WR SR_SCHED_WINNER_RESTS
int main(void) {
    char ln[512];
    while (fgets(ln, sizeof ln, stdin)) {
        char *p = ln + 1;
        long v[40]; int nv = 0;
        for (;;) { char *e; long x = strtol(p, &e, 0); if (e == p) break; v[nv++] = x; p = e; if (nv == 40) break; }
        uint32_t seed = nv ? (uint32_t)v[0] : 0;
        sr_match m[6];
        if (ln[0] == 'L')
            printf("%zu %zu %zu %zu %zu %zu %zu %zu %zu %d\n", sizeof(struct fp_ml), offsetof(struct fp_ml, seed), offsetof(struct fp_ml, club),
                   offsetof(struct fp_ml, m_raw), offsetof(struct fp_ml, winner), offsetof(struct fp_ml, flags), sizeof(sr_match),
                   sizeof(struct fp_mlrow), offsetof(struct fp_mlrow, ent), (int)WR);
        else if (ln[0] == 'S') {
            int r = sr_mini_sched(3, 1, WR, seed, m, 0, 3);
            printf("%d %d %d %d %d\n", r, m[0].md, m[0].home, m[0].away, m[0].played);
        } else if (ln[0] == 'N') {
            sr_mini_sched(3, 1, WR, seed, m, 0, 3);
            m[0].played = 1; m[0].hg = (uint8_t)v[1]; m[0].ag = (uint8_t)v[2];
            int r = sr_mini_sched(3, 1, WR, seed, m, 1, 3);
            int r3 = sr_mini_sched(3, 1, WR, seed, m, 3, 3);     /* (a load: the held list checked) */
            printf("%d %d %d %d %d %d %d %d %d %d\n", r, r3, m[1].md, m[1].home, m[1].away, m[1].played, m[2].md, m[2].home, m[2].away, m[2].played);
        } else if (ln[0] == 'T') {
            int nm = (int)v[1];
            for (int k = 0; k < nm; k++) { m[k].md = (uint8_t)k; m[k].home = (uint8_t)v[2 + 4 * k]; m[k].away = (uint8_t)v[3 + 4 * k];
                                           m[k].played = 1; m[k].hg = (uint8_t)v[4 + 4 * k]; m[k].ag = (uint8_t)v[5 + 4 * k]; }
            sr_srow t[3];
            int r = sr_rr_table(3, m, nm, 3, 1, 0, TB, seed, t);
            printf("%d", r);
            for (int k = 0; k < 3; k++) printf(" %d %d %d %d %d", t[k].club, t[k].pts, (int)t[k].gf - (int)t[k].ga, t[k].gf, t[k].agf);
            printf("\n");
        } else if (ln[0] == 'K') {      /* refusals: md1's sides swapped in a held list (a corrupt save), have 2, n 4, legs 2 */
            sr_mini_sched(3, 1, WR, seed, m, 0, 3);
            uint8_t x = m[0].home; m[0].home = m[0].away; m[0].away = x; m[0].played = 1; m[0].hg = 1; m[0].ag = 0;
            int a = sr_mini_sched(3, 1, WR, seed, m, 1, 3);
            sr_mini_sched(3, 1, WR, seed, m, 0, 3);
            int b = sr_mini_sched(3, 1, WR, seed, m, 2, 3);
            int c = sr_mini_sched(4, 1, WR, seed, m, 0, 6), d = sr_mini_sched(3, 2, WR, seed, m, 0, 6);
            sr_mini_sched(3, 1, WR, seed, m, 0, 3); m[0].played = 1; m[0].hg = 2; m[0].ag = 0;
            sr_mini_sched(3, 1, WR, seed, m, 1, 3);
            m[1].home = m[1].away;                              /* (md2 changed in a held list of 3) */
            int e = sr_mini_sched(3, 1, WR, seed, m, 3, 3);
            printf("%d %d %d %d %d\n", a, b, c, d, e);
        }
    }
    return 0;
}
'''
_BIN = {}


def engine_rules():
    """(dir, vendored) of the engine's rules with sr_mini_sched: tools/swce once minilg is vendored, else FPML_ENGINE
    (a rules dir), else the engine checkout / the minilg worktree; None = none found"""
    import glob
    cands = [(os.path.join(HERE, 'swce'), True)]
    if os.environ.get('FPML_ENGINE'):
        cands.append((os.environ['FPML_ENGINE'], False))
    cands.append((os.path.expanduser('~/swos-competition-engine/rules'), False))
    cands += [(d, False) for d in sorted(glob.glob('/private/tmp/claude-501/*/*/scratchpad/emini/rules'))]
    for d, v in cands:
        s, h = os.path.join(d, 'sr_stage.c'), os.path.join(d, 'swosrules.h')
        if os.path.exists(s) and os.path.exists(h) and 'sr_mini_sched' in open(s).read() and \
                'SR_SCHED_WINNER_RESTS' in open(h).read():
            return d, v
    return None


def host(cmds):
    """the driver's answers to cmds (one line each): (lines, where) or (None, why)"""
    import subprocess
    import tempfile
    er = engine_rules()
    if not er:
        return None, 'SKIP: no engine rules with sr_mini_sched (tools/swce not on minilg yet; FPML_ENGINE=<rules dir>)'
    d = er[0]
    if d not in _BIN:
        td = tempfile.mkdtemp(prefix='fpml_host')
        open(os.path.join(td, 't.c'), 'w').write(DRIVER)
        r = subprocess.run(['cc', '-std=c99', '-O1', '-w', f'-I{d}', f'-I{HERE}', '-o', os.path.join(td, 't'),
                            os.path.join(td, 't.c'), os.path.join(d, 'sr_stage.c')], capture_output=True, text=True)
        if r.returncode:
            return None, f'cc: {r.stderr[:400]}'
        _BIN[d] = os.path.join(td, 't')
    r = subprocess.run([_BIN[d]], input='\n'.join(cmds) + '\n', capture_output=True, text=True)
    out = [[int(x) for x in ln.split()] for ln in r.stdout.splitlines()]
    if len(out) != len(cmds):
        return None, f'driver: {len(out)} answers to {len(cmds)} commands ({r.stderr[:200]})'
    return out, f'engine rules {d}' + (' (vendored)' if er[1] else ' (NOT vendored yet: tools/swce has no sr_mini_sched)')


def host_sched():
    """every md1 draw (6) x md1 score 0..3 x 0..3: the engine's md1, md2, md3 = the model's; every pair once, every
    club rests once and hosts once; a held list of 3 accepted (the load path); the refusals"""
    seeds = {}
    for s in range(1, 4000):
        seeds.setdefault(md1(s)[:2], s)
    errs = []
    if len(seeds) != 6:
        return False, f'model: {len(seeds)} of the 6 md1 draws reached'
    cmds, keys = [], []
    for s in list(range(0, 300)) + [0xFFFFFFFF, 0x80000000, 0x12345678]:
        cmds.append(f'S {s}')
        keys.append(('S', s))
    for s in seeds.values():
        for hg in range(4):
            for ag in range(4):
                cmds.append(f'N {s} {hg} {ag}')
                keys.append(('N', s, hg, ag))
        cmds.append(f'K {s}')
        keys.append(('K', s))
    out, where = host(cmds)
    if out is None:
        return where.startswith('SKIP'), where
    n = 0
    for k, o in zip(keys, out):
        n += 1
        if k[0] == 'S':
            h, a, _ = md1(k[1])
            if o != [1, 0, h, a, 0]:
                errs.append(f'md1 seed {k[1]}: engine {o}, model 1 0 {h} {a} 0')
        elif k[0] == 'N':
            _, s, hg, ag = k
            h, a, rest = md1(s)
            m2, m3 = later(s, hg, ag)
            if o != [3, 3, 1, m2[0], m2[1], 0, 2, m3[0], m3[1], 0]:
                errs.append(f'seed {s} md1 {h}v{a} {hg}-{ag}: engine {o}, model md2 {m2} md3 {m3}')
            pairs = {frozenset((h, a)), frozenset(m2), frozenset(m3)}
            rests = {rest, 3 - sum(m2), 3 - sum(m3)}
            if len(pairs) != 3 or rests != {0, 1, 2} or {h, m2[0], m3[0]} != {0, 1, 2}:
                errs.append(f'seed {s} {hg}-{ag}: pairs {pairs} rests {rests} hosts {h, m2[0], m3[0]}')
            r2 = h if hg > ag else a                    # (spec row 3, said again without later())
            if 3 - sum(m2) != r2:
                errs.append(f'seed {s} {hg}-{ag}: md2 rests {3 - sum(m2)}, the spec says {r2}')
        elif o != [-1, -1, -1, -1, -1]:
            errs.append(f'refusals seed {k[1]}: {o} (md1 swapped, have 2, n 4, legs 2, md2 changed: all -1)')
    return not errs, '; '.join(errs[:6]) or f'{n} checks (303 seeds, 6 draws x 16 md1 scores, refusals); {where}'


TIES = (    # (name, matches (home, away, hg, ag), the order by hand, the criterion) - clubs 0, 1, 2
    ('points first, not goal difference', ((1, 0, 1, 0), (0, 2, 5, 0), (2, 1, 0, 1)), (1, 0, 2), 'pts'),
    ('three level on points: goal difference', ((1, 0, 3, 0), (0, 2, 1, 0), (2, 1, 1, 0)), (1, 2, 0), 'gd'),
    ('three level on points and goal difference: goals for', ((0, 1, 2, 1), (1, 2, 3, 2), (2, 0, 1, 0)), (1, 2, 0), 'gf'),
    ('two level on points: goal difference', ((0, 1, 2, 0), (1, 2, 1, 1), (2, 0, 0, 1)), (0, 2, 1), None),
    ('two level on points, gd, gf: away goals for', ((0, 1, 2, 1), (1, 2, 0, 0), (2, 0, 1, 2)), (0, 1, 2), 'agf'),
    ('two level on points and gd: goals for', ((0, 1, 3, 0), (1, 2, 2, 2), (2, 0, 1, 4)), (0, 2, 1), None),
)


def host_tiebreak():
    """the three-club tie-break cases by hand (TIES: the order written out, not computed), on the engine and on the
    model; exhaustive: the 6 draws x 4^6 scores - engine table = model table (rows and order); the lots: three clubs
    level on everything - every one of the 6 orders reached over the seeds, the same order for one seed whatever the
    input; the chain's reach: with each club hosting once, three clubs level on points + goal difference + goals for
    are level on away goals too (away goals can only split TWO clubs)"""
    import itertools
    errs, cmds, keys = [], [], []
    for name, ms, order, _c in TIES:
        cmds.append('T 77 3 ' + ' '.join(' '.join(map(str, m)) for m in ms))
        keys.append(('H', name, ms, order))
    seeds = {}
    for s in range(1, 4000):
        seeds.setdefault(md1(s)[:2], s)
    for s in seeds.values():
        for sc in itertools.product(range(4), repeat=6):
            ms, _rows = stage(s, {1: sc[0:2], 2: sc[2:4], 3: sc[4:6]})
            cmds.append(f'T {s} 3 ' + ' '.join(' '.join(map(str, m[1:])) for m in ms))
            keys.append(('X', s, ms))
    for s in range(1, 400):
        cmds.append(f'T {s} 3 0 1 1 1 1 2 1 1 2 0 1 1')
        keys.append(('D', s))
    out, where = host(cmds)
    if out is None:
        return where.startswith('SKIP'), where
    lots, three_agf, nx = set(), 0, 0
    for k, o in zip(keys, out):
        got = [tuple(o[1 + 5 * i:6 + 5 * i]) for i in range(3)]
        order = tuple(g[0] for g in got)
        if k[0] == 'H':
            mod = tuple(r['club'] for r in table(k[2], 77))
            if o[0] != 3 or order != k[3] or mod != k[3]:
                errs.append(f'{k[1]}: engine {order}, model {mod}, by hand {k[3]}')
        elif k[0] == 'X':
            rows = table([m[1:] for m in k[2]], k[1])
            want = [(r['club'], r['pts'], r['gd'], r['gf'], r['agf']) for r in rows]
            nx += 1
            if o[0] != 3 or got != want:
                errs.append(f'seed {k[1]} {k[2]}: engine {got}, model {want}')
            if all(rows[0][f] == rows[2][f] for f in ('pts', 'gd', 'gf')) and len({r['agf'] for r in rows}) > 1:
                three_agf += 1
        else:
            lots.add(order)
            mod = tuple(r['club'] for r in table(((0, 1, 1, 1), (1, 2, 1, 1), (2, 0, 1, 1)), k[1]))
            if mod != order:
                errs.append(f'lots seed {k[1]}: engine {order}, model {mod}')
    if len(lots) != 6:
        errs.append(f'lots: {len(lots)} of the 6 orders reached over 399 seeds')
    if three_agf:
        errs.append(f'{three_agf} states with three clubs level on pts / gd / gf but not on away goals (expected none)')
    return not errs, '; '.join(errs[:6]) or f'{len(TIES)} cases by hand, {nx} exhaustive tables = the model, lots 6 orders; ' \
        f'three-way ties are never split by away goals (each club hosts once): lots follow goals for; {where}'


def host_iface():
    """tools/fpml.h against the engine's types, as the harness reads it: struct fp_ml 56 B (seed 4, club 8, m 16 = 6 x
    sr_match of 6 B, winner 52, flags 55), struct fp_mlrow 34 B (ent at 14), SR_SCHED_WINNER_RESTS 1; ml_decode's
    layout = the C layout"""
    out, where = host(['L'])
    if out is None:
        return where.startswith('SKIP'), where
    want = [ML_SIZE, 4, 8, 16, 52, 55, 6, 34, 14, 1]
    b = bytes(range(ML_SIZE))
    d = ml_decode(b)
    ok = out[0] == want and d['m'][1] == tuple(b[22:28]) and d['winner'] == b[52] | b[53] << 8 and d['flags'] == b[55]
    return ok, f'layout {out[0]} (want {want}); {where}'


def host_switches():
    """the test switches' plumbing: FPML_FORCE / FPML_SEED parsed (fpad.ml_force: md 1-based -> sr_match.md, the id
    default 1; bad entries refused), the flags (-DFP_MLF_INIT / -DFP_MLSEED_INIT; none without the switches: the
    release shape), both names in modver.TEST_VARS and BUILD_SWITCHES (buildrel clears them), a build with them is
    a test build"""
    sys.path.insert(0, HERE)
    import fpad
    import modver
    keep = {k: os.environ.get(k) for k in ('FPML_FORCE', 'FPML_SEED', 'FPORT')}
    errs = []
    try:
        for k in keep:
            os.environ.pop(k, None)
        T.check(fpad.ml_test_flags() == [], f'no switch: {fpad.ml_test_flags()} (want none)', errs)
        os.environ.update(FPORT='1', FPML_FORCE='1:2:0,2:5:0,2:3:0:1', FPML_SEED='0x2A')
        T.check(fpad.ml_force() == [(1, 0, 2, 0), (1, 1, 5, 0), (2, 2, 0, 1)], f'ml_force {fpad.ml_force()}', errs)
        T.check(fpad.ml_test_flags() == ['-DFP_MLF_INIT={{1,0,2,0},{1,1,5,0},{2,2,0,1}}', '-DFP_MLSEED_INIT=0x2au'],
                f'flags {fpad.ml_test_flags()}', errs)
        T.check(modver.is_test(), 'FPML_* set: not a test build', errs)
        os.environ.pop('FPML_FORCE')
        T.check(fpad.ml_test_flags() == ['-DFP_MLF_INIT={{0,0,0,0}}', '-DFP_MLSEED_INIT=0x2au'],
                f'seed only: {fpad.ml_test_flags()}', errs)
        for bad in ('1:2', '0:1:1', '7:1:1', '1:10:0', '1:1:0,1:2:2', ','.join(f'{i}:1:1:1' for i in range(1, 10))):
            os.environ['FPML_FORCE'] = bad
            try:
                fpad.ml_force()
                errs.append(f'FPML_FORCE={bad} accepted')
            except (AssertionError, ValueError):
                pass
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    for v in ('FPML_FORCE', 'FPML_SEED'):
        T.check(v in modver.TEST_VARS and v in modver.BUILD_SWITCHES, f'{v} not in modver TEST_VARS / BUILD_SWITCHES', errs)
    return not errs, '; '.join(errs) or 'FPML_FORCE / FPML_SEED: parsed, flags, modver lists'


def cup_units(country=8):
    """(first, last) week of the original cup struct of `country` (mkseason's 'national' cups take both: h[3], h[4])"""
    sys.path.insert(0, HERE)
    import fport
    fport.league_header_weeks(country)                  # (loads the original exe once: fport._HDR)
    p, comp = next(iter(fport._HDR.values()))
    gobj, gtab = p.target(2, comp + 4 * country)
    gd = p.le.obj_bytes(gobj)
    k = 8
    while struct.unpack_from('<i', gd, gtab + k - 4)[0] != -2:
        k += 4
    cobj, gcup = p.target(gobj, gtab + k)
    gc = p.le.obj_bytes(cobj)[gcup:gcup + 5]
    return gc[3], gc[4]


def host_cal():
    """the calendar slot, from the original exe and the pack (no DOSBox): Italy's league ends at unit 128 (header 56 ..
    32 + 96), so the row's units are 129, 130, 131; the Coppa Italia Serie C (pack competition 'league_cup', id 83,
    dates_from 8: a 'national' cup takes the original Italian cup struct's first / last weeks) lies in [96, 128]: its
    final's second leg at 128 = the league's last unit, nothing at 129..131"""
    sys.path.insert(0, HERE)
    import fport
    try:
        lf, ll = fport.league_header_weeks(8)
        cf, cl = cup_units(8)
    except (OSError, AssertionError) as e:
        return True, f'SKIP: the original exe is not readable ({e})'
    last = ll + 96 if ll < lf else ll
    cl2 = cl + 96 if cl < cf else cl
    days = fport.day_weeks(cf, cl, 7)                   # (3 single rounds + 2 two-leg rounds, IF spread as the league's)
    units = [last + o for o in OFF]
    ok = last == L_UNIT and cl2 <= L_UNIT and not set(range(cf, cl2 + 1)) & set(units)
    return ok, f'league {lf}..{last}; Coppa Italia Serie C (and Coppa Italia) {cf}..{cl2}, 7 match days if linear {days} ' \
        f'(final {days[-2]} / {days[-1]}); the stage {units}: ' + ('no clash' if ok else 'CLASH')


# ---------------------------------------------------------------- DOSBox: builds, reads

def data():
    return (os.environ.get('FPML_DATA') or os.environ.get('W2627REL_DATA') or
            os.path.join(T.MAIN, 'internal', 'world2526', 'world5tm-h3s7')).rstrip('/')


def has_row(src):
    p = os.path.join(src, 'ita', 'pack.json')
    return os.path.exists(p) and '"mini_leagues"' in open(p).read()


def producer():
    """the checkout has lane 1's producer (fp_ml_open defined in a C unit; fpml.h alone does not count)"""
    import glob
    return any('fp_ml_open(' in open(f, errors='replace').read() for f in glob.glob(os.path.join(HERE, '*.c')))


def gate(row=True):
    src = data()
    if not os.path.isdir(src):
        return f'SKIP: private data {src} missing'
    if not producer() and not os.environ.get('FPML_BUILD'):
        return 'SKIP: no mini-league producer in this checkout (no fp_ml_open in tools/*.c: lane 1 not merged)'
    if row and not has_row(src) and not os.environ.get('FPML_BUILD'):
        return f'SKIP: no mini_leagues row in {src}/ita/pack.json (FPML_DATA)'
    return None


def packs(src):
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    return ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])


def ml_exe(tag, place, seed=0, force=None, src=None):
    """an FPORT=1 build of data() with the career club forced to `place` of its group and the stage's switches"""
    env = {'SEASON_PACKS': packs(src or data()), 'FPORT': '1', 'GPLAY_FORCE': str(place), 'DPLAY_FORCE': str(100 + place)}
    if seed:
        env['FPML_SEED'] = f'{seed:#x}'
    if force:
        env['FPML_FORCE'] = ','.join(f'{md}:{hg}:{ag}' for md, (hg, ag) in sorted(force.items()))
    return os.environ.get('FPML_BUILD') or T.build('supc_' + tag, env=env)


def addrs(exe):
    """{name: (obj, offset) or None} from the build's ITALIAN.syms.json"""
    j = json.load(open(os.path.join(exe, 'ITALIAN.syms.json')))

    def find(name, mods):
        for m in mods:
            s = j.get(m, {}).get(name)
            if s:
                return s[0], s[1]
        return None
    return dict(ml=find('FP_ML', ('fpad', 'fpml', 'swe')), st=find('FP_ST', ('fpad',)), stk=find('FP_STKFREE', ('fpad',)),
                sp=find('SEASONPLAYING', ('gplay',)), mgr=find('GP_MGR', ('gplay',)), cal=(2, T.CAL_AT - 4))


def hkey(a):
    return f'{a[1]:x}' if a[0] == 2 else f'o{a[0]}/{a[1]:x}'


def hexspec(A):
    n = dict(ml=ML_SIZE * ML_N, st=ST_SIZE, stk=4, sp=1, mgr=2, cal=CAL_BYTES)
    return ','.join(f'{hkey(A[k])}:{n[k]}' for k in ('sp', 'mgr', 'cal', 'st', 'ml', 'stk') if A.get(k))


def vals(lines, a):
    p = f'HEX {hkey(a)} '
    return [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(p)]


def st_log(lines, a):
    """FP_ST's log entries in order over its successive states (fpgate.season_log, with the ML codes)"""
    out, last = [], []
    for b in vals(lines, a):
        magic, _s, _ld, _t, nlog = struct.unpack_from('<IBBBB', b, 0)
        if magic != MAGIC:
            continue
        e = []
        for i in range(min(nlog, 48)):
            c, u, rc, _x, mid, y = struct.unpack_from('<BBbBHH', b, 36 + 8 * i)
            e.append((FL.get(c, c), u, rc, mid, y))
        if len(e) < len(last) or e[:len(last)] != last:
            last = []
        out += e[len(last):]
        last = e
    return out


def observe(lines, A, inst=0):
    mls = [ml_decode(b[ML_SIZE * inst:]) for b in vals(lines, A['ml'])]
    mgr = [struct.unpack('<H', b)[0] for b in vals(lines, A['mgr'])] if A['mgr'] else []
    stk = [struct.unpack('<I', b)[0] for b in vals(lines, A['stk'])] if A['stk'] else []
    stk = [x for x in stk if x != M32]
    sp = [b[0] for b in vals(lines, A['sp'])] if A['sp'] else []
    log = st_log(lines, A['st']) if A['st'] else []
    cut = next((i for i, e in enumerate(log) if e[0] == 'SEASON' and i), None)      # (the next season's init: not this stage's)
    return dict(mls=mls, log=log[:cut], cals=[T.cal_entries(b) for b in vals(lines, A['cal'])],
                mgr=next((x for x in reversed(mgr) if x and x != 0xFFFF), None), stk=min(stk) if stk else None, sp=sp,
                record=[ln for ln in lines if ln.startswith('[record]')])


def season(exe, extra=None, runs_tag=1, team=None):
    """one sc_season with the stage's reads: (ok, msg, lines, A) - A None = the build has no FP_ML (SKIP)"""
    A = addrs(exe)
    if not A['ml'] or not A['st']:
        return True, 'SKIP: the build has no FP_ML / FP_ST label (no producer linked, or not an FPORT build)', [], None
    ok, msg, lines = T.sc_season(team or TEAM, dict(W8485_BUILD=exe, W8485_HEX=hexspec(A), W8485_RECSHOT='1',
                                                    **(extra or {})), runs_tag)
    return ok, msg, lines, A


def check_stage(o, errs, seed=None, force=None, me=None, played=None, fresh=True, late=True, noinst=True):
    """The stage of one season from a session's reads. Always: one instance, n 3, three distinct clubs, the seed and
    the clubs constant, have 1 or 3 only, a played score never changes, at the end state 2 / have 3 / all played, the
    schedule = the policy's for the held seed and md1 score (the model), the winner = the model's table's first, flags
    bit 0 (FP_MLDONE ran), the season byte = the season played, FL_MLOPEN / FL_MLDONE once, nothing REFUSED / ORPHAN.
    seed / force: the forced seed and scores held. me (an entrant career club's index): GP_MGR = club[me]; the matches
    with me (played: only these matchdays 0.., a run from a mid save) went through slot 4 - a LEG with the home side
    and the forced goals at unit 128 + off, a RES accepted, (fresh) an INST each, and the calendar never holds an
    entry after 128 but slot 4's at those units. me None: no INST, no calendar entry after 128 (late=False: not
    checked). Returns the final instance (None: none)."""
    mls = [m for m in o['mls'] if m['id']]
    if not mls:
        errs.append('no FP_ML instance in any state read (FP_ML stays zero: the stage never opened)')
        return None
    fin = mls[-1]
    T.check(len({m['seed'] for m in mls}) == 1 and len({m['club'] for m in mls}) == 1,
            f"the seed / the clubs changed during the stage: {sorted({(hex(m['seed']), m['club']) for m in mls})}", errs)
    cl = fin['club'][:3]
    T.check(fin['n'] == 3 and len(set(cl)) == 3 and 0 not in cl and 0xFFFF not in cl and all(c & 0xFF == cl[0] & 0xFF for c in cl),
            f"clubs {[hex(c) for c in fin['club']]} n {fin['n']} (three clubs of one league file)", errs)
    T.check(all(m['have'] in (1, 3) for m in mls), f"have {sorted({m['have'] for m in mls})} (1 or 3 only)", errs)
    for a, b in zip(mls, mls[1:]):
        for k in range(3):
            if a['m'][k][3] and a['m'][k] != b['m'][k]:
                errs.append(f"match {k} changed once played: {a['m'][k]} -> {b['m'][k]}")
    T.check(fin['state'] == 2 and fin['have'] == 3 and all(fin['m'][k][3] == 1 for k in range(3)),
            f"at the end state {fin['state']} have {fin['have']} matches {fin['m'][:3]} (want done, 3 played)", errs)
    if seed:
        T.check(fin['seed'] == seed, f"seed {fin['seed']:#x}, forced {seed:#x} (FPML_SEED)", errs)
    sc = {k + 1: fin['m'][k][4:6] for k in range(3)}
    ms, rows = stage(fin['seed'], sc)
    T.check([m[:3] for m in fin['m'][:3]] == [m[:3] for m in ms],
            f"schedule {[m[:3] for m in fin['m'][:3]]}, the policy's for seed {fin['seed']:#x} and md1 {sc[1]}: {[m[:3] for m in ms]}", errs)
    T.check(mls[0]['m'][0][:3] == ms[0][:3], f"md1 as first read {mls[0]['m'][0]} is not the draw {ms[0][:3]}", errs)
    if force:
        T.check(all(tuple(sc[md]) == tuple(force[md]) for md in force), f'scores {sc}, forced {force} (FPML_FORCE)', errs)
    top = [r['club'] for r in rows if level(r, rows[0])]
    T.check(fin['winner'] == cl[rows[0]['club']],
            f"winner {fin['winner']:#x}, the table's first is club {rows[0]['club']} = {cl[rows[0]['club']]:#x} "
            f"(rows {[(r['club'], r['pts'], r['gd'], r['gf'], r['agf']) for r in rows]}; level at the top {top})", errs)
    T.check(fin['flags'] & 1, f"flags {fin['flags']:#x}: bit 0 clear (FP_MLDONE did not run: no WINNERS / record line)", errs)
    T.check(not o['sp'] or fin['season'] in o['sp'], f"season byte {fin['season']}, seasons played {sorted(set(o['sp']))}", errs)
    log = o['log']
    codes = [e[0] for e in log]
    bad = [e for e in log if e[0] in ('REFUSED', 'ORPHAN')]
    T.check(not bad, f'refused / orphan {bad}', errs)
    T.check(codes.count('MLDONE') == 1 and (codes.count('MLOPEN') == 1 or not fresh),
            f"log: MLOPEN x{codes.count('MLOPEN')}, MLDONE x{codes.count('MLDONE')} (want 1 each) in {codes}", errs)
    lates = sorted({(e[0], e[1]) for c in o['cals'] for e in c if e[1] > L_UNIT})
    inst = [e for e in log if e[0] == 'INST']
    if me is None:
        T.check(not inst or not noinst, f'installs {inst} (the career club is not an entrant: everything simulated)', errs)
        if late:
            T.check(not lates, f'calendar entries after {L_UNIT}: {lates} (want none)', errs)
        return fin
    T.check(o['mgr'] == cl[me], f"the career club {o['mgr'] and hex(o['mgr'])} is not club[{me}] = {cl[me]:#x} "
            f'(entrants in FP_MLT.ent order; GPLAY_FORCE=1 must act before fp_ml_open)', errs)
    mine = [m for m in ms if me in m[1:3] and (played is None or m[0] in played)]
    units = [L_UNIT + OFF[m[0]] for m in mine]
    legs = [(e[1], e[3], e[4] & 255, e[4] >> 8) for e in log if e[0] == 'LEG']
    want = [(L_UNIT + OFF[m[0]], cl[m[1]], m[3], m[4]) for m in mine]
    T.check(legs == want, f'legs (unit, home, goals) {legs}, want {want} (FPML_FORCE on the career club\'s own match: '
            f'fp_leg)', errs)
    res = [e for e in log if e[0] == 'RES']
    T.check(len(res) == len(mine) and all(e[4] >> 4 & 15 == 0 for e in res), f'results {res} (want {len(mine)}, accepted)', errs)
    if fresh:
        T.check([e[4] & 255 for e in inst] == units and all(e[2] == 1 for e in inst), f'installs {inst}, want units {units}', errs)
        allm = [L_UNIT + OFF[m[0]] for m in ms if me in m[1:3]]
        T.check(set(lates) <= {(SLOT_PORT, u) for u in allm} and {u for _s, u in lates} == set(allm),
                f'calendar entries after {L_UNIT}: {lates}, want only slot {SLOT_PORT} at {allm}', errs)
        T.check(codes.count('MLADD') == len(allm) and codes.count('MLSIM') == 3 - len(allm),
                f"log: MLADD x{codes.count('MLADD')} (want {len(allm)}), MLSIM x{codes.count('MLSIM')} (want {3 - len(allm)})", errs)
    if o['stk'] is not None:
        need = int(os.environ.get('FPML_STK_CHAIN') or 300) + 512
        T.check(o['stk'] >= need, f"free game stack at fp_step {o['stk']} B < {need} (chain + 512)", errs)
    return fin


def end_save(runs_tag=1):
    return os.path.join(T.RUNS, T.w84_tag() + f'_{runs_tag}', 'SWOS', 'W84A.CAR' if runs_tag == 1 else 'W84B.CAR')


def check_pages(exe, car, tag, fin, o, errs, entrant):
    """lane 2's lines, on the next season's save: the WINNERS page's last-season block SUPERCOPPA SERIE C = the
    winner's name; the management record (logged '[record]' at the season end) names the Supercoppa iff the career
    club won it; the fixture list showed its name (an entrant)"""
    if fin is None:
        return
    if not os.path.exists(car):
        errs.append(f'no season-end save {car}')
        return
    with T.Session('supc_winners_' + tag, exe, {'W84A.CAR': car}, 'dump:2', 300) as s:
        s.wait()
        s.send(T.LOAD1 + ' dump:3')
        more = []
        _e, _title, lines = T.winners_page(s, more)
    blocks = {}
    for pg in [lines] + more:
        blocks.update(T.winner_blocks(pg))
    want = T.team_name(exe, fin['winner'])
    T.check(blocks.get(NAME) == want, f'WINNERS page: {NAME} = {blocks.get(NAME)!r}, want {want!r} ({blocks})', errs)
    mine = entrant and o['mgr'] == fin['winner']
    rec = any('SUPERCOPPA' in ln for ln in o['record'])
    T.check(bool(o['record']) and rec == bool(mine), f"management record: Supercoppa line {'present' if rec else 'absent'}, "
            f"the career club {'won' if mine else 'did not win'} it ({o['record'][-1:]})", errs)


def run_fresh(tag, place, seed, force, entrant=True, pages=True):
    """a new career's season on the stage's build: check_stage + check_pages"""
    skip = gate()
    if skip:
        return True, skip
    exe = ml_exe(tag, place, seed, force)
    ok, msg, lines, A = season(exe)
    if A is None:
        return True, msg
    o, errs = observe(lines, A), []
    T.check(ok, f'season: {msg[:300]}', errs)
    fin = check_stage(o, errs, seed, force, ME if entrant else None)
    if entrant:
        errs += T.sc_labels(lines, NAME)
    if pages:
        check_pages(exe, end_save(), tag, fin, o, errs, entrant)
    open(os.path.join(T.RUNS, f'supc_{tag}.txt'), 'w').write('\n'.join(map(str, o['log'] + o['mls'][-1:])) + '\n')
    return not errs, '; '.join(errs) or summary(fin, o) + f'; {msg[:60]}'


def summary(fin, o):
    if fin is None:
        return 'no stage'
    ms, rows = stage(fin['seed'], {k + 1: fin['m'][k][4:6] for k in range(3)})
    return f"seed {fin['seed']:#x}: " + ', '.join(f'md{m[0] + 1} {m[1]}v{m[2]} {m[3]}-{m[4]}' for m in ms) + \
        f"; table {[(r['club'], r['pts'], r['gd'], r['gf']) for r in rows]}; winner {fin['winner']:#x}" + \
        (f"; stack {o['stk']} B" if o['stk'] is not None else '')


# the shapes (clubs 0, 1, 2; ME = 1): the md1 draw, then the three forced scores
SHAPES = {
    # md1 CAMPOBASSO at home 1-0: it rests md2 (0 v 2, 5-0), md3 away 2 v 1 0-1: 6 points; club 0 has 3 points and the
    # better goal difference (+4 v +2): points rank first
    'home_win': ((1, 0), {1: (1, 0), 2: (5, 0), 3: (0, 1)}),
    # md1 away 0 v 1 1-1: the away side rests md2 (2 v 0, 2-0), md3 at home 1 v 2 0-0: club 2 wins (4, 2, 1 points)
    'draw': ((0, 1), {1: (1, 1), 2: (2, 0), 3: (0, 0)}),
    # md1 at home 1 v 2 0-2: the winner rests, md2 away 0 v 1 3-3, md3 2 v 0 0-1 without it: club 0 wins (4, 3, 1)
    'loss': ((1, 2), {1: (0, 2), 2: (3, 3), 3: (0, 1)}),
    # it rests md1 (0 v 2, 0-0: simulated at the league's end), md2 at home 1 v 0 2-1, md3 away 2 v 1 1-1: it wins (4, 2, 1)
    'rest': ((0, 2), {1: (0, 0), 2: (2, 1), 3: (1, 1)}),
    # three clubs on 3 points (1 beats 0, 0 beats 2, 2 beats 1): goal difference +2, 0, -2 -> 1, 2, 0
    'tie_gd': ((1, 0), {1: (3, 0), 2: (1, 0), 3: (1, 0)}),
    # three clubs on 3 points and goal difference 0: goals for 4, 3, 2 -> 1, 2, 0 (all simulated)
    'tie_gf': ((0, 1), {1: (2, 1), 2: (3, 2), 3: (1, 0)}),
    # three 1-1 draws: level on everything, the lots (from the seed) decide (all simulated)
    'tie_lots': ((0, 1), {1: (1, 1), 2: (1, 1), 3: (1, 1)}),
}


SHAPE_WANT = {   # (the matchdays 0.. the career club plays, the final order) - by hand, checked by fpml_host_shapes
    'home_win': ((0, 2), (1, 0, 2)), 'draw': ((0, 2), (2, 1, 0)), 'loss': ((0, 1), (0, 2, 1)), 'rest': ((1, 2), (1, 2, 0)),
    'tie_gd': ((0, 2), (1, 2, 0)), 'tie_gf': ((0, 1), (1, 2, 0)), 'tie_lots': ((0, 2), None)}


def host_shapes():
    """the DOSBox scenarios' shapes on the model: the md1 draw wanted, the matchdays the career club plays and the
    final order as written by hand (SHAPE_WANT); the lots' shape: three clubs level on everything"""
    errs = []
    for name, ((h, a), force) in SHAPES.items():
        seed = seed_for(h, a)
        ms, rows = stage(seed, force)
        mine = tuple(m[0] for m in ms if ME in m[1:3])
        order = tuple(r['club'] for r in rows)
        wm, wo = SHAPE_WANT[name]
        if md1(seed)[:2] != (h, a) or mine != wm or (wo is not None and order != wo) or \
                (wo is None and not (level(rows[0], rows[1]) and level(rows[1], rows[2]))):
            errs.append(f'{name}: seed {seed} {ms} mine {mine} order {order}, want {wm} {wo}')
    return not errs, '; '.join(errs) or f'{len(SHAPES)} shapes: ' + ', '.join(f'{k} seed {seed_for(*v[0])}' for k, v in SHAPES.items())


def shape(name):
    (h, a), force = SHAPES[name]
    return seed_for(h, a), force


def mid_save(exe, tag, off, val):
    """a career save on the stage's build once FP_ML's byte at off holds val (W8485_MIDSAVE with an o4/ address),
    cached by build: (car, the instance's bytes at the save) or (None, error)"""
    import re
    import shutil
    keep = os.path.join(T.RUNS, f'supc_mid_{tag}-' + os.path.basename(exe.rstrip('/')) + '.CAR')
    if os.path.exists(keep) and os.path.exists(keep + '.ml'):
        return keep, open(keep + '.ml', 'rb').read()
    A = addrs(exe)
    ok, msg, lines, A = season(exe, dict(W8485_MIDSAVE=f'{hkey((A["ml"][0], A["ml"][1] + off))}:{val}:1'))
    m = re.search(r'saved mid-season: (\S+\.CAR)', msg)
    if not (ok and m):
        return None, f'no mid-stage save: {msg[:300]}'
    live = [b for b in vals(lines, A['ml']) if b[0]]
    if not live:
        return None, 'the mid-stage save was made with no FP_ML instance read'
    shutil.copy(m.group(1), keep + '.tmp')
    open(keep + '.ml', 'wb').write(live[-1][:ML_SIZE])
    os.replace(keep + '.tmp', keep)
    return keep, live[-1][:ML_SIZE]


def fp_item(d):
    """the FP item's offset in a .CAR's bytes (its data, after the id / size words), or -1"""
    sys.path.insert(0, HERE)
    import engine
    import fpad
    k = d.find(struct.pack('<HH', engine.item_id('FP'), fpad.SAVE_SIZE))
    return k + 4 if k >= 0 else -1


def car_ml(car):
    """(tag, version, count, [instance bytes] x ML_N) of a .CAR's ML block, or None (no FP item)"""
    d = open(car, 'rb').read()
    b = fp_item(d)
    if b < 0:
        return None
    tag, ver, cnt = struct.unpack_from('<HBB', d, b + ML_AT)
    return tag, ver, cnt, [d[b + ML_AT + 8 + ML_SIZE * i:b + ML_AT + 8 + ML_SIZE * (i + 1)] for i in range(ML_N)]


def run_save(tag, name, off, val, after, what):
    """shape `name`, saved mid-stage (FP_ML byte off == val: `what`), the save loaded and played to the season end:
    the .CAR's ML block ('ML', version 1, the instance = the live one at the save); after the load the first instance
    read = the saved one (nothing redrawn), the matchdays in `after` played through slot 4, the end = the model's"""
    skip = gate()
    if skip:
        return True, skip
    seed, force = shape(name)
    exe = ml_exe(name, 1, seed, force)
    if not addrs(exe)['ml']:
        return True, 'SKIP: the build has no FP_ML label (no producer linked)'
    car, live = mid_save(exe, tag, off, val)
    if not car:
        return False, live
    errs = []
    blk = car_ml(car)
    T.check(blk is not None and blk[0] == 0x4C4D and blk[1] == 1 and blk[2] >= 1 and blk[3][0] == live,
            f"the save's ML block {blk and (hex(blk[0]), blk[1], blk[2], blk[3][0].hex())}, live at the save {live.hex()} "
            f'({what})', errs)
    sv = ml_decode(live)
    T.check(sv['state'] == 1 and [m[3] for m in sv['m'][:3]] == [int(k not in after) for k in range(3)],
            f"the save is not {what}: state {sv['state']} matches {sv['m'][:3]}", errs)
    ok, msg, lines, A = season(exe, dict(W8485_FROM=car), 2)
    o = observe(lines, A)
    T.check(ok, f'from the save: {msg[:300]}', errs)
    first = next((m for m in o['mls'] if m['id']), None)
    T.check(first is not None and first['raw'] == live, f"after the load FP_ML {first and first['raw'].hex()}, saved {live.hex()}", errs)
    mine = [k for k in after if ME in stage(seed, force)[0][k][1:3]]
    fin = check_stage(o, errs, seed, force, ME, played=mine, fresh=False)
    check_pages(exe, end_save(2), tag, fin, o, errs, True)
    codes = [e[0] for e in o['log']]
    T.check(codes[:2] == ['LOAD', 'PLOAD'] and 'MLOPEN' not in codes, f'after the load {codes[:8]} (LOAD, PLOAD; no second MLOPEN)', errs)
    return not errs, '; '.join(errs) or f'{what}: ' + summary(fin, o) + f'; {msg[:60]}'


def run_old(variants):
    """world_supc_save12's mid save (shape loss: md1 played, CAMPOBASSO's md2 pending) with its ML state gone, loaded and
    played to the season end - zero: the ML block zeroed (an FP item of save version 1 read as v2: tag 0 = no
    instance); noitem: no FP item (its header cleared: a save from before the port); corrupt: md1's home side changed in
    the held list (sr_mini_sched -1: the block refused, the port's own section kept). Each: no crash, the season ends,
    the whole edition simulated at the season end (T2: state 2, 3 matches, the forced seed and scores -> the same
    table and winner as the full run), FP_MLDONE once, the WINNERS line; noitem: PLOAD rc 0"""
    skip = gate()
    if skip:
        return True, skip
    seed, force = shape('loss')
    exe = ml_exe('loss', 1, seed, force)
    if not addrs(exe)['ml']:
        return True, 'SKIP: the build has no FP_ML label (no producer linked)'
    car, live = mid_save(exe, 'save12', 3, 3)
    if not car:
        return False, live
    errs, info = [], []
    for how in variants:
        d = bytearray(open(car, 'rb').read())
        b = fp_item(d)
        if b < 0:
            return False, 'no FP item in the mid save'
        if how == 'zero':
            d[b + ML_AT:b + ML_AT + 8 + ML_SIZE * ML_N] = bytes(8 + ML_SIZE * ML_N)
        elif how == 'noitem':
            d[b:b + 4] = bytes(4)
        else:
            d[b + ML_AT + 8 + 16 + 1] ^= 3              # (m[0].home: another club)
        c2 = os.path.join(T.RUNS, f'supc_old_{how}.CAR')
        open(c2, 'wb').write(d)
        ok, msg, lines, A = season(exe, dict(W8485_FROM=c2), 2)
        o, e2 = observe(lines, A), []
        T.check(ok, f'season: {msg[:200]}', e2)
        o['log'] = [e for e in o['log'] if e[0] not in ('ORPHAN', 'REFUSED')]   # (the K_PORT tie left in slot 4 / a
        fin = check_stage(o, e2, seed, force, None, fresh=False, late=False, noinst=False)   # result without its stage: by design)
        pl = [e for e in o['log'] if e[0] == 'PLOAD']
        if how == 'noitem':
            T.check(len(pl) == 1 and pl[0][2] == 0, f'PLOAD {pl} (want rc 0: no item)', e2)
        if fin is not None and how == variants[-1]:
            check_pages(exe, end_save(2), 'old_' + how, fin, o, e2, False)
        errs += [f'{how}: {x}' for x in e2]
        info.append(f'{how}: {summary(fin, o)}')
    return not errs, '; '.join(errs) or '; '.join(info)


def run_c20():
    """career_20seasons (C20_SEASONS, default 2: a save + reload every season) at CAMPOBASSO on shape home_win's build:
    season 1 the club wins group B and plays the stage (check_stage, entrant), season 2 it is in Serie B (forced 1st
    there): the whole stage simulated at the season end (check_stage, not an entrant) with a new season byte; every
    season's save holds the ML block with the finished instance of that season"""
    skip = gate()
    if skip:
        return True, skip
    seed, force = shape('home_win')
    exe = ml_exe('home_win', 1, seed, force)
    A = addrs(exe)
    if not A['ml']:
        return True, 'SKIP: the build has no FP_ML label (no producer linked)'
    n = int(os.environ.get('C20_SEASONS') or 2)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'C20_TEAM', 'C20_SEASONS', 'W8485_HEX')}
    os.environ.update(W8485_BUILD=exe, C20_TEAM=TEAM, C20_SEASONS=str(n), W8485_HEX=hexspec(A))
    try:
        ok, msg = T.career_20seasons()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    errs, info, seasons = [], [], set()
    T.check(ok, f'career_20seasons: {msg[:300]}', errs)
    for s in range(1, n + 1):
        car = os.path.join(T.RUNS, f'c20_after_s{s:02d}.CAR')
        blk = car_ml(car) if os.path.exists(car) else None
        if not blk or blk[0] != 0x4C4D or blk[1] != 1 or not blk[3][0][0]:
            errs.append(f'season {s}: the save\'s ML block {blk and (hex(blk[0]), blk[1], blk[2])} (want ML, 1, an instance)')
            continue
        sv = ml_decode(blk[3][0])
        T.check(sv['state'] == 2 and sv['have'] == 3 and sv['flags'] & 1 and sv['seed'] == seed,
                f"season {s}: saved instance state {sv['state']} have {sv['have']} flags {sv['flags']} seed {sv['seed']:#x}", errs)
        seasons.add(sv['season'])
        if s in (1, n):                                 # (the run dirs kept: season 1's, the last one's)
            p = os.path.join(T.RUNS, T.w84_tag() + ('_1' if s == 1 else '_2'), 'session.log')
            lines = open(p, errors='replace').read().splitlines() if os.path.exists(p) else []
            o, e2 = observe(lines, A), []
            if s > 1:                                   # (the loaded season: last season's instance first, then this one's)
                o['mls'] = [m for m in o['mls'] if m['season'] == sv['season']]
            fin = check_stage(o, e2, seed, force, ME if s == 1 else None, fresh=s == 1, late=False)
            T.check(fin is not None and fin['raw'] == sv['raw'], f'the save\'s instance is not the season\'s last one', e2)
            errs += [f'season {s}: {x}' for x in e2]
            info.append(f'season {s}: {summary(fin, o)}')
    T.check(len(seasons) == n, f'season bytes {sorted(seasons)} over {n} seasons (one instance per season)', errs)
    return not errs, '; '.join(errs) or '; '.join(info) + f'; {msg[:80]}'


def run_sim():
    """the release shape (no FPML switch: the seed from the game, fp_ml_sim's own scores): CAMPOBASSO forced 12th of
    group B - no fixture installed, no calendar entry after 128; at the season end the stage is done: 3 matches,
    the schedule the policy's for the seed drawn, the winner the model's for the scores drawn, FP_MLDONE, WINNERS"""
    skip = gate()
    if skip:
        return True, skip
    exe = ml_exe('sim', 12)
    ok, msg, lines, A = season(exe)
    if A is None:
        return True, msg
    o, errs = observe(lines, A), []
    T.check(ok, f'season: {msg[:300]}', errs)
    fin = check_stage(o, errs, None, None, None)
    T.check(fin is None or (fin['seed'] != 0 and all(m[4] <= 9 and m[5] <= 9 for m in fin['m'][:3])),
            f"seed {fin and fin['seed']} / scores {fin and fin['m'][:3]}", errs)
    T.check(o['stk'] is None, 'FP_STKFREE in a build without test switches (not the release shape)', errs)
    check_pages(exe, end_save(), 'sim', fin, o, errs, False)
    return not errs, '; '.join(errs) or summary(fin, o) + f'; {msg[:60]}'


def run_off():
    """the structural OFF (builds only, no DOSBox): this checkout built on a copy of the data WITHOUT the mini_leagues
    row = the reference commit (FPML_OFF_REF, default 42-int) on the same copy - ITALIAN.EXE and every DATA file
    byte-identical, without the port and with it (FPORT=1 FPORT_TEST=<fpgate's schedule A>)"""
    import filecmp
    import shutil
    src = data()
    if not os.path.isdir(src):
        return True, f'SKIP: private data {src} missing'
    off = src
    if has_row(src):                                    # (a copy without the row: ita/pack.json rewritten, the rest linked)
        off = os.path.join(T.WORK, 'data', 'supc_off-' + os.path.basename(src))
        if not os.path.isdir(off):
            tmp = f'{off}.tmp{os.getpid()}'
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp)
            for x in os.listdir(src):
                if x != 'ita':
                    os.symlink(os.path.join(src, x), os.path.join(tmp, x))
            shutil.copytree(os.path.join(src, 'ita'), os.path.join(tmp, 'ita'))
            pk = json.load(open(os.path.join(tmp, 'ita', 'pack.json')))
            n = sum(1 for c in pk['competitions'] if c.pop('mini_leagues', None) is not None) + (pk.pop('mini_leagues', None) is not None)
            assert n == 1, ('supc_off: mini_leagues keys removed', n)
            json.dump(pk, open(os.path.join(tmp, 'ita', 'pack.json'), 'w'), ensure_ascii=False, indent=1)
            shutil.copy(src + '.txt', tmp + '.txt')
            os.replace(tmp + '.txt', off + '.txt')
            os.rename(tmp, off)
    ref = os.environ.get('FPML_OFF_REF') or '42-int'
    sys.path.insert(0, HERE)
    import fpgate
    errs, info = [], []
    for tag, extra in (('plain', {}), ('fport', {'FPORT': '1', 'FPORT_TEST': fpgate.SCHED_A})):
        env = dict({'SEASON_PACKS': packs(off)}, **extra)
        a, b = T.build('supc_off_' + tag, env=env), T.build('supc_offref_' + tag, env=env, branch=ref)
        files = ['ITALIAN.EXE'] + sorted(os.path.join('DATA', x) for x in os.listdir(os.path.join(b, 'DATA')))
        diff = [f for f in files if not os.path.exists(os.path.join(a, f)) or
                not filecmp.cmp(os.path.join(a, f), os.path.join(b, f), shallow=False)]
        extra_f = sorted(set(os.listdir(os.path.join(a, 'DATA'))) - set(os.listdir(os.path.join(b, 'DATA'))))
        T.check(not diff and not extra_f, f'{tag}: differs from {ref} in {diff[:6]}, new files {extra_f[:6]}', errs)
        info.append(f'{tag}: {len(files)} files identical to {ref}')
    return not errs, '; '.join(errs) or '; '.join(info) + ('' if has_row(src) else f' (the data {os.path.basename(src)} has no row yet)')


def register(mod):
    global T
    T = mod
    sc = mod.scenario

    @sc
    def fpml_host_sched():
        """Supercoppa Serie C, host: the engine's sr_mini_sched (WINNER_RESTS) = the model on 303 seeds' md1 and on the 6
        draws x 16 md1 scores (md2 / md3, every pair once, every club rests and hosts once, the load path's held list
        of 3 accepted); a corrupt held list, have 2, n 4, legs 2 refused"""
        return host_sched()

    @sc
    def fpml_host_tiebreak():
        """Supercoppa Serie C, host: sr_rr_table (3 / 1 / 0; points, goal difference, goals for, away goals for, lots)
        on the tie-break cases written by hand (points before goal difference; three clubs level decided by goal
        difference, by goals for; two clubs by away goals), = the model on the 6 draws x 4^6 scores, the lots' 6
        orders; three-way ties are never split by away goals"""
        return host_tiebreak()

    @sc
    def fpml_host_iface():
        """Supercoppa Serie C, host: tools/fpml.h compiled with the engine's header - struct fp_ml 56 B and its
        offsets as the harness (and the FP item's ML block) read them, struct fp_mlrow 34 B"""
        return host_iface()

    @sc
    def fpml_host_switches():
        """Supercoppa Serie C, host: FPML_FORCE / FPML_SEED - parsing, the compile flags (none without the switches),
        modver's TEST_VARS / BUILD_SWITCHES"""
        return host_switches()

    @sc
    def fpml_host_shapes():
        """Supercoppa Serie C, host: the world_supc_* scenarios' forced shapes on the model - the md1 draw, the career
        club's matchdays, the final order as written by hand"""
        return host_shapes()

    @sc
    def fpml_host_cal():
        """Supercoppa Serie C, host: the stage's units 129..131 against the league's last unit (128) and the Coppa
        Italia Serie C's dates (the original Italian cup struct: 96..128) - no clash"""
        return host_cal()

    @sc
    def world_supc_home_win():
        """Supercoppa Serie C: CAMPOBASSO wins group B (forced), md1 at home won 1-0, rests md2 (simulated 5-0), md3
        away won: slot-4 ties at 129 and 131 only, the table by points before goal difference, the winner, the
        WINNERS line and the management record's line (the career club won), the fixture list's name"""
        return run_fresh('home_win', 1, *shape('home_win'))

    @sc
    def world_supc_draw():
        """Supercoppa Serie C: md1 away drawn 1-1 - the away side (CAMPOBASSO) rests md2, plays md3 at home; another
        club wins: the WINNERS line names it, no record line"""
        return run_fresh('draw', 1, *shape('draw'))

    @sc
    def world_supc_loss():
        """Supercoppa Serie C: md1 at home lost 0-2 - the winner rests, CAMPOBASSO plays md2 away (129, 130), md3
        simulated without it"""
        return run_fresh('loss', 1, *shape('loss'))

    @sc
    def world_supc_rest():
        """Supercoppa Serie C: CAMPOBASSO rests md1 (simulated at the league's end: no calendar entry at 129), plays
        md2 at home and md3 away (130, 131), wins"""
        return run_fresh('rest', 1, *shape('rest'))

    @sc
    def world_supc_tie_gd():
        """Supercoppa Serie C: three clubs on 3 points, goal difference decides (the career club plays md1 and md3)"""
        return run_fresh('tie_gd', 1, *shape('tie_gd'))

    @sc
    def world_supc_tie_gf():
        """Supercoppa Serie C: three clubs level on points and goal difference, goals for decide - CAMPOBASSO 12th
        (not an entrant): the three matches simulated at the season end with the forced scores, no slot-4 tie"""
        return run_fresh('tie_gf', 12, *shape('tie_gf'), entrant=False)

    @sc
    def world_supc_tie_lots():
        """Supercoppa Serie C: three 1-1 draws, level on everything - the lots from the seed give the winner (the
        model's), not an entrant career club"""
        return run_fresh('tie_lots', 12, *shape('tie_lots'), entrant=False)

    @sc
    def world_supc_sim():
        """Supercoppa Serie C, the release shape: no test switch but the place (12th) - the stage simulated at the
        season end with the game's seed and fp_ml_sim's scores, consistent with the policy and the table rules"""
        return run_sim()

    @sc
    def world_supc_save12():
        """Supercoppa Serie C: a save between md1 and md2 (shape loss: md1 played, md2 + md3 scheduled, CAMPOBASSO's
        md2 pending), loaded: nothing redrawn, md2 played through slot 4, md3 simulated, the end as the full run"""
        return run_save('save12', 'loss', 3, 3, (1, 2), 'between md1 and md2')

    @sc
    def world_supc_save23():
        """Supercoppa Serie C: a save between md2 and md3 (shape rest: md2 played, CAMPOBASSO's md3 pending), loaded:
        md3 played through slot 4, the end as the full run"""
        return run_save('save23', 'rest', 16 + 6 + 3, 1, (2,), 'between md2 and md3')

    @sc
    def world_supc_oldsave():
        """Supercoppa Serie C: a save from after the league's end without the stage's state (the ML block zeroed = an FP
        item of save version 1; no FP item at all; a corrupt held list) loaded: the season ends, the whole edition
        simulated at the season end, WINNERS"""
        return run_old(('zero', 'noitem', 'corrupt'))

    @sc
    def world_supc_c20():
        """Supercoppa Serie C: career_20seasons C20_SEASONS=2 at CAMPOBASSO - season 1 an entrant (plays), season 2 in
        Serie B (simulated), a save + reload each, the saves' ML blocks"""
        return run_c20()

    @sc
    def world_supc_off():
        """Supercoppa Serie C, the structural OFF (builds only): no mini_leagues row = the reference commit's exe and
        data, byte for byte, with and without the port"""
        return run_off()


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import swostest
    register(swostest)
    sys.exit(swostest.main(sys.argv[1:]))
