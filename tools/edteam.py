"""EDIT CUSTOM TEAMS: the players' looks and shirt numbers (4.0.6, Marco).

The editor (editTeamsMenu) shows 16 rows: the face button (entries 23..38, FIRE = EditTeamsChangePlayerFace, LEFT goes
nowhere), the number (entry 55, drawn for each row by the face buttons' before-draw EditTeamsPlayersBeforeDraw), the
name (39..54), the position. The team being edited is editTeamsTeam (684 bytes; OK copies it into CUSTOMS.EDT's slot).
- looks: FIRE on the face cycles ten looks (the game: three faces; blond.py: four): white, ginger, black, dark blond,
  then receding light / dark, shaved light / dark, white hair light / dark (the record's byte 25 bits 0 / 1 / 2 with
  face 0 or 2, blond.py's flags; bits 3..7 kept). The game's `add word [D0], 1` (the next face) -> et_next; the preview
  icon is blond's (icon_d1a / bicon read byte 25). Under SWOS++ (blond's SPPMMI gate: no looks there) and for a
  22-letter name (byte 25 is its terminator) the four faces only, byte 25 untouched;
- numbers: shirtedit's number box: se_ctl's `call se_row` (squadnum's sq_row, chained) -> et_row: an editor face button
  is a row (edi = its record, ebp = editTeamsTeam); se_ctl's direction test -> et_dir: RIGHT on the face lights the
  number (drawn right of the face; 4.0.6 RC3, Davide), LEFT goes nowhere, the next RIGHT after the box is the move
  to the name; UP / DOWN, digits, swap,
  FIRE / ENTER / LEFT / RIGHT done, ESC undo, the first edit pins the team (benchnum.PIN_BIT in editTeamsTeam's byte 23,
  saved with it); EditTeamsPlayersBeforeDraw's `mov [esi + 26h], ax / mov ax, [D7]` (entry 55's number) -> et_hl: the
  lit box's background on the edited row (entry 55 is one entry drawn for every row: plain on the others).
The original game ignores byte 25 (a look is a plain face there) and keeps the numbers as typed.
Code in obj3 at the chain's end (CONVENTIONS 23). Nothing without shirtedit (no career worlds).
"""
import re
import struct

import nasmcave
import shirtedit

