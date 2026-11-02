"""The stadium's name before the line-ups (4.0.6, Davide's look B).

ShowStadiumInit (the line-ups screen, GameLoop's stadiumMenu) ends with FadeOutToBlack / DrawMenu /
CallToWaitRetrace / FadeIn. Its `call FadeOutToBlack` -> st_fade (chained): when the home club (gameTeam1, the TeamFile
of the left team: countryNumber = its TEAM file, teamOrdinal) has a name in DATA\\STADIUM.DAT, the stadium picture
(the title memory, stad.256) is shown alone with a framed banner (white frame, black fill) in the middle, the name in
the line-ups' small font doubled when twice its width fits 290 px, in the normal size otherwise; it stays ~1.5 s
(105 ticks of menuCycleTimer) or until a key / a new fire, fades out, and the game's line-ups follow as before.
No file, no record or an empty name: no banner, the game's flow unchanged. The file is read with own DOS calls
(LoadFile ends the program on a missing file).

DATA\\STADIUM.DAT (agreed with Dati coppe, little-endian): 'STAD', u16 version 1, u16 venue count V; 256 x (u32 offset,
u16 count) by TEAM file; per file its club records sorted by ordinal: u8 teamOrdinal + 33-byte NUL-padded name (at most
32 chars, the game charset A-Z 0-9 space - . '); then the venue table, V x 33 bytes (venue id 1..V).
Code in obj3 after kbd2 (CONVENTIONS 23).
"""
import re
import struct

import benchx
import nasmcave
import sacups

FILE = b'STADIUM.DAT'
MAGIC = b'STAD'
VERSION = 1
REC = 34                                # u8 ordinal + 33-byte name
NAME = 33
WAIT = 105                              # ticks of menuCycleTimer (70 Hz): ~1.5 s
BIG_MAX = 290                           # doubled when 2 x the width fits this

