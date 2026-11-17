/* Knockout promotion / relegation play-offs of a career world's leagues (pack.json league 'ko_playoffs', kind
   'promotion'), decided at the season end from the final tables (tools/gplay.py; the European play-offs are
   uefaq's, the Italian ones dplay's).

   GP_IN.spec: the country's play-offs, each
     kind (1 promotion, 2 europe, 3 placement, 4 playout), n entrants, rounds, winner_div, loser_div (0xFE: the
     reserve, out of the league = division nd), flags,
     n x (type, div, a, b): type 0 = [div, place a], 1 = the best of div without Europe, 2 = the league cup winner;
     rounds x (ties, legs, host, level, pairing, gap) + 2 x ties member codes: 0..63 an entrant, 0x80|k the winner of
     tie k, 0xC0|k its loser (ties numbered across rounds); pairing p > 0 = the first p members best v worst, re-paired;
   gap g > 0: a tie whose clubs are g+ points apart is not played, the better placed goes through;
   a GROUP round (a round robin): (members m, 0x80 | meetings, host, 0, 0, 0) + m member codes + m start bonus points;
   its final placings are appended to the placings list (numbered across the group rounds), member code 0x40|k = the
   k-th placing; flags bits 4-7 = 'winners' (a promotion play-off ending with a group: its top w go to winner_div,
   the other winner_div clubs to loser_div; 0 = 1); ended by a 0.
   Only the promotion / playout play-offs whose entrants are all [div, place] are played here: promotion = the
   winner to winner_div, another winner_div entrant to loser_div; playout = the last round's losers to loser_div.
   4.0 package 6 ('title' / 'continental', world byte 0 and 5.0): kind 5 title = the champion is the last tie's
   winner (GP_OUT.res: team / global number), kind 6 continental = the continental places go to the last tie's winner
   and loser (the champion stays the table's 1st); entrant type 3 = place a of stage b's kept table (GP_IN.st[b],
   split's 'keep'), resolved to its row of division div's final table by the global number; host byte bit 7 =
   skip_if_same (a tie of one club with itself is not played: it goes through); levels 4 away_pens / 5 away_better
   (away goals are not simulated: as et_pens / better); member 0x3F = the best placed loser of the previous round.
   Entrant type 6 (4.0, Malta 2026-27) = seed a (1..4) of a split season's title decider (split_seed).
   4.2 (s3shape, the Serie B / C play-offs as data; the rules library's sr_gplay, rules-check identical): kind | 0x40 =
   an extension block (PO_EXT); levels 6 better_pts / 7 second; entrant type 9 = the Coppa Italia Serie C's place
   (cup_code: GP_CUPW / GP_CUPF, the winner / the other finalist). An extended play-off is played at the season end
   only (playable: no contest). */

#include "gpsc.h"                       /* (u8 / u16 / u32 / s8, SC_*, IS_MGR: shared with gplay3.c) */

enum { GT = 32, GD = 16, GN = 64, RESERVE = 0xFE, EXTERNAL = 0xFD };   /* (EXTERNAL, S7: gplay.py's) */   /* (GD: Italy 2026-27 has 14 divisions; GT: Argentina's 30) */
enum { HOST_LISTED, HOST_BETTER, HOST_DRAWN, HOST_NEUTRAL, HOST_UEFA_FINAL = 0x40, HOST_SKIP_SAME = 0x80 };
enum { LV_BETTER, LV_ET_PENS, LV_ET_BETTER, LV_PENS, LV_AWAY_PENS, LV_AWAY_BETTER,
       LV_BETTER_PTS, LV_SECOND };      /* (4.2 s3shape: the better placed unless level on points, then e.t. + penalties;
                                           the listed second - a seeded round's seed) */
enum { PO_EXT = 0x40 };                 /* (4.2 s3shape: kind | 0x40 - an extension block after the header: its length,
                                           then ops: 1 g direct (entrant 0 wins if g+ points ahead of entrant 1), 2 a
                                           level of groups' ranking, 3 k round k seeded, 4 k i j round k: the best of
                                           members i .. j-1 first) */
enum { E_DIRECT = 1, E_LEVEL, E_SEEDED, E_BEST };
static const u8 *ents_of(const u8 *s) { return s + 6 + (s[0] & PO_EXT ? 1 + s[6] : 0); }
/* 4.2 S3 glue (MC 14/11): the career-club path (playable / gap_done / gp_need / ko_build / build_game / rbyte) is shared with
   every shipped ko_playoffs country, so its S3 changes sit under GP_S3SKIP (the S3 builds: a pack with the Serie B play-off
   in ko_playoffs): KIND / ENTS expand to the old expressions otherwise, the other additions are compiled out - the
   non-S3 exes stay byte-identical to 42-int. */
#if GP_S3SKIP
#define KIND(s) ((s)[0] & 0x3F)
#define ENTS(s) ents_of(s)
#else
#define KIND(s) ((s)[0])
#define ENTS(s) ((s) + 6)
#endif
enum { K_TITLE = 5, K_CONT = 6, K_PROM = 7, K_STAGE = 8, GS = 2, BEST_LOSER = 0x3F };
enum { PO_SUPER = 4, PO_SKIP2 = 0x80 };                  /* (a play-off spec's flag, pack 'supercup': not played at the season end) */
enum { PO_DECIDER = 1 };                /* (4.2, Serie D Art. 51 c.6: flag bit 0 - 'skip_qualified' of the europe kind,
                                           uefaq's - on the other kinds 'decider': the last tie's winner takes the
                                           loser's better place in GP_IN.t, so the later play-offs read the new order) */
struct gp_row { u16 team, glob, won, gf, ga, pts; };
static void rcopy(struct gp_row *d, const struct gp_row *s) {   /* (no memcpy in the exe: field by field) */
    d->team = s->team; d->glob = s->glob; d->won = s->won; d->gf = s->gf; d->ga = s->ga; d->pts = s->pts;
}
enum { KT = 24, SD = 2, SDX = 9, GSD = 7, GSR = 20 };   /* SD: early tables in GP_ST; SDX: all (+ GP_GS) */
struct gp_in {
    u8 nd, pad[3];
    u8 n[GD], pad2[2];                  /* clubs per division (0 = not captured) */
    struct gp_row t[GD][GT];
    const u8 *spec;
    u8 nst[GS], pad3[2];                /* kept stage tables (split 'keep'), rows by place */
    struct gp_row st[GS][GT];
    /* the playable play-offs (gp_lend / gp_end) */
    u16 mgr, week;                      /* the career club's team word, the league's last week */
    u8 mdiv, gtype, pl_pi, pl_t2;       /* its division, g_gameType; gp_end: the played play-off (index + 1); a
                                           group contest's (the Poule): pl_w[0] / [1] = its champion / runner-up */
    u8 pi[2], sim[SDX];                 /* gp_need: the play-offs to play (spec index, 0xFF), divisions simulated early */
    u16 pl_w[KT];                       /* gp_end: the played play-off's tie winners (team words, 0 = not played) */
    u16 pl_fw, pl_fl;                   /* 4.2: its final's winner, loser (a title play-off's champion, runner-up) */
};
struct gp_mv { u16 glob, team; s8 delta; u8 pad[3]; };
struct gp_res { u8 kind, div; u16 team[2], glob[2]; };     /* title: [0] the champion; continental: winner, loser */
struct gp_out { u8 nmv, nres, pad[2]; struct gp_mv mv[32]; struct gp_res res[4];
                struct gp_res sres[3]; };   /* 4.0 ARG stage_title: [stage] champion, runner-up (0xFFFF: none) */
struct gp_in GP_IN;
struct gp_out GP_OUT;
struct gp_dec { u8 season, done, pad[2]; u16 team[2], glob[2]; };   /* 4.0 ARG: a stage title decided mid-season */
static const struct gp_dec *stage_dec(int k);   /* (GP_ST's, this season's, or 0: after GP_ST) */
enum { SS_N = 4, SS_BASE = 4 };      /* stage tables of a league with fixture stages (split 'table'): entrant
                                        'stage_place' s = SS_BASE + k (Argentina: 4 Apertura, 5 Clausura, 6 the
                                        annual table; 7 the MLS season, its own: GP_SS is the world's); saved with the career (engine item 'SS') */
struct gp_ss { u8 n[SS_N], fresh, key; struct gp_row r[SS_N][GT]; };   /* key (4.0.1): the bank's team file */   /* fresh: bit k = r[k] written this season */
static int ss_used;                     /* (a play-off read GP_SS this season end: fresh cleared after) */
#ifndef SS_NB
#define SS_NB 1
#endif
struct gp_ss GP_SSB[SS_NB > 1 ? SS_NB + 1 : 1];         /* 4.0.1: one bank per league with stage tables. Bank 0 = 4.0's single one
                                           (Argentina r[0..2], MLS r[3]: engine item 'SS', unchanged for 4.0 saves);
                                           bank 1 = the CAREER club's league when it is another one (item 'SS2': its
                                           tables must survive a mid-season save); 2.. the other leagues', not saved
                                           (they play at the season end's simulation). GP_SSF[team file] = 1.. */
static struct gp_ss *SSB = &GP_SSB[0];
#if SS_NB > 1
extern const u8 GP_SSF[256];
extern const u16 GP_CAREERW;            /* (selTeamNumber: the career club's team word) */
static void ss_set(u32 file) {
    u32 b = GP_SSF[file & 255];
    file &= 255;
    if (!b || b >= SS_NB) { SSB = &GP_SSB[0]; return; }
    SSB = &GP_SSB[(GP_CAREERW & 255) == file ? 1 : 1 + b];
    if (SSB->key != file) {                     /* (a new league in this bank: e.g. the career club moved) */
        SSB->key = (u8)file;
        SSB->fresh = 0;
        for (int q = 0; q < SS_N; q++) SSB->n[q] = 0;
    }
}
static const struct gp_ss *ss_view(u32 file) {  /* (4.0.1, the WINNERS page: league file's bank, read only - ss_set
                                                    would reset a bank holding another league; 0: none this season) */
    u32 b = GP_SSF[file & 255];
    file &= 255;
    if (!b || b >= SS_NB) return &GP_SSB[0];
    const struct gp_ss *x = &GP_SSB[(GP_CAREERW & 255) == file ? 1 : 1 + b];
    return x->key == file ? x : 0;
}
#else
static void ss_set(u32 file) { (void)file; }
static const struct gp_ss *ss_view(u32 file) { (void)file; return &GP_SSB[0]; }
#endif
const u32 GP_LAYOUT[] = { sizeof(struct gp_row), GT, __builtin_offsetof(struct gp_in, n),
                          __builtin_offsetof(struct gp_in, t), __builtin_offsetof(struct gp_in, spec),
                          __builtin_offsetof(struct gp_out, mv), sizeof(struct gp_mv), GD,
                          __builtin_offsetof(struct gp_in, nst), __builtin_offsetof(struct gp_in, st), GS,
                          __builtin_offsetof(struct gp_out, nres), __builtin_offsetof(struct gp_out, res),
                          sizeof(struct gp_res) };

#if GP_X3
#define GP_X3S                          /* (4.2 X3: gplay3.c in obj3 calls it) */
#else
#define GP_X3S static
#endif
GP_X3S u32 rng;
GP_X3S u32 below(u32 n) {
    rng = rng * 1103515245u + 12345u;
    return ((rng >> 16) * n) >> 16;
}

#define DV(c) ((c) / GT)
#define PL(c) ((c) % GT)
static const struct gp_row *row(int c) { return &GP_IN.t[DV(c)][PL(c)]; }

static int by_rec;                      /* spec flag 2 'host_by_record' (4.0 MLS): in one division the better record */
static int x_lvl, x_direct, x_sdiv, x_sfrom;    /* (4.2 s3shape, gp_season's extended play-off: a level of groups, its
                                                   direct gap; the cup place's scroll: division, first place) */
static u32 x_seeded, x_lot0;
static const u8 *x_b, *x_e;
static u8 x_lot(int c) { return (u8)((row(c)->glob * 2654435761u + x_lot0) >> 24); }
static int better(int a, int b) {       /* the higher tier, then the better place */
    if (DV(a) != DV(b) && x_lvl) {      /* (4.2: a level of groups - the place, then points, wins, goals, the lot:
                                           dplay.c dp_better) */
        const struct gp_row *x = row(a), *y = row(b);
        if (PL(a) != PL(b)) return PL(a) < PL(b);
        if (x->pts != y->pts) return x->pts > y->pts;
        if (x->won != y->won) return x->won > y->won;
        if (x->gf != y->gf) return x->gf > y->gf;
        return x_lot(a) < x_lot(b);
    }
    if (DV(a) != DV(b)) return DV(a) < DV(b);
    if (by_rec) {                       /* (points, wins, goal difference, goals: MLS; then the place) */
        const struct gp_row *x = row(a), *y = row(b);
        int dx = x->gf - x->ga, dy = y->gf - y->ga;
        if (x->pts != y->pts) return x->pts > y->pts;
        if (x->won != y->won) return x->won > y->won;
        if (dx != dy) return dx > dy;
        if (x->gf != y->gf) return x->gf > y->gf;
    }
    return PL(a) < PL(b);
}

/* 4.2 S1.3, the FIGC C.U. 244/A exception (iv): a play-off match is not played when one of its clubs is already in a
   UEFA competition's final - round host bit 0x40 (pack "skip_if_uefa_finalist"; the rules library's sr_season
   .uefa_final). The game plays one UEFA cup, the career club's: its finalists are the winners of the last stage uesum's
   US_REC kept this season (GP_USRP, 1 without uesum; struct cup: u8 id, n[4], ss, ties of 8 B at +6: u16 x, y, .., u8
   fl - 0x80 played, 1 y went through) when that stage is the semi-finals (2 ties). */
const u8 *GP_USRP = (const u8 *)1;      /* (1: none - not in .bss; patch.py: gplay.link_usrec after uesum) */
extern const u8 GP_SEASP;               /* seasonPlaying (US_REC's stamp - 1) */
#if GP_UEFAFORCE >= 2
/* (test builds, GPLAY_UEFAF=2 - H6 M2: a probe, US_REC left to uesum: what the last uefa_fin read - US_REC's stamp, the
   stamp it wants, the last stage's tie count, the semi-finals' winners (0 none), the clubs asked, the answer.
   GPLAY_UEFAF=3: the same, and before the read uesum's own record forced - this season's semi-finals (stamp and stages
   kept) with the career club the 1st tie's winner, unless it already won one; frc = 1 forced, 2 already a winner) */
struct { u32 tag; u8 calls, ss, want, nst; u16 w[2], ta, tb; u8 res, frc, pad[2]; } GP_UFPB = { 0x42504655 };   /* 'UFPB' */
static int uefa_fin1(u16 ta, u16 tb);
static int uefa_fin(u16 ta, u16 tb) {
    const u8 *c = GP_USRP;
    int s = 3, off = 0;
#if GP_UEFAFORCE == 3
    if (c != (const u8 *)1 && c && c[5] == (u8)(GP_SEASP + 1)) {
        u8 *u = (u8 *)c;
        int z = 3, o = 0;
        while (z >= 0 && !u[1 + z]) z--;
        if (z >= 0 && u[1 + z] == 2) {
            for (int k = 0; k < z; k++) o += u[1 + k];
            if (o + 1 < 22) {
                u8 *t0 = u + 6 + 8 * o, *t1 = t0 + 8;
                u16 mgr = GP_IN.mgr, w1 = t1[7] & 1 ? *(u16 *)(t1 + 2) : *(u16 *)t1;
                if ((t1[7] & 0x80) && w1 == mgr) GP_UFPB.frc = 2;
                else if (*(u16 *)(t0 + 2) == mgr) { t0[7] |= 0x81; GP_UFPB.frc = 1; }
                else { *(u16 *)t0 = mgr; t0[7] = (u8)((t0[7] & ~1) | 0x80); GP_UFPB.frc = 1; }
            }
        }
    }
#endif
    int r = uefa_fin1(ta, tb);
    GP_UFPB.calls++;
    GP_UFPB.want = (u8)(GP_SEASP + 1);
    GP_UFPB.ta = ta; GP_UFPB.tb = tb; GP_UFPB.res = (u8)r;
    GP_UFPB.ss = GP_UFPB.nst = 0; GP_UFPB.w[0] = GP_UFPB.w[1] = 0;
    if (c == (const u8 *)1 || !c) return r;
    GP_UFPB.ss = c[5];
    while (s >= 0 && !c[1 + s]) s--;
    if (s < 0) return r;
    GP_UFPB.nst = c[1 + s];
    for (int k = 0; k < s; k++) off += c[1 + k];
    for (int i = 0; i < 2 && i < c[1 + s] && off + i < 22; i++) {
        const u8 *t = c + 6 + 8 * (off + i);
        if (t[7] & 0x80) GP_UFPB.w[i] = t[7] & 1 ? *(const u16 *)(t + 2) : *(const u16 *)t;
    }
    return r;
}
static int uefa_fin1(u16 ta, u16 tb) {
#else
static int uefa_fin(u16 ta, u16 tb) {
#endif
    const u8 *c = GP_USRP;
    int s = 3, off = 0;
#if GP_UEFAFORCE == 1
    if (c != (const u8 *)1 && c) {      /* (test builds, GPLAY_UEFAF=1: US_REC written as if the career club had won
                                           this season's semi-final - the record the read below takes) */
        u8 *w = (u8 *)c;
        w[1] = w[2] = w[3] = 0; w[4] = 2; w[5] = (u8)(GP_SEASP + 1);
        *(u16 *)(w + 6) = GP_IN.mgr; *(u16 *)(w + 8) = 0xFFFE; w[13] = 0x80;
        *(u16 *)(w + 14) = 0xFFFD; *(u16 *)(w + 16) = 0xFFFC; w[21] = 0x81;
    }
#endif
    if (c == (const u8 *)1 || !c || c[5] != (u8)(GP_SEASP + 1)) return 0;
    while (s >= 0 && !c[1 + s]) s--;
    if (s < 0 || c[1 + s] != 2) return 0;
    for (int k = 0; k < s; k++) off += c[1 + k];
    for (int i = 0; i < 2 && off + i < 22; i++) {
        const u8 *t = c + 6 + 8 * (off + i);
        u16 w = t[7] & 1 ? *(const u16 *)(t + 2) : *(const u16 *)t;
        if ((t[7] & 0x80) && (w == ta || w == tb)) return 1;
    }
    return 0;
}

static u32 str2(int c, int home) {      /* strength: the place in its division, the tier */
    int n = GP_IN.n[DV(c)];
    int s = 30 + 40 * (n - PL(c)) / (n ? n : 1) - 25 * DV(c);
    if (s < 5) s = 5;
    if (home) s = s * 11 / 10;
    return (u32)(s * s);
}

/* a tie: a = the single match's host / the first leg's home club (listed order), b = the other */
static int tie(int a, int b, int legs, int host, int level) {
    int h = a, o = b, w;
    if (host == HOST_BETTER || host == HOST_NEUTRAL) {      /* the better placed hosts the single match / return */
        if (better(b, a)) { h = b; o = a; }
        else { h = a; o = b; }
        if (legs == 2 || host == HOST_NEUTRAL) { int x = h; h = o; o = x; }   /* (h = the first leg's / listed) */
    } else if (host == HOST_DRAWN && below(2)) { h = b; o = a; }
    /* the club with home advantage: a single match's host, the return leg's home club */
    int adv = (legs == 1) ? (host == HOST_NEUTRAL ? -1 : h) : o;
    u32 sh = str2(h, adv == h), so = str2(o, adv == o);
    if (below(100) < (legs == 1 ? 22u : 12u)) {             /* level after the regulation time */
        int bp = better(h, o) ? h : o;
        if (level == LV_BETTER || level == LV_ET_BETTER || level == LV_AWAY_BETTER) return bp;
        if (level == LV_SECOND) return b;
        if (level == LV_BETTER_PTS && row(h)->pts != row(o)->pts) return bp;
        u32 x = str2(h, 0), y = str2(o, 0);                   /* e.t. + penalties: close to a coin toss */
        sh = 2 * x + y; so = x + 2 * y;
    }
    w = below(sh + so) < sh ? h : o;
    return w;
}

static int series(int a, int b, int level) {   /* best of three: games 1 and 3 at the better placed's */
    int h = better(a, b) ? a : b, o = h == a ? b : a, wh = 0, wo = 0;
    for (int g = 0; g < 3 && wh < 2 && wo < 2; g++)
        if (tie(g == 1 ? o : h, g == 1 ? h : o, 1, HOST_LISTED, level) == h) wh++; else wo++;
    return wh == 2 ? h : o;
}

#ifndef GP_FORCE
#define GP_FORCE 0
#endif
#ifndef GP_GOUT
#define GP_GOUT 0
#endif
#ifndef GP_GFFORCE
#define GP_GFFORCE 0                    /* (test builds, GPLAY_GFFORCE: 1 the career club kept out of a Grand Final,
                                           2 the career club its host) */
#endif
#ifndef GP_KOFORCE
#define GP_KOFORCE 0                    /* (test builds, GPLAY_KOFORCE: 1 the career club loses its played knockout ties,
                                           2 wins them - gp_perm_c / gp_rec_c, the game told so through the next round) */
#endif
#if GP_KOFORCE                          /* (4.0.5: gp_season compiled for size in KOFORCE builds only - their forcing code */
#define GP_KOSIZE __attribute__((minsize))  /* left longtable no room in gplay's pages; a release build is unchanged) */
#else
#define GP_KOSIZE
#endif
/* test builds (GPLAY_FORCE=k): the career club takes place k of its division (team and global number swapped with
   the club there), at the league end and again at the season end */
static int gp_force(void) {
    if (!GP_FORCE || !GP_IN.mgr) return -1;
    for (int s = 0; s < SS_N; s++)              /* (a stage table written this season: the same place there) */
        if (SSB->fresh & 1 << s && GP_FORCE <= SSB->n[s])
            for (int k = 0; k < SSB->n[s]; k++)
                if (SSB->r[s][k].team == GP_IN.mgr && k != GP_FORCE - 1) {
                    struct gp_row x, *r = SSB->r[s];
                    rcopy(&x, &r[k]); rcopy(&r[k], &r[GP_FORCE - 1]); rcopy(&r[GP_FORCE - 1], &x);
                    break;
                }
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++)
            if (GP_IN.t[d][k].team == GP_IN.mgr && GP_FORCE <= GP_IN.n[d]) {
                struct gp_row *t = GP_IN.t[d], x = t[k];
                t[k].team = t[GP_FORCE - 1].team; t[k].glob = t[GP_FORCE - 1].glob;
                t[GP_FORCE - 1].team = x.team; t[GP_FORCE - 1].glob = x.glob;
                return GP_FORCE - 1;
            }
    return -1;
}

static void move(int c, int delta) {
    if (!delta || GP_OUT.nmv >= 32) return;
    struct gp_mv *m = &GP_OUT.mv[GP_OUT.nmv++];
    m->glob = row(c)->glob; m->team = row(c)->team; m->delta = delta;
}

/* S7 glue (MC 12/11, mc-s7-glue.md §3.5): a play-off destination in the OTHER league struct (Italy: Serie C's
   play-out losers -> file 144's Serie D, the Serie D title winner -> file 102's Serie C) is compiled as EXTERNAL
   (gplay.py, mkseason Pack.po_local). The game moves nobody across structs: the club stays where it is (no GP_OUT
   move) and is listed here - entry, outcome, its global number - for the season-end swap builder, which reads the
   entry's target division_key from mkseason's ko_external table (the one place of that policy). Not in GP_OUT
   (its layout is the season-end log's, GP_LOG). The preview (GP_PRE) lists nothing. Dormant: no EXTERNAL byte in
   any spec, n stays 0. Full (8): the last ones lost - the builder refuses that season by its
   flag (GP_EXT.full), never a guess. */
#if GP_S7
enum { GP_EXT_N = 8, EXT_WINNER = 0, EXT_LOSER = 1 };
struct gp_ext { u8 n, full, pad[2]; struct { u16 glob, team; u8 pidx, outcome, pad[2]; } e[GP_EXT_N]; };
struct gp_ext GP_EXT;

extern u8 GP_PRE;                       /* (the preview flag, defined below) */
static void dest(int c, int to, int pidx, int outcome) {
    if (to != EXTERNAL) {
        move(c, to - DV(c));
        return;
    }
    if (GP_PRE) return;
    if (GP_EXT.n >= GP_EXT_N) { GP_EXT.full = 1; return; }
    GP_EXT.e[GP_EXT.n].glob = row(c)->glob; GP_EXT.e[GP_EXT.n].team = row(c)->team;
    GP_EXT.e[GP_EXT.n].pidx = (u8)pidx; GP_EXT.e[GP_EXT.n].outcome = (u8)outcome;
    GP_EXT.n++;
}

/* S7 snapshot (Shaved 13/11, s7-swap-plan.md piece 1; MC's Q2): GP_IN and GP_EXT are one country's, so at the end of
   each league struct's gp_season its crossings are copied into S7X[its file's index] for the season-end swap builder
   (obj4 s7swap.c, in pg_fix before InitializeNewSeason): the DIRECT ones - a division's original 'promoted' /
   'relegated' count that B1 zeroed in the struct records (mkseason Pack.s7_direct -> S7_DIR {file, local division,
   up 1 / down 0, count}), taken from its final table (GP_IN.t, after the play-offs' deciders) - then the play-out
   ones (GP_EXT, its order). dir: the struct's side of the boundary (S7_FA = the upper struct's file: its clubs go
   down). bad: a division not captured, a short table or GP_EXT.full - the builder refuses the season, never guesses.
   season: GP_SEASP's stamp (the builder takes only this season's two snapshots). */
#ifndef GP_DATA_SECTION
#if defined(__MACH__)                   /* (a native host build - mach-o has no ".data" section name; the exe is always ELF) */
#define GP_DATA_SECTION
#else
#define GP_DATA_SECTION __attribute__((section(".data")))      /* (host tests build gplay.c natively: -DGP_DATA_SECTION=) */
#endif
#endif
struct s7x { u16 file; u8 n, bad, season, pad[3]; struct { u16 glob, team; u8 kind, dir, div, rank; } e[24]; };
struct s7x S7X[2];                      /* (written by s7swap.c s7_snap, read by its s7_season) */
void (*GP_S7SNAP)(const struct gp_in *in, const struct gp_ext *ext, u32 pre, u32 seasp) GP_DATA_SECTION;   /* (s7swap.py:
                                           -> obj4 s7_snap - MC ruling (b) 13/11: the S7-only code out of obj1) */
_Static_assert(__builtin_offsetof(struct gp_in, t) == 22 && sizeof(struct gp_row) == 12 && GD == 16 && GT == 32,
               "s7swap.c s7_in: gp_in's head as gplay.c has it");
#else
#define dest(c, to, pidx, outcome) move((c), (to) - DV(c))   /* (dormant: the game's own move) */
#endif

static int sbetter_cmp(int a, int b) { return better(a, b); }

static u16 dsw[16];                     /* (4.2 'decider': the preview's row swaps, undone at its end) */
static int ndsw;
static void dswap(int a, int b) {       /* rows a, b of one division: their places exchanged */
    struct gp_row x, *ra = &GP_IN.t[DV(a)][PL(a)], *rb = &GP_IN.t[DV(b)][PL(b)];
    rcopy(&x, ra); rcopy(ra, rb); rcopy(rb, &x);
}

static u32 ch_low, po_low;              /* 4.2 (Jacopo's TERMOLI, Davide 11/11): a title play-off with no entrant from
                                           the top division (Italy's POULE SCUDETTO SERIE D) is a lower tier's title -
                                           po_low while it is decided, ch_low bit k = GP_OUT.res[k]: gp_champ leaves it
                                           out of the qualifiers' top-9 list (Europe from the top flight only) */
static void result(int kind, int w, int l) {
    if (GP_OUT.nres >= 4) return;
    if (kind == K_TITLE && po_low) ch_low |= 1u << GP_OUT.nres;
    struct gp_res *x = &GP_OUT.res[GP_OUT.nres++];
    x->kind = kind; x->div = DV(w);
    x->team[0] = row(w)->team; x->glob[0] = row(w)->glob;
    x->team[1] = l >= 0 ? row(l)->team : 0xFFFF; x->glob[1] = l >= 0 ? row(l)->glob : 0xFFFF;
}

static int stage_club(int d, int s, int a) {   /* place a of kept stage s -> its row of division d, or -1 */
    u16 g;
    if (s >= SS_BASE && s < SS_BASE + SS_N) {
        int k = s - SS_BASE;
        ss_used = 1;
        if (!(SSB->fresh & 1 << k)) {          /* (not written this season: a simulated league skips split's stage
                                                   end -> the division's final table, its places as the stage's) */
            if (d >= GP_IN.nd || a < 1 || a > GP_IN.n[d]) return -1;
            return d * GT + a - 1;
        }
        if (a < 1 || a > SSB->n[k] || d >= GP_IN.nd) return -1;
        g = SSB->r[k][a - 1].glob;
    } else {
        if (s >= GS || a < 1 || a > GP_IN.nst[s] || d >= GP_IN.nd) return -1;
        g = GP_IN.st[s][a - 1].glob;
    }
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int glob_club(int d, u16 g) {     /* a global number -> its row of division d, or -1 */
    if (g == 0xFFFF || d >= GP_IN.nd) return -1;
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int mgr_div(void) {              /* the career club's division in GP_IN (this country's), or -1 */
    if (!GP_IN.mgr) return -1;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].team == GP_IN.mgr) return d;
    return -1;
}
static struct gp_res SRL[3];            /* 4.0.1 MEX: another division's stage titles (GP_OUT.sres: the career club's
                                           division's; a league's divisions each with stages 0..2 - stage_title's byte
                                           = stage | division << 2) */
static int srl_div = -1;
static struct gp_res *sres_of(int d) {
    if (d == mgr_div() || (mgr_div() < 0 && d == 0)) return GP_OUT.sres;
    if (srl_div != d) {
        for (int k = 0; k < 3; k++) {
            SRL[k].kind = 0;
            SRL[k].team[0] = SRL[k].team[1] = SRL[k].glob[0] = SRL[k].glob[1] = 0xFFFF;
        }
        srl_div = d;
    }
    return SRL;
}
static u16 stage_glob(int d, int k, int j) {   /* division d's stage k champion (j 0) / runner-up (1): decided this
                                           season (dec: the Trofeo built mid-season), else this gp_season pass's */
    const struct gp_dec *x = stage_dec(k | d << 2);
    return x ? x->glob[j] : sres_of(d)[k].glob[j];
}

static int title_club(int d, int c) {   /* entrant type 5 (the Trofeo): 1 the 1st stage's champion; 2 / 3 the 2nd
                                           stage's champion, or (the same club won both) the 1st's / 2nd's runner-up */
    u16 c0 = stage_glob(d, 0, 0), c1 = stage_glob(d, 1, 0);
    if (c == 1) return glob_club(d, c0);
    if (c0 != c1 || c == 4) return glob_club(d, c1);   /* (4: the 2nd stage's champion always - MEX) */
    return glob_club(d, stage_glob(d, c - 2, 1));
}

static int kept_pts(int s, int c) {    /* club c's points in kept stage s (0: not in it) */
    u16 g = row(c)->glob;
    if (s >= GS) return 0;
    for (int k = 0; k < GP_IN.nst[s]; k++) if (GP_IN.st[s][k].glob == g) return GP_IN.st[s][k].pts;
    return 0;
}

static int agg_better(int s, int a, int b) {   /* the two rounds' points together, then the final table's place */
    int x = kept_pts(s, a) + row(a)->pts, y = kept_pts(s, b) + row(b)->pts;
    return x != y ? x > y : PL(a) < PL(b);
}

/* entrant type 6 (Malta 2026-27, MFA competition rules): seed a (1..4) of the title decider of division d, from kept
   stage s (the Opening Round, its 1st / 2nd O1 / O2) and the final table (the Closing Round: C1 / C2), for a bracket
   1v4, 2v3, then the final, every tie skip_if_same: one club won both rounds -> 4 x O1 (no match: champion); O1 / C1
   1st and 2nd in reverse order, or one club 2nd in both (it is the runner-up, out of the decider) -> the Finalissima
   O1 v C1 (seeds A A B B, A the better by aggregate points); three clubs -> the one 1st in a round and 2nd in the
   other straight to the final (seeds 1 and 4), the other two play for its other place (a club 2nd in both: 3rd, the
   Finalissima as above); four clubs -> the Final Four seeded by the season's points (the Opening's kept table, Top 6
   included, + the Closing's). Equal points: the Closing table's place (the rules' direct encounters need every
   pair's results over both rounds, which no table keeps; the Top-6 / league-phase rule is the rules' classification
   of 2nd-4th when one club won both, not a seeding) */
static int split_seed(int d, int s, int a) {
    if (d >= GP_IN.nd || GP_IN.n[d] < 2 || a < 1 || a > 4) return -1;
    int o1 = stage_club(d, s, 1), o2 = stage_club(d, s, 2), c1 = d * GT, c2 = d * GT + 1;
    if (o1 < 0 || o2 < 0) return -1;
    if (o1 == c1) return o1;
    if (o2 == c2 || (o1 == c2 && o2 == c1)) {
        int x = agg_better(s, o1, c1) ? o1 : c1, y = x == o1 ? c1 : o1;
        return a == 1 || a == 4 ? x : y;
    }
    int x = o1 == c2 ? o1 : c1 == o2 ? c1 : -1;
    if (x >= 0) {
        int y = x == o1 ? c1 : o1, z = x == o1 ? o2 : c2;
        if (agg_better(s, z, y)) { int t = y; y = z; z = t; }
        return a == 1 || a == 4 ? x : a == 2 ? y : z;
    }
    int q[4] = { o1, c1, o2, c2 };
    for (int i = 1; i < 4; i++)
        for (int j = i; j > 0 && agg_better(s, q[j], q[j - 1]); j--) { int t = q[j]; q[j] = q[j - 1]; q[j - 1] = t; }
    return q[a - 1];
}

/* entrant type 7 (4.0.1, package 6): seed a of a national title play-off between the tournament winners and the
   annual table (GP_SS: A = stage_place 4's 1st, C = the closing tournament's (rule 1: stage_place 7, Uruguay's
   Clausura in table 3; rule 2: stage_place 5), T = stage_place 6, the annual / accumulated table).
   Rule 1, Uruguay (AUF): SF A v C, the final v T's 1st; seeds 1 A, 2 C, 3 T1 - or A when A won both tournaments
   (then both ties are of A with itself: champion at once, as the rules say).
   Rule 2, Peru (Liga1 2026): the winners (each only if in T's top 8) and T's top 2 other than the winners; a winner in
   T's top 2 waits in the final; seeds for SF [[1, 4], [2, 3]], F [W0, W1], every tie skip_if_same: A = C -> all A
   (champion); both winners in the top 2 -> 1 = 4 = A, 2 = 3 = C (the final only); one, X -> 1 = 4 = X, 2 / 3 = the
   other winner and the other top-2 club; else four clubs by T's places, best v lowest, 2nd v 3rd. */
static int t_place(int d, int c) {             /* club c's place in T (stage_place 6), 0 = not found */
    for (int p = 1; d < GP_IN.nd && p <= GP_IN.n[d]; p++) if (stage_club(d, 6, p) == c) return p;
    return 0;
}
static int title_seed(int d, int rule, int a) {
    if (d >= GP_IN.nd || GP_IN.n[d] < 4 || a < 1 || a > 4) return -1;
    int A = stage_club(d, 4, 1), C = stage_club(d, rule == 1 ? 7 : 5, 1), t1 = stage_club(d, 6, 1);
    if (A < 0 || C < 0 || t1 < 0) return -1;
    if (A == C) return A;
    if (rule == 1) return a == 1 ? A : a == 2 ? C : t1;
    int pa = t_place(d, A), pc = t_place(d, C), q[4], nq = 0;
    if (pa && pa <= 2 && pc && pc <= 2) return a == 1 || a == 4 ? A : C;
    if (pa > 0 && pa <= 8) q[nq++] = A;        /* (a winner outside T's top 8 does not qualify: its place goes to */
    if (pc > 0 && pc <= 8) q[nq++] = C;        /*  the next club of T - declared, the bases do not say) */
    for (int p = 1; nq < 4 && p <= GP_IN.n[d]; p++) {
        int c = stage_club(d, 6, p);
        if (c >= 0 && c != A && c != C) q[nq++] = c;
    }
    if (nq < 4) return -1;
    int x = pa && pa <= 2 ? A : pc && pc <= 2 ? C : -1;
    if (x >= 0) {                               /* one winner in the top 2: it waits in the final */
        int y = -1, z = -1;
        for (int i = 0; i < 4; i++) {           /* y: the other qualified winner (or the next club of T), z: the */
            if (q[i] == x) continue;            /*  best other club of T */
            if ((q[i] == A || q[i] == C) && y < 0) y = q[i];
        }
        for (int i = 0; i < 4; i++) if (q[i] != x && q[i] != y && (z < 0 || t_place(d, q[i]) < t_place(d, z))) z = q[i];
        if (y < 0) {                            /* (the other winner outside the top 8: the next two of T) */
            for (int i = 0; i < 4; i++) if (q[i] != x && q[i] != z) { y = q[i]; break; }
        }
        return a == 1 || a == 4 ? x : a == 2 ? y : z;
    }
    for (int i = 1; i < 4; i++)                 /* four clubs by T's places */
        for (int j = i; j > 0 && t_place(d, q[j]) < t_place(d, q[j - 1]); j--) { int t = q[j]; q[j] = q[j - 1]; q[j - 1] = t; }
    return q[a == 1 ? 0 : a == 4 ? 3 : a == 2 ? 1 : 2];
}

/* a group match: goals by strength (draws ~ 1 in 4), home advantage unless neutral */
static void gmatch(int h, int a, int neutral, int *gh, int *ga) {
    u32 sh = str2(h, !neutral), sa = str2(a, 0);
    if (below(100) < 26) { int g = below(3); *gh = g; *ga = g; return; }
    int w = below(sh + sa) < sh, gw = 1 + below(3), gl = below(gw);
    *gh = w ? gw : gl; *ga = w ? gl : gw;
}

struct gs { int c, pts, gd, gf; };
static int gs_before(const struct gs *x, const struct gs *y) {   /* points, goal difference, goals, the better place */
    if (x->pts != y->pts) return x->pts > y->pts;
    if (x->gd != y->gd) return x->gd > y->gd;
    if (x->gf != y->gf) return x->gf > y->gf;
    return better(x->c, y->c);
}

/* a group round: mem[0..m) round robin `meet` times (home and away alternate), start bonus points; placings -> out,
   their figures -> outs. meet 0 = a ranking round (pack 'best_of'): the members, earlier placings, ranked by the
   figures of their own groups (ins) */
static void group(const int *mem, int m, int meet, int neutral, const u8 *bonus, int *out, const struct gs *ins,
                  struct gs *outs) {
    struct gs t[GT];                    /* (at most 24 members: compile_spec)  */
    for (int i = 0; i < m; i++) {
        t[i].c = mem[i]; t[i].pts = bonus[i]; t[i].gd = 0; t[i].gf = 0;
        if (!meet) { t[i].pts = ins[i].pts; t[i].gd = ins[i].gd; t[i].gf = ins[i].gf; }
    }
    for (int k = 0; k < meet; k++)
        for (int i = 0; i < m; i++)
            for (int j = i + 1; j < m; j++) {
                int h = (k & 1) ? j : i, a = (k & 1) ? i : j, gh, ga;
                gmatch(t[h].c, t[a].c, neutral, &gh, &ga);
                t[h].gf += gh; t[a].gf += ga; t[h].gd += gh - ga; t[a].gd += ga - gh;
                if (gh > ga) t[h].pts += 3; else if (gh < ga) t[a].pts += 3; else { t[h].pts++; t[a].pts++; }
            }
    for (int i = 1; i < m; i++) {
        struct gs x = t[i]; int j = i;
        while (j > 0 && gs_before(&x, &t[j - 1])) { t[j] = t[j - 1]; j--; }
        t[j] = x;
    }
    for (int i = 0; i < m; i++) { out[i] = t[i].c; outs[i] = t[i]; }
}

static struct gs PS[GN], ms[GT];       /* (gp_season: the placings' figures; a round's members' (static: the stack)) */

/* split's kept stage table (gp_cap, every captured division; split.py's freeze sets the 'kept' byte at ST+5 when a
   'keep' stage froze the table before it: rows by place at S_KEEP, their points at S_KEEP+22): into GP_IN.st[k] in the
   order the season end captures them (k = 0 again at each country's division 0). diy = DIY, st = split.ST, keep =
   S_KEEP - ST, sel = the team cache (a row's team dword is an offset into it: +2 the global number). */
static u8 gp_kn;
u8 *GP_SHB[2];   /* 4.0.1 (split.py sp_shsel): [0] 'SH' (key: team file, division | 80h; then the career league's
                    head-to-head / 'keep' block), [1] the scratch block of any other league - the 'keep' table left the
                    DIY */
void gp_keep(const u8 *diy, u32 st, u32 keep, const u8 *sel, u32 div, u32 magic) {
    if (div == 0) {
        gp_kn = 0;
        for (int i = 0; i < GS; i++) GP_IN.nst[i] = 0;
    }
    const u8 *sh = GP_SHB[0], *s = diy + st, *k;  /* keep 0: CFB, the career league's own block; 1: DIY, the career
                                                     league's block when its key is this league's, else the scratch */
    if (!sh || !GP_SHB[1]) return;
    k = keep == 0 || (sh[0] == diy[0x12D] && sh[1] == (0x80 | div)) ? sh + 2 : GP_SHB[1];
    int n = diy[0x31] | diy[0x32] << 8;
    if ((u32)(s[0] | s[1] << 8) != magic || s[5] != 1 || gp_kn >= GS || n < 2 || n > GT || n > 21) return;
    u32 seen = 0;
    for (int i = 0; i < n; i++) {
        if (k[i] >= n || seen & 1u << k[i]) return;
        seen |= 1u << k[i];
    }
    struct gp_row *o = GP_IN.st[gp_kn];
    for (int i = 0; i < n; i++) {
        int r = k[i];
        const u8 *row = diy + 0x2B3 + 18 * r;
        u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
        o[i].team = diy[0x12D + 2 * r] | diy[0x12E + 2 * r] << 8;
        o[i].glob = sel[t + 2] | sel[t + 3] << 8;
        o[i].won = o[i].gf = o[i].ga = 0;
        o[i].pts = k[22 + 2 * i] | k[23 + 2 * i] << 8;
    }
    GP_IN.nst[gp_kn++] = n;
}

/* 4.0 overall tables (longtable.py, STAT > CLASSIFICA GENERALE; display only): the table's rows in GP_OV_ROWS (the
   DIY row layout: +0 team, +4 played, won, drawn, lost, for, against, points) and their order in GP_OV_ORD (row
   offsets, best first: points, wins, goal difference, goals). Argentina's annual table: when the Apertura's kept table
   (GP_SS 0, written this season) holds every club of this one, its figures are added by club (played = apn, the
   Apertura's match days; drawn from its points). The MLS's Supporters' Shield: the live table, re-sorted. */
u16 GP_OV_ORD[32];
u8 GP_OV_ROWS[32 * 18];
u32 GP_OV_N, GP_OV_ANNUAL;
static u16 w16(const u8 *b) { return b[0] | b[1] << 8; }
static void p16(u8 *b, u32 v) { b[0] = v; b[1] = v >> 8; }
void gp_overall(const u8 *diy, const u8 *sel, u32 apn) {
    int n = w16(diy + 0x31);
    ss_set(diy[0x12D]);
    if (n < 1 || n > 32) { GP_OV_N = 0; return; }
    for (int i = 0; i < n * 18; i++) GP_OV_ROWS[i] = diy[0x2B3 + i];
    int found = 0;
    if (apn && (SSB->fresh & 1) && SSB->n[0] == n) {
        for (int r = 0; r < n; r++) {
            u8 *row = GP_OV_ROWS + 18 * r;
            u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
            u16 g = w16(sel + t + 2);
            for (int k = 0; k < n; k++) if (SSB->r[0][k].glob == g) { found++; break; }
        }
    }
    GP_OV_ANNUAL = found == n;
    if (GP_OV_ANNUAL)
        for (int r = 0; r < n; r++) {
            u8 *row = GP_OV_ROWS + 18 * r;
            u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
            u16 g = w16(sel + t + 2);
            for (int k = 0; k < n; k++) {
                const struct gp_row *a = &SSB->r[0][k];
                if (a->glob != g) continue;
                int d = a->pts - 3 * a->won, l = (int)apn - a->won - d;
                if (d < 0) d = 0;
                if (l < 0) l = 0;
                p16(row + 4, w16(row + 4) + apn);
                p16(row + 6, w16(row + 6) + a->won);
                p16(row + 8, w16(row + 8) + d);
                p16(row + 10, w16(row + 10) + l);
                p16(row + 12, w16(row + 12) + a->gf);
                p16(row + 14, w16(row + 14) + a->ga);
                p16(row + 16, w16(row + 16) + a->pts);
                break;
            }
        }
    for (int i = 0; i < n; i++) GP_OV_ORD[i] = w16(diy + 0x6D + 2 * i);    /* the table's own order first (ties) */
    for (int i = 1; i < n; i++)                 /* insertion sort, stable */
        for (int j = i; j > 0; j--) {
            const u8 *a = GP_OV_ROWS + GP_OV_ORD[j], *b = GP_OV_ROWS + GP_OV_ORD[j - 1];
            int dp = w16(a + 16) - w16(b + 16), dw = w16(a + 6) - w16(b + 6);
            int dd = (w16(a + 12) - w16(a + 14)) - (w16(b + 12) - w16(b + 14)), dg = w16(a + 12) - w16(b + 12);
            if (dp > 0 || (!dp && (dw > 0 || (!dw && (dd > 0 || (!dd && dg > 0)))))) {
                u16 x = GP_OV_ORD[j]; GP_OV_ORD[j] = GP_OV_ORD[j - 1]; GP_OV_ORD[j - 1] = x;
            } else break;
        }
    GP_OV_N = n;
}

/* 4.0.5 FASE 1 page (split leagues, Davide 28/10; internal/design/split-fase1-page.md): split.py's sp_freeze, at the
   first split of the season and before the points rule, keeps the career league's full phase-1 table (f1_capture:
   per place the row, played, won, drawn, lost, for, against, points - all < 256 in a phase 1) in F1_ST, the engine
   item 'F1' (saved with the career; the season byte: only this season's is shown). The table screen shows it in the
   overall mode (longtable lt_ov: f1_build -> GP_OV_ROWS / GP_OV_ORD), opened by itself while no phase-2 result
   exists (f1_auto), and by the statistics menu's entry FASE 1 / GRUPPI (fmtpage) any time this season. */
enum { F1N = 30, F1_MAGIC = 0x3146 };
struct f1_state { u16 magic; u8 season, n; u16 key, pad; u8 pl[F1N][8]; };
struct f1_state F1_ST;
const u32 F1_SIZE = sizeof(struct f1_state);
static u16 f1w(const u8 *b) { return b[0] | b[1] << 8; }
void f1_capture(const u8 *diy, u32 season, u32 mgr) {
    int n = f1w(diy + 0x31), me = 0;
    if (!mgr || n < 2 || n > F1N) return;       /* (S6a: mgr 0 = an all-CPU world SEASON - no manager's league, no
                                           FASE 1 table kept; split's sp_shsel keys no 'SH' either: every league the
                                           scratch block, as the season end's simulations) */
    for (int i = 0; i < n; i++) if (f1w(diy + 0x12D + 2 * i) == (u16)mgr) me = 1;
    if (!me) return;                            /* (the career's league only: its state is the saved one) */
    int played = 0;                             /* (groups known from day 0 - split's sp_pregroup, the MLS: no */
    for (int i = 0; i < n; i++) played += f1w(diy + 0x2B3 + 18 * i + 4);   /* phase-1 table yet) */
    if (!played) return;
    F1_ST.magic = F1_MAGIC; F1_ST.season = season; F1_ST.n = n; F1_ST.key = f1w(diy + 0x12D);
    for (int i = 0; i < n; i++) {
        int off = f1w(diy + 0x6D + 2 * i);
        const u8 *row = diy + 0x2B3 + off;
        u8 *p = F1_ST.pl[i];
        p[0] = off / 18; p[1] = row[4]; p[2] = row[6]; p[3] = row[8]; p[4] = row[10];
        p[5] = row[12]; p[6] = row[14]; p[7] = row[16];
    }
}
u32 f1_valid(const u8 *diy, u32 season) {
    return F1_ST.magic == F1_MAGIC && F1_ST.season == (u8)season && F1_ST.n == f1w(diy + 0x31) &&
           F1_ST.key == f1w(diy + 0x12D);
}
u32 f1_auto(const u8 *diy, u32 season) {       /* the phase-1 table still the live one: no phase-2 result yet */
    if (!f1_valid(diy, season)) return 0;
    u32 a = 0, b = 0;
    for (int i = 0; i < F1_ST.n; i++) { a += f1w(diy + 0x2B3 + 18 * i + 4); b += F1_ST.pl[i][1]; }
    return a == b;
}
u32 f1_build(const u8 *diy, u32 season) {
    if (!f1_valid(diy, season)) return 0;
    int n = F1_ST.n;
    for (int i = 0; i < n * 18; i++) GP_OV_ROWS[i] = diy[0x2B3 + i];
    for (int i = 0; i < n; i++) {
        const u8 *p = F1_ST.pl[i];
        u8 *row = GP_OV_ROWS + 18 * p[0];
        for (int k = 0; k < 7; k++) { row[4 + 2 * k] = p[1 + k]; row[5 + 2 * k] = 0; }
        GP_OV_ORD[i] = 18 * p[0];
    }
    GP_OV_N = n;
    GP_OV_ANNUAL = 0;
    return 1;
}

/* split's stage end (sp_stage_end, a fixture stage with 'table'): the DIY table in its order (+6Dh, the groups
   partitioned by sp_sort: Argentina's zone A then zone B) into SSB->r[k]; annual: SSB->r[2] = r[0] + r[1] by club,
   by points, goal difference, goals (the earlier stage's order on a tie). */
extern u16 GP_MGR;
void gp_stage(const u8 *diy, const u8 *sel, u32 k, u32 annual) {
    int n = diy[0x31] | diy[0x32] << 8;
    ss_set(diy[0x12D]);                         /* (the league's bank: its clubs' team file) */
    if (k >= SS_N || n < 1 || n > GT) return;
    struct gp_row *o = SSB->r[k];
    for (int i = 0; i < n; i++) {
        int off = diy[0x6D + 2 * i] | diy[0x6E + 2 * i] << 8, r = off / 18;
        const u8 *row = diy + 0x2B3 + off;
        u32 t = row[0] | row[1] << 8 | (u32)row[2] << 16 | (u32)row[3] << 24;
        o[i].team = diy[0x12D + 2 * r] | diy[0x12E + 2 * r] << 8;
        o[i].glob = sel[t + 2] | sel[t + 3] << 8;
        o[i].won = row[6] | row[7] << 8;
        o[i].gf = row[12] | row[13] << 8;
        o[i].ga = row[14] | row[15] << 8;
        o[i].pts = row[16] | row[17] << 8;
    }
    SSB->n[k] = n;
    SSB->fresh |= 1 << k;
    if (GP_FORCE && GP_MGR && GP_FORCE <= n)    /* (test builds, GPLAY_FORCE=k: the career club at place k of the
                                                   stage's kept table too - a stage_title knockout built at its end) */
        for (int i = 0; i < n; i++)
            if (o[i].team == (u16)GP_MGR && i != GP_FORCE - 1) {
                struct gp_row x;
                rcopy(&x, &o[i]); rcopy(&o[i], &o[GP_FORCE - 1]); rcopy(&o[GP_FORCE - 1], &x);
                break;
            }
    if (!annual || k == 0 || SSB->n[0] != n) return;
    struct gp_row *a = SSB->r[2], tmp;          /* (4.0.1: every stage table of this season but the annual's own, by
                                                    club: Uruguay's Apertura + Intermedio + Clausura) */
    for (int i = 0; i < n; i++) rcopy(&a[i], &SSB->r[0][i]);
    for (int q = 1; q < SS_N; q++) {
        if (q == 2 || !(SSB->fresh & 1 << q) || SSB->n[q] != n) continue;
        const struct gp_row *o2 = SSB->r[q];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) if (o2[j].glob == a[i].glob) {
                a[i].won += o2[j].won; a[i].gf += o2[j].gf; a[i].ga += o2[j].ga; a[i].pts += o2[j].pts;
            }
    }
    for (int i = 1; i < n; i++)                 /* insertion sort: stable */
        for (int j = i; j > 0; j--) {
            int dp = a[j].pts - a[j - 1].pts, dd = (a[j].gf - a[j].ga) - (a[j - 1].gf - a[j - 1].ga);
            if (dp > 0 || (dp == 0 && (dd > 0 || (dd == 0 && a[j].gf > a[j - 1].gf)))) {
                rcopy(&tmp, &a[j]); rcopy(&a[j], &a[j - 1]); rcopy(&a[j - 1], &tmp);
            } else break;
        }
    SSB->n[2] = n;
    SSB->fresh |= 4;
}

/* Argentina's relegation (LPF reglamento 2026 art. 26, AFA statute art. 93): kind 7 'promedio' (n = 0, no rounds;
   winner_div byte = the season's matches counted, loser_div = where the relegated go): the last of the promedios
   (points per match over this season's annual table and the two before, top-flight seasons only) and the last of
   the annual table (GP_SS 2) go down; a tie in a relegation place -> a play-off match at a neutral ground. History
   per club in PR_STATE (engine item 'PR', the build's GP_PROM table at a new career: dw count; count x (dw global,
   dw points y-2, db matches y-2, dw points y-1, db matches y-1)), shifted after every season end. */
enum { PR_N = 48 };
struct pr_club { u16 glob, p[2]; u8 m[2]; };
struct pr_state { u8 init, n, pad[2]; struct pr_club c[PR_N]; };
struct pr_state PR_STATE;
extern const u8 GP_PROM_TAB[];

static struct pr_club *pr_find(u16 g) {
    for (int i = 0; i < PR_STATE.n; i++) if (PR_STATE.c[i].glob == g) return &PR_STATE.c[i];
    return 0;
}

static void pr_seed(void) {
    const u8 *t = GP_PROM_TAB;
    PR_STATE.n = 0;
    for (int k = t[0] | t[1] << 8, i = 0; i < k && i < PR_N; i++) {
        const u8 *e = t + 2 + 8 * i;
        struct pr_club *c = &PR_STATE.c[PR_STATE.n++];
        c->glob = e[0] | e[1] << 8; c->p[0] = e[2] | e[3] << 8; c->m[0] = e[4]; c->p[1] = e[5] | e[6] << 8; c->m[1] = e[7];
    }
    PR_STATE.init = 1;
}

static int pr_row(int d, u16 g) {               /* a global number -> its row of division d's table, or -1 */
    for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

#if GP_S7
static int pr_pidx;                     /* (S7: the promedio entry's index, for GP_EXT) */
#endif
static void promedio(int d, int mnow, int ldiv) {
    if (!PR_STATE.init) pr_seed();
    int n = SSB->n[2];
    const struct gp_row *a = SSB->r[2];
    if (!(SSB->fresh & 4) || n != GP_IN.n[d]) {   /* (no annual table this season: the league's final table) */
        n = GP_IN.n[d];
        a = GP_IN.t[d];
    }
    ss_used = 1;
    if (n < 3) return;
    u32 P[GT], M[GT];
    for (int i = 0; i < n; i++) {
        struct pr_club *c = pr_find(a[i].glob);
        P[i] = a[i].pts + (c ? c->p[0] + c->p[1] : 0);
        M[i] = mnow + (c ? c->m[0] + c->m[1] : 0);
    }
    int w = 0, w2 = -1;                         /* the worst promedio (P / M), then the next worst */
    for (int i = 1; i < n; i++) if (P[i] * M[w] < P[w] * M[i] || (P[i] * M[w] == P[w] * M[i] && i > w)) w = i;
    for (int i = 0; i < n; i++) if (i != w && (w2 < 0 || P[i] * M[w2] < P[w2] * M[i])) w2 = i;
    int down1 = w;
    if (w2 >= 0 && P[w2] * M[w] == P[w] * M[w2]) {          /* level: a play-off match, the loser goes down */
        int ca = pr_row(d, a[w].glob), cb = pr_row(d, a[w2].glob);
        if (ca >= 0 && cb >= 0) down1 = tie(ca, cb, 1, HOST_NEUTRAL, LV_ET_PENS) == ca ? w2 : w;
    }
    int l = n - 1;                              /* the annual table's last, the promedio's relegated apart */
    if (l == down1) l--;
    int l2 = l - 1 == down1 ? l - 2 : l - 1, down2 = l;
    if (l2 >= 0 && a[l2].pts == a[l].pts) {
        int ca = pr_row(d, a[l].glob), cb = pr_row(d, a[l2].glob);
        if (ca >= 0 && cb >= 0) down2 = tie(ca, cb, 1, HOST_NEUTRAL, LV_ET_PENS) == ca ? l2 : l;
    }
    int c1 = pr_row(d, a[down1].glob), c2 = pr_row(d, a[down2].glob);
#if GP_S7
    if (c1 >= 0) dest(c1, ldiv, pr_pidx, EXT_LOSER);   /* (S7: an EXTERNAL loser_div - listed, not moved) */
    if (c2 >= 0) dest(c2, ldiv, pr_pidx, EXT_LOSER);
#else
    if (c1 >= 0) move(c1, ldiv - d);
    if (c2 >= 0) move(c2, ldiv - d);
#endif
    static struct pr_club nx[PR_N];             /* next season's history: this season and the one before */
    int nn = 0;
    for (int i = 0; i < n && nn < PR_N; i++) {
        if (i == down1 || i == down2) continue;
        struct pr_club *c = pr_find(a[i].glob), *o = &nx[nn++];
        o->glob = a[i].glob;
        o->p[0] = c ? c->p[1] : 0; o->m[0] = c ? c->m[1] : 0;
        o->p[1] = a[i].pts; o->m[1] = mnow;
    }
    for (int i = 0; i < nn; i++) {
        struct pr_club *o = &PR_STATE.c[i];
        o->glob = nx[i].glob; o->p[0] = nx[i].p[0]; o->p[1] = nx[i].p[1]; o->m[0] = nx[i].m[0]; o->m[1] = nx[i].m[1];
    }
    PR_STATE.n = nn;
    PR_STATE.init = 1;
}

static int team_club(u16 team) {        /* a team word -> its club (division * GT + place) in the tables, or -1 */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (team && GP_IN.t[d][k].team == team) return d * GT + k;
    return -1;
}

/* Second teams (B / II / U21 / U23 / Reserves: formats2627.md 'Second teams', Davide 2026-10-18; the integrator's
   design): SEC_TAB (mkseason.second_table): db countries; per country db nd, nd x db the division's level in the chain,
   db n, n x (dw the B team's global, dw its first team's (0xFFFF: another country), db top = the highest level it may
   reach (0xFF: any), db flags: bit 0 play-offs allowed (ITA), bit 1 it may leave the world from the lowest level (an
   off-file pool refills its slot), dw the B team's team word). In the country's tables (GP_IN, gp_end) a B team may not go up into or above its
   first team's level (the first team's level after this season's moves) nor above 'top': it is skipped as a [div,
   place] entrant of every play-off but a play-out (the next placed club enters) and held in a direct promotion place
   (the next club of its division goes up instead); a first team that ends in its B team's level or below sends the B
   team one level down (out of the world from the lowest level, flag bit 1: kind 0 pool swap) and the best placed
   relegated club of the B team's division stays (the level keeps its size). */
extern const u8 SEC_TAB[];
extern s8 SEC_SLT[], SEC_COPY[];
enum { BQ_N = 24 };
extern u8 GP_SEAS;
u8 SEC_BQ[BQ_N];                        /* 4.0.6 [0] the season byte when written (GP_SEAS at the season end: a new
                                           career's or another career's stale bytes are not this season's), then per B
                                           team (SEC_TAB order): 1 it may go up next season, 2 it may not (sec_post,
                                           its country's tables; 0: not known - an older save, a country not played:
                                           zones.py's build-time value). Item 'BQ'; zones zb_is reads it. */
enum { SEC_PO = 1, SEC_EXIT = 2 };

static const u8 *sec_find(int g, int team, const u8 **ent) {   /* the country entry and B entry of global g (or
                                                                    of team word team, when not 0), or 0 */
    const u8 *t = SEC_TAB;
    int nc = *t++;
    for (int c = 0; c < nc; c++) {
        const u8 *lv = t + 1;
        int nd = t[0], n = lv[nd];
        const u8 *e = lv + nd + 1;
        for (int i = 0; i < n; i++, e += 8)
            if ((e[0] | e[1] << 8) == g || (team && (e[6] | e[7] << 8) == team)) { *ent = e; return t; }
        t = e;
    }
    return 0;
}
static const u8 *sec_country(int g, const u8 **ent) { return sec_find(g, 0, ent); }

static int sec_lvl(const u8 *ct, int d) { return d < ct[0] ? ct[1 + d] : ct[1 + ct[0] - 1] + 1; }

static int sec_newlvl(const u8 *ct, int d, int g) {     /* a club's level after this season's moves */
    int dl = SEC_COPY[g] - SEC_SLT[g], l = sec_lvl(ct, d);
    if (!dl) return l;
    int nd = d + dl, nl = sec_lvl(ct, nd < 0 ? 0 : nd);
    if (nl == l) nl = l + (dl < 0 ? -1 : 1);          /* (a move inside a level of groups: pg_season's level change) */
    return nl;
}

static int sec_row(int g) {                             /* a global number's row in the country's tables, or -1 */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].glob == g) return d * GT + k;
    return -1;
}

static int sec_up_bad(const u8 *ct, const u8 *e, int d) {   /* B team of division d: going up one level is illegal */
    int target = sec_lvl(ct, d) - 1, f = e[2] | e[3] << 8;
    if (e[4] != 0xFF && target < e[4]) return 1;
    int fr = f == 0xFFFF ? -1 : sec_row(f);
    return fr >= 0 && target <= sec_newlvl(ct, DV(fr), f);
}

static int sec_inelig(int c) {                          /* a row skipped as a play-off entrant (not a play-out) */
    const u8 *e, *ct = sec_find(row(c)->glob, row(c)->team, &e);   /* (rows of a division simulated early carry
                                                                       their team word, not their global number) */
    return ct && (!(e[5] & SEC_PO) || sec_up_bad(ct, e, DV(c)));
}

static int place_club(int d, int p, int kind) {         /* [div, place] -> its row, B teams skipped but in play-outs */
    if (x_sfrom && d == x_sdiv && p >= x_sfrom) p++;    /* (4.2: the cup place's scroll) */
    if (d >= GP_IN.nd || d >= GD || p < 1 || p > GP_IN.n[d]) return -1;
    if (kind == 4) return d * GT + p - 1;
    for (int k = 0; k < GP_IN.n[d]; k++)
        if (!sec_inelig(d * GT + k) && !--p) return d * GT + k;
    return -1;
}

#ifndef SEC_FORCE
#define SEC_FORCE 0
#endif
#ifndef SEC_FORCE_B
#define SEC_FORCE_B 0xFFFF
#endif
static void sec_swap(int d, int g, int up) {            /* (SEC_FORCE test builds: g takes a mover's move) */
    for (int k = 0; k < GP_IN.n[d]; k++) {
        int h = GP_IN.t[d][k].glob, dh = SEC_COPY[h] - SEC_SLT[h];
        if (h != g && (up ? dh < 0 : dh > 0) && SEC_COPY[g] == SEC_SLT[g]) {
            SEC_COPY[g] = SEC_SLT[g] + dh;
            SEC_COPY[h] = SEC_SLT[h];
            return;
        }
    }
}

void sec_post(void) {                                   /* gp_end, after the moves: holds, next clubs, B teams down */
    const u8 *t = SEC_TAB;
    int nc = *t++;
    if (SEC_FORCE > 0 && nc > 0) {                            /* (test builds: B team SEC_FORCE_B (else the first) promoted
                                                           (1), its first team relegated (2), both (3)) */
        const u8 *e = 0;
        if (!sec_country(SEC_FORCE_B, &e)) e = t + 1 + t[0] + 1;
        int rb = sec_row(e[0] | e[1] << 8), rf = sec_row(e[2] | e[3] << 8);
        int fo = SEC_FORCE;
        if (rb >= 0 && (fo & 1)) sec_swap(DV(rb), e[0] | e[1] << 8, 1);
        if (rb >= 0 && rf >= 0 && (fo & 2)) sec_swap(DV(rf), e[2] | e[3] << 8, 0);
    }
    for (int c = 0; c < nc; c++) {
        const u8 *ct = t, *e = t + 1 + t[0] + 1;
        int n = t[1 + t[0]];
        t = e + 8 * n;
        for (int i = 0; i < n; i++, e += 8) {
            int gb = e[0] | e[1] << 8, gf = e[2] | e[3] << 8, rb = sec_row(gb);
            if (rb < 0) continue;                       /* (not this country's tables) */
            int db = DV(rb), lb = sec_lvl(ct, db), nb = sec_newlvl(ct, db, gb);
            int rf = gf == 0xFFFF ? -1 : sec_row(gf), nf = rf >= 0 ? sec_newlvl(ct, DV(rf), gf) : -1;
            int lowest = sec_lvl(ct, db) == sec_lvl(ct, ct[0] - 1);
            int coupled = rf >= 0 && nf >= (nb < lb ? lb : nb) && nb <= lb, dl = SEC_COPY[gb] - SEC_SLT[gb];
            if (coupled && (!lowest || (e[5] & SEC_EXIT))) {   /* the first team in its level: one down */
                SEC_COPY[gb] = SEC_SLT[gb] + (lowest ? ct[0] - db : 1);
                if (!lowest)                            /* (out of the world: a pool identity takes its slot) */
                    for (int k = 0; k < GP_IN.n[db]; k++) {    /* the best placed relegated of its division stays */
                        int g = GP_IN.t[db][k].glob;
                        if (g != gb && SEC_COPY[g] > SEC_SLT[g]) { SEC_COPY[g] = SEC_SLT[g]; break; }
                    }
            } else if (nb < lb && (coupled || sec_up_bad(ct, e, db)))   /* up, not allowed: held (coupled, no pool: */
                SEC_COPY[gb] = SEC_SLT[gb];                             /* it stays, declared) */
            else
                continue;
            if (nb < lb)                                /* its promotion: the next club of its division */
                for (int k = 0; k < GP_IN.n[db]; k++) {
                    int g = GP_IN.t[db][k].glob, r = db * GT + k;
                    if (g == gb || SEC_COPY[g] != SEC_SLT[g] || sec_inelig(r)) continue;
                    SEC_COPY[g] = SEC_SLT[g] + dl;
                    break;
                }
        }
    }
    t = SEC_TAB + 1;                                    /* 4.0.6 next season: may each B team go up (zone colours) */
    for (int c = 0, bi = 0; c < nc; c++) {
        const u8 *ct = t, *e = t + 1 + t[0] + 1;
        int n = t[1 + t[0]];
        t = e + 8 * n;
        for (int i = 0; i < n; i++, e += 8, bi++) {
            int gb = e[0] | e[1] << 8, gf = e[2] | e[3] << 8, rb = sec_row(gb);
            if (rb < 0 || bi + 1 >= BQ_N) continue;
            int target = sec_newlvl(ct, DV(rb), gb) - 1, rf = gf == 0xFFFF ? -1 : sec_row(gf);
            int bad = (e[4] != 0xFF && target < e[4]) || (rf >= 0 && target <= sec_newlvl(ct, DV(rf), gf));
            SEC_BQ[1 + bi] = bad ? 2 : 1;
            SEC_BQ[0] = GP_SEAS;
        }
    }
}

/* The league champion from a 'title' play-off (GP_OUT.res kind 5): the season end's top-9 list of the country's top
   division (cseg_927A2: GP_TOPW = their team words, GP_TOPR = their 684-byte records), which the qualifiers read for
   the 'champion' place (the game's cseg_93974 / uefaq's uq_country), gets the play-off's winner first, the clubs
   above it one place down. 4.1 (Davide 06/11, Malta's 11th won the Final Four): a winner outside the top 9 comes in
   first all the same - its record from the game's team cache (FindTeamInCache), the 9th drops out; not in the cache:
   as before, the table's 1st stays. */
extern u16 GP_TOPW[9];
extern u8 GP_TOPR[9 * 684];
static u8 ch_tmp[684];
extern u8 GP_FTIC[];                    /* FindTeamInCache: word [D0] = the team -> ZF, [A0] = its 684-byte record */
extern u32 GP_D0, GP_D1, GP_A0;         /* (the game's pseudo registers it uses: kept) */
#if defined(__i386__)                   /* (the exe; the host tests' cc - arm64 - has no x86 asm: no cache there) */
__attribute__((naked, noinline)) static const u8 *gp_ftic(u32 w) {
    __asm__ volatile(
        "pushl GP_D0\n\tpushl GP_D1\n\tpushl GP_A0\n\t"
        "movl 16(%esp), %eax\n\tmovw %ax, GP_D0\n\t"
        "pushal\n\tcall GP_FTIC\n\tpopal\n\t"
        "movl $0, %eax\n\tjnz 1f\n\tmovl GP_A0, %eax\n"
        "1:\n\tpopl GP_A0\n\tpopl GP_D1\n\tpopl GP_D0\n\tret");
}
#else
static const u8 *gp_ftic(u32 w) { (void)w; return 0; }
#endif
#ifndef GP_CHFORCE                      /* (4.1 test builds, GPLAY_CHFORCE=1: the title winner taken out of the top 9 - its */
#define GP_CHFORCE 0                    /* slot gets the 9th's word and record - so gp_champ fetches it from the cache) */
#endif
void gp_champ(void) {
    for (int k = 0; k < GP_OUT.nres; k++) {
        if (GP_OUT.res[k].kind != K_TITLE || ch_low >> k & 1) continue;
        u16 w = GP_OUT.res[k].team[0];
        int j = 0;
        while (j < 9 && GP_TOPW[j] != w) j++;
        if (GP_CHFORCE && j < 8) {
            GP_TOPW[j] = GP_TOPW[8];
            for (int b = 0; b < 684; b++) GP_TOPR[684 * j + b] = GP_TOPR[684 * 8 + b];
            j = 9;
        }
        if (j == 0) continue;
        const u8 *src = GP_TOPR + 684 * j;
        if (j >= 9) {
            src = gp_ftic(w);
            if (!src || (src[0] | src[1] << 8) != w) continue;
            j = 8;
        }
        for (int b = 0; b < 684; b++) ch_tmp[b] = src[b];
        for (int i = j; i > 0; i--) {
            GP_TOPW[i] = GP_TOPW[i - 1];
            for (int b = 0; b < 684; b++) GP_TOPR[684 * i + b] = GP_TOPR[684 * (i - 1) + b];
        }
        GP_TOPW[0] = w;
        for (int b = 0; b < 684; b++) GP_TOPR[b] = ch_tmp[b];
    }
}

/* 4.0.1 the SEASON WINNERS page's last season (winners.py; the engine block's item 'WN', zeroed in a save without it):
   the career country's titles as this season end decides them - each play-off's winner ('K', its index; a stage
   title's champion) and each division's 1st ('L', its index; division 0 of a league with an annual table: that
   table's), as team words. Written by gp_season's pass over the career club's country only; read by gp_wn_c. */
extern u8 GP_SEAS;
enum { WN_N = 40, WN_MAGIC = 0x4E57 };
struct wn_e { u8 type, idx; u16 team; };
struct wn_state { u16 magic; u8 season, n; struct wn_e e[WN_N]; };
struct wn_state WN_ST;
const u32 WN_SIZE = sizeof(struct wn_state);
static int wn_on;
static void wn_add(int type, int idx, u16 team) {
    if (!wn_on || team == 0xFFFF || WN_ST.n >= WN_N) return;
    struct wn_e *x = &WN_ST.e[WN_ST.n++];
    x->type = (u8)type; x->idx = (u8)idx; x->team = team;
}
/* 4.0.5 rc19 (Davide): this season's titles decided BEFORE the season-end menu - gp_pre_c runs gp_season in preview
   mode (GP_PRE) at the career league's end; its entries follow a marker 'p' (idx = the season) after the last
   season's in WN_ST (saved with the career). The last season's readers stop at the marker; gp_wn_c reads this
   season's after it. CONTINUA's gp_season decides the same (per play-off seeds from its own entrants, the early
   tables kept) and rewrites WN_ST as the last season. */
enum { WN_PRE = 'p' };
u8 GP_PRE;
#if GP_GPLX
#define GP_XS                           /* (4.2 GPLX: gplx.c in obj4 calls it) */
#else
#define GP_XS static
#endif
__attribute__((minsize)) GP_XS u32 wn_find(int ty, int ix, int pre) {   /* the last season's entry (before a marker), or (pre) this
                                           season's previewed one (after its marker) */
    int i = 0;
    if (pre) {
        if (WN_ST.magic != WN_MAGIC) return 0xFFFE;
        while (i < WN_ST.n && i < WN_N && !(WN_ST.e[i].type == WN_PRE && WN_ST.e[i].idx == GP_SEAS)) i++;
        i++;
    }
    for (; i < WN_ST.n && i < WN_N && (pre || WN_ST.e[i].type != WN_PRE); i++)
        if (WN_ST.e[i].type == ty && (ty == 'M' || WN_ST.e[i].idx == ix))
            return WN_ST.e[i].team | (ty == 'M' ? (u32)WN_ST.e[i].idx << 16 : 0);
    return 0xFFFE;
}

/* 4.0.1 (Colombia's cuadrangulares): spec flag 08h = the entrants after the heads (one per leading group round) are
   drawn - pm[i] = the entrant taking slot i (the builders keep the result in GP_ST's contest; a simulation draws once) */
static void pot_perm(const u8 *s, int *pm) {
    int n = s[1], h = 0;
    for (int i = 0; i < n; i++) pm[i] = i;
    if (!(s[5] & 8)) return;
    const u8 *r = ents_of(s) + 4 * n;
    for (int k = 0; k < s[2] && (r[1] & 0x80); k++) { h++; r += 6 + 2 * r[0]; }
    for (int i = n - 1; i > h; i--) { int j = h + below(i - h + 1), x = pm[i]; pm[i] = pm[j]; pm[j] = x; }
}

/* 4.2 s3shape: the Coppa Italia Serie C's play-off place (entrant type 9: e[1] the first group's division, e[2] the
   groups, e[3] the play-out gap | 0x80 the real rule when the finalist is known). A winner in the play-out places
   (n-3 / n-2 always, n-5 / n-4 when their tie is under the gap apart) or relegated is precluded, as one in 1st-3rd.
   The Mod 4.1's (dplay.c): the winner from 11th down unless precluded, else the 11th of its group; unknown: the best
   11th of the groups. The real rule (FIGC C.U. 209/A, NOIF art. 49 II-III): a precluded winner's place to the other
   finalist (the same preclusions); both precluded, the 4th of the winner's group; the club taking it from 4th-10th
   leaves its group's play-off and that group scrolls (the places below move up one, the 11th comes in). */
u16 GP_CUPW, GP_CUPF;                   /* (the glue: the cup's winner and other finalist, team words; 0 unknown) */
#if GP_S3SKIP
/* The cup place: cuprule.c's cup_rule - the ONE implementation (MC 15/11, FIGC C.U. 209/A), a leaf TU in obj4's S3C band that
   gplay's cup_code (the season-end play-off, GP_IN's tables) and dplay's career contest (DP_IN's tables) both call on a view
   (cupview.h) of the groups' final tables, the cup's winner and finalist, the play-out gap and the rule (real: C.U. 209/A
   II.1-II.2; else the Mod's 4.1 rule). Its result: the place g * 32 + k (k from 0), and the scroll: the club of group sg
   leaves its play-off from place sfrom (1-based; 0 none). The host tests include it (GP_RULE_INLINE). */
#include "cupview.h"
#ifdef GP_RULE_INLINE
#include "cuprule.c"
#else
extern int cup_rule(struct cup_view *v);
#endif
static int cup_code(const u8 *e) {
    struct cup_view v;
    int d0 = e[1], ng = e[2], r;
    v.ng = ng < 4 ? ng : 4; v.real = e[3] >> 7; v.w = GP_CUPW; v.f = GP_CUPF;
    for (int g = 0; g < v.ng; g++) {
        int d = d0 + g;
        v.t[g] = (const struct cv_row *)(d < GP_IN.nd ? GP_IN.t[d] : GP_IN.t[0]);
        v.n[g] = d < GP_IN.nd ? GP_IN.n[d] : 0;
        v.gap[g] = e[3] & 0x7F;         /* (the spec holds one gap for its groups) */
    }
    if ((r = cup_rule(&v)) < 0) return -1;
    if (v.sfrom) { x_sdiv = d0 + v.sg; x_sfrom = v.sfrom; }
    return (d0 + (r >> 5)) * GT + (r & 31);
}
#else
static int cup_out(int d, int k, int gap) {     /* place k (from 0) precluded */
    const struct gp_row *t = GP_IN.t[d];
    int n = GP_IN.n[d];
    if (k <= 2) return 1;
    if (n < 6 || k < n - 5) return 0;
    if (k == n - 5) return !gap || t[n - 5].pts - t[n - 2].pts < gap;
    if (k == n - 4) return !gap || t[n - 4].pts - t[n - 3].pts < gap;
    return 1;
}
static int cup_find(int d0, int ng, u16 team, int *d, int *k) {
    for (*d = d0; team && *d < d0 + ng && *d < GP_IN.nd; (*d)++)
        for (*k = 0; *k < GP_IN.n[*d]; (*k)++) if (GP_IN.t[*d][*k].team == team) return 1;
    return 0;
}
static int cup_code(const u8 *e) {
    int d0 = e[1], ng = e[2], gap = e[3] & 0x7F, dw, kw, df, kf, b = -1;
    int w = cup_find(d0, ng, GP_CUPW, &dw, &kw);
    if ((e[3] & 0x80) && GP_CUPF && w) {
        int d = -1, k = -1;
        if (!cup_out(dw, kw, gap)) d = dw, k = kw;
        else if (cup_find(d0, ng, GP_CUPF, &df, &kf) && !cup_out(df, kf, gap)) d = df, k = kf;
        if (d < 0) { d = dw; k = 3; }   /* (both precluded: the 4th of the winner's group) */
        if (k <= 9) { x_sdiv = d; x_sfrom = k + 1; }
        return d * GT + k;
    }
    if (w) return dw * GT + (kw >= 10 && !cup_out(dw, kw, gap) ? kw : 10);
    for (int d = d0; d < d0 + ng && d < GP_IN.nd; d++)
        if (GP_IN.n[d] > 10 && (b < 0 || better(d * GT + 10, b))) b = d * GT + 10;
    return b;
}
#endif
static void draw(int *c, int n) {       /* a draw: c[0 .. n) shuffled */
    for (int i = n - 1; i > 0; i--) { int j = below(i + 1), x = c[i]; c[i] = c[j]; c[j] = x; }
}

#ifndef GP_S3SKIP
#define GP_S3SKIP 0
#endif
#if GP_S3SKIP
/* (4.2 S3 glue, MC's guard: bit i = play-off i of the country's spec is not run THIS season end - dplay finished the Serie B
   phase of an old save (gplay.py gp_end sets it from dplay's DP_BHOLD, only then). Transient: gp_season clears it at its end;
   never saved; 0 when nothing holds. Compiled in S3 builds only.) */
u32 GP_SKIPPO;
#endif
GP_KOSIZE void gp_season(void) {
    const u8 *s = GP_IN.spec;
    u32 h = 0;
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) h = h * 31 + GP_IN.t[d][k].glob + (GP_IN.t[d][k].pts << 9);
    rng = h;
    GP_OUT.nmv = 0;
    GP_OUT.nres = 0;
    ch_low = 0;
#if GP_S7
    if (!GP_PRE) GP_EXT.n = GP_EXT.full = 0;   /* (S7: this season end's cross-struct list) */
#endif
    for (int k = 0; k < 3; k++) {               /* (stage titles: this season's, from the specs below) */
        GP_OUT.sres[k].kind = 0;
        GP_OUT.sres[k].team[0] = GP_OUT.sres[k].team[1] = GP_OUT.sres[k].glob[0] = GP_OUT.sres[k].glob[1] = 0xFFFF;
    }
    int prev_loser = -1;                        /* the last tie's loser of the play-off before (entrant type 4) */
    srl_div = -1;
    ss_used = 0;
    ss_set(GP_IN.n[0] ? GP_IN.t[0][0].team : GP_PRE ? GP_IN.mgr : 0);   /* (this country's bank: its top division's
                                                   file; the preview without it: the career club's) */
    gp_force();
    wn_on = 0;                                  /* (the career club's country: its titles into WN_ST) */
    int wn_div = 0;
    for (int d = 0; d < GP_IN.nd && d < GD && GP_IN.mgr; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].team == GP_IN.mgr) { wn_on = 1; wn_div = d; }
    if (GP_PRE) wn_on = 1;                      /* (rc19 preview: the play-offs' entries only, after gp_pre_c's marker) */
    else if (wn_on) {
        WN_ST.magic = WN_MAGIC; WN_ST.season = GP_SEAS; WN_ST.n = 0;
        wn_add('M', wn_div, GP_IN.mgr);         /* (4.0.1: the division it played in - the last season's page) */
        for (int d = 0; d < GP_IN.nd && d < GD; d++)
            if (GP_IN.n[d])
                wn_add('L', d, d == 0 && (SSB->fresh & 4) && SSB->n[2] == GP_IN.n[0] ? SSB->r[2][0].team
                                                                                        : GP_IN.t[d][0].team);
    }
    for (int pidx = 0; s && *s; pidx++) {
        int kind = s[0] & 0x3F, n = s[1], nr = s[2], wdiv = s[3], ldiv = s[4];
        const u8 *e = ents_of(s), *r = e + 4 * n;
        by_rec = s[5] & 2;
        x_lvl = x_direct = 0; x_seeded = 0;     /* (4.2: the extension's ops) */
        x_b = s + 7; x_e = s[0] & PO_EXT ? s + 7 + s[6] : x_b;
        for (const u8 *x = x_b; x < x_e; x += x[0] == E_LEVEL ? 1 : x[0] == E_BEST ? 4 : 2) {
            if (x[0] == E_DIRECT) x_direct = x[1];
            if (x[0] == E_LEVEL) x_lvl = 1;
            if (x[0] == E_SEEDED) x_seeded |= 1u << (x[1] & 31);
        }
        if (kind == K_PROM) {                   /* (no entrants, no rounds) */
#if GP_S7
            if (!GP_PRE) { pr_pidx = pidx; promedio(0, wdiv, ldiv); }   /* (the preview: no promedio - its history is written) */
#else
            if (!GP_PRE) promedio(0, wdiv, ldiv);   /* (the preview: no promedio - its history is written) */
#endif
            s = r;
            continue;
        }
#if GP_S3SKIP
        if (GP_SKIPPO >> (pidx & 31) & 1) {     /* (S3 guard: dplay's B phase finished this one; its moves are dplay's) */
            for (int k = nr; k; k--) r += 6 + 2 * r[0];
            s = r;
            continue;
        }
#endif
        int club[GN], ok = kind == 1 || kind == 4 || kind == K_TITLE || kind == K_CONT || kind == K_STAGE;
        const struct gp_dec *dec = kind == K_STAGE ? stage_dec(wdiv) : 0;   /* (decided mid-season) */
        if (dec) ok = 0;
        if (GP_PRE && (pidx == GP_IN.pi[0] || pidx == GP_IN.pi[1])) ok = 0;   /* (rc19 preview: the club's own) */
        if (s[5] & PO_SUPER) { ok = 0; dec = 0; }   /* (4.0.5 MEX's Campeon de Campeones: the next season's supercup) */
        int W[GN], L[GN], nt = 0, last = -1, lastr = 0, nlast = 0;
        int P[GN], np = 0, glast = -1, kog = 0, winners = s[5] >> 4 & 7 ? s[5] >> 4 & 7 : 1;   /* (kog: a knockout
                                           round after a group - its last tie decides, NZ's Grand Final, the Poule) */
        x_lot0 = 0x9E3779B9u * (u32)(pidx + 1);
        x_sfrom = 0;
        for (int i = 0; i < n && i < GN; i++)   /* (4.2: the cup place first - its scroll moves the places) */
            if (e[4 * i] == 9 && (club[i] = cup_code(e + 4 * i)) < 0) ok = 0;
        for (int i = 0; i < n && i < GN; i++) {
            int ty = e[4 * i], d = e[4 * i + 1], p = e[4 * i + 2];
            if (ty == 9) continue;
            club[i] = -1;                       /* (4.0.6, Ben: an entrant refused below kept stack garbage, which
                                                   rc19's seed loop then read through row(): San Marino's 'europe'
                                                   entrants past its 6 clubs) */
            if (ty == 3) {
                club[i] = stage_club(d, e[4 * i + 3], p);
                if (club[i] < 0) ok = 0;
            } else if (ty == 4) {               /* the previous play-off's final loser (Primera Nacional's reducido) */
                club[i] = prev_loser;
                if (club[i] < 0) ok = 0;
            } else if (ty == 5) {               /* 4.0 ARG: the Trofeo's finalists (title_club) */
                club[i] = title_club(d, p);
                if (club[i] < 0) ok = 0;
            } else if (ty == 6) {               /* 4.0 MLT: a seed of the title decider (split_seed) */
                club[i] = split_seed(d, e[4 * i + 3], p);
                if (club[i] < 0) ok = 0;
            } else if (ty == 7) {               /* 4.0.1 URU / PER: a seed of the national title play-off */
                club[i] = title_seed(d, e[4 * i + 3], p);
                if (club[i] < 0) ok = 0;
            } else if (ty == 8) {               /* a given club, by its team word (NZ: the A-League reserves) */
                club[i] = team_club(p | e[4 * i + 3] << 8);
                if (club[i] < 0) club[i] = -2;  /* (rc18: not in this country's tables - another league's reserves:
                                                   left out of a group round, NZ's Championship simulated without
                                                   them - they never reach its Grand Final; anywhere else: not played) */
            } else if (ty != 0 || d >= GP_IN.nd || p < 1 || p > GP_IN.n[d]) { club[i] = -1; ok = 0; }   /* (4.0.6:
                                           set - its stream's seed below read it; the play-off is not played then) */
            else if ((club[i] = place_club(d, p, kind)) < 0) ok = 0;
        }
        po_low = 1;                             /* (an entrant by a top-division place: ty 0 / 3 / 5 / 6 / 7 with d 0) */
        for (int i = 0; i < n && i < GN; i++)
            if (e[4 * i] != 4 && e[4 * i] != 8 && e[4 * i] != 9 && e[4 * i + 1] == 0) po_low = 0;
        {                                       /* rc19: each play-off's own random stream, from its entrants' rows
                                                   (the preview at the league's end and CONTINUA's season end decide
                                                   the same whatever the other divisions' tables) */
            u32 h2 = 0x9E3779B9u * (u32)(pidx + 1) + (u32)kind;
            for (int i = 0; i < n && i < GN; i++)
                h2 = h2 * 31 + (club[i] >= 0 ? row(club[i])->team + ((u32)row(club[i])->pts << 16) : 0xFFFFu);   /* (team
                                                   words: an early table's glob is read off the wrong team list) */
            rng = h2;
        }
        if (s[5] & 8) {                         /* (4.0.1: the drawn pot) */
            int pm[GN], tmp[GN];
            pot_perm(s, pm);
            for (int i = 0; i < n && i < GN; i++) tmp[i] = club[pm[i]];
            for (int i = 0; i < n && i < GN; i++) club[i] = tmp[i];
        }
        if (x_direct && ok && n >= 2 && (int)row(club[0])->pts - (int)row(club[1])->pts >= x_direct) {
            W[0] = club[0]; L[0] = club[1];     /* (4.2: entrant 0 far enough ahead - no round played) */
            nt = 1; last = 0; lastr = 0; nlast = 1;
            for (; nr; nr--) r += 6 + 2 * r[0];
        }
        for (int k = 0; k < nr; k++) {          /* walk the rounds (also to skip a play-off not played here) */
            int ties = r[0], legs = r[1], host = r[2] & 0x3F, skip = r[2] & HOST_SKIP_SAME, level = r[3];
            int fin = r[2] & HOST_UEFA_FINAL;
            int pairing = r[4], gap = r[5];
            const u8 *m = r + 6;
            int mem[2 * GN], gm = legs & 0x80 ? ties : 2 * ties;     /* (a group round: ties = its members) */
            for (int i = 0; i < gm; i++) {
                int c = m[i], v = -1;
                if (c == BEST_LOSER) {          /* the best placed loser of the previous round */
                    for (int t = lastr; t < lastr + nlast && t < nt; t++)   /* (still the previous round's) */
                        if (v < 0 || better(L[t], v)) v = L[t];
                } else if (c < 0x40) v = c < n ? club[c] : -1;
                else if (c < 0x80 && (s[5] & PO_SKIP2)) {     /* 'skip_second': the k-th placing that is no B team */
                    int k = c & 0x3F, j = 0;
                    for (; j < np; j++) if (!sec_inelig(P[j]) && !k--) break;
                    v = j < np ? P[j] : -1;
                    if (v >= 0 && i < GT) ms[i] = PS[j];
                } else if (c < 0x80) { v = (c & 0x3F) < np ? P[c & 0x3F] : -1; if (v >= 0 && i < GT) ms[i] = PS[c & 0x3F]; }
                else if (c < 0xC0) v = (c & 0x3F) < nt ? W[c & 0x3F] : -1;
                else v = (c & 0x3F) < nt ? L[c & 0x3F] : -1;
                mem[i] = v;
                if (v < 0 && !(v == -2 && (legs & 0x80))) ok = 0;
            }
            if (legs & 0x80) {                  /* a group round */
                static u8 bon[GT];              /* (rc18: members left out, -2: absent reserves - compacted in
                                                   place, mem / ms: the .bss is full; bon static: the stack, as ms) */
                int gm2 = 0;
                for (int i = 0; i < ties && i < GT; i++)
                    if (mem[i] != -2) { mem[gm2] = mem[i]; bon[gm2] = m[ties + i]; ms[gm2] = ms[i]; gm2++; }
                if (ok && gm2 <= GT && np + gm2 <= GN) {
                    group(mem, gm2, legs & 0x7F, host == HOST_NEUTRAL, bon, P + np, ms, PS + np);
                    glast = np;
                }
                np += gm2;
                last = -1;
                r = m + 2 * ties;
                continue;
            }
            for (const u8 *x = x_b; x < x_e && ok; x += x[0] == E_LEVEL ? 1 : x[0] == E_BEST ? 4 : 2)
                if (x[0] == E_BEST && x[1] == k && x[3] <= 2 * ties) {  /* (4.2: the best of i .. j-1 first) */
                    int at = x[2];
                    for (int i = x[2] + 1; i < x[3]; i++) if (better(mem[i], mem[at])) at = i;
                    for (int c = mem[at]; at > x[2]; at--) mem[at] = mem[at - 1], mem[at - 1] = c;
                }
            int tmp[2 * GN];
            if (ok && (x_seeded >> k & 1)) {    /* (4.2: seeds mem[0 .. ties) v the others drawn, the seed second) */
                draw(mem + ties, ties);
                for (int i = 0; i < ties; i++) { tmp[2 * i] = mem[ties + i]; tmp[2 * i + 1] = mem[i]; }
                for (int i = 0; i < 2 * ties; i++) mem[i] = tmp[i];
            } else if (ok && (pairing & 0x80)) {   /* a draw (pack 'pairing': 'draw'): the first p members shuffled, paired */
                int pn = (pairing & 0x7F) <= 2 * ties ? pairing & 0x7F : 2 * ties;
                draw(mem, pn);
            } else if (ok && pairing) {     /* best v worst: sorted, then 1st v last, 2nd v second last ... */
                int pn = pairing <= 2 * ties ? pairing : 2 * ties;
                for (int i = 1; i < pn; i++) {
                    int x = mem[i], j = i;
                    while (j > 0 && sbetter_cmp(x, mem[j - 1])) { mem[j] = mem[j - 1]; j--; }
                    mem[j] = x;
                }
                for (int i = 0; i < pn / 2; i++) { tmp[2 * i] = mem[pn - 1 - i]; tmp[2 * i + 1] = mem[i]; }
                for (int i = 0; i < pn; i++) mem[i] = tmp[i];
            }
            lastr = nt; nlast = ties;
            if (glast >= 0) kog = 1;
            for (int i = 0; i < ties; i++) {
                if (ok && nt < GN) {
                    int a = mem[2 * i], b = mem[2 * i + 1], d = (int)row(a)->pts - (int)row(b)->pts;
                    int w = a == b && skip ? a                                         /* (one club: no tie) */
                          : gap && (d >= gap || -d >= gap) ? (better(a, b) ? a : b)   /* (too far apart: no tie) */
                          : fin && uefa_fin(row(a)->team, row(b)->team) ? (better(a, b) ? a : b)   /* (C.U. 244/A (iv)) */
                          : legs == 3 ? series(a, b, level) : tie(a, b, legs, host, level);
                    if (GP_IN.pl_pi == pidx + 1 && nt < KT && GP_IN.pl_w[nt])    /* (played in slot 4: its result) */
                        w = row(b)->team == GP_IN.pl_w[nt] ? b : row(a)->team == GP_IN.pl_w[nt] ? a : w;
                    W[nt] = w; L[nt] = w == mem[2 * i] ? mem[2 * i + 1] : mem[2 * i];
                    last = nt; glast = -1;
                }
                nt++;
            }
            r = m + 2 * ties;
        }
        if (ldiv == RESERVE) ldiv = GP_IN.nd;   /* (the reserve: out of every division) */
        const int pfin = kind == K_TITLE && !GP_IN.pl_t2 && GP_IN.pl_pi == pidx + 1 && team_club(GP_IN.pl_fw) >= 0;
        if (kind == K_STAGE) {                  /* a stage title: its champion / runner-up, no move, no league title */
            struct gp_res *x = (wdiv & 3) < 3 ? &sres_of(wdiv >> 2)[wdiv & 3] : 0;
            if (x && dec) {
                x->kind = K_STAGE; x->div = wdiv >> 2;
                x->team[0] = dec->team[0]; x->team[1] = dec->team[1]; x->glob[0] = dec->glob[0]; x->glob[1] = dec->glob[1];
            } else if (x && ok && last >= 0) {
                x->kind = K_STAGE; x->div = DV(W[last]);
                x->team[0] = row(W[last])->team; x->glob[0] = row(W[last])->glob;
                x->team[1] = L[last] != W[last] ? row(L[last])->team : 0xFFFF;
                x->glob[1] = L[last] != W[last] ? row(L[last])->glob : 0xFFFF;
            }
        } else if (kind == K_TITLE && GP_IN.pl_t2 && GP_IN.pl_pi == pidx + 1 && team_club(GP_IN.pl_w[0]) >= 0) {
            result(kind, team_club(GP_IN.pl_w[0]), team_club(GP_IN.pl_w[1]));   /* (played: a group contest's final) */
        } else if (pfin) {                      /* 4.2: played: the contest's own final, not the re-run's (its seeds may
                                                   differ from the league end's: RC3 world_title_mlt) */
            result(kind, team_club(GP_IN.pl_fw), GP_IN.pl_fl ? team_club(GP_IN.pl_fl) : -1);
        } else if (ok && (kind == K_TITLE || kind == K_CONT) && glast >= 0 && !kog) {   /* a final group: its 1st (2nd) */
            result(kind, P[glast], np - glast > 1 ? P[glast + 1] : -1);
        } else if (ok && (kind == K_TITLE || kind == K_CONT) && last >= 0) {   /* the last tie's winner (loser) */
            result(kind, W[last], L[last] == W[last] ? -1 : L[last]);
        } else if (ok && glast >= 0 && kind == 1) {    /* a final group: its top `winners` to winner_div, the other
                                                   winner_div clubs to loser_div, the rest stay */
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c), top = 0;
                for (int k = 0; k < winners; k++) if (P[glast + k] == c) top = 1;
                if (top) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                dest(c, to, pidx, top ? EXT_WINNER : EXT_LOSER);
            }
        } else if (ok && last >= 0 && kind == 4) {     /* playout: the last round's losers down */
            for (int t = lastr; t < lastr + nlast && t < GN; t++) dest(L[t], ldiv, pidx, EXT_LOSER);
        } else if (ok && last >= 0) {           /* the winner to winner_div; another winner_div entrant down */
            int w = W[last];
            for (int i = 0; i < n; i++) {
                int c = club[i], to = DV(c);
                if (c == w) to = wdiv;
                else if (DV(c) == wdiv) to = ldiv;
                dest(c, to, pidx, c == w ? EXT_WINNER : EXT_LOSER);
            }
        }
        if (kind == K_STAGE)                    /* (WN_ST: this play-off's winner) */
            wn_add('K', pidx, (wdiv & 3) < 3 && sres_of(wdiv >> 2)[wdiv & 3].kind ? sres_of(wdiv >> 2)[wdiv & 3].team[0]
                                                                                : 0xFFFF);
        else if (kind == K_TITLE && GP_IN.pl_t2 && GP_IN.pl_pi == pidx + 1)
            wn_add('K', pidx, GP_IN.pl_w[0] ? GP_IN.pl_w[0] : 0xFFFF);
        else if (pfin)
            wn_add('K', pidx, GP_IN.pl_fw);
        else if (ok && kind != 4 && (glast >= 0 || last >= 0))
            wn_add('K', pidx, row(glast >= 0 && !(kog && last >= 0) ? P[glast] : W[last])->team);
        if (ok && kind == K_TITLE && glast < 0)  /* (a title play-off's last three ties: the MLS conference finals) */
            for (int t = nt > 3 ? nt - 3 : 0; t < nt && t < GN; t++) wn_add(0x80 | (pidx & 0x7F), t, row(W[t])->team);
        prev_loser = ok && last >= 0 ? L[last] : -1;
        if (ok && last >= 0 && (s[5] & PO_DECIDER) && DV(W[last]) == DV(L[last]) && PL(W[last]) > PL(L[last])) {
            dswap(W[last], L[last]);            /* (4.2 'decider': the winner up to the loser's place, the moves
                                                   above made by global number) */
            prev_loser = W[last];               /* (the loser: now on the winner's old row) */
            if (GP_PRE && ndsw < 8) { dsw[2 * ndsw] = W[last]; dsw[2 * ndsw + 1] = L[last]; ndsw++; }
        }
        s = r;
    }
#if GP_S3SKIP
    GP_SKIPPO = 0;                              /* (transient: this season end's only) */
#endif
    wn_on = 0;
    x_sfrom = 0; x_lvl = 0;                     /* (4.2: this season end's only - a contest reads the places as they are) */
    if (ss_used && !GP_PRE) SSB->fresh = 0;   /* (this league's stage tables used: next season's are new ones) */
    while (ndsw) { ndsw--; dswap(dsw[2 * ndsw], dsw[2 * ndsw + 1]); }   /* (the preview: the tables as they were) */
#if GP_S7
    if (GP_S7SNAP) GP_S7SNAP(&GP_IN, &GP_EXT, GP_PRE, GP_SEASP);   /* (S7: this struct's crossings for the swap builder) */
#endif
}

/* ---- The playable play-offs (gp_lend .. gp_end in gplay.py): the career club's play-off or play-out is played in
   slot 4 (Season mode: the chosen division's play-off and play-out, slots 4 and 3), as dplay does the Italian ones.
   A contest of the game's type 1 (a national cup, no draw): its team list = the entrants, round 1's ties first (the
   home club / the first leg's first), then the clubs that wait (lib97 byes: gp_bye); every later round is listed
   by gp_perm_c from the spec's member codes; a best-of-three ('series': 3, legs byte 3) is three single-match rounds
   (games 1 and 3 at the better placed's), a game 3 nobody needs is skipped (the contest's rounds - 1). The results:
   gp_rec_c (every decisive match), gp_draw_c (a level tie without penalties: the better placed); the season end
   (gp_played_c) gives gp_season the played winners. The state GP_ST is saved with the career (the engine's save
   block); its season byte makes an old state void. */
enum { KN = 24, KG = 12, KP = 40, KR = 8, KC = 96, MAGIC = 0x4B47, NOC = 0xFF };
enum { LV_BITS_BETTER = 0, LV_BITS_ET_PENS = 0x14, LV_BITS_ET = 0x10, LV_BITS_PENS = 0x04 };
struct gp_srow { u16 team; u8 played, won, drawn, lost, gf, ga; u16 pts; };   /* a place of an early-simulated table */
struct gp_ko {
    u16 magic; u8 season, slot;         /* 'GK' while it runs, its season, slot 4 / 3 */
    u8 cid, pi, kind, n;                /* contest id, play-off index in the country's spec, kind, entrants */
    u8 nrs, ngr, gcur, ntie;            /* spec rounds, game rounds, the game round being played, ties */
    u8 lfile, d1, d2, ldiv;             /* team file, first / last week, the spec's loser_div */
    u8 rs[KR][6];                       /* spec rounds: ties, legs (3 = best of three), host, level, pairing, gap */
    u8 rc[2 * KT];                      /* member codes in spec order */
    u8 gt0[KR + 1];                     /* the first tie of each spec round */
    u8 rb[KG], gsr[KG], gno[KG];        /* game rounds: round byte, spec round, game number in a series */
    u8 gp0[KG + 1];                     /* the first pair of each game round */
    u8 pa[KP], pb[KP], pw[KP], ptie[KP];    /* pairs (list indices, home first), winner, spec tie */
    u8 tw[KT], tl[KT];                  /* spec ties: winner, loser (list indices, NOC) */
    u16 code[KN];                       /* list index -> division * GT + place (GP_IN.t) */
    u8 ient[KN], prio[KN];              /* entrant -> list index; list index -> rank (the better placed: lower) */
    u16 team[KN], pts[KN];
    u8 bye[8];                          /* lib97 bye_find entry: id, 0FFh, clubs, byes, game rounds */
    u8 con[KC];                         /* the contest (type 1) */
};
struct gp_state {
    u16 magic; u8 season, nsim;         /* the early simulations: */
    u8 sdiv[SD], pad[2];
    struct gp_srow srow[SD][GT];
    struct gp_ko ko[2];
    struct gp_dec dec[3];               /* 4.0 ARG: the stage titles decided mid-season (by stage: 0, 1, 2) */
    u8 pend, pweek, pseas, s3wait;      /* 'then_build': play-off pend - 1 to build at the calendar advance from week
                                           pweek on (gp_adv), this season's; s3wait (4.0.5 NZ): bit i = ko[i], a
                                           slot-3 contest built while slot 3 still had days to come (the OFC CL's),
                                           installed at the first calendar advance with slot 3 free (t2_due) */
    u8 rn[KG];                          /* ko[0]'s game rounds' names (rnames index, 0: the game's): pack
                                           'round_names', gplay.py gp_rname (4.0 MLS) */
};
struct gp_state GP_ST;
extern const u8 *GP_CFB;
extern u16 GP_MGR;
struct gp_gs { u8 sdiv[GSD], pad; struct gp_srow srow[GSD][GSR]; };   /* the early tables beyond SD (a group contest:
                                           the Poule's 8 other groups; the engine block's item 'GS') */
struct gp_gs GP_GS;
struct gp_log { u32 tag; u8 seas, stseas, pl_pi, pad; struct gp_ko ko; struct gp_out out;
                u16 top[9]; } GP_LOG;    /* top: the qualifiers' top-9 list after gp_champ (harness: world_title) */
                                        /* the last season end's (harness): its season, the state's, the played one */
/* set by the glue */
u8 GP_HDR[14] = { 0xAD };               /* (gplay.py: the game's Australian cup header, no draw, no away goals) */
const u32 *GP_NM;                       /* the country's names: per play-off dd long, short, record (relative) */
const u8 *GP_RN;                        /* the country's 'round_names': KG bytes per play-off (rnames indices) */
const u8 *GP_TH;                        /* the country's 'then_build': per play-off the next one's index + 1, or 0 */
u8 *GP_DIYP;
u32 GP_K, GP_W, GP_SKIP, GP_RB, GP_ALIVE, GP_LAST;
u16 GP_MGR;                             /* (the career club: CAREERTEAM, set by the glue before the call) */
u16 GP_HUM[64];                         /* S6a (c): the human-controlled clubs (gplay.py gp_hum: a career's club; a world
                                           SEASON's teamControls != 1 clubs, league order), GP_NHUM of them */
u32 GP_NHUM;
u16 GP_A, GP_B;
u8 GP_CID, GP_SEAS, GP_DIV, GP_PT[64], GP_PL[64];
static const struct gp_dec *stage_dec(int w) {   /* w = stage | division << 2: GP_ST.dec[stage] holds the career
                                           club's division's (the only one built mid-season) */
    int k = w & 3;
    return k < 3 && w >> 2 == mgr_div() && GP_ST.magic == MAGIC && GP_ST.dec[k].season == GP_SEAS && GP_ST.dec[k].done
           ? &GP_ST.dec[k] : 0;
}

#define KDV(k, i) ((k)->code[i] / GT)
#define KPL(k, i) ((k)->code[i] % GT)
static int kbetter(const struct gp_ko *k, int a, int b) { return k->prio[a] < k->prio[b]; }

static const u8 *po_at(int pi) {        /* the country's play-off pi in GP_IN.spec */
    const u8 *s = GP_IN.spec;
    for (; s && *s; pi--) {
        if (!pi) return s;
        int n = s[1], nr = s[2];
        const u8 *r = ents_of(s) + 4 * n;
        for (int k = 0; k < nr; k++) r += 6 + 2 * r[0];
        s = r;
    }
    return 0;
}

static int ent_club(const u8 *e, int kind) {    /* an entrant -> its club (division * GT + place), or -1 */
    if (e[0] == 3) return stage_club(e[1], e[3], e[2]);
    if (e[0] == 5) return title_club(e[1], e[2]);
    if (e[0] == 6) return split_seed(e[1], e[3], e[2]);
    if (e[0] == 7) return title_seed(e[1], e[3], e[2]);
    if (e[0] == 8) return team_club(e[2] | e[3] << 8);
    if (e[0]) return -1;
    return place_club(e[1], e[2], kind);
}

static int playable(const u8 *s) {      /* knockouts only (promotion, placement, playout, title, continental), entrants [div, place]
                                           or stage places, members entrants / W / L */
    int n = s[1], nr = s[2], nt = 0;
    const u8 *e = ENTS(s), *r = e + 4 * n;
    if ((KIND(s) < 1 || (KIND(s) > 6 && KIND(s) != K_STAGE) || KIND(s) == 2) || n > KN || nr > KR || nr < 1) return 0;   /* (not 'europe': uefaq's) */
#if GP_S3SKIP
    if (s[0] & PO_EXT)                  /* (S3 step 1: the Serie B play-off's direct_gap only - rank 'level', seeded rounds and
                                           best_first are Serie C's, step 2, not played yet) */
        for (const u8 *x = s + 7; x < s + 7 + s[6]; x += x[0] == E_LEVEL ? 1 : x[0] == E_BEST ? 4 : 2)
            if (x[0] != E_DIRECT) return 0;
#endif
    if (s[5] & PO_SUPER) return 0;      /* (4.0.5: played as the next season's national supercup, sc_step_c) */
    for (int i = 0; i < n; i++)
        if (e[4 * i] != 0 && e[4 * i] != 3 && e[4 * i] != 5 && e[4 * i] != 6) return 0;   /* (5: the Trofeo, built by then_build; 6: Malta's split seeds) */
    for (int k = 0; k < nr; k++) {
        if (r[1] < 1 || r[1] > 3 || (r[1] == 3 && k == nr - 1)) return 0;   /* (no group round; a series: not last) */
        for (int i = 0; i < 2 * r[0]; i++)
            if ((r[6 + i] >= BEST_LOSER && r[6 + i] < 0x80) || (k == 0 && r[6 + i] >= 0x80)) return 0;
#if GP_S3SKIP
        if (r[3] == LV_BETTER_PTS && r[0] != 1) return 0;   /* (decided by the two clubs' points: one tie a round; no shipped
                                           spec has levels 6 / 7 - the Serie B play-out has this level without an extension) */
        if (r[3] == LV_SECOND) return 0;    /* (a seeded round's: step 2) */
#endif
        nt += r[0];
        r += 6 + 2 * r[0];
    }
    return nt <= KT;
}

/* test builds (GPLAY_FORCE=k): the league's own final table too (competitionFileBuffer at GP_CFB, before gp_need): the
   career club's row and place k's swap their figures and places, so the game's own moves see the forced place */
void gp_forcecfb(void) {
    u8 *d = (u8 *)GP_CFB;
    int n = *(u16 *)(d + 0x31), m = -1;
    if (!GP_FORCE || GP_FORCE > n) return;
    for (int j = 0; j < n; j++)
        if (*(u16 *)(d + 0x12D + 2 * (*(u16 *)(d + 0x6D + 2 * j) / 0x12)) == GP_IN.mgr) m = j;
    if (m < 0 || m == GP_FORCE - 1) return;
    u16 *pa = (u16 *)(d + 0x6D + 2 * m), *pb = (u16 *)(d + 0x6D + 2 * (GP_FORCE - 1));
    u16 *ra = (u16 *)(d + *pa + 0x2B7), *rb = (u16 *)(d + *pb + 0x2B7), x;
    for (int i = 0; i < 7; i++) { x = ra[i]; ra[i] = rb[i]; rb[i] = x; }
#if GP_FORCE                            /* (GP_SP*: gplay.py's defines; host compiles without them, check.sh) */
    if (*(u16 *)(d + GP_SPST) == GP_SPMAGIC) {  /* (a split league: the rows' groups and 'points before rounding' too -
                                                   sp_sort's partition re-sorts by them at the season end, MC 10/11) */
        u8 *g = d + GP_SPST + GP_SPGRP, ia = *pa / 0x12, ib = *pb / 0x12, y = g[ia];
        u16 *q = (u16 *)(d + GP_SPST + GP_SPPRE);
        g[ia] = g[ib]; g[ib] = y;
        x = q[ia]; q[ia] = q[ib]; q[ib] = x;
    }
#endif
    x = *pa; *pa = *pb; *pb = x;
}

/* a group contest (the Poule Scudetto): a title whose rounds are g groups of m entrants (one meeting count), then
   optional ranking rounds, then knockout rounds (single / two legs) whose first takes q placings; played as the game's
   type-2 contest in slot 3 (groups -> q qualifiers: the winners, then the best runners-up as the game's best thirds;
   then its knockout stages). o: stages for the contest header, or 0 (a check). */
struct t2s { u8 g, m, meet, nk, q, kt[4], kb[4]; };
static int t2_shape(const u8 *s, struct t2s *o) {
    struct t2s x;
    int n = s[1], nr = s[2], k = 0, ent = 0;
    const u8 *r = s + 6 + 4 * n;
    if (s[0] != K_TITLE || nr < 2) return 0;
    for (int i = 0; i < n; i++) if (s[6 + 4 * i] != 0 && s[6 + 4 * i] != 8) return 0;   /* ([div, place], a club: NZ) */
    x.g = 0; x.m = 0; x.meet = 0; x.nk = 0; x.q = 0;
    for (; k < nr && (r[1] & 0x80) && (r[1] & 0x7F); k++) {      /* the groups */
        if (x.g && (r[0] != x.m || (r[1] & 0x7F) != x.meet)) return 0;
        x.m = r[0]; x.meet = r[1] & 0x7F; x.g++;
        for (int i = 0; i < r[0]; i++) if (r[6 + i] != ent++) return 0;   /* (entrants in order, group by group) */
        r += 6 + 2 * r[0];
    }
    for (; k < nr && r[1] == 0x80; k++) r += 6 + 2 * r[0];        /* (ranking rounds: the game's best runners-up) */
    for (; k < nr; k++) {                                          /* the knockout stages */
        if ((r[1] & 0x80) || r[1] < 1 || r[1] > 2 || x.nk >= 4) return 0;
        if (!x.nk) x.q = 2 * r[0];
        x.kt[x.nk] = r[0];
        x.kb[x.nk++] = (r[1] == 2 ? 0x80 : 0x01) | (r[3] == LV_PENS ? 0x04 : r[3] == LV_ET_PENS ? 0x14 :
                                                    r[3] == LV_ET_BETTER ? 0x10 : 0);
        r += 6 + 2 * r[0];
    }
    if (x.g < 1 || !x.nk || ent != n || x.q < x.g || x.q > 2 * x.g || x.g * x.m > KN) return 0;
    if (o) *o = x;
    return 1;
}

/* 4.0.5 NZ (the championship built into slot 3 at the league's end while WESTERN SPRINGS still had the OFC Champions
   League final there: the game plays every slot-3 calendar day for the contest in slot 3 - the OFC's days ran our group
   two days ahead, its last two days had no match, PARTITA for ever): gp_install leaves such a ko waiting (s3wait);
   gp_adv, once slot 3 has no day to come, takes it: its weeks moved to start after the current one, installed. */
extern u32 GP_WK;
u32 t2_defer(u32 i) { GP_ST.s3wait |= (u8)(1 << i); return 0; }
#ifndef GP_S3DEFER
#define GP_S3DEFER 0                    /* (test builds, GPLAY_S3DEFER=1: the group's slot 3 taken once, as by a late
                                           OFC day - rc17's MiSTer career) */
#endif
static u8 t2_forced;
u32 t2_force(void) {                    /* gp_install: 1 = treat slot 3 as busy now (GP_S3DEFER, once a season) */
    if (!GP_S3DEFER || t2_forced == (u8)GP_SEAS) return 0;
    t2_forced = (u8)GP_SEAS;
    return 1;
}
u32 t2_waiting(u32 i) { return GP_ST.s3wait >> i & 1; }
u32 t2_due(void) {
    u32 m = 0;
    for (int i = 0; i < 2; i++) {
        if (!(GP_ST.s3wait >> i & 1)) continue;
        GP_ST.s3wait &= (u8)~(1 << i);
        struct gp_ko *k = &GP_ST.ko[i];
        if (k->magic != MAGIC || k->season != GP_SEAS || k->slot != 3) continue;
        int d = (int)GP_WK + 1 - k->d1;
        if (d > 0) {
            k->d1 = (u8)(k->d1 + d);
            k->d2 = k->d2 + d > 255 ? 255 : (u8)(k->d2 + d);
            k->con[3] = k->d1; k->con[4] = k->d2;
        }
        m |= 1u << i;
    }
    return m;
}

/* the career club's league has ended (GP_IN.t[mdiv] its table, mgr, week, gtype): the play-offs it plays (pi[]) and
   the divisions to simulate now for their entrants (sim[]); returns how many */
/* A type-2 group contest of ours (id FE: the Poule, NZ's Championship) at its group stage's end, before the game picks
   the qualifiers (cseg_8A2CE: each group's sorted list +6Dh in order): the B teams that may never qualify (SEC_TAB
   without play-offs: NZ's A-League reserves, 'can not qualify for the Grand Final') move to the end of their group's
   list, the others keep their order (their places: the next club qualifies). con = diyFileBufferCopy (its header),
   diy = DIY_competitionStart, sel = selTeamsPtr. */
void t2_pre(const u8 *con, u8 *diy, u32 sel) {
    int g = *(const u16 *)(diy + 0x4F), m = *(const u16 *)(diy + 0x51);
#if GP_GOUT                                 /* (GPLAY_GOUT test builds only: the career club last of its group in the
                                               game's other group stages - NZ: out of the OFC Champions League early) */
    if (con[0] != 0xFE) {
        for (int gi = 0; gi < g && gi * m < 64; gi++) {
            u16 *l = (u16 *)(diy + 0x6D) + gi * m;
            for (int j = 0; j + 1 < m && j < 24; j++) {
                const u8 *rec = (const u8 *)(*(const u32 *)(diy + l[j] + 0x2B3) + sel);
                if (IS_MGR(rec[0] | rec[1] << 8)) {
                    u16 x = l[j];
                    for (int k = j; k + 1 < m; k++) l[k] = l[k + 1];
                    l[m - 1] = x;
                    break;
                }
            }
        }
    }
#endif
    if (con[0] != 0xFE) return;
    for (int gi = 0; gi < g && gi * m < 64; gi++) {
        u16 *l = (u16 *)(diy + 0x6D) + gi * m, keep[24], out[24];
        int nk = 0, no = 0;
        for (int j = 0; j < m && j < 24; j++) {
            const u8 *rec = (const u8 *)(*(const u32 *)(diy + l[j] + 0x2B3) + sel);
            const u8 *e;
            int team = rec[0] | rec[1] << 8;
            if (sec_find(-1, team, &e) && !(e[5] & SEC_PO)) out[no++] = l[j]; else keep[nk++] = l[j];
        }
        for (int j = 0; j < nk; j++) l[j] = keep[j];
        for (int j = 0; j < no; j++) l[nk + j] = out[j];
    }
}

static int gap_done(const u8 *s) {      /* 4.2: a one-round play-off whose ties are all decided by its gap on the final
                                           table (no tie to play: gp_season's 'too far apart') - not the club's contest */
    const u8 *e = ENTS(s), *r = e + 4 * s[1];
#if GP_S3SKIP
    if (s[0] & PO_EXT)                  /* (S3: direct_gap - entrant 0 wins, nothing to play, if g+ points ahead of entrant 1) */
        for (const u8 *x = s + 7; x < s + 7 + s[6]; x += x[0] == E_LEVEL ? 1 : x[0] == E_BEST ? 4 : 2)
            if (x[0] == E_DIRECT) {
                int a = ent_club(e, KIND(s)), b = ent_club(e + 4, KIND(s));
                if (a >= 0 && b >= 0 && (int)row(a)->pts - (int)row(b)->pts >= x[1]) return 1;
            }
#endif
    if (s[2] != 1 || !r[5] || (r[1] & 0x80)) return 0;
    for (int i = 0; i < r[0]; i++) {
        int a = r[6 + 2 * i], b = r[7 + 2 * i];
        if (a >= s[1] || b >= s[1]) return 0;
        a = ent_club(e + 4 * a, KIND(s)); b = ent_club(e + 4 * b, KIND(s));
        if (a < 0 || b < 0) return 0;
        int d = (int)row(a)->pts - (int)row(b)->pts;
        if (d < r[5] && -d < r[5]) return 0;
    }
    return 1;
}

u32 gp_need(void) {
    int m = -1, d0 = GP_IN.mdiv, cnt = 0, ns = 0;
    ss_set(GP_IN.mgr);                          /* (the career club's league's bank) */
    GP_IN.pi[0] = GP_IN.pi[1] = NOC;
    for (int j = 0; j < SDX; j++) GP_IN.sim[j] = NOC;
    GP_ST.nsim = 0;
    for (int k = 0; k < GP_IN.n[d0]; k++) if (GP_IN.t[d0][k].team == GP_IN.mgr) m = k;
    if (GP_FORCE) { int f = gp_force(); if (f >= 0) m = f; }
    if (GP_IN.gtype == 4 && m < 0) return 0;
    for (int pi = 0; cnt < (GP_IN.gtype == 4 ? 1 : 2); pi++) {
        const u8 *s = po_at(pi), *e = s ? ENTS(s) : 0;
        if (!s) break;
        if ((!playable(s) && !(GP_IN.gtype == 4 && t2_shape(s, 0))) || KIND(s) == K_STAGE || gap_done(s)) continue;
                                                    /* (stage titles: gp_build, mid-season; a group contest: careers) */
        int in = 0, all = 1;
        for (int i = 0; i < s[1]; i++) {
            int c = ent_club(e + 4 * i, KIND(s));
            if (c == d0 * GT + m) in = 1;
            if (e[4 * i + 1] != d0) all = 0;
        }
        if (GP_IN.gtype == 4 ? !in : !all) continue;    /* (Season: the division's own play-offs, no other loaded) */
        int ok = 1;
        for (int i = 0; i < s[1] && ok; i++) {          /* the other divisions: simulated now (at most SDX) */
            int d = e[4 * i + 1], j = 0;
            if (d == d0) continue;
            while (j < ns && GP_IN.sim[j] != d) j++;
            if (j == ns) { if (ns < (t2_shape(s, 0) ? SDX : SD)) GP_IN.sim[ns++] = d; else ok = 0; }
        }
        if (ok) GP_IN.pi[cnt++] = pi;
    }
    return cnt;
}

/* early simulation of division GP_DIV (DIY at GP_DIYP): its rows into the state, place by place */
void gp_simkeep(void) {
    const u8 *d = GP_DIYP;
    int n = *(const u16 *)(d + 0x31), j = GP_ST.nsim, nr = j < SD ? GT : GSR;
    if (j >= SDX) return;
    if (j < SD) GP_ST.sdiv[j] = GP_DIV; else GP_GS.sdiv[j - SD] = GP_DIV;
    GP_ST.nsim = j + 1;
    for (int k = 0; k < nr; k++) {
        struct gp_srow *s = j < SD ? &GP_ST.srow[j][k] : &GP_GS.srow[j - SD][k];
        s->team = 0;
        if (k >= n) continue;
        int off = *(const u16 *)(d + 0x6D + 2 * k), i = off / 0x12;
        const u16 *r = (const u16 *)(d + off + 0x2B7);
        s->team = *(const u16 *)(d + 0x12D + 2 * i);
        s->played = r[0]; s->won = r[1]; s->drawn = r[2]; s->lost = r[3]; s->gf = r[4]; s->ga = r[5]; s->pts = r[6];
    }
}

/* the season end simulated division GP_DIV again (DIY at GP_DIYP): an early one gets its results back */
void gp_restore(void) {
    u8 *d = GP_DIYP;
    int n = *(u16 *)(d + 0x31);
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS) return;
    for (int j = 0; j < GP_ST.nsim && j < SDX; j++) {
        if ((j < SD ? GP_ST.sdiv[j] : GP_GS.sdiv[j - SD]) != GP_DIV) continue;
        const struct gp_srow *s = j < SD ? GP_ST.srow[j] : GP_GS.srow[j - SD];
        for (int k = 0; k < n && k < (j < SD ? GT : GSR); k++)
            for (int i = 0; i < n; i++)
                if (*(u16 *)(d + 0x12D + 2 * i) == s[k].team) {
                    u16 *r = (u16 *)(d + 0x2B7 + 0x12 * i);
                    r[0] = s[k].played; r[1] = s[k].won; r[2] = s[k].drawn; r[3] = s[k].lost;
                    r[4] = s[k].gf; r[5] = s[k].ga; r[6] = s[k].pts;
                    *(u16 *)(d + 0x6D + 2 * k) = 0x12 * i;
                }
    }
}

static int member(const struct gp_ko *k, int c) {      /* a member code -> list index, or -1 (not decided yet) */
    if (c < BEST_LOSER) return c < KN && k->ient[c] != NOC ? k->ient[c] : -1;
    if (c < 0x80) return -1;            /* (group placings, the best loser: not played here) */
    int t = c & 0x3F;
    if (t >= k->ntie) return -1;
    int v = c & 0x40 ? k->tl[t] : k->tw[t];
    return v == NOC ? -1 : v;
}

static void resolve(struct gp_ko *k) {  /* ties decided by their pairs: the last one's winner, a series' 2 wins */
    for (int t = 0; t < k->ntie; t++) {
        int w = NOC, c[2] = { NOC, NOC }, x[2] = { 0, 0 };
        if (k->tw[t] != NOC) continue;
        for (int p = 0; p < k->gp0[k->gcur + 1]; p++) {
            if (k->ptie[p] != t || k->pw[p] == NOC) continue;
            if (c[0] == NOC) { c[0] = k->pa[p]; c[1] = k->pb[p]; }
            x[k->pw[p] == c[1]]++;
            w = k->pw[p];
        }
        int sr = 0;
        while (sr + 1 < k->nrs && k->gt0[sr + 1] <= t) sr++;
        if (k->rs[sr][1] == 3) w = x[0] >= 2 ? c[0] : x[1] >= 2 ? c[1] : NOC;
        if (w == NOC) continue;
        k->tw[t] = w;
        k->tl[t] = w == c[0] ? c[1] : c[0];
    }
}

static u32 hseed(const struct gp_ko *k, int g) {
    u32 h = g * 7919u + k->pi;
    for (int i = 0; i < k->n; i++) h = h * 31 + k->team[i];
    return h;
}

/* game round g's pairs (from k->gp0[g]); returns how many (0: nothing to play) */
static int presim;                      /* a career club that waits in round 1 (MLS: seeds 1-7 v the wild cards): the
                                           first round's ties simulated at the build, the contest starts after them */
static int build_game(struct gp_ko *k, int g) {
    int r = k->gsr[g], ties = k->rs[r][0], legs = k->rs[r][1], host = k->rs[r][2] & 0x3F, pairing = k->rs[r][4];
    int t0 = k->gt0[r], np = k->gp0[g], mem[2 * KT];
    rng = hseed(k, g);
    if (k->gno[g]) {                    /* a series' game 2 / 3: the ties not decided yet */
        for (int i = 0; i < ties; i++) {
            int t = t0 + i, a = NOC, b = NOC;
            if (k->tw[t] != NOC) continue;
            for (int p = 0; p < np; p++) if (k->ptie[p] == t) { a = k->pa[p]; b = k->pb[p]; }
            if (a == NOC || np >= KP) continue;
            if (kbetter(k, b, a)) { int x = a; a = b; b = x; }      /* (a = the better placed) */
            k->pa[np] = k->gno[g] == 1 ? b : a; k->pb[np] = k->gno[g] == 1 ? a : b;
            k->pw[np] = NOC; k->ptie[np++] = t;
        }
        k->gp0[g + 1] = np;
        return np - k->gp0[g];
    }
    for (int i = 0; i < 2 * ties; i++) {
        mem[i] = member(k, k->rc[2 * t0 + i]);
        if (mem[i] < 0) return 0;
    }
    if (pairing & 0x80) {               /* a draw: the first p members shuffled */
        int pn = (pairing & 0x7F) <= 2 * ties ? pairing & 0x7F : 2 * ties;
        for (int i = pn - 1; i > 0; i--) { int j = below(i + 1), x = mem[i]; mem[i] = mem[j]; mem[j] = x; }
    } else if (pairing) {               /* best v worst: sorted, the worst first */
        int pn = pairing <= 2 * ties ? pairing : 2 * ties, tmp[2 * KT];
        for (int i = 1; i < pn; i++) {
            int x = mem[i], j = i;
            while (j > 0 && kbetter(k, x, mem[j - 1])) { mem[j] = mem[j - 1]; j--; }
            mem[j] = x;
        }
        for (int i = 0; i < pn / 2; i++) { tmp[2 * i] = mem[pn - 1 - i]; tmp[2 * i + 1] = mem[i]; }
        for (int i = 0; i < pn; i++) mem[i] = tmp[i];
    }
    for (int i = 0; i < ties; i++) {
        int t = t0 + i, a = mem[2 * i], b = mem[2 * i + 1], gap = k->rs[r][5], fin = k->rs[r][2] & HOST_UEFA_FINAL;
        if (k->tw[t] != NOC) continue;  /* (decided by the gap rule) */
        if (g == 0 && presim && k->code[a] != k->code[b]) {   /* (the career club waits: simulated now) */
            int ca = k->code[a], cb = k->code[b], lv = k->rs[r][3];
            int w = legs == 3 ? series(ca, cb, lv) : tie(ca, cb, legs, host, lv);
            k->tw[t] = w == ca ? a : b; k->tl[t] = w == ca ? b : a;
            continue;
        }
        if (k->code[a] == k->code[b]) { k->tw[t] = k->tl[t] = a; continue; }   /* (skip_if_same: one CLUB twice
                                           (two entrants, e.g. the Trofeo's R1 = R2): no tie) */
        if (g == 0 && (gap || fin)) {
            int d = (int)k->pts[a] - (int)k->pts[b];
            if ((gap && (d >= gap || -d >= gap)) || (fin && uefa_fin(k->team[a], k->team[b]))) { k->tw[t] = kbetter(k, a, b) ? a : b; k->tl[t] = k->tw[t] == a ? b : a; continue; }
        }
        int bt = kbetter(k, a, b) ? a : b, wo = bt == a ? b : a;
        if (legs == 3 || host == HOST_NEUTRAL) { a = bt; b = wo; }   /* (no neutral grounds: the better placed's) */
        else if (host == HOST_BETTER) { a = legs == 2 ? wo : bt; b = legs == 2 ? bt : wo; }
        else if (host == HOST_DRAWN && below(2)) { int x = a; a = b; b = x; }
        if (np >= KP) break;
        k->pa[np] = a; k->pb[np] = b; k->pw[np] = NOC; k->ptie[np++] = t;
    }
#if GP_S3SKIP
    if (k->rs[r][3] == LV_BETTER_PTS && np > k->gp0[g]) {   /* (S3: level -> the better placed, unless the two are level on
                                           points: then e.t. + penalties - the round byte; one tie a round, extension specs) */
        int pa = k->pa[k->gp0[g]], pb = k->pb[k->gp0[g]];
        k->rb[g] = (u8)((k->rb[g] & ~0x14) | (k->pts[pa] == k->pts[pb] ? LV_BITS_ET_PENS : 0));
    }
#endif
    k->gp0[g + 1] = np;
    return np - k->gp0[g];
}

static u8 rbyte(int legs, int level) {  /* (away goals: the contest's header, gp_lend_c) */
    static const u8 lv[6] = { LV_BITS_BETTER, LV_BITS_ET_PENS, LV_BITS_ET, LV_BITS_PENS, LV_BITS_ET_PENS,
                              LV_BITS_BETTER };
#if GP_S3SKIP
    return (legs == 2 ? 0x80 : 0x01) | (level >= 6 ? LV_BITS_BETTER : lv[level]);   /* (S3: better_pts / second: the better
                                           placed; build_game adds e.t. + penalties when level on points) */
#else
    return (legs == 2 ? 0x80 : 0x01) | lv[level < 6 ? level : 1];
#endif
}

/* a group contest (t2_shape) as the game's type 2 in slot 3: the entrants in group order, the Champions Cup's header
   with its stages (groups of m, q qualifiers; the knockout stages), weeks after the league's last; its result: the
   last decisive match's clubs (gp_rec_c: tw[0] / tl[0], the final's) */
u8 GP_HDR2[0x27] = { 0xAD };            /* (gplay.py: the Champions Cup's first 0x27 bytes) */
#define KT2(k) ((k)->bye[7])            /* (a type-2 contest: bye[] is unused there) */
#define GF(k) ((k)->bye[6])             /* 4.0.5 NZ, a type-2 contest's Grand Final (gf_step_c): */
enum { GF_WAIT = 1, GF_ON = 2, GF_DONE = 3, K_GF = 11 };   /* the group under way, the final built (ko[1]), decided */
static int ko_t2(struct gp_ko *k, const u8 *s, int pi, int cid, const struct t2s *x) {
    const u8 *e = s + 6;
    int n = s[1], me = 0, len = 0x27, days = x->meet * (x->m & 1 ? x->m : x->m - 1);
    k->magic = 0;
    k->slot = 3; k->cid = cid; k->pi = pi; k->kind = s[0]; k->n = n; k->nrs = s[2]; k->ldiv = s[4];
    k->ntie = 1; k->ngr = 0; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int i = 0; i < 8; i++) k->bye[i] = 0;
    KT2(k) = 1;
    *(u32 *)k->bye = GP_NM[3 * pi + 2]; /* (its record line's name: a type-2 contest has no byes) */
    int pm[GN];
    pot_perm(s, pm);                        /* (4.0.1: a drawn pot; else the identity) */
    for (int i = 0; i < n; i++) {
        int c = ent_club(e + 4 * pm[i], s[0]);
        if (c < 0) return 0;
        k->ient[i] = i; k->code[i] = c; k->prio[i] = c > 255 ? 255 : c;
        k->team[i] = row(c)->team; k->pts[i] = row(c)->pts;
        me |= k->team[i] == GP_IN.mgr;
    }
#ifndef GP_GFIDX
#define GP_GFIDX 0
#endif
#if GP_GFIDX                            /* (test builds, GPLAY_GFIDX=i+1: the career club at index i of the group - its
                                           rest day: oddtables' circle, 11 clubs: index 2 rests in the last round) */
    for (int i = 0; i < n; i++)
        if (k->team[i] == GP_IN.mgr && i != GP_GFIDX - 1 && GP_GFIDX <= n) {
            int j = GP_GFIDX - 1;
            u16 c = k->code[j], t = k->team[j], q = k->pts[j];
            u8 r = k->prio[j];
            k->code[j] = k->code[i]; k->team[j] = k->team[i]; k->pts[j] = k->pts[i]; k->prio[j] = k->prio[i];
            k->code[i] = c; k->team[i] = t; k->pts[i] = q; k->prio[i] = r;
            break;
        }
#endif
    int gf = x->g == 1 && x->nk == 1 && x->kt[0] == 1;   /* 4.0.5 NZ: one group, then a one-match final (the
                                           game's type-2 knockout after a single group never put the career match
                                           in the calendar): the group alone here, the Grand Final ours (gf_step_c) */
    if (!gf) for (int i = 0; i < x->nk; i++) days += (x->kb[i] & 0x80) ? 2 : 1;
    k->lfile = k->team[0] & 0xFF;
    k->d1 = GP_IN.week + 1; k->d2 = GP_IN.week + days + 1 > 255 ? 255 : GP_IN.week + days + 1;
    u8 *c = k->con;
    for (int i = 0; i < 0x27; i++) c[i] = GP_HDR2[i];
    c[0] = cid; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2;
    c[5] = 0x22; c[7] = 0x28; c[8] = 1; c[9] = 0; c[10] = 0;     /* names at +27h, the list at +2Fh, no seeding, no
                                                                   away goals */
    c[11] = x->meet;
    u8 st[0x14];
    int ns = 0;
    int nk = gf ? 0 : x->nk;
    st[ns++] = 1 + nk; st[ns++] = n;
    st[ns++] = x->g; st[ns++] = x->m; st[ns++] = gf ? 0 : x->q;
    for (int i = 0; i < nk; i++) { st[ns++] = 0; st[ns++] = 2 * x->kt[i]; st[ns++] = x->kt[i]; }
    for (int i = 0; i < 0x14; i++) c[0x0E + i] = i < ns ? st[i] : 0;
    for (int i = 0; i < 5; i++) c[0x22 + i] = i == 0 || i > nk ? 0 : x->kb[i - 1];
    GF(k) = gf ? GF_WAIT : 0;
    if (gf) {                           /* (the final's legs and level for gf_step_c: rs[] is unused in a type 2) */
        u8 b = x->kb[0];
        k->rs[0][1] = b & 0x80 ? 2 : 1;
        k->rs[0][3] = (b & 0x14) == 0x14 ? LV_ET_PENS : b & 0x04 ? LV_PENS : b & 0x10 ? LV_ET_BETTER : LV_BETTER;
    }
    for (int i = 0; i < 8; i++) c[len + i] = ((const u8 *)GP_NM)[12 * pi + i];
    len += 8;
    for (int j = 0; j < n; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    if (GP_IN.gtype == 4 && !me) { k->slot = 0; k->cid = 0; return 0; }
    return 1;
}

/* a contest for play-off pi in slot `slot` (id cid): k filled, 1 if there is something to play */
static int ko_build(struct gp_ko *k, int pi, int slot, int cid) {
    const u8 *s = po_at(pi), *e = ENTS(s), *r = e + 4 * s[1];
    int n = s[1];
    struct t2s x;
    by_rec = s[5] & 2;
    if (GP_IN.gtype == 4 && t2_shape(s, &x)) return ko_t2(k, s, pi, 0xFE, &x);   /* (career: slot 3, id FE) */
    k->bye[5] = k->bye[6] = k->bye[7] = 0;              /* (KT2: a knockout) */
    k->magic = 0;
    k->slot = slot; k->cid = cid; k->pi = pi; k->kind = KIND(s); k->n = n; k->nrs = s[2]; k->ldiv = s[4];
    k->ntie = 0; k->ngr = 0; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int j = 0; j < k->nrs; j++) {
        for (int i = 0; i < 6; i++) k->rs[j][i] = r[i];
        k->gt0[j] = k->ntie;
        for (int i = 0; i < 2 * r[0]; i++) k->rc[2 * k->ntie + i] = r[6 + i];
        k->ntie += r[0];
        int games = r[1] == 3 ? 3 : 1;
        for (int g = 0; g < games && k->ngr < KG; g++) {
            k->gsr[k->ngr] = j; k->gno[k->ngr] = g;
            k->rb[k->ngr++] = rbyte(r[1] == 3 ? 1 : r[1], r[3]);
        }
        r += 6 + 2 * r[0];
    }
    k->gt0[k->nrs] = k->ntie;
    /* the list: round 1's members in tie order, then the others in entrant order */
    int pm[GN];
    pot_perm(s, pm);                        /* (4.0.1: a drawn pot; else the identity) */
    for (int i = 0; i < n; i++) {
        int c = ent_club(e + 4 * pm[i], KIND(s));
        if (c < 0) return 0;
        k->ient[i] = i; k->code[i] = c;
        k->prio[i] = e[4 * pm[i]] == 3 ? e[4 * pm[i] + 2] - 1 : c > 255 ? 255 : c;   /* (stage entrants: the stage place) */
        k->team[i] = row(c)->team; k->pts[i] = row(c)->pts;
    }
    if (by_rec)                             /* (the better record hosts: the ranks by it) */
        for (int i = 0; i < n; i++) {
            k->prio[i] = 0;
            for (int j = 0; j < n; j++) if (j != i && better(k->code[j], k->code[i])) k->prio[i]++;
        }
    presim = 0;
    if (GP_IN.gtype == 4) {
        int in = 0, in0 = 0;
        for (int i = 0; i < n; i++) in |= k->team[i] == GP_IN.mgr;
        for (int i = 0; i < k->rs[0][0]; i++) {   /* (a round-1 tie of the club with itself - Malta's split seeds,
                                               skip_if_same - is no match: the club waits) */
            int a = k->rc[2 * i], b = k->rc[2 * i + 1];
            if (a < n && b < n && (k->team[a] == GP_IN.mgr || k->team[b] == GP_IN.mgr) && k->code[a] != k->code[b])
                in0 = 1;
        }
        presim = in && !in0;
    }
    k->gp0[0] = 0;
    int g0 = 0, np0 = build_game(k, 0);     /* (entrant indices for now: the list order next) */
    while (np0 <= 0 && g0 + 1 < k->ngr && k->gno[g0 + 1] == 0) np0 = build_game(k, ++g0);   /* (a round decided
                                               without a match, skip_if_same / gap: the first with one is round 1) */
    if (np0 <= 0) {                         /* (every tie decided by the gap: nothing to play, the results kept) */
        for (int i = 0; i < n; i++) k->team[i] = row(k->code[i])->team;
        k->slot = 0; k->cid = 0; k->season = GP_SEAS; k->magic = MAGIC;
        return 0;
    }
    u8 used[KN], order[KN], pr[KN];
    u16 cd[KN];
    for (int i = 0; i < n; i++) { cd[i] = k->code[i]; pr[i] = k->prio[i]; }
    int m = 0;
    for (int i = 0; i < n; i++) used[i] = 0;
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++) {
        order[m++] = k->pa[p]; used[k->pa[p]] = 1;
        order[m++] = k->pb[p]; used[k->pb[p]] = 1;
    }
    int np1 = m, me0 = GP_IN.gtype != 4;
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++)
        me0 |= k->team[k->pa[p]] == GP_IN.mgr || k->team[k->pb[p]] == GP_IN.mgr;
    u8 need[KN];                        /* (a built contest lists only the clubs that can still play: round g0's, and
                                           the entrants / decided ties' clubs later rounds name; the Trofeo's R2 = R1
                                           twice was a 3-club contest whose match the career calendar lost) */
    for (int i = 0; i < n; i++) need[i] = !me0;
    for (int t = 0; t < k->ntie; t++)   /* (a decided tie's clubs stay: its result is kept, gp_played_c / gp_sack) */
        if (k->tw[t] != NOC) { need[k->tw[t]] = 1; if (k->tl[t] != NOC) need[k->tl[t]] = 1; }
    for (int t = k->gt0[k->gsr[g0] + 1 <= k->nrs ? k->gsr[g0] + 1 : k->nrs]; t < k->ntie; t++)
        for (int x = 0; x < 2; x++) {
            int c = k->rc[2 * t + x];
            if (c < BEST_LOSER && c < n) need[c] = 1;
            else if (c >= 0x80 && (c & 0x3F) < k->ntie) {
                int v = c & 0x40 ? k->tl[c & 0x3F] : k->tw[c & 0x3F];
                if (v != NOC) need[v] = 1;
            }
        }
    for (int i = 0; i < n; i++) if (!used[i] && need[i]) order[m++] = i;
    for (int i = 0; i < KN; i++) k->ient[i] = NOC;
    n = m;                              /* (the contest's clubs) */
    k->n = n;
    for (int j = 0; j < n; j++) {       /* list index j = entrant order[j] */
        int i = order[j];
        k->ient[i] = j;
        k->code[j] = cd[i]; k->prio[j] = pr[i];
        const struct gp_row *w = row(cd[i]);
        k->team[j] = w->team; k->pts[j] = w->pts;
    }
    for (int p = 0; p < k->gp0[g0 + 1]; p++) { k->pa[p] = k->ient[k->pa[p]]; k->pb[p] = k->ient[k->pb[p]]; }
    for (int t = 0; t < k->ntie; t++) {         /* (gap-decided ties, entrant indices too) */
        if (k->tw[t] != NOC) {
            k->tw[t] = k->ient[k->tw[t]]; k->tl[t] = k->tl[t] != NOC ? k->ient[k->tl[t]] : NOC;
        }
    }
    int me = 0;                         /* a career: the club must play round 1 (a slot-4 contest without it stops the
                                           season); else no contest, its gap-decided tie kept (gp_sack, gp_played_c) */
    for (int p = k->gp0[g0]; p < k->gp0[g0 + 1]; p++)
        me |= k->team[k->pa[p]] == GP_IN.mgr || k->team[k->pb[p]] == GP_IN.mgr;
    int days = 0;
    for (int g = g0; g < k->ngr; g++) days += (k->rb[g] & 0xC0) == 0x80 ? 2 : 1;
    k->gcur = g0;
    k->bye[5] = GP_TH ? GP_TH[pi] : 0;  /* (pack 'then_build': the play-off built when this one ends, index + 1) */
    if (k == &GP_ST.ko[0])              /* (its round names: the slot-4 screens, gp_rname) */
        for (int i = 0; i < KG; i++) GP_ST.rn[i] = GP_RN ? GP_RN[KG * pi + i] : 0;
    k->lfile = k->team[0] & 0xFF;
    k->d1 = GP_IN.week + 1; k->d2 = GP_IN.week + days > 255 ? 255 : GP_IN.week + days;
    k->bye[0] = cid; k->bye[1] = 0xFF; k->bye[2] = n; k->bye[3] = n - np1; k->bye[4] = k->ngr - g0;
    /* the contest: the game's header, round bytes, names, the team words */
    u8 *c = k->con;
    int len = 14;
    for (int i = 0; i < 14; i++) c[i] = GP_HDR[i];
    c[0] = cid; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2; c[10] = n;
    for (int j = 0; j < k->nrs; j++)    /* away goals (levels away_pens / away_better): the whole contest's */
        if (k->rs[j][3] == LV_AWAY_PENS || k->rs[j][3] == LV_AWAY_BETTER) c[13] = 0;
    for (int g = g0; g < k->ngr; g++) c[len++] = k->rb[g];
    c[len++] = 0;
    c[5] = len - 5;
    c[7] = len + 8 - 7;
    for (int i = 0; i < 8; i++) c[len + i] = ((const u8 *)GP_NM)[12 * pi + i];
    len += 8;
    for (int j = 0; j < n; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    if (GP_IN.gtype == 4 && !me) { k->slot = 0; k->cid = 0; return 0; }
    return 1;
}

/* after gp_need and the early simulations: the contests (ko[0]: slot 4, id FE; Season's second: slot 3, FC) */
u32 gp_lend_c(void) {
    u32 built = 0;
    if (GP_IN.mgr != 0xFFFF)                    /* (gp_build_c's trivial table title runs us with no career club: */
        ss_set(GP_IN.mgr);                      /*  its ss_set chose the league's bank; 0xFFFF picked bank 0, not */
                                                /*  written - the title went to row 0 of the reset table, 4.0.1 rc3) */
    GP_ST.magic = MAGIC;
    GP_ST.season = GP_SEAS;
    for (int i = 0; i < 2; i++) {
        GP_ST.ko[i].magic = 0;
        if (GP_IN.pi[i] != NOC && ko_build(&GP_ST.ko[i], GP_IN.pi[i], i ? 3 : 4, i ? 0xFC : 0xFE)) built |= 1 << i;
    }
    return built;
}

/* a knockout not built (the career club not in round 1): every tie simulated now with gplay's tie rules (4.0's
   gp_build: the champion = team[tw[last tie]], the runner-up team[tl[...]] at once) */
static void ko_sim(struct gp_ko *k) {
    int g = 0;
    for (;;) {
        for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++) {
            if (k->pw[p] != NOC) continue;
            int r = k->gsr[g], a = k->code[k->pa[p]], b = k->code[k->pb[p]];
            int w = tie(a, b, k->rs[r][1] == 2 ? 2 : 1, HOST_LISTED, k->rs[r][3]);
            k->pw[p] = w == a ? k->pa[p] : k->pb[p];
        }
        k->gcur = g;
        resolve(k);
        while (++g < k->ngr && build_game(k, g) <= 0)
            ;
        if (g >= k->ngr) break;
    }
}

/* gp_build (mid-season): play-off GP_BPIC of the spec into slot 4 when its entrants' tables are captured */
u32 GP_BPIC;
static u16 team_glob(u16 team) {        /* a team word -> its global number (the captured tables), 0xFFFF */
    for (int d = 0; d < GP_IN.nd && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d]; k++) if (GP_IN.t[d][k].team == team) return GP_IN.t[d][k].glob;
    return 0xFFFF;
}

static int club_res(struct gp_ko *k, u16 mgr);
static void stage_done(const struct gp_ko *k) {   /* a stage title's knockout decided: GP_ST.dec[stage] */
    const u8 *s = k->magic == MAGIC && k->season == GP_SEAS && k->ntie ? po_at(k->pi) : 0;
    int t = k->ntie - 1;
    if (!s || s[0] != K_STAGE || (s[3] & 3) >= 3 || s[3] >> 2 != mgr_div() || k->tw[t] == NOC) return;
    struct gp_dec *x = &GP_ST.dec[s[3] & 3];
    int w = k->tw[t], l = k->tl[t];
    x->season = GP_SEAS; x->done = 1;
    x->team[0] = k->team[w]; x->glob[0] = team_glob(k->team[w]);
    x->team[1] = l != NOC ? k->team[l] : 0xFFFF; x->glob[1] = l != NOC ? team_glob(k->team[l]) : 0xFFFF;
    x->pad[0] = (u8)club_res((struct gp_ko *)k, GP_IN.mgr);   /* (the career club's result: its season record line) */
    x->pad[1] = k->pi + 1;
}

/* the SEASON WINNERS page (winners.py): a title's source GP_WNSRC ('S' / 'D' / 'K' / 'T', stage or tie << 8, play-off pi
   << 16; 'T': an intermediate title, tie st's winner) -> its
   winner's team word this season (GP_SEAS); 0xFFFF: not decided yet, but being played (the play-off's contest is
   this season's GP_ST.ko); 0xFFFE: nothing of it this season (a play-off the career club is not in: decided at the
   season end). 'S': stage table st's 1st (GP_SS.r[st] written this season: ARG's annual table); 'D': a stage title
   decided mid-season (GP_ST.dec[stage] of play-off pi), else as 'K': play-off pi's last tie in GP_ST.ko (the career
   club's, played; not a group contest). The page names a club only when it is one of the viewed league's rows. */
u32 GP_WNSRC;
u32 GP_WNFILE;                          /* (4.0.1: the viewed league's team file, DIY +12Dh: its stage bank) */
static u32 wn_double(int rule) {        /* 4.0.2 'Q': a title_seed play-off without the career club's contest - its
                                           champion once one club has won both tournaments (A = C: no play-off), from
                                           the viewed league's bank as title_seed reads it (A = table 0, C = table 3
                                           rule 1 / 1 rule 2); else 0FFFEh */
    const struct gp_ss *b = ss_view(GP_WNFILE);
    int c = rule == 1 ? 3 : 1;
    if ((rule == 1 || rule == 2) && b && (b->fresh & 1) && (b->fresh >> c & 1) && b->n[0] && b->n[c]
        && b->r[0][0].team == b->r[c][0].team)
        return b->r[0][0].team;
    return 0xFFFE;
}
static u32 cf_last1(void);              /* (4.0.5: CF_ST, defined with it below) */
static u32 sc_wn(void);                 /* (4.0.5: the supercup's winner, below) */
u32 gp_wn_c(void) {
    int t = GP_WNSRC & 0xFF, st = GP_WNSRC >> 8 & 0xFF, pi = GP_WNSRC >> 16 & 0xFF;
    if (GP_WNSRC >> 24 && t == 'M') {   /* (4.0.1: the division the career club played in: team | division << 16) */
        if (WN_ST.magic != WN_MAGIC || (u8)(WN_ST.season + 1) != GP_SEAS) return 0xFFFE;
        return wn_find('M', 0, 0);
    }
    if (GP_WNSRC >> 24 && t == 'E') {   /* (4.0.5 a league with no WIN entry, winners.py's fallback line: the last
                                           season's 1st of the career club's level, from CF_ST's places) */
        return cf_last1();
    }
    if (GP_WNSRC >> 24) {               /* (4.0.1 the last season: WN_ST's entry 'K' pi, or 'L' division st) */
        int ty = t == 'K' || t == 'D' || t == 'Q' ? 'K' : t == 'T' ? 0x80 | (pi & 0x7F) : 'L', ix = ty == 'K' ? pi : st;
        if (WN_ST.magic != WN_MAGIC || (u8)(WN_ST.season + 1) != GP_SEAS) return 0xFFFE;
        return wn_find(ty, ix, 0);
    }
    if (t == 'U') return sc_wn();       /* (4.0.5: the national supercup, sc_done's winner) */
    if (t == 'S') {
        const struct gp_ss *b = ss_view(GP_WNFILE);
        return b && st < SS_N && (b->fresh >> st & 1) && b->n[st] ? b->r[st][0].team : 0xFFFE;
    }
    if (GP_ST.magic != MAGIC) return t == 'Q' ? wn_double(st) : 0xFFFE;
    if (t == 'T') {                     /* (tie st of play-off pi, the career club's: an intermediate title) */
        for (int j = 0; j < 2; j++) {
            const struct gp_ko *k = &GP_ST.ko[j];
            if (k->magic != MAGIC || k->season != GP_SEAS || k->pi != pi || k->bye[7] || st >= KT) continue;
            return k->tw[st] != NOC ? k->team[k->tw[st]] : 0xFFFF;
        }
        return 0xFFFE;
    }
    if (t == 'D' && st < 3) {
        const struct gp_dec *x = &GP_ST.dec[st];
        if (x->season == GP_SEAS && x->done && x->pad[1] == pi + 1) return x->team[0];
    }
    for (int j = 0; j < 2; j++) {
        const struct gp_ko *k = &GP_ST.ko[j];
        if (k->magic == MAGIC && k->season == GP_SEAS && k->pi == pi && k->bye[7] && GF(k))   /* (4.0.5 NZ: a Grand
                                           Final's - ours: decided, else IN CORSO) */
            return GF(k) == GF_DONE && k->tw[0] != NOC ? k->team[k->tw[0]] : 0xFFFF;
        if (k->magic == MAGIC && k->season == GP_SEAS && k->pi == pi && k->bye[7])
            return 0xFFFC;              /* (a group contest of ours - the Poule: its winner is the game's, slot 3) */
        if (k->magic != MAGIC || k->season != GP_SEAS || k->pi != pi || !k->ntie || k->bye[7]) continue;
        int w = k->tw[k->ntie - 1];
        return w != NOC ? k->team[w] : 0xFFFF;   /* (running: IN CORSO - 4.0's a41b1e4 decides it even once the
                                                   career club is out: rc10's interim no-line rule is gone) */
    }
    {                                   /* (rc19: a play-off the career club is not in - previewed at the league's end) */
        int ty = t == 'K' || t == 'D' || t == 'Q' ? 'K' : t == 'T' ? 0x80 | (pi & 0x7F) : 0;
        u32 w = ty ? wn_find(ty, ty == 'K' ? pi : st, 1) : 0xFFFE;
        if (w != 0xFFFE) return w;
    }
    return t == 'Q' ? wn_double(st) : 0xFFFE;
}

u32 GP_WK;                              /* (the glue: the current calendar entry's week) */

/* ---- The Coppa Italia Serie D (cupd.py: CD_TAB; state CD_ST, the engine block's item 'CD'). At every calendar
   advance (gp_adv -> cd_step_c), each round whose week is next (or past): the career club's tie is built in slot 4
   (a 1-tie contest, its result back through gp_rec_c -> cd_done), every other tie decided now (the world's first
   season: its real result when known; else 55% to the home club). Hosts: listed, drawn, or 'alternate' (the club
   away in its previous tie hosts; both home / both away: drawn). A 'draw' round pairs the previous round's winners
   at random. Later seasons (the data session's entry rule, LND art. 1-2 in the game's terms): the season's Serie D
   clubs of the team file (CD_DT); the preliminary round = the first 2 x (N - 128) of an entry order (the new
   arrivals: relegated from Serie C, promoted from the pool; then the clubs of each group from the bottom of last
   season's table up), the others enter at the first round; both rounds paired within a group where possible, else
   at random; from the 3rd round on a fixed bracket (tie k = the winners of ties 2k, 2k + 1), the round records'
   weeks, hosts and drawn semi-finals as the table's. */
enum { K_CUPD = 9, CDT = 168, CDP = 41, CD1 = 64 };
enum { K_SC = 10 };                     /* (4.0.5: a national supercup tie, sc_step_c at the file's end) */
struct gp_ko;
#if GP_X3                               /* 4.2 X3 (MC 16/11, CONVENTIONS 23): sc_done in obj3 (gplay3.c), bound by gplay.py x3_patch */
#ifndef GP_DATA_SECTION
#if defined(__MACH__)                   /* (a native host build - mach-o has no ".data" section name; the exe is always ELF) */
#define GP_DATA_SECTION
#else
#define GP_DATA_SECTION __attribute__((section(".data")))
#endif
#endif
void (*GP_SCDONE)(u16 w) GP_DATA_SECTION;
#define SC_DONE(w) GP_SCDONE(w)
#else
static void sc_done(u16 w);
#define SC_DONE(w) sc_done(w)
#endif
static u32 sc_rline(void);              /* (4.0.5: gp_rlines_c's supercup line) */
#if GP_PORT
u32 (*GP_PRLINE)(u32 k) __attribute__((section(".data")));   /* (4.2 the port's trophies: the k-th record line the career club
                                           won this season, STR_BASE-relative, 0 = no more - fpmlv.c fpv_rline_c; 0 = none bound) */
static void port_rlines(void);
#endif
static u32 usc_rline(void);             /* (4.0.6: the UEFA Super Cup's) */
static void rl_put(void);
int sc_busy(void);                      /* (4.0.5: the slot-4 guard) */
#if GP_FRND
int slot4_busy(void);                   /* (4.2: + the friendlies) */
#else
#define slot4_busy sc_busy
#endif   /* (CDP: preliminary ties at most, CDP + 2 x CD1 - 1 <= CDT) */
struct cd_state { u16 magic; u8 season, round, built, bt, drawn, pad; u8 res[CDT], home[CDT]; u8 sd[4];
                  u8 ent[256];          /* cd_season (the season end): per ordinal of the file, the entry order's key
                                           for the season to come (0 not in Serie D, 1 a new arrival, 2 + places from
                                           the bottom of last season's group, 40h unknown) */
                  u8 efresh, gen_on, np, nfc, nfp, ranked, nrk, nrc;   /* (ent written; this season's bracket
                                           generated; its preliminary ties; the new arrivals from Serie C, from the
                                           pool; ent holds the season's final places: cd_rank, its clubs placed,
                                           its calls) */
                  u16 gen[2 * (CDP + CD1)]; };   /* (the generated rounds 0-1: tie t's sides gen[2t], gen[2t + 1]) */
struct cd_state CD_ST;
const u32 CD_STSZ = sizeof(struct cd_state);
const u8 *GP_CDT;                       /* (the glue: CD_TAB of the running world, or 0) */
u32 GP_CDFORCE;                         /* (the glue: CD_FORCE test builds, the career club wins its Coppa D ties) */
u16 *GP_CDS1;                           /* 4.0 (the glue): the Coppa D's slot-1 contest team list (64 words), 0 = none */
const u8 *GP_CDD;                       /* (its CD_DT: db first Serie D division, groups; dw global base; [GP_CD2 builds:
                                           dw base2, dw ord2]; 256 x db base division, FFh none) */
/* S7-G (MC 11/11): a league over two team files (gplay.py: globnum.exe_split) - CD_DT's file B rows from ord2 on
   take run 2 (global base2 + ordinal - ord2); without GP_CD2 (every dormant build) the readers expand to today's
   tokens */
#ifndef GP_CD2
#define GP_CD2 0
#endif
#if GP_CD2
#define CD_O 8
#define CD_G(dt, gb, i) ((i) >= ((dt)[6] | (dt)[7] << 8) ? ((dt)[4] | (dt)[5] << 8) + (i) - ((dt)[6] | (dt)[7] << 8) \
                         : (gb) + (i))
#else
#define CD_O 4
#define CD_G(dt, gb, i) (gb + i)
#endif
const u32 *GP_CDNM;                     /* (its names: dd long, short) */
u32 GP_CDFIRST;                         /* (the career's first season in the world) */
#define CDREC(r) (GP_CDT + 4 + 8 * (r))
#define CDTIE(t) (GP_CDT + 4 + 8 * GP_CDT[1] + 6 * (t))
#define CD_REF(i) ((u16)((i) << 8 | 0xFF))      /* (a tie as a side: a team word's file is never 255) */
#define CD_ISREF(v) (((v) & 0xFF) == 0xFF)
#define CD_DRAWN 0xFEFF
extern const s8 *GP_SLT;

static int cd_gen(void) { return !GP_CDFIRST && CD_ST.gen_on; }
static int cd_n(int r) {                /* round r's ties */
    if (!cd_gen()) return CDREC(r)[4];
    return r ? 1 << (GP_CDT[1] - 1 - r) : CD_ST.np;
}
static int cd_first(int r) {            /* round r's first tie */
    if (!cd_gen()) return CDREC(r)[6] | CDREC(r)[7] << 8;
    int f = 0;
    for (int i = 0; i < r; i++) f += cd_n(i);
    return f;
}
static int cd_round(int t) {            /* the round tie t belongs to */
    int r = 0;
    while (r + 1 < GP_CDT[1] && t >= cd_first(r + 1)) r++;
    return r;
}
static u16 cd_raw(int t, int sd) {      /* tie t's side sd as listed: a team word, CD_REF(a tie), CD_DRAWN */
    if (!cd_gen()) { const u8 *x = CDTIE(t); return x[2 * sd] | x[2 * sd + 1] << 8; }
    int r = cd_round(t);
    if (r < 2) return CD_ST.gen[2 * t + sd];
    if (CDREC(r)[5] & 1) return CD_DRAWN;
    return CD_REF(cd_first(r - 1) + 2 * (t - cd_first(r)) + sd);
}

static u16 cd_side(int t, int sd) {     /* tie t's side sd (0 a, 1 b): a team word, 0 (off-file), FFFFh undecided */
    u16 v = cd_raw(t, sd);
    if (!CD_ISREF(v)) return v;
    int i = v >> 8;
    if (v == CD_DRAWN) {                  /* (a drawn round: its k-th tie = the previous round's sd[2k], sd[2k+1]) */
        int first = cd_first(cd_round(t));   /* (4.0.5 rc9: tie t's round - not CD_ST.round, the round under way:
                                                once the final was on, its semis read sd[] at a negative index ->
                                                the preliminary tie 0's winner won the cup every season) */
        i = CD_ST.sd[2 * (t - first) + sd];
    }
    if (i >= CDT || !CD_ST.res[i]) return 0xFFFF;
    return cd_side(i, CD_ST.res[i] - 1);
}

static int cd_hosted(int t, u16 club) { /* the club hosted tie t (two legs: the first leg) */
    int h = CD_ST.home[t];
    return cd_side(t, h) == club;
}

static void ko_one(struct gp_ko *k, u16 home, u16 away, int w1, int w2, int legs, int kind, int level, int lfile,
                   const u8 *names) {   /* a one-tie contest in slot 4 (the Coppa D's; 4.0.5 also the supercups') */
    k->magic = 0;
    k->slot = 4; k->cid = 0xFE; k->pi = 0xFF; k->kind = kind; k->n = 2; k->nrs = 1; k->ldiv = 0;
    k->ntie = 1; k->ngr = 1; k->gcur = 0;
    for (int i = 0; i < KT; i++) k->tw[i] = k->tl[i] = NOC;
    for (int i = 0; i < 8; i++) k->bye[i] = 0;
    k->rs[0][0] = 1; k->rs[0][1] = legs; k->rs[0][2] = HOST_LISTED; k->rs[0][3] = level; k->rs[0][4] = 0;
    k->rs[0][5] = 0;
    k->rc[0] = 0; k->rc[1] = 1; k->gt0[0] = 0; k->gt0[1] = 1;
    k->rb[0] = rbyte(legs, level); k->gsr[0] = 0; k->gno[0] = 0;
    k->gp0[0] = 0; k->gp0[1] = 1; k->pa[0] = 0; k->pb[0] = 1; k->pw[0] = NOC; k->ptie[0] = 0;
    k->team[0] = home; k->team[1] = away; k->code[0] = 0; k->code[1] = 1; k->prio[0] = 0; k->prio[1] = 1;
    k->ient[0] = 0; k->ient[1] = 1; k->pts[0] = k->pts[1] = 0;
    k->lfile = lfile;
    k->d1 = w1 > (int)GP_WK ? w1 : GP_WK + 1;
    k->d2 = legs == 2 ? (w2 > k->d1 ? w2 : k->d1 + 1) : k->d1;
    k->bye[0] = 0xFE; k->bye[1] = 0xFF; k->bye[2] = 2; k->bye[3] = 0; k->bye[4] = 1;
    u8 *c = k->con;
    int len = 14;
    for (int i = 0; i < 14; i++) c[i] = GP_HDR[i];
    c[0] = 0xFE; c[2] = k->lfile; c[3] = k->d1; c[4] = k->d2; c[10] = 2;
    c[len++] = k->rb[0];
    c[len++] = 0;
    c[5] = len - 5;
    c[7] = len + 8 - 7;
    for (int i = 0; i < 8; i++) c[len + i] = names[i];
    len += 8;
    for (int j = 0; j < 2; j++) { c[len++] = k->team[j]; c[len++] = k->team[j] >> 8; }
    k->season = GP_SEAS;
    k->magic = MAGIC;
    GP_ST.magic = MAGIC;
    GP_ST.season = GP_SEAS;
}

/* 4.0.5 NZ, the National League's Grand Final: a type-2 contest of one group whose spec ends with a one-tie final
   (ko_t2: GF_WAIT, the group alone in slot 3; the game's knockout after a single group never had the career match in
   the calendar). The final is ours, in ko[1] (slot 4, id FE: gp_ours_c skips the group contest once it is over):
   - gf_place_c (gp_install, right after the group's slot-3 install): a placeholder final of the career club in slot
     4 the week after the group's last day - the calendar's next entry after the group (else the season ended there:
     no calendar advance to build the final at);
   - gf_step_c (gp_adv, slot 3 free, every group row played): the group's final table from the working DIY (its last
     day was the event just done; the slot buffer is not written back yet: its rows read 0 played) (points,
     goal difference, goals scored, then the list's order - the game's group order) gives the top two clubs that may
     qualify (a B team without play-offs, SEC_TAB - NZ's A-League reserves 'can not qualify for the Grand Final' - is
     skipped); the higher placed hosts. The career club in it: the real final into ko[1] by ko_one (the spec's legs
     and level: one match, extra time + penalties), installed over the placeholder from the next week. Not in it:
     decided now, the host winning 3 in 5 (as a simulated supercup final, seeded by the season), the placeholder's
     days dropped;
   - gf_done (gp_rec_c): the winner / loser into the group contest's tw[0] / tl[0] (its champion / runner-up for the
     season end, VINCITORI, the record). */
const u8 *GP_S3;                        /* (the glue: the game's working DIY - the group's last day just played) */
const u8 *GP_S3B;                       /* (the glue: slot 3's own 443h buffer - rc17) */
u32 GP_GFT;                             /* (harness trace: 1 built, 2 simulated, 3 placeholder, 0x80 | why not) */
static int kidx(const struct gp_ko *k, u16 team);
static void gf_one(struct gp_ko *f, const struct gp_ko *g, u16 home, u16 away, int w) {
    ko_one(f, home, away, w, w + 1, g->rs[0][1], K_GF, g->rs[0][3], g->lfile, g->con + 0x27);
    f->pi = g->pi;                      /* (gp_fixload_c: its names from this exe's tables, as the group's) */
}
static int gf_live(const struct gp_ko *k) {
    return GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS && k->magic == MAGIC && k->season == GP_SEAS && KT2(k);
}
void gf_done(struct gp_ko *f) {         /* gp_rec_c: the Grand Final decided */
    struct gp_ko *g = &GP_ST.ko[0];
    if (f->tw[0] == NOC || !gf_live(g) || GF(g) != GF_ON) return;
    g->tw[0] = kidx(g, f->team[f->tw[0]]);
    g->tl[0] = kidx(g, f->team[f->tl[0]]);
    GF(g) = GF_DONE;
}
u32 gf_place_c(void) {                  /* the group just installed in slot 3: 1 = a placeholder final in ko[1] */
    struct gp_ko *g = &GP_ST.ko[0];
    if (!gf_live(g) || GF(g) != GF_WAIT || g->slot != 3) return 0;
    int me = kidx(g, GP_MGR);
    if (me == NOC) return 0;
    gf_one(&GP_ST.ko[1], g, GP_MGR, g->team[me ? 0 : 1], g->d2 + 1);
    GP_GFT = 3;
    return 1;
}
void gf_hide_c(u8 *cal, u32 cur) {     /* gp_install, after a slot-4 install: the placeholder final's days with no
                                           career match (calendar byte 5 = 0): the fixture list shows the round alone,
                                           as the game's undrawn cup rounds - no pairing before the group is over */
    const struct gp_ko *g = &GP_ST.ko[0], *f = &GP_ST.ko[1];
    if (!gf_live(g) || GF(g) != GF_WAIT || f->magic != MAGIC || f->kind != K_GF || f->slot != 4) return;
    u16 cnt = *(const u16 *)(cal - 4);
    u8 *e = cal;
    for (u32 i = 0; i < cnt; i++) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) >= cur && e[0] == 4) {
            e[5] = 0;
            if (!(GP_ST.s3wait & 1)) e[6] = 0;  /* (4.0.6: the group installed - gf_place_c's placeholder, not
                                           gf_anchor_c's - no career day either: byte 6, cseg_8EC2B's flag. With the
                                           club resting in the group's last round the menu offered PARTITA for it,
                                           the final decided inside that day - a phantom final without the club. Now
                                           FINISH SEASON: gplay.py gp_fin plays the days to the decision, back to
                                           PARTITA if the club is in the final) */
        }
        e += len;
    }
}
u32 gp_hrest_c(u8 *cal, u32 cur, u32 ki) {  /* S6a (A), gp_install after a slot-4 install in a world SEASON: the
                                           human clubs (GP_HUM) with a match left in ko ki; none -> the
                                           slot-4 days from the current entry on lose the 'human, no match' flag
                                           (byte 6 FFh, cseg_8BC06 - cseg_8EC2B counts it, PARTITA's loop hunted
                                           for a day that never comes) */
    const struct gp_ko *k = &GP_ST.ko[ki < 2 ? ki : 0];
    if (k->magic != MAGIC || KT2(k)) return 1;
    u32 c = 0, last = k->nrs ? k->gt0[k->nrs - 1] : 0;
    for (u32 h = 0; h < GP_NHUM && h < 64; h++) {  /* (a match left: in the bracket, no tie lost, no tie of the last
                                           spec round won - a bye into a later round counts: the 3-club Final Four's
                                           top seed waits for the final, MC 16/11) */
        int me = kidx(k, GP_HUM[h]), left = me != NOC;
        for (int t = 0; t < k->ntie && left; t++)
            if (k->tw[t] != NOC && k->tw[t] != k->tl[t] && (k->tl[t] == me || (k->tw[t] == me && (u32)t >= last))) left = 0;
        c += left;
    }
    if (c) return c;
    u16 cnt = *(const u16 *)(cal - 4);
    u8 *e = cal;
    for (u32 i = 0; i < cnt; i++) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) >= cur && e[0] == 4 && e[6] == 0xFF) e[6] = 0;
        e += len;
    }
    return 0;
}
#ifndef GP_GFREST
#define GP_GFREST 0                     /* (test builds, GPLAY_GFREST=1: the placeholder shown at once - gf_unhide_c's
                                           path, as when the career club rests in the group's last round) */
#endif
u32 gf_unhide_c(u8 *cal, u32 cur) {    /* rc18 (Davide's MiSTer, rc17): gp_adv - the Grand Final still to be built and
                                           no career-club day left before it (its rest day the group's last round): the
                                           hidden placeholder (gf_hide_c) is the career club's day again (byte 5 = 1),
                                           else the game offered FINISH SEASON (cseg_8EC2B), the group's last round and
                                           the final never played. Its pairing shows from now until the final is built
                                           (the week after the group's last day) */
    const struct gp_ko *g = &GP_ST.ko[0], *f = &GP_ST.ko[1];
    if (!GP_GFREST) return 0;           /* (4.0.6: gf_hide_c's placeholder is no career day - gp_fin's FINISH SEASON
                                           plays to the decision; the test builds' pairing shown at once only) */
    if (!gf_live(g) || GF(g) != GF_WAIT || f->magic != MAGIC || f->kind != K_GF || f->slot != 4) return 0;
    u16 cnt = *(const u16 *)(cal - 4);
    u8 *e = cal, *ph = 0;
    int other = 0;
    for (u32 i = 0; i < cnt; i++) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) >= cur) {    /* (the current entry - the next day - counts as one to come) */
            if (e[0] == 4) { if (!ph) ph = e; }
            else if (e[5]) other = 1;
        }
        e += len;
    }
    if (!ph || ph[5] || (other && !GP_GFREST)) return 0;
    ph[5] = 1;
    GP_GFT = 6;
    return 1;
}
u32 gf_anchor_c(const u8 *cal, u32 cur) {   /* gp_install: the group waits for slot 3 (t2_defer: the OFC's days still to
                                           come, the career club maybe out of it) - the placeholder final in ko[1] the
                                           week after slot 3's last day: a day of the career club still to come (the
                                           game's cseg_8EC2B: else FINISH SEASON, the group and the final simulated
                                           inside it), replaced once the group is installed (t2_due, gf_place_c) */
    struct gp_ko *g = &GP_ST.ko[0];
    if (!gf_live(g) || GF(g) != GF_WAIT || g->slot != 3) return 0;
    int me = kidx(g, GP_MGR);
    if (me == NOC) return 0;
    u16 cnt = *(const u16 *)(cal - 4);
    const u8 *e = cal;
    int w = (int)GP_WK;
    for (u32 i = 0; i < cnt; i++) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) > cur && e[0] == 3 && e[1] > w) w = e[1];
        e += len;
    }
    if (w + 2 > 255) return 0;
    gf_one(&GP_ST.ko[1], g, GP_MGR, g->team[me ? 0 : 1], w + 1);
    GP_GFT = 5;
    return 1;
}
u32 gf_step_c(void) {                   /* the calendar advance (slot 3 free): 2 = the final built into ko[1], 4 = the
                                           placeholder's days to drop (decided without the career club), else 0 */
    struct gp_ko *k = &GP_ST.ko[0];
    if (!gf_live(k) || GF(k) != GF_WAIT || (GP_ST.s3wait & 1) || (!GP_S3 && !GP_S3B) || (int)GP_WK < k->d1) return 0;
    int n = k->n, meet = k->con[11] ? k->con[11] : 1, ord[KN], m = 0;
    u16 tm[KN];
    const u8 *d = 0;
    for (int b = 0; b < 2 && !d; b++) {     /* (rc17: the working DIY after a '- RISULTATO -' day; after a match
                                           played for real it may hold another contest - then slot 3's own buffer,
                                           written back: the one whose table is the whole group played) */
        const u8 *c = b ? GP_S3B : GP_S3;
        if (!c) continue;
        if (*(const u16 *)(c + 0x4F) != 1 || *(const u16 *)(c + 0x51) != n) { GP_GFT = 0x84; continue; }
        int ok = 1;
        for (int j = 0; j < n && ok; j++) { /* (the rows: every club's group played to the end, all of them ours) */
            int o = *(const u16 *)(c + 0x6D + 2 * j);
            tm[j] = *(const u16 *)(c + 0x12D + 2 * (o / 0x12));
            if (kidx(k, tm[j]) == NOC) { GP_GFT = 0x81; ok = 0; }
            else if (*(const u16 *)(c + o + 0x2B7) < meet * (n - 1)) { GP_GFT = 0x82; ok = 0; }
            ord[j] = j;
        }
        if (ok) d = c;
    }
    if (!d) return 0;
    u16 f[2];
    for (int i = 0; i < n && m < 2; i++) {
        const u8 *e;
        if (sec_find(-1, tm[ord[i]], &e) && !(e[5] & SEC_PO)) continue;   /* (a B team that may not qualify) */
        if (GP_GFFORCE == 1 && tm[ord[i]] == GP_MGR) continue;
        f[m++] = tm[ord[i]];
    }
    if (m < 2) { GP_GFT = 0x83; return 0; }
    if (GP_FORCE && !GP_GFFORCE && f[0] != GP_MGR && f[1] != GP_MGR && kidx(k, GP_MGR) != NOC) {   /* (test builds: the career
                                           club in the final, as its host) */
        f[1] = f[0]; f[0] = GP_MGR;
    }
    if (GP_GFFORCE == 2 && kidx(k, GP_MGR) != NOC && f[0] != GP_MGR) {   /* (test builds: the career club the host, as
                                           the group's winner - rc17's MiSTer case) */
        f[1] = f[0];                    /* (2nd -> swapped; out of the two -> it replaces the 2nd) */
        f[0] = GP_MGR;
    }
    struct gp_ko *fk = &GP_ST.ko[1];
    if (!IS_MGR(f[0]) && !IS_MGR(f[1])) {       /* (the career club not in it: 4.1.1, the placeholder's day is the
                                           real final, the two finalists, the game's simulated match deciding it -
                                           gp_rec_c -> gf_done, as the career club's own final; before: decided here,
                                           the host winning 3 in 5, and the placeholder's career club v the group's
                                           other club played as a computer match - a phantom match, an injury. The
                                           placeholder stays installed (ko[1] live, its days kept - rc19): gf_drop_c
                                           rewrites its calendar entry and slot 4's teams) */
        if (fk->magic != MAGIC || fk->kind != K_GF || fk->slot != 4) {
            rng = GP_SEAS * 7919u + 0x4E5A;     /* (no placeholder in slot 4: decided now, as before) */
            int w = below(5) < 3 ? 0 : 1;
            k->tw[0] = kidx(k, f[w]); k->tl[0] = kidx(k, f[1 - w]);
            GF(k) = GF_DONE;
            fk->magic = 0;
            GP_GFT = 2;
            return 4;
        }
        fk->team[0] = f[0]; fk->team[1] = f[1];
        fk->tw[0] = fk->tl[0] = fk->pw[0] = NOC;
        GF(k) = GF_ON;
        GP_GFT = 8;
        return 4;
    }
    gf_one(fk, k, f[0], f[1], GP_WK + 1);
    GF(k) = GF_ON;
    GP_GFT = 1;
    return 2;
}
u32 gf_drop_c(u8 *cal, u32 cur) {       /* rc20 (Panchina's natural NZ season, WESTERN SPRINGS 3rd of the group): gp_gf
                                           after gf_step_c's 4 - the Grand Final decided without the career club, often
                                           at the end of the club's rest day (the group's last round), inside the game's
                                           day: the placeholder's days stay (removing one under the game's day loop left
                                           the squad screen for ever - rc19's gp_calold removal) and are no longer the
                                           club's: byte 6 = 0 (the career-day flag cseg_8EC2B counts - p6's host test;
                                           byte 4 != 0 entries it skips), byte 5 = 0 (gf_hide_c's). Returns 1 when no
                                           career day is left from the cursor on: the glue sets the menu's word (FINISH
                                           SEASON), as cseg_8EC2B would.
                                           4.1.1 (gf_step_c's GP_GFT 8: ko[1] the real final): the slot-4 entries'
                                           pairing (+12 / +14) the finalists; GP_GFT 9 -> the glue loads them into
                                           slot 4 (cseg_8ECAE's tail, as gp_install), the game simulates their match */
    const struct gp_ko *f = &GP_ST.ko[1];
    int real = GP_GFT == 8 && f->magic == MAGIC && f->kind == K_GF && f->slot == 4;
    u16 cnt = *(const u16 *)(cal - 4);
    u8 *e = cal;
    int ahead = 0;
    for (u32 i = 0; i < cnt; i++) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) >= cur) {
            if (e[0] == 4) {
                e[5] = 0; e[6] = 0;
                if (real && len >= 16) { *(u16 *)(e + 12) = f->team[0]; *(u16 *)(e + 14) = f->team[1]; }
            }
            else if (!e[4] && e[6]) ahead = 1;
        }
        e += len;
    }
    GP_GFT = real ? 9 : 7;
    return !ahead;
}
static void cd_ko(struct gp_ko *k, u16 home, u16 away, int w1, int w2, int legs) {
    ko_one(k, home, away, w1, w2, legs, K_CUPD, LV_PENS, GP_CDT[2], (const u8 *)GP_CDNM);
}

/* The league's end (gp_end_c, the final tables in GP_IN): each Serie D club's place from the bottom of its group
   into CD_ST.ent (saved with the career: a save before CONTINUA's season end loses GP_IN). */
static void cd_rank(void) {
    const u8 *dt = GP_CDD;
    int df = dt[0], dc = dt[1], lf = GP_CDT[2], n = 0;
    if (CD_ST.nrc < 255) CD_ST.nrc++;
    for (int d = df; d < df + dc && d < GD; d++)        /* (GP_IN: the league just ended - another country's: none) */
        for (int k = 0; k < GP_IN.n[d] && k < GT; k++) if ((GP_IN.t[d][k].team & 0xFF) == lf) n++;
    if (!n) return;
    for (int i = 0; i < 256; i++) CD_ST.ent[i] = 0;
    for (int d = df; d < df + dc && d < GD; d++)
        for (int k = 0; k < GP_IN.n[d] && k < GT; k++) {
            u16 t = GP_IN.t[d][k].team;
            if ((t & 0xFF) == lf) CD_ST.ent[t >> 8] = 2 + (GP_IN.n[d] - 1 - k);
        }
    CD_ST.nrk = n;
    CD_ST.ranked = 1;
    CD_ST.efresh = 0;
}

/* The season end (pgroups' pg_fix, after the moves: slt = this season's divisions, copy = the next one's): the entry
   order's keys of the next season's Serie D clubs (CD_ST.ent). tab = CD_TAB, dt = CD_DT. */
enum { CD_RF = 8 };                     /* (= the RI section's RF: the off-file pools' files) */
extern u8 RI_SWAPPED[CD_RF][32];
extern u8 RI_FILES_FILE[CD_RF];
void cd_season(const u8 *tab, const u8 *dt, const s8 *slt, const s8 *copy, int world) {
    if (tab[0] != world) return;
    int df = dt[0], dc = dt[1], gb = dt[2] | dt[3] << 8, lf = tab[2], moved = 0, fi = -1;
    for (int i = 0; i < 256; i++) if (dt[CD_O + i] != 0xFF && copy[CD_G(dt, gb, i)] != slt[CD_G(dt, gb, i)]) moved = 1;
    if (!moved) return;                 /* (InitializeNewSeason at a career's start: the world's real bracket) */
    for (int k = 0; k < CD_RF; k++) if (RI_FILES_FILE[k] == lf) fi = k;
    CD_ST.nfc = CD_ST.nfp = 0;
    for (int i = 0; i < 256; i++) {
        int b = dt[CD_O + i], e = 0;
        if (b != 0xFF) {
            int nd = b + copy[CD_G(dt, gb, i)], od = b + slt[CD_G(dt, gb, i)];
            if (nd >= df && nd < df + dc) {
                if (fi >= 0 && (RI_SWAPPED[fi][i >> 3] & 1 << (i & 7))) {
                    e = 1;              /* (a new arrival: a new identity from the pool) */
                    CD_ST.nfp++;
                } else if (od < df || od >= df + dc) {
                    e = 1;              /* (relegated from Serie C) */
                    CD_ST.nfc++;
                }
                else            /* (an old club: its place from the bottom, cd_rank) */
                    e = CD_ST.ranked && CD_ST.ent[i] >= 2 ? CD_ST.ent[i] : 0x40;
            }
        }
        CD_ST.ent[i] = e;
    }
    CD_ST.efresh = 1;
    CD_ST.ranked = 0;
}

static void cd_pair(u16 *side, u8 *sg, int m, int at) {   /* m sides -> ties from gen[at]: shuffled, each paired
                                                                   with the next of its group, else the next */
    for (int i = m - 1; i > 0; i--) {
        int j = below(i + 1); u16 x = side[i]; u8 y = sg[i];
        side[i] = side[j]; side[j] = x; sg[i] = sg[j]; sg[j] = y;
    }
    u8 used[256];
    for (int i = 0; i < m; i++) used[i] = 0;
    for (int i = 0; i < m; i++) {
        if (used[i]) continue;
        int j = -1;
        for (int k = i + 1; k < m && j < 0; k++) if (!used[k] && sg[k] != 0xFF && sg[k] == sg[i]) j = k;
        for (int k = i + 1; k < m && j < 0; k++) if (!used[k]) j = k;
        used[i] = 1;
        CD_ST.gen[at++] = side[i];
        if (j >= 0) { used[j] = 1; CD_ST.gen[at++] = side[j]; } else CD_ST.gen[at++] = 0;
    }
}

#ifndef GP_DATA_SECTION
#if defined(__MACH__)                   /* (a native host build - mach-o has no ".data" section name; the exe is always ELF) */
#define GP_DATA_SECTION
#else
#define GP_DATA_SECTION __attribute__((section(".data")))      /* (host tests build gplay.c natively: -DGP_DATA_SECTION=) */
#endif
#endif
/* 4.2 S2 knockouts (MC 14/11, 42-cdkn): rounds 0-1 by the engine's sr_kn (cdkn.c, obj4 band CDKN; cdkn.py sets it in
   CD_KN builds; 0 = today's cd_make). ord / grp / key as cd_make's loop leaves them (key >> 8: the entry key); 1 = CD_ST
   written (cdkn.c reads GP_CDT / GP_SEAS / CD_ST itself: the fewest bytes here). */
int (*GP_CDKN)(const u8 *ord, const u8 *grp, const u16 *key, int n) GP_DATA_SECTION;
static void cd_make(void) {             /* a later season's rounds 0-1 (CD_ST.gen) */
    const u8 *dt = GP_CDD;
    int df = dt[0], dc = dt[1], gb = dt[2] | dt[3] << 8, lf = GP_CDT[2], n = 0;
    u8 ord[256], grp[256];
    u16 key[256], side[256];
    rng = GP_SEAS * 104729u + 17;
    for (int i = 0; i < 256; i++) {
        int b = dt[CD_O + i];
        if (b == 0xFF || !GP_SLT) continue;
        int dv = b + GP_SLT[CD_G(dt, gb, i)];
        if (dv < df || dv >= df + dc) continue;
        int e = CD_ST.efresh ? CD_ST.ent[i] : 0;
        ord[n] = i; grp[n] = dv - df; key[n] = (e ? e : 0x40) << 8 | below(256); n++;
    }
    if (GP_CDKN && GP_CDKN(ord, grp, key, n)) return;   /* (4.2 S2 knockouts: the engine's draw, cdkn.c - CD_ST's gen /
                                                           np / gen_on / efresh written there; 0 = refused, logged) */
    for (int i = 1; i < n; i++)         /* (the entry order: insertion sort by key) */
        for (int j = i; j > 0 && key[j - 1] > key[j]; j--) {
            u16 k = key[j]; key[j] = key[j - 1]; key[j - 1] = k;
            u8 o = ord[j]; ord[j] = ord[j - 1]; ord[j - 1] = o; o = grp[j]; grp[j] = grp[j - 1]; grp[j - 1] = o;
        }
    int n1 = 1 << (GP_CDT[1] - 2), p = n - 2 * n1, m = 0;
    if (p < 0) p = 0;
    if (p > 2 * n1) p = 2 * n1;         /* (more clubs than 4 x round 1's ties: the first in entry order play, the rest
                                           are left out - engine sr_cupd_make, Motore's fuzz round 2 find 7) */
    if (p > CDP) p = CDP;
    CD_ST.np = p;
    u8 sg[256];
    for (int k = 0; k < 2 * p; k++) { side[m] = lf | ord[k] << 8; sg[m++] = grp[k]; }
    cd_pair(side, sg, m, 0);
    u8 pg[CDP];
    for (int t = 0; t < p; t++) {       /* (a preliminary tie's group: its first side's) */
        int o = CD_ST.gen[2 * t] >> 8;
        pg[t] = 0xFF;
        for (int k = 0; k < 2 * p; k++) if (ord[k] == o) pg[t] = grp[k];
    }
    m = 0;
    for (int t = 0; t < p; t++) { side[m] = CD_REF(t); sg[m++] = pg[t]; }
    for (int k = 2 * p; k < n && m < 2 * n1; k++) { side[m] = lf | ord[k] << 8; sg[m++] = grp[k]; }
    while (m < 2 * n1) { side[m] = 0; sg[m++] = 0xFF; }
    cd_pair(side, sg, m, 2 * p);
    CD_ST.gen_on = 1;
    CD_ST.efresh = 0;
}

/* The ties nobody plays, by strength as statespec's statesim: strength = the best 11's prices (CD_DT), squared;
   the home club's x 1.21; a match drawn 1 in 4 (0-0, 1-1, 2-2), else won by a weighted coin, 1-3 goals to fewer;
   level after the legs: the penalties, weighted 2:1 to the stronger. */
#if GP_S7
#ifndef GP_DATA_SECTION
#if defined(__MACH__)                   /* (a native host build - mach-o has no ".data" section name; the exe is always ELF) */
#define GP_DATA_SECTION
#else
#define GP_DATA_SECTION __attribute__((section(".data")))      /* (host tests build gplay.c natively: -DGP_DATA_SECTION=) */
#endif
#endif
/* s7-ri-fix.md "Changes" (MC 13/11): in S7 builds the REGISTRY decides and ri's maps[] is unused. The logic is s7ri.c (obj4,
   included by s7swap.c); gplay.c keeps these two hook pointers (set by s7swap.py; 0 = today's path, dormant). */
int (*GP_RIPOOL)(const u8 *e, u16 *q, u8 *qn, int init, int file, const s8 *slt, s8 *copy, int manager, u16 *og, int *nog,
                 u16 *out, int *no, u16 *map, int nmap) GP_DATA_SECTION;
u32 (*GP_CDSTR)(u16 w, const u8 *s) GP_DATA_SECTION;      /* (0: not applicable here) */
/* 4.2 Serie D geography (MC 14/11): a pool arrival whose own girone is full takes it anyway by a CHAIN of one-step moves of
   stayers along s7ri.c's neighbour table to the nearest girone with a seat (tbl c / rs / nc = the table's clubs, fl = the level's
   first division, a = the arrival's girone, cnt / sz / occ the level's groups, pend = pg_pend, og / nog = this season end's
   arrivals, mgr = the manager's club); returns 1 when girone a has a seat now (0 = no chain: today's fallbacks). */
int (*GP_GEOCH)(const u8 *c, int rs, int nc, int fl, int a, int cnt, const u8 *sz, u8 *occ, const s8 *slt, s8 *copy,
                const u8 *pend, int npend, const u16 *og, int nog, int mgr) GP_DATA_SECTION;
#endif
int cd_ident(int m, int i);             /* (the RI section: a pooled slot's identity) */
static u32 cd_below(u32 n) {            /* (below() for n past 65535: the product in 64 bits) */
    rng = rng * 1103515245u + 12345u;
    return (u32)(((unsigned long long)(rng >> 16) * n) >> 16);
}
static u32 cd_str(u16 w) {
    const u8 *s = GP_CDD + CD_O + 256;
    int i = w >> 8, moff = s[0] | s[1] << 8, nmap = s[2] | s[3] << 8, np = s[4] | s[5] << 8, id = i;
    if (moff != 0xFFFF && i < nmap) id = cd_ident(moff + i, i);
#if GP_S7
    if (GP_CDSTR) { u32 v = GP_CDSTR(w, s); if (v) return v; }     /* (s7ri.c: the occupant's real strength) */
#endif
    const u8 *p = id < 256 ? s + 6 + 2 * id : id - 256 < np ? s + 6 + 512 + 2 * (id - 256) : 0;
    u32 v = p ? (u32)(p[0] | p[1] << 8) : 5;
    if (v < 5) v = 5;
    return v * v;
}
static int cd_sim(u16 a, u16 b, int legs, int h) {     /* h: 0 a hosts (the first leg), 1 b -> 1 a through, 2 b */
    u32 sa = cd_str(a), sb = cd_str(b);
    int ga = 0, gb = 0;
    for (int l = 0; l < legs; l++) {
        int home_a = (l == 0) == (h == 0);
        u32 x = home_a ? sa * 121 / 100 : sa, y = home_a ? sb : sb * 121 / 100;
        int p, q;
        if (cd_below(100) < 26) { p = cd_below(3); q = p; }
        else { int w = cd_below(x + y) < x, gw = 1 + cd_below(3), gl = cd_below(gw); p = w ? gw : gl; q = w ? gl : gw; }
        ga += p; gb += q;
    }
    if (ga != gb) return ga > gb ? 1 : 2;
    return cd_below(3 * (sa + sb)) < 2 * sa + sb ? 1 : 2;
}

/* the calendar advance: 1 = a tie of the career club built into ko[0] (gp_install it), else 0 */
u32 cd_step_c(void) {
    if (slot4_busy()) return 0;         /* (4.0.5: an early supercup tie in slot 4 - 4.2 or the friendlies: the next
                                           advance) */
    if (!GP_CDT) return 0;
    if (CD_ST.magic != 0x4443 || CD_ST.season != GP_SEAS) {     /* (a new season: the cup from its start) */
        u8 *p = (u8 *)&CD_ST;
        if (CD_ST.magic != 0x4443) CD_ST.efresh = 0;   /* (a new career / an older save: no entry order) */
        for (u32 i = 0; i < __builtin_offsetof(struct cd_state, ent); i++) p[i] = 0;
        CD_ST.magic = 0x4443; CD_ST.season = GP_SEAS; CD_ST.gen_on = 0;
        if (!GP_CDFIRST) cd_make();
    }
    while (CD_ST.round < GP_CDT[1]) {
        int r = CD_ST.round;
        const u8 *rec = CDREC(r);
        if (GP_CDS1 && cd_n(r) == 32 && (int)GP_WK + 1 >= rec[0] && !CD_ST.built) {
            /* 4.0: the 1/32 on as the game's own knockout in slot 1 (GP_CDS1: its 64 team words), the career club in it:
               the round's pairs in bracket order, cd done for the season (CD_ST.round past the last) */
            int f = cd_first(r), me = 0;
            for (int q = 0; q < 32; q++)
                for (int sd = 0; sd < 2; sd++) {
                    u16 w = cd_side(f + q, sd);
                    GP_CDS1[2 * q + sd] = w && w != 0xFFFF ? w : 0xFFFF;
                    me |= IS_MGR(w);
                }
            if (me) { CD_ST.round = GP_CDT[1]; return 2; }
        }
        int w1 = rec[0], w2 = rec[1], legs = rec[2], host = rec[3], n = cd_n(r), first = cd_first(r);
        if ((int)GP_WK + 1 < w1 || CD_ST.built) return 0;
        rng = GP_SEAS * 7919u + r * 131u + first;
        if ((rec[5] & 1) && CD_ST.drawn != r + 1) {             /* (the pairs drawn: the previous round's ties) */
            int pf = cd_first(r - 1), pn = cd_n(r - 1);
            for (int i = 0; i < 4 && i < pn; i++) CD_ST.sd[i] = pf + i;
            for (int i = (pn < 4 ? pn : 4) - 1; i > 0; i--) { int j = below(i + 1); u8 x = CD_ST.sd[i];
                                                                  CD_ST.sd[i] = CD_ST.sd[j]; CD_ST.sd[j] = x; }
            CD_ST.drawn = r + 1;
        }
        for (int q = 0; q < n; q++) {
            int t = first + q;
            if (CD_ST.res[t]) continue;
            u16 a = cd_side(t, 0), b = cd_side(t, 1), ra = cd_raw(t, 0), rb = cd_raw(t, 1);
            int h = 0;                  /* (0: a hosts, 1: b hosts) */
            if (host == 2) h = below(2);
            else if (host == 4) {
                int pa_ = CD_ISREF(ra) && ra != CD_DRAWN ? ra >> 8 : -1, pb_ = CD_ISREF(rb) && rb != CD_DRAWN ? rb >> 8 : -1;
                int ha = pa_ >= 0 && pa_ < CDT && cd_hosted(pa_, a), hb = pb_ >= 0 && pb_ < CDT && cd_hosted(pb_, b);
                h = ha && !hb ? 1 : !ha && hb ? 0 : below(2);
            }
            CD_ST.home[t] = h;
            if ((IS_MGR(a) || IS_MGR(b)) && a && b && a != 0xFFFF && b != 0xFFFF) {   /* the career club's */
                cd_ko(&GP_ST.ko[0], h ? b : a, h ? a : b, w1, w2, legs);
                CD_ST.built = 1; CD_ST.bt = t; CD_ST.pad = 1;   /* (pad: the harness's trace) */
                return 1;
            }
            if (IS_MGR(a) || IS_MGR(b)) CD_ST.pad = 0x80 | (a == 0xFFFF || b == 0xFFFF ? 2 : 4);
            int w = GP_CDFIRST ? CDTIE(t)[4] : 0;               /* (the real result, the world's first season) */
            if (!w) w = !a ? 2 : !b ? 1 : cd_sim(a, b, legs, h);   /* (else by strength) */
            CD_ST.res[t] = w;
        }
        CD_ST.round = r + 1;
    }
    return 0;
}

/* 4.0: a Coppa Italia Serie D entrant this season (team word = file | ordinal << 8: the Serie D file, its ordinal's
   division of the season in the Serie D groups) - InitNewSeason gives it no cup / league cup (gp_cup12) */
u32 cd_member_c(u32 team) {
    const u8 *dt = GP_CDD;
    if (!GP_CDT || !dt || !GP_SLT || (team & 0xFF) != GP_CDT[2]) return 0;
    int i = team >> 8 & 0xFF, b = dt[CD_O + i];
    if (b == 0xFF) return 0;
    int dv = b + GP_SLT[CD_G(dt, (dt[2] | dt[3] << 8), i)];
    return dv >= dt[0] && dv < dt[0] + dt[1];
}

/* 4.0.1, a career load (gp_after, before gp_sync): a 4.0 save played on after a reload with a Coppa D tie built
   (CD_ST.built): 4.0's gp_after cleared slot 4 together with slot 2, the tie came back as an empty contest, read as a
   league over, and gp_lend built the club's play-off over it into ko[0] from that day's table (Gianmarco's FIDELIS
   ANDRIA, match day 5). Its signature - ko[0] a play-off of this season, the tie still built, the league (slot 0's
   buffer: day +1C1h, days +1C3h) not over - drops that play-off; the tie is built again at the next calendar advance
   (gp_install) and the play-off comes at the league's real end. The play-off's calendar entries still to come (slot
   4 from cur on: the next entry to play; cal: the career calendar, its count word at cal - 4) go, as lib97's
   cal_noreplay removes an entry - the next one moves into cur's place: else its final was played next, then its
   leftover days stuck the career. */
static void cal_drop(u8 *cal, u32 cur, u8 slot) {
    u16 *cnt = (u16 *)(cal - 4);
    u8 *e = cal;
    for (u32 i = 0; i < *cnt; ) {
        u32 len = *(const u16 *)(e + 2);
        if (!len) break;
        if ((u32)(e - cal) >= cur && e[0] == slot) {
            u32 rest = 0;                       /* (the bytes of the entries after it) */
            const u8 *f = e + len;
            for (u32 j = i + 1; j < *cnt; j++) {
                u32 l = *(const u16 *)(f + 2);
                if (!l) break;
                rest += l;
                f += l;
            }
            volatile u8 *o = e;
            for (u32 b = 0; b < rest; b++) o[b] = e[len + b];
            (*cnt)--;
            continue;
        }
        e += len;
        i++;
    }
}
void cd_fixload_c(const u8 *league, u32 seas, u8 *cal, u32 cur) {
    struct gp_ko *k = &GP_ST.ko[0];
    if (CD_ST.magic != 0x4443 || CD_ST.season != (u8)seas || !CD_ST.built) return;
    if (k->magic != MAGIC || k->season != (u8)seas || k->kind == K_CUPD) return;
    if (!league || *(const u16 *)(league + 0x1C1) >= *(const u16 *)(league + 0x1C3)) return;
    k->magic = 0;
    k->slot = 0;
    CD_ST.built = 0;
    if (cal) cal_drop(cal, cur, 4);
    CD_ST.pad |= 0x20;                  /* (the harness's trace: repaired at a load) */
}

static void cd_done(struct gp_ko *k) {  /* gp_rec_c: our CD tie decided -> its result */
    if (!CD_ST.built || k->tw[0] == NOC) return;
    CD_ST.res[CD_ST.bt] = k->team[k->tw[0]] == cd_side(CD_ST.bt, 0) ? 1 : 2;
    if (GP_CDFORCE)                     /* (CD_FORCE test builds: 1 won, 2 lost) */
        CD_ST.res[CD_ST.bt] = (cd_side(CD_ST.bt, 0) == GP_MGR) == (GP_CDFORCE == 1) ? 1 : 2;
    CD_ST.built = 0;
    CD_ST.pad |= 0x40;
}
static void set_pend(int then, int week) {   /* 'then_build': the next play-off at the calendar advance from week on */
    GP_ST.pend = then; GP_ST.pweek = week > 255 ? 255 : week; GP_ST.pseas = GP_SEAS;
}

u32 gp_build_c(void) {
    if (slot4_busy()) { set_pend(GP_BPIC + 1, GP_WK + 1); return 0; }   /* (4.0.5: an early supercup tie holds slot 4:
                                                                     built again at the next advance) */
    ss_set(GP_IN.mgr);
    const u8 *s = po_at(GP_BPIC);
    stage_done(&GP_ST.ko[0]);                   /* (the previous stage's knockout, played: before ko[0] is rebuilt) */
    if (!s || !playable(s)) return 0;
    for (int i = 0; i < s[1]; i++) {
        const u8 *e = s + 6 + 4 * i;
        if (e[2] > GP_IN.n[e[1]]) return 0;
    }
    GP_ST.nsim = 0;
    GP_IN.pi[0] = GP_BPIC; GP_IN.pi[1] = NOC;
    const u8 *e0 = s + 6, *e1 = s + 10;         /* 4.0.1: a table's leader as both entrants of one tie (sa_exact's
                                                   'table titles'): nothing to play, decided at once as a simulated
                                                   one - a slot contest of the career club with itself stayed stuck
                                                   after a mid-season reload */
    int trivial = s[1] == 2 && s[2] == 1 && e0[0] == e1[0] && e0[1] == e1[1] && e0[2] == e1[2] && e0[3] == e1[3];
    u16 mgr = GP_IN.mgr;
    if (trivial) GP_IN.mgr = 0xFFFF;
    u32 b = gp_lend_c() & 1;
    GP_IN.mgr = mgr;
    if (!b && GP_ST.ko[0].magic == MAGIC) {
        ko_sim(&GP_ST.ko[0]);
        stage_done(&GP_ST.ko[0]);               /* (simulated at once: decided now) */
        if (GP_ST.ko[0].bye[5]) { set_pend(GP_ST.ko[0].bye[5], GP_ST.ko[0].d2); GP_ST.ko[0].bye[5] = 0; }
    }                                           /* ('then_build' after the simulated final's week) */
    return b;
}
const u32 GP_KOLAY[] = { __builtin_offsetof(struct gp_state, ko), sizeof(struct gp_ko),
                         __builtin_offsetof(struct gp_ko, slot), __builtin_offsetof(struct gp_ko, ntie),
                         __builtin_offsetof(struct gp_ko, tw), __builtin_offsetof(struct gp_ko, tl),
                         __builtin_offsetof(struct gp_ko, team), __builtin_offsetof(struct gp_ko, n) };

/* the contest in DIY (id GP_CID) is ours: its ko index, else -1 */
int gp_ours_c(void) {
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS) return -1;
    for (int i = 0; i < 2; i++)
        if (GP_ST.ko[i].magic == MAGIC && GP_ST.ko[i].slot && GP_ST.ko[i].cid == GP_CID && GP_ST.ko[i].season == GP_SEAS
            && !(KT2(&GP_ST.ko[i]) && GF(&GP_ST.ko[i]) >= GF_ON))   /* (4.0.5 NZ: its group over - the Grand Final's id) */
            return i;
    return -1;
}

/* (4.2, benchx bx_look) the contest in DIY when it is a play-off of ours (not a one-tie contest: the Coppa D's, a
   supercup, the Grand Final keep their titles' benches): its team file | the lowest division of its entrants << 8 (a
   play-off's bench = its clubs' division, the lowest if mixed: one bench entry per division, not one per title);
   0xFFFF: none */
u32 gp_bdiv_c(void) {
    int i = gp_ours_c();
    if (i < 0 || GP_ST.ko[i].pi == NOC) return 0xFFFF;
    const struct gp_ko *k = &GP_ST.ko[i];
    int d = 0;
    for (int j = 0; j < k->n && j < KN; j++) if (KDV(k, j) > d) d = KDV(k, j);
    return k->lfile | d << 8;
}

static int kidx(const struct gp_ko *k, u16 team) {
    if (!team) return NOC;              /* (S6a: GP_MGR 0 = an all-CPU world SEASON - no manager's club; world team
                                           words are never 0: files 101+) */
    for (int i = 0; i < k->n; i++) if (k->team[i] == team) return i;
    return NOC;
}

/* lib97 nc_adv (gp_perm): GP_PT = the winners of the round just played in tie order -> GP_PL = the next round's
   list, GP_RB its round byte, GP_SKIP game rounds skipped (a game 3 nobody needs); returns its clubs (0: none) */
static u32 hum_alive(const struct gp_ko *k) {   /* S6a (c): the human clubs (GP_HUM: a career's one club, a world
                                           SEASON's teamControls != 1 clubs) in k's bracket, none of its ties lost */
    u32 c = 0;
    for (u32 h = 0; h < GP_NHUM && h < 64; h++) {
        int me = kidx(k, GP_HUM[h]), in = me != NOC;
        for (int t = 0; t < k->ntie && in; t++)
            if (k->tw[t] != NOC && k->tl[t] == me && k->tw[t] != me) in = 0;
        c += in;
    }
    return c;
}
u32 gp_perm_c(void) {
    struct gp_ko *k = &GP_ST.ko[GP_K];
    GP_ALIVE = 0xFFFFFFFF;
    if (KT2(k)) return 0;               /* (a type-2 contest: the game's own stages) */
    int g = k->gcur, p0 = k->gp0[g], np = k->gp0[g + 1] - p0, c = 0;
    for (int i = 0; i < np && i < 64; i++) k->pw[p0 + i] = GP_PT[i];
    if (GP_KOFORCE) {                   /* (test builds: the career club's ties of this round lost / won) */
        int m = kidx(k, GP_MGR);
        for (int p = p0; p < p0 + np && m != NOC; p++)
            if (k->pa[p] == m || k->pb[p] == m)
                k->pw[p] = (GP_KOFORCE == 2) == (k->pa[p] == m) ? k->pa[p] : k->pb[p];
    }
    resolve(k);
    GP_ALIVE = hum_alive(k);            /* the contest's human-clubs count (+4Bh): the game takes 1 off for every
                                           match a human club loses (cseg_2ABF0), a series' lost game 1 too -> a
                                           later elimination left it FFFFh, the next round's entry 'still in' (FFh)
                                           and PARTITA without a match hung (MLS): ours */
    GP_SKIP = 0;
    for (;;) {
        if (++g >= k->ngr) return 0;
        c = build_game(k, g);
        if (c > 0) break;
        GP_SKIP++;
    }
    k->gcur = g;
    for (int i = 0; i < c; i++) { GP_PL[2 * i] = k->pa[k->gp0[g] + i]; GP_PL[2 * i + 1] = k->pb[k->gp0[g] + i]; }
    GP_RB = k->rb[g];
    return 2 * c;
}

/* a decisive match of ours (GP_A v GP_B, GP_W = 1: the second won): its pair's winner */

u32 GP_DEFWK, GP_ADVWK;                 /* 4.0: a deferred stage build's week (its stage's last day), the week gp_adv builds
                                           from (the advance's own week is already the next league day's) */
void gp_defer_c(void) {                 /* (gp_defer: play-off GP_BPIC built at the calendar advance from week GP_WK on) */
    set_pend(GP_BPIC + 1, GP_WK);
    GP_DEFWK = GP_WK + 1;
}

/* the calendar advance (gp_adv, cseg_8EA82's callers): a pending 'then_build' due -> its play-off index + 1 (then
   gp_build with GP_BWEEK = this week), else 0 */
u32 gp_adv_c(void) {
    if (!GP_ST.pend || GP_ST.pseas != GP_SEAS || GP_WK < GP_ST.pweek) return 0;
    u32 t = GP_ST.pend;
    GP_ST.pend = 0;
    GP_ADVWK = GP_DEFWK ? GP_DEFWK - 1 : GP_WK;
    GP_DEFWK = 0;
    return t;
}

static void ko_copy(struct gp_ko *d, const struct gp_ko *s) {   /* (no memcpy in the exe: byte by byte) */
    volatile u8 *o = (volatile u8 *)d;
    const u8 *i = (const u8 *)s;
    for (unsigned n = 0; n < sizeof *d; n++) o[n] = i[n];
}

#ifndef GP_PORT
#define GP_PORT 0                       /* (4.2 fixture port P2 builds: fpad.py; 0 = no byte of it) */
#endif
#ifndef GP_FRND
#define GP_FRND 0                       /* (4.2 preseason friendlies: frnd.py on(); the engine in obj4 FRND, frstep.c) */
#endif
#define GP_HOOK (GP_PORT || GP_FRND)    /* (the slot-4 hooks below: the port's, shared by the friendlies - Fable review +
                                           MC 16/11: one set, chained in obj4, FRND first) */
enum { K_FR = 13 };                     /* (a preseason friendly: one match, LV_BETTER, frstep.c) */
#if GP_HOOK
#ifndef GP_DATA_SECTION
#define GP_DATA_SECTION __attribute__((section(".data")))      /* (host tests build gplay.c natively: -DGP_DATA_SECTION=) */
#endif
/* 4.2 fixture port P2 (internal/handoff/motore-fixport-plan.md 1b): the adapter fpad.c lives in obj4 (swreg FPORT band,
   fpad.py) and fills these hooks; gplay keeps slot 4's builder (ko_one) and hands it over through GP_PAPI. */
enum { K_PORT = 12 };
u32 (*GP_PSTEP)(void) GP_DATA_SECTION;                          /* sc_step_c's head: 1 = a fixture built into ko[0] */
void (*GP_PDONE)(void) GP_DATA_SECTION;                         /* gp_rec_c: ko[0]'s K_PORT tie decided */
void (*GP_PLEG)(void) GP_DATA_SECTION;                          /* gp_rec: every match of ours (fp_leg: K_PORT ones) */
void (*GP_PSEAS)(void) GP_DATA_SECTION;                         /* pg_season's end: a new season (fp_season) */
u8 GP_PMID;                             /* (.bss, obj2: fpad.c's legs played of the K_PORT tie - the gate's mid-tie save) */
#if GP_FRND
u32 (*GP_PROW)(const u8 *) GP_DATA_SECTION;                     /* gp_scrow_c's head (frnd fr_row): a played friendly's
                                                                   slot-4 row keeps the friendly's short name, 0 = not one */
#endif
#endif
void gp_rec_c(void) {
    struct gp_ko *k = &GP_ST.ko[GP_K];
    int a = kidx(k, GP_A), b = kidx(k, GP_B), g = k->gcur;
    if (KT2(k)) {                       /* a type-2 contest: the last decisive match (the final's, at the end) */
        if (a != NOC && b != NOC && !GF(k)) { k->tw[0] = GP_W ? b : a; k->tl[0] = GP_W ? a : b; }
        return;
    }
    for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++)
        if ((k->pa[p] == a && k->pb[p] == b) || (k->pa[p] == b && k->pb[p] == a)) {
            k->pw[p] = GP_W ? b : a;
            if (GP_KOFORCE) {           /* (test builds: lost / won; GP_IN: the career club as ko_build saw it) */
                int me = kidx(k, GP_IN.mgr ? GP_IN.mgr : GP_MGR);
                if (me != NOC && (a == me || b == me)) k->pw[p] = (GP_KOFORCE == 2) == (a == me) ? a : b;
            }
        }
    resolve(k);
    if (k->kind == K_CUPD) { cd_done(k); return; }
    if (k->kind == K_SC) { SC_DONE(k->tw[0] != NOC ? k->team[k->tw[0]] : 0); return; }   /* (4.0.5 supercup: a final four's semi -> its final) */
    if (k->kind == K_GF) { gf_done(k); return; }   /* (4.0.5 NZ: the Grand Final) */
#if GP_PORT
    if (k->kind == K_PORT) { if (GP_PDONE) GP_PDONE(); return; }   /* (K_PORT: the fixture port's tie, fpad.c) */
#endif
    GP_LAST = 0;
    int left = 0;
    for (int p = k->gp0[g]; p < k->gp0[g + 1]; p++) if (k->pw[p] == NOC) left++;
    if (!left && g + 1 < k->ngr) {      /* (this match ended its round: the later ones all decided without a match -
                                           a skip_if_same / gap round, CRC's Gran Final of one club - end the contest
                                           here, the game's own last round: gp_rec, +59h = +57h + 1; else the game
                                           draws a next round gp_perm cannot build and hangs) */
        static struct gp_ko t;
        ko_copy(&t, k);
        int g2 = g + 1, over = 1;
        while (g2 < t.ngr && build_game(&t, g2) == 0) g2++;
        resolve(&t);
        for (int i = 0; i < t.ntie; i++) if (t.tw[i] == NOC) over = 0;
        if (g2 >= t.ngr && over) {
            ko_copy(k, &t);
            k->gcur = t.ngr - 1;
            GP_LAST = 1;
        }
    }
    if (k->bye[5] && k->ntie && k->tw[k->ntie - 1] != NOC) {   /* (its final decided: the next one, once, from the
                                           week after: the advance right after the final still has slot 4's contest
                                           in hand, a build there was lost - 4.0's Trofeo) */
        set_pend(k->bye[5], GP_WK + 1);
        GP_DEFWK = 0;
        k->bye[5] = 0;
    }
}

/* a level tie of ours with no penalties: 1 if the second club (GP_B) goes through, the better placed */
u32 gp_draw_c(void) {
    const struct gp_ko *k = &GP_ST.ko[GP_K];
    int a = kidx(k, GP_A), b = kidx(k, GP_B);
    if (KT2(k)) return 0xFFFFFFFF;      /* (a type-2 contest: the game's rules) */
#if GP_PORT
    if (k->kind == K_PORT && !k->rs[0][3]) return 0x10;   /* (a port fixture with no decider - a mini-league match: the
                                           draw stands, fpad.c reads the score; result flag 10h keeps bplace's 'better
                                           placed goes through' line off its result) */
#endif
    return a != NOC && b != NOC && kbetter(k, b, a);
}

/* the season end, before gp_season: the career club's played play-off (ko 0) -> GP_IN.pl_*; and the log */
void gp_played_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    GP_IN.pl_pi = 0;
    GP_IN.pl_t2 = 0;
    GP_IN.pl_fw = GP_IN.pl_fl = 0;
    if (k->kind == K_CUPD) return;      /* (a Coppa Italia Serie D tie: not a play-off of the spec) */
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS || k->magic != MAGIC || k->season != GP_SEAS) return;
    GP_IN.pl_pi = k->pi + 1;
    GP_IN.pl_t2 = KT2(k);
    if (KT2(k)) {                       /* a type-2 contest: its champion / runner-up */
        for (int t = 0; t < KT; t++) GP_IN.pl_w[t] = 0;
        GP_IN.pl_w[0] = k->tw[0] != NOC ? k->team[k->tw[0]] : 0;
        GP_IN.pl_w[1] = k->tl[0] != NOC ? k->team[k->tl[0]] : 0;
        return;
    }
    resolve(k);
    for (int t = 0; t < KT; t++) GP_IN.pl_w[t] = t < k->ntie && k->tw[t] != NOC ? k->team[k->tw[t]] : 0;
    int f = k->ntie - 1;                /* (4.2: its final - gp_season's title play-off result) */
    if (f >= 0 && f < KT && k->tw[f] != NOC) {
        GP_IN.pl_fw = k->team[k->tw[f]];
        GP_IN.pl_fl = k->tl[f] != NOC && k->tl[f] != k->tw[f] ? k->team[k->tl[f]] : 0;
    }
}

#ifndef GP_GSON
#define GP_GSON 0                               /* (1: the engine block saves GP_GS - early tables beyond SD kept) */
#endif
/* rc19: the career league has ended (gp_lend, after gp_need: the career club's play-offs GP_IN.pi[], their divisions
   GP_IN.sim[]): the divisions its country's OTHER play-offs need, appended to sim[] - simulated now and kept (GP_ST /
   GP_GS: the season end restores them); the titles with an entrant from the career club's division first, then the
   other titles, the other play-offs with one, the rest; one whose divisions do not all fit is left to the season end. GP_PREI = the first
   appended (gp_simkeep_pre). Returns 1 if the preview may run. */
u8 GP_PREI;
#if GP_PORT
/* 4.2 the fixture port's league-end / season-end hooks (fpml.c, the mini-league producer; bound by fpad.py, 0 = none):
   GP_PNEED - gp_need_pre's head: the divisions a stage opening at the career league's last day needs simulated now and
   kept are appended to GP_IN.sim[] by the hook itself (obj4: no byte of that here - obj1's room), as the club's own
   play-offs' (before GP_PREI); GP_PLEND - gp_pre_c's head: the career league over, those tables in GP_IN (the
   club's own table after gp_force); GP_PEND - gp_end_c's head: the season end, after gp_season, every table final.
   Every hook dword is wired by tools/gphooks.py (MC 17/11: the one registry, a chain per hook), never by a module. */
void (*GP_PNEED)(void) __attribute__((section(".data")));
void (*GP_PLEND)(void) __attribute__((section(".data")));
void (*GP_PEND)(void) __attribute__((section(".data")));
#endif
__attribute__((minsize)) u32 gp_need_pre(void) {
    int ns = 0, lim = GP_GSON ? SDX : SD;
#if GP_PORT
    if (GP_PNEED) GP_PNEED();                   /* (the port's stage: its entrants' divisions into sim[], always kept) */
#endif
    u32 have = 1u << GP_IN.mdiv;                /* (divisions with a table: the career club's, the ones in sim[]) */
    while (ns < SDX && GP_IN.sim[ns] != NOC) have |= 1u << GP_IN.sim[ns++];
    GP_PREI = (u8)ns;
    if (GP_IN.gtype != 4 || !GP_IN.spec) return 0;   /* (careers only: Season mode plays its division's own) */
    if (!(GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS)) {   /* (a state for the kept tables: no contest of ours) */
        GP_ST.magic = MAGIC; GP_ST.season = GP_SEAS;
        GP_ST.ko[0].magic = GP_ST.ko[1].magic = 0;
        GP_ST.pend = 0; GP_ST.s3wait = 0;
    }
    for (int pass = 0; pass < 4; pass++)
        for (int pi = 0; ; pi++) {
            const u8 *s = po_at(pi), *e = s ? ents_of(s) : 0;
            if (!s) break;
            if (s[0] == K_PROM || pi == GP_IN.pi[0] || pi == GP_IN.pi[1]) continue;   /* (the club's: built, played) */
            u32 need = 0;
            for (int i = 0; i < s[1]; i++) {
                int ty = e[4 * i], d = e[4 * i + 1];
                if ((ty == 0 || ty == 3 || ty == 6 || ty == 7) && d < GP_IN.nd) need |= 1u << d;
                for (int g = 0; ty == 9 && g < e[4 * i + 2] && d + g < GP_IN.nd; g++) need |= 1u << (d + g);   /* (4.2: the cup's groups) */
            }
            int mine = need >> GP_IN.mdiv & 1, title = s[0] == K_TITLE || s[0] == K_STAGE || s[0] == K_CONT, nn = 0;
            need &= ~have;
            for (u32 x = need; x; x &= x - 1) nn++;
            if (pass != (title ? !mine : 3 - mine) || ns + nn > lim) continue;
            have |= need;
            for (int d = 0; need; d++, need >>= 1) if (need & 1) GP_IN.sim[ns++] = (u8)d;
        }
    return 1;
}

/* rc19: an early simulation for the preview (gp_simkeep), unless its rows would not fit the slot (GP_GS: GSR) -
   then the division is left out (its play-offs decided at the season end) */
__attribute__((minsize)) void gp_simkeep_pre(void) {
    int n = *(const u16 *)(GP_DIYP + 0x31), j = GP_ST.nsim;
    if (j >= GP_PREI && (j >= SDX || (j >= SD && n > GSR))) { if (GP_DIV < GD) GP_IN.n[GP_DIV] = 0; return; }
    gp_simkeep();                       /* (the club's own play-offs' divisions, j < GP_PREI: as gp_simkeep always) */
}

/* rc19: the preview - gp_season over the tables known now (the career division's, the kept ones), its play-off
   winners into WN_ST after a marker; no move applied, the state as it was (GP_OUT void) */
__attribute__((minsize)) void gp_pre_c(void) {
    if (GP_IN.gtype != 4 || !GP_IN.spec) return;
#if GP_PORT
    if (GP_PLEND) GP_PLEND();           /* (the port: a stage of the league's end opens - fpml.c fp_ml_lend) */
#endif
    if (WN_ST.magic != WN_MAGIC || (u8)(WN_ST.season + 1) != GP_SEAS) {   /* (no last season: an empty one that
                                                   no reader takes for the last season) */
        WN_ST.magic = WN_MAGIC; WN_ST.season = GP_SEAS ^ 0x80; WN_ST.n = 0;
    } else
        for (int i = 0; i < WN_ST.n && i < WN_N; i++)
            if (WN_ST.e[i].type == WN_PRE) { WN_ST.n = i; break; }   /* (an earlier preview: replaced) */
    if (WN_ST.n + 2 > WN_N) return;
    struct wn_e *x = &WN_ST.e[WN_ST.n++];
    x->type = WN_PRE; x->idx = GP_SEAS; x->team = 0;
    GP_IN.pl_pi = GP_IN.pl_t2 = 0;      /* (the club's own play-offs, GP_IN.pi[]: not previewed - their lines are
                                           its contests', played; nor those taking their clubs, type 4) */
    GP_PRE = 1;
    gp_season();
    GP_PRE = 0;
    GP_OUT.nmv = 0; GP_OUT.nres = 0;
    if (GP_IN.mgr != 0xFFFF) ss_set(GP_IN.mgr);   /* (the career league's bank again, as gp_need / gp_lend_c left it) */
}

void gp_end_c(void) {                   /* after gp_season: the log, the state void */
    const u8 *s = (const u8 *)&GP_ST.ko[0];
#if GP_PORT
    if (GP_PEND) GP_PEND();             /* (the port: a stage not played is decided now, its trophies written -
                                           fpml.c fp_ml_open(1), after gp_season and before the S7 swap) */
#endif
    u8 *d = (u8 *)&GP_LOG.ko;
    if (GP_ST.magic == MAGIC || GP_IN.pl_pi) {   /* (the career club's play-off only: rc18's `|| GP_OUT.nres` let
                                           every later country's season end overwrite the harness's log) */
        for (u32 i = 0; i < sizeof GP_LOG.ko; i++) d[i] = s[i];
        s = (const u8 *)&GP_OUT; d = (u8 *)&GP_LOG.out;
        for (u32 i = 0; i < sizeof GP_LOG.out; i++) d[i] = s[i];
        GP_LOG.seas = GP_SEAS; GP_LOG.stseas = GP_ST.season; GP_LOG.pl_pi = GP_IN.pl_pi;
        for (int i = 0; i < 9; i++) GP_LOG.top[i] = GP_TOPW[i];
        GP_LOG.tag = 0x474C5047;        /* 'GPLG' */
    }
    if (GP_CDT && GP_CDD) cd_rank();          /* (the Coppa D: the Serie D groups' final places) */
    GP_ST.magic = 0;
    GP_ST.nsim = 0;
    GP_ST.ko[0].magic = GP_ST.ko[1].magic = 0;
    GP_IN.pl_pi = 0;
}

/* SeasonFinished's contract check (gp_sack): the career club relegated into the reserve (loser_div 'reserve', the
   reserve below the lowest level: pgroups' RS_TAB) is sacked, with job offers - directly (a reserve country's club
   in a division >= its lowest level, placed below teams - relegated) or by the played play-out it lost. */
const u8 *GP_CFB, *GP_LG, *GP_RST, *GP_RIT;   /* the league's final table, its struct, RS_TAB, RI_TAB (0: none) */
const s8 *GP_SLT;                       /* someLeaguesTable (the clubs' divisions: base + delta) */
u32 GP_SEL;                             /* selTeamsPtr */
u8 GP_WORLD;

/* SeasonFinished (gp_sack, before the season review): the career club won our played group contest (the Poule) ->
   its record line's name (the season record's 4th line: a Serie D club plays no European cup), else 0. Test builds
   (GPLAY_FORCE): the club is made the winner (the review's DA11B too: no European trophy for it, gp_sack's guard). */
/* 4.0 stage titles (longtable.stage_table): tab: dw n; dw S_MAGIC, S_FROZEN, S_GRP offsets (split's state in a league
   buffer), dw its magic; dd the career team word's address; dw the weeks table's offset; n records of 136 B: key (41 B:
   the DIY+4 title) + pad, [5 stages][4 groups] dw long-title offsets from tab, the same for the short ones (0 = none),
   5 db the stage's first day (255 = none) + pad. */
enum { STG_REC = 136, STG_TBL = 128 };  /* (4.0.5: + MAXS db the stage's 'table' + 1, 0 = none, + pad) */
static const u8 *st_rec(const u8 *lg, const u8 *tab) {      /* lg's record, or 0 */
    if (w16(lg + w16(tab + 2)) != w16(tab + 8)) return 0;
    const u8 *r = tab + 16;
    for (int i = 0, n = w16(tab); i < n; i++, r += STG_REC) {
        int k = 0;
        while (k < 41 && lg[4 + k] == r[k] && r[k]) k++;
        if (k == 41 || lg[4 + k] == r[k]) return r;
    }
    return 0;
}
static int st_grp(const u8 *lg, const u8 *tab) {           /* the career club's group in lg (0 if none) */
    const u16 *ct = *(const u16 * const *)(tab + 10);
    for (int j = 0, nc = w16(lg + 0x31); j < nc && j < 64; j++)
        if (w16(lg + 0x12D + 2 * j) == *ct) return lg[w16(tab + 6) + j] & 3;
    return 0;
}
/* longtable lt_stage (a table's OnRestore): the table title of diy's current stage / the career club's group */
u32 gp_stitle_c(const u8 *diy, const u8 *tab) {
    const u8 *r = st_rec(diy, tab);
    if (!r) return 0;
    int s = diy[w16(tab + 4)];
    if (s >= 5) return 0;
    const u8 *row = r + 42 + 8 * s;
    if (w16(row + 2) && w16(row + 2) != w16(row)) return 0;   /* 4.0: names per group (a split's GRUPPO TITOLO /
                                    SALVEZZA): the one table shows every group under its header row - the league's name */
    int g = st_grp(diy, tab), o = w16(row + 2 * g);
    if (!o) o = w16(row);
    return o ? (u32)(tab + o) : 0;
}
/* 4.0 group headers in a long table (longtable lt_d5 / lt_row / lt_end; the labels: gp_hlabel_c, 3.3.6's): the
   table's places in virtual rows - a header before each group's first place (split's group of its row, tab = the
   stage table's header) - and the window of rows virtual rows from cur: GP_HF / GP_HL its first / last place,
   GP_HP[place] = 0x80 | group when its header is shown before it (| 0x40: an empty row before the header), GP_HGP[place] its place in the group, GP_HV the
   virtual rows (ScrollDown's limit), GP_HON = headers in this table. */
u8 GP_HP[65], GP_HGP[65], GP_HG[65];   /* (GP_HG: every place's group, for zones by group) */
u32 GP_HV, GP_HF, GP_HL, GP_HON;
extern const u8 GP_HLT[];                /* zones.header_labels: [n dw] + n x (title 41 B, 4 labels of 24 B) */
u32 gp_hlabel_c(const u8 *t, u32 g) {   /* a group's header label (3.3.6: ZONA A / B, EASTERN / WESTERN CONFERENCE) */
#ifndef HDR_TEST
    u32 n = *(const u32 *)GP_HLT;
    const u8 *e = GP_HLT + 4;
    if (g > 3)
        return 0;
    for (u32 k = 0; k < n; k++, e += 41 + 4 * 24) {
        u32 i = 0;
        while (i < 40 && e[i] && e[i] == t[4 + i])
            i++;
        if ((i == 40 || (!e[i] && !t[4 + i])) && e[41 + 24 * g])
            return (u32)(e + 41 + 24 * g);
    }
    return 0;
#endif
#ifdef HDR_TEST
    static const char *L[4] = { "GROUP 1", "GROUP 2", "GROUP 3", "GROUP 4" };
    return g < 4 ? (u32)L[g] : 0;
#else
    (void)t; (void)g;
    return 0;
#endif
}
void gp_hplan_c(const u8 *t, const u8 *tab, u32 cur, u32 rows, u32 off) {
    int n = w16(t + 0x51), g[65], hdr = 0;
    if (n > 64) n = 64;
    for (int k = 1; k <= n; k++) { GP_HP[k] = 0; GP_HGP[k] = k; g[k] = 0; }
    if ((!off || off >= 4) && tab && w16(t + w16(tab + 2)) == w16(tab + 8)) {   /* (4.0.6: off 4 + k = an earlier
                                           stage's table, longtable lt_plan: its places in ap_build's order) */
        for (int k = 1; k <= n; k++)
            g[k] = t[w16(tab + 6) + (off >= 4 ? GP_OV_ORD[k - 1] : w16(t + 0x6D + 2 * (k - 1))) / 18] & 3;
        for (int k = 2; k <= n; k++) if (g[k] != g[1]) hdr = 1;
        for (int k = 1; k <= n && hdr; k++) if ((k == 1 || g[k] != g[k - 1]) && !gp_hlabel_c(t, g[k])) hdr = 0;
        if (off >= 4 && hdr) {                  /* (4.0.6: a stage table only when its places come in group blocks -
                                                   ARG's Apertura: Zona A 1..15, B 16..30; a stage of one table, e.g.
                                                   URU's Apertura seen in the Intermedio, mixes the groups: none) */
            int seen = 0;
            for (int k = 1; k <= n && hdr; k++)
                if (k == 1 || g[k] != g[k - 1]) {
                    if (seen >> g[k] & 1) hdr = 0;
                    seen |= 1 << g[k];
                }
        }
    }
    GP_HON = hdr;
    int v = 0, h0[65], s0[65];          /* h0[k]: the virtual row of place k's header (or -1), its own row after;
                                           s0[k]: an empty row before every header but the first (Davide, 4.0) */
    for (int k = 1; k <= n; k++) {
        s0[k] = hdr && k > 1 && g[k] != g[k - 1] ? v++ : -1;
        h0[k] = hdr && (k == 1 || g[k] != g[k - 1]) ? v++ : -1;
        v++;
    }
    GP_HV = v;
    int mx = v > (int)rows ? v - (int)rows : 0, c = (int)cur > mx ? mx : (int)cur, end = c + (int)rows, gp = 0;
    GP_HF = 0; GP_HL = 0;
    v = 0;
    for (int k = 1; k <= n; k++) {
        gp = h0[k] >= 0 || k == 1 ? 1 : gp + 1;
        GP_HGP[k] = hdr ? gp : k;
        GP_HG[k] = (u8)g[k];
        v = h0[k] >= 0 ? h0[k] + 1 : v;
        if (v >= c && v < end) {
            if (!GP_HF) GP_HF = k;
            GP_HL = k;
            if (h0[k] >= c) GP_HP[k] = 0x80 | (s0[k] >= c ? 0x40 : 0) | g[k];
        }
        v++;
    }
    if (!GP_HF) { GP_HF = 1; GP_HL = 1; }
}

/* gp_cal (the career calendar's league row): the short title of the league day in week wk (lg = slot 0's buffer) */
u32 gp_scal_c(const u8 *lg, const u8 *tab, u32 wk) {
    if (!lg || !tab) return 0;
    const u8 *r = st_rec(lg, tab);
    if (!r) return 0;
    const u8 *weeks = lg + w16(tab + 14);
    int d = -1;
    for (int i = 0; i < 64; i++) if (weeks[i] == (u8)wk) { d = i; break; }
    if (d < 0) return 0;
    int s = 0;
    for (int k = 1; k < 5; k++) if (r[122 + k] != 255 && d >= r[122 + k]) s = k;
    const u8 *row = r + 82 + 8 * s;
    int g = s ? st_grp(lg, tab) : 0, o = w16(row + 2 * g);
    if (!o) o = w16(row);
    return o ? (u32)(tab + o) : 0;
}

/* 4.0.5 the earlier stages' tables (Davide's MEX.CAR: the Apertura's final table during the Clausura): the stage
   tables gp_stage kept in the league's SS bank (r[k], fresh bit k), for the stages before diy's current one (split's
   frozen stage index = its stage-title row; a row's table: the record's STG_TBL bytes). The STAT entry cycles the
   table screen through the live table, the overall one (one group over 24 clubs: CLASSIFICA GENERALE) and these
   (fmtpage fp_ov: OV_FLAG 0 / 1 / 4 + k); longtable lt_ov draws k from ap_build. A table of this season only: its
   stage ended this season (the frozen index is this season's), its rows this league's (team file, club count). */
static const struct gp_ss *ap_bank(const u8 *diy, int k) {
    const struct gp_ss *b = ss_view(diy[0x12D]);
    int n = w16(diy + 0x31);
    if (!b || k < 0 || k >= SS_N || k == 2 || !(b->fresh >> k & 1) || b->n[k] != n || n < 2 || n > 32) return 0;
    if ((b->r[k][0].team & 255) != diy[0x12D]) return 0;
    return b;
}
u32 ap_mask(const u8 *diy, const u8 *tab) {     /* bit k: table k viewable now */
    const u8 *r = tab ? st_rec(diy, tab) : 0;
    if (!r) return 0;
    u32 m = 0;
    for (int row = 1, s = diy[w16(tab + 4)]; row < s && row < 5; row++) {
        int k = r[STG_TBL + row] - 1;
        if (ap_bank(diy, k)) m |= 1u << k;
    }
    return m;
}
u32 ap_next(const u8 *diy, const u8 *tab, u32 cur, u32 ov) {    /* the mode after cur: 0 live, 1 overall, 4 + k */
    u32 m = ap_mask(diy, tab), seq[2 + SS_N], n = 0;
    seq[n++] = 0;
    if (ov) seq[n++] = 1;
    for (int k = 0; k < SS_N; k++) if (m >> k & 1) seq[n++] = 4 + k;
    for (u32 i = 0; i < n; i++) if (seq[i] == cur) return seq[(i + 1) % n];
    return seq[1 % n];
}
static int ap_row(const u8 *r, const u8 *diy, const u8 *tab, u32 mode) {   /* mode's stage-title row, -1 none */
    if (!mode) { int s = diy[w16(tab + 4)]; return s < 5 ? s : -1; }
    for (int q = 1; q < 5; q++) if (mode >= 4 && r[STG_TBL + q] == mode - 3) return q;
    return -1;
}
u32 ap_label(const u8 *diy, const u8 *tab, u32 mode, u32 lng) {   /* mode's stage name (short; lng: long), 0 none */
    const u8 *r = tab ? st_rec(diy, tab) : 0;
    int row = r ? ap_row(r, diy, tab, mode) : -1;
    if (row < 0) return 0;
    int o = w16(r + (lng ? 42 : 82) + 8 * row);
    return o ? (u32)(tab + o) : 0;
}
static void ap_put(u8 *x, int v) { x[0] = (u8)v; x[1] = (u8)(v >> 8); }
u32 ap_build(const u8 *diy, const u8 *tab, u32 k) {    /* GP_OV_ROWS / GP_OV_ORD = stage table k, by its places */
    const u8 *r = tab ? st_rec(diy, tab) : 0;
    const struct gp_ss *b = r ? ap_bank(diy, k) : 0;
    int row = b ? ap_row(r, diy, tab, 4 + k) : -1;
    if (row < 1 || row >= 4) return 0;
    int n = w16(diy + 0x31), d0 = r[122 + row], d1 = r[122 + row + 1];
    int played = d0 != 255 && d1 != 255 && d1 > d0 ? d1 - d0 : 0;  /* (the stage's days: every club plays each) */
    for (int i = 0; i < n * 18; i++) GP_OV_ROWS[i] = diy[0x2B3 + i];
    for (int i = 0; i < n; i++) {
        const struct gp_row *o = &b->r[k][i];
        int j = -1;
        for (int q = 0; q < n; q++) if (w16(diy + 0x12D + 2 * q) == o->team) { j = q; break; }
        if (j < 0) return 0;
        int won = o->won, drawn = o->pts - 3 * won, pl = played > won ? played : won;
        if (drawn < 0) drawn = 0;
        if (drawn > pl - won) drawn = pl - won;
        u8 *x = GP_OV_ROWS + 18 * j;            /* (played, won, drawn, lost, gf, ga, pts; no array: no memcpy) */
        ap_put(x + 4, pl); ap_put(x + 6, won); ap_put(x + 8, drawn); ap_put(x + 10, pl - won - drawn);
        ap_put(x + 12, o->gf); ap_put(x + 14, o->ga); ap_put(x + 16, o->pts);
        GP_OV_ORD[i] = 18 * j;
    }
    GP_OV_N = n;
    GP_OV_ANNUAL = 0;
    return 1;
}

/* 4.0 after a career load (gp_repoint, after ProcessCareerFile): every slot buffer's long-name pointer (DIY+27h,
   absolute: stale in a save from another build - 3.x, an older 4.0) from its contest struct (D8CAA[k], rebuilt from
   this exe's records: names at struct + 5 + [struct + 5], [long, short] per division, the career division for slot 0);
   a title (DIY+4, '<country> <long>') whose name part differs is rebuilt from its country prefix (a 4.0 test save's
   overflowed 'ARGENTINA LIGA PROFESIONAL DE FUTBO'). base: the strings' base (aChairmanScenes). */
/* 4.0 after a career load from another build: phase 0, the running knockouts' contest names from this exe's play-off
   names (nm: the career country's GP_NM, long / short / record rel per play-off); phase 1, every season record whose
   league line (leagueStringOffset, +16h) is not the start of a string of the names (an old build's offset: ' . PROF.',
   'ION' ...) gets the career league's name (slot 0's DIY+27h, repointed). */
static int str_ok(const u8 *s) {        /* the start of a name string (the names table / the game's strings)? */
    if (s[-1] || s[0] < 'A' || s[0] > 'Z') return 0;
    int n = 0;
    while (s[n] && n < 41) {
        u8 c = s[n++];
        if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == ' ' || c == '.' || c == '-' || c == '\'' || c == '/' || c == '&' || c == '(' || c == ')')) return 0;
    }
    return n >= 2 && !s[n];
}
GP_X3S const u8 *sc_entry(void);
static const u8 *usc_entry(void);
GP_X3S int usc_live(void);
void gp_fixload_c(const u32 *nm, u8 *recs, u32 base, u8 *const *slots, u32 phase) {
    if (phase == 0) {
        for (int i = 0; i < 2; i++) {
            struct gp_ko *k = &GP_ST.ko[i];
            if (k->magic != MAGIC || k->season != GP_SEAS) continue;
            u8 *c = k->con, *names = c + 5 + c[5];
            if (k->pi == 0xFF || k->kind == K_CUPD || k->kind == K_SC) {   /* 4.0.5 a one-tie contest (ko_one: the Coppa D's, a supercup): its names
                                           (STR_BASE-relative, saved with the career) from this exe's tables again -
                                           a 4.0.x save's pending Coppa D tie showed 'RV. TITOLO' / 'T. PRELIM.'
                                           (Ischia's: the strings moved since); never nm[3 * 255] ('SCENE
                                           PRESIDENZIALI') */
                const u8 *src = k->kind == K_CUPD && GP_CDT && GP_CDNM ? (const u8 *)GP_CDNM :
                                k->kind == K_SC ? (usc_live() ? usc_entry() : sc_entry()) : 0;
                if (src && k->kind == K_SC) src += 20;
                if (src) for (int j = 0; j < 8; j++) names[j] = src[j];
                continue;
            }
            if (!nm) continue;
            *(u32 *)names = nm[3 * k->pi];
            *(u32 *)(names + 4) = nm[3 * k->pi + 1];
        }
        return;
    }
    if (!slots || !recs || !slots[0]) return;
    u32 lg = *(const u32 *)(slots[0] + 0x27), cup = slots[1] ? *(const u32 *)(slots[1] + 0x27) : 0;
    for (int i = 0; i < 64; i++) {
        u8 *r = recs + 106 * i;
        if (!r[2]) break;
        for (int f = 0; f < 4; f++) {   /* +16h the league, +1Ah the national cup, +1Eh / +22h the continental cups */
            u32 *o = (u32 *)(r + 0x16 + 4 * f);
            if (!*o || str_ok((const u8 *)(base + *o))) continue;
            *o = f == 0 && lg ? lg - base : f == 1 && cup ? cup - base : 0;
        }
    }
}

/* 4.2 option C (strmap.py): a 4.1 save's season record lines through DATA\STRMAP41.DAT, before phase 1's heuristic -
   the 4.1 offsets whose name moved since, per language, sorted (old rel, new rel; 0 = gone: left to the heuristic).
   Only a 4.1 save: no release tag (someLeaguesTable[1842], trailer.py) and the engine block's 4.1 item seen (en41).
   Own DOS calls: a missing / foreign file = the heuristic alone. Returns the lines translated. */
#ifndef SM_LANG
#define SM_LANG 0
#endif
static char sm_fn[] = "data\\strmap41.dat";
static u32 sm_buf[256];                 /* (a 1 KB chunk of pairs; the header first) */
static u32 *sm_at[256];                 /* the lines to translate, sorted by their rel */
static int sm_dos(u32 ax, u32 bx, u32 cx, u32 dx) {
#if defined(__i386__)                   /* (the game's build; the engine's rules-check compiles gplay.c on the host:
                                           no DOS there - -1 = no file, the heuristic alone; as 9f33156's guard) */
    u32 r; u8 cf;
    __asm__ volatile("int $0x21; setc %1" : "=a"(r), "=qm"(cf), "+b"(bx), "+c"(cx), "+d"(dx) : "0"(ax) : "memory", "cc");
    return cf ? -1 : (int)(r & 0xFFFF);
#else
    (void)ax; (void)bx; (void)cx; (void)dx;
    return -1;
#endif
}
u32 gp_strmap_c(u8 *recs, u32 tag, u32 en41) {
    if (tag || !en41 || !recs) return 0;
    int n = 0;
    for (int i = 0; i < 64; i++) {
        u8 *r = recs + 106 * i;
        if (!r[2]) break;
        for (int f = 0; f < 4; f++) {
            u32 *o = (u32 *)(r + 0x16 + 4 * f), v = *o;
            if (!v) continue;
            int j = n++;
            while (j > 0 && *sm_at[j - 1] > v) { sm_at[j] = sm_at[j - 1]; j--; }
            sm_at[j] = o;
        }
    }
    if (!n) return 0;
    int h = sm_dos(0x3D00, 0, 0, (u32)sm_fn);
    if (h < 0) return 0;
    u32 done = 0, *b = sm_buf;
    if (sm_dos(0x3F00, (u32)h, 44, (u32)b) == 44 && b[0] == 0x50414D53 && b[1] == (1 | 41u << 16)
        && (b[2] & 0xFFFF) == 42) {
        u32 off = b[3 + 2 * SM_LANG], cnt = b[4 + 2 * SM_LANG];
        int k = 0;                      /* (the lines and the section, both sorted: one pass) */
        if (sm_dos(0x4200, (u32)h, off >> 16, off & 0xFFFF) >= 0)
            while (cnt && k < n) {
                u32 m = cnt > 128 ? 128 : cnt;
                if (sm_dos(0x3F00, (u32)h, 8 * m, (u32)b) != (int)(8 * m)) break;
                cnt -= m;
                for (u32 e = 0; e < m && k < n; e++) {
                    while (k < n && *sm_at[k] < b[2 * e]) k++;
                    while (k < n && *sm_at[k] == b[2 * e]) {
                        if (b[2 * e + 1]) { *sm_at[k] = b[2 * e + 1]; done++; }
                        k++;
                    }
                }
            }
    }
    sm_dos(0x3E00, (u32)h, 0, 0);
    return done;
}

static int title_is(const u8 *t, const u8 *s) {  /* a slot's title (DIY+4, 34 chars at most) is the name s */
    int j = 0;
    while (j < 34 && t[j] && t[j] == s[j]) j++;
    return j && (j == 34 || (!t[j] && !s[j]));
}
/* 4.2 (Regia 13/11, perf): the contest structs slots 2 / 3 can hold after a load (sacups.SLOT23: the euro chain's
   copies and originals, the SA cups, the extra / continental cups; gplay.py fills them after the link): their long
   names are where a slot's title is searched, else the slot's own title (b + 4). No byte scan of obj2 any more: a
   title in no candidate scanned all of it at every load (W84E's slot 3 ' COPPA CAMPIONI EUROPEA', in no exe: 36 of
   that load's 110 ticks at 486 speed); one it found was the slot's own title (4.1.1 cv_s2: INGHILTERRA EFL CUP,
   UEFA CHAMPIONS LEAGUE at b + 4, the lowest copy). */
#define GP_RPMAX 64
const u8 *GP_RPS[GP_RPMAX] = { (const u8 *)1 };   /* (not in .bss) */
u32 GP_RPSN = 1;

void gp_repoint_c(u8 *const *slots, u8 *const *structs, u32 base, u32 div, u32 lim) {
    for (int k = 0; k < 5; k++) {
        u8 *b = slots[k];
        const u8 *s = structs[k];
        if (k == 2 || k == 3) {         /* 4.2 the European / continental slots: their title (DIY+4, the long name,
                                           saved) finds the name in this exe - never D8CAA[k] alone: at a load
                                           D8CAA[3] may already be conti's next contest while the buffer is still
                                           this season's. The old absolute DIY+27h (another build's obj2) gave a
                                           wrong title and the season record's +1Eh / +22h line (DIY+27h -
                                           STR_BASE) at the season end. The candidates: D8CAA[k], the old
                                           pointer, GP_RPS (no obj2 byte scan, Regia 13/11). */
            if (!b || !b[4]) continue;
            const u8 *cur = *(const u8 *const *)(b + 0x27);
            if (!cur) continue;
            const u8 *ln = 0;
            if (s) {
                u32 r = *(const u32 *)(s + 5 + s[5]);
                if (r && r < lim - base && str_ok((const u8 *)(base + r)) && title_is(b + 4, (const u8 *)(base + r)))
                    ln = (const u8 *)(base + r);
            }
            if (!ln && (u32)cur > base && (u32)cur < lim && str_ok(cur) && title_is(b + 4, cur)) continue;
            for (u32 i = 0; !ln && i < GP_RPSN && i < GP_RPMAX; i++) {
                const u8 *c = GP_RPS[i];
                if ((u32)c < 0x1000) continue;
                u32 r = *(const u32 *)(c + 5 + c[5]);
                if (r && r < lim - base && str_ok((const u8 *)(base + r)) && title_is(b + 4, (const u8 *)(base + r)))
                    ln = (const u8 *)(base + r);
            }
            if (!ln && str_ok(b + 4)) ln = b + 4;   /* (no candidate: the slot's own title - where 5c658a3's byte
                                                       scan landed for such a save anyway: the lowest copy in obj2) */
            if (ln) *(const u8 **)(b + 0x27) = ln;
            continue;
        }
        if (!b || !s || !b[4]) continue;
        const u8 *nm = s + 5 + s[5] + (k == 0 ? 8 * div : 0);
        const u8 *ln = (const u8 *)(base + *(const u32 *)nm);
        *(const u8 **)(b + 0x27) = ln;
        int n = 0;
        while (ln[n] && n < 40) n++;
        if (!n) continue;
        int p = -1;                     /* the country prefix: up to the name's first word in the title */
        for (int i = 0; i < 34 && b[4 + i]; i++)
            if ((i == 0 || b[3 + i] == ' ')) {
                int j = 0;
                while (ln[j] && ln[j] != ' ' && b[4 + i + j] == ln[j]) j++;
                if (!ln[j] || ln[j] == ' ') { p = i; break; }
            }
        if (p <= 0 || p + n > 34) continue;
        int same = 1;
        for (int j = 0; j <= n; j++) if (b[4 + p + j] != ln[j]) { same = 0; break; }
        if (same) continue;
        for (int j = 0; j < n; j++) b[4 + p + j] = ln[j];
        for (int j = p + n; j < 35; j++) b[4 + j] = 0;
    }
}

/* The career club's result in a decided knockout, as the season record's codes (FillManagementRecordInfo): 1 WINNERS,
   -100 FINALIST (the last round lost), -101 REACHED SEMI-FINAL, -102 REACHED QUARTER-FINAL, -110 - n KNOCKED OUT IN
   ROUND n; 0: not in it / undecided. */
#ifndef GP_RLFORCE
#define GP_RLFORCE 0                    /* test builds (GPLAY_RLFORCE=code, never release): the career club's result in
                                           a contest it is in, read by the record lines only (no game flow) */
#endif
static int club_res(struct gp_ko *k, u16 mgr) {
    int me = mgr ? kidx(k, mgr) : NOC;
    if (me == NOC || !k->ntie) return 0;
    if (GP_RLFORCE) return GP_RLFORCE;
    resolve(k);
    if (k->tw[k->ntie - 1] == me) return 1;
    for (int t = 0; t < k->ntie; t++) {
        if (k->tl[t] != me) continue;
        int r = 0;
        while (r + 1 < k->nrs && t >= k->gt0[r + 1]) r++;
        int d = k->nrs - 1 - r;
        return d == 0 ? -100 : d == 1 ? -101 : d == 2 ? -102 : -(110 + r + 1);
    }
    return 0;
}

/* SeasonFinished (gp_sack): the season record's extra lines (GP_RLN names, GP_RLC result codes; the count returned):
   the Poule won (its record name, WINNERS); a stage title's knockout played (4.0 ARG: TORNEO APERTURA / CLAUSURA,
   TROFEO DE CAMPEONES: its long name and the club's result, from GP_ST.dec - stage_done - or ko[0]); a title
   play-off played (MLS CUP PLAYOFFS, CAN, AUS, CRC, MLT: the league's name with WINNERS, else the play-off's long
   name with the round reached). GP_RLPOULE: the Poule's line (the test builds' DA11B). */
u32 GP_RLN[4];
s8 GP_RLC[4];
u32 GP_RLPOULE;
u8 *GP_REC;                             /* the season record (106 B, gp_sack: GetCurrentSeasonPointer), or 0 */
const u32 *GP_CMB;                      /* the country's stage titles won together: one name per mask (bit = stage 0..2,
                                           relative, 0: none; gplay.py names_lines GPC) */
static int rl_rank(int c) {             /* a line's worth to keep (lower: replaced first by a title won): KNOCKED OUT IN
                                           ROUND n by n, then '-', still in, 4th, 3rd, quarter, semi, final lost */
    if (c <= -110) return -(c + 110);
    static const s8 ord[] = { -106, -104, -105, -103, -102, -101, -100, 2 };
    for (int i = 0; i < 8; i++) if (c == ord[i]) return 40 + i;
    return 48;
}
static int rl_n, rl_w;
static void rl_add(u32 name, int code) {
    if (rl_n >= 4) return;
    if (code == 1) {                    /* (titles won first, in their order) */
        for (int i = rl_n; i > rl_w; i--) { GP_RLN[i] = GP_RLN[i - 1]; GP_RLC[i] = GP_RLC[i - 1]; }
        GP_RLN[rl_w] = name; GP_RLC[rl_w++] = 1; rl_n++;
    } else { GP_RLN[rl_n] = name; GP_RLC[rl_n++] = (s8)code; }
}
u32 gp_rlines_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    int kstage = -1, wmask = 0, wd = 0;   /* (wd: the stage titles' division - the career club's) */
    u32 wname[3] = { 0, 0, 0 };
    rl_n = rl_w = 0;
    GP_RLPOULE = 0;
    int live = GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS && k->magic == MAGIC && k->season == GP_SEAS;
    if (live && k->kind == K_STAGE) {
        const u8 *s = po_at(k->pi);
        kstage = s ? s[3] & 3 : -1;
        wd = s && s[0] == K_STAGE ? s[3] >> 2 : 0;
    }
    for (int st = 0; st < 3 && GP_NM; st++) {       /* (the stage titles decided before: Apertura, Clausura, Trofeo) */
        const struct gp_dec *x = &GP_ST.dec[st];
        if (st == kstage || x->season != GP_SEAS || !x->done || !x->pad[0] || !x->pad[1]) continue;
        if (x->pad[0] == 1) {
            const u8 *ps = po_at(x->pad[1] - 1);
            wmask |= 1 << st; wname[st] = GP_NM[3 * (x->pad[1] - 1)];
            if (ps && ps[0] == K_STAGE) wd = ps[3] >> 2;
        }
        else rl_add(GP_NM[3 * (x->pad[1] - 1)], (s8)x->pad[0]);
    }
    u32 kn = 0;                         /* ko[0]'s line (after the stage titles) */
    int kr = 0;
    if (live && KT2(k)) {
        int me = kidx(k, GP_MGR);
        if (me != NOC) {
            if (GP_FORCE && !GF(k)) { k->tw[0] = me; k->tl[0] = me ? 0 : 1; }   /* (a Grand Final: its own result) */
            if (k->tw[0] == me) { kn = *(u32 *)k->bye; kr = 1; GP_RLPOULE = 1; }
            else if (GF(k) == GF_DONE && k->tl[0] == me && GP_NM) { kn = GP_NM[3 * k->pi]; kr = -100; }   /* (4.0.5 NZ:
                                           the Grand Final lost - FINALIST, as the title play-offs' lines) */
        }
    } else if (live && (k->kind == K_TITLE || k->kind == K_STAGE) && GP_NM) {
        int r = club_res(k, GP_MGR);    /* (SeasonFinished comes before the season end's gp_season: the contest itself) */
        if (r == 1 && k->kind == K_STAGE && kstage >= 0 && kstage < 3) { wmask |= 1 << kstage; wname[kstage] = GP_NM[3 * k->pi]; }
        else if (r) { kn = GP_NM[3 * k->pi + (r == 1 && k->kind == K_TITLE ? 2 : 0)]; kr = r; }
    }
    if (wmask & (wmask - 1) && GP_CMB && GP_CMB[wmask + 8 * (wd & 3)]) {   /* (several stage titles of the league:
                                                                           one line, Davide; 8 masks per division) */
        rl_add(GP_CMB[wmask + 8 * (wd & 3)], 1);
        wmask = 0;
    }
    for (int st = 0; st < 3; st++)      /* (else one line each, in stage order) */
        if (wmask & 1 << st) rl_add(wname[st], 1);
    if (kr) rl_add(kn, kr);
    { u32 sn = sc_rline(); if (sn) rl_add(sn, 1); }   /* (4.0.5: a national supercup won) */
    { u32 sn = usc_rline(); if (sn) rl_add(sn, 1); }  /* (4.0.6: the UEFA Super Cup won) */
#if GP_PORT
    port_rlines();                      /* (4.2: the port's mini-leagues won - the Supercoppa Serie C) */
#endif
    rl_put();
    return rl_n;
}
/* 4.1.2 (Enzo, Davide 12/11; split.py zp_bonus): the stage titles (Apertura, Clausura, Trofeo) the club mgr won
   this season, for the chairman's season-end opinion in a league in zones (each one counts as a cup won). The same
   sources as gp_rlines_c: GP_ST.dec (stages decided before) and ko[0] (the stage knockout still live). Read only. */
u32 gp_stwins_c(u32 mgr) {
    struct gp_ko *k = &GP_ST.ko[0];
    int kstage = -1;
    u32 n = 0;
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS) return 0;
    int live = k->magic == MAGIC && k->season == GP_SEAS && k->kind == K_STAGE;
    if (live) {
        const u8 *s = po_at(k->pi);
        kstage = s ? s[3] & 3 : -1;
    }
    for (int st = 0; st < 3; st++) {
        const struct gp_dec *x = &GP_ST.dec[st];
        if (st == kstage || x->season != GP_SEAS || !x->done || !x->pad[1]) continue;
        if (x->pad[0] == 1) n++;
    }
    if (live && kstage >= 0 && club_res(k, (u16)mgr) == 1) n++;
    return n;
}
#if GP_PORT
static void port_rlines(void) {
    u32 sn;
    for (u32 k = 0; GP_PRLINE && k < 2 && (sn = GP_PRLINE(k)); k++) rl_add(sn, 1);
}
#endif
u32 sc_rlines_c(void) {                 /* 4.0.5 (gp_rl, a league with no gplay play-offs: LaLiga, Serie A): only a
                                           national supercup won */
    rl_n = rl_w = 0;
    u32 sn = sc_rline();
    if (sn) rl_add(sn, 1);
    if ((sn = usc_rline())) rl_add(sn, 1);   /* (4.0.6: the UEFA Super Cup won) */
    rl_put();
    return rl_n;
}
static void rl_put(void) {
    if (GP_REC) {                       /* each into its line if there already, else the first free line 4 / 3 / 2; a
                                           title won with none free: in place of the game's weakest non-winning line (an
                                           elimination, Davide), not ours */
        int ours = 0;
        for (int i = 0; i < rl_n; i++) {
            int at = -1;
            for (int o = 3; o >= 1 && at < 0; o--)  /* (already there: a second pass - REGISTRO GESTIONE's refresh,
                                                       gp_mrec - only restores its code) */
                if (!(ours & 1 << o) && *(u32 *)(GP_REC + 22 + 4 * o) == GP_RLN[i]) at = o;
            for (int o = 3; o >= 1 && at < 0; o--) if (!*(u32 *)(GP_REC + 22 + 4 * o)) at = o;
            if (at < 0 && GP_RLC[i] == 1) {
                int best = 99;
                for (int o = 3; o >= 1; o--) {
                    int c = (s8)GP_REC[86 + o];
                    if (ours & 1 << o || c == 1 || rl_rank(c) >= best) continue;
                    best = rl_rank(c); at = o;
                }
            }
            if (at < 0) continue;
            *(u32 *)(GP_REC + 22 + 4 * at) = GP_RLN[i];
            GP_REC[86 + at] = (u8)GP_RLC[i];
            ours |= 1 << at;
        }
    }
}

u32 gp_pwin_c(void) {
    struct gp_ko *k = &GP_ST.ko[0];
    if (GP_ST.magic != MAGIC || GP_ST.season != GP_SEAS || k->magic != MAGIC || k->season != GP_SEAS)
        return 0;
    int me = kidx(k, GP_MGR);
    if (me == NOC) return 0;
    if (KT2(k)) {
        if (GP_FORCE && !GF(k)) { k->tw[0] = me; k->tl[0] = me ? 0 : 1; }   /* (a Grand Final: its own result) */
        return k->tw[0] == me ? *(u32 *)k->bye : 0;
    }
    if (k->kind != K_TITLE || !GP_NM || !k->ntie) return 0;   /* a played title play-off (CAN, AUS, CRC, MLT) won:
                                           its last tie's winner (SeasonFinished comes before the season end's
                                           gp_season: the contest itself, not GP_OUT); the line: the league's name
                                           (compile_spec's league_names). The club keeps its table place. */
    resolve(k);
    return k->tw[k->ntie - 1] == me ? GP_NM[3 * k->pi + 2] : 0;
}

/* RI_TAB (ripool.table_bytes): a league pool's slot (kind 0) of world w with global g -> its lowest level's first
   division and base division (gp_sack_c) */
static int ri_league_slot(const u8 *t, int w, int g, int *low, int *base) {
    int nf = *t++;
    for (int fi = 0; fi < nf; fi++) {
        int world = t[0], np = t[2], nsp = t[9];
        t += 10 + nsp;
        for (int k = 0; k < np; k++) {
            int kind = t[0], n = t[1];
            const u8 *p = t + 2;
            if (kind == 0) {
                int lw = p[0], ns = p[1] | p[2] << 8;
                const u8 *sl = p + 3;
                for (int i = 0; world == w && i < ns; i++)
                    if ((sl[4 * i] | sl[4 * i + 1] << 8) == g) { *low = lw; *base = sl[4 * i + 2]; return 1; }
                t = sl + 4 * ns + n + n;
            } else {
                int ns = p[3];
                const u8 *ps = p + 4 + 4 * ns;
                int ne = ps[n];
                t = ps + n + 1 + 2 * ne + n;
            }
        }
    }
    return 0;
}

u32 gp_sack_c(void) {
    const struct gp_ko *k = &GP_ST.ko[0];
    if (GP_ST.magic == MAGIC && GP_ST.season == GP_SEAS && k->magic == MAGIC && k->season == GP_SEAS && k->kind == 4
        && k->ldiv == RESERVE) {        /* (a play-out into the reserve, played: its last round's losers) */
        int r = k->nrs - 1;
        for (int t = k->gt0[r]; t < k->gt0[r + 1]; t++)
            if (k->tl[t] != NOC && IS_MGR(k->team[k->tl[t]])) return 1;
    }
    if ((!GP_RST && !GP_RIT) || !GP_CFB || !GP_LG) return 0;
    const u8 *d = GP_CFB;
    int n = *(const u16 *)(d + 0x31), m = -1, off = 0;
    for (int j = 0; j < n && j < GT; j++) {
        int o = *(const u16 *)(d + 0x6D + 2 * j);
        if (IS_MGR(*(const u16 *)(d + 0x12D + 2 * (o / 0x12)))) { m = j; off = o; }
    }
    if (m < 0) return 0;
    if (GP_FORCE) m = GP_FORCE - 1;
    u16 g = *(const u16 *)(*(const u32 *)(d + off + 0x2B3) + GP_SEL + 2);
    int low, base;                       /* the off-file pools (ripool: RI_TAB; a swap never takes the manager's club) */
    if (GP_RIT && ri_league_slot(GP_RIT, GP_WORLD, g, &low, &base)) {
        int dv = base + GP_SLT[g];
        return dv >= low && dv < GD && m >= n - GP_LG[13 + 6 * dv + 3];
    }
    const u8 *t = GP_RST;
    for (int cnt = t ? *t++ : 0; cnt > 0; cnt--) {
        int w = t[0], nd = t[1], low = t[2], nc = t[3] | t[4] << 8;
        const u8 *c = t + 5, *pl = c + 3 * nc;
        t = pl + 1 + 2 * pl[0];
        if (w != GP_WORLD) continue;
        for (int i = 0; i < nc; i++)
            if ((c[3 * i] | c[3 * i + 1] << 8) == g) {     /* its division now: base + someLeaguesTable[g] */
                int dv = c[3 * i + 2] + GP_SLT[g];
                return dv >= low && dv < nd && m >= n - GP_LG[13 + 6 * dv + 3];   /* (among its relegated) */
            }
    }
    return 0;
}

const u32 GP_LAYOUT2[] = { __builtin_offsetof(struct gp_in, mgr), __builtin_offsetof(struct gp_in, week),
                           __builtin_offsetof(struct gp_in, mdiv), __builtin_offsetof(struct gp_in, gtype),
                           __builtin_offsetof(struct gp_in, sim), sizeof(struct gp_ko),
                           __builtin_offsetof(struct gp_state, ko), __builtin_offsetof(struct gp_ko, season),
                           __builtin_offsetof(struct gp_ko, cid), __builtin_offsetof(struct gp_ko, n),
                           __builtin_offsetof(struct gp_ko, team), __builtin_offsetof(struct gp_ko, bye),
                           __builtin_offsetof(struct gp_ko, con), sizeof(struct gp_state), sizeof(struct gp_log),
                           __builtin_offsetof(struct gp_ko, slot), __builtin_offsetof(struct gp_state, rn),
                           __builtin_offsetof(struct gp_ko, gcur) };

/* Parallel groups at the season end (pgroups.py: InitializeNewSeason's copy-back, leaguesTableCopy -> someLeaguesTable).
   The table: db count; per country db world, levels; per level db first division, groups, sizes[groups] (top-down,
   all the chain's divisions); db parallel levels np; dw clubs; clubs x (dw global number, db base division,
   np x db area: per level of groups its group index, 0xFF = none). The game moved each club by its division's
   promoted / relegated counts: one division up or down the chain. Here a move is one LEVEL up or down instead: into a
   single division as it is, into a level of groups to the group of the club's area for that level, else the nearest
   one with room (each group keeps its size). A division past the chain (the reserve, gplay's 'reserve') is a level of
   its own below the last one. */
enum { PL = 8, PG = 9 };                    /* (Serie D 2026-27: 9 groups) */
static u8 pg_pend[4096 / 8];                      /* (bits, by global number) */
#define PEND(g) (pg_pend[(g) >> 3] & (1 << ((g) & 7)))

static int pg_level(int d, int nl, const u8 *first, const u8 *cnt) {
    if (d >= first[nl - 1] + cnt[nl - 1]) return nl;   /* (out of the chain: the reserve) */
    for (int l = nl - 1; l >= 0; l--) if (d >= first[l]) return l;
    return 0;
}

/* The off-file pool's swapped slots this season end (ri_season, before pg_season): each enters the lowest level from
   below the chain (its identity is new) and goes to the group of the NEW identity's area (every season: ripool's
   ri_ida gives each swapped slot's pgroups entry its current identity's areas before pg_season). */
enum { RIO = 64 };
static u16 ri_og[RIO];
extern int RI_MGR;                     /* (the manager's club, below: the geography chain never moves it) */
static int ri_no;
static int ri_over(int g) {
    for (int i = 0; i < ri_no; i++) if (ri_og[i] == g) return i;
    return -1;
}

static int pg_room(int a, int n, const u8 *occ, const u8 *sz) {   /* group a, else the nearest one with room (else a) */
    for (int k = 0; k < PG; k++) {
        if (a + k < n && occ[a + k] < sz[a + k]) return a + k;
        if (a - k >= 0 && occ[a - k] < sz[a - k]) return a - k;
    }
    return a;
}

/* 4.0.5 (Serie C groups from the real compositions, Francesco's ISCHIA report): a club's area byte per level of groups
   holds two choices, low nibble the 1st, high nibble the 2nd + 1 (1 = A; 0 or 0xF: none, 0xE: any group - a second
   team, U23) and its bit 3 = never another group (a northern club never in C, a southern one never in A; levels of up
   to 7 groups).
   Serie C's choices come from where the Lega Pro put each region's clubs in 2016-17..2025-26 (never north <-> south);
   the second teams went to any group and were moved to balance. Raw area bytes 0..8 (ripool's pool areas): 1st only. */
#define A1(b) ((b) & 15)
static int pg_a2(int b) { int h = b >> 4; return h == 0 || h == 15 || !(h & 7) ? 15 : h == 14 ? 14 : (h & 7) - 1; }
                                        /* (4.0.6: !(h & 7) - a 2nd choice H, or a ban with none, read as no 2nd choice:
                                           (h & 7) - 1 = -1 indexed occ[tl][-1] - clang's analyzer; the data's 2nd
                                           choices are A..C) */
static int pg_ban(int b) { int h = b >> 4; return h != 0 && h < 14 && (h & 8); }

/* A club placed in group a of level tl that can leave to make room: a second team first (to the group with room
   nearest to a), else a club out of its 1st choice whose 1st choice has room, else one out of both choices whose
   2nd choice has room, else one in its 1st choice whose 2nd choice has room (a centre club to C so that a northern
   club gets B), else a club free to go anywhere (2 choices, no ban: a centre club) to the nearest group with room. Moves it and
   returns 1; 0 = none (ao: the area byte's offset in a club entry, -1 none). */
static int pg_make_room(const u8 *c, int rs, int nc, int g, int tl, int a, const u8 *first, const u8 *cnt,
                        const u8 *const *sz, u8 (*occ)[PG], int ao, s8 *copy) {
    if (ao < 0) return 0;
    for (int pass = 0; pass < 5; pass++)
        for (int j = 0; j < nc; j++) {
            const u8 *f = c + rs * j;
            int h = f[0] | f[1] << 8, hb = f[2];
            if (h == g || h >= 8 * (int)sizeof pg_pend || PEND(h) || copy[h] + hb != first[tl] + a) continue;
            int b = f[ao], h1 = A1(b), h2 = pg_a2(b), w = 99;
            if (pass == 0 ? h2 == 14 : pass == 4 && h2 < cnt[tl] && !pg_ban(b))   /* (4: 2-choice data only) */
                w = pg_room(a, cnt[tl], occ[tl], sz[tl]);   /* (a is full: the nearest other group with room) */
            else if (h2 != 14)
                w = pass == 1 ? (h1 != a ? h1 : 99) : pass == 2 ? (h1 != a && h2 != a ? h2 : 99) : pass == 3 && h1 == a ? h2 : 99;
            if (w == a || w >= cnt[tl] || occ[tl][w] >= sz[tl][w]) continue;
            occ[tl][w]++;
            occ[tl][a]--;
            copy[h] = first[tl] + w - hb;
            return 1;
        }
    return 0;
}

static const u8 *pg_one(const u8 *t, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 2; pass++)
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            if (pass == 1) {                    /* into a level of groups: the area's, else the nearest with room */
                if (!PEND(g)) continue;
                pg_pend[g >> 3] &= ~(1 << (g & 7));
                int n = copy[g] + base, o = slt[g] + base;       /* (copy still the game's move) */
                int ov = ri_over(g);
                if (ov >= 0) { o = first[nl - 1] + cnt[nl - 1]; n = first[nl - 1]; }   /* (a new identity from below) */
                int lo = pg_level(o, nl, first, cnt), tl = n < o ? lo - 1 : lo + 1;
                int ab = pidx[tl] < npar ? e[3 + pidx[tl]] : 0xFF;    /* (a swapped slot: its identity's, ripool's
                                                   ri_ida; a new identity from below: its lowest level's area) */
                int area = A1(ab), area2 = pg_a2(ab), ao = pidx[tl] < npar ? 3 + pidx[tl] : -1;
                int a = area < cnt[tl] ? area : ab == 0xFF ? cnt[tl] / 2 : cnt[tl] - 1, to = -1;
                for (int k = 0; k < 2 && to < 0; k++) {     /* its 1st choice, then its 2nd: room, else make room */
                    int w = k ? area2 : area;
                    if (w >= cnt[tl]) continue;
#if GP_S7
                    if (!k && ov >= 0 && GP_GEOCH && occ[tl][w] >= sz[tl][w] &&     /* (a pool arrival: the chain, 4.2 geography) */
                        GP_GEOCH(c, rs, nc, first[tl], w, cnt[tl], sz[tl], occ[tl], slt, copy, pg_pend, (int)sizeof pg_pend * 8,
                                 ri_og, ri_no, RI_MGR))
                        { to = w; continue; }
#endif
                    if (occ[tl][w] < sz[tl][w] || pg_make_room(c, rs, nc, g, tl, w, first, cnt, sz, occ, ao, copy))
                        to = w;
                }
                if (to < 0) to = pg_room(a, cnt[tl], occ[tl], sz[tl]);   /* (a second team, or no choice fits: nearest) */
                occ[tl][to]++;
                copy[g] = first[tl] + to - base;
                continue;
            }
            int o = slt[g] + base, n = copy[g] + base;
            if (ri_over(g) >= 0) { o = first[nl - 1] + cnt[nl - 1]; n = first[nl - 1]; }
            int lo = pg_level(o, nl, first, cnt);
            int tl = n < o ? lo - 1 : n > o ? lo + 1 : lo;
            if (tl < 0 || tl >= nl) continue;   /* (off the chain, or into the reserve: as moved) */
            if (tl == lo) {                     /* staying: counted in its group */
                if (o - first[lo] < cnt[lo]) occ[lo][o - first[lo]]++;
            } else if (cnt[tl] == 1)
                copy[g] = first[tl] - base;
            else
                pg_pend[g >> 3] |= 1 << (g & 7);
        }
    return c + rs * nc;
}

void pg_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pg_one(t, slt, copy, t[0] == world);
#if GP_HOOK
    if (GP_PSEAS) GP_PSEAS();           /* (4.2 fixture port: pg_fix, InitializeNewSeason - every career, seasonPlaying
                                           already the new one: fpad.c fp_season arms, the next fp_step inits; MC 14/11:
                                           0 B in pgroups' extra pages) */
#endif
}

/* A save from before the groups (3.x: pgroups.py's table on a chain the save's divisions don't know). Every club of
   the table: its division now (base + slt), through map (old division -> new, 0xFF = the same), to its level on the
   new chain; a single division as it is, a level of groups to the group of its area, else the nearest with room (the
   clubs with an area first, so every group keeps its size). A map value 0x80 | division pins the club to exactly
   that division (4.0: a 3.x career's live 18-club league kept together for its current season), counted before the
   others are placed. copy = the result (not slt: slt is read again). */
static const u8 *pl_one(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int run) {
    int nl = t[1];
    u8 first[PL], cnt[PL], occ[PL][PG], pidx[PL];
    const u8 *sz[PL], *p = t + 2;
    int np = 0;
    for (int l = 0; l < nl; l++) {
        if (l < PL) { first[l] = p[0]; cnt[l] = p[1] > PG ? PG : p[1]; sz[l] = p + 2; pidx[l] = p[1] > 1 ? np++ : 0xFF;
                      for (int g = 0; g < PG; g++) occ[l][g] = 0; }
        p += 2 + p[1];
    }
    int npar = p[0], nc = p[1] | p[2] << 8, rs = 3 + npar;
    const u8 *c = p + 3;
    if (!run || nl > PL) return c + rs * nc;
    for (int pass = 0; pass < 3; pass++)        /* 0: single divisions, 1: groups of the area, 2: the nearest */
        for (int i = 0; i < nc; i++) {
            const u8 *e = c + rs * i;
            int g = e[0] | e[1] << 8, base = e[2];
            if (g >= 8 * (int)sizeof pg_pend) continue;
            int d = slt[g] + base, pin = 0;
            if (d >= 0 && d < 256 && map[d] != 0xFF) { pin = map[d] & 0x80; d = map[d] & 0x7F; }
            int l = pg_level(d, nl, first, cnt);
            if (l >= nl) { if (pass == 0) copy[g] = d - base; continue; }    /* (the reserve: as it is) */
            if (cnt[l] == 1) { if (pass == 0) copy[g] = first[l] - base; continue; }
            if (pin) {                          /* pinned (map 0x80 | division): exactly that group, counted first */
                if (pass == 0) { copy[g] = d - base; if (d - first[l] < PG) occ[l][d - first[l]]++; }
                continue;
            }
            if (pass == 0) { pg_pend[g >> 3] |= 1 << (g & 7); continue; }
            if (!PEND(g)) continue;
            int area = pidx[l] < npar ? e[3 + pidx[l]] : 0xFF, to = -1;
            if (pass == 1) {
                if (area < cnt[l] && occ[l][area] < sz[l][area]) to = area;
            } else {
                int a = area < cnt[l] ? area : cnt[l] / 2;
                for (int k = 0; k < PG && to < 0; k++) {
                    if (a + k < cnt[l] && occ[l][a + k] < sz[l][a + k]) to = a + k;
                    else if (a - k >= 0 && occ[l][a - k] < sz[l][a - k]) to = a - k;
                }
                if (to < 0) to = a;             /* (more clubs than room: the area's group) */
            }
            if (to < 0) continue;
            pg_pend[g >> 3] &= ~(1 << (g & 7));
            occ[l][to]++;
            copy[g] = first[l] + to - base;
        }
    return c + rs * nc;
}

void pg_place(const u8 *t, const u8 *map, const s8 *slt, s8 *copy, int world) {
    for (int k = *t++; k > 0; k--)
        t = pl_one(t, map, slt, copy, t[0] == world);
}

/* The reserve (gplay loser_div 'reserve', pack.json league 'reserve', engine.reserve): a pool of clubs out of every
   division (division nd). At the season end (pg_fix, before pg_season places the new clubs by area) every club that
   went down from the lowest level (the game's relegation, gplay's play-out) leaves for the reserve, and as many come
   back from it to the lowest level: the longest out first (the queue: the pool's first order, then each season's
   relegated at its end). Table: db count; per country db world, nd, low (the lowest level's first division); dw clubs;
   clubs x (dw global, db base division); db pool; pool x dw global. State RS_STATE (saved by the engine block):
   per country db init, n, -, -; dw q[RQ]. */
enum { RQ = 64, RC = 8 };
struct rs_state { u8 init, n, pad[2]; u16 q[RQ]; };
struct rs_state RS_STATE[RC];
const u32 RS_STATE_SIZE = sizeof RS_STATE;          /* (gplay.RS_SIZE: the engine block item 'RS') */

static int rs_base(const u8 *c, int nc, int g) {
    for (int i = 0; i < nc; i++) if ((c[3 * i] | c[3 * i + 1] << 8) == g) return c[3 * i + 2];
    return -1;
}

void rs_season(const u8 *t, const s8 *slt, s8 *copy, int world) {
    int cnt = *t++;
    for (int k = 0; k < cnt; k++) {
        int w = t[0], nd = t[1], low = t[2], nc = t[3] | t[4] << 8;
        const u8 *c = t + 5, *pl = c + 3 * nc, *pg = pl + 1;
        int np = pl[0];
        t = pg + 2 * np;
        if (w != world || k >= RC) continue;
        struct rs_state *st = &RS_STATE[k];
        if (!st->init) {                        /* (a new career: the pool's first order) */
            st->n = 0;
            for (int i = 0; i < np && i < RQ; i++) st->q[st->n++] = pg[2 * i] | pg[2 * i + 1] << 8;
            st->init = 1;
        }
        u16 out[RQ];
        int no = 0;
        for (int i = 0; i < nc; i++) {          /* down from the lowest level: out, to the reserve */
            int g = c[3 * i] | c[3 * i + 1] << 8, base = c[3 * i + 2];
            int o = base + slt[g], n = base + copy[g];
            if (o >= low && o < nd && n > o && no < RQ) { out[no++] = g; copy[g] = nd - base; }
        }
        int up = no < st->n ? no : st->n, m = 0;
        for (int i = 0; i < up; i++) {          /* back: to the lowest level's first division (pg_season: by area) */
            int g = st->q[i], base = rs_base(c, nc, g);
            if (base >= 0) copy[g] = low - base;
        }
        for (int i = up; i < st->n; i++) st->q[m++] = st->q[i];
        for (int i = 0; i < no && m < RQ; i++) st->q[m++] = out[i];
        st->n = m;
    }
}

/* Off-file pools (mkseason Pack.off_pools): a team file's slots swap IDENTITIES with an off-file pool instead of
   clubs leaving the world. Per team file (up to RF; one RS file each, DATA\RS<world><file>.DAT): identity 0..255 = the
   file's own records (file order), 256 + k = the RS file's record k; map[slot] = identity + 1 (0 = the slot itself: a
   cleared item is the start). Per pool (up to RP) a queue of identities out: the pool's first order at the first
   season end, each season's relegated at its tail (rotation: its length stays the pool's size).
   - kind 0, a league's lowest level (Eccellenza: Italy's 256 slots are the whole file): every slot relegated from
     the lowest level (o in it, n below) keeps its slot and its level; pg_season places the new identity by area;
   - kind 1, a state championship (Brazil 2026: the state-only clubs of file 161): its n relegated = the bottom state-
     only clubs of the state's stage-1 ranking (RI_SR, statespec's 'SR' item: dw first club, db n, db 0, n x dw team
     word, best first) when the career played it; else by RI_RULE (0 none, 1 the weakest n, 2 a draw weighted by
     weakness). Never the manager's club (RI_MGR, global number).
   Table: db files; per file: db world, file, pools; per pool: db kind, n (pool records), then
     kind 0: db low; dw slots; slots x (dw global, db base division, db D area); n x db D area;
     kind 1: dw key (the state's first club's team word); db relegated; db slots; slots x (db ordinal, dw global,
             db strength); n x db strength; db entries; entries x dw the contest's original team words;
     then n x db RS record (the pool's first order).
   Exact state relegation (Davide 2026-10-19): a LEAGUE club relegated from its state leaves the state contest (its
   national place kept) and waits in the queue as a marker 0x8000 | its entry; the A2 club coming in takes a free
   SPARE slot of the file (pack.json "state_spares": the file's last ordinals, in no contest), and the contest's entry
   points to it: RI_STATE.ovr[pool][entry] = the new team word (0 = the original), applied to the contest list by
   statecup (package 5) after every load and at the season start. A marker at the queue's head brings its league
   club back (its spare's identity moves to the slot that goes down, or the spare passes to the entry that goes down).
   No spare free: that league club stays (declared approximation). File header: db world, file, pools; dw base;
   dw map offset (words in RI_STATE.maps), dw slots (the file's records); db spares; spares x db ordinal. */
enum { RIS = 256, RF = 8, RP = 20, RQT = 192, RO = 16, RMT = 640 };
_Static_assert(RF == CD_RF, "cd_season's view of the pools' files");
struct ri_state { u8 init[RF]; u8 qn[RP]; u16 q[RQT]; u16 ovr[RP][RO]; u16 maps[RMT]; };   /* (maps: per file its
                                                   slots only, from the table's map offset) */
struct ri_file { u8 *init; u16 *map; int n; };   /* (a file's view of RI_STATE) */
struct ri_state RI_STATE;
u8 RI_SWAPPED[RF][RIS / 8];                     /* (this season end's swapped slots: ri_cache) */
int RI_MGR;                                     /* (the manager's club, global number: set by the glue, never swapped) */
int RI_RULE = 2;
u8 RI_FILES_FILE[RF];                           /* (each table file's team file number, set by ri_season) */
const u32 RI_STATE_SIZE = sizeof(struct ri_state);   /* (the engine item 'RI': ripool.RI_SIZE) */
static u32 ri_rng;

static u32 ri_rand(u32 n) {
    ri_rng = ri_rng * 1103515245u + 12345u;
    return n ? (ri_rng >> 8) % n : 0;
}

/* one swap: slot i of file fi takes the queue head of the pool (q = its queue, *qn its length, m = this season's
   takes so far), its identity goes out */
static int ri_swap(struct ri_file *f, int fi, int i, u16 *q, int qn, int m, u16 *out, int *no) {
    if (m >= qn) return -1;
    int was = f->map[i] ? f->map[i] - 1 : i, in = q[m];
    out[(*no)++] = was;
    f->map[i] = in == i ? 0 : in + 1;
    RI_SWAPPED[fi][i >> 3] |= 1 << (i & 7);
    return in;
}

static int ri_id(struct ri_file *f, int x) { return f->map[x] ? f->map[x] - 1 : x; }
int cd_ident(int m, int i) { return m < RMT && RI_STATE.maps[m] ? RI_STATE.maps[m] - 1 : i; }   /* (gplay's Coppa D) */
static void ri_set(struct ri_file *f, int fi, int x, int id) {
    f->map[x] = id == x ? 0 : id + 1;
    RI_SWAPPED[fi][x >> 3] |= 1 << (x & 7);
}

/* a free spare of the file (pools p0 .. p0 + np - 1 of it hold its overrides), or -1 */
static int ri_spare(const u8 *sp, int ns, int file, int p0, int np) {
    for (int s = 0; s < ns; s++) {
        int w = file | sp[s] << 8, used = 0;
        for (int p = p0; p < p0 + np && p < RP; p++)
            for (int j = 0; j < RO; j++) if (RI_STATE.ovr[p][j] == w) used = 1;
        if (!used) return sp[s];
    }
    return -1;
}

static const u8 *ri_pool(const u8 *e, struct ri_file *f, int fi, u16 *q, u8 *qn, const s8 *slt, s8 *copy,
                         const u8 *sr, int run, int pi, int base, const u8 *sp, int nsp, int p0, int np) {
    int kind = e[0], n = e[1], manager = RI_MGR;
    const u8 *p = e + 2, *order;
    u16 out[64];
    int no = 0, m = 0;
    if (kind == 0) {
        int low = p[0], ns = p[1] | p[2] << 8;
        const u8 *sl = p + 3, *pa = sl + 4 * ns;
        order = pa + n;
#if GP_S7
        int s7p = 0;
        if (run && GP_RIPOOL) {                 /* S7 builds (s7ri.c): the registry decides for the S7 pooled file (-1: another file) */
            m = GP_RIPOOL(e, q, qn, *f->init, RI_FILES_FILE[fi], slt, copy, manager, ri_og, &ri_no, out, &no, f->map, f->n);
            if (m >= 0) s7p = 1; else m = 0;
        }
        if (!s7p)
#endif
        {
        if (run && *f->init == 1) {
            for (int i = 0; i < n; i++) q[i] = RIS + order[i];
            *qn = n;
        }
        for (int i = 0; run && i < ns && i < RIS && ri_no < RIO && m < *qn && no < 64; i++) {
            const u8 *s = sl + 4 * i;
            int g = s[0] | s[1] << 8, base = s[2];
            int o = base + slt[g], nn = base + copy[g];
            if (o < low || nn <= o) continue;   /* (relegated from the lowest level) */
            if (g == manager) {                 /* never the manager's: re-admitted, its slot and identity stay in the
                                                   lowest level (a relegated manager is sacked by gp_sack, so this is
                                                   a job taken at the season end - accepted before ContinueCareer's
                                                   moves - at a club going down: left below it, the career trapped) */
                copy[g] = slt[g];
                continue;
            }
            ri_swap(f, fi, i, q, *qn, m++, out, &no);
            ri_og[ri_no++] = g;
            copy[g] = slt[g];                   /* (the slot stays; pg_season places its new identity by area) */
        }
        }
    } else {
        int key = p[0] | p[1] << 8, rel = p[2], ns = p[3], file = RI_FILES_FILE[fi];
        const u8 *sl = p + 4, *ps = sl + 4 * ns, *en = ps + n + 1;
        int ne = ps[n];
        order = en + 2 * ne;
        u16 *ovr = RI_STATE.ovr[pi < RP ? pi : RP - 1];
        if (run && *f->init == 1) {
            for (int i = 0; i < n; i++) q[i] = RIS + order[i];
            *qn = n;
            for (int j = 0; j < RO; j++) ovr[j] = 0;
        }
        u16 rw[16];                             /* the relegated, as the contest's current team words */
        int nr = 0;
        const u8 *b = sr;
        while (run && b && (b[0] | b[1] << 8)) {    /* statespec's rankings ('SR'): this state's last 'rel' */
            int nb = b[2];
            if ((b[0] | b[1] << 8) == key) {
                for (int k = nb - rel < 0 ? 0 : nb - rel; k < nb && nr < 16; k++) rw[nr++] = b[4 + 2 * k] | b[5 + 2 * k] << 8;
                break;
            }
            b += 4 + 2 * nb;
        }
        if (run && !(b && (b[0] | b[1] << 8)) && RI_RULE) {    /* no ranking: the fallback among the state-only */
            u8 st[RIS], pick[RIS / 8];
            int smax = 0;
            for (int i = 0; i < RIS / 8; i++) pick[i] = 0;
            for (int i = 0; i < ns; i++) {
                int id = ri_id(f, sl[4 * i]), s = 0;
                for (int jj = 0; id < RIS && jj < ns; jj++) if (sl[4 * jj] == id) s = sl[4 * jj + 3];
                for (int jj = 0; id >= RIS && jj < n; jj++) if (order[jj] == id - RIS) s = ps[jj];
                st[i] = s;
                if (s > smax) smax = s;
            }
            for (int r = 0; r < rel && nr < 16; r++) {
                u32 tot = 0;
                int best = -1;
                for (int i = 0; i < ns; i++) {
                    int o = sl[4 * i];
                    if (pick[o >> 3] & 1 << (o & 7)) continue;
                    u32 wgt = smax + 1 - st[i];
                    if (RI_RULE == 1) { if (best < 0 || st[i] < st[best]) best = i; }
                    else tot += wgt * wgt;
                }
                if (RI_RULE == 2 && tot) {
                    u32 x = ri_rand(tot);
                    for (int i = 0; i < ns; i++) {
                        int o = sl[4 * i];
                        if (pick[o >> 3] & 1 << (o & 7)) continue;
                        u32 wgt = smax + 1 - st[i];
                        if (x < wgt * wgt) { best = i; break; }
                        x -= wgt * wgt;
                    }
                }
                if (best < 0) break;
                int o = sl[4 * best];
                pick[o >> 3] |= 1 << (o & 7);
                rw[nr++] = file | o << 8;
            }
        }
        for (int r = 0; r < nr && m < *qn && no < 64; r++) {
            int j = -1;
            for (int k = 0; k < ne && k < RO; k++)
                if ((ovr[k] ? ovr[k] : (en[2 * k] | en[2 * k + 1] << 8)) == rw[r]) j = k;
            if (j < 0) continue;
            int cur = ovr[j] ? ovr[j] : (en[2 * j] | en[2 * j + 1] << 8);
            int league = (cur & 0xFF) != file, x = cur >> 8;
            if (!league && base + x == manager) continue;   /* (never the manager's club) */
            int in = q[m], outid = league ? 0x8000 | j : ri_id(f, x);
            if (in & 0x8000) {                  /* a league club comes back: its spare's identity / the spare */
                int k = in & 0xFF, sw = ovr[k];
                if (k >= RO || !sw) continue;
                ovr[k] = 0;
                if (league) ovr[j] = sw;
                else ri_set(f, fi, x, ri_id(f, sw >> 8));
            } else if (league) {                /* a league club goes: the A2 club into a free spare */
                int s = ri_spare(sp, nsp, file, p0, np);
                if (s < 0) continue;
                ri_set(f, fi, s, in);
                ovr[j] = file | s << 8;
            } else
                ri_set(f, fi, x, in);
            out[no++] = outid;
            m++;
        }
    }
    if (run && m) {                             /* the queue: drop the taken, append the outs */
        int k = 0;
        for (int i = m; i < *qn; i++) q[k++] = q[i];
        for (int i = 0; i < no && k < n; i++) q[k++] = out[i];
    }
    if (run) *qn = n;
    return order + n;
}

void ri_season(const u8 *t, const s8 *slt, s8 *copy, int world, u8 *sr) {
    ri_no = 0;
    for (int fi = 0; fi < RF; fi++)
        for (int i = 0; i < RIS / 8; i++) RI_SWAPPED[fi][i] = 0;
    u32 h = 0x9E3779B9u;                        /* (the draw: the season's own table as seed) */
    int moved = 0;
    for (int g = 0; g < 2000; g++) { h = h * 31 + (u8)slt[g]; if (copy[g] != slt[g]) moved = 1; }
    ri_rng = h;
    if (!moved) return;                         /* (InitializeNewSeason at a career's start: no season end yet) */
    int nf = *t++, qo = 0, pi = 0;
    for (int fi = 0; fi < nf; fi++) {
        int w = t[0], np = t[2];
        RI_FILES_FILE[fi] = t[1];
        int base = t[3] | t[4] << 8, moff = t[5] | t[6] << 8, nmap = t[7] | t[8] << 8, nsp = t[9];
        struct ri_file fv = { &RI_STATE.init[fi < RF ? fi : RF - 1], RI_STATE.maps + moff, nmap }, *f = &fv;
        int run = w == world && fi < RF && moff + nmap <= RMT;
        if (run && !*f->init) {                 /* (a new career / an older save: identities, the pools' first order) */
            for (int i = 0; i < nmap; i++) f->map[i] = 0;
            *f->init = 1;
        }
        const u8 *sp = t + 10;
        t = sp + nsp;
        int p0 = pi;
        for (int k = 0; k < np; k++) {
            int n = t[1];
            t = ri_pool(t, f, fi, RI_STATE.q + qo, RI_STATE.qn + pi, slt, copy, sr,
                        run && pi < RP && qo + n <= RQT, pi, base, sp, nsp, p0, np);
            qo += n;
            pi++;
        }
        if (run) *f->init = 2;
    }
    if (sr) sr[0] = sr[1] = 0;                  /* (the rankings used: a season end without any has none) */
}

/* A slot's record from its identity: everything but the slot's own bytes (file, ordinal, global number, controls,
   the 0xFE flags, the league / division). */
static void ri_copy(u8 *dst, const u8 *src) {
    for (int b = 0; b < 684; b++)
        if (b > 4 && b != 23 && b != 25) dst[b] = src[b];
}

/* After a pooled team file is read (LoadTeamFile): buf = teamFileBuffer (BE count + records), orig = its copy as
   read, pool = its RS file's buffer (BE count + records), fi = its index in the table. */
void ri_apply(u8 *buf, const u8 *orig, const u8 *pool, int fi, int moff) {
    int n = buf[0] << 8 | buf[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int i = 0; i < n && i < RIS && moff + i < RMT; i++) {
        int id = RI_STATE.maps[moff + i];
        if (!id--) continue;
        if (id < RIS && id < n) ri_copy(buf + 2 + 684 * i, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(buf + 2 + 684 * i, pool + 2 + 684 * (id - RIS));
    }
}

/* The career's team cache after a swap: every cached record of a swapped slot (team word file | slot << 8) gets its
   new identity's record. recs = the cache's records, n of them; file = the team file; orig / pool / fi as for
   ri_apply. */
void ri_cache(u8 *recs, int n, int file, const u8 *orig, const u8 *pool, int fi, int moff) {
    int nf = orig[0] << 8 | orig[1], np = pool ? pool[0] << 8 | pool[1] : 0;
    for (int k = 0; k < n; k++) {
        u8 *r = recs + 684 * k;
        int i = r[1];
        if (r[0] != file || !(RI_SWAPPED[fi][i >> 3] & 1 << (i & 7))) continue;
        if (moff + i >= RMT) continue;
        int id = RI_STATE.maps[moff + i] ? RI_STATE.maps[moff + i] - 1 : i;
        if (id < RIS && id < nf) ri_copy(r, orig + 2 + 684 * id);
        else if (id >= RIS && id - RIS < np) ri_copy(r, pool + 2 + 684 * (id - RIS));
    }
}

/* 4.0.1 (cupsf.py): the World 2026-27 national and league cups follow promotions and relegations. From the world's
   second season a cup's entrants come from the clubs' CURRENT divisions (base + someLeaguesTable delta), with the real
   list's format: n_d entrants per division, b_d of them byes (the list's end, as lib97's BYE_TAB); the career club
   first when its division takes part; the others by LAST SEASON'S FINAL POSITION in the division they played in
   (Davide: best placed first, a promoted / relegated club by its place in its old division; equal places: the file's
   order; clubs without a place - an old save, a club not in last season's league - after them in the file's order). The positions: cf_cap_c at the
   season end (gp_cap: every division's final table), saved with the career (engine item 'CF'). The set-up (cf_a6) and
   rule 11's check (gp_notin -> cf_member_c) compute the same list.
   CF_TAB: db world, db first season, db cups; per cup: db id, db n, db groups, db dt, groups x (db division, db n_d,
   db b_d); then db dts; per dt: dw global base, db file, dw m, 16 x db the divisions' levels, m x (db ordinal, db base
   division). CF_ST.rank[ordinal] = place (1..31) | level of last season's division << 5; 0 = none. */
const u8 *CF_TAB;
static const u8 *cf_cup(int id, const u8 **dtp) {
    const u8 *t = CF_TAB, *c;
    if (!t || !GP_SLT) return 0;
    int nc = t[2];
    c = t + 3;
    const u8 *hit = 0;
    for (int k = 0; k < nc; k++) {
        if (c[0] == id && !hit) hit = c;
        c += 4 + 3 * c[2];
    }
    if (!hit) return 0;
    int nd = c[0], di = hit[3];
    const u8 *d = c + 1;
    if (di >= nd) return 0;
    for (int k = 0; k < di; k++) d += 21 + 2 * (d[3] | d[4] << 8);
    *dtp = d;
    return hit;
}
struct cf_state { u16 magic; u8 season, file; u8 rank[256]; };
struct cf_state CF_ST;
enum { CN_N = 32 };
struct cn_state { u8 season, pad[3]; u8 name[CN_N]; };
struct cn_state CN_ST;                  /* 4.0.5: the career club's division at the last season end (its name) */
const u32 CN_SIZE = sizeof(struct cn_state);
static u32 cf_last1(void) {              /* 4.0.5 (gp_wn_c 'E', last season): the 1st of the career club's division */
    if (CN_ST.pad[2] == 'W' && (u8)(CN_ST.season + 1) == GP_SEAS)    /* (the career club's OWN last division's 1st, kept
                                           as a word by cf_cap_c - every build since 4.2 (MC 15/11; S7 4.2 before): a club
                                           that crossed files since (S7, WSITES row 'CN') is still its old division's) */
        return (u32)(CN_ST.pad[0] | CN_ST.pad[1] << 8);
    if (CF_ST.magic != 0x4643 || (u8)(CF_ST.season + 1) != GP_SEAS || (GP_MGR & 0xFF) != CF_ST.file) return 0xFFFE;
    int lv = CF_ST.rank[GP_MGR >> 8] >> 5, hit = -1;    /* (no 'W': a save from before it, the first season end after
                                           loading - CF_ST's places have no group: the 1st of the level only when the level
                                           has ONE, else unknown, no line - was the lowest ordinal of every group's 1st) */
    for (int i = 0; i < 256; i++)
        if (CF_ST.rank[i] == (1 | lv << 5)) {
            if (hit >= 0) return 0xFFFE;
            hit = i;
        }
    return hit < 0 ? 0xFFFE : (u32)CF_ST.file | (u32)hit << 8;
}
#ifndef CF_SEED
#define CF_SEED 0
#endif
static const u8 *cf_dt(int file) {      /* the league file's dt */
    const u8 *t = CF_TAB, *c;
    if (!t) return 0;
    c = t + 3;
    for (int k = 0; k < t[2]; k++) c += 4 + 3 * c[2];
    const u8 *d = c + 1;
    for (int k = 0; k < c[0]; k++) { if (d[2] == file) return d; d += 21 + 2 * (d[3] | d[4] << 8); }
    return 0;
}
const u32 CF_STSZ = sizeof(struct cf_state);
enum { CF_MAGIC = 0x4643 };
void cf_cap_c(u32 dv, const u8 *diy, u32 season) {     /* a division's final table (DIY: +31h clubs, +6Dh the places'
                                                           row offsets, +12Dh the rows' team words) */
    int n = diy[0x31] | diy[0x32] << 8;
    if (n > 255) n = 255;
    for (int k = 0; k < n; k++) {
        int row = (diy[0x6D + 2 * k] | diy[0x6E + 2 * k] << 8) / 0x12;
        u16 w = (u16)(diy[0x12D + 2 * row] | diy[0x12E + 2 * row] << 8);
        if (CF_ST.magic != CF_MAGIC || CF_ST.season != (u8)season) {
            for (int i = 0; i < 256; i++) CF_ST.rank[i] = 0;
            CF_ST.magic = CF_MAGIC; CF_ST.season = (u8)season; CF_ST.file = (u8)(w & 0xFF);
        }
        if (w == GP_MGR && GP_MGR) {       /* (4.0.5: the division the career club played in - its name for the
                                           WINNERS page's last season, winners.py 'E': CN_ST, item 'CN') */
            CN_ST.season = (u8)season;
            int i = 0;
            for (; i < CN_N - 1 && diy[4 + i]; i++) CN_ST.name[i] = diy[4 + i];
            CN_ST.name[i] = 0;
            {                           /* (cf-st-s7.md: the 1st of this division, as the career club's own last
                                           season: its WORD (S7: walked by WSITES row 'CN' +1: a winner that crosses at a
                                           later swap keeps its identity); pad[2] = 'W' marks it - word 0 is a real club.
                                           Every build since 4.2 (MC 15/11): cf_last1's group-blind fallback picked
                                           another group's 1st on a level of 2+ groups; S7 builds only before) */
                int r0 = (diy[0x6D] | diy[0x6E] << 8) / 0x12;
                u16 w0 = (u16)(diy[0x12D + 2 * r0] | diy[0x12E + 2 * r0] << 8);
                CN_ST.pad[0] = (u8)w0; CN_ST.pad[1] = (u8)(w0 >> 8); CN_ST.pad[2] = 'W';
            }
        }
        if ((w & 0xFF) != CF_ST.file) continue;
        const u8 *dt = cf_dt(CF_ST.file);
        int lv = dt && dv < 16 ? dt[5 + dv] : 0;
        CF_ST.rank[w >> 8] = (u8)((k + 1 > 31 ? 31 : k + 1) | lv << 5);
    }
}
static int cf_build(int id, int season, u32 cteam, u16 *out) {
    const u8 *dt, *c = cf_cup(id, &dt);
    if (!c || season == CF_TAB[1]) return 0;     /* (the first season: the real list and bracket) */
    int n = c[1], ng = c[2], gb = dt[0] | dt[1] << 8, lf = dt[2], nm = dt[3] | dt[4] << 8, nb = 0, at = 0;
    u16 byes[64];
    u8 cand[256];
    for (int g = 0; g < ng; g++) {
        int dv = c[4 + 3 * g], want = c[5 + 3 * g], wb = c[6 + 3 * g], m = 0;
        for (int q = 0; q < nm; q++) {
            int i = dt[21 + 2 * q], b = dt[22 + 2 * q];
            if (b + GP_SLT[gb + i] == dv) cand[m++] = (u8)i;
        }
        if (m < want) return 0;                  /* (a division shorter than the format: keep the fixed list) */
        int ranked = CF_ST.magic == CF_MAGIC && (u8)(CF_ST.season + 1) == (u8)season && CF_ST.file == lf;
        u32 key[256];
        int nl = dv < 16 ? dt[5 + dv] : 0;      /* (this division's level) */
        for (int i = 0; i < m; i++) {            /* (CF_SEED 1: relegated, stayers, promoted; then the place, the
                                                    ordinal; unplaced last) */
            int o = cand[i], v = ranked ? CF_ST.rank[o] : 0, r = v ? v & 31 : 0xFF, ol = v ? v >> 5 : nl;
            int g = !v ? 3 : !CF_SEED ? 0 : ol < nl ? 0 : ol == nl ? 1 : 2;
            key[i] = (u32)g << 16 | (u32)r << 8 | (u32)o;
        }
        for (int i = 1; i < m; i++)              /* (insertion sort by key) */
            for (int j = i; j > 0 && key[j - 1] > key[j]; j--) {
                u32 k = key[j]; key[j] = key[j - 1]; key[j - 1] = k;
                u8 x = cand[j]; cand[j] = cand[j - 1]; cand[j - 1] = x;
            }
        if ((cteam & 0xFF) == lf)                /* the career club first */
            for (int i = 0; i < m; i++)
                if (cand[i] == (cteam >> 8 & 0xFF)) { u8 x = cand[i]; for (int j = i; j > 0; j--) cand[j] = cand[j - 1]; cand[0] = x; break; }
        for (int k = 0; k < want; k++) {
            u16 w = (u16)(lf | cand[k] << 8);
            if (k >= want - wb) { if (nb < 64) byes[nb++] = w; }
            else if (at < 64) out[at++] = w;
        }
    }
    for (int k = 0; k < nb && at < 64; k++) out[at++] = byes[k];
    return at == n ? n : 0;
}
static u16 CF_BUF[64];
u32 cf_list_c(u32 id, u32 season, u32 cteam) {          /* -> CF_BUF filled (its address) or 0: keep the list */
    return cf_build((int)id, (int)season, cteam, CF_BUF) ? (u32)CF_BUF : 0;
}
u32 cf_member_c(u32 id, u32 season, u32 cteam) {        /* 2: not ours (the definition decides), 1 in, 0 not in */
    u16 l[64];
    int n = cf_build((int)id, (int)season, cteam, l);
    if (!n) return 2;
    for (int k = 0; k < n; k++) if (l[k] == (u16)cteam) return 1;
    return 0;
}

/* ---- 4.0.5 national supercups (supercup.py; internal/handoff/supercups.md). SC_ST (engine item 'SC'): db 'S','C',
   count, the last season handled (the game's season byte); db round (0, 1 = the career club's semi-final built, 2 =
   won: its final due, 3 = done), 0; dw the other semi-final's winner; dd 0; then the season end's national cup
   winners / finalists (supercup.py's sc_cup: 12 B per cup, by contest id). GP_SCT (the glue, a World 2026-27 career):
   db count; per country SC_E bytes: db league team file, cup contest id, from_season (1, or 2: not in the world's
   first season), week (the first match), legs, level (LV_*), n (2: a final; 4: semi-finals e0-e1, e2-e3 + the final),
   week of the final; db rule[4] (SCR_* | the fallback SCR_* << 4, used when the rule's club is already in); dw the
   world's first season's entrants[4] (the real edition); dd long name, short name; db round-name codes (semi,
   final), db the stage-title play-offs of the rules SCR_TITLE0 / 1 (MEX); dd the season record's name (REGISTRO GESTIONE: the long name if it fits 144 px, else the short).
   SC_ST +5 = 1: the career club won this season's (SC_ST +3) supercup -> its record line (sc_rline, gp_rlines_c). Only the career club's country's supercup is played: the career club in it -> its tie in slot 4 (as
   a Coppa D tie, kind K_SC); the other semi-final is decided at once (the better placed of last season wins 3 in 5). */
/* (SC_E, SC_NE, SC_H, SC_EARLY, SC_U: gpsc.h) */
enum { SCR_CHAMP = 1, SCR_SECOND, SCR_CUPW, SCR_CUPF, SCR_THIRD, SCR_FOURTH, SCR_TITLE0, SCR_TITLE1,
       SCR_UCL, SCR_UEL, SCR_UECL };   /* (4.0.6: the game's UEFA holders, the UEFA Super Cup) */
/* 4.0.6 the UEFA Super Cup (internal/handoff/csup.md): GP_SCT's entry with league file SC_UEFA (world-level), its
   entrants the game's own holders of last season's Champions / Europa / Conference League (HOLD_CC, CWC, UEFA), as
   supercup.py's usc_snap copied them at the season end - right after the three European cups' season ends
   (cseg_92D55 / 9307A / 9339D), before the qualifiers clear a holder that qualified through its league
   (cseg_93BCE; the game does not save them either). Its state is SC_ST's last cup entry (supercup.py keeps the cups
   below it): db the season handled, state (1 the career club's tie built, 3 done or not in it), won, the season of
   the snapshot (the season byte at its end), dw the winner, dw the holders CL, EL, UECL (FFFFh none). Built first (early, at the season's first advance): a national early one waits for slot 4 and is built
   at its own week, after the UEFA tie. The career club not a holder: nothing played or simulated (VINCITORI names
   only the viewed league's rows, so no page could show a foreign winner). */
enum { SC_UEFA = 0xFF };
u8 SC_ST[SC_H + 12 * SC_NE];
const u32 SC_STSZ = sizeof SC_ST;
const u8 *GP_SCT;                       /* (the glue: the table, 0 = none) */
u32 GP_SCFIRST;                         /* (the glue: the career's first season in the world) */
u32 SC_TRACE;                           /* (the harness: 1 built, 2 final built, 0x81 summer skipped in season 1, 0x82
                                           entrants unknown, 0x84 career club not in it, | 0x40 decided) */

GP_X3S int sc_rank(u16 w) {                    /* last season's place (top division), 9 = none */
    if (CF_ST.magic != CF_MAGIC || CF_ST.file != (w & 0xFF)) return 9;
    int r = CF_ST.rank[w >> 8];
    return r && r < 32 ? r : 9;
}
/* 4.2 GPLX (MC 15/11: gplay was 16 B free in the S3 release shape, h3s): the supercup entrants' rule (sc_rule, with
   sc_place / sc_cup) lives in tools/gplx.c, linked into obj4's GPLX band (swreg.GPLX_AT) in builds with worlds
   (GP_GPLX); the other builds and the host tests include it here. */
#if GP_GPLX
u16 sc_rule(const u8 *e, int r);
#else
#define GP_GPLX_INLINE 1
#include "gplx.c"
#endif
static void sc_ko(struct gp_ko *k, const u8 *e, u16 home, u16 away, int final) {
    int w = final ? e[7] : e[3];
    ko_one(k, home, away, w, w + 1, e[4], K_SC, e[5], e[0], e + 20);
    for (int i = 0; i < KG; i++) GP_ST.rn[i] = 0;
    GP_ST.rn[0] = e[28 + (final || e[6] == 2)];      /* (the round's name: semi-final / final) */
}
static int sc_free(void) {              /* slot 4 not holding a contest of this season still to decide */
    return !(GP_ST.magic == MAGIC && GP_ST.ko[0].magic == MAGIC && GP_ST.ko[0].season == GP_SEAS &&
             GP_ST.ko[0].tw[0] == NOC);
}
int sc_busy(void) {                     /* 4.0.5: slot 4 holds this season's supercup tie, not played yet (built early:
                                           another slot-4 builder waits) */
    return GP_ST.magic == MAGIC && GP_ST.ko[0].magic == MAGIC && GP_ST.ko[0].season == GP_SEAS &&
           GP_ST.ko[0].kind == K_SC && GP_ST.ko[0].tw[0] == NOC;
}
#if GP_FRND
int slot4_busy(void) {                  /* 4.2 friendlies (Convergence 16/11): slot 4 held - this season's supercup tie
                                           (sc_busy), or the friendlies (FR_OPEN: from the season start to the last one
                                           decided, between them too), or a friendly being played. sc_busy keeps its
                                           supercup-only meaning (sc_wline_c's VINCITORI line) */
    return FR_HELD() || sc_busy() || (GP_ST.magic == MAGIC && GP_ST.ko[0].magic == MAGIC &&
           GP_ST.ko[0].season == GP_SEAS && GP_ST.ko[0].kind == K_FR && GP_ST.ko[0].tw[0] == NOC);
}
#endif
static const u8 *usc_entry(void) {     /* 4.0.6 the UEFA Super Cup's GP_SCT entry, 0 = none */
    if (!GP_SCT) return 0;
    for (int i = 0; i < GP_SCT[0]; i++)
        if (GP_SCT[1 + SC_E * i] == SC_UEFA) return GP_SCT + 1 + SC_E * i;
    return 0;
}
GP_X3S int usc_live(void) {             /* 4.0.6: slot 4's supercup tie this season is the UEFA Super Cup's */
    return SC_U[0] == GP_SEAS && SC_U[1] == 1;
}
u32 GP_SCROW;                            /* (4.2 supercups-s1: gp_scrow_c's trace - week << 16 | count) */
u32 gp_scrow_c(const u8 *row) {        /* 4.2 supercups-s1 (MC 15/11): the fixture list's slot-4 row of this season's
                                           played UEFA Super Cup (its week, the career club's tie decided: SC_U +4 the
                                           winner) - its short name (STR_BASE-relative), not the label of the national
                                           supercup slot 4 holds now; 0 = the slot's label */
#if GP_FRND
    if (GP_PROW) { u32 r = GP_PROW(row); if (r) return r; }   /* (4.2 friendlies: their weeks keep AMICHEVOLE after slot 4
                                                               moves on to the supercup) */
#endif
    const u8 *e = usc_entry();
    if (!e || !row || row[0] != 4 || row[1] != e[3]) return 0;
    if (SC_U[0] != GP_SEAS || SC_U[1] != 3 || !(SC_U[4] | SC_U[5])) return 0;
    GP_SCROW = (u32)row[1] << 16 | ((GP_SCROW + 1) & 0xFFFF);   /* (the harness: the row's week, draws relabelled) */
    return (u32)(e[24] | e[25] << 8 | e[26] << 16 | (u32)e[27] << 24);
}
static int usc_step(void) {             /* 4.0.6 the UEFA Super Cup at the advance: 1 = the career club's tie built,
                                           -1 = its tie pending (slot 4 held), 0 = nothing (the national one next) */
    const u8 *e = usc_entry();
    if (!e) return 0;
    if (SC_U[0] == GP_SEAS) return SC_U[1] == 1 ? -1 : 0;
    if (!sc_free()) return 0;
    SC_U[0] = GP_SEAS; SC_U[1] = 3; SC_U[2] = 0; SC_U[4] = SC_U[5] = 0;
    if (GP_SCFIRST && (e[2] & 0x7F) > 1) { SC_TRACE = 0x91; return 0; }   /* (played before the world's first season) */
    u16 c[2];
    if (GP_SCFIRST) {                   /* (4.2 supercups-s1, Davide 15/11: the world's first season plays the real 2026
                                           edition - the entry's first_entrants words, the same field as the national
                                           ones (MC); no season end has set the holders yet) */
        c[0] = (u16)(e[12] | e[13] << 8);
        c[1] = (u16)(e[14] | e[15] << 8);
    } else {
        c[0] = sc_rule(e, e[8]);
        c[1] = sc_rule(e, e[9]);
#if GP_USCFORCE
        if (c[1] != GP_MGR) c[0] = GP_MGR;   /* (test builds, USC_FORCE=1: the career club the Champions League holder) */
#endif
        if (c[1] && c[1] == c[0]) c[1] = sc_rule(e, e[9] >> 4);   /* (one club holds both: the Conference League's) */
    }
    if (!c[0] || !c[1] || c[0] == c[1]) { SC_TRACE = 0x92; return 0; }
    if (!IS_MGR(c[0]) && !IS_MGR(c[1])) { SC_TRACE = 0x94; return 0; }
    sc_ko(&GP_ST.ko[0], e, c[0], c[1], 1);
    SC_U[1] = 1; SC_TRACE = 0x11;
    return 1;
}
#if GP_HOOK
/* 4.2 fixture port (MC 14/11 (b)+(c)): fpad.c (obj4) builds the K_PORT tie itself, through ko_one's pointer; the rest
   - GP_ST, GP_IN, GP_SCT, the pseudo registers - it reads at their symbols, the struct offsets from GP_OFFS (a
   -DGP_OFFSETS compile of this file, fpad.py: no byte of them in the exe) */
void *GP_PAPI[1] GP_DATA_SECTION = { (void *)ko_one };
#ifdef GP_OFFSETS
#define OF(t, f) __builtin_offsetof(t, f)
const u16 GP_OFFS[] = { OF(struct gp_state, ko), OF(struct gp_ko, season), OF(struct gp_ko, kind), OF(struct gp_ko, tw),
                        OF(struct gp_ko, team), OF(struct gp_ko, d1), OF(struct gp_ko, d2), OF(struct gp_ko, rs),
                        OF(struct gp_in, mdiv), MAGIC, NOC, K_PORT, HOST_NEUTRAL, SC_E, SC_UEFA, sizeof(struct gp_ko),
                        OF(struct gp_in, n), OF(struct gp_in, t), OF(struct gp_in, mgr), GD, GT, sizeof(struct gp_row),
                        OF(struct gp_row, pts), OF(struct gp_in, sim), SDX,
                        OF(struct gp_ko, pts), K_FR, LV_BETTER, OF(struct gp_state, rn) };   /* (4.2 friendlies: O_PTS - the fee in pts[2], a
                                           one-tie contest's unused entry -, C_KFR, C_LVBETTER; O_RN: fpad.c's install
                                           names a mini-league fixture's round - its matchday) */
#endif
#endif
u32 sc_step_c(void) {                   /* the calendar advance: 1 = the career club's tie built into ko[0] */
#if GP_HOOK
    if (GP_MGR && GP_PSTEP) { u32 r = GP_PSTEP(); if (r) return 1; }   /* (the port first: never "clear" - Q2 / Q3) */
#endif
    if (!GP_SCT || !GP_MGR) return 0;
    { int u = usc_step(); if (u) return u > 0; }   /* (4.0.6: the UEFA Super Cup first) */
    const u8 *e = 0;
    for (int i = 0; i < GP_SCT[0]; i++)
        if (GP_SCT[1 + SC_E * i] == (GP_MGR & 0xFF)) e = GP_SCT + 1 + SC_E * i;
    if (!e) return 0;
    if (SC_ST[3] == GP_SEAS) {          /* (handled: a final four's final still due) */
        if (SC_ST[4] != 2 || (int)GP_WK + 1 < e[7] || !sc_free()) return 0;
        sc_ko(&GP_ST.ko[0], e, GP_MGR, (u16)(SC_ST[6] | SC_ST[7] << 8), 1);
        SC_ST[4] = 3; SC_TRACE = 2;
        return 1;
    }
    if (((int)GP_WK + 1 < e[3] && !(e[2] & SC_EARLY)) || !sc_free()) return 0;   /* (4.0.5 'early': built at the
                                           season's first advance - its fixture row and VISUAL. COMPETIZ. entry from
                                           the start - still played at its own week, ko_one's dates) */
    SC_ST[3] = GP_SEAS; SC_ST[4] = 0; SC_ST[5] = 0; SC_ST[8] = SC_ST[9] = 0;
    if (GP_SCFIRST && (e[2] & 0x7F) > 1) { SC_TRACE = 0x81; return 0; }   /* (a summer one: already played before the world) */
    int n = e[6] == 4 ? 4 : 2;
    u16 c[4];
    for (int i = 0; i < n; i++) {
        if (GP_SCFIRST) { c[i] = (u16)(e[12 + 2 * i] | e[13 + 2 * i] << 8); continue; }
        c[i] = sc_rule(e, e[8 + i]);
        for (int j = 0; j < i; j++) if (c[i] && c[i] == c[j]) c[i] = sc_rule(e, e[8 + i] >> 4);   /* (the double) */
        for (int j = 0; j < i; j++) if (c[i] == c[j]) c[i] = 0;
    }
    for (int i = 0; i < n; i++) if (!c[i]) { SC_TRACE = 0x82; return 0; }
    int me = -1;
    for (int i = 0; i < n; i++) if (IS_MGR(c[i])) me = i;
    if (me < 0) { SC_TRACE = 0x84; return 0; }
    if (n == 4) {                       /* (the other semi-final, decided now) */
        int o = me < 2 ? 2 : 0;
        u16 a = c[o], b = c[o + 1];
        int ra = sc_rank(a), rb = sc_rank(b);
        rng = GP_SEAS * 7919u + e[1];
        u16 w = below(5) < 3 ? (ra <= rb ? a : b) : (ra <= rb ? b : a);
        SC_ST[6] = (u8)w; SC_ST[7] = (u8)(w >> 8);
        SC_ST[4] = 1;
    }
    sc_ko(&GP_ST.ko[0], e, c[me & 2], c[(me & 2) + 1], n == 2);
    SC_TRACE = 1;
    return 1;
}
GP_X3S const u8 *sc_entry(void);
#if !GP_X3
#define GP_X3_INLINE 1
#include "gplay3.c"
#endif
GP_X3S const u8 *sc_entry(void) {      /* the career club's country's GP_SCT entry, 0 = none */
    if (!GP_SCT || !GP_MGR) return 0;
    for (int i = 0; i < GP_SCT[0]; i++)
        if (GP_SCT[1 + SC_E * i] == (GP_MGR & 0xFF)) return GP_SCT + 1 + SC_E * i;
    return 0;
}
u32 sc_wline_c(void) {                  /* winners.py: this season's supercup line on the career league's VINCITORI
                                           page - its record name (STR_BASE-relative), 0 = no line: the career club's
                                           tie not built this season (not in it, a summer one before the world); a
                                           final four's semi-final lost: its simulated final's winner (sc_done) */
    const u8 *e = sc_entry();
    if (!e || SC_ST[3] != GP_SEAS) return 0;
    if (!(SC_ST[8] | SC_ST[9]) && !sc_busy() && SC_ST[4] != 2) return 0;
    return *(const u32 *)(e + 32);
}
static u32 sc_wn(void) {                /* gp_wn_c 'U': the winner, else 0FFFEh (DA GIOCARE on the career's league) */
    u16 w = (u16)(SC_ST[8] | SC_ST[9] << 8);
    return SC_ST[3] == GP_SEAS && w ? w : 0xFFFE;
}
static u32 sc_rline(void) {             /* the career club's supercup won this season: its record name, else 0 */
    if (!SC_ST[3] || SC_ST[3] != GP_SEAS || SC_ST[5] != 1 || !GP_SCT || !GP_MGR) return 0;   /* (no magic check: the
                                           magic is written with the first cup stored, at the season end - after the
                                           season record; a first season's SC_ST has none until then) */
    for (int i = 0; i < GP_SCT[0]; i++)
        if (GP_SCT[1 + SC_E * i] == (GP_MGR & 0xFF)) return *(const u32 *)(GP_SCT + 1 + SC_E * i + 32);
    return 0;
}
static u32 usc_rline(void) {            /* 4.0.6: the UEFA Super Cup won this season: its record name, else 0 */
    const u8 *e = usc_entry();
    return e && SC_U[0] == GP_SEAS && SC_U[1] == 3 && SC_U[2] == 1 ? *(const u32 *)(e + 32) : 0;
}
