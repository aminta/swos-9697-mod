/* fpml.c -- 4.2 the fixture port's MINI-LEAGUE producer (lane 1 of the Supercoppa Serie C; design
 * internal/handoff/supercoppa-c-design-20261116.md (a), interface tools/fpml.h), its own link unit in obj4's FPML band
 * (fpad.py links it after fpad.c). GENERIC: a stage is one row of FP_MLT (the pack's 'mini_leagues', compiled by
 * fpad.py) - n clubs given as [division, place] of the final tables, a schedule policy, points, tie-breaks, calendar
 * offsets from the league's last unit L. No division, file, club or name in this file; the Serie C specifics are the
 * Italian pack's row. The rules are the engine's (tools/swce/sr_stage.c: sr_mini_sched, sr_rr_table - their one copy
 * in the exe is this unit's).
 *
 * When (gplay.c's hooks, bound by fpad.py):
 * - GP_PNEED (gp_need_pre, the career league's last day): the career club holds an entrant place -> the other
 *   entrants' divisions, simulated now and kept (gplay's early simulations: the season end restores them).
 * - GP_PLEND (gp_pre_c's head, right after): fp_ml_open(0) - the career club is an entrant: the instance opens, md1
 *   is drawn, the stage runs (progress()).
 * - the port's result callback (fpad.c h_done -> fp_ml_result): the career club's match scored -> progress().
 * - GP_PEND (gp_end_c's head: the season end, after gp_season, before the S7 swap): fp_ml_open(1) - a stage with no
 *   instance (the career club not an entrant; an old save loaded after L) is opened, simulated and closed in one
 *   call; one left open is finished the same way; FP_MLDONE for every decided instance (lane 2's contract).
 * progress(): the matches the policy has decided so far, in order - one without the career club is scored at once
 * (fp_ml_sim: h_sim's hash of its match id, no decider), the career club's is queued as ONE port fixture (fpad.c
 * fp_ml_add: one leg, level NONE, unit L + off[md]) and the stage waits for its result; a fixture the port refuses is
 * simulated (the stage never stalls). All played: the table (sr_rr_table), the winner, state 2.
 *
 * State: FP_ML[FP_ML_N] (swe.c .bss; saved in the FP item's ML block, fpsave.c), instance i = row i. Valid only under
 * the port's own validity (FP_ST: magic + season); an instance of another season counts as none. */
#include "fpad.h"
#include "fpml.h"
#include "swce/sr_stage.c"

#ifndef FP_DATA                                 /* (host tests compile this file natively: -DFP_DATA=) */
#define FP_DATA __attribute__((section(".data")))
#endif
#ifndef FP_MLN_
#define FP_MLN_ 1
#endif
struct fp_mlrow FP_MLT[FP_MLN_] FP_DATA;        /* fpad.py puts the rows after the link (plain data, never const) */
u8 FP_MLTF[FP_MLN_] FP_DATA;                    /* each row's league team file (whose season end decides it) */
u16 FP_MLN FP_DATA;
void (*FP_MLDONE)(const struct fp_ml *) FP_DATA;   /* lane 2 (fpmlv.py binds fpv_done) */

#ifndef GP_GIN_HOST
extern u8 GP_GIN[];                             /* gplay.c GP_IN (obj2): nd, n[], t[][], sim[] at fpad.py's gp_offsets */
#endif
extern const u8 GP_SEAS;                        /* gplay.c: the season */
extern u16 GP_MGR;                              /* gplay.c: the career club's team word */
/* fpad.c (FPORT band) */
void fp_log(u32 code, i32 rc, u32 id, u32 y);
u32 fp_wake(void);
i32 fp_ml_add(u32 match_id, u16 home, u16 away, u32 off);
enum { FL_MLOPEN = 15, FL_MLSIM, FL_MLADD, FL_MLDONE, FP_ML_KIND = 0x4D4C };
enum { ML_NONE, ML_OPEN, ML_DONE };

#define MLS ((struct fp_ml *)FP_ML)
#define MM(ml) ((sr_match *)(ml)->m_raw)
typedef char fp_ml_size_is[sizeof(struct fp_ml) == 56 && FP_ML_SZ == 56 * FP_ML_N && sizeof(sr_match) == 6 ? 1 : -1];

