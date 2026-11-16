"""4.2 the mini-league's views and trophies (tools/fpmlv.c / fpmlv.py, lane 2 of the Supercoppa Serie C) on the host:
fpmlv.c compiled natively against STUBS of tools/fpml.h (fp_ml_get / fp_ml_row over a test FP_ML / FP_MLT; fp_ml_table =
the vendored engine's sr_rr_table) - lane 1's producer is not needed. No exe, no DOSBox.

test_fpmlv_c: the scenarios of fpmlv.c's contract (old save, open, decided in May, the season end, the next season,
              a full WN_ST, the record line's three conditions, the calendar names, the table);
test_fpmlv_strings: FPV_TAB in the four languages (every string within its bar, font characters only), the layout
              fpmlv.h declares, the numbering, the WINNERS source, the FORMAT hook (empty until the prose is in);
test_fpmlv_winners_asm: winners.py's 'N' rewrites apply to its source exactly once each and assemble (nasm);
test_fpmlv_size: fpmlv.c's size in the exe's shape (a dry link, -Oz) within fpmlv.RESERVE less its slack."""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)

ROW = {'key': 'supercoppa_c', 'names': {'*': ['SUPERCOPPA SERIE C', 'SUPERCOPPA C']},
       'entrants': [[2, 1], [3, 1], [4, 1]], 'schedule': 'winner_rests', 'legs': 1, 'points': [3, 1, 0],
       'record': {'*': 'SUPERCOPPA SERIE C'}}
COMP = {'key': 'league', 'mini_leagues': [ROW]}
COUNTRY = {'it': 'ITALIA', 'en': 'ITALY', 'fr': 'ITALIE', 'de': 'ITALIEN'}

