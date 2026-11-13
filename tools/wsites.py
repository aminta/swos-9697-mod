"""S7 word sites (sreg_walk.h's WSITES): the rows the season-end swap builder (s7swap.c) and the old-save import walk
after a registry swap - every saved place that holds a team word, a global number, a file-keyed ordinal or a key over
words (n7-s7-clubmap.md §4: forms W / G / O8 / K). OWNER OF THE ROWS: Panchina (MC 13/11); the contract (row layout,
item numbers, forms) is sreg_walk.h's. Rows: (item, off, stride, count, form, aux); item 'NAME' (str) = the engine
item 'EN' of that name, or WI_CFB / WI_CACHE / WI_MAIN. Empty until the inventory lands: the builder walks nothing."""
import os
import struct

TEST = os.environ.get('S7_WSITES_TEST') == '1'       # (host-test builds only: TEST_ROWS instead of ROWS)

WI_CFB, WI_CACHE, WI_MAIN, WI_CFBH, WS_END, WS_MAX = 0, 1, 2, 3, 0xFFFF, 128   # (WI_CFBH: careerFileBuffer + 0x10000)
WS_W, WS_G, WS_O8, WS_K, WS_R = 1, 2, 3, 4, 5

# WSITES 4a (Panchina 13/11): the engine items' word / global sites (n7-s7-clubmap.md §4a), forms W and G only - the
# walker's (O8 / K rows wait for their pieces: CD ent and CF rank (O8, file 102 by ordinal), F1 / ST / LR / SH / the SS
# banks' key byte (K: WS_KEYS callbacks, Shaved)). Offsets from the structs (i686, clang -target i686: test_wsites
# test_wsites_layout recomputes every row from offsetof / the modules' constants). Not walked: CN, BQ, CR, CC, GI, FF,
# TR, T3, UP, SWC1 (no team word), SR / SB (Brazilian state files only), RI (Italy retired by RB: feeds the import),
# BT_EXT (someLeaguesTable bytes 2000+: one byte per global = per ROW, not per club - never permuted: s7_season's
# re-base writes every row's delta of both files in leaguesTableCopy, file 144's split globals 2283.. included, and
# InitializeNewSeason's copy (cseg_8CC4E, loop widened to LIMIT by bigtables.py) carries them over; test_wsites_walk), BU (bteam.py: its B team words are DATA\\BAGE.nnn's, HOME words - identity
# data by the HOME word, MC 13/11 - compared with BAGE's again: walking them would break the match; the S7 audit's
# bteam item). rows() keeps a build's own items only (an item it does not save: no row).
ROWS = [
    # careerFileBuffer (WI_CFB: the .CAR's fixed part, 95151 B), WSITES 4b (Panchina 13/11): the 17 regions of
    # n7-s7-clubmap.md 4b, named by their observed layout in 26 real saves (stride, parity, count); every slot of an
    # array is walked as a word (a slot of another file, 0 or FFFFh is kept by the walker). PROVISIONAL extents:
    # the arrays' true bounds come from the game's code (the region's writer); test_wsites_cfb pins what the saves show.
    (WI_CFB, 0x00034, 2, 22, WS_W, 0),         # header: a 22-word by-file list (every save)
    (WI_CFB, 0x0C202, 2, 137, WS_W, 0),        # season 2+: word lists (3 x 16, 34, 35) - draws / entrant lists
    (WI_CFB, 0x0CAE4, 2, 31, WS_W, 0),         # season 8+: ~30 words
    (WI_CFB, 0x0CBF2, 16, 40, WS_W, 0),        # season 4+: 40 table rows, word at +2 (26h at +4)
    (WI_CFB, 0x0CED2, 2, 42, WS_W, 0),         # season 8+: ~30 words
    (WI_CFB, 0x0CFF6, 16, 40, WS_W, 0),        # season 8+: a second 40-row table, word at +6
    (WI_CFB, 0x0D27C, 8, 3, WS_W, 0),          # season 2+: stride 8
    (WI_CFB, 0x0D7CA, 4, 25, WS_W, 0),         # stride 4 (the career's league clubs)
    (WI_CFB, 0x0D886, 26, 5, WS_W, 0),         # season 2+: stride 26, word + FFh
    (WI_CFB, 0x0F9CB, 2, 15, WS_W, 0),         # stride 2 (odd address)
    (WI_CFBH, 0x051D, 2, 16, WS_W, 0),         # stride 2 (odd address)
    (WI_CFBH, 0x0960, 2, 28, WS_W, 0),         # season 8+: 28 words
    (WI_CFBH, 0x0BF9, 2, 4, WS_W, 0),          # 4 words (odd address)
    (WI_CFBH, 0x10AC, 2, 4, WS_W, 0),          # 4 words
    (WI_CFBH, 0x11C2, 2, 36, WS_W, 0),         # season 2+: a by-file sorted list, 36 words
    (WI_CFBH, 0x1E66, 22, 67, WS_W, 0),        # the league's fixture list: 22-byte records, home word +0, away word +2
    (WI_CFBH, 0x1E68, 22, 67, WS_W, 0),
    (WI_CFBH, 0x6097, 2, 20, WS_W, 0),         # a 20-club list (odd address)
    # GP (gplay.c struct gp_state, 2048 B): srow[SD 2][GT 32] {u16 team; ...} 10 B at +8; ko[2] (674 B at +648):
    # team[KN 24] at +474; dec[3] (12 B at +1996): team[2] at +4, glob[2] at +8
    ('GP', 8, 10, 64, WS_W, 0),
    ('GP', 648 + 474, 2, 24, WS_W, 0),
    ('GP', 648 + 674 + 474, 2, 24, WS_W, 0),
    ('GP', 1996 + 4, 12, 3, WS_W, 0),
    ('GP', 1996 + 6, 12, 3, WS_W, 0),
    ('GP', 1996 + 8, 12, 3, WS_G, 0),
    ('GP', 1996 + 10, 12, 3, WS_G, 0),
    # GS (struct gp_gs, 1408 B): srow[GSD 7][GSR 20] at +8, 10 B
    ('GS', 8, 10, 140, WS_W, 0),
    # SS / SS2 (struct gp_ss, one bank, 1542 B): r[SS_N 4][GT 32] {u16 team, glob; ...} 12 B at +6 (key byte +5: K, later)
    ('SS', 6, 12, 128, WS_W, 0),
    ('SS', 8, 12, 128, WS_G, 0),
    ('SS2', 6, 12, 128, WS_W, 0),
    ('SS2', 8, 12, 128, WS_G, 0),
    # CD (struct cd_state, 1032 B): gen[2 x (CDP 41 + CD1 64)] at +612 (ent[256] at +348: O8, later)
    ('CD', 612, 2, 210, WS_W, 0),
    # WN (struct wn_state, 164 B): e[WN_N 40] {u8 type, idx; u16 team} at +4. Entry 0 is always 'M' (gplay.c gp_season:
    # wn_add('M', wn_div, GP_IN.mgr) first): the career club's LAST-SEASON division = its team file + local division,
    # the key of the page's division title (winners.py wn_lastdiv) - the old division's identity, so its word is NOT walked
    # (walked, a club that crossed gets the new file with the old division index: 'SERIE A (STAGIONE REGOLARE)' for a Serie
    # D winner, Panchina 13/11); entries 1.. ('L' / 'K' / stage titles: winners' words) are
    ('WN', 10, 4, 39, WS_W, 0),
    # RS (RS_STATE[RC 8], struct rs_state 132 B): q[RQ 64] globals at +4 of each
    *[('RS', 132 * c + 4, 2, 64, WS_G, 0) for c in range(8)],
    # PR (struct pr_state, 388 B): c[PR_N 48] {u16 glob, p[2]; u8 m[2]} 8 B at +4
    ('PR', 4, 8, 48, WS_G, 0),
    # SC (gplay.c SC_ST, supercup.py: SC_H 12 + 12 x SC_NE 16): the cups below the last entry {db file, cid, 0, 0;
    # dw winner, winner global, finalist, finalist global}; the last entry (SC_U) the UEFA Super Cup's: db season, state,
    # won, snapshot season; dw winner, holders CL, EL, UECL
    ('SC', 12 + 4, 12, 15, WS_W, 0),
    ('SC', 12 + 6, 12, 15, WS_G, 0),
    ('SC', 12 + 8, 12, 15, WS_W, 0),
    ('SC', 12 + 10, 12, 15, WS_G, 0),
    ('SC', 12 + 12 * 15 + 4, 2, 4, WS_W, 0),
    # CT (conti.h struct ct_state, 196 B): hold[NCUP 16] {u16 id; u8 assoc, pad; u32 str, pts} 12 B at +4
    ('CT', 4, 12, 16, WS_W, 0),
    # CE (struct ct_ed, 2260 B): mgr at +8; e[NED 440] {u8 id0, id1, cr, s0, s1} at +60 (id0 | id1 << 8: a word)
    ('CE', 8, 0, 1, WS_W, 0),
    ('CE', 60, 5, 440, WS_W, 0),
    # US (uesum.h struct cup, 290 B): t[NTIE 22] {u16 x, y; u8 l1, l2, pn, fl} at +6; lw[NLP 36] at +182
    ('US', 6, 8, 22, WS_W, 0),
    ('US', 8, 8, 22, WS_W, 0),
    ('US', 182, 2, 36, WS_W, 0),
    # CF (gplay.c struct cf_state, 260 B: u16 magic, u8 season, file; u8 rank[256]) - WS_R: last season's places by ordinal of
    # file CF_ST.file (byte +3); a crosser's row is cleared (cf-st-s7.md); CN (struct cn_state, 36 B: u8 season, pad[3],
    # name[32]): pad[0..1] = the career club's division winner's WORD, pad[2] = 'W' marks it (S7 builds)
    ('CF', 4, 1, 256, WS_R, 3),
    ('CN', 1, 2, 1, WS_W, 0),
    # XS (xtra.py xsold, 2 + 3 x XSOLD 128): dw count, then {dw seller's word, db index} (S7 audit, MC 13/11)
    ('XS', 2, 3, 128, WS_W, 0),
    # XL (xleft.py, 5 + 3 x XLMAX 32): db on, dw count, dw oldest, then {dw managed club's word, db index} (S7 audit)
    ('XL', 5, 3, 32, WS_W, 0),
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
    import engine
    return [r for r in ROWS if not isinstance(r[0], str) or r[0] in engine.SAVE_ITEMS]   # (this build's items)


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
            assert item not in (WI_CFB, WI_CACHE, WI_MAIN, WI_CFBH, WS_END), ('wsites: an item id clashes', item)
            ids.add(item)
        assert form in (WS_W, WS_G, WS_O8, WS_K, WS_R) and 0 <= off < 0x10000 and count < 0x10000, ('wsites: row', item, off)
        assert count <= 1 or stride >= (1 if form in (WS_O8, WS_R) else 2), ('wsites: stride', item, off)
        out += struct.pack('<4H2B', item, off, stride, count, form, aux)
    assert len(rows) < WS_MAX, ('wsites: rows past WS_MAX', len(rows))
    return (out + struct.pack('<4H2B', WS_END, 0, 0, 0, 0, 0)).ljust(10 * WS_MAX, b'\0')
