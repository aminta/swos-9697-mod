/* uesum.c's recorded cup (US_REC, MC's save item 'US'): shared with usmenu.c (4.1 RC2, the RIEPILOGO phase menu) */
struct tie {                            /* x = the first leg's home club, y its guest (team words) */
    u16 x, y;
    u8 l1, l2, pn, fl;                  /* goals x << 4 | y (15 at most): leg 1, leg 2, penalties; FL_* */
};
enum { FL_PLAYED = 0x80, FL_TWO = 0x40, FL_LEG1 = 0x20, FL_Y = 1, FL_DEC = 2, FL_AET = 4, FL_PEN = 8 };
#define NSTG 4                          /* the earlier stages kept: play-offs, round of 16, quarter-finals, semi-finals */
#define NTIE 22                         /* (8 + 8 + 4 + 2) */
#define NLP 36                          /* the league phase's clubs */
struct cup {                            /* ss: the season stamp, seasonPlaying + 1 (0: none) */
    u8 id, n[NSTG], ss;
    struct tie t[NTIE];
    u16 lw[NLP];                        /* the league phase's final table: team words, place order (lw[0] 0: none) */
    u8 lp[NLP];                         /* their points */
};
