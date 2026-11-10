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

/* 4.2 P7: conti.c draw_groups' placement, moved here (obj1 had no room): m clubs x / v (via) / k (key) in seeding
   order (pot p = x[p*ng ..]), as[] their associations. mode = rule (conti.h A_*) | hold << 4 (the holder x[0] into
   group A's first slot) | 0x20 (ED_S: ct_sdraw) | tries << 8 (the 411 draw: 16 with ED_R, else 1). Out: x / v / k in
   slot order (slot g * gs + p), ng * gs of them, 0 = empty. Returns 0, or ct_sdraw's refusal (< 0: nothing placed).
   The 411 path is conti.c's code as it was (4.1.1: the same rng steps, the same slots). */
enum { PA_ANY, PA_NO, PA_NOVIA, PA_NO2 };
#define PNE 64
static uint32_t pbelow(uint32_t *rng, uint32_t n)
{
    *rng = *rng * 1103515245u + 12345u;
    return n ? ((*rng >> 16) * n) >> 16 : 0;
}
static int pconf(const uint8_t *as, int a, int b, int va, int vb, int rule)   /* (conti.c conflict(): club indices) */
{
    if (rule == PA_ANY) return 0;
    if (as[a] != as[b]) return 0;
    if (rule == PA_NOVIA && (va || vb)) return 0;
    return 1;
}
int ct_place(int m, int ng, int gs, int mode, uint16_t *x, uint8_t *v, uint8_t *k, const uint8_t *as, uint32_t *rng,
             int tag)
{
    int rule = mode & 15, hold = mode >> 4 & 1, size = ng * gs;
    uint8_t S[PNE];                     /* slot -> club index + 1 */
    if (mode & 0x20) {
        uint8_t sa[PNE], grp[PNE];
        for (int i = 0; i < m; i++)     /* (a via club under A_NOVIA: a value of its own, above every association's) */
            sa[i] = rule == PA_NOVIA && v[i] ? (uint8_t)(0x80 + i) : as[i];
        pbelow(rng, 0);                 /* (the seed: exactly one step of the edition's rng, whatever the outcome) */
        int rc = ct_sdraw(m, ng, rule == PA_ANY ? 0 : sa, rule == PA_NO2 ? 2 : 1, *rng, grp, tag);
        if (rc < 0) return rc;
        int h = hold ? grp[0] : 0;      /* (the holder in group A: its group and A swap labels - still a valid draw) */
        for (int i = 0; i < PNE; i++) S[i] = 0;
        for (int i = 0; i < m; i++) {
            int g = grp[i] == h ? 0 : grp[i] == 0 ? h : grp[i];
            S[g * gs + i / ng] = (uint8_t)(i + 1);
        }
    } else
        for (int tr = 0, tries = mode >> 8; tr < tries; tr++) {
            for (int i = 0; i < PNE; i++) S[i] = 0;
            for (int p = 0; p < gs; p++) {
                int base = p * ng, pn = 0;
                uint8_t px[PNE];
                for (int i = base; i < base + ng && i < m; i++) px[pn++] = (uint8_t)i;
                if (p == 0 && hold) {
                    S[0] = px[0] + 1;
                    for (int i = 1; i < pn; i++) px[i - 1] = px[i];
                    pn--;
                }
                for (int i = pn - 1; i > 0; i--) {   /* (conti.c shuffle()) */
                    int j = pbelow(rng, i + 1);
                    uint8_t t = px[i]; px[i] = px[j]; px[j] = t;
                }
                for (int i = 0; i < pn; i++) {
                    int best = -1, g0 = pbelow(rng, ng), c = px[i];
                    for (int t = 0; t < ng; t++) {   /* (every group once, from a drawn one) */
                        int g = (t + g0) % ng, s = g * gs + p;
                        if (S[s]) continue;
                        int bad = 0;
                        for (int q = 0; q < p; q++) {
                            int o = S[g * gs + q];
                            if (o && pconf(as, o - 1, c, v[o - 1], v[c], rule)) bad = 1;
                        }
                        if (!bad) { best = s; break; }
                        if (best < 0) best = -2 - s;        /* (a slot with a conflict: the last resort) */
                    }
                    if (best < -1) best = -2 - best;
                    if (best < 0)                           /* (every free slot taken by the loop's order: any free) */
                        for (int g = 0; g < ng; g++) if (!S[g * gs + p]) { best = g * gs + p; break; }
                    if (best >= 0) S[best] = (uint8_t)(c + 1);
                }
            }
            int cl = 0;                 /* (conti.c clash(): drawn again while two that may not meet share a group) */
            for (int g = 0; g < ng && !cl; g++)
                for (int p = 1; p < gs; p++)
                    for (int q = 0; q < p; q++) {
                        int a = S[g * gs + p], b = S[g * gs + q];
                        if (a && b && pconf(as, b - 1, a - 1, v[b - 1], v[a - 1], rule)) cl = 1;
                    }
            if (!cl) break;
        }
    uint16_t ox[PNE];
    uint8_t ov[PNE], ok[PNE];
    for (int i = 0; i < m; i++) { ox[i] = x[i]; ov[i] = v[i]; ok[i] = k[i]; }
    for (int s = 0; s < size; s++) {
        int i = S[s];
        x[s] = i ? ox[i - 1] : 0; v[s] = i ? ov[i - 1] : 0; k[s] = i ? ok[i - 1] : 0;
    }
    return 0;
}
