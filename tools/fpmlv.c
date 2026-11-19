/* fpmlv.c -- 4.2 the fixture port's mini-league: its views and trophies (lane 2 of the Supercoppa Serie C; design
 * internal/handoff/supercoppa-c-design-20261116.md (e), plan P6 / P7). obj3 (fpmlv.py, CONVENTIONS 23: no engine code,
 * nothing in gplay's obj1). GENERIC: the Serie C specifics are the pack's 'mini_leagues' row (FP_MLT, lane 1) and its
 * names in FPV_TAB (fpmlv.py); this file reads the instances only through fpml.h.
 *
 * No state of its own (no .bss): what it shows is the saved instance (FP_ML, the FP item) and gplay's WN_ST (the 'WN'
 * item). An old save reads zero: fp_ml_get() NULL -> no line, no record, no table.
 *
 * - THIS season's WINNERS line and the management record's line are PULLED, as the national supercup's (gplay.c
 *   sc_wline_c / sc_wn / sc_rline): fpv_wn_c for winners.py's source 'N', fpv_rline_c for gp_rlines_c's hook - both
 *   read the instance (state 2, its season = GP_SEAS), so they hold from the last matchday to the season's end and
 *   after a save + load, with nothing written twice.
 * - The LAST season's WINNERS line is WRITTEN once: fpv_done (FP_MLDONE) appends ('N', id, winner) to WN_ST when
 *   WN_ST is that season's (gp_season has rewritten it: the season end) and sets fp_ml.flags bit 0. Called before
 *   that (the stage decided in May, WN_ST still the season before's) it writes nothing and leaves the bit clear:
 *   lane 1 calls FP_MLDONE again for every done instance from GP_PEND (after gp_season). A repeat with the bit set,
 *   or with the entry already there, is a no-op. */
#include "fpmlv.h"
#include "swce/swosrules.h"

#ifndef FPV_DATA
#define FPV_DATA __attribute__((section(".data")))
#endif
struct fpv_tab FPV_TAB FPV_DATA;

/* gplay.c's (obj2): the season gp_ours / the pages last saw, the career club, winners.py's source, the 'WN' item */
extern const u8 GP_SEAS;
extern const u16 GP_MGR;
extern const u32 GP_WNSRC;
enum { WN_N = 40, WN_MAGIC = 0x4E57, WN_PRE = 'p', WN_ML = 'N' };   /* (gplay.c's; fpmlv.py asserts WN_SIZE) */
struct wn_e { u8 type, idx; u16 team; };
extern struct wn_state { u16 magic; u8 season, n; struct wn_e e[WN_N]; } WN_ST;

enum { ML_OPEN = 1, ML_DONE = 2, MLF_WN = 1, WN_NONE = 0xFFFE, WN_RUN = 0xFFFF };

static const struct fp_ml *ml_of(u32 id)        /* this season's instance of row id, or 0 */
{
    for (u32 i = 0; i < FP_ML_N; i++) {
        const struct fp_ml *ml = fp_ml_get(i);
        if (ml && ml->id == id && ml->state && ml->season == GP_SEAS) return ml;
    }
    return 0;
}

void fpv_done(const struct fp_ml *ml)
{
    if (!ml || !ml->id || ml->state != ML_DONE || (ml->flags & MLF_WN)) return;
    if (WN_ST.magic != WN_MAGIC || WN_ST.season != ml->season || WN_ST.n > WN_N) return;   /* (not yet that season's) */
    u32 i = 0;
    for (; i < WN_ST.n; i++) {
        if (WN_ST.e[i].type == WN_PRE) return;  /* (a preview's marker: never in a season's own list) */
        if (WN_ST.e[i].type == WN_ML && WN_ST.e[i].idx == ml->id) break;
    }
    if (i == WN_ST.n) {
        if (i >= WN_N) return;                  /* (full: no line, the bit left clear) */
        WN_ST.e[i].type = WN_ML; WN_ST.e[i].idx = ml->id; WN_ST.e[i].team = ml->winner;
        WN_ST.n = (u8)(i + 1);
    }
    ((struct fp_ml *)ml)->flags |= MLF_WN;      /* (fpml.h: flags bit 0, the repeat's guard - the saved instance) */
}

u32 fpv_wn_c(void)
{
    const u32 id = GP_WNSRC >> 8 & 0xFF;
    if (GP_WNSRC >> 24) {                       /* the last season: WN_ST's entry, as gplay.c wn_find */
        if (WN_ST.magic != WN_MAGIC || (u8)(WN_ST.season + 1) != GP_SEAS) return WN_NONE;
        for (u32 i = 0; i < WN_ST.n && i < WN_N && WN_ST.e[i].type != WN_PRE; i++)
            if (WN_ST.e[i].type == WN_ML && WN_ST.e[i].idx == id) return WN_ST.e[i].team;
        return WN_NONE;
    }
    const struct fp_ml *ml = ml_of(id);
    if (!ml) return WN_NONE;
    return ml->state == ML_DONE ? ml->winner : WN_RUN;
}

u32 fpv_rline_c(u32 k)
{
    if (!GP_MGR) return 0;
    for (u32 i = 0; i < FP_ML_N; i++) {
        const struct fp_ml *ml = fp_ml_get(i);
        if (!ml || ml->state != ML_DONE || ml->season != GP_SEAS || ml->winner != GP_MGR) continue;
        const struct fp_mlrow *r = fp_ml_row(ml->id);
        if (!r || !(r->flags & 1) || r->rec >= FPV_TAB.nrec || !FPV_TAB.rec[r->rec]) continue;
        if (!k--) return FPV_TAB.rec[r->rec];
    }
    return 0;
}

