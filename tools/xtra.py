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

Wages (Davide 2026-10-17, option 3): the extras are paid like the game's reserves (66%) but stay normal players (they
never leave). PlayerFile byte 37 (someFlag) is not free: the game keeps a regular player's form there (signed, read by
cseg_94C7E for his value and wage) and marks trial (9Bh, 33% wage) / reserve (9Ah, 66% wage, may leave or become a
regular) players with it. So the extras are recognised by name instead: the wage routine's `cmp someFlag, 9Ah`
(cseg_5E345) becomes 'reserve, or a name of the managed club's XTRA block' (xtra_wage); the block is cached in xblock
and read again when the managed club or the file name (XTRA_NAMEP, per world) changes, so it works after a .CAR load.
The season's wages (InitializeNewSeason -> cseg_5DEB9) are computed after xtra_load, so the extras start at 66%.
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
    call xtra_read                      ; the club's block -> xblock (eax = players with a name)
    test eax, eax
    jz .out
    mov esi, xblock                     ; -> slots 16..
    mov edi, CT + 684
    mov ecx, [xsize]
    rep movsb
    xor ecx, ecx
.order:
    lea edx, [ecx + 16]
    mov [CMP + 16 + ecx], dl            ; squad order: position 16 + i = slot 16 + i
    inc ecx
    cmp ecx, eax
    jb .order
    add [CNP], ax
    mov [xadded], al
.out:
    popad
    popfd
    ret

xtra_read:                              ; [SEL]'s block of the XTRA file -> xblock, zero-filled; eax = players
    mov word [xteam], -1
    mov edi, xblock
    mov ecx, MAXE_ * PLAYER_
    xor eax, eax
    rep stosb
    mov byte [xcount], 0
    mov eax, [xtra_namep]
    mov [xnamecache], eax
    mov ax, [SEL]
    mov [xteam], ax
    movzx eax, byte [SEL]               ; team file number
    cmp al, 100                         ; CUSTOMS.EDT
    je .none
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
    jc .none
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
    mov edx, xblock
    int 21h
    jc .close
    cmp eax, [xsize]
    jne .close
    movzx ecx, byte [xhead + 2]
    xor eax, eax
    mov edi, xblock + 3                 ; first name byte
.count:
    cmp byte [edi], 0
    je .done
    inc eax
    add edi, PLAYER_
    cmp eax, ecx
    jb .count
.done:
    mov [xcount], al
.close:
    push eax
    mov ah, 3Eh
    int 21h
    pop eax
    movzx eax, byte [xcount]
    ret
.none:
    xor eax, eax
    ret

xtra_reserves:                          ; replaces InitializeNewSeason's call of cseg_64A65 (new club: 10 reserves)
    cmp byte [xadded], 0
    je RESERVES
    mov byte [xadded], 0                ; the club's real players instead of the invented reserves, but cseg_64A65's
    jmp RESTAIL                         ; own tail still runs: cseg_6481C -> cseg_63F6F copies the squad order into
                                        ; trainingMatchSavedPlayers (a sale's cseg_639F9 looks the player up there:
                                        ; left all 0, 'int 3; jmp $' on ACCETTA OFFERTA - TEST 8, 2026-10-21)

xtra_order:                             ; after a career load (engine.after_process, pushfd / pushad around it): a
    movzx ecx, word [CNP]               ; career started before the reserves' fix kept trainingMatchSavedPlayers all 0
    cmp ecx, 2                          ; (every sale trapped in cseg_639F9): when its careerNumPlayers entries are not
    jb .ok                              ; distinct slots < 32, cseg_6481C rebuilds it from currentMatchPlayers, as a
    cmp ecx, 32                         ; new club's season start does; the game's pseudo registers D0..A6 kept
    ja .ok
    xor edx, edx
    xor esi, esi
.l:
    movzx eax, byte [TMSP + esi]
    cmp eax, 32
    jae .fix
    bt edx, eax
    jc .fix
    bts edx, eax
    inc esi
    cmp esi, ecx
    jb .l
.ok:
    ret
.fix:
    mov esi, REGS
    mov edi, xregs
    mov ecx, 15
    rep movsd
    call RESTAIL
    mov esi, xregs
    mov edi, REGS
    mov ecx, 15
    rep movsd
    ret

xtra_wage:                              ; replaces `mov esi, [A0] / cmp byte [esi+71h], 9Ah` in cseg_5E345
    mov esi, [REGS + 32]                ; A0 = the player (- 4Ch)
    cmp byte [esi + 71h], 9Ah           ; reserve: 66%
    je .r
    pushad
    mov ax, [SEL]                       ; the cached block is the managed club's (and the current world's)?
    cmp ax, [xteam]
    jne .reload
    mov eax, [xtra_namep]
    cmp eax, [xnamecache]
    je .cached
.reload:
    call xtra_read
.cached:
    mov byte [xres], 0
    movzx ebp, byte [xcount]
    mov ebx, xblock + 3
.name:
    test ebp, ebp
    jz .end
    mov esi, [REGS + 32]
    add esi, 4Fh                        ; the player's name
    mov edi, ebx
    mov ecx, 23
    repe cmpsb
    je .extra
    add ebx, PLAYER_
    dec ebp
    jmp .name
.extra:
    mov byte [xres], 1
.end:
    popad
    cmp byte [xres], 1                  ; an extra (XTRA): 66% too; he stays a normal player (form, never leaves)
.r:
    ret

