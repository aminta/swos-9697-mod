/* The other confederations' club cups of a world career (World 2026-27): CONMEBOL, CONCACAF, AFC, CAF, OFC, FIFA.

   Compiled twice: for the game (tools/cobj.py: i686 freestanding, linked into an obj1 cave, called from the season
   end's asm, conti.py) and natively for the tests (tools/conti.py --test: ctypes). Every cup is data (conti.py packs
   internal/conti/<conf>.format.json + .access.json into CT_SPEC): its rounds (knockout / groups), draws, routes
   (winners, losers, group places -> another round, possibly of another cup), the access lists per association
   (league places, the cup winner, Apertura / Clausura champions, 'the next club not yet in'), the holders' places.

   ct_season(): one whole edition of every cup from the world's tables (CT_IN, filled per country at the season
   end): the entrants, then every round in calendar order (month, cup, round), draws seeded by the confederation's
   ranking, matches simulated by strength; the winners become the next edition's holders (CT_ST, in the save). The
   career club's own rounds (segments in slot 3) use the same round steps (ct_round) later. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;

#define NA 48                           /* associations (countries) of the confederations in the world */
#define NL 16                           /* league clubs kept per association (the final table's top 16) */
#define NC 640                          /* clubs seen */
#define NCUP 16
#define NRD 12                          /* rounds per cup */
#define NE 64                           /* entrants of a round */
#define RB 24                           /* bytes per round in the spec */
#define OUT 0xFF
#define CHAMP 0xFE

/* round kinds, draws, association rules (spec byte values) */
enum { K_KO, K_GROUPS };
enum { D_ORDER, D_POTS2, D_SAMEPAIRS, D_SEED12, D_BRACKET, D_GROUPS, D_CROSS };
enum { A_ANY, A_NO, A_NOVIA };
/* access codes: 0 champion, 1 cup winner, 2..10 the k-th place, NEXT the best club not yet in, AP / CL a split
   season's stage champions (else as NEXT) */
enum { C_NEXT = 0x40, C_AP = 0x41, C_CL = 0x42 };

struct ct_in {                          /* filled by the caller */
    u32 seed;
    u16 nclub;
    u16 manager;                        /* the career club: index + 1 (0 = none) */
    u16 league[NA][NL];                 /* club indices + 1, final table order (0 = none) */
    u16 cup[NA];                        /* the national cup winner */
    u16 ap[NA], cl[NA];                 /* stage champions (Argentina) */
    struct { u16 id; u8 assoc; u8 pad; u32 str; u32 pts; } club[NC];   /* team word, association, strength, ranking */
};
struct ct_state {                       /* kept in the save */
    u16 mark;                           /* 'CT' */
    u16 season;
    struct { u16 id; u8 assoc; u8 pad; u32 str; u32 pts; } hold[NCUP];  /* each cup's holder (id 0 = none) */
};
struct ct_out {
    u8 ncup;
    u8 pad[3];
    u16 winner[NCUP], second[NCUP];     /* club indices + 1 */
    u8 last[NC];                        /* the last round reached by each club: cup << 4 | round, OUT none */
    u8 out_of[NC];                      /* how it left that round: 0 lost / eliminated, 1 won the cup */
    u8 nent[NCUP][NRD];                 /* entrants per round (after its draw) */
    u16 ent[NCUP][NRD][NE];             /* in draw order: ties (a, b) / groups of gsize */
    u8 res[NCUP][NRD][NE];              /* ko: 1 = the first club of the tie went through; groups: final place */
};

const u8 *CT_SPEC;
struct ct_in CT_IN;
struct ct_state CT_ST;
struct ct_out CT_OUT;

/* --- the spec ----------------------------------------------------------------------------------------------------- */
static u8 ncup, na;
static const u8 *cupr[NCUP];            /* first round of each cup */
static u8 nrd[NCUP];
static const u8 *acc;                   /* access entries: assoc, cup, round, code */
static u16 nacc;
static const u8 *hol;                   /* holders: src cup, dst cup, dst round */
static u8 nhol;
#define RND(c, r) (cupr[c] + (r) * RB)

