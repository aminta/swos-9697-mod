"""4.2 keeper gloves (Davide's ok 14/11, World 2026-27 only; David Foster's idea): which pixels of the goalkeeper sprites (GOAL1.DAT,
116 frames, tools/kitmask.py) are HANDS, as a 4th role of the keeper kit masks (white gloves for every keeper).

The hands share the skin entries (5 / 6: orange / yellow in the file's own palette) with the legs and the held ball, so the pixels are
told by what they touch (4-neighbourhood, per connected group of 5 / 6 pixels): a group touching the SHIRT (entry 8) and none of the
shorts (14), the socks (15), the boots (3) or the ball (4) is a hand. Frames where the hands are on the ball or hidden (profile,
lying: 0 pixels) get none: review sheet `python3 tools/gkgloves.py SHEET.png [GOAL1.DAT]` (hands in magenta).
Status: v1 (14/11): 268 hand pixels in 116 frames, 42 frames with none - hand-curated frames to follow (see internal/handoff/gloves.md)."""
import os
import sys

import kitmask

SKIN = (5, 6)


def hands(g):
    """set of (y, x) glove pixels of a keeper frame (palette-index grid, kitmask.grid)"""
    h, w = len(g), len(g[0])
    nb = lambda y, x: [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    seen, out = set(), set()
    for y in range(h):
        for x in range(w):
            if g[y][x] in SKIN and (y, x) not in seen:
                st, c = [(y, x)], []
                seen.add((y, x))
                while st:
                    a, b = st.pop()
                    c.append((a, b))
                    for n in nb(a, b):
                        if 0 <= n[0] < h and 0 <= n[1] < w and g[n[0]][n[1]] in SKIN and n not in seen:
                            seen.add(n)
                            st.append(n)
                adj = {g[n[0]][n[1]] for p in c for n in nb(*p) if 0 <= n[0] < h and 0 <= n[1] < w} - set(SKIN)
                if 8 in adj and not adj & {14, 15, 3, 4}:
                    out |= set(c)
    return out or curated(g)


def _groups(g):
    h, w = len(g), len(g[0])
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] in SKIN and (y, x) not in seen:
                st, c = [(y, x)], []
                seen.add((y, x))
                while st:
                    a, b = st.pop()
                    c.append((a, b))
                    for n in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= n[0] < h and 0 <= n[1] < w and g[n[0]][n[1]] in SKIN and n not in seen:
                            seen.add(n)
                            st.append(n)
                out.append(c)
    return out


def _adj(g, c):
    h, w = len(g), len(g[0])
    return {g[n[0]][n[1]] for a, b in c for n in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1))
            if 0 <= n[0] < h and 0 <= n[1] < w} - set(SKIN)


def curated(g):
    """4.2 hand curation (Davide's option 1, 14/11; reviewed frame by frame on enlarged sheets): for a frame the first rule finds
    nothing in (profile frames with the hands raised in front of the chest, lying / diving frames with the arms forward):
    (1) skin groups wholly above the shorts' first row (the hands raised); else (2) skin groups touching neither the shorts nor
    the socks (the head end of a lying keeper); at most 7 pixels (HC's 3 bits), the ones farthest from the shirt's centre. Frames
    whose arms are hidden (lying, 44 / 51 / 102 / 109 of the 116) stay without."""
    h = len(g)
    shorts = [y for y in range(h) if any(v == 14 for v in g[y])]
    top = min(shorts) if shorts else h
    res = set()
    for c in _groups(g):
        if all(y < top for y, _ in c):
            res |= set(c)
    if not res:
        for c in _groups(g):
            if not _adj(g, c) & {14, 15}:
                res |= set(c)
    if len(res) > 7:
        sh = [(y, x) for y, r in enumerate(g) for x, v in enumerate(r) if v == 8]
        cy, cx = (sum(y for y, _ in sh) / len(sh), sum(x for _, x in sh) / len(sh)) if sh else (h / 2, 8)
        res = set(sorted(res, key=lambda p: -((p[0] - cy) ** 2 + (p[1] - cx) ** 2))[:7])
    return res


def masks(path):
    """{frame: set of (y, x)} for the 116 frames of GOAL1.DAT"""
    return {i: hands(kitmask.grid(s)) for i, s in enumerate(kitmask.sprites(path))}


def sheet(path, png, scale=6):
    from PIL import Image, ImageDraw
    sp = kitmask.sprites(path)
    col = {0: (255, 255, 255), 1: (120, 0, 0), 2: (60, 60, 60), 3: (0, 0, 0), 4: (130, 80, 20), 5: (255, 140, 0), 6: (255, 220, 0),
           8: (150, 150, 150), 9: (255, 200, 160), 12: (220, 150, 110), 13: (120, 70, 40), 14: (30, 60, 220), 15: (30, 170, 60)}
    cols = 12
    rows = (len(sp) + cols - 1) // cols
    cw, ch = 16 * scale + 8, 24 * scale + 14
    im = Image.new('RGB', (cols * cw, rows * ch), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for i, s in enumerate(sp):
        g = kitmask.grid(s)
        hp = hands(g)
        ox, oy = (i % cols) * cw + 4, (i // cols) * ch + 12
        d.text((ox, oy - 11), f'{i}:{len(hp)}', fill=(255, 0, 0))
        for y, r in enumerate(g):
            for x, v in enumerate(r):
                if v:
                    d.rectangle([ox + x * scale, oy + y * scale, ox + x * scale + scale - 1, oy + y * scale + scale - 1],
                                fill=(255, 0, 255) if (y, x) in hp else col.get(v, (255, 0, 255)))
    im.save(png)


if __name__ == '__main__':
    sheet(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'REL412c', 'SWOS', 'GOAL1.DAT'), sys.argv[1])
