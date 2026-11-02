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


TEXTS = {   # (the CONTROLS page's 4th device value, the two columns' headers, the ghosting note - proposed 02/11, Davide's ok
            # pending)
    'it': ("G1 E G2 SU TASTIERA", "G1", "G2",
           "SU MOLTE TASTIERE TROPPI TASTI PREMUTI INSIEME NON VENGONO LETTI: SCEGLI TASTI LONTANI TRA LORO"),
    'en': ("P1 AND P2 ON KEYBOARD", "P1", "P2", "MANY KEYBOARDS MISS KEYS PRESSED TOGETHER: PICK KEYS FAR APART"),
    'fr': ("J1 ET J2 AU CLAVIER", "J1", "J2",
           "BEAUCOUP DE CLAVIERS PERDENT DES TOUCHES APPUYEES ENSEMBLE : CHOISISSEZ DES TOUCHES ELOIGNEES"),
    'de': ("S1 UND S2 AN DER TASTATUR", "S1", "S2",
           "VIELE TASTATUREN ERKENNEN GLEICHZEITIG GEDRUECKTE TASTEN NICHT: WEIT AUSEINANDER LIEGENDE TASTEN WAEHLEN"),
}
K2_DEV = 7                                      # (the page's WORK device for this mode: 1 + CONTROL2.DAT on when saved)
LAB_W, COL_X, COL_W = 96, (108, 210), 100       # (the two-column rows, packed coordinates: labels, P1 / P2 values)

# The CONTROLS page (controls.py) in this mode: its menu copied into obj3 with 7 entries more - 19 / 20 the column
# headers, 21..25 player 2's keys (WORK + 101..105 while the page is open: past SETUP.DAT's fields, inside WORK's 108
# bytes; ct_draw's key capture writes WORK + 96 + KIDX, KIDX 5..9 here, and checks a key against all 10 - its loop's
# 5 made 10: a P1 key may not be a P2 key in any mode). kc_init: the keys into WORK, KEYBOARD ONLY with CONTROL2.DAT
# on shown as this mode (K2_DEV), the rows' geometry kept; kc_dev: 1 -> 3 -> 5 -> K2_DEV -> 1; kc_draw (every frame,
# after ct_draw): the mode's texts, columns, rows shown and links over ct_refresh's; kc_save: K2_DEV saved as 1,
# CONTROL2.DAT written (DOS create), then ct_save.
ASM_UI = r"""
kc_init:
    pushad
    mov eax, [K2_KEYS]
    mov [WORK + 101], eax
    mov al, [K2_KEYS + 4]
    mov [WORK + 105], al
    cmp word [WORK + 6], 1
    jne .d
    cmp byte [K2_ON], 0
    je .d
    mov word [WORK + 6], K2_DEV
.d: popad
    call CT_INIT
    pushad
    mov esi, MENU_ + 16h + 3 * 38h + 14h    ; (rows 3..12: x / width as unpacked)
    mov edi, KC_GEOM
    mov ecx, 10
.g: mov eax, [esi]                       ; (x)
    mov [edi], ax
    mov ax, [esi + 4]                   ; (width)
    mov [edi + 2], ax
    add esi, 38h
    add edi, 4
    loop .g
    popad
    jmp kc_fix

kc_draw:
    call CT_DRAW
kc_fix:                                 ; this mode's rows over ct_refresh's
    pushad
    mov esi, MENU_ + 16h
    cmp word [WORK + 6], K2_DEV
    je .k2
    xor ecx, ecx                        ; (other modes: the page as controls.py made it)
.r: mov ax, [KC_GEOM + ecx * 4]
    imul edx, ecx, 38h
    mov [esi + 3 * 38h + 14h + edx], ax
    mov ax, [KC_GEOM + ecx * 4 + 2]
    mov [esi + 3 * 38h + 18h + edx], ax
    inc ecx
    cmp ecx, 10
    jb .r
    xor ecx, ecx
.h: imul edx, ecx, 38h
    mov word [esi + 19 * 38h + 4 + edx], 1
    inc ecx
    cmp ecx, 7
    jb .h
    mov byte [esi + 8 * 38h + 9], 0FFh
    mov byte [esi + 9 * 38h + 9], 0FFh
    mov byte [esi + 10 * 38h + 9], 0FFh
    mov byte [esi + 11 * 38h + 9], 0FFh
    mov byte [esi + 12 * 38h + 9], 0FFh
    jmp .x
.k2:
    mov dword [esi + 2 * 38h + 26h], S_DVK
    xor ecx, ecx
.c: imul edx, ecx, 38h                  ; labels narrower, P1's values in the first column
    mov ax, [KC_GEOM + ecx * 4 + 2]
    sub ax, 140 - LAB_W
    mov [esi + 3 * 38h + 18h + edx], ax
    mov ax, [KC_GEOM + 20 + ecx * 4]
    sub ax, 154 - COL_X1
    mov [esi + 8 * 38h + 14h + edx], ax
    mov word [esi + 8 * 38h + 18h + edx], COL_W
    lea eax, [ecx + 21]                 ; P1 key i -> right: P2 key i
    mov [esi + 8 * 38h + 9 + edx], al
    movzx eax, byte [WORK + 101 + ecx]  ; P2 key i: its name, links
    and eax, 7Fh
    imul eax, REC_
    add eax, KEYTAB
    mov [esi + 21 * 38h + 26h + edx], eax
    lea eax, [ecx + 8]
    mov [esi + 21 * 38h + 8 + edx], al
    mov byte [esi + 21 * 38h + 9 + edx], 0FFh
    lea eax, [ecx + 20]
    test ecx, ecx
    jnz .u
    mov al, 2
.u: mov [esi + 21 * 38h + 0Ah + edx], al
    lea eax, [ecx + 22]
    cmp ecx, 4
    jb .dn
    mov al, 17
.dn: mov [esi + 21 * 38h + 0Bh + edx], al
    inc ecx
    cmp ecx, 5
    jb .c
    xor ecx, ecx
.v: imul edx, ecx, 38h                  ; headers + P2's keys shown
    mov word [esi + 19 * 38h + 4 + edx], 0
    inc ecx
    cmp ecx, 7
    jb .v
    mov word [esi + 13 * 38h + 4], 1    ; (no joypad: no calibration)
    mov word [esi + 14 * 38h + 4], 1
    mov byte [esi + 12 * 38h + 0Bh], 17
    mov byte [esi + 17 * 38h + 0Ah], 12
    mov byte [esi + 18 * 38h + 0Ah], 25
    cmp byte [MODE], 0                  ; (the ghosting note in place of the hint)
    jne .x
    cmp byte [DUP], 0
    jne .x
    mov dword [esi + 15 * 38h + 26h], S_GH1
    mov dword [esi + 16 * 38h + 26h], S_GH2
.x: popad
    ret

kc_dev:                                 ; the device row: 1 -> 3 -> 5 -> K2_DEV -> 1
    cmp byte [MODE], 0
    jne .x
    cmp word [WORK + 6], 5
    je .k
    cmp word [WORK + 6], K2_DEV
    jne CT_DEV
    mov word [WORK + 6], 1
    jmp .r
.k: mov word [WORK + 6], K2_DEV
.r: call CT_REFRESH
.x: ret

kc_save:                                ; SAVE: CONTROL2.DAT, then the game's (ct_save: SETUP.DAT, the page closed)
    cmp byte [MODE], 0
    jne CT_SAVE
    pushad
    xor eax, eax
    cmp word [WORK + 6], K2_DEV
    jne .o
    mov word [WORK + 6], 1
    inc eax
.o: mov [K2_ON], al
    mov [K2_REC + 3], al
    mov eax, [WORK + 101]
    mov [K2_KEYS], eax
    mov [K2_REC + 4], eax
    mov al, [WORK + 105]
    mov [K2_KEYS + 4], al
    mov [K2_REC + 8], al
    mov edx, K2_NAME
    xor ecx, ecx
    mov ah, 3Ch
    int 21h
    jc .n
    mov ebx, eax
    mov edx, K2_REC
    mov ecx, 9
    mov ah, 40h
    int 21h
    mov ah, 3Eh
    int 21h
.n: popad
    jmp CT_SAVE
""" + ''.join(f"kc_k{5 + i}:\n    mov byte [KIDX], {5 + i}\n    jmp CT_KEY\n" for i in range(5))


