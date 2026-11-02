"""CONTROLS B (4.0.6, Marco 29/10): two humans on ONE keyboard - player 2's own key set (internal/handoff/motore-kbd2.md).

The game has one key set (SETUP.DAT +96..+100, g_up/down/left/right/fireScanCode) and one key word, keyboardControlFlags
(SetKeyboardControlFlags, from Int9KeyboardHandler and the harness's feeder: 1 up, 2 down, 4 left, 8 right, 20h fire,
the opposite direction cleared). With g_inputControls 1 (KEYBOARD ONLY) Player1StatusProc and Player2StatusProc both
read that word, so two human teams moved together. A team is a player's by the fire pressed on its PLAY MATCH screen
(SetupPlayers / ShowPlayMatchMenu: D0 = 1 or 2), and the menus OR both players' input (MenuCheckControls).

Here, with the P2 set on (K2_ON) and the device KEYBOARD ONLY:
- kb_set (the end of SetKeyboardControlFlags, `mov keyboardControlFlags, bx / retn`): the same make / break rules for
  the 5 P2 scan codes into K2_FLAGS (interrupt context: ax / bx only, as the game's);
- kb_p2 (Player2StatusProc's `mov bx, keyboardControlFlags`): bx = K2_FLAGS;
- kb_rst (the game's 6 `mov keyboardControlFlags, 0`: SWOS start, GameLoop, ShowMenu, RestorePreviousMenu,
  CommitInputTextToMenuEntry): K2_FLAGS cleared too;
- kb_load (Initialization's `call ReadSetupDat`, chained onto the call's current target): then CONTROL2.DAT (our own file - SETUP.DAT is read whole into its
  105-byte buffer, a longer one would run over it; INSTALL / SETUP.EXE rewrite it), 9 bytes: 'K2', version 1, on, the 5
  scan codes (up, down, left, right, fire). No file / another magic: off, the default keys (W S A D, left SHIFT: key
  positions - Z S Q D on AZERTY; never CTRL, P1's fire, one scan code for both).
Off under SWOS++ (its own controls; controls.locate's SWOSPP byte). The CONTROLS page (controls.py) edits and saves it.
"""
import re
import struct

import nasmcave

DEFAULT = (0x11, 0x1F, 0x1E, 0x20, 0x2A)         # W, S, A, D, left SHIFT (up, down, left, right, fire)
FILE = b'CONTROL2.DAT'
MAGIC = b'K2\x01'

ASM = r"""
kb_set:                                 ; SetKeyboardControlFlags' end (ax / bx free there, as the game's)
    mov [KCF], bx
    cmp byte [K2_ON], 0
    je .x
    cmp byte [SWOSPP], 0FFh             ; (SWOS++: its own controls)
    jne .x
    mov ax, [SCAN]
    mov bx, [K2_FLAGS]
    test ax, 80h
    jnz .rel
    cmp al, [K2_KEYS + 4]
    jne .r
    or bx, 20h
.r: cmp al, [K2_KEYS + 3]
    jne .l
    or bx, 8
    and bx, ~4
.l: cmp al, [K2_KEYS + 2]
    jne .d
    or bx, 4
    and bx, ~8
.d: cmp al, [K2_KEYS + 1]
    jne .u
    or bx, 2
    and bx, ~1
.u: cmp al, [K2_KEYS]
    jne .w
    or bx, 1
    and bx, ~2
    jmp .w
.rel:
    and al, 7Fh
    cmp al, [K2_KEYS + 4]
    jne .r2
    and bx, ~20h
.r2: cmp al, [K2_KEYS + 3]
    jne .l2
    and bx, ~8
.l2: cmp al, [K2_KEYS + 2]
    jne .d2
    and bx, ~4
.d2: cmp al, [K2_KEYS + 1]
    jne .u2
    and bx, ~2
.u2: cmp al, [K2_KEYS]
    jne .w
    and bx, ~1
.w: mov [K2_FLAGS], bx
.x: ret

kb_p2:                                  ; Player2StatusProc: bx = player 2's key word
    mov bx, [KCF]
    cmp byte [K2_ON], 0
    je .x
    cmp byte [SWOSPP], 0FFh
    jne .x
    cmp word [INCTL], 1                 ; (KEYBOARD ONLY: the other devices as the game's)
    jne .x
    mov bx, [K2_FLAGS]
.x: ret

kb_rst:                                 ; the game's `mov keyboardControlFlags, 0`
    mov word [KCF], 0
    mov word [K2_FLAGS], 0
    ret

kb_load:                                ; Initialization: SETUP.DAT, then our CONTROL2.DAT
    call RSD
    pushad
    mov edx, K2_NAME
    mov eax, 3D00h
    int 21h
    jc .x
    mov ebx, eax
    mov edx, K2_BUF
    mov ecx, 9
    mov ah, 3Fh
    int 21h
    mov ah, 3Eh
    int 21h
    cmp word [K2_BUF], 'K2'
    jne .x
    cmp byte [K2_BUF + 2], 1
    jne .x
    mov al, [K2_BUF + 3]
    mov [K2_ON], al
    mov eax, [K2_BUF + 4]
    mov [K2_KEYS], eax
    mov al, [K2_BUF + 8]
    mov [K2_KEYS + 4], al
.x: popad
    ret
"""


