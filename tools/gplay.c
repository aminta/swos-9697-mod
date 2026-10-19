/* Knockout promotion / relegation play-offs of a career world's leagues (pack.json league 'ko_playoffs', kind
   'promotion'), decided at the season end from the final tables (tools/gplay.py; the European play-offs are
   uefaq's, the Italian ones dplay's).

   GP_IN.spec: the country's play-offs, each
     kind (1 promotion, 2 europe, 3 placement, 4 playout), n entrants, rounds, winner_div, loser_div (0xFE: the
     reserve, out of the league = division nd), flags,
     n x (type, div, a, b): type 0 = [div, place a], 1 = the best of div without Europe, 2 = the league cup winner;
     rounds x (ties, legs, host, level, pairing, gap) + 2 x ties member codes: 0..63 an entrant, 0x80|k the winner of
     tie k, 0xC0|k its loser (ties numbered across rounds); pairing p > 0 = the first p members best v worst, re-paired;
   gap g > 0: a tie whose clubs are g+ points apart is not played, the better placed goes through;
   a GROUP round (a round robin): (members m, 0x80 | meetings, host, 0, 0, 0) + m member codes + m start bonus points;
   its final placings are appended to the placings list (numbered across the group rounds), member code 0x40|k = the
   k-th placing; flags bits 4-7 = 'winners' (a promotion play-off ending with a group: its top w go to winner_div,
   the other winner_div clubs to loser_div; 0 = 1); ended by a 0.
   Only the promotion / playout play-offs whose entrants are all [div, place] are played here: promotion = the
   winner to winner_div, another winner_div entrant to loser_div; playout = the last round's losers to loser_div.
   4.0 package 6 ('title' / 'continental', world byte 0 and 5.0): kind 5 title = the champion is the last tie's
   winner (GP_OUT.res: team / global number), kind 6 continental = the continental places go to the last tie's winner
   and loser (the champion stays the table's 1st); entrant type 3 = place a of stage b's kept table (GP_IN.st[b],
   split's 'keep'), resolved to its row of division div's final table by the global number; host byte bit 7 =
   skip_if_same (a tie of one club with itself is not played: it goes through); levels 4 away_pens / 5 away_better
   (away goals are not simulated: as et_pens / better); member 0x3F = the best placed loser of the previous round. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;

enum { GT = 32, GD = 16, GN = 64, RESERVE = 0xFE };   /* (GD: Italy 2026-27 has 14 divisions; GT: Argentina's 30) */
enum { HOST_LISTED, HOST_BETTER, HOST_DRAWN, HOST_NEUTRAL, HOST_SKIP_SAME = 0x80 };
enum { LV_BETTER, LV_ET_PENS, LV_ET_BETTER, LV_PENS, LV_AWAY_PENS, LV_AWAY_BETTER };
enum { K_TITLE = 5, K_CONT = 6, K_PROM = 7, K_STAGE = 8, GS = 2, BEST_LOSER = 0x3F };
struct gp_row { u16 team, glob, won, gf, ga, pts; };
static void rcopy(struct gp_row *d, const struct gp_row *s) {   /* (no memcpy in the exe: field by field) */
    d->team = s->team; d->glob = s->glob; d->won = s->won; d->gf = s->gf; d->ga = s->ga; d->pts = s->pts;
}
enum { KT = 24, SD = 2, SDX = 9, GSD = 7, GSR = 20 };   /* SD: early tables in GP_ST; SDX: all (+ GP_GS) */
struct gp_in {
    u8 nd, pad[3];
    u8 n[GD], pad2[2];                  /* clubs per division (0 = not captured) */
    struct gp_row t[GD][GT];
    const u8 *spec;
    u8 nst[GS], pad3[2];                /* kept stage tables (split 'keep'), rows by place */
    struct gp_row st[GS][GT];
    /* the playable play-offs (gp_lend / gp_end) */
    u16 mgr, week;                      /* the career club's team word, the league's last week */
    u8 mdiv, gtype, pl_pi, pl_t2;       /* its division, g_gameType; gp_end: the played play-off (index + 1); a
                                           group contest's (the Poule): pl_w[0] / [1] = its champion / runner-up */
    u8 pi[2], sim[SDX];                 /* gp_need: the play-offs to play (spec index, 0xFF), divisions simulated early */
    u16 pl_w[KT];                       /* gp_end: the played play-off's tie winners (team words, 0 = not played) */
};
struct gp_mv { u16 glob, team; s8 delta; u8 pad[3]; };
struct gp_res { u8 kind, div; u16 team[2], glob[2]; };     /* title: [0] the champion; continental: winner, loser */
struct gp_out { u8 nmv, nres, pad[2]; struct gp_mv mv[32]; struct gp_res res[4];
                struct gp_res sres[3]; };   /* 4.0 ARG stage_title: [stage] champion, runner-up (0xFFFF: none) */
struct gp_in GP_IN;
struct gp_out GP_OUT;
struct gp_dec { u8 season, done, pad[2]; u16 team[2], glob[2]; };   /* 4.0 ARG: a stage title decided mid-season */
static const struct gp_dec *stage_dec(int k);   /* (GP_ST's, this season's, or 0: after GP_ST) */
enum { SS_N = 3, SS_BASE = 4 };      /* stage tables of a league with fixture stages (split 'table'): entrant
                                        'stage_place' s = SS_BASE + k (Argentina: 4 Apertura, 5 Clausura, 6 the
                                        annual table); saved with the career (engine item 'SS') */
struct gp_ss { u8 n[SS_N], fresh; struct gp_row r[SS_N][GT]; };   /* fresh: bit k = r[k] written this season */
static int ss_used;                     /* (a play-off read GP_SS this season end: fresh cleared after) */
struct gp_ss GP_SS;
const u32 GP_LAYOUT[] = { sizeof(struct gp_row), GT, __builtin_offsetof(struct gp_in, n),
                          __builtin_offsetof(struct gp_in, t), __builtin_offsetof(struct gp_in, spec),
                          __builtin_offsetof(struct gp_out, mv), sizeof(struct gp_mv), GD,
                          __builtin_offsetof(struct gp_in, nst), __builtin_offsetof(struct gp_in, st), GS,
                          __builtin_offsetof(struct gp_out, nres), __builtin_offsetof(struct gp_out, res),
                          sizeof(struct gp_res) };

static u32 rng;
static u32 below(u32 n) {
    rng = rng * 1103515245u + 12345u;
    return ((rng >> 16) * n) >> 16;
}

#define DV(c) ((c) / GT)
#define PL(c) ((c) % GT)
static const struct gp_row *row(int c) { return &GP_IN.t[DV(c)][PL(c)]; }

static int better(int a, int b) {       /* the higher tier, then the better place */
    if (DV(a) != DV(b)) return DV(a) < DV(b);
    return PL(a) < PL(b);
}

static u32 str2(int c, int home) {      /* strength: the place in its division, the tier */
    int n = GP_IN.n[DV(c)];
    int s = 30 + 40 * (n - PL(c)) / (n ? n : 1) - 25 * DV(c);
    if (s < 5) s = 5;
    if (home) s = s * 11 / 10;
    return (u32)(s * s);
}

/* a tie: a = the single match's host / the first leg's home club (listed order), b = the other */
static int tie(int a, int b, int legs, int host, int level) {
    int h = a, o = b, w;
    if (host == HOST_BETTER || host == HOST_NEUTRAL) {      /* the better placed hosts the single match / return */
        if (better(b, a)) { h = b; o = a; }
        else { h = a; o = b; }
        if (legs == 2 || host == HOST_NEUTRAL) { int x = h; h = o; o = x; }   /* (h = the first leg's / listed) */
    } else if (host == HOST_DRAWN && below(2)) { h = b; o = a; }
    /* the club with home advantage: a single match's host, the return leg's home club */
    int adv = (legs == 1) ? (host == HOST_NEUTRAL ? -1 : h) : o;
    u32 sh = str2(h, adv == h), so = str2(o, adv == o);
    if (below(100) < (legs == 1 ? 22u : 12u)) {             /* level after the regulation time */
        int bp = better(h, o) ? h : o;
        if (level == LV_BETTER || level == LV_ET_BETTER || level == LV_AWAY_BETTER) return bp;
        u32 x = str2(h, 0), y = str2(o, 0);                   /* e.t. + penalties: close to a coin toss */
        sh = 2 * x + y; so = x + 2 * y;
    }
    w = below(sh + so) < sh ? h : o;
    return w;
}

static int series(int a, int b, int level) {   /* best of three: games 1 and 3 at the better placed's */
    int h = better(a, b) ? a : b, o = h == a ? b : a, wh = 0, wo = 0;
    for (int g = 0; g < 3 && wh < 2 && wo < 2; g++)
        if (tie(g == 1 ? o : h, g == 1 ? h : o, 1, HOST_LISTED, level) == h) wh++; else wo++;
    return wh == 2 ? h : o;
}

#ifndef GP_FORCE
#define GP_FORCE 0
#endif
/* test builds (GPLAY_FORCE=k): the career club takes place k of its division (team and global number swapped with
   the club there), at the league end and again at the season end */
static int gp_force(void) {
    if (!GP_FORCE || !GP_IN.mgr) return -1;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++)
            if (GP_IN.t[d][k].team == GP_IN.mgr && GP_FORCE <= GP_IN.n[d]) {
                struct gp_row *t = GP_IN.t[d], x = t[k];
                t[k].team = t[GP_FORCE - 1].team; t[k].glob = t[GP_FORCE - 1].glob;
                t[GP_FORCE - 1].team = x.team; t[GP_FORCE - 1].glob = x.glob;
                return GP_FORCE - 1;
            }
    return -1;
}

static void move(int c, int delta) {
    if (!delta || GP_OUT.nmv >= 32) return;
    struct gp_mv *m = &GP_OUT.mv[GP_OUT.nmv++];
    m->glob = row(c)->glob; m->team = row(c)->team; m->delta = delta;
}

static int sbetter_cmp(int a, int b) { return better(a, b); }

static void result(int kind, int w, int l) {
    if (GP_OUT.nres >= 4) return;
    struct gp_res *x = &GP_OUT.res[GP_OUT.nres++];
    x->kind = kind; x->div = DV(w);
    x->team[0] = row(w)->team; x->glob[0] = row(w)->glob;
    x->team[1] = l >= 0 ? row(l)->team : 0xFFFF; x->glob[1] = l >= 0 ? row(l)->glob : 0xFFFF;
}

