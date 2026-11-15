"""42-drp NORMAL gate, structural (MC 14/11, internal/handoff/42-diff-outcome-gate.md): NORMALE + CLASSICO = the
original game, proved on the host without DOSBox.

  internal/hosttest/.venv/bin/python tools/hosttest/diff_structural.py REF_BUILD NEW_BUILD [--trials N] [--out NAME]
      [--break]

REF_BUILD = a build without DIFF_* (the original game of this tree), NEW_BUILD = DIFF_TEST=3 DIFF_DRIB=0 (the beta
shape at NORMALE + CLASSICO). Both dirs hold ITALIAN.EXE (+ NEW's ITALIAN.syms.json).

1. Byte diff: the relocated obj1 / obj2 / obj3 / obj4 images of the two exes (same bases) differ only inside the hook
   regions (call + nops), the obj4 rooms (page 15, the 42-drp band) and the listed obj2 words (the OPTIONS menu
   header). Every hook region is `call <its stub>` + nops over exactly the original instruction(s).
2. Knob table: every value the NEW exe's stubs can read at NORMALE + CLASSICO (BLK_N, the L3 rows, DF_W / DF_DR's
   start) next to the original exe's own immediate / table at the same site; and the DIFFICILE column (L5).
3. Differential execution (Unicorn, both exes at the same bases): for every hook site, N random machine states
   (registers, flags, the game's D0..A6 variables, every other byte of memory = the same deterministic random page in
   both); REF runs its original instructions, NEW its call + stub + nops, to the region's end. Equal = every register,
   the arithmetic flags, ESP / EIP, every memory byte either wrote (outside NEW's own obj4 rooms and the dead stack
   under ESP), and every call out of the region (target, registers, stack top) - an external routine is a stand-in
   that returns the same pseudo-random eax / flags in both. Run with DF_ACT 0 / DF_DACT 0 (the kick-off's output at
   NORMALE + CLASSICO, which the KICK site itself is checked to produce).
   Controls: the same runs with DF_ACT 5 (DIFFICILE) and DF_DACT 1 (DRIBBLING NUOVO) on states that make one team a
   computer team facing a human: the knob sites must then differ (the check sees a real change).
4. --break: the must-break control (MC): a scratch copy of NEW with BLK_N.hold 3200 -> 3264; the table and the HOLD
   sites must flag it.
Writes internal/swostest/outcome-gate/NAME.md + .json."""
import argparse
import hashlib
import json
import os
import random
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED, \
    UC_PROT_ALL
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI,
                               UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS,
                               UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_GDTR)

import emu
import swreg
import difficulty as df
import buildup
from lepatch import LEPatch

B1, B2, B3, B4 = 0x0100000, 0x0400000, 0x0C00000, 0x0E00000
SCR, SCR_N = 0x1800000, 0x100000         # the pointer zone of the random pages
STACK = 0x1F00800
GDT_AT = 0x1FF0000
GPR = (('eax', UC_X86_REG_EAX), ('ebx', UC_X86_REG_EBX), ('ecx', UC_X86_REG_ECX), ('edx', UC_X86_REG_EDX),
       ('esi', UC_X86_REG_ESI), ('edi', UC_X86_REG_EDI), ('ebp', UC_X86_REG_EBP))
FLAGS = 0x8D5                            # CF PF AF ZF SF OF
SP_COVER = []                                       # (set pieces' obj1 hook regions, when NEW links them)
ROOMS = ((swreg.DRIB1V1_AT, swreg.DRIB1V1_END), (swreg.DIFF_AT, swreg.DIFF_END), (swreg.DIFF2_AT, swreg.DIFF2_END))
HOOKS = (('KICK', 10, 'df_kick'), ('SC', 13, 'df_scale'), ('GK', 11, 'df_gk'), ('PS', 10, 'df_pass'),
         ('GL', 8, 'df_goal'), ('SL', 7, 'df_slide'), ('TU', 6, 'df_turn'), ('CAR', 37, 'df_carrier'))


def lin(sym):
    obj, off = sym
    if obj == 'lin':
        return off
    return {1: B1, 2: B2, 3: B3, 4: B4}[obj] + off


def sites(ref_exe):
    """(name, obj1 offset, length, stub label) for every hook, found in the ORIGINAL exe by the build's own finders."""
    p = LEPatch(ref_exe)
    s, sym = df.find(p)
    w1 = df.w1_find(p, sym)
    bs, _ = buildup.find(p, sym)
    out = [(k, s[k], n, l) for k, n, l in HOOKS]
    out += [(f'HOLD{i}', o, 7, 'df_hold') for i, o in enumerate(s['HOLD'])]
    out += [('LOCKW', s['LOCK'][0], 9, 'df_lockw'), ('LOCKL', s['LOCK'][1], 9, 'df_lockl')]
    out += [(f'W1A{i}', o, 11, 'w1_pick') for i, o in enumerate(w1['A'])]
    out += [('W1B', w1['B'], 40, 'w1_dest'), ('W1C', w1['C'], 16, 'w1_aim'), ('W1D', w1['D'], 5, 'w1_win'),
            ('W1E', w1['E'], 8, 'w1_nbh')]
    out += [('BUG1', bs['G1'], 6, 'bu_g1'), ('BUH1', bs['H1'], 10, 'bu_h1'), ('BUP1', bs['P1'], 10, 'bu_p1')]
    return out, s, sym, w1, p


def images(exe):
    i1, i2, le = emu.relocate(exe, B1, B2, B3, B4)
    assert B1 + len(i1) <= B2 and B2 + len(i2) <= B3, 'bases overlap'
    assert le.img3 is None or B3 + len(le.img3) <= B4, 'obj3 overlaps obj4'
    return {1: i1, 2: i2, 3: le.img3, 4: le.img4}


def labels(build):
    sy = json.load(open(os.path.join(build, 'ITALIAN.syms.json')))
    lab = {}
    for mod in ('difficulty', 'buildup'):
        for k, v in sy[mod].items():
            lab[k] = v[1]                        # (obj4 offsets)
    return lab


