"""In-game CONTROLS page (4.0.2 / 4.0.3, Davide 2026-10-26): what INSTALL.EXE did, from the OPTIONS menu.

The game keeps its controls in SETUP.DAT (105 bytes, read once into setupDatBuffer by ReadSetupDat, never written):
  +6  g_inputControls: 1 keyboard only, 3 joypad P1 + keyboard P2, 4 keyboard P1 + joypad P2, 5 two joypads
      (2 joypad only, 6 mouse: not offered; Player1StatusProc reads stick 1 whenever it is not 1, Player2StatusProc
      stick 2 only with 5)
  +22 / +24 stick 1 raw x / y (ReadGamePort, every menu frame), +56 / +58 stick 2
  +30 centre x, +32 centre y, +38 min y, +40 min x, +42 max x, +44 max y, +46 x left divisor (centre - min x),
      +48 x right (max x - centre), +50 y top (centre - min y), +52 y bottom (max y - centre): stick 1; +64.. stick 2
      (Joy1NormalizeX: (distance << 16) / divisor >> 1, clipped beyond min / max: the divisors are the distances)
  +92 / +94 g_numLoopsJoy1 / 2 (ReadGamePort's count limit: the largest calibrated value; 2 for both sticks with 5)
  +96..+100 the keyboard's up / down / left / right / fire scan codes (SetKeyboardControlFlags, menus too)

The OPTIONS menu's entry 19 (PRE-RELEASE VERSION, invisible at y 208) becomes the CONTROLS button between EXIT TO DOS
(17) and EXIT (18), set by its init and on-return functions (hidden under SWOS++: menunum's byte). The page edits a copy
(WORK) of the game's buffer: the menus keep the old keys and device until SAVE, which re-reads SETUP.DAT (none: the
game's buffer), puts only the fields above into it and writes it back (DOS create: a missing file is created), applies
them to the game, then checks the sticks as VerifyJoypadControls (joyfix): no stick 1 = keyboard, with 5 and no stick 2
= 3, in memory only. CANCEL drops the copy.

A key row: fire -> PRESS A KEY; the next key typed (lastKey, one menu frame after the selecting key is released) is
taken, ESC keeps the old one, a key of another row is refused (KEY ALREADY USED). Menu input is held meanwhile with the
game's own switches (player1ClearFlag / player2ClearFlag, g_inputtingText = -1 for the latched-key branch), until the
new key is released. Calibration: the game's ReadGamePort is run with two sticks and the longest loops; centre + fire
(the stick's buttons, or the keyboard's fire / ENTER), every corner + fire, then a live TEST line until fire / ESC on
the keyboard. No stick (raw 0 or 65535): NO JOYPAD n CONNECTED.
"""
import re
import struct

import nasmcave

W = 140                       # the OPTIONS rows' boxes (labels x 10, values x 154 as defined; +8 at run time)
LINE_PX = 298                 # a message line (304 wide)
REC = 24                      # key name records (KEYTAB: 128 scan codes)

