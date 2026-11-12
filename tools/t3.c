/* 4.2.y T3 "mini primavera" (Davide 12/11 via Regia): TRASFERIMENTI > ACQUISTA GIOCATORE > PRIMAVERA, a page of six
   boys 17-19 of the club's youth team; fire on one signs him; one signing a month (a period = 4 calendar weeks).
   obj4 page 14 (swreg.T3_AT, tools/t3.py: this file, then the glue with the packed menu T3_MENU).

   The list is a pure function of (the career club, currentSeasonNumber, the period, the row) and of the squad and
   the career's team pool as they are: the same week shows the same boys, also after a save and a load; the next
   period other ones. It draws nothing from the game's random generators: the name comes from the game's own
   cseg_52B6A (a first name and a surname of two random players of the career's team pool, as a trial player's) run
   with Rand2's state (seed2, randXorIndex2, randXorKey2) set from the row's hash and put back after it, with the
   game's D0..A6 and the name buffer it writes; Rand is never touched.

   A boy: his role from the squad's largest gap against the oracle's ROLE_TARGET (G 3, D 9, M 10, A 5; at most 3 of
   one), his position by the trial tables (D: RB LB D D, M: RW LW M M); his level (the price index, oracle v3 rules)
   = 0.7 x the club's XI median + 0.3 x its division's XI median (the pool's clubs of its file and division) - 10
   + a normal draw of sd 3.5 (four bytes of the hash), 0..49; the game's own skill template of that level / 3 and
   position (cseg_567B5's tail: dseg_17A1A4 / dseg_17A184), his price their sum as the game's. The age (17-19) is the
   page's only: the game keeps no age. The row's + marks: his price against the club's XI median (+++++ = 6 below
   it or better, one + less every 4 below; the boys' templates run some 14 below the XI median: +++).

   Signing (t3_sign) = what the game's purchase does (cseg_56379, as bteam's bt_add): the lowest free slot, its
   trainingMatchSavedPlayers entry (cseg_63919), the record (bought mark +1Ah bit 2, stats 0, status +25h 0: a
   squad player, not a trial one), after the 11 + bench in currentMatchPlayers, SetBenchPlayersNumbers,
   careerNumPlayers + 1, his wage (cseg_5E345). Then T3_ITEM = the period's code (engine item 'T3', 1 B; 0 = none).
   Closed: a boy already signed this period, the squad full (30, the game's trial cap), a national selector. */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;

extern u8 CT[];                         /* careerTeam: the 76-B header, then 38-B records by slot */
extern u16 CNP;                         /* careerNumPlayers */
extern u8 CMP[];                        /* currentMatchPlayers: the squad's slots in order */
extern u16 SELT;                        /* selTeamNumber */
extern u16 ISNAT;                       /* isNationalSelector */
extern u8 COMPFB[];                     /* competitionFileBuffer (the bench size: +65h, a type-2 file +4Dh) */
extern u16 CFB;                         /* careerFileBuffer: the pool's team count */
extern u8 TMD[];                        /* tmdFileBuffer: the pool, 684-B team records */
extern u16 CSN;                         /* currentSeasonNumber */
extern u8 CAL[];                        /* the career calendar (+1 of an entry: its week) */
extern u16 CAL_CUR;                     /* the current entry's offset */
extern u32 TPL[];                       /* dseg_17A1A4: the skill templates, [level][position] */
extern u32 TPB[];                       /* dseg_17A184: the position's base bits */
extern u8 R2S, R2I, R2K;                /* Rand2: seed2, randXorIndex2, randXorKey2 */
extern char NBUF[];                     /* cseg_52B6A's name buffer (dseg_17A3D0, 23 B) */
extern u8 DREG[];                       /* the game's D0..D7, A0..A6 */
extern const char T3_POSN[];            /* the exe's 8 position abbreviations, 4 B each (the glue) */
extern const char T3_S_OPEN[], T3_S_DONE[], T3_S_FULL[];
void C52B6A(void);
void C63919(void);
void SETBENCH(void);
void WAGE(void);
void CALC(void);                       /* CalcMenuEntryAddress: entry D0 -> A0 */

