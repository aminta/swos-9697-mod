/* fpad.c -- 4.2 the fixture port's adapter (P2; internal/handoff/motore-fixport-plan.md 1b, MC review 14/11), linked
 * by fpad.py at obj4 + swreg.FPORT_AT. The engine's sr_port (tools/swce/sr_port.c: its one copy in the exe) queues
 * the season's non-league fixtures; at each calendar advance (gplay's sc_step_c head, GP_PSTEP) fp_step installs the
 * career club's due fixture in slot 4 through gplay's ko_one (GP_PAPI[0], kind K_PORT), every other one is
 * simulated (fp_sim); the played tie comes back through gp_rec (GP_PLEG: each match's goals, GP_PDONE: the tie
 * decided) as an sr_port_result, checked by the engine (sr_port_result_in: a mismatch refused, never overridden).
 *
 * State: FP_PORT (sr_port, 2368 B) and FP_ST in swe.c's .bss (DOS/4GW zeroes no tail): valid only under FP_MAGIC and
 * the season, written only by fp_new (a new career: engine.after_new), fp_load (a load: engine.after_process, which
 * also sets FP_ST.loaded - MC 2) and a new season (fp_season: gplay pg_season's end, pg_fix in InitializeNewSeason), which arm it; fp_step inits. fp_step with FP_ST.loaded first
 * revalidates (MC 2a: before the poll and before any season-end path), a refusal goes to sr_port_missed with a log
 * line (2b), nothing touches FP_PORT between the load and there (2c).
 *
 * Interim until P5 (the FP save section): a load starts an empty queue; a K_PORT tie left in slot 4 is played by
 * gplay and its result logged as an orphan (FL_ORPHAN), not credited. P5 is required before a release (MC 14/11). */
#include <stdint.h>
#include "swce/swosrules.h"
#include "swce/sr_port.c"

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t i32;

/* gplay (MC 14/11 (b)+(c)): slot 4's builder ko_one through GP_PAPI[0]; GP_ST / GP_IN / GP_SCT and the game's pseudo
   registers at their symbols (fpad.py externs); the struct offsets and constants (O_*, C_*) from gplay.c's GP_OFFS -
   a -DGP_OFFSETS compile of it with the build's own flags (fpad.py gp_offsets) */
struct gp_ko;
typedef void ko_one_fn(struct gp_ko *, u16, u16, int, int, int, int, int, int, const u8 *);
extern void *const GP_PAPI[1];          /* gplay.c (obj1): ko_one */
extern u8 GP_GST[];                     /* gplay.c GP_ST (obj2) */
extern const u8 GP_GIN[];               /* gplay.c GP_IN (obj2) */
extern const u16 FP_CDIV[1];            /* the game's career-club division word (D6CDC, obj2: gplay._cardiv) */
extern const u8 GP_SEAS;                /* gplay.c: the season gp_ours / the advance last saw */
extern const u32 GP_K;                  /* gplay.c: gp_ours' contest index (ko[GP_K]) */
extern const u8 *const GP_SCT;          /* gplay.c: the supercup table (0 = none) */
extern u8 GP_PMID;                      /* gplay.c .bss: the port tie's legs played (the gate's mid-tie save) */
extern const u8 FP_D1R[];               /* obj2: the game's pseudo registers D1..D7 (stride 4) */
extern const u8 *const FP_A1R, *const FP_A2R;   /* obj2: A1 / A2 (the match's clubs' team words) */
extern const u16 FP_CALCUR;             /* obj2: the current calendar entry's offset */
#define KO0 (GP_GST + O_KO)             /* ko[0] */
#define KB(o) (KO0[o])
#define KW(o) (*(const u16 *)(KO0 + (o)))
extern u32 GP_WK;                       /* gplay.c: the current calendar entry's week (the unit) */
extern u16 GP_MGR;                      /* gplay.c: the career club's team word */
extern const u8 FP_SEASON;              /* obj2: the game's seasonPlaying byte (always current) */
extern const u8 FP_CWB;                 /* obj2: the career's world byte (careerworld; fpad.py's world: FP_WORLD) */
extern u8 FP_CAL[];                     /* obj2: the career calendar (count word at -4, entries: slot, week, len word) */
extern sr_port FP_PORT;                 /* swe.c .bss */

