"""Team-cache audit, leg 2 (teamcache-fable-design.md 1.8): what in a real .CAR save depends on the cache's address.

    python3 tools/tcaudit.py [--report FILE.md] [--store DIR] [--jobs N] PATH ...

PATH = a .CAR file, a directory (walked, symlinks not followed) or a tar archive (read in place with tarfile, nothing is
extracted). Saves are deduplicated by sha1. Read-only on every PATH; it writes only --report (+ FILE.tsv: every hit) and
--store (zlib copies of the distinct saves + an index of the archives read, so a later run reads only new archives).

Per save (file = fixed part 95153 B: careerFileBuffer .. g_numSelectedTeams; then N records of 684 B; then the trailer:
main block, engine block 'EN' of items):
1. Declared positions. The 5 competition buffers (ProcessCareerFile's arrayOfPointers; wsites.DIY_SLOTS) each hold a DIY
   contest, walked by the WS_D rules (sreg_walk.c walk_diy): type word +0 (0 league, 1 cup, 2 = header + the current
   stage's contest at +0x41F, itself type 0 / 1), numTeams +49 (<= 64), the type's size within the slot's room - else the
   buffer is "refused" (not a contest) and nothing in it is declared. A contest keeps each club as a DWORD offset from
   selTeamsPtr: league rows +691 + 18 i, i < numTeams; cups +0x343 + 4 x, x = each of the numTeams order bytes at +717
   (the writer, cseg_27436: a plain cup's order is a permutation of 0..n-1; a type 2's knockout stage holds one tie,
   numTeams 2, whose order bytes index the whole list - the two entries are not entries 0 and 1). Every such dword is
   classed
     record      a multiple of 684 below N x 684
     careerTeam  the player's club record (careerFileBuffer + 0xDB80) - selTeamsPtr as saved: -0x9831 when the cache
                 is the game's (it follows the fixed part); with the big cache (B_SEL) a negative value whose address
                 has careerTeam's page offset (the loader's own test, careerworld w_loadcopy; any of the 4 languages), one value per save
     OTHER       anything else, with a sub-kind:
                 stale-rec   a multiple of 684 from N x 684 to 160 x 684: a record offset of an earlier, larger cache
                             (a declared list not filled yet: play-offs / a later stage, or last season's contest). It
                             does not depend on the cache's address
                 fixed       selTeamsPtr + value falls inside careerFileBuffer's fixed part (not careerTeam): an offset
                             to an object outside the cache = what H1 says does not exist. tmd = one of the 80 records
                 big-tmd     a record of a big world's B_TMD area seen from B_SEL (value = 684 k - 0x5C000, k < 128)
                 in-cache    inside the cache's room, not a record start
                 far         anywhere else
   Liveness: the file has no "slot in use" mark (the game keeps it in BSS pointers rebuilt at load); the career
   calendar (757 x 22 B at fixed + 0x11E5A, byte 0 of each entry = the slot; read up to its end: a size 0 or a week
   going back) names the slots that have matches this season. A buffer whose slot is not in the calendar is "idle" (bytes of an earlier contest); its dwords are classed
   too but counted apart.
2. Strays. Every byte offset of the whole file (fixed part with its W1 block, records, main block, every EN item) is
   scanned for a dword equal to
   (a) an absolute address of a record in the save's cache (selTeamsPtr + 684 k, k < 160; the game's cache: k < 100) -
       the one declared place is selTeamsPtr itself, fixed part + 0x1739C. A pointer field would follow the cache: the
       same place would hold selTeamsPtr + 684 k under every address the cache had (the archive has dozens: one per
       build layout). So a place counts as a stray when it hits under >= 3 different selTeamsPtr values, or under 2
       and in at least half of the saves that have those values; any other hit is an "address coincidence" (bytes that
       happen to read as that one address: with the cache at 0x4A0000 every word pair 0000 004A is "record 0"),
       counted and listed apart. Dwords that merely fall inside the cache's address range without being a record
       start are counted, not listed, next to the same count for the two neighbouring ranges of the same size
       (control: text and word pairs give the same rate there);
   (b) careerTeam's offset outside the declared positions. A (b) hit inside one of the 5 buffers at a place that is an
       offset-array entry under some layout (past numTeams, another type's array, an idle / refused buffer) is "stale"
       (an earlier contest's bytes; the loader's exact-value rewrite covers the whole range 0xF77E..0x16ABC), counted
       apart; anywhere else it is a stray.
   The game saves no relocated pointers (the code at cseg:000335E3 that would subtract aChairmanScenes is unreferenced);
   ProcessCareerFile rebuilds every pointer at load.
Wanted: OTHER = 0, strays = 0, in every world (world byte = someLeaguesTable[1845]; 0 = 1996-97)."""
import hashlib
import json
import os
import struct
import sys
import tarfile
import zlib

