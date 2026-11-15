"""5.0 NT piece (1) fixtures (Nazionali exe, MC 15/11 D1 / D2): a SYNTHETIC world national pack with the 211-NT layout of
internal/handoff/nt-layout-42nats9.json - six files of 55 / 53 / 10 / 35 / 47 / 11 teams with explicit global bases 2409 / 2464 /
2517 / 2527 / 2562 / 2609 (G1'), physical files 200..205 standing for the game's 80..85 - so the build side (mkseason.NationalPack,
bigtables.limit_all / nt_files) can be tested without the real squads (not built yet). Squads are empty: a fixture, never data.
make(dir, **over) writes the pack into dir and returns it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
COUNTS = (55, 53, 10, 35, 47, 11)                  # nt-layout-42nats9: the files' sizes (143 game + 68 appended)
BASES = (2409, 2464, 2517, 2527, 2562, 2609)


def make(path, counts=COUNTS, bases=BASES, world=5, physical=200, extra=None, players=False):
    os.makedirs(path, exist_ok=True)
    files = {f'nat{80 + i}': {'file': physical + i, 'base': bases[i], 'as': 80 + i} for i in range(6)}
    meta = {'format': 1, 'id': 'nt-fixture', 'kind': 'national', 'world': world, 'files': files,
            'squads': [{'files': list(files), 'method': 'explicit'}]}
    meta.update(extra or {})
    json.dump(meta, open(os.path.join(path, 'pack.json'), 'w'))
    rows = ['key,name,coach,country,file,division,tactic,kit1,kit2,lineup,source']
    for i in range(6):
        for k in range(counts[i]):
            rows.append(f'nt{80 + i}_{k},TEAM{80 + i}_{k},,ALB,nat{80 + i},0,3,0 4 4 4 4,0 1 1 1 1,'
                        f'0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15,fixture')
    open(os.path.join(path, 'clubs.csv'), 'w').write('\n'.join(rows) + '\n')
    prow = ['club,name,role,position,number,nat,skin,pa,ve,he,ta,co,sp,fi,price']
    shape = [('G', 'G'), ('D', 'RB'), ('D', 'LB'), ('D', 'D'), ('D', 'D'), ('M', 'RW'), ('M', 'LW'), ('M', 'M'), ('M', 'M'), ('A', 'A'),
             ('A', 'A'), ('G', 'G'), ('D', 'D'), ('M', 'M'), ('A', 'A'), ('D', 'LB')]          # (albania80's 16: the game's squad shape)
    if players:                                       # (generic squads: 16 players a team, the fixture is never data)
        for i in range(6):
            for k in range(counts[i]):
                for j, (ro, po) in enumerate(shape):
                    prow.append(f'nt{80 + i}_{k},PLAYER {80 + i} {k} {j},{ro},{po},{j + 1},0,light,2*,2*,2*,2,2,2,2,14')
    open(os.path.join(path, 'players.csv'), 'w').write('\n'.join(prow) + '\n')
    import mkseason
    return mkseason.NationalPack(path)
