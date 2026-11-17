"""4.2.y T3 PRIMAVERA (t3.c): the preview draws nothing from the game, on the static image of HT_T3_BUILD (a
release-recipe exe with HOSTTEST_SYMS=1; default c/T3h/SWOS; none: SKIP as a PASS), obj1..obj4 relocated into Unicorn
(test_lrank's Exe), a career state written in: careerTeam (22 players, 3 G / 6 D / 9 M / 4 A), a pool of 24 teams of
the club's file (12 in its division) with two-word names, currentSeasonNumber 2, the calendar week 10.

- t3_list (the page's open) changes no byte of obj1, obj2 or obj3 - Rand's and Rand2's states (seed, randXorIndex,
  randXorKey), the game's D0..A6, cseg_52B6A's name buffer, careerTeam among them - and of obj4 only t3.c's .bss;
- it is pure: a second call gives the same six records and rows; the Rand2 state set to anything else before it,
  the same; the week + 4 (another period code): other boys; the week back: the first ones;
- the six: ages 17-19, positions by the squad's gaps (here the defence and the attack first: D 9 - 6, A 5 - 4),
  names from the pool (a first word and a last word of its players), prices = the game's templates' sums;
- T3_ITEM = the code: T3_STATE 1 (closed); careerNumPlayers 30: 2 (full)."""
import json
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_lrank as tl                                 # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import fixroot  # noqa: E402
BUILD = fixroot.build_dir('HT_T3_BUILD')           # (the current fixture, never a fixed c/<old> dir: MC 17/11)

FIRST = ['MARCO', 'LUCA', 'PAOLO', 'ANDREA', 'DAVIDE', 'SIMONE', 'MATTEO', 'NICOLA']
LAST = ['ROSSI', 'BIANCHI', 'VERDI', 'NERI', 'GALLI', 'CONTI', 'RICCI', 'MARINO']


def setup(x, e, rnd):
    w = lambda k, b: x.wr(x.base[e[k][0]] + e[k][1], b)
    own = 0x0105                                        # (file 5, team 1)
    ct = bytearray(76 + 38 * 32)
    ct[0:2] = struct.pack('<H', own)
    ct[25] = 1
    roles = [0] * 3 + [1, 2, 3, 3, 3, 3] + [4, 5, 6, 6, 6, 6, 6, 6, 6] + [7] * 4
    for i, ps in enumerate(roles):
        r = 76 + 38 * i
        ct[r + 3:r + 3 + 10] = f'{FIRST[i % 8]} {LAST[i % 8]}'[:10].encode()
        ct[r + 0x1A] = ps << 5
        ct[r + 0x20] = 10 + (i * 7) % 20
    w('CT', ct)
    w('CNP', struct.pack('<H', len(roles)))
    w('CMP', bytes(range(len(roles))) + bytes(8))
    w('SELT', struct.pack('<H', own))
    w('ISNAT', bytes(2))
    tmd = bytearray()
    for t in range(24):
        r = bytearray(684)
        r[0:2] = struct.pack('<H', 0x0205 + 0x100 * t)
        r[0] = 5
        r[25] = 1 if t < 12 else 2
        for i in range(16):
            p = 76 + 38 * i
            nm = f'{rnd.choice(FIRST)} {rnd.choice(LAST)}'.encode()
            r[p] = 3
            r[p + 3:p + 3 + len(nm)] = nm
            r[p + 0x1A] = (i % 8) << 5 | rnd.choice((0, 8, 16))
            r[p + 0x20] = rnd.randrange(5, 40)
        tmd += r
    w('TMD', tmd)
    w('CFB', struct.pack('<H', 24))
    w('CSN', struct.pack('<H', 2))
    w('CAL_CUR', struct.pack('<H', 0))
    w('CAL', bytes((0, 10, 0, 0)))
    w('DREG', bytes(rnd.randrange(256) for _ in range(60)))
    w('R2S', bytes((rnd.randrange(256),)))
    w('R2I', bytes((rnd.randrange(256),)))
    w('R2K', bytes((rnd.randrange(256),)))