def menu_copy(lang, at, base, off, ptrs, m_at, data):
    """controls.py's page (data[m_at:], its terminator dropped) + entries 19..25, for obj3:at. Returns (bytes, pointers
    [(offset in it, target name or (obj, offset))])."""
    import controls
    T = TEXTS[lang]
    pg = bytearray(data[m_at:])
    assert struct.unpack_from('<h', pg, len(pg) - 2)[0] == -999
    del pg[-2:]
    out = [(o - m_at, t_obj, t) for o, t_obj, t in ptrs if o >= m_at]

    def entry(x, y, w, h, nav=None, color=None, text=None, select=None):
        b = bytearray(struct.pack('<hhhh', x, y, w, h))
        if nav:
            b += struct.pack('<H', 2) + bytes(v & 0xFF for v in nav)
        if color is not None:
            b += struct.pack('<HH', 4, color)
        if text is not None:
            b += struct.pack('<HH', 8, 0)
            out.append((len(pg) + len(b), 2, text))
            b += b'\0\0\0\0'
        if select is not None:
            b += struct.pack('<H', 13)
            out.append((len(pg) + len(b), 3, select))
            b += b'\0\0\0\0'
        pg.extend(b + b'\0\0')

    for x in (10, 154):                         # (Davide 02/11: the headers touched the device row's box - its row 4 px
        o = [m.start() for m in re.finditer(re.escape(struct.pack('<hhhh', x, 30, controls.W, 11)), pg)]
        assert len(o) == 1, (x, o)              # up, 26..37; headers 39..46; key rows from 48)
        struct.pack_into('<h', pg, o[0] + 2, 26)
    entry(COL_X[0], 39, COL_W, 7, text=('S_H1',))
    entry(COL_X[1], 39, COL_W, 7, text=('S_H2',))
    for i in range(5):
        entry(COL_X[1], 48 + 12 * i, COL_W, 11, nav=(8 + i, -1, 20 + i if i else 2, 22 + i if i < 4 else 17),
              color=controls.VALUE_COL, text='empty', select=f'kc_k{5 + i}')
    pg += struct.pack('<h', -999)
    return bytes(pg), out


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
    import controls
    import zones
    C = controls.LAST                                   # (controls.patch ran first: its labels and data block)
    T, TC = TEXTS[lang], controls.TEXTS[lang]
    assert controls.px(T[0]) <= controls.W - 2, T[0]
    assert all(controls.px(x) <= LAB_W - 2 for x in TC['keys']), TC['keys']
    assert all(controls.px(x) <= COL_W - 2 for x in controls.key_names(lang)[:0x60]), 'a key name too wide'
    gh = controls.lines(T[3])
    db = lambda b: ', '.join(str(x) for x in b)
    st = lambda x: db(x.encode('latin-1') + b'\0')
    src = ASM + ASM_UI + (f'K2_ON: db 0\nK2_KEYS: db {db(DEFAULT)}, 0\nK2_FLAGS: dw 0\nK2_BUF: times 12 db 0\n'
                          f'K2_NAME: db {db(FILE + b"\0")}\nK2_REC: db {db(MAGIC)}, 0, {db(DEFAULT)}\n'
                          f'KC_GEOM: times 40 db 0\nS_DVK: db {st(T[0])}\nS_H1: db {st(T[1])}\nS_H2: db {st(T[2])}\n'
                          f'S_GH1: db {st(gh[0])}\nS_GH2: db {st(gh[1])}\n')
    sym = {k: sym0[k] for k in ('KCF', 'SCAN', 'SWOSPP', 'INCTL')}
    sym['RSD'] = prev
    v = C['base'] + C['off']['vars']
    sym.update({'CT_' + k.upper(): (1, C['lab']['ct_' + k]) for k in ('init', 'draw', 'refresh', 'dev', 'save', 'key')})
    sym.update({'WORK': (1, C['base'] + C['off']['work']), 'MODE': (1, v), 'KIDX': (1, v + 2), 'DUP': (1, v + 5),
                'KEYTAB': (1, C['base'] + C['off']['keytab']), 'REC_': (0, controls.REC), 'MENU_': zones._current_menu(p),
                'K2_DEV': (0, K2_DEV), 'LAB_W': (0, LAB_W), 'COL_X1': (0, COL_X[0]), 'COL_W': (0, COL_W)})
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
    # the CONTROLS page: its menu copy after the code (obj3), ct_open's `mov dword [A6], CTMENU` to it, the key
    # capture's duplicate check over the 10 keys
    m_at = (at + len(code) + 3) & ~3
    pg, mp = menu_copy(lang, m_at, C['base'], C['off'], C['ptrs'], C['m_at'], C['data'])
    assert not any(p.get(3, m_at, len(pg)))
    p.put(3, m_at, pg)
    over = {'ct_init': 'kc_init', 'ct_draw': 'kc_draw', 'ct_dev': 'kc_dev', 'ct_save': 'kc_save'}
    for o, t_obj, t in mp:
        if t_obj == 1 and t in over:
            p.add_ptr(3, m_at + o, 3, lab[over[t]])
        elif t_obj == 1:
            p.add_ptr(3, m_at + o, 1, C['lab'][t])
        elif t_obj == 3 or isinstance(t, tuple):
            p.add_ptr(3, m_at + o, 3, lab[t[0] if isinstance(t, tuple) else t])
        else:
            p.add_ptr(3, m_at + o, 1, C['base'] + C['off'][t])
    old = struct.pack('<I', C['base'] + C['m_at'])
    co = C['lab']['ct_open']
    oc = bytes(p.get(1, co, 0x60))
    k = [i for i in range(len(oc) - 9) if oc[i:i + 2] == b'\xc7\x05' and oc[i + 6:i + 10] == old]
    assert len(k) == 1, ('ct_open: mov dword [A6], CTMENU', k)
    p.retarget(1, co + k[0] + 6, 3, m_at)
    p.put(1, co + k[0] + 6, struct.pack('<I', m_at))
    dr = C['lab']['ct_draw']
    dc = bytes(p.get(1, dr, 0x80))
    k = [i for i in range(len(dc) - 5) if dc[i:i + 5] == b'\x41\x83\xf9\x05\x72']   # (.cap's inc ecx / cmp ecx, 5 / jb)
    assert len(k) == 1, ('ct_draw: the duplicate check', k)
    p.put(1, dr + k[0] + 3, b'\x0a')
    LABELS.update(lab)
    print(f'exe: CONTROLS B (player 2 key set, {FILE.decode()}): code obj3+{at:#x} ({len(code)} B), sites '
          f'set {s["set"]:#x} p2 {s["p2"]:#x} resets {[hex(x) for x in s["rst"]]} load {s["load"]:#x}, page obj3+{m_at:#x}')
    return m_at + len(pg)


LABELS = {}
