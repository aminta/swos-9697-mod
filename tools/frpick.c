/* 4.2 preseason friendlies, part (b): the opponent pick. THE RULES are tools/frpick.h's header comment; this file only
   adds the details the header leaves open (host test: tools/hosttest/tests/test_frpick.py, with a Python reference).

   - margin: M = max(11, S / 10), integer division (S = 119 -> 11, S = 120 -> 12).
   - band of a club of strength s (d = s - S, signed): d > M stronger, d < -M weaker, else similar (the edges
     S + M and S - M are similar).
   - order of the checks / return codes: FR_BADBLOB, FR_NOSELF, FR_GIVEN, FR_NOPOOL. *out is zeroed first, so why[] is
     0 on every path but FR_GIVEN. self is looked up among the call's world entries only; strength 0 = FR_NOSELF.
   - blob: len >= 8, 'FRSS', version 2, len == 8 + 6 * blocks + 2 * sum(counts), the first block's first value index
     0 and each next one = the previous first + count. Byte +5 and the index's sort order are not checked (a word is
     always resolved by the FIRST index entry of (world, file)).
   - given: every entry is checked, in slot order; FR_E_DUP = the same word as ANY earlier non-empty given entry (a
     refused one too). The room is spent in slot order by the accepted entries that are not cached; cached() is
     called for a given entry only when the five checks before FR_E_ROOM passed.
   - uncovered bands: need = {1 stronger, 2 similar, 1 weaker}; each valid given club takes one off its band's need
     (when one is left). With E empty slots: similar x min(need, E), then weaker x min(need, what is left of E),
     then stronger for the rest. They go into the empty slots in ascending slot order, weaker first, then similar,
     then stronger (no given: weaker, similar, similar, stronger). The automatic slots are filled in ascending order.
   - "a country already used by an earlier slot" / "never twice": the clubs already in the four when the slot is
     filled = every given club (of any slot) + the automatic slots filled before it.
   - the key is compared as (distance << 2 | avoid << 1 | country, hash); a full tie (a 32-bit hash collision) keeps
     the first club in table order (index order, then ordinal).
   - hash: slot = the slot's index 0..3 in the four; uint32 operations only (see fr_hash).
   - room: an automatic pass calls cached() only while no room is left, and only for a club that would become the
     best so far (a non-cached one is skipped); with room left the pass calls nothing and the chosen club is asked
     once after the pass (not cached: one unit of room spent).
   - venues: nhome > 4 = 4; home = the club has fewer than nhome clubs before it in (strength, slot) order. */
#include "frpick.h"

#define RD16(p) ((uint32_t)(p)[0] | (uint32_t)(p)[1] << 8)

static uint32_t fr_hash(uint32_t seed, uint32_t season, uint32_t slot, uint32_t word)
{
    uint32_t h = seed ^ (season * 0x9E3779B1u) ^ ((slot << 16 | word) * 0x85EBCA6Bu);
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return h;
}

/* the strength of a team word in the call's world (0: not in the table, ordinal >= count, or no club); *ctry = its
   country id */
static uint32_t fr_find(const uint8_t *frss, uint32_t world, uint32_t word, uint32_t *ctry)
{
    uint32_t nb = RD16(frss + 6), i;
    const uint8_t *e = frss + 8;

    for (i = 0; i < nb; i++, e += 6)
        if (e[0] == world && e[1] == (word & 0xFF)) {
            if ((word >> 8) >= e[2])
                break;
            *ctry = e[3];
            return RD16(frss + 8 + 6 * nb + 2 * (RD16(e + 4) + (word >> 8)));
        }
    return 0;
}

static uint32_t fr_band(int32_t d, int32_t m)
{
    return d > m ? FR_STRONGER : d < -m ? FR_WEAKER : FR_SIMILAR;
}

