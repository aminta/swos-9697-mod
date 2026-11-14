"""4.2 set pieces 1+2: CLASSICI = the original game, proved on the host (the 42-drp method, diff_structural.py).

  internal/hosttest/.venv/bin/python tools/hosttest/sp_structural.py REF_BUILD NEW_BUILD [--trials N] [--out NAME]

REF_BUILD = this tree without SP_TEST, NEW_BUILD = SP_TEST=0 (the stubs in, CALCI PIAZZATI = CLASSICI).
1. Byte diff: obj1 changes only at the 11 hook regions (`call stub` + nops; FB / FT keep their branches, re-aimed),
   obj4 only in the SETPIECE band, nothing else.
2. Differential execution (Unicorn): every site, random states, REF's original instructions vs NEW's call + stub, with
   SP_W 0: registers, ESP / EIP, memory, calls out, and the flags where the original code reads them later (ndisasm
   walk). Controls with SP_W 1 (NUOVI) on states near each knob's threshold: the knob sites must differ.
Writes internal/swostest/outcome-gate/NAME.md."""
import argparse
import json
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_ESI

import diff_structural as ds
import setpieces as sp
import swreg
from lepatch import LEPatch

B1, B2, B3, B4 = ds.B1, ds.B2, ds.B3, ds.B4
ROOM = (swreg.SETPIECE_AT, swreg.SETPIECE_END)


