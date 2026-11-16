"""S6a (c), MC 15/11 condition 2: an all-CPU world SEASON has no manager's club - gplay.py gp_mgr returns 0 and every
GP_MGR use in gplay.c handles 0 (gplay.c built natively with a driver that includes it, as test_cd_dt):
- kidx(k, 0) = NOC even with a 0 word in k's list (the placeholder day gf_place_c / gf_anchor_c, gp_perm_c, the
  record lines, gp_rl);
- IS_MGR(0) false (Coppa D cd_step_c's membership / build / CD_ST.pad, gp_sack's play-out loser and table row, the
  GF placeholder's 'career club not in it', the supercups); mgr_div() -1 when GP_IN.mgr is 0 (sres_of, stage_dec);
- gf_place_c / gf_anchor_c return 0, club_res 0, gp_sack_c 0 (positive controls: the same states with GP_MGR set);
- hum_alive (condition 1, gp_perm_c's +4Bh count): every human club of a SEASON (GP_HUM), 0 with none;
- no raw GP_MGR compare left outside the test switches (GP_FORCE / GP_GFFORCE / GP_CDFORCE / USC_FORCE lines);
- mutations: kidx / IS_MGR / mgr_div without the 0 guard are caught."""
import ctypes
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
FLAGS = ['-DGP_S7=0', '-DSS_NB=1', '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0']
A, B, C, D, E = 0x0165, 0x0265, 0x0365, 0x0465, 0x0565

DRIVER = r'''
#include "gplay.c"
static void kset(struct gp_ko *k, const u16 *t, int n) {
    u8 *p = (u8 *)k;
    for (unsigned i = 0; i < sizeof *k; i++) p[i] = 0;
    k->magic = MAGIC; k->season = GP_SEAS; k->n = n;
    for (int i = 0; i < n; i++) k->team[i] = t[i];
}
static const u16 T0[4] = { 0x0165, 0, 0x0265, 0x0365 };
int d_kidx(u32 team) { struct gp_ko k; kset(&k, T0, 4); return kidx(&k, (u16)team); }
int d_ismgr(u32 mgr, u32 w) { GP_MGR = (u16)mgr; return IS_MGR(w) ? 1 : 0; }
int d_mgrdiv(u32 mgr) {
    GP_IN.nd = 1; GP_IN.n[0] = 2; GP_IN.t[0][0].team = 0; GP_IN.t[0][1].team = 0x0165; GP_IN.mgr = (u16)mgr;
    return mgr_div();
}
static void gfset(void) {
    GP_ST.magic = MAGIC; GP_ST.season = GP_SEAS;
    kset(&GP_ST.ko[0], T0, 4);
    KT2(&GP_ST.ko[0]) = 1; GF(&GP_ST.ko[0]) = GF_WAIT; GP_ST.ko[0].slot = 3;
}
int d_gfplace(u32 mgr) { gfset(); GP_MGR = (u16)mgr; return (int)gf_place_c(); }
int d_gfanchor(u32 mgr) {
    static u8 cal[64] = { 2, 0, 0, 0 };  /* (count 2 at cal - 4, no entries: len 0) */
    gfset(); GP_MGR = (u16)mgr; return (int)gf_anchor_c(cal + 4, 0);
}
int d_clubres(u32 mgr) {
    struct gp_ko k; kset(&k, T0, 4);
    k.nrs = 1; k.ntie = 2; k.gt0[0] = 0; k.gt0[1] = 2;
    k.rs[0][0] = 2; k.rs[0][1] = 1;
    k.ngr = 1; k.gp0[0] = 0; k.gp0[1] = 2;
    k.pa[0] = 0; k.pb[0] = 1; k.pw[0] = 0; k.ptie[0] = 0;
    k.pa[1] = 2; k.pb[1] = 3; k.pw[1] = 2; k.ptie[1] = 1;
    k.tw[0] = 0; k.tl[0] = 1; k.tw[1] = 2; k.tl[1] = 3;
    return club_res(&k, (u16)mgr);
}
int d_sack(u32 mgr) {
    GP_ST.magic = MAGIC; GP_ST.season = GP_SEAS;
    struct gp_ko *k = &GP_ST.ko[0];
    kset(k, T0, 4);
    k->kind = 4; k->ldiv = RESERVE; k->nrs = 1; k->gt0[0] = 0; k->gt0[1] = 2; k->ntie = 2;
    k->tw[0] = 0; k->tl[0] = 1; k->tw[1] = 2; k->tl[1] = 3;   /* (the losers: the 0 word, 0x0365) */
    GP_MGR = (u16)mgr;
    return (int)gp_sack_c();
}
int d_f1(u32 mgr) {                     /* f1_capture on a 2-club table holding a 0 word: kept? */
    static u8 diy[0x400];
    for (unsigned i = 0; i < sizeof diy; i++) diy[i] = 0;
    diy[0x31] = 2; diy[0x12D] = 0; diy[0x12E] = 0; diy[0x12F] = 0x65; diy[0x130] = 0x01;
    diy[0x6D] = 0; diy[0x6F] = 18; diy[0x2B3 + 4] = 1; diy[0x2B3 + 18 + 4] = 1;
    F1_ST.magic = 0;
    f1_capture(diy, 1, mgr);
    return F1_ST.magic == F1_MAGIC;
}
int d_alive(u32 n, u32 h0, u32 h1, u32 h2) {
    static const u16 t[4] = { 0x0165, 0x0265, 0x0365, 0x0465 };
    struct gp_ko k; kset(&k, t, 4);
    k.ntie = 2; k.tw[0] = 0; k.tl[0] = 1; k.tw[1] = NOC; k.tl[1] = NOC;   /* (A beat B; C v D undecided) */
    GP_NHUM = n; GP_HUM[0] = (u16)h0; GP_HUM[1] = (u16)h1; GP_HUM[2] = (u16)h2;
    return (int)hum_alive(&k);
}
'''


