"""POSITION TRAITS (1) + (3): RUOLI NO = the exe without the traits, proved on the host (prereg gate D1 of
internal/handoff/trhead-design.md; the 42-sp method, sp_structural.py / diff_structural.py).

  internal/hosttest/.venv/bin/python tools/hosttest/trhd_structural.py REF_BUILD NEW_BUILD [--trials N] [--out NAME]

REF_BUILD = this tree with TRHD_RUOLI unset (nothing linked), NEW_BUILD = TRHD_RUOLI=0 (the band in, RUOLI NO); both
HOSTTEST_SYMS=1, same recipe otherwise.
1. Byte diff. obj1: only the two distance compares (DIST0 / DIST1: `call tr_dist` + 5 nops) and operands aimed at a
   setpieces label that moved (the SETPIECE band grows by the one `call tr_head`: the same label by name in both
   builds). obj4: the TRHD band (empty in REF), the SETPIECE band (its three header stubs call tr_hdown, sp_head calls
   tr_head: checked at the labels; + 5 B), its SPX overflow band (same length: displacements
   to the moved labels), operands aimed at a moved setpieces label, and - when TRHD_END is past
   REF's last obj4 page - the band's own new page(s) with the operands into the engine's .bss above them moved by
   that size (as SPX in sp_structural). Nothing else.
2. Differential execution (Unicorn): every setpieces site with a plain end (13) + DIST0 / DIST1, random registers and
   flags, match states near the rules' thresholds, CALCI PIAZZATI 0 / 1 / 2, SWOS++ and training flags random:
   REF's region vs NEW's with TR_RU = 0 (RUOLI NO): registers, flags, ESP / EIP, calls out, every byte written (obj4
   state compared by label name). Control: TR_RU = 1 must differ at JZ, FZ, HD, DIST0, DIST1 and nowhere else.
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

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS

import diff_structural as ds
import setpieces as sp
import swreg
import trhead as tr
from lepatch import LEPatch

B1, B2, B3, B4 = ds.B1, ds.B2, ds.B3, ds.B4
SPR_ROOM = (swreg.SETPIECE_AT, swreg.SETPIECE_END)
TR_ROOM = (swreg.TRHD_AT, swreg.TRHD_END)
PLAIN = [h for h in sp.HOOKS if h[0] not in ('FB', 'FT', 'AF')]     # (those three leave through their own branches)
MUST = ('JZ', 'FZ', 'HD', 'DIST0', 'DIST1')


def name_of(off, lab):
    """An obj4 offset as (label, delta) of the nearest label at or below it."""
    best = max(((v, k) for k, v in lab.items() if v <= off), default=None)
    return (best[1], off - best[0]) if best else (None, off)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('new')
    ap.add_argument('--trials', type=int, default=300)
    ap.add_argument('--out', default='42trhd-structural')
    a = ap.parse_args()
    ref_exe, new_exe = os.path.join(a.ref, 'ITALIAN.EXE'), os.path.join(a.new, 'ITALIAN.EXE')
    rj, nj = (json.load(open(os.path.join(b, 'ITALIAN.syms.json'))) for b in (a.ref, a.new))
    assert 'trhead' not in rj and 'trhead' in nj, 'REF = TRHD_RUOLI unset, NEW = TRHD_RUOLI=0 (HOSTTEST_SYMS=1 both)'
    rs, ns = ({k: v[1] for k, v in j['setpieces'].items() if '.' not in k} for j in (rj, nj))
    tl = {k: v[1] for k, v in nj['trhead'].items() if '.' not in k}
    trg = nj['difficulty']['SYMS.TRG'][1]
    assert trg == rj['difficulty']['SYMS.TRG'][1]
    p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
    s, c = sp.find(p)
    ts, tc = tr.find(p)
    top = B2 + tc['TOP_O']
    hooks = [(k, s[k], n, l) for k, n, l in PLAIN] + [(k, ts[k], 10, 'tr_dist') for k in ('DIST0', 'DIST1')]
    ri, ni = ds.images(ref_exe), ds.images(new_exe)
    L = [f'# POSITION TRAITS (1)(3): RUOLI NO = no traits, structural: {a.out}', '', f'REF `{ref_exe}`  ',
         f'NEW `{new_exe}` (TRHD_RUOLI=0)', '', '## 1. Byte diff', '']
    ok_b = True

    def aimed(x, y, base, r):
        """A changed range inside a dword operand (absolute or rel32) that names the same setpieces label in both."""
        for w in range(max(0, r[0] - 3), r[0] + 1):
            if w + 4 < r[1]:
                continue
            va, vb = struct.unpack_from('<I', x, w)[0], struct.unpack_from('<I', y, w)[0]
            for ta, tb in (((va - B4) & 0xFFFFFFFF, (vb - B4) & 0xFFFFFFFF),
                           ((base + w + 4 + va - B4) & 0xFFFFFFFF, (base + w + 4 + vb - B4) & 0xFFFFFFFF)):
                if SPR_ROOM[0] <= ta < SPR_ROOM[1] and SPR_ROOM[0] <= tb < SPR_ROOM[1] and \
                        name_of(ta, rs) == name_of(tb, ns) and name_of(ta, rs)[0]:
                    return True
            if GROW[0] and (vb - va) & 0xFFFFFFFF == GROW[0] and va - B4 >= GROW[1]:
                BSS[0] += 1                             # (an operand into the engine's .bss above obj4's file pages:
                return True                             #  moved by TRHD's new page, as SPX's in sp_structural)
        return False

    GROW, BSS = [0, len(ri[4])], [0]
    if len(ni[4]) > len(ri[4]):                         # (TRHD_END past REF's last obj4 page: the band's own page(s))
        tail = [i for i in range(len(ri[4]), len(ni[4])) if ni[4][i]]
        g = all(TR_ROOM[0] <= i < TR_ROOM[1] for i in tail)
        ok_b &= g
        GROW[0] = len(ni[4]) - len(ri[4])
        L.append(f'- obj4 grows {len(ri[4]):#x} -> {len(ni[4]):#x} (TRHD up to {TR_ROOM[1]:#x}): every non-zero byte of '
                 f'the new pages inside the TRHD band: {"ok" if g else "WRONG"}')
    for obj in (1, 2, 3, 4):
        x, y = ri[obj], ni[obj]
        if x is None and y is None:
            continue
        if obj == 4:
            y = y[:len(x)]
        if len(x) != len(y):
            L.append(f'- obj{obj}: sizes {len(x):#x} / {len(y):#x} (FAIL)')
            ok_b = False
            continue
        diff = [i for i in range(len(x)) if x[i] != y[i]] if x != y else []
        cover = set()
        if obj == 1:
            for k in ('DIST0', 'DIST1'):
                o = ts[k]
                want = b'\xe8' + struct.pack('<i', B4 + tl['tr_dist'] - (B1 + o + 5)) + b'\x90' * 5
                g = bytes(y[o:o + 10]) == want
                ok_b &= g
                cover |= set(range(o, o + 10))
                L.append(f'- obj1 {k} {o:#x}+10: `{bytes(x[o:o + 10]).hex()}` -> `{bytes(y[o:o + 10]).hex()}` '
                         f'({"ok" if g else "WRONG"})')
        elif obj == 4:
            cover = set(range(*SPR_ROOM)) | set(range(*TR_ROOM)) | set(range(swreg.SPX_AT, swreg.SPX_END))
            g = not any(x[TR_ROOM[0]:TR_ROOM[1]])
            ok_b &= g
            L.append(f'- obj4 TRHD band: {"empty" if g else "NOT EMPTY"} in REF, '
                     f'{len(bytes(ni[4][TR_ROOM[0]:TR_ROOM[1]]).rstrip(bytes(1)))} B in NEW')
            ur, un = (len(bytes(z[SPR_ROOM[0]:SPR_ROOM[1]]).rstrip(bytes(1))) for z in (x, y))
            calls = {}
            for st_ in ('sp_jz', 'sp_fz', 'sp_head'):   # (push ebp / call <the verdict>)
                o = ns[st_]
                calls[st_] = y[o] == 0x55 and y[o + 1] == 0xE8 and \
                    o + 6 + struct.unpack_from('<i', y, o + 2)[0] == tl['tr_hdownj'] and \
                    x[rs[st_] + 1] == 0xE8 and rs[st_] + 6 + struct.unpack_from('<i', x, rs[st_] + 2)[0] == rs['sp_on']
            hd = [o for o in range(ns['sp_head'], ns['sp_head'] + 80) if y[o] == 0xE8 and
                  o + 5 + struct.unpack_from('<i', y, o + 1)[0] == tl['tr_headj']]
            moved = {k for k in rs if k in ns and ns[k] - rs[k] not in (0, 5)}
            xr, xn = (bytes(z[swreg.SPX_AT:swreg.SPX_END]) for z in (x, y))
            xd = sum(1 for i in range(len(xr)) if xr[i] != xn[i])
            g = un - ur == 5 and all(calls.values()) and len(hd) == 1 and not moved and \
                len(xr.rstrip(bytes(1))) == len(xn.rstrip(bytes(1)))
            L.append(f'- obj4 SPX band (setpieces\' overflow: its displacements from SPB to the moved labels): same '
                     f'length {len(xr.rstrip(bytes(1)))} B, {xd} bytes differ')
            ok_b &= g
            L.append(f'- obj4 SETPIECE band: {ur} -> {un} B used (+{un - ur}); sp_jz / sp_fz / sp_head call tr_hdown '
                     f'(sp_on in REF): {calls}; `call tr_head` in sp_head: {len(hd)}; labels moved by 0 or 5 only: '
                     f'{not moved} ({"ok" if g else "WRONG"})')
        stray = ds.ranges([i for i in diff if i not in cover])
        base = {1: B1, 2: B2, 3: B3, 4: B4}[obj]
        BSS[0] = 0
        bad = [(hex(r[0]), r[1] - r[0]) for r in stray if not aimed(x, y, base, r)]
        L.append(f'- obj{obj}: {len(ds.ranges(diff))} changed ranges; outside the sites / bands {len(stray)}: '
                 f'{len(stray) - len(bad) - BSS[0]} operands aimed at the same (moved) setpieces label, {BSS[0]} into the '
                 f'engine\'s .bss (+{GROW[0]:#x}); unexplained: {bad or "none"}')
        ok_b &= not bad

    # ------------------------------------------------------------------------------------------ 2. differential
    whole4 = lambda img: ((B4, B4 + len(img[4])),)
    kn = sp.knobs()

    def prep(m, lab, r, ctl):
        """One match state (the same draw in both machines); band state by label (the labels differ by build)."""
        ball, pl, tm = B2 + c['BALL_O'], ds.SCR + 0x30000, r.choice((top, top + 0x91))
        m.w32(B2 + c['A2_O'], ball)
        m.w16(ball + c['ZO'], r.randrange(0, 30))
        m.w32(ball + c['DZO'], r.choice((kn['JZ'] & 0xFFFFFFFF, kn['FZ'], 0xA000, r.getrandbits(32))))
        m.w16(ball + 0x20, r.randrange(100, 600))
        m.w16(ball + 0x24, r.randrange(120, 780))
        m.w16(ball + 0x2C, r.randrange(0, 4000))
        m.w16(ball + 0x1E, r.getrandbits(16))
        m.w32(ball + 0x32, r.randrange(-0x30000, 0x30000) & 0xFFFFFFFF)
        m.w16(B2 + c['BDZ_O'], r.randrange(8, 32))
        m.w16(B2 + c['GKA_O'], r.choice((0, 1)))
        m.w16(B2 + c['D7_O'], r.choice((1, 2, 5, 6, r.randrange(0, 8))))
        m.w32(B2 + c['A5_O'], pl)
        m.w32(pl + 0x4A, r.randrange(400, 1100))
        spr, ordn = pl + 0x400, r.randrange(1, 12)       # A1: the header's / kicker's sprite
        rec = pl + 0x1000 + (ordn - 1) * 61
        m.w32(B2 + c['A1_O'], spr)
        m.w16(spr + 2, ordn)
        m.w16(spr + 0x20, r.choice((r.randrange(60, 620), r.randrange(193, 479))))
        m.w16(spr + 0x24, r.choice((r.randrange(100, 800), r.randrange(129, 217), r.randrange(682, 770))))
        m.w32(spr + 0x4A, r.choice((r.randrange(40, 130), r.randrange(0, 5000), r.getrandbits(32))))
        m.w16(spr + c['TKS'], r.choice((0, 1, 2, 2)))
        m.w32(B2 + c['A6T_O'], tm)
        m.w32(tm, top + 0x91 if tm == top else top)
        m.w16(tm + 4, r.choice((0, 1)))
        m.w16(tm + 0x38, r.randrange(0, 8))
        m.w16(tm + 0x76, r.choice((0, 3, 9, 0xFFFF)))
        m.w32(tm + 0x0A, pl + 0x1000)
        m.w8(rec + tr.POS, r.choice((3, 3, 7, r.randrange(0, 8), 0xFF)))
        m.w8(rec + c['HDO'], r.choice((r.randrange(0, 8), 7)))
        m.w8(rec + c['HDO'] - 1, r.randrange(0, 8))
        m.w32(B2 + c['A4_O'], rec)
        m.w16(B2 + c['GS_O'], r.choice((3, 6, 9, 12, 13, 100)))
        m.w16(B2 + c['GSP_O'], r.choice((100, 101, 102)))
        m.w16(B2 + trg, 0 if ctl else r.choice((0, 0, 0, 1)))
        m.w16(B4 + lab['SP_W'], r.choice((0, 1, 2)))
        prd = struct.unpack('<i', m.read(B4 + lab['PR_D'], 4))[0]        # (the practice's KIND byte: in the engine's
        kind = r.choice((0, 0, 1))                      #  .bss, which TRHD's page moves - set by its own address)
        if prd:
            m.w8(B4 + lab['SPB'] + prd, kind)
        m.w8(B4 + lab['SP_OK'], 1 if ctl else r.choice((1, 1, 1, 0)))
        m.w32(B4 + lab['FK_TM'], r.choice((tm, tm + 0x91)))
        m.w8(B4 + lab['FK_ST'], r.choice((0, 1, 2, 2)))
        m.w8(B4 + lab['FK_CU'], r.choice((0, 1, 2)))
        m.w8(B4 + lab['FK_SH'], r.randrange(0, 5))
        m.w8(B4 + lab['FK_UP'], r.choice((0, 1)))
        m.w16(B4 + lab['FK_Y0'], r.randrange(200, 700))
        m.w16(B4 + lab['FK_N'], r.randrange(0, 110))
        m.w32(B4 + lab['FK_E'], r.randrange(-4096, 8192) & 0xFFFFFFFF)

    def trial(site, seed, ru):
        name, o, ln, _ = site
        ms = (ds.Mach(ri, seed), ds.Mach(ni, seed))
        r = random.Random(seed)
        regs = {n: ds.rval(r) for n, _ in ds.GPR}
        fl = 0x202 | (r.getrandbits(12) & ds.FLAGS)
        st0 = r.getstate()
        for m, lab in zip(ms, (rs, ns)):
            for n, rg in ds.GPR:
                m.uc.reg_write(rg, regs[n])
            m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
            m.uc.reg_write(UC_X86_REG_EFLAGS, fl)
            m.read(ds.STACK - 0x100, 0x200)
            r.setstate(st0)
            prep(m, lab, r, ru)
            m.writes.clear()
        ms[1].w8(B4 + tl['TR_RU'], ru)
        ms[1].writes.clear()
        start, end = B1 + o, B1 + o + ln
        out = []
        for m, img in zip(ms, (ri, ni)):
            log, err = ds.run(m, start, end, ((start, end),) + whole4(img))
            out.append((ds.state(m), log, err))
        (sa, la, ea), (sb, lb, eb) = out
        diffs = []
        if ea or eb:
            diffs.append(f'run: REF {ea} / NEW {eb}')
        diffs += [f'{k} {sa[k]:#x} / {sb[k]:#x}' for k in sa if sa[k] != sb[k]]
        if [x[0] for x in la] != [x[0] for x in lb]:
            diffs.append('calls out differ')
        esp = min(sa['esp'], sb['esp'])
        named = ({}, {})
        for i, (m, lab) in enumerate(zip(ms, ({**rs}, {**ns, **tl}))):
            for adr in m.writes:
                if ds.STACK - 0x1000 <= adr < esp:
                    continue
                if B4 <= adr < B4 + len(ni[4]):
                    named[i][name_of(adr - B4, lab)] = m.read(adr, 1)
                elif ms[0].read(adr, 1) != ms[1].read(adr, 1):
                    diffs.append(f'mem {adr:#x}')
        for k in set(named[0]) | set(named[1]):         # (obj4 state by label: the final byte on each side)
            va = ms[0].read(B4 + rs[k[0]] + k[1], 1) if k[0] in rs else None
            vb = ms[1].read(B4 + {**ns, **tl}[k[0]] + k[1], 1) if k[0] in ns or k[0] in tl else None
            if va != vb:
                diffs.append(f'obj4 {k[0]}+{k[1]}')
        return diffs

    modes = (('RUOLI NO', 0), ('RUOLI SI (control)', 1))
    table = {}
    for site in hooks:
        for mode, ru in modes:
            bad, first = 0, None
            for t in range(a.trials):
                d = trial(site, f'{site[0]}:{mode}:{t}', ru)
                if d:
                    bad += 1
                    first = first or d[:3]
            table[(site[0], mode)] = (bad, first)
        print(site[0], [table[(site[0], m[0])] for m in modes], flush=True)
    ok_e = all(table[(h[0], 'RUOLI NO')][0] == 0 for h in hooks)
    ok_c = all((table[(h[0], 'RUOLI SI (control)')][0] > 0) == (h[0] in MUST) for h in hooks)
    L += ['', '## 2. Differential execution: differing trials / trials', '',
          'CALCI PIAZZATI 0 / 1 / 2, the header at random places (half inside a box\'s width, a third in each box\'s '
          'depth), file position 3 / 7 / random, HEADING 0..7, ballDistance 40..130 a third of the time; RUOLI NO also '
          'with the SWOS++ / training flags. Control: RUOLI SI must differ at ' + ', '.join(MUST) + ' only.', '',
          '| site | obj1 | len | stub | ' + ' | '.join(m[0] for m in modes) + ' |', '|---|---|---|---|---|---|']
    for k, o, n, l in hooks:
        cells = [f'{table[(k, m[0])][0]}/{a.trials}' + (f' `{"; ".join(table[(k, m[0])][1])}`'
                                                        if table[(k, m[0])][0] and m[1] == 0 else '') for m in modes]
        L.append(f'| {k} | {o:#x} | {n} | {l} | ' + ' | '.join(cells) + ' |')
    v = ok_b and ok_e and ok_c
    L += ['', f'- byte diff: {"ok" if ok_b else "FAIL"}; RUOLI NO: {"every site equal in every trial" if ok_e else "FAIL"}; '
          f'control: {"only the five traits sites differ" if ok_c else "UNEXPECTED"}.', '',
          f'Verdict: **{"PASS" if v else "FAIL"}**', '']
    d = os.path.expanduser('~/swos-mod/internal/swostest/outcome-gate')
    open(os.path.join(d, a.out + '.md'), 'w').write('\n'.join(L))
    print('\n'.join(L))
    return v


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
