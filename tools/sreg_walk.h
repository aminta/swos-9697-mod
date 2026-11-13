/* sreg_walk.h - the word-site walker's contract (S7, MC 13/11): the season-end swap builder (s7swap.c, Shaved) walks
   WSITES after its registry swaps; the table's rows are Panchina's (n7-s7-clubmap.md §4, the piece-1 inventory) and
   live in tools/wsites.py (ROWS), which s7swap.py renders into WSITES at link time. sreg_walk.c's walker core reads
   one row; the old-save import (SREG2) uses the same rows.

   A row: item, off, stride, count, form, aux.
   - item: where the bytes are -
       WI_CFB   (0)  careerFileBuffer (the .CAR fixed part: obj2+0x96D6 = .CAR +0),
       WI_CACHE (1)  the team cache: EACH cached record (off / stride inside one 684-byte record),
       WI_MAIN  (2)  the save's main block (C6, trailer.py),
       WI_CFBH  (3)  careerFileBuffer from byte 0x10000 on (a row's off is a u16: Panchina 13/11, WSITES 4b - 8 of the 17
                     regions lie above 0xFFFF; off here = the .CAR offset - 0x10000),
       any other     an engine item 'EN' by its id = engine.item_id(name) (crc32 & 0xFFFF; wsites.py asserts it is
                     none of 0, 1, 2, WS_END and unique);
     WS_END (0xFFFF) ends the table.
   - off, stride, count: count values from off, stride bytes apart (count 1: stride 0 allowed).
   - form: WS_W a u16 team word (file | ordinal << 8; 0 / FFFFh = none); WS_G a u16 global number; WS_O8 a u8 ordinal
     whose file is the byte at aux (0FFh: file 102 fixed) - not handled yet (-2); WS_K a key computed over words:
     aux = the index of its owner's re-key callback in WS_KEYS[] (run once after the whole walk) - not handled yet (-2).
   - WS_R (Panchina 13/11, cf-st-s7.md): a u8 array indexed by ORDINAL of a file (off, count <= 256; the entries are
     contiguous, so stride is not a step: stride = fill | file << 8 (MC 13/11, CD ent); file 0 = the file is the item's
     byte at aux, else aux is unused): each entry whose row's registry club CHANGED (its word is the old or the new word
     of a swap pair) is set to fill (CF: 0 = "unknown", the entry described the departed club; CD ent: 1 = new to Serie
     D); entries of rows that kept their club are untouched. Not a permutation: such a table is one file's, a crosser has no entry in
     the other file's.
   - aux: per form above, else 0. */
#ifndef SREG_WALK_H
#define SREG_WALK_H

typedef struct { uint16_t item; uint16_t off, stride, count; uint8_t form, aux; } sreg_wsite;   /* 10 bytes */
typedef struct { uint8_t file, rows; uint16_t base; uint8_t ord0, pad[3]; } sreg_gfile;   /* a WS_G run of a file:
                                           globals [base, base + rows) = ordinals [ord0, ord0 + rows); rows 0 = 256
                                           (a split file - G144 - has two runs) */
enum { WS_W = 1, WS_G = 2, WS_O8 = 3, WS_K = 4, WS_R = 5 };
enum { WI_CFB = 0, WI_CACHE = 1, WI_MAIN = 2, WI_CFBH = 3 };
#define WS_END 0xFFFF
#define WS_MAX 128                              /* WSITES' room: rows + the WS_END row (wsites.py asserts) */
extern sreg_wsite WSITES[WS_MAX];                /* s7swap.c (.data, filled by s7swap.py from wsites.ROWS) */
typedef void (*sreg_rekey)(void);
extern sreg_rekey WS_KEYS[];                     /* WS_K's callbacks: none yet */

int32_t sreg_walk_site(const sreg_wsite *s, uint8_t *b, int32_t len, const sr_wpair *m, int32_t n,
                       const sreg_gfile *g, int32_t ng);

#endif
