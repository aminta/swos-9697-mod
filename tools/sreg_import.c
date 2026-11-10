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
      byte, +25: RI kind 0 keeps a slot's level, pg_season sets its group); off the files (the RI pool state: a pool
      club not swapped on, a club swapped off) -> SR_REG_POOL when the spec has pool rows, else SR_REG_OUT (MC 11/11:
      S7's file 144 = the 9 groups only, the stand-ins off-file as in 4.1); SR_REG_OUT in the spec stays SR_REG_OUT;
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
        } else                                          /* (off the files: the pool rows if the spec has them) */
            w->nd[c] = s == SR_REG_OUT || imp_file(r, SR_REG_POOL) < 0 ? SR_REG_OUT : SR_REG_POOL;
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

/* The import's RI_STATE (MC 11/11, model (i), binding; n7-p4.md §9b's RI row): RI stays live for Italy on S7's Serie D
   file (file_new: 144, its rows only; the stand-ins off-file, as in 4.1). An off-file club on a row is RI's identity
   map (map[r] = identity + 1), never a moved record; the registry only mirrors it. So sreg_import's swaps split by
   kind: file <-> file (b != SR_REG_NONE) move records (the exe's record path), pool swaps (b == SR_REG_NONE) are RI
   maps -- one only on file_new (another file: refused, SREG_RI_KIND).
   Identities in file_new's RI space (gplay.c ri_*): 0..255 = the record at that row of the file as the game reads it
   after the import's file <-> file moves; 256 + k = record k of the S7 RS file. newpool[k41] (s7pack, next to
   import41.csv): a 4.1 pool record -> its S7 RS index, 0xFF = it left the pool (S7's 6 joiners: PENDING-placed).
   Inputs: r / sw / ns = sreg_import's registry and swaps; spec / nf / spec_div / n / old_ord as for sreg_import;
   old_lay / new_lay = the two RI tables' layouts (sreg.ri_layout: db files; per file db world, db file, dw map offset,
   dw slots, db pools, pools x db n); old_ri = the save's RI_STATE (SREG_RI_SIZE B, gplay.c struct ri_state);
   new_ri = the S7 one. Every file of new_lay found in old_lay (same world and file; Italy's: file_old -> file_new)
   gets its state: another file's copied as it is (same slots and pools, else SREG_RI_LAYOUT), Italy's translated:
   - init: the old one; 0 (no season end with RI yet) -> maps / queue empty, and no pool swap allowed;
   - maps[o] (o < file_new's rows = its slots): 0 if the club the registry puts on row o owns the record there, else
     the club's identity + 1 (none: SREG_RI_NOID);
   - the queue (its one pool): the old entries in order, each the club with that 4.1 identity (old_ord; none:
     SREG_RI_QUEUE): a joiner leaves it (every joiner must be in it: SREG_RI_SIX), any other club off the files now
     (else SREG_RI_QUEUE) -> its S7 identity; the length = the S7 pool's n (else SREG_RI_LAYOUT).
   0, or a refusal with *bad = the club's ident (-1: no club). Deterministic; old_ri never written. */
#define SREG_RI_SIZE 2332               /* ripool.RI_SIZE: init[8], qn[20], q[192] u16, ovr[20][16] u16, maps[640] u16 */
enum { SREG_RI_INIT = 0, SREG_RI_QN = 8, SREG_RI_Q = 28, SREG_RI_OVR = 412, SREG_RI_MAPS = 1052 };
enum { SREG_RI_ARGS = -21, SREG_RI_LAYOUT = -22, SREG_RI_KIND = -23, SREG_RI_NOID = -24, SREG_RI_QUEUE = -25,
       SREG_RI_SIX = -26, SREG_RI_POOLMAP = -27, SREG_RI_ROWS = -28 };
typedef struct {
    sr_registry rec;                    /* the spec's places, then each row's record owner after the file <-> file moves */
    uint16_t id[SR_REG_CLUBS];          /* a club's identity in file_new's RI space, SR_REG_NONE */
} sreg_ri_work;
typedef struct { int32_t world, file, moff, nmap, np, pi, qo; const uint8_t *n; } sreg_ri_ent;

