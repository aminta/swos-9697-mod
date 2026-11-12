"""4.2 opsign (Davide 12/11): the chairman's season-end opinion's ratio signed (tools/opsign.py: `xor edx, edx` ->
`cdq; nop` before its `idiv ebx`). The original game's own code, run in the emulator from
ShowChairmanOpinionAboutTheSeason's entry (obj1 2BFC2h, IT) to cseg_3C2DF (2C133h: the place terms done, before the
career competitions' finals), twice per case: with the original bytes (33 D2) and with the build's (99 90).

Fixture opsign_mlt: a World 2026-27 career at FLORIANA (Malta, 12 clubs, the league's most expensive: expected place 0)
on a HOSTTEST_SYMS=1 build of 42-opsign, snapshot at the routine's entry (HT_SNAP_LABELS=obj1+2bfc2) at the season end.

Cases, forced: the club's place (competitionFileBuffer +6Dh, the table's order) written, the expected place forced
at GetMoreExpensiveTeamsCount's end (its D3, which the game copies to D2: the emulator has no team loader, so the
clubs' own prices can't decide it): below expected (2nd / 3rd / 6th / 12th for 1st; 3rd for 2nd ...), at it, above it.
Checks: the verdict (D7) before = the original formula with its 32-bit unsigned dividend, after = the signed one;
before = after for every club at or above its expected place; a club below it: after = the signed rule."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import emu  # noqa: E402
from emu import Machine  # noqa: E402

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures', 'opsign_mlt')
START, STOP, SITE = 0x2bfc2, 0x2c133, 0x2c051           # obj1 (ITALIAN.EXE; opsign.site checks the bytes)
D1, D2, D3, D7, SEL, CFB = 0x315bb, 0x315bf, 0x315c3, 0x315d3, 0x16e20, 0x1f640   # obj2
MEC_END = 0x81211                       # obj1: GetMoreExpensiveTeamsCount's `mov ax, [D3]; mov [D2], ax ...; ret`
CASES = [(0, 0), (1, 0), (2, 0), (5, 0), (11, 0),        # (place, expected), 0-based: at / below expected
         (2, 1), (6, 3), (9, 6),
         (0, 5), (3, 5), (5, 5), (4, 9), (8, 11), (11, 11)]   # at / above expected: unchanged
MSG = ['COMPLIMENTI', 'UNA BUONA', 'ALTERNA', 'NON BUONA', 'DELUDENTE']


def verdict(p, e, n, signed):
    """ShowChairmanOpinionAboutTheSeason's place terms (to cseg_3C2DF) -> D7 before the clamp."""
    d = (e - p) * 100
    if signed:
        d0 = int(d / n)
    else:                                   # (edx cleared: 2^32 + d divided, its low word read as signed)
        d0 = (d & 0xffffffff) // n & 0xffff
        d0 -= 0x10000 if d0 & 0x8000 else 0
    d7 = 0
    if p != 0 and d0 < 30:
        d7 = 1 if d0 >= 10 else 2 if d0 > -10 else 3 if d0 > -30 else 4
    q = p * 100 // n
    return d7 - (q <= 25) + (q >= 75)


def _w(m, off, data):
    m.uc.mem_write(m.base2 + off, data)


def _r16(m, off):
    v = struct.unpack('<H', bytes(m.uc.mem_read(m.base2 + off, 2)))[0]
    return v - 0x10000 if v & 0x8000 else v


def _run(m, code, exp):
    m.uc.mem_write(m.base1 + SITE, code)
    m.uc.reg_write(emu.UC_X86_REG_ESP, emu.STACK_TOP - 4)
    m.uc.emu_start(m.base1 + START, m.base1 + MEC_END, count=20_000_000)   # (GetMoreExpensiveTeamsCount's end:
    if m.reg('eip') != m.base1 + MEC_END:                                   #  `mov ax, [D3]` -> D2, the expected
        raise RuntimeError(f'stopped at {m.where(m.reg("eip"))}')          #  place, forced here)
    _w(m, D3, struct.pack('<H', exp))
    m.uc.emu_start(m.base1 + MEC_END, m.base1 + STOP, count=20_000_000)
    if m.reg('eip') != m.base1 + STOP:
        raise RuntimeError(f'stopped at {m.where(m.reg("eip"))}')
    return _r16(m, D1), _r16(m, D2), _r16(m, D7)


def test_opsign():
    if not os.path.isdir(FIX):
        return True, f'SKIP: fixture {FIX} missing'
    m0 = Machine(FIX, 0)
    if bytes(m0.uc.mem_read(m0.base1 + SITE, 2)) != b'\x99\x90':
        return False, f'the snapshot exe has {bytes(m0.uc.mem_read(m0.base1 + SITE, 2)).hex()} at the site, not 9990'
    n = _r16(m0, CFB + 0x31)
    teams = [struct.unpack('<H', bytes(m0.uc.mem_read(m0.base2 + CFB + 0x12d + 2 * k, 2)))[0] for k in range(n)]
    order = [struct.unpack('<H', bytes(m0.uc.mem_read(m0.base2 + CFB + 0x6d + 2 * k, 2)))[0] // 18 for k in range(n)]
    me = teams.index(struct.unpack('<H', bytes(m0.uc.mem_read(m0.base2 + SEL, 2)))[0])
    bad, rows = [], []
    cl = lambda x: MSG[max(0, min(4, x))]
    for place, exp in CASES:
        out = []
        for code in (b'\x33\xd2', b'\x99\x90'):
            m = Machine(FIX, 0)
            o = [r for r in order if r != me]
            o.insert(place, me)
            _w(m, CFB + 0x6d, struct.pack(f'<{n}H', *[r * 18 for r in o]))
            out.append(_run(m, code, exp))
        (p0, e0, b), (p1, e1, a) = out
        tag = f'{place + 1}/{n} exp {exp + 1}'
        if (p0, e0) != (place, exp) or (p1, e1) != (place, exp):
            bad.append(f'{tag}: D1/D2 {p0}/{e0}, {p1}/{e1}')
        if b != verdict(place, exp, n, False):
            bad.append(f'{tag}: before {b}, the original formula {verdict(place, exp, n, False)}')
        if a != verdict(place, exp, n, True):
            bad.append(f'{tag}: after {a}, the signed rule {verdict(place, exp, n, True)}')
        if exp >= place and a != b:
            bad.append(f'{tag}: at / above expected but changed {b} -> {a}')
        rows.append(f'{tag}: {cl(b)} -> {cl(a)}')
    return not bad, '; '.join(bad) or f'{len(rows)} cases: ' + ', '.join(rows)
