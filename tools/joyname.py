"""Names with the joystick only (4.2, Gianfranco 14/11: Android RetroArch + DOSBox Pure, the on-screen keyboard is
microscopic). Every name the game asks for goes through InputText / InputTextKeyLoop (player / team / coach names in
EDIT CUSTOM TEAMS, the career's name, DIY competition names, the save and tactic file names): one hook covers them all.

An arcade letter picker inside that loop, at its `call FilterKeys` (jn_filt chains to what was there):
- UP / DOWN: the character right of the cursor cycles through the field's characters (names: space, A..Z, 0..9 and
  the punctuation keytext types; the save dialog - g_allowExtraCharsFlag - A..Z, 0..9, - and _); at the end of the name
  (cursor on the terminator) UP appends a character, while the name is shorter than the field, and DOWN deletes the
  last one (as BACKSPACE: no chord, for touch overlays and arrows-only pads; 4.2 row 153); held: repeats after JN_REP1
  loops, then every JN_REP2;
- LEFT / RIGHT: the cursor (the game's own 21 / 22);
- FIRE: released = the name confirmed (as ENTER), trailing spaces trimmed; held JN_LONG loops = cancelled (as ESC);
  FIRE held + LEFT = delete left of the cursor (as BACKSPACE); a direction held with FIRE restarts the long count
  (row 153: several deletes with FIRE held never end in a cancel). The FIRE that opened the field counts only once
  released (no instant confirm).
- The keyboard's UP / DOWN arrows cycle the same way (a pad mapped to the arrows: RetroArch / DOSBox Pure's
  keyboard mapping); everything typed works as before. The stick is read (Joy1SetStatus) only when the controls are not
  KEYBOARD ONLY; a held keyboard direction (keyboardControlFlags) masks the stick's directions (no double moves with
  keytext's arrows).
- Off under SWOS++ (its own keyboard, as keytext).

The state is reset at each InputText (its deadInputTextVar, written 0 there and read nowhere: our 'new field' flag).
Test builds: JOYNAME_FAKE=1 reads the stick's flags from jn_fake (poked by the harness) instead of the port."""
import os
import re
import struct

import nasmcave

JN_REP1, JN_REP2, JN_LONG = 10, 3, 40
NAMES = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
SAVE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
LABELS = {}