enum { FP_MAGIC = 0x50504631, FL_N = 48 };   /* 'FPP1' */
enum { FL_ADD = 1, FL_INST, FL_RES, FL_REFUSED, FL_MISSED, FL_REVAL, FL_SIM, FL_ORPHAN, FL_NEW, FL_LOAD, FL_SEASON,
       FL_LEG, FL_LEGX };                /* (FL_LEGX: the leg's e.t. (id) and penalties (y), home | away << 8, FFFFh none) */
struct fp_logent { u8 code, unit; int8_t rc; u8 x; u16 id, y; };
struct fp_st {
    u32 magic;
    u8 season, loaded, tadded, nlog;    /* (tadded: FPORT_TEST's fixtures queued this season) */
    u16 leg[2][4];                      /* this tie's legs as played: home team word, away, home goals (90'), away */
    u16 et[2], pens[2];                 /* the deciding leg's e.t. goals / penalties (FFFFh none), its home first */
    u8 nleg, pad[3];
    struct fp_logent log[FL_N];
};
extern struct fp_st FP_ST;              /* swe.c .bss */

typedef char fp_st_size_is[sizeof(struct fp_st) == FP_ST_SZ ? 1 : -1];   /* (swe.c's FP_ST: fpad.py ST_SIZE) */

/* the slot-4 windows (fport.py, written by fpad.py): FP_FMAP[team file] = country index (FFh none); FP_DIV rows by
   country then division, FP_NDIV of them; FP_SET their (shared) window lists. (volatile reads: the bytes are put after the
   link: plain data, never const - the compiler must not fold the placeholders) */
#define FP_DATA __attribute__((section(".data")))
#ifndef FP_NDIV_
#define FP_NDIV_ 1
#define FP_NSET_ 1
#endif
u8 FP_FMAP[256] FP_DATA;
u8 FP_DIV[FP_NDIV_][4] FP_DATA;         /* country, division, its window list's offset in FP_SET (u16) */
u8 FP_SET[FP_NSET_] FP_DATA;            /* window lists: n, then n x (B, E) - E FFh = none */
u16 FP_NDIV FP_DATA;
#ifdef FPORT_TEST
u8 FP_TEST[FP_NTEST_][7] FP_DATA;   /* (test builds: the probe's entries, fpad.test_entries' form) */
u16 FP_NTEST FP_DATA;
/* MC 14/11 (SR_PORT_WINDOWS 24: reserved()'s window buffer +32 B): the least free game stack seen at fp_step's entry
   (ESP - the game's _STACKLOW, its pointer at obj2+0xC3178; fp_step runs on the game's own 4 KB stack) - fpgate checks
   it against the port's deepest static chain + 512 B */
extern u32 FP_STKLOWP[1];
u32 FP_STKFREE FP_DATA = 0xFFFFFFFFu;
static void stk_probe(void)
{
    u32 e;
    __asm__ volatile ("movl %%esp, %0" : "=r"(e));
    e -= FP_STKLOWP[0];
    if (e < FP_STKFREE) FP_STKFREE = e;
}
#endif

/* fp_et's capture of the 90 minutes (below) */
#define FP_G90_NONE 0xFFFF                /* (MC 14/11 guard 2: no capture since the last use / install) */
u16 FP_G90[2] FP_DATA __attribute__((used)) = { FP_G90_NONE, FP_G90_NONE };

static void flog(u8 code, i32 rc, u16 id, u16 y)
{
    struct fp_logent *e = &FP_ST.log[FP_ST.nlog % FL_N];
    e->code = code; e->unit = (u8)GP_WK; e->rc = (int8_t)rc; e->x = FP_ST.nlog < 255 ? 0 : 1; e->id = id; e->y = y;
    if (FP_ST.nlog < 255) FP_ST.nlog++;
}

/* ---- the career calendar ---- */
static i32 cal_n(void) { return FP_CAL[-4] | FP_CAL[-3] << 8; }
static i32 cal_next(i32 o) { return o + (FP_CAL[o + 2] | FP_CAL[o + 3] << 8); }

