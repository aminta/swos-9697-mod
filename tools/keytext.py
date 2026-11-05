"""Typed names with punctuation (4.0.6, Marco 04/11: his tactic "FWRD 3-2" came out as FWRD32).

Every name the game takes from the keyboard (InputText: saved tactics, the players / teams / coach of MODIFICA
SQUADRE, the save dialog) gets its characters from GetKey's convertKeysTable (obj2, one per exe: scan code -> ASCII)
and FilterKeys (letters, digits, then controlChars: # space - / . and the control codes; with g_allowExtraCharsFlag,
the save dialog's file name, not . / space). The table gives 0 for the - . / ' , keys and has no shift layer (both
SHIFTs are the text cursor's left / right, 21 / 22): only + (the = key), # and space could be typed besides letters
and digits.

Here (off under SWOS++: its own keyboard; the game's table there):
- kt_irq (kbd2's kb_set, the end of SetKeyboardControlFlags: every key make / break, the feeder's too): SHIFT held
  (left / right, not the E0-prefixed fake shifts) and the last E0-prefixed key (numpad /, the arrows);
- kt_conv (GetKey's `add ebx, offset convertKeysTable / mov al, [ebx]`): the exe language's keyboard - IT / UK /
  AZERTY / QWERTZ, the character printed on the key - unshifted and with SHIFT, plus the numpad's - + and /; only
  characters both menu fonts draw (complist.FONT: no ! & # @ ...), never an existing key changed (letters, digits,
  + on the = key, # on the ` key stay the game's); SHIFT no longer moves the cursor: the LEFT / RIGHT arrows do
  (21 / 22, they gave nothing). French: the game types the digits without SHIFT, so the AZERTY digit row's own
  symbols ' ( - come with SHIFT there;
- kt_filt (FilterKeys' `mov A1, offset controlChars`): its list + the new characters; the save dialog (flag set:
  file names - saves, tactics, whose name IS the .TAC file's) its list + ' ( ) _ (DOS-legal, drawn), so a tactic
  can be FWRD_3-2 (shown FWRD 3-2) but no . / space (the game refuses them there).
Names are bytes as before (TACTICS.DAT, team files, saves): no format change, old files read as they were.
"""
import re
import struct

import nasmcave

NEW = "-./'?+():,_"                        # (complist.FONT minus what the game already took; '_': no glyph, the game
SAVE = "'()_"                              # draws it as a space everywhere - DrawMenuText / Text2Sprite /
                                           # PrintStringInColor - as in ROBERTO_CARLOS: FWRD_3-2 shows FWRD 3-2)
# SAVE: what the save dialog (file names: saves, tactics) adds to the game's letters / digits / # / -: DOS-legal and
# drawn (Davide 04/11, (b); no '!': no glyph)
# per exe language: {scan: char} unshifted (only where the game's table has 0) and with SHIFT
LAYOUT = {
    'en': ({0x0C: '-', 0x34: '.', 0x35: '/', 0x28: "'", 0x33: ','},
           {0x0A: '(', 0x0B: ')', 0x27: ':', 0x35: '?', 0x0D: '+', 0x0C: '_'}),
    'it': ({0x35: '-', 0x34: '.', 0x33: ',', 0x0C: "'", 0x1B: '+'},
           {0x08: '/', 0x09: '(', 0x0A: ')', 0x0C: '?', 0x34: ':', 0x35: '_'}),
    'de': ({0x35: '-', 0x34: '.', 0x33: ',', 0x1B: '+'},
           {0x08: '/', 0x09: '(', 0x0A: ')', 0x0C: '?', 0x34: ':', 0x2B: "'", 0x35: '_'}),
    'fr': ({0x0C: ')', 0x32: ',', 0x34: ':'},
           {0x05: "'", 0x06: '(', 0x07: '-', 0x09: '_', 0x0D: '+', 0x32: '?', 0x33: '.', 0x34: '/'}),
}
NUMPAD = {0x4A: '-', 0x4E: '+'}            # (E0 35, numpad /: KT_E0)
N = 0x60                                   # table size (the game's 94 bytes, padded)

