/* tools/cuprule.c - the Serie C play-off's cup place, FIGC C.U. 209/A II.1 / II.2 (internal/handoff/serie-c-cu209a.md): the ONE
   implementation (MC 15/11). A state-free leaf TU (no globals, no writes outside its argument): linked into obj4's S3C band
   (swreg.S3C_AT) and called by gplay.c (cup_code, the season-end play-off, GP_IN's tables) and by dplay.c (DP_NOC: the career
   contest, DP_IN's tables) on a cup_view (cupview.h). The gplay.c host tests include it (GP_RULE_INLINE). 4.2 S3 step 2. */
#include "cupview.h"
typedef unsigned char u8;
typedef unsigned short u16;
_Static_assert(sizeof(void *) != 4 || sizeof(struct cup_view) == 36, "cup_view layout (cupview.h) is shared with gplay.c / dplay.c");
static int cup_out(const struct cup_view *v, int g, int k) {     /* place k (from 0) precluded */
    const struct cv_row *t = v->t[g];
    int n = v->n[g], gap = v->gap[g];
    if (k <= 2) return 1;
    if (n < 6 || k < n - 5) return 0;
    if (k == n - 5) return !gap || t[n - 5].pts - t[n - 2].pts < gap;
    if (k == n - 4) return !gap || t[n - 4].pts - t[n - 3].pts < gap;
    return 1;
}
static int cup_find(const struct cup_view *v, u16 team, int *g, int *k) {
    for (*g = 0; team && *g < v->ng; (*g)++)
        for (*k = 0; *k < v->n[*g]; (*k)++) if (v->t[*g][*k].team == team) return 1;
    return 0;
}
static int cup_better(const struct cup_view *v, int a, int b) {    /* the 11ths of two groups: pts, wins, goals scored then the lot (C.U. 209/A art. 49, 'squadra meglio classificata': place, points, wins, goals scored, sorteggio) */
    const struct cv_row *x = &v->t[a][10], *y = &v->t[b][10];
    if (x->pts != y->pts) return x->pts > y->pts;
    if (x->won != y->won) return x->won > y->won;
    if (x->gf != y->gf) return x->gf > y->gf;
    return (u8)(x->glob * 37 + 11) < (u8)(y->glob * 37 + 11);      /* (the lot: a fixed pseudo-random of the club's global number) */
}
int cup_rule(struct cup_view *v) {      /* -> g * 32 + k, or -1 (no group has an 11th); fills og / ok / sg / sfrom */
    int gw, kw, gf, kf, b = -1;
    int w = cup_find(v, v->w, &gw, &kw);
    v->sg = v->sfrom = 0;
    if (v->real && w) {                 /* (an unknown / invalid finalist - an old save reads 0 - counts as precluded: the 4th of the winner's group) */
        int g = -1, k = -1;
        if (!cup_out(v, gw, kw)) g = gw, k = kw;
        else if (cup_find(v, v->f, &gf, &kf) && !cup_out(v, gf, kf)) g = gf, k = kf;
        if (g < 0) { g = gw; k = 3; }   /* (both precluded: the 4th of the winner's group) */
        if (k <= 9) { v->sg = g; v->sfrom = k + 1; }
        v->og = g; v->ok = k;
        return g * 32 + k;
    }
    if (w) { v->og = gw; v->ok = kw >= 10 && !cup_out(v, gw, kw) ? kw : 10; return gw * 32 + v->ok; }
    for (int g = 0; g < v->ng; g++)
        if (v->n[g] > 10 && (b < 0 || cup_better(v, g, b))) b = g;
    if (b < 0) return -1;
    v->og = b; v->ok = 10;
    return b * 32 + 10;
}

