"""Guest clubs of the continental cups (World 2026-27): real clubs of associations that are not in the world (CAF,
AFC, OFC, CONCACAF entrants), as team files of their own - no country / league entry, no table.

Data: internal/conti/<conf>.guests.json (the data session's; format agreed 2026-10-20):
  {"conf": "caf", "rotation": ..., "season1": {cup: {round: [club keys]}},
   "clubs": [{"key", "assoc" (FIFA code), "club" (as in the access files), "name" (<= 16, upper case), "coach",
              "tactic", "kit1", "kit2", "lineup", "access", "source",
              "players": [players.csv columns: name, role, position, number, nat, skin, pa ve he ta co sp fi, price]}]}
One team file per confederation (FILES); a club's team word = file | ordinal << 8, ordinal = its place in "clubs".
Each record's countryNumber is its file (GetTeamPointer finds a team by its record's first word, file | ordinal) and
its global number base + ordinal (teamsCountryNumbers[file] = base). The game shows a team's country from
countriesTable[file]: one label per file (LABELS).
"""
import json
import os
import struct

import conti
import mkseason

TEAM_SIZE = mkseason.TEAM_SIZE
DATA = os.environ.get('GUESTS_DATA') or conti.DATA      # (GUESTS_DATA: tests, a sample folder)
FILES = {'caf': 191, 'afc': 192, 'ofc': 193, 'concacaf': 194}
LABELS = {191: ('africa', {'*': b'AFRICA'}),       # (continent, the country name shown for its clubs)
          192: ('asia', {'*': b'ASIA'}),
          193: ('oceania', {'*': b'OCEANIA'}),
          194: ('north_america', {'it': b'NORDAMERICA', 'en': b'N. AMERICA', 'fr': b'AM. DU NORD', 'de': b'NORDAMERIKA'}),
          190: ('europe', {'it': b'ESTERO', 'en': b'ABROAD', 'fr': b'ETRANGER', 'de': b'AUSLAND'})}
POOL = 190                              # the foreign-market pool clubs' file (worldpool.POOL_FILE, 4.0 hotfix): built from
                                        # the world's POOLnn.DAT, one global number for all its records (worldpool.wp_glob)


_POOL = []


def pool_data():
    """The guest world's pool bytes when its records name file POOL (their clubs need a team file), else None."""
    import worldpool
    if _POOL:
        return _POOL[0]
    w = world()
    src = next((d['pool'][1] for d in mkseason.world_defs() if d['n'] == w and d['pool']), None) if w is not None else None
    data = open(src, 'rb').read() if src else None
    _POOL.append(data if data and worldpool.pool_split(data) else None)
    return _POOL[0]