TEAM, FIXED = 684, 95153                    # (95151 + the count word g_numSelectedTeams)
IDA_CFB = 0xC958C                           # careerFileBuffer's IDA dseg address (ref/swos.asm)
NUMSEL_AT, SELPTR_AT, CT_AT = 0xE093B - IDA_CFB, 0xE0928 - IDA_CFB, 0xD710C - IDA_CFB   # 0x173AF, 0x1739C, 0xDB80
assert (NUMSEL_AT, SELPTR_AT, CT_AT) == (0x173AF, 0x1739C, 0xDB80) and NUMSEL_AT + 2 == FIXED
SLT_AT = 0xD7E68 - IDA_CFB                  # someLeaguesTable
WORLD_AT, TAG_GLOBAL = SLT_AT + 1845, 1842  # careerworld.WORLD_BYTE (+1 = balance), strmap.TAG_GLOBAL
TMD_AT, TMD_N = 2, 80                       # tmdFileBuffer: the 80-record area (a big world's W1 block lives there)
BIGC_AT, BIGC, WMARK = TMD_AT + TMD_N * TEAM - 4, 0x43474942, 0x3157
OLD_CAP, SEL_CAP, B_SEL = 100, 160, 0x5C000                # careerworld: the game's cache, the big one (obj2 tail + B_SEL)
OLD_ROOM, SEL_ROOM = OLD_CAP * TEAM, SEL_CAP * TEAM + 0x4000 + 0x280    # trailer.SELECTED_ROOM, careerworld.SEL_ROOM
CAL_AT, CAL_END = 0xDB3E6 - IDA_CFB, 0xDF4F4 - IDA_CFB      # the career calendar (wsites.CAL)
CT_OLD = CT_AT - FIXED                      # careerTeam - g_selectedTeams = -0x9831
# careerFileBuffer's page offset per language (obj2 is page aligned; its obj2 offset: IT 0x96D6, EN 0x958C, FR 0x9266,
# DE 0x9086 - the same in the original and in every mod build; test_tc_saves recomputes them from orig/)
CFB_PAGES = {0x6D6: 'it', 0x58C: 'en', 0x266: 'fr', 0x086: 'de'}
LOADER_RANGE = (0xF77E, 0x16ABC)            # w_loadcopy's exact-value rewrite
# the 5 buffers: (name, fixed-part offset, room) = wsites.DIY_SLOTS (test_tc_saves asserts the equality)
SLOTS = [('competitionFileBuffer', 0xDF4F6 - IDA_CFB, 0xB52), ('slot1 D8D0A', 0xD8D0A - IDA_CFB, 0xB52),
         ('slot2 D985C', 0xD985C - IDA_CFB, 0x443), ('slot3 DA0E2', 0xDA0E2 - IDA_CFB, 0xB52),
         ('slot4 D9C9F', 0xD9C9F - IDA_CFB, 0x443)]
SWE_CODE = 0x1800                           # swe.c's code band in obj4 (swreg.REG_AT follows it)
DL_N, DL_MAX, DL_STAGE = 49, 64, 0x41F      # sreg_walk.c
DL_SIZE = (0x733, 0x443, 0xB52)
DL_OFFS = ((691, 18), (0x343, 4))           # the offset arrays: (first, stride) for a league / a cup
DL_ORDER = 717                              # a cup's order bytes (cseg_27436: offs[order[k]] = record of list[order[k]], k < numTeams)
WORLD_NAMES = {0: '1996-97', 4: 'Europe 1984-85 (4)', 5: 'World 2026-27 (5)'}
MAIN_MARKS = {0x3743: 'C7', 0x3643: 'C6', 0x3543: 'C5', 0x3443: 'C4', 0x3343: 'C3', 0x3243: 'C2', 0x3143: 'C1'}


def u16(b, o):
    return b[o] | b[o + 1] << 8


def s32(b, o):
    return struct.unpack_from('<i', b, o)[0]


def walk_slot(b, off, room):
    """The declared offset dwords of one buffer: (positions [(file offset, i, 'league' / 'cup')], state).
    state: 'league' / 'cup' / 'type2+league' / 'type2+cup' or 'refused: why' (then no position is declared)."""
    names, c = [], off
    for lvl in range(2):
        t, n = u16(b, c), u16(b, c + DL_N)
        if t > 2 - lvl:
            return [], f'refused: type {t}' + (' in a stage' if lvl else '')
        if n > DL_MAX:
            return [], f'refused: numTeams {n}'
        if DL_SIZE[t] > room:               # a league whose n rows fit a cup-sized slot is walked and named (the WS_D
            if t or not n or DL_OFFS[0][0] + DL_OFFS[0][1] * n > room:     # walker refuses it; seen: the national-team
                return [], f'refused: type {t} needs {DL_SIZE[t]:#x} > room {room:#x}'     # career's friendlies in slot 2)
            return [(c + 691 + 18 * i, i, 'league') for i in range(n)], '+'.join(names + ['league in a cup-sized slot'])
        names.append(('league', 'cup', 'type2')[t])
        if t == 2:
            c, room = c + DL_STAGE, DL_SIZE[2] - DL_STAGE
            continue
        first, stride = DL_OFFS[t]
        idx = list(range(n))
        if t == 1:                          # a cup: entry = the club's index in the list, through the order bytes
            idx = sorted(set(b[c + DL_ORDER:c + DL_ORDER + n]))
            if idx and idx[-1] >= DL_MAX:
                return [], f'refused: cup order byte {idx[-1]}'
        return [(c + first + stride * i, i, names[-1]) for i in idx], '+'.join(names)
    return [], 'refused: a type 2 inside a type 2'


def split_trailer(b, n):
    """Regions after the fixed part: [(name, start, end)] - records, the main block, each EN item (or 'tail?')."""
    out, r0 = [], FIXED
    r1 = min(len(b), FIXED + n * TEAM)
    out.append(('records', r0, r1))
    tail = b[r1:]
    if not tail:
        return out
    k = -1
    while True:                             # the engine block is the file's last block: 'EN', word length, items
        k = tail.find(b'EN', k + 1)
        if k < 0 or (k + 4 <= len(tail) and k + 4 + u16(tail, k + 2) == len(tail)):
            break
        if k + 4 > len(tail):
            k = -1
            break
    main_end = len(tail) if k < 0 else k
    mark = MAIN_MARKS.get(u16(tail, 0)) if len(tail) >= 2 else None
    out.append((f"main block {mark or '?'}", r1, r1 + main_end))
    if k >= 0:
        o, end = k + 4, len(tail)
        while o + 4 <= end:
            iid, ln = tail[o:o + 2], u16(tail, o + 2)
            if o + 4 + ln > end:
                out.append(('EN tail?', r1 + o, r1 + end))
                break
            out.append((f"EN item {iid.decode('latin-1')!r}", r1 + o, r1 + o + 4 + ln))
            o += 4 + ln
    return out