def _lib(d, gsrc, tag):
    g = os.path.join(d, f'gplay{tag}.c')
    open(g, 'w').write(gsrc)
    src = os.path.join(d, f'drv{tag}.c')
    open(src, 'w').write(DRIVER.replace('#include "gplay.c"', f'#include "gplay{tag}.c"'))
    lib = os.path.join(d, f'drv{tag}.dylib')
    cmd = ['cc', '-shared', '-fPIC', '-O1', '-w', '-I', TOOLS, '-I', d] + FLAGS + ['-o', lib, src]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:                    # (the glue's tables, defined in asm in the exe: zeroed stubs here)
        und = sorted(set(re.findall(r'"_(\w+)", referenced from', r.stderr)))
        if not und:
            raise RuntimeError(r.stderr[-600:])
        stub = os.path.join(d, f'stub{tag}.c')
        open(stub, 'w').write(''.join(f'unsigned char {n}[65536];\n' for n in und))
        r = subprocess.run(cmd + [stub], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[-600:])
    L = ctypes.CDLL(lib)
    for f in ('d_kidx', 'd_ismgr', 'd_mgrdiv', 'd_gfplace', 'd_gfanchor', 'd_clubres', 'd_sack', 'd_alive', 'd_f1'):
        getattr(L, f).restype = ctypes.c_int
    return L


def _cases(L):
    """[(what, got, want)]"""
    return [
        ('kidx(k, 0) with a 0 word in k', L.d_kidx(0), 0xFF), ('kidx(k, 0x0265)', L.d_kidx(B), 2),
        ('IS_MGR(0), GP_MGR 0', L.d_ismgr(0, 0), 0), ('IS_MGR(A), GP_MGR 0', L.d_ismgr(0, A), 0),
        ('IS_MGR(A), GP_MGR A', L.d_ismgr(A, A), 1), ('IS_MGR(0), GP_MGR A', L.d_ismgr(A, 0), 0),
        ('mgr_div, GP_IN.mgr 0 (a 0 row)', L.d_mgrdiv(0), -1), ('mgr_div, GP_IN.mgr A', L.d_mgrdiv(A), 0),
        ('gf_place_c, GP_MGR 0 (a 0 word in the group)', L.d_gfplace(0), 0),
        ('gf_anchor_c, GP_MGR 0', L.d_gfanchor(0), 0),
        ('club_res(k, 0) (the 0 word lost)', L.d_clubres(0), 0), ('club_res(k, 0x0365) (the last tie lost)', L.d_clubres(C), -100),
        ('gp_sack_c, GP_MGR 0 (the 0 word a play-out loser)', L.d_sack(0), 0),
        ('gp_sack_c, GP_MGR 0x0365 (a play-out loser)', L.d_sack(C), 1),
        ('f1_capture, mgr 0 (a 0 word in the table)', L.d_f1(0), 0), ('f1_capture, mgr 0x0165', L.d_f1(A), 1),
        ('hum_alive, no human club', L.d_alive(0, A, B, C), 0), ('hum_alive {B} (lost)', L.d_alive(1, B, 0, 0), 0),
        ('hum_alive {A}', L.d_alive(1, A, 0, 0), 1), ('hum_alive {A, C}', L.d_alive(2, A, C, 0), 2),
        ('hum_alive {A, B, C}', L.d_alive(3, A, B, C), 2), ('hum_alive {E} (not in it)', L.d_alive(1, E, 0, 0), 0),
    ]