TEXTS = {
    'it': dict(title="COMANDI", dev="CONTROLLI",
               devs=("SOLO TASTIERA", "G1 JOYPAD, G2 TASTIERA", "G1 TASTIERA, G2 JOYPAD", "DUE JOYPAD"),
               keys=("SU", "GIU'", "SINISTRA", "DESTRA", "FUOCO"),
               press="PREMI UN TASTO (ESC: LASCIA)", dup="TASTO GIA' USATO",
               cal="CALIBRA JOYPAD {}", step1="LEVA AL CENTRO, PREMI FUOCO",
               step2="MUOVI LA LEVA IN TUTTI GLI ANGOLI, POI FUOCO", nopad="NESSUN JOYPAD {} COLLEGATO",
               test="PROVA:", save="SALVA", cancel="ANNULLA",
               hint="CON LA MODALITA' TASTIERA DEL PATCHER TIENI FRECCE E CTRL",
               arrows=("FRECCIA SU", "FRECCIA GIU'", "FRECCIA SINISTRA", "FRECCIA DESTRA"), ctrl="CTRL",
               shift=("SHIFT SX", "SHIFT DX"), space="SPAZIO", enter="INVIO", kp="TN", key="TASTO"),
    'en': dict(title="CONTROLS", dev="INPUT",
               devs=("KEYBOARD ONLY", "P1 JOYPAD, P2 KEYBOARD", "P1 KEYBOARD, P2 JOYPAD", "TWO JOYPADS"),
               keys=("UP", "DOWN", "LEFT", "RIGHT", "FIRE"),
               press="PRESS A KEY (ESC: KEEP)", dup="KEY ALREADY USED",
               cal="CALIBRATE JOYPAD {}", step1="STICK CENTRED, PRESS FIRE",
               step2="MOVE THE STICK TO EVERY CORNER, THEN FIRE", nopad="NO JOYPAD {} CONNECTED",
               test="TEST:", save="SAVE", cancel="CANCEL",
               hint="WITH THE PATCHER'S KEYBOARD MODE KEEP ARROWS AND CTRL",
               arrows=("UP ARROW", "DOWN ARROW", "LEFT ARROW", "RIGHT ARROW"), ctrl="CTRL",
               shift=("L. SHIFT", "R. SHIFT"), space="SPACE", enter="ENTER", kp="KP", key="KEY"),
    'fr': dict(title="COMMANDES", dev="PERIPHERIQUES",
               devs=("CLAVIER SEUL", "J1 MANETTE, J2 CLAVIER", "J1 CLAVIER, J2 MANETTE", "DEUX MANETTES"),
               keys=("HAUT", "BAS", "GAUCHE", "DROITE", "TIR"),
               press="APPUYEZ SUR UNE TOUCHE (ESC: GARDER)", dup="TOUCHE DEJA UTILISEE",
               cal="CALIBRER MANETTE {}", step1="MANCHE AU CENTRE, APPUYEZ SUR TIR",
               step2="BOUGEZ LE MANCHE DANS CHAQUE COIN, PUIS TIR", nopad="AUCUNE MANETTE {} BRANCHEE",
               test="TEST :", save="ENREGISTRER", cancel="ANNULER",
               hint="AVEC LE MODE CLAVIER DU PATCHER GARDEZ FLECHES ET CTRL",
               arrows=("FLECHE HAUT", "FLECHE BAS", "FLECHE GAUCHE", "FLECHE DROITE"), ctrl="CTRL",
               shift=("MAJ G", "MAJ D"), space="ESPACE", enter="ENTREE", kp="PN", key="TOUCHE"),
    'de': dict(title="STEUERUNG", dev="GERAETE",
               devs=("NUR TASTATUR", "S1 JOYPAD, S2 TASTATUR", "S1 TASTATUR, S2 JOYPAD", "ZWEI JOYPADS"),
               keys=("OBEN", "UNTEN", "LINKS", "RECHTS", "FEUER"),
               press="TASTE DRUECKEN (ESC: BEHALTEN)", dup="TASTE SCHON BELEGT",
               cal="JOYPAD {} KALIBRIEREN", step1="STICK IN DIE MITTE, FEUER DRUECKEN",
               step2="STICK IN ALLE ECKEN, DANN FEUER", nopad="KEIN JOYPAD {} ANGESCHLOSSEN",
               test="TEST:", save="SPEICHERN", cancel="ABBRECHEN",
               hint="IM TASTATURMODUS DES PATCHERS PFEILE UND STRG LASSEN",
               arrows=("PFEIL OBEN", "PFEIL UNTEN", "PFEIL LINKS", "PFEIL RECHTS"), ctrl="STRG",
               shift=("UMSCH. L", "UMSCH. R"), space="LEERTASTE", enter="EINGABE", kp="ZB", key="TASTE"),
}
# the letters by the exe language's usual keyboard (scan codes are key positions): QWERTY, AZERTY, QWERTZ
ROWS = {'it': ('QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'), 'en': ('QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'),
        'fr': ('AZERTYUIOP', 'QSDFGHJKLM', 'WXCVBN'), 'de': ('QWERTZUIOP', 'ASDFGHJKL', 'YXCVBNM')}

# the small font (complist.SMALL_W); German as AE / OE / UE (Davide 26/10: the small font draws the exe's umlaut bytes
# without dots, DRUCKEN would read 'print')
SMALL_W = dict({c: 6 for c in 'ABCDEFGHJKLMNOPQRSTUVWXYZ023456789!"#$%&*+/<=>?@'},
               **{'I': 2, '1': 2, "'": 2, '(': 3, ')': 3, ',': 2, '-': 4, '.': 2, ':': 2, ' ': 3})


def px(s):
    assert all(c in SMALL_W for c in s), ('character outside the font', s)
    return sum(SMALL_W[c] for c in s)


def lines(s):
    """A message as one or two lines of LINE_PX (cut at a space)."""
    if px(s) <= LINE_PX:
        return s, ''
    words = s.split(' ')
    for k in range(len(words) - 1, 0, -1):
        a, b = ' '.join(words[:k]), ' '.join(words[k:])
        if px(a) <= LINE_PX:
            assert px(b) <= LINE_PX, s
            return a, b
    raise AssertionError(s)


def key_names(lang):
    T = TEXTS[lang]
    n = {}
    for sc, ch in enumerate('1234567890', 0x02):
        n[sc] = ch
    for row, base in zip(ROWS[lang], (0x10, 0x1E, 0x2C)):
        for sc, ch in enumerate(row, base):
            n[sc] = ch
    n.update({0x0F: 'TAB', 0x1C: T['enter'], 0x1D: T['ctrl'], 0x2A: T['shift'][0], 0x36: T['shift'][1], 0x38: 'ALT',
              0x39: T['space'], 0x48: T['arrows'][0], 0x50: T['arrows'][1], 0x4B: T['arrows'][2],
              0x4D: T['arrows'][3]})
    for sc, d in ((0x47, 7), (0x49, 9), (0x4C, 5), (0x4F, 1), (0x51, 3), (0x52, 0)):   # (the others: the arrows'
        n[sc] = f"{T['kp']} {d}"                                                         # scan codes)
    out = []
    for sc in range(128):
        s = n.get(sc, f"{T['key']} {sc}")
        assert len(s) < REC and px(s) <= W - 2, s
        out.append(s)
    return out


