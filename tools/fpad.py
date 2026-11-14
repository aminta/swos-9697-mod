"""4.2 fixture port P2 (internal/handoff/motore-fixport-plan.md 1b, MC review 14/11): fpad.c, the adapter between the
engine's sr_port (tools/swce/sr_port.c, vendored: SWCE_SHA) and gplay's slot 4, linked at obj4 + swreg.FPORT_AT.

Dormant unless on(): no byte of it (gplay.c GP_PORT 0, swe.c without FPORT_ON, nothing linked - the dormant proof:
objects identical to 42-int). Until a producer (P4 conti, the Supercoppa Serie C consumer) exists, on() is a test
switch: FPORT=1 (test builds only, modver.is_test), FPORT_TEST: the probe's GPLAY_PROBE entries queued as fixtures.

The slot-4 windows (rule 6) are a static table built here from fport.windows(): FP_DIV (country, division, set) and
FP_SET (the distinct window lists, units as bytes), FP_FMAP[team file] = country; a conditional window (cond 'entrant' / 'alive') counts as on - the superset (a
fixture refused by it is simulated, never a clash)."""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'fpad.c')
PORT_SIZE = 2368                    # (swosrules.h SR_PORT_SIZE: asserted against the header below)
ST_SIZE = 4 + 4 + 16 + 8 + 4 + 8 * 48   # (fpad.c struct fp_st: magic, season..nlog, leg, et + pens, nleg + pad, log)
SLACK = 256                         # (the band's room left at least - MC: stop and report under it)
LABELS = {}


def on():
    if not os.environ.get('FPORT'):
        return False
    import modver
    assert modver.is_test(), 'FPORT: test builds only until a producer (P4 / the Supercoppa Serie C consumer) exists'
    return True


def window_table():
    """(fmap 256 B, rows [(country, div, B, E)], [(country id, problem)]) from the build's career packs"""
    import fport
    import mkseason
    fmap, rows, bad, ci = bytearray(b'\xff' * 256), [], [], 0
    for pk in mkseason.packs():
        lfiles = [pk.files[k][0] for k in ('league', 'league_b') if k in pk.files]
        if pk.kind != 'career' or not lfiles:
            continue
        w = fport.windows(dict(pk.meta, dir=pk.path))
        if 'unresolved' in w:
            bad.append((pk.meta.get('id'), w['unresolved']))
            continue
        assert ci < 255, 'fpad: past 255 countries'
        for f in lfiles:
            assert fmap[f] == 0xFF, ('fpad: a league file in two packs', f, pk.meta.get('id'))
            fmap[f] = ci
        for d, ws in sorted(w.items()):
            for b, e, _user, _cond in ws:      # (cond: on - the static superset)
                rows.append((ci, int(d), b, e))
        ci += 1
    return bytes(fmap), rows, bad


def test_entries():
    """FPORT_TEST (test builds): 'u1/u2/legs/level/flags/opp/file;...' -> [(unit1, unit2, legs, level, flags, opponent
    ordinal, its team file: 0 = the career club's)] - the probe's form (42-fprobe GPLAY_PROBE), level = the port's
    SR_PORT_LV_* (1 e.t. + pens ... 5; 0 = level stays, the group-match case), flags 1 neutral, 4 the career club away,
    opp FFh = auto"""
    out = []
    for e in filter(None, (os.environ.get('FPORT_TEST') or '').split(';')):
        x = [int(t, 0) for t in e.split('/')]
        x += [0, 0, 1, 1, 0, 0xFF, 0][len(x):]
        assert len(x) == 7 and all(0 <= t < 256 for t in x) and x[3] <= 5, e
        out.append(tuple(x))
    return out


def _hdr_define(name):
    s = open(os.path.join(HERE, 'swce', 'swosrules.h')).read()
    i = s.index(f'#define {name} ')
    return int(s[i:].split()[2])


def exact(ws, c, d):
    """a division's windows exactly as fport gives them (sorted, duplicates dropped - nothing merged: MC 14/11, a
    merged gap would make the port refuse a tie the player should play); at most SR_PORT_WINDOWS, else the build stops"""
    out = sorted(set(ws))
    cap = _hdr_define('SR_PORT_WINDOWS')
    assert len(out) <= cap, ('fpad: a division past SR_PORT_WINDOWS - raise it in the engine, never merge', c, d,
                             len(out), cap)
    return out


def pack_windows(rows):
    """rows [(country, div, B, E)] -> (FP_DIV bytes: (country, div, set offset u16) per division with windows, FP_SET
    bytes: per distinct window list n, then B, E bytes - E NONE = FFh). Units are calendar weeks (< 255; asserted)."""
    import fport
    sets, divs = {}, {}
    for c, d, b, e in rows:
        e = 0xFF if e == fport.NONE else e
        assert 0 <= b < 0xFF and 0 <= e <= 0xFF and c < 0xFF and d < 0xFF, ('fpad: a window past a byte', c, d, b, e)
        divs.setdefault((c, d), []).append((b, e))
    blob, off, out = bytearray(), {}, bytearray()
    for (c, d), ws in sorted(divs.items()):
        k = tuple(exact(ws, c, d))
        if k not in off:
            off[k] = len(blob)
            blob += bytes((len(k),)) + b''.join(bytes(w) for w in k)
        out += struct.pack('<BBH', c, d, off[k])
    return bytes(out), bytes(blob)


