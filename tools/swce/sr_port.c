/*
 * sr_port.c -- the fixture port (docs/fixture-port.md): the engine side of every non-league fixture. Producers
 * queue fixtures (sr_port_add, the rules checked there); at each calendar advance the exe simulates the others
 * (sr_port_advance) and asks for the career club's next one (sr_port_poll, lookahead 1), installs it in slot 4,
 * plays it and submits its result (sr_port_result_in), which the engine checks against its own reading. The FP
 * save section is version 0, a draft, until the slot-4 probe answers Q1 / Q4.
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;

#define NOGOAL 0xFF

void sr_port_init(sr_port *p, uint16_t career, uint16_t unit, uint16_t s4first, uint32_t pack_hash)
{
    u8 *b = (u8 *)p;
    for (u32 i = 0; i < sizeof *p; i++) b[i] = 0;   /* (no memset: no libcalls on the DOS build) */
    p->career = career; p->unit = unit; p->s4first = s4first; p->pack_hash = pack_hash;
}

static int shares(const sr_port_fixture *a, const sr_port_fixture *b)
{
    return a->home == b->home || a->home == b->away || a->away == b->home || a->away == b->away;
}

/* the unit a fixture starting at u is installed in: the game's advance before u */
static int32_t inst(const sr_port_host *h, uint16_t u)
{
    return h && h->prev_unit ? h->prev_unit(h->ctx, u) : (int32_t)u - 1;
}

/* rule 6: does the fixture meet a slot-4 window reserved for either club's division? Outside one = done before its
   build unit B (unit2 < B), or installed at or after its last match E (the advance before unit1 >= E: the advance
   from E runs after E's matches, probe fprobe-clash98: installed at the Supercoppa's E 93, played at 98): no slot clear */
static int reserved(const sr_port_host *h, uint16_t s4first, const sr_port_fixture *x)
{
    uint16_t w[SR_PORT_WINDOWS][2];
    for (int32_t s = 0; s < 2; s++) {
        int32_t n = 1;
        w[0][0] = s4first; w[0][1] = SR_PORT_NONE;
        if (h && h->slot4_windows) n = h->slot4_windows(h->ctx, s ? x->away : x->home, w, SR_PORT_WINDOWS);
        if (n > SR_PORT_WINDOWS || n < 0) return 1;    /* (windows it could not hand over: refused, never unread) */
        for (int32_t k = 0; k < n; k++)
            if (!(x->unit2 < w[k][0] || inst(h, x->unit1) >= (int32_t)w[k][1])) return 1;
    }
    return 0;
}

/* the rules over f[0 .. n), rule 2 only for f[from ..) (the fixtures not yet played), rules 1 and 6 (the league's
   matches, the slot-4 windows: live data) only for a fixture not PLAYED (state NULL: none played). nbad NULL: the
   first broken rule; else every fixture's (*nbad of them, the first max_ids match ids into ids), the first's code */
