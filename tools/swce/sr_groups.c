/*
 * sr_groups.c -- leagues with parallel groups at the season end: the SWOS 96/97 Mod's
 * tools/gplay.c pg_one, pg_level, pg_room, pg_a2, pg_ban and pg_make_room (4.0.5: two choices of
 * group per level; 4.0.6's pg_a2 guard), as ported to OpenSWOS (its src/league_groups.c) and
 * checked against the Mod's C (tests/rules/check.sh).
 *
 * Changed in the port: typed tables (sr_pg_league) instead of the Mod's packed byte table, a club
 * by its index in the table instead of its global number, the swapped pool slots passed in
 * (entering) instead of ri_og; a league past the limits refused instead of clamped.
 *
 * Copyright (c) 2026 Davide Lorigliola, Ben Baker. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t u8;

enum { PL = SR_PG_LEVELS, PG = SR_PG_GROUPS, NONE = 0xFF };

/* The level of division d (past the last one: the level below the chain, nl; above the first: -1). */
static int level_of(int d, int nl, const sr_pg_level *lv)
{
    if (d >= lv[nl - 1].first + lv[nl - 1].groups) return nl;
    for (int l = nl - 1; l >= 0; l--) if (d >= lv[l].first) return l;
    return -1;                                  /* (above the chain: off it, as a club below it is) */
}

/* group a, else the nearest one with room -- at equal distance the later one (else a) */
static int with_room(int a, const sr_pg_level *L, const u8 *occ)
{
    for (int k = 0; k < PG; k++) {
        if (a + k < L->groups && occ[a + k] < L->size[a + k]) return a + k;
        if (a - k >= 0 && occ[a - k] < L->size[a - k]) return a - k;
    }
    return a;
}

/* An area byte's 2nd choice: 15 none, 14 any group, else the group. 4.0.6's guard: a 2nd choice
 * past G, or a ban with no 2nd choice ((h & 7) == 0), is none -- 4.0.5 indexed group -1. */
#define A1(b) ((b) & 15)
static int area2(int b)
{
    const int h = b >> 4;
    return h == 0 || h == 15 ? 15 : h == 14 ? 14 : (h & 7) == 0 ? 15 : (h & 7) - 1;
}
static int banned(int b) { const int h = b >> 4; return h != 0 && h < 14 && (h & 8); }

/* Group a of level tl is full: a club placed in it that can leave moves (the Mod's pg_make_room) -- a
 * second team first (to the group with room nearest to a), else a club out of its 1st choice whose
 * 1st choice has room, else one out of both choices whose 2nd has room, else one in its 1st choice
 * whose 2nd has room, else a club free to go anywhere (two choices, no ban) to the nearest group
 * with room. 1: one moved. */
static int make_room(const sr_pg_league *pg, int8_t *new_off, const u8 *pend, int self, int tl, int a,
                     u8 (*occ)[PG], int p)
{
    const sr_pg_level *L = &pg->level[tl];
    if (p >= SR_PG_PARALLEL) return 0;
    for (int pass = 0; pass < (L->chain ? 4 : 5); pass++)   /* (a chain level: no move out of a club's choices) */
        for (int j = 0; j < pg->clubs; j++) {
            const sr_pg_club *f = &pg->club[j];
            if (j == self || (pend[j >> 3] & (1 << (j & 7))) || new_off[j] + f->base != L->first + a) continue;
            const int b = f->area[p], h1 = A1(b), h2 = area2(b);
            int w = 99;
            if (pass == 0 ? h2 == 14 : pass == 4 && h2 < L->groups && !banned(b))
                w = with_room(a, L, occ[tl]);
            else if (h2 != 14)
                w = pass == 1 ? (h1 != a ? h1 : 99) : pass == 2 ? (h1 != a && h2 != a ? h2 : 99)
                  : pass == 3 && h1 == a ? h2 : 99;
            if (w == a || w >= L->groups || occ[tl][w] >= L->size[w]) continue;
            occ[tl][w]++;
            occ[tl][a]--;
            new_off[j] = (int8_t)(L->first + w - f->base);
            return 1;
        }
    return 0;
}

/* the club's other choice than w at level p (or none, GROUPS) */
static int other_choice(int b, int w, int groups)
{
    const int h1 = A1(b), h2 = area2(b);
    if (banned(b) || h2 == 14 || h2 >= groups || h1 >= groups) return groups;
    return h1 == w ? h2 : h2 == w ? h1 : groups;
}

