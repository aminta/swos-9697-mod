"""4.2 set pieces 1+2: CLASSICI = the original game, proved on the host (the 42-drp method, diff_structural.py).

  internal/hosttest/.venv/bin/python tools/hosttest/sp_structural.py REF_BUILD NEW_BUILD [--trials N] [--out NAME]

REF_BUILD = this tree without SP_TEST, NEW_BUILD = SP_TEST=0 (the stubs in, CALCI PIAZZATI = CLASSICI).
1. Byte diff: obj1 changes only at the hook regions (11 + §3's KD / GR / AT / BLO) (`call stub` + nops; FB / FT keep their branches, re-aimed),
   obj4 only in the SETPIECE band, nothing else.
2. Differential execution (Unicorn): every site, random states, REF's original instructions vs NEW's call + stub, with
   SP_W 0: registers, ESP / EIP, memory, calls out, and the flags where the original code reads them later (ndisasm
   walk). Controls with SP_W 1 (NUOVI) on states near each knob's threshold: the knob sites must differ.
Writes internal/swostest/outcome-gate/NAME.md."""
import argparse
import collections
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
DF_AREAS = ((swreg.DIFF_AT, swreg.DIFF_END), (swreg.DRIB1V1_AT, swreg.DRIB1V1_END))
AIMED = DF_AREAS + (ROOM,)        # (the engine's after-load calls: df_load / df_new -> sp_load_j / sp_new_j)


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
    p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))   # (the sites: REF may carry difficulty's hooks)
    s, c = sp.find(p)
    hooks = [(k, s[k], n, l) for k, n, l in sp.HOOKS]
    ri, ni = ds.images(ref_exe), ds.images(new_exe)
    k0 = lab['sp_on'] + 5                               # (the training flag: sp_on's own operand, obj2)
    assert ni[4][k0:k0 + 7] == bytes.fromhex('518b4d006683b9'), ni[4][k0:k0 + 12].hex()
    trg = (2, struct.unpack_from('<I', ni[4], k0 + 7)[0])
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
        if not stray:
            continue
        if obj == 4:                                    # (difficulty.py's code: page 15 relaid by the OPTIONS row's
            dfa = [r for r in stray if any(lo <= r[0] and r[1] <= hi for lo, hi in DF_AREAS)]   #  move, MC 14/11)
            bad = [(hex(r[0]), r[1] - r[0]) for r in stray if r not in dfa]
            L.append(f'  - {len(dfa)} inside difficulty\'s own areas (page 15, the 42-drp band): its code relaid')
            L.append(f'  - obj4 unexplained: {bad or "none"}')
            ok_b &= not bad
            continue
        base = {1: B1, 2: B2, 3: B3}[obj]
        dfr = []                                        # (operands - abs or rel32 - aimed into difficulty's areas in
        for r in stray:                                 #  both: its hooks' calls, the OPTIONS init / return)
            for w in range(r[0] - 3, r[0] + 1):
                if w + 4 < r[1] or w < 0:
                    continue
                va, vb = struct.unpack_from('<I', x, w)[0], struct.unpack_from('<I', y, w)[0]
                tg = [(v - B4, (base + w + 4 + v - B4) & 0xFFFFFFFF) for v in (va, vb)]
                if all(any(lo <= t[0] < hi for lo, hi in AIMED) for t in tg) or \
                        all(any(lo <= t[1] < hi for lo, hi in AIMED) for t in tg):
                    dfr.append(r)
                    break
        if dfr:
            L.append(f'  - {len(dfr)} operands aimed into difficulty\'s relaid code in both (its hooks\' calls, OPTIONS '
                     f'init / return): {[hex(u) for u, v in dfr]}')
        stray = [r for r in stray if r not in dfr]
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
                SWOSPP=('lin', ds.SCR + 0x50000), TRG=trg)           # (diff_structural.trial's state names; SWOSPP unused)
    nl = {'DF_W': lab['SP_W'], 'DF_DR': lab['SP_W'], 'DF_ACT': lab['SP_OK'], 'DF_DACT': lab['SP_OK'], **lab}

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
            m.w16(B2 + trg[1], 0)
            if 'FK_ST' in lab:                          # (§3 free kicks: the kick record's inputs and the band's state)
                tm = ds.SCR + 0x34000
                m.w32(B2 + c['A6T_O'], tm)
                m.w32(B4 + lab['FK_TM'], r.choice((tm, tm + 0x91)))
                m.w16(tm + 4, r.choice((0, 1)))
                m.w16(tm + 0x38, r.randrange(0, 8))
                m.w16(tm + 0x76, r.choice((0, 3, 9, 0xFFFF)))
                m.w32(tm + 0x0A, pl + 0x200)
                m.w32(B2 + c['A1_O'], pl + 0x400)
                m.w16(pl + 0x402, r.randrange(1, 12))
                m.w16(B2 + c['GS_O'], r.choice((3, 6, 9, 12, 13, 100)))
                m.w16(B2 + c['GSP_O'], r.choice((100, 101, 102)))
                m.w16(ball + 0x24, r.randrange(120, 780))
                m.w16(ball + 0x1E, r.getrandbits(16))
                m.w32(ball + 0x32, r.randrange(-0x30000, 0x30000) & 0xFFFFFFFF)
                m.w8(B4 + lab['FK_ST'], r.choice((0, 1, 2, 2)))
                m.w8(B4 + lab['FK_CU'], r.choice((0, 1, 2)))
                m.w8(B4 + lab['FK_SH'], r.randrange(0, 5))
                m.w8(B4 + lab['FK_UP'], r.choice((0, 1)))
                m.w16(B4 + lab['FK_Y0'], r.randrange(200, 700))
                m.w16(B4 + lab['FK_N'], r.randrange(0, 110))
                m.w32(B4 + lab['FK_E'], r.randrange(-4096, 8192) & 0xFFFFFFFF)
        diffs, own, cl = ds.trial(ri, ni, site, syms, nl, seed, 1, 1, False, live[k][0] == 'dead', ends[k]) \
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
    expect = {'JZ', 'FZ', 'CEIL0', 'CEIL1', 'BAND', 'GKA0', 'GKA1', 'CPU', 'FB', 'FT', 'GR', 'AT', 'BLO'}
    # (KD: NUOVI writes only the band's own state - excluded from the memory diff - so it differs nowhere; its record is
    #  checked by fk_check below)
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
    ok_s, sl = save_check(ni, json.load(open(os.path.join(a.new, 'ITALIAN.syms.json'))), lab)
    L += ['', '## 3. The save item (bits 6-7 of \'DF\'): df_pack, sp_load_j, sp_new_j on the host', ''] + sl
    ok_f, fl_ = fk_check(ni, lab, c, trg)
    L += ['', '## 4. §3 free kicks on the host (NUOVI): sp_kick / sp_grav / sp_at / sp_blo', ''] + fl_
    v = ok_b and ok_e and ok_c and ok_s and ok_f
    L += ['', f'- byte diff: {"ok" if ok_b else "FAIL"}; CLASSICI: {"every site equal in every trial" if ok_e else "FAIL"}; '
          f'NUOVI control: {"every knob site differs" if ok_c else "UNEXPECTED"}.', '', f'Verdict: **{"PASS" if v else "FAIL"}**', '']
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(L))
    print('\n'.join(L))


