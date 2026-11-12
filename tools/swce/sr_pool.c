/*
 * sr_pool.c -- a light pool's divisions at the season end: England's step 3 (the Northern Premier
 * League, the Southern League Premier Central and South, the Isthmian Premier; Davide 07/11 B).
 * No matches are played: each division's table comes from the clubs' strengths and the season's
 * seed, then its champion and its play-off winner (2nd-7th, the National League's shape) go up. The semi-finals:
 * SR_LP_FIXED (the default, declared: 2nd v W(5v6), 3rd v W(4v7), the National League's bracket; approved by
 * Davide 09/11, until the leagues publish their 2026-27 bracket) or SR_LP_RESEED (2nd v the lower placed winner).
 * The 2026-27 step-3 play-offs are that shape (the NPL, SPL Central / South and Isthmian Premier tables on
 * en.wikipedia, "2026-27 ...": "six teams play for one spot", 2nd-3rd into the semi-finals, 4th-7th the
 * quarter-finals); tests/rules/step3real.c runs the chain on the 2026-27 clubs.
 *
 * Every draw is from a hash of the seed, the division and the clubs' idents (or the tie), never a
 * running generator: the same clubs give the same table whatever the order they come in, and a club
 * swapped in or out changes only its own matches.
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint32_t u32;

static u32 mix(u32 h, u32 v)
{
    h ^= v + 0x9E3779B9u + (h << 6) + (h >> 2);
    h ^= h >> 16; h *= 0x7FEB352Du;
    h ^= h >> 15; h *= 0x846CA68Bu;
    return h ^ (h >> 16);
}

typedef struct { u32 h; } rng;
static u32 below(rng *r, u32 n)                 /* 0 .. n-1; n may exceed 65536 (squared strengths summed): a 64-bit
                                                   product (as gplay.c's light seasons, statesim), the same result
                                                   for every n <= 65536 */
{
    r->h = r->h * 1103515245u + 12345u;
    return (u32)(((uint64_t)(r->h >> 16) * n) >> 16);
}

static u32 str2(int strength, int home, int sp)  /* 30 .. 30 + spread for 0.00 .. 2.50, linear on to 3.75 */
{
    int s = 30 + (strength > 375 ? 375 : strength) * sp / 250;
    if (home) s = s * 11 / 10;
    return (u32)(s * s);
}

/* one light match's goals: a draw ~ 1 in 4, else the winner by the two (squared) strengths */
static void goals(rng *r, u32 sh, u32 sa, int *gh, int *ga)
{
    if (below(r, 100) < 26) { *gh = *ga = (int)below(r, 3); return; }
    const int w = below(r, sh + sa) < sh, gw = 1 + (int)below(r, 3), gl = (int)below(r, (u32)gw);
    *gh = w ? gw : gl; *ga = w ? gl : gw;
}

typedef struct { int pts, gd, gf, gp, won; } fig;

int32_t sr_lp_table_sp(uint32_t seed, int32_t d, const sr_lp_club *c, int32_t n, sr_row *out, int32_t sp)
{
    fig f[SR_LP_CLUBS];
    int ord[SR_LP_CLUBS];
    if (!c || !out || n < 2 || n > SR_LP_CLUBS) return -1;
    for (int i = 0; i < n; i++) { f[i].pts = f[i].gd = f[i].gf = f[i].gp = f[i].won = 0; ord[i] = i; }
    for (int h = 0; h < n; h++)
        for (int a = 0; a < n; a++) {
            if (h == a) continue;
            rng r = { mix(mix(mix(seed, (u32)d), c[h].ident), (u32)c[a].ident << 16 | 1u) };
            const u32 sh = str2(c[h].strength, 1, sp), sa = str2(c[a].strength, 0, sp);
            int gh, ga;
            goals(&r, sh, sa, &gh, &ga);
            f[h].gf += gh; f[h].gd += gh - ga; f[a].gf += ga; f[a].gd += ga - gh;
            f[h].gp++; f[a].gp++;
            if (gh > ga) { f[h].pts += 3; f[h].won++; }
            else if (gh < ga) { f[a].pts += 3; f[a].won++; }
            else { f[h].pts++; f[a].pts++; }
        }
    for (int i = 1; i < n; i++)                 /* points, goal difference, goals, strength, ident */
        for (int j = i; j > 0; j--) {
            const int x = ord[j], y = ord[j - 1];
            const int before = f[x].pts != f[y].pts ? f[x].pts > f[y].pts
                             : f[x].gd != f[y].gd ? f[x].gd > f[y].gd
                             : f[x].gf != f[y].gf ? f[x].gf > f[y].gf
                             : c[x].strength != c[y].strength ? c[x].strength > c[y].strength
                             : c[x].ident < c[y].ident;
            if (!before) break;
            ord[j] = y; ord[j - 1] = x;
        }
    for (int k = 0; k < n; k++) {
        const int i = ord[k];
        out[k].team = (uint16_t)i;
        out[k].glob = c[i].ident;
        out[k].won = (uint16_t)f[i].won;
        out[k].gf = (uint16_t)f[i].gf;
        out[k].ga = (uint16_t)(f[i].gf - f[i].gd);
        out[k].pts = (uint16_t)f[i].pts;
    }
    return 0;
}

