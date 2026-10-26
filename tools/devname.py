"""DOS device names refused as save names (4.0.2).

The save dialog (SelectFileToSaveDialog: careers, seasons, DIY and preset competitions, highlights) takes the typed name
(InputText, letters / digits / '#' / '-'), AddExtension appends '.CAR' etc. and the save writes g_selectedFilename. A name
that DOS takes as a device (CON, PRN, AUX, NUL, COM1..4, LPT1..3 ..., an extension does not change it: CON.CAR is CON) made
the save "succeed" into the device: nothing on disk, the career lost. AddExtension (166 bytes, the extension copied a byte
at a time) is rewritten in place, shorter, with the check: g_selectedFilename is opened read-only (3D00h) and asked
whether it is a device (IOCTL 4400h, DX bit 7); a device -> the game's error box (ShowErrorMenu's continueMenu, big font)
with the message in the exe's language and back to the dialog (the exit flag not set). Whatever DOS calls a device is
caught, on DOSBox, DOSBox-X and a real PC alike (also drivers' devices as EMMXXXX0); a missing file or a real one (the
overwrite of an old save) go on as before.
"""
import re
import struct

import nasmcave

MSG = {'it': 'NOME FILE NON VALIDO', 'en': 'INVALID FILENAME', 'fr': 'NOM DE FICHIER INVALIDE',
       'de': 'DATEINAME NICHT ERLAUBT'}

# AddExtension: mov [A1], g_selectedFilename; call StringCopy; mov [A0], g_extension; add [A0], 3; 4 x (byte [A0] ->
# [A1], A0--, A1++); mov esi, [A1]; mov byte [esi], 0; jmp SetExitMenuFlag
PAT = (rb'\xc7\x05(....)(....)\xe8(....)\xc7\x05(....)(....)\x83\x05\4\x03'
       rb'(?:\x8b\x35\4\x8a\x06\xff\x0d\4\x8b\x35\1\x88\x06\xff\x05\1){4}\x8b\x35\1\xc6\x06\x00\xe9(....)')

ASM = r"""
add_ext:                                ; AddExtension (A0 -> the typed name)
    mov dword [A1], SELNAME
    call STRCOPY                        ; (A1 -> its NUL)
    mov esi, [A1]
    mov eax, [EXT]                      ; '.CAR' as a dword: the '.' in the top byte
    xchg al, ah
    rol eax, 16
    xchg al, ah
    mov [esi], eax
    mov byte [esi + 4], 0
    mov edx, SELNAME
    mov eax, 3D00h                      ; open, read only
    int 21h
    jc .ok                              ; no such file: a new save
    mov ebx, eax
    mov eax, 4400h                      ; IOCTL get device information: DX bit 7 = a device
    int 21h
    push edx
    mov eax, 3E00h                      ; close
    int 21h
    pop edx
    test dl, 80h
    jz .ok
    mov dword [ERRTEXT], DEV_MSG        ; ShowErrorMenu's body (A0 not touched: the dialog's entry string)
    mov dword [A6R], CONTMENU
    jmp SHOWMENU                        ; (its ret: back to the dialog)
.ok:
    jmp SETEXIT
"""


def patch(p, lang):
    """Rewrites AddExtension in place (no cave)."""
    import instcheck
    d1 = p.le.obj_bytes(1)
    ms = list(re.finditer(PAT, d1, re.S))
    assert len(ms) == 1, len(ms)
    m = ms[0]
    at, end = m.start(), m.end()
    assert p.get(1, at, end - at) == d1[at:end], 'AddExtension already patched'
    rel = lambda g: m.end(g) + struct.unpack('<i', m.group(g))[0]
    sym = {'A1': p.target(1, m.start(1)), 'SELNAME': p.target(1, m.start(2)), 'STRCOPY': (1, rel(3)),
           'A0': p.target(1, m.start(4)), 'EXT': p.target(1, m.start(5)), 'SETEXIT': (1, rel(6))}
    sym.update({k: v for k, v in instcheck.sites(p).items() if k in ('ERRTEXT', 'CONTMENU', 'SHOWMENU', 'A6R')})
    src = ASM + 'DEV_MSG: db ' + ', '.join(map(str, MSG[lang].encode('latin1') + b'\0')) + '\n'
    code, fix = nasmcave.assemble(src, at, sym)
    assert len(code) <= end - at, len(code)
    for so, s, *_ in p.le.fixups():
        if so == 1 and at <= s < end:
            p.remove(1, s)
    p.put(1, at, code + b'\xcc' * (end - at - len(code)))
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    print(f'exe: DOS device names refused as save names (AddExtension obj1+{at:#x}, {len(code)} of {end - at} B)')
