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
Still 5 on screen until block 2 (the bench graphic and its cursor) and block 3 (name sprites).
"""
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
    at = (at + 15) & ~15
    sym = {'GMAX': (2, gmax), 'D2': (2, d2), 'A2': (2, regs['A0'] + 8), 'A6': (2, regs['A0'] + 24),
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
    rs = refs(p, 2, table, table + 32)
    assert 10 <= len(rs) <= 24, ('inGameTeamPlayerOffsets refs', len(rs))
    for objn, off, toff in rs:
        p.retarget(objn, off, 1, lab['bx_table'] + toff - table)
        p.put(objn, off, struct.pack('<I', lab['bx_table'] + toff - table))
    LABELS.update(lab)
    print(f'exe: bench up to 15 (block 1: in-match teams of {MAXP}; GMAX obj2+{gmax:#x}, loop obj1+{lp:#x}, '
          f'{len(rs)} offset-table refs moved; code obj1+{at:#x}, {len(code)} B, bx_bench obj1+{lab["bx_bench"]:#x})')
    return at + len(code)
