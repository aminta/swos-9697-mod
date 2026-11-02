/* COPPE CONTINENTALI / CONTINENTAL CUPS (4.0.6, Gianmarco's ask): the other confederations' club cups of a world
   career as fmtpage text, for a player who is not taking part. obj3 (tools/ctview.py), linked with conti.c's
   symbols (obj1 code, obj2 .bss) by cross-object fixups.

   No state of its own: the edition in progress (CT_ED, in the save) is replayed by conti.c's ct_resume() - the same
   deterministic run a load does, so CT_IN / CT_OUT / CT_SEG end as they were (harness: the career club's next tie
   byte-identical) - and CT_OUT's draws and results are read back. A round shows only once its month has come in the
   career calendar (its draw), its results once that month is over; the run stops at the career club's next game,
   so the rounds after it are TO BE PLAYED. No scores: the conti matches have no goals, only who went through.
   Season 1 (no edition yet: the build drew the main rounds, CT_LP): those draws only.

   cv_text(conf, week, out, room): confederation conf's cups, each from a new page (FF), lines LF, 14 a page,
   at most room bytes; returns the length. cv_confs(word, order): the confederations with a cup, the career club's
   first (team word = its file's association); returns their number. Names: DATA\TEAM.nnn (as winners.py). */

#include "conti.h"

extern const u8 *CT_SPEC;
extern u16 *CT_LP[NCUP];
extern struct ct_in CT_IN;
extern struct ct_state CT_ST;
extern struct ct_out CT_OUT;
extern struct ct_ed CT_ED;
extern struct ct_seg CT_SEG;
void ct_resume(void);

/* ctview.py's table: u16 text offsets [8] (holder, to be played, winner, group, earlier rounds, none, -, -),
   u8 widths [64] (' '..'_'), u8 na, u8 ncup, u8 the association's league file [na], u8 its confederation [na],
   then per cup: u8 conf, u8 nrd, u16 name, u16 round names [nrd]; strings NUL-ended (offsets from the table) */
#ifdef NATIVE
u8 CV_TAB[8192];
#else
extern const u8 CV_TAB[];
#endif
enum { T_HOLD, T_TBP, T_WIN, T_GRP, T_BEFORE, T_NONE };

#define PXMAX 298                       /* fmtpage's line (fmtgame PX_MAX) */
#define LINES 14
#define LW 63

static u32 w16(const u8 *p) { return p[0] | p[1] << 8; }
static const char *txt(int k) { return (const char *)CV_TAB + w16(CV_TAB + 2 * k); }
static int cwid(u8 ch) { return ch >= 0x20 && ch < 0x60 ? CV_TAB[16 + ch - 0x20] : 6; }
static int spx(const char *s) { int n = 0; while (*s) n += cwid((u8)*s++); return n; }
static int slen(const char *s) { int n = 0; while (s[n]) n++; return n; }

static const u8 *cuptab(int c) {        /* cup c's entry */
    int na = CV_TAB[80];
    const u8 *p = CV_TAB + 82 + 2 * na;
    for (int i = 0; i < c; i++) p += 4 + 2 * p[1];
    return p;
}

/* --- the spec's rounds (conti.c's parse(), the part this needs) ---------------------------------------------------- */
static const u8 *rnd0[NCUP];
static u8 nr[NCUP], ncup;
static void spec(void) {
    const u8 *p = CT_SPEC;
    ncup = p[0];
    p += 4;
    for (int c = 0; c < ncup && c < NCUP; c++) { nr[c] = p[0]; rnd0[c] = p + 4; p += 4 + nr[c] * RB; }
}
#define RD(c, r) (rnd0[c] + (r) * RB)
static u32 mweek(int m) { return (u32)((m - 1 + (m < 8 ? 12 : 0)) * 8); }   /* (x 8 from January, as CT_SEG.month) */

/* --- names ---------------------------------------------------------------------------------------------------------- */
static char fname[] = "data\\team.000";
static char nbuf[18];
#ifdef NATIVE
const char *(*cv_native_name)(u32);
static const char *name(u32 w) { return cv_native_name(w); }
#else
static int dos(u32 ax, u32 bx, u32 cx, u32 dx) {
    u32 r; u8 cf;
    __asm__ volatile("int $0x21; setc %1" : "=a"(r), "=qm"(cf), "+b"(bx), "+c"(cx), "+d"(dx) : "0"(ax) : "memory", "cc");
    return cf ? -1 : (int)(r & 0xFFFF);
}
static const char *name(u32 w) {        /* team word: file w & FF, record w >> 8 (2 + 684 x n, teamName at +5) */
    u32 f = w & 0xFF, off = 2 + 684 * ((w >> 8) & 0xFF) + 5;
    fname[10] = (char)('0' + f / 100); fname[11] = (char)('0' + f / 10 % 10); fname[12] = (char)('0' + f % 10);
    nbuf[0] = '?'; nbuf[1] = 0;
    int h = dos(0x3D00, 0, 0, (u32)fname);
    if (h < 0) return nbuf;
    if (dos(0x4200, (u32)h, off >> 16, off & 0xFFFF) >= 0 && dos(0x3F00, (u32)h, 17, (u32)nbuf) == 17) nbuf[17] = 0;
    else { nbuf[0] = '?'; nbuf[1] = 0; }
    dos(0x3E00, (u32)h, 0, 0);
    return nbuf;
}
#endif
static const char *cname(int x) { return x ? name(CT_IN.club[x - 1].id) : "-"; }   /* a run's club index + 1 */

