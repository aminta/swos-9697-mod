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


def test_nz_stall():
    """the release stall (Panchina's save, rc19 = c/HT19R; fixtures nz_stall, snapshot 2 = gf_step at week 140 with the
    career club out of the final): with rc19's code the calendar ends on the career club's rest day (the stall, detected);
    with the fixed build's code (HT_NZFIX, default c/HTPRE22 = INT-PRE22-1409) an entry stays after it"""
    d = os.path.join(os.path.dirname(FIX), 'nz_stall')
    res = {}
    for name, code in (('rc19', None), ('fix', os.environ.get('HT_NZFIX', 'HTPRE22'))):
        m = Machine(d, 2, code_from=os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', code, 'SWOS') if code else None)
        m.call('gplay.gp_gf')
        cur, rows = _cal_tail(m)
        after = [r for r in rows if r[0] > cur]
        res[name] = (hex(m.u32('gplay.csyms.GP_GFT')), after[:2])
    ok = not res['rc19'][1] and bool(res['fix'][1])
    return ok, f'(GP_GFT, entries after the current one): rc19 {res["rc19"]}, fix {res["fix"]}'