def ranges(xs):
    out = []
    for x in sorted(xs):
        if out and x == out[-1][1]:
            out[-1][1] = x + 1
        else:
            out.append([x, x + 1])
    return out


# ---------------------------------------------------------------------------------------------------- 1. byte diff
def byte_diff(ri, ni, hooks, lab):
    res, ok = [], True
    for obj in (1, 2, 3, 4):
        a, b = ri[obj], ni[obj]
        if a is None and b is None:
            continue
        if len(a) != len(b):
            n = min(len(a), len(b))
            # (obj4 may grow by pages for the DIFF2 band, 14/11: the new tail must be zero outside the rooms)
            tail_ok = obj == 4 and len(b) > len(a) and not any(
                b[i] for i in range(n, len(b)) if not any(lo <= i < hi for lo, hi in ROOMS))
            res.append(f'obj{obj}: sizes {len(a):#x} / {len(b):#x}'
                       + (' (the new tail: zero outside the rooms)' if tail_ok else ' FAIL'))
            ok &= tail_ok
        else:
            n = len(a)
        diff = [i for i in range(n) if a[i] != b[i]] if a[:n] != b[:n] else []
        rs = ranges(diff)
        if obj == 1:
            cover = {}
            for name, o, ln, l in hooks:
                for x in range(o, o + ln):
                    cover[x] = name
                want = b'\xe8' + struct.pack('<i', B4 + lab[l] - (B1 + o + 5)) + b'\x90' * (ln - 5)
                got = bytes(b[o:o + ln])
                good = got == want
                ok &= good
                res.append(f'obj1 {name} {o:#x}+{ln}: REF {bytes(a[o:o + ln]).hex()} -> NEW `call {l}` + {ln - 5} nop '
                           f'{"ok" if good else "WRONG " + got.hex()}')
            stray = [r for r in rs if any(x not in cover for x in range(*r))]
            spc = [r for r in stray if any(lo <= r[0] and r[1] <= hi for lo, hi in SP_COVER)]
            if SP_COVER:                                # (disk A: CALCI PIAZZATI's own hooks, proved by sp_structural)
                res.append(f'obj1: {len(spc)} changed ranges inside the set pieces\' hook regions (sp_structural.py)')
                stray = [r for r in stray if r not in spc]
            cls, bad, BLOCKS[:] = classify(a, b, stray)
            res.append(f'obj1: {len(rs)} changed ranges, {len(stray)} outside the hook regions, classified:')
            res += ['  ' + x for x in cls]
            res.append(f'obj1: unexplained changes outside the hooks: {bad or "none"}')
            ok &= not bad
        elif obj == 4:
            stray = [r for r in rs if not any(lo <= r[0] and r[1] <= hi for lo, hi in ROOMS)]
            # (more obj4 pages - the DIFF2 band, 14/11 - move the engine's .bss, which follows obj4's image: its
            #  pointers change by exactly the size delta; every stray byte must sit in such a dword)
            delta, moved, keep = len(b) - len(a), 0, []
            for r in stray:
                okr = delta > 0 and all(any(B4 + len(a) <= struct.unpack_from('<I', a, d)[0] < B4 + 0x100000
                                            and struct.unpack_from('<I', b, d)[0]
                                            == struct.unpack_from('<I', a, d)[0] + delta
                                            for d in range(max(0, x - 3), x + 1)) for x in range(*r))
                if okr:
                    moved += 1
                else:
                    keep.append(r)
            if moved:
                res.append(f'obj4: {moved} changed ranges = engine .bss pointers moved by the obj4 size delta {delta:#x}')
            stray = keep
            res.append(f'obj4: {len(rs)} changed ranges, all inside the rooms '
                       f'{[(hex(lo), hex(hi)) for lo, hi in ROOMS]}: {not stray} {[(hex(x), y - x) for x, y in stray]}')
            ok &= not stray
        else:
            res.append(f'obj{obj}: changed ranges {[(hex(x), y - x) for x, y in rs]}')
            if obj == 2:                                # (the OPTIONS menu header: init / return -> df_init / df_ret,
                hdr = [r for r in rs if struct.unpack_from('<I', b, r[0] & ~3)[0] in (B4 + lab['df_init'],
                                                                                    B4 + lab['df_ret'])]
                for r in hdr:                           #  the DIFFICOLTA / DRIBBLING rows' chain)
                    res.append(f'  {r[0]:#x}: OPTIONS menu header {struct.unpack_from("<I", a, r[0] & ~3)[0]:#x} -> '
                               f'{struct.unpack_from("<I", b, r[0] & ~3)[0]:#x} (df_init / df_ret, the new rows)')
                rs = [r for r in rs if r not in hdr]
                OBJ2_OK.extend(hdr)
            cls, bad, _ = classify(a, b, rs, {2: B2, 3: B3}[obj], BLOCKS)
            res += ['  ' + x for x in cls]
            res.append(f'obj{obj}: unexplained: {bad or "none"}')
            ok &= not bad
    return ok, res


