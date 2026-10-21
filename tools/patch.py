"""Build patched ITALIAN.EXE + DATA/TEAM.020 into c/SWOS (DOSBox-X install).

Patches:
 1. teamsCountryNumbers[20] (Italy) -> ITALY_BASE, so Italy can hold >51 teams
    without its global team numbers overlapping Latvia's (someLeaguesTable,
    2000 entries, keeps per-team promotion/relegation deltas by global number).
 2. Italian league structure rebuilt with 4 divisions (A, B, C1, C2) inside the
    zero-filled slack at the end of the code object; italyTable's fixup is
    retargeted there and the object's virtual size is grown to cover it.
 3. TEAM.020: non-league teams become C1, placeholders fill C1/C2 to 18 each.
"""
import os
import re
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from le import LE
from lepatch import LEPatch, add_object_page
import c1c2
import cafcups
import countries
import historic
import kitcolors
import shirtnum
import weeks
import purple
import blond
import xtra
import pgroups
import engine
import menunum
import avgprice
import fmtpage
import menumusic
import longtable
import mkseason
import careerworld
import bigtables
import worldpool
import benchnum
import split
import statecup
import nsl97
import nz97
import finals97
import mls97
import arg97
import lib97
import sacups
import trailer
import menulevels
import menutab
import nasmcave
from strpool import StrPool

ROOT = os.path.join(os.path.dirname(__file__), '..')
ITALY = 20
ITALY_BASE = 1850          # free global numbers: ~1794..1999
OBJ1_NEW_VSIZE = 0xa6000     # + five added pages (lepatch.add_object_page)
SA_CAVE = 0xa1000            # first added page: South American cups
WORLD_CAVE = 0xa2000         # second added page: new countries, CAF cups (Roadmap 2)
NZ_CAVE = 0xa4000            # fourth added page (2.1): NSSL shoot-out (the world cave may grow into page 3)
FIN_CAVE = 0xa4300           # 2.1: finals series (finals97.fin_pre)
FINALS = True                # NSL / NSSL play-offs, option B: native 4-club type-1 cup (session 28s)
ARG_CAVE = 0xa4400           # 2.1: Argentina Apertura/Clausura, aggregate, promedio (arg97)
CAREER_CAVE = 0xa6000        # 6th + 7th added pages (3.1: two; three with several worlds: cave_pages), only in builds
                             # with a historic career world (careerworld.py)
CAREER_DATA = 0xa8000        # 8th + 9th added pages (same builds; after the cave): the career packs' structs (mkseason)
HIST2_PAGE = 0x1000          # 3.2: one more page after the others (0xa6000, or 0xaa000 with a world): tourney packs'
                             # contests and the ESCI fix (historic.patch; the world cave was nearly full)
ARG_LOAD_HOOK = True

LEAGUES_OLD = bytes.fromhex('3c00144020150000000202033512')
TEAM_BASES = struct.pack('<16H', 0, 16, 26, 44, 60, 72, 86, 102, 114, 207, 207, 221, 233, 245, 287, 333)

# (teams, promoted, playoff teams, relegated, relegation playoff, playoff data)
DIVISIONS = [
    (18, 0, 0, 4, 0, 0),   # Serie A
    (20, 4, 0, 4, 0, 0),   # Serie B
    (18, 4, 0, 4, 0, 0),   # Serie C1
    (18, 4, 0, 0, 0, 0),   # Serie C2
]
TEAM_SIZE = 684

# per exe language: file, Champions Cup name (locates STR_BASE), displayed names, string pool fill order
# (the pool is first-fit: the order makes the names fit the few free string slots)
LANGS = {
    'it': dict(exe='ITALIAN.EXE', int=b'COPPA INTERCONTINENTALE', order=('LIB', 'SUP', 'CON', 'C1', 'C2', 'INT')),
    'en': dict(exe='ENGLISH.EXE', int=b'INTERCONTINENTAL CUP', order=('INT', 'LIB', 'SUP', 'CON', 'C1', 'C2')),
    'de': dict(exe='GERMAN.EXE', int=b'WELTPOKAL', reuse=('INT',),        # the game's own 'WELTPOKAL' string
               order=('CON', 'C1', 'LIB', 'SUP', 'C2')),
    'fr': dict(exe='FRENCH.EXE', int=b'COUPE INTERCONTINENTALE', order=('INT', 'LIB', 'CON', 'SUP', 'C1', 'C2')),
}


# Short contest names (the 2nd name dword: career schedule, fixtures lists; the game's own are <= 13 characters, e.g.
# 'C.D. COP EURO'). Suggested by Playaveli: long names overlapped on the career main screen.
SHORT = {sacups.LIB_ID: b'COPA LIB.', sacups.SUP_ID: b'SUPERCOPA', sacups.CON_ID: b'COPA CONMEBOL',
         cafcups.CAFCL_ID: b'CAF CL', cafcups.CAFCWC_ID: b'CAF CWC', cafcups.CAFCUP_ID: b'CAF CUP',
         cafcups.CCC_ID: b'CONCACAF CUP', cafcups.ACC_ID: b'ASIAN CC', cafcups.ACWC_ID: b'ASIAN CWC'}
SHORT_INT = {'it': b'COPPA INTERC.', 'en': b'INTERC. CUP', 'fr': b'COUPE INTERC.', 'de': None}   # WELTPOKAL is short


def short_names(p, area, lang):
    """Second name dword of the SA, CAF, CONCACAF and Asian cups -> a short name in the new obj2 page."""
    short = dict(SHORT)
    short[sacups.INT_ID] = SHORT_INT[lang]
    n = 0
    for cid, off in sacups.NAME_SITES + cafcups.NAME_SITES:
        name = short.get(cid)
        if name is None:
            continue
        assert len(name) <= 13, name
        p.put(1, off + 4, struct.pack('<I', area.add(name + b'\0') - sacups.STR_BASE))
        n += 1
    print(f'exe: short names for {n} cups')


