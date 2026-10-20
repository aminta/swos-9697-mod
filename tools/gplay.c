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
   (away goals are not simulated: as et_pens / better); member 0x3F = the best placed loser of the previous round.
   Entrant type 6 (4.0, Malta 2026-27) = seed a (1..4) of a split season's title decider (split_seed). */

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
enum { SS_N = 4, SS_BASE = 4 };      /* stage tables of a league with fixture stages (split 'table'): entrant
                                        'stage_place' s = SS_BASE + k (Argentina: 4 Apertura, 5 Clausura, 6 the
                                        annual table; 7 the MLS season, its own: GP_SS is the world's); saved with the career (engine item 'SS') */
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

static int by_rec;                      /* spec flag 2 'host_by_record' (4.0 MLS): in one division the better record */
static int better(int a, int b) {       /* the higher tier, then the better place */
    if (DV(a) != DV(b)) return DV(a) < DV(b);
    if (by_rec) {                       /* (points, wins, goal difference, goals: MLS; then the place) */
        const struct gp_row *x = row(a), *y = row(b);
        int dx = x->gf - x->ga, dy = y->gf - y->ga;
        if (x->pts != y->pts) return x->pts > y->pts;
        if (x->won != y->won) return x->won > y->won;
        if (dx != dy) return dx > dy;
        if (x->gf != y->gf) return x->gf > y->gf;
    }
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
    for (int s = 0; s < SS_N; s++)              /* (a stage table written this season: the same place there) */
        if (GP_SS.fresh & 1 << s && GP_FORCE <= GP_SS.n[s])
            for (int k = 0; k < GP_SS.n[s]; k++)
                if (GP_SS.r[s][k].team == GP_IN.mgr && k != GP_FORCE - 1) {
                    struct gp_row x, *r = GP_SS.r[s];
                    rcopy(&x, &r[k]); rcopy(&r[k], &r[GP_FORCE - 1]); rcopy(&r[GP_FORCE - 1], &x);
                    break;
                }
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

static u16 stage_glob(int k, int j) {   /* stage k's champion (j 0) / runner-up (1): decided this season (dec: the
                                           Trofeo built mid-season), else this gp_season pass's GP_OUT.sres */
    const struct gp_dec *x = stage_dec(k);
    return x ? x->glob[j] : GP_OUT.sres[k].glob[j];
}

static int title_club(int d, int c) {   /* entrant type 5 (the Trofeo): 1 the 1st stage's champion; 2 / 3 the 2nd
                                           stage's champion, or (the same club won both) the 1st's / 2nd's runner-up */
    u16 c0 = stage_glob(0, 0), c1 = stage_glob(1, 0);
    if (c == 1) return glob_club(d, c0);
    if (c0 != c1) return glob_club(d, c1);
    return glob_club(d, stage_glob(c - 2, 1));
}

static int kept_pts(int s, int c) {    /* club c's points in kept stage s (0: not in it) */
    u16 g = row(c)->glob;
    if (s >= GS) return 0;
    for (int k = 0; k < GP_IN.nst[s]; k++) if (GP_IN.st[s][k].glob == g) return GP_IN.st[s][k].pts;
    return 0;
}

static int agg_better(int s, int a, int b) {   /* the two rounds' points together, then the final table's place */
    int x = kept_pts(s, a) + row(a)->pts, y = kept_pts(s, b) + row(b)->pts;
    return x != y ? x > y : PL(a) < PL(b);
}

/* entrant type 6 (Malta 2026-27, MFA competition rules): seed a (1..4) of the title decider of division d, from kept
   stage s (the Opening Round, its 1st / 2nd O1 / O2) and the final table (the Closing Round: C1 / C2), for a bracket
   1v4, 2v3, then the final, every tie skip_if_same: one club won both rounds -> 4 x O1 (no match: champion); O1 / C1
   1st and 2nd in reverse order, or one club 2nd in both (it is the runner-up, out of the decider) -> the Finalissima
   O1 v C1 (seeds A A B B, A the better by aggregate points); three clubs -> the one 1st in a round and 2nd in the
   other straight to the final (seeds 1 and 4), the other two play for its other place (a club 2nd in both: 3rd, the
   Finalissima as above); four clubs -> the Final Four seeded by the season's points (the Opening's kept table, Top 6
   included, + the Closing's). Equal points: the Closing table's place (the rules' direct encounters need every
   pair's results over both rounds, which no table keeps; the Top-6 / league-phase rule is the rules' classification
   of 2nd-4th when one club won both, not a seeding) */
static int split_seed(int d, int s, int a) {
    if (d >= GP_IN.nd || GP_IN.n[d] < 2 || a < 1 || a > 4) return -1;
    int o1 = stage_club(d, s, 1), o2 = stage_club(d, s, 2), c1 = d * GT, c2 = d * GT + 1;
    if (o1 < 0 || o2 < 0) return -1;
    if (o1 == c1) return o1;
    if (o2 == c2 || (o1 == c2 && o2 == c1)) {
        int x = agg_better(s, o1, c1) ? o1 : c1, y = x == o1 ? c1 : o1;
        return a == 1 || a == 4 ? x : y;
    }
    int x = o1 == c2 ? o1 : c1 == o2 ? c1 : -1;
    if (x >= 0) {
        int y = x == o1 ? c1 : o1, z = x == o1 ? o2 : c2;
        if (agg_better(s, z, y)) { int t = y; y = z; z = t; }
        return a == 1 || a == 4 ? x : a == 2 ? y : z;
    }
    int q[4] = { o1, c1, o2, c2 };
    for (int i = 1; i < 4; i++)
        for (int j = i; j > 0 && agg_better(s, q[j], q[j - 1]); j--) { int t = q[j]; q[j] = q[j - 1]; q[j - 1] = t; }
    return q[a - 1];
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

/* 4.0 overall tables (longtable.py, STAT > CLASSIFICA GENERALE; display only): the table's rows in GP_OV_ROWS (the
   DIY row layout: +0 team, +4 played, won, drawn, lost, for, against, points) and their order in GP_OV_ORD (row
   offsets, best first: points, wins, goal difference, goals). Argentina's annual table: when the Apertura's kept table
   (GP_SS 0, written this season) holds every club of this one, its figures are added by club (played = apn, the
   Apertura's match days; drawn from its points). The MLS's Supporters' Shield: the live table, re-sorted. */
u16 GP_OV_ORD[32];
u8 GP_OV_ROWS[32 * 18];
u32 GP_OV_N, GP_OV_ANNUAL;
static u16 w16(const u8 *b) { return b[0] | b[1] << 8; }
static void p16(u8 *b, u32 v) { b[0] = v; b[1] = v >> 8; }
void gp_overall(const u8 *diy, const u8 *sel, u32 apn) {
    int n = w16(diy + 0x31);
    if (n < 1 || n > 32) { GP_OV_N = 0; return; }
    for (int i = 0; i < n * 18; i++) GP_OV_ROWS[i] = diy[0x2B3 + i];
    int found = 0;
    if (apn && (GP_SS.fresh & 1) && GP_SS.n[0] == n) {
        for (int r = 0; r < n; r++) {
            u8 *row = GP_OV_ROWS + 18 * r;
            u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
            u16 g = w16(sel + t + 2);
            for (int k = 0; k < n; k++) if (GP_SS.r[0][k].glob == g) { found++; break; }
        }
    }
    GP_OV_ANNUAL = found == n;
    if (GP_OV_ANNUAL)
        for (int r = 0; r < n; r++) {
            u8 *row = GP_OV_ROWS + 18 * r;
            u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
            u16 g = w16(sel + t + 2);
            for (int k = 0; k < n; k++) {
                const struct gp_row *a = &GP_SS.r[0][k];
                if (a->glob != g) continue;
                int d = a->pts - 3 * a->won, l = (int)apn - a->won - d;
                if (d < 0) d = 0;
                if (l < 0) l = 0;
                p16(row + 4, w16(row + 4) + apn);
                p16(row + 6, w16(row + 6) + a->won);
                p16(row + 8, w16(row + 8) + d);
                p16(row + 10, w16(row + 10) + l);
                p16(row + 12, w16(row + 12) + a->gf);
                p16(row + 14, w16(row + 14) + a->ga);
                p16(row + 16, w16(row + 16) + a->pts);
                break;
            }
        }
    for (int i = 0; i < n; i++) GP_OV_ORD[i] = w16(diy + 0x6D + 2 * i);    /* the table's own order first (ties) */
    for (int i = 1; i < n; i++)                 /* insertion sort, stable */
        for (int j = i; j > 0; j--) {
            const u8 *a = GP_OV_ROWS + GP_OV_ORD[j], *b = GP_OV_ROWS + GP_OV_ORD[j - 1];
            int dp = w16(a + 16) - w16(b + 16), dw = w16(a + 6) - w16(b + 6);
            int dd = (w16(a + 12) - w16(a + 14)) - (w16(b + 12) - w16(b + 14)), dg = w16(a + 12) - w16(b + 12);
            if (dp > 0 || (!dp && (dw > 0 || (!dw && (dd > 0 || (!dd && dg > 0)))))) {
                u16 x = GP_OV_ORD[j]; GP_OV_ORD[j] = GP_OV_ORD[j - 1]; GP_OV_ORD[j - 1] = x;
            } else break;
        }
    GP_OV_N = n;
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

/* Second teams (B / II / U21 / U23 / Reserves: formats2627.md 'Second teams', Davide 2026-10-18; the integrator's
   design): SEC_TAB (mkseason.second_table): db countries; per country db nd, nd x db the division's level in the chain,
   db n, n x (dw the B team's global, dw its first team's (0xFFFF: another country), db top = the highest level it may
   reach (0xFF: any), db flags: bit 0 play-offs allowed (ITA), bit 1 it may leave the world from the lowest level (an
   off-file pool refills its slot)). In the country's tables (GP_IN, gp_end) a B team may not go up into or above its
   first team's level (the first team's level after this season's moves) nor above 'top': it is skipped as a [div,
   place] entrant of every play-off but a play-out (the next placed club enters) and held in a direct promotion place
   (the next club of its division goes up instead); a first team that ends in its B team's level or below sends the B
   team one level down (out of the world from the lowest level, flag bit 1: kind 0 pool swap) and the best placed
   relegated club of the B team's division stays (the level keeps its size). */
extern const u8 SEC_TAB[];
extern s8 SEC_SLT[], SEC_COPY[];
enum { SEC_PO = 1, SEC_EXIT = 2 };

static const u8 *sec_country(int g, const u8 **ent) {   /* the country entry and B entry of global g, or 0 */
    const u8 *t = SEC_TAB;
    int nc = *t++;
    for (int c = 0; c < nc; c++) {
        const u8 *lv = t + 1;
        int nd = t[0], n = lv[nd];
        const u8 *e = lv + nd + 1;
        for (int i = 0; i < n; i++, e += 6)
            if ((e[0] | e[1] << 8) == g) { *ent = e; return t; }
        t = e;
    }
    return 0;
}

static int sec_lvl(const u8 *ct, int d) { return d < ct[0] ? ct[1 + d] : ct[1 + ct[0] - 1] + 1; }

static int sec_newlvl(const u8 *ct, int d, int g) {     /* a club's level after this season's moves */
    int dl = SEC_COPY[g] - SEC_SLT[g], l = sec_lvl(ct, d);
    if (!dl) return l;
    int nd = d + dl, nl = sec_lvl(ct, nd < 0 ? 0 : nd);
    if (nl == l) nl = l + (dl < 0 ? -1 : 1);          /* (a move inside a level of groups: pg_season's level change) */
    return nl;
}

static int sec_row(int g) {                             /* a global number's row in the country's tables, or -1 */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int sec_up_bad(const u8 *ct, const u8 *e, int d) {   /* B team of division d: going up one level is illegal */
    int target = sec_lvl(ct, d) - 1, f = e[2] | e[3] << 8;
    if (e[4] != 0xFF && target < e[4]) return 1;
    int fr = f == 0xFFFF ? -1 : sec_row(f);
    return fr >= 0 && target <= sec_newlvl(ct, DV(fr), f);
}

static int sec_inelig(int c) {                          /* a row skipped as a play-off entrant (not a play-out) */
    const u8 *e, *ct = sec_country(row(c)->glob, &e);
    return ct && (!(e[5] & SEC_PO) || sec_up_bad(ct, e, DV(c)));
}

static int place_club(int d, int p, int kind) {         /* [div, place] -> its row, B teams skipped but in play-outs */
    if (d >= GP_IN.nd || d >= GD || p < 1 || p > GP_IN.n[d]) return -1;
    if (kind == 4) return d * GT + p - 1;
    for (int k = 0; k < GP_IN.n[d]; k++)
        if (!sec_inelig(d * GT + k) && !--p) return d * GT + k;
    return -1;
}

#ifndef SEC_FORCE
#define SEC_FORCE 0
#endif
#ifndef SEC_FORCE_B
#define SEC_FORCE_B 0xFFFF
#endif
static void sec_swap(int d, int g, int up) {            /* (SEC_FORCE test builds: g takes a mover's move) */
    for (int k = 0; k < GP_IN.n[d]; k++) {
        int h = GP_IN.t[d][k].glob, dh = SEC_COPY[h] - SEC_SLT[h];
        if (h != g && (up ? dh < 0 : dh > 0) && SEC_COPY[g] == SEC_SLT[g]) {
            SEC_COPY[g] = SEC_SLT[g] + dh;
            SEC_COPY[h] = SEC_SLT[h];
            return;
        }
    }
}

void sec_post(void) {                                   /* gp_end, after the moves: holds, next clubs, B teams down */
    const u8 *t = SEC_TAB;
    int nc = *t++;
    if (SEC_FORCE > 0 && nc > 0) {                            /* (test builds: B team SEC_FORCE_B (else the first) promoted
                                                           (1), its first team relegated (2), both (3)) */
        const u8 *e = 0;
        if (!sec_country(SEC_FORCE_B, &e)) e = t + 1 + t[0] + 1;
        int rb = sec_row(e[0] | e[1] << 8), rf = sec_row(e[2] | e[3] << 8);
        int fo = SEC_FORCE;
        if (rb >= 0 && (fo & 1)) sec_swap(DV(rb), e[0] | e[1] << 8, 1);
        if (rb >= 0 && rf >= 0 && (fo & 2)) sec_swap(DV(rf), e[2] | e[3] << 8, 0);
    }
    for (int c = 0; c < nc; c++) {
        const u8 *ct = t, *e = t + 1 + t[0] + 1;
        int n = t[1 + t[0]];
        t = e + 6 * n;
        for (int i = 0; i < n; i++, e += 6) {
            int gb = e[0] | e[1] << 8, gf = e[2] | e[3] << 8, rb = sec_row(gb);
            if (rb < 0) continue;                       /* (not this country's tables) */
            int db = DV(rb), lb = sec_lvl(ct, db), nb = sec_newlvl(ct, db, gb);
            int rf = gf == 0xFFFF ? -1 : sec_row(gf), nf = rf >= 0 ? sec_newlvl(ct, DV(rf), gf) : -1;
            int lowest = sec_lvl(ct, db) == sec_lvl(ct, ct[0] - 1);
            int coupled = rf >= 0 && nf >= (nb < lb ? lb : nb) && nb <= lb, dl = SEC_COPY[gb] - SEC_SLT[gb];
            if (coupled && (!lowest || (e[5] & SEC_EXIT))) {   /* the first team in its level: one down */
                SEC_COPY[gb] = SEC_SLT[gb] + (lowest ? ct[0] - db : 1);
                if (!lowest)                            /* (out of the world: a pool identity takes its slot) */
                    for (int k = 0; k < GP_IN.n[db]; k++) {    /* the best placed relegated of its division stays */
                        int g = GP_IN.t[db][k].glob;
                        if (g != gb && SEC_COPY[g] > SEC_SLT[g]) { SEC_COPY[g] = SEC_SLT[g]; break; }
                    }
            } else if (nb < lb && (coupled || sec_up_bad(ct, e, db)))   /* up, not allowed: held (coupled, no pool: */
                SEC_COPY[gb] = SEC_SLT[gb];                             /* it stays, declared) */
            else
                continue;
            if (nb < lb)                                /* its promotion: the next club of its division */
                for (int k = 0; k < GP_IN.n[db]; k++) {
                    int g = GP_IN.t[db][k].glob, r = db * GT + k;
                    if (g == gb || SEC_COPY[g] != SEC_SLT[g] || sec_inelig(r)) continue;
                    SEC_COPY[g] = SEC_SLT[g] + dl;
                    break;
                }
        }
    }
}

/* The league champion from a 'title' play-off (GP_OUT.res kind 5): the season end's top-9 list of the country's top
   division (cseg_927A2: GP_TOPW = their team words, GP_TOPR = their 684-byte records), which the qualifiers read for
   the 'champion' place (the game's cseg_93974 / uefaq's uq_country), gets the play-off's winner first, the clubs
   above it one place down. A winner outside the top 9: as it is (the table's 1st stays). */
extern u16 GP_TOPW[9];
extern u8 GP_TOPR[9 * 684];
static u8 ch_tmp[684];
void gp_champ(void) {
    for (int k = 0; k < GP_OUT.nres; k++) {
        if (GP_OUT.res[k].kind != K_TITLE) continue;
        u16 w = GP_OUT.res[k].team[0];
        int j = 0;
        while (j < 9 && GP_TOPW[j] != w) j++;
        if (j == 0 || j >= 9) continue;
        for (int b = 0; b < 684; b++) ch_tmp[b] = GP_TOPR[684 * j + b];
        for (int i = j; i > 0; i--) {
            GP_TOPW[i] = GP_TOPW[i - 1];
            for (int b = 0; b < 684; b++) GP_TOPR[684 * i + b] = GP_TOPR[684 * (i - 1) + b];
        }
        GP_TOPW[0] = w;
        for (int b = 0; b < 684; b++) GP_TOPR[b] = ch_tmp[b];
    }
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
        by_rec = s[5] & 2;
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
            } else if (ty == 6) {               /* 4.0 MLT: a seed of the title decider (split_seed) */
                club[i] = split_seed(d, e[4 * i + 3], p);
                if (club[i] < 0) ok = 0;
            } else if (ty != 0 || d >= GP_IN.nd || p < 1 || p > GP_IN.n[d]) ok = 0;
            else if ((club[i] = place_club(d, p, kind)) < 0) ok = 0;
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
    u8 rn[KG];                          /* ko[0]'s game rounds' names (rnames index, 0: the game's): pack
                                           'round_names', gplay.py gp_rname (4.0 MLS) */
};
struct gp_state GP_ST;
extern const u8 *GP_CFB;
extern u16 GP_MGR;
struct gp_gs { u8 sdiv[GSD], pad; struct gp_srow srow[GSD][GSR]; };   /* the early tables beyond SD (a group contest:
                                           the Poule's 8 other groups; the engine block's item 'GS') */
struct gp_gs GP_GS;
struct gp_log { u32 tag; u8 seas, stseas, pl_pi, pad; struct gp_ko ko; struct gp_out out;
                u16 top[9]; } GP_LOG;    /* top: the qualifiers' top-9 list after gp_champ (harness: world_title) */
                                        /* the last season end's (harness): its season, the state's, the played one */
/* set by the glue */
u8 GP_HDR[14] = { 0xAD };               /* (gplay.py: the game's Australian cup header, no draw, no away goals) */
const u32 *GP_NM;                       /* the country's names: per play-off dd long, short, record (relative) */
const u8 *GP_RN;                        /* the country's 'round_names': KG bytes per play-off (rnames indices) */
const u8 *GP_TH;                        /* the country's 'then_build': per play-off the next one's index + 1, or 0 */
u8 *GP_DIYP;
u32 GP_K, GP_W, GP_SKIP, GP_RB, GP_ALIVE, GP_LAST;
u16 GP_MGR;                             /* (the career club: CAREERTEAM, set by the glue before the call) */
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

static int ent_club(const u8 *e, int kind) {    /* an entrant -> its club (division * GT + place), or -1 */
    if (e[0] == 3) return stage_club(e[1], e[3], e[2]);
    if (e[0] == 5) return title_club(e[1], e[2]);
    if (e[0] == 6) return split_seed(e[1], e[3], e[2]);
    if (e[0]) return -1;
    return place_club(e[1], e[2], kind);
}

static int playable(const u8 *s) {      /* knockouts only (promotion, placement, playout, title, continental), entrants [div, place]
                                           or stage places, members entrants / W / L */
    int n = s[1], nr = s[2], nt = 0;
    const u8 *e = s + 6, *r = e + 4 * n;
    if ((s[0] < 1 || (s[0] > 6 && s[0] != K_STAGE) || s[0] == 2) || n > KN || nr > KR || nr < 1) return 0;   /* (not 'europe': uefaq's) */
    for (int i = 0; i < n; i++)
        if (e[4 * i] != 0 && e[4 * i] != 3 && e[4 * i] != 5 && e[4 * i] != 6) return 0;   /* (5: the Trofeo, built by then_build; 6: Malta's split seeds) */
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
            int c = ent_club(e + 4 * i, s[0]);
            if (c == d0 * GT + m) in = 1;
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
    if (c < BEST_LOSER) return c < KN && k->ient[c] != NOC ? k->ient[c] : -1;
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
static int presim;                      /* a career club that waits in round 1 (MLS: seeds 1-7 v the wild cards): the
                                           first round's ties simulated at the build, the contest starts after them */
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
        if (g == 0 && presim && k->code[a] != k->code[b]) {   /* (the career club waits: simulated now) */
            int ca = k->code[a], cb = k->code[b], lv = k->rs[r][3];
            int w = legs == 3 ? series(ca, cb, lv) : tie(ca, cb, legs, host, lv);
            k->tw[t] = w == ca ? a : b; k->tl[t] = w == ca ? b : a;
            continue;
        }
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
        int c = ent_club(e + 4 * i, s[0]);
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
    by_rec = s[5] & 2;
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
        int c = ent_club(e + 4 * i, s[0]);
        if (c < 0) return 0;
        k->ient[i] = i; k->code[i] = c;
        k->prio[i] = e[4 * i] == 3 ? e[4 * i + 2] - 1 : c > 255 ? 255 : c;   /* (stage entrants: the stage place) */
        k->team[i] = row(c)->team; k->pts[i] = row(c)->pts;
    }
    if (by_rec)                             /* (the better record hosts: the ranks by it) */
        for (int i = 0; i < n; i++) {
            k->prio[i] = 0;
            for (int j = 0; j < n; j++) if (j != i && better(k->code[j], k->code[i])) k->prio[i]++;
        }
    presim = 0;
    if (GP_IN.gtype == 4) {
        int in = 0, in0 = 0;
        for (int i = 0; i < n; i++) in |= k->team[i] == GP_IN.mgr;
        for (int i = 0; i < k->rs[0][0]; i++) {   /* (a round-1 tie of the club with itself - Malta's split seeds,
                                               skip_if_same - is no match: the club waits) */
            int a = k->rc[2 * i], b = k->rc[2 * i + 1];
            if (a < n && b < n && (k->team[a] == GP_IN.mgr || k->team[b] == GP_IN.mgr) && k->code[a] != k->code[b])
                in0 = 1;
        }
        presim = in && !in0;
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
    int np1 = m, me0 = GP_IN.gtype != 4;
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++)
        me0 |= k->team[k->pa[p]] == GP_IN.mgr || k->team[k->pb[p]] == GP_IN.mgr;
    u8 need[KN];                        /* (a built contest lists only the clubs that can still play: round g0's, and
                                           the entrants / decided ties' clubs later rounds name; the Trofeo's R2 = R1
                                           twice was a 3-club contest whose match the career calendar lost) */
    for (int i = 0; i < n; i++) need[i] = !me0;
    for (int t = 0; t < k->ntie; t++)   /* (a decided tie's clubs stay: its result is kept, gp_played_c / gp_sack) */
        if (k->tw[t] != NOC) { need[k->tw[t]] = 1; if (k->tl[t] != NOC) need[k->tl[t]] = 1; }
    for (int t = k->gt0[k->gsr[g0] + 1 <= k->nrs ? k->gsr[g0] + 1 : k->nrs]; t < k->ntie; t++)
        for (int x = 0; x < 2; x++) {
            int c = k->rc[2 * t + x];
            if (c < BEST_LOSER && c < n) need[c] = 1;
            else if (c >= 0x80 && (c & 0x3F) < k->ntie) {
                int v = c & 0x40 ? k->tl[c & 0x3F] : k->tw[c & 0x3F];
                if (v != NOC) need[v] = 1;
            }
        }
    for (int i = 0; i < n; i++) if (!used[i] && need[i]) order[m++] = i;
    for (int i = 0; i < KN; i++) k->ient[i] = NOC;
    n = m;                              /* (the contest's clubs) */
    k->n = n;
    for (int j = 0; j < n; j++) {       /* list index j = entrant order[j] */
        int i = order[j];
        k->ient[i] = j;
        k->code[j] = cd[i]; k->prio[j] = pr[i];
        const struct gp_row *w = row(cd[i]);
        k->team[j] = w->team; k->pts[j] = w->pts;
    }
    for (int p = 0; p < k->gp0[g0 + 1]; p++) { k->pa[p] = k->ient[k->pa[p]]; k->pb[p] = k->ient[k->pb[p]]; }
    for (int t = 0; t < k->ntie; t++) {         /* (gap-decided ties, entrant indices too) */
        if (k->tw[t] != NOC) {
            k->tw[t] = k->ient[k->tw[t]]; k->tl[t] = k->tl[t] != NOC ? k->ient[k->tl[t]] : NOC;
        }
    }
    int me = 0;                         /* a career: the club must play round 1 (a slot-4 contest without it stops the
                                           season); else no contest, its gap-decided tie kept (gp_sack, gp_played_c) */
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++)
        me |= k->team[k->pa[p]] == GP_IN.mgr || k->team[k->pb[p]] == GP_IN.mgr;
    int days = 0;
    for (int g = g0; g < k->ngr; g++) days += (k->rb[g] & 0xC0) == 0x80 ? 2 : 1;
    k->gcur = g0;
    k->bye[5] = GP_TH ? GP_TH[pi] : 0;  /* (pack 'then_build': the play-off built when this one ends, index + 1) */
    if (k == &GP_ST.ko[0])              /* (its round names: the slot-4 screens, gp_rname) */
        for (int i = 0; i < KG; i++) GP_ST.rn[i] = GP_RN ? GP_RN[KG * pi + i] : 0;
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

static int club_res(struct gp_ko *k, u16 mgr);
static void stage_done(const struct gp_ko *k) {   /* a stage title's knockout decided: GP_ST.dec[stage] */
    const u8 *s = k->magic == MAGIC && k->season == GP_SEAS && k->ntie ? po_at(k->pi) : 0;
    int t = k->ntie - 1;
    if (!s || s[0] != K_STAGE || s[3] >= 3 || k->tw[t] == NOC) return;
    struct gp_dec *x = &GP_ST.dec[s[3]];
    int w = k->tw[t], l = k->tl[t];
    x->season = GP_SEAS; x->done = 1;
    x->team[0] = k->team[w]; x->glob[0] = team_glob(k->team[w]);
    x->team[1] = l != NOC ? k->team[l] : 0xFFFF; x->glob[1] = l != NOC ? team_glob(k->team[l]) : 0xFFFF;
    x->pad[0] = (u8)club_res((struct gp_ko *)k, GP_IN.mgr);   /* (the career club's result: its season record line) */
    x->pad[1] = k->pi + 1;
}

u32 GP_WK;                              /* (the glue: the current calendar entry's week) */

/* ---- The Coppa Italia Serie D (cupd.py: CD_TAB; state CD_ST, the engine block's item 'CD'). At every calendar
   advance (gp_adv -> cd_step_c), each round whose week is next (or past): the career club's tie is built in slot 4
   (a 1-tie contest, its result back through gp_rec_c -> cd_done), every other tie decided now (the world's first
   season: its real result when known; else 55% to the home club). Hosts: listed, drawn, or 'alternate' (the club
   away in its previous tie hosts; both home / both away: drawn). A 'draw' round pairs the previous round's winners
   at random. Later seasons (the data session's entry rule, LND art. 1-2 in the game's terms): the season's Serie D
   clubs of the team file (CD_DT); the preliminary round = the first 2 x (N - 128) of an entry order (the new
   arrivals: relegated from Serie C, promoted from the pool; then the clubs of each group from the bottom of last
   season's table up), the others enter at the first round; both rounds paired within a group where possible, else
   at random; from the 3rd round on a fixed bracket (tie k = the winners of ties 2k, 2k + 1), the round records'
   weeks, hosts and drawn semi-finals as the table's. */
enum { K_CUPD = 9, CDT = 168, CDP = 41, CD1 = 64 };   /* (CDP: preliminary ties at most, CDP + 2 x CD1 - 1 <= CDT) */
struct cd_state { u16 magic; u8 season, round, built, bt, drawn, pad; u8 res[CDT], home[CDT]; u8 sd[4];
                  u8 ent[256];          /* cd_season (the season end): per ordinal of the file, the entry order's key
                                           for the season to come (0 not in Serie D, 1 a new arrival, 2 + places from
                                           the bottom of last season's group, 40h unknown) */
                  u8 efresh, gen_on, np, nfc, nfp, ranked, nrk, nrc;   /* (ent written; this season's bracket
                                           generated; its preliminary ties; the new arrivals from Serie C, from the
                                           pool; ent holds the season's final places: cd_rank, its clubs placed,
                                           its calls) */
                  u16 gen[2 * (CDP + CD1)]; };   /* (the generated rounds 0-1: tie t's sides gen[2t], gen[2t + 1]) */
struct cd_state CD_ST;
const u32 CD_STSZ = sizeof(struct cd_state);
const u8 *GP_CDT;                       /* (the glue: CD_TAB of the running world, or 0) */
u16 *GP_CDS1;                           /* 4.0 (the glue): the Coppa D's slot-1 contest team list (64 words), 0 = none */
const u8 *GP_CDD;                       /* (its CD_DT: db first Serie D division, groups; dw global base; 256 x db
                                           base division, FFh none) */
const u32 *GP_CDNM;                     /* (its names: dd long, short) */
u32 GP_CDFIRST;                         /* (the career's first season in the world) */
#define CDREC(r) (GP_CDT + 4 + 8 * (r))
#define CDTIE(t) (GP_CDT + 4 + 8 * GP_CDT[1] + 6 * (t))
#define CD_REF(i) ((u16)((i) << 8 | 0xFF))      /* (a tie as a side: a team word's file is never 255) */
#define CD_ISREF(v) (((v) & 0xFF) == 0xFF)
#define CD_DRAWN 0xFEFF
extern const s8 *GP_SLT;

static int cd_gen(void) { return !GP_CDFIRST && CD_ST.gen_on; }
static int cd_n(int r) {                /* round r's ties */
    if (!cd_gen()) return CDREC(r)[4];
    return r ? 1 << (GP_CDT[1] - 1 - r) : CD_ST.np;
}
static int cd_first(int r) {            /* round r's first tie */
    if (!cd_gen()) return CDREC(r)[6] | CDREC(r)[7] << 8;
    int f = 0;
    for (int i = 0; i < r; i++) f += cd_n(i);
    return f;
}
static u16 cd_raw(int t, int sd) {      /* tie t's side sd as listed: a team word, CD_REF(a tie), CD_DRAWN */
    if (!cd_gen()) { const u8 *x = CDTIE(t); return x[2 * sd] | x[2 * sd + 1] << 8; }
    int r = 0;
    while (r + 1 < GP_CDT[1] && t >= cd_first(r + 1)) r++;
    if (r < 2) return CD_ST.gen[2 * t + sd];
    if (CDREC(r)[5] & 1) return CD_DRAWN;
    return CD_REF(cd_first(r - 1) + 2 * (t - cd_first(r)) + sd);
}

static u16 cd_side(int t, int sd) {     /* tie t's side sd (0 a, 1 b): a team word, 0 (off-file), FFFFh undecided */
    u16 v = cd_raw(t, sd);
    if (!CD_ISREF(v)) return v;
    int i = v >> 8;
    if (v == CD_DRAWN) {                  /* (a drawn round: its k-th tie = the previous round's sd[2k], sd[2k+1]) */
        int first = cd_first(CD_ST.round);
        i = CD_ST.sd[2 * (t - first) + sd];
    }
    if (i >= CDT || !CD_ST.res[i]) return 0xFFFF;
    return cd_side(i, CD_ST.res[i] - 1);
}

static int cd_hosted(int t, u16 club) { /* the club hosted tie t (two legs: the first leg) */
    int h = CD_ST.home[t];
    return cd_side(t, h) == club;
}

static void cd_ko(struct gp_ko *k, u16 home, u16 away, int w1, int w2, int legs) {
    k->magic = 0;
    k->slot = 4; k->cid = 0xFE; k->pi = 0xFF; k->kind = K_CUPD; k->n = 2; k->nrs = 1; k->ldiv = 0;
    k->ntie = 1; k->ngr = 1; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int i = 0; i < 8; i++) k->bye[i] = 0;
    k->rs[0][0] = 1; k->rs[0][1] = legs; k->rs[0][2] = HOST_LISTED; k->rs[0][3] = LV_PENS; k->rs[0][4] = 0;
    k->rs[0][5] = 0;
    k->rc[0] = 0; k->rc[1] = 1; k->gt0[0] = 0; k->gt0[1] = 1;
    k->rb[0] = rbyte(legs, LV_PENS); k->gsr[0] = 0; k->gno[0] = 0;
    k->gp0[0] = 0; k->gp0[1] = 1; k->pa[0] = 0; k->pb[0] = 1; k->pw[0] = NOC; k->ptie[0] = 0;
    k->team[0] = home; k->team[1] = away; k->code[0] = 0; k->code[1] = 1; k->prio[0] = 0; k->prio[1] = 1;
    k->ient[0] = 0; k->ient[1] = 1; k->pts[0] = k->pts[1] = 0;
    k->lfile = GP_CDT[2];
    k->d1 = w1 > (int)GP_WK ? w1 : GP_WK + 1;
    k->d2 = legs == 2 ? (w2 > k->d1 ? w2 : k->d1 + 1) : k->d1;
    k->bye[0] = 0xFE; k->bye[1] = 0xFF; k->bye[2] = 2; k->bye[3] = 0; k->bye[4] = 1;
    u8 *c = k->con;
    int len = 14;
    for (int i = 0; i < 14; i++) c[i] = GP_HDR[i];
    c[0] = 0xFE; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2; c[10] = 2;
    c[len++] = k->rb[0];
    c[len++] = 0;
    c[5] = len - 5;
    c[7] = len + 8 - 7;
    for (int i = 0; i < 8; i++) c[len + i] = ((const u8 *)GP_CDNM)[i];
    len += 8;
    for (int j = 0; j < 2; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    GP_ST.magic = MAGIC;
    GP_ST.season = GP_SEAS;
}

/* The league's end (gp_end_c, the final tables in GP_IN): each Serie D club's place from the bottom of its group
   into CD_ST.ent (saved with the career: a save before CONTINUA's season end loses GP_IN). */
static void cd_rank(void) {
    const u8 *dt = GP_CDD;
    int df = dt[0], dc = dt[1], lf = GP_CDT[2], n = 0;
    if (CD_ST.nrc < 255) CD_ST.nrc++;
    for (int d = df; d < df + dc && d < GD; d++)        /* (GP_IN: the league just ended - another country's: none) */
        for (int k = 0; k < GP_IN.n[d] && k < GT; k++) if ((GP_IN.t[d][k].team & 0xFF) == lf) n++;
    if (!n) return;
    for (int i = 0; i < 256; i++) CD_ST.ent[i] = 0;
    for (int d = df; d < df + dc && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d] && k < GT; k++) {
            u16 t = GP_IN.t[d][k].team;
            if ((t & 0xFF) == lf) CD_ST.ent[t >> 8] = 2 + (GP_IN.n[d] - 1 - k);
        }
    CD_ST.nrk = n;
    CD_ST.ranked = 1;
    CD_ST.efresh = 0;
}

/* The season end (pgroups' pg_fix, after the moves: slt = this season's divisions, copy = the next one's): the entry
   order's keys of the next season's Serie D clubs (CD_ST.ent). tab = CD_TAB, dt = CD_DT. */
enum { CD_RF = 8 };                     /* (= the RI section's RF: the off-file pools' files) */
extern u8 RI_SWAPPED[CD_RF][32];
extern u8 RI_FILES_FILE[CD_RF];
void cd_season(const u8 *tab, const u8 *dt, const s8 *slt, const s8 *copy, int world) {
    if (tab[0] != world) return;
    int df = dt[0], dc = dt[1], gb = dt[2] | dt[3] << 8, lf = tab[2], moved = 0, fi = -1;
    for (int i = 0; i < 256; i++) if (dt[4 + i] != 0xFF && copy[gb + i] != slt[gb + i]) moved = 1;
    if (!moved) return;                 /* (InitializeNewSeason at a career's start: the world's real bracket) */
    for (int k = 0; k < CD_RF; k++) if (RI_FILES_FILE[k] == lf) fi = k;
    CD_ST.nfc = CD_ST.nfp = 0;
    for (int i = 0; i < 256; i++) {
        int b = dt[4 + i], e = 0;
        if (b != 0xFF) {
            int nd = b + copy[gb + i], od = b + slt[gb + i];
            if (nd >= df && nd < df + dc) {
                if (fi >= 0 && (RI_SWAPPED[fi][i >> 3] & 1 << (i & 7))) {
                    e = 1;              /* (a new arrival: a new identity from the pool) */
                    CD_ST.nfp++;
                } else if (od < df || od >= df + dc) {
                    e = 1;              /* (relegated from Serie C) */
                    CD_ST.nfc++;
                }
                else            /* (an old club: its place from the bottom, cd_rank) */
                    e = CD_ST.ranked && CD_ST.ent[i] >= 2 ? CD_ST.ent[i] : 0x40;
            }
        }
        CD_ST.ent[i] = e;
    }
    CD_ST.efresh = 1;
    CD_ST.ranked = 0;
}

static void cd_pair(u16 *side, u8 *sg, int m, int at) {   /* m sides -> ties from gen[at]: shuffled, each paired
                                                                   with the next of its group, else the next */
    for (int i = m - 1; i > 0; i--) {
        int j = below(i + 1); u16 x = side[i]; u8 y = sg[i];
        side[i] = side[j]; side[j] = x; sg[i] = sg[j]; sg[j] = y;
    }
    u8 used[256];
    for (int i = 0; i < m; i++) used[i] = 0;
    for (int i = 0; i < m; i++) {
        if (used[i]) continue;
        int j = -1;
        for (int k = i + 1; k < m && j < 0; k++) if (!used[k] && sg[k] != 0xFF && sg[k] == sg[i]) j = k;
        for (int k = i + 1; k < m && j < 0; k++) if (!used[k]) j = k;
        used[i] = 1;
        CD_ST.gen[at++] = side[i];
        if (j >= 0) { used[j] = 1; CD_ST.gen[at++] = side[j]; } else CD_ST.gen[at++] = 0;
    }
}

static void cd_make(void) {             /* a later season's rounds 0-1 (CD_ST.gen) */
    const u8 *dt = GP_CDD;
    int df = dt[0], dc = dt[1], gb = dt[2] | dt[3] << 8, lf = GP_CDT[2], n = 0;
    u8 ord[256], grp[256];
    u16 key[256], side[256];
    rng = GP_SEAS * 104729u + 17;
    for (int i = 0; i < 256; i++) {
        int b = dt[4 + i];
        if (b == 0xFF || !GP_SLT) continue;
        int dv = b + GP_SLT[gb + i];
        if (dv < df || dv >= df + dc) continue;
        int e = CD_ST.efresh ? CD_ST.ent[i] : 0;
        ord[n] = i; grp[n] = dv - df; key[n] = (e ? e : 0x40) << 8 | below(256); n++;
    }
    for (int i = 1; i < n; i++)         /* (the entry order: insertion sort by key) */
        for (int j = i; j > 0 && key[j - 1] > key[j]; j--) {
            u16 k = key[j]; key[j] = key[j - 1]; key[j - 1] = k;
            u8 o = ord[j]; ord[j] = ord[j - 1]; ord[j - 1] = o; o = grp[j]; grp[j] = grp[j - 1]; grp[j - 1] = o;
        }
    int n1 = 1 << (GP_CDT[1] - 2), p = n - 2 * n1, m = 0;
    if (p < 0) p = 0;
    if (p > CDP) p = CDP;
    CD_ST.np = p;
    u8 sg[256];
    for (int k = 0; k < 2 * p; k++) { side[m] = lf | ord[k] << 8; sg[m++] = grp[k]; }
    cd_pair(side, sg, m, 0);
    u8 pg[CDP];
    for (int t = 0; t < p; t++) {       /* (a preliminary tie's group: its first side's) */
        int o = CD_ST.gen[2 * t] >> 8;
        pg[t] = 0xFF;
        for (int k = 0; k < 2 * p; k++) if (ord[k] == o) pg[t] = grp[k];
    }
    m = 0;
    for (int t = 0; t < p; t++) { side[m] = CD_REF(t); sg[m++] = pg[t]; }
    for (int k = 2 * p; k < n && m < 2 * n1; k++) { side[m] = lf | ord[k] << 8; sg[m++] = grp[k]; }
    while (m < 2 * n1) { side[m] = 0; sg[m++] = 0xFF; }
    cd_pair(side, sg, m, 2 * p);
    CD_ST.gen_on = 1;
    CD_ST.efresh = 0;
}

/* The ties nobody plays, by strength as statespec's statesim: strength = the best 11's prices (CD_DT), squared;
   the home club's x 1.21; a match drawn 1 in 4 (0-0, 1-1, 2-2), else won by a weighted coin, 1-3 goals to fewer;
   level after the legs: the penalties, weighted 2:1 to the stronger. */
int cd_ident(int m, int i);             /* (the RI section: a pooled slot's identity) */
static u32 cd_below(u32 n) {            /* (below() for n past 65535: the product in 64 bits) */
    rng = rng * 1103515245u + 12345u;
    return (u32)(((unsigned long long)(rng >> 16) * n) >> 16);
}
static u32 cd_str(u16 w) {
    const u8 *s = GP_CDD + 260;
    int i = w >> 8, moff = s[0] | s[1] << 8, nmap = s[2] | s[3] << 8, np = s[4] | s[5] << 8, id = i;
    if (moff != 0xFFFF && i < nmap) id = cd_ident(moff + i, i);
    const u8 *p = id < 256 ? s + 6 + 2 * id : id - 256 < np ? s + 6 + 512 + 2 * (id - 256) : 0;
    u32 v = p ? (u32)(p[0] | p[1] << 8) : 5;
    if (v < 5) v = 5;
    return v * v;
}
static int cd_sim(u16 a, u16 b, int legs, int h) {     /* h: 0 a hosts (the first leg), 1 b -> 1 a through, 2 b */
    u32 sa = cd_str(a), sb = cd_str(b);
    int ga = 0, gb = 0;
    for (int l = 0; l < legs; l++) {
        int home_a = (l == 0) == (h == 0);
        u32 x = home_a ? sa * 121 / 100 : sa, y = home_a ? sb : sb * 121 / 100;
        int p, q;
        if (cd_below(100) < 26) { p = cd_below(3); q = p; }
        else { int w = cd_below(x + y) < x, gw = 1 + cd_below(3), gl = cd_below(gw); p = w ? gw : gl; q = w ? gl : gw; }
        ga += p; gb += q;
    }
    if (ga != gb) return ga > gb ? 1 : 2;
    return cd_below(3 * (sa + sb)) < 2 * sa + sb ? 1 : 2;
}

/* the calendar advance: 1 = a tie of the career club built into ko[0] (gp_install it), else 0 */
u32 cd_step_c(void) {
    if (!GP_CDT) return 0;
    if (CD_ST.magic != 0x4443 || CD_ST.season != GP_SEAS) {     /* (a new season: the cup from its start) */
        u8 *p = (u8 *)&CD_ST;
        if (CD_ST.magic != 0x4443) CD_ST.efresh = 0;   /* (a new career / an older save: no entry order) */
        for (u32 i = 0; i < __builtin_offsetof(struct cd_state, ent); i++) p[i] = 0;
        CD_ST.magic = 0x4443; CD_ST.season = GP_SEAS; CD_ST.gen_on = 0;
        if (!GP_CDFIRST) cd_make();
    }
    while (CD_ST.round < GP_CDT[1]) {
        int r = CD_ST.round;
        const u8 *rec = CDREC(r);
        if (GP_CDS1 && cd_n(r) == 32 && (int)GP_WK + 1 >= rec[0] && !CD_ST.built) {
            /* 4.0: the 1/32 on as the game's own knockout in slot 1 (GP_CDS1: its 64 team words), the career club in it:
               the round's pairs in bracket order, cd done for the season (CD_ST.round past the last) */
            int f = cd_first(r), me = 0;
            for (int q = 0; q < 32; q++)
                for (int sd = 0; sd < 2; sd++) {
                    u16 w = cd_side(f + q, sd);
                    GP_CDS1[2 * q + sd] = w && w != 0xFFFF ? w : 0xFFFF;
                    me |= w == GP_MGR;
                }
            if (me) { CD_ST.round = GP_CDT[1]; return 2; }
        }
        int w1 = rec[0], w2 = rec[1], legs = rec[2], host = rec[3], n = cd_n(r), first = cd_first(r);
        if ((int)GP_WK + 1 < w1 || CD_ST.built) return 0;
        rng = GP_SEAS * 7919u + r * 131u + first;
        if ((rec[5] & 1) && CD_ST.drawn != r + 1) {             /* (the pairs drawn: the previous round's ties) */
            int pf = cd_first(r - 1), pn = cd_n(r - 1);
            for (int i = 0; i < 4 && i < pn; i++) CD_ST.sd[i] = pf + i;
            for (int i = (pn < 4 ? pn : 4) - 1; i > 0; i--) { int j = below(i + 1); u8 x = CD_ST.sd[i];
                                                                  CD_ST.sd[i] = CD_ST.sd[j]; CD_ST.sd[j] = x; }
            CD_ST.drawn = r + 1;
        }
        for (int q = 0; q < n; q++) {
            int t = first + q;
            if (CD_ST.res[t]) continue;
            u16 a = cd_side(t, 0), b = cd_side(t, 1), ra = cd_raw(t, 0), rb = cd_raw(t, 1);
            int h = 0;                  /* (0: a hosts, 1: b hosts) */
            if (host == 2) h = below(2);
            else if (host == 4) {
                int pa_ = CD_ISREF(ra) && ra != CD_DRAWN ? ra >> 8 : -1, pb_ = CD_ISREF(rb) && rb != CD_DRAWN ? rb >> 8 : -1;
                int ha = pa_ >= 0 && pa_ < CDT && cd_hosted(pa_, a), hb = pb_ >= 0 && pb_ < CDT && cd_hosted(pb_, b);
                h = ha && !hb ? 1 : !ha && hb ? 0 : below(2);
            }
            CD_ST.home[t] = h;
            if ((a == GP_MGR || b == GP_MGR) && a && b && a != 0xFFFF && b != 0xFFFF) {   /* the career club's */
                cd_ko(&GP_ST.ko[0], h ? b : a, h ? a : b, w1, w2, legs);
                CD_ST.built = 1; CD_ST.bt = t; CD_ST.pad = 1;   /* (pad: the harness's trace) */
                return 1;
            }
            if (a == GP_MGR || b == GP_MGR) CD_ST.pad = 0x80 | (a == 0xFFFF || b == 0xFFFF ? 2 : 4);
            int w = GP_CDFIRST ? CDTIE(t)[4] : 0;               /* (the real result, the world's first season) */
            if (!w) w = !a ? 2 : !b ? 1 : cd_sim(a, b, legs, h);   /* (else by strength) */
            CD_ST.res[t] = w;
        }
        CD_ST.round = r + 1;
    }
    return 0;
}

/* 4.0: a Coppa Italia Serie D entrant this season (team word = file | ordinal << 8: the Serie D file, its ordinal's
   division of the season in the Serie D groups) - InitNewSeason gives it no cup / league cup (gp_cup12) */
u32 cd_member_c(u32 team) {
    const u8 *dt = GP_CDD;
    if (!GP_CDT || !dt || !GP_SLT || (team & 0xFF) != GP_CDT[2]) return 0;
    int i = team >> 8 & 0xFF, b = dt[4 + i];
    if (b == 0xFF) return 0;
    int dv = b + GP_SLT[(dt[2] | dt[3] << 8) + i];
    return dv >= dt[0] && dv < dt[0] + dt[1];
}

static void cd_done(struct gp_ko *k) {  /* gp_rec_c: our CD tie decided -> its result */
    if (!CD_ST.built || k->tw[0] == NOC) return;
    CD_ST.res[CD_ST.bt] = k->team[k->tw[0]] == cd_side(CD_ST.bt, 0) ? 1 : 2;
    CD_ST.built = 0;
    CD_ST.pad |= 0x40;
}
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
    GP_ALIVE = 0xFFFFFFFF;
    if (KT2(k)) return 0;               /* (a type-2 contest: the game's own stages) */
    int g = k->gcur, p0 = k->gp0[g], np = k->gp0[g + 1] - p0, c = 0;
    for (int i = 0; i < np && i < 64; i++) k->pw[p0 + i] = GP_PT[i];
    resolve(k);
    int me = kidx(k, GP_MGR);           /* the contest's human-clubs count (+4Bh): the game takes 1 off for every
                                           match a human club loses (cseg_2ABF0), a series' lost game 1 too -> a
                                           later elimination left it FFFFh, the next round's entry 'still in' (FFh)
                                           and PARTITA without a match hung (MLS): ours, the club still in the bracket */
    GP_ALIVE = me != NOC;
    for (int t = 0; t < k->ntie && GP_ALIVE; t++)
        if (k->tw[t] != NOC && k->tl[t] == me && k->tw[t] != me) GP_ALIVE = 0;
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

u32 GP_DEFWK, GP_ADVWK;                 /* 4.0: a deferred stage build's week (its stage's last day), the week gp_adv builds
                                           from (the advance's own week is already the next league day's) */
void gp_defer_c(void) {                 /* (gp_defer: play-off GP_BPIC built at the calendar advance from week GP_WK on) */
    set_pend(GP_BPIC + 1, GP_WK);
    GP_DEFWK = GP_WK + 1;
}

/* the calendar advance (gp_adv, cseg_8EA82's callers): a pending 'then_build' due -> its play-off index + 1 (then
   gp_build with GP_BWEEK = this week), else 0 */
u32 gp_adv_c(void) {
    if (!GP_ST.pend || GP_ST.pseas != GP_SEAS || GP_WK < GP_ST.pweek) return 0;
    u32 t = GP_ST.pend;
    GP_ST.pend = 0;
    GP_ADVWK = GP_DEFWK ? GP_DEFWK - 1 : GP_WK;
    GP_DEFWK = 0;
    return t;
}

static void ko_copy(struct gp_ko *d, const struct gp_ko *s) {   /* (no memcpy in the exe: byte by byte) */
    volatile u8 *o = (volatile u8 *)d;
    const u8 *i = (const u8 *)s;
    for (unsigned n = 0; n < sizeof *d; n++) o[n] = i[n];
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
    if (k->kind == K_CUPD) { cd_done(k); return; }
    GP_LAST = 0;
    int left = 0;
    for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++) if (k->pw[p] == NOC) left++;
    if (!left && g + 1 < k->ngr) {      /* (this match ended its round: the later ones all decided without a match -
                                           a skip_if_same / gap round, CRC's Gran Final of one club - end the contest
                                           here, the game's own last round: gp_rec, +59h = +57h + 1; else the game
                                           draws a next round gp_perm cannot build and hangs) */
        static struct gp_ko t;
        ko_copy(&t, k);
        int g2 = g + 1, over = 1;
        while (g2 < t.ngr && build_game(&t, g2) == 0) g2++;
        resolve(&t);
        for (int i = 0; i < t.ntie; i++) if (t.tw[i] == NOC) over = 0;
        if (g2 >= t.ngr && over) {
            ko_copy(k, &t);
            k->gcur = t.ngr - 1;
            GP_LAST = 1;
        }
    }
    if (k->bye[5] && k->ntie && k->tw[k->ntie - 1] != NOC) {   /* (its final decided: the next one, once, from the
                                           week after: the advance right after the final still has slot 4's contest
                                           in hand, a build there was lost - 4.0's Trofeo) */
        set_pend(k->bye[5], GP_WK + 1);
        GP_DEFWK = 0;
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
    if (k->kind == K_CUPD) return;      /* (a Coppa Italia Serie D tie: not a play-off of the spec) */
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
        for (int i = 0; i < 9; i++) GP_LOG.top[i] = GP_TOPW[i];
        GP_LOG.tag = 0x474C5047;        /* 'GPLG' */
    }
    if (GP_CDT && GP_CDD) cd_rank();          /* (the Coppa D: the Serie D groups' final places) */
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
u8 GP_WORLD;

/* SeasonFinished (gp_sack, before the season review): the career club won our played group contest (the Poule) ->
   its record line's name (the season record's 4th line: a Serie D club plays no European cup), else 0. Test builds
   (GPLAY_FORCE): the club is made the winner (the review's DA11B too: no European trophy for it, gp_sack's guard). */
/* 4.0 stage titles (longtable.stage_table): tab: dw n; dw S_MAGIC, S_FROZEN, S_GRP offsets (split's state in a league
   buffer), dw its magic; dd the career team word's address; dw the weeks table's offset; n records of 128 B: key (41 B:
   the DIY+4 title) + pad, [5 stages][4 groups] dw long-title offsets from tab, the same for the short ones (0 = none),
   5 db the stage's first day (255 = none) + pad. */
static const u8 *st_rec(const u8 *lg, const u8 *tab) {      /* lg's record, or 0 */
    if (w16(lg + w16(tab + 2)) != w16(tab + 8)) return 0;
    const u8 *r = tab + 16;
    for (int i = 0, n = w16(tab); i < n; i++, r += 128) {
        int k = 0;
        while (k < 41 && lg[4 + k] == r[k] && r[k]) k++;
        if (k == 41 || lg[4 + k] == r[k]) return r;
    }
    return 0;
}
static int st_grp(const u8 *lg, const u8 *tab) {           /* the career club's group in lg (0 if none) */
    const u16 *ct = *(const u16 * const *)(tab + 10);
    for (int j = 0, nc = w16(lg + 0x31); j < nc && j < 64; j++)
        if (w16(lg + 0x12D + 2 * j) == *ct) return lg[w16(tab + 6) + j] & 3;
    return 0;
}
/* longtable lt_stage (a table's OnRestore): the table title of diy's current stage / the career club's group */
u32 gp_stitle_c(const u8 *diy, const u8 *tab) {
    const u8 *r = st_rec(diy, tab);
    if (!r) return 0;
    int s = diy[w16(tab + 4)];
    if (s >= 5) return 0;
    const u8 *row = r + 42 + 8 * s;
    int g = st_grp(diy, tab), o = w16(row + 2 * g);
    if (!o) o = w16(row);
    return o ? (u32)(tab + o) : 0;
}
/* 4.0 group headers in a long table (longtable lt_d5 / lt_row / lt_end; the labels: gp_hlabel_c, 3.3.6's): the
   table's places in virtual rows - a header before each group's first place (split's group of its row, tab = the
   stage table's header) - and the window of rows virtual rows from cur: GP_HF / GP_HL its first / last place,
   GP_HP[place] = 0x80 | group when its header is shown before it (| 0x40: an empty row before the header), GP_HGP[place] its place in the group, GP_HV the
   virtual rows (ScrollDown's limit), GP_HON = headers in this table. */
u8 GP_HP[65], GP_HGP[65], GP_HG[65];   /* (GP_HG: every place's group, for zones by group) */
u32 GP_HV, GP_HF, GP_HL, GP_HON;
extern const u8 GP_HLT[];                /* zones.header_labels: [n dw] + n x (title 41 B, 4 labels of 24 B) */
u32 gp_hlabel_c(const u8 *t, u32 g) {   /* a group's header label (3.3.6: ZONA A / B, EASTERN / WESTERN CONFERENCE) */
#ifndef HDR_TEST
    u32 n = *(const u32 *)GP_HLT;
    const u8 *e = GP_HLT + 4;
    if (g > 3)
        return 0;
    for (u32 k = 0; k < n; k++, e += 41 + 4 * 24) {
        u32 i = 0;
        while (i < 40 && e[i] && e[i] == t[4 + i])
            i++;
        if ((i == 40 || (!e[i] && !t[4 + i])) && e[41 + 24 * g])
            return (u32)(e + 41 + 24 * g);
    }
    return 0;
#endif
#ifdef HDR_TEST
    static const char *L[4] = { "GROUP 1", "GROUP 2", "GROUP 3", "GROUP 4" };
    return g < 4 ? (u32)L[g] : 0;
#else
    (void)t; (void)g;
    return 0;
#endif
}
void gp_hplan_c(const u8 *t, const u8 *tab, u32 cur, u32 rows, u32 off) {
    int n = w16(t + 0x51), g[65], hdr = 0;
    if (n > 64) n = 64;
    for (int k = 1; k <= n; k++) { GP_HP[k] = 0; GP_HGP[k] = k; g[k] = 0; }
    if (!off && tab && w16(t + w16(tab + 2)) == w16(tab + 8)) {
        for (int k = 1; k <= n; k++) g[k] = t[w16(tab + 6) + w16(t + 0x6D + 2 * (k - 1)) / 18] & 3;
        for (int k = 2; k <= n; k++) if (g[k] != g[1]) hdr = 1;
        for (int k = 1; k <= n && hdr; k++) if ((k == 1 || g[k] != g[k - 1]) && !gp_hlabel_c(t, g[k])) hdr = 0;
    }
    GP_HON = hdr;
    int v = 0, h0[65], s0[65];          /* h0[k]: the virtual row of place k's header (or -1), its own row after;
                                           s0[k]: an empty row before every header but the first (Davide, 4.0) */
    for (int k = 1; k <= n; k++) {
        s0[k] = hdr && k > 1 && g[k] != g[k - 1] ? v++ : -1;
        h0[k] = hdr && (k == 1 || g[k] != g[k - 1]) ? v++ : -1;
        v++;
    }
    GP_HV = v;
    int mx = v > (int)rows ? v - (int)rows : 0, c = (int)cur > mx ? mx : (int)cur, end = c + (int)rows, gp = 0;
    GP_HF = 0; GP_HL = 0;
    v = 0;
    for (int k = 1; k <= n; k++) {
        gp = h0[k] >= 0 || k == 1 ? 1 : gp + 1;
        GP_HGP[k] = hdr ? gp : k;
        GP_HG[k] = (u8)g[k];
        v = h0[k] >= 0 ? h0[k] + 1 : v;
        if (v >= c && v < end) {
            if (!GP_HF) GP_HF = k;
            GP_HL = k;
            if (h0[k] >= c) GP_HP[k] = 0x80 | (s0[k] >= c ? 0x40 : 0) | g[k];
        }
        v++;
    }
    if (!GP_HF) { GP_HF = 1; GP_HL = 1; }
}

/* gp_cal (the career calendar's league row): the short title of the league day in week wk (lg = slot 0's buffer) */
u32 gp_scal_c(const u8 *lg, const u8 *tab, u32 wk) {
    if (!lg || !tab) return 0;
    const u8 *r = st_rec(lg, tab);
    if (!r) return 0;
    const u8 *weeks = lg + w16(tab + 14);
    int d = -1;
    for (int i = 0; i < 64; i++) if (weeks[i] == (u8)wk) { d = i; break; }
    if (d < 0) return 0;
    int s = 0;
    for (int k = 1; k < 5; k++) if (r[122 + k] != 255 && d >= r[122 + k]) s = k;
    const u8 *row = r + 82 + 8 * s;
    int g = s ? st_grp(lg, tab) : 0, o = w16(row + 2 * g);
    if (!o) o = w16(row);
    return o ? (u32)(tab + o) : 0;
}

/* 4.0 after a career load (gp_repoint, after ProcessCareerFile): every slot buffer's long-name pointer (DIY+27h,
   absolute: stale in a save from another build - 3.x, an older 4.0) from its contest struct (D8CAA[k], rebuilt from
   this exe's records: names at struct + 5 + [struct + 5], [long, short] per division, the career division for slot 0);
   a title (DIY+4, '<country> <long>') whose name part differs is rebuilt from its country prefix (a 4.0 test save's
   overflowed 'ARGENTINA LIGA PROFESIONAL DE FUTBO'). base: the strings' base (aChairmanScenes). */
/* 4.0 after a career load from another build: phase 0, the running knockouts' contest names from this exe's play-off
   names (nm: the career country's GP_NM, long / short / record rel per play-off); phase 1, every season record whose
   league line (leagueStringOffset, +16h) is not the start of a string of the names (an old build's offset: ' . PROF.',
   'ION' ...) gets the career league's name (slot 0's DIY+27h, repointed). */
static int str_ok(const u8 *s) {        /* the start of a name string (the names table / the game's strings)? */
    if (s[-1] || s[0] < 'A' || s[0] > 'Z') return 0;
    int n = 0;
    while (s[n] && n < 41) {
        u8 c = s[n++];
        if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == ' ' || c == '.' || c == '-' || c == '\'' || c == '/' || c == '&' || c == '(' || c == ')')) return 0;
    }
    return n >= 2 && !s[n];
}
void gp_fixload_c(const u32 *nm, u8 *recs, u32 base, u8 *const *slots, u32 phase) {
    if (phase == 0) {
        if (!nm) return;
        for (int i = 0; i < 2; i++) {
            struct gp_ko *k = &GP_ST.ko[i];
            if (k->magic != MAGIC || k->season != GP_SEAS) continue;
            u8 *c = k->con, *names = c + 5 + c[5];
            *(u32 *)names = nm[3 * k->pi];
            *(u32 *)(names + 4) = nm[3 * k->pi + 1];
        }
        return;
    }
    if (!slots || !recs || !slots[0]) return;
    u32 lg = *(const u32 *)(slots[0] + 0x27), cup = slots[1] ? *(const u32 *)(slots[1] + 0x27) : 0;
    for (int i = 0; i < 64; i++) {
        u8 *r = recs + 106 * i;
        if (!r[2]) break;
        for (int f = 0; f < 4; f++) {   /* +16h the league, +1Ah the national cup, +1Eh / +22h the continental cups */
            u32 *o = (u32 *)(r + 0x16 + 4 * f);
            if (!*o || str_ok((const u8 *)(base + *o))) continue;
            *o = f == 0 && lg ? lg - base : f == 1 && cup ? cup - base : 0;
        }
    }
}

