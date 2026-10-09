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
ENABLED = os.environ.get('SEASON_PACKS', 'ddr-1988-89').split(',')   # packs built into the mod, in this order
                                        # (a name in packs/ or a path; SEASON_PACKS only for test builds)
TEAM_SIZE = 684
SEASONS = 97                            # pseudo-continent 'classic seasons' of the Season menu
SEASONS_NAMES = {'it': b'STAG. STORICHE', 'en': b'CLASSIC SEASONS', 'fr': b"SAISONS D'ANTAN", 'de': b'SAISONKLASSIKER'}
SEASONS_REC = [None]                    # obj2 offset of its countriesTable record (historic.hist_names colours it)
CAREERS = 98                            # pseudo-continent 'classic careers' of the career team selector
CAREERS_NAMES = {'it': b'CARR. STORICHE', 'en': b'CLASSIC CAREERS', 'fr': b"CARR. D'ANTAN", 'de': b'KLASS. KARRIERE'}
CAREERS_REC = [None]
ROUND = {'two_legs': 0x94, 'single': 0x14, 'single_et': 0x54}   # knockout round byte: two legs (away goals),
                                                                 # single match, single match + extra time/penalties
AU_CUP_SIG = bytes((0xAD, 1, 0x2C, 0x28, 0x50))   # SWOS's Australian cup: layout of a 'national' cup
COUNTRY = {'ALB': 0, 'AUT': 1, 'BEL': 2, 'BUL': 3, 'CYP': 5, 'TCH': 6, 'DEN': 7, 'FIN': 12, 'FRA': 13, 'GDR': 14,
           'FRG': 14, 'GRE': 15, 'HUN': 16, 'ISL': 17, 'IRL': 18, 'ITA': 20, 'LUX': 23, 'MLT': 24, 'NED': 25,
           'NIR': 26, 'NOR': 27, 'POL': 28, 'POR': 29, 'ROU': 30, 'URS': 31, 'SCO': 33, 'ESP': 35, 'SWE': 36,
           'SUI': 37, 'TUR': 38, 'WAL': 40, 'YUG': 41}   # code -> game country (team file whose clubs give templates)
ROLES = 'GDMA'
BORROW = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}   # slot role -> roles its player may come from


EXPLICIT_POS = ['G', 'RB', 'LB', 'D', 'RW', 'LW', 'M', 'A']        # player byte 26, bits 5-7
EXPLICIT_ROLE = {'G': 'G', 'RB': 'D', 'LB': 'D', 'D': 'D', 'RW': 'M', 'LW': 'M', 'M': 'M', 'A': 'A'}
EXPLICIT_SKIN = {'light': 0, 'ginger': 1, 'dark': 2}                 # bits 3-4
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


def _norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s.replace('fc', '').replace('-', ''))


