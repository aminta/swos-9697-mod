"""4.1 RC3 (Enzo 09/11, Davide via Regia): money in euros - display only.

The game has one currency glyph: character 0x9C (Int2Pounds' `pound db 9Ch`, the offer / price / budget texts of all
four languages), drawn by both menu fonts' conversion tables (smallCharsTable / bigCharsTable, identical in the four
exes) as sprite 46 (small, 6 x 6) and 46 + 57 = 103 (big, 8 x 8). Those sprites are CHARSET.DAT's (the first 227
spritesIndex entries are offsets into it: SPRITE.DAT; each a SpriteGraphics header + 4 bit-planes of 16 pixels a
line, colour 2 the letter, 8 its shadow one pixel down-right). Here:
- CHARSEU.DAT (gen): the user's CHARSET.DAT with sprites 46 / 103 redrawn as the euro sign, same size, same colours;
  written beside the exe as dugout's PITCHA-E (the patcher ships it as a delta from the user's own CHARSET.DAT);
- the exe (patch): its one 'charset.dat' name (obj2, read by the three loads: the game's start, back from a match,
  after the highlights) -> 'charseu.dat'. The game's CHARSET.DAT stays original: an older exe still finds it.
Amounts are unchanged (the World 2026-27's prices come from TM values, already in euros). Saves: no change.
Left alone: the IT exe's amount list '\xa325m*' .. '\xa315M*' (the EN a25k.. strings, there with 9Ch) writes A3h, a
character the fonts do not have (the crossed box), but nothing references it (no XREF in ref/swos.asm): never drawn.
"""
import os
import struct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NAME = 'CHARSEU.DAT'
SPRITES = {46: ('.2222',                 # small font: 5 x 5 + the shadow (6 x 6, as the pound sign)
                '222..',
                '2....',
                '222..',
                '.2222'),
           103: ('..22222',              # big font: 7 x 7 + the shadow (8 x 8), two-pixel strokes as its letters
                 '.22....',
                 '222222.',
                 '22.....',
                 '222222.',
                 '.22....',
                 '..22222')}


def glyph(rows, w, nl):
    """[nl][w] colours: the letter (2) and its shadow (8) one pixel down-right where the letter is not."""
    px = [[0] * w for _ in range(nl)]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '2':
                px[y][x] = 2
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '2' and y + 1 < nl and x + 1 < w and px[y + 1][x + 1] != 2:
                px[y + 1][x + 1] = 8
    return px


def sprite(cs, sp, i):
    """(pixel data offset, width, lines, quads a line) of CHARSET sprite i."""
    h = struct.unpack_from('<I', sp, 4 * i)[0]
    pd = struct.unpack_from('<I', cs, h)[0]
    w, nl, wq = struct.unpack_from('<hhh', cs, h + 10)
    return pd, w, nl, wq


def planes(px, wq):
    """A sprite's lines as the game stores them: per line and quad, 4 big-endian 16-bit planes."""
    out = bytearray()
    for row in px:
        for q in range(wq):
            for p in range(4):
                v = 0
                for x in range(16):
                    c = row[16 * q + x] if 16 * q + x < len(row) else 0
                    v |= ((c >> p) & 1) << (15 - x)
                out += struct.pack('>H', v)
    return bytes(out)


def build(cs, sp):
    """CHARSET.DAT bytes with the euro sign in sprites 46 / 103."""
    cs = bytearray(cs)
    for i, rows in SPRITES.items():
        pd, w, nl, wq = sprite(cs, sp, i)
        assert (w, nl, wq) == ((6, 6, 1) if i == 46 else (8, 8, 1)), ('the pound sprite moved', i, w, nl, wq)
        cs[pd:pd + nl * wq * 8] = planes(glyph(rows, w, nl), wq)
    return bytes(cs)


def letter(cs, sp, i):
    """Sprite i's letter pixels (colour 2) as rows of bools, the shadow column / row left out (harness: euro_money)."""
    pd, w, nl, wq = sprite(cs, sp, i)
    rows = []
    for y in range(nl - 1):
        r = []
        for x in range(w - 1):
            c = 0
            for p in range(4):
                o = pd + (y * wq + x // 16) * 8 + 2 * p
                c |= ((struct.unpack_from('>H', cs, o)[0] >> (15 - x % 16)) & 1) << p
            r.append(c == 2)
        rows.append(r)
    return rows


def gen(dst_dir, src=None):
    """Writes CHARSEU.DAT into dst_dir from src's (default orig/) CHARSET.DAT + SPRITE.DAT; returns the log line."""
    src = src or os.path.join(ROOT, 'orig')
    cs, sp = (open(os.path.join(src, f), 'rb').read() for f in ('CHARSET.DAT', 'SPRITE.DAT'))
    out = build(cs, sp)
    open(os.path.join(dst_dir, NAME), 'wb').write(out)
    return f'{NAME}: the currency glyph (sprites 46 / 103) as the euro sign, {sum(a != b for a, b in zip(cs, out))} bytes'


def patch(p):
    """The exe's 'charset.dat' -> 'charseu.dat' (obj2, one string)."""
    d = p.le.obj_bytes(2)
    o = d.find(b'charset.dat\0')
    assert o >= 0 and d.find(b'charset.dat\0', o + 1) < 0, 'charset.dat: not one string in obj2'
    p.put(2, o, b'charseu.dat\0')
    return o


if __name__ == '__main__':
    import sys
    print(gen(sys.argv[1]))
