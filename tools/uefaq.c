/* UEFA qualifying rounds of a league-phase career world (access list 2024-27, as for 2026/27).

   Compiled twice: for the game (tools/cobj.py: clang -target i686 -march=i486, linked into an obj1 cave, called from
   the season end's asm) and natively for the tests against the Python reference model (internal/world2526/
   uefa_access/season.py, which this file follows step by step: the same order of the random draws).

   The access list: places per association rank (round, code): code 0 = champion, 1 = cup winner, k = k-th place.
   uq_season(): the season's list (absent associations, the 2 European Performance Spots, the title holders' rules,
   the round totals rebalanced top-down from the 36-club league phases), the clubs of every place, the qualifying
   rounds in their real order (draws seeded by club coefficient, no two clubs of one association; a two-legged tie
   won with probability s1^2 / (s1^2 + s2^2)), the drop-downs, and the three league phases. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

enum { CL_LS, CL_PO, CL_POnc, CL_Q3, CL_Q3nc, CL_Q2, CL_Q2nc, CL_Q1, EL_LS, EL_PO, EL_Q3, EL_Q3ch, EL_Q2, EL_Q1,
       CO_LS, CO_PO, CO_POch, CO_Q3, CO_Q3ch, CO_Q2, CO_Q2ch, CO_Q1, NR, OUT = 255, SPLIT = 254 };
#define COMP(r) ((r) < EL_LS ? 0 : (r) < CO_LS ? 1 : 2)
/* season.py ROUND_ORDER index of each round (LS PO POnc POch Q3 Q3nc Q3ch Q2 Q2nc Q2ch Q1) */
static const u8 RORD[NR] = { 0, 1, 2, 4, 5, 7, 8, 10, 0, 1, 4, 6, 7, 10, 0, 1, 3, 4, 6, 7, 9, 10 };
/* winners -> , losers -> (season.py FLOW) */
static const u8 WIN[NR] = { OUT, CL_LS, CL_LS, CL_PO, CL_POnc, CL_Q3, CL_Q3nc, CL_Q2, OUT, EL_LS, EL_PO, EL_PO,
                            EL_Q3, EL_Q2, OUT, CO_LS, CO_LS, CO_PO, CO_POch, CO_Q3, CO_Q3ch, CO_Q2 };
static const u8 LOSE[NR] = { OUT, EL_LS, EL_LS, EL_PO, EL_LS, EL_Q3ch, EL_Q3, SPLIT, OUT, CO_LS, CO_PO, CO_POch,
                             CO_Q3, CO_Q2, OUT, OUT, OUT, OUT, OUT, OUT, OUT, OUT };
static const u8 SCHED[] = { CL_Q1, EL_Q1, CO_Q1, OUT, CL_Q2, CL_Q2nc, EL_Q2, CO_Q2, CO_Q2ch, OUT,
                            CL_Q3, CL_Q3nc, EL_Q3, EL_Q3ch, CO_Q3, CO_Q3ch, OUT, CL_PO, CL_POnc, EL_PO, CO_PO, CO_POch,
                            OUT, OUT };

