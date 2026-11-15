"""practice_car's .CAR gate (tools/carfields.py, MC 15/11): a practice-only byte passes only inside a named field the
control changed too. Synthetic saves shaped as the 15/11 RELpr7 run's (q8):
- a player record in a cache slot: control 'ROBERT DRAMEH', practice 'SIMONE PULISIC' (one byte longer) -> info;
- a line-up order array, the practice's in another order with one entry where the control kept 0 -> info;
- CONTROL (must FAIL): a stat byte the control changed (record + 30) and the practice changing the byte after it
  (+ 31) too - contiguous changed bytes, but not one named field;
- a byte in no field at all -> FAIL.
HT_CAR_RUNS=<runs dir with practice_car_ctrl / _fk>: the real saves too (all practice-only bytes named)."""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import carfields  # noqa: E402

N = 0x400
REC = 0x100                                  # a 38-byte player record
ORD = 0x200                                  # a line-up order array


def rec(name, num, stat):
    r = bytearray(38)
    r[0], r[2] = 0x08, num
    r[3:3 + len(name)] = name
    r[30] = stat
    return r


def saves(pr_name, pr_order, pr_stat, extra=None):
    blank = bytearray(N)
    c1, p1 = bytearray(N), bytearray(N)
    c1[REC:REC + 38] = rec(b'ROBERT DRAMEH', 1, 0x52)
    p1[REC:REC + 38] = rec(pr_name, 1, 0x42)
    c1[ORD:ORD + 15] = bytes([4, 10, 8, 11, 1, 7, 14, 5, 2, 6, 12, 3, 0, 13, 9])
    p1[ORD:ORD + 15] = bytes(pr_order)
    if pr_stat is not None:
        p1[REC + 31] = pr_stat
    if extra is not None:
        p1[extra] = 0x77
    return carfields.diff(blank, c1), carfields.diff(blank, p1), bytes(c1), bytes(p1)


ORDER2 = [4, 10, 8, 11, 1, 7, 14, 5, 12, 6, 0, 3, 2, 13, 9]


def test_carfields_named():
    fail, info = carfields.classify(*saves(b'SIMONE PULISIC', ORDER2, None))
    assert not fail, [hex(i) for i in fail]
    got = {i: f for i, f in info}
    assert got.get(REC + 16, '').startswith('player name'), info          # the 'C' of PULISIC
    assert got.get(ORD + 12, '').startswith('line-up order'), info        # 02 where the control has 00
    return True, '; '.join(f'{i:#x} {f}' for i, f in info)


def test_carfields_control_stat_neighbour():
    """CONTROL: a practice-only byte right after a stat the control changed is not a named field: FAIL."""
    fail, info = carfields.classify(*saves(b'SIMONE PULISIC', ORDER2, 0x05))
    assert fail == [REC + 31], ([hex(i) for i in fail], info)
    return True, f'caught {fail[0]:#x} (record + 31, after the stat at + 30)'


def test_carfields_control_loose_byte():
    fail, info = carfields.classify(*saves(b'ROBERT DRAMEH', ORDER2, None, extra=0x300))
    assert fail == [0x300], ([hex(i) for i in fail], info)
    return True, 'caught 0x300'


def test_carfields_real_runs():
    d = os.environ.get('HT_CAR_RUNS')
    if not d:
        return True, 'SKIP: HT_CAR_RUNS not set'
    r = {}
    for m in ('ctrl', 'fk'):
        a, b = (open(os.path.join(d, f'practice_car_{m}', 'SWOS', n + '.CAR'), 'rb').read() for n in ('PRA0', 'PRA1'))
        r[m] = carfields.diff(a, b), b
    fail, info = carfields.classify(r['ctrl'][0], r['fk'][0], r['ctrl'][1], r['fk'][1])
    assert not fail, [hex(i) for i in fail]
    return True, '; '.join(f'{i:#x} {f}' for i, f in info)
