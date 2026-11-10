/* 4.0.6 option C, P1 (Davide GO 03/11): a continental round as the game's own contest, for the game's competition
   screens (P3) - a knockout round a type-1 cup of its clubs, a group stage a type-2 contest - built by the game's
   own code (cseg_8B2D3's first half: the team list, the cup / tournament init, the copy into the buffer; not its
   second half, the career calendar) into a scratch buffer, never a career slot. obj3, its own page (tools/ctgame.py);
   the scratch is obj3's zero-fill tail (vsize only, never in the file or the save; DOS/4GW does not zero it: every
   build clears what it uses).

   cg_build(cup, round, tie, week): the contest of conti.c's round (CT_OUT, the replay's draw) in CG_SCR's buffer;
   tie >= 0: only that tie (D[2 tie] v D[2 tie + 1], conti.py's ct_prep layout: the career club's slot-3 tie), -1 the
   whole round. Returns the struct's length, 0 if it can't be built (CG_ERR: why). cg_replay(): conti.c's replay
   (ct_resume, the run a load does) keeping every match's goals in CG_SCR's record (conti.h struct ct_grec).
   cg_selftest() (CONTI_CGTEST test builds): after conti's ct_build put the career club's game in slot 3, the same
   contest built here must be byte-identical to it (CG_T: builds, mismatches, the first one's offset). */

#include "conti.h"

extern const u8 *CT_SPEC;
extern struct ct_in CT_IN;
extern struct ct_out CT_OUT;
extern struct ct_seg CT_SEG;
extern struct ct_grec *CT_GREC;
void ct_resume(void);

/* ctgame.py's table: u8 base[14] (the ties' contest header: its id, type 1, ...), u8 ncup, u8 pad, then per cup
   u32 name, u32 short name (sacups.STR_BASE-relative), u8 main round (FF none), u8 hlen, u8 n, u8 pad, u32 its
   struct (obj1, 0 none), u16 groups[NRD] (a non-main group stage's header from the table, 0 none) */
#ifdef NATIVE
u8 CG_TAB[4096];
u8 CG_SCR[0x4280];
u16 CG_NUMSEL_[1];
u8 CG_SLOT3[0xB52];
u8 CG_CAREER[0x17400], CG_WORK[0xB52], CG_DREG[60], CG_SELB[684 * 160];
u8 *CG_SELBASEV = CG_SELB;
u8 CG_GTAB[4];
u8 CG_FCNT[288];
#define CG_FIXED 95153
static void cg_nat0(const u8 *st, u8 *buf) { (void)st; (void)buf; }
void (*CG_NAT)(const u8 *, u8 *) = cg_nat0;
#define CG_NUMSEL (CG_NUMSEL_[0])
#else
extern const u8 CG_TAB[];
extern u8 CG_SCR[];
extern u16 CG_NUMSEL;                   /* g_numSelectedTeams */
void (*CG_NAT)(const u8 *, u8 *) = 0;   /* ctgame.py's glue cg_native: cseg_8B2D3's first half, slot index 3,
                                           into buf (patched in: the glue comes after the C) */
#endif
#ifndef NATIVE
extern u8 CG_SLOT3[];                   /* (cg_selftest: conti's slot 3) */
extern const u8 CG_FCNT[];              /* P4: each team file's last club ordinal, then a bitmap of the files the
                                           world loads (ctgame.py fcnt) - a word past its file's clubs would never be found (GetTeamPointer's search of the
                                           file has no end: the game hangs) */
#endif

#define SEL_CAP 160                     /* (careerworld SEL_N: a World 2026-27 career's team cache) */
#define CG_BUF 0x0000                   /* the contest (B52h: a type-2's) */
#define CG_ST 0x0B60                    /* its struct (<= 0x100) */
#define CG_SAVE 0x0C60                  /* the game's work area while the glue runs (B52h) */
#define CG_CLR 0x17C0                   /* (a build's cleared part: buffer, struct, save area) */
#define CG_WSAVE 0x2000                 /* P2's guard: the game's work area while a view is open (B52h) */
#define CG_DSAVE 0x2B60                 /* D0..A6 (60) */
#define CG_KEEP 0x2BA0                  /* the guard table's kept bytes (ST_RANK...) */
#define CG_END 0x3000
                                        /* (0x3000..0x3280: ctview's rounds menu buffers) */
