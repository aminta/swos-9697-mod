/* tools/frstep.c - 4.2 preseason friendlies (a), the engine's game side (Motore). One unit linked by frnd.py into the
   obj4 band FRND (swreg FRND_AT): this file + frnd.c (the pure parts) + frpick.c (Mercato's pick, one copy: the
   chooser page links to fr_pick / fr_given / fr_level here).

   Design: internal/handoff/motore-frnd-engine.md + motore-frnd-fable-review.md (MC 16/11). The fixture port's hooks
   (gplay GP_PAPI ko_one, GP_PSTEP at sc_step_c's head, GP_PLEG in gp_rec), chained here: FRND first, then what the
   hook held before (fpad's fp_step / fp_leg, or nothing) through FR_NSTEP / FR_NLEG.

   fr_season (the tail of InitializeNewSeason, after cseg_3D204; careers only, never on a load): the world's FRSS
     slice read (swefile, FR_BUF in swe.c's .bss); given = 4 x FR_NONE, venues 0xFF; FR_GIVENW (test builds) or the
     chooser (frc_choose through FR_CHOOSE, 0 = not linked); fr_pick - the only installing call; FR_ST rewritten
     (season, FR_OPEN, the four words, home flags; FR_LEVEL kept as frc_choose left it). No install here: friendly 1
     is built by fr_step at the first menu (gp_scgl -> gp_sc -> sc_step_c), as friendlies 2-4 at the advances.
   fr_step (sc_step_c's head): FR_OPEN this season -> friendly k (= played) built into ko[0] at its turn (fr_turns on
     the calendar, slot-4 entries never block), kind K_FR, one match, LV_BETTER (a draw stands: no e.t., no
     penalties); slot 4 held between the friendlies by FR_OPEN (gplay sc_busy); the fee kept in ko[0] (FR_KO_FEE)
     for finance.py's fi_gate. Every friendly decided, or a turn missed, or any failure: FR_OPEN cleared and
     fr_after4 (weak: the 1996-97 session's native re-install) called once; then the chain.
   fr_leg (gp_rec, every match of ours): ko[0] a K_FR of this season -> fr_result (W / D / L from the goals, never
     from tw); then the chain. */
#include "frnd.c"
#include "frpick.c"

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;

/* gplay (fpad.py's gp_offsets: O_* / C_* from gplay.c's GP_OFFS, -D at the compile) */
struct gp_ko;
typedef void ko_one_fn(struct gp_ko *, u16, u16, int, int, int, int, int, int, const u8 *);
extern void *const GP_PAPI[1];          /* ko_one */
extern u8 GP_GST[];                     /* GP_ST */
extern u8 GP_SEAS;
extern u32 GP_WK;
extern u16 GP_MGR;
extern const u32 GP_K;
extern const u8 FR_D1R[];               /* the pseudo registers D1..D7 (stride 4) */
extern const u8 *const FR_A1R;          /* A1: the home side's team record (word 0 = the team) */
#ifndef FR_CAL                          /* (the host test: its own calendar) */
extern u8 FR_CAL[];                     /* the career calendar */
#endif
extern const u16 FR_CALCUR;
extern const u8 FR_SEASON;              /* the game's seasonPlaying byte */
extern const u8 FR_CWB;                 /* the career's world byte */
extern u8 FR_ST[FR_SZ];                 /* SC_ST entry FR_E (gplay, saved with 'SC') */
extern u8 FR_BUF[];                     /* swe.c .bss: the world's FRSS slice (FR_BUFSZ) */
#if defined(__MACH__)                   /* (the host test: mach-o has no ".data" section name) */
#define FR_DATA
#else
#define FR_DATA __attribute__((section(".data")))   /* (file dwords: frnd.py binds them with add_ptr, 0 = none) */
#endif
u32 (*FR_NSTEP)(void) FR_DATA;          /* the hooks' previous targets (fpad's fp_step / fp_leg, or 0) */
void (*FR_NLEG)(void) FR_DATA;
void (*FR_CHOOSE)(const FrcCtx *, uint16_t *, uint8_t *) FR_DATA;   /* the FRCH slot, 0 = no page */
void (*FR_AFTER4)(void) FR_DATA;        /* fr_after4 (the 1996-97 session's), 0 = none */
u8 FR_NAMES[8] FR_DATA;                 /* the slot-4 contest's names, long + short STR_BASE-relative (frnd.py: gplay's
                                           FR_NAMEB, frtext.LABEL) */
