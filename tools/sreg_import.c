/* N7 piece 4 (n7-p4.md §4 step 1, n7-s7-clubmap.md §3 point 2): the old-save import's old words -- each ident's
   team word in a 4.1 save, from its 4.1 identity (sreg.py old_ord, the shaped pack's import41.csv) and the save's RI
   slot map. Host-only today (test_sreg test_sreg_oldwords, a native build); sreg.c #includes it with the import
   once the import has its obj4 page (swreg.SREG2_AT) and MC has answered how the import places RI-swapped clubs
   (spec places + swaps, or spec only).

   - old_ord[i]: the club's 4.1 identity in gplay's RI space: a row of the one-file team file (0 .. RIS-1) or
     RIS + its off-file pool index; SREG_OLD_NONE: a club 4.1 did not have.
   - maps[x] (x < nslot): RI_STATE.maps[moff + x] of that file: 0 = slot x holds its own record (identity x), else
     identity maps[x] - 1 (gplay.c ri_apply). maps may be 0: no RI state (no swaps yet).
   - old_word[i] = file | x << 8 for the slot x holding identity old_ord[i], else SR_REG_NONE (off the file in that
     save: a pool club not swapped on, a club swapped off, a club 4.1 did not have).
   Returns the clubs on a slot, -1 on a bad map (an identity on two slots, or past RIS + npool), -2 on bad
   arguments (nslot past RIS). */
#ifndef SREG_IMPORT_C
#define SREG_IMPORT_C

#define SREG_RIS 256                    /* gplay.c RIS */
#define SREG_OLD_NONE 0xFFFFu           /* sreg.py OLD_NONE */

int32_t sreg_old_words(const uint16_t *old_ord, int32_t n, const uint16_t *maps, int32_t nslot, int32_t npool,
                       uint8_t file, uint16_t *old_word)
{
    if (!old_ord || !old_word || n < 0 || nslot < 0 || nslot > SREG_RIS || npool < 0) return -2;
    for (int32_t x = 0; x < nslot; x++) {               /* the map first: every identity on one slot at most */
        int32_t id = maps && maps[x] ? maps[x] - 1 : x;
        if (id >= SREG_RIS + npool) return -1;
        for (int32_t y = 0; y < x; y++)
            if ((maps && maps[y] ? maps[y] - 1 : y) == id) return -1;
    }
    int32_t on = 0;
    for (int32_t i = 0; i < n; i++) {
        old_word[i] = SR_REG_NONE;
        if (old_ord[i] == SREG_OLD_NONE) continue;
        for (int32_t x = 0; x < nslot; x++)
            if ((maps && maps[x] ? maps[x] - 1 : x) == old_ord[i]) {
                old_word[i] = (uint16_t)(file | x << 8);
                on++;
                break;
            }
    }
    return on;
}

#endif