/* --- the text: lines into out, a page every LINES ------------------------------------------------------------------ */
static char *o, *oend;
static int nline;
static char cur[LW + 1];
static int clen, cpx;
static void put(char ch) { if (o < oend) *o++ = ch; }
static void endline(void) {
    if (nline && nline % LINES == 0) put('\f');
    else if (nline) put('\n');
    for (int i = 0; i < clen; i++) put(cur[i]);
    nline++;
    clen = cpx = 0;
}
static void newpage(void) {             /* the next line starts a page (a cup's first) */
    if (clen) endline();
    while (nline % LINES) { put('\n'); nline++; }
}
static void keep(int k) {              /* the next k lines on one page (a header with its first line) */
    if (clen) endline();
    if (nline % LINES && nline % LINES + k > LINES) newpage();
}
static void add(const char *s) {        /* s (trailing spaces kept) on this line */
    while (*s) {
        if (clen < LW) { cur[clen++] = *s; cpx += cwid((u8)*s); }
        s++;
    }
}
static void word(const char *s, int indent) {   /* s whole on this line, else on the next one after indent spaces */
    if (clen && (clen + slen(s) > LW || cpx + spx(s) > PXMAX)) {
        endline();
        for (int i = 0; i < indent; i++) add(" ");
    }
    add(s);
}
static void head(const char *rname, const char *tail) { add(rname); add(":"); if (tail) { add(" "); add(tail); } }

/* one round: ko ties (a winner's '>' once played), groups by final place (draw order before) */
static void round_lines(int c, int r, int played) {
    const u8 *R = RD(c, r);
    const u8 *ct = cuptab(c);
    const char *rn = (const char *)CV_TAB + w16(ct + 4 + 2 * r);
    int n = CT_OUT.nent[c][r];
    if (R[0] == K_GROUPS) {
        int ng = R[6], gs = R[7];
        for (int g = 0; g < ng; g++) {
            char t[3] = { ' ', (char)('A' + g), 0 };
            keep(2 + (gs > 4));
            add(ng > 1 ? txt(T_GRP) : rn);
            if (ng > 1) add(t);
            add(":");
            if (!played) { add(" "); add(txt(T_TBP)); }
            endline();
            add("  ");
            for (int q = 1; q <= gs; q++)
                for (int k = 0; k < gs; k++) {
                    int i = g * gs + k;
                    if (i >= n || !CT_OUT.ent[c][r][i]) continue;
                    if (played ? CT_OUT.res[c][r][i] != q : k + 1 != q) continue;
                    char b[40];
                    int m = 0;
                    if (played) { if (q >= 10) b[m++] = (char)('0' + q / 10); b[m++] = (char)('0' + q % 10); b[m++] = ' '; }
                    for (const char *s = cname(CT_OUT.ent[c][r][i]); *s && m < 36; ) b[m++] = *s++;
                    b[m++] = ' '; b[m++] = ' '; b[m] = 0;
                    word(b, 2);
                }
            endline();
        }
        return;
    }
    keep(2);
    head(rn, played ? 0 : txt(T_TBP));
    endline();
    for (int i = 0; i + 1 < n; i += 2) {
        int w = CT_OUT.res[c][r][i];
        add(played && w ? "  >" : "  ");
        add(cname(CT_OUT.ent[c][r][i]));
        add(" - ");
        if (played && !w) add(">");
        add(cname(CT_OUT.ent[c][r][i + 1]));
        endline();
    }
}

static int seg_before(int c, int r, int mo) {   /* round (mo, c, r) runs before the career club's next game */
    if (CT_SEG.kind == 0xFF) return 1;
    int sm = RD(CT_SEG.cup, CT_SEG.round)[9], smo = (sm + 4) % 12;   /* (calendar order: August first) */
    if (mo != smo) return mo < smo;
    if (c != CT_SEG.cup) return c < CT_SEG.cup;
    return r < CT_SEG.round;
}

static int main_after(int c, int r) {   /* round r comes after cup c's main round (calendar order) */
    for (int k = 0; k < nr[c]; k++)
        if (RD(c, k)[17]) {
            int a = (RD(c, k)[9] + 4) % 12, b = (RD(c, r)[9] + 4) % 12;
            return b > a || (b == a && r > k);
        }
    return 0;
}

