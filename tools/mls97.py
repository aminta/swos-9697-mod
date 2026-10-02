"""MLS 1997 (session 28n, for 2.1; Davide's choices: 1997, penalties for the 35-yard shoot-out, 4 games per pair,
one table).

Sources (fetched 2026-10-02): Transfermarkt "Major League Soccer 1997" squad statistics of the 10 clubs (positions,
nationalities, appearances; internal/mls97, tools/mls_tm.py); en.wikipedia "1997 Major League Soccer season" (format, head
coaches). Real format: 32 games (conference x4, other conference x3, +1), win 3, shoot-out win 1, loss 0, two conferences,
best-of-three play-offs. Here: one 10-club table, 4 games per pair (36), win 3 / shoot-out win 1 / loss 0 (nz97 shoot-out
hooks, MLS variant), penalties instead of the 35-yard shoot-out.
Squads: the 16 players with most 1997 MLS appearances (a mid-season mover goes to the club he played most for), roles from
Transfermarkt; a player already in SWOS 96/97 keeps his record (skills), new ones take the skills of the slot they fill.
"""
import collections, os, struct, unicodedata

import mls_tm

FILE = 73
TEAM_SIZE = 684
CODES = None            # nationality codes of the game (obj2 'ALBAUTBEL...'), set by build()

# record -> (Transfermarkt page, new name or None, 1997 head coach)
CLUBS = {
    0: ('columbus-crew-sc', 'COLUMBUS CREW', 'Tom Fitzgerald'),      # SWOS: COLOMBUS CREW (typo)
    2: ('colorado-rapids', None, 'Glenn Myernick'),
    3: ('fc-dallas', None, 'Dave Dir'),
    5: ('sporting-kansas-city', 'KANSAS CITY WIZ.', 'Ron Newman'),  # Kansas City Wizards
    6: ('los-angeles-galaxy', None, 'Octavio Zambrano'),
    9: ('new-england-revolution', None, 'Thomas Rongen'),
    10: ('new-york-red-bulls', None, 'Carlos Alberto Parreira'),
    12: ('san-jose-earthquakes', None, 'Brian Quinn'),
    14: ('tampa-bay-mutiny', None, 'John Kowalski'),
    17: ('d-c-united', 'D.C. UNITED', 'Bruce Arena'),                 # SWOS: WASHINGTON DC
}
MLS_MASK = sum(1 << i for i in CLUBS)
NAT = {'United States': 'USA', 'Argentina': 'ARG', 'Nigeria': 'NIG', 'Mexico': 'MEX', 'Brazil': 'BRA',
       'South Africa': 'SAF', 'El Salvador': 'ELS', 'Trinidad and Tobago': 'TRI', 'Italy': 'ITA', 'Colombia': 'COL',
       'Poland': 'POL', 'Honduras': 'HON', 'St. Vincent & Grenadinen': 'SVC', 'Scotland': 'SCO', 'Liberia': 'LIB',
       'Bolivia': 'BOL', 'Canada': 'CAN', 'Mozambique': 'MOZ', 'Jamaica': 'JAM', 'Hungary': 'HUN', 'Guatemala': 'GUA',
       'Paraguay': 'PAR', 'Ecuador': 'ECU', 'Armenia': 'ARM', 'Zimbabwe': 'ZIM', 'Switzerland': 'SUI', 'Ireland': 'IRL',
       'Venezuela': 'VNZ', 'Uruguay': 'URU'}
CLASS = 'GDDDMMMA'


def role(pos):
    p = pos.lower()
    if 'goal' in p:
        return 'G'
    if 'back' in p or 'sweeper' in p or p == 'defender':
        return 'D'
    if 'midfield' in p:
        return 'M'
    return 'A'                          # wingers, forwards, strikers


def norm(s):
    return ' '.join(unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper().replace('.', ' ').split())


def swos_name(s, maxlen=22):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()
    if len(s) > maxlen:
        w = s.split(' ', 1)
        s = f'{w[0][0]}. {w[1]}'[:maxlen]
    return s


