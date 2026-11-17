/* 4.2 preseason friendlies, the chooser's selection state. THE RULES are tools/frcsel.h's header comment.
   Details the header leaves open:
   - a refusal code = fr_pick's return code (FR_NOSELF .. FR_NOPOOL: -1 .. -3) or, for FR_GIVEN, 16 + the first
     non-zero why[] (so 16 + FR_E_*: 15 .. 9); frc_msg() is the one decoder.
   - frc_trial never changes the state; it is fr_given (the pick's own given-list check for one entry, no automatic
     fill: MC 16/11, the ONLY per-club query of the page) for `word` in slot k among the page's other rows; band =
     fr_given's (the club's band also when it is refused, 0xFF when it is no club). The rows after k are asked too
     (fr_pick reports a duplicate / a full cache on the LATER entry): 0 = fr_pick would accept the whole given list
     (the automatic rows can still fail: FR_NOPOOL, told by the real change).
   - a level outside 0..3 in FR_ST cannot happen (2 bits). */
#include "frcsel.h"

static const uint16_t frc_fill[FRC_LEVELS] = {          /* level -> the given[] word of an empty slot */
    FR_NONE, FR_AUTO(FR_WEAKER), FR_AUTO(FR_SIMILAR), FR_AUTO(FR_STRONGER)
};

static void frc_given(const FrcSel *s, uint16_t *given)
{
    uint32_t k;
    for (k = 0; k < 4; k++)
        given[k] = s->club[k] != FR_NONE ? s->club[k] : frc_fill[s->level];
}

static int frc_pick(const FrcSel *s, const uint16_t *given, FrPick *out)
{
    const FrcCtx *c = s->c;
    int rc = fr_pick(c->frss, c->len, c->world, c->self, c->self2, given, c->avoid, c->navoid, c->room, c->season,
                     c->seed, s->venues == FRC_VENUES_AUTO ? c->nhome : FR_VENUES(s->venues), out);
    uint32_t k;
    if (rc == FR_GIVEN)
        for (k = 0; k < 4; k++)
            if (out->why[k])
                return 16 + out->why[k];
    return rc;
}

/* the one path of every change: try `n`; accepted -> it is the state, refused -> *s stays, msg = why */
static int frc_try(FrcSel *s, FrcSel *n)
{
    uint16_t given[4];
    int rc;
    frc_given(n, given);
    rc = frc_pick(n, given, &n->out);
    if (rc) {
        s->msg = (int8_t)rc;
        return rc;
    }
    n->msg = 0;
    *s = *n;
    return 0;
}

int frc_init(FrcSel *s, const FrcCtx *c)
{
    FrcSel n;
    uint32_t k;
    n.c = c;
    for (k = 0; k < 4; k++)
        n.club[k] = FR_NONE;
    n.level = c->frst[FRC_ST_OFF] >> FRC_ST_SHIFT & 3;
    n.venues = FRC_VENUES_AUTO;
    return frc_try(s, &n);
}

int frc_set_level(FrcSel *s, int dir)
{
    FrcSel n = *s;
    n.level = (uint8_t)((s->level + (dir < 0 ? FRC_LEVELS - 1 : 1)) % FRC_LEVELS);
    return frc_try(s, &n);
}

int frc_set_club(FrcSel *s, uint32_t k, uint16_t word)
{
    FrcSel n = *s;
    n.club[k & 3] = word;
    return frc_try(s, &n);
}

int frc_swap_venue(FrcSel *s, uint32_t k)
{
    FrcSel n = *s;
    uint32_t home = s->out.home & 15, d, j;
    k &= 3;
    if (home != 3 && home != 5 && home != 6 && home != 9 && home != 10 && home != 12)
        return 0;                                       /* not 2 + 2 (the engine's nhome is not 2): no swap */
    for (d = 1; d < 4; d++) {
        j = k - d;                                      /* the lower slot first */
        if (j >= 4 || !((home >> j ^ home >> k) & 1)) {
            j = k + d;
            if (j >= 4 || !((home >> j ^ home >> k) & 1))
                continue;
        }
        n.venues = (uint8_t)(home ^ 1u << k ^ 1u << j);
        return frc_try(s, &n);
    }
    return 0;
}

int frc_trial(const FrcSel *s, uint32_t k, uint16_t word, uint8_t *band)
{
    const FrcCtx *c = s->c;
    uint16_t given[4];
    uint32_t j;
    uint8_t b2;
    int rc;
    k &= 3;
    frc_given(s, given);
    given[k] = word;
    rc = fr_given(c->frss, c->len, c->world, c->self, c->self2, given, k, c->room, band);
    for (j = k + 1; !rc && j < 4; j++)                  /* (a later row's club refused because of this one: the same
                                                           club there, or no room left for it) */
        rc = fr_given(c->frss, c->len, c->world, c->self, c->self2, given, j, c->room, &b2);
    return rc ? 16 + rc : 0;
}

void frc_result(const FrcSel *s, uint16_t given[4], uint8_t *venues)
{
    uint8_t *b = &s->c->frst[FRC_ST_OFF];
    frc_given(s, given);
    *venues = s->venues;
    *b = (uint8_t)((*b & ~(3u << FRC_ST_SHIFT)) | (uint32_t)s->level << FRC_ST_SHIFT);
}

int frc_msg(int code)
{
    switch (code) {
    case 0:                 return FRC_M_NONE;
    case 16 + FR_E_DUP:     return FRC_M_DUP;
    case 16 + FR_E_ROOM:    return FRC_M_ROOM;
    case FR_NOPOOL:         return FRC_M_NOPOOL;
    default:                return FRC_M_CLUB;          /* NOCLUB / SELF / BTEAM (+ the codes a page cannot cause) */
    }
}
