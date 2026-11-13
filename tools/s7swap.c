/* S7 season-end swap builder (Shaved 13/11, internal/handoff/s7-swap-plan.md piece 2; MC's Q1-Q4 the same day):
   the crossings between the two league structs of a shaped league (Italy: file 102 Serie A..C, file 144 Serie D) as
   swaps of the N7 club registry (sreg.c's REG), at obj4+swreg.S7SWAP_AT, linked only with a shaped pack (GP_S7).

   Called from pg_fix (pgroups.py, through its S7_PTR) after pg_season and the reserve / Coppa D steps, before the
   balance byte and InitializeNewSeason's copy-back: leaguesTableCopy (SLTCOPY) holds next season's deltas per global
   number (division = the slot record's +25, the file's local division, + delta), every in-struct move already in it.
   - The crossings: gplay.c's snapshots S7X[0] (the upper struct, file S7_FA: its clubs down) and S7X[1] (the lower,
     S7_FB: up), this season's both, neither bad; |down| == |up| (each is its declared direct counts + its play-out
     entries: gplay.c s7_snap). Otherwise the season is REFUSED: nothing crosses (B1: no club leaves its struct
     natively), S7_LOG.status says why - never a guess.
   - Destinations (MC Q3): every group keeps its size. A club going down takes a place freed in the lower level by a
     club going up, and the reverse; the group: its clubs.csv area for that level (S7_AREA: low nibble the upper
     level's group, high nibble the lower level's, 0xF none), else the nearest group with a free place (index
     distance, the lower index first). Order: S7X's (direct crossings first, best placed first; then play-out ones).
   - nd[ident]: every registry club's next division - its row's division + its delta (a crosser: its destination);
     sr_reg_season (contiguous 0: a club staying in its file keeps its row; the rows freed in a file go to the clubs
     coming in, by rank = S7X order) gives the swaps; then every row's delta in SLTCOPY is its new division (the
     registry's rdiv, local to its file) - the slot's base (+25 as shipped: the spec's range of that row).
   Not here yet: the records themselves (piece 3, the load apply) and the saved words (piece 4, the WSITES walker). */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_reg.c"            /* (its own copy: sreg.c's band has no room for sr_reg_season) */
#include "swce/sr_regsave.c"         /* (sr_wmap_build, for piece 4) */

#define DATA __attribute__((section(".data")))
#ifndef S7_NID
#define S7_NID 320                       /* (the shape's idents: s7swap.py asserts SREG_NCLUB <= it) */
#endif

struct s7x { uint16_t file; uint8_t n, bad, season, pad[3];
             struct { uint16_t glob, team; uint8_t kind, dir, div, rank; } e[24]; };   /* (gplay.c's) */
extern struct s7x S7X[2];               /* obj2 (gplay.c .bss) */
extern sr_registry *SREG_REG;           /* sreg.c: -> the engine arena */
extern uint8_t SWE_ARENA_AT[];          /* swe.c: the registry at its start, the work area after it */
int32_t sreg_get(void);                 /* sreg.c: 1 = REG holds this career's registry (built from the spec if needed) */
int32_t cstack_call(int32_t (*fn)(void *), void *arg);

/* s7swap.py fills these */
uint8_t S7_FA DATA = 0, S7_FB DATA = 0; /* the upper / lower struct's team file */
uint8_t S7_NUP DATA = 0, S7_NLO DATA = 0;   /* groups of the boundary levels: the upper's last, the lower's first */
uint8_t S7_UP[16] DATA = {0};           /* their league divisions, group order (A, B, ...) */
uint8_t S7_LO[16] DATA = {0};
uint16_t S7_GB[2][3] DATA = {{0}};      /* per file (FA, FB): global base, the ordinal its second run starts at (0 none),
                                           that run's global base (G144: rows 156.. at 2283..) */
uint8_t S7_AREA[S7_NID] DATA = {0};   /* per ident: low nibble the upper level's group, high the lower's (F none) */

/* the result (harness: S7_LOG) */
enum { S7_OK = 1, S7_NOREG = 2, S7_STALE = 3, S7_BAD = 4, S7_COUNT = 5, S7_PLACE = 6, S7_REG = 7, S7_NOCLUB = 8 };
struct { uint8_t status, season, nswap, ncross; int32_t rc; sr_reg_swap sw[32]; } S7_LOG DATA = {0};

static int32_t fi_of(uint8_t file) {
    for (int32_t i = 0; i < SREG_REG->nfiles; i++) if (SREG_REG->f[i].file == file) return i;
    return -1;
}
static uint32_t glob_of(int32_t s, uint32_t ord) {     /* s: 0 = FA, 1 = FB */
    return S7_GB[s][1] && ord >= S7_GB[s][1] ? S7_GB[s][2] + ord - S7_GB[s][1] : S7_GB[s][0] + ord;
}
static int32_t base_local(int32_t fi, uint32_t ord) {  /* the row's division as shipped (its spec range), local */
    const sr_reg_file *f = &SREG_REG->f[fi];
    uint32_t r = 0;
    for (int32_t k = 0; k < f->ndiv; k++) {
        r += f->size[k];
        if (ord < r) return k;
    }
    return -1;                                         /* (a pool row: not the league's) */
}

struct args { int8_t *sltcopy; };
/* the work area: the engine arena after the registry (swe.c SWE_ARENA; s7swap.py asserts the sum fits) - sr_reg_work,
   then nd[SR_REG_CLUBS], then order[48]; no .bss of s7swap.c's own (swe.c's is the arena) */
