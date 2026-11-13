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
   s7_load (piece 3, the load apply): ri_load (ripool.py, LoadTeamFile after TEAM.nnn is read, through S7_LPTR) passes
   the team buffer and the file read. In a career whose registry is this build's (sreg_get), for the two league files:
   every row gets the record of the club the registry puts there - its ident's home record (S7_HRUN: its file and
   ordinal as shipped, = the spec's first registry) from the two files AS READ (S7_ORIG, swe.c .bss, read once per DOS
   session through the engine's file layer; MC 13/11: every load compares the file read with its ORIG's FNV-1a and reads
   both again on a difference - never a stale ORIG; still different, or a failed read: nothing applied, S7_LD.status
   LD_FILE / LD_READ, retried at the next load), all but the row's own bytes (file, ordinal, global number, 23, the
   division byte 25: ri_copy's rule). A file that cannot be read or does not match the shipped count: nothing applied,
   S7_LD says why. The career club's own crossing: walk() (option B, MC 13/11). */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_reg.c"            /* (its own copy: sreg.c's band has no room for sr_reg_season) */
#include "swce/sr_regsave.c"         /* (sr_wmap_build, for piece 4) */

#include "swefile.h"                /* (prototypes: swefile.c is linked at obj4+SWEFILE_AT) */
#include "sreg_walk.c"               /* (the walker core: its one copy in the exe, here) */

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

/* the idents' home team words as shipped, as runs (s7swap.py: <= 8): idents [first, first + n) are file's ordinals
   [ord, ord + n); an ident in no run has none */
struct { uint16_t first, n; uint8_t file, ord, pad[2]; } S7_HRUN[8] DATA = {{0}};
static uint16_t home_of(int32_t id)
{
    for (int32_t k = 0; k < 8; k++)
        if (S7_HRUN[k].n && id >= S7_HRUN[k].first && id < S7_HRUN[k].first + S7_HRUN[k].n)
            return (uint16_t)(S7_HRUN[k].file | (S7_HRUN[k].ord + id - S7_HRUN[k].first) << 8);
    return 0xFFFF;
}
char S7_NAME[2][16] DATA = {{0}};       /* the two files' names (DATA\\TMW5.102 ...) */
uint32_t S7_OAT[2] DATA = {0};          /* their ORIG buffers' offsets in S7_ORIG */
uint16_t S7_ONREC[2] DATA = {0};        /* their records as shipped */
uint32_t S7_FNV[2] DATA = {0};          /* their FNV-1a as read into S7_ORIG (orig_read); every load checks it */
extern uint8_t S7_ORIG[];               /* swe.c .bss (swreg.S7_ORIG_SZ) */

/* the load apply's result (harness: S7_LD): status, both files read (1) / failed (2) / not yet (0), rows given another
   record by the last call, calls */
enum { LD_OK = 1, LD_NOREG = 2, LD_READ = 3, LD_SIZE = 4, LD_FILE = 5 };   /* (LD_FILE: the file read is not the
                                           one on disk even after a fresh ORIG read: nothing applied) */
struct { uint8_t status, oread, file, pad; uint16_t moved, rows; uint32_t calls; int32_t rc; } S7_LD DATA = {0};
#ifdef S7_LDFAIL
uint32_t S7_LDFAILN DATA = S7_LDFAIL;    /* (S7_LDFAIL test builds: that call's ORIG read fails once - MC 13/11) */
#endif

/* piece 4: the saved words after the swaps. WSITES = wsites.py's rows (Panchina's, sreg_walk.h), S7_WRES the bytes
   each row's item resolves to (s7swap.py late(): careerFileBuffer's fixed part, an engine item; 0 = the team cache,
   resolved here per record): S7_WRES in the arena (WR_AT), resolved from trailer's EN_ITEMS at each season end. Every row is checked BEFORE the registry changes (a bad row = the season refused:
   S7_WSITE, S7_WLOG.row; an item this build does not save: the same). The team cache's records follow their clubs (n7-s7-clubmap §3.3): a cached record whose word
   moved gets the new row's own bytes - word 0..1, global 2..3 (LE, in memory), league 25 (base + next delta) - and keeps
   the rest (its players, 4, 23); WSITES' WI_CACHE rows never cover those bytes (wsites.py asserts). */
