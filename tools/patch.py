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
import mkseason
import careerworld
import nsl97
import nz97
import finals97
import mls97
import arg97
import lib97
import sacups
import trailer
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


def patch_exe(src, dst, remap, lang='it'):
    grown = dst + '.tmp'
    data = open(src, 'rb').read()
    for _ in range(5):
        data = add_object_page(data, 1)
    while True:                    # obj2: zero pages over the old BSS/stack tail, then one free page
        data = add_object_page(data, 2)
        le2 = LE(data)
        if (le2.obj(2).npages - 1) * le2.page_size >= le2.obj(2).vsize:
            break
    open(grown, 'wb').write(data)
    p = LEPatch(grown)
    os.remove(grown)
    o2 = p.le.obj(2)
    obj2_free = (o2.npages - 1) * p.le.page_size       # the last page: above the stack top (ESP = old vsize)
    assert o2.vsize <= obj2_free and p.le.esp_obj == 2 and p.le.esp <= obj2_free
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
    area = countries.Obj2Area(p, obj2_free, obj2_free + p.le.page_size)
    world, caf = cafcups.structs(p, area, WORLD_CAVE)
    world = countries.patch(p, lang, area, world, cafcups.continents(caf))
    fin_end, fin_pre = finals97.code(p, FIN_CAVE)  # 2.1: NSL/NSSL finals (lib_pre calls fin_pre)
    fin_end = finals97.rec_guard(p, fin_end)      # 2.5: season record of a club not in its cup (Perth Glory)
    fin_end = finals97.cal_rounds(p, fin_end)     # 2.5: NSL/NSSL play-offs: semi-finals AND final get dates
    world, lib_pre = lib97.patch(p, world, fin_pre)  # Libertadores 1997: bye, real calendar (hist_draw calls lib_pre)
    world, pack_leagues = mkseason.patch(p, lang, area, world)   # season packs (2.6: DDR 1988-89), CLASSIC SEASONS
    world = historic.patch(p, lang, area, world, lib_pre, pack_leagues)
    nz_end = nz97.shootout(p, NZ_CAVE)            # 2.1: NSSL shoot-out after every draw, +1 point to its winner
    arg_end = arg97.patch(p, area, sacups.STR_BASE, ARG_CAVE, nz97.SITE_B, os.path.join(ROOT, 'orig/DATA'))   # 2.1: Apertura / Clausura
    info = cafcups.career_info(caf)
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
                                      + arg97.ARG_ITEMS)
    p.add_ptr(1, info['new_career_ptr'], 1, new_career)
    if ARG_LOAD_HOOK:
        arg_end = arg97.load_hook(p, arg_end)     # 2.1: Apertura/Clausura names after loading a career
    arg_end = finals97.rec_playoff(p, arg_end)    # 2.5: the play-off winner is the champion in the record (FIN cave full)
    assert cave <= WORLD_CAVE, hex(cave)
    world = cafcups.intl_list(p, caf, world)
    assert world <= NZ_CAVE and nz_end <= FIN_CAVE and fin_end <= ARG_CAVE and arg_end <= OBJ1_NEW_VSIZE, \
        (hex(world), hex(nz_end), hex(fin_end), hex(arg_end))
    p.set_vsize(1, OBJ1_NEW_VSIZE)
    p.set_vsize(2, obj2_free + p.le.page_size)
    p.add_flags(1, 0x2)            # writable: season end rewrites the SA cup team lists in the cave
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
    open(dst, 'wb').write(struct.pack('>H', len(out)) + b''.join(out))
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
            assert g < 2000 and (mkseason.shares_base(n) or mkseason.career_file(n) or g not in taken), (n, g, taken.get(g))
            if n not in hist:
                taken[g] = n
        open(os.path.join(dst_dir, 'TEAM.%03d' % n), 'wb').write(data)
        print(f'TEAM.{n:03d}: {k} teams, global numbers {base}..{base + k - 1}')
    for mod in (nsl97, nz97, mls97):                  # 2.1: Australia (54 records), New Zealand (40), MLS 1997
        data = mod.build(src_dir)
        for i in range(struct.unpack('>H', data[:2])[0]):
            r = data[2 + i * TEAM_SIZE:]
            g = bases[r[0]] + r[1]
            assert g < 2000 and g not in taken, (mod.FILE, g, taken.get(g))   # word +2 is recomputed by the game
            taken[g] = mod.FILE
        open(os.path.join(dst_dir, 'TEAM.%03d' % mod.FILE), 'wb').write(data)
    print(f'TEAM.{nsl97.FILE:03d}/{nz97.FILE:03d}/{mls97.FILE:03d}: Australia and New Zealand 1996-97, MLS 1997')
    for name, data in mkseason.world_files().items():  # career packs: first-season European clubs of each world
        open(os.path.join(dst_dir, name), 'wb').write(data)
        print(f'{name}: {len(data) // TEAM_SIZE} European clubs')


if __name__ == '__main__':
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else 'it'
    exe = LANGS[lang]['exe']
    swos = os.path.join(ROOT, 'c/SWOS')
    remap = patch_teams(os.path.join(ROOT, 'orig/DATA/TEAM.020'), os.path.join(swos, 'DATA/TEAM.020'))
    write_new_teams(os.path.join(ROOT, 'orig/DATA'), os.path.join(swos, 'DATA'))
    patch_exe(os.path.join(ROOT, 'orig', exe), os.path.join(swos, exe), remap, lang)
