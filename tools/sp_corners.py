#!/usr/bin/env python3
"""4.2 set pieces M3: classify the corner meter's logs (tools/spmeter.py, scenario sp_corners) and print a table.

    python3 tools/sp_corners.py ROWS.jsonl [...] [-v]      # one row per match; -v lists every corner

Per corner (the log from its FORCE entry to the next one):
- attacking team = the taker's (the first touch while the corner state is up);
- outcome = the first of: GOAL (the attacking team's goals + 1), OWN GOAL / CONCEDED (the other side's), OVER (the
  ball left over the goal line between the posts, x 302..366, above the bar z > 15), WIDE (over the goal line
  elsewhere: a goal kick), CORNER (out again for a corner), KEEPER CATCH / KEEPER CLAIM (the keeper holds it -
  gameState 3 - after a catch, playerState 4, or a claim, 11; CLAIM6 = a claim in his 6-yard box), THROW-IN, FOUL,
  else PLAY ON (the window ended with the ball in play);
- headers: a touch by a player in a heading state (8 static, 9 jump). An attacking header is ON TARGET when what
  follows it, before any other player's touch, is a goal or the keeper (a touch, a save state, a catch / claim); OVER /
  WIDE when the ball leaves over the goal line; else BLOCKED / PLAY ON.
Pitch: goal lines y 129 / 769, goal mouth x 302..366, bar z 15, the 6-yard box 22 px deep (keeper-setpieces-study).
"""
import collections
import json
import math
import struct
import sys

T_FORCE, T_GS, T_TOUCH, T_GOALS, T_GSP, T_END, T_KEEPER, T_PST, T_FAIL, T_KICK = 1, 2, 3, 4, 5, 6, 7, 8, 10, 11
SIX = 22


def entries(hexlog):
    b = bytes.fromhex(hexlog)
    for i in range(0, len(b), 16):
        f, t, gs, gsp, tm, od, ps, x, y, z, g1, g2 = struct.unpack('<HBBBBBBhhhBB', b[i:i + 16])
        yield dict(f=f, t=t, gs=gs, gsp=gsp, team=tm, ord=od, ps=ps, x=x, y=y, z=z, g=(g1, g2))


def corners(hexlog):
    cur = None
    for e in entries(hexlog):
        if e['t'] == T_FORCE:
            if cur:
                yield cur
            cur = [e]
        elif cur is not None:
            cur.append(e)
    if cur:
        yield cur


def in_six(y):
    return y < 129 + SIX or y > 769 - SIX


