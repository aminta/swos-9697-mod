"""4.2 preseason friendlies (a), the engine's game side on the host: tools/frstep.c (fr_season / fr_step / fr_leg /
fr_gate, the FRSS.DAT read) built natively with the game around it mocked - swefile reads a real FRSS.DAT packed by
frstr.pack from tools/frdata's slices, ko_one records its calls and writes the contest's head as gplay's does (the week
clamp included), the calendar is synthetic. A C driver includes frstep.c; each check prints 'ok name' / 'FAIL name'."""
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

DRIVER = r'''
#include <stdio.h>
#include <string.h>
#define O_KO 16
#define O_SEASON 2
#define O_KIND 6
#define O_TW 40
#define O_D1 13
#define O_PTS 60
#define C_MAGIC 0x4B47
#define C_NOC 0xFF
#define C_KFR 13
#define C_LVBETTER 0
#define FR_BUFSZ 8192
#define FR_TEST 1
#include <stdint.h>
static uint8_t CALB[4 + 256];
#define FR_CAL (CALB + 4)
#define const
#include "frstep.c"
#undef const
static int fails;
#define CHECK(c, name, ...) do { if (c) printf("ok %s\n", name); else { fails++; printf("FAIL %s: ", name); \
    printf(__VA_ARGS__); printf("\n"); } } while (0)
u8 GP_GST[16 + 700]; u8 GP_SEAS; u32 GP_WK; u16 GP_MGR; u32 GP_K;
u8 FR_D1R[28]; static u16 A1T; u8 *FR_A1R = (u8 *)&A1T;
u16 FR_CALCUR; u8 FR_SEASON, FR_CWB; u8 FR_ST[FR_SZ]; u8 FR_BUF[FR_BUFSZ];
u32 FR_D6BA2; u16 FR_D6C4E; void *FR_SLOT4;
static int bad_d1, nko, ko_w1, ko_home, ko_away, ko_kind, ko_level, ko_lfile;
static void mock_ko_one(struct gp_ko *k, u16 h, u16 a, int w1, int w2, int legs, int kind, int level, int lfile,
                        const u8 *nm) {
    u8 *b = (u8 *)k; (void)w2; (void)legs; (void)nm;
    nko++; ko_w1 = w1; ko_home = h; ko_away = a; ko_kind = kind; ko_level = level; ko_lfile = lfile;
    *(u16 *)b = C_MAGIC; b[O_SEASON] = GP_SEAS; b[O_KIND] = (u8)kind; b[O_TW] = C_NOC;
    b[O_D1] = (u8)(w1 > (int)GP_WK ? w1 : (int)GP_WK + 1) + bad_d1;
}
void *GP_PAPI[1] = { (void *)mock_ko_one };
u32 tc_room(void) { return 50; }
u32 fr_cached_asm(u32 w) { (void)w; return 0; }
static const u8 *FILEB; static u32 FILEN, FPOS; static int opens;
int swe_fopen_r(char *n) { (void)n; opens++; FPOS = 0; return FILEB ? 5 : -2; }
int swe_fread(int h, void *b, unsigned int n) { (void)h; u32 m = FILEN - FPOS < n ? FILEN - FPOS : n;
    memcpy(b, FILEB + FPOS, m); FPOS += m; return (int)m; }
int swe_fclose(int h) { (void)h; return 0; }
static int nafter; static void after4(void) { nafter++; }
static int nnext; static u32 next_step(void) { nnext++; return 0; }
static void cal(int first) {            /* the league from week first, every 2 weeks, 20 days */
    memset(CALB, 0, sizeof CALB); u8 *e = CALB + 4; *(u16 *)CALB = 20;
    for (int i = 0; i < 20; i++, e += 8) { e[0] = 0; e[1] = (u8)(first + 2 * i); *(u16 *)(e + 2) = 8; e[6] = 1; }
}
static u8 *KO(void) { return GP_GST + O_KO; }
static void play(int gf, int ga, int home) {   /* a friendly's match: gp_rec -> fr_leg, then decided */
    A1T = home ? GP_MGR : 0x0101; *(u16 *)FR_D1R = (u16)(home ? gf : ga); *(u16 *)(FR_D1R + 4) = (u16)(home ? ga : gf);
    fr_leg(); KO()[O_TW] = 0;
    GP_WK = KO()[O_D1]; FR_CALCUR = 8;
}
int main(int argc, char **argv) {
    static u8 file[16384]; FILE *f = fopen(argv[1], "rb"); FILEN = (u32)fread(file, 1, sizeof file, f); fclose(f);
    FILEB = file;
    *(u16 *)GP_GST = C_MAGIC; GP_SEAS = FR_SEASON = 3; GP_MGR = 0x0001; FR_CWB = 0; cal(56);
    FR_D6BA2 = 4000000; FR_D6C4E = 40; FR_NSTEP = next_step; FR_AFTER4 = after4;
    /* 1. the season start: pick, FR_ST, FR_OPEN; no install */
    fr_season(GP_MGR);
    CHECK(FR_ST[0] == 3 && FR_ST[1] == FR_OPEN && FR_TRACE == 0x10 && nko == 0, "season_pick",
          "st %d %d trace %x nko %d", FR_ST[0], FR_ST[1], FR_TRACE, nko);
    int nh = 0; for (int k = 0; k < 4; k++) nh += FR_ST[10] >> k & 1;
    CHECK(nh == 2 && *(u16 *)(FR_ST + 2) != FR_NONE && *(u16 *)(FR_ST + 2) != GP_MGR, "season_words_venues", "nh %d", nh);
    /* 2. the first menu (CAL_CUR 0, GP_WK = the first entry's week): friendly 1 at 48, under ko_one's clamp */
    GP_WK = 56; FR_CALCUR = 0;
    CHECK(fr_step() == 1 && nko == 1 && ko_w1 == 48 && KO()[O_D1] == 48 && GP_WK == 56 && ko_kind == C_KFR &&
          ko_level == C_LVBETTER, "friendly1_week48", "nko %d w1 %d d1 %d wk %u", nko, ko_w1, KO()[O_D1], GP_WK);
    int h0 = FR_ST[10] & 1;
    CHECK((h0 ? ko_home : ko_away) == GP_MGR, "friendly1_venue", "home %x away %x", ko_home, ko_away);
    u32 fee0 = *(u16 *)(KO() + O_FEE);
    CHECK(FR_G > 0 && fee0 == FR_FEE[0] >> 4, "fee_kept_in_ko", "G %u fee %u ko %u", FR_G, FR_FEE[0], fee0);
    /* 3. held while being played; the gate pays the fee on slot 4 only */
    CHECK(fr_step() == 0 && nko == 1 && nnext == 0, "held_while_played", "nko %d next %d", nko, nnext);
    FR_CAL[0] = 4; FR_CALCUR = 0;
    CHECK(fr_gate(999) == fee0, "gate_fee", "%u", fr_gate(999));
    FR_CAL[0] = 0;
    CHECK(fr_gate(999) == 999, "gate_other_slot", "%u", fr_gate(999));
    /* 4. W / D / L, friendlies 2-4 at the advance after each, then closed + fr_after4 once + the chain */
    play(2, 0, h0);
    CHECK(FR_NPLAYED(FR_ST) == 1 && (FR_FLAGS(FR_ST) >> 4 & 7) == 1, "leg1_win", "played %d", FR_NPLAYED(FR_ST));
    CHECK(fr_step() == 1 && ko_w1 == 50, "friendly2_week50", "w1 %d", ko_w1);
    play(1, 1, FR_ST[10] >> 1 & 1);
    CHECK(fr_step() == 1 && ko_w1 == 52, "friendly3", "w1 %d", ko_w1);
    play(0, 3, FR_ST[10] >> 2 & 1);
    CHECK(fr_step() == 1 && ko_w1 == 54, "friendly4", "w1 %d", ko_w1);
    play(1, 0, FR_ST[10] >> 3 & 1);
    u32 fl = FR_FLAGS(FR_ST);
    CHECK(FR_NPLAYED(FR_ST) == 4 && (fl >> 4 & 7) == 2 && (fl >> 7 & 7) == 1 && (fl >> 10 & 7) == 1, "wdl_2_1_1",
          "fl %x", fl);
    CHECK(fr_step() == 0 && !(FR_ST[1] & FR_OPEN) && nafter == 1 && nnext == 1, "closed_after4_chain",
          "open %d after %d next %d", FR_ST[1] & FR_OPEN, nafter, nnext);
    fr_step();
    CHECK(nafter == 1 && nnext == 2, "after4_once", "after %d next %d", nafter, nnext);
    /* 5. next season: last season's four avoided, the level bits kept; an old save (season mismatch): nothing */
    u16 last[4]; memcpy(last, FR_ST + 2, 8);
    FR_ST[11] |= 0x80;                  /* (FR_LEVEL HARD... bit 15 as frc_choose would leave it) */
    GP_SEAS = FR_SEASON = 4; fr_season(GP_MGR);
    int rep = 0; for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) rep += *(u16 *)(FR_ST + 2 + 2 * i) == last[j];
    CHECK(FR_ST[0] == 4 && (FR_ST[11] & 0xC0) == 0x80 && rep == 0, "avoid_level_kept", "rep %d hi %x", rep, FR_ST[11]);
    GP_SEAS = FR_SEASON = 5; nko = 0; GP_WK = 70; FR_CALCUR = 9;
    CHECK(fr_step() == 0 && nko == 0, "old_season_nothing", "nko %d", nko);
    /* 6. a load mid-friendlies past the turn (GP_WK beyond the next week): closed, never installed late */
    GP_SEAS = FR_SEASON = 4; GP_WK = 56; FR_CALCUR = 0; KO()[O_SEASON] = 0; fr_step();
    play(0, 0, 1); GP_WK = 60;
    nko = 0; int na = nafter;
    CHECK(fr_step() == 0 && nko == 0 && !(FR_ST[1] & FR_OPEN) && nafter == na + 1, "missed_turn_closes",
          "nko %d open %d", nko, FR_ST[1] & FR_OPEN);
    /* 7. no FRSS.DAT / no slice for the world: no friendlies */
    FILEB = 0; GP_SEAS = FR_SEASON = 6; fr_season(GP_MGR);
    CHECK(FR_ST[0] == 6 && !(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x81, "no_file", "trace %x", FR_TRACE);
    FILEB = file; FR_CWB = 9; GP_SEAS = FR_SEASON = 7; fr_season(GP_MGR);
    CHECK(!(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x81, "no_world_slice", "trace %x", FR_TRACE);
    /* 8. every other refusal path leaves FR_OPEN clear (MC 16/11: one host check per path) */
    FR_CWB = 0; GP_SEAS = FR_SEASON = 8; GP_MGR = 0x7777; fr_season(GP_MGR);   /* (not in the table: FR_NOSELF) */
    CHECK(FR_ST[0] == 8 && !(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x82, "pick_refused", "trace %x", FR_TRACE);
    GP_MGR = 0x0001; memset(CALB, 0, sizeof CALB); GP_SEAS = FR_SEASON = 9; fr_season(GP_MGR);   /* (no league day) */
    CHECK(!(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x83, "no_turns", "trace %x", FR_TRACE);
    cal(56); GP_SEAS = FR_SEASON = 10; fr_season(GP_MGR); GP_WK = 56; FR_CALCUR = 0; bad_d1 = 1; na = nafter;
    CHECK(fr_step() == 0 && !(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x85 && nafter == na + 1 && *(u16 *)KO() == 0, "install_week_refused",
          "trace %x open %d", FR_TRACE, FR_ST[1] & FR_OPEN);
    bad_d1 = 0;
    /* 9. a native slot-4 contest (D8CBA set at the season start: play-offs, NSL; Friendlies 96-97 16/11):
       with FR_AFTER4 the friendlies go on, FR_NATIVE set; without it none (trace 0x86, no FR_OPEN) */
    static u8 nat4; FR_SLOT4 = &nat4; GP_SEAS = FR_SEASON = 11; fr_season(GP_MGR);
    CHECK(FR_ST[1] == FR_OPEN && FR_TRACE == 0x10 && (FR_FLAGS(FR_ST) & FR_NATIVE), "native_with_after4",
          "open %d trace %x fl %x", FR_ST[1], FR_TRACE, FR_FLAGS(FR_ST));
    FR_AFTER4 = 0; GP_SEAS = FR_SEASON = 12; fr_season(GP_MGR);
    CHECK(FR_ST[0] == 12 && !(FR_ST[1] & FR_OPEN) && FR_TRACE == 0x86, "native_no_after4_none", "open %d trace %x",
          FR_ST[1], FR_TRACE);
    FR_SLOT4 = 0; GP_SEAS = FR_SEASON = 13; fr_season(GP_MGR);
    CHECK(FR_ST[1] == FR_OPEN && !(FR_FLAGS(FR_ST) & FR_NATIVE), "no_native_bit_clear", "fl %x", FR_FLAGS(FR_ST));
    printf("fails %d\n", fails);
    return fails != 0;
}
'''