ASM = r"""
ct_optinit:                             ; OPTIONS' init: the game's, then the CONTROLS button
    call OMBD
ct_optret:                              ; (and on return to OPTIONS: unpacked again from its packed form)
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no button (it has its own options)
    jne .x
    mov esi, MENU_ + 16h + 17 * 38h     ; entry 19 = EXIT TO DOS's box, colour, text type and flags...
    mov edi, MENU_ + 16h + 19 * 38h
    push esi
    add esi, 14h
    add edi, 14h
    mov ecx, 38h - 14h
    rep movsb
    pop esi
    mov edi, MENU_ + 16h + 19 * 38h
    mov word [edi + 4], 0
    mov word [edi + 16h], BTN_Y
    mov dword [edi + 26h], S_TITLE
    mov dword [edi + 2Ah], ct_open
    mov dword [edi + 8], 1211FFFFh      ; up EXIT TO DOS (17), down EXIT (18)
    mov dword [edi + 10h], 1211FFFFh
    mov byte [esi + 0Bh], 19
    mov byte [esi + 13h], 19
    mov byte [MENU_ + 16h + 18 * 38h + 0Ah], 19
    mov byte [MENU_ + 16h + 18 * 38h + 12h], 19
.x: popad
    ret

ct_open:                                ; CONTROLS (fire): the page on a copy of the game's settings
    pushad
    mov esi, BUF
    mov edi, WORK
    mov ecx, 105
    rep movsb
    mov ax, [WORK + 6]
    cmp ax, 2                           ; joypad only (an old INSTALL choice): as joypad + keyboard
    jne .n2
    mov ax, 3
.n2:
    cmp ax, 1
    je .ok
    cmp ax, 3
    jb .kb
    cmp ax, 5
    jbe .ok
.kb:
    mov ax, 1                           ; the mouse (6) or garbage: keyboard
.ok:
    mov [WORK + 6], ax
    mov byte [MODE], 0
    popad
    mov dword [A6], CTMENU
    jmp SHOW_MENU

ct_init:                                ; the page's init
    mov byte [MODE], 0
    mov byte [DUP], 0
    jmp ct_refresh

ct_draw:                                ; the page's onDraw (every frame, before the entries are drawn)
    pushad
    movzx eax, byte [MODE]
    cmp al, 1
    je .cap
    cmp al, 2
    je .centre
    cmp al, 3
    je .corners
    cmp al, 4
    je .test
    cmp al, 5
    je .nopad
    cmp al, 6
    je .release
    jmp .done

.cap:                                   ; a key row waits for its key
    call ct_kev
    test eax, eax
    jz .done
    cmp al, 1                           ; ESC: the old key stays
    je .leave
    movzx ebx, byte [KIDX]
    xor ecx, ecx
.dl:
    cmp ecx, ebx
    je .dn
    cmp [WORK + 96 + ecx], al
    je .dup
.dn:
    inc ecx
    cmp ecx, 5
    jb .dl
    mov [WORK + 96 + ebx], al
.leave:
    mov byte [MODE], 6
    jmp .done
.dup:
    mov byte [DUP], 1
    jmp .done

.release:                               ; the menus read the keys again once the last one is released
    mov ax, [SCAN]
    test ax, 80h
    jnz .unblock
    test ax, ax
    jnz .done
.unblock:
    call ct_unblock
    jmp .done

.centre:                                ; calibration 1: stick centred + fire
    call ct_kev
    mov [KEY], al
    cmp al, 1
    je .calend
    cmp byte [WAIT], 0                  ; (ReadGamePort's first readings with the long loops)
    je .c0
    dec byte [WAIT]
    jmp .done
.c0:
    call ct_raw
    cmp cx, -1                          ; all ones (no port / no stick) or all zeros (DOSBox-X auto without one)
    je .none
    test cx, cx
    je .none
    call ct_fire
    test al, al
    jz .done
    mov [CX_], cx
    mov [CY_], dx
    mov [MINX], cx
    mov [MAXX], cx
    mov [MINY], dx
    mov [MAXY], dx
    mov byte [MODE], 3
    jmp .done
.none:
    mov byte [MODE], 5
    jmp .done

.corners:                               ; calibration 2: every corner + fire
    call ct_kev
    mov [KEY], al
    cmp al, 1
    je .calend
    call ct_raw
    cmp cx, [MINX]
    jae .x1
    mov [MINX], cx
.x1:
    cmp cx, [MAXX]
    jbe .x2
    mov [MAXX], cx
.x2:
    cmp dx, [MINY]
    jae .y1
    mov [MINY], dx
.y1:
    cmp dx, [MAXY]
    jbe .y2
    mov [MAXY], dx
.y2:
    call ct_fire
    test al, al
    jz .done
    mov ax, [CX_]                       ; at least 8 counts each way, else from the centre again
    sub ax, [MINX]
    cmp ax, 8
    jb .again
    mov ax, [MAXX]
    sub ax, [CX_]
    cmp ax, 8
    jb .again
    mov ax, [CY_]
    sub ax, [MINY]
    cmp ax, 8
    jb .again
    mov ax, [MAXY]
    sub ax, [CY_]
    cmp ax, 8
    jb .again
    call ct_store
    mov byte [MODE], 4
    jmp .done
.again:
    mov byte [MODE], 2
    jmp .done

.test:                                  ; the live TEST line until fire / ESC on the keyboard
    call ct_kev
    mov [KEY], al
    cmp al, 1
    je .calend
    call ct_kfire
    jnz .calend
    call ct_testline
    jmp .done

.nopad:
    call ct_kev
    mov [KEY], al
    cmp al, 1
    je .calend
    call ct_kfire
    jz .done
.calend:                                ; the game's controls and loops back as they were
    mov ax, [SV_CTL]
    mov [BUF + 6], ax
    mov eax, [SV_NL]
    mov [BUF + 92], eax
    mov byte [MODE], 6
.done:
    call ct_refresh
    popad
    ret

ct_kev:                                 ; eax = the key typed since the last frame (0: none); keys count once the
    cmp byte [ARMED], 0                 ; key that selected the row is released
    jne .r
    mov ax, [SCAN]
    test ax, 80h
    jnz .arm
    test ax, ax
    jnz .no
.arm:
    mov byte [ARMED], 1
.no:
    xor eax, eax
    ret
.r:
    movzx eax, byte [LASTKEY]
    ret

ct_kfire:                               ; ZF clear: KEY is the keyboard's fire (the game's) or ENTER
    mov al, [KEY]
    test al, al
    jz .no
    cmp al, [BUF + 100]
    je .yes
    cmp al, 1Ch
    je .yes
.no:
    cmp al, al
    ret
.yes:
    or al, 1
    ret

ct_fire:                                ; al = 1: fire (a button of the stick pressed now, or the keyboard's)
    call ct_kfire
    jnz .yes
    call ct_btn
    mov ah, [FPREV]
    mov [FPREV], al
    test al, al
    jz .no
    test ah, ah
    jnz .no
.yes:
    mov al, 1
    ret
.no:
    xor eax, eax
    ret

ct_btn:                                 ; al = 1: a button of the stick being calibrated is down (port 201h, low = down)
    push edx
    mov dx, 201h
    in al, dx
    pop edx
    not al
    cmp byte [PAD], 0
    jne .p2
    test al, 30h
    jmp .t
.p2:
    test al, 0C0h
.t:
    setnz al
    ret

ct_raw:                                 ; ecx / edx = the stick's raw x / y (ReadGamePort's)
    cmp byte [PAD], 0
    jne .p2
    movzx ecx, word [BUF + 22]
    movzx edx, word [BUF + 24]
    ret
.p2:
    movzx ecx, word [BUF + 56]
    movzx edx, word [BUF + 58]
    ret

ct_store:                               ; the measured stick into WORK (+30 stick 1, +64 stick 2) and its loops
    pushad
    mov edi, WORK + 30
    cmp byte [PAD], 0
    je .p
    mov edi, WORK + 64
.p:
    mov ax, [CX_]
    mov [edi], ax
    mov ax, [CY_]
    mov [edi + 2], ax
    mov ax, [MINY]
    mov [edi + 8], ax
    mov ax, [MINX]
    mov [edi + 10], ax
    mov ax, [MAXX]
    mov [edi + 12], ax
    mov ax, [MAXY]
    mov [edi + 14], ax
    mov ax, [CX_]
    sub ax, [MINX]
    mov [edi + 16], ax
    mov ax, [MAXX]
    sub ax, [CX_]
    mov [edi + 18], ax
    mov ax, [CY_]
    sub ax, [MINY]
    mov [edi + 20], ax
    mov ax, [MAXY]
    sub ax, [CY_]
    mov [edi + 22], ax
    movzx eax, word [MAXX]              ; loops: the largest value + 1/8
    movzx edx, word [MAXY]
    cmp eax, edx
    jae .m
    mov eax, edx
.m:
    mov edx, eax
    shr edx, 3
    add eax, edx
    cmp eax, 0FFFFh
    jbe .m2
    mov eax, 0FFFFh
.m2:
    cmp byte [PAD], 0
    jne .l2
    mov [WORK + 92], ax                 ; stick 1; stick 2's loops (two sticks: ReadGamePort's only count) at
    cmp ax, [WORK + 94]                 ; least as many
    jbe .x
    mov [WORK + 94], ax
    jmp .x
.l2:
    cmp ax, [WORK + 92]
    jae .l3
    mov ax, [WORK + 92]
.l3:
    mov [WORK + 94], ax
.x:
    popad
    ret

ct_testline:                            ; TEST: + the directions held + FIRE, from the new calibration
    pushad
    mov edi, PB
    mov esi, S_TEST
    call .cpy
    call ct_raw
    mov ax, [CX_]                       ; left: below the centre by half its range
    sub ax, [MINX]
    shr ax, 1
    mov bx, [CX_]
    sub bx, ax
    cmp cx, bx
    jae .nl
    mov esi, S_K2
    call .word
.nl:
    mov ax, [MAXX]
    sub ax, [CX_]
    shr ax, 1
    add ax, [CX_]
    cmp cx, ax
    jbe .nr
    mov esi, S_K3
    call .word
.nr:
    mov ax, [CY_]
    sub ax, [MINY]
    shr ax, 1
    mov bx, [CY_]
    sub bx, ax
    cmp dx, bx
    jae .nu
    mov esi, S_K0
    call .word
.nu:
    mov ax, [MAXY]
    sub ax, [CY_]
    shr ax, 1
    add ax, [CY_]
    cmp dx, ax
    jbe .nd
    mov esi, S_K1
    call .word
.nd:
    call ct_btn
    test al, al
    jz .nf
    mov esi, S_K4
    call .word
.nf:
    mov byte [edi], 0
    popad
    ret
.word:
    mov byte [edi], ' '
    inc edi
.cpy:
    lodsb
    test al, al
    jz .e
    stosb
    jmp .cpy
.e:
    ret

ct_block:                               ; menu input held: the game's own switches (text input: no latched keys)
    mov ax, [P1CLR]
    mov [SV_P1], ax
    mov ax, [P2CLR]
    mov [SV_P2], ax
    mov ax, [INTEXT]
    mov [SV_IT], ax
    mov word [P1CLR], 1
    mov word [P2CLR], 1
    mov word [INTEXT], -1
    mov word [LASTKEY], 0               ; (the selecting key)
    mov byte [ARMED], 0
    mov byte [DUP], 0
    ret

ct_unblock:
    mov ax, [SV_P1]
    mov [P1CLR], ax
    mov ax, [SV_P2]
    mov [P2CLR], ax
    mov ax, [SV_IT]
    mov [INTEXT], ax
    mov word [KCF], 0                   ; (held under the old keys)
    mov byte [MODE], 0
    mov byte [DUP], 0
    ret

ct_dev:                                 ; the device row (fire): 1 -> 3 -> 4 -> 5 -> 1
    cmp byte [MODE], 0
    jne .x
    mov ax, [WORK + 6]
    inc ax
    cmp ax, 2
    jne .n
    inc ax
.n:
    cmp ax, 5
    jbe .s
    mov ax, 1
.s:
    mov [WORK + 6], ax
    call ct_refresh
.x:
    ret

ct_k0:
    mov byte [KIDX], 0
    jmp ct_key
ct_k1:
    mov byte [KIDX], 1
    jmp ct_key
ct_k2:
    mov byte [KIDX], 2
    jmp ct_key
ct_k3:
    mov byte [KIDX], 3
    jmp ct_key
ct_k4:
    mov byte [KIDX], 4
ct_key:                                 ; a key row (fire): wait for its key
    cmp byte [MODE], 0
    jne .x
    pushad
    call ct_block
    mov byte [MODE], 1
    call ct_refresh
    popad
.x:
    ret

ct_cal1:
    mov byte [PAD], 0
    jmp ct_cal
ct_cal2:
    mov byte [PAD], 1
ct_cal:                                 ; CALIBRATE JOYPAD n (fire): ReadGamePort reads both sticks to the end
    cmp byte [MODE], 0
    jne .x
    pushad
    call ct_block
    mov ax, [BUF + 6]
    mov [SV_CTL], ax
    mov eax, [BUF + 92]
    mov [SV_NL], eax
    mov word [BUF + 6], 5
    mov dword [BUF + 92], -1
    mov byte [WAIT], 2
    mov byte [FPREV], 1                 ; (a button held: its release first)
    mov byte [MODE], 2
    call ct_refresh
    popad
.x:
    ret

ct_cancel:                              ; CANCEL: the copy dropped
    cmp byte [MODE], 0
    jne .x
    mov word [EXITM], 1
.x:
    ret

ct_save:                                ; SAVE: SETUP.DAT (as it is on disk, our fields replaced) and the game
    cmp byte [MODE], 0
    jne .x
    pushad
    mov esi, BUF                        ; (no file: the game's buffer)
    mov edi, FBUF
    mov ecx, 105
    rep movsb
    mov edx, FNAME
    mov eax, 3D00h
    int 21h
    jc .nofile
    mov ebx, eax
    mov edx, FBUF
    mov ecx, 105
    mov ah, 3Fh
    int 21h
    mov ah, 3Eh
    int 21h
.nofile:
    mov edi, FBUF
    call ct_apply
    mov edi, BUF
    call ct_apply
    mov edx, FNAME
    xor ecx, ecx
    mov ah, 3Ch                         ; create / truncate
    int 21h
    jc .nowrite
    mov ebx, eax
    mov edx, FBUF
    mov ecx, 105
    mov ah, 40h
    int 21h
    mov ah, 3Eh
    int 21h
.nowrite:
    cmp word [BUF + 6], 1               ; the sticks, as VerifyJoypadControls at the start (memory only)
    je .ok
    push dword [BUF + 92]
    mov dword [BUF + 92], -1
    call RGP
    pop dword [BUF + 92]
    mov ax, [BUF + 22]
    inc ax
    cmp ax, 1
    jbe .kb
    cmp word [BUF + 6], 5
    jne .ok
    mov ax, [BUF + 56]
    inc ax
    cmp ax, 1
    ja .ok
    mov word [BUF + 6], 3
    jmp .ok
.kb:
    mov word [BUF + 6], 1
.ok:
    mov word [KCF], 0
    mov word [EXITM], 1
    popad
.x:
    ret

ct_apply:                               ; WORK's fields -> [edi]: device, the two sticks' calibration, loops, keys
    mov esi, FIELDS
.f:
    movzx ecx, byte [esi + 1]
    jecxz .e
    movzx eax, byte [esi]
    push esi
    push edi
    lea esi, [WORK + eax]
    add edi, eax
    rep movsb
    pop edi
    pop esi
    add esi, 2
    jmp .f
.e:
    ret

ct_refresh:                             ; texts, rows shown and links from WORK and the mode
    pushad
    mov esi, MENU_ + 16h
    movzx eax, word [WORK + 6]          ; the device: 1, 3, 4, 5 -> 0..3
    sub eax, 2
    jae .d
    xor eax, eax
.d:
    mov eax, [DEVPTR + eax * 4]
    mov [esi + 2 * 38h + 26h], eax
    xor ecx, ecx
.k:
    movzx eax, byte [WORK + 96 + ecx]
    and eax, 7Fh
    imul eax, REC_
    add eax, KEYTAB
    imul edx, ecx, 38h
    mov [esi + 8 * 38h + 26h + edx], eax
    inc ecx
    cmp ecx, 5
    jb .k
    xor eax, eax                        ; CALIBRATE 1: a joypad in use; 2: two
    cmp word [WORK + 6], 1
    sete al
    mov [esi + 13 * 38h + 4], ax
    xor eax, eax
    cmp word [WORK + 6], 5
    setne al
    mov [esi + 14 * 38h + 4], ax
    mov byte [esi + 12 * 38h + 0Bh], 13
    mov byte [esi + 17 * 38h + 0Ah], 13
    mov byte [esi + 18 * 38h + 0Ah], 14
    mov byte [esi + 13 * 38h + 9], 14
    cmp word [WORK + 6], 5
    je .links
    mov byte [esi + 18 * 38h + 0Ah], 13
    mov byte [esi + 13 * 38h + 9], 0FFh
    cmp word [WORK + 6], 1
    jne .links
    mov byte [esi + 12 * 38h + 0Bh], 17
    mov byte [esi + 17 * 38h + 0Ah], 12
    mov byte [esi + 18 * 38h + 0Ah], 12
.links:
    movzx eax, byte [MODE]              ; the message lines
    cmp al, 6
    jb .m
    xor eax, eax
.m:
    cmp al, 5
    jne .m5
    add al, [PAD]
.m5:
    mov edx, [MSGTAB + eax * 8]
    mov [esi + 15 * 38h + 26h], edx
    mov edx, [MSGTAB + eax * 8 + 4]
    cmp byte [DUP], 0
    je .m2
    mov edx, S_DUP
.m2:
    mov [esi + 16 * 38h + 26h], edx
    popad
    ret
"""

