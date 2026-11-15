"""4.2 set-piece takers: TIRATORI AUTOMATICI (TK_W 0) = the original game, proved on the host (MC 15/11 gate before the
takers sha; the 42-drp method, diff_structural.py / sp_structural.py).

  internal/hosttest/.venv/bin/python tools/hosttest/tk_structural.py REF_BUILD NEW_BUILD [--trials N] [--out NAME]

REF_BUILD = the tree without takers (42-int), NEW_BUILD = with takers, TK_W 0 (no TAKERS_TEST); both built with
HOSTTEST_SYMS=1 and the same MODVER_TAG.
1. Byte diff: obj1 changes only at the two hook regions (ORD: UpdatePlayers' kicking-team ordinal, 16 B; CTL:
   UpdateControlledPlayer @@check_closest_active_player, 10 B), each `call stub` + nops; obj2 / obj3 unchanged; obj4
   only in the TAKERS / TKUI bands, the SETPIECE band (sp_set's `ret` -> `jmp tk_kick`) and the engine's own code (the
   career save item TK: its old-save behaviour is the harness's oldsave trio).
2. Differential execution (Unicorn), both hook sites, REF's original instructions vs NEW's call + stub:
   a. random machine states (every register, memory and the band's own TK_CT / TK_CTT / TK_CG at random: a stale taker
      of an earlier match), TK_W 0;
   b. "armed" states - a break of the kicking team where TK_W 1 swaps the taker (ORD) or holds him controlled (CTL) -
      with TK_W 0, with TK_W 1 in a training game that is no practice, with TK_W 1 under SWOS++ (SP_OK 0): all equal;
   c. control: the same armed states with TK_W 1: must differ in every trial.
   Equal = every register, ESP / EIP, the flags where the original code reads them later, every memory byte either
   wrote outside NEW's own bands and the dead stack, the calls out.
3. tk_kick (sp_set's tail): every register and flag kept, writes only inside the TAKERS band.
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

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_EIP

import diff_structural as ds
import swreg
from lepatch import LEPatch

B1, B2, B3, B4 = ds.B1, ds.B2, ds.B3, ds.B4
TAK = (swreg.TAKERS_AT, swreg.TAKERS_END)
TKUI = (swreg.TKUI_AT, swreg.TKUI_END)
SETP = (swreg.SETPIECE_AT, swreg.SETPIECE_END)
SPX = (swreg.SPX_AT, swreg.SPX_END)
OWN = (TAK, TKUI)
TRL = [None]


def game_syms(orig):
    """The obj2 offsets the stubs read, from the original exe (takers' own finders)."""
    import difficulty as df
    import gkinj
    import setpieces as sp
    import takers
    p = LEPatch(orig)
    _, sym = df.find(p)
    sym['TRG'] = gkinj.find(p)['TRG']
    df.SYMS.clear()
    df.SYMS.update(sym)
    site, c = takers.find(p)
    csite, cc = takers.find_ctl(p)
    c.update(cc)
    c['GS_O'] = sp.find(p)[1]['GS_O']
    c['TRG_O'] = sym['TRG'][1]
    return {'ORD': site, 'CTL': csite}, c


def bss_moved(x, y, r, grow, top):
    """A changed range explained as a 32-bit operand into the engine's .bss above obj4's file pages, moved by `grow`
    (NEW's obj4 has the TKUI pages: the .bss after them starts that much higher)."""
    for w in range(max(0, r[0] - 3), r[0] + 1):
        if w + 4 < r[1] or w + 4 > len(x):
            continue
        va, vb = struct.unpack_from('<I', x, w)[0], struct.unpack_from('<I', y, w)[0]
        if (vb - va) & 0xFFFFFFFF == grow and B4 + top <= va < B4 + top + 0x100000:
            return True
    return False


def moved_into(x, y, r, base, lo, hi, d=None):
    """A changed range explained as an operand (absolute, or rel32 from `base`, the operand's object) aimed into
    lo..hi (linear) in REF and moved by d (None: 1..0xFF) in NEW."""
    for w in range(max(0, r[0] - 3), r[0] + 1):
        if w + 4 < r[1] or w + 4 > len(x):
            continue
        va, vb = struct.unpack_from('<I', x, w)[0], struct.unpack_from('<I', y, w)[0]
        dv = (vb - va) & 0xFFFFFFFF
        if not (dv == d if d is not None else 0 < dv < 0x100):
            continue
        if lo <= va < hi or lo <= (base + w + 4 + va) & 0xFFFFFFFF < hi:
            return True
    return False


def trailer_at(build):
    """The engine's .CAR trailer code (obj1 offset) from the build log (engine.py: its save-item tables)."""
    import re
    m = re.search(r'\.CAR trailer .*? @ obj1\+(0x[0-9a-f]+)', open(os.path.join(build, '..', 'build.log')).read())
    return int(m.group(1), 16) if m else None


def run_site(img, start, end, allowed, regs, fl, seed, prep):
    m = ds.Mach(img, seed)
    for n, rg in ds.GPR:
        m.uc.reg_write(rg, regs[n])
    m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
    m.uc.reg_write(UC_X86_REG_EFLAGS, fl)
    m.read(ds.STACK - 0x100, 0x200)
    prep(m)
    m.writes.clear()
    log, err = ds.run(m, start, end, allowed)
    return m, log, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('new')
    ap.add_argument('--trials', type=int, default=400)
    ap.add_argument('--out', default='42tk-structural')
    a = ap.parse_args()
    ref_exe, new_exe = os.path.join(a.ref, 'ITALIAN.EXE'), os.path.join(a.new, 'ITALIAN.EXE')
    sj = json.load(open(os.path.join(a.new, 'ITALIAN.syms.json')))
    lab = {k: v[1] for k, v in sj['takers'].items()}
    spl = {k: v[1] for k, v in sj['setpieces'].items()}
    sites, c = game_syms(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
    hooks = [('ORD', sites['ORD'], 16, 'tk_ord'), ('CTL', sites['CTL'], 10, 'tk_ctl')]
    ri, ni = ds.images(ref_exe), ds.images(new_exe)
    L = [f'# 42 takers: TIRATORI AUTOMATICI (TK_W 0) = original, structural: {a.out}', '', f'REF `{ref_exe}`  ',
         f'NEW `{new_exe}` (TK_W {ni[4][lab["TK_W"]]} at start)', '', '## 1. Byte diff', '']
    ok_b = ni[4][lab['TK_W']] == 0
    if not ok_b:
        L.append('- NEW starts at TK_W 1: build it without TAKERS_TEST')
    grow = len(ni[4]) - len(ri[4])
    top = len(ri[4])
    tr = trailer_at(a.new)
    assert tr is not None and tr == trailer_at(a.ref), ('trailer', tr, trailer_at(a.ref))
    for obj in (1, 2, 3, 4):
        x, y = ri[obj], ni[obj]
        if x is None and y is None:
            continue
        if len(x) != len(y):
            L.append(f'- obj{obj}: sizes {len(x):#x} / {len(y):#x}')
            if obj != 4 or len(y) < len(x) or any(y[len(x):]) and any(
                    not any(lo <= i < hi for lo, hi in OWN) for i in range(len(x), len(y)) if y[i]):
                ok_b = False
                continue
            y = y[:len(x)]
        diff = [i for i in range(len(x)) if x[i] != y[i]] if x != y else []
        if obj == 1:
            cover = set()
            for k, o, n, l in hooks:
                cover |= set(range(o, o + n))
                want = b'\xe8' + struct.pack('<i', B4 + lab[l] - (B1 + o + 5)) + b'\x90' * (n - 5)
                g = bytes(y[o:o + n]) == want
                ok_b &= g
                L.append(f'- obj1 {k} {o:#x}+{n}: `{bytes(x[o:o + n]).hex()}` -> `{bytes(y[o:o + n]).hex()}` '
                         f'({"ok" if g else "WRONG"})')
            stray = ds.ranges([i for i in diff if i not in cover])
            bss = [r for r in stray if bss_moved(x, y, r, grow, top)]
            spm = [r for r in stray if r not in bss and moved_into(x, y, r, B1, B4 + SETP[0], B4 + SETP[1])]
            rest = [r for r in stray if r not in bss and r not in spm]
            te = tr                                     # (the trailer: its first change from tr, gaps < 0x400)
            for u, v in rest:
                if te <= u < te + 0x400 or u >= tr and u - te < 0x400:
                    te = max(te, v)
            trl = [r for r in rest if tr <= r[0] < te]
            rest = [r for r in rest if r not in trl]
            tro = [r for r in rest if moved_into(x, y, r, B1, B1 + tr, B1 + te + 0x2000)]
            bad = [r for r in rest if r not in tro]
            TRL[0] = (tr, te)
            L.append(f'- obj1: {len(ds.ranges(diff))} changed ranges: 2 hooks, {len(bss)} operands into the engine\'s '
                     f'.bss moved by +{grow:#x} (obj4\'s TKUI pages), {len(spm)} calls / operands into the SETPIECE band moved by +4 / +9 (sp_set\'s `ret` -> `jmp tk_kick`, sp_load_j\'s `call tk_load`), {len(tro)} operands into the trailer\'s data moved, {len(trl)} in the .CAR trailer obj1+{tr:#x}..'
                     f'{te:#x} (engine.py\'s save-item tables: + TK, its loads / saves = the oldsave trio); unexplained '
                     f'{[(hex(u), v - u) for u, v in bad] or "none"}')
            ok_b &= not bad
        elif obj in (2, 3):
            rr = ds.ranges(diff)
            ob = B2 if obj == 2 else B3
            bad = [r for r in rr if not bss_moved(x, y, r, grow, top) and not
                   moved_into(x, y, r, ob, B4 + SETP[0], B4 + SETP[1]) and not
                   moved_into(x, y, r, ob, B1 + TRL[0][0], B1 + TRL[0][1] + 0x2000)]
            L.append(f'- obj{obj}: {len(rr)} changed ranges, {len(rr) - len(bad)} operands into the .bss (+{grow:#x}), the '
                     f'SETPIECE band (+4) or the trailer\'s data; unexplained {[(hex(u), v - u) for u, v in bad] or "none"}')
            ok_b &= not bad
        else:
            rr = ds.ranges(diff)
            where = {'TAKERS': 0, 'TKUI': 0, 'SETPIECE': 0, 'engine': 0}
            bad = []
            eng_hi = min(swreg.DIFF_AT, swreg.SETPIECE_AT)       # (the engine's C code and data: below every band)
            for u, v in rr:
                k = 'TAKERS' if TAK[0] <= u < TAK[1] else 'TKUI' if TKUI[0] <= u < TKUI[1] else \
                    'SETPIECE' if SETP[0] <= u < SETP[1] else 'engine' if u < eng_hi else None
                if k is None and bss_moved(x, y, (u, v), grow, top):
                    where['.bss operands'] = where.get('.bss operands', 0) + 1
                elif k is None and SPX[0] <= u < SPX[1] and moved_into(x, y, (u, v), 0, SETP[0] - spl['SPB'],
                                                                     SETP[1] - spl['SPB']):
                    where['SPX: [ebp + label - SPB] moved'] = where.get('SPX: [ebp + label - SPB] moved', 0) + 1
                elif k is None and moved_into(x, y, (u, v), B4, B4 + SETP[0], B4 + SETP[1]):
                    where['operands into SETPIECE moved'] = where.get('operands into SETPIECE moved', 0) + 1
                elif k is None and moved_into(x, y, (u, v), B4, B1 + TRL[0][0], B1 + TRL[0][1] + 0x2000):
                    where['operands into the trailer'] = where.get('operands into the trailer', 0) + 1
                elif k is None:
                    bad.append((hex(u), v - u))
                else:
                    where[k] += 1
            L.append(f'- obj4: {len(rr)} changed ranges: {where}; unexplained {bad or "none"}')
            ok_b &= not bad
            sp_set = [i for i in range(SETP[0], SETP[1] - 5) if y[i] == 0xE9 and
                      i + 5 + struct.unpack_from('<i', y, i + 1)[0] == TAK[0]]
            L.append(f'  - SETPIECE: `jmp tk_kick` at {[hex(i) for i in sp_set]} (sp_set\'s tail; one wanted)')
            ok_b &= len(sp_set) == 1
    # ---- 2. differential execution
    live = {}
    calls = sorted({B1 + i + 5 + struct.unpack_from('<i', ri[1], i + 1)[0] for i in range(len(ri[1]) - 5)
                    if ri[1][i] == 0xE8})
    for k, o, n, l in hooks:
        fn = max((q for q in calls if q <= B1 + o), default=None)
        live[k] = ds.flag_liveness(ri[1], B1 + o + n, fn=fn)[0] == 'dead'
    TM, IG, SPR, SPT, PL = ds.SCR + 0x34000, ds.SCR + 0x36000, ds.SCR + 0x38000, ds.SCR + 0x39000, ds.SCR + 0x3A000

    def arm(m, k, w, trg, spok, r):
        """A break of the kicking team that TK_W 1 acts on (ORD: free kick CENTER, T = ordinal 4 swapped in for N 10;
        CTL: TK_CT = 4 of this team and gameState, A3 random)."""
        m.w8(B4 + lab['TK_W'], w)
        m.w16(B2 + c['TRG_O'], trg)
        m.w32(B4 + spl['PR_D'], 0)
        m.w8(B4 + spl['SP_OK'], spok)
        m.w32(B2 + c['A6_O'], TM)
        m.w32(B2 + c['LTP_O'], TM)
        m.w32(TM + 0x0A, IG)
        m.w32(TM + 0x14, SPR)
        for i in range(11):
            m.w32(SPR + 4 * i, SPT + 0x80 * i)
            m.w16(SPT + 0x80 * i + 0x6C, 0)
            m.w8(IG + 42 + 1 + 61 * i, 0x40 + i)
        gs = 10                                         # (free kick CENTER: NEAR 10, ROLE 0)
        m.w16(B2 + c['GS_O'], gs)
        if k == 'ORD':
            m.w32(B4 + lab['TK_SIDE'], IG)
            m.w32(B4 + lab['TK_SIDE'] + 4, 0)
            m.w8(B4 + lab['TK_TAB'], 0x40 + 3)          # (side 0, role 0, pick 1: ordinal 4's file index)
            m.w32(B2 + c['A1_O'], PL)
            m.w16(PL + 2, 4)
        else:
            m.w16(TM + c['BOOP'], r.randrange(1, 0x10000))
            m.w8(B4 + lab['TK_CT'], 4)
            m.w32(B4 + lab['TK_CTT'], TM)
            m.w8(B4 + lab['TK_CG'], gs - 4)
            m.w32(B2 + c['A3_O'], ds.SCR + 0x3F000)

    def trial(site, seed, mode):
        k, o, n, l = site
        r = random.Random(seed)
        regs = {nm: ds.rval(r) for nm, _ in ds.GPR}
        fl = 0x202 | (r.getrandbits(12) & ds.FLAGS)
        stale = (r.randrange(0, 12), ds.rval(r), r.randrange(0, 11))

        def prep_new(m):
            if mode == 'random':
                m.w8(B4 + lab['TK_W'], 0)
                m.w8(B4 + lab['TK_CT'], stale[0])
                m.w32(B4 + lab['TK_CTT'], stale[1])
                m.w8(B4 + lab['TK_CG'], stale[2])
            else:
                w, trg, spok = {'armed TK_W 0': (0, 0, 1), 'armed TK_W 1, training': (1, 1, 1),
                                'armed TK_W 1, SWOS++': (1, 0, 0), 'TK_W 1 (control)': (1, 0, 1)}[mode]
                arm(m, k, w, trg, spok, random.Random(seed + 'a'))

        def prep_ref(m):
            if mode != 'random':
                arm(m, k, 0, 0, 0, random.Random(seed + 'a'))   # (the same game memory; REF has no band)
        reg = (B1 + o, B1 + o + n)
        mr, lr, er = run_site(ri, B1 + o, B1 + o + n, (reg,), regs, fl, seed, prep_ref)
        mn, ln_, en = run_site(ni, B1 + o, B1 + o + n, (reg,) + tuple((B4 + u, B4 + v) for u, v in OWN), regs, fl,
                               seed, prep_new)
        d = []
        if er or en:
            d.append(f'run: REF {er} / NEW {en}')
        sa, sb = ds.state(mr), ds.state(mn)
        for q in sa:
            if sa[q] != sb[q] and not (q == 'flags' and live[k]):
                d.append(f'{q} {sa[q]:#x} / {sb[q]:#x}')
        if lr != ln_:
            d.append('calls out differ')
        esp = min(sa['esp'], sb['esp'])
        for adr in sorted(mr.writes | mn.writes):
            if ds.STACK - 0x1000 <= adr < esp or any(B4 + u <= adr < B4 + v for u, v in OWN):
                continue
            if mr.read(adr, 1) != mn.read(adr, 1):
                d.append(f'mem {adr:#x}')
                break
        return d
    modes = ('random', 'armed TK_W 0', 'armed TK_W 1, training', 'armed TK_W 1, SWOS++', 'TK_W 1 (control)')
    table = {}
    for site in hooks:
        for mode in modes:
            bad, first = 0, None
            for t in range(a.trials):
                d = trial(site, f'{site[0]}:{mode}:{t}', mode)
                if d:
                    bad += 1
                    first = first or d[:3]
            table[(site[0], mode)] = (bad, first)
        print(site[0], [table[(site[0], m)][0] for m in modes], flush=True)
    ok_e = all(table[(h[0], m)][0] == 0 for h in hooks for m in modes[:4])
    ok_c = all(table[(h[0], modes[4])][0] == a.trials for h in hooks)
    L += ['', '## 2. Differential execution: differing trials / trials', '',
          '"random": every register and memory byte random, TK_W 0, the band\'s TK_CT / TK_CTT / TK_CG random (a stale '
          'taker). "armed": a break of the kicking team that TK_W 1 acts on (ORD: free kick CENTER, the pick = '
          'ordinal 4, N 10; CTL: TK_CT 4 of this team and gameState). Control: TK_W 1 must differ in every trial.', '',
          '| site | obj1 | len | stub | ' + ' | '.join(modes) + ' | flags after |', '|---|---|---|---|' + '---|' * len(modes) + '---|']
    for k, o, n, l in hooks:
        cells = [f'{table[(k, m)][0]}/{a.trials}' + (f' `{"; ".join(table[(k, m)][1])}`' if table[(k, m)][0] and
                                                     m != modes[4] else '') for m in modes]
        L.append(f'| {k} | {o:#x} | {n} | {l} | ' + ' | '.join(cells) + f' | {"dead" if live[k] else "live"} |')
    # ---- 3. tk_kick
    bad, R = [], B4 + TAK[1] - 16
    for t in range(a.trials):
        r = random.Random(f'kick{t}')
        regs = {nm: ds.rval(r) for nm, _ in ds.GPR}
        fl = 0x202 | (r.getrandbits(12) & ds.FLAGS)
        m = ds.Mach(ni, f'kick{t}')
        for nm, rg in ds.GPR:
            m.uc.reg_write(rg, regs[nm])
        m.uc.reg_write(UC_X86_REG_EFLAGS, fl)
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.w32(ds.STACK, R)
        m.w8(B4 + lab['TK_CT'], r.randrange(1, 12))
        m.writes.clear()
        log, err = ds.run(m, B4 + TAK[0], R, ((B4 + TAK[0], B4 + TAK[1]),))
        s = ds.state(m)
        wr = [w for w in m.writes if not (ds.STACK - 0x1000 <= w < ds.STACK + 4) and not B4 + TAK[0] <= w < B4 + TAK[1]]
        if err or log or wr or any(s[nm] != regs[nm] for nm, _ in ds.GPR) or s['esp'] != ds.STACK + 4 or \
                s['flags'] != fl & ds.FLAGS or m.read(B4 + lab['TK_CT'], 1)[0] != 0:
            bad.append(f'{t}: {err} writes {[hex(w) for w in wr[:3]]} flags {s["flags"]:#x}/{fl & ds.FLAGS:#x}')
    ok_k = not bad
    L += ['', '## 3. tk_kick (sp_set\'s tail)', '',
          f'- {a.trials} random states: every register and flag kept, ESP + 4, writes only in the TAKERS band, TK_CT '
          f'cleared: {"all" if ok_k else "FAIL " + "; ".join(bad[:4])}']
    v = ok_b and ok_e and ok_c and ok_k
    L += ['', f'- byte diff: {"ok" if ok_b else "FAIL"}; TK_W 0 / training / SWOS++: '
          f'{"every site equal in every trial" if ok_e else "FAIL"}; TK_W 1 control: '
          f'{"every trial differs" if ok_c else "UNEXPECTED"}; tk_kick: {"ok" if ok_k else "FAIL"}.', '',
          f'Verdict: **{"PASS" if v else "FAIL"}**', '']
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(L))
    print('\n'.join(L))


if __name__ == '__main__':
    main()