/* one match, places a < b (a the better placed, at home): the winner's place */
static int tie(rng *r, const sr_row *t, const sr_lp_club *c, int a, int b, int sp)
{
    const int x = c[t[a].team].strength, y = c[t[b].team].strength;
    u32 sa = str2(x, 1, sp), sb = str2(y, 0, sp);
    if (below(r, 100) < 22) { const u32 p = str2(x, 0, sp), q = str2(y, 0, sp); sa = 2 * p + q; sb = p + 2 * q; }
    return below(r, sa + sb) < sa ? a : b;
}

int32_t sr_lp_semis(int32_t w47, int32_t w56, int32_t bracket, int32_t *v2, int32_t *v3)
{
    if (!v2 || !v3 || (bracket != SR_LP_FIXED && bracket != SR_LP_RESEED)) return -1;
    if (bracket == SR_LP_FIXED) { *v2 = w56; *v3 = w47; return 0; }
    *v2 = w47 > w56 ? w47 : w56;            /* (the lower placed: the larger index) */
    *v3 = w47 > w56 ? w56 : w47;
    return 0;
}

int32_t sr_lp_playoff_b(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c, int32_t sp,
                        int32_t bracket)
{
    if (!table || !c || n < 7 || (bracket != SR_LP_FIXED && bracket != SR_LP_RESEED)) return -1;
    rng r = { mix(mix(seed, (u32)d), 0x504Fu) };
    const int q1 = tie(&r, table, c, 3, 6, sp), q2 = tie(&r, table, c, 4, 5, sp);   /* 4v7, 5v6 */
    int32_t a, b;
    sr_lp_semis(q1, q2, bracket, &a, &b);
    const int s1 = tie(&r, table, c, 1, a, sp), s2 = tie(&r, table, c, 2, b, sp);
    return s1 < s2 ? tie(&r, table, c, s1, s2, sp) : tie(&r, table, c, s2, s1, sp);
}

int32_t sr_lp_playoff_sp(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c, int32_t sp)
{
    return sr_lp_playoff_b(seed, d, table, n, c, sp, SR_LP_FIXED);
}

int32_t sr_lp_season_b(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n, int32_t *up, int32_t sp,
                       int32_t bracket)
{
    sr_row t[SR_LP_CLUBS];
    if (!c || !n || !up || nd < 1 || nd > SR_LP_DIVS) return -1;
    for (int d = 0; d < nd; d++) {
        if (n[d] < 7 || sr_lp_table_sp(seed, d, c[d], n[d], t, sp) != 0) return -1;
        const int32_t w = sr_lp_playoff_b(seed, d, t, n[d], c[d], sp, bracket);
        if (w < 0) return -1;
        up[2 * d] = t[0].team;
        up[2 * d + 1] = t[w].team;
    }
    return 0;
}

int32_t sr_lp_season_sp(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n, int32_t *up,
                        int32_t sp)
{
    return sr_lp_season_b(seed, nd, c, n, up, sp, SR_LP_FIXED);
}

/* ---- a pool with a cross play-off (Italy's Eccellenza) ---- */