const u8 *fpv_calnames(u32 match_id)
{
    if (match_id >> 16 != FPV_ML_KIND) return 0;
    const struct fp_mlrow *r = fp_ml_row((u8)((match_id >> 4 & 0xF) + 1));
    if (!r || r->name >= FPV_TAB.nname || !FPV_TAB.nm[r->name][0]) return 0;
    return (const u8 *)FPV_TAB.nm[r->name];
}

static const struct fp_ml *ml_at(u32 i)
{
    const struct fp_ml *ml = i < FP_ML_N ? fp_ml_get(i) : 0;
    return ml && ml->id && ml->state && ml->n >= 2 && ml->n <= 4 ? ml : 0;
}

i32 fpv_table(u32 i, struct fpv_trow out[4])
{
    const struct fp_ml *ml = ml_at(i);
    sr_srow rows[4];
    if (!ml || fp_ml_table(ml, rows) < 0) return 0;
    for (u32 k = 0; k < ml->n; k++) {
        const sr_srow *s = &rows[k];
        struct fpv_trow *o = &out[k];
        if (s->club >= ml->n) return 0;
        o->team = ml->club[s->club];
        o->colour = k ? 0 : FPV_TAB.zone;       /* (the place that wins, as a league's zone: from the first day) */
        o->pl = (u8)s->pl; o->w = (u8)s->w; o->d = (u8)s->d; o->l = (u8)s->l; o->gf = (u8)s->gf; o->ga = (u8)s->ga;
        o->pad = 0;
        o->pts = s->pts;
    }
    return ml->n;
}

u32 fpv_title(u32 i)
{
    const struct fp_ml *ml = ml_at(i);
    const struct fp_mlrow *r = ml ? fp_ml_row(ml->id) : 0;
    return r && r->name < FPV_TAB.nname ? FPV_TAB.ttl[r->name] : 0;
}

const char *fpv_legend(void) { return FPV_TAB.leg; }

u32 fpv_round(u32 match_id)
{
    const u32 md = match_id & 0xF;
    return match_id >> 16 == FPV_ML_KIND && FPV_TAB.rnd && md < FPV_TAB.ndays ? FPV_TAB.rnd + md : 0;
}

/* The table VIEW (Davide 17/11: screen 1 - the game's own table screen with the stage's rows; longtable lt_ov's mode
   3, opened from STAT of a league table that holds one of the stage's clubs). The game's table struct: +31h its
   clubs, +12Dh their team words, +2B3h their 18-byte rows. */
static u32 w16(const u8 *b) { return b[0] | b[1] << 8; }
static i32 diy_row(const u8 *diy, u32 team)     /* the club's row in the table, -1 = not one */
{
    u32 n = w16(diy + 0x31);
    if (n > 64) n = 64;
    for (u32 q = 0; q < n; q++)
        if (w16(diy + 0x12D + 2 * q) == team) return (i32)q;
    return -1;
}
static i32 view_of(const u8 *diy)       /* this season's instance with a club of the table, -1 = none */
{
    for (u32 i = 0; i < FP_ML_N; i++) {
        const struct fp_ml *ml = ml_at(i);
        if (!ml || ml->season != GP_SEAS) continue;
        for (u32 k = 0; k < ml->n; k++)
            if (diy_row(diy, ml->club[k]) >= 0) return (i32)i;
    }
    return -1;
}

u32 fpv_view(const u8 *diy, u32 *title)
{
    const i32 i = view_of(diy);
    const struct fp_mlrow *r = i < 0 ? 0 : fp_ml_row(fp_ml_get((u32)i)->id);
    const u32 t = r ? fpv_title((u32)i) : 0;
    if (!t || (FPV_TAB.vcid[r->name] && FPV_TAB.vcid[r->name] != diy[0x2D])) return 0;
    *title = t;
    return 0x100 | FPV_TAB.vflags[r->name];
}

u32 fpv_rows(const u8 *diy, u8 *rows, u16 *ord, const u8 *sel, u8 *tf)
{
    struct fpv_trow t[4];
    const i32 i = view_of(diy);
    const u32 n = i < 0 ? 0 : (u32)fpv_table((u32)i, t);
    for (u32 k = 0; k < 4; k++) {
        u8 *f = tf + FPV_TF * k, *x = rows + 18 * k;
        for (u32 j = 0; j < FPV_TF; j++) f[j] = 0;
        if (k >= n) continue;
        const i32 q = diy_row(diy, t[k].team);
        u32 off = (u32)((const u8 *)f - sel);   /* (a row names its club by its TeamFile: selTeamsPtr + this) */
        if (q >= 0) {
            const u8 *o = diy + 0x2B3 + 18 * q;
            off = o[0] | o[1] << 8 | (u32)o[2] << 16 | (u32)o[3] << 24;
        } else {
            f[0] = (u8)t[k].team; f[1] = (u8)(t[k].team >> 8); f[2] = f[0]; f[3] = f[1]; f[4] = 1; f[5] = '?';
        }
        const u16 v[7] = { t[k].pl, t[k].w, t[k].d, t[k].l, t[k].gf, t[k].ga, (u16)t[k].pts };
        x[0] = (u8)off; x[1] = (u8)(off >> 8); x[2] = (u8)(off >> 16); x[3] = (u8)(off >> 24);
        for (u32 j = 0; j < 7; j++) { x[4 + 2 * j] = (u8)v[j]; x[5 + 2 * j] = (u8)(v[j] >> 8); }
        ord[k] = (u16)(18 * k);
    }
    return n;
}