ASM = r"""
jn_filt:                                ; InputTextKeyLoop's `call FilterKeys` (chained)
    call FILT
    pushad
    call jn_b
jn_b:
    pop ebp                             ; ebp: our state (jn_* relative to jn_b)
    xor ecx, ecx                        ; cx = the code for D1 at the end (0: none)
    cmp byte [SWOSPP], 0FFh             ; (FFh: the game's own keyboard; else SWOS++'s, as keytext: off)
    jne .out
    cmp word [D1], 0                    ; a typed key: nothing to do
    jne .out
    mov eax, DEAD
    cmp word [eax], cx                  ; a new field: what the stick holds now is no edge
    jne .go
    inc word [eax]
    mov [ebp + jn_fire - jn_b], cl
    mov byte [ebp + jn_prev - jn_b], 0FFh
.go:mov ax, [LASTKEY]                   ; the keyboard's UP / DOWN arrows (they type nothing)
    cmp al, 48h
    je .up
    cmp al, 50h
    je .down
FAKE_
    cmp word [CTL], 1                   ; KEYBOARD ONLY: no stick
    je .out
    call JOY1
    movzx eax, word [PL1CF]
.have:
    test byte [KCF], 0Fh                ; a held keyboard direction: the stick's directions ignored
    jz .j
    and al, 0F0h
.j: mov bl, al
    and bl, 0Fh
    mov bh, [ebp + jn_prev - jn_b]
    mov [ebp + jn_prev - jn_b], bl
    cmp bh, 0FFh                        ; (the first read of a field: no edge)
    jne .f
    mov bh, bl
.f: lea edi, [ebp + jn_fire - jn_b]
    test al, 20h
    jz .frel
    cmp byte [edi], 0                   ; held since the field opened: not armed yet
    je .out
    cmp byte [edi], 1
    jne .fh
    mov word [edi], 2                   ; (jn_fire 2, jn_ft 0)
.fh:test bl, bl                         ; 4.2 (row 153): long = FIRE held with no direction - a direction held with
    jz .fi                              ;  FIRE (FIRE + LEFT deletes) restarts the count, so deletes never end in ESC
    mov byte [edi + 1], 0
.fi:inc byte [edi + 1]
    cmp byte [edi + 1], LONG_
    mov cl, 1                           ; long FIRE: cancel (ESC)
    jae .out
    mov cl, 0
    test bl, 4                          ; FIRE + LEFT (its edge): delete left (BACKSPACE)
    jz .out
    test bh, 4
    jnz .out
    mov cl, 8
    mov byte [edi], 3
    jmp .out
.frel:
    cmp byte [edi], 2
    mov byte [edi], 1                   ; (released: armed; 3, FIRE + LEFT used: no confirm)
    je .commit
    lea edi, [ebp + jn_cnt - jn_b]
    test bl, bl
    jz .zero
    cmp bl, bh
    jne .act
    inc byte [edi]                      ; held: the repeat
    cmp byte [edi], REP1_
    jb .out
    mov byte [edi], REP1_ - REP2_
    db 66h, 0B8h                        ; (mov ax, imm16: skips the next 2-byte instruction)
.act:
    mov [edi], cl
    shr bl, 1
    jc .up
    shr bl, 1
    jc .down
    mov cl, 21                          ; LEFT / RIGHT: the game's cursor keys
    shr bl, 1
    jc .out
    inc ecx
    jmp .out
.zero:
    mov [edi], cl
    jmp .out
.up:push 1
    jmp .cy
.down:
    push -1
.cy:pop eax
    call jn_cyc
    jmp .out
.commit:
    call jn_end                         ; trailing spaces off, the cursor kept inside the name
.t: cmp edi, BUF
    je .c
    cmp byte [edi - 1], ' '
    jne .c
    dec edi
    mov [edi], cl
    jmp .t
.c: cmp [A0], edi
    jbe .ok
    mov [A0], edi
.ok:mov cl, 13                          ; confirm (ENTER)
.out:
    jecxz .r
    mov [D1], cx
.r: popad
    ret

jn_end:                                 ; edi = the name's terminator
    mov edi, BUF
.l: cmp byte [edi], 0
    je .r
    inc edi
    jmp .l
.r: ret

jn_cyc:                                 ; eax = +1 / -1: the character at the cursor (A0) one step on in the field's set
    mov esi, [A0]
    lea edx, [ebp + jn_names - jn_b]
    mov ecx, NNAMES_
    cmp word [ALLOWX], 0
    je .set
    lea edx, [ebp + jn_save - jn_b]
    mov cl, NSAVE_
.set:
    cmp byte [esi], 0
    jne .find
    test eax, eax                       ; 4.2 (row 153): DOWN at the end = delete the last character (BACKSPACE), no
    jns .app                            ;  chord (touch overlays, arrows-only pads); held = repeat; UP appends
    xor ecx, ecx
    cmp esi, BUF
    je .r0
    mov cl, 8
.r0:ret
.app:
    push ecx
    call jn_end                         ; at the end: append one, if the field has room
    pop ecx
    sub edi, BUF
    cmp di, [D7]                        ; (D7 = the field's length - 1)
    jae .r
    mov word [esi], 20h                 ; (a space, 0: names UP 'A'; file names: not in their set, UP the first)
.find:
    mov bl, [esi]
    xor edi, edi
.f: cmp [edx + edi], bl
    je .step
    inc edi
    cmp edi, ecx
    jb .f
    xor edi, edi                        ; not in the set: UP the first, DOWN the last
    test eax, eax
    jns .put
.step:
    add edi, eax
    jns .hi
    add edi, ecx
.hi:cmp edi, ecx
    jb .put
    xor edi, edi
.put:
    mov bl, [edx + edi]
    mov [esi], bl
.r: xor ecx, ecx
    ret

jn_prev: db 0
jn_fire: db 0
jn_ft:   db 0
jn_cnt:  db 0
JNMARK_
jn_fake: dw 0
"""
FAKE = """    movzx eax, word [ebp + jn_fake - jn_b]   ; (JOYNAME_FAKE test build: the harness's flags, 8000h | flags)
    btr eax, 15
    jc .have
"""


