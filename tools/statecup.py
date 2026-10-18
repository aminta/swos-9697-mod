"""State championships (a club's own regional competition next to its league) on the game's DIY group engine, in
career / Season slot 1 (package 6; the Brazilian estaduais: 4.0's World 2026-27, 4.1's 1996-97 world).

Facts (notes/state-championships-design.md on v4.0-worldphases, probes 1-3 and the season tests):
- Career slots 1 and 3 have the big 0xB52 buffer a type-2 (groups + knockout) contest needs; slots 2 and 4 0x443.
- cseg_8B2D3 (slot set-up) refuses type 2 in slots 1-2 (national teams only) and cseg_3C4CE (after each match) treats
  slots 1-2 as knockouts: slot_types() lets slot 1-2 contests of type 2 through; the gate after each match sends
  anything but a knockout to the slot-3 path (a group stage runs with the DIY league layout: type word 0).
- cseg_91857 (the season end's national cup: finish / simulate, winner to the CWC list) traps on a non-knockout cup:
  cup_end_types() makes it return.
- The slot-1 contest is the country's cup 1 (competitionsTable [leagues, -2, cup 1, cup 2, -1]); pick() replaces it, at
  the slot-1 set-up (career: the career club; STAGIONE: the first club not the computer's) and at a career load (by
  the saved slot-1 id), by the club's own state contest; a club outside every state gets cup 2 in slot 1 (slot 2 then
  empty), or no slot-1 contest at all when there is no cup 2.

Use (before patch_exe sizes its pages: at import of the caller's module):
    statecup.register(world, cup1_id, team_file, states)
        states = [{'id': contest id, 'members': [team-file ordinals choosing it], 'struct': obj1 offset or None}]
    statecup.contest_bytes(...)   -> a type-2 struct (the Champions Cup layout) for the caller to place
and in patch_exe: statecup.set_struct(world, id, (obj, off)) once a contest is placed, then statecup.patch(p, at)
(after sacups.patch: its career symbols) and statecup.slot_types / cup_end_types (idempotent, natcups may have run).
A world entry is recognised at run time by the running world byte (career: someLeaguesTable + WORLD_BYTE; else 0) and
the cup's id byte (ids are unique per world), never by the struct pointer (careerworld's w_swap copies the lists).
"""
import re
import struct

ENTRIES = []            # {world, cup1, file, states: [{'id', 'members', 'struct'}]}
TEAM = 684


def register(world, cup1_id, team_file, states):
    for e in ENTRIES:
        assert (e['world'], e['cup1']) != (world, cup1_id), (world, cup1_id)
    ENTRIES.append({'world': world, 'cup1': cup1_id, 'file': team_file, 'states': [dict(s) for s in states]})


def set_struct(world, contest_id, at):
    """at = (obj, offset) of a registered state contest's struct."""
    for e in ENTRIES:
        for s in e['states']:
            if e['world'] == world and s['id'] == contest_id:
                s['struct'] = at
                return
    raise KeyError((world, contest_id))


def contest_bytes(cc_header, cid, team_file, months, meetings, points, stages, stage_bytes, clubs, names):
    """A type-2 contest: cc_header = the Champions Cup's first 0x27 bytes (sacups.EUROCUP_HDR's struct); stages =
    [(groups, clubs per group, qualifiers), ...] after the first stage's club count; stage_bytes = one per stage at
    +22h (0 groups, 0x14 / 0x94 knockout single / two legs); clubs = [(file, ordinal)] (a fixed list); names = 8 bytes
    (two string offsets from sacups.STR_BASE)."""
    h = bytearray(cc_header[:0x27])
    h[0], h[2] = cid, team_file
    h[3], h[4] = months
    h[5], h[7], h[8], h[9], h[10] = 0x22, 0x28, 1, 0, 0     # names at +27h, team list at +2Fh (fixed), no seeding,
    h[11], h[12] = meetings, points                         # no away goals; meetings per pair in a group, points
    st = [len(stages), len(clubs)] + [x for s in stages for x in s]
    assert len(st) <= 0x22 - 0x0E and len(stage_bytes) == len(stages) <= 5, (st, stage_bytes)
    h[0x0E:0x22] = bytes(st) + bytes(0x22 - 0x0E - len(st))
    h[0x22:0x27] = bytes(stage_bytes) + bytes(5 - len(stage_bytes))
    assert len(names) == 8
    return bytes(h) + names + b''.join(bytes(c) for c in clubs)