static int32_t check(const sr_port_fixture *f, int32_t n, int32_t from, const uint8_t *state, uint16_t unit,
                     uint16_t s4first, const sr_port_host *h, int32_t *bad, int32_t *nbad, uint32_t *ids,
                     int32_t max_ids)
{
    int32_t first = 0;
    if (nbad) *nbad = 0;
    for (int32_t i = 0; i < n; i++) {
        const int live = !state || state[i] != SR_PORT_PLAYED;
        const sr_port_fixture *x = &f[i];
        int32_t e = 0;
        if (x->legs != 1 && x->legs != 2) e = SR_PORT_E_R3;
        else if (x->level < SR_PORT_LV_ET_PENS || x->level > SR_PORT_LV_AWAY_BETTER ||
                 (x->legs == 1 && (x->level == SR_PORT_LV_AWAY_PENS || x->level == SR_PORT_LV_AWAY_BETTER)))
            e = SR_PORT_E_LEVEL;            /* (away goals need two legs) */
        else if (!x->match_id || ((x->flags & SR_PORT_F_REPLAY) && !x->prev_id)) e = SR_PORT_E_ID;
        else if (x->neutral && x->legs != 1) e = SR_PORT_E_R3;
        else if (x->home == SR_PORT_NONE || x->away == SR_PORT_NONE || x->home == x->away) e = SR_PORT_E_R4;
        else if (i >= from && x->unit1 <= unit) e = SR_PORT_E_R2;
        else if ((x->legs == 2 ? x->unit2 <= x->unit1 : x->unit2 != x->unit1) || x->unit2 == SR_PORT_NONE)
            e = SR_PORT_E_R3;                   /* (SR_PORT_NONE is no unit: fuzz_lib's find, a tie at FFFFh a load refused) */
        else if (live && reserved(h, s4first, x)) e = SR_PORT_E_SLOT4_RESERVED;
        for (int32_t j = 0; !e && j < i; j++) {
            const sr_port_fixture *y = &f[j];
            if (y->match_id == x->match_id) e = SR_PORT_E_ID;
            else if (shares(x, y) && !(y->unit2 < inst(h, x->unit1) || x->unit2 < inst(h, y->unit1)))
                e = SR_PORT_E_R5;           /* (the later one is installed over slot 4 at the advance before it: the
                                               earlier ends strictly before that; any club's, a job change keeps it) */
        }
        if (!e && live && h && h->league_plays)
            for (int32_t s = 0; s < 2 && !e; s++)
                for (int32_t k = 0; k < x->legs && !e; k++)
                    if (h->league_plays(h->ctx, s ? x->away : x->home, k ? x->unit2 : x->unit1)) e = SR_PORT_E_R1;
        if (e) {
            if (!first) {
                first = e;
                if (bad) *bad = i;
            }
            if (!nbad) return e;
            if (*nbad < max_ids && ids) ids[*nbad] = x->match_id;
            ++*nbad;
        }
    }
    return first;
}

int32_t sr_port_check(const sr_port_fixture *f, int32_t n, uint16_t unit, uint16_t s4first,
                      const sr_port_host *h, int32_t *bad)
{
    if (!f || n < 0 || n > SR_PORT_MAX) return SR_PORT_E_ARGS;
    return check(f, n, 0, 0, unit, s4first, h, bad, 0, 0, 0);
}

int32_t sr_port_check_queue(const sr_port_fixture *f, int32_t n, int32_t from, const uint8_t *state, uint16_t unit,
                            uint16_t s4first, const sr_port_host *h, int32_t *bad)
{
    if (!f || n < 0 || n > SR_PORT_MAX || from < 0 || from > n) return SR_PORT_E_ARGS;
    return check(f, n, from, state, unit, s4first, h, bad, 0, 0, 0);
}

int32_t sr_port_add(sr_port *p, const sr_port_host *h, const sr_port_fixture *f)
{
    if (!p || !f) return SR_PORT_E_ARGS;
    if (p->n >= SR_PORT_MAX) return SR_PORT_E_FULL;
    p->f[p->n] = *f;
    p->state[p->n] = SR_PORT_QUEUED;                    /* (counted only on success) */
    const int32_t e = check(p->f, p->n + 1, p->n, p->state, p->unit, p->s4first, h, 0, 0, 0, 0);
    if (e) return e;
    p->state[p->n++] = SR_PORT_QUEUED;
    return 0;
}