#define NB 6                            /* the boys */
#define PL 38
#define LW 40                           /* a row's text */
#define MAXP 30                         /* the squad's cap (CheckPlayersLeavingComing's) */
#define SALT 0x54335933u

u8 T3_ITEM;                             /* engine item 'T3' (the glue's ITEM_AT): the period code of the last signing */
u8 T3_REC[NB][PL];                      /* the boys' records (written on every open: DOS/4GW zeroes nothing) */
u8 T3_AGE[NB];
char T3_LBL[NB][LW];
char T3_MSG[LW];
u32 T3_STATE;                           /* 0 open, 1 signed this period, 2 squad full, 3 national selector */
u32 T3_SIGNED;                          /* (harness: signings made by this exe since boot) */
u32 T3_CODE;                            /* (harness: the period code of the last list) */
u32 T3_OWN;                             /* the club's XI median price (the rows' + marks) */

#define D(k) (*(u32 *)(DREG + 4 * (k)))
#define A(k) (*(u32 *)(DREG + 32 + 4 * (k)))

static u32 hmix(u32 h, u32 v) {
    for (u32 i = 0; i < 4; i++, v >>= 8) { h ^= v & 0xFF; h *= 16777619u; }
    return h;
}
static u32 xs(u32 *s) { u32 x = *s; x ^= x << 13; x ^= x >> 17; x ^= x << 5; return *s = x ? x : 0x9E3779B9u; }
static void cpy(void *d, const void *s, u32 n) { u8 *a = d; const u8 *b = s; while (n--) *a++ = *b++; }
static void zero(void *d, u32 n) { u8 *a = d; while (n--) *a++ = 0; }

u32 t3_code(void) {                     /* the period's code: 1..255 (0 = none), a new one every 4 calendar weeks */
    u32 week = CAL[CAL_CUR + 1];
    return 1 + ((u32)CSN * 64 + (week >> 2)) % 255;
}

static u8 *rec(u32 slot) { return CT + 76 + PL * slot; }

static u32 xi_med(const u8 *p, u32 n, u32 stride) {   /* the 6th highest price of n records (the best XI's median) */
    u8 v[MAXP + 2];
    if (n > MAXP) n = MAXP;
    for (u32 i = 0; i < n; i++) {
        u8 x = p[stride * i + 0x20], j = (u8)i;
        while (j && v[j - 1] < x) { v[j] = v[j - 1]; j--; }
        v[j] = x;
    }
    if (!n) return 0;
    return v[n > 11 ? 5 : n / 2];
}

static u32 club_med(void) {
    u8 tmp[MAXP];
    u32 n = CNP > MAXP ? MAXP : CNP;
    for (u32 i = 0; i < n; i++) tmp[i] = rec(CMP[i])[0x20];
    u8 v[MAXP];
    for (u32 i = 0; i < n; i++) {
        u8 x = tmp[i], j = (u8)i;
        while (j && v[j - 1] < x) { v[j] = v[j - 1]; j--; }
        v[j] = x;
    }
    return n ? v[n > 11 ? 5 : n / 2] : 0;
}

static u32 div_med(u32 own) {           /* the median of the pool's XI medians of the club's file and division */
    u8 v[256];
    u32 n = 0, nt = CFB;
    for (u32 t = 0; t < nt && n < 256; t++) {
        const u8 *r = TMD + 684 * t;
        if (r[0] != CT[0] || r[25] != CT[25] || (r[0] | r[1] << 8) == SELT) continue;
        u8 x = (u8)xi_med(r + 76, 16, PL), j = (u8)n;
        while (j && v[j - 1] < x) { v[j] = v[j - 1]; j--; }
        v[j] = x;
        n++;
    }
    return n ? v[n / 2] : own;
}

