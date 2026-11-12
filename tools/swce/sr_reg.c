/*
 * sr_reg.c -- one league across N team files: the club registry (swc/1.4 countries.<c>.files; MC 42-s7reg).
 * A club's identity stays; its team word (file | ordinal << 8) is where its record is. Each file keeps its
 * divisions in fixed ranges of rows, so the season end's moves become record swaps: within a file or across
 * files (Italy 4.2: Serie C in file 102, Serie D in file 144), and with the off-file pool. Nothing in either
 * game uses it yet (the exe's part, applying the swaps to the team files and an old save, is the Mod's).
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;

static int32_t fidx(const sr_registry *r, u16 word)
{
    for (int32_t i = 0; i < r->nfiles; i++)
        if (r->f[i].file == (word & 0xFF))
            return (word >> 8) < r->rows[i] ? i : -1;
    return -1;
}

static int32_t known_div(const sr_registry *r, u8 d)
{
    if (d == SR_REG_OUT) return 1;
    for (int32_t i = 0; i < r->nfiles; i++) {
        if (d == SR_REG_POOL && r->f[i].pool) return 1;
        for (int32_t k = 0; k < r->f[i].ndiv; k++) if (r->f[i].div[k] == d) return 1;
    }
    return 0;
}

int32_t sr_reg_build(sr_registry *r, int32_t nfiles, const sr_reg_file *f, int32_t n, const uint8_t *div)
{
    int32_t pools = 0;
    if (!r || !f || nfiles < 1 || nfiles > SR_REG_FILES || n < 0 || n > SR_REG_CLUBS || (n && !div))
        return -1;
    r->nfiles = nfiles; r->nclub = n;
    for (int32_t i = 0; i < nfiles; i++) {
        int32_t rows = f[i].pool;
        r->f[i].file = f[i].file; r->f[i].ndiv = f[i].ndiv; r->f[i].pool = f[i].pool;   /* (no struct copy: no memcpy) */
        for (int32_t k = 0; k < SR_DIVS; k++) r->f[i].div[k] = f[i].div[k], r->f[i].size[k] = f[i].size[k];
        if (f[i].ndiv > SR_DIVS || f[i].file == 0xFF) return -1;   /* (file 255: row 255's word = SR_REG_NONE) */
        for (int32_t j = 0; j < i; j++) if (f[j].file == f[i].file) return -1;
        for (int32_t k = 0; k < f[i].ndiv; k++) {
            if (f[i].div[k] >= SR_REG_POOL) return -1;
            rows += f[i].size[k];
            for (int32_t j = 0; j <= i; j++)
                for (int32_t q = 0; q < (j < i ? f[j].ndiv : k); q++) if (f[j].div[q] == f[i].div[k]) return -1;
        }
        if (rows > 256) return -1;
        pools += f[i].pool != 0;
        r->rows[i] = (u16)rows;
    }
    if (pools > 1) return -1;
    for (int32_t i = 0; i < n; i++) {
        if (!known_div(r, div[i])) return -1;
        r->word[i] = SR_REG_NONE;
    }
    for (int32_t i = 0; i < nfiles; i++) {
        int32_t o = 0;
        for (int32_t k = 0; k < f[i].ndiv + (f[i].pool != 0); k++) {
            const u8 d = k < f[i].ndiv ? f[i].div[k] : SR_REG_POOL;
            const int32_t size = k < f[i].ndiv ? f[i].size[k] : f[i].pool, o0 = o;
            for (int32_t c = 0; c < n; c++)
                if (div[c] == d) {
                    if (o - o0 >= size) return -1;
                    r->at[i][o] = (u16)c; r->rdiv[i][o] = d; r->word[c] = (u16)(f[i].file | o << 8); o++;
                }
            if (o - o0 != size) return -1;
        }
        for (; o < 256; o++) r->at[i][o] = SR_REG_NONE, r->rdiv[i][o] = SR_REG_OUT;
    }
    return 0;
}

