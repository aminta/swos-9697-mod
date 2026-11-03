"""4.0.6 two-row dugouts (Davide 03/11, two-row V1): both in-match dugouts 2 tile rows longer and one tile column
wider, two rows of 8 figures each (coach + 7, then 8 in front).

The dugouts are pitch-map tiles: PITCHn.DAT (55 rows x 42 dword offsets into PITCHn.BLK, 256-byte 16 x 16 patterns,
296 at most) for the five match pitches (PITCH6, the training pitch, is not touched). Each dugout is 5 tile rows in
columns 0-1: the roof cap, 2 middle rows (the seats), the seat end, the steps; the top one rows 23-27 (SWOS y
368..447), the bottom one rows 29-33 (464..543), the halfway line between them (y 449, row 28). Across: the roof
(x 11..26), then the floor in the roof's shadow (x 27..31) where the bench sits.

Here the top dugout grows upwards (cap row 21, middle rows 22-25, end 26, steps 27) and the bottom one downwards
(cap 29, middle 30-33, end 34, steps 35): 4 middle rows. Every tile comes from the original dugouts in the same
grass-stripe phase (the row's place in the stripes' period: 1 row on PITCH1, 4 on PITCH2-4, 6 on PITCH5); a tile
missing in a phase (PITCH5's diagonal stripes) is made from one that exists, its grass pixels (those equal to that
phase's grass) swapped for the phase's grass, pixel by pixel.
The 3rd column (x 32..47, was grass): the floor goes on, each dugout row's column 2 is column 1's last pixel column
(x 31: shadow, or grass above the cap's shadow diagonal) repeated, its grass pixels swapped for the row's column-2
grass. The box is 48 px wide, both rows of figures sit on its floor (x 27..35 and 36..44). The new patterns go at the
end of the BLK file.

The exe side (benchx.py block 2): the top bench's y 389 -> 357, the two rows (back: the coach + places 1..BACK at the
game's seats; front: places BACK+1.. at x + FRONT_X, y + FRONT_Y, the first level with the coach), a standing back-row
figure in front of the front row (exit e), the front row's arrow mirrored on its right, the camera at the halfway
line (both dugouts in one screen).

The 16-colour mode (EGA graphics, ReadPitchFile) reads SWCPICHn.P16 instead: the same 55 x 42 map, then 128-byte
16 x 16 patterns (the file read whole into 65535 bytes: 511 patterns at most). A map dword's high word is the
pattern's byte offset stored big-endian (EGA's fixup swaps the bytes): pattern p = word 0x8000 x (p & 1) + p >> 1.
A pattern is 16 rows of 4 bit planes of 2 bytes (16 pixels, the first the most significant bit), the pixels the
same colour numbers as the VGA tiles' grass. Its map gets the same rows, the tiles taken whole; where a phase has no
middle tile (PITCH5) the original itself draws one middle tile in every phase it has (asserted), and that one is
used. The 3rd column as in VGA (column 1's x 15 repeated, the grass pixels the row's column-2 grass), new patterns
at the end of the file.

gen(dst_dir) writes PITCH1-5.DAT (and a BLK that grew) and SWCPICH1-5.P16 from orig/ into dst_dir (beside the exe,
as kitfix's KITFIX.DAT); the patcher ships them (mkpatcher FILES).
"""
import os
import struct

ROOT = os.path.join(os.path.dirname(__file__), '..')
PITCHES = (1, 2, 3, 4, 5)
ADD = 2                                     # tile rows added to each dugout (two rows of 8 figures)
TOP = (23, 24, 25, 26, 27)                  # cap, middle, middle, end, steps
BOT = (29, 30, 31, 32, 33)
MAX_PATTERNS = 296                          # the game's PITCHn.BLK buffer (75776 bytes)
BACK = 7                                    # (the exe, benchx) places in the back row, after the coach (V1)
FRONT_X, FRONT_Y = 9, 3                     # the front row (places 8..): towards the pitch, a little lower
ARROW_DX = 41                               # the front row's arrow: the game's (x 15..23 at D1 = benchXLimit - 12,
                                            # tip 3 px from the figure) mirrored around x 35.5 (+ 41 on D1)
