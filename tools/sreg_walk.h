/* sreg_walk.h - the word-site walker's contract (S7, MC 13/11): the season-end swap builder (s7swap.c, Shaved) walks
   WSITES after its registry swaps; the table's rows are Panchina's (n7-s7-clubmap.md §4, the piece-1 inventory) and
   live in tools/wsites.py (ROWS), which s7swap.py renders into WSITES at link time. sreg_walk.c's walker core reads
   one row; the old-save import (SREG2) uses the same rows.

   A row: item, off, stride, count, form, aux.
   - item: where the bytes are -
       WI_CFB   (0)  careerFileBuffer (the .CAR fixed part: obj2+0x96D6 = .CAR +0),
       WI_CACHE (1)  the team cache: EACH cached record (off / stride inside one 684-byte record),
       WI_MAIN  (2)  the save's main block (C6, trailer.py),
       any other     an engine item 'EN' by its id = engine.item_id(name) (crc32 & 0xFFFF; wsites.py asserts it is
                     none of 0, 1, 2, WS_END and unique);
     WS_END (0xFFFF) ends the table.
   - off, stride, count: count values from off, stride bytes apart (count 1: stride 0 allowed).
   - form: WS_W a u16 team word (file | ordinal << 8; 0 / FFFFh = none); WS_G a u16 global number; WS_O8 a u8 ordinal
     whose file is the byte at aux (0FFh: file 102 fixed) - not handled yet (-2); WS_K a key computed over words:
     aux = the index of its owner's re-key callback in WS_KEYS[] (run once after the whole walk) - not handled yet (-2).
   - aux: per form above, else 0. */
#ifndef SREG_WALK_H
#define SREG_WALK_H

typedef struct { uint16_t item; uint16_t off, stride, count; uint8_t form, aux; } sreg_wsite;   /* 10 bytes */
typedef struct { uint8_t file, rows; uint16_t base; } sreg_gfile;     /* a WS_G file run: rows 0 = 256 */
enum { WS_W = 1, WS_G = 2, WS_O8 = 3, WS_K = 4 };
enum { WI_CFB = 0, WI_CACHE = 1, WI_MAIN = 2 };
#define WS_END 0xFFFF
#define WS_MAX 128                              /* WSITES' room: rows + the WS_END row (wsites.py asserts) */
extern const sreg_wsite WSITES[WS_MAX];          /* s7swap.c (.data, filled by s7swap.py from wsites.ROWS) */
typedef void (*sreg_rekey)(void);
extern sreg_rekey WS_KEYS[];                     /* WS_K's callbacks: none yet */

int32_t sreg_walk_site(const sreg_wsite *s, uint8_t *b, int32_t len, const sr_wpair *m, int32_t n,
                       const sreg_gfile *g, int32_t ng);

#endif
