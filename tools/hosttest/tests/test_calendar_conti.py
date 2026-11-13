"""Engine step C, part 1 - golden of 4.0.5 rc20's Libertadores bug (adce370): the career club's next continental tie
(conti.ct_prep, phase B) must start after the week the calendar has reached. NACIONAL's season 2: q1 and q2 both in
month 8, the q2 built after a won q1 had its first leg in a played week - only RITORNO left, ESCI on it crashed to DOS.
Fixtures ct_prep_HT19 (rc19, before the fix) and ct_prep_HT20 (rc20, fixed) = snapshots at ct_prep's entry (as
test_conti). After the call: the tie's first week (conti.@TIE + 3, when CT_SEG's kind byte is 0: a tie) > the current
week, and the calendar contract C1..C4 (test_calendar_lib) holds.
  HT19's snapshot, its own code                         -> red (the q2 into a played week)
  HT19's snapshot, HT20's code (the fix over the state)  -> green
  HT20's snapshots, own code                            -> green
Today's exe: cal_uru (c/HTCAL, a NACIONAL season 2 from h_uru's save_s1.CAR, ct_prep snapshots; HT_CAL_URU)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402


def prep_case(d, k, code):
    m = L.machine(d, k, code)
    seg = m.read('conti.syms.CT_SEG', 12)
    _, _, rows, _ = L.cal(m)
    cur = m.u16('uefaq.SYMS.CAL_CUR')
    now = next((r['week'] for r in rows if r['off'] == cur), None)
    m.call('conti.ct_prep')
    bad, summ = L.check(m)
    first = m.u8('conti.@TIE', 3) if seg[2] == 0 else None
    if first is not None and now is not None and first <= now:
        bad.append(f'the tie\'s first week {first} <= the reached week {now}')
    return bad, f'k{k} tie first week {first} at week {now}; {summ}'


def run(cases):
    out, ok = [], True
    for d, ks, code, want in cases:
        for k in ks:
            bad, summ = prep_case(d, k, code)
            ok &= (not bad) == want
            out.append(f'{d}/{code or "own"} {"green" if not bad else "red"} (want {"green" if want else "red"}): '
                       f'{summ}' + (f' {bad}' if bad else ''))
    return ok, '; '.join(out)


def test_calendar_conti_405():
    """rc19 red, the rc20 fix green (on rc19's state and on its own snapshots)"""
    hi = [k for k, _ in L.snaps('ct_prep_HT20')]
    return run((('ct_prep_HT19', [0], None, False), ('ct_prep_HT19', [0], 'HT20', True), ('ct_prep_HT20', hi, None, True)))


def test_calendar_conti_now():
    """today's exe (c/HTCAL) on its own ct_prep snapshots: green"""
    d = os.environ.get('HT_CAL_URU', 'cal_uru')
    ks = [k for k, meta in L.snaps(d, 'conti.ct_prep')] if os.path.isdir(os.path.join(L.FIX, d)) else []
    if not ks:
        return True, f'SKIP: fixture {d} (conti.ct_prep) not taken yet (today\'s exe needs its own snapshot)'
    return run(((d, ks, None, True),))