ASM = r"""
et_row:                                 ; se_ctl's `call se_row` (ebx = the selected entry)
    call PREV                           ; the team screen's / squad screen's rows
    jnc .r
    cmp dword [ebx + 30h], EPBD         ; an Edit Teams face button (its before-draw)
    jne .no
    cmp byte [ebx + 8], 0FFh            ; LEFT goes nowhere from it
    jne .no
    movzx eax, word [ebx + 2]           ; ordinal: 23.. = rows 0..15
    sub eax, 23
    jb .no
    cmp eax, 16
    jae .no
    imul edi, eax, 38
    mov ebp, ETT
    lea edi, [ebp + 76 + edi]
    clc
    ret
.no:
    stc
.r:
    ret

et_dir:                                 ; se_ctl's idle `cmp word [MCD], 6` (jnz: no box): ZF = 1 opens the number box.
    push ebx                            ; 4.0.6 (Davide, RC3): on an editor face button RIGHT opens it (the number is
    mov ebx, [CURMENU + 0Ch]            ; drawn right of the face), LEFT goes nowhere; once the box was used on this
    test ebx, ebx                       ; row, the next RIGHT is the menu's move (to the name). Elsewhere LEFT, as before
    jz .game
    cmp dword [ebx + 30h], EPBD
    jne .game
    cmp word [ebx + 2], 23
    jb .game
    cmp word [ebx + 2], 38
    ja .game
    cmp ebx, [et_sel]                   ; just arrived on this face: a box used here before does not count
    je .same
    mov [et_sel], ebx
    cmp ebx, [SE_ENT]
    jne .same
    mov dword [SE_ENT], 0
.same:
    cmp word [MCD], 2                   ; RIGHT
    jne .no
    cmp ebx, [SE_ENT]                   ; the box was used on this row: RIGHT moves on (and forgets it: back on this
    je .on                              ; face, RIGHT opens it again - also when no idle frame saw the cursor away,
    cmp eax, eax                        ; SWOS++'s timer-fed keys)
    pop ebx
    ret
.on:
    mov dword [SE_ENT], 0
.no:
    test esp, esp
    pop ebx
    ret
.game:
    mov dword [et_sel], 0               ; (off the faces: back on one = arrived again)
    cmp word [MCD], 6
    pop ebx
    ret
et_sel: dd 0

et_hl:                                  ; EditTeamsPlayersBeforeDraw: replaces `mov [esi + 26h], ax / mov ax, [D7]`
    mov [esi + 26h], ax
    push eax
    mov word [esi + 1Ch], 0
    cmp byte [SE_ON], 0
    je .p
    mov eax, [A6]
    add eax, 76
    cmp eax, [SE_REC]
    jne .p
    mov word [esi + 1Ch], 2             ; a coloured background (shirtedit's lit box)
    mov word [esi + 1Eh], HL
.p:
    pop eax
    mov ax, [D7]
    ret

et_next:                                ; EditTeamsChangePlayerFace: replaces `add word [D0], 1` (D0 = the face 0..3,
    push eax                            ; A0 -> the player: his record at + 76)
    push ebx
    push esi
    mov esi, [A0]
    add esi, 76
    movzx eax, word [D0]
    cmp byte [SPPMMI], 66h              ; SWOS++: the four faces
    jne .face
    cmp byte [esi + 24], 0              ; a 22-letter name: byte 25 is its terminator
    jne .face
    mov bl, [esi + 25]
    test bl, 5
    jz .next                            ; a plain face: look = face
    xor eax, eax
    cmp word [D0], 2
    setae al                            ; dark
    test bl, 1
    jz .white
    add eax, 4                          ; receding 4 / 5
    test bl, 2
    jz .next
    add eax, 2                          ; shaved 6 / 7
    jmp .next
.white:
    add eax, 8                          ; white hair 8 / 9
.next:
    inc eax
    cmp eax, 10
    jb .set
    xor eax, eax
.set:
    and byte [esi + 25], 0F8h
    cmp eax, 4
    jae .look
    mov [D0], ax                        ; faces 0..3 (the game's `cmp 4` after us: no wrap)
    jmp .r
.look:
    sub eax, 4
    mov ebx, eax
    and ebx, 1                          ; dark
    shr eax, 1
    mov al, [et_bits + eax]
    or [esi + 25], al
    add ebx, ebx                        ; face 0 / 2
    mov [D0], bx
    jmp .r
.face:
    inc eax                             ; the game's +1 (its `cmp 4` wraps)
    mov [D0], ax
.r:
    pop esi
    pop ebx
    pop eax
    ret
et_bits: db 1, 3, 4                     ; receding, shaved, white hair
"""


