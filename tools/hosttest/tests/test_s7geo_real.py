"""42-s7trap follow-up (MC 16/11): s7geo.c's shared geo functions - s7rd_travel, s7rd_centroid, s7rd_near - pinned on the REAL Italy towns
(world5tm-h3s7rl3/ita/clubs.csv lat / lon, 0.01 degree as s7swap.geo_coords), so that Shaved's rebase of 42-redrawc (which drops its own
copies of travel / centroid) can be proven equal: the OUTPUTS are pinned by md5. Native build of s7geo.c (DATA empty), S7GEO_XY by ident = the
club's index, S7GEO_IDENT the identity on the word.
- INPUT md5: the 162 Serie D clubs' (group, lat, lon) in file order - a changed pack is reported as data, not as code;
- TRAVEL: every Serie D club's travel point (Sardinia from Civitavecchia 4209,1180; Sicily from the Messina strait 3819,1557; the mainland
  unchanged), md5 of the 162 pairs; the island points asserted by value;
- CENTROID: the nine anchors (integer mean of each group's travel points), md5 and the values;
- NEAR: (1) every Serie D club against the 161 others with every group in room: its nearest group, md5 of the 162 answers; (2) named cases,
  asserted by value and pinned: the Sicilian-like club (a Serie D club whose town is in Sicily) with its own group full (room = the others), with
  room only in the far north groups (the island does not make Sardinia / Sicily 'near' the north: it travels from its port), a club
  with no town (the lowest group in room), an empty room set (-1 from the caller's guard: never asked);
  md5 of all the named answers."""
import csv
import ctypes
import hashlib
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CSV = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'world2526', 'world5tm-h3s7rl3', 'ita', 'clubs.csv')
PIN = {'input': '5111e2732e474cb5b8b6a52a63a13191', 'travel': '60888c127cce89d7678bacc4677a068a', 'centroid': '1dce92ba06d4ab26262f908c6433b3bb', 'near_all': '3dfe6d97577f6c04effe00039b1f364b', 'near_cases': 'c8a9bdc157c9d2fd10641c23cca276a5'}      # (pinned 16/11 on 42-s7trap fb3547d's s7geo.c, which carries 42-redrawc's s7rd_travel / s7rd_centroid verbatim)


def _md5(vals):
    return hashlib.md5(repr(vals).encode()).hexdigest()


def _lib():
    d = tempfile.mkdtemp()
    src = os.path.join(d, 'g.c')
    with open(src, 'w') as f:
        f.write('#include <stdint.h>\n#define DATA\n'
                f'#include "{TOOLS}/s7geo.c"\n'
                'static uint32_t ident(uint32_t w) { return w; }\n'
                'void g_init(void) { S7GEO_IDENT = ident; S7GEO_HAVE = 1; }\n'
                'void g_xy(int32_t id, int32_t la, int32_t lo) { S7GEO_XY[id][0] = (int16_t)la; S7GEO_XY[id][1] = (int16_t)lo; }\n')
    lib = os.path.join(d, 'g.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-Wall', '-Werror', '-o', lib, src], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    L = ctypes.CDLL(lib)
    L.s7rd_travel.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]
    L.s7rd_centroid.argtypes = [ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p]
    L.s7rd_near.argtypes = [ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint32, ctypes.c_int32]
    L.s7rd_near.restype = ctypes.c_int32
    return L


def _data():
    rows = [r for r in csv.DictReader(open(CSV, encoding='utf-8')) if r['file'] == 'league_b']
    return [(r['key'], int(r['division']) - 5, round(float(r['lat']) * 100), round(float(r['lon']) * 100)) for r in rows]


