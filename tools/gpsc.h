/* tools/gpsc.h - the definitions gplay.c and gplay3.c share (MC 16/11: one copy, no drift): the base types, the
   supercup state's shape (SC_ST: SC_H header bytes + SC_NE entries of 12 B; SC_U = the last entry, the UEFA Super
   Cup; the friendlies' FR_ST is entry 14, tools/frnd.h FR_E) and IS_MGR. */
#ifndef GPSC_H
#define GPSC_H
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
enum { SC_E = 36, SC_NE = 16, SC_H = 12, SC_EARLY = 0x80 };   /* (entry byte 2: from_season | SC_EARLY) */
#define SC_U (SC_ST + SC_H + 12 * (SC_NE - 1))
#define IS_MGR(w) (GP_MGR && (u16)(w) == (u16)GP_MGR)   /* (S6a: GP_MGR 0 = no manager's club, gplay.py gp_mgr) */
_Static_assert(SC_H + 12 * (SC_NE - 1) == 192 && SC_H + 12 * SC_NE == 204,
               "SC_ST shape: SC_U at +192 (entry 15), FR_ST at +180 (entry 14), 204 B saved by the 'SC' item");
#endif
