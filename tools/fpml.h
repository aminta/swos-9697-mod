#ifndef FPML_H
#define FPML_H
/* tools/fpml.h - the fixture port's MINI-LEAGUE interface (Supercoppa Serie C, 4.2; design: internal/handoff/supercoppa-c-design-20261116.md (e)).
   Owner: lane 1 (Nazionali), FROZEN as of this commit: lanes 2 (views / trophies) and 3 (harness) code against it. GENERIC: nothing here knows
   a division, a file or a name; the Serie C specifics are ONE pack.json 'mini_leagues' row compiled into FP_MLT. Types sr_match / sr_srow /
   sr_port_fixture / sr_port_result come from the engine headers (swosrules.h, swc/sr_port.h) the exe already vendors. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int i32;

enum { FP_ML_N = 2 };                   /* instances budgeted (save: 2 x 56 B) */

struct fp_mlrow {                       /* FP_MLT[]: const, from the pack's 'mini_leagues' (fpad.py compiles it) */
    u8 id;                              /* 1.. (0 = none) */
    u8 n;                               /* clubs (3 for the Supercoppa Serie C) */
    u8 legs;                            /* 1: every pairing once */
    u8 policy;                          /* engine SR_SCHED_*: WINNER_RESTS (md1 drawn, the md1 winner rests md2, ...) */
    u8 pts[3];                          /* win, draw, loss points (3, 1, 0 pending Davide: spec Q1) */
    u8 ntb, tb[6];                      /* tie-break codes (engine sr_rr_table) */
    u8 ent[4][2];                       /* entrants as [division, place] (place 1 = the winner), resolved with place_club at the league end */
    u8 off[6];                          /* calendar unit offsets from the league's last unit L, per matchday (129, 130, 131 -> 1, 2, 3) */
    u8 name, rec, flags, pad[3];        /* string-table index (4 languages), record-line id, bit 0 = FP_MLF_RECORD (winner recorded in the management record) */
};

struct fp_ml {                          /* FP_ML[FP_ML_N]: swe.c .bss, saved in the FP item (save v2: header 36 B, ML block at 36, 2 x 56 B); zero = none */
    u8 id;                              /* the FP_MLT row + 1 (0 = no instance) */
    u8 state;                           /* 0 none, 1 open, 2 done */
    u8 n, have;                         /* clubs, matches decided so far */
    u32 seed;                           /* the draw seed (md1 drawing) */
    u16 club[4];                        /* team words, in the draw order */
    /* sr_match m[6]: md, home, away, played, hg, ag (6 B each, engine swosrules.h) */
    u8 m_raw[36];
    u16 winner;                         /* team word once state = 2 */
    u8 season, flags;                   /* flags bit 0: the WINNERS / record line was written (FP_MLDONE ran) */
};

/* lane 1 implements: */
void fp_ml_open(u32 at_end);            /* GP_PLEND (the career league's last match day) / GP_PEND (non-entrant career club, whole stage simulated) */
void fp_ml_sim(struct fp_ml *ml, u32 md);                                   /* scores the matches of md not involving the career club (h_sim's hash, no decider) */
i32 fp_ml_table(const struct fp_ml *ml, void *rows /* sr_srow[4] */);       /* rank order by the engine's sr_rr_table; club index -> ml->club[]; the winner is row 0 */
const struct fp_ml *fp_ml_get(u32 i);                                       /* i < FP_ML_N, NULL when none */
const struct fp_mlrow *fp_ml_row(u8 id);                                    /* id from fp_ml.id */
/* fp_ml_result(const sr_port_fixture *, const sr_port_result *): the port's result callback for K_ML fixtures (lane 1; declared with the engine types in fpad.c) */

/* lane 2 fills it (once, when state becomes 2): the WINNERS line + the management record line; flags bit 0 guards the repeat */
extern void (*FP_MLDONE)(const struct fp_ml *);

/* lane 3 test switches (FPORT_TEST builds only; never in a release): forced simulated scores and seed */
#ifdef FPORT_TEST
extern u8 FP_MLF[8][4];                 /* (id, md, hg, ag) per row; id 0 = unused */
extern u32 FP_MLSEED;                   /* 0 = none; else forces the md1 draw seed */
#endif
/* log codes in FP_ST.log (fpad.c:44): FL_MLOPEN, FL_MLSIM, FL_MLADD, FL_MLDONE */
#endif
