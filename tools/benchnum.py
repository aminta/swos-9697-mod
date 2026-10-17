"""Real squad numbers: worlds with pack.json 'squad_numbers': true keep every player's own shirt number.

The game binds numbers to line-up places and writes them INTO the player records (team buffer, so into the .CAR):
  - SetBenchPlayersNumbers (SquadFinish, SquadCommon, PlayMatchMenuInit, OnSwapPlayer, UseMatchTeamSelect,
    EditTacticsInit, EditTacticsPlayerNamesCommon, cseg_56379, cseg_5C5EF): the players in places 11..15 get 12..16;
  - the shirt swap block (10 instructions, 46 bytes) of cseg_125F4 (squad screens), PlayMatchMenuSwapPlayers (play
    match menu) and cseg_4E3DD (tactics names): a starter swapped with a bench / reserve player swaps numbers with
    him; the same block twice in cseg_52EA6, when a generated filler is removed.
A real 23 put on the bench became 14 for good. In a career of a squad-number world (game type 4 and the save's world
byte, someLeaguesTable[careerworld.WORLD_BYTE], in the table) all of them are skipped, also for the computer's side.
New players of the managed club get a free number there: a purchase (cseg_56379) keeps his old club's number if no
one in the squad has it, else the lowest free of 2..99 (1 too for a keeper); the game's reserves / trial players
(cseg_64B80) and generated fillers (cseg_52956), which the game numbers 16, likewise. Elsewhere the game runs as
before. (cseg_56129, a player moving into a computer club's record, takes that slot's number: left as the game does.)

SWOS++ (English) hooks SetBenchPlayersNumbers+0x40 (keeps numbers > 16 and 0) and PlayMatchMenuSwapPlayers' swap
block + 6 (keeps them on a swap) at run time. Our hooks take other bytes: the routine's first instruction and each
swap block's first one (`mov esi, [A0]`, 6 bytes), so both coexist: in a squad-number world ours return before
SWOS++'s code; elsewhere they run the moved instruction and go on into it.
"""
import re
import struct

SWAPLEN = 46                           # the shirt swap block: 10 instructions, 6+3+5+6+3+6+3+5+6+3 bytes

ASM = r"""
bn_bench:                               ; replaces SetBenchPlayersNumbers' `mov esi, [A0]`
    call bn_world
    jz .game
    add esp, 4                          ; squad-number world: return from SetBenchPlayersNumbers itself
.game:
    mov esi, [A0]
    ret

bn_swap:                                ; replaces a shirt swap block's `mov esi, [A0]`
    call bn_world
    jz .game
    add dword [esp], SWAPLEN_ - 5       ; squad-number world: on after the block (positions are swapped already)
.game:
    mov esi, [A0]
    ret

bn_buy:                                 ; replaces `add word [careerNumPlayers], 1` after a purchase (cseg_56379)
    add word [CNP], 1
    call bn_world
    jz .r
    pushad
    movzx ebx, word [REGS + 4]          ; D1 = the new player's slot (pushed around SetBenchPlayersNumbers)
    call bn_free
    popad
.r:
    ret

bn_new:                                 ; replaces `mov esi, [A0] / mov byte [esi+4Eh], 16`: a generated filler
    mov esi, [A0]                       ; (cseg_52956) or the game's reserve / trial player (cseg_64B80)
    mov byte [esi + 4Eh], 16
    call bn_world
    jz .r
    pushad
    lea eax, [esi + 4Ch]
    sub eax, CT + 76
    xor edx, edx
    mov ecx, 38
    div ecx
    mov ebx, eax                        ; his slot
    call bn_free
    popad
.r:
    ret

bn_free:                                ; slot ebx of the managed club: keep his number if no other player of the
    mov edi, bn_used                    ; squad has it, else the lowest free of 2..99 (1 too for a keeper)
    mov ecx, 100
    xor eax, eax
    rep stosb
    movzx ecx, word [CNP]
    xor esi, esi
.mark:
    cmp esi, ecx
    jae .marked
    movzx eax, byte [CMP + esi]         ; squad order -> slot
    inc esi
    cmp eax, ebx
    je .mark
    imul eax, eax, 38
    movzx eax, byte [CT + 76 + 2 + eax]
    cmp eax, 100
    jae .mark
    mov byte [bn_used + eax], 1
    jmp .mark
.marked:
    imul edi, ebx, 38
    add edi, CT + 76                    ; his record
    movzx eax, byte [edi + 2]
    mov dl, [edi + 26]
    shr dl, 5                           ; position: 0 = keeper
    test eax, eax
    jz .pick
    cmp eax, 100
    jae .pick
    cmp eax, 1
    jne .own
    test dl, dl
    jnz .pick
.own:
    cmp byte [bn_used + eax], 0
    je .done
.pick:
    mov eax, 1
    test dl, dl
    jz .try
    inc eax
.try:
    cmp byte [bn_used + eax], 0
    je .set
    inc eax
    cmp eax, 100
    jb .try
    jmp .done                           ; 99 numbers taken: keep it
.set:
    mov [edi + 2], al
.done:
    ret

bn_world:                               ; ZF clear = a career in a squad-number world
    push eax
    push esi
    cmp word [GAMETYPE], 4
    jne .no
    mov al, [SLT + WORLD_BYTE]
    mov esi, BN_TAB
.find:
    cmp byte [esi], 0
    je .no
    cmp al, [esi]
    je .yes
    inc esi
    jmp .find
.yes:
    or esi, esi                         ; ZF = 0 (esi points into the table)
    pop esi
    pop eax
    ret
.no:
    xor eax, eax                        ; ZF = 1
    pop esi
    pop eax
    ret

bn_used: times 100 db 0
BN_TAB:
"""