ASM = r"""
st_fade:                                ; ShowStadiumInit's `call FadeOutToBlack` (the line-ups drawn next)
    call FADEOUT
    pushad
    mov byte [st_shown], 0
    call st_find
    jz .out
    mov esi, D0                         ; (the game's pseudo-registers D0..A6, kept around the text calls)
    mov edi, st_regs
    mov ecx, 15
    rep movsd
    call st_draw
    mov esi, [LIN]                      ; the virtual screen -> the display
    mov edi, 0A0000h
    mov ecx, 16000
    rep movsd
    call FADEIN
    mov byte [st_shown], 1
    call st_wait
    call FADEOUT
    mov esi, st_regs
    mov edi, D0
    mov ecx, 15
    rep movsd
.out:
    popad
    ret

st_find:                                ; ZF = 0: st_name = the home club's stadium (gameTeam1)
    mov byte [st_name], 0
    mov eax, [GT1]
    test eax, eax
    jz .no
    cmp eax, TOP                        ; (a highlights replay: the in-game copies)
    je .no
    mov ax, [eax]                       ; al = countryNumber (the TEAM file), ah = teamOrdinal
    mov [st_key], ax
    mov edx, st_fn
    mov eax, 3D00h
    int 21h
    jc .no
    mov ebx, eax
    mov edx, st_rec                     ; the header: 'STAD', version
    mov ecx, 8
    call .read
    jne .close
    cmp dword [st_rec], 'STAD'
    jne .close
    cmp word [st_rec + 4], 1
    jne .close
    movzx edx, byte [st_key]            ; its index entry: 8 + file x 6
    imul edx, 6
    add edx, 8
    call .seek
    jc .close
    mov edx, st_rec
    mov ecx, 6
    call .read
    jne .close
    movzx esi, word [st_rec + 4]        ; the file's records
    test esi, esi
    jz .close
    mov edx, [st_rec]
    call .seek
    jc .close
.rec:
    mov edx, st_rec
    mov ecx, 34
    call .read
    jne .close
    mov al, [st_rec]
    cmp al, [st_key + 1]
    je .hit
    ja .close                           ; (sorted by ordinal)
    dec esi
    jnz .rec
    jmp .close
.hit:
    push esi
    mov esi, st_rec + 1
    mov edi, st_name
    mov ecx, 33
    rep movsb
    mov byte [st_name + 32], 0          ; (at most 32 chars)
    pop esi
.close:
    mov ah, 3Eh
    int 21h
.no:
    cmp byte [st_name], 0
    ret
.read:                                  ; ecx bytes at edx; ZF = 1 when all read
    mov ah, 3Fh
    push ecx
    int 21h
    pop ecx
    jc .rf
    movzx eax, ax
    cmp eax, ecx
    ret
.rf:
    or ecx, ecx                         ; (ecx > 0: ZF = 0)
    ret
.seek:                                  ; to edx from the start
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    ret

st_draw:                                ; the stadium picture + the banner on the virtual screen
    mov esi, [LIN]
    lea esi, [esi + 20000h]             ; (the title memory: stad.256)
    mov edi, [LIN]
    mov ecx, 16000
    rep movsd
    mov eax, [CHT]                      ; (the line-ups' names' font: charTables[0])
    mov [A1], eax
    mov dword [A0], st_name
    call GTW
    movzx eax, word [D7]                ; the width
    mov [st_w], eax
    lea ecx, [eax + eax]
    cmp ecx, BIG_MAX
    setbe byte [st_big]
    jbe .big
    mov ebx, 160                        ; normal size: x = 160 - (w + 1) / 2, the box 12 px around it, y 90..108
    lea ecx, [eax + 1]
    shr ecx, 1
    sub ebx, ecx
    mov [st_x], ebx
    mov edi, 90
    mov edx, 108
    mov ecx, 97
    jmp .box
.big:
    mov ebx, 160                        ; doubled: x = 160 - w, y 86..112 (the text rows 94.. doubled)
    sub ebx, eax
    mov [st_x], ebx
    mov edi, 86
    mov edx, 112
    mov ecx, 94
.box:
    mov [st_y], ecx
    lea eax, [ebx - 12]                 ; eax = left, ebx = right, edi = top, edx = bottom
    add ebx, [st_w]
    cmp byte [st_big], 0
    je .r
    add ebx, [st_w]
.r:
    add ebx, 12
    mov [st_box], eax
    mov [st_box + 4], edi
    mov [st_box + 8], ebx
    mov [st_box + 12], edx
    mov cl, 2                           ; the frame (white), the fill (black) 1 px inside
    call st_rect
    inc eax
    inc edi
    dec ebx
    dec edx
    mov cl, 3
    call st_rect
    mov eax, [CHT]
    mov [A1], eax
    mov dword [A0], st_name
    mov eax, [st_x]
    mov [D1], ax
    mov eax, [st_y]
    mov [D2], ax
    mov word [D3], 2
    call DMT
    cmp byte [st_big], 0
    je .ret
    call st_double
.ret:
    ret

st_rect:                                ; colour cl, x eax..ebx, y edi..edx (inclusive) on the virtual screen
    pushad
    mov esi, edi
.y:
    imul edi, esi, 320
    add edi, [LIN]
    add edi, eax
    push eax
    mov al, cl
    mov ecx, ebx
    sub ecx, [esp]
    inc ecx
    rep stosb
    pop eax
    mov cl, [esp + 24]                  ; (pushad's ecx)
    inc esi
    cmp esi, edx
    jbe .y
    popad
    ret

st_double:                              ; the text block (st_x, st_y, w + 2 x 8) x 2 in place, from its far corner
    pushad                              ; (each target pixel lies at or after its source: nothing unread is overwritten)
    mov ebp, 7                          ; j = 7..0
.j:
    mov ecx, [st_w]
    inc ecx                             ; i = w + 1..0
.i:
    mov eax, [st_y]                     ; source (x + i, y + j)
    add eax, ebp
    imul eax, eax, 320
    add eax, [st_x]
    add eax, ecx
    add eax, [LIN]
    mov dl, [eax]
    mov eax, ebp                        ; target (x + 2i, y + 2j), 2 x 2
    add eax, eax
    add eax, [st_y]
    imul eax, eax, 320
    add eax, [st_x]
    add eax, ecx
    add eax, ecx
    add eax, [LIN]
    mov dh, dl
    mov [eax], dx
    mov [eax + 320], dx
    dec ecx
    jns .i
    dec ebp
    jns .j
    popad
    ret

st_wait:                                ; ~1.5 s; a key or a new fire ends it (the one that started the match is
    mov byte [st_rel], 0                ; still held: not a new one)
    mov byte [st_skip], 0
    mov byte [st_on], 1
    mov word [MCT], 0
.l:
    mov ax, [MCT]
.w:
    cmp ax, [MCT]                       ; (one controls read a tick)
    je .w
    pushad
    call MCC
    popad
    cmp word [LASTKEY], 0
    jne .skip
    mov al, [FIRE]
    or al, [SHORTFIRE]
    jz .rel
    cmp byte [st_rel], 0
    jne .skip
    jmp .t
.rel:
    mov byte [st_rel], 1
.t:
    cmp word [MCT], WAIT_
    jb .l
    jmp .out
.skip:
    mov byte [st_skip], 1
.out:
    mov ax, [MCT]
    mov [st_ticks], ax
    mov byte [st_on], 0
    ret

st_fn: db 'data\stadium.dat', 0
st_mark: db 'STNM'                      ; (the harness finds these by the mark)
st_name: times 33 db 0                  ; the name shown last ('' = none)
st_shown: db 0                          ; 1 once the banner is on the display
st_big: db 0                            ; 1: doubled
st_rel: db 0
st_skip: db 0                           ; 1: ended by a key / fire
st_key: dw 0                            ; countryNumber, teamOrdinal (looked up last)
st_ticks: dw 0                          ; the ticks it stayed
st_on: db 0                             ; 1 while it waits (the harness: bench scenarios wait it out)
align 4
st_box: dd 0, 0, 0, 0                   ; left, top, right, bottom
st_x: dd 0
st_y: dd 0
st_w: dd 0
st_rec: times 34 db 0
align 4
st_regs: times 15 dd 0
"""


