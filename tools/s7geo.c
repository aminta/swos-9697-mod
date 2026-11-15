/* 4.2 Serie D geography (MC 14/11; band S7GEO 0x19000, its own TU: MC's room ruling, the S7SWAP band is full). The code, the neighbour
   table, the log and (after Davide's ok) the per-club coordinates of the chain that makes a seat for a pool arrival. Linked
   only with GP_S7 (s7swap.py link_geo); gplay.c's GP_GEOCH points at s7geochain. Host tests include it natively (DATA empty). */
#include <stdint.h>
#ifndef DATA
#define DATA __attribute__((section(".data")))
#endif
enum { S7GEO_G = 9, S7GEO_MAXSTEPS = 8, S7GEO_NL = 32 };
uint8_t S7GEO_NEIGH[S7GEO_G][S7GEO_G] DATA = {{0}};      /* per girone: its neighbours in list order, 0xFF-terminated */
uint8_t S7GEO_ON DATA = 0;                                /* the table is in the pack (0: no chain) */
uint16_t S7GEO_LOG[S7GEO_NL][2] DATA = {{0}};            /* the natives moved this season end: {club (global number), from << 8 | to} */
int32_t S7GEO_NLOG DATA = 0;
int32_t S7GEO_BAD DATA = 0;
/* Town coordinates (MC 14/11, Davide's ok): per registry ident, latitude and longitude in 0.01 degree (0 = none). The mover of a chain
   step is the movable club NEAREST to the target girone's centroid (the mean of that girone's stayers, before the move); ties the lowest
   row. S7GEO_HAVE 0 (a pack without coordinates): the lowest row, as before. s7swap.py checks every club has one, inside Italy's box. */
enum { S7GEO_NID = 320 };
int16_t S7GEO_XY[S7GEO_NID][2] DATA = {{0}};
uint8_t S7GEO_HAVE DATA = 0;
uint16_t S7GEO_FILE DATA = 0;                                 /* the Serie D file's number (a team word's low byte) */
int32_t S7GEO_BASE DATA = 0;                                  /* ... and its first global number: row = global - base */
uint32_t (*S7GEO_IDENT)(uint32_t w) DATA = 0;                 /* s7swap.c's s7_ident (set by s7swap.py; host tests: a stand-in) */

/* 4.2 Serie D geography (MC 14/11, backlog 'Serie D pool arrivals placed geographically'): a pool arrival whose own girone is full
   takes it anyway, through a CHAIN of one-step moves along the pack's neighbour table (S7GEO_NEIGH, ita pack data 'geo': per
   girone its neighbours in list order) to the nearest girone with a seat (breadth first, ties in list order). Each step moves
   one STAYER of the girone it leaves (never the manager's club, never an arrival of this season end, never a club that already
   moved: only copy == slt qualifies, so a club moves at most once) into the next girone. At most S7GEO_MAXSTEPS steps; any step
   without a mover, or a longer chain: no chain (S7GEO_BAD++, today's fallbacks). Called by gplay.c's pg_one (GP_GEOCH). */

static int geo_eligible(const uint8_t *e, int fl, int x, const int8_t *slt, const int8_t *copy, const uint8_t *pend, int npend,
                        const uint16_t *og, int nog)
{
    int h = e[0] | e[1] << 8;
    if (h >= npend || (pend[h >> 3] >> (h & 7) & 1) || copy[h] + e[2] != fl + x || copy[h] != slt[h]) return 0;
    for (int k = 0; k < nog; k++) if (og[k] == h) return 0;
    return 1;
}

/* The ONE read interface of the town coordinates (also for 42-cdkn's PAIR_GEO): s7geo_ll(w, &lat, &lon) - w = a team word (file | row << 8) of
   a club in the Serie D file or the pool; lat / lon in 0.01 degree; returns 1 when the club has a coordinate, else 0 (lat / lon untouched). */
int32_t s7geo_ll(uint32_t w, int16_t *lat, int16_t *lon)
{
    if (!S7GEO_HAVE || !S7GEO_IDENT) return 0;
    uint32_t id = S7GEO_IDENT(w);
    if (id >= S7GEO_NID || !S7GEO_XY[id][0]) return 0;
    *lat = S7GEO_XY[id][0]; *lon = S7GEO_XY[id][1];
    return 1;
}

static int geo_xy(int h, int32_t *la, int32_t *lo)             /* a club's town coordinates by its global number; 0 = none */
{
    int16_t a, b;
    if (!s7geo_ll((uint32_t)S7GEO_FILE | (uint32_t)(h - S7GEO_BASE) << 8, &a, &b)) return 0;
    *la = a; *lo = b;
    return 1;
}