def find(p):
    """The game's sites (obj1, the original exe): SetKeyboardControlFlags' end, Player2StatusProc's key word read, the
    6 resets, Initialization's call ReadSetupDat."""
    import controls
    import joyfix
    d = p.le.obj_bytes(1)
    sym = controls.locate(p)
    kcf, buf = sym['KCF'][1], sym['BUF'][1]
    P = lambda x: re.escape(struct.pack('<I', x))
    one = lambda pat: (lambda m: m[0].start() if len(m) == 1 else (_ for _ in ()).throw(AssertionError((pat, len(m)))))(
        list(re.finditer(pat, d, re.S)))
    s = {'set': one(rb'\x66\x89\x1d' + P(kcf) + rb'\xc3'),
         'p2': one(rb'\x66\x83\x3d' + P(buf + 6) + rb'\x05\x74.\x66\x8b\x1d' + P(kcf) + rb'\x66\x89\x1d') + 10,
         'rst': [m.start() for m in re.finditer(rb'\x66\xc7\x05' + P(kcf) + rb'\x00\x00', d)]}
    assert len(s['rst']) == 6, s['rst']
    rs = one(joyfix.RSD_PAT)
    s['rsd'] = rs
    s['load'] = [i for i in range(len(d) - 5) if d[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d, i + 1)[0] == rs]
    assert len(s['load']) == 1, s['load']
    s['load'] = s['load'][0]
    sym.update({'INCTL': (2, buf + 6)})
    return s, sym


def patch(p, at, lang):
    """Code + data at obj3:at (after the previous obj3 block's end); returns the end."""
    s, sym0 = find(p)
    d = p.le.obj_bytes(1)
    for k, n in (('set', 8), ('p2', 7)):
        assert p.get(1, s[k], n) == d[s[k]:s[k] + n], ('kbd2 site already patched', k)
    for r in s['rst']:
        assert p.get(1, r, 9) == d[r:r + 9], ('kbd2 reset already patched', hex(r))
    prev = p.call_target(1, s['load'])                  # (chained: joyfix's hook on it, or ReadSetupDat itself)
    db = lambda b: ', '.join(str(x) for x in b)
    src = ASM + (f'K2_ON: db 0\nK2_KEYS: db {db(DEFAULT)}, 0\nK2_FLAGS: dw 0\nK2_BUF: times 12 db 0\n'
                 f'K2_NAME: db {db(FILE + b"\0")}\n')
    sym = {k: sym0[k] for k in ('KCF', 'SCAN', 'SWOSPP', 'INCTL')}
    sym['RSD'] = prev
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['set'] + 3)                           # (the overwritten instructions' fixups)
    p.branch(1, s['set'], 0xE9, 3, lab['kb_set'], 8)
    p.remove(1, s['p2'] + 3)
    p.branch(1, s['p2'], 0xE8, 3, lab['kb_p2'], 7)
    for r in s['rst']:
        p.remove(1, r + 3)
        p.branch(1, r, 0xE8, 3, lab['kb_rst'], 9)
    p.branch(1, s['load'], 0xE8, 3, lab['kb_load'])
    LABELS.update(lab)
    print(f'exe: CONTROLS B (player 2 key set, {FILE.decode()}): code obj3+{at:#x} ({len(code)} B), sites '
          f'set {s["set"]:#x} p2 {s["p2"]:#x} resets {[hex(x) for x in s["rst"]]} load {s["load"]:#x}')
    return at + len(code)


LABELS = {}
