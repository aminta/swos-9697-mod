/* 4.2 preseason friendlies, the chooser page (Davide 16/11; owner Friends Choice, 42-frchoose). obj4 band FRCH
   (swreg.FRCH_AT, tools/frchoose.py: this file + frcsel.c, then the glue with the packed menu FC_MENU and the
   language's strings).

   WHEN: the engine's season-start step (Motore's fr_season, the tail of InitializeNewSeason, careers only, never on a
   load) calls frc_choose(ctx, given, venues) before its one installing fr_pick call (tools/frnd.h). The page only
   previews: what it shows is fr_pick's own answer for the state on screen (tools/frcsel.h), and what it hands back
   (given[], venues, the level in FR_ST +10 bits 14-15) makes the engine's call give exactly that.
   No page (given / venues untouched = the plain automatic pick): under SWOS++, or when fr_pick refuses the page's
   opening state (no table, club not in it, no room: the engine's own "no friendlies this season" path).

   THE PAGE (entries FC_E_*; frchoose.py builds the packed menu from the same numbers):
     title; the legend (3 colour boxes in the row above the rows: only the colours painted, CONVENTIONS 5-6);
     AUTOMATIC  MIX / EASY / MEDIUM / HARD      LEFT / RIGHT / FIRE: what an empty row is (frcsel.h)
     4 rows:  venue | club | band box | level   FIRE on the venue: the swap (2 home + 2 away stay)
                                                FIRE on the club: a chosen club -> back to automatic; an automatic
                                                one -> the game's club browser (FC_K = the row; the glue calls it)
     a message line (why the last change was refused: never a silent replacement); CONTINUE (the cursor starts here).
   Every row shows its club (automatic rows too, Davide's D4): the name comes from the game's GetTeamPointer (the
   team cache, the career's pool, else the club's team file), read once per club. The band box = the club against
   MY club (fr_pick's band; the far bands are painted as stronger / weaker), the figure 1-5 = fr_level (the world's
   quintile, Davide's D5). A chosen club's name box has its own colour.

   THE CLUB LIST (the game's chooseTeamsFriendlyMenu while FC_K is a row): fc_list, called after the game built the
   list, paints each listed club by the band it would have in that row; grey = fr_pick would refuse it (picking it
   anyway shows the reason on the page).

   The menu is re-unpacked by the game after every nested menu: fc_paint (init, onReturn, after every action) redraws
   everything from the state. DOS/4GW zeroes nothing: frc_choose sets every variable it reads.
   Harness (test builds read them by symbol): FC_TRACE bit 0 = the page was shown this season start, bits 1-7 = the
   last refusal's text (FRC_M_*); FC_SEL (the state); FC_NAME. */
#include "frcsel.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define FC_E_TITLE  0
#define FC_E_LEG    1                   /* 3: stronger, similar, weaker */
#define FC_E_LVLL   4
#define FC_E_LVL    5
#define FC_E_ROW    6                   /* 4 x (venue, club, band, level) */
#define FC_E_MSG    22
#define FC_E_GO     23
#define FC_NE       24

#define FC_C_STRONG 0x0C                /* orange */
#define FC_C_SIMIL  0x0D                /* light blue */
#define FC_C_WEAK   0x0E                /* green */
#define FC_C_NO     0x02                /* grey: a club fr_pick would refuse */
#define FC_C_AUTO   0x09                /* a row's club box: automatic / chosen */
#define FC_C_CHOSEN 0x0A

#define FC_LIST0    7                   /* chooseTeamsFriendlyMenu: the clubs' entries 7 .. 54 */
#define FC_LIST1    55
#define FC_NL       20                  /* a name's bytes (the team record's name: 17 B at +5, NUL-ended) */

