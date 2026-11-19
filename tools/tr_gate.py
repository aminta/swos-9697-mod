"""POSITION TRAITS (1) / (3), gates D4 / D6 (internal/handoff/trhead-design.md): the rules for the forced headers of
`swostest.py run trhd_headers` (spmeter MODE 5, entry 19) and the forced reach cases of `trhd_reach` (MODE 6, entry
20). The rules live here, the exe only records. (The whipped cross's gate D5: tools/tr_whip.py.)

  python3 tools/tr_gate.py headers RUNS/trhd_headers.jsonl
  python3 tools/tr_gate.py reach RUNS/trhd_reach.jsonl

Headers, case k: bit 0 the team, bit 1 the header (0 straight, 1 lob), bits 2-3 the forced file position (A D M RW),
k >> 4 = spot + 5 x HEADING index (spots: the attacking box, its corner edge, 1 px outside by depth, 1 px outside by
width, his own box; HEADING 0 / 3 / 7). The ball's deltaZ right after the game's PlayerHittingJumpHeader:
  lob: kLobHeaderBallDeltaZ 0x24000 always;
  straight, RUOLI SI: down (JZ - HEADING x JST, setpieces' own numbers) in the attacking box (spots 0, 1), the original
  0xA000 elsewhere, whatever CALCI PIAZZATI says; RUOLI NO: 0xA000 with CLASSICI, down everywhere with NUOVI.
Reach, case k: bit 0 the team, bits 1-2 the forced file position (D A RB M), bit 3 HEADING (0 / 7), k >> 4 = distance
index + 3 x spot (the ball 7 / 10 / 12 px away; the man inside / outside his own box). Result 1 = he headed it:
  7 px always, 12 px never; 10 px only with RUOLI SI for a file D with HEADING 7 inside his own box (limit 64 + 8 x 7
  = 120 >= 100; HEADING 0: 64). Result 2 (another player touched the pinned ball first) = a case not measured: FAIL.
"""
import json
import struct
import sys

H5P, H5V = (7, 3, 6, 4), (0, 3, 7)
H5X, H5A = (336, 193, 336, 192, 336), (40, 87, 88, 40, 600)
R6P, R6R, R6A = (3, 7, 1, 6), (7, 10, 12), (60, 100)
NH, NR = 240, 96
JUMP, LOB = 0xA000, 0x24000


def hcase(k):
    q = k >> 4
    return dict(k=k, team=k & 1, lob=bool(k & 2), pos=H5P[k >> 2 & 3], spot=q % 5, heading=H5V[q // 5])


def hexpect(k, ruoli, sp, jz=-0x800, jst=0x400):
    c = hcase(k)
    if c['lob']:
        return LOB
    down = c['spot'] in (0, 1) if ruoli else bool(sp)
    return (jz - c['heading'] * jst) & 0xFFFFFFFF if down else JUMP


def rcase(k):
    q = k >> 4
    return dict(k=k, team=k & 1, pos=R6P[k >> 1 & 3], heading=7 if k & 8 else 0, r=R6R[q % 3], inside=q // 3 == 0)


def rexpect(k, ruoli, rst=8):
    c = rcase(k)
    lim = 64 + rst * c['heading'] if ruoli and c['pos'] == 3 and c['inside'] else 64
    return int(c['r'] * c['r'] <= lim)


def entries(raw, typ):
    for i in range(0, len(raw) - 15, 16):
        f, t, k, a, b, c, d, v, w = struct.unpack_from('<HBBBBBBII', raw, i)
        if t == typ:
            yield dict(f=f, k=k, a=a, b=b, c=c, d=d, v=v, w=w)


def classify_headers(rows, jz=-0x800, jst=0x400):
    errs, summ = [], {}
    for arm in sorted({(r['ruoli'], r['sp']) for r in rows}):
        seen = {}
        for r in (x for x in rows if (x['ruoli'], x['sp']) == arm and 'log' in x):
            for e in entries(bytes.fromhex(r['log']), 19):
                c = hcase(e['k'])
                want = hexpect(e['k'], arm[0], arm[1], jz, jst)
                if e['k'] in seen:
                    errs.append(f'RUOLI {arm[0]} CP {arm[1]} case {e["k"]}: logged twice')
                seen[e['k']] = e['v']
                if (e['a'], e['b'], e['d']) != (c['pos'], c['heading'], c['team']):
                    errs.append(f'RUOLI {arm[0]} CP {arm[1]} case {e["k"]}: forced position / HEADING / team {e["a"], e["b"], e["d"]}')
                if e['v'] != want:
                    errs.append(f'RUOLI {arm[0]} CP {arm[1]} case {e["k"]} {c}: deltaZ {e["v"]:#x} (want {want:#x})')
        miss = [k for k in range(NH) if k not in seen]
        if miss:
            errs.append(f'RUOLI {arm[0]} CP {arm[1]}: {len(miss)} of {NH} cases not played (first {miss[:8]})')
        summ[f'ruoli{arm[0]}_cp{arm[1]}'] = dict(cases=len(seen), down=sum(1 for v in seen.values() if v >= 0x80000000),
                                                 up=sum(1 for v in seen.values() if v == JUMP),
                                                 lob=sum(1 for v in seen.values() if v == LOB))
    return errs, summ


def classify_reach(rows, rst=8):
    errs, summ = [], {}
    for ru in sorted({r['ruoli'] for r in rows}):
        seen = {}
        for r in (x for x in rows if x['ruoli'] == ru and 'log' in x):
            for e in entries(bytes.fromhex(r['log']), 20):
                c = rcase(e['k'])
                want = rexpect(e['k'], ru, rst)
                if e['k'] in seen:
                    errs.append(f'RUOLI {ru} case {e["k"]}: logged twice')
                seen[e['k']] = e['d']
                if (e['a'], e['b'], e['c']) != (c['pos'], c['heading'], c['r']):
                    errs.append(f'RUOLI {ru} case {e["k"]}: forced position / HEADING / distance {e["a"], e["b"], e["c"]}')
                if e['d'] == 2:
                    errs.append(f'RUOLI {ru} case {e["k"]} {c}: another player touched the pinned ball (not measured)')
                elif e['d'] != want:
                    errs.append(f'RUOLI {ru} case {e["k"]} {c}: {"headed" if e["d"] else "no contact"} after {e["w"]} frames '
                                f'(want {"a header" if want else "no contact"})')
        miss = [k for k in range(NR) if k not in seen]
        if miss:
            errs.append(f'RUOLI {ru}: {len(miss)} of {NR} cases not played (first {miss[:8]})')
        summ[ru] = dict(cases=len(seen), headed=sum(1 for v in seen.values() if v == 1),
                        expected=sum(rexpect(k, ru, rst) for k in range(NR)), disturbed=sum(1 for v in seen.values() if v == 2))
    return errs, summ


def main():
    kind, files = sys.argv[1], sys.argv[2:]
    rows = [json.loads(l) for p in files for l in open(p)]
    errs, summ = (classify_headers if kind == 'headers' else classify_reach)(rows)
    print(json.dumps(summ, indent=1))
    print(f'{len(errs)} errors')
    for e in errs[:40]:
        print('-', e)
    return not errs


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