#if defined(FPORT_TEST) && defined(__i386__)    /* (the mini-league paths' stack: sr_rr_table's frame - the gate reads
                                                   FP_STKFREE, the least free game stack seen; fpad.c's) */
extern u32 FP_STKLOWP[1];
extern u32 FP_STKFREE;
enum { ML_CHAIN = 1792 };                       /* (sr_rr_table + its callees below the probe, rounded up) */
static void stk_probe(void)
{
    u32 e;
    __asm__ volatile ("movl %%esp, %0" : "=r"(e));
    e -= FP_STKLOWP[0];
    e = e > ML_CHAIN ? e - ML_CHAIN : 0;
    if (e < FP_STKFREE) FP_STKFREE = e;
}
#else
#define stk_probe() ((void)0)
#endif

/* ---- GP_IN: the final tables ---- */
static u32 in_n(u32 d) { return d < GP_GIN[0] && d < C_GD ? GP_GIN[O_INN + d] : 0; }
static const u8 *in_row(u32 d, u32 k) { return GP_GIN + O_INT + (d * C_GT + k) * C_ROW; }
/* an entrant [division, place] -> its team word, 0 = that table is not in GP_IN. The table's own place, B teams
   included: gplay's place_club reading with kind 4 */
static u16 entrant(const u8 *e)
{
    return e[1] >= 1 && e[1] <= in_n(e[0]) ? *(const u16 *)in_row(e[0], e[1] - 1u) : 0;
}

const struct fp_mlrow *fp_ml_row(u8 id) { return id >= 1 && id <= FP_MLN ? &FP_MLT[id - 1] : 0; }
const struct fp_ml *fp_ml_get(u32 i) { return i < FP_ML_N && MLS[i].id ? &MLS[i] : 0; }

static u32 total(const struct fp_mlrow *r) { return r->legs * (r->n * (r->n - 1u) / 2); }
static i32 sched(const struct fp_mlrow *r, struct fp_ml *ml)
{
    return sr_mini_sched(r->n, r->legs, r->policy, ml->seed, MM(ml), ml->have, 6);
}

i32 fp_ml_table(const struct fp_ml *ml, void *rows)
{
    const struct fp_mlrow *r = ml ? fp_ml_row(ml->id) : 0;
    if (!r) return -1;
    stk_probe();
    return sr_rr_table(ml->n, MM(ml), ml->have, r->pts[0], r->pts[1], r->pts[2], r->tb, ml->seed, (sr_srow *)rows);
}

static u32 fmix(u32 h) { h ^= h >> 16; h *= 0x7FEB352Du; h ^= h >> 15; h *= 0x846CA68Bu; return h ^ (h >> 16); }
static u32 mid(const struct fp_ml *ml, u32 md) { return (u32)FP_ML_KIND << 16 | (u32)ml->season << 8 | (ml->id - 1u) << 4 | md; }

/* the matches of matchday md not yet played: scored from their match id, as fpad.c's h_sim (no decider: a level
   score stands); FP_MLF (test builds) forces THE match of that matchday */
static void sim_one(struct fp_ml *ml, u32 k)
{
    sr_match *x = &MM(ml)[k];
    const u32 id = mid(ml, x->md), h = fmix(id ^ 0x5F0A7u ^ (u32)ml->season << 24 ^ k << 20);
    x->hg = (u8)(h % 4); x->ag = (u8)(h >> 4 & 3);
#ifdef FPORT_TEST
    for (u32 i = 0; i < 8; i++)
        if (FP_MLF[i][0] == ml->id && FP_MLF[i][1] == x->md) { x->hg = FP_MLF[i][2]; x->ag = FP_MLF[i][3]; }
#endif
    x->played = 1;
    fp_log(FL_MLSIM, 0, id, (u32)(x->hg | x->ag << 4 | x->home << 8 | x->away << 12));
}
void fp_ml_sim(struct fp_ml *ml, u32 md)
{
    for (u32 k = 0; k < ml->have; k++) {
        const sr_match *x = &MM(ml)[k];
        if (x->md == md && !x->played && !(GP_MGR && (ml->club[x->home] == GP_MGR || ml->club[x->away] == GP_MGR)))
            sim_one(ml, k);
    }
}

