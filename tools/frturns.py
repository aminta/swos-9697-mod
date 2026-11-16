"""4.2 preseason friendlies, data part 2: the TURNS table (teamcache-fable-design.md 5.1 / 5.4, Davide 16/11).

One table format for every world (CONVENTIONS rule 0): a row per (world byte, country) with the country's first league
day F and the four friendly turns, read from the league / cup structs of an exe - never typed by hand. Today it is
built for world 0 (1996-97: the 67 original leagues + the countries the mod adds / rebuilds: arg97, mls97, nsl97,
nz97, finals97, africa, asia, namerica); another world = another call of rows() with its own structs.

Weeks ("turns") are the career calendar's week bytes: 8 a month from January, a year = 96 (split.week_of).

The rule (friendlies-a-research.md 1.4, made general):
  F  = the league header's first week (byte +3; every division of a country starts there: cseg_2730A spreads each
       division's days from the same header weeks). A league with F < 8 has no room for a preseason: it is SHIFTED
       +8 (option A, Davide 16/11: header start and end + 8) and F is the shifted value.
  E  = F, moved back to the first week of any other competition a club of the country can be in whose weeks
       [first, last] the window E-8 .. E-2 would touch: its national cups (the country table's cup structs) and its
       continent's club cups (the continent table's structs with country FFh). A span, not the single days: the
       days of a knockout depend on its draw sizes, the span is safe for every one.
  turns = E-8, E-6, E-4, E-2 (even; E odd -> E-1 first). So every friendly is before the club's first league day and
       on no cup / continental week. E == F in every country but the ones flagged EARLY.

Flags (one byte a row):
  SHIFT   01h  the league moves 8 turns later (option A); the row's F is the moved one
  NATIVE  02h  a division of the country has a native play-off (division byte +5): cseg_8DAC3 puts it in career
               slot 4 at the season start -> the friendlies need the re-install (design 5.2); pomask = the divisions
  ICUP4   04h  the Intercontinental can be in slot 4 at the season start (sacups int4_step: the country has a league
               cup = two cup structs, and its continent's champion plays the Intercontinental) -> same re-install
  EARLY   08h  E < F: a cup / continental span touches F-8 .. F-2, the friendlies are moved before it

Binary (FRTN, little-endian; the engine reads it by world byte + country):
  +0  'FRTN'   +4 db version (1)   +5 db row size (10)   +6 dw rows
  rows, sorted by (world, country): db world, country, F, turn 1..4, flags, pomask, shift (turns added to the
  league header's two week bytes: 0 or 8)

    python3 tools/frturns.py [--exe EXE] [--world 0] [--out DIR]      (writes frturns_w<world>.bin / .txt / .json)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'frdata')

SHIFT, NATIVE, ICUP4, EARLY = 1, 2, 4, 8
FLAG_NAMES = ((SHIFT, 'SHIFT'), (NATIVE, 'NATIVE'), (ICUP4, 'ICUP4'), (EARLY, 'EARLY'))
MAGIC, VERSION, ROW = b'FRTN', 1, 10
SHIFT_TURNS = 8                     # option A: one month
YEAR = 96
CONTINENTS = range(80, 86)          # competitionsTable entries: Europe, Africa, South America, North America, Asia, Oceania
NOT_CLUBS = (72, 100)               # CUSTOM, EDITED CUSTOMS: league structs, but no real clubs
INT_ID = 0x6F                       # sacups.INT_ID (the Intercontinental's contest id)
LANGS = ('ENGLISH', 'ITALIAN', 'FRENCH', 'GERMAN')


class Exe:
    """The competition structs of an exe (an original or a built one), found by content."""

    def __init__(self, path):
        import lepatch
        self.path = path
        self.p = lepatch.LEPatch(path)
        self.fx = {(f[0], f[1]): (f[3], f[4]) for f in self.p.le.fixups()}
        self._b = {}
        self.comp = self._comp()

    def b(self, obj):
        if obj not in self._b:
            self._b[obj] = self.p.le.obj_bytes(obj)
        return self._b[obj]

    def _comp(self):
        """obj2 offset of competitionsTable: the one pointer run whose entries 0 / 1 / 2 lead to the league structs
        of countries 0 / 1 / 2 (struct byte 1 = 0 a league, byte 2 = the country)"""
        hit = []
        for (obj, off), _t in self.fx.items():
            if obj != 2:
                continue
            ok = True
            for n in range(3):
                t = self.fx.get((2, off + 4 * n))
                t = t and self.fx.get(t)
                if not t or self.b(t[0])[t[1] + 1:t[1] + 3] != bytes((0, n)):
                    ok = False
                    break
            if ok:
                hit.append(off)
        assert len(hit) == 1, f'{self.path}: competitionsTable {hit}'
        return hit[0]

    def table(self, n):
        """country table n -> (leagues, cups, tail bytes): struct locations (obj, offset) before / after the -2
        mark, and the bytes after the -1 terminator up to FFh (a continent's countries)"""
        t = self.fx.get((2, self.comp + 4 * n))
        if not t:
            return None
        obj, off = t
        b, sec, out = self.b(obj), 0, ([], [])
        for _ in range(64):
            v = struct.unpack_from('<i', b, off)[0]
            if (obj, off) in self.fx:
                out[sec].append(self.fx[(obj, off)])
            elif v == -2:
                sec = 1
            elif v == -1:
                break
            off += 4
        else:
            raise AssertionError(f'country table {n}: no terminator')
        tail = b[off + 4:b.index(b'\xff', off + 4)]
        return out[0], out[1], bytes(tail)

    def hdr(self, loc, n=13):
        return bytes(self.b(loc[0])[loc[1]:loc[1] + n])


def league_of(x, n):
    """(location, header 13 B, [division 6 B]) of country n's league struct, None when it has none"""
    t = x.table(n)
    if not t:
        return None
    for loc in t[0]:
        h = x.hdr(loc)
        if h[1] == 0 and h[2] == n:
            nd = h[9]
            assert 1 <= nd <= 8, (n, h.hex())
            body = x.hdr(loc, 13 + 6 * nd)
            return loc, h, [body[13 + 6 * d:19 + 6 * d] for d in range(nd)]
    return None


def world0(x):
    """{country: continent entry} of the world the exe's own tables describe (1996-97): the countries listed in the
    six continent tables that have a league struct and real clubs"""
    out = {}
    for c in CONTINENTS:
        t = x.table(c)
        assert t, f'continent table {c}'
        for n in t[2]:
            if n in NOT_CLUBS or n in CONTINENTS or n >= 0xF0:
                continue
            if league_of(x, n):
                assert n not in out, f'country {n} in two continents'
                out[n] = c
    return out


def club_cups(x, c):
    """the club cups of continent entry c: [(id, first week, last week)] (struct byte 2 = FFh: any country)"""
    t = x.table(c)
    return [(h[0], h[3], h[4]) for h in (x.hdr(loc) for loc in t[0] + t[1]) if h[2] == 0xFF]


def span(first, last):
    """the weeks a competition's days lie in: [first, last], last a year later when below first (cseg_2730A)"""
    return first, last + (YEAR if last < first else 0)


def turns_of(f, others):
    """(E, [4 turns]) for a first league day f and the other competitions' (first, last) header weeks: the window
    E-8 .. E-2 starts at E = f and moves before every competition whose span it would touch"""
    e = f - f % 2
    spans = sorted(span(a, b) for a, b in others)
    moved = True
    while moved:
        moved = False
        for a, b in spans:
            if a <= e - 2 and b >= e - 8:
                e, moved = a - a % 2, True
    assert e >= 8, f'no room for 4 friendlies before week {e} (F {f})'
    return e, [e - 8, e - 6, e - 4, e - 2]


def rows(x, world=0):
    """the table's rows: [dict(world, country, cont, f0, l0, f, last, shift, turns, flags, pomask, divs, cups,
    conti, e, loc)]; f0 / l0 = the header's own weeks, f / last = after the shift"""
    out = []
    cc = world0(x)
    conti = {c: club_cups(x, c) for c in CONTINENTS}
    for n in sorted(cc):
        loc, h, divs = league_of(x, n)
        f0, l0 = h[3], h[4]
        shift = SHIFT_TURNS if f0 < 8 else 0
        f, last = f0 + shift, l0 + shift
        cups = [(c[0], c[3], c[4]) for c in (x.hdr(l) for l in x.table(n)[1]) if c[1] in (1, 2) and c[2] == n]
        cont = conti[cc[n]]
        e, tt = turns_of(f, [c[1:] for c in cups] + [c[1:] for c in cont])
        pomask = sum(1 << d for d, dv in enumerate(divs) if dv[5])
        flags = (SHIFT if shift else 0) | (NATIVE if pomask else 0) | (EARLY if e < f - f % 2 else 0)
        if len(cups) >= 2 and any(c[0] == INT_ID for c in cont):
            flags |= ICUP4
        out.append(dict(world=world, country=n, cont=cc[n], f0=f0, l0=l0, f=f, last=last, shift=shift, turns=tt,
                        flags=flags, pomask=pomask, divs=[d.hex() for d in divs], cups=cups, conti=cont, e=e,
                        loc=loc, games=h[10], teams=[d[0] for d in divs]))
    return out


def check(rs):
    """the builder's asserts (design 5.1): four even turns in order, all before F and before every cup / continental
    first day, none below 0; a shifted league keeps its length; F below 128 after the shift"""
    for r in rs:
        t, n = r['turns'], r['country']
        assert len(t) == 4 and t == sorted(set(t)) and all(w % 2 == 0 for w in t), (n, t)
        assert 0 <= t[0] and t[3] < r['f'], (n, t, r['f'])
        for a, b in (span(*c[1:]) for c in r['cups'] + r['conti']):
            assert b < t[0] or a > t[3], (n, t, (a, b))
        assert (r['shift'] == SHIFT_TURNS) == (r['f0'] < 8) and r['f'] - r['f0'] == r['last'] - r['l0'], n
        assert r['f'] < 128 and r['last'] < 256, n
    assert len({(r['world'], r['country']) for r in rs}) == len(rs)


def blob(rs):
    rs = sorted(rs, key=lambda r: (r['world'], r['country']))
    out = MAGIC + struct.pack('<BBH', VERSION, ROW, len(rs))
    for r in rs:
        out += bytes([r['world'], r['country'], r['f']] + r['turns'] + [r['flags'], r['pomask'], r['shift']])
    return out


def parse(b):
    """{(world, country): dict(f, turns, flags, pomask, shift)} of a FRTN blob (the reference reader)"""
    assert b[:4] == MAGIC and b[4] == VERSION and b[5] == ROW, b[:8]
    n = struct.unpack_from('<H', b, 6)[0]
    assert len(b) == 8 + ROW * n, (len(b), n)
    out = {}
    for i in range(n):
        r = b[8 + ROW * i:8 + ROW * (i + 1)]
        out[(r[0], r[1])] = dict(f=r[2], turns=list(r[3:7]), flags=r[7], pomask=r[8], shift=r[9])
    assert len(out) == n and list(out) == sorted(out)
    return out


def lookup(tab, world, country):
    """the engine's read: the row of (world byte, country), None = no friendlies there"""
    return tab.get((world, country))


def league_days(r, div=0, shifted=True):
    """the weeks of division div's match days (fport.day_weeks = cseg_2730A's spread)"""
    import fport
    n = r['teams'][div]
    a, b = (r['f'], r['last']) if shifted else (r['f0'], r['l0'])
    return fport.day_weeks(a, b, fport.days_of(n + n % 2, r['games']))


def shift_sites(names=None, dirs=None):
    """Option A's bytes: for every original exe, [(exe, country, obj, offset of header byte +3, old 2 B, new 2 B)] -
    the league header's first / last week of each SHIFT country. Nothing else holds those weeks: the calendar
    (cseg_8BF89), the season's week count (dseg_D6CA2) and the job-offer quarters (weeks.py) are computed from the
    header at run time."""
    dirs = dirs or [os.path.join(MAIN, 'orig'), os.path.join(MAIN, 'orig', 'gog')]
    out = []
    for d in dirs:
        for lang in names or LANGS:
            f = os.path.join(d, lang + '.EXE')
            if not os.path.isfile(f):
                continue
            x = Exe(f)
            for r in rows(x):
                if r['shift']:
                    obj, off = r['loc']
                    le = x.p.le
                    fo = le.file_off(obj, off + 3) if hasattr(le, 'file_off') else None
                    out.append(dict(exe=os.path.relpath(f, MAIN), country=r['country'], obj=obj, off=off + 3,
                                    file_off=fo, old=[r['f0'], r['l0']], new=[r['f'], r['last']]))
    return out


def names_of(x):
    """{country: name} from the exe's countriesTable (found from competitionsTable's twin: the pointer run whose
    entries lead to [continent byte, NAME\\0]) - for the report only; {} when not found"""
    out = {}
    b2 = x.b(2)
    for (obj, off), t in x.fx.items():
        if obj != 2 or t[0] != 2:
            continue
        if bytes(b2[t[1]:t[1] + 9]) == b'\0ALBANIA\0' or bytes(b2[t[1]:t[1] + 9]) == b'\0ALBANIE\0' \
                or bytes(b2[t[1]:t[1] + 10]) == b'\0ALBANIEN\0':
            for n in range(256):
                u = x.fx.get((2, off + 4 * n))
                if u:
                    s = bytes(x.b(u[0])[u[1] + 1:u[1] + 40]).split(b'\0')[0]
                    out[n] = s.decode('latin1')
            break
    return out


def report(rs, x, sites):
    nm = names_of(x)
    fl = lambda v: '+'.join(s for b, s in FLAG_NAMES if v & b) or '-'
    ln = [f'# frturns: world {rs[0]["world"]}, {len(rs)} leagues, from {os.path.relpath(x.path, MAIN)}',
          '# country name: F (header first-last) turns | flags | divisions with a native play-off | cups (spans) |'
          ' continent club cups (spans)']
    for r in rs:
        hd = f'{r["f0"]}-{r["l0"]}' + (f' -> {r["f"]}-{r["last"]}' if r['shift'] else '')
        ln.append(f'{r["country"]:3} {nm.get(r["country"], "?"):18} F {r["f"]:3} ({hd}) turns {r["turns"]} | '
                  f'{fl(r["flags"])} | po {[d for d in range(8) if r["pomask"] >> d & 1]} | cups '
                  f'{[list(span(*c[1:])) for c in r["cups"]]} | conti '
                  f'{sorted(set(span(*c[1:]) for c in r["conti"]))}')
    hist = {}
    for r in rs:
        hist[r['f']] = hist.get(r['f'], 0) + 1
    ln.append('# F histogram: ' + ', '.join(f'{k}: {v}' for k, v in sorted(hist.items())))
    ln.append('# option A sites (league header byte +3 = first week, +4 = last week):')
    for s in sites:
        ln.append(f'#   {s["exe"]:24} country {s["country"]:3} obj{s["obj"]}+{s["off"]:#x} (file {s["file_off"]:#x}) '
                  f'{bytes(s["old"]).hex()} -> {bytes(s["new"]).hex()}')
    return '\n'.join(ln) + '\n'


def main(argv):
    exe = argv[argv.index('--exe') + 1] if '--exe' in argv else os.path.join(MAIN, 'orig', 'ENGLISH.EXE')
    world = int(argv[argv.index('--world') + 1]) if '--world' in argv else 0
    out = argv[argv.index('--out') + 1] if '--out' in argv else OUT
    x = Exe(exe)
    rs = rows(x, world)
    check(rs)
    sites = shift_sites()
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, f'frturns_w{world}')
    open(base + '.bin', 'wb').write(blob(rs))
    open(base + '.txt', 'w').write(report(rs, x, sites))
    json.dump(dict(rows=[{k: v for k, v in r.items() if k != 'loc'} for r in rs], shift_sites=sites),
              open(base + '.json', 'w'), indent=1, sort_keys=True)
    print(f'frturns: world {world}: {len(rs)} leagues, {len(blob(rs))} B -> {base}.bin / .txt / .json')


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])
