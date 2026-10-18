/* Knockout promotion / relegation play-offs of a career world's leagues (pack.json league 'ko_playoffs', kind
   'promotion'), decided at the season end from the final tables (tools/gplay.py; the European play-offs are
   uefaq's, the Italian ones dplay's).

   GP_IN.spec: the country's play-offs, each
     kind (1 promotion, 2 europe, 3 placement, 4 playout), n entrants, rounds, winner_div, loser_div (0xFE: the
     reserve, out of the league = division nd), flags,
     n x (type, div, a, b): type 0 = [div, place a], 1 = the best of div without Europe, 2 = the league cup winner;
     rounds x (ties, legs, host, level, pairing, gap) + 2 x ties member codes: 0..63 an entrant, 0x80|k the winner of
     tie k, 0xC0|k its loser (ties numbered across rounds); pairing p > 0 = the first p members best v worst, re-paired;
   gap g > 0: a tie whose clubs are g+ points apart is not played, the better placed goes through;
   a GROUP round (a round robin): (members m, 0x80 | meetings, host, 0, 0, 0) + m member codes + m start bonus points;
   its final placings are appended to the placings list (numbered across the group rounds), member code 0x40|k = the
   k-th placing; flags bits 4-7 = 'winners' (a promotion play-off ending with a group: its top w go to winner_div,
   the other winner_div clubs to loser_div; 0 = 1); ended by a 0.
   Only the promotion / playout play-offs whose entrants are all [div, place] are played here: promotion = the
   winner to winner_div, another winner_div entrant to loser_div; playout = the last round's losers to loser_div. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;

enum { GT = 24, GD = 8, GN = 64, RESERVE = 0xFE };
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

/* a group match: goals by strength (draws ~ 1 in 4), home advantage unless neutral */
static void gmatch(int h, int a, int neutral, int *gh, int *ga) {
    u32 sh = str2(h, !neutral), sa = str2(a, 0);
    if (below(100) < 26) { int g = below(3); *gh = g; *ga = g; return; }
    int w = below(sh + sa) < sh, gw = 1 + below(3), gl = below(gw);
    *gh = w ? gw : gl; *ga = w ? gl : gw;
}

struct gs { int c, pts, gd, gf; };
static int gs_before(const struct gs *x, const struct gs *y) {   /* points, goal difference, goals, the better place */
    if (x->pts != y->pts) return x->pts > y->pts;
    if (x->gd != y->gd) return x->gd > y->gd;
    if (x->gf != y->gf) return x->gf > y->gf;
    return better(x->c, y->c);
}

