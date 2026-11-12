/*
 * sr_post.c -- the season's moves: each club's one-level move from its record's place and the
 * play-offs, then the B-team rules (the SWOS 96/97 Mod's tools/gplay.c sec_post), as ported to
 * OpenSWOS (its src/league_playoffs.c) and checked against the Mod's C (tests/rules/check.sh).
 *
 * The Mod works on division numbers (SEC_COPY - SEC_SLT); OpenSWOS and the library on levels, a
 * level of groups counting as one -- the same moves.
 *
 * Copyright (c) 2026 Davide Lorigliola, Ben Baker. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;
typedef int8_t   s8;

static int32_t sign(int32_t x) { return x < 0 ? -1 : x > 0; }

static int32_t level_of(const sr_levels *lv, int32_t d)
{
    if (!lv || !lv->levels)
        return d;
    for (int32_t l = lv->levels - 1; l >= 0; l--)
        if (d >= lv->first[l])
            return l;
    return 0;
}

static int32_t find_club(const sr_state *st, u16 g, int32_t *d, int32_t *k)
{
    for (*d = 0; *d < st->t.nd; (*d)++)
        for (*k = 0; *k < st->t.n[*d]; (*k)++)
            if (st->t.t[*d][*k].glob == g)
                return 1;
    return 0;
}

/* B team at division db: going up one level is not allowed -- above `top`, or into or
 * above its first team's level after this season's moves */
static int32_t up_bad(const sr_state *st, const sr_league *lp, const sr_levels *lv, int32_t i, int32_t db, u16 base)
{
    const int32_t target = level_of(lv, db) - 1;
    int32_t df, kf;
    if (lp->second_top != 0xFF && target < lp->second_top)
        return 1;
    return lp->second[i][1] != 0xFF && find_club(st, (u16)(base + lp->second[i][1]), &df, &kf) &&
           target <= level_of(lv, df) + st->want[df][kf];
}

/* a club skipped for a promotion place: a B team that may not go up */
static int32_t ineligible(const sr_state *st, const sr_league *lp, const sr_levels *lv, int32_t d, int32_t k, u16 base)
{
    for (int32_t i = 0; i < lp->seconds; i++)
        if (st->t.t[d][k].glob == (u16)(base + lp->second[i][0]))
            return !(lp->second_flags & 1) || up_bad(st, lp, lv, i, d, base);
    return 0;
}

/* a row that is one of the league's B teams */
static int32_t is_b(const sr_state *st, const sr_league *lp, int32_t d, int32_t k, u16 base)
{
    for (int32_t i = 0; i < lp->seconds; i++)
        if (st->t.t[d][k].glob == (u16)(base + lp->second[i][0]))
            return 1;
    return 0;
}

/* the best placed relegated of division d stays (not k; with v42, no B team) */
static void stays(sr_state *st, const sr_league *lp, int32_t d, int32_t k, int32_t v42, u16 base)
{
    for (int32_t j = 0; j < st->t.n[d]; j++)
        if (j != k && st->want[d][j] > 0 && !(v42 && is_b(st, lp, d, j, base))) { st->want[d][j] = 0; break; }
}

static void b_exit(sr_state *st, u16 g)
{
    for (int32_t i = 0; i < st->b_exits; i++)
        if (st->b_exit[i] == g)
            return;
    if (st->b_exits < SR_B_EXITS)
        st->b_exit[st->b_exits++] = g;
}

