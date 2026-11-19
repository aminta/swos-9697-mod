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
 * P5 (the FP save section, fpsave.c): a load restores the queue and the tie in progress (FL_PLOAD); a refused or
 * absent section starts an empty queue - a K_PORT tie left in slot 4 is then played by gplay and its result logged
 * as an orphan (FL_ORPHAN), not credited. */
#include "fpad.h"
#include "swce/sr_port.c"

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
extern u8 FP_CAL[];                     /* obj2: the career calendar (count word at -4, entries: slot, week, len word) */

enum { FP_NREV = 4 };                   /* (REVAL: failing fixtures logged one by one, at most) */
enum { FL_ADD = 1, FL_INST, FL_RES, FL_REFUSED, FL_MISSED, FL_REVAL, FL_SIM, FL_ORPHAN, FL_NEW, FL_LOAD, FL_SEASON,
       FL_LEG, FL_LEGX, FL_PLOAD, FL_MLOPEN, FL_MLSIM, FL_MLADD, FL_MLDONE };   /* (15..18: fpml.c's, the mini-league) */
enum { FP_K_ML = 0x4D, FP_ML_KIND = 0x4D4C };   /* a mini-league fixture: its kind, its match_id >> 16 (| season << 8 | (id - 1) << 4 | md) */
/* fpml.c (the mini-league producer, its own unit in obj4's FPML band; linked after this one): its entries, bound by
   fpad.py - 0 in a build without it */
void (*FP_MLRES)(const sr_port_fixture *, const sr_port_result *) __attribute__((section(".data")));   /* fp_ml_result */
u32 (*FP_MLBUSY)(u16 team) __attribute__((section(".data")));     /* fp_ml_busy: the club is in a running mini-league stage */
void (*FP_MLLOAD)(void) __attribute__((section(".data")));        /* fp_ml_loaded: the instances a load / reset left, checked */
      /* (FL_LEGX: the leg's e.t. (id) and penalties (y), home | away << 8, FFFFh none) */
                                         /* (FL_PLOAD, P5: the FP item at a load - rc the fixtures loaded / 0 none / < 0 refused, y the tie's legs played) */
/* (FP_ST, struct fp_st, FP_MAGIC / FP_ARM: fpad.h) */

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
#ifndef FP_MLF_INIT
#define FP_MLF_INIT {{0}}
#define FP_MLSEED_INIT 0
#endif
u8 FP_MLF[8][4] FP_DATA = FP_MLF_INIT;  /* (lane 3, fpml.h: forced scores (id, md, hg, ag) of the mini-league's matches) */
u32 FP_MLSEED FP_DATA = FP_MLSEED_INIT;
static int ml_forced(u32 match_id, u8 *g)   /* a forced row for that mini-league match: its goals, home first */
{
    if (match_id >> 16 != FP_ML_KIND) return 0;
    for (u32 i = 0; i < 8; i++)
        if (FP_MLF[i][0] == (match_id >> 4 & 0xF) + 1 && FP_MLF[i][1] == (match_id & 0xF)) {
            g[0] = FP_MLF[i][2]; g[1] = FP_MLF[i][3];
            return 1;
        }
    return 0;
}
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
    if (!GP_MGR || team != GP_MGR) return 0;   /* (S6a: GP_MGR 0 = no manager's club) */
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
    if (!GP_MGR || team != GP_MGR) return 0;   /* (S6a: GP_MGR 0 = no manager's club) */
    const u8 c = FP_FMAP[team & 0xFF];
    const u16 d = FP_CDIV[0];       /* (the career club's division now: the game's D6CDC - gplay's GP_IN.mdiv is set
                                       only by gp_setup at the league's end, stale before: world_fport_sd, Serie D) */
    i32 n = 0;
    for (u32 i = 0; i < FP_NDIV; i++)
        if (FP_DIV[i][0] == c && FP_DIV[i][1] == d) {
            const u8 *w = FP_SET + (FP_DIV[i][2] | FP_DIV[i][3] << 8);
            /* G3, the live condition (CONVENTIONS: the general rule, no competition named): a club in a running
               mini-league stage is not in its division's season-end play-offs - the windows open to the season's end
               (E none: fport's dplay / play-off / play-out ones, [L, END]) are off for it */
            const u32 busy = FP_MLBUSY ? FP_MLBUSY(team) : 0;
            for (i32 k = 0; k < w[0]; k++) {
                if (busy && w[2 + 2 * k] == 0xFF) continue;
                if (n < max) {
                    out[n][0] = w[1 + 2 * k];
                    out[n][1] = w[2 + 2 * k] == 0xFF ? SR_PORT_NONE : w[2 + 2 * k];
                }
                n++;                    /* (the true count: past max the engine refuses - fpad.py asserts <= max) */
            }
            break;
        }
    return n;
}

