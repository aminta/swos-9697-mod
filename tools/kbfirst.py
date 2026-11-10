"""Keyboard first (4.0.6 fix A, Davide 04/11): a held keyboard direction replaces the stick's axis for that frame.

With a joypad device (g_inputControls 2, 3, 4, 6: Player1StatusProc reads stick 1, Player2StatusProc the keyboard) a stick
that reads off centre - not calibrated, worn, a port that reads a corner - beat the keyboard everywhere:
- the menus (MenuCheckControls): the up / down / left / right bytes are player 1's ORed with player 2's, and the
  direction is player 1's, player 2's only when player 1's is -1 - a stick held UP made DOWN on the keyboard dead;
- a match: the team controlled by player 1 reads the stick only (Joy1SetStatus -> g_pl1ControlFlags).
Here (off under SWOS++: its own controls; off with KEYBOARD ONLY and TWO JOYPADS, where the keyboard is not a second device):
- kf_menu (MenuCheckControls' `mov ax, pl1Direction` before the `jns` that keeps player 1's direction): player 2's
  direction >= 0 -> ax = -1, so the game takes player 2's direction; the axis player 2 holds (up / down, left / right)
  replaces the ORed bytes;
- kf_p1 (Player1StatusProc's `call Joy1SetStatus`, chained onto the call's current target): after the stick's flags the
  keyboard's (keyboardControlFlags) replace them axis by axis, when no team of the match is controlled by player 2
  (TeamGeneralInfo.playerNumber / playerCoachNumber 2: a second human on the keyboard keeps his own keys).
It is insurance, not the cure of the DOWN reports (the keyboard's own path: notes in internal/handoff/panchina.md).
"""
import re
import struct

import nasmcave

ASM = r"""
kf_p1:                                  ; Player1StatusProc: the stick's flags, then the keyboard's axes over them
    call J1S
    cmp byte [SWOSPP], 0FFh             ; (SWOS++: its own controls)
    jne .x
    cmp word [INCTL], 1                 ; (KEYBOARD ONLY: player 1 is the keyboard already; TWO JOYPADS: no keyboard)
    je .x
    cmp word [INCTL], 5
    je .x
    cmp word [TOP_PN], 2                ; (a team controlled by player 2: the keyboard is his)
    je .x
    cmp word [TOP_PN + 2], 2
    je .x
    cmp word [BOT_PN], 2
    je .x
    cmp word [BOT_PN + 2], 2
    je .x
    push eax
    push ebx
    mov bx, [KCF]
    mov ax, [PL1F]
    test bx, 3
    jz .h
    and ax, ~3
    push ebx
    and bx, 3
    or ax, bx
    pop ebx
.h: test bx, 0Ch
    jz .w
    and ax, ~0Ch
    and bx, 0Ch
    or ax, bx
.w: mov [PL1F], ax
    pop ebx
    pop eax
.x: ret

kf_menu:                                ; MenuCheckControls: ax = player 1's direction, or -1 when player 2 (the keyboard) holds one
    mov ax, [PL1DIR]
    cmp byte [SWOSPP], 0FFh
    jne .x
    cmp word [INCTL], 1
    je .x
    cmp word [INCTL], 5
    je .x
    cmp word [PL2DIR], 0
    jl .x
    mov al, [PL2UP]
    or al, [PL2DN]
    jz .h
    mov al, [PL2UP]
    mov [M_UP], al
    mov al, [PL2DN]
    mov [M_DN], al
.h: mov al, [PL2LT]
    or al, [PL2RT]
    jz .d
    mov al, [PL2LT]
    mov [M_LT], al
    mov al, [PL2RT]
    mov [M_RT], al
.d: mov ax, -1
.x: ret
"""


