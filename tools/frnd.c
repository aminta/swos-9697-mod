/* tools/frnd.c - 4.2 preseason friendlies (a), the engine side (Motore). Linked into the obj4 band FRND (swreg
   FRND_AT, with frpick.c); the agreed interface: tools/frnd.h + internal/handoff/friendlies-a-interface.md.

   This file holds the engine's pure parts (no game state of their own; host-tested by tools/hosttest/tests/
   test_frnd.py):
     fr_turns   the four weeks of the season's friendlies from the career calendar (the "Turns" rule, run time)
     fr_fee     a friendly's fee from G (the club's league gate, cseg_3CB08 home = away = the career club), its band
                (FrPick.band after any fallback) and its venue (Mercato's table, OK 16/11)
     fr_result  FR_ST after a friendly decided (played count, W/D/L counts) */
#include <stdint.h>
#include "frnd.h"

/* The career calendar: entries back to back from cal, their count the word at cal - 4; an entry: +0 db slot, +1 db
   week, +2 dw length (0 = the end), +6 db the league day's matches (slot 0: > 0 = a played day).
   F = the first slot-0 entry with +6 > 0; E = F & ~1; while an entry BLOCKS the window [E-8, E-1]: E = the earliest
   such entry's week & ~1. An entry blocks when it is in the window and it is not a continental slot-3 entry, or its
   week is one of the turns E-8, E-6, E-4, E-2 (a UEFA Q1 club keeps 48/50/52/54 between its odd-week legs).
   out[k] = E - 8 + 2k; turns below 0 dropped (out[k] = 0xFF). Returns the turns kept (0 = no league day found). */
static int fr_blocks(const uint8_t *e, int lo) {
    int w = e[1];
    if (w < lo || w > lo + 7) return 0;
    return e[0] != 3 || !((w - lo) & 1);
}

uint32_t fr_turns(const uint8_t *cal, uint8_t out[4]) {
    uint32_t n = *(const uint16_t *)(cal - 4);
    int f = -1;
    const uint8_t *e = cal;
    for (uint32_t i = 0; i < n; i++) {
        uint32_t len = *(const uint16_t *)(e + 2);
        if (!len) break;
        if (e[0] == 0 && e[6]) { f = e[1]; break; }
        e += len;
    }
    for (int k = 0; k < 4; k++) out[k] = 0xFF;
    if (f < 0) return 0;
    int E = f & ~1;
    for (;;) {
        int lo = E - 8, low = -1;
        e = cal;
        for (uint32_t i = 0; i < n; i++) {
            uint32_t len = *(const uint16_t *)(e + 2);
            if (!len) break;
            if (fr_blocks(e, lo) && (low < 0 || e[1] < low)) low = e[1];
            e += len;
        }
        if (low < 0) break;
        E = low & ~1;
    }
    uint32_t kept = 0;
    for (int k = 0; k < 4; k++) {
        int w = E - 8 + 2 * k;
        if (w >= 0) { out[k] = (uint8_t)w; kept++; }
    }
    return kept;
}

/* % of G by band (FR_STRONGER, FR_SIMILAR, FR_WEAKER, FR_FAR_UP, FR_FAR_DOWN) and venue (home, away) */
static const uint8_t FR_PCT[5][2] = { { 100, 40 }, { 50, 20 }, { 30, 10 }, { 120, 50 }, { 20, 5 } };
#define FR_FEE_CAP 1048560u             /* fi_gate: D7 is 16 bits, << 4 */

/* the credited fee (fi_gate's D7 << 4): floor(G * pct / 100), capped, rounded down to 16 */
uint32_t fr_fee(uint32_t g, uint32_t band, uint32_t home) {
    if (band > 4) return 0;
    uint64_t f = (uint64_t)g * FR_PCT[band][home ? 0 : 1] / 100;
    if (f > FR_FEE_CAP) f = FR_FEE_CAP;
    return (uint32_t)f & ~15u;
}

/* FR_ST after friendly k (0..3) decided: gf / ga the career club's goals for / against. The played count = k + 1;
   W / D / L counts (bits 4-6 / 7-9 / 10-12 of +10) + 1; bits 0-3, 13-15 kept. */
void fr_result(uint8_t *st, uint32_t k, uint32_t gf, uint32_t ga) {
    uint32_t fl = FR_FLAGS(st);
    uint32_t sh = gf > ga ? 4 : gf == ga ? 7 : 10;
    uint32_t c = (fl >> sh) & 7;
    if (c < 7) fl = (fl & ~(7u << sh)) | (c + 1) << sh;
    st[10] = (uint8_t)fl; st[11] = (uint8_t)(fl >> 8);
    st[1] = (uint8_t)((st[1] & ~7u) | ((k + 1) & 7));
}
