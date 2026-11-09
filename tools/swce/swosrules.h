/*
 * swosrules.h -- the SWOS rules library: the competition rules the SWOS 96/97 Mod and OpenSWOS
 * share (docs/rules-library.md).
 *
 * Input: a league's final tables and its rules as the Mod's tools compile them. Output: each
 * club's move. No engine: calendars, menus, contests and saves stay each game's own. The code is
 * the Mod's (tools/dplay.c, tools/gplay.c), as OpenSWOS ported it and checked it against the
 * Mod's own C season after season (tests/rules/check.sh), now one copy for both games.
 *
 * Freestanding C99 for the DOS build (clang -target i686, -march=i486, no libc): no globals --
 * one caller-owned state passed by pointer --, no library calls, no compiler-generated
 * memcpy / memset. <stdint.h> is the one include -- or none, when the host's own header has
 * given int8_t .. uint32_t already and says so with SWOSRULES_HAVE_STDINT (the Amiga's toolchain
 * has no <stdint.h>: OpenSWOS defines them itself).
 *
 * Copyright (c) 2026 Davide Lorigliola, Ben Baker. MIT licence (LICENSE).
 */
#ifndef SWOSRULES_H
#define SWOSRULES_H

#ifndef SWOSRULES_HAVE_STDINT
#include <stdint.h>
#endif

#define SWOSRULES_VERSION 1

#define SR_DIVS  16                 /* a league's divisions (gplay.c GD) */
#define SR_CLUBS 32                 /* a division's clubs (gplay.c GT) */
#define SR_MOVES 48
#define SR_B_EXITS 8               /* a league's B teams under the 4.2 rules (second_floor >= 1): each may leave */

/* A club as both games name it: the Mod's team word (team file | ordinal << 8) and its global
 * number (the league table's index); its record. */
typedef struct { uint16_t team, glob, won, gf, ga, pts; } sr_row;

/* A league's final tables, place order (row 0 the top). */
typedef struct {
    uint8_t nd;                     /* divisions in it */
    uint8_t n[SR_DIVS];             /* clubs in each */
    sr_row  t[SR_DIVS][SR_CLUBS];
} sr_tables;

/* A move: a club's division delta (one level: -1 up, 1 down), the rule that made it. */
enum { SR_RULE_ITALY = 1, SR_RULE_KNOCKOUT = 2 };
typedef struct { uint16_t glob; int8_t delta; uint8_t rule; } sr_move;

/* A league's stage tables (gplay.c's GP_SS bank: gp_stage / gp_keep), kept by the caller through
 * the season and saved with it: r[k] a fixture stage's table (its 'table' k), fresh bit k when this
 * season wrote it; a 'keep' stage's frozen table (Malta's Opening Round) in kept. */
#define SR_STAGE_TABLES 4
typedef struct {
    uint8_t used, key, fresh, pad;  /* key: the caller's (its country) */
    uint8_t n[SR_STAGE_TABLES];
    sr_row  r[SR_STAGE_TABLES][SR_CLUBS];
    uint8_t kept_div, n_kept;       /* the kept table's division; 0 clubs: none */
    sr_row  kept[SR_CLUBS];
} sr_stage_bank;

/* Argentina's promedio history (gplay.c PR_STATE): each top-flight club's points and matches of
 * the two seasons before; the caller's, saved. A new career starts from the league's seed. */
#define SR_PROMEDIO_CLUBS 48
typedef struct { uint16_t glob, p[2]; uint8_t m[2]; } sr_promedio_club;
typedef struct { uint8_t init, n, pad[2]; sr_promedio_club c[SR_PROMEDIO_CLUBS]; } sr_promedio;
typedef struct { uint16_t glob, points2, points1; uint8_t matches2, matches1; } sr_promedio_seed;

/* The SEASON WINNERS page's last season (gplay.c WN_ST), written for the career club's league:
 * 'M' the division the club played in, 'L' each division's 1st, 'K' each play-off's winner,
 * 0x80 | play-off: a title play-off's last three ties' winners (idx: the tie); team words. */
#define SR_WINNERS_MAX 40
typedef struct { uint8_t type, idx; uint16_t team; } sr_winners_entry;
typedef struct { uint8_t season, n, fresh, pad; sr_winners_entry e[SR_WINNERS_MAX]; } sr_winners;

/* A league's rules: the pack's, as the Mod's tools compile them. */
typedef struct {
    uint8_t        divisions;
    const uint8_t *promoted;        /* per division: the record's counts by place */
    const uint8_t *relegated;
    uint8_t        italy;           /* the Italian rules (dplay.c): Serie B and its groups -- */
    uint8_t        serie_b;         /* Serie B's division, the first of Serie C's groups, */
    uint8_t        group_first;     /* how many groups (2..4) */
    uint8_t        groups;
    const uint8_t *spec;            /* the pack's knockouts: gplay.py compile_spec's bytes, 0-ended */
    const sr_promedio_seed *promedio_seed;  /* the promedio's history at a new career (gplay.c */
    uint8_t        promedio_seeds;          /* GP_PROM_TAB, global numbers) */
    uint8_t        seconds;         /* B teams (gplay.c SEC_TAB): each one's (global number - base, */
    const uint8_t (*second)[2];     /* its first team's or FFh); the highest level one may reach */
    uint8_t        second_top;      /* (FFh any); flags: 1 play-offs allowed, 2 it may leave the */
    uint8_t        second_flags;    /* league from the lowest division (the pool) */
    const uint16_t *second_team;    /* each B team's team word, or 0: a row is found by it as well as by
                                       its global number (the Mod 4.0.5's SEC_TAB: rows of a division
                                       simulated early may carry no global number) */
    uint32_t        spec_len;       /* spec's bytes, required with a spec: the rules check it first
                                       (sr_spec_check) and refuse a league whose spec is not sound, or
                                       has no length (SR_CHECK_COUNT, "spec_len") */
    uint8_t         team_file_high; /* how this game lays out a team word (sr_row.team, second_team):
                                       0 the Mod's, file | ordinal << 8 (an x86 word over the two
                                       bytes); 1 file << 8 | ordinal (OpenSWOS). A spec names a club
                                       as its (file, ordinal) bytes -- entrant type 8 -- the same in
                                       both games; the rules make the word from them this way */
    uint8_t         second_floor;   /* the B teams' floor (4.2, swc second_teams.lowest; MC 09/11): 0 the Mod 4.1's
                                       sec_post as it is (its lowest level the floor); n >= 1 the level n the floor and
                                       the 4.2 rules -- the stays loop passes over every B team (order-independent), a
                                       final guard puts a B team at or above its first team's new level one below it, or
                                       out of the league from the floor (and when its first team is below the league),
                                       and the B teams that leave are reported (sr_state.b_exit); at most SR_B_EXITS
                                       B teams (sr_league_check) */
} sr_league;

