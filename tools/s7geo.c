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

/* 42-s7trap (MC 16/11): the redraw's own distance, for the old-save import's pending clubs (sreg_import.c). The three helpers below
   are 42-redrawc's s7rd_travel / s7rd_centroid / rd_isqrt VERBATIM (the redraw is not in 42-int yet: the merge keeps one copy), plus
   s7rd_near, the import's one call: the group, among those with room, whose anchor is nearest to a club's travel point by the redraw's
   distance isqrt(16 dlat^2 + 9 dlon^2) (42-redrawc's w->d[][]); ties the lower group. */
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

/* the anchors: the integer mean (floor, Italy's coordinates are positive) of last season's members' travel points per group */
void s7rd_centroid(int32_t n, const int16_t *la, const int16_t *lo, const uint8_t *grp, int32_t ng, int32_t *ala, int32_t *alo)
{
    int32_t c[9];
    for (int32_t g = 0; g < ng; g++) { ala[g] = alo[g] = 0; c[g] = 0; }
    for (int32_t i = 0; i < n; i++) if (grp[i] < ng) { ala[grp[i]] += la[i]; alo[grp[i]] += lo[i]; c[grp[i]]++; }
    for (int32_t g = 0; g < ng; g++) if (c[g]) { ala[g] /= c[g]; alo[g] /= c[g]; }
}

/* The old-save import's pick: among the groups in the bitmask room (bit k = group k, div[k] its division byte, ng <= 9), the one whose
   anchor - the mean of the travel points of the clubs c < n with nd[c] == div[k] (the import holds its pending clubs at 0xFF meanwhile) that
   have a town - is nearest to club cw's travel point by the redraw's distance; ties the lower group; the club without a town, or no group
   in room with a member: the lowest group in room (room != 0). word[c] = club c's team word (its registry row). */
int32_t s7rd_near(int32_t n, const uint16_t *word, const uint8_t *nd, const uint8_t *div, int32_t ng, uint32_t room, int32_t cw)
{
    int16_t ta[168], to[168], a16, b16;
    uint8_t gr[168];
    int32_t ala[9], alo[9], a, b, m = 0, best = -1, bd = 0;
    if (ng > 9) return -1;
    if (!s7geo_ll((uint32_t)cw, &a16, &b16)) return __builtin_ctz(room);
    for (int32_t c = 0, k; c < n && m < 168; c++) {
        for (k = 0; k < ng && div[k] != nd[c]; k++) {}
        if (k == ng || !s7geo_ll(word[c], &ta[m], &to[m])) continue;
        a = ta[m]; b = to[m]; s7rd_travel(&a, &b);
        ta[m] = (int16_t)a; to[m] = (int16_t)b; gr[m++] = (uint8_t)k;
    }
    s7rd_centroid(m, ta, to, gr, ng, ala, alo);
    a = a16; b = b16; s7rd_travel(&a, &b);
    for (int32_t g = 0; g < ng; g++) {
        if (!(room >> g & 1) || !ala[g]) continue;
        int32_t da = a - ala[g], db = b - alo[g];
        da = rd_isqrt((uint32_t)(16 * da * da + 9 * db * db));
        if (best < 0 || da < bd) { best = g; bd = da; }
    }
    return best >= 0 ? best : __builtin_ctz(room);
}
