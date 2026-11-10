/* ctdraw.c - 4.2 engine P7: the World 2026-27 confederation cups' group draw by the rules library's
   sr_group_draw_k (tools/swce/sr_stage.c, cap 1 = sr_group_draw_p), on the engine's C stack (cstack.h).

   In the exe it is #included by lrank.c (one linked copy of sr_stage in obj4, P1); conti.c calls ct_sdraw through
   its obj1 .data pointer CT_SDRAW (conti.py sdraw_patch). NATIVE (conti.py --test): compiled on its own with
   sr_stage.c and called directly.

   ct_sdraw(n, g, assoc, cap, seed, grp, tag): n clubs in seeding order (pot p = clubs p*g .. p*g+g-1) into g
   groups, assoc NULL = no rule; grp[c] = club c's group. Returns g, or the library's refusal (CONVENTIONS 14a: never
   relaxed): -1 bad arguments, -2 no draw exists, -3 undecided in the budget, -4 the C stack refused the call.
   tag = season << 8 | cup << 4 | round. CT_SDRAW_N counts the draws made; CT_SDRAW_ERR = tag << 8 | -rc, the first
   refusal only (the harness asserts 0). CT_SDRAW_FORCE (test builds only, -DCTDRAW_FORCE): from season << 16 |
   (cup << 4 | round) + 1 = that round refused (-2) in that season's editions and later ones. */
#ifdef NATIVE
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_stage.c"
#else
#include "cstack.h"
void swe_ready(void);                   /* (swe.c: cstack_init once, the arena left as it is) */
#endif

uint32_t CT_SDRAW_N = 0, CT_SDRAW_ERR = 0;
#if defined(CTDRAW_FORCE) || defined(NATIVE)
uint32_t CT_SDRAW_FORCE = 0;
#endif

struct ct_sjob { int32_t n, g, cap; const uint8_t *assoc; uint32_t seed; uint8_t *grp; };

static int ct_sjob_run(void *a)
{
    struct ct_sjob *j = a;
    return sr_group_draw_k(j->n, j->g, j->assoc, 0, 0, j->cap, j->seed, j->grp);
}

int ct_sdraw(int n, int g, const uint8_t *assoc, int cap, uint32_t seed, uint8_t *grp, int tag)
{
    struct ct_sjob j = { n, g, cap, assoc, seed, grp };
    int rc;
#if defined(CTDRAW_FORCE) || defined(NATIVE)
    if ((CT_SDRAW_FORCE & 0xFF) == ((uint32_t)tag & 0xFF) + 1 && (uint32_t)tag >> 8 >= CT_SDRAW_FORCE >> 16)
        rc = -2;
    else
#endif
#ifdef NATIVE
        rc = ct_sjob_run(&j);
#else
    {
        swe_ready();
        rc = cstack_call(ct_sjob_run, &j);
    }
#endif
    if (rc >= 0)
        CT_SDRAW_N++;
    else if (!CT_SDRAW_ERR)
        CT_SDRAW_ERR = (uint32_t)tag << 8 | (uint8_t)-rc;
    return rc;
}
