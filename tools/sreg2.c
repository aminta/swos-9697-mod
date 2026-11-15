/* 42-s7import (MC 15/11, Panchina's scope, binding): the old-save import in the exe - obj4+SREG2_AT (one page, sreg.py
   patch_import). A 4.1 World 2026-27 career (one-file Italy: 102 with Serie D on rows 100..255, RI live on it) loaded on
   an S7 build has no SWC1 'IT': swe.c it_load's absent branch calls SREG_FN[4], which is sreg_absent here (sreg.c's
   sreg_build before; a dormant build links none of this). Steps (n7-p4.md §4 / §9c option B, mc-s7-glue.md §4):
   1. sreg_build: the spec's registry, built = 1 (sreg.c), the word caches flushed (SREG_CHG);
   2. sreg_import: each 4.1 slot's actual division (IMP_BASE = 4.1 TMW5.102 +25, + the save's someLeaguesTable delta at
      the slot's 4.1 global), the save's RI maps and queue (RI_STATE through 4.1's layout IMP_LAY41) -> ONE
      sr_reg_season; the 6 PENDING; the word map (sr_wmap_import);
   3. sreg_ri_import: RI_STATE re-laid for the S7 table (Italy on 144);
   4. sreg_slt_import: someLeaguesTable re-based - old base IMP_BASE[4.1 slot], new base the S7 row's shipped division
      (s7_load's rec_copy keeps a row's byte 25: s7_season / put_slot's convention, MC 15/11);
   5. s7_imp_walk: every WSITES row, the team cache, the career club (selTeamNumber, careerTeam, careerTeamLeague);
      D6CDC = careerTeamLeague + its new delta when the career club changed row (MC 15/11, point 4);
   6. commit: RI_STATE and someLeaguesTable written, SREG_FLAGS = IMPORTED (| PENDING | season << 8); s7_flush.
   All checked before anything is written: the walk checks its sites first (nothing walked on a bad one), RI_STATE and
   the table are built in the arena and copied only after the walk. A refusal (SREG_IMP.rc < 0, .stage, .bad = the
   club's ident) leaves the spec's registry and the save's bytes as loaded (CONVENTIONS 14a: never a guess).
   Memory: the engine arena only (no .bss): s7swap.c's S7_AREG says which parts no season end holds while a load runs. */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/swosrules.h"                     /* (prototypes only: sr_reg_build / check from sreg.c, sr_reg_season /
                                                   sr_wmap_import from s7swap.c - the library's one copy each) */
#include "sreg_import.c"

#define DATA __attribute__((section(".data")))
#ifndef IMP_NCLUB
#define IMP_NCLUB 1
#define IMP_NPOOL41 1
#define IMP_LAYN 1
#define IMP_GLN 1
#define IMP_NSLT 2000
#define SWE_ARENA 0x8000
#endif

extern sr_registry *SREG_REG;
extern int32_t SREG_NF, SREG_NCLUB;
extern sr_reg_file SREG_SPEC[];
extern const uint8_t SREG_DIV[];
extern const uint8_t SREG_SWC1[];
extern uint32_t SREG_WORLD, SREG_FLAGS;
int32_t sreg_build(void);
extern uint8_t SWE_ARENA_AT[];
int cstack_call(int (*fn)(void *), void *arg);
void swe_ready(void);
extern uint8_t IMP_RI[];                        /* gplay.c RI_STATE (the engine item 'RI', as loaded) */
extern uint8_t IMP_SLT[];                       /* someLeaguesTable (bigtables: IMP_NSLT bytes, the live table) */
extern uint8_t IMP_SEASON[];                    /* the game's seasonPlaying */
extern uint16_t IMP_D6CDC;                      /* dseg_D6CDC: the career division (obj2, selTeamNumber + 6) */
extern uint8_t IMP_CCN;                         /* compCountryNumber (obj2, in the .CAR: ProcessCareerFile's country at load) */
extern uint32_t IMP_COMPTAB[256];               /* competitionsTable (obj2): per country [league ptr, -2, cup ptrs, -1] */
extern uint8_t IMP_D8[26];                      /* dseg_D8CAA, D8CAE, D8CB2, D8CB6 at +0/4/8/12, D8CBA +16, D8CC0 +22: the loaded contests'
                                                   sources (obj2, rebuilt by ProcessCareerFile at every load) */
