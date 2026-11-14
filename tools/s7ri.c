/* S7 x ri (s7-ri-fix.md "Changes", MC 13/11: the REGISTRY is the single source of truth in S7 builds, ri's maps[] unused).
   Included by s7swap.c at the end (one translation unit: it calls s7_ident / s7_poolk / s7_home_word directly and its data
   lives in the S7SWAP band); gplay.c keeps only two GP_S7 hook pointers, set by s7swap.py to s7ri_pool / s7ri_cdstr:
   - s7ri_pool: ri_pool kind 0's whole decision. Dormant (the pointer 0) = today's maps[] path. The first order: a pool ident j
     = the identity of RS record j (s7_poolk(0x10000 | j), the one place of the rule: s7swap.pool_order). A relegated row's
     occupant (s7_ident of its CURRENT word, whatever its home: native, foreign, pool) goes to the queue tail, the head ident
     comes in; every move is logged in RI_MOVES for s7_season (out -> SR_REG_POOL, in -> placed at the row). An occupant the
     registry does not know: the club stays (like the manager), RI_S7_BAD++ (a can't-happen: the host tests assert 0 and the
     DOSBox scenario FAILs on != 0). maps[] and RI_SWAPPED are never touched.
   - s7ri_cdstr: Coppa D tie seeding by the occupant's REAL strength (cupd.strengths): a pool club by its RS index, a native of
     this file by its home row, a club of the other league file by its home row in the block cupd appends (db other file, 256
     ordinals); the floor 5 only by the rule (strength < 5). */
uint32_t s7_ident(uint32_t w);          /* (s7swap.c: the registry ident of the club at a team word, 0xFFFF none) */
uint32_t s7_poolk(uint32_t id);         /* (index among the pool idents; 0x10000 | k = the ident of RS record k; 0xFFFF none) */

#ifndef S7RI_NSTR
#define S7RI_NSTR 256                           /* (s7swap.py: -DS7RI_NSTR = the other league file's rows) */
#endif
extern uint8_t RI_FRESH;                        /* (s7swap.c: one-shot, s7_season applies RI_MOVES only when a fresh ri_season logged them) */
enum { S7RI_MV = 64 };
uint16_t S7RI_STRF DATA = 0;                    /* the OTHER league file (cupd.other_strengths), written by s7swap.py */
uint16_t S7RI_STR[S7RI_NSTR] DATA = {0};        /* the strength of each of its rows (cupd.strength's rule) */
uint16_t RI_MOVES[S7RI_MV][3] DATA = {{0}};    /* this season end's pool moves {row, out ident, in ident} */
int32_t RI_NMOVES DATA = 0;
int32_t RI_S7_BAD DATA = 0;

/* (4.2 geography, below) */
enum { S7GEO_G = 9, S7GEO_MAXSTEPS = 8, S7GEO_NL = 48 };
uint8_t S7GEO_NEIGH[S7GEO_G][S7GEO_G] DATA = {{0}};      /* per girone: its neighbours in list order, 0xFF-terminated */
uint8_t S7GEO_ON DATA = 0;                                /* the table is in the pack (0: no chain) */
uint16_t S7GEO_LOG[S7GEO_NL][2] DATA = {{0}};            /* the natives moved this season end: {club (global number), from << 8 | to} */
int32_t S7GEO_NLOG DATA = 0;
int32_t S7GEO_BAD DATA = 0;
uint16_t *RI_HINTMAP DATA = 0;                  /* ri_ida's transient input (s7-ri-fix.md, MC 13/11): the file's maps[] words, written here from the */
int32_t RI_HINTN DATA = 0;                      /* registry before ri_ida, alive only inside one pg_fix: s7_season clears them first of all (s7ri_unhint) */

/* e: ri_pool's table entry (db kind, db n, db low, dw ns, ns x {dw global, db base, db area}, n x db area, n x db RS record);
   q / qn: the pool's queue (idents) and its length; init: the pool's first order is due (ri_season's *init == 1); file: the
   team file; manager: its club's global number; og / nog: ri_pool's list of the relegated globals; out / no: the identities
   going out. Returns the number of swaps made (m), or -1: not the S7 pooled file (the caller runs its own path). */
static uint16_t s7ri_hint(uint32_t ident, int32_t file, int32_t row)
{                                               /* ri_ida's maps[] word of a club on a row: identity + 1 (identity: the file's own
                                                   record index, or 256 + the pool record k); 0 = the row's own record */
    if (ident == 0xFFFF) return 0;
    uint32_t k = s7_poolk(ident);
    if (k != 0xFFFF) return (uint16_t)(257 + k);                    /* a pool club: its RS record's areas */
    uint16_t hw = home_of((int32_t)ident);
    if (hw != 0xFFFF && (hw & 0xFF) == (uint32_t)file && (uint32_t)(hw >> 8) != (uint32_t)row) return (uint16_t)((hw >> 8) + 1);
    return 0;                                   /* a native on its own row, or a club of the other file (S7_AREA's: the crossers) */
}

