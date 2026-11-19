"""4.2 the fixture port's mini-league PRODUCER (tools/fpml.c, lane 1 of the Supercoppa Serie C) on the host: fpml.c
compiled natively with the vendored engine's sr_stage.c inside it, against stubs of fpad.c's side (fp_log, fp_wake,
fp_ml_add: the port's queue as a list) and a test GP_IN. No exe, no DOSBox. The oracle is lane 3's model
(tools/fpmlgate.py: md1 / later / table).

test_fpml_stage: every md1 draw x the career club as each entrant / not an entrant x a set of scores (wins, draws,
                 the three-way ties): the schedule, who plays through the port (one fixture at a time, at L + off, the
                 next one only after the result), who is simulated, the winner, state / have / flags, the log counts;
                 a refused fixture is simulated; a second open is a no-op; another country's season end opens nothing.
test_fpml_load:  fp_ml_loaded keeps a sound instance (open and done) and drops a corrupt one (md1 swapped, a club
                 doubled, a bad row id), leaving the other instance alone.
test_fpml_row:   fpad.ml_table(): the Italian row's bytes (struct fp_mlrow, 34 B) and its refusals."""
import itertools
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)

ROW = {'key': 'supercoppa_c', 'names': {'*': ['SUPERCOPPA SERIE C', 'SUPERCOPPA C']},
       'entrants': [[2, 1], [3, 1], [4, 1]], 'schedule': 'winner_rests', 'legs': 1, 'points': [3, 1, 0],
       'tiebreak': ['goal_difference', 'goals_for', 'away_goals_for', 'draw_lots'], 'units': [1, 2, 3],
       'record': {'*': ['SUPERCOPPA SERIE C']}}
