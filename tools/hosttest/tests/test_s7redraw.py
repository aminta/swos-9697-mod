"""4.2 S7 redraw (MC design internal/handoff/s7-redraw.md, item 3 / gate 2): s7geo.c's s7rd_rule, built natively (-m32 not needed:
int32 arithmetic only), against Panchina's oracle goldens tools/s7redraw_golden.json (tools/s7redraw.py rule(), frozen 42-redraw
31db319): every case's groups byte for byte (real 2025-26 -> 2026-27 C and D, the C second teams' seeds 1..5, ten-season chains);
group sizes asserted; no club twice / lost; determinism (each case run twice). Controls: STAY ignored (cost without the last-group
bonus) changes some case; a seed's arrangement changes the C second teams; s7rd_centroid == the oracle's centroid; s7rd_travel ==
travel() on the island boxes' corners."""
import ctypes
import json
import os
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
GOLD = os.path.join(TOOLS, 's7redraw_golden.json')
_LIB = {}


def lib(extra=()):
    key = tuple(extra)
    if key not in _LIB:
        d = tempfile.mkdtemp(prefix='s7rd')
        so = os.path.join(d, 's7geo.dylib')
        r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-w', '-DDATA=', *extra, '-o', so, os.path.join(TOOLS, 's7geo.c')],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[-800:])
        _LIB[key] = ctypes.CDLL(so)
    return _LIB[key]


def run(L, c, seed=None):
    """(rc, {ident: group letter}) of s7rd_rule on a golden case."""
    groups = sorted(c['anchors'])
    gi = {g: i for i, g in enumerate(groups)}
    ids = [x[0] for x in c['clubs']]
    assert ids == sorted(ids)
    n, ng = len(ids), len(groups)
    last, prev = dict((k, g) for k, g in c['last']), dict((k, g) for k, g in c['prev_second'])
    sec = set(c['second'])
    A16, A8, A32 = ctypes.c_int16 * n, ctypes.c_uint8 * n, ctypes.c_int32 * ng
    la, lo = A16(*[x[1] for x in c['clubs']]), A16(*[x[2] for x in c['clubs']])
    lst = A8(*[gi[last[k]] if last.get(k) is not None else 0xFF for k in ids])
    prv = A8(*[gi[prev[k]] if prev.get(k) is not None else 0xFF for k in ids])
    sc = A8(*[1 if k in sec else 0 for k in ids])
    cap = (ctypes.c_uint8 * ng)(*[c['size']] * ng)
    ala, alo = A32(*[c['anchors'][g][0] for g in groups]), A32(*[c['anchors'][g][1] for g in groups])
    out = A8(*[0xEE] * n)
    work = ctypes.create_string_buffer(0x10000)
    rc = L.s7rd_rule(n, la, lo, lst, prv, sc, ng, cap, ala, alo, ctypes.c_uint32(c['seed'] if seed is None else seed), out, work)
    return rc, {k: (groups[out[i]] if out[i] < ng else None) for i, k in enumerate(ids)}


def test_s7redraw_golden():
    cases = json.load(open(GOLD))
    L = lib()
    n_ok = 0
    for c in cases:
        rc, got = run(L, c)
        assert rc == 0, (c['name'], rc)
        want = dict((k, g) for k, g in c['out'])
        bad = [(k, want[k], got[k]) for k in want if want[k] != got[k]]
        assert not bad, (c['name'], len(bad), bad[:6])
        sizes = {}
        for g in got.values():
            sizes[g] = sizes.get(g, 0) + 1
        assert set(sizes.values()) == {c['size']} and len(sizes) == len(c['anchors']), (c['name'], sizes)
        assert run(L, c)[1] == got, (c['name'], 'not deterministic')
        n_ok += 1
    return True, f'{n_ok} golden cases byte for byte (C {sum(c["level"] == "C" for c in cases)}, D {sum(c["level"] == "D" for c in cases)})'