/* A league's levels when some are groups of parallel divisions (Serie C's, Serie D's): where each
 * level starts. levels 0: a level per division. */
typedef struct { uint8_t levels; const uint8_t *first; } sr_levels;

/* What the game around the rules knows (all optional, 0 for none): a tie, a title or a stage
 * title the career club played itself; a line for the game's log. */
typedef struct {
    void *ctx;
    /* the career club's play-off pidx, played: 1 and its winner when it holds the tie a v b */
    int32_t (*played_tie)(void *ctx, int32_t pidx, uint16_t a, uint16_t b, uint16_t *winner);
    /* a title play-off pidx played as a group contest: 1 and its champion, runner-up */
    int32_t (*played_title)(void *ctx, int32_t pidx, uint16_t *champion, uint16_t *runner_up);
    /* the career club's division's stage title k (0..2) decided mid-season: 1 and its champion,
     * runner-up (team words, global numbers) */
    int32_t (*stage_title)(void *ctx, int32_t k, uint16_t team[2], uint16_t glob[2]);
    void    (*log)(void *ctx, const char *fmt, ...);
} sr_host;

/* Tests only (NULL in a game): every tie's winner, every draw's order and every lot forced the same way in both
 * the Italian rules (sr_dplay) and the knockouts (sr_gplay), for the structural differential of 42-s3shape. */
typedef struct {
    void     *ctx;
    /* a tie's winner, one of the two: home = the club with home advantage (a single match's host, the return
     * leg's home club), legs 1..3 */
    uint16_t (*win)(void *ctx, uint16_t home, uint16_t away, int32_t legs);
    void     (*draw)(void *ctx, int32_t n, uint16_t *glob);        /* a draw: glob[0 .. n) put in its order */
    uint8_t  (*lot)(void *ctx, uint16_t glob);                     /* a club's lot (the last tie-break) */
} sr_force;

/* The season: what the career club played itself (0: simulated) and the results the rules use. */
typedef struct {
    uint16_t po_win, out_win;       /* its Serie B play-off, play-out: the winner's team word */
    uint16_t cpo_win;               /* its Serie C play-off */
    uint16_t cup_winner;            /* the Coppa Italia Serie C winner, 0 unknown */
    uint8_t  test_held;             /* a test: Serie B's play-off and play-out held whatever the points */
    uint16_t mgr;                   /* the career club (team word), 0 none */
    uint16_t tie_a, tie_b, tie_w;   /* a group tie it played (gplay.c pl_w): its clubs, winner */
    sr_stage_bank *bank;            /* the league's stage tables, 0 none */
    sr_promedio   *promedio;        /* its promedio history, 0 none */
    sr_winners    *winners;         /* the SEASON WINNERS page, 0 not kept */
    const sr_host *host;            /* 0: none */
    /* The season-end preview (the Mod 4.0.5 rc19, gplay.c GP_PRE): this season's titles decided
     * at the career club's league end, before the season-end menu -- the same results the season
     * end will reach (each play-off draws from its own entrants), but no promedio, no move of the
     * stage tables and no new SEASON WINNERS page: its entries are appended (the caller marks
     * where they start). The career club's own play-offs are left to it: own_pi, each the play-off's
     * index + 1 (0 none -- a zeroed sr_season previews every play-off). */
    uint8_t        preview;
    uint8_t        own_pi[2];
    /* The B teams in the knockouts (gplay.c place_club / sec_inelig): their global numbers' base
     * (as sr_final_moves takes it) and the league's levels, 0 a level per division. A B team is
     * passed over as a play-off entrant by place (not in a play-out) unless its league's B teams
     * may play play-offs and it may go up: not above second_top, nor into or above its first
     * team's level after this season's record (the places' promotions and relegations). b_in_ko
     * switches it on: 0 (a zeroed sr_season) no B team is passed over in the knockouts, as before
     * 4.0.5's port; 1 B teams found by global number (base + ordinal: base 0 is a league that comes
     * first) or by team word (sr_league.second_team). */
    uint8_t        b_in_ko;
    uint16_t       base;
    const sr_levels *levels;
    /* 42-s3shape: the Coppa Italia Serie C's other finalist (team word, 0 unknown: the Mod 4.1's rule, the 11th) --
     * with it a knockout's cup place (entrant type 9, flag 0x80) plays the real C.U. 209/A rule; and the test hook */
    uint16_t       cup_finalist;
    const sr_force *force;
    /* 4.2 S1.3: the clubs (team words, 0 none) already in a UEFA competition's final (the career club's cup: the Mod's
     * uesum US_REC, its semi-finals' winners) -- a knockout round with host bit 0x40 (pack "skip_if_uefa_finalist", the
     * FIGC C.U. 244/A exception (iv)) does not play a tie of one of them: the better placed goes through */
    uint16_t       uefa_final[2];
} sr_season;

/* A result the knockouts decide beside the moves: a title's champion and runner-up, a continental
 * play-off's winner and loser, a stage title's (kind 5 title, 6 continental, 8 stage). */
enum { SR_KIND_TITLE = 5, SR_KIND_CONTINENTAL = 6, SR_KIND_PROMEDIO = 7, SR_KIND_STAGE = 8 };
typedef struct { uint8_t kind, div; uint16_t team[2], glob[2]; } sr_result;

typedef struct { int32_t c, pts, gd, gf; } sr_gs;      /* a group table's row (gplay.c gs) */

/* The library's working state: the caller's memory, zeroed once (sr_reset). The caller writes
 * the season's tables into `t`, then calls the season end; the moves come back in `mv`. */
