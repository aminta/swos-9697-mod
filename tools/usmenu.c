/* 4.1 RC2 (Davide 09/11, option A + a): STAT > RIEPILOGO of a world's UEFA cup as a menu of green boxes, one per
   phase as far as the cup has gone (like the conti rounds menu), each opening that phase in the game's own screens.
   obj4, its own page (swreg.USMENU_AT, tools/usmenu.py); ctview's CV_UST (cv_sum's UEFA branch) points at the glue's
   us_open. uesum.c keeps what is shown: the viewed contest (UC / UD), US_REC (us_cur), the page texts.

   The phases (us_list): the league phase (in progress: the real one; over: US_REC's final table on the text page,
   us_lpt - option a), the knockout stages US_REC recorded before the current one, the current stage. An old save
   (US_REC zero), another season's or cup's block (VIEW WORLD's other UEFA cups): the current stage alone.

   A view (us_prep .. us_done): the game's view of a contest (cseg_37B74) copies A0 into the work area (diyFileBufferCopy
   + DIY_competitionStart, B52h for a type-2 contest), shows it, copies the work area back into A0 - and STAT is
   inside the view of the real contest, whose work area is that view's. So the work area and D0..A6 go to ctgame's
   scratch (its P2 guard's place: no conti view is open here), A0 = a copy of the work area in the scratch, and the
   work area and registers come back after it. The copy's current stage (+53h) is the phase; an earlier knockout
   stage's UD is rewritten from US_REC the way the game keeps a round (uesum.c norm(), reversed; ctgame ko_fill's
   fields; +343h the clubs' cache offsets, the screen's names). UD+53h 0 (the round not 'complete': cseg_89B5C's
   career path would advance it - cseg_284D8). US_IN: no RIEPILOGO inside the view (us_ok). */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#include "uesum.h"

extern u8 UC[];                         /* diyFileBufferCopy: the work area (UD = UC + 41Fh) */
extern u8 SCR[];                        /* ctgame's scratch (obj3 zero-fill) */
extern u8 DREG[];                       /* the game's D0..D7, A0..A6 */
extern u32 A0R;
extern u8 *SELPTR;                      /* selTeamsPtr: the team cache (684-byte records, the word at +0) */
extern u16 NUMSEL;
extern u8 US_IN;
const struct cup *us_cur(void);
const char *us_stname(u32 s);
void us_lpt(void);
void us_text(void);
void VC_CALC(void);                     /* CalcMenuEntryAddress: entry D0 -> A0 */

#define BUF 0x0000                      /* the viewed copy (B52h) */
#define WSAVE 0x2000                    /* the work area (B52h), as ctgame's guard */
#define DSAVE 0x2B60                    /* D0..A6 (60) */
#define WORK 0xB52
#define NPH 6                           /* league phase, play-offs, round of 16, QF, SF, final */
#define LW 32                           /* a label's bytes */

#define w16(p) (*(const u16 *)(p))
static void p16(u8 *p, u32 v) { p[0] = (u8)v; p[1] = (u8)(v >> 8); }
static void copy(u8 *d, const u8 *s, u32 n) { while (n--) *d++ = *s++; }
static void p32(u8 *p, u32 v) { p16(p, v); p16(p + 2, v >> 16); }

static u32 toff(u32 w) {                /* club w's record offset in the team cache (FFFFFFFFh: not there) */
    for (u32 i = 0; i < NUMSEL; i++) if (w16(SELPTR + 684 * i) == w) return 684 * i;
    return 0xFFFFFFFFu;
}

u8 US_PH[NPH] = {0};                    /* the menu's entries 1..US_NP: their stages */
u32 US_NP = 0, US_SEL = 0;              /* (US_SEL: the current stage's entry - 1, the cursor) */
char US_LBL[NPH][LW] = {{0}};
char US_TTL[LW] = {0};

void us_list(void) {
    const u8 *UD = UC + 0x41F;
    const struct cup *c = us_cur();
    u32 st = w16(UC + 0x53), n = 0;
    if (st == 0 || (c && c->lw[0])) US_PH[n++] = 0;
    for (u32 s = 1; s < st && s <= NSTG; s++) if (c && c->n[s - 1]) US_PH[n++] = (u8)s;
    if (st && st < NPH) US_PH[n++] = (u8)st;
    US_NP = n;
    US_SEL = n ? n - 1 : 0;
    for (u32 k = 0; k < n; k++) {
        const char *t = us_stname(US_PH[k]);
        u32 i = 0;
        for (; t[i] && i < LW - 1; i++) US_LBL[k][i] = t[i];
        US_LBL[k][i] = 0;
    }
    u32 i = 0;
    for (; i < 24 && UD[4 + i]; i++) US_TTL[i] = (char)UD[4 + i];
    US_TTL[i] = 0;
}

static u8 *ent(u32 k) {                 /* the shown menu's entry k (the game's own CalcMenuEntryAddress) */
    DREG[0] = (u8)k; DREG[1] = DREG[2] = DREG[3] = 0;
    __asm__ volatile("pushal\n\tcall VC_CALC\n\tpopal" : : : "memory", "cc");
    return (u8 *)A0R;
}