ASM = r"""
kt_irq:                                 ; kbd2's kb_set: SetKeyboardControlFlags' end (interrupt: ax / bx only)
    mov [KCF], bx
    push eax
    mov ax, [SCAN]
    cmp byte [PREV], 0E0h               ; (E0-prefixed: numpad /, the arrows; their fake shifts ignored)
    je .e0
    mov ah, 1
    cmp al, 2Ah
    je .dn
    cmp al, 0AAh
    je .up
    mov ah, 2
    cmp al, 36h
    je .dn
    cmp al, 0B6h
    je .up
    jmp .x
.dn: or [kt_sh], ah
    jmp .x
.up: not ah
    and [kt_sh], ah
    jmp .x
.e0: test al, 80h
    jnz .x
    mov [kt_e0], al
.x: pop eax
    ret

kt_conv:                                ; GetKey: ebx = scan code -> al = its character
    cmp byte [SWOSPP], 0FFh             ; (SWOS++: its own keyboard, the game's table)
    jne .game
    cmp ebx, N_
    jae .game
    cmp bl, [kt_e0]
    jne .n
    mov byte [kt_e0], 0
    mov al, [KT_E0 + ebx]
    test al, al
    jnz .r
.n: test byte [kt_sh], 3
    jz .u
    mov al, [KT_SH + ebx]
    test al, al
    jnz .r
.u: mov al, [KT_UN + ebx]
.r: ret
.game:
    add ebx, CKT
    mov al, [ebx]
    ret

kt_filt:                                ; FilterKeys: A1 = the allowed list (the save dialog: the game's)
    mov dword [A1], KT_CTRL
    cmp word [ALLOWX], 0
    je .r
    mov dword [A1], KT_SAVE
.r: ret

kt_sh: db 0
kt_e0: db 0
"""


def find(p):
    """The game's sites (obj1, the original exe): GetKey's table read, FilterKeys' list, Int9KeyboardHandler's
    g_prevScanCode; the table and the list themselves."""
    import controls
    d = p.le.obj_bytes(1)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    P = lambda x: re.escape(struct.pack('<I', x))
    sym = controls.locate(p)
    g = [m.start() + 7 for m in re.finditer(rb'\x66\x89\x1d....\x81\xc3....\x8a\x03\xa2', d, re.S)
         if fx.get(m.start() + 9, (0,))[0] == 2]
    assert len(g) == 1, ('GetKey convertKeysTable', g)
    f = [m.start() for m in re.finditer(rb'\xc7\x05........\x66\xa1....\x66\x0b\xc0\x74.\x80\x3d....\x2e\x74.'
                                        rb'\x80\x3d....\x2f\x74', d, re.S)]
    assert len(f) == 1, ('FilterKeys controlChars', f)
    sc = sym['SCAN'][1]
    pv = [m.start() + 10 for m in re.finditer(rb'\x66\x8b\x1d' + P(sc) + rb'\x66\x89\x1d....\x66\xa3' + P(sc), d, re.S)]
    assert len(pv) == 1, ('Int9KeyboardHandler g_prevScanCode', pv)
    s = {'get': g[0], 'filt': f[0]}
    v = {'CKT': fx[g[0] + 2], 'A1': fx[f[0] + 2], 'CTRL': fx[f[0] + 6], 'ALLOWX': fx[f[0] + 12], 'PREV': fx[pv[0]],
         'SCAN': sym['SCAN'], 'KCF': sym['KCF'], 'SWOSPP': sym['SWOSPP']}
    return s, v


