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

#define SWE_VERSION 3
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

/* W-modes M2: the friendly / DIY picker lists the worlds (swreg M_FRIENDLY). It runs on the CLASSIC CAREERS selector's
   world table (CAREER_WORLD: careerworld's w_ns_menu swaps the namespace of the world on the path). The default world
   (SETUP.DAT +105, mainbtn) opens first: its own list plus the STORICO entry (menu id 98), which lists the other worlds
   (the 1996-97 game as WMENU + 0, its continents proxies of the game's). The 1996-97 default = the game's top list
   + STORICO. Mixing A: one career world per contest besides the 1996-97 game's clubs. The first club picked under a
   career world sets the contest's world (SEL_CW), and the lists then leave the other career worlds out, until no
   club is selected. All the lists are copies in obj4; swe_sel_post puts the game's back. */
#define WMENU 200                       /* (mkseason WMENU, CAREERS) */
#define CAREERS 98
#define CLUB_TEAMS 1
#define DATA __attribute__((section(".data")))   /* (initialised: obj4's .bss is not zeroed at boot) */

extern u8 SWE_D0[], SWE_NUMSEL[], SWE_TTYPE[], SWE_A0[], SWE_NDIY[], SWE_CFB[];
u32 SEL_ON DATA = 0;                    /* 1 = this picker lists the worlds */
u32 SEL_DW DATA = 0;                    /* the default world (0 = the 1996-97 game) */
u32 SEL_CW DATA = 0;                    /* the contest's career world, 0 = none yet */
u32 SEL_N DATA = 0;                     /* NUMSEL at the last list */
u32 SWE_CWORLD DATA = 0;                /* the last contest's world (picker / DIY load): the 'WM' block */
u32 *SEL_SLOT98 DATA = 0, *SEL_SLOTD DATA = 0;
u32 SEL_O98 DATA = 0, SEL_OD DATA = 0;  /* the game's list pointers */
u8 L_HIST[24] DATA = {0};
u8 L_DEF[88] DATA = {0};
static const u8 SET_W[3] = {5, 0, 4};   /* SETUP.DAT +105 -> world (mainbtn: 2026-27, 1996-97, 1984-85) */

static u32 *comp_slot(u32 id) { return (u32 *)(rd32(SWE_REG + 12) - 4 * 254 + 4 * id); }

static const u8 *list_ids(u32 l)        /* a list's menu ids: after its dd entries up to -1 */
{
    const u8 *p = (const u8 *)l;
    while (rd32(p) != 0xFFFFFFFF)
        p += 4;
    return p + 4;
}

static int friendly_world(u32 n)        /* world n is listed by the friendly / DIY picker */
{
    const u8 *r = reg_world(n);
    return r && (r[6] & M_FRIENDLY);
}

static int locked(u32 n) { return SEL_CW && n && n != SEL_CW; }

static void put_ff(u8 *l) { l[0] = l[1] = l[2] = l[3] = 0xFF; }

static void sel_lists(void)
{
    u8 *h = L_HIST + 4;
    put_ff(L_HIST);
    if (SEL_DW && *comp_slot(WMENU))
        *h++ = WMENU;
    for (const u8 *p = list_ids(SEL_O98); *p != 0xFF && h < L_HIST + sizeof L_HIST - 1; p++) {
        u32 w = *p >= WMENU && *p < WMENU + 10 ? *p - WMENU : 0;
        if (*p == WMENU + SEL_DW || (w && (!friendly_world(w) || locked(w))))
            continue;
        *h++ = *p;
    }
    *h = 0xFF;
    if (!SEL_DW)
        return;
    u8 *d = L_DEF + 4;
    put_ff(L_DEF);
    if (!locked(SEL_DW))
        for (const u8 *p = list_ids(SEL_OD); *p != 0xFF && d < L_DEF + sizeof L_DEF - 2; p++)
            *d++ = *p;
    *d++ = CAREERS;
    *d = 0xFF;
}

void swe_sel_pre(u32 mode)
{
    SEL_MODE = mode;
    u32 *c254 = (u32 *)rd32(SWE_REG + 12);
    SEL_C254 = *c254;
    SEL_ON = 0;
    u32 cw = rd32(SWE_REG + 16), set = rd32(SWE_REG + 28);
    if (!cw || !set || *(u16 *)SWE_TTYPE != CLUB_TEAMS || !*comp_slot(CAREERS))
        return;
    u32 s = *(u8 *)set, dw = s < sizeof SET_W ? SET_W[s] : 0;
    if (dw && !friendly_world(dw))
        dw = 0;
    SEL_ON = 1;
    SEL_DW = dw;
    SEL_CW = 0;
    SEL_N = 0;
    *c254 = cw;
    SEL_SLOT98 = comp_slot(CAREERS);
    SEL_O98 = *SEL_SLOT98;
    *SEL_SLOT98 = (u32)L_HIST;
    if (dw) {
        SEL_SLOTD = comp_slot(WMENU + dw);
        SEL_OD = *SEL_SLOTD;
        *SEL_SLOTD = (u32)L_DEF;
        SWE_D0[0] = WMENU + dw;         /* (GoGetTeamsForPlay's 255: the top list) */
    }
    sel_lists();
}

