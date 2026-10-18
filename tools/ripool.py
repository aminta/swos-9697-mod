"""The off-file pool's glue (Eccellenza 2026-27; gplay.c ri_season / ri_apply / ri_cache; design in
notes/world-2025-26.md 'Off-file Eccellenza pool').

Italy's 256 league slots fill its team file, so the clubs relegated from the lowest level swap IDENTITIES with an
off-file pool (DATA\\RS<world><file>.DAT, mkseason.rs_files) instead of leaving:
- ri_load replaces LoadTeamFile's `call SetLoadedTeamsGlobalNumbers` after TEAM.nnn is read: in a career of the
  pool's world, when the file read is the pool's league file (careerworld WTPHYS), the buffer is copied as read to
  RI_ORIG, the RS file is read once per DOS session into RI_POOL (the game's LoadFile, the pseudo registers kept),
  then gplay.c ri_apply gives every remapped slot its identity's record;
- pg_fix (pgroups.py) calls ri_season before pg_season and ri_after after the balance: the career cache's records of
  the swapped slots get their new identity (ri_cache), LoadTeamFile's own cache is cleared (teamsLoaded = 0,
  lastLoadedExtNumber = 0FFh) so the next load applies the new map;
- RI_STATE is the engine item 'RI' (saved with the career; cleared for a new career and for a save without it: the
  identity map, the pool's first order at the first season end).
"""
import re
import struct

ORIG_SIZE, POOL_SIZE = 0x2B000, 0x10000         # BSS: Italy's file as read (256 x 684 + 2), the pool (<= 95 records)
assert ORIG_SIZE >= 256 * 684 + 2                 # (Italy's 256 records + the count: 175106 B)
BSS_NEED = ORIG_SIZE + POOL_SIZE + 0x100
RI_SIZE = 4 + 2 * 256 + 2 * 64                  # gplay.c struct ri_state: the engine item 'RI'
LABELS = {}


def table_bytes(tabs):
    """db count (0 or 1); db world, file, low; dw slots; slots x (dw global, db base division, db D area); db pool;
    pool x db D area; pool x db first order."""
    assert len(tabs) <= 1, 'one off-file pool per build (gplay.c RI_STATE)'
    out = bytearray([len(tabs)])
    for world, fl, low, slots, areas, order in tabs:
        assert len(slots) <= 256 and len(areas) <= 64 and sorted(order) == list(range(len(areas)))
        out += bytes((world, fl, low)) + struct.pack('<H', len(slots))
        for g, base, a in slots:
            out += struct.pack('<HBB', g, base, a)
        out += bytes((len(areas),)) + bytes(areas) + bytes(order)
    return bytes(out)


ASM = '''
ri_load:                                ; replaces `call SetLoadedTeamsGlobalNumbers` after LoadTeamFile read TEAM.nnn
    pushad
    cmp word [GAMETYPE], 4              ; a career of the pool's world, the pool's league file
    jne .x
    cmp byte [SLT + WORLD_BYTE], RI_WORLD
    jne .x
    cmp byte [WTPHYS], RI_FILE
    jne .x
    mov esi, TEAMBUF                    ; Italy's file as read -> RI_ORIG
    movzx ecx, word [esi]
    xchg cl, ch
    imul ecx, ecx, 684
    add ecx, 2
    cmp ecx, ORIG_SIZE
    jbe .c0
    mov ecx, ORIG_SIZE
.c0:
    mov edi, RI_ORIG
    call ri_copyb
    cmp byte [RI_PLOADED], 0            ; the pool's file, once per DOS session
    jne .ap
    mov byte [RI_PLOADED], 1
    mov esi, D0R                        ; (inside LoadTeamFile: keep the game's pseudo registers D0..A6)
    mov edi, RI_REGS
    mov ecx, 60
    call ri_copyb
    mov dword [A0R], RI_NAME
    mov dword [A1R], RI_POOL
    call LOADFILE
    jz .ok
    mov word [RI_POOL], 0               ; (no pool file: no pool records)
.ok:
    mov esi, RI_REGS
    mov edi, D0R
    mov ecx, 60
    call ri_copyb
.ap:
    push dword RI_POOL
    push dword RI_ORIG
    push dword TEAMBUF
    call RI_APPLY
    add esp, 12
.x:
    popad
    jmp SETGLOBALS

ri_after:                               ; pg_fix, after ri_season and pg_season: the cache, LoadTeamFile's cache
    pushad
    cmp byte [SLT + WORLD_BYTE], RI_WORLD
    jne .x
    cmp word [RI_ORIG], 0               ; (Italy's file never read: no Italian record cached)
    je .c
    push dword RI_POOL
    push dword RI_ORIG
    push dword RI_FILE
    movzx eax, word [NUMSEL]
    push eax
    push dword [SELBASEV]
    call RI_CACHE
    add esp, 20
.c:
    mov word [TEAMSLOADED], 0
    mov byte [LASTEXT], 0FFh
.x:
    popad
    ret

ri_copyb:                               ; ecx bytes esi -> edi (no string instructions: ES may differ from DS)
    test ecx, ecx
    jz .r
.l:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .l
.r:
    ret
align 4
RI_PLOADED: db 0
RI_NAME: db RI_FNAME, 0
'''