def test_frstep():
    sys.path.insert(0, TOOLS)
    import frstr
    d = tempfile.mkdtemp(prefix='frstep')
    blob = open(os.path.join(TOOLS, 'frdata', 'frstr_w0.bin'), 'rb').read()
    blob4 = open(os.path.join(TOOLS, 'frdata', 'frstr_w4.bin'), 'rb').read()
    dat = os.path.join(d, 'FRSS.DAT')
    open(dat, 'wb').write(frstr.pack({0: blob, 4: blob4}))
    src = os.path.join(d, 'drv.c')
    open(src, 'w').write(DRIVER)
    exe = os.path.join(d, 'drv')
    r = subprocess.run(['cc', '-O1', '-Wall', '-Wno-unused-function', '-Wno-unused-variable',
                        '-I', TOOLS, '-o', exe, src], capture_output=True, text=True)
    if r.returncode:
        return False, 'compile: ' + r.stderr[-900:]
    r = subprocess.run([exe, dat], capture_output=True, text=True)
    bad = [x for x in r.stdout.split('\n') if x.startswith('FAIL')]
    ok = [x for x in r.stdout.split('\n') if x.startswith('ok ')]
    return r.returncode == 0 and not bad and len(ok) >= 23, '; '.join(bad) if bad else f'{len(ok)} checks PASS'