def save_check(ni, sj, lab):
    """df_pack (moved here): DF_SV = DF_SH = W | DR << 4 | SP_W << 6 for every W 0..4, DR 0..2, SP 0..2; sp_load_j /
    sp_new_j: SP_W = bits 6-7 of DF_SV / DF_SH (3 -> 0; every byte), then on to difficulty's df_load / df_new."""
    d = {k: v[1] for k, v in sj['difficulty'].items()}
    R = B4 + swreg.SETPIECE_END - 16                   # (a return address nobody jumps to: the run's end)
    allowed = tuple((B4 + lo, B4 + hi) for lo, hi in AIMED)
    bad, n = [], 0

    def go(entry, end, prep):
        m = ds.Mach(ni, 'save')
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.w32(ds.STACK, R)
        prep(m)
        log, err = ds.run(m, B4 + entry, end, allowed)
        return m, log, err
    for w in range(5):
        for dr in range(3):
            for sp_ in range(3):
                def prep(m):
                    m.w16(B4 + d['DF_W'], w)
                    m.w16(B4 + d['DF_DR'], dr)
                    m.w16(B4 + lab['SP_W'], sp_)
                m, log, err = go(lab['df_pack'], R, prep)
                want = w | dr << 4 | sp_ << 6
                got = (m.read(B4 + d['DF_SV'], 1)[0], m.read(B4 + d['DF_SH'], 1)[0])
                n += 1
                if err or log or got != (want, want):
                    bad.append(f'df_pack W {w} DR {dr} SP {sp_}: {got} {err} {log[:1]}')
    for lbl, src, dst in (('sp_load_j', 'DF_SV', 'df_load'), ('sp_new_j', 'DF_SH', 'df_new')):
        for byte in range(256):
            def prep(m):
                m.w8(B4 + d[src], byte)
                m.w16(B4 + lab['SP_W'], 0x5A5A)
            m, log, err = go(lab[lbl], B4 + d[dst], prep)
            n += 1
            got = struct.unpack('<H', m.read(B4 + lab['SP_W'], 2))[0]
            if err or log or got != ((byte >> 6) & 3 if (byte >> 6) & 3 < 3 else 0) or m.read(B4 + d[src], 1)[0] != byte:
                bad.append(f'{lbl} {src} {byte:#x}: SP_W {got:#x} {err}')
    return not bad, [f'- {n} cases: {"all as wanted" if not bad else "FAIL"}'] + [f'  - {b}' for b in bad[:10]]


