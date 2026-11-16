/* 4.2 preseason friendlies, the chooser's selection state (owner: Friends Choice, 42-frchoose). Pure C like frpick:
   no exe symbol, no global, no libc, no malloc. The page (tools/frchoose.c, FRCH band) holds one FrcSel and only calls
   these functions; the host test builds this file natively with frpick.c (tools/hosttest/tests/test_frcsel.py).

   NO RULE OF THE PICK LIVES HERE (MC / Mercato 16/11): bands, mix, validation, venues and levels are fr_pick's and
   fr_level's (tools/frpick.h). This file only (1) turns what the player set on the page into fr_pick's given[] and
   nhome, (2) calls fr_pick with the engine's own arguments (FrcCtx, Motore) for the preview, and (3) undoes a change
   that fr_pick refuses - a refused change is never replaced by something else, the page shows why.

   THE PAGE'S STATE
     level     what an EMPTY slot is: FRC_MIX (fr_pick's own 1 / 2 / 1 mix: given 0xFFFF) or FRC_EASY / FRC_MEDIUM /
               FRC_HARD (given FR_AUTO(weaker / similar / stronger)): frc_fill[] below is the ONE table.
     club[k]   the club the player chose for slot k, FR_NONE = empty. A chosen club keeps its slot at any level.
     venues    FRC_VENUES_AUTO = fr_pick's rule (nhome of the engine), else the 2 + 2 mask after a swap.
     out       fr_pick's last accepted answer for this state: what the page draws (every slot reveals its club).
     msg       0, or the code of the last refused change (frc_msg() below turns it into a text index).
   Every change goes through one path: the new state is tried with fr_pick; rc < 0 -> the old state and its
   preview stay, msg = the reason. fr_pick is pure and deterministic, so the engine's installing call (same FrcCtx,
   the given[] / venues frc_result() hands back) gives exactly `out`.

   THE VENUE SWAP (Davide's V2): FIRE on slot k's venue flips it together with the NEAREST slot of the other venue
   (ties: the lower slot), so the four stay 2 home + 2 away; the mask then stays as swapped while clubs change.

   THE REMEMBERED LEVEL: FR_ST +10 bits 14-15 (the high byte's bits 6-7), read by frc_init and written by frc_result;
   0 = FRC_MIX = what a save without the bits reads. (Bit meanings: friendlies-a-interface.md; not frozen until
   Davide's answer on the default - FRC_ST_* below is the one place.) */
#ifndef FRCSEL_H
#define FRCSEL_H

#include "frpick.h"

#ifndef FRND_H                          /* TEMPORARY until Motore's tools/frnd.h lands (same text, his field order): */
typedef struct {                        /* the engine's fr_pick arguments + FR_ST                                     */
    const uint8_t *frss; uint32_t len; uint8_t world; uint16_t self, self2; const uint16_t *avoid;
    uint32_t navoid; const FrRoom *room; uint32_t season, seed, nhome; uint8_t *frst;
} FrcCtx;
#endif
#if defined(__i386__)                   /* (the exe's layout: frchoose.py's test caller FRC_PROBE writes one by hand) */
_Static_assert(sizeof(FrcCtx) == 44 && __builtin_offsetof(FrcCtx, world) == 8 && __builtin_offsetof(FrcCtx, self) == 10 &&
               __builtin_offsetof(FrcCtx, self2) == 12 && __builtin_offsetof(FrcCtx, avoid) == 16 &&
               __builtin_offsetof(FrcCtx, room) == 24 && __builtin_offsetof(FrcCtx, season) == 28 &&
               __builtin_offsetof(FrcCtx, nhome) == 36 && __builtin_offsetof(FrcCtx, frst) == 40, "FrcCtx layout");
#endif

#define FRC_MIX         0               /* level */
#define FRC_EASY        1
#define FRC_MEDIUM      2
#define FRC_HARD        3
#define FRC_LEVELS      4

#define FRC_VENUES_AUTO 0xFF

#define FRC_ST_OFF      11              /* FR_ST +10 is a word: bits 14-15 = bits 6-7 of byte +11 */
#define FRC_ST_SHIFT    6

#define FRC_M_NONE      0               /* frc_msg(): the page's message texts */
#define FRC_M_CLUB      1               /* club not available (not in the table, own club, B team)   */
#define FRC_M_DUP       2               /* club chosen twice                                         */
#define FRC_M_ROOM      3               /* too many clubs in memory                                  */
#define FRC_M_NOPOOL    4               /* no opponents available for this choice                    */
#define FRC_M_COUNT     5

typedef struct {
    const FrcCtx *c;
    uint16_t club[4];
    uint8_t level;
    uint8_t venues;
    int8_t msg;
    FrPick out;
} FrcSel;

int frc_init(FrcSel *s, const FrcCtx *c);               /* fr_pick's return code; < 0: no page this season */
int frc_set_level(FrcSel *s, int dir);                  /* dir +1 / -1 (wraps); every setter: 0 or the refusal */
int frc_set_club(FrcSel *s, uint32_t k, uint16_t word); /* FR_NONE clears slot k */
int frc_swap_venue(FrcSel *s, uint32_t k);
int frc_trial(const FrcSel *s, uint32_t k, uint16_t word, uint8_t *band);   /* fr_given for `word` in slot k */
void frc_result(const FrcSel *s, uint16_t given[4], uint8_t *venues);       /* + the level into FR_ST          */
int frc_msg(int code);                                  /* a refusal code -> FRC_M_* */

#endif
