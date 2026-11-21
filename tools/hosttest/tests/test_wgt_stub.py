"""4.2.x harness fix (MC 21/11, lp36_tie / lp36_tourney rc1 FAILs): since S6a (908a12b) the W sites `call W_GT`, a
GLOBAL only careerworld.patch defines, so a build without a career world (lp36's packs) could not assemble. nasmcave
(NO_WORLD, set by patch.py) turns an undefined W_GT's calls into WGT_STUB = `cmp word [GAMETYPE], 4`, the pre-S6a site.
- w_gt's own body (careerworld.py, run in Unicorn) and the stub give the same ZF and leave every register as it was, for
  gameType 0..5 with world byte 0 (a no-world build never sets it); with a world byte the two differ (gameType 3: the
  world SEASON), which is why the stub only exists in no-world builds;
- nasmcave: the stub assembles to the cmp; a world build (NO_WORLD False) without W_GT still errors; a defined W_GT wins;
- every `call W_GT` site of tools/ was a `cmp word [GAMETYPE], 4` before 908a12b (no site with other semantics)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixroot  # noqa: E402,F401
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, TOOLS)
import nasmcave  # noqa: E402

GT, SLT, WB = 0x20000, 0x20100, 1845
CODE, RET, STK = 0x10000, 0x18000, 0x40000
REGS = ('EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP', 'ESP')


def _wgt_body():
    s = open(os.path.join(TOOLS, 'careerworld.py')).read()
    body = s[s.index('\nw_gt:') + 1:s.index('\nw_holders:')]
    return '\n'.join(ln.split(';')[0].rstrip() for ln in body.splitlines())


def _asm(src):
    return nasmcave._nasm(src, CODE, {'GAMETYPE': (0, GT), 'SLT': (0, SLT), 'WORLD_BYTE': (0, WB)}, {1: 0})


def _run(code, gt, wb):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn import x86_const as X
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    for a in (CODE & ~0xFFFF, GT & ~0xFFFF, STK - 0x10000):
        uc.mem_map(a, 0x10000)
    uc.mem_write(CODE, code)
    uc.mem_write(RET, b'\xf4')
    uc.mem_write(GT, gt.to_bytes(2, 'little'))
    uc.mem_write(SLT + WB, bytes([wb]))
    vals = {r: 0x11111111 * (i + 1) for i, r in enumerate(REGS[:-1])}
    for r, v in vals.items():
        uc.reg_write(getattr(X, 'UC_X86_REG_' + r), v)
    uc.reg_write(X.UC_X86_REG_ESP, STK - 0x100)
    uc.mem_write(STK - 0x100, RET.to_bytes(4, 'little'))
    uc.emu_start(CODE, RET, count=100)
    out = {r: uc.reg_read(getattr(X, 'UC_X86_REG_' + r)) for r in REGS}
    return (uc.reg_read(X.UC_X86_REG_EFLAGS) >> 6) & 1, out


def test_wgt_stub_is_world0_wgt():
    try:
        import unicorn  # noqa: F401
    except ImportError:
        return True, 'SKIP: unicorn missing (run with the hosttest venv)'
    real = _asm('call w_gt\nret\n' + _wgt_body())
    stub = _asm(nasmcave.WGT_STUB + '\nret\n')
    bad, differ = [], []
    for gt in range(6):
        for wb in (0, 1, 7):
            zr, rr = _run(real, gt, wb)
            zs, rs = _run(stub, gt, wb)
            if wb == 0 and (zr != zs or rr != rs or zs != (gt == 4)):
                bad.append((gt, wb, zr, zs, {k: (hex(rr[k]), hex(rs[k])) for k in rr if rr[k] != rs[k]}))
            if wb and zr != zs:
                differ.append((gt, wb))
    assert not bad, f'w_gt v stub at world byte 0 (gameType, wb, ZF real, ZF stub, regs): {bad}'
    assert differ == [(3, 1), (3, 7)], f'red: with a world byte only the world SEASON (gameType 3) differs: {differ}'
    return True, 'w_gt == stub (ZF, 8 registers) for gameType 0..5 at world byte 0; differ only gameType 3 + world byte'


def test_wgt_nasmcave():
    src = 'call W_GT\njne x\nx: ret\n'
    sy = {'GAMETYPE': (0, GT)}
    old = nasmcave.NO_WORLD[0], dict(nasmcave.GLOBAL)
    try:
        nasmcave.GLOBAL.pop('W_GT', None)
        nasmcave.NO_WORLD[0] = True
        got = nasmcave._nasm(src, 0, sy, {1: 0x1000})
        want = nasmcave._nasm(nasmcave.WGT_STUB + '\njne x\nx: ret\n', 0, sy, {1: 0x1000})
        assert got == want and got[:2] == b'\x66\x83', got.hex()
        nasmcave.NO_WORLD[0] = False
        try:
            nasmcave._nasm(src, 0, sy, {1: 0x1000})
            raise AssertionError('a world build without W_GT assembled (must error)')
        except RuntimeError as e:
            assert 'W_GT' in str(e), str(e)
        nasmcave.GLOBAL['W_GT'] = (1, 0x40)
        nasmcave.NO_WORLD[0] = True
        got = nasmcave._nasm(src, 0, sy, {1: 0x1000})
        assert got[0] == 0xE8, got.hex()
    finally:
        nasmcave.NO_WORLD[0] = old[0]
        nasmcave.GLOBAL.clear()
        nasmcave.GLOBAL.update(old[1])
    return True, 'stub = cmp; world build without W_GT errors; defined W_GT wins'


def test_wgt_sites_were_cmp4():
    import subprocess
    root = os.path.abspath(os.path.join(TOOLS, '..'))
    d = subprocess.run(['git', '-C', root, 'show', '908a12b', '--', 'tools/'], capture_output=True, text=True)
    if d.returncode:
        return True, 'SKIP: 908a12b not in this checkout'
    minus = len(re.findall(r'^-\s+.*cmp word \[GAMETYPE\], 4', d.stdout, re.M))
    plus = len(re.findall(r'^\+\s+call W_GT\b', d.stdout, re.M | re.I)) + len(re.findall(r"^\+.*sub\(src, 'WORLD_BYTE", d.stdout, re.M))
    kept = len(re.findall(r'^\+\s+cmp word \[GAMETYPE\], 4', d.stdout, re.M)) - 1   # (minus w_gt's own first cmp;
    assert minus == plus + kept, (minus, plus, kept)                                   #  careerworld: call w_gt)
    return True, f'908a12b: {minus} cmp GAMETYPE,4 sites -> {plus} W_GT calls + {kept} kept'
