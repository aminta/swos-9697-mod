"""4.2 kits (Davide 12/11, David's FB idea): which pixels of the goalkeeper and referee sprites are kit, as bit masks the
exe keeps (kits.py); internal/handoff/kits-keeper-referee.md.

The sprite files (GOAL1.DAT, BENCH.DAT / BENC2.DAT, TEAM1.DAT: byte-identical on the CD and GOG and under SWOS++) hold
each sprite as a 24-byte SpriteGraphics header + Amiga planar pixels (4 big-endian words per 16 pixels); ChainFont(227)
makes them chunky (4 bit) when a match starts.
- Keepers (GOAL1.DAT, 116 frames, loaded twice: sprites 947.. and 1063..): the shirt is palette entry 8, the entry of
  every player's shadow; shorts / socks are the team placeholders 14 / 15. The shirt pixels = the 8-pixels that are
  not shadow:
  1. a frame with an outfield twin (TEAM1.DAT, the same silhouette): the twin's shirt pixels (10 / 11);
  2. else the 8-components that do not reach the frame's lowest 8-rows (the shadow under the feet);
  3. the lying / diving frames, whose shirt touches the shadow (2. can't split them): the 8-pixels above the first
     row that holds only 8s (the shadow under the body).
- Referee (BENCH.DAT 1273..1283, every kit pixel entry 3 like his hair and boots): shirt / shorts / socks from the
  outfield twin's 10-11 / 14 / 15; the four card frames (1280..1283, no twin) from 1279 (his side view) shifted onto
  the body, the raised or held arm = sleeve (shirt).
Masks: per frame, per row a 16-bit word (bit 15 = pixel 0), every frame 1 quad wide (16 px)."""
import os
import struct

KEEPER_N = 116
REF_FIRST, REF_N, BENCH_FIRST = 1273, 11, 1179
ROLES = ('shirt', 'shorts', 'socks')


def sprites(path):
    """[(w, nlines, wquads, planar bytes)] in file order"""
    d = open(path, 'rb').read()
    o, out = 0, []
    while o + 24 <= len(d):
        w, nl, wq = struct.unpack_from('<hhh', d, o + 10)
        n = nl * wq * 8
        if n <= 0 or o + 24 + n > len(d):
            break
        out.append((w, nl, wq, d[o + 24:o + 24 + n]))
        o += 24 + n
    assert o == len(d), (path, o, len(d))
    return out


def grid(spr):
    """rows of palette indices (planar -> chunky, as ChainFont)"""
    w, nl, wq, b = spr
    rows = []
    for y in range(nl):
        line = []
        for q in range(wq):
            base = (y * wq + q) * 8
            pl = [int.from_bytes(b[base + 2 * k:base + 2 * k + 2], 'big') for k in range(4)]
            line += [sum(((pl[k] >> (15 - x)) & 1) << k for k in range(4)) for x in range(16)]
        rows.append(line)
    return rows


def sil(g):
    return tuple(tuple(1 if v else 0 for v in r) for r in g)


def _twins(team):
    idx = {}
    for i, g in enumerate(team):
        idx.setdefault(sil(g), i)
    return idx


def _comps(g, val):
    h, w = len(g), len(g[0])
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] == val and (y, x) not in seen:
                st, c = [(y, x)], []
                seen.add((y, x))
                while st:
                    a, b = st.pop()
                    c.append((a, b))
                    for n in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= n[0] < h and 0 <= n[1] < w and g[n[0]][n[1]] == val and n not in seen:
                            seen.add(n)
                            st.append(n)
                out.append(c)
    return out


def keeper_shirt(g, twin=None):
    """(set of (y, x) shirt pixels, method)"""
    if twin is not None:
        return {(y, x) for y, r in enumerate(twin) for x, v in enumerate(r) if v in (10, 11) and g[y][x] == 8}, 'twin'
    cs = _comps(g, 8)
    if not cs:
        return set(), 'none'
    low = max(y for c in cs for y, _ in c)
    shadow = [c for c in cs if max(y for y, _ in c) >= low - 1]
    if all(min(y for y, _ in c) >= low - 4 for c in shadow):
        return {p for c in cs if c not in shadow for p in c}, 'comp'
    # lying / diving: the shadow under the body starts at the first row of 8s only (below a body pixel)
    body = [y for y, r in enumerate(g) if any(v not in (0, 8) for v in r)]
    pure = next(y for y, r in enumerate(g) if y > body[0] and any(r) and all(v in (0, 8) for v in r))
    return {(y, x) for y in range(pure) for x, v in enumerate(g[y]) if v == 8}, 'lying'


def _shift_from(g, refroles):
    """roles for a card frame from 1279's: the (dy, dx) that lays ref's body best onto g, then the arm = shirt"""
    best = None
    for dy in range(-2, 3):
        for dx in range(-3, 4):
            hit = sum(1 for (y, x) in refroles if 0 <= y + dy < len(g) and 0 <= x + dx < len(g[0])
                      and g[y + dy][x + dx] == 3)
            if best is None or hit > best[0]:
                best = (hit, dy, dx)
    _, dy, dx = best
    out = {}
    for (y, x), role in refroles.items():
        if 0 <= y + dy < len(g) and 0 <= x + dx < len(g[0]) and g[y + dy][x + dx] == 3:
            out[(y + dy, x + dx)] = role
    shirt_y = [y for (y, _), r in out.items() if r == 'shirt']
    for y, r in enumerate(g):                          # (black pixels left in the shirt rows, below the hair = arm)
        for x, v in enumerate(r):
            if v == 3 and (y, x) not in out and min(shirt_y) <= y <= max(shirt_y) + 1:
                out[(y, x)] = 'shirt'
    return out


