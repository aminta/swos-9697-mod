/* ctdraw.c - 4.2 engine P7: the World 2026-27 confederation cups' group draw by the rules library's
   sr_group_draw_k (tools/swce/sr_stage.c, cap 1 = sr_group_draw_p), on the engine's C stack (cstack.h).

   In the exe it is #included by ctband.c (4.2 AFC mode: its own link after lrank's in the code band - MC 11/11); conti.c calls
   ct_place through its obj1 .data pointer CT_SDRAW (conti.py sdraw_patch). NATIVE (conti.py --test): compiled on its own with
   sr_stage.c and called directly.

   ct_sdraw(n, g, assoc, cap, seed, grp, tag): n clubs in seeding order (pot p = clubs p*g .. p*g+g-1) into g
   groups, assoc NULL = no rule; grp[c] = club c's group. Returns g, or the library's refusal (CONVENTIONS 14a: never
   relaxed): -1 bad arguments, -2 no draw exists, -3 undecided in the budget, -4 the C stack refused the call.
   tag = season << 8 | cup << 4 | round. CT_SDRAW_N counts the draws made; CT_SDRAW_ERR = tag << 8 | -rc, the first
   refusal only (the harness asserts 0). CT_SDRAW_HIT (4.2 AFC mode, MC 11/11 gate item 4): the draws whose search
   budget ran out (the library's sr_gdraw_hits delta: still a draw, not surely the rule's own; the harness asserts 0,
   a real season that hits it is a reported bug). CT_SDRAW_FORCE (test builds only, -DCTDRAW_FORCE): from season << 16 |
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

uint32_t CT_SDRAW_N = 0, CT_SDRAW_ERR = 0, CT_SDRAW_HIT = 0;
#ifdef NATIVE
uint32_t CT_SDRAW_MAXU = 0;             /* (conti.py drawgate: the most steps of one library draw since reset) */
uint32_t CT_PSEED[256];                 /* (the gate's game seeds: each (cup << 4 | round)'s ct_place rng before its
                                           step, the last edition's) */
#endif
#if defined(CTDRAW_FORCE) || defined(NATIVE)
uint32_t CT_SDRAW_FORCE = 0;
#endif

struct ct_sjob { int32_t n, g, cap; const uint8_t *assoc; uint32_t seed; uint8_t *grp; };

static int ct_sjob_run(void *a)         /* (cap 0, 4.2 AFC mode: the fewest of an association a group, _m) */
{
    struct ct_sjob *j = a;
    return j->cap ? sr_group_draw_k(j->n, j->g, j->assoc, 0, 0, j->cap, j->seed, j->grp)
                  : sr_group_draw_m(j->n, j->g, j->assoc, j->seed, j->grp);
}

int ct_sdraw(int n, int g, const uint8_t *assoc, int cap, uint32_t seed, uint8_t *grp, int tag)
{
    struct ct_sjob j = { n, g, cap, assoc, seed, grp };
    uint32_t h0 = sr_gdraw_hits;
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
    CT_SDRAW_HIT += sr_gdraw_hits - h0;
#ifdef NATIVE
    if (sr_gdraw_used > CT_SDRAW_MAXU) CT_SDRAW_MAXU = sr_gdraw_used;   /* (the gate: the most steps since reset) */
#endif
    if (rc >= 0)
        CT_SDRAW_N++;
    else if (!CT_SDRAW_ERR)
        CT_SDRAW_ERR = (uint32_t)tag << 8 | (uint8_t)-rc;
    return rc;
}

/* 4.2 P7: conti.c draw_groups' placement, moved here (obj1 had no room): m clubs x / v (via) / k (key) in seeding
   order (pot p = x[p*ng ..]), as[] their associations. mode = rule (conti.h A_*) | hold << 4 (the holder x[0] into
   group A's first slot) | 0x20 (ED_S: ct_sdraw) | 0x40 (per region, ED_S only) | tries << 8 (the 411 draw: 16 with
   ED_R, else 1).
   4.2 AFC mode: per region, as[i] bit 7 = club i's region (0 West: groups 0 .. ng/2 - 1, 1 East: the rest, ACL Two
   A-D / E-H); each region drawn on its own over ng/2 groups, its clubs in their seeding order (pot p = its clubs
   p*ng/2 ..), the holder into its region's first group; seeds: West the edition's one rng step, East that ^
   0x9E3779B9. A_MIN = ct_sdraw cap 0 (sr_group_draw_m). Out: x / v / k in
   slot order (slot g * gs + p), ng * gs of them, 0 = empty. Returns 0, or ct_sdraw's refusal (< 0: nothing placed).
   The 411 path is conti.c's code as it was (4.1.1: the same rng steps, the same slots). */