extern u32 tc_room(void);               /* tcache.py */
extern int swe_fopen_r(const char *);
extern int swe_fread(int, void *, unsigned int);
extern int swe_fclose(int);
extern u32 fr_cached_asm(u32 word);     /* frnd.py glue: FindTeamInCache (non-trapping), 1 = cached */
extern const u32 FR_D6BA2;              /* the season's wage bill (cseg_3D204) */
extern void *const FR_SLOT4;            /* dseg_D8CBA: the game's slot-4 contest (0 = none; InitializeNewSeason zeroes it,
                                           cseg_8DAC3 / int4_step set it before cseg_3D204: a native slot-4 contest) */
extern const u16 FR_D6C4E;              /* the season's expected gates of slots 0-3 (cseg_3D204) */

#define KO0 (GP_GST + O_KO)
#define O_FEE (O_PTS + 4)               /* (pts[2]: a one-tie contest's unused entry - the fee >> 4, fi_gate's D7) */

/* G = cseg_3CB08 with A1 = A2 = careerTeam (the league gate formula, both sides the career club's wage bill: the
   second term reads D0's low word, as the game) -> fi_gate's D7 << 4 */
static u32 fr_g(void) {
    u32 v = FR_D6BA2, d = FR_D6C4E;
    u32 d7 = v / 4000 * 10000 + (v & 0xFFFF) / 4000 * 2000;
    d7 = d ? (d7 >> 4) / d : 0;
    return (d7 & 0xFFFF) << 4;
}
#ifdef FR_TEST                          /* (test builds, HOSTTEST_SYMS: the harness's reads / given list; none in a release) */
#define FR_TRACE_SET(x) (FR_TRACE = (u8)(x))
#define FR_T(x) x
FR_DATA u8 FR_TRACE;                          /* (the last step: 1x season, 2x install, 3x leg, 4x close; 0x8x why not) */
FR_DATA u16 FR_GIVENW[4] = { 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF };   /* (the harness's given list: replaces the chooser) */
FR_DATA u32 FR_FEE[4]; FR_DATA u32 FR_G;                  /* (the fees credited, G) */
FR_DATA u8 FR_FB;
FR_DATA u8 FR_ROWC;                           /* (bit k: friendly k's fixture row relabelled by fr_row after the close) */
#else
#define FR_TRACE_SET(x) ((void)0)
#define FR_T(x)
#endif

static int fr_cached(void *ctx, uint16_t w) { (void)ctx; return (int)fr_cached_asm(w); }

static u32 fr_slice(u8 world) {         /* FRSS.DAT -> FR_BUF: the world's slice length, 0 = none */
    int h = swe_fopen_r("data\\frss.dat");
    if (h < 0) return 0;
    u8 *b = FR_BUF;                     /* (header + index: 8 + 12 x 255 at most, inside FR_BUFSZ) */
    u32 len = 0, off = 0, at = (u32)swe_fread(h, b, 8 + 12 * 255);
    if (at >= 8 && *(u32 *)b == 0x44535246u && b[4] == 1)   /* ('FRSD' v1) */
        for (u32 i = 0; i < b[5] && 20 + 12 * i <= at; i++)
            if (b[8 + 12 * i] == world) { off = *(u32 *)(b + 12 + 12 * i); len = *(u32 *)(b + 16 + 12 * i); }
    if (len > FR_BUFSZ || off < 8) len = 0;
    u32 got = 0;                        /* (the slice's bytes already in b, moved down to b[0]) */
    if (len && off < at) {
        got = at - off < len ? at - off : len;
        for (u32 i = 0; i < got; i++) b[i] = b[off + i];
        at = off;
    }
    while (len && at < off) {           /* (no seek in swefile v1: what lies before the slice read over) */
        u32 n = off - at < FR_BUFSZ ? off - at : FR_BUFSZ;
        if (swe_fread(h, b, n) != (int)n) len = 0;
        at += n;
    }
    if (len && got < len && swe_fread(h, b + got, len - got) != (int)(len - got)) len = 0;
    swe_fclose(h);
    return len;
}

