"""4.2 AFC mode (MC 11/11 option b, check 2): ctdraw's own link after lrank's in obj4's code band, as linked into a
build (obj1..obj4 relocated into Unicorn: test_lrank's Exe) against conti's native ct_place (conti.py _native,
-DNATIVE: the library called directly). The build: HT_CT_BUILD (default HT_LRANK_BUILD / c/S1R/SWOS; a build with
conti, lrank and HOSTTEST_SYMS=1; none: SKIP as a PASS).

- conti.c's CT_SDRAW (obj1 .data) holds ct_place's obj4 offset (the cross-band pointer, relocated);
- ct_place in the build (its calls into the engine's swe_ready / cstack_call: the run on the engine's C stack)
  = the native one, slots and rng, on random shapes of every mode: the 411 draw (1 and 16 tries), ED_S with each rule
  (A_ANY, A_NO, A_NOVIA, A_NO2, A_MIN), the holder, per region (as[] bit 7, 0x40) - ACL Two's 8 x 4 among them;
- CT_SDRAW_N / CT_SDRAW_HIT / CT_SDRAW_ERR count as the native ones."""
import ctypes
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('HT_LRANK_BUILD', os.environ.get('HT_CT_BUILD') or os.path.join(os.path.expanduser('~'),
                                                                                       'swos-mod', 'c', 'S1R', 'SWOS'))
import test_lrank as tl                                 # noqa: E402

N = int(os.environ.get('HT_CT_SHAPES') or 600)


