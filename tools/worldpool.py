"""Per-world foreign market: a career in a historic world loads its own pool file (POOLPLYR.DAT layout: 900 PoolPlayer
records of 58 B = team id, player ordinal, team name 17, PlayerFile 38) instead of the 1996-97 data\\poolplyr.dat.

The game loads the pool once per run (LoadPoolplyrDat: `poolplyrLoaded` set after the first load). Hooks (found by
content on the original bytes; careerworld never touches LoadPoolplyrDat):
  wp_load  replaces `mov ax, [poolplyrLoaded]` at LoadPoolplyrDat's start: the wanted pool = the world's when the game
           type is a career (4) and the save's world byte (someLeaguesTable[1845]) names a world with a pool, else the
           game's own (0); a change of pool clears poolplyrLoaded, so the file is read again.
  wp_name  replaces `mov [A0], offset aDataPoolplyr_d`: the file name of the wanted pool.
Pool files: mkseason.world_files() writes POOLnn.DAT from the root pack's 'pool' field (pack.json, a file in the
pack folder). Pool clubs use pseudo team-file numbers outside the world's files (mkworld_tm: 190+), so the market's
'other country' test always passes; their names come from the pool record.

Pool clubs' team file (4.0 hotfix, 2026-10-23): buying a pool player loads his club (GetTeamPointer -> LoadTeamFile
of file 190), so the world ships that file too (pool_team_file: one record per pool club, a club over 16 players
split into extra ordinals and its pool records renumbered to match, pool_split; guests.py adds it to the world's
namespace, its label and the patcher). SetTeamGlobalNumbers sets a loaded record's global number to
teamsCountryNumbers[file] + ordinal: wp_glob gives every record of file POOL_FILE one global number instead
(guests.alloc: a number the world never uses; w_guest clears its someLeaguesTable byte at the load)."""
import re
import struct

ASM = r'''
wp_load:                                ; LoadPoolplyrDat start (replaces mov ax, [poolplyrLoaded])
    push ebx
    push esi
    xor ebx, ebx
    cmp word [GAMETYPE], 4
    jne .chosen
    mov bl, [SLT + WORLD_BYTE]
    mov esi, WP_TAB
.find:
    cmp byte [esi], 0
    je .none
    cmp bl, [esi]
    je .chosen
    add esi, 5
    jmp .find
.none:
    xor ebx, ebx
.chosen:
    cmp bl, [WP_LAST]                   ; another pool than the one in memory: read the file again
    je .same
    mov [WP_LAST], bl
    mov word [LOADED], 0
.same:
    mov eax, ORIGNAME
    test bl, bl
    jz .set
    mov eax, [esi + 1]
.set:
    mov [WP_NAME], eax
    pop esi
    pop ebx
    mov ax, [LOADED]
    ret

wp_name:                                ; replaces mov [A0], offset aDataPoolplyr_d
    push eax
    mov eax, [WP_NAME]
    mov [A0], eax
    pop eax
    ret

%ifdef POOLG
wp_glob:                                ; SetTeamGlobalNumbers' store (replaces mov esi, [A0]; mov [esi+2], ax)
    mov esi, [A0]
    cmp byte [esi], POOL_FILE
    jne .s
    mov ax, POOLG                       ; the pool clubs' one global number
.s:
    mov [esi+2], ax
    ret
%endif

WP_LAST: db 0
align 4
WP_NAME: dd 0
WP_TAB:
'''


