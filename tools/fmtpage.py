"""FORMAT page (5.0 / 4.0): a text page describing a competition's format, from the competition view.

Where: STAT (the competition view's statistics: cseg_33E38 sets diyNameOfCompetitionPtr = the contest slot + 4, its
name, then `mov [A6], offset competitionStatsMenu / call ShowMenu`) gets a copy of competitionStatsMenu with a 6th
entry FORMULA / FORMAT / FORMULE / MODUS under VIEW SQUADS. It opens the page: a menu of our own with the
competition's name, LINES lines of up to LINE_W - 1 characters (small font, left) and NEXT PAGE / EXIT.

Texts: DATA\\FMTxx.DAT (xx = the exe language: IT, EN, FR, DE), read only when the page opens, with DOS calls of our
own (the game's LoadFile ends the program on a missing file; a missing file or key shows NONE): into a BSS buffer of
BSS_SIZE bytes, nothing resident.
  header  'FMT1', u16 entries, u16 0
  entry   48 bytes: u8 contest id (the slot's byte +2Dh; 0FFh = any), 41 bytes name (the slot's name: the title
          the game shows, e.g. ITALIA 1947-48 SERIE A 1947-48, NUL padded), u32 file offset of the text, u16 its length
  text    lines separated by LF, pages by FF; upper case, the game's font (no accents).
build(path, pages) writes such a file: pages = [(id or None, name, [page = [line, ...], ...]), ...].
"""
import re
import struct

import nasmcave

LINES = 14
LINE_W = 42                     # buffer per line (41 characters + NUL); the renderer wraps at 40
IDXMAX = 0x6000                 # header + index read at once (511 entries)
TXTMAX = 0x2000                 # one competition's text
BSS_SIZE = IDXMAX + TXTMAX
ENTRY = 48
NAME = 41                       # the slot's name (+4 .. +2Ch, before the contest id): the title the game shows

TEXTS = {
    'it': dict(btn=b'FORMULA', next=b'PAG. SUCC.', none=b'NESSUNA DESCRIZIONE', file=b'data/fmtit'),
    'en': dict(btn=b'FORMAT', next=b'NEXT PAGE', none=b'NO DESCRIPTION', file=b'data/fmten'),
    'fr': dict(btn=b'FORMULE', next=b'PAGE SUIV.', none=b'PAS DE DESCRIPTION', file=b'data/fmtfr'),
    'de': dict(btn=b'MODUS', next=b'WEITER', none=b'KEINE BESCHREIBUNG', file=b'data/fmtde'),
}

