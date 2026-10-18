/* Knockout promotion / relegation play-offs of a career world's leagues (pack.json league 'ko_playoffs', kind
   'promotion'), decided at the season end from the final tables (tools/gplay.py; the European play-offs are
   uefaq's, the Italian ones dplay's).

   GP_IN.spec: the country's play-offs, each
     kind (1 promotion, 2 europe, 3 placement), n entrants, rounds, winner_div, loser_div, flags,
     n x (type, div, a, b): type 0 = [div, place a], 1 = the best of div without Europe, 2 = the league cup winner;
     rounds x (ties, legs, host, level, pairing) + 2 x ties member codes: 0..63 an entrant, 0x80|k the winner of
     tie k, 0xC0|k its loser (ties numbered across rounds); pairing p > 0 = the first p members best v worst, re-paired;
   ended by a 0. Only the promotion play-offs whose entrants are all [div, place] are played here. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;

enum { GT = 24, GD = 6, GN = 64 };
enum { HOST_LISTED, HOST_BETTER, HOST_DRAWN, HOST_NEUTRAL };
enum { LV_BETTER, LV_ET_PENS, LV_ET_BETTER, LV_PENS };
struct gp_row { u16 team, glob, won, gf, ga, pts; };
struct gp_in {
    u8 nd, pad[3];
    u8 n[GD], pad2[2];                  /* clubs per division (0 = not captured) */
    struct gp_row t[GD][GT];
    const u8 *spec;
};
struct gp_mv { u16 glob, team; s8 delta; u8 pad[3]; };
struct gp_out { u8 nmv, pad[3]; struct gp_mv mv[32]; };
struct gp_in GP_IN;
struct gp_out GP_OUT;
const u32 GP_LAYOUT[] = { sizeof(struct gp_row), GT, __builtin_offsetof(struct gp_in, n),
                          __builtin_offsetof(struct gp_in, t), __builtin_offsetof(struct gp_in, spec),
                          __builtin_offsetof(struct gp_out, mv), sizeof(struct gp_mv), GD };

static u32 rng;
static u32 below(u32 n) {
    rng = rng * 1103515245u + 12345u;
    return ((rng >> 16) * n) >> 16;
}

#define DV(c) ((c) / GT)
#define PL(c) ((c) % GT)
static const struct gp_row *row(int c) { return &GP_IN.t[DV(c)][PL(c)]; }

static int better(int a, int b) {       /* the higher tier, then the better place */
    if (DV(a) != DV(b)) return DV(a) < DV(b);
    return PL(a) < PL(b);
}

static u32 str2(int c, int home) {      /* strength: the place in its division, the tier */
    int n = GP_IN.n[DV(c)];
    int s = 30 + 40 * (n - PL(c)) / (n ? n : 1) - 25 * DV(c);
    if (s < 5) s = 5;
    if (home) s = s * 11 / 10;
    return (u32)(s * s);
}

/* a tie: a = the single match's host / the first leg's home club (listed order), b = the other */
static int tie(int a, int b, int legs, int host, int level) {
    int h = a, o = b, w;
    if (host == HOST_BETTER || host == HOST_NEUTRAL) {      /* the better placed hosts the single match / return */
        if (better(b, a)) { h = b; o = a; }
        else { h = a; o = b; }
        if (legs == 2 || host == HOST_NEUTRAL) { int x = h; h = o; o = x; }   /* (h = the first leg's / listed) */
    } else if (host == HOST_DRAWN && below(2)) { h = b; o = a; }
    /* the club with home advantage: a single match's host, the return leg's home club */
    int adv = (legs == 1) ? (host == HOST_NEUTRAL ? -1 : h) : o;
    u32 sh = str2(h, adv == h), so = str2(o, adv == o);
    if (below(100) < (legs == 1 ? 22u : 12u)) {             /* level after the regulation time */
        int bp = better(h, o) ? h : o;
        if (level == LV_BETTER || level == LV_ET_BETTER) return bp;
        u32 x = str2(h, 0), y = str2(o, 0);                   /* e.t. + penalties: close to a coin toss */
        sh = 2 * x + y; so = x + 2 * y;
    }
    w = below(sh + so) < sh ? h : o;
    return w;
}

static void move(int c, int delta) {
    if (!delta || GP_OUT.nmv >= 32) return;
    struct gp_mv *m = &GP_OUT.mv[GP_OUT.nmv++];
    m->glob = row(c)->glob; m->team = row(c)->team; m->delta = delta;
}

static int sbetter_cmp(int a, int b) { return better(a, b); }