#define CG_REC 0x3280                   /* the goals (struct ct_grec; P4: 4 KB, the scratch's end - a season used 1437 B
                                           of the 2 KB it had at 17C0h) */
#define CG_RECEND 0x4280

enum { E_OK, E_NOSPEC, E_ROUND, E_TIE, E_CACHE, E_KIND, E_NONE, E_GUARD, E_OPEN };
enum { E_GUEST = 10, E_NOREC = 11 };   /* (P4: a club no team file of the world has; a round played, its goals not
                                           kept - the replay's record full)  E_OWN 9 below */
u32 CG_ERR = 0;
u32 CG_T[8] = {0};                      /* cg_selftest: builds, mismatches, first diff, its cup | round << 8 | tie << 16,
                                           the length compared, the cache count before / after, the last error */

static u32 w16(const u8 *p) { return p[0] | p[1] << 8; }
static u32 w32(const u8 *p) { return p[0] | p[1] << 8 | p[2] << 16 | (u32)p[3] << 24; }
static void p16(u8 *p, u32 v) { p[0] = (u8)v; p[1] = (u8)(v >> 8); }
static void p32(u8 *p, u32 v) { p[0] = (u8)v; p[1] = (u8)(v >> 8); p[2] = (u8)(v >> 16); p[3] = (u8)(v >> 24); }
static void zero(u8 *p, u32 n) { while (n--) *p++ = 0; }
static void copy(u8 *d, const u8 *s, u32 n) { while (n--) *d++ = *s++; }

/* --- the spec's rounds (conti.c parse(), as ctview.c) ---------------------------------------------------------------- */
static const u8 *rnd0[NCUP];
static u8 nr[NCUP], ncup;
static void spec(void) {
    const u8 *p = CT_SPEC;
    ncup = p[0];
    p += 4;
    for (int c = 0; c < ncup && c < NCUP; c++) { nr[c] = p[0]; rnd0[c] = p + 4; p += 4 + nr[c] * RB; }
}
#define RD(c, r) (rnd0[c] + (r) * RB)

static const u8 *cupent(int c) { return CG_TAB + 16 + 32 * c; }   /* (32 bytes a cup) */
static u8 g_view = 0;                   /* (P3: a view's build - the round's own month, its days over the month) */
static int g_nw = 0;                      /* (mkstruct: its club words, the struct's last 2 g_nw bytes) */
static u32 id(int x) { return x ? CT_IN.club[x - 1].id : 0xFFFF; }

/* the struct of round (c, r) - tie t, or the round - at st; returns its length */
static u32 mkstruct(int c, int r, int t, u32 week, u8 *st) {
    const u8 *R = RD(c, r), *ce = cupent(c);
    const u16 *e = CT_OUT.ent[c][r];
    int n = CT_OUT.nent[c][r];
    if (r == ce[8] && w32(ce + 12) && t < 0) {        /* the main round: the cup's own contest (conti.structs) */
        const u8 *s = (const u8 *)w32(ce + 12);
        int h = ce[9], m = ce[10];
        copy(st, s, h);
        for (int i = 0; i < m; i++) p16(st + h + 2 * i, i < n && i < NE ? id(e[i]) : 0xFFFF);
        g_nw = m;
        return h + 2 * m;
    }
    if (R[0] == K_KO) {                                /* a type-1 cup: the ties' contest header, its clubs */
        int k = t >= 0 ? 2 : n, nr1 = 0, h;
        if (t >= 0 && 2 * t + 1 >= n) { CG_ERR = E_TIE; return 0; }
        if (k < 2 || k > 64) { CG_ERR = E_ROUND; return 0; }
        for (int x = k >> 1; x; x >>= 1) nr1++;        /* (cseg_87DA0's round count: [31h] / 2 halved to 0) */
        copy(st, CG_TAB, 14);
        st[10] = (u8)k;
        u32 mo = (u32)((R[9] - 1 + (R[9] < 8 ? 12 : 0)) * 8);   /* (ct_prep: never a week already reached) */
        if (mo <= week && !g_view) mo = week + 1;
        st[3] = (u8)mo;
        st[4] = (u8)(mo + (g_view ? 7 : 2));
        u8 legs = R[1] == 2 ? (R[2] == 1 || R[2] == 3 ? 0x94 : 0x84) : 0x14;
        for (int i = 0; i < nr1; i++) st[14 + i] = i ? 0x14 : legs;
        h = 14 + nr1;
        st[h++] = 0;
        st[5] = (u8)(h - 5);
        st[7] = (u8)(h + 8 - 7);
        p32(st + h, w32(ce)); p32(st + h + 4, w32(ce + 4));
        h += 8;
        for (int i = 0; i < k; i++) p16(st + h + 2 * i, id(e[(t >= 0 ? 2 * t : 0) + i]));
        g_nw = k;
        return h + 2 * k;
    }
    u32 g = w16(ce + 16 + 2 * r);                      /* a group stage not the main round: its own header */
    if (!g) { CG_ERR = E_KIND; return 0; }
    const u8 *b = CG_TAB + g;
    int h = b[0], m = b[1];
    copy(st, b + 2, h);
    for (int i = 0; i < m; i++) p16(st + h + 2 * i, i < n && i < NE ? id(e[i]) : 0xFFFF);
    g_nw = m;
    return h + 2 * m;
}