static int32_t ri_ent(const uint8_t *lay, int32_t world, int32_t file, sreg_ri_ent *e)
{
    const uint8_t *p = lay + 1;
    int32_t pi = 0, qo = 0;
    for (int32_t k = 0; k < lay[0]; k++) {
        e->world = p[0]; e->file = p[1]; e->moff = p[2] | p[3] << 8; e->nmap = p[4] | p[5] << 8; e->np = p[6];
        e->n = p + 7; e->pi = pi; e->qo = qo;
        for (int32_t j = 0; j < e->np; j++) qo += e->n[j];
        pi += e->np;
        if (e->world == world && e->file == file) return k;
        p += 7 + e->np;
    }
    return -1;
}

static uint16_t ri_get(const uint8_t *b, int32_t at) { return (uint16_t)(b[at] | b[at + 1] << 8); }
static void ri_put(uint8_t *b, int32_t at, uint16_t v) { b[at] = (uint8_t)v; b[at + 1] = (uint8_t)(v >> 8); }

static int32_t ri_fi(const sr_registry *r, uint8_t file)
{
    for (int32_t i = 0; i < r->nfiles; i++) if (r->f[i].file == file) return i;
    return -1;
}

int32_t sreg_ri_import(const sr_registry *r, const sr_reg_file *spec, int32_t nf, const uint8_t *spec_div, int32_t n,
                       const uint16_t *old_ord, const sr_reg_swap *sw, int32_t ns, const uint8_t *newpool,
                       int32_t npool_old, const uint8_t *old_lay, const uint8_t *new_lay, uint8_t world,
                       uint8_t file_old, uint8_t file_new, const uint8_t *old_ri, uint8_t *new_ri, sreg_ri_work *w,
                       int32_t *bad)
{
    if (!bad) return SREG_RI_ARGS;
    *bad = -1;
    if (!r || !spec || !spec_div || !old_ord || (ns && !sw) || !newpool || !old_lay || !new_lay || !old_ri || !new_ri ||
        !w || n != r->nclub || npool_old < 0)
        return SREG_RI_ARGS;
    if (sr_reg_build(&w->rec, nf, spec, n, spec_div)) return SREG_RI_ARGS;
    const int32_t fi = ri_fi(r, file_new);
    if (fi < 0) return SREG_RI_ARGS;
    int32_t npsw = 0;
    for (int32_t k = 0; k < ns; k++) {                  /* the record owners: file <-> file moves only */
        const int32_t ia = ri_fi(r, (uint8_t)sw[k].a), oa = sw[k].a >> 8;
        if (ia < 0) return SREG_RI_ARGS;
        if (sw[k].b == SR_REG_NONE) {
            if (ia != fi) { *bad = sw[k].on; return SREG_RI_KIND; }
            npsw++;
            continue;
        }
        const int32_t ib = ri_fi(r, (uint8_t)sw[k].b), ob = sw[k].b >> 8;
        if (ib < 0) return SREG_RI_ARGS;
        const uint16_t t = w->rec.at[ia][oa];
        w->rec.at[ia][oa] = w->rec.at[ib][ob]; w->rec.at[ib][ob] = t;
    }
    for (int32_t i = 0; i < r->nfiles; i++)             /* off file_new every row's club owns its record */
        for (int32_t o = 0; i != fi && o < r->rows[i]; o++)
            if (r->at[i][o] != w->rec.at[i][o]) { *bad = r->at[i][o]; return SREG_RI_KIND; }
    for (int32_t c = 0; c < n; c++) w->id[c] = SR_REG_NONE;
    for (int32_t o = 0; o < r->rows[fi]; o++) w->id[w->rec.at[fi][o]] = (uint16_t)o;
    int32_t njoin = 0;
    for (int32_t c = 0; c < n; c++) {                   /* the stand-ins: 256 + their S7 RS index; the joiners: none */
        const uint8_t s = spec_div[c];
        const int join = s != SR_REG_POOL && s != SR_REG_OUT && (old_ord[c] == SREG_OLD_NONE || old_ord[c] >= SREG_RIS);
        const int32_t k = old_ord[c] == SREG_OLD_NONE || old_ord[c] < SREG_RIS ? -1 : old_ord[c] - SREG_RIS;
        njoin += join && k >= 0;
        if (k < 0) continue;
        if (k >= npool_old || join != (newpool[k] == 0xFF)) { *bad = c; return SREG_RI_POOLMAP; }
        if (!join) {
            if (w->id[c] != SR_REG_NONE) { *bad = c; return SREG_RI_POOLMAP; }
            w->id[c] = (uint16_t)(SREG_RIS + newpool[k]);
        }
    }
    for (int32_t b = 0; b < SREG_RI_SIZE; b++) new_ri[b] = 0;
    sreg_ri_ent ne, oe;
    for (int32_t k = 0; k < new_lay[0]; k++) {
        const uint8_t *p = new_lay + 1;                 /* (new_lay's k-th file: walk to it) */
        for (int32_t j = 0; j < k; j++) p += 7 + p[6];
        const int32_t nk = ri_ent(new_lay, p[0], p[1], &ne);
        const int italy = ne.world == world && ne.file == file_new;
        const int32_t ok_ = ri_ent(old_lay, ne.world, italy ? file_old : ne.file, &oe);
        if (nk != k) return SREG_RI_LAYOUT;             /* (one entry per world and file) */
        if (ok_ < 0) continue;                          /* (a file new in the table: its first season end sets it) */
        if (ne.moff + ne.nmap > 640 || oe.moff + oe.nmap > 640 || ne.pi + ne.np > 20 || oe.pi + oe.np > 20)
            return SREG_RI_LAYOUT;
        new_ri[SREG_RI_INIT + k] = old_ri[SREG_RI_INIT + ok_];
        if (!italy) {
            if (ne.nmap != oe.nmap || ne.np != oe.np) return SREG_RI_LAYOUT;
            for (int32_t j = 0; j < ne.np; j++) if (ne.n[j] != oe.n[j]) return SREG_RI_LAYOUT;
            for (int32_t x = 0; x < ne.nmap; x++)
                ri_put(new_ri, SREG_RI_MAPS + 2 * (ne.moff + x), ri_get(old_ri, SREG_RI_MAPS + 2 * (oe.moff + x)));
            for (int32_t j = 0, q = 0; j < ne.np; q += ne.n[j], j++) {
                new_ri[SREG_RI_QN + ne.pi + j] = old_ri[SREG_RI_QN + oe.pi + j];
                for (int32_t x = 0; x < ne.n[j]; x++)
                    ri_put(new_ri, SREG_RI_Q + 2 * (ne.qo + q + x), ri_get(old_ri, SREG_RI_Q + 2 * (oe.qo + q + x)));
                for (int32_t x = 0; x < 16; x++)
                    ri_put(new_ri, SREG_RI_OVR + 2 * (16 * (ne.pi + j) + x), ri_get(old_ri, SREG_RI_OVR + 2 * (16 * (oe.pi + j) + x)));
            }
            continue;
        }
        if (ne.np != 1 || oe.np != 1 || ne.nmap != r->rows[fi]) return SREG_RI_LAYOUT;
        if (!old_ri[SREG_RI_INIT + ok_]) {              /* (no RI season end yet: nothing swapped, ri_season starts it) */
            if (npsw) return SREG_RI_LAYOUT;
            continue;
        }
        for (int32_t o = 0; o < ne.nmap; o++) {
            const uint16_t c = r->at[fi][o];
            if (c == w->rec.at[fi][o]) continue;
            if (w->id[c] == SR_REG_NONE) { *bad = c; return SREG_RI_NOID; }
            ri_put(new_ri, SREG_RI_MAPS + 2 * (ne.moff + o), (uint16_t)(w->id[c] + 1));
        }
        int32_t m = 0, out = 0;
        const int32_t qn = old_ri[SREG_RI_QN + oe.pi];
        if (qn > oe.n[0]) return SREG_RI_LAYOUT;
        for (int32_t x = 0; x < qn; x++) {
            const uint16_t e = ri_get(old_ri, SREG_RI_Q + 2 * (oe.qo + x));
            int32_t c = 0;
            while (c < n && old_ord[c] != e) c++;
            if (c == n) return SREG_RI_QUEUE;
            const uint8_t s = spec_div[c];
            if (s != SR_REG_POOL && s != SR_REG_OUT && old_ord[c] >= SREG_RIS) { out++; continue; }   /* (a joiner) */
            if (r->word[c] != SR_REG_NONE || w->id[c] == SR_REG_NONE || m == ne.n[0]) { *bad = c; return SREG_RI_QUEUE; }
            ri_put(new_ri, SREG_RI_Q + 2 * (ne.qo + m++), w->id[c]);
        }
        if (out != njoin) return SREG_RI_SIX;
        if (m != ne.n[0]) return SREG_RI_LAYOUT;
        new_ri[SREG_RI_QN + ne.pi] = (uint8_t)m;
    }
    return 0;
}