/* default list 2026/27 by rank: rank, n, n x (round, code); Kassies' matrix, the EPS places removed */
static const u8 AL[] = {
    1, 7, 0,0, 0,2, 0,3, 0,4, 15,6, 8,1, 8,5,
    2, 7, 0,0, 0,2, 0,3, 0,4, 15,6, 8,1, 8,5,
    3, 7, 0,0, 0,2, 0,3, 0,4, 15,6, 8,1, 8,5,
    4, 7, 0,0, 0,2, 0,3, 0,4, 15,6, 8,1, 8,5,
    5, 7, 0,0, 0,2, 0,3, 4,4, 15,6, 8,1, 8,5,
    6, 6, 0,0, 0,2, 4,3, 19,5, 8,1, 12,4,
    7, 5, 0,0, 4,2, 19,4, 8,1, 12,3,
    8, 5, 0,0, 4,2, 19,4, 9,1, 12,3,
    9, 5, 0,0, 4,2, 19,4, 9,1, 12,3,
    10, 5, 0,0, 6,2, 19,4, 9,1, 12,3,
    11, 5, 1,0, 6,2, 19,4, 9,1, 12,3,
    12, 5, 1,0, 6,2, 19,4, 9,1, 12,3,
    13, 5, 1,0, 6,2, 19,3, 19,4, 10,1,
    14, 5, 1,0, 6,2, 19,3, 19,4, 10,1,
    15, 5, 5,0, 6,2, 19,3, 19,4, 10,1,
    16, 4, 5,0, 19,2, 19,3, 13,1,
    17, 4, 5,0, 19,2, 19,3, 13,1,
    18, 4, 5,0, 19,2, 19,3, 13,1,
    19, 4, 5,0, 19,2, 19,3, 13,1,
    20, 4, 5,0, 19,2, 19,3, 13,1,
    21, 4, 5,0, 19,2, 19,3, 13,1,
    22, 4, 5,0, 19,2, 19,3, 13,1,
    23, 4, 7,0, 19,2, 19,3, 13,1,
    24, 4, 7,0, 19,2, 19,3, 13,1,
    25, 4, 7,0, 19,2, 19,3, 13,1,
    26, 4, 7,0, 19,2, 19,3, 13,1,
    27, 4, 7,0, 19,2, 19,3, 13,1,
    28, 4, 7,0, 19,2, 19,3, 13,1,
    29, 4, 7,0, 19,2, 19,3, 13,1,
    30, 4, 7,0, 21,3, 19,2, 13,1,
    31, 4, 7,0, 21,3, 19,2, 13,1,
    32, 4, 7,0, 21,3, 19,2, 13,1,
    33, 4, 7,0, 21,3, 19,2, 13,1,
    34, 4, 7,0, 21,2, 21,3, 19,1,
    35, 4, 7,0, 21,2, 21,3, 19,1,
    36, 4, 7,0, 21,2, 21,3, 19,1,
    37, 4, 7,0, 21,2, 21,3, 19,1,
    38, 4, 7,0, 21,2, 21,3, 19,1,
    39, 4, 7,0, 21,1, 21,2, 21,3,
    40, 4, 7,0, 21,1, 21,2, 21,3,
    41, 4, 7,0, 21,1, 21,2, 21,3,
    42, 4, 7,0, 21,1, 21,2, 21,3,
    43, 4, 7,0, 21,1, 21,2, 21,3,
    44, 1, 21,1,
    45, 4, 7,0, 21,1, 21,2, 21,3,
    46, 4, 7,0, 21,1, 21,2, 21,3,
    47, 4, 7,0, 21,1, 21,2, 21,3,
    48, 4, 7,0, 21,1, 21,2, 21,3,
    49, 4, 7,0, 21,1, 21,2, 21,3,
    50, 4, 7,0, 21,1, 21,2, 21,3,
    51, 3, 7,0, 21,1, 21,2,
    52, 3, 7,0, 21,1, 21,2,
    53, 3, 7,0, 21,1, 21,2,
    54, 3, 7,0, 21,1, 21,2,
    55, 3, 7,0, 21,1, 21,2,
    0 };

#define NA 56                           /* ranks 1..55 */
#define NL 10                           /* clubs per association: the top 9 of the league + the cup winner */
#define NC 600
#define NE 400