void swe_sel_ns(u32 w)                  /* careerworld w_ns_menu, every list: w = the world on the path (0 = base) */
{
    if (SEL_MODE == 0xFFFFFFFF || !SEL_ON)
        return;
    u32 n = *(u16 *)SWE_NUMSEL;
    if (!n)
        SEL_CW = 0;
    else if (n > SEL_N && !SEL_CW && w)
        SEL_CW = w;
    SEL_N = n;
    sel_lists();
}

void swe_sel_post(void)
{
    *(u32 *)rd32(SWE_REG + 12) = SEL_C254;
    if (SEL_ON) {
        *SEL_SLOT98 = SEL_O98;
        if (SEL_DW)
            *SEL_SLOTD = SEL_OD;
        SWE_CWORLD = *(u16 *)SWE_NUMSEL ? SEL_CW : 0;
    }
    SEL_ON = 0;
    SEL_MODE = 0xFFFFFFFF;
}

/* GoGetTeamsForPlay's picker call (swe.py pick_site) lands here: SWE_PICK = what that call reached before (chained) */
__attribute__((naked)) void swe_sel_tramp(void)
{
    __asm__ volatile("pushal\n\tpushl %0\n\tcall swe_sel_pre\n\taddl $4, %%esp\n\tpopal\n\t"
                     "call SWE_PICK\n\tpushal\n\tcall swe_sel_post\n\tpopal\n\tret" : : "i"(M_FRIENDLY));
}

#ifdef NS
/* w_ns_menu's `call w_ns_set` (al = the path's world) lands here, then goes on to it (SWE_NSSET) */
__attribute__((naked)) void swe_ns_tramp(void)
{
    __asm__ volatile("pushal\n\tmovzbl %al, %eax\n\tpushl %eax\n\tcall swe_sel_ns\n\taddl $4, %esp\n\tpopal\n\t"
                     "jmp SWE_NSSET");
}
#endif

/* The DIY contest's world: the 'WM' block after the file's last record (notes/engine/save-ledger.md) */
static u32 diy_size(void) { return (u32)SWE_NUMSEL + 2 + 684 * *(u16 *)SWE_NDIY - (u32)SWE_CFB; }

static int dos_open(u32 name, u32 mode)
{
    u32 r, cf;
    __asm__ volatile("int $0x21\n\tsbbl %1, %1" : "=a"(r), "=r"(cf) : "a"(0x3D00 | mode), "d"(name) : "cc", "memory");
    return cf ? -1 : (int)(r & 0xFFFF);
}

static u32 dos_end(int h)               /* the file's size (lseek to its end) */
{
    u32 a, d, cf;
    __asm__ volatile("int $0x21\n\tsbbl %2, %2" : "=a"(a), "=d"(d), "=r"(cf) : "a"(0x4202), "b"(h), "c"(0), "d"(0)
                     : "cc", "memory");
    return cf ? 0xFFFFFFFF : (a & 0xFFFF) | d << 16;
}

static void dos_write(int h, const u8 *b, u32 n)
{
    u32 r;
    __asm__ volatile("int $0x21" : "=a"(r) : "a"(0x4000), "b"(h), "c"(n), "d"(b) : "cc", "memory");
    (void)r;
}

static void dos_close(int h)
{
    u32 r;
    __asm__ volatile("int $0x21" : "=a"(r) : "a"(0x3E00), "b"(h) : "cc", "memory");
    (void)r;
}

u8 WM_BLK[4] DATA = {'W', 'M', 1, 0};
u32 DIY_NAME DATA = 0;

void swe_diy_saved(void)                /* after SaveDIYFile (A0 = the file name): the block when a career world plays */
{
    if (*(u16 *)SWE_D0 || !SWE_CWORLD)
        return;
    int h = dos_open(rd32(SWE_A0), 1);
    if (h < 0)
        return;
    if (dos_end(h) == diy_size()) {
        WM_BLK[3] = SWE_CWORLD;
        dos_write(h, WM_BLK, 4);
    }
    dos_close(h);
}

void swe_diy_name(void) { DIY_NAME = rd32(SWE_A0); }

void swe_diy_loaded(void)               /* after LoadDIYFile: the block only on a file of the game's size + 4 */
{
    SWE_CWORLD = 0;
    if (*(u16 *)SWE_D0 || !DIY_NAME)
        return;
    int h = dos_open(DIY_NAME, 0);
    if (h < 0)
        return;
    u32 n = dos_end(h);
    dos_close(h);
    const u8 *b = SWE_NUMSEL + 2 + 684 * *(u16 *)SWE_NDIY;
    if (n == diy_size() + 4 && b[0] == 'W' && b[1] == 'M' && b[2] == 1 && b[3] && reg_world(b[3]))
        SWE_CWORLD = b[3];
}

__attribute__((naked)) void swe_diy_save_tramp(void)
{
    __asm__ volatile("call SWE_SAVEDIY\n\tpushfl\n\tpushal\n\tcall swe_diy_saved\n\tpopal\n\tpopfl\n\tret");
}

__attribute__((naked)) void swe_diy_load_tramp(void)
{
    __asm__ volatile("pushal\n\tcall swe_diy_name\n\tpopal\n\tcall SWE_LOADDIY\n\tpushfl\n\tpushal\n\t"
                     "call swe_diy_loaded\n\tpopal\n\tpopfl\n\tret");
}
