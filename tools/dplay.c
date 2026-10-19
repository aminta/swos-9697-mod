/* Italian play-offs and play-outs of a career world at the season end (tools/dplay.py, rules 2025-26:
   FIGC C.U. 39/A for Serie B, NOIF art. 49 + C.U. 114/A for Serie C; notes/world-2025-26.md).

   Compiled for the game (tools/cobj.py, linked into dplay's obj1 page, called from the season end's asm after the
   last division's play-off step) and natively for the tests (internal/world2526/dplay/dpt.c).

   Input: the final tables (places in order) of Serie B (t[0]) and of the Serie C groups (t[1..ng]), captured while
   the season end has each division in DIY. Output: the extra moves the game's own promoted / relegated counts do not
   make (Serie B promoted 2, relegated 3; groups promoted 1, relegated 0):
   - Serie B: the 3rd up directly if it leads the 4th by more than 14 points, else the play-off winner (3rd-8th:
     preliminary 5v8, 6v7 single at the better placed's ground, a draw after extra time -> the better placed; semis
     3rd v W(6v7), 4th v W(5v8), two legs, return at the 3rd / 4th's, level -> the better placed; final two legs,
     return at the better placed's, level -> the better placed, or extra time + penalties when level on points);
   - Serie B: the 17th down directly if the 16th leads it by more than 4 points, else the play-out loser (two legs,
     first leg at the 17th's, level -> the 16th stays, or extra time + penalties when level on points);
   - Serie C: the play-off winner up (per group R1 5v10, 6v9, 7v8 and R2 the 3 winners + the 4th, single at the
     better placed's, a draw -> the better placed; national R1 the 6 group qualifiers + the 3 thirds + the Coppa
     Italia Serie C winner, 5 seeds (thirds, cup winner, best qualifier), seeded draw, two legs, return at the seed's,
     level -> the seed; R2 the 5 winners + the 3 seconds, 4 seeds (seconds, best R1 winner), the same; Final Four free
     draw, semis and final two legs, extra time + penalties). Until the world has the league cups the cup winner's
     place goes to the best 11th of the groups (Davide, temporary).
   'Better placed' across groups: place, points, wins, goals scored, lot. A tie is decided by the clubs' points
   (strength ~ points + 20, squared, as uefaq's ties; home side +10%): single matches level after extra time 22% of
   the time, two-legged ties level on aggregate 12%. */

#ifndef DP_FORCE
#define DP_FORCE 0
#endif
/* (test builds, DPLAY_FORCE >= 16: the play-out is held whatever the points) */
#define OUT_HELD(t) ((t)[15].pts <= (t)[16].pts + 4 || DP_FORCE >= 16)

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;

enum { NT = 24, NDIV = 5 };
struct dp_row { u16 team, glob, won, gf, ga, pts; };            /* a place of a final table (12 B) */
struct dp_in {
    u8 ng, pad[3];                      /* C groups */
    u8 n[NDIV], pad2[3];                /* clubs per table (0 = not captured) */
    struct dp_row t[NDIV][NT];          /* t[0] Serie B, t[1..ng] the groups */
    u16 po_win, out_win;                /* the career club's play-off / play-out played in slot 4: its winner's team
                                           number (0 = none: simulated) */
    u16 mgr, week;                      /* dp_lend: the career club's team number, the league's last week */
    u16 cpo_win;                        /* the career club's Serie C play-off: its winner (0 = simulated) */
    u8 mdiv, pad3;                      /* dp_lend: the career club's table (0 Serie B, 1.. the groups) */
    u16 cupw;                           /* the Coppa Italia Serie C winner (a played final: dp_cupw), 0 = unknown */
};
/* the career club's play-off / play-out (Serie B) or play-off (Serie C) in slot 4 (dp_lend; saved with the career,
   tmdFileBuffer): its clubs in the contest's team list order */
