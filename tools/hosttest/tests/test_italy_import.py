"""N7 piece 4 (n7-p4.md §7): the absent-'IT' import on REAL 4.1 Italy career saves, host-only (sreg_import.c built
natively). The saves: the c20 Inter career on REL41rc3 (internal/swostest/n7/saves/c20_after_s02..s19.CAR, World
2026-27, one per season end: RI swaps from the second one on, s04 = "relegated twice", s05+ = the reverse case, see
s7-twice-scan.md) + IT_IMPORT_CARS (more .CARs, comma-separated: e.g. a Serie D club's career). The 4.1 side is
REL41rc3's own data (DATA/TMW5.102: each slot's base division +25 and global +2, big-endian; data world world5tm-403c19); the S7
side is s7pack's pack from world5tm-h2/ita + internal/n7/s7-groups.csv (as test_s7pack), the RI tables of both from
mkseason.off_pools() (4.1: Italy on 102 at map offset 0, 256 slots, pool 42; S7: on 144, 162 slots, pool 36).

For every save, three steps as the S7 glue will run them (MC's option 1, model (i)):
- sreg_import: nd[] from each slot's actual division (TMW5.102 +25 + the save's someLeaguesTable delta at its global)
  and RI's maps; then every club on a 4.1 slot has a map pair (every word resolved), every slot word 102|x has exactly
  one, no new word on file 102 has an ordinal >= 100 (Serie D is off 102), the registry's division of every club on a
  slot = its actual 4.1 division (the 6 joiners: PENDING, their S7 group), flags IMPORTED | PENDING | season;
- sreg_ri_import: the save's RI_STATE -> S7's (0: no refusal);
- sreg_slt_import: someLeaguesTable re-based on the clubs' S7 records (new base = the registry's division): every
  Italy club on a row now has delta 0 at its S7 global (its record carries its actual division), the other countries'
  bytes unchanged;
- roundtrip_old (n7-p4.md §7, the registry's part): the imported registry's 'IT' section (sr_reg_save, flags at +8)
  loaded into a spec-built registry over other garbage gives the same state (rdiv[] aside: not in the section by
  design, the exe re-reads it from its records' division bytes after a load), and saving it again gives the same
  section: upgraded once, then a fixed point (the exe's round trip waits for the S7 glue's call site);
- all deterministic: two runs from different garbage give the same bytes.
Shape checks: s04's pergolettese (4.1 identity 55) is in S7's RI queue, s05+'s on a file-144 row with no RI map there."""
import csv
import ctypes
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
M = os.path.expanduser('~/swos-mod')
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

REL = os.environ.get('IT_IMPORT_REL') or os.path.join(M, 'c', 'REL41rc3', 'SWOS', 'DATA')
WORLD41 = os.environ.get('IT_IMPORT_WORLD') or 'world5tm-403c19'      # (REL41rc3's data world: its build.log)
SAVES = os.path.join(M, 'internal', 'swostest', 'n7', 'saves')
DEFAULT_CARS = ('davide-mister-2026102*/*.CAR', 'player-saves/*/*.CAR', 'reports/*.CAR', 'swostest/guests_end_squads.CAR',
                'swostest/saves/guests_end_squads-*.CAR', 'uesum/*.CAR')     # (IT_IMPORT_CARS='' : the c20 saves only)
SLT, CT = 59612, 56192                          # .CAR: someLeaguesTable (2000 B, world byte at +1845), careerTeam
RI_SIZE, RI_MAPS, RI_Q, RI_QN = 2332, 1052, 28, 8
POOL, OUT, NONE = 0xFE, 0xFF, 0xFFFF
CLUBS, FILES = 1024, 8


def _recs(p):
    d = open(p, 'rb').read()
    n = struct.unpack('>H', d[:2])[0]
    return [d[2 + 684 * i:2 + 684 * (i + 1)] for i in range(n)]