typedef struct sr_state {
    sr_tables t;
    sr_move   mv[SR_MOVES];
    int32_t   nmv;
    int32_t   dp_moves;             /* how many of mv the Italian rules made (they come first) */
    /* dplay.c */
    struct {
        uint8_t  ng, n[5];
        sr_row   t[5][24];
        uint16_t po_win, out_win, cpo_win, cupw;
        uint32_t rng;
        uint8_t  lot[5 * 24];
        uint8_t  test_held;
        const sr_force *force;      /* (tests: sr_season.force) */
    } dp;
    /* gplay.c */
    struct {
        uint32_t rng;
        int32_t  by_rec, pidx, ss_used, srl_div, wn_on;
        uint16_t mgr, played_a, played_b, played_w;
        sr_result res[4], sres[3], srl[3];
        int32_t  nres;
        uint8_t  nst[2];            /* the kept 'keep' tables (gp_keep) */
        sr_row   st[2][SR_CLUBS];
        sr_stage_bank *ssb, no_bank;
        const sr_season *se;
        sr_gs    ps[64], ms[SR_CLUBS];
        sr_promedio_club nx[SR_PROMEDIO_CLUBS];
        int32_t  ce_club[64], ce_n; /* the last contest's entrants (sr_contest_entrants) */
        int32_t  lvl;               /* 42-s3shape: this play-off ranks a level of groups (place, then the record) */
        int32_t  scroll_div, scroll_from;   /* its cup place's scroll: that division's places from it move up one */
        uint32_t lot0;              /* its lots' seed */
        const uint8_t *xb, *xe;     /* its extension ops */
        uint32_t seeded;            /* its seeded rounds */
        int32_t  direct;            /* its direct gap, 0 none */
    } gp;
    int8_t    want[SR_DIVS][SR_CLUBS];      /* each club's move, a level: -1 up, 1 down (sr_final_moves) */
    /* The B teams that leave the league this season end by the B-team rules (sr_b_teams, second_floor >= 1): their
     * global numbers. Each one's want is 1; it goes out of the world (the off-file pool), not to the level below, and
     * the pool sends up one club more for each (swc up.extra). Relegations by place from the floor are not counted. */
    int32_t   b_exits;
    uint16_t  b_exit[SR_B_EXITS];
} sr_state;

void     sr_reset(sr_state *st);
uint32_t sr_state_size(void);

/* The season end's first step: Serie B and Serie C's play-offs and play-outs (dplay.c dp_season)
 * over st->t, by the league's Italian rules. The moves start again in st->mv (rule
 * SR_RULE_ITALY); their count, 0 when the league is not Italian, -1 when it is refused
 * (sr_league_check: nothing played). */
int32_t sr_italy(sr_state *st, const sr_league *lg, const sr_season *se);

/* Serie B's play-out is held unless the 16th leads the 17th by more than 4 points; its play-off
 * unless the 3rd leads the 4th by more than 14 (dplay.c OUT_HELD and its play-off rule). */
int32_t sr_out_held(uint16_t pts16, uint16_t pts17);
int32_t sr_playoff_held(uint16_t pts3, uint16_t pts4);

/* The season end's second step: the pack's knockouts (gplay.c gp_season, whole: promotion,
 * play-out, placement, title, continental, promedio and stage-title play-offs; every entrant kind
 * -- by place, the stage tables, the Trofeo's finalists, the title deciders' seeds, the previous
 * play-off's loser --, group rounds, the drawn pot) over st->t: their moves after the Italian ones
 * (rule SR_RULE_KNOCKOUT), the results in st->gp.res[0 .. nres) (titles, continental places) and
 * st->gp.sres (the career club's division's stage titles); the SEASON WINNERS page in
 * se->winners when the career club is in the league. The count of moves it added. */
int32_t sr_knockouts(sr_state *st, const sr_league *lg, const sr_season *se);

/* ---- The career club's own play-off, played as a contest (gplay.c ko_build, gp_need, t2_shape)
 * -- the contest itself is the game's ---- */

#define SR_CONTEST_MAX 32           /* a contest's entrants */

/* Play-off pidx of the league's knockouts (its bytes), 0: none. */
const uint8_t *sr_spec_at(const sr_league *lg, int32_t pidx);

/* The career club's play-off at its league's end (gp_need, a career): the first playable one in
 * spec order with `club` (in division d's final table, best first) among its entrants -- its index,
 * the other divisions its entrants come from (to simulate now: at most two; nine for a group
 * contest) in other[9]; -2 - its index when it is a group contest; -1 none. Uses st->t. */
int32_t sr_club_playoff(sr_state *st, const sr_league *lg, const sr_season *se, int32_t d, const sr_row *table,
                        int32_t n, uint16_t club, uint8_t *other, int32_t *nother);

/* Play-off pidx's entrants as the season end would resolve them (ko_build), from nt tables
 * (divs[0] the club's division, then the ones simulated early) and the stage tables: in entrant
 * order their team words, global numbers, points and ranks (a stage entrant: its stage place;
 * 'host_by_record': by record), *spec its bytes; their count, 0 when one is not known. */
int32_t sr_contest_entrants(sr_state *st, const sr_league *lg, const sr_season *se, int32_t nt,
                            const int32_t *divs, const sr_row *const *tables, const int32_t *ns, int32_t pidx,
                            uint16_t *team, uint16_t *glob, uint8_t *prio, uint16_t *pts, const uint8_t **spec);

/* Right after sr_contest_entrants: a round-1 tie simulated at the contest's build, the career club
 * waiting (ko_build's presim): the seed (hseed of game round 0), then each tie of entrants a, b
 * (legs 3: a best of three); the winner, a or b. */
void    sr_contest_seed(sr_state *st, int32_t pidx, const uint16_t *team, int32_t n);
int32_t sr_contest_tie(sr_state *st, int32_t a, int32_t b, int32_t legs, int32_t host, int32_t level);

/* A title of groups then knockouts (gplay.c t2_shape: the Poule Scudetto), played as a group
 * contest: g groups of m entrants, meet meetings, then nk knockout stages of kt ties, the first
 * taking q (the groups' winners and best runners-up), kb their round bytes. 0: not one. */
typedef struct { uint8_t g, m, meet, nk, q, kt[4], kb[4]; } sr_group_shape;
int32_t sr_group_shape_of(const uint8_t *spec, sr_group_shape *shape);

/* ---- The season's moves (sr_post.c) ---- */

/* Each club's move, one level, into st->want[d][k] (k its place in st->t): the record's by place
 * (the top promoted[d] up, the bottom relegated[d] down), the play-offs' moves (st->mv) on top,
 * then the B-team rules. base: the league's first global number (a B team's is base + its
 * ordinal). */
void sr_final_moves(sr_state *st, const sr_league *lg, const sr_levels *lv, uint16_t base);

/* The B-team rules alone (gplay.c sec_post), over the moves already in st->want: a B team may not
 * go up above second_top, nor into or above its first team's level after this season's moves --
 * held, the next club of its division goes up instead; it goes down when its first team comes
 * into its level, the best placed relegated of its division staying. */
void sr_b_teams(sr_state *st, const sr_league *lg, const sr_levels *lv, uint16_t base);

