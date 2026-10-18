"""Parallel groups in a career world (Serie C 2026-27: 3 groups of 20 below Serie B; El Salvador: two levels of zones).

The engine knows one chain of divisions per country: at the season end a division's 'promoted' clubs go one division
up and its 'relegated' ones one down, as signed deltas per global club number in leaguesTableCopy (someLeaguesTable
holds the season's own; division = the club record's base division + delta). A level of groups is a run of the chain
(pack.json league 'parallel': {upper, first = upper + 1, count}, or a list of them, top-down); each group's data say
how many go up ('promoted') and down ('relegated'). Before InitializeNewSeason copies leaguesTableCopy back (its
`call cseg_7CAA2`, obj1 0x7CB86) gplay.c pg_season turns every move of the game into a move of one LEVEL:
- up or down into a single division: that division (a group winner below the first group went to the group above);
- into a level of groups: the group of the club's area (clubs.csv 'area'; else its own group's index, else the
  middle group), else the nearest group with room (each group keeps its size: balancing).
No club leaves the lowest level (Davide: as the original game's lowest English division).
"""
import re
import struct

import nasmcave

ASM = '''
pg_fix:                                 ; replaces `call cseg_7CAA2` (leaguesTableCopy -> someLeaguesTable) in
    pushad                              ; InitializeNewSeason: the running world's tables first (gplay.c pg_season)
    movzx eax, byte [SLT + WORLD_BYTE]
    push eax
    push dword SLTCOPY
    push dword SLT
    push dword RS_TAB                   ; the reserve first (gplay.c rs_season: who leaves the lowest level, who
    call RS_SEASON                      ; comes back), then the levels' groups (pg_season places the new clubs)
    add esp, 4
    push dword PG_TAB
    call PG_SEASON
    add esp, 16
    xor eax, eax                        ; cseg_9487A traps unless leaguesTableCopy adds up to 0 (8 bits): a move of
    mov esi, SLTCOPY                    ; several divisions (a group winner up two levels of groups, a club down into
    mov ecx, NSUM                       ; a farther group) breaks the game's +1 / -1 pairs: the balance byte BAL
.s:                                     ; (a global number of no club) takes the difference
    add al, [esi]
    inc esi
    loop .s
    sub [SLTCOPY + BAL], al
    popad
    jmp C7CAA2
PG_TAB: TAB_BYTES
RS_TAB: RS_BYTES
'''


BALANCE = 1844                  # someLeaguesTable / leaguesTableCopy index of no club (careerworld: 1818..1846 free of
                                # clubs; 1845 world byte): the moves' balance byte


def relax_file_check(p):
    """cseg_9487A (every country's season end) also traps unless the loaded team file's clubs' deltas in
    leaguesTableCopy add up to 0: true while every division keeps its size, but between the season end's moves (the
    game's +1 / -1 chain, gplay's play-off moves of several divisions) and pg_fix (InitializeNewSeason) a level of
    groups is briefly off, and a file's range has no club-free byte to balance. The second check's `jz` becomes
    `jmp` (the whole table's sum, the first check, stays: BALANCE keeps it 0)."""
    ms = [m.start() for m in re.finditer(rb'\x66\x0b\xc0\x74.\xcc\xeb\xfe', p.le.obj_bytes(1), re.S)]
    assert len(ms) == 2 and 0 < ms[1] - ms[0] < 0x100, [hex(x) for x in ms]
    p.put(1, ms[1] + 3, b'\xeb')
    print(f'exe: season end: the team file sum check relaxed (obj1+{ms[1] + 3:#x})')


def reserve_bytes(tables):
    """db count; per country (world, nd, low, [(global, base)], [pool globals]): gplay.c rs_season."""
    out = bytearray((len(tables),))
    for world, nd, low, clubs, pool in tables:
        assert len(pool) <= 64 and len(tables) <= 8
        out += bytes((world, nd, low)) + struct.pack('<H', len(clubs))
        for g, base in clubs:
            out += struct.pack('<HB', g, base)
        out += bytes((len(pool),)) + b''.join(struct.pack('<H', g) for g in pool)
    return bytes(out)


def table_bytes(tables):
    """db count; per country (world, [(first division, [group sizes])] top-down over the whole chain, [(global,
    base division, area or [areas per level of groups])]): see gplay.c pg_season."""
    out = bytearray((len(tables),))
    for world, levels, clubs in tables:
        npar = sum(1 for _, sizes in levels if len(sizes) > 1)
        out += bytes((world, len(levels)))
        for first, sizes in levels:
            out += bytes((first, len(sizes))) + bytes(min(255, x) for x in sizes)
        out += bytes((npar,)) + struct.pack('<H', len(clubs))
        for g, base, area in clubs:
            areas = list(area) if isinstance(area, (list, tuple)) else [area] * npar
            assert len(areas) == npar, (g, areas, npar)
            out += struct.pack('<HB', g, base) + bytes(areas)
    return bytes(out)


def _site(p):
    """The call of cseg_7CAA2 (leaguesTableCopy -> someLeaguesTable) in InitializeNewSeason."""
    import careerworld
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    s = careerworld.SITES                   # (careerworld.patch ran first; its patterns are hooked by now)
    pk = lambda x: re.escape(struct.pack('<I', x))
    import bigtables
    slt = struct.pack('<I', bigtables.SITES.get('old', s['slt'])[1])   # (the original bytes: the table's old address)
    starts = [x.start() - 9 for x in re.finditer(rb'\xc7\x05' + pk(r['A0']) + re.escape(slt) + rb'\xc7\x05' +
                                                 pk(r['A0'] + 4), d1)]
    # the copy back: reads [A1] (leaguesTableCopy) first: mov esi, [A1] right after the three set-ups
    back = [st for st in starts if d1[st + 29:st + 35] == b'\x8b\x35' + struct.pack('<I', r['A0'] + 4)]
    assert len(back) == 1, [hex(x) for x in starts]
    calls = [i for i in range(len(d1) - 5) if d1[i] == 0xe8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == back[0]]
    assert len(calls) == 1, calls
    return calls[0], back[0], s


LABELS = {}             # obj1 offsets other modules link to (RS_TAB: gplay's sacking check; PG_TAB: pg_place at a 3.x load)


def patch(p, at, tables, pg_season, rs_tables=(), rs_season=None):
    """Glue + tables at obj1:at (the fix itself: gplay.c pg_season, (1, offset)); returns the end."""
    import bigtables
    import careerworld
    site, c7caa2, s = _site(p)
    assert p.get(1, site, 5) == p.le.obj_bytes(1)[site:site + 5], 'the copy-back call is already hooked'
    sym = {'SLT': s['slt'], 'SLTCOPY': s['sltcopy'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'C7CAA2': (1, c7caa2), 'PG_SEASON': pg_season, 'BAL': (0, BALANCE), 'RS_SEASON': rs_season,
           'RS_BYTES': (0, 'db ' + ', '.join(str(b) for b in reserve_bytes(list(rs_tables)))),
           'NSUM': (0, bigtables.LIMIT if bigtables.ON[0] else 2000),
           'TAB_BYTES': (0, 'db ' + ', '.join(str(b) for b in table_bytes(tables)))}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', lab['pg_fix'] - (site + 5)))   # (a relative call: no fixup)
    LABELS.update(RS_TAB=lab['RS_TAB'], PG_TAB=lab['PG_TAB'])
    print(f'exe: parallel groups: {len(tables)} countries, reserves {len(rs_tables)}, copy-back call obj1+{site:#x}, code obj1+{at:#x}..'
          f'{at + len(code):#x}')
    return at + len(code)