def sites(p):
    """The original obj1's sites and variables (benchx.sites7's for the line-ups screen and the controls)."""
    d = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d)
    D7, A0, A1 = r['D7'], r['A0'], r['A1']
    D0, D1, D2 = D7 - 28, D7 - 24, D7 - 20
    pk = lambda x: re.escape(struct.pack('<I', x))
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    s7 = benchx.INFO['S7'] if 'S7' in benchx.INFO else benchx.sites7(p, r)   # (a probe of the original: no INFO)
    end = s7['stend'] - 20          # call FadeOutToBlack / DrawMenu / CallToWaitRetrace / FadeIn, jmp SetExitMenuFlag
    assert all(d[end + k] == 0xE8 for k in (0, 5, 10, 15)), 'ShowStadiumInit end'
    assert bytes(p.get(1, end, 5)) == d[end:end + 5], 'stadium: FadeOutToBlack call already patched'
    lin = p.target(1, s7['DRAWMENU'][1] + 2)              # DrawMenu: mov esi, [linAdr384k]
    assert d[s7['DRAWMENU'][1]:s7['DRAWMENU'][1] + 2] == b'\x8b\x35' and lin[0] == 2, ('linAdr384k', lin)
    # DrawMenuTextCentered: push D1 / D2 / A0 / A1, call GetTextWidth, 4 pops, D7 = (D7 + 1) / 2, D1 -= it,
    # jmp DrawMenuText
    m = [x.start() for x in re.finditer(rb'\xff\x35' + pk(D1) + rb'\xff\x35' + pk(D2) + rb'\xff\x35' + pk(A0)
                                         + rb'\xff\x35' + pk(A1) + rb'\xe8....(?:\x8f\x05....){4}\x66\x83\x05' + pk(D7)
                                         + rb'\x01\x66\xd1\x2d' + pk(D7) + rb'\x66\xa1' + pk(D7) + rb'\x66\x29\x05' + pk(D1)
                                         + rb'\xe9', d, re.S)]
    assert m, 'DrawMenuTextCentered'
    gtw, dmt = rel(m[0] + 24), rel(m[0] + 24 + 5 + 24 + 8 + 7 + 6 + 7)
    assert all(rel(x + 24) == gtw for x in m), ('GetTextWidth', [hex(rel(x + 24)) for x in m])
    # DrawMenuItem: mov A1, offset charTables / mov esi, A1 / movzx eax, word [D0] ...
    ct = {p.target(1, x.start() + 6) for x in re.finditer(rb'\xc7\x05' + pk(A1) + rb'....\x8b\x35' + pk(A1)
                                                           + rb'\x0f\xb7\x05' + pk(D0) + rb'\x03\xf0\x8b\x06\xa3' + pk(A1),
                                                           d, re.S)}
    assert len(ct) == 1, ('charTables', ct)
    # InitializeInGameTeamsAndStartGame: hilStarted = 0 / plg_D0_param = D0 / gameMinSubstitutes = D1 /
    # gameMaxSubstitutes = D2 / plg_D3_param = D3 / gameTeam1 = A1 / gameTeam2 = A2
    st = lambda r: rb'\x66\xa1' + pk(r) + rb'\x66\xa3....'
    gt = {p.target(1, x.end() - 9) for x in re.finditer(rb'\x66\xc7\x05....\x00\x00' + st(D0) + st(D1) + st(D2) + st(D7 - 16)
                                                        + rb'\xa1' + pk(A1) + rb'\xa3....\xa1' + pk(A1 + 4), d, re.S)}
    assert len(gt) == 1, ('gameTeam1', gt)
    return {'end': end, 'FADEOUT': p.call_target(1, end), 'FADEIN': p.call_target(1, end + 15), 'LIN': lin,
            'GTW': (1, gtw), 'DMT': (1, dmt), 'CHT': ct.pop(), 'GT1': gt.pop(), 'TOP': s7['TOP'], 'MCC': s7['MCC'],
            'MCT': s7['MCT'], 'LASTKEY': s7['LASTKEY'], 'FIRE': s7['FIRE'], 'SHORTFIRE': s7['SHORTFIRE'],
            'D0': (2, D0), 'D1': (2, D1), 'D2': (2, D2), 'D3': (2, D7 - 16), 'D7': (2, D7), 'A0': (2, A0), 'A1': (2, A1)}


