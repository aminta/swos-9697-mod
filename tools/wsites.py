"""S7 word sites (sreg_walk.h's WSITES): the rows the season-end swap builder (s7swap.c) and the old-save import walk
after a registry swap - every saved place that holds a team word, a global number, a file-keyed ordinal or a key over
words (n7-s7-clubmap.md §4: forms W / G / O8 / K). OWNER OF THE ROWS: Panchina (MC 13/11); the contract (row layout,
item numbers, forms) is sreg_walk.h's. Rows: (item, off, stride, count, form, aux); item 'NAME' (str) = the engine
item 'EN' of that name, or WI_CFB / WI_CACHE / WI_MAIN. Empty until the inventory lands: the builder walks nothing."""
import os
import struct

TEST = os.environ.get('S7_WSITES_TEST') == '1'       # (host-test builds only: TEST_ROWS instead of ROWS)

WI_CFB, WI_CACHE, WI_MAIN, WS_END, WS_MAX = 0, 1, 2, 0xFFFF, 128
WS_W, WS_G, WS_O8, WS_K = 1, 2, 3, 4

ROWS = [
]
# S7_WSITES_TEST=1 (test builds, modver.is_test): a cache row inside the players' bytes, a careerFileBuffer row of
# globals and an engine item's words - places the host test pokes (test_s7swap test_s7walk), never real data
TEST_ROWS = [
    (WI_CACHE, 100, 2, 3, WS_W, 0),
    (WI_CFB, 0x200, 2, 4, WS_G, 0),
    ('ST', 16, 2, 4, WS_W, 0),
]
OWN = (0, 1, 2, 3, 4, 25)                       # (a cache record's own bytes: s7swap.c rewrites them itself)


def rows():
    if TEST:
        import modver
        assert modver.is_test(), 'S7_WSITES_TEST: test builds only'
        return TEST_ROWS
    return ROWS


def table(rows=None):
    """WSITES' bytes (WS_MAX rows of 10, WS_END after the last)."""
    import engine
    rows = ROWS if rows is None else rows
    out, ids = b'', set()
    for item, off, stride, count, form, aux in rows:
        if item == WI_CACHE:
            span = range(off, off + max(count - 1, 0) * stride + (1 if form == WS_O8 else 2))
            assert not set(span) & set(OWN), ('wsites: a WI_CACHE row on the record\'s own bytes (s7swap.c\'s)', off)
        if isinstance(item, str):
            item = engine.item_id(item)
            assert item not in (WI_CFB, WI_CACHE, WI_MAIN, WS_END), ('wsites: an item id clashes', item)
            ids.add(item)
        assert form in (WS_W, WS_G, WS_O8, WS_K) and 0 <= off < 0x10000 and count < 0x10000, ('wsites: row', item, off)
        assert count <= 1 or stride >= (1 if form == WS_O8 else 2), ('wsites: stride', item, off)
        out += struct.pack('<4H2B', item, off, stride, count, form, aux)
    assert len(rows) < WS_MAX, ('wsites: rows past WS_MAX', len(rows))
    return (out + struct.pack('<4H2B', WS_END, 0, 0, 0, 0, 0)).ljust(10 * WS_MAX, b'\0')
