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
SRC2 = os.path.join(HERE, 'fpsave.c')       # P5 (MC 15/11): fp_save / fps_load + sr_port_save / _load, obj4 FPORT2
PORT_SIZE = 2368                    # (swosrules.h SR_PORT_SIZE: asserted against the header below)
ST_SIZE = 4 + 4 + 16 + 8 + 4 + 8 * 48   # (fpad.c struct fp_st: magic, season..nlog, leg, et + pens, nleg + pad, log)
SLACK = 256                         # (the band's room left at least - MC: stop and report under it)
# P5 (MC option A): the EN item 'FP' = a 36-B header ('FPS1', season, the tie in progress: legs played, their goals, e.t.,
# penalties - FP_ST's, not in sr_port) + sr_port_save's bytes, at most 20 + SR_PORT_MAX x (33 + 16) (all played)
SAVE_HDR, SAVE_VERSION = 36, 1
SAVE_SIZE = SAVE_HDR + 20 + 48 * (33 + 16)


def fp_hash():
    """MC P5 review: FP_HASH covers only what a saved fixture refers to by identity - the world byte and the format
    (SR_PORT_SIZE, SR_PORT_MAX, the item header's version); never the window table (revalidated live)"""
    import zlib
    return zlib.crc32(struct.pack('<BHHB', world(), PORT_SIZE, 48, SAVE_VERSION)) & 0xFFFFFFFF
LABELS = {}


def on():
    if not os.environ.get('FPORT'):
        return False
    import modver
    assert modver.is_test(), 'FPORT: test builds only until a producer (P4 / the Supercoppa Serie C consumer) exists'
    return True


def world():
    """the one world the port runs in (P2: team files are per world - FPORT_WORLD, default 5 = World 2026-27); fp_step
    leaves the port off in a career of any other world"""
    return int(os.environ.get('FPORT_WORLD') or 5)


def window_table():
    """(fmap 256 B, rows [(country, div, B, E)], [(country id, problem)]) from the build's career packs of world()"""
    import fport
    import mkseason
    fmap, rows, bad, ci = bytearray(b'\xff' * 256), [], [], 0
    for pk in mkseason.packs():
        lfiles = [pk.files[k][0] for k in ('league', 'league_b') if k in pk.files]
        if pk.kind != 'career' or pk.world != world() or not lfiles:
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
    rows = win_edit(rows)
    return bytes(fmap), rows, bad


def win_edit(rows):
    """FPORT_WINEDIT (test builds only - world_fport_ld_win): '+B:E' adds the window [B, E] to every division with
    windows, '-B' drops every window starting at B; ',' between edits"""
    ed = os.environ.get('FPORT_WINEDIT')
    if not ed:
        return rows
    assert os.environ.get('FPORT_TEST'), 'fpad: FPORT_WINEDIT is for FPORT_TEST builds only'
    for e in ed.split(','):
        if e[0] == '+':
            b, e2 = (int(x) for x in e[1:].split(':'))
            rows = rows + [(c, d, b, e2) for c, d in sorted({(r[0], r[1]) for r in rows})]
        else:
            rows = [r for r in rows if r[2] != int(e[1:])]
    return rows


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


OFFS = ('O_KO', 'O_SEASON', 'O_KIND', 'O_TW', 'O_TEAM', 'O_D1', 'O_D2', 'O_RS', 'O_MDIV', 'C_MAGIC', 'C_NOC', 'C_KPORT',
        'C_NEUTRAL', 'C_SCE', 'C_SCUEFA', 'KO_SIZE')


