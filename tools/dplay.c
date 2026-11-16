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
/* (test builds, DPLAY_CUPW=k: the Coppa Italia Serie C winner = the club at place k of the career club's group,
   after DPLAY_FORCE's swap) */
#ifndef DP_CUPWF
#define DP_CUPWF 0
#endif
/* (4.2 S3 glue: DP_NOB = 1 when the pack's ko_playoffs hold the Serie B play-off + play-out (gplay's S3 path plays them):
   dp_season no longer simulates Serie B and dp_lend no longer starts the career club's B contest - except a B phase an
   old save already runs on dplay (DP_IN.po_win / out_win from its saved state), which finishes here: dp_rec / dp_perm /
   dp_draw / dp_end's use of the state are not conditional. DP_BHOLD = 1 then: gplay does not run its B play-offs that
   season end (gplay.py gp_end -> GP_SKIPPO). Not compiled in without DP_NOB: the object is the 42-int one.) */
#ifndef DP_NOB
#define DP_NOB 0
#endif
/* (4.2 S3 glue step 2: DP_NOC = 1 when the pack's ko_playoffs hold the Serie C play-off 'c_po' (gplay plays it): dp_season no longer
   simulates Serie C unless dplay played the career club's C play-off (a saved kind-3 state: DP_CHOLD = 1, gplay then skips
   c_po that season end). Not compiled in without DP_NOC.) */
#ifndef DP_NOC
#define DP_NOC 0
#endif
/* (test builds, DPLAY_FORCE >= 16: the play-out is held whatever the points) */
#define OUT_HELD(t) ((t)[15].pts <= (t)[16].pts + 4 || DP_FORCE >= 16)

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
#if DP_NOC
#include "cupview.h"
#endif

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
#if DP_NOC
    u16 cupf;                           /* (4.2 S3 step 2) the other finalist, 0 = unknown */
#endif
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
                          sizeof(struct dp_srow), __builtin_offsetof(struct dp_in, cupw)
#if DP_NOC
                          , __builtin_offsetof(struct dp_in, cupf)
