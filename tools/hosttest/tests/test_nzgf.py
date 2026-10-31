"""NZ National League Championship -> Grand Final (gplay.c gf_*): fixtures = snapshots of gf_unhide_c / gf_anchor_c /
gf_step_c from week 125 of a world_gplay_nzchamp career (snapshot.py ... --scenario world_gplay_nzchamp --week-min
125), dir nz_gf. The first gf_step_c at or after the group's last day must build the final (2, GP_GFT 1) or decide it
(4); a 0 there names its reason in GP_GFT (0x81 a row not ours, 0x82 a club short of games, 0x83 < 2 qualifiers,
0x84 the buffer not the group)."""
import glob
import json
import os

from emu import Machine

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures', os.environ.get('HT_NZ', 'nz_gf'))


def test_gf_step_builds_final():
    steps = []
    for js in sorted(glob.glob(os.path.join(FIX, '*.json')), key=lambda p: int(os.path.basename(p)[:-5])):
        meta = json.load(open(js))
        if meta['label'].endswith('gf_step_c'):
            k = int(os.path.basename(js)[:-5])
            m = Machine(FIX, k)
            r = m.call('gplay.csyms.gf_step_c')
            steps.append((meta['week'], r, m.u32('gplay.csyms.GP_GFT')))
            if r in (2, 4):
                break
    if not steps:
        return False, f'no gf_step_c snapshot in {FIX}'
    w, r, gft = steps[-1]
    return r in (2, 4), f'gf_step_c calls {[(w_, r_, hex(g_)) for w_, r_, g_ in steps]}'


def _cal_tail(m):
    import struct
    c = m.lin('uefaq.SYMS.CAL')
    cnt, cur, e, rows = m.u16(c - 4), m.u16('uefaq.SYMS.CAL_CUR'), c, []
    for _ in range(cnt):
        h = m.read(e, 8)
        ln = struct.unpack_from('<H', h, 2)[0]
        if not ln:
            break
        rows.append((e - c, h[0], h[1], h[5]))
        e += ln
    return cur, rows


NEXT_SCAN = 0x7EA7F                     # the game's cseg_8EC2B (obj1, unpatched game code): the career club's next day
SEASON_OVER = 0x18DF2                   # its result (obj2 word): 1 = none ahead - the menu's FINISCI STAGIONE, 0 = PARTITA


def nz_stall_case(code):
    """(GP_GFT, the menu's flag as gp_gf leaves it, the flag re-scanned, the career days after the cursor) on
    nz_stall's snapshot 2 (week 140, the career club out of the Grand Final, resting that day) with that build's code"""
    d = os.path.join(os.path.dirname(FIX), 'nz_stall')
    m = Machine(d, 2, code_from=os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', code, 'SWOS') if code else None)
    m.call('gplay.gp_gf')
    left = m.u16(m.base2 + SEASON_OVER)
    cur, rows = _cal_tail(m)
    ahead = [r for r in rows if r[0] > cur and m.u8(m.lin('uefaq.SYMS.CAL') + r[0] + 6)]
    m.call(m.base1 + NEXT_SCAN)
    return hex(m.u32('gplay.csyms.GP_GFT')), left, m.u16(m.base2 + SEASON_OVER), ahead


def test_nz_stall():
    """the release NZ Grand Final stall (Panchina's save, rc19 = c/HT19R): after gp_gf drops the career club from the
    final at its rest day the menu must offer FINISCI STAGIONE (flag 1 as gp_gf leaves it) and no career-club day may
    follow (a phantom final). rc19: flag left 0 (PARTITA on nothing: the stall); HT_NZFIX's code must pass"""
    res = {name: nz_stall_case(code) for name, code in (('rc19', None), ('fix', os.environ.get('HT_NZFIX', 'HTPRE22')))}
    good = lambda r: r[1] == 1 and r[2] == 1 and not r[3]
    ok = not good(res['rc19']) and good(res['fix'])
    return ok, (f'(GP_GFT, flag left, flag re-scanned, career days ahead): rc19 {res["rc19"]}, '
                f'{os.environ.get("HT_NZFIX", "HTPRE22")} {res["fix"]}')