def test_frstep_fee_field():
    """the fee >> 4 lives in ko[0].pts[2] (MC 16/11: FR_ST has no 2 free bytes): every gplay C reader / writer of a
    contest's pts[] indexes it by a list index (entrants < k->n; a ko_one contest has n = 2), never a constant >= 2 -
    a new access in another form fails here and must be checked against the friendlies' field"""
    import re
    ok_idx = {'a', 'b', 'pa', 'pb', 'i', 'j', '0', '1'}
    bad = []
    for f in ('gplay.c', 'gplay3.c', 'gplx.c', 'fpad.c'):
        src = open(os.path.join(TOOLS, f)).read()
        for m in re.finditer(r'(?:->|\.)pts\[([^\]]+)\]', src):
            if m.group(1).strip() not in ok_idx:
                bad.append(f'{f}:{src.count(chr(10), 0, m.start()) + 1} pts[{m.group(1)}]')
    return not bad, '; '.join(bad) if bad else 'every pts[] access by a list index (a, b, pa, pb, i, j, 0, 1)'


GPMAIN = r"""#include <stdio.h>
#include "%s"
u8 GP_SEAS;
static u8 tab[1 + SC_E];
int main(void) {
    GP_SEAS = 5; GP_MGR = 0x0166; tab[0] = 1; tab[1] = 0x66; GP_SCT = tab;
    SC_ST[3] = GP_SEAS; SC_ST[4] = 0;   /* (the career club's supercup this season, its tie not built yet) */
    u8 *fr = SC_ST + SC_H + 12 * FR_E;
    printf("a %%u %%d %%d\n", sc_wline_c(), slot4_busy(), sc_busy());
    fr[0] = GP_SEAS; fr[1] = FR_OPEN;  /* (the friendlies hold slot 4) */
    printf("b %%u %%d %%d\n", sc_wline_c(), slot4_busy(), sc_busy());
    fr[1] = 0; GP_ST.magic = GP_ST.ko[0].magic = MAGIC; GP_ST.ko[0].season = GP_SEAS; GP_ST.ko[0].kind = K_FR;
    GP_ST.ko[0].tw[0] = NOC;           /* (a friendly being played) */
    printf("c %%u %%d %%d\n", sc_wline_c(), slot4_busy(), sc_busy());
    fr[0] = GP_SEAS - 1; fr[1] = FR_OPEN; GP_ST.ko[0].magic = 0;   /* (last season's FR_ST: holds nothing) */
    printf("d %%d\n", slot4_busy());
    return 0;
}
"""


