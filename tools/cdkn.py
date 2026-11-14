"""4.2 S2 knockouts (MC 14/11, 42-cdkn): the Coppa Italia Serie D's rounds 0-1 by the engine's sr_kn (cdkn.c, its
docstring). obj4 band CDKN (swreg.CDKN_AT..CDKN_END, >= 256 B left), the work area in swe.c's .bss (CDKN_WORK,
WORK_SZ). Linked only with CD_KN=1 (a test switch; the release enable is a module constant + MC's ruling + Davide's ok,
with Panchina's per-club coordinates in place of CENTRES). gplay.c's GP_CDKN -> cdkn_make."""
import os
import struct

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cdkn.c')
WORK_SZ = 0x4400                        # (struct cdkn_ws: asserted against CDKN_WSZ at link)
# Interim geography (test switch only): the 2026-27 Serie D gironi A..I, each at its region's rough centre (lat, lon in
# 0.01 degree): A north-west (Piedmont / Liguria / west Lombardy), B Lombardy, C the north-east, D Emilia / north
# Tuscany, E Tuscany / Umbria, F the Adriatic centre (Marche / Abruzzo / Molise), G Lazio / Sardinia, H Apulia /
# Basilicata / Campania, I Sicily / Calabria.
CENTRES = [(4500, 830), (4560, 970), (4570, 1200), (4430, 1100), (4330, 1150), (4280, 1380), (4180, 1200),
           (4100, 1580), (3850, 1500)]
ROOTS = ['cdkn_make', 'CDKN_LL', 'CDKN_CTR', 'CDKN_NCTR', 'CDKN_LOG', 'CDKN_NLOG', 'CDKN_OK', 'CDKN_TFALL', 'CDKN_WSZ']
LABELS = {}


def on():
    if os.environ.get('CD_KN') != '1':
        return False
    import modver
    assert modver.is_test(), 'CD_KN is a test switch (modver.TEST_VARS)'
    return True


def page_end():
    import swreg
    return (swreg.CDKN_END + 0xFFF) & ~0xFFF


def patch(p, ssyms, gsyms):
    """links cdkn.c at obj4+CDKN_AT (ssyms swe.c's, gsyms gplay's); points gplay.c's GP_CDKN at cdkn_make."""
    if not on():
        return None
    import cobj
    import swreg
    assert 'CDKN_WORK' in ssyms, 'cdkn: swe.c without CDKN_WORK (swe.py CDKN_WORK_SZ)'
    assert 'GP_CDKN' in gsyms, 'cdkn: gplay.c without GP_CDKN'
    assert p.le.obj(4).npages * 0x1000 >= page_end(), 'cdkn: obj4 pages (patch.py)'
    assert not any(p.get(4, swreg.CDKN_AT, swreg.CDKN_END - swreg.CDKN_AT)), 'cdkn: obj4+CDKN_AT not free'
    import gplay
    assert gplay.CD_SIZE == 1032, ('cdkn: struct cd_state changed (cdkn.c CD_EFRESH / CD_GENON / CD_NP / CD_GEN)', gplay.CD_SIZE)
    cs = gsyms['csyms']
    flags, ext = (), {'CDKN_WORK': ssyms['CDKN_WORK'], 'GP_CDT': cs['GP_CDT'], 'GP_SEAS': cs['GP_SEAS'], 'CD_ST': cs['CD_ST']}
    tmgr = os.environ.get('CDKN_TMGR')                  # (test builds: the career club in the preliminary (1) / a bye (2))
    if tmgr:
        assert tmgr in ('1', '2'), tmgr
        flags, ext['GP_MGR'] = (f'-DCDKN_TMGR={tmgr}',), gsyms['GP_MGR']
    obj = cobj.compile_c(SRC, flags, sections=True)
    syms, end, bss = cobj.link(p, obj, swreg.CDKN_AT, (4, 0), externs=ext,
                               limit=swreg.CDKN_END - 256, text_obj=4, roots=ROOTS)
    assert not bss, ('cdkn.c: no .bss (its work area is swe.c\'s CDKN_WORK)', bss)
    wsz = struct.unpack('<I', bytes(p.get(*syms['CDKN_WSZ'], 4)))[0]
    assert wsz <= WORK_SZ, ('cdkn: struct cdkn_ws past CDKN_WORK', wsz, WORK_SZ)
    w0 = ssyms['CDKN_WORK'][1]                          # (MC 14/11: the .bss range overlaps no band, inside obj4's vsize)
    vs = struct.unpack_from('<I', p.out, p.le.hdr + struct.unpack_from('<I', p.out, p.le.hdr + 0x40)[0] + 3 * 24)[0]   # (obj4's vsize as set_vsize left it)
    assert ssyms['CDKN_WORK'][0] == 4 and w0 + WORK_SZ <= vs, ('cdkn: CDKN_WORK outside obj4', hex(w0), hex(vs))
    assert w0 >= p.le.obj(4).npages * 0x1000, ('cdkn: CDKN_WORK under obj4\'s file pages (a band)', hex(w0))
    p.put(*syms['CDKN_CTR'], b''.join(struct.pack('<hh', *c) for c in CENTRES))
    p.put(*syms['CDKN_NCTR'], bytes((len(CENTRES),)))
    import s7swap
    ll = getattr(s7swap, 'LABELS', {}).get('s7geo_ll')  # (Panchina's per-club towns, S7 builds with 42-geo-pack: the one source)
    if ll:
        cobj.add_ptr(p, syms['CDKN_LL'][1], *ll[:2], syms['CDKN_LL'][0])
    if os.environ.get('CDKN_TFALL') == '1':             # (test builds: every draw refused - the fallback's forced case)
        p.put(*syms['CDKN_TFALL'], b'\x01')
    cobj.add_ptr(p, gsyms['GP_CDKN'][1], *syms['cdkn_make'][:2], gsyms['GP_CDKN'][0])
    LABELS.clear()
    LABELS.update(syms)
    print(f'exe: cdkn (S2 knockouts, Coppa D rounds 0-1 by sr_kn): obj4+{swreg.CDKN_AT:#x}..{end:#x} '
          f'({end - swreg.CDKN_AT} B, {swreg.CDKN_END - end} B left), work CDKN_WORK obj4+{w0:#x} ({wsz} of {WORK_SZ} B), '
          f'GP_CDKN -> cdkn_make obj4+{syms["cdkn_make"][1]:#x}, towns {"s7geo_ll" if ll else "girone centres"}')
    return end