/* input (filled by the caller) */
struct uq_in {
    u32 seed;
    u8 present[NA];                     /* rank -> 1 if the world has that association */
    u8 eps[2];                          /* ranks of the 2 European Performance Spots (0 = none) */
    u16 hold[3];                        /* title holders CL, EL, UECL: club indices + 1 (0 = none) */
    u16 nclub;
    u16 league[NA][NL - 1];             /* club indices + 1, league order (0 = none) */
    u16 cup[NA];                        /* the cup winner: club index + 1 (0 = none) */
    struct { u16 id; u8 rank; u8 pad; u32 coef; u32 str; } club[NC];
    u16 manager;                        /* the manager's club: index + 1 (0 = none / not seen) */
    u8 force;                           /* test builds: the manager's club enters this round (0 = its place) */
};
/* output */
struct uq_out {
    u8 n[3];                            /* clubs in the three league phases (36 each) */
    u16 ls[3][40];                      /* club indices + 1 */
    u8 status[3];                       /* holders: 0 none, 1 'league', 2 'own' */
    u8 nent;                            /* places of the season's list (after the rebalancing) */
    u8 round_of[NC];                    /* the club's first round (NR = none) */
    u8 last[NC];                        /* the last round played (NR = none) */
    u8 mt_n;                            /* the manager's ties (in the simulation): round, opponent, won */
    u8 mt_round[6];
    u16 mt_opp[6];
    u8 mt_win[6];
    u16 standin;                        /* the club in the manager's league-phase place until its ties are played */
};

struct uq_in UQ_IN;
struct uq_out UQ_OUT;
#define OFF(t, f) ((u32) __builtin_offsetof(struct t, f))
/* for the asm (uefaq.py): offsets in UQ_IN / UQ_OUT, the club record's size */
const u32 UQ_LAYOUT[] = { OFF(uq_in, present), OFF(uq_in, eps), OFF(uq_in, hold), OFF(uq_in, nclub),
                          OFF(uq_in, league), OFF(uq_in, cup), OFF(uq_in, club), sizeof(UQ_IN.club[0]),
                          OFF(uq_out, n), OFF(uq_out, ls), OFF(uq_out, status), sizeof(struct uq_in), NC,
                          OFF(uq_in, manager), OFF(uq_in, force), OFF(uq_out, mt_n), OFF(uq_out, mt_round),
                          OFF(uq_out, mt_opp), OFF(uq_out, mt_win), OFF(uq_out, standin) };

static struct { u8 rank, round, code, pad; } E[NE];
static int ne;
static u32 CRC[NA][NL + 1];             /* club coefficient of (rank, code) */
static u32 rng;

static u32 below(u32 n) {
    rng = rng * 1103515245u + 12345u;
    return ((rng >> 16) * n) >> 16;
}

static int d(int r) {
    int n = 0;
    for (int i = 0; i < ne; i++)
        n += E[i].round == r;
    return n;
}

/* key comparisons of model.py: best = max (coef, -rank, -code); by rank: min (code != CW, rank, code) */
static int better(int a, int b) {                /* a > b in (coef, -rank, -code) */
    u32 ca = CRC[E[a].rank][E[a].code], cb = CRC[E[b].rank][E[b].code];
    if (ca != cb) return ca > cb;
    if (E[a].rank != E[b].rank) return E[a].rank < E[b].rank;
    return E[a].code < E[b].code;
}
static int rkey_less(int a, int b) {             /* a < b in (code != CW, rank, code) */
    int wa = E[a].code != 1, wb = E[b].code != 1;
    if (wa != wb) return wa < wb;
    if (E[a].rank != E[b].rank) return E[a].rank < E[b].rank;
    return E[a].code < E[b].code;
}

static void up(int lo, int hi, int k, int bycoef) {
    for (; k < 0; k++) {                         /* the worst clubs of hi down to lo */
        int x = -1;
        for (int i = 0; i < ne; i++)
            if (E[i].round == hi && (x < 0 || (bycoef ? better(x, i) : rkey_less(x, i))))
                x = i;
        if (x < 0) return;
        E[x].round = lo;
    }
    for (; k > 0; k--) {                         /* the best ones of lo up to hi */
        int x = -1;
        for (int i = 0; i < ne; i++)
            if (E[i].round == lo && (x < 0 || (bycoef ? better(i, x) : rkey_less(i, x))))
                x = i;
        if (x < 0) return;
        E[x].round = hi;
    }
}

