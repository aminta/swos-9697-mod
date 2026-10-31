"""CAREER_SEED (test builds only, 4.0.5): a career's random seed pinned. CareerInitVars seeds the game's generators from
currentTick (the timer's count when the career starts: `mov ax,[currentTick]; mov [randomSeed],ax; mov al,[currentTick];
mov [newRandomSeedCopy],al`), so the league draws (a 17-club group's byes) follow the emulator's timing and move with
any change to the exe. With CAREER_SEED=n (0..65535) both reads become the constant n (their fixups removed): the same
draw on every build - the harness's way to land a club's bye on its group's last matchday (world_gplay_seried_bye)."""
import os
import re
import struct


def patch(p):
    v = os.environ.get('CAREER_SEED')
    if not v:
        return
    n = int(v, 0) & 0xFFFF
    d = p.le.obj_bytes(1)
    fx = {f[1]: f[4] for f in p.le.fixups() if f[0] == 1 and f[3] == 2}
    hits = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\xa3....\xa0....\xa2', d, re.S)
            if fx.get(m.start() + 2) is not None and fx.get(m.start() + 13) == fx.get(m.start() + 2)]
    assert len(hits) == 1, hits
    o = hits[0]
    p.remove(1, o + 2)
    p.put(1, o, b'\x66\xb8' + struct.pack('<H', n) + b'\x90\x90')       # mov ax, n
    p.remove(1, o + 13)
    p.put(1, o + 12, b'\xb0' + bytes([n & 0xFF]) + b'\x90\x90\x90')       # mov al, n
    print(f'exe: CAREER_SEED {n} (test build: CareerInitVars obj1+{o:#x} seeds with it, not the timer)')