def test_t3_preview():
    fixroot.need(BUILD, 'test_t3_preview', 'ITALIAN.syms.json')
    old, tl.BUILD = tl.BUILD, BUILD                     # (test_lrank's Exe loads tl.BUILD)
    try:
        x = tl.Exe()
    finally:
        tl.BUILD = old
    syms = json.load(open(os.path.join(BUILD, 'ITALIAN.syms.json')))['t3']
    x.syms = syms
    e = {k[4:]: tuple(v) for k, v in syms.items() if k.startswith('EXT.')}
    if 'T3_ITEM' not in syms or not e:
        return False, 'no t3 symbols in the build'
    sys.path.insert(0, tl.TOOLS)
    import swreg
    import t3
    lin = lambda k: x.base[e[k][0]] + e[k][1]
    bss0 = x.base[4] + swreg.T3_AT + t3.BSS_AT
    bss1 = x.base[4] + swreg.T3_END
    rnd = random.Random(1203)
    setup(x, e, rnd)
    bad, info = [], []
    snap = lambda: {k: x.rd(x.base[k], x.base[k + 1] - x.base[k] if k < 4 else x.top - x.base[4]) for k in (1, 2, 3, 4)}
    recs = lambda: x.rd(x.lin('T3_REC'), 6 * 38)
    lbls = lambda: [x.rd(x.lin('T3_LBL') + 40 * k, 40).split(b'\0')[0].decode('latin1') for k in range(6)]
    u32 = lambda n: struct.unpack('<I', x.rd(x.lin(n), 4))[0]
    before = snap()
    x.call(x.lin('t3_list'))
    after = snap()
    for k in (1, 2, 3):
        if before[k] != after[k]:
            d = [i for i in range(len(before[k])) if before[k][i] != after[k][i]]
            bad.append(f'obj{k}: {len(d)} bytes changed, first at +{d[0]:#x}')
    d4 = [i for i in range(len(before[4])) if before[4][i] != after[4][i]
          and not bss0 <= x.base[4] + i < bss1]
    if d4:
        bad.append(f'obj4 outside the .bss: {len(d4)} bytes, first +{d4[0]:#x}')
    r0, l0 = recs(), lbls()
    info.append(' | '.join(l0))
    if u32('T3_STATE') != 0:
        bad.append(f'state {u32("T3_STATE")}')
    code = u32('T3_CODE')
    if code != 1 + (2 * 64 + 10 // 4) % 255:
        bad.append(f'code {code}')
    for k in range(6):
        r = r0[38 * k:38 * k + 38]
        nm = r[3:25].split(b'\0')[0].decode('latin1').split(' ')
        age = x.rd(x.lin('T3_AGE') + k, 1)[0]
        if not (17 <= age <= 19) or len(nm) < 2 or nm[0] not in FIRST or nm[-1] not in LAST or r[0] != 3:
            bad.append(f'boy {k}: age {age}, name {nm}, nat {r[0]}')
    ps = [r0[38 * k + 0x1A] >> 5 for k in range(6)]
    grp = [(0, 1, 1, 1, 2, 2, 2, 3)[q] for q in ps]
    if grp.count(1) < 2 or grp.count(3) < 1 or ps != sorted(ps):
        bad.append(f'positions {ps}')
    x.call(x.lin('t3_list'))
    if recs() != r0 or lbls() != l0:
        bad.append('a second call: other boys')
    x.wr(lin('R2S'), b'\x11')
    x.wr(lin('R2I'), b'\x22')
    x.call(x.lin('t3_list'))
    if recs() != r0:
        bad.append('another Rand2 state: other boys')
    if x.rd(lin('R2S'), 1) != b'\x11' or x.rd(lin('R2I'), 1) != b'\x22':
        bad.append('Rand2 state not put back')
    x.wr(lin('CAL'), bytes((0, 14)))
    x.call(x.lin('t3_list'))
    if recs() == r0 or u32('T3_CODE') == code:
        bad.append(f'week + 4: the same boys (code {u32("T3_CODE")})')
    info.append('week+4: ' + ' | '.join(lbls()))
    x.wr(lin('CAL'), bytes((0, 10)))
    x.call(x.lin('t3_list'))
    if recs() != r0:
        bad.append('week back: other boys')
    x.wr(x.lin('T3_ITEM'), bytes((code,)))
    x.call(x.lin('t3_list'))
    if u32('T3_STATE') != 1:
        bad.append(f'item = code: state {u32("T3_STATE")}')
    x.wr(x.lin('T3_ITEM'), b'\0')
    x.wr(lin('CNP'), struct.pack('<H', 30))
    x.call(x.lin('t3_list'))
    if u32('T3_STATE') != 2:
        bad.append(f'30 players: state {u32("T3_STATE")}')
    return not bad, '; '.join(bad + info)