/* the league's last unit L: the latest slot-0 entry of the career calendar (0 = none) */
static u16 last_league(void)
{
    u16 best = 0;
    for (i32 k = 0, o = 0; k < cal_n(); k++, o = cal_next(o)) {
        if (!(FP_CAL[o + 2] | FP_CAL[o + 3])) break;
        if (FP_CAL[o] == 0 && FP_CAL[o + 1] > best) best = FP_CAL[o + 1];
    }
    return best;
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
    }
#ifdef FPORT_TEST
    if (ml_forced(f->match_id, r->g90)) { a = r->g90[0]; b = r->g90[1]; }   /* (FP_MLF: whoever plays it) */
#endif
    if (f->legs != 2 && a == b && f->level) {    /* (one match level: penalties) */
        r->get[0] = r->get[1] = 0;
        r->pens[0] = (u8)(4 + (h >> 20 & 1)); r->pens[1] = (u8)(4 + !(h >> 20 & 1));
        a += r->pens[0]; b += r->pens[1];
    }
    r->winner = a > b ? 0 : a < b || f->level ? 1 : 2;   /* (level NONE: a level score stands, winner 2) */
    flog(FL_SIM, 0, (u16)f->match_id, (u16)(r->g90[0] | r->g90[1] << 4 | r->winner << 8));
    return 0;
}

#ifdef FP_TSEQ
static void test_one(u32 i);
#endif
static void h_done(void *ctx, const sr_port_fixture *f, const sr_port_result *r)
{
    (void)ctx;                          /* (P2: the log; the producers' outcomes - P4 conti, P7 trophies - by kind) */
    flog(FL_RES, f->kind, (u16)f->match_id, (u16)(r->winner | r->status << 4 | f->kind << 8));
#ifdef FP_TSEQ                          /* (Q13 chain, test builds - FPORT_SEQ=1: the probe's next entry is added when the
                                           previous one's result is in, as a producer does; rule 5 accepts a tie next
                                           to a PLAYED one, never two pending adjacent ones - engine 05eea45) */
    if (f->kind == 0xFE && FP_ST.tadded && FP_ST.tadded < FP_NTEST) test_one(FP_ST.tadded++);
#endif
    if (f->kind == FP_K_ML && FP_MLRES) FP_MLRES(f, r);   /* (the mini-league: its match scored, the next one queued) */
}

static const sr_port_host HOST = { h_league, h_sim, h_done, h_prev, h_windows, 0 };

static int valid(void) { return FP_ST.magic == FP_MAGIC && FP_ST.season == FP_SEASON; }

/* MC 1: never inferred from a season mismatch. The three hooks only ARM (FP_ARM + why): they run where GP_MGR / GP_WK
   are not yet this career's (a load's ProcessCareerFile, a new career's defaults, InitializeNewSeason's pg_fix - also
   run by InitCareer, so arming is idempotent); the first fp_step after them (sc_step_c: GP_MGR, GP_WK, FP_SEASON current)
   initialises. A state neither armed nor FP_MAGIC + this season: the port is off. */
