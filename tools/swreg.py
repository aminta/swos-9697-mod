"""The world registry (engine step W, PLAN §19 option B): a compiled manifest of the build's worlds in obj4, read by the
engine's mode-independent loader (swe.c reg_*) and, from W-modes on, by the team pickers and the preset list.

A world is the 1996-97 game itself (world 0) or a career world of the build (mkseason.worlds(): 4 = Europe 1984-85,
5 = World 2026-27 in the release recipe). Its teams are the team files of its country namespace (careerworld w_ns_set:
the rows of the 3 country tables, data/<stem>.nnn); its competitions are its packs' contests by (file, contest id).
Nothing is copied that the exe already holds: the names come from countriesTable[menu id] (mkseason's world entry)
at run time, the rows from careerworld's NSWT.

    obj4+REG_AT  'SWRG', u16 version, u8 worlds, u8 the base namespace (careerworld NSBASE; 0 = one namespace)
            +8   u32 -> WCUR (obj1; 0 = one namespace)       +12  u32 -> competitionsTable[254] (obj2)
            +16  u32 -> the CLASSIC CAREERS world table (obj1; 0 = none)   +20  u32 -> the namespace numbers
                 (careerworld NSLIST, obj1; 0 = none)   +24  u32 their count (a row = 10 B each: ct, comp, tcn)
            +28  u32 -> the default world byte (v2, W-modes: setupDatBuffer + 105, obj2, mainbtn's switch: 0 World
                 2026-27, 1 the 1996-97 game, 2 Europe 1984-85; 0 = no switch in the build)
            +32  per world REC bytes: u8 n, u8 flags (F_*), u8 its menu id (mkseason WMENU + n; 0 = world 0),
                 u8 countries, u16 first season, u8 modes (M_*), u8 competitions, 4 B team file stem,
                 u32 -> its namespace rows (obj1; 0 = the static tables), u32 -> u8 league files (countries),
                 u32 -> (u8 file, u8 contest id) per competition
            then the lists

modes = where a picker lists the world. Step W turns on only what exists today (world 0 everywhere, the career worlds
in CAREER); W-modes adds M_FRIENDLY / M_PRESET for World 2026-27 with its picker texts."""
import struct

REG_AT = 0x800                          # obj4: swe.c's code + data below it, the manifest up to the page end
MAGIC = b'SWRG'
VERSION = 2
HDR = 32
REC = 24
F_BASE, F_NS, F_XTRA = 1, 2, 4
M_FRIENDLY, M_PRESET, M_SEASON, M_CAREER = 1, 2, 4, 8        # M_FRIENDLY: friendly + the 3 DIY editors (GoGetTeamsForPlay)
INFO = {}                               # (the last build's manifest, for the harness / host tests)


def worlds():
    """[(n, flags, menu id, first season, modes, stem, [league files], [(file, contest id)])] of this build"""
    import careerworld
    import mkseason
    ns = careerworld.NS.get('info')
    out = [(0, F_BASE | (F_NS if ns else 0), 0, 1996, M_FRIENDLY | M_PRESET | M_SEASON | M_CAREER, 'team', [], [])]
    for n, pks in sorted(mkseason.worlds().items()):
        root = [pk for pk in pks if 'world_cups' in pk.meta][0].meta['world_cups']
        files = [pk.files[pk.league['clubs']][0] for pk in pks]
        comps = [(pk.files[pk.league['clubs']][0], int(c['id'], 16)) for pk in pks for c in pk.comps if 'id' in c]
        flags = F_NS if ns else 0
        stem = mkseason.ns_stem(n)
        if stem != 'team':
            flags |= F_XTRA
        out.append((n, flags, mkseason.WMENU + n, root['start_year'], M_CAREER, stem, files, comps))
    return out


def patch(p, add_ptr):
    """the manifest at obj4+REG_AT; add_ptr(off, tobj, toff) = an obj4 fixup. Returns its end."""
    import careerworld
    ws = worlds()
    ns = careerworld.NS.get('info')
    lab = careerworld.LABELS
    at = REG_AT + HDR + REC * len(ws)
    lists = bytearray()
    recs = []
    for n, flags, menu, year, modes, stem, files, comps in ws:
        assert len(files) < 256 and len(comps) < 256 and all(f < 256 and c < 256 for f, c in comps)
        fl = at + len(lists)
        lists += bytes(files)
        cl = at + len(lists)
        lists += b''.join(bytes(x) for x in comps)
        lists += bytes(-len(lists) % 4)
        recs.append((n, flags, menu, len(files), year, modes, len(comps), stem.encode(), fl, cl))
    end = at + len(lists)
    assert end <= 0x1000, f'world registry: {end - REG_AT:#x} B past obj4\'s page'
    base = ns['base'] if ns else 0
    p.put(4, REG_AT, MAGIC + struct.pack('<HBB', VERSION, len(ws), base) + bytes(16)
          + struct.pack('<I', len(ns['numbers']) if ns else 0) + bytes(4))
    import mainbtn
    if mainbtn.SETTING[0]:
        add_ptr(REG_AT + 28, *mainbtn.SETTING[0])
    if ns:
        add_ptr(REG_AT + 8, 1, lab['WCUR'])
    import countries
    assert countries.COMP[0]
    add_ptr(REG_AT + 12, 2, countries.COMP[0] + 4 * 254)
    if ns:
        add_ptr(REG_AT + 16, 1, ns['cworld'])
        add_ptr(REG_AT + 20, 1, ns['list_at'])
    for k, (n, flags, menu, nf, year, modes, nc, stem, fl, cl) in enumerate(recs):
        r = REG_AT + HDR + REC * k
        p.put(4, r, struct.pack('<BBBBHBB4s', n, flags, menu, nf, year, modes, nc, stem) + bytes(12))
        if ns and n:
            add_ptr(r + 12, 1, ns['rows_at'][n])
        if nf:
            add_ptr(r + 16, 4, fl)
        if nc:
            add_ptr(r + 20, 4, cl)
    p.put(4, at, bytes(lists))
    INFO.clear()
    INFO.update(worlds=ws, end=end)
    print(f'exe: world registry obj4+{REG_AT:#x}..{end:#x}: worlds ' + ', '.join(
        f'{n} ({stem}, {len(files)} countries, {len(comps)} competitions)' for n, _, _, _, _, stem, files, comps in ws))
    return end
