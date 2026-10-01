"""Register countries and club leagues (Roadmap 2).

A country number is also its team file number (data/team.nnn, 0..255). What a club country needs
(addresses for ENGLISH.EXE, all found by content here, so every language works):
  countriesTable    obj2+0x6742  256 dword ptrs -> [continent byte, NAME\\0, ADJECTIVE\\0]
  competitionsTable obj2+0x8B1C  256 dword ptrs -> country table [league ptrs, -2, cup ptrs, -1]
  teamsCountryNumbers obj2+0xB2A38 256 words: global team number base (global = base + team ordinal, < 2000)
  continent tables  competitionsTable[80..85] -> [ptr, ptr, -1] + country bytes + FF (menus, world view)
  seasonEndList     obj2+0x943A  country bytes + FF, read by cseg_91428: at the end of a career season every
                                 listed country gets cseg_9153F (league) + cseg_93974 (cup qualifiers)
League struct: 13-byte header [id, 0, country, start, end, names offset - 5 (0 = default names; 0x15 with 2 divisions), 0, 0, 0, divisions, 2 (games per
pair), 3 (points per win), 0x35] + 6 bytes per division [teams, promoted, promotion playoff teams, relegated,
relegation playoff, playoff data] + 0 + (if named) 2 name dwords per division (offsets from STR_BASE).

New strings go to obj2 pages added after the data object (OBJ2_AREA); pointer tables go to the obj1 cave.
"""
import struct

import sacups

CN_NORTH_AMERICA = 83
CONTINENT = {'europe': 0, 'north_america': 1, 'south_america': 2, 'asia': 3, 'oceania': 4, 'africa': 5}
COMP = [None]                                      # obj2 offset of competitionsTable (tables())
FREE_IDS = list(range(0x70, 0x7c))                 # contest ids nobody uses (0x6c..0x6f = SA cups)

# country number -> (continent, name, adjective per language ('*' = all), league)
COUNTRIES = {
    47: dict(continent='north_america', name={'*': b'COSTA RICA'}, adj={'en': b'COSTA RICAN', '*': b'COSTA RICA'},
             league=dict(start=0x38, end=0x20, games=2, divisions=[(12, 0, 0, 0, 0, 0)],
                         names=[(b'PRIMERA DIVISION', b'PRIMERA')])),
}

import africa                                       # noqa: E402  Egypt, Morocco, Tunisia, Nigeria, Cameroon
import asia                                         # noqa: E402  South Korea, China, Saudi Arabia
COUNTRIES.update(africa.countries_config())
COUNTRIES.update(asia.countries_config())
import namerica                                     # noqa: E402  Guatemala, Honduras
COUNTRIES.update(namerica.countries_config())


class Obj2Area:
    """Bump allocator in the obj2 pages added by lepatch.add_object_page (strings, records)."""
    def __init__(self, p, start, end):
        self.p, self.at, self.end = p, start, end

    def add(self, data):
        off = self.at
        assert off + len(data) <= self.end, 'obj2 area full'
        self.p.put(2, off, data)
        self.at += len(data)
        return off


def tables(p):
    """obj2 offsets of countriesTable, teamsCountryNumbers and seasonEndList (+ its single code reference)."""
    d2 = p.le.obj_bytes(2)
    fx = {f[1]: (f[3], f[4]) for f in p.le.fixups() if f[0] == 2}
    # countriesTable: entries 0..46 and 252..255 set, 47 empty; 9 (second England) set, unlike competitionsTable
    ct = [o for o in fx if all(o + 4 * i in fx for i in list(range(47)) + [252, 253, 254, 255])
          and o + 4 * 47 not in fx and o + 4 * 86 not in fx]
    assert len(ct) == 1, ct
    # competitionsTable: same holes, but entry 9 (second England) empty
    comp = [o for o in fx if all(o + 4 * i in fx for i in list(range(9)) + list(range(10, 47)) + list(range(80, 86)))
            and o + 4 * 9 not in fx and o + 4 * 47 not in fx and o + 4 * 86 not in fx]
    assert len(comp) == 1, comp
    COMP[0] = comp[0]
    tcn = d2.find(struct.pack('<6H', 0, 16, 26, 44, 60, 72))
    assert tcn >= 0 and d2.find(struct.pack('<6H', 0, 16, 26, 44, 60, 72), tcn + 1) < 0
    head = bytes([0, 1, 76, 2, 3, 4, 5, 6, 7, 8, 10])         # also inside the Europe table: take the one code reads
    starts = [i for i in range(len(d2)) if d2.startswith(head, i)]
    refs = [f for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] in starts]
    assert len(refs) == 1, refs
    return ct[0], tcn, refs[0][4], refs[0][1]