static void parse(void) {
    const u8 *p = CT_SPEC;
    ncup = p[0]; na = p[1];
    p += 4;
    for (int c = 0; c < ncup; c++) {
        nrd[c] = p[0];
        cupr[c] = p + 4;
        p += 4 + nrd[c] * RB;
    }
    nacc = p[0] | p[1] << 8;
    acc = p + 2;
    p += 2 + 4 * nacc;
    nhol = p[0];
    hol = p + 1;
}

/* --- random, strength -------------------------------------------------------------------------------------------- */
static u32 rng;
static u32 below(u32 n) { rng = rng * 1103515245u + 12345u; return n ? ((rng >> 16) * n) >> 16 : 0; }
static u32 sq(int c) { u32 s = CT_IN.club[c - 1].str / 16; if (s < 1) s = 1; if (s > 4000) s = 4000; return s * s; }
static u32 pts(int c) { return CT_IN.club[c - 1].pts ? CT_IN.club[c - 1].pts : CT_IN.club[c - 1].str / 64; }
static int assoc(int c) { return CT_IN.club[c - 1].assoc; }

/* goals of one side: binomial(8, m / 8), m in eighths */
static int goals(u32 m8) { int g = 0; for (int i = 0; i < 8; i++) if (below(64) < m8) g++; return g; }
/* a match: home h v away a -> goals; mean 0.5 .. 2.5 by the strengths' square ratio, a home bonus */
static void match(int h, int a, int neutral, int *gh, int *ga) {
    u32 sh = sq(h), sa = sq(a);
    u32 r = (u32)(((unsigned long long)sh * 64) / (sh + sa));             /* 0..64 */
    u32 mh = 4 + r / 2 + (neutral ? 0 : 2), ma = 4 + (64 - r) / 2;         /* eighths of a goal: 4..36 */
    *gh = goals(mh > 63 ? 63 : mh);
    *ga = goals(ma > 63 ? 63 : ma);
}
/* a tie a v b (b at home in the second leg when legs = 2): 1 if a goes through. level: 0 penalties, 1 extra time +
   penalties, 2 away goals then penalties (CAF, CONCACAF) */
static int tie(int a, int b, int legs, int level, int neutral) {
    int x, y, ga = 0, gb = 0, awa = 0, awb = 0;
    if (legs == 2) {
        match(a, b, 0, &x, &y); ga += x; gb += y; awb = y;
        match(b, a, 0, &x, &y); gb += x; ga += y; awa = y;
    } else {
        match(a, b, neutral, &x, &y); ga += x; gb += y;
    }
    if (ga != gb) return ga > gb;
    if (level == 2 && legs == 2 && awa != awb) return awa > awb;
    if (level == 1) {                   /* extra time */
        match(a, b, 1, &x, &y);
        x /= 3; y /= 3;
        if (x != y) return x > y;
    }
    return below(100) < 50;             /* penalties */
}

/* --- the edition ------------------------------------------------------------------------------------------------- */
static u16 E[NCUP][NRD][NE];            /* a round's entrants (club + 1), before its draw */
static u8 EV[NCUP][NRD][NE];            /* 1 = came through an earlier round ('via': the association exception) */
static u8 EK[NCUP][NRD][NE];            /* side for D_CROSS (0 = this cup's, 1 = another's) and its rank key */
static u8 EN[NCUP][NRD];
static u8 taken[NC + 1];                /* the access pass: the club already has a place (this edition) */

