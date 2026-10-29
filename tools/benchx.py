"""A bench of up to 15 substitutes (4.1, Panchina block 1: the in-match teams).

The game passes every match "substitutions X from a bench of Y" (InitializeInGameTeamsAndStartGame: D1 ->
gameMinSubstitutes, D2 -> gameMaxSubstitutes, Y <= 5 everywhere) and builds each in-match team (topTeamInGame /
bottomTeamInGame, 1704 bytes: TeamGame 42 + PlayerInfo 61 per player) with 16 players (InitInGameTeamStructure).
InitInGamePlayer already takes the players from 11 + gameMaxSubstitutes on out of the match (position -1,
substituted). The buffers' tail (bytes 1018..1703) is free (harness bench_mem, 2026-10-29), so 26 players fit
(42 + 26 x 61 = 1628), also in the highlights (SetHilFileHeader copies 1704 bytes per team).

- bx_max replaces `mov [gameMaxSubstitutes], ax`: a non-zero BENCH word (bx_bench; the per-competition rule comes in
  phase 2, a test poke until then) is the match's bench instead, at most 15.
- bx_next replaces InitInGameTeamStructure's `add word [D2], 1 / cmp word [D2], 16` (the jnz after it stays): the
  loop goes to 11 + max(5, bench) players; a team with fewer players (only the managed career club has more than 16:
  careerTeam, careerNumPlayers, its order in currentMatchPlayers, 32 places) gets empty places: zeroed, position -1,
  substituted, which every bench routine skips.
- inGameTeamPlayerOffsets (16 x index * 61) moves to a 26-entry table here: every fixup to it is retargeted.
- The game's own `cmp word [gameMaxSubstitutes], 5` branches (a bench over 5 = the first bench place is the
  goalkeeper's only, in FirePressedInSubsMenu, UpdateSubstitutePlayerIndices and DrawBenchPlayersAndCoach twice)
  compare with 127: never taken.

Block 2 (the bench graphic, 4.1): the dugout keeps its art and 5 places; with a bigger bench they are a window of 5
that scrolls with the cursor (Davide's choice B).
- BenchMenuHandleControls' `cmp [g_benchPlayerIndex], 5` / `, 6` (the cursor's last place / one past it) ->
  bx_cmp_last / bx_cmp_last1: the last place is max(5, gameMaxSubstitutes) <= 15 (5 in a training game); empty
  places are skipped by IsThisPlayerOkToSelect as the game's own substituted players.
- DrawBenchAndSubsMenu's `mov ax, [g_benchPlayerIndex]` (the arrow's row) -> bx_arrow: the window start bx_win
  follows the cursor (the coach or a training game: 0), the arrow's row = index - bx_win.
- DrawBenchPlayersAndCoach's `mov word [D7], 1` / `cmp word [D7], 6` -> bx_win_init / bx_win_end: places
  bx_win + 1 .. bx_win + 5 (A0 moved on by bx_win players); the opponent's bench (g_subsState -1) its first 5.
- SetCurrentPlayerName's `add word [D1], 255` / `, 271` (the in-match name sprites: 16 a team) -> bx_name1 /
  bx_name2: a player from place 16 on has no name sprite yet (block 3): the name is hidden, never another's.
- The after-match write-backs (cseg_2F194 cards, UpdatePlayerInjuries, cseg_2F3AB goals: `mov word [D2], 15`, 16
  in-match players) -> bx_wcount: 11 + max(5, gameMaxSubstitutes) places (16 with the game's bench: no stale
  record read), so a player from place 17 on who came on keeps his card / injury / goals (GetPlayer: careerTeam's 32).
"""
import os
import re
import struct

import nasmcave

MAXP = 26                               # 11 + 15
PI = 61                                 # sizeof PlayerInfo
TABLE = struct.pack('<16H', *(i * PI for i in range(16)))     # 0, 61 .. 915

