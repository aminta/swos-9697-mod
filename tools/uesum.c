/* 4.1 S2a (Davide 08/11): STAT > RIEPILOGO of a world's UEFA cup (a league-phase world career: contest 0..2, the
   uefacoef uc_ok rule) - its state as the game keeps it in the viewed contest, nothing of its own. obj4 (tools/
   uesum.py), after swe.c; ctview's glue (cv_stinit, cv_sum) asks us_ok() and calls us_text().

   The viewed contest: diyFileBufferCopy (UC: +53h the current stage, stages from +15Dh, 76h each, +4 its clubs) and
   DIY_competitionStart (UD), the current stage in the game's own layout:
   - type 0, the league phase (lp36): +4Fh groups, +51h clubs each, +6Dh the order (row offsets), the rows +2B3h
     (18 B: +4 played .. +10h points), their team words +12Dh - lp36 sorts the 36 as one table over its 2 groups;
   - type 1, a knockout round (cseg_28E76): +51h ties, +14Bh 2 two legs, +149h the second leg's turn (the pairs
     swapped, the first leg's score at +14Dh with them), per tie +2CDh the pair (indices into the team words
     +24Dh), +89h flags (80h played, 2 decided, 1 the second club through, 4 a.e.t., 8 penalties), +C9h this leg's
     score, +1CDh the penalties - a word, hi = the pair's first club; +39h the winner (FFFFh none).
   4.1 S2b (Davide 08/11, option A): the earlier knockout stages (play-offs .. semi-finals) as us_rec recorded them -
   after every match cseg_28E76 plays, its common exit (us_hook) - in US_REC, MC's save item (uesum.REC_SIZE).
   Holders: the last season end's HOLD_CC / HOLD_CWC / HOLD_UEFA as supercup.py's usc_snap keeps them (saved). Names: the team cache
   (selTeamsPtr, its records' word at +0, teamName +5); a club not there has no line. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern u8 UC[], UD[];                   /* diyFileBufferCopy, DIY_competitionStart */
extern u8 *SELPTR;                      /* selTeamsPtr */
extern u16 NUMSEL;                      /* g_numSelectedTeams */
extern u16 HOLD[3];                     /* CC, CWC, UEFA holder words (usc_snap's SC_ST entry +6) */
extern char TXT[], TITLE[];             /* fmtpage's page text and title */
void W_LPW(void);                       /* careerworld w_lpw: ZF = 1 in a league-phase world */
extern u8 SEASONP;                      /* seasonPlaying: the season's year, 2 digits (InitializeNewSeason +1) */
static u32 stamp(void) { return SEASONP + 1u; }

/* uesum.py's table: u16 offsets [11] (holder, to be played, winner, pens, a.e.t., league phase, play-offs, round of
   16, quarter-finals, semi-final, final), u8 widths [64] (' '..'_'), the strings NUL-ended */
extern const u8 US_TAB[];
enum { T_HOLD, T_TBP, T_WIN, T_PEN, T_AET, T_LP };

#define PXMAX 298
#define LINES 14

#define w16(p) (*(const u16 *)(p))     /* (x86: unaligned word loads) */
static const char *txt(int k) { return (const char *)US_TAB + w16(US_TAB + 2 * k); }
static int cwid(u8 ch) { return ch >= 0x20 && ch < 0x60 ? US_TAB[22 + ch - 0x20] : 6; }

u32 us_ok(void) {
    u8 z;
    if (UD[0x2D] > 2) return 0;
    __asm__ volatile("call W_LPW; sete %0" : "=q"(z) : : "memory", "cc");
    return z;
}

static __attribute__((noinline)) const char *name(u32 w) {
    const u8 *p = SELPTR;
    for (u32 i = 0; i < NUMSEL; i++, p += 684) if (w16(p) == w) return (const char *)p + 5;
    return 0;
}

/* --- lines: LF, FF every LINES (ctview.c's); a line's width by the font (PXMAX), the page text far below TXTMAX --- */
static char *o;
static int nl = 0, px = 0;
static __attribute__((noinline)) void brk(void) {      /* a new line (none before the first) */
    if (o != TXT) *o++ = ++nl % LINES ? '\n' : '\f';
    px = 0;
}
static __attribute__((noinline)) void add(const char *s) { while (*s) { px += cwid((u8)*s); *o++ = *s++; } }
static __attribute__((noinline)) void word(const char *s) {     /* s whole on this line, else on the next (indent 4) */
    int w = 0;
    for (const char *q = s; *q; q++) w += cwid((u8)*q);
    if (px && px + w > PXMAX) { brk(); add("    "); }
    add(s);
}
static __attribute__((noinline)) char *dig(char *b, u32 v) { if (v >= 10) *b++ = (char)('0' + v / 10 % 10); *b++ = (char)('0' + v % 10); return b; }
static __attribute__((noinline)) void head(const char *a, const char *b) {
    brk();
    add(a); add(":");
    if (b) { add(" "); add(b); }
}
static __attribute__((noinline)) void score(u32 a, u32 b, int par) {      /* ' a-b' or ' (a-b)' */
    char t[10], *q = t;
    *q++ = ' ';
    if (par) *q++ = '(';
    q = dig(q, a); *q++ = '-'; q = dig(q, b);
    if (par) *q++ = ')';
    *q = 0;
    word(t);
}

