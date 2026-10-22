"""Off-file pools' glue (gplay.c ri_season / ri_apply / ri_cache; design in notes/world-2025-26.md 'Off-file
Eccellenza pool' and 'State pools'): Italy's Eccellenza (its 256 league slots fill its team file) and Brazil's state
A2 clubs (file 161, the state-only clubs: no free global numbers) swap IDENTITIES with off-file pools
(DATA\\RS<world><file>.DAT, mkseason.rs_files) instead of clubs leaving or entering the world:
- ri_load replaces LoadTeamFile's `call SetLoadedTeamsGlobalNumbers` after TEAM.nnn is read: in a career of a pooled
  file's world, when the file read is that file (careerworld WTPHYS), the buffer is copied as read to its ORIG buffer,
  its RS file is read once per DOS session into its POOL buffer (the game's LoadFile, the pseudo registers kept),
  then gplay.c ri_apply gives every remapped slot its identity's record;
- pg_fix (pgroups.py) calls ri_season before pg_season (with every state's ranking, statespec's 'SR' item, through
  RI_SR_PTR, which statecup fills) and ri_after after the balance: the career cache's records of the swapped slots get their new
  identity (ri_cache), LoadTeamFile's own cache is cleared (teamsLoaded = 0, lastLoadedExtNumber = 0FFh) so the next
  load applies the new map;
- RI_STATE is the engine item 'RI' (saved with the career; cleared for a new career and for a save without it: the
  identity maps, the pools' first order at the first season end).
"""
import os
import re
import struct

RF = 8                                          # gplay.c RF / RP / RQT / RO / RMT: files, pools, queue words, contest
RP, RQT, RO, RMT = 20, 192, 16, 640             # entries per state, map words (each file: its own slots)
RI_SIZE = RF + RP + 2 * RQT + 2 * RP * RO + 2 * RMT  # gplay.c struct ri_state: the engine item 'RI'
OVR_AT = RF + RP + 2 * RQT                      # (+ RI_STATE: ovr[RP][RO], statecup applies them: RI_OVR)


def layout(tabs):
    """Per pooled file (map offset, map words = its records, its ORIG buffer's size, its POOL buffer's size, the ORIG
    buffer's offset in the BSS); and the BSS size."""
    out, moff, b = [], 0, 0
    for world, fl, pools, base, spares, nrec, npool in tabs:
        osz, psz = (nrec * 684 + 2 + 15) & ~15, (npool * 684 + 2 + 15) & ~15   # (the file as read: Italy 175106 B)
        assert osz >= nrec * 684 + 2 and psz >= npool * 684 + 2
        out.append((moff, nrec, osz, psz, b))
        moff += nrec
        b += osz + psz
    assert moff <= RMT, f'{moff} pooled slots (gplay.c RMT {RMT})'
    return out, b + 0x100


def bss_need(tabs):
    return layout(tabs)[1]
LABELS = {}


def table_bytes(tabs):
    """gplay.c ri_season's table: db files; per file db world, file, pools, dw base (its global numbers), db spares,
    spares x db ordinal; per pool db kind, n (its pool records),
    kind 0 ('league'): db low; dw slots; slots x (dw global, db base division, db D area); n x db D area;
    kind 1 ('state'): dw key; db relegated; db slots; slots x (db ordinal, dw global, db strength); n x db strength;
    db entries; entries x dw the contest's team words;
    then n x db RS record (the first order). tabs: [(world, file, pools, base, [spare ordinals])]."""
    assert len(tabs) <= RF, f'at most {RF} pooled team files (gplay.c RF)'
    out = bytearray([len(tabs)])
    npools = nq = 0
    for (world, fl, pools, base, spares, nrec, npool), (moff, nmap, *_) in zip(tabs, layout(tabs)[0]):
        out += bytes((world, fl, len(pools))) + struct.pack('<HHHB', base, moff, nmap, len(spares)) + bytes(spares)
        for pl in pools:
            if pl[0] == 'league':
                _, low, slots, areas, order = pl
                assert len(slots) <= 256 and len(areas) <= 255 and sorted(order) == list(range(len(areas)))
                out += bytes((0, len(order), low)) + struct.pack('<H', len(slots))
                for g, b, a in slots:
                    out += struct.pack('<HBB', g, b, a)
                out += bytes(areas)
            else:
                _, key, rel, slots, strength, order, entries = pl
                assert len(slots) <= 255 and len(strength) == len(order) <= 255 and len(entries) <= RO
                out += bytes((1, len(order))) + struct.pack('<HBB', key, rel, len(slots))
                for o, g, s in slots:
                    out += struct.pack('<BHB', o, g, s)
                out += bytes(strength) + bytes((len(entries),)) + b''.join(struct.pack('<H', w) for w in entries)
            out += bytes(order)
            npools += 1
            nq += len(order)
    assert npools <= RP and nq <= RQT, (npools, nq)
    return bytes(out)