ASM = r"""
bx_max:                                 ; replaces `mov [GMAX], ax` (InitializeInGameTeamsAndStartGame)
    cmp word [bx_bench], 0
    je .game
    mov ax, [bx_bench]
    cmp ax, 15
    jbe .game
    mov ax, 15
.game:
    mov [GMAX], ax
    ret

bx_next:                                ; replaces `add word [D2], 1 / cmp word [D2], 16`: ZF = 1 when the loop ends
    push eax
    push ecx
    push edi
    inc word [D2]
    movzx ecx, word [GMAX]              ; the loop's end: 11 + max(5, bench), at most 26
    cmp ecx, 5
    jae .m
    mov ecx, 5
.m:
    add ecx, 11
    cmp ecx, MAXP
    jbe .l
    mov ecx, MAXP
.l:
    mov eax, 16                         ; the team's players: 16, the managed career club careerNumPlayers
    cmp dword [A2], CT
    jne .a
    movzx eax, word [CNP]
.a:
    cmp ax, cx
    jbe .n
    mov eax, ecx
.n:
    cmp [D2], ax
    jb .more
    mov edi, [A6]                       ; the rest are empty places: A6 -> this place (already advanced)
.empty:
    cmp [D2], cx
    jae .done
    push ecx
    push edi
    add edi, 42
    mov ecx, PI
    xor al, al
    rep stosb
    pop edi
    pop ecx
    mov byte [edi + 42], 1              ; substituted
    mov byte [edi + 46], -1             ; position
    add edi, PI
    inc word [D2]
    jmp .empty
.done:
    mov [A6], edi
    xor eax, eax                        ; ZF = 1: done
    jmp .out
.more:
    or eax, 1                           ; ZF = 0: next player
.out:
    pop edi
    pop ecx
    pop eax
    ret

bx_lastw:                               ; ax = the cursor's last bench place: max(5, GMAX) <= 15; 5 in a training game
    mov ax, [GMAX]
    cmp ax, 5
    jae .a
    mov ax, 5
.a:
    cmp ax, 15
    jbe .b
    mov ax, 15
.b:
    cmp word [TRAIN], 0
    je .c
    mov ax, 5
.c:
    ret

bx_cmp_last:                            ; replaces `cmp word [IDX], 5` (its flags)
    push eax
    call bx_lastw
    cmp [IDX], ax
    pop eax
    ret

bx_cmp_last1:                           ; replaces `cmp word [IDX], 6`
    push eax
    call bx_lastw
    inc ax
    cmp [IDX], ax
    pop eax
    ret

bx_arrow:                               ; replaces `mov ax, [IDX]` (the arrow's row): ax = IDX - bx_win
    push ebx
    movzx eax, word [IDX]
    xor ebx, ebx
    cmp word [TRAIN], 0
    jne .set
    or eax, eax
    jz .set                             ; (the coach: the first 5)
    movzx ebx, word [bx_win]
    dec eax                             ; the cursor's place - 1
    cmp eax, ebx
    jae .down
    mov ebx, eax                        ; above the window: it starts there
    jmp .set
.down:
    sub eax, 4
    cmp eax, ebx
    jle .set
    mov ebx, eax                        ; below it: it ends there
.set:
    mov [bx_win], bx
    movzx eax, word [IDX]
    sub eax, ebx
    pop ebx
    ret

bx_win_init:                            ; replaces `mov word [D7], 1` (DrawBenchPlayersAndCoach, A0 -> place 11)
    push eax
    xor eax, eax
    cmp word [SUBST], 0
    jl .w                               ; (the opponent's bench: its first 5)
    cmp word [TRAIN], 0
    jne .w
    mov ax, [bx_win]
.w:
    mov [bx_cur], ax
    inc eax
    mov [D7], ax
    dec eax
    imul eax, eax, PI
    add [A0], eax
    pop eax
    ret

bx_win_end:                             ; replaces `cmp word [D7], 6`
    push eax
    mov ax, [bx_cur]
    add ax, 6
    cmp [D7], ax
    pop eax
    ret

bx_name1:                               ; replaces `add word [D1], 255` (SetCurrentPlayerName, D1 = the place)
    cmp word [D1], 16
    jae bx_noname
    add word [D1], 255
    ret
bx_name2:                               ; replaces `add word [D1], 271`
    cmp word [D1], 16
    jae bx_noname
    add word [D1], 271
    ret
bx_noname:                              ; no sprite for places 16..25 (block 3): the name hidden
    add esp, 4
    jmp HIDE

bx_wcount:                              ; replaces `mov word [D2], 15`: the in-match places - 1
    push eax
    movzx eax, word [GMAX]
    cmp eax, 5
    jae .a
    mov eax, 5
.a:
    cmp eax, 15
    jbe .b
    mov eax, 15
.b:
    add eax, 10
    mov [D2], ax
    pop eax
    ret

bx_win: dw 0
bx_cur: dw 0
bx_bench: dw 0                          ; the match's bench (0 = the game's), test switch BENCH_FORCE
align 2
bx_table:
%assign i 0
%rep MAXP
    dw i * PI
%assign i i + 1
%endrep
"""