def shape(rnd, k):
    """(m, ng, gs, mode, as[]) - k picks the mode family"""
    ng, gs = rnd.choice(((8, 4), (8, 4), (4, 4), (6, 4), (2, 4), (5, 4), (4, 3)))
    rule = k % 5
    ed_s = k % 7 != 0
    pr = ed_s and ng % 2 == 0 and k % 3 == 0
    m = ng * gs - (rnd.random() < 0.15)
    while True:
        na = rnd.randint(3, 14)                     # (redrawn too: few associations may admit no valid draw)
        w = [rnd.random() ** 2 + 0.05 for _ in range(na)]
        a = [rnd.choices(range(na), w)[0] for _ in range(m)]
        cap = {1: 1, 2: 1, 3: 2}.get(rule)          # (a valid draw exists: per association at most cap * groups)
        per = ng // 2 if pr else ng
        reg = [rnd.random() < 0.5 for _ in range(na)] if pr else [0] * na
        if pr:                                      # (each half its share of the places)
            nw = sum(1 for x in a if not reg[x])
            if not (m - ng * gs // 2 <= nw <= ng * gs // 2):
                continue
        if cap is None or all(sum(1 for x in a if x == q) <= cap * per for q in range(na)):
            break
    asb = bytes((x | (0x80 if reg[x] else 0)) for x in a)
    hold = k % 4 == 1
    mode = rule | hold << 4 | (0x20 if ed_s else 0) | (0x40 if pr else 0) | (16 if k % 2 else 1) << 8
    return m, ng, gs, mode, asb


def test_ctplace_differential():
    if not os.path.exists(os.path.join(tl.BUILD, 'ITALIAN.syms.json')):
        return True, f'SKIP: no build at {tl.BUILD}'
    import json
    sys.path.insert(0, tl.TOOLS)
    import conti
    x = tl.Exe()
    allsyms = json.load(open(os.path.join(tl.BUILD, 'ITALIAN.syms.json')))
    cs = allsyms['conti'].get('syms.CT_SDRAW') or allsyms['conti'].get('SYMS.CT_SDRAW')
    ptr = struct.unpack('<I', x.rd(x.base[cs[0]] + cs[1], 4))[0]
    bad = []
    if ptr != x.lin('ct_place'):
        bad.append(f'CT_SDRAW {ptr:#x} != ct_place {x.lin("ct_place"):#x}')
    L = conti._native()
    L.ct_place.restype = ctypes.c_int
    rnd = random.Random(2627)
    buf = x.stack - 0x8000                              # (the arguments' arrays, below the stack)
    same = drawn = 0
    for k in range(N):
        m, ng, gs, mode, asb = shape(rnd, k)
        xs = [0x100 + i for i in range(m)]
        v = bytes(1 if (mode & 15) == 2 and rnd.random() < 0.3 else 0 for _ in range(m))
        kk = bytes(rnd.randrange(256) for _ in range(m))
        seed = rnd.getrandbits(32)
        # native
        nx = (ctypes.c_uint16 * 64)(*xs); nv = (ctypes.c_uint8 * 64)(*v); nk = (ctypes.c_uint8 * 64)(*kk)
        na = (ctypes.c_uint8 * 64)(*asb); nr = ctypes.c_uint32(seed)
        rc_n = L.ct_place(m, ng, gs, mode, nx, nv, nk, na, ctypes.byref(nr), k)
        # the build
        ax, av, ak, aa, ar = buf, buf + 0x100, buf + 0x200, buf + 0x300, buf + 0x400
        x.wr(ax, struct.pack('<64H', *(xs + [0] * (64 - m))))
        x.wr(av, v.ljust(64, b'\0')); x.wr(ak, kk.ljust(64, b'\0')); x.wr(aa, asb.ljust(64, b'\0'))
        x.wr(ar, struct.pack('<I', seed))
        rc_e = cdecl(x, x.lin('ct_place'), m, ng, gs, mode, ax, av, ak, aa, ar, k)
        ex = list(struct.unpack('<64H', x.rd(ax, 128)))
        er = struct.unpack('<I', x.rd(ar, 4))[0]
        ok = rc_e == rc_n and er == nr.value and (rc_n < 0 or (ex[:ng * gs] == list(nx)[:ng * gs]
                                                               and x.rd(av, ng * gs) == bytes(nv)[:ng * gs]
                                                               and x.rd(ak, ng * gs) == bytes(nk)[:ng * gs]))
        same += ok
        drawn += rc_n >= 0 and bool(mode & 0x20)
        if not ok and len(bad) < 5:
            bad.append(f'shape {k} (m {m}, {ng}x{gs}, mode {mode:#x}): rc {rc_e}/{rc_n}, rng {er:#x}/{nr.value:#x}')
    cnt = {n: (struct.unpack('<I', x.rd(x.lin(n), 4))[0], ctypes.c_uint32.in_dll(L, n).value)
           for n in ('CT_SDRAW_N', 'CT_SDRAW_HIT')}
    if cnt['CT_SDRAW_N'][0] != cnt['CT_SDRAW_N'][1] or cnt['CT_SDRAW_N'][0] == 0:
        bad.append(f'CT_SDRAW_N build/native {cnt["CT_SDRAW_N"]}')
    if cnt['CT_SDRAW_HIT'][0] != cnt['CT_SDRAW_HIT'][1]:
        bad.append(f'CT_SDRAW_HIT build/native {cnt["CT_SDRAW_HIT"]}')
    return not bad and same == N, '; '.join(bad) or (f'{same}/{N} shapes the same (ED_S draws {drawn}; CT_SDRAW '
                                                     f'{x.lin("ct_place") - x.base[4]:#x} relocated; counters '
                                                     f'N {cnt["CT_SDRAW_N"][0]}, HIT {cnt["CT_SDRAW_HIT"][0]})')


def cdecl(x, at, *args):
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    sp = x.stack - 256
    x.wr(sp, struct.pack(f'<I{len(args)}I', x.sent, *[a & 0xFFFFFFFF for a in args]))
    x.uc.reg_write(UC_X86_REG_ESP, sp)
    x.uc.emu_start(at, x.sent, timeout=30_000_000)     # (30 s: no per-instruction count, JIT speed)
    r = x.uc.reg_read(UC_X86_REG_EAX)
    return r - (1 << 32) if r & 0x80000000 else r