def classify(ev):
    """dict(team, outcome, headers=[(team, result)], ...) for one corner's entries."""
    r = dict(team=None, outcome=None, headers=[], kicked=False, attempts=0)
    g0 = ev[0]['g']
    k = 0
    for k, e in enumerate(ev):                    # the taker: the first touch with the corner state up
        if e['t'] == T_TOUCH and e['gs'] in (4, 5):
            r['team'] = e['team']
            break
    if r['team'] is None:
        r['outcome'] = 'NO TAKER'
        return r
    att = r['team']
    kick = next((j for j in range(k, len(ev)) if ev[j]['t'] == T_KICK), None)
    if kick is None:
        r['outcome'] = 'NOT KICKED'
        return r
    r['kicked'] = True
    seq = ev[kick + 1:]
    last_keeper_ps = None
    open_header = None                              # (index in r['headers']) awaiting its result

    def close(res):
        nonlocal open_header
        if open_header is not None:
            r['headers'][open_header] = (r['headers'][open_header][0], res)
            open_header = None

    for e in seq:
        t = e['t']
        if t == T_PST and e['ps'] in (8, 9):
            if e['team'] == att:
                r['attempts'] += 1
            continue
        if t == T_PST and e['ord'] == 1 and e['ps'] in (4, 6, 7, 11):
            last_keeper_ps = e['ps']
            if open_header is not None and e['team'] != r['headers'][open_header][0]:
                close('ON TARGET')
            continue
        if t == T_KEEPER:
            continue                                # (lastKeeperPlayed: bookkeeping, not a touch)
        if t == T_TOUCH and e['ord'] == 1 and e['ps'] in (4, 6, 7, 11):
            last_keeper_ps = e['ps']
        if t == T_TOUCH:
            if e['ps'] in (8, 9) and e['ord'] != 1:
                close('BLOCKED' if e['team'] != (r['headers'][open_header][0] if open_header is not None else e['team'])
                      else 'PLAY ON')
                r['headers'].append((e['team'], None))
                open_header = len(r['headers']) - 1
                continue
            if open_header is not None:
                if e['ord'] == 1 and e['team'] != r['headers'][open_header][0]:
                    close('ON TARGET')
                else:
                    close('BLOCKED' if e['team'] != r['headers'][open_header][0] else 'PLAY ON')
            continue
        if t == T_GOALS:
            side = 0 if e['g'][0] != g0[0] else 1
            scorer_team = side + 1
            # (the goals are statsTeam1 / 2: team numbers 1 / 2)
            r['outcome'] = 'GOAL' if scorer_team == att else 'CONCEDED'
            close('ON TARGET' if scorer_team == (r['headers'][open_header][0] if open_header is not None else 0)
                  else 'OTHER')
            return r
        if t == T_GS:
            gs = e['gs']
            if gs in (1, 2, 4, 5):
                over_line = e['y'] < 129 or e['y'] > 769
                mouth = 302 <= e['x'] - 1 <= 366
                if over_line and mouth and e['z'] > 15:
                    res = 'OVER'
                elif gs in (4, 5):
                    res = 'CORNER'
                else:
                    res = 'WIDE'
                r['outcome'] = res
                close('OVER' if res == 'OVER' else 'WIDE')
                return r
            if gs == 3:
                claim = last_keeper_ps == 11
                r['outcome'] = ('KEEPER CLAIM6' if in_six(e['y']) else 'KEEPER CLAIM') if claim else 'KEEPER CATCH'
                close('ON TARGET')
                return r
            if 15 <= gs <= 20:
                r['outcome'] = 'THROW-IN'
                close('WIDE')
                return r
            if gs in (6, 7, 8, 9, 10, 11, 12, 13, 14):
                r['outcome'] = 'FOUL'
                close('OTHER')
                return r
            if gs == 0:
                continue                            # (players to the initial positions: the goal entry follows)
        if t == T_END:
            break
    r['outcome'] = r['outcome'] or 'PLAY ON'
    close('PLAY ON')
    return r


def se_pct(k, n):
    if not n:
        return '-'
    p = k / n
    return f'{100 * p:.1f}% +-{100 * math.sqrt(p * (1 - p) / n):.1f}'


def main(argv):
    files = [a for a in argv if not a.startswith('-')]
    verbose = '-v' in argv
    by = collections.defaultdict(list)
    meta = collections.defaultdict(lambda: collections.Counter())
    for fn in files:
        for line in open(fn):
            row = json.loads(line)
            if 'log' not in row:
                meta[row.get('variant', '?')]['errors'] += 1
                continue
            v = row['variant']
            meta[v]['matches'] += 1
            meta[v]['nfail'] += row['nfail']
            meta[v]['drop'] += row['drop']
            for i, ev in enumerate(corners(row['log'])):
                c = classify(ev)
                by[v].append(c)
                if verbose:
                    print(v, row['pairing'], row['seed'], i, c)
    outs = ['GOAL', 'OVER', 'WIDE', 'CORNER', 'KEEPER CATCH', 'KEEPER CLAIM', 'KEEPER CLAIM6', 'THROW-IN', 'FOUL',
            'PLAY ON', 'CONCEDED', 'NOT KICKED', 'NO TAKER']
    for v, cs in sorted(by.items()):
        kicked = [c for c in cs if c['kicked']]
        n = len(kicked)
        cnt = collections.Counter(c['outcome'] for c in kicked)
        hs = [h for c in kicked for h in c['headers'] if h[0] == c['team']]
        hn = len(hs)
        hc = collections.Counter(h[1] for h in hs)
        att = sum(c['attempts'] for c in kicked)
        print(f'== {v}: {meta[v]["matches"]} matches, {len(cs)} corners ({n} kicked), force fails {meta[v]["nfail"]}, '
              f'log drops {meta[v]["drop"]}')
        print('   outcomes: ' + ', '.join(f'{o} {cnt[o]} ({se_pct(cnt[o], n)})' for o in outs if cnt[o]))
        print(f'   attacking headers: {hn} contacts / {att} attempts; per corner {hn / n if n else 0:.2f}; '
              + ', '.join(f'{k} {v2} ({se_pct(v2, hn)})' for k, v2 in hc.most_common()))
        print(f'   corners with an attacking header: {se_pct(sum(1 for c in kicked if any(h[0] == c["team"] for h in c["headers"])), n)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