static void done_cb(struct fp_ml *ml) { if (FP_MLDONE) FP_MLDONE(ml); }

static void drop(struct fp_ml *ml, i32 rc)      /* an instance the rules refuse: none (logged) */
{
    fp_log(FL_MLOPEN, rc, ml->id, 0xBAD);
    volatile u8 *b = (volatile u8 *)ml;
    for (u32 j = 0; j < sizeof *ml; j++) b[j] = 0;
}

/* the stage as far as it goes now; all: the season end - the career club's matches left are simulated too */
static void progress(struct fp_ml *ml, u32 all)
{
    const struct fp_mlrow *r = fp_ml_row(ml->id);
    if (!r || ml->state != ML_OPEN) return;
    for (;;) {
        const i32 h = sched(r, ml);
        if (h < 0) { drop(ml, h); return; }
        ml->have = (u8)h;
        u32 k = 0;
        while (k < ml->have && MM(ml)[k].played) k++;
        if (k == ml->have) {
            if (ml->have < total(r)) { drop(ml, -2); return; }   /* (the policy gave no further match: never a loop) */
            break;
        }
        const sr_match *x = &MM(ml)[k];
        const u16 hm = ml->club[x->home], aw = ml->club[x->away];
        if (!all && GP_MGR && (hm == GP_MGR || aw == GP_MGR) && !fp_ml_add(mid(ml, x->md), hm, aw, r->off[x->md]))
            return;                             /* (the career club's: queued - or there already; its result comes back) */
        sim_one(ml, k);                         /* (not the career club's, the season end, or one the port refused) */
    }
    sr_srow rows[4];
    if (fp_ml_table(ml, rows) != ml->n || rows[0].club >= ml->n) { drop(ml, -3); return; }
    ml->winner = ml->club[rows[0].club];
    ml->state = ML_DONE;
    fp_log(FL_MLDONE, 0, ml->winner, (u32)(ml->id | rows[0].pts << 8));
    done_cb(ml);
}

/* the port's result callback for a mini-league fixture (fpad.c h_done) */
void fp_ml_result(const sr_port_fixture *f, const sr_port_result *res)
{
    const u32 i = f->match_id >> 4 & 0xF, md = f->match_id & 0xF;
    if (f->match_id >> 16 != FP_ML_KIND || i >= FP_ML_N) return;
    struct fp_ml *ml = &MLS[i];
    if (ml->id != i + 1 || ml->state != ML_OPEN || ml->season != (u8)(f->match_id >> 8)) return;
    for (u32 k = 0; k < ml->have; k++) {
        sr_match *x = &MM(ml)[k];
        if (x->md != md || x->played || ml->club[x->home] != f->home || ml->club[x->away] != f->away) continue;
        x->hg = res->g90[0]; x->ag = res->g90[1]; x->played = 1;
        progress(ml, 0);
        return;
    }
}

/* G3's question (fpad.c h_windows): the club is in a mini-league stage that is running */
u32 fp_ml_busy(u16 team)
{
    for (u32 i = 0; i < FP_ML_N; i++) {
        const struct fp_ml *ml = &MLS[i];
        if (!ml->id || ml->state != ML_OPEN || ml->season != FP_SEASON) continue;
        for (u32 c = 0; c < ml->n && c < 4; c++)
            if (ml->club[c] == team) return 1;
    }
    return 0;
}

/* after a load / a reset (fpad.c fresh): an instance whose content the rules do not hold is dropped (a corrupt
   save) - the others, and the port's own section, are unaffected */
void fp_ml_loaded(void)
{
    for (u32 i = 0; i < FP_ML_N; i++) {
        struct fp_ml *ml = &MLS[i];
        const struct fp_mlrow *r = fp_ml_row(ml->id);
        if (!ml->id && !ml->state) continue;
        i32 bad = !r || ml->id != i + 1 || ml->n != r->n || ml->state < ML_OPEN || ml->state > ML_DONE || ml->have > 6;
        for (u32 c = 0; !bad && c < ml->n; c++)
            for (u32 d = 0; d < c; d++) bad |= ml->club[c] == ml->club[d];
        for (u32 k = 0; !bad && k < ml->have; k++)
            bad |= MM(ml)[k].home >= ml->n || MM(ml)[k].away >= ml->n || MM(ml)[k].played > 1;
        if (!bad) bad = sched(r, ml) < (i32)ml->have || (ml->state == ML_DONE && ml->have != total(r));
        if (bad) drop(ml, -1);
    }
}

