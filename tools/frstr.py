"""4.2 preseason friendlies, data part 1: the STRENGTH table (teamcache-fable-design.md 5.3) and DATA\\FRSS.DAT.

One strength value per club, for the opponent pick's bands (1 stronger / 2 similar / 1 weaker; tools/frpick.h). One
table format for every world (CONVENTIONS rule 0): the key is world byte + team file + ordinal, because team file
numbers repeat between worlds (file 101 = England in Europe 1984-85 and in World 2026-27). Built for every career
world of the build by the same function, table():
  world 0   1996-97: the countries of the exe's own continent tables (frturns.world0), files TEAM.nnn
  world N   a career world of the build's packs (pack.json "world" = the save's world byte, careerworld.WORLD_BYTE:
            4 = Europe 1984-85, 5 = World 2026-27): the team files of its career packs named by mkseason.ns_stem
            (TEAM.nnn for the base world, TMWn.nnn for the others).
THE FILE RULE (every world): league and state-championship club files only; cup-only, national, custom, guest,
pack / tourney and off-file pools excluded. In a career pack: the files of its league (Pack.league_roles) and the
files holding a club of a 'state' competition; never its off-file pool (RS*.DAT: no team word) and never a file whose
clubs play the national cup only (Europe 1984-85's 'cuponly' files 133..144: amateur / reserve sides, names that
repeat a league club's). Guests = guests.py 190..194 (no country, no league).

Strength = the mod's one club-strength rule, statespec.club_strength: the best 11 players' prices, at least 5 (the
rule of statesim / cupd.strength / gplay.c cd_str in World 2026-27). It is CALLED here, not copied: the rows are the
price bytes (PlayerFile +32, the players.csv 'price' column as mkseason writes it) of the record's 16 players.
Range 5 .. 539 (11 x 49), a word.

The table also carries each file's club count: the pick must refuse an ordinal >= count BEFORE any install
(cseg_32E15's file scan has no end test, ref/swos.asm 39437-39445); lookup() is that check's reference.

COUNTRY ID (v2, index byte +3): one id per country of a world, the same for every file of that country = the lowest
file number among the country's club files. World 0: a country is one file, id = file. A career pack with a second
club file shares its first file's id (World 2026-27: Brazil 161 + its state championships' 162 -> 161; a country
split over two league files would do the same; Europe 1984-85 has one file per country). An id means something inside its world's slice only.

COUNT 0 = 256 CLUBS: the index's count is a byte; a file with 256 clubs (the most a team word can address: World
2026-27's Italy, TMW5.102, ordinals 0..255) is written with count 0. A block never has 0 clubs, so 0 is read as 256
by parse() / lookup() / frpick.c (tools/frpick.h).

One world's table (FRSS v2, little-endian; the slice frpick.c reads, tools/frpick.h "THE TABLE"):
  +0 'FRSS'   +4 db version (2)   +5 db 0   +6 dw blocks
  index, sorted by (world, file): blocks x [db world, db file, db count, db country, dw first value's index]
  values: dw strength per club, in ordinal order (0 = no club in that record: never picked)
  (count 0 = 256 clubs; length = 8 + 6 x blocks + 2 x clubs. Version 1 = the same with index byte +3 = 0: refused by parse().)

DATA\\FRSS.DAT (FRSD v1, little-endian): every world's slice in one file. Motore reads the header + index, then only
the current world's slice (offset, length) at the season start; no file, or no entry for the world = no friendlies.
  +0 'FRSD'   +4 db version (1)   +5 db worlds   +6 dw 0
  index, sorted by world: worlds x [db world, db 0, dw 0, dd offset (from the file's start), dd length]   (12 B)
  slices: one complete FRSS v2 table per world (its blocks all carry that world byte), back to back in index order,
          the first right after the index (offset = 8 + 12 x worlds), the last one ends the file.
TEST VECTOR (the reader's reference; test_frss_test_vector builds it with pack() and compares it with these lines):
a 66-byte FRSS.DAT of two worlds - world 0 with file 20 (2 clubs, strengths 455 and 300), world 5 with file 102
(1 club, strength 462). Every byte, offsets decimal from the file's start:
  TV +00: 46 52 53 44 01 02 00 00              'FRSD', version 1, 2 worlds, dw 0
  TV +08: 00 00 00 00 20 00 00 00 12 00 00 00  index: world 0, db 0, dw 0, offset 32, length 18
  TV +20: 05 00 00 00 32 00 00 00 10 00 00 00  index: world 5, db 0, dw 0, offset 50, length 16
  TV +32: 46 52 53 53 02 00 01 00              world 0's slice: 'FRSS', version 2, db 0, 1 block
  TV +40: 00 14 02 14 00 00                    block: world 0, file 20, count 2, country 20, first value 0
  TV +46: C7 01 2C 01                          values: 455, 300 (ordinals 0, 1)
  TV +50: 46 52 53 53 02 00 01 00              world 5's slice: 'FRSS', version 2, db 0, 1 block
  TV +58: 05 66 01 66 00 00                    block: world 5, file 102, count 1, country 102, first value 0
  TV +64: CE 01                                value: 462 (ordinal 0)
A reader asked for world 5 takes bytes 50..65; asked for world 4 it finds no entry = no friendlies.

The build writes it beside each exe's DATA (patch.patch_exe -> gen()); a world whose team files are not all there (a
scenario's test build) is left out. buildrel.sh ASSERTS the release's file: `frstr.py check c/RELxx`.

    python3 tools/frstr.py [--exe EXE] [--data DIR] [--world N | --all] [--out DIR]
                                    (frstr_w<world>.bin / .txt; --all: every world + FRSS.DAT; worlds > 0 need the
                                     build's SEASON_PACKS, as buildrel.sh exports it)
    python3 tools/frstr.py build c/RELxx      (c/RELxx/SWOS/DATA/FRSS.DAT from its ENGLISH.EXE + DATA)
    python3 tools/frstr.py check c/RELxx      (FRSS OK / FRSS FAIL, exit code 1: the file is there, holds every world
                                               of the build, every word with a strength > 0 is a named record
                                               (file, ordinal) of the team files in the dir NOW - a word without
                                               one hangs the game, GetTeamPointer has no bound - and the file
                                               equals a fresh build from the DATA)
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'frdata')

MAGIC, VERSION = b'FRSS', 2
FILE_MAGIC, FILE_VERSION, FILE_NAME, FILE_ENTRY = b'FRSD', 1, 'FRSS.DAT', 12
GUEST_FILES = range(190, 195)           # guests.POOL + guests.FILES: no country, never in a table (asserted in world_files)
TEAM_SIZE, HEAD, PLAYER, PLAYERS, PRICE = 684, 76, 38, 16, 32       # TeamFile / PlayerFile (ref/swos.asm:309, :391)
NAME, NAME_LEN, DIVISION = 5, 17, 25


class _Rows:
    """statespec.club_strength's view of one team record: prows[key] = its players' {'price'} rows"""

    def __init__(self, rec):
        self.prows = {0: [{'price': rec[HEAD + PLAYER * j + PRICE]} for j in range(PLAYERS)]}


def club_strength(rec):
    """the strength of a 684-byte team record: statespec.club_strength on its price bytes"""
    import statespec
    assert len(rec) == TEAM_SIZE
    return statespec.club_strength(_Rows(rec), 0)


def records(path):
    """the 684-byte records of a team file (2-byte big-endian count first)"""
    d = open(path, 'rb').read()
    n = struct.unpack_from('>H', d, 0)[0]
    assert len(d) == 2 + TEAM_SIZE * n, f'{path}: {len(d)} B for {n} clubs'
    return [d[2 + TEAM_SIZE * i:2 + TEAM_SIZE * (i + 1)] for i in range(n)]


def name_of(rec):
    return rec[NAME:NAME + NAME_LEN].split(b'\0')[0].decode('latin1')


def table(world, files):
    """{(world, file): [(strength, name, division)] by ordinal} for files = {file number: path}"""
    out = {}
    for fl in sorted(files):
        assert 0 <= fl <= 255 and 0 <= world <= 255
        recs = records(files[fl])
        assert 0 < len(recs) <= 256, f'file {fl}: {len(recs)} clubs'
        rows = []
        for i, r in enumerate(recs):
            assert r[0] == fl and r[1] == i, f'file {fl} record {i}: team word {r[0]}/{r[1]}'
            nm = name_of(r)
            rows.append((club_strength(r) if nm else 0, nm, r[DIVISION]))
        out[(world, fl)] = rows
    return out


def blob(tab, country=None):
    """the FRSS v2 table of tab; country = {(world, file): country id} (default: the file itself)"""
    keys = sorted(tab)
    idx, vals = b'', []
    for w, fl in keys:
        rows = tab[(w, fl)]
        cid = fl if country is None else country[(w, fl)]
        assert 0 < len(rows) <= 256 and len(vals) <= 0xFFFF and 0 <= cid <= 255
        idx += struct.pack('<BBBBH', w, fl, len(rows) & 255, cid, len(vals))        # (count 0 = 256)
        for st, *_ in rows:
            assert 0 <= st <= 0xFFFF
            vals.append(st)
    return MAGIC + struct.pack('<BBH', VERSION, 0, len(keys)) + idx + struct.pack(f'<{len(vals)}H', *vals)


def _index(b):
    """[(world, file, count, country, first)] of an FRSS v2 blob, checked (a v1 blob is refused)"""
    assert len(b) >= 8 and b[:4] == MAGIC, b[:8]
    assert b[4] == VERSION, f'FRSS version {b[4]}: only v{VERSION} is read'
    n = struct.unpack_from('<H', b, 6)[0]
    assert b[5] == 0 and len(b) >= 8 + 6 * n
    rows, end = [], 0
    for i in range(n):
        r = struct.unpack_from('<BBBBH', b, 8 + 6 * i)
        r = r[:2] + (r[2] or 256,) + r[3:]              # (count 0 = 256 clubs)
        assert r[4] == end, (r, end)
        rows.append(r)
        end += r[2]
    keys = [r[:2] for r in rows]
    assert len(b) == 8 + 6 * n + 2 * end and keys == sorted(set(keys))
    return rows


def parse(b):
    """{(world, file): [strength by ordinal]} of an FRSS v2 blob (the reference reader)"""
    rows = _index(b)
    v0 = 8 + 6 * len(rows)
    return {(w, fl): list(struct.unpack_from(f'<{cnt}H', b, v0 + 2 * first)) for w, fl, cnt, _c, first in rows}


def countries(b):
    """{(world, file): country id} of an FRSS v2 blob"""
    return {(w, fl): c for w, fl, _n, c, _f in _index(b)}


def pack(slices):
    """DATA\\FRSS.DAT of {world byte: that world's FRSS v2 blob}"""
    ws = sorted(slices)
    assert 0 < len(ws) <= 255
    off = 8 + FILE_ENTRY * len(ws)
    idx = b''
    for w in ws:
        assert {k[0] for k in parse(slices[w])} == {w}, f'world {w}: a slice holds its own world only'
        idx += struct.pack('<BBHII', w, 0, 0, off, len(slices[w]))
        off += len(slices[w])
    return FILE_MAGIC + struct.pack('<BBH', FILE_VERSION, len(ws), 0) + idx + b''.join(slices[w] for w in ws)


def unpack(b):
    """{world byte: slice} of an FRSS.DAT, every slice checked (the reference reader of the file)"""
    assert len(b) >= 8 and b[:4] == FILE_MAGIC and b[4] == FILE_VERSION and b[6:8] == b'\0\0', b[:8]
    n = b[5]
    out, end = {}, 8 + FILE_ENTRY * n
    assert n and len(b) >= end
    for i in range(n):
        w, z, z2, off, ln = struct.unpack_from('<BBHII', b, 8 + FILE_ENTRY * i)
        assert z == 0 and z2 == 0 and off == end and w not in out and (not out or w > max(out)), (w, off, end)
        out[w] = b[off:off + ln]
        assert len(out[w]) == ln and {k[0] for k in parse(out[w])} == {w}, f'world {w}'
        end = off + ln
    assert end == len(b)
    return out


def world_slice(b, world):
    """the engine's read: the world's slice of an FRSS.DAT, None when the file has no entry for it"""
    return unpack(b).get(world)


def lookup(tab, world, team):
    """the pick's read of a team word (file | ordinal << 8) in a parsed table: its strength; None when the world /
    file is not in the table, when the ordinal is not below the file's club count (never installed: the guard) or
    when the record holds no club"""
    fl, i = team & 0xFF, team >> 8
    vals = tab.get((world, fl))
    if vals is None or i >= len(vals):
        return None
    return vals[i] or None


def world0_files(exe, data):
    """{file: path} of the 1996-97 world's club files: the countries of frturns.world0 (the exe's own continent
    tables: no customs, no national teams, no pack / other-world files)"""
    import frturns
    out = {}
    for n in sorted(frturns.world0(frturns.Exe(exe))):
        f = os.path.join(data, f'TEAM.{n:03d}')
        assert os.path.isfile(f), f
        out[n] = f
    return out


def _packs():
    import contextlib
    import io
    import mkseason
    with contextlib.redirect_stdout(io.StringIO()):          # (the packs' build logs)
        return mkseason, mkseason.worlds()


def build_worlds():
    """the world bytes a build has tables for: 0 + the career worlds of its packs (pack.json "world")"""
    return [0] + sorted(_packs()[1])


def world_files(world, exe, data):
    """({file: path}, {file: country id}) of a world's club files in a build's DATA dir. World 0: world0_files, a
    country = its file. A career world: per career pack the files of pack_roles (league + state championships),
    under the world's stem (mkseason.ns_stem); country id = the pack's lowest such file number."""
    if world == 0:
        files = world0_files(exe, data)
        return files, {fl: fl for fl in files}
    mk, worlds = _packs()
    assert world in worlds, f'world {world}: no career pack of the build (SEASON_PACKS) has it; worlds {sorted(worlds)}'
    stem = mk.ns_stem(world).upper()
    files, cid = {}, {}
    for pk in worlds[world]:
        fls = sorted(pack_roles(pk)[0])
        assert fls, pk.meta['id']
        for fl in fls:
            assert fl not in files and fl not in GUEST_FILES and not 80 <= fl <= 85, (pk.meta['id'], fl)
            files[fl] = os.path.join(data, '%s.%03d' % (stem, fl))
            cid[fl] = fls[0]
    return files, cid


def pack_roles(pk):
    """({file: role} taken, {file: role} left out) of a career pack by THE FILE RULE: taken = the league's files +
    the files holding a club of a 'state' competition; left out = every other file key but the off-file pool (cup-only
    clubs)"""
    pool = getattr(pk, 'pool_key', None)
    roles = set(pk.league_roles()) | {pk.clubs[k]['file'] for c in pk.comps if c.get('type') == 'state' for k in c['clubs']}
    take = {f: k for k, (f, _b) in pk.files.items() if k in roles and k != pool}
    out = {f: k for k, (f, _b) in pk.files.items() if k not in roles and k != pool}
    assert take and not set(take) & set(out), pk.meta['id']
    return take, out


def pack_files():
    """{world: {career pack id: {'files': its club files taken, 'out': {file: role} left out}}} of the build's packs
    (the file rule's and the country-id rule's input)"""
    return {w: {pk.meta['id']: {'files': sorted(t), 'out': {str(f): k for f, k in o.items()}}
                for pk in pks for t, o in [pack_roles(pk)]} for w, pks in _packs()[1].items()}


def world_table(world, exe, data):
    """(tab, {(world, file): country id}) of one world from a build's exe + DATA"""
    files, cid = world_files(world, exe, data)
    return table(world, files), {(world, fl): c for fl, c in cid.items()}


def gen(exe, data, out=None, log=None):
    """DATA\\FRSS.DAT for the build of exe + data (written to out, default data): every world of build_worlds() whose
    club files are all in data. Returns {world: (files, clubs, slice bytes)}, None when no world could be built
    (nothing written)."""
    slices, info = {}, {}
    for w in build_worlds():
        try:
            files, fc = world_files(w, exe, data)
        except AssertionError as e:                    # (a test build's exe / DATA without this world's files)
            (log or print)(f'frstr: world {w} left out: {str(e)[:120]}')
            continue
        miss = [os.path.basename(f) for f in files.values() if not os.path.isfile(f)]
        if miss:
            (log or print)(f'frstr: world {w} left out: {len(miss)} of {len(files)} team files not in {data} ({miss[0]} ...)')
            continue
        tab, cid = table(w, files), {(w, fl): c for fl, c in fc.items()}
        slices[w] = blob(tab, cid)
        assert {k: [r[0] for r in v] for k, v in tab.items()} == parse(slices[w]) and countries(slices[w]) == cid
        info[w] = (len(tab), sum(len(v) for v in tab.values()), len(slices[w]))
    if not slices:
        return None
    b = pack(slices)
    assert unpack(b) == slices
    open(os.path.join(out or data, FILE_NAME), 'wb').write(b)
    return info


def verify_words(b, data, stems):
    """every team word with a strength > 0 in an FRSS.DAT (bytes b) against the team files that are in data NOW:
    [texts] of the words whose record is missing (file absent / short, ordinal >= its count), does not carry (file,
    ordinal) in bytes 0 / 1 or has no name. stems = {world: 'TEAM' / 'TMW5'}. The game has no bound after
    LoadTeamFile (GetTeamPointer): such a word, once picked or shown, hangs it - [] is the only release state."""
    bad = []
    for w, sl in sorted(unpack(b).items()):
        for (_w, fl), vals in sorted(parse(sl).items()):
            f = os.path.join(data, '%s.%03d' % (stems[w], fl))
            d = open(f, 'rb').read() if os.path.isfile(f) else b''
            n = min(struct.unpack_from('>H', d, 0)[0], (len(d) - 2) // TEAM_SIZE) if len(d) >= 2 else 0
            for i, st in enumerate(vals):
                if not st:
                    continue
                r = d[2 + TEAM_SIZE * i:2 + TEAM_SIZE * (i + 1)] if i < n else None
                why = 'no record' if r is None else f'record says {r[0]}/{r[1]}' if (r[0], r[1]) != (fl, i) else \
                    '' if name_of(r) else 'no name'
                if why:
                    bad.append(f'world {w} {os.path.basename(f)} ordinal {i} (strength {st}): {why}')
    return bad


def build_stems():
    """{world: team file stem} of the build's worlds (0 and the base world: TEAM)"""
    mk = _packs()[0]
    return {w: 'TEAM' if w == 0 else mk.ns_stem(w).upper() for w in build_worlds()}


def check(build):
    """the release recipe's ASSERT: (ok, text) - build/SWOS/DATA/FRSS.DAT is there, holds every world of the build
    (0 + its packs' career worlds), every team word with a strength is a named record of the build's team files as
    they are now (verify_words) and the file equals a fresh gen() from the build's ENGLISH.EXE + DATA"""
    import tempfile
    data = os.path.join(build, 'SWOS', 'DATA')
    f = os.path.join(data, FILE_NAME)
    if not os.path.isfile(f):
        return False, f'no {f}'
    b = open(f, 'rb').read()
    try:
        got = unpack(b)
    except AssertionError as e:
        return False, f'{f} does not parse: {e}'
    want = build_worlds()
    if sorted(got) != want or len(want) < 3:
        return False, f'worlds {sorted(got)} in the file, the build has {want} (a release: 3 worlds)'
    bad = verify_words(b, data, build_stems())
    if bad:
        return False, f'{len(bad)} team word(s) with a strength and no record in the team files (the game would hang): ' \
            + '; '.join(bad[:5])
    with tempfile.TemporaryDirectory() as t:
        try:
            info = gen(os.path.join(build, 'SWOS', 'ENGLISH.EXE'), data, t, log=lambda s: None)
        except AssertionError as e:
            return False, f'a fresh build of the DATA fails: {str(e)[:200]}'
        if info is None or open(os.path.join(t, FILE_NAME), 'rb').read() != b:
            return False, f'{f} differs from a fresh build of the DATA'
    return True, f'{len(b)} B, ' + ', '.join(f'world {w}: {i[0]} files {i[1]} clubs {i[2]} B' for w, i in sorted(info.items()))


def report(tab, src, country=None):
    n = sum(len(v) for v in tab.values())
    h = hashlib.sha256()
    for k in sorted(tab):
        h.update(repr((k, tab[k])).encode())
    ln = [f'# frstr: {len(tab)} files, {n} clubs, from {src}; rule statespec.club_strength (best 11 prices, >= 5)',
          f'# sha256 of the rows {h.hexdigest()[:16]}', '# world file country ordinal strength division name']
    for (w, fl) in sorted(tab):
        c = fl if country is None else country[(w, fl)]
        for i, (st, nm, dv) in enumerate(tab[(w, fl)]):
            ln.append(f'{w} {fl:3} {c:3} {i:3} {st:4} {dv} {nm}')
    return '\n'.join(ln) + '\n'


def main(argv):
    if argv[:1] == ['build'] or argv[:1] == ['check']:
        build = argv[1]
        if argv[0] == 'build':
            data = os.path.join(build, 'SWOS', 'DATA')
            info = gen(os.path.join(build, 'SWOS', 'ENGLISH.EXE'), data)
            assert info, f'{build}: no world could be built'
            print(f'frstr: {FILE_NAME} {os.path.getsize(os.path.join(data, FILE_NAME))} B: '
                  + ', '.join(f'world {w}: {i[0]} files {i[1]} clubs {i[2]} B' for w, i in sorted(info.items())))
            return 0
        ok, txt = check(build)
        print(('FRSS OK: ' if ok else 'FRSS FAIL: ') + txt)
        return 0 if ok else 1
    if argv[:1] == ['packs']:                       # (the host test's read of the country rule's input)
        import json
        print(json.dumps(pack_files(), sort_keys=True))
        return 0
    arg = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    exe = arg('--exe', os.path.join(MAIN, 'orig', 'ENGLISH.EXE'))
    data = arg('--data', os.path.join(MAIN, 'orig', 'DATA'))
    out = arg('--out', OUT)
    os.makedirs(out, exist_ok=True)
    src = os.path.relpath(data, MAIN)
    for world in (build_worlds() if '--all' in argv else [int(arg('--world', '0'))]):
        tab, cid = world_table(world, exe, data)
        b = blob(tab, cid)
        assert {k: [r[0] for r in v] for k, v in tab.items()} == parse(b) and countries(b) == cid
        base = os.path.join(out, f'frstr_w{world}')
        open(base + '.bin', 'wb').write(b)
        open(base + '.txt', 'w').write(report(tab, src, cid))
        print(f'frstr: world {world}: {len(tab)} files, {len(set(cid.values()))} countries, '
              f'{sum(len(v) for v in tab.values())} clubs, {len(b)} B -> {base}.bin / .txt')
    if '--all' in argv:
        info = gen(exe, data, out)
        print(f'frstr: {FILE_NAME} {os.path.getsize(os.path.join(out, FILE_NAME))} B, worlds {sorted(info)} -> {out}')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    sys.exit(main(sys.argv[1:]))
