"""New Zealand 1996-97 (session 28g, for 2.1): National Summer Soccer League + three regional divisions of 10.

Sources (fetched 2026-10-02): en.wikipedia "1996-97 National Summer Soccer League" (format, table, play-offs); The Ultimate New
Zealand Soccer Website by Jeremy Ruane (ultimatenzsoccer.com, NZClubSoccer: 1996-7 National Summer League results, 1996 Northern,
Central and Southern League tables; Wayback copies in internal/nz9697).
- NSSL 1996-97 (Nov 1996 - Apr 1997): 10 invited clubs, home and away, 4 points a win, 1 a draw (+1 to the winner of the
  shoot-out after every draw: nz97 shoot-out code, later), top 4 to the play-offs. All 10 are SWOS clubs (two renamed).
- NORTHERN / CENTRAL / SOUTHERN: the 20 other SWOS clubs (all kept) + the best 1996 clubs SWOS lacks: Northern League 1996
  champion Lynn-Avon United and Blockhouse Bay, Fencibles United, Ngaruawahia United, Papakura City; Central League 1996
  champion Western Suburbs and North Wellington, Gisborne City, Tararua United; Southern League 1996 Div One North champion
  Northern Hearts (Davide's pick). Their squads and coaches are INVENTED (no source); kits are those of the template club.
- Global numbers: NZ needs 40 -> moves to the free run 1960..1999; Bolivia (moved there for Australia, see nsl97) goes to NZ's
  old 1248..1261.
"""
import random, struct

FILE = 62
TEAM_SIZE = 684
NZL = 149                       # nationality byte of the New Zealand players
BASE = 1960
NSSL, NORTH, CENTRAL, SOUTH = 0, 1, 2, 3

# SWOS record index -> (new division, new name or None)
CLUBS = {
    0: (SOUTH, None),                       # Burnside
    1: (NSSL, None),                        # Central United
    2: (SOUTH, None), 3: (SOUTH, None), 4: (SOUTH, None), 5: (SOUTH, None), 6: (SOUTH, None),
    7: (CENTRAL, None),                     # Lower Hutt City
    8: (NORTH, None),                       # Manurewa
    9: (NSSL, None),                        # Miramar Rangers
    10: (NORTH, None),                      # Mount Albert
    11: (NSSL, 'MT. MAUNGANUI'),            # SWOS: MOUNT MANGANUI (typo)
    12: (NORTH, None),                      # Mount Wellington
    13: (NSSL, 'NAPIER CITY ROV.'),
    14: (NSSL, None),                       # Nelson Suburbs
    15: (CENTRAL, None),                    # New Plymouth
    16: (NSSL, None),                       # North Shore United
    17: (NORTH, None), 18: (NORTH, None),   # Oratia United, Papatoetoe
    19: (CENTRAL, None),                    # Petone
    20: (SOUTH, None), 21: (SOUTH, None),   # Rangers, Roslyn Wakari
    22: (NSSL, 'MELVILLE UNITED'),          # SWOS: WAIKATO UNITED (its name until 1995)
    23: (NSSL, None),                       # Waitakere City
    24: (CENTRAL, None), 25: (CENTRAL, None), 26: (CENTRAL, None),   # Wanganui East, Waterside Karori, Wellington Olympic
    27: (NSSL, None),                       # Wellington United
    28: (SOUTH, None),                      # Western
    29: (NSSL, None),                       # Woolston WMC
}
# new clubs: (name, division, template record (a SWOS club of the same region), strength step)
NEW = [
    ('LYNN-AVON UNITED', NORTH, 12, 0), ('BLOCKHOUSE BAY', NORTH, 18, -1), ('FENCIBLES UNITED', NORTH, 8, -1),
    ('NGARUAWAHIA UTD', NORTH, 17, 0), ('PAPAKURA CITY', NORTH, 10, 0),
    ('WESTERN SUBURBS', CENTRAL, 26, 0), ('NORTH WELLINGTON', CENTRAL, 19, -1), ('GISBORNE CITY', CENTRAL, 15, -1),
    ('TARARUA UNITED', CENTRAL, 7, 0),
    ('NORTHERN HEARTS', SOUTH, 21, 0),
]
FIRST = ('ANDREW BRENT CHRIS CRAIG DANIEL DARREN DAVID DEAN GARY GRANT GREG IAN JASON JOHN KEVIN MARK MATTHEW MICHAEL NEIL '
         'NICK PAUL PETER RICHARD ROSS SCOTT SHANE SIMON STEVE STUART TIM TONY TREVOR WAYNE').split()