def region_of(o, regions):
    if o < FIXED:
        for name, off, room in SLOTS:
            if off <= o < off + room + (1 if name == 'competitionFileBuffer' else 0):
                return f'fixed: {name} +{o - off:#x}'
        if TMD_AT <= o < TMD_AT + TMD_N * TEAM:
            return f'fixed: tmd / W1 area +{o - TMD_AT:#x}'
        return 'fixed'
    for name, a, e in regions:
        if a <= o < e:
            return f'{name} +{o - a:#x}'
    return 'past the end'


def ctx(b, o):
    a = max(0, o - 8)
    return b[a:o].hex() + '[' + b[o:o + 4].hex() + ']' + b[o + 4:o + 12].hex()


def find_range(b, lo, hi):
    """Every offset whose LE dword is in [lo, hi) - by the dword's two high bytes (bytes.find), then the test."""
    out = []
    for h in range(lo >> 16, ((hi - 1) >> 16) + 1):
        pat, k = struct.pack('<H', h & 0xFFFF), 1
        while True:
            k = b.find(pat, k + 1)
            if k < 0:
                break
            if k >= 2:
                v = struct.unpack_from('<I', b, k - 2)[0]
                if lo <= v < hi:
                    out.append(k - 2)
    return sorted(set(out))


def cal_slots(b):
    """The slots named by the career calendar's entries (byte 0 = slot, byte 1 = week, word +2 = the entry's size). The
    list is in week order (cseg_8C516 inserts before the first later week) and has no end mark of its own: it ends at a
    size 0 or where the week goes back (what follows is an earlier, longer calendar's tail)."""
    out, o, week = set(), CAL_AT, 0
    while o + 4 <= CAL_END:
        sz = u16(b, o + 2)
        if sz < 4 or b[o + 1] < week:
            break
        out.add(b[o])
        week = b[o + 1]
        o += sz
    return out


def array_places(off, room):
    """Every offset of a buffer that is an offset-array entry under some layout (league / cup, direct or as a stage)."""
    out = set()
    for base in (off, off + DL_STAGE):
        for t in (0, 1):
            first, stride = DL_OFFS[t]
            out.update(o for o in (base + first + stride * i for i in range(DL_MAX)) if o + 4 <= off + room + 1)
    return out


def place_key(o, regions):
    """Where a hit is, in a form that is the same place in another save: the fixed part's offset, the offset inside a
    given record, inside the main block or inside an EN item."""
    if o < FIXED:
        return f'fixed +{o:#x}'
    for name, a, e in regions:
        if a <= o < e:
            return f'record {(o - a) // TEAM} +{(o - a) % TEAM:#x}' if name == 'records' else f'{name} +{o - a:#x}'
    return 'past the end'


def classify(v, n, sel, ct, cfb):
    if v >= 0 and v % TEAM == 0 and v < n * TEAM:
        return 'record'
    if v == ct:
        return 'careerTeam'
    if v >= 0 and v % TEAM == 0 and v < SEL_CAP * TEAM:
        return 'stale-rec'
    if cfb is not None and 0 <= sel + v - cfb < FIXED:
        d = sel + v - cfb - TMD_AT
        return 'fixed' + (' (tmd record)' if d % TEAM == 0 and 0 <= d < TMD_N * TEAM else '')
    if -B_SEL <= v < -B_SEL + 128 * TEAM and (v + B_SEL) % TEAM == 0:
        return 'big-tmd'
    if 0 <= v < SEL_ROOM:
        return 'in-cache'
    return 'far'


