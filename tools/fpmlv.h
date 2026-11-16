#ifndef FPMLV_H
#define FPMLV_H
/* tools/fpmlv.h - the mini-league's VIEWS and TROPHIES (lane 2 of the Supercoppa Serie C, 4.2; fpmlv.c, obj3 - CONVENTIONS 23).
   GENERIC, as fpml.h: nothing here knows a division, a file or a name; the names are the pack row's, in FPV_TAB (fpmlv.py,
   the exe's language). Reads the mini-league only through fpml.h (fp_ml_get / fp_ml_row / fp_ml_table); fills FP_MLDONE. */
#include "fpml.h"

enum { FPV_NN = 4, FPV_NR = 4 };        /* names / record lines budgeted (fpmlv.py asserts) */
enum { FPV_ML_KIND = 0x4D4C };          /* a mini-league fixture's match_id >> 16 ('ML'; design (a) 4: | season << 8 | (id - 1) << 4 | md) */

struct fpv_tab {                        /* fpmlv.py table(): put after the link (plain data, never const) */
    u8 nname, nrec;                     /* entries of nm[] / rec[] in use */
    u8 zone;                            /* the 1st place's row colour (zones.py LIGHT_BLUE 0Dh) */
    u8 pad;
    char leg[8];                        /* its legend label (<= 5 characters, NUL-ended): VINCE / WINS / VAINQ / SIEG */
    u32 nm[FPV_NN][2];                  /* fp_mlrow.name -> the long name (the slot's title after the country), the calendar
                                           label; STR_BASE-relative, the 8 bytes gplay's ko_one copies */
    u32 rec[FPV_NR];                    /* fp_mlrow.rec -> the management record's line (STR_BASE-relative), 0 = none */
    u32 ttl[FPV_NN];                    /* fp_mlrow.name -> the table view's title (STR_BASE-relative) */
};

struct fpv_trow {                       /* a row of the table view, in rank order */
    u16 team;                           /* the club's team word (fp_ml.club[]) */
    u8 colour;                          /* its zone colour, 0 = the game's own alternating rows */
    u8 pl, w, d, l, gf, ga, pad;
    short pts;
};

void fpv_done(const struct fp_ml *ml);  /* FP_MLDONE's target */
u32 fpv_wn_c(void);                     /* winners.py's source 'N' (GP_WNSRC = 'N' | id << 8 [| 1 << 24: the last season]):
                                           the winner's team word, 0FFFFh being played, 0FFFEh nothing */
u32 fpv_rline_c(u32 k);                 /* the k-th record line the career club won this season (STR_BASE-relative), 0 = no more */
const u8 *fpv_calnames(u32 match_id);   /* a mini-league fixture's 8 name bytes for ko_one, 0 = not one (the caller's own) */
i32 fpv_table(u32 i, struct fpv_trow out[4]);   /* instance i's table: the rows written (0 = none: no instance, an old save) */
u32 fpv_title(u32 i);                   /* instance i's view title (STR_BASE-relative), 0 = none */
const char *fpv_legend(void);           /* the 1st place's legend label */
#endif