int fr_pick(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t self, uint16_t self2,
            const uint16_t *given, const uint16_t *avoid, uint32_t navoid, const FrRoom *room,
            uint32_t season, uint32_t seed, uint32_t nhome, FrPick *out)
{
    uint32_t nb, i, j, k, sum, left, filled, sc, c;
    int32_t S, M;
    uint16_t str[4];
    uint8_t ctry[4], need[3];
    int rc;

    for (i = 0; i < sizeof *out; i++)
        ((uint8_t *)out)[i] = 0;

    /* the blob */
    if (len < 8 || frss[0] != 'F' || frss[1] != 'R' || frss[2] != 'S' || frss[3] != 'S' || frss[4] != FRSS_VERSION)
        return FR_BADBLOB;
    nb = RD16(frss + 6);
    if (len < 8 + 6 * nb)
        return FR_BADBLOB;
    for (i = 0, sum = 0; i < nb; i++) {
        if (RD16(frss + 8 + 6 * i + 4) != sum)
            return FR_BADBLOB;
        sum += frss[8 + 6 * i + 2];
    }
    if (len != 8 + 6 * nb + 2 * sum)
        return FR_BADBLOB;

    S = (int32_t)fr_find(frss, world, self, &sc);
    if (!S)
        return FR_NOSELF;
    M = S / 10;
    if (M < 11)
        M = 11;
    left = room ? room->room : 0;
    need[FR_STRONGER] = need[FR_WEAKER] = 1;
    need[FR_SIMILAR] = 2;

    /* the given list */
    for (k = 0, filled = 0, rc = FR_OK; k < 4; k++) {
        uint32_t w = given ? given[k] : FR_NONE, s;
        int e = 0;

        if (w == FR_NONE)
            continue;
        s = fr_find(frss, world, w, &c);
        for (j = 0; j < k; j++)
            if (given[j] == w)
                e = FR_E_DUP;
        if (!s)
            e = FR_E_NOCLUB;
        else if (w == self)
            e = FR_E_SELF;
        else if (w == self2)
            e = FR_E_BTEAM;
        else if (e)
            ;
        else if (c == sc)
            e = FR_E_HOME;
        else if (room && !room->cached(room->ctx, (uint16_t)w)) {
            if (left)
                left--;
            else
                e = FR_E_ROOM;
        }
        if (e) {
            out->why[k] = (int8_t)e;
            rc = FR_GIVEN;
            continue;
        }
        out->word[k] = (uint16_t)w;
        str[k] = (uint16_t)s;
        ctry[k] = (uint8_t)c;
        filled |= 1u << k;
        j = fr_band((int32_t)s - S, M);
        out->band[k] = (uint8_t)j;
        if (need[j])
            need[j]--;
    }
    if (rc)
        return rc;

    /* the uncovered bands of the empty slots: similar, similar, weaker, stronger (as many as the empty slots) */
    for (k = 0, j = 0; k < 4; k++)
        j += !(filled >> k & 1);
    if (need[FR_SIMILAR] > j)
        need[FR_SIMILAR] = (uint8_t)j;
    j -= need[FR_SIMILAR];
    if (need[FR_WEAKER] > j)
        need[FR_WEAKER] = (uint8_t)j;

    /* the automatic slots: one pass over the table each */
    for (k = 0; k < 4; k++) {
        uint32_t want, best = 0xFFFFFFFFu, besth = 0, bw = FR_NONE, bs = 0, bc = 0;
        const uint8_t *e = frss + 8, *v;

        if (filled >> k & 1)
            continue;
        want = need[FR_WEAKER] ? FR_WEAKER : need[FR_SIMILAR] ? FR_SIMILAR : FR_STRONGER;
        if (need[want])                 /* (the stronger ones are simply the rest) */
            need[want]--;
        for (i = 0; i < nb; i++, e += 6) {
            if (e[0] != world || e[3] == sc)
                continue;
            v = frss + 8 + 6 * nb + 2 * RD16(e + 4);
            for (c = 0; c < e[2]; c++, v += 2) {
                uint32_t w = e[1] | c << 8, key = 0, h;
                int32_t s = (int32_t)RD16(v), d = s - S;

                if (!s || w == self || w == self2)
                    continue;
                for (j = 0; j < 4; j++)
                    if (filled >> j & 1) {
                        if (out->word[j] == w)
                            goto next;
                        if (ctry[j] == e[3])
                            key = 1;
                    }
                for (j = 0; j < navoid; j++)
                    if (avoid[j] == w)
                        key |= 2;
                if (fr_band(d, M) != want) {
                    if (want == FR_STRONGER)
                        d = M + 1 - d;
                    else if (want == FR_WEAKER)
                        d = d + M + 1;
                    else
                        d = (d < 0 ? -d : d) - M;
                    key |= (uint32_t)d << 2;
                }
                h = fr_hash(seed, season, k, w);
                if (key > best || (key == best && h >= besth))
                    continue;
                if (room && !left && !room->cached(room->ctx, (uint16_t)w))
                    continue;
                best = key, besth = h, bw = w, bs = (uint32_t)s, bc = e[3];
            next:;
            }
        }
        if (bw == FR_NONE)
            return FR_NOPOOL;
        if (room && left && !room->cached(room->ctx, (uint16_t)bw))
            left--;
        out->word[k] = (uint16_t)bw;
        str[k] = (uint16_t)bs;
        ctry[k] = (uint8_t)bc;
        filled |= 1u << k;
        out->band[k] = (uint8_t)fr_band((int32_t)bs - S, M);
        if (best >> 2)
            out->fb |= (uint8_t)(1u << k);
    }

    /* the venues: the nhome weakest at home (ties: the lower slot first) */
    for (k = 0; k < 4; k++) {
        for (j = 0, i = 0; j < 4; j++)
            i += str[j] < str[k] || (str[j] == str[k] && j < k);
        if (i < nhome)
            out->home |= (uint8_t)(1u << k);
    }
    return FR_OK;
}
