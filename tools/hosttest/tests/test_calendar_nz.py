"""Engine step C, part 1 - golden of 4.0.5's NZ Grand Final calendar bugs (093c89f, e3170dc, 74b589f): the career club
out of the Grand Final, decided at its rest day in the Championship's last group round. Fixture nz_stall (Panchina's
save, rc19 = c/HT19R, snapshot 2: week 140, the club resting); the glue = gplay.gp_gf, then the calendar contract
(test_calendar_lib C1..C4, glue=True: the menu flag as gp_gf leaves it) and no career day may follow (the club is out:
any day ahead is a phantom final).
  rc19 (the fixture's own code): the flag left 0 with nothing ahead - PARTITA on nothing, the stall          -> red
  HTPRE22 (the rejected 'hide only' candidate): a career day at week 141 - the phantom final               -> red
  HTMOT25 (the shipped 4.0.5 fix MOT25 + symbols)                                                         -> green
Today's exe: cal_nz (gf_step_c snapshots of an NZ career on c/HTCALnz = HTCAL + GPLAY_FORCE=1, HT_CAL_NZ) - the old snapshots cannot carry today's
code (LayoutChanged: obj3 and the state moved), so it has its own fixture."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402

CASES = (('rc19', None, False), ('HTPRE22', 'HTPRE22', False), ('HTMOT25', 'HTMOT25', True))


def nz_case(d, k, code, out=True):
    m = L.machine(d, k, code)
    _, idx, rows, _ = L.cal(m)
    glue = idx + 1 < len(rows)          # (gp_gf decides the final before its day: at the final's own day - the last
    m.call('gplay.gp_gf')               #  entry, the club's byte 6 already spent - the menu flag is the scan's, not its)
    cur, _, rows, _ = L.cal(m)
    ahead = [(r['i'], r['slot'], r['week']) for r in L.career_ahead(rows, cur)]
    bad, summ = L.check(m, glue=glue)
    if out and ahead:
        bad.append(f'phantom final: career days ahead with the club out {ahead}')
    return bad, summ


def test_calendar_nz_405():
    """the three builds on nz_stall: red where 4.0.5 was broken, green on the shipped fix"""
    out, ok = [], True
    for name, code, want in CASES:
        bad, summ = nz_case('nz_stall', 2, code)
        ok &= (not bad) == want
        out.append(f'{name} {"green" if not bad else "red"} ({"want green" if want else "want red"}): {summ}'
                   + (f' {bad}' if bad else ''))
    return ok, '; '.join(out)


def test_calendar_nz_now():
    """today's exe on its own gf_step_c snapshots (c/HTCALnz = c/HTCAL + GPLAY_FORCE=1: WESTERN SPRINGS 1st of the
    Northern League, in the Championship; weeks 125+): gp_gf then C1..C4, with the flag as gp_gf leaves it before the
    final's day (whether the club is in the final is the run's: no phantom check here)"""
    d = os.environ.get('HT_CAL_NZ', 'cal_nz')
    ks = [k for k, _ in L.snaps(d, 'gplay.csyms.gf_step_c')] if os.path.isdir(os.path.join(L.FIX, d)) else []
    if not ks:
        return True, f'SKIP: fixture {d} (gplay.csyms.gf_step_c) not taken yet (today\'s exe needs its own snapshot)'
    out, bad = [], []
    for k in ks:
        b, summ = nz_case(d, k, None, out=False)
        out.append(f'k{k}: {summ}')
        bad += [f'k{k}: {x}' for x in b]
    return not bad, '; '.join(out + bad)

