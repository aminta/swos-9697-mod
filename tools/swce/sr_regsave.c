/*
 * sr_regsave.c -- the club registry in a save (N7, the save side of 42-s7reg; Mod's internal/handoff/n7-s7-clubmap.md):
 * the identity map only, 10 bits a row, and the word map that rewrites an old save's team words.
 *
 *   +0        u8 version (SR_REGSAVE_VERSION), u8 nfiles
 *   +2        u16 season (the one the map was last written in)
 *   +4        u32 layout (sr_reg_layout: the files' shape and nclub -- another pack reads as absent)
 *   +8        u16 flags (the caller's: SR_REGSAVE_IMPORTED, SR_REGSAVE_PENDING; sr_reg_save writes 0, the caller sets
 *             them after it -- swe_st_save's order)
 *   +10       u16 rows (the files' rows, all of them)
 *   +12       the identity map: every row's ident, file order then ordinal order, 10 bits each, low bit first
 *
 * word[] is the map's inverse and rdiv[] is not saved: sr_reg_load leaves each row's division as built (the
 * division's range); the exe's default (contiguous 0) sets it from its records' division byte afterwards.
 * Idents are the pack's order, append-only (CONVENTIONS): a pack that appends clubs or reshapes a file has
 * another layout, and its saves import again (the caller's old-save path) instead of reading the wrong clubs.
 *
 * Copyright (c) 2026 Davide Lorigliola. MIT licence (LICENSE).
 */
#include "swosrules.h"

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;

enum { HDR = SR_REGSAVE_HDR };
typedef char idents_fit_10_bits[SR_REG_CLUBS <= 1024 ? 1 : -1];   /* (C99: no _Static_assert) */

/* nclub within the arrays and every file's rows = its divisions' sizes + its pool (sr_reg_load fills by those) */
static int shape_ok(const sr_registry *r)
{
    if (r->nclub < 0 || r->nclub > SR_REG_CLUBS || r->nfiles < 0 || r->nfiles > SR_REG_FILES) return 0;
    for (int32_t i = 0; i < r->nfiles; i++) {
        int32_t n = r->f[i].pool;
        if (r->f[i].ndiv < 0 || r->f[i].ndiv > SR_DIVS) return 0;
        for (int32_t d = 0; d < r->f[i].ndiv; d++) n += r->f[i].size[d];
        if (n != r->rows[i] || n > 256) return 0;
    }
    return 1;
}

static u32 fnv(u32 h, u32 v, int bytes)
{
    for (int i = 0; i < bytes; i++) h = (h ^ (u8)(v >> 8 * i)) * 16777619u;
    return h;
}

uint32_t sr_reg_layout(int32_t nfiles, const sr_reg_file *f, int32_t nclub)
{
    u32 h = fnv(2166136261u, (u32)nfiles, 1);
    for (int32_t i = 0; f && i < nfiles && i < SR_REG_FILES; i++) {
        h = fnv(h, f[i].file, 1);
        h = fnv(h, f[i].ndiv, 1);
        for (int32_t k = 0; k < f[i].ndiv && k < SR_DIVS; k++) h = fnv(fnv(h, f[i].div[k], 1), f[i].size[k], 1);
        h = fnv(h, f[i].pool, 2);
    }
    return fnv(h, (u32)nclub, 2);
}

static int32_t total_rows(const sr_registry *r)
{
    int32_t n = 0;
    for (int32_t i = 0; i < r->nfiles; i++) n += r->rows[i];
    return n;
}

int32_t sr_reg_save_size(const sr_registry *r)
{
    return r ? HDR + (total_rows(r) * 10 + 7) / 8 : -1;
}

int32_t sr_reg_save(const sr_registry *r, uint32_t layout, uint16_t season, uint8_t *out, int32_t room)
{
    const int32_t size = sr_reg_save_size(r);
    if (size < 0 || !out || room < size || !shape_ok(r) || sr_reg_check(r)) return -1;
    const int32_t rows = total_rows(r);
    out[0] = SR_REGSAVE_VERSION; out[1] = (u8)r->nfiles;
    out[2] = (u8)season; out[3] = (u8)(season >> 8);
    for (int i = 0; i < 4; i++) out[4 + i] = (u8)(layout >> 8 * i);
    out[8] = out[9] = 0;
    out[10] = (u8)rows; out[11] = (u8)(rows >> 8);
    for (int32_t i = HDR; i < size; i++) out[i] = 0;
    int32_t bit = HDR * 8;
    for (int32_t i = 0; i < r->nfiles; i++)
        for (int32_t o = 0; o < r->rows[i]; o++, bit += 10) {
            const u32 v = r->at[i][o];
            for (int b = 0; b < 10; b++) if (v >> b & 1) out[(bit + b) >> 3] |= (u8)(1 << ((bit + b) & 7));
        }
    return size;
}

static u16 row_at(const uint8_t *in, int32_t k)
{
    const int32_t bit = HDR * 8 + 10 * k;
    u16 v = 0;
    for (int b = 0; b < 10; b++) v |= (u16)((in[(bit + b) >> 3] >> ((bit + b) & 7) & 1) << b);
    return v;
}