enum { SN = 28, SR = 20 };
struct dp_srow { u16 team, played, won, drawn, lost, gf, ga, pts; };    /* a final table's place (16 B) */
struct dp_save {
    u16 magic, res;                     /* 'DP' while it runs; res = the last round's winner (dp_rec) */
    u8 kind, n, season, cup;            /* 1 B play-off (6), 2 B play-out (2), 3 C play-off (28); season: the glue's;
                                           cup = the index of the Coppa Italia Serie C winner's place */
    u16 team[SN], pts[SN];
    u8 place[SN], group[SN];            /* place (0-based) in its table: 0 Serie B, 1.. the groups */
    u8 prio[SN];                        /* a level tie goes to the lower prio (dp_draw): the place, the seed */
    u8 won[SN], gf[SN];
    u8 rb[8], d1, d2, sg[2];            /* round bytes, first and last week; sg: the divisions whose tables were
                                           simulated early (Serie C: the other groups), their tables: */
    struct dp_srow srow[2][SR];
};
struct dp_save *DP_SVP;                 /* (set by the glue: DP_ST) */
struct dp_save DP_ST;                   /* the running state (the season end may clear the saved copy) */
enum { K_DIRECT = 1, K_PRE, K_SEMI, K_FINAL, K_OUT, K_GR1 = 10, K_GR2, K_NR1, K_NR2, K_FFS, K_FFF };
enum { H_PLAY, H_LEVEL, H_PENS };       /* how a tie ended: played out, level -> the rule's club, e.t. / penalties */
struct dp_tie { u8 kind, a, b, win, how, pad[3]; };            /* a = host (single) / return host, clubs as div*NT+place */
struct dp_mv { u16 glob, team; s8 delta; u8 club, pad[2]; };
struct dp_out {
    u8 nmv, ntie, pad[2];
    struct dp_mv mv[4];
    struct dp_tie tie[48];
};
struct dp_in DP_IN;
struct dp_out DP_OUT;
/* layout for the asm glue and the tests */
const u32 DP_LAYOUT[] = { sizeof(struct dp_in), sizeof(struct dp_out), sizeof(struct dp_row), NT,
                          __builtin_offsetof(struct dp_in, n), __builtin_offsetof(struct dp_in, t),
                          __builtin_offsetof(struct dp_out, mv), sizeof(struct dp_mv),
                          __builtin_offsetof(struct dp_in, po_win), __builtin_offsetof(struct dp_in, mgr),
                          sizeof(struct dp_save), __builtin_offsetof(struct dp_save, kind),
                          __builtin_offsetof(struct dp_save, team), __builtin_offsetof(struct dp_save, pts),
                          __builtin_offsetof(struct dp_save, prio), __builtin_offsetof(struct dp_save, rb),
                          __builtin_offsetof(struct dp_in, cpo_win), __builtin_offsetof(struct dp_in, mdiv),
                          __builtin_offsetof(struct dp_save, sg), __builtin_offsetof(struct dp_save, srow),
                          sizeof(struct dp_srow), __builtin_offsetof(struct dp_in, cupw) };

static u32 rng;
static u32 below(u32 n) {
    rng = rng * 1103515245u + 12345u;
    return ((rng >> 16) * n) >> 16;
}

#define DIV(c) ((c) / NT)
#define PL(c) ((c) % NT)
static const struct dp_row *row(int c) { return &DP_IN.t[DIV(c)][PL(c)]; }
static u8 lot[NDIV * NT];

static int better(int a, int b) {       /* 1 if club a is better placed than club b */
    const struct dp_row *x = row(a), *y = row(b);
    if (PL(a) != PL(b) || DIV(a) == DIV(b)) return PL(a) < PL(b);
    if (x->pts != y->pts) return x->pts > y->pts;
    if (x->won != y->won) return x->won > y->won;
    if (x->gf != y->gf) return x->gf > y->gf;
    return lot[a] < lot[b];
}

static u32 str2(int c, int home) {
    u32 s = row(c)->pts + 20;
    if (home) s = s * 11 / 10;
    return s * s;
}

/* legs 1 or 2; host = the single match's / the return leg's home club; level = the club through when level (-1:
   extra time + penalties, by strength) */
