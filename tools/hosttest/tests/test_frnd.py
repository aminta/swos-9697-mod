"""4.2 preseason friendlies (a), the engine's pure parts (tools/frnd.c, Motore): fr_turns (the Turns rule of
internal/handoff/friendlies-a-interface.md on synthetic career calendars: the plain window, Italy 1996-97's Coppa Italia
at F-8, San Marino's cups, a UEFA Q1 club's odd-week legs, a slot-3 entry on a turn, an early league with turns < 0),
fr_fee (Mercato's table, the cap, the 16-rounding, a u64 product) and fr_result (played count, W / D / L, the other
bits kept). Host only: frnd.c built natively (clang -shared, ctypes) at -O0 and -Oz, both checked."""
import ctypes
import os
import struct
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(TOOLS, 'frnd.c')
STRONGER, SIMILAR, WEAKER, FAR_UP, FAR_DOWN = 0, 1, 2, 3, 4
_LIBS = {}


def libs():
    if not _LIBS:
        d = tempfile.mkdtemp(prefix='frnd')
        for opt in ('-O0', '-Oz'):
            so = os.path.join(d, f'frnd{opt}.dylib')
            subprocess.run(['clang', '-shared', opt, '-Wall', '-Werror', '-I', TOOLS, '-o', so, SRC], check=True)
            L = ctypes.CDLL(so)
            L.fr_turns.restype = ctypes.c_uint32
            L.fr_fee.restype = ctypes.c_uint32
            _LIBS[opt] = L
    return _LIBS


def cal(entries):
    """a career calendar of (slot, week, matches) entries, 8 B each; returns (the buffer, the pointer to cal)"""
    body = b''.join(struct.pack('<BBHHBB', s, w, 8, 0, m, 0) for s, w, m in entries) + struct.pack('<BBH', 0, 0, 0)
    raw = struct.pack('<HH', len(entries), 0) + body
    buf = ctypes.create_string_buffer(raw, len(raw) + 8)
    return buf, ctypes.cast(ctypes.addressof(buf) + 4, ctypes.c_void_p)


def turns(L, entries):
    buf, p = cal(entries)
    out = (ctypes.c_uint8 * 4)()
    n = L.fr_turns(p, out)
    return n, list(out)


def league(f, n=4, step=4):
    return [(0, f + step * i, 6) for i in range(n)]


def test_frnd_turns():
    X = 0xFF
    cases = (
        ('plain, F 56', league(56), (4, [48, 50, 52, 54])),
        ('F odd 57 -> E 56', league(57), (4, [48, 50, 52, 54])),
        ('a slot-0 entry with 0 matches first is not F', [(0, 40, 0)] + league(56), (4, [48, 50, 52, 54])),
        ('Italy 1996-97: Coppa Italia (slot 1) at 56 = F-8, F 64', [(1, 56, 4)] + league(64), (4, [48, 50, 52, 54])),
        ('San Marino: cups at 64, F 72', [(1, 64, 4), (2, 64, 2)] + league(72), (4, [56, 58, 60, 62])),
        ('UEFA Q1: slot-3 legs on odd weeks 49..55 do not block', [(3, 49, 1), (3, 51, 1), (3, 53, 1), (3, 55, 1)] +
         league(56), (4, [48, 50, 52, 54])),
        ('slot 3 on a turn (52) blocks', [(3, 52, 1)] + league(56), (4, [44, 46, 48, 50])),
        ('a chain: cup at 50 blocks, then 44 blocks again', [(1, 44, 2), (1, 50, 2)] + league(56), (4, [36, 38, 40, 42])),
        ('early league F 4: turns < 0 dropped', league(4), (2, [X, X, 0, 2])),
        ('no league day', [(1, 56, 2)], (0, [X, X, X, X])),
    )
    for opt, L in libs().items():
        for name, ent, want in cases:
            got = turns(L, ent)
            if got != (want[0], list(want[1])):
                return False, f'{opt} {name}: {got}, want {want}'
    return True, f'{len(cases)} calendars x -O0 / -Oz: plain F-8..F-2, odd F, Coppa Italia 56 -> 48-54, San Marino ' \
                 '56-62, UEFA Q1 odd legs kept between, slot 3 on a turn moves E, chained blocks, turns < 0 dropped'


def test_frnd_fee():
    pct = {STRONGER: (100, 40), SIMILAR: (50, 20), WEAKER: (30, 10), FAR_UP: (120, 50), FAR_DOWN: (20, 5)}
    n = 0
    for opt, L in libs().items():
        for g in (0, 1, 15, 16, 999, 123457, 873813, 1048560, 5000000, 0xFFFFFFFF,
                  # the exact clamp (no u64 divide): edges of 0x1400000, the 5% cap point, 32-bit overflow of g * 120
                  20971199, 20971200, 20971201, 0x13FFFFF, 0x1400000, 0x1400001, 35791394, 35791395, 0x80000000):
            for b, (h, a) in pct.items():
                for home, p in ((1, h), (0, a)):
                    want = min(g * p // 100, 1048560) & ~15
                    got = L.fr_fee(g, b, home)
                    n += 1
                    if got != want:
                        return False, f'{opt} fr_fee(G {g}, band {b}, home {home}) = {got}, want {want}'
        if L.fr_fee(100000, 5, 1) or L.fr_fee(100000, 0xFF, 0):
            return False, f'{opt}: a band > 4 pays'
    return True, f'{n} cases: Mercato\'s table (120/50, 100/40, 50/20, 30/10, 20/5), floor, cap 1 048 560, ' \
                 '16-rounding, no 32-bit overflow (G 0xFFFFFFFF, clamp edges 0x1400000 / 5% cap / g*120 wrap), band > 4 = 0'


def test_frnd_result():
    for opt, L in libs().items():
        st = (ctypes.c_uint8 * 12)()
        st[0], st[1] = 30, 0xF8                     # (season; spare bits 3-7 set: kept)
        fl0 = 0b1110_0000_0000_0101                 # (home flags 0101, NATIVE, level 3)
        st[10], st[11] = fl0 & 0xFF, fl0 >> 8
        for k, (gf, ga) in enumerate(((2, 0), (1, 1), (0, 3), (4, 4))):
            L.fr_result(st, k, gf, ga)
            if st[1] != (0xF8 | (k + 1)):
                return False, f'{opt}: played byte {st[1]:#x} after friendly {k + 1}'
        fl = st[10] | st[11] << 8
        w, d, l = (fl >> 4) & 7, (fl >> 7) & 7, (fl >> 10) & 7
        if (w, d, l) != (1, 2, 1) or fl & 0xE00F != fl0 & 0xE00F or st[0] != 30:
            return False, f'{opt}: W/D/L {(w, d, l)}, flags {fl:#06x} (want 1/2/1, bits 0-3 13-15 of {fl0:#06x})'
        for _ in range(9):                          # (a count saturates at 7: no carry into the next field)
            L.fr_result(st, 3, 1, 0)
        fl = st[10] | st[11] << 8
        if ((fl >> 4) & 7, (fl >> 7) & 7) != (7, 2):
            return False, f'{opt}: W saturation {fl:#06x}'
    return True, 'played count k + 1, W/D/L 1/2/1 after 2-0, 1-1, 0-3, 4-4; home flags, NATIVE, level, season, spare ' \
                 'bits kept; a count saturates at 7 without a carry'
