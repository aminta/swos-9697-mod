"""Simulated results of a league-phase world (World 2026-27): real draw rate and goals.

The game's result simulation (CalculateViewResult, every match not played with the engine: league days, cups, the
season-end simulations) compares the two clubs' ratings (each with a random factor): D3 = the difference (+2 at home,
clamped to +-23); dseg_1728FF[|D3|] gives the winning margin of the stronger side (4 slots: 0 = a draw), then the
loser's goals from per-margin distributions. Row 0 is [0, 0, 0, 0], so equal clubs always draw, and ~45 % of CPU
matches end level (real leagues: ~26 %), with 2.0-2.3 goals per match (real: ~2.6-2.8).

In a career in a league-phase world (careerworld w_lpw, GAMETYPE 4) sd_site (at cseg_2BE12, right after the margin
pick) draws the whole score from our own table instead: per |D3| = d a 128-slot table of (stronger, weaker) goals from
two Poisson laws with the total G(d) and a ratio set so that P(stronger wins) - P(weaker wins) equals the original
row's (its non-zero slots / 4): the strength split of the points stays the game's, draws and goals become real. The
margin (stronger - weaker, may be negative) goes into D1, the weaker side's goals into D2, then cseg_2BFBF as the game
(D1 += D2, sides swapped when D3 < 0). Other worlds, normal careers and every other mode: the game's code.
"""
import math
import re
import struct

SLOTS = 128
ROWS = 24
ORIG_ADV = [0, .25, .5, .5, .5, .75, .75, .75, .75, .75] + [1] * 14     # dseg_1728FF rows 0..23: non-zero slots / 4
import os
G0 = float(os.environ.get('SIMDRAW_G0', 2.55))                         # goals per match: G0 + G1 * d (at most GMAX)
G1 = float(os.environ.get('SIMDRAW_G1', 0.06))
GMAX = 4.2
K = float(os.environ.get('SIMDRAW_K', 1.0))                            # the original advantage x K (calibration)
D0 = float(os.environ.get('SIMDRAW_D0', 0.30))                         # draws at d = 0, then - D1 per step (>= DMIN)
D1 = float(os.environ.get('SIMDRAW_D1', 0.015))
DMIN = 0.08
ADV_MAX = 0.93                                                         # (an advantage of 1 is not a Poisson pair)
GOALS_MAX = 9


def _pois(lam, k):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _pair(ls, lw):
    """{(gs, gw): p} for two independent Poisson laws (goals up to GOALS_MAX)."""
    return {(a, b): _pois(ls, a) * _pois(lw, b) for a in range(GOALS_MAX + 1) for b in range(GOALS_MAX + 1)}


def _adv(ls, lw):
    pr = _pair(ls, lw)
    return sum(p for (a, b), p in pr.items() if a > b) - sum(p for (a, b), p in pr.items() if a < b)


def row(d, g0=G0, g1=G1):
    """(lambda_stronger, lambda_weaker, {(gs, gw): p}) of row d."""
    g = min(GMAX, g0 + g1 * d)
    want = min(ADV_MAX, K * ORIG_ADV[d])
    lo, hi = 0.5, 0.999                                               # the stronger side's share of the goals
    if want <= 0:
        share = 0.5
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            if _adv(g * mid, g * (1 - mid)) < want:
                lo = mid
            else:
                hi = mid
        share = (lo + hi) / 2
    ls, lw = g * share, g * (1 - share)
    pr = _pair(ls, lw)
    # masses: draws D(d), stronger wins W, weaker wins L with W - L = the advantage (the game's points split); the
    # scores inside each class keep the Poisson shape (more draws than independent goals give, as real football)
    dr = max(DMIN, D0 - D1 * d)
    adv = min(K * ORIG_ADV[d], 1 - dr)
    mass = {'w': (1 - dr + adv) / 2, 'd': dr, 'l': (1 - dr - adv) / 2}
    cls = lambda a, b: 'w' if a > b else 'd' if a == b else 'l'
    tot = {c: sum(p for (a, b), p in pr.items() if cls(a, b) == c) for c in 'wdl'}
    return ls, lw, {(a, b): p / tot[cls(a, b)] * mass[cls(a, b)] for (a, b), p in pr.items()}


def table(g0=G0, g1=G1):
    """ROWS x SLOTS bytes (stronger goals << 4 | weaker goals), largest-remainder rounding of each row."""
    out = bytearray()
    for d in range(ROWS):
        _, _, pr = row(d, g0, g1)
        items = sorted(pr.items(), key=lambda kv: -kv[1])
        tot = sum(pr.values())
        raw = [(k, p / tot * SLOTS) for k, p in items]
        n = {k: int(x) for k, x in raw}
        left = SLOTS - sum(n.values())
        for k, x in sorted(raw, key=lambda kx: -(kx[1] - int(kx[1])))[:left]:
            n[k] += 1
        slots = [a << 4 | b for (a, b), c in sorted(n.items()) for _ in range(c)]
        assert len(slots) == SLOTS
        out += bytes(slots)
    return bytes(out)