int32_t sr_port_winner(const sr_port_fixture *f, const sr_port_result *r)
{
    if (!f || !r || r->match_id != f->match_id) return -1;
    if (r->status == 1 || r->status == 2) return r->status == 1 ? 1 : 0;   /* (a forfeit: the other side) */
    if (r->status) return -1;
    const int two = f->legs == 2, lv = f->level;
    /* side 0 = the fixture's home (leg 1's host); leg 2 and the deciding leg's extra time / penalties as played:
       in a two-leg tie leg 2's home is side 1 */
    const int a = r->g90[0] + (two ? r->g90b[1] : 0), b = r->g90[1] + (two ? r->g90b[0] : 0);
    const int et = r->get[0] != NOGOAL, pens = r->pens[0] != NOGOAL;
    const int eta = et ? r->get[two ? 1 : 0] : 0, etb = et ? r->get[two ? 0 : 1] : 0;
    const int pa = pens ? r->pens[two ? 1 : 0] : 0, pb = pens ? r->pens[two ? 0 : 1] : 0;
    const int away = two && (lv == SR_PORT_LV_AWAY_PENS || lv == SR_PORT_LV_AWAY_BETTER);
    if (!two && (r->g90b[0] || r->g90b[1])) return -1;
    if ((r->get[0] == NOGOAL) != (r->get[1] == NOGOAL) || (r->pens[0] == NOGOAL) != (r->pens[1] == NOGOAL)) return -1;
    if (a != b) return et || pens ? -1 : a < b;                     /* (decided in 90': nothing after) */
    if (away && r->g90b[1] != r->g90[1])                            /* (away goals: side 0's in leg 2, side 1's in 1) */
        return et || pens ? -1 : r->g90b[1] < r->g90[1];
    if (lv == SR_PORT_LV_ET_PENS || lv == SR_PORT_LV_ET_BETTER || lv == SR_PORT_LV_AWAY_PENS) {
        if (!et) return -1;
        if (eta != etb) return pens ? -1 : eta < etb;
        if (away && eta) return pens ? -1 : 0;                      /* (level after e.t. with goals: side 0's away) */
    } else if (et) return -1;                                       /* (PENS / AWAY_BETTER: no extra time) */
    if (lv == SR_PORT_LV_ET_BETTER || lv == SR_PORT_LV_AWAY_BETTER) return pens ? -1 : 0;   /* (the listed side) */
    if (!pens || pa == pb) return -1;
    return pa < pb;
}

static int32_t take(sr_port *p, const sr_port_host *h, int32_t i, const sr_port_result *r)
{
    const int32_t w = sr_port_winner(&p->f[i], r);
    if (w < 0) return SR_PORT_E_RESULT;
    if (w != r->winner) return SR_PORT_E_WINNER;    /* (refused with the fixture, never overridden) */
    p->r[i] = *r;
    p->state[i] = SR_PORT_PLAYED;
    if (h && h->done) h->done(h->ctx, &p->f[i], &p->r[i]);
    return 0;
}

static int32_t simulate(sr_port *p, const sr_port_host *h, int32_t i)
{
    sr_port_result r;
    u8 *b = (u8 *)&r;
    for (u32 k = 0; k < sizeof r; k++) b[k] = 0;
    if (!h || !h->sim || h->sim(h->ctx, &p->f[i], &r)) return SR_PORT_E_SIM;
    r.match_id = p->f[i].match_id;
    return take(p, h, i, &r);
}

static int career_in(const sr_port *p, int32_t i) { return p->f[i].home == p->career || p->f[i].away == p->career; }

int32_t sr_port_advance(sr_port *p, const sr_port_host *h, uint16_t unit)
{
    int32_t played = 0;
    if (!p) return SR_PORT_E_ARGS;
    for (int32_t i = 0; i < p->n; i++) {
        if (p->state[i] != SR_PORT_QUEUED || career_in(p, i) || p->f[i].unit2 > unit) continue;
        const int32_t e = simulate(p, h, i);
        if (e) return e;
        played++;
    }
    if (unit > p->unit) p->unit = unit;
    return played;
}

int32_t sr_port_poll(sr_port *p, const sr_port_host *h, uint16_t unit, uint16_t next_unit, sr_port_fixture *f)
{
    int32_t best = -1;
    if (!p || !f) return SR_PORT_E_ARGS;
    for (int32_t i = 0; i < p->n; i++)
        if (p->pending && p->f[i].match_id == p->pending && p->state[i] == SR_PORT_INSTALLED) { *f = p->f[i]; return 1; }
    for (int32_t i = 0; i < p->n; i++)
        if (p->state[i] == SR_PORT_QUEUED && career_in(p, i) && (best < 0 || p->f[i].unit1 < p->f[best].unit1)) best = i;
    if (best < 0 || p->f[best].unit1 > next_unit) return 0;
    if (p->f[best].unit1 <= unit) return SR_PORT_E_MISSED;
    if (reserved(h, p->s4first, &p->f[best])) return SR_PORT_E_SLOT4_RESERVED;   /* (probe Q6: a tie left in slot 4
                                                                    into a window drops the play-off silently) */
    p->state[best] = SR_PORT_INSTALLED;
    p->pending = p->f[best].match_id;
    *f = p->f[best];
    return 1;
}

