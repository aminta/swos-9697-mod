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
enum { K_TITLE = 5, K_CONT = 6, K_PROM = 7, GS = 2, BEST_LOSER = 0x3F };
struct gp_row { u16 team, glob, won, gf, ga, pts; };
static void rcopy(struct gp_row *d, const struct gp_row *s) {   /* (no memcpy in the exe: field by field) */
    d->team = s->team; d->glob = s->glob; d->won = s->won; d->gf = s->gf; d->ga = s->ga; d->pts = s->pts;
}
struct gp_in {
    u8 nd, pad[3];
    u8 n[GD], pad2[2];                  /* clubs per division (0 = not captured) */
    struct gp_row t[GD][GT];
    const u8 *spec;
    u8 nst[GS], pad3[2];                /* kept stage tables (split 'keep'), rows by place */
    struct gp_row st[GS][GT];
};
struct gp_mv { u16 glob, team; s8 delta; u8 pad[3]; };
struct gp_res { u8 kind, div; u16 team[2], glob[2]; };     /* title: [0] the champion; continental: winner, loser */
struct gp_out { u8 nmv, nres, pad[2]; struct gp_mv mv[32]; struct gp_res res[4]; };
struct gp_in GP_IN;
struct gp_out GP_OUT;
enum { SS_N = 3, SS_BASE = 4 };      /* stage tables of a league with fixture stages (split 'table'): entrant
                                        'stage_place' s = SS_BASE + k (Argentina: 4 Apertura, 5 Clausura, 6 the
                                        annual table); saved with the career (engine item 'SS') */
struct gp_ss { u8 n[SS_N], pad; struct gp_row r[SS_N][GT]; };
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
        if (a < 1 || a > GP_SS.n[s - SS_BASE] || d >= GP_IN.nd) return -1;
        g = GP_SS.r[s - SS_BASE][a - 1].glob;
    } else {
        if (s >= GS || a < 1 || a > GP_IN.nst[s] || d >= GP_IN.nd) return -1;
        g = GP_IN.st[s][a - 1].glob;
    }
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
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

/* a group round: mem[0..m) round robin `meet` times (home and away alternate), start bonus points; placings -> out */
static void group(const int *mem, int m, int meet, int neutral, const u8 *bonus, int *out) {
    struct gs t[GT];                    /* (at most 24 members: compile_spec)  */
    for (int i = 0; i < m; i++) { t[i].c = mem[i]; t[i].pts = bonus[i]; t[i].gd = 0; t[i].gf = 0; }
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
    for (int i = 0; i < m; i++) out[i] = t[i].c;
}

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
    if (n < 3 || n != GP_IN.n[d]) return;
    const struct gp_row *a = GP_SS.r[2];
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

void gp_season(void) {
    const u8 *s = GP_IN.spec;
    u32 h = 0;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) h = h * 31 + GP_IN.t[d][k].glob + (GP_IN.t[d][k].pts << 9);
    rng = h;
    GP_OUT.nmv = 0;
    GP_OUT.nres = 0;
    int prev_loser = -1;                        /* the last tie's loser of the play-off before (entrant type 4) */
    while (s && *s) {
        int kind = s[0], n = s[1], nr = s[2], wdiv = s[3], ldiv = s[4];
        const u8 *e = s + 6, *r = e + 4 * n;
        if (kind == K_PROM) {                   /* (no entrants, no rounds) */
            promedio(0, wdiv, ldiv);
            s = r;
            continue;
        }
        int club[GN], ok = kind == 1 || kind == 4 || kind == K_TITLE || kind == K_CONT;
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
                else if (c < 0x80) v = (c & 0x3F) < np ? P[c & 0x3F] : -1;
                else if (c < 0xC0) v = (c & 0x3F) < nt ? W[c & 0x3F] : -1;
                else v = (c & 0x3F) < nt ? L[c & 0x3F] : -1;
                mem[i] = v;
                if (v < 0) ok = 0;
            }
            if (legs & 0x80) {                  /* a group round */
                if (ok && ties <= GT && np + ties <= GN) {
                    group(mem, ties, legs & 0x7F, host == HOST_NEUTRAL, m + ties, P + np);
                    glast = np;
                }
                np += ties;
                last = -1;
                r = m + 2 * ties;
                continue;
            }
            if (ok && pairing) {            /* best v worst: sorted, then 1st v last, 2nd v second last ... */
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
                                                           : tie(a, b, legs, host, level);
                    W[nt] = w; L[nt] = w == mem[2 * i] ? mem[2 * i + 1] : mem[2 * i];
                    last = nt; glast = -1;
                }
                nt++;
            }
            r = m + 2 * ties;
        }
        if (ldiv == RESERVE) ldiv = GP_IN.nd;   /* (the reserve: out of every division) */
        if (ok && (kind == K_TITLE || kind == K_CONT) && glast >= 0) {     /* a final group: its 1st (and 2nd) */
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
}

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

