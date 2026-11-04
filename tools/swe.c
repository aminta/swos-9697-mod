/* The competition engine's object (engine step O, PLAN §19; CONVENTIONS 23bis): obj4, the engine's alone - its code in
   the file pages after the header (swe.py), its arena the zero-filled tail (.bss). DOS/4GW zeroes no tail, so the
   engine zeroes the arena itself: swe_init() first, before any other engine call.

   Step O links the empty engine: swe_init() only, called by nothing in the game yet (step W's registry is its first
   caller). Freestanding, cdecl, as every C file of the mod (cobj.py). */

typedef unsigned char u8;
typedef unsigned int u32;

#define SWE_VERSION 1
#define SWE_ARENA 0x8000                /* (step W sizes it: the world registry's tables) */

u8 SWE_ARENA_AT[SWE_ARENA];
u32 SWE_STATE;                          /* 0 = not initialised, 1 = swe_init ran */

int swe_init(void)
{
    volatile u8 *a = SWE_ARENA_AT;      /* (volatile: no memset call for clang to emit - there is no library) */
    for (u32 i = 0; i < SWE_ARENA; i++)
        a[i] = 0;
    SWE_STATE = 1;
    return SWE_VERSION;
}
