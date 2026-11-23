"""4.2 rc6 (Davide 23/11): a drawn preseason friendly showed 'PASSA X (MIGL. PIAZZ.)' - gp_draw_c (a level tie of ours with no
penalties) gave the better placed club's flag to K_FR as to a cup tie. gplay.c built natively (as test_cd_dt) with GP_PORT=1
GP_FRND=1, gp_draw_c over every contest kind x decider / type-2 / which club is better placed:
  - K_FR -> 10h (the draw stands, no 'better placed' line), whatever the rest;
  - K_PORT unchanged (10h with no decider, else the better placed), every other kind unchanged = the base gplay.c's answer;
red twin: the base gplay.c (git 14b23dc, before the fix) gives K_FR the better-placed answer (the bug)."""
import ctypes
import os
import re
import subprocess
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
FLAGS = ['-DGP_S7=0', '-DSS_NB=1', '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0',
         '-DGP_PORT=1', '-DGP_FRND=1', '-DGP_DATA_SECTION=']
BASE = '14b23dc'
DRIVER = r'''
#include <string.h>
u32 t_draw(u32 kind, u32 dec, u32 t2, u32 bbetter) {
    struct gp_ko *k = &GP_ST.ko[0];
    memset(k, 0, sizeof *k);
    k->kind = kind; k->rs[0][3] = dec; k->bye[7] = t2; k->n = 2;
    k->team[0] = 0x1065; k->team[1] = 0x2065; k->prio[0] = bbetter ? 2 : 1; k->prio[1] = bbetter ? 1 : 2;
    GP_K = 0; GP_A = 0x1065; GP_B = 0x2065;
    return gp_draw_c();
}
u32 t_kfr(void) { return K_FR; }
u32 t_kport(void) { return K_PORT; }
'''


def _lib(d, gplay_text, tag):
    src = os.path.join(d, f'g{tag}.c')
    gplay_text = gplay_text.replace('__attribute__((section(".data")))', '')   # (GP_PORT's hook dwords: an ELF section
    open(os.path.join(d, f'gplay_{tag}.c'), 'w').write(gplay_text)                  #  name, not Mach-O - the same in both twins)
    open(src, 'w').write(f'#include <stdint.h>\n#include "gplay_{tag}.c"\n' + DRIVER)
    lib = os.path.join(d, f'g{tag}.dylib')
    cmd = ['cc', '-shared', '-fPIC', '-O1', '-w', '-I', TOOLS, '-I', d] + FLAGS + ['-o', lib, src]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:                    # (the glue's tables, defined in asm in the exe: zeroed stubs here)
        und = sorted(set(re.findall(r'"_(\w+)", referenced from', r.stderr)))
        if not und:
            raise RuntimeError(r.stderr[-400:])
        stub = os.path.join(d, f'stub{tag}.c')
        open(stub, 'w').write(''.join(f'unsigned char {n}[65536];\n' for n in und))
        r = subprocess.run(cmd + [stub], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[-400:])
    L = ctypes.CDLL(lib)
    L.t_draw.argtypes, L.t_draw.restype = [ctypes.c_uint32] * 4, ctypes.c_uint32
    return L


def _table(L):
    return {(kind, dec, t2, bb): L.t_draw(kind, dec, t2, bb) for kind in range(32) for dec in (0, 1, 2) for t2 in (0, 1)
            for bb in (0, 1)}


def test_frdraw():
    base = subprocess.run(['git', '-C', TOOLS, 'show', f'{BASE}:tools/gplay.c'], capture_output=True, text=True)
    if base.returncode:
        return None, f'git show {BASE}: {base.stderr[-200:]}'
    with tempfile.TemporaryDirectory() as d:
        new = _lib(d, open(os.path.join(TOOLS, 'gplay.c')).read(), 'new')
        old = _lib(d, base.stdout, 'old')
        twin = _lib(d, '#define GP_FRDRAW_TWIN 1\n' + open(os.path.join(TOOLS, 'gplay.c')).read(), 'twin')
        ttw = _table(twin)
        kfr, kport = new.t_kfr(), new.t_kport()
        tn, to = _table(new), _table(old)
    bad = []
    fr = {k: v for k, v in tn.items() if k[0] == kfr and not k[2]}
    if set(fr.values()) != {0x10}:
        bad.append(f'K_FR not 10h: {sorted(set(fr.values()))}')
    if tn[(kfr, 0, 1, 1)] != 0xFFFFFFFF:
        bad.append('K_FR type-2 should keep the game rules (the KT2 check first)')
    other = [k for k in tn if k[0] != kfr and tn[k] != to[k]]
    if other:
        bad.append(f'other kinds changed: {other[:6]}')
    port = {(dec, bb): tn[(kport, dec, 0, bb)] for dec in (0, 1) for bb in (0, 1)}
    if port != {(0, 0): 0x10, (0, 1): 0x10, (1, 0): 0, (1, 1): 1}:
        bad.append(f'K_PORT: {port}')
    # red twin: the base gives K_FR the better placed club's answer (0 / 1: the 'PASSA X (MIGL. PIAZZ.)' line)
    red = {to[(kfr, dec, 0, bb)] for dec in (0, 1, 2) for bb in (0, 1)}
    if red != {0, 1}:
        bad.append(f'red: base K_FR answers {sorted(red)}, want the bug (0 / 1)')
    if ttw != to:
        bad.append('FRDRAW_TWIN build differs from the base (the scenario\'s red twin must be the bug)')
    if bad:
        return False, '; '.join(bad)
    return True, (f'K_FR ({kfr}) -> 10h in {len(fr)} cases, type-2 -> game rules; K_PORT ({kport}) {port}; the other '
                  f'{len(tn) - len(fr)} cases (K_FR type-2 included) = base {BASE}; red: base K_FR = better placed (0 / 1), the FRDRAW_TWIN build = base')