static int geo_mover(const uint8_t *c, int rs, int nc, int fl, int x, int y, const int8_t *slt, const int8_t *copy, const uint8_t *pend,
                     int npend, const uint16_t *og, int nog, int mgr)
{
    int first = -1, best = -1, n = 0;
    int32_t sla = 0, slo = 0, la, lo, d, bd = 0;
    if (S7GEO_HAVE) {                                       /* the target girone's centroid: the mean of its stayers, before the move */
        for (int i = 0; i < nc; i++) {
            const uint8_t *e = c + rs * i;
            if (geo_eligible(e, fl, y, slt, copy, pend, npend, og, nog) && geo_xy(e[0] | e[1] << 8, &la, &lo)) { sla += la; slo += lo; n++; }
        }
        if (n) { sla /= n; slo /= n; }
    }
    for (int i = 0; i < nc; i++) {                          /* (the table's order = the rows' order: the lowest row first) */
        const uint8_t *e = c + rs * i;
        int h = e[0] | e[1] << 8;
        if (h == mgr || !geo_eligible(e, fl, x, slt, copy, pend, npend, og, nog)) continue;
        if (first < 0) first = i;
        if (!n || !geo_xy(h, &la, &lo)) continue;
        la -= sla; lo = (lo - slo) * 3 / 4;                 /* (a degree of longitude is ~0.75 of a degree of latitude at 41-45 N) */
        d = la * la + lo * lo;
        if (best < 0 || d < bd) { best = i; bd = d; }       /* (strictly nearer: a tie keeps the lowest row) */
    }
    return best >= 0 ? best : first;
}

int32_t s7geochain(const uint8_t *c, int32_t rs, int32_t nc, int32_t fl, int32_t a, int32_t cnt, const uint8_t *sz, uint8_t *occ,
                      const int8_t *slt, int8_t *copy, const uint8_t *pend, int32_t npend, const uint16_t *og, int32_t nog,
                      int32_t mgr)
{
    int prev[S7GEO_G], dist[S7GEO_G], q[S7GEO_G], qh = 0, qt = 0, to = -1;
    if (!S7GEO_ON || cnt > S7GEO_G || a < 0 || a >= cnt) return 0;
    for (int i = 0; i < cnt; i++) { dist[i] = -1; prev[i] = -1; }
    dist[a] = 0; q[qt++] = a;
    while (qh < qt && to < 0) {
        int x = q[qh++];
        for (int k = 0; k < S7GEO_G && S7GEO_NEIGH[x][k] != 0xFF; k++) {
            int y = S7GEO_NEIGH[x][k];
            if (y >= cnt || dist[y] >= 0) continue;
            dist[y] = dist[x] + 1; prev[y] = x; q[qt++] = y;
            if (occ[y] < sz[y]) { to = y; break; }         /* (the first girone with a seat in BFS order: nearest, then list order) */
        }
    }
    if (to < 0 || dist[to] > S7GEO_MAXSTEPS || S7GEO_NLOG + dist[to] > S7GEO_NL) { S7GEO_BAD++; return 0; }
    int path[S7GEO_G + 1], n = 0, mv[S7GEO_G];
    for (int y = to; y >= 0; y = prev[y]) path[n++] = y;   /* to ... a */
    for (int s = 0; s < n - 1; s++) {                      /* step s: from path[s + 1] into path[s] */
        mv[s] = geo_mover(c, rs, nc, fl, path[s + 1], path[s], slt, copy, pend, npend, og, nog, mgr);
        if (mv[s] < 0) { S7GEO_BAD++; return 0; }          /* (checked first: never a half chain) */
    }
    for (int s = 0; s < n - 1; s++) {
        const uint8_t *e = c + rs * mv[s];
        int h = e[0] | e[1] << 8;
        copy[h] = (int8_t)(fl + path[s] - e[2]);
        occ[path[s]]++; occ[path[s + 1]]--;
        S7GEO_LOG[S7GEO_NLOG][0] = (uint16_t)h;
        S7GEO_LOG[S7GEO_NLOG][1] = (uint16_t)(path[s + 1] << 8 | path[s]);
        S7GEO_NLOG++;
    }
    return 1;                                               /* (girone a lost a club to its neighbour: a seat for the arrival) */
}

