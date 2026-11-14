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

/* 4.2 Serie D geography (MC 14/11, backlog 'Serie D pool arrivals placed geographically'): a pool arrival whose own girone is full
   takes it anyway, through a CHAIN of one-step moves along the pack's neighbour table (S7GEO_NEIGH, ita pack data 'geo': per
   girone its neighbours in list order) to the nearest girone with a seat (breadth first, ties in list order). Each step moves
   one STAYER of the girone it leaves (never the manager's club, never an arrival of this season end, never a club that already
   moved: only copy == slt qualifies, so a club moves at most once) into the next girone. At most S7GEO_MAXSTEPS steps; any step
   without a mover, or a longer chain: no chain (S7GEO_BAD++, today's fallbacks). Called by gplay.c's pg_one (GP_GEOCH). */

static int geo_mover(const uint8_t *c, int rs, int nc, int fl, int x, const int8_t *slt, const int8_t *copy, const uint8_t *pend,
                     int npend, const uint16_t *og, int nog, int mgr)
{
    for (int i = 0; i < nc; i++) {                         /* (the table's order = the rows' order: the lowest row first) */
        const uint8_t *e = c + rs * i;
        int h = e[0] | e[1] << 8, hb = e[2], skip = 0;
        if (h >= npend || (pend[h >> 3] >> (h & 7) & 1) || copy[h] + hb != fl + x || copy[h] != slt[h] || h == mgr) continue;
        for (int k = 0; k < nog; k++) if (og[k] == h) skip = 1;
        if (!skip) return i;
    }
    return -1;
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
        mv[s] = geo_mover(c, rs, nc, fl, path[s + 1], slt, copy, pend, npend, og, nog, mgr);
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