def _sites(p):
    import sacups
    orig = p.le.obj_bytes(1)
    d1 = bytes(p.get(1, 0, len(orig)))
    r = sacups.regs(orig)
    a0 = r['D7'] + 4
    d0 = r['D7'] - 28
    pk = lambda x: re.escape(struct.pack('<I', x))
    ms = [m for m in re.finditer(rb'\x66\xa1(.{4})\x66[\x09\x0b]\xc0\x75.\x66\xc7\x05(.{4})\x01\x00\xc7\x05' + pk(a0)
                                 + rb'(.{4})\xc7\x05' + pk(a0 + 4) + rb'.{4}\xe8', d1, re.S) if m.group(1) == m.group(2)]
    assert len(ms) == 1, ('LoadPoolplyrDat', len(ms))
    m = ms[0]
    # 66 A1 [loaded] | 66 0B C0 | 75 xx | 66 C7 05 [loaded] 01 00 | C7 05 [A0] [name] (at +20) | C7 05 [A1] [buf]
    s = {'load': m.start(), 'name': m.start() + 20, 'loaded': p.target(1, m.start() + 2),
         'orig': p.target(1, m.start() + 26), 'a0': a0}
    # someLeaguesTable: cseg_8CC0A / cseg_8CC4E `mov [D0], 1999; mov [A0], someLeaguesTable; mov [A1], ...`
    sl = {p.target(1, x.start() + 15) for x in re.finditer(rb'\x66\xc7\x05' + pk(d0) + rb'\xcf\x07\xc7\x05' + pk(a0)
                                                            + rb'.{4}\xc7\x05' + pk(a0 + 4), d1, re.S)}
    assert len(sl) == 1, ('someLeaguesTable', sl)
    s['slt'] = sl.pop()
    gt = {p.target(1, x.start() + 14) for x in
          re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d.{4}\x04\x75', orig, re.S)}
    assert len(gt) == 1, ('gameType', gt)
    s['gametype'] = gt.pop()
    # SetTeamGlobalNumbers: mov esi, [A0]; mov [esi+2], ax; add [A0], 684
    ag = re.escape(struct.pack('<I', a0))
    gs = [x.start() for x in re.finditer(rb'\x8b\x35' + ag + rb'\x66\x89\x46\x02\x81\x05' + ag + rb'\xac\x02\x00\x00', d1)]
    assert len(gs) == 1, ('SetTeamGlobalNumbers', gs)
    s['glob'] = gs[0]
    return s


POOL_FILE = 190                         # mkseason.POOL_IDS[0]: the pool clubs' pseudo team file
REC = 58
TEAM_HDR = bytes.fromhex('0000000000010102010002020102')   # record bytes 22..35: tactic 0, plain kits


def pool_split(data):
    """(pool bytes with the records of clubs over 16 players renumbered, [(ordinal, name 17 B, [PlayerFile 38 B])]
    in ordinal order) - for a pool whose records all name file POOL_FILE; None for any other pool."""
    recs = [bytearray(data[i:i + REC]) for i in range(0, len(data), REC)]
    if not recs or any(r[0] != POOL_FILE for r in recs):
        return None
    clubs = {}
    for r in recs:
        clubs.setdefault(r[1], {})[r[2]] = r
    assert sorted(clubs) == list(range(len(clubs))), 'pool club ordinals 0..n-1'
    nxt, out = len(clubs), []
    for o in range(len(clubs)):
        ps = clubs[o]
        assert sorted(ps) == list(range(len(ps))), ('pool club', o, sorted(ps))
        for c in range((len(ps) + 15) // 16):
            ordn = o if c == 0 else nxt
            nxt += c > 0
            chunk = [ps[k] for k in range(16 * c, min(16 * c + 16, len(ps)))]
            for j, r in enumerate(chunk):
                r[1], r[2] = ordn, j
            out.append((ordn, bytes(chunk[0][3:20]), [bytes(r[20:58]) for r in chunk]))
    assert nxt <= 256, nxt
    out.sort()
    return b''.join(recs), out


def pool_team_file(data, glob):
    """TEAM-file bytes (BE count + 684-byte records) of a pool's clubs: name from the pool record, plain kits, lineup
    0..15, its players in slots 0..n-1 and slots n..15 repeating them (the game's records hold 16)."""
    _, clubs = pool_split(data)
    out = bytearray(struct.pack('>H', len(clubs)))
    for i, (ordn, name, ps) in enumerate(clubs):
        assert ordn == i
        r = bytearray(684)
        r[0], r[1] = POOL_FILE, ordn
        struct.pack_into('>H', r, 2, glob)
        r[5:22] = name
        r[22:36] = TEAM_HDR
        r[60:76] = bytes(range(16))
        for j in range(16):
            r[76 + 38 * j:76 + 38 * (j + 1)] = ps[j % len(ps)]
        import mkseason
        r[60:76] = bytes(mkseason.auto_lineup([r[76 + 38 * j + 26] >> 5 for j in range(16)]))
        out += r
    return bytes(out)


def patch(p, cave, nasmcave, pools, glob=None):
    """pools: [(world number, 'POOLnn.DAT')]; glob: the pool clubs' global number when the build ships their team
    file (guests.alloc()[POOL_FILE]). Returns the cave end (nothing done without pools)."""
    import careerworld
    if not pools:
        return cave
    s = _sites(p)
    tab = ''.join(f'    db {n}\n    dd WP_STR_{n}\n' for n, _ in pools) + '    db 0\n'
    strs = ''.join(f'WP_STR_{n}: db "data\\\\{name.lower()}", 0\n' for n, name in pools)
    src = ASM + tab + strs
    if glob is not None:
        src = f'%define POOLG {glob}\n%define POOL_FILE {POOL_FILE}\n' + src
    symbols = {'GAMETYPE': s['gametype'], 'SLT': s['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
               'LOADED': s['loaded'], 'ORIGNAME': s['orig'], 'A0': (2, s['a0'])}
    code, fix = nasmcave.assemble(src, cave, symbols)
    labels = nasmcave.labels(src, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.remove(1, s['load'] + 2)                       # mov ax, [poolplyrLoaded] -> call wp_load; nop
    p.put(1, s['load'], b'\xe8' + struct.pack('<i', labels['wp_load'] - (s['load'] + 5)) + b'\x90')
    p.remove(1, s['name'] + 2)                       # mov [A0], offset name -> call wp_name; 5 x nop
    p.remove(1, s['name'] + 6)
    p.put(1, s['name'], b'\xe8' + struct.pack('<i', labels['wp_name'] - (s['name'] + 5)) + b'\x90' * 5)
    if glob is not None:                             # mov esi, [A0]; mov [esi+2], ax -> call wp_glob; 5 x nop
        g = s['glob']
        p.remove(1, g + 2)
        p.put(1, g, b'\xe8' + struct.pack('<i', labels['wp_glob'] - (g + 5)) + b'\x90' * 5)
        print(f'exe: pool clubs (file {POOL_FILE}): one global number {glob}, SetTeamGlobalNumbers obj1+{g:#x}')
    print(f'exe: world pools {pools}: LoadPoolplyrDat obj1+{s["load"]:#x}, code obj1+{cave:#x}..{cave + len(code):#x}')
    return (cave + len(code) + 3) & ~3
