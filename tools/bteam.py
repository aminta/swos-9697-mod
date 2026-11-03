"""4.0.6 B-team call-ups (Davide 02/11 + 03/11, notes/bteam-trace.md): the career club calls up players of its B team
(clubs.csv 'second_of'): (1) for the next match only (U23 by birth year, a goalkeeper at any age, the country's
over-age cap, at most 4 a match, back to the B team after the match, no money), (2) for the season (at most 3 a
window, in the country's real transfer windows, a generated replacement in the B record, the game's wages).

This file, step 1: the data. DATA\\BAGE.nnn (nnn = the world) is read by the exe when the call-up page opens:
  'BA', db version 1, db teams
  per team (the career club = parent):  dw B team word, dw parent team word (file | ordinal << 8), db rules index,
                                        db players (record places 1..16, then its XTRA places 17..), db age codes
                                        (birth year - 1900; 0 = unknown: callable, never over-age)
  'BR', db rules
  per rules:                            db over-age cap (one-match call-ups: players older than U23 among those
                                        called; 0FFh = no cap), db U23 age limit,
                                        db windows, (db first week, db last week) x windows (split.week_of: the
                                        career calendar's week byte, 8 a month from January of the season's first
                                        year, +96 the next year)
The windows are the real ones per country (Davide (a), 02/11: Europe summer to 1 Sep, winter January); the
one-match call-ups and the normal market are open all year.
"""
import os
import struct

import split

# Over-age caps and windows by country (the B team's league rules, pack.json second_teams.rules). Week = split.week_of.
#   ITA: Serie C U23 squads (Juventus NG, Atalanta U23, Inter U23, Milan Futuro) - 4 over-age players in a match list;
#        windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   GER: 3. Liga II teams - 3 over-age (U23) players on the pitch; windows 1 Jul - 1 Sep, 1 Jan - 1 Feb.
#   ESP: Primera Federacion filial - 4 over-age; windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   NED: Jong / U21 in the Eerste Divisie - count-only (no cap in the game: the real rule counts appearances, <15
#        apps, which SWOS does not keep - approximate); windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   POR: Liga 2 B teams - generic U23 + 4 over-age; windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   AUS / NZL: A-League youth / reserves - generic U23 + 4 (TO CONFIRM); windows A-League 2026-27 (TO CONFIRM).
RULES = {
    'ita': (4, 23, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'ger': (3, 23, (('1/7', '1/9'), ('1/1+1', '1/2+1'))),
    'esp': (4, 23, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'ned': (0xFF, 23, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'por': (4, 23, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'aus': (4, 23, (('1/7', '30/9'), ('1/1+1', '31/1+1'))),
    'nzl': (4, 23, (('1/7', '30/9'), ('1/1+1', '31/1+1'))),
}
RULE_IDS = list(RULES)
MAX_MATCH = 4                   # (1) at most 4 called up for one match
MAX_WINDOW = 3                  # (2) at most 3 attached in one window


def team_word(pk, key):
    f, i = pk.where[key]
    return f | i << 8


def links(packs):
    """[(world, pack of B, B key, pack of parent, parent key, rules)] for every B team of the career worlds."""
    by_country = {}
    for pk in packs:
        if pk.world is not None:
            by_country.setdefault((pk.world, pk.meta.get('id', '').rsplit('-', 1)[-1].upper()), pk)
    out = []
    for pk in packs:
        if pk.world is None:
            continue
        st = (pk.league or {}).get('second_teams') or {}
        for k, c in pk.clubs.items():
            par = c.get('second_of')
            if not par:
                continue
            ppk = pk
            if ':' in par:                      # (NZ reserves: 'AUS:auckland', the parent in another country's pack)
                cc, par = par.split(':')
                ppk = by_country.get((pk.world, cc))
                assert ppk is not None, f'bteam: {k}: no pack for {cc}'
            assert par in ppk.clubs, f'bteam: {k}: parent {par} not in {ppk.meta.get("id")}'
            r = st.get('rules')
            assert r in RULES, f'bteam: {k}: rules {r!r} not in bteam.RULES'
            out.append((pk.world, pk, k, ppk, par, r))
    return out


def ages(pk, key):
    """Age codes (birth year - 1900, 0 = unknown) of the club's players in record order (places 1..16, then XTRA)."""
    out = []
    for row in pk.prows[key]:
        b = (row.get('born') or '').strip()
        out.append(int(b) - 1900 if b.isdigit() and 1901 <= int(b) <= 2155 else 0)
    return out


def bage(packs):
    """{'BAGE.nnn': bytes} per world with B teams."""
    by_world = {}
    for w, pk, k, ppk, par, r in links(packs):
        by_world.setdefault(w, []).append((team_word(pk, k), team_word(ppk, par), RULE_IDS.index(r), ages(pk, k)))
    out = {}
    for w, rows in sorted(by_world.items()):
        d = b'BA' + bytes((1, len(rows)))
        for bw, pw, ri, a in rows:
            assert len(a) <= 30, (w, bw, len(a))
            d += struct.pack('<HHBB', bw, pw, ri, len(a)) + bytes(a)
        d += b'BR' + bytes((len(RULE_IDS),))
        for r in RULE_IDS:
            cap, u, wins = RULES[r]
            d += bytes((cap, u, len(wins))) + b''.join(bytes((split.week_of(a), split.week_of(b))) for a, b in wins)
        out['BAGE.%03d' % w] = d
    return out


def files():
    """mkpatcher / patch.py: the names (and bytes) of the build's BAGE files."""
    import mkseason
    return bage(mkseason.packs())


def write(data_dir):
    """patch.py: the BAGE files into the build's DATA; a summary line."""
    fs = files()
    for n, d in fs.items():
        with open(os.path.join(data_dir, n), 'wb') as f:
            f.write(d)
    return ', '.join(f'{n} {len(d)} B' for n, d in fs.items()) or 'none (no B teams)'