static int stage_club(int d, int s, int a) {   /* place a of kept stage s -> its row of division d, or -1 */
    u16 g;
    if (s >= SS_BASE && s < SS_BASE + SS_N) {
        int k = s - SS_BASE;
        ss_used = 1;
        if (!(GP_SS.fresh & 1 << k)) {          /* (not written this season: a simulated league skips split's stage
                                                   end -> the division's final table, its places as the stage's) */
            if (d >= GP_IN.nd || a < 1 || a > GP_IN.n[d]) return -1;
            return d * GT + a - 1;
        }
        if (a < 1 || a > GP_SS.n[k] || d >= GP_IN.nd) return -1;
        g = GP_SS.r[k][a - 1].glob;
    } else {
        if (s >= GS || a < 1 || a > GP_IN.nst[s] || d >= GP_IN.nd) return -1;
        g = GP_IN.st[s][a - 1].glob;
    }
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int glob_club(int d, u16 g) {     /* a global number -> its row of division d, or -1 */
    if (g == 0xFFFF || d >= GP_IN.nd) return -1;
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int title_club(int d, int c) {   /* entrant type 5 (the Trofeo): 1 the 1st stage's champion; 2 / 3 the 2nd
                                           stage's champion, or (the same club won both) the 1st's / 2nd's runner-up */
    u16 c0 = GP_OUT.sres[0].glob[0], c1 = GP_OUT.sres[1].glob[0];
    if (c == 1) return glob_club(d, c0);
    if (c0 != c1) return glob_club(d, c1);
    return glob_club(d, GP_OUT.sres[c - 2].glob[1]);
}

/* a group match: goals by strength (draws ~ 1 in 4), home advantage unless neutral */
static void gmatch(int h, int a, int neutral, int *gh, int *ga) {
    u32 sh = str2(h, !neutral), sa = str2(a, 0);
    if (below(100) < 26) { int g = below(3); *gh = g; *ga = g; return; }
    int w = below(sh + sa) < sh, gw = 1 + below(3), gl = below(gw);
    *gh = w ? gw : gl; *ga = w ? gl : gw;
}

struct gs { int c, pts, gd, gf; };
static int gs_before(const struct gs *x, const struct gs *y) {   /* points, goal difference, goals, the better place */
    if (x->pts != y->pts) return x->pts > y->pts;
    if (x->gd != y->gd) return x->gd > y->gd;
    if (x->gf != y->gf) return x->gf > y->gf;
    return better(x->c, y->c);
}

/* a group round: mem[0..m) round robin `meet` times (home and away alternate), start bonus points; placings -> out,
   their figures -> outs. meet 0 = a ranking round (pack 'best_of'): the members, earlier placings, ranked by the
   figures of their own groups (ins) */
static void group(const int *mem, int m, int meet, int neutral, const u8 *bonus, int *out, const struct gs *ins,
                  struct gs *outs) {
    struct gs t[GT];                    /* (at most 24 members: compile_spec)  */
    for (int i = 0; i < m; i++) {
        t[i].c = mem[i]; t[i].pts = bonus[i]; t[i].gd = 0; t[i].gf = 0;
        if (!meet) { t[i].pts = ins[i].pts; t[i].gd = ins[i].gd; t[i].gf = ins[i].gf; }
    }
    for (int k = 0; k < meet; k++)
        for (int i = 0; i < m; i++)
            for (int j = i + 1; j < m; j++) {
                int h = (k & 1) ? j : i, a = (k & 1) ? i : j, gh, ga;
                gmatch(t[h].c, t[a].c, neutral, &gh, &ga);
                t[h].gf += gh; t[a].gf += ga; t[h].gd += gh - ga; t[a].gd += ga - gh;
                if (gh > ga) t[h].pts += 3; else if (gh < ga) t[a].pts += 3; else { t[h].pts++; t[a].pts++; }
            }
    for (int i = 1; i < m; i++) {
        struct gs x = t[i]; int j = i;
        while (j > 0 && gs_before(&x, &t[j - 1])) { t[j] = t[j - 1]; j--; }
        t[j] = x;
    }
    for (int i = 0; i < m; i++) { out[i] = t[i].c; outs[i] = t[i]; }
}

static struct gs PS[GN], ms[GT];       /* (gp_season: the placings' figures; a round's members' (static: the stack)) */

/* split's kept stage table (gp_cap, every captured division; split.py's freeze sets the 'kept' byte at ST+5 when a
   'keep' stage froze the table before it: rows by place at S_KEEP, their points at S_KEEP+22): into GP_IN.st[k] in the
   order the season end captures them (k = 0 again at each country's division 0). diy = DIY, st = split.ST, keep =
   S_KEEP - ST, sel = the team cache (a row's team dword is an offset into it: +2 the global number). */
static u8 gp_kn;
void gp_keep(const u8 *diy, u32 st, u32 keep, const u8 *sel, u32 div, u32 magic) {
    if (div == 0) {
        gp_kn = 0;
        for (int i = 0; i < GS; i++) GP_IN.nst[i] = 0;
    }
    const u8 *s = diy + st, *k = s + keep;
    int n = diy[0x31] | diy[0x32] << 8;
    if ((u32)(s[0] | s[1] << 8) != magic || s[5] != 1 || gp_kn >= GS || n < 2 || n > GT || n > 21) return;
    u32 seen = 0;
    for (int i = 0; i < n; i++) {
        if (k[i] >= n || seen & 1u << k[i]) return;
        seen |= 1u << k[i];
    }
    struct gp_row *o = GP_IN.st[gp_kn];
    for (int i = 0; i < n; i++) {
        int r = k[i];
        const u8 *row = diy + 0x2B3 + 18 * r;
        u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
        o[i].team = diy[0x12D + 2 * r] | diy[0x12E + 2 * r] << 8;
        o[i].glob = sel[t + 2] | sel[t + 3] << 8;
        o[i].won = o[i].gf = o[i].ga = 0;
        o[i].pts = k[22 + 2 * i] | k[23 + 2 * i] << 8;
    }
    GP_IN.nst[gp_kn++] = n;
}

/* split's stage end (sp_stage_end, a fixture stage with 'table'): the DIY table in its order (+6Dh, the groups
   partitioned by sp_sort: Argentina's zone A then zone B) into GP_SS.r[k]; annual: GP_SS.r[2] = r[0] + r[1] by club,
   by points, goal difference, goals (the earlier stage's order on a tie). */
void gp_stage(const u8 *diy, const u8 *sel, u32 k, u32 annual) {
    int n = diy[0x31] | diy[0x32] << 8;
    if (k >= SS_N || n < 1 || n > GT) return;
    struct gp_row *o = GP_SS.r[k];
    for (int i = 0; i < n; i++) {
        int off = diy[0x6D + 2 * i] | diy[0x6E + 2 * i] << 8, r = off / 18;
        const u8 *row = diy + 0x2B3 + off;
        u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
        o[i].team = diy[0x12D + 2 * r] | diy[0x12E + 2 * r] << 8;
        o[i].glob = sel[t + 2] | sel[t + 3] << 8;
        o[i].won = row[6] | row[7] << 8;
        o[i].gf = row[12] | row[13] << 8;
        o[i].ga = row[14] | row[15] << 8;
        o[i].pts = row[16] | row[17] << 8;
    }
    GP_SS.n[k] = n;
    GP_SS.fresh |= 1 << k;
    if (!annual || k == 0 || GP_SS.n[0] != n) return;
    struct gp_row *a = GP_SS.r[2], tmp;
    for (int i = 0; i < n; i++) {
        rcopy(&a[i], &GP_SS.r[0][i]);
        for (int j = 0; j < n; j++) if (o[j].glob == a[i].glob) {
            a[i].won += o[j].won; a[i].gf += o[j].gf; a[i].ga += o[j].ga; a[i].pts += o[j].pts;
        }
    }
    for (int i = 1; i < n; i++)                 /* insertion sort: stable */
        for (int j = i; j > 0; j--) {
            int dp = a[j].pts - a[j - 1].pts, dd = (a[j].gf - a[j].ga) - (a[j - 1].gf - a[j - 1].ga);
            if (dp > 0 || (dp == 0 && (dd > 0 || (dd == 0 && a[j].gf > a[j - 1].gf)))) {
                rcopy(&tmp, &a[j]); rcopy(&a[j], &a[j - 1]); rcopy(&a[j - 1], &tmp);
            } else break;
        }
    GP_SS.n[2] = n;
    GP_SS.fresh |= 4;
}

/* Argentina's relegation (LPF reglamento 2026 art. 26, AFA statute art. 93): kind 7 'promedio' (n = 0, no rounds;
   winner_div byte = the season's matches counted, loser_div = where the relegated go): the last of the promedios
   (points per match over this season's annual table and the two before, top-flight seasons only) and the last of
   the annual table (GP_SS 2) go down; a tie in a relegation place -> a play-off match at a neutral ground. History
   per club in PR_STATE (engine item 'PR', the build's GP_PROM table at a new career: dw count; count x (dw global,
   dw points y-2, db matches y-2, dw points y-1, db matches y-1)), shifted after every season end. */
enum { PR_N = 48 };
struct pr_club { u16 glob, p[2]; u8 m[2]; };
struct pr_state { u8 init, n, pad[2]; struct pr_club c[PR_N]; };
struct pr_state PR_STATE;
extern const u8 GP_PROM_TAB[];

static struct pr_club *pr_find(u16 g) {
    for (int i = 0; i < PR_STATE.n; i++) if (PR_STATE.c[i].glob == g) return &PR_STATE.c[i];
    return 0;
}

static void pr_seed(void) {
    const u8 *t = GP_PROM_TAB;
    PR_STATE.n = 0;
    for (int k = t[0] | t[1] << 8, i = 0; i < k && i < PR_N; i++) {
        const u8 *e = t + 2 + 8 * i;
        struct pr_club *c = &PR_STATE.c[PR_STATE.n++];
        c->glob = e[0] | e[1] << 8; c->p[0] = e[2] | e[3] << 8; c->m[0] = e[4]; c->p[1] = e[5] | e[6] << 8; c->m[1] = e[7];
    }
    PR_STATE.init = 1;
}

static int pr_row(int d, u16 g) {               /* a global number -> its row of division d's table, or -1 */
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static void promedio(int d, int mnow, int ldiv) {
    if (!PR_STATE.init) pr_seed();
    int n = GP_SS.n[2];
    const struct gp_row *a = GP_SS.r[2];
    if (!(GP_SS.fresh & 4) || n != GP_IN.n[d]) {   /* (no annual table this season: the league's final table) */
        n = GP_IN.n[d];
        a = GP_IN.t[d];
    }
    ss_used = 1;
    if (n < 3) return;
    u32 P[GT], M[GT];
    for (int i = 0; i < n; i++) {
        struct pr_club *c = pr_find(a[i].glob);
        P[i] = a[i].pts + (c ? c->p[0] + c->p[1] : 0);
        M[i] = mnow + (c ? c->m[0] + c->m[1] : 0);
    }
    int w = 0, w2 = -1;                         /* the worst promedio (P / M), then the next worst */
    for (int i = 1; i < n; i++) if (P[i] * M[w] < P[w] * M[i] || (P[i] * M[w] == P[w] * M[i] && i > w)) w = i;
    for (int i = 0; i < n; i++) if (i != w && (w2 < 0 || P[i] * M[w2] < P[w2] * M[i])) w2 = i;
    int down1 = w;
    if (w2 >= 0 && P[w2] * M[w] == P[w] * M[w2]) {          /* level: a play-off match, the loser goes down */
        int ca = pr_row(d, a[w].glob), cb = pr_row(d, a[w2].glob);
        if (ca >= 0 && cb >= 0) down1 = tie(ca, cb, 1, HOST_NEUTRAL, LV_ET_PENS) == ca ? w2 : w;
    }
    int l = n - 1;                              /* the annual table's last, the promedio's relegated apart */
    if (l == down1) l--;
    int l2 = l - 1 == down1 ? l - 2 : l - 1, down2 = l;
    if (l2 >= 0 && a[l2].pts == a[l].pts) {
        int ca = pr_row(d, a[l].glob), cb = pr_row(d, a[l2].glob);
        if (ca >= 0 && cb >= 0) down2 = tie(ca, cb, 1, HOST_NEUTRAL, LV_ET_PENS) == ca ? l2 : l;
    }
    int c1 = pr_row(d, a[down1].glob), c2 = pr_row(d, a[down2].glob);
    if (c1 >= 0) move(c1, ldiv - d);
    if (c2 >= 0) move(c2, ldiv - d);
    static struct pr_club nx[PR_N];             /* next season's history: this season and the one before */
    int nn = 0;
    for (int i = 0; i < n && nn < PR_N; i++) {
        if (i == down1 || i == down2) continue;
        struct pr_club *c = pr_find(a[i].glob), *o = &nx[nn++];
        o->glob = a[i].glob;
        o->p[0] = c ? c->p[1] : 0; o->m[0] = c ? c->m[1] : 0;
        o->p[1] = a[i].pts; o->m[1] = mnow;
    }
    for (int i = 0; i < nn; i++) {
        struct pr_club *o = &PR_STATE.c[i];
        o->glob = nx[i].glob; o->p[0] = nx[i].p[0]; o->p[1] = nx[i].p[1]; o->m[0] = nx[i].m[0]; o->m[1] = nx[i].m[1];
    }
    PR_STATE.n = nn;
    PR_STATE.init = 1;
}

static int team_club(u16 team) {        /* a team word -> its club (division * GT + place) in the tables, or -1 */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (team && GP_IN.t[d][k].team == team) return d * GT + k;
    return -1;
}

void gp_season(void) {
    const u8 *s = GP_IN.spec;
    u32 h = 0;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) h = h * 31 + GP_IN.t[d][k].glob + (GP_IN.t[d][k].pts << 9);
    rng = h;
    GP_OUT.nmv = 0;
    GP_OUT.nres = 0;
    for (int k = 0; k < 3; k++) {               /* (stage titles: this season's, from the specs below) */
        GP_OUT.sres[k].kind = 0;
        GP_OUT.sres[k].team[0] = GP_OUT.sres[k].team[1] = GP_OUT.sres[k].glob[0] = GP_OUT.sres[k].glob[1] = 0xFFFF;
    }
    int prev_loser = -1;                        /* the last tie's loser of the play-off before (entrant type 4) */
    ss_used = 0;
    gp_force();
    for (int pidx = 0; s && *s; pidx++) {
        int kind = s[0], n = s[1], nr = s[2], wdiv = s[3], ldiv = s[4];
        const u8 *e = s + 6, *r = e + 4 * n;
        if (kind == K_PROM) {                   /* (no entrants, no rounds) */
            promedio(0, wdiv, ldiv);
            s = r;
            continue;
        }
        int club[GN], ok = kind == 1 || kind == 4 || kind == K_TITLE || kind == K_CONT || kind == K_STAGE;
        const struct gp_dec *dec = kind == K_STAGE ? stage_dec(wdiv) : 0;   /* (decided mid-season) */
        if (dec) ok = 0;
        int W[GN], L[GN], nt = 0, last = -1, lastr = 0, nlast = 0;
        int P[GN], np = 0, glast = -1, winners = s[5] >> 4 ? s[5] >> 4 : 1;
        for (int i = 0; i < n && i < GN; i++) {
            int ty = e[4 * i], d = e[4 * i + 1], p = e[4 * i + 2];
            if (ty == 3) {
                club[i] = stage_club(d, e[4 * i + 3], p);
                if (club[i] < 0) ok = 0;
            } else if (ty == 4) {               /* the previous play-off's final loser (Primera Nacional's reducido) */
                club[i] = prev_loser;
                if (club[i] < 0) ok = 0;
            } else if (ty == 5) {               /* 4.0 ARG: the Trofeo's finalists (title_club) */
                club[i] = title_club(d, p);
                if (club[i] < 0) ok = 0;
            } else if (ty != 0 || d >= GP_IN.nd || p < 1 || p > GP_IN.n[d]) ok = 0;
            else club[i] = d * GT + p - 1;
        }
        for (int k = 0; k < nr; k++) {          /* walk the rounds (also to skip a play-off not played here) */
            int ties = r[0], legs = r[1], host = r[2] & 0x7F, skip = r[2] & HOST_SKIP_SAME, level = r[3];
            int pairing = r[4], gap = r[5];
            const u8 *m = r + 6;
            int mem[2 * GN], gm = legs & 0x80 ? ties : 2 * ties;     /* (a group round: ties = its members) */
            for (int i = 0; i < gm; i++) {
                int c = m[i], v = -1;
                if (c == BEST_LOSER) {          /* the best placed loser of the previous round */
                    for (int t = lastr; t < lastr + nlast && t < nt; t++)   /* (still the previous round's) */
                        if (v < 0 || better(L[t], v)) v = L[t];
                } else if (c < 0x40) v = c < n ? club[c] : -1;
                else if (c < 0x80) { v = (c & 0x3F) < np ? P[c & 0x3F] : -1; if (v >= 0 && i < GT) ms[i] = PS[c & 0x3F]; }
                else if (c < 0xC0) v = (c & 0x3F) < nt ? W[c & 0x3F] : -1;
                else v = (c & 0x3F) < nt ? L[c & 0x3F] : -1;
                mem[i] = v;
                if (v < 0) ok = 0;
            }
            if (legs & 0x80) {                  /* a group round */
                if (ok && ties <= GT && np + ties <= GN) {
                    group(mem, ties, legs & 0x7F, host == HOST_NEUTRAL, m + ties, P + np, ms, PS + np);
                    glast = np;
                }
                np += ties;
                last = -1;
                r = m + 2 * ties;
                continue;
            }
            if (ok && (pairing & 0x80)) {   /* a draw (pack 'pairing': 'draw'): the first p members shuffled, paired */
                int pn = (pairing & 0x7F) <= 2 * ties ? pairing & 0x7F : 2 * ties;
                for (int i = pn - 1; i > 0; i--) { int j = below(i + 1), x = mem[i]; mem[i] = mem[j]; mem[j] = x; }
            } else if (ok && pairing) {     /* best v worst: sorted, then 1st v last, 2nd v second last ... */
                int pn = pairing <= 2 * ties ? pairing : 2 * ties;
                for (int i = 1; i < pn; i++) {
                    int x = mem[i], j = i;
                    while (j > 0 && sbetter_cmp(x, mem[j - 1])) { mem[j] = mem[j - 1]; j--; }
                    mem[j] = x;
                }
                int tmp[2 * GN];
                for (int i = 0; i < pn / 2; i++) { tmp[2 * i] = mem[pn - 1 - i]; tmp[2 * i + 1] = mem[i]; }
                for (int i = 0; i < pn; i++) mem[i] = tmp[i];
            }
            lastr = nt; nlast = ties;
            for (int i = 0; i < ties; i++) {
                if (ok && nt < GN) {
                    int a = mem[2 * i], b = mem[2 * i + 1], d = (int)row(a)->pts - (int)row(b)->pts;
                    int w = a == b && skip ? a                                         /* (one club: no tie) */
                          : gap && (d >= gap || -d >= gap) ? (better(a, b) ? a : b)   /* (too far apart: no tie) */
                          : legs == 3 ? series(a, b, level) : tie(a, b, legs, host, level);
                    if (GP_IN.pl_pi == pidx + 1 && nt < KT && GP_IN.pl_w[nt])    /* (played in slot 4: its result) */
                        w = row(b)->team == GP_IN.pl_w[nt] ? b : row(a)->team == GP_IN.pl_w[nt] ? a : w;
                    W[nt] = w; L[nt] = w == mem[2 * i] ? mem[2 * i + 1] : mem[2 * i];
                    last = nt; glast = -1;
                }
                nt++;
            }
            r = m + 2 * ties;
        }
        if (ldiv == RESERVE) ldiv = GP_IN.nd;   /* (the reserve: out of every division) */
        if (kind == K_STAGE) {                  /* a stage title: its champion / runner-up, no move, no league title */
            struct gp_res *x = wdiv < 3 ? &GP_OUT.sres[wdiv] : 0;
            if (x && dec) {
                x->kind = K_STAGE; x->div = 0;
                x->team[0] = dec->team[0]; x->team[1] = dec->team[1]; x->glob[0] = dec->glob[0]; x->glob[1] = dec->glob[1];
            } else if (x && ok && last >= 0) {
                x->kind = K_STAGE; x->div = DV(W[last]);
                x->team[0] = row(W[last])->team; x->glob[0] = row(W[last])->glob;
                x->team[1] = L[last] != W[last] ? row(L[last])->team : 0xFFFF;
                x->glob[1] = L[last] != W[last] ? row(L[last])->glob : 0xFFFF;
            }
        } else if (kind == K_TITLE && GP_IN.pl_t2 && GP_IN.pl_pi == pidx + 1 && team_club(GP_IN.pl_w[0]) >= 0) {
            result(kind, team_club(GP_IN.pl_w[0]), team_club(GP_IN.pl_w[1]));   /* (played: a group contest's final) */
        } else if (ok && (kind == K_TITLE || kind == K_CONT) && glast >= 0) {     /* a final group: its 1st (and 2nd) */
            result(kind, P[glast], np - glast > 1 ? P[glast + 1] : -1);
        } else if (ok && (kind == K_TITLE || kind == K_CONT) && last >= 0) {   /* the last tie's winner (loser) */
            result(kind, W[last], L[last] == W[last] ? -1 : L[last]);
        } else if (ok && glast >= 0 && kind == 1) {    /* a final group: its top `winners` to winner_div, the other
                                                   winner_div clubs to loser_div, the rest stay */
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c), top = 0;
                for (int k = 0; k < winners; k++) if (P[glast + k] == c) top = 1;
                if (top) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                move(c, to - DV(c));
            }
        } else if (ok && last >= 0 && kind == 4) {     /* playout: the last round's losers down */
            for (int t = lastr; t < lastr + nlast && t < GN; t++) move(L[t], ldiv - DV(L[t]));
        } else if (ok && last >= 0) {           /* the winner to winner_div; another winner_div entrant down */
            int w = W[last];
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c);
                if (c == w) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                move(c, to - DV(c));
            }
        }
        prev_loser = ok && last >= 0 ? L[last] : -1;
        s = r;
    }
    if (ss_used) GP_SS.fresh = 0;              /* (this league's stage tables used: next season's are new ones) */
}

