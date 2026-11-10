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
    return (c >= SR_TB_H2H_REAPPLIED && c <= SR_TB_AWAY_GOAL_DIFFERENCE) || (c >= SR_TB_POINTS && c <= SR_TB_NAME && c != SR_TB_FAIR_PLAY &&
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
    case SR_TB_AWAY_GOAL_DIFFERENCE: {                          /* over the whole season, as home_losses_fewer */
        i32 d = 0;
        if (x->pairs)
            for (i32 j = 0; j < x->n; j++) {
                const u8 v = j == c ? SR_PAIR_NONE : x->pairs[j * x->n + c];
                if (v != SR_PAIR_NONE) d += (v & 15) - (v >> 4);
            }
        for (i32 k = 0; k < nm; k++) if (m[k].played && m[k].away == c) d += m[k].ag - m[k].hg;
        return d;
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
static void crit(const sr_tctx *x, u8 t, u8 *ord, u8 *cut, int only2)
{
    for (i32 b = 0; b < x->n;) {
        i32 e = b + 1;
        while (!cut[e]) e++;
        if (e - b > 1 && (!only2 || e - b == 2)) {
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
    int only2 = 0;                                              /* (only_if_two_level: for the next criterion) */
    for (const u8 *t = tieb; t && *t; t++)
        if (*t == SR_TB_ONLY_IF_TWO) only2 = 1;
        else {
            if (*t == SR_TB_FAITHFUL_1996) for (const u8 *f = F96; *f; f++) crit(x, *f, ord, cut, only2);
            else crit(x, *t, ord, cut, only2);
            only2 = 0;
        }
}

i32 sr_league_rank(i32 n, const sr_srow *row, const u8 *pairs, const u8 *namek, i32 win, i32 draw, i32 loss,
                   const u8 *tieb, u32 seed, u8 *ord)
{
    if (n < 1 || n > N) return -1;
    for (const u8 *t = tieb; t && *t; t++) if (!usable(*t) && *t != SR_TB_FAITHFUL_1996) return -1;
    u8 tl[24];                                                  /* (no results: the head-to-head criteria left out) */
    i32 k = 0;
#define NEEDS_PAIRS(c) (((c) >= SR_TB_H2H_POINTS && (c) <= SR_TB_H2H_AWAY_GOALS) || (c) == SR_TB_H2H_REAPPLIED || \
                        (c) == SR_TB_AVULSA || (c) == SR_TB_HOME_LOSSES_FEWER || (c) == SR_TB_H2H_TABLE_ONCE || \
                        (c) == SR_TB_AWAY_GOAL_DIFFERENCE)
    for (const u8 *t = tieb; t && *t && k < 23; t++)
        if (*t == SR_TB_ONLY_IF_TWO && !pairs && t[1] && NEEDS_PAIRS(t[1])) t++;   /* (its criterion left out too) */
        else if (pairs || !NEEDS_PAIRS(*t)) tl[k++] = *t;
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

/* The groups draw as an edge colouring: each club an edge between its pot and its association, its group the colour --
 * one club of a pot per group, one club of an association per group; the last pot's colours the larger groups only.
 * A whole draw exists iff no association has more clubs than there are groups (Koenig: a bipartite multigraph of
 * degree <= g takes g colours; the short last pot padded with g - r dummy clubs of a dummy association, whose colours
 * are then named the smaller groups). gking builds one: the witness. A pick of the draw equal to the witness's group
 * needs no check; another first tries gkempe, the witness's two-group Kempe chain from the club flipped (a draw again,
 * no search: UEFA-like shapes need nothing more); failing that, gsolve, a complete search, says whether the picks so
 * far still leave a whole draw (and if so, which: the new witness). gsolve: done as soon as the witness's groups are
 * free for every club left; else the most constrained club (fewest groups) or slot (a pot's group with the fewest
 * clubs that can fill it) first, the witness's value first, Hall matchings where the last pick changed them, groups
 * whose state is the same tried once, a club's association once per slot. Its nodes have a budget for the whole draw:
 * a pick it cannot decide in time is passed over as one that leaves no draw, so the club goes to a later group of its
 * order -- at the latest the witness's. The draw always ends, in a bounded time. */
enum { GBUDGET = 100000, GBUDGET_P = 25000, GBUDGET_C = 40000 };   /* gsolve's nodes + matching steps in one draw
                                                                   (~200 i486 instructions a step: ~20 M); with
                                                                   protect pairs ~750 a step (T2 re-run): 25000;
                                                                   cap 2 ~400 a step (64 clubs): 40000 */

typedef struct {
    i32 n, g, np, steps, nprot, witok, cap;                     /* (witok 0: the witness not a draw yet -- a
                                                                   protect chain's first search; cap: an
                                                                   association's clubs per group, 1 or 2) */
    const u8 *assoc, *prot;                                     /* (prot: nprot pairs of assoc values never in one
                                                                   group -- swc/1.5's protect chains) */
    u8 club[N], pot[N], grp[N], wit[N];                         /* the draw's order; club c's pot; its group (FFh
                                                                   none); the witness */
    u32 slot[N];                                                /* per pot: the groups whose place of it is free */
    u32 used[256];                                              /* per association: the groups holding one of its */
    u32 blk[256];                                               /* (with protect pairs) per association: its
                                                                   used plus its partners', kept by gput / gtake;
                                                                   (cap 2, no pairs) the groups holding two */
} sr_gdraw;

static i32 bits(u32 m) { i32 k = 0; for (; m; m &= m - 1) k++; return k; }
static u32 gblk(const sr_gdraw *d, i32 c)                       /* the groups closed to club c: its association's,
                                                                   a protect partner's */
{
    if (!d->assoc) return 0;
    return d->nprot || d->cap > 1 ? d->blk[d->assoc[c]] : d->used[d->assoc[c]];
}
static void gfix(sr_gdraw *d, i32 a, i32 j)                     /* association a's blk, group j's bit, again */
{
    u32 m = d->used[a];
    for (i32 i = 0; i < d->nprot; i++)
        if (d->prot[2 * i] == a) m |= d->used[d->prot[2 * i + 1]];
        else if (d->prot[2 * i + 1] == a) m |= d->used[d->prot[2 * i]];
    d->blk[a] = (d->blk[a] & ~(1u << j)) | (m & 1u << j);
}
static __attribute__((noinline)) void gblks(sr_gdraw *d, i32 a, i32 j)   /* a's and its partners' after a change */
{
    gfix(d, a, j);
    for (i32 i = 0; i < d->nprot; i++)
        if (d->prot[2 * i] == a) gfix(d, d->prot[2 * i + 1], j);
        else if (d->prot[2 * i + 1] == a) gfix(d, d->prot[2 * i], j);
}
static u32 gdom(const sr_gdraw *d, i32 c)                       /* the groups club c can still go to */
{
    return d->slot[d->pot[c]] & ~gblk(d, c);
}
static void gput(sr_gdraw *d, i32 c, i32 j)
{
    d->grp[c] = (u8)j; d->slot[d->pot[c]] &= ~(1u << j);
    if (d->assoc && d->cap > 1 && d->used[d->assoc[c]] >> j & 1) { d->blk[d->assoc[c]] |= 1u << j; return; }
    if (d->assoc) d->used[d->assoc[c]] |= 1u << j;
    if (d->nprot) gblks(d, d->assoc[c], j);
}
static void gtake(sr_gdraw *d, i32 c, i32 j)
{
    d->grp[c] = 0xFF; d->slot[d->pot[c]] |= 1u << j;
    if (d->assoc && d->cap > 1 && d->blk[d->assoc[c]] >> j & 1) { d->blk[d->assoc[c]] &= ~(1u << j); return; }
    if (d->assoc) d->used[d->assoc[c]] &= ~(1u << j);
    if (d->nprot) gblks(d, d->assoc[c], j);
}

/* groups j and k interchangeable for what is left: the same free places in every pot, and every club still to draw
 * closed to both or to neither */
static int gsame(const sr_gdraw *d, i32 j, i32 k)
{
    for (i32 p = 0; p < d->np; p++) if ((d->slot[p] >> j & 1) != (d->slot[p] >> k & 1)) return 0;
    for (i32 c = 0; d->assoc && c < d->n; c++)
        if (d->grp[c] == 0xFF && ((gblk(d, c) >> j & 1) != (gblk(d, c) >> k & 1) ||
                                  (d->cap > 1 && (d->used[d->assoc[c]] >> j & 1) != (d->used[d->assoc[c]] >> k & 1)))) return 0;
    return 1;
}

/* clubs l[0..m-1] each to a group of its own among those they can go to (Kuhn's augmenting paths) */
static int gaug(sr_gdraw *d, const u8 *l, i32 i, u32 *seen, i8 *by)
{
    if (--d->steps < 0) return 1;                               /* (the budget: no pruning, gsolve stops) */
    const u32 m = gdom(d, l[i]) & ~*seen;
    for (i32 j = 0; j < d->g; j++) {
        if (!(m >> j & 1)) continue;
        *seen |= 1u << j;
        if (by[j] < 0 || gaug(d, l, by[j], seen, by)) { by[j] = (i8)i; return 1; }
    }
    return 0;
}
static int gmatch(sr_gdraw *d, const u8 *l, i32 m)
{
    i8 by[32];
    for (i32 j = 0; j < d->g; j++) by[j] = -1;
    for (i32 i = 0; i < m; i++) { u32 seen = 0; if (!gaug(d, l, i, &seen, by)) return 0; }
    return 1;
}
/* (cap 2) an association's clubs left l[0..m-1] into the groups' room for it: group j twice (j, j + g) while it holds
 * none of the association, once while it holds one */
static int gaug2(sr_gdraw *d, const u8 *l, i32 i, u32 *seen, i8 *by)   /* (seen[0]: the first places, [1] the
                                                                   second ones: no 64-bit shifts, no libcalls) */
{
    if (--d->steps < 0) return 1;
    const u32 m = gdom(d, l[i]), v0 = m & ~seen[0], v1 = m & ~d->used[d->assoc[l[i]]] & ~seen[1];
    for (i32 t = 0; t < 2 * d->g; t++) {
        const i32 j = t < d->g ? t : t - d->g, s = t >= d->g;
        if (!((s ? v1 : v0) >> j & 1)) continue;
        seen[s] |= 1u << j;
        if (by[t] < 0 || gaug2(d, l, by[t], seen, by)) { by[t] = (i8)i; return 1; }
    }
    return 0;
}
static int gmatch2(sr_gdraw *d, const u8 *l, i32 m)
{
    i8 by[64];
    for (i32 j = 0; j < 2 * d->g; j++) by[j] = -1;
    for (i32 i = 0; i < m; i++) { u32 seen[2] = { 0, 0 }; if (!gaug2(d, l, i, seen, by)) return 0; }
    return 1;
}
/* a pot's clubs left, and an association's, each to groups of their own: the draw's two Hall conditions -- checked
 * where club `last`, just placed, changed them (they held before: a draw existed): its pot and the pots of its
 * association's clubs, its association and the associations of its pot's clubs */
static __attribute__((noinline)) int ghall(sr_gdraw *d, i32 last)   /* (its arrays off gsolve's
                                                                   recursion: the DOS stack) */
{
    u8 l[N], mark[N];
    i32 m;
    const i32 lp = d->pot[last];
    for (i32 p = 0; p < d->np; p++) mark[p] = p == lp;
    for (i32 c = 0; d->assoc && c < d->n; c++)
        if (d->grp[c] == 0xFF && d->assoc[c] == d->assoc[last]) mark[d->pot[c]] = 1;
    for (i32 p = 0; p < d->np; p++) {
        if (!mark[p]) continue;
        m = 0;
        for (i32 c = p * d->g; c < d->n && c < (p + 1) * d->g; c++) if (d->grp[c] == 0xFF) l[m++] = (u8)c;
        if (m > 1 && !gmatch(d, l, m)) return 0;
    }
    if (!d->assoc) return 1;
    u32 seen[8] = { 0 };
    for (i32 t = -1; t < d->g; t++) {
        const i32 c = t < 0 ? last : lp * d->g + t;
        if (t >= 0 && (c >= d->n || d->grp[c] != 0xFF)) continue;
        const u8 a = d->assoc[c];
        if (seen[a >> 5] >> (a & 31) & 1) continue;
        seen[a >> 5] |= 1u << (a & 31);
        m = 0;
        for (i32 k = 0; k < d->n; k++) if (d->grp[k] == 0xFF && d->assoc[k] == a) l[m++] = (u8)k;
        if (m > 1 && !(d->cap > 1 ? gmatch2(d, l, m) : gmatch(d, l, m))) return 0;
    }
    return 1;
}

/* group j's state for what is left (gsame's), hashed: interchangeable groups hash alike */
static u16 gsig(const sr_gdraw *d, i32 j)
{
    u32 h = 2166136261u;
    for (i32 p = 0; p < d->np; p++) h = (h ^ (d->slot[p] >> j & 1)) * 16777619u;
    for (i32 c = 0; d->assoc && c < d->n; c++)
        if (d->grp[c] == 0xFF) {
            h = (h ^ (gblk(d, c) >> j & 1)) * 16777619u;
            if (d->cap > 1) h = (h ^ (d->used[d->assoc[c]] >> j & 1)) * 16777619u;
        }
    return (u16)(h ^ h >> 16);
}

/* 1: the clubs left all placed (the witness written), 0: none can be, -1: the budget spent */
static i32 gsolve(sr_gdraw *d, i32 last)
{
    if (--d->steps < 0) return -1;
    i32 bc = -1, bn = 99;
    for (i32 c = 0; c < d->n; c++) {
        if (d->grp[c] != 0xFF) continue;
        const i32 k = bits(gdom(d, c));
        if (!k) return 0;
        if (k < bn) { bn = k; bc = c; }
    }
    if (bc < 0) { for (i32 c = 0; c < d->n; c++) d->wit[c] = d->grp[c]; return 1; }
    i32 fits = 1;                                               /* the witness's groups still free for every club
                                                                   left: they complete the draw (the witness keeps
                                                                   them apart among themselves) */
    for (i32 c = 0; c < d->n && fits; c++) fits = d->witok && (d->grp[c] != 0xFF || (gdom(d, c) >> d->wit[c] & 1));
    for (i32 c = 0; d->cap > 1 && c < d->n && fits; c++) {    /* (cap 2: the drawn and the witness's left of an
                                                                   association in one group, two at most -- only
                                                                   a group already holding one of it can go over:
                                                                   the witness has two at most, gdom none full) */
        if (d->grp[c] != 0xFF || !(d->used[d->assoc[c]] >> d->wit[c] & 1)) continue;
        for (i32 x = c + 1; x < d->n && fits; x++)
            fits = !(d->grp[x] == 0xFF && d->assoc[x] == d->assoc[c] && d->wit[x] == d->wit[c]);
    }
    if (fits) { for (i32 c = 0; c < d->n; c++) if (d->grp[c] != 0xFF) d->wit[c] = d->grp[c]; return 1; }
    if (last >= 0 && !ghall(d, last)) return 0;                 /* (last < 0: the first witness's search) */
    i32 bp = -1, bj = -1, sn = 99;
    for (i32 p = 0; bn > 1 && p < d->np; p++)                   /* every free place of a pot needs a club */
        for (i32 j = 0; j < d->g; j++) {
            if (!(d->slot[p] >> j & 1)) continue;
            i32 k = 0;
            for (i32 c = p * d->g; c < d->n && c < (p + 1) * d->g; c++) k += d->grp[c] == 0xFF && (gdom(d, c) >> j & 1);
            if (!k) return 0;
            if (k < sn) { sn = k; bp = p; bj = j; }
        }
    if (sn < bn) {                                              /* the place of pot bp in group bj: which club */
        u32 tried[8] = { 0 };
        i32 wc = -1;                                            /* (the witness's club there first) */
        for (i32 c = bp * d->g; c < d->n && c < (bp + 1) * d->g; c++) if (d->wit[c] == bj) wc = c;
        for (i32 t = bp * d->g - 1; t < d->n && t < (bp + 1) * d->g; t++) {
            const i32 c = t < bp * d->g ? wc : t;
            if (c < 0 || (t >= bp * d->g && c == wc)) continue;
            if (d->grp[c] != 0xFF || !(gdom(d, c) >> bj & 1)) continue;
            const u8 a = d->assoc ? d->assoc[c] : 0;
            if (tried[a >> 5] >> (a & 31) & 1) continue;        /* (a club of the same association: the same) */
            tried[a >> 5] |= 1u << (a & 31);
            gput(d, c, bj);
            const i32 r = gsolve(d, c);
            gtake(d, c, bj);
            if (r) return r;
        }
        return 0;
    }
    const u32 m = gdom(d, bc);                                  /* club bc: which group (the witness's first) */
    u32 done = 0;
    u16 sig[32];
    for (i32 t = -1; t < d->g; t++) {
        const i32 j = t < 0 ? d->wit[bc] : t;
        if (!(m >> j & 1) || (t >= 0 && j == d->wit[bc])) continue;
        i32 dup = 0;
        sig[j] = gsig(d, j);
        for (i32 k = 0; k < d->g && !dup; k++) if (done >> k & 1 && sig[k] == sig[j]) dup = gsame(d, j, k);
        if (dup) continue;
        done |= 1u << j;
        gput(d, bc, j);
        const i32 r = gsolve(d, bc);
        gtake(d, bc, j);
        if (r) return r;
    }
    return 0;
}

/* edge e's pot and association (0x100 the dummy one; clubs without one each their own past it) */
typedef struct { i32 n, g, e; const u8 *assoc; i8 col[N + 32]; } sr_gking;
static i32 kpot(const sr_gking *k, i32 e) { return e < k->n ? e / k->g : k->n / k->g; }
static i32 kas(const sr_gking *k, i32 e) { return e >= k->n ? 0x100 : k->assoc ? k->assoc[e] : 0x101 + e; }
static u32 kused(const sr_gking *k, i32 pot, i32 as)            /* the colours at a pot (as < 0) or an association */
{
    u32 m = 0;
    for (i32 e = 0; e < k->e; e++)
        if (k->col[e] >= 0 && (as < 0 ? kpot(k, e) == pot : kas(k, e) == as)) m |= 1u << k->col[e];
    return m;
}
static i32 kat(const sr_gking *k, i32 pot, i32 as, i32 x)       /* the edge of colour x there, -1 none */
{
    for (i32 e = 0; e < k->e; e++)
        if (k->col[e] == x && (as < 0 ? kpot(k, e) == pot : kas(k, e) == as)) return e;
    return -1;
}
static i32 lowbit(u32 m) { i32 j = 0; while (!(m >> j & 1)) j++; return j; }

/* a whole draw into wit (-2 an association with more clubs than groups) */
static __attribute__((noinline)) i32 gking(i32 n, i32 g, const u8 *assoc, u8 *wit)
{
    sr_gking k;
    k.n = n; k.g = g; k.assoc = assoc; k.e = n % g ? n + g - n % g : n;
    for (i32 e = 0; e < k.e; e++) k.col[e] = -1;
    const u32 all = g < 32 ? (1u << g) - 1 : 0xFFFFFFFFu;
    for (i32 e = 0; e < k.e; e++) {
        const i32 p = kpot(&k, e), as = kas(&k, e);
        const u32 fu = all & ~kused(&k, p, -1), fv = all & ~kused(&k, 0, as);
        if (!fv) return -2;
        const i32 x = lowbit(fu), y = lowbit(fv);               /* (a pot has g edges: x is there) */
        if (!(fv >> x & 1)) {                                   /* swap x / y on the path from as that starts on x:
                                                                   it never reaches pot p (bipartite), x stays free */
            i32 onpot = 0, c = x;
            for (i32 f = kat(&k, 0, as, x); f >= 0; onpot = !onpot) {
                c = c == x ? y : x;
                const i32 nf = onpot ? kat(&k, 0, kas(&k, f), c) : kat(&k, kpot(&k, f), -1, c);
                k.col[f] = (i8)c;
                f = nf;
            }
        }
        k.col[e] = (i8)x;
    }
    u8 name[32];                                                /* the dummies' colours: the smaller groups */
    u32 dm = 0;
    for (i32 e = n; e < k.e; e++) dm |= 1u << k.col[e];
    for (i32 j = 0, big = 0, small = 0; j < g; j++) {
        if (dm >> j & 1) name[j] = (u8)(g - (k.e - n) + small++);
        else name[j] = (u8)big++;
    }
    for (i32 c = 0; c < n; c++) wit[c] = name[k.col[c]];
    return 1;
}

/* the witness keeps every protect pair apart (with no pairs: always) */
static int gwit_ok(const sr_gdraw *d)
{
    for (i32 i = 0; i < d->nprot; i++)
        for (i32 x = 0; x < d->n; x++)
            if (d->assoc[x] == d->prot[2 * i])
                for (i32 y = 0; y < d->n; y++)
                    if (d->assoc[y] == d->prot[2 * i + 1] && d->wit[y] == d->wit[x]) return 0;
    return 1;
}

/* club c, just put in group j off the witness (its group w there): the witness's j / w Kempe chain from c flipped --
 * the clubs in j or w linked to c through a pot or an association swap the two (still a proper draw, c in j). Refused
 * (0) when the chain holds another drawn club or would put the short last pot's club in a smaller group. */
static __attribute__((noinline)) int gkempe(sr_gdraw *d, i32 c, i32 j, i32 big)
{
    const i32 w = d->wit[c];
    u8 q[N], in[N];
    i32 nq = 0;
    for (i32 x = 0; x < d->n; x++) in[x] = 0;
    q[nq++] = (u8)c; in[c] = 1;
    for (i32 h = 0; h < nq; h++) {
        const i32 x = q[h];
        for (i32 y = 0; y < d->n; y++)
            if (!in[y] && (d->wit[y] == j || d->wit[y] == w) &&
                (d->pot[y] == d->pot[x] || (d->assoc && d->assoc[y] == d->assoc[x]))) { in[y] = 1; q[nq++] = (u8)y; }
    }
    for (i32 h = 1; h < nq; h++) {
        const i32 y = q[h], to = d->wit[y] == j ? w : j;
        if (d->grp[y] != 0xFF || (d->pot[y] == d->np - 1 && d->n % d->g && to >= big)) return 0;
    }
    for (i32 h = 0; h < nq; h++) d->wit[q[h]] = (u8)(d->wit[q[h]] == j ? w : j);
    if (gwit_ok(d)) return 1;
    for (i32 h = 0; h < nq; h++) d->wit[q[h]] = (u8)(d->wit[q[h]] == j ? w : j);   /* (a protect pair together:
                                                                   undone, the search decides) */
    return 0;
}

/* swc/1.5 protect pairs: a component of them that is a clique (on the associations drawn) is one class -- König's
 * bound and gking stay exact (cls: the class per club, its component's first association); the pairs of the other components
 * (chains: KOS-BIH + KOS-SRB leave BIH v SRB free) go to fp, for gblk. Returns the pairs kept. */
static __attribute__((noinline)) i32 gclasses(i32 n, const u8 *assoc, const u8 *prot, i32 nprot, u8 *cls, u8 *fp)
{
    u8 v[N], par[N], mem[N], prs[N];                           /* the associations drawn, their union-find, per root
                                                                   its members and its pairs */
    i32 nv = 0, np = 0;
    for (i32 c = 0; c < n; c++) {
        i32 k = 0;
        while (k < nv && v[k] != assoc[c]) k++;
        if (k == nv) { v[nv] = assoc[c]; par[nv] = (u8)nv; mem[nv] = 1; prs[nv] = 0; nv++; }
    }
    for (i32 i = 0; i < nprot; i++) {
        i32 x = 0, y = 0;
        while (x < nv && v[x] != prot[2 * i]) x++;
        while (y < nv && v[y] != prot[2 * i + 1]) y++;
        if (x == nv || y == nv || x == y) continue;             /* (a pair with an association not drawn: no part) */
        while (par[x] != x) x = par[x];
        while (par[y] != y) y = par[y];
        if (x != y) { par[y] = (u8)x; mem[x] = (u8)(mem[x] + mem[y]); prs[x] = (u8)(prs[x] + prs[y]); }
        prs[x]++;
    }
    for (i32 c = 0; c < n; c++) {
        i32 k = 0, r;
        while (v[k] != assoc[c]) k++;
        for (r = k; par[r] != r; r = par[r])
            ;
        cls[c] = prs[r] == mem[r] * (mem[r] - 1) / 2 ? v[r] : assoc[c];    /* (a clique: one class, its root's) */
    }
    for (i32 i = 0; i < nprot; i++) {
        i32 r = 0, y = 0;
        while (r < nv && v[r] != prot[2 * i]) r++;
        while (y < nv && v[y] != prot[2 * i + 1]) y++;
        if (r == nv || y == nv || r == y) continue;
        while (par[r] != r) r = par[r];
        if (prs[r] == mem[r] * (mem[r] - 1) / 2) continue;      /* (inside a clique: the class) */
        fp[2 * np] = prot[2 * i]; fp[2 * np + 1] = prot[2 * i + 1]; np++;
    }
    return np;
}

i32 sr_group_draw(i32 n, i32 g, const u8 *assoc, u32 seed, u8 *grp)
{
    return sr_group_draw_p(n, g, assoc, 0, 0, seed, grp);
}

i32 sr_group_draw_p(i32 n, i32 g, const u8 *assoc, const u8 *prot, i32 nprot, u32 seed, u8 *grp)
{
    return sr_group_draw_k(n, g, assoc, prot, nprot, 1, seed, grp);
}

i32 sr_group_draw_k(i32 n, i32 g, const u8 *assoc, const u8 *prot, i32 nprot, i32 cap, u32 seed, u8 *grp)
{
    u8 size[N], cls[N], fp[2 * SR_PROT_PAIRS];
    if (n > N || sr_group_sizes(n, g, size) < 0 || nprot < 0 || nprot > SR_PROT_PAIRS || (nprot && (!assoc || !prot)) ||
        cap < 1 || cap > 2 || (cap > 1 && nprot))
        return -1;
    sr_gdraw d;
    d.n = n; d.g = g; d.np = (n + g - 1) / g; d.assoc = assoc; d.steps = GBUDGET; d.nprot = 0; d.prot = fp; d.witok = 1;
    d.cap = assoc ? cap : 1;
    if (d.cap > 1) d.steps = GBUDGET_C;
    if (nprot) { d.nprot = gclasses(n, assoc, prot, nprot, cls, fp); d.assoc = cls; if (d.nprot) d.steps = GBUDGET_P; }
    for (i32 p = 0; p < d.np; p++) {                           /* pot by pot, each pot in hashed order */
        const i32 b = p * g, len = n - b < g ? n - b : g;
        u8 o[N];
        hash_order(seed, 0x90700000u + (u32)p * 64u, len, o);
        for (i32 k = 0; k < len; k++) d.club[b + k] = (u8)(b + o[k]);
        d.slot[p] = 0;
        for (i32 j = 0; j < g; j++) if (size[j] > p) d.slot[p] |= 1u << j;
    }
    for (i32 c = 0; c < n; c++) { d.pot[c] = (u8)(c / g); d.grp[c] = 0xFF; }
    for (i32 a = 0; a < 256; a++) d.used[a] = d.blk[a] = 0;
    if (d.cap > 1) {                                            /* (cap 2: the first witness by König on each
                                                                   association split in two classes, its clubs
                                                                   alternately -- a class over g: the association
                                                                   over 2g, no draw) */
        u8 v[N], h[N];
        i32 nv = 0;
        for (i32 c = 0; c < n; c++) {
            i32 k = 0;
            while (k < nv && v[k] != assoc[c]) k++;
            if (k == nv) { v[nv] = assoc[c]; h[nv] = 0; nv++; }
            cls[c] = (u8)(2 * k + h[k]); h[k] ^= 1;
        }
    }
    i32 r = gking(n, g, d.cap > 1 ? cls : d.assoc, d.wit);
    if (r < 0) return r;
    if (!gwit_ok(&d)) {                                         /* a protect chain: the first witness by the search */
        d.witok = 0;
        r = gsolve(&d, -1);
        if (r <= 0) return r < 0 ? -3 : -2;
        d.witok = 1;
    }
    for (i32 i = 0; i < n; i++) {                               /* each club to the first group, in an order hashed
                                                                   from the seed and the club, that leaves a draw */
        const i32 c = d.club[i];
        u8 go[N];
        r = 0;
        hash_order(seed, 0x6D000000u + (u32)c * 64u, g, go);
        for (i32 k = 0; k < g; k++) {
            const i32 j = go[k];
            if (!(gdom(&d, c) >> j & 1)) continue;
            gput(&d, c, j);
            r = d.wit[c] == j || gkempe(&d, c, j, n % g) ? 1 : gsolve(&d, c);
            if (r > 0) break;
            gtake(&d, c, j);                                    /* (no draw that way, or undecided in the budget) */
        }
        if (r <= 0) return -2;                                  /* (not reached: the witness's group is one) */
    }
    for (i32 c = 0; c < n; c++) grp[c] = d.grp[c];
    return g;
}

i32 sr_best_placed(const sr_group *g, i32 ng, i32 place, i32 win, i32 draw, i32 loss, const u8 *tieb, u32 seed,
                   u8 *ord)
{
    for (const u8 *t = tieb; t && *t; t++)
        if (!usable(*t) || (*t >= SR_TB_H2H_POINTS && *t <= SR_TB_H2H_AWAY_GOALS) || *t == SR_TB_H2H_REAPPLIED ||
            *t == SR_TB_AVULSA || *t == SR_TB_H2H_TABLE_ONCE || *t == SR_TB_ONLY_IF_TWO) return -1;
    if (ng < 1 || ng > N) return -1;
    for (i32 j = 0; j < ng; j++) {                              /* (each group as sr_rr_table leaves it) */
        u8 seen[N];
        if (g[j].n < 0 || g[j].n > N || g[j].nm < 0) return -1;
        for (i32 k = 0; k < g[j].n; k++) seen[k] = 0;
        for (i32 k = 0; k < g[j].n; k++) {
            const i32 c = g[j].table[k].club;
            if (c >= g[j].n || seen[c]) return -1;
            seen[c] = 1;
        }
        for (i32 k = 0; k < g[j].nm; k++)
            if (g[j].m[k].home >= g[j].n || g[j].m[k].away >= g[j].n) return -1;
    }
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

typedef struct {
    i32 mode, n, nprot, multi;
    const u8 *avoid, *assoc, *prot;
    u32 seed; u8 order[N]; u8 used[N]; i32 steps;
    u32 adj[N / 2];                                             /* (multi, seeded: top club t's allowed bottom clubs) */
} sr_pdraw;

/* a and b may meet: other groups (avoid), other associations, no protect pair (swc/1.5) */
static int pok(const sr_pdraw *d, i32 a, i32 b)
{
    if (d->avoid && d->avoid[a] == d->avoid[b]) return 0;
    if (!d->assoc) return 1;
    const u8 x = d->assoc[a], y = d->assoc[b];
    if (x == y) return 0;
    for (i32 i = 0; i < d->nprot; i++)
        if ((d->prot[2 * i] == x && d->prot[2 * i + 1] == y) || (d->prot[2 * i] == y && d->prot[2 * i + 1] == x)) return 0;
    return 1;
}

/* seeded, two keys or protect pairs: the free top clubs each to a free bottom club it may meet (Kuhn) -- exact */
static int paug(const sr_pdraw *d, i32 t, u32 *seen, i8 *by)
{
    const i32 h = d->n / 2;
    for (i32 b = 0; b < h; b++) {
        if (!(d->adj[t] >> b & 1) || d->used[h + b] || *seen >> b & 1) continue;
        *seen |= 1u << b;
        if (by[b] < 0 || paug(d, by[b], seen, by)) { by[b] = (i8)t; return 1; }
    }
    return 0;
}

/* the free clubs can still all be paired (exact: draw -- no avoid class holds more than half of them; seeded --
 * no class more than the pairs left, its free top-half and bottom-half clubs together; Hall's condition; seeded with
 * two keys or protect pairs: a perfect matching of the free clubs, by augmenting paths) */
static int pdraw_open(const sr_pdraw *d)
{
    if (d->multi) {
        i8 by[N / 2];
        for (i32 b = 0; b < d->n / 2; b++) by[b] = -1;
        for (i32 t = 0; t < d->n / 2; t++) {
            u32 seen = 0;
            if (!d->used[t] && !paug(d, t, &seen, by)) return 0;
        }
        return 1;
    }
    if (!d->avoid) return 1;
    const i32 half = d->mode == SR_PAIR_SEEDED ? d->n / 2 : d->n;
    u8 cnt[256];
    i32 left = 0;
    for (i32 a = 0; a < 256; a++) cnt[a] = 0;
    for (i32 c = 0; c < d->n; c++) if (!d->used[c]) { cnt[d->avoid[c]]++; left += c < half; }
    const i32 pairs = d->mode == SR_PAIR_SEEDED ? left : left / 2;
    for (i32 a = 0; a < 256; a++) if (cnt[a] > pairs) return 0;
    return 1;
}

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
        if (d->used[b] || (d->mode == SR_PAIR_SEEDED && b < half) || !pok(d, a, b)) continue;
        d->used[b] = 1; out[2 * k] = (u8)a; out[2 * k + 1] = (u8)b;
        if (pdraw_open(d) && pdraw(d, out, k + 1)) return 1;
        d->used[b] = 0;
    }
    d->used[a] = 0;
    return 0;
}

i32 sr_ko_pairs(i32 mode, i32 n, const u8 *avoid, u32 seed, u8 *out)
{
    return sr_ko_pairs_x(mode, n, avoid, 0, 0, 0, seed, out);
}

i32 sr_ko_pairs_x(i32 mode, i32 n, const u8 *avoid, const u8 *assoc, const u8 *prot, i32 nprot, u32 seed, u8 *out)
{
    if (n < 2 || n > N || (n & 1) || nprot < 0 || nprot > SR_PROT_PAIRS || (nprot && (!assoc || !prot))) return -1;
    if (mode == SR_PAIR_DRAW && avoid && assoc) return -1;      /* (two keys: seeded only -- a bipartite matching) */
    if (!avoid && assoc && !nprot) avoid = assoc, assoc = 0;    /* (one key: sr_ko_pairs's own) */
    if (mode == SR_PAIR_FIXED || mode == SR_PAIR_BRACKET) {
        if (mode == SR_PAIR_FIXED) for (i32 k = 0; k < n; k++) out[k] = (u8)k;
        else {
            if (n & (n - 1)) return -1;
            out[0] = 0;                                         /* order(2m) = x, 2m-1-x for each x of order(m) */
            for (i32 m = 1; m < n; m *= 2)
                for (i32 k = m - 1; k >= 0; k--) { const u8 v = out[k]; out[2 * k] = v; out[2 * k + 1] = (u8)(2 * m - 1 - v); }
        }
        sr_pdraw f;
        f.avoid = avoid; f.assoc = assoc; f.prot = prot; f.nprot = nprot;
        for (i32 k = 0; k < n; k += 2) if (!pok(&f, out[k], out[k + 1])) return -3;
        return n / 2;
    }
    if (mode != SR_PAIR_DRAW && mode != SR_PAIR_SEEDED) return -1;
    sr_pdraw d;
    d.mode = mode; d.n = n; d.avoid = avoid; d.seed = seed; d.steps = BUDGET;
    d.assoc = assoc; d.prot = prot; d.nprot = nprot; d.multi = mode == SR_PAIR_SEEDED && assoc;
    for (i32 t = 0; d.multi && t < n / 2; t++) {
        d.adj[t] = 0;
        for (i32 b = 0; b < n / 2; b++) if (pok(&d, t, n / 2 + b)) d.adj[t] |= 1u << b;
    }
    for (i32 k = 0; k < n; k++) d.used[k] = 0;
    hash_order(seed, 0xD7000000u, n, d.order);
    return pdraw_open(&d) && pdraw(&d, out, 0) ? n / 2 : -2;
}