LABELS = {}


def sites(p, regs):
    """(GMAX store, its variable, the InitInGameTeamStructure loop step, the 4 `cmp [GMAX], 5`, the table)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d1, d2, d3 = regs['D7'] - 24, regs['D7'] - 20, regs['D7'] - 16
    d0 = regs['D7'] - 28                    # mov word [hilStarted], 0 / D0 -> plg_D0_param / D1 -> GMIN / D2 -> GMAX / D3
    ms = list(re.finditer(rb'\x66\xc7\x05....\x00\x00\x66\xa1' + pk(d0) + rb'\x66\xa3....\x66\xa1' + pk(d1)
                          + rb'\x66\xa3....\x66\xa1' + pk(d2) + rb'\x66\xa3(....)\x66\xa1' + pk(d3), d, re.S))
    assert len(ms) == 1, ('gameMaxSubstitutes store', len(ms))
    store = ms[0].start() + 9 + 12 + 12 + 6
    gmax = p.target(1, store + 2)[1]
    a6 = regs['A0'] + 24
    lp = [m.start() + 39 for m in re.finditer(rb'(?:\xc6\x46.\x00){8}\x83\x05' + pk(a6) + rb'\x3d\x66\x83\x05' + pk(d2)
                                             + rb'\x01\x66\x83\x3d' + pk(d2) + rb'\x10\x0f\x85', d, re.S)]
    assert len(lp) == 1, ('InitInGameTeamStructure loop', lp)
    g = struct.pack('<I', gmax)
    c5 = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\x05', d, re.S) if d[m.start() + 3:m.start() + 7] == g
          and p.target(1, m.start() + 3) == (2, gmax)]
    assert len(c5) == 4, ('cmp [gameMaxSubstitutes], 5', len(c5))
    d2b = p.le.obj_bytes(2)
    tb = [m.start() for m in re.finditer(re.escape(TABLE), d2b)]
    assert len(tb) == 1, ('inGameTeamPlayerOffsets', tb)
    return store, gmax, lp[0], c5, tb[0], d2


def sites2(p, regs):
    """Block 2's sites in the original obj1: {name: offset} + the variables IDX, TRAIN, SUBST (obj2) and HIDE (obj1)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    J = rb'(?:\xe9....|\xeb.)'
    m = list(re.finditer(rb'\x66\x83\x3d(....)\x05\x75.' + J + rb'\x66\xc7\x05\1\x00\x00' + J + rb'\x66\x83\x05\1\x01'
                         rb'\x66\x83\x3d\1\x06\x74', d, re.S))
    assert len(m) == 1, ('BenchMenuHandleControls cursor', len(m))
    idx = p.target(1, m[0].start() + 3)[1]
    c6 = m[0].end() - 9                         # (cmp word [IDX], 6: the 8 bytes before the jz)
    ar = [x.start() for x in re.finditer(rb'\x66\xa1' + re.escape(m[0].group(1)) + rb'\x66\xa3....\x66\x83\x2d....\x0c', d, re.S)]
    assert len(ar) == 1, ('the bench arrow', ar)
    wi = list(re.finditer(rb'\x05\x9f\x02\x00\x00\xa3' + pk(regs['A0']) + rb'\x66\xa1(....)\x66\x0b\xc0\x74', d, re.S))
    assert len(wi) == 1, ('DrawBenchPlayersAndCoach A0 + 671', len(wi))
    w0 = wi[0].start()
    train = p.target(1, w0 + 12)[1]
    d7 = regs['D7']
    d7i = [x.start() for x in re.finditer(rb'\x66\xc7\x05' + pk(d7) + rb'\x01\x00', d) if 0 < x.start() - w0 < 80]
    d7e = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + pk(d7) + rb'\x06\x0f\x85', d) if 0 < x.start() - w0 < 0x300]
    assert len(d7i) == 1 and len(d7e) == 1, ('the bench drawing loop', d7i, d7e)
    sb = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x0f\x88', d, re.S) if 0 < x.start() - d7i[0] < 0x60]
    assert len(sb) == 1, ('g_subsState in the bench loop', sb)
    subst = p.target(1, sb[0] + 2)[1]
    d1 = regs['D7'] - 24
    n1 = [x.start() for x in re.finditer(rb'\x66\x81\x05' + pk(d1) + rb'\xff\x00', d)]
    n2 = [x.start() for x in re.finditer(rb'\x66\x81\x05' + pk(d1) + rb'\x0f\x01', d)]
    assert len(n1) == 1 and len(n2) == 1 and 0 < n2[0] - n1[0] < 0x80, ('the name sprites', n1, n2)
    hd = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(regs['A0']) + rb'\x66\xc7\x46.\xff\xff\x66\xc7\x46.\xa8\x61', d, re.S)
          if 0 < n1[0] - x.start() < 0x400]
    assert len(hd) == 1, ('@@hide_current_player_name', hd)
    lp = sites(p, regs)[2]                      # the three after-match loops just before InitInGameTeamStructure
    d2 = regs['D7'] - 20
    wb = [x.start() for x in re.finditer(rb'\x66\xc7\x05' + pk(d2) + rb'\x0f\x00\x8b\x35' + pk(regs['A0'] + 4) + rb'\x8a\x46[\x2a\x2c]', d)
          if lp - 0x600 < x.start() < lp]
    assert len(wb) == 3, ('the after-match write-back loops', [hex(x) for x in wb])
    at = {'wb0': wb[0], 'wb1': wb[1], 'wb2': wb[2], 'c5': m[0].start(), 'c6': c6, 'arrow': ar[0], 'd7i': d7i[0], 'd7e': d7e[0], 'n1': n1[0], 'n2': n2[0]}
    for k, a in at.items():                     # (no other hook there)
        assert bytes(p.get(1, a, 9)) == d[a:a + 9], ('block 2 site already patched', k, hex(a))
    return at, {'IDX': (2, idx), 'TRAIN': (2, train), 'SUBST': (2, subst), 'HIDE': (1, hd[0])}