def keys_bytes(tabs):
    """RI_OVR_KEYS: RP x dw, each pool's state key (its contest's original first club; 0 = a league pool / none), in
    RI_STATE.ovr's order."""
    ks = [pl[1] if pl[0] == 'state' else 0 for _, _, pools, *_ in tabs for pl in pools]
    return b''.join(struct.pack('<H', k) for k in (ks + [0] * RP)[:RP])


def _asm(nf):
    load, after = [], []
    for k in range(nf):
        load.append(f'''
    cmp byte [SLT + WORLD_BYTE], RI_W{k}    ; file {k}: its world, its team file
    jne .n{k}
    cmp byte [WTPHYS], RI_F{k}
    jne .n{k}
    mov esi, TEAMBUF                    ; the file as read -> its ORIG buffer
    movzx ecx, word [esi]
    xchg cl, ch
    imul ecx, ecx, 684
    add ecx, 2
    cmp ecx, RI_OSZ{k}
    jbe .c{k}
    mov ecx, RI_OSZ{k}
.c{k}:
    mov edi, RI_ORIG{k}
    call ri_copyb
    cmp byte [RI_PLOADED + {k}], 0      ; its RS file, once per DOS session
    jne .a{k}
    mov byte [RI_PLOADED + {k}], 1
    mov esi, D0R                        ; (inside LoadTeamFile: keep the game's pseudo registers D0..A6)
    mov edi, RI_REGS
    mov ecx, 60
    call ri_copyb
    mov dword [A0R], RI_NAME{k}
    mov dword [A1R], RI_POOL{k}
    call LOADFILE
    jz .k{k}
    mov word [RI_POOL{k}], 0            ; (no pool file: no pool records)
.k{k}:
    mov esi, RI_REGS
    mov edi, D0R
    mov ecx, 60
    call ri_copyb
.a{k}:
    push dword RI_MOFF{k}
    push dword {k}
    push dword RI_POOL{k}
    push dword RI_ORIG{k}
    push dword TEAMBUF
    call RI_APPLY
    add esp, 20
    jmp .x
.n{k}:''')
        after.append(f'''
    cmp byte [SLT + WORLD_BYTE], RI_W{k}
    jne .n{k}
    cmp word [RI_ORIG{k}], 0            ; (the file never read: none of its records cached)
    je .n{k}
    push dword RI_MOFF{k}
    push dword {k}
    push dword RI_POOL{k}
    push dword RI_ORIG{k}
    push dword RI_F{k}
    movzx eax, word [NUMSEL]
    push eax
    push dword [SELBASEV]
    call RI_CACHE
    add esp, 28
.n{k}:''')
    names = ''.join(f'RI_NAME{k}: db RI_FNAME{k}, 0\n' for k in range(nf))
    return f'''
ri_load:                                ; replaces `call SetLoadedTeamsGlobalNumbers` after LoadTeamFile read TEAM.nnn
    pushad
    cmp word [GAMETYPE], 4              ; a career
    jne .x
{''.join(load)}
.x:
    popad
    jmp SETGLOBALS

ri_after:                               ; pg_fix, after ri_season and pg_season: the cache, LoadTeamFile's cache
    pushad
{''.join(after)}
    mov word [TEAMSLOADED], 0
    mov byte [LASTEXT], 0FFh
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
RI_SR_PTR: dd 0                         ; statespec's ST_RANK (statecup.py: p.add_ptr on LABELS['RI_SR_PTR']), or 0
RI_PRE_PTR: dd 0                        ; statesim's entry, called by pg_fix before ri_season (statecup.py: add_ptr), or 0
RI_POST_PTR: dd 0                       ; statecup's RI_OVR apply, called by pg_fix after ri_season, or 0
RI_SR_DUMMY: dd 0                       ; (RIPOOL_TEST_SR builds: statespec's ST_RANK pointer lands here, unused)
RI_PLOADED: times {RF} db 0
{names}'''


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