def vendored():
    """(SWCE_SHA, {file: sha1}) of the engine sources fpad.c includes (hosttest test_fpad_vendor compares)"""
    import hashlib
    import swce
    return swce.SWCE_SHA, {f: hashlib.sha1(open(os.path.join(HERE, 'swce', f), 'rb').read()).hexdigest()
                           for f in ('sr_port.c', 'swosrules.h')}


def patch(p, ssyms, gsyms):
    """links fpad.c at obj4 + FPORT_AT (ssyms swe.c's: FP_PORT / FP_ST, gsyms gplay's hooks); returns the end, or
    None (dormant)"""
    if not on():
        return None
    import cobj
    import engine
    import gplay
    import swe
    import swreg
    assert _hdr_define('SR_PORT_SIZE') == PORT_SIZE, ('fpad: SR_PORT_SIZE', _hdr_define('SR_PORT_SIZE'), PORT_SIZE)
    assert gsyms.get('SC_ON'), 'fpad: gp_sc not built (SC_ON 0): sc_step_c, the port\'s step, never runs'
    for k in ('GP_PAPI', 'GP_PSTEP', 'GP_PDONE', 'GP_PLEG', 'GP_PSEAS', 'GP_WK', 'GP_MGR', 'GP_SEAS', 'CAL'):
        assert k in gsyms, ('fpad: gplay without', k)
    assert 'FP_PORT' in ssyms and 'FP_ST' in ssyms, 'fpad: swe.c without FPORT_ON (swe.py)'
    assert p.le.obj(4).npages * 0x1000 >= swreg.FPORT_END, 'fpad: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.FPORT_AT, swreg.FPORT_END - swreg.FPORT_AT)), 'fpad: obj4+FPORT_AT not free'
    band = swe.OBJ4_PAGES * 0x1000
    obj_tab = p.le.hdr + struct.unpack_from('<I', p.out, p.le.hdr + 0x40)[0]
    vsize = struct.unpack_from('<I', p.out, obj_tab + 3 * 24)[0]   # (obj4's vsize as swe.py set it: p.set_vsize)
    for k, n in (('FP_PORT', PORT_SIZE), ('FP_ST', ST_SIZE)):   # (swe.c's .bss: past every obj4 band, inside the vsize)
        o, a = ssyms[k]
        assert o == 4 and a >= band and a + n <= vsize, ('fpad: swe.c .bss', k, hex(a), hex(band), hex(vsize))
    fmap, rows, bad = window_table()
    for cc, why in bad:
        print(f'exe: fpad: {cc}: windows unresolved ({why}) - no window: the engine refuses nothing there')
    fdiv, fset = pack_windows(rows)
    ext = {'GP_PAPI': gsyms['GP_PAPI'], 'GP_WK': gsyms['GP_WK'], 'GP_MGR': gsyms['GP_MGR'],
           'GP_SEAS': gsyms['GP_SEAS'], 'FP_CAL': gsyms['CAL'], 'FP_PORT': ssyms['FP_PORT'], 'FP_ST': ssyms['FP_ST']}
    flags = [f'-DFP_ST_SZ={ST_SIZE}', f'-DFP_NDIV_={max(1, len(fdiv) // 4)}', f'-DFP_NSET_={max(1, len(fset))}']
    roots = ['fp_step', 'fp_leg', 'fp_done', 'fp_new', 'fp_load', 'fp_season', 'FP_FMAP', 'FP_DIV', 'FP_SET', 'FP_NDIV']
    test = test_entries()
    if test:
        flags += ['-DFPORT_TEST', f'-DFP_NTEST_={len(test)}']
        roots += ['FP_TEST', 'FP_NTEST']
    obj = cobj.compile_c(SRC, tuple(flags), sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.FPORT_AT, (4, 0), externs=ext, limit=swreg.FPORT_END, text_obj=4,
                               roots=roots)
    assert not bss, ('fpad.c: no .bss (it would land on swe.c\'s)', bss)
    left = swreg.FPORT_END - end
    assert left >= SLACK, ('fpad: the FPORT band has under 256 B left - stop and report to MC', left)
    p.put(*syms['FP_FMAP'], fmap)
    p.put(*syms['FP_DIV'], fdiv)
    p.put(*syms['FP_SET'], fset)
    p.put(*syms['FP_NDIV'], struct.pack('<H', len(fdiv) // 4))
    if test:
        p.put(*syms['FP_TEST'], b''.join(bytes(e) for e in test))
        p.put(*syms['FP_NTEST'], struct.pack('<H', len(test)))
    for hook, f in (('GP_PSTEP', 'fp_step'), ('GP_PDONE', 'fp_done'), ('GP_PLEG', 'fp_leg'), ('GP_PSEAS', 'fp_season')):
        cobj.add_ptr(p, gsyms[hook][1], *syms[f], gsyms[hook][0])
    engine.CALL_AT['fp_new'] = syms['fp_new']
    engine.CALL_AT['fp_load'] = syms['fp_load']
    LABELS.update(syms)
    LABELS['FP_PORT'], LABELS['FP_ST'] = ssyms['FP_PORT'], ssyms['FP_ST']
    print(f'exe: fixture port (fpad.c) obj4+{swreg.FPORT_AT:#x}..{end:#x} of {swreg.FPORT_END:#x} ({left} B left), '
          f'{len(rows)} slot-4 windows ({len(fdiv) // 4} divisions, {len(fset)} B of sets), {256 - fmap.count(255)} league files'
          + (f', FPORT_TEST {len(test)} fixtures' if test else ''))
    return end