uint16_t sr_reg_word(const sr_registry *r, int32_t ident)
{
    return r && ident >= 0 && ident < r->nclub ? r->word[ident] : SR_REG_NONE;
}

int32_t sr_reg_ident(const sr_registry *r, uint16_t word)
{
    const int32_t i = r ? fidx(r, word) : -1;
    return i < 0 || r->at[i][word >> 8] == SR_REG_NONE ? -1 : r->at[i][word >> 8];
}

int32_t sr_reg_div(const sr_registry *r, int32_t ident)
{
    const u16 w = sr_reg_word(r, ident);
    const int32_t i = w == SR_REG_NONE ? -1 : fidx(r, w);
    return i < 0 ? SR_REG_OUT : r->rdiv[i][w >> 8];
}

static void put(sr_registry *r, int32_t i, int32_t o, u16 c)
{
    r->at[i][o] = c;
    if (c != SR_REG_NONE) r->word[c] = (u16)(r->f[i].file | o << 8);
}

uint32_t sr_reg_size(void) { return sizeof(sr_registry); }
uint32_t sr_reg_work_size(void) { return sizeof(sr_reg_work); }

/* the division of file i's row o as built (its range), SR_REG_OUT past the rows */
static u8 range_div(const sr_registry *r, int32_t i, int32_t o)
{
    for (int32_t k = 0; k < r->f[i].ndiv; k++) {
        if (o < r->f[i].size[k]) return r->f[i].div[k];
        o -= r->f[i].size[k];
    }
    return o < r->f[i].pool ? SR_REG_POOL : SR_REG_OUT;
}

/* the file index division d lives in, -1 off the files */
static int32_t file_of(const sr_registry *r, u8 d)
{
    for (int32_t i = 0; i < r->nfiles; i++) {
        if (d == SR_REG_POOL && r->f[i].pool) return i;
        for (int32_t k = 0; k < r->f[i].ndiv; k++) if (r->f[i].div[k] == d) return i;
    }
    return -1;
}

/* one range of rows (contiguous: a division's; default: a whole file's) -- its leavers' rows to its comers, both by
 * rank; the number of rows changed, -1 not equal */
static int32_t fill(const sr_registry *r, const uint8_t *nd, int32_t contiguous, int32_t i, int32_t o0, int32_t o1,
                    u8 d, sr_reg_work *w)
{
    int32_t nf = 0, ne = 0;
    for (int32_t o = o0; o < o1; o++) {
        const u16 c = r->at[i][o];
        w->want[i][o] = c;
        if (contiguous ? nd[c] == d : file_of(r, nd[c]) == i) continue;
        int32_t j = nf++;
        for (; j > 0 && w->rank[r->at[i][w->fr[j - 1]]] > w->rank[c]; j--) w->fr[j] = w->fr[j - 1];
        w->fr[j] = (u16)o;
    }
    for (int32_t c = 0; c < r->nclub; c++) {
        const u16 cw = r->word[c];
        const int32_t ci = cw == SR_REG_NONE ? -1 : fidx(r, cw);
        if (contiguous ? nd[c] != d || (ci == i && (cw >> 8) >= o0 && (cw >> 8) < o1) : file_of(r, nd[c]) != i || ci == i)
            continue;
        if (ne == 256) return -1;
        int32_t j = ne++;
        for (; j > 0 && w->rank[w->en[j - 1]] > w->rank[c]; j--) w->en[j] = w->en[j - 1];
        w->en[j] = (u16)c;
    }
    if (nf != ne) return -1;
    if (!contiguous)                    /* (first a club leaving to file j against one coming from j, by rank: two files
                                           trade as single swaps; then the rest -- the off-file pool -- by rank) */
        for (int32_t j = 0; j < r->nfiles; j++) {
            int32_t a = 0, b = 0;
            if (j == i) continue;
            for (;;) {
                while (a < nf && (w->fr[a] == SR_REG_NONE || file_of(r, nd[r->at[i][w->fr[a]]]) != j)) a++;
                while (b < ne && (w->en[b] == SR_REG_NONE || r->word[w->en[b]] == SR_REG_NONE ||
                                  fidx(r, r->word[w->en[b]]) != j)) b++;
                if (a == nf || b == ne) break;
                w->want[i][w->fr[a]] = w->en[b];
                w->fr[a++] = SR_REG_NONE; w->en[b++] = SR_REG_NONE;
            }
        }
    for (int32_t a = 0, b = 0;; a++, b++) {
        while (a < nf && w->fr[a] == SR_REG_NONE) a++;
        while (b < ne && w->en[b] == SR_REG_NONE) b++;
        if (a == nf || b == ne) break;
        w->want[i][w->fr[a]] = w->en[b];
    }
    return nf;
}

