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
#define M_CAREER 8

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
   club is selected. All the lists are copies in obj4; swe_sel_post puts the game's back.
   Q1 (b), Davide 2026-11-04: MONDO 2026-27 (the current world, SET_W[0]) is never in STORICO: under another default it
   is its own GREEN entry next to the box (the 1996-97 default: in the game's top list, CAREER_WORLD's spare byte, as
   careerworld's w_ns_menu needs COMP254 = CAREER_WORLD), and STORICO lists the historic worlds only. */
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
u8 *SEL_TOP DATA = 0;                   /* the 1996-97 default: CAREER_WORLD's 98, FF, FF (spare) */
extern u8 SWE_CT[], SWE_EFV[];
#define GREEN 14                        /* (mainbtn GREEN) */
u8 LOCK_TXT[48] DATA = {0};             /* the lock line (swe.py LOCK_LINE, the exe's language) */
u8 LOCK_BUF[48] DATA = {0};             /* what the title shows (a copy: the game may write its title through it) */
u32 *TITLE_P DATA = 0;                  /* the title entry's text pointer while it shows the lock line */
u32 TITLE_O DATA = 0;                   /* its own text */
static const u8 SET_W[3] = {5, 0, 4};   /* SETUP.DAT +105 -> world (mainbtn: 2026-27, 1996-97, 1984-85) */

static u32 *comp_slot(u32 id) { return (u32 *)(rd32(SWE_REG + 12) - 4 * 254 + 4 * id); }

static const u8 *list_ids(u32 l)        /* a list's menu ids: after its dd entries up to -1 */
{
    const u8 *p = (const u8 *)l;
    while (rd32(p) != 0xFFFFFFFF)
        p += 4;
    return p + 4;
}

static int friendly_world(u32 n)        /* world n is listed by this picker (its mode: friendly / DIY, career) */
{
    const u8 *r = reg_world(n);
    return r && (r[6] & (SEL_MODE == M_CAREER ? M_CAREER : M_FRIENDLY));
}

static int locked(u32 n) { return SEL_CW && n && n != SEL_CW; }

static int cur_entry(void)              /* MONDO 2026-27 is an entry of the default world's list */
{
    return SEL_DW != SET_W[0] && friendly_world(SET_W[0]) && !locked(SET_W[0]);
}

static void put_ff(u8 *l) { l[0] = l[1] = l[2] = l[3] = 0xFF; }

static void sel_lists(void)
{
    u8 *h = L_HIST + 4;
    put_ff(L_HIST);
    if (SEL_DW && *comp_slot(WMENU))
        *h++ = WMENU;
    for (const u8 *p = list_ids(SEL_O98); *p != 0xFF && h < L_HIST + sizeof L_HIST - 1; p++) {
        u32 w = *p >= WMENU && *p < WMENU + 10 ? *p - WMENU : 0;
        if (*p == WMENU + SEL_DW || *p == WMENU + SET_W[0] || (w && (!friendly_world(w) || locked(w))))
            continue;
        *h++ = *p;
    }
    *h = 0xFF;
    int hist = h > L_HIST + 4;          /* (an empty STORICO is left out) */
    if (!SEL_DW) {
        if (SEL_TOP) {
            u8 *t = SEL_TOP;
            t[1] = t[2] = 0xFF;
            if (cur_entry())
                *t++ = WMENU + SET_W[0];
            *t = hist ? CAREERS : 0xFF;
        }
        return;
    }
    u8 *d = L_DEF + 4;
    put_ff(L_DEF);
    if (!locked(SEL_DW))
        for (const u8 *p = list_ids(SEL_OD); *p != 0xFF && d < L_DEF + sizeof L_DEF - 3; p++)
            *d++ = *p;
    if (cur_entry())
        *d++ = WMENU + SET_W[0];
    if (hist)
        *d++ = CAREERS;
    *d = 0xFF;
}

static void title_restore(void)
{
    if (TITLE_P && *TITLE_P == (u32)LOCK_BUF)
        *TITLE_P = TITLE_O;
    TITLE_P = 0;
}

static void top_restore(void)
{
    if (SEL_TOP) {
        SEL_TOP[0] = CAREERS;
        SEL_TOP[1] = SEL_TOP[2] = 0xFF;
    }
    SEL_TOP = 0;
}

/* SelectTeamsReinit's names call (swe.py, chained: historic's hist_names, which leaves the first entry in its
   EF_VARS): MONDO 2026-27 GREEN in the lists of a friendly / DIY picker; while the lock applies, the lists of worlds
   (an entry of a world or the STORICO box) show the lock line in the title bar (entry 0). */
static int world_name(u32 t)
{
    for (u32 k = 0; k < 10; k++)
        if (rd32(SWE_CT + 4 * (WMENU + k)) && t == rd32(SWE_CT + 4 * (WMENU + k)) + 1)
            return 1;
    return t == rd32(SWE_CT + 4 * CAREERS) + 1;
}

void swe_names_post(void)
{
    u32 nm = rd32(SWE_CT + 4 * (WMENU + SET_W[0]));
    u8 *e0 = (u8 *)rd32(SWE_EFV), *e = e0;
    if (!SEL_ON || !nm || !e)
        return;
    int worlds = 0;
    for (int k = 0; k < 64 && *(u16 *)(e + 2) != 87; k++, e += 56) {   /* (ordinal 87: the end of the entries) */
        if (*(u16 *)(e + 4))
            continue;
        if (rd32(e + 0x26) == nm + 1)
            *(u16 *)(e + 0x1E) = GREEN;
        worlds |= world_name(rd32(e + 0x26));
    }
    u8 *t0 = e0 - 21 * 56;              /* (EF_VARS = entry 21: the title is entry 0) */
    u32 *pp = (u32 *)(t0 + 0x26);
    if (*(u16 *)(t0 + 2) != 0 || !LOCK_TXT[0])
        return;
    if (SEL_CW && worlds) {
        if (*pp != (u32)LOCK_BUF) {
            TITLE_P = pp;
            TITLE_O = *pp;
        }
        for (u32 k = 0; k < sizeof LOCK_BUF; k++)
            LOCK_BUF[k] = LOCK_TXT[k];
        *pp = (u32)LOCK_BUF;
    } else if (TITLE_P == pp)
        title_restore();
}

/* The contest's namespace (W-modes M2): the game reads a picked club's country NAME by its number after the picker
   (the pre-match screen), so a friendly / DIY with a World 2026-27 club keeps that world's namespace (the 1996-97
   game's numbers, < 100, are the same in every namespace). The next team picker of another kind (season, preset, edit,
   a new career) puts the base one back: swe_stfm_guard at SelectTeamsFinalMenu's entry, outside a career and only
   while the namespace is still the one left here. */
u32 NS_LEFT DATA = 0;                   /* the namespace swe left after a contest's picker / DIY load, 0 = none */
extern u8 SWE_GTYPE[];
#define GAME_TYPE_CAREER 4

static void ns_left(u32 w)
{
    u8 *wcur = (u8 *)rd32(SWE_REG + 8);
    ns_set(w);
    NS_LEFT = w && wcur ? *wcur : 0;
}

#ifdef NS
void swe_stfm_guard(void)
{
    u8 *wcur = (u8 *)rd32(SWE_REG + 8);
    if (!NS_LEFT || SEL_MODE != 0xFFFFFFFF || !wcur)
        return;
    if (*wcur == NS_LEFT && *(u16 *)SWE_GTYPE != GAME_TYPE_CAREER)
        ns_set(0);
    NS_LEFT = 0;
}
#endif

void swe_sel_pre(u32 mode)
{
    SEL_MODE = mode;
    u32 *c254 = (u32 *)rd32(SWE_REG + 12);
    SEL_C254 = *c254;
    SEL_ON = 0;
    u32 cw = rd32(SWE_REG + 16), set = rd32(SWE_REG + 28);
    if (!cw || !set || (mode != M_CAREER && *(u16 *)SWE_TTYPE != CLUB_TEAMS) || !*comp_slot(CAREERS))
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
        SWE_D0[0] = WMENU + dw;         /* (GoGetTeamsForPlay's 255 / mainbtn mb_d0's: the top list) */
    } else {
        u8 *t = (u8 *)list_ids(cw);
        while (*t != 0xFF && *t != CAREERS)
            t++;
        SEL_TOP = t[0] == CAREERS && t[1] == 0xFF && t[2] == 0xFF ? t : 0;
    }
    sel_lists();
}