sreg_wsite WSITES[WS_MAX] DATA = {{0}};
sreg_rekey WS_KEYS[1] DATA = {0};
struct s7wres { uint32_t ptr, len; };   /* (S7_WRES: the arena's WR_AT, resolved at each season end - MC 13/11) */
extern const uint32_t S7_ENI[];         /* trailer's EN_ITEMS: per engine item {ptr, size, id | flags << 16} */
uint32_t S7_ENN DATA = 0;               /* their count (s7swap.py) */
extern uint8_t S7_CFB[];                /* careerFileBuffer (obj2: the .CAR fixed part) */
uint32_t S7_CFBLEN DATA = 0;            /* its fixed part's bytes (trailer FIXED) */
extern uint16_t S7_NUMSEL;              /* trailer: the cache's records (obj2) */
extern uint8_t *S7_SELBASE;             /* trailer SELBASEV: -> the cache's first record (obj1 dword) */
struct { int16_t row, rc; uint16_t changed, cache, npair, rows; } S7_WLOG DATA = {0};
extern uint16_t S7_SELTEAM;             /* selTeamNumber (obj2: the career club's word) */
extern uint16_t S7_CTLEAGUE;            /* careerTeamLeague (obj2: its base division, record +25 at selection) */
extern uint8_t S7_CTEAM[];              /* careerTeam (obj2: the career club's record copy) */
struct { uint16_t old, neww; int16_t league, pad; } S7_CLOG DATA = {0};   /* the career club's crossing (harness) */

/* the result (harness: S7_LOG) */
enum { S7_OK = 1, S7_NOREG = 2, S7_STALE = 3, S7_BAD = 4, S7_COUNT = 5, S7_PLACE = 6, S7_REG = 7, S7_NOCLUB = 8,
       S7_WSITE = 9, S7_WMAP = 10, S7_SKIP = 11 };
struct { uint8_t status, season, nswap, ncross; int32_t rc; } S7_LOG DATA = {0};   /* (the swaps: the arena's SW_AT) */

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
/* the work area: the engine arena after the registry (swe.c SWE_ARENA; asserted below) - sr_reg_work,
   then nd[SR_REG_CLUBS], then order[48], then the swaps; no .bss of s7swap.c's own (swe.c's is the arena) */
#define W_AT ((sizeof(sr_registry) + 15) & ~15u)
#define ND_AT ((W_AT + sizeof(sr_reg_work) + 15) & ~15u)
#define ORD_AT (ND_AT + SR_REG_CLUBS)
#define SW_AT ((ORD_AT + 2 * 48 + 15) & ~15u)     /* sr_reg_swap[S7_NSW]: the last season's swaps (piece 4's wmap) */
#define S7_NSW 32
#define PR_AT ((SW_AT + S7_NSW * sizeof(sr_reg_swap) + 15) & ~15u)   /* the word map: sr_wpair[S7_NPR] */
#define S7_NPR 128
#define WR_AT ((PR_AT + S7_NPR * sizeof(sr_wpair) + 15) & ~15u)   /* S7_WRES[WS_MAX] */
#ifndef SWE_ARENA
#define SWE_ARENA 0x8000
#endif
typedef char s7_work_fits_the_arena[WR_AT + WS_MAX * 8 <= SWE_ARENA ? 1 : -1];
#define S7_WRES ((struct s7wres *)(SWE_ARENA_AT + WR_AT))

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