/* 4.2 S7 redraw (MC design internal/handoff/s7-redraw.md, Davide 15/11 "regola attuale al 78% e basta"): Serie C (3 x 20) and Serie D
   (9 x 18) groups redrawn at every season end. s7rd_rule is the C twin of Panchina's oracle tools/s7redraw.py rule() (frozen 42-redraw
   31db319): integer arithmetic only, the same groups bit for bit (host test test_s7redraw: the oracle's goldens). Pure: no global read
   but its arguments; the caller (s7swap.c, through S7RD_PTR) builds the inputs from the registry and writes nd[].
   - clubs: n, sorted by ident ascending (the oracle's tie-break order), their TRAVEL points (s7rd_travel) in 0.01 degree;
     last[k] / prev[k] the group last season at this level (0xFF none), sec[k] 1 = a second team (U23 / Next Gen / Futuro).
   - groups: ng anchors (the centroids of last season's groups, s7rd_centroid), cap[g] clubs each (sum = n).
   - second teams: never two in a group, none in its prev group (the alternation clause); among the allowed arrangements (the
     permutations of the groups in lexicographic order, itertools') the seed picks one: arr = allowed[seed % count]. Fixed first.
   - the others: the min-cost assignment to the group slots (slots = groups in order, each repeated by its free places), cost =
     isqrt(16 dlat^2 + 9 dlon^2) - S7RD_STAY if the slot's group is the club's last one; the Hungarian algorithm (Jonker-Volgenant
     form, the oracle's loop order: the same optimum and the same tie choices). out[k] = the club's group.
   Returns 0, or -1 (inputs out of range / no allowed arrangement / caps not summing to n): out untouched then (the caller keeps
   today's placement). work: S7RD_WORK bytes, 4-aligned. */
#ifndef S7RD_STAY_TEST
#define S7RD_STAY_TEST 540                                  /* (host test control: 0 = no stability bonus) */
#endif
enum { S7RD_STAY = S7RD_STAY_TEST, S7RD_MAXN = 168, S7RD_MAXG = 9, S7RD_MAXSEC = 4 };
struct s7rd_work {
    int32_t u[S7RD_MAXN + 1], v[S7RD_MAXN + 1], minv[S7RD_MAXN + 1];
    int16_t p[S7RD_MAXN + 1], way[S7RD_MAXN + 1], fr[S7RD_MAXN];
    int16_t d[S7RD_MAXN][S7RD_MAXG];                        /* isqrt distance of club k to group g */
    uint8_t used[S7RD_MAXN + 1], slot[S7RD_MAXN];
};
enum { S7RD_WORK = sizeof(struct s7rd_work) };

static int32_t rd_isqrt(uint32_t x)                         /* floor(sqrt(x)), math.isqrt */
{
    uint32_t r = 0, b = 1u << 30;
    while (b > x) b >>= 2;
    while (b) {
        if (x >= r + b) { x -= r + b; r = (r >> 1) + b; } else r >>= 1;
        b >>= 2;
    }
    return (int32_t)r;
}

void s7rd_travel(int32_t *la, int32_t *lo)                 /* the oracle's travel(): an island club travels from its mainland port */
{
    if (*la >= 3880 && *la <= 4140 && *lo >= 800 && *lo <= 990) { *la = 4209; *lo = 1180; return; }      /* Sardinia: Civitavecchia */
    if (*la >= 3650 && *la <= 3840 && *lo >= 1230 && *lo <= 1570) { *la = 3819; *lo = 1557; }           /* Sicily: the Messina strait */
}

/* the next permutation (lexicographic over 0..ng-1, length k) after a[]; 0 when a[] was the last (itertools.permutations' order) */
static int32_t rd_nextperm(uint8_t *a, int32_t k, int32_t ng)
{
    for (int32_t i = k - 1; i >= 0; i--) {
        for (int32_t c = a[i] + 1; c < ng; c++) {
            int32_t taken = 0;
            for (int32_t j = 0; j < i; j++) if (a[j] == c) taken = 1;
            if (taken) continue;
            a[i] = (uint8_t)c;
            for (int32_t j = i + 1; j < k; j++) {           /* the rest: the smallest unused, ascending */
                for (int32_t c2 = 0; c2 < ng; c2++) {
                    int32_t t2 = 0;
                    for (int32_t q = 0; q < j; q++) if (a[q] == c2) t2 = 1;
                    if (!t2) { a[j] = (uint8_t)c2; break; }
                }
            }
            return 1;
        }
    }
    return 0;
}

static int32_t rd_allowed(const uint8_t *a, int32_t k, const uint8_t *sp)
{
    for (int32_t i = 0; i < k; i++) if (sp[i] == a[i]) return 0;
    return 1;
}

