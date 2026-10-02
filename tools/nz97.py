"""New Zealand 1996-97 (session 28g, for 2.1): National Summer Soccer League + three regional divisions of 10.

Sources (fetched 2026-10-02): en.wikipedia "1996-97 National Summer Soccer League" (format, table, play-offs); The Ultimate New
Zealand Soccer Website by Jeremy Ruane (ultimatenzsoccer.com, NZClubSoccer: 1996-7 National Summer League results, 1996 Northern,
Central and Southern League tables; Wayback copies in internal/nz9697).
- NSSL 1996-97 (Nov 1996 - Apr 1997): 10 invited clubs, home and away, 4 points a win, 1 a draw (+1 to the winner of the
  shoot-out after every draw: nz97 shoot-out code, later), top 4 to the play-offs. All 10 are SWOS clubs (two renamed).
- NORTHERN / CENTRAL / SOUTHERN: the 20 other SWOS clubs (all kept) + the best 1996 clubs SWOS lacks: Northern League 1996
  champion Lynn-Avon United and Blockhouse Bay, Fencibles United, Ngaruawahia United, Papakura City; Central League 1996
  champion Western Suburbs and North Wellington, Gisborne City, Tararua United; Southern League 1996 Div One North champion
  Northern Hearts (Davide's pick). Their squads and coaches are INVENTED (no source); kits are those of the template club.
- Global numbers: NZ needs 40 -> moves to the free run 1960..1999; Bolivia (moved there for Australia, see nsl97) goes to NZ's
  old 1248..1261.
"""
import random, struct

FILE = 62
TEAM_SIZE = 684
NZL = 149                       # nationality byte of the New Zealand players
BASE = 1960
NSSL, NORTH, CENTRAL, SOUTH = 0, 1, 2, 3

# SWOS record index -> (new division, new name or None)
CLUBS = {
    0: (SOUTH, None),                       # Burnside
    1: (NSSL, None),                        # Central United
    2: (SOUTH, None), 3: (SOUTH, None), 4: (SOUTH, None), 5: (SOUTH, None), 6: (SOUTH, None),
    7: (CENTRAL, None),                     # Lower Hutt City
    8: (NORTH, None),                       # Manurewa
    9: (NSSL, None),                        # Miramar Rangers
    10: (NORTH, None),                      # Mount Albert
    11: (NSSL, 'MT. MAUNGANUI'),            # SWOS: MOUNT MANGANUI (typo)
    12: (NORTH, None),                      # Mount Wellington
    13: (NSSL, 'NAPIER CITY ROV.'),
    14: (NSSL, None),                       # Nelson Suburbs
    15: (CENTRAL, None),                    # New Plymouth
    16: (NSSL, None),                       # North Shore United
    17: (NORTH, None), 18: (NORTH, None),   # Oratia United, Papatoetoe
    19: (CENTRAL, None),                    # Petone
    20: (SOUTH, None), 21: (SOUTH, None),   # Rangers, Roslyn Wakari
    22: (NSSL, 'MELVILLE UNITED'),          # SWOS: WAIKATO UNITED (its name until 1995)
    23: (NSSL, None),                       # Waitakere City
    24: (CENTRAL, None), 25: (CENTRAL, None), 26: (CENTRAL, None),   # Wanganui East, Waterside Karori, Wellington Olympic
    27: (NSSL, None),                       # Wellington United
    28: (SOUTH, None),                      # Western
    29: (NSSL, None),                       # Woolston WMC
}
# new clubs: (name, division, template record (a SWOS club of the same region), strength step)
NEW = [
    ('LYNN-AVON UNITED', NORTH, 12, 0), ('BLOCKHOUSE BAY', NORTH, 18, -1), ('FENCIBLES UNITED', NORTH, 8, -1),
    ('NGARUAWAHIA UTD', NORTH, 17, 0), ('PAPAKURA CITY', NORTH, 10, 0),
    ('WESTERN SUBURBS', CENTRAL, 26, 0), ('NORTH WELLINGTON', CENTRAL, 19, -1), ('GISBORNE CITY', CENTRAL, 15, -1),
    ('TARARUA UNITED', CENTRAL, 7, 0),
    ('NORTHERN HEARTS', SOUTH, 21, 0),
]
FIRST = ('ANDREW BRENT CHRIS CRAIG DANIEL DARREN DAVID DEAN GARY GRANT GREG IAN JASON JOHN KEVIN MARK MATTHEW MICHAEL NEIL '
         'NICK PAUL PETER RICHARD ROSS SCOTT SHANE SIMON STEVE STUART TIM TONY TREVOR WAYNE').split()