int32_t sr_reg_load(sr_registry *r, uint32_t layout, const uint8_t *in, int32_t len)
{
    u8 seen[SR_REG_CLUBS / 8];
    if (!r || !in || len <= 0) return 0;                 /* absent */
    if (len < HDR || !shape_ok(r)) return -1;
    const u32 lay = in[4] | (u32)in[5] << 8 | (u32)in[6] << 16 | (u32)in[7] << 24;
    if (in[0] != SR_REGSAVE_VERSION || in[1] != r->nfiles || lay != layout) return 0;
    const int32_t rows = total_rows(r);
    if ((in[10] | in[11] << 8) != rows || len < sr_reg_save_size(r)) return -1;
    for (int32_t i = 0; i < SR_REG_CLUBS / 8; i++) seen[i] = 0;
    for (int32_t k = 0; k < rows; k++) {               /* checked whole before the registry changes */
        const u16 c = row_at(in, k);
        if (c >= r->nclub || seen[c >> 3] >> (c & 7) & 1) return -1;
        seen[c >> 3] |= (u8)(1 << (c & 7));
    }
    for (int32_t c = 0; c < r->nclub; c++) r->word[c] = SR_REG_NONE;
    for (int32_t i = 0, k = 0; i < r->nfiles; i++) {
        int32_t o = 0;
        for (int32_t d = 0; d < r->f[i].ndiv + 1; d++) {   /* each row's division as built: its range */
            const int32_t size = d < r->f[i].ndiv ? r->f[i].size[d] : r->f[i].pool;
            const u8 dv = d < r->f[i].ndiv ? r->f[i].div[d] : SR_REG_POOL;
            for (int32_t j = 0; j < size; j++, o++, k++) {
                const u16 c = row_at(in, k);
                r->at[i][o] = c; r->rdiv[i][o] = dv; r->word[c] = (u16)(r->f[i].file | o << 8);
            }
        }
    }
    return sr_reg_check(r) ? -1 : 1;                    /* (-1 here only: r filled -- the caller rebuilds it) */
}

/* pairs sorted by from (insertion: a few hundred at most); -1 a word twice, -2 room short */
static int32_t add(sr_wpair *out, int32_t n, int32_t max, u16 from, u16 to)
{
    int32_t j = n;
    for (int32_t i = 0; i < n; i++) if (out[i].from == from) return -1;
    if (n >= max) return -2;
    for (; j > 0 && out[j - 1].from > from; j--) out[j] = out[j - 1];
    out[j].from = from; out[j].to = to;
    return n + 1;
}

/* the tracked club (one with an old word) at word w now: its pair's index; -1 none (an `on` club, no old word) */
static int32_t at_word(sr_wpair *out, int32_t *m, int32_t max, u16 w)
{
    for (int32_t i = 0; i < *m; i++) if (out[i].to == w) return i;
    for (int32_t i = 0; i < *m; i++) if (out[i].from == w) return -1;   /* its first club left, an `on` club came */
    if (*m >= max) return -2;
    out[*m].from = w; out[*m].to = w;                   /* still its first club */
    return (*m)++;
}

int32_t sr_wmap_build(const sr_reg_swap *sw, int32_t n, sr_wpair *out, int32_t max)
{
    int32_t m = 0;
    if ((n && !sw) || n < 0 || !out || max < 0) return -1;
    /* out[] holds (old word, its club's word now) in arrival order, then gets sorted */
    for (int32_t s = 0; s < n; s++) {
        const u16 a = sw[s].a, b = sw[s].b;
        if (a == SR_REG_NONE || a == b) return -1;
        const int32_t ia = at_word(out, &m, max, a);
        if (ia == -2) return -2;
        if (b == SR_REG_NONE) {                         /* a's club off the files; `on` comes with no old word */
            if (ia >= 0) out[ia].to = SR_REG_NONE;
            continue;
        }
        const int32_t ib = at_word(out, &m, max, b);
        if (ib == -2) return -2;
        if (ia >= 0) out[ia].to = b;
        if (ib >= 0) out[ib].to = a;
    }
    int32_t k = 0;                                      /* the clubs back where they were: no pair */
    for (int32_t i = 0; i < m; i++) if (out[i].from != out[i].to) out[k++] = out[i];
    for (int32_t i = 1; i < k; i++) {
        const sr_wpair p = out[i];
        int32_t j = i;
        for (; j > 0 && out[j - 1].from > p.from; j--) out[j] = out[j - 1];
        out[j] = p;
    }
    return k;
}

int32_t sr_wmap_import(const sr_registry *r, const uint16_t *old_word, int32_t n, sr_wpair *out, int32_t max)
{
    int32_t m = 0;
    if (!r || !old_word || !out || n < 0 || n > r->nclub) return -1;
    for (int32_t c = 0; c < n; c++)                     /* the clubs whose word changed (to SR_REG_NONE: now off) */
        if (old_word[c] != SR_REG_NONE && old_word[c] != r->word[c] && (m = add(out, m, max, old_word[c], r->word[c])) < 0)
            return m;
    for (int32_t c = 0; c < n; c++)                     /* a kept word that a moved club also had: two clubs, one word */
        if (old_word[c] != SR_REG_NONE && old_word[c] == r->word[c] && sr_wmap_get(out, m, old_word[c]) != old_word[c])
            return -1;
    return m;
}

uint16_t sr_wmap_get(const sr_wpair *m, int32_t n, uint16_t w)
{
    int32_t lo = 0, hi = n - 1;
    while (m && lo <= hi) {
        const int32_t mid = (lo + hi) / 2;
        if (m[mid].from == w) return m[mid].to;
        if (m[mid].from < w) lo = mid + 1; else hi = mid - 1;
    }
    return w;
}