/* row i's entrants are the career club's league's (the tables in GP_IN are its country's) and all known: their team
   words into club[]; me = the career club's index or -1 */
static i32 resolve(const struct fp_mlrow *r, u32 i, u16 *club, i32 *me)
{
    *me = -1;
    for (u32 c = 0; c < r->n; c++) {
        const u16 t = entrant(r->ent[c]);
        if (!t || (t & 0xFF) != FP_MLTF[i]) return 0;
        for (u32 d = 0; d < c; d++) if (club[d] == t) return 0;
        club[c] = t;
        if (t == GP_MGR) *me = (i32)c;
    }
    return 1;
}

/* GP_PNEED (gp_need_pre's head): the divisions to simulate now - the other entrants' of a row whose entrant place the
   career club holds - appended to GP_IN.sim[] (after the club's own play-offs' divisions; gp_need_pre counts them
   as theirs: always kept). Returns the mask it wanted. */
u32 fp_ml_need(void)
{
    u32 mask = 0;
    if (!fp_wake() || !GP_MGR) return 0;
    for (u32 i = 0; i < FP_MLN && i < FP_ML_N; i++) {
        const struct fp_mlrow *r = &FP_MLT[i];
        u32 m = 0, mine = 0;
        for (u32 c = 0; c < r->n; c++) {
            m |= 1u << r->ent[c][0];
            mine |= entrant(r->ent[c]) == GP_MGR;
        }
        if (mine) mask |= m;
    }
    u8 *sim = GP_GIN + O_INSIM;
    u32 ns = 0, have = 0;
    while (ns < C_SDX && sim[ns] != C_NOC) have |= 1u << sim[ns++];
    for (u32 d = 0; d < C_GD && ns < C_SDX; d++)
        if ((mask & ~have) >> d & 1 && !in_n(d)) sim[ns++] = (u8)d;   /* (a table already in GP_IN - the club's own: not again) */
    return mask;
}

void fp_ml_open(u32 at_end)
{
    if (!fp_wake()) return;
    for (u32 i = 0; i < FP_MLN && i < FP_ML_N; i++) {
        const struct fp_mlrow *r = &FP_MLT[i];
        struct fp_ml *ml = &MLS[i];
        const int have = ml->id == i + 1 && ml->state && ml->season == GP_SEAS;
        u16 club[4];
        i32 me;
        if (!have) {
            if (!resolve(r, i, club, &me) || (!at_end && me < 0)) continue;   /* (another country's season end; the
                                                   career club not an entrant: the season end's) */
            volatile u8 *b = (volatile u8 *)ml;
            for (u32 j = 0; j < sizeof *ml; j++) b[j] = 0;
            u32 seed = (u32)GP_SEAS << 24 ^ 0x4D4C5345u;
            for (u32 c = 0; c < r->n; c++) {    /* (the draw's seed: the entrants and their seasons' points - kept in
                                                   the instance, a reload redraws nothing) */
                ml->club[c] = club[c];
                seed = fmix(seed ^ club[c] ^ (u32)*(const u16 *)(in_row(r->ent[c][0], r->ent[c][1] - 1u) + O_RPTS) << 16);
            }
#ifdef FPORT_TEST
            if (FP_MLSEED) seed = FP_MLSEED;
#endif
            ml->seed = seed ? seed : 1;
            ml->id = (u8)(i + 1); ml->n = r->n; ml->season = GP_SEAS; ml->state = ML_OPEN;
            fp_log(FL_MLOPEN, (i32)at_end, ml->id, (u32)(me & 0xFF) | r->n << 8);
        } else if (!at_end || !in_n(r->ent[0][0]) || (*(const u16 *)in_row(r->ent[0][0], 0) & 0xFF) != FP_MLTF[i])
            continue;                           /* (open already; another country's season end) */
        progress(ml, at_end);
        if (at_end && ml->state == ML_DONE) done_cb(ml);   /* (lane 2: again once gp_season has written this season's
                                                   WINNERS list - its flags bit 0 guards the repeat) */
    }
}