static void cup_lines(int c, u32 week, int live) {
    const u8 *ct = cuptab(c);
    newpage();
    add((const char *)CV_TAB + w16(ct + 2));
    endline();
    if (live && CT_ST.mark == 0x5443 && CT_ST.hold[c].id) { head(txt(T_HOLD), name(CT_ST.hold[c].id)); endline(); }
    int done = 1;
    for (int mo = 0; mo < 12; mo++) {   /* calendar order, as conti.c's run() */
        int m = (mo + 7) % 12 + 1;
        for (int r = 0; r < nr[c]; r++) {
            const u8 *R = RD(c, r);
            if (R[9] != m) continue;
            if (!live) {                /* season 1: the main round's draw (the build's), the rounds before it played */
                if (!CT_LP[c]) continue;
                if (!R[17]) {
                    if (main_after(c, r)) { head((const char *)CV_TAB + w16(ct + 4 + 2 * r), txt(T_TBP)); endline(); }
                    continue;
                }
                int gs = R[0] == K_GROUPS ? R[7] : 2, n = R[0] == K_GROUPS ? R[6] * R[7] : 0;
                if (!n) while (n < 32 && CT_LP[c][n] != 0xFFFF && CT_LP[c][n]) n++;
                if (r) { add(txt(T_BEFORE)); endline(); }
                const char *rn = (const char *)CV_TAB + w16(ct + 4 + 2 * r);
                for (int g = 0; g * gs < n; g++) {
                    if (R[0] == K_GROUPS) {
                        char t[3] = { ' ', (char)('A' + g), 0 };
                        keep(2);
                        add(R[6] > 1 ? txt(T_GRP) : rn); if (R[6] > 1) add(t); add(": "); add(txt(T_TBP)); endline();
                        add("  ");
                        for (int k = 0; k < gs; k++) {
                            u16 w = CT_LP[c][g * gs + k];
                            if (!w || w == 0xFFFF) continue;
                            char b[24]; int q = 0;
                            for (const char *s = name(w); *s && q < 20; ) b[q++] = *s++;
                            b[q++] = ' '; b[q++] = ' '; b[q] = 0;
                            word(b, 2);
                        }
                        endline();
                    } else {
                        if (!g) { head(rn, txt(T_TBP)); endline(); }
                        add("  "); add(name(CT_LP[c][2 * g])); add(" - "); add(name(CT_LP[c][2 * g + 1])); endline();
                    }
                }
                continue;
            }
            int n = CT_OUT.nent[c][r];
            int drawn = n && seg_before(c, r, mo) ? 2 : (CT_SEG.kind != 0xFF && CT_SEG.cup == c && CT_SEG.round == r);
            if (R[0] == K_KO && R[18] && n && 2 * n <= R[18]) continue;   /* (all through without playing: no ties) */
            if (!n && seg_before(c, r, mo)) continue;                 /* (no entrants: not played this season) */
            const char *rn = (const char *)CV_TAB + w16(ct + 4 + 2 * r);
            if (week < mweek(m) || !drawn) {   /* not drawn yet */
                head(rn, txt(T_TBP)); endline(); done = 0;
                continue;
            }
            int played = drawn == 2 && week >= mweek(m) + 8;
            if (!played) done = 0;
            round_lines(c, r, played);
        }
    }
    if (live && done && CT_OUT.winner[c]) { head(txt(T_WIN), cname(CT_OUT.winner[c])); endline(); }
}

u32 cv_text(u32 conf, u32 week, char *out, u32 room) {
    o = out; oend = out + room - 1; nline = 0; clen = cpx = 0;
    if (!CT_SPEC) { add(txt(T_NONE)); endline(); *o = 0; return (u32)(o - out); }
    spec();
    int live = CT_ED.mark == 0x4543;
    if (live) ct_resume();              /* (the replay: CT_OUT as it stands, CT_SEG unchanged) */
    int any = 0;
    for (int c = 0; c < ncup; c++)
        if (cuptab(c)[0] == conf) { cup_lines(c, week, live); any = 1; }
    if (!any) { add(txt(T_NONE)); endline(); }
    if (clen) endline();
    *o = 0;
    return (u32)(o - out);
}

u32 cv_confs(u32 word, u8 *order) {     /* the confederations with a cup (ctview.py's numbers), the career club's first */
    int na = CV_TAB[80], nc = CV_TAB[81], k = 0, mine = 0xFF;
    for (int a = 0; a < na; a++) if (CV_TAB[82 + a] == (word & 0xFF)) mine = CV_TAB[82 + na + a];
    for (int pass = 0; pass < 2; pass++)
        for (int c = 0; c < nc; c++) {
            int f = cuptab(c)[0], seen = 0;
            if ((pass == 0) != (f == mine)) continue;
            for (int i = 0; i < k; i++) if (order[i] == f) seen = 1;
            if (!seen) order[k++] = (u8)f;
        }
    return (u32)k;
}
