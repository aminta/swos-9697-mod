"""Australia 1996-97 (session 28, for 2.1): the real National Soccer League of 14 clubs with their 1996-97 squads.

Sources (fetched 2026-10-02):
- ozfootball.net archive (Wayback Machine copies, kept in internal/nsl9697): line-ups with substitutes of all 26 rounds
  (Round01..Round26.html, Thomas Esamie), the finals series (Playoff.html) and the NSL Cup (NSLCup.html);
- en.wikipedia "1996-97 National Soccer League" (clubs, table, finals), "1997 National Soccer League grand final" (bracket),
  season pages of Perth Glory, Collingwood Warriors, Canberra Cosmos (coaches), club pages (Adelaide City: John Nyskohus
  1996-98; South Melbourne: Ange Postecoglou from 1996-97); match reports for the other coaches (Frank Farina player-manager
  of Brisbane, John Kosmina at Newcastle, Frank Arok at Gippsland).
Squads = the 16 players with most appearances (starts + substitute appearances), roles from the game's own record of the
player when he is in SWOS 96/97 (any team file), otherwise from his average place in the printed line-ups (keeper first,
then backs, midfield, forwards) - those roles are reconstructed. Players new to SWOS take the skills of the slot they fill.
"""
import collections, difflib, glob, os, re, struct, unicodedata

import nsl_lineups

FILE = 44                       # TEAM.044 = Australia
TEAM_SIZE = 684
AUS = 148                       # nationality byte of the Australian players
CLASS = 'GDDDMMMA'

# ozfootball team names -> club in TEAM.044 (index, 1996-97 name or None = keep, coach or None = keep)
CLUBS = {
    'Adelaide City':        (3, None, 'John Nyskohus'),
    'Brisbane Strikers':    (9, 'BRIS. STRIKERS', 'Frank Farina'),      # SWOS: BRISBANE STRIKES (typo)
    'Canberra Cosmos':      (11, None, 'Mick Lyons'),
    'Collingwood Warriors': (19, 'COLLINGWOOD WAR.', 'Zoran Matic'),     # Heidelberg United merged into them in 1996
    'Gippsland Falcons':    (26, 'GIPPSLAND FALCON', 'Frank Arok'),      # Morwell Falcons renamed
    'Marconi-Fairfield':    (22, 'MARCONI-FAIRFLD', None),             # SWOS: MARCONI FAIRFIED (typo)
    'Melbourne Knights':    (23, None, None),
    'Newcastle Breakers':   (28, None, 'John Kosmina'),
    'Perth Glory':          (51, 'PERTH GLORY', 'Gary Marocchi'),        # NEW 52nd record (from Brunswick's)
    'South Melbourne':      (39, None, 'Ange Postecoglou'),
    'Sydney United':        (42, None, 'Branko Culina'),
    'UTS Olympic':          (44, None, None),
    'West Adelaide':        (46, None, None),
    'Wollongong City':      (49, None, None),
}
TEAM_ALIAS = {'Marconi Fairfield': 'Marconi-Fairfield', 'South Mebourne': 'South Melbourne', 'Brisbane': 'Brisbane Strikers',
              'Wollongong Wolves': 'Wollongong City'}
KITS = {'Perth Glory': [0, 6, 6, 6, 6], 'Collingwood Warriors': [2, 2, 1, 2, 2]}   # purple; black-and-white stripes
NSL, SOUTH = 0, 1               # division byte (record +25)
BRUNSWICK = 10                  # Brunswick United: no league in SWOS -> SOUTH (Victoria), in place of Heidelberg
# Australia needs 52 global numbers but TEAM.045 (Bolivia, 14 clubs) starts at 1035 (global = teamsCountryNumbers[file
# byte] + ordinal, recomputed by SetTeamGlobalNumbers at every load; cup lists use file/ordinal pairs): New Zealand (40 clubs
# in 2.1, nz97) moves to the free run 1960..1999 and Bolivia to NZ's old 1248..1261, so Australia may use 984..1048.
BASE_MOVES = {45: (1035, 1248), 62: (1248, 1960)}     # file: (original base, new base)
COUNT = 52


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()
    return ' '.join(s.replace('.', ' ').split())


def key(s):
    w = norm(s).split()
    return (w[0][0], ''.join(w[1:])) if len(w) > 1 else ('', ''.join(w))