static void fr_close(u32 why) {         /* FR_OPEN cleared, fr_after4 once */
    if (!(FR_ST[1] & FR_OPEN)) return;
    FR_ST[1] &= ~FR_OPEN;
    FR_TRACE_SET(why);
    if (FR_AFTER4) FR_AFTER4();
}

void fr_season(u32 self) {              /* InitializeNewSeason's tail: self = the career club (gplay gp_mgr) */
    u16 avoid[4];
    u32 nav = 0, season = FR_SEASON;
    if (FR_ST[0] && FR_ST[0] != (u8)season)  /* (last season's four: avoided) */
        for (int k = 0; k < 4; k++) { u16 w = *(u16 *)(FR_ST + 2 + 2 * k); if (w != FR_NONE && w) avoid[nav++] = w; }
    u32 lvl = FR_FLAGS(FR_ST) & FR_LEVEL_MASK;
    FR_ST[0] = (u8)season; FR_ST[1] = 0;
    for (int k = 0; k < 4; k++) *(u16 *)(FR_ST + 2 + 2 * k) = FR_NONE;
    FR_ST[10] = 0; FR_ST[11] = (u8)(lvl >> 8);
    /* a native slot-4 contest this season (play-offs, NSL...: Friendlies 96-97 16/11): only with an FR_AFTER4 to
       reinstall it after the 4th friendly; else no friendlies (no FR_OPEN), the native one keeps slot 4 */
    u32 native = FR_SLOT4 != 0;
    if (native && !FR_AFTER4) { FR_TRACE_SET(0x86); return; }
    u32 len = fr_slice(FR_CWB);
    if (!len || !self) { FR_TRACE_SET(0x81); return; }
    FrRoom room = { tc_room(), fr_cached, 0 };
    u16 given[4] = { FR_NONE, FR_NONE, FR_NONE, FR_NONE };
    u8 venues = 0xFF;
    FrcCtx c = { FR_BUF, len, FR_CWB, (u16)self, FR_NONE, avoid, nav, &room, season, season * 7919u + 0x4652u, 2, FR_ST };
#ifdef FR_TEST
    if (FR_GIVENW[0] != FR_NONE || FR_GIVENW[1] != FR_NONE || FR_GIVENW[2] != FR_NONE || FR_GIVENW[3] != FR_NONE)
        for (int k = 0; k < 4; k++) given[k] = FR_GIVENW[k];
    else
#endif
    if (FR_CHOOSE) FR_CHOOSE(&c, given, &venues);
    FrPick out;
    int rc = fr_pick(FR_BUF, len, FR_CWB, (u16)self, FR_NONE, given, avoid, nav, &room, season, c.seed,
                     venues == 0xFF ? c.nhome : FR_VENUES(venues), &out);
    if (rc) { FR_TRACE_SET(0x82); return; }
    u8 wk[4];
    if (!fr_turns(FR_CAL, wk)) { FR_TRACE_SET(0x83); return; }
    for (int k = 0; k < 4; k++) *(u16 *)(FR_ST + 2 + 2 * k) = out.word[k];
    u32 fl = (FR_FLAGS(FR_ST) & FR_LEVEL_MASK) | (out.home & 15) | (native ? FR_NATIVE : 0);   /* (FR_LEVEL as frc_choose left it) */
    FR_ST[10] = (u8)fl; FR_ST[11] = (u8)(fl >> 8);
    FR_ST[1] = FR_OPEN;
    FR_T(FR_FB = out.fb;)
    FR_TRACE_SET(0x10);
}

static int fr_first(const u8 *wk) {     /* the first turn kept (turns < 0 dropped: fewer friendlies) */
    int k = 0;
    while (k < 4 && wk[k] == 0xFF) k++;
    return k;
}

