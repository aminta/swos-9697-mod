"""The game's pair tables for an odd number of clubs (dseg_11F356[n - 2], n = 5..23) are no rounds: the league
engine counts n // 2 pairs as a match day (cseg_8922B, [1C7h]), and in those tables many 'days' have a club twice and
others none (n = 15: 9 days of 15; n = 21: 15 of 21). In a career the calendar builder (cseg_8B8D9) then writes two of
the career club's matches into one 22-byte block, which runs over the next one: the next season traps (int 3 at
cseg_8B8D9+A0, World 2026-27: ARG 15, SLV 9, USA 15). In a season (Italy 1947-48, 21 clubs) a club plays twice on
some match days.
patch(): the odd tables rewritten in place (same length, same n(n-1)/2 pairs) as real rounds: the circle method with
a rest, every club once per round at rest, (n - 1) / 2 +- 1 home games each in a cycle and n - 1 in two (the engine
plays the second cycle the other way round), at most 3 home or away games running. Only with mkseason.odd_leagues (a pack with an odd
division): the other builds stay byte for byte as they were."""
import re
import struct


def rounds(n):
    """Berger tables of n clubs (odd: a rest each round): [[(home, away), ...] per round]."""
    k = n + (n & 1)
    lst = list(range(k))
    out = []
    for r in range(k - 1):
        day = []
        for i in range(k // 2):
            a, b = lst[i], lst[k - 1 - i]
            if (r % 2 == 1) if i == 0 else (i % 2 == 1):  # the fixed club alternates, the others by their
                a, b = b, a                                 # place: at most 3 home or away games running
            if max(a, b) < n:
                day.append((a, b))
        out.append(day)
        lst = [lst[0]] + [lst[-1]] + lst[1:-1]
    return out


def table(p):
    """(obj, offset) of the per-size pointer table dseg_11F356 (cseg_89758: mov [A3], offset dseg_11F356)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\x66\x8b\x46\x51\x66\xa3' + A(a0 - 32) + rb'\x66\x83\x2d' + A(a0 - 32) + rb'\x02', d1, re.S)]
    assert len(m) == 1, 'cseg_89758: mov ax, [esi+51h]; mov [D0], ax; sub [D0], 2'
    k = d1.rfind(b'\xc7\x05' + struct.pack('<I', a0 + 12), m[0].start() - 0x30, m[0].start())
    assert k > 0, 'mov [A3], offset dseg_11F356'
    return p.target(1, k + 6)


def patch(p):
    tobj, toff = table(p)
    out = []
    for n in range(5, 24, 2):
        eobj, eoff = p.target(tobj, toff + 4 * (n - 2))
        new = b''.join(bytes(pr) for day in rounds(n) for pr in day)
        assert len(new) == n * (n - 1), n
        old = p.get(eobj, eoff, len(new))
        assert sorted(zip(old[::2], old[1::2])) != [] and {frozenset(x) for x in zip(old[::2], old[1::2])} == \
            {frozenset(x) for x in zip(new[::2], new[1::2])}, f'pair table {n}: not the same pairs'
        p.put(eobj, eoff, new)
        out.append(n)
    print(f'exe: odd pair tables as rounds (a rest each round) for {out[0]}..{out[-1]} clubs')