def expected(a, o, n, l, lab, key):
    want = b'\xe8' + struct.pack('<i', B4 + lab[l] - (B1 + o + 5))
    if key == 'FB':
        f = o + 10 + struct.unpack_from('<b', a, o + 9)[0]
        nf = o + 15 + struct.unpack_from('<i', a, o + 11)[0]
        return want + struct.pack('<Bb', 0x74, f - (o + 7)) + b'\xe9' + struct.pack('<i', nf - (o + 12)) + b'\x90' * 3
    if key == 'FT':
        nf = o + 14 + struct.unpack_from('<i', a, o + 10)[0]
        return want + b'\x0f\x85' + struct.pack('<i', nf - (o + 11)) + b'\x90' * 3
    return want + b'\x90' * (n - 5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('new')
    ap.add_argument('--trials', type=int, default=300)
    ap.add_argument('--out', default='42sp-structural')
    a = ap.parse_args()
    ref_exe, new_exe = os.path.join(a.ref, 'ITALIAN.EXE'), os.path.join(a.new, 'ITALIAN.EXE')
    lab = {k: v[1] for k, v in json.load(open(os.path.join(a.new, 'ITALIAN.syms.json')))['setpieces'].items()}
    p = LEPatch(ref_exe)
    s, c = sp.find(p)
    hooks = [(k, s[k], n, l) for k, n, l in sp.HOOKS]
    ri, ni = ds.images(ref_exe), ds.images(new_exe)
    k0 = lab['sp_on']                                   # (SWOS++'s flag: sp_on's own operand, obj1)
    assert ni[4][k0:k0 + 6] == bytes.fromhex('518b4d0480b9'), ni[4][k0:k0 + 12].hex()
    swpp = (1, struct.unpack_from('<I', ni[4], k0 + 6)[0])
    ds.ROOMS = (ROOM,)                                  # (NEW's own code / state: the SETPIECE band)
    L = [f'# 42-sp set pieces: CLASSICI = original, structural: {a.out}', '', f'REF `{ref_exe}`  ',
         f'NEW `{new_exe}` (SP_TEST=0: CALCI PIAZZATI = CLASSICI)', '', '## 1. Byte diff', '']
    ok_b, blocks = True, []
    for obj in (1, 2, 3, 4):
        x, y = ri[obj], ni[obj]
        if x is None:
            continue
        if len(x) != len(y):
            L.append(f'- obj{obj}: sizes {len(x):#x} / {len(y):#x}')
            ok_b = False
            continue
        diff = [i for i in range(len(x)) if x[i] != y[i]] if x != y else []
        cover = set()
        if obj == 1:
            for k, o, n, l in hooks:
                cover |= set(range(o, o + n))
                g = bytes(y[o:o + n]) == expected(x, o, n, l, lab, k)
                ok_b &= g
                L.append(f'- obj1 {k} {o:#x}+{n}: `{bytes(x[o:o + n]).hex()}` -> `{bytes(y[o:o + n]).hex()}` '
                         f'({"ok" if g else "WRONG"})')
        elif obj == 4:
            cover = set(range(*ROOM))
        stray = ds.ranges([i for i in diff if i not in cover])
        L.append(f'- obj{obj}: {len(ds.ranges(diff))} changed ranges, {len(stray)} outside the hooks / band')
        if obj == 4 or not stray:
            ok_b &= not stray
            continue
        if obj == 1:                                    # (the version tag "TEST" moves obj1's tail: insert blocks and
            cls, bad, blocks = ds.classify(x, y, stray)  #  operands into them, as in 42drp-structural)
        else:
            cls, bad, _ = ds.classify(x, y, stray, {2: B2, 3: B3}[obj], blocks)
        L += ['  - ' + q for q in cls]
        L.append(f'  - obj{obj} unexplained: {bad or "none"}')
        ok_b &= not bad
    calls = sorted({B1 + i + 5 + struct.unpack_from('<i', ri[1], i + 1)[0] for i in range(len(ri[1]) - 5)
                    if ri[1][i] == 0xE8})
    live = {}
    for k, o, n, l in hooks:
        fn = max((q for q in calls if q <= B1 + o), default=None)
        live[k] = ds.flag_liveness(ri[1], B1 + o + n, fn=fn)
    syms = dict(D0_=(2, c['A2_O'] - 4 * 10), A2_=(2, c['A2_O']), A3_=(2, c['A2_O'] + 4), A6_=(2, c['A2_O'] + 16),
                SWOSPP=swpp, TRG=('lin', ds.SCR + 0x50000))           # (diff_structural.trial's state names; TRG unused here)
    nl = {'DF_W': lab['SP_W'], 'DF_DR': lab['SP_W'], 'DF_ACT': lab['SP_W'], 'DF_DACT': lab['SP_W'], **lab}

    def trial(site, seed, on, near):
        k = site[0]
        def prep(m):                                    # (both machines, the same draw: the knobs' inputs near
            r = random.Random(seed + 'x')               #  their thresholds)
            ball = B2 + c['BALL_O']
            m.w32(B2 + c['A2_O'], ball)
            m.w16(ball + c['ZO'], r.randrange(0, 30))
            m.w32(ball + c['DZO'], r.choice((sp.knobs()['JZ'] & 0xFFFFFFFF, r.getrandbits(32))))
            m.w16(ball + 0x20, r.randrange(100, 600))
            m.w16(B2 + c['BDZ_O'], r.randrange(8, 32))
            m.w16(B2 + c['GKA_O'], r.choice((0, 1)))
            m.w16(B2 + c['D7_O'], r.choice((1, 2, 5, 6, r.randrange(0, 8))))
            pl = ds.SCR + 0x30000
            m.w32(B2 + c['A5_O'], pl)
            m.w32(pl + 0x4A, r.randrange(400, 1100))
            m.w32(B2 + c['A4_O'], pl + 0x100)
            m.w8(pl + 0x100 + c['HDO'], r.randrange(0, 8))
            m.w8(B1 + swpp[1], 0xFF)
        diffs, own, cl = ds.trial(ri, ni, site, syms, nl, seed, on, on, False, live[k][0] == 'dead', ends[k]) \
            if not near else _near(site, seed, on, prep, live[k][0] == 'dead')
        return diffs, cl

    def _near(site, seed, on, prep, dead):
        return _trial_with_prep(ri, ni, site, syms, nl, seed, on, prep, dead, ends[site[0]])

    ends = {}                                           # (where each region is left: FB / FT end in their branches)
    for k, o, n, l in hooks:
        x = ri[1]
        if k == 'FB':
            ends[k] = (B1 + o + 10 + struct.unpack_from('<b', x, o + 9)[0], B1 + o + 15 + struct.unpack_from('<i', x, o + 11)[0])
        elif k == 'FT':
            ends[k] = (B1 + o + 14, B1 + o + 14 + struct.unpack_from('<i', x, o + 10)[0])
        else:
            ends[k] = B1 + o + n

    modes = (('CLASSICI', 0, False), ('CLASSICI, near the thresholds', 0, True), ('NUOVI (control)', 1, True))
    table = {}
    for site in hooks:
        for mode, on, near in modes:
            bad, first = 0, None
            for t in range(a.trials):
                d, _ = trial(site, f'{site[0]}:{mode}:{t}', on, near)
                if d:
                    bad += 1
                    first = first or d[:3]
            table[(site[0], mode)] = (bad, first)
        print(site[0], [table[(site[0], m[0])] for m in modes], flush=True)
    ok_e = all(table[(h[0], m)][0] == 0 for h in hooks for m in ('CLASSICI', 'CLASSICI, near the thresholds'))
    expect = {'JZ', 'FZ', 'CEIL0', 'CEIL1', 'BAND', 'GKA0', 'GKA1', 'CPU', 'FB', 'FT'}
    ok_c = all(table[(k, 'NUOVI (control)')][0] > 0 for k in expect)
    L += ['', '## 2. Differential execution: differing trials / trials', '',
          'SP_W 0 = CLASSICI (SWOS++ flag random in "CLASSICI", absent in the others). "near the thresholds" = ball z '
          '0..30, ballDefensiveZ 8..32, ballDistance 400..1100, D7 0..7, ball x 100..600, heading 0..7, deltaZ = '
          'NUOVI\'s jump value half the time. Control: SP_W 1 must differ at ' + ', '.join(sorted(expect)) + '.', '',
          '| site | obj1 | len | stub | ' + ' | '.join(m[0] for m in modes) + ' | flags after (original) |',
          '|---|---|---|---|' + '---|' * len(modes) + '---|']
    for k, o, n, l in hooks:
        cells = [f'{table[(k, m[0])][0]}/{a.trials}' + (f' `{"; ".join(table[(k, m[0])][1])}`'
                                                        if table[(k, m[0])][0] and m[1] == 0 else '') for m in modes]
        r_ = live[k][0]
        L.append(f'| {k} | {o:#x} | {n} | {l} | ' + ' | '.join(cells) + f' | {r_ if isinstance(r_, str) else r_[0]} |')
    v = ok_b and ok_e and ok_c
    L += ['', f'- byte diff: {"ok" if ok_b else "FAIL"}; CLASSICI: {"every site equal in every trial" if ok_e else "FAIL"}; '
          f'NUOVI control: {"every knob site differs" if ok_c else "UNEXPECTED"}.', '', f'Verdict: **{"PASS" if v else "FAIL"}**', '']
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(L))
    print('\n'.join(L))


