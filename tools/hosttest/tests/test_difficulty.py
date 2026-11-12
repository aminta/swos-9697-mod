"""42-diff difficulty.py: every stub in Unicorn against the original exe's own instructions, every language.
For each site the original exe runs its instructions (site .. site + n) and the DIFF_TEST exe runs the call into obj4
over the same range, from the same inputs (team structs, sprite, team files, the D / A variables):
- DF_ACT 0 (off) and 3 (NORMAL): registers, the variables and the scratch structs end equal to the original's (flags too
  where the next instruction reads them: the hold-back / slide compares, the carrier's sub, the sharp turn's add);
- DF_ACT 1 / 5: the level's value on the right side only (the opposition = a computer team v a human; the human's
  side for the dribbling rows), the original on every other pairing (two humans, two computer teams).
- df_kick: DF_W -> DF_ACT through LVMAP, 0 in a training game.
Exes: DIFF_EXE_DIR/<lang>/ITALIAN.EXE when set (b1<lang> dirs of a DIFF_TEST build), else built here (slow)."""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(HERE, '..'))
import difficulty as df                                         # noqa: E402

ORIG = os.path.join(TOOLS, '..', 'orig')
LANGS = {'en': 'ENGLISH', 'it': 'ITALIAN', 'fr': 'FRENCH', 'de': 'GERMAN'}
B1 = 0x100000
SCR = 0x1F00000
TA, TB, SPR, FA, FB = SCR, SCR + 0x100, SCR + 0x200, SCR + 0x300, SCR + 0x380
STACK = 0x1E00000


def _build(lang):
    d = os.environ.get('DIFF_EXE_DIR')
    if d:
        return os.path.join(d.replace('{lang}', lang), 'ITALIAN.EXE')
    import patch
    out = tempfile.mkdtemp(prefix=f'diff_{lang}_')
    os.makedirs(os.path.join(out, 'DATA'))
    old = os.environ.get('DIFF_TEST')
    os.environ['DIFF_TEST'] = '1'
    try:
        r = patch.patch_teams(os.path.join(ORIG, 'DATA/TEAM.020'), os.path.join(out, 'DATA/TEAM.020'))
        patch.write_new_teams(os.path.join(ORIG, 'DATA'), os.path.join(out, 'DATA'))
        patch.patch_exe(os.path.join(ORIG, f'{LANGS[lang]}.EXE'), os.path.join(out, 'ITALIAN.EXE'), r, lang)
    finally:
        os.environ.pop('DIFF_TEST', None) if old is None else os.environ.__setitem__('DIFF_TEST', old)
    return os.path.join(out, 'ITALIAN.EXE')


def _load(path):
    """(uc, snapshot, base2, base4): the exe relocated, objects one after another, scratch + stack above them"""
    import emu
    from le import LE
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    le = LE(open(path, 'rb').read())
    al = lambda x: (x + 0xFFFF) & ~0xFFFF
    b = [B1]
    for o in le.objs[:-1]:
        b.append(al(b[-1] + max(o.vsize, o.npages * 0x1000)))
    b += [None] * (4 - len(b))
    i1, i2, l2 = emu.relocate(path, b[0], b[1], b[2], b[3])
    top = al(max(x for x in b if x) + 0x400000)
    assert top <= SCR - 0x200000, hex(top)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, 0x2000000)
    for img, base in ((i1, b[0]), (i2, b[1]), (l2.img3, b[2]), (l2.img4, b[3])):
        if img and base:
            uc.mem_write(base, bytes(img))
    return uc, bytes(uc.mem_read(0, 0x2000000)), b[1], b[3]


def _setup(uc, sym, case, B2):
    """case: dict of inputs. Variables are obj2 offsets (sym) at B2."""
    w = lambda a, fmt, v: uc.mem_write(a, struct.pack(fmt, v))
    uc.mem_write(SCR, b'\0' * 0x1000)
    for t, o, pn, pc in ((TA, TB, case.get('pa', 1), case.get('ca', 0)), (TB, TA, case.get('pb', 0), case.get('cb', 0))):
        w(t, '<I', o)
        w(t + 4, '<H', pn)
        w(t + 6, '<H', pc)
    w(FA + 4, 'B', case.get('fa', 2))
    w(FB + 4, 'B', case.get('fb', 1))
    w(SPR + 0x2C, '<H', case.get('speed', 0))
    w(SPR + 0x4A, '<I', case.get('dist', 0))
    v = lambda k: B2 + sym[k][1]
    w(v('A6_'), '<I', case.get('a6', TB))
    w(v('A1_'), '<I', SPR)
    w(v('A2_'), '<I', case.get('a2', FB))
    w(v('A3_'), '<I', case.get('a3', FA))
    for k in ('D0_', 'D1_', 'D2_', 'D3_'):
        w(v(k), '<I', case.get(k, 0))