/* a group round: mem[0..m) round robin `meet` times (home and away alternate), start bonus points; placings -> out */
static void group(const int *mem, int m, int meet, int neutral, const u8 *bonus, int *out) {
    struct gs t[GT];                    /* (at most 24 members: compile_spec)  */
    for (int i = 0; i < m; i++) { t[i].c = mem[i]; t[i].pts = bonus[i]; t[i].gd = 0; t[i].gf = 0; }
    for (int k = 0; k < meet; k++)
        for (int i = 0; i < m; i++)
            for (int j = i + 1; j < m; j++) {
                int h = (k & 1) ? j : i, a = (k & 1) ? i : j, gh, ga;
                gmatch(t[h].c, t[a].c, neutral, &gh, &ga);
                t[h].gf += gh; t[a].gf += ga; t[h].gd += gh - ga; t[a].gd += ga - gh;
                if (gh > ga) t[h].pts += 3; else if (gh < ga) t[a].pts += 3; else { t[h].pts++; t[a].pts++; }
            }
    for (int i = 1; i < m; i++) {
        struct gs x = t[i]; int j = i;
        while (j > 0 && gs_before(&x, &t[j - 1])) { t[j] = t[j - 1]; j--; }
        t[j] = x;
    }
    for (int i = 0; i < m; i++) out[i] = t[i].c;
}

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
        int club[GN], ok = kind == 1 || kind == 4, W[GN], L[GN], nt = 0, last = -1, lastr = 0, nlast = 0;
        int P[GN], np = 0, glast = -1, winners = s[5] >> 4 ? s[5] >> 4 : 1;
        for (int i = 0; i < n && i < GN; i++) {
            int d = e[4 * i + 1], p = e[4 * i + 2];
            if (e[4 * i] != 0 || d >= GP_IN.nd || p < 1 || p > GP_IN.n[d]) ok = 0;
            else club[i] = d * GT + p - 1;
        }
        for (int k = 0; k < nr; k++) {          /* walk the rounds (also to skip a play-off not played here) */
            int ties = r[0], legs = r[1], host = r[2], level = r[3], pairing = r[4], gap = r[5];
            const u8 *m = r + 6;
            int mem[2 * GN], gm = legs & 0x80 ? ties : 2 * ties;     /* (a group round: ties = its members) */
            for (int i = 0; i < gm; i++) {
                int c = m[i], v = -1;
                if (c < 0x40) v = c < n ? club[c] : -1;
                else if (c < 0x80) v = (c & 0x3F) < np ? P[c & 0x3F] : -1;
                else if (c < 0xC0) v = (c & 0x3F) < nt ? W[c & 0x3F] : -1;
                else v = (c & 0x3F) < nt ? L[c & 0x3F] : -1;
                mem[i] = v;
                if (v < 0) ok = 0;
            }
            if (legs & 0x80) {                  /* a group round */
                if (ok && ties <= GT && np + ties <= GN) {
                    group(mem, ties, legs & 0x7F, host == HOST_NEUTRAL, m + ties, P + np);
                    glast = np;
                }
                np += ties;
                last = -1;
                r = m + 2 * ties;
                continue;
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
            lastr = nt; nlast = ties;
            for (int i = 0; i < ties; i++) {
                if (ok && nt < GN) {
                    int a = mem[2 * i], b = mem[2 * i + 1], d = (int)row(a)->pts - (int)row(b)->pts;
                    int w = gap && (d >= gap || -d >= gap) ? (better(a, b) ? a : b)   /* (too far apart: no tie) */
                                                           : tie(a, b, legs, host, level);
                    W[nt] = w; L[nt] = w == mem[2 * i] ? mem[2 * i + 1] : mem[2 * i];
                    last = nt; glast = -1;
                }
                nt++;
            }
            r = m + 2 * ties;
        }
        if (ldiv == RESERVE) ldiv = GP_IN.nd;   /* (the reserve: out of every division) */
        if (ok && glast >= 0 && kind == 1) {    /* a final group: its top `winners` to winner_div, the other
                                                   winner_div clubs to loser_div, the rest stay */
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c), top = 0;
                for (int k = 0; k < winners; k++) if (P[glast + k] == c) top = 1;
                if (top) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                move(c, to - DV(c));
            }
        } else if (ok && last >= 0 && kind == 4) {     /* playout: the last round's losers down */
            for (int t = lastr; t < lastr + nlast && t < GN; t++) move(L[t], ldiv - DV(L[t]));
        } else if (ok && last >= 0) {           /* the winner to winner_div; another winner_div entrant down */
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
   The table: db count; per country db world, levels; per level db first division, groups, sizes[groups] (top-down,
   all the chain's divisions); db parallel levels np; dw clubs; clubs x (dw global number, db base division,
   np x db area: per level of groups its group index, 0xFF = none). The game moved each club by its division's
   promoted / relegated counts: one division up or down the chain. Here a move is one LEVEL up or down instead: into a
   single division as it is, into a level of groups to the group of the club's area for that level, else the nearest
   one with room (each group keeps its size). A division past the chain (the reserve, gplay's 'reserve') is a level of
   its own below the last one. */
enum { PL = 8, PG = 6 };
static u8 pg_pend[4096 / 8];                      /* (bits, by global number) */
#define PEND(g) (pg_pend[(g) >> 3] & (1 << ((g) & 7)))

static int pg_level(int d, int nl, const u8 *first, const u8 *cnt) {
    if (d >= first[nl - 1] + cnt[nl - 1]) return nl;   /* (out of the chain: the reserve) */
    for (int l = nl - 1; l >= 0; l--) if (d >= first[l]) return l;
    return 0;
}

static const u8 *pg_one(const u8 *t, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            if (pass == 1) {                    /* into a level of groups: the area's, else the nearest with room */
                if (!PEND(g)) continue;
                pg_pend[g >> 3] &= ~(1 << (g & 7));
                int n = copy[g] + base, o = slt[g] + base;       /* (copy still the game's move) */
                int lo = pg_level(o, nl, first, cnt), tl = n < o ? lo - 1 : lo + 1;
                int area = pidx[tl] < npar ? e[3 + pidx[tl]] : 0xFF;
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
            if (tl < 0 || tl >= nl) continue;   /* (off the chain, or into the reserve: as moved) */
            if (tl == lo) {                     /* staying: counted in its group */
                if (o - first[lo] < cnt[lo]) occ[lo][o - first[lo]]++;
            } else if (cnt[tl] == 1)
                copy[g] = first[tl] - base;
            else
                pg_pend[g >> 3] |= 1 << (g & 7);
        }
    return c + rs * nc;
}

void pg_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pg_one(t, slt, copy, t[0] == world);
}

/* A save from before the groups (3.x: pgroups.py's table on a chain the save's divisions don't know). Every club of
   the table: its division now (base + slt), through map (old division -> new, 0xFF = the same), to its level on the
   new chain; a single division as it is, a level of groups to the group of its area, else the nearest with room (the
   clubs with an area first, so every group keeps its size). copy = the result (not slt: slt is read again). */
static const u8 *pl_one(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 3; pass++)        /* 0: single divisions, 1: groups of the area, 2: the nearest */
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            int d = slt[g] + base;
            if (d >= 0 && d < 256 && map[d] != 0xFF) d = map[d];
            int l = pg_level(d, nl, first, cnt);
            if (l >= nl) { if (pass == 0) copy[g] = d - base; continue; }    /* (the reserve: as it is) */
            if (cnt[l] == 1) { if (pass == 0) copy[g] = first[l] - base; continue; }
            if (pass == 0) { pg_pend[g >> 3] |= 1 << (g & 7); continue; }
            if (!PEND(g)) continue;
            int area = pidx[l] < npar ? e[3 + pidx[l]] : 0xFF, to = -1;
            if (pass == 1) {
                if (area < cnt[l] && occ[l][area] < sz[l][area]) to = area;
            } else {
                int a = area < cnt[l] ? area : cnt[l] / 2;
                for (int k = 0; k < PG && to < 0; k++) {
                    if (a + k < cnt[l] && occ[l][a + k] < sz[l][a + k]) to = a + k;
                    else if (a - k >= 0 && occ[l][a - k] < sz[l][a - k]) to = a - k;
                }
                if (to < 0) to = a;             /* (more clubs than room: the area's group) */
            }
            if (to < 0) continue;
            pg_pend[g >> 3] &= ~(1 << (g & 7));
            occ[l][to]++;
            copy[g] = first[l] + to - base;
        }
    return c + rs * nc;
}