def patch(p, lang, area, cave, extra=None):
    """Register COUNTRIES; extra = {continent: [(obj, contest offset)]} cup buttons added to that continent.
    Returns the new end of the obj1 cave."""
    d2 = p.le.obj_bytes(2)
    ct, tcn, sel, sel_ref = tables(p)
    fx2 = {f[1] for f in p.le.fixups() if f[0] == 2}
    comp = COMP[0]
    at = cave
    ids = iter(FREE_IDS)
    new = []
    for n, c in sorted(COUNTRIES.items()):
        name = c['name'][lang] if lang in c['name'] else c['name']['*']
        adj = c['adj'][lang] if lang in c['adj'] else c['adj']['*']
        assert ct + 4 * n not in fx2 and comp + 4 * n not in fx2, f'country {n} exists'
        rec = area.add(bytes((CONTINENT[c['continent']],)) + name + b'\0' + adj + b'\0')
        p.add_ptr(2, ct + 4 * n, 2, rec)
        if 'base' in c:                             # global team numbers: base + ordinal, must be free and < 2000
            p.put(2, tcn + 2 * n, struct.pack('<H', c['base']))

        lg = c['league']
        named = bool(lg.get('names'))
        cid = lg['id'] if 'id' in lg else next(ids)
        hdr = bytes((cid, 0, n, lg['start'], lg['end'], 9 + 6 * len(lg['divisions']) if named else 0, 0, 0, 0, len(lg['divisions']),
                     lg['games'], 3, 0x35))
        body = hdr + b''.join(bytes(dv) for dv in lg['divisions']) + b'\0'
        if named:
            for full, short in lg['names']:
                rel = []
                for s in (full, short):
                    i = d2.find(s + b'\0')
                    if i < 0 or d2[i - 1] != 0:
                        i = area.add(s + b'\0')
                    rel.append(i - sacups.STR_BASE)
                body += struct.pack('<II', *rel)
        league = at
        p.put(1, at, body)
        at = (at + len(body) + 3) & ~3
        cup = None
        if lg.get('cup'):                           # national cup: clone of the Algerian cup layout (18 bytes)
            cu = lg['cup']
            body = bytes((cu['id'], 1, n, 0x60, 0x80, 0, 0, 0, 0, 0, cu['teams'], 1, 0x35, 2)) + bytes(cu['rounds'])
            cup = at
            p.put(1, at, body)
            at = (at + len(body) + 3) & ~3
        table = at                                  # [league, -2, (cup,) -1]
        p.add_ptr(1, at, 1, league)
        p.put(1, at + 4, struct.pack('<i', -2))
        at += 8
        if cup is not None:
            p.add_ptr(1, at, 1, cup)
            at += 4
        p.put(1, at, struct.pack('<i', -1))
        at += 4
        p.add_ptr(2, comp + 4 * n, 1, table)
        new.append((n, c['continent'], cid, sum(dv[0] for dv in lg['divisions'])))

    # continent tables: [ptr, ptr, -1] + countries + FF, rebuilt in the cave with the new countries
    for cont in sorted({c['continent'] for c in COUNTRIES.values()}):
        cn = 80 + {'europe': 0, 'africa': 1, 'south_america': 2, 'north_america': 3, 'asia': 4, 'oceania': 5}[cont]
        tobj, old = p.target(2, comp + 4 * cn)
        assert tobj in (1, 2) and cont != 'europe' and cont != 'south_america', 'Europe/SA tables live in the cave'
        src = p.le.obj_bytes(tobj)
        ptrs = [p.target(tobj, old), p.target(tobj, old + 4)] + (extra or {}).get(cont, [])
        assert src[old + 8:old + 12] == b'\xff' * 4
        countries = src[old + 12:src.index(b'\xff', old + 12)]
        countries += bytes(n for n, cc, _, _ in new if cc == cont and n not in countries)
        tab = at
        for k, (o, t) in enumerate(ptrs):
            p.add_ptr(1, at + 4 * k, o, t)
        end = at + 4 * len(ptrs)
        p.put(1, end, b'\xff' * 4 + countries + b'\xff')
        at = (end + 4 + len(countries) + 1 + 3) & ~3
        p.retarget(2, comp + 4 * cn, 1, tab)

    # season-end list: + new league countries
    old = d2[sel:d2.index(b'\xff', sel)]
    lst = old + bytes(n for n, _, _, _ in new if n not in old)
    sel_new = at
    p.put(1, at, lst + b'\xff')
    at = (at + len(lst) + 1 + 3) & ~3
    p.retarget(1, sel_ref, 1, sel_new)

    for n, cont, cid, teams in new:
        base = COUNTRIES[n].get('base', struct.unpack_from('<H', d2, tcn + 2 * n)[0])
        print(f'exe: country {n} ({cont}) registered: league id {cid:#x}, {teams} teams, global base {base}')
    print(f'exe: countriesTable obj2+{ct:#x}, season-end list obj2+{sel:#x} -> obj1+{sel_new:#x} ({len(lst)} countries)')
    return at
