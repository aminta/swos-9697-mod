"""CD_DT over a split file (S7-G, MC 11/11): gplay.c's Coppa D readers with GP_CD2 (built natively) and cupd.head.
- dormant: gplay.c without GP_CD2 compiles to the same object as before the change (cobj, the exe's flags) - the
  readers' macros expand to today's tokens; cupd.head = today's 4 bytes;
- GP_CD2: file 144 rows 0 / 155 (run 1: 192 / 347) and 156 / 161 (run 2: 2283 / 2288) read GP_SLT at their real
  globals (cd_member_c), the aliases 348 / 353 are never read; a one-run CD_DT (FFFFh / 256) as today;
- mutation: CD_G without run 2 (caught);
- the S7 pack: cupd.head(pk, 144) = (5, 9, 192, 2283, 156) in a cd2 build."""
import ctypes
import os
import re
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FLAGS = ['-DGP_S7=0', '-DSS_NB=1', '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0']
CD2_COMMIT = os.environ.get('CD_DT_COMMIT', 'bd8e5bc')   # (the commit that brought GP_CD2 into gplay.c: the dormant
                                                           # reference = TODAY's gplay.c with its hunks reversed - MC
                                                           # 13/11: no fixed sha, valid while gplay.c evolves)


def _lib(d, src_text, cd2, tag=''):
    src = os.path.join(d, f'g{cd2}{tag}.c')     # (a new name per library: dlopen keeps one image per path)
    open(src, 'w').write(src_text)
    lib = os.path.join(d, f'g{cd2}{tag}.dylib')
    cmd = ['cc', '-shared', '-fPIC', '-O1', '-w', '-I', TOOLS] + FLAGS + [f'-DGP_CD2={cd2}', '-o', lib, src]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:                    # (the glue's tables, defined in asm in the exe: zeroed stubs here)
        und = sorted(set(re.findall(r'"_(\w+)", referenced from', r.stderr)))
        if not und:
            raise RuntimeError(r.stderr[-400:])
        stub = os.path.join(d, f'stub{cd2}{tag}.c')
        open(stub, 'w').write(''.join(f'unsigned char {n}[65536];\n' for n in und))
        r = subprocess.run(cmd + [stub], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[-400:])
    return ctypes.CDLL(lib)


def _member(L, dt, slt, team):
    cdt = ctypes.create_string_buffer(bytes((5, 7, 144)) + bytes(13), 16)    # (CD_TAB: [2] = the Serie D file)
    cdd = ctypes.create_string_buffer(dt, len(dt))
    sl = ctypes.create_string_buffer(slt, len(slt))
    for name, buf in (('GP_CDT', cdt), ('GP_CDD', cdd), ('GP_SLT', sl)):
        ctypes.c_void_p.in_dll(L, name).value = ctypes.addressof(buf)
    L.cd_member_c.argtypes, L.cd_member_c.restype = [ctypes.c_uint32], ctypes.c_uint32
    return L.cd_member_c(144 | team << 8)