#endif
                          };

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
   11th of the groups. 4.1 (FIGC C.U. 209/A, 27/04/2026, NOIF art. 49 II.1 d-e): a winner relegated directly or in a
   play-out place has no play-off place either - the 11th of its group (it went up and down at once before: Serie B
   21 / its group 19 a season later). The play-out places of a group of n: n-5 v n-2 and n-4 v n-3, each not played
   when its gap or more points apart (the better placed is safe, the other down). 4.2: the gap is the group's own
   play-out's, DP_CG<g> (dplay.py: the pack's playout of that division, the bytes gp_season's 'too far apart' reads;
   8 without one, 0 = always played) - a constant 8 here let the cup winner win the play-off and lose a play-out held
   at 8 points under a gap of 9 (simdrv SIMDRV_CGAP=9, the engine's sr_dplay cup_out the same) */
#ifndef DP_CG1
#define DP_CG1 8
#endif
#ifndef DP_CG2
#define DP_CG2 8
#endif
#ifndef DP_CG3
#define DP_CG3 8
#endif
#ifndef DP_CG4
#define DP_CG4 8
#endif
#if DP_NOC
/* (4.2 S3 step 2, MC 15/11: the cup place is ONE implementation, gplay.c cup_rule - FIGC C.U. 209/A; dplay holds no rule code: it
   calls it through DP_RULEP, patched by gplay.py, on a view of its own tables (DP_IN, no copy) and applies the scroll to the
   places it lists: pm) */
volatile const u32 DP_RULEP = 0;
static u8 sc_g, sc_from;                /* the scroll: group (1 ..), first place (1-based; 0 none) */
static int pm(int g, int p) { return p + (g == sc_g && sc_from && p + 1 >= sc_from); }   /* a listed place -> the real place */
static int cup_place(int ng) {
    struct cup_view v;
    static const u8 cg[4] = { DP_CG1, DP_CG2, DP_CG3, DP_CG4 };
    v.ng = ng; v.real = 1; v.w = DP_IN.cupw; v.f = DP_IN.cupf;
    for (int g = 0; g < ng; g++) { v.t[g] = (const struct cv_row *)DP_IN.t[g + 1]; v.n[g] = DP_IN.n[g + 1]; v.gap[g] = cg[g]; v.lot[g] = lot[(g + 1) * NT + 10]; }
    int r = ((int (*)(struct cup_view *))DP_RULEP)(&v);
    sc_g = v.sfrom ? v.sg + 1 : 0; sc_from = v.sfrom;
    return (1 + (r >> 5)) * NT + (r & 31);
}
#else
static const u8 DP_CGAP[NDIV] = { 8, DP_CG1, DP_CG2, DP_CG3, DP_CG4 };
static int cup_out(int g, int k) {     /* place k of group g relegated or in a play-out */
    const struct dp_row *t = DP_IN.t[g];
    int n = DP_IN.n[g], gap = DP_CGAP[g];
    if (n < 6 || k < n - 5) return 0;
    if (k == n - 5) return !gap || t[n - 5].pts - t[n - 2].pts < gap;
    if (k == n - 4) return !gap || t[n - 4].pts - t[n - 3].pts < gap;
    return 1;
}
static int cup_place(int ng) {
    int e[4];
    for (int g = 1; g <= ng && DP_IN.cupw; g++)
        for (int k = 0; k < DP_IN.n[g]; k++)
            if (DP_IN.t[g][k].team == DP_IN.cupw) return g * NT + (k >= 10 && !cup_out(g, k) ? k : 10);
    for (int g = 0; g < ng; g++) e[g] = (g + 1) * NT + 10;
    return best_of(e, ng);
}

#endif

/* Serie C play-off winner already promoted by the table (4.2 S3, MC 16/11): the place goes on. Exactly 4 clubs leave a
   Serie C group set upwards (3 group winners + the play-off's). The list was built at the career club's group end
   (c_lend), when the other groups' tables were simulated early; the final tables can differ, so a club of the list can
   end 1st of its group (promoted by the title) or down in the relegation zone. Eligible = not 1st, not in the last 5 of
   its group. Order: the final's loser, then the two semi-final losers (better placed first, `better`), then (an old save past round 5, no record) the best eligible of the others in the state's list; none: 3 clubs go up, DP_SUBF = 1.
   Eligible = not 1st of its group and not in the last 5 of it on the final tables (a little stricter than 'relegated or in a lost
   play-out place', harmless). */
#ifdef DP_STATS
u32 DP_SUBN[4];
#define DP_STAT(i) DP_SUBN[i]++
#else
#define DP_STAT(i)
#endif
                         /* (test / log) substitutions: final's loser, semi-final loser, state list, none */
u8 DP_SUBF;                             /* the last season end: 1 = no substitute (3 up) */
#define NOINL __attribute__((noinline))
static int c_elig(int g, int k) { return k > 0 && k < DP_IN.n[g] - 5; }
static int club_of(u16 team) {         /* the ELIGIBLE club of a team number (c_elig), -1 otherwise */
    for (int g = 1; g <= DP_IN.ng; g++)
        for (int k = 1; k < DP_IN.n[g] - 5; k++) if (DP_IN.t[g][k].team == team) return g * NT + k;
    return -1;
}
/* the contest record (rb[6..7] + cup's low bits, cup bit 7 = valid): four 5-bit state indices */
#define FREC_OK(v) ((v)->cup & 0x80)
#define FREC(v) ((u32)(v)->rb[6] | (u32)(v)->rb[7] << 8 | (u32)((v)->cup & 63) << 16)
static void frec_set(struct dp_save *v, const u8 *e) {   /* the Final Four's four clubs, tie by tie (a bit 20 / 21 later: the second of a tie won) */
    u32 x = e[0] | e[1] << 5 | e[2] << 10 | e[3] << 15;
    v->rb[6] = x & 255; v->rb[7] = x >> 8 & 255; v->cup = 0x80 | (x >> 16 & 15);
}
/* the substitute for a play-off winner (team DP_IN.cpo_win, club w) that the final tables do not allow: over the state's list,
   class 0 = the final's loser, 1 = the semi-final losers, 2 = any other club of the list (no record: an old save), the
   better placed first inside a class; -1 = none */
static NOINL int c_sub(void) {
    const struct dp_save *v = &DP_ST;
    u32 x = FREC_OK(v) ? FREC(v) : ~0u;
    u8 cls[32];
    int best = -1, bk = 9;
    for (int i = 0; i < 32; i++) cls[i] = 2;
    for (int p = 0; p < 2; p++) {       /* the record: pair p = the clubs x >> 10p and x >> 10p + 5, bit 20 + p = the second won */
        int a = (x >> 10 * p) & 31, b = (x >> (10 * p + 5)) & 31, d = (x >> (20 + p)) & 1;
        cls[d ? a : b] = 1;             /* the semi-final loser */
        cls[d ? b : a] = 3;             /* the final's entrant: 0 if the other final entrant won (below) */
    }
    for (int i = 0; i < SN; i++) if (cls[i] == 3) cls[i] = v->team[i] == DP_IN.cpo_win ? 4 : 0;
    for (int i = 0; i < v->n; i++) {
        int c = club_of(v->team[i]), k = cls[i];
        if (c < 0 || k > bk || (k == bk && !better(c, best))) continue;
        best = c; bk = k;
    }
    DP_STAT(best < 0 ? 3 : bk);
    return best;
}


#ifndef DP_FREC
#define DP_FREC 0
#endif
#if DP_FREC
/* test builds (DPLAY_FREC = 1..3, MC 16/11): just before serie_c reads the Final Four record, make the real winner R of the career club's
   Serie C play-off ineligible (1st of its group in DP_IN: the game's own tables are not touched, the substitute is dplay's):
   1: R -> 1st of its group; the final's loser goes up. 2: also the final's loser L is ineligible (taken out of the tables):
   the best semi-final loser goes up. 3: the career club is made the final's loser (the record is rewritten: the final is R v the
   career club); R -> 1st of its group: the career club goes up. Without the switch none of this is compiled in. */
static void swap_rows(int g, int a, int b) { struct dp_row x = DP_IN.t[g][a]; DP_IN.t[g][a] = DP_IN.t[g][b]; DP_IN.t[g][b] = x; }
static int find_team(u16 team, int *g, int *k) {
    for (*g = 1; *g <= DP_IN.ng; (*g)++) for (*k = 0; *k < DP_IN.n[*g]; (*k)++) if (DP_IN.t[*g][*k].team == team) return 1;
    return 0;
}
static void frec_force(void) {
    struct dp_save *v = &DP_ST;
    int gr, kr, ir = -1;
    if (!DP_IN.cpo_win || v->kind != 3 || !FREC_OK(v) || !find_team(DP_IN.cpo_win, &gr, &kr)) return;
    for (int i = 0; i < v->n; i++) if (v->team[i] == DP_IN.cpo_win) ir = i;
#if DP_FREC == 3
    {
        u8 e[4], o[2], j = 0;
        int ic = -1;
        for (int i = 0; i < v->n; i++) if (v->team[i] == DP_IN.mgr) ic = i;
        if (ic < 0 || ir == ic) return;
        for (int i = 0; i < v->n && j < 2; i++) if (i != ir && i != ic) o[j++] = i;
        e[0] = ir; e[1] = o[0]; e[2] = ic; e[3] = o[1];
        frec_set(v, e);
    }
#endif
#if DP_FREC == 2
    {
        u32 x = FREC(v);
        int w0 = (x >> (x >> 20 & 1 ? 5 : 0)) & 31, w1 = (x >> (x >> 21 & 1 ? 15 : 10)) & 31, l = w0 == ir ? w1 : w0, gl, kl;
        if (find_team(v->team[l], &gl, &kl)) DP_IN.t[gl][kl].team = 0xFFFE;       /* (not in the tables: not eligible) */
    }
#endif
    (void)ir;
    swap_rows(gr, kr, 0);
}
#endif

static void serie_c(void) {
    int ng = DP_IN.ng, q[8], nq = 0, thirds[4], seconds[4], cup, nr1[5], nr1o[5], w1[5], s2[4], o2[4], w2[4];
    if (ng < 2 || ng > 4) return;
    for (int g = 1; g <= ng; g++) if (DP_IN.n[g] < 11) return;
#if DP_NOC
    cup = cup_place(ng);                /* (first: its scroll moves the places below) */
#endif
    for (int g = 1; g <= ng; g++) {
        int b = g * NT, r2[4];
#if DP_NOC
        r2[0] = b + pm(g, 3);
        for (int k = 0; k < 3; k++) r2[1 + k] = tie(K_GR1, b + pm(g, 4 + k), b + pm(g, 9 - k), 1, b + pm(g, 4 + k));
#else
        r2[0] = b + 3;
        for (int k = 0; k < 3; k++) r2[1 + k] = tie(K_GR1, b + 4 + k, b + 9 - k, 1, b + 4 + k);
#endif
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
#if DP_FREC
        frec_force();
#endif
        for (int g = 1; g <= ng && DP_IN.cpo_win; g++)          /* (played in slot 4: its real winner) */
            for (int k = 0; k < DP_IN.n[g]; k++)
                if (DP_IN.t[g][k].team == DP_IN.cpo_win) {
                    w = g * NT + k;
                    if (!c_elig(g, k)) w = c_sub();
                }
        DP_SUBF = w < 0;
        if (w >= 0) move(w, -1);
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

#if DP_NOC
#ifndef DP_CUPFF
#define DP_CUPFF 0                      /* (test builds, 4.2 S3 step 2: DPLAY_CUPF = group * 100 + place (1-based): the other finalist) */
#endif
#endif
static void cup_force(void) {
    if (DP_CUPWF && DP_IN.mdiv && DP_CUPWF <= DP_IN.n[DP_IN.mdiv]) DP_IN.cupw = DP_IN.t[DP_IN.mdiv][DP_CUPWF - 1].team;
#if DP_NOC
    if (DP_CUPFF && DP_CUPFF / 100 >= 1 && DP_CUPFF / 100 <= DP_IN.ng && DP_CUPFF % 100 >= 1 && DP_CUPFF % 100 <= DP_IN.n[DP_CUPFF / 100])
        DP_IN.cupf = DP_IN.t[DP_CUPFF / 100][DP_CUPFF % 100 - 1].team;
#endif
}

/* test builds: the league's own final table too (competitionFileBuffer at DP_CFB, at the league end before dp_rows):
   the career club's row and the forced place's swap their figures and places (as gplay's gp_forcecfb), so the game's
   own moves see the forced place. Without it a club really 18th-20th, forced 17th, went down twice (the game's direct
   relegation + the play-out loser's move) and the real 17th stayed up: one relegation lost, swostest world_dplay_out
   trapped in cseg_3283C a season later (Serie B 21, a Serie C group 19) */
u8 *DP_CFB;
#if DP_NOB
u8 DP_BHOLD;                            /* (set by dp_season, read by gplay.py's gp_end: 0 / 1) */
#endif
#if DP_NOC
u8 DP_CHOLD;                            /* (set by dp_season, read by gplay.py's gp_end: 0 / 1) */
#endif
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
    cup_force();
    for (int i = 0; i < NDIV * NT; i++) lot[i] = below(256);
    DP_OUT.nmv = DP_OUT.ntie = 0;
#if DP_NOB
    DP_BHOLD = DP_IN.po_win || DP_IN.out_win;           /* (a B phase of an old save finished on dplay) */
    if (DP_BHOLD) serie_b();
#else
    serie_b();
#endif
#if DP_NOC
    DP_CHOLD = DP_IN.cpo_win != 0;                      /* (a C play-off played on dplay: the career club's; else gplay's c_po) */
    if (DP_CHOLD) serie_c();
#else
    serie_c();
#endif
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
#if DP_NOB
    return;                                             /* (Serie B: gplay's S3 plays the career club's contest) */
#endif
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
    cup_force();
    for (int k = 0; k < NDIV * NT; k++) lot[k] = (u8)(DP_IN.t[k / NT][k % NT].glob * 37 + 11);
    cup = cup_place(ng);
#if DP_NOC
    {   int in = 0;                     /* (the career club plays if it is in a group's lists after the scroll, or takes the cup seat) */
        for (int p = 1; p <= 9; p++) if (pm(g0, p) == m) in = 1;
        if (!in && cup != g0 * NT + m) return;
    }
    for (int g = 1; g <= ng; g++) for (int k = 0; k < 6; k++) { v->place[i] = pm(g, r1[k]); v->group[i++] = g; }
    for (int p = 3; p >= 1; p--) {
        for (int g = 1; g <= ng; g++) { v->place[i] = pm(g, p); v->group[i++] = g; }
#else
    if (!(m >= 1 && m <= 9) && cup != g0 * NT + m) return;
    for (int g = 1; g <= ng; g++) for (int k = 0; k < 6; k++) { v->place[i] = r1[k]; v->group[i++] = g; }
    for (int p = 3; p >= 1; p--) {
        for (int g = 1; g <= ng; g++) { v->place[i] = p; v->group[i++] = g; }
#endif
        if (p == 2) { v->place[i] = cup % NT; v->group[i++] = cup / NT; }
    }
    v->kind = 3; v->n = SN; v->cup = 0;                 /* (cup's place is always 24; the byte now holds the final-four record) */
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
        s[0] = 21; s[1] = 22; s[2] = 23; s[3] = 24; s[4] = q[b];
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
        if (DP_PR == 5 && FREC_OK(v)) {  /* the semi-finals' winners in tie order: which of each pair won */
            u32 x = FREC(v);
            v->cup |= (t[0] == (x >> 5 & 31) ? 16 : 0) | (t[1] == (x >> 15 & 31) ? 32 : 0);
        }
        for (int i = 0; i < n; i++) DP_PL[i] = t[i];
        if (n == 4) {
            sshuffle(DP_PL, 4);
            frec_set(v, DP_PL);                                         /* (the pairs: ties 0 and 1) */
        }
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