/* ---- A cup's clubs from the second season on (sr_cups.c: gplay.c cf_build, the Mod 4.0.1) ---- */

#define SR_CUP_CLUBS 64             /* a cup's entrants */
#define SR_CLUB_SLOTS 512           /* a country's clubs (its slots: two team files' at most) */

/* From the cup's real (first-season) list: per division, how many of its clubs, how many of
 * them with a bye. */
typedef struct { uint8_t division, clubs, byes; } sr_quota;

/* A cup's clubs this season. The league's nclubs clubs are each a slot and this season's division
 * (after the moves); place[slot] is last season's (place | level << 5, 0 none) or the whole table 0
 * when last season's places are not this league's last season; level[d] a division's level (a
 * level of groups one). Each division's quota is taken in order -- relegated into it, stayed,
 * promoted, without a place; then the place, the slot --, the career club first when it is in it.
 * The slots in order (round 1's clubs, then the byes); their count, or 0 when it must play the
 * real list (a division with fewer clubs than its quota, or not n in all). */
int32_t sr_cup_entrants(const sr_quota *q, int32_t nq, int32_t n, int32_t nclubs, const uint16_t *slot,
                        const uint8_t *division, const uint8_t *place, const uint8_t *level,
                        int32_t career_slot, uint16_t *out);

/* ---- Untrusted input (sr_check.c): a spec written by hand, a damaged save -- checked once, up
 * front, so the rules' code (the Mod's, line for line, its fixed buffers) needs no check ---- */

enum {
    SR_CHECK_OK = 0,
    SR_CHECK_TRUNCATED,     /* the bytes end inside a field */
    SR_CHECK_COUNT,         /* a count over its buffer (entrants, ties, a table's clubs ...) */
    SR_CHECK_INDEX,         /* an index past what exists (a division, a member, a stage table ...) */
    SR_CHECK_VALUE          /* a byte with no meaning (a kind, an entrant type, legs, host, level ...) */
};
typedef struct {
    int32_t     code;       /* SR_CHECK_* */
    int32_t     pidx;       /* the play-off, -1 none */
    uint32_t    offset;     /* the byte (spec) or the element (state) */
    const char *field;      /* its name */
} sr_check_error;

/* A pack's knockouts, len bytes, for a league of `divisions` (0: any up to SR_DIVS): SR_CHECK_OK, or
 * the first fault (err, optional). */
int32_t sr_spec_check(const uint8_t *spec, uint32_t len, int32_t divisions, sr_check_error *err);
/* A league's rules (its spec too, which needs its spec_len) and a season's saved state (the stage
 * tables, the promedio, the SEASON WINNERS page, the levels). */
int32_t sr_league_check(const sr_league *lg, sr_check_error *err);
int32_t sr_season_check(const sr_season *se, sr_check_error *err);

/* ---- The Coppa Italia Serie D: a later season's first two rounds (sr_cupd.c: gplay.c cd_rank,
 * cd_season, cd_make) ---- */

#define SR_CUPD_PRE 41              /* a generated preliminary round's ties at most (gplay.c CDP) */
#define SR_CUPD_R1  64              /* a generated first round's ties (CD1) */

/* The season end the entry order is made from: each slot's division and, in Serie D, its place
 * from the bottom of its group + 2; the slots that took a pool club. The caller's, one season. */
typedef struct {
    uint8_t last_div[SR_CLUB_SLOTS];    /* FFh: in no table */
    uint8_t place[SR_CLUB_SLOTS];       /* 0 none */
    uint8_t arrival[SR_CLUB_SLOTS / 8];
} sr_cupd_end;

/* The cup's rounds 0-1 generated: np preliminary ties, then the first round's 64; tie t's sides
 * side[2t], side[2t + 1] -- a team word, 0 (a bye), or a preliminary tie's winner (t << 8 | FFh). */
typedef struct {
    uint8_t  np;
    uint16_t side[2 * (SR_CUPD_PRE + SR_CUPD_R1)];
} sr_cupd_rounds;

void sr_cupd_end_reset(sr_cupd_end *e);
/* A club's final place (0 the top of `clubs`) in `division` (Serie D: first .. first + groups - 1). */
void sr_cupd_keep_place(sr_cupd_end *e, uint8_t first, uint8_t groups, uint16_t division, uint16_t slot,
                        int32_t place, int32_t clubs);
void sr_cupd_note_arrival(sr_cupd_end *e, uint16_t slot);

/* A later season's rounds 0-1: Serie D's clubs this season (base[slot] + their move: division[slot],
 * FFh none) in entry order -- from the season end e (0: unknown, a random order) -- relegated
 * from Serie C and the pool's new clubs first, then from the bottom of each group --, paired
 * within their groups where they can. season: the Mod's season byte (the year from 1900), its
 * generator's seed; word[slot] a slot's team word; rounds the cup's. The number of Serie D's
 * clubs. */
int32_t sr_cupd_make(const sr_cupd_end *e, uint32_t season, uint8_t rounds, uint8_t first, uint8_t groups,
                  int32_t nslots, const uint8_t *division, const uint16_t *word, sr_cupd_rounds *out);
/* (-1: rounds outside 2..8 -- a first round of more than 64 ties --, or first + groups past the
 * league's divisions: nothing made) */

/* ---- Parallel groups at the season end (sr_groups.c: gplay.c pg_one / pg_season, the Mod 4.0.5,
 * with 4.0.6's pg_a2 guard) ---- */

#define SR_PG_LEVELS   8            /* a league's levels (gplay.c PL) */
#define SR_PG_GROUPS   9            /* a level's groups side by side (PG: Serie D 2026-27's nine) */
#define SR_PG_PARALLEL 4            /* levels of groups whose areas a club carries */

/* One level of the league's chain, top-down: a single division (groups 1) or groups side by side,
 * divisions first .. first + groups - 1, each size[g] clubs. */
/* chain (not in the Mod: 0 for its leagues): when both choices of a club coming in are full and no club
 * there can step aside, a club of a full choice may go to its other choice by making room there in turn
 * (one step deeper), before the nearest-group fallback -- for a level whose groups are not in a line
 * (England's step 3: N C S I). */
typedef struct { uint8_t first, groups; uint8_t size[SR_PG_GROUPS]; uint8_t chain; } sr_pg_level;

/* A club that can play at a level of groups: its division in its team file (`base`: a division
 * offset is from it) and its area byte at each level of groups, top-down (the Mod's area_byte):
 * low nibble its 1st choice of group (A = 0), high nibble its 2nd + 1 -- 0 or Fh no 2nd, Eh any
 * group (a second team), + 8 never another group ('C,B!'); FFh no area. A swapped pool slot gives
 * its new identity's areas (the Mod's ripool ri_ida). */