DRIVER = r'''
#include <stdio.h>
#include <string.h>
#include "fpmlv.h"
#include "swce/swosrules.h"
u8 GP_SEAS; u16 GP_MGR; u32 GP_WNSRC;
struct wn_e { u8 type, idx; u16 team; };
struct wn_state { u16 magic; u8 season, n; struct wn_e e[40]; } WN_ST;
extern struct fpv_tab FPV_TAB;
static struct fp_ml ML[FP_ML_N];
static struct fp_mlrow MLT[2];
const struct fp_ml *fp_ml_get(u32 i) { return i < FP_ML_N && ML[i].id ? &ML[i] : 0; }
const struct fp_mlrow *fp_ml_row(u8 id) { return id >= 1 && id <= 2 && MLT[id - 1].id ? &MLT[id - 1] : 0; }
i32 fp_ml_table(const struct fp_ml *ml, void *rows)
{
    const struct fp_mlrow *r = fp_ml_row(ml->id);
    static const u8 tb[] = { SR_TB_GOAL_DIFFERENCE, SR_TB_GOALS_FOR, SR_TB_AWAY_GOALS_FOR, SR_TB_DRAW_LOTS, 0 };
    return sr_rr_table(ml->n, (const sr_match *)ml->m_raw, 3, r->pts[0], r->pts[1], r->pts[2], tb, ml->seed, rows);
}
static void match(struct fp_ml *ml, int k, int md, int h, int a, int played, int hg, int ag)
{
    const u8 m[6] = { (u8)md, (u8)h, (u8)a, (u8)played, (u8)hg, (u8)ag };
    memcpy(ml->m_raw + 6 * k, m, 6);
}
static void show(const char *what)
{
    printf("%s wn=%04X run=", what, fpv_wn_c());
    printf("%04X rl0=%u rl1=%u wnn=%u fl=%u/%u\n", 0, fpv_rline_c(0), fpv_rline_c(1), WN_ST.n, ML[0].flags, ML[1].flags);
}
int main(void)
{
    struct fpv_trow t[4];
    FPV_TAB.nname = 1; FPV_TAB.nrec = 1; FPV_TAB.zone = 0x0D; strcpy(FPV_TAB.leg, "VINCE");
    FPV_TAB.nm[0][0] = 0x1111; FPV_TAB.nm[0][1] = 0x2222; FPV_TAB.rec[0] = 0x3333; FPV_TAB.ttl[0] = 0x4444;
    MLT[0].id = 1; MLT[0].n = 3; MLT[0].pts[0] = 3; MLT[0].pts[1] = 1; MLT[0].name = 0; MLT[0].rec = 0; MLT[0].flags = 1;
    GP_SEAS = 30; GP_MGR = 0x0A45; GP_WNSRC = 'N' | 1 << 8;
    WN_ST.magic = 0x4E57; WN_ST.season = 29; WN_ST.n = 2;       /* the season before's list + a preview's marker */
    WN_ST.e[0].type = 'M'; WN_ST.e[1].type = 'L'; WN_ST.e[2].type = 'p'; WN_ST.e[2].idx = 30; WN_ST.n = 3;
    show("old");                                                /* an old save: FP_ML zero */
    printf("old table=%d title=%u names=%d\n", fpv_table(0, t), fpv_title(0), fpv_calnames(0x4D4C1E01) != 0);
    fpv_done(0); fpv_done(&ML[0]);
    show("old-done");
    ML[0].id = 1; ML[0].state = 1; ML[0].n = 3; ML[0].season = 30; ML[0].seed = 7;
    ML[0].club[0] = 0x0A45; ML[0].club[1] = 0x0B45; ML[0].club[2] = 0x0C45;
    match(&ML[0], 0, 1, 0, 1, 0, 0, 0); match(&ML[0], 1, 2, 2, 1, 0, 0, 0); match(&ML[0], 2, 3, 0, 2, 0, 0, 0);
    fpv_done(&ML[0]);                                           /* not decided: nothing */
    show("open");
    printf("open table=%d\n", fpv_table(0, t));
    match(&ML[0], 0, 1, 0, 1, 1, 2, 0); match(&ML[0], 1, 2, 2, 1, 1, 1, 1); match(&ML[0], 2, 3, 2, 0, 1, 0, 1);
    ML[0].state = 2; ML[0].have = 3; ML[0].winner = 0x0A45;
    fpv_done(&ML[0]);                                           /* decided in May: WN_ST still the season before's */
    show("may");
    int n = fpv_table(0, t);
    printf("table n=%d title=%u leg=%s\n", n, fpv_title(0), fpv_legend());
    for (int k = 0; k < n; k++)
        printf("row %d team=%04X col=%02X %d %d %d %d %d-%d pts=%d\n", k, t[k].team, t[k].colour, t[k].pl, t[k].w, t[k].d,
               t[k].l, t[k].gf, t[k].ga, t[k].pts);
    GP_MGR = 0x0B45; show("may-other");                         /* the career club is not the winner: no record line */
    GP_MGR = 0x0A45; MLT[0].flags = 0; show("may-norec");       /* the row's FP_MLF_RECORD off */
    MLT[0].flags = 1; MLT[0].rec = 3; show("may-badrec");       /* a record id past the table */
    MLT[0].rec = 0; GP_MGR = 0; show("may-nomgr"); GP_MGR = 0x0A45;
    WN_ST.season = 30; WN_ST.n = 2;                             /* the season end: gp_season has rewritten WN_ST */
    fpv_done(&ML[0]);
    show("end");
    printf("end entry=%c %u %04X\n", WN_ST.e[2].type, WN_ST.e[2].idx, WN_ST.e[2].team);
    fpv_done(&ML[0]); ML[0].flags = 0; fpv_done(&ML[0]);        /* the repeat, with the bit and without (the entry there) */
    show("end-repeat");
    GP_SEAS = 31; show("next");                                 /* the next season: this season's page */
    GP_WNSRC |= 1u << 24; show("next-last");                    /* its last season's page */
    GP_WNSRC = 'N' | 2 << 8 | 1u << 24; show("next-last-id2");
    WN_ST.season = 29; GP_WNSRC = 'N' | 1 << 8 | 1u << 24; show("next-stale");
    GP_SEAS = 30; GP_WNSRC = 'N' | 1 << 8;
    ML[0].flags = 0; WN_ST.season = 30; WN_ST.n = 40; memset(WN_ST.e, 0, sizeof WN_ST.e);
    fpv_done(&ML[0]); show("full");                             /* WN_ST full: no line, the bit clear */
    WN_ST.n = 1; WN_ST.e[0].type = 'p'; fpv_done(&ML[0]); show("marker");
    printf("names ml=%d other=%d badrow=%d badname=", fpv_calnames(0x4D4C1E01) == (const u8 *)FPV_TAB.nm[0],
           fpv_calnames(0x7E001E00) != 0, fpv_calnames(0x4D4C1E11) != 0);
    MLT[0].name = 2; printf("%d\n", fpv_calnames(0x4D4C1E01) != 0);
    return 0;
}
'''

