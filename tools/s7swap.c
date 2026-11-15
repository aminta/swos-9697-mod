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

/* S7 snapshot (s7-swap-plan.md piece 1; moved here from gplay.c, MC ruling (b) 13/11): gplay.c's gp_season calls it
   (GP_S7SNAP) at the end of each league struct's pass - GP_IN and GP_EXT are that country's - to copy the struct's
   crossings into S7X[its file's index]: the DIRECT ones (a division's original promoted / relegated count that B1 zeroed
   in the struct records: S7_DIR {file, local division, up 1 / down 0, count}, mkseason Pack.s7_direct), from its final
   table, then the play-out ones (GP_EXT, its order). dir: the struct's side (FA: its clubs go down). bad: a division not
   captured / a short table (1), GP_EXT.full (2), S7X full (4) - the builder refuses the season. season: the stamp. */
struct s7_row { uint16_t team, glob, won, gf, ga, pts; };
struct s7_in { uint8_t nd, pad[3]; uint8_t n[16], pad2[2]; struct s7_row t[16][32]; };   /* (gplay.c gp_in's head: its
                                           _Static_assert keeps t at 22, rows of 12 B, GD 16, GT 32) */
struct s7_ext { uint8_t n, full, pad[2]; struct { uint16_t glob, team; uint8_t pidx, outcome, pad[2]; } e[8]; };
_Static_assert(__builtin_offsetof(struct s7_in, t) == 22 && sizeof(struct s7_row) == 12, "gplay.c gp_in");
extern uint8_t S7_FA, S7_FB;            /* (below: the two struct files) */
uint8_t S7_DIR[16][4] DATA = {{0}};     /* (s7swap.py: Pack.s7_direct) */
uint8_t S7_NDIR DATA = 0;
static void s7_add(struct s7x *x, uint16_t glob, uint16_t team, int32_t kind, int32_t dir, int32_t div, int32_t rank)
{
    if (x->n >= 24) { x->bad |= 4; return; }
    x->e[x->n].glob = glob; x->e[x->n].team = team;
    x->e[x->n].kind = (uint8_t)kind; x->e[x->n].dir = (uint8_t)dir; x->e[x->n].div = (uint8_t)div; x->e[x->n].rank = (uint8_t)rank;
    x->n++;
}
void s7_snap(const struct s7_in *in, const struct s7_ext *ext, uint32_t pre, uint32_t seasp)
{
    if ((pre & 0xFF) || !in->n[0]) return;
    uint16_t f = in->t[0][0].team & 0xFF;       /* (the struct: its top division's file) */
    if (f != S7_FA && f != S7_FB) return;
    struct s7x *x = &S7X[f == S7_FA ? 0 : 1];
    x->file = f; x->n = x->bad = 0; x->season = (uint8_t)(seasp + 1);
    for (uint32_t k = 0; k < S7_NDIR && k < 16; k++) {
        const uint8_t *z = S7_DIR[k];
        if (z[0] != f || !z[3]) continue;
        int32_t d = z[1], n = d < 16 ? in->n[d] : 0;
        if (n <= z[3]) { x->bad |= 1; continue; }
        for (int32_t i = 0; i < z[3]; i++) {
            int32_t pl = z[2] ? i : n - z[3] + i;   /* (up: the first places; down: the last ones, best first) */
            s7_add(x, in->t[d][pl].glob, in->t[d][pl].team, 0, f == S7_FA, d, pl);
        }
    }
    if (ext->full) x->bad |= 2;
    for (int32_t i = 0; i < ext->n && i < 8; i++) s7_add(x, ext->e[i].glob, ext->e[i].team, 1, f == S7_FA, 0xFF, i);
}
extern sr_registry *SREG_REG;           /* sreg.c: -> the engine arena */
extern uint8_t SWE_ARENA_AT[];          /* swe.c: the registry at its start, the work area after it */
extern uint32_t SREG_FLAGS;             /* sreg.c: 'IT' flags (IMPORTED 1 | PENDING 2 | season << 8) */
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