typedef struct { uint8_t base; uint8_t area[SR_PG_PARALLEL]; } sr_pg_club;

typedef struct {
    uint8_t            levels;
    const sr_pg_level *level;
    uint16_t           clubs;       /* at most SR_CLUB_SLOTS, in the table's order (it decides) */
    const sr_pg_club  *club;
} sr_pg_league;

/* The game has moved every club one division up or down the league's chain (its divisions'
 * promoted / relegated counts). Each move becomes one LEVEL: into a single division as it is;
 * into a level of groups, the club's 1st choice, then its 2nd -- each with room, else room made by
 * moving a club that may go elsewhere --, else the group nearest to its 1st choice with room
 * (schema/v1.md, "Parallel leagues by area"). Clubs that stay are counted in their group first.
 * old_off[i] / new_off[i]: club i's division offset (division - base) before the season end and
 * after the game's move -- new_off rewritten. entering (0: none): nonzero for a slot taking a club
 * from below the chain this season end (the off-file pool's swap, the Mod's ri_og), which enters
 * the lowest level. 0; -1 a league past the limits above (nothing changed). */
int32_t sr_pg_season(const sr_pg_league *pg, const int8_t *old_off, int8_t *new_off, const uint8_t *entering);

/* The summer re-allocation of a level of two groups (England's National League North / South, Davide
 * 07/11 B): after sr_pg_season's moves, every club of level l -- the ones that stay too -- placed
 * again by its ground. Strict clubs (no 2nd choice in the level, or a ban) go to their 1st choice;
 * the flexible ones (a 2nd choice, or any group) by rank[i] -- the ground's north-south rank, 0 the
 * northernmost, SR_RANK_NONE none: placed as a strict club -- north first, ties by ident[i] (the club's
 * identity, NULL: its index), group 0 filled to its size, the rest into group 1. A group's strict
 * clubs past its size cross by rank too (the ones nearest the other group). Same clubs, same split,
 * whatever their slots. new_off rewritten for the level's clubs. The count of strict clubs that
 * crossed (0 with real data); -1 a level that is not one of two groups, or more clubs than room. */
#define SR_RANK_NONE 0xFF
int32_t sr_pg_realloc(const sr_pg_league *pg, int32_t l, const uint8_t *rank, const uint16_t *ident,
                      int8_t *new_off);

/* ---- A light pool's divisions (sr_pool.c: England's step 3, Davide 07/11 B) ----
 * Clubs with no league slot: a name, a strength, an area and a prebuilt record. Each season their
 * divisions are simulated from strength and the season's seed (no matches played), then each sends
 * up its champion and its play-off winner (2nd-7th, the National League's shape). */

#define SR_LP_DIVS  32              /* a pool's divisions (England's step 3: 4; Italy's Eccellenza: 28 groups) */
#define SR_LP_CLUBS 24              /* a pool division's clubs */

/* strength: hundredths of the club's built first-16 mean (step 3 2.50 .. 0.00; a club down from N / S
 * keeps its own, 3.06 and up: the favourite it is), the scale linear to 3.75; ident: the club's
 * identity (its pool record), which also seeds its matches */
typedef struct { uint16_t ident; uint16_t strength; } sr_lp_club;

/* The light tables' spread: a match's strength 30 .. 30 + SR_LP_SPREAD over 0.00 .. 2.50 (squared). Calibrated
 * against the real bounce-back (a club relegated from N / S straight back up: 7.3%, 4 of 55 over 2011-12 .. 2023-24,
 * en.wikipedia; the Mod's internal/nonleague2627/bounce). Under rule iii the mass simulation (tests/sim) gives 15.1% at
 * 40 and never below the 9.0% of pure chance (spread 0): 7.3% is out of reach of the spread; the value is Davide's. */
#ifndef SR_LP_SPREAD
#define SR_LP_SPREAD 40
#endif

/* Division d's light table of n clubs (n <= SR_LP_CLUBS), a double round robin: each match's goals by
 * the two strengths (home advantage, draws ~ 1 in 4) from seed, d and the two idents only -- the same
 * clubs give the same table whatever their order. out[0 .. n), best first (points, goal difference,
 * goals, then the higher strength, then the lower ident): team = the club's index in c, glob = its
 * ident. 0; -1 n out of range. */
int32_t sr_lp_table(uint32_t seed, int32_t d, const sr_lp_club *c, int32_t n, sr_row *out);

/* The play-off of a light table (2nd-7th: quarter-finals 4v7 and 5v6, semi-finals 2 and 3 v the
 * winners -- 2 v the lower placed --, the final; one match each, the better placed at home, extra time
 * and penalties near a coin toss): the winner's place in the table (1..6). n < 7: no play-off, -1. */
int32_t sr_lp_playoff(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c);

/* A pool season: nd divisions' light tables, then each one's champion and play-off winner up.
 * up[2 * d] / up[2 * d + 1]: their indices in division d's c[d] (champion, then play-off winner).
 * 0; -1 a division out of range. */
/* A club down from the level above (N / S) into the pool (Davide 08/11, D): the strength at its own position in
 * the level above's strength order (above[0 .. na), strongest first) taken at the same position of the pool's
 * (pool[0 .. np), strongest first), both linear between neighbours. -1 lists of fewer than 2. */
int32_t sr_lp_rank_strength(uint16_t own, const uint16_t *above, int32_t na, const uint16_t *pool, int32_t np);

/* A club down from the level above (N / S) into the pool (Davide 09/11, iii; replaces D above, which the mass
 * simulation showed draining the pool: its best leave each summer and D refilled from its bottom): the club keeps its
 * own strength, capped at the pool's strongest (pool[0 .. np), any order). -1 an empty pool. */
int32_t sr_lp_newcomer_strength(uint16_t own, const uint16_t *pool, int32_t np);

int32_t sr_lp_season(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n, int32_t *up);

/* The same with the spread given at run time (MC 09/11: a calibration of the engine's strength mapping, not a fact of
 * the competition, so not in the spec; the sims sweep it). The names above = these at SR_LP_SPREAD. */
int32_t sr_lp_table_sp(uint32_t seed, int32_t d, const sr_lp_club *c, int32_t n, sr_row *out, int32_t spread);
int32_t sr_lp_playoff_sp(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c, int32_t spread);
int32_t sr_lp_season_sp(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n, int32_t *up,
                        int32_t spread);