def sites(p):
    """The game's sites (obj1, the original exe): (InputTextKeyLoop's FilterKeys call, {symbol: (obj, off)})."""
    c = p.le.obj_bytes(1)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    loop = [m.start() for m in re.finditer(rb'\xe8....\xe8....\x66\xa1....\x66\x0b\xc0\x74.\x66\x83\x3d....\x0d\x0f\x84',
                                           c, re.S)]
    assert len(loop) == 1, ('InputTextKeyLoop', loop)
    k = loop[0]
    assert c[k - 9:k - 6] == b'\x66\xc7\x05' and c[k - 2:k] == b'\0\0', ('InputText: mov deadInputTextVar, 0', c[k - 9:k])
    cl = [m.start() for m in re.finditer(rb'\x81\x3d........\x0f\x84', c[k:k + 0x300], re.S)]
    assert cl, 'InputTextMoveCursorLeft: cmp A0, offset inMenuKeyboardBuffer'
    ic = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\x39\x05....\x0f\x84', c[k:k + 0x400], re.S)]
    assert ic, 'InputTextInsertCharacter: mov ax, D7; cmp D0, ax'
    lk = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\xa3....\x66\xc7\x05....\x00\x00\x66\x0f\xb6\x05', c, re.S)]
    assert len(lk) == 1, ('MenuCheckControls: mov ax, lastKey (two joypads)', lk)
    ps = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\x01\x75.\x66\x8b\x1d....\x66\x89\x1d....\xeb.\xe8', c, re.S)]
    assert ps, 'Player1StatusProc: KEYBOARD_ONLY test, Joy1SetStatus call'
    ps = ps[0]
    joy = ps + 26 + 5 + struct.unpack_from('<i', c, ps + 27)[0]
    import controls
    sym = controls.locate(p)
    v = {'D1': fx[k + 12], 'DEAD': fx[k - 6], 'A0': fx[k + cl[0] + 2], 'BUF': fx[k + cl[0] + 6],
         'D7': fx[k + ic[0] + 2], 'LASTKEY': fx[lk[0] + 2], 'CTL': fx[ps + 3], 'KCF': fx[ps + 13],
         'PL1CF': fx[ps + 20], 'JOY1': (1, joy), 'SWOSPP': sym['SWOSPP']}
    assert v['KCF'] == sym['KCF'], (v['KCF'], sym['KCF'])
    return k + 5, v


def patch(p, at, lang):
    """Code + sets at obj3:at, chained onto InputTextKeyLoop's FilterKeys call; returns the end."""
    import complist
    import keytext
    site, v = sites(p)
    assert p.get(1, site, 1) == b'\xe8', 'InputTextKeyLoop: not a call at FilterKeys'
    filt = p.call_target(1, site)
    v['ALLOWX'] = keytext.find(p)[1]['ALLOWX']
    names = NAMES + ''.join(c for c in keytext.NEW if c not in NAMES and c != '_')
    assert set(names) - {' '} <= complist.FONT and set(SAVE) - {'_'} <= complist.FONT, (lang, names)
    fake = bool(os.environ.get('JOYNAME_FAKE'))
    db = lambda t: ', '.join(str(ord(ch)) for ch in t)
    src = nasmcave.sub(nasmcave.sub(ASM, 'FAKE_', FAKE if fake else ''), 'JNMARK_', '    db "JNFAKE"' if fake else '') + f'jn_names: db {db(names)}\njn_save: db {db(SAVE)}\n'
    sym = dict(v, FILT=filt, REP1_=(0, JN_REP1), REP2_=(0, JN_REP2), LONG_=(0, JN_LONG), NNAMES_=(0, len(names)),
               NSAVE_=(0, len(SAVE)))
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, site, 0xE8, 3, lab['jn_filt'], 5)
    LABELS.clear()                              # (HOSTTEST_SYMS: obj3 labels + the game's sites; test_joyname)
    LABELS.update({k: (3, o) for k, o in lab.items() if isinstance(o, int)})
    LABELS.update({k: tuple(x) for k, x in sym.items() if isinstance(x, tuple) and len(x) == 2 and x[0] in (1, 2, 3, 4)})
    print(f'exe: joystick names (joyname, {len(names)} name chars, {len(SAVE)} file chars{", JOYNAME_FAKE" if fake else ""}): '
          f'code obj3+{at:#x} ({len(code)} B), site InputTextKeyLoop FilterKeys call obj1+{site:#x} -> {filt}')
    return at + len(code)
