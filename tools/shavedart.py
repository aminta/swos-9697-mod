"""4.0.5 the shaved bald look's final art (Marco 01/11: every light and dark head and both icons drawn by him), as data
for bald.c.

shavedart.json (extract() from the editor files in internal/design/bald-mock/shaved-20261030/editor: data.json's head
groups + marco-complete-20261101.json's light, dark and icons) holds, per skin, the 83 heads
(the frames whose head box is the same: 101 frames of a set) as the RAW nibbles to write over the copied raw sprite
(-1 = keep), each head's changed cells as a rectangle (ry, rx from the head box, h x w), the frames' head index and
head box column, and the two 16 x 8 menu icons (converted menu colours: written as they are).

Raw values (bald.c works before the team's colour conversion): light = face 0's identity (6 / 5 / 4 skin, 3 black,
2 white, 1 grey, 0 transparent) and 16 = the light tone 84 <- raw 13 (face 0's variant table: 13 -> nibble 7); dark = face 2's inverse (converted 4 <- raw 6, 3 <- raw 4, 17 = the dark tone 85 <- raw 13, which
the variant's table F makes nibble 7; 1 / 2 the eyes as they are).

Encoding (blob(); bald.c's art_head decodes it): FT = 101 x 3 bytes (head, dark rect origin y << 4 | x, light
origin), then per skin the 83 head records in order, each: h << 4 | w, flag << 7 | number of exceptions, the h x w
rectangle in 2-bit codes (row-major, 4 per byte, high bits first: 0 keep, 1 skull, 2 shade, 3 'alt'), then the
exceptions (cell index, raw value). Skull / shade / alt: light 13 / 5 / 0 (flag 1: alt = 6), dark 6 / 13 / 0.
The light heads + FT + icons go into namespr's unused tail (Integratore + p6 31/10), the dark heads before bald.c in
blond's cave.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(HERE, 'shavedart.json')
NF = 101
SKINS = ('dark', 'light')
RAW = {'dark': {0: 0, 1: 1, 2: 2, 3: 4, 4: 6, 17: 13}, 'light': {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 16: 13}}
CODES = {'dark': (6, 13, 0), 'light': (13, 5, 0)}   # codes 1, 2, 3 (light flag 1: code 3 = 6)
FLAG_ALT = {'light': 6}
ICON_BYTES = 64
ART_FILE = 'marco-complete-20261101.json'     # (Marco 01/11: every head of both skins + both icons, his own)


def extract(src):
    d = json.load(open(os.path.join(src, 'data.json')))
    m = json.load(open(os.path.join(src, ART_FILE)))
    art = {skin: m['full'][skin] for skin in SKINS}
    icons = {skin: m['icons'][skin] for skin in SKINS}
    out = {'heads': {}, 'frames': [[None, None, None] for _ in range(NF)], 'icons': icons}
    for s, skin in enumerate(SKINS):
        hs = []
        for i, h in enumerate(d['heads'][skin]):
            a, W = art[skin][i], h['w']
            fr, (y0, x0) = d['frames'][skin][h['frames'][0]], h['box'][0]
            g = [[-1] * W for _ in range(h['h'])]
            for c, v in enumerate(a):
                y, x = divmod(c, W)
                if not h['lock'][c] and v != fr[y0 + y][x0 + x]:
                    g[y][x] = RAW[skin][v]
            for j, k in enumerate(h['frames']):             # (every frame of the group: the same head pixels)
                f2, (y1, x1) = d['frames'][skin][k], h['box'][j]
                assert y1 == 0 and all(f2[y1 + y][x1 + x] == fr[y0 + y][x0 + x]
                                       for y in range(h['h']) for x in range(W) if not h['lock'][y * W + x]), (skin, i, k)
                assert out['frames'][k][0] in (None, i)
                out['frames'][k][0] = i
                out['frames'][k][1 + s] = x1
            cells = [(y, x) for y in range(h['h']) for x in range(W) if g[y][x] >= 0]
            ry, rx = min(y for y, x in cells), min(x for y, x in cells)
            rh, rw = max(y for y, x in cells) - ry + 1, max(x for y, x in cells) - rx + 1
            hs.append({'ry': ry, 'rx': rx, 'rows': [g[y][rx:rx + rw] for y in range(ry, ry + rh)]})
        out['heads'][skin] = hs
    assert all(None not in f for f in out['frames'])
    return out


def load():
    return json.load(open(JSON))


def head_record(skin, h):
    rows = h['rows']
    rh, rw = len(rows), len(rows[0])
    assert 1 <= rh <= 15 and 1 <= rw <= 15
    cells = [v for r in rows for v in r]
    best = None
    for flag in ((0, 1) if skin == 'light' else (0,)):
        cv = list(CODES[skin])
        if flag:
            cv[2] = FLAG_ALT[skin]
        codes, ex = [], []
        for n, v in enumerate(cells):
            if v < 0:
                codes.append(0)
            elif v in cv:
                codes.append(1 + cv.index(v))
            else:
                codes.append(0)
                ex.append((n, v))
        if best is None or len(ex) < len(best[2]):
            best = (flag, codes, ex)
    flag, codes, ex = best
    assert len(ex) < 128
    b = bytearray([rh << 4 | rw, flag << 7 | len(ex)])
    for i in range(0, len(codes), 4):
        q = codes[i:i + 4] + [0] * (4 - len(codes[i:i + 4]))
        b.append(q[0] << 6 | q[1] << 4 | q[2] << 2 | q[3])
    for n, v in ex:
        b += bytes((n, v))
    return bytes(b)


def blobs(art=None):
    """(main, dark): main = FT + the light heads + the icons (dark, light: 64 bytes each, 4-bit, high nibble first);
    dark = the dark heads. Returns (main, light heads' offset in main, icons' offset in main, dark)."""
    art = art or load()
    ft = bytearray()
    for k, (i, xd, xl) in enumerate(art['frames']):
        hd, hl = art['heads']['dark'][i], art['heads']['light'][i]
        ft += bytes((i, hd['ry'] << 4 | (xd + hd['rx']), hl['ry'] << 4 | (xl + hl['rx'])))
        assert xd + hd['rx'] < 16 and xl + hl['rx'] < 16 and hd['ry'] < 16 and hl['ry'] < 16
    light = b''.join(head_record('light', h) for h in art['heads']['light'])
    dark = b''.join(head_record('dark', h) for h in art['heads']['dark'])
    ic = bytearray()
    for skin in SKINS:
        rows = art['icons'][skin]
        assert len(rows) == 8 and all(len(r) == 16 and max(r) < 16 for r in rows)
        for r in rows:
            ic += bytes(r[x] << 4 | r[x + 1] for x in range(0, 16, 2))
    main = bytes(ft) + light
    return main + bytes(ic), len(ft), len(main), dark


def decode(recs, head, oy, ox, skin, px):
    """Python mirror of bald.c's art_head: px = rows of raw nibbles (16 wide), changed in place."""
    p = 0
    for _ in range(head):
        n = recs[p + 1] & 127
        p += 2 + ((recs[p] >> 4) * (recs[p] & 15) + 3) // 4 + 2 * n
    rh, rw, flag, n = recs[p] >> 4, recs[p] & 15, recs[p + 1] >> 7, recs[p + 1] & 127
    cv = list(CODES[skin])
    if flag:
        cv[2] = FLAG_ALT[skin]
    q = p + 2
    for c in range(rh * rw):
        code = recs[q + c // 4] >> (6 - 2 * (c % 4)) & 3
        y, x = divmod(c, rw)
        if code and oy + y < len(px):
            px[oy + y][ox + x] = cv[code - 1]
    e = q + (rh * rw + 3) // 4
    for i in range(n):
        y, x = divmod(recs[e + 2 * i], rw)
        if oy + y < len(px):
            px[oy + y][ox + x] = recs[e + 2 * i + 1]


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['extract']:
        a = extract(sys.argv[2])
        json.dump(a, open(JSON, 'w'), separators=(',', ':'))
    main, lo, io, dark = blobs()
    print(f'shavedart: FT {lo} B, light heads {io - lo} B, icons {len(main) - io} B (main {len(main)} B), dark {len(dark)} B')