static void enter(int c, int r, int club, int via, int side) {
    if (!club || r >= nrd[c] || EN[c][r] >= NE) return;
    for (int i = 0; i < EN[c][r]; i++) if (E[c][r][i] == club) return;
    int i = EN[c][r]++;
    E[c][r][i] = club; EV[c][r][i] = via; EK[c][r][i] = side;
}
/* a route byte: cup << 4 | round, OUT, CHAMP */
static void route(int from_cup, u8 rt, int club, int side_rank) {
    if (rt == OUT || rt == CHAMP || !club) return;
    int c = rt >> 4, r = rt & 15;
    enter(c, r, club, 1, (c != from_cup ? 0x80 : 0) | (side_rank & 0x7F));
}

static int next_club(int a) {          /* the best league club of association a not yet in */
    for (int l = 0; l < NL; l++) {
        int x = CT_IN.league[a][l];
        if (x && !taken[x]) return x;
    }
    return 0;
}
static void access(void) {
    for (int c = 0; c <= NC; c++) taken[c] = 0;
    u8 vac[NCUP * 2]; int nvac = 0;     /* holder places with no holder yet (season 1): filled after the access */
    for (int h = 0; h < nhol; h++) {    /* the holders first: their own places */
        const u8 *e = hol + 3 * h;
        int s = e[0];
        if (!CT_ST.hold[s].id) { if (nvac < NCUP * 2) vac[nvac++] = h; continue; }
        int k = 0;                      /* the holder's club index (seen this season, else appended) */
        for (int i = 0; i < CT_IN.nclub; i++) if (CT_IN.club[i].id == CT_ST.hold[s].id) { k = i + 1; break; }
        if (!k && CT_IN.nclub < NC) {
            k = ++CT_IN.nclub;
            CT_IN.club[k - 1].id = CT_ST.hold[s].id; CT_IN.club[k - 1].assoc = CT_ST.hold[s].assoc;
            CT_IN.club[k - 1].str = CT_ST.hold[s].str; CT_IN.club[k - 1].pts = CT_ST.hold[s].pts;
        }
        if (k) { enter(e[1], e[2], k, 0, 0); taken[k] = 1; }   /* (a holder may hold places in two cups: the Recopa) */
    }
    for (int i = 0; i < nacc; i++) {
        const u8 *e = acc + 4 * i;
        int a = e[0], c = e[1], r = e[2], k = e[3], club = 0;
        if (k == 0) club = CT_IN.league[a][0];
        else if (k == 1) club = CT_IN.cup[a];
        else if (k == C_AP) club = CT_IN.ap[a];
        else if (k == C_CL) club = CT_IN.cl[a];
        else if (k >= 2 && k <= NL) club = CT_IN.league[a][k - 1];
        if (club && taken[club]) club = 0;          /* already in: the place passes down the table */
        if (!club) club = next_club(a);
        if (club) { enter(c, r, club, 0, 0); taken[club] = 1; }
    }
    for (int v = 0; v < nvac; v++) {    /* a vacant holder place: the best ranked club not yet in (declared) */
        const u8 *e = hol + 3 * vac[v];
        if (e[1] != e[0] && RND(e[1], e[2])[0] == K_KO && nrd[e[1]] == 1) continue;   /* (a holders' match: none) */
        int best = 0;
        for (int i = 1; i <= CT_IN.nclub; i++)
            if (!taken[i] && (!best || pts(i) > pts(best))) best = i;
        if (best) { enter(e[1], e[2], best, 0, 0); taken[best] = 1; }
    }
}