static int32_t wcheck(void)            /* S7_WRES resolved; -1 every row resolvable and in its bytes, else the first bad row */
{
    for (int32_t k = 0; k < WS_MAX && WSITES[k].item != WS_END; k++) {
        const sreg_wsite *s = &WSITES[k];
        S7_WRES[k].ptr = S7_WRES[k].len = 0;
        if (s->item == WI_CFB) { S7_WRES[k].ptr = (uint32_t)S7_CFB; S7_WRES[k].len = S7_CFBLEN; }
        else if (s->item != WI_CACHE)
            for (uint32_t e = 0; e < S7_ENN; e++)
                if ((S7_ENI[3 * e + 2] & 0xFFFF) == s->item) { S7_WRES[k].ptr = S7_ENI[3 * e]; S7_WRES[k].len = S7_ENI[3 * e + 1]; }
        uint32_t len = s->item == WI_CACHE ? 684 : S7_WRES[k].len;
        if (s->form != WS_W && s->form != WS_G) return k;
        if (s->item != WI_CACHE && !S7_WRES[k].ptr) return k;
        if (s->count && (s->off + (uint32_t)(s->count - 1) * s->stride + 2 > len || (s->count > 1 && s->stride < 2)))
            return k;
    }
    return -1;
}

/* a record in memory (the cache, careerTeam) at its new row w: its own bytes as the game's loader leaves them -
   word 0..1, global 2..3 (LE: SetTeamGlobalNumbers' in-memory form; a team FILE holds it BE), league 25 = the row's
   base division + next season's delta (SetLeagueNumbers' rule, slt = leaguesTableCopy after the re-base). Returns the
   row's base division (careerTeamLeague's form), -1 when w is not a row of the two files. */
static int32_t put_slot(uint8_t *r, uint16_t w, const sreg_gfile *g, int32_t ng, const int8_t *slt)
{
    int32_t j = gindex(g, ng, w & 0xFF, w >> 8), fi = fi_of(w & 0xFF), b = fi >= 0 ? base_local(fi, w >> 8) : -1;
    if (j < 0 || b < 0) return -1;
    uint16_t gl = (uint16_t)(g[j].base + (w >> 8) - g[j].ord0);
    r[0] = (uint8_t)w; r[1] = (uint8_t)(w >> 8); r[2] = (uint8_t)gl; r[3] = (uint8_t)(gl >> 8);
    r[25] = (uint8_t)(b + slt[gl]);
    return b;
}