def sites(p):
    """EditTeamsPlayersBeforeDraw, editTeamsTeam, the number's site in it, EditTeamsChangePlayerFace's `add word [D0], 1`,
    SWOSMainMenuInit's SWOS++ byte (blond's SPPMMI) and the variables (original bytes)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    pk = lambda x: re.escape(struct.pack('<I', x))
    d0, d7, a5, a6 = a0 - 32, a0 - 4, a0 + 20, a0 + 24
    one = lambda what, ms: (ms if len(ms) == 1 else (_ for _ in ()).throw(AssertionError((what, len(ms)))))[0]
    # mov esi,[A5]; mov ax,[esi+2]; mov [D0],ax; sub word [D0],23; mov ax,[D0]; mov bx,38; mul bx; mov [D0],ax;
    # mov [D0+2],dx; mov [A6], editTeamsTeam  (EditTeamsGetPlayerPointer: the same with [A0])
    bd = one('EditTeamsPlayersBeforeDraw', [m.start() for m in re.finditer(
        rb'\x8b\x35' + pk(a5) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d0) + rb'\x66\x83\x2d' + pk(d0) + rb'\x17\x66\xa1' + pk(d0)
        + rb'\x66\xbb\x26\x00\x66\xf7\xe3\x66\xa3' + pk(d0) + rb'\x66\x89\x15' + pk(d0 + 2) + rb'\xc7\x05' + pk(a6), d1, re.S)])
    ett = p.target(1, bd + 0x38)
    # its number: mov ax,[D0]; mov esi,[A0]; mov [esi+26h],ax; mov ax,[D7]; mov esi,[A0]; mov [esi+16h],ax
    hl = bd + one('number', [m.start() + 12 for m in re.finditer(
        rb'\x66\xa1' + pk(d0) + rb'\x8b\x35' + pk(a0) + rb'\x66\x89\x46\x26\x66\xa1' + pk(d7) + rb'\x8b\x35' + pk(a0)
        + rb'\x66\x89\x46\x16', d1[bd:bd + 0x100], re.S)])
    cyc = one('face cycle', [m.start() for m in re.finditer(rb'\x66\x83\x05' + pk(d0) + rb'\x01\x66\x83\x3d' + pk(d0)
                                                             + rb'\x03\x75', d1, re.S)])
    mmi = [m.start() for m in re.finditer(rb'\x66\xc7\x05.{4}\xff\xff\xe8.{4}\xe8.{4}\xeb\x00', d1, re.S)]
    assert len(mmi) == 2 and mmi[0] < 0x20000, [hex(x) for x in mmi]    # (blond.py's SPPMMI)
    return {'EPBD': (1, bd), 'ETT': ett, 'HL_SITE': hl, 'CYC_SITE': cyc, 'SPPMMI': (1, mmi[0]),
            'D0': (2, d0), 'D7': (2, d7), 'A0': (2, a0), 'A6': (2, a6)}


def patch(p, at):
    """et_* at obj3:at (the chain's end, after squadnum chained se_row); returns the end."""
    info = shirtedit.INFO
    if 'se_row' not in info:
        return at
    s = sites(p)
    d = p.le.obj_bytes(1)
    cs = info['row_call']                               # se_ctl's `call se_row` (squadnum's sq_row by now)
    prev = p.call_target(1, cs)
    sym = {k: v for k, v in s.items() if not k.endswith('_SITE')}
    sym.update(PREV=prev, SE_ON=(1, info['se_on']), SE_REC=(1, info['se_rec']), HL=(0, shirtedit.HL_COLOR),
               SE_ENT=(1, info['se_ent']), MCD=info['MCD'], CURMENU=info['CURMENU'])
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, cs, 0xE8, 3, lab['et_row'])
    for site, n, fx, name in ((s['HL_SITE'], 10, 6, 'et_hl'), (s['CYC_SITE'], 8, 3, 'et_next')):
        assert bytes(p.get(1, site, n)) == d[site:site + n], ('edteam: site already patched', name, hex(site))
        p.remove(1, site + fx)
        p.branch(1, site, 0xE8, 3, lab[name], n)
    da = info['dir_at']                                 # se_ctl's `cmp word [MCD], 6` (8 bytes, its MCD fixup at +3)
    assert bytes(p.get(1, da, 3)) == b'\x66\x83\x3d' and p.get(1, da + 7, 1) == b'\x06', ('edteam: dir site', hex(da))
    p.remove(1, da + 3)
    p.branch(1, da, 0xE8, 3, lab['et_dir'], 8)
    print(f'exe: edteam: EDIT CUSTOM TEAMS looks (10) + number box, obj3+{at:#x}..{at + len(code):#x} ({len(code)} B), '
          f'face obj1+{s["CYC_SITE"]:#x}, number obj1+{s["HL_SITE"]:#x}')
    return at + len(code)