int32_t sr_port_missed(sr_port *p, const sr_port_host *h, uint16_t unit, uint16_t next_unit)
{
    int32_t played = 0;
    if (!p) return SR_PORT_E_ARGS;
    for (int32_t i = 0; i < p->n; i++) {
        if (p->state[i] != SR_PORT_QUEUED || !career_in(p, i) || p->f[i].unit1 > next_unit ||
            (p->f[i].unit1 > unit && !reserved(h, p->s4first, &p->f[i]))) continue;
        const int32_t e = simulate(p, h, i);
        if (e) return e;
        played++;
    }
    return played;
}

int32_t sr_port_revalidate(const sr_port *p, const sr_port_host *h, int32_t *bad)
{
    if (!p || !h || !h->league_plays) return SR_PORT_E_ARGS;
    return check(p->f, p->n, p->n, p->state, p->unit, p->s4first, h, bad, 0, 0, 0);   /* (rule 2 off: a save's units
                                                                                       are past) */
}

int32_t sr_port_revalidate_all(const sr_port *p, const sr_port_host *h, int32_t *bad, int32_t *nbad, uint32_t *ids,
                               int32_t max_ids)
{
    if (!p || !h || !h->league_plays || !nbad || max_ids < 0 || (max_ids && !ids)) return SR_PORT_E_ARGS;
    return check(p->f, p->n, p->n, p->state, p->unit, p->s4first, h, bad, nbad, ids, max_ids);
}

int32_t sr_port_result_in(sr_port *p, const sr_port_host *h, const sr_port_result *r)
{
    if (!p || !r) return SR_PORT_E_ARGS;
    if (!p->pending || r->match_id != p->pending) return SR_PORT_E_PENDING;
    for (int32_t i = 0; i < p->n; i++)
        if (p->f[i].match_id == p->pending && p->state[i] == SR_PORT_INSTALLED) {
            const int32_t e = take(p, h, i, r);
            if (!e) p->pending = 0;
            return e;
        }
    return SR_PORT_E_PENDING;
}

int32_t sr_port_club_change(sr_port *p, const sr_port_host *h, uint16_t career)
{
    if (!p) return SR_PORT_E_ARGS;
    for (int32_t i = 0; p->pending && i < p->n; i++)
        if (p->f[i].match_id == p->pending && p->state[i] == SR_PORT_INSTALLED) {
            const int32_t e = simulate(p, h, i);    /* (taken out of slot 4: the engine plays it) */
            if (e) return e;
        }
    p->pending = 0;
    p->career = career;
    return 0;
}

/* ---- the FP section: a 20-B header (u16 version, u16 n, u32 pack hash, u32 pending, u16 unit, career, s4first,
 * u16 0), then per fixture its 32 B, field by field, its state byte, and its 16-B result when played ---- */
static u8 *w16(u8 *o, u16 v) { o[0] = (u8)v; o[1] = (u8)(v >> 8); return o + 2; }
static u8 *w32(u8 *o, u32 v) { return w16(w16(o, (u16)v), (u16)(v >> 16)); }
static u16 r16(const u8 *i) { return (u16)(i[0] | i[1] << 8); }
static u32 r32(const u8 *i) { return r16(i) | (u32)r16(i + 2) << 16; }

int32_t sr_port_save_size(const sr_port *p)
{
    int32_t n = 20;
    for (int32_t i = 0; p && i < p->n; i++) n += 33 + (p->state[i] == SR_PORT_PLAYED ? 16 : 0);
    return n;
}