u32 cg_build(u32 c, u32 r, s32 t, u32 week) {
    u8 *buf = CG_SCR + CG_BUF, *st = CG_SCR + CG_ST;
    CG_ERR = E_OK;
    if (!CT_SPEC) { CG_ERR = E_NOSPEC; return 0; }
    spec();
    if (c >= ncup || r >= nr[c]) { CG_ERR = E_ROUND; return 0; }
    zero(CG_SCR, CG_CLR);                              /* (buffer, struct, the save area: never trusted) */
    u32 n = mkstruct((int)c, (int)r, t, week, st);
    if (!n) return 0;
    u32 k = st[1] == 1 ? st[10] : st[15];              /* (its clubs: type 1 [0Ah], type 2 [0Fh]) */
    if (CG_NUMSEL + k > SEL_CAP) { CG_ERR = E_CACHE; return 0; }   /* (each club at most once more) */
    for (int i = 0; i < g_nw; i++) {                   /* (P4: every club in a team file of the world) */
        u32 w = w16(st + n - 2 * (u32)g_nw + 2 * (u32)i);
        if (w != 0xFFFF && (!(CG_FCNT[256 + ((w & 0xFF) >> 3)] >> (w & 7) & 1) || (w >> 8) > CG_FCNT[w & 0xFF])) {
            CG_ERR = E_GUEST;
            return 0;
        }
    }
    CG_NAT(st, buf);
    p16(buf + 0x39, 0xFFFF);                           /* (ct_build: no winner yet) */
    return n;
}

u32 CG_ROOM = CG_RECEND - CG_REC - sizeof(struct ct_grec);   /* (the record's room: Tier B lowers it - E_NOREC) */
void cg_replay(void) {
    struct ct_grec *g = (struct ct_grec *)(CG_SCR + CG_REC);
    zero((u8 *)g, sizeof *g);
    g->room = (u16)CG_ROOM;
    CT_GREC = g;
    ct_resume();
    CT_GREC = 0;
}

/* --- P3: the round's results in the built contest (Davide GO 03/11) ------------------------------------------------
   A knockout round (a type-1 cup, its round 0): every tie as the game's cup screen keeps it (cseg_28E76 / cseg_284D8:
   +89h a flag a tie, +C9h its score, +14Dh the first leg / 90 minutes, +1CDh the penalties - a word hi = the first
   club of the pair +2CDh; the second leg: the pair swapped, the first leg's score with it, flag 20h; 80h played, 2
   decided, 1 the second club through, 4 a.e.t., 8 penalties, 10h away goals) - a leg once its day (+337h) is before
   the week. A group stage (type 2): each match day before the week through the game's own routines (ctgame.py's
   glue cg_gplay: cseg_89758's pairing, cseg_88A12's sums, cseg_8922B's counters, cseg_883DD's sort) with the
   replay's goals (cg_ggoal). The career club's own games: the calendar's played slot-3 entries (22 bytes: +1 week,
   +0Bh flags, +0Ch / +0Eh the clubs, +10h score, +12h first leg / 90 minutes, +14h penalties); its group stage's
   other matches are not kept anywhere once slot 3 moved on: E_OWN (the text page). conti.c decides a shoot-out's
   winner only: its score is made up here, the same at every view (pens). */
