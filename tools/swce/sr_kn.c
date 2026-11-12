/*
 * sr_kn.c -- 42-s2ko: a knockout's bracket numbers and its fixed bracket, as the Coppa Italia plays them (Lega
 * Serie A C.U. n. 253 of 27/05/2024, the regulation 2024-25 .. 2026-27, and its Allegato 1).
 *
 * The numbers: groups of last season's clubs numbered 1, 2, ... in order -- each group takes its clubs from the
 * caller's lists (a league's table, the clubs promoted out of it, a cup's winner ...), skips a club already
 * numbered or not eligible (not in this season's leagues), in list order or by the record (points per match, wins,
 * goals for, then a draw: C.U. 253 3.1 f/g as applied to groups of unequal size), and fills what it lacks from its
 * 'else' lists (place, then points per match: "la meglio classificata ex art. 49 NOIF").
 *
 * The bracket: rounds of fixed pairs, a side being a number (that club enters here) or an earlier tie's winner;
 * the host by the lower entry number (the second leg's, in two legs), neutral, drawn or as listed; a first season's
 * field swaps (C.U. 253 3.3: "inversione del campo"). M2: drawn rounds (the previous winners and the round's
 * joiners, drawn openly or within each zone, a joiner hosting) and the zones by proximity (the Coppa Italia Serie
 * C's geographic groups, Lega Pro C.U. n. 36/L 2.1-2.2: four groups of 14, each seed to the nearest group). M2b
 * (the Coppa Italia Serie D, LND Dipartimento Interregionale C.U. n. 1 of 06/08/2026): a draw within geographic
 * blocks (the pool halved by geography, the Dipartimento's "abbinamenti" -- a fixed bracket of neighbours), the
 * host by alternation (art. 4) and the entry order from the bottom of last season's tables.
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint16_t u16;
typedef uint32_t u32;

static u32 below(u32 *rng, u32 n)
{
    *rng = *rng * 1103515245u + 12345u;
    return ((*rng >> 16) * n) >> 16;
}

/* a before b: 1 */
static int kn_before(const sr_kn_rec *rec, const u32 *key, u16 a, u16 b, int32_t order)
{
    const sr_kn_rec *x = &rec[a], *y = &rec[b];
    u32 l, r;
    if (order == SR_KN_PLACE_RECORD && x->place != y->place) return x->place < y->place;
    if (order == SR_KN_PLACE_DESC) return x->place != y->place ? x->place > y->place : key[a] < key[b];
    l = (u32)x->pts * (y->pld ? y->pld : 1);
    r = (u32)y->pts * (x->pld ? x->pld : 1);
    if (l != r) return l > r;
    if (order == SR_KN_RECORD) {
        if (x->won != y->won) return x->won > y->won;
        if (x->gf != y->gf) return x->gf > y->gf;
    }
    return key[a] < key[b];
}

/* the candidates of lists ls[0 .. n) not numbered yet and eligible, in order, into c; their count */
static int32_t kn_cands(const sr_kn_list *lists, const uint8_t *ls, int32_t n, const uint8_t *taken,
                        const uint8_t *eligible, u16 *c, int32_t max)
{
    int32_t m = 0;
    for (int32_t i = 0; i < n; i++) {
        const sr_kn_list *l = &lists[ls[i]];
        for (int32_t hop = 0; l && l->n < 0; hop++)  /* (unknown: its fallback, as the spec chains them) */
            l = hop < 16 && l->unknown >= 0 ? &lists[l->unknown] : 0;
        if (!l) continue;
        for (int32_t j = 0; j < l->n; j++) {
            const u16 k = l->club[j];
            int32_t dup = 0;
            if (k >= SR_KN_CLUBS || taken[k] || !eligible[k]) continue;
            for (int32_t q = 0; q < m; q++) dup |= c[q] == k;
            if (!dup && m < max) c[m++] = k;
        }
    }
    return m;
}