void us_minit(void) {                   /* the menu's onInit (and back from a phase): entries past US_NP hidden; links
                                           down the column, the last one's down RIEPILOGO, ESCI's and RIEPILOGO's up it */
    u32 n = US_NP;
    for (u32 k = 1; k <= NPH; k++) {
        u8 *e = ent(k);
        p16(e + 4, k > n);
        e[8] = e[9] = 0xFF;
        e[10] = k > 1 ? (u8)(k - 1) : 0xFF;
        e[11] = k < n ? (u8)(k + 1) : NPH + 1;
    }
    ent(NPH + 1)[10] = n ? (u8)n : 0xFF;
    ent(NPH + 2)[10] = n ? (u8)n : 0xFF;
}

/* an earlier knockout stage s (1..NSTG) into the copy's UD, from US_REC (its ties after n[0..s-2]'s): 0 if a club
   is not in the team cache. The cup screen names a club by +343h, its record's offset in the cache per club index
   (cseg_46589), the team words +24Dh are the match's */
static u32 ko_build(u8 *d, const struct cup *c, u32 s) {
    u32 off = 0, nt = c->n[s - 1], two = 0;
    for (u32 k = 0; k + 1 < s; k++) off += c->n[k];
    const struct tie *t = c->t + off;
    for (u32 i = 0; i < nt; i++) {
        two |= t[i].fl & FL_TWO;
        if (toff(t[i].x) == 0xFFFFFFFFu || toff(t[i].y) == 0xFFFFFFFFu) return 0;
    }
    p16(d + 0x4F, nt);
    p16(d + 0x51, nt);
    p16(d + 0x14B, two ? 2 : 1);
    p16(d + 0x149, two ? 1 : 0);
    p16(d + 0x39, 0xFFFF);
    p16(d + 0x63, 0);
    for (u32 i = 0; i < 32; i++) {
        d[0x89 + i] = 0;
        p16(d + 0xC9 + 2 * i, 0); p16(d + 0x14D + 2 * i, 0); p16(d + 0x1CD + 2 * i, 0);
    }
    for (u32 i = 0; i < nt; i++, t++) {
        u32 fl = t->fl, x1 = t->l1 >> 4, y1 = t->l1 & 15, x2 = t->l2 >> 4, y2 = t->l2 & 15, xp = t->pn >> 4, yp = t->pn & 15;
        u8 *pr = d + 0x2CD + 2 * i, f = 0;
        p16(d + 0x24D + 4 * i, t->x);
        p16(d + 0x24D + 4 * i + 2, t->y);
        p32(d + 0x343 + 8 * i, toff(t->x));
        p32(d + 0x343 + 8 * i + 4, toff(t->y));
        pr[0] = (u8)(2 * i); pr[1] = (u8)(2 * i + 1);
        if ((fl & FL_TWO) && (fl & (FL_LEG1 | FL_PLAYED))) {   /* the second leg's view: y first, the first leg with it */
            pr[0] = (u8)(2 * i + 1); pr[1] = (u8)(2 * i);
            p16(d + 0x14D + 2 * i, y1 << 8 | x1);
            f = 0x20;
            if (fl & FL_PLAYED) {
                f |= (u8)(0x80 | (fl & (FL_DEC | FL_AET | FL_PEN)) | (fl & FL_Y ? 0 : 1));
                p16(d + 0xC9 + 2 * i, y2 << 8 | x2);
                p16(d + 0x1CD + 2 * i, yp << 8 | xp);
            }
        } else if (fl & FL_PLAYED) {
            f = (u8)(0x80 | (fl & (FL_DEC | FL_AET | FL_PEN | FL_Y)));
            p16(d + 0xC9 + 2 * i, x1 << 8 | y1);
            p16(d + 0x14D + 2 * i, x1 << 8 | y1);
            p16(d + 0x1CD + 2 * i, xp << 8 | yp);
        }
        d[0x89 + i] = f;
    }
    return 1;
}

/* entry k's phase: 1 = the text page (TXT, TITLE: the league phase over), 0 = a view - the copy at SCR + BUF (A0),
   the work area kept (us_done after the view) */
u32 us_prep(u32 k) {
    u32 s = US_PH[k], st = w16(UC + 0x53);
    const struct cup *c = us_cur();
    if (s != st && (s == 0 || !c)) { us_lpt(); return 1; }
    copy(SCR + WSAVE, UC, WORK);
    copy(SCR + DSAVE, DREG, 60);
    u8 *b = SCR + BUF;
    copy(b, UC, WORK);
    if (s != st) {
        p16(b + 0x53, s);
        if (!ko_build(b + 0x41F, c, s)) { us_text(); return 1; }   /* (a club gone from the cache: the page) */
    }
    p16(b + 0x41F + 0x53, 0);
    A0R = (u32)b;
    US_IN = 1;
    return 0;
}

void us_done(void) {
    copy(UC, SCR + WSAVE, WORK);
    copy(DREG, SCR + DSAVE, 60);
    US_IN = 0;
}