align 4
xtra_namep: dd xname                    ; -> 'data\xtra.nnn' (digits at +10..+12); LABELS['XTRA_NAMEP']
xnamecache: dd 0
xsize: dd 0
xteam: dw -1
xname: db 'data\xtra.000', 0
xadded: db 0
xregs: times 15 dd 0
xcount: db 0
xres: db 0
xhead: db 0, 0, 0
align 4
xblock: times MAXE_ * PLAYER_ db 0
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


def reserves_tail(p, reserves):
    """cseg_64A65's last call, cseg_6481C (after its 10 calls of cseg_64B06, the invented reserves): the squad order
    copy into trainingMatchSavedPlayers that xtra_reserves must keep."""
    d1 = p.le.obj_bytes(1)
    calls, i = [], reserves
    while len(calls) < 11 and i < reserves + 0x200:
        if d1[i] == 0xE8:
            calls.append(i + 5 + struct.unpack_from('<i', d1, i + 1)[0])
            i += 5
        else:
            i += 1
    assert len(calls) == 11 and len(set(calls[:10])) == 1 and calls[10] != calls[0], [hex(c) for c in calls]
    return calls[10]


def order_site(p):
    """obj2 offset of trainingMatchSavedPlayers, from cseg_639F9's lookup (mov [A6], offset it; careerNumPlayers; ...
    int 3; jmp $)."""
    d1 = p.le.obj_bytes(1)
    m = [x for x in re.finditer(rb'\xc7\x05(.{4})(.{4})\x66\xa1.{4}\x66\xa3.{4}\x66\x83\x2d.{4}\x01\x8b\x35\1'
                                rb'.{0,40}?\xcc\xeb\xfe', d1, re.S)]
    assert len(m) == 1, m
    return struct.unpack('<I', m[0].group(2))[0]


def wage_sites(p):
    """(site of `mov esi, [A0] / cmp byte [esi+71h], 9Ah` in cseg_5E345, cseg_5E345, D0 = the pseudo registers' base)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['A0']
    w = [m.start() for m in re.finditer(rb'\x8b\x35' + re.escape(struct.pack('<I', a0)) +
                                       rb'\x80\x7e\x71\x9a\x75.\x66\xa1....\x66\xbb\x42\x00', d1, re.S)]
    assert len(w) == 1, w
    _, cnp, *_ = sites(p)
    fn = []                                        # cseg_5DEB9: mov ax,[careerNumPlayers] ... call GetPlayerAtIndex;
    for m in re.finditer(rb'\x66\xa1' + re.escape(struct.pack('<I', cnp)) + rb'\x66\xa3....\x66\x83\x2d', d1, re.S):
        calls = [m.start() + c.start() + 5 + struct.unpack('<i', c.group(1))[0]   # call cseg_5E345 (the wage routine)
                 for c in re.finditer(rb'\xe8(....)', d1[m.start():m.start() + 0x60], re.S)]
        fn += [t for t in calls[1:2] if t < w[0] < t + 0x200]
    assert len(set(fn)) == 1, fn
    return w[0], fn[0], r['D7'] - 28


def wage_table(p):
    """obj2 offset of the managed club's wage table (dseg_D6BA6, one dword per slot): the first `mov [A0], table`
    after the wage site of cseg_5E345 (original exe, or a built one where the site calls xtra_wage)."""
    d1 = p.get(1, 0, len(p.le.obj_bytes(1)))
    m = [x.start() for x in re.finditer(rb'\xe8....\x90{5}\x75.\x66\xa1....\x66\xbb\x42\x00', d1, re.S)]
    if m:                                          # built exe: xtra_wage starts with mov esi, [A0]
        ws = m[0]
        stub = ws + 5 + struct.unpack('<i', d1[ws + 1:ws + 5])[0]
        a0 = p.target(1, stub + 2)[1]
    else:
        import sacups
        ws, _, _ = wage_sites(p)
        a0 = sacups.regs(d1)['A0']
    t = [x.start() for x in re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', a0)), d1[ws:ws + 0x200])]
    assert t, 'wage table'
    return p.target(1, ws + t[0] + 6)[1]


def patch(p, at):
    """Code at obj1:at; returns the code end."""
    s, cnp, ct, cmp, sel = sites(p)
    rs, reserves = reserves_site(p)
    tail = reserves_tail(p, reserves)
    tmsp = order_site(p)
    ws, wage, regs = wage_sites(p)
    at = (at + 15) & ~15
    sym = {'CNP': (2, cnp), 'CT': (2, ct), 'CMP': (2, cmp), 'SEL': (2, sel), 'RESERVES': (1, reserves), 'RESTAIL': (1, tail), 'TMSP': (2, tmsp),
           'WAGE': (1, wage), 'REGS': (2, regs), 'PLAYER_': (0, PLAYER), 'MAXE_': (0, MAX_EXTRA)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    LABELS['XTRA_NAMEP'] = lab['xtra_namep']
    import engine                                       # (the old saves' squad order after every career load:
    engine.CALL_AT['xtra_order'] = (1, lab['xtra_order'])   # patch.py registers it before trailer.patch)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.remove(1, s + 3)
    p.put(1, s, b'\xE8' + struct.pack('<i', lab['xtra_load'] - (s + 5)) + b'\x90' * 4)
    p.put(1, rs, b'\xE8' + struct.pack('<i', lab['xtra_reserves'] - (rs + 5)))      # relative call: no fixup
    p.remove(1, ws + 2)                                                               # mov esi, [A0]
    p.put(1, ws, b'\xE8' + struct.pack('<i', lab['xtra_wage'] - (ws + 5)) + b'\x90' * 5)
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