PICK_ASM = r'''
; sc_pick: replaces `mov esi, [A6]; mov eax, [esi]` (A6 = the country's competitionsTable entry at its cup 1) at three
; sites: the slot-1 set-up of InitNewSeason (STAGIONE) and InitializeNewSeason (career), and ProcessCareerFile's
; slot-1 pointer (career load). A registered cup 1 (running world + its id) becomes the club's state contest, or cup 2
; (slot 2 then skipped), or no slot-1 contest at all.
sc_pick:
    mov esi, [A6]
    mov eax, [esi]
    cmp eax, -1
    je .r
    pushad
    xor ecx, ecx                        ; the running world: 0, or the career's world byte
    cmp word [GAMETYPE], 4
    jne .w
    mov cl, [SLT + WORLD_BYTE]
.w:
    mov dl, [eax]                       ; the cup's id
    mov edi, ENT
.e:
    cmp byte [edi], 0FFh
    je .none
    cmp [edi], cl
    jne .en
    cmp [edi + 1], dl
    je .found
.en:
    movzx ebx, word [edi + 6]           ; entry length
    add edi, ebx
    jmp .e
.none:
    popad
.r:
    ret
.found:                                 ; edi = entry: +0 world, +1 cup-1 id, +2 file, +3 states, +4 word records,
    mov ebx, [esp + 32]                 ; +6 word length, +8 map (records bytes), then states x (db id, dd struct)
    mov dl, 0FFh
    cmp ebx, SITE_LOAD
    je .load
    cmp ebx, SITE_SEASON
    je .season
    mov ax, [SEL]                       ; career: the manager's club
    call .state
    jmp .chosen
.season:                                ; STAGIONE: the first club not the computer's of this file (none: cup 1)
    mov esi, [SELPTR]
    movzx ecx, word [NSEL]
    mov dl, 0
    jecxz .chosen
.s:
    cmp byte [esi + 4], 1
    je .sn
    mov ax, [esi]
    cmp al, [edi + 2]
    jne .sn
    call .state
    jmp .chosen
.sn:
    add esi, TEAM_
    loop .s
    jmp .chosen
.load:                                  ; career load: by the slot-1 contest's id
    mov al, [SLOT1 + 2Dh]
    movzx ecx, byte [edi + 3]
    movzx edx, word [edi + 4]
    lea esi, [edi + 8 + edx]
    xor edx, edx
.l:
    cmp edx, ecx
    jae .lx
    cmp al, [esi]
    je .chosen
    add esi, 5
    inc edx
    jmp .l
.lx:
    mov dl, 0FFh
    test al, al
    jz .skip
.chosen:
    cmp dl, [edi + 3]
    jae .other
    movzx edx, dl
    lea edx, [edx + edx * 4]
    movzx ecx, word [edi + 4]
    add edx, ecx
    mov eax, [edi + 8 + edx + 1]        ; (the state's struct: after the map, 5 bytes per state)
    mov [esp + 28], eax
    popad
    ret
.other:                                 ; outside every state: cup 2 in slot 1, slot 2 skipped; none: no slot 1
    mov esi, [esp + 4]
    mov eax, [esi + 4]
    cmp eax, -1
    je .skip
    mov [esp + 28], eax
    add dword [A6], 4
    popad
    ret
.skip:
    popad
    cmp dword [esp], SITE_CAREER
    jne .s2
    add esp, 4 + 6                      ; (the career site saved three words first)
    jmp EXIT_CAREER
.s2:
    cmp dword [esp], SITE_SEASON
    jne .s3
    add esp, 4
    jmp EXIT_SEASON
.s3:
    add esp, 4
    jmp EXIT_LOAD
.state:                                 ; ax = club word (file, ordinal), edi = entry -> dl = its state, FF none
    mov dl, 0FFh
    cmp al, [edi + 2]
    jne .sr
    movzx eax, ah
    cmp ax, [edi + 4]
    jae .sr
    mov dl, [edi + 8 + eax]
.sr:
    ret
'''