/* rule 1: the career club's league plays that unit (slot 0 = the league); other clubs: never asked a league match */
static i32 h_league(void *ctx, u16 team, u16 unit)
{
    (void)ctx;
    if (team != GP_MGR) return 0;
    for (i32 k = 0, o = 0; k < cal_n(); k++, o = cal_next(o)) {
        if (!(FP_CAL[o + 2] | FP_CAL[o + 3])) break;
        if (FP_CAL[o] == 0 && FP_CAL[o + 1] == unit) return 1;
    }
    return 0;
}

static i32 h_prev(void *ctx, u16 unit)  /* the game's advance before unit: the latest calendar week below it */
{
    (void)ctx;
    i32 best = -1;
    for (i32 k = 0, o = 0; k < cal_n(); k++, o = cal_next(o)) {
        if (!(FP_CAL[o + 2] | FP_CAL[o + 3])) break;
        if (FP_CAL[o + 1] < unit && FP_CAL[o + 1] > best) best = FP_CAL[o + 1];
    }
    return best;
}

static u16 next_unit(u16 unit)          /* the game's next advance after unit, SR_PORT_NONE none */
{
    i32 best = SR_PORT_NONE;
    for (i32 k = 0, o = 0; k < cal_n(); k++, o = cal_next(o)) {
        if (!(FP_CAL[o + 2] | FP_CAL[o + 3])) break;
        if (FP_CAL[o + 1] > unit && FP_CAL[o + 1] < best) best = FP_CAL[o + 1];
    }
    return (u16)best;
}

/* rule 6: the career club's division's windows, exactly (fport's; the conditional ones on: the static superset - a conditional window, the supercup's
   'entrant' / the Coppa D's 'alive', counted as on; a refusal then plays the fixture as simulated, never a clash) */
static i32 h_windows(void *ctx, u16 team, u16 (*out)[2], i32 max)
{
    (void)ctx;
    if (team != GP_MGR) return 0;
    const u8 c = FP_FMAP[team & 0xFF];
    const u16 d = FP_CDIV[0];       /* (the career club's division now: the game's D6CDC - gplay's GP_IN.mdiv is set
                                       only by gp_setup at the league's end, stale before: world_fport_sd, Serie D) */
    i32 n = 0;
    for (u32 i = 0; i < FP_NDIV; i++)
        if (FP_DIV[i][0] == c && FP_DIV[i][1] == d) {
            const u8 *w = FP_SET + (FP_DIV[i][2] | FP_DIV[i][3] << 8);
            for (i32 k = 0; k < w[0] && n < max; k++, n++) {
                out[n][0] = w[1 + 2 * k];
                out[n][1] = w[2 + 2 * k] == 0xFF ? SR_PORT_NONE : w[2 + 2 * k];
            }
            n = w[0];                   /* (the true count: past max the engine refuses - fpad.py asserts <= max) */
            break;
        }
    return n;
}

/* a fixture without the career club: a result from the match id (no running generator), decided by its level */
static u32 fmix(u32 h) { h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15; h *= 0x846CA68Bu; return h ^ (h >> 16); }
static i32 h_sim(void *ctx, const sr_port_fixture *f, sr_port_result *r)
{
    (void)ctx;
    const u32 h = fmix(f->match_id ^ 0x5F0A7u ^ (u32)FP_SEASON << 24);
    r->match_id = f->match_id;
    r->g90[0] = (u8)(h % 4); r->g90[1] = (u8)(h >> 4 & 3);
    r->g90b[0] = r->g90b[1] = 0;
    r->get[0] = r->get[1] = r->pens[0] = r->pens[1] = 0xFF;
    r->cards[0] = r->cards[1] = 0;
    r->status = 0;
    i32 a = r->g90[0], b = r->g90[1];
    if (f->legs == 2) {                 /* (leg 2: the first leg's away side at home; aggregate level -> one more) */
        r->g90b[0] = (u8)(h >> 8 & 3); r->g90b[1] = (u8)(h >> 12 & 3);
        a += r->g90b[1]; b += r->g90b[0];
        if (a == b) { r->g90b[0]++; b++; }
    } else if (a == b && f->level) {    /* (one match level: penalties) */
        r->get[0] = r->get[1] = 0;
        r->pens[0] = (u8)(4 + (h >> 20 & 1)); r->pens[1] = (u8)(4 + !(h >> 20 & 1));
        a += r->pens[0]; b += r->pens[1];
    }
    r->winner = a > b ? 0 : 1;
    flog(FL_SIM, 0, (u16)f->match_id, (u16)(r->g90[0] | r->g90[1] << 4 | r->winner << 8));
    return 0;
}

