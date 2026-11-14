"""DRIBBLING test (4.2, Davide 12/11 via Regia: "sì, vai con DRIBBLING"): a calmer match at the normal 70 fps, more room
on the ball. Study: internal/handoff/calm-match-study.md (preset 1 = knobs A + B + C). Only with DRIBBLE_TEST=1 (a test
build, modver's TEST_VARS): the default build stays byte-identical.
- A, UpdatePlayerSpeed: the controlled player with the ball runs at speed - speed >> 3 (87.5 %): `shr word [D0], 3` ->
  4 (93.75 %): a chaser of the same speed catches him half as fast. Both teams.
- B, the second chaser's hold-back (UpdatePlayers, ~116694 / 116704): he stays off the carrier only when the controlled
  player and he are both within ballDistance 3200 (squared px: 57 px) and the controlled one is nearer; both radii ->
  4400 (66 px): fewer two-against-one. Both teams (a human team's second chaser is AI too).
- C, wonTheBallTimer = 12 after a lost contact (CalculateIfPlayerWinsBall) and a won tackle: 16 team updates (+0.11 s)
  before the beaten side can touch the ball again. Both teams.
Immediates only: 1 + 2 x 4 + 2 x 1 bytes, no code, no room. Simulated results (CalculateViewResult) never run this
engine: careers / unwatched CPU matches are untouched."""
import os
import re
import struct

A = rb'\x66\x8b\x46\x2c\x66\xa3(....)\x66\x0b\xc0\x66\xc1\x2d\1\x03\x66\xa1\1\x8b\x35....\x66\x29\x46\x2c'
B = rb'\x81\x7e\x4a\x80\x0c\x00\x00\x77'           # cmp dword [esi+Sprite.ballDistance], 3200 / ja short
C = rb'\x66\xc7\x86\x8a\x00\x00\x00\x0c\x00'        # mov word [esi+TeamGeneralInfo.wonTheBallTimer], 12
SHIFT, RADIUS, LOCK = 4, 4400, 16


def on():
    return bool(os.environ.get('DRIBBLE_TEST'))


def sites(d):
    """[(name, obj1 offset, original bytes, new bytes)] in obj1 bytes d (the original exe's, every language)"""
    a = [m.start() for m in re.finditer(A, d, re.S)]
    b = [m.start() for m in re.finditer(B, d)]
    c = [m.start() for m in re.finditer(C, d)]
    assert len(a) == 1 and len(b) == 2 and len(c) == 2, ('dribble sites', len(a), len(b), len(c))
    assert 0 < b[1] - b[0] < 0x40, 'the two hold-back radii are one block'
    out = [('A carrier shr', a[0] + 20, b'\x03', bytes((SHIFT,)))]
    out += [(f'B hold-back radius {i}', x + 3, struct.pack('<I', 3200), struct.pack('<I', RADIUS)) for i, x in enumerate(b)]
    out += [(f'C wonTheBallTimer {i}', x + 7, b'\x0c\x00', struct.pack('<H', LOCK)) for i, x in enumerate(c)]
    return out


def patch(p):
    if not on():
        return
    d = p.le.obj_bytes(1)
    for name, at, old, new in sites(d):
        assert p.get(1, at, len(old)) == old, (name, p.get(1, at, len(old)).hex())
        p.put(1, at, new)
    print(f'exe: DRIBBLING test - carrier at 93.75 %, second chaser holds back within 66 px, win-back lockout {LOCK} '
          '(5 sites)')