static int tie(int kind, int host, int other, int legs, int level) {
    struct dp_tie *t = &DP_OUT.tie[DP_OUT.ntie < 48 ? DP_OUT.ntie++ : 47];
    u32 sh = str2(host, 1), so = str2(other, 0), w;
    t->kind = kind; t->a = host; t->b = other; t->how = H_PLAY;
    if (below(100) < (legs == 1 ? 22u : 12u)) {
        if (level >= 0) { t->win = level; t->how = H_LEVEL; return level; }
        t->how = H_PENS;                /* penalties: close to a coin toss */
        u32 a = str2(host, 0);
        sh = 2 * a + so;
        so = a + 2 * so;
    }
    w = below(sh + so) < sh ? host : other;
    t->win = w;
    return w;
}

static void move(int c, int delta) {
    struct dp_mv *m = &DP_OUT.mv[DP_OUT.nmv++];
    m->glob = row(c)->glob; m->team = row(c)->team; m->delta = delta; m->club = c;
}

static int best_of(const int *c, int n) {
    int b = c[0];
    for (int i = 1; i < n; i++) if (better(c[i], b)) b = c[i];
    return b;
}

static void sort_better(int *c, int n) {
    for (int i = 1; i < n; i++) {
        int x = c[i], j = i;
        while (j > 0 && better(x, c[j - 1])) { c[j] = c[j - 1]; j--; }
        c[j] = x;
    }
}

static void shuffle(int *c, int n) {
    for (int i = n - 1; i > 0; i--) { int j = below(i + 1), x = c[i]; c[i] = c[j]; c[j] = x; }
}

/* seeded round: seeds s[0..n-1] v the others drawn; two legs, return at the seed's, level -> the seed */
static void seeded(int kind, int *s, int *o, int n, int *win) {
    shuffle(o, n);
    for (int i = 0; i < n; i++) win[i] = tie(kind, s[i], o[i], 2, s[i]);
}

static void serie_b(void) {
    int n = DP_IN.n[0];
    const struct dp_row *t = DP_IN.t[0];
    if (n < 17) return;
    if (t[2].pts > t[3].pts + 14) {
        DP_OUT.tie[DP_OUT.ntie++] = (struct dp_tie){ K_DIRECT, 2, 3, 2, H_PLAY, {0} };
        move(2, -1);
    } else {
        int w58 = tie(K_PRE, 4, 7, 1, 4), w67 = tie(K_PRE, 5, 6, 1, 5);
        int s1 = tie(K_SEMI, 2, w67, 2, 2), s2 = tie(K_SEMI, 3, w58, 2, 3);
        int h = better(s1, s2) ? s1 : s2, o = h == s1 ? s2 : s1;
        int w = tie(K_FINAL, h, o, 2, t[PL(h)].pts == t[PL(o)].pts ? -1 : h);
        for (int k = 2; k < 8 && DP_IN.po_win; k++)     /* (played in slot 4: its real winner) */
            if (t[k].team == DP_IN.po_win) w = k;
        move(w, -1);
    }
    if (!OUT_HELD(t)) {
        DP_OUT.tie[DP_OUT.ntie++] = (struct dp_tie){ K_DIRECT, 15, 16, 15, H_PLAY, {0} };
        move(16, 1);
    } else {
        int w = tie(K_OUT, 15, 16, 2, t[15].pts == t[16].pts ? -1 : 15);
        if (DP_IN.out_win == t[15].team) w = 15;
        if (DP_IN.out_win == t[16].team) w = 16;
        move(w == 15 ? 16 : 15, 1);
    }
}

/* the Coppa Italia Serie C winner's play-off place: the winner itself when it finished 11th or lower, the 11th of
   its group when it is promoted or already in (2nd-10th); unknown (its final not played in this career): the best
   11th of the groups */
static int cup_place(int ng) {
    int e[4];
    for (int g = 1; g <= ng && DP_IN.cupw; g++)
        for (int k = 0; k < DP_IN.n[g]; k++)
            if (DP_IN.t[g][k].team == DP_IN.cupw) return g * NT + (k >= 10 ? k : 10);
    for (int g = 0; g < ng; g++) e[g] = (g + 1) * NT + 10;
    return best_of(e, ng);
}

