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
[GP_CD2 builds (cd2: a league over two files, S7-G): dw base2, dw ord2 - the file's rows from ord2 on are global
base2 + ordinal - ord2];
256 x db each ordinal's base division (FFh: no league club) - the season's Serie D clubs from someLeaguesTable;
then the strengths (gplay.c cd_str, the ties nobody plays): dw the file's off-file pool map offset in RI_STATE.maps
(FFFFh: none), its map words, the pool's records; 256 x dw each ordinal's strength; pool records x dw theirs. A
strength = the best 11 players' prices (players.csv), at least 5, as statespec's statesim.

Table (CD_TAB, gplay.patch): db world, rounds, team file, -; per round db week1, week2 (two legs, else 0), legs,
host (0 listed, 2 drawn, 4 alternate), ties, flags (1 = the pairs drawn, 2 = penalties without extra time); dw the
first tie's index; then per tie dw a, b (a team word, or REF = index << 8 | FFh: a previous round's tie (a team word's file is never 255; FEFFh = drawn), or 0 = a club outside
the file: its tie needs a real result), db the real winner (0 unknown, 1 a, 2 b), db -.
"""
import globnum
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
        assert not draw or n <= 2, (f"cup_d: round {ri} ({r.get('name')}) drawn with {n} ties - gplay.c draws at most 2 "
                                    f"(cd_side reads CD_ST.sd[4]: a 3rd tie would read past it)")
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


def strength(pk, key):
    """The best 11 players' prices (players.csv), at least 5 (statespec.club_strength's rule)."""
    pr = sorted((int(r.get('price') or 0) for r in pk.prows.get(key, [])), reverse=True)
    return max(5, min(0xFFFF, sum(pr[:11])))


def strengths(pk, lfile):
    """CD_DT's strength part: the pool map's offset / words / pool records (ripool.layout), the file's 256 ordinals,
    the pool records (an identity >= 256 = pool record id - 256, ripool's order: pk.pool_clubs)."""
    import mkseason
    import ripool
    tabs = mkseason.off_pools()
    lay = ripool.layout(tabs)[0] if tabs else []
    moff, nmap = 0xFFFF, 0
    for (world, fl, *_), (mo, nm, *_r) in zip(tabs, lay):
        if world == pk.world and fl == lfile:
            moff, nmap = mo, nm
    pool = list(pk.pool_clubs) if moff != 0xFFFF else []
    st = [5] * 256
    for k in pk.clubs:
        fl, i = pk.where.get(k, (None, None))
        if fl == lfile and i < 256:
            st[i] = strength(pk, k)
    return (struct.pack('<HHH', moff, nmap, len(pool)) + struct.pack('<256H', *st)
            + b''.join(struct.pack('<H', strength(pk, k)) for k in pool))


def other_strengths(pk, lfile):
    """S7 (s7-ri-fix.md, MC 13/11): (the OTHER league file's number, [strength of each of its rows]) - s7ri.c's S7RI_STRF /
    S7RI_STR (obj4, written by s7swap.py: only S7 code reads them, so they stay out of the gplay pages), the same rule as
    strength(): a club of the other file sitting in this file's rows is seeded by its real strength (its home row)."""
    other = [f for f in pk.league_files() if f != lfile]
    assert len(other) == 1, ('cupd: S7 league files', pk.league_files(), lfile)
    rows = {}
    for k in pk.clubs:
        fl, i = pk.where.get(k, (None, None))
        if fl == other[0]:
            rows[i] = strength(pk, k)
    n = max(rows) + 1 if rows else 0
    return other[0], [rows.get(i, 5) for i in range(n)]


def cd2():
    """True in a build with a league over two team files (globnum.exe_split): gplay.c is compiled with GP_CD2 and
    every CD_DT carries base2 / ord2 (head); else today's CD_DT bytes exactly."""
    return globnum.exe_split() is not None


def head(pk, lfile, df, dc):
    """CD_DT's head: db first Serie D division, groups; dw the file's global base (run 1); [cd2 builds: dw base2, dw
    ord2 - run 2's first global and its first ordinal (S7-G: globnum.runs_of), FFFFh / 256 for a one-run file]."""
    runs = globnum.runs_of(pk, lfile)
    assert len(runs) <= 2, f'CD_DT: file {lfile} over {len(runs)} runs'
    out = bytes((df, dc)) + struct.pack('<H', runs[0][0])
    if cd2():
        out += struct.pack('<HH', *((runs[1][0], runs[0][1]) if len(runs) == 2 else (0xFFFF, 256)))
    else:
        assert len(runs) == 1, f'CD_DT: file {lfile} in two runs without GP_CD2'
    return out


def pack_table(pk):
    """A pack's 'cup_d' (league key): None, or (world, team file, table bytes, rounds, ties, names, CD_DT bytes)."""
    lg = pk.league
    if not lg or pk.world is None or not lg.get('cup_d'):
        return None
    c = lg['cup_d']
    d = json.load(open(os.path.join(pk.path, c['file'])))

    par0 = lg.get('parallel') or []         # (S7: Serie D's file = div_file of its first division; dormant: the league's)
    lfile = pk.div_file((par0 if isinstance(par0, list) else [par0])[-1]['first'] if par0 else 0)[0]
    assert lfile != 255, 'cup_d: team file 255 (its words would read as tie references)'
    assert not getattr(pk, 'shaped', False) or lfile == pk.league_files()[-1], \
        ('cup_d: a shaped pack\'s Coppa D must follow the Serie D file (league_b), else it silently has no Serie D clubs', lfile, pk.league_files())

    def word(key):                      # (a club of the league's own file; the pool's are off-file: 0)
        if not key or key not in pk.where or pk.where[key][0] not in pk.league_files():   # (S7: file A or B)
            return None
        fl, i = pk.where[key]
        return fl | i << 8
    tab, nr, nt = compile_table(d, word)
    par = lg.get('parallel') or []
    par = par if isinstance(par, list) else [par]
    assert par, 'cup_d: the league needs its Serie D level of groups (parallel)'
    df, dc = par[-1]['first'], par[-1]['count']
    base = [0xFF] * 256
    for k in pk.league_clubs:
        fl, i = pk.where[k]
        if fl == lfile:
            base[i] = pk.division[k]
    nd = sum(1 for b in base if df <= b < df + dc)
    assert nr >= 3 and 2 << (nr - 2) < nd <= (2 << (nr - 2)) + 41, f'cup_d: {nd} Serie D clubs for {nr} rounds'
    dt = head(pk, lfile, df, dc) + bytes(base) + strengths(pk, lfile)
    return (pk.world, lfile, tab, nr, nt, c.get('names') or {'*': ['COPPA ITALIA SERIE D', 'COPPA IT SERIE D']},
            dt)