def merged(counter):
    """Merge spellings of the same player (Brad/Bradley Hassell, De Amicis/DeAmicis, Kalageracos): same initial and a
    near-identical surname; the most frequent spelling wins. Surname-only entries (the NSL Cup line-ups: 'Bolton') join
    the full name with that surname."""
    groups = []
    full = [(n, c) for n, c in counter.most_common() if key(n)[0]]
    bare = [(n, c) for n, c in counter.most_common() if not key(n)[0]]
    for name, n in full:
        k = key(name)
        for g in groups:
            if g['key'][0] == k[0] and difflib.SequenceMatcher(None, g['key'][1], k[1]).ratio() >= 0.85:
                g['n'] += n
                g['all'].append(name)
                break
        else:
            groups.append({'key': k, 'name': name, 'n': n, 'all': [name]})
    for name, n in bare:
        same = [g for g in groups if difflib.SequenceMatcher(None, g['key'][1], key(name)[1]).ratio() >= 0.85]
        if len(same) == 1:
            same[0]['n'] += n
            same[0]['all'].append(name)
        else:
            groups.append({'key': key(name), 'name': name, 'n': n, 'all': [name], 'bare': True})
    groups.sort(key=lambda g: -g['n'])
    return groups


def lineup_roles():
    """Average place of each player (by merged spelling) in the printed starting line-ups."""
    pos = collections.defaultdict(list)
    for _, _, team, st, _ in nsl_lineups.matches():
        if len(st) == 11:
            for i, p in enumerate(st):
                pos[(TEAM_ALIAS.get(team, team), p)].append(i)
    return pos


def role_from_place(places):
    if not places:
        return None
    if sum(1 for x in places if x == 0) * 2 >= len(places):
        return 'G'
    a = sum(places) / len(places)
    return 'D' if a < 4.6 else 'M' if a < 8.0 else 'A'


def known_players(src_dir):
    """Every player of the original team files: normalized name -> 38-byte record (TEAM.044 first)."""
    known = {}
    files = [os.path.join(src_dir, 'TEAM.%03d' % FILE)] + sorted(glob.glob(os.path.join(src_dir, 'TEAM.0[0-9][0-9]')))
    for f in files:
        d = open(f, 'rb').read()
        for i in range(struct.unpack('>H', d[:2])[0]):
            r = d[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE]
            for k in range(16):
                p = r[76 + k * 38:76 + (k + 1) * 38]
                known.setdefault(norm(p[3:26].split(b'\0')[0].decode('latin1')), p)
    return known


def find_known(group, known):
    if group.get('bare'):
        return None
    for n in group['all']:
        if norm(n) in known:
            return known[norm(n)]
    k = group['key']                       # DINI MENNILLO (SWOS typo) = Dino Mennillo
    best = None
    for name, rec in known.items():
        w = name.split()
        if len(w) > 1 and w[0][0] == k[0] and ''.join(w[1:]) == k[1]:
            return rec
        if len(w) > 1 and ''.join(w[1:]) == k[1] and difflib.SequenceMatcher(None, w[0], norm(group['name']).split()[0]).ratio() >= 0.75:
            best = rec
    return best


def swos_name(s, maxlen=22):
    s = norm(s)
    if len(s) > maxlen:
        w = s.split(' ', 1)
        s = f'{w[0][0]}. {w[1]}'[:maxlen]
    return s


