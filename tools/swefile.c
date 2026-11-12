/* The engine's file layer (swefile.h), its one copy in the exe: obj4+swreg.SWEFILE_AT..SWEFILE_END (page 18, MC
   12/11), linked by swefile.py. No .bss (cobj.link puts a unit's .bss at obj4's tail: swe.c's).

   SWEFILE_TEST=1 builds add swef_selftest (past SWEFILE_END on page 18: test bytes, not the release range), called once
   by swe.c swe_sel_pre (SWEF_HOOK) at the first FRIENDLY picker, its buffers swe.c's SWEF_BIG / SWEF_RB. SWEF_RES
   ('SWEFRES2') is what the harness reads (swostest.py swefile_layer); the files it leaves in the game's folder are
   checked on the host byte for byte (patterns: swef_fill's LCG, the same as swostest.py swef_pat).
   Freestanding, cdecl, as every C file of the mod (cobj.py). */
#define SWEFILE_IMPL
#include "swefile.h"

#ifdef SWEFILE_TEST
typedef unsigned char u8;
typedef unsigned int u32;

#define K64 65536
#define BIGN (22 * K64)                         /* 1.375 MB */
extern u8 SWEF_BIG[], SWEF_RB[];                /* (swe.c .bss: BIGN and K64 bytes) */

struct { char magic[8]; u32 done; int rc[32]; u32 bad, t[6], bytes; } SWEF_RES = {"SWEFRES2"};

static u32 swef_lcg(u32 *x) { return (*x = *x * 1103515245u + 12345u) >> 16 & 0xFF; }

static void swef_fill(u8 *b, u32 seed, u32 n)
{
    for (u32 i = 0; i < n; i++)
        b[i] = (u8)swef_lcg(&seed);
}

static u32 swef_ticks(void) { return *(volatile u32 *)0x46C; }   /* (BIOS ticks, 18.2 Hz: DOS/4GW maps the 1st MB) */

static int swef_check(u8 *b, u32 seed, u32 n)   /* b[0..n) = seed's bytes: 0, else -1 */
{
    for (u32 i = 0; i < n; i++)
        if (b[i] != swef_lcg(&seed))
            return -1;
    return 0;
}

static int swef_vchunks(const char *name, u32 seed, u32 n, u32 chunk)   /* the file = seed's n bytes, read in chunks */
{
    int h = swe_fopen_r(name), bad = 0;
    if (h < 0)
        return h;
    for (u32 at = 0; at <= n && !bad; at += chunk) {
        u32 want = n - at < chunk ? n - at : chunk;
        int r = swe_fread(h, SWEF_RB, chunk);
        bad = r != (int)want || swef_check(SWEF_RB, seed, r);
        for (u32 i = 0; i < want; i++)          /* (the LCG advanced by this chunk) */
            swef_lcg(&seed);
        if (r < (int)chunk)
            break;
    }
    swe_fclose(h);
    return bad ? -1 : 0;
}

static int swef_small(const char *name, u32 seed, u32 n)  /* a file of seed's n bytes, written as it is (no MK$) */
{
    swef_fill(SWEF_RB, seed, n);
    int h = swe_fopen_w(name);
    if (h < 0)
        return h;
    int r = swe_fwrite(h, SWEF_RB, n), c = swe_fclose(h);
    return r < 0 ? r : c < 0 ? c : r;
}

