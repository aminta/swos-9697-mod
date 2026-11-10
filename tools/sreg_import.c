/* N7 piece 4 (n7-p4.md §4 step 1, n7-s7-clubmap.md §3 point 2): the old-save import's old words -- each ident's
   team word in a 4.1 save, from its 4.1 identity (sreg.py old_ord, the shaped pack's import41.csv) and the save's RI
   slot map; and sreg_import, the import's registry (n7-p4.md §9c, MC's option 1). Host-only today (test_sreg
   test_sreg_oldwords / test_sreg_import, native builds); sreg.c #includes it once the import has its obj4 page
   (swreg.SREG2_AT) and MC's S7 glue calls it.

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

/* The import's registry (n7-p4.md §9c, MC 10/11: option 1, binding): a 4.1 save (one file, RI swaps) -> the S7 registry.
   1. sr_reg_build from the spec (spec / nf, spec_div = SREG_DIV: each ident's division in the shaped pack, n = its clubs);
   2. old_word[ident] = sreg_old_words (old_ord, the save's RI slot map maps / nslot / npool of file `file`);
   3. nd[ident] = the club's ACTUAL division in the save: on slot x -> slot_div[x] (the save's file record x's division
      byte, +25: RI kind 0 keeps a slot's level, pg_season sets its group); off the files -> SR_REG_POOL (the RI pool
      state: a pool club not swapped on, a club swapped off), or its spec value when that is SR_REG_POOL / SR_REG_OUT;
      the PENDING clubs (below) -> their spec division;
   4. ONE sr_reg_season(r, nd, no order, contiguous 0: the exe's) -- the swaps (sw, at most maxsw) for the exe's
      normal record-move path; no replay of past seasons, no RI order;
   5. the word map for the walker: sr_wmap_import(r, old_word) (map, at most maxmap pairs, sorted).
   PENDING (§9a.5): a club the spec puts in a division (not the pool, not off) whose 4.1 identity was off the file
   (a pool index, or none) -- S7's 6 joiners. It is on its S7 row in the registry at once; the caller holds its
   record's division byte back until the season end that clears PENDING. One of them on a slot in the save (RI swapped
   it on) is refused (MC: no fallback).
   Returns the swaps' count (>= 0), res filled (flags IMPORTED, + PENDING | season << 8 when a club is pending, the
   pending idents in ident order); or a refusal SREG_IMP_* with res->bad = the club's ident (SREG_IMP_LOST: 0x8000 |
   the slot; the caller shows the club key, CONVENTIONS 14a) -- r then holds the spec's registry, nothing to apply.
   Deterministic: the same inputs give the same registry, swaps, map and res (w's and r's old bytes never read). */
#define SREG_PEND_MAX 16
enum { SREG_IMP_ARGS = -1, SREG_IMP_SPEC = -2, SREG_IMP_MAP = -3, SREG_IMP_LOST = -4, SREG_IMP_DIV = -5,
       SREG_IMP_SIX = -6, SREG_IMP_PEND = -7, SREG_IMP_BALANCE = -8, SREG_IMP_ROOM = -9, SREG_IMP_WMAP = -10 };
typedef struct {
    uint16_t old_word[SR_REG_CLUBS];
    uint8_t nd[SR_REG_CLUBS];
    sr_reg_work rw;
} sreg_imp_work;
typedef struct {
    int32_t nswap, nmap, npend, bad;
    uint32_t flags;                     /* SREG_FLAGS: IMPORTED 1 | PENDING 2 | season << 8 */
    uint16_t pend[SREG_PEND_MAX];
} sreg_imp_res;

static int32_t imp_file(const sr_registry *r, uint8_t d)       /* the file index holding division d, -1 off the files */
{
    for (int32_t i = 0; i < r->nfiles; i++) {
        if (d == SR_REG_POOL && r->f[i].pool) return i;
        for (int32_t k = 0; k < r->f[i].ndiv; k++) if (r->f[i].div[k] == d) return i;
    }
    return -1;
}

static int32_t imp_spec_file(const sr_registry *r, int32_t c)  /* the file index of club c's place as built */
{
    const uint16_t w = r->word[c];
    if (w == SR_REG_NONE) return -1;
    for (int32_t i = 0; i < r->nfiles; i++) if (r->f[i].file == (w & 0xFF)) return i;
    return -1;
}

