/* N7 piece 4 (n7-s7-clubmap.md §4c, n7-p4.md §4 step 3): the word-site walker's core -- one WSITES line over the
   bytes its item resolves to, through the old-save import's word map (sr_wmap_get). Host-only today (test_sreg
   test_sreg_walk, a native build); sreg.c #includes it once the import has its obj4 page (swreg.SREG2_AT) and the
   S7 glue names where the import is called (MC).

   Forms (clubmap §4):
   - WS_W: a u16 team word (file | ordinal << 8); 0 and FFFFh are "none", never rewritten.
   - WS_G: a u16 global number (someLeaguesTable index): the run whose [base, base + rows) holds it gives the
     word (file | (ord0 + g - base) << 8), the map the new word, the run holding the new word's ordinal the new
     global (a split file - G144 - has two runs, each its ord0). A global in no listed
     file (another country) is kept.
   - WS_D: a DIY contest buffer - its type's live team list(s) only (sreg_walk.h); -1 and nothing written on a refusal.
   - WS_O8 / WS_K: not here (O8 moves array rows between the two files' ordinals; K is its owner's re-key after the
     walk): -2, so a table with such a line fails loudly until its piece lands.
   Returns the words / globals changed, -1 when a line runs past the item's bytes (nothing written then: checked
   whole first), -2 for a form not handled. */
#ifndef SREG_WALK_C
#define SREG_WALK_C

#include "sreg_walk.h"                        /* (the row layout, forms, items: the contract) */

static int32_t gfile_of(const sreg_gfile *g, int32_t ng, uint32_t glob)
{
    for (int32_t i = 0; i < ng; i++) {
        uint32_t rows = g[i].rows ? g[i].rows : 256;
        if (glob >= g[i].base && glob < g[i].base + rows) return i;
    }
    return -1;
}

static int32_t gindex(const sreg_gfile *g, int32_t ng, uint32_t file, uint32_t ord)   /* the run holding (file, ord) */
{
    for (int32_t i = 0; i < ng; i++) {
        uint32_t rows = g[i].rows ? g[i].rows : 256;
        if (g[i].file == file && ord >= g[i].ord0 && ord < g[i].ord0 + rows) return i;
    }
    return -1;
}

static int32_t walk_rows(const sreg_wsite *s, uint8_t *b, int32_t len, const sr_wpair *m, int32_t n)
{                                               /* WS_R: the entries of the rows whose club changed -> fill */
    if (!s->count) return 0;
    uint32_t fill = s->stride & 0xFF, lit = s->stride >> 8;     /* (stride = fill | file << 8; file 0: the item's b[aux]) */
    if (s->count > 256 || s->off + (int32_t)s->count > len || (!lit && s->aux >= len)) return -1;
    int32_t changed = 0;
    uint32_t file = lit ? lit : b[s->aux];
    for (uint32_t k = 0; k < s->count; k++) {
        uint16_t w = (uint16_t)(file | k << 8);
        for (int32_t i = 0; i < n; i++)                     /* (its club left or a club arrived: a pair names the row) */
            if ((m[i].from == w || m[i].to == w) && m[i].from != m[i].to) {
                if (b[s->off + k] != fill) { b[s->off + k] = (uint8_t)fill; changed++; }
                break;
            }
    }
    return changed;
}

/* WS_D: a DIY contest's live team list(s) (sreg_walk.h). DL_*: the list offset / size per type (league, cup, type 2) */
enum { DL_N = 49, DL_MAX = 64, DL_STAGE = 0x41F };
static const uint16_t DL_LIST[3] = { 301, 589, 153 }, DL_SIZE[3] = { 0x733, 0x443, 0xB52 };

static int32_t walk_diy(const sreg_wsite *s, uint8_t *b, int32_t len, const sr_wpair *m, int32_t n)
{                                               /* the contest's live list(s), each walked as a WS_W run (s7swap.c's band is tight) */
    int32_t room = s->stride, at[2], cnt[2], nl = 0, changed = 0;
    uint8_t *c = b + s->off;
    if (s->count != 1 || room < DL_SIZE[1] || s->off + room > len) return -1;   /* (0x443: the smallest contest) */
    for (int32_t l = 0; l < 2; l++) {           /* l 1: a type 2's current stage, type 0 / 1 only, inside the 0xB52 */
        uint32_t t = (uint32_t)(c[0] | c[1] << 8), k = (uint32_t)(c[DL_N] | c[DL_N + 1] << 8);
        if (t > (uint32_t)(2 - l) || DL_SIZE[t] > room || k > DL_MAX) return -1;
        at[l] = (int32_t)(c - b) + DL_LIST[t]; cnt[l] = (int32_t)k; nl = l + 1;
        if (t != 2) break;
        c += DL_STAGE; room = DL_SIZE[2] - DL_STAGE;
    }
    for (int32_t l = 0; l < nl; l++) {          /* (all checked above: nothing written on a refusal) */
        sreg_wsite w = { s->item, 0, 2, (uint16_t)cnt[l], WS_W, 0 };
        changed += sreg_walk_site(&w, b + at[l], len - at[l], m, n, 0, 0);
    }
    return changed;
}

int32_t sreg_walk_site(const sreg_wsite *s, uint8_t *b, int32_t len, const sr_wpair *m, int32_t n,
                       const sreg_gfile *g, int32_t ng)
{
    if (s->form == WS_R) return walk_rows(s, b, len, m, n);
    if (s->form == WS_D) return walk_diy(s, b, len, m, n);
    if (s->form != WS_W && s->form != WS_G) return -2;
    if (!s->count) return 0;
    if (s->off + (int32_t)(s->count - 1) * s->stride + 2 > len || (s->count > 1 && s->stride < 2)) return -1;
    int32_t changed = 0;
    for (uint32_t k = 0; k < s->count; k++) {
        uint8_t *p = b + s->off + k * s->stride;
        uint16_t v = (uint16_t)(p[0] | p[1] << 8), w = v;
        if (s->form == WS_W) {
            if (v && v != 0xFFFF) w = sr_wmap_get(m, n, v);
        } else {
            int32_t i = gfile_of(g, ng, v);
            if (i >= 0) {
                uint16_t nw = sr_wmap_get(m, n, (uint16_t)(g[i].file | (g[i].ord0 + v - g[i].base) << 8));
                int32_t j = gindex(g, ng, nw & 0xFF, nw >> 8);
                if (j >= 0) w = (uint16_t)(g[j].base + (nw >> 8) - g[j].ord0);
            }
        }
        if (w != v) {
            p[0] = (uint8_t)w;
            p[1] = (uint8_t)(w >> 8);
            changed++;
        }
    }
    return changed;
}

#endif