static void kn_sort(u16 *c, int32_t m, const sr_kn_rec *rec, const u32 *key, int32_t order)
{
    for (int32_t i = 1; i < m; i++) {               /* (insertion: stable, a handful of clubs) */
        const u16 v = c[i];
        int32_t j = i;
        while (j > 0 && kn_before(rec, key, v, c[j - 1], order)) { c[j] = c[j - 1]; j--; }
        c[j] = v;
    }
}

int32_t sr_kn_number(const sr_kn_group *g, int32_t ng, const sr_kn_list *lists, const sr_kn_rec *rec,
                     const uint8_t *eligible, uint32_t *rng, sr_kn_work *w, uint16_t *out, int32_t max)
{
    int32_t n = 0;
    for (int32_t k = 0; k < SR_KN_CLUBS; k++) { w->taken[k] = 0; w->key[k] = below(rng, 0x10000u); }
    for (int32_t gi = 0; gi < ng; gi++) {
        int32_t m = kn_cands(lists, g[gi].from, g[gi].nfrom, w->taken, eligible, w->cand, SR_KN_NUMBERS), want = g[gi].take;
        if (g[gi].order != SR_KN_LIST) kn_sort(w->cand, m, rec, w->key, g[gi].order);
        for (int32_t i = 0; i < m && want; i++, want--) {
            if (n >= max) return -1;
            out[n++] = w->cand[i];
            w->taken[w->cand[i]] = 1;
        }
        if (want) {                                 /* (short: the group's 'else') */
            m = kn_cands(lists, g[gi].els, g[gi].nelse, w->taken, eligible, w->cand, SR_KN_NUMBERS);
            if (g[gi].else_order != SR_KN_LIST) kn_sort(w->cand, m, rec, w->key, g[gi].else_order);
            for (int32_t i = 0; i < m && want; i++, want--) {
                if (n >= max) return -1;
                out[n++] = w->cand[i];
                w->taken[w->cand[i]] = 1;
            }
        }
        if (want) return -1;                        /* (nobody left to number) */
    }
    return n;
}

/* M2b: idx[0 .. n) (pool places) in geographic order -- a segment over 'block' clubs sorted along its longer extent
   (latitude, or longitude by cos 42 degrees; equal: the lower club) and halved (both halves even), down to blocks of
   at most 'block', each block then shuffled (the draw). 0; -1 an odd pool or a block under 2. */
static int32_t kn_geo(u16 *idx, int32_t n, int32_t block, const sr_kn_work *w, uint32_t *rng)
{
    int32_t lo[24], len[24], sp = 0;
    if (n & 1 || block < 2 || !w->geo) return -1;
    lo[0] = 0; len[0] = n; sp = 1;
    while (sp) {
        const int32_t a = lo[--sp], k = len[sp];
        if (k <= block) {
            for (int32_t i = k - 1; i > 0; i--) {
                const int32_t j = (int32_t)below(rng, (u32)i + 1);
                const u16 x = idx[a + i]; idx[a + i] = idx[a + j]; idx[a + j] = x;
            }
            continue;
        }
        int32_t x0 = 0x7FFF, x1 = -0x8000, y0 = 0x7FFF, y1 = -0x8000, h = k / 2;
        for (int32_t i = a; i < a + k; i++) {
            const sr_kn_geo *g = &w->geo[w->pool[idx[i]]];
            const int32_t x = g->lon * 761 / 1024;
            if (x < x0) x0 = x;
            if (x > x1) x1 = x;
            if (g->lat < y0) y0 = g->lat;
            if (g->lat > y1) y1 = g->lat;
        }
        const int32_t lon = x1 - x0 > y1 - y0;
        for (int32_t i = a + 1; i < a + k; i++) {   /* (insertion: stable, the key then the club) */
            const u16 v = idx[i];
            const sr_kn_geo *gv = &w->geo[w->pool[v]];
            const int32_t kv = lon ? gv->lon * 761 / 1024 : gv->lat;
            int32_t j = i;
            while (j > a) {
                const sr_kn_geo *gp = &w->geo[w->pool[idx[j - 1]]];
                const int32_t kp = lon ? gp->lon * 761 / 1024 : gp->lat;
                if (kp < kv || (kp == kv && w->pool[idx[j - 1]] <= w->pool[v])) break;
                idx[j] = idx[j - 1]; j--;
            }
            idx[j] = v;
        }
        if (h & 1) h--;
        if (sp + 2 > 24) return -1;
        lo[sp] = a + h; len[sp++] = k - h;
        lo[sp] = a; len[sp++] = h;
    }
    return 0;
}