def tables(p, lang, v):
    """(unshifted, shifted, E0) tables of N bytes for the exe language, and the allowed list."""
    import complist
    t = v['CKT']
    game = bytes(p.le.obj_bytes(t[0])[t[1]:t[1] + 94]) + bytes(N - 94)
    un, sh, e0 = bytearray(game), bytearray(N), bytearray(N)
    cur = [k for k, c in enumerate(game) if c in (21, 22)]  # (the cursor keys: the SHIFTs - the French exe's right
    assert game[0x2A] == 21 and len(cur) == 2 and game[0x0D] == ord('+'), ('convertKeysTable', cur)  # one on 35h)
    for k in cur:
        un[k] = 0                               # SHIFT: the shift layer, no cursor move
    lay = LAYOUT[lang]
    for k, c in {**lay[0], **NUMPAD}.items():
        assert un[k] == 0, (lang, hex(k), un[k])
        un[k] = ord(c)
    for k, c in lay[1].items():
        sh[k] = ord(c)
    un[0x4B], un[0x4D] = 21, 22                 # the arrows (numpad 4 / 6 too): the cursor
    e0[0x35], e0[0x1C], e0[0x4B], e0[0x4D] = ord('/'), 13, 21, 22
    typed = {chr(c) for c in un + sh if c >= 32}
    assert typed - complist.FONT - {'#', '_'} == set(), (lang, typed - complist.FONT)   # (# is the game's own)
    assert set(NEW) <= typed, (lang, set(NEW) - typed)
    c0 = v['CTRL']
    ctrl = bytes(p.le.obj_bytes(c0[0])[c0[1]:c0[1] + 11])
    assert ctrl == bytes([8, 13, 0x23, 0x15, 0x16, 0x20, 0x2D, 0x2F, 0x2E, 1, 0xFF]), ctrl
    extra = bytes(ord(c) for c in NEW if ord(c) not in ctrl)
    save = bytes(ord(c) for c in SAVE if ord(c) not in ctrl)
    return bytes(un), bytes(sh), bytes(e0), ctrl[:-1] + extra + b'\xff', ctrl[:-1] + save + b'\xff'


def patch(p, at, lang):
    """Code + tables at obj3:at, chained onto kbd2's kb_set (kbd2.patch ran first); returns the end."""
    import kbd2
    s, v = find(p)
    d = p.le.obj_bytes(1)
    assert p.get(1, s['get'], 8) == d[s['get']:s['get'] + 8], 'GetKey site already patched'
    assert p.get(1, s['filt'], 10) == d[s['filt']:s['filt'] + 10], 'FilterKeys site already patched'
    ks = kbd2.LABELS['kb_set']
    assert bytes(p.get(3, ks, 3)) == b'\x66\x89\x1d', 'kbd2 kb_set: not its mov [KCF], bx'
    un, sh, e0, ctrl, save = tables(p, lang, v)
    db = lambda b: ', '.join(str(x) for x in b)
    src = ASM + f'KT_UN: db {db(un)}\nKT_SH: db {db(sh)}\nKT_E0: db {db(e0)}\nKT_CTRL: db {db(ctrl)}\nKT_SAVE: db {db(save)}\n'
    sym = dict(v, N_=(0, N))
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['get'] + 2)                           # (the overwritten instructions' fixups)
    p.branch(1, s['get'], 0xE8, 3, lab['kt_conv'], 8)
    p.remove(1, s['filt'] + 2)
    p.remove(1, s['filt'] + 6)
    p.branch(1, s['filt'], 0xE8, 3, lab['kt_filt'], 10)
    p.remove(3, ks + 3)
    p.branch(3, ks, 0xE8, 3, lab['kt_irq'], 7)
    LABELS.update(lab)
    print(f'exe: typed names (keytext, {lang} keyboard, + {NEW}): code obj3+{at:#x} ({len(code)} B), sites GetKey '
          f'{s["get"]:#x} FilterKeys {s["filt"]:#x}, kb_set chained')
    return at + len(code)


LABELS = {}
