"""cf_last1 (gplay.c, gp_wn_c 'E': the WINNERS page's last-season fallback line, MC 15/11): the 1st of the career
club's OWN division last season, never another group's. gplay.c built natively (as test_cd_dt), GP_S7=0 (the non-S7
builds: before the fix the only path there).
Shape: file 102, CF_TAB with one dt: divisions 0 (level 0), 1 (level 1: one group), 2 / 3 (level 2: groups A / B).
cf_cap_c's final tables: A = ordinals 3, 4, 5 (1st: 3), B = 20, 21, 22 (1st: 21, the career club 22), division 1 =
30, 31 (1st: 30).
- repro (the reference gplay.c, REF_COMMIT's): the career club in B gets A's 1st (102 | 3 << 8) - the lowest ordinal
  of the level's 1sts;
- fixed: B's 1st (cf_cap_c's 'W' word in every build); career club in division 1: 30;
- an old save (CN pad[2] != 'W'; CF_ST as captured): a level of two groups -> 0xFFFE (unknown: the page's last-season
  branch skips the line, winners.py .lst 'jae .skip'), a level of one group -> its 1st;
- not last season's data (CN / CF season + 1 != GP_SEAS) or the career club on another file -> 0xFFFE."""
import ctypes
import os
import re
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
FLAGS = ['-DGP_S7=0', '-DSS_NB=1', '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0']
REF_COMMIT = os.environ.get('CFLAST1_REF', 'c92ace9')     # (42-int before the fix: the repro's gplay.c)
F = 102
UNK = 0xFFFE


def _lib(d, src_text, tag):
    src = os.path.join(d, f'g{tag}.c')
    open(src, 'w').write(src_text)
    lib = os.path.join(d, f'g{tag}.dylib')
    cmd = ['cc', '-shared', '-fPIC', '-O1', '-w', '-I', TOOLS] + FLAGS + ['-o', lib, src]
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
    return ctypes.CDLL(lib)


def _cftab():
    levels = [0, 1, 2, 2] + [7] * 12
    pairs = [(o, 2) for o in (3, 4, 5)] + [(o, 3) for o in (20, 21, 22)] + [(o, 1) for o in (30, 31)]
    t = bytes((1, 0, 0, 1)) + struct.pack('<HBH', 0, F, len(pairs)) + bytes(levels)
    return t + b''.join(bytes(p) for p in pairs)


def _diy(name, ords):                   # (DIY: +4 name, +31h clubs, +6Dh places' row offsets, +12Dh rows' team words)
    b = bytearray(0x200)
    b[4:4 + len(name)] = name
    struct.pack_into('<H', b, 0x31, len(ords))
    for k, o in enumerate(ords):        # (row k = place k)
        struct.pack_into('<H', b, 0x6D + 2 * k, 0x12 * k)
        struct.pack_into('<H', b, 0x12D + 2 * k, F | o << 8)
    return bytes(b)


def _run(L, keep, mgr, season=5, seas=None, old=False, file_mgr=F):
    """caps the season's tables with the career club mgr, then gp_wn_c 'E' at GP_SEAS (season + 1)."""
    for n in ('CF_ST', 'CN_ST'):
        ctypes.memset(ctypes.addressof(ctypes.c_uint8.in_dll(L, n)), 0, 64 if n == 'CN_ST' else 260)
    ctypes.c_void_p.in_dll(L, 'CF_TAB').value = ctypes.addressof(keep['tab'])
    ctypes.c_void_p.in_dll(L, 'GP_SLT').value = ctypes.addressof(keep['slt'])
    ctypes.c_uint16.in_dll(L, 'GP_MGR').value = F | mgr << 8
    for dv, nm, ords in ((1, b'SERIE B', (30, 31)), (2, b'GIRONE A', (3, 4, 5)), (3, b'GIRONE B', (21, 20, 22))):
        L.cf_cap_c(dv, keep[dv], season)
    if old:                             # (a save from before 'W': CN's pad as never written)
        cn = ctypes.addressof(ctypes.c_uint8.in_dll(L, 'CN_ST'))
        ctypes.memset(cn + 1, 0, 3)
    ctypes.c_uint16.in_dll(L, 'GP_MGR').value = file_mgr | mgr << 8
    ctypes.c_uint8.in_dll(L, 'GP_SEAS').value = (season + 1 if seas is None else seas) & 0xFF
    ctypes.c_uint32.in_dll(L, 'GP_WNSRC').value = 0x01000045      # ('E', the last season)
    return L.gp_wn_c() & 0xFFFF