void s7ri_unhint(void)                          /* the FIRST statement of s7_season: the transient words never outlive the pg_fix */
{
    for (int32_t i = 0; RI_HINTMAP && i < RI_HINTN; i++) RI_HINTMAP[i] = 0;
    RI_HINTN = 0;
}

int32_t s7ri_pool(const uint8_t *e, uint16_t *q, uint8_t *qn, int32_t init, int32_t file, const int8_t *slt, int8_t *copy,
                  int32_t manager, uint16_t *og, int32_t *nog, uint16_t *out, int32_t *no, uint16_t *map, int32_t nmap)
{
    if (file != S7_FB) return -1;                   /* (not the S7 pooled file: the world has other kind-0 pools - Spain, Germany,
                                                       the Netherlands, Portugal -: gplay.c's own maps[] path handles those) */
    int32_t n = e[1], low = e[2], ns = e[3] | e[4] << 8, m = 0;
    const uint8_t *sl = e + 5, *order = sl + 4 * ns + n;
    S7GEO_NLOG = 0;                                 /* (the geography chain's log: this season end's, ahead of the first arrival)
    RI_NMOVES = 0;                                  /* (a new season end's log: the S7 world has ONE kind-0 pool, file 144) */
    RI_FRESH = 1;                                   /* (s7_season consumes the log once: no stale moves at a career start / a second career) */
    if (init == 1) {
        for (int32_t i = 0; i < n; i++) q[i] = (uint16_t)s7_poolk(0x10000u | order[i]);
        *qn = (uint8_t)n;
    }
    for (int32_t i = 0; i < ns && i < 256 && *nog < S7RI_MV && m < *qn && *no < 64; i++) {
        const uint8_t *s = sl + 4 * i;
        int32_t g = s[0] | s[1] << 8, base = s[2];
        int32_t o = base + slt[g], nn = base + copy[g];
        if (o < low || nn <= o) continue;           /* (relegated from the lowest level) */
        if (g == manager) { copy[g] = slt[g]; continue; }
        uint32_t id = s7_ident((uint32_t)file | (uint32_t)i << 8);
        if (id == 0xFFFF || RI_NMOVES >= S7RI_MV) {  /* (never: every row has a club) the club stays, as the manager's */
            RI_S7_BAD++;
            copy[g] = slt[g];
            continue;
        }
        out[(*no)++] = (uint16_t)id;
        RI_MOVES[RI_NMOVES][0] = (uint16_t)i;
        RI_MOVES[RI_NMOVES][1] = (uint16_t)id;
        RI_MOVES[RI_NMOVES][2] = q[m++];
        RI_NMOVES++;
        og[(*nog)++] = (uint16_t)g;
        copy[g] = slt[g];                           /* (the slot stays; pg_season places its new club by area) */
    }
    /* ri_ida (right after ri_season, before pg_season) gives every club entry of the file the areas of its slot's identity from
       maps[]: in S7 builds those words are DERIVED here from the registry, for every row: the occupant's identity, and for this
       season's moves the INCOMING club's (a pool club enters its region's Serie D group). Transient: s7ri_unhint clears them. */
    if (nmap > 256) nmap = 256;
    RI_HINTMAP = map; RI_HINTN = nmap;
    for (int32_t i = 0; i < nmap; i++) map[i] = s7ri_hint(s7_ident((uint32_t)file | (uint32_t)i << 8), file, i);
    for (int32_t j = 0; j < RI_NMOVES; j++)
        if (RI_MOVES[j][0] < nmap) map[RI_MOVES[j][0]] = s7ri_hint(RI_MOVES[j][2], file, RI_MOVES[j][0]);
    return m;
}

/* the tie seeding's strength squared of the club at team word w; s = CD_DT's strength part (moff, nmap, np, 256 x dw, np x dw,
   [db other file, 256 x dw]) */
uint32_t s7ri_cdstr(uint16_t w, const uint8_t *s)
{
    int32_t moff = s[0] | s[1] << 8, nmap = s[2] | s[3] << 8, np = s[4] | s[5] << 8;
    if (moff == 0xFFFF || (w >> 8) >= nmap) return 0;      /* (not a pooled file's row: gplay.c's own rule) */
    uint32_t k = s7_poolk(s7_ident(w)), hm = s7_home_word(w) & 0xFFFF, v = 5;
    const uint8_t *p = 0;
    if (k != 0xFFFF) { if ((int32_t)k < np) p = s + 6 + 512 + 2 * k; }
    else if ((hm & 0xFF) == (w & 0xFFu)) { if ((hm >> 8) < 256) p = s + 6 + 2 * (hm >> 8); }
    else if ((hm & 0xFF) == S7RI_STRF && (hm >> 8) < S7RI_NSTR) v = S7RI_STR[hm >> 8];
    if (p) v = p[0] | p[1] << 8;
    if (v < 5) v = 5;
    return v * v;
}

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

int32_t s7ri_geochain(const uint8_t *c, int32_t rs, int32_t nc, int32_t fl, int32_t a, int32_t cnt, const uint8_t *sz, uint8_t *occ,
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