def patch(p, at):
    """st_* at obj3:at (after kbd2); returns the end."""
    s = sites(p)
    sym = {k: v for k, v in s.items() if k != 'end'}
    sym.update(BIG_MAX=(0, BIG_MAX), WAIT_=(0, WAIT))
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['end'], 0xE8, 3, lab['st_fade'])
    print(f'exe: stadium: the home club\'s stadium before the line-ups, obj3+{at:#x} ({len(code)} B), '
          f'ShowStadiumInit obj1+{s["end"]:#x}')
    return at + len(code)


def build(records, venues=()):
    """STADIUM.DAT: records = {(team file, ordinal): name}, venues = [name, ...] (venue id = index + 1)."""
    by = {}
    for (f, o), n in records.items():
        by.setdefault(f, []).append((o, n))
    head = MAGIC + struct.pack('<HH', VERSION, len(venues))
    idx, body = bytearray(), bytearray()
    off = len(head) + 256 * 6
    for f in range(256):
        recs = sorted(by.get(f, []))
        idx += struct.pack('<IH', off + len(body) if recs else 0, len(recs))
        for o, n in recs:
            body += bytes([o]) + check(n).encode('ascii').ljust(NAME, b'\0')
    ven = b''.join(check(v).encode('ascii').ljust(NAME, b'\0') for v in venues)
    return head + bytes(idx) + bytes(body) + ven


CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -.'")


def check(name):
    assert len(name) <= 32 and set(name) <= CHARSET, ('stadium name', name)
    return name