/* ---- A pool with a cross play-off (swc/1.4 'up.cross'; Italy's Eccellenza 2026-27, 4.2 light; MC 42-ecclp) ----
 * Each division sends up its champion and one club to a play-off across the pool's divisions through its own
 * play-off (Italy: the regional play-offs, then the national one); the cross play-off's winners go up; then `extra`
 * places: the override clubs first, then the declared rule (the Mod's italy42.md 5d). */

/* A division's play-off (the pool file's divisions[i].playoff, or its `direct` place): who of its table goes to
 * the cross play-off. kind SR_LP_RPO_DIRECT: the place `first` (1 = the 2nd); SR_LP_RPO_FOUR: places first .. first + 3,
 * first v first + 3 and first + 1 v first + 2, then the final; SR_LP_RPO_LADDER: first + 1 v first + 2, then the
 * winner v first. One match each, the better placed at home (final_neutral: the final on neutral ground). A tie
 * whose clubs are gap_skip points or more apart (the first round; gap_final: the final or the ladder's second step;
 * 0: always played) is not played: the better placed goes through. direct_gap: the place `first` this many points or
 * more ahead of the next goes through with no play-off (0: never). draw_better: a draw after extra time sends the
 * better placed through (else penalties, near a coin toss). */
enum { SR_LP_RPO_DIRECT, SR_LP_RPO_FOUR, SR_LP_RPO_LADDER };
typedef struct { uint8_t kind, first, gap_skip, gap_final, direct_gap, draw_better, final_neutral; } sr_lp_rpo;

/* The regional play-off's winner: its place in the table (0-based). -1 a shape out of the table. (_sp: the spread
 * at run time.) */
int32_t sr_lp_regional(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c,
                       const sr_lp_rpo *r);
int32_t sr_lp_regional_sp(uint32_t seed, int32_t d, const sr_row *table, int32_t n, const sr_lp_club *c,
                          const sr_lp_rpo *r, int32_t spread);

/* The cross play-off. e[0 .. ne): the entrants, urn[i] entrant i's urn (0 .. nu - 1). Round 1: each urn drawn in
 * pairs (legs1 legs). Round 2: its winners paired by pair[0 .. np) ({u, v}: one of urn u v one of urn v; u == v:
 * two of urn u), each pair kind used as long as it can be, in order, drawn (legs2 legs). Ties level on aggregate:
 * extra time, then penalties near a coin toss (no away goals). up[0 .. return): the winners' entrant indices.
 * -1 an urn of odd size, a winner left without a pair, a shape out of range. */
int32_t sr_lp_cross(uint32_t seed, const sr_lp_club *e, int32_t ne, const uint8_t *urn, int32_t nu,
                       const uint8_t (*pair)[2], int32_t np, int32_t legs1, int32_t legs2, int32_t *up);
int32_t sr_lp_cross_sp(uint32_t seed, const sr_lp_club *e, int32_t ne, const uint8_t *urn, int32_t nu,
                       const uint8_t (*pair)[2], int32_t np, int32_t legs1, int32_t legs2, int32_t *up, int32_t spread);

/* The cup's place (5d): of the clubs not up (isup[d][i] == 0), the strongest; ties: the better place in its table,
 * then the lower ident. override (SR_LP_NONE: none): that ident takes the place instead when it is in the pool and
 * not up. 0 and *od / *oi the club's division and index in c[od] (*ov 1: by the override); -1 no club left. */
#define SR_LP_NONE 0xFFFFu
int32_t sr_lp_extra(int32_t nd, const sr_lp_club *const *c, const int32_t *n, const uint8_t *const *place,
                    const uint8_t *const *isup, uint16_t override, int32_t *od, int32_t *oi, int32_t *ov);

/* A season's shape: per division its play-off and urn; the cross play-off's pairs and legs; the `extra` places and
 * the override clubs (override[0 .. nov): they take extra places first, in order, when in the pool and not up). */
typedef struct {
    const sr_lp_rpo *rpo;
    const uint8_t *urn;
    int32_t nu;
    const uint8_t (*pair)[2];
    int32_t np, legs1, legs2, extra;
    const uint16_t *override;
    int32_t nov;
    int32_t spread;                 /* < 0: SR_LP_SPREAD (0 is a spread: pure chance) */
    const uint16_t *barred;         /* idents that may not go up this season (4.2: a B team whose first team plays the */
    int32_t nbarred;                /* level above or lower, MC F4): passed over as if not in their tables -- the champion,
                                       the play-off places and the extra rule take the next club; 0 none */
} sr_lp_shape;

/* How a club went up: its division's champion, the cross play-off, the extra rule, an override club. */
enum { SR_LP_UP_CHAMPION = 1, SR_LP_UP_CROSS, SR_LP_UP_EXTRA, SR_LP_UP_OVERRIDE };
typedef struct { int16_t div, idx; uint8_t how; } sr_lp_up;

/* The whole season: nd divisions' light tables (as sr_lp_season), each champion up, the regional play-offs, the
 * cross play-off, the extra places. up[0 .. return): divisions' champions in division order, then the cross
 * play-off's winners, then the cup's places. -1 a division or a shape out of range. */
int32_t sr_lp_season_cross(uint32_t seed, int32_t nd, const sr_lp_club *const *c, const int32_t *n,
                        const sr_lp_shape *s, sr_lp_up *up);

/* ---- sr_stage.c: the generic stages a spec's competitions are made of (swc/1.2: round_robin, groups,
 * knockout / playoff rounds, single_match), as the competition editor writes them. Nothing in either
 * game plays them yet; the codes are swcc's dense ones (format/swc_format.h SwcTieBreak / SwcDecider,
 * checked equal by tests/rules/stage.c). A stage's clubs are 0 .. n-1 in the caller's order. */
#define SR_STAGE_CLUBS 64
enum { SR_TB_END = 0, SR_TB_POINTS, SR_TB_GOAL_DIFFERENCE, SR_TB_GOALS_FOR, SR_TB_GOALS_AGAINST, SR_TB_WINS,
       SR_TB_AWAY_WINS, SR_TB_AWAY_GOALS_FOR, SR_TB_H2H_POINTS, SR_TB_H2H_GOAL_DIFFERENCE, SR_TB_H2H_GOALS_FOR,
       SR_TB_H2H_AWAY_GOALS, SR_TB_FAIR_PLAY, SR_TB_COEFFICIENT, SR_TB_PREVIOUS_STAGE_RANK, SR_TB_PLAY_OFF_MATCH,
       SR_TB_DRAW_LOTS, SR_TB_NAME, SR_TB_FAITHFUL_1996,
       SR_TB_H2H_REAPPLIED, SR_TB_AVULSA, SR_TB_LOSSES_FEWER, SR_TB_HOME_LOSSES_FEWER, SR_TB_H2H_TABLE_ONCE };