static int32_t walk(int32_t nsw, const int8_t *slt)
{
    sr_wpair *m = (sr_wpair *)(SWE_ARENA_AT + PR_AT);
    int32_t n = sr_wmap_build((const sr_reg_swap *)(SWE_ARENA_AT + SW_AT), nsw, m, S7_NPR);
    S7_WLOG.npair = (uint16_t)(n < 0 ? 0 : n);
    if (n < 0) { S7_WLOG.rc = (int16_t)n; return -1; }
    sreg_gfile g[4];
    int32_t ng = 0;
    for (int32_t s = 0; s < 2; s++) {
        int32_t fi = fi_of(s ? S7_FB : S7_FA);
        uint32_t rows = SREG_REG->rows[fi], split = S7_GB[s][1];
        g[ng].file = s ? S7_FB : S7_FA; g[ng].base = S7_GB[s][0]; g[ng].ord0 = 0;
        g[ng++].rows = (uint8_t)(split ? split : rows);
        if (split) { g[ng].file = s ? S7_FB : S7_FA; g[ng].base = S7_GB[s][2]; g[ng].ord0 = (uint8_t)split;
                     g[ng++].rows = (uint8_t)(rows - split); }
    }
    uint32_t changed = 0, cache = 0, nsel = S7_NUMSEL;
    for (int32_t k = 0; k < WS_MAX && WSITES[k].item != WS_END; k++) {
        const sreg_wsite *s = &WSITES[k];
        if (s->item == WI_CACHE) {
            for (uint32_t i = 0; i < nsel; i++) {
                int32_t c = sreg_walk_site(s, S7_SELBASE + 684 * i, 684, m, n, g, ng);
                if (c > 0) changed += c;
            }
        } else {
            int32_t c = sreg_walk_site(s, (uint8_t *)S7_WRES[k].ptr, (int32_t)S7_WRES[k].len, m, n, g, ng);
            if (c > 0) changed += c;
        }
        S7_WLOG.rows = (uint16_t)(k + 1);
    }
    for (uint32_t i = 0; i < nsel; i++) {          /* the cache's records follow their clubs */
        uint8_t *r = S7_SELBASE + 684 * i;
        uint16_t w = (uint16_t)(r[0] | r[1] << 8), nw = sr_wmap_get(m, n, w);
        if (nw != w && nw != SR_REG_NONE && put_slot(r, nw, g, ng, slt) >= 0) cache++;
    }
    /* the career club (MC 13/11, option B: a crossing is not a job change - squad, funds, job count kept): the words
       cseg_5DB56 would set, nothing else; InitializeNewSeason (after pg_fix: our caller) then takes its league from
       selTeamNumber's file (competitionsTable[file] -> D8CAA) and D6CDC = careerTeamLeague + slt[careerTeam global] */
    uint16_t cw = S7_SELTEAM, cn = sr_wmap_get(m, n, cw);
    S7_CLOG.old = cw; S7_CLOG.neww = 0; S7_CLOG.league = -1;
    if (cn != cw && cn != SR_REG_NONE) {
        int32_t b = put_slot(S7_CTEAM, cn, g, ng, slt);
        if (b >= 0) { S7_SELTEAM = cn; S7_CTLEAGUE = (uint16_t)b; S7_CLOG.neww = cn; S7_CLOG.league = (int16_t)b; }
    }
    S7_WLOG.changed = (uint16_t)changed; S7_WLOG.cache = (uint16_t)cache;
    return 0;
}

static int32_t run(void *pv) {
    int8_t *slt = ((struct args *)pv)->sltcopy;
    uint8_t *nd = SWE_ARENA_AT + ND_AT;
    uint16_t *order = (uint16_t *)(SWE_ARENA_AT + ORD_AT);
    sr_registry *R = SREG_REG;
    S7_LOG.nswap = S7_LOG.ncross = 0; S7_LOG.rc = 0;
#ifdef S7_NOSWAP
    return S7_LOG.status = S7_SKIP;     /* (S7_NOSWAP test builds: no swap at all - world_s7cross_diff's control) */
#endif
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
    S7_WLOG.row = (int16_t)wcheck(); S7_WLOG.rc = 0; S7_WLOG.changed = S7_WLOG.cache = S7_WLOG.npair = S7_WLOG.rows = 0;
    if (S7_WLOG.row >= 0) return S7_LOG.status = S7_WSITE;     /* (before the registry changes: nothing done) */
    sr_reg_work *w = (sr_reg_work *)(SWE_ARENA_AT + W_AT);
    int32_t c = sr_reg_season(R, nd, order, no, 0, w, (sr_reg_swap *)(SWE_ARENA_AT + SW_AT), S7_NSW);
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
    if (walk(c, slt) < 0) return S7_LOG.status = S7_WMAP;      /* (cannot happen: <= S7_NSW swaps, S7_NPR pairs) */
    return S7_LOG.status = S7_OK;
}

static int32_t be16(const uint8_t *b) { return b[0] << 8 | b[1]; }

static uint32_t s7_fnv(const uint8_t *b, uint32_t n)
{
    uint32_t h = 2166136261u;
    for (uint32_t i = 0; i < n; i++) h = (h ^ b[i]) * 16777619u;
    return h;
}

