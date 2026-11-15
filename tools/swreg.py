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
SWEFILE_AT = 0xB000                    # 4.2 the engine's file layer (swefile.c, MC 12/11): obj4 page 18, after Difficolta's
SWEFILE_END = 0xB500                   # page 15 (0xE000..0xF000) and Panchina's kits (0xF000..0x11000); dormant until a consumer
S7SWAP_AT = 0x11100                     # 4.2 S7 season-end swap builder (s7swap.c, Shaved; MC 13/11) + the registry library's
S7SWAP_END = 0x14E00                    # one copy (sr_reg_season, sr_wmap_*: the import in SREG2 calls it here), pages 18-20 (MC 13/11: 0x14000, WSITES with the code);
# (MC 13/11: 0x15000, CF_ST + s7_home_word; obj4 0x14000..0x15000 was free; the next free obj4 room starts at 0x15000)
                                        # linked only with a registry shape (sreg.shape(), = GP_S7)
assert SWEFILE_END <= S7SWAP_AT < S7SWAP_END, 'swreg: SWEFILE_END <= S7SWAP_AT < S7SWAP_END'
OBJ1MV_AT = 0x14E00                     # 4.2 obj1 relief (MC 13/11, Shaved's census): whole modules moved out of obj1's full
OBJ1MV_END = 0x16500                    # regions (237 pages frozen): winners.py (the extra pages), then instcheck + shirtedit
                                        # (the career cave); linked with the SEASON WINNERS page (worlds + gplay + extra pages)
OBJ1MV_CC = 0x15A00                     # (step 2: the career cave's shirtedit + instcheck from here; winners below it)
assert OBJ1MV_AT < OBJ1MV_CC < OBJ1MV_END, 'swreg: OBJ1MV_CC inside the band'
SETPIECE_AT = 0xB500                   # 4.2 set pieces 1+2 (setpieces.py, MC 14/11): the unused half of page 0x16 (no new
SETPIECE_END = 0xC000                  # page), linked in every build; >= SETPIECE_MIN B left (build check). MC 14/11:
                                        # +0x400 in place for set pieces §3-§5 (0x16C00 -> 0x17000), same SPB base
SETPIECE_MIN = 256                      # (MC 15/11: the release floor, as every band)
FPORT_AT = 0x35000                      # 4.2 the fixture port's adapter (P2, Motore; MC 14/11): sr_port.o + port_step + the
FPORT_END = 0x37000                     # slot-4 window table generated from fport.py, embedded; 2 pages, >= 256 B left at link
                                        # (0x16800..0x17000: Difficolta's SETPIECE, 42-sp, not merged yet)
S7GEO_AT = 0x16500                      # 4.2 Serie D geography (MC 14/11 room ruling, 42-geo-d): the geography chain's own TU (s7geo.c:
S7GEO_END = 0x17700                     # code + neighbour table + log + the per-club coordinates), after FPORT; linked only with
                                        # GP_S7; >= 256 B left
CDKN_AT = 0x37000                       # 4.2 S2 knockouts (cdkn.c: the Coppa D's rounds 0-1 by the engine's sr_kn; MC 14/11, 42-cdkn):
CDKN_END = 0x39000                      # code + const after DIFF2 (0x1A000..0x1A800, 42-drp, not merged yet), >= 256 B left at link;
                                        # its work area in swe.c's .bss (CDKN_WORK), linked only in CD_KN builds
PRACTICE_AT = 0x18A80                   # 4.2 set-piece practice (Shaved, 42-practice; MC 14/11): the last 4.2 band; unlinked until 42-practice
PRACTICE_END = 0x19400                  # is merged; 3 KB (MC 15/11, option B: +0x400 for Davide's practice fixes; the 4.3
                                        # reservations below +0x400; the release's obj4 ends inside page 0x1D)
FPORT2_AT = 0x39000                     # 4.2 P5 (MC 15/11): the fixture port's save - fpsave.c (sr_port_save / sr_port_load + the
FPORT2_END = 0x3A000                    # FP item glue), its own link unit; FPORT_ON builds only (test-only), >= 256 B left (release shape);
                                        # right after Shaved's PRACTICE (0x1C800..0x1D400)