void gp_repoint_c(u8 *const *slots, u8 *const *structs, u32 base, u32 div) {
    for (int k = 0; k < 5; k++) {
        u8 *b = slots[k];
        const u8 *s = structs[k];
        if (k == 2 || k == 3) continue; /* (never the European / continental slots: at a load D8CAA[3] may already
                                           be conti's next contest while the buffer is still this season's) */
        if (!b || !s || !b[4]) continue;
        const u8 *nm = s + 5 + s[5] + (k == 0 ? 8 * div : 0);
        const u8 *ln = (const u8 *)(base + *(const u32 *)nm);
        *(const u8 **)(b + 0x27) = ln;
        int n = 0;
        while (ln[n] && n < 40) n++;
        if (!n) continue;
        int p = -1;                     /* the country prefix: up to the name's first word in the title */
        for (int i = 0; i < 34 && b[4 + i]; i++)
            if ((i == 0 || b[3 + i] == ' ')) {
                int j = 0;
                while (ln[j] && ln[j] != ' ' && b[4 + i + j] == ln[j]) j++;
                if (!ln[j] || ln[j] == ' ') { p = i; break; }
            }
        if (p <= 0 || p + n > 34) continue;
        int same = 1;
        for (int j = 0; j <= n; j++) if (b[4 + p + j] != ln[j]) { same = 0; break; }
        if (same) continue;
        for (int j = 0; j < n; j++) b[4 + p + j] = ln[j];
        for (int j = p + n; j < 35; j++) b[4 + j] = 0;
    }
}

