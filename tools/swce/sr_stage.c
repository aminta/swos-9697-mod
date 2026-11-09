/*
 * sr_stage.c -- the generic stages of a spec's competitions (swc/1.2), as the competition editor writes
 * them: a round robin's calendar, a table ranked by the spec's tie-breakers, a knockout's round sizes and
 * one tie decided by the spec's deciders, a groups stage's group sizes. Nothing in either game plays them
 * yet (they are the new engine's first pieces); the codes are swcc's (SR_TB_* / SR_D_*).
 *
 * Every draw comes from a hash of the seed and the club (or the tie), never a running generator: the same
 * clubs give the same answer whatever the order they come in.
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t  i32;
typedef int8_t   i8;

enum { N = SR_STAGE_CLUBS };

static u32 mix(u32 h, u32 v)
{
    h ^= v + 0x9E3779B9u + (h << 6) + (h >> 2);
    h ^= h >> 16; h *= 0x7FEB352Du;
    h ^= h >> 15; h *= 0x846CA68Bu;
    return h ^ (h >> 16);
}

/* ---- the round robin's calendar ---- */

/* One leg by the circle method over m = n or n + 1 slots (slot m - 1 fixed, the others turning; with n odd
 * the slot n is the rest). The fixed slot's match swaps home every matchday; the others take the home side
 * by their place on the circle, which keeps each club's home matches within one of each other. */
static i32 leg(i32 n, i32 md0, int swap, sr_match *out)
{
    const i32 m = n + (n & 1);
    i32 k = 0;
    for (i32 r = 0; r < m - 1; r++) {
        for (i32 i = 0; i < m / 2; i++) {
            const i32 a = i == 0 ? m - 1 : (r + i) % (m - 1), b = (r + m - 1 - i) % (m - 1);
            if (a >= n || b >= n) continue;                     /* the rest */
            int a_home = i == 0 ? (r & 1) : (i & 1);
            if (swap) a_home = !a_home;
            out[k].md = (u8)(md0 + r);
            out[k].home = (u8)(a_home ? a : b);
            out[k].away = (u8)(a_home ? b : a);
            out[k].played = out[k].hg = out[k].ag = 0;
            k++;
        }
    }
    return k;
}

i32 sr_rr_calendar(i32 n, i32 legs, sr_match *out, i32 room)
{
    if (n < 2 || n > N || legs < 1 || legs > 4) return -1;
    const i32 per = n * (n - 1) / 2, mds = n - 1 + (n & 1);
    if (room < legs * per) return -1;
    i32 k = 0;
    for (i32 l = 0; l < legs; l++) k += leg(n, l * mds, l & 1, out + k);
    return k;
}

/* ---- the table ---- */

static int usable(u8 c)
{
    return (c >= SR_TB_H2H_REAPPLIED && c <= SR_TB_H2H_TABLE_ONCE) || (c >= SR_TB_POINTS && c <= SR_TB_NAME && c != SR_TB_FAIR_PLAY &&
                                        c != SR_TB_COEFFICIENT && c != SR_TB_PREVIOUS_STAGE_RANK && c != SR_TB_PLAY_OFF_MATCH);
}

typedef struct { const sr_srow *row; const sr_match *m; i32 nm, n, win, draw, loss; u32 seed;
                 const u8 *pairs, *namek; } sr_tctx;    /* (pairs: sr_league_rank's results, n x n; namek: the names' order) */

