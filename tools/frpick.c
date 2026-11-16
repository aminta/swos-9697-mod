/* 4.2 preseason friendlies, part (b): the opponent pick. THE RULES are tools/frpick.h's header comment; this file only
   adds the details the header leaves open (host test: tools/hosttest/tests/test_frpick.py, with a Python reference).

   - margin: M = max(11, S / 10), integer division (S = 119 -> 11, S = 120 -> 12).
   - band of a club of strength s (d = s - S, signed 32-bit, so S - 4M below 0 is no special case): the edges belong
     to the nearer band (d = M and -M similar, d = 4M stronger, d = -4M weaker).
   - count: the index's count byte 0 = 256 clubs, everywhere (ordinal guard, length, contiguity, the passes).
   - avoid == NULL = navoid 0.
   - order of the checks / return codes: FR_BADBLOB, FR_NOSELF, FR_GIVEN, FR_NOPOOL. *out is zeroed first, so why[] is
     0 on every path but FR_GIVEN. self is looked up among the call's world entries only; strength 0 = FR_NOSELF.
   - blob: len >= 8, 'FRSS', version 2, len == 8 + 6 * blocks + 2 * sum(counts), the first block's first value index
     0 and each next one = the previous first + count (a sum past 65535 cannot be indexed: refused), no index entry
     of file 255. Byte +5 and
     the index's sort order are not checked (a word is always resolved by the FIRST index entry of (world, file)).
   - given: every chosen club is checked, in slot order; FR_E_DUP = the same word as ANY earlier chosen club (a
     refused one too; pinned and empty slots are never duplicates). The room is spent in slot order by the accepted
     clubs that are not cached; cached() is called for a chosen club only when the four checks before FR_E_ROOM
     passed. A chosen club of self's country is accepted (its country then counts for the country penalty like any
     other, which no candidate can match).
   - pinned slots: (word & 0xFF) == 0xFF and (word >> 8) - 0xF0 < 3; they take their band off the need in the same
     slot-order pass as the chosen clubs, before the empty slots are counted.
   - venues as given: any nhome >= 0x100 -> mask = nhome & 0xF, checked right after the given list (so before
     FR_NOPOOL): 2 bits set, or FR_GIVEN with FR_E_VENUE x 4.
   - fr_level: no cap is coded - b counts strengths strictly below the club's own, so b <= n - 1 and 5 * b / n <= 4.
   - fr_given: k must be 0..3. With a room it walks the entries 0..k (one index lookup and at most one cached() call
     each: k + 1 lookups, <= k + 1 calls); without a room entry k only (one lookup, no call). *band: 0xFF for an
     empty slot and for FR_E_NOCLUB; the pinned band for FR_AUTO; the club's band otherwise - also when the club is
     refused (FR_E_SELF / BTEAM / DUP / ROOM: the page can still colour it). It knows nothing of the venues
     (FR_E_VENUE is fr_pick's only).
   - stack: fr_pick keeps the state (FrCtx) and calls the phases - fr_open, fr_entry per given entry, fr_auto per
     automatic slot (noinline) - so their frames do not add up. Deepest path fr_pick -> fr_auto -> cached(): 240 B
     with the exe flags at -Oz, return addresses and pushed arguments included (measured by test_frpick_exe_run,
     which executes the object; < 256 asserted there).
   - FRPICK_TEST (host test builds only, never the exe object): fr_test_band exports fr_band.
   - uncovered bands: need = {1 stronger, 2 similar, 1 weaker}; each valid given club / pinned slot takes one off its
     band's need (when one is left; a far club takes none, and its band[k] is FR_FAR_UP / FR_FAR_DOWN with fb 0).
     With E empty slots: similar x min(need, E), then weaker x min(need, what is left of E), then stronger for the
     rest. They go into the empty slots in ascending slot order, weaker first, then similar, then stronger (no given:
     weaker, similar, similar, stronger). The automatic slots are filled in ascending order.
   - "a country already used by an earlier slot" / "never twice": the clubs already in the four when the slot is
     filled = every given club (of any slot) + the automatic slots filled before it.
   - the key is compared as (distance << 2 | avoid << 1 | country, hash); a full tie (a 32-bit hash collision) keeps
     the first club in table order (index order, then ordinal).
   - hash: slot = the slot's index 0..3 in the four; uint32 operations only (see fr_hash; seed and season are mixed
     once per call).
   - room: an automatic pass calls cached() only while no room is left, and only for a club that would become the
     best so far (a non-cached one is skipped); with room left the pass calls nothing and the chosen club is asked
     once after the pass (not cached: one unit of room spent).
   - venues: nhome > 4 = 4; home = the club has fewer than nhome clubs before it in (strength, slot) order. */