int32_t s7rd_rule(int32_t n, const int16_t *la, const int16_t *lo, const uint8_t *last, const uint8_t *prev, const uint8_t *sec,
                  int32_t ng, const uint8_t *cap, const int32_t *ala, const int32_t *alo, uint32_t seed, uint8_t *out, void *work)
{
    struct s7rd_work *w = (struct s7rd_work *)work;
    uint8_t si[S7RD_MAXSEC], sp[S7RD_MAXSEC], a[S7RD_MAXSEC], fixg[S7RD_MAXSEC], left[S7RD_MAXG];
    int32_t k = 0, tot = 0;
    if (n <= 0 || n > S7RD_MAXN || ng <= 0 || ng > S7RD_MAXG) return -1;
    for (int32_t g = 0; g < ng; g++) { left[g] = cap[g]; tot += cap[g]; }
    if (tot != n) return -1;
    for (int32_t i = 0; i < n; i++) if (sec[i]) {
        if (k == S7RD_MAXSEC) return -1;
        si[k] = (uint8_t)i; sp[k] = prev[i]; k++;
    }
    if (k > ng) return -1;
    if (k) {                                                /* the second teams' draw among the allowed arrangements */
        uint32_t cnt = 0, pick;
        for (int32_t i = 0; i < k; i++) a[i] = (uint8_t)i;
        do cnt += rd_allowed(a, k, sp); while (rd_nextperm(a, k, ng));
        if (!cnt) return -1;
        pick = seed % cnt;
        for (int32_t i = 0; i < k; i++) a[i] = (uint8_t)i;
        for (;;) {
            if (rd_allowed(a, k, sp)) { if (!pick) break; pick--; }
            rd_nextperm(a, k, ng);
        }
        for (int32_t i = 0; i < k; i++) {
            fixg[i] = a[i];
            if (!left[a[i]]) return -1;
            left[a[i]]--;
        }
    }
    /* the free clubs (ident order) and the slots (groups in order, each its free places) */
    int32_t m = 0, s = 0;
    for (int32_t i = 0; i < n; i++) if (!sec[i]) w->fr[m++] = (int16_t)i;
    for (int32_t g = 0; g < ng; g++) for (int32_t j = 0; j < left[g]; j++) w->slot[s++] = (uint8_t)g;
    if (s != m) return -1;
    for (int32_t r = 0; r < m; r++) {
        int32_t i = w->fr[r];
        for (int32_t g = 0; g < ng; g++) {
            int32_t dla = la[i] - ala[g], dlo = lo[i] - alo[g];
            w->d[r][g] = (int16_t)rd_isqrt((uint32_t)(16 * dla * dla + 9 * dlo * dlo));
        }
    }
    /* Hungarian (the oracle's hungarian(): 1-based, column 0 the dummy) */
    const int32_t INF = 0x3FFFFFFF;
    for (int32_t j = 0; j <= m; j++) { w->u[j] = w->v[j] = 0; w->p[j] = w->way[j] = 0; }
    for (int32_t i = 1; i <= m; i++) {
        int32_t j0 = 0;
        w->p[0] = (int16_t)i;
        for (int32_t j = 0; j <= m; j++) { w->minv[j] = INF; w->used[j] = 0; }
        for (;;) {
            w->used[j0] = 1;
            int32_t i0 = w->p[j0], delta = INF, j1 = 0, ci = w->fr[i0 - 1];
            for (int32_t j = 1; j <= m; j++) {
                if (w->used[j]) continue;
                int32_t g = w->slot[j - 1];
                int32_t cur = w->d[i0 - 1][g] - (last[ci] == g ? S7RD_STAY : 0) - w->u[i0] - w->v[j];
                if (cur < w->minv[j]) { w->minv[j] = cur; w->way[j] = (int16_t)j0; }
                if (w->minv[j] < delta) { delta = w->minv[j]; j1 = j; }
            }
            for (int32_t j = 0; j <= m; j++) {
                if (w->used[j]) { w->u[w->p[j]] += delta; w->v[j] -= delta; }
                else w->minv[j] -= delta;
            }
            j0 = j1;
            if (!w->p[j0]) break;
        }
        while (j0) { int32_t j1 = w->way[j0]; w->p[j0] = w->p[j1]; j0 = j1; }
    }
    for (int32_t i = 0; i < k; i++) out[si[i]] = fixg[i];
    for (int32_t j = 1; j <= m; j++) out[w->fr[w->p[j] - 1]] = w->slot[j - 1];
    return 0;
}