/* ---- The playable play-offs (gp_lend .. gp_end in gplay.py): the career club's play-off or play-out is played in
   slot 4 (Season mode: the chosen division's play-off and play-out, slots 4 and 3), as dplay does the Italian ones.
   A contest of the game's type 1 (a national cup, no draw): its team list = the entrants, round 1's ties first (the
   home club / the first leg's first), then the clubs that wait (lib97 byes: gp_bye); every later round is listed
   by gp_perm_c from the spec's member codes; a best-of-three ('series': 3, legs byte 3) is three single-match rounds
   (games 1 and 3 at the better placed's), a game 3 nobody needs is skipped (the contest's rounds - 1). The results:
   gp_rec_c (every decisive match), gp_draw_c (a level tie without penalties: the better placed); the season end
   (gp_played_c) gives gp_season the played winners. The state GP_ST is saved with the career (the engine's save
   block); its season byte makes an old state void. */
enum { KN = 24, KG = 12, KP = 40, KR = 8, KC = 96, MAGIC = 0x4B47, NOC = 0xFF };
enum { LV_BITS_BETTER = 0, LV_BITS_ET_PENS = 0x14, LV_BITS_ET = 0x10, LV_BITS_PENS = 0x04 };
struct gp_srow { u16 team; u8 played, won, drawn, lost, gf, ga; u16 pts; };   /* a place of an early-simulated table */
struct gp_ko {
    u16 magic; u8 season, slot;         /* 'GK' while it runs, its season, slot 4 / 3 */
    u8 cid, pi, kind, n;                /* contest id, play-off index in the country's spec, kind, entrants */
    u8 nrs, ngr, gcur, ntie;            /* spec rounds, game rounds, the game round being played, ties */
    u8 lfile, d1, d2, ldiv;             /* team file, first / last week, the spec's loser_div */
    u8 rs[KR][6];                       /* spec rounds: ties, legs (3 = best of three), host, level, pairing, gap */
    u8 rc[2 * KT];                      /* member codes in spec order */
    u8 gt0[KR + 1];                     /* the first tie of each spec round */
    u8 rb[KG], gsr[KG], gno[KG];        /* game rounds: round byte, spec round, game number in a series */
    u8 gp0[KG + 1];                     /* the first pair of each game round */
    u8 pa[KP], pb[KP], pw[KP], ptie[KP];    /* pairs (list indices, home first), winner, spec tie */
    u8 tw[KT], tl[KT];                  /* spec ties: winner, loser (list indices, NOC) */
    u16 code[KN];                       /* list index -> division * GT + place (GP_IN.t) */
    u8 ient[KN], prio[KN];              /* entrant -> list index; list index -> rank (the better placed: lower) */
    u16 team[KN], pts[KN];
    u8 bye[8];                          /* lib97 bye_find entry: id, 0FFh, clubs, byes, game rounds */
    u8 con[KC];                         /* the contest (type 1) */
};
struct gp_state {
    u16 magic; u8 season, nsim;         /* the early simulations: */
    u8 sdiv[SD], pad[2];
    struct gp_srow srow[SD][GT];
    struct gp_ko ko[2];
    struct gp_dec dec[3];               /* 4.0 ARG: the stage titles decided mid-season (by stage: 0, 1, 2) */
    u8 pend, pweek, pseas, pad3;        /* 'then_build': play-off pend - 1 to build at the calendar advance from week
                                           pweek on (gp_adv), this season's */
};
struct gp_state GP_ST;
extern const u8 *GP_CFB;
struct gp_gs { u8 sdiv[GSD], pad; struct gp_srow srow[GSD][GSR]; };   /* the early tables beyond SD (a group contest:
                                           the Poule's 8 other groups; the engine block's item 'GS') */
struct gp_gs GP_GS;
struct gp_log { u32 tag; u8 seas, stseas, pl_pi, pad; struct gp_ko ko; struct gp_out out; } GP_LOG;
                                        /* the last season end's (harness): its season, the state's, the played one */
/* set by the glue */
u8 GP_HDR[14] = { 0xAD };               /* (gplay.py: the game's Australian cup header, no draw, no away goals) */
const u32 *GP_NM;                       /* the country's names: per play-off dd long, short, record (relative) */
const u8 *GP_TH;                        /* the country's 'then_build': per play-off the next one's index + 1, or 0 */
u8 *GP_DIYP;
u32 GP_K, GP_W, GP_SKIP, GP_RB;
u16 GP_A, GP_B;
u8 GP_CID, GP_SEAS, GP_DIV, GP_PT[64], GP_PL[64];
static const struct gp_dec *stage_dec(int k) {
    return k < 3 && GP_ST.magic == MAGIC && GP_ST.dec[k].season == GP_SEAS && GP_ST.dec[k].done ? &GP_ST.dec[k] : 0;
}

#define KDV(k, i) ((k)->code[i] / GT)
#define KPL(k, i) ((k)->code[i] % GT)
static int kbetter(const struct gp_ko *k, int a, int b) { return k->prio[a] < k->prio[b]; }

