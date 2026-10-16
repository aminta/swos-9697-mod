"""Extended career squads: the managed club starts with the players of DATA\\XTRA.nnn beyond the 16 of its record.

The managed club of a career has 32 player slots (careerTeam = 684-byte record + 16 more PlayerFile, saved in the
.CAR fixed part); the game fills only the 16 of the record. cseg_5DB56 (new career from InitCareer, new job from
cseg_942F2) is the only place that loads the club: it copies the record, the record's playerNumbers into
currentMatchPlayers and sets careerNumPlayers = 16. The hook replaces that last store: after it, the club's block of
XTRA.nnn (nnn = team file = low byte of the team number) is read straight into slots 16.., every player with a name
is appended to the squad order and counted. Wages follow by themselves (InitializeNewSeason -> cseg_5DEB9 computes
them for all careerNumPlayers players). A .CAR load or a season start never runs cseg_5DB56: nothing is added twice.

The 'fake' players: for a new club (stayingInOldClub == 0) InitializeNewSeason calls cseg_64A65, which invents 10
reserves (positions LB RB LW RW D D M M A A, random names, flag 154) -> 26 players. The real ones replace them: when
XTRA added players, that call is skipped once (else 25 + 10 would overrun the 32 slots and the variables after
careerTeam). Mid-season trial players (CheckPlayersLeavingComing -> AddTrialPlayer, while careerNumPlayers < 30) stay.

XTRA.nnn: word (big endian) k = clubs (as the team file), byte E = players per block (1..16), then k blocks of
E x 38 bytes (PlayerFile, as in a record); block i = the club with ordinal i in TEAM.nnn; empty name = no player
(the players of a block come first). No file, an ordinal >= k or a bad header: the squad stays at 16.
"""
import re
import struct

import nasmcave

PLAYER = 38
MAX_EXTRA = 16                         # 16 + 16 = the 32 slots of careerTeam
LABELS = {}                            # obj1 offsets after patch(): XTRA_NAMEP = the dd holding the file name's address

ASM = r"""
xtra_load:
    mov word [CNP], 16                  ; the instruction the call replaces
    mov byte [xadded], 0
    pushfd
    pushad
    movzx eax, byte [SEL]               ; team file number
    cmp al, 100                         ; CUSTOMS.EDT
    je .out
    mov edi, [xtra_namep]               ; the file name (another session may point it at a per-world name)
    xor edx, edx
    mov ecx, 100
    div ecx
    add al, '0'
    mov [edi + 10], al
    mov eax, edx
    mov cl, 10
    div cl                              ; al = tens, ah = units
    add ax, 3030h
    mov [edi + 11], ax
    mov ax, 3D00h                       ; open, read only
    mov edx, edi
    int 21h
    jc .out
    movzx ebx, ax
    mov ah, 3Fh
    mov ecx, 3
    mov edx, xhead
    int 21h
    jc .close
    cmp eax, 3
    jne .close
    movzx ecx, byte [xhead + 2]         ; E
    test ecx, ecx
    jz .close
    cmp ecx, MAXE_
    ja .close
    movzx eax, word [xhead]
    xchg al, ah                         ; k (big endian)
    movzx esi, byte [SEL + 1]           ; the club's ordinal
    cmp esi, eax
    jae .close
    imul ecx, ecx, PLAYER_
    mov [xsize], ecx
    imul esi, ecx
    add esi, 3
    mov edx, esi
    shr esi, 16
    mov ecx, esi                        ; cx:dx = 3 + ordinal * E * 38
    mov ax, 4200h
    int 21h
    jc .close
    mov ah, 3Fh
    mov ecx, [xsize]
    mov edx, CT + 684
    int 21h
    jc .close
    cmp eax, [xsize]
    jne .close
    movzx ecx, byte [xhead + 2]
    xor eax, eax
    mov edi, CT + 684 + 3               ; first name byte of slot 16
.count:
    cmp byte [edi], 0
    je .done
    lea edx, [eax + 16]
    mov [CMP + 16 + eax], dl            ; squad order: position 16 + i = slot 16 + i
    inc eax
    add edi, PLAYER_
    cmp eax, ecx
    jb .count
.done:
    add [CNP], ax
    mov [xadded], al
.close:
    mov ah, 3Eh
    int 21h
.out:
    popad
    popfd
    ret

xtra_reserves:                          ; replaces InitializeNewSeason's call of cseg_64A65 (new club: 10 reserves)
    cmp byte [xadded], 0
    je RESERVES
    mov byte [xadded], 0                ; the club's real players instead of the invented reserves
    ret

align 4
xtra_namep: dd xname                    ; -> 'data\xtra.nnn' (digits at +10..+12); LABELS['XTRA_NAMEP']
xname: db 'data\xtra.000', 0
xadded: db 0
xhead: db 0, 0, 0
align 4
xsize: dd 0
"""