enum { PA_ANY, PA_NO, PA_NOVIA, PA_NO2, PA_MIN };
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
        uint8_t sa[PNE], grp[PNE], ord[PNE];   /* (by draw position j: club ord[j], West's first, then East's) */
        int nh = mode & 0x40 ? 2 : 1, hg = ng / nh, nw = 0, j = 0;
        for (int h = 0; h < nh; h++)
            for (int i = 0; i < m; i++)
                if (nh == 1 || as[i] >> 7 == h) {   /* (a via club under A_NOVIA: a value of its own, above every
                                                       association's) */
                    ord[j] = (uint8_t)i;
                    sa[j++] = rule == PA_NOVIA && v[i] ? (uint8_t)(0x80 + i) : as[i] & 0x7F;
                    nw += !h;
                }
#ifdef NATIVE
        CT_PSEED[tag & 0xFF] = *rng;
#endif
        pbelow(rng, 0);                 /* (the seed: exactly one step of the edition's rng, whatever the outcome) */
        for (int h = 0; h < nh; h++) {
            int o = h ? nw : 0, n = h ? m - nw : nw;
            if (!n) continue;
            int rc = ct_sdraw(n, hg, rule == PA_ANY ? 0 : sa + o, rule == PA_NO2 ? 2 : rule == PA_MIN ? 0 : 1,
                              *rng ^ (h ? 0x9E3779B9u : 0), grp + o, tag);
            if (rc < 0) return rc;
            for (int q = o; q < o + n; q++) grp[q] = (uint8_t)(grp[q] + h * hg);
        }
        int j0 = 0;
        while (hold && ord[j0]) j0++;   /* (the holder x[0] in its region's first group: the two swap labels - still
                                           a valid draw) */
        int hb = j0 >= nw ? hg : 0, hl = hold ? grp[j0] : hb;
        for (int i = 0; i < PNE; i++) S[i] = 0;
        for (j = 0; j < m; j++) {
            int g = grp[j] == hl ? hb : grp[j] == hb ? hl : grp[j];
            S[g * gs + (j - (j >= nw ? nw : 0)) / hg] = (uint8_t)(ord[j] + 1);
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

#ifdef NATIVE
/* 4.2 AFC mode, the build's draw gate (MC 11/11; conti.py drawgate): one association multiset as0[] (m clubs, bit 7
   the region), v0[] via flags, mode as ct_place's (ED_S), over ns seeds: s0[0 .. ns0) given (the game's), the rest
   an LCG from seed0. Each seed: the clubs in an order of its own (a shuffle by the seed), then ct_place with rng =
   the seed. out[0] the most steps (one library draw), out[1] its seed index, out[2] budget hits, out[3] refusals,
   out[4] the first refused seed index + 1; wo[] / wv[] / *ws the worst seed's order and rng (Unicorn's replay). */
int ct_gate(int m, int ng, int gs, int mode, const uint8_t *as0, const uint8_t *v0, const uint32_t *s0, int ns0,
            int ns, uint32_t seed0, uint32_t *out, uint8_t *wo, uint8_t *wv, uint32_t *ws)
{
    uint32_t lcg = seed0 ? seed0 : 1;
    out[0] = out[1] = out[2] = out[3] = out[4] = 0;
    for (int s = 0; s < ns; s++) {
        uint32_t sd = s < ns0 ? s0[s] : (lcg = lcg * 1664525u + 1013904223u);
        uint8_t as[PNE], v[PNE], k[PNE];
        uint16_t x[PNE];
        uint32_t r = sd ^ 0x5bd1e995u;
        for (int i = 0; i < m; i++) { as[i] = as0[i]; v[i] = v0[i]; }
        for (int i = m - 1; i > 0; i--) {   /* (the order: a shuffle of its own, by the seed) */
            int j = pbelow(&r, i + 1);
            uint8_t t = as[i]; as[i] = as[j]; as[j] = t;
            t = v[i]; v[i] = v[j]; v[j] = t;
        }
        for (int i = 0; i < m; i++) { x[i] = (uint16_t)(i + 1); k[i] = 0; }
        uint8_t oa[PNE], ov[PNE];
        for (int i = 0; i < m; i++) { oa[i] = as[i]; ov[i] = v[i]; }
        uint32_t h0 = CT_SDRAW_HIT, rng = sd;
        CT_SDRAW_MAXU = 0;
        int rc = ct_place(m, ng, gs, mode, x, v, k, as, &rng, 0);
        out[2] += CT_SDRAW_HIT - h0;
        if (rc < 0) { out[3]++; if (!out[4]) out[4] = (uint32_t)s + 1; }
        if (CT_SDRAW_MAXU > out[0] || s == 0) {
            out[0] = CT_SDRAW_MAXU; out[1] = (uint32_t)s; *ws = sd;
            for (int i = 0; i < m; i++) { wo[i] = oa[i]; wv[i] = ov[i]; }
        }
    }
    return 0;
}
#endif