/* S7 x pool (MC 13/11, s7-ri-fix.md Changes: the registry is the one truth). The off-file pool's clubs are registry
   idents S7_POOL0 .. + S7_NPOOL - 1, ident S7_POOL0 + j = the RS file's record j (s7swap.py pool_order asserts it by
   name); a row's record comes from its occupant's ident (s7_load). ri_pool (gplay.c) decides the pool's moves and logs
   them in RI_MOVES; s7_season applies them to the registry. */
uint16_t S7_POOL0 DATA = 0xFFFF, S7_NPOOL DATA = 0;
uint8_t *S7_RIPOOL DATA = 0;            /* ripool's RI_POOL of FB (obj2): u16 BE records, then 684 B each - read by ri_load
                                           once per DOS session; s7_load reads it itself when still empty (S7_RSNAME) */
char S7_RSNAME[16] DATA = {0};          /* its RS file (DATA\\RS5144.DAT) */
extern uint16_t RI_MOVES[][3];          /* s7ri.c (included below): this season end's pool moves {row of FB, out, in ident} */
extern int32_t RI_NMOVES;
struct { uint8_t n, status; uint16_t row; } S7_RIMV DATA = {0};   /* (harness: the moves applied, 1 ok / 2 refused,
                                                                     the refused move's row) */
uint32_t S7_OAT[2] DATA = {0};          /* their ORIG buffers' offsets in S7_ORIG */
uint16_t S7_ONREC[2] DATA = {0};        /* their records as shipped */
uint32_t S7_FNV[2] DATA = {0};          /* their FNV-1a as read into S7_ORIG (orig_read); every load checks it */
#ifndef S7_XNC
#define S7_XNC 0
#endif
#ifndef S7_XLB
#define S7_XLB 0
#endif
#ifndef S7_XT
#define S7_XT 0
#endif
#if S7_XT
extern uint16_t S7_XTEAM;               /* xtra.py xteam (obj1): xtra_read's cached block's team word, -1 none */
#endif
#if S7_XLB
extern uint16_t S7_XLBT;                /* xleft.py xlbt (obj3): xl_find's cached block's team word, -1 none */
#endif
#if S7_XNC
extern uint8_t S7_XCACHE[];             /* xtra.py xcache (obj1): S7_XNC entries of S7_XENT bytes, +3 = valid */
#endif
extern uint8_t S7_ORIG[];               /* swe.c .bss (swreg.S7_ORIG_SZ) */

/* the load apply's result (harness: S7_LD): status, both files read (1) / failed (2) / not yet (0), rows given another
   record by the last call, calls */
enum { LD_OK = 1, LD_NOREG = 2, LD_READ = 3, LD_SIZE = 4, LD_FILE = 5 };   /* (LD_FILE: the file read is not the
                                           one on disk even after a fresh ORIG read: nothing applied) */
struct { uint8_t status, oread, file, nopool; uint16_t moved, rows; uint32_t calls; int32_t rc; } S7_LD DATA = {0};
                                        /* (nopool: rows of a pool club with no RS record to give - never) */
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
       S7_WSITE = 9, S7_WMAP = 10, S7_SKIP = 11, S7_RIMV_BAD = 12 };
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
#define S7_NSW 96                        /* (S7 x pool: ri's moves too - Italy 36 + 18 crossers) */
#define PR_AT ((SW_AT + S7_NSW * sizeof(sr_reg_swap) + 15) & ~15u)   /* the word map: sr_wpair[S7_NPR] */
#define S7_NPR 256
#define WR_AT ((PR_AT + S7_NPR * sizeof(sr_wpair) + 15) & ~15u)   /* S7_WRES[WS_MAX] */
#ifndef SWE_ARENA
#define SWE_ARENA 0x8000
#endif
/* 4.2 S7 redraw (s7-redraw.md): pre[SR_REG_CLUBS] = every club's division BEFORE this season end (last season's groups), then the
   redraw's lists and s7geo.c's work (S7RD_LWORK <= RD_WSZ, asserted there) */