/* the key of club c under criterion t (higher is better); the head-to-head ones over the clubs in `in` */
static i32 key(const sr_tctx *x, u8 t, i32 c, const u8 *in)
{
    const sr_srow *r = &x->row[c];
    const sr_match *m = x->m;
    const i32 nm = x->nm, win = x->win, draw = x->draw, loss = x->loss;
    const u32 seed = x->seed;
    switch (t) {
    case SR_TB_POINTS:          return r->pts;
    case SR_TB_GOAL_DIFFERENCE: return (i32)r->gf - (i32)r->ga;
    case SR_TB_GOALS_FOR:       return r->gf;
    case SR_TB_GOALS_AGAINST:   return -(i32)r->ga;
    case SR_TB_WINS:            return r->w;
    case SR_TB_AWAY_WINS:       return r->aw;
    case SR_TB_AWAY_GOALS_FOR:  return r->agf;
    case SR_TB_DRAW_LOTS:       return (i32)(mix(seed, 0x51A6E000u + (u32)c) >> 1);
    case SR_TB_NAME:            return x->namek ? -(i32)x->namek[c] : -c;
    case SR_TB_LOSSES_FEWER:    return -(i32)r->l;
    case SR_TB_HOME_LOSSES_FEWER: {                             /* over the whole season, not the tied clubs */
        i32 hl = 0;
        if (x->pairs)
            for (i32 j = 0; j < x->n; j++) {
                const u8 v = j == c ? SR_PAIR_NONE : x->pairs[c * x->n + j];
                if (v != SR_PAIR_NONE && (v >> 4) < (v & 15)) hl++;
            }
        for (i32 k = 0; k < nm; k++) if (m[k].played && m[k].home == c && m[k].hg < m[k].ag) hl++;
        return -hl;
    }
    default: break;
    }
    i32 pts = 0, gd = 0, gf = 0, ag = 0;                        /* head to head */
    if (x->pairs)                                               /* (sr_league_rank: the results block) */
        for (i32 j = 0; j < x->n; j++) {
            if (j == c || !in[j]) continue;
            for (int home = 1; home >= 0; home--) {
                const u8 v = home ? x->pairs[c * x->n + j] : x->pairs[j * x->n + c];
                if (v == SR_PAIR_NONE) continue;
                const i32 hg = v >> 4, ag2 = v & 15, f = home ? hg : ag2, a = home ? ag2 : hg;
                pts += f > a ? win : f == a ? draw : loss;
                gd += f - a; gf += f;
                if (!home) ag += f;
            }
        }
    for (i32 k = 0; k < nm; k++) {
        const sr_match *x = &m[k];
        if (!x->played || !in[x->home] || !in[x->away] || (x->home != c && x->away != c)) continue;
        const int home = x->home == c;
        const i32 f = home ? x->hg : x->ag, a = home ? x->ag : x->hg;
        pts += f > a ? win : f == a ? draw : loss;
        gd += f - a; gf += f;
        if (!home) ag += f;
    }
    return t == SR_TB_H2H_POINTS ? pts : t == SR_TB_H2H_GOAL_DIFFERENCE ? gd : t == SR_TB_H2H_GOALS_FOR ? gf : ag;
}

static void block_in(i32 n, const u8 *ord, i32 b, i32 e, u8 *in)
{
    for (i32 k = 0; k < n; k++) in[k] = 0;
    for (i32 k = b; k < e; k++) in[ord[k]] = 1;
}

/* criterion t inside ord[b..e) (one tied block): a stable sort, best first, then a cut between unequal keys */
static void split(const sr_tctx *x, u8 t, const u8 *in, u8 *ord, u8 *cut, i32 b, i32 e)
{
    i32 kv[N];
    for (i32 k = b; k < e; k++) kv[ord[k]] = key(x, t, ord[k], in);
    for (i32 k = b + 1; k < e; k++) {
        const u8 c = ord[k];
        i32 j = k;
        while (j > b && kv[ord[j - 1]] < kv[c]) { ord[j] = ord[j - 1]; j--; }
        ord[j] = c;
    }
    for (i32 k = b + 1; k < e; k++) if (kv[ord[k]] != kv[ord[k - 1]]) cut[k] = 1;
}

/* head_to_head_reapplied (UEFA): head-to-head points, goal difference, goals for among the tied clubs; a smaller
 * block still tied after them takes the three again over its own matches only, until nothing splits */