def audit(b):
    """One save -> dict (JSON-able). None if the bytes are not a career save (too short for the fixed part)."""
    if len(b) < FIXED:
        return None
    n = u16(b, NUMSEL_AT)
    sel = struct.unpack_from('<I', b, SELPTR_AT)[0]
    world = b[WORLD_AT] if (b[WORLD_AT] + b[WORLD_AT + 1]) & 0xFF == 0 else -1     # (-1: no balanced world byte)
    r = {'n': n, 'sel': sel, 'world': world, 'size': len(b), 'bigc': struct.unpack_from('<I', b, BIGC_AT)[0] == BIGC,
         'w1': u16(b, TMD_AT) == WMARK, 'tag': b[SLT_AT + TAG_GLOBAL], 'short': len(b) < FIXED + n * TEAM,
         'slots': [], 'counts': {}, 'other': [], 'strays': [], 'stale': [], 'notes': []}
    regions = split_trailer(b, n)
    r['trailer'] = [name.split(' +')[0] for name, a, e in regions[1:]]
    live = cal_slots(b) | {0}
    declared, places = {}, set()
    for k, (name, off, room) in enumerate(SLOTS):
        pos, state = walk_slot(b, off, room)
        title = bytes(c for c in b[off + 4:off + 39].split(b'\0')[0] if 32 <= c < 127).decode()
        r['slots'].append({'state': state, 'live': k in live, 'title': title})
        places |= array_places(off, room)
        for o, i, kind in pos:
            declared[o] = (k, i, kind)
    # careerTeam's offset in this save
    vals = {o: s32(b, o) for o in declared}
    nonrec = sorted({v for v in vals.values() if not (v >= 0 and v % TEAM == 0)})
    gpage = (sel - FIXED) & 0xFFF in CFB_PAGES                  # selTeamsPtr has g_selectedTeams' page offset (some language)
    ct = None
    cand = [v for v in nonrec if -0x200000 < v < 0 and (v + sel - CT_AT) & 0xFFF in CFB_PAGES]
    if CT_OLD in nonrec or (gpage and not r['bigc'] and not cand):
        ct, r['form'] = CT_OLD, 'game cache'
        if not gpage:
            r['notes'].append(f'selTeamsPtr {sel:#x}: not g_selectedTeams page offset')
    else:
        r['form'] = 'big cache'
        if len(cand) == 1:
            ct = cand[0]
        elif cand:
            r['notes'].append('several careerTeam candidates: ' + ', '.join(f'{v:#x}' for v in cand))
    if ct is None or ct not in nonrec:
        r['notes'].append('no declared dword is careerTeam')
    r['ct'] = ct
    cfb = sel + ct - CT_AT if ct is not None else None          # careerFileBuffer's address in the exe that saved
    r['lang'] = CFB_PAGES.get(cfb & 0xFFF, '?') if cfb is not None else '?'
    cap = OLD_CAP if r['form'] == 'game cache' else SEL_CAP
    room = OLD_ROOM if r['form'] == 'game cache' else SEL_ROOM
    for o, v in sorted(vals.items()):
        k, i, kind = declared[o]
        cls = classify(v, n, sel, ct, cfb)
        key = ('live ' if k in live else 'idle ') + cls
        r['counts'][key] = r['counts'].get(key, 0) + 1
        if cls not in ('record', 'careerTeam'):
            r['other'].append({'at': o, 'value': v, 'slot': k, 'entry': i, 'kind': kind, 'sub': cls, 'live': k in live, 'ctx': ctx(b, o)})
    # strays (a): absolute addresses into the cache
    if sel >= 0x10000 + room:
        hits = find_range(b, sel, sel + room)
        r['abs_in_range'] = len([o for o in hits if o != SELPTR_AT])
        r['abs_control'] = len(find_range(b, sel - room, sel)) + len(find_range(b, sel + room, sel + 2 * room))
        for o in hits:
            v = struct.unpack_from('<I', b, o)[0]
            if o != SELPTR_AT and (v - sel) % TEAM == 0 and (v - sel) // TEAM < cap:
                k = (v - sel) // TEAM
                r['strays'].append({'at': o, 'value': v, 'kind': f'absolute address of record {k}' + (' (past N)' if k >= n else ''),
                                    'where': region_of(o, regions), 'ctx': ctx(b, o), 'key': place_key(o, regions)})
    else:
        r['abs_in_range'] = r['abs_control'] = 0
        r['notes'].append(f'selTeamsPtr {sel:#x}: no absolute scan')
    # strays (b): careerTeam's offset outside the declared positions
    if ct is not None:
        pat, k = struct.pack('<i', ct), -1
        while True:
            k = b.find(pat, k + 1)
            if k < 0:
                break
            if k in declared:
                continue
            h = {'at': k, 'value': ct, 'kind': "careerTeam's offset", 'where': region_of(k, regions), 'ctx': ctx(b, k),
                 'loader_range': LOADER_RANGE[0] <= k < LOADER_RANGE[1]}
            (r['stale'] if k in places else r['strays']).append(h)
    return r


# ---- the archive -------------------------------------------------------------------------------------------------

def is_car(name):
    return name.lower().endswith('.car')


def is_tar(path):
    return path.lower().endswith(('.tar', '.tar.gz', '.tgz', '.tar.xz', '.tar.bz2'))


def scan_tar(path):
    """[(member path, sha1 or None, bytes or the error text)] of one tar, read in place (headers + the .CAR members)."""
    out = []
    try:
        with tarfile.open(path, 'r:*') as tf:
            for m in tf:
                if m.isfile() and is_car(m.name) and m.size >= FIXED:
                    b = tf.extractfile(m).read()
                    out.append((path + '!' + m.name, hashlib.sha1(b).hexdigest(), b))
    except Exception as e:                  # (a truncated archive: what was read counts, the error is reported)
        out.append((path, None, f'{type(e).__name__}: {e}'))
    return out


def tar_job(args):
    """(worker) one tar -> [(member, sha1, bytes if new else None)]: bytes cross the pipe only for unseen saves."""
    path, store = args
    out = []
    for p, h, b in scan_tar(path):
        if h and store:
            f = os.path.join(store, h[:2], h + '.z')
            if not os.path.exists(f):
                os.makedirs(os.path.dirname(f), exist_ok=True)
                tmp = f + f'.{os.getpid()}.tmp'
                open(tmp, 'wb').write(zlib.compress(b, 1))
                os.replace(tmp, f)
            b = None
        out.append((p, h, b))
    return out


def sources(paths):
    """-> (loose .CAR files, tars) under the given paths."""
    files, tars = [], []
    for p in paths:
        if os.path.isfile(p):
            (tars if is_tar(p) else files).append(p)
            continue
        for d, dirs, names in os.walk(p):
            dirs.sort()
            for f in sorted(names):
                if f.startswith('._'):      # (AppleDouble side files of a non-HFS disk: not archives, not saves)
                    continue
                if is_car(f):
                    files.append(os.path.join(d, f))
                elif is_tar(f):
                    tars.append(os.path.join(d, f))
    return files, tars