#ifndef NATIVE
extern const u8 CG_CAL[];               /* the career calendar (dseg_DB3E6) */
extern u8 CG_RNTIE[];                   /* rnames' RN_TIE (conti's ct_rntie without rnames) */
extern const u8 CG_CTRN[];              /* conti's ct_rn: each cup's rounds' name index, 16 a cup */
#else
u8 CG_CAL[22], CG_RNTIE[1], CG_CTRN[256];
#endif
enum { E_OWN = 9 };
u32 cg_open(u32 c, u32 r, s32 t, u32 week);
void cg_close(void);
extern u32 CG_G[12];
static const struct ct_grec *grec(void) { return (const struct ct_grec *)(CG_SCR + CG_REC); }
static const u8 *recof(int c, int r) { u32 o = grec()->off[c][r]; return o ? grec()->b + o - 1 : 0; }
static int gx(u32 b) { return (int)(b & 15) - 1; }
static int gy(u32 b) { return (int)(b >> 4) - 1; }

static u32 pens(u32 c, u32 r, u32 i) {  /* a shoot-out's score, the winner's first (made up: see above) */
    static const u8 P[12][2] = { {4,3}, {5,4}, {4,2}, {3,2}, {5,3}, {4,3}, {3,1}, {6,5}, {5,4}, {4,2}, {7,6}, {3,0} };
    u32 h = ((c * 131u + r * 31u + i * 7u + 5u) * 2654435761u) >> 20;
    return (u32)P[h % 12][0] << 8 | P[h % 12][1];
}

/* the career club's game v (a, b): the last played slot-3 calendar entry of these two before week (leg2: flag 20h) */
static const u8 *calent(u16 a, u16 b, int leg2, u32 week) {
    const u8 *p = CG_CAL, *hit = 0;
    for (int k = 0; k < 600; k++) {
        u32 n = w16(p + 2);
        if (p[0] == 3 && p[5] && (p[11] & 0x80) && p[1] < week && !(p[11] & 0x20) == !leg2 &&
            ((w16(p + 12) == a && w16(p + 14) == b) || (w16(p + 12) == b && w16(p + 14) == a)))
            hit = p;
        if (!n || n > 0x100) break;
        p += n;
    }
    return hit;
}

struct tie_r { int st, l1a, l1b, l2a, l2b, na, nb, f, win_a; u32 pn; };   /* (a = D[2i], b = D[2i + 1]) */

static void tie_conti(const u8 *R, const u8 *g, int win_a, u32 pn, struct tie_r *t) {
    int legs = R[1] == 2, lv = R[2];
    t->l1a = gx(g[0]); t->l1b = gy(g[0]);
    t->l2a = t->l2b = 0;
    if (legs) { t->l2b = gx(g[1]); t->l2a = gy(g[1]); }
    int ga = t->l1a + t->l2a, gb = t->l1b + t->l2b;
    t->na = ga; t->nb = gb;
    t->f = 0;
    if (ga == gb) {
        if ((lv == 2 || lv == 3) && legs && t->l2a != t->l1b) t->f = 0x10;
        else {
            if (g[2]) {                 /* extra time: in the second leg (two legs), else in the match */
                t->f = 4;
                if (legs) { t->l2a += gx(g[2]); t->l2b += gy(g[2]); }
                else { t->l1a += gx(g[2]); t->l1b += gy(g[2]); }
                if (gx(g[2]) == gy(g[2])) t->f |= 8;
            } else t->f = 8;
        }
    }
    t->win_a = win_a;
    t->pn = win_a ? pn : (pn & 0xFF) << 8 | pn >> 8;    /* (a's first) */
}