static void serie_c(void) {
    int ng = DP_IN.ng, q[8], nq = 0, thirds[4], seconds[4], cup, nr1[5], nr1o[5], w1[5], s2[4], o2[4], w2[4];
    if (ng < 2 || ng > 4) return;
    for (int g = 1; g <= ng; g++) if (DP_IN.n[g] < 11) return;
    for (int g = 1; g <= ng; g++) {
        int b = g * NT, r2[4];
        r2[0] = b + 3;
        for (int k = 0; k < 3; k++) r2[1 + k] = tie(K_GR1, b + 4 + k, b + 9 - k, 1, b + 4 + k);
        sort_better(r2, 4);
        q[nq++] = tie(K_GR2, r2[0], r2[3], 1, r2[0]);
        q[nq++] = tie(K_GR2, r2[1], r2[2], 1, r2[1]);
        thirds[g - 1] = b + 2;
        seconds[g - 1] = b + 1;
    }
    cup = cup_place(ng);                /* the cup winner's place */
    /* national R1: seeds = the thirds, the cup winner, the best group qualifier; the others drawn */
    {
        int bq = best_of(q, nq), ns = 0, no = 0;
        for (int g = 0; g < ng; g++) nr1[ns++] = thirds[g];
        nr1[ns++] = cup;
        nr1[ns++] = bq;
        for (int i = 0; i < nq; i++) if (q[i] != bq) nr1o[no++] = q[i];
        if (ns != no) return;           /* (3 groups: 5 v 5) */
        seeded(K_NR1, nr1, nr1o, ns, w1);
        /* national R2: seeds = the seconds, the best R1 winner */
        int bw = best_of(w1, ns), k = 0, m = 0;
        for (int g = 0; g < ng; g++) s2[k++] = seconds[g];
        s2[k++] = bw;
        for (int i = 0; i < ns; i++) if (w1[i] != bw) o2[m++] = w1[i];
        if (k != m) return;
        seeded(K_NR2, s2, o2, k, w2);
        /* Final Four: free draw, two legs, extra time + penalties */
        if (k != 4) return;
        shuffle(w2, 4);
        int f1 = tie(K_FFS, w2[1], w2[0], 2, -1), f2 = tie(K_FFS, w2[3], w2[2], 2, -1);
        int w = tie(K_FFF, f2, f1, 2, -1);
        for (int g = 1; g <= ng && DP_IN.cpo_win; g++)          /* (played in slot 4: its real winner) */
            for (int k = 0; k < DP_IN.n[g]; k++)
                if (DP_IN.t[g][k].team == DP_IN.cpo_win) w = g * NT + k;
        move(w, -1);
    }
}

/* test builds (DPLAY_FORCE=k): the career club takes Serie B place k (its team and global number swapped with the
   club there), at the league end and again at the season end */
static int force_place(int m) {        /* (DP_FORCE 1..20: Serie B place; 101..120: place in the club's group) */
    struct dp_row *t = DP_IN.t[DP_FORCE > 100 ? DP_IN.mdiv : 0], x;
    if (!DP_FORCE || m < 0 || (DP_FORCE > 100) != (DP_IN.mdiv > 0)) return m;
    if (DP_FORCE > 100) {
        int f = DP_FORCE - 101;
        x = t[m];
        t[m].team = t[f].team; t[m].glob = t[f].glob;
        t[f].team = x.team; t[f].glob = x.glob;
        return f;
    }
    x = t[m];
    t[m].team = t[DP_FORCE - 1].team; t[m].glob = t[DP_FORCE - 1].glob;
    t[DP_FORCE - 1].team = x.team; t[DP_FORCE - 1].glob = x.glob;
    return DP_FORCE - 1;
}

/* test builds: the league's own final table too (competitionFileBuffer at DP_CFB, at the league end before dp_rows):
   the career club's row and the forced place's swap their figures and places (as gplay's gp_forcecfb), so the game's
   own moves see the forced place. Without it a club really 18th-20th, forced 17th, went down twice (the game's direct
   relegation + the play-out loser's move) and the real 17th stayed up: one relegation lost, swostest world_dplay_out
   trapped in cseg_3283C a season later (Serie B 21, a Serie C group 19) */
