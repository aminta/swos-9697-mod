/* tools/gplay3.c - 4.2 gplay code in obj3 (MC 16/11, CONVENTIONS 23: mod code that is not engine code goes in obj3; the
   gplay obj1 pages were full after S6a - the host fixture shape 10 B over, the release shape 82 B free; MC's floor 256 B
   in both). Builds with worlds compile gplay.c with GP_X3=1 and link this file into obj3 on its own (gplay.py x3_patch,
   after gplay.c's link, against its symbols); gplay.c calls it through the bound dword GP_SCDONE. The other builds and
   the host tests include it into gplay.c (GP_X3_INLINE), at the place sc_done had.
   Holds: sc_done, the career club's national / UEFA supercup tie decided (gp_rec_c). w = the tie's winner (0 = none). */
#ifdef GP_X3_INLINE
#define GP_X3FN static
#else
#define GP_X3FN
#include "gpsc.h"                       /* (the types, SC_*, IS_MGR: the one copy gplay.c includes too) */
extern u8 GP_SEAS;
extern u16 GP_MGR;
extern u32 SC_TRACE;
extern u8 SC_ST[SC_H + 12 * SC_NE];
extern u32 rng;                         /* (gplay.c's one generator: a private copy would change later draws) */
u32 below(u32 n);
const u8 *sc_entry(void);
int sc_rank(u16 w);
int usc_live(void);
#endif
GP_X3FN void sc_done(u16 w) {           /* gp_rec_c: the career club's supercup tie decided */
    SC_TRACE |= 0x40;
    int won = w && IS_MGR(w);
    if (usc_live()) {                   /* (4.0.6 the UEFA Super Cup) */
        SC_U[1] = 3; SC_U[2] = (u8)won;
        if (w) { SC_U[4] = (u8)w; SC_U[5] = (u8)(w >> 8); }
        return;
    }
    if (SC_ST[4] == 1) {
        SC_ST[4] = won ? 2 : 3;
        u16 a = w, b = (u16)(SC_ST[6] | SC_ST[7] << 8);
        if (!won && a && b) {           /* (4.0.5 Davide 29/10: the semi-final lost - the final simulated now, as the
                                           other semi-final was: the better placed of last season wins 3 in 5, the
                                           draw seeded by the season and the cup - its winner for VINCITORI) */
            const u8 *e = sc_entry();
            int ra = sc_rank(a), rb = sc_rank(b);
            rng = GP_SEAS * 7919u + (e ? e[1] : 0) + 1;
            u16 x = below(5) < 3 ? (ra <= rb ? a : b) : (ra <= rb ? b : a);
            SC_ST[8] = (u8)x; SC_ST[9] = (u8)(x >> 8);
        }
    } else {
        if (won) SC_ST[5] = 1;          /* (the final, or the one match, won: the season record's line) */
        if (w) { SC_ST[8] = (u8)w; SC_ST[9] = (u8)(w >> 8); }
    }                                   /* (4.0.5 Davide 29/10: the winner kept for VINCITORI all season - SC_ST +8,
                                           header bytes the 'SC' item already saves: slot 4 is reused later) */
}
