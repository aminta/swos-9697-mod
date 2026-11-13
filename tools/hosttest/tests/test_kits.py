"""4.2 kits (kits.py: K2 keepers, R1 referee; swe.c swe_match_w27).

- test_kits_masks: tools/kitmasks.py (committed) = kits.build_masks of the game's sprite files (HT_KITS_GAME, else
  c/REL40rc2/SWOS: GOAL1 / BENCH / TEAM1.DAT are the same on the CD and GOG);
- test_kits_reference: kits.match over every pair of a sample of worn kits: the two keepers never wear the same shirt
  (but the game's old one), no keeper clashes with the referee or either team's shirt / stripes; on the original
  TEAM.* home kits the old keeper look is under 1 % of matches (kits.eval_pairs);
- test_kits_exe: the exe's own code (HT_KITS_EXE, else c/K42a/SWOS/ITALIAN.EXE: a build with kits) on its static
  image in Unicorn (test_registry's machine): swe_match_w27 per mode (career world byte, friendly / DIY SWE_W27,
  else WCUR; WCUR absent -> 0); kt_chain (its `call ChainFont` nopped) on fake TeamGame pairs = kits.match, the
  referee's shirt masks on fake all-black sprites (3 -> his colour on the mask's pixels only); kt_conv1 / kt_conv2 on
  fake all-8 keeper sprites: A0 -> the keeper table (the team table with 10 / 11 / 14 / 15 = his kit), 8 -> 11 on the
  mask's pixels only."""
import os
import random
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'hosttest'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kits  # noqa: E402
import kitmasks  # noqa: E402