TEST_SW = ('GP_FORCE', 'GP_GFFORCE', 'GP_CDFORCE', 'USC_FORCE', '&& GP_MGR')


def raw_compares(src):
    """gplay.c's lines comparing a word with GP_MGR directly (not via IS_MGR / kidx), outside the test switches"""
    out, ifs = [], []                   # (ifs: the open #if's - one on a test switch (...FORCE) covers its lines)
    for i, ln in enumerate(src.split('\n'), 1):
        code = ln.split('/*')[0]
        pp = code.strip()
        if pp.startswith('#if'):
            ifs.append('FORCE' in pp)
        elif pp.startswith('#endif') and ifs:
            ifs.pop()
        if any(ifs):
            continue
        if re.search(r'[=!]=\s*\(u16\)\s*GP_MGR\b|[=!]=\s*GP_MGR\b|\bGP_MGR\s*[=!]=', code) \
                and '#define IS_MGR' not in code and not any(t in code for t in TEST_SW):
            out.append(f'gplay.c:{i}: {code.strip()}')
    return out


def test_s6a_mgr0():
    errs = []
    gsrc = open(os.path.join(TOOLS, 'gplay.c')).read()
    inc = '#include "gpsc.h"'         # (the shared definitions - IS_MGR among them - expanded in place: the mutations
    assert gsrc.count(inc) == 1         #  and the raw-compare scan see them as gplay.c's own lines)
    gsrc = gsrc.replace(inc, open(os.path.join(TOOLS, 'gpsc.h')).read())
    d = tempfile.mkdtemp(prefix='s6amgr0')
    L = _lib(d, gsrc, '')
    errs += [f'{w}: {g} != {x}' for w, g, x in _cases(L) if g != x]
    errs += [f'raw compare: {r}' for r in raw_compares(gsrc)]
    muts = (('kidx', '    if (!team) return NOC;', '    if (0) return NOC;', 'kidx(k, 0) with a 0 word in k'),
            ('IS_MGR', '#define IS_MGR(w) (GP_MGR && (u16)(w) == (u16)GP_MGR)', '#define IS_MGR(w) ((u16)(w) == (u16)GP_MGR)',
             'IS_MGR(0), GP_MGR 0'),
            ('mgr_div', '    if (!GP_IN.mgr) return -1;\n', '', 'mgr_div, GP_IN.mgr 0 (a 0 row)'),
            ('f1_capture', '    if (!mgr || n < 2 || n > F1N) return;', '    if (n < 2 || n > F1N) return;',
             'f1_capture, mgr 0 (a 0 word in the table)'))
    for name, old, new, case in muts:
        if gsrc.count(old) != 1:
            errs.append(f'mutation {name}: pattern not found once')
            continue
        M = _lib(d, gsrc.replace(old, new), name)
        if all(g == x for w, g, x in _cases(M) if w == case):
            errs.append(f'mutation {name} (no 0 guard): not caught')
    return not errs, '; '.join(errs) or (f'{len(_cases(L))} cases: GP_MGR 0 never matches (kidx, IS_MGR, mgr_div, '
                                         'gf_place / gf_anchor, club_res, gp_sack), hum_alive counts every human club; '
                                         'f1_capture keeps no FASE 1 table; no raw GP_MGR compare outside test switches; 4 mutations caught')