void gp_season(void) {
    const u8 *s = GP_IN.spec;
    u32 h = 0;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) h = h * 31 + GP_IN.t[d][k].glob + (GP_IN.t[d][k].pts << 9);
    rng = h;
    GP_OUT.nmv = 0;
    while (s && *s) {
        int kind = s[0], n = s[1], nr = s[2], wdiv = s[3], ldiv = s[4];
        const u8 *e = s + 6, *r = e + 4 * n;
        int club[GN], ok = kind == 1, W[GN], L[GN], nt = 0, last = -1;
        for (int i = 0; i < n && i < GN; i++) {
            int d = e[4 * i + 1], p = e[4 * i + 2];
            if (e[4 * i] != 0 || d >= GP_IN.nd || p < 1 || p > GP_IN.n[d]) ok = 0;
            else club[i] = d * GT + p - 1;
        }
        for (int k = 0; k < nr; k++) {          /* walk the rounds (also to skip a play-off not played here) */
            int ties = r[0], legs = r[1], host = r[2], level = r[3], pairing = r[4];
            const u8 *m = r + 5;
            int mem[2 * GN];
            for (int i = 0; i < 2 * ties; i++) {
                int c = m[i], v = -1;
                if (c < 0x80) v = c < n ? club[c] : -1;
                else if (c < 0xC0) v = (c & 0x3F) < nt ? W[c & 0x3F] : -1;
                else v = (c & 0x3F) < nt ? L[c & 0x3F] : -1;
                mem[i] = v;
                if (v < 0) ok = 0;
            }
            if (ok && pairing) {            /* best v worst: sorted, then 1st v last, 2nd v second last ... */
                int pn = pairing <= 2 * ties ? pairing : 2 * ties;
                for (int i = 1; i < pn; i++) {
                    int x = mem[i], j = i;
                    while (j > 0 && sbetter_cmp(x, mem[j - 1])) { mem[j] = mem[j - 1]; j--; }
                    mem[j] = x;
                }
                int tmp[2 * GN];
                for (int i = 0; i < pn / 2; i++) { tmp[2 * i] = mem[pn - 1 - i]; tmp[2 * i + 1] = mem[i]; }
                for (int i = 0; i < pn; i++) mem[i] = tmp[i];
            }
            for (int i = 0; i < ties; i++) {
                if (ok && nt < GN) {
                    int w = tie(mem[2 * i], mem[2 * i + 1], legs, host, level);
                    W[nt] = w; L[nt] = w == mem[2 * i] ? mem[2 * i + 1] : mem[2 * i];
                    last = nt;
                }
                nt++;
            }
            r = m + 2 * ties;
        }
        if (ok && last >= 0) {                  /* the winner to winner_div; another winner_div entrant down */
            int w = W[last];
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c);
                if (c == w) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                move(c, to - DV(c));
            }
        }
        s = r;
    }
}

/* Parallel groups at the season end (pgroups.py: InitializeNewSeason's copy-back, leaguesTableCopy -> someLeaguesTable).
   A country's table: db world, levels; per level db first division, groups, sizes[groups] (top-down, all the chain's
   divisions); dw clubs; clubs x (dw global number, db base division, db area: a group index, 0xFF = none). The game
   moved each club by its division's promoted / relegated counts: one division up or down the chain. Here a move is
   one LEVEL up or down instead: into a single division as it is, into a level of groups to the group of the club's
   area, else the nearest one with room (each group keeps its size). Ended by a 0. */
enum { PL = 8, PG = 6 };
static u8 pg_pend[4096 / 8];                      /* (bits, by global number: the 4096 tables to come) */
#define PEND(g) (pg_pend[(g) >> 3] & (1 << ((g) & 7)))

static int pg_level(int d, int nl, const u8 *first, const u8 *cnt) {
    for (int l = nl - 1; l >= 0; l--) if (d >= first[l]) return l;
    return 0;
}

static void pg_one(const u8 *t, const s8 *slt, s8 *copy) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG];
    const u8 *sz[PL], *p = t + 2;
    if (nl > PL) return;
    for (int l = 0; l < nl; l++) {
        first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; p += 2 + p[1];
        for (int g = 0; g < PG; g++) occ[l][g] = 0;
    }
    int nc = p[0] | p[1] << 8;
    const u8 *c = p + 2;
    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + 4 * i;
            int g = e[0] | e[1] << 8, base = e[2], area = e[3];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            if (pass == 1) {                    /* into a level of groups: the area's, else the nearest with room */
                if (!PEND(g)) continue;
                pg_pend[g >> 3] &= ~(1 << (g & 7));
                int n = copy[g] + base, o = slt[g] + base;       /* (copy still the game's move) */
                int lo = pg_level(o, nl, first, cnt), tl = n < o ? lo - 1 : lo + 1;
                int a = area < cnt[tl] ? area : area == 0xFF ? cnt[tl] / 2 : cnt[tl] - 1, to = a;
                for (int k = 0; k < PG; k++) {
                    if (a + k < cnt[tl] && occ[tl][a + k] < sz[tl][a + k]) { to = a + k; break; }
                    if (a - k >= 0 && occ[tl][a - k] < sz[tl][a - k]) { to = a - k; break; }
                }
                occ[tl][to]++;
                copy[g] = first[tl] + to - base;
                continue;
            }
            int o = slt[g] + base, n = copy[g] + base, lo = pg_level(o, nl, first, cnt);
            int tl = n < o ? lo - 1 : n > o ? lo + 1 : lo;
            if (tl < 0 || tl >= nl) continue;   /* (off the chain: as the game moved it) */
            if (tl == lo) {                     /* staying: counted in its group */
                if (o - first[lo] < cnt[lo]) occ[lo][o - first[lo]]++;
            } else if (cnt[tl] == 1)
                copy[g] = first[tl] - base;
            else
                pg_pend[g >> 3] |= 1 << (g & 7);
        }
}

void pg_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    while (*t) {
        int nl = t[1];
        const u8 *p = t + 2;
        for (int l = 0; l < nl; l++) p += 2 + p[1];
        int nc = p[0] | p[1] << 8;
        if (t[0] == world) pg_one(t, slt, copy);
        t = p + 2 + 4 * nc;
    }
}