/* The import's someLeaguesTable (MC 11/11, from Shaved's S7-G 21d9407): a club's byte (the game's per-global division
   state, and the same for its sltcopy: call twice) moves from its 4.1 global to its S7 one, in the walk's pass. In a
   4.1 save file 102's rows 100..255 had globals 192..347; in S7 those are file 144's first run, file 102 keeps 92..191.
   Global numbers come from run tables (sreg.glob_bytes, globnum.split / base): db files; per file db file, db runs,
   runs x (dw first global, dw count) - glob(file, ord) = the run holding ord, counted in order (globnum.glob).
   old_gl = 4.1's (102: one run of 256 from 92), new_gl = S7's (102: 92 x 100; 144: 192 x 156 + 2283 x 6).
   new_slt = old_slt with every global of either table zeroed, then for each club on a row in both layouts
   (old_word[c] and r->word[c] not SR_REG_NONE) new_slt[its S7 global] = old_slt[its 4.1 global]. A club on a row now
   with no 4.1 row (S7's joiners) keeps 0 (the season start fills it). A stand-in on a row through RI (model (i)) uses
   that row's global, as ri_copy keeps the slot's bytes 0..4. The byte is copied as it is: it assumes both files'
   globals read it against the same league base (Italy's one league). Returns the clubs moved; SREG_SLT_ARGS, or
   SREG_SLT_GLOB with *bad = the club whose word has no global (a file or ordinal past its table). */