/* The career club's result in a decided knockout, as the season record's codes (FillManagementRecordInfo): 1 WINNERS,
   -100 FINALIST (the last round lost), -101 REACHED SEMI-FINAL, -102 REACHED QUARTER-FINAL, -110 - n KNOCKED OUT IN
   ROUND n; 0: not in it / undecided. */
#ifndef GP_RLFORCE
#define GP_RLFORCE 0                    /* test builds (GPLAY_RLFORCE=code, never release): the career club's result in
                                           a contest it is in, read by the record lines only (no game flow) */
#endif
static int club_res(struct gp_ko *k, u16 mgr) {
    int me = mgr ? kidx(k, mgr) : NOC;
    if (me == NOC || !k->ntie) return 0;
    if (GP_RLFORCE) return GP_RLFORCE;
    resolve(k);
    if (k->tw[k->ntie - 1] == me) return 1;
    for (int t = 0; t < k->ntie; t++) {
        if (k->tl[t] != me) continue;
        int r = 0;
        while (r + 1 < k->nrs && t >= k->gt0[r + 1]) r++;
        int d = k->nrs - 1 - r;
        return d == 0 ? -100 : d == 1 ? -101 : d == 2 ? -102 : -(110 + r + 1);
    }
    return 0;
}

/* SeasonFinished (gp_sack): the season record's extra lines (GP_RLN names, GP_RLC result codes; the count returned):
   the Poule won (its record name, WINNERS); a stage title's knockout played (4.0 ARG: TORNEO APERTURA / CLAUSURA,
   TROFEO DE CAMPEONES: its long name and the club's result, from GP_ST.dec - stage_done - or ko[0]); a title
   play-off played (MLS CUP PLAYOFFS, CAN, AUS, CRC, MLT: the league's name with WINNERS, else the play-off's long
   name with the round reached). GP_RLPOULE: the Poule's line (the test builds' DA11B). */