extern uint8_t IMP_DIY[0x733];                 /* DIY_competitionStart = competitionFileBuffer (obj2): the career's live league */
extern uint8_t IMP_D6CB8;                       /* dseg_D6CB8: the career club's FILE (obj2, selTeamNumber - 0x1E; set by
                                                   InitializeNewSeason, read by cseg_5B705's LoadTeamFile - Motore 15/11) */
extern uint32_t S7_AREG[3];
extern struct { uint16_t old, neww; int16_t league, pad; } S7_CLOG;
int32_t s7_imp_walk(const sr_wpair *m, int32_t n, const int8_t *slt);
void s7_flush(void);

/* sreg.py fills these (tools/import41_fixed.json, the shaped pack) */
uint16_t IMP_OLD[IMP_NCLUB] DATA = {0};         /* old_ord: each ident's 4.1 identity (import41.csv) */
uint8_t IMP_NEWPOOL[IMP_NPOOL41] DATA = {0};    /* a 4.1 pool record -> its S7 RS index, 0xFF gone (newpool41.csv) */
uint8_t IMP_BASE[256] DATA = {0};               /* 4.1 TMW5.102's byte 25 per slot */
uint8_t IMP_LAY41[IMP_LAYN] DATA = {0}, IMP_LAY7[IMP_LAYN] DATA = {0};   /* the two RI tables (sreg.ri_layout) */
uint8_t IMP_GL41[IMP_GLN] DATA = {0}, IMP_GL7[IMP_GLN] DATA = {0};       /* the two global run tables */
uint8_t IMP_FILES[2] DATA = {0};                /* 4.1's file (102), S7's RI file (144) */
uint8_t IMP_NDIV DATA = 0;                      /* the league's divisions (sreg_slt_import's range) */
/* harness: the last import (calls counts sreg_absent's; stage 0 none, 1 import, 2 RI, 3 table, 4 walk, 5 room;
   rc < 0 a refusal there, 1 imported, 0 no import - another world, or nothing to do) */
struct { int32_t rc, stage, bad, nswap, nmap, npend; uint32_t flags, calls; uint16_t walked, cache; } SREG_IMP DATA = {0};

#define NSW 384
#define NPR 512
#define A16(x) (((x) + 15u) & ~15u)

static int32_t rowbase(uint16_t w)              /* the S7 row's shipped division (the league's index), 0 off the files */
{
    const sr_registry *R = SREG_REG;
    if (w == SR_REG_NONE) return 0;
    for (int32_t i = 0; i < R->nfiles; i++) {
        if (R->f[i].file != (w & 0xFF)) continue;
        uint32_t r = 0;
        for (int32_t k = 0; k < R->f[i].ndiv; k++) if ((w >> 8) < (r += R->f[i].size[k])) return R->f[i].div[k];
    }
    return 0;
}

/* 42-s7import (LIGORNA 15/11): the career club changed file at the import (a Serie D career, 102 -> 144) - the
   season's league is the new file's: compCountryNumber and the pointers ProcessCareerFile derived from it at this load
   (before after_load), redone as it does them: D8CAA = the country's league, D8CAE / D8CB2 = its cups up to the -1,
   D8CBA / D8CC0 = the career division's (D6CDC) sub-contest when its byte +12h is set. Without it the season end
   treated D6CDC as a division of the OLD league (Serie A) and the game sat on a match screen. */
#define D8W(o) (*(uint32_t *)(IMP_D8 + (o)))
#ifndef IMP_PTR
#define IMP_PTR(x) ((const uint8_t *)(x))     /* (an obj2 linear address; the host test maps it into its arena) */
#endif
static void ccn_move(uint8_t f)
{
    const uint32_t *t = (const uint32_t *)IMP_PTR(IMP_COMPTAB[f]);
    IMP_CCN = f;
    D8W(0) = D8W(4) = D8W(8) = 0;
    D8W(16) = D8W(22) = 0;   /* (D8CBA, D8CC0) */
    if (!IMP_COMPTAB[f]) return;
    D8W(0) = t[0];
    if (t[2] != 0xFFFFFFFFu) { D8W(4) = t[2]; if (t[3] != 0xFFFFFFFFu) D8W(8) = t[3]; }
    const uint8_t *a1 = IMP_PTR(D8W(0)) + 6u * IMP_D6CDC;
    if (IMP_DIY[0] == 0 && IMP_DIY[1] == 0) {   /* (the live league - a league: its rules as cseg_8F1F2 copied them from the
                                                   OLD struct's division at the season start; the new struct's, the same way:
                                                   +53h promotions, +55h play-off ones, +57h relegations, +59h play-off ones,
                                                   a negative play-off byte = (-x) >> 1. Else the season end applies the 4.1
                                                   Serie D group's 1 up / 2 down to a file-144 group: BIELLESE -1 by
                                                   cseg_93FD8, -3 by pg_season, cseg_3283C's trap - LIGORNA 15/11) */
        for (int32_t k = 0; k < 4; k++) {
            uint8_t x = a1[0x0E + k];
            uint16_t v = (k & 1) && (x & 0x80) ? (uint16_t)((uint8_t)-x >> 1) : x;
            IMP_DIY[0x53 + 2 * k] = (uint8_t)v; IMP_DIY[0x54 + 2 * k] = (uint8_t)(v >> 8);
        }
    }
    const uint8_t d0 = a1[0x12];
    if (d0) {
        const uint8_t *q = a1 + 0x12 + d0;
        D8W(16) = *(const uint32_t *)q;
        D8W(22) = *(const uint32_t *)(q + 4);
    }
}