S3C_AT = 0x19400                        # 4.2 S3 step 2 (MC 15/11): cuprule.c, the Serie C play-off's cup place (C.U. 209/A) - ONE implementation, a
S3C_END = 0x19800                       # state-free leaf TU called by gplay.c and dplay.c; S3 builds only; >= 256 B left (584 B used). After FPORT2 /
                                        # PRACTICE's growth (0x1D000..0x1E400, the Integratore's merges); the 4.3 chain starts at 0x1E800 (MC 15/11)
MKTHOOK_AT = 0x1D500                    # 4.3 reservations only (MC 14/11: sizes 6 KB + 4 KB + 4 KB, final addresses at 4.3 start, after
MKTHOOK_END = 0x1ED00                   # the last 4.2 band): the CPU market's exe hooks (mkthook.c), then MKTLOAD (the .MKT load half),
MKTLOAD_AT = 0x1ED00                    # then MKTAGE (Mercato CPU); unlinked in 4.2 (the unlinked bands go last, so a release never
MKTLOAD_END = 0x1FD00                   # carries an empty page for them). DIFF2 0x1A000..0x1A400 + SPX 0x1A400..0x1A800 stay free
MKTAGE_AT = 0x1FD00                     # here for 42-drp / 42-sp (their swreg lines are taken verbatim)
MKTAGE_END = 0x21D00                    # (MC 15/11: 0x20500 -> 0x21500, Mercato measured 0x205FB + floor + h3_team + sweep; +0x800 after TKUI)
GPLX_AT = 0x19B00                       # 4.2 GPLX "gplay overflow" (MC 15/11, obj1-room.md): gplx.c (gplay.c code out of the full
GPLX_END = 0x19E00                      # gplay pages: the supercups' sc_rule); a RELEASE band, >= 256 B left; temporary address after
                                        # the MKT reservations and R17 (0x22000..0x22400, Panchina), packed at the rc freeze
SESTRIP_AT = 0x19E00                    # 4.2 row 32 B1 (MC 15/11): shirtedit's number strip (se_supd / se_sshow / se_soff + buffer +
SESTRIP_END = 0x1A100                   # verb), out of OBJ1MV (A+B left 32 B there); temporary after Motore's GPLX, packed among
                                        # the release bands at the rc freeze; >= 256 B left (asserted in shirtedit.patch)
R17_AT = 0x19800                        # 4.2 row-17 hint (r17.py, Panchina; MC 15/11): a RELEASE band, 1 KB, floor >= 256 B; this address is
R17_END = 0x19B00                       # TEMPORARY (right after the MKT size reservations): the rc-freeze packing moves it in among the release bands
DIFF2_AT = 0x17700                      # 4.2 the difficulty family's overflow band (MC 14/11, after S7GEO 0x19000..0x1A000):
DIFF2_END = 0x17F00                     # W1's cover role (w1_cov) now, set pieces §4-§5 if SETPIECE runs short; linked
DIFF2_MIN = 128                         # whenever the OPTIONS rows are; >= DIFF2_MIN B left at link (asserted)
DIFF2_SPLIT = 0x17B00                   # MC 14/11 split: DIFF2_AT..DIFF2_SPLIT = difficulty's code (link limit DIFF2_SPLIT - 128),
SPX_AT = DIFF2_SPLIT                    # SPX_AT..SPX_END = setpieces' overflow (its own unit, PC-relative from SPB: ARCADE fouls,
SPX_END = DIFF2_END                     # the §3 sideways steer, §4 takers); each side >= 128 B left on the release shape
assert DIFF2_AT < DIFF2_SPLIT == SPX_AT < SPX_END == DIFF2_END, 'swreg: DIFF2 | SPX split (MC 14/11; one block since the 4.2 freeze)'
S7_ORIG_SZ = 0x2C000                    # 4.2 S7: s7swap.c's ORIG buffers in swe.c's .bss (shaped builds only; MC 13/11):
                                        # the two league files as read (Italy: 102 = 100 records, 144 = 162: 179212 B;
                                        # s7swap.py asserts they fit)