def _records(data):
    return [data[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE] for k in range(struct.unpack('>H', data[:2])[0])]


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
            _need(row['country'] in COUNTRY, f"clubs.csv: {row['key']}: unknown country code {row['country']}")
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
        self.league = next(c for c in self.comps if c['key'] == m['season']['league'])
        self.kind = m.get('kind', 'season')
        _need(self.kind in ('season', 'career'), "pack.json: kind must be 'season' or 'career'")
        self.league_clubs = [k for k, c in self.clubs.items() if c['file'] == self.league['clubs']]
        self.division = {k: int(self.clubs[k].get('division') or 0) for k in self.league_clubs}
        divs = self.divisions()
        for d, dv in enumerate(divs):
            n = sum(1 for k in self.league_clubs if self.division[k] == d)
            _need(n == dv['teams'], f"{self.league['key']}: division {d + 1} has {n} clubs in clubs.csv, {dv['teams']} in pack.json")
        _need(sum(dv['teams'] for dv in divs) == len(self.league_clubs), f"{self.league['key']}: clubs outside the divisions")
        for c in self.comps:
            if c['type'] == 'cup':
                self.bracket(c)          # validates
        self.world = m.get('world')
        if self.world is not None:
            _need(self.kind == 'career' and isinstance(self.world, int) and 1 <= self.world <= 50,
                  'pack.json: world must be a number 1..50 (career packs only)')
            pl = m.get('europe_places', {})
            _need(set(pl) <= {'cc', 'cwc', 'uefa'}, 'europe_places: keys cc, cwc, uefa')
            for key, clubs in m.get('first_europe', {}).items():
                _need(key in ('cc', 'cwc', 'uefa') and len(clubs) == pl.get(key, 0),
                      f'first_europe.{key}: one club per place ({pl.get(key, 0)})')
                for c in clubs:
                    _need(c in self.league_clubs, f'first_europe.{key}: {c} is not a league club')
        for club, cup in m['season'].get('europe', {}).items():
            _need(club in self.league_clubs, f'season.europe: {club} is not a league club')
            _need(club in self.bracket(self.comp(cup))['clubs'], f'season.europe: {club} does not play {cup}')

    def divisions(self):
        """League divisions: pack.json 'divisions' [{teams, promoted, relegated, names}], or one division."""
        lg = self.league
        if 'divisions' in lg:
            return lg['divisions']
        return [{'teams': len(self.league_clubs), 'promoted': 0, 'relegated': lg['relegated'], 'names': lg['names']}]

    def comp(self, key):
        return next(c for c in self.comps if c['key'] == key)

    def bracket(self, comp):
        """{'clubs': contest order (round 1 ties, then byes), 'draws': [perm per round], 'byes': n} from ties.csv."""
        key = comp['key']
        rows = self.ties.get(key)
        _need(rows, f'ties.csv: no ties for {key}')
        nr = max(int(r['round']) for r in rows)
        _need(nr == len(comp['rounds']), f"{key}: {nr} rounds in ties.csv, {len(comp['rounds'])} in pack.json")
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
        for sq in self.meta['squads']:
            builder = {'calibrate': self._calibrate, 'game': self._game, 'explicit': self._explicit}[sq['method']]
            out.update(builder(sq))
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
        the club's target strength (average price byte)."""
        import c1c2
        src = _records(open(os.path.join(ROOT, sq['source']), 'rb').read())
        known = {}
        for r in src:
            for j in range(16):
                p = r[76 + j * 38:76 + (j + 1) * 38]
                known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
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
            avg = sum(t[76 + j * 38 + 32] for j in range(16)) / 16
            step = max(-3, min(3, round((int(c['target']) - avg) / 2)))
            pools = self._pools(key)
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
                if sname in known and c['file'] in sq['reuse_ratings']:
                    q = bytearray(known[sname])
                    q[2] = t[p + 2]
                    q[26] = (q[26] & 0x1f) | (t[p + 26] & 0xe0)
                    r[p:p + 38] = q
                else:
                    r[p] = sq['nationality']
                    r[p + 3:p + 26] = sname.encode('latin1').ljust(23, b'\0')[:23]
                    c1c2.level_player(r, p, step)
            recs[c['file']].append(bytes(r))
        self.log(f"{'+'.join(sq['files'])}: {sum(map(len, recs.values()))} clubs, invented names {fillers}")
        return {self.files[f][0]: struct.pack('>H', len(v)) + b''.join(v) for f, v in recs.items()}

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
        number, position, nat, skin, the 7 skills and price (see EXPLICIT_*)."""
        out = {}
        for fk in sq['files']:
            recs = []
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
                _need(len(rows) == 16, f'players.csv: {key}: explicit squads need exactly 16 players ({len(rows)})')
                for j, row in enumerate(rows):
                    w = f"players.csv: {key} {row['name']}"
                    p = 76 + j * 38
                    pos = row.get('position', '')
                    _need(pos in EXPLICIT_POS, f'{w}: position must be one of {" ".join(EXPLICIT_POS)}')
                    _need(EXPLICIT_ROLE[pos] == row['role'], f"{w}: position {pos} is not role {row['role']}")
                    _need(row.get('skin', '') in EXPLICIT_SKIN, f'{w}: skin must be one of {" ".join(EXPLICIT_SKIN)}')
                    r[p] = _num(row, 'nat', 0, 255, w)
                    r[p + 2] = _num(row, 'number', 1, 255, w)
                    r[p + 3:p + 26] = _sn(row['name']).encode('latin1').ljust(23, b'\0')[:23]
                    r[p + 26] = EXPLICIT_POS.index(pos) << 5 | EXPLICIT_SKIN[row['skin']] << 3
                    nib = [0]
                    for sk in EXPLICIT_SKILLS:
                        v = row.get(sk, '').strip()
                        key_skill = v.endswith('*')
                        v = v.rstrip('*')
                        _need(v.isdigit() and int(v) <= 7, f'{w}: {sk} must be 0..7 (a trailing * marks a key skill)')
                        nib.append(int(v) | (8 if key_skill else 0))
                    for i in range(4):
                        r[p + 28 + i] = nib[2 * i] << 4 | nib[2 * i + 1]
                    r[p + 32] = _num(row, 'price', 0, 49, w)
                recs.append(bytes(r))
            out[self.files[fk][0]] = struct.pack('>H', len(recs)) + b''.join(recs)
        self.log(f"{'+'.join(sq['files'])}: {sum(self.count[f] for f in sq['files'])} clubs, explicit records")
        return out

    def log(self, s):
        print(f"pack {self.meta['id']}: {s}")

    # --- exe ---------------------------------------------------------------------------------------------------------
    def draws(self):
        """historic.DRAWS entries (contest id, permutation), cups in pack order."""
        return [(int(c['id'], 16), perm) for c in self.comps if c['type'] == 'cup' for perm in self.bracket(c)['draws']]

    def bye_cups(self):
        return [(int(c['id'], 16), len(self.bracket(c)['clubs'])) for c in self.comps
                if c['type'] == 'cup' and self.bracket(c)['byes']]

    def team_bytes(self, clubs):
        return b''.join(bytes(self.where[k]) for k in clubs)


def packs():
    if not hasattr(packs, 'cache'):
        packs.cache = [Pack(x if os.sep in x else os.path.join(PACKS, x)) for x in ENABLED]
    return packs.cache


def team_files():
    out = {}
    for pk in packs():
        out.update(pk.team_files())
    return out


def draws():
    return [d for pk in packs() for d in pk.draws()]


def bye_cups():
    return [b for pk in packs() for b in pk.bye_cups()]


def file_numbers():
    return sorted(f for pk in packs() for f, _ in pk.files.values())


def base_of(n):
    """First global number of a pack team file (None if n is not one)."""
    for pk in packs():
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


def _first_europe(pk):
    """First-season European clubs of a world country per cup: pack.json first_europe, else the league order
    (Champions Cup first, then Cup Winners' Cup, then UEFA Cup)."""
    pl, fe = pk.meta.get('europe_places', {}), pk.meta.get('first_europe', {})
    order = iter(pk.league_clubs)
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
             'clubs': {}, 'tmd': 'WORLD%02d.TMD' % n}
        first = {id(pk): _first_europe(pk) for pk in pks}
        for key in ('cc', 'cwc', 'uefa'):
            w['places'][key] = [pk.files[pk.league['clubs']][0] for pk in pks
                                for _ in range(pk.meta.get('europe_places', {}).get(key, 0))]
            clubs = [(pk, c) for pk in pks for c in first[id(pk)][key]]
            size = len(clubs)
            _need(2 <= size <= careerworld.MAX[key] and size & (size - 1) == 0,
                  f'world {n}: {key} has {size} clubs (a power of 2, at most {careerworld.MAX[key]})')
            rounds = wc.get(key, {}).get('rounds') or ['two_legs'] * (size.bit_length() - 2) + ['single']
            _need(2 ** len(rounds) == size, f'world {n}: {key}: {len(rounds)} rounds for {size} clubs')
            w['cups'][key] = (bytes(ROUND[x] for x in rounds), [pk.where[c] for pk, c in clubs])
            w['clubs'][key] = clubs
        _need(len({c for key in w['clubs'] for c in w['clubs'][key]}) == sum(len(v) for v in w['clubs'].values()),
              f'world {n}: a club is in two European cups')
        out.append(w)
    return out