def classify(a, b, stray, base=B1, blocks=None):
    """The obj1 changes outside the hook regions: blocks where NEW inserted bytes (difflib alignment of each cluster of
    changes) and operands elsewhere that point into such a block (a dword whose value moved by the inserted size).
    Returns (lines, unexplained ranges)."""
    import difflib
    cl = []
    for r in stray:
        if cl and r[0] - cl[-1][1] < 0x400:
            cl[-1][1] = r[1]
        else:
            cl.append(list(r))
    lines, rest = [], []
    if blocks is not None:                              # (obj2 / obj3: only operands into obj1's blocks)
        rest = [tuple(r) for r in stray]
        cl = []
    blocks = [] if blocks is None else blocks
    for lo, hi in cl:
        if hi - lo < 8:
            rest.append((lo, hi))
            continue
        w0, w1 = max(0, lo - 64), min(len(a), hi + 64)
        sm = difflib.SequenceMatcher(None, bytes(a[w0:w1]), bytes(b[w0:w1]), autojunk=False)
        ins, rep, other = [], 0, []
        for t, i1, i2, j1, j2 in sm.get_opcodes():
            if t == 'insert':
                ins.append((w0 + i1, bytes(b[w0 + j1:w0 + j2])))
            elif t == 'replace' and i2 - i1 <= 4:
                rep += 1
            elif t != 'equal':
                other.append((t, hex(w0 + i1), i2 - i1, j2 - j1))
        if not ins:                                     # (no insertion: its changes are operands, checked one by one)
            rest += [tuple(r) for r in stray if lo <= r[0] < hi]
            continue
        blocks.append((lo, hi))
        lines.append(f'block {lo:#x}..{hi:#x}: inserted {[(hex(o), x.hex()) for o, x in ins]}; {rep} operand-size '
                     f'replacements (the shifted code\'s own references); other: {other or "none"}')
    bad = []
    for lo, hi in rest:
        why = None
        for w in range(lo - 3, lo + 1):
            ra, rb = struct.unpack_from('<I', a, w)[0], struct.unpack_from('<I', b, w)[0]
            if not 0 < (rb - ra) & 0xFFFFFFFF <= 0x40 or w + 4 < hi:
                continue
            for tgt, kind in ((ra - B1, 'abs'), (base + w + 4 + struct.unpack_from('<i', a, w)[0] - B1, 'rel')):
                if any(blo - 0x2000 <= tgt < bhi + 0x2000 for blo, bhi in blocks):
                    why = f'{kind} operand at {w:#x} -> obj1+{tgt:#x} moved +{(rb - ra) & 0xFFFFFFFF:#x}'
                    break
            if why:
                break
        if why:
            lines.append(f'{lo:#x}+{hi - lo}: {why}')
        else:
            bad.append((hex(lo), hi - lo))
    return lines, bad, blocks


OBJ2_OK = []
BLOCKS = []


# ---------------------------------------------------------------------------------------------------- 2. knob table
def knob_table(ref_p, s, sym, ni, lab):
    o4 = ni[4]
    u8 = lambda off: o4[off]
    s8 = lambda off: struct.unpack_from('<b', o4, off)[0]
    u16 = lambda off: struct.unpack_from('<H', o4, off)[0]
    u32 = lambda off: struct.unpack_from('<I', o4, off)[0]
    d = ref_p.le.obj_bytes(1)
    r16 = lambda o: struct.unpack_from('<H', d, o)[0]
    r32 = lambda o: struct.unpack_from('<I', d, o)[0]
    kf = sym['KFAIL']
    ref_k3 = list(struct.unpack_from('<8H', ref_p.le.obj_bytes(kf[0]), kf[1]))
    bn = lab['BLK_N']
    lv = lambda L: L - 1
    car = d[s['CAR']:s['CAR'] + 37]
    assert car[13:16] == b'\x66\xc1\x2d' and car[20] == 3, car.hex()
    rows = [
        # (knob, NEW address, REF value / where, NEW@NORMAL, NEW@DIFFICILE (L5), equal at NORMAL)
        ('DF_W start (DIFFICOLTA)', f'obj4+{lab["DF_W"]:#x}', 'no option', u16(lab['DF_W']), '-', u16(lab['DF_W']) == 0),
        ('LVMAP[DF_W] -> DF_ACT', f'obj4+{lab["LVMAP"]:#x}', 'off', f'level {u8(lab["LVMAP"])} -> DF_ACT 0 (df_kick)',
         '-', u8(lab['LVMAP']) == 3),
        ('DF_DR start (DRIBBLING)', f'obj4+{lab["DF_DR"]:#x}', 'no option', u16(lab['DF_DR']), '-', u16(lab['DF_DR']) == 0),
        ('K1 skills %', f'obj4+{lab["K1T"]:#x}', '100 (no scaling)', u16(lab['K1T'] + 2 * lv(3)),
         u16(lab['K1T'] + 2 * lv(5)), u16(lab['K1T'] + 2 * lv(3)) == 100),
        ('K2 keeper points', f'obj4+{lab["K2T"]:#x}', '0', s8(lab['K2T'] + lv(3)), s8(lab['K2T'] + lv(5)),
         s8(lab['K2T'] + lv(3)) == 0),
        ('K2b keeper close-shot shift', f'obj4+{lab["K2BT"]:#x}', '0', s8(lab['K2BT'] + lv(3)), s8(lab['K2BT'] + lv(5)),
         s8(lab['K2BT'] + lv(3)) == 0),
        ('K3 pass errors /16 by passing 0..7', f'obj4+{lab["K3T"]:#x}', f'{ref_k3} (kAIFailedPassChance)',
         list(struct.unpack_from('<8H', o4, lab['K3T'] + 16 * lv(3))),
         list(struct.unpack_from('<8H', o4, lab['K3T'] + 16 * lv(5))),
         list(struct.unpack_from('<8H', o4, lab['K3T'] + 16 * lv(3))) == ref_k3),
        ('K4 carrier slowdown k (speed*k>>5)', f'BLK_N+0 obj4+{bn:#x}', f'shr {car[20]} = k {1 << (5 - car[20])}',
         u16(bn), 'BLK_N (same)', u16(bn) == 1 << (5 - car[20])),
        ('K9 lockw (winner timer)', f'BLK_N+2', f'{r16(s["LOCK"][0] + 7)} @obj1+{s["LOCK"][0] + 7:#x}', u16(bn + 2),
         'BLK_N (same)', u16(bn + 2) == r16(s['LOCK'][0] + 7)),
        ('K9 lockl (loser timer)', f'BLK_N+4', f'{r16(s["LOCK"][1] + 7)} @obj1+{s["LOCK"][1] + 7:#x}', u16(bn + 4),
         'BLK_N (same)', u16(bn + 4) == r16(s['LOCK'][1] + 7)),
        ('K10 turn run-ahead', f'BLK_N+6', f'{r16(s["TU"] + 4)} @obj1+{s["TU"] + 4:#x}', u16(bn + 6), 'BLK_N (same)',
         u16(bn + 6) == r16(s['TU'] + 4)),
        ('K11 box gate px', f'BLK_N+8', '0 (no gate)', u16(bn + 8), 'BLK_N (same)', u16(bn + 8) == 0),
        ('K8 hold-back (site 1)', f'BLK_N+12', f'{r32(s["HOLD"][0] + 3)} @obj1+{s["HOLD"][0] + 3:#x}', u32(bn + 12),
         'BLK_N (same)', u32(bn + 12) == r32(s['HOLD'][0] + 3)),
        ('K8 hold-back (site 2)', f'BLK_N+12', f'{r32(s["HOLD"][1] + 3)} @obj1+{s["HOLD"][1] + 3:#x}', u32(bn + 12),
         'BLK_N (same)', u32(bn + 12) == r32(s['HOLD'][1] + 3)),
        ('K5 CPU slide radius', f'BLK_N+16', f'{r32(s["SL"] + 3)} @obj1+{s["SL"] + 3:#x}', u32(bn + 16),
         'BLK_N (same)', u32(bn + 16) == r32(s['SL'] + 3)),
        ('W1 wait (1-v-1)', f'BLK_N+20', '0 (no W1)', u16(bn + 20), 'BLK_N (same)', u16(bn + 20) == 0),
    ]
    return rows


