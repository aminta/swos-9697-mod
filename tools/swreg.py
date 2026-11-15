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
SWEFILE_AT = 0x11000                    # 4.2 the engine's file layer (swefile.c, MC 12/11): obj4 page 18, after Difficolta's
SWEFILE_END = 0x11800                   # page 15 (0xE000..0xF000) and Panchina's kits (0xF000..0x11000); dormant until a consumer
S7SWAP_AT = 0x11800                     # 4.2 S7 season-end swap builder (s7swap.c, Shaved; MC 13/11) + the registry library's
S7SWAP_END = 0x15000                    # one copy (sr_reg_season, sr_wmap_*: the import in SREG2 calls it here), pages 18-20 (MC 13/11: 0x14000, WSITES with the code);
# (MC 13/11: 0x15000, CF_ST + s7_home_word; obj4 0x14000..0x15000 was free; the next free obj4 room starts at 0x15000)
                                        # linked only with a registry shape (sreg.shape(), = GP_S7)
assert SWEFILE_END <= S7SWAP_AT < S7SWAP_END, 'swreg: SWEFILE_END <= S7SWAP_AT < S7SWAP_END'
OBJ1MV_AT = 0x15000                     # 4.2 obj1 relief (MC 13/11, Shaved's census): whole modules moved out of obj1's full
OBJ1MV_END = 0x16800                    # regions (237 pages frozen): winners.py (the extra pages), then instcheck + shirtedit
                                        # (the career cave); linked with the SEASON WINNERS page (worlds + gplay + extra pages)
OBJ1MV_CC = 0x15C00                     # (step 2: the career cave's shirtedit + instcheck from here; winners below it)
assert OBJ1MV_AT < OBJ1MV_CC < OBJ1MV_END, 'swreg: OBJ1MV_CC inside the band'
FPORT_AT = 0x17000                      # 4.2 the fixture port's adapter (P2, Motore; MC 14/11): sr_port.o + port_step + the
FPORT_END = 0x19000                     # slot-4 window table generated from fport.py, embedded; 2 pages, >= 256 B left at link
                                        # (0x16800..0x17000: Difficolta's SETPIECE, 42-sp, not merged yet)
S7GEO_AT = 0x19000                      # 4.2 Serie D geography (MC 14/11 room ruling, 42-geo-d): the geography chain's own TU (s7geo.c:
S7GEO_END = 0x1A000                     # code + neighbour table + log + the per-club coordinates), after FPORT; linked only with
                                        # GP_S7; >= 256 B left
CDKN_AT = 0x1A800                       # 4.2 S2 knockouts (cdkn.c: the Coppa D's rounds 0-1 by the engine's sr_kn; MC 14/11, 42-cdkn):
CDKN_END = 0x1C800                      # code + const after DIFF2 (0x1A000..0x1A800, 42-drp, not merged yet), >= 256 B left at link;
                                        # its work area in swe.c's .bss (CDKN_WORK), linked only in CD_KN builds
PRACTICE_AT = 0x1C800                   # 4.2 set-piece practice (Shaved, 42-practice; MC 14/11): the last 4.2 band; unlinked until 42-practice
PRACTICE_END = 0x1D400                  # is merged; 3 KB (MC 15/11, option B: +0x400 for Davide's practice fixes; the 4.3
                                        # reservations below +0x400; the release's obj4 ends inside page 0x1D)
FPORT2_AT = 0x1D400                     # 4.2 P5 (MC 15/11): the fixture port's save - fpsave.c (sr_port_save / sr_port_load + the
FPORT2_END = 0x1E400                    # FP item glue), its own link unit; FPORT_ON builds only (test-only), >= 256 B left (release shape);
                                        # right after Shaved's PRACTICE (0x1C800..0x1D400)
S3C_AT = 0x1E400                        # 4.2 S3 step 2 (MC 15/11): cuprule.c, the Serie C play-off's cup place (C.U. 209/A) - ONE implementation, a
S3C_END = 0x1E800                       # state-free leaf TU called by gplay.c and dplay.c; S3 builds only; >= 256 B left (584 B used). After FPORT2 /
                                        # PRACTICE's growth (0x1D000..0x1E400, the Integratore's merges); the 4.3 chain starts at 0x1E800 (MC 15/11)