/* --- draws -------------------------------------------------------------------------------------------------------- */
static u16 D[NE];                       /* the drawn order */
static u8 DV[NE], DK[NE];
static void sort_by_pts(u16 *x, u8 *v, u8 *k, int n) {
    for (int i = 1; i < n; i++) {
        u16 cx = x[i]; u8 cv = v[i], ck = k[i];
        int j = i;
        while (j > 0 && pts(cx) > pts(x[j - 1])) { x[j] = x[j - 1]; v[j] = v[j - 1]; k[j] = k[j - 1]; j--; }
        x[j] = cx; v[j] = cv; k[j] = ck;
    }
}
static void shuffle(u16 *x, u8 *v, u8 *k, int n) {
    for (int i = n - 1; i > 0; i--) {
        int j = below(i + 1);
        u16 t = x[i]; x[i] = x[j]; x[j] = t;
        u8 tv = v[i]; v[i] = v[j]; v[j] = tv;
        u8 tk = k[i]; k[i] = k[j]; k[j] = tk;
    }
}
static int conflict(int a, int b, int va, int vb, int rule) {
    if (rule == A_ANY) return 0;
    if (assoc(a) != assoc(b)) return 0;
    if (rule == A_NOVIA && (va || vb)) return 0;
    return 1;
}
/* a knockout round's pairs into D (D[2i] v D[2i+1]: the second at home in the second leg) */
static void draw_ko(int c, int r, const u8 *R) {
    int n = EN[c][r], dr = R[4], rule = R[5];
    u16 x[NE]; u8 v[NE], k[NE];
    for (int i = 0; i < n; i++) { x[i] = E[c][r][i]; v[i] = EV[c][r][i]; k[i] = EK[c][r][i]; }
    if (dr == D_ORDER || dr == D_BRACKET) {
        for (int i = 0; i < n; i++) { D[i] = x[i]; DV[i] = v[i]; DK[i] = k[i]; }
        return;
    }
    if (dr == D_SAMEPAIRS) {            /* clubs of one association against each other, the first drawn at home */
        int m = 0;
        u8 used[NE] = {0};
        shuffle(x, v, k, n);
        for (int i = 0; i < n; i++) {
            if (used[i]) continue;
            used[i] = 1;
            for (int j = i + 1; j < n; j++)
                if (!used[j] && assoc(x[j]) == assoc(x[i])) {
                    used[j] = 1;
                    D[m] = x[j]; DV[m] = v[j]; DK[m] = k[j]; m++;  /* (the first drawn plays at home: listed second) */
                    D[m] = x[i]; DV[m] = v[i]; DK[m] = k[i]; m++;
                    goto next;
                }
            D[m] = x[i]; DV[m] = v[i]; DK[m] = k[i]; m++;           /* (no partner: a bye-like odd one) */
        next:;
        }
        return;
    }
    if (dr == D_CROSS) {                /* fixed: this cup's side ranked best..worst v the other's worst..best */
        u16 a[NE], b[NE]; u8 av[NE], bv[NE], ak[NE], bk[NE];
        int na_ = 0, nb = 0;
        for (int i = 0; i < n; i++)
            if (k[i] & 0x80) { b[nb] = x[i]; bv[nb] = v[i]; bk[nb] = k[i]; nb++; }
            else { a[na_] = x[i]; av[na_] = v[i]; ak[na_] = k[i]; na_++; }
        for (int i = 1; i < na_; i++) { u16 t = a[i]; u8 tk = ak[i], tv = av[i]; int j = i;
            while (j > 0 && (ak[j - 1] & 0x7F) > (tk & 0x7F)) { a[j] = a[j - 1]; ak[j] = ak[j - 1]; av[j] = av[j - 1]; j--; }
            a[j] = t; ak[j] = tk; av[j] = tv; }
        for (int i = 1; i < nb; i++) { u16 t = b[i]; u8 tk = bk[i], tv = bv[i]; int j = i;
            while (j > 0 && (bk[j - 1] & 0x7F) > (tk & 0x7F)) { b[j] = b[j - 1]; bk[j] = bk[j - 1]; bv[j] = bv[j - 1]; j--; }
            b[j] = t; bk[j] = tk; bv[j] = tv; }
        int m = 0;
        for (int i = 0; i < na_ && i < nb; i++) {   /* the other cup's club at home first: listed first */
            D[m] = b[nb - 1 - i]; DV[m] = bv[nb - 1 - i]; DK[m] = bk[nb - 1 - i]; m++;
            D[m] = a[i]; DV[m] = av[i]; DK[m] = ak[i]; m++;
        }
        return;
    }
    /* D_POTS2 / D_SEED12: the seeded half (D_SEED12: this cup's group winners, rank keys 1..; else by ranking)
       against the other half, drawn; the seeded club at home in the second leg (listed second) */
    if (dr == D_SEED12) {
        for (int i = 1; i < n; i++) { u16 t = x[i]; u8 tk = k[i], tv = v[i]; int j = i;
            while (j > 0 && (k[j - 1] & 0x7F) > (tk & 0x7F)) { x[j] = x[j - 1]; k[j] = k[j - 1]; v[j] = v[j - 1]; j--; }
            x[j] = t; k[j] = tk; v[j] = tv; }
    } else
        sort_by_pts(x, v, k, n);
    int h = n / 2;
    for (int tries = 0; tries < 50; tries++) {
        u16 lo[NE]; u8 lv[NE], lk[NE];
        for (int i = 0; i < n - h; i++) { lo[i] = x[h + i]; lv[i] = v[h + i]; lk[i] = k[h + i]; }
        shuffle(lo, lv, lk, n - h);
        int ok = 1;
        for (int i = 0; i < h; i++) if (conflict(x[i], lo[i], v[i], lv[i], rule)) ok = 0;
        if (ok || tries == 49) {
            for (int i = 0; i < h; i++) {
                D[2 * i] = lo[i]; DV[2 * i] = lv[i]; DK[2 * i] = lk[i];
                D[2 * i + 1] = x[i]; DV[2 * i + 1] = v[i]; DK[2 * i + 1] = k[i];
            }
            return;
        }
    }
}
/* groups into D: group g = D[g * size ..]; pots of ngroups clubs by ranking (via clubs last), the holder A1 */
static void draw_groups(int c, int r, const u8 *R) {
    int n = EN[c][r], ng = R[6], gs = R[7], rule = R[5];
    u16 x[NE]; u8 v[NE], k[NE];
    int m = 0;
    for (int pass = 0; pass < 3; pass++)        /* holders (rank key 0x7F, set by the caller: not used), direct, via */
        for (int i = 0; i < n; i++)
            if ((pass == 1 && !EV[c][r][i]) || (pass == 2 && EV[c][r][i])) {
                x[m] = E[c][r][i]; v[m] = EV[c][r][i]; k[m] = EK[c][r][i]; m++;
            }
    int nd = 0;
    while (nd < m && !v[nd]) nd++;
    sort_by_pts(x, v, k, nd);
    int hold = R[16] && CT_ST.hold[c].id;
    if (hold)                           /* the holder first (pot 1, group A) */
        for (int i = 0; i < nd; i++)
            if (CT_IN.club[x[i] - 1].id == CT_ST.hold[c].id) {
                u16 t = x[i]; u8 tv = v[i], tk = k[i];
                for (int j = i; j > 0; j--) { x[j] = x[j - 1]; v[j] = v[j - 1]; k[j] = k[j - 1]; }
                x[0] = t; v[0] = tv; k[0] = tk;
                break;
            }
    for (int i = 0; i < NE; i++) D[i] = 0;
    for (int p = 0; p < gs; p++) {
        int base = p * ng;
        u16 px[NE]; u8 pv[NE], pk[NE];
        int pn = 0;
        for (int i = base; i < base + ng && i < m; i++) { px[pn] = x[i]; pv[pn] = v[i]; pk[pn] = k[i]; pn++; }
        if (p == 0 && hold) {
            D[0] = px[0]; DV[0] = pv[0]; DK[0] = pk[0];
            for (int i = 1; i < pn; i++) { px[i - 1] = px[i]; pv[i - 1] = pv[i]; pk[i - 1] = pk[i]; }
            pn--;
        } else
            ;
        shuffle(px, pv, pk, pn);
        for (int i = 0; i < pn; i++) {
            int best = -1;
            for (int t = 0; t < ng; t++) {
                int g = (t + below(ng)) % ng, s = g * gs + p;
                if (D[s]) continue;
                int bad = 0;
                for (int q = 0; q < p; q++)
                    if (D[g * gs + q] && conflict(D[g * gs + q], px[i], DV[g * gs + q], pv[i], rule)) bad = 1;
                if (!bad) { best = s; break; }
                if (best < 0) best = -2 - s;            /* (a slot with a conflict: the last resort) */
            }
            if (best < -1) best = -2 - best;
            if (best < 0)                               /* (every free slot taken by the loop's order: any free) */
                for (int g = 0; g < ng; g++) if (!D[g * gs + p]) { best = g * gs + p; break; }
            if (best >= 0) { D[best] = px[i]; DV[best] = pv[i]; DK[best] = pk[i]; }
        }
    }
}