/* the anchors: the integer mean (floor, Italy's coordinates are positive) of last season's members' travel points per group */
void s7rd_centroid(int32_t n, const int16_t *la, const int16_t *lo, const uint8_t *grp, int32_t ng, int32_t *ala, int32_t *alo)
{
    int32_t c[S7RD_MAXG];
    for (int32_t g = 0; g < ng; g++) { ala[g] = alo[g] = 0; c[g] = 0; }
    for (int32_t i = 0; i < n; i++) if (grp[i] < ng) { ala[grp[i]] += la[i]; alo[grp[i]] += lo[i]; c[grp[i]]++; }
    for (int32_t g = 0; g < ng; g++) if (c[g]) { ala[g] /= c[g]; alo[g] /= c[g]; }
}

/* s7rd_level: one level's redraw from registry idents (s7swap.c's run, through S7RD_PTR): n next-season members id[] (ident order),
   last[k] their group last season at this level (0xFF none); nl last-season members lid[] / lgrp[] (the anchors: their centroids,
   leavers included - the oracle's 'last season's groups'); use_sec: the second teams' constraint (Serie C; Serie D: none, the
   oracle's rule); seed: the draw's. The coordinates: S7GEO_XY (0 = none -> -2), each through s7rd_travel. out[k] = the new group.
   S7RD_LOG[lvl]: {status 1 ok / 2 refused, n, moved (group changed for a club with a last group), rc}. work: S7RD_LWORK bytes. */
enum { S7RD_LWORK = (S7RD_WORK + 3) / 4 * 4 + 6 * S7RD_MAXN * 2 + 2 * S7RD_MAXN };
typedef char s7rd_lwork_fits[S7RD_LWORK <= 0x2800 ? 1 : -1];   /* (s7swap.c RD_WSZ) */
uint8_t S7RD_SEC[(S7GEO_NID + 7) / 8] DATA = {0};           /* per ident: a second team (clubs.csv second_of; s7swap.py) */
struct { uint8_t status, n, moved; int8_t rc; } S7RD_LOG[2] DATA = {{0}};

int32_t s7rd_level(int32_t lvl, int32_t n, const uint16_t *id, const uint8_t *last, int32_t use_sec, int32_t nl, const uint16_t *lid,
                   const uint8_t *lgrp, int32_t ng, const uint8_t *cap, uint32_t seed, uint8_t *out, uint8_t *work)
{
    int16_t *la = (int16_t *)(work + (S7RD_WORK + 3) / 4 * 4), *lo = la + S7RD_MAXN, *pla = lo + S7RD_MAXN, *plo = pla + 2 * S7RD_MAXN;
    uint8_t *sec = (uint8_t *)(plo + 2 * S7RD_MAXN), *prv = sec + S7RD_MAXN;
    int32_t ala[S7RD_MAXG], alo[S7RD_MAXG], rc = -1;
    S7RD_LOG[lvl & 1].status = 2; S7RD_LOG[lvl & 1].n = (uint8_t)n; S7RD_LOG[lvl & 1].moved = 0;
    if (n > S7RD_MAXN || nl > 2 * S7RD_MAXN || ng > S7RD_MAXG || !S7GEO_HAVE) goto done;
    rc = -2;
    for (int32_t k = 0; k < n + nl; k++) {
        uint32_t i = k < n ? id[k] : lid[k - n];
        if (i >= S7GEO_NID || !S7GEO_XY[i][0]) goto done;
        int32_t a = S7GEO_XY[i][0], b = S7GEO_XY[i][1];
        s7rd_travel(&a, &b);
        if (k < n) { la[k] = (int16_t)a; lo[k] = (int16_t)b; } else { pla[k - n] = (int16_t)a; plo[k - n] = (int16_t)b; }
    }
    for (int32_t k = 0; k < n; k++) { sec[k] = use_sec && (S7RD_SEC[id[k] >> 3] >> (id[k] & 7) & 1); prv[k] = last[k]; }
    s7rd_centroid(nl, pla, plo, lgrp, ng, ala, alo);
    rc = s7rd_rule(n, la, lo, last, prv, sec, ng, cap, ala, alo, seed, out, work);
    if (!rc) {
        int32_t mv = 0;
        for (int32_t k = 0; k < n; k++) mv += last[k] != 0xFF && last[k] != out[k];
        S7RD_LOG[lvl & 1].status = 1; S7RD_LOG[lvl & 1].moved = (uint8_t)mv;
    }
done:
    S7RD_LOG[lvl & 1].rc = (int8_t)rc;
    return rc;
}