enum { SR_D_END = 0, SR_D_AGGREGATE, SR_D_AWAY_GOALS, SR_D_EXTRA_TIME, SR_D_PENALTIES, SR_D_BETTER_PLACED,
       SR_D_REPLAY, SR_D_DRAW_LOTS, SR_D_GOLDEN_GOAL };

/* A match of a stage: its matchday (0-based), the two clubs; the score once played. */
typedef struct { uint8_t md, home, away, played, hg, ag; } sr_match;

/* A round robin's calendar (the circle method): every pair meets `legs` times (1..4), one match per club
 * per matchday, a club resting each matchday when n is odd; leg 2 the mirror of leg 1 (home and away
 * swapped), legs 3-4 again legs 1-2. Matchdays: legs * (n - 1), legs * n when n is odd. Each club at home
 * (n - 1) / 2 or n / 2 times a leg. Returns the matches written (legs * n * (n - 1) / 2), -1 for n outside
 * 2..SR_STAGE_CLUBS, legs outside 1..4, or room short. */
int32_t sr_rr_calendar(int32_t n, int32_t legs, sr_match *out, int32_t room);

/* A table's row: the club (0 .. n-1) and its record from the played matches. */
typedef struct { uint8_t club, pad; int16_t pts; uint16_t pl, w, d, l, gf, ga, aw, agf; } sr_srow;

/* The table of n clubs from the played matches (points win / draw / loss), ranked by the tie-breaker list
 * (SR_TB_*, 0-ended; each head-to-head criterion compares the matches among the clubs its block still holds;
 * SR_TB_AVULSA (FIGC): h2h points then h2h goal difference over all the clubs level when it starts, once;
 * SR_TB_H2H_TABLE_ONCE (EFL reg. 9.2): the same with h2h goals for as its third key (one mini-table); then the
 * next criterion; draw lots from the seed and the club, so the input order never matters; 'name' = the
 * caller's order). Returns n, or -1: a criterion the stage cannot use alone (fair play, coefficient,
 * previous stage rank, play-off match, faithful_1996: they need the game's data), a club outside 0..n-1. */
int32_t sr_rr_table(int32_t n, const sr_match *m, int32_t nm, int32_t win, int32_t draw, int32_t loss,
                    const uint8_t *tieb, uint32_t seed, sr_srow *out);

/* 4.2 S1: a league's table ranked by its tie-breaker list, from the game's own rows (the record criteria) and
 * the season's results between the clubs (head to head). row[c]: club c's record (club = c); pairs: n x n
 * bytes, pairs[h * n + a] = the result of h at home to a, home goals << 4 | away goals (each 0..14, 14 = 14 or
 * more: 15-15 would be SR_PAIR_NONE), SR_PAIR_NONE not played; NULL = no results kept (an old save, a season begun before them): the
 * head-to-head criteria are left out. namek[c]: club c's place in the names' order (the game's unsigned byte
 * compare), for 'name' and faithful_1996 (NULL: the caller's order). faithful_1996 = the 1996 game's own sort
 * (cseg_883DD): points, goal difference, goals for, name. ord[k] = the k-th club. No match list, no rows on
 * the stack: the DOS build's frames. Returns n, -1 for n outside 1..SR_STAGE_CLUBS or a criterion that needs
 * the game's data (fair play, coefficient, previous stage rank, play-off match). */
#define SR_PAIR_NONE 0xFF
int32_t sr_league_rank(int32_t n, const sr_srow *row, const uint8_t *pairs, const uint8_t *namek, int32_t win,
                       int32_t draw, int32_t loss, const uint8_t *tieb, uint32_t seed, uint8_t *ord);

/* A knockout's rounds: ties and byes per round, entrants the clubs that reach the first. Returns the clubs
 * left at the end; -(k + 1) when round k does not take the clubs that reach it (2 * ties + byes), as swcc. */
typedef struct { uint16_t ties, byes; } sr_round_size;
int32_t sr_ko_left(int32_t entrants, const sr_round_size *r, int32_t nr);

/* One tie: its legs (side 0's and side 1's goals, the home side, 2 = neutral), extra time and penalties if
 * played (after the last leg), the sides' places (better_placed: the lower wins). The aggregate score
 * first; level, the deciders in order. Returns the winning side 0 / 1, SR_TIE_REPLAY when the list says
 * 'replay', SR_TIE_OPEN when still level (a decider not played yet, or none left). */
enum { SR_TIE_REPLAY = 2, SR_TIE_OPEN = -1 };
typedef struct { uint8_t g[2], home; } sr_leg;
typedef struct { uint8_t et_played, et[2], pens_played, pens[2]; uint8_t place[2]; } sr_tie_extra;
int32_t sr_ko_tie(const sr_leg *leg, int32_t nlegs, const sr_tie_extra *x, const uint8_t *deci, uint32_t seed);

/* Group sizes for n clubs in g groups when the spec gives none: as even as can be, the larger first
 * (29 in 3: 10, 10, 9). Returns g, -1 when g < 1 or a group would have fewer than 2 clubs. */
int32_t sr_group_sizes(int32_t n, int32_t g, uint8_t *size);

/* A groups stage's draw: clubs 0..n-1 in seeding order (0 the best) into g groups sized by sr_group_sizes. Pot p =
 * clubs p*g .. p*g+g-1, one club of a pot per group; the last pot, when short, goes to the larger groups. assoc (NULL
 * = none): two clubs with one value never in one group. The draw goes pot by pot, the pot's clubs in an order hashed
 * from the seed, each to the first group (in an order hashed from the seed and the club) that still leaves a whole
 * draw possible -- UEFA's computer draw. grp[c] = club c's group. Returns g; -1 sizes refused (sr_group_sizes);
 * -2 no draw keeps the clubs of one association apart. */
int32_t sr_group_draw(int32_t n, int32_t g, const uint8_t *assoc, uint32_t seed, uint8_t *grp);

/* One group of a groups stage, for sr_best_placed: its clubs (0..n-1 inside it), its matches, its final table. */
typedef struct { const sr_match *m; int32_t nm, n; const sr_srow *table; } sr_group;