# ---------------------------------------------------------------------------------------------------- 3. emulation
class Mach:
    def __init__(self, img, seed):
        self.seed = seed
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_32)
        for base, b in ((B1, img[1]), (B2, img[2]), (B3, img[3]), (B4, img[4])):
            if b:
                n = (len(b) + 0xFFF) & ~0xFFF
                uc.mem_map(base, n)
                uc.mem_write(base, bytes(b))
        uc.mem_map(GDT_AT, 0x1000)
        gdt = bytearray(8 * 64)
        gdt[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
        gdt[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
        uc.mem_write(GDT_AT, bytes(gdt))
        uc.reg_write(UC_X86_REG_GDTR, (0, GDT_AT, len(gdt) - 1, 0))
        for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
            uc.reg_write(r, emu.DATA_SEL)
        uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
        self.writes = set()
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._fill)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._w)

    def _fill(self, uc, access, addr, size, value, _):
        pg = addr & ~0xFFF
        self.npages = getattr(self, 'npages', 0) + 1
        if self.npages > 512:                           # (runaway code: stop, the run reports an error)
            return False
        for q in (pg, (addr + size - 1) & ~0xFFF):
            try:
                uc.mem_map(q, 0x1000, UC_PROT_ALL)
                uc.mem_write(q, page(self.seed, q))
            except UcError:
                pass
        return True

    def _w(self, uc, access, addr, size, value, _):
        for k in range(size):
            self.writes.add(addr + k)

    def read(self, a, n):
        try:
            return bytes(self.uc.mem_read(a, n))
        except UcError:
            self._fill(self.uc, 0, a, n, 0, None)
            return bytes(self.uc.mem_read(a, n))

    def w32(self, a, v):
        self.read(a, 4)
        self.uc.mem_write(a, struct.pack('<I', v & 0xFFFFFFFF))

    def w8(self, a, v):
        self.read(a, 1)
        self.uc.mem_write(a, bytes([v & 0xFF]))

    def w16(self, a, v):
        self.read(a, 2)
        self.uc.mem_write(a, struct.pack('<H', v & 0xFFFF))


_PAGES = {}


def page(seed, pg):
    k = (seed, pg)
    if k not in _PAGES:
        r = random.Random(hashlib.sha256(f'{seed}:{pg}'.encode()).digest())
        out = bytearray()
        for _ in range(1024):
            c = r.random()
            v = (SCR + (r.randrange(SCR_N) & ~1)) if c < 0.35 else r.randrange(0, 5000) if c < 0.7 else \
                r.getrandbits(32)
            out += struct.pack('<I', v)
        if len(_PAGES) > 4096:
            _PAGES.clear()
        _PAGES[k] = bytes(out)
    return _PAGES[k]


def rval(r):
    c = r.random()
    return (SCR + (r.randrange(SCR_N) & ~1)) if c < 0.4 else r.randrange(0, 5000) if c < 0.7 else r.getrandbits(32)


class External(Exception):
    pass


def run(m, start, end, allowed, max_steps=20000):
    """Run from start until EIP == end. A jump / call to an address outside `allowed` is an external routine: logged
    (target, registers, 4 stack dwords) and stood in for: pops its return address, eax / edx / flags = a value from
    the call's log entry (the same in both machines when the logs agree)."""
    uc = m.uc
    log = []
    steps = [0]

    def code(uc, addr, size, _):
        steps[0] += 1
        if steps[0] > max_steps:
            raise External('steps')
        if addr in ends:
            uc.emu_stop()
            return
        if not any(lo <= addr < hi for lo, hi in allowed):
            esp = uc.reg_read(UC_X86_REG_ESP)
            regs = tuple(uc.reg_read(r) for _, r in GPR)
            stk = struct.unpack('<4I', m.read(esp, 16))
            log.append((addr, regs, stk))
            h = int.from_bytes(hashlib.sha256(repr(log[-1]).encode()).digest()[:12], 'little')
            ret = stk[0]
            uc.reg_write(UC_X86_REG_ESP, esp + 4)
            uc.reg_write(UC_X86_REG_EAX, h & 0xFFFFFFFF)
            uc.reg_write(UC_X86_REG_EDX, (h >> 32) & 0xFFFFFFFF)
            uc.reg_write(UC_X86_REG_EFLAGS, 0x202 | ((h >> 64) & FLAGS))
            uc.reg_write(UC_X86_REG_EIP, ret)

    ends = set(end) if isinstance(end, (tuple, list, set)) else {end}
    end = min(ends)
    hk = uc.hook_add(UC_HOOK_CODE, code)
    err = None
    try:
        uc.emu_start(start, end, count=max_steps + 5)
    except (UcError, External) as e:
        err = str(e)
    uc.hook_del(hk)
    eip = uc.reg_read(UC_X86_REG_EIP)
    if err is None and eip not in ends:
        err = f'stopped at {eip:#x}'
    return log, err