int32_t sreg_import(sr_registry *r, const sr_reg_file *spec, int32_t nf, const uint8_t *spec_div, int32_t n,
                    const uint16_t *old_ord, const uint16_t *maps, int32_t nslot, int32_t npool, uint8_t file,
                    const uint8_t *slot_div, uint32_t season, sreg_imp_work *w, sr_reg_swap *sw, int32_t maxsw,
                    sr_wpair *map, int32_t maxmap, sreg_imp_res *res)
{
    if (!res) return SREG_IMP_ARGS;
    res->nswap = res->nmap = res->npend = 0; res->bad = -1; res->flags = 0;
    if (!r || !spec || !spec_div || !old_ord || !slot_div || !w || !sw || !map || maxsw < 0 || maxmap < 0)
        return SREG_IMP_ARGS;
    if (sr_reg_build(r, nf, spec, n, spec_div)) return SREG_IMP_SPEC;
    if (sreg_old_words(old_ord, n, maps, nslot, npool, file, w->old_word) < 0) return SREG_IMP_MAP;
    for (int32_t x = 0; x < nslot; x++) {               /* every club on the save's file has an ident: none lost */
        const int32_t id = maps && maps[x] ? maps[x] - 1 : x;
        int32_t c = 0;
        while (c < n && old_ord[c] != id) c++;
        if (c == n) { res->bad = 0x8000 | x; return SREG_IMP_LOST; }
    }
    for (int32_t c = 0; c < n; c++) {
        const uint8_t s = spec_div[c];
        const uint16_t ow = w->old_word[c];
        const int pend = s != SR_REG_POOL && s != SR_REG_OUT && (old_ord[c] == SREG_OLD_NONE || old_ord[c] >= SREG_RIS);
        if (pend && ow != SR_REG_NONE) { res->bad = c; return SREG_IMP_SIX; }
        if (pend) {
            if (res->npend == SREG_PEND_MAX) { res->bad = c; return SREG_IMP_PEND; }
            res->pend[res->npend++] = (uint16_t)c;
            w->nd[c] = s;
        } else if (ow != SR_REG_NONE) {
            w->nd[c] = slot_div[ow >> 8];
            if (w->nd[c] >= SR_REG_POOL || imp_file(r, w->nd[c]) < 0) { res->bad = c; return SREG_IMP_DIV; }
        } else
            w->nd[c] = s == SR_REG_OUT ? SR_REG_OUT : SR_REG_POOL;
    }
    for (int32_t i = 0; i < r->nfiles; i++) {           /* each file's comings and goings (sr_reg_season's -1, named) */
        int32_t in = 0;
        for (int32_t c = 0; c < n; c++) in += imp_file(r, w->nd[c]) == i;
        if (in == r->rows[i]) continue;
        for (int32_t c = 0; c < n && res->bad < 0; c++)     /* over: the first comer; under: the first leaver */
            if (in > r->rows[i] ? imp_file(r, w->nd[c]) == i && imp_spec_file(r, c) != i
                                : imp_spec_file(r, c) == i && imp_file(r, w->nd[c]) != i) res->bad = c;
        return SREG_IMP_BALANCE;
    }
    const int32_t ns = sr_reg_season(r, w->nd, 0, 0, 0, &w->rw, sw, maxsw);
    if (ns == -2) { sr_reg_build(r, nf, spec, n, spec_div); return SREG_IMP_ROOM; }
    if (ns < 0 || sr_reg_check(r)) { sr_reg_build(r, nf, spec, n, spec_div); return SREG_IMP_BALANCE; }
    const int32_t nm = sr_wmap_import(r, w->old_word, n, map, maxmap);
    if (nm < 0) { sr_reg_build(r, nf, spec, n, spec_div); return nm == -2 ? SREG_IMP_ROOM : SREG_IMP_WMAP; }
    res->nswap = ns; res->nmap = nm;
    res->flags = SR_REGSAVE_IMPORTED | (res->npend ? SR_REGSAVE_PENDING | (season & 0xFF) << 8 : 0);
    return ns;
}

#endif