/* A drawn round's sides into out[first ..): the previous round's winners (their zones) and this round's joiners,
   drawn within each zone (or all as one); under home "joiner" each joiner against a club of the earlier round. The
   ties made; -1 they do not fit, or a club is twice in the pool. */
static int32_t kn_draw(const sr_kn_round *rd, int32_t r, const sr_kn_entry *join, uint32_t *rng, sr_kn_work *w,
                       sr_kn_tie *out)
{
    int32_t m = 0, made = 0;
    if (r > 0)
        for (int32_t t = 0; t < rd[r - 1].ties; t++) {
            const sr_kn_tie *p = &out[rd[r - 1].first + t];
            if (m >= SR_KN_NUMBERS) return -1;
            w->pool[m] = p->winner; w->pnum[m] = p->nwin; w->pzone[m] = p->zone; w->pjoin[m++] = 0;
        }
    for (int32_t k = 0; join && k < rd[r].njoin; k++) {
        const sr_kn_entry *e = &join[rd[r].jfirst + k];
        if (m >= SR_KN_NUMBERS) return -1;
        w->pool[m] = e->club; w->pnum[m] = 0; w->pzone[m] = e->zone; w->pjoin[m++] = rd[r].home == SR_KN_JOINER;
    }
    for (int32_t i = 0; i < m; i++) {               /* (a club twice in the pool -- a club in two chains, a
                                                       joiner already through: refused, never a tie with itself) */
        if (w->pool[i] >= SR_KN_CLUBS) return -1;
        w->taken[w->pool[i]] = 0;
    }
    for (int32_t i = 0; i < m; i++) {
        if (w->taken[w->pool[i]]) return -1;
        w->taken[w->pool[i]] = 1;
    }
    if (rd[r].pairing == SR_KN_PAIR_GEO) {          /* (M2b: neighbours, in the order's pairs) */
        u16 *idx = w->cand;
        for (int32_t i = 0; i < m; i++) idx[i] = (u16)i;
        if (kn_geo(idx, m, rd[r].block, w, rng) < 0 || m / 2 != rd[r].ties) return -1;
        for (int32_t i = 0; i < m / 2; i++) {
            sr_kn_tie *o = &out[rd[r].first + i];
            o->home = w->pool[idx[2 * i]]; o->away = w->pool[idx[2 * i + 1]];
            o->nhome = w->pnum[idx[2 * i]]; o->naway = w->pnum[idx[2 * i + 1]];
            o->zone = 0; o->flags = 0;
        }
        return m / 2;
    }
    for (int32_t z = 0; z < (rd[r].pairing == SR_KN_PAIR_ZONE ? SR_KN_ZONES : 1); z++) {
        u16 *idx = w->cand;                         /* (the zone's members: indexes into the pool) */
        int32_t n = 0, nj = 0, at;
        for (int32_t i = 0; i < m; i++)
            if (rd[r].pairing != SR_KN_PAIR_ZONE || w->pzone[i] == z) idx[n++] = (u16)i;
        for (int32_t i = n - 1; i > 0; i--) {       /* (the draw) */
            const int32_t j = (int32_t)below(rng, (u32)i + 1);
            const u16 x = idx[i]; idx[i] = idx[j]; idx[j] = x;
        }
        for (int32_t i = 0; i < n; i++)             /* (the joiners first, in drawn order) */
            if (w->pjoin[idx[i]]) { const u16 x = idx[i]; idx[i] = idx[nj]; idx[nj++] = x; }
        if (n & 1 || nj * 2 > n) return -1;
        at = nj;                                    /* (joiner i v idx[nj + i]; the rest in pairs) */
        for (int32_t i = 0; i < n / 2; i++) {
            const u16 a = i < nj ? idx[i] : idx[at++], b = idx[at++];
            sr_kn_tie *o;
            if (made >= rd[r].ties) return -1;
            o = &out[rd[r].first + made++];
            o->home = w->pool[a]; o->away = w->pool[b];
            o->nhome = w->pnum[a]; o->naway = w->pnum[b];
            o->zone = w->pzone[a];
            o->flags = w->pjoin[a] ? 4 : 0;         /* (until played: the home side joined here) */
        }
    }
    return made == rd[r].ties ? made : -1;
}