def referee_roles(bench, team):
    """{sprite: {(y, x): 'shirt' | 'shorts' | 'socks'}} for 1273..1283"""
    tw = _twins(team)
    out = {}
    for k in range(REF_N):
        g = bench[REF_FIRST - BENCH_FIRST + k]
        t = tw.get(sil(g))
        if t is None:
            continue
        r = {}
        for y, row in enumerate(team[t]):
            for x, v in enumerate(row):
                role = 'shirt' if v in (10, 11) else 'shorts' if v == 14 else 'socks' if v == 15 else None
                if role and g[y][x] == 3:
                    r[(y, x)] = role
        out[REF_FIRST + k] = r
    side = out[1279]
    for k in range(REF_N):
        if REF_FIRST + k not in out:
            out[REF_FIRST + k] = _shift_from(bench[REF_FIRST - BENCH_FIRST + k], side)
    return out


def words(pixels, nl):
    """per row a 16-bit mask, bit 15 = pixel 0"""
    m = [0] * nl
    for y, x in pixels:
        m[y] |= 0x8000 >> x
    return m


def build(game_dir):
    """{'keeper': [(nl, [words]) x 116], 'keeper_how': [...], 'ref': {sprite: {role: (nl, [words])}}}"""
    team = [grid(s) for s in sprites(os.path.join(game_dir, 'TEAM1.DAT'))]
    goal = [grid(s) for s in sprites(os.path.join(game_dir, 'GOAL1.DAT'))]
    bench = [grid(s) for s in sprites(os.path.join(game_dir, 'BENCH.DAT'))]
    assert len(goal) == KEEPER_N and len(bench) >= REF_FIRST - BENCH_FIRST + REF_N
    assert all(len(g[0]) == 16 for g in goal + bench[REF_FIRST - BENCH_FIRST:REF_FIRST - BENCH_FIRST + REF_N])
    tw = _twins(team)
    import gkgloves                                          # (4.2 gloves: the hands, pixel lists, not row masks: 268 pixels in 116 frames)
    keeper, how, hand = [], [], []
    for i, g in enumerate(goal):
        hand.append([] if i % (KEEPER_N // 2) in gkgloves.NO_GLOVES else sorted(gkgloves.hands(g)))
        t = tw.get(sil(g))
        px, m = keeper_shirt(g, team[t] if t is not None else None)
        keeper.append((len(g), words(px, len(g))))
        how.append(m)
    ref = {}
    for spr, roles in referee_roles(bench, team).items():
        nl = len(bench[spr - BENCH_FIRST])
        ref[spr] = {r: (nl, words([p for p, v in roles.items() if v == r], nl)) for r in ROLES}
    return {'keeper': keeper, 'keeper_how': how, 'ref': ref, 'hands': hand}


def sheet(game_dir, out, scale=5):
    """review sheet: every keeper frame (shirt magenta) and every referee frame (shirt yellow, shorts / socks blue)"""
    from PIL import Image
    m = build(game_dir)
    pal = open(os.path.join(game_dir, 'PAL.256'), 'rb').read()[-768:]
    P = [tuple(min(255, c * 4) for c in pal[i * 3:i * 3 + 3]) for i in range(16)]
    goal = [grid(s) for s in sprites(os.path.join(game_dir, 'GOAL1.DAT'))]
    bench = [grid(s) for s in sprites(os.path.join(game_dir, 'BENCH.DAT'))]
    frames = [(g, {(y, x): (255, 0, 255) for y, w in enumerate(m['keeper'][i][1]) for x in range(16) if w & (0x8000 >> x)})
              for i, g in enumerate(goal)]
    col = {'shirt': (255, 255, 0), 'shorts': (0, 0, 255), 'socks': (0, 160, 255)}
    for spr, roles in sorted(m['ref'].items()):
        frames.append((bench[spr - BENCH_FIRST], {(y, x): col[r] for r, (nl, ws) in roles.items()
                                                  for y, w in enumerate(ws) for x in range(16) if w & (0x8000 >> x)}))
    cols, W, H = 16, 20, 20
    im = Image.new('RGB', (cols * W * scale, ((len(frames) + cols - 1) // cols) * H * scale), (60, 150, 40))
    for i, (g, over) in enumerate(frames):
        for y, r in enumerate(g):
            for x, v in enumerate(r):
                if v:
                    c = over.get((y, x), P[v])
                    x0, y0 = ((i % cols) * W + x) * scale, ((i // cols) * H + y) * scale
                    im.paste(c, (x0, y0, x0 + scale, y0 + scale))
    im.save(out)
    return m


if __name__ == '__main__':
    import sys
    m = sheet(sys.argv[1], sys.argv[2])
    from collections import Counter
    print('keeper', Counter(m['keeper_how']), 'ref', sorted(m['ref']))