static int best_of(int (*pred)(int)) {
    int x = -1;
    for (int i = 0; i < ne; i++)
        if (pred(i) && (x < 0 || better(i, x)))
            x = i;
    return x;
}
static int p_cp_champ(int i) { return E[i].code == 0 && (E[i].round == CL_PO || E[i].round == CL_Q3 ||
                                                          E[i].round == CL_Q2 || E[i].round == CL_Q1); }
static int p_clq(int i) { return E[i].round > CL_LS && E[i].round < EL_LS; }
static int p_elq(int i) { return E[i].round > EL_LS && E[i].round < CO_LS; }
static u8 top[NA];
static int p_clq_top(int i) { return p_clq(i) && (E[i].code == 0 || E[i].code == top[E[i].rank]); }

static int x_split;                              /* CL Q1 losers into UECL Q2ch (the others into Q3ch) */

/* model.rebalance: the season's list in E. st[3] = holders' status (1 'league', 2 'own') */
static void rebalance(const u8 *eps, const u8 *st, int totals) {
    ne = 0;
    for (const u8 *a = AL; *a; a += 2 + 2 * a[1]) {
        if (!UQ_IN.present[a[0]]) continue;
        for (int j = 0; j < a[1]; j++) {
            E[ne].rank = a[0];
            E[ne].round = a[2 + 2 * j];
            E[ne].code = a[3 + 2 * j];
            ne++;
        }
    }
    for (int e = 0; e < 2; e++) {                /* EPS: one more league-phase place, the lower places shift */
        int rk = eps[e], n = 1;
        if (!rk || !UQ_IN.present[rk]) continue;
        for (int i = 0; i < ne; i++)
            if (E[i].rank == rk && E[i].round == CL_LS && E[i].code >= 2 && E[i].code > n)
                n = E[i].code;
        for (int i = 0; i < ne; i++)
            if (E[i].rank == rk && E[i].code >= 2 && E[i].round != CL_LS)
                E[i].code++;
        E[ne].rank = rk;
        E[ne].round = CL_LS;
        E[ne].code = n + 1;
        ne++;
    }
    if (!totals) return;
    int x;
    if (st[0] == 1 && (x = best_of(p_cp_champ)) >= 0)
        E[x].round = CL_LS;
    if (st[1] == 1) {
        for (int r = 0; r < NA; r++) top[r] = 0;
        for (int i = 0; i < ne; i++)
            if (p_clq(i) && E[i].code != 0) {   /* (model.py order: the N places, then a cup winner) */
                int k = E[i].code == 1 ? 99 : E[i].code, t = top[E[i].rank] == 1 ? 99 : top[E[i].rank];
                if (!t || k < t) top[E[i].rank] = E[i].code;
            }
        if ((x = best_of(p_clq_top)) >= 0)
            E[x].round = CL_LS;
    }
    if (st[2] == 1 && (x = best_of(p_elq)) >= 0)
        E[x].round = EL_LS;
    up(CL_Q2nc, CL_Q3nc, 16 - 2 * d(CL_Q3nc) - d(CL_Q2nc), 1);
    int t_q3 = 12, t_q2 = 24;
    while (d(CL_PO) < 10 - t_q3 / 2) {
        int lo = d(CL_Q3) ? CL_Q3 : d(CL_Q2) ? CL_Q2 : d(CL_Q1) ? CL_Q1 : -1, y = -1;
        if (lo < 0) break;
        for (int i = 0; i < ne; i++)
            if (E[i].round == lo && (y < 0 || better(i, y)))
                y = i;
        E[y].round = CL_PO;
    }
    up(CL_Q1, CL_Q2, 2 * t_q2 - 2 * d(CL_Q2) - d(CL_Q1), 1);
    int cl_q1_losers = d(CL_Q1) / 2, cl_q2nc_losers = d(CL_Q2nc) / 2;
    int cl_lp_ls_losers = 6, cl_cp_q3_losers = t_q3 / 2, cl_cp_po_losers = 5, cl_cp_q2_losers = t_q2 / 2;
    int hold_el = st[2] == 2;
    int w_po = 36 - d(EL_LS) - hold_el - cl_lp_ls_losers - cl_cp_po_losers, t_po = 2 * w_po;
    int w_q3ch = cl_cp_q2_losers / 2;
    int w_q3 = t_po - d(EL_PO) - cl_cp_q3_losers - w_q3ch, t_q3e = 2 * w_q3;
    int w_q2 = t_q3e - d(EL_Q3) - cl_q2nc_losers, t_q2e = 2 * w_q2;
    up(EL_Q1, EL_Q2, 2 * t_q2e - 2 * d(EL_Q2) - d(EL_Q1), 0);
    int el_q1_losers = d(EL_Q1) / 2;
    int el_q2_losers = w_q2, el_q3_losers = w_q3, el_po_losers = w_po, el_q3ch_losers = w_q3ch;
    int w_poch = 5, w_q3ch_c = 2 * w_poch - el_q3ch_losers, t_q3ch = 2 * w_q3ch_c;
    x_split = 2 * (cl_q1_losers - t_q3ch);
    if (x_split < 0) x_split = 0;               /* (a small world) */
    if (x_split > cl_q1_losers) x_split = cl_q1_losers;
    int w_po_c = 36 - d(CO_LS) - w_poch - el_po_losers, t_po_c = 2 * w_po_c;
    int w_q3_c = t_po_c - d(CO_PO) - el_q3_losers, t_q3_c = 2 * w_q3_c;
    int w_q2_c = t_q3_c - d(CO_Q3) - el_q2_losers, t_q2_c = 2 * w_q2_c;
    up(CO_Q1, CO_Q2, 2 * t_q2_c - 2 * d(CO_Q2) - 2 * el_q1_losers - d(CO_Q1), 0);
}