/* a club placed in group g that can go to its other choice, which has room: moved, 1 */
static int step_aside(const sr_pg_league *pg, int8_t *new_off, const u8 *pend, int skip, int tl, int g,
                      u8 (*occ)[PG], int p)
{
    const sr_pg_level *L = &pg->level[tl];
    for (int k = 0; k < pg->clubs; k++) {
        const sr_pg_club *f = &pg->club[k];
        if (k == skip || (pend[k >> 3] & (1 << (k & 7))) || new_off[k] + f->base != L->first + g) continue;
        const int y = other_choice(f->area[p], g, L->groups);
        if (y >= L->groups || occ[tl][y] >= L->size[y]) continue;
        occ[tl][y]++; occ[tl][g]--;
        new_off[k] = (int8_t)(L->first + y - f->base);
        return 1;
    }
    return 0;
}

/* level.chain: room in group w (full) one step deeper -- a club of w goes to its other choice x
 * (full too) once a club of x steps aside to its own other choice; every move within the clubs'
 * own choices. 1: room made in w. */
static int chain_room(const sr_pg_league *pg, int8_t *new_off, const u8 *pend, int self, int tl, int w,
                      u8 (*occ)[PG], int p)
{
    const sr_pg_level *L = &pg->level[tl];
    for (int j = 0; j < pg->clubs; j++) {
        const sr_pg_club *f = &pg->club[j];
        if (j == self || (pend[j >> 3] & (1 << (j & 7))) || new_off[j] + f->base != L->first + w) continue;
        const int x = other_choice(f->area[p], w, L->groups);
        if (x >= L->groups || !step_aside(pg, new_off, pend, j, tl, x, occ, p)) continue;
        occ[tl][x]++; occ[tl][w]--;
        new_off[j] = (int8_t)(L->first + x - f->base);
        return 1;
    }
    return 0;
}

int32_t sr_pg_season(const sr_pg_league *pg, const int8_t *old_off, int8_t *new_off, const uint8_t *entering)
{
    u8 occ[PL][PG], pidx[PL], pend[SR_CLUB_SLOTS / 8];
    int np = 0;
    if (!pg || !pg->level || !pg->club || pg->levels < 1 || pg->levels > PL || pg->clubs > SR_CLUB_SLOTS)
        return -1;
    const int nl = pg->levels;
    for (int l = 0; l < nl; l++) {
        const sr_pg_level *L = &pg->level[l];
        if (L->groups < 1 || L->groups > PG) return -1;
        pidx[l] = L->groups > 1 ? (u8)np++ : NONE;
        for (int g = 0; g < PG; g++) occ[l][g] = 0;
    }
    if (np > SR_PG_PARALLEL) return -1;
    for (int i = 0; i < SR_CLUB_SLOTS / 8; i++) pend[i] = 0;

    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < pg->clubs; i++) {
            const sr_pg_club *c = &pg->club[i];
            const int in = entering && entering[i];   /* (a new identity from below: */
            const int o = in ? pg->level[nl - 1].first + pg->level[nl - 1].groups : old_off[i] + c->base;
            const int n = in ? pg->level[nl - 1].first : new_off[i] + c->base;   /* the lowest level) */
            const int lo = level_of(o, nl, pg->level);
            if (pass == 1) {                    /* into a level of groups */
                if (!(pend[i >> 3] & (1 << (i & 7)))) continue;
                pend[i >> 3] &= (u8)~(1 << (i & 7));
                const int tl = n < o ? lo - 1 : lo + 1;
                const sr_pg_level *L = &pg->level[tl];
                const int p = pidx[tl];
                const int ab = p < np ? c->area[p] : NONE;
                const int area = A1(ab), second = area2(ab);
                const int a = area < L->groups ? area : ab == NONE ? L->groups / 2 : L->groups - 1;
                int to = -1;
                for (int k = 0; k < 2 && to < 0; k++) {     /* its 1st choice, then its 2nd: room, else made */
                    const int w = k ? second : area;
                    if (w >= L->groups) continue;
                    if (occ[tl][w] < L->size[w] || make_room(pg, new_off, pend, i, tl, w, occ, p)) to = w;
                }
                for (int k = 0; k < 2 && to < 0 && L->chain; k++) {   /* (not in the Mod: one step deeper) */
                    const int w = k ? second : area;
                    if (w < L->groups && chain_room(pg, new_off, pend, i, tl, w, occ, p)) to = w;
                }
                if (to < 0) to = with_room(a, L, occ[tl]);  /* (a second team, or no choice fits: nearest) */
                occ[tl][to]++;
                new_off[i] = (int8_t)(L->first + to - c->base);
                continue;
            }
            const int tl = n < o ? lo - 1 : n > o ? lo + 1 : lo;
            if (tl < 0 || tl >= nl) continue;   /* (off the chain, or into the reserve: as moved) */
            const sr_pg_level *L = &pg->level[tl];
            if (tl == lo) {                     /* staying: counted in its group */
                if (o - L->first < L->groups) occ[lo][o - L->first]++;
            } else if (L->groups == 1)
                new_off[i] = (int8_t)(L->first - c->base);
            else
                pend[i >> 3] |= (u8)(1 << (i & 7));
        }
    return 0;
}

