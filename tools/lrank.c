/* 4.2 S1.3: a career league's table by its real tie-breaker list (FIGC 2026-27: the classifica avulsa ...), the
   engine's sr_league_rank (tools/swce/sr_stage.c, the rules library at tools/swce/SWCE_SHA). obj4 (tools/lrank.py).

   The career club's league (a league DIY holding CAREERTEAM, in a career: g_gameType 4) whose (league struct D8CAA,
   world, division D6CDC) has an entry in LR_TAB, and DIY is that division's table (H5 B1: one group of the
   division's clubs - a European group / league phase or a gplay group contest holding the career club is a league
   layout too, under the same globals):
   - lr_res (cseg_88CBB, where a result goes into the rows: chained before split's sp_res, or the game's own
     `add word [esi+1BDh], 1`): the result into the pairs block LR_BLK, one byte per ordered pair (home goals << 4 |
     away goals, each 0..14, FFh not played) - saved with the career (engine item 'LR', lrank.LR_SIZE). The block is
     keyed by the season stamp, the club count and the first team word: a new key with every row still at 0 played
     starts it; a new key mid-season (an older save, a season begun before the block, a job change) leaves it void
     until the next season: the head-to-head criteria are then left out (sr_league_rank with pairs NULL);
   - lr_rank (the end of cseg_883DD, the table sort: chained after lp36's lp_sort or the game's own first
     instruction): DIY+6Dh rewritten in sr_league_rank's order. The rows: DIY+2B3h + 18 * k (+4 played, +6 won,
     +8 drawn, +0Ah lost, +0Ch goals for, +0Eh against, +10h points), the win points at +61h, a draw 1, a loss 0.
   A split league (split.py's state magic) keeps split's own order. The play-off matches (SR_TB_PLAY_OFF_MATCH) are
   not in the lists: gplay plays them (pack.json ko_playoffs with gap 1) on the table this order leaves. */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_stage.c"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

extern u8 UD[];                         /* DIY_competitionStart */
extern u8 *A3, *A4;                     /* the result's home / away row (DIY + 18 * row) */
extern u16 D1, D2;                      /* its home / away goals */
extern u16 GAMETYPE, SIMFLAG, CAREERTEAM, D6CDC;
extern u8 *D8CAA;                       /* the career league's struct */
extern u8 WORLDB;                       /* the career's world byte (someLeaguesTable) */
extern u8 SEASONP;                      /* seasonPlaying (uesum's stamp) */

/* LR_TAB (lrank.py): entries of 24 B - u32 league struct, u8 world, u8 division, u8 h2h (1: the list has a
   head-to-head code), u8 the division's clubs, the list (16 codes, 0-ended); ended by a null struct */
extern const u8 LR_TAB[];

#define LR_N 20                         /* the pairs block's clubs (the .CAR's 'EN' room: lrank.LR_SIZE) */
#define VOID 0x80
struct lr_blk { u8 ss, n; u16 t0; u8 p[LR_N * LR_N]; };
struct lr_blk LR_BLK = { 0, 0, 0, { 0 } };
static sr_srow lr_rows[SR_STAGE_CLUBS];
static u8 lr_ord[SR_STAGE_CLUBS];

#define w16(p) (*(const u16 *)(p))
#define ROW(k) (UD + 0x2B3 + 18 * (k))

static __attribute__((noinline)) const u8 *mine(void) {  /* the career league's LR_TAB entry, else 0 */
    u32 n = w16(UD + 0x31), k;
    if (GAMETYPE != 4 || UD[0] || n < 2 || n > SR_STAGE_CLUBS || w16(UD + 0x4F) != 1) return 0;
#ifdef SPLIT_ST
    if (w16(UD + SPLIT_ST) == SPLIT_MAGIC) return 0;
#endif
    for (k = 0; k < n && w16(UD + 0x12D + 2 * k) != CAREERTEAM; k++) ;
    if (k == n) return 0;
    for (const u8 *e = LR_TAB; *(const u32 *)e; e += 24)
        if (*(u8 *const *)e == D8CAA && e[4] == WORLDB && e[5] == D6CDC) return e[7] == n ? e : 0;
    return 0;
}

static u32 stamp(void) { return SEASONP + 1u; }