def test_s7redraw_controls():
    cases = {c['name']: c for c in json.load(open(GOLD))}
    L = lib()
    # a different seed moves the C second teams (the draw is live)
    c = cases['real_C']
    base = run(L, c)[1]
    moved = [sd for sd in range(1, 6) if run(L, c, sd)[1] != base]
    assert moved, 'the seed never changes the C groups'
    # without the stability bonus some case differs (STAY is live)
    L0 = lib(('-DS7RD_STAY_TEST=0',))
    diff = [nm for nm, cc in cases.items() if run(L0, cc)[1] != dict((k, g) for k, g in cc['out'])]
    assert diff, 'STAY 0 gives the same groups everywhere'
    # travel / centroid twins
    import s7redraw as O
    for la, lo in ((3880, 800), (4140, 990), (3879, 800), (3650, 1230), (3840, 1570), (3841, 1570), (4500, 900)):
        a, b = ctypes.c_int32(la), ctypes.c_int32(lo)
        L.s7rd_travel(ctypes.byref(a), ctypes.byref(b))
        assert (a.value, b.value) == O.travel(la, lo), (la, lo, a.value, b.value)
    cl = cases['real_D']['clubs']
    n = len(cl)
    grp = [i % 9 for i in range(n)]
    A16, A8, A32 = ctypes.c_int16 * n, ctypes.c_uint8 * n, ctypes.c_int32 * 9
    ala, alo = A32(), A32()
    L.s7rd_centroid(n, A16(*[x[1] for x in cl]), A16(*[x[2] for x in cl]), A8(*grp), 9, ala, alo)
    for g in range(9):
        assert (ala[g], alo[g]) == O.centroid((x[1], x[2]) for i, x in enumerate(cl) if grp[i] == g), g
    return True, f'seed moves C for seeds {moved}; STAY 0 differs in {len(diff)} cases; travel / centroid twins'


# ---- gate 2 on the exe (s7-redraw.md 4.2): s7swap.c run() -> S7RD_PTR -> s7rd_level, on a REAL-pack HOSTTEST_SYMS build ---------------
# HT_S7RD_EXE (default c/HTRD1: the release recipe world5tm-h3s7r + HOSTTEST_SYMS=1). Each case: the season end from a fresh career
# (test_s7swap's crossings: 9 Serie C clubs down, the 9 Serie D winners up), first with S7RD_PTR poked 0 (the crossers' place() groups:
# the members of each level after the crossings), then with the redraw; the oracle (tools/s7redraw.py rule()) gets those members, their
# last group (the registry before the season end), the anchors = centroids of last season's members (leavers included), the exe's own
# coordinates through travel(), the C second teams (S7RD_SEC) with their last group, seed = (the career club's word * 2654435761) ^ (the season * 0x9E3779B9) (MC 15/11). The
# registry's division of every club of both levels == the oracle's, byte for byte; sizes 20 / 18; no club twice / lost; twice = same.
# Cases: season 1 end (career club = a Serie C club), the same with two other career clubs (the seed: the second teams' draw), a
# 3-season chain (each season's crossers picked from the registry as it stands: the redraw's own groups become the next last season).
RD_EXE = os.environ.get('HT_S7RD_EXE') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'HTRD1', 'SWOS', 'ITALIAN.EXE')


def _sec_csv():
    """S7RD_SEC as s7swap.py builds it (clubs.csv second_of, ident = row order) - for builds before the S7RD_* labels were exported"""
    import csv
    p = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'world2526', os.environ.get('HT_S7RD_DATA', 'world5tm-h3s7r'), 'ita', 'clubs.csv')
    b = bytearray(40)
    for i, r in enumerate(csv.DictReader(open(p, encoding='utf-8'))):
        if (r.get('second_of') or '').strip():
            b[i >> 3] |= 1 << (i & 7)
    return bytes(b)


def _season(m, t7, down, up, season):
    """t7.run with a budget for the redraw (~21M instructions on the real pack: tr._call's 2M stops it half way - status left as it was)"""
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
    import test_registry as tr
    m.snap(0, t7.FA, down, season)
    m.snap(1, t7.FB, up, season)
    m.w(t7.SLT_AT, bytes(2400))
    m.w(m.log, b'\0')
    sp = tr.STACK - 0x100
    m.uc.mem_write(sp, struct.pack('<II', tr.RET, t7.SLT_AT))
    m.uc.reg_write(UC_X86_REG_ESP, sp)
    h = m.uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=tr.RET, end=tr.RET)
    m.uc.emu_start(m.at('s7swap', 's7_season'), tr.RET, count=100_000_000)
    m.uc.hook_del(h)
    assert m.uc.reg_read(UC_X86_REG_EIP) == tr.RET, 's7_season did not return in 100M instructions'
    st, _, nsw, ncr = m.rd(m.log, 4)
    return st, nsw, ncr


