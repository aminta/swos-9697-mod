"""Engine step C, part 1 - golden of 4.0.5's early supercup tie (403faf2 + c1cdd1a): in an 'early' country (ITA ESP TUR
KSA ENG GER FRA) the career club's supercup tie is built at the season start, so the first screen's fixture list
already has it and it is played at its real week. rc6 (Davide, MiSTer): a new INTER career showed no SUPERCOPPA row -
the build waited for the first calendar advance, after the first screen. The fix: gp_scgl (CareerGameListCommon's
menu pointer) runs gp_sc (the supercup block of gp_adv) before the list.
Fixture cal_sc: a new INTER career on today's exe (c/HTCAL, world_uru_nacional with URU_TEAM = INTER), snapshots at
gplay.gp_scgl (the first screen; the first hit, before the tie exists). The contract: before gp_scgl (= the reverted
glue's first screen) no supercup day; after it a career day of slot 4 in a real week of this season, after the reached
one, and C1..C4 (test_calendar_lib); gp_scgl a second time changes nothing (sc_step_c handles a season once)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402


def sc_days(m):
    cur, idx, rows, _ = L.cal(m)
    now = rows[idx]['week'] if idx < len(rows) else None
    return now, [(r['i'], r['week'], r['b6']) for r in rows if r['slot'] == 4 and r['b6'] > 0]


def test_calendar_sc():
    d = os.environ.get('HT_CAL_SC', 'cal_sc')
    ks = [k for k, meta in L.snaps(d, 'gplay.gp_scgl')] if os.path.isdir(os.path.join(L.FIX, d)) else []
    if not ks:
        return True, f'SKIP: fixture {d} (gplay.gp_scgl) not taken yet'
    k = ks[0]
    m = L.machine(d, k, files=True)
    now, before = sc_days(m)
    m.call('gplay.gp_scgl', max_insn=300_000_000)
    _, after = sc_days(m)
    c = m.lin('uefaq.SYMS.CAL')
    snap = m.read(c - 4, 0x1000)
    m.call('gplay.gp_scgl', max_insn=300_000_000)
    again = m.read(c - 4, 0x1000) == snap
    bad, summ = L.check(m)
    red = not before                                    # (the reverted glue's first screen: no supercup day yet)
    if not after:
        bad.append('no supercup career day after gp_sc')
    elif any(w is None or now is None or w < now for _, w, _ in after):
        bad.append(f'a supercup day before the reached week {now}: {after}')
    if not again:
        bad.append('gp_scgl a second time changed the calendar')
    return red and not bad, (f'{d}:{k} week {now}: supercup days before gp_scgl {before} (reverted glue: '
                             f'{"red" if red else "NOT red"}), after {after}, again unchanged {again}; {summ} {bad or ""}')
