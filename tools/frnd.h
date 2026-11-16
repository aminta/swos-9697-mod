/* 4.2 preseason friendlies (a), the engine side (Motore): the interface the chooser page (FRCH, frc_choose) includes.
   The agreed text is internal/handoff/friendlies-a-interface.md ("FINAL (16/11" block); the pick is frpick.h (Mercato).

   FR_ST = SC_ST entry FR_E (12 B, gplay.c, saved with SC_ST: engine item 'SC'; agreed with Nazionali 16/11):
     +0  db the season handled (the game's season byte), 0 = none (an old save: that season has no friendlies)
     +1  db bits 0-2 = friendlies played (0..4); bits 3-7 spare (ask Motore first)
     +2  dw x 4 the opponents' team words, in play order (next season's avoid list)
     +10 dw bits 0-3 home flags (bit k = friendly k at home), bits 4-12 W/D/L counts (3 bits each),
            bit 13 NATIVE (reserved), bits 14-15 FR_MODE (written only by frc_choose; kept across the season rewrite)

   The season-start step (the tail of InitializeNewSeason, careers only, never on a load):
     given = 4 x FR_NONE, venues = 0xFF;
     frc_choose(&ctx, given, &venues) when linked (in test builds FR_GIVEN, when set, replaces the call);
     fr_pick(ctx.frss, ctx.len, ctx.world, ctx.self, ctx.self2, given, ctx.avoid, ctx.navoid, ctx.room, ctx.season,
             ctx.seed, venues == 0xFF ? ctx.nhome : FR_VENUES(venues), &out)   - the only call that installs;
     FR_ST written, friendly 1 installed (CAL_CUR = 0). frc_choose only previews (it may call fr_pick / fr_level with
     the same ctx values as often as it wants: both are pure; ctx.room's callback is the engine's cdecl shim). */
#ifndef FRND_H
#define FRND_H
#include "frpick.h"

#define FR_E            14              /* SC_ST entry index of FR_ST (SC_U = entry 15, the UEFA Super Cup) */
#define FR_SZ           12
#define FR_NPLAYED(st)  ((st)[1] & 7u)
#define FR_FLAGS(st)    ((uint32_t)(st)[10] | (uint32_t)(st)[11] << 8)
#define FR_NATIVE       (1u << 13)
#define FR_MODE_SH      14
#define FR_MODE_MASK    (3u << FR_MODE_SH)
#define FR_MODE_MEDIUM  0               /* AUTOMATIC, the 1/2/1 mix (old saves read 0) */
#define FR_MODE_EASY    1
#define FR_MODE_HARD    2
#define FR_MODE_CHOSEN  3
#define FR_MODE(st)     ((FR_FLAGS(st) & FR_MODE_MASK) >> FR_MODE_SH)

typedef struct {
    const uint8_t *frss;                /* the current world's FRSS v2 slice (read from FRSS.DAT at the season start) */
    uint32_t len;
    uint8_t world;
    uint16_t self, self2;               /* the career club's team word; its B team's or FR_NONE */
    const uint16_t *avoid;              /* last season's 4 (FR_ST +2..+9) */
    uint32_t navoid;
    const FrRoom *room;                 /* the team cache's room, or NULL */
    uint32_t season, seed, nhome;       /* nhome: the engine's default (2) */
    uint8_t *frst;                      /* FR_ST: frc_choose writes +10 bits 14-15 only */
} FrcCtx;

/* The chooser page (FRCH band, weak: absent = skipped, given stays 4 x FR_NONE, venues 0xFF). cdecl. *venues: 0xFF =
   ctx.nhome, else the venues mask (bit k = friendly k at home, 2 + 2), passed to fr_pick as FR_VENUES(*venues). */
void frc_choose(const FrcCtx *c, uint16_t given[4], uint8_t *venues);

#endif
