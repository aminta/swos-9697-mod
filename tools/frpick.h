/* 4.2 preseason friendlies, part (b): the opponent pick (owner Mercato CPU; engine side Motore, review Convergence).
   Decisions: internal/handoff/friendlies-pick.md. Pure C: no exe symbol, no global, no libc beyond memset / memcpy,
   no malloc, no file I/O, stack < 256 B (no array sized by the pool: the table is walked in place). Linked by Motore
   in FRND; the host tests build it natively (tools/hosttest/tests/test_frpick.py).

   THE TABLE (FRSS v2, one world's slice of DATA\FRSS.DAT, read by Motore at the season start into a scratch buffer):
     +0 'FRSS'  +4 db version 2  +5 db 0  +6 dw blocks
     index, sorted by (world, file): blocks x [db world, db file, db count, db country, dw first value's index]
     (count 0 = 256 clubs: World 2026-27's Italy file holds ordinals 0..255; a file never has 0 clubs)
     values: dw strength per club in ordinal order (0 = no club in that record: never picked, never accepted)
   A team word = file | ordinal << 8. strength = statespec.club_strength (best 11 player prices, at least 5) in every
   world. country = one id per country, meaningful inside its world only (a country of several files shares one:
   World 2026-27 Brazil 161 + its states file 162). A v1 blob, a bad magic, a length that does not match the index,
   or first-value indices that are not contiguous (0, then the previous first + count) -> FR_BADBLOB. No world has a
   file 255 (its words are FR_NONE / FR_AUTO below): a blob with an index entry of file 255 -> FR_BADBLOB too. The
   DATA file around the slices (magic 'FRSD', world index) is tools/frstr.py's docstring; Motore reads it.

   THE POOL (of the automatic slots; a club the player chose follows THE GIVEN LIST): the table's clubs of the call's
   world with strength > 0, of ANOTHER country than self's (so never self, never a B team of self's country), never
   self2 (the B team; self2 = 0xFFFF: no B team, nothing more is excluded),
   never twice in the same four, and only while the team cache has room (room below).

   THE BANDS (S = self's strength, d = club's strength - S, margin M = max(11, S / 10), integer division):
     FR_FAR_DOWN  d < -4M       FR_WEAKER  -4M <= d < -M       FR_SIMILAR  -M <= d <= M
     FR_STRONGER  M < d <= 4M   FR_FAR_UP  d > 4M
   The far bands are never wanted (a giant against a small club is not a preseason test, Davide's reality rule): a
   club there is taken only by the nearest-band rule.
   The mix: 1 stronger, 2 similar, 1 weaker. Play order of the automatic four: weaker, similar, similar, stronger.

   THE CHOICE of one automatic slot (one pass over the table per slot): the candidate with the smallest key
     (fallback distance, last-season penalty, country penalty, hash(seed, season, slot, word))
   - fallback distance: 0 inside the wanted band; outside it, how far the club's strength lies from the band
     (stronger: M + 1 - d below the band, d - 4M above it; weaker: d + M + 1 above it, -4M - d below it; similar:
     |d| - M). THE "NEAREST BAND" RULE:
     when the wanted band has no candidate, the slot takes the club nearest to one of that band's two edges, from
     either side (a top club with no stronger opponent gets the strongest club left, a bottom club with no weaker one
     the weakest left; a club beyond the far edge when it is the nearer). Such a slot
     has bit k of FrPick.fb set and band[k] = the band its club really falls in.
   - last-season penalty: 1 for a word in avoid[] (last season's four, FR_ST +2..+9), else 0: avoided while the
     band allows, never at the cost of the band.
   - country penalty: 1 for a country already used by an earlier slot of the four, else 0: four distinct countries
     where possible.
   - "earlier slot" / "never twice": the clubs already in the four when a slot is filled = every valid given club (any
     slot) + the automatic slots filled before it; the automatic slots - pinned (FR_AUTO) and empty alike - are filled
     in ascending slot order.
   - hash: a fixed uint32 mix of seed, season, slot (the slot's index 0..3 in the four) and word (seed is opaque:
     Motore's sc_step_c formula + a FR constant); a full tie keeps the first club in table order.
   Same inputs -> the same output, at any -O level.

   THE ROOM (MC 16/11, section 1's tc_room / tc_reserve): with room != NULL the pick loads at most room->room clubs
   that room->cached() says are not in the team cache (cached clubs cost nothing). An automatic slot skips a club
   that would not fit and takes the next candidate by the key above; a given club that does not fit is refused
   (FR_E_ROOM). room == NULL: no limit. Unit: one team record in the team cache per club not yet cached; a pick adds
   at most 4 (its four clubs; a club already cached adds 0 and is never counted twice). cached is a plain cdecl C
   function pointer (Motore's gplay shim wraps FindTeamInCache; frpick never calls an exe address), called at most
   once per candidate per slot pass and never with room == NULL (agreed with Motore 16/11).

   THE GIVEN LIST (the player's choice page, Davide 16/11): given[k] = what the player set for slot k; given == NULL
   is exactly 4 x 0xFFFF. An entry is one of
     0xFFFF (FR_NONE)   an empty slot: automatic, its band comes from the mix (below)
     FR_AUTO(band)      a PINNED automatic slot: 0xF0FF stronger ("hard") / 0xF1FF similar ("medium") / 0xF2FF weaker
                        ("easy"). Automatic in everything (the pool: foreign clubs only; avoid, country penalty, room,
                        the nearest-band rule with fb) but its wanted band is the pinned one. Never refused.
     a team word        a club the player CHOSE. It may be of self's country (FR_E_HOME is no longer used by the given
                        list: the value stays reserved; "another country" is a rule of the automatic slots only).
   Each chosen club is checked in this order (the first that applies):
     FR_E_NOCLUB  not in this world's table, ordinal >= its file's count, strength 0, or any other word of file 255
                  (0xnnFF with nn not F0 / F1 / F2 / FF)
     FR_E_SELF    = self          FR_E_BTEAM  = self2          FR_E_DUP    = an earlier chosen club (a refused one too)
     FR_E_ROOM    no room in the team cache
   Any refusal: fr_pick returns FR_GIVEN with why[k] set for every refused entry (0 for the others) and out->word[]
   undefined: a refused entry is NEVER silently replaced. Valid chosen clubs keep their slot (their band = where
   their strength falls). THE MIX WITH A GIVEN LIST: the need starts at 1 stronger / 2 similar / 1 weaker; every
   chosen club and every pinned slot, in slot order, covers its band = takes one off that band's need when one is
   left (a chosen club in a far band covers none). OVER-PINNED lists are allowed (3 x "hard"; 2 chosen stronger clubs
   + a pinned "hard"): the extra ones cover nothing and stay what they are. The empty (0xFFFF) slots then take the
   bands still uncovered, taken in the order similar, similar, weaker, stronger (as many as there are empty slots),
   placed in the empty slots in ascending slot order weakest first; an empty slot left when everything is covered
   takes the first band in the order similar, weaker, stronger, i.e. similar (coded, but it cannot arise: the need is
   4 and each non-empty slot covers at most one, so the uncovered bands are never fewer than the empty slots).
   last-season avoid does not apply to a chosen club.

   THE VENUES (after the list is final): the nhome opponents with the lowest strength are played at home (ties: the
   lower slot first), the others away; bit k of out->home = friendly k at home. nhome 5 .. 0xFF -> 4. Default 2
   (2H / 2A). VENUES AS GIVEN: nhome = FR_VENUES(mask) = 0x100 | mask (any nhome >= 0x100; only bits 0-3 are read):
   out->home = nhome & 0xF, bit k = friendly k at home, no strength rule. The mask is VALIDATED: it must be exactly
   2 home + 2 away (the page swaps a row's venue with the nearest row of the other venue, so 2 + 2 holds there); any
   other mask is refused, never replaced: FR_GIVEN with why[k] = FR_E_VENUE on all four slots. The venue check runs
   after the given entries are validated and before any automatic slot is filled; when a given entry is refused,
   why[] carries the entries' codes only and the venue check is skipped.

   THE LEVEL (fr_level; a 1 .. 5 figure the page shows next to a club, beside the band): the club's quintile inside
   its own world's table, one function for every world. n = the world's clubs (strength > 0), b = how many of them
   have a strength strictly below the club's: level = 1 + (5 * b) / n (integer division; b < n, so 5 at most - the
   weakest clubs are 1, equal strengths share a level). 0 = no level: the blob is refused (as FR_BADBLOB) or the word
   is not a club of the table (as FR_E_NOCLUB: unknown file, ordinal >= count, strength 0, file 255). One pass over
   the table, no room / cache involved. The level is ABSOLUTE within the world (the same for whoever looks at the
   club); the band (the page's colour) is RELATIVE to self: a level-3 club is "stronger" for a level-1 self and
   "weaker" for a level-5 one.

   RETURN: FR_OK 0; FR_NOSELF -1 self not in the table; FR_BADBLOB -2 the blob refused; FR_NOPOOL -3 an automatic slot
   found no candidate at all (pool too small or no room); FR_GIVEN -4 a given entry or the given venues refused
   (details in why[]). On
   any < 0 Motore installs no friendlies (FR_TRACE = the code in test builds). why[k] = 0 on every success path.
   The checks run in this order: FR_BADBLOB, FR_NOSELF, FR_GIVEN (entries, then venues), FR_NOPOOL (*out zeroed
   first). Byte +5 and the index's sort order are not checked; a word resolves through the first index entry of its
   (world, file). avoid == NULL is navoid 0. The word 0xFFFF (file 255, ordinal 255) is always FR_NONE. */