def patch(p, at, bss, tabs):
    """ri_load / ri_after + the table at obj1:at (a page of its own), buffers at obj2:bss (bss_need(tabs));
    tabs = mkseason.off_pools(). Returns (end, the symbols pgroups.patch needs)."""
    import careerworld
    import gplay
    import nasmcave
    import split
    import trailer
    call, loadfile, teambuf, r = _load_site(p)
    setglobals = call + 5 + struct.unpack('<i', bytes(p.get(1, call + 1, 4)))[0]
    s = careerworld.SITES
    sym = {'GAMETYPE': split.sites(p)['GAMETYPE'], 'SLT': s['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'WTPHYS': (1, careerworld.LABELS['WTPHYS']), 'TEAMBUF': teambuf,
           'RI_REGS': (2, bss + layout(tabs)[1] - 0x100), 'D0R': (2, r['D7'] - 28), 'A0R': (2, r['A0']),
           'A1R': (2, r['A0'] + 4), 'LOADFILE': (1, loadfile), 'SETGLOBALS': (1, setglobals),
           'RI_APPLY': gplay.LABELS['ri_apply'], 'RI_CACHE': gplay.LABELS['ri_cache'],
           'NUMSEL': trailer.INFO['NUMSEL'], 'SELBASEV': (1, trailer.INFO['selbasev']),
           'TEAMSLOADED': (2, s['teamsloaded']), 'LASTEXT': s['lastext']}
    names = []
    for k, ((world, fl, *_), (moff, nmap, osz, psz, bo)) in enumerate(zip(tabs, layout(tabs)[0])):
        o = bss + bo
        names.append('data/rs%d%03d.dat' % (world, fl))
        sym.update({f'RI_W{k}': (0, world), f'RI_F{k}': (0, fl), f'RI_ORIG{k}': (2, o), f'RI_OSZ{k}': (0, osz),
                    f'RI_POOL{k}': (2, o + osz), f'RI_MOFF{k}': (0, moff), f'RI_FNAME{k}': (0, '"%s"' % names[-1])})
    src = _asm(len(tabs))
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, call + 1, struct.pack('<i', lab['ri_load'] - (call + 5)))
    LABELS.update(lab)
    tab = (at + len(code) + 15) & ~15           # the table (gplay.c ri_season reads it; pgroups' pg_fix passes it)
    tb = table_bytes(tabs) + bytes(-len(table_bytes(tabs)) % 4) + keys_bytes(tabs)
    p.put(1, tab, tb)
    keys_at = tab + len(tb) - 2 * RP
    LABELS['RI_OVR_KEYS'] = (1, keys_at)
    LABELS['RI_OVR'] = (gplay.LABELS['RI_STATE'][0], gplay.LABELS['RI_STATE'][1] + OVR_AT)
    print(f"exe: off-file pools ({', '.join(names)}: {sum(len(x[2]) for x in tabs)} pools): LoadTeamFile "
          f'obj1+{call:#x} -> ri_load obj1+{at:#x}, table {len(tb)} B, buffers obj2+{bss:#x}')
    import dplay
    ct = dplay._sites(p)[5]                     # careerTeam (obj2), as gplay
    test = os.environ.get('RIPOOL_TEST_SR')     # (harness builds: a fixed ranking in hex, as the 'SR' item)
    if test:
        b = bytes.fromhex(test)
        at_sr = (tab + len(tb) + 15) & ~15
        p.put(1, at_sr, b)
        tb += bytes(at_sr - tab - len(tb)) + b
        p.add_ptr(1, lab['RI_SR_PTR'], 1, at_sr)
        print(f'exe: off-file pools: TEST ranking {test} at obj1+{at_sr:#x}')
    LABELS['RI_SR_PTR'] = (1, lab['RI_SR_DUMMY' if test else 'RI_SR_PTR'])   # (statecup places ST_RANK later: it
                                                # fills this dword; a test ranking keeps its own)
    LABELS['RI_PRE_PTR'] = (1, lab['RI_PRE_PTR'])    # (statesim: every state's ranking before ri_season)
    LABELS['RI_POST_PTR'] = (1, lab['RI_POST_PTR'])  # (statecup: the contest overrides applied after it)
    return (tab + len(tb) + 15) & ~15, {'RI_TAB': (1, tab), 'RI_SEASON': gplay.LABELS['ri_season'],
                                         'RI_MGR': gplay.LABELS['RI_MGR'], 'RI_AFTER': (1, lab['ri_after']),
                                         'CAREERTEAM': (2, ct), 'RI_SR_PTR': (1, lab['RI_SR_PTR']),
                                         'RI_PRE_PTR': (1, lab['RI_PRE_PTR']), 'RI_POST_PTR': (1, lab['RI_POST_PTR'])}