static const u8 *po_at(int pi) {        /* the country's play-off pi in GP_IN.spec */
    const u8 *s = GP_IN.spec;
    for (; s && *s; pi--) {
        if (!pi) return s;
        int n = s[1], nr = s[2];
        const u8 *r = s + 6 + 4 * n;
        for (int k = 0; k < nr; k++) r += 6 + 2 * r[0];
        s = r;
    }
    return 0;
}

static int ent_club(const u8 *e) {     /* an entrant -> its club (division * GT + place), or -1 */
    if (e[0] == 3) return stage_club(e[1], e[3], e[2]);
    if (e[0] || e[1] >= GP_IN.nd || e[1] >= GD || e[2] < 1 || e[2] > GP_IN.n[e[1]]) return -1;
    return e[1] * GT + e[2] - 1;
}

static int playable(const u8 *s) {      /* knockouts only (promotion, placement, playout, title, continental), entrants [div, place]
                                           or stage places, members entrants / W / L */
    int n = s[1], nr = s[2], nt = 0;
    const u8 *e = s + 6, *r = e + 4 * n;
    if ((s[0] < 1 || (s[0] > 6 && s[0] != K_STAGE) || s[0] == 2) || n > KN || nr > KR || nr < 1) return 0;   /* (not 'europe': uefaq's) */
    for (int i = 0; i < n; i++)
        if (e[4 * i] != 0 && e[4 * i] != 3) return 0;     /* (type 5, the Trofeo: at the season end only) */
    for (int k = 0; k < nr; k++) {
        if (r[1] < 1 || r[1] > 3 || (r[1] == 3 && k == nr - 1)) return 0;   /* (no group round; a series: not last) */
        for (int i = 0; i < 2 * r[0]; i++)
            if ((r[6 + i] >= BEST_LOSER && r[6 + i] < 0x80) || (k == 0 && r[6 + i] >= 0x80)) return 0;
        nt += r[0];
        r += 6 + 2 * r[0];
    }
    return nt <= KT;
}

/* test builds (GPLAY_FORCE=k): the league's own final table too (competitionFileBuffer at GP_CFB, before gp_need): the
   career club's row and place k's swap their figures and places, so the game's own moves see the forced place */
void gp_forcecfb(void) {
    u8 *d = (u8 *)GP_CFB;
    int n = *(u16 *)(d + 0x31), m = -1;
    if (!GP_FORCE || GP_FORCE > n) return;
    for (int j = 0; j < n; j++)
        if (*(u16 *)(d + 0x12D + 2 * (*(u16 *)(d + 0x6D + 2 * j) / 0x12)) == GP_IN.mgr) m = j;
    if (m < 0 || m == GP_FORCE - 1) return;
    u16 *pa = (u16 *)(d + 0x6D + 2 * m), *pb = (u16 *)(d + 0x6D + 2 * (GP_FORCE - 1));
    u16 *ra = (u16 *)(d + *pa + 0x2B7), *rb = (u16 *)(d + *pb + 0x2B7), x;
    for (int i = 0; i < 7; i++) { x = ra[i]; ra[i] = rb[i]; rb[i] = x; }
    x = *pa; *pa = *pb; *pb = x;
}

/* a group contest (the Poule Scudetto): a title whose rounds are g groups of m entrants (one meeting count), then
   optional ranking rounds, then knockout rounds (single / two legs) whose first takes q placings; played as the game's
   type-2 contest in slot 3 (groups -> q qualifiers: the winners, then the best runners-up as the game's best thirds;
   then its knockout stages). o: stages for the contest header, or 0 (a check). */
struct t2s { u8 g, m, meet, nk, q, kt[4], kb[4]; };
static int t2_shape(const u8 *s, struct t2s *o) {
    struct t2s x;
    int n = s[1], nr = s[2], k = 0, ent = 0;
    const u8 *r = s + 6 + 4 * n;
    if (s[0] != K_TITLE || nr < 2) return 0;
    for (int i = 0; i < n; i++) if (s[6 + 4 * i] != 0) return 0;
    x.g = 0; x.m = 0; x.meet = 0; x.nk = 0; x.q = 0;
    for (; k < nr && (r[1] & 0x80) && (r[1] & 0x7F); k++) {      /* the groups */
        if (x.g && (r[0] != x.m || (r[1] & 0x7F) != x.meet)) return 0;
        x.m = r[0]; x.meet = r[1] & 0x7F; x.g++;
        for (int i = 0; i < r[0]; i++) if (r[6 + i] != ent++) return 0;   /* (entrants in order, group by group) */
        r += 6 + 2 * r[0];
    }
    for (; k < nr && r[1] == 0x80; k++) r += 6 + 2 * r[0];        /* (ranking rounds: the game's best runners-up) */
    for (; k < nr; k++) {                                          /* the knockout stages */
        if ((r[1] & 0x80) || r[1] < 1 || r[1] > 2 || x.nk >= 4) return 0;
        if (!x.nk) x.q = 2 * r[0];
        x.kt[x.nk] = r[0];
        x.kb[x.nk++] = (r[1] == 2 ? 0x80 : 0x01) | (r[3] == LV_PENS ? 0x04 : r[3] == LV_ET_PENS ? 0x14 :
                                                    r[3] == LV_ET_BETTER ? 0x10 : 0);
        r += 6 + 2 * r[0];
    }
    if (x.g < 2 || !x.nk || ent != n || x.q < x.g || x.q > 2 * x.g || x.g * x.m > KN) return 0;
    if (o) *o = x;
    return 1;
}

/* the career club's league has ended (GP_IN.t[mdiv] its table, mgr, week, gtype): the play-offs it plays (pi[]) and
   the divisions to simulate now for their entrants (sim[]); returns how many */
u32 gp_need(void) {
    int m = -1, d0 = GP_IN.mdiv, cnt = 0, ns = 0;
    GP_IN.pi[0] = GP_IN.pi[1] = NOC;
    for (int j = 0; j < SDX; j++) GP_IN.sim[j] = NOC;
    GP_ST.nsim = 0;
    for (int k = 0; k < GP_IN.n[d0]; k++) if (GP_IN.t[d0][k].team == GP_IN.mgr) m = k;
    if (GP_FORCE) { int f = gp_force(); if (f >= 0) m = f; }
    if (GP_IN.gtype == 4 && m < 0) return 0;
    for (int pi = 0; cnt < (GP_IN.gtype == 4 ? 1 : 2); pi++) {
        const u8 *s = po_at(pi), *e = s ? s + 6 : 0;
        if (!s) break;
        if ((!playable(s) && !(GP_IN.gtype == 4 && t2_shape(s, 0))) || s[0] == K_STAGE) continue;
                                                    /* (stage titles: gp_build, mid-season; a group contest: careers) */
        int in = 0, all = 1;
        for (int i = 0; i < s[1]; i++) {
            int c = ent_club(e + 4 * i);
            if (e[4 * i] == 0 ? e[4 * i + 1] == d0 && e[4 * i + 2] == m + 1 : c == d0 * GT + m) in = 1;
            if (e[4 * i + 1] != d0) all = 0;
        }
        if (GP_IN.gtype == 4 ? !in : !all) continue;    /* (Season: the division's own play-offs, no other loaded) */
        int ok = 1;
        for (int i = 0; i < s[1] && ok; i++) {          /* the other divisions: simulated now (at most SDX) */
            int d = e[4 * i + 1], j = 0;
            if (d == d0) continue;
            while (j < ns && GP_IN.sim[j] != d) j++;
            if (j == ns) { if (ns < (t2_shape(s, 0) ? SDX : SD)) GP_IN.sim[ns++] = d; else ok = 0; }
        }
        if (ok) GP_IN.pi[cnt++] = pi;
    }
    return cnt;
}

/* early simulation of division GP_DIV (DIY at GP_DIYP): its rows into the state, place by place */
void gp_simkeep(void) {
    const u8 *d = GP_DIYP;
    int n = *(const u16 *)(d + 0x31), j = GP_ST.nsim, nr = j < SD ? GT : GSR;
    if (j >= SDX) return;
    if (j < SD) GP_ST.sdiv[j] = GP_DIV; else GP_GS.sdiv[j - SD] = GP_DIV;
    GP_ST.nsim = j + 1;
    for (int k = 0; k < nr; k++) {
        struct gp_srow *s = j < SD ? &GP_ST.srow[j][k] : &GP_GS.srow[j - SD][k];
        s->team = 0;
        if (k >= n) continue;
        int off = *(const u16 *)(d + 0x6D + 2 * k), i = off / 0x12;
        const u16 *r = (const u16 *)(d + off + 0x2B7);
        s->team = *(const u16 *)(d + 0x12D + 2 * i);
        s->played = r[0]; s->won = r[1]; s->drawn = r[2]; s->lost = r[3]; s->gf = r[4]; s->ga = r[5]; s->pts = r[6];
    }
}

/* the season end simulated division GP_DIV again (DIY at GP_DIYP): an early one gets its results back */
void gp_restore(void) {
    u8 *d = GP_DIYP;
    int n = *(u16 *)(d + 0x31);
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS) return;
    for (int j = 0; j < GP_ST.nsim && j < SDX; j++) {
        if ((j < SD ? GP_ST.sdiv[j] : GP_GS.sdiv[j - SD]) != GP_DIV) continue;
        const struct gp_srow *s = j < SD ? GP_ST.srow[j] : GP_GS.srow[j - SD];
        for (int k = 0; k < n && k < (j < SD ? GT : GSR); k++)
            for (int i = 0; i < n; i++)
                if (*(u16 *)(d + 0x12D + 2 * i) == s[k].team) {
                    u16 *r = (u16 *)(d + 0x2B7 + 0x12 * i);
                    r[0] = s[k].played; r[1] = s[k].won; r[2] = s[k].drawn; r[3] = s[k].lost;
                    r[4] = s[k].gf; r[5] = s[k].ga; r[6] = s[k].pts;
                    *(u16 *)(d + 0x6D + 2 * k) = 0x12 * i;
                }
    }
}

static int member(const struct gp_ko *k, int c) {      /* a member code -> list index, or -1 (not decided yet) */
    if (c < BEST_LOSER) return c < k->n ? k->ient[c] : -1;
    if (c < 0x80) return -1;            /* (group placings, the best loser: not played here) */
    int t = c & 0x3F;
    if (t >= k->ntie) return -1;
    int v = c & 0x40 ? k->tl[t] : k->tw[t];
    return v == NOC ? -1 : v;
}

static void resolve(struct gp_ko *k) {  /* ties decided by their pairs: the last one's winner, a series' 2 wins */
    for (int t = 0; t < k->ntie; t++) {
        int w = NOC, c[2] = { NOC, NOC }, x[2] = { 0, 0 };
        if (k->tw[t] != NOC) continue;
        for (int p = 0; p < k->gp0[k->gcur + 1]; p++) {
            if (k->ptie[p] != t || k->pw[p] == NOC) continue;
            if (c[0] == NOC) { c[0] = k->pa[p]; c[1] = k->pb[p]; }
            x[k->pw[p] == c[1]]++;
            w = k->pw[p];
        }
        int sr = 0;
        while (sr + 1 < k->nrs && k->gt0[sr + 1] <= t) sr++;
        if (k->rs[sr][1] == 3) w = x[0] >= 2 ? c[0] : x[1] >= 2 ? c[1] : NOC;
        if (w == NOC) continue;
        k->tw[t] = w;
        k->tl[t] = w == c[0] ? c[1] : c[0];
    }
}

static u32 hseed(const struct gp_ko *k, int g) {
    u32 h = g * 7919u + k->pi;
    for (int i = 0; i < k->n; i++) h = h * 31 + k->team[i];
    return h;
}