MKTHOOK_AT = 0x1E800                    # 4.3 reservations only (MC 14/11: sizes 6 KB + 4 KB + 4 KB, final addresses at 4.3 start, after
MKTHOOK_END = 0x20000                   # the last 4.2 band): the CPU market's exe hooks (mkthook.c), then MKTLOAD (the .MKT load half),
MKTLOAD_AT = 0x20000                    # then MKTAGE (Mercato CPU); unlinked in 4.2 (the unlinked bands go last, so a release never
MKTLOAD_END = 0x21000                   # carries an empty page for them). DIFF2 0x1A000..0x1A400 + SPX 0x1A400..0x1A800 stay free
MKTAGE_AT = 0x21000                     # here for 42-drp / 42-sp (their swreg lines are taken verbatim)
MKTAGE_END = 0x22000
R17_AT = 0x22000                        # 4.2 row-17 hint (r17.py, Panchina; MC 15/11): a RELEASE band, 1 KB, floor >= 256 B; this address is
R17_END = 0x22400                       # TEMPORARY (right after the MKT size reservations): the rc-freeze packing moves it in among the release bands
assert MKTAGE_END <= R17_AT < R17_END, 'swreg: R17 above the MKT reservations'
assert S7SWAP_END <= OBJ1MV_AT < OBJ1MV_END <= FPORT_AT < FPORT_END <= S7GEO_AT < S7GEO_END <= CDKN_AT < CDKN_END <= PRACTICE_AT < \
    PRACTICE_END <= FPORT2_AT < FPORT2_END <= S3C_AT < S3C_END <= MKTHOOK_AT < MKTHOOK_END <= MKTLOAD_AT < MKTLOAD_END <= MKTAGE_AT < MKTAGE_END <= 0x22000, \
    'swreg: S7SWAP_END <= OBJ1MV_AT < OBJ1MV_END <= FPORT_AT < FPORT_END <= S7GEO_AT < S7GEO_END <= CDKN_AT < CDKN_END <= PRACTICE_AT < PRACTICE_END <= FPORT2_AT < FPORT2_END <= S3C_AT < S3C_END <= MKTHOOK_AT < MKTHOOK_END <= MKTLOAD_AT < MKTLOAD_END <= MKTAGE_AT < MKTAGE_END'
S7_ORIG_SZ = 0x2C000                    # 4.2 S7: s7swap.c's ORIG buffers in swe.c's .bss (shaped builds only; MC 13/11):
                                        # the two league files as read (Italy: 102 = 100 records, 144 = 162: 179212 B;
                                        # s7swap.py asserts they fit)
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
SREG_AT = 0x5100                        # 4.2 N7: the club registry's code + data (sreg.py, sreg.c), after ST, under
                                        # lrank.LR_AT (MC 10/11: the band 0x5100..0x6000); linked only with a shape
SREG_DIV_AT = 0x4600                    # 4.2 N7: sreg.c's SREG_DIV (SR_REG_CLUBS bytes, 0x4600..0x4A00), above 4.1's
                                        # uprize2 (0x4000..0x42c8), under conti (CONTI4_AT 0x4B00; MC 10/11)
SREG2_AT = 0xB000                       # 4.2 N7 piece 4: obj4's 12th page (0xB000..0xC000; MC 12/11: the 11th,
SREG2_END = 0xC000                      # 0xA000..0xB000, is lrank's LR_TAB alone since MC's 11/11 option b), the
                                        # old-save import (old_ord, the walker, its sites); only with a shape (sreg.py
                                        # obj4_pages / sreg2_check). 0xC000: Shaved's 42-slow; the CT spare: 0xD000
KITS_AT = 0xF000                        # 4.2 kits (kits.py, Panchina; MC 12/11): K2 keepers + R1 referee code and the
KITS_END = 0x11000                      # sprite masks on obj4's 16th page (end asserted <= 0x10000), the KEEPKIT table
                                        # (128 x 24 B, zero-filled) on the 17th
KITS_PAGE16_END = 0x10000               # (code + masks; the 17th: KEEPKIT.DAT's 'KKST' block, table and kk_* code, MC 13/11)
assert T3_END <= globals().get('DIFF_END', KITS_AT) <= KITS_AT < KITS_PAGE16_END < KITS_END, 'kits: above T3 and the difficulty band'
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