extern u8 DREG[];                       /* the game's D0..D7, A0..A6 (60 B) */
extern u8 SWOSPP;                       /* 0FFh = no SWOS++ */
extern const char FC_S_LVL[FRC_LEVELS][16];
extern const char FC_S_BAND[3][12];
extern const char FC_S_VEN[2][4];       /* home, away */
extern const char FC_S_MSG[FRC_M_COUNT][40];
extern u8 MENU[];                       /* g_currentMenu: the unpacked menu (16h header, 38h an entry) */
void GTP(void);                         /* GetTeamPointer: word D0 = a team word -> A0 = its record */
void FC_SHOW(void);                     /* the glue: ShowMenu(FC_MENU) with the game's registers kept */

FrcSel FC_SEL;
char FC_NAME[4][FC_NL];
u16 FC_NW[4];                           /* the club FC_NAME[k] is the name of (FR_NONE: none) */
char FC_LV[4][2];
u32 FC_K = 4;                           /* the row whose club is being browsed (4 = none: also before the first
                                           season start - the club list's hook runs in every club browser) */
u8 FC_TRACE;

#define D(k) (*(u32 *)(DREG + 4 * (k)))
#define A(k) (*(u32 *)(DREG + 32 + 4 * (k)))

static void p16(u8 *p, u32 v) { p[0] = (u8)v; p[1] = (u8)(v >> 8); }
static void p32(u8 *p, u32 v) { p16(p, v); p16(p + 2, v >> 16); }

#if defined(__i386__)                   /* (the exe; the host tests' cc has no x86 asm: no game there) */
#define P32(p) ((u32)(p))                /* the game's pointers are 32-bit */
#define PTR(v) ((const u8 *)(v))
static u8 *ent(u32 k) { return MENU + 0x16 + 0x38 * k; }   /* the shown (unpacked) menu's entry k */
static const u8 *team(u32 w) {          /* club w's record: the cache, the career's pool, else its team file (the
                                           game's routine does not report a miss: w is a club of the pick's table) */
    u32 d0 = D(0), a0 = A(0);
    const u8 *r;
    D(0) = w;
    __asm__ volatile("pushal\n\tcall GTP\n\tpopal" : : : "memory", "cc");
    r = PTR(A(0));
    D(0) = d0; A(0) = a0;
    return r;
}
static void show(void) { __asm__ volatile("pushal\n\tcall FC_SHOW\n\tpopal" : : : "memory", "cc"); }
#else
u8 *fc_host_ent(u32 k);
const u8 *fc_host_team(u32 w);
void fc_host_show(void);
static u8 *ent(u32 k) { return fc_host_ent(k); }
static const u8 *team(u32 w) { return fc_host_team(w); }
static void show(void) { fc_host_show(); }
const u8 *fc_host_ptr(u32 v);           /* (a 64-bit host: the pointer whose low 32 bits are v) */
#define P32(p) ((u32)(unsigned long)(p))
#define PTR(v) fc_host_ptr(v)
#endif

static u32 bidx(u32 band) {             /* a band -> its legend box: 0 stronger, 1 similar, 2 weaker */
    return band == FR_SIMILAR ? 1 : band == FR_STRONGER || band == FR_FAR_UP ? 0 : 2;
}

static const u8 fc_col[3] = { FC_C_STRONG, FC_C_SIMIL, FC_C_WEAK };

static void text(u8 *e, const char *s) { p32(e + 0x26, P32(s)); }