def _exe_case(m, t7, down, up, season, sel):
    """(oracle {ident: div}, exe {ident: div}, log, errs) of one season end from the registry as it stands in m (restored between runs)"""
    import s7redraw as O
    gm = 's7swap'                                       # (s7swap.py exports the S7GEO band's S7GEO_* / S7RD_* data)
    ptr = m.at('s7swap', 'S7RD_PTR')
    pv = m.rd(ptr, 4)
    r0 = m.regb()
    fs0, word0, at0, rdiv0, rows0 = t7.reg_parse(r0)
    fidx = {f[0]: i for i, f in enumerate(fs0)}

    def divs(word, rdiv):
        return {i: rdiv[fidx[w & 0xFF]][w >> 8] for i, w in enumerate(word) if w != 0xFFFF and (w & 0xFF) in fidx}
    pre = divs(word0, rdiv0)
    m.w(m.at('s7swap', 'S7_SELTEAM'), struct.pack('<H', sel))
    m.w(ptr, b'\0' * 4)
    st, nsw, ncr = _season(m, t7, down, up, season)
    assert st == t7.OK, ('place() run', st)
    _, word1, _, rdiv1, _ = t7.reg_parse(m.regb())
    mid = divs(word1, rdiv1)
    m.w(m.reg, r0)                                      # (the registry back: the redraw run from the same start)
    m.w(ptr, pv)
    m.w(m.at('s7swap', 'S7_SELTEAM'), struct.pack('<H', sel))
    st, nsw, ncr = _season(m, t7, down, up, season)
    assert st == t7.OK and nsw == len(up), ('redraw run', st, nsw)
    _, word2, _, rdiv2, _ = t7.reg_parse(m.regb())
    got = divs(word2, rdiv2)
    xy = struct.unpack('<640h', m.rd(m.at(gm, 'S7GEO_XY'), 1280))
    sec = m.rd(m.at(gm, 'S7RD_SEC'), 40) if 'S7RD_SEC' in m.sy[gm] else _sec_csv()
    log = m.rd(m.at(gm, 'S7RD_LOG'), 8) if 'S7RD_LOG' in m.sy[gm] else bytes(8)
    want = dict(got)
    errs = []
    for lvl, lv in ((0, list(m.up)), (1, list(m.lo))):
        mem = sorted(i for i, d in mid.items() if d in lv)
        clubs = {i: O.travel(xy[2 * i], xy[2 * i + 1]) for i in mem}
        lastm = {g: [i for i, d in pre.items() if d == lv[g]] for g in range(len(lv))}
        anchors = {g: O.centroid(O.travel(xy[2 * i], xy[2 * i + 1]) for i in ids) for g, ids in lastm.items()}
        last = {i: (lv.index(pre[i]) if pre.get(i) in lv else None) for i in mem}
        s2 = sorted(i for i in mem if lvl == 0 and sec[i >> 3] >> (i & 7) & 1)
        prev = {i: last[i] for i in s2 if last[i] is not None}
        size = len(mem) // len(lv)
        out = O.rule(clubs, anchors, size, last, set(s2), prev, ((sel * 2654435761) ^ (season * 0x9E3779B9)) & 0xFFFFFFFF)
        for i in mem:
            want[i] = lv[out[i]]
        cnt = [sum(1 for i in mem if got.get(i) == d) for d in lv]
        if set(cnt) != {size}:
            errs.append(f'level {lvl}: sizes {cnt}')
        if lvl == 0 and len({got[i] for i in s2}) != len(s2):
            errs.append(f'second teams share a group: {[(i, got[i]) for i in s2]}')
        if lvl == 0 and any(prev.get(i) is not None and got[i] == lv[prev[i]] for i in s2):
            errs.append('alternation broken')
    if sorted(got) != sorted(mid):
        errs.append('a club lost / added')
    lvs = (set(m.up), set(m.lo))
    rg = sum(1 for i in got if any(pre.get(i) in L and got[i] in L and got[i] != pre[i] for L in lvs))
    return want, got, (log, rg), errs


