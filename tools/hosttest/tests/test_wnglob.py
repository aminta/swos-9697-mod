"""4.0.6 #26 (I10p world_winners_out_nz): the rc19 preview's early-simulated divisions carried the career league's global
numbers (gp_rows after RESTSEL: SELTEAMS the career club's list, each row's number its index there) - NZ's Southern
winner took AUCKLAND FC RES's, a B team to sec_find, dropped from the previewed Championship: the season-end page named
AUCKLAND CITY, CONTINUA TAURANGA CITY. Fixtures (ht_snapshot, world8485, the NZ career GPLAY_FORCE=12 on the 403c14
data, HOSTTEST_SYMS=1): wn_nzend (gplay.csyms.gp_season, CONTINUA's NZ call - the L3 run's own WOUT.CAR, I10p build)
and wn_nzpre (gplay.csyms.gp_pre_c on the fixed build, gp_sims' rows read before RESTSEL).

wn_nzend: the preview (GP_PRE=1, no club play-off) = CONTINUA (GP_PRE=0) on the same tables - the Championship's
champion; the old rows (the career division's numbers at each early row's index) decide otherwise (the bug, pinned).
wn_nzpre: every early division's row carries its own number - one base per team file (global = base + index), the
career division's for its file."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from emu import Machine  # noqa: E402

FIXD = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures')


def _lay(m):
    return (struct.unpack('<14I', m.read('gplay.csyms.GP_LAYOUT', 56)),
            struct.unpack('<5I', m.read('gplay.csyms.GP_LAYOUT2', 20)))


def _rows(m, d):
    L, _ = _lay(m)
    n = m.read('gplay.GP_IN', 16, L[2])[d]
    return [struct.unpack('<6H', m.read('gplay.GP_IN', 12, L[3] + (d * 32 + k) * 12)) for k in range(n)]


def _champ(fx, pre, old):
    m = Machine(os.path.join(FIXD, fx), 0)
    L, L2 = _lay(m)
    if old:                                     # (the old preview's rows: the career division's numbers by index)
        g0 = {r[0] >> 8: r[1] for r in _rows(m, 0)}
        for d in (1, 2):
            rows = _rows(m, d)
            first = min(r[0] >> 8 for r in rows)
            for k, r in enumerate(rows):
                m.write('gplay.GP_IN', struct.pack('<H', g0[(r[0] >> 8) - first]), L[3] + (d * 32 + k) * 12 + 2)
    m.write('gplay.csyms.GP_PRE', bytes([pre]))
    if pre:                                     # (gp_pre_c's: no club play-off, WN_ST = its marker only)
        m.write('gplay.GP_IN', b'\xff\xff', L2[4] - 2)
        m.write('gplay.WN_ST', bytes([1]), 3)
    m.call('gplay.csyms.gp_season', max_insn=200_000_000)
    raw = m.read('gplay.WN_ST', 164)
    return next((struct.unpack_from('<H', raw, 6 + 4 * i)[0] for i in range(raw[3]) if raw[4 + 4 * i] == ord('K')), None)


def test_wn_preview_globs():
    for fx in ('wn_nzend', 'wn_nzpre'):
        if not os.path.isdir(os.path.join(FIXD, fx)):
            return True, f'SKIP: fixture {fx} missing'
    bad, out = [], []
    pre, end, old = _champ('wn_nzend', 1, 0), _champ('wn_nzend', 0, 0), _champ('wn_nzend', 1, 1)
    if pre is None or pre != end:
        bad.append(f'wn_nzend: preview {pre} != CONTINUA {end}')
    if old == end:
        bad.append(f'wn_nzend: the old rows decide the same ({old:#x}) - the fixture no longer shows the bug')
    out.append(f'wn_nzend champion: preview {pre:#x} = CONTINUA {end:#x}; old rows {old:#x}')
    m = Machine(os.path.join(FIXD, 'wn_nzpre'), 0)
    L, L2 = _lay(m)
    sim = [d for d in m.read('gplay.GP_IN', 9, L2[4]) if d != 0xFF]
    base = {}
    for d in [m.read('gplay.GP_IN', 1, L2[2])[0]] + sim:
        for t, g, *_ in _rows(m, d):
            base.setdefault(t & 255, set()).add(g - (t >> 8))
    multi = {hex(f): sorted(map(hex, b)) for f, b in base.items() if len(b) > 1}
    if not sim or multi:
        bad.append(f'wn_nzpre: early divisions {sim}, files with more than one base {multi}')
    out.append(f'wn_nzpre: early divisions {sim}, one base per file {sorted((hex(f), hex(min(b))) for f, b in base.items())}')
    return not bad, ('; '.join(bad) + ' | ' if bad else '') + '; '.join(out)