#include "frpick.h"

#define RD16(p) ((uint32_t)(p)[0] | (uint32_t)(p)[1] << 8)
#define CNT(e)  ((((uint32_t)(e)[2] - 1) & 0xFF) + 1)         /* the count byte: 0 = 256 clubs */

/* mix = seed ^ season * 0x9E3779B1 (made once per call, in fr_pick) */
static uint32_t fr_hash(uint32_t mix, uint32_t slot, uint32_t word)
{
    uint32_t h = mix ^ ((slot << 16 | word) * 0x85EBCA6Bu);
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
            if ((word >> 8) >= CNT(e))
                break;
            *ctry = e[3];
            return RD16(frss + 8 + 6 * nb + 2 * (RD16(e + 4) + (word >> 8)));
        }
    return 0;
}

/* the blob: 1 = accepted */
static int fr_check(const uint8_t *frss, uint32_t len)
{
    uint32_t nb, i, sum;

    if (len < 8 || frss[0] != 'F' || frss[1] != 'R' || frss[2] != 'S' || frss[3] != 'S' || frss[4] != FRSS_VERSION)
        return 0;
    nb = RD16(frss + 6);
    if (len < 8 + 6 * nb)
        return 0;
    for (i = 0, sum = 0; i < nb; i++) {
        const uint8_t *e = frss + 8 + 6 * i;

        if (RD16(e + 4) != sum || e[1] == 0xFF)
            return 0;
        sum += CNT(e);
    }
    return len == 8 + 6 * nb + 2 * sum;
}

static uint32_t fr_band(int32_t d, int32_t m)
{
    return d > 4 * m ? FR_FAR_UP : d > m ? FR_STRONGER
         : d < -4 * m ? FR_FAR_DOWN : d < -m ? FR_WEAKER : FR_SIMILAR;
}

/* the state shared by the phases (in fr_pick's / fr_given's frame; the phases are separate functions so that their
   frames do not add up: the stack condition) */
typedef struct {
    const uint8_t *frss;
    const uint16_t *given;
    const FrRoom *room;
    uint32_t world, self, self2;
    uint32_t left;                      /* the room left */
    uint32_t s, c;                      /* fr_entry: the club's strength (0: no club) and country */
    int32_t S, M;                       /* self's strength, the margin */
} FrG;

typedef struct {
    FrG g;
    const uint16_t *avoid;
    uint32_t navoid, mix, sc, filled;       /* mix: seed and season, see fr_hash */
    FrPick *out;
    uint16_t str[4];
    uint8_t ctry[4];
} FrCtx;

/* the blob and self: 0, FR_BADBLOB or FR_NOSELF; *sc = self's country */
static int fr_open(FrG *g, const uint8_t *frss, uint32_t len, uint32_t world, uint32_t self, uint32_t self2,
                   const uint16_t *given, const FrRoom *room, uint32_t *sc)
{
    if (!fr_check(frss, len))
        return FR_BADBLOB;
    g->frss = frss;
    g->given = given;
    g->room = room;
    g->world = world;
    g->self = self;
    g->self2 = self2;
    g->left = room ? room->room : 0;
    g->S = (int32_t)fr_find(frss, world, self, sc);
    if (!g->S)
        return FR_NOSELF;
    g->M = g->S < 110 ? 11 : g->S / 10;
    return 0;
}

/* THE GIVEN CHECK of entry k, shared by fr_pick and fr_given (so the two cannot drift). FR_G_EMPTY: 0xFFFF;
   FR_G_PIN + band: FR_AUTO(band); 0: a club accepted; < 0: its FR_E_* code. g->s = the club's strength (0: no club),
   g->c its country. g->left = the room left, spent here by an accepted club that is not cached: the caller walks
   the entries in slot order. */
#define FR_G_EMPTY  1
#define FR_G_PIN    2

