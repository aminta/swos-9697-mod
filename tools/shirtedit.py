"""Editable shirt numbers (4.0.2; Marco Malave's SWOS 2020 video, Nicola's request): on the team screen before a match
(playMatchMenu: each player row is an entry drawn by DrawPlayerEntries), LEFT on one of your players' rows lights his
number box (once the cursor has been on that row ~0.3 s: a LEFT that just brought it there, or a held one, still only
moves); then
  - UP / DOWN: the next / previous number of 1..99 that no other player of the team has (held = the menu's repeat);
  - digits (the keyboard's top row, by scan code: any layout): one or two digits, the second within ~1 s; a number
    another player has is swapped with him (he gets the old one): never two players with one number;
  - FIRE, ENTER, LEFT, RIGHT: done; ESC: the numbers as they were before this edit.
Not on the opponent's / the computer's squads (VIEW OPPO, showingCpuTeams). The number is the player record's own
shirtNumber byte, so it goes wherever the game keeps that team (career: careerTeam in the .CAR; seasons / competitions:
their saves; a friendly: that session only).

The game binds numbers to line-up places (benchnum.py: the bench gets 12..16, a starter swapped with a bench player
swaps numbers). The first edit sets bit 7 of the team record's byte 23 (benchnum.PIN_BIT: bit 0 is the game's
training-match flag, the other bits are 0 in every team file and TeamInit clears bit 0 only): from then on benchnum's
hooks treat that team as a squad-number world's (numbers stay with the players; a purchase / new player of a pinned
career club gets a free number).

Hooks: MenuProc's `call MenuCheckControls` -> `call se_ctl` (which calls it first; the controls are consumed while the
box is lit, so the cursor does not move and fire does not swap players); in DrawPlayerEntries the number entry's
(entry 32) `mov word [esi + isInvisible], 0` -> `call se_hl; nop` (the lit box: a coloured background on that row).
"""
import re
import struct

import nasmcave

HL_COLOR = 0x0E                 # the lit number box's background colour (menu palette)
WAIT = 28                       # menu frames for a second digit (~1 s)
DWELL = 8                       # menu frames on a row before LEFT lights its number (~0.3 s)

