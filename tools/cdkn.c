/* 4.2 S2 knockouts (MC 14/11, 42-cdkn): the Coppa Italia Serie D's rounds 0-1 of a later season by the engine's knockout
   library (swce/sr_kn.c, fuzz-tested, its one copy in the exe). obj4 band CDKN (swreg.CDKN_AT), linked by cdkn.py only in
   CD_KN builds; gplay.c's cd_make calls cdkn_make through GP_CDKN after its loop over the Serie D clubs (ord / grp / key:
   the file ordinal, the girone, the entry key << 8 | a draw - cd_season's ent: 1 a new arrival, 2 + the place from the
   bottom of last season's girone, 40h unknown).

   The LND format (C.U. 1 of the Dipartimento Interregionale; the engine's Coppa D spec, s2ko_glue d_rd):
   - the entry order (sr_kn_number): group 0 = the 2p preliminary clubs, the new arrivals first (in drawn order), then the
     others from the bottom of last season's tables (SR_KN_PLACE_DESC, place = 200 - ent: the lower first; unknown last);
     group 1 = everybody else (they enter at round 1: a bye through the preliminary);
   - round 0 (p ties) and round 1 (n1 ties: the p winners + the n - 2p joiners) drawn within geographic blocks
     (SR_KN_PAIR_GEO, blocks of 2 / 4): neighbours meet; tie k of round 1 next to k + 1 (round 2's fixed bracket).
   The draw needs no result: round 0's ties 'played' with the home side through (its club stands for the tie's winner -
   CD_REF(t) in gen), the stop at round 1's first tie (its ties all drawn by then). Side a = the engine's home: it counts
   where the table's host is 'listed' (cd_step_c decides 'drawn' / 'alternate' as before).
   Geography: geo[club] = its town by Panchina's s7geo_ll (S7GEO band, the one source: CDKN_LL, S7 builds with the
   coordinates); a club without one (or no S7GEO band) = its girone's centre (CDKN_CTR, cdkn.py) + a per-season jitter of
   +-0.20 degrees - interim, test switch only.
   Never silent (MC 14/11): every refusal or shape the form cannot express returns 0 (today's cd_make) and logs
   season << 8 | reason in CDKN_LOG (8 entries, CDKN_NLOG counts), CDKN_OK counts the engine's draws. */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_kn.c"
#ifndef DATA
#define DATA __attribute__((section(".data")))
#endif
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
enum { CDP = 41, CD1 = 64, CDKN_G = 16 };
enum { WHY_SHAPE = 1, WHY_NUMBER = 2, WHY_CUP = 3, WHY_GEO = 4, WHY_TEST = 9 };

struct cdkn_ws {
    sr_kn_work w;
    sr_kn_rec rec[SR_KN_CLUBS];
    sr_kn_geo geo[SR_KN_CLUBS];
    u8 el[SR_KN_CLUBS];
    u16 arr[256], rest[256], num[SR_KN_NUMBERS];
    sr_kn_entry join[256];
    sr_kn_tie out[CDP + CD1];
};
extern u8 CDKN_WORK[];
#ifdef CDKN_TMGR
extern u16 GP_MGR;
#endif                  /* (swe.c's .bss, CDKN_WORK_SZ >= sizeof(struct cdkn_ws): cdkn.py asserts) */
const u32 CDKN_WSZ = sizeof(struct cdkn_ws);
int16_t CDKN_CTR[CDKN_G][2] DATA = {{0}};      /* (the gironi's centres, lat / lon in 0.01 degree; cdkn.py) */
u8 CDKN_NCTR DATA = 0;
u32 CDKN_LOG[8] DATA = {0};
u32 CDKN_NLOG DATA = 0;
u32 CDKN_OK DATA = 0;
int32_t (*CDKN_LL)(uint32_t w, int16_t *lat, int16_t *lon) DATA = 0;   /* (Panchina's s7geo_ll, S7GEO band - the one
                                           source of the clubs' towns; cdkn.py sets it when linked; 0 = CDKN_CTR) */
u8 CDKN_TFALL DATA = 0;                 /* (the harness: 1 = refuse, the fallback's forced case) */

static int fall(u32 seas, int why)
{
    CDKN_LOG[CDKN_NLOG & 7] = seas << 8 | (u32)why;
    CDKN_NLOG++;
    return 0;
}

static int32_t play(void *ctx, int32_t r, int32_t t, const sr_kn_tie *o)
{
    (void)ctx; (void)t; (void)o;
    return r ? -1 : 0;                  /* (round 0: the home side through; round 1 drawn: stop) */
}

static u32 below_(u32 *rng, u32 n)
{
    *rng = *rng * 1103515245u + 12345u;
    return ((*rng >> 16) * n) >> 16;
}

extern const u8 *GP_CDT;                /* (gplay.c: the running world's CD_TAB - [1] rounds, [2] the Serie D file) */
extern u8 GP_SEAS;
extern u8 CD_ST[];                      /* (gplay.c's struct cd_state, its saved layout: cdkn.py asserts CD_SIZE) */
enum { CD_EFRESH = 604, CD_GENON = 605, CD_NP = 606, CD_GEN = 612 };