def refs(p, tobj, lo, hi):
    """Every 32-bit fixup source (objn, off) whose target is tobj:lo..hi-1 -> [(objn, off, toff)]."""
    out = []
    for gp, recs in enumerate(p.recs):
        objn, base = p.page_obj[gp]
        for r in recs:
            if r[0] & 0x20 or r[0] & 0xf == 2:
                continue
            po = struct.unpack_from('<h', r, 2)[0]
            if po < 0:                          # (the second half of a straddling pointer: counted on its page)
                continue
            q = 4
            t = struct.unpack_from('<H', r, q)[0] if r[1] & 0x40 else r[q]
            q += 2 if r[1] & 0x40 else 1
            toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, q)[0]
            if t == tobj and lo <= toff < hi:
                out.append((objn, base + po, toff))
    return out


def patch(p, at):
    """Code + data at obj1:at (a page of its own); returns the end."""
    import sacups
    import xtra
    regs = sacups.regs(p.le.obj_bytes(1))
    store, gmax, lp, c5, table, d2 = sites(p, regs)
    if 'CT' in xtra.LABELS:                         # xtra already hooked cseg_5DB56 (its site is a call now)
        ct = xtra.LABELS['CT']
        cnp = ct + 1292                             # careerNumPlayers follows careerTeam
    else:
        _, cnp, ct, _, _ = xtra.sites(p)
    s2, v2 = sites2(p, regs)
    at = (at + 15) & ~15
    sym = {**v2, 'D7': (2, regs['D7']), 'D1': (2, regs['D7'] - 24), 'A0': (2, regs['A0']), 'GMAX': (2, gmax), 'D2': (2, d2), 'A2': (2, regs['A0'] + 8), 'A6': (2, regs['A0'] + 24),
           'CT': (2, ct), 'CNP': (2, cnp), 'MAXP': (0, MAXP), 'PI': (0, PI)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    # gameMaxSubstitutes store (6 bytes: 66 A3 addr) -> call bx_max + nop
    p.remove(1, store + 2)
    p.put(1, store, b'\xe8' + struct.pack('<i', lab['bx_max'] - (store + 5)) + b'\x90')
    # the loop step (16 bytes: add word [D2], 1 / cmp word [D2], 16) -> call bx_next + 11 nops (the jnz stays)
    p.remove(1, lp + 3)
    p.remove(1, lp + 11)
    p.put(1, lp, b'\xe8' + struct.pack('<i', lab['bx_next'] - (lp + 5)) + b'\x90' * 11)
    for c in c5:                                    # the game's 'bench over 5' branches: never
        p.put(1, c + 7, b'\x7f')
    def call9(o, n, lbl, fixat):                     # an n-byte instruction with an address at o + fixat -> call + nops
        p.remove(1, o + fixat)
        p.put(1, o, b'\xe8' + struct.pack('<i', lab[lbl] - (o + 5)) + b'\x90' * (n - 5))
    call9(s2['c5'], 8, 'bx_cmp_last', 3)            # cmp word [IDX], 5 (66 83 3D addr 05)
    call9(s2['c6'], 8, 'bx_cmp_last1', 3)
    call9(s2['arrow'], 6, 'bx_arrow', 2)            # mov ax, [IDX] (66 A1 addr)
    call9(s2['d7i'], 9, 'bx_win_init', 3)           # mov word [D7], 1 (66 C7 05 addr 01 00)
    call9(s2['d7e'], 8, 'bx_win_end', 3)            # cmp word [D7], 6 (66 83 3D addr 06)
    call9(s2['n1'], 9, 'bx_name1', 3)               # add word [D1], 255 (66 81 05 addr FF 00)
    call9(s2['n2'], 9, 'bx_name2', 3)
    for k in ('wb0', 'wb1', 'wb2'):                 # mov word [D2], 15 (66 C7 05 addr 0F 00)
        call9(s2[k], 9, 'bx_wcount', 3)
    rs = refs(p, 2, table, table + 32)
    assert 10 <= len(rs) <= 24, ('inGameTeamPlayerOffsets refs', len(rs))
    for objn, off, toff in rs:
        p.retarget(objn, off, 1, lab['bx_table'] + toff - table)
        p.put(objn, off, struct.pack('<I', lab['bx_table'] + toff - table))
    bf = int(os.environ.get('BENCH_FORCE', '0'))   # BENCH_FORCE=n (test / playtest builds only): every match's bench
    if bf:                                          # n (<= 15) until the per-competition rule (phase 2)
        p.put(1, lab['bx_bench'], struct.pack('<H', min(bf, 15)))
        print(f'exe: BENCH_FORCE={min(bf, 15)} (test build)')
    LABELS.update(lab)
    print(f'exe: bench up to 15 (block 1: in-match teams of {MAXP}; GMAX obj2+{gmax:#x}, loop obj1+{lp:#x}, '
          f'{len(rs)} offset-table refs moved; block 2: bench window of 5, cursor to 15, names 17+ hidden, 3 after-match loops to 11 + bench; code obj1+{at:#x}, {len(code)} B, bx_bench obj1+{lab["bx_bench"]:#x})')
    return at + len(code)