ASM = r"""
se_ctl:                                 ; MenuProc: replaces `call MenuCheckControls`
    call MCC
    pushad
    push dword [D0]
    push dword [D1]
    push dword [A0]
    mov ebx, [CURMENU + 0Ch]            ; the selected entry
    cmp ebx, [se_last]                  ; frames on this entry (LEFT just after arriving on a row is a move that
    je .same                            ; overshot, not an edit: the harness's paths, a held key)
    mov [se_last], ebx
    mov byte [se_dwell], 0
    jmp .counted
.same:
    cmp byte [se_dwell], 255
    je .counted
    inc byte [se_dwell]
.counted:
    cmp byte [se_on], 0
    jne .editing
    cmp byte [se_hold], 0               ; after an edit: wait until fire / left / right are released
    je .idle
    cmp word [FIRE], 0
    jne .swallow
    cmp byte [LEFT], 0
    jne .swallow
    cmp byte [RIGHT], 0
    jne .swallow
    mov byte [se_hold], 0
    jmp .idle
.swallow:
    call se_clear
    jmp .out
.idle:
    cmp word [MCD], 6                   ; left (MenuProc: 0 up, 2 right, 4 down, 6 left)
    jne .out
    cmp byte [se_dwell], DWELL
    jb .out
    test ebx, ebx
    jz .out
    call se_row
    jc .out
    mov [se_rec], edi
    mov [se_team], ebp
    mov [se_ent], ebx
    mov al, [edi + 2]
    mov [se_old], al
    test byte [ebp + PIN_AT], PIN_BIT
    jnz .pinned
    call se_unique                      ; (first edit of this team: one number per player first)
.pinned:
    mov byte [se_on], 1
    mov byte [se_dig], 0
    mov dword [se_prec], 0
    call se_clear
    jmp .out
.editing:
    cmp ebx, [se_ent]
    jne .stop
    movzx eax, word [LASTKEY]
    cmp eax, 1                          ; ESC
    je .esc
    cmp eax, 1Ch                        ; ENTER
    je .done
    cmp eax, 2                          ; '1' .. '9' = 2 .. 10, '0' = 11
    jb .nokey
    cmp eax, 11
    ja .nokey
    dec eax
    cmp eax, 10
    jb .digit
    xor eax, eax
.digit:
    cmp byte [se_dig], 0
    je .first
    movzx ecx, byte [se_first]
    imul ecx, ecx, 10
    add ecx, eax
    mov byte [se_dig], 0
    call se_commit
    jmp .eaten
.first:
    test eax, eax
    jz .eaten                           ; (a leading 0)
    mov [se_first], al
    mov byte [se_dig], 1
    mov byte [se_timer], WAIT
    mov edi, [se_rec]
    mov al, [edi + 2]
    mov [se_base], al                   ; the number before this typing (for the swap)
    mov al, [se_first]
    mov [edi + 2], al                   ; shown at once; committed by the timer / a second digit / done
    jmp .eaten
.nokey:
    cmp byte [se_dig], 0
    je .dirs
    dec byte [se_timer]
    jnz .dirs
    call se_first_commit
.dirs:
    movsx eax, word [MCD]
    test eax, eax
    js .fire
    jz .up
    cmp eax, 4
    je .down
    cmp eax, 2
    je .done
    cmp eax, 6
    je .done
    jmp .eaten                          ; diagonals: nothing
.fire:
    cmp word [FIRE], 0
    jne .done
    cmp word [SHORTFIRE], 0
    jne .done
    jmp .out
.up:
    call se_first_commit
    mov edx, 1
    call se_step
    jmp .eaten
.down:
    call se_first_commit
    mov edx, -1
    call se_step
    jmp .eaten
.esc:
    mov byte [se_dig], 0
    mov edi, [se_rec]
    mov al, [se_old]
    mov [edi + 2], al
    mov esi, [se_prec]
    test esi, esi
    jz .done
    mov al, [se_pold]
    mov [esi + 2], al
.done:
    call se_first_commit
    mov byte [se_on], 0
    mov byte [se_hold], 1
.eaten:
    mov word [LASTKEY], 0
    call se_clear
    jmp .out
.stop:
    call se_first_commit
    mov byte [se_on], 0
.out:
    pop dword [A0]
    pop dword [D1]
    pop dword [D0]
    popad
    ret

se_clear:                               ; no move, no fire this frame
    mov word [MCD], -1
    mov word [FIRE], 0
    mov word [SHORTFIRE], 0
    ret

se_first_commit:                        ; a single typed digit pending: commit it
    cmp byte [se_dig], 0
    je .r
    mov byte [se_dig], 0
    movzx ecx, byte [se_first]
    call se_commit
.r:
    ret

se_commit:                              ; ecx = typed number 1..99: the player holding it gets se_base
    mov edi, [se_rec]
    mov eax, ecx
    call se_used                        ; esi = another record with that number, or 0
    test esi, esi
    jz .set
    cmp dword [se_prec], 0
    jne .swap
    mov [se_prec], esi
    mov al, [esi + 2]
    mov [se_pold], al
.swap:
    mov al, [se_base]
    mov [esi + 2], al
.set:
    mov [edi + 2], cl
    jmp se_pin

se_step:                                ; edx = +1 / -1: the next number of 1..99 nobody else has
    mov edi, [se_rec]
    movzx eax, byte [edi + 2]
    mov ecx, 99
.n:
    add eax, edx
    cmp eax, 99
    jle .lo
    mov eax, 1
.lo:
    cmp eax, 1
    jge .chk
    mov eax, 99
.chk:
    push eax
    call se_used
    pop eax
    test esi, esi
    jz .set
    loop .n
    ret
.set:
    mov [edi + 2], al
se_pin:
    mov ebp, [se_team]
    or byte [ebp + PIN_AT], PIN_BIT     ; numbers stay with the players from now on (benchnum)
    ret

se_count:                               ; ebp = team -> edx = its players (the career club: careerNumPlayers)
    mov edx, 16
    cmp ebp, CT
    jne .r
    movzx edx, word [CNP]
.r:
    ret

se_recn:                                ; ebp = team, ecx = squad index -> esi = his record
    movzx esi, cl
    cmp ebp, CT
    jne .rec
    movzx esi, byte [CMP + ecx]
.rec:
    imul esi, esi, 38
    lea esi, [ebp + 76 + esi]
    ret

se_unique:                              ; ebp = team: duplicates / 0 / 100+ get free numbers (the first holder in
    pushad                              ; squad order keeps his: starters first), the lowest free of 2..99 (1 too
    mov edi, se_seen                    ; for a keeper), as benchnum's purchases
    xor eax, eax
    mov ecx, 100 + 32
.z:
    mov [edi], al
    inc edi
    loop .z
    call se_count
    xor ecx, ecx
.p1:
    cmp ecx, edx
    jae .p2s
    call se_recn
    movzx eax, byte [esi + 2]
    inc ecx
    test eax, eax
    jz .p1
    cmp eax, 100
    jae .p1
    cmp byte [se_seen + eax], 0
    jne .p1
    mov byte [se_seen + eax], 1
    mov byte [se_seen + 100 + ecx - 1], 1   ; keeps his number
    jmp .p1
.p2s:
    xor ecx, ecx
.p2:
    cmp ecx, edx
    jae .done
    cmp byte [se_seen + 100 + ecx], 0
    jne .next
    call se_recn
    mov bl, [esi + 26]
    shr bl, 5                           ; position: 0 = keeper
    mov eax, 1
    test bl, bl
    jz .try
    inc eax
.try:
    cmp byte [se_seen + eax], 0
    je .set
    inc eax
    cmp eax, 100
    jb .try
    jmp .next
.set:
    mov [esi + 2], al
    mov byte [se_seen + eax], 1
.next:
    inc ecx
    jmp .p2
.done:
    popad
    ret

se_used:                                ; al = number, edi = this record -> esi = another record of the team with it
    push ebx
    push ecx
    push edx
    mov ebp, [se_team]
    xor ecx, ecx
    mov edx, 16
    cmp ebp, CT
    jne .loop
    movzx edx, word [CNP]               ; the career club: its squad order, all its players
.loop:
    cmp ecx, edx
    jae .none
    movzx esi, cl
    cmp ebp, CT
    jne .rec
    movzx esi, byte [CMP + ecx]
.rec:
    imul esi, esi, 38
    lea esi, [ebp + 76 + esi]
    inc ecx
    cmp esi, edi
    je .loop
    cmp [esi + 2], al
    jne .loop
    jmp .r
.none:
    xor esi, esi
.r:
    pop edx
    pop ecx
    pop ebx
    ret

se_row:                                 ; ebx = entry: one of your players' rows? -> CF clear, edi = his record, ebp = team
    cmp dword [ebx + 34h], DPE          ; (its afterDraw)
    jne .no
    cmp byte [ebx + 8], 0FFh            ; LEFT goes nowhere from it (else LEFT is the menu's move)
    jne .no
    cmp word [VOPP], 0
    jne .no
    cmp word [SCPU], 0
    jne .no
    mov ebp, [PM1]
    test ebp, ebp
    jz .no
    movzx eax, word [ebx + 2]           ; ordinal: 13.. = the rows (16 = the last substitute's, as OnSwapPlayer)
    sub eax, 13
    jb .no
    cmp eax, 16
    ja .no
    jne .idx
    sub eax, 5
    add ax, [MAXSUB]
.idx:
    mov [A0], ebp
    mov [D1], ax
    push ebp
    push ebx
    call GPIBP                          ; -> [A0] + 4Ch = his record
    pop ebx
    pop ebp
    mov edi, [A0]
    add edi, 76
    mov eax, edi
    sub eax, ebp
    sub eax, 76
    cmp eax, 38 * 32
    jae .no
    clc
    ret
.no:
    stc
    ret

se_hl:                                  ; DrawPlayerEntries, number entry: replaces `mov word [esi + 4], 0`
    mov word [esi + 4], 0
    push eax
    cmp byte [se_on], 0
    je .plain
    mov eax, [A6]
    add eax, 76
    cmp eax, [se_rec]
    jne .plain
    mov word [esi + 1Ch], 2             ; a coloured background
    mov word [esi + 1Eh], HL
    pop eax
    ret
.plain:
    mov word [esi + 1Ch], 0
    pop eax
    ret

align 4
se_seen: times 100 + 32 db 0
align 4
se_rec: dd 0
se_last: dd 0
se_dwell: db 0
se_team: dd 0
se_ent: dd 0
se_prec: dd 0
se_on: db 0
se_hold: db 0
se_dig: db 0
se_first: db 0
se_timer: db 0
se_old: db 0
se_pold: db 0
se_base: db 0
"""