#ifndef FRPICK_H
#define FRPICK_H

#ifndef FRPICK_NO_STDINT
#include <stdint.h>
#endif

#define FRSS_VERSION    2

#define FR_OK           0
#define FR_NOSELF       (-1)
#define FR_BADBLOB      (-2)
#define FR_NOPOOL       (-3)
#define FR_GIVEN        (-4)

#define FR_E_NOCLUB     (-1)            /* why[k] */
#define FR_E_SELF       (-2)
#define FR_E_BTEAM      (-3)
#define FR_E_DUP        (-4)
#define FR_E_HOME       (-5)            /* reserved: not used by the given list any more (Davide 16/11) */
#define FR_E_ROOM       (-6)
#define FR_E_VENUE      (-7)            /* on all four slots: FR_VENUES(mask) is not 2 home + 2 away */

#define FR_STRONGER     0               /* band[k] */
#define FR_SIMILAR      1
#define FR_WEAKER       2
#define FR_FAR_UP       3               /* band[k] only: never wanted (nearest-band rule or a given club) */
#define FR_FAR_DOWN     4

#define FR_NONE         0xFFFFu         /* an empty given entry / self2 without a B team */
#define FR_AUTO(band)   (0xF0FFu | (uint32_t)(band) << 8)   /* given[k]: an automatic slot pinned to FR_STRONGER /
                                                               FR_SIMILAR / FR_WEAKER (0xF0FF / 0xF1FF / 0xF2FF) */
#define FR_VENUES(mask) (0x100u | (mask))                   /* nhome: the venues as given (2 + 2), bit k = home */

typedef struct {
    uint16_t word[4];                   /* the opponents' team words, in play order */
    uint8_t home;                       /* bit k: friendly k at home */
    uint8_t fb;                         /* bit k: slot k filled by the nearest-band rule */
    uint8_t band[4];                    /* FR_STRONGER .. FR_FAR_DOWN: where word[k]'s strength falls */
    int8_t why[4];                      /* 0, or the FR_E_* code of a refused given entry / FR_E_VENUE x 4 */
} FrPick;

typedef struct {
    uint32_t room;                      /* tc_room(): clubs the cache can still take */
    int (*cached)(void *ctx, uint16_t word);   /* nonzero: already in the team cache (FindTeamInCache) */
    void *ctx;
} FrRoom;

int fr_pick(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t self, uint16_t self2,
            const uint16_t *given, const uint16_t *avoid, uint32_t navoid, const FrRoom *room,
            uint32_t season, uint32_t seed, uint32_t nhome, FrPick *out);

uint32_t fr_level(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t word);     /* 1 .. 5, 0 = no level */

#endif