def load(conf, data=None):
    p = os.path.join(data or DATA, f'{conf}.guests.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def ready(data=None):
    """The confederations with a guests file."""
    return [c for c in FILES if load(c, data)]


def words(conf, data=None):
    """{club key: team word} of a confederation's guests (conti's lists; {} without its file)."""
    g = load(conf, data)
    return {c['key']: FILES[conf] | i << 8 for i, c in enumerate(g['clubs'])} if g else {}


def strengths(conf, data=None):
    """{club key: strength} of a confederation's guests: the sum of their first 16 players' prices (as conti rates the
    world's clubs)."""
    g = load(conf, data)
    return {c['key']: sum(int(p['price']) for p in c['players'][:16]) for c in g['clubs']} if g else {}


def record(conf, i, c, base):
    """One club's 684-byte record (squads 'explicit' as the world packs: tactic, kits, lineup, 16 players)."""
    where = f'{conf}.guests.json: {c.get("key")}'
    n = FILES[conf]
    c = {k: v if isinstance(v, (list, dict)) or v is None else str(v) for k, v in c.items()}   # (the csv helpers)
    mkseason._need(0 < len(c['name']) <= 16 and c['name'] == c['name'].upper(), f'{where}: name 1-16 upper case')
    r = bytearray(TEAM_SIZE)
    r[0], r[1] = n, i
    struct.pack_into('>H', r, 2, base + i)
    r[5:22] = c['name'].encode('latin1').ljust(17, b'\0')[:17]
    r[24] = mkseason._num(c, 'tactic', 0, 15, where)
    for col, at in (('kit1', 26), ('kit2', 31)):
        r[at:at + 5] = bytes(mkseason._nums(c, col, 5, 0, 255, where))
    lineup = mkseason._nums(c, 'lineup', 16, 0, 15, where) if c.get('lineup') else list(range(16))
    mkseason._need(sorted(lineup) == list(range(16)), f'{where}: lineup must list 0..15 once each')
    r[60:76] = bytes(lineup)
    r[36:59] = mkseason._sn(c['coach']).encode('latin1').ljust(23, b'\0')[:23] if c.get('coach') else bytes(23)
    rows = c['players']
    mkseason._need(len(rows) >= 16, f'{where}: at least 16 players ({len(rows)})')
    for j, row in enumerate(rows[:16]):
        row = {k: str(v) for k, v in row.items()}
        row.setdefault('club', c['key'])
        r[76 + j * 38:76 + (j + 1) * 38] = mkseason.Pack._explicit_player(None, row)
    return bytes(r)


def build(bases, data=None):
    """{file: TEAM.nnn bytes} for every confederation with a guests file; bases = {file: global base}."""
    out = {}
    for conf in ready(data):
        n = FILES[conf]
        clubs = load(conf, data)['clubs']
        mkseason._need(len(clubs) <= 255, f'{conf}: at most 255 guests ({len(clubs)})')
        out[n] = struct.pack('>H', len(clubs)) + b''.join(record(conf, i, c, bases[n]) for i, c in enumerate(clubs))
    if POOL in bases:
        import worldpool
        out[POOL] = worldpool.pool_team_file(pool_data(), bases[POOL])
    return out


def world():
    """The career world whose continental cups take the guests (World 2026-27's packs), or None."""
    return next((pk.world for pk in mkseason.packs() if pk.meta.get('id', '').startswith('world-2026-27-')), None)


def files():
    """The guest team files of this build (the confederations with a guests file; none without World 2026-27)."""
    return [FILES[c] for c in ready()] + ([POOL] if pool_data() else []) if world() is not None else []


def alloc():
    """{file: global base} of the guest files (integrator's option b, 2026-10-20): ranges of global numbers that world
    world() never loads - not its packs' or national pack's clubs, not the reserved 1730..1849 (career marks, world
    byte, the saved SA block; its pool 190 / off-file pools 253 sit there too) - below bigtables.LIMIT: numbers of
    1996-97 files that world never loads. Asserted at the build: enough room, no overlap."""
    import bigtables
    w = world()
    used = set(range(1730, 1850))
    for pk in mkseason.packs() + mkseason.nationals():
        if pk.world == w:
            for key, (f, base) in pk.files.items():
                used.update(range(base, base + pk.count.get(key, 0)))
    out = {}
    for n, k in counts().items():
        start = next((g for g in range(bigtables.LIMIT - k + 1) if not used & set(range(g, g + k))), None)
        mkseason._need(start is not None, f'guests file {n}: no {k} free global numbers in world {w} below '
                                          f'{bigtables.LIMIT}')
        out[n] = start
        used.update(range(start, start + k))
    return out


def counts():
    """{file: clubs} of the guest files."""
    if world() is None:
        return {}
    return {**{FILES[c]: len(load(c)['clubs']) for c in ready()}, **({POOL: 1} if pool_data() else {})}   # (the pool:
                                                                                        # one global number)


def team_files():
    """{'<stem>.nnn': data} of the guest files (the world's namespace stem: TEAM, or TMWn in a multi-world build)."""
    if not files():
        return {}
    stem = mkseason.ns_stem(world()).upper()
    return {'%s.%03d' % (stem, n): data for n, data in build(alloc()).items()}
