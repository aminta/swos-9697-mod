"""Engine step C, part 1 - golden of 4.0.5's Serie D FINISH SEASON bug (d2b2538, Panchina's find): a club resting on
its group's last matchday (17 clubs: two byes) with another contest's day in between had no career day left after its
last match; the menu offered FINISH SEASON (CareerPlayMatch: every day simulated to the season's end) and gp_lend built
its play-off inside that loop - simulated, never played (~1 career in 8). The fix: gplay.gp_fin replaces PlayMatchMenu's
`call CareerPlayMatch`: the same loop, but after each day's advance a scan of the days left (byte 4 = 0, byte 6 > 0);
one of the club's -> careerFinished 0, the career menu refreshed, PlayMatchMenu returns to it (`add esp, 4`).

The contract, on a mid-season snapshot (h_uru 4: NACIONAL, week 100, days of three contests ahead): FINISH SEASON
pressed with no career day ahead (careerFinished 1, every byte 6 ahead 0), then one later day becomes the club's (byte
6 = 1: the play-off built inside the loop). The day's simulation cseg_8E841 is stubbed (it waits on the machine in the
emulator; each call logs the day it would simulate): FINISH SEASON may simulate the days before the club's, never the
club's own - it gives the menu back (careerFinished 0) with the club's day still ahead.
  the reverted glue (the game's CareerPlayMatch, still in the exe: the fix only redirected its one call) -> red
  gp_fin (4.0.5's fix, h_uru's build 406-i4)                                                         -> green
Today's exe: the same on cal_uru's gplay.gp_fin snapshot (c/HTCAL: the real FINISH SEASON entry of NACIONAL's season
2, week 112; HT_CAL_SD=dir:k)."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_calendar_lib as L  # noqa: E402
from emu import EXTRA, SENTINEL  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP  # noqa: E402

STUB = EXTRA + 0xFE000                  # call <routine>; ret - PlayMatchMenu's frame: gp_fin's `add esp, 4` drops it
CPM = (rb'\x66\xa1.{4}\x66\x0b\xc0\x74.\x66\xa1.{4}\x66\x0b\xc0\x75\x05\xe8.{4}\xe8.{4}'
       rb'\x66\xa1.{4}\x66\x0b\xc0\x74.\xc3')   # (gplay._fin_site: CareerPlayMatch)


def cpm_sites(m):
    """(CareerPlayMatch, cseg_8E841 = the day's simulation) linear addresses, from the code in memory"""
    o1 = m.read(m.base1, m.base2 - m.base1 if m.base2 > m.base1 else 0xB0000)
    hit = [x.start() for x in re.finditer(CPM, o1, re.S)]
    assert len(hit) == 1, hit
    o = hit[0]
    sim = o + 22 + 5 + struct.unpack_from('<i', o1, o + 23)[0]
    return m.base1 + o, m.base1 + sim


def fin_case(d, k, routine, mark_ahead=6):
    """-> (violations, summary) of FINISH SEASON by `routine` ('gp_fin' or 'cpm') on snapshot d:k"""
    m = L.machine(d, k, files=True)
    cpm, sim = cpm_sites(m)
    c = m.lin('uefaq.SYMS.CAL')
    cur, idx, rows, cnt = L.cal(m)
    ahead = [r for r in rows if r['i'] > idx]
    if len(ahead) < 2:
        return [f'only {len(ahead)} days ahead'], ''
    mark = ahead[min(mark_ahead, len(ahead) - 1)]
    for r in rows[idx:]:
        m.write(c + r['off'] + 6, bytes([1 if r is mark else 0]))
    m.write(m.base2 + L.SEASON_OVER, b'\1\0')
    days = []

    def stub(uc, addr, size, data):     # the day's simulation: log the day, return at once
        _, i, rs, _ = L.cal(m)
        days.append((i, rs[i]['week'], rs[i]['b6']) if i < len(rs) else (i, None, 0))
        esp = uc.reg_read(UC_X86_REG_ESP)
        uc.reg_write(UC_X86_REG_EIP, struct.unpack('<I', bytes(uc.mem_read(esp, 4)))[0])
        uc.reg_write(UC_X86_REG_ESP, esp + 4)
    m.uc.hook_add(UC_HOOK_CODE, stub, begin=sim, end=sim)
    target = m.lin('gplay.gp_fin') if routine == 'gp_fin' else cpm
    m.uc.mem_write(STUB, b'\xE8' + struct.pack('<i', target - (STUB + 5)) + b'\xC3')
    err = ''
    try:
        m.call(STUB, max_insn=400_000_000)
    except Exception as e:              # (the reverted loop runs on to the season's end: its advance is the game's)
        err = f'{type(e).__name__}: {str(e)[:80]}'
    _, i2, rows2, _ = L.cal(m)
    cf = m.u16(m.base2 + L.SEASON_OVER)
    bad = []
    own = [x for x in days if x[0] == mark['i']]
    if own:
        bad.append(f'FINISH SEASON simulated the club\'s day {mark["i"]} (week {mark["week"]}, slot {mark["slot"]})')
    if not own and (cf != 0 or i2 > mark['i']):
        bad.append(f'no menu back before the club\'s day: careerFinished {cf}, cursor {i2} vs the day {mark["i"]}')
    return bad, (f'the club\'s day {mark["i"]} (week {mark["week"]}); days simulated {[x[0] for x in days]}, cursor '
                 f'{idx} -> {i2}, careerFinished {cf}' + (f', {err}' if err else ''))


def test_calendar_seried_405():
    """h_uru 4 (406-i4): the game's CareerPlayMatch red, gp_fin green"""
    out, ok = [], True
    for name, want in (('cpm', False), ('gp_fin', True)):
        bad, summ = fin_case('h_uru', 4, name)
        ok &= (not bad) == want
        out.append(f'{name} {"green" if not bad else "red"} (want {"green" if want else "red"}): {summ}'
                   + (f' {bad}' if bad else ''))
    return ok, '; '.join(out)


def test_calendar_seried_now():
    """today's exe (c/HTCAL): gp_fin green, the game's CareerPlayMatch red, on its own FINISH SEASON snapshot"""
    d, _, k = os.environ.get('HT_CAL_SD', 'cal_uru:').partition(':')
    if not os.path.isdir(os.path.join(L.FIX, d)):
        return True, f'SKIP: fixture {d} not taken yet (today\'s exe needs its own snapshot)'
    if not k:                           # (the real FINISH SEASON entry)
        k = next((str(kk) for kk, meta in L.snaps(d, 'gplay.gp_fin')), None)
        if k is None:
            return True, f'SKIP: no gplay.gp_fin snapshot in {d} yet'
    bad, summ = fin_case(d, int(k), 'gp_fin')
    rbad, rsumm = fin_case(d, int(k), 'cpm')          # (the reverted glue on today's code: red)
    return not bad and bool(rbad), (f'{d}:{k} gp_fin {"green" if not bad else "red"}: {summ} {bad or ""}; the game\'s '
                                    f'CareerPlayMatch {"red" if rbad else "NOT red"}: {rsumm}')
