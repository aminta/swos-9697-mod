"""trhd_whip_host.py: spmeter MODE 4 (the forced wide kicks of scenario trhd_whip, gate D5) on the host, before any
DOSBox run: Unicorn runs the meter's frame routine on the relocated exe with the GAME'S OWN PlayerKickingBall and
ApplyBallAfterTouch (their callees outside the two functions are stood in for, diff_structural.run), for all 192
cases with RUOLI SI and NO, and tools/tr_whip.py's rule must hold on the logged entry 17 (ball deltaZ / speed).

  internal/hosttest/.venv/bin/python tools/hosttest/trhd_whip_host.py BUILD_DIR

BUILD_DIR: ITALIAN.EXE + ITALIAN.syms.json of a DIFF_TEST=3 DIFF_TRACE=1 SP_METER=1 SP_METER_MODE=4 TRHD_RUOLI=0 / 1
build (HOSTTEST_SYMS=1). What this proves: the meter's case decoding (team, side, direction, forced position, spot),
its call sequence (5 after-touch calls reach the game's high-kick branch at spinTimer 4), tr_kick / tr_hk in the real
call chain. What it does not: the flight after the kick and anything the live match does around it (DOSBox).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS

import diff_structural as ds
import setpieces as sp
import spmeter
import swreg
import tr_whip
import trhead as tr
from lepatch import LEPatch

B1, B2, B4 = ds.B1, ds.B2, ds.B4


def main(build):
    img = ds.images(os.path.join(build, 'ITALIAN.EXE'))
    sj = json.load(open(os.path.join(build, 'ITALIAN.syms.json')))
    L = {k: v[1] for k, v in sj['trhead'].items()}
    S = {k: v[1] for k, v in sj['setpieces'].items()}
    D = {k: v[1] for k, v in sj['difficulty'].items()}
    p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
    s, c = sp.find(p)
    _, c2 = tr.find(p)
    top = B2 + c2['TOP_O']
    bot = top + 0x91
    spr0 = B2 + c['BALL_O'] - 22 * 0x6E
    ball = B2 + c['BALL_O']
    blk = bytes(img[4]).find(spmeter.TAG, spmeter.SPM_AT, spmeter.SPM_AT + spmeter.LOG_AT)
    assert blk > 0 and img[4][blk + spmeter.OFF['MODE']] == 4, 'not an SP_METER_MODE=4 build'
    log = spmeter.SPM_AT + spmeter.LOG_AT
    pkb, at = s['KD'] - 0xE7, s['AT']
    R = B4 + swreg.TRHD_END - 16
    allowed = ((B1 + pkb, B1 + pkb + 0x2F0), (B1 + at, B1 + at + 0x700), (B4 + spmeter.SPM_AT, B4 + spmeter.SPM_AT + spmeter.LOG_AT),
               (B4 + swreg.TRHD_AT, B4 + swreg.TRHD_END), (B4 + swreg.SETPIECE_AT, B4 + swreg.SETPIECE_END),
               (B4 + swreg.SPX_AT, B4 + swreg.SPX_END), (B4 + swreg.TAKERS_AT, B4 + swreg.TAKERS_END))
    rec = ds.SCR + 0x30000
    n = bad = 0
    first = []
    for ru in (1, 0):
        for k in range(tr_whip.NCASE):
            m = ds.Mach(img, f'whip{ru}')
            m.w8(B4 + L.get('RU', L['TR_RU']), ru)
            m.w8(B4 + S['SP_OK'], 1)
            m.w16(B4 + S['SP_W'], 0)
            m.w32(B4 + S['PR_D'], 0)
            m.w16(B2 + sj['difficulty']['SYMS.TRG'][1], 0)
            m.w16(B2 + c['GSP_O'], 100)
            m.w16(B2 + c['GS_O'], 100)
            m.w32(B4 + D['DF_FRAMES'], 5000)
            for t, other, num, r_ in ((top, bot, 1, rec), (bot, top, 2, rec + 0x1000)):
                m.read(t, 0x91)
                m.uc.mem_write(t, bytes(0x91))
                m.w32(t, other)
                m.w16(t + 0x12, num)
                m.w32(t + 0x0A, r_)
                m.w16(t + 4, 0)
                m.w16(t + 0x76, 0xFFFF)                  # spinTimer -1: only PlayerKickingBall opens the after-touch
            m.read(spr0, 23 * 0x6E)
            m.uc.mem_write(spr0, bytes(23 * 0x6E))
            for i, num in ((9, 1), (20, 2)):            # each team's 10th man
                m.w16(spr0 + i * 0x6E, num)
                m.w16(spr0 + i * 0x6E + 2, 10)
            m.w16(B4 + blk + spmeter.OFF['NC'], k % 48)
            m.w8(B4 + blk + spmeter.OFF['K0B'], k // 48)
            m.w32(B4 + blk + spmeter.OFF['LN'], 0)
            m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
            m.uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
            m.w32(ds.STACK, R)
            lg, err = ds.run(m, B4 + spmeter.SPM_AT, R, allowed, max_steps=60000)
            raw = m.read(B4 + log, 64)
            es = [e for e in tr_whip.entries(raw) if e['t'] == 17]
            c_ = tr_whip.case(k)
            wdz, wsp, whip = tr_whip.expect(k, ru)
            team = bot if k & 1 else top
            sprite = spr0 + (20 if k & 1 else 9) * 0x6E
            x, y = (struct.unpack('<H', m.read(sprite + o, 2))[0] for o in (0x20, 0x24))
            wx = 671 - c_['x'] if c_['right'] else c_['x']
            wy = 129 + c_['a'] if k & 1 else 769 - c_['a']
            pos = m.read((rec + 0x1000 if k & 1 else rec) + 9 * 61 + tr.POS, 1)[0]
            ok = not err and len(es) == 1 and (es[0]['dz'], es[0]['sp'], es[0]['k']) == (wdz, wsp, k) and (x, y) == (wx, wy) \
                and pos == 4 + (k >> 3 & 3) and m.read(B4 + blk + spmeter.OFF['ST'], 1)[0] == 2
            n += 1
            if not ok:
                bad += 1
                if len(first) < 10:
                    first.append(f'RUOLI {ru} k {k} {c_}: {es and (hex(es[0]["dz"]), es[0]["sp"])} want {hex(wdz), wsp}; '
                                 f'spot {x, y} want {wx, wy}; pos {pos}; err {err}; calls out {[hex(a[0]) for a in lg][:6]}')
    for f in first:
        print('DIFF', f)
    print(f'spmeter MODE 4 on the host: {n} forced kicks (192 x RUOLI SI / NO), {bad} different: {"PASS" if not bad else "FAIL"}')
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)