void swe_sel_ns(u32 w)                  /* careerworld w_ns_menu, every list: w = the world on the path (0 = base) */
{
    if (SEL_MODE == 0xFFFFFFFF || !SEL_ON)
        return;
    u32 n = *(u16 *)SWE_NUMSEL;
    if (SEL_MODE == M_CAREER)           /* (one club: no lock) */
        n = 0;
    if (!n)
        SEL_CW = 0;
    else if (n > SEL_N && !SEL_CW && w)
        SEL_CW = w;
    SEL_N = n;
    sel_lists();
}

static void sel_restore(void)           /* the game's lists back */
{
    *(u32 *)rd32(SWE_REG + 12) = SEL_C254;
    if (SEL_ON) {
        *SEL_SLOT98 = SEL_O98;
        if (SEL_DW)
            *SEL_SLOTD = SEL_OD;
        top_restore();
        title_restore();
    }
}

void swe_sel_post(void)
{
    sel_restore();
    if (SEL_ON) {
        SWE_CWORLD = *(u16 *)SWE_NUMSEL ? SEL_CW : 0;
        ns_left(SWE_CWORLD);
    }
    SEL_ON = 0;
    SEL_MODE = 0xFFFFFFFF;
}

/* W-modes M3: the career's team choice (ChooseTeamsDialog's SelectTeamsFinalMenu call after mainbtn's mb_d0, only for
   SELECT TEAM TO MANAGE: a player purchase's team choice stays the game's) lists the worlds as the friendly picker
   (the default world's list, MONDO 2026-27 next to STORICO), with no lock (one club). The namespace stays the one the
   path left (careerworld w_ns_menu): InitCareer's w_load1 reads it for the career's world. */