static void arm(u8 why) { FP_ST.magic = FP_ARM; FP_ST.loaded = why; }
void fp_new(void) { arm(FL_NEW); }      /* engine.after_new: a new career */
void fp_load(void) { arm(FL_LOAD); }    /* engine.after_process: a career load (MC 2: the flag -> revalidate first) */
void fp_season(void) { if (FP_ST.magic == FP_MAGIC || FP_ST.magic == FP_ARM) arm(FL_SEASON); }   /* gplay pg_season's end (GP_PSEAS): pg_fix, InitializeNewSeason */

/* ---- P5 (MC option A): the FP item - fp_save / fps_load (the load + the slot-4 cross-check) in fpsave.c, obj4
   FPORT2 (MC 15/11) ---- */
static void fresh(void)
{
    const u8 why = FP_ST.loaded;
    FP_ST.magic = FP_MAGIC; FP_ST.season = FP_SEASON; FP_ST.nlog = 0;
    FP_ST.loaded = why == FL_LOAD;      /* (MC 2a: revalidate before the first poll) */
    flog(why, 0, 0, FP_SEASON);          /* (y: the season initialised - the gate checks it is the one played) */
    if (why != FL_SEASON)               /* (the mini-league instances: none in a new career, the save's after a load - fpsave.c
                                           ml_load; a new season keeps the last one's, decided: its season byte says so) */
        for (u32 i = 0; i < FP_ML_SZ; i++) FP_ML[i] = 0;
    if (why == FL_LOAD) {               /* (P5: the FP item - fpsave.c; none or refused: an empty port, as fps_reset) */
        const i32 got = fps_load();
        flog(FL_PLOAD, got, 0, (u16)FP_ST.nleg);
        FP_ST.tadded = got > 0;         /* (FPORT_TEST: the loaded queue holds the test fixtures already) */
    } else
        fps_reset();
    if (FP_MLLOAD) FP_MLLOAD();         /* (fpml.c: FP_ML as the load / the reset left it, checked) */
}

/* ---- fpml.c's side of the port (the mini-league producer: obj4 FPML, linked after this unit) ---- */
void fp_log(u32 code, i32 rc, u32 id, u32 y) { flog((u8)code, rc, (u16)id, (u16)y); }
u32 fp_wake(void)                       /* the port usable now: 1 (an armed one initialised first, as fp_step would) */
{
    if (FP_CWB != FP_WORLD) return 0;
    if (FP_ST.magic == FP_ARM) { GP_WK = FP_CAL[FP_CALCUR + 1]; fresh(); }
    return (u32)valid();
}
/* one match of a mini-league as a port fixture: the career club's, one leg, level NONE, at L + off; 0 queued (or
   already there), else the rule's code */
i32 fp_ml_add(u32 match_id, u16 home, u16 away, u32 off)
{
    for (i32 j = 0; j < FP_PORT.n; j++)
        if (FP_PORT.f[j].match_id == match_id) return 0;
    sr_port_fixture f;
    volatile u8 *b = (volatile u8 *)&f;
    for (u32 j = 0; j < sizeof f; j++) b[j] = 0;
    f.match_id = match_id;
    f.unit1 = f.unit2 = (u16)(last_league() + off);
    f.legs = 1; f.level = SR_PORT_LV_NONE;
    f.home = home; f.away = away;
    f.lfile = (u8)GP_MGR; f.kind = FP_K_ML; f.prev_id = 0xFFFF; f.comp_id = 0xFFFF; f.label_id = 0xFFFF;
    const i32 rc = sr_port_add(&FP_PORT, &HOST, &f);
    flog(FL_MLADD, rc, (u16)match_id, (u16)(f.unit1 | f.unit2 << 8));
    return rc;
}

