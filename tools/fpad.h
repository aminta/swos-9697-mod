/* fpad.h -- 4.2 the fixture port: what fpad.c (obj4 FPORT band) and fpsave.c (P5, obj4 FPORT2 band: MC 15/11) share -
 * FP_ST's layout (swe.c .bss), the FP item's header (swe.c's FP_SAVE, the EN item 'FP'), the game's bytes both read */
#ifndef FPAD_H
#define FPAD_H
#include <stdint.h>
#include "swce/swosrules.h"

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t i32;

enum { FP_MAGIC = 0x50504631, FP_ARM = 0x4D524146, FL_N = 48 };   /* 'FPP1', 'FARM' */
struct fp_logent { u8 code, unit; int8_t rc; u8 x; u16 id, y; };
struct fp_st {
    u32 magic;
    u8 season, loaded, tadded, nlog;    /* (tadded: FPORT_TEST's fixtures queued this season) */
    u16 leg[2][4];                      /* this tie's legs as played: home team word, away, home goals (90'), away */
    u16 et[2], pens[2];                 /* the deciding leg's e.t. goals / penalties (FFFFh none), its home first */
    u8 nleg, pad[3];
    struct fp_logent log[FL_N];
};
typedef char fp_st_size_is[sizeof(struct fp_st) == FP_ST_SZ ? 1 : -1];   /* (swe.c's FP_ST: fpad.py ST_SIZE) */

/* P5 (MC option A): the EN item 'FP' at swe.c's FP_SAVE - this header, then sr_port_save's bytes. The tie in progress
   (its legs' goals: FP_ST, not sr_port) rides in the header; FP_HASH = the world + the format (fpad.fp_hash) */
struct fp_sv {
    u32 tag;                            /* 'FPS1' */
    u8 season, nleg, bad, ver;          /* the season saved, FP_ST.nleg / pad[0], FP_SAVE_VER */
    u16 len, pad;                       /* sr_port_save's length (0: no port saved) */
    u16 leg[2][4], et[2], pens[2];      /* FP_ST's tie in progress */
};
typedef char fp_sv_size_is[sizeof(struct fp_sv) == FP_SAVE_HDR ? 1 : -1];
enum { FP_STAG = 0x31535046, FP_SAVE_VER = 1 };

extern struct fp_st FP_ST;              /* swe.c .bss */
extern sr_port FP_PORT;                 /* swe.c .bss */
extern u8 FP_SAVE[FP_SAVE_SZ];          /* swe.c .bss: the FP item */
extern const u8 FP_SEASON;              /* obj2: the game's seasonPlaying byte (always current) */
extern const u8 FP_CWB;                 /* obj2: the career's world byte (careerworld; fpad.py's world: FP_WORLD) */

void fp_save(void);                     /* fpsave.c: engine.before_save */
i32 fps_load(void);                     /* fpsave.c: a load's FP item into FP_PORT + FP_ST's tie (see there) */
void fps_reset(void);                   /* fpsave.c: a new, empty port; no tie in progress (tadded, nleg, GP_PMID 0) */
#endif
