/* fpad.c -- 4.2 the fixture port's adapter (P2; internal/handoff/motore-fixport-plan.md 1b, MC review 14/11), linked
 * by fpad.py at obj4 + swreg.FPORT_AT. The engine's sr_port (tools/swce/sr_port.c: its one copy in the exe) queues
 * the season's non-league fixtures; at each calendar advance (gplay's sc_step_c head, GP_PSTEP) fp_step installs the
 * career club's due fixture in slot 4 through gplay (GP_PAPI.install: ko_one, kind K_PORT), every other one is
 * simulated (fp_sim); the played tie comes back through gp_rec (GP_PLEG: each match's goals, GP_PDONE: the tie
 * decided) as an sr_port_result, checked by the engine (sr_port_result_in: a mismatch refused, never overridden).
 *
 * State: FP_PORT (sr_port, 2368 B) and FP_ST in swe.c's .bss (DOS/4GW zeroes no tail): valid only under FP_MAGIC and
 * the season, written only by fp_new (a new career: engine.after_new), fp_load (a load: engine.after_process, which
 * also sets FP_ST.loaded - MC 2) and the season end (fp_season, gp_end_c's hook), which arm it; fp_step inits. fp_step with FP_ST.loaded first
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

struct gp_ko;
struct gp_papi { u32 (*install)(u16, u16, u32, u32, u32, u32, u32, u32, const u8 *); u32 (*live)(void);
                 void (*kinfo)(const struct gp_ko *, u16 *); u32 (*mdiv)(void); const struct gp_ko *ko0; };
extern const struct gp_papi GP_PAPI;    /* gplay.c (obj1) */
extern u32 GP_WK;                       /* gplay.c: the current calendar entry's week (the unit) */
extern u16 GP_MGR;                      /* gplay.c: the career club's team word */
extern u8 GP_SEAS;                      /* gplay.c: seasonPlaying */
extern u8 FP_CAL[];                     /* obj2: the career calendar (count word at -4, entries: slot, week, len word) */
extern sr_port FP_PORT;                 /* swe.c .bss */

enum { FP_MAGIC = 0x50504631, FL_N = 48 };   /* 'FPP1' */
enum { FL_ADD = 1, FL_INST, FL_RES, FL_REFUSED, FL_MISSED, FL_REVAL, FL_SIM, FL_ORPHAN, FL_NEW, FL_LOAD, FL_SEASON,
       FL_LEG };
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
#endif

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
    const u16 d = (u16)GP_PAPI.mdiv();
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
    const u32 h = fmix(f->match_id ^ 0x5F0A7u ^ (u32)GP_SEAS << 24);
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

static int valid(void) { return FP_ST.magic == FP_MAGIC && FP_ST.season == GP_SEAS; }

/* MC 1: never inferred from a season mismatch. The three hooks only ARM (FP_ARM + why): they run where GP_MGR / GP_WK
   are not yet this career's (a load's ProcessCareerFile, a new career's defaults, gp_end_c - called once per country's
   season end, so arming is idempotent); the first fp_step after them (sc_step_c: GP_MGR, GP_WK, GP_SEAS current)
   initialises. A state neither armed nor FP_MAGIC + this season: the port is off. */
enum { FP_ARM = 0x4D524146 };           /* 'FARM' */
static void arm(u8 why) { FP_ST.magic = FP_ARM; FP_ST.loaded = why; }
void fp_new(void) { arm(FL_NEW); }      /* engine.after_new: a new career */
void fp_load(void) { arm(FL_LOAD); }    /* engine.after_process: a career load (MC 2: the flag -> revalidate first) */
void fp_season(void) { if (FP_ST.magic == FP_MAGIC || FP_ST.magic == FP_ARM) arm(FL_SEASON); }   /* gp_end_c (GP_PSEAS) */

static void fresh(void)
{
    const u8 why = FP_ST.loaded;
    sr_port_init(&FP_PORT, GP_MGR, (u16)GP_WK, SR_PORT_NONE, 0);   /* (s4first NONE: the host's windows - plan 1) */
    FP_ST.magic = FP_MAGIC; FP_ST.season = GP_SEAS; FP_ST.tadded = 0; FP_ST.nleg = 0; FP_ST.nlog = 0;
    FP_ST.loaded = why == FL_LOAD;      /* (interim before P5: a load's queue starts empty; the flag still runs the
                                           revalidate path, so 2a-2c hold once P5 restores the queue) */
    flog(why, 0, 0, 0);
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
        f.match_id = 0x7E000000u | (u32)GP_SEAS << 8 | i;
        f.unit1 = e[0]; f.unit2 = e[1]; f.legs = e[2];
        f.level = e[3];
        f.neutral = e[4] & 1;
        f.home = e[4] & 4 ? opp : GP_MGR; f.away = e[4] & 4 ? GP_MGR : opp;
        f.lfile = (u8)GP_MGR; f.kind = 0xFE; f.prev_id = 0xFFFF; f.comp_id = 0xFFFF; f.label_id = 0xFFFF;
        flog(FL_ADD, sr_port_add(&FP_PORT, &HOST, &f), (u16)f.match_id, (u16)(f.unit1 | f.unit2 << 8));
    }
}
#endif

static const u8 *names_of(const sr_port_fixture *f) { (void)f; return 0; }   /* (P2: gplay's own names; P6 views) */

u32 fp_step(void)                       /* sc_step_c's head: 1 = the career club's fixture built into ko[0] */
{
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
            if (GP_PAPI.live() == 1) return 0;   /* (installed already, being played: slot 4 held) */
            const u32 ok = GP_PAPI.install(f.home, f.away, f.unit1, f.unit2, f.legs, f.level, f.neutral, f.lfile,
                                           names_of(&f));
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

/* gp_rec, every K_PORT match: d = cseg_2AE97's D1..D7 at its end (D1 / D2 the goals with e.t., D3 / D4 the e.t. goals,
   D5 / D6 the penalties, D7 bit 4 e.t. played, 8 penalties), GP_A (A1: the home side), GP_B, legs left */
void fp_leg(const struct gp_ko *k, const u16 *d)
{
    (void)k;
    if (!valid()) return;
    const u32 i = FP_ST.nleg < 2 ? FP_ST.nleg : 1;
    const int et = d[6] & 4, pens = d[6] & 8;
    FP_ST.leg[i][0] = d[7]; FP_ST.leg[i][1] = d[8];
    FP_ST.leg[i][2] = (u16)(d[0] - (et ? d[2] : 0)); FP_ST.leg[i][3] = (u16)(d[1] - (et ? d[3] : 0));
    FP_ST.et[0] = et ? d[2] : 0xFFFF; FP_ST.et[1] = et ? d[3] : 0xFFFF;
    FP_ST.pens[0] = pens ? d[4] : 0xFFFF; FP_ST.pens[1] = pens ? d[5] : 0xFFFF;
    FP_ST.nleg = (u8)(i + 1);
    flog(FL_LEG, (i32)i, d[7], (u16)(FP_ST.leg[i][2] | FP_ST.leg[i][3] << 8));
}

/* gp_rec_c: the K_PORT tie decided -> the pending fixture's result */
void fp_done(const struct gp_ko *k)
{
    if (!valid()) return;
    u16 o[5];
    GP_PAPI.kinfo(k, o);
    const i32 p = (i32)FP_PORT.pending;
    if (FP_PORT.pending == 0xFFFFFFFFu || p < 0 || p >= FP_PORT.n || FP_ST.nleg == 0) {
        flog(FL_ORPHAN, (i32)FP_ST.nleg, o[0], o[1]);   /* (interim before P5: a tie from before a load) */
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