u8 *DP_CFB;
void dp_forcecfb(void) {
    u8 *d = DP_CFB;
    int n = *(u16 *)(d + 0x31), m = -1, k = DP_FORCE > 100 ? DP_FORCE - 100 : DP_FORCE;
    if (!DP_FORCE || (DP_FORCE > 100) != (DP_IN.mdiv > 0) || k > n) return;
    for (int j = 0; j < n; j++)
        if (*(u16 *)(d + 0x12D + 2 * (*(u16 *)(d + 0x6D + 2 * j) / 0x12)) == DP_IN.mgr) m = j;
    if (m < 0 || m == k - 1) return;
    u16 *pa = (u16 *)(d + 0x6D + 2 * m), *pb = (u16 *)(d + 0x6D + 2 * (k - 1));
    u16 *ra = (u16 *)(d + *pa + 0x2B7), *rb = (u16 *)(d + *pb + 0x2B7), x;
    for (int i = 0; i < 7; i++) { x = ra[i]; ra[i] = rb[i]; rb[i] = x; }
    x = *pa; *pa = *pb; *pb = x;
}

void dp_season(void) {
    u32 h = 0;
    for (int d = 0; d < NDIV; d++)      /* the seed: the tables (a save gives the same results) */
        for (int k = 0; k < DP_IN.n[d] && k < NT; k++) {
            const struct dp_row *r = &DP_IN.t[d][k];
            h = h * 31 + r->glob;
            h = h * 31 + r->pts + (r->gf << 8);
        }
    rng = h;
    if (DP_FORCE && DP_IN.mgr) {
        int d = DP_FORCE > 100 ? DP_IN.mdiv : 0;
        for (int k = 0; k < DP_IN.n[d]; k++)
            if (DP_IN.t[d][k].team == DP_IN.mgr) { force_place(k); break; }
    }
    for (int i = 0; i < NDIV * NT; i++) lot[i] = below(256);
    DP_OUT.nmv = DP_OUT.ntie = 0;
    serie_b();
    serie_c();
}

/* The career club's Serie B league has ended (DP_IN.t[0] = its final table, mgr, week): its play-off (places 3-8:
   list 5th, 8th, 6th, 7th, 3rd, 4th, the 3rd and 4th waiting in round 1; rounds single + e.t. / two legs / two legs)
   or play-out (17th, 16th: the first leg at the 17th's) into *DP_SVP, kind 0 when the club plays neither. */
static void c_lend(void);

void dp_lend(void) {
    static const u8 po[6] = { 4, 7, 5, 6, 2, 3 };
    const struct dp_row *t = DP_IN.t[0];
    struct dp_save *v = DP_SVP;
    int m = -1, n = DP_IN.n[0];
    v->magic = 0;
    v->kind = 0;
    for (int i = 0; i < 8; i++) v->rb[i] = 0;
    if (DP_IN.mdiv) { c_lend(); return; }
    v->sg[0] = v->sg[1] = 0;
    for (int k = 0; k < n; k++) if (t[k].team == DP_IN.mgr) m = k;
    if (n < 17 || m < 0) return;
    m = force_place(m);
    if (m >= 2 && m <= 7 && t[2].pts <= t[3].pts + 14) {
        v->kind = 1; v->n = 6;
        for (int i = 0; i < 6; i++) v->place[i] = po[i];
        v->rb[0] = 0x10; v->rb[1] = 0x80; v->rb[2] = 0x80;  /* (the final's e.t. / penalties: dp_perm) */
        v->d1 = DP_IN.week + 1; v->d2 = DP_IN.week + 5;
    } else if ((m == 15 || m == 16) && OUT_HELD(t)) {
        v->kind = 2; v->n = 2;
        v->place[0] = 16; v->place[1] = 15;
        v->rb[0] = t[15].pts == t[16].pts ? 0x94 : 0x80;
        v->d1 = DP_IN.week + 2; v->d2 = DP_IN.week + 3;
    } else
        return;
    for (int i = 0; i < v->n; i++) {
        v->team[i] = t[v->place[i]].team; v->pts[i] = t[v->place[i]].pts;
        v->prio[i] = v->place[i]; v->group[i] = 0;
    }
    v->res = 0;
    v->magic = 0x5044;
}

/* The career club's Serie C group has ended; DP_IN.t[1..ng] = the groups' final tables (the others simulated early).
   Its club 2nd-10th (or the best 11th, standing in for the Coppa Italia Serie C winner) -> the 28-club play-off:
   0..17 the group rounds' ties per group (5th v 10th, 6th v 9th, 7th v 8th), 18..20 the 4ths, 21..23 the 3rds, 24
   the cup winner's place, 25..27 the 2nds (waiting for their round: lib97 byes for round 1, dp_perm_c after). */