extern u8 MB_HDR[], MB_STR[];
u32 CAR_ON DATA = 0;

/* M3 (Davide 04/11): the coach's nationality list follows the career's world, chosen with the team (careerworld nat_init
   picked it at CareerMenuInit from the default world): today's list for World 2026-27, else the era list. A
   nationality not in the new list -> its era counterpart (careerworld.NAT_ERA, swe.py writes the pairs), else ENG. */
#ifdef NAT
extern u8 CW_PLNAT[], CW_NATPTR[], CW_NATORD[], CW_NATORD27[], CW_WRAPD[], CW_WRAPI[];
u8 NATMAP27[32] DATA = {0xFF};          /* (from, to) pairs to today's list, FF */
u8 NATMAPERA[64] DATA = {0xFF};         /* to the era list */
#define NAT_ENG 8

u32 swe_nat_fix(u32 today)
{
    const u8 *l = today ? CW_NATORD27 : CW_NATORD, *m = today ? NATMAP27 : NATMAPERA;
    u32 n = 0;
    while (l[n] != 0xFF)
        n++;
    n++;                                /* (OTHER, FF, is the list's last entry: ChangeNationality wraps after it) */
    *(u32 *)CW_NATPTR = (u32)l;
    *CW_WRAPI = (u8)n;
    *CW_WRAPD = (u8)(n - 1);
    u8 c = *CW_PLNAT;
    for (u32 k = 0; k < n; k++)
        if (l[k] == c)
            return c;
    for (const u8 *p = m; *p != 0xFF; p += 2)
        if (p[0] == c)
            return *CW_PLNAT = p[1];
    return *CW_PLNAT = NAT_ENG;
}

/* (obj4 header +60) */
const u32 NAT_X[6] = {(u32)swe_nat_fix, (u32)CW_PLNAT, (u32)NATMAP27, (u32)NATMAPERA, (u32)CW_NATORD,
                      (u32)CW_NATORD27};
#endif

void swe_car_pre(void)
{
    CAR_ON = rd32(MB_HDR) == (u32)MB_STR;
    if (!CAR_ON)
        return;
    NS_LEFT = 0;                        /* (the career's picker owns the namespace: no guard after it) */
    swe_sel_pre(M_CAREER);
}

void swe_car_post(void)
{
    if (!CAR_ON)
        return;
    sel_restore();
#ifdef NAT
    u8 *wcur = (u8 *)rd32(SWE_REG + 8);
    if (wcur)
        swe_nat_fix(*wcur == SET_W[0]);   /* (the namespace the path left: World 2026-27's = its number) */
#endif
    SEL_ON = 0;
    SEL_MODE = 0xFFFFFFFF;
    CAR_ON = 0;
}

__attribute__((naked)) void swe_car_tramp(void)
{
    __asm__ volatile("pushal\n\tcall swe_car_pre\n\tpopal\n\tcall SWE_CARPICK\n\t"
                     "pushfl\n\tpushal\n\tcall swe_car_post\n\tpopal\n\tpopfl\n\tret");
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

/* after LoadDIYFile: the block only on a file of the game's size + 4; then the contest's namespace */
void swe_diy_loaded(void)
{
    SWE_CWORLD = 0;
    if (*(u16 *)SWE_D0 || !DIY_NAME) {
        ns_left(0);
        return;
    }
    int h = dos_open(DIY_NAME, 0);
    if (h < 0)
        return;
    u32 n = dos_end(h);
    dos_close(h);
    const u8 *b = SWE_NUMSEL + 2 + 684 * *(u16 *)SWE_NDIY;
    if (n == diy_size() + 4 && b[0] == 'W' && b[1] == 'M' && b[2] == 1 && b[3] && reg_world(b[3]))
        SWE_CWORLD = b[3];
    ns_left(SWE_CWORLD);
}

#ifdef NS
/* SelectTeamsFinalMenu's entry (a jmp of an earlier patch there, chained: SWE_STFM) */
__attribute__((naked)) void swe_stfm_tramp(void)
{
    __asm__ volatile("pushfl\n\tpushal\n\tcall swe_stfm_guard\n\tpopal\n\tpopfl\n\tjmp SWE_STFM");
}
#endif

__attribute__((naked)) void swe_names_tramp(void)
{
    __asm__ volatile("call SWE_NAMES\n\tpushfl\n\tpushal\n\tcall swe_names_post\n\tpopal\n\tpopfl\n\tret");
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