LAST = ('ANDERSON BAKER BROWN CAMPBELL CLARKE COOPER DAVIES EDWARDS FRASER GRAHAM HALL HARRIS HUGHES JOHNSTON KING LEWIS '
        'MACDONALD MARTIN MITCHELL MORRIS MURRAY NGATA PARATA ROBERTSON ROSS SCOTT SMITH STEWART TAYLOR THOMPSON TUHIWAI '
        'WALKER WATSON WHITE WILSON WOOD WRIGHT YOUNG').split()


def level_player(r, p, step):
    import c1c2
    c1c2.level_player(r, p, step)


def build(src_dir):
    d = open(f'{src_dir}/TEAM.{FILE:03d}', 'rb').read()
    assert struct.unpack('>H', d[:2])[0] == 30
    recs = [bytearray(d[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE]) for i in range(30)]
    used = {r[76 + k * 38 + 3:76 + k * 38 + 26].split(b'\0')[0].decode('latin1') for r in recs for k in range(16)}
    for i, (div, name) in CLUBS.items():
        r = recs[i]
        r[25] = div
        if name:
            r[5:22] = name.encode().ljust(17, b'\0')[:17]
    rng = random.Random(1996 * 100 + FILE)
    def gen():
        while True:
            n = f'{rng.choice(FIRST)} {rng.choice(LAST)}'
            if n not in used:
                used.add(n)
                return n
    for k, (name, div, tmpl, step) in enumerate(NEW):
        assert len(name) <= 16, name
        r = bytearray(recs[tmpl])
        r[1] = 30 + k
        r[5:22] = name.encode().ljust(17, b'\0')
        r[25] = div
        r[36:59] = gen().encode().ljust(23, b'\0')
        for j in range(16):
            p = 76 + j * 38
            r[p] = NZL
            r[p + 3:p + 26] = gen().encode().ljust(23, b'\0')
            if step:
                level_player(r, p, step)
        recs.append(r)
    for i, r in enumerate(recs):
        assert r[0] == FILE and r[1] == i
        struct.pack_into('>H', r, 2, BASE + i)
    out = struct.pack('>H', len(recs)) + b''.join(bytes(r) for r in recs)
    divs = [sum(1 for r in recs if r[25] == v) for v in range(4)]
    assert divs == [10, 10, 10, 10], divs
    return out


# --- exe: league struct (4 divisions, 4 points a win) ---------------------------------------------------------------
LEAGUE_SIG = bytes((0x61, 0, 0x3E, 0x10, 0x48, 0x1B, 0, 0, 0, 3, 2, 3, 0x35))
NSSL_NAME = (b'NAT. SUMMER LEAGUE', b'NSSL')
LEAGUE_AT = None