static __attribute__((noinline)) const char *stname(u32 s) {             /* stage s's name: 0 the league phase, 1 the play-offs, then by clubs */
    u32 n = w16(UC + 0x15D + 0x76 * s + 4);
    return txt(s < 2 ? T_LP + (int)s : n == 16 ? T_LP + 2 : n == 8 ? T_LP + 3 : n == 4 ? T_LP + 4 : T_LP + 5);
}

/* --- a tie, normalised (4.1 S2b): the current stage's (ko) and the earlier stages' (US_REC, saved) the same way --- */
struct tie {                            /* x = the first leg's home club, y its guest (team words) */
    u16 x, y;
    u8 l1, l2, pn, fl;                  /* goals x << 4 | y (15 at most): leg 1, leg 2, penalties; FL_* */
};
enum { FL_PLAYED = 0x80, FL_TWO = 0x40, FL_LEG1 = 0x20, FL_Y = 1, FL_DEC = 2, FL_AET = 4, FL_PEN = 8 };
#define NSTG 4                          /* the earlier stages kept: play-offs, round of 16, quarter-finals, semi-finals */
#define NTIE 22                         /* (8 + 8 + 4 + 2) */
struct cup { u8 id, n[NSTG], ss; struct tie t[NTIE]; };    /* ss: the season stamp, seasonPlaying + 1 (0: none) */
struct { u32 tag; struct cup c; } US = { 0x52423253 };   /* 'S2BR' (the harness finds the block by it), then the
                                           career club's UEFA cup (the one contest a career keeps: id = its contest 0..2):
                                           stage s's ties after n[0..s-2]'s - the save item's block US_REC = US.c (MC's
                                           'EN' item copies it, zero after an old save) */
#define US_REC US.c
_Static_assert(sizeof US.c == 182, "US_REC: uesum.REC_SIZE");

static u32 nib(u32 a, u32 b) { return (a > 15 ? 15 : a) << 4 | (b > 15 ? 15 : b); }
static __attribute__((noinline)) void norm(u32 i, struct tie *t) {      /* UD's tie i (see the top) */
    u32 two = w16(UD + 0x14B) == 2, l2 = w16(UD + 0x149) != 0;
    const u8 *pr = UD + 0x2CD + 2 * i;
    u32 f = UD[0x89 + i], s = w16(UD + 0xC9 + 2 * i), a = w16(UD + 0x14D + 2 * i), p = w16(UD + 0x1CD + 2 * i);
    u32 fl = two ? FL_TWO : 0;
    t->x = w16(UD + 0x24D + 2 * pr[l2]);
    t->y = w16(UD + 0x24D + 2 * pr[!l2]);
    t->l1 = t->l2 = 0;
    if (l2) {                                   /* the second leg's turn: the first leg (hi = y now), this leg */
        fl |= FL_LEG1;
        t->l1 = (u8)nib(a & 0xFF, a >> 8);
        if (f & 0x80) { fl |= FL_PLAYED; t->l2 = (u8)nib(s & 0xFF, s >> 8); }
    } else if (f & 0x80) {
        fl |= two ? FL_LEG1 : FL_PLAYED;
        t->l1 = (u8)nib(s >> 8, s & 0xFF);
    }
    if (fl & FL_PLAYED) fl |= (f & (FL_DEC | FL_AET | FL_PEN)) | ((f ^ l2) & FL_Y);  /* (1: the pair's second club) */
    t->pn = (u8)(l2 ? nib(p & 0xFF, p >> 8) : nib(p >> 8, p & 0xFF));
    t->fl = (u8)fl;
}