/* a regional tie, places a < b: the winner's place */
static int rtie(rng *r, const sr_row *t, const sr_lp_club *c, const sr_lp_rpo *p, int a, int b, int gap, int neutral, int sp)
{
    if (gap && t[a].pts - t[b].pts >= gap) return a;
    const int x = c[t[a].team].strength, y = c[t[b].team].strength;
    if (p->draw_better) {
        if (below(r, 100) < 25) return a;
        const u32 sa = str2(x, !neutral, sp), sb = str2(y, 0, sp);
        return below(r, sa + sb) < sa ? a : b;
    }
    u32 sa = str2(x, !neutral, sp), sb = str2(y, 0, sp);
    if (below(r, 100) < 22) { const u32 q = str2(x, 0, sp), w = str2(y, 0, sp); sa = 2 * q + w; sb = q + 2 * w; }
    return below(r, sa + sb) < sa ? a : b;
}

int32_t sr_lp_regional_sp(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c,
                          const sr_lp_rpo *p, int32_t sp)
{
    if (!table || !c || !p || p->first < 1) return -1;
    const int f = p->first;
    rng r = { mix(mix(seed, (u32)d), 0x52504Fu) };
    switch (p->kind) {
    case SR_LP_RPO_DIRECT:
        return f < n ? f : -1;
    case SR_LP_RPO_FOUR: {
        if (f + 3 >= n) return -1;
        if (p->direct_gap && table[f].pts - table[f + 1].pts >= p->direct_gap) return f;
        const int s1 = rtie(&r, table, c, p, f, f + 3, p->gap_skip, 0, sp), s2 = rtie(&r, table, c, p, f + 1, f + 2, p->gap_skip, 0, sp);
        return rtie(&r, table, c, p, s1 < s2 ? s1 : s2, s1 < s2 ? s2 : s1, p->gap_final, p->final_neutral, sp);
    }
    case SR_LP_RPO_LADDER: {
        if (f + 2 >= n) return -1;
        if (p->direct_gap && table[f].pts - table[f + 1].pts >= p->direct_gap) return f;
        const int w = rtie(&r, table, c, p, f + 1, f + 2, p->gap_skip, 0, sp);
        return rtie(&r, table, c, p, f, w, p->gap_final, p->final_neutral, sp);
    }
    }
    return -1;
}

/* a national tie of `legs` legs (x at home first): 1 x goes through, 0 y */
static int ntie(rng *r, const sr_lp_club *x, const sr_lp_club *y, int legs, int sp)
{
    int gx = 0, gy = 0;
    for (int k = 0; k < legs; k++) {
        int a, b;
        if (k % 2 == 0) { goals(r, str2(x->strength, 1, sp), str2(y->strength, 0, sp), &a, &b); gx += a; gy += b; }
        else { goals(r, str2(y->strength, 1, sp), str2(x->strength, 0, sp), &a, &b); gy += a; gx += b; }
    }
    if (gx != gy) return gx > gy;
    const u32 p = str2(x->strength, 0, sp), q = str2(y->strength, 0, sp), sa = 2 * p + q, sb = p + 2 * q;
    return below(r, sa + sb) < sa;                  /* extra time, penalties: near a coin toss */
}

static void shuffle(rng *r, int32_t *v, int n)
{
    for (int i = n - 1; i > 0; i--) { const int j = (int)below(r, (u32)i + 1); const int32_t t = v[i]; v[i] = v[j]; v[j] = t; }
}