/* the flexible order: rank (north first), then ident (else the index) */
static int north_of(int i, int j, const uint8_t *rank, const uint16_t *ident)
{
    if (rank[i] != rank[j]) return rank[i] < rank[j];
    return ident ? ident[i] < ident[j] : i < j;
}

int32_t sr_pg_realloc(const sr_pg_league *pg, int32_t l, const uint8_t *rank, const uint16_t *ident,
                      int8_t *new_off)
{
    static uint16_t on[SR_CLUB_SLOTS];          /* (the level's clubs; a strict club's group in grp) */
    static u8 grp[SR_CLUB_SLOTS], flex[SR_CLUB_SLOTS];
    int n = 0, p = 0, crossed = 0, cnt[2] = { 0, 0 };
    if (!pg || !pg->level || !pg->club || !rank || !new_off || l < 0 || l >= pg->levels || pg->levels > PL
        || pg->clubs > SR_CLUB_SLOTS)                          /* (sr_pg_season's limits) */
        return -1;
    const sr_pg_level *L = &pg->level[l];
    if (L->groups != 2) return -1;
    for (int k = 0; k < l; k++) if (pg->level[k].groups > 1) p++;
    if (p >= SR_PG_PARALLEL) return -1;
    for (int i = 0; i < pg->clubs; i++) {
        const int d = new_off[i] + pg->club[i].base - L->first;
        if (d < 0 || d >= 2) continue;
        const int b = pg->club[i].area[p], h1 = A1(b), h2 = area2(b);
        on[n] = (uint16_t)i;
        flex[n] = rank[i] != SR_RANK_NONE && !banned(b) && (h2 == 14 || (h2 < 2 && h2 != h1));
        grp[n] = (u8)(h1 < 2 ? h1 : d);     /* (no area in the level: where it is) */
        if (!flex[n]) cnt[grp[n]]++;
        n++;
    }
    if (n > L->size[0] + L->size[1]) return -1;
    for (int i = 1; i < n; i++)                 /* every club by rank: the order a crossing or a fill takes */
        for (int j = i; j > 0 && north_of(on[j], on[j - 1], rank, ident); j--) {
            uint16_t x = on[j]; on[j] = on[j - 1]; on[j - 1] = x;
            u8 y = grp[j]; grp[j] = grp[j - 1]; grp[j - 1] = y;
            y = flex[j]; flex[j] = flex[j - 1]; flex[j - 1] = y;
        }
    for (int j = n - 1; j >= 0 && cnt[0] > L->size[0]; j--)        /* too many strict northerners: */
        if (!flex[j] && grp[j] == 0) { grp[j] = 1; cnt[0]--; cnt[1]++; crossed++; }   /* the southernmost cross */
    for (int j = 0; j < n && cnt[1] > L->size[1]; j++)
        if (!flex[j] && grp[j] == 1) { grp[j] = 0; cnt[1]--; cnt[0]++; crossed++; }
    int room0 = L->size[0] - cnt[0];            /* the flexible ones, north first, fill the northern group */
    for (int j = 0; j < n; j++) {
        if (!flex[j]) continue;
        grp[j] = room0 > 0 ? 0 : 1;
        if (room0 > 0) room0--;
    }
    for (int j = 0; j < n; j++) {
        const int i = on[j];
        new_off[i] = (int8_t)(L->first + grp[j] - pg->club[i].base);
    }
    return crossed;
}
