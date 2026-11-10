"""4.2 S1.3: a career league's table by its real tie-breaker list - the glue around tools/lrank.c, which runs the
rules library's sr_league_rank (tools/swce/, copied from aminta/swos-competition-engine at tools/swce/SWCE_SHA).

pack.json, a division of a world league: "tiebreak": ["points", "avulsa", "goal_difference", "goals_for",
"draw_lots"] (swc's codes, schema/v1.md; FIGC 2026-27: internal/handoff/mc-s1-plan.md 'S1.2 RESULT'). Only the
career club's league is played in SWOS, so the list ranks that table (the view during the season and the final
table the season end reads); every other division keeps the game's own order. Not in a list: 'play_off_match'
(gplay plays it: a ko_playoffs entry with gap 1), and the codes that need data the game lacks (fair_play,
coefficient, previous_stage_rank).

Head to head: lr_res keeps the career league's results, one byte per ordered pair, in LR_BLK (engine item 'LR',
LR_SIZE B, saved with the career; leagues of up to lrank.c LR_N clubs). An older save, or a season already under way
when the block starts: no results for that season, its head-to-head criteria are left out (declared); from the
next season the list applies in full. The same for the away criteria (away_wins, away_goals_for): the game's rows
have no home / away split, so they come from the block too and are left out with it (declared).

Which table (H5 B1, Motore 09/11): the career club's league (D8CAA / world / D6CDC: an LR_TAB entry) only when DIY
is that division's table - one group (+4Fh) of the division's clubs (LR_TAB's count). A European group stage or league
phase, or a gplay group contest, holding the career club is a league layout under the same globals: left alone.

Code: obj4+LR_AT (lrank.c + LR_TAB), above the 4.1 pages (today swreg.UESUM_AT 0x2000; the 4.2 rebase's c-map in
mc.md: RIEPILOGO 0x3000, uprize 0x4000, uesum 0x5000). Hooks (chained): cseg_88CBB's `add word [esi+1BDh], 1` (split's sp_res when there) -> call
lr_res_hook; cseg_883DD's first instruction `mov [A4], offset DIY` (lp36's jmp lp_sort when there) -> jmp
lr_sort_hook."""
import os
import struct

LR_AT = 0x6000
LR_PAGES = 4                    # (4.2 H2 import: 121 world divisions' lists, 3 pages overflowed by 0xD1)
LR_N = 20                       # (lrank.c: the pairs block's clubs; 24 for the EFL / Segunda does not fit: the
                                # career cache's room (careerworld.SEL_ROOM) has 6 B left with 404, 24 needs +176)
LR_SIZE = 4 + LR_N * LR_N       # struct lr_blk
ENTRY = 24
CODES = (None, 'points', 'goal_difference', 'goals_for', 'goals_against', 'wins', 'away_wins', 'away_goals_for',
         'head_to_head_points', 'head_to_head_goal_difference', 'head_to_head_goals_for', 'head_to_head_away_goals',
         'fair_play', 'coefficient', 'previous_stage_rank', 'play_off_match', 'draw_lots', 'name', 'faithful_1996',
         'head_to_head_reapplied', 'avulsa', 'losses_fewer', 'home_losses_fewer',
         'head_to_head_table_once', 'only_if_two_level', 'away_goal_difference')     # (swcc TIEBS = SR_TB_*)
H2H = {'head_to_head_points', 'head_to_head_goal_difference', 'head_to_head_goals_for', 'head_to_head_away_goals',
       'head_to_head_reapplied', 'avulsa', 'home_losses_fewer', 'away_wins', 'away_goals_for',
       'head_to_head_table_once', 'away_goal_difference'}   # (the block's)
REFUSED = {'fair_play', 'coefficient', 'previous_stage_rank', 'play_off_match'}
LABELS = {}
# what the hooks and the host test use: cobj links only the sections they reach (of the #included library: sr_league_rank)
ROOTS = ('lr_res_hook', 'lr_sort_hook', 'lr_res', 'lr_rank', 'LR_BLK')
# 4.2 AFC mode (MC 11/11, option b): the code band obj4 0x6000..0xA000 = lrank.c, then conti's group draw (ctdraw.c
# via ctband.c, its own link right after lrank's end); LR_TAB alone in the 11th page (TAB_AT..+0x1000); SREG2 at 0xB000
# (the 12th). ctdraw's symbols go into LABELS too (the harness: syms['lrank'][CT_SDRAW_*]). MC: a code margin < 512 B
# -> ask MC (the next step a CT page past SREG2, 0xC000).
TAB_AT = LR_AT + 0x1000 * LR_PAGES
CT_ROOTS = ('ct_place', 'CT_SDRAW_N', 'CT_SDRAW_ERR', 'CT_SDRAW_HIT')