SREG2_AT = 0x1A100                      # 4.2 N7 piece 4 / 42-s7import (MC 15/11): the old-save import (sreg.py patch_import:
SREG2_END = 0x1C100                     # sreg2.c + sreg_import.c at -Oz, ~7.5 KB + 256 floor; was the one page 0xB000..0xC000,
                                        # too small); only in a shaped S7 build. A release map band (obj1-room.md), packed at
                                        # the rc freeze
TKUI_AT = 0x1C100                       # 4.2 takers UI (MC 15/11, Difficolta): the TIRATORI page, the in-match CHI TIRA, the practice
TKUI_END = 0x1D500                      # picker; a RELEASE band (0x1400: MC 15/11 +0x800, takers A1 playMatchMenu copy 1639 B + A2 TIRATORI
                                        # page ~2 KB) right after SREG2; its linker adds OBJ4_PAGES in ceiling form (-(-swreg.TKUI_END //
                                        # 0x1000) = 0x1E); the 4.3 MKT reservations follow it
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
DIFF_AT = 0xE000                        # 42-diff (difficulty + DRIBBLING, difficulty.py + buildup.py): obj4's whole
DIFF_END = 0xF000                       # page 15 (MC 12/11, option a; a future CT page goes to 0xF000+). Split:
BU_AT = 0xEC00                          # difficulty 0xE000..BU_AT, the build-up v1 BU_AT..DIFF_END. The build FAILs
BU_END = DIFF_END                       # when the release shape leaves under DIFF_MARGIN B of the page. (4.2 42-drp: 0xE900 -> 0xEC00, the PERSONALIZZATO page)
DIFF_MARGIN = 512
assert T3_END <= DIFF_AT < BU_AT < BU_END == DIFF_END <= 0x10000, 'page 15: T3 < difficulty < build-up'
SREG_AT = 0x5100                        # 4.2 N7: the club registry's code + data (sreg.py, sreg.c), after ST, under
                                        # lrank.LR_AT (MC 10/11: the band 0x5100..0x6000); linked only with a shape
SREG_DIV_AT = 0x4600                    # 4.2 N7: sreg.c's SREG_DIV (SR_REG_CLUBS bytes, 0x4600..0x4A00), above 4.1's
                                        # uprize2 (0x4000..0x42c8), under conti (CONTI4_AT 0x4B00; MC 10/11)
# (SREG2: below, after SESTRIP - 42-s7import moved it out of 0xB000..0xC000, MC 15/11)
KITS_AT = 0xF000                        # 4.2 kits (kits.py, Panchina; MC 12/11): K2 keepers + R1 referee code and the
KITS_END = 0x11100                      # sprite masks on obj4's 16th page (end asserted <= 0x10000), the KEEPKIT table
                                        # (128 x 24 B, zero-filled) on the 17th