def sites(p):
    """(site of `mov word [careerNumPlayers], 16` in cseg_5DB56, careerNumPlayers, careerTeam, currentMatchPlayers,
    selTeamNumber) as obj2 offsets."""
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'(?:\x66\xC7\x05....\x10\x00|\xE8....\x90{4})\x66\xC7\x05....\x00\x00'
                                        rb'\xC7\x05....\x00\x00\x00\x00', d1, re.S)]
    assert len(m) == 1, m
    s = m[0]                                       # original exe, or a patched one (call xtra_load: same store first)
    at = s + 5 + struct.unpack('<i', d1[s + 1:s + 5])[0] if d1[s] == 0xE8 else s
    def t(o):
        try:
            return p.target(1, o)
        except AssertionError:                     # no fixup there
            return None
    obj, cnp = t(at + 3)
    assert obj == 2
    ct, cmp = cnp - 1292, cnp - 1324
    # the record copy and the squad order load before it: mov [A1], offset careerTeam / offset currentMatchPlayers
    near = [t(o) for o in range(s - 0x120, s) if t(o)]
    assert (2, ct) in near and (2, cmp) in near, 'careerTeam / currentMatchPlayers'
    # mov selTeamNumber, ax (66 A3) after the GetTeamPointer call; the same variable is read back (66 A1) later
    sel = [t(o + 2)[1] for o in range(s - 0x120, s) if d1[o:o + 2] == b'\x66\xA3' and t(o + 2)
           and t(o + 2)[0] == 2 and any(d1[q:q + 2] == b'\x66\xA1' and t(q + 2) == t(o + 2)
                                        for q in range(o + 6, s))]
    assert len(set(sel)) == 1, sel
    return s, cnp, ct, cmp, sel[0]


def hooked(p):
    """True when the exe already calls xtra_load (a build with the hook)."""
    return p.le.obj_bytes(1)[sites(p)[0]] == 0xE8


def reserves_site(p):
    """(site, target) of InitializeNewSeason's `call cseg_64A65` (the 10 invented reserves of a new club)."""
    d1 = p.le.obj_bytes(1)
    pos = b''.join(rb'\x66\xC7\x05....' + bytes((n, 0)) + rb'\xE8....' for n in (2, 1, 5, 4, 3, 3, 6, 6, 7, 7))
    f = [m.start() for m in re.finditer(pos, d1, re.S)]
    assert len(f) == 1, f
    calls = [(m.start() + 5, m.start() + 10 + struct.unpack('<i', m.group(1))[0])     # or ax, ax / jnz / call
             for m in re.finditer(rb'\x66\x0B\xC0\x75\x15\xE8(....)', d1, re.S)]
    calls = [(c, t) for c, t in calls if f[0] - 0x20 <= t <= f[0]]
    assert len(calls) == 1, calls
    return calls[0]


def patch(p, at):
    """Code at obj1:at; returns the code end."""
    s, cnp, ct, cmp, sel = sites(p)
    rs, reserves = reserves_site(p)
    at = (at + 15) & ~15
    sym = {'CNP': (2, cnp), 'CT': (2, ct), 'CMP': (2, cmp), 'SEL': (2, sel), 'RESERVES': (1, reserves),
           'PLAYER_': (0, PLAYER), 'MAXE_': (0, MAX_EXTRA)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    LABELS['XTRA_NAMEP'] = lab['xtra_namep']
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, s + 3)
    p.put(1, s, b'\xE8' + struct.pack('<i', lab['xtra_load'] - (s + 5)) + b'\x90' * 4)
    p.put(1, rs, b'\xE8' + struct.pack('<i', lab['xtra_reserves'] - (rs + 5)))      # relative call: no fixup
    print(f'exe: extended career squads (DATA\\XTRA.nnn) at obj1+{s:#x}, code obj1+{at:#x}, {len(code)} B')
    return at + len(code)


def build(blocks, k, extra):
    """XTRA file bytes: blocks = {ordinal: [38-byte players]}, k = clubs of the team file, extra = players per block."""
    assert 1 <= extra <= MAX_EXTRA
    out = bytearray(struct.pack('>HB', k, extra))
    for i in range(k):
        pl = blocks.get(i, [])
        assert len(pl) <= extra and all(len(x) == PLAYER and x[3] for x in pl), i
        out += b''.join(pl) + bytes(PLAYER * (extra - len(pl)))
    return bytes(out)


def read(data):
    """{ordinal: [players]} of an XTRA file (tests, tools)."""
    k, e = struct.unpack_from('>HB', data)
    out = {}
    for i in range(k):
        b = data[3 + i * e * PLAYER:3 + (i + 1) * e * PLAYER]
        pl = [b[j * PLAYER:(j + 1) * PLAYER] for j in range(e)]
        out[i] = [x for x in pl if x[3]]
    return out
