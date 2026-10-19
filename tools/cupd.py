"""Coppa Italia Serie D (World 2026-27): a knockout of every Serie D club (162; 156 in the world's file) at its real
dates, on gplay's engine (gplay.c 'The Coppa Italia Serie D'). The career club's ties are played in slot 4 (a 1-tie
contest built at the calendar advance before the round's week, as gplay's other mid-season contests); every other tie
is decided at that advance: in the world's first season by its real result when known, else by gplay's tie rules.

Data: the pack's league key "cup_d": {"file": "<json in the pack dir>"} - the data session's
internal/world2526/formats/coppa_italia_serie_d_2627.json shape (coppa_d.py): rounds [{name, date ('dd/mm[+1]',
two for two legs), legs, rule, host ('drawn' | 'alternate' | 'listed'), pairing ('draw'), matches [{home_key,
away_key, home_from, away_from ('W<i>': the winner of match i of the previous round), winner (tm id), home, away,
played}]}], clubs [{tm, key, file ('league' | 'pool' | None)}]. A round listing fewer ties than half the previous
round's are completed from the previous round's unused winners, in order (TM leaves a tie out while one before it is
undecided).

Later seasons (gplay.c cd_make): CD_DT = db the first Serie D division, its groups; dw the file's global base;
256 x db each ordinal's base division (FFh: no league club) - the season's Serie D clubs from someLeaguesTable.

Table (CD_TAB, gplay.patch): db world, rounds, team file, -; per round db week1, week2 (two legs, else 0), legs,
host (0 listed, 2 drawn, 4 alternate), ties, flags (1 = the pairs drawn, 2 = penalties without extra time); dw the
first tie's index; then per tie dw a, b (a team word, or REF = index << 8 | FFh: a previous round's tie (a team word's file is never 255; FEFFh = drawn), or 0 = a club outside
the file: its tie needs a real result), db the real winner (0 unknown, 1 a, 2 b), db -.
"""
import json
import os
import struct

HOST = {'listed': 0, 'drawn': 2, 'alternate': 4}
DRAWN = 0xFEFF


def REF(i):                     # (a previous round's tie: gplay.c CD_REF; not 8000h | i - an ordinal 128+ sets bit 15)
    assert 0 <= i < 0xFE, i
    return i << 8 | 0xFF
MAXT = 168


def _weeks(date):
    import split
    ds = [x for x in str(date).split() if '/' in x and x[0].isdigit()]
    ws = [split.week_of(d.strip(',')) for d in ds[:2]]
    return ws + [0] * (2 - len(ws))


def compile_table(d, word):
    """d: the bracket json; word: club key -> team word (file | ordinal << 8), or None outside the file. Returns the
    table's bytes and a summary."""
    rounds, ties, nprev = [], [], 0
    for ri, r in enumerate(d['rounds']):
        ms = list(r.get('matches') or [])
        w1, w2 = _weeks(r.get('date', ''))
        legs = r.get('legs', 1)
        draw = r.get('pairing') == 'draw'
        n = len(ms) if ri < 2 else nprev // 2       # (rounds 0-1: as listed, byes entering at 1; then halving)
        first, used = len(ties), set()
        for m in ms:
            for side in ('home', 'away'):
                f = m.get(side + '_from')
                if f:
                    used.add(int(f[1:]))
        free = [i for i in range(nprev) if i not in used] if ri else []
        for k in range(n):
            if k < len(ms) and not draw:
                m = ms[k]
                ab = []
                for side in ('home', 'away'):
                    f, key = m.get(side + '_from'), m.get(side + '_key')
                    if f and ri:
                        ab.append(REF(int(f[1:]) + (first - nprev)))
                    else:
                        ab.append(word(key) or 0)
                win = 0
                if m.get('played') and m.get('winner') is not None:
                    win = 1 if m['winner'] == m.get('home') else 2 if m['winner'] == m.get('away') else 0
                ties.append((ab[0], ab[1], win))
            else:                       # (a tie TM leaves out / a drawn round: the previous round's free winners)
                if draw:
                    a = b = DRAWN               # (drawn at run time from the previous round's winners)
                else:
                    a, b = REF(free.pop(0) + first - nprev), REF(free.pop(0) + first - nprev)
                ties.append((a, b, 0))
        if r.get('legs', 1) == 2 and not w2:
            w2 = w1 + 2
        flags = (1 if draw else 0) | (2 if 'pens' in str(r.get('rule', 'pens')) else 0)
        rounds.append((w1, w2 if legs == 2 else 0, legs, HOST.get(r.get('host', 'drawn'), 2), n, flags, first))
        nprev = n
    assert len(ties) <= MAXT, len(ties)
    out = bytearray()
    for w1, w2, legs, host, n, flags, first in rounds:
        out += bytes((w1, w2, legs, host, n, flags)) + struct.pack('<H', first)
    for a, b, win in ties:
        out += struct.pack('<HHBB', a, b, win, 0)
    return bytes(out), len(rounds), len(ties)


def pack_table(pk):
    """A pack's 'cup_d' (league key): None, or (world, team file, table bytes, rounds, ties, names, CD_DT bytes)."""
    lg = pk.league
    if not lg or pk.world is None or not lg.get('cup_d'):
        return None
    c = lg['cup_d']
    d = json.load(open(os.path.join(pk.path, c['file'])))

    lfile = pk.files[lg['clubs']][0]
    assert lfile != 255, 'cup_d: team file 255 (its words would read as tie references)'

    def word(key):                      # (a club of the league's own file; the pool's are off-file: 0)
        if not key or key not in pk.where or pk.where[key][0] != lfile:
            return None
        fl, i = pk.where[key]
        return fl | i << 8
    tab, nr, nt = compile_table(d, word)
    par = lg.get('parallel') or []
    par = par if isinstance(par, list) else [par]
    assert par, 'cup_d: the league needs its Serie D level of groups (parallel)'
    df, dc = par[-1]['first'], par[-1]['count']
    gbase = next(b for ff, b in pk.files.values() if ff == lfile)
    base = [0xFF] * 256
    for k in pk.league_clubs:
        fl, i = pk.where[k]
        if fl == lfile:
            base[i] = pk.division[k]
    nd = sum(1 for b in base if df <= b < df + dc)
    assert nr >= 3 and 2 << (nr - 2) < nd <= (2 << (nr - 2)) + 41, f'cup_d: {nd} Serie D clubs for {nr} rounds'
    dt = bytes((df, dc)) + struct.pack('<H', gbase) + bytes(base)
    return (pk.world, lfile, tab, nr, nt, c.get('names') or {'*': ['COPPA ITALIA SERIE D', 'COPPA IT SERIE D']},
            dt)
