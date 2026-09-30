"""Serie C1 / C2 1996-97 teams for TEAM.020.

Real club names (from the 1996-97 final standings); kits are approximate.
New clubs get their real 1996-97 squads and coaches (c1c2_rosters.py) on the
positions of a non-league template club with a compatible role mix; template
skills and prices are shifted towards a strength target from the standings.
Kit tuple: (shirt type, shirt colour, stripe colour, shorts, socks)
  types: 0 plain, 1 coloured sleeves, 2 vertical stripes, 3 horizontal stripes
  colours: 0 grey 1 white 2 black 3 orange 4 red 5 blue 6 brown(maroon)
           7 light blue 8 green 9 yellow
"""
import random

# clubs already in TEAM.020 as non-league, by their 1996-97 division
EXISTING_C1 = ['ACIREALE', 'ANCONA', 'ASCOLI', 'AVELLINO', 'COMO', 'FIDELIS ANDRIA',
               'MODENA', 'MONZA', 'PISTOIESE', 'SPAL']
EXISTING_C2 = ['PISA', 'TARANTO', 'TERNANA']

NEW_C1 = {
    'TREVISO': (1, 1, 7, 1, 1),
    'BRESCELLO': (0, 9, 9, 5, 9),
    'CARPI': (1, 1, 4, 1, 4),
    'SARONNO': (0, 7, 7, 1, 7),
    'PRATO': (0, 7, 7, 1, 7),
    'NOCERINA': (2, 4, 2, 2, 2),
    'CASARANO': (2, 4, 5, 5, 4),
    'JUVE STABIA': (0, 9, 9, 5, 9),
}
NEW_C2 = {
    'LUMEZZANE': (2, 4, 5, 5, 5),
    'LECCO': (2, 7, 5, 5, 5),
    'LIVORNO': (0, 6, 6, 1, 6),
    'BATTIPAGLIESE': (2, 1, 2, 2, 1),
    'TURRIS': (0, 4, 4, 1, 4),
    'BENEVENTO': (2, 4, 9, 4, 4),
    'CATANZARO': (1, 9, 4, 4, 4),
    'TRIESTINA': (0, 4, 4, 1, 4),
    'RIMINI': (1, 4, 1, 1, 4),
    'FROSINONE': (0, 9, 9, 5, 9),
    'SANDONA': (2, 1, 7, 1, 7),
    'PRO PATRIA': (1, 1, 5, 5, 5),
    'CATANIA': (2, 4, 5, 5, 5),
    'PRO SESTO': (0, 7, 7, 1, 7),
    'CITTADELLA': (0, 6, 6, 1, 6),
}

FIRST = ('ALESSANDRO ANDREA ANGELO ANTONIO CARLO CLAUDIO CRISTIAN DANIELE DARIO DAVIDE DIEGO '
         'EMANUELE ENRICO FABIO FABRIZIO FEDERICO FILIPPO FRANCESCO GABRIELE GIACOMO GIANLUCA '
         'GIORGIO GIOVANNI GIUSEPPE LORENZO LUCA MARCO MASSIMO MATTEO MAURIZIO MICHELE NICOLA '
         'PAOLO PIETRO RICCARDO ROBERTO SALVATORE SERGIO SIMONE STEFANO TOMMASO VINCENZO').split()
LAST = ('AMATO BARBIERI BASILE BELLINI BERNARDI BIANCHI BRUNO CARUSO CATTANEO COLOMBO CONTE '
        'CONTI COSTA ESPOSITO FABBRI FARINA FERRARA FERRARI FERRI FONTANA GALLI '
        'GALLO GENTILE GIORDANO GRECO GUERRA LEONE LOMBARDI LONGO MANCINI MARCHETTI MARINI MARINO '
        'MARTINI MAZZA MONTANARI MORETTI MORELLI ORLANDO PAGANO PELLEGRINI RICCI RIZZI RIZZO ROMANO '
        'ROSSI RUSSO SALA SANNA SANTORO SERRA SILVESTRI TESTA VALENTINI VITALE').split()