def test_s7geo_real():
    if not os.path.exists(CSV):
        return True, f'SKIP: {CSV} missing'
    clubs = _data()
    assert len(clubs) == 162 and sorted({g for _, g, _, _ in clubs}) == list(range(9)), (len(clubs))
    L = _lib()
    L.g_init()
    n = len(clubs)
    for i, (_, _, la, lo) in enumerate(clubs):
        L.g_xy(i, la, lo)
    errs, out = [], {}
    out['input'] = _md5([(g, la, lo) for _, g, la, lo in clubs])
    tr = []
    for _, _, la, lo in clubs:
        a, b = ctypes.c_int32(la), ctypes.c_int32(lo)
        L.s7rd_travel(ctypes.byref(a), ctypes.byref(b))
        tr.append((a.value, b.value))
    out['travel'] = _md5(tr)
    isl = {(a, b) for (a, b), (_, _, la, lo) in zip(tr, clubs) if (a, b) != (la, lo)}
    if not isl <= {(3819, 1557), (4209, 1180)} or not isl:
        errs.append(f'island travel points {sorted(isl)} (want only Messina 3819,1557 / Civitavecchia 4209,1180, at least one)')
    I16 = ctypes.c_int16 * n
    la16, lo16 = I16(*[a for a, _ in tr]), I16(*[b for _, b in tr])
    gr = (ctypes.c_uint8 * n)(*[g for _, g, _, _ in clubs])
    ala, alo = (ctypes.c_int32 * 9)(), (ctypes.c_int32 * 9)()
    L.s7rd_centroid(n, la16, lo16, gr, 9, ala, alo)
    anchors = [(ala[g], alo[g]) for g in range(9)]
    out['centroid'] = _md5(anchors)
    words = (ctypes.c_uint16 * n)(*range(n))
    nd = (ctypes.c_uint8 * n)(*[5 + g for _, g, _, _ in clubs])
    div = (ctypes.c_uint8 * 9)(*range(5, 14))

    def near(c, room, members=None):
        """the nearest group in room for club c among the members (default: every other club of the file)"""
        mem = [k for k in range(n) if k != c] if members is None else members
        ids = (ctypes.c_uint16 * len(mem))(*mem)
        nds = (ctypes.c_uint8 * len(mem))(*[5 + clubs[k][1] for k in mem])
        return L.s7rd_near(len(mem), ids, nds, div, 9, room, c)
    out['near_all'] = _md5([near(c, 0x1FF) for c in range(n)])
    sic = [i for i, (_, _, la, lo) in enumerate(clubs) if 3650 <= la <= 3840 and 1230 <= lo <= 1570]
    sar = [i for i, (_, _, la, lo) in enumerate(clubs) if 3880 <= la <= 4140 and 800 <= lo <= 990]
    if not sic or not sar:
        errs.append(f'the pack has no Sicilian ({len(sic)}) / Sardinian ({len(sar)}) Serie D club')
        return False, '; '.join(errs)
    s0 = sic[0]
    cases = []
    own = 1 << clubs[s0][1]
    cases.append(('sicily own group full', near(s0, 0x1FF & ~own)))                  # every other group in room
    cases.append(('sicily, room only in groups A B C D', near(s0, 0b1111)))             # the far north: travel from Messina, not Palermo
    cases.append(('sardinia, room only in groups A B', near(sar[0], 0b11)))
    cases.append(('club alone in room 1 group', near(s0, 1 << 4)))                      # one group in room: that one
    cases.append(('mainland club (first of the file), own group full', near(0, 0x1FF & ~(1 << clubs[0][1]))))
    # a club without a town: its xy cleared -> the lowest group in room
    L.g_xy(s0, 0, 0)
    cases.append(('no town: the lowest in room', near(s0, 0b110100000)))
    L.g_xy(s0, clubs[s0][2], clubs[s0][3])
    out['near_cases'] = _md5(cases)
    if cases[3][1] != 4 or cases[5][1] != 5:
        errs.append(f'one-group room / no town: {cases[3]} {cases[5]} (want 4 / the lowest in room 5)')
    if any(v < 0 for _, v in cases):
        errs.append(f'a case without an answer: {cases}')
    for k, v in out.items():
        if PIN[k] and PIN[k] != v:
            errs.append(f'{k}: md5 {v} != pinned {PIN[k]} ' + ('(the pack data changed?)' if k == 'input' else '(s7geo.c changed: the shared geo module)'))
    return not errs, '; '.join(errs) or (f'real Italy towns, 162 Serie D clubs: input {out["input"][:8]}, travel {out["travel"][:8]}, anchors '
                                         f'{out["centroid"][:8]} {anchors}, nearest {out["near_all"][:8]}, cases {out["near_cases"][:8]} {cases}')