static int32_t orig_read(void)         /* both files as read into S7_ORIG: 1, else 2 (S7_LD.rc: which, why) */
{
    for (int32_t s = 0; s < 2; s++) {
        uint8_t *o = S7_ORIG + S7_OAT[s];
        uint32_t want = 2 + 684u * S7_ONREC[s];
        int h = swe_fopen_r(S7_NAME[s]);
        if (h < 0) { S7_LD.rc = (s + 1) << 16 | (h & 0xFFFF); return 2; }
        int r = swe_fread(h, o, want + 1);           /* (one more: a longer file is refused) */
        swe_fclose(h);
        if (r != (int)want || be16(o) != S7_ONREC[s]) { S7_LD.rc = (s + 1) << 16 | 0x8000 | (r & 0x7FFF); return 2; }
        S7_FNV[s] = s7_fnv(o, want);
    }
    return 1;
}

static void rec_copy(uint8_t *d, const uint8_t *s)   /* gplay.c ri_copy's rule: all but the row's own bytes */
{
    for (int32_t b = 0; b < 684; b++)
        if (b > 4 && b != 23 && b != 25) d[b] = s[b];
}

struct largs { uint8_t *buf; uint32_t file; };

static int32_t load_run(void *pv)
{
    uint8_t *buf = ((struct largs *)pv)->buf;
    uint32_t file = ((struct largs *)pv)->file & 0xFF;
    int32_t s = file == S7_FA ? 0 : file == S7_FB ? 1 : -1;
    if (s < 0) return 0;
    S7_LD.calls++; S7_LD.file = (uint8_t)file; S7_LD.moved = S7_LD.rows = 0;
    if (!sreg_get()) return S7_LD.status = LD_NOREG;
    if (be16(buf) != S7_ONREC[s]) return S7_LD.status = LD_SIZE;
    uint32_t h = s7_fnv(buf, 2 + 684u * S7_ONREC[s]);
    if (S7_LD.oread == 1 && h != S7_FNV[s]) S7_LD.oread = 0;   /* (the file changed since ORIG was read: read again) */
#ifdef S7_LDFAIL
    if (S7_LD.calls == S7_LDFAILN) { S7_LD.oread = 2; S7_LD.rc = -0x5F; return S7_LD.status = LD_READ; }
#endif
    if (S7_LD.oread != 1) S7_LD.oread = (uint8_t)orig_read();
    if (S7_LD.oread != 1) return S7_LD.status = LD_READ;
    if (h != S7_FNV[s]) return S7_LD.status = LD_FILE;         /* (read again, still not the file LoadTeamFile read) */
    const sr_registry *R = SREG_REG;
    int32_t fi = fi_of((uint8_t)file), n = be16(buf);
    if (fi < 0 || n != S7_ONREC[s] || R->rows[fi] > n) return S7_LD.status = LD_SIZE;
    uint32_t moved = 0;
    for (uint32_t o = 0; o < R->rows[fi]; o++) {
        int32_t id = R->at[fi][o];
        if (id < 0 || id >= R->nclub) continue;
        uint16_t h = home_of(id);
        int32_t hs = (h & 0xFF) == S7_FA ? 0 : (h & 0xFF) == S7_FB ? 1 : -1;
        if (hs < 0 || (h >> 8) >= S7_ONREC[hs]) continue;
        if (hs == s && (h >> 8) == o) continue;      /* (its own row: the record as read) */
        rec_copy(buf + 2 + 684 * o, S7_ORIG + S7_OAT[hs] + 2 + 684 * (h >> 8));
        moved++;
    }
    S7_LD.moved = (uint16_t)moved; S7_LD.rows = R->rows[fi];
    return S7_LD.status = LD_OK;
}

void s7_load(uint8_t *buf, uint32_t file)    /* ri_load (S7_LPTR): cdecl, the game's stack -> the engine's C stack */
{
    struct largs a;
    a.buf = buf; a.file = file;
    cstack_call(load_run, &a);
}

int32_t s7_season(int8_t *sltcopy)     /* pg_fix: cdecl, the game's stack -> the engine's C stack */
{
    struct args a;
    a.sltcopy = sltcopy;
    return cstack_call(run, &a);
}