/* season.py slot_key: (comp, CH 0 / CL place 1 / CW 2 / other 3, round order, code) */
static u32 skey(int i) {
    int c = COMP(E[i].round), k = E[i].code;
    int cls = k == 0 ? 0 : k == 1 ? 2 : c == 0 ? 1 : 3;
    return c << 24 | cls << 16 | RORD[E[i].round] << 8 | (k >= 2 ? k : 0);
}

static u16 CLUB[NE];                    /* the club (index + 1) of each place, 0 = none */
static u8 taken[NC + 1];

/* season.py assign() for every association: CLUB[] from E; skip[] = holders taking their own place */
static void assign(const u16 *skip) {
    static short ord[NE];
    for (int i = 0; i < ne; i++) CLUB[i] = 0;
    for (int rk = 1; rk < NA; rk++) {
        int n = 0;
        for (int i = 0; i < ne; i++)
            if (E[i].rank == rk) {
                int j = n++;                    /* insertion by slot key */
                while (j > 0 && skey(ord[j - 1]) > skey(i)) { ord[j] = ord[j - 1]; j--; }
                ord[j] = i;
            }
        if (!n) continue;
        for (int c = 0; c <= UQ_IN.nclub; c++) taken[c] = 0;
        for (int h = 0; h < 3; h++) if (skip[h]) taken[skip[h]] = 1;
        const u16 *lg = UQ_IN.league[rk];
        for (int j = 0; j < n; j++) {
            int i = ord[j], club = 0;
            if (E[i].code == 0 && lg[0] && !taken[lg[0]])
                club = lg[0];
            else if (E[i].code == 1 && UQ_IN.cup[rk] && !taken[UQ_IN.cup[rk]])
                club = UQ_IN.cup[rk];
            else
                for (int l = 0; l < NL - 1; l++)
                    if (lg[l] && !taken[lg[l]]) { club = lg[l]; break; }
            if (club) { CLUB[i] = club; taken[club] = 1; }
        }
    }
}

