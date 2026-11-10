/* ctband.c - 4.2 AFC mode (MC 11/11, room decision a): the confederation cups' group draw as a band of its own,
   linked on its own right after lrank.c's code in the code band obj4 0x6000..0xA000 (MC 11/11 option b; LR_TAB in
   the 11th page): ctdraw.c on its own copy of the rules library (tools/swce/sr_stage.c: cobj keeps only the sections
   ct_place reaches - sr_group_draw_k / _m and their search); lrank.c's link keeps sr_league_rank only. conti.c reaches ct_place through CT_SDRAW (conti.py sdraw_patch). */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_stage.c"
#include "ctdraw.c"