void sr_b_teams(sr_state *st, const sr_league *lp, const sr_levels *lv, uint16_t base)
{
    const int32_t v42 = lp->second_floor != 0;
    const int32_t lowestLevel = v42 ? lp->second_floor : lv && lv->levels ? lv->levels - 1 : lp->divisions - 1;
    st->b_exits = 0;
    for (int32_t i = 0; i < lp->seconds; i++) {
        const u16 gb = (u16)(base + lp->second[i][0]);
        int32_t db, kb, df = 0, kf = 0;
        if (!find_club(st, gb, &db, &kb))
            continue;
        const int32_t lb = level_of(lv, db), nb = lb + st->want[db][kb], dl = st->want[db][kb];
        const int32_t rf = lp->second[i][1] != 0xFF && find_club(st, (u16)(base + lp->second[i][1]), &df, &kf);
        const int32_t nf = rf ? level_of(lv, df) + st->want[df][kf] : -1;
        const int32_t lowest = lb == lowestLevel;
        const int32_t coupled = rf && nf >= (nb < lb ? lb : nb) && nb <= lb;
        if (coupled && (!lowest || (lp->second_flags & 2))) {
            st->want[db][kb] = 1;               /* the first team in its level: one down */
            if (!lowest)                        /* the best placed relegated of its division stays */
                stays(st, lp, db, kb, v42, base);
            else if (v42 && dl <= 0)            /* (out of the league from the floor) */
                b_exit(st, gb);
        } else if (nb < lb && (coupled || up_bad(st, lp, lv, i, db, base))) {
            st->want[db][kb] = 0;               /* up, not allowed: held */
        } else
            continue;
        if (nb < lb)                            /* its promotion: the next club of its division */
            for (int32_t k = 0; k < st->t.n[db]; k++) {
                if (k == kb || st->want[db][k] != 0 || ineligible(st, lp, lv, db, k, base))
                    continue;
                st->want[db][k] = (s8)dl;
                break;
            }
    }
    if (!v42)
        return;
    /* 4.2: the final guard -- a B team at or above its first team's new level (or its first team below the league)
     * goes one below it: one level down, or out of the league when that is below the floor. An invariant, not a case
     * list: it also mends a state an old save or another rule left. */
    for (int32_t i = 0; i < lp->seconds; i++) {
        const u16 gb = (u16)(base + lp->second[i][0]);
        int32_t db, kb, df = 0, kf = 0;
        if (!find_club(st, gb, &db, &kb) || lp->second[i][1] == 0xFF)
            continue;
        const int32_t lb = level_of(lv, db), w = st->want[db][kb], nb = lb + w;
        const int32_t rf = find_club(st, (u16)(base + lp->second[i][1]), &df, &kf);
        const int32_t target = rf ? level_of(lv, df) + st->want[df][kf] + 1 : lowestLevel + 1;
        if (nb >= target)
            continue;
        if (w < 0) {                            /* (its promotion: back to the next club, as held) */
            st->want[db][kb] = 0;
            for (int32_t k = 0; k < st->t.n[db]; k++)
                if (k != kb && st->want[db][k] == 0 && !ineligible(st, lp, lv, db, k, base)) { st->want[db][k] = -1; break; }
        }
        if (lb + st->want[db][kb] >= target)
            continue;
        if (st->want[db][kb] == 0) {
            st->want[db][kb] = 1;
            if (lb < lowestLevel)
                stays(st, lp, db, kb, 1, base);
        }
        if (target > lowestLevel && (lp->second_flags & 2) && !(lb == lowestLevel && w > 0))
            b_exit(st, gb);                     /* (below the floor: out of the league; not a relegation by place) */
    }
}

void sr_final_moves(sr_state *st, const sr_league *lg, const sr_levels *lv, uint16_t base)
{
    for (int32_t d = 0; d < lg->divisions && d < SR_DIVS; d++) {
        const int32_t n = st->t.n[d];
        for (int32_t k = 0; k < n; k++) {
            const u16 g = st->t.t[d][k].glob;
            int32_t want = 0;
            if (k < lg->promoted[d] && d > 0)
                want = -1;
            else if (k >= n - lg->relegated[d])
                want = 1;
            for (int32_t i = 0; i < st->nmv; i++)
                if (st->mv[i].glob == g)
                    want += st->mv[i].delta;
            st->want[d][k] = (s8)sign(want);
        }
    }
    sr_b_teams(st, lg, lv, base);
}