/* the rounds' entrants */
static u16 RL[NR][128];
static u8 RN[NR];
static void add(int r, int club) { if (RN[r] < 128) RL[r][RN[r]++] = club; }

static int seed_less(int a, int b) {            /* (-coef, id) */
    u32 ca = UQ_IN.club[a - 1].coef, cb = UQ_IN.club[b - 1].coef;
    if (ca != cb) return ca > cb;
    return UQ_IN.club[a - 1].id < UQ_IN.club[b - 1].id;
}

static u32 sq(int c) { u32 s = UQ_IN.club[c - 1].str / 16; if (s < 1) s = 1; return s * s; }

static void play(int r) {
    static u16 t[128], ta[64], tb[64];
    int n = RN[r];
    RN[r] = 0;
    if (!n) return;
    for (int i = 0; i < n; i++) {               /* sorted, seeded first */
        int j = i, c = RL[r][i];
        while (j > 0 && seed_less(c, t[j - 1])) { t[j] = t[j - 1]; j--; }
        t[j] = c;
    }
    int k = 0;
    if (n & 1) {                                /* a bye for the best club */
        UQ_OUT.last[t[0] - 1] = r;
        if (WIN[r] != OUT) add(WIN[r], t[0]);
        k = 1;
        n--;
    }
    int h = n / 2;
    u16 *s = t + k, *u = t + k + h;
    for (int a = 0; a < 200; a++) {
        for (int i = h - 1; i > 0; i--) {
            int j = below(i + 1);
            u16 x = u[i]; u[i] = u[j]; u[j] = x;
        }
        int ok = 1;
        for (int i = 0; i < h; i++)
            if (UQ_IN.club[s[i] - 1].rank == UQ_IN.club[u[i] - 1].rank) { ok = 0; break; }
        if (ok) break;
    }
    for (int i = 0; i < h; i++) {
        if (below(2)) { ta[i] = s[i]; tb[i] = u[i]; } else { ta[i] = u[i]; tb[i] = s[i]; }
    }
    for (int i = 0; i < h; i++) {
        int a = ta[i], b = tb[i];
        u32 pa = sq(a), pb = sq(b);
        int w = below(1000) < pa * 1000 / (pa + pb) ? a : b, l = w == a ? b : a;
        UQ_OUT.last[a - 1] = UQ_OUT.last[b - 1] = r;
        if ((a == UQ_IN.manager || b == UQ_IN.manager) && UQ_OUT.mt_n < 6) {
            int k = UQ_OUT.mt_n++;
            UQ_OUT.mt_round[k] = r;
            UQ_OUT.mt_opp[k] = a == UQ_IN.manager ? b : a;
            UQ_OUT.mt_win[k] = w == UQ_IN.manager;
        }
        if (WIN[r] != OUT) add(WIN[r], w);
        if (LOSE[r] == SPLIT)
            add(RN[CO_Q2ch] < x_split ? CO_Q2ch : CO_Q3ch, l);
        else if (LOSE[r] != OUT)
            add(LOSE[r], l);
    }
}