FIELDS = ((6, 2), (30, 4), (38, 16), (64, 4), (72, 16), (92, 9))   # WORK -> SETUP.DAT / the game (ct_apply)


def locate(p):
    """The game's symbols (obj, offset) on the original exe."""
    import fmtpage
    import joyfix
    import zones
    d1 = p.le.obj_bytes(1)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    one = lambda pat: (lambda m: m[0].start() if len(m) == 1 else (_ for _ in ()).throw(AssertionError((pat, len(m)))))(
        list(re.finditer(pat, d1, re.S)))
    rs = one(joyfix.RSD_PAT)                                     # ReadSetupDat: "SETUP.DAT", setupDatBuffer
    sym = {'FNAME': fx[rs + 1], 'BUF': fx[rs + 17]}
    vj = one(joyfix.VJC_PAT)
    assert fx[vj + 13] == (sym['BUF'][0], sym['BUF'][1] + 92), 'g_numLoopsJoy1 = setupDatBuffer + 92'
    assert fx[vj + 3] == (sym['BUF'][0], sym['BUF'][1] + 6), 'g_inputControls = setupDatBuffer + 6'
    sym['RGP'] = (1, vj + 0x66)                                  # ReadGamePort
    s = one(rb'\x66\xa1....\x66\x8b\x1d....\x66\xa9\x80\x00\x75.\x3a\x05')   # SetKeyboardControlFlags
    sym['SCAN'], sym['KCF'] = fx[s + 2], fx[s + 9]
    assert fx[s + 0x4f + 2] == (2, sym['BUF'][1] + 96) and fx[s + 0x13 + 2] == (2, sym['BUF'][1] + 100), 'scan codes'
    g = one(rb'\x0f\xb6\x1d....\x66\x89\x1d....\x81\xc3')        # GetKey: mov lastKey, bx
    sym['LASTKEY'] = fx[g + 10]
    lk = re.escape(struct.pack('<I', sym['LASTKEY'][1]))
    mc = [m.start() for m in re.finditer(rb'\xe8....\x66\xa1' + lk, d1, re.S)]
    mc = [x for x in mc if fx.get(x + 7) == sym['LASTKEY']]
    m5 = one(rb'\x66\x83\x3d....\x05\x0f\x85....\x66\x83\x3d....\xff\x0f\x84')   # (its two joypads branch)
    mc = max(x for x in mc if x < m5)                            # MenuCheckControls: call GetKey / mov ax, lastKey
    assert m5 - mc < 0x500, hex(m5 - mc)
    c1 = [m for m in re.finditer(rb'\x66\xa1(....)\x66\x0b\xc0(?:\x74|\x0f\x84)', d1[mc:mc + 0x80], re.S)]
    sym['P1CLR'] = fx[mc + c1[0].start() + 2]
    c2 = re.search(rb'\xc6\x05....\x00\x66\xa1....\x66\x0b\xc0\x0f\x85', d1[mc:mc + 0x200], re.S)
    sym['P2CLR'] = fx[mc + c2.start() + 9]
    assert fx[m5 + 3] == (2, sym['BUF'][1] + 6)
    sym['INTEXT'] = fx[m5 + 17]
    _, _, _, show, a6 = fmtpage.locate(p)
    sym['SHOW_MENU'], sym['A6'] = (1, show), a6
    e = re.search(rb'\x66\xc7\x05....\x00\x00\xe8', d1[show:show + 0x80], re.S)   # mov g_exitMenu, 0 / call ActivateMenu
    sym['EXITM'] = fx[show + e.start() + 3]
    sym['MENU_'] = zones._current_menu(p)
    ob = one(rb'\x66\x83\x3d....\x01\x0f\x84....\xff\x35....\xc7\x05....\x0f\x00\x00\x00')   # OptionsMenuBeforeDraw
    sym['OMBD'] = (1, ob)
    import sacups                                                # (menunum's tactics-pitch site: SWOS++ hooks +0x23;
    a0 = sacups.regs(d1)['A0']                                   # menunum.sites reads fixups menunum removed)
    pk = lambda x: re.escape(struct.pack('<I', x))
    tac = one(rb'\x66\x81\x05' + pk(a0 - 32) + rb'\xa1\x00\x66\x83\x2d' + pk(a0 - 24) + rb'\x09'
              rb'(?:\xff\x35....){3}\xff\x35' + pk(a0 + 16))
    sym['SWOSPP'] = (1, tac + 0x23)
    return sym