static void reapply(const sr_tctx *x, u8 *ord, u8 *cut, i32 b, i32 e)
{
    u8 in[N];
    block_in(x->n, ord, b, e, in);
    for (u8 t = SR_TB_H2H_POINTS; t <= SR_TB_H2H_GOALS_FOR; t++)
        for (i32 s = b; s < e;) {
            i32 f = s + 1;
            while (f < e && !cut[f]) f++;
            if (f - s > 1) split(x, t, in, ord, cut, s, f);
            s = f;
        }
    for (i32 s = b; s < e;) {
        i32 f = s + 1;
        while (f < e && !cut[f]) f++;
        if (f - s > 1 && f - s < e - b) reapply(x, ord, cut, s, f);
        s = f;
    }
}

/* avulsa (FIGC, NOIF art. 51 / 49 X): head-to-head points, then head-to-head goal difference, BOTH over the matches
 * among all the clubs of the block (the clubs level when it starts), once; the smaller blocks it leaves stay tied.
 * head_to_head_table_once (EFL reg. 9.2, last = h2h goals for): the same mini-table with goals for as a third key */
static void avulsa(const sr_tctx *x, u8 *ord, u8 *cut, i32 b, i32 e, u8 last)
{
    u8 in[N];
    block_in(x->n, ord, b, e, in);
    for (u8 t = SR_TB_H2H_POINTS; t <= last; t++)
        for (i32 s = b; s < e;) {
            i32 f = s + 1;
            while (f < e && !cut[f]) f++;
            if (f - s > 1) split(x, t, in, ord, cut, s, f);
            s = f;
        }
}

/* each criterion once, in order, inside the blocks the ones before left tied (a stable sort there);
 * faithful_1996 = points, goal difference, goals for, name (the 1996 game's cseg_883DD) */
static void crit(const sr_tctx *x, u8 t, u8 *ord, u8 *cut)
{
    for (i32 b = 0; b < x->n;) {
        i32 e = b + 1;
        while (!cut[e]) e++;
        if (e - b > 1) {
            if (t == SR_TB_H2H_REAPPLIED) reapply(x, ord, cut, b, e);
            else if (t == SR_TB_AVULSA) avulsa(x, ord, cut, b, e, SR_TB_H2H_GOAL_DIFFERENCE);
            else if (t == SR_TB_H2H_TABLE_ONCE) avulsa(x, ord, cut, b, e, SR_TB_H2H_GOALS_FOR);
            else {
                u8 in[N];
                block_in(x->n, ord, b, e, in);
                split(x, t, in, ord, cut, b, e);
            }
        }
        b = e;
    }
}
static void rank(const sr_tctx *x, const u8 *tieb, u8 *ord)
{
    static const u8 F96[] = { SR_TB_POINTS, SR_TB_GOAL_DIFFERENCE, SR_TB_GOALS_FOR, SR_TB_NAME, 0 };
    u8 cut[N + 1];                                              /* cut[k]: a block starts at k */
    for (i32 k = 0; k < x->n; k++) { ord[k] = (u8)k; cut[k] = k == 0; }
    cut[x->n] = 1;
    for (const u8 *t = tieb; t && *t; t++)
        if (*t == SR_TB_FAITHFUL_1996) for (const u8 *f = F96; *f; f++) crit(x, *f, ord, cut);
        else crit(x, *t, ord, cut);
}

i32 sr_league_rank(i32 n, const sr_srow *row, const u8 *pairs, const u8 *namek, i32 win, i32 draw, i32 loss,
                   const u8 *tieb, u32 seed, u8 *ord)
{
    if (n < 1 || n > N) return -1;
    for (const u8 *t = tieb; t && *t; t++) if (!usable(*t) && *t != SR_TB_FAITHFUL_1996) return -1;
    u8 tl[24];                                                  /* (no results: the head-to-head criteria left out) */
    i32 k = 0;
    for (const u8 *t = tieb; t && *t && k < 23; t++)
        if (pairs || !((*t >= SR_TB_H2H_POINTS && *t <= SR_TB_H2H_AWAY_GOALS) || *t == SR_TB_H2H_REAPPLIED ||
                       *t == SR_TB_AVULSA || *t == SR_TB_HOME_LOSSES_FEWER || *t == SR_TB_H2H_TABLE_ONCE)) tl[k++] = *t;
    tl[k] = 0;
    const sr_tctx x = { row, 0, 0, n, win, draw, loss, seed, pairs, namek };
    rank(&x, tl, ord);
    return n;
}