def run(paths, store=None, jobs=1, log=None):
    """-> {'saves': {sha1: audit result + 'paths': first 3, 'copies': k}, 'errors', 'notcar', 'files', 'tars'}.
    store: a directory for zlib copies of the distinct saves + index.json (tar -> its members' sha1s), so that a later
    run re-reads no archive; without it every archive is read again and the saves are kept in memory."""
    log = log or (lambda s: None)
    index, mem = {}, {}
    ipath = os.path.join(store, 'index.json') if store else None
    if ipath and os.path.exists(ipath):
        index = json.load(open(ipath))
    seen, errors, notcar = {}, [], 0
    files, tars = sources(paths)
    log(f'{len(files)} loose .CAR files, {len(tars)} tar archives')

    def keep(h, b):
        if not store:
            mem[h] = b
            return
        f = os.path.join(store, h[:2], h + '.z')
        if not os.path.exists(f):
            os.makedirs(os.path.dirname(f), exist_ok=True)
            open(f + '.tmp', 'wb').write(zlib.compress(b, 1))
            os.replace(f + '.tmp', f)

    def flush():
        if ipath:
            json.dump(index, open(ipath + '.tmp', 'w'))
            os.replace(ipath + '.tmp', ipath)

    for f in files:
        try:
            st = os.stat(f)
            key = f'{f}|{st.st_size}|{int(st.st_mtime)}'
            if st.st_size < FIXED:
                notcar += 1
                continue
            h = index.get(key)
            if h is None:
                b = open(f, 'rb').read()
                h = hashlib.sha1(b).hexdigest()
                keep(h, b)
                if store:
                    index[key] = h
        except OSError as e:
            errors.append(f'{f}: {e}')
            continue
        seen.setdefault(h, []).append(f)
    todo = []
    for t in tars:
        st = os.stat(t)
        key = f'{t}|{st.st_size}|{int(st.st_mtime)}'
        if key in index:
            for p, h in index[key]['members']:
                seen.setdefault(h, []).append(p)
            errors += index[key]['errors']
        else:
            todo.append((t, key))

    def take(key, res):
        members, errs = [], []
        for p, h, b in res:
            if h is None:
                errs.append(f'{p}: {b}')
                continue
            if b is not None:
                keep(h, b)
            members.append((p, h))
            seen.setdefault(h, []).append(p)
        if store:
            index[key] = {'members': members, 'errors': errs}
        errors.extend(errs)

    if todo:
        import concurrent.futures as cf
        with (cf.ProcessPoolExecutor(jobs) if jobs > 1 else cf.ThreadPoolExecutor(1)) as ex:
            fut = {ex.submit(tar_job, (t, store)): key for t, key in todo}
            for k, f in enumerate(cf.as_completed(fut)):
                take(fut[f], f.result())
                if k % 25 == 24:
                    flush()
                    log(f'tars {k + 1}/{len(todo)}, {len(seen)} distinct saves')
    flush()
    saves = {}
    for h, p in seen.items():
        b = mem[h] if not store else zlib.decompress(open(os.path.join(store, h[:2], h + '.z'), 'rb').read())
        saves[h] = dict(audit(b), paths=p[:3], copies=len(p))
    return {'saves': saves, 'errors': errors, 'notcar': notcar, 'files': len(files), 'tars': len(tars)}


# ---- leg 1 (static): the fixups of a built exe that point into a team cache ------------------------------------------

def exe_layout(le):
    """A built (or original) exe -> {'selptr', 'old', 'd0', 'numsel', 'selbasev', 'new', 'fx'}: obj2 offsets of selTeamsPtr /
    g_selectedTeams (OLDSEL) / D0 / g_numSelectedTeams, the obj1 offset of trailer's SELBASEV (None: the original game) and
    the obj2 offset of the big cache NEWSEL (None: a build without it); fx = {(src obj, src off): (target obj, target off)}."""
    fx = {(f[0], f[1]): (f[3], f[4]) for f in le.fixups() if f[4] is not None}
    c = [(so, to) for (sobj, so), (tobj, to) in fx.items() if sobj == 2 and tobj == 2 and to - so == FIXED - SELPTR_AT]
    assert len(c) == 1, ('selTeamsPtr dd offset g_selectedTeams: one data fixup expected', c)
    selptr, old = c[0]
    d1 = le.obj_bytes(1)
    L = {'selptr': selptr, 'old': old, 'd0': old + OLD_ROOM, 'numsel': old - 2, 'selbasev': None, 'new': None, 'fx': fx, 'd1': d1}
    # w_setbase / w_switch: mov dword [SELBASEV], X; mov dword [ROOMV], room
    for imm, key in ((OLD_ROOM, 'old'), (SEL_ROOM, 'new')):
        k, found = -1, set()
        pat = struct.pack('<I', imm)
        while True:
            k = d1.find(pat, k + 1)
            if k < 0:
                break
            a = k - 16                          # C7 05 m32 imm32 C7 05 m32 [imm32 at k]
            if a >= 0 and d1[a:a + 2] == b'\xc7\x05' and d1[a + 10:a + 12] == b'\xc7\x05' and (1, a + 6) in fx \
                    and fx.get((1, a + 2), (0, 0))[0] == 1 and fx[1, a + 6][0] == 2:
                found.add((fx[1, a + 2][1], fx[1, a + 6][1]))
        if key == 'old' and found:
            assert {t for _, t in found} == {old}, ('mov [SELBASEV], OLDSEL', found)
            assert len({s for s, _ in found}) == 1, found
            L['selbasev'] = found.pop()[0]
        elif key == 'new' and found:
            assert len(found) == 1 and {s for s, _ in found} == {L['selbasev']}, ('mov [SELBASEV], NEWSEL', found)
            L['new'] = found.pop()[1]
    return L


def fixup_kind(le, L, sobj, soff, toff, obytes):
    """The whitelist (design 1.8 leg 1): the name of the allowed use of a fixup into a cache, or None (a violation).
    obytes = the source object's bytes."""
    fx, old, new = L['fx'], L['old'], L['new']
    pre = obytes[max(0, soff - 12):soff]
    ptr = lambda k: fx.get((sobj, soff - k)) in ((2, L['selptr']), (1, L['selbasev']) if L['selbasev'] is not None else None)
    which = 'OLDSEL' if old <= toff < old + OLD_ROOM else 'NEWSEL'
    if toff in (old, new) and sobj == 1:        # the constants of careerworld's stubs (and the game's ProcessCareerFile)
        if pre[-6:-4] == b'\xc7\x05' and ptr(4):
            return f'mov dword [selTeamsPtr / SELBASEV], {which}'
        if pre[-6:-4] == b'\x81\x3d' and ptr(4):
            return f'cmp dword [selTeamsPtr / SELBASEV], {which}'
        if pre[-1:] == b'\x3d':
            return f'cmp eax, {which}'
        if pre[-1:] in (b'\xbe', b'\xbf') and which == 'NEWSEL':
            return 'mov esi / edi, NEWSEL (the save from the stage: records + trailer)'
    if toff == old:
        if (sobj, soff) == (2, L['selptr']):
            return "selTeamsPtr's initial value"
        if (sobj, soff) == (1, L['selbasev']):
            return "SELBASEV's default (trailer.py: dd SELBUF)"
        if struct.pack('<i', -FIXED) in pre:
            return 'end of the fixed part: an index running from -95153 (ctgame.c cg hash of careerFileBuffer)'
    if sobj == 4 and soff < SWE_CODE and old <= toff <= old + 4:
        return "swe.c's DIY code (diy_size / the 'WM' block after the DIY file's records)"
    return None