def gp_offsets(cflags):
    """gplay.c's struct offsets / constants fpad.c reads (MC 14/11 (b)+(c): no byte of them in gplay): GP_OFFS of a
    -DGP_OFFSETS compile of gplay.c with the build's own flags (gplay.LABELS['GP_CFLAGS']) -> {name: value}"""
    import cobj
    obj = cobj.compile_c(os.path.join(HERE, 'gplay.c'), tuple(cflags) + ('-DGP_OFFSETS',), sections=True)
    secs = cobj._elf(obj)
    symtab = next(s for s in secs if s['type'] == 2)
    strtab = secs[symtab['link']]
    for k in range(symtab['size'] // 16):
        name, value, size, _info, _o, shndx = struct.unpack_from('<IIIBBH', obj, symtab['offset'] + 16 * k)
        a = strtab['offset'] + name
        if obj[a:obj.index(b'\0', a)] == b'GP_OFFS':
            assert size == 2 * len(OFFS), ('fpad: GP_OFFS', size)
            v = struct.unpack_from(f'<{len(OFFS)}H', obj, secs[shndx]['offset'] + value)
            return dict(zip(OFFS, v))
    raise AssertionError('fpad: no GP_OFFS in gplay.c -DGP_OFFSETS')


def fp_et_sites(p):
    """obj1 offsets of cseg_2AE97's two `call cseg_2B81B` (the extra time: `or byte [D7], 4`, 9 pushes, the call -
    bplace.force's pattern), read on the original bytes"""
    import re
    import sacups
    d = p.le.obj_bytes(1)
    d7 = struct.pack('<I', sacups.regs(d)['D7'])
    sites = [m.end() - 5 for m in re.finditer(rb'\x80\x0d' + re.escape(d7) + rb'\x04(?:\xff\x35....){9}\xe8....', d, re.S)]
    assert len(sites) == 2, ('fpad: cseg_2AE97 extra-time calls', [hex(x) for x in sites])
    tgt = {o + 5 + struct.unpack_from('<i', d, o + 1)[0] for o in sites}
    assert len(tgt) == 1, ('fpad: the extra-time calls reach two routines', tgt)
    return sites, tgt.pop()


def et_chain_end(p, t, end):
    """follows a chained hook (a routine whose first instruction is a call / jmp to what the site reached before:
    bplace.force's bf_et; never fp_et itself) to its end - cseg_2B81B in every patch order (MC guard 1); a patch
    after fpad's (bplace.force asserts an unpatched site) stops the build there"""
    for _ in range(4):
        if t == end or bytes(p.get(t[0], t[1], 1)) not in (b'\xe8', b'\xe9'):
            return t
        t = p.call_target(*t)
    return t


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
    for k in ('GP_PAPI', 'GP_PSTEP', 'GP_PDONE', 'GP_PLEG', 'GP_PSEAS', 'GP_WK', 'GP_MGR', 'SEASONPLAYING', 'CAL',
              'GP_ST', 'GP_IN', 'GP_SEAS', 'GP_K', 'GP_SCT', 'GP_PMID', 'D1R', 'A1R', 'A2R', 'CAL_CUR', 'GP_CFLAGS'):
        assert k in gsyms, ('fpad: gplay without', k)
    import pgroups
    assert 'PG_TAB' in pgroups.LABELS, 'fpad: no pg_fix (pgroups) in this build: pg_season - the new-season arm - never runs'
    assert 'FP_PORT' in ssyms and 'FP_ST' in ssyms and 'FP_SAVE' in ssyms, 'fpad: swe.c without FPORT_ON (swe.py)'
    assert p.le.obj(4).npages * 0x1000 >= swreg.FPORT_END, 'fpad: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.FPORT_AT, swreg.FPORT_END - swreg.FPORT_AT)), 'fpad: obj4+FPORT_AT not free'
    assert p.le.obj(4).npages * 0x1000 >= swreg.FPORT2_END, 'fpad: obj4 pages for FPORT2 (patch.py)'
    assert not any(p.get(4, swreg.FPORT2_AT, swreg.FPORT2_END - swreg.FPORT2_AT)), 'fpad: obj4+FPORT2_AT not free'
    band = swe.OBJ4_PAGES * 0x1000
    obj_tab = p.le.hdr + struct.unpack_from('<I', p.out, p.le.hdr + 0x40)[0]
    vsize = struct.unpack_from('<I', p.out, obj_tab + 3 * 24)[0]   # (obj4's vsize as swe.py set it: p.set_vsize)
    assert _hdr_define('SR_PORT_MAX') == 48, ('fpad: SR_PORT_MAX (SAVE_SIZE)', _hdr_define('SR_PORT_MAX'))
    for k, n in (('FP_PORT', PORT_SIZE), ('FP_ST', ST_SIZE), ('FP_SAVE', SAVE_SIZE)):   # (swe.c's .bss: past every obj4 band, inside the vsize)
        o, a = ssyms[k]
        assert o == 4 and a >= band and a + n <= vsize, ('fpad: swe.c .bss', k, hex(a), hex(band), hex(vsize))
    fmap, rows, bad = window_table()
    assert rows, ('fpad: no slot-4 windows for world', world())
    import careerworld
    so, soff = careerworld.SITES['slt']                 # (the career's world byte, as swe.c's SWE_CWB)
    for cc, why in bad:
        print(f'exe: fpad: {cc}: windows unresolved ({why}) - no window: the engine refuses nothing there')
    fdiv, fset = pack_windows(rows)
    ext = {'GP_PAPI': gsyms['GP_PAPI'], 'GP_WK': gsyms['GP_WK'], 'GP_MGR': gsyms['GP_MGR'],
           'FP_SEASON': gsyms['SEASONPLAYING'], 'FP_CAL': gsyms['CAL'], 'FP_PORT': ssyms['FP_PORT'], 'FP_ST': ssyms['FP_ST'],
           'FP_SAVE': ssyms['FP_SAVE'],
           'FP_CWB': (so, soff + careerworld.WORLD_BYTE), 'GP_GST': gsyms['GP_ST'], 'GP_GIN': gsyms['GP_IN'],
           'FP_D1R': gsyms['D1R'], 'FP_A1R': gsyms['A1R'], 'FP_A2R': gsyms['A2R'],
           'FP_CALCUR': gsyms['CAL_CUR'], **{k: gsyms[k] for k in ('GP_SEAS', 'GP_K', 'GP_SCT', 'GP_PMID')}}
    ets, et0 = fp_et_sites(p)
    d1w = gsyms['D1R']
    ext.update(FP_D1W=d1w, FP_D2W=(d1w[0], d1w[1] + 4), FP_D3W=(d1w[0], d1w[1] + 8), FP_D4W=(d1w[0], d1w[1] + 12),
               FP_ETX=p.call_target(1, ets[0]), FP_STKLOWP=(2, 0xC3178), FP_CDIV=(2, __import__('gplay')._cardiv(p)))   # (FPORT_TEST: the game's _STACKLOW pointer)
    for o in ets:                                       # (MC guard 1: each site, through its chain, ends at cseg_2B81B)
        assert p.call_target(1, o) == ext['FP_ETX'] and et_chain_end(p, p.call_target(1, o), (1, et0)) == (1, et0), \
            ('fpad: an extra-time call does not reach cseg_2B81B', hex(o), p.call_target(1, o), hex(et0))
    offs = gp_offsets(gsyms['GP_CFLAGS'])
    # (-Oz, MC 15/11 room: fpad.c + fpsave.c only - cobj's -Os for every other unit; the port runs once per calendar
    #  step, size over speed: FPORT ~1.7 KB, FPORT2 ~0.35 KB smaller than at -Os, engine 52301fb)
    flags = ['-Oz'] + [f'-D{k}={v}' for k, v in offs.items()] + [f'-DFP_ST_SZ={ST_SIZE}', f'-DFP_SAVE_SZ={SAVE_SIZE}', f'-DFP_SAVE_HDR={SAVE_HDR}', f'-DFP_HASH={fp_hash():#x}u', f'-DFP_WORLD={world()}', f'-DFP_NDIV_={max(1, len(fdiv) // 4)}', f'-DFP_NSET_={max(1, len(fset))}']
    roots = ['fp_step', 'fp_leg', 'fp_et', 'fp_done', 'fp_new', 'fp_load', 'fp_season', 'FP_FMAP', 'FP_DIV', 'FP_SET', 'FP_NDIV', 'FP_NAMES']   # (FP_NAMES: lane 2's fpmlv.patch binds it)
    import collections
    import swefile

    class _Dry(swefile._Rec):           # (the dry links' target: also a dword across a page boundary - cobj.add_ptr's
        recs = collections.defaultdict(list)    # two records - 0x1D400's FPORT2 has one, swefile._Rec has no pages)

        def _page(self, *a):
            return 0, 0

        def _record(self, *a):
            return None
    # P5 (MC 15/11): fpsave.c first, its own unit at FPORT2 (no fpad.c symbol in it); the same flags (no test code in it)
    ext2 = {k: ext[k] for k in ('FP_PORT', 'FP_ST', 'FP_SAVE', 'FP_SEASON', 'FP_CWB', 'GP_GST', 'GP_SEAS', 'GP_PMID', 'GP_WK', 'GP_MGR')}
    obj2 = cobj.compile_c(SRC2, tuple(flags), sections=True)
    _, end2, _ = cobj.link(_Dry(), obj2, swreg.FPORT2_AT, (4, 0), externs=ext2, limit=swreg.FPORT2_END,
                           text_obj=4, roots=['fp_save', 'fps_load', 'fps_reset'])     # (dry: the release shape's end)
    left2 = swreg.FPORT2_END - end2
    assert left2 >= SLACK, ('fpad: the FPORT2 band has under 256 B left (release shape) - stop and report to MC', left2)
    syms2, e2, bss2 = cobj.link(p, obj2, swreg.FPORT2_AT, (4, 0), externs=ext2, limit=swreg.FPORT2_END, text_obj=4,
                                roots=['fp_save', 'fps_load', 'fps_reset'])
    assert not bss2 and e2 == end2, ('fpsave.c: no .bss, the dry link\'s end', bss2, hex(e2), hex(end2))
    ext['fps_load'], ext['fps_reset'] = syms2['fps_load'], syms2['fps_reset']
    rel_flags = tuple(flags)
    rel = cobj.compile_c(SRC, rel_flags, sections=True)   # (MC's floor on the release shape - no test code -, as
    _, rel_end, _ = cobj.link(_Dry(), rel, swreg.FPORT_AT, (4, 0), externs=ext, limit=swreg.FPORT_END,
                              text_obj=4, roots=roots)        # swefile's MARGIN: a dry link, its size only)
    left = swreg.FPORT_END - rel_end
    assert left >= SLACK, ('fpad: the FPORT band has under 256 B left (release shape) - stop and report to MC', left)
    if os.environ.get('FPORT_ETFORCE'):              # (test builds, with BPLACE_FORCE: an e.t. decided 1-0 at home)
        flags.append('-DFP_ETFORCE')
    test = test_entries()
    if test:
        flags += ['-DFPORT_TEST', f'-DFP_NTEST_={len(test)}']
        roots += ['FP_TEST', 'FP_NTEST']
    obj = rel if flags == list(rel_flags) else cobj.compile_c(SRC, tuple(flags), sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.FPORT_AT, (4, 0), externs=ext, limit=swreg.FPORT_END, text_obj=4,
                               roots=roots)             # (a test build's own code: within the band only)
    assert not bss, ('fpad.c: no .bss (it would land on swe.c\'s)', bss)
    assert flags != list(rel_flags) or end == rel_end
    p.put(*syms['FP_FMAP'], fmap)
    p.put(*syms['FP_DIV'], fdiv)
    p.put(*syms['FP_SET'], fset)
    p.put(*syms['FP_NDIV'], struct.pack('<H', len(fdiv) // 4))
    if test:
        p.put(*syms['FP_TEST'], b''.join(bytes(e) for e in test))
        p.put(*syms['FP_NTEST'], struct.pack('<H', len(test)))
    for hook, f in (('GP_PSTEP', 'fp_step'), ('GP_PDONE', 'fp_done'), ('GP_PLEG', 'fp_leg'), ('GP_PSEAS', 'fp_season')):
        cobj.add_ptr(p, gsyms[hook][1], *syms[f], gsyms[hook][0])   # (GP_PSEAS: pg_season's end, pg_fix - MC 14/11)
    for o in ets:                                       # (cseg_2AE97's extra time -> fp_et, chained)
        p.branch(1, o, 0xE8, *syms['fp_et'])
    engine.CALL_AT['fp_new'] = syms['fp_new']
    engine.CALL_AT['fp_load'] = syms['fp_load']
    engine.CALL_AT['fp_save'] = syms2['fp_save']       # P5: engine.before_save (fpsave.c), the FP item at swe.c's FP_SAVE
    engine.ITEM_AT['FP'] = ssyms['FP_SAVE']
    LABELS.update(syms)
    LABELS['FP_PORT'], LABELS['FP_ST'] = ssyms['FP_PORT'], ssyms['FP_ST']
    print(f'exe: fixture port (fpad.c) obj4+{swreg.FPORT_AT:#x}..{rel_end:#x} of {swreg.FPORT_END:#x} ({left} B left, '
          f'release shape' + (f'; this test build to {end:#x}, {swreg.FPORT_END - end} B left' if end != rel_end else '') + '), '
          f'{len(rows)} slot-4 windows ({len(fdiv) // 4} divisions, {len(fset)} B of sets), {256 - fmap.count(255)} league files'
          + (f', FPORT_TEST {len(test)} fixtures' if test else '')
          + f'; FP save (fpsave.c) obj4+{swreg.FPORT2_AT:#x}..{end2:#x} of {swreg.FPORT2_END:#x} ({left2} B left)')
    if os.environ.get('FPAD_BANDS'):                    # (the bands' report on stderr: a build's stdout is captured)
        print(f'FPAD_BANDS FPORT end {rel_end:#x} ({left} B left){"" if end == rel_end else f", test build {end:#x}"}; '
              f'FPORT2 end {end2:#x} ({left2} B left); obj4 pages {swe.OBJ4_PAGES}', file=__import__('sys').stderr)
    return end