i32 sr_rr_table(i32 n, const sr_match *m, i32 nm, i32 win, i32 draw, i32 loss, const u8 *tieb, u32 seed,
                sr_srow *out)
{
    if (n < 1 || n > N) return -1;
    for (const u8 *t = tieb; t && *t; t++) if (!usable(*t)) return -1;
    sr_srow row[N];
    for (i32 c = 0; c < n; c++) {
        row[c].club = (u8)c; row[c].pad = 0; row[c].pts = 0;
        row[c].pl = row[c].w = row[c].d = row[c].l = row[c].gf = row[c].ga = row[c].aw = row[c].agf = 0;
    }
    for (i32 k = 0; k < nm; k++) {
        const sr_match *x = &m[k];
        if (x->home >= n || x->away >= n || x->home == x->away) return -1;
        if (!x->played) continue;
        sr_srow *h = &row[x->home], *a = &row[x->away];
        h->pl++; a->pl++;
        h->gf = (u16)(h->gf + x->hg); h->ga = (u16)(h->ga + x->ag);
        a->gf = (u16)(a->gf + x->ag); a->ga = (u16)(a->ga + x->hg);
        a->agf = (u16)(a->agf + x->ag);
        if (x->hg > x->ag)      { h->w++; a->l++; h->pts = (int16_t)(h->pts + win); a->pts = (int16_t)(a->pts + loss); }
        else if (x->hg < x->ag) { a->w++; a->aw++; h->l++; a->pts = (int16_t)(a->pts + win); h->pts = (int16_t)(h->pts + loss); }
        else                    { h->d++; a->d++; h->pts = (int16_t)(h->pts + draw); a->pts = (int16_t)(a->pts + draw); }
    }
    u8 ord[N];
    const sr_tctx x = { row, m, nm, n, win, draw, loss, seed, 0, 0 };
    rank(&x, tieb, ord);
    for (i32 k = 0; k < n; k++) {                               /* (field by field: a struct copy is a memcpy call) */
        const sr_srow *r = &row[ord[k]];
        sr_srow *o = &out[k];
        o->club = r->club; o->pad = 0; o->pts = r->pts; o->pl = r->pl; o->w = r->w; o->d = r->d; o->l = r->l;
        o->gf = r->gf; o->ga = r->ga; o->aw = r->aw; o->agf = r->agf;
    }
    return n;
}

/* ---- knockouts ---- */

i32 sr_ko_left(i32 entrants, const sr_round_size *r, i32 nr)
{
    i32 left = entrants;
    for (i32 k = 0; k < nr; k++) {
        if (2 * (i32)r[k].ties + (i32)r[k].byes != left) return -(k + 1);
        left = r[k].ties + r[k].byes;
    }
    return left;
}

i32 sr_ko_tie(const sr_leg *leg_, i32 nlegs, const sr_tie_extra *x, const u8 *deci, u32 seed)
{
    i32 tot[2] = { 0, 0 }, away[2] = { 0, 0 };
    for (i32 k = 0; k < nlegs; k++) {
        tot[0] += leg_[k].g[0]; tot[1] += leg_[k].g[1];
        if (leg_[k].home < 2) away[!leg_[k].home] += leg_[k].g[!leg_[k].home];
    }
    if (tot[0] != tot[1]) return tot[1] > tot[0];
    for (const u8 *d = deci; d && *d; d++) {
        switch (*d) {
        case SR_D_AGGREGATE: break;                             /* (level already) */
        case SR_D_AWAY_GOALS:
            if (away[0] != away[1]) return away[1] > away[0];
            break;
        case SR_D_EXTRA_TIME: case SR_D_GOLDEN_GOAL:
            if (!x || !x->et_played) return SR_TIE_OPEN;
            tot[0] += x->et[0]; tot[1] += x->et[1];
            if (nlegs && leg_[nlegs - 1].home < 2) {            /* extra time's away goals: the last leg's visitors' */
                const i32 v = !leg_[nlegs - 1].home;
                away[v] += x->et[v];
            }
            if (tot[0] != tot[1]) return tot[1] > tot[0];
            break;
        case SR_D_PENALTIES:
            if (!x || !x->pens_played || x->pens[0] == x->pens[1]) return SR_TIE_OPEN;
            return x->pens[1] > x->pens[0];
        case SR_D_BETTER_PLACED:
            if (x && x->place[0] != x->place[1]) return x->place[1] < x->place[0];
            break;
        case SR_D_REPLAY: return SR_TIE_REPLAY;
        case SR_D_DRAW_LOTS: return (i32)(mix(seed, 0x7E1Eu) & 1);
        default: return SR_TIE_OPEN;
        }
    }
    return SR_TIE_OPEN;
}

