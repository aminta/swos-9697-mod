"""Season packs: historic seasons from data files (phase A, 2026-10-09).

A season pack is a folder (packs/<id>/) with no code, only data:
  pack.json    competitions, team files, rules, squad building, which club plays which European cup
  clubs.csv    key, name (SWOS, <= 16 chars), coach, country (code), file (a key of pack.json 'files'),
               template, target, kit, source (provenance: the source's club name)
  players.csv  club, name, role (G/D/M/A; '?' = no known name, a filler) — in squad order
  ties.csv     competition, round, home, away, winner — every tie of every cup; a bye is a row with no away club
               (round 1); the winner is empty in the final

The compiler is deterministic: the same pack gives the same TEAM files and the same exe bytes. It replaces the hand
written ddr89.py / euro8889.py of 2.6 (the DDR 1988-89 is now packs/ddr-1988-89, byte-identical output).

Engine facts used here (see the hex manual, chapter 17):
- a country's team count = teamsCountryNumbers[n+1] - [n]: a single-league country must hold exactly its league, so
  cup-only clubs live in their own file ('cuponly');
- Season menu: CLASSIC SEASONS = pseudo-continent 97, listing the packs' countries;
- InitNewSeason: the country table [league, -2, cup, <European cup>, -1] fills slot 0, 1, 2; euro_slot2 swaps slot 2
  for the cup of the first human-controlled club of the league that played in Europe (or skips it);
- cups are fixed team lists with fixed draws per round (historic.DRAWS): the real bracket if the real winners win.

Usage:
  python3 tools/mkseason.py check packs/ddr-1988-89     validate + summary
"""
import csv
import json
import os
import random
import re
import struct
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
PACKS = os.path.join(ROOT, 'packs')
NATIONAL = 'national'                   # packs/<world>/national: the world's national teams (NationalPack)
WORLDS = ['europe-1984-85']                        # career worlds: packs/<world>/<country> (3.0: Europe 1984-85)
ENABLED = (os.environ['SEASON_PACKS'].split(',') if 'SEASON_PACKS' in os.environ else   # packs built into the mod,
           ['ddr-1988-89', 'italia-1947-48', 'world-cup-1934'] + [os.path.join(PACKS, w, c) for w in WORLDS                 # in this order
                              for c in sorted(os.listdir(os.path.join(PACKS, w)))
                              if not c.startswith('.') and c != NATIONAL])
                                        # (a name in packs/ or a path; SEASON_PACKS only for test builds)
TEAM_SIZE = 684
SEASONS = 97                            # pseudo-continent 'classic seasons' of the Season menu
SEASONS_NAMES = {'it': b'STAG. STORICHE', 'en': b'CLASSIC SEASONS', 'fr': b"SAISONS D'ANTAN", 'de': b'SAISONKLASSIKER'}
SEASONS_REC = [None]                    # obj2 offset of its countriesTable record (historic.hist_names colours it)
CAREERS = 98                            # pseudo-continent 'classic careers' of the career team selector
CAREERS_NAMES = {'it': b'CARR. STORICHE', 'en': b'CLASSIC CAREERS', 'fr': b"CARR. D'ANTAN", 'de': b'KLASS. KARRIERE'}
CAREERS_REC = [None]
WCONT_IDS = {}                          # world 2025-26: world n -> [(menu id, [country files], top level)] when the world
CONT_ORDER = ['europe', 'south_america', 'north_america', 'asia', 'africa', 'oceania']   # spans several continents
OTHER_NAMES = {'it': b'ALTRE NAZIONI', 'en': b'OTHER NATIONS', 'fr': b'AUTRES PAYS', 'de': b'WEITERE LAENDER'}
WCONT_MAX = int(os.environ.get('WCONT_MAX', 44))                             # countries a continent list of a world holds (more exits to DOS)
CONT_NAT = {'europe': 80, 'africa': 81, 'south_america': 82, 'north_america': 83, 'asia': 84, 'oceania': 85}
WMENU = 200                             # a world's entry in the CLASSIC CAREERS list: pseudo-continent 200 + world number
                                        # (its countries), named by the root pack's world_cups.name
CAREER_DATA = [None]                    # obj1 pages of the career packs' structs (patch.py, only with worlds)
CAREER_DATA_SIZE = 0x2000                # grows to 3 pages for a big world (career_data_pages)


def career_data_pages():
    """obj1 pages of the career packs' structs: 2, or 3 when the worlds hold more than ~75 country packs (~105 B
    each; world 2026-27: 87)."""
    n = sum(len(pks) for pks in worlds().values())
    if not multi_ns():
        return 3 if n * 105 > 0x2000 else 2
    ns = len(worlds()) * 151 * 10 + 512         # several worlds: + the namespaces' rows (ns_emit)
    return max(2, -(-(n * 105 + ns) // 0x1000))


CAREER_CAVE = [None]                    # obj1 page of the career world code (patch.py adds it when worlds exist)
CAREER_CAVE_SIZE = 0x2000               # 3.1: two pages (patch.py; three with several worlds, cave_pages)
ROUND = {'two_legs': 0x94, 'single': 0x14, 'single_et': 0x54}   # knockout round byte: two legs (away goals),
                                                                 # single match, single match + extra time/penalties
# tourney packs (3.2, CLASSIC TOURNEYS): matches of a knockout stage = the legs byte of a worldCup-layout stage (as the
# World Cup 1982 / Mitropa 1934 / FA Cup 1871-72 of historic.py). *_replay: a draw (on aggregate) is replayed, a drawn
# replay is decided by a coin toss (historic coin_draw): those tourneys use no penalties at all.
MATCHES = {'single': 0x14, 'single_et': 0x54, 'two_legs': 0x94, 'single_replay': 0x00, 'two_legs_replay': 0x80}
REPLAY = ('single_replay', 'two_legs_replay')
RESERVED_IDS = {0xAD, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5} | set(range(0x6c, 0x7f))   # hand-made contests (historic, finals97,
                                                                               # sacups, cafcups, Australian cup,
                                                                               # uefaq's qualifying ties 7C..7E)
AU_CUP_SIG = bytes((0xAD, 1, 0x2C, 0x28, 0x50))   # SWOS's Australian cup: layout of a 'national' cup
COUNTRY = {'ALB': 0, 'AUT': 1, 'BEL': 2, 'BUL': 3, 'CYP': 5, 'TCH': 6, 'DEN': 7, 'ENG': 8, 'FIN': 12, 'FRA': 13, 'GDR': 14,
           'FRG': 14, 'GRE': 15, 'HUN': 16, 'ISL': 17, 'IRL': 18, 'ITA': 20, 'LUX': 23, 'MLT': 24, 'NED': 25,
           'NIR': 26, 'NOR': 27, 'POL': 28, 'POR': 29, 'ROU': 30, 'URS': 31, 'SCO': 33, 'ESP': 35, 'SWE': 36,
           'SUI': 37, 'TUR': 38, 'WAL': 40, 'YUG': 41}
COUNTRY.update({'CRO': 4, 'CZE': 6, 'GER': 14, 'EST': 10, 'FRO': 11, 'ISR': 19, 'LVA': 21, 'LTU': 22, 'SMR': 32,
                'SVN': 34, 'UKR': 39, 'SRB': 41, 'BLR': 76, 'SVK': 78, 'XEU': 31, 'ALG': 42, 'ARG': 43, 'AUS': 44,
                'BOL': 45, 'BRA': 46, 'CRC': 47, 'CHI': 48, 'COL': 49, 'ECU': 50, 'SLV': 51, 'GUA': 51, 'HON': 51,
                'PAN': 51, 'JPN': 55, 'MEX': 60, 'NZL': 62, 'FIJ': 62, 'SOL': 62, 'PAR': 64, 'PER': 65, 'KSA': 67,
                'RSA': 69, 'URU': 71, 'USA': 73, 'QAT': 75, 'VEN': 77, 'EGY': 79})   # world 2025-26 (phase-0 prototype)   # code -> game country (team file whose clubs give templates)
COUNTRY.update({'RUS': 31, 'KAZ': 31, 'AZE': 31, 'ARM': 31, 'GEO': 31, 'MDA': 30, 'BIH': 41, 'KOS': 0, 'MKD': 41,
                'MNE': 41, 'AND': 35, 'GIB': 8, 'CAN': 73, 'KOR': 55, 'CHN': 55, 'IRN': 67, 'UAE': 67, 'MAR': 42,
                'TUN': 42, 'LIE': 37})                         # world 2026-27 (Transfermarkt): the countries it adds
ROLES = 'GDMA'
BORROW = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}   # slot role -> roles its player may come from


EXPLICIT_POS = ['G', 'RB', 'LB', 'D', 'RW', 'LW', 'M', 'A']        # player byte 26, bits 5-7
EXPLICIT_ROLE = {'G': 'G', 'RB': 'D', 'LB': 'D', 'D': 'D', 'RW': 'M', 'LW': 'M', 'M': 'M', 'A': 'A'}
EXPLICIT_SKIN = {'light': 0, 'ginger': 1, 'dark': 2, 'darkblond': 3}   # bits 3-4 (3: 3.3.0, blond.py)
EXPLICIT_SKILLS = ['pa', 've', 'he', 'ta', 'co', 'sp', 'fi']          # passing, shooting, heading, tackling, ball
                                                                      # control, speed, finishing: nibbles 1-7 of +28


def _num(row, col, lo, hi, where):
    v = (row.get(col) or '').strip()
    _need(v.isdigit() and lo <= int(v) <= hi, f'{where}: {col} must be a number {lo}..{hi}')
    return int(v)


def _nums(row, col, n, lo, hi, where):
    v = (row.get(col) or '').split()
    _need(len(v) == n and all(x.isdigit() and lo <= int(x) <= hi for x in v),
          f'{where}: {col} must be {n} numbers {lo}..{hi} separated by spaces')
    return [int(x) for x in v]


class PackError(Exception):
    pass


def _need(cond, msg):
    if not cond:
        raise PackError(msg)


def _sn(s):
    """SWOS player name: upper case ASCII, the German sharp s as SS (NFKD would drop it)."""
    import c1c2
    return c1c2.swos_name(s.replace('ß', 'ss'))


def _bare(s):
    """Name without the Italian numbering of namesakes (FERRARIS II, MENTI II): sources do not agree on it."""
    return re.sub(r' (I{1,3}|IV|V|VI)$', '', s)


def _norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s.replace('fc', '').replace('-', ''))


def _records(data):
    return [data[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE] for k in range(struct.unpack('>H', data[:2])[0])]


def _shirt_numbers(data):
    """Team file bytes with every shirt number outside 1..99 replaced by the lowest number of 1..16 its club does not
    use (record order): the mod draws 1..99 over the controlled / booked player (shirtnum.py), others not at all.
    Returns (bytes, count)."""
    d, n = bytearray(data), 0
    for k in range(struct.unpack('>H', d[:2])[0]):
        at = [2 + k * TEAM_SIZE + 76 + j * 38 + 2 for j in range(16)]
        free = sorted(set(range(1, 17)) - {d[a] for a in at})
        for a in at:
            if not 1 <= d[a] <= 99:
                d[a] = free.pop(0)
                n += 1
    return bytes(d), n


