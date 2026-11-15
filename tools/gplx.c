/* tools/gplx.c - 4.2 GPLX, "gplay overflow" (MC 15/11, internal/handoff/obj1-room.md): gplay.c code moved out of the full
   gplay pages into obj4's GPLX band (swreg.GPLX_AT..GPLX_END, a 4.2 release band, floor >= 256 B). Builds with worlds compile
   gplay.c with GP_GPLX=1 and link this file on its own (gplay.py: a dry link for its addresses, gplay.c's link, then this
   one against gplay.c's symbols); the other builds and the host tests include it into gplay.c (GP_GPLX_INLINE).
   Holds: the supercup entrants' rule sc_rule (4.0.5 / 4.0.6, with sc_place and sc_cup), called by sc_step_c / usc_step. */
#ifdef GP_GPLX_INLINE
#define GPLX_FN static
#else
#define GPLX_FN
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
/* (gplay.c's layouts, as there - the sizes asserted) */
enum { WN_N = 40, WN_MAGIC = 0x4E57 };
struct wn_e { u8 type, idx; u16 team; };
struct wn_state { u16 magic; u8 season, n; struct wn_e e[WN_N]; };
struct cf_state { u16 magic; u8 season, file; u8 rank[256]; };
_Static_assert(sizeof(struct wn_state) == 164 && sizeof(struct cf_state) == 260, "gplay.c wn_state / cf_state layouts");
enum { CF_MAGIC = 0x4643 };
enum { SC_E = 36, SC_NE = 16, SC_H = 12 };
enum { SCR_CHAMP = 1, SCR_SECOND, SCR_CUPW, SCR_CUPF, SCR_THIRD, SCR_FOURTH, SCR_TITLE0, SCR_TITLE1,
       SCR_UCL, SCR_UEL, SCR_UECL };
#define SC_U (SC_ST + SC_H + 12 * (SC_NE - 1))
extern u8 GP_SEAS;
extern u8 SC_ST[SC_H + 12 * SC_NE];
extern struct cf_state CF_ST;
extern struct wn_state WN_ST;
u32 wn_find(int ty, int ix, int pre);
#endif
static u16 sc_place(int file, int place) {     /* last season's top-division club at place (CF_ST), 0 = unknown */
    if (CF_ST.magic != CF_MAGIC || CF_ST.file != file) return 0;
    for (int i = 0; i < 256; i++) if (CF_ST.rank[i] == place) return (u16)(file | i << 8);   /* (level 0 << 5) */
    return 0;
}
static u16 sc_cup(int id, int fin) {           /* the stored cup winner (fin 0) / finalist (1), 0 = unknown */
    if ((SC_ST[0] | SC_ST[1] << 8) != 0x4353) return 0;
    for (int i = 0; i < SC_ST[2] && i < SC_NE; i++) {
        const u8 *e = SC_ST + SC_H + 12 * i;
        if (e[1] == id) return (u16)(fin ? e[8] | e[9] << 8 : e[4] | e[5] << 8);
    }
    return 0;
}
GPLX_FN u16 sc_rule(const u8 *e, int r) {
    switch (r & 15) {
    case SCR_CHAMP: return sc_place(e[0], 1);
    case SCR_SECOND: return sc_place(e[0], 2);
    case SCR_CUPW: return sc_cup(e[1], 0);
    case SCR_CUPF: return sc_cup(e[1], 1);
    case SCR_THIRD: return sc_place(e[0], 3);
    case SCR_FOURTH: return sc_place(e[0], 4);
    case SCR_UCL: case SCR_UEL: case SCR_UECL: {   /* (4.0.6: last season's snapshot, SC_U +6) */
        int i = (r & 15) - SCR_UCL;
        u16 w = (u16)(SC_U[6 + 2 * i] | SC_U[7 + 2 * i] << 8);
        return (u8)(SC_U[3] + 1) == GP_SEAS && w != 0xFFFF ? w : 0;
    }
    case SCR_TITLE0: case SCR_TITLE1:   /* (4.0.5 MEX: last season's stage-title winner, play-off e[30] / e[31]: WN_ST) */
        if (WN_ST.magic != WN_MAGIC || (u8)(WN_ST.season + 1) != GP_SEAS) return 0;
        { u32 w = wn_find('K', e[30 + (r & 15) - SCR_TITLE0], 0); return w == 0xFFFE ? 0 : w; }
    }
    return 0;
}