def test_cd_dt():
    import cobj
    errs = []
    gsrc = open(os.path.join(TOOLS, 'gplay.c')).read()
    diff = subprocess.run(['git', '-C', TOOLS, 'show', '--format=', CD2_COMMIT, '--', ':(top)tools/gplay.c'],
                          capture_output=True, text=True).stdout
    d = tempfile.mkdtemp(prefix='cddt')
    os.makedirs(os.path.join(d, 'tools'))
    p = os.path.join(d, 'tools', 'gplay.c')
    open(p, 'w').write(gsrc)
    todo, seen = [gsrc], set()                          # (gplay.c's own #include "..." files, recursive: linked next to the
    while todo:                                         #  copy - Integratore 15/11: gplx.c, 42-gplx; cupview.h, cuprule.c)
        for f in re.findall(r'^\s*#\s*include\s+"([^"]+)"', todo.pop(), re.M):
            src = os.path.join(TOOLS, f)
            if f not in seen and os.path.exists(src) and not os.path.exists(os.path.join(d, 'tools', f)):
                seen.add(f)
                os.makedirs(os.path.dirname(os.path.join(d, 'tools', f)), exist_ok=True)
                os.symlink(src, os.path.join(d, 'tools', f))
                todo.append(open(src).read())
    r = subprocess.run(['patch', '-R', '-s', '-p1', '-d', d], input=diff, capture_output=True, text=True) \
        if 'GP_CD2' in diff else None
    skip = None
    if r is None or r.returncode:
        skip = (f'dormant check SKIPPED: {CD2_COMMIT}\'s gplay.c hunks no longer reverse onto today\'s file '
                '(the release md5 gate covers the dormant bytes)')
    elif 'CD_G(' in open(p).read() or 'cd_member_c' not in open(p).read():
        errs.append(f'the reversed reference still has GP_CD2 code ({CD2_COMMIT})')
    elif cobj.compile_c(p, FLAGS) != cobj.compile_c(os.path.join(TOOLS, 'gplay.c'), FLAGS):
        errs.append('dormant gplay.c object changed')
    d = tempfile.mkdtemp(prefix='cddt')
    L = _lib(d, gsrc, 1)
    base = bytes([5 + i // 18 for i in range(162)] + [0xFF] * 94)       # (9 groups: divisions 5..13)
    dt2 = bytes((5, 9)) + struct.pack('<HHH', 192, 2283, 156) + base
    dt1 = bytes((5, 9)) + struct.pack('<HHH', 192, 0xFFFF, 256) + base
    slt = bytearray(2400)
    # a club's division = base + slt[global]: 0 keeps it in Serie D; -100 (0x9C) takes it out of the groups
    for g in (348, 353):
        slt[g] = 0x9C                                                   # (the aliases: another file's, never read)
    cases = []
    for row, g in ((0, 192), (155, 347), (156, 2283), (161, 2288)):
        for v, want in ((0, 1), (0x9C, 0)):
            s = bytearray(slt)
            s[g] = v
            cases.append((dt2, row, bytes(s), want, f'row {row} (global {g}) slt {v:#x}'))
    s = bytearray(slt)
    s[192 + 156] = 0x9C                                                 # (one run: row 156 at 348, as today)
    cases += [(dt1, 156, bytes(s), 0, 'one-run CD_DT: row 156 at 348'), (dt1, 155, bytes(s), 1, 'one-run row 155')]
    for dt, row, s, want, what in cases:
        got = _member(L, dt, s, row)
        if got != want:
            errs.append(f'{what}: {got} != {want}')
    mut = gsrc.replace('#define CD_G(dt, gb, i) ((i) >= ((dt)[6] | (dt)[7] << 8) ? ((dt)[4] | (dt)[5] << 8) + (i) - '
                       '((dt)[6] | (dt)[7] << 8) \\\n                         : (gb) + (i))', '#define CD_G(dt, gb, i) ((gb) + (i))')
    if mut == gsrc:
        errs.append('mutation: CD_G not found')
    else:
        M = _lib(d, mut, 1, 'mut')
        s = bytearray(slt)
        if all(_member(M, dt2, bytes(s), r) == 1 for r in (156, 161)):
            errs.append('mutation (no run 2): not caught')
    # cupd.head
    import cupd
    if not hasattr(cupd, 'head'):
        errs.append('cupd.head missing')
    import test_s7pack
    if os.path.isdir(test_s7pack.SRC) and os.path.isfile(test_s7pack.GROUPS):
        import test_globnum
        prev = os.environ.get('SEASON_PACKS')
        test_globnum._env()
        tmp = tempfile.mkdtemp(prefix='cddt')
        try:
            import mkseason
            import s7pack
            one = next(pk for pk in mkseason.packs() if pk.world == 5 and pk.files.get('league', (0,))[0] == 102)
            h1 = cupd.head(one, 102, 5, 9)
            if h1 != bytes((5, 9)) + struct.pack('<H', 92):
                errs.append(f'dormant head {h1.hex()}')
            s7pack.build(test_s7pack.SRC, test_s7pack.GROUPS, os.path.join(tmp, 'ita'))
            pk = mkseason.Pack(os.path.join(tmp, 'ita'))
            real = cupd.cd2
            cupd.cd2 = lambda: True             # (a shaped build: the S7 pack among SEASON_PACKS)
            try:
                h2, h0 = cupd.head(pk, 144, 5, 9), cupd.head(pk, 102, 0, 1)
            finally:
                cupd.cd2 = real
            if h2 != bytes((5, 9)) + struct.pack('<HHH', 192, 2283, 156):
                errs.append(f'S7 head 144 {h2.hex()}')
            if h0 != bytes((0, 1)) + struct.pack('<HHH', 92, 0xFFFF, 256):
                errs.append(f'S7 head 102 (one run in a cd2 build) {h0.hex()}')
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            if prev is None:
                os.environ.pop('SEASON_PACKS', None)
            else:
                os.environ['SEASON_PACKS'] = prev
    return not errs, '; '.join(errs) or ('dormant gplay.c object and CD_DT head as today; GP_CD2: rows 0 / 155 / 156 / '
                                         '161 read slt at 192 / 347 / 2283 / 2288 (348 / 353 never), one-run CD_DT '
                                         'as today; mutation (no run 2) caught; S7 head 144 = 192 + (2283, 156)'
                                         + (f'; {skip}' if skip else f' (reference: today\'s gplay.c - {CD2_COMMIT})'))