REGS = None


def _run(uc, at, n, esi, df_act, dfa_addr):
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI,
                                   UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EFLAGS)
    regs = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI)
    for i, r in enumerate(regs):
        uc.reg_write(r, 0x11110000 + i * 0x101)
    uc.reg_write(UC_X86_REG_ESI, esi)
    uc.reg_write(UC_X86_REG_ESP, STACK)
    uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
    if dfa_addr is not None:
        uc.mem_write(dfa_addr, bytes([df_act]))
    uc.emu_start(B1 + at, B1 + at + n, count=400)
    return [uc.reg_read(r) for r in regs], uc.reg_read(UC_X86_REG_ESP), uc.reg_read(UC_X86_REG_EFLAGS) & 0x8D5


def _state(uc, sym, B2):
    v = [bytes(uc.mem_read(B2 + sym[k][1], 4)) for k in ('D0_', 'D1_', 'D2_', 'D3_', 'A1_', 'A6_')]
    v[4] = bytes(uc.mem_read(struct.unpack('<I', v[4])[0], 16))   # (A1: the bytes it points at - pass table / sprite)
    return v, bytes(uc.mem_read(SCR, 0x400))


def test_difficulty():
    import lepatch
    errs, n_cases = [], 0
    for lang, name in LANGS.items():
        p = lepatch.LEPatch(os.path.join(ORIG, f'{name}.EXE'))
        s, sym = df.find(p)
        exe = _build(lang)
        uo, so, b2o, _ = _load(os.path.join(ORIG, f'{name}.EXE'))
        un, sn, b2n, B4 = _load(exe)
        mem4 = bytes(un.mem_read(B4 + 0xF000, 0x1000))
        k = mem4.find(df.TAG)
        if k < 0:
            errs.append(f'{lang}: no DIFF tag in obj4')
            continue
        dfa = B4 + 0xF000 + k + 5
        k3 = B4 + 0xF000 + mem4.find(struct.pack('<8H', *df.K3[0]))
        kfail = None

        def run(key, at, n, case, esi=SPR, flags=False):
            nonlocal n_cases
            res = {}
            for tag, uc, sn_, B2 in (('o', uo, so, b2o), ('n0', un, sn, b2n), ('n3', un, sn, b2n), ('n1', un, sn, b2n),
                                     ('n5', un, sn, b2n)):
                uc.mem_write(0, sn_)
                _setup(uc, sym, case, B2)
                act = {'o': None, 'n0': 0, 'n3': 3, 'n1': 1, 'n5': 5}[tag]
                r = _run(uc, at, n, esi if esi != 'A6' else case.get('a6', TB), act or 0,
                         None if act is None else dfa)
                res[tag] = (r, _state(uc, sym, B2))
            n_cases += 1
            o = res['o']
            for t in ('n0', 'n3'):
                a, b = o, res[t]
                if a[0][0] != b[0][0] or a[0][1] != b[0][1] or a[1] != b[1] or (flags and a[0][2] != b[0][2]):
                    errs.append(f'{lang} {key} {case} DF {t[1]}: not the original ({a[0]} / {a[1][0]} vs {b[0]} / '
                                f'{b[1][0]})')
            return res

        u16 = lambda st, off: struct.unpack_from('<H', st[1][1], off)[0]
        var = lambda st, i: struct.unpack_from('<I', st[1][0][i])[0]
        # K1 ScaleSkill: pct D2 x app D3; opposition FB (1) v FA (2)
        for d2, d3 in ((75, 100), (125, 100), (100, 106), (90, 94)):
            for fa, fb in ((2, 1), (1, 1), (2, 2), (3, 1)):
                case = dict(D2_=d2, D3_=d3, fa=fa, fb=fb)
                r = run('K1', s['SC'], 13, case)
                for t, lv in (('n1', 0), ('n5', 4)):
                    want3 = d3 * df.K1[lv] // 100 if (fa, fb) == (2, 1) else d3
                    got = (r[t][0][0][0] & 0xffff, r[t][0][0][3] & 0xffff)
                    prod = d2 * want3
                    if got != (prod & 0xffff, prod >> 16) or var(r[t], 3) & 0xffff != want3:
                        errs.append(f'{lang} K1 {case} {t}: {got} D3 {var(r[t], 3)}, want D3 {want3}')
        # K2 keeper
        for d0 in range(0, 8):
            for fa, fb in ((2, 1), (1, 1)):
                case = dict(D0_=d0, fa=fa, fb=fb)
                r = run('K2', s['GK'], 11, case)
                for t, lv in (('n1', 0), ('n5', 4)):
                    want = max(0, min(7, d0 + df.K2[lv])) if (fa, fb) == (2, 1) else d0
                    if r[t][0][0][0] & 0xff != want or var(r[t], 0) & 0xffff != want:
                        errs.append(f'{lang} K2 D0 {d0} {t}: {r[t][0][0][0] & 0xff}, want {want}')
        # K3 pass table (A6 = the passing team)
        for a6, pa, pb in ((TB, 1, 0), (TA, 1, 0), (TB, 0, 0), (TB, 1, 1)):
            case = dict(a6=a6, pa=pa, pb=pb)
            r = run('K3', s['PS'], 10, case)
            for t, lv in (('n1', 0), ('n5', 4)):
                opp = a6 == TB and pa and not pb
                want = struct.pack('<8H', *df.K3[lv]) if opp else r['o'][1][0][4]
                if r[t][1][0][4] != want:
                    errs.append(f'{lang} K3 {case} {t}: table {r[t][1][0][4].hex()}, want {want.hex()}')
        # K2b close shot (A6 = the keeper's team)
        for d1 in (0, 3, 7, 14):
            for a6 in (TB, TA):
                case = dict(D1_=d1 - 7 & 0xffff, a6=a6)
                r = run('K2b', s['GL'], 8, case)
                for t, lv in (('n1', 0), ('n5', 4)):
                    want = max(0, min(14, d1 - df.K2B[lv])) if a6 == TB else d1
                    if lv == 0 and a6 == TB and df.K2B[lv] == 0:
                        want = d1
                    if var(r[t], 1) & 0xffff != want:
                        errs.append(f'{lang} K2b D1 {d1} {case} {t}: {var(r[t], 1) & 0xffff}, want {want}')
        # match loop, per side: (key, site, n, field, esi)
        for a6 in (TA, TB):
            for pa, pb in ((1, 0), (1, 1), (0, 0)):
                side = (0 if a6 == TA else 1) if (pa, pb) == (1, 0) else None   # 0 human, 1 opposition
                for sp in (928, 1024, 1250):
                    case = dict(a6=a6, pa=pa, pb=pb, speed=sp)
                    r = run('K4', s['CAR'], 37, case, flags=True)
                    for t, lv in (('n1', 0), ('n5', 4)):
                        k = (df.USER, df.OPP)[side]['k'][lv] if side is not None else 4
                        want = sp - (sp * k >> 5)
                        if u16(r[t], 0x22C) != want:
                            errs.append(f'{lang} K4 {case} {t}: {u16(r[t], 0x22C)}, want {want}')
                    r = run('K10', s['TU'], 6, case, flags=True)
                    for t, lv in (('n1', 0), ('n5', 4)):
                        add = (df.USER, df.OPP)[side]['turn'][lv] if side is not None else 256
                        if u16(r[t], 0x22C) != sp + add:
                            errs.append(f'{lang} K10 {case} {t}: {u16(r[t], 0x22C)}, want {sp + add}')
                for dist in (100, 121, 150, 161, 199, 200, 201, 3200, 3201, 4400, 4401):
                    case = dict(a6=a6, pa=pa, pb=pb, dist=dist)
                    for key, site, f in (('K5', s['SL'], 'slide'),) + tuple(('K8', o, 'hold') for o in s['HOLD']):
                        r = run(key, site, 7, case, flags=True)
                        for t, lv in (('n1', 0), ('n5', 4)):
                            lim = (df.USER, df.OPP)[side][f][lv] if side is not None else df.NORM[f]
                            ja = not (r[t][0][2] & 1) and not (r[t][0][2] & 0x40)
                            if ja != (dist > lim):
                                errs.append(f'{lang} {key} {case} {t}: ja {ja}, limit {lim}')
                for o in s['LOCK']:
                    case = dict(a6=a6, pa=pa, pb=pb)
                    r = run('K9', o, 9, case, esi=a6)
                    for t, lv in (('n1', 0), ('n5', 4)):
                        want = (df.USER, df.OPP)[side]['lock'][lv] if side is not None else 12
                        got = u16(r[t], (a6 - SCR) + 0x8A)
                        if got != want:
                            errs.append(f'{lang} K9 {case} {t}: {got}, want {want}')
    return not errs, '; '.join(errs[:12]) + (f' (+{len(errs) - 12})' if len(errs) > 12 else '') or \
        f'4 languages, {n_cases} cases: DF 0 / 3 = the original at every site, L1 / L5 on the right side only'


if __name__ == '__main__':
    ok, msg = test_difficulty()
    print('PASS' if ok else 'FAIL', msg)