def sites(p):
    """Sites and variables on the original bytes: (SetBenchPlayersNumbers, [swap blocks], A0, gameType,
    someLeaguesTable, {buy, new: [..], cnp, ct, cmp})."""
    import sacups
    import xtra
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    d7 = a0 - 4
    d0, d1r = d7 - 28, d7 - 24
    pk = lambda x: re.escape(struct.pack('<I', x))
    # SetBenchPlayersNumbers: mov esi,[A0]; mov ax,[esi]; mov [D0],ax; mov word [D1],11
    b = [m.start() for m in re.finditer(rb'\x8b\x35' + pk(a0) + rb'\x66\x8b\x06\x66\xa3' + pk(d0) + rb'\x66\xc7\x05'
                                        + pk(d1r) + rb'\x0b\x00', d1, re.S)]
    assert len(b) == 1, ('SetBenchPlayersNumbers', b)
    # shirt swap: mov esi,[A0]; mov al,[esi+4Eh]; mov [D0],al; mov esi,[A1]; mov al,[esi+4Eh]; mov esi,[A0];
    #             mov [esi+4Eh],al; mov al,[D0]; mov esi,[A1]; mov [esi+4Eh],al
    sw = rb''.join((rb'\x8b\x35' + pk(a0), rb'\x8a\x46\x4e', rb'\xa2' + pk(d0), rb'\x8b\x35' + pk(a0 + 4),
                    rb'\x8a\x46\x4e', rb'\x8b\x35' + pk(a0), rb'\x88\x46\x4e', rb'\xa0' + pk(d0),
                    rb'\x8b\x35' + pk(a0 + 4), rb'\x88\x46\x4e'))
    s = [m.start() for m in re.finditer(sw, d1, re.S)]  # cseg_125F4, PlayMatchMenuSwapPlayers, cseg_4E3DD,
    assert len(s) == 5, ('shirt swaps', s)             # cseg_52EA6 x 2
    sl = {p.target(1, x.start() + 15) for x in re.finditer(rb'\x66\xc7\x05' + pk(d0) + rb'\xcf\x07\xc7\x05' + pk(a0)
                                                            + rb'.{4}\xc7\x05' + pk(a0 + 4), d1, re.S)}
    assert len(sl) == 1, ('someLeaguesTable', sl)
    gt = {p.target(1, x.start() + 14) for x in
          re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d.{4}\x04\x75', d1, re.S)}
    assert len(gt) == 1, ('gameType', gt)
    # purchases (cseg_56379): call SetBenchPlayersNumbers; pop [D1]; add word [careerNumPlayers], 1
    _, cnp, ct, cmp, _ = xtra.sites(p)
    buy = [m.start() + 11 for m in re.finditer(rb'\xe8(....)\x8f\x05' + pk(d1r) + rb'\x66\x83\x05' + pk(cnp) + rb'\x01',
                                               d1, re.S) if m.start() + 5 + struct.unpack('<i', m.group(1))[0] == b[0]]
    assert len(buy) == 1, ('purchase', buy)
    # new fillers (cseg_52956) and the game's reserves / trial players (cseg_64B80): mov esi,[A0]; mov byte [esi+4Eh],16
    new = [m.start() for m in re.finditer(rb'\x8b\x35' + pk(a0) + rb'\xc6\x46\x4e\x10', d1, re.S)]
    assert len(new) == 2, ('fillers / reserves', new)
    return b[0], s, a0, gt.pop(), sl.pop(), dict(buy=buy[0], new=new, cnp=cnp, ct=ct, cmp=cmp)


def patch(p, cave, nasmcave, worlds):
    """worlds: the world numbers with squad numbers. Returns the cave end (nothing done without such worlds)."""
    import careerworld
    if not worlds:
        return cave
    bench, swaps, a0, gametype, slt, sq = sites(p)
    src = ASM + ''.join(f'    db {n}\n' for n in worlds) + '    db 0\n'
    sym = {'A0': (2, a0), 'GAMETYPE': gametype, 'SLT': slt, 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'SWAPLEN_': (0, SWAPLEN), 'CNP': (2, sq['cnp']), 'CT': (2, sq['ct']), 'CMP': (2, sq['cmp']),
           'REGS': (2, a0 - 32)}
    cave = (cave + 3) & ~3
    code, fix = nasmcave.assemble(src, cave, sym)
    lab = nasmcave.labels(src, cave, sym)
    assert not any(p.get(1, cave, len(code)))
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    for site, label in [(bench, 'bn_bench')] + [(x, 'bn_swap') for x in swaps]:
        p.remove(1, site + 2)                        # mov esi, [A0] -> call; nop
        p.put(1, site, b'\xe8' + struct.pack('<i', lab[label] - (site + 5)) + b'\x90')
    p.remove(1, sq['buy'] + 3)                       # add word [careerNumPlayers], 1 -> call bn_buy; 3 x nop
    p.put(1, sq['buy'], b'\xe8' + struct.pack('<i', lab['bn_buy'] - (sq['buy'] + 5)) + b'\x90' * 3)
    for site in sq['new']:                           # mov esi,[A0]; mov byte [esi+4Eh],16 -> call bn_new; 5 x nop
        p.remove(1, site + 2)
        p.put(1, site, b'\xe8' + struct.pack('<i', lab['bn_new'] - (site + 5)) + b'\x90' * 5)
    print(f'exe: real squad numbers in worlds {worlds}: SetBenchPlayersNumbers obj1+{bench:#x}, '
          f'swaps {", ".join(hex(x) for x in swaps)}, purchase {sq["buy"]:#x}, new {[hex(x) for x in sq["new"]]}, '
          f'code obj1+{cave:#x}..{cave + len(code):#x}')
    return (cave + len(code) + 3) & ~3