/* game round g's pairs (from k->gp0[g]); returns how many (0: nothing to play) */
static int build_game(struct gp_ko *k, int g) {
    int r = k->gsr[g], ties = k->rs[r][0], legs = k->rs[r][1], host = k->rs[r][2] & 0x7F, pairing = k->rs[r][4];
    int t0 = k->gt0[r], np = k->gp0[g], mem[2 * KT];
    rng = hseed(k, g);
    if (k->gno[g]) {                    /* a series' game 2 / 3: the ties not decided yet */
        for (int i = 0; i < ties; i++) {
            int t = t0 + i, a = NOC, b = NOC;
            if (k->tw[t] != NOC) continue;
            for (int p = 0; p < np; p++) if (k->ptie[p] == t) { a = k->pa[p]; b = k->pb[p]; }
            if (a == NOC || np >= KP) continue;
            if (kbetter(k, b, a)) { int x = a; a = b; b = x; }      /* (a = the better placed) */
            k->pa[np] = k->gno[g] == 1 ? b : a; k->pb[np] = k->gno[g] == 1 ? a : b;
            k->pw[np] = NOC; k->ptie[np++] = t;
        }
        k->gp0[g + 1] = np;
        return np - k->gp0[g];
    }
    for (int i = 0; i < 2 * ties; i++) {
        mem[i] = member(k, k->rc[2 * t0 + i]);
        if (mem[i] < 0) return 0;
    }
    if (pairing & 0x80) {               /* a draw: the first p members shuffled */
        int pn = (pairing & 0x7F) <= 2 * ties ? pairing & 0x7F : 2 * ties;
        for (int i = pn - 1; i > 0; i--) { int j = below(i + 1), x = mem[i]; mem[i] = mem[j]; mem[j] = x; }
    } else if (pairing) {               /* best v worst: sorted, the worst first */
        int pn = pairing <= 2 * ties ? pairing : 2 * ties, tmp[2 * KT];
        for (int i = 1; i < pn; i++) {
            int x = mem[i], j = i;
            while (j > 0 && kbetter(k, x, mem[j - 1])) { mem[j] = mem[j - 1]; j--; }
            mem[j] = x;
        }
        for (int i = 0; i < pn / 2; i++) { tmp[2 * i] = mem[pn - 1 - i]; tmp[2 * i + 1] = mem[i]; }
        for (int i = 0; i < pn; i++) mem[i] = tmp[i];
    }
    for (int i = 0; i < ties; i++) {
        int t = t0 + i, a = mem[2 * i], b = mem[2 * i + 1], gap = k->rs[r][5];
        if (k->tw[t] != NOC) continue;  /* (decided by the gap rule) */
        if (k->code[a] == k->code[b]) { k->tw[t] = k->tl[t] = a; continue; }   /* (skip_if_same: one CLUB twice
                                           (two entrants, e.g. the Trofeo's R1 = R2): no tie) */
        if (g == 0 && gap) {
            int d = (int)k->pts[a] - (int)k->pts[b];
            if (d >= gap || -d >= gap) { k->tw[t] = kbetter(k, a, b) ? a : b; k->tl[t] = k->tw[t] == a ? b : a; continue; }
        }
        int bt = kbetter(k, a, b) ? a : b, wo = bt == a ? b : a;
        if (legs == 3 || host == HOST_NEUTRAL) { a = bt; b = wo; }   /* (no neutral grounds: the better placed's) */
        else if (host == HOST_BETTER) { a = legs == 2 ? wo : bt; b = legs == 2 ? bt : wo; }
        else if (host == HOST_DRAWN && below(2)) { int x = a; a = b; b = x; }
        if (np >= KP) break;
        k->pa[np] = a; k->pb[np] = b; k->pw[np] = NOC; k->ptie[np++] = t;
    }
    k->gp0[g + 1] = np;
    return np - k->gp0[g];
}

static u8 rbyte(int legs, int level) {  /* (away goals: the contest's header, gp_lend_c) */
    static const u8 lv[6] = { LV_BITS_BETTER, LV_BITS_ET_PENS, LV_BITS_ET, LV_BITS_PENS, LV_BITS_ET_PENS,
                              LV_BITS_BETTER };
    return (legs == 2 ? 0x80 : 0x01) | lv[level < 6 ? level : 1];
}

/* a group contest (t2_shape) as the game's type 2 in slot 3: the entrants in group order, the Champions Cup's header
   with its stages (groups of m, q qualifiers; the knockout stages), weeks after the league's last; its result: the
   last decisive match's clubs (gp_rec_c: tw[0] / tl[0], the final's) */
u8 GP_HDR2[0x27] = { 0xAD };            /* (gplay.py: the Champions Cup's first 0x27 bytes) */
#define KT2(k) ((k)->bye[7])            /* (a type-2 contest: bye[] is unused there) */
static int ko_t2(struct gp_ko *k, const u8 *s, int pi, int cid, const struct t2s *x) {
    const u8 *e = s + 6;
    int n = s[1], me = 0, len = 0x27, days = x->meet * (x->m & 1 ? x->m : x->m - 1);
    k->magic = 0;
    k->slot = 3; k->cid = cid; k->pi = pi; k->kind = s[0]; k->n = n; k->nrs = s[2]; k->ldiv = s[4];
    k->ntie = 1; k->ngr = 0; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int i = 0; i < 8; i++) k->bye[i] = 0;
    KT2(k) = 1;
    *(u32 *)k->bye = GP_NM[3 * pi + 2]; /* (its record line's name: a type-2 contest has no byes) */
    for (int i = 0; i < n; i++) {
        int c = ent_club(e + 4 * i);
        if (c < 0) return 0;
        k->ient[i] = i; k->code[i] = c; k->prio[i] = c > 255 ? 255 : c;
        k->team[i] = row(c)->team; k->pts[i] = row(c)->pts;
        me |= k->team[i] == GP_IN.mgr;
    }
    for (int i = 0; i < x->nk; i++) days += (x->kb[i] & 0x80) ? 2 : 1;
    k->lfile = k->team[0] & 0xFF;
    k->d1 = GP_IN.week + 1; k->d2 = GP_IN.week + days + 1 > 255 ? 255 : GP_IN.week + days + 1;
    u8 *c = k->con;
    for (int i = 0; i < 0x27; i++) c[i] = GP_HDR2[i];
    c[0] = cid; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2;
    c[5] = 0x22; c[7] = 0x28; c[8] = 1; c[9] = 0; c[10] = 0;     /* names at +27h, the list at +2Fh, no seeding, no
                                                                   away goals */
    c[11] = x->meet;
    u8 st[0x14];
    int ns = 0;
    st[ns++] = 1 + x->nk; st[ns++] = n;
    st[ns++] = x->g; st[ns++] = x->m; st[ns++] = x->q;
    for (int i = 0; i < x->nk; i++) { st[ns++] = 0; st[ns++] = 2 * x->kt[i]; st[ns++] = x->kt[i]; }
    for (int i = 0; i < 0x14; i++) c[0x0E + i] = i < ns ? st[i] : 0;
    for (int i = 0; i < 5; i++) c[0x22 + i] = i == 0 || i > x->nk ? 0 : x->kb[i - 1];
    for (int i = 0; i < 8; i++) c[len + i] = ((const u8 *)GP_NM)[12 * pi + i];
    len += 8;
    for (int j = 0; j < n; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    if (GP_IN.gtype == 4 && !me) { k->slot = 0; k->cid = 0; return 0; }
    return 1;
}

/* a contest for play-off pi in slot `slot` (id cid): k filled, 1 if there is something to play */
static int ko_build(struct gp_ko *k, int pi, int slot, int cid) {
    const u8 *s = po_at(pi), *e = s + 6, *r = e + 4 * s[1];
    int n = s[1];
    struct t2s x;
    if (GP_IN.gtype == 4 && t2_shape(s, &x)) return ko_t2(k, s, pi, 0xFE, &x);   /* (career: slot 3, id FE) */
    k->bye[5] = k->bye[6] = k->bye[7] = 0;              /* (KT2: a knockout) */
    k->magic = 0;
    k->slot = slot; k->cid = cid; k->pi = pi; k->kind = s[0]; k->n = n; k->nrs = s[2]; k->ldiv = s[4];
    k->ntie = 0; k->ngr = 0; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int j = 0; j < k->nrs; j++) {
        for (int i = 0; i < 6; i++) k->rs[j][i] = r[i];
        k->gt0[j] = k->ntie;
        for (int i = 0; i < 2 * r[0]; i++) k->rc[2 * k->ntie + i] = r[6 + i];
        k->ntie += r[0];
        int games = r[1] == 3 ? 3 : 1;
        for (int g = 0; g < games && k->ngr < KG; g++) {
            k->gsr[k->ngr] = j; k->gno[k->ngr] = g;
            k->rb[k->ngr++] = rbyte(r[1] == 3 ? 1 : r[1], r[3]);
        }
        r += 6 + 2 * r[0];
    }
    k->gt0[k->nrs] = k->ntie;
    /* the list: round 1's members in tie order, then the others in entrant order */
    for (int i = 0; i < n; i++) {
        int c = ent_club(e + 4 * i);
        if (c < 0) return 0;
        k->ient[i] = i; k->code[i] = c;
        k->prio[i] = e[4 * i] == 3 ? e[4 * i + 2] - 1 : c > 255 ? 255 : c;   /* (stage entrants: the stage place) */
        k->team[i] = row(c)->team; k->pts[i] = row(c)->pts;
    }
    k->gp0[0] = 0;
    int g0 = 0, np0 = build_game(k, 0);     /* (entrant indices for now: the list order next) */
    while (np0 <= 0 && g0 + 1 < k->ngr && k->gno[g0 + 1] == 0) np0 = build_game(k, ++g0);   /* (a round decided
                                               without a match, skip_if_same / gap: the first with one is round 1) */
    if (np0 <= 0) {                         /* (every tie decided by the gap: nothing to play, the results kept) */
        for (int i = 0; i < n; i++) k->team[i] = row(k->code[i])->team;
        k->slot = 0; k->cid = 0; k->season = GP_SEAS; k->magic = MAGIC;
        return 0;
    }
    u8 used[KN], order[KN], pr[KN];
    u16 cd[KN];
    for (int i = 0; i < n; i++) { cd[i] = k->code[i]; pr[i] = k->prio[i]; }
    int m = 0;
    for (int i = 0; i < n; i++) used[i] = 0;
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++) {
        order[m++] = k->pa[p]; used[k->pa[p]] = 1;
        order[m++] = k->pb[p]; used[k->pb[p]] = 1;
    }
    int np1 = m;
    for (int i = 0; i < n; i++) if (!used[i]) order[m++] = i;
    for (int j = 0; j < n; j++) {       /* list index j = entrant order[j] */
        int i = order[j];
        k->ient[i] = j;
        k->code[j] = cd[i]; k->prio[j] = pr[i];
        const struct gp_row *w = row(cd[i]);
        k->team[j] = w->team; k->pts[j] = w->pts;
    }
    for (int p = 0; p < k->gp0[g0 + 1]; p++) { k->pa[p] = k->ient[k->pa[p]]; k->pb[p] = k->ient[k->pb[p]]; }
    for (int t = 0; t < k->ntie; t++) {         /* (gap-decided ties, entrant indices too) */
        if (k->tw[t] != NOC) { k->tw[t] = k->ient[k->tw[t]]; k->tl[t] = k->ient[k->tl[t]]; }
    }
    int me = 0;                         /* a career: the club must play round 1 (a slot-4 contest without it stops the
                                           season); else no contest, its gap-decided tie kept (gp_sack, gp_played_c) */
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++)
        me |= k->team[k->pa[p]] == GP_IN.mgr || k->team[k->pb[p]] == GP_IN.mgr;
    int days = 0;
    for (int g = g0; g < k->ngr; g++) days += (k->rb[g] & 0xC0) == 0x80 ? 2 : 1;
    k->gcur = g0;
    k->bye[5] = GP_TH ? GP_TH[pi] : 0;  /* (pack 'then_build': the play-off built when this one ends, index + 1) */
    k->lfile = k->team[0] & 0xFF;
    k->d1 = GP_IN.week + 1; k->d2 = GP_IN.week + days > 255 ? 255 : GP_IN.week + days;
    k->bye[0] = cid; k->bye[1] = 0xFF; k->bye[2] = n; k->bye[3] = n - np1; k->bye[4] = k->ngr - g0;
    /* the contest: the game's header, round bytes, names, the team words */
    u8 *c = k->con;
    int len = 14;
    for (int i = 0; i < 14; i++) c[i] = GP_HDR[i];
    c[0] = cid; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2; c[10] = n;
    for (int j = 0; j < k->nrs; j++)    /* away goals (levels away_pens / away_better): the whole contest's */
        if (k->rs[j][3] == LV_AWAY_PENS || k->rs[j][3] == LV_AWAY_BETTER) c[13] = 0;
    for (int g = g0; g < k->ngr; g++) c[len++] = k->rb[g];
    c[len++] = 0;
    c[5] = len - 5;
    c[7] = len + 8 - 7;
    for (int i = 0; i < 8; i++) c[len + i] = ((const u8 *)GP_NM)[12 * pi + i];
    len += 8;
    for (int j = 0; j < n; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    if (GP_IN.gtype == 4 && !me) { k->slot = 0; k->cid = 0; return 0; }
    return 1;
}