void pg_place(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pl_one(t, map, slt, copy, t[0] == world);
}

/* The reserve (gplay loser_div 'reserve', pack.json league 'reserve', engine.reserve): a pool of clubs out of every
   division (division nd). At the season end (pg_fix, before pg_season places the new clubs by area) every club that
   went down from the lowest level (the game's relegation, gplay's play-out) leaves for the reserve, and as many come
   back from it to the lowest level: the longest out first (the queue: the pool's first order, then each season's
   relegated at its end). Table: db count; per country db world, nd, low (the lowest level's first division); dw clubs;
   clubs x (dw global, db base division); db pool; pool x dw global. State RS_STATE (saved by the engine block):
   per country db init, n, -, -; dw q[RQ]. */
enum { RQ = 64, RC = 8 };
struct rs_state { u8 init, n, pad[2]; u16 q[RQ]; };
struct rs_state RS_STATE[RC];
const u32 RS_STATE_SIZE = sizeof RS_STATE;          /* (gplay.RS_SIZE: the engine block item 'RS') */

static int rs_base(const u8 *c, int nc, int g) {
    for (int i = 0; i < nc; i++) if ((c[3 * i] | c[3 * i + 1] << 8) == g) return c[3 * i + 2];
    return -1;
}

void rs_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    int cnt = *t++;
    for (int k = 0; k < cnt; k++) {
        int w = t[0], nd = t[1], low = t[2], nc = t[3] | t[4] << 8;
        const u8 *c = t + 5, *pl = c + 3 * nc, *pg = pl + 1;
        int np = pl[0];
        t = pg + 2 * np;
        if (w != world || k >= RC) continue;
        struct rs_state *st = &RS_STATE[k];
        if (!st->init) {                        /* (a new career: the pool's first order) */
            st->n = 0;
            for (int i = 0; i < np && i < RQ; i++) st->q[st->n++] = pg[2 * i] | pg[2 * i + 1] << 8;
            st->init = 1;
        }
        u16 out[RQ];
        int no = 0;
        for (int i = 0; i < nc; i++) {          /* down from the lowest level: out, to the reserve */
            int g = c[3 * i] | c[3 * i + 1] << 8, base = c[3 * i + 2];
            int o = base + slt[g], n = base + copy[g];
            if (o >= low && o < nd && n > o && no < RQ) { out[no++] = g; copy[g] = nd - base; }
        }
        int up = no < st->n ? no : st->n, m = 0;
        for (int i = 0; i < up; i++) {          /* back: to the lowest level's first division (pg_season: by area) */
            int g = st->q[i], base = rs_base(c, nc, g);
            if (base >= 0) copy[g] = low - base;
        }
        for (int i = up; i < st->n; i++) st->q[m++] = st->q[i];
        for (int i = 0; i < no && m < RQ; i++) st->q[m++] = out[i];
        st->n = m;
    }
}