def _xtra_cap(q, r):
    """An extra player (XTRA.nnn) no better than the weakest of his club's 16 (Davide 2026-10-16: the managed club
    must not be favoured): goalkeeper price <= the lowest keeper price of the record; outfield skill sum and price
    <= the lowest outfield price of the record (skills scaled down in proportion, key-skill marks kept; price = sum)."""
    ps = [r[76 + j * 38:76 + (j + 1) * 38] for j in range(16)]
    gk = q[26] >> 5 == 0
    same = [p[32] for p in ps if (p[26] >> 5 == 0) == gk] or [p[32] for p in ps]
    cap = min(same)
    if gk:
        q[32] = min(q[32], cap)
        return q
    nib = [q[28] & 15] + [q[29 + i // 2] >> (4 * (1 - i % 2)) & 15 for i in range(6)]
    val = [v & 7 for v in nib]
    tot = sum(val)
    if tot > cap:                                  # scaled in proportion: the player's profile stays his own
        exact = [v * cap / tot for v in val]
        val = [int(x) for x in exact]
        for i in sorted(range(7), key=lambda i: (val[i] - exact[i], i))[:cap - sum(val)]:
            val[i] += 1
    nib = [(n & 8) | v for n, v in zip(nib, val)]
    q[28] = (q[28] & 0xF0) | nib[0]
    for i in range(3):
        q[29 + i] = nib[1 + 2 * i] << 4 | nib[2 + 2 * i]
    q[32] = min(q[32], sum(val))
    return q


def _csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class Pack:
    def __init__(self, path):
        self.path = path
        self.meta = json.load(open(os.path.join(path, 'pack.json'), encoding='utf-8'))
        m = self.meta
        _need(m.get('format') == 1, 'pack.json: format must be 1')
        self.files = {k: (v['file'], v['base']) for k, v in m['files'].items()}
        self.clubs = {}
        for row in _csv(os.path.join(path, 'clubs.csv')):
            _need(row['key'] not in self.clubs, f"clubs.csv: duplicate key {row['key']}")
            _need(row['file'] in self.files, f"clubs.csv: {row['key']}: unknown file {row['file']}")
            _need(0 < len(row['name']) <= 16 and row['name'] == row['name'].upper(),
                  f"clubs.csv: {row['key']}: name must be 1-16 upper-case characters")
            _need(m.get('kind') == 'tourney' or row['country'] in COUNTRY,
                  f"clubs.csv: {row['key']}: unknown country code {row['country']}")
            self.clubs[row['key']] = row
        self.players = {k: [] for k in self.clubs}
        self.prows = {k: [] for k in self.clubs}
        for row in _csv(os.path.join(path, 'players.csv')):
            _need(row['club'] in self.players, f"players.csv: unknown club {row['club']}")
            _need(row['role'] in ROLES, f"players.csv: {row['club']} {row['name']}: role must be one of G D M A")
            self.players[row['club']].append((row['name'], row['role']))
            self.prows[row['club']].append(row)
        self.ties = {}
        for row in _csv(os.path.join(path, 'ties.csv')):
            for side in ('home', 'away', 'winner'):
                _need(not row[side] or row[side] in self.clubs, f"ties.csv: unknown club {row[side]}")
            self.ties.setdefault(row['competition'], []).append(row)
        # ordinal of every club in its file (csv order)
        self.where = {}
        count = {}
        for k, c in self.clubs.items():
            n = count.get(c['file'], 0)
            self.where[k] = (self.files[c['file']][0], n)
            count[c['file']] = n + 1
        self.count = count
        self.comps = m['competitions']
        self.kind = m.get('kind', 'season')
        _need(self.kind in ('season', 'career', 'tourney'), "pack.json: kind must be 'season', 'career' or 'tourney'")
        self.world = None
        if self.kind == 'tourney':              # 3.2: CLASSIC TOURNEYS only (no league, no Season / Career entry)
            self.league, self.league_clubs, self.division = None, [], {}
            _need(self.comps and all(c['type'] in ('tourney', 'league') for c in self.comps),
                  "a tourney pack holds competitions of type 'tourney' or 'league' only")
            for c in self.comps:
                self.tourney(c) if c['type'] == 'tourney' else self.round_robin(c)     # validates
            return
        self.league = next(c for c in self.comps if c['key'] == m['season']['league'])
        self.league_clubs = [k for k, c in self.clubs.items() if c['file'] == self.league['clubs']]
        self.division = {k: int(self.clubs[k].get('division') or 0) for k in self.league_clubs}
        divs = self.divisions()
        for d, dv in enumerate(divs):
            n = sum(1 for k in self.league_clubs if self.division[k] == d)
            _need(n == dv['teams'], f"{self.league['key']}: division {d + 1} has {n} clubs in clubs.csv, {dv['teams']} in pack.json")
        _need(sum(dv['teams'] for dv in divs) == len(self.league_clubs), f"{self.league['key']}: clubs outside the divisions")
        par = self.league.get('parallel')          # parallel groups of one level (Serie C 3 x 20): pgroups.py
        if par:
            u, f, n = par.get('upper'), par.get('first'), par.get('count')
            _need(isinstance(u, int) and f == u + 1 and isinstance(n, int) and 2 <= n <= 4 and f + n == len(divs),
                  'league.parallel: {upper, first = upper + 1, count 2..4}, the groups being the last divisions')
            for k in self.league_clubs:
                a = self.clubs[k].get('area') or ''
                _need(a == '' or a in 'ABCD'[:n], f"clubs.csv: {k}: area must be one of {'ABCD'[:n]} (a group of the level)")
        for c in self.comps:
            if c['type'] == 'cup':
                self.bracket(c)          # validates
            _need(not c.get('classic_tourney') or c['type'] == 'league',
                  f"{c['key']}: classic_tourney is for leagues (a cup or a tournament: a tourney pack, see packs/README.md)")
        self.world = m.get('world')
        if self.world is not None:
            _need(self.kind == 'career' and isinstance(self.world, int) and 1 <= self.world <= 50,
                  'pack.json: world must be a number 1..50 (career packs only)')
            pl = m.get('europe_places', {})
            _need(set(pl) <= {'cc', 'cwc', 'uefa'}, 'europe_places: keys cc, cwc, uefa')
            for key, clubs in m.get('first_europe', {}).items():
                # any number of clubs per country (the real first season: a holder that is also champion, a club
                # of a country with no league); world_defs checks each cup's total = places + 1
                _need(key in ('cc', 'cwc', 'uefa'), f'first_europe.{key}: keys cc, cwc, uefa')
                for c in clubs:
                    _need(c in self.league_clubs, f'first_europe.{key}: {c} is not a league club')
        _need(m['season'].get('cup') or not m['season'].get('europe'), 'season: European cups need a national cup')
        for club, cup in m['season'].get('europe', {}).items():
            _need(club in self.league_clubs, f'season.europe: {club} is not a league club')
            _need(club in self.bracket(self.comp(cup))['clubs'], f'season.europe: {club} does not play {cup}')

    def parallel(self):
        """pgroups table: None, or (world, upper, first, [group sizes], [(global number, base division, area group)])
        for every league club (any of them may reach the level). Area: clubs.csv 'area' (A, B, ...), else the club's
        own group, else the middle group."""
        par = self.league.get('parallel') if self.league else None
        if not par or self.world is None:
            return None
        u, f, n = par['upper'], par['first'], par['count']
        divs = self.divisions()
        out = []
        for k in self.league_clubs:
            c = self.clubs[k]
            fl, i = self.where[k]
            base = next(b for fk, (ff, b) in self.files.items() if ff == fl)
            d = self.division[k]
            a = 'ABCD'.index(c['area']) if c.get('area') else d - f if d >= f else n // 2
            out.append((base + i, d, a))
        return self.world, u, f, [divs[f + g]['teams'] for g in range(n)], out

    def divisions(self):
        """League divisions: pack.json 'divisions' [{teams, promoted, relegated, names}], or one division."""
        lg = self.league
        if lg is None:
            return []
        if 'divisions' in lg:
            return lg['divisions']
        return [{'teams': len(self.league_clubs), 'promoted': 0, 'relegated': lg['relegated'], 'names': lg['names']}]

    def comp(self, key):
        return next(c for c in self.comps if c['key'] == key)

    def bracket(self, comp, rounds=None):
        """{'clubs': contest order (round 1 ties, then byes), 'draws': [perm per round], 'byes': n} from ties.csv."""
        key = comp['key']
        rows = self.ties.get(key)
        _need(rows, f'ties.csv: no ties for {key}')
        nr = max(int(r['round']) for r in rows)
        want = len(comp['rounds']) if rounds is None else rounds
        _need(nr == want, f"{key}: {nr} rounds in ties.csv, {want} in pack.json")
        by = {r: [x for x in rows if int(x['round']) == r] for r in range(1, nr + 1)}
        byes = [x['home'] for x in by[1] if not x['away']]
        _need(all(not x['away'] for x in by[1][len(by[1]) - len(byes):]), f'{key}: byes must follow the round 1 ties')
        _need(all(x['away'] for r in range(2, nr + 1) for x in by[r]), f'{key}: byes only in round 1')
        clubs = [x[s] for x in by[1] if x['away'] for s in ('home', 'away')] + byes
        _need(len(set(clubs)) == len(clubs), f'{key}: a club plays twice in round 1')
        draws, prev = [], None
        for r in range(1, nr + 1):
            ties = [x for x in by[r] if x['away']]
            if prev is None:
                draws.append(list(range(2 * len(ties))))
            else:
                perm = []
                for t in ties:
                    for s in ('home', 'away'):
                        _need(t[s] in prev, f"{key} round {r}: {t[s]} did not win round {r - 1}")
                        perm.append(prev.index(t[s]))
                _need(sorted(perm) == list(range(len(prev))), f'{key} round {r}: not every winner plays')
                draws.append(perm)
            for t in ties:
                _need(not t['winner'] or t['winner'] in (t['home'], t['away']),
                      f"{key} round {r}: winner {t['winner']} did not play {t['home']}-{t['away']}")
                _need(bool(t['winner']) == (r < nr), f'{key} round {r}: winner needed in every round but the final')
            prev = [t['winner'] for t in ties] + (byes if r == 1 else [])
        _need(len(draws[-1]) == 2, f'{key}: the last round must be the final (2 clubs)')
        return {'clubs': clubs, 'draws': draws, 'byes': len(byes)}

    # --- TEAM files --------------------------------------------------------------------------------------------------
    def team_files(self):
        out = {}
        self.xtra = {}                                  # file number -> XTRA bytes (explicit squads with "extra")
        for sq in self.meta['squads']:
            builder = {'calibrate': self._calibrate, 'game': self._game, 'explicit': self._explicit,
                       'records': self._records}[sq['method']]
            out.update(builder(sq))
        fixed = 0
        for k in out:
            out[k], n = _shirt_numbers(out[k])
            fixed += n
        if fixed:
            self.log(f'{fixed} shirt numbers outside 1..99 renumbered (shirtnum draws 1..99)')
        return out

    def _empty_record(self, key, template):
        c = self.clubs[key]
        r = bytearray(template)
        f, i = self.where[key]
        r[0], r[1] = f, i
        struct.pack_into('>H', r, 2, self.files[c['file']][1] + i)
        r[25] = self.division.get(key, 0)              # division (0 = top)
        r[5:22] = c['name'].encode('latin1').ljust(17, b'\0')[:17]
        r[36:59] = _sn(c['coach']).encode('latin1').ljust(23, b'\0')[:23] if c['coach'] else bytes(23)
        return r

    def _pools(self, key):
        pools = {c: [] for c in ROLES}
        for who, role in self.players[key]:
            pools[role].append(who)
        return pools

    def _calibrate(self, sq):
        """Clubs on a template record of a source TEAM file (slots, roles, kit); players found in that file by name keep
        their record (only for the files in reuse_ratings), the others get the template slot's skills moved towards
        the club's target strength (average price byte). ratings_from [{source, clubs}]: the players of those clubs
        found by name in another team file (or a CUSTOMS.EDT) keep that record instead."""
        import c1c2

        def players_of(path):
            known = {}
            for r in _records(open(os.path.join(ROOT, path), 'rb').read()):
                for j in range(16):
                    p = r[76 + j * 38:76 + (j + 1) * 38]
                    known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
            return known
        src = _records(open(os.path.join(ROOT, sq['source']), 'rb').read())
        known = players_of(sq['source'])
        extra = {}
        for rf in sq.get('ratings_from', []):
            other = {_bare(n): q for n, q in players_of(rf['source']).items()}
            for key in rf['clubs']:
                _need(key in self.clubs, f'ratings_from: unknown club {key}')
                extra[key] = other
        rng = random.Random(sq['seed'])
        used, fillers = set(), []
        recs = {f: [] for f in sq['files']}
        for key, c in self.clubs.items():
            if c['file'] not in sq['files']:
                continue
            t = src[int(c['template'])]
            r = self._empty_record(key, t)
            if c['kit']:
                r[26:36] = src[int(c['kit'])][26:36]
            for col, at in (('kit1', 26), ('kit2', 31)):         # optional explicit colours (as for 'explicit')
                if c.get(col):
                    r[at:at + 5] = bytes(_nums(c, col, 5, 0, 255, f'clubs.csv: {key}'))
            avg = sum(t[76 + j * 38 + 32] for j in range(16)) / 16
            step = max(-3, min(3, round((int(c['target']) - avg) / 2)))
            pools = self._pools(key)
            nat = {row['name']: row.get('nat') for row in self.prows[key]}     # optional players.csv column
            for j in range(16):
                p = 76 + j * 38
                cls = c1c2.CLASS[t[p + 26] >> 5]
                role = next((x for x in BORROW[cls] if pools[x]), None)
                who = pools[role].pop(0) if role else '?'
                if who == '?':
                    while True:
                        who = f"{rng.choice(sq['filler_first'])} {rng.choice(sq['filler_last'])}"
                        if _sn(who) not in known and who not in used:
                            break
                    fillers.append((c['name'], who))
                used.add(who)
                sname = _sn(who)
                mine = extra.get(key, {}).get(_bare(sname))
                if mine or (sname in known and c['file'] in sq['reuse_ratings']):
                    q = bytearray(mine or known[sname])
                    q[3:26] = sname.encode('latin1').ljust(23, b'\0')[:23]
                    q[2] = t[p + 2]
                    q[26] = (q[26] & 0x1f) | (t[p + 26] & 0xe0)
                    r[p:p + 38] = q
                else:
                    r[p] = int(nat[who]) if nat.get(who) else sq['nationality']
                    r[p + 3:p + 26] = sname.encode('latin1').ljust(23, b'\0')[:23]
                    c1c2.level_player(r, p, step)
            recs[c['file']].append(bytes(r))
        self.log(f"{'+'.join(sq['files'])}: {sum(map(len, recs.values()))} clubs, invented names {fillers}")
        return {self.files[f][0]: struct.pack('>H', len(v)) + b''.join(v) for f, v in recs.items()}

    def _records(self, sq):
        """Whole teams from a SWOS team file (a TEAM.xxx, a SWOS 2020 CUSTOMS.EDT): clubs.csv 'record' = the team's name
        in sq['source'] (first one of that name); players, kit, tactic, lineup as there; clubs.csv name, and coach when
        given, replace that file's; kit1 / kit2 optional as for 'explicit'."""
        path = os.path.join(ROOT, sq['source'])
        _need(os.path.exists(path), f"squads: {sq['source']} not found (SWOS 2020 files go in orig/swos2020/, not in the "
                                    f"repository)")
        by = {}
        for r in _records(open(path, 'rb').read()):
            by.setdefault(r[5:22].split(b'\0')[0].decode('latin1'), r)
        recs = {f: [] for f in sq['files']}
        for key, c in self.clubs.items():
            if c['file'] not in sq['files']:
                continue
            _need(c.get('record') in by, f"clubs.csv: {key}: record {c.get('record')!r} is not a team of {sq['source']}")
            src = by[c['record']]
            r = self._empty_record(key, src)
            if not c['coach']:
                r[36:59] = src[36:59]
            for col, at in (('kit1', 26), ('kit2', 31)):
                if c.get(col):
                    r[at:at + 5] = bytes(_nums(c, col, 5, 0, 255, f'clubs.csv: {key}'))
            recs[c['file']].append(bytes(r))
        self.log(f"{'+'.join(sq['files'])}: {sum(map(len, recs.values()))} teams from {sq['source']}")
        return {self.files[f][0]: struct.pack('>H', len(v)) + b''.join(v) for f, v in recs.items()}

    def round_robin(self, c):
        """A tourney pack's league (3.2): every club of its file plays every other once (games 1) or home and away
        (games 2); clubs, id, names, win_points, games, dates_from (the country whose league calendar it copies)."""
        w = f"{c['key']}:"
        _need(c.get('clubs') in self.files, f"{w} clubs must be a key of files")
        n = self.count.get(c['clubs'], 0)
        _need(3 <= n <= 24, f'{w} 3 to 24 clubs ({n})')
        _need(c.get('games') in (1, 2), f'{w} games 1 (one match per pair) or 2 (home and away)')
        _need(isinstance(c.get('win_points'), int) and 1 <= c['win_points'] <= 9, f'{w} win_points 1..9')
        _need(isinstance(c.get('dates_from', 14), int), f'{w} dates_from: a country number')
        c.setdefault('dates_from', 14)
        _need(re.fullmatch(r'[0-9A-F]{2}', c.get('id', '')) and int(c['id'], 16) >= 0x80
              and int(c['id'], 16) not in RESERVED_IDS, f'{w} id: a free contest id (hex, 80..FE, see packs/README.md)')
        for lg, nm in c['names'].items():
            _need(len(nm) == 2 and all(x == x.upper() for x in nm) and len(nm[1]) <= 16 and len(nm[0]) <= 30,
                  f'{w} names.{lg}: [long name (<= 30), short name (<= 16)], upper case')
        _need(sum(1 for x in self.files.values() if x[0] == self.files[c['clubs']][0]) == 1, w)
        return n

    def tourney(self, c):
        """A CLASSIC TOURNEYS competition (worldCup layout, historic.py): {'clubs': contest order, 'stages': the 26 bytes
        from header +0Eh, 'draws': [perm], 'coin': replays decided by a coin toss}.
        pack.json: key, type 'tourney', id, clubs (a files key), names, win_points, draw ('fixed' or 'random'), stages:
          {"type": "groups", "teams": 24, "groups": 6}                 round robin, one match per pair
          {"type": "knockout", "teams": 16, "matches": "single"}      MATCHES; the last stage: knockout of 2 (final)
          {"type": "third_place", "matches": "single"}                the semi-final losers (before the final)
          "from": ["1A", "2B", ...] on the stage after a group stage: where each qualifier goes (1A = winner of group
          A); qualifiers otherwise come in the game's order (1st of every group A.., then 2nd ...).
        Order of the clubs: ties.csv round 1 when the tourney starts with a knockout and has ties (the real bracket:
        every round of ties.csv must follow from the winners), else clubs.csv order (groups: A first)."""
        key = c['key']
        w = f'{key}:'
        _need(c.get('clubs') in self.files, f"{w} clubs must be a key of files")
        _need(isinstance(c.get('win_points'), int) and 1 <= c['win_points'] <= 9, f'{w} win_points 1..9')
        _need(c.get('draw', 'fixed') in ('fixed', 'random'), f"{w} draw must be 'fixed' or 'random'")
        _need(re.fullmatch(r'[0-9A-F]{2}', c.get('id', '')) and int(c['id'], 16) >= 0x80
              and int(c['id'], 16) not in RESERVED_IDS, f'{w} id: a free contest id (hex, 80..FE, see packs/README.md)')
        for lg, nm in c['names'].items():
            _need(len(nm) == 2 and all(x == x.upper() for x in nm) and len(nm[1]) <= 16 and len(nm[0]) <= 30,
                  f'{w} names.{lg}: [long name (<= 30), short name (<= 16)], upper case')
        st = c.get('stages') or []
        _need(2 <= len(st) <= 6, f'{w} 2 to 6 stages (the last one the final)')
        clubs = [k for k, x in self.clubs.items() if x['file'] == c['clubs']]
        _need(len(clubs) <= (40 if os.environ.get('PROTO36') else 32), f'{w} at most 32 teams (CLASSIC TOURNEYS share 32 global numbers)')
        trip, legs, draws, coin, prev = [], [], [], None, None
        nko = sum(1 for x in st if x['type'] == 'knockout')
        ties = st[0]['type'] == 'knockout' and key in self.ties
        if ties:
            br = self.bracket(c, nko)
            _need(not br['byes'], f'{w} no byes in a tourney (every knockout round halves the teams)')
            clubs = br['clubs']
            # the game leaves a round's winners in an order of its own (replays first ...): historic hist_draw sorts
            # them by their place in the contest (flag), so each perm is relative to that order
            rows = sorted(self.ties[key], key=lambda r: int(r['round']))
            sperm, prev = [], None
            for r in range(1, nko + 1):
                tr = [x for x in rows if int(x['round']) == r]
                if prev is not None:
                    order = sorted(prev, key=clubs.index)
                    sperm.append([order.index(x[side]) for x in tr for side in ('home', 'away')])
                prev = [x['winner'] for x in tr]
            _need(sorted(clubs) == sorted(k for k, x in self.clubs.items() if x['file'] == c['clubs']),
                  f"{w} ties.csv round 1 must hold every club of {c['clubs']}")
        lp = bool(c.get('league_phase'))       # UEFA league phase (tools/lp36.py, prototype): 36 in 2 x 18, play-offs, R16
        if lp:
            _need(os.environ.get('PROTO36') and [x.get('teams') for x in st] == [36, 16, 16, 8, 4, 2]
                  and st[0].get('groups') == 2, f'{w} league_phase: stages 36 (2 groups) 16 16 8 4 2 (PROTO36 builds)')
        ko = 0
        for i, x in enumerate(st):
            t = x.get('type')
            n = x.get('teams', 2 if t == 'third_place' else None)
            sw = f'{w} stage {i + 1}:'
            _need(t in ('groups', 'knockout', 'third_place'), f'{sw} type groups, knockout or third_place')
            _need(isinstance(n, int) and n >= 2, f'{sw} teams')
            if i == 0:
                _need(n == len(clubs), f'{sw} {n} teams, {len(clubs)} clubs in {c["clubs"]}')
                _need(t != 'third_place', f'{sw} a tourney cannot start with the third place match')
            elif t == 'third_place':
                _need(prev['type'] == 'knockout' and prev['teams'] == 4 and i == len(st) - 2,
                      f'{sw} third_place comes after the semi-finals (knockout of 4), before the final')
            elif prev['type'] == 'groups':
                _need(n < prev['teams'], f'{sw} fewer teams than the group stage before')
            elif lp and i == 2:
                _need(n == 16 and prev['teams'] == 16, f'{sw} league phase: the round of 16 after the play-offs')
            else:
                last = st[i - 2] if prev['type'] == 'third_place' else prev
                _need(n * 2 == last['teams'], f'{sw} {n} teams: half of the knockout before')
            if t == 'groups':
                g = x.get('groups')
                _need(isinstance(g, int) and g >= 1 and n % g == 0 and n // g >= 2, f'{sw} groups: teams / groups >= 2')
                _need(n // g <= (36 if os.environ.get('PROTO36') else 24), f'{sw} at most 24 teams per group')
                trip += [n, g, n // g]
                legs.append(0)
            else:
                _need(x.get('matches') in MATCHES, f"{sw} matches: one of {', '.join(MATCHES)}")
                _need(t == 'third_place' or n & (n - 1) == 0, f'{sw} a knockout stage needs 2, 4, 8, 16 or 32 teams')
                trip += [n, 0xFF, n] if t == 'third_place' else [n, 0, n]
                legs.append(MATCHES[x['matches']])
                rp = x['matches'] in REPLAY
                _need(coin is None or coin == rp, f'{w} replays (coin toss) and penalties cannot be mixed in one '
                                                 f'tourney: the results screen shows the coin toss for every shoot-out')
                coin = rp
            frm = x.get('from')
            if frm is not None:
                _need(i > 0 and prev['type'] == 'groups', f'{sw} from: only on the stage after a group stage')
                g = prev['groups']
                _need(n % g == 0, f'{sw} from needs the same number of qualifiers from every group')
                labels = [f'{r}{chr(65 + k)}' for r in range(1, n // g + 1) for k in range(g)]
                _need(sorted(frm) == sorted(labels), f"{sw} from must list {' '.join(labels)} once each")
                draws.append((n, [labels.index(q) for q in frm], False))
            elif i == 0:
                draws.append((n, list(range(n)), False))   # keep the order: groups / round 1 ties as listed
            elif prev['type'] != 'groups' and c.get('draw', 'fixed') == 'fixed' and n > 2:
                draws.append((n, list(range(n)), True))    # winners by their place in the contest: tie k = W2k-W2k+1
            if t == 'knockout':
                ko += 1
            prev = dict(x, teams=n)
        _need(st[-1]['type'] == 'knockout' and st[-1]['teams'] == 2, f'{w} the last stage must be the final (knockout of 2)')
        if ties:                                # the real bracket replaces the knockout orders
            sizes = [len(pm) for pm in sperm] + [len(clubs)]
            draws = [d for d in draws if d[0] not in sizes] + [(len(clubs), list(range(len(clubs))), False)]
            draws += [(len(pm), pm, True) for pm in sperm if len(pm) > 2]
        if lp:
            draws = [(36, list(range(36)), False)]  # lp36.lp_draw keeps every later order (the play-offs from lp_gend)
        ns = [d[0] for d in draws]
        _need(len(set(ns)) == len(ns), f'{w} two stages of {ns} teams: the fixed order needs a different team count per '
                                       f'stage (or draw: random)')
        body = bytes([len(st)] + trip + [1])
        _need(len(body) <= 20, w)
        stages = body + bytes(20 - len(body)) + bytes(legs) + bytes(6 - len(legs))
        return {'clubs': clubs, 'stages': stages, 'draws': [(pm, srt) for _, pm, srt in draws], 'coin': bool(coin)}

    def _game(self, sq):
        """Clubs on the record of the same club in the 1996-97 game when there is one (name match >= 0.8 in its country),
        else on a random club of its country; players already in the game (any team file) keep their record, the others
        take the template slot's skills; '?' = a random player of the country."""
        import difflib
        import glob
        import c1c2
        rng = random.Random(sq['seed'])
        known, country_teams = {}, {}
        for f in sorted(glob.glob(os.path.join(ROOT, 'orig', 'DATA', 'TEAM.0[0-9][0-9]'))):
            recs = _records(open(f, 'rb').read())
            country_teams[int(f[-3:])] = recs
            for r in recs:
                for j in range(16):
                    p = r[76 + j * 38:76 + (j + 1) * 38]
                    known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
        out, own = {}, 0
        for fk in sq['files']:
            recs = []
            for key, c in self.clubs.items():
                if c['file'] != fk:
                    continue
                teams = country_teams.get(COUNTRY[c['country']]) or country_teams[14]
                names = [t[5:22].split(b'\0')[0].decode('latin1') for t in teams]
                ratio = lambda k: difflib.SequenceMatcher(None, _norm(c['name']), _norm(names[k])).ratio()
                best = max(range(len(teams)), key=ratio)
                same = ratio(best) >= 0.8
                own += same
                t = teams[best] if same else rng.choice(teams)
                r = self._empty_record(key, t)
                pools = self._pools(key)
                filler = [p for tt in teams for p in [tt[76 + j * 38:76 + (j + 1) * 38] for j in range(16)]]
                for j in range(16):
                    p0 = 76 + j * 38
                    cls = c1c2.CLASS[t[p0 + 26] >> 5]
                    role = next((x for x in BORROW[cls] if pools[x]), None)
                    who = pools[role].pop(0) if role else '?'
                    if who == '?':
                        q = bytearray(rng.choice(filler))
                    else:
                        pname = _sn(who)
                        if pname in known:
                            q = bytearray(known[pname])
                        else:
                            q = bytearray(t[p0:p0 + 38])
                            q[3:26] = pname.encode('latin1').ljust(23, b'\0')[:23]
                    q[2] = t[p0 + 2]
                    q[26] = (q[26] & 0x1f) | (t[p0 + 26] & 0xe0)
                    r[p0:p0 + 38] = q
                recs.append(bytes(r))
            out[self.files[fk][0]] = struct.pack('>H', len(recs)) + b''.join(recs)
        self.log(f"{'+'.join(sq['files'])}: {sum(self.count[f] for f in sq['files'])} clubs, {own} on their own 1996-97 record")
        return out

    def _explicit(self, sq):
        """Every byte from the pack: clubs.csv tactic, kit1, kit2, lineup; players.csv (16 per club, in record order)
        number, position, nat, skin, the 7 skills and price (see EXPLICIT_*). squads "extra": E (1..16): rows 17..16+E
        of a club go to XTRA.nnn, the players the managed club of a career gets beyond its 16 (xtra.py)."""
        out = {}
        extra = sq.get('extra', 0)
        _need(isinstance(extra, int) and 0 <= extra <= 16, 'squads "extra" must be 0..16')
        for fk in sq['files']:
            recs, blocks = [], {}
            for key, c in self.clubs.items():
                if c['file'] != fk:
                    continue
                r = self._empty_record(key, bytes(TEAM_SIZE))
                where = f'clubs.csv: {key}'
                r[24] = _num(c, 'tactic', 0, 15, where)
                for col, at in (('kit1', 26), ('kit2', 31)):
                    v = _nums(c, col, 5, 0, 255, where)
                    r[at:at + 5] = bytes(v)
                lineup = _nums(c, 'lineup', 16, 0, 15, where)
                _need(sorted(lineup) == list(range(16)), f'{where}: lineup must list 0..15 once each')
                r[60:76] = bytes(lineup)
                rows = self.prows[key]
                _need(16 <= len(rows) <= 16 + extra, f'players.csv: {key}: explicit squads need 16 players'
                      + (f' + at most {extra} more (squads "extra")' if extra else '') + f' ({len(rows)})')
                for j, row in enumerate(rows[:16]):
                    r[76 + j * 38:76 + (j + 1) * 38] = self._explicit_player(row)
                more = [_xtra_cap(bytearray(self._explicit_player(row)), r) for row in rows[16:]]
                used = {r[76 + j * 38 + 2] for j in range(16)}
                for q in more:                         # extras: numbers 1..99 (shirtnum), else a free one from 17
                    if not 1 <= q[2] <= 99 or q[2] in used:
                        q[2] = min(set(range(17, 100)) - used)
                    used.add(q[2])
                if more:
                    blocks[r[1]] = [bytes(q) for q in more]
                recs.append(bytes(r))
            out[self.files[fk][0]] = struct.pack('>H', len(recs)) + b''.join(recs)
            if blocks:                             # XTRA.nnn only for a file with extra players
                import xtra
                self.xtra[self.files[fk][0]] = xtra.build(blocks, len(recs), extra)
        self.log(f"{'+'.join(sq['files'])}: {sum(self.count[f] for f in sq['files'])} clubs, explicit records")
        return out

    def _explicit_player(self, row):
        """38 bytes of one explicit players.csv row."""
        w = f"players.csv: {row['club']} {row['name']}"
        q = bytearray(38)
        pos = row.get('position', '')
        _need(pos in EXPLICIT_POS, f'{w}: position must be one of {" ".join(EXPLICIT_POS)}')
        _need(EXPLICIT_ROLE[pos] == row['role'], f"{w}: position {pos} is not role {row['role']}")
        _need(row.get('skin', '') in EXPLICIT_SKIN, f'{w}: skin must be one of {" ".join(EXPLICIT_SKIN)}')
        q[0] = _num(row, 'nat', 0, 255, w)
        q[2] = _num(row, 'number', 1, 255, w)
        q[3:26] = _sn(row['name']).encode('latin1').ljust(23, b'\0')[:23]
        q[26] = EXPLICIT_POS.index(pos) << 5 | EXPLICIT_SKIN[row['skin']] << 3
        nib = [0]
        for sk in EXPLICIT_SKILLS:
            v = row.get(sk, '').strip()
            key_skill = v.endswith('*')
            v = v.rstrip('*')
            _need(v.isdigit() and int(v) <= 7, f'{w}: {sk} must be 0..7 (a trailing * marks a key skill)')
            nib.append(int(v) | (8 if key_skill else 0))
        for i in range(4):
            q[28 + i] = nib[2 * i] << 4 | nib[2 * i + 1]
        q[32] = _num(row, 'price', 0, 49, w)
        return bytes(q)

    def log(self, s):
        print(f"pack {self.meta['id']}: {s}")

    # --- exe ---------------------------------------------------------------------------------------------------------
    def draws(self):
        """historic.DRAWS entries (contest id, permutation), cups in pack order."""
        if self.kind == 'tourney':
            return [(int(c['id'], 16), pm, srt) for c in self.comps if c['type'] == 'tourney'
                    for pm, srt in self.tourney(c)['draws']]
        return [(int(c['id'], 16), perm) for c in self.comps if c['type'] == 'cup' for perm in self.bracket(c)['draws']]

    def bye_cups(self):
        """[(contest id, world or 0, clubs, byes)] of the cups with first-round byes (lib97 BYE_TAB)."""
        return [(int(c['id'], 16), self.world or 0, len(self.bracket(c)['clubs']), self.bracket(c)['byes'])
                for c in self.comps if c['type'] == 'cup' and self.bracket(c)['byes']]

    def team_bytes(self, clubs):
        return b''.join(bytes(self.where[k]) for k in clubs)


class NationalPack(Pack):
    """A world's national teams (3.1): explicit squads only, one team file per 1996-97 national file (TEAM.080-085)
    with the same ordinals. pack.json: world, files {key: {file, base, as}} (as = the game's national file it stands
    for: the records say 'as', so global numbers and every (file, ordinal) reference stay the game's; the world's
    career loads TEAM.<file> instead of TEAM.<as>, careerworld w_tfile), squads [{files, method: explicit}]."""

    def __init__(self, path):
        self.path = path
        self.meta = m = json.load(open(os.path.join(path, 'pack.json'), encoding='utf-8'))
        _need(m.get('format') == 1 and m.get('kind') == 'national', f'{path}: pack.json: format 1, kind national')
        self.kind, self.world = 'national', m.get('world')
        _need(isinstance(self.world, int) and 1 <= self.world <= 50, f'{path}: world must be a number 1..50')
        self.files = {k: (v['file'], v['base']) for k, v in m['files'].items()}
        self.as_file = {v['file']: v['as'] for v in m['files'].values()}
        off = {f - a for f, a in self.as_file.items()}
        _need(sorted(self.as_file.values()) == list(range(80, 86)) and len(off) == 1,
              f'{path}: files must stand for the national files 80..85, in order (as = file - constant)')
        _need(all(sq['method'] == 'explicit' for sq in m['squads']), f'{path}: squads: method explicit only')
        self.clubs, self.prows = {}, {}
        for row in _csv(os.path.join(path, 'clubs.csv')):
            _need(row['key'] not in self.clubs and row['file'] in self.files, f"clubs.csv: {row['key']}: key / file")
            _need(0 < len(row['name']) <= 16 and row['name'] == row['name'].upper(),
                  f"clubs.csv: {row['key']}: name must be 1-16 upper-case characters")
            self.clubs[row['key']], self.prows[row['key']] = row, []
        for row in _csv(os.path.join(path, 'players.csv')):
            _need(row['club'] in self.prows, f"players.csv: unknown club {row['club']}")
            self.prows[row['club']].append(row)
        self.where, self.count = {}, {}
        for k, c in self.clubs.items():
            n = self.count.get(c['file'], 0)
            self.where[k] = (self.files[c['file']][0], n)
            self.count[c['file']] = n + 1
        self.division, self.comps, self.ties = {}, [], {}
        self.nations = {}                       # nations.csv: (game file, ordinal) -> code, nat, home, unused
        np_ = os.path.join(path, 'nations.csv')
        for row in (_csv(np_) if os.path.exists(np_) else []):
            _need(row['key'] in self.clubs, f"nations.csv: unknown team {row['key']}")
            f, i = self.where[row['key']]
            self.nations[(self.as_file[f], i)] = row

    def word(self, key):
        """The game's team word of a national team: file (80..85) | ordinal << 8."""
        _need(key in self.where, f"{self.path}: national: unknown team {key}")
        f, i = self.where[key]
        return self.as_file[f] | i << 8

    def competitions(self):
        """pack.json 'national' (3.1): the world's national competitions as team words, validated."""
        n = self.meta.get('national')
        if not n:
            return None
        cyc = []
        for c in n['cycles']:
            g = {}
            for k in ('wcq', 'ecq'):
                _need(len(c[k]) <= 8, f"national {c['years']}: {k}: at most 8 groups")
                g[k] = [(take, [self.word(t) for t in teams]) for take, teams in c[k]]
                for j, (take, teams) in enumerate(g[k]):
                    _need(len(teams) <= (4 if j == 7 else 6) and take <= len(teams),
                          f"national {c['years']}: {k} group {j + 1}: at most {4 if j == 7 else 6} teams, places <= teams")
            ec = 1 + sum(t for t, _ in g['ecq'])
            _need(ec == n['ec_teams'], f"national {c['years']}: European Championship: host + {ec - 1} places != {n['ec_teams']}")
            direct = [self.word(t) for t in c['wc_direct']]
            wc = 2 + sum(t for t, _ in g['wcq'])
            _need(wc + len(direct) >= n['wc_teams'] + 3,
                  f"national {c['years']}: World Cup: holder, host, {wc - 2} places, {len(direct)} direct: too few spares")
            cyc.append({'wc_host': self.word(c['wc_host']), 'ec_host': self.word(c['ec_host']), 'direct': direct, **g})
        _need(n['wc_teams'] == 24 and n['ec_teams'] == 8, 'national: wc_teams 24 and ec_teams 8 (the formats built)')
        return {'holder': self.word(n['wc_holder']), 'points': n['win_points'], 'wc_teams': n['wc_teams'],
                'ec_teams': n['ec_teams'], 'cycles': cyc}

    def nat_base(self):
        """Physical team file that stands for TEAM.080."""
        return next(f for f, a in self.as_file.items() if a == 80)

    def _empty_record(self, key, template):
        r = super()._empty_record(key, template)
        r[0] = self.as_file[r[0]]
        return r

    def divisions(self):
        return []

    def draws(self):
        return []

    def bye_cups(self):
        return []


def nationals():
    """National team packs of the career worlds (packs/<world>/national)."""
    if not hasattr(nationals, 'cache'):
        if 'SEASON_PACKS' in os.environ:        # test builds: the listed folders named 'national'
            paths = [x for x in ENABLED if os.path.basename(x.rstrip(os.sep)) == NATIONAL]
        else:
            paths = [os.path.join(PACKS, w, NATIONAL) for w in WORLDS if os.path.isdir(os.path.join(PACKS, w, NATIONAL))]
        nationals.cache = [NationalPack(x) for x in paths]
    return nationals.cache


def packs():
    if not hasattr(packs, 'cache'):
        packs.cache = [Pack(x if os.sep in x else os.path.join(PACKS, x)) for x in ENABLED
                       if os.path.basename(x.rstrip(os.sep)) != NATIONAL]
    return packs.cache


def team_files():
    """{file number: TEAM.nnn data} of the packs outside worlds and of the worlds named 'team' (ns_stem)."""
    out = {}
    for pk in packs() + nationals():
        if pk.world is None or ns_stem(pk.world) == 'team':
            out.update(pk.team_files())
    return out


def xtra_files():
    """The XTRA files of the packs whose explicit squads have "extra" players: {name: bytes}, name = XTRA.nnn (nnn =
    the club's team file), XTWn.nnn for a world with a namespace of its own (ns_stem; careerworld w_ns_set points
    xtra.py's XTRA_NAMEP at data\\xtwN.nnn while that world is current)."""
    out = {}
    for pk in packs():
        if not hasattr(pk, 'xtra'):
            pk.team_files()
        stem = 'XTRA' if pk.world is None or ns_stem(pk.world) == 'team' else 'XTW%d' % pk.world
        for n, data in pk.xtra.items():
            out['%s.%03d' % (stem, n)] = data
    return out


def ns_team_files():
    """{'TMWn.nnn': data}: the team files of the worlds with a namespace of their own (several worlds in the build)."""
    out = {}
    for pk in packs() + nationals():
        if pk.world is not None and ns_stem(pk.world) != 'team':
            for n, data in pk.team_files().items():
                out['%s.%03d' % (ns_stem(pk.world).upper(), n)] = data
    return out


def multi_ns():
    """Several career worlds in the build: each has its own country namespace (numbers 101..251 per world, swapped
    into countriesTable / competitionsTable / teamsCountryNumbers by careerworld w_ns_set)."""
    return len(worlds()) > 1


def ns_base():
    """The world whose namespace is in the exe's static tables (the lowest; its team files keep the name TEAM.nnn)."""
    return min(worlds()) if worlds() else None


def ns_stem(w):
    """Team file name stem of world w (8.3: data/<stem>.nnn): 'team' for the base world (and for a build with one
    world: old installs and saves stay valid), 'tmwN' for the other worlds of a multi-world build."""
    if not multi_ns() or w == ns_base():
        return 'team'
    _need(w <= 9, f'world {w}: team file stem tmw{w} (worlds 1..9 only)')
    return 'tmw%d' % w


def ns_files(w):
    """Team file numbers of world w (its packs and its national pack): the files named by its stem."""
    return sorted({f for pk in packs() + nationals() if pk.world == w for f, _ in pk.files.values()})


def draws():
    """Fixed draws of the packs outside career worlds (one contest id each in the whole build)."""
    return [d for pk in packs() if pk.world is None for d in pk.draws()]


def world_draws():
    """{world: fixed draws of its packs}: a world's cup ids are its own (worlds never run together), so historic's
    table puts each world's draws after a filter record [1, 0, world] matched against the career's world byte."""
    out = {}
    for pk in packs():
        if pk.world is not None:
            out.setdefault(pk.world, []).extend(pk.draws())
    return out


def parallel_tables():
    """pgroups: the countries of the worlds with parallel groups (Pack.parallel)."""
    return [t for pk in packs() for t in [pk.parallel()] if t]


def bye_cups():
    return [b for pk in packs() for b in pk.bye_cups()]


def league_phase_cups():
    """[(contest id, countries of the clubs in contest order)] of the tourneys with league_phase (lp36 prototype)."""
    out = []
    for pk in packs():
        for c in pk.comps:
            if pk.kind == 'tourney' and c['type'] == 'tourney' and c.get('league_phase'):
                out.append((int(c['id'], 16), [pk.clubs[k]['country'] for k in pk.tourney(c)['clubs']]))
    return out


def league_phase_worlds():
    """Contest ids (the game's cups: 0 Champions Cup, 1 Cup Winners' Cup, 2 UEFA Cup) some world plays as a league
    phase (2: the Conference League format, 6 matches)."""
    import careerworld
    return sorted({k for w in world_defs() for k, key in ((0, 'cc'), (1, 'cwc'), (2, 'uefa'))
                   if w['cups'][key][0] == careerworld.LP_ROUNDS})


def tourneys():
    """The tourney packs' competitions for historic.patch (CLASSIC TOURNEYS after the hand-made ones): [{id, names,
    win_points, file, base, stages, pairs, coin}]."""
    out = []
    for pk in packs():
        if pk.kind != 'tourney':
            continue
        for c in pk.comps:
            if c['type'] != 'tourney':
                continue                        # round robins: _tourney_leagues
            t = pk.tourney(c)
            f, base = pk.files[c['clubs']]
            out.append(dict(id=int(c['id'], 16), names=c['names'], win_points=c['win_points'], file=f, base=base,
                            stages=t['stages'], pairs=pk.team_bytes(t['clubs']), coin=t['coin']))
    return out


def file_numbers():
    return sorted(f for pk in packs() + nationals() for f, _ in pk.files.values())


def base_of(n):
    """First global number of a pack team file named TEAM.nnn (None if n is not one)."""
    for pk in packs() + nationals():
        if pk.world is not None and ns_stem(pk.world) != 'team':
            continue
        for f, b in pk.files.values():
            if f == n:
                return b
    return None


def worlds():
    """Historic career worlds: {number: [career packs of that world, ENABLED order]}."""
    out = {}
    for pk in packs():
        if pk.world is not None:
            out.setdefault(pk.world, []).append(pk)
    return out


def _first_europe(pk, holders=None):
    """First-season European clubs of a world country per cup: pack.json first_europe, else the league order
    (Champions Cup first, then Cup Winners' Cup, then UEFA Cup). holders ({cup: n}, the world's root pack): it also
    fills the places the holders take from season 2 on."""
    pl, fe = dict(pk.meta.get('europe_places', {})), pk.meta.get('first_europe', {})
    if holders:
        pl = {k: pl.get(k, 0) + holders[k] for k in ('cc', 'cwc', 'uefa')}
    order = iter(sorted(pk.league_clubs, key=lambda k: pk.division[k]))   # top division first, table order
    taken = {c for v in fe.values() for c in v}
    out = {}
    for key in ('cc', 'cwc', 'uefa'):
        if key in fe:
            out[key] = fe[key]
        else:
            out[key] = []
            for _ in range(pl.get(key, 0)):
                c = next(x for x in order if x not in taken)
                taken.add(c)
                out[key].append(c)
    return out


def world_defs():
    """[{n, countries, places, cups: {key: (round bytes, [(file, ordinal)])}, clubs: {key: [(pack, club)]}, tmd}]."""
    import careerworld
    out = []
    for n, pks in sorted(worlds().items()):
        roots = [pk for pk in pks if 'world_cups' in pk.meta]
        _need(len(roots) == 1, f'world {n}: exactly one pack must have world_cups')
        wc = roots[0].meta['world_cups']
        w = {'n': n, 'countries': [pk.files[pk.league['clubs']][0] for pk in pks], 'places': {}, 'cups': {},
             'clubs': {}, 'tmd': 'WORLD%02d.TMD' % n, 'pool': None}
        if roots[0].meta.get('pool'):                     # its foreign market (worldpool.py): POOLnn.DAT
            src = os.path.join(roots[0].path, roots[0].meta['pool'])
            _need(os.path.getsize(src) == 900 * 58, f'world {n}: pool {src}: 900 records of 58 bytes needed')
            w['pool'] = ('POOL%02d.DAT' % n, src)
        _need(isinstance(wc.get('start_year'), int) and 1900 < wc["start_year"] < 2100,
              f'world {n}: world_cups.start_year (first season, e.g. 1984) is needed')
        w['year'] = wc['start_year']
        nat = [x for x in nationals() if x.world == n]
        _need(len(nat) <= 1, f'world {n}: one national pack at most')
        w['nat'] = nat[0].nat_base() if nat else 0     # 0 = the game's national teams
        w['nations'] = nat[0].nations if nat else {}
        w['natcomp'] = nat[0].competitions() if nat else None
        w['codes'] = {pk.clubs[pk.league_clubs[0]]['country']: pk.files[pk.league['clubs']][0] for pk in pks}
        lpw = any(wc.get(k, {}).get('format') == 'league_phase' for k in ('cc', 'cwc', 'uefa'))
        for pk in pks:                          # cseg_93974: the champion, the cup winner, then the top 9's next clubs
            pl = pk.meta.get('europe_places', {})
            if lpw:                             # league-phase world (careerworld.QUAL_ASM): top N, cup winner + next
                _need(pl.get('cc', 0) <= 5 and pl.get('cwc', 0) <= 3 and pl.get('uefa', 0) <= 6 and sum(pl.values()) <= 9,
                      f"{pk.meta['id']}: europe_places at most cc 5, cwc 3, uefa 6, 9 in all (the top 9 of the league)")
                continue
            _need(pl.get('cc', 0) <= 1 and pl.get('cwc', 0) <= 1 and pl.get('uefa', 0) <= 6,
                  f"{pk.meta['id']}: europe_places at most cc 1, cwc 1, uefa 6")
        # holders' places per cup: one each (the game's rule); a league-phase world (2025-26 rules): the Champions
        # League takes its holder and the Europa League winner, the Europa League the Conference League winner
        holders = {'cc': 2, 'cwc': 1, 'uefa': 0} if lpw else {'cc': 1, 'cwc': 1, 'uefa': 1}
        first = {id(pk): _first_europe(pk, holders if pk is roots[0] else None) for pk in pks}
        for key in ('cc', 'cwc', 'uefa'):
            w['places'][key] = [pk.files[pk.league['clubs']][0] for pk in pks
                                for _ in range(pk.meta.get('europe_places', {}).get(key, 0))]
            clubs = [(pk, c) for pk in pks for c in first[id(pk)][key]]
            size = len(clubs)
            _need(size == len(w['places'][key]) + holders[key],
                  f'world {n}: {key}: {size} clubs in the first season, {len(w["places"][key])} places + '
                  f'{holders[key]} holder place(s)')
            if wc.get(key, {}).get('format') == 'league_phase':     # UEFA league phase (lp36): 36 clubs, type 2
                _need(size == 36, f'world {n}: {key}: a league phase has 36 clubs ({size})')
                w['cups'][key] = (careerworld.LP_ROUNDS, [pk.where[c] for pk, c in clubs])
                w['clubs'][key] = clubs
                continue
            _need(2 <= size <= careerworld.MAX[key] and size & (size - 1) == 0,
                  f'world {n}: {key} has {size} clubs (a power of 2, at most {careerworld.MAX[key]})')
            rounds = wc.get(key, {}).get('rounds') or ['two_legs'] * (size.bit_length() - 2) + ['single']
            _need(2 ** len(rounds) == size, f'world {n}: {key}: {len(rounds)} rounds for {size} clubs')
            w['cups'][key] = (bytes(ROUND[x] for x in rounds), [pk.where[c] for pk, c in clubs])
            w['clubs'][key] = clubs
        _need(len({c for key in w['clubs'] for c in w['clubs'][key]}) == sum(len(v) for v in w['clubs'].values()),
              f'world {n}: a club is in two European cups')
        tot = sum(len(v) for v in w['clubs'].values())
        _need(tot <= careerworld.TOTAL_MAX, f'world {n}: {tot} European clubs (at most {careerworld.TOTAL_MAX})')
        # UEFA coefficients (league-phase worlds, uefacoef.py): pack.json uefa_coef = {country: 5 seasons, oldest first;
        # clubs: {club key: coefficient}}
        w['coef'] = {'countries': [], 'clubs': []}
        for pk in pks:
            uc = pk.meta.get('uefa_coef')
            if uc:
                _need(len(uc.get('country', [])) == 5, f"{pk.meta['id']}: uefa_coef.country: 5 seasons")
                w['coef']['countries'].append((pk.files[pk.league['clubs']][0], uc['country']))
                for c, v in uc.get('clubs', {}).items():
                    _need(c in pk.league_clubs, f"{pk.meta['id']}: uefa_coef: {c} is not a league club")
                    w['coef']['clubs'].append((pk.where[c], v))
        out.append(w)
    return out


def world_files():
    """{'WORLDnn.TMD': first-season European clubs of world nn (team-file records, the game sets word +2),
    'POOLnn.DAT': its foreign-market pool when the root pack names one (pack.json 'pool')}."""
    out = {}
    for w in world_defs():
        files = {}
        for pk in packs() + nationals():
            if pk.world == w['n']:
                files.update(pk.team_files())
        recs = []
        for key in ('cc', 'cwc', 'uefa'):
            for pk, c in w['clubs'][key]:
                f, i = pk.where[c]
                recs.append(files[f][2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE])
        out[w['tmd']] = b''.join(recs)
        if w['pool']:
            out[w['pool'][0]] = open(w['pool'][1], 'rb').read()
    return out


def career_file(n):
    """True for the team files of world career packs: their clubs may reuse 1996-97 European global numbers (a world
    career never loads those files)."""
    return any(pk.world is not None and n in (f for f, _ in pk.files.values()) for pk in packs() + nationals())


def shares_base(n):
    """True for the pack files that share their global numbers (only one of them runs in a Season)."""
    return any(pk.files[k][0] == n for pk in packs() for k in pk.meta.get('shared_base_files', []))


HOOK_ASM = '''
season_sel:                             ; replaces `call SelectTeamsFinalMenu` in the season team selector
    push dword [COMP254]
    mov dword [COMP254], SEASON_WORLD
    call SELECT
    pop dword [COMP254]
    ret

cont_check:                             ; ja target of `cmp word [D7], 85`: 97 (classic seasons) is a continent too
    cmp word [D7REG], SEASONS_N
    je CONT_WORLD
    jmp CONT_LAST

euro_slot2:                             ; replaces `mov [A0], eax` before slot 2 is loaded in InitNewSeason
    mov [A0], eax
    pushad
    mov al, [COMPCOUNTRY]
    mov edi, PACK_TAB                   ; per pack with European cups: league file, clubs, 0, 0, map, cup pointers
.p:
    cmp byte [edi], 0xff
    je .ret
    cmp [edi], al
    je .pack
    add edi, 12
    jmp .p
.pack:
    mov esi, [SELTEAMS]
    movzx ecx, word [NUMSEL]
    mov bx, [edi]                       ; bl = league file, bh = its club count
    mov ebp, [edi + 4]
.n:
    test ecx, ecx
    jz .none
    cmp byte [esi + 4], 1               ; computer-controlled
    je .skip
    cmp [esi], bl
    jne .skip
    movzx eax, byte [esi + 1]
    cmp al, bh
    jae .skip
    movzx eax, byte [ebp + eax]         ; 0 = no European cup, else 1-based index into the cup pointers
    test eax, eax
    jnz .found
.skip:
    add esi, 684
    dec ecx
    jmp .n
.found:
    mov edx, [edi + 8]
    mov eax, [edx + eax * 4 - 4]
    mov [A0], eax
.ret:
    popad
    ret
.none:
    popad
    add esp, 4
    jmp SKIP_SLOT2
'''



WMENU_ASM = '''
w_lvl:                                  ; replaces `cmp word [numSelectedTeams], 2` (SelectTeamsFinalMenu shows a
    cmp word [NST], 2                   ; country's leagues at depth 2 only): depth 3 too when the parent list is a
    je .r                               ; world of CLASSIC CAREERS (top of countryStack = WMENU + n)
    cmp word [NST], 3                   ; depth 3+: CLASSIC CAREERS > world (> continent (> OTHER NATIONS ...)) >
    jb .r                               ; country, whenever the parent list is one of a world's (id >= WMENU)
    push eax
    mov eax, [CSP]
    cmp byte [eax - 1], WMENU_N
    jb .no
    cmp eax, eax
    pop eax
    ret
.no:
    or esp, esp
    pop eax
.r:
    ret
'''


CAREER_ASM = '''
career_sel:                             ; replaces `call ChooseTeamsDialog` in SelectTeamToManage (career start)
    push dword [COMP254]
    mov dword [COMP254], CAREER_WORLD
    call CHOOSE
    pop dword [COMP254]
    ret
'''


def _level_site(p):
    """(obj1 offset of `cmp word [numSelectedTeams], 2; jnz` in SelectTeamsFinalMenu, numSelectedTeams, countryStackPtr):
    both from PushContinent (mov eax, [countryStackPtr] ... add word [numSelectedTeams], 1; ret)."""
    d1 = p.le.obj_bytes(1)
    pat = rb'\xa1(.{4})\xa3(.{4})\xa0.{4}\x8b\x35\2\x88\x06\xff\x05\2\xa1\2\xa3\1\x66\x83\x05(.{4})\x01\xc3'
    ms = list(re.finditer(pat, d1, re.S))
    assert len(ms) == 1, len(ms)
    push = ms[0].start()
    nst = p.target(1, ms[0].end() - 6)
    csp = p.target(1, push + 1)
    sites = [m.start() for m in re.finditer(rb'\x66\x83\x3d' + re.escape(ms[0].group(3)) + rb'\x02\x0f\x85', d1)]
    assert len(sites) == 1, sites
    assert d1[sites[0] + 8:sites[0] + 10] == b'\x0f\x85'        # the cmp is 8 bytes, the jnz must stay intact
    return sites[0], nst, csp


def _career_site(p):
    """(obj1 offset of `call ChooseTeamsDialog` in SelectTeamToManage, ChooseTeamsDialog): A1 = 0, D2 = 1 (club teams
    only), D3 = D4 = 0, call, ret."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    pat = (rb'\xc7\x05' + pk(r['A0']) + rb'.{4}\xc7\x05' + pk(r['A0'] + 4) + rb'\x00\x00\x00\x00'
           + rb'\x66\xc7\x05' + pk(r['D7'] - 20) + rb'\x01\x00\x66\xc7\x05' + pk(r['D7'] - 16) + rb'\x00\x00'
           + rb'\x66\xc7\x05' + pk(r['D7'] - 12) + rb'\x00\x00\xe8(.{4})\xc3')
    ms = list(re.finditer(pat, d1, re.S))
    assert len(ms) == 1, len(ms)
    site = ms[0].end() - 6
    return site, site + 5 + struct.unpack('<i', ms[0].group(1))[0]


def _hook_sites(p):
    """(site of `mov [A0], eax` before slot 2, skip target, compCountryNumber, selTeamsPtr, g_numSelectedTeams, regs)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = struct.pack('<I', r['A0'])
    a6 = struct.pack('<I', r['A0'] + 24)
    d0 = struct.pack('<I', r['D7'] - 28)
    d1_ = struct.pack('<I', r['D7'] - 24)
    d2_ = struct.pack('<I', r['D7'] - 20)
    pat = (rb'\x8b\x35' + re.escape(a6) + rb'\x8b\x06\xa3' + re.escape(a0) + rb'\x66\xc7\x05' + re.escape(d0) + rb'\x02\x00'
           + rb'\x66\xc7\x05' + re.escape(d1_) + rb'\x00\x00\x66\xc7\x05' + re.escape(d2_) + rb'\x00\x00\xff\x35' + re.escape(a6)
           + rb'\xe8.{4}\x8f\x05' + re.escape(a6) + rb'(?=\x66\xc7\x05.{4}\x00\x00\x66\xc7\x05)')
    ms = list(re.finditer(pat, d1, re.S))
    assert len(ms) == 1, len(ms)
    site = ms[0].start() + 8                                # the `a3 <A0>` (mov [A0], eax)
    assert d1[site] == 0xa3
    c = re.search(rb'\x8a\x46\x02\xa2' + re.escape(struct.pack('<I', r['D7'])) + rb'\xa2(.{4})', d1, re.S)
    t = re.search(rb'\x66\xa1(.{4})\x66\xa3' + re.escape(d0) + rb'\x66\x83\x2d' + re.escape(d0) + rb'\x01\xa1(.{4})\xa3' +
                  re.escape(a0), d1, re.S)
    return (site, ms[0].end(), struct.unpack('<I', c.group(1))[0], struct.unpack('<I', t.group(2))[0],
            struct.unpack('<I', t.group(1))[0], r)


def _league_body(p, lang, area, comp, c, lfile, divs):
    """A league struct: the calendar of the league of country dates_from, divs [{teams, promoted, relegated, names}]."""
    import sacups
    src_c = c['dates_from']
    gobj, gtab = p.target(2, comp + 4 * src_c)
    lobj, glg = p.target(gobj, gtab)
    lg = p.le.obj_bytes(lobj)[glg:glg + 13]
    assert lg[2] == src_c, lg.hex()
    rel = []
    for dv in divs:
        dn = dv['names'].get(lang) or dv['names']['*']
        rel += [area.add(x.encode('latin1') + b'\0') - sacups.STR_BASE for x in dn]
    hdr = bytes((int(c['id'], 16), 0, lfile, lg[3], lg[4], 9 + 6 * len(divs), 0, 0, 0, len(divs), c['games'],
                 c['win_points'], 0x35))
    return hdr + b''.join(bytes((dv['teams'], dv['promoted'], 0, dv['relegated'], 0, 0)) for dv in divs) \
        + b'\0' + struct.pack(f'<{len(rel)}I', *rel)


def _tourney_leagues(p, lang, area, at, env):
    """Tourney packs' round robins (3.2): a league struct each, its team file a country of its own (record =
    CLASSIC TOURNEYS, team count closed by the next file's base). Returns (cave end, [league offsets])."""
    import countries
    import historic
    d2, ct, tcn, comp, fx2 = env
    out = []
    name = historic.NAMES[lang]
    rec = None
    for pk in packs():
        if pk.kind != 'tourney':
            continue
        for c in pk.comps:
            if c['type'] != 'league':
                continue
            f, base = pk.files[c['clubs']]
            n = pk.count[c['clubs']]
            _need(ct + 4 * f not in fx2 and ct + 4 * (f + 1) not in fx2, f"{pk.meta['id']}: country {f} or {f + 1} is used")
            if rec is None:
                rec = area.add(bytes((countries.CONTINENT['europe'],)) + name + b'\0' + name + b'\0')
            p.add_ptr(2, ct + 4 * f, 2, rec)
            p.put(2, tcn + 2 * f, struct.pack('<H', base))
            p.put(2, tcn + 2 * (f + 1), struct.pack('<H', base + n))     # a league = every club of its country
            names = c['names'].get(lang) or c['names']['*']
            body = _league_body(p, lang, area, comp, c, f, [{'teams': n, 'promoted': 0, 'relegated': 0,
                                                             'names': {'*': names}}])
            p.put(1, at, body)
            out.append(at)
            pk.log(f"exe: tourney league {names[0]} id {c['id']} @ obj1+{at:#x}, {n} clubs, file {f}")
            at = (at + len(body) + 3) & ~3
    return at, out


POOL_IDS = range(190, 200)              # pseudo-countries of the worlds' foreign-market pools (worldpool.py): no world file
NS = {}                                 # several worlds: world -> {country number: {'ct': (obj, off), 'comp': (obj, off),
NS_INFO = {}                            # 'tcn': base}} (its namespace); NS_INFO: where patch() put the tables (ns_emit)


def _tab(p, env, w, kind, n, *val):
    """A country entry (kind 'ct' / 'comp' = countriesTable / competitionsTable pointer, 'tcn' = teamsCountryNumbers
    word): written into the exe, or with several worlds into world w's namespace (ns_emit writes them)."""
    d2, ct, tcn, comp, fx2 = env
    if w is None or not multi_ns():
        if kind == 'tcn':
            p.put(2, tcn + 2 * n, struct.pack('<H', val[0]))
        else:
            p.add_ptr(2, (ct if kind == 'ct' else comp) + 4 * n, *val)
        return
    _need(n < 252 and n not in (SEASONS, CAREERS, 99) and not WMENU <= n <= WMENU + 9 and n not in POOL_IDS,
          f'world {w}: country {n} is a menu id or a pool pseudo-country')
    row = NS.setdefault(w, {}).setdefault(n, {})
    _need(kind == 'tcn' or kind not in row, f'world {w}: country {n} is already used')
    row[kind] = val[0] if kind == 'tcn' else val


def _has_fix(p, objn, off):
    try:
        p.target(objn, off)
        return True
    except AssertionError:
        return False


def ns_emit(p):
    """Several worlds (after every other patch, before save): per world a row per namespace number (countriesTable
    and competitionsTable entries as obj-tagged offsets: bit 30 = obj1, bit 31 = obj2, 0 = none; teamsCountryNumbers
    word) = its own entry, else the build's global one; the base world's rows into the static tables."""
    if not NS_INFO:
        return
    ct, tcn, comp, nums = NS_INFO['ct'], NS_INFO['tcn'], NS_INFO['comp'], NS_INFO['numbers']

    def cur(off):
        if _has_fix(p, 2, off):
            obj, t = p.target(2, off)
            assert obj in (1, 2) and t < 1 << 30
            return obj << 30 | t
        assert bytes(p.get(2, off, 4)) == bytes(4), hex(off)
        return 0
    glob = {n: (cur(ct + 4 * n), cur(comp + 4 * n), struct.unpack('<H', bytes(p.get(2, tcn + 2 * n, 2)))[0]) for n in nums}
    p.put(1, NS_INFO['list_at'], bytes(nums))
    for w, at in NS_INFO['rows_at'].items():
        p.add_ptr(1, NS_INFO['wt_at'] + 4 * w, 1, at)
        rows = b''
        for n in nums:
            r, (gct, gcomp, gtcn) = NS[w].get(n, {}), glob[n]
            for kind, g in (('ct', gct), ('comp', gcomp)):
                _need(kind not in r or g == 0, f'world {w}: country {n} is also a global {kind} entry')
            rows += struct.pack('<IIH', r['ct'][0] << 30 | r['ct'][1] if 'ct' in r else gct,
                                r['comp'][0] << 30 | r['comp'][1] if 'comp' in r else gcomp, r.get('tcn', gtcn))
        p.put(1, at, rows)
    for n, r in NS[ns_base()].items():            # the static tables = the base world's namespace
        for kind, tab in (('ct', ct), ('comp', comp)):
            if kind in r:
                p.add_ptr(2, tab + 4 * n, *r[kind])
        if 'tcn' in r:
            p.put(2, tcn + 2 * n, struct.pack('<H', r['tcn']))
    print(f"exe: country namespaces of worlds {sorted(NS)}: {len(nums)} numbers ({nums[0]}..{nums[-1]}), "
          f"base world {ns_base()}, rows @ obj1+{min(NS_INFO['rows_at'].values()):#x}")


def _patch_pack(pk, p, lang, area, at, env):
    """One pack: country entries, competition structs, country table. Returns (cave end, info for the shared part)."""
    import countries
    import sacups
    d2, ct, tcn, comp, fx2 = env
    m = pk.meta
    lfile, _ = pk.files[pk.league['clubs']]
    button = m.get('button_names', {}).get(lang) or m['button']      # button_names: the country name per language
    rec = area.add(bytes((countries.CONTINENT[m['continent']],)) + button.encode('latin1') + b'\0'
                   + button.encode('latin1') + b'\0')
    # every pack file is a country entry (a club's country is never null); bases in teamsCountryNumbers; the entry
    # after the last own-base file closes its team count (a country's count = next base - its base); shared-base
    # files last: their bases overwrite that closing entry when they follow it
    own = sorted(v for v in pk.files.values() if not shares_base(v[0]))
    for f, base in own + sorted(v for v in pk.files.values() if shares_base(v[0])):
        _need(ct + 4 * f not in fx2 and comp + 4 * f not in fx2, f'{pk.meta["id"]}: country {f} is already used')
        _tab(p, env, pk.world, 'ct', f, 2, rec)
        _tab(p, env, pk.world, 'tcn', f, base)
        if (f, base) == own[-1]:
            _tab(p, env, pk.world, 'tcn', f + 1, base + pk.count[next(k for k, v in pk.files.items() if v[0] == f)])

    ptr = {}
    for c in pk.comps:
        names = c['names'].get(lang) or c['names']['*']
        if c['type'] == 'league':
            body = _league_body(p, lang, area, comp, c, lfile, pk.divisions())
        else:
            br = pk.bracket(c)
            rounds = bytes(ROUND[x] for x in c['rounds'])
            if c['layout'] == 'national':
                lo = d2.find(AU_CUP_SIG)
                assert lo >= 0 and d2.count(AU_CUP_SIG) == 1
                h = bytearray(d2[lo:lo + 14])
                assert h[7] == 0 and h[5] == 0 and d2[lo + 14 + 5] == 0
                gobj, gtab = p.target(2, comp + 4 * c['dates_from'])
                gd = p.le.obj_bytes(gobj)
                k = 8
                while struct.unpack_from('<i', gd, gtab + k - 4)[0] != -2:
                    k += 4
                cobj, gcup = p.target(gobj, gtab + k)
                gc = p.le.obj_bytes(cobj)[gcup:gcup + 5]
                h[2], h[3], h[4] = lfile, gc[3], gc[4]
            else:
                h = bytearray(d2[sacups.unique(d2, sacups.CWC_HDR):][:14])
            h[0], h[10] = int(c['id'], 16), len(br['clubs'])
            h += rounds + b'\0'
            h[5] = len(h) - 5
            h[7] = len(h) + 8 - 7
            rel = [area.add(s.encode('latin1') + b'\0') - sacups.STR_BASE for s in names]
            body = bytes(h) + struct.pack('<II', *rel) + pk.team_bytes(br['clubs'])
        ptr[c['key']] = at
        p.put(1, at, body)
        at = (at + len(body) + 3) & ~3

    s = m['season']
    europe = [c['key'] for c in pk.comps if c['type'] == 'cup' and c['key'] != s.get('cup')]
    p.add_ptr(1, at, 1, ptr[s['league']])       # [league, -2, cup, <European cup>, -1]: slot 2 swapped by euro_slot2
    p.put(1, at + 4, struct.pack('<i', -2))     # no national cup (Italy 1947-48): [league, -2, -1], like Costa Rica
    table = at
    at += 8
    if s.get('cup'):
        p.add_ptr(1, at, 1, ptr[s['cup']])
        at += 4
    if s.get('europe'):
        p.add_ptr(1, at, 1, ptr[s['europe_placeholder']])
        at += 4
    p.put(1, at, struct.pack('<i', -1))
    at += 4
    _tab(p, env, pk.world, 'comp', lfile, 1, table)
    emap = bytearray(len(pk.league_clubs))
    for club, cup in s.get('europe', {}).items():
        emap[pk.league_clubs.index(club)] = europe.index(cup) + 1
    pk.log(f"exe: country {lfile}, " + ', '.join(f"{c['key']} id {c['id']} @ obj1+{ptr[c['key']]:#x}" for c in pk.comps))
    info = dict(kind=pk.kind, file=lfile, n=len(pk.league_clubs), emap=bytes(emap) if s.get('europe') else None,
                cups=[ptr[k] for k in europe], classic=[ptr[c['key']] for c in pk.comps if c.get('classic_tourney')])
    return at, info


def odd_leagues(p):
    """Allow leagues with an odd number of clubs (Italy 1947-48: 21). The league setup of Season/Career traps with
    `test byte [esi+ebx+0Dh], 1; jz ok; int 3; jmp $` (+0Dh = the division's club count, ebx = division * 6), but the
    league engine handles odd sizes (DIY leagues, World Cup 1982 groups of 3: one club rests each round, like
    historic.odd_groups). The jz becomes jmp."""
    d1 = p.le.obj_bytes(1)
    ms = list(re.finditer(rb'\x0f\xb7\x1d[\s\S]{4}\xf6\x44\x1e\x0d\x01\x74\x03\xcc\xeb\xfe', d1))
    assert len(ms) == 1, len(ms)
    p.put(1, ms[0].end() - 5, b'\xeb')
    print(f'exe: odd league sizes allowed (trap obj1+{ms[0].end() - 3:#x})')


def patch(p, lang, area, cave):
    """Every enabled pack into the exe (countries, competitions), then the shared part: CLASSIC SEASONS button with one
    country per pack, season_sel / cont_check / euro_slot2 hook with the packs' European-cup tables.
    Returns (cave end, obj1 offsets of the leagues that are also classic tourneys)."""
    import countries
    import historic
    import nasmcave
    import sacups
    ct, tcn, _, _ = countries.tables(p)
    comp = countries.COMP[0]
    env = (p.le.obj_bytes(2), ct, tcn, comp, {f[1] for f in p.le.fixups() if f[0] == 2})
    ids = {}                                   # a league id may be shared by the packs of one career world, and
    for pk in packs():                         # every world has its own ids (worlds never run together: their cups'
        for c in pk.comps:                     # fixed draws are filtered by the career's world byte, world_draws)
            owner = ('world', pk.world) if pk.world is not None and c['type'] == 'league' else ('pack', pk.meta['id'])
            scope = pk.world                   # None = seasons / tourneys / no-world careers: unique in the build
            users = ids.setdefault(c['id'], {})
            _need(all(s2 is not None and scope is not None and s2 != scope or o == owner for s2, o in users.items())
                  and users.get(scope, owner) == owner, f"contest id {c['id']} used twice")
            users[scope] = owner
            _need(int(c['id'], 16) not in RESERVED_IDS, f"contest id {c['id']} is used by the mod")
    at, infos = cave, []
    cat = CAREER_DATA[0]                       # career packs: own obj1 pages (a world of 30 countries needs ~5 KB)
    for pk in packs():
        if pk.kind == 'tourney':                # historic.patch: CLASSIC TOURNEYS
            continue
        if pk.world is not None:
            cat, info = _patch_pack(pk, p, lang, area, cat, env)
        else:
            at, info = _patch_pack(pk, p, lang, area, at, env)
        infos.append(info)
    if multi_ns():                              # several worlds: their namespaces' rows (filled by ns_emit)
        nums = sorted(set().union(*NS.values()))
        NS_INFO.update(ct=ct, tcn=tcn, comp=comp, numbers=nums, list_at=cat, rows_at={})
        cat = (cat + len(nums) + 3) & ~3
        NS_INFO['wt_at'] = cat                  # dd per world number: its rows (0 = not in the build)
        cat += 4 * (max(worlds()) + 1)
        for w in sorted(NS):
            NS_INFO['rows_at'][w] = cat
            cat += 10 * len(nums)
        cat = (cat + 3) & ~3
    if cat is not None:
        _need(cat <= CAREER_DATA[0] + 0x1000 * career_data_pages(), f'career packs overflow their pages ({cat:#x})')
    at, tleagues = _tourney_leagues(p, lang, area, at, env)
    if any(dv['teams'] % 2 for pk in packs() for dv in pk.divisions()) or \
            any(pk.count[c['clubs']] % 2 for pk in packs() if pk.kind == 'tourney' for c in pk.comps if c['type'] == 'league'):
        odd_leagues(p)

    # Season: CLASSIC SEASONS after the continents (pseudo-continent 97: [-1] + the pack countries + FF; the game reads a
    # country list only for 80..85, so that check also accepts 97). The season selector runs on a world table
    # [worldCup, -1] + continents + 97, swapped in like historic.hist_preset.
    fx2 = env[4]
    assert ct + 4 * SEASONS not in fx2 and comp + 4 * SEASONS not in fx2
    srec = area.add(bytes((countries.CONTINENT['europe'],)) + SEASONS_NAMES[lang] + b'\0' + SEASONS_NAMES[lang] + b'\0')
    SEASONS_REC[0] = srec
    p.add_ptr(2, ct + 4 * SEASONS, 2, srec)
    stab = at
    lst = struct.pack('<i', -1) + bytes(i['file'] for i in infos if i['kind'] == 'season') + b'\xff'
    p.put(1, at, lst)
    at = (at + len(lst) + 3) & ~3
    p.add_ptr(2, comp + 4 * SEASONS, 1, stab)
    wobj, world = p.target(2, comp + 4 * 254)
    wd = p.le.obj_bytes(wobj)
    conts = wd[world + 8:wd.index(b'\xff', world + 8)]
    sworld = at
    p.add_ptr(1, at, *p.target(wobj, world))
    p.put(1, at + 4, b'\xff' * 4 + conts + bytes((SEASONS, 0xff)))
    at = (at + 8 + len(conts) + 2 + 3) & ~3
    careers = [i['file'] for i in infos if i['kind'] == 'career']
    wmenus = []
    if careers:                                 # career team selector: CLASSIC CAREERS (98) after the continents
        assert ct + 4 * CAREERS not in fx2 and comp + 4 * CAREERS not in fx2
        crec = area.add(bytes((countries.CONTINENT['europe'],)) + CAREERS_NAMES[lang] + b'\0' + CAREERS_NAMES[lang] + b'\0')
        CAREERS_REC[0] = crec
        p.add_ptr(2, ct + 4 * CAREERS, 2, crec)
        entries = []                            # a world = one entry (WMENU + n) listing its countries; packs of no
        for pk, i in zip(packs(), infos):       # world stay countries of the list
            if i['kind'] != 'career':
                continue
            if pk.world is None:
                entries.append(i['file'])
            elif WMENU + pk.world not in entries:
                entries.append(WMENU + pk.world)
        for n, pks in sorted(worlds().items()):
            wid = WMENU + n
            _need(wid < 252 and ct + 4 * wid not in fx2 and comp + 4 * wid not in fx2, f'world {n}: menu id {wid} is used')
            root = [pk for pk in pks if 'world_cups' in pk.meta][0].meta['world_cups']
            name = root.get('name', f"{root['start_year']}-{(root['start_year'] + 1) % 100:02d}")
            name = (name.get(lang) or name.get('*') or next(iter(name.values()))) if isinstance(name, dict) else name
            name = name.upper().encode('latin1')
            _need(len(name) <= 20, f'world {n}: world_cups.name longer than 20 characters')
            rec = area.add(bytes((countries.CONTINENT['europe'],)) + name + b'\0' + name + b'\0')
            p.add_ptr(2, ct + 4 * wid, 2, rec)
            wconts = {}                          # several continents: the world entry lists them (continent menu
            for pk in pks:                      # ids from 251 down; names = the game's continents)
                wconts.setdefault(pk.meta.get('continent', 'europe'), []).append(pk.files[pk.league['clubs']][0])
            if len(wconts) > 1:
                ids, cid = [], 251
                # a continent of more than WCONT_MAX countries (a longer list exits to DOS): its list holds the first
                # WCONT_MAX - 1 (pack order = the UEFA ranking for Europe) and an OTHER NATIONS entry, a list of the
                # rest (chained again if needed). Davide 2026-10-16: one list per continent + ALTRE NAZIONI.
                def take_id():
                    nonlocal cid
                    while ct + 4 * cid in fx2 or comp + 4 * cid in fx2 or cid in wmenus or any(
                            cid == e[0] for v in WCONT_IDS.values() for e in v) or cid in [e[0] for e in ids] or \
                            any(cid in v for v in NS.values()):     # (a global id: no world may use it)
                        cid -= 1
                    _need(cid > WMENU + max(worlds()), f'world {n}: no free continent menu id')
                    cid -= 1
                    return cid + 1

                def put_list(lid, entries):
                    nonlocal at
                    cl = struct.pack('<i', -1) + bytes(entries) + b'\xff'
                    p.put(1, at, cl)
                    p.add_ptr(2, comp + 4 * lid, 1, at)
                    at = (at + len(cl) + 3) & ~3
                for c in sorted(wconts, key=CONT_ORDER.index):
                    files, lid, top = wconts[c], take_id(), True
                    p.add_ptr(2, ct + 4 * lid, *p.target(2, ct + 4 * CONT_NAT[c]))
                    while True:
                        if len(files) <= WCONT_MAX:
                            put_list(lid, files)
                            ids.append((lid, files, top))
                            break
                        more = take_id()
                        oname = OTHER_NAMES[lang]
                        p.add_ptr(2, ct + 4 * more, 2, area.add(bytes((countries.CONTINENT[c],)) + oname + b'\0'
                                                                + oname + b'\0'))
                        put_list(lid, files[:WCONT_MAX - 1] + [more])
                        ids.append((lid, files[:WCONT_MAX - 1], top))
                        files, lid, top = files[WCONT_MAX - 1:], more, False
                WCONT_IDS[n] = ids
                wl = struct.pack('<i', -1) + bytes(x for x, _, top in ids if top) + b'\xff'
            else:
                wl = struct.pack('<i', -1) + bytes(pk.files[pk.league['clubs']][0] for pk in pks) + b'\xff'
            p.put(1, at, wl)
            p.add_ptr(2, comp + 4 * wid, 1, at)
            at = (at + len(wl) + 3) & ~3
            wmenus.append(wid)
        lst = struct.pack('<i', -1) + bytes(entries) + b'\xff'
        p.put(1, at, lst)
        p.add_ptr(2, comp + 4 * CAREERS, 1, at)
        at = (at + len(lst) + 3) & ~3
        cworld = at
        p.add_ptr(1, at, *p.target(wobj, world))
        p.put(1, at + 4, b'\xff' * 4 + conts + bytes((CAREERS, 0xff)))
        at = (at + 8 + len(conts) + 2 + 3) & ~3
    d1 = p.le.obj_bytes(1)
    d7 = sacups.regs(d1)['D7']                  # continent range check: cmp word [D7], 85; ja last -> ja cont_check
    ms = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + re.escape(struct.pack('<I', d7)) + rb'\x55\x0f\x87', d1)]
    assert len(ms) == 1, ms
    ja = ms[0] + 8
    last = ja + 6 + struct.unpack_from('<i', d1, ja + 2)[0]

    _, season_call, select = historic._calls(p)
    site, skip, comp_cn, sel, num, r = _hook_sites(p)
    symbols = {'COMP254': (2, comp + 4 * 254), 'SEASON_WORLD': (1, sworld), 'SELECT': (1, select),
               'D7REG': (2, d7), 'SEASONS_N': (0, SEASONS), 'CONT_WORLD': (1, ja + 6), 'CONT_LAST': (1, last),
               'A0': (2, r['A0']), 'COMPCOUNTRY': (2, comp_cn), 'SELTEAMS': (2, sel), 'NUMSEL': (2, num),
               'SKIP_SLOT2': (1, skip)}
    src = HOOK_ASM
    if careers:
        site_c, choose = _career_site(p)
        symbols.update({'CAREER_WORLD': (1, cworld), 'CHOOSE': (1, choose), 'CAREERS_N': (0, CAREERS)})
        src = src.replace('cont_check:', 'cont_check:\n    cmp word [D7REG], CAREERS_N\n    je CONT_WORLD') + CAREER_ASM
        if worlds():                                      # careerworld.WCONT: the running world's continent
            src = src.replace('cont_check:', 'cont_check:\n    cmp word [D7REG], 99\n    je CONT_WORLD')
        for wid in wmenus:                                # the worlds of the CLASSIC CAREERS list
            src = src.replace('cont_check:', f'cont_check:\n    cmp word [D7REG], {wid}\n    je CONT_WORLD')
        for ids in WCONT_IDS.values():                    # a world's continents and OTHER NATIONS lists
            for cid, _, _ in ids:
                src = src.replace('cont_check:', f'cont_check:\n    cmp word [D7REG], {cid}\n    je CONT_WORLD')
        if wmenus:
            lvl, nst, csp = _level_site(p)
            symbols.update({'NST': nst, 'CSP': csp, 'WMENU_N': (0, WMENU)})
            src += WMENU_ASM
    tab = ['align 4', 'PACK_TAB:']
    data = []
    for k, i in enumerate(x for x in infos if x['emap']):
        tab.append(f"    db {i['file']}, {i['n']}, 0, 0")
        tab.append(f'    dd PACK_MAP_{k}, PACK_CUPS_{k}')
        data.append(f'PACK_CUPS_{k}: dd ' + ', '.join(f'CUP_{k}_{j}' for j in range(len(i['cups']))))
        data.append(f'PACK_MAP_{k}: db ' + ', '.join(map(str, i['emap'])))
        for j, c in enumerate(i['cups']):
            symbols[f'CUP_{k}_{j}'] = (1, c)
    src += '\n'.join(tab + ['    db 0xff', 'align 4'] + data) + '\n'
    code, fix = nasmcave.assemble(src, at, symbols)
    labels = nasmcave.labels(src, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, season_call + 1, struct.pack('<i', labels['season_sel'] - (season_call + 5)))
    p.put(1, ja + 2, struct.pack('<i', labels['cont_check'] - (ja + 6)))
    if careers:
        p.put(1, site_c + 1, struct.pack('<i', labels['career_sel'] - (site_c + 5)))
    if wmenus:
        p.remove(1, lvl + 3)                              # the cmp's address operand
        p.put(1, lvl, b'\xe8' + struct.pack('<i', labels['w_lvl'] - (lvl + 5)) + b'\x90' * 3)   # the cmp is 8 bytes; keep the jnz
    p.remove(1, site + 1)                                # `mov [A0], eax`: drop the fixup of its address operand
    p.put(1, site, b'\xe8' + struct.pack('<i', labels['euro_slot2'] - (site + 5)))
    at = (at + len(code) + 3) & ~3
    if worlds():                                          # career packs M2: historic career worlds
        import careerworld
        cave = CAREER_CAVE[0]
        careerworld.LANG[0] = lang
        if multi_ns():
            careerworld.NS['info'] = dict(NS_INFO, files={n: ns_files(n) for n in worlds()}, base=ns_base(),
                                          stems={n: ns_stem(n) for n in worlds()}, cworld=cworld, wmenu=WMENU)
        end = careerworld.patch(p, world_defs(), cave, nasmcave, comp, ct, (2, CAREERS_REC[0]))
        _need(end <= cave + CAREER_CAVE_SIZE, f'career world code overflows its pages ({end:#x})')
    return at, [x for i in infos for x in i['classic']] + tleagues



def main(argv):
    if len(argv) >= 2 and argv[0] == 'check':
        try:
            pks = [Pack(x) for x in argv[1:]]
            for pk in pks:
                print(f"== {pk.meta['id']} ({pk.kind})")
                for c in pk.comps:
                    if c['type'] == 'league' and pk.kind == 'tourney':
                        print(f"{c['key']}: round robin, {pk.round_robin(c)} clubs, "
                              f"{'home and away' if c['games'] == 2 else 'one match per pair'}")
                        continue
                    if c['type'] == 'tourney':
                        t = pk.tourney(c)
                        print(f"{c['key']}: tourney, {len(t['clubs'])} teams, stages "
                              f"{' > '.join(str(x.get('teams', 2)) + ' ' + x['type'] for x in c['stages'])}, "
                              f"{'replays + coin toss' if t['coin'] else 'no replays'}")
                        continue
                    n = len(pk.league_clubs) if c['type'] == 'league' else len(pk.bracket(c)['clubs'])
                    print(f"{c['key']}: {c['type']}, {n} clubs")
                short = [k for k, v in pk.players.items() if len(v) < 16 and pk.kind != 'tourney']
                print(f'{len(pk.clubs)} clubs, {sum(map(len, pk.players.values()))} players; under 16 players (fillers): {short}')
            packs.cache = pks                   # several career packs = a world: check it as a whole
            for w in world_defs():
                print(f"== world {w['n']}: from {w['year']}, countries {w['countries']}")
                for key in ('cc', 'cwc', 'uefa'):
                    print(f"{key}: {len(w['cups'][key][1])} clubs = {len(w['places'][key])} places + "
                          f"{len(w['cups'][key][1]) - len(w['places'][key])} holder place(s); "
                          f"season 1: {', '.join(pk.clubs[c]['name'] for pk, c in w['clubs'][key])}")
        except PackError as e:
            sys.exit(f'ERROR: {e}')
        return
    print(__doc__)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])