def patch_italy(p, pool):
    """Italy's global team base and 4-division league structure. Returns cave end."""
    CAVE = (p.le.obj(1).vsize + 15) & ~15       # slack after obj1's code (ITA 0xa09c9 -> 0xa09d0, ENG 0xa0b79 -> 0xa0b80)
    d2 = p.le.obj_bytes(2)

    # 1. Italy's global team number base
    tb = d2.find(TEAM_BASES)
    assert tb >= 0 and d2.count(TEAM_BASES) == 1
    p.put(2, tb + ITALY * 2, struct.pack('<H', ITALY_BASE))

    # 2. league structure
    lo = d2.find(LEAGUES_OLD)
    assert lo >= 0 and d2.count(LEAGUES_OLD) == 1
    chairman = d2.find(b'SERIE A\0') - struct.unpack_from('<I', d2, lo + 26)[0]
    assert d2.find(b'SERIE B\0') - struct.unpack_from('<I', d2, lo + 34)[0] == chairman
    sacups.STR_BASE = chairman                  # base of all league/contest name offsets, same in every language

    n = len(DIVISIONS)
    names_at = 10 + 3 + 6 * n + 1
    hdr = bytearray(d2[lo:lo + 10])
    hdr[5] = names_at - 5
    hdr[9] = n
    body = bytes(hdr) + d2[lo + 10:lo + 13]
    for div in DIVISIONS:
        body += bytes(div)
    body += b'\0'
    name_ptrs = [struct.unpack_from('<I', d2, lo + 26)[0], struct.unpack_from('<I', d2, lo + 34)[0]]
    for name in (b'SERIE C1', b'SERIE C2'):
        name_ptrs.append(pool.add(name) - chairman)
    for ptr in name_ptrs:
        body += struct.pack('<II', ptr, ptr)
    blob = body
    assert not any(p.le.obj_bytes(1)[CAVE:CAVE + len(blob)])
    p.put(1, CAVE, blob)

    # retarget italyTable -> obj1:CAVE
    refs = [f for f in p.le.fixups() if f[3] == 2 and f[4] == lo]
    assert len(refs) == 1, refs
    p.retarget(refs[0][0], refs[0][1], 1, CAVE)
    print(f'exe: Italy base {ITALY_BASE}, leagues @ obj1+{CAVE:#x} ({len(blob)} bytes)')
    return CAVE + len(blob)


def remap_italian_cup_teams(p, remap):
    """Euro cup team lists name Italian clubs by TEAM.020 index; follow the re-sort."""
    d2 = p.le.obj_bytes(2)
    n = 0
    for hdr in (sacups.EUROCUP_HDR, sacups.CWC_HDR, sacups.UEFA_HDR):
        off = sacups.unique(d2, hdr)
        size = 7 + d2[off + 7] + 2 * d2[off + (15 if d2[off + 1] == 2 else 10)]
        for k in range(off + 7 + d2[off + 7], off + size, 2):
            if d2[k] == ITALY:
                p.put(2, k + 1, bytes((remap[d2[k + 1]],)))
                n += 1
    print(f'exe: {n} Italian clubs in euro cup lists remapped')


def cave_pages():
    """obj1 pages of the career world code (CAREER_CAVE): 3 (several worlds' tables, then 3.3.3's team cache switch
    in every big-world build overflowed 2)."""
    cp = 3
    mkseason.CAREER_CAVE_SIZE = 0x1000 * cp
    return cp


LT_SPACE = []