def exe_fixups(path):
    """-> (layout, [(src obj, src off, 'OLD' / 'NEW', offset in the cache, kind or None, context hex)]) for one exe."""
    from le import LE
    le = LE(path)
    L = exe_layout(le)
    ob, out = {}, []
    for (sobj, soff), (tobj, toff) in sorted(L['fx'].items()):
        if tobj != 2:
            continue
        for name, base, room in (('OLD', L['old'], OLD_ROOM), ('NEW', L['new'], SEL_ROOM)):
            if base is not None and base <= toff < base + room:
                d = ob.setdefault(sobj, le.obj_bytes(sobj))
                out.append((sobj, soff, name, toff - base, fixup_kind(le, L, sobj, soff, toff, d),
                            d[max(0, soff - 8):soff].hex() + '[' + d[soff:soff + 4].hex() + ']' + d[soff + 4:soff + 10].hex()))
    return L, out


def insert_sites(L):
    """The game's insert sites in obj1: `add word [g_numSelectedTeams], 1` (66 83 05 addr 01) -> [(obj1 offset, distance
    to its copy-count `mov word [D0], 341` (66 C7 05 D0 55 01): negative = before, None = not within 0x60 B)]."""
    d1, fx, out = L['d1'], L['fx'], []
    k = -1
    while True:
        k = d1.find(b'\x66\x83\x05', k + 1)
        if k < 0:
            break
        if fx.get((1, k + 3)) != (2, L['numsel']) or d1[k + 7] != 1:
            continue
        dist = None
        for j in list(range(k - 9, k - 0x61, -1)) + list(range(k + 8, k + 0x60)):
            if d1[j:j + 3] == b'\x66\xc7\x05' and fx.get((1, j + 3)) == (2, L['d0']) and d1[j + 7:j + 9] == b'\x55\x01':
                dist = j - k
                break
        out.append((k, dist))
    return out


# ---- the report --------------------------------------------------------------------------------------------------

def wname(w):
    return WORLD_NAMES.get(w, 'no world byte' if w < 0 else f'world {w}')


CLASSES = ('record', 'careerTeam', 'stale-rec', 'fixed', 'fixed (tmd record)', 'big-tmd', 'in-cache', 'far')
DEPENDENT = ('fixed', 'fixed (tmd record)', 'big-tmd')      # OTHER sub-kinds that would depend on the cache's address