CAM_MID = 440                               # the bench camera's y (- 100 = its top): both dugouts' span 340..539 in one screen
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


def phases(T, n):
    """(grass-stripe period, grass rows, {(kind, column, phase): tile}) of a map read through T(row, column)."""
    grass = [r for r in range(10, 47) if r not in TOP and r not in BOT]
    assert all(r in grass for r in layout() if r not in TOP and r not in BOT), n
    per = next(p for p in range(1, 9) if all(T(r, c) == T(q, c) for c in (0, 1) for r in grass for q in grass
                                             if (q - r) % p == 0))
    have = {}
    for r in TOP + BOT:
        for c in (0, 1):
            have.setdefault((kinds(r), c, r % per), T(r, c))
    return per, grass, have


MAX_P16 = 511                               # SWCPICHn.P16's patterns: ReadPitchFile reads 65535 bytes


def p16_word(p):
    """the map's high word for 16-colour pattern p (its byte offset p x 128, big-endian)"""
    return ((p & 1) << 15) | (p >> 1)


def p16_pat(w):
    """the 16-colour pattern of a map high word"""
    return ((w & 0x7fff) << 1) | (w >> 15)


def p16_pixels(b):
    """a 128-byte 16-colour pattern -> 256 pixels (row-major)"""
    return [sum(((b[y * 8 + q * 2 + x // 8] >> (7 - x % 8)) & 1) << q for q in range(4)) for y in range(16) for x in range(16)]


def p16_bytes(px):
    """256 pixels -> a 128-byte 16-colour pattern"""
    out = bytearray(128)
    for y in range(16):
        for x in range(16):
            for q in range(4):
                if px[y * 16 + x] >> q & 1:
                    out[y * 8 + q * 2 + x // 8] |= 0x80 >> (x % 8)
    return bytes(out)


def p16(n, src=None):
    """(new SWCPICHn.P16 bytes, info): the 16-colour map with the long dugouts and their 3rd column."""
    src = src or os.path.join(ROOT, 'orig')
    raw = open(os.path.join(src, f'SWCPICH{n}.P16'), 'rb').read()
    dat = list(struct.unpack('<2310I', raw[:9240]))
    pats = bytearray(raw[9240:])
    assert len(pats) % 128 == 0 and all(v & 0xffff == 0 for v in dat), n
    T = lambda r, c: p16_pat(dat[r * COLS + c] >> 16)
    px = lambda i: p16_pixels(pats[i * 128:(i + 1) * 128])
    new = layout()
    per, grass, have = phases(T, n)
    orig = dict(have)                       # (the original's tiles per (kind, column, stripe phase))
    o = tuple(dat)
    g = lambda r, c: p16_pat(o[next(q for q in grass if (q - r) % per == 0 and q not in new) * COLS + c] >> 16)
    same, made = 0, []
    for r, k in sorted(new.items()):
        for c in (0, 1):
            key = (k, c, r % per)
            if key not in have:             # the original's one tile for this kind and column, whatever the phase
                ts = {t for (kk, cc, p), t in have.items() if kk == k and cc == c}
                assert len(ts) == 1, (n, key, ts)
                have[key] = ts.pop()
                same += 1
            dat[r * COLS + c] = p16_word(have[key]) << 16
    for r in sorted(new):                   # the 3rd column: the floor goes on (column 1's x 15 repeated)
        ph = r % per                        # g1: the grass of the stripe phase column 1's tile comes from (PITCH5's
        if orig.get((new[r], 1, ph)) != T(r, 1):    # one tile for every phase: its own phase's grass)
            ph = min(p for (k, c, p), t in orig.items() if k == new[r] and c == 1 and t == T(r, 1))
        t1, g1, g2 = px(T(r, 1)), px(g(ph, 1)), px(g(r, 2))
        assert sum(a != b for a, b in zip(px(T(r, 2)), g2)) <= 32, (n, r)   # (it was grass: SWCPICH1 rows 34-37
                                                                            # have a variant, 205: a few pixels)
        tile = p16_bytes([g2[y * 16 + x] if t1[y * 16 + 15] == g1[y * 16 + 15] else t1[y * 16 + 15]
                          for y in range(16) for x in range(16)])
        old = [i for i in range(len(pats) // 128) if pats[i * 128:(i + 1) * 128] == tile]
        if not old:
            made.append(len(pats) // 128)
            pats.extend(tile)
        dat[r * COLS + 2] = p16_word(old[0] if old else made[-1]) << 16
    npat = len(pats) // 128
    assert npat <= MAX_P16, (n, npat)
    return (struct.pack('<2310I', *dat) + bytes(pats),
            f'SWCPICH{n}: period {per}, {len(new)} rows x 3 columns, {same} phases with the one middle tile, '
            f'{len(made)} new patterns ({npat} of {MAX_P16})')


def pitch(n, src=None):
    """(new DAT bytes, new BLK bytes or None when unchanged, info) for PITCHn."""
    src = src or os.path.join(ROOT, 'orig')
    dat = list(struct.unpack('<2310I', open(os.path.join(src, f'PITCH{n}.DAT'), 'rb').read()))
    blk = bytearray(open(os.path.join(src, f'PITCH{n}.BLK'), 'rb').read())
    assert len(blk) % 256 == 0 and all(v % 256 == 0 for v in dat), n
    T = lambda r, c: dat[r * COLS + c] // 256
    pat = lambda i: bytes(blk[i * 256:(i + 1) * 256])
    new = layout()
    per, grass, have = phases(T, n)
    o = tuple(dat)                          # (the grass from the original map: the new rows were grass rows)
    g = lambda r, c: o[next(q for q in grass if (q - r) % per == 0 and q not in new) * COLS + c] // 256
    made = []

    def add(tile):
        """the pattern's index: an existing one with the same pixels, or a new one at the end"""
        old = [i for i in range(len(blk) // 256) if pat(i) == tile]
        if old:
            return old[0]
        made.append(len(blk) // 256)
        blk.extend(tile)
        return made[-1]
    for r, k in sorted(new.items()):
        for c in (0, 1):
            key = (k, c, r % per)
            if key not in have:             # a phase with no such tile: from one that exists, the grass swapped
                ph, t = next((p, t) for (kk, cc, p), t in sorted(have.items()) if kk == k and cc == c)
                s, g0, g1 = pat(t), pat(g(ph, c)), pat(g(r, c))
                assert s != g0, (n, key)
                have[key] = add(bytes(g1[i] if s[i] == g0[i] else s[i] for i in range(256)))
            dat[r * COLS + c] = have[key] * 256
    for r in sorted(new):                   # the 3rd column: the floor goes on (column 1's x 31 repeated)
        assert T(r, 2) == g(r, 2), (n, r)
        t1, g1, g2 = pat(T(r, 1)), pat(g(r, 1)), pat(g(r, 2))
        dat[r * COLS + 2] = add(bytes(g2[y * 16 + x] if t1[y * 16 + 15] == g1[y * 16 + 15] else t1[y * 16 + 15]
                                      for y in range(16) for x in range(16))) * 256
    npat = len(blk) // 256
    assert npat <= MAX_PATTERNS, (n, npat)
    return (struct.pack('<2310I', *dat), bytes(blk) if made else None,
            f'PITCH{n}: period {per}, {len(new)} rows x 3 columns, {len(made)} new patterns ({npat} of {MAX_PATTERNS})')


def gen(dst_dir, src=None):
    """Writes PITCH1-5.DAT (+ a grown BLK) into dst_dir; returns the log line."""
    out = []
    for n in PITCHES:
        d, b, info = pitch(n, src)
        open(os.path.join(dst_dir, f'PITCH{n}.DAT'), 'wb').write(d)
        if b:
            open(os.path.join(dst_dir, f'PITCH{n}.BLK'), 'wb').write(b)
        out.append(info)
        d, info = p16(n, src)
        open(os.path.join(dst_dir, f'SWCPICH{n}.P16'), 'wb').write(d)
        out.append(info)
    return '; '.join(out)


if __name__ == '__main__':
    import sys
    print(gen(sys.argv[1]))