def _table():
    """The entries as nasm source (absolute struct pointers: obj-tagged symbols)."""
    lines, syms = ['ENT:'], {}
    for i, e in enumerate(ENTRIES):
        nrec = max([m for s in e['states'] for m in s['members']] + [0]) + 1
        state = {m: k for k, s in enumerate(e['states']) for m in s['members']}
        ln = 8 + nrec + 5 * len(e['states'])
        lines.append(f"    db {e['world']}, {e['cup1']}, {e['file']}, {len(e['states'])}")
        lines.append(f'    dw {nrec}, {ln}')
        lines.append('    db ' + ', '.join(str(state.get(k, 255)) for k in range(nrec)))
        for k, s in enumerate(e['states']):
            assert s.get('struct'), (e['world'], s['id'])
            syms[f'SC{i}_{k}'] = s['struct']
            lines.append(f"    db {s['id']}\n    dd SC{i}_{k}")
    lines.append('    db 0FFh')
    return '\n'.join(lines), syms


def sites(p):
    """The three sites, their exits and the symbols the picker needs."""
    import sacups
    d1 = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d1)
    a0, d0 = r['A0'], r['D7'] - 28
    a6 = a0 + 24
    A6, A0, D0 = (re.escape(struct.pack('<I', x)) for x in (a6, a0, d0))
    build = [m.start() for m in re.finditer(rb'\x8b\x35' + A6 + rb'\x8b\x06\x83\x05' + A6 + rb'\x04\xa3' + A0 +
                                            rb'\x66\xc7\x05' + D0 + rb'\x01\x00', d1)]
    load = [m.start() for m in re.finditer(rb'\x8b\x35' + A6 + rb'\x8b\x06\x83\x05' + A6 + rb'\x04\xa3.{4}\x8b\x35' +
                                           A6 + rb'\x83\x3e\xff\x74', d1, re.S)]
    assert len(build) == 2 and len(load) == 1, (build, load)
    season, career = build                                      # (InitNewSeason comes first in obj1)
    load = load[0]
    assert d1[season - 6] == 0x74 and d1[season - 4:season] == b'\x90' * 4
    assert d1[career - 27:career - 25] == b'\x0f\x84' and d1[career - 21:career - 18] == b'\x66\xff\x35'
    assert d1[load - 2] == 0x74
    m = re.search(rb'\x66\xa1(.{4})\x66\xa3' + D0 + rb'\x66\x83\x2d' + D0 + rb'\x01\xa1(.{4})\xa3' + A0,
                  d1[season:season + 0x200], re.S)
    nsel, selptr = (struct.unpack('<I', g)[0] for g in m.groups())
    slot1 = struct.unpack_from('<I', d1, career - 18)[0] - 0x3D  # (push word [slot1 + 3Dh] x3 before the career site)
    return dict(season=season, career=career, load=load, a6=a6, nsel=nsel, selptr=selptr, slot1=slot1,
                exit_season=season - 4 + d1[season - 5],
                exit_career=career - 21 + struct.unpack_from('<i', d1, career - 25)[0],
                exit_load=load + d1[load - 1])


