"""conti.py ct_prep (phase B: the career club's next continental tie into the ties' contest): its first week must lie
after the calendar's current week - rc20's Libertadores bug (q1 and q2 both month 8: the q2 built after a won q1 got
weeks already played, only RITORNO left, ESCI on it -> DOS). Fixtures: snapshots at ct_prep's entry in a NACIONAL
career's season 2 (snapshot.py ... conti.ct_prep), one dir per build: ct_prep_<build>."""
import glob
import os

from emu import Machine

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures')


def ct_prep_cases(build):
    """[(k, seg, current week, first week built)] of every snapshot of the build"""
    out = []
    d = os.path.join(FIX, f'ct_prep_{build}')
    for js in sorted(glob.glob(os.path.join(d, '*.json')), key=lambda p: int(os.path.basename(p)[:-5])):
        k = int(os.path.basename(js)[:-5])
        m = Machine(d, k)
        seg = m.read('conti.syms.CT_SEG', 12)
        cal, cur = m.lin('uefaq.SYMS.CAL'), m.u16('uefaq.SYMS.CAL_CUR')
        week = m.u8(cal + cur + 1)
        m.call('conti.ct_prep')
        first = m.u8('conti.@TIE', 3) if seg[2] == 0 else None
        out.append((k, seg.hex(), week, first))
    return out


def check(build, expect_ok):
    cases = ct_prep_cases(build)
    bad = [c for c in cases if c[3] is not None and c[3] <= c[2]]
    ok = (not bad) == expect_ok
    return ok, f'{build}: {len(cases)} snapshots, ties built into played weeks: {bad or "none"}'


def test_ct_prep_fixed():
    """the fixed build (adce370): no tie of the career club starts in a week already reached"""
    return check(os.environ.get('HT_FIX', 'HT20'), True)


def test_ct_prep_control():
    """control (rc19, before adce370): the q2 tie after the won q1 is built into played weeks"""
    return check(os.environ.get('HT_CONTROL', 'HT19'), False)