/* the career club's tie from the calendar: 0 no entry */
static int tie_own(const u8 *R, u16 ia, u16 ib, u32 week, int win_a, struct tie_r *t) {
    int legs = R[1] == 2;
    const u8 *e = legs ? calent(ia, ib, 1, week) : 0, *e1 = calent(ia, ib, 0, week);
    if (!e && !e1) return 0;
    if (!e) e = e1;
    int sw = w16(e + 12) != ia;         /* (the entry's first club is b) */
    u32 s = w16(e + 16), v = w16(e + 18), q = w16(e + 20);
#define HL(x, a_, b_) do { if (sw) { b_ = (int)((x) >> 8); a_ = (int)((x) & 0xFF); } else { a_ = (int)((x) >> 8); b_ = (int)((x) & 0xFF); } } while (0)
    t->f = e[11] & 0x1C;
    t->win_a = win_a;
    t->pn = sw ? (q & 0xFF) << 8 | q >> 8 : q;
    if (legs && (e[11] & 0x20)) {
        HL(s, t->l2a, t->l2b);
        HL(v, t->l1a, t->l1b);
        t->st = 2;
    } else {
        HL(s, t->l1a, t->l1b);
        t->l2a = t->l2b = 0;
        if (!legs && (e[11] & 4)) HL(v, t->na, t->nb); else { t->na = t->l1a; t->nb = t->l1b; }
        t->st = legs ? 1 : 2;
    }
#undef HL
    return 1;
}

static int ko_fill(int c, int r, int t0, u32 week) {
    u8 *b = CG_SCR + CG_BUF;
    const u8 *R = RD(c, r), *g = recof(c, r);
    const u16 *e = CT_OUT.ent[c][r];
    int legs = R[1] == 2, nt = w16(b + 0x51);
    u32 d1 = b[0x337], d2 = legs ? b[0x338] : d1;
    int rs = week > d1 ? (legs && week <= d2 ? 1 : 2) : 0;   /* (the round's legs played by the week) */
    if (rs && !g) { CG_ERR = E_NOREC; return 0; }       /* (P4: played, no goals kept) */
    int all2 = 1, any1 = 0;
    for (int i = 0; i < nt; i++) {
        int k = (t0 >= 0 ? t0 : i);     /* (the tie in the round's draw) */
        if (2 * k + 1 >= CT_OUT.nent[c][r]) break;
        struct tie_r t;
        t.st = 0;
        int win_a = CT_OUT.res[c][r][2 * k] ? 1 : 0;
        const u8 *gk = g ? g + 3 * k : 0;
        if (gk && gk[0] == GR_OWN) {
            if (!tie_own(R, (u16)id(e[2 * k]), (u16)id(e[2 * k + 1]), week, win_a, &t)) {
                if (rs) { CG_ERR = E_OWN; return 0; }
            }
        } else if (gk && gk[0] && rs) {
            tie_conti(R, gk, win_a, pens((u32)c, (u32)r, (u32)k), &t);
            t.st = rs;
        } else if (CT_SEG.kind != 0xFF && CT_SEG.cup == c && CT_SEG.round == r &&
                   (id(e[2 * k]) == CT_SEG.club[0] || id(e[2 * k]) == CT_SEG.club[1])) {
            tie_own(R, (u16)id(e[2 * k]), (u16)id(e[2 * k + 1]), week, win_a, &t);   /* (its game in progress) */
            if (t.st == 2 && legs) t.st = 1;    /* (not through yet: its second leg is to come) */
        }
        if (t.st != 2) all2 = 0;
        if (t.st) any1 = 1;
        u8 *pr = b + 0x2CD + 2 * i;
        if (legs && t.st) {             /* the second leg's view: b first */
            u8 x = pr[0]; pr[0] = pr[1]; pr[1] = x;
            p16(b + 0x14D + 2 * i, (u32)t.l1b << 8 | (u32)t.l1a);
            b[0x89 + i] = 0x20;
            if (t.st == 2) {
                b[0x89 + i] |= (u8)(0x82 | t.f | (t.win_a ? 1 : 0));
                p16(b + 0xC9 + 2 * i, (u32)t.l2b << 8 | (u32)t.l2a);
                p16(b + 0x1CD + 2 * i, (t.pn & 0xFF) << 8 | t.pn >> 8);
            }
        } else if (t.st == 2) {
            b[0x89 + i] = (u8)(0x82 | t.f | (t.win_a ? 0 : 1));
            p16(b + 0xC9 + 2 * i, (u32)t.l1a << 8 | (u32)t.l1b);
            p16(b + 0x14D + 2 * i, (u32)t.na << 8 | (u32)t.nb);
            p16(b + 0x1CD + 2 * i, t.pn);
        }
    }
    p16(b + 0x63, 0);
    if (legs && any1) { p16(b + 0x149, 1); p16(b + 0x335, 1); }
    p16(b + 0x53, any1 && all2 ? 1 : 0);
    return 1;
}