#define PRE_AT ((WR_AT + WS_MAX * 8 + 15) & ~15u)
#define RD_AT ((PRE_AT + SR_REG_CLUBS + 15) & ~15u)
#define RD_N 168                         /* (s7geo.c S7RD_MAXN) */
#define RD_WSZ 0x2800
#define RD_WORK_AT ((RD_AT + RD_N * 2 + RD_N + 2 * RD_N * 2 + 2 * RD_N + RD_N + 16 + 15) & ~15u)
typedef char s7_work_fits_the_arena[RD_WORK_AT + RD_WSZ <= SWE_ARENA ? 1 : -1];
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
        else if (s->item == WI_CFBH) { S7_WRES[k].ptr = (uint32_t)S7_CFB + 0x10000; S7_WRES[k].len = S7_CFBLEN - 0x10000; }
        else if (s->item != WI_CACHE)
            for (uint32_t e = 0; e < S7_ENN; e++)
                if ((S7_ENI[3 * e + 2] & 0xFFFF) == s->item) { S7_WRES[k].ptr = S7_ENI[3 * e]; S7_WRES[k].len = S7_ENI[3 * e + 1]; }
        uint32_t len = s->item == WI_CACHE ? 684 : S7_WRES[k].len;
        if (s->form != WS_W && s->form != WS_G && s->form != WS_R && s->form != WS_D) return k;
        if (s->item != WI_CACHE && !S7_WRES[k].ptr) return k;
        if (s->form == WS_R) {                      /* (u8 entries, contiguous, <= 256; stride = fill | file << 8: file 0 =
                                                       the item's byte at aux) */
            if (s->count && (s->off + (uint32_t)s->count > len || s->count > 256 || (!(s->stride >> 8) && s->aux >= len)))
                return k;
            continue;
        }
        if (s->form == WS_D) {                      /* (a DIY contest: count 1, stride = its room) */
            if (s->count != 1 || s->item == WI_CACHE || s->off + (uint32_t)s->stride > len) return k;
            continue;
        }
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

static int32_t walkm(const sr_wpair *m, int32_t n, const int8_t *slt);
static int32_t walk(int32_t nsw, const int8_t *slt)
{
    sr_wpair *m = (sr_wpair *)(SWE_ARENA_AT + PR_AT);
    int32_t n = sr_wmap_build((const sr_reg_swap *)(SWE_ARENA_AT + SW_AT), nsw, m, S7_NPR);
    S7_WLOG.npair = (uint16_t)(n < 0 ? 0 : n);
    if (n < 0) { S7_WLOG.rc = (int16_t)n; return -1; }
    return walkm(m, n, slt);
}

/* 42-s7import (MC 15/11): the old-save import's walk (sreg2.c, obj4+SREG2_AT) - its word map m (sr_wmap_import's, n
   pairs) over the same rows, the cache and the career club, the sites checked first (S7_WLOG.row >= 0: -1, nothing
   walked). S7_AREG: the arena's room the import may use while no season end runs: [W_AT, WR_AT) and [WR end, SWE_ARENA)
   (WR_AT..WR end = S7_WRES, this walk's). */
uint32_t S7_AREG[3] DATA = {W_AT, WR_AT, WR_AT + WS_MAX * 8};
int32_t s7_imp_walk(const sr_wpair *m, int32_t n, const int8_t *slt)
{
    S7_WLOG.row = (int16_t)wcheck(); S7_WLOG.rc = 0; S7_WLOG.changed = S7_WLOG.cache = S7_WLOG.rows = 0;
    S7_WLOG.npair = (uint16_t)n;
    if (S7_WLOG.row >= 0) return -1;
    return walkm(m, n, slt);
}

