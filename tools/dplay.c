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

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;

enum { NT = 24, NDIV = 5 };
struct dp_row { u16 team, glob, won, gf, ga, pts; };            /* a place of a final table (12 B) */
struct dp_in {
    u8 ng, cupw, pad[2];                /* C groups; cupw: 0 = the best 11th stands in for the cup winner */
    u8 n[NDIV], pad2[3];                /* clubs per table (0 = not captured) */
    struct dp_row t[NDIV][NT];          /* t[0] Serie B, t[1..ng] the groups */
    u16 po_win, out_win;                /* the career club's play-off / play-out played in slot 4: its winner's team
                                           number (0 = none: simulated) */
    u16 mgr, week;                      /* dp_lend: the career club's team number, the league's last week */
};
/* the career club's play-off or play-out in slot 4 (dp_lend; saved with the career, careerworld's 80-record area) */
struct dp_save {
    u16 magic, res;                     /* 'DP' while it runs; res = the winner's team number (dp_rec) */
    u8 kind, n, season, pad;            /* 1 = play-off (6 clubs), 2 = play-out (2); season: the glue's */
    u16 team[6], pts[6];                /* the contest's clubs (its team list order) */
    u8 place[6], pad2[2];               /* their Serie B places (0-based): 'better placed' */
    u8 rb[3], d1, d2, pad3[3];          /* round bytes, first and last week */
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
                          __builtin_offsetof(struct dp_save, place), __builtin_offsetof(struct dp_save, rb) };

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
    if (t[15].pts > t[16].pts + 4) {
        DP_OUT.tie[DP_OUT.ntie++] = (struct dp_tie){ K_DIRECT, 15, 16, 15, H_PLAY, {0} };
        move(16, 1);
    } else {
        int w = tie(K_OUT, 15, 16, 2, t[15].pts == t[16].pts ? -1 : 15);
        if (DP_IN.out_win == t[15].team) w = 15;
        if (DP_IN.out_win == t[16].team) w = 16;
        move(w == 15 ? 16 : 15, 1);
    }
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
    {                                   /* the cup winner's place (temporary: the best 11th) */
        int e[4];
        for (int g = 0; g < ng; g++) e[g] = (g + 1) * NT + 10;
        cup = best_of(e, ng);
    }
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
        move(tie(K_FFF, f2, f1, 2, -1), -1);
    }
}

#ifndef DP_FORCE
#define DP_FORCE 0
#endif
/* test builds (DPLAY_FORCE=k): the career club takes Serie B place k (its team and global number swapped with the
   club there), at the league end and again at the season end */
static int force_place(int m) {
    struct dp_row *t = DP_IN.t[0], x;
    if (!DP_FORCE || m < 0) return m;
    x = t[m];
    t[m].team = t[DP_FORCE - 1].team; t[m].glob = t[DP_FORCE - 1].glob;
    t[DP_FORCE - 1].team = x.team; t[DP_FORCE - 1].glob = x.glob;
    return DP_FORCE - 1;
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
    if (DP_FORCE && DP_IN.mgr)
        for (int k = 0; k < DP_IN.n[0]; k++)
            if (DP_IN.t[0][k].team == DP_IN.mgr) { force_place(k); break; }
    for (int i = 0; i < NDIV * NT; i++) lot[i] = below(256);
    DP_OUT.nmv = DP_OUT.ntie = 0;
    serie_b();
    serie_c();
}

/* The career club's Serie B league has ended (DP_IN.t[0] = its final table, mgr, week): its play-off (places 3-8:
   list 5th, 8th, 6th, 7th, 3rd, 4th, the 3rd and 4th waiting in round 1; rounds single + e.t. / two legs / two legs)
   or play-out (17th, 16th: the first leg at the 17th's) into *DP_SVP, kind 0 when the club plays neither. */
void dp_lend(void) {
    static const u8 po[6] = { 4, 7, 5, 6, 2, 3 };
    const struct dp_row *t = DP_IN.t[0];
    struct dp_save *v = DP_SVP;
    int m = -1, n = DP_IN.n[0];
    v->magic = 0;
    v->kind = 0;
    v->rb[0] = v->rb[1] = v->rb[2] = 0;
    for (int k = 0; k < n; k++) if (t[k].team == DP_IN.mgr) m = k;
    if (n < 17 || m < 0) return;
    m = force_place(m);
    if (m >= 2 && m <= 7 && t[2].pts <= t[3].pts + 14) {
        v->kind = 1; v->n = 6;
        for (int i = 0; i < 6; i++) v->place[i] = po[i];
        v->rb[0] = 0x10; v->rb[1] = 0x80; v->rb[2] = 0x80;  /* (the final's e.t. / penalties: dp_perm) */
        v->d1 = DP_IN.week + 1; v->d2 = DP_IN.week + 5;
    } else if ((m == 15 || m == 16) && t[15].pts <= t[16].pts + 4) {
        v->kind = 2; v->n = 2;
        v->place[0] = 16; v->place[1] = 15;
        v->rb[0] = t[15].pts == t[16].pts ? 0x94 : 0x80;
        v->d1 = DP_IN.week + 2; v->d2 = DP_IN.week + 3;
    } else
        return;
    for (int i = 0; i < v->n; i++) { v->team[i] = t[v->place[i]].team; v->pts[i] = t[v->place[i]].pts; }
    v->res = 0;
    v->magic = 0x5044;
}