/* a group stage: the glue's callback - the goals of home row h v away row a (rows in the contest's order: group
   h / gs), the replay's byte (home | away << 4, + 1 each), 0 none */
static const u8 *g_rec;
static int g_gs, g_grd, g_gm;
static u8 g_seen[64];                   /* (a single round robin: each match once - the game's contest plays it twice) */
u32 cg_ggoal(u32 h, u32 a) {
    if (!g_rec || !g_gs || h / (u32)g_gs != a / (u32)g_gs || h == a) return 0;
    int g = (int)h / g_gs, i = (int)h % g_gs, j = (int)a % g_gs, lo = i < j ? i : j, hi = i ^ j ^ lo;
    int m = lo * (2 * g_gs - lo - 1) / 2 + (hi - lo - 1), sw = 0;
    if (i > j) { if (g_grd == 2) m += g_gs * (g_gs - 1) / 2; else sw = 1; }
    if (m >= g_gm) return 0;
    if (g_grd == 1) {
        int q = g * g_gm + m;
        if (q >= 512 || g_seen[q >> 3] & 1 << (q & 7)) return 0;
        g_seen[q >> 3] |= (u8)(1 << (q & 7));
    }
    u32 b = g_rec[g * g_gm + m];
    if (b == GR_OWN) return 0;
    return sw && b ? (b >> 4 | (b & 15) << 4) : b;
}
#ifndef NATIVE
void (*CG_GPLAY)(u8 *, u32) = 0;        /* ctgame.py's glue cg_gplay (patched in) */
#else
static void cg_gp0(u8 *b, u32 w) { (void)b; (void)w; }
void (*CG_GPLAY)(u8 *, u32) = cg_gp0;
#endif

static int gr_fill(int c, int r, u32 week) {
    const u8 *R = RD(c, r);
    g_rec = recof(c, r);
    if (!g_rec) {                       /* not played yet: the draw - played (its first match day before the week),
                                           no goals kept: E_NOREC (P4) */
        const u8 *D = CG_SCR + CG_BUF + 0x41F;
        if (D[0x1CD + w16(D + 0x1C1)] < week) { CG_ERR = E_NOREC; return 0; }
        return 1;
    }
    g_gs = R[7]; g_grd = R[8] ? R[8] : 2;
    g_gm = g_gs * (g_gs - 1) / 2 * g_grd;
    for (int i = 0; i < R[6] * g_gm; i++) if (g_rec[i] == GR_OWN) { CG_ERR = E_OWN; return 0; }
    for (int i = 0; i < 64; i++) g_seen[i] = 0;
    CG_GPLAY(CG_SCR + CG_BUF, week);
    g_rec = 0;
    /* (a group short of a club: its empty slot - the draw's 0xFFFF, a team pointer the game made of it, not in the
       cache - last in its table, not above a real club on goal difference) */
    u8 *o = CG_SCR + CG_BUF + 0x41F + 0x6D, *rows = CG_SCR + CG_BUF + 0x41F + 0x2B3;
    for (int g = 0; g < R[6]; g++) {
        u8 *w = o + 2 * g * g_gs;
        for (int k = 0, e = g_gs - 1; k < e; ) {
            if (w32(rows + w16(w + 2 * k)) >> 24) {
                u32 x = w16(w + 2 * k);
                for (int j = k; j < g_gs - 1; j++) p16(w + 2 * j, w16(w + 2 * j + 2));
                p16(w + 2 * (g_gs - 1), x);
                e--;
            } else k++;
        }
    }
    return 1;
}

/* cg_view(cup, round, tie, week): a view of round (c, r) as it stands at the week - opened (cg_open: close it with
   cg_close), built on the round's own dates, its results in; its length, 0 none (CG_ERR) */
u32 cg_view(u32 c, u32 r, s32 t, u32 week) {
    cg_replay();
    g_view = 1;
    u32 n = cg_open(c, r, t, week);
    g_view = 0;
    if (!n) return 0;
    if (CG_SCR[CG_BUF + 0x2D] == CG_TAB[0]) CG_RNTIE[0] = CG_CTRN[c << 4 | r];   /* (the ties' contest: its round's
                                           name - rnames' RN_TIE, ct_prep's from CT_SEG; kept: put back at the close) */
    int ok = CG_SCR[CG_BUF] == 1 ? ko_fill((int)c, (int)r, t, week) : gr_fill((int)c, (int)r, week);
    if (!ok) { CG_G[7] = CG_ERR; cg_close(); return 0; }
    return n;
}