def sites(p):
    """Variables and sites on the original bytes."""
    import sacups
    import xtra
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['A0']
    pk = lambda x: re.escape(struct.pack('<I', x))
    t = lambda o: p.target(1, o)
    rel = lambda o: o + 4 + struct.unpack_from('<i', d1, o)[0]
    d7, d0, d1v, d5, a1, a5, a6 = a0 - 4, a0 - 32, a0 - 28, a0 - 12, a0 + 4, a0 + 20, a0 + 24
    out = {}
    # OnSwapPlayer: mov eax,[playMatchTeam1Ptr]; mov [A1],eax; mov ax,[viewingOpponentTeam]; or ax,ax; jnz;
    #               mov ax,[showingCpuTeams]; or ax,ax; jnz; jmp
    m = [x for x in re.finditer(rb'\xa1(....)\xa3' + pk(a1) + rb'\x66\xa1(....)\x66\x0b\xc0\x75.\x66\xa1(....)\x66\x0b\xc0'
                                rb'\x75.\xe9', d1, re.S)]
    assert len(m) == 1, ('OnSwapPlayer', len(m))
    sw = m[0].start()
    out.update(PM1=t(sw + 1), VOPP=t(sw + 12), SCPU=t(sw + 23))
    # its no-cpu path: mov ax,[maxSubstitutesEntries]; add [D6],ax ... mov eax,[PM1]; mov [A0],eax; mov ax,[D6];
    # mov [D1],ax; call GetPlayerInfoBreakPosition
    pm1 = d1[sw + 1:sw + 5]
    g = [x for x in re.finditer(rb'\x66\xa1(....)\x66\x01\x05(....)\xa1' + re.escape(pm1) + rb'\xa3' + pk(a0) +
                                rb'\x66\xa1\2\x66\xa3' + pk(d1v) + rb'\xe8', d1[sw:sw + 0x400], re.S)]
    assert len(g) == 1, ('GetPlayerInfoBreakPosition', len(g))
    out['MAXSUB'] = t(sw + g[0].start(1))
    out['GPIBP'] = (1, rel(sw + g[0].end()))
    # MenuProc: call ReadTimerDelta; call DrawMenu; mov ax, 4; cmp word [g_videoSpeedIndex], 50
    m = [x.start() for x in re.finditer(rb'\xe8....\xe8....\x66\xb8\x04\x00\x66\x83\x3d....\x32\x7f', d1, re.S)]
    assert len(m) == 1, ('MenuProc', m)
    mp = m[0]
    c = [x for x in re.finditer(rb'\xe8(....)\x66\xc7\x05(....)\x00\x00\xe8(....)', d1[mp:mp + 0x100], re.S)]
    assert len(c) == 1, ('MenuCheckControls call', len(c))
    out['MCC_SITE'] = mp + c[0].start(3) - 1
    out['MCC'] = (1, rel(mp + c[0].start(3)))
    mcc = out['MCC'][1]
    k = re.match(rb'\xe8....\x66\xa1(....)\x66\xa3' + pk(d0), d1[mcc:mcc + 24], re.S)
    assert k, 'lastKey'
    out['LASTKEY'] = t(mcc + 7)
    q = mp + 0x40
    sf = re.search(rb'\x66\xa1(....)\x66\x0b\xc0\x74.\x80\x0d' + pk(d7) + rb'\x20\x66\xa1(....)\x66\x0b\xc0\x74.\x80\x0d'
                   + pk(d7) + rb'\x01\xa0(....)\x0a\xc0\x74.\x80\x0d' + pk(d7) + rb'\x02\xa0(....)\x0a\xc0\x74.\x80\x0d'
                   + pk(d7) + rb'\x04', d1[q:q + 0x200], re.S)
    assert sf, 'fire / shortFire / left / right'
    out.update(SHORTFIRE=t(q + sf.start(1)), FIRE=t(q + sf.start(2)), LEFT=t(q + sf.start(3)), RIGHT=t(q + sf.start(4)))
    md = re.search(rb'\x66\xa1(....)\x66\xa3' + pk(d0) + rb'\x66\x0b\xc0\x78', d1[q:q + 0x300], re.S)
    assert md, 'menuControlsDirection'
    out['MCD'] = t(q + md.start(1))
    cm = re.search(rb'\xc7\x05' + pk(a6) + rb'(....)\x8b\x35' + pk(a6) + rb'\x8b\x46\x0c', d1[mp:mp + 0x200], re.S)
    assert cm, 'g_currentMenu'
    out['CURMENU'] = t(mp + cm.start(1))
    # DrawPlayerEntries: mov esi,[A5]; mov ax,[esi+2]; mov [D7],ax; sub word [D7],13; cmp word [D7],16
    m = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(a5) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d7) + rb'\x66\x83\x2d'
                                        + pk(d7) + rb'\x0d\x66\x83\x3d' + pk(d7) + rb'\x10', d1, re.S)]
    assert len(m) == 1, ('DrawPlayerEntries', m)
    out['DPE'] = (1, m[0])
    # its number entry: mov esi,[A0]; mov word [esi+4],1; mov ax,[D5]; or ax,ax; jnz; mov word [D0],0; mov esi,[A6];
    # mov al,[esi+4Eh]; mov [D0],al; mov ax,[D0]; mov esi,[A0]; mov [esi+26h],ax; mov esi,[A0]; mov word [esi+4],0
    m = [x.end() - 6 for x in re.finditer(rb'\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x01\x00\x66\xa1' + pk(d5) +
                                          rb'\x66\x0b\xc0\x75.\x66\xc7\x05' + pk(d0) + rb'\x00\x00\x8b\x35' + pk(a6) +
                                          rb'\x8a\x46\x4e\xa2' + pk(d0) + rb'\x66\xa1' + pk(d0) + rb'\x8b\x35' + pk(a0) +
                                          rb'\x66\x89\x46\x26\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x00\x00',
                                          d1[out['DPE'][1]:out['DPE'][1] + 0x1000], re.S)]
    assert len(m) == 1, ('number entry', m)
    out['HL_SITE'] = out['DPE'][1] + m[0]
    _, cnp, ct, cmp, _ = xtra.sites(p)
    out.update(CNP=(2, cnp), CT=(2, ct), CMP=(2, cmp), A0=(2, a0), D0=(2, d0), D1=(2, d1v), A6=(2, a6))
    return out