def _trial_with_prep(ri, ni, site, sym, lab, seed, on, prep, dead, ends):
    import random as _r
    name, o, ln, l = site
    ms = (ds.Mach(ri, seed), ds.Mach(ni, seed))
    r = _r.Random(seed)
    regs = {n: ds.rval(r) for n, _ in ds.GPR}
    fl = 0x202 | (r.getrandbits(12) & ds.FLAGS)
    for m in ms:
        for n, rg in ds.GPR:
            m.uc.reg_write(rg, regs[n])
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.uc.reg_write(UC_X86_REG_EFLAGS, fl)
        m.read(ds.STACK - 0x100, 0x200)
        prep(m)
        m.writes.clear()
    ms[1].w8(B4 + lab['SP_W'], on)
    ms[1].writes.clear()
    start, end = B1 + o, B1 + o + ln
    reg = (start, end)
    out = []
    for m, allowed in ((ms[0], (reg,)), (ms[1], (reg, (B4 + ROOM[0], B4 + ROOM[1])))):
        log, err = ds.run(m, start, ends, allowed)
        out.append((ds.state(m), log, err))
    (sa, la, ea), (sb, lb, eb) = out
    diffs = []
    if ea or eb:
        diffs.append(f'run: REF {ea} / NEW {eb}')
    for k in sa:
        if sa[k] != sb[k] and not (k == 'flags' and dead):
            diffs.append(f'{k} {sa[k]:#x} / {sb[k]:#x}')
    if la != lb:
        diffs.append('calls out differ')
    esp = min(sa['esp'], sb['esp'])
    for adr in ms[0].writes | ms[1].writes:
        if ds.STACK - 0x1000 <= adr < esp or B4 + ROOM[0] <= adr < B4 + ROOM[1]:
            continue
        if ms[0].read(adr, 1) != ms[1].read(adr, 1):
            diffs.append(f'mem {adr:#x}')
            break
    return diffs, [], la


if __name__ == '__main__':
    main()
