"""The obj2 tail registry (5.0 NT piece 2, MC 15/11 condition 3): the zeroed-at-startup part of obj2 (obj2 + obj2_free +
o2pages * page = the tail's start, vsize beyond the file pages, zeroed by tailzero.py: build.log 'obj2 tail obj2+0xd5000..') is
claimed by modules at hand-computed offsets (the career BSS: UEFA qualifying rounds, gplay / dplay / conti / ripool .bss, then
shirtnum, blond, menunum, fmtpage, teamstab, lgreal's tables: patch.py's num_bss chain). That chain starts AFTER the claims made
here: a claim is a named region at the tail's very start, reserved before every other user is placed, so nothing overlaps it by
construction, and check() asserts it (sorted, disjoint, inside the reserved size, the sum the chain was shifted by).

Claims today: bigtables' two NT tables (someLeaguesTable / leaguesTableCopy, LIMIT_ALL + 4 bytes each, only in a build with the
211-NT data: they must read 0 at every NT global; zeroed at startup like the rest of the tail). No claim = no shift = a 4.x build
is byte-identical.

    plan(sizes)  -> the total reserved bytes (16-aligned), before the chain is placed;  claim(name, size) -> offset in the tail
    check()      -> asserts; where(name, tail0) -> absolute obj2 offset"""
CLAIMS = {}
RESERVED = [0]


def reset():
    CLAIMS.clear()
    RESERVED[0] = 0


def _al(n, a=16):
    return (n + a - 1) // a * a


def plan(sizes):
    """Reserve the tail's first bytes for claims of these sizes (in the order claim() will be called)."""
    RESERVED[0] = sum(_al(s) for s in sizes)
    return RESERVED[0]


def claim(name, size):
    assert name not in CLAIMS, f'obj2 tail: {name} claimed twice'
    off = sum(_al(s) for _, s in CLAIMS.values())
    assert off + _al(size) <= RESERVED[0], f'obj2 tail: {name} ({size} B) past the reserved {RESERVED[0]} B (plan() first)'
    CLAIMS[name] = (off, size)
    return off


def check():
    rs = sorted((o, o + s, n) for n, (o, s) in CLAIMS.items())
    for (a0, a1, an), (b0, b1, bn) in zip(rs, rs[1:]):
        assert a1 <= b0, f'obj2 tail: {an} [{a0:#x}, {a1:#x}) overlaps {bn} [{b0:#x}, {b1:#x})'
    assert not rs or rs[-1][1] <= RESERVED[0], f'obj2 tail: claims end {rs[-1][1]:#x} past the reserved {RESERVED[0]:#x}'
    assert sum(_al(s) for _, s in CLAIMS.values()) == RESERVED[0], 'obj2 tail: the reserved size is not the claims\' sum (plan / claim sizes differ)'


def where(name, tail0):
    return tail0 + CLAIMS[name][0]


def describe(tail0):
    return ', '.join(f'{n} obj2+{tail0 + o:#x} ({s} B)' for n, (o, s) in sorted(CLAIMS.items(), key=lambda kv: kv[1][0]))