static void c_lend(void) {
    static const u8 r1[6] = { 4, 9, 5, 8, 6, 7 };
    struct dp_save *v = DP_SVP;
    int g0 = DP_IN.mdiv, ng = DP_IN.ng, m = -1, i = 0, cup;
    if (ng != 3) return;
    for (int g = 1; g <= ng; g++) if (DP_IN.n[g] < 11) return;
    for (int k = 0; k < DP_IN.n[g0]; k++) if (DP_IN.t[g0][k].team == DP_IN.mgr) m = k;
    if (m < 0) return;
    m = force_place(m);
    for (int k = 0; k < NDIV * NT; k++) lot[k] = (u8)(DP_IN.t[k / NT][k % NT].glob * 37 + 11);
    cup = cup_place(ng);
    if (!(m >= 1 && m <= 9) && cup != g0 * NT + m) return;
    for (int g = 1; g <= ng; g++) for (int k = 0; k < 6; k++) { v->place[i] = r1[k]; v->group[i++] = g; }
    for (int p = 3; p >= 1; p--) {
        for (int g = 1; g <= ng; g++) { v->place[i] = p; v->group[i++] = g; }
        if (p == 2) { v->place[i] = cup % NT; v->group[i++] = cup / NT; }
    }
    v->kind = 3; v->n = SN; v->cup = 24;
    for (int k = 0; k < SN; k++) {
        const struct dp_row *r = &DP_IN.t[v->group[k]][v->place[k]];
        v->team[k] = r->team; v->pts[k] = r->pts; v->won[k] = r->won; v->gf[k] = r->gf; v->prio[k] = v->place[k];
    }
    v->rb[0] = 0x01; v->rb[1] = 0x01;   /* group rounds: single, a draw -> the better placed (dp_draw); (bit 0 is
                                           not read: 0x01 = 0x00, but lib97 nc_bye stops at a 0 round byte) */
    v->rb[2] = 0x80; v->rb[3] = 0x80;   /* national rounds: two legs, level -> the seed */
    v->rb[4] = 0x94; v->rb[5] = 0x94;   /* Final Four: two legs, e.t. + penalties (no away goals: header) */
    v->d1 = DP_IN.week + 1; v->d2 = DP_IN.week + 7;
    v->res = 0;
    v->magic = 0x5044;
}

/* 'better placed' between two clubs of the state (indices): place, points, wins, goals scored, lot */
static int sbetter(int a, int b) {
    const struct dp_save *v = &DP_ST;
    if (v->place[a] != v->place[b]) return v->place[a] < v->place[b];
    if (v->pts[a] != v->pts[b]) return v->pts[a] > v->pts[b];
    if (v->won[a] != v->won[b]) return v->won[a] > v->won[b];
    if (v->gf[a] != v->gf[b]) return v->gf[a] > v->gf[b];
    return (u8)(v->team[a] * 37) < (u8)(v->team[b] * 37);
}

static void ssort(u8 *c, int n) {
    for (int i = 1; i < n; i++) {
        u8 x = c[i]; int j = i;
        while (j > 0 && sbetter(x, c[j - 1])) { c[j] = c[j - 1]; j--; }
        c[j] = x;
    }
}

static void sshuffle(u8 *c, int n) {
    for (int i = n - 1; i > 0; i--) { int j = below(i + 1); u8 x = c[i]; c[i] = c[j]; c[j] = x; }
}

/* lib97 nc_adv (through the glue's dp_perm), after a round's draw: DP_PT = the winners in tie order (the waiting
   clubs after them, unused), DP_PR = the next round (1 = the second) -> DP_PL = its list (tie by tie, the first
   leg's / the single match's home club first), returns its clubs (0: not ours); DP_ETP = e.t. + penalties in it. */
u8 DP_PT[64], DP_PL[64];
u32 DP_PR, DP_ETP;
static int seeded_round(const u8 *seed, int ns, u8 *other) {
    sshuffle(other, ns);
    for (int i = 0; i < ns; i++) {
        DP_ST.prio[seed[i]] = 0; DP_ST.prio[other[i]] = 1;
        DP_PL[2 * i] = other[i]; DP_PL[2 * i + 1] = seed[i];      /* (the return at the seed's) */
    }
    return 2 * ns;
}