int32_t sr_port_save(const sr_port *p, uint8_t *out, int32_t max)
{
    if (!p || !out || max < sr_port_save_size(p)) return SR_PORT_E_SAVE;
    u8 *o = w16(w32(w32(w16(w16(out, SR_PORT_VERSION), p->n), p->pack_hash), p->pending), p->unit);
    o = w16(w16(w16(o, p->career), p->s4first), 0);
    for (int32_t i = 0; i < p->n; i++) {
        const sr_port_fixture *f = &p->f[i];
        o = w16(w16(w16(w16(w16(w16(w32(o, f->match_id), f->unit1), f->unit2), f->comp_id), f->label_id),
                    f->home), f->away);
        *o++ = f->legs; *o++ = f->level; *o++ = f->neutral; *o++ = f->kind; *o++ = f->lfile; *o++ = f->flags;
        o = w16(o, f->prev_id);
        for (int32_t k = 0; k < 8; k++) *o++ = f->names[k];
        *o++ = p->state[i];
        if (p->state[i] == SR_PORT_PLAYED) {
            const sr_port_result *r = &p->r[i];
            o = w32(o, r->match_id);
            for (int32_t k = 0; k < 2; k++) o[k] = r->g90[k], o[2 + k] = r->g90b[k], o[4 + k] = r->get[k],
                                            o[6 + k] = r->pens[k], o[8 + k] = r->cards[k];
            o[10] = r->status; o[11] = r->winner; o += 12;
        }
    }
    return (int32_t)(o - out);
}

static int32_t load(sr_port *p, const uint8_t *in, int32_t len, uint32_t pack_hash)
{
    if (!in || len < 20) return SR_PORT_E_SAVE;
    const u16 n = r16(in + 2);
    if (r16(in) != SR_PORT_VERSION || n > SR_PORT_MAX || r32(in + 4) != pack_hash || r16(in + 18)) return SR_PORT_E_SAVE;
    sr_port_init(p, r16(in + 14), r16(in + 12), r16(in + 16), pack_hash);
    const u8 *i8 = in + 20, *end = in + len;
    int32_t installed = 0;
    for (int32_t i = 0; i < n; i++) {
        if (end - i8 < 33) return SR_PORT_E_SAVE;
        sr_port_fixture *f = &p->f[i];
        f->match_id = r32(i8); f->unit1 = r16(i8 + 4); f->unit2 = r16(i8 + 6); f->comp_id = r16(i8 + 8);
        f->label_id = r16(i8 + 10); f->home = r16(i8 + 12); f->away = r16(i8 + 14);
        f->legs = i8[16]; f->level = i8[17]; f->neutral = i8[18]; f->kind = i8[19]; f->lfile = i8[20]; f->flags = i8[21];
        f->prev_id = r16(i8 + 22);
        for (int32_t k = 0; k < 8; k++) f->names[k] = i8[24 + k];
        p->state[i] = i8[32]; i8 += 33;
        if (p->state[i] > SR_PORT_PLAYED) return SR_PORT_E_SAVE;
        installed += p->state[i] == SR_PORT_INSTALLED;
        if (p->state[i] == SR_PORT_INSTALLED && f->match_id != r32(in + 8)) return SR_PORT_E_SAVE;
        if (p->state[i] == SR_PORT_PLAYED) {
            sr_port_result *r = &p->r[i];
            if (end - i8 < 16) return SR_PORT_E_SAVE;
            r->match_id = r32(i8);
            for (int32_t k = 0; k < 2; k++) r->g90[k] = i8[4 + k], r->g90b[k] = i8[6 + k], r->get[k] = i8[8 + k],
                                            r->pens[k] = i8[10 + k], r->cards[k] = i8[12 + k];
            r->status = i8[14]; r->winner = i8[15]; i8 += 16;
            if (sr_port_winner(f, r) != r->winner) return SR_PORT_E_SAVE;
        }
    }
    p->n = n;
    p->pending = r32(in + 8);
    if (i8 != end || installed != (p->pending != 0) || check(p->f, n, n, p->state, p->unit, p->s4first, 0, 0, 0, 0, 0))
        return SR_PORT_E_SAVE;
    return 0;
}

int32_t sr_port_load(sr_port *p, const uint8_t *in, int32_t len, uint32_t pack_hash)
{
    if (!p) return SR_PORT_E_ARGS;
    const int32_t e = load(p, in, len, pack_hash);
    if (e) sr_port_init(p, 0, 0, 0, 0);     /* (a refused section leaves no port, never half of one) */
    return e;
}