/* after gp_need and the early simulations: the contests (ko[0]: slot 4, id FE; Season's second: slot 3, FC) */
u32 gp_lend_c(void) {
    u32 built = 0;
    GP_ST.magic = MAGIC;
    GP_ST.season = GP_SEAS;
    for (int i = 0; i < 2; i++) {
        GP_ST.ko[i].magic = 0;
        if (GP_IN.pi[i] != NOC && ko_build(&GP_ST.ko[i], GP_IN.pi[i], i ? 3 : 4, i ? 0xFC : 0xFE)) built |= 1 << i;
    }
    return built;
}

/* a knockout not built (the career club not in round 1): every tie simulated now with gplay's tie rules (4.0's
   gp_build: the champion = team[tw[last tie]], the runner-up team[tl[...]] at once) */
static void ko_sim(struct gp_ko *k) {
    int g = 0;
    for (;;) {
        for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++) {
            if (k->pw[p] != NOC) continue;
            int r = k->gsr[g], a = k->code[k->pa[p]], b = k->code[k->pb[p]];
            int w = tie(a, b, k->rs[r][1] == 2 ? 2 : 1, HOST_LISTED, k->rs[r][3]);
            k->pw[p] = w == a ? k->pa[p] : k->pb[p];
        }
        k->gcur = g;
        resolve(k);
        while (++g < k->ngr && build_game(k, g) <= 0)
            ;
        if (g >= k->ngr) break;
    }
}

/* gp_build (mid-season): play-off GP_BPIC of the spec into slot 4 when its entrants' tables are captured */
u32 GP_BPIC;
static u16 team_glob(u16 team) {        /* a team word -> its global number (the captured tables), 0xFFFF */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].team == team) return GP_IN.t[d][k].glob;
    return 0xFFFF;
}

static void stage_done(const struct gp_ko *k) {   /* a stage title's knockout decided: GP_ST.dec[stage] */
    const u8 *s = k->magic == MAGIC && k->season == GP_SEAS && k->ntie ? po_at(k->pi) : 0;
    int t = k->ntie - 1;
    if (!s || s[0] != K_STAGE || s[3] >= 3 || k->tw[t] == NOC) return;
    struct gp_dec *x = &GP_ST.dec[s[3]];
    int w = k->tw[t], l = k->tl[t];
    x->season = GP_SEAS; x->done = 1;
    x->team[0] = k->team[w]; x->glob[0] = team_glob(k->team[w]);
    x->team[1] = l != NOC ? k->team[l] : 0xFFFF; x->glob[1] = l != NOC ? team_glob(k->team[l]) : 0xFFFF;
}

u32 GP_WK;                              /* (the glue: the current calendar entry's week) */
static void set_pend(int then, int week) {   /* 'then_build': the next play-off at the calendar advance from week on */
    GP_ST.pend = then; GP_ST.pweek = week > 255 ? 255 : week; GP_ST.pseas = GP_SEAS;
}

u32 gp_build_c(void) {
    const u8 *s = po_at(GP_BPIC);
    stage_done(&GP_ST.ko[0]);                   /* (the previous stage's knockout, played: before ko[0] is rebuilt) */
    if (!s || !playable(s)) return 0;
    for (int i = 0; i < s[1]; i++) {
        const u8 *e = s + 6 + 4 * i;
        if (e[2] > GP_IN.n[e[1]]) return 0;
    }
    GP_ST.nsim = 0;
    GP_IN.pi[0] = GP_BPIC; GP_IN.pi[1] = NOC;
    u32 b = gp_lend_c() & 1;
    if (!b && GP_ST.ko[0].magic == MAGIC) {
        ko_sim(&GP_ST.ko[0]);
        stage_done(&GP_ST.ko[0]);               /* (simulated at once: decided now) */
        if (GP_ST.ko[0].bye[5]) { set_pend(GP_ST.ko[0].bye[5], GP_ST.ko[0].d2); GP_ST.ko[0].bye[5] = 0; }
    }                                           /* ('then_build' after the simulated final's week) */
    return b;
}
const u32 GP_KOLAY[] = { __builtin_offsetof(struct gp_state, ko), sizeof(struct gp_ko),
                         __builtin_offsetof(struct gp_ko, slot), __builtin_offsetof(struct gp_ko, ntie),
                         __builtin_offsetof(struct gp_ko, tw), __builtin_offsetof(struct gp_ko, tl),
                         __builtin_offsetof(struct gp_ko, team), __builtin_offsetof(struct gp_ko, n) };

/* the contest in DIY (id GP_CID) is ours: its ko index, else -1 */
int gp_ours_c(void) {
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS) return -1;
    for (int i = 0; i < 2; i++)
        if (GP_ST.ko[i].magic == MAGIC && GP_ST.ko[i].slot && GP_ST.ko[i].cid == GP_CID && GP_ST.ko[i].season == GP_SEAS)
            return i;
    return -1;
}

static int kidx(const struct gp_ko *k, u16 team) {
    for (int i = 0; i < k->n; i++) if (k->team[i] == team) return i;
    return NOC;
}

/* lib97 nc_adv (gp_perm): GP_PT = the winners of the round just played in tie order -> GP_PL = the next round's
   list, GP_RB its round byte, GP_SKIP game rounds skipped (a game 3 nobody needs); returns its clubs (0: none) */
u32 gp_perm_c(void) {
    struct gp_ko *k = &GP_ST.ko[GP_K];
    if (KT2(k)) return 0;               /* (a type-2 contest: the game's own stages) */
    int g = k->gcur, p0 = k->gp0[g], np = k->gp0[g + 1] - p0, c = 0;
    for (int i = 0; i < np && i < 64; i++) k->pw[p0 + i] = GP_PT[i];
    resolve(k);
    GP_SKIP = 0;
    for (;;) {
        if (++g >= k->ngr) return 0;
        c = build_game(k, g);
        if (c > 0) break;
        GP_SKIP++;
    }
    k->gcur = g;
    for (int i = 0; i < c; i++) { GP_PL[2 * i] = k->pa[k->gp0[g] + i]; GP_PL[2 * i + 1] = k->pb[k->gp0[g] + i]; }
    GP_RB = k->rb[g];
    return 2 * c;
}

/* a decisive match of ours (GP_A v GP_B, GP_W = 1: the second won): its pair's winner */

void gp_defer_c(void) {                 /* (gp_defer: play-off GP_BPIC built at the calendar advance from week GP_WK on) */
    set_pend(GP_BPIC + 1, GP_WK);
}

/* the calendar advance (gp_adv, cseg_8EA82's callers): a pending 'then_build' due -> its play-off index + 1 (then
   gp_build with GP_BWEEK = this week), else 0 */
u32 gp_adv_c(void) {
    if (!GP_ST.pend || GP_ST.pseas != GP_SEAS || GP_WK < GP_ST.pweek) return 0;
    u32 t = GP_ST.pend;
    GP_ST.pend = 0;
    return t;
}

void gp_rec_c(void) {
    struct gp_ko *k = &GP_ST.ko[GP_K];
    int a = kidx(k, GP_A), b = kidx(k, GP_B), g = k->gcur;
    if (KT2(k)) {                       /* a type-2 contest: the last decisive match (the final's, at the end) */
        if (a != NOC && b != NOC) { k->tw[0] = GP_W ? b : a; k->tl[0] = GP_W ? a : b; }
        return;
    }
    for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++)
        if ((k->pa[p] == a && k->pb[p] == b) || (k->pa[p] == b && k->pb[p] == a)) k->pw[p] = GP_W ? b : a;
    resolve(k);
    if (k->bye[5] && k->ntie && k->tw[k->ntie - 1] != NOC) {   /* (its final decided: the next one, once, from the
                                           week after: the advance right after the final still has slot 4's contest
                                           in hand, a build there was lost - 4.0's Trofeo) */
        set_pend(k->bye[5], GP_WK + 1);
        k->bye[5] = 0;
    }
}

/* a level tie of ours with no penalties: 1 if the second club (GP_B) goes through, the better placed */
u32 gp_draw_c(void) {
    const struct gp_ko *k = &GP_ST.ko[GP_K];
    int a = kidx(k, GP_A), b = kidx(k, GP_B);
    if (KT2(k)) return 0xFFFFFFFF;      /* (a type-2 contest: the game's rules) */
    return a != NOC && b != NOC && kbetter(k, b, a);
}

/* the season end, before gp_season: the career club's played play-off (ko 0) -> GP_IN.pl_*; and the log */
void gp_played_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    GP_IN.pl_pi = 0;
    GP_IN.pl_t2 = 0;
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS || k->magic != MAGIC || k->season != GP_SEAS) return;
    GP_IN.pl_pi = k->pi + 1;
    GP_IN.pl_t2 = KT2(k);
    if (KT2(k)) {                       /* a type-2 contest: its champion / runner-up */
        for (int t = 0; t < KT; t++) GP_IN.pl_w[t] = 0;
        GP_IN.pl_w[0] = k->tw[0] != NOC ? k->team[k->tw[0]] : 0;
        GP_IN.pl_w[1] = k->tl[0] != NOC ? k->team[k->tl[0]] : 0;
        return;
    }
    resolve(k);
    for (int t = 0; t < KT; t++) GP_IN.pl_w[t] = t < k->ntie && k->tw[t] != NOC ? k->team[k->tw[t]] : 0;
}

void gp_end_c(void) {                   /* after gp_season: the log, the state void */
    const u8 *s = (const u8 *)&GP_ST.ko[0];
    u8 *d = (u8 *)&GP_LOG.ko;
    if (GP_ST.magic == MAGIC || GP_IN.pl_pi) {
        for (u32 i = 0; i < sizeof GP_LOG.ko; i++) d[i] = s[i];
        s = (const u8 *)&GP_OUT; d = (u8 *)&GP_LOG.out;
        for (u32 i = 0; i < sizeof GP_LOG.out; i++) d[i] = s[i];
        GP_LOG.seas = GP_SEAS; GP_LOG.stseas = GP_ST.season; GP_LOG.pl_pi = GP_IN.pl_pi;
        GP_LOG.tag = 0x474C5047;        /* 'GPLG' */
    }
    GP_ST.magic = 0;
    GP_ST.nsim = 0;
    GP_ST.ko[0].magic = GP_ST.ko[1].magic = 0;
    GP_IN.pl_pi = 0;
}

/* SeasonFinished's contract check (gp_sack): the career club relegated into the reserve (loser_div 'reserve', the
   reserve below the lowest level: pgroups' RS_TAB) is sacked, with job offers - directly (a reserve country's club
   in a division >= its lowest level, placed below teams - relegated) or by the played play-out it lost. */
const u8 *GP_CFB, *GP_LG, *GP_RST, *GP_RIT;   /* the league's final table, its struct, RS_TAB, RI_TAB (0: none) */
const s8 *GP_SLT;                       /* someLeaguesTable (the clubs' divisions: base + delta) */
u32 GP_SEL;                             /* selTeamsPtr */
u16 GP_MGR;
u8 GP_WORLD;

/* SeasonFinished (gp_sack, before the season review): the career club won our played group contest (the Poule) ->
   its record line's name (the season record's 4th line: a Serie D club plays no European cup), else 0. Test builds
   (GPLAY_FORCE): the club is made the winner (the review's DA11B too: no European trophy for it, gp_sack's guard). */
u32 gp_pwin_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS || k->magic != MAGIC || k->season != GP_SEAS || !KT2(k))
        return 0;
    int me = kidx(k, GP_MGR);
    if (me == NOC) return 0;
    if (GP_FORCE) { k->tw[0] = me; k->tl[0] = me ? 0 : 1; }
    return k->tw[0] == me ? *(u32 *)k->bye : 0;
}