static int fr_entry(FrG *g, uint32_t k)
{
    uint32_t w = g->given ? g->given[k] : FR_NONE, j;
    int e = 0;

    g->s = 0;
    if (w == FR_NONE)
        return FR_G_EMPTY;
    if ((w & 0xFF) == 0xFF && (j = (w >> 8) - 0xF0) < 3)
        return (int)(FR_G_PIN + j);
    g->s = fr_find(g->frss, g->world, w, &g->c);
    for (j = 0; j < k; j++)
        if (g->given[j] == w)
            e = FR_E_DUP;
    if (!g->s)
        return FR_E_NOCLUB;
    if (w == g->self)
        return FR_E_SELF;
    if (w == g->self2)
        return FR_E_BTEAM;
    if (!e && g->room && !g->room->cached(g->room->ctx, (uint16_t)w)) {
        if (!g->left)
            return FR_E_ROOM;
        g->left--;
    }
    return e;
}

int fr_given(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t self, uint16_t self2,
             const uint16_t *given, uint32_t k, const FrRoom *room, uint8_t *band)
{
    FrG g;
    uint32_t j;
    int e;

    *band = 0xFF;
    e = fr_open(&g, frss, len, world, self, self2, given, room, &j);
    if (e)
        return e;
    for (j = room ? 0 : k; j <= k; j++)         /* (the earlier entries matter for the room only) */
        e = fr_entry(&g, j);
    if (e > 0) {
        if (e >= FR_G_PIN)
            *band = (uint8_t)(e - FR_G_PIN);
        return 0;
    }
    if (g.s)
        *band = (uint8_t)fr_band((int32_t)g.s - g.S, g.M);
    return e;
}

/* one automatic slot: the pass over the table for slot k, wanted band wb; 0, or FR_NOPOOL. noinline: its frame must
   not join fr_pick's (the stack condition; test_frpick_exe_run measures it) */
__attribute__((noinline)) static int fr_auto(FrCtx *x, uint32_t k, uint32_t wb)
{
    const uint8_t *frss = x->g.frss, *e = frss + 8, *v;
    const FrRoom *room = x->g.room;
    uint32_t nb = RD16(frss + 6), i, j, c, best = 0xFFFFFFFFu, besth = 0, bw = 0, bs = 0, bc = 0;
    const int32_t M = x->g.M;

    for (i = 0; i < nb; i++, e += 6) {
        if (e[0] != x->g.world || e[3] == x->sc)
            continue;
        v = frss + 8 + 6 * nb + 2 * RD16(e + 4);
        for (c = 0; c < CNT(e); c++, v += 2) {
            uint32_t w = e[1] | c << 8, key = 0, h;
            int32_t s = (int32_t)RD16(v), d = s - x->g.S;

            if (!s || w == x->g.self || w == x->g.self2)
                continue;
            for (j = 0; j < 4; j++)
                if (x->filled >> j & 1) {
                    if (x->out->word[j] == w)
                        goto next;
                    if (x->ctry[j] == e[3])
                        key = 1;
                }
            for (j = 0; j < x->navoid; j++)
                if (x->avoid[j] == w)
                    key |= 2;
            if (fr_band(d, M) != wb) {
                if (wb == FR_STRONGER)
                    d = d > M ? d - 4 * M : M + 1 - d;
                else if (wb == FR_WEAKER)
                    d = d < -M ? -4 * M - d : d + M + 1;
                else
                    d = (d < 0 ? -d : d) - M;
                key |= (uint32_t)d << 2;
            }
            h = fr_hash(x->mix, k, w);
            if (key > best || (key == best && h >= besth))
                continue;
            if (room && !x->g.left && !room->cached(room->ctx, (uint16_t)w))
                continue;
            best = key, besth = h, bw = w, bs = (uint32_t)s, bc = e[3];
        next:;
        }
    }
    if (best == 0xFFFFFFFFu)
        return FR_NOPOOL;
    if (room && x->g.left && !room->cached(room->ctx, (uint16_t)bw))
        x->g.left--;
    x->out->word[k] = (uint16_t)bw;
    x->str[k] = (uint16_t)bs;
    x->ctry[k] = (uint8_t)bc;
    x->filled |= 1u << k;
    x->out->band[k] = (uint8_t)fr_band((int32_t)bs - x->g.S, M);
    if (best >> 2)
        x->out->fb |= (uint8_t)(1u << k);
    return 0;
}