/* --- rounds ------------------------------------------------------------------------------------------------------- */
static void reached(int club, int c, int r) { CT_OUT.last[club - 1] = c << 4 | r; }

/* a group: double / single round robin of D[base .. base + gs) -> places into P */
static void group(int base, int gs, int grounds, int *P) {
    int pt[8] = {0}, gd[8] = {0}, gf[8] = {0};
    for (int leg = 0; leg < grounds; leg++)
        for (int i = 0; i < gs; i++)
            for (int j = i + 1; j < gs; j++) {
                int h = leg ? j : i, a = leg ? i : j, x, y;
                if (!D[base + h] || !D[base + a]) continue;
                match(D[base + h], D[base + a], 0, &x, &y);
                gf[h] += x; gf[a] += y; gd[h] += x - y; gd[a] += y - x;
                if (x > y) pt[h] += 3; else if (x < y) pt[a] += 3; else { pt[h]++; pt[a]++; }
            }
    for (int i = 0; i < gs; i++) P[i] = i;
    for (int i = 1; i < gs; i++) {
        int t = P[i], j = i;
        while (j > 0) {
            int u = P[j - 1];
            s32 d = pt[t] != pt[u] ? pt[t] - pt[u] : gd[t] != gd[u] ? gd[t] - gd[u] : gf[t] != gf[u] ? gf[t] - gf[u]
                    : (s32)(sq(D[base + t]) > sq(D[base + u])) - (s32)(sq(D[base + t]) < sq(D[base + u]));
            if (d <= 0) break;
            P[j] = u; j--;
        }
        P[j] = t;
    }
    for (int i = 0; i < gs; i++) gd[i] = gd[i] * 100 + gf[i] + pt[i] * 10000;   /* (a record key for the ranking) */
    for (int i = 0; i < gs; i++) P[8 + i] = gd[P[i]];
}