def _lib(d):
    src = os.path.join(d, 'ii.c')
    with open(src, 'w') as f:
        f.write('#define SWOSRULES_HAVE_STDINT\n#include <stdint.h>\n'
                f'#include "{TOOLS}/swce/sr_reg.c"\n#include "{TOOLS}/swce/sr_regsave.c"\n'
                f'#include "{os.environ.get("IT_IMPORT_C") or os.path.join(TOOLS, "sreg_import.c")}"\n'
                'uint32_t imp_work_size(void) { return sizeof(sreg_imp_work); }\n'
                'uint32_t imp_res_size(void) { return sizeof(sreg_imp_res); }\n'
                'uint32_t ri_work_size(void) { return sizeof(sreg_ri_work); }\n'
                'uint32_t reg_size(void) { return sizeof(sr_registry); }\n')
    lib = os.path.join(d, 'ii.dylib')
    r = subprocess.run(['cc', '-shared', '-fPIC', '-O1', '-Wall', '-Werror', '-I', os.path.join(TOOLS, 'swce'), '-o',
                        lib, src], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('cc: ' + r.stderr[-400:])
    L = ctypes.CDLL(lib)
    import test_sreg
    test_sreg._imp_protos(L)
    P, I32, U32, U16 = ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint16
    L.sr_reg_layout.argtypes, L.sr_reg_layout.restype = [I32, P, I32], U32
    L.sr_reg_save.argtypes, L.sr_reg_save.restype = [P, U32, U16, P, I32], I32
    L.sr_reg_load.argtypes, L.sr_reg_load.restype = [P, U32, P, I32], I32
    L.sr_reg_build.argtypes, L.sr_reg_build.restype = [P, I32, P, I32, P], I32
    return L


def _gl(files):                                 # sreg_slt_import's run tables (globnum.glob's runs)
    return bytes([len(files)]) + b''.join(bytes([fl, len(rs)]) + b''.join(struct.pack('<HH', a, c) for a, c in rs)
                                          for fl, rs in files)


def _rowbase(files, w):
    """the S7 row's shipped division (the league's index) of team word w, 0 off the files (sreg2.c rowbase)"""
    if w == NONE:
        return 0
    for f, divs, _ in files:
        if f == w & 0xFF:
            r = 0
            for d, k in divs:
                r += k
                if (w >> 8) < r:
                    return d
    return 0


def _sides(tmp):
    """(the S7 pack, its shape / old_ord / newpool, the 4.1 and S7 RI layouts, the S7 globals) - mkseason on REL41rc3's
    world, then the same packs with Italy replaced by s7pack's (ENABLED / caches restored after)."""
    import test_globnum
    import test_s7pack
    prev, prevw = os.environ.get('SEASON_PACKS'), os.environ.get('HT_GLOB_WORLD')
    os.environ['HT_GLOB_WORLD'] = WORLD41
    test_globnum._env()
    import mkseason
    import globnum
    import sreg
    import s7pack
    old_en = mkseason.ENABLED
    try:
        en = os.environ['SEASON_PACKS'].split(',')
        mkseason.ENABLED = en
        for f in (mkseason.packs,):
            f.__dict__.pop('cache', None)
        globnum._split_cached.cache_clear()
        lay41 = sreg.ri_layout(mkseason.off_pools())
        out = os.path.join(tmp, 'ita')
        s7pack.build(test_s7pack.SRC, test_s7pack.GROUPS, out)
        ita = [p for p in en if p.rstrip('/').endswith(os.path.join(WORLD41, 'ita'))]
        assert len(ita) == 1, ('the world\'s Italy pack', ita)
        mkseason.ENABLED = [out if p in ita else p for p in en]
        mkseason.packs.__dict__.pop('cache', None)
        globnum._split_cached.cache_clear()
        lay7 = sreg.ri_layout(mkseason.off_pools())
        pk = next(p for p in mkseason.packs() if os.path.realpath(p.path) == os.path.realpath(out))
        world, files, divs = sreg.shape_of(pk)
        gl7 = _gl([(f, globnum.runs_of(pk, f)) for f, _, _ in files])
        keys = list(pk.clubs)
        return dict(world=world, files=files, divs=divs, old=sreg.old_ord(pk), newpool=sreg.new_pool(pk), keys=keys,
                    spec=sreg.spec_bytes(files), lay41=lay41, lay7=lay7, gl7=gl7,
                    glob7={(f, i): globnum.glob(pk, f, i) for f, d, p in files for i in range(sum(n for _, n in d) + p)})
    finally:
        mkseason.ENABLED = old_en
        mkseason.packs.__dict__.pop('cache', None)
        globnum._split_cached.cache_clear()
        for k, v in (('SEASON_PACKS', prev), ('HT_GLOB_WORLD', prevw)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _import(L, S, car, fill):
    """the three steps on one save from arenas of `fill`; -> (results, the bytes compared for determinism)"""
    d = open(car, 'rb').read()
    rid = __import__('engine').item_id('RI')
    p = d.find(struct.pack('<HH', rid, RI_SIZE))
    ri = d[p + 4:p + 4 + RI_SIZE] if p >= 0 else bytes(RI_SIZE)
    slt = d[SLT:SLT + 2000]
    t102 = S['t102']
    maps = struct.unpack_from('<256H', ri, RI_MAPS)
    slot = bytes((t102[x][25] + struct.unpack('b', slt[92 + x:93 + x])[0]) & 0xFF for x in range(256))
    n, nf = len(S['keys']), len(S['files'])
    R = ctypes.create_string_buffer(bytes([fill]) * L.reg_size(), L.reg_size())
    wk = ctypes.create_string_buffer(bytes([fill]) * L.imp_work_size(), L.imp_work_size())
    res = ctypes.create_string_buffer(bytes([fill]) * L.imp_res_size(), L.imp_res_size())
    sw, mp = (ctypes.c_uint16 * (3 * 512))(), (ctypes.c_uint16 * 2048)()
    old = (ctypes.c_uint16 * n)(*S['old'])
    spec = ctypes.create_string_buffer(S['spec'], len(S['spec']))
    season = S['season']
    qn = ri[RI_QN]                                      # (Italy = RI pool 0, queue at 0: REL41rc3's layout)
    queue = struct.unpack_from(f'<{qn}H', ri, RI_Q) if ri[0] else ()
    if S.get('cut') is not None:
        queue = queue[:S['cut']]
    ns = L.sreg_import(R, spec, nf, bytes(S['divs']), n, old, (ctypes.c_uint16 * 256)(*maps), 256, 42, 102, slot,
                       (ctypes.c_uint16 * max(len(queue), 1))(*queue), len(queue), 144, season, wk, sw, 512, mp, 1024,
                       res)
    nswap, nmap, npend, bad, flags = struct.unpack_from('<iiiiI', res.raw)
    out = dict(ns=ns, nmap=nmap, npend=npend, bad=bad, flags=flags, ri=ri, slt=slt, slot=slot, maps=maps, queue=queue)
    if ns < 0:
        return out, (ns, bad)
    out['pend'] = list(struct.unpack_from(f'<{npend}H', res.raw, 20))
    out['map'] = [(mp[2 * k], mp[2 * k + 1]) for k in range(nmap)]
    rb = R.raw
    wo = 8 + FILES * 36                                 # (sr_registry: nfiles, nclub, f[8] x 36 B, word[], at[][], rdiv[][])
    out['word'] = struct.unpack_from(f'<{n}H', rb, wo)
    at = wo + 2 * CLUBS
    rdiv = at + FILES * 512
    out['rdiv'] = [rb[rdiv + 256 * i:rdiv + 256 * (i + 1)] for i in range(FILES)]
    wb = wk.raw
    out['old_word'] = struct.unpack_from(f'<{n}H', wb, 0)
    out['nd'] = wb[2 * CLUBS:2 * CLUBS + n]
    # RI_STATE -> S7
    riw = ctypes.create_string_buffer(bytes([fill]) * L.ri_work_size(), L.ri_work_size())
    new_ri = ctypes.create_string_buffer(bytes([fill]) * RI_SIZE, RI_SIZE)
    rbad = ctypes.c_int32()
    rk = L.sreg_ri_import(R, spec, nf, bytes(S['divs']), n, old, sw, ns, S['newpool'], 42, S['lay41'], S['lay7'],
                          S['world'], 102, 144, ri, new_ri, riw, ctypes.byref(rbad))
    out['rk'], out['rbad'], out['new_ri'] = rk, rbad.value, new_ri.raw
    # someLeaguesTable: old base = the 4.1 slot's +25 (ri_copy keeps it), new base = the S7 ROW's shipped division (the
    # exe's convention, MC 15/11: s7_load's rec_copy keeps a row's byte 25, as s7_season / put_slot; sreg2.c rowbase)
    ob = bytes(t102[ow >> 8][25] if ow != NONE else 0 for ow in out['old_word'])
    nb = bytes(_rowbase(S['files'], w) for w in out['word'])
    new_slt = ctypes.create_string_buffer(bytes([fill]) * 2400, 2400)
    sbad = ctypes.c_int32()
    sk = L.sreg_slt_import(R, wk, n, _gl([(102, [(92, 256)])]), S['gl7'], ob, nb, 14, slt + bytes(400), new_slt, 2400,
                           ctypes.byref(sbad))
    out['sk'], out['sbad'], out['new_slt'] = sk, sbad.value, new_slt.raw
    rows = rdiv + FILES * 256                           # (the state sr_reg_build writes: test_sreg.view's, nf files)

    def state(b, div=True):                             # (div False: rdiv[] is not in 'IT' - sr_regsave.c: a load
        return (b[:8 + nf * 36] + b[wo:wo + 2 * n] + b[at:at + nf * 512] +   # leaves each row's division as built,
                (b[rdiv:rdiv + nf * 256] if div else b'') + b[rows:rows + 2 * nf])   # the exe sets it from its records)
    # roundtrip_old: upgraded once (this import), then a fixed point - the section sreg_save writes (flags at +8),
    # loaded into a registry built from the spec over other garbage, gives the same state and the same section again
    lay = L.sr_reg_layout(nf, spec, n)
    room = 4096
    b1 = ctypes.create_string_buffer(room)
    k1 = L.sr_reg_save(R, lay, season, b1, room)
    rt = None
    if k1 <= 0:
        rt = f'sr_reg_save {k1}'
    else:
        ctypes.memmove(ctypes.addressof(b1) + 8, struct.pack('<H', out['flags'] & 0xFFFF), 2)
        R2 = ctypes.create_string_buffer(bytes([fill ^ 0x5A]) * L.reg_size(), L.reg_size())
        ld = -9 if L.sr_reg_build(R2, nf, spec, n, bytes(S['divs'])) else L.sr_reg_load(R2, lay, b1, k1)
        b2 = ctypes.create_string_buffer(room)
        k2 = L.sr_reg_save(R2, lay, season, b2, room) if ld == 1 else -1
        if k2 > 0:
            ctypes.memmove(ctypes.addressof(b2) + 8, b1.raw[8:10], 2)
        st = state(R2.raw, False) == state(rb, False)
        if ld != 1 or not st or k2 != k1 or b2.raw[:k2] != b1.raw[:k1]:
            rt = (f'load {ld}, state {"=" if st else "!="}, sizes {k1} / {k2}, '
                  f'section {"=" if b2.raw[:max(k2, 0)] == b1.raw[:k1] else "!="}')
    out['rt'], out['it'] = rt, b1.raw[:max(k1, 0)]
    det = (ns, state(rb), res.raw[:20 + 2 * npend],
           bytes(sw)[:6 * ns], bytes(mp)[:4 * nmap], rk, new_ri.raw, sk, new_slt.raw, out['it'])
    return out, det


def _oracle(S, o):
    """option B (MC 12/11) in Python, from the save alone: (the PENDING idents sorted, [(substituted slot, filler)]).
    A joiner off the files: PENDING. A stand-in on a slot now outside Serie D (division < 5): its slot to the next
    filler, in slot order; then each free Serie D row (162 - the Serie D clubs on slots - the off joiners) to the next
    filler. Fillers: spec Serie D (5..13), a 4.1 row, off the files; the save's RI queue order, then ident order."""
    keys, old, divs = S['keys'], S['old'], S['divs']
    ident = [m - 1 if m else x for x, m in enumerate(o['maps'])]
    on = {i: x for x, i in enumerate(ident)}
    club = {v: c for c, v in enumerate(old) if v != 0xFFFF}
    joiner = [c for c in range(len(keys)) if 5 <= divs[c] <= 13 and (old[c] == 0xFFFF or old[c] >= 256)]
    pend = [c for c in joiner if old[c] not in on]
    kind = sorted(on[old[c]] for c in range(len(keys)) if divs[c] == 0xFF and old[c] in on and o['slot'][on[old[c]]] < 5)
    order = [club[e] for e in o['queue'] if e in club] + list(range(len(keys)))
    taken, fill = set(), []

    def nxt():
        for c in order:
            if c not in taken and 5 <= divs[c] <= 13 and old[c] < 256 and old[c] not in on:
                taken.add(c)
                return c
        return None
    kinds = [(x, nxt()) for x in kind]
    nd_d = sum(1 for x in range(256) if o['slot'][x] >= 5)
    for _ in range(162 - nd_d - len(pend)):
        fill.append(nxt())
    return sorted(pend + fill), kinds


def _check(S, o, tag):
    errs = []
    keys, old, divs = S['keys'], S['old'], S['divs']
    if o['ns'] < 0:
        k = o['bad']
        return [f'{tag}: sreg_import {o["ns"]}, club {keys[k] if 0 <= k < len(keys) else hex(k)}']
    if o['rt']:
        errs.append(f'{tag}: roundtrip_old {o["rt"]}')
    if o['rk'] or o['sk'] < 0:
        return [f'{tag}: sreg_ri_import {o["rk"]} (club {o["rbad"]}), sreg_slt_import {o["sk"]} (club {o["sbad"]})']
    frm = [a for a, _ in o['map']]
    on = [c for c in range(len(keys)) if o['old_word'][c] != NONE]
    mp = dict(o['map'])                                 # (sr_wmap_get: no pair = the word kept)
    miss = [(keys[c], hex(o['old_word'][c]), hex(mp.get(o['old_word'][c], o['old_word'][c])), hex(o['word'][c]))
            for c in on if mp.get(o['old_word'][c], o['old_word'][c]) != o['word'][c]]
    if miss:
        errs.append(f'{tag}: {len(miss)} 4.1 word(s) not resolved to the registry\'s: {miss[:4]}')
    slots = sorted(o['old_word'][c] >> 8 for c in on)
    if slots != list(range(256)) or len(frm) != len(set(frm)):
        errs.append(f'{tag}: 4.1 slots covered {len(set(slots))}/256, map from-words unique {len(frm) == len(set(frm))}')
    hi = [(hex(a), hex(b)) for a, b in o['map'] if b & 0xFF == 102 and b >> 8 >= 100]
    hi += [(keys[c], hex(w)) for c, w in enumerate(o['word']) if w != NONE and w & 0xFF == 102 and w >> 8 >= 100]
    if hi:
        errs.append(f'{tag}: file 102 ordinals >= 100 left: {hi[:4]}')
    pend = set(o['pend'])
    wrong = []
    for c in range(len(keys)):
        w = o['word'][c]
        if w == NONE:
            continue
        fi = next(i for i, (f, _, _) in enumerate(S['files']) if f == w & 0xFF)
        dv = o['rdiv'][fi][w >> 8]
        want = divs[c] if c in pend else o['slot'][o['old_word'][c] >> 8] if o['old_word'][c] != NONE else None
        if want is not None and dv != want:
            wrong.append((keys[c], dv, want))
    if wrong:
        errs.append(f'{tag}: registry division != the actual 4.1 one: {wrong[:4]}')
    want_p, want_k = _oracle(S, o)
    if sorted(pend) != want_p or len(pend) != 6:
        errs.append(f'{tag}: pending {[keys[c] for c in sorted(pend)]} (want {[keys[c] for c in want_p]})')
    for x, f in want_k:                                 # (substitution: the filler holds the stand-in's slot word)
        if o['old_word'][f] != (102 | x << 8) or o['nd'][f] != o['slot'][x]:
            errs.append(f'{tag}: slot {x} substituted by {keys[f]}: old word {o["old_word"][f]:#x}, nd {o["nd"][f]}')
    want_fl = 1 | 2 | (S['season'] & 0xFF) << 8
    if o['flags'] != want_fl:
        errs.append(f'{tag}: flags {o["flags"]:#x} (want {want_fl:#x})')
    # someLeaguesTable: every Italy club on a row gets delta = its actual division - the row's shipped base (the exe's
    # convention, MC 15/11: s7_season / put_slot read record +25 = the row's base); others kept
    g7 = set(S['glob7'].values())
    nz = []
    for c, w in enumerate(o['word']):
        if w == NONE or o['old_word'][c] == NONE:
            continue
        g = S['glob7'][(w & 0xFF, w >> 8)]
        want = (o['nd'][c] - _rowbase(S['files'], w)) & 0xFF
        if o['new_slt'][g] != want:
            nz.append((keys[c], g, o['new_slt'][g], want))
    if nz:
        errs.append(f'{tag}: S7 deltas != actual - row base: {nz[:4]}')
    kept = [g for g in range(2000) if g not in g7 and not 92 <= g < 348 and o['new_slt'][g] != o['slt'][g]]
    if kept:
        errs.append(f'{tag}: other globals changed: {kept[:6]}')
    return errs


def test_italy_import():
    need = [REL, SAVES, os.path.join(M, 'internal', 'world2526', WORLD41)]
    import test_s7pack
    need += [test_s7pack.SRC, test_s7pack.GROUPS]
    miss = [p for p in need if not os.path.exists(p)]
    if miss:
        return True, f'SKIP: private data missing {miss}'
    cars = sorted(glob.glob(os.path.join(SAVES, 'c20_after_s*.CAR')))
    extra = os.environ.get('IT_IMPORT_CARS')
    if extra is None:                                   # (n7-six-real.md's set: every other World 2026-27 .CAR we have)
        extra = ','.join(sorted(c for pat in DEFAULT_CARS for c in glob.glob(os.path.join(M, 'internal', pat))))
    cars += [c for c in extra.split(',') if c]
    tmp = tempfile.mkdtemp(prefix='itimp')
    try:
        S = _sides(tmp)
        S['t102'] = _recs(os.path.join(REL, 'TMW5.102'))
        L = _lib(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    errs = []
    bad_g = [x for x in range(256) if struct.unpack_from('>H', S['t102'][x], 2)[0] != 92 + x]
    if len(S['t102']) != 256 or bad_g:
        return False, f'TMW5.102: {len(S["t102"])} records, globals not 92 + x at {bad_g[:4]}'
    keys = S['keys']
    peg = keys.index('pergolettese') if 'pergolettese' in keys else None
    stats = []
    for car in cars:
        tag = os.path.basename(car)[:-4]
        d = open(car, 'rb').read()
        if d[SLT + 1845] != S['world'] or len(d) < SLT + 2000:
            if car.startswith(SAVES):
                errs.append(f'{tag}: world {d[SLT + 1845] if len(d) > SLT + 1845 else "?"}')
            continue                                    # (an extra save of another world: not an import case)
        S['season'] = 27                                # (the shaped section's season byte: a 4.1 save = 2026-27's line)
        a, da = _import(L, S, car, 0xAA)
        b, db = _import(L, S, car, 0x11)
        if da != db:
            errs.append(f'{tag}: not deterministic in part(s) {[i for i, (x, y) in enumerate(zip(da, db)) if x != y]}')
        errs += _check(S, a, tag)
        if a['ns'] < 0:
            continue
        nri = sum(1 for m in a['maps'] if m)
        stats.append(f'{tag.replace("c20_after_", "")} {a["ns"]}sw/{nri}ri')
        if peg is not None and tag in ('c20_after_s04', 'c20_after_s05'):
            qn = a['new_ri'][RI_QN]
            q = struct.unpack_from(f'<{qn}H', a['new_ri'], RI_Q)
            w = a['word'][peg]
            if tag.endswith('s04') and (w != NONE or not any(e < 256 for e in q)):
                errs.append(f'{tag}: pergolettese word {w:#x}, S7 queue {q[:8]}')
            if tag.endswith('s05'):
                m7 = struct.unpack_from('<162H', a['new_ri'], RI_MAPS)
                if w == NONE or w & 0xFF != 144 or m7[w >> 8]:
                    errs.append(f'{tag}: pergolettese word {w:#x}, S7 map there {m7[w >> 8] if w != NONE else "-"}')
    # MC 12/11 point 2: the queue cut short (here: none of it) - the fillers come in spec order, the same checks
    for tag, cut in (('c20_after_s05', 0), ('c20_after_s05', 3)):
        car = os.path.join(SAVES, tag + '.CAR')
        if not os.path.exists(car):
            continue
        S['cut'] = cut
        a, da = _import(L, S, car, 0xAA)
        _, db = _import(L, S, car, 0x11)
        S['cut'] = None
        if da != db:
            errs.append(f'{tag} queue cut to {cut}: not deterministic')
        errs += _check(S, a, f'{tag} queue cut to {cut}')
    return not errs, '; '.join(errs) or (f'{len(stats)} real 4.1 saves imported (swaps / 4.1 RI maps: '
                                         f'{", ".join(stats)}): every slot word mapped once, no 102 ordinal >= 100, '
                                         'registry = actual divisions, the 6 pending (option B: joiners off + fillers by queue / spec order, '
                                         'substitutions), queue cut short (s05: 0 / 3 entries) the same, RI + slt translated (S7 deltas = actual - row base, '
                                         'other countries kept), IT round trip a fixed point, deterministic; s04 pergolettese queued, s05 on 144')
