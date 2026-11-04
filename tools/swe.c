/* The competition engine's object (engine step O, PLAN §19; CONVENTIONS 23bis): obj4, the engine's alone - its code in
   the file pages after the header (swe.py), its arena the zero-filled tail (.bss). DOS/4GW zeroes no tail, so the
   engine zeroes the arena itself: swe_init() first, before any other engine call that uses the arena.

   Step W adds the world registry's loader (swreg.py writes the manifest at SWE_REG): reg_enter / reg_leave put a
   world's country namespace into the game's tables and back, in any mode (careerworld's w_ns_set does the swap; the
   career keeps its own path, w_ns_ld). Their state is initialised data (file pages), so they need no swe_init.
   swe_sel_pre / swe_sel_post wrap the team pickers' SelectTeamsFinalMenu call (swe.py's obj1 trampoline): step W
   lists nothing new there, W-modes adds the worlds a mode lists.
   Freestanding, cdecl, as every C file of the mod (cobj.py). */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define SWE_VERSION 2
#define SWE_ARENA 0x8000

#define REG_HDR 32                      /* (swreg.py HDR, REC, F_*) */
#define REG_REC 24
#define F_NS 2
#define M_FRIENDLY 1                    /* (swreg.py M_*) */

u8 SWE_ARENA_AT[SWE_ARENA];
u32 SWE_STATE;                          /* 0 = not initialised, 1 = swe_init ran */
extern const u8 SWE_REG[];              /* obj4+REG_AT: the manifest */
u32 REG_PREV = 0xFFFFFFFF;              /* the namespace reg_enter left (WCUR), ~0 = none entered */
u32 SEL_C254 = 0;                       /* competitionsTable[254] at the picker's entry */
u32 SEL_MODE = 0xFFFFFFFF;              /* the picker's mode (swreg M_*), ~0 = outside a picker */

int swe_init(void)
{
    volatile u8 *a = SWE_ARENA_AT;      /* (volatile: no memset call for clang to emit - there is no library) */
    for (u32 i = 0; i < SWE_ARENA; i++)
        a[i] = 0;
    SWE_STATE = 1;
    return SWE_VERSION;
}

static u32 rd32(const u8 *p) { return p[0] | p[1] << 8 | p[2] << 16 | (u32)p[3] << 24; }

int reg_count(void) { return SWE_REG[6]; }

const u8 *reg_world(u32 n)              /* world n's record, 0 = not in this build */
{
    for (int k = 0; k < SWE_REG[6]; k++) {
        const u8 *r = SWE_REG + REG_HDR + REG_REC * k;
        if (r[0] == n)
            return r;
    }
    return 0;
}

static void ns_set(u32 w)               /* careerworld w_ns_set: al = world (0 = the base namespace); keeps every register */
{
#ifdef NS
    __asm__ volatile("call w_ns_set" : : "a"(w) : "memory", "cc");
#else
    (void)w;
#endif
}

int reg_enter(u32 n)                    /* 1 = world n's namespace is in the tables, 0 = nothing to swap, < 0 = refused */
{
    const u8 *r = reg_world(n);
    u8 *wcur = (u8 *)rd32(SWE_REG + 8);
    if (!r)
        return -1;
    if (REG_PREV != 0xFFFFFFFF)
        return -2;                      /* (one level: leave first) */
    if (!(r[1] & F_NS) || !wcur)
        return 0;
    REG_PREV = *wcur;
    ns_set(n);
    return 1;
}

int reg_leave(void)                     /* back to the namespace reg_enter left */
{
    if (REG_PREV == 0xFFFFFFFF)
        return 0;
    ns_set(REG_PREV);
    REG_PREV = 0xFFFFFFFF;
    return 1;
}

void swe_sel_pre(u32 mode)
{
    SEL_MODE = mode;
    SEL_C254 = *(u32 *)rd32(SWE_REG + 12);
}

void swe_sel_post(void)
{
    *(u32 *)rd32(SWE_REG + 12) = SEL_C254;
    SEL_MODE = 0xFFFFFFFF;
}

/* GoGetTeamsForPlay's picker call (swe.py pick_site) lands here: SWE_PICK = what that call reached before (chained) */
__attribute__((naked)) void swe_sel_tramp(void)
{
    __asm__ volatile("pushal\n\tpushl %0\n\tcall swe_sel_pre\n\taddl $4, %%esp\n\tpopal\n\t"
                     "call SWE_PICK\n\tpushal\n\tcall swe_sel_post\n\tpopal\n\tret" : : "i"(M_FRIENDLY));
}