int cdkn_make(const u8 *ord, const u8 *grp, const u16 *key, int n)
{
    const int rounds = GP_CDT[1], lf = GP_CDT[2];
    const u32 seas = GP_SEAS;
    u16 *gen = (u16 *)(CD_ST + CD_GEN);
    struct cdkn_ws *W = (struct cdkn_ws *)CDKN_WORK;
    sr_kn_list lists[2];
    sr_kn_group g[2];
    sr_kn_round rd[2];
    u8 *gb;
    int n1, p, na = 0, nr = 0;
    u32 rng = seas * 40503u + 5;
    if (CDKN_TFALL) return fall(seas, WHY_TEST);
    if (rounds < 3 || rounds > 8 || n < 2 || n > 256) return fall(seas, WHY_SHAPE);
    n1 = 1 << (rounds - 2);
    p = n - 2 * n1;
    if (p <= 0 || p > CDP || n1 > CD1) return fall(seas, WHY_SHAPE);
    for (int i = 0; i < SR_KN_CLUBS; i++) {
        W->el[i] = 0;
        W->rec[i].pts = W->rec[i].pld = W->rec[i].won = W->rec[i].gf = 0;
        W->rec[i].place = 0;
    }
    for (int i = 0; i < n; i++) {
        const int c = ord[i];
        int e = key[i] >> 8;
#ifdef CDKN_TMGR                        /* (test builds: the career club forced - 1 an arrival: the preliminary; 2 unknown:
                                           the last in the order, a bye to round 1) */
        if (GP_MGR && (u16)(lf | c << 8) == GP_MGR) e = CDKN_TMGR == 1 ? 1 : 0x40;   /* (S6a: GP_MGR 0, no manager) */
#endif
        if (grp[i] >= CDKN_NCTR) return fall(seas, WHY_GEO);
        W->el[c] = 1;
        if (e == 1) W->arr[na++] = (u16)c;
        else {
            W->rest[nr++] = (u16)c;
            W->rec[c].place = (u8)(e >= 2 && e < 0x40 ? 200 - e : 0);
            W->rec[c].pld = 1;
        }
        {
            int16_t la, lo;
            const u32 jl = below_(&rng, 41), jo = below_(&rng, 41);   /* (drawn either way: the draw's sequence) */
            if (CDKN_LL && CDKN_LL((u32)(lf | c << 8), &la, &lo)) { W->geo[c].lat = la; W->geo[c].lon = lo; }
            else {
                W->geo[c].lat = (int16_t)(CDKN_CTR[grp[i]][0] + (int)jl - 20);
                W->geo[c].lon = (int16_t)(CDKN_CTR[grp[i]][1] + (int)jo - 20);
            }
        }
    }
    for (int i = na - 1; i > 0; i--) {  /* (the new arrivals in drawn order) */
        const int j = (int)below_(&rng, (u32)i + 1);
        const u16 x = W->arr[i]; W->arr[i] = W->arr[j]; W->arr[j] = x;
    }
    lists[0].club = W->arr; lists[0].n = na; lists[0].unknown = SR_KN_NONE;
    lists[1].club = W->rest; lists[1].n = nr; lists[1].unknown = SR_KN_NONE;
    gb = (u8 *)g;
    for (u32 i = 0; i < sizeof g; i++) gb[i] = 0;
    g[0].take = (u8)(2 * p); g[0].order = SR_KN_LIST; g[0].else_order = SR_KN_PLACE_DESC;
    g[0].nfrom = 1; g[0].nelse = 1; g[0].from[0] = 0; g[0].els[0] = 1;
    g[1].take = (u8)(n - 2 * p); g[1].order = SR_KN_LIST; g[1].else_order = SR_KN_LIST;
    g[1].nfrom = 1; g[1].nelse = 1; g[1].from[0] = 1; g[1].els[0] = 0;
    if (n - 2 * p > 255 || sr_kn_number(g, 2, lists, W->rec, W->el, &rng, &W->w, W->num, SR_KN_NUMBERS) != n)
        return fall(seas, WHY_NUMBER);
    for (int i = 0; i < n; i++) { W->join[i].club = W->num[i]; W->join[i].zone = 0; W->join[i].pad = 0; }
    W->w.geo = W->geo;
    rd[0].ties = (u16)p; rd[0].first = 0; rd[0].legs = 1; rd[0].home = SR_KN_DRAW; rd[0].pairing = SR_KN_PAIR_GEO;
    rd[0].block = 2; rd[0].jfirst = 0; rd[0].njoin = (u16)(2 * p);
    rd[1].ties = (u16)n1; rd[1].first = (u16)p; rd[1].legs = 1; rd[1].home = SR_KN_DRAW; rd[1].pairing = SR_KN_PAIR_GEO;
    rd[1].block = 4; rd[1].jfirst = (u16)(2 * p); rd[1].njoin = (u16)(n - 2 * p);
    if (sr_kn_cup(rd, 2, 0, 0, 0, W->join, 0, &rng, play, 0, &W->w, W->out) != -1) return fall(seas, WHY_CUP);
    for (int t = 0; t < p; t++) {
        gen[2 * t] = (u16)(lf | W->out[t].home << 8);
        gen[2 * t + 1] = (u16)(lf | W->out[t].away << 8);
    }
    for (int t = 0; t < n1; t++)
        for (int s = 0; s < 2; s++) {
            const u16 c = s ? W->out[p + t].away : W->out[p + t].home;
            u16 v = (u16)(lf | c << 8);
            for (int k = 0; k < p; k++)
                if (W->out[k].home == c) v = (u16)(k << 8 | 0xFF);  /* (round 0's tie k: its winner, CD_REF) */
            gen[2 * (p + t) + s] = v;
        }
    CD_ST[CD_NP] = (u8)p;
    CD_ST[CD_GENON] = 1;
    CD_ST[CD_EFRESH] = 0;
    CDKN_OK++;
    return 1;
}