/* A fixed side's winner reference (round wr, tie wt): its count of uses over the cup -- a fixed side naming it, and
   the drawn round after wr taking all of wr's winners. */
static int32_t kn_uses(const sr_kn_round *rd, int32_t nr, const sr_kn_pair *pairs, int32_t wr, int32_t wt)
{
    int32_t n = wr + 1 < nr && rd[wr + 1].pairing != SR_KN_PAIR_FIXED;
    const u16 ref = SR_KN_WIN(wr, wt);
    for (int32_t r = wr + 1; r < nr; r++)
        if (rd[r].pairing == SR_KN_PAIR_FIXED)
            for (int32_t t = 0; t < rd[r].ties; t++)
                n += (pairs[rd[r].first + t].a == ref) + (pairs[rd[r].first + t].b == ref);
    return n;
}

int32_t sr_kn_cup_check(const sr_kn_round *rd, int32_t nr, const sr_kn_pair *pairs, const uint16_t *numbers,
                        int32_t nn, const sr_kn_entry *join)
{
    int32_t nj = 0;
    if (!rd || nr < 0 || nn < 0 || nn > SR_KN_NUMBERS || (nn && !numbers)) return -1;
    for (int32_t r = 0; r < nr; r++) {
        if (rd[r].ties < 1) return -1;
        if (rd[r].pairing == SR_KN_PAIR_FIXED) {
            if (rd[r].njoin || !pairs) return -1;   /* (a fixed round's joiners would never enter) */
            for (int32_t t = 0; t < rd[r].ties; t++)
                for (int32_t s = 0; s < 2; s++) {
                    const u16 v = s ? pairs[rd[r].first + t].b : pairs[rd[r].first + t].a;
                    if (v & 0x8000u) {
                        const int32_t wr = (v >> 9) & 0x3F, wt = v & 0x1FF;
                        if (wr >= r || wt >= rd[wr].ties || kn_uses(rd, nr, pairs, wr, wt) != 1) return -1;
                    } else {
                        int32_t used = 0;           /* (a number enters once) */
                        if (v < 1 || v > nn) return -1;
                        for (int32_t q = 0; q < nr; q++)
                            if (rd[q].pairing == SR_KN_PAIR_FIXED)
                                for (int32_t k = 0; k < rd[q].ties; k++)
                                    used += (pairs[rd[q].first + k].a == v) + (pairs[rd[q].first + k].b == v);
                        if (used != 1) return -1;
                    }
                }
        } else {
            if ((r ? rd[r - 1].ties : 0) + rd[r].njoin != 2 * rd[r].ties || (rd[r].njoin && !join)) return -1;
            if (r && rd[r - 1].pairing == SR_KN_PAIR_FIXED)    /* (the fixed round's winners all taken here: none
                                                                   named again by a later fixed side) */
                for (int32_t t = 0; t < rd[r - 1].ties; t++)
                    if (kn_uses(rd, nr, pairs, r - 1, t) != 1) return -1;
            if (rd[r].jfirst + rd[r].njoin > nj) nj = rd[r].jfirst + rd[r].njoin;
        }
    }
    for (int32_t i = 0; i < nn + nj; i++) {         /* (every club entering, numbered or joining: once) */
        const u16 c = i < nn ? numbers[i] : join[i - nn].club;
        int32_t joins = i < nn;
        if (c >= SR_KN_CLUBS) return -1;
        for (int32_t r = 0; r < nr && !joins; r++)  /* (a joiner entry no round takes is not an entrant) */
            joins = rd[r].pairing != SR_KN_PAIR_FIXED && i - nn >= rd[r].jfirst && i - nn < rd[r].jfirst + rd[r].njoin;
        if (!joins) continue;
        for (int32_t k = 0; k < i; k++) {
            int32_t kj = k < nn;
            for (int32_t r = 0; r < nr && !kj; r++)
                kj = rd[r].pairing != SR_KN_PAIR_FIXED && k - nn >= rd[r].jfirst && k - nn < rd[r].jfirst + rd[r].njoin;
            if (kj && (k < nn ? numbers[k] : join[k - nn].club) == c) return -1;
        }
    }
    return 0;
}