def patch_exe(src, dst, remap, lang='it'):
    LT_SPACE.clear()
    grown = dst + '.tmp'
    data = open(src, 'rb').read()
    worlds = bool(mkseason.worlds())
    mkseason.register_states()                         # the career worlds' state championships (statespec.py)
    import statespec
    statespec.register_test()                          # STATESPEC_TEST=1: a world-0 test state (harness)
    if statespec.TEST or statespec.TEST2 or any(e['states'] for e in statecup.ENTRIES if e['world']):
        engine.save_item('SR', statespec.SR_SIZE)      # (statespec.ko_patch: the states' rankings, the last fixed
        engine.save_item('SB', 32)                     # knockout round and its winners)
        engine.after_load('st_ovr')                    # (statespec.ov_patch: ripool's overrides on the state lists)
    import lp36
    lpb = bool(mkseason.league_phase_cups() or mkseason.league_phase_worlds() or lp36.FIXTURES)
    lpb += bool(mkseason.league_phase_worlds())   # (+1 more: the UEFA coefficients, uefacoef)
    lpb += 4 * bool(mkseason.league_phase_worlds())   # (+4: the UEFA qualifying rounds, uefaq: C code + glue)
    xtra_on = bool(mkseason.xtra_files() or os.environ.get('XTRA_HOOK'))
    bigtables.ON[0] = bigtables.needed()         # a world numbering its clubs 2000+ (World 5.0; 4.0's world 0)
    bigtables.MOVED.clear()
    pg_tabs = mkseason.parallel_tables() + engine.parallel_tables()   # parallel groups (worlds' packs; world 0: engine)
    rs_tabs = mkseason.reserve_tables() + engine.reserve_tables()     # reserves below the lowest level (gplay.c)
    if rs_tabs:                                        # their queues (RS_STATE) in the .CAR engine block: cleared on
        import gplay as gp_mod                         # a new career or an old save (init 0: seeded from the pool)
        engine.save_item('RS', gp_mod.RS_SIZE)
    ri_tabs = mkseason.off_pools()              # off-file pools: identity swaps (gplay.c ri_season, ripool.py)
    if ri_tabs:                                        # their identity map + queue (RI_STATE) in the engine block
        import ripool
        engine.save_item('RI', ripool.RI_SIZE)
    dp_tabs = mkseason.dplay_tables() if mkseason.worlds() else []   # Italian play-offs (dplay.py)
    lpb += 2 * bool(dp_tabs)                           # (+2: their code pages, before the extra one)
    gp_tabs = (mkseason.gplay_tables() if mkseason.worlds() else []) + engine.gplay_tables()   # knockout play-offs
    if gp_tabs and mkseason.worlds():                  # the played ones' state (GP_ST) in the .CAR engine block, its
        import gplay as gp_mod                         # contest pointers back after a load (gp_sync)
        engine.save_item('GP', gp_mod.GP_ST_SIZE)
        engine.after_load('gp_sync')
        if any(t[2] in gp_mod.T2_SPECS for t in gp_tabs):   # (a group contest played: the early tables beyond 2)
            engine.save_item('GS', gp_mod.GS_SIZE)
        if mkseason.cupd_tables():                     # (the Coppa Italia Serie D's state)
            engine.save_item('CD', gp_mod.CD_SIZE)
    gp_on = bool((gp_tabs or pg_tabs or rs_tabs or ri_tabs) and mkseason.worlds())         # (gplay.c also holds the parallel groups' fix)
    import gplay as gp_mod
    lpb += gp_mod.GP_PAGES * gp_on                     # (its pages, after dplay's: C + glue + specs)
    xtra_pg = bool((xtra_on or pg_tabs or rs_tabs or ri_tabs or bigtables.ON[0]) and mkseason.worlds())   # (+1: an extra code page in a build with worlds,
    xpg = 2 * xtra_pg                                  # (2 pages: xtra + pgroups + bigtables filled one in the full
    lpb += xpg                                         # world 2026-27; whose world cave is full)
    ri_pg = 2 * bool(ri_tabs and mkseason.worlds())    # (+2: the off-file pools' code + table, up to 8 files)
    lpb += ri_pg
    cos_pg = 1                                         # (+1, the top one: purple + blond + menunum + avgprice + the
    lpb += cos_pg                                      # FORMAT page: every build; without worlds too, e.g. PROTO36)
    cdp = mkseason.career_data_pages() - 2 if worlds else 0   # a big world: a 3rd career data page and a 2nd
    h2 = HIST2_PAGE * (1 + cdp)                                # historic page (its cups' fixed draws)
    cp = cave_pages()                                          # career world code: 2 pages, 3 with several worlds
    sp_tabs = (mkseason.splits() if worlds else []) + engine.split_tables()   # mid-season splits (worlds; world 0)
    sp_pg = split.pages(sp_tabs) if worlds else 0      # (own pages after all the others)
    ss_on = any(st.get('table') is not None for *_, sp in sp_tabs for st in sp.get('stages') or [])
    if ss_on:                                          # stage tables (GP_SS, gplay.c gp_stage: Argentina's Apertura /
        engine.save_item('SS', 6 + 4 * 32 * 12)        # Clausura / annual, the MLS season) in the .CAR engine block
    pr_on = any(t and any(po.get('kind') == 'promedio' for po in pk.league.get('ko_playoffs') or [])
                for pk in mkseason.packs() if pk.world is not None and pk.league for t in [True])
    if pr_on:                                          # Argentina's promedio history (gplay.c PR_STATE)
        engine.save_item('PR', 4 + 48 * 8)
    sc_pg = int(bool(statecup.ENTRIES))                # state championships (statecup.py): one page after split's
    sc_pg += statespec.SIM_PAGES * int(any(e['world'] and e['states'] for e in statecup.ENTRIES))   # (statesim.c)
    import conti                                       # the other confederations' cups (conti.c): own pages after
    ct_pg = conti.PAGES * int(bool(mkseason.league_phase_worlds() and conti.enabled()))   # statecup's, a save item
    if ct_pg:
        engine.save_item('CT', conti.ST_SIZE)
        engine.save_item('CE', conti.ED_SIZE)          # (phase B: the edition being played, conti.c CT_ED)
    for _ in range((6 + cp + 2 + 2 * cdp if worlds else 6) + lpb + sp_pg + sc_pg + ct_pg):  # (+1: the UEFA league phase's page, lp36)
        data = add_object_page(data, 1)
    mkseason.CAREER_CAVE[0] = CAREER_CAVE if worlds else None
    mkseason.CAREER_DATA[0] = CAREER_DATA + 0x1000 * (cp - 2) if worlds else None
    bigw = worlds and any(careerworld.big(w) for w in mkseason.world_defs())   # euro 128: obj2 tail + .CAR W1 block
    while True:                    # obj2: zero pages over the old BSS/stack tail, then one free page
        data = add_object_page(data, 2)
        le2 = LE(data)
        if (le2.obj(2).npages - 1) * le2.page_size >= le2.obj(2).vsize:
            break
    o2pages = 2 if worlds else 1   # career packs: one more obj2 page (their strings; two with several worlds)
    if worlds:
        data = add_object_page(data, 2)
    if mkseason.multi_ns():
        o2pages += 1
        data = add_object_page(data, 2)
    o2pages += 1                                     # the FORMAT page's menu and texts (fmtpage.py) and the zones'
    data = add_object_page(data, 2)                  # menu copy (zones.py): every build shape (a world-less season /
                                                     # tourney pack build too: its one page was full, classic_groups)
    nclubs = max((sum(len(pk.clubs) for pk in w) for w in mkseason.worlds().values()), default=0)
    for _ in range(max(0, -(-(nclubs - 1600) // 500))):   # a world of more than 1600 clubs (5.0, ~1850): its
        o2pages += 1                                     # strings + uefacoef's seeding table, one page per 500 more
        data = add_object_page(data, 2)
    for _ in range(-(-len(historic.draw_table()) // 0x1000) if mkseason.multi_ns() else 0):   # several worlds: draws in obj2
        o2pages += 1
        data = add_object_page(data, 2)
    if mkseason.league_phase_cups() or mkseason.league_phase_worlds():   # UEFA league phase: the draw's buffers
        o2pages += 2
        data = add_object_page(data, 2)
        data = add_object_page(data, 2)
    if mkseason.league_phase_worlds():          # simulated results' score table (simdraw.py, 3 KB)
        o2pages += 1
        data = add_object_page(data, 2)
    if mkseason.league_phase_worlds():          # 4.0's World 2026-27 adds: state fixture calendars (lp36 fx_patch),
        o2pages += 2                            # play-off round names / title specs' strings (gplay), the MLS (area
        data = add_object_page(data, 2)         # full with TM_MLS_EXACT or TM_TITLE)
        data = add_object_page(data, 2)
    if statespec.TEST or statespec.TEST2:       # STATESPEC_TEST builds (harness): the test state + zones' menu copy
        o2pages += 1                            # (world 0's area was full)
        data = add_object_page(data, 2)
    if bigtables.ON[0]:                         # the two tables of LIMIT global numbers (bigtables.retarget)
        o2pages += 2
        data = add_object_page(data, 2)
        data = add_object_page(data, 2)
    open(grown, 'wb').write(data)
    p = LEPatch(grown)
    os.remove(grown)
    o2 = p.le.obj(2)
    obj2_free = (o2.npages - o2pages) * p.le.page_size  # the free pages: above the stack top (ESP = old vsize)
    careerworld.BSS[0] = obj2_free + o2pages * p.le.page_size if bigw else None
    assert o2.vsize <= obj2_free and p.le.esp_obj == 2 and p.le.esp <= obj2_free
    if bigw:
        careerworld.big_team_buffer(p)     # world 2025-26: countries above 93 clubs (Italy A + B + C)
    import glob as _glob                   # (any team file above the game's 64000 B, e.g. 4.0's Italy of 146 clubs:
    tsz = max((os.path.getsize(f) for f in _glob.glob(os.path.join(os.path.dirname(dst), 'DATA', 'TEAM.*'))), default=0)
    assert tsz <= 64000 or bigw and tsz <= careerworld.TFB_SIZE - 14, \
        f'a team file of {tsz} B: above 64000 needs the big team buffer (a big world in the build), at most ' \
        f'{careerworld.TFB_SIZE - 14}'          # the big team buffer, which a big world in the build brings)
    kitcolors.patch(p)             # automatic home/away kit choice (DaniSwos's analysis)
    cfg = LANGS[lang]
    sacups.NAMES[sacups.INT_ID] = cfg['int']
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUES_OLD)
    pool = StrPool(p, lang, d2.find(b'SERIE A\0') - struct.unpack_from('<I', d2, lo + 26)[0])
    names = {'LIB': sacups.NAMES[sacups.LIB_ID], 'SUP': sacups.NAMES[sacups.SUP_ID], 'CON': sacups.NAMES[sacups.CON_ID],
             'C1': b'SERIE C1', 'C2': b'SERIE C2', 'INT': cfg['int']}
    for k in cfg.get('reuse', ()):  # names the exe already has: point at them, write nothing
        pool.reuse(names[k])
    for k in cfg['order']:          # packs the free slots
        pool.add(names[k])
    remap_italian_cup_teams(p, remap)
    cave = patch_italy(p, pool)
    assert cave <= SA_CAVE
    area = countries.Obj2Area(p, obj2_free, obj2_free + o2pages * p.le.page_size)
    if bigtables.ON[0]:
        assert bigw, 'a world numbering clubs 2000+ is a big world (careerworld.big)'
        bigtables.retarget(p, area)             # before every user of someLeaguesTable / leaguesTableCopy
    menutab.patch(p, area)                      # 4.0: the team-choice list of > 10 competitions (Italy 2026-27: 14)
    world, caf = cafcups.structs(p, area, WORLD_CAVE)
    world = countries.patch(p, lang, area, world, cafcups.continents(caf))
    fin_end, fin_pre = finals97.code(p, FIN_CAVE)  # 2.1: NSL/NSSL finals (lib_pre calls fin_pre)
    fin_end = finals97.rec_guard(p, fin_end)      # 2.5: season record of a club not in its cup (Perth Glory)
    fin_end = finals97.cal_rounds(p, fin_end)     # 2.5: NSL/NSSL play-offs: semi-finals AND final get dates
    world, lib_pre = lib97.patch(p, world, fin_pre)  # Libertadores 1997: bye, real calendar (hist_draw calls lib_pre)
    world, pack_leagues = mkseason.patch(p, lang, area, world)   # season packs (2.6: DDR 1988-89), CLASSIC SEASONS
    hist2 = OBJ1_NEW_VSIZE + (0x1000 * (cp + 2 + cdp) if worlds else 0)
    lp = None
    if mkseason.league_phase_cups() or mkseason.league_phase_worlds() or lp36.FIXTURES:   # UEFA league phase (lp36), fixture contests
        import lp36
        lp_end, lp_chk, lp_draw = lp36.patch(p, hist2 + h2, mkseason.league_phase_cups(), area, lang,
                                             mkseason.league_phase_worlds())
        assert lp_end <= hist2 + h2 + 0x1000, hex(lp_end)
        lp = (lp_chk, lp_draw)
    world = historic.patch(p, lang, area, world, lib_pre, pack_leagues, cave2=hist2, lp=lp, cave2_size=h2)
    nz_end = nz97.shootout(p, NZ_CAVE)            # 2.1: NSSL shoot-out after every draw, +1 point to its winner
    arg_end = arg97.patch(p, area, sacups.STR_BASE, ARG_CAVE, nz97.SITE_B, os.path.join(ROOT, 'orig/DATA'))   # 2.1: Apertura / Clausura
    info = cafcups.career_info(caf)
    if mkseason.league_phase_worlds():          # UEFA qualifying ties of the career club (uefaq): 3 contests in the
        import uefaq                            # slot-3 chain (D7 / E092F after the CAF / CONCACAF ones)
        q = uefaq.structs(p, area, lang, hist2 + h2 + 0x2000 + uefaq.STRUCTS_AT)
        uefaq.D7_BASE[0] = 6 + len(info['structs'])     # (sacups: D7 / E092F = 6 + index in the chain)
        info['structs'] += q
        info['kinds'] += [0, 1, 2]
    if ct_pg:                                   # the other confederations' contests: after uefaq's in the slot-3 chain
        ct_at = hist2 + h2 + 0x1000 * (lpb + sp_pg + sc_pg)
        ct_code, cq, ck = conti.structs(p, area, lang, ct_at)
        conti.D7_BASE[0] = 6 + len(info['structs'])     # (sacups: D7 / E092F = 6 + index in the chain)
        info['conti_from'] = len(info['structs'])
        info['structs'] += cq
        info['kinds'] += ck
    info['new_career_ptr'] = world              # dword filled below: sacups is assembled before the trailer code
    world += 4
    cave = sacups.patch(p, pool, SA_CAVE, info)
    arg97.late(p)                               # 2.1: Argentina aggregate table before sacups' qualifiers
    short_names(p, area, lang)
    nsl97.patch(p, area, sacups.STR_BASE)       # 2.1: Australia 1996-97 (14-club NSL), team bases moved
    nz97.patch(p, area, sacups.STR_BASE)        # 2.1: New Zealand 1996-97 (NSSL + 3 regions)
    nsl97.cup(p, area, sacups.STR_BASE)         # 2.1: NSL Cup 1996-97, real clubs and bracket
    mls97.patch(p)                              # 2.1: MLS 1997, 4 games per pair
    if FINALS:                                  # 2.5: option B (native 4-club play-off); slot4_type is NOT needed
        finals97.structs(p, area, sacups.STR_BASE)
    world, new_career = trailer.patch(p, world, sacups.SAVE_ITEMS[0] + [(base, 32) for base, _ in info['q']]
                                      + arg97.ARG_ITEMS, tails=bigw)
    if worlds:
        end = careerworld.late(p, careerworld.LABELS['end'], nasmcave)
        if bigw:
            end = careerworld.patch_tails(p, end, nasmcave)
        end = worldpool.patch(p, end, nasmcave, [(w['n'], w['pool'][0]) for w in mkseason.world_defs() if w['pool']])
        end = benchnum.patch(p, end, nasmcave, [w['n'] for w in mkseason.world_defs() if w['squad_numbers']])
        assert end <= CAREER_CAVE + mkseason.CAREER_CAVE_SIZE, hex(end)
    p.add_ptr(1, info['new_career_ptr'], 1, new_career)
    if ARG_LOAD_HOOK:
        arg_end = arg97.load_hook(p, arg_end)     # 2.1: Apertura/Clausura names after loading a career
        careerworld.ns_load(p, arg97.LOAD_CALL[0])   # several worlds: the save's namespace before the trailer
    arg_end = finals97.rec_playoff(p, arg_end)    # 2.5: the play-off winner is the champion in the record (FIN cave full)
    arg_end = careerworld.euro_draw(p, arg_end, nasmcave)   # 2.7.x: no same-country ties in rounds 1-2 of the
                                                  # European cups of a career (1996-97 CWC / UEFA, worlds)
    lib97.chain_adv(p)                           # national-cup byes before the round advance's draw (euro_draw's hook)
    arg_end = kitcolors.button(p, arg_end, lang, area)  # KITS button + SELECT KITS menu (pre-match screen)
    if mkseason.league_phase_worlds():          # UEFA coefficients of a league-phase world (own page after lp36's)
        import uefacoef
        import lp36
        a0 = sacups.regs(p.le.obj_bytes(1))['A0']
        s36 = lp36._sites(p)
        cs = {'tmd': careerworld.LABELS['sites']['tmd'], 'tcn': countries.tables(p)[1], 'diy': s36['DIY'],
              'diycopy': s36['DIYCOPY'], 'qual': careerworld._qual_sites(p.le.obj_bytes(1), p), 'a0': a0,
              'lp_ord': lp36.LABELS['LP_ORD'], 'area': area}
        uc_end = uefacoef.patch(p, hist2 + h2 + 0x1000, mkseason.world_defs(), cs)
        import simdraw                          # simulated results: real draws and goals (World 2026-27)
        uc_end = simdraw.patch(p, uc_end, area, careerworld.LABELS['sites']['gametype'], careerworld.LABELS['w_lpw'],
                               historic._coin_sites(p, historic._draw_call(p)[1])['rand2'])
        assert uc_end <= hist2 + h2 + 0x2000, hex(uc_end)
        import uefaq                            # UEFA qualifying rounds (C code, tools/uefaq.c; 4 pages)
        cs['bss'] = careerworld.BSS[0]
        cs['lceu'] = mkseason.league_cup_europe_files()
        cs['sel'] = sacups.SEL_ADDR[0]
        cs.update(sacups.SITES)
        uq_end = uefaq.patch(p, hist2 + h2 + 0x2000, hist2 + h2 + 0x2000 + uefaq.STRUCTS_AT, cs)
        import rnames                           # the real round names (league phase, round of 16 ...): in uefaq's
        lp_ids = [p.get(o, a, 1)[0] for o, a in careerworld.SITES['euro']]          # pages, before its structs
        rnames.patch(p, uq_end, hist2 + h2 + 0x2000 + uefaq.STRUCTS_AT, lang, area, lp_ids, mkseason.numbered_cups())
        careerworld.BSS_SIZE = (careerworld.B_UQ + careerworld.UQ_BSS + careerworld.UQ_RECS * 684 + 0xFFF) & ~0xFFF
    if dp_tabs:                                 # Italian play-offs (C, tools/dplay.c; own 2 pages,
        import dplay                            # its .bss after the career BSS)
        dp_at = hist2 + h2 + 0x1000 * (lpb - cos_pg - 2 - gp_mod.GP_PAGES * gp_on - xpg - ri_pg)
        dplay.patch(p, dp_at, dp_at + 0x2000, dp_tabs, careerworld.BSS[0] + careerworld.BSS_SIZE, area)
        careerworld.BSS_SIZE += 0x1000
    if gp_on:                                   # knockout play-offs (C, tools/gplay.c; chained after dplay's hooks)
        import gplay                            # and the parallel groups' season-end fix (pg_season, pgroups.py)
        gp_at = hist2 + h2 + 0x1000 * (lpb - cos_pg - gplay.GP_PAGES - xpg - ri_pg)
        gp_end = gplay.patch(p, gp_at, gp_at + 0x1000 * gplay.GP_PAGES, gp_tabs, careerworld.BSS[0] + careerworld.BSS_SIZE, area, lang)
        LT_SPACE[:] = [(gp_end + 15) & ~15, gp_at + 0x1000 * gplay.GP_PAGES]   # (4.0: longtable's code after gplay's)
        if rs_tabs:
            engine.ITEM_AT['RS'] = gplay.LABELS['RS_STATE']
        if ri_tabs:
            engine.ITEM_AT['RI'] = gplay.LABELS['RI_STATE']
        if ss_on:
            engine.ITEM_AT['SS'] = gplay.LABELS['GP_SS']
        if pr_on:
            engine.ITEM_AT['PR'] = gplay.LABELS['PR_STATE']
        engine.ITEM_AT['GP'] = gplay.LABELS['GP_ST']    # (the played play-offs' state; its pointers after a load)
        if 'GS' in engine.SAVE_ITEMS:
            engine.ITEM_AT['GS'] = gplay.LABELS['GP_GS']
        if 'CD' in engine.SAVE_ITEMS:
            engine.ITEM_AT['CD'] = gplay.LABELS['CD_ST']
        engine.CALL_AT['gp_sync'] = (1, gplay.LABELS['gp_sync'])
        pgroups.relax_file_check(p)             # (moves of several divisions: cseg_9487A's per-file sum check)
        careerworld.BSS_SIZE += gplay.GP_BSS
    if ri_tabs:                                 # the off-file pool's buffers (Italy's file as read, the pool's file)
        import ripool
        ri_bss = careerworld.BSS[0] + careerworld.BSS_SIZE
        careerworld.BSS_SIZE += (ripool.bss_need(ri_tabs) + 0xFFF) & ~0xFFF
    if ct_pg:                                   # conti.c's .bss (the other confederations' cups)
        ct_bss = careerworld.BSS[0] + careerworld.BSS_SIZE
        careerworld.BSS_SIZE += conti.BSS
    assert cave <= WORLD_CAVE, hex(cave)
    print(f'exe: caves: world end {world:#x} (limit {NZ_CAVE:#x}), arg end {arg_end:#x} (limit {OBJ1_NEW_VSIZE:#x})')
    world = cafcups.intl_list(p, caf, world)
    num_bss = obj2_free + o2pages * p.le.page_size + (careerworld.BSS_SIZE if bigw else 0)
    world = shirtnum.patch(p, world, num_bss)    # 3.2.5: shirt numbers 17..99 over the players (built from the digits)
    weeks.patch(p)                               # 3.2.7: career weeks 128+ (mod cups outside Europe) in the job offers
    if gp_on and arg97.LABELS.get('GP_AFTER') and 'gp_after' in gplay.LABELS:   # 4.0: arg_load's call after a load
        p.put(1, arg97.LABELS['GP_AFTER'], struct.pack('<I', 0))
        p.add_ptr(1, arg97.LABELS['GP_AFTER'], 1, gplay.LABELS['gp_after'])
    cos = hist2 + h2 + 0x1000 * (lpb - 1) if cos_pg else world   # (worlds: their own page)
    cos = purple.patch(p, area, cos)            # 3.3.0: kit colour 10 = purple (palette entry 12 when no maroon; in
                                                # the cosmetics page with worlds: the world cave is full, 2026-27)
    cos = blond.patch(p, area, cos, num_bss + shirtnum.BSS_SIZE, shirtnum.spr_index(p))   # 3.3.0: face 3
    cos = menunum.patch(p, cos, num_bss + shirtnum.BSS_SIZE + blond.BSS_SIZE)   # 3.3.4: menu numbers 17..99
    cos = avgprice.patch(p, cos)                 # 3.3.4: average player price >= 1 (divide error, 1984-85 Iceland)
    cos = menumusic.patch(p, cos)                # 3.3.6: menu music when the main menu opens (SWOS++ options load late)
    cos = fmtpage.patch(p, cos, lang, area, num_bss + shirtnum.BSS_SIZE + blond.BSS_SIZE + menunum.BSS_SIZE,
                         careerworld.SITES if worlds else None)   # FORMAT page (5.0)
    cos = menulevels.patch(p, cos, area, lang)   # 4.0: team choice of a league with levels of groups: level, then group
    import zones                                 # 4.0: zone colours in the league tables (light blue, green, ...)
    cos = zones.patch(p, cos, area, lang, [e if os.sep in e else os.path.join(mkseason.PACKS, e) for e in mkseason.ENABLED],
                      num_bss + shirtnum.BSS_SIZE + blond.BSS_SIZE + menunum.BSS_SIZE, fmtpage.BSS_SIZE,
                      careerworld.SITES if worlds else None)   # (the FORMAT page's buffer, shared)
    if LT_SPACE and LT_SPACE[1] - LT_SPACE[0] >= 0x700:        # (4.0: in gplay's pages - the cosmetics page is full)
        lt_end_ = longtable.patch(p, LT_SPACE[0], area, lang)
        if worlds and any(pk.meta.get('id', '').startswith('world-2026-27-') for pk in mkseason.packs()):
            import mainbtn                               # 4.0: the green CARRIERA 2026-27 button on the main menu
            lt_end_ = mainbtn.patch(p, (lt_end_ + 15) & ~15, lang)
        assert lt_end_ <= LT_SPACE[1], hex(lt_end_)
        print(f'exe: longtable code in gplay\'s pages: obj1+{LT_SPACE[0]:#x}..{lt_end_:#x} (free to {LT_SPACE[1]:#x})')
    else:
        cos = longtable.patch(p, cos, area, lang)                # 4.0: tables over 24 clubs scroll (ARG / MLS 30: no drawing past the screen)
    if cos_pg:
        assert cos <= hist2 + h2 + 0x1000 * lpb, hex(cos)
    else:
        world = cos
    if xtra_pg:                                                  # extended career squads (packs with "extra";
        xp = hist2 + h2 + 0x1000 * (lpb - cos_pg - ri_pg - xpg)  # XTRA_HOOK=1: test builds): DATA\XTRA.nnn players;
        xe = xtra.patch(p, xp) if xtra_on else xp                # the extra page in a build with worlds, with the
        ri = None
        if ri_tabs:                                              # the off-file pool (Eccellenza): its own page
            rp = hist2 + h2 + 0x1000 * (lpb - cos_pg - ri_pg)
            re_, ri = ripool.patch(p, rp, ri_bss, ri_tabs)
            assert re_ <= rp + 0x1000 * ri_pg, hex(re_)
        if pg_tabs or rs_tabs or ri_tabs:                        # parallel groups' / reserves' season end (pgroups.py)
            xe = pgroups.patch(p, (xe + 15) & ~15, pg_tabs, gplay.LABELS['pg_season'], rs_tabs, gplay.LABELS['rs_season'],
                               ri=ri, cd={'CD_SEASON': gplay.LABELS['cd_season'], 'CD_TAB': (1, gplay.LABELS['CD_TAB']),
                                          'CD_DT': (1, gplay.LABELS['CD_DT'])} if 'CD_DT' in gplay.LABELS else None)
            gplay.link_reserve(p, ri)                            # (the reserves: gp_sack's tables)
        if bigtables.ON[0]:                                      # the .CAR's 2000 bytes <-> the moved tables,
            xe = bigtables.hooks(p, (xe + 15) & ~15)             # numbers 2000+ (after every finder of the tables)
        assert xe <= xp + 0x1000 * xpg, hex(xe)
    elif xtra_on:
        world = xtra.patch(p, world)
    assert world <= NZ_CAVE and nz_end <= FIN_CAVE and fin_end <= ARG_CAVE and arg_end <= OBJ1_NEW_VSIZE, \
        (hex(world), hex(nz_end), hex(fin_end), hex(arg_end))
    careerworld.ns_xtra(p, xtra.LABELS['XTRA_NAMEP'] if xtra_on else None)   # several worlds: XTWn.nnn names
    mkseason.ns_emit(p)                          # several worlds: the namespaces' rows, the base one static
    if sp_pg:                                    # World 2026-27: mid-season splits (split.py), after lpb's pages
        sp_at = hist2 + h2 + 0x1000 * lpb
        sp_end = split.patch(p, sp_at, nasmcave, sp_tabs)
        assert sp_end <= sp_at + 0x1000 * sp_pg, hex(sp_end)
    if sc_pg:                                    # state championships in career / Season slot 1 (statecup.py)
        sc_at = hist2 + h2 + 0x1000 * (lpb + sp_pg)
        sc_end = statecup.test_contest(p, sc_at) if statecup.TEST else sc_at   # (STATECUP_TEST=1 builds)
        sc_end = statespec.test_contest(p, sc_end) if statespec.TEST or statespec.TEST2 else sc_end   # (STATESPEC_TEST=1 / 2 builds)
        sc_end = lp36.fx_patch(p, sc_end, area)    # fixture contests (cross-group round robins) on this page
        sc_end = statecup.slot_types(p, sc_end)
        statecup.cup_end_types(p)
        sc_end = statecup.patch(p, sc_end)
        sc_end = statespec.ko_patch(p, sc_end)     # careers' state knockouts + the played state's ranking ('SB', 'SR')
        assert sc_end <= sc_at + 0x1000, hex(sc_end)
        if sc_pg > 1:
            statespec.sim_patch(p, sc_at + 0x1000)  # statesim.c: every state's stage 1 + relegation at the season end
    if ct_pg:                                    # the other confederations' cups (conti.c): after statecup's pages
        conti.patch(p, ct_code, ct_at + 0x1000 * ct_pg, ct_bss, area)
    p.set_vsize(1, OBJ1_NEW_VSIZE + (0x1000 * (cp + 2 + cdp) if worlds else 0) + h2 + 0x1000 * (lpb + sp_pg + sc_pg + ct_pg))
    tail = (careerworld.BSS_SIZE if bigw else 0) + shirtnum.BSS_SIZE + blond.BSS_SIZE + menunum.BSS_SIZE + fmtpage.BSS_SIZE   # obj2 tail
    p.set_vsize(2, obj2_free + o2pages * p.le.page_size + tail, bss=tail)
    p.add_flags(1, 0x2)            # writable: season end rewrites the SA cup team lists in the cave
    split.late(p)                                # split's after-stage routines (engine.after_stage)
    trailer.late(p)                              # the engine block's late addresses (RS_STATE ...)
    delta, shift = p.save(dst)
    print(f'exe: fixups +{delta} bytes, data pages moved {shift:#x}, caves used up to obj1+{cave:#x} / +{world:#x}')


def team(rec, ordinal, league, name=None):
    r = bytearray(rec)
    r[1] = ordinal
    struct.pack_into('>H', r, 2, ITALY_BASE + ordinal)
    r[25] = league
    if name:
        r[5:22] = name.encode('latin1').ljust(17, b'\0')[:17]
    return bytes(r)


def team_fix(data, header=True):
    """3.3.0: every team file the build writes: purple clubs (purple.recolor), blond players (blond.faces)."""
    return blond.faces(purple.recolor(data, header)[0], header)[0]


def patch_teams(src, dst):
    d = open(src, 'rb').read()
    n = struct.unpack('>H', d[:2])[0]
    recs = [d[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE] for i in range(n)]
    by_name = {r[5:22].split(b'\0')[0].decode('latin1'): r for r in recs}
    nonleague = [r for r in recs if r[25] == 4]
    rng = random.Random(1997)
    out = [r for r in recs if r[25] in (0, 1)]
    used = {r[76 + k * 38 + 3:76 + k * 38 + 26].split(b'\0')[0].decode('latin1') for r in out for k in range(16)}
    clubs = [(t, 2, None, by_name[t]) for t in c1c2.EXISTING_C1] + [(t, 3, None, by_name[t]) for t in c1c2.EXISTING_C2]
    clubs += [(t, 2, k, None) for t, k in c1c2.NEW_C1.items()] + [(t, 3, k, None) for t, k in c1c2.NEW_C2.items()]
    for name, league, kit, base in clubs:     # all C1/C2 clubs: real 1996-97 squads (c1c2_rosters.py)
        rec, fillers = c1c2.real_team(nonleague, name, league, kit, rng, used, base)
        out.append(rec)
        if fillers:
            print(f'TEAM.020: {name}: {len(fillers)} player(s) not in the 1996-97 source, kept/random {fillers}')
    out.sort(key=lambda r: r[5:22])
    out = [team(r, i, r[25]) for i, r in enumerate(out)]
    counts = [sum(1 for r in out if r[25] == lg) for lg in range(4)]
    assert counts == [18, 20, 18, 18] and len(out) <= 93, counts
    open(dst, 'wb').write(team_fix(struct.pack('>H', len(out)) + b''.join(out)))   # 3.3.0: purple clubs
    print(f'TEAM.020: {len(out)} teams, A/B/C1/C2 = {counts}')
    new_idx = {r[5:22]: i for i, r in enumerate(out)}
    return {i: new_idx[r[5:22]] for i, r in enumerate(recs) if r[5:22] in new_idx}

def hist_base(n):
    """First global number of a historic file (historic.BASE shared; season pack files have their own)."""
    b = mkseason.base_of(n)
    return historic.BASE if b is None else b


def write_new_teams(src_dir, dst_dir):
    """Team files of the new countries (africa.py); checks their global numbers against every other team file."""
    import africa, asia, namerica, glob
    files = {**africa.build(src_dir), **asia.build(src_dir), **namerica.build(src_dir)}
    taken = {}
    tcn = {n: c['base'] for n, c in countries.COUNTRIES.items() if 'base' in c}
    d2 = LE(os.path.join(ROOT, 'orig/ENGLISH.EXE')).obj_bytes(2)
    bases = list(struct.unpack_from('<256H', d2, d2.find(struct.pack('<6H', 0, 16, 26, 44, 60, 72))))
    for n, (_, b) in nsl97.BASE_MOVES.items():        # 2.1: NZ and Bolivia moved (room for Australia and NZ)
        bases[n] = b
    for f in sorted(glob.glob(os.path.join(src_dir, 'TEAM.0[0-9][0-9]'))):
        n = int(f[-3:])
        if n in files or n in (20, nsl97.FILE, nz97.FILE, mls97.FILE):
            continue
        d = open(f, 'rb').read()
        for i in range(struct.unpack('>H', d[:2])[0]):   # the game recomputes it: base[team byte 0] + team byte 1
            r = d[2 + i * TEAM_SIZE:]
            taken[bases[r[0]] + r[1]] = n
    italy = struct.unpack('>H', open(os.path.join(dst_dir, 'TEAM.020'), 'rb').read(2))[0]   # written by patch_teams
    for g in range(ITALY_BASE, ITALY_BASE + italy):
        taken[g] = 20
    for g in range(sacups.MARK3_GLOBAL, sacups.MARK3_GLOBAL + 3):   # career mark 'S3' + balance (1.2; lists in the
        taken[g] = 'S3'                                             # .CAR trailer, 1730..1846 free again)
    for g in (careerworld.WORLD_BYTE, careerworld.WORLD_BYTE + 1):   # career packs: world byte + balance
        taken[g] = 'world'
    hist = historic.build_teams(src_dir)
    for n, data in list(files.items()) + list(hist.items()):
        k = struct.unpack('>H', data[:2])[0]
        base = tcn.get(n) or hist_base(n)
        for g in range(base, base + k):
            assert g < (bigtables.LIMIT if mkseason.worlds() and bigtables.needed() else 2000) and \
                (mkseason.shares_base(n) or mkseason.career_file(n) or g not in taken), (n, g, taken.get(g))
            assert not (mkseason.career_file(n) and sacups.SAVED_GLOBAL <= g <= sacups.MARK3_GLOBAL + 2), \
                (n, g, f'world clubs must skip the reserved global numbers {sacups.SAVED_GLOBAL}..{sacups.MARK3_GLOBAL + 2} '
                 '(the saved SA block, the world byte, the career mark: someLeaguesTable)')
            if n not in hist:
                taken[g] = n
        open(os.path.join(dst_dir, 'TEAM.%03d' % n), 'wb').write(team_fix(data))
        print(f'TEAM.{n:03d}: {k} teams, global numbers {base}..{base + k - 1}')
    for mod in (nsl97, nz97, mls97):                  # 2.1: Australia (54 records), New Zealand (40), MLS 1997
        data = mod.build(src_dir)
        for i in range(struct.unpack('>H', data[:2])[0]):
            r = data[2 + i * TEAM_SIZE:]
            g = bases[r[0]] + r[1]
            assert g < 2000 and g not in taken, (mod.FILE, g, taken.get(g))   # word +2 is recomputed by the game
            taken[g] = mod.FILE
        open(os.path.join(dst_dir, 'TEAM.%03d' % mod.FILE), 'wb').write(team_fix(data))
    print(f'TEAM.{nsl97.FILE:03d}/{nz97.FILE:03d}/{mls97.FILE:03d}: Australia and New Zealand 1996-97, MLS 1997')
    for name, data in mkseason.rs_files().items():     # off-file pools (ripool.py): their clubs' records
        k = struct.unpack('>H', data[:2])[0]
        assert 0 < k <= 95, (name, k)
        open(os.path.join(dst_dir, name), 'wb').write(team_fix(data))
        print(f'{name}: {k} off-file pool clubs')
    for name, data in mkseason.xtra_files().items():   # extended career squads: players beyond 16 (xtra.py)
        open(os.path.join(dst_dir, name), 'wb').write(data)
        print(f'{name}: up to {data[2]} more players for {struct.unpack(">H", data[:2])[0]} clubs')
    import careerworld as cw_                         # (a big world: teamFileBuffer is careerworld's TFB_SIZE one,
    tfb = (cw_.TFB_SIZE - 14 if any(cw_.big(w) for w in mkseason.world_defs())   # 257 clubs: the
           else 106496)                               # 4.0 build's TMW5.102 = Italy 2026-27's 256)
    import guests
    for name, data in guests.team_files().items():      # the continental cups' guest clubs (guests.py: their globals
        k = struct.unpack('>H', data[:2])[0]             # alias 1996-97 files the world never loads, guests.alloc)
        open(os.path.join(dst_dir, name), 'wb').write(team_fix(data))
        print(f'{name}: {k} guest clubs, global numbers {struct.unpack(">H", data[4:6])[0]}..'
              f'{struct.unpack(">H", data[4:6])[0] + k - 1}')
    for name, data in mkseason.ns_team_files().items():   # several worlds: the team files of a namespace of its own
        k = struct.unpack('>H', data[:2])[0]
        assert k * TEAM_SIZE + 2 <= tfb, (name, k)
        open(os.path.join(dst_dir, name), 'wb').write(team_fix(data))   # (3.3.0 purple clubs, blond players)
        print(f'{name}: {k} teams')
    for name, data in mkseason.world_files().items():  # career packs: first-season European clubs of each world
        open(os.path.join(dst_dir, name), 'wb').write(team_fix(data, header=False))
        print(f'{name}: {len(data) // TEAM_SIZE} European clubs')
    for n in purple.VANILLA_FILES:                    # 3.3.0: original team files whose purple clubs wore maroon
        data, k = purple.recolor(open(os.path.join(src_dir, 'TEAM.%03d' % n), 'rb').read())
        assert k, n
        open(os.path.join(dst_dir, 'TEAM.%03d' % n), 'wb').write(blond.faces(data)[0])
    print(f'purple clubs: TEAM.{", ".join("%03d" % n for n in purple.VANILLA_FILES)} recoloured')
    import fmtgame                                    # 5.0 / 4.0: the FORMAT page's texts (fmtpage.py), per world
    items = [x for e in mkseason.ENABLED for x in fmtgame.from_pack(e if os.sep in e else os.path.join(mkseason.PACKS, e))] + fmtgame.world_items() + fmtgame.conti_items() + fmtgame.EXTRA
    for name, k in fmtgame.write(dst_dir, items):
        print(f'{name}: FORMAT pages of {k} competitions')
    import zones                                      # 4.0: the league tables' zone colours, per world
    for name, k in zones.write(dst_dir, [e if os.sep in e else os.path.join(mkseason.PACKS, e) for e in mkseason.ENABLED]):
        print(f'{name}: zone colours of {k} league tables')
    rename_clubs(src_dir, dst_dir)


# 4.0 (Davide, 2026-10-18): the Milan clubs by the names they go by. Name fields are zero padded: the shorter name +
# zeros, the rest of the record unchanged. Every team file the build wrote (1996-97, the historic packs and worlds,
# which take some names from the 1996-97 records) and the original files that hold them (European cup tourneys, the
# transfer pool), all languages (the DATA files are shared).
CLUB_NAMES = {b'INTER MILAN': b'INTER', b'AC MILAN': b'MILAN', b'INTERNAZIONALE': b'INTER'}   # (the last: historic packs)
RENAMED_ORIGINALS = ('EUROCUP.TMD', 'UEFACUP.TMD', 'POOLPLYR.DAT')


def rename_names(data):
    pat = re.compile(rb'(?<![A-Z0-9 .])(' + b'|'.join(re.escape(k) for k in CLUB_NAMES) + rb')\x00')
    return pat.sub(lambda m: CLUB_NAMES[m.group(1)] + b'\0' * (len(m.group(1)) - len(CLUB_NAMES[m.group(1)]) + 1),
                   data), len(pat.findall(data))


def rename_clubs(src_dir, dst_dir):
    done = []
    for name in sorted(os.listdir(dst_dir)):
        if re.fullmatch(r'TEAM\.\d{3}|TMW\d\.\d{3}|.*\.TMD', name):
            data, k = rename_names(open(os.path.join(dst_dir, name), 'rb').read())
            if k:
                open(os.path.join(dst_dir, name), 'wb').write(data)
                done.append(f'{name} {k}')
    for name in RENAMED_ORIGINALS:
        data, k = rename_names(open(os.path.join(src_dir, name), 'rb').read())
        assert k, name
        open(os.path.join(dst_dir, name), 'wb').write(data)
        done.append(f'{name} {k}')
    print('INTER / MILAN: ' + ', '.join(done))


if __name__ == '__main__':
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else 'it'
    exe = LANGS[lang]['exe']
    swos = os.path.join(ROOT, 'c/SWOS')
    remap = patch_teams(os.path.join(ROOT, 'orig/DATA/TEAM.020'), os.path.join(swos, 'DATA/TEAM.020'))
    write_new_teams(os.path.join(ROOT, 'orig/DATA'), os.path.join(swos, 'DATA'))
    patch_exe(os.path.join(ROOT, 'orig', exe), os.path.join(swos, exe), remap, lang)