def patch(p, area, str_base):
    """New 4-division struct in the new obj2 page; every pointer to the old one retargeted."""
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1
    old = [struct.unpack_from('<I', d2, lo + 13 + 3 * 6 + 1 + 4 * i)[0] for i in range(6)]   # 3 x (long, short)
    hdr = bytearray(d2[lo:lo + 13])
    n = 4
    hdr[5] = 13 + 6 * n + 1 - 5
    hdr[9] = n
    hdr[11] = 4                                         # 4 points for a win (NSSL 1996-97)
    body = bytes(hdr) + bytes((10, 0, 0, 0, 0, 0)) * n + b'\0'
    nssl = [area.add(s + b'\0') - str_base for s in NSSL_NAME]
    for ptr in nssl + old:
        body += struct.pack('<I', ptr)
    at = area.add(body)
    refs = []                                           # every single-target record (original or added by the mod)
    for gp, recs in enumerate(p.recs):
        for r in recs:
            if r[0] & 0x20 or r[1] & 3 or (r[0] & 0x0F) == 2:   # source lists, imports, selector-only fixups
                continue
            q = 4
            tobj = struct.unpack_from('<H', r, q)[0] if r[1] & 0x40 else r[q]
            q += 2 if r[1] & 0x40 else 1
            toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, q)[0]
            if tobj == 2 and toff == lo:
                obj = next(o for o in p.le.objs if o.page_idx - 1 <= gp < o.page_idx - 1 + o.npages)
                refs.append((obj.idx, (gp - (obj.page_idx - 1)) * p.le.page_size + struct.unpack_from('<h', r, 2)[0]))
    assert refs, 'no pointer to the NZ league struct'
    for objn, off in refs:
        p.retarget(objn, off, 2, at)
    print(f'exe: New Zealand NSSL 1996-97 + 3 regions of 10, struct obj2+{at:#x} ({len(refs)} pointers)')
    global LEAGUE_AT
    LEAGUE_AT = at                                      # finals97 adds the play-off block
    return at