/* ---- groups ---- */

i32 sr_group_sizes(i32 n, i32 g, u8 *size)
{
    if (g < 1 || n / g < 2 || (n + g - 1) / g > 255) return -1;
    for (i32 k = 0; k < g; k++) size[k] = (u8)(n / g + (k < n % g));
    return g;
}

/* ---- draws ---- */

enum { BUDGET = 200000 };                                       /* search steps before a draw gives up */

/* ord = 0..n-1 by the hash of the seed, the salt and the club */
static void hash_order(u32 seed, u32 salt, i32 n, u8 *ord)
{
    u32 h[N];
    for (i32 k = 0; k < n; k++) {
        const u32 v = mix(seed, salt + (u32)k);
        i32 j = k;
        while (j > 0 && h[j - 1] > v) { h[j] = h[j - 1]; ord[j] = ord[j - 1]; j--; }
        h[j] = v; ord[j] = (u8)k;
    }
}

typedef struct {
    i32 n, g; const u8 *assoc; u32 seed; const u8 *size;
    u8 club[N], cnt[N];                                         /* the draw's order; clubs in each group */
    u32 has[N][8];                                              /* the associations in each group (bits) */
    u8 left[256], with[256];                                    /* an association's clubs still to draw; groups with it */
    i32 steps;
} sr_gdraw;

static u8 assoc_of(const sr_gdraw *d, i32 c) { return d->assoc ? d->assoc[c] : 0; }

static int gfree(const sr_gdraw *d, i32 j, i32 c, i32 p)       /* group j open to club c of pot p */
{
    const u8 a = assoc_of(d, c);
    return d->size[j] > p && d->cnt[j] <= p && !(d->assoc && (d->has[j][a >> 5] >> (a & 31) & 1));
}

/* Kuhn's augmenting path: pot club q (of the list) to a group, moving the ones placed before it */
static int augment(const sr_gdraw *d, const u8 *list, i32 q, i32 p, i8 *owner, u8 *seen)
{
    for (i32 j = 0; j < d->g; j++) {
        if (seen[j] || !gfree(d, j, list[q], p)) continue;
        seen[j] = 1;
        if (owner[j] < 0 || augment(d, list, owner[j], p, owner, seen)) { owner[j] = (i8)q; return 1; }
    }
    return 0;
}

/* still possible after club i: every pot's clubs not yet drawn can each take a group of their own (a matching),
 * and no association has more clubs left than groups without it */
static int gdraw_open(const sr_gdraw *d, i32 i)
{
    if (d->assoc)
        for (i32 a = 0; a < 256; a++) if (d->left[a] > d->g - d->with[a]) return 0;
    for (i32 p = i / d->g; p * d->g < d->n; p++) {
        const i32 b = p * d->g > i + 1 ? p * d->g : i + 1, end = (p + 1) * d->g < d->n ? (p + 1) * d->g : d->n;
        if (b >= end) continue;
        u8 list[N];
        i32 nl = 0;
        for (i32 k = b; k < end; k++) list[nl++] = d->club[k];
        i8 owner[N];
        for (i32 j = 0; j < d->g; j++) owner[j] = -1;
        for (i32 q = 0; q < nl; q++) {
            u8 seen[N];
            for (i32 j = 0; j < d->g; j++) seen[j] = 0;
            if (!augment(d, list, q, p, owner, seen)) return 0;
        }
    }
    return 1;
}

