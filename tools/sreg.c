/* N7 piece 3 (Panchina 10/11, MC's GO): the club registry in a save -- one league across N team files (S7: Italy's
   102 + 144), the engine's sr_reg / sr_regsave (tools/swce, the rules library at tools/swce/SWCE_SHA). obj4+SREG_AT
   (tools/sreg.py), linked only for a world with a registry shape: swe.c calls these through SREG_FN (0: dormant).

   The registry lives in swe.c's engine arena (SREG_REG -> SWE_ARENA_AT, ~8.3 KB: the band holds code + data only);
   swe.c keeps its bytes in SWC1's section 'IT' (n7-s7-clubmap.md §2):
   - sreg_build: from the spec (SREG_SPEC's files, SREG_DIV: each club's division in pack order = its ident, append-
     only, CONVENTIONS) -- a new career, or a save whose 'IT' is absent / of another layout / corrupt (the import of
     piece 4 takes the absent case over); deterministic: the same spec gives the same registry;
   - sreg_size / sreg_save: the section's bytes (sr_reg_save; flags 0, the caller's);
   - sreg_load: sr_reg_load -- 1 loaded, 0 absent / another layout, -1 corrupt; anything but 1 leaves REG rebuilt
     from the spec. */
#define SWOSRULES_HAVE_STDINT
typedef unsigned char uint8_t;
typedef signed char int8_t;
typedef unsigned short uint16_t;
typedef short int16_t;
typedef unsigned int uint32_t;
typedef int int32_t;
#include "swce/sr_reg.c"
#include "swce/sr_regsave.c"

#define DATA __attribute__((section(".data")))

/* sreg.py fills these: the files' shape and each club's division (SREG_NCLUB of them) */
int32_t SREG_NF DATA = 0, SREG_NCLUB DATA = 0;
sr_reg_file SREG_SPEC[SR_REG_FILES] DATA = {{0}};
extern const uint8_t SREG_DIV[];        /* obj4+swreg.SREG_DIV_AT, SR_REG_CLUBS bytes (MC 10/11: outside the band) */
sr_registry *SREG_REG DATA = 0;         /* sreg.py: -> the engine arena (swe.c SWE_ARENA_AT) */
int32_t SREG_LAST DATA = 0;             /* the last sreg_load's result (1 / 0 / -1; harness) */
static int32_t built DATA = 0;          /* *SREG_REG holds this career's registry */
#define REG (*SREG_REG)
typedef char registry_fits_the_arena[sizeof(sr_registry) <= SWE_ARENA ? 1 : -1];   /* (sreg.py: swe.c's SWE_ARENA) */

static uint32_t layout(void) { return sr_reg_layout(SREG_NF, SREG_SPEC, SREG_NCLUB); }

int32_t sreg_build(void)
{
    built = !sr_reg_build(&REG, SREG_NF, SREG_SPEC, SREG_NCLUB, SREG_DIV);
    return built ? 0 : -1;
}

int32_t sreg_size(void) { return built || !sreg_build() ? sr_reg_save_size(&REG) : -1; }

int32_t sreg_save(uint8_t *out, int32_t room, uint32_t season)
{
    if (!built && sreg_build()) return -1;
    return sr_reg_save(&REG, layout(), (uint16_t)season, out, room);
}

int32_t sreg_load(const uint8_t *in, int32_t len)
{
    if (sreg_build()) return SREG_LAST = -1;            /* (the spec first: sr_reg_load reads into a built shape) */
    int32_t r = sr_reg_load(&REG, layout(), in, len);
    if (r != 1) sreg_build();                           /* (0: nothing changed; -1 after the fill: rebuilt) */
    return SREG_LAST = r;
}

void sreg_new(void) { built = 0; SREG_LAST = 0; }     /* a new career: built from the spec at its first save */
