/* conti.c's shared layout (4.0.6: also ctview.c, the COPPE CONTINENTALI view, in obj3) */
#ifndef CONTI_H
#define CONTI_H
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int s32;

#define NA 128                          /* associations (countries) of the confederations in the world */
#define NL 32                           /* league clubs kept per association (the final table; J1 20, ARG 30) */
#define NC 1024                         /* clubs seen + the guest clubs */
#define NCUP 16
#define NRD 8                           /* rounds per cup (the Libertadores: 8) */
#define NE 64                           /* entrants of a round (CAF q1: 52) */
#define RB 24                           /* bytes per round in the spec */
#define OUT 0xFF
#define CHAMP 0xFE

/* round kinds, draws, association rules (spec byte values) */
enum { K_KO, K_GROUPS };
enum { D_ORDER, D_POTS2, D_SAMEPAIRS, D_SEED12, D_BRACKET, D_GROUPS, D_CROSS, D_SLOT, D_PLACE };
enum { A_ANY, A_NO, A_NOVIA };
/* access codes: 0 champion, 1 cup winner, 2..10 the k-th place, NEXT the best club not yet in, AP / CL a split
   season's stage champions (else as NEXT) */
enum { C_NEXT = 0x40, C_AP = 0x41, C_CL = 0x42 };

struct ct_in {                          /* filled by the caller */
    u32 seed;
    u16 nclub;
    u16 manager;                        /* the career club: index + 1 (0 = none) */
    u16 league[NA][NL];                 /* club indices + 1, final table order (0 = none) */
    u16 cup[NA];                        /* the national cup winner */
    u16 ap[NA], cl[NA];                 /* stage champions (Argentina) */
    struct { u16 id; u8 assoc; u8 pad; u32 str; u32 pts; } club[NC];   /* team word, association, strength, ranking */
};
struct ct_state {                       /* kept in the save */
    u16 mark;                           /* 'CT' */
    u16 season;
    struct { u16 id; u8 assoc; u8 pad; u32 str; u32 pts; } hold[NCUP];  /* each cup's holder (id 0 = none) */
};
struct ct_out {
    u8 ncup;
    u8 pad[3];
    u16 winner[NCUP], second[NCUP];     /* club indices + 1 */
    u8 last[NC];                        /* the last round reached by each club: cup << 4 | round, OUT none */
    u8 out_of[NC];                      /* how it left that round: 0 lost / eliminated, 1 won the cup */
    u8 nent[NCUP][NRD];                 /* entrants per round (after its draw) */
    u16 ent[NCUP][NRD][NE];             /* in draw order: ties (a, b) / groups of gsize */
    u8 res[NCUP][NRD][NE];              /* ko: 1 = the first club of the tie went through; groups: final place */
};

/* phase B: the edition being played, kept in the save (engine item 'CE'): its entrants (the access result), the
   career club's results so far; every step re-runs it from the start (same seed), the club's games forced, up to
   the club's next game: its segment (CT_SEG) goes into slot 3 */
#define NED 440                         /* (the save's room: the item must leave 80 team records; 384 used with
                                           all six confederations, reserves included) */
struct ct_ed {
    u16 mark;                           /* 'CE' */
    u16 ne;                             /* entries */
    u32 seed;
    u16 mgr;                            /* the career club's team word (0 = none) */
    u8 nf, pad;
    struct { u8 c, r, v; } f[16];       /* the club's results: ko 1 won / 0 lost, groups the place */
    struct { u8 id0, id1, cr, s0, s1; } e[NED];   /* an entrant: team word, cup << 4 | round (0xFF: a reserve
                                           club for group fills), strength / 16 (12 bits) | its slot << 12; the
                                           association from the team file (the guests' table), the ranking from
                                           the spec */
};
struct ct_seg {                         /* the career club's next game (CT_SEG.kind 0xFF: none) */
    u8 cup, round, kind, n;             /* kind: K_KO a tie (club[0] v club[1]), K_GROUPS the drawn groups */
    u8 legs, level, month, pos;         /* pos: the club's place in the list */
    u16 club[32];                       /* team words */
};
/* 4.0.6 option C (ctgame.c, obj3): the goals of a replay, kept only while CT_GREC points at one (the view's own
   replay; NULL in the season end's, a load's and the daily's runs - the same RNG calls either way). A played round's
   bytes from off[cup][round] - 1 (0: not kept): a knockout 3 per tie (D[2i] v D[2i+1]: the first leg, the second
   leg - D[2i+1] at home -, extra time; a one-legged tie its match in the first), a group stage its groups' matches
   in conti.c group()'s order. A byte: home goals + 1 | (away goals + 1) << 4 (extra time: its third); 0 no match,
   GR_OWN a game the career club played in the game (its goals not in the replay) */
#define GR_OWN 0xFF
struct ct_grec {
    u16 used, room;                     /* bytes of b[] used / available */
    u16 off[NCUP][NRD];
    u8 b[];
};
#endif