def patch(p, at):
    """sc_pick + the entries' table at obj1 at (after sacups.patch). Returns the end."""
    import careerworld
    import nasmcave
    import sacups
    import split
    if not ENTRIES:
        return at
    s = sites(p)
    tab, tsyms = _table()
    sym = {'A6': (2, s['a6']), 'SEL': (2, sacups.SEL_ADDR[0]), 'SLOT1': (2, s['slot1']), 'NSEL': (2, s['nsel']),
           'SELPTR': (2, s['selptr']), 'SITE_LOAD': (1, s['load'] + 5), 'SITE_SEASON': (1, s['season'] + 5),
           'SITE_CAREER': (1, s['career'] + 5), 'EXIT_CAREER': (1, s['exit_career']),
           'EXIT_SEASON': (1, s['exit_season']), 'EXIT_LOAD': (1, s['exit_load']), 'TEAM_': (0, TEAM),
           'GAMETYPE': split.sites(p)['GAMETYPE'], 'SLT': careerworld.SITES['slt'],
           'WORLD_BYTE': (0, careerworld.WORLD_BYTE), **tsyms}
    src = PICK_ASM + tab + '\n'
    code, fix = nasmcave.assemble(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    for site in (s['season'], s['career'], s['load']):
        p.remove(1, site + 2)                                    # (mov esi, [A6]: its fixup)
        p.put(1, site, b'\xe8' + struct.pack('<i', at - (site + 5)) + b'\x90' * 3)
    print(f'exe: state championships: sc_pick obj1+{at:#x} ({len(ENTRIES)} entries) at STAGIONE '
          f'obj1+{s["season"]:#x}, career obj1+{s["career"]:#x}, load obj1+{s["load"]:#x}')
    return (at + len(code) + 15) & ~15


SLOT_TEST = (b'\x01\x0f\x85', b'\x00\x0f\x84')     # cseg_8B2D3: cmp byte [esi+1], 1; jnz -> cmp ..., 0; jz
GATE = """
gate:                                   ; a knockout (type 1): as before; anything else = the slot-3 path (a type-2
    mov esi, [A3]                       ; contest's group stage runs with the DIY league layout: word 0 = 0)
    cmp word [esi], 1
    je BACK
    jmp SLOT3
"""


def slot_types(p, at):
    """Career slots 1-2 take type-2 contests (the same change as package 7's natcups.slot_types: skipped when it has
    already been made; any other form of the two sites is an error)."""
    import nasmcave
    import sacups
    d1 = bytes(p.le.obj_bytes(1))
    a0 = sacups.regs(d1)['A0']
    pre = re.escape(b'\x8b\x35' + struct.pack('<I', a0)) + rb'\x80\x7e\x01'
    orig = [x.start() for x in re.finditer(pre + rb'\x01\x0f\x85(.{4})\xeb', d1, re.S)]
    if len(orig) == 2:                                           # slots 1-2's test, then slot 4's
        k = orig[0]
    else:                                                        # (slots 1-2's already patched: just before slot 4's)
        assert len(orig) == 1, [hex(x) for x in orig]
        near = [x.start() for x in re.finditer(pre + rb'\x00\x0f\x84(.{4})\xeb', d1[orig[0] - 0x20:orig[0]], re.S)]
        assert len(near) == 1, near
        k = orig[0] - 0x20 + near[0]
    cur = bytes(p.get(1, k + 9, 3))
    assert cur in SLOT_TEST, cur.hex()
    tgt = {}
    for slot in (1, 2, 3):
        x = [y.start() for y in re.finditer(rb'\x66\x83\x7e\x2b' + bytes([slot]) + rb'\x0f\x84', d1)]
        assert len(x) == 1, (slot, x)
        tgt[slot] = x[0] + 11 + struct.unpack_from('<i', d1, x[0] + 7)[0]
    g = tgt[1] + 5
    gcur = bytes(p.get(1, g, 15))
    if cur == SLOT_TEST[1]:                                      # natcups (or we) did it already: the gate must be
        assert gcur[0] == 0xE9 and gcur[5:] == b'\x90' * 10, gcur.hex()   # a jump out
        return at
    assert gcur[6:] == b'\x66\x83\x3e\x01\x74\x03\xcc\xeb\xfe', gcur.hex()
    a3 = struct.unpack_from('<I', d1, g + 2)[0]
    p.put(1, k + 9, SLOT_TEST[1])
    code, fix = nasmcave.assemble(GATE, at, {'A3': (2, a3), 'BACK': (1, g + 15), 'SLOT3': (1, tgt[3])})
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.remove(1, g + 2)
    p.put(1, g, b'\xe9' + struct.pack('<i', at - (g + 5)) + b'\x90' * 10)
    print(f'exe: career slots 1-2 take group contests (statecup; obj1+{k:#x}, gate obj1+{g:#x})')
    return (at + len(code) + 3) & ~3


def cup_end_types(p):
    """cseg_91857 (the season end's national cup) returns for a cup that is not a knockout (its jnz to the 'ret'
    just before its int 3). Idempotent (natcups makes the same change)."""
    d1 = bytes(p.le.obj_bytes(1))
    m = [x.start() for x in re.finditer(rb'\xc3\xcc\xeb\xfe\x8b\x35.{4}\x80\x7e\x01\x01\x75[\xf0\xf1]\xa1', d1, re.S)]
    assert len(m) == 1, [hex(x) for x in m]
    k = m[0] + 15                       # ret, int 3, jmp $ (4); mov esi, [A4] (6); cmp byte [esi+1], 1 (4); jnz (75)
    cur = bytes(p.get(1, k, 1))[0]
    assert cur in (0xF0, 0xF1), hex(cur)
    if cur == 0xF1:
        p.put(1, k, b'\xf0')
    print(f'exe: season-end national cup: a non-knockout cup returns (statecup, obj1+{k - 1:#x})')


# --- self-test (STATECUP_TEST=1 builds only): world 0's Brazil gets a test state contest as its cup 1 ---------------
import os
TEST = os.environ.get('STATECUP_TEST') == '1'
TEST_ID, TEST_FILE = 0xF1, 46           # (0xF1: free in world 0)
if TEST:
    register(0, TEST_ID, TEST_FILE, [{'id': TEST_ID, 'members': list(range(24)), 'struct': None}])


def test_contest(p, at):
    """The test contest (1 group of 16 Brazilian clubs, single round robin, January - June) at obj1 at and Brazil's
    competitionsTable entry [league, -2, it, -1] (world 0). Returns the end."""
    import countries
    import sacups
    d2 = p.le.obj_bytes(2)
    cc = bytes(d2[sacups.unique(d2, sacups.EUROCUP_HDR):][:0x27])
    sup = sacups.NAME_SITES[1][1] if len(sacups.NAME_SITES) > 1 else None   # (reuse the Supercopa's name offsets)
    names = bytes(p.get(1, sup, 8)) if sup else bytes(8)
    body = contest_bytes(cc, TEST_ID, TEST_FILE, (0x00, 0x28), 1, 3, [(1, 16, 1)], [0],
                         [(TEST_FILE, i) for i in range(16)], names)
    p.put(1, at, body)
    set_struct(0, TEST_ID, (1, at))
    comp = countries.COMP[0]
    tobj, t = p.target(2, comp + 4 * TEST_FILE)
    league = p.target(tobj, t)
    tab = (at + len(body) + 3) & ~3
    p.add_ptr(1, tab, *league)
    p.put(1, tab + 4, struct.pack('<i', -2))
    p.add_ptr(1, tab + 8, 1, at)
    p.put(1, tab + 12, struct.pack('<i', -1))
    p.retarget(2, comp + 4 * TEST_FILE, 1, tab)
    p.put(2, comp + 4 * TEST_FILE, struct.pack('<I', tab))
    print(f'exe: statecup TEST: Brazil cup 1 = test contest {TEST_ID:#x} (16 clubs) obj1+{at:#x}')
    return tab + 16
