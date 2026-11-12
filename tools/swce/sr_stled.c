/*
 * sr_stled.c -- a groups stage's state in a save: the ledger item 'ST' (the sr_stage plan's P6), as lrank's 'LR'
 * keeps a league's head to head. One block per stage, of a size fixed by its shape (sr_st_size), so the caller's
 * ledger declares it once:
 *
 *   +0        'S' 'T', u8 version (SR_ST_VERSION)
 *   +3        u8 n (clubs), u8 g (groups), u8 legs
 *   +6        u16 season, u32 purpose (SwcStage.purpose), u32 the entrants: FNV-1a 32 of their n team words in
 *             seeding order, each low byte first -- the key, with the shape (Motore's review R1: as LR keys on its
 *             first team word, ST keys on all its clubs)
 *   +16       u8 grp[n]: club c's group (sr_group_draw); a group's clubs are those of its number, ascending c
 *   +16 + n   u8 res[m]: each group's matches in sr_rr_calendar's order (group 0's first), home goals << 4 | away
 *             goals (each 0..14), SR_PAIR_NONE not played; m = the sum of legs * s * (s - 1) / 2 over the groups'
 *             sizes s (sr_group_sizes)
 *
 * Known limit: a side's goals above 14 are kept as 14 (as LR). Harmless when the glue ranks the record criteria from
 * the game's own group rows and uses ST for the draw and head to head (LR's model); a table rebuilt from ST alone
 * would be wrong past 14 goals -- then 2 bytes a match (Motore's review R2: decided with P7). With 3 or 4 legs a
 * pair meets twice at one ground: a result goes to its first unplayed match (the same table either way).
 *
 * No calendar and no table in it: both come again from the groups and the results. An older save has no item
 * (the ledger zeroes it), and a block of another season or stage is not this one: either way sr_st_check says
 * 'not started' and the caller draws again with sr_st_begin -- the same groups, the seed being the stage's (P4:
 * the world, the season and the purpose, never the game's RNG).
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t  i32;

enum { HDR = 16 };

/* FNV-1a 32 of the entrants' team words, in seeding order (each low byte first): the key tells a stale block (a
   job change, another career or world loaded, the entrants changed) from this stage's (Motore's review R1) */
static u32 clubs(const u16 *word, i32 n)
{
    u32 h = 2166136261u;
    for (i32 c = 0; c < n; c++) {
        h = (h ^ (u8)word[c]) * 16777619u;
        h = (h ^ (u8)(word[c] >> 8)) * 16777619u;
    }
    return h;
}

static i32 pairs(i32 s, i32 legs) { return legs * s * (s - 1) / 2; }

/* the shape's group sizes and its block size; -1 refused */
static i32 shape(i32 n, i32 g, i32 legs, u8 *size)
{
    if (n < 2 || n > SR_STAGE_CLUBS || legs < 1 || legs > 4 || sr_group_sizes(n, g, size) < 0) return -1;
    i32 m = 0;
    for (i32 k = 0; k < g; k++) m += pairs(size[k], legs);
    return HDR + n + m;
}

i32 sr_st_size(i32 n, i32 g, i32 legs)
{
    u8 size[SR_STAGE_CLUBS];
    return shape(n, g, legs, size);
}

static void key(u8 *st, i32 n, i32 g, i32 legs, u32 season, u32 purpose, u32 cl)
{
    st[0] = 'S'; st[1] = 'T'; st[2] = SR_ST_VERSION;
    st[3] = (u8)n; st[4] = (u8)g; st[5] = (u8)legs;
    st[6] = (u8)season; st[7] = (u8)(season >> 8);
    for (int i = 0; i < 4; i++) st[8 + i] = (u8)(purpose >> 8 * i);
    for (int i = 0; i < 4; i++) st[12 + i] = (u8)(cl >> 8 * i);
}