/* --- P2: the save guards (Davide GO 03/11)------------------------------------------------------------------------
   A view borrows the game's state the .CAR is made of: cg_open snapshots it, builds, cg_close puts it back.
   Put back: the team cache's count (a build adds its clubs past it: never saved), the game's work area and D0..A6
   (the view's cseg_8B71C), both random generators, and the guard table's kept ranges (CG_GTAB: what a build was seen
   to write in the saved state - careerFileBuffer + 16ABCh, statespec's ST_RANK, lib97's NC_WDON..NC_RD). Checked:
   a sum of everything the save writes (the fixed part, the cache's N records, every trailer / 'EN' item: CG_GTAB's
   summed ranges) the same at the close as at the open - else CG_G[5] (bad) and no view again this run (fallback A).
   Never a save or a day while one is open: save_trailer and ct_daily call cg_guard first (closes it: CG_G[4]). */
#ifndef NATIVE
extern u8 CG_CAREER[];                  /* careerFileBuffer: the .CAR's fixed part (CG_FIXED bytes, the count last) */
extern u8 *CG_SELBASEV;                 /* trailer's SELBASEV: the career's team cache (a big world's) */
extern u8 CG_WORK[];                    /* diyFileBufferCopy + DIY_competitionStart (B52h) */
extern u8 CG_DREG[];                    /* D0..D7, A0..A6 */
extern const u8 CG_GTAB[];              /* ctgame.py: u16 nkeep, nsum; then (u32 address, u32 length) x nkeep + nsum */
#endif
u32 CG_G[12] = {0};                     /* open, its count, its sum, opens, trips (closed by a save / day), bad sums,
                                           sticky (no view: fallback A), the last error, vtest builds, vtest fails */
#define CG_OPEN 0x4E45504Fu             /* ('OPEN': CG_G[0] - in the file page, zero at the start) */

static u32 gsum(void) {                 /* FNV-1a over the saved state */
    u32 h = 0x811C9DC5u;
    const u8 *p = CG_CAREER;
    for (u32 i = 0; i < CG_FIXED; i++) h = (h ^ p[i]) * 0x01000193u;
    p = CG_SELBASEV;
    for (u32 i = 0, n = (u32)CG_NUMSEL * 684; i < n; i++) h = (h ^ p[i]) * 0x01000193u;
    u32 nk = w16(CG_GTAB), ns = w16(CG_GTAB + 2);
    for (u32 k = nk; k < nk + ns; k++) {
        const u8 *q = (const u8 *)w32(CG_GTAB + 4 + 8 * k);
        for (u32 i = 0, n = w32(CG_GTAB + 8 + 8 * k); i < n; i++) h = (h ^ q[i]) * 0x01000193u;
    }
    return h;
}

static void keep(int out) {             /* the kept ranges <-> CG_KEEP */
    u8 *d = CG_SCR + CG_KEEP;
    for (u32 k = 0, nk = w16(CG_GTAB); k < nk; k++) {
        u8 *q = (u8 *)w32(CG_GTAB + 4 + 8 * k);
        u32 n = w32(CG_GTAB + 8 + 8 * k);
        if (out) copy(d, q, n); else copy(q, d, n);
        d += n;
    }
}

static void close_(int regs) {
    CG_NUMSEL = (u16)CG_G[1];
    copy(CG_WORK, CG_SCR + CG_WSAVE, 0xB52);
    if (regs) copy(CG_DREG, CG_SCR + CG_DSAVE, 60);
    keep(0);
    CG_G[0] = 0;
    if (gsum() != CG_G[2]) { CG_G[5]++; CG_G[6] = 1; }
}