u32 gp_sack_c(void) {
    const struct gp_ko *k = &GP_ST.ko[0];
    if (GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS && k->magic == MAGIC && k->season == GP_SEAS && k->kind == 4
        && k->ldiv == RESERVE) {        /* (a play-out into the reserve, played: its last round's losers) */
        int r = k->nrs - 1;
        for (int t = k->gt0[r]; t < k->gt0[r + 1]; t++)
            if (k->tl[t] != NOC && k->team[k->tl[t]] == GP_MGR) return 1;
    }
    if ((!GP_RST && !GP_RIT) || !GP_CFB || !GP_LG) return 0;
    const u8 *d = GP_CFB;
    int n = *(const u16 *)(d + 0x31), m = -1, off = 0;
    for (int j = 0; j < n && j < GT; j++) {
        int o = *(const u16 *)(d + 0x6D + 2 * j);
        if (*(const u16 *)(d + 0x12D + 2 * (o / 0x12)) == GP_MGR) { m = j; off = o; }
    }
    if (m < 0) return 0;
    if (GP_FORCE) m = GP_FORCE - 1;
    u16 g = *(const u16 *)(*(const u32 *)(d + off + 0x2B3) + GP_SEL + 2);
    const u8 *t = GP_RIT;                /* the off-file pool (ripool: RI_TAB; its swap never takes the manager's club) */
    if (t && *t++ && t[0] == GP_WORLD) {
        int low = t[2], ns = t[3] | t[4] << 8;
        for (int i = 0; i < ns; i++)
            if ((t[5 + 4 * i] | t[6 + 4 * i] << 8) == g) {
                int dv = t[7 + 4 * i] + GP_SLT[g];
                return dv >= low && dv < GD && m >= n - GP_LG[13 + 6 * dv + 3];
            }
    }
    t = GP_RST;
    for (int cnt = t ? *t++ : 0; cnt > 0; cnt--) {
        int w = t[0], nd = t[1], low = t[2], nc = t[3] | t[4] << 8;
        const u8 *c = t + 5, *pl = c + 3 * nc;
        t = pl + 1 + 2 * pl[0];
        if (w != GP_WORLD) continue;
        for (int i = 0; i < nc; i++)
            if ((c[3 * i] | c[3 * i + 1] << 8) == g) {     /* its division now: base + someLeaguesTable[g] */
                int dv = c[3 * i + 2] + GP_SLT[g];
                return dv >= low && dv < nd && m >= n - GP_LG[13 + 6 * dv + 3];   /* (among its relegated) */
            }
    }
    return 0;
}

const u32 GP_LAYOUT2[] = { __builtin_offsetof(struct gp_in, mgr), __builtin_offsetof(struct gp_in, week),
                           __builtin_offsetof(struct gp_in, mdiv), __builtin_offsetof(struct gp_in, gtype),
                           __builtin_offsetof(struct gp_in, sim), sizeof(struct gp_ko),
                           __builtin_offsetof(struct gp_state, ko), __builtin_offsetof(struct gp_ko, season),
                           __builtin_offsetof(struct gp_ko, cid), __builtin_offsetof(struct gp_ko, n),
                           __builtin_offsetof(struct gp_ko, team), __builtin_offsetof(struct gp_ko, bye),
                           __builtin_offsetof(struct gp_ko, con), sizeof(struct gp_state), sizeof(struct gp_log),
                           __builtin_offsetof(struct gp_ko, slot) };

/* Parallel groups at the season end (pgroups.py: InitializeNewSeason's copy-back, leaguesTableCopy -> someLeaguesTable).
   The table: db count; per country db world, levels; per level db first division, groups, sizes[groups] (top-down,
   all the chain's divisions); db parallel levels np; dw clubs; clubs x (dw global number, db base division,
   np x db area: per level of groups its group index, 0xFF = none). The game moved each club by its division's
   promoted / relegated counts: one division up or down the chain. Here a move is one LEVEL up or down instead: into a
   single division as it is, into a level of groups to the group of the club's area for that level, else the nearest
   one with room (each group keeps its size). A division past the chain (the reserve, gplay's 'reserve') is a level of
   its own below the last one. */
enum { PL = 8, PG = 9 };                    /* (Serie D 2026-27: 9 groups) */
static u8 pg_pend[4096 / 8];                      /* (bits, by global number) */
#define PEND(g) (pg_pend[(g) >> 3] & (1 << ((g) & 7)))

static int pg_level(int d, int nl, const u8 *first, const u8 *cnt) {
    if (d >= first[nl - 1] + cnt[nl - 1]) return nl;   /* (out of the chain: the reserve) */
    for (int l = nl - 1; l >= 0; l--) if (d >= first[l]) return l;
    return 0;
}

/* The off-file pool's swapped slots this season end (ri_season, before pg_season): each enters the lowest level from
   below the chain (its identity is new) and goes to the group of the NEW identity's area. */
enum { RIO = 64 };
static u16 ri_og[RIO];
static u8 ri_oa[RIO];
static int ri_no;
static int ri_over(int g) {
    for (int i = 0; i < ri_no; i++) if (ri_og[i] == g) return i;
    return -1;
}

static const u8 *pg_one(const u8 *t, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            if (pass == 1) {                    /* into a level of groups: the area's, else the nearest with room */
                if (!PEND(g)) continue;
                pg_pend[g >> 3] &= ~(1 << (g & 7));
                int n = copy[g] + base, o = slt[g] + base;       /* (copy still the game's move) */
                int ov = ri_over(g);
                if (ov >= 0) { o = first[nl - 1] + cnt[nl - 1]; n = first[nl - 1]; }   /* (a new identity from below) */
                int lo = pg_level(o, nl, first, cnt), tl = n < o ? lo - 1 : lo + 1;
                int area = ov >= 0 ? ri_oa[ov] : pidx[tl] < npar ? e[3 + pidx[tl]] : 0xFF;
                int a = area < cnt[tl] ? area : area == 0xFF ? cnt[tl] / 2 : cnt[tl] - 1, to = a;
                for (int k = 0; k < PG; k++) {
                    if (a + k < cnt[tl] && occ[tl][a + k] < sz[tl][a + k]) { to = a + k; break; }
                    if (a - k >= 0 && occ[tl][a - k] < sz[tl][a - k]) { to = a - k; break; }
                }
                occ[tl][to]++;
                copy[g] = first[tl] + to - base;
                continue;
            }
            int o = slt[g] + base, n = copy[g] + base;
            if (ri_over(g) >= 0) { o = first[nl - 1] + cnt[nl - 1]; n = first[nl - 1]; }
            int lo = pg_level(o, nl, first, cnt);
            int tl = n < o ? lo - 1 : n > o ? lo + 1 : lo;
            if (tl < 0 || tl >= nl) continue;   /* (off the chain, or into the reserve: as moved) */
            if (tl == lo) {                     /* staying: counted in its group */
                if (o - first[lo] < cnt[lo]) occ[lo][o - first[lo]]++;
            } else if (cnt[tl] == 1)
                copy[g] = first[tl] - base;
            else
                pg_pend[g >> 3] |= 1 << (g & 7);
        }
    return c + rs * nc;
}

void pg_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pg_one(t, slt, copy, t[0] == world);
}

/* A save from before the groups (3.x: pgroups.py's table on a chain the save's divisions don't know). Every club of
   the table: its division now (base + slt), through map (old division -> new, 0xFF = the same), to its level on the
   new chain; a single division as it is, a level of groups to the group of its area, else the nearest with room (the
   clubs with an area first, so every group keeps its size). A map value 0x80 | division pins the club to exactly
   that division (4.0: a 3.x career's live 18-club league kept together for its current season), counted before the
   others are placed. copy = the result (not slt: slt is read again). */
static const u8 *pl_one(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 3; pass++)        /* 0: single divisions, 1: groups of the area, 2: the nearest */
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            int d = slt[g] + base, pin = 0;
            if (d >= 0 && d < 256 && map[d] != 0xFF) { pin = map[d] & 0x80; d = map[d] & 0x7F; }
            int l = pg_level(d, nl, first, cnt);
            if (l >= nl) { if (pass == 0) copy[g] = d - base; continue; }    /* (the reserve: as it is) */
            if (cnt[l] == 1) { if (pass == 0) copy[g] = first[l] - base; continue; }
            if (pin) {                          /* pinned (map 0x80 | division): exactly that group, counted first */
                if (pass == 0) { copy[g] = d - base; if (d - first[l] < PG) occ[l][d - first[l]]++; }
                continue;
            }
            if (pass == 0) { pg_pend[g >> 3] |= 1 << (g & 7); continue; }
            if (!PEND(g)) continue;
            int area = pidx[l] < npar ? e[3 + pidx[l]] : 0xFF, to = -1;
            if (pass == 1) {
                if (area < cnt[l] && occ[l][area] < sz[l][area]) to = area;
            } else {
                int a = area < cnt[l] ? area : cnt[l] / 2;
                for (int k = 0; k < PG && to < 0; k++) {
                    if (a + k < cnt[l] && occ[l][a + k] < sz[l][a + k]) to = a + k;
                    else if (a - k >= 0 && occ[l][a - k] < sz[l][a - k]) to = a - k;
                }
                if (to < 0) to = a;             /* (more clubs than room: the area's group) */
            }
            if (to < 0) continue;
            pg_pend[g >> 3] &= ~(1 << (g & 7));
            occ[l][to]++;
            copy[g] = first[l] + to - base;
        }
    return c + rs * nc;
}

void pg_place(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pl_one(t, map, slt, copy, t[0] == world);
}

/* The reserve (gplay loser_div 'reserve', pack.json league 'reserve', engine.reserve): a pool of clubs out of every
   division (division nd). At the season end (pg_fix, before pg_season places the new clubs by area) every club that
   went down from the lowest level (the game's relegation, gplay's play-out) leaves for the reserve, and as many come
   back from it to the lowest level: the longest out first (the queue: the pool's first order, then each season's
   relegated at its end). Table: db count; per country db world, nd, low (the lowest level's first division); dw clubs;
   clubs x (dw global, db base division); db pool; pool x dw global. State RS_STATE (saved by the engine block):
   per country db init, n, -, -; dw q[RQ]. */
enum { RQ = 64, RC = 8 };
struct rs_state { u8 init, n, pad[2]; u16 q[RQ]; };
struct rs_state RS_STATE[RC];
const u32 RS_STATE_SIZE = sizeof RS_STATE;          /* (gplay.RS_SIZE: the engine block item 'RS') */

static int rs_base(const u8 *c, int nc, int g) {
    for (int i = 0; i < nc; i++) if ((c[3 * i] | c[3 * i + 1] << 8) == g) return c[3 * i + 2];
    return -1;
}

void rs_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    int cnt = *t++;
    for (int k = 0; k < cnt; k++) {
        int w = t[0], nd = t[1], low = t[2], nc = t[3] | t[4] << 8;
        const u8 *c = t + 5, *pl = c + 3 * nc, *pg = pl + 1;
        int np = pl[0];
        t = pg + 2 * np;
        if (w != world || k >= RC) continue;
        struct rs_state *st = &RS_STATE[k];
        if (!st->init) {                        /* (a new career: the pool's first order) */
            st->n = 0;
            for (int i = 0; i < np && i < RQ; i++) st->q[st->n++] = pg[2 * i] | pg[2 * i + 1] << 8;
            st->init = 1;
        }
        u16 out[RQ];
        int no = 0;
        for (int i = 0; i < nc; i++) {          /* down from the lowest level: out, to the reserve */
            int g = c[3 * i] | c[3 * i + 1] << 8, base = c[3 * i + 2];
            int o = base + slt[g], n = base + copy[g];
            if (o >= low && o < nd && n > o && no < RQ) { out[no++] = g; copy[g] = nd - base; }
        }
        int up = no < st->n ? no : st->n, m = 0;
        for (int i = 0; i < up; i++) {          /* back: to the lowest level's first division (pg_season: by area) */
            int g = st->q[i], base = rs_base(c, nc, g);
            if (base >= 0) copy[g] = low - base;
        }
        for (int i = up; i < st->n; i++) st->q[m++] = st->q[i];
        for (int i = 0; i < no && m < RQ; i++) st->q[m++] = out[i];
        st->n = m;
    }
}

/* Off-file pools (mkseason Pack.off_pools): a team file's slots swap IDENTITIES with an off-file pool instead of
   clubs leaving the world. Per team file (up to RF; one RS file each, DATA\RS<world><file>.DAT): identity 0..255 = the
   file's own records (file order), 256 + k = the RS file's record k; map[slot] = identity + 1 (0 = the slot itself: a
   cleared item is the start). Per pool (up to RP) a queue of identities out: the pool's first order at the first
   season end, each season's relegated at its tail (rotation: its length stays the pool's size).
   - kind 0, a league's lowest level (Eccellenza: Italy's 256 slots are the whole file): every slot relegated from
     the lowest level (o in it, n below) keeps its slot and its level; pg_season places the new identity by area;
   - kind 1, a state championship (Brazil 2026: the state-only clubs of file 161): its n relegated = the bottom state-
     only clubs of the state's stage-1 ranking (RI_SR, statespec's 'SR' item: dw first club, db n, db 0, n x dw team
     word, best first) when the career played it; else by RI_RULE (0 none, 1 the weakest n, 2 a draw weighted by
     weakness). Never the manager's club (RI_MGR, global number).
   Table: db files; per file: db world, file, pools; per pool: db kind, n (pool records), then
     kind 0: db low; dw slots; slots x (dw global, db base division, db D area); n x db D area;
     kind 1: dw key (the state's first club's team word); db relegated; db slots; slots x (db ordinal, dw global,
             db strength); n x db strength; db entries; entries x dw the contest's original team words;
     then n x db RS record (the pool's first order).
   Exact state relegation (Davide 2026-10-19): a LEAGUE club relegated from its state leaves the state contest (its
   national place kept) and waits in the queue as a marker 0x8000 | its entry; the A2 club coming in takes a free
   SPARE slot of the file (pack.json "state_spares": the file's last ordinals, in no contest), and the contest's entry
   points to it: RI_STATE.ovr[pool][entry] = the new team word (0 = the original), applied to the contest list by
   statecup (package 5) after every load and at the season start. A marker at the queue's head brings its league
   club back (its spare's identity moves to the slot that goes down, or the spare passes to the entry that goes down).
   No spare free: that league club stays (declared approximation). File header: db world, file, pools; dw base;
   db spares; spares x db ordinal. */
