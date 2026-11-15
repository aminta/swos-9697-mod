"""4.2 W1 cover role (14/11, Davide: one CPU defender at a time) on the host: w1_cov in the DIFF2 band.

  internal/hosttest/.venv/bin/python tools/hosttest/w1cov_check.py BUILD     (a DIFF_TEST=3 HOSTTEST_SYMS=1 IT build)

w1_cov(ebx = the defending team, esi = presser 2): DIFENSORI CPU 2 / 3 with presser 1 (team.controlledPlayer) goal-side
-> ZF = 1, eax = y << 16 | x on the ball -> own goal centre line, W1_COV px from the ball (octagonal length, +-12%);
presser 1 beaten (not goal-side), level 1 (ASPETTANO), no presser 1 or presser 2 = presser 1 -> ZF = 0 (engage, drp4).
The double: drawn once per carrier, 1 in 4 (level 2) / 1 in 16 (level 3). df_blk runs as an external routine here
(ebx kept: the level is read at team + 20, set by the test)."""
import json
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EAX, UC_X86_REG_EFLAGS

import diff_structural as ds
import difficulty as df
import swreg
from lepatch import LEPatch

B2, B4 = ds.B2, ds.B4


def run_keep(m, start, end, allowed, keep_at):
    """ds.run, but the stand-in for the routine at keep_at (df_blk) keeps eax / edx, as the real one does (push / pop
    eax): w1_on reads [eax + 28h] after it."""
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_EDX
    uc = m.uc
    saved = {}

    def pre(uc, addr, size, _):
        if addr == keep_at:
            saved['a'] = (uc.reg_read(UC_X86_REG_EAX), uc.reg_read(UC_X86_REG_EDX),
                          struct.unpack('<I', m.read(uc.reg_read(UC_X86_REG_ESP), 4))[0])
        elif saved.get('a') and addr == saved['a'][2]:
            uc.reg_write(UC_X86_REG_EAX, saved['a'][0])
            uc.reg_write(UC_X86_REG_EDX, saved['a'][1])
            saved['a'] = None
    h = uc.hook_add(UC_HOOK_CODE, pre)
    try:
        return ds.run(m, start, end, allowed)
    finally:
        uc.hook_del(h)


