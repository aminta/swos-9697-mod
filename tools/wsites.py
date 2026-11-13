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
# WS_R rows: entries are u8 and contiguous, so stride is not a step: stride = fill | file << 8 (file 0 = the file is the
# item's byte at aux). CD ent's file is the build's Serie D file: CD_FILE[0], set by s7swap.late (CD_TAB[2]) before rows()
CD_FILL = 1
CD_FILE = [None]

# careerFileBuffer layout (WSITES 4c): CFB offsets. TMD = tmdFileBuffer (careerFileBuffer dw, then the 80 records);
# IDA_CFB: an IDA dseg address - IDA_CFB = its CFB offset (dseg_D6B4E = TMD + 54720)
TMD, IDA_CFB = 2, 0xD6B4E - (2 + 54720)
UC_PREV = TMD + 0x3800 + 0x89FC             # uefacoef CB + PREV (NG 2409: KPTS 0x1910 + 12 NG)
UQ_ST = UC_PREV + 0x6C + 0xC                # uefacoef CB + SIZE: uefaq's state
DP_SV = TMD + ((UQ_ST - TMD + 2152 + 15) & ~15)   # dplay save_at: uefaq.STATE_END rounded to 16
CAL, CAL_N = 0xDB3E6 - IDA_CFB, (0xDF4F4 - 0xDB3E6) // 22