enum { RIS = 256, RF = 2, RP = 16, RQT = 192, RO = 16 };
struct ri_file { u8 init, pad[3]; u16 map[RIS]; };
struct ri_state { struct ri_file f[RF]; u8 qn[RP]; u16 q[RQT]; u16 ovr[RP][RO]; };
struct ri_state RI_STATE;
u8 RI_SWAPPED[RF][RIS / 8];                     /* (this season end's swapped slots: ri_cache) */
int RI_MGR;                                     /* (the manager's club, global number: set by the glue, never swapped) */
int RI_RULE = 2;
u8 RI_FILES_FILE[RF];                           /* (each table file's team file number, set by ri_season) */
const u32 RI_STATE_SIZE = sizeof(struct ri_state);   /* (the engine item 'RI': ripool.RI_SIZE) */
static u32 ri_rng;

static u32 ri_rand(u32 n) {
    ri_rng = ri_rng * 1103515245u + 12345u;
    return n ? (ri_rng >> 8) % n : 0;
}

/* one swap: slot i of file fi takes the queue head of the pool (q = its queue, *qn its length, m = this season's
   takes so far), its identity goes out */
static int ri_swap(struct ri_file *f, int fi, int i, u16 *q, int qn, int m, u16 *out, int *no) {
    if (m >= qn) return -1;
    int was = f->map[i] ? f->map[i] - 1 : i, in = q[m];
    out[(*no)++] = was;
    f->map[i] = in == i ? 0 : in + 1;
    RI_SWAPPED[fi][i >> 3] |= 1 << (i & 7);
    return in;
}

static int ri_id(struct ri_file *f, int x) { return f->map[x] ? f->map[x] - 1 : x; }
static void ri_set(struct ri_file *f, int fi, int x, int id) {
    f->map[x] = id == x ? 0 : id + 1;
    RI_SWAPPED[fi][x >> 3] |= 1 << (x & 7);
}

/* a free spare of the file (pools p0 .. p0 + np - 1 of it hold its overrides), or -1 */
static int ri_spare(const u8 *sp, int ns, int file, int p0, int np) {
    for (int s = 0; s < ns; s++) {
        int w = file | sp[s] << 8, used = 0;
        for (int p = p0; p < p0 + np && p < RP; p++)
            for (int j = 0; j < RO; j++) if (RI_STATE.ovr[p][j] == w) used = 1;
        if (!used) return sp[s];
    }
    return -1;
}

static const u8 *ri_pool(const u8 *e, struct ri_file *f, int fi, u16 *q, u8 *qn, const s8 *slt, s8 *copy,
                         const u8 *sr, int run, int pi, int base, const u8 *sp, int nsp, int p0, int np) {
    int kind = e[0], n = e[1], manager = RI_MGR;
    const u8 *p = e + 2, *order;
    u16 out[64];
    int no = 0, m = 0;
    if (kind == 0) {
        int low = p[0], ns = p[1] | p[2] << 8;
        const u8 *sl = p + 3, *pa = sl + 4 * ns;
        order = pa + n;
        if (run && f->init == 1) {
            for (int i = 0; i < n; i++) q[i] = RIS + order[i];
            *qn = n;
        }
        for (int i = 0; run && i < ns && i < RIS && ri_no < RIO && m < *qn && no < 64; i++) {
            const u8 *s = sl + 4 * i;
            int g = s[0] | s[1] << 8, base = s[2];
            int o = base + slt[g], nn = base + copy[g];
            if (o < low || nn <= o || g == manager) continue;   /* (relegated from the lowest level; never the manager's) */
            int in = ri_swap(f, fi, i, q, *qn, m++, out, &no);
            ri_og[ri_no] = g;
            ri_oa[ri_no] = in < RIS ? sl[4 * in + 3] : pa[in - RIS];
            ri_no++;
            copy[g] = slt[g];                   /* (the slot stays; pg_season places its new identity by area) */
        }
    } else {
        int key = p[0] | p[1] << 8, rel = p[2], ns = p[3], file = RI_FILES_FILE[fi];
        const u8 *sl = p + 4, *ps = sl + 4 * ns, *en = ps + n + 1;
        int ne = ps[n];
        order = en + 2 * ne;
        u16 *ovr = RI_STATE.ovr[pi < RP ? pi : RP - 1];
        if (run && f->init == 1) {
            for (int i = 0; i < n; i++) q[i] = RIS + order[i];
            *qn = n;
            for (int j = 0; j < RO; j++) ovr[j] = 0;
        }
        u16 rw[16];                             /* the relegated, as the contest's current team words */
        int nr = 0;
        const u8 *b = sr;
        while (run && b && (b[0] | b[1] << 8)) {    /* statespec's rankings ('SR'): this state's last 'rel' */
            int nb = b[2];
            if ((b[0] | b[1] << 8) == key) {
                for (int k = nb - rel < 0 ? 0 : nb - rel; k < nb && nr < 16; k++) rw[nr++] = b[4 + 2 * k] | b[5 + 2 * k] << 8;
                break;
            }
            b += 4 + 2 * nb;
        }
        if (run && !(b && (b[0] | b[1] << 8)) && RI_RULE) {    /* no ranking: the fallback among the state-only */
            u8 st[RIS], pick[RIS / 8];
            int smax = 0;
            for (int i = 0; i < RIS / 8; i++) pick[i] = 0;
            for (int i = 0; i < ns; i++) {
                int id = ri_id(f, sl[4 * i]), s = 0;
                for (int jj = 0; id < RIS && jj < ns; jj++) if (sl[4 * jj] == id) s = sl[4 * jj + 3];
                for (int jj = 0; id >= RIS && jj < n; jj++) if (order[jj] == id - RIS) s = ps[jj];
                st[i] = s;
                if (s > smax) smax = s;
            }
            for (int r = 0; r < rel && nr < 16; r++) {
                u32 tot = 0;
                int best = -1;
                for (int i = 0; i < ns; i++) {
                    int o = sl[4 * i];
                    if (pick[o >> 3] & 1 << (o & 7)) continue;
                    u32 wgt = smax + 1 - st[i];
                    if (RI_RULE == 1) { if (best < 0 || st[i] < st[best]) best = i; }
                    else tot += wgt * wgt;
                }
                if (RI_RULE == 2 && tot) {
                    u32 x = ri_rand(tot);
                    for (int i = 0; i < ns; i++) {
                        int o = sl[4 * i];
                        if (pick[o >> 3] & 1 << (o & 7)) continue;
                        u32 wgt = smax + 1 - st[i];
                        if (x < wgt * wgt) { best = i; break; }
                        x -= wgt * wgt;
                    }
                }
                if (best < 0) break;
                int o = sl[4 * best];
                pick[o >> 3] |= 1 << (o & 7);
                rw[nr++] = file | o << 8;
            }
        }
        for (int r = 0; r < nr && m < *qn && no < 64; r++) {
            int j = -1;
            for (int k = 0; k < ne && k < RO; k++)
                if ((ovr[k] ? ovr[k] : (en[2 * k] | en[2 * k + 1] << 8)) == rw[r]) j = k;
            if (j < 0) continue;
            int cur = ovr[j] ? ovr[j] : (en[2 * j] | en[2 * j + 1] << 8);
            int league = (cur & 0xFF) != file, x = cur >> 8;
            if (!league && base + x == manager) continue;   /* (never the manager's club) */
            int in = q[m], outid = league ? 0x8000 | j : ri_id(f, x);
            if (in & 0x8000) {                  /* a league club comes back: its spare's identity / the spare */
                int k = in & 0xFF, sw = ovr[k];
                if (k >= RO || !sw) continue;
                ovr[k] = 0;
                if (league) ovr[j] = sw;
                else ri_set(f, fi, x, ri_id(f, sw >> 8));
            } else if (league) {                /* a league club goes: the A2 club into a free spare */
                int s = ri_spare(sp, nsp, file, p0, np);
                if (s < 0) continue;
                ri_set(f, fi, s, in);
                ovr[j] = file | s << 8;
            } else
                ri_set(f, fi, x, in);
            out[no++] = outid;
            m++;
        }
    }
    if (run && m) {                             /* the queue: drop the taken, append the outs */
        int k = 0;
        for (int i = m; i < *qn; i++) q[k++] = q[i];
        for (int i = 0; i < no && k < n; i++) q[k++] = out[i];
    }
    if (run) *qn = n;
    return order + n;
}

void ri_season(const u8 *t, const s8 *slt, s8 *copy, int world, u8 *sr) {
    ri_no = 0;
    for (int fi = 0; fi < RF; fi++)
        for (int i = 0; i < RIS / 8; i++) RI_SWAPPED[fi][i] = 0;
    u32 h = 0x9E3779B9u;                        /* (the draw: the season's own table as seed) */
    int moved = 0;
    for (int g = 0; g < 2000; g++) { h = h * 31 + (u8)slt[g]; if (copy[g] != slt[g]) moved = 1; }
    ri_rng = h;
    if (!moved) return;                         /* (InitializeNewSeason at a career's start: no season end yet) */
    int nf = *t++, qo = 0, pi = 0;
    for (int fi = 0; fi < nf; fi++) {
        int w = t[0], np = t[2];
        RI_FILES_FILE[fi] = t[1];
        struct ri_file *f = &RI_STATE.f[fi < RF ? fi : RF - 1];
        int run = w == world && fi < RF;
        if (run && !f->init) {                  /* (a new career / an older save: identities, the pools' first order) */
            for (int i = 0; i < RIS; i++) f->map[i] = 0;
            f->init = 1;
        }
        int base = t[3] | t[4] << 8, nsp = t[5];
        const u8 *sp = t + 6;
        t = sp + nsp;
        int p0 = pi;
        for (int k = 0; k < np; k++) {
            int n = t[1];
            t = ri_pool(t, f, fi, RI_STATE.q + qo, RI_STATE.qn + pi, slt, copy, sr,
                        run && pi < RP && qo + n <= RQT, pi, base, sp, nsp, p0, np);
            qo += n;
            pi++;
        }
        if (run) f->init = 2;
    }
    if (sr) sr[0] = sr[1] = 0;                  /* (the rankings used: a season end without any has none) */
}

/* A slot's record from its identity: everything but the slot's own bytes (file, ordinal, global number, controls,
   the 0xFE flags, the league / division). */
static void ri_copy(u8 *dst, const u8 *src) {
    for (int b = 0; b < 684; b++)
        if (b > 4 && b != 23 && b != 25) dst[b] = src[b];
}

/* After a pooled team file is read (LoadTeamFile): buf = teamFileBuffer (BE count + records), orig = its copy as
   read, pool = its RS file's buffer (BE count + records), fi = its index in the table. */
void ri_apply(u8 *buf, const u8 *orig, const u8 *pool, int fi) {
    int n = buf[0] << 8 | buf[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int i = 0; i < n && i < RIS; i++) {
        int id = RI_STATE.f[fi].map[i];
        if (!id--) continue;
        if (id < RIS && id < n) ri_copy(buf + 2 + 684 * i, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(buf + 2 + 684 * i, pool + 2 + 684 * (id - RIS));
    }
}

/* The career's team cache after a swap: every cached record of a swapped slot (team word file | slot << 8) gets its
   new identity's record. recs = the cache's records, n of them; file = the team file; orig / pool / fi as for
   ri_apply. */
void ri_cache(u8 *recs, int n, int file, const u8 *orig, const u8 *pool, int fi) {
    int nf = orig[0] << 8 | orig[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int k = 0; k < n; k++) {
        u8 *r = recs + 684 * k;
        int i = r[1];
        if (r[0] != file || !(RI_SWAPPED[fi][i >> 3] & 1 << (i & 7))) continue;
        int id = RI_STATE.f[fi].map[i] ? RI_STATE.f[fi].map[i] - 1 : i;
        if (id < RIS && id < nf) ri_copy(r, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(r, pool + 2 + 684 * (id - RIS));
    }
}