LAST = ('ANDERSON BAKER BROWN CAMPBELL CLARKE COOPER DAVIES EDWARDS FRASER GRAHAM HALL HARRIS HUGHES JOHNSTON KING LEWIS '
        'MACDONALD MARTIN MITCHELL MORRIS MURRAY NGATA PARATA ROBERTSON ROSS SCOTT SMITH STEWART TAYLOR THOMPSON TUHIWAI '
        'WALKER WATSON WHITE WILSON WOOD WRIGHT YOUNG').split()


def level_player(r, p, step):
    import c1c2
    c1c2.level_player(r, p, step)


def build(src_dir):
    d = open(f'{src_dir}/TEAM.{FILE:03d}', 'rb').read()
    assert struct.unpack('>H', d[:2])[0] == 30
    recs = [bytearray(d[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE]) for i in range(30)]
    used = {r[76 + k * 38 + 3:76 + k * 38 + 26].split(b'\0')[0].decode('latin1') for r in recs for k in range(16)}
    for i, (div, name) in CLUBS.items():
        r = recs[i]
        r[25] = div
        if name:
            r[5:22] = name.encode().ljust(17, b'\0')[:17]
    rng = random.Random(1996 * 100 + FILE)
    def gen():
        while True:
            n = f'{rng.choice(FIRST)} {rng.choice(LAST)}'
            if n not in used:
                used.add(n)
                return n
    for k, (name, div, tmpl, step) in enumerate(NEW):
        assert len(name) <= 16, name
        r = bytearray(recs[tmpl])
        r[1] = 30 + k
        r[5:22] = name.encode().ljust(17, b'\0')
        r[25] = div
        r[36:59] = gen().encode().ljust(23, b'\0')
        for j in range(16):
            p = 76 + j * 38
            r[p] = NZL
            r[p + 3:p + 26] = gen().encode().ljust(23, b'\0')
            if step:
                level_player(r, p, step)
        recs.append(r)
    for i, r in enumerate(recs):
        assert r[0] == FILE and r[1] == i
        struct.pack_into('>H', r, 2, BASE + i)
    out = struct.pack('>H', len(recs)) + b''.join(bytes(r) for r in recs)
    divs = [sum(1 for r in recs if r[25] == v) for v in range(4)]
    assert divs == [10, 10, 10, 10], divs
    return out


# --- exe: league struct (4 divisions, 4 points a win) ---------------------------------------------------------------
LEAGUE_SIG = bytes((0x61, 0, 0x3E, 0x10, 0x48, 0x1B, 0, 0, 0, 3, 2, 3, 0x35))
NSSL_NAME = (b'NAT. SUMMER LEAGUE', b'NSSL')


def patch(p, area, str_base):
    """New 4-division struct in the new obj2 page; every pointer to the old one retargeted."""
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1
    old = [struct.unpack_from('<I', d2, lo + 13 + 3 * 6 + 1 + 4 * i)[0] for i in range(6)]   # 3 x (long, short)
    hdr = bytearray(d2[lo:lo + 13])
    n = 4
    hdr[5] = 13 + 6 * n + 1 - 5
    hdr[9] = n
    hdr[11] = 4                                         # 4 points for a win (NSSL 1996-97)
    body = bytes(hdr) + bytes((10, 0, 0, 0, 0, 0)) * n + b'\0'
    nssl = [area.add(s + b'\0') - str_base for s in NSSL_NAME]
    for ptr in nssl + old:
        body += struct.pack('<I', ptr)
    at = area.add(body)
    refs = []                                           # every single-target record (original or added by the mod)
    for gp, recs in enumerate(p.recs):
        for r in recs:
            if r[0] & 0x20 or r[1] & 3 or (r[0] & 0x0F) == 2:   # source lists, imports, selector-only fixups
                continue
            q = 4
            tobj = struct.unpack_from('<H', r, q)[0] if r[1] & 0x40 else r[q]
            q += 2 if r[1] & 0x40 else 1
            toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, q)[0]
            if tobj == 2 and toff == lo:
                obj = next(o for o in p.le.objs if o.page_idx - 1 <= gp < o.page_idx - 1 + o.npages)
                refs.append((obj.idx, (gp - (obj.page_idx - 1)) * p.le.page_size + struct.unpack_from('<h', r, 2)[0]))
    assert refs, 'no pointer to the NZ league struct'
    for objn, off in refs:
        p.retarget(objn, off, 2, at)
    print(f'exe: New Zealand NSSL 1996-97 + 3 regions of 10, struct obj2+{at:#x} ({len(refs)} pointers)')
    return at