int32_t sr_kn_cup(const sr_kn_round *rd, int32_t nr, const sr_kn_pair *pairs, const uint16_t *numbers, int32_t nn,
                  const sr_kn_entry *join, const uint8_t *swap, uint32_t *rng, sr_kn_play_fn play, void *ctx,
                  sr_kn_work *w, sr_kn_tie *out)
{
    int32_t last = -1;
    if (sr_kn_cup_check(rd, nr, pairs, numbers, nn, join) < 0) return -2;   /* (refused before a tie is built) */
    for (int32_t r = 0; r < nr; r++) {
        const int32_t drawn = rd[r].pairing != SR_KN_PAIR_FIXED;
        if (drawn && (!w || kn_draw(rd, r, join, rng, w, out) < 0)) return -2;
        for (int32_t t = 0; t < rd[r].ties; t++) {
            const int32_t p = rd[r].first + t;
            u16 club[2], num[2];
            uint8_t zone = 0, joined = 0, was[2] = { 2, 2 };   /* (each side's previous tie: 1 home, 0 away, 2 none) */
            sr_kn_tie *o = &out[p];
            if (drawn) {
                club[0] = o->home; club[1] = o->away; num[0] = o->nhome; num[1] = o->naway;
                zone = o->zone; joined = o->flags & 4;
            } else
                for (int32_t s = 0; s < 2; s++) {
                    const u16 v = s ? pairs[p].b : pairs[p].a;
                    if (v & 0x8000u) {              /* an earlier tie's winner: its club, its entry number */
                        const int32_t wr = (v >> 9) & 0x3F, wt = v & 0x1FF;
                        if (wr >= r || wt >= rd[wr].ties) return -2;
                        const sr_kn_tie *pt = &out[rd[wr].first + wt];
                        club[s] = pt->winner;
                        num[s] = pt->nwin;
                        if (!(pt->flags & SR_KN_F_NEUTRAL)) was[s] = pt->winner == pt->home;
                        if (!s) zone = out[rd[wr].first + wt].zone;
                    } else {
                        if (v < 1 || v > nn) return -2;
                        club[s] = numbers[v - 1];
                        num[s] = v;
                    }
                }
            int32_t h = 0;                          /* (the side at home: in two legs, the first leg's) */
            o->flags = 0;
            switch (rd[r].home) {
            case SR_KN_LOWER: h = num[1] < num[0]; break;
            case SR_KN_LOWER_2ND: h = num[1] > num[0]; o->flags |= SR_KN_F_2ND; break;
            case SR_KN_NEUTRAL: o->flags |= SR_KN_F_NEUTRAL; break;
            case SR_KN_DRAW: h = (int32_t)below(rng, 2); break;
            case SR_KN_JOINER: h = joined ? 0 : (int32_t)below(rng, 2); break;
            case SR_KN_ALTERNATE: h = was[0] != 2 && was[1] != 2 && was[0] != was[1] ? was[0] : (int32_t)below(rng, 2); break;
            default: break;                         /* (fixed: as listed) */
            }
            if (swap && swap[p]) h ^= 1;
            o->home = club[h]; o->away = club[h ^ 1];
            o->nhome = num[h]; o->naway = num[h ^ 1];
            o->legs = rd[r].legs;
            o->zone = zone;
            const int32_t a = play(ctx, r, t, o);
            if (a < 0) return -1;
            o->winner = a ? o->away : o->home;
            o->nwin = a ? o->naway : o->nhome;
            last = o->winner;
        }
    }
    return last;
}