static void h_done(void *ctx, const sr_port_fixture *f, const sr_port_result *r)
{
    (void)ctx;                          /* (P2: the log; the producers' outcomes - P4 conti, P7 trophies - by kind) */
    flog(FL_RES, f->kind, (u16)f->match_id, (u16)(r->winner | r->status << 4 | f->kind << 8));
}

static const sr_port_host HOST = { h_league, h_sim, h_done, h_prev, h_windows, 0 };

static int valid(void) { return FP_ST.magic == FP_MAGIC && FP_ST.season == FP_SEASON; }

/* MC 1: never inferred from a season mismatch. The three hooks only ARM (FP_ARM + why): they run where GP_MGR / GP_WK
   are not yet this career's (a load's ProcessCareerFile, a new career's defaults, InitializeNewSeason's pg_fix - also
   run by InitCareer, so arming is idempotent); the first fp_step after them (sc_step_c: GP_MGR, GP_WK, FP_SEASON current)
   initialises. A state neither armed nor FP_MAGIC + this season: the port is off. */
enum { FP_ARM = 0x4D524146 };           /* 'FARM' */
static void arm(u8 why) { FP_ST.magic = FP_ARM; FP_ST.loaded = why; }
void fp_new(void) { arm(FL_NEW); }      /* engine.after_new: a new career */
void fp_load(void) { arm(FL_LOAD); }    /* engine.after_process: a career load (MC 2: the flag -> revalidate first) */
void fp_season(void) { if (FP_ST.magic == FP_MAGIC || FP_ST.magic == FP_ARM) arm(FL_SEASON); }   /* gplay pg_season's end (GP_PSEAS): pg_fix, InitializeNewSeason */

static void fresh(void)
{
    const u8 why = FP_ST.loaded;
    sr_port_init(&FP_PORT, GP_MGR, (u16)GP_WK, SR_PORT_NONE, 0);   /* (s4first NONE: the host's windows - plan 1) */
    FP_ST.magic = FP_MAGIC; FP_ST.season = FP_SEASON; FP_ST.tadded = 0; FP_ST.nleg = 0; FP_ST.nlog = 0;
    GP_PMID = 0;
    FP_ST.loaded = why == FL_LOAD;      /* (interim before P5: a load's queue starts empty; the flag still runs the
                                           revalidate path, so 2a-2c hold once P5 restores the queue) */
    flog(why, 0, 0, FP_SEASON);          /* (y: the season initialised - the gate checks it is the one played) */
}

#ifdef FPORT_TEST
static void test_add(void)              /* the probe's entries as port fixtures (unit1, unit2, legs, level, flags, opp,
                                           file): flags 1 neutral, 4 the career club away */
{
    FP_ST.tadded = 1;
    for (u32 i = 0; i < FP_NTEST; i++) {
        const u8 *e = FP_TEST[i];
        const int me = GP_MGR >> 8, o = e[5] != 0xFF ? e[5] : (me ? 0 : 1);
        const u16 opp = (u16)((e[6] ? e[6] : GP_MGR & 0xFF) | o << 8);
        sr_port_fixture f;
        volatile u8 *b = (volatile u8 *)&f;   /* (volatile: no memset for clang to emit) */
        for (u32 j = 0; j < sizeof f; j++) b[j] = 0;
        f.match_id = 0x7E000000u | (u32)FP_SEASON << 8 | i;
        f.unit1 = e[0]; f.unit2 = e[1]; f.legs = e[2];
        f.level = e[3];
        f.neutral = e[4] & 1;
        f.home = e[4] & 4 ? opp : GP_MGR; f.away = e[4] & 4 ? GP_MGR : opp;
        f.lfile = (u8)GP_MGR; f.kind = 0xFE; f.prev_id = 0xFFFF; f.comp_id = 0xFFFF; f.label_id = 0xFFFF;
        flog(FL_ADD, sr_port_add(&FP_PORT, &HOST, &f), (u16)f.match_id, (u16)(f.unit1 | f.unit2 << 8));
    }
}
#endif