def state(m):
    uc = m.uc
    return dict(**{n: uc.reg_read(r) for n, r in GPR}, esp=uc.reg_read(UC_X86_REG_ESP),
                eip=uc.reg_read(UC_X86_REG_EIP), flags=uc.reg_read(UC_X86_REG_EFLAGS) & FLAGS)


def trial(ri, ni, site, sym, lab, seed, act, dact, structured, dead_flags=False, gspl=None, ends=None):
    name, o, ln, l = site
    r = random.Random(seed)
    ms = (Mach(ri, seed), Mach(ni, seed))
    regs = {n: rval(r) for n, _ in GPR}
    fl = 0x202 | (r.getrandbits(12) & FLAGS)
    var = {k: rval(r) for k in range(15)}               # D0..D7, A0..A6
    swpp, trg = r.choice((0xFF, 0xFF, 0xFF, r.getrandbits(8))), r.choice((0, 0, 0, 1))
    t1, t2 = SCR + 0x40000 + 0x200 * r.randrange(64), SCR + 0x80000 + 0x200 * r.randrange(64)
    f1, f2 = SCR + 0xC0000 + 0x100 * r.randrange(64), SCR + 0xE0000 + 0x100 * r.randrange(64)
    cpu_side = r.random() < 0.5
    dist = r.choice((r.randrange(0, 260), r.randrange(0, 6000), r.getrandbits(32)))
    for m in ms:
        for n, rg in GPR:
            m.uc.reg_write(rg, regs[n])
        m.uc.reg_write(UC_X86_REG_ESP, STACK)
        m.uc.reg_write(UC_X86_REG_EFLAGS, fl)
        m.read(STACK - 0x100, 0x200)
        for k, v in var.items():
            m.w32(lin(sym['D0_']) + 4 * k, v)
        m.w8(lin(sym['SWOSPP']), swpp)
        m.w16(lin(sym['TRG']), trg)
        if structured:                                  # human team t1 v computer team t2 (TeamGeneralInfo: +0
            for t, u, h in ((t1, t2, 1), (t2, t1, 0)):  #  opponentsTeam, +4 playerNumber, +6 playerCoachNumber)
                m.w32(t, u)
                m.w16(t + 4, h)
                m.w16(t + 6, 0)
                m.w32(t + 0x20, SCR + 0x10000)          # (controlledPlayer)
            me = t2 if cpu_side else t1
            m.w32(lin(sym['A6_']), me)
            m.w8(f1 + 4, 1)                             # (team files: A2 the computer's, A3 the human's)
            m.w8(f2 + 4, 2)
            m.w32(lin(sym['A2_']), f1)
            m.w32(lin(sym['A3_']), f2)
            m.uc.reg_write(UC_X86_REG_EBX, me)
            m.uc.reg_write(UC_X86_REG_ESI, me if name.startswith('LOCK') else regs['esi'])
            sp = m.uc.reg_read(UC_X86_REG_ESI)
            m.w32(sp + 0x4A, dist)
        m.writes.clear()
    nm = ms[1]
    nm.w16(B4 + lab['DF_W'], 0)
    nm.w16(B4 + lab['DF_DR'], 0)
    nm.w8(B4 + lab['DF_ACT'], act if name != 'KICK' else r.getrandbits(8))
    nm.w8(B4 + lab['DF_DACT'], dact if name != 'KICK' else r.getrandbits(8))
    if gspl is not None:                                # (14/11 the corner: gameStatePl in both; NEW's PERSONALIZZATO
        for m in ms:                                    #  blocks far off the original, W1 on in both sides' blocks)
            m.w16(lin(sym['GSPL']), gspl)
        for b in ('BLK_CU', 'BLK_CO'):
            nm.read(B4 + lab[b], 32)
            nm.uc.mem_write(B4 + lab[b], bytes([0, 0, 24, 0, 24, 0, 176, 0, 16, 0, 0, 0, 0x50, 0x24, 0, 0,
                                         50, 0, 0, 0, r.choice((1, 2, 3)), 0]) + bytes(10))
    nm.writes.clear()
    start, end = B1 + o, B1 + o + ln
    reg = (start, end)
    out = []
    for m, allowed in ((ms[0], (reg,)), (ms[1], (reg,) + tuple((B4 + lo, B4 + hi) for lo, hi in ROOMS))):
        log, err = run(m, start, ends or end, allowed)
        out.append((state(m), log, err))
    (sa, la, ea), (sb, lb, eb) = out
    diffs = []
    if ea or eb:
        diffs.append(f'run: REF {ea} / NEW {eb}')
    for k in sa:
        if sa[k] != sb[k] and not (k == 'flags' and dead_flags):
            diffs.append(f'{k} {sa[k]:#x} / {sb[k]:#x}')
    if la != lb:
        diffs.append(f'calls out: REF {[hex(x[0]) for x in la]} / NEW {[hex(x[0]) for x in lb]}')
    esp = min(sa['esp'], sb['esp'])
    own = set()
    for a in ms[0].writes | ms[1].writes:
        if STACK - 0x1000 <= a < esp:
            continue                                    # (dead stack under ESP)
        if any(B4 + lo <= a < B4 + hi for lo, hi in ROOMS):
            own.add(a - B4)                             # (NEW's own state)
            continue
        if ms[0].read(a, 1) != ms[1].read(a, 1):
            diffs.append(f'mem {a:#x} {ms[0].read(a, 1).hex()} / {ms[1].read(a, 1).hex()}')
            if len(diffs) > 8:
                break
    if name == 'KICK':                                  # (the kick-off at NORMALE + CLASSICO: DF_ACT = DF_DACT = 0)
        a_, d_ = nm.read(B4 + lab['DF_ACT'], 1)[0], nm.read(B4 + lab['DF_DACT'], 1)[0]
        if (a_, d_) != (0, 0):
            diffs.append(f'kick-off: DF_ACT {a_} DF_DACT {d_} (want 0 0)')
    inv = {v: k for k, v in lab.items()}
    own_names = sorted({inv.get(a, None) or near(a, lab) for a in own})
    return diffs, own_names, la


def near(a, lab):
    best = max(((v, k) for k, v in lab.items() if v <= a), default=(0, '?'))
    return f'{best[1]}+{a - best[0]}'


