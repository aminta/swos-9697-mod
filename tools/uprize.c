/* 4.1 RC3 (Miguel via Davide, 09/11): UEFA prize money for the career club in a league-phase world (World 2026-27):
   the cup's real distribution (UEFA's figures in euros x one scale K, uprize.py's UP_TAB), credited as the game's
   competitionBonuses (the statement row) + newBalance, and FFP's season income (finance's FF_INC). obj4, after usmenu
   (swreg.USMENU_AT's page; tools/uprize.py).

   The payments, the career club only (careerTeam's word), its UEFA cup (contest 0..2 = CL, EL, UECL):
   - participation: its first league-phase result of the season;
   - a league-phase win / draw: every result (up_res, lp36's lp_cb_res: A3 / A4 the rows, their played / won / drawn
     with this result, D1 / D2 the goals);
   - a knockout stage reached (play-offs, round of 16, quarter-finals, semi-finals, final): its first match in it
     (up_ko, uesum's us_hook after every match cseg_28E76 plays: UC+53h the stage, the ties' team words UD+24Dh);
   - the winner: the final's winner (UD+39h).
   What is paid is kept (UP, the save item 'UP'): a reload pays nothing twice; another season / cup starts at zero.
   An older save (no 'UP': ok 0) counts what its club has already reached as paid, at its first event (nothing back-
   paid); a new career (up_new) starts with ok 1.

   The season start's euro-cup term (cseg_5DEB9: slot 3 x its kind x a progress byte into competitionBonuses) would
   pay the same cup again next summer: up_eur (its `mov eax, [D8CB6]`) reads 0 in a league-phase world. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern u8 UC[], UD[];                   /* diyFileBufferCopy, DIY_competitionStart (lp36's DIY) */
extern u16 CTEAM;                       /* careerTeam's word (file, ordinal) */
extern u16 GAMETYPE;                    /* 4 = career */
extern int NEWBAL, CBON;                /* newBalance, competitionBonuses */
extern u32 FF_INC;                      /* finance / ffp: the season's income so far (FFP's I) */
extern u32 D8CB6;                       /* the season start's euro-cup slot */
extern u8 *A3R, *A4R;                   /* lp_cb_res: the home / away row (DIY + 18 x row) */
extern u16 D1R, D2R;                    /* their goals */
extern u8 SEASONP;                      /* seasonPlaying (uesum's stamp) */
extern const u32 UP_TAB[3][12];         /* uprize.py: participation, win, draw, play-offs, R16, QF, SF, final, winner,
                                           the ranking's share, places 1-8, places 9-16 */
extern u8 LP_ORD[];                     /* lp36: the league phase's rows, best first (final at lp_cb_gend) */
void W_LPW(void);                       /* careerworld w_lpw: ZF = 1 in a league-phase world */
enum { P_PART, P_WIN, P_DRAW, P_PO, P_R16, P_QF, P_SF, P_FIN, P_WON, P_SHARE, P_TOP8, P_TOP16 };
enum { F_PART = 1, F_WON = 2, F_RANK = 4 };
#define MAXBAL 100000000                /* the game's own cap (cseg_3C4CE's area) */

#define w16(p) (*(const u16 *)(p))

struct up { u8 ok, id, ss, fl, w, d, st, off; };        /* the save item 'UP' (8 B); off: ANDAMENTO CLUB's switch
                                                           (uprize2.c: 0 = ON - an older save, a new career) */
struct { u32 tag; struct up u; u32 sum; } UP = { 0x5A525055 };  /* 'UPRZ' (the harness finds it); sum: this run's
                                                                    payments (not saved, the harness's) */
_Static_assert(sizeof UP.u == 8, "UP: uprize.UP_SIZE");

u32 up_world(void) {                    /* a league-phase world's career (the switch's button shows) */
    u8 z;
    if (GAMETYPE != 4) return 0;
    __asm__ volatile("call W_LPW; sete %0" : "=q"(z) : : "memory", "cc");
    return z;
}
static u32 lpw(void) { return !UP.u.off && up_world(); }   /* (OFF: no prizes, the season start's own euro-cup term) */
static u32 stamp(void) { return SEASONP + 1u; }
static u32 cid;                         /* the cup (contest 0..2) of this event */

void up_credit(u32 a) {                 /* (rounded to thousands: the ranking's / value pillar's shares x K) */
    a = (a + 500) / 1000 * 1000;
    if (!a) return;
    UP.sum += a;
    CBON += (int)a;
    FF_INC += a;
    NEWBAL = NEWBAL > MAXBAL - (int)a ? MAXBAL : NEWBAL + (int)a;
}
static __attribute__((noinline)) void pay(u32 k, u32 n) { up_credit(UP_TAB[cid][k] * n); }
void (*UP_VFN)(u32 me) = 0;             /* uprize2.c up_value (the value pillar, with the participation), set by uprize.py */

/* UP for this cup and season; another one (or none yet) starts at zero - an older save's (ok 0) at what its club has
   reached now (part, w, d, st, won: counted as paid) */
