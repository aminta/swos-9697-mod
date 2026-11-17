/* fpsave.c -- 4.2 the fixture port's save (P5, MC option A; MC 15/11: its own link unit in obj4's FPORT2 band, the
 * FPORT band's floor kept), linked by fpad.py at obj4 + swreg.FPORT2_AT before fpad.c (which calls fps_load). Only
 * sr_port_save / sr_port_load (and sr_port_init, which the load calls) are laid out of the vendored sr_port.c here
 * (roots, -ffunction-sections); fpad.c keeps its own copy of the rest. No log here: fpad.c logs the load (FL_PLOAD).
 * The slot-4 cross-check is here too (the FPORT band's room: its FPORT_TEST build) - ko[0] read as fpad.c reads it. */
#include "fpad.h"
#include "swce/sr_port.c"

extern u8 GP_GST[];                     /* gplay.c GP_ST (obj2): ko[0] at O_KO (fpad.py's gp_offsets flags) */
extern const u8 GP_SEAS;                /* gplay.c: the season gp_ours / the advance last saw */
extern u8 GP_PMID;                      /* gplay.c .bss: the port tie's legs played */
extern u32 GP_WK;                       /* gplay.c: the current calendar entry's week (the unit) */
extern u16 GP_MGR;                      /* gplay.c: the career club's team word */
#define KO0 (GP_GST + O_KO)
#define KW(o) (*(const u16 *)(KO0 + (o)))
static u32 live(void)                   /* as fpad.c's: slot 4 holds an undecided K_PORT tie of this season */
{
    return *(const u16 *)GP_GST == C_MAGIC && KW(0) == C_MAGIC && KO0[O_SEASON] == GP_SEAS && KO0[O_KIND] == C_KPORT
           && KO0[O_TW] == C_NOC;
}

static int valid(void) { return FP_ST.magic == FP_MAGIC && FP_ST.season == FP_SEASON; }

void fp_save(void)                      /* engine.before_save: a career save */
{
    struct fp_sv *h = (struct fp_sv *)FP_SAVE;
    if (FP_ST.magic == FP_ARM) return;  /* (armed, not yet stepped: FP_SAVE still holds what the load read - a save
                                           right after a load keeps the queue; a new career's / season's: as cleared) */
    h->tag = FP_STAG; h->ver = FP_SAVE_VER; h->season = FP_SEASON; h->len = 0;
    u8 *m = FP_SAVE + FP_SV_ML;         /* (v2: the ML block - written whole or as none, count 0) */
    for (u32 i = 0; i < 8; i++) m[i] = 0;
    if (FP_CWB != FP_WORLD || !valid()) return;
    m[0] = (u8)FP_MLTAG; m[1] = FP_MLTAG >> 8; m[2] = FP_MLVER; m[3] = FP_ML_SZ / 56;
    for (u32 i = 0; i < FP_ML_SZ; i++) m[8 + i] = FP_ML[i];
    const i32 n = sr_port_save(&FP_PORT, FP_SAVE + FP_SV_PORT, FP_SAVE_SZ - FP_SV_PORT);
    if (n <= 0) return;                 /* (never a half section: len 0 = none; fpad.py asserts SAVE_SIZE fits 48) */
    h->len = (u16)n; h->nleg = FP_ST.nleg; h->bad = FP_ST.pad[0];
    for (u32 i = 0; i < 2; i++) {
        for (u32 j = 0; j < 4; j++) h->leg[i][j] = FP_ST.leg[i][j];
        h->et[i] = FP_ST.et[i]; h->pens[i] = FP_ST.pens[i];
    }
}

void fps_reset(void)                    /* a new career / season, or a load without a usable FP item */
{
    sr_port_init(&FP_PORT, GP_MGR, (u16)GP_WK, SR_PORT_NONE, FP_HASH);   /* (s4first NONE: the host's windows) */
    FP_ST.tadded = 0; FP_ST.nleg = 0; FP_ST.pad[0] = 0; GP_PMID = 0;
    for (u32 i = 0; i < FP_ML_SZ; i++) FP_ML[i] = 0;   /* (no mini-league instance: a new career / season, an older save) */
}

static void ml_load(void)               /* the ML block of a v2 item of this season -> FP_ML (after fps_reset's zero); a bad
                                           tag / version / count: none (the port's own section unaffected). The instances'
                                           content is checked by fpml.c (fp_ml_loaded: sr_mini_sched on the held list) */
{
    const struct fp_sv *h = (const struct fp_sv *)FP_SAVE;
    const u8 *m = FP_SAVE + FP_SV_ML;
    if (h->tag != FP_STAG || h->ver != FP_SAVE_VER || h->season != FP_SEASON) return;
    if ((m[0] | m[1] << 8) != FP_MLTAG || m[2] != FP_MLVER || m[3] != FP_ML_SZ / 56) return;
    for (u32 i = 0; i < FP_ML_SZ; i++) FP_ML[i] = m[8 + i];
}

static i32 fp_load_item(void)          /* the fixtures loaded (>= 1; FP_ST's tie and GP_PMID the saved ones), 0 none
                                           (an older save / no port saved), or the refusal (< 0) */
{
    const struct fp_sv *h = (const struct fp_sv *)FP_SAVE;
    if (h->tag != FP_STAG || h->len == 0) return 0;
    if (h->ver != FP_SAVE_VER || h->season != FP_SEASON || h->len > FP_SAVE_SZ - FP_SV_PORT || h->nleg > 2)
        return SR_PORT_E_SAVE;          /* (a ver-1 item, test builds': refused whole - its sr_port section is version 0) */
    const i32 rc = sr_port_load(&FP_PORT, FP_SAVE + FP_SV_PORT, h->len, FP_HASH);
    if (rc) return rc < 0 ? rc : SR_PORT_E_SAVE;
    /* slot 4 cross-check (plan: a mismatch = refusal): pending = an undecided K_PORT tie of this season in ko[0] with
       the fixture's sides; no pending = none there and no leg played */
    const sr_port_fixture *f = 0;
    for (i32 j = 0; FP_PORT.pending && j < FP_PORT.n; j++)
        if (FP_PORT.f[j].match_id == FP_PORT.pending) f = &FP_PORT.f[j];
    if (FP_PORT.pending) {
        const u16 t0 = KW(O_TEAM), t1 = KW(O_TEAM + 2);
        if (!f || !live() || !((t0 == f->home && t1 == f->away) || (t0 == f->away && t1 == f->home)))
            return SR_PORT_E_SAVE;
    } else if (live() || h->nleg)
        return SR_PORT_E_SAVE;
    FP_ST.nleg = h->nleg; FP_ST.pad[0] = h->bad;
    GP_PMID = h->nleg;
    for (u32 i = 0; i < 2; i++) {
        for (u32 j = 0; j < 4; j++) FP_ST.leg[i][j] = h->leg[i][j];
        FP_ST.et[i] = h->et[i]; FP_ST.pens[i] = h->pens[i];
    }
    return FP_PORT.n;
}

i32 fps_load(void)                      /* fp_load_item(); none or refused: an empty port (fps_reset) - the tie in slot 4, if
                                           any, then plays as an ORPHAN */
{
    const i32 got = fp_load_item();
    if (got <= 0) fps_reset();
    else for (u32 i = 0; i < FP_ML_SZ; i++) FP_ML[i] = 0;
    ml_load();
    return got;
}