u32 dp_perm_c(void) {
    struct dp_save *v = &DP_ST;
    const u8 *t = DP_PT;
    u32 h = DP_PR;
    for (int k = 0; k < v->n; k++) h = h * 31 + v->team[k];
    rng = h;
    DP_ETP = 0;
    if (v->kind == 1) {
        if (DP_PR == 1) {               /* semis: 3rd v W(6v7), 4th v W(5v8), the return at the 3rd / 4th's */
            DP_PL[0] = t[1]; DP_PL[1] = t[2]; DP_PL[2] = t[0]; DP_PL[3] = t[3];
            return 4;
        }
        if (DP_PR == 2) {               /* final: the first leg at the worse placed's; level on points: e.t. + pens */
            int a = t[0], b = t[1], w = v->place[a] < v->place[b];
            DP_PL[0] = w ? b : a; DP_PL[1] = w ? a : b;
            DP_ETP = v->pts[a] == v->pts[b];
            return 2;
        }
        return 0;
    }
    if (v->kind != 3) return 0;
    if (DP_PR == 1) {                   /* group round 2: the 3 winners + the 4th, best v worst, the other two */
        for (int g = 0; g < 3; g++) {
            u8 c[4] = { t[3 * g], t[3 * g + 1], t[3 * g + 2], (u8)(18 + g) };
            ssort(c, 4);
            DP_PL[4 * g] = c[0]; DP_PL[4 * g + 1] = c[3]; DP_PL[4 * g + 2] = c[1]; DP_PL[4 * g + 3] = c[2];
        }
        return 12;
    }
    if (DP_PR == 2) {                   /* national round 1: seeds = the 3rds, the cup winner, the best qualifier */
        u8 q[6], s[5], o[5]; int b = 0, k = 0;
        for (int i = 0; i < 6; i++) { q[i] = t[i]; if (sbetter(q[i], q[b])) b = i; }
        s[0] = 21; s[1] = 22; s[2] = 23; s[3] = v->cup; s[4] = q[b];
        for (int i = 0; i < 6; i++) if (i != b) o[k++] = q[i];
        return seeded_round(s, 5, o);
    }
    if (DP_PR == 3) {                   /* national round 2: seeds = the 2nds, the best round-1 winner */
        u8 s[4], o[4]; int b = 0, k = 0;
        for (int i = 1; i < 5; i++) if (sbetter(t[i], t[b])) b = i;
        s[0] = 25; s[1] = 26; s[2] = 27; s[3] = t[b];
        for (int i = 0; i < 5; i++) if (i != b) o[k++] = t[i];
        return seeded_round(s, 4, o);
    }
    if (DP_PR == 4 || DP_PR == 5) {     /* Final Four: free draw, then the final */
        int n = DP_PR == 4 ? 4 : 2;
        for (int i = 0; i < n; i++) DP_PL[i] = t[i];
        if (n == 4) sshuffle(DP_PL, 4);
        return n;
    }
    return 0;
}

/* the season end, a group simulated early (DP_PR = its index in sg): its fresh simulation (DIY at DP_DIYP) gets the
   early one's results, place by place (the rows by team number: the cache pointers stay the fresh ones) */
u8 *DP_DIYP;
void dp_restore(void) {
    const struct dp_srow *s = DP_ST.srow[DP_PR];
    u8 *d = DP_DIYP;
    int n = *(u16 *)(d + 0x31);
    for (int k = 0; k < n && k < SR; k++)
        for (int i = 0; i < n; i++)
            if (*(u16 *)(d + 0x12D + 2 * i) == s[k].team) {
                u16 *r = (u16 *)(d + 0x2B7 + 0x12 * i);
                r[0] = s[k].played; r[1] = s[k].won; r[2] = s[k].drawn; r[3] = s[k].lost;
                r[4] = s[k].gf; r[5] = s[k].ga; r[6] = s[k].pts;
                *(u16 *)(d + 0x6D + 2 * k) = 0x12 * i;
            }
}
