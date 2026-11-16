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
