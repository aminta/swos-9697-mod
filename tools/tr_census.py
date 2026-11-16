"""POSITION TRAITS (2) measure (Mercato 16/11, trhead-design.md section C): how often is a long / high ball played
from Marco's wide attacking zones, and by whom. Reads the json lines of `swostest.py run sp_corners` on a census build
(SPC_ENV=SP_METER_MODE=3,SP_METER_WIN=100: spmeter MODE 3 logs every touch in a wide band near a goal line with the
toucher's FILE position, and the ball's height level after it). The rules live here, the exe only records.

  python3 tools/tr_census.py RUNS/sp_corners.jsonl [--wz 160] [--md out.md]

Zone (Marco's 5 x 4 grid): x <= 183 or x >= 488, and within WZ px of the goal line the toucher's team ATTACKS
(topTeamData attacks down: y >= 769 - WZ; bottomTeamData up: y <= 129 + WZ). A kick's class = the highest ball level
before the next touch: 0 ground, 1 drive (z > 10), 2 lofted (z > 18), 3 high (z > 30; the 'back' after-touch peaks
at ~42 px, a normal long kick at ~22). Header after = a header state (8 / 9) logged within 100 frames of the kick.
"""
import argparse
import collections
import json
import struct

POS = ('GK', 'RB', 'LB', 'D', 'RW', 'LW', 'M', 'A')
CLS = ('ground', 'drive', 'lofted', 'high')


def entries(raw):
    for k in range(0, len(raw) - 15, 16):
        f, t, gs, gsp, team, ordn, pst, x, y, z, g1, g2 = struct.unpack_from('<HBBBBBBhhhBB', raw, k)
        yield dict(f=f, t=t, team=team, ord=ordn, pst=pst, x=x, y=y, z=z)


def in_zone(e, wz):
    top = e['pst'] & 0x80
    if not (e['x'] <= 183 or e['x'] >= 488):
        return False
    return e['y'] >= 769 - wz if top else e['y'] <= 129 + wz


def classify(rows, wz):
    out = collections.Counter()
    per = []
    for r in rows:
        if 'log' not in r:
            continue
        es = list(entries(bytes.fromhex(r['log'])))
        c = collections.Counter()
        for i, e in enumerate(es):
            if e['t'] != 15 or not in_zone(e, wz):
                continue
            lvl, head = 0, False
            for n in es[i + 1:]:
                if n['t'] == 15 or n['t'] == 6:
                    break
                if n['t'] in (12, 13, 14):
                    lvl = max(lvl, n['t'] - 11)
            for n in es[i + 1:]:
                if (n['f'] - e['f']) & 0xFFFF > 100:
                    break
                if n['t'] == 8 and n['pst'] in (8, 9):
                    head = True
                    break
            p = e['pst'] & 7 if e['pst'] != 0xFF else None
            role = 'W' if p in (4, 5) else 'other'
            c[(role, CLS[lvl])] += 1
            if head:
                c[(role, CLS[lvl], 'header')] += 1
        per.append((r.get('pairing'), r.get('seed'), r.get('frames'), r.get('drop'), c))
        out.update(c)
    return out, per


def main():
    a = argparse.ArgumentParser()
    a.add_argument('jsonl', nargs='+')
    a.add_argument('--wz', type=int, default=160)
    a.add_argument('--md')
    o = a.parse_args()
    rows = [json.loads(l) for p in o.jsonl for l in open(p)]
    tot, per = classify(rows, o.wz)
    n = len(per) or 1
    lines = [f'# Traits (2) measure: zone touches (WZ {o.wz} px), {len(per)} matches', '',
             '| Toucher | ' + ' | '.join(CLS) + ' | high + header after |', '|---|' + '---|' * (len(CLS) + 1)]
    for role in ('W', 'other'):
        cells = [f"{tot[(role, c)]} ({tot[(role, c)] / n:.2f}/m)" for c in CLS]
        lines.append(f"| {'RW / LW (file)' if role == 'W' else 'others'} | " + ' | '.join(cells) +
                     f" | {tot[(role, 'high', 'header')]} |")
    lines += ['', '| pairing | seed | frames | dropped | W high | W lofted | others high |', '|---|---|---|---|---|---|---|']
    for pr, sd, fr, dr, c in per:
        lines.append(f"| {pr} | {sd} | {fr} | {dr} | {c[('W', 'high')]} | {c[('W', 'lofted')]} | {c[('other', 'high')]} |")
    txt = '\n'.join(lines) + '\n'
    print(txt)
    if o.md:
        open(o.md, 'w').write(txt)


if __name__ == '__main__':
    main()