/* ---- slot 4 (gplay's GP_ST.ko[0]) ---- */
static int ko_this(void)                /* ko[0] holds a contest of this season (gplay's sc_free / sc_busy test) */
{
    return *(const u16 *)GP_GST == C_MAGIC && KW(0) == C_MAGIC && KB(O_SEASON) == GP_SEAS;
}
static u32 live(void)                   /* slot 4 holds a K_PORT tie of this season: 1 undecided, 2 decided, 0 none */
{
    if (!ko_this() || KB(O_KIND) != C_KPORT) return 0;
    return KB(O_TW) == C_NOC ? 1 : 2;
}
static const u8 *sct_entry(u8 key)      /* GP_SCT's entry for a country (the career club's file) / C_SCUEFA, 0 = none */
{
    if (!GP_SCT) return 0;
    for (int i = 0; i < GP_SCT[0]; i++)
        if (GP_SCT[1 + C_SCE * i] == key) return GP_SCT + 1 + C_SCE * i;
    return 0;
}
static u32 install(const sr_port_fixture *f)   /* slot 4's contest for the fixture: 1 built, 0 slot busy */
{
    if (ko_this() && KB(O_TW) == C_NOC) return 0;   /* (gplay's sc_free: this season's contest still to decide) */
    const u8 *nm = GP_MGR ? sct_entry((u8)GP_MGR) : 0;   /* (no names of the fixture's own yet - P6: the supercup
                                           entry's calendar names or none; ko_one copies 8 bytes: never a null pointer) */
    if (!nm) nm = sct_entry(C_SCUEFA);
    static const u8 zero[8];
    ((ko_one_fn *)GP_PAPI[0])((struct gp_ko *)KO0, f->home, f->away, f->unit1, f->unit2, f->legs, C_KPORT, f->level,
                             f->lfile, nm ? nm + 20 : zero);
    if (f->neutral) KO0[O_RS + 2] = C_NEUTRAL;
    FP_G90[0] = FP_G90[1] = FP_G90_NONE;   /* (guard 2: a capture only from this tie's own matches) */
    FP_ST.pad[0] = 0;
    return 1;
}

u32 fp_step(void)                       /* sc_step_c's head: 1 = the career club's fixture built into ko[0] */
{
#ifdef FPORT_TEST
    stk_probe();
#endif
    if (FP_CWB != FP_WORLD) return 0;   /* (P2: the windows / file map are this world's only - another world: off) */
    if (FP_ST.magic == FP_ARM) fresh();
    if (!valid()) return 0;             /* (no explicit init this career / season: the port is off - never inferred) */
    const u16 unit = (u16)GP_WK, next = next_unit(unit);
    if (FP_ST.loaded) {                 /* MC 2a: the first advance after a load, before the poll */
        i32 bad = -1, rc = sr_port_revalidate(&FP_PORT, &HOST, &bad);
        flog(FL_REVAL, rc, bad >= 0 ? (u16)FP_PORT.f[bad].match_id : 0, 0);
        if (rc) flog(FL_MISSED, sr_port_missed(&FP_PORT, &HOST, unit, next), 0, 0);   /* (2b: never dropped silently) */
        FP_ST.loaded = 0;
    }
#ifdef FPORT_TEST
    if (!FP_ST.tadded) test_add();
#endif
    i32 rc = sr_port_advance(&FP_PORT, &HOST, unit);
    if (rc < 0) flog(FL_SIM, rc, 0, 0);
    for (int tries = 0; tries < 4; tries++) {
        sr_port_fixture f;
        rc = sr_port_poll(&FP_PORT, &HOST, unit, next, &f);
        if (rc == 1) {
            if (live() == 1) return 0;  /* (installed already, being played: slot 4 held) */
            const u32 ok = install(&f);
            flog(FL_INST, (i32)ok, (u16)f.match_id, (u16)(f.unit1 | f.unit2 << 8));
            FP_ST.nleg = 0;
            return ok;
        }
        if (rc != SR_PORT_E_MISSED && rc != SR_PORT_E_SLOT4_RESERVED) {
            if (rc < 0) flog(FL_REFUSED, rc, 0, 0);
            return 0;
        }
        flog(FL_REFUSED, rc, 0, 0);     /* `[port] refused`: the harness reads it */
        flog(FL_MISSED, sr_port_missed(&FP_PORT, &HOST, unit, next), 0, 0);
    }
    return 0;
}