static void ct_round(int c, int r) {
    const u8 *R = RND(c, r);
    int n = EN[c][r];
    if (!n) return;
    if (R[0] == K_GROUPS) draw_groups(c, r, R); else draw_ko(c, r, R);
    CT_OUT.nent[c][r] = n;
    for (int i = 0; i < n && i < NE; i++) { CT_OUT.ent[c][r][i] = D[i]; if (D[i]) reached(D[i], c, r); }
    if (R[0] == K_GROUPS) {
        int ng = R[6], gs = R[7];
        /* every group, then each place's clubs ranked across the groups by record (the rank keys of the next draw) */
        static int PL[NCUP][8][16];
        static u16 byplace[8][16];
        static s32 key[8][16];
        for (int g = 0; g < ng; g++) {
            int P[16];
            group(g * gs, gs, R[8], P);
            for (int q = 0; q < gs; q++) {
                byplace[q][g] = D[g * gs + P[q]];
                key[q][g] = P[8 + q];
                CT_OUT.res[c][r][g * gs + P[q]] = q + 1;
                PL[c][q][g] = P[q];
            }
        }
        for (int q = 0; q < gs && q < 4; q++) {
            int ord[16];
            for (int g = 0; g < ng; g++) ord[g] = g;
            for (int i = 1; i < ng; i++) { int t = ord[i], j = i;
                while (j > 0 && key[q][ord[j - 1]] < key[q][t]) { ord[j] = ord[j - 1]; j--; }
                ord[j] = t; }
            for (int i = 0; i < ng; i++) {
                int club = byplace[q][ord[i]];
                if (R[12 + q] == OUT) continue;
                route(c, R[12 + q], club, q * ng + i + 1);
            }
        }
        return;
    }
    /* knockout: D[2i] v D[2i+1] */
    for (int i = 0; i + 1 < n; i += 2) {
        int a = D[i], b = D[i + 1];
        int w = tie(a, b, R[1], R[2], R[3]);
        CT_OUT.res[c][r][i] = w;
        int win = w ? a : b, los = w ? b : a;
        if (R[10] == CHAMP) {
            CT_OUT.winner[c] = win; CT_OUT.second[c] = los;
            CT_OUT.out_of[win - 1] = 1;
        } else
            route(c, R[10], win, (DK[w ? i : i + 1] & 0x7F) ? DK[w ? i : i + 1] & 0x7F : i / 2 + 1);
        route(c, R[11], los, i / 2 + 1);
    }
    if (n & 1) route(c, R[10], D[n - 1], 0x7F);         /* (an odd one goes through) */
}