def fk_check(ni, lab, c, trg):
    """§3 on the host, NUOVI: sp_kick records a wall-zone free kick (SHOOTING weight, side, start); sp_grav flown tick by
    tick with the game's ball rules (tools/fkmodel.py) brings a cleared kick to its target FK_TT = SP_FKT +- the
    SHOOTING aim error (SP_FKW px) at the line, nothing for a drive; sp_at holds facing +- 2 on the open side; sp_blo raises the low bound."""
    from unicorn.x86_const import UC_X86_REG_EAX
    import fkmodel
    k = sp.knobs()
    R = B4 + swreg.SETPIECE_END - 16
    allowed = ((B4 + ROOM[0], B4 + ROOM[1]),)
    tm, pl = ds.SCR + 0x34000, ds.SCR + 0x30000
    ball = B2 + c['BALL_O']
    bad, rows, n = [], [], 0

    def mach(seed):
        m = ds.Mach(ni, seed)
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.w32(ds.STACK, R)
        m.w16(B4 + lab['SP_W'], 1)
        m.w8(B4 + lab['SP_OK'], 1)
        m.w16(B2 + trg[1], 0)
        return m

    def call(m, entry):
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.w32(ds.STACK, R)
        log, err = ds.run(m, B4 + lab[entry], R, allowed)
        return log, err

    def kick(m, sh, y, x=336, cpu=0, gs=9, gsp=101):
        m.w32(B2 + c['A6T_O'], tm)
        m.w16(tm + 4, 0 if cpu else 1)
        m.w32(tm + 0x0A, pl)
        m.w32(B2 + c['A1_O'], pl + 0x400)
        m.w16(pl + 0x402, 10)
        m.w8(pl + 9 * 61 + c['HDO'] - 1, sh)
        m.w16(B2 + c['GS_O'], gs)
        m.w16(B2 + c['GSP_O'], gsp)
        m.w16(ball + 0x24, y)
        m.w16(ball + 0x20, x)
        return call(m, 'sp_kick')
    b8 = lambda m, l: m.read(B4 + lab[l], 1)[0]
    for sh in range(8):
        for dist in (90, 100, 125, 150, 175, 200):
            for kind in ('normal', 'normal_diag', 'high', 'high_diag', 'drive'):
                m = mach(f'fk{sh}{dist}{kind}')
                log, err = kick(m, sh, 129 + dist)
                n += 1
                w = k['FKW'][sh]
                if err or log or (b8(m, 'FK_ST'), b8(m, 'FK_SH'), b8(m, 'FK_UP'), b8(m, 'FK_CU')) != (1, w, 1, 0):
                    bad.append(f'kick sh {sh} d {dist}: {err} st {b8(m, "FK_ST")} sh {b8(m, "FK_SH")}')
                    continue
                # the flight (UpdateBall per tick: z += dz - g', y moves speed / 512 x 41 / 64 px)
                z, dz, sp_, yy, extra_used = 0, 0x14000, 2208, float(129 + dist), 0
                zl = None
                for t in range(1, 120):
                    if t == 4 and kind != 'drive':
                        dz, sp_ = (0x16000, 2560) if kind.startswith('normal') else (0x20000, 2688)
                        sp_ = sp_ - (sp_ >> 2) + (sp_ >> 3 if kind.endswith('diag') else 0)
                    sp_ = max(0, sp_ - 4)
                    step = sp_ / 512 * 41 / 64
                    m.w16(ball + 0x24, int(yy))
                    m.w32(ball + 0x32, -int(step * 65536))
                    m.w32(ball + 0x26, z)
                    m.w32(ball + 0x36, dz)
                    m.uc.reg_write(UC_X86_REG_EAX, 0)
                    log, err = call(m, 'sp_grav')
                    g = m.uc.reg_read(UC_X86_REG_EAX)
                    g = g - (1 << 32) if g & 0x80000000 else g
                    if err or log:
                        bad.append(f'grav sh {sh} d {dist} {kind} t {t}: {err}')
                        break
                    extra_used = max(extra_used, abs(g - 3291))
                    dz = (dz - g) | 1
                    z += dz
                    ny = yy - step
                    if ny <= 129:
                        zl = (z / 65536)
                        break
                    yy = ny
                    if z < 0:
                        zl = -1
                        break
                ref = fkmodel.z_at(fkmodel.fly(kind), dist) if kind in ('normal', 'normal_diag', 'drive') else None
                rows.append((sh, dist, kind, zl, ref, b8(m, 'FK_ST')))
                if kind == 'drive' and extra_used:
                    bad.append(f'drive dipped: sh {sh} d {dist}')
                tt = int.from_bytes(m.read(B4 + lab['FK_TT'], 4), 'little', signed=True) / 65536
                if not (k['FKT'] / 65536 - w <= tt <= k['FKT'] / 65536 + w):
                    bad.append(f'aim target off: sh {sh} d {dist} {kind}: FK_TT {tt} (amplitude {w})')
                if kind.startswith('high') and 100 <= dist <= 175 and not (zl is not None and zl <= tt + 3 and
                                                                          (dist > 150 or abs(zl - tt) <= 3)):
                    bad.append(f'high kick not at its target: sh {sh} d {dist} {kind}: z at the line {zl}, target {tt}')
    for case, args, want in (('in play', dict(gsp=100), 0), ('corner state', dict(gs=4), 0), ('too far', dict(y=129 + 210), 0),
                             ('too close', dict(y=129 + 80), 0), ('bottom goal', dict(y=769 - 120), 1)):
        m = mach('c' + case)
        kick(m, 7, **{'y': 129 + 120, **args})
        n += 1
        if b8(m, 'FK_ST') != want or (want and b8(m, 'FK_UP') != (0 if case == 'bottom goal' else 1)):
            bad.append(f'kick gate {case}: FK_ST {b8(m, "FK_ST")}')
    cu = collections.Counter()
    for i in range(400):                                 # (the CPU: 1 in 2 curls; the far side from the ball's x)
        x = (290, 336, 382)[i % 3]
        m = mach(f'cpu{i}')
        m.w32(B4 + lab['FK_R'], i * 7919)
        m.w16(ball + 0x1E, i * 2654435761 & 0xFFFF)
        kick(m, 7, 129 + 120, x=x, cpu=1)
        cu[(x, b8(m, 'FK_CU'))] += 1
        for face in (0, 1, 7, 4):
            m.w16(tm + 0x38, face)
            m.w16(tm + 0x76, 2)
            m.w16(tm + 0x2C, 0xFFFF)
            m.w32(B4 + lab['FK_TM'], tm)
            call(m, 'sp_at')
            got = struct.unpack('<H', m.read(tm + 0x2C, 2))[0]
            u = b8(m, 'FK_CU')
            c1, c2 = (face + 3) & 7, (face + 5) & 7
            want = 0xFFFF if not u else c1 if (1 if 1 <= c1 <= 3 else 2 if c1 >= 5 else 0) == u else c2
            n += 1
            if got != want:
                bad.append(f'sp_at face {face} cu {u}: {got:#x} want {want:#x}')
    for x in (290, 382):
        side = 1 if x < 324 else 2
        if cu[(x, 3 - side)]:
            bad.append(f'curl toward the near side from x {x}: {cu[(x, 3 - side)]}')
    tot = sum(cu.values())
    share = sum(v for (x, u), v in cu.items() if u) / tot
    if not 0.4 <= share <= 0.6:
        bad.append(f'CPU curl share {share:.2f}')
    for st, z, want in ((2, 13, 'no'), (2, 14, 'yes'), (1, 13, 'yes'), (0, 13, 'yes'), (2, 12, 'no')):
        m = mach(f'blo{st}{z}')
        m.w8(B4 + lab['FK_ST'], st)
        m.w16(B2 + c['BDZ_O'], z)
        call(m, 'sp_blo')
        fl = m.uc.reg_read(UC_X86_REG_EFLAGS)
        jle = bool(fl & 0x40) or bool(fl & 0x80) != bool(fl & 0x800)
        n += 1
        if ('no' if jle else 'yes') != want:
            bad.append(f'sp_blo ST {st} z {z}: catch {"no" if jle else "yes"}')
    tab = ['', 'z at the line: the bar is 15, a wall header needs z 8..17; -1 = the ball lands before the line.', '',
           '| SHOOTING | dist px | kick | z at the line (stub) | today (fkmodel) |', '|---|---|---|---|---|']
    for sh, dist, kind, zl, ref, _ in rows:
        if kind in ('normal', 'high', 'high_diag') and sh in (0, 4, 6, 7):
            tab.append(f'| {sh} | {dist} | {kind} | {"-" if zl is None else f"{zl:.1f}"} | '
                       f'{"-" if ref is None else f"{ref:.1f}"} |')
    out = [f'- {n} cases: {"all as wanted" if not bad else "FAIL"}; CPU curl share {share:.2f}'] + \
        [f'  - {b}' for b in bad[:12]] + tab
    return not bad, out


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
    ms[1].w16(B4 + lab['SP_W'], on)
    ms[1].w8(B4 + lab['SP_OK'], 1)
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
