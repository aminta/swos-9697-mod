/* S6a (4.3, MC 15/11): SEASON under a default world whose registry record has M_SEASON - its own unit in obj4's S6
   band (swreg.S6_AT..S6_END, linked by s6sea.py), swe.c keeps only the picker's mode rules (M_SEASON = one club, no
   STORICO, the STAG. STORICHE box) and exports what this unit reads.

   historic.CALLS[1] (SeasonMenu's picker call, mkseason's season_sel chained) lands on s6_sea_tramp: a world season
   runs the career-style picker on that world's lists - SelectTeamsFinalMenu (SWE_SELECT) with the CLASSIC CAREERS
   selector's world table on top, swe_sel_pre(M_SEASON): the default world's list only, the path's lists swap the
   namespace (careerworld w_ns_menu). The namespace the path left stays: careerworld's SeasonMenu tramp (sw_init)
   reads CW_SEAW (careerworld W_SEAW) for the season's world. Anything else falls through to swe.c's swe_sea_tramp
   (the 1996-97 picker; a default world without seasons keeps step 2.5's message). No .bss: the state is swe.c's.
   Freestanding, cdecl, as every C file of the mod (cobj.py). */
typedef unsigned char u8;
typedef unsigned int u32;

#define M_SEASON 4                      /* (swreg.py M_*) */

extern u8 SWE_SELECT[], CW_SEAW[];      /* SelectTeamsFinalMenu; careerworld W_SEAW (db) */
extern u32 SEL_ON, SEL_DW, SEL_MODE, NS_LEFT;   /* (swe.c) */
u32 av_world(void);
const u8 *reg_world(u32 n);
void sel_restore(void);
void swe_sel_pre(u32 mode);

void s6_sea_post(void)
{
    sel_restore();
    SEL_ON = 0;
    SEL_MODE = 0xFFFFFFFF;
}

u32 s6_sea_pre(void)                    /* the season's world (CW_SEAW too) when its picker runs, else 0 */
{
    u32 w = av_world();
    const u8 *r = w ? reg_world(w) : 0;
    CW_SEAW[0] = 0;
    if (!r || !(r[6] & M_SEASON))
        return 0;
    NS_LEFT = 0;                        /* (the picker owns the namespace: no guard after it) */
    swe_sel_pre(M_SEASON);
    if (SEL_ON && SEL_DW == w)
        return CW_SEAW[0] = (u8)w;
    s6_sea_post();
    return 0;
}

__attribute__((naked)) void s6_sea_tramp(void)
{
    __asm__ volatile("pushal\n\tcall s6_sea_pre\n\ttestl %eax, %eax\n\tpopal\n\tjz swe_sea_tramp\n\t"
                     "call SWE_SELECT\n\tpushfl\n\tpushal\n\tcall s6_sea_post\n\tpopal\n\tpopfl\n\tret");
}