enum { SREG_SLT_ARGS = -31, SREG_SLT_GLOB = -32 };

static int32_t gl_glob(const uint8_t *gl, uint16_t word)
{
    const uint8_t *p = gl + 1;
    for (int32_t k = 0; k < gl[0]; k++) {
        const int32_t nr = p[1];
        if (p[0] == (word & 0xFF)) {
            int32_t o = word >> 8;
            for (int32_t j = 0; j < nr; j++) {
                const int32_t first = p[2 + 4 * j] | p[3 + 4 * j] << 8, cnt = p[4 + 4 * j] | p[5 + 4 * j] << 8;
                if (o < cnt) return first + o;
                o -= cnt;
            }
            return -1;
        }
        p += 2 + 4 * nr;
    }
    return -1;
}

static int32_t gl_zero(const uint8_t *gl, uint8_t *slt, int32_t nslt)
{
    const uint8_t *p = gl + 1;
    for (int32_t k = 0; k < gl[0]; k++) {
        for (int32_t j = 0; j < p[1]; j++) {
            const int32_t first = p[2 + 4 * j] | p[3 + 4 * j] << 8, cnt = p[4 + 4 * j] | p[5 + 4 * j] << 8;
            if (first + cnt > nslt) return -1;
            for (int32_t g = first; g < first + cnt; g++) slt[g] = 0;
        }
        p += 2 + 4 * p[1];
    }
    return 0;
}

int32_t sreg_slt_import(const sr_registry *r, const uint16_t *old_word, int32_t n, const uint8_t *old_gl,
                        const uint8_t *new_gl, const uint8_t *old_slt, uint8_t *new_slt, int32_t nslt, int32_t *bad)
{
    if (!bad) return SREG_SLT_ARGS;
    *bad = -1;
    if (!r || !old_word || !old_gl || !new_gl || !old_slt || !new_slt || old_slt == new_slt || n != r->nclub || nslt < 0)
        return SREG_SLT_ARGS;
    for (int32_t g = 0; g < nslt; g++) new_slt[g] = old_slt[g];
    if (gl_zero(old_gl, new_slt, nslt) || gl_zero(new_gl, new_slt, nslt)) return SREG_SLT_ARGS;
    int32_t moved = 0;
    for (int32_t c = 0; c < n; c++) {
        if (old_word[c] == SR_REG_NONE || r->word[c] == SR_REG_NONE) continue;
        const int32_t go = gl_glob(old_gl, old_word[c]), gn = gl_glob(new_gl, r->word[c]);
        if (go < 0 || gn < 0) { *bad = c; return SREG_SLT_GLOB; }
        new_slt[gn] = old_slt[go];
        moved++;
    }
    return moved;
}

#endif