int32_t sr_kn_bracket(const sr_kn_round *rd, int32_t nr, const sr_kn_pair *pairs, const uint16_t *numbers,
                      int32_t nn, const uint8_t *swap, uint32_t *rng, sr_kn_play_fn play, void *ctx, sr_kn_tie *out)
{
    return sr_kn_cup(rd, nr, pairs, numbers, nn, 0, swap, rng, play, ctx, 0, out);
}

int32_t sr_kn_zones(const sr_kn_geo *geo, const uint16_t *clubs, int32_t n, const sr_kn_geo *centre, int32_t nz,
                    int32_t cap, sr_kn_work *w, uint8_t *zone)
{
    int32_t left[SR_KN_ZONES];
    if (nz < 1 || nz > SR_KN_ZONES || n < 0 || n > nz * cap || n > SR_KN_NUMBERS) return -1;
    for (int32_t z = 0; z < nz; z++) left[z] = cap;
    for (int32_t i = 0; i < n; i++) w->taken[i] = 0;
    for (int32_t k = 0; k < n; k++) {
        int32_t bi = -1, bz = 0;
        u32 breg = 0;
        for (int32_t i = 0; i < n; i++) {
            u32 d1 = 0xFFFFFFFFu, d2 = 0xFFFFFFFFu;
            int32_t z1 = 0;
            if (w->taken[i]) continue;
            for (int32_t z = 0; z < nz; z++) {
                if (!left[z]) continue;
                const int32_t dy = geo[clubs[i]].lat - centre[z].lat;
                const int32_t dx = (geo[clubs[i]].lon - centre[z].lon) * 761 / 1024;   /* (cos 42 = 0.743) */
                const u32 d = (u32)(dy * dy + dx * dx);
                if (d < d1) { d2 = d1; d1 = d; z1 = z; } else if (d < d2) d2 = d;
            }
            const u32 reg = d2 == 0xFFFFFFFFu ? 0xFFFFFFFFu : d2 - d1;
            if (bi < 0 || reg > breg) { bi = i; bz = z1; breg = reg; }
        }
        w->taken[bi] = 1;
        zone[bi] = (uint8_t)bz;
        left[bz]--;
    }
    return 0;
}

uint32_t sr_kn_work_size(void)
{
    return (uint32_t)sizeof(sr_kn_work);
}

/* ---- the 'KN' block (42-s2ko): next season's cup numbers, built at the season end, read at each cup's set-up ----
 * stamp, nparts, then per part: id, n, the payload -- the Coppa Italia / Supercoppa n idents (dw, little-endian, in
 * number order), the Coppa D n bits (byte i / 8, bit i % 8) over this season's Serie D clubs in sr_kn_dorder's order,
 * 1 = in the preliminary. */
static int32_t kns_payload(uint8_t id, int32_t n)
{
    return id == SR_KNS_D ? (n + 7) / 8 : 2 * n;
}

int32_t sr_kn_dorder(const sr_kn_list *groups, int32_t ng, uint16_t *order, int32_t max)
{
    int32_t n = 0;
    if (!groups || ng < 0 || !order) return -1;
    for (int32_t g = 0; g < ng; g++)
        for (int32_t i = 0; i < groups[g].n; i++) {
            if (n >= max) return -1;
            order[n++] = groups[g].club[i];
        }
    return n;
}

