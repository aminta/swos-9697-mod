"""4.2 S7 redraw (MC design internal/handoff/s7-redraw.md, item 3 / gate 2): s7geo.c's s7rd_rule, built natively (-m32 not needed:
int32 arithmetic only), against Panchina's oracle goldens tools/s7redraw_golden.json (tools/s7redraw.py rule(), frozen 42-redraw
31db319): every case's groups byte for byte (real 2025-26 -> 2026-27 C and D, the C second teams' seeds 1..5, ten-season chains);
group sizes asserted; no club twice / lost; determinism (each case run twice). Controls: STAY ignored (cost without the last-group
bonus) changes some case; a seed's arrangement changes the C second teams; s7rd_centroid == the oracle's centroid; s7rd_travel ==
travel() on the island boxes' corners."""
import ctypes
import json
import os
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
