"""Engine step W: the world registry (swreg.py) and its loader (swe.c reg_enter / reg_leave, swe_sel_tramp), on the
exe's static image - no snapshot. obj1, obj2 and obj4 of HT_REG_EXE (else c/HTW/SWOS/ITALIAN.EXE, a release-recipe
exe: worlds 4 and 5, two namespaces) relocated in a bare Unicorn machine, at the boot state (careerworld WCUR = the
base world).

- the manifest: header, worlds 0 / 4 / 5, stems, menu ids, every list pointer inside obj4 and its lists in range;
- reg_enter(5): countriesTable / competitionsTable / teamsCountryNumbers hold world 5's rows (careerworld NSWT, read
  from the image) for every namespace number, WCUR = 5; a second reg_enter is refused (-2), an unknown world (-1);
- reg_leave(): obj1 and obj2 are byte for byte the boot image again (and reg_enter(0) at boot swaps nothing);
- the picker: GoGetTeamsForPlay's call reaches swe_sel_tramp, which calls the previous target (stubbed by a `ret`
  here) with SEL_MODE = M_FRIENDLY, then leaves competitionsTable[254] and every other byte as they were."""
import os
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'hosttest'))
import swe  # noqa: E402
import swreg  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_REG_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTW', 'SWOS', 'ITALIAN.EXE')
ORIG = os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE')
B1, B2, B4 = 0x1000000, 0x2000000, 0x3000000
STACK, RET = 0x5000000, 0x4FF0000


class _P:                                       # (countries.tables reads p.le: the original exe's tables)
    def __init__(self, le):
        self.le = le


def _machine():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    import emu
    from le import LE
    i1, i2, le = emu.relocate(EXE, B1, B2, None, B4)
    o4 = le.obj(4)
    i4 = bytes(le.img4).ljust(o4.vsize, b'\xAA')        # (the arena: garbage, as DOS/4GW may leave it)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    for b, img in ((B1, i1), (B2, i2), (B4, i4)):
        uc.mem_map(b, (len(img) + 0xfff) & ~0xfff)
        uc.mem_write(b, bytes(img))
    uc.mem_map(RET & ~0xfffff, 0x200000)
    uc.mem_write(RET, b'\xF4')
    import countries
    ct, tcn, _, _ = countries.tables(_P(LE(open(ORIG, 'rb').read())))
    return uc, le, (len(i1), len(i2)), (ct, countries.COMP[0], tcn)


def _call(uc, fn, *args):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    sp = STACK - 0x100
    uc.mem_write(sp, struct.pack('<I', RET) + b''.join(struct.pack('<I', a) for a in args))
    uc.reg_write(UC_X86_REG_ESP, sp)
    h = uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=RET, end=RET)
    uc.emu_start(fn, RET, count=2_000_000)
    uc.hook_del(h)
    v = uc.reg_read(UC_X86_REG_EAX)
    return v - (1 << 32) if v & 0x80000000 else v


def _snap(uc, sizes):
    return bytes(uc.mem_read(B1, sizes[0])), bytes(uc.mem_read(B2, sizes[1]))


def _diff(a, b, base):
    return [hex(base + i) for i in range(len(a)) if a[i] != b[i]][:6]