/* club i of the draw's order (pot p = i / g) into a group, the rest after it */
static int gdraw(sr_gdraw *d, u8 *grp, i32 i)
{
    if (i == d->n) return 1;
    if (--d->steps < 0) return 0;
    const i32 c = d->club[i], p = i / d->g;
    const u8 a = assoc_of(d, c);
    u8 go[N];
    hash_order(d->seed, 0x6D000000u + (u32)c * 64u, d->g, go);
    for (i32 k = 0; k < d->g; k++) {
        const i32 j = go[k];
        if (d->cnt[j] != p || d->size[j] <= p) continue;        /* this pot's club there already, or the group full */
        if (d->assoc && (d->has[j][a >> 5] >> (a & 31) & 1)) continue;
        grp[c] = (u8)j; d->cnt[j]++;
        if (d->assoc) { d->has[j][a >> 5] |= 1u << (a & 31); d->left[a]--; d->with[a]++; }
        if (gdraw_open(d, i) && gdraw(d, grp, i + 1)) return 1;
        if (d->assoc) { d->has[j][a >> 5] &= ~(1u << (a & 31)); d->left[a]++; d->with[a]--; }
        d->cnt[j]--;
    }
    return 0;
}

i32 sr_group_draw(i32 n, i32 g, const u8 *assoc, u32 seed, u8 *grp)
{
    u8 size[N];
    if (n > N || sr_group_sizes(n, g, size) < 0) return -1;
    sr_gdraw d;
    d.n = n; d.g = g; d.assoc = assoc; d.seed = seed; d.size = size; d.steps = BUDGET;
    for (i32 j = 0; j < g; j++) { d.cnt[j] = 0; for (i32 w = 0; w < 8; w++) d.has[j][w] = 0; }
    for (i32 a = 0; a < 256; a++) d.left[a] = d.with[a] = 0;
    for (i32 c = 0; assoc && c < n; c++) d.left[assoc[c]]++;
    for (i32 p = 0; p * g < n; p++) {                           /* pot by pot, each pot in hashed order */
        const i32 b = p * g, len = n - b < g ? n - b : g;
        u8 o[N];
        hash_order(seed, 0x90700000u + (u32)p * 64u, len, o);
        for (i32 k = 0; k < len; k++) d.club[b + k] = (u8)(b + o[k]);
    }
    return gdraw(&d, grp, 0) ? g : -2;
}

i32 sr_best_placed(const sr_group *g, i32 ng, i32 place, i32 win, i32 draw, i32 loss, const u8 *tieb, u32 seed,
                   u8 *ord)
{
    for (const u8 *t = tieb; t && *t; t++)
        if (!usable(*t) || (*t >= SR_TB_H2H_POINTS && *t <= SR_TB_H2H_AWAY_GOALS) || *t == SR_TB_H2H_REAPPLIED ||
            *t == SR_TB_AVULSA || *t == SR_TB_H2H_TABLE_ONCE) return -1;
    if (ng < 1 || ng > N) return -1;
    i32 least = g[0].n;
    for (i32 j = 1; j < ng; j++) if (g[j].n < least) least = g[j].n;
    sr_srow row[N];
    u8 gi[N];
    i32 e = 0;
    for (i32 j = 0; j < ng; j++) {
        if (place >= g[j].n) continue;
        u8 pos[N];
        for (i32 k = 0; k < g[j].n; k++) pos[g[j].table[k].club] = (u8)k;
        const i32 c = g[j].table[place].club;
        sr_srow *r = &row[e];
        r->club = (u8)e; r->pad = 0; r->pts = 0;
        r->pl = r->w = r->d = r->l = r->gf = r->ga = r->aw = r->agf = 0;
        for (i32 k = 0; k < g[j].nm; k++) {
            const sr_match *x = &g[j].m[k];
            if (!x->played || (x->home != c && x->away != c)) continue;
            const i32 o = x->home == c ? x->away : x->home;
            if (pos[o] >= least) continue;                      /* against the extra clubs of a larger group */
            const int home = x->home == c;
            const i32 f = home ? x->hg : x->ag, a = home ? x->ag : x->hg;
            r->pl++; r->gf = (u16)(r->gf + f); r->ga = (u16)(r->ga + a);
            if (!home) r->agf = (u16)(r->agf + f);
            if (f > a)       { r->w++; if (!home) r->aw++; r->pts = (int16_t)(r->pts + win); }
            else if (f == a) { r->d++; r->pts = (int16_t)(r->pts + draw); }
            else             { r->l++; r->pts = (int16_t)(r->pts + loss); }
        }
        gi[e++] = (u8)j;
    }
    u8 o[N], cut[N + 1], in[N];
    for (i32 k = 0; k < e; k++) { o[k] = (u8)k; cut[k] = k == 0; in[k] = 1; }
    cut[e] = 1;
    const sr_tctx x = { row, 0, 0, e, win, draw, loss, seed, 0, 0 };
    for (const u8 *t = tieb; t && *t; t++)
        for (i32 b = 0; b < e;) {
            i32 f = b + 1;
            while (!cut[f]) f++;
            if (f - b > 1) split(&x, *t, in, o, cut, b, f);
            b = f;
        }
    for (i32 k = 0; k < e; k++) ord[k] = gi[o[k]];
    return e;
}

