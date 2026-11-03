"""4.0.6 option C, P1 (Tier B): ctgame.c's builder on the real code. Fixtures cg_uru: conti.ct_daily snapshots of a
NACIONAL career's season 2 (snapshot.py c/HTcg1/SWOS conti.ct_daily cg_uru --car h_uru/save_s1.CAR --max 8
--every 6; c/HTcg1 = 406-cgame on the release recipe, HOSTTEST_SYMS=1).

cg_replay: CT_SEG / CT_OUT / CT_IN / CT_ED byte-identical after it (the view's replay changes nothing: after the
replay a load's daily makes, ct_resume), its goals give
CT_OUT's results (conti.grec_check), deterministic. cg_build: every round conti.c has drawn (a knockout round whole and
its first tie, a group stage), each < 1 s, the same bytes twice; the contest's type, id and clubs as the struct; the
game's work area, D0..A6 and the random seed untouched; the pages written outside the scratch only the team cache's
records past its count, the count, the team file buffer and 32E15's flags (footprint golden: footprint.json,
HT_REGOLD=1); a cache with no room -> 0, CG_ERR 4, nothing written."""
import glob
import hashlib
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from emu import Machine  # noqa: E402

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures', os.environ.get('HT_CG', 'cg_uru'))
MEM, PAGE = 0x2000000, 0x1000
SCR, SCR_N, REC = 0x8000, 0x3000, 0x17C0        # (ctgame.py: the scratch at obj3 + 0x1000 * pages; ctgame.c CG_REC)
NCUP, NRD, NE, RB = 16, 8, 64, 24


def _snaps():
    for js in sorted(glob.glob(os.path.join(FIX, '[0-9]*.json')), key=lambda f: int(os.path.basename(f)[:-5])):
        yield int(os.path.basename(js)[:-5]), json.load(open(js))


def _m(k):
    m = Machine(FIX, k)
    b = m.meta['build']
    if not os.path.isdir(b):
        b = os.path.join(os.path.expanduser('~'), b[b.find('/swos-mod/') + 1:])
    m.dos_files(b)
    return m


def _state(m):
    lay = struct.unpack('<20I', m.read('conti.syms.CT_LAYOUT', 80))
    return (m.read('conti.syms.CT_SEG', 72), m.read('conti.syms.CT_OUT', lay[2]), m.read('conti.syms.CT_IN', lay[0]),
            m.read('conti.syms.CT_ED', 2260)), lay


def _spec(m):
    return m.read(m.u32('conti.syms.CT_SPEC'), 0x4000)


def _week(m):
    cur = m.u16('uefaq.SYMS.CAL_CUR')
    return m.u8(m.lin('uefaq.SYMS.CAL') + cur + 1)


def _rounds(spec, out, lay):
    """(cup, round, kind, clubs) of every round with a draw"""
    o_nent = lay[11]
    p, r_ = 4, []
    for c in range(spec[0]):
        nr = spec[p]
        for r in range(nr):
            n = out[o_nent + c * NRD + r]
            if n:
                r_.append((c, r, spec[p + 4 + r * RB], n))
        p += 4 + nr * RB
    return r_