def stats(tab):
    """Per row: draw share, stronger-win share, weaker-win share, mean goals (of the table as built)."""
    out = []
    for d in range(ROWS):
        s = tab[d * SLOTS:(d + 1) * SLOTS]
        a = [x >> 4 for x in s]
        b = [x & 15 for x in s]
        out.append((sum(x == y for x, y in zip(a, b)) / SLOTS, sum(x > y for x, y in zip(a, b)) / SLOTS,
                    sum(x < y for x, y in zip(a, b)) / SLOTS, (sum(a) + sum(b)) / SLOTS))
    return out


ASM = '''
sd_site:                                ; jmp from cseg_2BE12 (mov al, [D1]; cbw; mov [D1], ax: 13 bytes)
    mov al, [D1R]
    cbw
    mov [D1R], ax
    cmp word [GAMETYPE], 4              ; a career (the world byte is stale outside one)
    jne .game
    call W_LPW                          ; ZF = 1: a league-phase world (World 2026-27)
    jne .game
    pushad
    movsx eax, word [D3R]               ; |strength difference| = the row
    test eax, eax
    jns .p
    neg eax
.p:
    cmp eax, ROWS - 1
    jbe .r
    mov eax, ROWS - 1
.r:
    shl eax, 7
    push eax
    call RAND2                          ; the game's random byte in D0
    pop eax
    movzx ecx, byte [D0R]
    shr ecx, 1                          ; 0..127
    movzx eax, byte [SD_TAB + eax + ecx]
    mov ecx, eax
    and ecx, 15                         ; the weaker side's goals
    shr eax, 4                          ; the stronger side's goals
    sub eax, ecx                        ; margin (negative: the weaker side wins)
    mov [D1R], ax
    mov [D2R], cx
    popad
    jmp C2BFBF                          ; D1 += D2; swap when D3 < 0; the game's bookkeeping
.game:
    jmp SITE_NEXT
'''


def _site(p):
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D1 = struct.pack('<I', r['D7'] - 24)
    D0 = struct.pack('<I', r['D7'] - 28)
    pat = (rb'\xa0' + re.escape(D1) + rb'\x66\x98\x66\xa3' + re.escape(D1) + rb'\xc7\x05' + re.escape(struct.pack('<I', r['A0']))
           + rb'.{4}\x66\xa1' + re.escape(D1) + rb'\x66\xa3' + re.escape(D0) + rb'\x66\xc1\x25' + re.escape(D0) + rb'\x02')
    # (cseg_2BE12: then mov [A0], offset dseg_172985; mov ax, [D1]; mov [D0], ax; shl word [D0], 2)
    m = [x.start() for x in re.finditer(pat, d1, re.S)]
    assert len(m) == 1, [hex(x) for x in m]
    site = m[0]
    # cseg_2BFBF: mov ax, [D2]; add [D1], ax; mov ax, [D3]; or ax, ax; jns
    D2, D3 = struct.pack('<I', r['D7'] - 20), struct.pack('<I', r['D7'] - 16)
    k = d1.find(b'\x66\xa1' + D2 + b'\x66\x01\x05' + D1 + b'\x66\xa1' + D3 + b'\x66\x0b\xc0\x79', site)
    assert 0 < k - site < 0x400, hex(k - site)
    return site, k, r


def patch(p, at, area, gametype, w_lpw, rand2):
    """sd_site at obj1:at (its table in obj2 via area); gametype = careerworld sites' (obj, off), w_lpw = obj1 label,
    rand2 = Rand2's obj1 offset. Returns the end."""
    import nasmcave
    site, c2bfbf, r = _site(p)
    tab = table()
    sym = {'D0R': (2, r['D7'] - 28), 'D1R': (2, r['D7'] - 24), 'D2R': (2, r['D7'] - 20), 'D3R': (2, r['D7'] - 16),
           'GAMETYPE': gametype, 'W_LPW': (1, w_lpw), 'RAND2': (1, rand2), 'SD_TAB': (2, area.add(tab)),
           'C2BFBF': (1, c2bfbf), 'SITE_NEXT': (1, site + 13), 'ROWS': (0, ROWS)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.remove(1, site + 1)                                   # the two [D1] operands of the overwritten 13 bytes
    p.remove(1, site + 9)
    p.put(1, site, b'\xe9' + struct.pack('<i', lab['sd_site'] - (site + 5)) + b'\x90' * 8)
    st = stats(tab)
    print(f'exe: simulated results of a league-phase world: cseg_2BE12 obj1+{site:#x} -> sd_site obj1+{at:#x}; '
          f'row 0 draws {st[0][0]:.2f} goals {st[0][3]:.2f}, row 5 draws {st[5][0]:.2f} goals {st[5][3]:.2f}')
    return (at + len(code) + 3) & ~3


if __name__ == '__main__':
    t = table()
    for d, (dr, sw, ww, g) in enumerate(stats(t)):
        ls, lw, _ = row(d)
        print(f'd {d:2}: draws {dr:.2f} stronger {sw:.2f} weaker {ww:.2f} goals {g:.2f} (lambda {ls:.2f} / {lw:.2f})')