u32 GP_RLN[4];
s8 GP_RLC[4];
u32 GP_RLPOULE;
u8 *GP_REC;                             /* the season record (106 B, gp_sack: GetCurrentSeasonPointer), or 0 */
const u32 *GP_CMB;                      /* the country's stage titles won together: one name per mask (bit = stage 0..2,
                                           relative, 0: none; gplay.py names_lines GPC) */
static int rl_rank(int c) {             /* a line's worth to keep (lower: replaced first by a title won): KNOCKED OUT IN
                                           ROUND n by n, then '-', still in, 4th, 3rd, quarter, semi, final lost */
    if (c <= -110) return -(c + 110);
    static const s8 ord[] = { -106, -104, -105, -103, -102, -101, -100, 2 };
    for (int i = 0; i < 8; i++) if (c == ord[i]) return 40 + i;
    return 48;
}
static int rl_n, rl_w;
static void rl_add(u32 name, int code) {
    if (rl_n >= 4) return;
    if (code == 1) {                    /* (titles won first, in their order) */
        for (int i = rl_n; i > rl_w; i--) { GP_RLN[i] = GP_RLN[i - 1]; GP_RLC[i] = GP_RLC[i - 1]; }
        GP_RLN[rl_w] = name; GP_RLC[rl_w++] = 1; rl_n++;
    } else { GP_RLN[rl_n] = name; GP_RLC[rl_n++] = (s8)code; }
}
u32 gp_rlines_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    int kstage = -1, wmask = 0;
    u32 wname[3] = { 0, 0, 0 };
    rl_n = rl_w = 0;
    GP_RLPOULE = 0;
    int live = GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS && k->magic == MAGIC && k->season == GP_SEAS;
    if (live && k->kind == K_STAGE) {
        const u8 *s = po_at(k->pi);
        kstage = s ? s[3] : -1;
    }
    for (int st = 0; st < 3 && GP_NM; st++) {       /* (the stage titles decided before: Apertura, Clausura, Trofeo) */
        const struct gp_dec *x = &GP_ST.dec[st];
        if (st == kstage || x->season != GP_SEAS || !x->done || !x->pad[0] || !x->pad[1]) continue;
        if (x->pad[0] == 1) { wmask |= 1 << st; wname[st] = GP_NM[3 * (x->pad[1] - 1)]; }
        else rl_add(GP_NM[3 * (x->pad[1] - 1)], (s8)x->pad[0]);
    }
    u32 kn = 0;                         /* ko[0]'s line (after the stage titles) */
    int kr = 0;
    if (live && KT2(k)) {
        int me = kidx(k, GP_MGR);
        if (me != NOC) {
            if (GP_FORCE) { k->tw[0] = me; k->tl[0] = me ? 0 : 1; }
            if (k->tw[0] == me) { kn = *(u32 *)k->bye; kr = 1; GP_RLPOULE = 1; }
        }
    } else if (live && (k->kind == K_TITLE || k->kind == K_STAGE) && GP_NM) {
        int r = club_res(k, GP_MGR);    /* (SeasonFinished comes before the season end's gp_season: the contest itself) */
        if (r == 1 && k->kind == K_STAGE && kstage >= 0 && kstage < 3) { wmask |= 1 << kstage; wname[kstage] = GP_NM[3 * k->pi]; }
        else if (r) { kn = GP_NM[3 * k->pi + (r == 1 && k->kind == K_TITLE ? 2 : 0)]; kr = r; }
    }
    if (wmask & (wmask - 1) && GP_CMB && GP_CMB[wmask]) {   /* (several stage titles of the league: one line, Davide) */
        rl_add(GP_CMB[wmask], 1);
        wmask = 0;
    }
    for (int st = 0; st < 3; st++)      /* (else one line each, in stage order) */
        if (wmask & 1 << st) rl_add(wname[st], 1);
    if (kr) rl_add(kn, kr);
    if (GP_REC) {                       /* each into its line if there already, else the first free line 4 / 3 / 2; a
                                           title won with none free: in place of the game's weakest non-winning line (an
                                           elimination, Davide), not ours */
        int ours = 0;
        for (int i = 0; i < rl_n; i++) {
            int at = -1;
            for (int o = 3; o >= 1 && at < 0; o--)  /* (already there: a second pass - REGISTRO GESTIONE's refresh,
                                                       gp_mrec - only restores its code) */
                if (!(ours & 1 << o) && *(u32 *)(GP_REC + 22 + 4 * o) == GP_RLN[i]) at = o;
            for (int o = 3; o >= 1 && at < 0; o--) if (!*(u32 *)(GP_REC + 22 + 4 * o)) at = o;
            if (at < 0 && GP_RLC[i] == 1) {
                int best = 99;
                for (int o = 3; o >= 1; o--) {
                    int c = (s8)GP_REC[86 + o];
                    if (ours & 1 << o || c == 1 || rl_rank(c) >= best) continue;
                    best = rl_rank(c); at = o;
                }
            }
            if (at < 0) continue;
            *(u32 *)(GP_REC + 22 + 4 * at) = GP_RLN[i];
            GP_REC[86 + at] = (u8)GP_RLC[i];
            ours |= 1 << at;
        }
    }
    return rl_n;
}