def _pages(a, b):
    return {i // PAGE for i in range(0, MEM, PAGE) if a[i:i + PAGE] != b[i:i + PAGE]}


def test_cg_replay():
    import conti
    out, bad = [], []
    for k, meta in _snaps():
        m = _m(k)
        if m.u16('conti.syms.CT_ED') != 0x4543:
            out.append(f'{k}:no CE')
            continue
        m.call('conti.syms.ct_resume')                 # (as ct_daily after a load: the state the view sees)
        s0, lay = _state(m)
        t = time.time()
        m.call('ctgame.cg_replay')
        dt = time.time() - t
        s1, _ = _state(m)
        g = m.read(m.base3 + SCR + REC, 4 + 2 * NCUP * NRD + 0x1000)
        if s0 != s1:
            bad.append(f'{k}: the replay changed {["CT_SEG", "CT_OUT", "CT_IN", "CT_ED"][[a != b for a, b in zip(s0, s1)].index(True)]}')
            continue
        try:
            used = conti.grec_check(_spec(m), g, s1[1], lay, struct.unpack_from('<H', s1[2], 6)[0], f'snap {k}')
        except AssertionError as e:
            bad.append(f'{k}: goals {e}')
            continue
        m2 = _m(k)
        m2.call('ctgame.cg_replay')
        if m2.read(m2.base3 + SCR + REC, len(g)) != g:
            bad.append(f'{k}: not deterministic')
        if dt >= 1.0:
            bad.append(f'{k}: {dt:.2f} s')
        out.append(f'{k}:w{meta["week"]} {used}B {dt:.2f}s')
    return not bad and bool(out), ('; '.join(bad) + ' | ' if bad else '') + ', '.join(out)


def test_cg_build():
    out, bad = [], []
    regold = os.environ.get('HT_REGOLD') == '1'
    fpf = os.path.join(FIX, 'footprint.json')
    gold = {} if regold or not os.path.exists(fpf) else json.load(open(fpf))
    for k, meta in _snaps():
        m = _m(k)
        if m.u16('conti.syms.CT_ED') != 0x4543:
            continue
        m.call('ctgame.cg_replay')
        s, lay = _state(m)
        spec, week = _spec(m), _week(m)
        rounds = _rounds(spec, s[1], lay)
        work = m.lin('lp36.symbols.DIYCOPY')
        regs = m.lin('uefaq.SYMS.D0R')
        for c, r, kind, n in rounds:
            for t in ((-1, 0) if kind == 0 else (-1,)):
                key = f'{k}:{c}.{r}.{t}'
                a = _m(k)
                a.call('ctgame.cg_replay')
                before = bytes(a.uc.mem_read(0, MEM))
                w0, r0 = a.read(work, 0xB52), a.read(regs, 60)
                t0 = time.time()
                ln = a.call('ctgame.cg_build', c, r, t, week, max_insn=200_000_000)
                dt = time.time() - t0
                err = a.u32('ctgame.CG_ERR')
                after = bytes(a.uc.mem_read(0, MEM))
                if not ln:
                    if kind == 0 or err != 5:                  # (E_KIND: a league stage - the A page)
                        bad.append(f'{key}: not built, err {err}')
                    continue
                buf = a.read(a.base3 + SCR, 0xB52)
                st = a.read(a.base3 + SCR + 0xB60, 0x100)
                typ = struct.unpack_from('<H', buf, 0)[0]
                if typ != st[1] or buf[0x2D] != st[0]:
                    bad.append(f'{key}: type {typ} id {buf[0x2D]:#x}, struct {st[1]} {st[0]:#x}')
                ncl = st[10] if st[1] == 1 else st[15]
                if struct.unpack_from('<H', buf, 0x31)[0] != ncl:
                    bad.append(f'{key}: [31h] {struct.unpack_from("<H", buf, 0x31)[0]} clubs, struct {ncl}')
                if a.read(work, 0xB52) != w0 or a.read(regs, 60) != r0:
                    bad.append(f'{key}: work area / D0..A6 not put back')
                pg = sorted(p for p in _pages(before, after)
                            if not (a.base3 + SCR) // PAGE <= p < (a.base3 + SCR + SCR_N + PAGE - 1) // PAGE)
                b2 = _m(k)
                b2.call('ctgame.cg_replay')
                b2.call('ctgame.cg_build', c, r, t, week, max_insn=200_000_000)
                if b2.read(b2.base3 + SCR, 0xB52) != buf:
                    bad.append(f'{key}: not deterministic')
                if dt >= 1.0:
                    bad.append(f'{key}: {dt:.2f} s')
                gk = f'{k}'
                if regold or gk not in gold:
                    gold[gk] = sorted(set(gold.get(gk, [])) | set(pg))
                elif not set(pg) <= set(gold[gk]):
                    bad.append(f'{key}: pages outside the footprint {[a.where(p * PAGE) for p in sorted(set(pg) - set(gold[gk]))][:5]}')
                out.append(f'{key} n{n} t{typ} {len(pg)}p {dt:.2f}s')
                if os.environ.get('HT_CGSHOW'):
                    print(key, n, typ, [a.where(p * PAGE) for p in pg])
    if regold or not os.path.exists(fpf):
        json.dump(gold, open(fpf, 'w'))
    return not bad and bool(out), ('; '.join(bad[:8]) + ' | ' if bad else '') + f'{len(out)} builds: ' + ', '.join(out[:12])


def test_cg_nocache():
    """a team cache with no room: nothing built, CG_ERR 4 (E_CACHE), the scratch's contest untouched"""
    for k, meta in _snaps():
        m = _m(k)
        if m.u16('conti.syms.CT_ED') != 0x4543:
            continue
        m.call('ctgame.cg_replay')
        s, lay = _state(m)
        rounds = _rounds(_spec(m), s[1], lay)
        if not rounds:
            continue
        c, r, kind, n = rounds[0]
        m.write('ctgame.CG_NUMSEL', struct.pack('<H', 159))
        before = bytes(m.uc.mem_read(0, MEM))
        ln = m.call('ctgame.cg_build', c, r, -1, _week(m), max_insn=200_000_000)
        err = m.u32('ctgame.CG_ERR')
        after = bytes(m.uc.mem_read(0, MEM))
        own = m.lin('ctgame.CG_ERR') // PAGE             # (ctgame's own data: CG_ERR, spec()'s statics)
        pg = [m.where(p * PAGE) for p in sorted(_pages(before, after))
              if p != own and not (m.base3 + SCR) // PAGE <= p < (m.base3 + SCR + SCR_N) // PAGE]
        return ln == 0 and err == 4 and not pg, f'snap {k} cup {c} round {r}: returned {ln}, err {err}, pages {pg[:4]}'
    return False, 'no snapshot with an edition'
