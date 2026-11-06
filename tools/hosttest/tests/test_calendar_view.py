"""Engine step C, part 1 - the continental view's days (4.0.6 COPPE CONTINENTALI, ctgame.c): the view replays the
season's ties from conti's state (ctgame.cg_replay) to show their days; the career calendar is the game's and must come
out byte for byte as it went in (CAL's count, entries and cursor), and the contract C1..C4 (test_calendar_lib) still
holds - a view that moved a day or the cursor would give the club a day twice or none (the view-days item of PLAN step
C). Fixtures: cw_uru6 (NACIONAL season 2, c/HTcw6), cs1_s1 / cs1_s1g / cs1_s1i (season 1: the week-10 start, the group
end at week 95, INTER's February), snapshots with conti's state (CT_ED = 'CE'). Today's exe: cal_uru (HT_CAL_VIEW)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402

DIRS = ('cw_uru6', 'cs1_s1', 'cs1_s1g', 'cs1_s1i')


def view_sweep(dirs):
    bad, out = [], []
    for d in dirs:
        if not os.path.isdir(os.path.join(L.FIX, d)):
            continue
        for k, meta in L.snaps(d):
            m = L.machine(d, k, files=True)
            if 'ctgame' not in m.syms or m.u16('conti.syms.CT_ED') != 0x4543:
                continue
            c = m.lin('uefaq.SYMS.CAL')
            cnt = m.u16(c - 4)
            before = (m.read(c - 4, 4), m.read(c, 0x1000), m.read(m.lin('uefaq.SYMS.CAL_CUR') - 2, 4))
            m.call('ctgame.cg_replay', max_insn=300_000_000)
            after = (m.read(c - 4, 4), m.read(c, 0x1000), m.read(m.lin('uefaq.SYMS.CAL_CUR') - 2, 4))
            v, summ = L.check(m)
            if before != after:
                v.append('the calendar changed: ' + ', '.join(n for n, a, b in zip(('count', 'entries', 'cursor'), before,
                                                                                    after) if a != b))
            if v:
                bad.append(f'{d}:{k} w{meta.get("week")}: {v}')
            out.append(f'{d}:{k} w{meta.get("week")} {cnt} days')
    return bad, out


def test_calendar_view():
    """cg_replay leaves the calendar as it was, C1..C4 hold (4.0.6 builds)"""
    bad, out = view_sweep(DIRS)
    return not bad and bool(out), f'{len(out)} replays: {"; ".join(bad) if bad else ", ".join(out)}'


def test_calendar_view_now():
    """the same on today's exe (c/HTCAL)"""
    d = os.environ.get('HT_CAL_VIEW', 'cal_uru')
    bad, out = view_sweep((d,)) if os.path.isdir(os.path.join(L.FIX, d)) else ([], [])
    if not out and not bad:
        return True, f'SKIP: no {d} snapshot with conti\'s state yet (today\'s exe needs its own snapshot)'
    return not bad, f'{len(out)} replays: {"; ".join(bad) if bad else ", ".join(out)}'