def test_registry():
    if not os.path.exists(EXE):
        return False, f'{EXE} missing (HT_REG_EXE: a release-recipe exe of step W)'
    uc, le, sizes, (ct, comp, tcn) = _machine()
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    u32 = lambda a: struct.unpack('<I', rd(a, 4))[0]
    hdr = rd(B4, 0x40)
    errs = []
    if hdr[:8] != swe.MAGIC or struct.unpack_from('<I', hdr, 8)[0] != swe.VERSION:
        return False, f'obj4 header {hdr[:12]!r}'
    reg, enter, leave, selmode, regprev = struct.unpack_from('<5I', hdr, 32)
    m = rd(reg, swreg.HDR)
    if m[:4] != swreg.MAGIC or struct.unpack_from('<H', m, 4)[0] != swreg.VERSION:
        return False, f'manifest {m[:6]!r}'
    nw, nsbase = m[6], m[7]
    wcur, c254, cworld, nslist, nsn = struct.unpack_from('<5I', m, 8)
    worlds = {}
    for k in range(nw):
        r = rd(reg + swreg.HDR + swreg.REC * k, swreg.REC)
        n, fl, menu, nf, year, modes, nc, stem = struct.unpack_from('<BBBBHBB4s', r)
        rows, fp, cp = struct.unpack_from('<3I', r, 12)
        worlds[n] = dict(fl=fl, menu=menu, nf=nf, year=year, modes=modes, nc=nc, stem=stem, rows=rows, fp=fp, cp=cp)
        for p_, ln in ((fp, nf), (cp, 2 * nc)):
            if ln and not B4 + swreg.REG_AT <= p_ and p_ + ln <= B4 + 0x1000:
                errs.append(f'world {n}: a list at {p_:#x} outside the manifest')
    if sorted(worlds) != [0, 4, 5]:
        return False, f'worlds {sorted(worlds)} (a release-recipe exe has 0, 4, 5)'
    w5 = worlds[5]
    if w5['stem'] != b'tmw5' or worlds[4]['stem'] != b'team' or worlds[0]['stem'] != b'team':
        errs.append(f"stems {[worlds[n]['stem'] for n in (0, 4, 5)]}")
    if w5['menu'] != 205 or worlds[4]['menu'] != 204 or worlds[0]['menu']:
        errs.append(f"menu ids {[worlds[n]['menu'] for n in (0, 4, 5)]}")
    if w5['year'] != 2026 or worlds[4]['year'] != 1984 or not all(worlds[n]['fl'] & swreg.F_NS for n in worlds):
        errs.append(f"years / flags {[(worlds[n]['year'], worlds[n]['fl']) for n in (0, 4, 5)]}")
    if worlds[0]['modes'] != 15 or any(worlds[n]['modes'] != swreg.M_CAREER for n in (4, 5)):
        errs.append(f"modes {[worlds[n]['modes'] for n in (0, 4, 5)]} (step W: nothing new listed)")
    if not (B1 <= wcur < B1 + sizes[0] and c254 == B2 + comp + 4 * 254 and B1 <= nslist < B1 + sizes[0] and nsn):
        errs.append(f'header pointers WCUR {wcur:#x} C254 {c254:#x} NSLIST {nslist:#x} ({nsn})')
    if rd(wcur, 1)[0] != nsbase or nsbase != 4:
        errs.append(f'boot WCUR {rd(wcur, 1)[0]} base {nsbase}')
    if errs:
        return False, '; '.join(errs)

    boot = _snap(uc, sizes)
    if _call(uc, enter, 0) != 1 or _call(uc, leave) != 1 or _snap(uc, sizes) != boot:
        errs.append('reg_enter(0) / reg_leave at boot changed the tables')
    nums = rd(nslist, nsn)
    tag = lambda v: 0 if not v else (B1 if v >> 30 == 1 else B2) + (v & 0x3FFFFFFF)
    r = _call(uc, enter, 5)
    if r != 1 or rd(wcur, 1)[0] != 5:
        errs.append(f'reg_enter(5) = {r}, WCUR {rd(wcur, 1)[0]}')
    bad = []
    for i, n in enumerate(nums):
        gct, gcomp, gtcn = struct.unpack('<IIH', rd(w5['rows'] + 10 * i, 10))
        got = (u32(B2 + ct + 4 * n), u32(B2 + comp + 4 * n), struct.unpack('<H', rd(B2 + tcn + 2 * n, 2))[0])
        if got != (tag(gct), tag(gcomp), gtcn):
            bad.append(n)
    if bad:
        errs.append(f'world 5 rows not in the tables for countries {bad[:8]} ({len(bad)} of {nsn})')
    in5 = _snap(uc, sizes)
    changed = sum(1 for a, b in zip(in5[1], boot[1]) if a != b)
    if _call(uc, enter, 4) != -2 or _call(uc, enter, 7) != -1 or _call(uc, enter, 5) != -2:
        errs.append('a second reg_enter / an unknown world was not refused')
    if _snap(uc, sizes) != in5:
        errs.append('a refused reg_enter changed memory')
    if _call(uc, leave) != 1 or _call(uc, leave) != 0:
        errs.append('reg_leave results')
    after = _snap(uc, sizes)
    xw = boot[0].find(b'data\\xtw0.000\0')       # careerworld XNAMEW: w_ns_set writes a tmwN world's digit there and
    ok1 = bytearray(after[0])                     # leaves it (the base world's XTRA name is its own NSXDEF string)
    if xw >= 0 and after[0][xw + 8] == ord('5'):
        ok1[xw + 8] = ord('0')
    if bytes(ok1) != boot[0] or after[1] != boot[1]:
        errs.append(f'after reg_leave obj1 {_diff(ok1, boot[0], B1)} obj2 {_diff(after[1], boot[1], B2)}')
    boot = after
    if u32(regprev) != 0xFFFFFFFF:
        errs.append(f'REG_PREV {u32(regprev):#x}')

    # the picker: obj1's call -> swe_sel_tramp -> the previous target (a `ret` here)
    from unicorn import UC_HOOK_CODE
    from le import LE
    site = swe.pick_site(_P(LE(open(ORIG, 'rb').read())))     # (the game's code: the original exe's offset)
    rel = struct.unpack('<i', rd(B1 + site + 1, 4))[0]
    tramp = B1 + site + 5 + rel
    if not B4 < tramp < B4 + swreg.REG_AT:
        errs.append(f'the picker call goes to {tramp:#x}, not obj4')
    else:
        pick = [a for a in range(tramp, tramp + 64) if rd(a, 1) == b'\xe8' and
                B1 <= a + 5 + struct.unpack('<i', rd(a + 1, 4))[0] < B1 + sizes[0]]
        tgt = pick[0] + 5 + struct.unpack('<i', rd(pick[0] + 1, 4))[0] if pick else 0
        orig = tgt
        seen = []
        uc.mem_write(orig, b'\xC3')
        h = uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: seen.append(u32(selmode)), begin=orig, end=orig)
        _call(uc, tramp)
        uc.hook_del(h)
        uc.mem_write(orig, boot[0][orig - B1:orig - B1 + 1])
        if seen != [swreg.M_FRIENDLY] or u32(selmode) != 0xFFFFFFFF or _snap(uc, sizes) != boot:
            errs.append(f'picker: SEL_MODE seen {seen}, after {u32(selmode):#x}, memory same {_snap(uc, sizes) == boot}')
    return not errs, '; '.join(errs) or (f'worlds 0 / 4 / 5 ({w5["nf"]} countries, {w5["nc"]} competitions in 5); '
                                         f'reg_enter(5): {nsn} numbers, {changed} obj2 bytes; reg_leave = boot image; '
                                         f'picker call -> obj4+{tramp - B4:#x} -> obj1+{tgt - B1:#x}')