def menu_header(p, ombd):
    """optionsMenu (obj2): the packed menu whose initFunc is OptionsMenuBeforeDraw."""
    hdr = [s for so, s, _, t, o, *_ in p.le.fixups() if so == 2 and t == 1 and o == ombd]
    assert len(hdr) == 1, hdr
    return hdr[0]


def layout(lang):
    """The page's obj2 block: (data, offsets, pointers [(offset, obj, name)], menu offset)."""
    T = TEXTS[lang]
    data = bytearray()
    off, ptrs = {}, []

    def put(key, b, size=None):
        off[key] = len(data)
        data.extend(b + b'\0' * ((size or len(b) + 1) - len(b)))

    enc = lambda s: s.encode('latin-1')
    put('title', enc(T['title']))
    put('dev', enc(T['dev']))
    for i, s in enumerate(T['devs']):
        put(f'dv{i}', enc(s))
    for i, s in enumerate(T['keys']):
        put(f'k{i}', enc(s))
    put('cal1', enc(T['cal'].format(1)))
    put('cal2', enc(T['cal'].format(2)))
    put('save', enc(T['save']))
    put('cancel', enc(T['cancel']))
    put('test', enc(T['test']))
    put('dup', enc(T['dup']))
    put('empty', b'')
    msgs = [lines(T['hint']), lines(T['press']), lines(T['step1']), lines(T['step2']), None,
            lines(T['nopad'].format(1)), lines(T['nopad'].format(2))]
    for i, m in enumerate(msgs):
        if m:
            put(f'm{i}a', enc(m[0]))
            put(f'm{i}b', enc(m[1]))
    assert px(T['test'] + ' ' + ' '.join(T['keys'][1:])) <= LINE_PX
    put('pb', b'', 64)
    put('work', b'', 108)
    put('fbuf', b'', 108)
    put('vars', b'', 48)
    put('fields', bytes(sum(FIELDS, ())) + b'\0\0')
    put('keytab', b''.join(enc(s).ljust(REC, b'\0') for s in key_names(lang)))
    while len(data) % 4:
        data.append(0)
    off['devptr'] = len(data)
    for i in range(4):
        ptrs.append((len(data), 2, f'dv{i}'))
        data.extend(b'\0' * 4)
    off['msgtab'] = len(data)
    for i, m in enumerate(msgs):
        ptrs.append((len(data), 2, f'm{i}a' if m else 'pb'))
        ptrs.append((len(data) + 4, 2, f'm{i}b' if m else 'empty'))
        data.extend(b'\0' * 8)

    def entry(buf, base_at, x, y, w, h, nav=None, color=None, text=None, flags=0, select=None):
        b = bytearray(struct.pack('<hhhh', x, y, w, h))
        if nav:
            b += struct.pack('<H', 2) + bytes(v & 0xFF for v in nav)
        if color is not None:
            b += struct.pack('<HH', 4, color)
        if text is not None:
            b += struct.pack('<HH', 8, flags)
            ptrs.append((base_at + len(buf) + len(b), 2, text))
            b += b'\0\0\0\0'
        if select is not None:
            b += struct.pack('<H', 13)
            ptrs.append((base_at + len(buf) + len(b), 1, select))
            b += b'\0\0\0\0'
        buf.extend(b + b'\0\0')

    m_at = len(data)                    # the page: 0 title, 1 / 2 device, 3..7 / 8..12 keys, 13 / 14 calibrate,
    pg = bytearray(struct.pack('<IIII', 0, 0, 0, 2))   # 15 / 16 messages, 17 SAVE, 18 CANCEL
    ptrs.append((m_at, 1, 'ct_init'))
    ptrs.append((m_at + 8, 1, 'ct_draw'))
    entry(pg, m_at, 92, 0, 120, 15, color=0x17, text='title')
    entry(pg, m_at, 10, 30, W, 11, color=LABEL_COL, text='dev')
    entry(pg, m_at, 154, 30, W, 11, nav=(-1, -1, -1, 8), color=VALUE_COL, text='dv0', select='ct_dev')
    for i in range(5):
        entry(pg, m_at, 10, 48 + 12 * i, W, 11, color=LABEL_COL, text=f'k{i}')
    for i in range(5):
        entry(pg, m_at, 154, 48 + 12 * i, W, 11, nav=(-1, -1, 2 if i == 0 else 7 + i, 9 + i if i < 4 else 13),
              color=VALUE_COL, text=f'k{i}', select=f'ct_k{i}')
    entry(pg, m_at, 10, 114, W, 13, nav=(-1, 14, 12, 17), color=0x0E, text='cal1', select='ct_cal1')
    entry(pg, m_at, 154, 114, W, 13, nav=(13, -1, 12, 18), color=0x0E, text='cal2', select='ct_cal2')
    entry(pg, m_at, 0, 136, 304, 10, text='m0a')
    entry(pg, m_at, 0, 147, 304, 10, text='m0b')
    entry(pg, m_at, 28, 180, 120, 15, nav=(-1, 18, 13, -1), color=0x0E, text='save', select='ct_save')
    entry(pg, m_at, 156, 180, 120, 15, nav=(17, -1, 14, -1), color=0x0C, text='cancel', select='ct_cancel')
    pg += struct.pack('<h', -999)
    data.extend(pg)
    return data, off, ptrs, m_at