EXPECT = '''old wn=FFFE run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
old table=0 title=0 names=1
old-done wn=FFFE run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
open wn=FFFF run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
open table=3
may wn=0A45 run=0000 rl0=13107 rl1=0 wnn=3 fl=0/0
table n=3 title=17476 leg=VINCE
row 0 team=0A45 col=0D 2 2 0 0 3-0 pts=6
row 1 team=0C45 col=00 2 0 1 1 1-2 pts=1
row 2 team=0B45 col=00 2 0 1 1 1-3 pts=1
may-other wn=0A45 run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
may-norec wn=0A45 run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
may-badrec wn=0A45 run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
may-nomgr wn=0A45 run=0000 rl0=0 rl1=0 wnn=3 fl=0/0
end wn=0A45 run=0000 rl0=13107 rl1=0 wnn=3 fl=1/0
end entry=N 1 0A45
end-repeat wn=0A45 run=0000 rl0=13107 rl1=0 wnn=3 fl=1/0
next wn=FFFE run=0000 rl0=0 rl1=0 wnn=3 fl=1/0
next-last wn=0A45 run=0000 rl0=0 rl1=0 wnn=3 fl=1/0
next-last-id2 wn=FFFE run=0000 rl0=0 rl1=0 wnn=3 fl=1/0
next-stale wn=FFFE run=0000 rl0=0 rl1=0 wnn=3 fl=1/0
full wn=0A45 run=0000 rl0=13107 rl1=0 wnn=40 fl=0/0
marker wn=0A45 run=0000 rl0=13107 rl1=0 wnn=1 fl=0/0
names ml=1 other=0 badrow=0 badname=0
'''


def test_fpmlv_c():
    with tempfile.TemporaryDirectory() as t:
        drv = os.path.join(t, 'drv.c')
        open(drv, 'w').write(DRIVER)
        exe = os.path.join(t, 'drv')
        r = subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', '-O1', '-DFPV_DATA=', '-I', TOOLS, drv,
                            os.path.join(TOOLS, 'fpmlv.c'), os.path.join(TOOLS, 'swce', 'sr_stage.c'), '-o', exe],
                           capture_output=True, text=True)
        if r.returncode:
            return False, 'native build: ' + r.stderr[-800:]
        out = subprocess.run([exe], capture_output=True, text=True).stdout
    if out != EXPECT:
        a, b = out.splitlines(), EXPECT.splitlines()
        d = [f'{x!r} != {y!r}' for x, y in zip(a, b) if x != y] or [f'{len(a)} lines, expected {len(b)}']
        return False, d[0]
    return True, f'{len(EXPECT.splitlines())} lines: old save, open, May, season end, repeat, next season, full WN_ST, names, table'