int fr_pick(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t self, uint16_t self2,
            const uint16_t *given, const uint16_t *avoid, uint32_t navoid, const FrRoom *room,
            uint32_t season, uint32_t seed, uint32_t nhome, FrPick *out)
{
    FrCtx x;
    uint32_t i, j, k;
    uint8_t need[3], want[4];
    int rc, e;

    for (i = 0; i < sizeof *out; i++)
        ((uint8_t *)out)[i] = 0;
    rc = fr_open(&x.g, frss, len, world, self, self2, given, room, &x.sc);
    if (rc)
        return rc;
    x.avoid = avoid;
    x.navoid = avoid ? navoid : 0;
    x.mix = seed ^ season * 0x9E3779B1u;
    x.out = out;
    x.filled = 0;
    need[FR_STRONGER] = need[FR_WEAKER] = 1;
    need[FR_SIMILAR] = 2;

    /* the given list */
    for (k = 0; k < 4; k++) {
        e = fr_entry(&x.g, k);
        want[k] = 0xFF;
        if (e == FR_G_EMPTY)
            continue;
        if (e >= FR_G_PIN) {                                        /* FR_AUTO(band): a pinned automatic slot */
            j = (uint32_t)e - FR_G_PIN;
            want[k] = (uint8_t)j;
        } else if (e) {
            out->why[k] = (int8_t)e;
            rc = FR_GIVEN;
            continue;
        } else {
            out->word[k] = given[k];
            x.str[k] = (uint16_t)x.g.s;
            x.ctry[k] = (uint8_t)x.g.c;
            x.filled |= 1u << k;
            j = fr_band((int32_t)x.g.s - x.g.S, x.g.M);
            out->band[k] = (uint8_t)j;
        }
        if (j < 3 && need[j])
            need[j]--;
    }
    if (rc)
        return rc;
    if (nhome >= 0x100 && !(0x1668u >> (nhome & 0xF) & 1)) {        /* 0x1668: the masks of 2 bits (3 5 6 9 10 12) */
        for (k = 0; k < 4; k++)
            out->why[k] = FR_E_VENUE;
        return FR_GIVEN;
    }

    /* the uncovered bands of the empty slots: similar, similar, weaker, stronger (as many as the empty slots) */
    for (k = 0, j = 0; k < 4; k++)
        j += !(x.filled >> k & 1) && want[k] == 0xFF;
    if (need[FR_SIMILAR] > j)
        need[FR_SIMILAR] = (uint8_t)j;
    j -= need[FR_SIMILAR];
    if (need[FR_WEAKER] > j)
        need[FR_WEAKER] = (uint8_t)j;

    /* the automatic slots, in ascending order: one pass over the table each */
    for (k = 0; k < 4; k++) {
        if (x.filled >> k & 1)
            continue;
        j = want[k];
        if (j == 0xFF) {                /* an empty slot: the next uncovered band, weakest first (none left: similar) */
            j = need[FR_WEAKER] ? FR_WEAKER : need[FR_SIMILAR] || !need[FR_STRONGER] ? FR_SIMILAR : FR_STRONGER;
            if (need[j])
                need[j]--;
        }
        if (fr_auto(&x, k, j))
            return FR_NOPOOL;
    }

    /* the venues: as given (FR_VENUES), or the nhome weakest at home (ties: the lower slot first) */
    if (nhome >= 0x100) {
        out->home = (uint8_t)(nhome & 0xF);
        return FR_OK;
    }
    for (k = 0; k < 4; k++) {
        for (j = 0, i = 0; j < 4; j++)
            i += x.str[j] < x.str[k] || (x.str[j] == x.str[k] && j < k);
        if (i < nhome)
            out->home |= (uint8_t)(1u << k);
    }
    return FR_OK;
}

uint32_t fr_level(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t word)
{
    uint32_t nb, i, c, s, S, n = 0, b = 0;
    const uint8_t *e, *v;

    if (!fr_check(frss, len))
        return 0;
    S = fr_find(frss, world, word, &c);
    if (!S)
        return 0;
    nb = RD16(frss + 6);
    for (i = 0, e = frss + 8; i < nb; i++, e += 6) {
        if (e[0] != world)
            continue;
        v = frss + 8 + 6 * nb + 2 * RD16(e + 4);
        for (c = CNT(e); c; c--, v += 2) {
            s = RD16(v);
            n += s != 0;
            b += s && s < S;
        }
    }
    return 1 + 5 * b / n;
}

#ifdef FRPICK_TEST
uint32_t fr_test_band(int32_t d, int32_t m)
{
    return fr_band(d, m);
}
#endif