def random_name(rng, maxlen=22):
    while True:
        n = f'{rng.choice(FIRST)} {rng.choice(LAST)}'
        if len(n) <= maxlen:
            return n


# --- session 14: real 1996-97 squads (tools/c1c2_rosters.py) ---------------
import unicodedata

import c1c2_rosters

CLASS = 'GDDDMMMA'          # position (bits 5-7 of byte 26): G RB LB D RW LW M A -> goalkeeper/defence/midfield/attack


def swos_name(s, maxlen=22):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()
    if len(s) > maxlen:                      # MASSIMILIANO DAL COMPARE -> M. DAL COMPARE
        w = s.split(' ', 1)
        s = f'{w[0][0]}. {w[1]}'[:maxlen]
    return s


def roster(name):
    coach, *lists = c1c2_rosters.ROSTERS[name]
    split = lambda x: [swos_name(n.strip()) for n in x.split(',') if n.strip()]
    return swos_name(coach), dict(zip('GDMA', (split(x) for x in lists)))


def slots(template):
    return [CLASS[template[76 + k * 38 + 26] >> 5] for k in range(16)]


def level_player(r, p, step):
    for i in range(28, 32):
        b = r[p + i]
        nib = []
        for v in (b >> 4, b & 15):
            nib.append((v & 8) | max(0, min(7, (v & 7) + step)))
        r[p + i] = nib[0] << 4 | nib[1]
    r[p + 32] = max(1, r[p + 32] + 2 * step)


def real_team(templates, name, league, kit, rng, used=None, base=None):
    """New club with its real 1996-97 squad: positions/skills from a non-league template with a compatible role mix."""
    coach, players = roster(name)
    have = {c: len(v) for c, v in players.items()}
    def deficit(t):
        need = slots(t)
        return sum(max(0, need.count(c) - have[c]) for c in 'GDMA')
    best = min(deficit(t) for t in templates)
    template = rng.choice([t for t in templates if deficit(t) == best])
    r = bytearray(template)
    r[5:22] = name.encode('latin1').ljust(17, b'\0')
    r[25] = league
    if base is None:
        r[26:31] = bytes(kit)
        r[31:36] = bytes((0, 1, 1, 1, 1))   # white away kit
    else:                                    # existing club: its own kits; its SWOS players fill missing roles
        r[26:36] = base[26:36]
        spare = {c: [base[76 + k * 38 + 3:76 + k * 38 + 26].split(b'\0')[0].decode('latin1')
                     for k in range(16) if CLASS[base[76 + k * 38 + 26] >> 5] == c] for c in 'GDMA'}
    r[36:59] = coach.encode('latin1').ljust(23, b'\0')
    avg = sum(template[76 + k * 38 + 32] for k in range(16)) / 16
    step = max(-3, min(2, round((c1c2_rosters.TARGET[name] - avg) / 2)))
    used = set() if used is None else used     # mid-season transfers: a name already in the game goes last
    pools = {c: [n for n in v if n not in used] + [n for n in v if n in used] for c, v in players.items()}
    borrow = {'G': '', 'D': 'MA', 'M': 'DA', 'A': 'MD'}
    fillers = []
    for k, c in enumerate(slots(template)):
        p = 76 + k * 38
        src = next((x for x in c + borrow[c] if pools[x]), None)
        if src is None:                    # e.g. SPAL, Modena: one goalkeeper known
            n = spare[c].pop(0) if base is not None and spare[c] else random_name(rng)
            fillers.append(n)
        else:
            n = pools[src].pop(0)
            used.add(n)
        nat, black = c1c2_rosters.FOREIGN.get(n, (18, False))
        r[p] = nat
        r[p + 3:p + 26] = n.encode('latin1').ljust(23, b'\0')
        if black:
            r[p + 26] = (r[p + 26] & 0xe0) | 0x10
        level_player(r, p, step)
    return bytes(r), fillers