def codes(exe):
    from le import LE
    d2 = LE(exe).obj_bytes(2)
    i = d2.find(b'ALBAUTBELBUL')
    out = []
    while d2[i]:
        out.append(d2[i:i + 3].decode())
        i += 3
    return out


def build(src_dir):
    global CODES
    CODES = codes(os.path.join(os.path.dirname(__file__), '..', 'orig', 'ENGLISH.EXE'))
    d = bytearray(open(os.path.join(src_dir, 'TEAM.%03d' % FILE), 'rb').read())
    known = {}
    import glob
    for f in [os.path.join(src_dir, 'TEAM.%03d' % FILE)] + sorted(glob.glob(os.path.join(src_dir, 'TEAM.0[0-9][0-9]'))):
        t = open(f, 'rb').read()
        for i in range(struct.unpack('>H', t[:2])[0]):
            r = t[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE]
            for k in range(16):
                p = r[76 + k * 38:76 + (k + 1) * 38]
                known.setdefault(norm(p[3:26].split(b'\0')[0].decode('latin1')), p)
    squads = {i: mls_tm.squad(os.path.join(mls_tm.SRC, page + '.apps.html')) for i, (page, _, _) in CLUBS.items()}
    best = {}
    for i, sq in squads.items():
        for pl in sq:
            k = norm(pl['name'])
            if k not in best or pl['apps'] > best[k][1]:
                best[k] = (i, pl['apps'])
    for i, (page, name, coach) in CLUBS.items():
        o = 2 + i * TEAM_SIZE
        r = d[o:o + TEAM_SIZE]
        assert r[25] == 0
        if name:
            r[5:22] = name.encode().ljust(17, b'\0')[:17]
        r[36:59] = swos_name(coach).encode().ljust(23, b'\0')[:23]
        cands = [dict(pl, role=role(pl['pos'])) for pl in sorted(squads[i], key=lambda x: -x['apps'])
                 if best[norm(pl['name'])][0] == i]
        pools = {c: [x for x in cands if x['role'] == c] for c in 'GDMA'}
        borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
        for k in sorted(range(16), key=lambda j: r[76 + j * 38 + 2]):   # shirts 1..11 first
            p = 76 + k * 38
            cls = CLASS[r[p + 26] >> 5]
            src = next((x for x in borrow[cls] if pools[x]), None)
            if src is None:
                continue                                    # keep the SWOS player of that slot
            c = pools[src].pop(0)
            rec = known.get(norm(c['name']))
            if rec is not None:
                q = bytearray(rec)
                q[1:3] = r[p + 1:p + 3]
                q[26] = (q[26] & 0x1F) | (r[p + 26] & 0xE0)
                r[p:p + 38] = q
            r[p] = CODES.index(NAT[c['nat']]) if c['nat'] in NAT else CODES.index('USA')
            r[p + 3:p + 26] = swos_name(c['name']).encode('latin1', 'ignore').ljust(23, b'\0')[:23]
        d[o:o + TEAM_SIZE] = r
    return bytes(d)


# --- exe: 4 games per pair ---------------------------------------------------------------------------------------
LEAGUE_SIG = bytes((0x69, 0, 0x49, 0x18, 0x48, 0, 0, 0, 0, 1, 2, 3, 0x35))


def patch(p):
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1 and d2[lo + 13] == 10
    p.put(2, lo + 10, b'\x04')                          # every pair meets 4 times (36 games; real 32, unbalanced)
    print(f'exe: MLS 1997: 4 games per pair (struct obj2+{lo:#x})')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    out = build(os.path.join(os.path.dirname(__file__), '..', 'orig', 'DATA'))
    for i in CLUBS:
        r = out[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE]
        print(r[5:22].split(b'\0')[0].decode(), '|', r[36:59].split(b'\0')[0].decode(), '|',
              ', '.join(f"{r[76 + k * 38 + 3:76 + k * 38 + 26].split(b'\\0')[0].decode()}({CODES[r[76 + k * 38]]})" for k in range(16)))