def patch(p, cave):
    """Code at obj1:cave (the career cave); returns its end."""
    import benchnum
    s = sites(p)
    sym = {k: v for k, v in s.items() if not k.endswith('_SITE')}
    sym.update(PIN_AT=(0, benchnum.PIN_AT), PIN_BIT=(0, benchnum.PIN_BIT), HL=(0, HL_COLOR), WAIT=(0, WAIT),
               DWELL=(0, DWELL))
    cave = (cave + 3) & ~3
    code, fix = nasmcave.assemble(ASM, cave, sym)
    lab = nasmcave.labels(ASM, cave, sym)
    assert not any(p.get(1, cave, len(code)))
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    mc = s['MCC_SITE']
    assert p.get(1, mc, 1) == b'\xe8' and mc + 5 + struct.unpack('<i', p.get(1, mc + 1, 4))[0] == s['MCC'][1], 'MenuProc call'
    p.put(1, mc + 1, struct.pack('<i', lab['se_ctl'] - (mc + 5)))
    hl = s['HL_SITE']
    assert p.get(1, hl, 6) == b'\x66\xc7\x46\x04\x00\x00'
    p.put(1, hl, b'\xe8' + struct.pack('<i', lab['se_hl'] - (hl + 5)) + b'\x90')
    print(f'exe: editable shirt numbers (MenuProc obj1+{mc:#x}, DrawPlayerEntries number obj1+{hl:#x}, '
          f'code obj1+{cave:#x}..{cave + len(code):#x})')
    return (cave + len(code) + 3) & ~3
