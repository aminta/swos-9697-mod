"""Engine step C, part 1 (PLAN §19.3, Regia 06/11): the calendar / menu contract as today's glue keeps it - the shared
reader + invariant checker of the test_calendar_* goldens (no test here).

The career calendar (uefaq.SYMS.CAL, count word at CAL - 4, the cursor CAL_CUR = byte offset, its index at CAL_CUR - 2):
entries of `len` bytes (word at +2), byte 0 = slot (0 league, 1 / 2 the national cups, 3 continental, 4 gplay's
play-offs / supercups), byte 1 = week (0..128), byte 4 = 0 for a day PARTITA plays, byte 6 = the career club's day
(> 0: the club plays; < 0: counted by the game's next-day scan cseg_8EC2B but only simulated by PARTITA - p6), byte 7 =
round (FFh: a played tie's old entry, uefaq). The invariants (step C's checker):
  C1 well formed: `count` entries, each len >= 8, weeks in calendar order (non-decreasing; past 128 in a career that
     spans more - NZ's Grand Final at 141, 3.2.7);
  C2 one match a club a week: at most one career day per (slot, week) - two contests in one week are the game's own
     (league weekend + continental midweek, h_uru week 72), two days of one contest are not; exceptions: a slot's
     final four (semi-finals + final in one week, FF_SLOTS) and the league (slot 0), at most LEAGUE_MAX = 2 a week: a
     real midweek round - MLS, Honduras, Peru, Colombia - lands in the weekend's career week at 8 weeks a month (MC
     13/11, 42-cal DOSBox gate); a third is a duplicated round (Panchina);
  C3 no career day ahead of the cursor in a week already reached (adce370's Libertadores q2: a first leg in a played
     week, only RITORNO left, ESCI crashed to DOS);
  C4 FINISH SEASON exactly when no career day is ahead: the game's next-day scan (NEXT_SCAN) sets SEASON_OVER 1 iff the
     calendar has no day with byte 4 = 0, byte 6 != 0 after the cursor (the phantom final / the stall of 4.0.5's NZ
     Grand Final; the Serie D play-off FINISH SEASON skipped, d2b2538); glue=True: also the flag as the glue routine
     just called left it (the menu reads it before any rescan - rc19's NZ stall: 0 with nothing ahead, PARTITA on
     nothing)."""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu import Machine  # noqa: E402

HOME = os.path.expanduser('~')
FIX = os.path.join(HOME, 'swos-mod', 'internal', 'hosttest', 'fixtures')
NEXT_SCAN = 0x7EA7F                     # (test_nzgf: the game's cseg_8EC2B, obj1, unpatched game code)
SEASON_OVER = 0x18DF2                   # (its result, obj2 word careerFinished: 1 = no career day ahead - FINISCI STAGIONE)
SEASON_FIN = 0x18DF0                    # (obj2 word seasonFinished: set, the scan answers 1 at once - between seasons)
FF_SLOTS = (1, 2, 3, 4)                 # slots whose contest may be played in a block in one week (a final four, the national
                                        # team's finals: world8485_nat's Euro 88 group, slot 1 week 152 x 3; MC 13/11) - swostest
                                        # logs them as info
LEAGUE_MAX = 2                          # the league's career days in one week (a real midweek round; a third = a duplicate)


def build_dir(code):
    """c/<code>/SWOS (a HOSTTEST_SYMS build) or None"""
    return os.path.join(HOME, 'swos-mod', 'c', code, 'SWOS') if code else None


def snaps(d, label=None):
    """[(k, meta)] of a fixture dir, in order; label: only snapshots taken at that label"""
    p = os.path.join(FIX, d)
    out = []
    for js in sorted(glob.glob(os.path.join(p, '[0-9]*.json')), key=lambda f: int(os.path.basename(f)[:-5])):
        meta = json.load(open(js))
        if label is None or meta.get('label') == label:
            out.append((int(os.path.basename(js)[:-5]), meta))
    return out