def test_cflast1():
    d = tempfile.mkdtemp(prefix='cfl1')
    L = _lib(d, open(os.path.join(TOOLS, 'gplay.c')).read(), 'new')
    for L_ in (L,):
        L_.gp_wn_c.restype = ctypes.c_uint32
        L_.cf_cap_c.argtypes = (ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32)
    keep = {'tab': ctypes.create_string_buffer(_cftab(), 64), 'slt': ctypes.create_string_buffer(4096)}
    keep.update({1: _diy(b'SERIE B', (30, 31)), 2: _diy(b'GIRONE A', (3, 4, 5)), 3: _diy(b'GIRONE B', (21, 20, 22))})
    errs, notes = [], []
    w = lambda o: F | o << 8            # noqa: E731
    ref = subprocess.run(['git', '-C', TOOLS, 'show', f'{REF_COMMIT}:tools/gplay.c'], capture_output=True, text=True)
    if ref.returncode:
        notes.append(f'repro SKIPPED ({REF_COMMIT} not in this repo)')
    else:
        R = _lib(d, ref.stdout, 'ref')
        R.gp_wn_c.restype = ctypes.c_uint32
        R.cf_cap_c.argtypes = (ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32)
        got = _run(R, keep, 22)
        if got != w(3):
            errs.append(f'repro: {REF_COMMIT} gave {got:#06x}, expected the wrong 1st {w(3):#06x} (A\'s) - '
                        f'the bug is not reproduced')
        else:
            notes.append(f'repro: {REF_COMMIT} gives group A\'s 1st (ordinal 3) to a group B career club')
    for name, kw, want in (('B club', dict(mgr=22), w(21)),
                           ('B club (its 1st itself)', dict(mgr=21), w(21)),
                           ('A club', dict(mgr=5), w(3)),
                           ('level of one group', dict(mgr=31), w(30)),
                           ('old save, 2 groups', dict(mgr=22, old=True), UNK),
                           ('old save, 2 groups (A)', dict(mgr=4, old=True), UNK),
                           ('old save, 1 group', dict(mgr=31, old=True), w(30)),
                           ('not last season', dict(mgr=22, seas=9), UNK),
                           ('old save, not last season', dict(mgr=31, old=True, seas=9), UNK),
                           ('old save, career on another file', dict(mgr=22, old=True, file_mgr=103), UNK)):
        got = _run(L, keep, **kw)
        if got != want:
            errs.append(f'{name}: {got:#06x} (want {want:#06x})')
    # the one display of 0xFFFE (MC 15/11): 'E' lines exist on the last-season page only (winners.py .ls -> .lle), and
    # GP_CALL's last-season branch skips any result >= 0FFFEh before a team lookup (no table indexed, no name printed)
    import winners
    src = open(winners.__file__).read()
    lst = winners.GP_CALL[winners.GP_CALL.index('.lst:'):]
    if not re.match(r'\.lst:[^\n]*\n\s+cmp ax, 0FFFEh[^\n]*\n\s+jae \.skip', lst):
        errs.append('winners.py GP_CALL .lst: no "cmp ax, 0FFFEh / jae .skip" before the team lookup')
    if src.count("mov bl, 'E'") != 1 or not re.search(r"cmp al, 'E'[^\n]*\n\s+je \.lle", src):
        errs.append("winners.py: 'E' reached other than through the last-season parser (.ls -> .lle)")
    return not errs, '; '.join(errs[:6]) or (
        '; '.join(notes) + '; fixed: B club -> B\'s 1st (21), A club -> 3, one-group level -> 30 (the \'W\' word in '
        'every build); old save (no \'W\'): 2 groups -> 0xFFFE (the page skips the line), 1 group -> its 1st; not last '
        'season / another file -> 0xFFFE')
