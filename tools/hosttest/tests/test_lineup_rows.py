"""Line-up rows (MC 19/11, Shaved's row-154 gate): a squad screen with a bench of 3 (the INTERCONTINENTALE) has 17
row entries, two of them hidden. row_entries / sq_ok take the drawn rows only: 15 rows, the last one = the reserve row
(the one with a face entry); a full screen stays 17 rows."""
import os
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)


class _Scr:
    def __init__(self, hidden):
        self.geom, self.entries = [], []
        for k in range(17):                       # rows at y 20 + 9k; the hidden ones keep their place
            self.geom.append((26, 20 + 9 * k, 81, 8))
            self.entries.append((k, '', k in hidden, 0))
        self.geom.append((26, 20, 81, 8))         # a text copy of row 1: not a row
        self.entries.append((17, 'SEAMAN', 0, 0))


def test_lineup_rows_short_bench():
    import swostest as T
    full, short = T.row_entries(_Scr(set())), T.row_entries(_Scr({14, 15}))
    errs = []
    if len(full) != 17 or not T.sq_ok(full):
        errs.append(f'full screen: {len(full)} rows')
    if len(short) != 15 or not T.sq_ok(short) or short[-1] != 16 or 14 in short or 15 in short:
        errs.append(f'bench of 3: {short}')
    if T.sq_ok(list(range(12))) or T.sq_ok(list(range(18))):
        errs.append('sq_ok bounds')
    return not errs, '; '.join(errs) or 'full 17, bench-of-3 15 (reserve = the last drawn row), bounds 13..17'