void uq_season(void) {
    static const u8 none[3] = { 0, 0, 0 };
    static u16 own[3];
    rng = UQ_IN.seed;
    for (int c = 0; c < UQ_IN.nclub; c++) { UQ_OUT.round_of[c] = NR; UQ_OUT.last[c] = NR; }
    own[0] = own[1] = own[2] = 0;
    rebalance(UQ_IN.eps, none, 0);              /* where would the holders qualify domestically */
    assign(own);
    for (int h = 0; h < 3; h++) {
        int c = UQ_IN.hold[h], dom = NR;
        UQ_OUT.status[h] = 0;
        if (!c) continue;
        for (int i = 0; i < ne; i++)
            if (CLUB[i] == c) dom = E[i].round;
        int league = h < 2 ? dom == CL_LS : dom == EL_LS || (dom != NR && COMP(dom) == 0);
        UQ_OUT.status[h] = league ? 1 : 2;
        if (!league) own[h] = c;
    }
    assign(own);                                /* the club coefficients of the places */
    for (int r = 0; r < NA; r++)
        for (int k = 0; k <= NL; k++) CRC[r][k] = 0;
    for (int i = 0; i < ne; i++)
        if (CLUB[i]) CRC[E[i].rank][E[i].code] = UQ_IN.club[CLUB[i] - 1].coef;
    rebalance(UQ_IN.eps, UQ_OUT.status, 1);
    assign(own);
    UQ_OUT.nent = ne;
    for (int r = 0; r < NR; r++) RN[r] = 0;
    for (int rk = 1; rk < NA; rk++)             /* (rank order, as season.py; the order does not matter) */
        for (int i = 0; i < ne; i++)
            if (E[i].rank == rk && CLUB[i]) {
                add(E[i].round, CLUB[i]);
                UQ_OUT.round_of[CLUB[i] - 1] = E[i].round;
            }
    int m = UQ_IN.manager;
    if (m && UQ_IN.force && UQ_IN.force < NR) {   /* (test builds) the manager's club into another round */
        for (int r = 0; r < NR; r++)
            for (int i = 0; i < RN[r]; i++)
                if (RL[r][i] == m) RL[r][i] = RL[r][--RN[r]];
        add(UQ_IN.force, m);
        UQ_OUT.round_of[m - 1] = UQ_IN.force;
    }
    UQ_OUT.mt_n = 0;
    UQ_OUT.standin = 0;
    static const u8 HR[3] = { CL_LS, CL_LS, EL_LS };
    for (int h = 0; h < 3; h++)
        if (own[h]) { add(HR[h], own[h]); UQ_OUT.round_of[own[h] - 1] = HR[h]; }
    for (const u8 *p = SCHED; *p != OUT || p[1] != OUT; p++)
        if (*p != OUT) play(*p);
    /* a small world (fewer than ~50 associations): a league phase short of 36 takes the best clubs by coefficient
       not in any league phase (of the clubs seen: the top 9 and the cup winner of each association, the holders) */
    static const u8 LS[3] = { CL_LS, EL_LS, CO_LS };
    for (int c = 0; c <= UQ_IN.nclub; c++) taken[c] = 0;
    for (int c = 0; c < 3; c++)
        for (int i = 0; i < RN[LS[c]]; i++) taken[RL[LS[c]][i]] = 1;
    for (int c = 0; c < 3; c++) {
        int r = LS[c];
        while (RN[r] < 36) {
            int b = 0;
            for (int k = 1; k <= UQ_IN.nclub; k++)
                if (!taken[k] && UQ_IN.club[k - 1].id && (!b || seed_less(k, b))) b = k;
            if (!b) break;
            taken[b] = 1;
            add(r, b);
        }
        int n = RN[r] < 36 ? RN[r] : 36;
        UQ_OUT.n[c] = n;
        /* the manager's club still has its ties to play: a stand-in holds its place (the best club by coefficient
           in no league phase, with a record: index < 550) until the qualifying rounds are over */
        if (m && UQ_OUT.mt_n && UQ_OUT.round_of[m - 1] != CL_LS && UQ_OUT.round_of[m - 1] != EL_LS &&
            UQ_OUT.round_of[m - 1] != CO_LS)
            for (int i = 0; i < n; i++)
                if (RL[r][i] == m) {
                    int b = 0;
                    for (int k = 1; k <= 550 && k <= UQ_IN.nclub; k++)
                        if (!taken[k] && UQ_IN.club[k - 1].id && (!b || seed_less(k, b))) b = k;
                    if (b) { taken[b] = 1; RL[r][i] = b; UQ_OUT.standin = b; }
                }
        for (int i = 0; i < n; i++) UQ_OUT.ls[c][i] = RL[r][i];
    }
}