typedef struct { i32 mode, n; const u8 *avoid; u32 seed; u8 order[N]; u8 used[N]; i32 steps; } sr_pdraw;

/* pair d of the round: the first club of the hashed order still free (the top half's, seeded) v a free club
 * the round can still be finished with */
static int pdraw(sr_pdraw *d, u8 *out, i32 k)
{
    if (2 * k == d->n) return 1;
    if (--d->steps < 0) return 0;
    const i32 half = d->mode == SR_PAIR_SEEDED ? d->n / 2 : d->n;
    i32 a = -1;
    for (i32 q = 0; q < d->n && a < 0; q++) if (!d->used[d->order[q]] && d->order[q] < half) a = d->order[q];
    if (a < 0) return 0;
    d->used[a] = 1;
    u8 go[N];
    hash_order(d->seed, 0xBA000000u + (u32)a * 64u, d->n, go);
    for (i32 q = 0; q < d->n; q++) {
        const i32 b = go[q];
        if (d->used[b] || (d->mode == SR_PAIR_SEEDED && b < half) || (d->avoid && d->avoid[a] == d->avoid[b])) continue;
        d->used[b] = 1; out[2 * k] = (u8)a; out[2 * k + 1] = (u8)b;
        if (pdraw(d, out, k + 1)) return 1;
        d->used[b] = 0;
    }
    d->used[a] = 0;
    return 0;
}

i32 sr_ko_pairs(i32 mode, i32 n, const u8 *avoid, u32 seed, u8 *out)
{
    if (n < 2 || n > N || (n & 1)) return -1;
    if (mode == SR_PAIR_FIXED || mode == SR_PAIR_BRACKET) {
        if (mode == SR_PAIR_FIXED) for (i32 k = 0; k < n; k++) out[k] = (u8)k;
        else {
            if (n & (n - 1)) return -1;
            out[0] = 0;                                         /* order(2m) = x, 2m-1-x for each x of order(m) */
            for (i32 m = 1; m < n; m *= 2)
                for (i32 k = m - 1; k >= 0; k--) { const u8 v = out[k]; out[2 * k] = v; out[2 * k + 1] = (u8)(2 * m - 1 - v); }
        }
        for (i32 k = 0; avoid && k < n; k += 2) if (avoid[out[k]] == avoid[out[k + 1]]) return -3;
        return n / 2;
    }
    if (mode != SR_PAIR_DRAW && mode != SR_PAIR_SEEDED) return -1;
    sr_pdraw d;
    d.mode = mode; d.n = n; d.avoid = avoid; d.seed = seed; d.steps = BUDGET;
    for (i32 k = 0; k < n; k++) d.used[k] = 0;
    hash_order(seed, 0xD7000000u, n, d.order);
    return pdraw(&d, out, 0) ? n / 2 : -2;
}