/* cseg_2AE97's extra time (`call cseg_2B81B`, two sites, fpad.py fp_et_sites): its D1 / D2 = this match's 90-minute
   goals. After it, D1 / D2 = the match's total and D3 / D4 the e.t. goals on the single match's path but the aggregate
   on a second leg's (the 90 minutes not recoverable there): kept here, read by fp_leg when D7 says e.t. was played.
   Chained: FP_ETX = what the call reached before (cseg_2B81B, or BPLACE_FORCE's bf_et in its test builds). */
extern const u16 FP_D1W, FP_D2W;        /* (D1 / D2 words: the pseudo registers, obj2) */
extern void FP_ETX(void);
#ifndef FP_ETFORCE
__attribute__((naked)) void fp_et(void)
{
    __asm__ volatile("push %eax\n\t"
                     "movw FP_D1W, %ax\n\t"
                     "movw %ax, FP_G90\n\t"
                     "movw FP_D2W, %ax\n\t"
                     "movw %ax, FP_G90+2\n\t"
                     "pop %eax\n\t"
                     "jmp FP_ETX");
}
#else
extern u16 FP_D3W, FP_D4W;              /* (FPORT_ETFORCE test builds: e.t. 1-0 to the home side, after FP_ETX - with
                                           BPLACE_FORCE's level 90 minutes: an e.t. decided without penalties) */
__attribute__((naked)) void fp_et(void)
{
    __asm__ volatile("push %eax\n\t"
                     "movw FP_D1W, %ax\n\t"
                     "movw %ax, FP_G90\n\t"
                     "movw FP_D2W, %ax\n\t"
                     "movw %ax, FP_G90+2\n\t"
                     "pop %eax\n\t"
                     "call FP_ETX\n\t"
                     "movw $1, FP_D3W\n\t"
                     "movw $0, FP_D4W\n\t"
                     "ret");
}
#endif

/* gp_rec, every match of ours (GP_PLEG): a K_PORT one in ko[0] -> its goals from cseg_2AE97's D1..D7 at its end (D1 /
   D2 the goals with e.t., D5 / D6 the penalties, D7 4 e.t. played, 8 penalties; the 90 minutes from fp_et), A1 (the
   home side), A2 */
void fp_leg(void)
{
    if (GP_K != 0 || KB(O_KIND) != C_KPORT) return;
    GP_WK = FP_CAL[FP_CALCUR + 1];      /* (gplay's gp_week: the unit flog stamps) */
    if (!valid()) return;
    u16 d[7];                           /* (d[2] / d[3] unused: D3 / D4 depend on the path, fp_et) */
    for (u32 j = 0; j < 7; j++) d[j] = *(const u16 *)(FP_D1R + 4 * j);
    const u16 ha = *(const u16 *)FP_A1R, aw = *(const u16 *)FP_A2R;
    const u32 i = FP_ST.nleg < 2 ? FP_ST.nleg : 1;
    const int et = d[6] & 4, pens = d[6] & 8;   /* (D7: 4 e.t. played, 8 penalties; D1 / D2 the total, e.t. included) */
    if (et && (FP_G90[0] == FP_G90_NONE || FP_G90[1] == FP_G90_NONE)) {   /* (guard 2: e.t. with no capture - never a
                                           total minus a stale 90 minutes: the leg refused, logged) */
        flog(FL_REFUSED, SR_PORT_E_RESULT, ha, 0xE790);
        FP_ST.pad[0] = 1;               /* (fp_done: this tie's result not sent) */
        return;
    }
    FP_ST.leg[i][0] = ha; FP_ST.leg[i][1] = aw;
    FP_ST.leg[i][2] = et ? FP_G90[0] : d[0]; FP_ST.leg[i][3] = et ? FP_G90[1] : d[1];   /* (the 90 minutes: fp_et's) */
    FP_ST.et[0] = et ? (u16)(d[0] - FP_G90[0]) : 0xFFFF; FP_ST.et[1] = et ? (u16)(d[1] - FP_G90[1]) : 0xFFFF;
    FP_G90[0] = FP_G90[1] = FP_G90_NONE;   /* (consumed) */
    FP_ST.pens[0] = pens ? d[4] : 0xFFFF; FP_ST.pens[1] = pens ? d[5] : 0xFFFF;
    FP_ST.nleg = (u8)(i + 1);
    GP_PMID = FP_ST.nleg;               /* (obj2: the gate's mid-tie save - 1 = the first leg played) */
    flog(FL_LEG, (i32)i, ha, (u16)(FP_ST.leg[i][2] | FP_ST.leg[i][3] << 8));
#ifdef FPORT_TEST                       /* (the gates' e.t. / penalties check: test builds' log only) */
    flog(FL_LEGX, (i32)i, et ? (u16)(FP_ST.et[0] | FP_ST.et[1] << 8) : 0xFFFF,
         pens ? (u16)(FP_ST.pens[0] | FP_ST.pens[1] << 8) : 0xFFFF);
#endif
}