ROWB = struct.pack('<4B3BB6s8B6B6B', 1, 3, 1, 1, 3, 1, 0, 5, bytes((1, 2, 3, 7, 16, 0)), 2, 1, 3, 1, 4, 1, 0, 0,
                   1, 2, 3, 0, 0, 0, 0, 0, 1, 0, 0, 0)

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define FP_DATA
#define FPORT_TEST
#define GP_GIN_HOST
static unsigned char GP_GIN[O_INT + C_GD * C_GT * C_ROW + 16];
#define IN GP_GIN
#include "fpml.c"
u8 FP_ML[FP_ML_SZ]; struct fp_st FP_ST; const u8 FP_SEASON = 30, FP_CWB = 5, GP_SEAS = 30; u16 GP_MGR;
u8 FP_MLF[8][4]; u32 FP_MLSEED;
static int nlog[32], refuse, wake = 1, nadd;
static struct { u32 id; u16 home, away; u32 off; } Q[8];
void fp_log(u32 code, i32 rc, u32 id, u32 y) { (void)rc; (void)id; (void)y; nlog[code & 31]++; }
u32 fp_wake(void) { return (u32)wake; }
i32 fp_ml_add(u32 match_id, u16 home, u16 away, u32 off)
{
    for (int i = 0; i < nadd; i++) if (Q[i].id == match_id) return 0;
    nlog[FL_MLADD]++;
    if (refuse) return -16;
    Q[nadd].id = match_id; Q[nadd].home = home; Q[nadd].away = away; Q[nadd].off = off; nadd++;
    return 0;
}
static void ndone(const struct fp_ml *ml) { ((struct fp_ml *)ml)->flags |= 1; nlog[31]++; }
static void put16(u8 *p, int v) { p[0] = (u8)v; p[1] = (u8)(v >> 8); }
static void tables(int file)                    /* 5 divisions of 4 clubs: team word = file | (16 * d + k) << 8 */
{
    memset(IN, 0, sizeof IN);
    IN[0] = 5;
    for (int d = 0; d < 5; d++) {
        IN[O_INN + d] = 4;
        for (int k = 0; k < 4; k++) {
            u8 *r = IN + O_INT + (d * C_GT + k) * C_ROW;
            put16(r, file | (16 * d + k) << 8); put16(r + O_RPTS, 60 - 3 * k + d);
        }
    }
}
static void show(const char *tag)
{
    const struct fp_ml *ml = (const struct fp_ml *)FP_ML;
    for (int i = 0; i < FP_ML_N; i++, ml++) {
        printf("%s%d id=%d st=%d n=%d have=%d seed=%u win=%04X fl=%d club=%04X,%04X,%04X m=", tag, i, ml->id, ml->state, ml->n,
               ml->have, ml->seed, ml->winner, ml->flags, ml->club[0], ml->club[1], ml->club[2]);
        for (int k = 0; k < 3; k++) { const u8 *m = ml->m_raw + 6 * k; printf("%d.%d.%d.%d.%d.%d ", m[0], m[1], m[2], m[3], m[4], m[5]); }
        printf("\n");
    }
}
static void play(int n)                         /* the queued fixture n: its forced score through the port's callback */
{
    sr_port_fixture f; sr_port_result r;
    memset(&f, 0, sizeof f); memset(&r, 0, sizeof r);
    f.match_id = r.match_id = Q[n].id; f.home = Q[n].home; f.away = Q[n].away; f.kind = 0x4D;
    for (int i = 0; i < 8; i++)
        if (FP_MLF[i][0] == (Q[n].id >> 4 & 15) + 1 && FP_MLF[i][1] == (Q[n].id & 15)) { r.g90[0] = FP_MLF[i][2]; r.g90[1] = FP_MLF[i][3]; }
    printf("fix id=%08X home=%04X away=%04X off=%u queued=%d\n", Q[n].id, Q[n].home, Q[n].away, Q[n].off, nadd);
    fp_ml_result(&f, &r);
}
int main(int argc, char **argv)
{
    /* me (-1: not an entrant) seed g1h g1a g2h g2a g3h g3a mode */
    const int me = atoi(argv[1]), mode = argc > 9 ? atoi(argv[9]) : 0;
    memcpy(FP_MLT, ROWBYTES, sizeof(struct fp_mlrow)); FP_MLN = 1; FP_MLTF[0] = 0x45; FP_MLDONE = ndone;
    FP_MLSEED = (u32)strtoul(argv[2], 0, 0);
    for (int k = 0; k < 3; k++) { FP_MLF[k][0] = 1; FP_MLF[k][1] = (u8)k; FP_MLF[k][2] = (u8)atoi(argv[3 + 2 * k]); FP_MLF[k][3] = (u8)atoi(argv[4 + 2 * k]); }
    tables(0x45);
    GP_MGR = me >= 0 ? (u16)(0x45 | (16 * (2 + me)) << 8) : (u16)(0x45 | (16 * 2 + 3) << 8);
    if (mode == 3) {                            /* fp_ml_loaded on hand-made instances (stdin: 112 B hex) */
        char hx[512]; if (!fgets(hx, sizeof hx, stdin)) return 1;
        for (int i = 0; i < FP_ML_SZ; i++) { unsigned v; sscanf(hx + 2 * i, "%2x", &v); FP_ML[i] = (u8)v; }
        fp_ml_loaded(); show("L");
        return 0;
    }
    if (mode == 1) refuse = 1;                  /* the port refuses every fixture: simulated */
    if (mode == 2) { tables(0x46); fp_ml_open(0); fp_ml_open(1); show("X"); tables(0x45); }   /* another country's tables */
    memset(GP_GIN + O_INSIM, 255, 9);
    for (int d = 0; d < 5; d++) if (d != (me >= 0 ? 2 + me : 2)) GP_GIN[O_INN + d] = 0;   /* (the league's end: the career club's table only) */
    printf("need=%X", fp_ml_need());
    printf(" sim=%d,%d,%d\n", GP_GIN[O_INSIM], GP_GIN[O_INSIM + 1], GP_GIN[O_INSIM + 2]);
    tables(0x45);
    fp_ml_lend();
    show("A");
    fp_ml_open(0);                              /* (a second league-end call: nothing) */
    for (int n = 0; n < nadd; n++) play(n);
    show("B");
    printf("busy=%u,%u\n", fp_ml_busy(GP_MGR), fp_ml_busy(0x1234));
    fp_ml_end();
    fp_ml_end();
    show("C");
    sr_srow rows[4];
    const int rc = fp_ml_table(fp_ml_get(0), rows);
    printf("table=%d first=%d log open=%d sim=%d add=%d done=%d cb=%d\n", rc, rows[0].club, nlog[FL_MLOPEN], nlog[FL_MLSIM],
           nlog[FL_MLADD], nlog[FL_MLDONE], nlog[31]);
    return 0;
}
'''


def _build(t):
    drv = os.path.join(t, 'drv.c')
    open(drv, 'w').write(DRIVER.replace('ROWBYTES', '"' + ''.join(f'\\x{b:02x}' for b in ROWB) + '"'))
    exe = os.path.join(t, 'drv')
    r = subprocess.run(['cc', '-std=gnu11', '-Wall', '-O1', '-I', TOOLS, '-DFP_ST_SZ=420', '-DFP_SAVE_SZ=2528',
                        '-DFP_SAVE_HDR=36', '-DFP_ML_SZ=112', '-DFP_HASH=1u', '-DFP_WORLD=5', '-DO_INN=4', '-DO_INT=22',
                        '-DO_INMGR=0', '-DC_GD=16', '-DC_GT=32', '-DC_ROW=12', '-DO_RPTS=10', '-DO_INSIM=6170', '-DC_SDX=9', '-DC_NOC=255', drv, '-o', exe], capture_output=True, text=True)
    return exe, r


def _exe(t):
    return _build(t)


def _parse(out):
    d = {'fix': []}
    for ln in out.splitlines():
        k, _, rest = ln.partition(' ')
        if k == 'fix':
            d['fix'].append(dict(x.split('=') for x in rest.split()))
        elif k[:1] in 'ABCXL' and k[1:].isdigit():
            f = dict(x.split('=') for x in rest.split() if '=' in x)
            f['m'] = [tuple(int(v) for v in x.split('.')) for x in rest.split('m=')[1].split()]
            d[k] = f
        else:
            d[k.split('=')[0]] = ln
    return d


def test_fpml_stage():
    import fpmlgate as G
    with tempfile.TemporaryDirectory() as t:
        exe, r = _exe(t)
        if r.returncode:
            return False, 'compile: ' + r.stderr[:600]
        club = [0x45 | (16 * (2 + c)) << 8 for c in range(3)]
        scores = [((2, 0), (1, 1), (0, 1)), ((0, 0), (0, 0), (0, 0)), ((1, 0), (1, 0), (1, 0)), ((0, 3), (2, 2), (3, 1)),
                  ((1, 1), (2, 0), (0, 2)), ((2, 1), (2, 1), (2, 1))]
        seeds = [G.seed_for(h, a) for h, a in itertools.permutations(range(3), 2)]
        errs, n = [], 0
        for seed, sc, me, mode in itertools.product(seeds, scores, (-1, 0, 1, 2), (0, 1, 2)):
            if mode and (sc != scores[0] or (mode == 2 and me != -1)):
                continue
            args = [str(me), str(seed)] + [str(g) for s in sc for g in s] + [str(mode)]
            out = subprocess.run([exe] + args, capture_output=True, text=True).stdout
            d = _parse(out)
            ms, rows = G.stage(seed, {k + 1: sc[k] for k in range(3)})
            what = f'seed {seed} scores {sc} me {me} mode {mode}'
            n += 1
            try:
                c = d['C0']
                mine = [m for m in ms if me in m[1:3]] if me >= 0 and mode == 0 else []
                assert d['C1']['id'] == '0', 'instance 1 used'
                assert (c['id'], c['st'], c['n'], c['have'], c['fl']) == ('1', '2', '3', '3', '1'), ('final', c)
                assert int(c['seed']) == seed and c['club'] == ','.join(f'{x:04X}' for x in club), ('seed / clubs', c)
                assert [m[:3] + (1,) + m[4:6] for m in c['m']] == [(k, m[1], m[2], 1, m[3], m[4]) for k, m in enumerate(ms)], \
                    ('matches', c['m'], ms)
                assert int(c['win'], 16) == club[rows[0]['club']], ('winner', c['win'], rows[0])
                assert d['table'].split()[0:2] == ['table=3', f"first={rows[0]['club']}"], d['table']
                fx = [(int(f['id'], 16) & 15, int(f['home'], 16), int(f['away'], 16), int(f['off']), int(f['queued'])) for f in d['fix']]
                want = [(m[0], club[m[1]], club[m[2]], m[0] + 1, i + 1) for i, m in enumerate(mine)]
                assert fx == want, ('port fixtures (md, home, away, off, queued when played)', fx, want)
                nadd = len(mine) if mode == 0 else (len([m for m in ms if me in m[1:3]]) if me >= 0 else 0)
                assert f'open=1 sim={3 - len(mine)} add={nadd} done=1 cb=3' in d['table'], ('log', d['table'])
                oth = [str(x) for x in (2, 3, 4) if x != 2 + me] + ['255']
                assert d['need'] == (f"need=1C sim={','.join(oth)}" if me >= 0 else 'need=0 sim=255,255,255'), d['need']
                if me >= 0:
                    assert d['A0']['st'] == ('2' if mode == 1 else '1') and d['A0']['have'] in ('1', '3'), ('after the league end', d['A0'])
                    assert d['B0']['st'] == '2', ('after the played matches', d['B0'])
                    assert d['busy'] == 'busy=0,0', d['busy']
                else:
                    assert d['A0']['id'] == '0' and d['B0']['id'] == '0', ('not an entrant: nothing before the season end', d['A0'])
                if mode == 2:
                    assert d['X0']['id'] == '0', ('another country\'s tables opened it', d['X0'])
            except (AssertionError, KeyError) as e:
                errs.append(f'{what}: {e.args}')
                if len(errs) > 3:
                    break
        return not errs, '; '.join(str(e) for e in errs)[:900] or f'{n} stages = the model (6 draws x scores x the career club entrant 0 / 1 / 2 / none; refused fixtures simulated; another country\'s season end)'


def _inst(i=1, st=1, n=3, have=1, seed=7, club=(0x2045, 0x3045, 0x4045), m=(), winner=0, season=30, flags=0):
    b = struct.pack('<4BI4H', i, st, n, have, seed, *(tuple(club) + (0,) * (4 - len(club))))
    b += b''.join(bytes(x) for x in m) + bytes(36 - 6 * len(m)) + struct.pack('<HBB', winner, season, flags)
    assert len(b) == 56
    return b


def test_fpml_load():
    import fpmlgate as G
    with tempfile.TemporaryDirectory() as t:
        exe, r = _exe(t)
        if r.returncode:
            return False, 'compile: ' + r.stderr[:600]
        seed = G.seed_for(1, 0)
        h, a, _rest = G.md1(seed)
        ms, rows = G.stage(seed, {1: (2, 0), 2: (1, 1), 3: (0, 1)})
        full = [(k, m[1], m[2], 1, m[3], m[4]) for k, m in enumerate(ms)]
        good1 = _inst(have=1, seed=seed, m=[(0, h, a, 0, 0, 0)])
        good3 = _inst(st=2, have=3, seed=seed, m=full, winner=0x2045, flags=1)
        cases = [('open, md1 to play', good1 + bytes(56), ('1', '0')), ('done', good3 + bytes(56), ('1', '0')),
                 ('md1 swapped', _inst(have=1, seed=seed, m=[(0, a, h, 0, 0, 0)]) + bytes(56), ('0', '0')),
                 ('a club twice', _inst(have=1, seed=seed, club=(0x2045, 0x2045, 0x4045), m=[(0, h, a, 0, 0, 0)]) + bytes(56), ('0', '0')),
                 ('row id 2 (no such row)', _inst(i=2, have=1, seed=seed, m=[(0, h, a, 0, 0, 0)]) + bytes(56), ('0', '0')),
                 ('done with one match', _inst(st=2, have=1, seed=seed, m=[(0, h, a, 0, 0, 0)]) + bytes(56), ('0', '0')),
                 ('md2 changed', _inst(st=2, have=3, seed=seed, m=[full[0], (1, full[1][2], full[1][1], 1, 0, 0), full[2]]) + bytes(56), ('0', '0')),
                 ('instance 0 sound, instance 1 garbage', good3 + bytes(range(56)), ('1', '0'))]
        errs = []
        for name, blob, want in cases:
            out = subprocess.run([exe, '0', '1', '0', '0', '0', '0', '0', '0', '3'], input=blob.hex() + '\n',
                                 capture_output=True, text=True).stdout
            d = _parse(out)
            got = (d.get('L0', {}).get('id'), d.get('L1', {}).get('id'))
            if got != want:
                errs.append(f'{name}: ids {got}, want {want}')
        return not errs, '; '.join(errs) or f'{len(cases)} loaded blocks: sound instances kept, corrupt ones dropped alone'


def test_fpml_row():
    import fpad

    class Pk:
        kind, world = 'career', 5
        files = {'league': (0x45, None)}

        def __init__(self, row):
            self.meta = {'id': 'ita', 'competitions': [{'type': 'league', 'ko_playoffs': [{}], 'mini_leagues': [row]}]}
    keep = dict(fpad._ROWS)
    errs = []
    try:
        def tab(row):
            pk = Pk(row)
            fpad._ROWS.clear()
            fpad._ROWS[(os.environ.get('SEASON_PACKS'), fpad.world())] = [(pk, pk.meta['competitions'][0], row)]
            return fpad.ml_table()
        t, f = tab(ROW)
        if t != ROWB or f != b'\x45':
            errs.append(f'row bytes {t.hex()} / {f.hex()}, want {ROWB.hex()} / 45')
        for name, ch in (('5 entrants', {'entrants': [[2, 1]] * 5}), ('winner_rests with 4', {'entrants': [[1, 1], [2, 1], [3, 1], [4, 1]], 'units': [1, 2, 3]}),
                         ('units not rising', {'units': [1, 1, 2]}), ('2 units', {'units': [1, 2]}),
                         ('a place 0', {'entrants': [[2, 0], [3, 1], [4, 1]]})):
            try:
                tab(dict(ROW, **ch))
                errs.append(f'{name}: accepted')
            except (AssertionError, KeyError):
                pass
    finally:
        fpad._ROWS.clear()
        fpad._ROWS.update(keep)
    return not errs, '; '.join(errs) or 'the Italian row = 34 B (winner_rests, 3 / 1 / 0, points + 4 tie-breaks, units 1 2 3, record flag); 5 bad rows refused'