# --- exe: shoot-out after every NSSL draw, +1 point to its winner (session 28h) ----------------------------------------
NSSL_MASK = sum(1 << i for i, (div, _) in CLUBS.items() if div == NSSL)   # TEAM.062 ordinals of the 10 NSSL clubs
SHOOTOUT_ASM = r'''
; Both hooks know an NSSL match by its two teams (record byte 0 = team file 62, byte 1 = ordinal in NSSL_MASK): career league
; days (player's division and the simulated other ones) and DIY leagues all reach cseg_88A12.
nssl_team:                              ; esi -> team record; ZF = 1 if it is an NSSL club
    cmp byte [esi], NZ_FILE
    jne .r
    movzx eax, byte [esi + 1]
    cmp eax, 32
    jae .no
    bt dword [NSSL_BITS], eax
    jnc .no
    cmp eax, eax
.r:
    ret
.no:
    or esi, esi                         ; esi != 0: ZF = 0
    ret

nz_setup:                               ; replaces `mov word [penaltiesState], 0` in cseg_89381 (league match set-up)
    mov word [PEN_STATE], 0
    pushad
    mov word [PEN1], 0                  ; no shoot-out yet (a real one never ends 0-0)
    mov byte [NZ_WIN], 0
    mov word [PEN2], 0
    mov esi, [A1]
    call nssl_team
    jne .x
    mov esi, [A2]
    call nssl_team
    jne .x
    mov word [PEN_STATE], 1             ; the engine plays the shoot-out at full time on a draw (no extra time)
.x:
    popad
    ret

nz_draw:                                ; replaces `mov esi, [A4]; add word [esi+2C3h], 1` (draw: 1 point each) in cseg_88A12
    mov esi, [A4]
    add word [esi + 2C3h], 1
    pushad
    push dword [D0]
    mov esi, [A1]                       ; the teams (A3/A4 are their table entries: no team file byte there)
    call nssl_team
    jne .x
    mov esi, [A2]
    call nssl_team
    jne .x
    mov al, [NZ_WIN]                    ; decided by nz_mark when the result went into the game list
    mov edi, [A3]                       ; home = team 1 of the match
    cmp al, 1
    je .won
    mov edi, [A4]
    cmp al, 2
    je .won
    mov edi, [A3]
    mov ax, [PEN1]
    cmp ax, [PEN2]
    ja .won
    mov edi, [A4]
    jb .won
    call RAND                           ; not played (simulated, or no shoot-out): the shoot-out is drawn by lot
    test byte [D0], 1
    mov edi, [A3]
    jz .won
    mov edi, [A4]
.won:
    add word [edi + 2C3h], 1            ; the bonus point
.x:
    mov byte [NZ_WIN], 0
    mov word [PEN1], 0
    mov word [PEN2], 0
    pop dword [D0]
    popad
    ret

nssl_id:                                ; ax = team number (low byte file, high byte ordinal); ZF = 1 if NSSL
    cmp al, NZ_FILE
    jne .r
    movzx eax, ah
    cmp eax, 32
    jae .no
    bt dword [NSSL_BITS], eax
    jnc .no
    cmp eax, eax
.r:
    ret
.no:
    or esi, esi
    ret

nz_mark:                                ; replaces `mov ax,[D6]; mov esi,[A1]; mov [esi+14h],ax`, the last store of a result
    mov ax, [D6]                        ; into the game list (cseg_2A71E, after the manager's statistics: a shoot-out
    mov esi, [A1]                       ; stays a draw there)
    mov [esi + 14h], ax
    pushad
    push dword [D0]
    mov esi, [A1]
    mov ax, [esi + 0Ch]
    call nssl_id
    jne .x
    mov ax, [esi + 0Eh]
    call nssl_id
    jne .x
    mov ax, [esi + 10h]                 ; the result: home goals << 8 | away goals
    cmp ah, al
    jne .x
    mov dx, [PEN1]
    mov cx, [PEN2]
    cmp dx, cx
    je .lot
    mov bl, 1                           ; played: the real shoot-out
    ja .score
    mov bl, 2
.score:
    mov ah, dl
    mov al, cl
    jmp .set
.lot:                                   ; simulated: winner by lot, a shoot-out score as the engine shows for cups
    call RAND                           ; (Rand uses esi)
    mov esi, [A1]
    movzx edx, byte [D0]
    mov bl, 1
    test dl, 1
    jz .w
    mov bl, 2
.w:
    mov ah, dl                          ; winner 4 or 5, loser 1 or 2 less
    shr ah, 1
    and ah, 1
    add ah, 4
    mov al, dl
    shr al, 2
    and al, 1
    inc al
    neg al
    add al, ah
    cmp bl, 1
    je .set
    xchg ah, al
.set:
    mov [esi + 14h], ax                 ; shoot-out score (home << 8 | away)
    or byte [esi + 0Bh], 8Ah            ; result (80h), decided (2), on penalties (8): "%a WIN %0-%1 ON PENS"
    cmp bl, 2
    jne .k
    or byte [esi + 0Bh], 1              ; won by the away side
.k:
    mov [NZ_WIN], bl
.x:
    pop dword [D0]
    popad
    ret
NZ_WIN: db 0
NSSL_BITS: dd NSSL_MASK_
'''