/* --- the season --------------------------------------------------------------------------------------------------- */
void ct_season(void) {
    parse();
    rng = CT_IN.seed ? CT_IN.seed : 1;
    for (int c = 0; c < NCUP; c++) for (int r = 0; r < NRD; r++) EN[c][r] = 0;
    CT_OUT.ncup = ncup;
    for (int i = 0; i < NC; i++) { CT_OUT.last[i] = OUT; CT_OUT.out_of[i] = 0; }
    for (int c = 0; c < NCUP; c++) { CT_OUT.winner[c] = CT_OUT.second[c] = 0;
        for (int r = 0; r < NRD; r++) { CT_OUT.nent[c][r] = 0; for (int i = 0; i < NE; i++) { CT_OUT.ent[c][r][i] = 0; CT_OUT.res[c][r][i] = 0; } } }
    access();
    /* every round in calendar order: month (8 = August first, the season's order), then cup, then round */
    for (int mo = 0; mo < 12; mo++) {
        int month = (mo + 7) % 12 + 1;
        for (int c = 0; c < ncup; c++)
            for (int r = 0; r < nrd[c]; r++)
                if (RND(c, r)[9] == month) ct_round(c, r);
    }
    for (int c = 0; c < ncup; c++) {    /* the holders of the next edition */
        int w = CT_OUT.winner[c];
        if (!w) continue;
        CT_ST.hold[c].id = CT_IN.club[w - 1].id; CT_ST.hold[c].assoc = CT_IN.club[w - 1].assoc;
        CT_ST.hold[c].str = CT_IN.club[w - 1].str; CT_ST.hold[c].pts = CT_IN.club[w - 1].pts;
    }
    CT_ST.mark = 0x5443; CT_ST.season++;
}

#define OFF(t, f) ((u32) __builtin_offsetof(struct t, f))
const u32 CT_LAYOUT[] = { sizeof(struct ct_in), sizeof(struct ct_state), sizeof(struct ct_out),
                          OFF(ct_in, league), OFF(ct_in, cup), OFF(ct_in, ap), OFF(ct_in, cl), OFF(ct_in, club),
                          OFF(ct_out, winner), OFF(ct_out, second), OFF(ct_out, last), OFF(ct_out, nent),
                          OFF(ct_out, ent), OFF(ct_out, res), NA, NL, NC, NCUP, NRD, NE };