void fc_paint(void) {                   /* the menu's onInit / onReturn, and after every action */
    const FrcSel *s = &FC_SEL;
    const FrcCtx *c = s->c;
    u32 used = 0, k, i;
    for (k = 0; k < 4; k++) {
        u32 w = s->out.word[k], b = bidx(s->out.band[k]), lv;
        u8 *e = ent(FC_E_ROW + 4 * k);
        if (FC_NW[k] != w) {
            const u8 *r = team(w);
            for (i = 0; i < FC_NL - 1 && r && r[5 + i]; i++)
                FC_NAME[k][i] = (char)r[5 + i];
            FC_NAME[k][i] = 0;
            FC_NW[k] = (u16)w;
        }
        used |= 1u << b;
        text(e, FC_S_VEN[s->out.home >> k & 1 ? 0 : 1]);
        e += 0x38;
        text(e, FC_NAME[k]);
        p16(e + 0x1E, s->club[k] != FR_NONE ? FC_C_CHOSEN : FC_C_AUTO);
        e += 0x38;
        text(e, FC_S_BAND[b]);
        p16(e + 0x1E, fc_col[b]);
        e += 0x38;
        lv = fr_level(c->frss, c->len, c->world, (u16)w);
        FC_LV[k][0] = (char)('0' + lv);
        FC_LV[k][1] = 0;
        text(e, FC_LV[k]);
        p16(e + 0x1E, fc_col[b]);
    }
    for (k = 0; k < 3; k++) {
        u8 *e = ent(FC_E_LEG + k);
        p16(e + 4, !(used >> k & 1));
        text(e, FC_S_BAND[k]);
    }
    text(ent(FC_E_LVL), FC_S_LVL[s->level]);
    text(ent(FC_E_MSG), FC_S_MSG[frc_msg(s->msg)]);
    FC_TRACE = (u8)(1 | frc_msg(s->msg) << 1);
}

void fc_level(void) {                   /* the AUTOMATIC row: LEFT one back, RIGHT / FIRE one on */
    frc_set_level(&FC_SEL, DREG[28] & 0x40 ? -1 : 1);
    fc_paint();
}

void fc_venue(u32 k) {
    frc_swap_venue(&FC_SEL, k);
    fc_paint();
}

u32 fc_club(u32 k) {                    /* FIRE on row k's club: 1 = the glue opens the club browser */
    if (FC_SEL.club[k] == FR_NONE) {
        FC_K = k;
        return 1;
    }
    frc_set_club(&FC_SEL, k, FR_NONE);
    fc_paint();
    return 0;
}

void fc_picked(void) {                  /* back from the browser: word D0 = FFFFh aborted, else A0 = the club's record */
    u32 k = FC_K;
    FC_K = 4;
    if (k < 4 && (u16)D(0) != 0xFFFF && A(0)) {
        const u8 *r = PTR(A(0));
        frc_set_club(&FC_SEL, k, (u16)(r[0] | r[1] << 8));
    }
    fc_paint();
}

void fc_list(void) {                    /* after the game built its club list (chooseTeamsFriendlyMenu) */
    u32 k = FC_K, i;
    if (k >= 4)
        return;
    for (i = FC_LIST0; i < FC_LIST1; i++) {
        u8 *e = ent(i), band;
        const u8 *r;
        if (e[4] | e[5])                /* (not shown) */
            continue;
        r = PTR(*(u32 *)(e + 0x26) - 5);
        p16(e + 0x1E, frc_trial(&FC_SEL, k, (u16)(r[0] | r[1] << 8), &band) ? FC_C_NO : fc_col[bidx(band)]);
    }
}

void frc_choose(const FrcCtx *c, uint16_t given[4], uint8_t *venues) {
    u32 k;
    FC_TRACE = 0;
    FC_K = 4;
    if (SWOSPP != 0xFF)
        return;
    if (frc_init(&FC_SEL, c))
        return;
    for (k = 0; k < 4; k++)
        FC_NW[k] = FR_NONE;
    show();
    FC_K = 4;
    frc_result(&FC_SEL, given, venues);
}

/* One object in the band (cobj.link takes one): the selection state always; the pick itself only where the engine's
   FRND band is not linked yet (frchoose.py FRC_OWN_PICK: a build of this branch alone - the exe then has no caller
   of frc_choose but the test probe). With FRND, fr_pick / fr_level are its symbols: one copy of the pick in the exe. */
#ifndef FRC_NO_UNITY
#include "frcsel.c"
#ifdef FRC_OWN_PICK
#include "frpick.c"
#endif
#endif