int32_t sr_kns_build(uint8_t stamp, const uint16_t *ci, int32_t nci, const uint16_t *sc, int32_t nsc,
                     const uint16_t *dorder, int32_t nd, const uint16_t *dpre, int32_t npre, uint8_t *out, int32_t max)
{
    int32_t len = 2, parts = 0;
    if (!out || max < 2 || nci < 0 || nci > 255 || nsc < 0 || nsc > 255 || nd < 0 || nd > 255 || npre < 0
        || npre > nd || (nci && !ci) || (nsc && !sc) || (nd && !dorder) || (npre && !dpre)) return -1;
    for (int32_t p = 0; p < 3; p++) {
        const uint8_t id = (uint8_t)(SR_KNS_CI + p);
        const int32_t n = p == 0 ? nci : p == 1 ? nsc : nd;
        if (!n) continue;
        const int32_t need = 2 + kns_payload(id, n);
        if (len + need > max) return -1;
        out[len] = id; out[len + 1] = (uint8_t)n;
        uint8_t *d = out + len + 2;
        if (id == SR_KNS_D) {
            for (int32_t i = 0; i < (n + 7) / 8; i++) d[i] = 0;
            int32_t found = 0;
            for (int32_t i = 0; i < n; i++)
                for (int32_t k = 0; k < npre; k++)
                    if (dpre[k] == dorder[i]) { d[i / 8] |= (uint8_t)(1u << (i % 8)); found++; break; }
            if (found != npre) return -1;                       /* (a preliminary club not in this season's D) */
        } else {
            const uint16_t *v = p == 0 ? ci : sc;
            for (int32_t i = 0; i < n; i++) { d[2 * i] = (uint8_t)v[i]; d[2 * i + 1] = (uint8_t)(v[i] >> 8); }
        }
        len += need;
        parts++;
    }
    out[0] = stamp; out[1] = (uint8_t)parts;
    return len;
}

/* the part id's payload and n, or -1: no block, another season's, malformed, no such part */
static int32_t kns_find(const uint8_t *blk, int32_t len, uint8_t stamp, uint8_t id, const uint8_t **data)
{
    if (!blk || len < 2 || blk[0] != stamp || blk[1] == 0) return -1;
    int32_t at = 2;
    for (int32_t p = 0; p < blk[1]; p++) {
        if (at + 2 > len) return -1;
        const uint8_t pid = blk[at], n = blk[at + 1];
        if (pid < SR_KNS_CI || pid > SR_KNS_D) return -1;
        const int32_t pl = kns_payload(pid, n);
        if (at + 2 + pl > len) return -1;
        if (pid == id) { *data = blk + at + 2; return n; }
        at += 2 + pl;
    }
    return -1;
}

int32_t sr_kns_idents(const uint8_t *blk, int32_t len, uint8_t stamp, uint8_t id, uint16_t *out, int32_t max)
{
    const uint8_t *d;
    if (id != SR_KNS_CI && id != SR_KNS_SC) return -1;
    const int32_t n = kns_find(blk, len, stamp, id, &d);
    if (n <= 0 || n > max || !out) return -1;
    for (int32_t i = 0; i < n; i++) out[i] = (uint16_t)(d[2 * i] | d[2 * i + 1] << 8);
    return n;
}

int32_t sr_kns_dpre(const uint8_t *blk, int32_t len, uint8_t stamp, const uint16_t *dorder, int32_t nd,
                    uint16_t *pre, uint16_t *rest, int32_t *npre)
{
    const uint8_t *d;
    const int32_t n = kns_find(blk, len, stamp, SR_KNS_D, &d);
    if (n <= 0 || n != nd || !dorder || !pre || !rest || !npre) return -1;   /* (n: another D than this season's) */
    int32_t a = 0, b = 0;
    for (int32_t i = 0; i < n; i++) {
        if (d[i / 8] >> (i % 8) & 1) pre[a++] = dorder[i];
        else rest[b++] = dorder[i];
    }
    *npre = a;
    return n;
}
