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
in CAREER); W-modes M2 adds M_FRIENDLY for the career worlds (the friendly / DIY pickers, swe.c), and world 0's menu
id WMENU + 0 (mkseason: the 1996-97 game's entry in their STORICO box). Presets wait for 4.1."""
import struct

REG_AT = 0x1800                         # obj4: swe.c's code + data below it, the manifest up to the object end
OBJ4_END = 0x2000                       # (the registry's end; swe.OBJ4_PAGES pages: 4.1 has a 3rd)
UESUM_AT = 0x2000                       # 4.1 S2a: uesum.c's page in obj4 (stays here in 4.2: usmenu took 0x3000)
USMENU_AT = 0x3000                      # 4.1 RC2: usmenu's page, the 4th (RIEPILOGO's phase menu; Regia / MC 09/11)
UPRIZE2_AT = 0x4000                     # 4.1 RC3: uprize's part 2 (value pillar, ANDAMENTO CLUB switch), the 5th page,
                                        # uprize's alone (MC 09/11; stays here in 4.2)
UPRIZE2_END = 0x4600                    # 4.2 (MC 10/11, the 4.1 merge): uprize part 2's link limit (0x42c8 used in 4.1),
                                        # under N7's SREG_DIV_AT (sreg.py asserts it)
ST_AT, ST_SIZE = 0x5000, 144             # 4.2: the engine's ledger item 'ST' (sr_stled.c: a groups stage's state;
                                        # sr_st_size(32, 8, 2) = 16 + 32 + 96), a zero block in obj4's 6th page,
                                        # under lrank.LR_AT (4.1's usmenu 0x3000 / uprize2 0x4000 / conti 0x4B00 below)
CONTI4_AT = 0x4B00                      # 4.1.1: conti's read-only data (the CONMEBOL ranking, the 4.1 season-1 lists +
CONTI4_END = 0x5000                     # winners) at the 5th page's top, above uprize part 2 (Regia / MC 10/11; 4.2 keeps
                                        # it: lrank from 0x6000)
SLOW_AT = 0xC000                        # 4.2 slow (MATCH SPEED, slow.py): obj4's 13th page, its own (MC 12/11; a
SLOW_END = 0xD000                       # CONVENTIONS 23bis exception: Davide's ok via Regia 12/11)
T3_AT = 0xD000                          # 4.2.y T3 "mini primavera" (t3.py / t3.c): obj4's 14th page, its own (MC 12/11;
T3_END = 0xE000                         # CONVENTIONS 23bis); 0xC000 = 42-slow's, 0xE000 = the conti CT spare
assert UPRIZE2_END <= CONTI4_AT, 'uprize part 2 would cross conti / ST'   # (4.2: bands never cross)
assert CONTI4_END <= ST_AT, 'conti data would cross ST'
NAMEFIT_AT = 0xC400                     # 4.2 names-fit (namefit.py, Marco (b) step 2: menu names by pixels; MC 12/11): page 13
NAMEFIT_END = 0xC800                    # between slow (its link limit NAMEFIT_AT) and trial; code + 16 x 24 B row buffers
TRIAL_AT = 0xC800                       # 4.2.x trial players T1+T2 (trial.py's code, out of obj3: MC 12/11, REL42i13 IT obj3
TRIAL_END = 0xCF00                      # 112 B): page 13 between slow (SLOW_AT, link limit TRIAL_AT) and the shirtbox (BOX_AT)
BOX_AT = 0xCF00                         # 4.2 shirtbox (Marco's lit number box, shirtedit se_unsh): obj4's 13th page top,
BOX_END = 0xD000                        # slow's page (SLOW_AT 0xC000, its code below BOX_AT); Mercato CPU's T3 from 0xD000 (MC 12/11)
assert SLOW_AT < NAMEFIT_AT < NAMEFIT_END <= TRIAL_AT < TRIAL_END <= BOX_AT < BOX_END <= SLOW_END, \
    'page 13: slow < namefit < trial < shirtbox'
assert SLOW_END <= T3_AT < T3_END, 'page 14: T3 above page 13'
DIFF_AT = 0xF000                        # 42-diff (difficulty + DRIBBLING beta): obj4's 16th page, PROVISIONAL until MC
DIFF_END = 0x10000                      # names the room (difficulty-plan.md §3)
assert T3_END <= DIFF_AT
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
    out = [(0, F_BASE | (F_NS if ns else 0), mkseason.WMENU if mkseason.W0_IDS else 0, 1996, M_FRIENDLY | M_PRESET | M_SEASON | M_CAREER, 'team', [], [])]
    for n, pks in sorted(mkseason.worlds().items()):
        root = [pk for pk in pks if 'world_cups' in pk.meta][0].meta['world_cups']
        files = [pk.files[pk.league['clubs']][0] for pk in pks]
        comps = [(pk.files[pk.league['clubs']][0], int(c['id'], 16)) for pk in pks for c in pk.comps if 'id' in c]
        flags = F_NS if ns else 0
        stem = mkseason.ns_stem(n)
        if stem != 'team':
            flags |= F_XTRA
        out.append((n, flags, mkseason.WMENU + n, root['start_year'], M_CAREER | M_FRIENDLY, stem, files, comps))
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
    assert end <= OBJ4_END, f'world registry: {end - REG_AT:#x} B past obj4'
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