void swef_selftest(void)
{
    int *rc = SWEF_RES.rc, h, r;
    u32 *t = SWEF_RES.t;
    rc[0] = swe_fopen_r("NOFILE.MKT");                          /* -2 */
    swef_fill(SWEF_BIG, 1, K64);
    rc[1] = swe_save_atomic("TEST.MKT", SWEF_BIG, K64);        /* new */
    rc[2] = swef_vchunks("TEST.MKT", 1, K64, 4096);
    rc[3] = swe_fopen_r("TEST.MK$");                            /* -2: no temporary left */
    swef_fill(SWEF_BIG, 2, K64);
    rc[4] = swe_save_atomic("TEST.MKT", SWEF_BIG, K64);        /* over the old one */
    rc[5] = swef_vchunks("TEST.MKT", 2, K64, 4096);
    rc[6] = swe_recover("TEST.MKT");                            /* 0: nothing to do */
    swef_fill(SWEF_BIG, 1, K64);                                /* cut point 1: CUT.MKT + a cut CUT.MK$ */
    rc[7] = swe_save_atomic("CUT.MKT", SWEF_BIG, K64);
    rc[8] = swef_small("CUT.MK$", 3, 1000);                     /* 1000 */
    rc[9] = swe_recover("CUT.MKT");                             /* 0: MK$ removed, CUT.MKT the old one */
    rc[10] = swe_fopen_r("CUT.MK$");                            /* -2 */
    rc[11] = swef_small("CUT2.MK$", 5, 100);                    /* cut point 1, a first save: CUT2.MK$ alone */
    rc[12] = swe_recover("CUT2.MKT");                           /* 0 */
    rc[13] = swe_fopen_r("CUT2.MKT");                           /* -2: a cut MK$ is never taken */
    rc[14] = swef_small("BOTH.MKT", 1, 512);                    /* cut point 2: NAME old + MK! new */
    rc[15] = swef_small("BOTH.MK!", 5, 512);
    rc[16] = swe_recover("BOTH.MKT");                           /* 1: MK! wins */
    rc[17] = swef_small("REC.MK!", 5, 512);                     /* cut point 3: no NAME, MK! */
    rc[18] = swe_recover("REC.MKT");                            /* 1 */
    rc[19] = swef_small("STALE.MK$", 4, 3000);                  /* a stale MK$ and MK!, then a save over them */
    rc[20] = swef_small("STALE.MK!", 4, 2000);
    swef_fill(SWEF_BIG, 2, K64);
    rc[21] = swe_save_atomic("STALE.MKT", SWEF_BIG, K64);
    rc[22] = swe_save_atomic("NODIR\\X.MKT", SWEF_BIG, 16);    /* -3, nothing written */
    swef_fill(SWEF_BIG, 6, BIGN);                               /* 1.375 MB in ONE write call (DOS/4GW splits it) */
    t[0] = swef_ticks();
    rc[23] = swe_save_atomic("BIG1.MKT", SWEF_BIG, BIGN);      /*  new */
    t[1] = swef_ticks();
    rc[24] = swe_save_atomic("BIG1.MKT", SWEF_BIG, BIGN);      /*  over itself */
    t[2] = swef_ticks();
    for (u32 i = 0; i < BIGN; i++)                              /* ... read back in ONE call */
        SWEF_BIG[i] = 0;
    h = swe_fopen_r("BIG1.MKT");
    rc[25] = h < 0 ? h : swe_fread(h, SWEF_BIG, BIGN + 16);     /* BIGN (the end of the file) */
    if (h >= 0)
        swe_fclose(h);
    t[3] = swef_ticks();
    rc[26] = swef_check(SWEF_BIG, 6, BIGN);
    swef_fill(SWEF_BIG, 8, BIGN);                               /* 1.375 MB in 64 KB chunks, the atomic steps */
    t[4] = swef_ticks();
    h = swe_fopen_w("BIG2.MK$");
    r = h;
    for (u32 at = 0; at < BIGN && r >= 0; at += K64)
        r = swe_fwrite(h, SWEF_BIG + at, K64);
    if (h >= 0) {
        int c = swe_fclose(h);
        r = r < 0 ? r : c;
    }
    r = r < 0 ? r : swe_frename("BIG2.MK$", "BIG2.MK!");
    rc[27] = r < 0 ? r : swe_frename("BIG2.MK!", "BIG2.MKT");
    t[5] = swef_ticks();
    rc[28] = swef_vchunks("BIG2.MKT", 8, BIGN, K64);            /* ... read back in 64 KB chunks */
    SWEF_RES.bytes = BIGN;
    static const int want[] = {-2, 0, 0, -2, 0, 0, 0, 0, 1000, 0, -2, 100, 0, -2, 512, 512, 1, 512, 1, 3000, 2000, 0,
                               -3, 0, 0, BIGN, 0, 0, 0};
    for (u32 i = 0; i < sizeof want / sizeof want[0]; i++)
        SWEF_RES.bad |= (u32)(rc[i] != want[i]) << i;
    SWEF_RES.done = 1;
}
#endif