#define W_AT ((sr_reg_size() + 15) & ~15u)
#define ND_AT ((W_AT + sr_reg_work_size() + 15) & ~15u)
#define ORD_AT (ND_AT + SR_REG_CLUBS)

/* the group of the level (n groups, free[] places) for an area nibble a: a, else the nearest with room */
static int32_t place(uint8_t *free, int32_t n, int32_t a) {
    if (a < n && free[a]) return a;
    for (int32_t d = 1; d < n; d++) {
        if (a - d >= 0 && a - d < n && free[a - d]) return a - d;
        if (a + d < n && free[a + d]) return a + d;
    }
    if (a >= n) for (int32_t g = 0; g < n; g++) if (free[g]) return g;
    return -1;
}

static int32_t run(void *pv) {
    int8_t *slt = ((struct args *)pv)->sltcopy;
    uint8_t *nd = SWE_ARENA_AT + ND_AT;
    uint16_t *order = (uint16_t *)(SWE_ARENA_AT + ORD_AT);
    sr_registry *R = SREG_REG;
    S7_LOG.nswap = S7_LOG.ncross = 0; S7_LOG.rc = 0;
    if (!sreg_get()) return S7_LOG.status = S7_NOREG;
    const struct s7x *A = &S7X[0], *B = &S7X[1];
    S7_LOG.season = A->season;
    if (A->file != S7_FA || B->file != S7_FB || !A->season || A->season != B->season) return S7_LOG.status = S7_STALE;
    if (A->bad || B->bad) return S7_LOG.status = S7_BAD;
    if (A->n != B->n || A->n > 24) return S7_LOG.status = S7_COUNT;
    int32_t fa = fi_of(S7_FA), fb = fi_of(S7_FB);
    if (fa < 0 || fb < 0) return S7_LOG.status = S7_NOREG;
    /* nd: every club's division after this season's in-struct moves */
    for (int32_t i = 0; i < R->nclub; i++) nd[i] = (uint8_t)sr_reg_div(R, i);
    for (int32_t s = 0; s < 2; s++) {
        int32_t fi = s ? fb : fa;
        for (uint32_t o = 0; o < R->rows[fi]; o++) {
            int32_t b = base_local(fi, o), id = R->at[fi][o];
            if (b < 0 || id >= R->nclub) continue;
            int32_t loc = b + slt[glob_of(s, o)];
            if (loc < 0 || loc >= R->f[fi].ndiv) return S7_LOG.status = S7_PLACE;
            nd[id] = R->f[fi].div[loc];
        }
    }
    /* the free places: per group of each boundary level, one per crosser leaving it */
    uint8_t fup[16], flo[16];
    for (int32_t g = 0; g < 16; g++) fup[g] = flo[g] = 0;
    for (int32_t s = 0; s < 2; s++) {
        const struct s7x *x = s ? B : A;
        for (int32_t k = 0; k < x->n; k++) {
            int32_t id = sr_reg_ident(R, x->e[k].team);
            if (id < 0) return S7_LOG.status = S7_NOCLUB;
            int32_t g = -1, n = s ? S7_NLO : S7_NUP;
            const uint8_t *lv = s ? S7_LO : S7_UP;
            for (int32_t q = 0; q < n; q++) if (lv[q] == nd[id]) g = q;
            if (g < 0) return S7_LOG.status = S7_PLACE;   /* (a crosser not on its boundary level) */
            if (s) flo[g]++; else fup[g]++;
        }
    }
    /* destinations: down into the lower level's freed places, up into the upper's */
    int32_t no = 0;
    for (int32_t s = 0; s < 2; s++) {
        const struct s7x *x = s ? B : A;
        for (int32_t k = 0; k < x->n; k++) {
            int32_t id = sr_reg_ident(R, x->e[k].team);
            uint8_t a = S7_AREA[id];
            int32_t g = s ? place(fup, S7_NUP, a & 0xF) : place(flo, S7_NLO, a >> 4);
            if (g < 0) return S7_LOG.status = S7_PLACE;
            if (s) { fup[g]--; nd[id] = S7_UP[g]; } else { flo[g]--; nd[id] = S7_LO[g]; }
            order[no++] = (uint16_t)id;
        }
    }
    S7_LOG.ncross = (uint8_t)no;
    sr_reg_work *w = (sr_reg_work *)(SWE_ARENA_AT + W_AT);
    int32_t c = sr_reg_season(R, nd, order, no, 0, w, S7_LOG.sw, 32);
    S7_LOG.rc = c;
    if (c < 0) return S7_LOG.status = S7_REG;
    S7_LOG.nswap = (uint8_t)c;
    /* next season's deltas: every row's division (rdiv, the league's) as its file's local, minus the slot's base */
    for (int32_t s = 0; s < 2; s++) {
        int32_t fi = s ? fb : fa;
        for (uint32_t o = 0; o < R->rows[fi]; o++) {
            int32_t b = base_local(fi, o);
            if (b < 0) continue;
            for (int32_t k = 0; k < R->f[fi].ndiv; k++)
                if (R->f[fi].div[k] == R->rdiv[fi][o]) slt[glob_of(s, o)] = (int8_t)(k - b);
        }
    }
    return S7_LOG.status = S7_OK;
}

int32_t s7_season(int8_t *sltcopy)     /* pg_fix: cdecl, the game's stack -> the engine's C stack */
{
    struct args a;
    a.sltcopy = sltcopy;
    return cstack_call(run, &a);
}