/* The off-file pool (Eccellenza 2026-27: mkseason Pack.off_pool, league 'reserve' off_file): Italy's 256 slots are the
   whole team file, so the clubs relegated from the lowest level swap IDENTITIES with the pool instead of leaving.
   Identity: 0..255 = the league's own records (file order), 256 + k = the pool's record k (DATA\RS<world><file>.DAT).
   RI_STATE (engine item 'RI'): map[slot] = identity + 1 (0 = the slot itself: a cleared item is the start), the queue
   of identities out (the pool's first order at the first season end; each season's relegated at its tail).
   Table: db count (0 or 1); db world, file, low (the lowest level's first division); dw slots; slots x (dw global,
   db base division, db D area); db pool; pool x db D area; pool x db first order (pool indices). */
enum { RIS = 256, RIQ = 64 };
struct ri_state { u8 init, n, pad[2]; u16 map[RIS]; u16 q[RIQ]; };
struct ri_state RI_STATE;
u8 RI_SWAPPED[RIS / 8];                         /* (this season end's swapped slots: ri_cache) */

int RI_MGR;                                     /* (the manager's club, global number: set by the glue, never swapped) */

void ri_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    int manager = RI_MGR;
    ri_no = 0;
    for (int i = 0; i < RIS / 8; i++) RI_SWAPPED[i] = 0;
    if (!*t++) return;
    int w = t[0], low = t[2], ns = t[3] | t[4] << 8;
    const u8 *sl = t + 5, *pa = sl + 4 * ns + 1;
    int np = sl[4 * ns];
    const u8 *po = pa + np;
    if (w != world) return;
    struct ri_state *st = &RI_STATE;
    if (!st->init) {                            /* (a new career / an older save: the pool's first order) */
        st->n = 0;
        for (int i = 0; i < np && i < RIQ; i++) st->q[st->n++] = RIS + po[i];
        st->init = 1;
    }
    u16 out[RIQ];
    int no = 0;
    for (int i = 0; i < ns && i < RIS && ri_no < RIO && ri_no < st->n; i++) {
        const u8 *e = sl + 4 * i;
        int g = e[0] | e[1] << 8, base = e[2];
        int o = base + slt[g], n = base + copy[g];
        if (o < low || n <= o || g == manager) continue;   /* (relegated from the lowest level; never the manager's) */
        int was = st->map[i] ? st->map[i] - 1 : i, in = st->q[ri_no];
        out[no++] = was;
        st->map[i] = in == i ? 0 : in + 1;
        ri_og[ri_no] = g;
        ri_oa[ri_no] = in < RIS ? sl[4 * in + 3] : pa[in - RIS];
        ri_no++;
        RI_SWAPPED[i >> 3] |= 1 << (i & 7);
        copy[g] = slt[g];                       /* (the slot stays; pg_season places its new identity by area) */
    }
    int m = 0;
    for (int i = ri_no; i < st->n; i++) st->q[m++] = st->q[i];
    for (int i = 0; i < no && m < RIQ; i++) st->q[m++] = out[i];
    st->n = m;
}

/* A slot's record from its identity: everything but the slot's own bytes (file, ordinal, global number, controls,
   the 0xFE flags, the league / division). */
static void ri_copy(u8 *dst, const u8 *src) {
    for (int b = 0; b < 684; b++)
        if (b > 4 && b != 23 && b != 25) dst[b] = src[b];
}

/* After Italy's team file is read (LoadTeamFile): buf = teamFileBuffer (BE count + records), orig = its copy as read,
   pool = the RS file's buffer (BE count + records). */
void ri_apply(u8 *buf, const u8 *orig, const u8 *pool) {
    int n = buf[0] << 8 | buf[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int i = 0; i < n && i < RIS; i++) {
        int id = RI_STATE.map[i];
        if (!id--) continue;
        if (id < RIS && id < n) ri_copy(buf + 2 + 684 * i, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(buf + 2 + 684 * i, pool + 2 + 684 * (id - RIS));
    }
}

/* The career's team cache after a swap: every cached record of a swapped slot (team word file | slot << 8) gets its
   new identity's record. recs = the cache's records, n of them; file = Italy's file; orig / pool as for ri_apply
   (orig = Italy's file as read). */
void ri_cache(u8 *recs, int n, int file, const u8 *orig, const u8 *pool) {
    int nf = orig[0] << 8 | orig[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int k = 0; k < n; k++) {
        u8 *r = recs + 684 * k;
        int i = r[1];
        if (r[0] != file || !(RI_SWAPPED[i >> 3] & 1 << (i & 7))) continue;
        int id = RI_STATE.map[i] ? RI_STATE.map[i] - 1 : i;
        if (id < RIS && id < nf) ri_copy(r, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(r, pool + 2 + 684 * (id - RIS));
    }
}