HOME = os.path.expanduser('~')
GAME = os.environ.get('HT_KITS_GAME') or os.path.join(HOME, 'swos-mod', 'c', 'REL40rc2', 'SWOS')
EXE = os.environ.get('HT_KITS_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'K42a', 'SWOS', 'ITALIAN.EXE')
SCR = 0x4000000                                 # (our fake TeamGames, sprite table and sprites)


def test_kits_masks():
    if not os.path.exists(os.path.join(GAME, 'GOAL1.DAT')):
        return True, f'SKIP: no sprite files in {GAME}'
    moff, ms = kits.build_masks(GAME)
    assert (moff, ms) == (kitmasks.MOFF, kitmasks.MS), 'tools/kitmasks.py is stale: kits.write_masks'
    return True, f'{len(moff)} masks, {len(ms)} B'


def test_kits_reference():
    rnd = random.Random(5)
    ks = kits.kits()
    n = old = 0
    for _ in range(20000):
        t1, t2 = rnd.choice(ks), rnd.choice(ks)
        for w in (0, 1):
            r, k1, k2 = kits.match(t1, t2, w)
            n += 1
            if kits.OLD_SHIRT in (k1[0], k2[0]):
                old += 1
                continue
            assert k1[0] != k2[0], (t1, t2, w, k1, k2)
            for k in (k1[0], k2[0]):
                assert not kits.clash(kits.EB, k, r), (t1, t2, w, r, k)
                for t in (t1, t2):
                    assert not (kits.clash(kits.EB, k, t[0]) or kits.clash(kits.EB, k, t[1])), (t1, t2, w, k)
            assert r in (kits.BLACK, kits.YELLOW) and (r == kits.BLACK or w)
    e0, e1 = kits.eval_pairs()
    assert e0 < 0.01 and e1 < 0.012, (e0, e1)
    return True, f'random kits: old look {old}/{n}; original home kits: {e0:.3%} / {e1:.3%} (w27)'


def _mask(i):
    o = kitmasks.MOFF[i]
    a, n = kitmasks.MS[o], kitmasks.MS[o + 1]
    ws = struct.unpack_from(f'<{n}H', kitmasks.MS, o + 2)
    return {(a + y, x) for y, w in enumerate(ws) for x in range(16) if w & (0x8000 >> x)}


def test_kits_exe():
    if not os.path.exists(EXE):
        return True, f'SKIP: {EXE} missing (HT_KITS_EXE: a build with kits)'
    import test_registry as tr
    import lepatch
    import re
    import swreg
    tr.EXE = EXE
    uc, le, sizes, _ = tr._machine()
    B1, B2, B4 = tr.B1, tr.B2, tr.B4
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    u32 = lambda a: struct.unpack('<I', rd(a, 4))[0]
    w8 = lambda a, v: uc.mem_write(a, bytes([v]))
    w16 = lambda a, v: uc.mem_write(a, struct.pack('<H', v))
    w32 = lambda a, v: uc.mem_write(a, struct.pack('<I', v))
    e8 = lambda a: a + 5 + struct.unpack('<i', rd(a + 1, 4))[0]
    o = lepatch.LEPatch(tr.ORIG)
    f = kits.find(o)
    va = lambda t: (B1 if t[0] == 1 else B2) + t[1]
    page = rd(B4 + swreg.KITS_AT, 0x1000)
    assert page.count(b'KITS') >= 1 and page.index(b'KITS') % 4 == 0, 'the KITS block'   # (the first: EN 'TEAM KITS'
                                                                                    #  comes after it)
    kb = B4 + swreg.KITS_AT + page.index(b'KITS') + 4
    REF, KK1, KK2, HS1 = kb, kb + 4, kb + 8, kb + 12
    CALLS, KT1, KT2 = kb + 20, kb + 44, kb + 76
    w27p, w27f = u32(kb + 36), u32(kb + 40)
    chain = e8(B1 + f['CF_AT'])
    conv = {lim: e8(B1 + at) for lim, at in f['LOOPS'].items()}
    assert rd(chain, 1) == b'\xe8', 'kt_chain: its call ChainFont first'
    uc.mem_write(chain, b'\x90' * 5)                # (no ChainFont on the static image)
    errs, notes = [], []
    # swe_match_w27 per mode
    d1o = o.le.obj_bytes(1)
    gt = {o.target(1, x.start() + 14) for x in re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d.{4}\x04\x75',
                                                           d1o, re.S)}
    assert len(gt) == 1, gt
    GT = va(gt.pop())
    code = rd(w27f, 48)                             # (the career's world byte: the build's careerworld SLT - the mod
    k = code.find(b'\x80\x3d')                      #  moves the table - as swe_match_w27's own `cmp byte [..], 5`)
    assert 0 <= k < 24 and code[k + 6] == 5, code.hex()
    CWB = struct.unpack_from('<I', code, k + 2)[0]
    reg = u32(B4 + 32)
    wcur_p = u32(reg + 8)
    assert w27f and w27p and wcur_p, (hex(w27f), hex(w27p), hex(wcur_p))
    cases = []
    for gtype, cwb, w27, wcur, want in ((4, 5, 0, 0, 1), (4, 4, 1, 5, 0), (4, 0, 1, 5, 0), (0, 0, 1, 0, 1),
                                         (0, 5, 0, 5, 0), (1, 0, 1, 4, 1), (1, 5, 0, 5, 0), (3, 0, 0, 5, 1),
                                         (2, 0, 1, 4, 0), (3, 5, 0, 0, 0), (2, 0, 0, 5, 1)):
        w16(GT, gtype)
        w8(CWB, cwb)
        w32(w27p, w27)
        w8(wcur_p, wcur)
        got = tr._call(uc, w27f)
        cases.append(got == want)
        if got != want:
            errs.append(f'swe_match_w27 gameType {gtype} world byte {cwb} SWE_W27 {w27} WCUR {wcur}: {got} (want {want})')
    w16(GT, 3)
    w8(wcur_p, 5)
    w32(reg + 8, 0)                                 # (no WCUR: 0)
    if tr._call(uc, w27f) != 0:
        errs.append('swe_match_w27 with no WCUR: not 0')
    w32(reg + 8, wcur_p)
    notes.append(f'swe_match_w27 {sum(cases)}/{len(cases)} modes')
    # the fake world: two TeamGames, a sprite table, all-black referee / all-8 keeper sprites
    uc.mem_map(SCR, 0x200000)
    TG1, TG2, TAB, SPR = SCR, SCR + 0x40, SCR + 0x1000, SCR + 0x10000
    w32(va(f['A5']), TG1)
    w32(va(f['A6']), TG2)
    w32(va(f['SGP']), TAB)

    def sprites(first, n, fill):
        for k in range(n):
            g = SPR + (first + k) * 0x100
            w32(TAB + 4 * (first + k), g)
            uc.mem_write(g, struct.pack('<I6xHHH', g + 24, 16, 20, 1) + bytes(6))
            uc.mem_write(g + 24, bytes([fill * 17]) * 160)

    def pixels(n):
        g = SPR + n * 0x100
        b = rd(g + 24, 160)
        return [[(b[y * 8 + x // 2] >> (0 if x & 1 else 4)) & 15 for x in range(16)] for y in range(20)]
    rnd = random.Random(7)
    ks = kits.kits()
    mism = 0
    ref_seen = set()
    for i in range(300):
        t1, t2 = rnd.choice(ks), rnd.choice(ks)
        w27 = i & 1
        w16(GT, 0)
        w32(w27p, w27)
        for tg, t in ((TG1, t1), (TG2, t2)):
            uc.mem_write(tg, struct.pack('<5H', 0, *t))
        sprites(1273, 11, 3)
        tr._call(uc, chain)
        r, k1, k2 = kits.match(t1, t2, w27)
        got = (rd(REF, 1)[0], tuple(rd(KK1, 3)), tuple(rd(KK2, 3)))
        if got != (r, k1, k2):
            mism += 1
            if mism <= 3:
                errs.append(f'kt_chain {t1} {t2} w27 {w27}: {got} (reference {r} {k1} {k2})')
        ref_seen.add(got[0])
        for k in range(11):
            m = _mask(116 + k)
            g = pixels(1273 + k)
            bad = [(y, x) for y in range(20) for x in range(16) if g[y][x] != (r if (y, x) in m else 3)]
            if bad:
                errs.append(f'referee sprite {1273 + k}: {len(bad)} pixels wrong (referee {r})')
                break
        if i < 6:                                   # the keeper conversions
            for lim, first, kk, kt, tabk in ((1005, 947, k1, KT1, 'TAB1'), (1121, 1063, k2, KT2, 'TAB2')):
                sprites(first, 116, 8)
                frame = rnd.randrange(116)
                w16(va(f['D0']), first + frame)
                tr._call(uc, conv[lim])
                tab = struct.unpack('<16H', rd(va(f[tabk]), 32))
                want = list(tab)
                want[10] = want[11] = kk[0]
                want[14], want[15] = kk[1], kk[2]
                if u32(va(f['A0'])) != kt or list(struct.unpack('<16H', rd(kt, 32))) != want:
                    errs.append(f'kt_conv {lim}: A0 {u32(va(f["A0"])):#x} table {struct.unpack("<16H", rd(kt, 32))} '
                                f'(want {kt:#x} {want})')
                m = _mask(frame)
                g = pixels(first + frame)
                bad = sum(1 for y in range(20) for x in range(16) if g[y][x] != (11 if (y, x) in m else 8))
                if bad:
                    errs.append(f'keeper sprite {first + frame} (frame {frame}): {bad} pixels wrong')
    notes.append(f'kt_chain 300 pairs: {mism} off the reference, referee colours {sorted(ref_seen)}; '
                 f'kt_chain runs {u32(CALLS)}')
    return not errs, '; '.join(errs + notes)