def main():
    bd = sys.argv[1]
    img = ds.images(os.path.join(bd, 'ITALIAN.EXE'))
    lab = {k: v[1] for k, v in json.load(open(os.path.join(bd, 'ITALIAN.syms.json')))['difficulty'].items()}
    p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
    _, sym = df.find(p)
    bally = df.w1_find(p, sym)['BALLY'][1]
    cov = int(os.environ.get('DIFF_W1COV') or df.W1_COV)
    det = int(os.environ.get('DIFF_W1DET') or df.W1_DET)
    sh, sh2 = int(os.environ.get('DIFF_W1SH') or df.W1_SH), int(os.environ.get('DIFF_W1SH2') or df.W1_SH2)
    R = B4 + swreg.DIFF2_END - 16
    allowed = ((B4 + swreg.DIFF2_AT, B4 + swreg.DIFF2_END), (B4 + swreg.DRIB1V1_AT, B4 + swreg.DRIB1V1_END))
    tm = ds.SCR + 0x34000                       # (the defending team; its opponents at tm + 0x91 - top < bottom)
    bad, n, geo = [], 0, []
    mem = {}

    def go(m, team, p2):
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.w32(ds.STACK, R)
        m.uc.reg_write(UC_X86_REG_EBX, team)
        m.uc.reg_write(UC_X86_REG_ESI, p2)
        log, err = ds.run(m, B4 + swreg.DIFF2_AT, R, allowed)
        zf = bool(m.uc.reg_read(UC_X86_REG_EFLAGS) & 0x40)
        return zf, m.uc.reg_read(UC_X86_REG_EAX), err, m.uc.reg_read(UC_X86_REG_EBX), m.uc.reg_read(UC_X86_REG_ESI)

    m = ds.Mach(img, 'w1cov')
    r = random.Random(1)
    for t in range(3000):
        top = r.random() < 0.5
        team, opp = (tm, tm + 0x91) if top else (tm + 0x91, tm)
        lvl = r.choice((1, 2, 2, 3, 3))
        p1, p2, car = ds.SCR + 0x30000, ds.SCR + 0x30100, ds.SCR + 0x30200 + (t % 7) * 0x10
        bx, by = r.randrange(120, 550), r.randrange(160, 740)
        gs1 = r.random() < 0.75                 # presser 1 goal-side?
        gy = 129 if top else 769
        y1 = by + (-8 if (gy < by) == gs1 else 8)
        m.w32(team, opp)
        m.w32(opp, team)
        m.w16(team + 20, lvl)
        m.w32(team + 0x20, r.choice((p1, p1, p1, p1, 0, p2)))
        m.w32(opp + 0x20, car)
        m.w16(team + 0x62, bx)
        m.w16(team + 0x64, by)
        m.w16(B2 + bally, by)
        m.w16(p1 + 0x24, y1)
        x2, y2 = r.randrange(100, 570), by + r.randrange(-60, 61)
        m.w16(p2 + 0x20, x2)
        m.w16(p2 + 0x24, y2)
        gs2 = (y2 < by) if top else (y2 > by)   # (w1_gs: strictly between the ball and his goal)
        zf, eax, err, ebx_, esi_ = go(m, team, p2)
        n += 1
        if err or ebx_ != team or esi_ != p2:
            bad.append(f'run {t}: {err} regs kept {ebx_ == team} {esi_ == p2}')
            continue
        c1 = struct.unpack('<I', m.read(team + 0x20, 4))[0]
        eng = c1 in (0, p2) or lvl == 1 or not gs1
        if eng and zf:
            bad.append(f'{t}: cover where it must engage (level {lvl} p1 {c1:#x} gs {gs1})')
            continue
        if not zf:
            mem.setdefault(lvl, []).append((car, eng))
            continue
        mem.setdefault(lvl, []).append((car, False))
        x, y = eax & 0xFFFF, eax >> 16
        x -= 0x10000 if x & 0x8000 else 0
        y -= 0x10000 if y & 0x8000 else 0
        if not gs2:                             # (presser 2 behind the ball: the recovery run, W1_DET px to his side)
            x -= det if x2 >= bx else -det
        gx, gyy = 336 - bx, gy - by
        L = math.hypot(gx, gyy)
        d = math.hypot(x - bx, y - by)
        want = min(cov, L) if L >= cov else cov
        ang = abs(math.atan2(y - by, x - bx) - math.atan2(gyy, gx)) if d else 0
        ang = min(ang, 2 * math.pi - ang)
        geo.append((d, ang))
        if L > cov and not (0.86 * cov <= d <= 1.14 * cov and ang < 0.08):
            bad.append(f'{t}: cover point ({x},{y}) ball ({bx},{by}) goal (336,{gy}): {d:.1f} px, {math.degrees(ang):.1f} deg')
        if not ((by <= y <= gy) or (gy <= y <= by)):
            bad.append(f'{t}: cover point not between the ball and the goal: y {y} ball {by} goal {gy}')
    # W1 A's shift (w1_sh, DIFF2_AT + 5): cl = W1_SH at levels 0 / 1, W1_SH2 at 2 / 3, ebx kept
    from unicorn.x86_const import UC_X86_REG_ECX
    m3 = ds.Mach(img, 'w1sh')
    for lvl in (0, 1, 2, 3):
        m3.w16(tm + 20, lvl)
        m3.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m3.w32(ds.STACK, R)
        m3.uc.reg_write(UC_X86_REG_EBX, tm)
        m3.uc.reg_write(UC_X86_REG_ECX, 0x12345600)
        log, err = ds.run(m3, B4 + swreg.DIFF2_AT + 5, R, allowed)
        cl = m3.uc.reg_read(UC_X86_REG_ECX)
        n += 1
        want = sh2 if lvl >= 2 else sh
        if err or cl != 0x12345600 | want or m3.uc.reg_read(UC_X86_REG_EBX) != tm:
            bad.append(f'w1_sh level {lvl}: ecx {cl:#x} (want cl {want}) {err}')
    # W1 E (w1_nb, DIFF2_AT + 10): an off-ball outfielder near the ball while a teammate is on it (16 px) -> dest pushed
    # out to W1_NBD px from the ball (octagonal length, same direction; on the ball's spot: toward his goal)
    nbr, nbd = int(os.environ.get('DIFF_W1NBR') or df.W1_NBR), int(os.environ.get('DIFF_W1NBD') or df.W1_NBD)
    m4 = ds.Mach(img, 'w1nb')
    tbl0, spr = ((ds.SCR + 0x40000) & ~0xFFFF), ds.SCR + 0x36000
    assert tbl0 >= ds.SCR + 0x37000
    held = 0
    for t in range(3000):
        top = r.random() < 0.5
        team, opp = (tm, tm + 0x91) if top else (tm + 0x91, tm)
        lvl = r.choice((0, 1, 2, 2, 3, 3))
        m4.w32(team, opp)
        m4.w32(opp, team)
        m4.w16(opp + 0x28, r.choice((0, 1, 1, 1)))              # (the opponents on the ball)
        tbl = tbl0 + lvl                                        # (the host's df_blk keeps ebx = the team, so the level
        m4.w32(team + 0x14, tbl)                                #  word at +20 = 0x14 is spritesTable's low word)
        bx, by = r.randrange(120, 550), r.randrange(160, 740)
        m4.w16(team + 0x62, bx)
        m4.w16(team + 0x64, by)
        sp = [spr + i * 0x6E for i in range(11)]
        for i, a_ in enumerate(sp):
            m4.w32(tbl + 4 * i, a_)
            m4.w16(a_ + 2, i + 1)
            m4.w32(a_ + 0x4A, r.randrange(300, 90000))
        k = r.randrange(1, 11)                                  # (the player: an outfielder)
        pl = sp[k]
        ctl = r.choice((sp[(k + 1) % 11 or 1], sp[(k + 1) % 11 or 1], pl, 0))
        m4.w32(team + 0x20, ctl)
        m4.w32(pl + 0x4A, r.choice((r.randrange(0, nbr * nbr), r.randrange(nbr * nbr, 2 * nbr * nbr))))
        eng = r.random() < 0.6
        if eng:
            j = r.choice([i for i in range(11) if i != k])
            m4.w32(sp[j] + 0x4A, r.randrange(0, 256))
        dx, dy = r.randrange(-60, 61), r.randrange(-60, 61)
        if r.random() < 0.05:
            dx = dy = 0
        m4.w16(pl + 0x3A, (bx + dx) & 0xFFFF)
        m4.w16(pl + 0x3C, (by + dy) & 0xFFFF)
        m4.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m4.w32(ds.STACK, R)
        m4.uc.reg_write(UC_X86_REG_EBX, team)
        m4.uc.reg_write(UC_X86_REG_ESI, pl)
        log, err = run_keep(m4, B4 + swreg.DIFF2_AT + 10, R, allowed, B4 + lab['df_blk'])
        n += 1
        gx, gy = struct.unpack('<hh', m4.read(pl + 0x3A, 4))
        bd = struct.unpack('<I', m4.read(pl + 0x4A, 4))[0]
        on = (lvl >= 2 and struct.unpack('<H', m4.read(opp + 0x28, 2))[0] and ctl != pl and bd < nbr * nbr
              and any(struct.unpack('<I', m4.read(a_ + 0x4A, 4))[0] < 256 for a_ in sp if a_ != pl and
                      struct.unpack('<H', m4.read(a_ + 2, 2))[0] != 1))
        L = max(abs(dx), abs(dy)) + min(abs(dx), abs(dy)) // 2
        if on and L < nbd:
            if L == 0:
                want = (bx, by + (-nbd if top else nbd))
            else:
                want = (bx + int(dx * nbd / L), by + int(dy * nbd / L))
            held += 1
        else:
            want = (bx + dx, by + dy)
        if err or (gx, gy) != want:
            bad.append(f'w1_nb {t}: level {lvl} on {bool(on)} dest ({gx},{gy}) want {want} ball ({bx},{by}) d ({dx},{dy}) {err}')
    if held < 60:
        bad.append(f'w1_nb: only {held} held cases')
    # double rates: per level, the share of "engage" draws among cases that should cover, one draw per carrier change
    rate = {}
    for lvl in (2, 3):
        m2 = ds.Mach(img, f'rate{lvl}')
        dbl, k = 0, 0
        for i in range(1600):
            team, opp = tm, tm + 0x91
            p1, p2 = ds.SCR + 0x30000, ds.SCR + 0x30100
            m2.w32(team, opp)
            m2.w32(opp, team)
            m2.w16(team + 20, lvl)
            m2.w32(team + 0x20, p1)
            m2.w32(opp + 0x20, ds.SCR + 0x31000 + 4 * i)       # (a new carrier every call)
            m2.w16(team + 0x62, 300)
            m2.w16(team + 0x64, 400)
            m2.w16(B2 + bally, 400)
            m2.w16(p1 + 0x24, 392)                              # (goal-side for the top team: y < ball)
            zf, *_ = go(m2, team, p2)
            zf2, *_ = go(m2, team, p2)                          # (same carrier: the same draw)
            n += 2
            if zf != zf2:
                bad.append(f'level {lvl}: the draw changed with the same carrier')
            k += 1
            dbl += not zf
        rate[lvl] = dbl / k
    if not 0.19 <= rate[2] <= 0.31:
        bad.append(f'level 2 double rate {rate[2]:.3f} (want 1/4)')
    if not 0.03 <= rate[3] <= 0.10:
        bad.append(f'level 3 double rate {rate[3]:.3f} (want 1/16)')
    print(f'w1_cov host check: {n} calls, cover points {len(geo)} (distance {min(g[0] for g in geo):.1f}..'
          f'{max(g[0] for g in geo):.1f} px, max angle {math.degrees(max(g[1] for g in geo)):.2f} deg), double rate '
          f'level 2 {rate[2]:.3f}, level 3 {rate[3]:.3f}, W1 E held {held}: {"PASS" if not bad else "FAIL"}')
    for b in bad[:12]:
        print('  -', b)
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
