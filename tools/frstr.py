"""4.2 preseason friendlies, data part 1: the STRENGTH table (teamcache-fable-design.md 5.3).

One strength value per club, for the opponent pick's bands (1 stronger / 2 similar / 1 weaker). One table format for
every world (CONVENTIONS rule 0): the key is world byte + team file + ordinal, because team file numbers repeat
between worlds (file 101 = England in Europe 1984-85 and in World 2026-27). Today it is built for world 0 (1996-97);
another world = another table() call with that world's files (TEAM.nnn of the 1984-85 countries, TMW5.nnn).

Strength = the mod's one club-strength rule, statespec.club_strength: the best 11 players' prices, at least 5 (the
rule of statesim / cupd.strength / gplay.c cd_str in World 2026-27). It is CALLED here, not copied: the rows are the
price bytes (PlayerFile +32, the players.csv 'price' column as mkseason writes it) of the record's 16 players.
Range 5 .. 539 (11 x 49), a word.

The table also carries each file's club count: the pick must refuse an ordinal >= count BEFORE any install
(cseg_32E15's file scan has no end test, ref/swos.asm 39437-39445); lookup() is that check's reference.

Binary (FRSS, little-endian):
  +0 'FRSS'   +4 db version (1)   +5 db 0   +6 dw blocks
  index, sorted by (world, file): blocks x [db world, db file, db count, db 0, dw first value's index]
  values: dw strength per club, in ordinal order (0 = no club in that record: never picked)

    python3 tools/frstr.py [--exe EXE] [--data DIR] [--world 0] [--out DIR]   (writes frstr_w<world>.bin / .txt)
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'frdata')

MAGIC, VERSION = b'FRSS', 1
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
        assert 0 < len(recs) <= 255, f'file {fl}: {len(recs)} clubs'
        rows = []
        for i, r in enumerate(recs):
            assert r[0] == fl and r[1] == i, f'file {fl} record {i}: team word {r[0]}/{r[1]}'
            nm = name_of(r)
            rows.append((club_strength(r) if nm else 0, nm, r[DIVISION]))
        out[(world, fl)] = rows
    return out


def blob(tab):
    keys = sorted(tab)
    idx, vals = b'', []
    for w, fl in keys:
        rows = tab[(w, fl)]
        assert len(rows) <= 255 and len(vals) <= 0xFFFF
        idx += struct.pack('<BBBBH', w, fl, len(rows), 0, len(vals))
        for st, *_ in rows:
            assert 0 <= st <= 0xFFFF
            vals.append(st)
    return MAGIC + struct.pack('<BBH', VERSION, 0, len(keys)) + idx + struct.pack(f'<{len(vals)}H', *vals)


def parse(b):
    """{(world, file): [strength by ordinal]} of an FRSS blob (the reference reader)"""
    assert b[:4] == MAGIC and b[4] == VERSION, b[:8]
    n = struct.unpack_from('<H', b, 6)[0]
    v0 = 8 + 6 * n
    out, end = {}, 0
    for i in range(n):
        w, fl, cnt, z, first = struct.unpack_from('<BBBBH', b, 8 + 6 * i)
        assert z == 0 and first == end, (w, fl, first, end)
        out[(w, fl)] = list(struct.unpack_from(f'<{cnt}H', b, v0 + 2 * first))
        end = first + cnt
    assert len(b) == v0 + 2 * end and list(out) == sorted(out) and len(out) == n
    return out


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


def report(tab, src):
    n = sum(len(v) for v in tab.values())
    h = hashlib.sha256()
    for k in sorted(tab):
        h.update(repr((k, tab[k])).encode())
    ln = [f'# frstr: {len(tab)} files, {n} clubs, from {src}; rule statespec.club_strength (best 11 prices, >= 5)',
          f'# sha256 of the rows {h.hexdigest()[:16]}', '# world file ordinal strength division name']
    for (w, fl) in sorted(tab):
        for i, (st, nm, dv) in enumerate(tab[(w, fl)]):
            ln.append(f'{w} {fl:3} {i:3} {st:4} {dv} {nm}')
    return '\n'.join(ln) + '\n'


def main(argv):
    arg = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    exe = arg('--exe', os.path.join(MAIN, 'orig', 'ENGLISH.EXE'))
    data = arg('--data', os.path.join(MAIN, 'orig', 'DATA'))
    world = int(arg('--world', '0'))
    out = arg('--out', OUT)
    assert world == 0, 'only world 0 has a file rule here; call table() with the world\'s own files'
    tab = table(world, world0_files(exe, data))
    b = blob(tab)
    assert {k: [r[0] for r in v] for k, v in tab.items()} == parse(b)
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, f'frstr_w{world}')
    open(base + '.bin', 'wb').write(b)
    open(base + '.txt', 'w').write(report(tab, os.path.relpath(data, MAIN)))
    print(f'frstr: world {world}: {len(tab)} files, {sum(len(v) for v in tab.values())} clubs, {len(b)} B -> '
          f'{base}.bin / .txt')


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])