int32_t sr_lp_cross_sp(uint32_t seed, const sr_lp_club *e, int32_t ne, const uint8_t *urn, int32_t nu,
                       const uint8_t (*pair)[2], int32_t np, int32_t legs1, int32_t legs2, int32_t *up, int32_t sp)
{
    int32_t box[SR_LP_DIVS][SR_LP_DIVS], cnt[SR_LP_DIVS] = { 0 }, nup = 0;
    if (!e || !urn || !pair || !up || ne < 2 || ne > SR_LP_DIVS || nu < 1 || nu > SR_LP_DIVS || np < 1
        || legs1 < 1 || legs1 > 2 || legs2 < 1 || legs2 > 2) return -1;
    for (int i = 0; i < ne; i++) { if (urn[i] >= nu) return -1; box[urn[i]][cnt[urn[i]]++] = i; }
    rng r = { mix(seed, 0x4E504Fu) };
    for (int u = 0; u < nu; u++) {                  /* round 1: each urn drawn in pairs */
        if (cnt[u] % 2) return -1;
        shuffle(&r, box[u], cnt[u]);
        int w = 0;
        for (int k = 0; k + 1 < cnt[u]; k += 2)
            box[u][w++] = ntie(&r, &e[box[u][k]], &e[box[u][k + 1]], legs1, sp) ? box[u][k] : box[u][k + 1];
        cnt[u] = w;
        shuffle(&r, box[u], cnt[u]);
    }
    for (int k = 0; k < np; k++) {                  /* round 2: by the pair kinds, in order */
        const int u = pair[k][0], v = pair[k][1];
        if (u >= nu || v >= nu) return -1;
        while (u == v ? cnt[u] >= 2 : cnt[u] >= 1 && cnt[v] >= 1) {
            const int32_t a = box[u][--cnt[u]], b = box[v][--cnt[v]];
            up[nup++] = ntie(&r, &e[a], &e[b], legs2, sp) ? a : b;
        }
    }
    for (int u = 0; u < nu; u++) if (cnt[u]) return -1;
    return nup;
}

int32_t sr_lp_extra(int32_t nd, const sr_lp_club *const *c, const int32_t *n, const uint8_t *const *place,
                    const uint8_t *const *isup, uint16_t override, int32_t *od, int32_t *oi, int32_t *ov)
{
    int bd = -1, bi = -1;
    if (!c || !n || !place || !isup || !od || !oi || !ov || nd < 1 || nd > SR_LP_DIVS) return -1;
    for (int d = 0; d < nd; d++)
        for (int i = 0; i < n[d]; i++) {
            if (isup[d][i]) continue;
            if (override != SR_LP_NONE && c[d][i].ident == override) { *od = d; *oi = i; *ov = 1; return 0; }
            if (bd < 0) { bd = d; bi = i; continue; }
            const sr_lp_club *x = &c[d][i], *y = &c[bd][bi];
            if (x->strength != y->strength ? x->strength > y->strength
                : place[d][i] != place[bd][bi] ? place[d][i] < place[bd][bi] : x->ident < y->ident) { bd = d; bi = i; }
        }
    if (bd < 0) return -1;
    *od = bd; *oi = bi; *ov = 0;
    return 0;
}

int32_t sr_lp_season_cross(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n,
                        const sr_lp_shape *s, sr_lp_up *up)
{
    sr_row t[SR_LP_CLUBS];
    uint8_t place[SR_LP_DIVS][SR_LP_CLUBS], isup[SR_LP_DIVS][SR_LP_CLUBS];
    const uint8_t *pl[SR_LP_DIVS], *iu[SR_LP_DIVS];
    sr_lp_club e[SR_LP_DIVS];
    int32_t ei[SR_LP_DIVS], w[SR_LP_DIVS];
    int nup = 0;
    const int sp = s && s->spread >= 0 ? s->spread : SR_LP_SPREAD;
    if (!c || !n || !s || !s->rpo || !s->urn || !up || nd < 1 || nd > SR_LP_DIVS || s->extra < 0 || s->nov < 0
        || (s->nov && !s->override)) return -1;
    if (s->nbarred < 0 || (s->nbarred && !s->barred)) return -1;
    for (int d = 0; d < nd; d++) {
        int nt = 0;
        if (n[d] < 2 || sr_lp_table_sp(seed, d, c[d], n[d], t, sp) != 0) return -1;
        for (int k = 0; k < n[d]; k++) { place[d][t[k].team] = (uint8_t)k; isup[d][k] = 0; }
        for (int k = 0; k < n[d]; k++) {        /* (the barred clubs out of the table: the next ones move up a place) */
            int b = 0;
            for (int j = 0; j < s->nbarred && !b; j++) b = s->barred[j] == c[d][t[k].team].ident;
            if (b) isup[d][t[k].team] = 1;      /* (and never taken by the extra rule) */
            else t[nt++] = t[k];
        }
        if (nt < 2) return -1;
        const int p = sr_lp_regional_sp(seed, d, t, nt, c[d], &s->rpo[d], sp);
        if (p < 0) return -1;
        up[nup++] = (sr_lp_up){ (int16_t)d, (int16_t)t[0].team, SR_LP_UP_CHAMPION };
        isup[d][t[0].team] = 1;
        e[d] = c[d][t[p].team]; ei[d] = t[p].team;
        pl[d] = place[d]; iu[d] = isup[d];
    }
    const int nw = sr_lp_cross_sp(seed, e, nd, s->urn, s->nu, s->pair, s->np, s->legs1, s->legs2, w, sp);
    if (nw < 0) return -1;
    for (int k = 0; k < nw; k++) {
        up[nup++] = (sr_lp_up){ (int16_t)w[k], (int16_t)ei[w[k]], SR_LP_UP_CROSS };
        isup[w[k]][ei[w[k]]] = 1;
    }
    int placed = 0;
    for (int k = 0; k < s->nov && placed < s->extra; k++) {      /* the override clubs first */
        int32_t od, oi, ov;
        if (sr_lp_extra(nd, c, n, pl, iu, s->override[k], &od, &oi, &ov) != 0) return -1;
        if (!ov) continue;
        up[nup++] = (sr_lp_up){ (int16_t)od, (int16_t)oi, SR_LP_UP_OVERRIDE };
        isup[od][oi] = 1; placed++;
    }
    for (; placed < s->extra; placed++) {                         /* then the rule */
        int32_t od, oi, ov;
        if (sr_lp_extra(nd, c, n, pl, iu, SR_LP_NONE, &od, &oi, &ov) != 0) return -1;
        up[nup++] = (sr_lp_up){ (int16_t)od, (int16_t)oi, SR_LP_UP_EXTRA };
        isup[od][oi] = 1;
    }
    return nup;
}