# ---------------------------------------------------------------------------------------------------- flag liveness
JCC = {'jo': 'O', 'jno': 'O', 'jc': 'C', 'jb': 'C', 'jnae': 'C', 'jnc': 'C', 'jae': 'C', 'jnb': 'C', 'jz': 'Z',
       'je': 'Z', 'jnz': 'Z', 'jne': 'Z', 'jna': 'CZ', 'jbe': 'CZ', 'ja': 'CZ', 'jnbe': 'CZ', 'js': 'S', 'jns': 'S',
       'jpe': 'P', 'jp': 'P', 'jpo': 'P', 'jnp': 'P', 'jl': 'SO', 'jnge': 'SO', 'jge': 'SO', 'jnl': 'SO', 'jng': 'ZSO',
       'jle': 'ZSO', 'jg': 'ZSO', 'jnle': 'ZSO'}
ALLW = {'cmp', 'test', 'add', 'sub', 'and', 'or', 'xor', 'neg', 'popf', 'popfd', 'popfw', 'sahf', 'cmpsb', 'cmpsw',
        'cmpsd', 'scasb', 'scasw', 'scasd', 'bsf', 'bsr'}
READ_ALL = {'pushf', 'pushfd', 'pushfw', 'lahf', 'into', 'adc', 'sbb', 'rcl', 'rcr', 'salc'}


_DIS = {}