def world_files():
    """{'WORLDnn.TMD': first-season European clubs of world nn (team-file records, the game sets word +2)}."""
    files = team_files()
    out = {}
    for w in world_defs():
        recs = []
        for key in ('cc', 'cwc', 'uefa'):
            for pk, c in w['clubs'][key]:
                f, i = pk.where[c]
                recs.append(files[f][2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE])
        out[w['tmd']] = b''.join(recs)
    return out


def career_file(n):
    """True for the team files of world career packs: their clubs may reuse 1996-97 European global numbers (a world
    career never loads those files)."""
    return any(pk.world is not None and n in (f for f, _ in pk.files.values()) for pk in packs())


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



CAREER_ASM = '''
career_sel:                             ; replaces `call ChooseTeamsDialog` in SelectTeamToManage (career start)
    push dword [COMP254]
    mov dword [COMP254], CAREER_WORLD
    call CHOOSE
    pop dword [COMP254]
    ret
'''


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


def _patch_pack(pk, p, lang, area, at, env):
    """One pack: country entries, competition structs, country table. Returns (cave end, info for the shared part)."""
    import countries
    import sacups
    d2, ct, tcn, comp, fx2 = env
    m = pk.meta
    lfile, _ = pk.files[pk.league['clubs']]
    rec = area.add(bytes((countries.CONTINENT[m['continent']],)) + m['button'].encode('latin1') + b'\0'
                   + m['button'].encode('latin1') + b'\0')
    # every pack file is a country entry (a club's country is never null); bases in teamsCountryNumbers; the entry
    # after the last own-base file closes its team count (a country's count = next base - its base); shared-base
    # files last: their bases overwrite that closing entry when they follow it
    own = sorted(v for v in pk.files.values() if not shares_base(v[0]))
    for f, base in own + sorted(v for v in pk.files.values() if shares_base(v[0])):
        _need(ct + 4 * f not in fx2 and comp + 4 * f not in fx2, f'{pk.meta["id"]}: country {f} is already used')
        p.add_ptr(2, ct + 4 * f, 2, rec)
        p.put(2, tcn + 2 * f, struct.pack('<H', base))
        if (f, base) == own[-1]:
            p.put(2, tcn + 2 * (f + 1),
                  struct.pack('<H', base + pk.count[next(k for k, v in pk.files.items() if v[0] == f)]))

    ptr = {}
    for c in pk.comps:
        names = c['names'].get(lang) or c['names']['*']
        if c['type'] == 'league':
            src_c = c['dates_from']
            gobj, gtab = p.target(2, comp + 4 * src_c)
            lobj, glg = p.target(gobj, gtab)
            lg = p.le.obj_bytes(lobj)[glg:glg + 13]
            assert lg[2] == src_c, lg.hex()
            divs = pk.divisions()
            rel = []
            for dv in divs:
                dn = dv['names'].get(lang) or dv['names']['*']
                rel += [area.add(s.encode('latin1') + b'\0') - sacups.STR_BASE for s in dn]
            hdr = bytes((int(c['id'], 16), 0, lfile, lg[3], lg[4], 9 + 6 * len(divs), 0, 0, 0, len(divs), c['games'],
                         c['win_points'], 0x35))
            body = hdr + b''.join(bytes((dv['teams'], dv['promoted'], 0, dv['relegated'], 0, 0)) for dv in divs) \
                + b'\0' + struct.pack(f'<{len(rel)}I', *rel)
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
    europe = [c['key'] for c in pk.comps if c['type'] == 'cup' and c['key'] != s['cup']]
    p.add_ptr(1, at, 1, ptr[s['league']])       # [league, -2, cup, <European cup>, -1]: slot 2 swapped by euro_slot2
    p.put(1, at + 4, struct.pack('<i', -2))
    p.add_ptr(1, at + 8, 1, ptr[s['cup']])
    table = at
    at += 12
    if s.get('europe'):
        p.add_ptr(1, at, 1, ptr[s['europe_placeholder']])
        at += 4
    p.put(1, at, struct.pack('<i', -1))
    at += 4
    p.add_ptr(2, comp + 4 * lfile, 1, table)
    emap = bytearray(len(pk.league_clubs))
    for club, cup in s.get('europe', {}).items():
        emap[pk.league_clubs.index(club)] = europe.index(cup) + 1
    pk.log(f"exe: country {lfile}, " + ', '.join(f"{c['key']} id {c['id']} @ obj1+{ptr[c['key']]:#x}" for c in pk.comps))
    info = dict(kind=pk.kind, file=lfile, n=len(pk.league_clubs), emap=bytes(emap) if s.get('europe') else None,
                cups=[ptr[k] for k in europe], classic=[ptr[c['key']] for c in pk.comps if c.get('classic_tourney')])
    return at, info


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
    ids = [c['id'] for pk in packs() for c in pk.comps]
    _need(len(set(ids)) == len(ids), f'contest ids used twice: {ids}')
    at, infos = cave, []
    for pk in packs():
        at, info = _patch_pack(pk, p, lang, area, at, env)
        infos.append(info)

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
    if careers:                                 # career team selector: CLASSIC CAREERS (98) after the continents
        assert ct + 4 * CAREERS not in fx2 and comp + 4 * CAREERS not in fx2
        crec = area.add(bytes((countries.CONTINENT['europe'],)) + CAREERS_NAMES[lang] + b'\0' + CAREERS_NAMES[lang] + b'\0')
        CAREERS_REC[0] = crec
        p.add_ptr(2, ct + 4 * CAREERS, 2, crec)
        lst = struct.pack('<i', -1) + bytes(careers) + b'\xff'
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
    p.remove(1, site + 1)                                # `mov [A0], eax`: drop the fixup of its address operand
    p.put(1, site, b'\xe8' + struct.pack('<i', labels['euro_slot2'] - (site + 5)))
    at = (at + len(code) + 3) & ~3
    if worlds():                                          # career packs M2: historic career worlds
        import careerworld
        at = careerworld.patch(p, world_defs(), at, nasmcave)
    return at, [x for i in infos for x in i['classic']]



def main(argv):
    if len(argv) >= 2 and argv[0] == 'check':
        try:
            pk = Pack(argv[1])
        except PackError as e:
            sys.exit(f'ERROR: {e}')
        for c in pk.comps:
            n = len(pk.league_clubs) if c['type'] == 'league' else len(pk.bracket(c)['clubs'])
            print(f"{c['key']}: {c['type']}, {n} clubs")
        short = [k for k, v in pk.players.items() if len(v) < 16]
        print(f'{len(pk.clubs)} clubs, {sum(map(len, pk.players.values()))} players; under 16 players (fillers): {short}')
        return
    print(__doc__)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])