def find(p):
    """The game's sites and symbols (obj1, the original exe): Player1StatusProc's call Joy1SetStatus, MenuCheckControls'
    player-2 direction test (with the 4 ORs of player 2's bytes just before it), the two teams' playerNumber (MainKeysCheck's
    PAGE UP / PAGE DOWN bench keys)."""
    import controls
    d = p.le.obj_bytes(1)
    sym = controls.locate(p)
    buf, kcf, lk = sym['BUF'][1], sym['KCF'][1], sym['LASTKEY'][1]
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    P = lambda x: re.escape(struct.pack('<I', x))
    one = lambda pat: (lambda m: m[0].start() if len(m) == 1 else (_ for _ in ()).throw(AssertionError((pat, len(m)))))(
        list(re.finditer(pat, d, re.S)))
    s = {}
    a = one(rb'\x66\x83\x3d' + P(buf + 6) + rb'\x01\x75.\x66\x8b\x1d' + P(kcf) + rb'\x66\x89\x1d....\xeb.\xe8')
    s['p1'] = a + 0x1a                                  # (call Joy1SetStatus)
    sym['PL1F'] = fx[a + 20]
    m = one(rb'\x66\xa1....\x66\x0b\xc0\x79.\x66\xa1(....)\x66\xa3....\x66\xa1\1\x66\xa3')
    s['menu'] = m
    sym['PL1DIR'], sym['PL2DIR'] = fx[m + 2], fx[m + 13]
    names = ('LT', 'RT', 'UP', 'DN')                   # (the game's order: left, right, up, down; a0 pl2X / a2 D0 /
    for i, n in enumerate(names):                     #  a0 D0 / 08 05 X, 21 bytes each)
        o = m - 21 * (4 - i)
        assert d[o] == 0xA0 and d[o + 5] == 0xA2 and d[o + 10] == 0xA0 and d[o + 15:o + 17] == b'\x08\x05', (n, d[o:o + 21].hex())
        sym['PL2' + n], sym['M_' + n] = fx[o + 1], fx[o + 17]
    p2 = one(rb'\x66\x83\x3d' + P(buf + 6) + rb'\x05\x74.\x66\x8b\x1d' + P(kcf))   # Player2StatusProc: pl2Left first
    t = d.find(b'\x66\xa9\x04\x00\xc6\x05', p2, p2 + 0x40)
    assert t > 0 and fx[t + 6] == sym['PL2LT'], 'pl2Left'
    for key, k in ((0x49, 'BOT_PN'), (0x51, 'TOP_PN')):   # PAGE UP: bottomTeamData, PAGE DOWN: topTeamData
        b = one(rb'\x66\x83\x3d' + P(lk) + bytes([key]) + rb'\x75.\x66\xa1....\x66\x0b\xc0\x0f\x85....\x66\xa1....'
                rb'\x66\x0b\xc0\x75.\x66\xa1')
        sym[k] = fx[b + 27]
        assert fx[b + 38] == (sym[k][0], sym[k][1] + 2), (k, 'playerCoachNumber')
    assert sym['BOT_PN'][1] - sym['TOP_PN'][1] == 0x91, 'TeamGeneralInfo 145 B'
    sym['INCTL'] = (2, buf + 6)
    return s, sym


def patch(p, at):
    """Code at obj3:at; returns the end."""
    s, sym0 = find(p)
    d = p.le.obj_bytes(1)
    assert p.get(1, s['menu'], 6) == d[s['menu']:s['menu'] + 6], 'kbfirst menu site already patched'
    sym = {k: sym0[k] for k in ('KCF', 'SWOSPP', 'INCTL', 'PL1F', 'PL1DIR', 'PL2DIR', 'TOP_PN', 'BOT_PN')}
    sym.update({k: sym0[k] for k in sym0 if k[:3] in ('PL2', 'M_U', 'M_D', 'M_L', 'M_R')})
    sym['J1S'] = p.call_target(1, s['p1'])              # (chained: Joy1SetStatus, or another hook on it)
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['p1'], 0xE8, 3, lab['kf_p1'])
    p.remove(1, s['menu'] + 2)                          # (the overwritten mov ax, pl1Direction's fixup)
    p.branch(1, s['menu'], 0xE8, 3, lab['kf_menu'], 6)
    LABELS.update(lab)
    print(f'exe: keyboard first: code obj3+{at:#x} ({len(code)} B), sites p1 {s["p1"]:#x} menu {s["menu"]:#x}')
    return at + len(code)


LABELS = {}
