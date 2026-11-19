"""trhd_gates_host.py: spmeter MODES 5 / 6 (the forced cases of scenarios trhd_headers / trhd_reach, gates D4 / D6) on
the host, before any DOSBox run (as trhd_whip_host.py for MODE 4): Unicorn runs the meter's frame routine on the
relocated exe with the GAME'S OWN routines, and tools/tr_gate.py's rule must hold on the logged entries.

  internal/hosttest/.venv/bin/python tools/hosttest/trhd_gates_host.py BUILD_DIR

BUILD_DIR: ITALIAN.EXE + ITALIAN.syms.json of a DIFF_TEST=3 DIFF_TRACE=1 SP_METER=1 SP_METER_MODE=5 (or 6) build with
the TRHD band (TRHD_RUOLI=0 / 1; the switch and CALCI PIAZZATI are poked), HOSTTEST_SYMS=1.
MODE 5: all 240 cases x RUOLI SI / NO x CALCI PIAZZATI 0 / 1 through the game's PlayerHittingJumpHeader (+
DoFlyingHeader / DoLobHeader, GetPlayerPointerFromShirtNumber): entry 19's deltaZ = the rule.
MODE 6: all 96 cases x RUOLI SI / NO: the meter's forcing frame (the game's PlayerAttemptingJumpHeader), then the
game's own contact test of UpdatePlayers (@@check_if_header_winded_up .. the call of PlayerHittingJumpHeader, with the
man's ballDistance set to the pinned distance squared): reached = headed; then the meter's window frame: entry 20's
result = the rule. Not covered here: that the live game runs that test for the man within the window and that nobody
else touches the pinned ball (DOSBox).
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_EIP

import difficulty as df
import diff_structural as ds
import setpieces as sp
import spmeter
import swreg
import tr_gate
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
    d1 = p.le.obj_bytes(1)
    s, c = sp.find(p)
    ts, c2 = tr.find(p)
    _, sym = df.find(p)
    d0 = sym['D0_'][1]
    a1, a4, a6 = (2, d0 + 36), (2, d0 + 48), sym['A6_']
    t = lambda o: df._t(p, o)
    top = B2 + c2['TOP_O']
    bot = top + 0x91
    ball = B2 + c['BALL_O']
    spr0 = ball - 22 * 0x6E
    blk = bytes(img[4]).find(spmeter.TAG, spmeter.SPM_AT, spmeter.SPM_AT + spmeter.LOG_AT)
    mode = img[4][blk + spmeter.OFF['MODE']]
    assert blk > 0 and mode in (5, 6), 'not an SP_METER_MODE=5 / 6 build'
    log = spmeter.SPM_AT + spmeter.LOG_AT
    ph = [s['JZ'] - 0x80 + x.start() for x in re.finditer(rb'\x8b\x35....\x66\xc7\x86\x80\x00\x00\x00\x00\x00',
                                                          d1[s['JZ'] - 0x80:s['JZ']], re.S)]
    ph = [o for o in ph if t(o + 2) == a6]
    pa = [x.start() for x in re.finditer(rb'\x8b\x35....\x66\xc7\x46\x62\x00\x00\x66\xa1....\x8b\x35....\x66\x89\x46\x2a', d1, re.S)
          if t(x.start() + 2) == a1 and t(x.start() + 14) == (2, d0)]
    tab = bytes(img[2]).find(struct.pack('<16H', *(61 * i for i in range(16))))
    gp = [x.start() for x in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x02\x66\xa3....\x66\x83\x2d....\x01\xc7\x05........', d1, re.S)
          if t(x.start() + 30) == (2, tab) and t(x.start() + 26) == a4]
    pa = [o for o in pa if ph and 0 < ph[0] - o < 0x100]
    assert len(ph) == len(pa) == len(gp) == 1, (ph, pa, gp)
    ph, pa, gp = ph[0], pa[0], gp[0]
    wind = ts['DIST1'] - 49                              # @@check_if_header_winded_up
    assert d1[wind:wind + 2] == b'\x8b\x35' and d1[wind + 6:wind + 10] == b'\x80\x7e\x0d\x2a' and d1[wind + 10:wind + 12] == b'\x0f\x82', \
        d1[wind:wind + 16].hex()
    upd = wind + 16 + struct.unpack_from('<i', d1, wind + 12)[0]     # @@update_player_speed_and_deltas
    R = B4 + swreg.TRHD_END - 16
    bands = tuple((B4 + lo, B4 + hi) for lo, hi in ((spmeter.SPM_AT, spmeter.SPM_AT + spmeter.LOG_AT), (swreg.TRHD_AT, swreg.TRHD_END),
                                                    (swreg.SETPIECE_AT, swreg.SETPIECE_END), (swreg.SPX_AT, swreg.SPX_END)))
    game = ((B1 + ph, B1 + s['FZ'] + 0x60), (B1 + gp, B1 + gp + 0x80), (B1 + pa, B1 + pa + 0x90))
    rec = ds.SCR + 0x30000
    trg = sj['difficulty']['SYMS.TRG'][1]
    df.SYMS.update(sym)                                 # (spmeter.find reads difficulty's symbols: a host run fills them)
    df.SYMS['SPR0'] = (2, c['BALL_O'] - 22 * 0x6E)
    lpp = B2 + spmeter.find(p)['LPP_O']

    def mach(ru, spw, k):
        m = ds.Mach(img, f'g{mode}{ru}{spw}')
        m.w8(B4 + L['TR_RU'], ru)
        m.w8(B4 + S['SP_OK'], 1)
        m.w16(B4 + S['SP_W'], spw)
        m.w32(B4 + S['PR_D'], 0)
        m.w16(B2 + trg, 0)
        m.w16(B2 + c['GSP_O'], 100)
        m.w16(B2 + c['GS_O'], 100)
        m.w32(B4 + D['DF_FRAMES'], 5000)
        for tm, other, num, r_ in ((top, bot, 1, rec), (bot, top, 2, rec + 0x1000)):
            m.read(tm, 0x91)
            m.uc.mem_write(tm, bytes(0x91))
            m.w32(tm, other)
            m.w16(tm + 0x12, num)
            m.w32(tm + 0x0A, r_)
        m.read(spr0, 23 * 0x6E)
        m.uc.mem_write(spr0, bytes(23 * 0x6E))
        for i, num in ((9, 1), (20, 2)):
            m.w16(spr0 + i * 0x6E, num)
            m.w16(spr0 + i * 0x6E + 2, 10)
        m.w16(B4 + blk + spmeter.OFF['NC'], k)
        m.w32(B4 + blk + spmeter.OFF['LN'], 0)
        return m

    def frame(m):
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
        m.w32(ds.STACK, R)
        return ds.run(m, B4 + spmeter.SPM_AT, R, bands + game, max_steps=60000)[1]

    n = bad = 0
    first = []

    def chk(ok, *what):
        nonlocal n, bad
        n += 1
        if not ok:
            bad += 1
            if len(first) < 10:
                first.append(' '.join(str(w) for w in what))
    if mode == 5:
        for ru, spw in ((1, 0), (1, 1), (0, 0), (0, 1)):
            for k in range(tr_gate.NH):
                m = mach(ru, spw, k)
                err = frame(m)
                es = list(tr_gate.entries(m.read(B4 + log, 32), 19))
                cs = tr_gate.hcase(k)
                want = tr_gate.hexpect(k, ru, spw)
                sprite = spr0 + (20 if k & 1 else 9) * 0x6E
                x, y = (struct.unpack('<H', m.read(sprite + o, 2))[0] for o in (0x20, 0x24))
                wy = 129 + tr_gate.H5A[cs['spot']] if k & 1 else 769 - tr_gate.H5A[cs['spot']]
                chk(not err and len(es) == 1 and (es[0]['k'], es[0]['a'], es[0]['b'], es[0]['d'], es[0]['v']) ==
                    (k, cs['pos'], cs['heading'], cs['team'], want) and (x, y) == (tr_gate.H5X[cs['spot']], wy),
                    'MODE 5', ru, spw, cs, es and hex(es[0]['v']), hex(want), (x, y), err)
    else:
        for ru in (1, 0):
            for k in range(tr_gate.NR):
                m = mach(ru, 0, k)
                err = frame(m)
                cs = tr_gate.rcase(k)
                want = tr_gate.rexpect(k, ru)
                team = bot if k & 1 else top
                sprite = spr0 + (20 if k & 1 else 9) * 0x6E
                st = (m.read(sprite + 0x0C, 1)[0], m.read(sprite + 0x0D, 1)[0], struct.unpack('<H', m.read(sprite + 0x62, 2))[0],
                      struct.unpack('<H', m.read(ball + 0x28, 2))[0], m.read(B4 + blk + spmeter.OFF['ST'], 1)[0])
                bx, mx = (struct.unpack('<H', m.read(a + 0x20, 2))[0] for a in (ball, sprite))
                # the game's contact test for this man (his ballDistance as its UpdatePlayers would have it)
                m.w32(sprite + 0x4A, cs['r'] ** 2)
                m.w32(B2 + a1[1], sprite)
                m.w32(B2 + a6[1], team)
                m.w32(B2 + c['A2_O'], ball)                   # (UpdatePlayers' A2: the ball)
                m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
                lg, e2 = ds.run(m, B1 + wind, (B1 + ph, B1 + upd), bands + ((B1 + wind, B1 + s['CEIL1'] + 0x100),), max_steps=20000)
                hit = m.uc.reg_read(UC_X86_REG_EIP) == B1 + ph
                if hit:
                    m.w32(lpp, sprite)                   # (the game's PlayerHittingJumpHeader call site sets it)
                m.w32(B4 + D['DF_FRAMES'], 5000 + (3 if hit else 30))
                e3 = frame(m)
                es = list(tr_gate.entries(m.read(B4 + log, 16 * 40), 20))
                chk(not (err or e2 or e3 or lg) and st == (9, 55, 0, 13, 2) and bx - mx == cs['r'] and hit == bool(want)
                    and len(es) == 1 and (es[0]['k'], es[0]['a'], es[0]['b'], es[0]['c'], es[0]['d']) ==
                    (k, cs['pos'], cs['heading'], cs['r'], want),
                    'MODE 6', ru, cs, 'state', st, 'dx', bx - mx, 'hit', hit, want, es and es[0]['d'], err, e2, e3)
    for f in first:
        print('DIFF', f)
    print(f'spmeter MODE {mode} on the host: {n} forced cases, {bad} different: {"PASS" if not bad else "FAIL"}')
    return not bad



if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)