def disasm_one(img1, addr):
    """(mnemonic, operands, length) of the instruction at linear addr (obj1), by ndisasm."""
    if (id(img1), addr) in _DIS:
        return _DIS[(id(img1), addr)]
    import subprocess
    import tempfile
    o = addr - B1
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(bytes(img1[o:o + 16]))
    out = subprocess.run(['ndisasm', '-b32', '-o', str(addr), f.name], capture_output=True, text=True).stdout
    os.unlink(f.name)
    lines = out.splitlines()
    ln = lines[0].split(None, 2)
    hexb = ln[1]
    for x in lines[1:]:                                 # (long instructions: '-4A00' continuation lines)
        if x.startswith(' ') and x.strip().startswith('-'):
            hexb += x.strip()[1:]
        else:
            break
    txt = ln[2] if len(ln) > 2 else ''
    m, _, ops = txt.partition(' ')
    _DIS[(id(img1), addr)] = r = (m.lower(), ops.strip(), len(hexb) // 2)
    return r


def callers(img1, fn):
    """Linear addresses of every `call rel32` to fn in obj1 (a byte scan: an E8 inside another instruction can only add
    a continuation to check - conservative)."""
    out = []
    for x in range(len(img1) - 5):
        if img1[x] == 0xE8 and B1 + x + 5 + struct.unpack_from('<i', img1, x + 1)[0] == fn:
            out.append(B1 + x)
    return out


def flag_liveness(img1, start, live='CPAZSO', max_n=80, fn=None):
    """Walk the ORIGINAL code from `start` (the region's end): 'dead' when every flag in `live` is written before any
    is read; ('LIVE', where) when one is read; ('UNKNOWN', where) at a ret / indirect branch / the step limit. Follows
    jmp, both arms of a jcc that reads no live flag, and calls (into the callee and back)."""
    todo, seen, path = [(start, frozenset(live), ())], set(), []
    budget = [600]                                      # (instructions in all: past it, UNKNOWN)
    outer = set()
    res = 'dead'
    while todo:
        a, lv, stack = todo.pop()
        for _ in range(max_n):
            if not lv:
                break
            if (a, lv, stack) in seen:
                break
            seen.add((a, lv, stack))
            budget[0] -= 1
            if budget[0] < 0:
                return ('UNKNOWN', 'walk budget (600 instructions)'), path
            m, ops, n = disasm_one(img1, a)
            path.append(f'{a:#x} {m} {ops}')
            nxt = a + n
            if m in JCC or m.startswith('set') or m.startswith('cmov') or m in ('loope', 'loopne', 'loopz', 'loopnz'):
                reads = set(JCC.get(m, 'CPAZSO' if not m.startswith('loop') else 'Z'))
                if reads & lv:
                    return ('LIVE', f'{a:#x} {m} {ops}'), path
                if m in JCC:
                    tgt = int(ops.split()[-1], 16)
                    todo.append((tgt, lv, stack))
                a = nxt
                continue
            if m in READ_ALL:
                return ('LIVE', f'{a:#x} {m} {ops}'), path
            if m in ALLW:
                lv = frozenset()
                break
            if m in ('inc', 'dec'):
                lv = lv & frozenset('C')
            elif m in ('shl', 'shr', 'sar', 'sal') and ',' in ops and ops.split(',')[-1].strip().replace('byte ', '') \
                    .startswith('0x') and int(ops.split(',')[-1].strip().replace('byte ', ''), 16) & 31:
                lv = lv & frozenset('A')
            elif m in ('shl', 'shr', 'sar', 'sal') and ',' not in ops:
                lv = lv & frozenset('A')
            elif m in ('mul', 'imul'):
                lv = lv & frozenset('PAZS')        # (CF / OF defined, the rest undefined: never relied on)
            if m == 'jmp':
                if ops.startswith(('dword', '[', 'e')):
                    return ('UNKNOWN', f'{a:#x} jmp {ops}'), path
                a = int(ops.split()[-1], 16)
                continue
            if m == 'call':
                if ops.startswith(('dword', '[', 'e')):
                    return ('UNKNOWN', f'{a:#x} call {ops}'), path
                stack = stack + (nxt,)
                a = int(ops.split()[-1], 16)
                continue
            if m in ('ret', 'retn', 'retf', 'iret', 'iretd') or m.startswith('ret'):
                if not stack:
                    if fn is None or a in outer:
                        return ('UNKNOWN', f'{a:#x} {m}: flags reach the caller'), path
                    cs = callers(img1, fn)          # (back in each caller of the routine: once)
                    path.append(f'  ret -> {len(cs)} callers of {fn:#x}: {[hex(c) for c in cs]}')
                    for c in cs:
                        todo.append((c + 5, lv, ('outer',)))
                    break
                if stack == ('outer',):
                    return ('UNKNOWN', f'{a:#x} {m}: flags reach a caller\'s caller'), path
                a, stack = stack[-1], stack[:-1]
                continue
            a = nxt
        else:
            return ('UNKNOWN', f'step limit at {a:#x}'), path
    return res, path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('new')
    ap.add_argument('--trials', type=int, default=300)
    ap.add_argument('--ctrl-trials', type=int, default=200)
    ap.add_argument('--out', default='42drp-structural')
    ap.add_argument('--brk', action='store_true', help='the must-break control (BLK_N.hold 3200 -> 3264)')
    a = ap.parse_args()
    ref_exe, new_exe = os.path.join(a.ref, 'ITALIAN.EXE'), os.path.join(a.new, 'ITALIAN.EXE')
    lab = labels(a.new)
    if a.brk:                                           # a scratch copy, one knob off REF
        raw = bytearray(open(new_exe, 'rb').read())
        pat = df._blk(df.NORM)
        at = [i for i in range(len(raw) - 32) if raw[i:i + 32] == pat]
        assert len(at) == 1, ('BLK_N in the file', at)
        struct.pack_into('<I', raw, at[0] + 12, 3264)
        new_exe = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'dstruct_break.EXE')
        open(new_exe, 'wb').write(raw)
        a.out += '-break'
    hooks, s, sym, w1, ref_p = sites(ref_exe)
    sym['CIPWB'] = w1['CIPWB']
    sym['GSPL'] = w1['GSPL']
    ri, ni = images(ref_exe), images(new_exe)
    if 'setpieces' in json.load(open(os.path.join(a.new, 'ITALIAN.syms.json'))):   # (disk A, 15/11: CALCI PIAZZATI
        global ROOMS                                    #  linked with the OPTIONS rows - its band = NEW's own code /
        import setpieces as sp                          #  state; df_kick's sp_set runs in it; sp_structural proves
        ROOMS = ROOMS + ((swreg.SETPIECE_AT, swreg.SETPIECE_END),)   # its own obj1 hooks)
        s0, _ = sp.find(LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE')))
        SP_COVER[:] = [(s0[k0], s0[k0] + n) for k0, n, _l in sp.HOOKS]
    k = lab['df_kick']                                  # (SWOS++ / training-game flags: df_kick's own operands,
    assert ni[4][k:k + 5] == bytes.fromhex('5031c0803d') and ni[4][k + 9] == 0xFF, ni[4][k:k + 16].hex()   #  linear)
    sym['SWOSPP'] = ('lin', struct.unpack_from('<I', ni[4], k + 5)[0])
    assert ni[4][k + 10] == 0x75 and ni[4][k + 12:k + 15] == bytes.fromhex('66833d'), ni[4][k:k + 24].hex()
    sym['TRG'] = ('lin', struct.unpack_from('<I', ni[4], k + 15)[0])
    L = [f'# 42-drp NORMAL gate, structural: {a.out}', '',
         f'REF `{ref_exe}`  ', f'NEW `{new_exe}` (DIFF_TEST=3 DIFF_DRIB=0: NORMALE + CLASSICO)', '']
    ok_b, res = byte_diff(ri, ni, hooks, lab)
    L += ['## 1. Byte diff (relocated images, same bases)', ''] + [f'- {x}' for x in res] + ['']
    rows = knob_table(ref_p, s, sym, ni, lab)
    ok_k = all(x[5] for x in rows)
    L += ['## 2. Knob table (what the stubs can read at NORMALE + CLASSICO)', '',
          '| knob | NEW address | REF (original exe) | NEW @ NORMALE+CLASSICO | NEW @ DIFFICILE (L5) | equal |',
          '|---|---|---|---|---|---|']
    L += [f'| {k} | {ad} | {rv} | {nv} | {hv} | {"yes" if e else "**NO**"} |' for k, ad, rv, nv, hv, e in rows]
    L += ['', 'At NORMALE the kick-off sets DF_ACT = 0, so no stub reads the L3 rows at all (they equal the original '
          'anyway); at CLASSICO DF_DACT = 0, so every DRIBBLING stub reads BLK_N.', '']
    modes = [('NORMAL', 0, 0, a.trials, False), ('NORMAL, team pair', 0, 0, a.trials, True),
             ('DIFFICILE (control)', 5, 0, a.ctrl_trials, True), ('DRIBBLING NUOVO (control)', 0, 1, a.ctrl_trials, True)]
    live = {}
    calls = sorted({B1 + x + 5 + struct.unpack_from('<i', ri[1], x + 1)[0] for x in range(len(ri[1]) - 5)
                    if ri[1][x] == 0xE8})
    for name, o, ln, l in hooks:                        # (the flags at the region's end: read later or not)
        fn = max((c for c in calls if c <= B1 + o), default=None)
        r_, pth = flag_liveness(ri[1], B1 + o + ln, fn=fn)
        live[name] = (r_, pth, fn)
    table, own_all, ok_e = {}, {}, True
    ex = {}
    for site in hooks:
        for mode, act, dact, n, st in modes:
            bad, first = 0, None
            for t in range(n):
                diffs, own, calls = trial(ri, ni, site, sym, lab, f'{site[0]}:{mode}:{t}', act, dact, st,
                                          live[site[0]][0] == 'dead')
                own_all.setdefault(site[0], set()).update(own) if mode.startswith('NORMAL') else None
                if diffs:
                    bad += 1
                    first = first or diffs[:4]
                if calls:
                    ex.setdefault(site[0], set()).update(hex(c[0]) for c in calls)
            table[(site[0], mode)] = (bad, n, first)
            if mode.startswith('NORMAL'):
                ok_e &= bad == 0
        print(site[0], [table[(site[0], m[0])][0] for m in modes], flush=True)
    # ---- 14/11 (Davide's corner never taken): outside live play every DRIBBLING / W1 site = the original, with
    #      PERSONALIZZATO's blocks far off (W1 on); control: the same at gameStatePl 100 differs (BU = buildup, CPU only,
    #      not gated: G1 is the keeper-holds-ball restart by design)
    nl = {}
    for site in hooks:
        if site[0] in ('KICK', 'SC', 'GK', 'PS', 'GL'):
            continue
        b0 = b1 = 0
        f0 = None
        for t in range(a.ctrl_trials):
            g = random.Random(f'g{site[0]}{t}').choice((101, 102, 0, 1, 5, 6, 13, 14, 20, 30))
            d_, _, _ = trial(ri, ni, site, sym, lab, f'{site[0]}:NL:{t}', 0, 2, True, live[site[0]][0] == 'dead', g)
            b0 += bool(d_)
            f0 = f0 or (d_[:3] if d_ else None)
            d_, _, _ = trial(ri, ni, site, sym, lab, f'{site[0]}:LV:{t}', 0, 2, True, live[site[0]][0] == 'dead', 100)
            b1 += bool(d_)
        nl[site[0]] = (b0, b1, f0)
        print('NL', site[0], b0, b1, flush=True)
    ok_nl = all(v[0] == 0 for k, v in nl.items() if not k.startswith('BU'))
    exp_hard = {'SC', 'GK', 'PS', 'GL'}
    exp_drib = {'SL', 'CAR', 'HOLD0', 'HOLD1', 'LOCKW', 'LOCKL'}
    ctl_hard = all((table[(h[0], 'DIFFICILE (control)')][0] > 0) == (h[0] in exp_hard) for h in hooks
                   if not h[0].startswith(('W1', 'BU')))
    ctl_drib = all(table[(h, 'DRIBBLING NUOVO (control)')][0] > 0 for h in exp_drib) and \
        all(table[(h, 'DRIBBLING NUOVO (control)')][0] == 0 for h in exp_hard | {'KICK'})
    L += ['## 3. Differential execution (Unicorn): differing trials / trials', '',
          'NORMAL = DF_ACT 0, DF_DACT 0 (KICK: DF_W 0, DF_DR 0, random DF_ACT / DF_DACT before, must end 0 / 0). '
          '"team pair" = A6 / ebx (/ esi at LOCK) a TeamGeneralInfo of a computer team facing a human (or the human), '
          'the team files A2 = computer, A3 = human, the sprite\'s ballDistance near the radii. Controls: expected '
          f'to differ at DIFFICILE: {sorted(exp_hard)}; at DRIBBLING NUOVO at least {sorted(exp_drib)} and never '
          'the difficulty sites.', '',
          '| site | obj1 | len | stub | ' + ' | '.join(m[0] for m in modes) + ' | NEW own state written (NORMAL) | calls out |',
          '|---|---|---|---|' + '---|' * len(modes) + '---|---|']
    for name, o, ln, l in hooks:
        cells = []
        for m in modes:
            b, n, f = table[(name, m[0])]
            cells.append(f'{b}/{n}' + (f' `{"; ".join(f)}`' if b and m[0].startswith('NORMAL') else ''))
        L.append(f'| {name} | {o:#x} | {ln} | {l} | ' + ' | '.join(cells) +
                 f' | {", ".join(sorted(own_all.get(name, ()))) or "-"} | {", ".join(sorted(ex.get(name, ()))) or "-"} |')
    L += ['', '### Flags after each region (MC: the same flags where a later Jcc reads them)', '',
          'Walk of the ORIGINAL code from the region\'s end (ndisasm): "dead" = every arithmetic flag is written '
          'before any is read (following jmp, both jcc arms, calls; at the routine\'s ret, every caller\'s '
          'continuation). Where dead, the differential ignores the flags; elsewhere they must be equal.', '',
          '| site | flags after the region | first full write / reason | instructions walked |', '|---|---|---|---|']
    for name, o, ln, l in hooks:
        r_, pth, fn = live[name]
        last = [x for x in pth if not x.startswith('  ')]
        L.append(f'| {name} | {r_ if isinstance(r_, str) else r_[0]} | '
                 f'{(last[-1] if last else "-") if r_ == "dead" else r_[1]} | {len(last)} |')
    L += ['', '## 4. Outside live play (14/11, the corner never taken): PERSONALIZZATO far off + W1 on, gameStatePl not '
          '100 must equal the original; the same at 100 (control) differs somewhere', '',
          '| site | differing trials, not live | control at 100 (live) | first diff |', '|---|---|---|---|']
    L += [f'| {k} | {v[0]}/{a.ctrl_trials} | {v[1]}/{a.ctrl_trials} | {v[2] or "-"} |' for k, v in nl.items()]
    ctl_nl = sum(v[1] for v in nl.values()) > 0
    L += ['', f'- not live: {"every DRIBBLING / W1 site equal" if ok_nl else "FAIL"} (BU = buildup, CPU only, listed); '
          f'control at 100: {"differs" if ctl_nl else "UNEXPECTED: never differs"}.']
    verdict = ok_b and ok_k and ok_e and ctl_hard and ctl_drib and ok_nl and ctl_nl
    L += ['', f'- byte diff: {"ok" if ok_b else "FAIL"}; knob table at NORMAL: {"all equal" if ok_k else "FAIL"}; '
          f'differential at NORMAL: {"every site equal in every trial" if ok_e else "FAIL"}; '
          f'DIFFICILE control: {"the expected sites differ, the others not" if ctl_hard else "UNEXPECTED"}; '
          f'DRIBBLING control: {"as expected" if ctl_drib else "UNEXPECTED"}.',
          f'- obj2 changes (listed, not in the match code): {[(hex(x), y - x) for x, y in OBJ2_OK]}', '',
          f'Verdict: **{"PASS" if verdict else "FAIL"}**', '']
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(L))
    json.dump(dict(verdict='PASS' if verdict else 'FAIL', byte=res, knobs=[list(map(str, x)) for x in rows],
                   diff={f'{k[0]}|{k[1]}': [v[0], v[1], v[2]] for k, v in table.items()}),
              open(os.path.join(d, a.out + '.json'), 'w'), indent=1)
    print('\n'.join(L))


if __name__ == '__main__':
    main()