ASM = r"""
fp_open:                                ; FORMULA (fire): the page of the competition the statistics are of
    pushad
    mov dword [PAGE], 0
    mov byte [FOUND], 0
    mov esi, [DIYNAME]
    mov edi, TITLE
    mov ecx, NAME_ - 1
.title:
    lodsb
    stosb
    test al, al
    jz .titled
    loop .title
    mov byte [edi], 0
.titled:
    mov edi, FNAME + FN_BASE_           ; data/fmtxx + the career's world number (none: the base world) + .dat
WORLD_FILE
    mov dword [edi], 7461642Eh          ; '.dat'
    mov byte [edi + 4], 0
    mov edx, FNAME
    mov eax, 3D00h                      ; open, read only
    int 21h
    jc .show
    mov ebx, eax
    mov edx, BUF
    mov ecx, IDXMAX_
    mov ah, 3Fh
    int 21h
    jc .close
    cmp dword [BUF], 31544D46h          ; 'FMT1'
    jne .close
    movzx ecx, word [BUF + 4]
    mov esi, BUF + 8
    mov edi, [DIYNAME]
    mov dl, [edi + 29h]                 ; the slot's contest id (+2Dh)
.find:
    jecxz .close
    mov al, [esi]
    cmp al, 0FFh
    je .name
    cmp al, dl
    jne .next
.name:
    push ecx
    push edi
    xor ecx, ecx
.cmp:
    mov al, [esi + ecx + 1]
    test al, al
    jz .kend
    cmp al, [edi + ecx]
    jne .ne
    inc ecx
    cmp ecx, NAME_ - 1
    jb .cmp
    jmp .eq                             ; a key of 40 characters: the title starts with it (a longer one cut)
.kend:
    cmp byte [edi + ecx], 0             ; a shorter key: the whole title
    jne .ne
.eq:
    pop edi
    pop ecx
    jmp .found
.ne:
    pop edi
    pop ecx
.next:
    add esi, ENTRY_
    dec ecx
    jmp .find
.found:
    mov edx, [esi + NAME_ + 1]          ; seek: cx:dx = offset
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    jc .close
    movzx ecx, word [esi + NAME_ + 5]
    cmp ecx, TXTMAX_ - 1
    jbe .len
    mov ecx, TXTMAX_ - 1
.len:
    mov edx, TXT
    mov ah, 3Fh
    int 21h
    jc .close
    mov byte [TXT + eax], 0
    mov byte [FOUND], 1
.close:
    mov ah, 3Eh
    int 21h
.show:
    call fp_fill
    popad
    mov dword [A6], FMTMENU
    jmp SHOW_MENU

fp_next:                                ; NEXT PAGE (fire): the next page, after the last the first
    inc dword [PAGE]
    call fp_fill
    ret

fp_fill:                                ; LINES from page [PAGE] of TXT (FOUND), else NONE
    pushad
    mov edi, LINES_BUF
    mov ecx, LINES_ * LINE_W_
    xor eax, eax
    rep stosb
    cmp byte [FOUND], 0
    jne .text
    mov esi, NONE
    mov edi, LINES_BUF
.none:
    lodsb
    stosb
    test al, al
    jnz .none
    jmp .out
.text:
    mov esi, TXT
    mov ecx, [PAGE]
.skip:
    jecxz .fill
.ff:
    lodsb
    test al, al
    jz .first
    cmp al, 0Ch
    jne .ff
    dec ecx
    jmp .skip
.first:                                 ; past the last page: the first one
    mov dword [PAGE], 0
    mov esi, TXT
.fill:
    mov ebx, LINES_BUF
    mov edx, LINES_
    xor ecx, ecx
.ch:
    lodsb
    test al, al
    jz .out
    cmp al, 0Ch
    je .out
    cmp al, 0Ah
    je .nl
    cmp ecx, LINE_W_ - 1
    jae .ch
    mov [ebx + ecx], al
    inc ecx
    jmp .ch
.nl:
    add ebx, LINE_W_
    xor ecx, ecx
    dec edx
    jnz .ch
.out:
    popad
    ret
"""


def _entries(menu, start, end):
    """{entry number: (offset, positions record offset or None)} of the packed entries in menu[start:end]."""
    out, k, n = {}, start, 0
    while k < end:
        w = struct.unpack_from('<h', menu, k)[0]
        assert w not in (-998, -997, -996, -999), (k, w)
        e, pos = k, None
        k += 8
        while True:
            t = struct.unpack_from('<H', menu, k)[0]
            k += 2
            if t == 0:
                break
            if t == 2:
                pos = k
            k += {1: 0, 2: 4, 4: 2, 8: 6, 13: 4, 14: 8, 20: 2}[t]
        out[n] = (e, pos)
        n += 1
    return out


def locate(p):
    """cseg_33E38 (the competition view's STAT): (A6 store site, competitionStatsMenu, diyNameOfCompetitionPtr,
    ShowMenu, A6)."""
    d = p.le.obj_bytes(1)
    a = [m.start() for m in re.finditer(rb'\x05\x2D\x01\x00\x00', d)]      # add eax, 301 (league teams)
    b = [m.start() for m in re.finditer(rb'\x05\x4D\x02\x00\x00', d)]      # add eax, 589 (cup teams)
    hits = [(x, y) for x in a for y in b if 0 < y - x < 0x100]
    sites = []
    for x, y in hits:
        m = re.compile(rb'\xC7\x05(....)(....)\xE8(....)\xC3', re.S).search(d, y, y + 0x80)
        if m and d[x - 10] == 0xA3:
            sites.append((x, m.start()))
    assert len(sites) == 1, sites
    x, site = sites[0]
    name = p.target(1, x - 9)                           # mov [diyNameOfCompetitionPtr], eax (before add eax, 301)
    a6 = p.target(1, site + 2)
    menu = p.target(1, site + 6)
    show = site + 15 + struct.unpack('<i', d[site + 11:site + 15])[0]
    return site, menu, name, show, a6