static __attribute__((noinline)) void tline(const struct tie *t) {
    const char *nx = name(t->x), *ny = name(t->y);
    u32 fl = t->fl;
    if (!nx || !ny) return;
    brk();
    add("  "); add(nx); word(" - "); word(ny);
    if (!(fl & (FL_LEG1 | FL_PLAYED))) return;
    score(t->l1 >> 4, t->l1 & 15, 0);
    if (!(fl & FL_PLAYED)) return;
    if (fl & FL_TWO) { score(t->l2 >> 4, t->l2 & 15, 0); score((t->l1 >> 4) + (t->l2 >> 4), (t->l1 & 15) + (t->l2 & 15), 1); }
    if (fl & FL_PEN) { word(" "); word(txt(T_PEN)); score(t->pn >> 4, t->pn & 15, 0); }
    else if (fl & FL_AET) { word(" "); word(txt(T_AET)); }
}

static void ko(void) {
    struct tie t;
    for (u32 i = 0, nt = w16(UD + 0x51); i < nt && i < 32; i++) { norm(i, &t); tline(&t); }
}

/* 4.1 S2b, the recorder: after every match cseg_28E76 plays (its common exit, us_hook) the contest's knockout stage
   1..NSTG into US_REC - the stage's last state is its result; recording stage s drops the stages after it, another
   cup or season (MC 08/11: the stamp) drops them all. */
void us_rec(void) {
    u32 s = w16(UC + 0x53), nt = w16(UD + 0x51), off = 0;
    if (UD[0] != 1 || s - 1 >= NSTG || !us_ok()) return;
    struct cup *c = &US_REC;
    if (c->id != UD[0x2D] || c->ss != stamp()) {   /* (another cup, or another season: what is kept is not this one's) */
        c->id = UD[0x2D];
        c->ss = (u8)stamp();
        for (u32 k = 0; k < NSTG; k++) c->n[k] = 0;
    }
    for (u32 k = 0; k + 1 < s; k++) off += c->n[k];
    if (off + nt > NTIE) return;                /* (a stage bigger than the room: not kept) */
    for (u32 k = s; k < NSTG; k++) c->n[k] = 0;
    c->n[s - 1] = (u8)nt;
    for (u32 i = 0; i < nt; i++) norm(i, &c->t[off + i]);
}
extern u16 D0W;                         /* the game's D0 */
void RET28(void);                       /* cseg_28E76's 'xor ax, ax; retn' */
__asm__(".globl us_hook\nus_hook:\n\tpushal\n\tcall us_rec\n\tpopal\n\tmovw $0, D0W\n\tjmp RET28\n");

static void earlier(u32 st) {                   /* the recorded stages before the current one */
    const struct cup *c = &US_REC;
    if (c->id != UD[0x2D] || c->ss != stamp()) return;   /* (another cup's or season's; an older save's zero block) */
    for (u32 s = 1, off = 0; s < st && s <= NSTG; off += c->n[s - 1], s++) {
        if (!c->n[s - 1]) continue;
        head(stname(s), 0);
        for (u32 i = 0; i < c->n[s - 1]; i++) tline(&c->t[off + i]);
    }
}

static void table(void) {                       /* the league phase: 'place NAME points', several to a line */
    u32 n = w16(UD + 0x4F) * w16(UD + 0x51);
    brk();
    add("  ");
    for (u32 k = 0; k < n && k < 64; k++) {
        u32 off = w16(UD + 0x6D + 2 * k);
        const char *nm = name(w16(UD + 0x12D + 2 * (off / 18)));
        if (!nm) continue;
        char b[40], *q = dig(b, k + 1);
        *q++ = ' ';
        for (int j = 0; nm[j] && j < 17; j++) *q++ = nm[j];
        *q++ = ' ';
        q = dig(q, w16(UD + 0x2B3 + off + 16));
        *q++ = ' '; *q++ = ' '; *q = 0;
        word(b);
    }
}

void us_text(void) {
    o = TXT; nl = px = 0;
    char *t = TITLE;
    for (int i = 0; i < 24 && UD[4 + i]; i++) *t++ = (char)UD[4 + i];
    *t = 0;
    const char *h = HOLD[UD[0x2D]] ? name(HOLD[UD[0x2D]]) : 0;   /* (0: none yet, a world's first season) */
    if (h) head(txt(T_HOLD), h);
    u32 st = w16(UC + 0x53), ko_ = UD[0] == 1;
    earlier(st);
    head(stname(st), 0);
    if (ko_) ko(); else table();
    for (u32 s = st + 1; s < 6 && w16(UC + 0x15D + 0x76 * s + 4); s++) head(stname(s), txt(T_TBP));
    if (ko_ && w16(UD + 0x39) != 0xFFFF && (h = name(w16(UD + 0x39)))) head(txt(T_WIN), h);
    *o = 0;
}