def stray_places(res):
    """The absolute-address hits by place: {key: {'hits', 'sels': {selTeamsPtr: hits}, 'ks', 'pop': saves that have those
    selTeamsPtr values, 'stray': the verdict (it follows the cache), 'ex': (sha1, hit)}}"""
    out, pop = {}, {}
    for h, r in res['saves'].items():
        pop[r['sel']] = pop.get(r['sel'], 0) + 1
        for x in r['strays']:
            if 'key' in x:
                e = out.setdefault(x['key'], {'hits': 0, 'sels': {}, 'ks': set(), 'ex': (h, x)})
                e['hits'] += 1
                e['sels'][r['sel']] = e['sels'].get(r['sel'], 0) + 1
                e['ks'].add((x['value'] - r['sel']) // TEAM)
    for e in out.values():
        e['pop'] = sum(pop[s] for s in e['sels'])
        e['stray'] = len(e['sels']) >= 3 or (len(e['sels']) == 2 and 2 * e['hits'] >= e['pop'])
    return out


def totals(res):
    """Per (world, form): saves, declared dwords by class (live / idle), OTHER, strays, stale."""
    t = {}
    places = stray_places(res)
    for h, r in res['saves'].items():
        d = t.setdefault((r['world'], r['form']), {'saves': 0, 'strays': 0, 'stale': 0, 'maxn': 0, 'short': 0, 'other': 0,
                                                    'other_idle': 0, 'dependent': 0, 'abs': 0, 'ctl': 0, 'coinc': 0, 'counts': {}})
        d['saves'] += 1
        for k, v in r['counts'].items():
            d['counts'][k] = d['counts'].get(k, 0) + v
            lv, cls = k.split(' ', 1)
            if cls not in ('record', 'careerTeam'):
                d['other' if lv == 'live' else 'other_idle'] += v
                d['dependent'] += v if cls in DEPENDENT else 0
        real = [x for x in r['strays'] if 'key' not in x or places[x['key']]['stray']]
        d['strays'] += len(real)
        d['coinc'] += len(r['strays']) - len(real)
        d['stale'] += len(r['stale'])
        d['short'] += r['short']
        d['abs'] += r['abs_in_range']
        d['ctl'] += r['abs_control']
        d['maxn'] = max(d['maxn'], r['n'])
    return t


def grand(res):
    t = totals(res)
    g = {k: sum(d[k] for d in t.values()) for k in ('saves', 'other', 'other_idle', 'dependent', 'strays', 'stale', 'short', 'abs', 'ctl', 'coinc')}
    g['counts'] = {}
    for d in t.values():
        for k, v in d['counts'].items():
            g['counts'][k] = g['counts'].get(k, 0) + v
    return g


def report(res, title='Team-cache audit, leg 2: real saves', tsv=None):
    sv, t, g, places = res['saves'], totals(res), grand(res), stray_places(res)
    c = g['counts']
    is_real = lambda x: 'key' not in x or places[x['key']]['stray']
    L = [f'# {title}', '', 'Tool: `tools/tcaudit.py` (its docstring = the rules). Design: teamcache-fable-design.md 1.8, leg 2.', '',
         f"Sources: {res['files']} loose .CAR files, {res['tars']} tar archives; {sum(r['copies'] for r in sv.values())} "
         f"saves read, **{len(sv)} distinct** (sha1); {res['notcar']} .CAR shorter than the fixed part skipped; "
         f"{len(res['errors'])} read errors.", '',
         f"**Result: OTHER = {g['other']} in live buffers (+ {g['other_idle']} in idle buffers), of which "
         f"cache-address dependent (fixed / tmd / big-tmd) = {g['dependent']}; strays = {g['strays']}** "
         f"(+ {g['coinc']} address coincidences at {sum(1 for e in places.values() if not e['stray'])} places, below).", '',
         f"- declared dwords, live buffers: record {c.get('live record', 0)}, careerTeam {c.get('live careerTeam', 0)}, "
         + ', '.join(f"{k} {c.get('live ' + k, 0)}" for k in CLASSES[2:]),
         f"- declared dwords, idle buffers: record {c.get('idle record', 0)}, careerTeam {c.get('idle careerTeam', 0)}, "
         + ', '.join(f"{k} {c.get('idle ' + k, 0)}" for k in CLASSES[2:]),
         f"- stale careerTeam offsets inside the buffers (other layouts' array places): {g['stale']}",
         f"- dwords inside the cache's address range that are not a record's address (not listed): {g['abs']}; the same "
         f"count in the two neighbouring ranges: {g['ctl']} (/ 2 = {g['ctl'] / 2:.0f} per range)",
         f"- files shorter than fixed + N x 684: {g['short']}", '',
         '## Totals per world and cache form', '',
         '| world | cache at save | saves | max N | record | careerTeam | OTHER live | of which stale-rec | OTHER idle | dependent | strays | coincidences | stale CT |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for (w, form), d in sorted(t.items()):
        k = d['counts']
        L.append(f"| {wname(w)} | {form} | {d['saves']} | {d['maxn']} | {k.get('live record', 0) + k.get('idle record', 0)} | "
                 f"{k.get('live careerTeam', 0) + k.get('idle careerTeam', 0)} | {d['other']} | {k.get('live stale-rec', 0)} | "
                 f"{d['other_idle']} | {d['dependent']} | {d['strays']} | {d['coinc']} | {d['stale']} |")
    L.append(f"| **all** | | **{g['saves']}** | | {c.get('live record', 0) + c.get('idle record', 0)} | "
             f"{c.get('live careerTeam', 0) + c.get('idle careerTeam', 0)} | **{g['other']}** | {c.get('live stale-rec', 0)} | "
             f"{g['other_idle']} | **{g['dependent']}** | **{g['strays']}** | {g['coinc']} | {g['stale']} |")
    st = {}
    for r in sv.values():
        for (name, off, room), s in zip(SLOTS, r['slots']):
            k = ('live ' if s['live'] else 'idle ') + s['state'].split(' needs')[0].split(' numTeams')[0]
            st.setdefault(name, {})[k] = st.setdefault(name, {}).get(k, 0) + 1
    L += ['', '## Buffer states (distinct saves)', '', '| buffer | state: saves |', '|---|---|']
    for name, off, room in SLOTS:
        L.append(f"| {name} (fixed + {off:#x}) | " + ', '.join(f'{k}: {v}' for k, v in sorted(st.get(name, {}).items())) + ' |')
    tr = {}
    for r in sv.values():
        for x in r['trailer']:
            x = 'EN items' if x.startswith('EN item') else x
            tr[x] = tr.get(x, 0) + 1
    L += ['', '## Trailer blocks scanned', '', ', '.join(f'{k}: {v}' for k, v in sorted(tr.items())) or 'none',
          f"(saves with no trailer: {sum(1 for r in sv.values() if not r['trailer'])})", '']
    notes = {}
    for h, r in sv.items():
        for x in r['notes']:
            notes.setdefault(x.split(' 0x')[0].split(': ')[0], []).append(h)
    if notes:
        L += ['## Notes', '']
        for k, hs in sorted(notes.items()):
            L.append(f"- {k}: {len(hs)} saves (e.g. {sv[hs[0]]['paths'][0]})")
        L.append('')
    # OTHER, grouped
    grp = {}
    for h, r in sv.items():
        for x in r['other']:
            s = r['slots'][x['slot']]
            k = (wname(r['world']), SLOTS[x['slot']][0], s['title'], s['state'], 'live' if x['live'] else 'idle', x['sub'])
            e = grp.setdefault(k, [0, set(), None])
            e[0] += 1
            e[1].add(h)
            e[2] = e[2] or (h, r, x)
    L += [f"## OTHER, grouped: {sum(e[0] for e in grp.values())} dwords in {len(grp)} groups", '',
          '| world | buffer | contest title | layout | slot | sub-kind | dwords | saves | example: save, N, selTeamsPtr, file offset, entry, value, context |',
          '|---|---|---|---|---|---|---|---|---|']
    order = sorted(grp.items(), key=lambda kv: (kv[0][5] not in DEPENDENT, kv[0][4] != 'live', kv[0][5] == 'stale-rec', -kv[1][0]))
    for k, (cnt, hs, (h, r, x)) in order[:300]:
        L.append('| ' + ' | '.join(k) + f" | {cnt} | {len(hs)} | {h[:10]} {r['paths'][0]}, N {r['n']}, {r['sel']:#x}, "
                 f"{x['at']:#x}, {x['kind']} entry {x['entry']}, {x['value']:#x} ({x['value']}), `{x['ctx']}` |")
    if len(order) > 300:
        L.append(f'| ... {len(order) - 300} more groups (all in the .tsv) | | | | | | | | |')
    L.append('')
    co = sorted(((k, e) for k, e in places.items() if not e['stray']), key=lambda ke: -ke[1]['hits'])
    L += [f"## Address coincidences: {sum(e['hits'] for _, e in co)} hits at {len(co)} places", '',
          'A dword that reads as selTeamsPtr + 684 k, at a place that does not follow the cache (docstring 2a).', '']
    if co:
        L += ['| place | hits | under selTeamsPtr = (hits) | saves that have those values | record k | example: save, context |',
              '|---|---|---|---|---|---|']
        for k, e in co:
            h, x = e['ex']
            L.append(f"| {k} | {e['hits']} | " + ', '.join(f'{a:#x} ({n})' for a, n in sorted(e['sels'].items())) + f" | {e['pop']} | "
                     + ', '.join(map(str, sorted(e['ks']))) + f" | {h[:10]} {sv[h]['paths'][0]}, N {sv[h]['n']}, `{x['ctx']}` |")
        L.append('')
    for key, head in (('strays', 'Strays'), ('stale', 'Stale careerTeam offsets inside the buffers')):
        hits = [(h, r, x) for h, r in sorted(sv.items(), key=lambda kv: kv[1]['paths'][0]) for x in r[key]
                if key != 'strays' or is_real(x)]
        L += [f'## {head}: {len(hits)}', '']
        if not hits:
            L += ['None.', '']
            continue
        if key == 'stale':
            by = {}
            for h, r, x in hits:
                k = (wname(r['world']), x['where'].split(' +')[0], x['loader_range'])
                e = by.setdefault(k, [0, set(), (h, r, x)])
                e[0] += 1
                e[1].add(h)
            L += ['| world | where | in the loader range | dwords | saves | example |', '|---|---|---|---|---|---|']
            for k, (cnt, hs, (h, r, x)) in sorted(by.items()):
                L.append(f"| {k[0]} | {k[1]} | {'yes' if k[2] else 'NO'} | {cnt} | {len(hs)} | {h[:10]} {r['paths'][0]}, {x['where']}, `{x['ctx']}` |")
            L.append('')
            continue
        L += ['| save (sha1, first path, copies) | world | N | selTeamsPtr | file offset | value | what / where | context (8 B before [dword] 8 B after) |',
              '|---|---|---|---|---|---|---|---|']
        for h, r, x in hits[:300]:
            v = x['value']
            L.append(f"| {h[:10]} {r['paths'][0]} x{r['copies']} | {wname(r['world'])} | {r['n']} | {r['sel']:#x} | {x['at']:#x} | "
                     f"{v:#x} | {x['kind']}; {x['where']}" + ('' if x.get('loader_range', True) else '; OUTSIDE the loader range')
                     + f" | `{x['ctx']}` |")
        if len(hits) > 300:
            L.append(f'| ... {len(hits) - 300} more (all in the .tsv) | | | | | | | |')
        L.append('')
    if res['errors']:
        L += ['## Read errors', ''] + [f'- {e}' for e in res['errors'][:100]] + ['']
    if tsv:
        with open(tsv, 'w') as f:
            f.write('class\tsha1\tpath\tworld\tform\tN\tselTeamsPtr\toffset\tvalue\twhat\tcontext\n')
            for h, r in sorted(sv.items(), key=lambda kv: kv[1]['paths'][0]):
                for key in ('other', 'strays', 'stale'):
                    for x in r[key]:
                        what = (f"{SLOTS[x['slot']][0]} [{r['slots'][x['slot']]['title']}] {r['slots'][x['slot']]['state']} "
                                f"{'live' if x['live'] else 'idle'} {x['kind']} entry {x['entry']}: {x['sub']}") if key == 'other' \
                            else f"{x['kind']}; {x['where']}"
                        f.write(f"{'coincidence' if key == 'strays' and not is_real(x) else key}\t{h}\t{r['paths'][0]}\t{wname(r['world'])}\t{r['form']}\t{r['n']}\t{r['sel']:#x}\t"
                                f"{x['at']:#x}\t{x['value']}\t{what}\t{x['ctx']}\n")
    return '\n'.join(L)


def main(argv):
    def opt(name, default=None):
        if name in argv:
            i = argv.index(name)
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
        return default
    rep, store, jobs = opt('--report'), opt('--store'), int(opt('--jobs', '1'))
    if not argv:
        print(__doc__)
        return 2
    if store:
        os.makedirs(store, exist_ok=True)
    res = run(argv, store, jobs, log=lambda s: print(s, file=sys.stderr, flush=True))
    if rep:
        os.makedirs(os.path.dirname(os.path.abspath(rep)), exist_ok=True)
        open(rep, 'w').write(report(res, tsv=os.path.splitext(rep)[0] + '.tsv') + '\n')
    for (w, form), d in sorted(totals(res).items()):
        print(f"{wname(w):14} {form:10} saves {d['saves']:5}  maxN {d['maxn']:3}  OTHER live {d['other']} idle {d['other_idle']} "
              f"dependent {d['dependent']}  strays {d['strays']}  coincidences {d['coinc']}  stale CT {d['stale']}")
    g = grand(res)
    print(f"tcaudit: {len(res['saves'])} distinct saves, OTHER {g['other']} (+ {g['other_idle']} idle; dependent {g['dependent']}), "
          f"strays {g['strays']}" + (f' -> {rep}' if rep else ''))
    return 1 if g['other'] or g['strays'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
