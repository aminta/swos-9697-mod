/* 4.1 RC3 part 2 (Davide 09/11): the UEFA prizes' value pillar and their ANDAMENTO CLUB switch. obj4's 5th page
   (swreg.UPRIZE2_AT, MC 09/11: this page uprize's alone), tools/uprize.py; uprize.c (part 1) keeps the state and pays.

   The value pillar (UEFA circular No. 48/2026, 1.1.2.3 / 1.2.3 / 1.3.3), paid with the participation (uprize.c
   up_res -> UP_VFN), from the 36 clubs of the cup's league phase (UD: team words +12Dh; their coefficients by lp36's
   lp_cb_coef = uefacoef's uc_coef, the mod's 5-year club coefficient with the association floor):
   - European part: the clubs ranked by their association's media-market order (UP_MKT, uprize.py: approximated - UEFA
     does not publish it) and, inside one association, by coefficient (UEFA: group-stage seasons over 5 years); a
     second ranking by coefficient; the European rank = the sum of the two ranks, ties by the coefficient rank;
     36 - rank + 1 shares;
   - non-European part: the coefficient rank (UEFA: the 10-year coefficient; the mod keeps 5 years); 36 - rank + 1
     shares. Ties in a coefficient: the contest order (the row).
   UPV: the last payment's ranks and amount (the harness). */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern u8 UD[];                         /* DIY_competitionStart */
extern const u8 UP_MKT[];               /* uprize.py: association file numbers in media-market order, 0-ended */
extern const u32 UP_VSH[3][2];          /* uprize.py: a share x K (European, non-European) per cup */
void up_credit(u32 a);                  /* uprize.c */
void LPCOEF(void);                      /* lp36 lp_cb_coef: edx = row, eax = fallback -> eax = its club coefficient */

#define w16(p) (*(const u16 *)(p))

struct { u32 tag; u8 e, b, pad[2]; u32 a; } UPV = { 0x56505555 };   /* 'UUPV' */

static u32 coef(u32 r) {
    u32 v;
    __asm__ volatile("call LPCOEF" : "=a"(v) : "d"(r), "a"(0) : "memory", "cc");
    return v;
}
static u32 mkt(u32 r) {                 /* the association's place in the media-market order (not listed: after, by file) */
    u32 f = w16(UD + 0x12D + 2 * r) & 0xFF, k;
    for (k = 0; UP_MKT[k]; k++) if (UP_MKT[k] == f) return k;
    return 64 + f;
}

void up_value(u32 me) {
    u32 c[36], m[36], a[36], b[36], i, j;
    for (i = 0; i < 36; i++) { c[i] = coef(i); m[i] = mkt(i); }
    for (i = 0; i < 36; i++) {          /* the ranks, 0-based: a by market then coefficient, b by coefficient */
        a[i] = b[i] = 0;
        for (j = 0; j < 36; j++) {
            u32 cb = c[j] > c[i] || (c[j] == c[i] && j < i);
            b[i] += cb;
            a[i] += m[j] < m[i] || (m[j] == m[i] && cb);
        }
    }
    u32 e = 0;
    for (j = 0; j < 36; j++) e += a[j] + b[j] < a[me] + b[me] || (a[j] + b[j] == a[me] + b[me] && b[j] < b[me]);
    u32 cup = UD[0x2D];
    UPV.e = (u8)e;
    UPV.b = (u8)b[me];
    UPV.a = UP_VSH[cup][0] * (36 - e) + UP_VSH[cup][1] * (36 - b[me]);
    up_credit(UPV.a);
}