def test_fpmlv_strings():
    import complist
    import fpmlv
    import gplay
    import zones
    bad = []
    if fpmlv.indices(COMP) != [(1, 0, 0, 1)]:
        bad.append(f'indices {fpmlv.indices(COMP)}')
    if fpmlv.indices({'mini_leagues': [dict(ROW, record=None)]}) != [(1, 0, 0, 0)]:
        bad.append('indices: a row without record keeps FP_MLF_RECORD')
    got = {}
    for lang in fpmlv.LANGS:
        pool = []

        def off(b, pool=pool):
            if b not in pool:
                pool.append(b)
            return 0x100 + pool.index(b)
        tab = fpmlv.table(COMP, lang, off, COUNTRY[lang])
        nn, nr, zone, _, leg = struct.unpack_from('<4B8s', tab)
        nm = struct.unpack_from('<II', tab, 12)
        rec, = struct.unpack_from('<I', tab, 12 + 8 * fpmlv.NN)
        ttl, = struct.unpack_from('<I', tab, 12 + 8 * fpmlv.NN + 4 * fpmlv.NR)
        s = lambda o: pool[o - 0x100].decode()
        got[lang] = (s(nm[0]), s(nm[1]), s(rec), s(ttl), leg.rstrip(b'\0').decode())
        if (len(tab), nn, nr, zone) != (fpmlv.TAB_SIZE, 1, 1, zones.LIGHT_BLUE):
            bad.append(f'{lang}: header {(len(tab), nn, nr, zone)}')
        title = f'{COUNTRY[lang]} {s(nm[0])}'
        if len(title) > complist.TITLE_MAX or complist.px(title) > complist.VC_PX:
            bad.append(f'{lang}: title {title} {len(title)} / {complist.px(title)} px')
        if complist.px(s(nm[1])) > complist.CAL_PX or complist.px(s(rec)) > gplay.REC_PX:
            bad.append(f'{lang}: label / record width')
        if len(got[lang][4]) > 5 or complist.px(got[lang][4]) > zones.LEG_W:
            bad.append(f'{lang}: legend {got[lang][4]}')
        if any(ch not in complist.FONT for x in got[lang] for ch in x):
            bad.append(f'{lang}: a character outside the font in {got[lang]}')
    want_leg = {'it': 'VINCE', 'en': 'WINS', 'fr': 'VAINQ', 'de': 'SIEG'}
    for lang in fpmlv.LANGS:
        if got[lang][:4] != ('SUPERCOPPA SERIE C', 'SUPERCOPPA C', 'SUPERCOPPA SERIE C', 'SUPERCOPPA SERIE C') \
                or got[lang][4] != want_leg[lang]:
            bad.append(f'{lang}: {got[lang]}')
    try:                                                    # a label past the calendar's 70 px: the build stops
        fpmlv.names(dict(ROW, names={'*': ['SUPERCOPPA SERIE C', 'SUPERCOPPA SERIE C']}), 'it', 'ITALIA')
        bad.append('a 98 px calendar label accepted')
    except AssertionError:
        pass
    try:
        fpmlv.names(dict(ROW, names={'*': ['SUPERCOPPA & C', 'SUPERC. C']}), 'it', 'ITALIA')
        bad.append("'&' accepted")
    except AssertionError:
        pass
    on = fpmlv.on
    try:
        fpmlv.on = lambda: True
        src = [fpmlv.win_sources(COMP, k) for k in range(6)]
        if [bool(x) for x in src] != [False, False, True, True, True, False] or src[2][0][1] != 'N100':
            bad.append(f'win_sources {src}')
        fpmlv.on = lambda: False
        if any(fpmlv.win_sources(COMP, k) for k in range(6)):
            bad.append('win_sources in a build without the port')
    finally:
        fpmlv.on = on
    if fpmlv.format_item(ROW, COUNTRY) is not None:
        bad.append('format_item without prose')
    prose = fpmlv.PROSE
    try:
        fpmlv.PROSE = {'supercoppa_c': {lang: ['X'] for lang in fpmlv.LANGS}}
        titles, text = fpmlv.format_item(ROW, COUNTRY)
        if titles != {lang: f'{COUNTRY[lang]} SUPERCOPPA SERIE C' for lang in fpmlv.LANGS} or text['de'] != ['X']:
            bad.append(f'format_item {titles}')
    finally:
        fpmlv.PROSE = prose
    return not bad, '; '.join(bad) or '4 languages: ' + ', '.join(f'{k} {v[1]} / {v[4]}' for k, v in got.items()) + \
        '; title, label, record, legend within their bars; WINNERS N100 for divisions 2-4; FORMAT hook empty'


def test_fpmlv_winners_asm():
    """winners.py's rewrites for 'N' (the port's builds): each anchor once, and the rewritten GP_CALL assembles."""
    import fpmlv
    import nasmcave
    import winners
    src = nasmcave.sub(winners.ASM, """    cmp byte [ebx], 0                   ; (dummy: replaced below)
    ret""", winners.GP_CALL)
    try:
        s2 = nasmcave.sub(src, winners.GP_CALL, nasmcave.sub(winners.GP_CALL, '    call GP_WN_C\n', fpmlv.WN_ASM_CALL))
        for a in (".nf:\n    pop edx\n", '.hex2:\n', "WN_KEY: db 1, 'H', '0000'\n",
                  "    cmp al, 'E'                         ; (4.0.5 the fallback line: last season's 1st of the career club's level)\n    je .lle\n"):
            nasmcave.sub(s2, a, a)
    except AssertionError as e:
        return False, f'an anchor of the rewrite is gone: {e}'
    body = ("bits 32\norg 0x1000\nGP_WN_C equ 0x5000\nstart:\n" + fpmlv.WN_ASM_CALL + "    ret\nwn_mlp: dd 0\n")
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, 'a.asm')
        open(f, 'w').write(body)
        r = subprocess.run(['nasm', '-f', 'bin', f, '-o', os.path.join(t, 'a.bin')], capture_output=True, text=True)
        if r.returncode:
            return False, 'nasm: ' + r.stderr[-300:]
        n = os.path.getsize(os.path.join(t, 'a.bin'))
    return True, f'5 anchors once each; the call sequence assembles ({n - 5} B + the dword)'


def test_fpmlv_size():
    import fpmlv
    try:
        end = fpmlv.size()
    except Exception as e:                                  # (no cross clang / cobj cache on this machine)
        return True, f'SKIP: dry link not possible here ({type(e).__name__}: {str(e)[:120]})'
    ok = end + fpmlv.SLACK <= fpmlv.RESERVE
    return ok, f'fpmlv.c {end} B at -Oz (code + FPV_TAB {fpmlv.TAB_SIZE} B) of RESERVE {fpmlv.RESERVE} B, {fpmlv.RESERVE - end} B left'