u32 gp_pwin_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS || k->magic != MAGIC || k->season != GP_SEAS)
        return 0;
    int me = kidx(k, GP_MGR);
    if (me == NOC) return 0;
    if (KT2(k)) {
        if (GP_FORCE) { k->tw[0] = me; k->tl[0] = me ? 0 : 1; }
        return k->tw[0] == me ? *(u32 *)k->bye : 0;
    }
    if (k->kind != K_TITLE || !GP_NM || !k->ntie) return 0;   /* a played title play-off (CAN, AUS, CRC, MLT) won:
                                           its last tie's winner (SeasonFinished comes before the season end's
                                           gp_season: the contest itself, not GP_OUT); the line: the league's name
                                           (compile_spec's league_names). The club keeps its table place. */
    resolve(k);
    return k->tw[k->ntie - 1] == me ? GP_NM[3 * k->pi + 2] : 0;
}

/* RI_TAB (ripool.table_bytes): a league pool's slot (kind 0) of world w with global g -> its lowest level's first
   division and base division (gp_sack_c) */
static int ri_league_slot(const u8 *t, int w, int g, int *low, int *base) {
    int nf = *t++;
    for (int fi = 0; fi < nf; fi++) {
        int world = t[0], np = t[2], nsp = t[9];
        t += 10 + nsp;
        for (int k = 0; k < np; k++) {
            int kind = t[0], n = t[1];
            const u8 *p = t + 2;
            if (kind == 0) {
                int lw = p[0], ns = p[1] | p[2] << 8;
                const u8 *sl = p + 3;
                for (int i = 0; world == w && i < ns; i++)
                    if ((sl[4 * i] | sl[4 * i + 1] << 8) == g) { *low = lw; *base = sl[4 * i + 2]; return 1; }
                t = sl + 4 * ns + n + n;
            } else {
                int ns = p[3];
                const u8 *ps = p + 4 + 4 * ns;
                int ne = ps[n];
                t = ps + n + 1 + 2 * ne + n;
            }
        }
    }
    return 0;
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
    int low, base;                       /* the off-file pools (ripool: RI_TAB; a swap never takes the manager's club) */
    if (GP_RIT && ri_league_slot(GP_RIT, GP_WORLD, g, &low, &base)) {
        int dv = base + GP_SLT[g];
        return dv >= low && dv < GD && m >= n - GP_LG[13 + 6 * dv + 3];
    }
    const u8 *t = GP_RST;
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
                           __builtin_offsetof(struct gp_ko, slot), __builtin_offsetof(struct gp_state, rn),
                           __builtin_offsetof(struct gp_ko, gcur) };

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
   dw map offset (words in RI_STATE.maps), dw slots (the file's records); db spares; spares x db ordinal. */
enum { RIS = 256, RF = 8, RP = 20, RQT = 192, RO = 16, RMT = 640 };
_Static_assert(RF == CD_RF, "cd_season's view of the pools' files");
struct ri_state { u8 init[RF]; u8 qn[RP]; u16 q[RQT]; u16 ovr[RP][RO]; u16 maps[RMT]; };   /* (maps: per file its
                                                   slots only, from the table's map offset) */
struct ri_file { u8 *init; u16 *map; int n; };   /* (a file's view of RI_STATE) */
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
int cd_ident(int m, int i) { return m < RMT && RI_STATE.maps[m] ? RI_STATE.maps[m] - 1 : i; }   /* (gplay's Coppa D) */
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
        if (run && *f->init == 1) {
            for (int i = 0; i < n; i++) q[i] = RIS + order[i];
            *qn = n;
        }
        for (int i = 0; run && i < ns && i < RIS && ri_no < RIO && m < *qn && no < 64; i++) {
            const u8 *s = sl + 4 * i;
            int g = s[0] | s[1] << 8, base = s[2];
            int o = base + slt[g], nn = base + copy[g];
            if (o < low || nn <= o) continue;   /* (relegated from the lowest level) */
            if (g == manager) {                 /* never the manager's: re-admitted, its slot and identity stay in the
                                                   lowest level (a relegated manager is sacked by gp_sack, so this is
                                                   a job taken at the season end - accepted before ContinueCareer's
                                                   moves - at a club going down: left below it, the career trapped) */
                copy[g] = slt[g];
                continue;
            }
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
        if (run && *f->init == 1) {
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
        int base = t[3] | t[4] << 8, moff = t[5] | t[6] << 8, nmap = t[7] | t[8] << 8, nsp = t[9];
        struct ri_file fv = { &RI_STATE.init[fi < RF ? fi : RF - 1], RI_STATE.maps + moff, nmap }, *f = &fv;
        int run = w == world && fi < RF && moff + nmap <= RMT;
        if (run && !*f->init) {                 /* (a new career / an older save: identities, the pools' first order) */
            for (int i = 0; i < nmap; i++) f->map[i] = 0;
            *f->init = 1;
        }
        const u8 *sp = t + 10;
        t = sp + nsp;
        int p0 = pi;
        for (int k = 0; k < np; k++) {
            int n = t[1];
            t = ri_pool(t, f, fi, RI_STATE.q + qo, RI_STATE.qn + pi, slt, copy, sr,
                        run && pi < RP && qo + n <= RQT, pi, base, sp, nsp, p0, np);
            qo += n;
            pi++;
        }
        if (run) *f->init = 2;
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
void ri_apply(u8 *buf, const u8 *orig, const u8 *pool, int fi, int moff) {
    int n = buf[0] << 8 | buf[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int i = 0; i < n && i < RIS && moff + i < RMT; i++) {
        int id = RI_STATE.maps[moff + i];
        if (!id--) continue;
        if (id < RIS && id < n) ri_copy(buf + 2 + 684 * i, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(buf + 2 + 684 * i, pool + 2 + 684 * (id - RIS));
    }
}

/* The career's team cache after a swap: every cached record of a swapped slot (team word file | slot << 8) gets its
   new identity's record. recs = the cache's records, n of them; file = the team file; orig / pool / fi as for
   ri_apply. */
void ri_cache(u8 *recs, int n, int file, const u8 *orig, const u8 *pool, int fi, int moff) {
    int nf = orig[0] << 8 | orig[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int k = 0; k < n; k++) {
        u8 *r = recs + 684 * k;
        int i = r[1];
        if (r[0] != file || !(RI_SWAPPED[fi][i >> 3] & 1 << (i & 7))) continue;
        if (moff + i >= RMT) continue;
        int id = RI_STATE.maps[moff + i] ? RI_STATE.maps[moff + i] - 1 : i;
        if (id < RIS && id < nf) ri_copy(r, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(r, pool + 2 + 684 * (id - RIS));
    }
}