def build(src_dir, report=False):
    d = bytearray(open(os.path.join(src_dir, 'TEAM.%03d' % FILE), 'rb').read())
    assert struct.unpack('>H', d[:2])[0] == 51
    o = 2 + BRUNSWICK * TEAM_SIZE
    perth = bytearray(d[o:o + TEAM_SIZE])               # Perth Glory: a new record on Brunswick's (players replaced)
    perth[1] = 51
    struct.pack_into('>H', perth, 2, 984 + 51)
    d[o + 25] = SOUTH
    d += perth
    struct.pack_into('>H', d, 0, COUNT)
    known = known_players(src_dir)
    places = lineup_roles()
    app = collections.defaultdict(collections.Counter)
    for _, _, team, st, sb in nsl_lineups.matches():
        team = TEAM_ALIAS.get(team, team)
        if team not in CLUBS:
            continue
        for p in st + sb:
            app[team][p] += 1
    assert set(app) == set(CLUBS), set(CLUBS) ^ set(app)
    log = []
    # a player who moved during the season (Joe Vrkic, Nick Meredith...) goes to the club he played most for
    best = {}
    for team in CLUBS:
        for g in merged(app[team]):
            if not g.get('bare'):
                k = norm(g['name'])
                if k not in best or g['n'] > best[k][1]:
                    best[k] = (team, g['n'])
    for team, (idx, name, coach) in CLUBS.items():
        o = 2 + idx * TEAM_SIZE
        r = d[o:o + TEAM_SIZE]
        if name:
            r[5:22] = name.encode('latin1').ljust(17, b'\0')[:17]
        if coach:
            r[36:59] = swos_name(coach).encode('latin1').ljust(23, b'\0')[:23]
        if team in KITS:
            r[26:31] = bytes(KITS[team])
        r[25] = NSL
        groups = merged(app[team])
        cands = []
        for g in groups:
            if not g.get('bare') and best[norm(g['name'])][0] != team:
                log.append((team, 'moved to', best[norm(g['name'])][0], g['name'], g['n']))
                continue
            rec = find_known(g, known)
            pl = [x for n in g['all'] for x in places.get((team, n), [])]
            # the line-ups decide when he started at least 3 games (SWOS 96/97 has some roles wrong or another
            # player of the same name); otherwise the game's own record, then whatever the line-ups say
            if len(pl) >= 3 or rec is None:
                role = role_from_place(pl) or (CLASS[rec[26] >> 5] if rec is not None else 'M')
            else:
                role = CLASS[rec[26] >> 5]
            cands.append(dict(g, rec=rec, role=role, guessed=rec is None))
        # slots: starters (shirt 1-11) first, then the bench; each slot keeps its role
        order = sorted(range(16), key=lambda k: r[76 + k * 38 + 2])
        pools = {c: [x for x in cands if x['role'] == c] for c in 'GDMA'}
        borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
        for k in order:
            p = 76 + k * 38
            cls = CLASS[r[p + 26] >> 5]
            src = next((x for x in borrow[cls] if pools[x]), None)
            if src is None:
                log.append((team, 'EMPTY SLOT', cls))
                continue
            c = pools[src].pop(0)
            if c['rec'] is not None:
                q = bytearray(c['rec'])
                q[1:3] = r[p + 1:p + 3]                       # the slot's number
                q[26] = (q[26] & 0x1f) | (r[p + 26] & 0xe0)   # the slot's role
                if not c.get('bare'):                         # the line-ups' spelling (SWOS: DINI MENNILLO, DODD)
                    q[3:26] = swos_name(c['name']).encode('latin1').ljust(23, b'\0')[:23]
                r[p:p + 38] = q
            else:
                r[p] = AUS
                r[p + 3:p + 26] = swos_name(c['name']).encode('latin1').ljust(23, b'\0')[:23]
            if report:
                log.append((team, r[p + 2], cls, c['name'], c['n'], 'new' if c['guessed'] else 'swos', c['role']))
        d[o:o + TEAM_SIZE] = r
    if report:
        for x in log:
            print(*x)
    return bytes(d)


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'orig', 'DATA'), report=True)


# league struct of Australia in obj2 (13-byte header, see countries.py): id 57h, country 2Ch, 4 divisions
LEAGUE_SIG = bytes((0x57, 0, 0x2C, 0x10, 0x50, 0x21, 0, 0, 0, 4, 2, 3, 0x35))
DIVISIONS = (14, 12, 14, 12)    # NSL 1996-97 (+ Perth, Collingwood), SOUTH (- Heidelberg + Brunswick), NSW, QLD
NSL_NAME = (b'NSL', b'NSL')     # Davide: "rinominare 1st division in NSL" (long and short name)


def patch(p, area, str_base):
    """Australia's league struct: 14 clubs in the NSL; division 1 renamed NSL; Bolivia's global base moved."""
    d2 = p.le.obj_bytes(2)
    o = d2.find(LEAGUE_SIG)
    assert o >= 0 and d2.count(LEAGUE_SIG) == 1
    for i, n in enumerate(DIVISIONS):
        assert d2[o + 13 + 6 * i] in (12, 14)
        p.put(2, o + 13 + 6 * i, bytes((n,)))
    assert sum(DIVISIONS) == COUNT
    tcn = d2.find(struct.pack('<6H', 0, 16, 26, 44, 60, 72))
    for n, (was, base) in BASE_MOVES.items():
        assert struct.unpack_from('<H', d2, tcn + 2 * n)[0] == was
        p.put(2, tcn + 2 * n, struct.pack('<H', base))
    names = o + 13 + 6 * 4 + 1
    for k, s in enumerate(NSL_NAME):
        p.put(2, names + 4 * k, struct.pack('<I', area.add(s + b'\0') - str_base))
    print(f'exe: Australia NSL 1996-97, divisions {DIVISIONS}')