def machine(d, k, code=None, files=False):
    """Machine of fixture d snapshot k; code: another build's code over it (Machine.overlay, LayoutChanged if moved)"""
    m = Machine(os.path.join(FIX, d), k, code_from=build_dir(code))
    if files:
        b = m.meta['build']
        if not os.path.isdir(b):
            b = os.path.join(HOME, b[b.find('/swos-mod/') + 1:])
        m.dos_files(b, writes=True)
    return m


def cal(m):
    """(cursor offset, cursor index, [entry dicts]) of the career calendar in m's memory"""
    c = m.lin('uefaq.SYMS.CAL')
    cnt, cur = m.u16(c - 4), m.u16('uefaq.SYMS.CAL_CUR')
    rows, e = [], c
    for i in range(cnt):
        h = m.read(e, 8)
        ln = struct.unpack_from('<H', h, 2)[0]
        rows.append(dict(i=i, off=e - c, slot=h[0], week=h[1], ln=ln, b4=h[4], b5=h[5],
                         b6=struct.unpack('b', h[6:7])[0], rnd=h[7]))
        if ln < 8:
            break
        e += ln
    return cur, m.u16(m.lin('uefaq.SYMS.CAL_CUR') - 2), rows, cnt


def career_ahead(rows, cur):
    """the days the next-day scan cseg_8EC2B counts as the club's: the current entry with byte 6 != 0, then from it on
    those with byte 4 = 0 and byte 6 != 0 (PARTITA plays byte 6 > 0, simulates < 0)"""
    return [r for r in rows if (r['off'] == cur and r['b6'] != 0) or (r['off'] >= cur and r['b4'] == 0 and r['b6'] != 0)]


def check(m, scan=True, glue=False):
    """the invariants C1..C4 on m's calendar (C4 runs the game's next-day scan: scan=False skips it, it changes the
    menu flag only). -> (violations [str], summary str)"""
    cur, idx, rows, cnt = cal(m)
    bad = []
    if len(rows) != cnt or any(r['ln'] < 8 for r in rows):
        bad.append(f'C1 {len(rows)} entries parsed of {cnt}, lens {[r["ln"] for r in rows if r["ln"] < 8][:3]}')
    wk = [r['week'] for r in rows]
    if any(b < a for a, b in zip(wk, wk[1:])):
        bad.append(f'C1 weeks out of order {wk}')
    seen = {}
    for r in rows:
        if r['b6'] > 0 and r['b4'] == 0 and r['rnd'] != 0xFF:
            seen.setdefault((r['slot'], r['week']), []).append(r['i'])
    two = {k: v for k, v in seen.items() if len(v) > (LEAGUE_MAX if k[0] == 0 else 1) and k[0] not in FF_SLOTS}
    if two:
        bad.append(f'C2 two career days of one contest in one week (slot, week): {two}')
    now = next((r['week'] for r in rows if r['off'] == cur), None)
    ahead = career_ahead(rows, cur)
    past = [(r['i'], r['slot'], r['week']) for r in ahead if now is not None and r['week'] < now]
    if past:
        bad.append(f'C3 career days ahead of the cursor in a week already reached (week {now}): {past}')
    flag = left = None
    between = m.u16(m.base2 + SEASON_FIN) != 0          # (seasonFinished: C4 does not apply between two seasons)
    if glue and not between:
        left = m.u16(m.base2 + SEASON_OVER)
        if (left == 1) != (not ahead):
            bad.append(f'C4 the glue left the FINISH SEASON flag {left} with {len(ahead)} career days ahead '
                       f'{[(r["i"], r["slot"], r["week"], r["b6"]) for r in ahead][:4]}')
    if scan and not between:
        m.call(m.base1 + NEXT_SCAN)
        flag = m.u16(m.base2 + SEASON_OVER)
        if flag not in (0, 1) or (flag == 1) != (not ahead):
            bad.append(f'C4 FINISH SEASON flag {flag} with {len(ahead)} career days ahead '
                       f'{[(r["i"], r["slot"], r["week"], r["b6"]) for r in ahead][:4]}')
    summ = (f'{cnt} days, cursor {idx} (week {now}), {len(ahead)} career ahead'
            + ('' if left is None else f', flag left {left}') + ('' if flag is None else f', flag {flag}')
            + (', between seasons (seasonFinished)' if between else ''))
    return bad, summ
