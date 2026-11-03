"""4.0.6 long dugouts (Davide 03/11, option A): both in-match dugouts 6 tile rows longer, 18 seats each.

The dugouts are pitch-map tiles: PITCHn.DAT (55 rows x 42 dword offsets into PITCHn.BLK, 256-byte 16 x 16 patterns,
296 at most) for the five match pitches (PITCH6, the training pitch, is not touched). Each dugout is 5 tile rows in
columns 0-1: the roof cap, 2 middle rows (the seats), the seat end, the steps; the top one rows 23-27 (SWOS y
368..447), the bottom one rows 29-33 (464..543), the halfway line between them (y 449, row 28).

Here the top dugout grows upwards (cap row 17, middle rows 18-25, end 26, steps 27) and the bottom one downwards
(cap 29, middle 30-37, end 38, steps 39): 8 middle rows = 128 px of seats, a seat every 7 px. Every tile comes from
the original dugouts in the same grass-stripe phase (the row's place in the stripes' period: 1 row on PITCH1, 4 on
PITCH2-4, 6 on PITCH5); a middle tile missing in a phase (PITCH5's left column: the diagonal stripes, 4 of 6 phases)
is made from one that exists, its grass pixels swapped for the phase's grass (the box's own pixels are a clean block
of columns: asserted). The new patterns go at the end of the BLK file (PITCH5: 269 -> 273).

The exe side (benchx.py block 2): the top bench's y 389 -> 293, every bench place seated (no window), the camera on
the own dugout in the subs menu.

gen(dst_dir) writes PITCH1-5.DAT (and a BLK that grew) from orig/ into dst_dir (beside the exe, as kitfix's
KITFIX.DAT); the patcher ships them (mkpatcher FILES).
"""
import os
import struct

ROOT = os.path.join(os.path.dirname(__file__), '..')
PITCHES = (1, 2, 3, 4, 5)
ADD = 6                                     # tile rows added to each dugout (Davide: 18 seats)
TOP = (23, 24, 25, 26, 27)                  # cap, middle, middle, end, steps
BOT = (29, 30, 31, 32, 33)
MAX_PATTERNS = 296                          # the game's PITCHn.BLK buffer (75776 bytes)
COLS = 42


def layout():
    """{row: kind} for the long dugouts (kind: cap / mid / end / steps); the rows they take over were grass."""
    rows = {}
    for cap, end in ((TOP[0] - ADD, TOP[3]), (BOT[0], BOT[3] + ADD)):
        rows[cap] = 'cap'
        for r in range(cap + 1, end):
            rows[r] = 'mid'
        rows[end] = 'end'
        rows[end + 1] = 'steps'
    return rows


def kinds(r):
    """The original dugouts' row r: its kind."""
    return ('cap', 'mid', 'mid', 'end', 'steps')[(TOP if r in TOP else BOT).index(r)]


def pitch(n, src=None):
    """(new DAT bytes, new BLK bytes or None when unchanged, info) for PITCHn."""
    src = src or os.path.join(ROOT, 'orig')
    dat = list(struct.unpack('<2310I', open(os.path.join(src, f'PITCH{n}.DAT'), 'rb').read()))
    blk = bytearray(open(os.path.join(src, f'PITCH{n}.BLK'), 'rb').read())
    assert len(blk) % 256 == 0 and all(v % 256 == 0 for v in dat), n
    T = lambda r, c: dat[r * COLS + c] // 256
    pat = lambda i: bytes(blk[i * 256:(i + 1) * 256])
    new = layout()
    grass = [r for r in range(8, 47) if r not in TOP and r not in BOT]
    assert all(r in grass for r in new if r not in TOP and r not in BOT), n
    per = next(p for p in range(1, 9) if all(T(r, c) == T(q, c) for c in (0, 1) for r in grass for q in grass
                                             if (q - r) % p == 0))
    g = lambda r, c: T(next(q for q in grass if (q - r) % per == 0), c)
    have = {}                               # (kind, column, phase) -> tile
    for r in TOP + BOT:
        for c in (0, 1):
            have.setdefault((kinds(r), c, r % per), T(r, c))
    made = []
    for r, k in sorted(new.items()):
        for c in (0, 1):
            key = (k, c, r % per)
            if key not in have:             # a phase with no such tile: from one that exists, the grass swapped
                ph, t = next((p, t) for (kk, cc, p), t in sorted(have.items()) if kk == k and cc == c)
                s, g0, g1 = pat(t), pat(g(ph, c)), pat(g(r, c))
                box = [x for x in range(16) if any(s[y * 16 + x] != g0[y * 16 + x] for y in range(16))]
                assert box and box == list(range(box[0], 16)) and all(
                    s[y * 16 + x] != g0[y * 16 + x] for y in range(16) for x in box), (n, key, 'box not a clean block')
                tile = bytes(s[i] if i % 16 >= box[0] else g1[i] for i in range(256))
                old = [i for i in range(len(blk) // 256) if pat(i) == tile]   # (no grass in it: the same tile)
                if old:
                    have[key] = old[0]
                else:
                    have[key] = len(blk) // 256
                    blk += tile
                    made.append(key)
            dat[r * COLS + c] = have[key] * 256
    npat = len(blk) // 256
    assert npat <= MAX_PATTERNS, (n, npat)
    return (struct.pack('<2310I', *dat), bytes(blk) if made else None,
            f'PITCH{n}: period {per}, {len(new)} rows, {len(made)} new patterns ({npat} of {MAX_PATTERNS})')


def gen(dst_dir, src=None):
    """Writes PITCH1-5.DAT (+ a grown BLK) into dst_dir; returns the log line."""
    out = []
    for n in PITCHES:
        d, b, info = pitch(n, src)
        open(os.path.join(dst_dir, f'PITCH{n}.DAT'), 'wb').write(d)
        if b:
            open(os.path.join(dst_dir, f'PITCH{n}.BLK'), 'wb').write(b)
        out.append(info)
    return '; '.join(out)


if __name__ == '__main__':
    import sys
    print(gen(sys.argv[1]))