void lr_res(void) {
    const u8 *e = mine();
    u32 n = w16(UD + 0x31), h = (u32)(A3 - UD) / 18, a = (u32)(A4 - UD) / 18;
    if (!e || SIMFLAG || n > LR_N || h >= n || a >= n) return;
    struct lr_blk *b = &LR_BLK;
    if (b->ss != stamp() || (b->n & ~VOID) != n || b->t0 != w16(UD + 0x12D)) {
        u32 pl = 0;
        for (u32 k = 0; k < n; k++) pl |= w16(ROW(k) + 6) | w16(ROW(k) + 8) | w16(ROW(k) + 10);
        b->ss = (u8)stamp();
        b->t0 = w16(UD + 0x12D);
        b->n = (u8)(n | (pl ? VOID : 0));    /* (a season already under way: void until the next one) */
        for (u32 k = 0; k < LR_N * LR_N; k++) b->p[k] = SR_PAIR_NONE;
    }
    if (b->n & VOID) return;
    u32 hg = D1 > 14 ? 14 : D1, ag = D2 > 14 ? 14 : D2;
    b->p[h * n + a] = (u8)(hg << 4 | ag);
}

void lr_rank(void) {
    const u8 *e = mine();
    if (!e) return;
    u32 n = w16(UD + 0x31);
    const struct lr_blk *b = &LR_BLK;
    const u8 *pairs = e[6] && n <= LR_N && b->ss == stamp() && b->n == n && b->t0 == w16(UD + 0x12D) ? b->p : 0;
    for (u32 k = 0; k < n; k++) {
        const u8 *r = ROW(k);
        sr_srow *s = &lr_rows[k];
        s->club = (u8)k;
        s->pad = 0;
        s->pts = (int16_t)w16(r + 0x10);
        s->pl = w16(r + 4);
        s->w = w16(r + 6);
        s->d = w16(r + 8);
        s->l = w16(r + 10);
        s->gf = w16(r + 12);
        s->ga = w16(r + 14);
        s->aw = s->agf = 0;
    }
    if (pairs)                                  /* (away wins / goals: from the block) */
        for (u32 h = 0; h < n; h++)
            for (u32 a = 0; a < n; a++) {
                u32 x = pairs[h * n + a];
                if (x == SR_PAIR_NONE) continue;
                lr_rows[a].agf += x & 15;
                if ((x & 15) > x >> 4) lr_rows[a].aw++;
            }
    u32 seed = stamp() * 0x9E3779B1u ^ w16(UD + 0x12D);
    if (sr_league_rank((int32_t)n, lr_rows, pairs, 0, w16(UD + 0x61), 1, 0, e + 8, seed, lr_ord) != (int32_t)n) return;
#ifdef LR_FORCE
    /* test builds (LR_FORCE=k): at the league end (every row has played 2 (n - 1)), place k + 1 gets place k's
       points - a level pair for gplay's play-off match (gap 1) */
    u32 full = 1;
    for (u32 k = 0; k < n; k++) full &= lr_rows[k].pl == 2 * (n - 1);
    u32 a = LR_FORCE < n ? lr_ord[LR_FORCE - 1] : 0, z = LR_FORCE < n ? lr_ord[LR_FORCE] : 0;
    if (full && LR_FORCE < n && lr_rows[a].pts != lr_rows[z].pts) {
        *(u16 *)(ROW(z) + 0x10) = (u16)lr_rows[a].pts;
        lr_rows[z].pts = lr_rows[a].pts;
        sr_league_rank((int32_t)n, lr_rows, pairs, 0, w16(UD + 0x61), 1, 0, e + 8, seed, lr_ord);
    }
#endif
    for (u32 k = 0; k < n; k++) *(u16 *)(UD + 0x6D + 2 * k) = (u16)(lr_ord[k] * 18);
}

#ifdef RES_CHAIN
void RES_PREV(void);                    /* split's sp_res (it does the game's add itself) */
__asm__(".globl lr_res_hook\nlr_res_hook:\n\tcall RES_PREV\n\tpushal\n\tcall lr_res\n\tpopal\n\tret\n");
#else
__asm__(".globl lr_res_hook\nlr_res_hook:\n\taddw $1, 0x1BD(%esi)\n\tpushal\n\tcall lr_res\n\tpopal\n\tret\n");
#endif
#ifdef SORT_CHAIN
void SORT_PREV(void);                   /* lp36's lp_sort (its own first instruction, then the sort or its ranking) */
__asm__(".globl lr_sort_hook\nlr_sort_hook:\n\tcall SORT_PREV\n\tpushal\n\tcall lr_rank\n\tpopal\n\tret\n");
#else
void SORT_NEXT(void);                   /* cseg_883DD after its first instruction */
__asm__(".globl lr_sort_hook\nlr_sort_hook:\n\tcall 1f\n\tpushal\n\tcall lr_rank\n\tpopal\n\tret\n"
        "1:\n\tmovl $UD, A4\n\tjmp SORT_NEXT\n");
#endif

/* (4.2 P7's ctdraw.c: its own band since the AFC mode - tools/ctband.c, its own link after this one - MC 11/11) */
