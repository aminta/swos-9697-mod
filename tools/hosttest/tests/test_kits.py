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


def test_kits_keepkit():
    """4.2 KEEPKIT.DAT (kits.py kk_*, MC 13/11) on the exe's own code (HT_KITS_EXE), int 21h served by test_swefile's
    DOS: SEMPRE in a career writes the club's record (swe_save_atomic), a new match / the kick-off read it back (after
    a reload: swe_recover + read); key = world + country + name: the same name in another country or world = no
    record (no cross-talk), '_' compared as stored; AUTO + SEMPRE removes it; SOLO PARTITA / not a career: no write;
    an armed SOLO PARTITA slot (SET or AUTO) wins over the record at the kick-off; a bad / short / foreign file = an
    empty table, never a crash; a complete KEEPKIT.MK! (a cut save) wins; 129 clubs: the lowest stamp replaced
    (KK_EVICT), a club OK'd again keeps its place."""
    if not os.path.exists(EXE):
        return True, f'SKIP: {EXE} missing (HT_KITS_EXE: a build with kits)'
    import test_registry as tr
    import test_swefile as tsf
    import swreg
    from unicorn import UC_HOOK_INTR
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBX
    tr.EXE = EXE
    uc, le, sizes, _ = tr._machine()
    B4 = tr.B4
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    u32 = lambda a: struct.unpack('<I', rd(a, 4))[0]
    k17 = B4 + swreg.KITS_PAGE16_END
    if rd(k17, 4) != b'KKST':
        return False, 'no KKST block on obj4 page 17'
    P = dict(zip(kits.KK_PTRS, struct.unpack_from(f'<{len(kits.KK_PTRS)}I', rd(k17 + 20, 4 * len(kits.KK_PTRS)))))
    O = {k: k17 + v for k, v in kits.KK_OFF.items()}
    FILE = O['KK_FILE']
    dos = [tsf.Dos()]
    uc.hook_add(UC_HOOK_INTR, lambda u, i, d: dos[0].intr(u, i, d))
    errs, notes = [], []
    KS, CT = P['KS'], P['CAREER_TEAM']

    def career(name, country, world=5, gtype=4, always=1):
        uc.mem_write(P['GAMETYPE'], struct.pack('<H', gtype))
        uc.mem_write(P['CWB'], bytes([world]))
        uc.mem_write(CT, bytes([country]))
        uc.mem_write(CT + 5, name.encode('latin-1').ljust(17, b'\0')[:17])
        uc.mem_write(P['KM_ALWAYS'], bytes([always]))

    def slots(n1, k1=None, n2='OTHER', k2=None):
        for i, (n, k) in enumerate(((n1, k1), (n2, k2))):
            uc.mem_write(KS + 24 * i, n.encode('latin-1').ljust(18, b'\0')[:18] + bytes(k or (0, 0, 0)) + bytes([k is not None]) + bytes(2))

    def slot(i):
        return tuple(rd(KS + 24 * i + 18, 4))

    def reload(files):                               # (a new game run: the file read again at the first use)
        dos[0] = tsf.Dos(files)
        uc.mem_write(O['KK_LOADED'], b'\0')

    def table():
        n = struct.unpack('<H', rd(FILE + 6, 2))[0]
        return [(r[0], r[1], struct.unpack('<H', r[2:4])[0], r[4:21].split(b'\0')[0].decode('latin-1'), tuple(r[21:24]))
                for r in (rd(FILE + 12 + 24 * i, 24) for i in range(n))]

    def disk():
        d = dos[0].files.get('KEEPKIT.DAT')
        return None if d is None else (d[:4], d[4], struct.unpack('<H', d[6:8])[0], len(d))

    def keep(name, country, kit, world=5, **kw):
        career(name, country, world, **kw)
        slots(name, kit)
        tr._call(uc, P['kk_keep'])

    def fill(name, country, world=5):
        career(name, country, world)
        slots(name)
        tr._call(uc, P['kk_fill'])
        return slot(0)

    def kickoff(name, country, world=5, gtype=4):     # kk_rec on a TeamGame of that name -> HS (palette entries)
        career(name, country, world, gtype)
        tg = 0x4000000
        try:
            uc.mem_map(tg, 0x1000)
        except Exception:
            pass
        uc.mem_write(tg + 0x16, name.encode('latin-1').ljust(17, b'\0')[:17])
        uc.mem_write(tg + 0x100, bytes(4))
        uc.reg_write(UC_X86_REG_ESI, tg)
        uc.reg_write(UC_X86_REG_EBX, tg + 0x100)
        tr._call(uc, P['kk_rec'])
        return tuple(rd(tg + 0x100, 4))

    code = (1, 2, 3, 6, 10, 11, 12, 13, 14, 15, 12)
    want = lambda k: (code[k[0]], code[k[1]], code[k[2]], 1)
    # 1. no file: SEMPRE writes it
    reload({})
    keep('NACIONAL', 30, (3, 1, 0))
    t = table()
    if t != [(5, 30, 1, 'NACIONAL', (3, 1, 0))] or disk() != (b'KEEP', 1, 1, 36) or u32(O['KK_SAVES']) != 1:
        errs.append(f'first save: table {t}, disk {disk()}, saves {u32(O["KK_SAVES"])}, err {u32(O["KK_ERR"]):#x}')
    f1 = dict(dos[0].files)
    # 2. a new run: read back by a new match and the kick-off; same name, another country / world: nothing
    reload(f1)
    if fill('NACIONAL', 30) != (3, 1, 0, 1):
        errs.append(f'reload: kk_fill slot {slot(0)}')
    if fill('NACIONAL', 31) != (0, 0, 0, 0) or fill('NACIONAL', 30, world=1) != (0, 0, 0, 0):
        errs.append('another country / world: a record was taken')
    if kickoff('NACIONAL', 30) != want((3, 1, 0)) or kickoff('NACIONAL', 31) != (0, 0, 0, 0) \
            or kickoff('NACIONAL', 30, gtype=0) != (0, 0, 0, 0):
        errs.append(f'kick-off: {kickoff("NACIONAL", 30)} / {kickoff("NACIONAL", 31)} / friendly {kickoff("NACIONAL", 30, gtype=0)}')
    # 3. the same name in another country: its own record, no cross-talk; '_' as stored
    keep('NACIONAL', 31, (6, 2, 2))
    keep('ROBERTO_X', 14, (1, 1, 1))
    reload(dict(dos[0].files))
    if fill('NACIONAL', 30) != (3, 1, 0, 1) or fill('NACIONAL', 31) != (6, 2, 2, 1) \
            or fill('ROBERTO X', 14) != (0, 0, 0, 0) or fill('ROBERTO_X', 14) != (1, 1, 1, 1):
        errs.append(f'two NACIONAL / underscore: table {table()}')
    # 4. SOLO PARTITA / not a career: nothing written; AUTO + SEMPRE removes the record
    saves = u32(O['KK_SAVES'])
    keep('ATALANTA', 14, (2, 2, 2), always=0)
    keep('ATALANTA', 14, (2, 2, 2), gtype=0)
    if u32(O['KK_SAVES']) != saves or any(r[3] == 'ATALANTA' for r in table()):
        errs.append('SOLO PARTITA / friendly wrote a record')
    keep('NACIONAL', 30, None)
    if [r[3:] for r in table()] != [('ROBERTO_X', (1, 1, 1)), ('NACIONAL', (6, 2, 2))] or disk()[2] != 2:
        errs.append(f'AUTO + SEMPRE: table {table()}, disk {disk()}')
    # 5. kg_match: an armed slot of that name wins (AUTO too); not armed: the record
    reload(dict(dos[0].files))
    career('NACIONAL', 31)
    tg = 0x4000000
    for arm, k, exp in ((0, None, want((6, 2, 2))), (1, None, (0, 0, 0, 0)), (1, (9, 1, 1), want((9, 1, 1)))):
        slots('NACIONAL', k, 'PENAROL', None)
        uc.mem_write(P['KG_ARM'], bytes([arm]))
        uc.mem_write(tg + 0x16, b'NACIONAL'.ljust(17, b'\0'))
        uc.mem_write(tg + 0x80 + 0x16, b'PENAROL'.ljust(17, b'\0'))
        uc.reg_write(UC_X86_REG_ESI, tg)
        uc.reg_write(UC_X86_REG_EDI, tg + 0x80)
        tr._call(uc, P['kg_match'])
        kb = B4 + swreg.KITS_AT + rd(B4 + swreg.KITS_AT, 0x1000).index(b'KITS') + 4
        got = (tuple(rd(kb + 12, 4)), tuple(rd(kb + 16, 4)))
        if got != (exp, (0, 0, 0, 0)):
            errs.append(f'kg_match armed {arm} slot {k}: HS {got} (want {exp})')
    uc.mem_write(P['KG_ARM'], b'\0')
    # 6. bad files: empty, no crash
    good = dos[0].files['KEEPKIT.DAT']
    bad = {'magic': b'KEEQ' + good[4:], 'version': good[:4] + b'\2' + good[5:], 'count': good[:6] + b'\x81\0' + good[8:],
           'short': good[:-1], 'colour': good[:-1] + b'\x0b', 'tiny': b'KE', 'empty': b''}
    for k, d in bad.items():
        reload({'KEEPKIT.DAT': d})
        if fill('NACIONAL', 31) != (0, 0, 0, 0) or table():
            errs.append(f'bad file {k}: slot {slot(0)}, table {table()}')
    # 7. a cut save: a complete KEEPKIT.MK! wins over the old file, a KEEPKIT.MK$ is dropped
    reload({'KEEPKIT.DAT': f1['KEEPKIT.DAT'], 'KEEPKIT.MK!': good, 'KEEPKIT.MK$': b'KEEP\1'})
    if fill('NACIONAL', 31) != (6, 2, 2, 1) or set(dos[0].files) != {'KEEPKIT.DAT'}:
        errs.append(f'recover: slot {slot(0)}, files {sorted(dos[0].files)}')
    # 8. 129 clubs: the lowest stamp replaced; one OK'd again keeps its place
    reload({})
    ev = u32(O['KK_EVICT'])
    for i in range(128):
        keep(f'CLUB {i}', 1, (i % 11, 0, 0))
    keep('CLUB 0', 1, (5, 5, 5))                    # (CLUB 0 again: the newest now)
    keep('CLUB 128', 1, (4, 4, 4))
    names = [r[3] for r in table()]
    if len(names) != 128 or 'CLUB 1' in names or 'CLUB 0' not in names or 'CLUB 128' not in names \
            or u32(O['KK_EVICT']) != ev + 1 or disk()[2] != 128 or disk()[3] != 12 + 128 * 24:
        errs.append(f'129 clubs: {len(names)} records, CLUB 1 {"CLUB 1" in names}, evict {u32(O["KK_EVICT"]) - ev}, disk {disk()}')
    reload(dict(dos[0].files))
    if fill('CLUB 0', 1) != (5, 5, 5, 1) or fill('CLUB 128', 1) != (4, 4, 4, 1) or fill('CLUB 1', 1) != (0, 0, 0, 0):
        errs.append('129 clubs: reload')
    notes.append(f'KEEPKIT: saves {u32(O["KK_SAVES"])}, evicted {u32(O["KK_EVICT"]) - ev}, page 17 {k17 - B4:#x}')
    return not errs, '; '.join(errs + notes)