def patch(p, at, lang, area):
    """The page's code at obj1:at (its own page), texts / tables / menu in obj2 area. Returns the code end."""
    sym = locate(p)
    T = TEXTS[lang]
    for s in (T['title'], T['save'], T['cancel']):
        assert px(s) <= 118, s
    for s in (T['dev'],) + T['devs'] + T['keys'] + (T['cal'].format(1), T['cal'].format(2)):
        assert px(s) <= W - 2, s
    data, off, ptrs, m_at = layout(lang)

    base = area.add(bytes(data))
    assert not any((base + o) // 0x1000 != (base + o + 3) // 0x1000 for o, _, _ in ptrs), 'a pointer straddles a page'
    v = base + off['vars']
    sym.update({'WORK': (2, base + off['work']), 'FBUF': (2, base + off['fbuf']), 'PB': (2, base + off['pb']),
                'KEYTAB': (2, base + off['keytab']), 'DEVPTR': (2, base + off['devptr']),
                'MSGTAB': (2, base + off['msgtab']), 'FIELDS': (2, base + off['fields']), 'CTMENU': (2, base + m_at),
                'S_TITLE': (2, base + off['title']), 'S_TEST': (2, base + off['test']), 'S_DUP': (2, base + off['dup']),
                'REC_': (0, REC), 'BTN_Y': (0, BTN_Y)})
    sym.update({f'S_K{i}': (2, base + off[f'k{i}']) for i in range(5)})
    for k, (o, sz) in {'MODE': (0, 1), 'PAD': (1, 1), 'KIDX': (2, 1), 'ARMED': (3, 1), 'FPREV': (4, 1),
                       'DUP': (5, 1), 'WAIT': (6, 1), 'KEY': (7, 1), 'SV_CTL': (8, 2), 'SV_P1': (10, 2),
                       'SV_P2': (12, 2), 'SV_IT': (14, 2), 'SV_NL': (16, 4), 'CX_': (20, 2), 'CY_': (22, 2),
                       'MINX': (24, 2), 'MAXX': (26, 2), 'MINY': (28, 2), 'MAXY': (30, 2)}.items():
        sym[k] = (2, v + o)
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for o, t_obj, t in ptrs:
        p.add_ptr(2, base + o, t_obj, lab[t] if t_obj == 1 else base + off[t])
    hdr = menu_header(p, sym['OMBD'][1])
    d2 = p.le.obj_bytes(2)
    assert struct.unpack_from('<I', d2, hdr + 4)[0] == 0, 'optionsMenu onReturn'
    p.retarget(2, hdr, 1, lab['ct_optinit'])
    p.put(2, hdr, struct.pack('<I', lab['ct_optinit']))
    p.put(2, hdr + 4, struct.pack('<I', lab['ct_optret']))
    p.add_ptr(2, hdr + 4, 1, lab['ct_optret'])
    print(f'exe: CONTROLS page ({T["title"]}): code obj1+{at:#x} ({len(code)} B), page obj2+{base + m_at:#x}, '
          f'options menu obj2+{hdr:#x}')
    return at + len(code)


LABEL_COL, VALUE_COL = 0x09, 0x0D     # (the OPTIONS rows: labels 9, values 13)
BTN_Y = 169                           # the button between EXIT TO DOS (152 + 15) and EXIT (185)


VARS = {'MODE': 0, 'PAD': 1, 'KIDX': 2, 'ARMED': 3, 'FPREV': 4, 'DUP': 5, 'WAIT': 6, 'KEY': 7, 'CX_': 20, 'CY_': 22,
        'MINX': 24, 'MAXX': 26, 'MINY': 28, 'MAXY': 30}


def runtime(exe, orig, lang):
    """The harness's view of a built exe: obj2 offsets of WORK, the variables, the TEST line and setupDatBuffer."""
    from lepatch import LEPatch
    data, off, _, m_at = layout(lang)
    d2 = LEPatch(exe).le.obj_bytes(2)
    pre = bytes(data[:off['pb']])
    b = d2.find(pre)
    assert b > 0 and d2.find(pre, b + 1) < 0, 'the CONTROLS block'
    sym = locate(LEPatch(orig))
    return {'work': b + off['work'], 'vars': b + off['vars'], 'pb': b + off['pb'], 'menu': b + m_at,
            'buf': sym['BUF'][1], 'rgp': sym['RGP'][1]}