static __attribute__((noinline)) struct up *cur(u32 part, u32 w, u32 d, u32 st, u32 won, u32 rank) {
    struct up *u = &UP.u;
    if (u->ok && u->id == cid && u->ss == stamp()) return u;
    if (u->ok) part = w = d = st = won = rank = 0;
    u->ok = 1;
    u->id = (u8)cid;
    u->ss = (u8)stamp();
    u->fl = (u8)((part ? F_PART : 0) | (won ? F_WON : 0) | (rank ? F_RANK : 0));
    u->w = (u8)w;
    u->d = (u8)d;
    u->st = (u8)st;
    return u;
}

static u32 row(const u8 *a) { u32 r = (u32)(a - UD) / 18; return r < 36 ? r : 99; }

void up_res(void) {                     /* a league-phase result, before the game adds it to the rows */
    if ((cid = UD[0x2D]) > 2 || !lpw()) return;
    u32 h = row(A3R), g = row(A4R), me, gf, ga;
    if (h < 36 && w16(UD + 0x12D + 2 * h) == CTEAM) me = h, gf = D1R, ga = D2R;
    else if (g < 36 && w16(UD + 0x12D + 2 * g) == CTEAM) me = g, gf = D2R, ga = D1R;
    else return;
    const u8 *r = UD + 0x2B3 + 18 * me;         /* +4 played, +6 won, +8 drawn: this result already in them
                                                   (cseg_8922B, cseg_88A12 before the goals) */
    u32 w = w16(r + 6), d = w16(r + 8);
    struct up *u = cur(w16(r + 4) > 1, w - (gf > ga), d - (gf == ga), 0, 0, 0);   /* (an older save: before it) */
    if (!(u->fl & F_PART)) { u->fl |= F_PART; pay(P_PART, 1); if (UP_VFN) UP_VFN(me); }
    if (w > u->w) { pay(P_WIN, w - u->w); u->w = (u8)w; }
    if (d > u->d) { pay(P_DRAW, d - u->d); u->d = (u8)d; }
}

void up_ko(void) {                      /* after a knockout match (us_hook): the stage reached, the winner */
    u32 s = w16(UC + 0x53), nt = w16(UD + 0x51), i, k;
    if (UD[0] != 1 || (cid = UD[0x2D]) > 2 || s - 1 > 4 || !lpw()) return;
    for (i = 0; i < 2 * nt && i < 64 && w16(UD + 0x24D + 2 * UD[0x2CD + i]) != CTEAM; i++) ;  /* (the ties' pairs:
                                           the team words also park the clubs of the next stage - lp36 lp_gend) */
    if (i == 2 * nt || i == 64) return;
    u32 n = w16(UC + 0x15D + 0x76 * s + 4);
    k = s == 1 ? P_PO : n == 16 ? P_R16 : n == 8 ? P_QF : n == 4 ? P_SF : n == 2 ? P_FIN : 99;
    if (k == 99) return;
    u32 won = k == P_FIN && w16(UD + 0x39) == CTEAM;
    struct up *u = cur(1, 0, 0, s, won, 1);
    if (s > u->st) { u->st = (u8)s; pay(k, 1); }
    if (won && !(u->fl & F_WON)) { u->fl |= F_WON; pay(P_WON, 1); }
}

u32 up_show(void) { return CBON && lpw(); }    /* the in-season statement: our row (the period's prizes) */

void up_lp(void) {                      /* the league phase's end (uesum's us_gend after us_lp): the ranking pillar -
                                           shares 36 (1st) .. 1 (36th), + places 1-8 / 9-16 */
    u32 k;
    if ((cid = UC[0x2D]) > 2 || !lpw()) return;
    for (k = 0; k < 36 && w16(UC + 0x99 + 2 * LP_ORD[k]) != CTEAM; k++) ;
    if (k == 36) return;
    struct up *u = cur(1, 0, 0, 0, 0, 0);
    if (u->fl & F_RANK) return;
    u->fl |= F_RANK;
    pay(P_SHARE, 36 - k);
    if (k < 16) pay(k < 8 ? P_TOP8 : P_TOP16, 1);
}

void up_new(void) { UP.u.ok = 1; }      /* a new career: nothing reached yet (an older save's item: 0) */

u32 up_eurc(void) { return lpw() ? 0 : D8CB6; }
__asm__(".globl up_eur\nup_eur:\n\tpushal\n\tcall up_eurc\n\tmovl %eax, 28(%esp)\n\tpopal\n\tret\n");
#if RES_CHAIN                           /* (lp_cb_res: uefacoef's uc_res after it, else its own ret) */
__asm__(".globl up_resg\nup_resg:\n\tpushal\n\tcall up_res\n\tpopal\n\tjmp RESOLD\n");
#else
__asm__(".globl up_resg\nup_resg:\n\tpushal\n\tcall up_res\n\tpopal\n\tret\n");
#endif