def test_s7redraw_exe():
    if not os.path.exists(RD_EXE) or not os.path.exists(RD_EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {RD_EXE} (release recipe h3s7r + HOSTTEST_SYMS=1) missing'
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_s7swap as t7
    m = t7.M(RD_EXE)
    if not struct.unpack('<I', m.rd(m.at('s7swap', 'S7RD_PTR'), 4))[0]:
        return False, f'{RD_EXE}: S7RD_PTR 0 (redraw off: S7_REDRAW_OFF or no coordinates)'
    notes, errs = [], []
    m.fresh()
    fs, word, at, rdiv, rows = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    cclubs = [t7.FA | o << 8 for o in (60, 70, 90)]     # (three Serie C rows that do not cross: the career club's word)
    for sel in cclubs:
        m.fresh()
        want, got, log, e = _exe_case(m, t7, down, up, t7.SEASON, sel)
        bad = [(i, want[i], got[i]) for i in want if want[i] != got[i]]
        if bad or e:
            errs.append(f'season 1 end, career {sel:#06x}: {len(bad)} clubs differ {bad[:4]} {e}')
        fl = struct.unpack('<I', m.rd(m.at('sreg', 'SREG_FLAGS'), 4))[0]
        if 'S7RD_LOG' in m.sy['s7swap'] and (fl >> 4 & 0xF) != 1:
            errs.append(f'career {sel:#06x}: SREG_FLAGS {fl:#x} (want the rule version 1 in bits 4..7 after a redraw season end)')
        reg1 = m.regb()
        m.fresh()
        _exe_case(m, t7, down, up, t7.SEASON, sel)
        if m.regb() != reg1:
            errs.append(f'career {sel:#06x}: not deterministic')
        notes.append(f'{sel:#06x}: {log[1]} regrouped, S7RD_LOG {log[0].hex()}')
    # the chain: 3 season ends in a row, crossers from the registry as it stands (each C group's 3 last rows down, each D group's first row up)
    m.fresh()
    moved = 0
    for k in range(3):
        fs1, word1, at1, rdiv1, rows1 = t7.reg_parse(m.regb())
        dn, upl = [], []
        for d in m.up:
            os_ = [o for o in range(rows1[0]) if rdiv1[0][o] == d][-3:]
            dn += [(t7.glob_of(m.gb[0], o), t7.FA | o << 8, 1, 1, 0xFF, 0) for o in os_]
        for d in m.lo:
            o = next(o for o in range(rows1[1]) if rdiv1[1][o] == d)
            upl.append((t7.glob_of(m.gb[1], o), t7.FB | o << 8, 0, 0, list(m.lo).index(d), 0))
        want, got, log, e = _exe_case(m, t7, dn, upl, t7.SEASON + k, cclubs[0])
        bad = [(i, want[i], got[i]) for i in want if want[i] != got[i]]
        if bad or e:
            errs.append(f'chain season {k + 1}: {len(bad)} clubs differ {bad[:4]} {e}')
        moved += log[1]
    return not errs, '; '.join(errs[:4]) or (f'exe == oracle on season 1 end x3 career clubs (deterministic) + a 3-season chain '
                                             f'({moved} regroupings in the chain); {"; ".join(notes)}')


# ---- MC 15/11 condition 1 (the rule version in the 'IT' flags' spare bits 4..7): every save we can load has bits 2..7 = 0 today -------------
# Every .CAR under ~/swos-mod/internal (the oldsave trio's and the other scenarios' saves, the hosttest fixtures, Davide's and the players'
# saves, the 4.1.x ones the import reads): its trailer's EN block -> SWC1 -> section 'IT' (the registry) -> the u16 flags at +8.
def _it_flags(b):
    """[(flags, season)] of every 'IT' section in a save's EN block(s) (none: no EN / SWC1 / 'IT')"""
    import engine
    import trailer
    sid, out = engine.item_id('SWC1'), []
    k = b.find(struct.pack('<H', trailer.EN_MARK))
    while k >= 0:
        p, end = k + 4, k + 4 + struct.unpack_from('<H', b, k + 2)[0]
        ok = end <= len(b)
        while ok and p + 4 <= end:
            iid, ln = struct.unpack_from('<HH', b, p)
            if p + 4 + ln > end:
                break
            if iid == sid and ln >= 24:
                s, q = b[p + 4:p + 4 + ln], 20                  # (SWC1_HDR 20, then u16 id, u16 len sections, id 0 ends)
                while q + 4 <= len(s) and struct.unpack_from('<H', s, q)[0]:
                    i2, n2 = struct.unpack_from('<HH', s, q)
                    if q + 4 + n2 > len(s):
                        break
                    if i2 == 0x5449 and n2 >= 12:
                        out.append(struct.unpack_from('<HH', s, q + 4 + 8)[0:1] + struct.unpack_from('<H', s, q + 4 + 2))
                    q += 4 + n2
            p += 4 + ln
        k = b.find(struct.pack('<H', trailer.EN_MARK), k + 2)
    return out


def test_s7redraw_saves():
    root = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal')
    if not os.path.isdir(root):
        return True, 'SKIP: no internal/'
    n = nit = 0
    bad = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.upper().endswith('.CAR'):
                continue
            n += 1
            try:
                b = open(os.path.join(d, f), 'rb').read()
            except OSError:
                continue
            fl = _it_flags(b)
            nit += bool(fl)
            bad += [(os.path.relpath(os.path.join(d, f), root), hex(x)) for x, _ in fl if x & 0xFC]
    assert not bad, (len(bad), bad[:8])
    return True, f'{n} .CAR saves under internal/, {nit} with a registry section \'IT\': flags bits 2..7 all 0 (the rule version\'s room is free)'


# ---- MC 15/11 conditions 1 + 2: the fallbacks, forced, on the exe -------------------------------------------------------------------------
# (a) the redraw refuses (S7GEO_HAVE poked 0: s7rd_level -> rc -1 before any change), (b) S7_REDRAW_OFF (S7RD_PTR 0, as s7swap.py leaves it
# under the switch), (c) a save from a newer rule (the 'IT' flags' version 2 > S7RD_RULE_VER): each season end = the crossers' place()
# groups exactly (the registry of (b)), Serie B 20, Serie C 3 x 20, Serie D 9 x 18, every ident at most one row, rows = the files';
# (a) S7RD_LOG status 2; (c) S7RD_NEWER 1 and the version kept at 2 (never lowered).
def test_s7redraw_fallback():
    if not os.path.exists(RD_EXE) or not os.path.exists(RD_EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {RD_EXE} missing'
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_s7swap as t7
    m = t7.M(RD_EXE)
    sy = m.sy['s7swap']
    if 'S7RD_NEWER' not in sy or 'S7GEO_HAVE' not in sy:
        return False, f'{RD_EXE}: no S7RD_NEWER / S7GEO_HAVE (a build before the fallback rules)'
    ptr, have, flg = m.at('s7swap', 'S7RD_PTR'), m.at('s7swap', 'S7GEO_HAVE'), m.at('sreg', 'SREG_FLAGS')
    pv, hv = m.rd(ptr, 4), m.rd(have, 1)
    m.fresh()
    fs, word, at, rdiv, rows = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    errs, regs = [], {}

    def shape(name):
        fs1, word1, at1, rdiv1, rows1 = t7.reg_parse(m.regb())
        cnt = {}
        for fi in range(len(fs1)):
            for o in range(rows1[fi]):
                cnt[rdiv1[fi][o]] = cnt.get(rdiv1[fi][o], 0) + 1
        allr = [at1[fi][o] for fi in range(len(fs1)) for o in range(rows1[fi])]
        want = {1: 20, **{d: 20 for d in m.up}, **{d: 18 for d in m.lo}}
        if any(cnt.get(d) != n for d, n in want.items()):
            errs.append(f'{name}: sizes {[(d, cnt.get(d)) for d in sorted(want)]}')
        if len(set(allr)) != len(allr) or any(word1[i] != (fs1[fi][0] | o << 8) for fi in range(len(fs1)) for o, i in enumerate(at1[fi][:rows1[fi]])):
            errs.append(f'{name}: an ident twice / words and rows disagree')
    for name, setup in (('off', lambda: m.w(ptr, bytes(4))), ('refused', lambda: m.w(have, b'\0')),
                        ('newer', lambda: m.w(flg, struct.pack('<I', 2 << 4)))):
        m.fresh()
        m.w(ptr, pv)
        m.w(have, hv)
        setup()
        st, nsw, ncr = _season(m, t7, down, up, t7.SEASON)
        if (st, nsw, ncr) != (t7.OK, 9, 18):
            errs.append(f'{name}: status {st} swaps {nsw} crossers {ncr} (want OK, 9, 18)')
        shape(name)
        regs[name] = m.regb()
        if name == 'refused' and m.rd(m.at('s7swap', 'S7RD_LOG'), 1)[0] != 2:
            errs.append(f'refused: S7RD_LOG {m.rd(m.at("s7swap", "S7RD_LOG"), 8).hex()} (want status 2)')
        if name == 'newer':
            fl = struct.unpack('<I', m.rd(flg, 4))[0]
            if m.rd(m.at('s7swap', 'S7RD_NEWER'), 1)[0] != 1 or (fl >> 4 & 0xF) != 2:
                errs.append(f'newer: S7RD_NEWER {m.rd(m.at("s7swap", "S7RD_NEWER"), 1)[0]}, SREG_FLAGS {fl:#x} (want 1, version 2 kept)')
    for name in ('refused', 'newer'):
        if regs[name] != regs['off']:
            errs.append(f'{name}: registry != the place() groups of S7_REDRAW_OFF')
    m.w(ptr, pv)
    m.w(have, hv)
    return not errs, '; '.join(errs[:5]) or ('S7_REDRAW_OFF, the redraw refused (rc -1) and a newer rule version (2) each end the season with '
                                            'the crossers\' place() groups (the same registry), B 20 / C 3 x 20 / D 9 x 18, no ident twice; '
                                            'refused: S7RD_LOG status 2; newer: S7RD_NEWER 1, the version kept')
