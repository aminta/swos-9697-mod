/* 4.2 preseason friendlies, part (b): the opponent pick (owner Mercato CPU; engine side Motore, review Convergence).
   Decisions: internal/handoff/friendlies-pick.md. Pure C: no exe symbol, no global, no libc beyond memset / memcpy,
   no malloc, no file I/O, stack < 256 B (no array sized by the pool: the table is walked in place). Linked by Motore
   in FRND; the host tests build it natively (tools/hosttest/tests/test_frpick.py).

   THE TABLE (FRSS v2, one world's slice of DATA\FRSS.DAT, read by Motore at the season start into a scratch buffer):
     +0 'FRSS'  +4 db version 2  +5 db 0  +6 dw blocks
     index, sorted by (world, file): blocks x [db world, db file, db count, db country, dw first value's index]
     values: dw strength per club in ordinal order (0 = no club in that record: never picked, never accepted)
   A team word = file | ordinal << 8. strength = statespec.club_strength (best 11 player prices, at least 5) in every
   world. country = one id per country (Italy's files 115 + 144 share one id). A v1 blob, a bad magic or a length
   that does not match the index -> FR_BADBLOB.

   THE POOL: the table's clubs of the call's world with strength > 0, of ANOTHER country than self's (so never self,
   never a B team of self's country), never self2 (the B team; self2 = 0xFFFF: no B team, nothing more is excluded),
   never twice in the same four, and only while the team cache has room (room below).

   THE BANDS (S = self's strength, d = club's strength - S, margin M = max(11, S / 10)):
     FR_STRONGER  d >  M        FR_SIMILAR  -M <= d <= M        FR_WEAKER  d < -M
   The mix: 1 stronger, 2 similar, 1 weaker. Play order of the automatic four: weaker, similar, similar, stronger.

   THE CHOICE of one automatic slot (one pass over the table per slot): the candidate with the smallest key
     (fallback distance, last-season penalty, country penalty, hash(seed, season, slot, word))
   - fallback distance: 0 inside the wanted band; outside it, how far the club's strength lies from the band
     (stronger: (S + M + 1) - strength; weaker: strength - (S - M - 1); similar: |d| - M). THE "NEAREST BAND" RULE:
     when the wanted band has no candidate, the slot takes the club nearest to that band's edge - a top club with no
     stronger opponent gets the strongest club left, a bottom club with no weaker one the weakest left. Such a slot
     has bit k of FrPick.fb set and band[k] = the band its club really falls in.
   - last-season penalty: 1 for a word in avoid[] (last season's four, FR_ST +2..+9), else 0: avoided while the
     band allows, never at the cost of the band.
   - country penalty: 1 for a country already used by an earlier slot of the four, else 0: four distinct countries
     where possible.
   - hash: a fixed mix of seed, season, slot and word (seed is opaque: Motore's sc_step_c formula + a FR constant).
   Same inputs -> the same output, at any -O level.

   THE ROOM (MC 16/11, section 1's tc_room / tc_reserve): with room != NULL the pick loads at most room->room clubs
   that room->cached() says are not in the team cache (cached clubs cost nothing). An automatic slot skips a club
   that would not fit and takes the next candidate by the key above; a given club that does not fit is refused
   (FR_E_ROOM). room == NULL: no limit. Unit: one team record in the team cache per club not yet cached; a pick adds
   at most 4 (its four clubs; a club already cached adds 0 and is never counted twice). cached is a plain cdecl C
   function pointer (Motore's gplay shim wraps FindTeamInCache; frpick never calls an exe address), called at most
   once per candidate per slot pass and never with room == NULL (agreed with Motore 16/11).

   THE GIVEN LIST (open for a player's choice, MC 16/11; not approved as UI): given[k] = a club the player chose for
   slot k, 0xFFFF = empty; given == NULL is exactly 4 x 0xFFFF. Each given entry is checked in this order:
     FR_E_NOCLUB  not in this world's table, ordinal >= its file's count, or strength 0
     FR_E_SELF    = self          FR_E_BTEAM  = self2          FR_E_DUP    = an earlier given entry
     FR_E_HOME    self's country  FR_E_ROOM   no room in the team cache
   Any refusal: fr_pick returns FR_GIVEN with why[k] set for every refused entry (0 for the others) and out->word[]
   undefined: a refused entry is NEVER silently replaced. Valid given entries keep their slot (their band = where
   their strength falls) and cover that band in the 1 / 2 / 1 mix; the empty slots take the uncovered bands, taken in
   the order similar, similar, weaker, stronger (as many as there are empty slots), placed in the empty slots in
   ascending slot order weakest first. last-season avoid does not apply to a given club.

   THE VENUES (after the list is final): the nhome opponents with the lowest strength are played at home (ties: the
   lower slot first), the others away; bit k of out->home = friendly k at home. nhome > 4 -> 4. Default 2 (2H / 2A).

   RETURN: FR_OK 0; FR_NOSELF -1 self not in the table; FR_BADBLOB -2 the blob refused; FR_NOPOOL -3 an automatic slot
   found no candidate at all (pool too small or no room); FR_GIVEN -4 a given entry refused (details in why[]). On
   any < 0 Motore installs no friendlies (FR_TRACE = the code in test builds). why[k] = 0 on every success path. */
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
#define FR_E_HOME       (-5)
#define FR_E_ROOM       (-6)

#define FR_STRONGER     0               /* band[k] */
#define FR_SIMILAR      1
#define FR_WEAKER       2

#define FR_NONE         0xFFFFu         /* an empty given entry / self2 without a B team */

typedef struct {
    uint16_t word[4];                   /* the opponents' team words, in play order */
    uint8_t home;                       /* bit k: friendly k at home */
    uint8_t fb;                         /* bit k: slot k filled by the nearest-band rule */
    uint8_t band[4];                    /* FR_STRONGER / FR_SIMILAR / FR_WEAKER: where word[k]'s strength falls */
    int8_t why[4];                      /* 0, or the FR_E_* code of a refused given entry */
} FrPick;

typedef struct {
    uint32_t room;                      /* tc_room(): clubs the cache can still take */
    int (*cached)(void *ctx, uint16_t word);   /* nonzero: already in the team cache (FindTeamInCache) */
    void *ctx;
} FrRoom;

int fr_pick(const uint8_t *frss, uint32_t len, uint8_t world, uint16_t self, uint16_t self2,
            const uint16_t *given, const uint16_t *avoid, uint32_t navoid, const FrRoom *room,
            uint32_t season, uint32_t seed, uint32_t nhome, FrPick *out);

#endif