/* the game's cseg_52B6A on Rand2's state from h: the name into d (22 B, NUL-padded), the nationality, face bits */
static void name(u32 h, u8 *d, u8 *nat, u8 *face) {
    u8 s0 = R2S, s1 = R2I, s2 = R2K, keep[60], nb[23];
    cpy(keep, DREG, 60);
    cpy(nb, NBUF, 23);
    R2S = (u8)h; R2I = (u8)(h >> 8); R2K = (u8)(h >> 16);
    D(0) = SELT & 0xFF;
    D(3) = SELT;
    __asm__ volatile("pushal\n\tcall C52B6A\n\tpopal" : : : "memory", "cc");
    *nat = (u8)D(0);
    *face = (u8)D(3) & 0x18;
    u32 i = 0;
    for (; i < 22 && NBUF[i]; i++) d[i] = (u8)NBUF[i];
    for (; i < 22; i++) d[i] = 0;
    R2S = s0; R2I = s1; R2K = s2;
    cpy(DREG, keep, 60);
    cpy(NBUF, nb, 23);
}

static const u8 TARGET[4] = { 3, 9, 10, 5 };          /* G D M A (oracle ROLE_TARGET) */
static const u8 GRP[8] = { 0, 1, 1, 1, 2, 2, 2, 3 };   /* position -> role */
static const u8 PICK[4][4] = { { 0, 0, 0, 0 }, { 1, 2, 3, 3 }, { 4, 5, 6, 6 }, { 7, 7, 7, 7 } };
static const u8 TIE[4] = { 2, 0, 1, 3 };               /* ties: M, G, D, A (the oracle's max by (gap, letter)) */

static void boy(u32 k, u32 h, u32 pos, u32 mean10) {
    u8 *r = T3_REC[k], nat, face;
    u32 s = h ^ SALT;
    zero(r, PL);
    name(xs(&s), r + 3, &nat, &face);
    u32 z = (xs(&s) & 0xFF) + (xs(&s) & 0xFF) + (xs(&s) & 0xFF) + (xs(&s) & 0xFF);   /* mean 510, sd 147.8 */
    s32 q10 = (s32)mean10 + ((s32)z - 510) * 35 / 148;
    s32 q = (q10 + 5) / 10;
    if (q10 < 0) q = 0;
    if (q > 49) q = 49;
    u32 lv = (u32)q / 3;
    if (lv > 15) lv = 15;
    u32 t = TPL[lv * 8 + pos], price = 0;
    if (pos) {
        u32 v = t | TPB[pos];
        r[0x1C] = (u8)(v >> 24); r[0x1D] = (u8)(v >> 16); r[0x1E] = (u8)(v >> 8); r[0x1F] = (u8)v;
        for (u32 i = 0; i < 7; i++, t >>= 4) price += t & 15;
    } else
        price = t & 0xFF;
    r[0] = nat;
    r[2] = 16;
    r[0x1A] = (u8)(pos << 5 | face | 4);
    r[0x20] = (u8)price;
    T3_AGE[k] = (u8)(17 + xs(&s) % 3);
}

static void label(u32 k) {
    char *d = T3_LBL[k];
    const u8 *r = T3_REC[k];
    const char *p = T3_POSN + 4 * (r[0x1A] >> 5);
    u32 i = 0;
    while (*p) d[i++] = *p++;
    d[i++] = ' ';
    d[i++] = (char)('0' + T3_AGE[k] / 10);
    d[i++] = (char)('0' + T3_AGE[k] % 10);
    d[i++] = ' ';
    for (u32 j = 0; j < 22 && r[3 + j]; j++) d[i++] = (char)r[3 + j];
    d[i++] = ' ';
    s32 g = (s32)r[0x20] - (s32)T3_OWN + 22;          /* + .. +++++ against the club's XI median: + = 19 or more */
    u32 st = g < 4 ? 1 : 1 + (u32)g / 4;               /* below it, one + more every 4, +++++ = 6 below or better */
    if (st > 5) st = 5;
    while (st--) d[i++] = '+';
    d[i] = 0;
}

static void msg(const char *s) { u32 i = 0; for (; s[i] && i < LW - 1; i++) T3_MSG[i] = s[i]; T3_MSG[i] = 0; }