int32_t sr_reg_season(sr_registry *r, const uint8_t *nd, const uint16_t *order, int32_t norder, int32_t contiguous,
                      sr_reg_work *w, sr_reg_swap *out, int32_t max)
{
    int32_t changed = 0, ns = 0;
    if (!r || !nd || !w || (norder && !order)) return -1;
    for (int32_t c = 0; c < r->nclub; c++) {
        w->rank[c] = (u16)(norder + c);
        if (!known_div(r, nd[c])) return -1;
    }
    for (int32_t k = norder - 1; k >= 0; k--) if (order[k] < r->nclub) w->rank[order[k]] = (u16)k;
    for (int32_t i = 0; i < r->nfiles; i++) {
        if (!contiguous) {
            const int32_t n = fill(r, nd, 0, i, 0, r->rows[i], 0, w);
            if (n < 0) return -1;
            changed += n;
            continue;
        }
        for (int32_t o = 0; o < r->rows[i];) {
            const u8 d = range_div(r, i, o);
            int32_t o1 = o;
            while (o1 < r->rows[i] && range_div(r, i, o1) == d) o1++;
            const int32_t n = fill(r, nd, 1, i, o, o1, d, w);
            if (n < 0) return -1;
            changed += n;
            o = o1;
        }
    }
    if (changed > max) return -2;
    /* the swaps: every row that wants a club on the files takes it from its row, then the rows left take
     * their clubs from the off-file pool (their clubs, by then, the ones that leave) */
    for (int32_t pass = 0; pass < 2; pass++)
        for (int32_t i = 0; i < r->nfiles; i++)
            for (int32_t o = 0; o < r->rows[i]; o++) {
                const u16 x = w->want[i][o], y = r->at[i][o], wd = (u16)(r->f[i].file | o << 8);
                if (x == y) continue;
                if (pass == 0 && r->word[x] != SR_REG_NONE) {
                    const u16 t = r->word[x];
                    const int32_t ti = fidx(r, t);
                    put(r, ti, t >> 8, y); put(r, i, o, x);
                    out[ns].a = wd; out[ns].b = t; out[ns].on = SR_REG_NONE; ns++;
                } else if (pass == 1) {
                    r->word[y] = SR_REG_NONE; put(r, i, o, x);
                    out[ns].a = wd; out[ns].b = SR_REG_NONE; out[ns].on = x; ns++;
                }
            }
    for (int32_t i = 0; i < r->nfiles; i++)         /* each row's division: its club's */
        for (int32_t o = 0; o < r->rows[i]; o++) r->rdiv[i][o] = nd[r->at[i][o]];
    return ns;
}

int32_t sr_reg_check(const sr_registry *r)
{
    int32_t placed = 0;
    if (!r) return -1;
    for (int32_t i = 0; i < r->nfiles; i++)
        for (int32_t o = 0; o < r->rows[i]; o++) {
            const u16 c = r->at[i][o];
            if (c >= r->nclub || r->word[c] != (u16)(r->f[i].file | o << 8)) return -1;
            placed++;
        }
    for (int32_t c = 0; c < r->nclub; c++) placed -= r->word[c] != SR_REG_NONE;
    return placed ? -1 : 0;
}