/* The clubs placed `place` (0 = the winners) across the groups, ranked best first: ord[k] = the k-th one's group.
 * A group without that place is left out. With groups of different sizes, each club's matches against the clubs
 * placed at or below the smallest group's size are dropped first (UEFA's best thirds). Criteria: sr_rr_table's
 * without head to head (clubs of different groups never met); 'name' = the groups' order. Returns the groups
 * ranked, -1 a criterion refused. */
int32_t sr_best_placed(const sr_group *g, int32_t ng, int32_t place, int32_t win, int32_t draw, int32_t loss,
                       const uint8_t *tieb, uint32_t seed, uint8_t *ord);

/* A knockout round's pairs (swcc's pairing codes): clubs 0..n-1 in seeding order, out[2k] v out[2k+1].
 *   fixed    0 v 1, 2 v 3, ... (the caller's order)
 *   bracket  n a power of 2: the top seeds meet last (8: 0 v 7, 3 v 4, 1 v 6, 2 v 5; halves 0..3 / 4..7 of out)
 *   seeded   each club of the top half v one of the bottom half, drawn; the seeded club first
 *   draw     any v any, drawn; the first drawn first
 * avoid (NULL = none): two clubs with one value (a group, an association) never paired. Draws by hashes, as
 * sr_group_draw (each pick leaves a whole round possible). Returns n / 2; -1 n odd or above SR_STAGE_CLUBS, bracket
 * not a power of 2, an unknown mode; -2 no pairing keeps them apart; -3 fixed / bracket pairs two clubs avoid
 * keeps apart. */
enum { SR_PAIR_DRAW = 0, SR_PAIR_SEEDED, SR_PAIR_BRACKET, SR_PAIR_FIXED };
int32_t sr_ko_pairs(int32_t mode, int32_t n, const uint8_t *avoid, uint32_t seed, uint8_t *out);

/* ---- sr_reg.c: one league across N team files -- the club registry (swc/1.4 countries.<c>.files; MC
 * 42-s7reg: Italy 4.2 = file 102 Serie A + B + C, file 144 Serie D + the Eccellenza stand-ins) ----
 * A club keeps its identity (an ident, 0 .. nclub-1) and has one place, its team word file | ordinal << 8,
 * or none (off the files). Each file is built with its divisions in its own order, each a range of rows
 * (its size), then its pool rows (at most one file has them); a division lives in exactly one file. */
#define SR_REG_FILES 8
#define SR_REG_CLUBS 1024
#define SR_REG_NONE  0xFFFF         /* an off-file club's word; an empty row's ident */
#define SR_REG_POOL  0xFE           /* a division value: the pool rows */
#define SR_REG_OUT   0xFF           /* a division value: off the files */
typedef struct {
    uint8_t  file;                  /* the team file's number (the word's low byte) */
    uint8_t  ndiv;
    uint8_t  div[SR_DIVS];          /* its divisions (the league's indices), in the file's order */
    uint8_t  size[SR_DIVS];         /* their sizes: rows */
    uint16_t pool;                  /* pool rows after them */
} sr_reg_file;
typedef struct {
    int32_t     nfiles, nclub;
    sr_reg_file f[SR_REG_FILES];
    uint16_t    word[SR_REG_CLUBS];         /* ident -> team word, SR_REG_NONE off the files */
    uint16_t    at[SR_REG_FILES][256];      /* (file index, ordinal) -> ident */
    uint8_t     rdiv[SR_REG_FILES][256];    /* (file index, ordinal) -> its club's division byte, SR_REG_POOL, SR_REG_OUT none */
    uint16_t    rows[SR_REG_FILES];
} sr_registry;
/* The records at team words a and b swapped; b == SR_REG_NONE: a's club goes off the files and club `on`
 * comes onto a (the off-file pool's record). In list order. */
typedef struct { uint16_t a, b, on; } sr_reg_swap;

/* Build from the layout: club i (0 .. n-1) of division div[i] (SR_REG_POOL a pool row, SR_REG_OUT off the
 * files) takes the next row of that division's range, clubs in index order -- so an old save's file order
 * (and then its off-file clubs) gives the new places with every club's order kept within its division: the
 * old-save import (a v1.3 save's words -> the registry, the caller keeping old word i -> word[i]). 0; -1 a
 * layout past the limits (files 1 .. 8, unique numbers, a division in one file, rows <= 256, pool rows in one
 * file at most) or a division's clubs not its size. */
int32_t sr_reg_build(sr_registry *r, int32_t nfiles, const sr_reg_file *f, int32_t n, const uint8_t *div);
uint16_t sr_reg_word(const sr_registry *r, int32_t ident);     /* SR_REG_NONE: off the files, or no such club */
int32_t sr_reg_ident(const sr_registry *r, uint16_t word);     /* -1: no club at that word */
int32_t sr_reg_div(const sr_registry *r, int32_t ident);       /* its row's division, SR_REG_POOL, SR_REG_OUT */
/* The season end's places (after sr_final_moves, the pool exchange, the groups): nd[ident] each club's new
 * division (SR_REG_POOL, SR_REG_OUT). Default (contiguous 0, the exe's: it reads each club's division byte,
 * MC 09/11): a club whose new division is in its file keeps its row, only its row's division changes; the
 * rows of a file freed by the clubs leaving it (to another file or off the files), ordered by their rank, go
 * to the clubs coming into it, ordered by theirs -- the best promoted into the row of the best placed
 * relegated. contiguous 1 (tests, tools): every division kept in its range of rows as built (moves inside a
 * file as swaps too). rank: order[0 .. norder) best first (the tables' order); a club not in it after them, by
 * ident. The moves as swaps out[0 .. count) for the exe to apply in order (its records move with the clubs:
 * the identity is kept, not EN's strength swap); the registry updated. w: the caller's work area (no big
 * locals: the exe's stack is small). The count; -1 a file's (contiguous: a division's) comings and goings
 * not equal or an unknown division (nothing changed), -2 more swaps than max (nothing changed). */
typedef struct {
    uint16_t rank[SR_REG_CLUBS], want[SR_REG_FILES][256], fr[256], en[256];
} sr_reg_work;
int32_t sr_reg_season(sr_registry *r, const uint8_t *nd, const uint16_t *order, int32_t norder, int32_t contiguous,
                      sr_reg_work *w, sr_reg_swap *out, int32_t max);
uint32_t sr_reg_size(void);         /* sizeof(sr_registry), sizeof(sr_reg_work): the exe's room ledger */
uint32_t sr_reg_work_size(void);
/* The invariants: every row holds one club, each club at most one row, words and rows agree. 0; -1. */
int32_t sr_reg_check(const sr_registry *r);

#endif