void t3_list(void) {                    /* the page's state and its six boys (every open, and after a signing) */
    u32 code = t3_code();
    T3_CODE = code;
    T3_STATE = ISNAT ? 3 : T3_ITEM == code ? 1 : CNP >= MAXP ? 2 : 0;
    msg(T3_STATE == 0 ? T3_S_OPEN : T3_STATE == 2 ? T3_S_FULL : T3_S_DONE);
    s32 gap[4] = { 0, 0, 0, 0 };
    u32 n = CNP > MAXP ? MAXP : CNP, own = club_med();
    T3_OWN = own;
    for (u32 i = 0; i < n; i++) gap[GRP[rec(CMP[i])[0x1A] >> 5]]--;
    for (u32 g = 0; g < 4; g++) gap[g] += TARGET[g];
    u32 mean10 = 7 * own + 3 * div_med(own);
    mean10 = mean10 > 100 ? mean10 - 100 : 0;
    u8 pos[NB], taken[4] = { 0, 0, 0, 0 };
    u32 h0 = hmix(hmix(hmix(2166136261u, SELT), CSN), code);
    for (u32 k = 0; k < NB; k++) {
        u32 best = 4;
        for (u32 j = 0; j < 4; j++) {
            u32 g = TIE[j];
            if (taken[g] >= 3) continue;
            if (best == 4 || gap[g] > gap[best]) best = g;
        }
        gap[best]--;
        taken[best]++;
        u32 h = hmix(h0, k);
        pos[k] = PICK[best][(h >> 24) & 3];
    }
    for (u32 a = 1; a < NB; a++)        /* the page in the game's position order (G, the defence, ...) */
        for (u32 b = a; b && pos[b - 1] > pos[b]; b--) { u8 x = pos[b]; pos[b] = pos[b - 1]; pos[b - 1] = x; }
    for (u32 k = 0; k < NB; k++) {
        boy(k, hmix(hmix(h0, k), 0x59), pos[k], mean10);
        label(k);
    }
}

u32 t3_sign(u32 k) {                    /* fire on row k: 0 = signed, else the page's state (nothing done) */
    t3_list();
    if (T3_STATE || k >= NB) return T3_STATE ? T3_STATE : 4;
    u32 n = CNP, slot = 0;
    for (u32 i = 0; i < n; i++)         /* the lowest slot not in the squad order (cseg_56379's way) */
        if (CMP[i] == slot) { slot++; i = (u32)-1; }
    u8 keep[60];
    cpy(keep, DREG, 60);
    D(1) = slot;
    __asm__ volatile("pushal\n\tcall C63919\n\tpopal" : : : "memory", "cc");
    cpy(rec(slot), T3_REC[k], PL);
    u32 at = ((COMPFB[0] | COMPFB[1] << 8) == 2 ? (COMPFB[0x4D] | COMPFB[0x4E] << 8) : (COMPFB[0x65] | COMPFB[0x66] << 8)) + 11;
    if (at > n) at = n;
    for (u32 i = n; i > at; i--) CMP[i] = CMP[i - 1];
    CMP[at] = (u8)slot;
    A(0) = (u32)CT;
    D(1) = slot;
    __asm__ volatile("pushal\n\tcall SETBENCH\n\tpopal" : : : "memory", "cc");
    CNP = (u16)(n + 1);
    D(1) = slot;
    __asm__ volatile("pushal\n\tcall WAGE\n\tpopal" : : : "memory", "cc");
    cpy(DREG, keep, 60);
    T3_ITEM = (u8)T3_CODE;
    T3_SIGNED++;
    t3_list();
    return 0;
}

static u8 *ent(u32 k) {                 /* the shown menu's entry k (the game's own CalcMenuEntryAddress) */
    D(0) = k;
    __asm__ volatile("pushal\n\tcall CALC\n\tpopal" : : : "memory", "cc");
    return (u8 *)A(0);
}

void t3_minit(void) {                   /* onInit / after a signing: the rows hidden unless open; ESCI's up link */
    u32 open = T3_STATE == 0;
    for (u32 k = 0; k < NB; k++) {
        u8 *e = ent(2 + k);
        e[4] = !open; e[5] = 0;
    }
    ent(2 + NB)[10] = open ? 1 + NB : 0xFF;
}