u32 fr_step(void) {                     /* sc_step_c's head: 1 = a friendly built into ko[0] */
    if (FR_ST[0] != FR_SEASON || !(FR_ST[1] & FR_OPEN) || !GP_MGR) return FR_NSTEP ? FR_NSTEP() : 0;
    const int live = *(const u16 *)GP_GST == C_MAGIC && *(const u16 *)KO0 == C_MAGIC && KO0[O_SEASON] == GP_SEAS;
    if (live && KO0[O_KIND] == C_KFR && KO0[O_TW] == C_NOC) return 0;   /* (a friendly being played: slot 4 held) */
    u8 wk[4];
    u32 kept = fr_turns(FR_CAL, wk);
    int k = fr_first(wk) + FR_NPLAYED(FR_ST);
    if (!kept || k >= 4) { fr_close(0x40); return FR_NSTEP ? FR_NSTEP() : 0; }
    int w = wk[k];
    if (k == fr_first(wk) ? FR_CALCUR != 0 : (int)GP_WK >= w) { fr_close(0x84); return FR_NSTEP ? FR_NSTEP() : 0; }
    u16 opp = *(u16 *)(FR_ST + 2 + 2 * k);
    int home = FR_ST[10] >> k & 1;
    u32 wk0 = GP_WK;
    if ((int)GP_WK >= w) GP_WK = (u32)w - 1;   /* (friendly 1 before the first entry's week: ko_one's clamp) */
    ((ko_one_fn *)GP_PAPI[0])((struct gp_ko *)KO0, home ? GP_MGR : opp, home ? opp : GP_MGR, w, w, 1, C_KFR,
                             C_LVBETTER, 0xFF, FR_NAMES);
    GP_WK = wk0;
    if (KO0[O_D1] != w) { *(u16 *)KO0 = 0; fr_close(0x85); return 0; }   /* (never half installed: ko[0] dropped) */
    u8 band = 0xFF;                     /* (the band the club falls in, as FrPick.band: not saved - fr_given on the
                                           slice, read again here; no slice / no level: no fee) */
    u32 len = fr_slice(FR_CWB);
    if (len) fr_given(FR_BUF, len, FR_CWB, GP_MGR, FR_NONE, (const u16 *)(FR_ST + 2), (u32)k, 0, &band);
    u32 g = fr_g();
    u32 f = band <= FR_FAR_DOWN ? fr_fee(g, band, home) : 0;
    FR_T(FR_G = g; FR_FEE[k] = f;)
    *(u16 *)(KO0 + O_FEE) = (u16)(f >> 4);
    FR_TRACE_SET(0x20 | k);
    return 1;
}

u32 fr_row(const u8 *row) {             /* gp_scrow_c's head (GP_PROW): a slot-4 fixture-list row at a played friendly's week
                                           this season -> the friendly's short name (STR_BASE-relative); 0 = not one */
    if (!row || row[0] != 4 || FR_ST[0] != FR_SEASON) return 0;
    u32 n = FR_NPLAYED(FR_ST);
    if (!n) return 0;
    u8 wk[4];
    if (!fr_turns(FR_CAL, wk)) return 0;
    for (int k = fr_first(wk), m = 0; k < 4 && m < (int)n; k++, m++)
        if (wk[k] == row[1]) {
            FR_T(if (!(FR_ST[1] & FR_OPEN)) FR_ROWC |= (u8)(1u << k);)
            return *(const u32 *)(FR_NAMES + 4);
        }
    return 0;
}

void fr_leg(void) {                     /* gp_rec, every match of ours */
    if (GP_K == 0 && FR_ST[0] == FR_SEASON && *(const u16 *)KO0 == C_MAGIC && KO0[O_KIND] == C_KFR &&
        KO0[O_SEASON] == GP_SEAS) {
        u16 d1 = *(const u16 *)FR_D1R, d2 = *(const u16 *)(FR_D1R + 4);
        int mh = *(const u16 *)FR_A1R == GP_MGR;
        u32 n = FR_NPLAYED(FR_ST);
        if (n < 4) fr_result(FR_ST, n, mh ? d1 : d2, mh ? d2 : d1);
        FR_TRACE_SET(0x30 | n);
    }
    if (FR_NLEG) FR_NLEG();
}

/* finance.py fi_gate (cseg_3C4CE's gate, through FI_FRGATE): the match of the current calendar entry is slot 4's and
   ko[0] this season's friendly -> its fee >> 4 instead of the 'final' gate (400 %); else d7 as it is */
u32 fr_gate(u32 d7) {
    if (FR_CAL[FR_CALCUR] == 4 && *(const u16 *)GP_GST == C_MAGIC && *(const u16 *)KO0 == C_MAGIC &&
        KO0[O_KIND] == C_KFR && KO0[O_SEASON] == GP_SEAS)
        return *(const u16 *)(KO0 + O_FEE);
    return d7;
}