static int32_t walkm(const sr_wpair *m, int32_t n, const int8_t *slt)
{
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

/* The caches keyed by a team word (xtra.py xt_block's xcache, xleft.py xlbt, xtra_read's xteam): after the
   registry moved clubs (s7_season) or may have (sreg_load / sreg_new: SREG_CHG) a word may name another club - every
   entry dropped; the reads go by the home word (MC 13/11). None of them is saved: after a load they start cold. */
void s7_flush(void)
{
#if S7_XNC
    for (int32_t k = 0; k < S7_XNC; k++) S7_XCACHE[k * S7_XENT + 3] = 0;
#endif
#if S7_XLB
    S7_XLBT = 0xFFFF;
#endif
#if S7_XT
    S7_XTEAM = 0xFFFF;
#endif
}

uint8_t S7RD_NEWER DATA = 0;            /* 1: the last season end met a newer rule version (no redraw; host tests / harness) */
#define S7RD_RULE_VER 1u              /* (the frozen rule: 42-redraw 31db319, STAY 540, isqrt((4 dlat)^2 + (3 dlon)^2), integer Hungarian) */
/* the redraw (s7geo.c's s7rd_level, obj4+S7GEO; s7swap.py sets it; 0: no redraw, the crossers' place() groups stay) */
int32_t (*S7RD_PTR)(int32_t, int32_t, const uint16_t *, const uint8_t *, int32_t, int32_t, const uint16_t *, const uint8_t *, int32_t,
                    const uint8_t *, uint32_t, uint8_t *, uint8_t *) DATA = 0;

/* one level (lv[0..ng) its divisions, group order): every club whose nd is there gets its group from the rule - last season's
   group from pre[], the anchors from last season's members (pre[]), the sizes as they stand (the crossers placed) */
static void redraw(int32_t lvl, const sr_registry *R, uint8_t *nd, const uint8_t *pre, const uint8_t *lv, int32_t ng, int32_t sec,
                   uint32_t seed)
{
    uint16_t *id = (uint16_t *)(SWE_ARENA_AT + RD_AT), *lid = id + RD_N;
    uint8_t *last = (uint8_t *)(lid + 2 * RD_N), *lgrp = last + RD_N, *out = lgrp + 2 * RD_N, *cap = out + RD_N;
    int32_t n = 0, nl = 0;
    for (int32_t g = 0; g < ng; g++) cap[g] = 0;
    for (int32_t i = 0; i < R->nclub; i++) {
        int32_t gn = -1, gp = -1;
        for (int32_t g = 0; g < ng; g++) { if (lv[g] == nd[i]) gn = g; if (lv[g] == pre[i]) gp = g; }
        if (gp >= 0) { if (nl == 2 * RD_N) return; lid[nl] = (uint16_t)i; lgrp[nl++] = (uint8_t)gp; }
        if (gn >= 0) { if (n == RD_N) return; id[n] = (uint16_t)i; last[n++] = gp >= 0 ? (uint8_t)gp : 0xFF; cap[gn]++; }
    }
    if (!n || S7RD_PTR(lvl, n, id, last, sec, nl, lid, lgrp, ng, cap, seed, out, SWE_ARENA_AT + RD_WORK_AT)) return;
    for (int32_t k = 0; k < n; k++) nd[id[k]] = lv[out[k]];
}

static int32_t run(void *pv) {
    int8_t *slt = ((struct args *)pv)->sltcopy;
    uint8_t *nd = SWE_ARENA_AT + ND_AT;
    uint16_t *order = (uint16_t *)(SWE_ARENA_AT + ORD_AT);
    sr_registry *R = SREG_REG;
    S7_LOG.nswap = S7_LOG.ncross = 0; S7_LOG.rc = 0;
    extern uint8_t RI_FRESH;                /* (consumed first, before any early return: never 1 after s7_season - MC 13/11) */
    int32_t nri = RI_FRESH ? RI_NMOVES : 0;  /* (RI_NMOVES / RI_MOVES stay as logged: the harness) */
    RI_FRESH = 0;
#ifdef S7_NOSWAP
    return S7_LOG.status = S7_SKIP;     /* (S7_NOSWAP test builds: no swap at all - world_s7cross_diff's control) */
#endif
    if (!sreg_get()) return S7_LOG.status = S7_NOREG;
    uint8_t *pre = SWE_ARENA_AT + PRE_AT;   /* (the redraw's last season: before ri's moves and the crossings) */
    for (int32_t i = 0; i < R->nclub && i < SR_REG_CLUBS; i++) pre[i] = (uint8_t)sr_reg_div(R, i);
    /* ri_pool's moves first (it ran before us, pg_fix order), whatever else this season end does: the registry
       follows ri's queue. Each as {a, NONE, on}: the occupant off the files (queued in ri's q[]), the pool head onto
       its row - the row and its division stay. All checked before any is applied. */
    sr_reg_swap *sw = (sr_reg_swap *)(SWE_ARENA_AT + SW_AT);
    int32_t fb0 = fi_of(S7_FB);
    S7_RIMV.n = 0; S7_RIMV.status = 1; S7_RIMV.row = 0;
    for (int32_t k = 0; k < nri; k++) {
        uint32_t row = RI_MOVES[k][0], out = RI_MOVES[k][1], in = RI_MOVES[k][2];
        int32_t ok = nri <= S7_NSW / 2 && fb0 >= 0 && row < R->rows[fb0] && R->at[fb0][row] == out &&
                     in < (uint32_t)R->nclub && R->word[in] == SR_REG_NONE && in != out;
        for (int32_t j = 0; ok && j < k; j++) ok = RI_MOVES[j][0] != row && RI_MOVES[j][2] != in;
        if (!ok) { S7_RIMV.status = 2; S7_RIMV.row = (uint16_t)row; return S7_LOG.status = S7_RIMV_BAD; }
    }
    for (int32_t k = 0; k < nri; k++) {
        uint16_t row = RI_MOVES[k][0], out = RI_MOVES[k][1], in = RI_MOVES[k][2], wd = (uint16_t)(S7_FB | row << 8);
        R->word[out] = SR_REG_NONE; R->at[fb0][row] = in; R->word[in] = wd;
        sw[k].a = wd; sw[k].b = SR_REG_NONE; sw[k].on = in;
    }
    S7_RIMV.n = (uint8_t)nri;
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
    uint32_t rver = SREG_FLAGS >> 4 & 0xF;  /* (the rule version this career's groups were drawn with: 'IT' flags bits 4..7, 0 none yet) */
    S7RD_NEWER = (uint8_t)(rver > S7RD_RULE_VER);   /* (MC 15/11: a save from a newer build's rule keeps its groups - no redraw,
                                                       the crossers' place() only, the version kept - never a crash) */
    if (S7RD_PTR && !S7RD_NEWER) {      /* 4.2 redraw: Serie C (the upper boundary level, second teams constrained) and Serie D */
        uint32_t seed = (uint32_t)S7_SELTEAM ^ A->season;   /* (the career club's word ^ the season: per career, per season) */
        redraw(0, R, nd, pre, S7_UP, S7_NUP, 1, seed);
        redraw(1, R, nd, pre, S7_LO, S7_NLO, 0, seed);
    }
    S7_WLOG.row = (int16_t)wcheck(); S7_WLOG.rc = 0; S7_WLOG.changed = S7_WLOG.cache = S7_WLOG.npair = S7_WLOG.rows = 0;
    if (S7_WLOG.row >= 0) return S7_LOG.status = S7_WSITE;     /* (before the registry changes: nothing done) */
    sr_reg_work *w = (sr_reg_work *)(SWE_ARENA_AT + W_AT);
    int32_t c = sr_reg_season(R, nd, order, no, 0, w, sw + nri, S7_NSW - nri);
    S7_LOG.rc = c;
    if (c < 0) return S7_LOG.status = S7_REG;
    c += nri;                           /* (the walk: ri's moves, then the crossings) */
    S7_LOG.nswap = (uint8_t)c;
    s7_flush();
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
    SREG_FLAGS &= ~(uint32_t)(SR_REGSAVE_PENDING | 0xFF00);    /* (42-s7import: an imported save's PENDING clears at its
                                                                  first S7 season end - n7-p4 §9a.1; IMPORTED stays) */
    if (S7RD_PTR && !S7RD_NEWER)        /* 4.2 redraw: the rule version in the 'IT' flags' spare bits 4..7 (s7-redraw.md 3: a later rule
                                           change can tell an old career's groups from its own; 0 = no redraw season end yet) */
        SREG_FLAGS = (SREG_FLAGS & ~(uint32_t)0xF0) | S7RD_RULE_VER << 4;
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

uint32_t s7_poolk(uint32_t x)            /* GP_POOLK (gplay.c): an ident's index among the pool idents, 0xFFFF none;
                                           0x10000 | k: RS record k's ident (ri's queue seed), 0xFFFF past the pool */
{
    if (x & 0x10000) return (x & 0xFFFF) < S7_NPOOL ? S7_POOL0 + (x & 0xFFFF) : 0xFFFF;
    x &= 0xFFFF;
    return x >= S7_POOL0 && x < (uint32_t)S7_POOL0 + S7_NPOOL ? x - S7_POOL0 : 0xFFFF;
}

static void pool_read(void)             /* RI_POOL still empty (ri_load reads it with the first FB load of a DOS session;
                                           a pool club promoted into FA can be loaded before): the RS file, as ri_load */
{
    uint32_t want = 2 + 684u * S7_NPOOL;
    int h = swe_fopen_r(S7_RSNAME);
    if (h < 0) return;
    int r = swe_fread(h, S7_RIPOOL, want);
    swe_fclose(h);
    if (r != (int)want || be16(S7_RIPOOL) != S7_NPOOL) S7_RIPOOL[0] = S7_RIPOOL[1] = 0;
}

static void rec_copy(uint8_t *d, const uint8_t *s)   /* gplay.c ri_copy's rule: all but the row's own bytes */
{
    for (int32_t b = 0; b < 684; b++)
        if (b > 4 && b != 23 && b != 25) d[b] = s[b];
}

struct largs { uint8_t *buf; uint32_t file; const uint8_t *orig; };   /* (orig: the file as read - TEAMBUF, or a
                                           pooled file's RI_ORIG copy taken before ri_apply wrote its identities into
                                           TEAMBUF: MC 13/11, option B; the hash checks the file on disk, the apply
                                           writes TEAMBUF as before) */

static int32_t load_run(void *pv)
{
    uint8_t *buf = ((struct largs *)pv)->buf;
    const uint8_t *orig = ((struct largs *)pv)->orig ? ((struct largs *)pv)->orig : buf;
    uint32_t file = ((struct largs *)pv)->file & 0xFF;
    int32_t s = file == S7_FA ? 0 : file == S7_FB ? 1 : -1;
    if (s < 0) return 0;
    S7_LD.calls++; S7_LD.file = (uint8_t)file; S7_LD.moved = S7_LD.rows = 0; S7_LD.nopool = 0;
    if (!sreg_get()) return S7_LD.status = LD_NOREG;
    if (be16(buf) != S7_ONREC[s] || be16(orig) != S7_ONREC[s]) return S7_LD.status = LD_SIZE;
    uint32_t h = s7_fnv(orig, 2 + 684u * S7_ONREC[s]);
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
        if (hs < 0) {                                   /* (no home row: a pool club - RS record S7_POOL0 + k) */
            uint32_t k = s7_poolk((uint32_t)id);
            if (k == 0xFFFF) continue;
            if (S7_RIPOOL && !be16(S7_RIPOOL)) pool_read();
            if (!S7_RIPOOL || k >= (uint32_t)be16(S7_RIPOOL)) { S7_LD.nopool++; continue; }
            rec_copy(buf + 2 + 684 * o, S7_RIPOOL + 2 + 684 * k);
            moved++;
            continue;
        }
        if ((h >> 8) >= S7_ONREC[hs]) continue;
        if (hs == s && (h >> 8) == o) continue;      /* (its own row: the record as read) */
        rec_copy(buf + 2 + 684 * o, S7_ORIG + S7_OAT[hs] + 2 + 684 * (h >> 8));
        moved++;
    }
    S7_LD.moved = (uint16_t)moved; S7_LD.rows = R->rows[fi];
    return S7_LD.status = LD_OK;
}

/* S7 (MC 13/11, the wage item): data keyed by a club's team word (XTRA.nnn blocks...) belongs to the club's HOME
   word (CONVENTIONS 14d: identity = home, place = current). The word -> the registry club in that row of the two
   league files -> its home word; any other word, no registry or a club without a home: the word itself. */
static int32_t home_run(void *pv)
{
    uint32_t w = *(uint32_t *)pv & 0xFFFF, file = w & 0xFF, ord = w >> 8;
    if (file != S7_FA && file != S7_FB) return (int32_t)w;
    if (!sreg_get()) return (int32_t)w;
    const sr_registry *R = SREG_REG;
    int32_t fi = fi_of((uint8_t)file);
    if (fi < 0 || ord >= R->rows[fi]) return (int32_t)w;
    int32_t id = R->at[fi][ord];
    if (id < 0 || id >= R->nclub) return (int32_t)w;
    uint16_t h = home_of(id);
    return h == 0xFFFF ? (int32_t)w : h;
}

static int32_t ident_run(void *pv)      /* the registry club in team word w's row of the two league files, 0xFFFF none */
{
    uint32_t w = *(uint32_t *)pv & 0xFFFF, file = w & 0xFF, ord = w >> 8;
    if ((file != S7_FA && file != S7_FB) || !sreg_get()) return 0xFFFF;
    const sr_registry *R = SREG_REG;
    int32_t fi = fi_of((uint8_t)file);
    if (fi < 0 || ord >= R->rows[fi]) return 0xFFFF;
    int32_t id = R->at[fi][ord];
    return id >= R->nclub ? 0xFFFF : id;
}

uint32_t s7_ident(uint32_t w)           /* GP_IDENT (gplay.c ri_pool / ri_cache / cd_str): cdecl, -> the engine's C stack */
{
    int32_t r = cstack_call(ident_run, &w);
    return r < 0 ? 0xFFFF : (uint32_t)r;  /* (CSTACK_REFUSED: none - ri_pool counts it in RI_S7_BAD) */
}

uint32_t s7_home_word(uint32_t w)       /* xtra_readto (S7_HPTR): cdecl, the game's stack -> the engine's C stack */
{
    uint32_t w0 = w & 0xFFFF;
    int32_t r = cstack_call(home_run, &w);
    return r < 0 ? w0 : (uint32_t)r;    /* (CSTACK_REFUSED: the word itself) */
}

void s7_load(uint8_t *buf, uint32_t file, const uint8_t *orig)   /* ri_load (S7_LPTR): cdecl, the game's stack -> the
                                                                    engine's C stack; orig: the file as read */
{
    struct largs a;
    a.buf = buf; a.file = file; a.orig = orig;
    cstack_call(load_run, &a);
}

void s7ri_unhint(void);                 /* (s7ri.c, included below) */
int32_t s7_season(int8_t *sltcopy)     /* pg_fix: cdecl, the game's stack -> the engine's C stack */
{
    s7ri_unhint();                      /* (FIRST, before any early return: ri_ida's transient maps[] words never outlive the pg_fix) */
    struct args a;
    a.sltcopy = sltcopy;
    return cstack_call(run, &a);
}

/* S7 x ri: Panchina's s7ri.c (MC ruling (b) 13/11: S7-only logic in obj4) - one translation unit with this file: it calls
   s7_ident / s7_poolk / s7_home_word, its RI_MOVES is read by s7_season above */
uint8_t RI_FRESH DATA = 0;             /* s7ri_pool(144) sets it with a new log; s7_season consumes it once (no stale moves at a
                                           career start - ri_season returns before its pools - or in a second career) */
#include "s7ri.c"