#ifdef FPORT_TEST
static void test_one(u32 i);
static void test_add(void)              /* the probe's entries as port fixtures (unit1, unit2, legs, level, flags, opp,
                                           file): flags 1 neutral, 4 the career club away */
{
    FP_ST.tadded = 1;                   /* (FP_TSEQ: the count of entries added - the first now, the rest from h_done) */
#ifdef FP_TSEQ
    if (FP_NTEST) test_one(0);
#else
    for (u32 i = 0; i < FP_NTEST; i++) test_one(i);
#endif
}
static void test_one(u32 i)
{
    {
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
const u8 *(*FP_NAMES)(u32 match_id) FP_DATA;   /* fpmlv.py binds it to fpv_calnames (obj3); 0 = no views in this build */
u32 (*FP_RND)(u32 match_id) FP_DATA;    /* fpmlv.py binds it to fpv_round (obj3): the fixture's round name, an rnames index
                                           (a mini-league's matchday: 'SUPERCOPPA SERIE C GIORNATA 2'); 0 = the game's own */
static u32 install(const sr_port_fixture *f)   /* slot 4's contest for the fixture: 1 built, 0 slot busy */
{
    if (ko_this() && KB(O_TW) == C_NOC) return 0;   /* (gplay's sc_free: this season's contest still to decide) */
    const u8 *own = FP_NAMES ? FP_NAMES(f->match_id) : 0;   /* (P6, lane 2: a mini-league fixture's own names - fpmlv.c
                                           fpv_calnames, 8 bytes as the supercup entry's +20; 0 = not one, or no views) */
    const u8 *nm = own || !GP_MGR ? 0 : sct_entry((u8)GP_MGR);   /* (the others: no names of their own yet - the supercup
                                           entry's calendar names or none; ko_one copies 8 bytes: never a null pointer) */
    if (!own && !nm) nm = sct_entry(C_SCUEFA);
    static const u8 zero[8];
    ((ko_one_fn *)GP_PAPI[0])((struct gp_ko *)KO0, f->home, f->away, f->unit1, f->unit2, f->legs, C_KPORT, f->level,
                             f->lfile, own ? own : nm ? nm + 20 : zero);
    if (f->neutral) KO0[O_RS + 2] = C_NEUTRAL;
    GP_GST[O_RN] = (u8)(FP_RND ? FP_RND(f->match_id) : 0);   /* (gp_rname: ko[0]'s game round 0 - the tie's only one; ko_one
                                           leaves the last contest's there) */
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
        i32 bad = -1, nbad = 0;         /* (MC 15/11: every failing fixture - the first FP_NREV ids, one entry each;
                                           y = how many failed; a PLAYED one is never failed by rules 1 / 6) */
        u32 ids[FP_NREV];
        const i32 rc = sr_port_revalidate_all(&FP_PORT, &HOST, &bad, &nbad, ids, FP_NREV);
        flog(FL_REVAL, rc, nbad ? (u16)ids[0] : 0, (u16)nbad);
        for (i32 i = 1; i < nbad && i < FP_NREV; i++) flog(FL_REVAL, rc, (u16)ids[i], (u16)nbad);
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
#ifdef FPORT_TEST
    {                                   /* (FP_MLF: a forced mini-league match, the career club's own - its goals as the
                                           port reads them, home first; test builds only) */
        u8 g[2];
        if (FP_PORT.pending && ml_forced(FP_PORT.pending, g)) { d[0] = g[0]; d[1] = g[1]; d[6] = 0; }
    }
#endif
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
    if (f->level == SR_PORT_LV_NONE)    /* (no decider: the winner is the score's - gplay's level 0 names the listed
                                           side on a level one; 2 = level, it stands) */
        r.winner = r.g90[0] > r.g90[1] ? 0 : r.g90[0] < r.g90[1] ? 1 : 2;
    const i32 rc = sr_port_result_in(&FP_PORT, &HOST, &r);
    if (rc) flog(FL_REFUSED, rc, (u16)f->match_id, (u16)(r.winner | FP_ST.nleg << 4));   /* (never overridden) */
    FP_ST.nleg = 0;
}
