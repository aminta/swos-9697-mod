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
    push dword PG_TAB
    call PG_SEASON
    add esp, 16
    popad
    jmp C7CAA2
PG_TAB: TAB_BYTES
'''


def table_bytes(tables):
    """(world, [(first division, [group sizes])] top-down over the whole chain, [(global, base division, area)])."""
    out = bytearray()
    for world, levels, clubs in tables:
        out += bytes((world, len(levels)))
        for first, sizes in levels:
            out += bytes((first, len(sizes))) + bytes(min(255, x) for x in sizes)
        out += struct.pack('<H', len(clubs))
        for g, base, area in clubs:
            out += struct.pack('<HBB', g, base, area)
    return bytes(out + b'\0')


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


def patch(p, at, tables, pg_season):
    """Glue + tables at obj1:at (the fix itself: gplay.c pg_season, (1, offset)); returns the end."""
    import careerworld
    site, c7caa2, s = _site(p)
    assert p.get(1, site, 5) == p.le.obj_bytes(1)[site:site + 5], 'the copy-back call is already hooked'
    sym = {'SLT': s['slt'], 'SLTCOPY': s['sltcopy'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'C7CAA2': (1, c7caa2), 'PG_SEASON': pg_season,
           'TAB_BYTES': (0, 'db ' + ', '.join(str(b) for b in table_bytes(tables)))}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', lab['pg_fix'] - (site + 5)))   # (a relative call: no fixup)
    print(f'exe: parallel groups: {len(tables)} countries, copy-back call obj1+{site:#x}, code obj1+{at:#x}..'
          f'{at + len(code):#x}')
    return at + len(code)