i32 sr_st_begin(u8 *st, i32 room, i32 n, i32 g, i32 legs, u32 season, u32 purpose, const u16 *word, const u8 *assoc,
                u32 seed)
{
    u8 size[SR_STAGE_CLUBS];
    const i32 sz = shape(n, g, legs, size);
    if (sz < 0 || room < sz || !word) return -1;
    const i32 d = sr_group_draw(n, g, assoc, seed, st + HDR);
    if (d < 0) return d;
    for (i32 i = HDR + n; i < sz; i++) st[i] = SR_PAIR_NONE;
    key(st, n, g, legs, season & 0xFFFF, purpose, clubs(word, n));
    return sz;
}

i32 sr_st_check(const u8 *st, i32 room, i32 n, i32 g, i32 legs, u32 season, u32 purpose, const u16 *word)
{
    u8 size[SR_STAGE_CLUBS], want[HDR], cnt[SR_STAGE_CLUBS];
    const i32 sz = shape(n, g, legs, size);
    if (sz < 0 || room < sz || !word) return -2;
    if (st[0] == 'S' && st[1] == 'T' && st[2] != SR_ST_VERSION) return 2;
    key(want, n, g, legs, season & 0xFFFF, purpose, clubs(word, n));
    for (i32 k = 0; k < g; k++) cnt[k] = 0;
    for (int i = 0; i < HDR; i++) if (st[i] != want[i]) return 0;
    for (i32 c = 0; c < n; c++) {
        if (st[HDR + c] >= g) return -1;
        cnt[st[HDR + c]]++;
    }
    for (i32 k = 0; k < g; k++) if (cnt[k] != size[k]) return -1;
    for (i32 i = HDR + n; i < sz; i++)
        if (st[i] != SR_PAIR_NONE && ((st[i] >> 4) > 14 || (st[i] & 15) > 14)) return -1;
    return 1;
}

/* group k's first result byte; its size into *s */
static i32 at(const u8 *st, i32 k, i32 *s)
{
    u8 size[SR_STAGE_CLUBS];
    const i32 n = st[3], g = st[4], legs = st[5];
    if (shape(n, g, legs, size) < 0 || k < 0 || k >= g) return -1;
    i32 o = HDR + n;
    for (i32 j = 0; j < k; j++) o += pairs(size[j], legs);
    *s = size[k];
    return o;
}

i32 sr_st_group(const u8 *st, i32 k, u8 *club, sr_match *m, i32 room)
{
    i32 s;
    const i32 o = at(st, k, &s);
    if (o < 0) return -1;
    const i32 n = st[3], nm = pairs(s, st[5]);
    i32 j = 0;
    for (i32 c = 0; c < n; c++) if (st[HDR + c] == k && j < s) club[j++] = (u8)c;
    if (j != s || sr_rr_calendar(s, st[5], m, room) != nm) return -1;
    for (i32 i = 0; i < nm; i++) {
        const u8 r = st[o + i];
        m[i].played = r != SR_PAIR_NONE;
        m[i].hg = m[i].played ? r >> 4 : 0;
        m[i].ag = m[i].played ? r & 15 : 0;
    }
    return nm;
}

i32 sr_st_record(u8 *st, i32 home, i32 away, i32 hg, i32 ag, sr_match *m, i32 room)
{
    const i32 n = st[3];
    if (home < 0 || home >= n || away < 0 || away >= n || hg < 0 || ag < 0) return -1;
    const i32 k = st[HDR + home];
    if (st[HDR + away] != k) return -1;
    u8 club[SR_STAGE_CLUBS];
    i32 s;
    const i32 o = at(st, k, &s), nm = sr_st_group(st, k, club, m, room);
    if (o < 0 || nm < 0) return -1;
    for (i32 i = 0; i < nm; i++)
        if (!m[i].played && club[m[i].home] == home && club[m[i].away] == away) {
            st[o + i] = (u8)((hg > 14 ? 14 : hg) << 4 | (ag > 14 ? 14 : ag));
            return o + i - HDR - n;
        }
    return -1;
}
