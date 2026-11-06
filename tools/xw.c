/* XW: contests across career worlds (notes/engine/xw-design.md) - the groundwork, pure functions with no game state:
   the visitor map (a visitor world's team FILE f -> a free number r in 220..253, the same for every club of that
   file) and its save, the DIY tail block 'WM' v2. Not linked into the exe yet (the hooks come after engine P): Tier B
   compiles this file for the host (hosttest test_xw.py). Freestanding, cdecl, integers only, as swe.c. */

typedef unsigned char u8;
typedef unsigned int u32;

#define XW_FIRST 220                    /* the numbers free in every world's namespace (registry: world 5 ends at 219) */
#define XW_MAX 34                       /* 220..253 */
#define XW_VFILES 220                   /* a visitor file number: 1..219 */

struct xw_map {                         /* host world (the contest's first), visitor world, k mapped files */
    u8 host, vis, k, pad;
    u8 r[XW_MAX], f[XW_MAX], fl[XW_MAX];
};

void xw_clear(struct xw_map *m, u32 host, u32 vis)
{
    volatile u8 *z = (u8 *)m;           /* (volatile: no memset call - there is no library) */
    for (u32 i = 0; i < sizeof *m; i++)
        z[i] = 0;
    m->host = (u8)host;
    m->vis = (u8)vis;
}

u32 xw_alloc(struct xw_map *m, u32 f)   /* f's number (one already given, or the first free); 0: no room / bad f */
{
    if (!f || f >= XW_VFILES)
        return 0;
    for (u32 i = 0; i < m->k; i++)
        if (m->f[i] == f)
            return m->r[i];
    if (m->k >= XW_MAX)
        return 0;
    for (u32 r = XW_FIRST; r < XW_FIRST + XW_MAX; r++) {
        u32 i = 0;
        while (i < m->k && m->r[i] != r)
            i++;
        if (i == m->k) {
            m->r[m->k] = (u8)r;
            m->f[m->k] = (u8)f;
            m->fl[m->k] = 0;
            m->k++;
            return r;
        }
    }
    return 0;
}

u32 xw_file(const struct xw_map *m, u32 r)     /* r's visitor file, 0 when r is not mapped */
{
    for (u32 i = 0; i < m->k; i++)
        if (m->r[i] == r)
            return m->f[i];
    return 0;
}

u32 xw_wm_put(const struct xw_map *m, u8 *out) /* the tail: 'W' 'M', len 2 + 3k, host, visitor, (r, f, flags) x k */
{
    u32 n = 2 + 3 * m->k;
    out[0] = 'W';
    out[1] = 'M';
    out[2] = (u8)n;
    out[3] = m->host;
    out[4] = m->vis;
    for (u32 i = 0; i < m->k; i++) {
        out[5 + 3 * i] = m->r[i];
        out[6 + 3 * i] = m->f[i];
        out[7 + 3 * i] = m->fl[i];
    }
    return 3 + n;
}

/* A file's tail block, n bytes at p (the file's end - the game's part known): 1 = mixing A ('WM' 1, world), the map
   cleared with host = that world; 2 = XW, the map read; 0 = no block / not a valid one (the contest reads as world 0).
   A v2 block counts only whole and sane: its length = n, k <= 34, every r in 220..253 and unique, every f 1..219. */
u32 xw_wm_get(const u8 *p, u32 n, struct xw_map *m)
{
    if (n < 4 || p[0] != 'W' || p[1] != 'M' || p[2] + 3u != n)
        return 0;
    if (p[2] == 1) {
        xw_clear(m, p[3], 0);
        return 1;
    }
    if (p[2] < 2 || (p[2] - 2) % 3)
        return 0;
    u32 k = (p[2] - 2) / 3;
    if (k > XW_MAX)
        return 0;
    for (u32 i = 0; i < k; i++) {
        u32 r = p[5 + 3 * i], f = p[6 + 3 * i];
        if (r < XW_FIRST || r >= XW_FIRST + XW_MAX || !f || f >= XW_VFILES)
            return 0;
        for (u32 j = 0; j < i; j++)
            if (p[5 + 3 * j] == r || p[6 + 3 * j] == f)
                return 0;
    }
    xw_clear(m, p[3], p[4]);
    for (u32 i = 0; i < k; i++) {
        m->r[i] = p[5 + 3 * i];
        m->f[i] = p[6 + 3 * i];
        m->fl[i] = p[7 + 3 * i];
    }
    m->k = (u8)k;
    return 2;
}

/* The rows 220..253 a contest's namespace gets (careerworld w_ns_set fills them from these on each swap): for every
   mapped file i, the visitor world's countriesTable entry for its file f (vlab[f], the country's name as that world
   shows it) and its teamsCountryNumbers word (vbase[f], the first global number of f's clubs; vcnt[f] clubs). The
   global numbers must not collide with the host world's files the contest uses (hf[0..nh), hbase / hcnt per file): 0
   when one does (the pick is refused), else 1 with lab[i] / base[i] filled. */
u32 xw_rows(const struct xw_map *m, const u32 *vlab, const unsigned short *vbase, const u8 *vcnt,
            const u8 *hf, u32 nh, const unsigned short *hbase, const u8 *hcnt, u32 *lab, unsigned short *base)
{
    for (u32 i = 0; i < m->k; i++) {
        u32 f = m->f[i], lo = vbase[f], hi = lo + vcnt[f];
        for (u32 j = 0; j < nh; j++) {
            u32 h = hf[j], hlo = hbase[h], hhi = hlo + hcnt[h];
            if (lo < hhi && hlo < hi)
                return 0;
        }
        lab[i] = vlab[f];
        base[i] = (unsigned short)lo;
    }
    return 1;
}