def _load_site(p):
    """(the `call SetLoadedTeamsGlobalNumbers` after TEAM.nnn is read, LoadFile, the team buffer's current address):
    mov [A1], offset teamFileBuffer; call LoadFile; jnz second_try (0F 85); cmp [D1], imm; ja FatalError; call X."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    A1, D1 = struct.pack('<I', r['A0'] + 4), struct.pack('<I', r['D7'] - 24)
    m = [x for x in re.finditer(rb'\xc7\x05' + re.escape(A1) + rb'(.{4})\xe8(.{4})\x0f\x85.{4}\x81\x3d' + re.escape(D1)
                                + rb'.{4}\x0f\x87.{4}\xe8', d1, re.S)]
    m = [x for x in m if d1[x.end() + 4] != 0xe9]       # (the TEAM.nnn read; CUSTOMS.EDT's jumps on after the call)
    assert len(m) == 1, len(m)
    call = m[0].end() - 1
    load = m[0].start(2) + 4 + struct.unpack('<i', m[0].group(2))[0]
    return call, load, p.target(1, m[0].start(1)), r


def patch(p, at, bss, tabs, world_file_name):
    """ri_load / ri_after at obj1:at, buffers at obj2:bss (BSS_NEED); tabs = mkseason.off_pools(). Returns
    (end, the symbols pgroups.patch needs)."""
    import careerworld
    import gplay
    import nasmcave
    import split
    import trailer
    world, fl = tabs[0][0], tabs[0][1]
    call, loadfile, teambuf, r = _load_site(p)
    setglobals = call + 5 + struct.unpack('<i', bytes(p.get(1, call + 1, 4)))[0]
    s = careerworld.SITES
    sym = {'GAMETYPE': split.sites(p)['GAMETYPE'], 'SLT': s['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'WTPHYS': (1, careerworld.LABELS['WTPHYS']), 'RI_WORLD': (0, world), 'RI_FILE': (0, fl),
           'TEAMBUF': teambuf, 'ORIG_SIZE': (0, ORIG_SIZE), 'RI_ORIG': (2, bss), 'RI_POOL': (2, bss + ORIG_SIZE),
           'RI_REGS': (2, bss + ORIG_SIZE + POOL_SIZE), 'D0R': (2, r['D7'] - 28), 'A0R': (2, r['A0']),
           'A1R': (2, r['A0'] + 4), 'LOADFILE': (1, loadfile), 'SETGLOBALS': (1, setglobals),
           'RI_APPLY': gplay.LABELS['ri_apply'], 'RI_CACHE': gplay.LABELS['ri_cache'],
           'NUMSEL': trailer.INFO['NUMSEL'], 'SELBASEV': (1, trailer.INFO['selbasev']),
           'TEAMSLOADED': (2, s['teamsloaded']), 'LASTEXT': s['lastext'],
           'RI_FNAME': (0, '"%s"' % world_file_name)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, call + 1, struct.pack('<i', lab['ri_load'] - (call + 5)))
    LABELS.update(lab)
    print(f'exe: off-file pool (world {world}, file {fl}, {world_file_name}): LoadTeamFile obj1+{call:#x} -> ri_load '
          f'obj1+{at:#x}, buffers obj2+{bss:#x}')
    tab = (at + len(code) + 15) & ~15           # the table (gplay.c ri_season reads it; pgroups' pg_fix passes it)
    tb = table_bytes(tabs)
    p.put(1, tab, tb)
    import dplay
    ct = dplay._sites(p)[5]                     # careerTeam (obj2), as gplay
    return (tab + len(tb) + 15) & ~15, {'RI_TAB': (1, tab), 'RI_SEASON': gplay.LABELS['ri_season'],
                                         'RI_MGR': gplay.LABELS['RI_MGR'], 'RI_AFTER': (1, lab['ri_after']),
                                         'CAREERTEAM': (2, ct)}
