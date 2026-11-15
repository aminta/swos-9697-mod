#ifndef CUPVIEW_H
#define CUPVIEW_H
/* The Serie C play-off's cup place (FIGC C.U. 209/A): the view the ONE implementation (gplay.c cup_rule) reads. gplay builds it from
   GP_IN, dplay (DP_NOC) from DP_IN - the rows have the same 12-byte layout (gp_row / dp_row). 4.2 S3 step 2. */
struct cv_row { unsigned short team, glob, won, gf, ga, pts; };
struct cup_view {
    const struct cv_row *t[4];          /* the groups' final tables by group 0 .. ng - 1 */
    unsigned char n[4], ng, gap, real, pad;
    unsigned short w, f;                /* the cup's winner and finalist (team words, 0 unknown) */
    unsigned char og, ok, sg, sfrom;    /* out: the place's group and place (from 0); the scroll: group, first place (1-based, 0 none) */
};
#endif