def compile_list(names, teams, where):
    """a division's "tiebreak" -> (codes, uses the block); raises ValueError"""
    if not (isinstance(names, list) and names and len(names) < 16):
        raise ValueError(f'{where}: tiebreak: a list of 1..15 codes')
    out = []
    for nm in names:
        if nm not in CODES[1:]:
            raise ValueError(f'{where}: tiebreak: unknown code {nm!r}')
        if nm in REFUSED:
            raise ValueError(f'{where}: tiebreak: {nm!r} needs data the game lacks (play_off_match: a ko_playoffs '
                             'entry with gap 1)')
        if nm in out and nm not in ('head_to_head_goal_difference', 'only_if_two_level'):
            raise ValueError(f'{where}: tiebreak: {nm!r} twice')
        out.append(nm)
    if out[-1] == 'only_if_two_level' or 'only_if_two_level only_if_two_level' in ' '.join(out):
        raise ValueError(f'{where}: tiebreak: only_if_two_level prefixes the code after it')
    h2h = bool(H2H & set(out))
    if h2h and teams > LR_N:
        raise ValueError(f'{where}: tiebreak: head to head in a division of {teams} clubs (the saved block: {LR_N})')
    return bytes(CODES.index(nm) for nm in out), h2h


def table(p, tables):
    """LR_TAB bytes and its league-struct dwords' (offset, (obj, off)): tables = [(world, league file, [(div, codes,
    h2h, clubs)])]"""
    import mkseason
    out, ptrs = bytearray(), []
    for world, lfile, divs in tables:
        at = mkseason.LEAGUE_AT[(world, lfile)]
        at = at if isinstance(at, tuple) else (1, at)
        for d, codes, h2h, teams in divs:
            ptrs.append((len(out), at))
            out += struct.pack('<IBBBB', at[1], world, d, int(h2h), teams) + codes.ljust(16, b'\0')
    return bytes(out + bytes(ENTRY)), ptrs