/* cg_open(cup, round, tie, week): the state kept, round (c, r) built (cg_build); its length, 0 none (CG_ERR) */
u32 cg_open(u32 c, u32 r, s32 t, u32 week) {
    if (CG_G[0] == CG_OPEN) { close_(0); CG_G[4]++; }
    if (CG_G[6]) { CG_ERR = E_GUARD; CG_G[7] = E_GUARD; return 0; }
    CG_G[1] = CG_NUMSEL;
    copy(CG_SCR + CG_WSAVE, CG_WORK, 0xB52);
    copy(CG_SCR + CG_DSAVE, CG_DREG, 60);
    keep(1);
    CG_G[2] = gsum();
    CG_G[0] = CG_OPEN;
    CG_G[3]++;
    u32 n = cg_build(c, r, t, week);
    if (!n) { CG_G[7] = CG_ERR; close_(1); }
    return n;
}

void cg_close(void) { if (CG_G[0] == CG_OPEN) close_(1); }

void cg_guard(void) { if (CG_G[0] == CG_OPEN) { close_(0); CG_G[4]++; } }   /* (a save / a day: the caller's D0..A6) */

#ifdef CGVIEW
void (*CG_VSIM)(u8 *) = 0;              /* ctgame.py's glue cg_vsim: the view's cseg_8B71C / cseg_8B7EA on buf */
static u32 vk = 0;
static void vtest(u32 week) {           /* (CONTI_CGVIEW test builds) one drawn round opened, viewed, closed a day */
    if (!CT_SPEC) return;
    spec();
    u32 m = 0;
    for (int c = 0; c < ncup; c++)
        for (int r = 0; r < nr[c]; r++) m += CT_OUT.nent[c][r] ? 1 : 0;
    if (!m) return;
    u32 j = vk++ % m;
    for (int c = 0; c < ncup; c++)
        for (int r = 0; r < nr[c]; r++)
            if (CT_OUT.nent[c][r] && !j--) {
                s32 t = (vk & 1) && RD(c, r)[0] == K_KO ? 0 : -1;
                if (cg_open((u32)c, (u32)r, t, week)) { CG_G[8]++; CG_VSIM(CG_SCR + CG_BUF); }
                else if (CG_ERR != E_KIND) CG_G[9]++;
                cg_close();
                return;
            }
}
#endif

void cg_daily(u32 week) {               /* conti's ct_daily, first: a view still open closed, then (CONTI_CGVIEW test
                                           builds) a view opened and closed */
    cg_guard();
#ifdef CGVIEW
    vtest(week);
#else
    (void)week;
#endif
}

#ifdef CGTEST
u32 cg_selftest(u32 week) {             /* (test builds) the career club's slot-3 game rebuilt here: byte-identical */
    int c = CT_SEG.cup, r = CT_SEG.round, t = -1;
#ifdef CG_FILL
    static u8 filled = 0;               /* (CG_FILL_TEST: the scratch as DOS/4GW may leave it - garbage - first) */
    if (!filled) { for (u32 i = 0; i < CG_RECEND; i++) CG_SCR[i] = CG_FILL; filled = 1; }
#endif
    if (CT_SEG.kind == 0xFF) return 0;
    if (!(CT_SEG.kind & 0x80)) {                       /* a tie: its index in the round's draw */
        const u16 *e = CT_OUT.ent[c][r];
        for (int i = 0; i + 1 < CT_OUT.nent[c][r]; i += 2)
            if (id(e[i]) == CT_SEG.club[0] && id(e[i + 1]) == CT_SEG.club[1]) t = i / 2;
        if (t < 0) { CG_T[7] = 0x100 | E_TIE; return 0; }
    }
    CG_T[5] = CG_NUMSEL;
    u32 n = cg_build((u32)c, (u32)r, t, week);
    CG_T[6] = CG_NUMSEL;
    CG_T[3] = (u32)c | (u32)r << 8 | (u32)(t & 0xFF) << 16;
    CG_T[0]++;
    if (!n) { CG_T[1]++; CG_T[7] = CG_ERR; return 0; }
    const u8 *a = CG_SCR + CG_BUF;
    u32 len = w16(a) == 2 ? 0xB52 : w16(a) == 1 ? 0x443 : 0x733;
    CG_T[4] = len;
    for (u32 i = 0; i < len; i++)
        if (a[i] != CG_SLOT3[i]) {
            if (!CG_T[2] && CG_T[1] == 0) CG_T[2] = i | 0x80000000u;
            CG_T[1]++;
            break;
        }
    return 1;
}
#endif
