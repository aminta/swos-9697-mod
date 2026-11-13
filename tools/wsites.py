"""S7 word sites (sreg_walk.h's WSITES): the rows the season-end swap builder (s7swap.c) and the old-save import walk
after a registry swap - every saved place that holds a team word, a global number, a file-keyed ordinal or a key over
words (n7-s7-clubmap.md §4: forms W / G / O8 / K). OWNER OF THE ROWS: Panchina (MC 13/11); the contract (row layout,
item numbers, forms) is sreg_walk.h's. Rows: (item, off, stride, count, form, aux); item 'NAME' (str) = the engine
item 'EN' of that name, or WI_CFB / WI_CACHE / WI_MAIN. Empty until the inventory lands: the builder walks nothing."""
import struct

WI_CFB, WI_CACHE, WI_MAIN, WS_END, WS_MAX = 0, 1, 2, 0xFFFF, 128
WS_W, WS_G, WS_O8, WS_K = 1, 2, 3, 4

ROWS = [
]


def table():
    """WSITES' bytes (WS_MAX rows of 10, WS_END after the last)."""
    import engine
    out, ids = b'', set()
    for item, off, stride, count, form, aux in ROWS:
        if isinstance(item, str):
            item = engine.item_id(item)
            assert item not in (WI_CFB, WI_CACHE, WI_MAIN, WS_END), ('wsites: an item id clashes', item)
            ids.add(item)
        assert form in (WS_W, WS_G, WS_O8, WS_K) and 0 <= off < 0x10000 and count < 0x10000, ('wsites: row', item, off)
        assert count <= 1 or stride >= (1 if form == WS_O8 else 2), ('wsites: stride', item, off)
        out += struct.pack('<4H2B', item, off, stride, count, form, aux)
    assert len(ROWS) < WS_MAX, ('wsites: rows past WS_MAX', len(ROWS))
    return (out + struct.pack('<4H2B', WS_END, 0, 0, 0, 0, 0)).ljust(10 * WS_MAX, b'\0')