def patch(p, tables, split_st, split_magic):
    """lrank.c + LR_TAB at obj4+LR_AT, the two hooks. Returns the end."""
    import cobj
    import dplay
    import split
    import swe
    import uesum
    import careerworld
    room = 0x1000 * swe.OBJ4_PAGES
    assert TAB_AT + 0x1000 <= room == p.le.obj(4).npages * 0x1000, ('lrank: obj4 pages', hex(room))
    assert not any(p.get(4, LR_AT, TAB_AT + 0x1000 - LR_AT)), 'lrank: obj4+LR_AT not free'
    s = split.sites(p)
    tab, ptrs = table(p, tables)
    res, sort = s['res'], s['sort_start']
    res_chain = p.get(1, res, 1) == b'\xe8'
    sort_chain = p.get(1, sort, 1) == b'\xe9'
    assert res_chain or bytes(p.get(1, res, 8)) == p.le.obj_bytes(1)[res:res + 8], 'lrank: cseg_88CBB site'
    assert sort_chain or bytes(p.get(1, sort, 10)) == p.le.obj_bytes(1)[sort:sort + 10], 'lrank: cseg_883DD site'
    a0 = s['A0']
    ds = dplay._sites(p)
    ps = dplay._play_sites(p, ds[8])
    ext = {'UD': (2, s['DIY']), 'A3': (2, a0 + 12), 'A4': (2, a0 + 16), 'D1': (2, a0 - 28), 'D2': (2, a0 - 24),
           'GAMETYPE': s['GAMETYPE'], 'SIMFLAG': (2, s['SIMFLAG']), 'CAREERTEAM': (2, ds[5]),
           'D6CDC': (2, ps['d6cdc']), 'D8CAA': (2, ps['d8caa']),
           'WORLDB': (s['SLT'][0], s['SLT'][1] + careerworld.WORLD_BYTE), 'SEASONP': uesum.season_var(p)}
    flags = ['-Oz', '-fno-zero-initialized-in-bss', f'-DSPLIT_ST={split_st}', f'-DSPLIT_MAGIC={split_magic}']
    force = int(os.environ.get('LR_FORCE') or 0)
    if force:
        print(f'exe: LR_FORCE={force} (test build: at the league end place {force + 1} gets place {force}\'s points)')
        flags.append(f'-DLR_FORCE={force}')
    if res_chain:
        ext['RES_PREV'] = p.call_target(1, res)
        flags.append('-DRES_CHAIN')
    if sort_chain:
        ext['SORT_PREV'] = p.call_target(1, sort)
        flags.append('-DSORT_CHAIN')
    else:
        ext['SORT_NEXT'] = (1, sort + 10)
    tab_at = TAB_AT
    assert tab_at + len(tab) <= TAB_AT + 0x1000, ('lrank: LR_TAB over its page', len(tab))   # (MC: S7 adds up to 9)
    ext['LR_TAB'] = (4, tab_at)
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lrank.c'), flags, sections=True)
    syms, end, bss = cobj.link(p, obj, LR_AT, (4, 0), externs=ext, limit=TAB_AT, text_obj=4, roots=ROOTS)
    assert bss == 0, ('lrank.c: no .bss', bss)
    assert end <= TAB_AT, ('lrank: code over its band', hex(end), hex(TAB_AT))   # (4.2 P7, MC: the band is fixed - LR_PAGES 4,
                                                    # SREG2 at 0xA000; anything more moves past 0xB000, ask MC)
    p.put(4, tab_at, tab)
    for off, (o, a) in ptrs:
        cobj.add_ptr(p, tab_at + off, o, a, 4)
    if p.rel_target(1, res + 1):
        p.remove(1, res + 1)
    p.branch(1, res, 0xE8, *syms['lr_res_hook'][:2], n=8)
    if not sort_chain:
        p.remove(1, sort + 2)                               # mov [A4], offset DIY (10 B): its two dwords' fixups
        p.remove(1, sort + 6)
    p.branch(1, sort, 0xE9, *syms['lr_sort_hook'][:2], n=10 if not sort_chain else 5)
    LABELS.clear()
    LABELS.update(syms)
    LABELS['ext'] = dict(ext, sort=(1, sort), res=(1, res))     # (hosttest: the game's variables and the two sites)
    print(f'exe: tie-breaker lists (lrank, 4.2 S1.3): obj4+{LR_AT:#x}..{end:#x}, LR_TAB {len(tab) // ENTRY - 1} '
          f'divisions at obj4+{tab_at:#x} ({TAB_AT + 0x1000 - tab_at - len(tab)} B left in its page); hooks cseg_88CBB obj1+{res:#x} ({"after sp_res" if res_chain else "own"}), '
          f'cseg_883DD obj1+{sort:#x} ({"after lp_sort" if sort_chain else "own"}); LR_BLK obj4+{syms["LR_BLK"][1]:#x} '
          f'({LR_SIZE} B, item LR)')
    LABELS['@end'] = (4, end)
    return end


def ct_patch(p):
    """4.2 AFC mode (MC 11/11, option b): ctband.c (ctdraw.c + the library's group draws), its own link in the code
    band right after lrank's end, up to TAB_AT; its symbols into LABELS (ct_place: conti.sdraw_patch). Returns
    ct_place."""
    import cobj
    import swe
    at, lim = (LABELS['@end'][1] + 15) & ~15, TAB_AT
    assert not any(p.get(4, at, lim - at)), 'ctdraw: obj4 after lrank not free'
    flags = ['-Oz', '-fno-zero-initialized-in-bss']
    ext = {'cstack_call': swe.LABELS['cstack_call'], 'swe_ready': swe.LABELS['swe_ready']}   # (the engine's C stack)
    roots = CT_ROOTS
    if os.environ.get('CTDRAW_FORCE'):
        print('exe: CTDRAW_FORCE (test build: CT_SDRAW_FORCE refuses a conti group draw)')
        flags.append('-DCTDRAW_FORCE')
        roots += ('CT_SDRAW_FORCE',)
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctband.c'), flags, sections=True)
    syms, end, bss = cobj.link(p, obj, at, (4, 0), externs=ext, limit=lim, text_obj=4, roots=roots)
    assert bss == 0, ('ctband.c: no .bss', bss)
    assert end <= lim, ('ctdraw: the code band over', hex(end), hex(lim))
    lib = sorted(k for k in syms if k.startswith('sr_'))
    LABELS.update(syms)
    print(f'exe: conti group draws (ctdraw, 4.2 AFC mode): obj4+{at:#x}..{end:#x} ({lim - end} B left in the code band'
          f'{", UNDER 512: ask MC" if lim - end < 512 else ""}); '
          f'library {lib}')
    return syms['ct_place']