def check_layout():
    """At build (s7swap.late): the offsets above are this build's (uefacoef.layout(), uefaq.STATE_END, dplay's
    save_at): a module that moves its block fails the build instead of leaving a row on stale bytes."""
    import dplay
    import uefacoef as uc
    import uefaq
    errs = []
    if uefaq.STATE_END[0] is not None:          # (a league-phase world: uefacoef.layout() ran, uefaq linked)
        if TMD + uc.CB_OFF + uc.PREV != UC_PREV or TMD + uc.CB_OFF + uc.SIZE != UQ_ST:
            errs.append(f'uefacoef PREV / SIZE moved ({uc.PREV:#x} / {uc.SIZE:#x})')
        if TMD + uefaq.STATE_END[0] != UQ_ST + 2152:
            errs.append(f'uefaq state size ({uefaq.STATE_END[0]:#x})')
    if dplay.SAVE_OFF[0] is not None and TMD + dplay.SAVE_OFF[0] != DP_SV:
        errs.append(f'dplay save_at {dplay.SAVE_OFF[0]:#x}')
    assert not errs, ('wsites: careerFileBuffer rows off this build\'s layout', errs)
    print(f'wsites: CFB layout checked (uefacoef / uefaq: {uefaq.STATE_END[0] is not None}, dplay save_at: '
          f'{dplay.SAVE_OFF[0] is not None})')


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
# K keys (MC 13/11): states KEYED over team words are NOT rows - no WS_K / WS_O8 row may be registered (table() asserts it).
# Each key's consumer discards its state on a mismatch and rebuilds it; one line per key, with its evidence:
#   F1 (F1_ST.key = the league's first team word): K, discard-on-mismatch, tests/test_wsites_keys.py test_k_f1
#      (f1_valid / f1_auto / f1_build return 0, f1_capture rewrites it - captured after the swap, nothing lost)
#   LR (LR_BLK ss / n / t0 = season stamp, club count, first word): K, discard-on-mismatch (lr_res wipes and re-keys, a
#      season under way is VOID until the next one; lr_rank drops the head-to-head, the table still sorts) - lrank.c:74-115
#   SH (sp_sh +0 = file, division | 80h): K, discard-on-mismatch (sp_shsel zeroes and re-keys outside a simulation, a
#      scratch block inside one; discard, rebuilt at the next real pass) - split.py sp_shsel
#   ST (the engine item 'ST', sr_stled: FNV-1a of the entrants' words): K, discard-on-mismatch (sr_st_check returns 0 =
#      not started); NO CALLER in this tree - test_k_unconsumed pins it
#   SS (gp_ss.key = the bank's league file): follows the STRUCT, not the club (a bank describes a division, like WN's 'M');
#      only the SS_NB > 1 build reads it (ss_set / ss_view re-key and reset) - the default build has none (test_k_unconsumed)
ROWS = [
    # careerFileBuffer (WI_CFB: the .CAR's fixed part, 95151 B). WSITES 4b (Panchina 13/11) found the regions in 26 real
    # saves; 4c (13/11, MC's code pass) gives each one its writer and its capacity from the code: the mod's structs in
    # tmdFileBuffer's 80-record area (CFB + TMD; a big world's save keeps only the W1 block there, careerworld.py) and the
    # game's own arrays (ref/swos.asm: CFB = IDA address - IDA_CFB). test_wsites_cfb_layout recomputes every row below
    # from offsetof / the modules / the listing; check_layout() asserts the build's real offsets (dplay's save_at).
    (WI_CFB, 0x00034, 2, 22, WS_W, 0),         # W1 block (careerworld w_save_tail: rewritten from the cache at every save)
    # uefacoef.py block CB (TMD + CB_OFF; NG = bigtables.LIMIT): PREV[3] {dd count; dw team[16]} (uc_draw: ja 16), FIN[3]
    # {dw a, b} (the final's two clubs)
    *[(WI_CFB, UC_PREV + 36 * c + 4, 2, 16, WS_W, 0) for c in range(3)],
    (WI_CFB, UC_PREV + 0x6C, 2, 6, WS_W, 0),
    # uefaq.c struct uq_state (TMD + CB_OFF + SIZE, 2152 B): m, s at +2 (career club, stand-in); gl[3][36] at +16;
    # br[NBR 320] {u8 r, aw; u16 a, b} 6 B at +232 (uq_season: every qualifying tie)
    (WI_CFB, UQ_ST + 2, 2, 2, WS_W, 0),
    (WI_CFB, UQ_ST + 16, 2, 3 * 36, WS_W, 0),
    (WI_CFB, UQ_ST + 232 + 2, 6, 320, WS_W, 0),
    (WI_CFB, UQ_ST + 232 + 4, 6, 320, WS_W, 0),
    # dplay.c struct dp_save (TMD + save_at, 912 B): res at +2 (dp_rec), team[SN 28] at +8, srow[2][SR 20] {u16 team; ..}
    # 16 B at +0x110; its log copy (DP_LOG = + LOG_AT: 'DPLG', the state, then dp_out's head + mv[4] {u16 glob, team; ..})
    *[r for base in (DP_SV, DP_SV + 0x400 + 4) for r in (
        (WI_CFB, base + 2, 2, 1, WS_W, 0),
        (WI_CFB, base + 8, 2, 28, WS_W, 0),
        (WI_CFB, base + 0x110, 16, 40, WS_W, 0))],
    (WI_CFB, DP_SV + 0x400 + 4 + 912 + 4, 8, 4, WS_G, 0),
    (WI_CFB, DP_SV + 0x400 + 4 + 912 + 6, 8, 4, WS_W, 0),
    # the game's arrays: foreignMarketPlayers / homeMarketPlayers {u16 team; u8 player, pad} (AddForeignMarketPlayer
    # cmp 15, AddPlayerToCareerContest cmp 25); newJobOffers / jobOffers JobOffer[5] {u16 teamNo; ..} 1Ah B
    (WI_CFB, 0x0D78E, 4, 15, WS_W, 0),
    (WI_CFB, 0x0D7CA, 4, 25, WS_W, 0),
    (WI_CFB, 0x0D886, 26, 5, WS_W, 0),
    (WI_CFB, 0x0D90A, 26, 5, WS_W, 0),
    (WI_CFB, 0x0F9CB, 2, 15, WS_W, 0),         # (4b, by the saves: not in the code pass) stride 2 (odd address)
    (WI_CFBH, 0x051D, 2, 16, WS_W, 0),         # (4b) stride 2 (odd address)
    (WI_CFBH, 0x0960, 2, 28, WS_W, 0),         # (4b) season 8+: 28 words
    (WI_CFBH, 0x0BF9, 2, 4, WS_W, 0),          # (4b) 4 words (odd address)
    (WI_CFBH, 0x10AC, 2, 4, WS_W, 0),          # (4b) 4 words
    (WI_CFBH, 0x11C2, 2, 36, WS_W, 0),         # (4b) season 2+: a by-file sorted list, 36 words
    # the career calendar dseg_DB3E6 .. dseg_DF4F4 (cseg_8C516's bound): records of 16h B in a career (cseg_8C2AE: one
    # match: +0Ah its entry, home word +0Ch, away word +0Eh), CAL_N of them at most
    (WI_CFBH, CAL - 0x10000 + 12, 22, CAL_N, WS_W, 0),
    (WI_CFBH, CAL - 0x10000 + 14, 22, CAL_N, WS_W, 0),
    (WI_CFBH, 0x6097, 2, 20, WS_W, 0),         # (4b) a 20-club list (odd address, dseg_DF623: the DIY buffer)
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
    # CD (struct cd_state, 1032 B): gen[2 x (CDP 41 + CD1 64)] at +612; ent[256] at +348 (cd_season, run BEFORE the swap:
    # per ordinal of the Serie D file lf, the entry order's key) - WS_R with fill 1 = 'new to Serie D' (MC 13/11): every
    # changed row of the Serie D file holds a club that arrived from another division (a down-crosser now; Eccellenza
    # promotions later are new to Serie D too), so a changed row's key is 1 whatever cd_season wrote for the club that left
    # it (an up-crosser's 2+ place too). The file is literal (cd_state has no file byte): rows() puts CD_FILE in stride's
    # high byte (s7swap.late reads it from CD_TAB[2], gplay's lf)
    ('CD', 612, 2, 210, WS_W, 0),
    ('CD', 348, CD_FILL, 256, WS_R, 0),
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
    ('CF', 4, 0, 256, WS_R, 3),                 # (WS_R stride = fill | file << 8: fill 0, file 0 = the item's byte +3)
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
    return resolve([r for r in ROWS if not isinstance(r[0], str) or r[0] in engine.SAVE_ITEMS])   # (this build's items)


def resolve(rows):
    """rows with CD ent's literal file in its stride (CD_FILE[0]: this exe's Serie D file)."""
    out = []
    for r in rows:
        if r[0] == 'CD' and r[4] == WS_R:                               # (CD ent: the Serie D file, literal)
            assert CD_FILE[0] and 0 < CD_FILE[0] < 255, ('wsites: CD saved but no Serie D file (CD_FILE)', CD_FILE[0])
            r = (r[0], r[1], r[2] & 0xFF | CD_FILE[0] << 8) + tuple(r[3:])
        out.append(r)
    return out


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
        assert form not in (WS_O8, WS_K), ('wsites: no O8 / K row is ever registered (K keys discard on mismatch; CD ent is WS_R with a fill byte)', item, off)
        assert form in (WS_W, WS_G, WS_R) and 0 <= off < 0x10000 and count < 0x10000, ('wsites: row', item, off)
        assert form == WS_R or count <= 1 or stride >= 2, ('wsites: stride', item, off)
        assert form != WS_R or (count <= 256 and (stride >> 8 or aux)), ('wsites: WS_R row', item, off)
        out += struct.pack('<4H2B', item, off, stride, count, form, aux)
    assert len(rows) < WS_MAX, ('wsites: rows past WS_MAX', len(rows))
    return (out + struct.pack('<4H2B', WS_END, 0, 0, 0, 0, 0)).ljust(10 * WS_MAX, b'\0')