/* gp_rec_c: the K_PORT tie decided -> the pending fixture's result */
void fp_done(void)
{
    if (!valid()) return;
    const u16 t0 = KW(O_TEAM), t1 = KW(O_TEAM + 2);
    const u8 tw = KB(O_TW);             /* (the winner's list index: its side 0 / 1, FFh none) */
    const u16 o[3] = { t0, t1, tw == C_NOC ? 0xFF : KW(O_TEAM + 2 * tw) == t0 ? 0 : 1 };
    i32 p = -1;                         /* (pending: the installed fixture's match id, 0 = none) */
    for (i32 j = 0; FP_PORT.pending && j < FP_PORT.n; j++)
        if (FP_PORT.f[j].match_id == FP_PORT.pending) p = j;
    GP_PMID = 0;
    if (p < 0 || FP_ST.nleg == 0) {
        flog(FL_ORPHAN, (i32)FP_ST.nleg, o[0], o[1]);   /* (interim before P5: a tie from before a load) */
        return;
    }
    if (FP_ST.pad[0]) {                 /* (a leg refused by fp_leg: no result sent - logged there) */
        flog(FL_REFUSED, SR_PORT_E_RESULT, (u16)FP_PORT.f[p].match_id, 0xE791);
        FP_ST.nleg = 0; FP_ST.pad[0] = 0;
        return;
    }
    const sr_port_fixture *f = &FP_PORT.f[p];
    sr_port_result r;
    volatile u8 *b = (volatile u8 *)&r;
    for (u32 j = 0; j < sizeof r; j++) b[j] = 0;
    r.match_id = f->match_id;
    for (u32 l = 0; l < FP_ST.nleg; l++) {   /* (each leg as played, that leg's home first) */
        u8 *g = l ? r.g90b : r.g90;
        g[0] = (u8)FP_ST.leg[l][2]; g[1] = (u8)FP_ST.leg[l][3];
    }
    r.get[0] = FP_ST.et[0] == 0xFFFF ? 0xFF : (u8)FP_ST.et[0];
    r.get[1] = FP_ST.et[1] == 0xFFFF ? 0xFF : (u8)FP_ST.et[1];
    r.pens[0] = FP_ST.pens[0] == 0xFFFF ? 0xFF : (u8)FP_ST.pens[0];
    r.pens[1] = FP_ST.pens[1] == 0xFFFF ? 0xFF : (u8)FP_ST.pens[1];
    r.status = 0;
    r.winner = o[2] == 0xFF ? 0 : (u8)o[2];
    const i32 rc = sr_port_result_in(&FP_PORT, &HOST, &r);
    if (rc) flog(FL_REFUSED, rc, (u16)f->match_id, (u16)(r.winner | FP_ST.nleg << 4));   /* (never overridden) */
    FP_ST.nleg = 0;
}