static int32_t fail(int32_t stage, int32_t rc, int32_t bad)
{
    SREG_IMP.stage = stage; SREG_IMP.rc = rc < 0 ? rc : -99; SREG_IMP.bad = bad;
    sr_reg_build(SREG_REG, SREG_NF, SREG_SPEC, SREG_NCLUB, SREG_DIV);   /* (the spec's registry: nothing applied) */
    SREG_FLAGS = 0;
    return SREG_IMP.rc;
}

static int32_t run(void *pv)
{
    (void)pv;
    SREG_IMP.rc = SREG_IMP.stage = SREG_IMP.nswap = SREG_IMP.nmap = SREG_IMP.npend = 0;
    SREG_IMP.bad = -1; SREG_IMP.flags = 0; SREG_IMP.walked = SREG_IMP.cache = 0;
    if (sreg_build() || !SREG_WORLD || *(const uint16_t *)(SREG_SWC1 + 2) != SREG_WORLD) return 0;
    const uint32_t n = (uint32_t)SREG_NCLUB;
    if (n > IMP_NCLUB) return fail(5, -1, -1);
    /* the arena: [r1, r1e) and [r2, SWE_ARENA) */
    const uint32_t r1 = A16(S7_AREG[0]), r1e = S7_AREG[1], r2 = A16(S7_AREG[2]);
    const uint32_t a_sw = r1, a_map = A16(a_sw + NSW * sizeof(sr_reg_swap)), a_slt = A16(a_map + NPR * sizeof(sr_wpair)),
                   a_ri = A16(a_slt + IMP_NSLT), a_sd = A16(a_ri + SREG_RI_SIZE), e1 = a_sd + 256;
    const uint32_t a_rw = r2 + A16(sizeof(uint16_t) * SR_REG_CLUBS);   /* (ri_work and then the bases: after old_word) */
    const uint32_t e2 = r2 + sizeof(sreg_imp_work) > a_rw + sizeof(sreg_ri_work) ? r2 + sizeof(sreg_imp_work)
                                                                                 : a_rw + sizeof(sreg_ri_work);
    if (e1 > r1e || e2 > SWE_ARENA || a_rw + 2 * n > SWE_ARENA) return fail(5, -2, -1);
    uint8_t *A = SWE_ARENA_AT;
    sr_reg_swap *sw = (sr_reg_swap *)(A + a_sw);
    sr_wpair *map = (sr_wpair *)(A + a_map);
    uint8_t *slt = A + a_slt, *nri = A + a_ri, *sd = A + a_sd;
    sreg_imp_work *iw = (sreg_imp_work *)(A + r2);
    sreg_ri_work *rw = (sreg_ri_work *)(A + a_rw);
    sreg_ri_ent oe;
    const int32_t k41 = ri_ent(IMP_LAY41, (int32_t)SREG_WORLD, IMP_FILES[0], &oe);
    if (k41 < 0 || oe.np != 1 || oe.nmap > 256) return fail(1, -3, -1);
    const int init = IMP_RI[SREG_RI_INIT + k41] != 0;
    const uint16_t *maps = (const uint16_t *)(IMP_RI + SREG_RI_MAPS + 2 * oe.moff);
    const uint16_t *queue = (const uint16_t *)(IMP_RI + SREG_RI_Q + 2 * oe.qo);
    const int32_t nq = init ? IMP_RI[SREG_RI_QN + oe.pi] : 0;
    for (int32_t x = 0; x < oe.nmap; x++) {     /* each 4.1 slot's actual division: base + the save's delta */
        const int32_t g = gl_glob(IMP_GL41, (uint16_t)(IMP_FILES[0] | x << 8));
        if (g < 0 || g >= IMP_NSLT) return fail(1, -4, 0x8000 | x);
        sd[x] = (uint8_t)(IMP_BASE[x] + (int8_t)IMP_SLT[g]);
    }
    sreg_imp_res res;
    const int32_t ns = sreg_import(SREG_REG, SREG_SPEC, SREG_NF, SREG_DIV, (int32_t)n, IMP_OLD, maps, oe.nmap,
                                   oe.n[0], IMP_FILES[0], sd, queue, nq, IMP_FILES[1], IMP_SEASON[0], iw, sw, NSW, map,
                                   NPR, &res);
    if (ns < 0) return fail(1, ns, res.bad);
    int32_t bad = -1;
    const int32_t rk = sreg_ri_import(SREG_REG, SREG_SPEC, SREG_NF, SREG_DIV, (int32_t)n, IMP_OLD, sw, ns, IMP_NEWPOOL,
                                      IMP_NPOOL41, IMP_LAY41, IMP_LAY7, (uint8_t)SREG_WORLD, IMP_FILES[0], IMP_FILES[1],
                                      IMP_RI, nri, rw, &bad);
    if (rk) return fail(2, rk, bad);
    uint8_t *ob = A + a_rw, *nb = ob + n;       /* (ri_work is done: its room holds the bases) */
    for (uint32_t c = 0; c < n; c++) {
        const uint16_t ow = iw->old_word[c];
        ob[c] = ow == SR_REG_NONE ? 0 : IMP_BASE[ow >> 8];
        nb[c] = (uint8_t)rowbase(SREG_REG->word[c]);
    }
    const int32_t sk = sreg_slt_import(SREG_REG, iw->old_word, (int32_t)n, IMP_GL41, IMP_GL7, ob, nb, IMP_NDIV, IMP_SLT,
                                       slt, IMP_NSLT, &bad);
    if (sk < 0) return fail(3, sk, bad);
    if (s7_imp_walk(map, res.nmap, (const int8_t *)slt) < 0) return fail(4, -5, -1);   /* (sites checked first) */
    for (uint32_t b = 0; b < SREG_RI_SIZE; b++) IMP_RI[b] = nri[b];
    for (uint32_t b = 0; b < IMP_NSLT; b++) IMP_SLT[b] = slt[b];
    if (S7_CLOG.neww) {                         /* (the career club on another row: its division in the struct) */
        const int32_t g = gl_glob(IMP_GL7, S7_CLOG.neww);
        if (g >= 0 && g < IMP_NSLT) IMP_D6CDC = (uint16_t)(S7_CLOG.league + (int8_t)IMP_SLT[g]);
        IMP_D6CB8 = (uint8_t)S7_CLOG.neww;      /* (its file: InitializeNewSeason's copy, stale until the next start) */
        if (IMP_CCN == (uint8_t)S7_CLOG.old) ccn_move((uint8_t)S7_CLOG.neww);
    } else if (IMP_CCN == IMP_FILES[0]) {
        ccn_move(IMP_CCN);                      /* (an Italian career that stays in 102 - TRENTO 15/11: its live league
                                                   still holds the 4.1 struct's rules (Serie C group: 4.1's relegations into
                                                   102's Serie D), the season end moved a row past 102's S7 divisions,
                                                   S7_PLACE, then cseg_3283C's trap. The S7 struct's rules; D8CAA.. as the
                                                   load computed them - the same bytes) */
    }
    SREG_FLAGS = res.flags;
    s7_flush();
    SREG_IMP.nswap = ns; SREG_IMP.nmap = res.nmap; SREG_IMP.npend = res.npend; SREG_IMP.flags = res.flags;
    SREG_IMP.walked = 1; SREG_IMP.cache = 0;
    return SREG_IMP.rc = 1;
}

void sreg_absent(void)                          /* SREG_FN[4]: it_load, a save with no 'IT' */
{
    SREG_IMP.calls++;
    swe_ready();
    if (cstack_call(run, 0) == -4)       /* (cstack.h CSTACK_REFUSED) */ fail(5, -6, -1);
}
