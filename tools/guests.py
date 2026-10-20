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
DATA = conti.DATA
FILES = {'caf': 191, 'afc': 192, 'ofc': 193, 'concacaf': 194}
LABELS = {191: ('africa', {'*': b'AFRICA'}),       # (continent, the country name shown for its clubs)
          192: ('asia', {'*': b'ASIA'}),
          193: ('oceania', {'*': b'OCEANIA'}),
          194: ('north_america', {'it': b'NORDAMERICA', 'en': b'N. AMERICA', 'fr': b'AM. DU NORD', 'de': b'NORDAMERIKA'})}


def load(conf, data=None):
    p = os.path.join(data or DATA, f'{conf}.guests.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def ready(data=None):
    """The confederations with a guests file."""
    return [c for c in FILES if load(c, data)]


def words(data=None):
    """{(conf, assoc, club): team word} and {(conf, key): team word} of every guest."""
    out = {}
    for conf in ready(data):
        n = FILES[conf]
        for i, c in enumerate(load(conf, data)['clubs']):
            w = n | i << 8
            out[(conf, c['assoc'], c['club'])] = w
            out[(conf, c['key'])] = w
    return out


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
    return out
