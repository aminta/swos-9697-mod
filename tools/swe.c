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
#define NAT_TEAMS 0                     /* (teamsType: 1 club, 0 national, 2 original, 3 custom: the menu's setters) */
#define DATA __attribute__((section(".data")))   /* (initialised: obj4's .bss is not zeroed at boot) */

extern u8 SWE_D0[], SWE_NUMSEL[], SWE_TTYPE[], SWE_A0[], SWE_NDIY[], SWE_CFB[];
u32 SEL_ON DATA = 0;                    /* 1 = this picker lists the worlds */
u32 SEL_DW DATA = 0;                    /* the default world (0 = the 1996-97 game) */
u32 SEL_CW DATA = 0;                    /* the contest's career world, 0 = none yet */
u32 SEL_N DATA = 0;                     /* NUMSEL at the last list */
u32 SEL_LW DATA = 0;                    /* the world of the last list (the one new picks came from) */
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

/* 4.1 (Davide 07/11, MiSTer): a career's team choice lists the main menu's world only - no STORICO box, no green
   MONDO 2026-27 entry (the world is the main menu's WORLD button's); the friendly / DIY pickers keep both (mixing) */
static int cur_entry(void)              /* MONDO 2026-27 is an entry of the default world's list */
{
    return SEL_MODE != M_CAREER && SEL_DW != SET_W[0] && friendly_world(SET_W[0]) && !locked(SET_W[0]);
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
    int hist = h > L_HIST + 4 && SEL_MODE != M_CAREER;   /* (an empty STORICO is left out; a career: none) */
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

/* Step 2.5 (Davide 2026-11-05): a picker with none of the default world's own content shows a message on the spot,
   2 lines in the list area: PRESET (COMP. PREDEFINITA) and SEASON (STAGIONE) under MONDO 2026-27 / EUROPA 1984-85
   (their purple TORNEI STORICI / STAG. STORICHE box stays below, the 1996-97 continents are the 1996-97 world's), the
   friendly / DIY NAZIONALI under MONDO 2026-27. The preset / season tramps (or swe_sel_pre) arm it; at
   SelectTeamsFinalMenu's entry (swe_stfm_guard) the top list (competitionsTable[254], what the caller set) becomes
   L_AV: no competitions, the list's box id 3 times (preset / season: 2 message rows + the box) or a continent twice
   (nationals: 2 rows); swe_names_post turns the first two rows of that list (the two equal names) into the message
   (disabled, the list area's width). The caller's pop / sel_restore puts the game's table back. */
#define AV_PRESET 1
#define AV_SEASON 2
#define AV_NAT 3
#define AV_EU 4                         /* (no message: EUROPA 1984-85's nationals, its one continent - Europe) */
#define AV_LEN 40
#define AV_COLOR 0                      /* (no button: the text on the menu's background) */
#define AV_GAP 5                        /* (historic MENU_GAP) */
u8 AV_TXT[3][2][AV_LEN] DATA = {{{0}}}; /* swe.py AV_LINES, the exe's language: [kind - 1][line] */
u32 AV_ARM DATA = 0;                    /* the message the next picker shows (AV_*), 0 = none */
u32 AV_SHOW DATA = 0;                   /* the message this picker's top list shows */
/* 4.1 ESCI next to ABBANDONA (Davide 06/11, MiSTer): on the nationals' message the game leaves ABBANDONA alone, which
   quits the whole choice. ESCI (the game's own word, swe.py AV_ESC) opens the team kinds menu (CLUB / NAZIONALI /
   PERSONALIZZATE: GoGetTeamsForPlay's, SWE_CHOOSE) from its on-select, as the game's own buttons open theirs (a menu
   opened after the picker's exit took the fire still held under SWOS++). Its ESCI: the message again; a kind chosen:
   out of the picker the way ABBANDONA goes (ExitSelectTeams), then swe_sel_tramp runs the picker again for that kind
   (GoGetTeamsForPlay after its kinds menu, AV_AFTER). The contest's editor and its teams stay as they were. */
extern u8 SWE_CHOOSE[], SWE_KEYCOUNT[], SWE_LASTKEY[];                 /* GoGetTeamsForPlay: mov [A6], offset chooseTeamsMenu; call ShowMenu; mov ax, [teamsType] */
u8 AV_ESC[12] DATA = {0};
u32 AV_ABORT DATA = 0;                  /* ABBANDONA's on-select (entry 88: ExitSelectTeams) */
u32 AV_BACK DATA = 0;                   /* a kind chosen through ESCI: the picker again */
u32 AV_AFTER DATA = 0;
void swe_av_esci(void);
u8 L_AV[12] DATA = {0};

#ifdef OMM
extern u8 MB_OMM[];                     /* mainbtn's mb_omm: the patcher's 'Original main menu' (4.1, Marco) */
#endif
static u32 set_w(void)                  /* the default-world setting (SETUP.DAT +105, mainbtn); the option: 1, the */
{                                       /* 1996-97 game, whatever the file holds (it is not touched) */
#ifdef OMM
    if (MB_OMM[0])
        return 1;
#endif
    u32 set = rd32(SWE_REG + 28);
    return set ? *(u8 *)set : 0;
}

static u32 av_world(void)               /* the default world (SETUP.DAT +105 -> SET_W), 0 = the 1996-97 game */
{
    u32 s = set_w();
    return s < sizeof SET_W ? SET_W[s] : 0;
}

static void av_arm(u32 kind) { AV_ARM = kind == AV_EU || AV_TXT[kind - 1][0][0] ? kind : 0; AV_SHOW = 0; }

/* EUROPA 1984-85's nationals (DaniSwos, packs/europe-1984-85/national) in a friendly / DIY: careerworld w_tmap maps a
   national file 80..85 to the world's own (WNAT, TEAM.180..) by CW_FNAT outside a career, as by the career's world byte
   inside one. Set by the friendly / DIY picker's national branch under that default world (or a DIY file of that
   world), cleared by any other picker kind's entry (preset, season, team editor: the game's TEAM.080). */
#ifdef FNAT
extern u8 CW_FNAT[];
static void fnat(u32 w) { CW_FNAT[0] = w; }
static u32 fnat_on(void) { return CW_FNAT[0]; }
#else
static void fnat(u32 w) { (void)w; }
static u32 fnat_on(void) { return 0; }
#endif

#ifdef NS                               /* (its one caller: swe_stfm_guard) */
static void av_swap(void)               /* at SelectTeamsFinalMenu's entry: the armed message's top list */
{
    u32 kind = AV_ARM, *c254 = (u32 *)rd32(SWE_REG + 12);
    AV_ARM = 0;
    if (!kind || !*c254)
        return;
    const u8 *p = list_ids(*c254);
    u8 b = 0xFF, *l = L_AV + 4;
    for (; *p != 0xFF; p++)
        b = (kind == AV_NAT || kind == AV_EU) && b != 0xFF ? b : *p;   /* (nationals: the first continent, EUROPA; else the box, the last id) */
    if (b == 0xFF)
        return;
    put_ff(L_AV);
    *l++ = b;
    if (kind != AV_EU)
        *l++ = b;
    if (kind == AV_PRESET || kind == AV_SEASON)
        *l++ = b;
    *l = 0xFF;
    *c254 = (u32)L_AV;
    AV_SHOW = kind == AV_EU ? 0 : kind;
}
#endif

static void av_esc(u8 *ent, u8 *after)  /* ESCI: a list row the message leaves hidden, as ABBANDONA left of it */
{
    u8 *ab = ent + 88 * 56, *x = after + 56;
    while (*(u16 *)(x + 2) != 87 && !*(u16 *)(x + 4))
        x += 56;
    if (*(u16 *)(x + 2) == 87)
        return;
    u16 ord = *(u16 *)(x + 2);
    for (int k = 0; k < 56; k++)
        x[k] = ab[k];
    *(u16 *)(x + 2) = ord;
    *(u16 *)(x + 0x14) -= *(u16 *)(ab + 0x18) + 4;
    *(u16 *)(x + 0x1E) = (*(u16 *)(x + 0x1E) & 0xFFF0) | 0x0C;   /* (the game's ESCI colour, orange; ABBANDONA's red) */
    *(u32 *)(x + 0x26) = (u32)AV_ESC;
    AV_ABORT = rd32(ab + 0x2A);
    *(u32 *)(x + 0x2A) = (u32)swe_av_esci;
    x[8] = x[10] = x[11] = 0xFF;        /* (left, up, down: none; right: ABBANDONA) */
    x[9] = 88;
    ab[8] = (u8)ord;
}

static void av_rows(u8 *e0)             /* the message in the top list's first two rows (e0 = entry 21) */
{
    u8 *r[2], *e = e0;
    int n = 0;
    for (int k = 0; k < 64 && n < 2 && *(u16 *)(e + 2) != 87; k++, e += 56)
        if (!*(u16 *)(e + 4))
            r[n++] = e;
    if (n < 2)
        return;
    u32 t0 = rd32(r[0] + 0x26), t1 = rd32(r[1] + 0x26), m0 = (u32)AV_TXT[AV_SHOW - 1][0];
    if (t0 != t1 && t0 != m0)           /* (a list below the top one: the rows are not the two equal names) */
        return;
    for (int j = 0; j < 2; j++) {
        *(u32 *)(r[j] + 0x26) = (u32)AV_TXT[AV_SHOW - 1][j];
        *(u16 *)(r[j] + 6) = 1;         /* disabled */
        *(u16 *)(r[j] + 0x1E) = AV_COLOR;
        *(u16 *)(r[j] + 0x14) = 10;     /* x, width: the list area (the title bar's) */
        *(u16 *)(r[j] + 0x18) = 300;
        if (AV_SHOW != AV_NAT)
            *(u16 *)(r[j] + 0x16) -= AV_GAP;   /* (the box's gap above it, as historic's MENU_GAP gave it to all 3) */
    }
    u8 *m = e0 - 21 * 56 - 0x16, *to = 0;   /* the menu's header: the cursor off the rows (the box, else ABBANDONA) */
    u32 *sel = (u32 *)(m + 0x0C);
    if (*sel == (u32)r[0] || *sel == (u32)r[1]) {
        for (u8 *x = r[1] + 56; !to && *(u16 *)(x + 2) != 87; x += 56)
            if (!*(u16 *)(x + 4) && !*(u16 *)(x + 6))
                to = x;
        *sel = (u32)(to ? to : m + 0x16 + 88 * 56);
    }
    if (AV_SHOW == AV_NAT && AV_ESC[0])     /* (4.1: after the cursor - it stays on ABBANDONA, the game's) */
        av_esc(m + 0x16, r[1]);
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

/* 4.1 (Davide 06/11, option A): STORICO > MONDO 1996-97's continent buttons with the year ('EUROPA 96-97': 1996-97 is wider than NORDAMERICA's 100 px, Davide ok 07/11): pairs
   (a proxy's own NAME, its text with the year), swe.py w0_proxies; the titles keep the NAME. */
const u8 *W0_YR[2 * 8] DATA = {0};
#define W0_BTN 100                      /* (the list's button width, x at +0x14, width at +0x18) */
#define W0_WIDEN 12

void swe_names_post(void)
{
    u32 nm = rd32(SWE_CT + 4 * (WMENU + SET_W[0]));
    u8 *e0 = (u8 *)rd32(SWE_EFV), *e = e0;
    if (AV_SHOW && e)
        av_rows(e);
    if (!SEL_ON || !nm || !e)
        return;
    int worlds = 0;
    for (int k = 0; k < 64 && *(u16 *)(e + 2) != 87; k++, e += 56) {   /* (ordinal 87: the end of the entries) */
        if (*(u16 *)(e + 4))
            continue;
        for (int j = 0; j < 8 && W0_YR[2 * j]; j++)
            if (rd32(e + 0x26) == (u32)W0_YR[2 * j]) {
                *(u32 *)(e + 0x26) = (u32)W0_YR[2 * j + 1];
                if (*(u16 *)(e + 0x18) == W0_BTN) {   /* (the one column of 100 px: 'NORTH AMERICA 96-97' is 102) */
                    *(u16 *)(e + 0x14) -= W0_WIDEN / 2;
                    *(u16 *)(e + 0x18) += W0_WIDEN;
                }
            }
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
/* Step 2.5, for Panchina's 2026-27 long bench (friendly / DIY): SWE_W27 = 1 while the contest a friendly / DIY picker
   or a DIY file load left is World 2026-27's (any of its clubs: mixed contests take the longer bench, Davide 05/11),
   0 after any other picker kind (preset, season, team editor, a career's team choice). swe.LABELS['SWE_W27'] after
   swe.patch(p). */
u32 SWE_W27 DATA = 0;
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
    if (SEL_MODE == 0xFFFFFFFF) {       /* (another picker kind: the game's nationals, no 2026-27 contest) */
        fnat(0);
        SWE_W27 = 0;
    }
    if (AV_ARM)
        av_swap();
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
    if (mode == M_FRIENDLY && *(u16 *)SWE_TTYPE == NAT_TEAMS) {   /* (step 2.5: NAZIONALI) */
        u32 w = av_world();
        fnat(0);
        if (w == SET_W[0])
            av_arm(AV_NAT);             /* MONDO 2026-27: the message */
        else if (w == SET_W[2] && reg_world(w)) {
            fnat(w);                    /* EUROPA 1984-85: DaniSwos's nations, Europe only */
            av_arm(fnat_on() ? AV_EU : 0);
        }
        ns_left(0);                     /* (the national lists pass no w_ns_menu: a 2026-27 contest's namespace left
                                           here named TEAM.180.. / TEAM.080 tmw5.nnn - 2026-27's Saudi clubs) */
    }
    if (!cw || !set || (mode != M_CAREER && *(u16 *)SWE_TTYPE != CLUB_TEAMS) || !*comp_slot(CAREERS))
        return;
    u32 s = set_w(), dw = s < sizeof SET_W ? SET_W[s] : 0;
    if (dw && !friendly_world(dw))
        dw = 0;
    SEL_ON = 1;
    SEL_DW = dw;
    SEL_CW = 0;
    SEL_N = 0;
    SEL_LW = 0;
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
    else if (n > SEL_N && !SEL_CW && SEL_LW)
        SEL_CW = SEL_LW;                /* (the picks came from the list shown last, not from this one) */
    SEL_N = n;
    SEL_LW = w;
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
    AV_ARM = AV_SHOW = 0;
    sel_restore();
    if (SEL_ON && SEL_MODE != M_CAREER && !SEL_CW && *(u16 *)SWE_NUMSEL > SEL_N && SEL_LW)
        SEL_CW = SEL_LW;                /* (picks in the last list: a toggle redraws no list, no swe_sel_ns saw them) */
    if (SEL_ON) {
        SWE_CWORLD = *(u16 *)SWE_NUMSEL ? SEL_CW : 0;
        ns_left(SWE_CWORLD);
    } else if (SEL_MODE == M_FRIENDLY && fnat_on())
        SWE_CWORLD = *(u16 *)SWE_NUMSEL ? fnat_on() : 0;   /* (the DIY file's 'WM' block: its nationals' world) */
    SWE_W27 = SEL_ON && SEL_MODE == M_FRIENDLY && SWE_CWORLD == SET_W[0];   /* (clubs only: SEL_ON) */
    SEL_ON = 0;
    SEL_MODE = 0xFFFFFFFF;
}

/* W-modes M3: the career's team choice (ChooseTeamsDialog's SelectTeamsFinalMenu call after mainbtn's mb_d0, only for
   SELECT TEAM TO MANAGE: a player purchase's team choice stays the game's) lists the worlds as the friendly picker
   (the default world's list, MONDO 2026-27 next to STORICO), with no lock (one club). The namespace stays the one the
   path left (careerworld w_ns_menu): InitCareer's w_load1 reads it for the career's world. */
#ifdef MB                               /* (a build with mainbtn's world switch: else no career picker hook) */
extern u8 MB_HDR[], MB_STR[];
u32 CAR_ON DATA = 0;
#endif

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

#ifdef MB
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
#endif

/* GoGetTeamsForPlay's picker call (swe.py pick_site) lands here: SWE_PICK = what that call reached before (chained) */
__attribute__((naked)) void swe_sel_tramp(void)
{
    __asm__ volatile("pushal\n\tpushl %0\n\tcall swe_sel_pre\n\taddl $4, %%esp\n\tpopal\n\t"
                     "call SWE_PICK\n\tpushal\n\tcall swe_sel_post\n\tpopal\n\t"
                     "cmpl $0, AV_BACK\n\tjne 1f\n\tret\n"
                     "1:\tmovl $0, AV_BACK\n\tpushal\n\tcall swe_av_clear\n\tpopal\n\taddl $4, %%esp\n\tjmp *AV_AFTER"
                     : : "i"(M_FRIENDLY));
}

void swe_av_kinds(void)                 /* ESCI fired: the kinds menu over the picker; AV_BACK = a kind chosen */
{
    u8 *c = SWE_CHOOSE;
    short *tt = (short *)rd32(c + 17), was = *tt;
    *(u32 *)rd32(c + 2) = rd32(c + 6);
    *(u16 *)SWE_KEYCOUNT = *(u16 *)SWE_LASTKEY = 0;   /* (ESCI's key is not read again by the kinds menu) */
    u32 show = (u32)(c + 15) + rd32(c + 11);
    __asm__ volatile("pushal\n\tcall *%0\n\tpopal" : : "r"(show) : "memory", "cc");
    AV_AFTER = (u32)(c + 15);
    AV_BACK = *tt >= 0;
    if (!AV_BACK)                       /* (its ESCI: teamsType -1 - the nationals' picker goes on as it was) */
        *tt = was;
}

void swe_av_clear(void)                 /* ExitSelectTeams' abortSelectTeams = 1 (its `mov word [x], 1`) back to 0 */
{
    u8 *f = (u8 *)AV_ABORT;
    for (int k = 0; k < 0x80; k++)
        if (f[k] == 0x66 && f[k + 1] == 0xC7 && f[k + 2] == 5 && f[k + 7] == 1 && f[k + 8] == 0) {
            *(u16 *)rd32(f + k + 3) = 0;
            return;
        }
}

/* 4.1: ESCI on the nationals' message (av_esc) */
__attribute__((naked)) void swe_av_esci(void)
{
    __asm__ volatile("pushal\n\tcall swe_av_kinds\n\tpopal\n\tcmpl $0, AV_BACK\n\tjne 1f\n\tret\n1:\tjmp *AV_ABORT");
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
    fnat(SWE_CWORLD == SET_W[2] ? SWE_CWORLD : 0);   /* (step 2.5: a 1984-85 DIY's nationals are DaniSwos's) */
    SWE_W27 = SWE_CWORLD == SET_W[0];
}

#if defined(NS) && defined(STFM)
/* SelectTeamsFinalMenu's entry (a jmp of an earlier patch there - menulevels' ml_reset -, chained: SWE_STFM; a build
   with no menulevels has none: no tramp, swe.py) */
__attribute__((naked)) void swe_stfm_tramp(void)
{
    __asm__ volatile("pushfl\n\tpushal\n\tcall swe_stfm_guard\n\tpopal\n\tpopfl\n\tjmp SWE_STFM");
}
#endif

/* Step 2.5: the preset / season selectors' picker calls (historic.CALLS: hist_preset / mkseason's season_sel, chained) */
void swe_av_pre(u32 kind)
{
    if (av_world())
        av_arm(kind);
}

void swe_av_post(void) { AV_ARM = AV_SHOW = 0; }

#ifdef AV
__attribute__((naked)) void swe_pre_tramp(void)
{
    __asm__ volatile("pushal\n\tpushl %0\n\tcall swe_av_pre\n\taddl $4, %%esp\n\tpopal\n\t"
                     "call SWE_PREPICK\n\tpushfl\n\tpushal\n\tcall swe_av_post\n\tpopal\n\tpopfl\n\tret"
                     : : "i"(AV_PRESET));
}

__attribute__((naked)) void swe_sea_tramp(void)
{
    __asm__ volatile("pushal\n\tpushl %0\n\tcall swe_av_pre\n\taddl $4, %%esp\n\tpopal\n\t"
                     "call SWE_SEAPICK\n\tpushfl\n\tpushal\n\tcall swe_av_post\n\tpopal\n\tpopfl\n\tret"
                     : : "i"(AV_SEASON));
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

/* LoadPresetFile (the same body: a preset's file has no 'WM' block, so swe_diy_loaded gives the base namespace back -
   a preset loaded after a mixed friendly kept the friendly's, engine_pre_ns 07/11) */
__attribute__((naked)) void swe_pre_load_tramp(void)
{
    __asm__ volatile("pushal\n\tcall swe_diy_name\n\tpopal\n\tcall SWE_LOADPRE\n\tpushfl\n\tpushal\n\t"
                     "call swe_diy_loaded\n\tpopal\n\tpopfl\n\tret");
}