WORLD_ASM = r"""
    cmp word [GAMETYPE], 4              ; a career: its world (the save's byte; stale outside a career)
    jne .w0
    movzx eax, byte [SLT + WORLD_BYTE_]
    test eax, eax
    jz .w0
    xor edx, edx
    mov ecx, 10
    div ecx
    test eax, eax
    jz .units
    add al, '0'
    stosb
.units:
    lea eax, [edx + '0']
    stosb
.w0:
"""


def patch(p, at, lang, area, bss, world=None):
    """Code at obj1:at, menus and buffers in obj2 area, the file buffer at obj2:bss (BSS_SIZE); world = careerworld's
    sites in a build with career worlds (DATA\\FMTxx<world>.DAT in a career of world 1+). Returns the code end."""
    d, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    site, (mobj, moff), name, show, a6 = locate(p)
    assert mobj == 2 and struct.unpack_from('<IIIIhhhh', d2, moff) == (0, 0, 0, 1, 92, 0, 120, 15), 'competitionStatsMenu'
    end = moff + 16
    while struct.unpack_from('<h', d2, end)[0] != -999:
        end += 2
    ents = _entries(d2, moff + 16, end)
    assert len(ents) == 5, ents
    fixes = [(o, t_obj, t_off) for (s_obj, o, _, t_obj, t_off, *_r) in p.le.fixups() if s_obj == 2 and moff <= o < end]
    T = TEXTS[lang]

    data = bytearray()
    off, ptrs = {}, []
    def put(key, b, size=None):
        off[key] = len(data)
        data.extend(b + b'\0' * ((size or len(b) + 1) - len(b)))
    for k in ('btn', 'next', 'none'):
        put(k, T[k])
    put('file', T['file'], 20)
    put('title', b'', NAME + 1)
    put('lines', b'', LINES * LINE_W)
    put('vars', b'', 8)                                  # page (dword), found (byte)
    while len(data) % 4:
        data.append(0)

    # the statistics menu with FORMULA (entry 5) between VIEW SQUADS (3) and EXIT (4)
    sm_at = len(data)
    sm = bytearray(d2[moff:end])
    for o, t_obj, t_off in fixes:
        ptrs.append((sm_at + o - moff, t_obj, t_off))
    e3, e4 = ents[3][1] - moff, ents[4][1] - moff
    assert sm[e3 + 3] == 4 and sm[e4 + 2] == 3, (sm[e3:e3 + 4], sm[e4:e4 + 4])
    sm[e3 + 3] = 5                                       # VIEW SQUADS: down -> FORMULA
    sm[e4 + 2] = 5                                       # EXIT: up -> FORMULA
    exit_text = [t for o, t in ((o, (t_obj, t_off)) for o, t_obj, t_off in fixes) if o == ents[4][0] + 22]
    exit_fn = [t for o, t in ((o, (t_obj, t_off)) for o, t_obj, t_off in fixes) if o == ents[4][0] + 28]
    assert len(exit_text) == 1 and len(exit_fn) == 1, (exit_text, exit_fn)
    def entry(buf, base_at, x, y, w, h, nav=None, color=None, text=None, flags=0, select=None):
        b = bytearray(struct.pack('<hhhh', x, y, w, h))
        if nav:
            b += struct.pack('<H', 2) + bytes(v & 0xFF for v in nav)
        if color is not None:
            b += struct.pack('<HH', 4, color)
        if text is not None:
            b += struct.pack('<HH', 8, flags)
            ptrs.append((base_at + len(buf) + len(b), text[0], text[1]))
            b += b'\0\0\0\0'
        if select is not None:
            b += struct.pack('<H', 13)
            ptrs.append((base_at + len(buf) + len(b), select[0], select[1]))
            b += b'\0\0\0\0'
        buf.extend(b + b'\0\0')
    tail = bytearray()
    entry(tail, sm_at + len(sm), 92, 115, 120, 15, nav=(-1, -1, 3, 4), color=0x0E, text=(2, 'btn'), select=(1, 'fp_open'))
    sm += tail + struct.pack('<h', -999)
    data.extend(sm)
    while len(data) % 4:
        data.append(0)

    # the page: 0 the competition's name, 1..LINES the lines, NEXT PAGE, EXIT (default)
    fm_at = len(data)
    nx, ex = LINES + 1, LINES + 2
    fm = bytearray(struct.pack('<IIII', 0, 0, 0, ex))
    entry(fm, fm_at, 0, 0, 304, 14, color=0x17, text=(2, 'title'))
    for i in range(LINES):
        entry(fm, fm_at, 0, 20 + 11 * i, 304, 10, text=(2, ('lines', i)), flags=0x8000)
    entry(fm, fm_at, 50, 185, 100, 15, nav=(-1, ex, -1, -1), color=0x0E, text=(2, 'next'), select=(1, 'fp_next'))
    entry(fm, fm_at, 154, 185, 100, 15, nav=(nx, -1, -1, -1), color=0x0C, text=exit_text[0], select=exit_fn[0])
    fm += struct.pack('<h', -999)
    data.extend(fm)

    base = area.add(bytes(data))
    assert not any((base + o) // 0x1000 != (base + o + 3) // 0x1000 for o, _, _ in ptrs), 'a pointer straddles a page'
    at = (at + 15) & ~15
    sym = {'DIYNAME': name, 'A6': a6, 'SHOW_MENU': (1, show), 'FNAME': (2, base + off['file']),
           'TITLE': (2, base + off['title']), 'LINES_BUF': (2, base + off['lines']), 'NONE': (2, base + off['none']),
           'PAGE': (2, base + off['vars']), 'FOUND': (2, base + off['vars'] + 4), 'FMTMENU': (2, base + fm_at),
           'BUF': (2, bss), 'TXT': (2, bss + IDXMAX), 'IDXMAX_': (0, IDXMAX), 'TXTMAX_': (0, TXTMAX),
           'ENTRY_': (0, ENTRY), 'NAME_': (0, NAME), 'LINES_': (0, LINES), 'LINE_W_': (0, LINE_W),
           'FN_BASE_': (0, len(T['file']))}
    src = ASM.replace('WORLD_FILE\n', WORLD_ASM if world else '')
    if world:
        sym.update({'GAMETYPE': world['gametype'], 'SLT': world['slt'], 'WORLD_BYTE_': (0, 1845)})
    code, cfix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for o, t_obj, t in ptrs:
        if isinstance(t, str):
            t = lab[t] if t_obj == 1 else base + off[t]
        elif isinstance(t, tuple):
            t = base + off[t[0]] + LINE_W * t[1]
        p.add_ptr(2, base + o, t_obj, t)
    p.retarget(1, site + 6, 2, base + sm_at)
    p.put(1, site + 6, struct.pack('<I', base + sm_at))
    print(f'exe: FORMAT page: statistics menu + FORMULA obj2+{base + sm_at:#x}, page obj2+{base + fm_at:#x}, '
          f'code obj1+{at:#x} ({len(code)} B), file {T["file"].decode()}[world].dat, buffer obj2+{bss:#x}')
    return at + len(code)


def build(path, pages):
    """DATA\\FMTxx.DAT from [(contest id or None, name, [[line, ...], ...]), ...]."""
    idx, body = bytearray(), bytearray()
    head = 8 + ENTRY * len(pages)
    assert head <= IDXMAX, len(pages)
    for cid, name, pp in pages:
        txt = '\x0c'.join('\n'.join(l.upper() for l in pg[:LINES]) for pg in pp).encode('ascii')
        assert len(txt) < TXTMAX, (name, len(txt))
        nm = name.encode('latin-1')[:NAME - 1]
        idx += struct.pack('<B', 0xFF if cid is None else cid) + nm + b'\0' * (NAME - len(nm))
        idx += struct.pack('<IH', head + len(body), len(txt))
        idx += b'\0' * (-len(idx) % ENTRY)
        body += txt
    open(path, 'wb').write(b'FMT1' + struct.pack('<HH', len(pages), 0) + idx + body)
