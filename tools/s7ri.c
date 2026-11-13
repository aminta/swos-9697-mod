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

enum { S7RI_MV = 64 };
uint16_t RI_MOVES[S7RI_MV][3] DATA = {{0}};    /* this season end's pool moves {row, out ident, in ident} */
int32_t RI_NMOVES DATA = 0;
int32_t RI_S7_BAD DATA = 0;

/* e: ri_pool's table entry (db kind, db n, db low, dw ns, ns x {dw global, db base, db area}, n x db area, n x db RS record);
   q / qn: the pool's queue (idents) and its length; init: the pool's first order is due (ri_season's *init == 1); file: the
   team file; manager: its club's global number; og / nog: ri_pool's list of the relegated globals; out / no: the identities
   going out. Returns the number of swaps made (m). */
int32_t s7ri_pool(const uint8_t *e, uint16_t *q, uint8_t *qn, int32_t init, int32_t file, const int8_t *slt, int8_t *copy,
                  int32_t manager, uint16_t *og, int32_t *nog, uint16_t *out, int32_t *no)
{
    int32_t n = e[1], low = e[2], ns = e[3] | e[4] << 8, m = 0;
    const uint8_t *sl = e + 5, *order = sl + 4 * ns + n;
    RI_NMOVES = 0;                                  /* (a new season end's log: the S7 world has ONE kind-0 pool, file 144) */
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
    return m;
}

/* the tie seeding's strength squared of the club at team word w; s = CD_DT's strength part (moff, nmap, np, 256 x dw, np x dw,
   [db other file, 256 x dw]) */
uint32_t s7ri_cdstr(uint16_t w, const uint8_t *s)
{
    int32_t moff = s[0] | s[1] << 8, nmap = s[2] | s[3] << 8, np = s[4] | s[5] << 8;
    if (moff == 0xFFFF || (w >> 8) >= nmap) return 0;      /* (not a pooled file's row: gplay.c's own rule) */
    uint32_t k = s7_poolk(s7_ident(w)), hm = s7_home_word(w) & 0xFFFF, v = 5;
    const uint8_t *p = 0, *o = s + 6 + 512 + 2 * np;
    if (k != 0xFFFF) { if ((int32_t)k < np) p = o - 2 * np + 2 * k; }
    else if ((hm & 0xFF) == (w & 0xFFu)) { if ((hm >> 8) < 256) p = s + 6 + 2 * (hm >> 8); }
    else if ((hm & 0xFF) == (uint32_t)(o[0] | o[1] << 8) && (hm >> 8) < 256) p = o + 2 + 2 * (hm >> 8);
    if (p) v = p[0] | p[1] << 8;
    if (v < 5) v = 5;
    return v * v;
}
