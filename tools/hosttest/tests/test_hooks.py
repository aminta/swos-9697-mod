"""Engine step H (PLAN §19.3): one Tier B test per bridge hook of PLAN §3.6, on today's code - the contract the engine
must keep when it takes a hook over. Fixtures (release recipe + HOSTTEST_SYMS=1, c/HTI4 = 406-i4 b0c5e07):
h_uru = a NACIONAL career's two seasons (snapshot.py BUILD gplay.gp_draw,gplay.gp_cap,gplay.gp_end,
careerworld.w_season_end,conti.ct_daily,lp36.lp_sort,trailer.save_trailer --max 3), save_s1.CAR = the .CAR the game
wrote at that save_trailer; h_uru_load = its season-2 load (trailer.load_trailer,conti.ct_prep --car save_s1.CAR).

Save: save_trailer's .CAR = the game's, byte for byte. Load: load_trailer by the contract only - save(load(x)) is
not x on the trailer (5083 of 16192 B differ after the after-load callbacks): step P's first item, not H's.

Hooks: cup draw (gp_draw), stage end (gp_cap), season end (w_season_end, gp_end), table order (lp_sort), the day
before a match (ct_daily), new season (ct_prep), save / load (save_trailer / load_trailer), FINISH SEASON (the game's
next-day scan). Each: returns within its budget, < 1 s, the same bytes on a second run, and writes only the pages it
wrote when the golden was taken (footprint.json next to the fixture; HT_REGOLD=1 rewrites it)."""
import glob
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # (test_nzgf's calendar helpers)
from emu import Machine  # noqa: E402
from test_nzgf import NEXT_SCAN, SEASON_OVER, _cal_tail  # noqa: E402

ROOT = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures')
DIRS = ('h_uru', 'h_uru_load')
MEM = 0x2000000
PAGE = 0x1000


def _snaps():
    for d in DIRS:
        p = os.path.join(ROOT, d)
        for js in sorted(glob.glob(os.path.join(p, '[0-9]*.json')), key=lambda f: int(os.path.basename(f)[:-5])):
            if os.path.basename(js) != 'footprint.json':
                yield p, int(os.path.basename(js)[:-5]), json.load(open(js))


def _machine(d, k, meta):
    m = Machine(d, k)
    b = meta['build']
    if not os.path.isdir(b):                    # (taken on the other Mac: the same tree under this home, as Machine)
        b = os.path.join(os.path.expanduser('~'), b[b.find('/swos-mod/') + 1:])
    m.dos_files(b, writes=True)
    return m


def _run(d, k, meta):
    """(changed pages {page: md5}, files written, seconds) of one call of the snapshot's label"""
    m = _machine(d, k, meta)
    before = bytes(m.uc.mem_read(0, MEM))
    t = time.time()
    m.call(meta['label'], max_insn=300_000_000)
    dt = time.time() - t
    after = bytes(m.uc.mem_read(0, MEM))
    pages = {i // PAGE: hashlib.md5(after[i:i + PAGE]).hexdigest() for i in range(0, MEM, PAGE)
             if before[i:i + PAGE] != after[i:i + PAGE]}
    return pages, m.files_written, dt


def test_hooks_contract():
    out, bad, gold = [], [], {}
    regold = os.environ.get('HT_REGOLD') == '1'
    for d in DIRS:
        f = os.path.join(ROOT, d, 'footprint.json')
        gold[d] = {} if regold or not os.path.exists(f) else json.load(open(f))
    seen = set()
    for d, k, meta in _snaps():
        lab, key = meta['label'], str(k)
        try:
            p1, w1, dt = _run(d, k, meta)
            p2, w2, _ = _run(d, k, meta)
        except Exception as e:
            bad.append(f'{os.path.basename(d)}/{k} {lab}: {e}')
            continue
        seen.add(lab)
        if p1 != p2 or w1 != w2:
            bad.append(f'{os.path.basename(d)}/{k} {lab}: not deterministic')
        if dt >= 1.0:
            bad.append(f'{os.path.basename(d)}/{k} {lab}: {dt:.2f} s')
        g = gold[os.path.basename(d)]
        if regold or key not in g:
            g[key] = sorted(p1)
        elif not set(p1) <= set(g[key]):
            bad.append(f'{os.path.basename(d)}/{k} {lab}: pages outside its footprint '
                       f'{[hex(x * PAGE) for x in sorted(set(p1) - set(g[key]))][:6]}')
        out.append(f'{k}:{lab.split(".")[-1]} {len(p1)}p {dt:.2f}s')
    for d in DIRS:
        f = os.path.join(ROOT, d, 'footprint.json')
        if regold or not os.path.exists(f):
            json.dump(gold[d], open(f, 'w'))
    want = {'gplay.gp_draw', 'gplay.gp_cap', 'gplay.gp_end', 'careerworld.w_season_end', 'conti.ct_daily',
            'lp36.lp_sort', 'trailer.save_trailer', 'trailer.load_trailer', 'conti.ct_prep'}
    if want - seen:
        bad.append(f'hooks without a fixture: {sorted(want - seen)}')
    return not bad, ('; '.join(bad) + ' | ' if bad else '') + ', '.join(out)


def test_save_bytes():
    """save_trailer in the emulator writes exactly the .CAR the game wrote (save_s1.CAR)"""
    for d, k, meta in _snaps():
        if meta['label'] == 'trailer.save_trailer':
            _, w, _ = _run(d, k, meta)
            car = open(os.path.join(d, 'save_s1.CAR'), 'rb').read()
            got = next(iter(w.values()), b'')
            diff = [i for i in range(min(len(car), len(got))) if car[i] != got[i]]
            return got == car, f'{len(got)} B written vs {len(car)} B, {len(diff)} bytes differ {diff[:6]}'
    return False, 'no save_trailer fixture'


def test_finish_season_flag():
    """the game's next-day scan (cseg_8EC2B) on every snapshot: FINISH SEASON (flag 1) exactly when the calendar has
    no career-club day after its cursor (PLAN step C's invariant: no phantom day, no stall)"""
    bad, out = [], []
    for d, k, meta in _snaps():
        m = _machine(d, k, meta)
        cur, rows = _cal_tail(m)
        ahead = [r for r in rows if r[0] > cur and m.u8(m.lin('uefaq.SYMS.CAL') + r[0] + 6)]
        m.call(m.base1 + NEXT_SCAN)
        flag = m.u16(m.base2 + SEASON_OVER)
        if flag not in (0, 1) or (flag == 1) != (not ahead):
            bad.append((os.path.basename(d), k, meta['week'], flag, len(ahead)))
        out.append(f'{k}:w{meta["week"]}={flag}/{len(ahead)}')
    return not bad and bool(out), (f'{bad} ' if bad else '') + ' '.join(out)