def test_frstep_slot4_busy():
    """Convergence 16/11: sc_busy keeps its supercup-only meaning (sc_wline_c's VINCITORI line: a supercup pending
    and the friendlies holding slot 4 -> still no line), slot4_busy = FR_OPEN this season, or sc_busy, or an undecided
    K_FR in ko[0] (the two slot guards). gplay.c built natively with GP_FRND=1 (as sc_rules)"""
    d = tempfile.mkdtemp(prefix='frs4')
    open(os.path.join(d, 't.c'), 'w').write(GPMAIN % os.path.join(TOOLS, 'gplay.c'))
    r = subprocess.run(['clang', '-w', '-DSS_NB=1', '-DGP_FRND=1', '-c', 't.c', '-o', 't.o'], cwd=d, capture_output=True,
                       text=True)
    if r.returncode:
        return False, 'clang: ' + r.stderr[-500:]
    und = [x.strip().lstrip('_') for x in subprocess.run(['nm', '-u', 't.o'], cwd=d, capture_output=True,
                                                          text=True).stdout.split()]
    open(os.path.join(d, 's.c'), 'w').write(''.join(f'char {x}[65536];\n' for x in und
                                                     if x and not x.startswith(('printf', 'memcpy', 'memset', 'dyld', '__'))))
    r = subprocess.run(['clang', '-w', 't.o', 's.c', '-o', 't'], cwd=d, capture_output=True, text=True)
    if r.returncode:
        return False, 'link: ' + r.stderr[-500:]
    got = {ln.split()[0]: ln.split()[1:] for ln in subprocess.run(['./t'], cwd=d, capture_output=True,
                                                                 text=True).stdout.splitlines()}
    want = {'a': ['0', '0', '0'], 'b': ['0', '1', '0'], 'c': ['0', '1', '0'], 'd': ['0']}
    bad = [f'{k} {got.get(k)} != {v}' for k, v in want.items() if got.get(k) != v]
    return not bad, '; '.join(bad) or 'pending supercup + FR_OPEN: no VINCITORI line, slot 4 held; a K_FR in play held; last season\'s FR_ST nothing'


if __name__ == '__main__':
    print(test_frstep(), test_frstep_fee_field(), test_frstep_slot4_busy())