def shootout(p, at):
    """Hooks for the NSSL shoot-out bonus point; code at obj1:at, returns the new end."""
    import re, nasmcave, sacups
    d1 = p.le.obj_bytes(1)
    regs = sacups.regs(d1)
    a0 = regs['D7'] + 4
    A = {n: a0 + 4 * i for i, n in enumerate(('A0', 'A1', 'A2', 'A3', 'A4'))}
    e = lambda x: re.escape(struct.pack('<I', x))
    zero = rb'\x66\xc7\x05(.{4})\x00\x00'
    # cseg_89381: team1/2GoalsFirstLeg, extraTimeState, penaltiesState, secondLeg, playing2ndGame, isGameFriendly = 0;
    # mov eax, [A0]; mov [A4], eax
    m = [x for x in re.finditer(zero * 7 + rb'\xa1' + e(A['A0']) + rb'\xa3' + e(A['A4']), d1, re.S)]
    assert len(m) == 1, len(m)
    site_a = m[0].start() + 27
    pen_state = struct.unpack('<I', m[0].group(4))[0]
    # cseg_88D6A: mov esi,[A3]; add word [esi+2BBh],1; mov esi,[A4]; add ...; mov esi,[A3]; add word [esi+2C3h],1; mov esi,[A4]; ...
    pat = (rb'\x8b\x35' + e(A['A3']) + rb'\x66\x83\x86\xbb\x02\x00\x00\x01\x8b\x35' + e(A['A4']) + rb'\x66\x83\x86\xbb\x02\x00\x00\x01'
           + rb'\x8b\x35' + e(A['A3']) + rb'\x66\x83\x86\xc3\x02\x00\x00\x01\x8b\x35' + e(A['A4']) + rb'\x66\x83\x86\xc3\x02\x00\x00\x01')
    m = [x for x in re.finditer(pat, d1)]
    assert len(m) == 1, len(m)
    site_b = m[0].start() + 42
    # StartPenalties: mov word [penaltiesState], -1; 2 x (mov ax,[statsTeamXGoals]; mov [savedTeamXGoals],ax); 8 x mov word [..],0
    # (team goals and digits ..., team1PenaltyGoals, team2PenaltyGoals); call Rand; and word [D0], 1
    m = [x for x in re.finditer(rb'\x66\xc7\x05' + e(pen_state) + rb'\xff\xff(?:\x66\xa1.{4}\x66\xa3.{4}){2}' + zero * 8
                                + rb'\xe8(.{4})\x66\x83\x25' + e(regs['D7'] - 28) + rb'\x01', d1, re.S)]
    assert len(m) == 1, len(m)
    pen1, pen2 = (struct.unpack('<I', m[0].group(k))[0] for k in (7, 8))
    rand = m[0].start(9) + 4 + struct.unpack('<i', m[0].group(9))[0]
    # cseg_2A71E: the result goes into the game list entry A1: flags +0Bh, D4 +10h, D5 +12h, D6 +14h
    d = lambda k: regs['D7'] - 28 + 4 * k
    m = [x for x in re.finditer(rb'\xa0' + e(regs['D7']) + rb'\x8b\x35' + e(A['A1']) + rb'\x88\x46\x0b'
                                + b''.join(rb'\x66\xa1' + e(d(k)) + rb'\x8b\x35' + e(A['A1']) + rb'\x66\x89\x46' + bytes((o,))
                                           for k, o in ((4, 0x10), (5, 0x12), (6, 0x14))), d1)]
    assert len(m) == 1, len(m)
    site_c = m[0].start() + 5 + 6 + 3 + 2 * 16
    symbols = {'NZ_FILE': (0, FILE), 'NSSL_MASK_': (0, NSSL_MASK), 'PEN_STATE': (2, pen_state), 'PEN1': (2, pen1),
               'PEN2': (2, pen2), 'RAND': (1, rand), 'D0': (2, regs['D7'] - 28), 'D6': (2, d(6)),
               **{k: (2, v) for k, v in A.items()}}
    code, fix = nasmcave.assemble(SHOOTOUT_ASM, at, symbols)
    labels = nasmcave.labels(SHOOTOUT_ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    # the overwritten instructions hold absolute addresses: drop their fixups first (see the coin-toss crash)
    p.remove(1, site_a + 3)                             # mov word [penaltiesState], 0
    p.put(1, site_a, b'\xe8' + struct.pack('<i', labels['nz_setup'] - (site_a + 5)) + b'\x90' * 4)
    p.remove(1, site_b + 2)                             # mov esi, [A4]
    p.put(1, site_b, b'\xe8' + struct.pack('<i', labels['nz_draw'] - (site_b + 5)) + b'\x90' * 9)
    p.remove(1, site_c + 2)                             # mov ax, [D6]
    p.remove(1, site_c + 8)                             # mov esi, [A1]
    p.put(1, site_c, b'\xe8' + struct.pack('<i', labels['nz_mark'] - (site_c + 5)) + b'\x90' * 11)
    print(f'exe: NSSL shoot-out: set-up obj1+{site_a:#x}, draw obj1+{site_b:#x}, game list obj1+{site_c:#x}, '
          f'code obj1+{at:#x} ({len(code)} B)')
    return (at + len(code) + 15) & ~15