KITS_PAGE16_END = 0x10000               # (code + masks; the 17th: KEEPKIT.DAT's 'KKST' block, table and kk_* code, MC 13/11)
assert T3_END <= globals().get('DIFF_END', KITS_AT) <= KITS_AT < KITS_PAGE16_END < KITS_END, 'kits: above T3 and the difficulty band'
DRIB1V1_AT = 0xC000                     # 42-drp (MC 14/11): the PERSONALIZZATO page's code + strings and W1, the 1-v-1
DRIB1V1_END = 0xC400                    # knob, in MATCH SPEED's parked room (page 13 under NAMEFIT_AT, its link limit);
assert DRIB1V1_AT == SLOW_AT and DRIB1V1_END == NAMEFIT_AT, 'the 42-drp band = slow\'s room (only with patch.SLOW off)'
assert (NAMEFIT_AT, TRIAL_AT, BOX_AT) == (0xC400, 0xC800, 0xCF00), 'page 13 bands unchanged (MC 14/11)'
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
# 4.2 rc freeze (MC 15/11, obj4pack pass 1 approved: Shaved 42-obj4pack2, internal/handoff/obj4pack-REL42op1/): the release
# bands packed in map order with no empty obj4 page - the 0xB000 page (SREG2's old one) filled first, then from KITS; the
# 4.3 reservations after the last release band; the test-only bands in the test region after SP_METER / DIFF_TC (0x35000).
# New release bands (official lines): DRP8D (42-drp8d clamp, 451 B), TAKERS (Difficolta's set-piece takers), GAMEPLAY
# (reserve: the GAMEPLAY page, gameplay-menu-design.md).
DRP8D_AT = 0x21D00                      # 0x300, a 4.3 reservation after MKTAGE, unlinked (MC 15/11: drp8d not in 4.2;
DRP8D_END = 0x22000                     # SETPIECE took its 0xBD00..0xC000, 160 B left on REL42i64; after MKTAGE's growth)
S6_AT = 0x22000                         # 4.3 S6 (MC 15/11, Motore 43-s6a): s6sea.c, world SEASONs' picker, its own unit out of
S6_END = 0x22200                        # swe.c (-Oz, 256 B floor; 161 B on the IT release recipe); after DRP8D
TAKERS_AT = 0x17F00                     # 0x500 (~1 KB + floor 256)
TAKERS_END = 0x18400
GAMEPLAY_AT = 0x18400                   # 0x680 reserve (MC 15/11: Panchina ~1.1 KB + floor 256; +0x80 15/11, taken from
GAMEPLAY_END = 0x18A80                  # PRACTICE's start: 480 B free on 42-int 9749ced (used to 0x19220) -> 352 B, floor 256)
assert (GAMEPLAY_END - GAMEPLAY_AT, PRACTICE_END - PRACTICE_AT) == (0x680, 0x980) and GAMEPLAY_END == PRACTICE_AT, \
    'swreg: GAMEPLAY 0x680 | PRACTICE 0x980, adjacent (MC 15/11: GAMEPLAY +0x80 out of PRACTICE)'
assert 0xB000 <= SWEFILE_AT < SWEFILE_END <= SETPIECE_AT < SETPIECE_END <= SLOW_AT, \
    'swreg (4.2 freeze): the 0xB000 page: SWEFILE < SETPIECE, below SLOW'
assert (TKUI_END - TKUI_AT, -(-TKUI_END // 0x1000)) == (0x1400, 0x1E) and TKUI_END == MKTHOOK_AT, \
    'swreg: TKUI 0x1400 (MC 15/11 +0x800), its ceiling page 0x1E, the 4.3 reservations right after it'
assert DIFF_END <= KITS_AT < KITS_END <= S7SWAP_AT < S7SWAP_END <= OBJ1MV_AT < OBJ1MV_END <= S7GEO_AT < S7GEO_END <= DIFF2_AT < \
    DIFF2_END <= TAKERS_AT < TAKERS_END <= GAMEPLAY_AT < GAMEPLAY_END <= PRACTICE_AT < PRACTICE_END <= S3C_AT < S3C_END <= \
    R17_AT < R17_END <= GPLX_AT < GPLX_END <= SESTRIP_AT < SESTRIP_END <= SREG2_AT < SREG2_END <= TKUI_AT < TKUI_END <= MKTHOOK_AT < MKTHOOK_END <= \
    MKTLOAD_AT < MKTLOAD_END <= MKTAGE_AT < MKTAGE_END <= DRP8D_AT < DRP8D_END <= S6_AT < S6_END < 0x30000, \
    'swreg (4.2 freeze): the release bands in map order, then the 4.3 reservations (obj4pack, MC 15/11)'
assert 0x35000 <= FPORT_AT < FPORT_END <= CDKN_AT < CDKN_END <= FPORT2_AT < FPORT2_END, \
    'swreg (4.2 freeze): the test-only bands after SP_METER (0x30000..0x34000) and DIFF_TC (0x34000..0x35000)'
