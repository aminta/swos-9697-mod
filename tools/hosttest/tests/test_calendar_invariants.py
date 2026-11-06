"""Engine step C, part 1 - the calendar contract on every hook of a career, as today's glue keeps it: each snapshot's
routine called (season start ct_prep, the day before a match ct_daily, the group end ct_gend, table order lp_sort, cup
draw gp_draw, stage end gp_cap, season end gp_end / w_season_end, save / load), then test_calendar_lib's C1..C4: the
days in week order, one career day per contest and week, no career day ahead in a week already reached, FINISH SEASON
exactly when none is ahead. Fixtures (each on its own build, c/<build> HOSTTEST_SYMS): h_uru + h_uru_load (NACIONAL,
two seasons, 406-i4: league + Libertadores + Sudamericana), cs1_s1 / cs1_s1g / cs1_s1i (season 1 continental cups:
INTER's February, the group end), cw_uru6 (the conti view build). HT_CAL_DIRS adds dirs (today's exe: cal_uru,
cal_nz, cal_sd, cal_sc on c/HTCAL)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402

DIRS = ('h_uru', 'h_uru_load', 'cs1_s1', 'cs1_s1g', 'cs1_s1i', 'cw_uru6')
NOW = ('cal_uru', 'cal_nz', 'cal_sd', 'cal_sc')


def sweep(dirs):
    bad, out, n = [], [], 0
    for d in dirs:
        if not os.path.isdir(os.path.join(L.FIX, d)):
            continue
        for k, meta in L.snaps(d):
            m = L.machine(d, k, files=True)
            m.call(meta['label'], max_insn=300_000_000)
            v, summ = L.check(m)
            n += 1
            if v:
                bad.append(f'{d}:{k} {meta["label"]} w{meta.get("week")}: {v}')
            out.append(f'{d}:{k}')
    return bad, out, n


def test_calendar_invariants():
    """C1..C4 after every hook of the archived career fixtures (4.0.6 builds)"""
    bad, out, n = sweep(DIRS + tuple(x for x in os.environ.get('HT_CAL_DIRS', '').split(',') if x))
    return not bad and n > 0, f'{n} hook calls, {len(bad)} violations ' + ('; '.join(bad) if bad else '')


def test_calendar_invariants_now():
    """the same on today's exe's fixtures (c/HTCAL: cal_*)"""
    have = [d for d in NOW if os.path.isdir(os.path.join(L.FIX, d))]
    if not have:
        return True, 'SKIP: no cal_* fixture taken yet (today\'s exe needs its own snapshots)'
    bad, out, n = sweep(have)
    return not bad and n > 0, f'{have}: {n} hook calls, {len(bad)} violations ' + ('; '.join(bad) if bad else '')
