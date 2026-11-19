"""POSITION TRAITS (2), gate D5 (internal/handoff/trhead-design.md): the forced wide kicks of `swostest.py run trhd_whip`
(spmeter MODE 4: every case is a kick with 'back' held, made through the game's own PlayerKickingBall and
ApplyBallAfterTouch) against the rule. The rules live here, the exe only records.

  python3 tools/tr_whip.py RUNS/trhd_whip.jsonl [--md out.md]

Case k (spmeter MODE 4): bit 0 the team (0 = the top structure's, attacking the bottom goal), bit 1 the side (0 left),
bit 2 the direction (1 toward the centre line), bits 3-4 the kicker's forced file position (RW LW M A), k >> 5 the
spot. Expected with RUOLI SI: the whip (ball deltaZ = TR_WDZ, speed = TR_WSP: a kick along the x axis gets none of the
game's slow-downs) only for RW / LW, from a spot inside the wide attacking zone (x <= 183 from the nearer touchline
side, <= TR_WZ px from the attacked goal line; the corner spot counts), toward the centre; every other case the game's
high ball (deltaZ 0x20000, speed 2688, x 0.75 = 2016 for a kick straight up / down the pitch). RUOLI NO: the high ball
in every case. The window's highest z is reported (a whip that nobody touches peaks under 14 px, the high ball over
30) and checked only when no player touched the ball in the window.
"""
import argparse
import json
import struct

POS = ('RW', 'LW', 'M', 'A')
WPX = (120, 183, 184, 120, 81, 150)      # spmeter's spots (left side) - asserted against the build by the scenario
WPA = (40, 160, 40, 161, 0, 100)
NCASE = 192
HIGH_DZ, HIGH_SP = 0x20000, 2688


def case(k):
    spot = k >> 5
    return dict(k=k, top=not k & 1, right=bool(k & 2), centre=bool(k & 4), pos=POS[k >> 3 & 3], spot=spot,
                x=WPX[spot], a=WPA[spot])


def expect(k, ruoli, wz=160, wdz=0x10000, wsp=4096):
    """(deltaZ, speed, whip?) of case k."""
    c = case(k)
    whip = bool(ruoli and c['pos'] in ('RW', 'LW') and c['x'] <= 183 and c['a'] <= wz and c['centre'])
    if whip:
        return wdz, wsp, True
    return HIGH_DZ, HIGH_SP if c['centre'] else HIGH_SP - (HIGH_SP >> 2), False


def entries(raw):
    for i in range(0, len(raw) - 15, 16):
        f, t = struct.unpack_from('<HB', raw, i)
        if t == 17:
            k, pos, dr, ordn, team, dz, sp = struct.unpack_from('<BBBBBIH', raw, i + 3)
            yield dict(f=f, t=17, k=k, pos=pos, dir=dr, ord=ordn, team=team, dz=dz, sp=sp)
        else:
            gs, gsp, team, ordn, pst, x, y, z = struct.unpack_from('<BBBBBhhh', raw, i + 3)
            yield dict(f=f, t=t, ord=ordn, x=x, y=y, z=z)


def classify(rows, wz=160, wdz=0x10000, wsp=4096):
    """rows: the scenario's json lines (ruoli, k0, log hex). -> (errors, per-(ruoli) summary dict)."""
    errs, summ = [], {}
    for ru in sorted({r['ruoli'] for r in rows}):
        seen, peaks = {}, {True: [], False: []}
        for r in (x for x in rows if x['ruoli'] == ru and 'log' in x):
            es = list(entries(bytes.fromhex(r['log'])))
            for i, e in enumerate(es):
                if e['t'] != 17:
                    continue
                c = case(e['k'])
                wdz_, wsp_, whip = expect(e['k'], ru, wz, wdz, wsp)
                if e['k'] in seen:
                    errs.append(f'RUOLI {ru} case {e["k"]}: logged twice')
                seen[e['k']] = (e['dz'], e['sp'])
                if e['pos'] != 4 + (e['k'] >> 3 & 3) or e['team'] != (e['k'] & 1):
                    errs.append(f'RUOLI {ru} case {e["k"]}: forced position / team {e["pos"]} / {e["team"]}')
                if (e['dz'], e['sp']) != (wdz_, wsp_):
                    errs.append(f'RUOLI {ru} case {e["k"]} {c}: deltaZ {e["dz"]:#x} speed {e["sp"]} (want {wdz_:#x} {wsp_}'
                                f'{", the whip" if whip else ""})')
                touched, peak = False, None
                for n in es[i + 1:]:
                    if n['t'] == 17:
                        break
                    if n['t'] in (3, 7, 8):
                        touched = True
                    if n['t'] == 18:
                        peak = n['z']
                        break
                if peak is not None and not touched:
                    peaks[whip].append(peak)
                    if whip and peak > 14:
                        errs.append(f'RUOLI {ru} case {e["k"]}: an untouched whip peaked at z {peak} (> 14)')
                    if not whip and c['centre'] and peak < 30:
                        errs.append(f'RUOLI {ru} case {e["k"]}: an untouched high ball peaked at z {peak} (< 30)')
        miss = [k for k in range(NCASE) if k not in seen]
        if miss:
            errs.append(f'RUOLI {ru}: {len(miss)} of {NCASE} cases not played (first {miss[:8]})')
        nw = sum(1 for k in seen if expect(k, ru, wz, wdz, wsp)[2])
        summ[ru] = dict(cases=len(seen), whips_expected=nw,
                        whips=sum(1 for k, v in seen.items() if v[0] == wdz and ru),
                        untouched_whip_peaks=sorted(set(peaks[True])), untouched_high_peaks=sorted(set(peaks[False])))
    return errs, summ


def main():
    a = argparse.ArgumentParser()
    a.add_argument('jsonl', nargs='+')
    a.add_argument('--md')
    o = a.parse_args()
    rows = [json.loads(l) for p in o.jsonl for l in open(p)]
    errs, summ = classify(rows)
    lines = ['# POSITION TRAITS (2): forced wide kicks (gate D5)', '',
             '| RUOLI | cases | whips (expected) | untouched whip peaks z | untouched high-ball peaks z |', '|---|---|---|---|---|']
    for ru, s in summ.items():
        lines.append(f"| {'SI' if ru else 'NO'} | {s['cases']} / {NCASE} | {s['whips']} ({s['whips_expected']}) | "
                     f"{s['untouched_whip_peaks']} | {s['untouched_high_peaks']} |")
    lines += ['', f'{len(errs)} errors' + (':' if errs else '')] + [f'- {e}' for e in errs[:40]]
    txt = '\n'.join(lines) + '\n'
    print(txt)
    if o.md:
        open(o.md, 'w').write(txt)
    return not errs


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