/* the compiled default spread (SR_LP_SPREAD) */
int32_t sr_lp_table(uint32_t seed, int32_t d, const sr_lp_club *c, int32_t n, sr_row *out)
{
    return sr_lp_table_sp(seed, d, c, n, out, SR_LP_SPREAD);
}

int32_t sr_lp_playoff(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c)
{
    return sr_lp_playoff_sp(seed, d, table, n, c, SR_LP_SPREAD);
}

int32_t sr_lp_season(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n, int32_t *up)
{
    return sr_lp_season_sp(seed, nd, c, n, up, SR_LP_SPREAD);
}

int32_t sr_lp_regional(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c, const sr_lp_rpo *p)
{
    return sr_lp_regional_sp(seed, d, table, n, c, p, SR_LP_SPREAD);
}

int32_t sr_lp_cross(uint32_t seed, const sr_lp_club *e, int32_t ne, const uint8_t *urn, int32_t nu,
                    const uint8_t (*pair)[2], int32_t np, int32_t legs1, int32_t legs2, int32_t *up)
{
    return sr_lp_cross_sp(seed, e, ne, urn, nu, pair, np, legs1, legs2, up, SR_LP_SPREAD);
}

/* the value at position x / 1000 of a list sorted strongest first (0 .. n - 1, linear between neighbours) */
static int at_pos(const uint16_t *v, int n, int x)
{
    const int i = x / 1000 < n - 1 ? x / 1000 : n - 2, f = x - i * 1000;
    return v[i] + ((int)v[i + 1] - (int)v[i]) * f / 1000;
}

int32_t sr_lp_rank_strength(uint16_t own, const uint16_t *above, int32_t na, const uint16_t *pool, int32_t np)
{
    int p;                                      /* (own's position in `above`, 0 .. 1000) */
    if (!above || !pool || na < 2 || np < 2) return -1;
    if (own >= above[0]) p = 0;
    else if (own <= above[na - 1]) p = 1000;
    else {
        int i = 0;
        while (i < na - 2 && !(above[i] >= own && own >= above[i + 1])) i++;
        const int d = above[i] - above[i + 1];
        p = (i * 1000 + (d ? (above[i] - own) * 1000 / d : 0)) / (na - 1);
    }
    return at_pos(pool, np, p * (np - 1));
}

int32_t sr_lp_newcomer_strength(uint16_t own, const uint16_t *pool, int32_t np)
{
    if (!pool || np < 1) return -1;
    int top = 0;
    for (int i = 0; i < np; i++) if (pool[i] > top) top = pool[i];
    return own < top ? own : top;
}
