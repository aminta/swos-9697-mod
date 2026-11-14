#!/usr/bin/env python3
"""4.2 set pieces §3 (Davide GO 14/11): the free-kick trajectory model, from the game's own constants (ref/swos.asm).

    python3 tools/fkmodel.py [--extra G] [--after PX] [--speed-table]

The ball, per tick (UpdateBall 109960..110100, ApplyBallAfterTouch 104749):
- in the air: speed -= kBallAirSpeedReduction (4); x / y move speed / 512 x 41 / 64 px (Sprite.speed: Q7.9);
- z: deltaZ -= kBallAirFriction (3291 / 65536); z += deltaZ (16.16);
- the kick (PlayerKickingBall): speed kBallKickingSpeed 2208 (+ kBallSpeedKicking[SHOOTING] only inside the long-shot
  zone, never from a free kick's wall zone... see LONG below), deltaZ kBallKickingDeltaZ 0x14000 (1.25);
- the after-touch at spinTimer 4 (the 4th tick): forward held = nothing (the DRIVE); no direction or sideways = deltaZ
  kNormalKickDeltaZ 0x16000 (1.375), speed kNormalKickBallSpeed 2560, then x 0.75 (facing straight) / x 0.875
  (diagonal) - the NORMAL kick; back held = deltaZ 0x20000, speed 2688 - the HIGH kick (always over).
Geometry: the wall 55 px from the ball (dseg_17E991's -55 / -54 rows), the bar z 15 (a goal needs z <= 15 when the
ball crosses the line), a header contact z 8..15 (NUOVI ceiling SP_CEIL 17); the keeper's catch band 13..27 (NUOVI 22).
A wall man stops the ball only by heading it (z 8..ceiling, his fire) or controlling it (z <= 12): so the kick must be
over the wall's head-height ceiling at 55 px and at z <= 15 at the line.

§3 knob modelled: from the wall on (the ball past the wall's distance), every tick deltaZ -= EXTRA (16.16) more - the
taker's SHOOTING picks EXTRA (a table by skill). The table this prints is what the stub would carry.
"""
import argparse

G = 3291
AIR = 4
WALL = 38                                # (the wall stands ~35-40 px from the ball: meter 14/11; dseg_17E991 is not px)
BAR = 15


def fly(kind, extra=0, after=WALL, ticks=200, speed0=2208, dz0=0x14000):
    """[(dist px, z)] per tick for a kick: kind 'drive' / 'normal' / 'normal_diag' / 'high'; extra = more gravity per
    tick (16.16) once dist >= after."""
    z, dz, sp, d = 0, dz0, speed0, 0.0
    out = []
    for t in range(1, ticks):
        if t == 4:                          # (ApplyBallAfterTouch at spinTimer 4)
            if kind.startswith('normal'):
                dz, sp = 0x16000, 2560
                sp = sp - (sp >> 2) if kind == 'normal' else sp - (sp >> 2) + (sp >> 3)
            elif kind == 'high':
                dz, sp = 0x20000, 2688
        sp = max(0, sp - AIR)
        d += sp / 512 * 41 / 64
        if dz:
            dz -= G
            if d >= after:
                dz -= extra
            dz |= 1
        z += dz
        out.append((d, z / 65536))
        if z < 0:
            break
    return out


def z_at(tr, dist):
    for (d0, z0), (d1, z1) in zip(tr, tr[1:]):
        if d0 <= dist <= d1:
            return z0 + (z1 - z0) * (dist - d0) / (d1 - d0) if d1 > d0 else z1
    return None


def window(kind, extra=0, ceil=15, after=WALL):
    """The distances (px from the ball to the goal line, 5 px steps) from which the kick clears the wall (z > ceil at
    WALL) and is under the bar (z <= 15, > 0) at the line."""
    tr = fly(kind, extra, after)
    zw = z_at(tr, WALL)
    ok = []
    for dist in range(60, 205, 5):
        zl = z_at(tr, dist)
        if zw is not None and zw > ceil and zl is not None and 0 < zl <= BAR:
            ok.append(dist)
    return zw, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ceil', type=int, default=15, help='the wall header ceiling (CLASSICI 15, NUOVI SP_CEIL 17)')
    a = ap.parse_args()
    print(f'wall at {WALL} px, header ceiling {a.ceil}, bar {BAR}; free-kick wall zone 87..202 px from the line')
    for kind in ('drive', 'normal', 'normal_diag', 'high'):
        zw, ok = window(kind, 0, a.ceil)
        print(f'{kind:12} today: z at wall {zw:.1f}; goal window {ok[0] if ok else "-"}..{ok[-1] if ok else "-"} px')
    print('extra gravity after the wall (16.16 per tick): goal window, normal / normal_diag / drive')
    for extra in range(0, 3001, 250):
        w = []
        for kind in ('normal', 'normal_diag', 'drive'):
            zw, ok = window(kind, extra, a.ceil)
            w.append(f'{ok[0]}..{ok[-1]}' if ok else '-')
        print(f'  {extra:5}: ' + '  '.join(f'{x:>9}' for x in w))


if __name__ == '__main__':
    main()
