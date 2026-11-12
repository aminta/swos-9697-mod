"""4.2 names-fit (Marco (b) step 2, Davide 12/11 scope A): player names on the menu screens cut by PIXELS, not by
characters (survey: internal/handoff/names14-menus-survey.md).

The game cuts a name in the menus with ExtractSurname by a character count, but its columns have room for more: the
small font's letters are 6 px, an I 2, a space 3. Four sites:
- the squad screen's list (DrawPlayerEntries, 800Dh: the initial + surname, 13 characters; VIS. SQUADRA too) and the
  tactics editor's list (EditTacticsAfterDrawPlayerNames, 800Dh): the name entry's width - 3 px;
- the transfer market lists (cseg_54116: the whole name, 29 - length(club) characters): from the name entry's x to
  the club entry's right edge (the club is right-aligned in the next entry), minus the '(club)' width and a gap;
- the top scorers (TopGoalScorersBeforeDrawCommon, 15h: the whole name, 21 characters): to the club column's x.

Each site's `call ExtractSurname` -> a stub (obj4, type-8 fixups) that computes that room and calls nf_go:
1. the game's ExtractSurname as before (its D0); not cut (no-flag sites: the name itself returned; 800Dh: the result
   shorter than 13 or not ending in '.') = kept as it is, byte for byte;
2. cut: the first text that fits the room, measured with the game's own GetTextWidth (smallCharsTable): the whole
   name (market, scorers), the initial + the surname words, the surname words dropping leading words (the match's
   rule: JOSE ANTONIO CAMACHO -> ANTONIO CAMACHO), last the initial form (one word: the word) cut by pixels + '.'.
The text goes into a ring of 16 buffers x 24 bytes (the market and the scorers set every row in one pass - the
game's single surnameBuf would make the cut rows share one text; 16 >= the rows of any of these screens).
Code + buffers at obj4 swreg.NAMEFIT_AT..NAMEFIT_END (MC 12/11, page 13 below trial: 948 of 0x400 B); nothing saved.
One base register (ebx -> nf_data, the game's D0..A6 through nf_regs): 6 absolute fixups + 2 rel32 (CLAUDE.md: the LE
header padding); GetTextWidth called with every x86 register and the game's D0..A6 kept."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nasmcave
import sacups

RING, BUF = 16, 24

ASM = r"""
BITS 32
%define V(x) [ebx + x - nf_data]        ; (one base register: ebx -> nf_data; the game's D0..A6 via nf_regs)
nf_sq:                                  ; squad screen / tactics editor (800Dh): [esp+16] -> the name entry
    pushad
    mov ebx, nf_data
    mov eax, [esp + 48]
    movzx ecx, word [eax + 18h]
    sub ecx, 3
    xor edx, edx
    jmp nf_set
nf_sc:                                  ; top scorers (15h): [A4] -> the name entry, +38h the club entry (left-aligned)
    pushad
    mov ebx, nf_data
    mov esi, V(nf_regs)
    mov eax, [esi + 30h]
    movzx ecx, word [eax + 38h + 14h]
    movzx edx, word [eax + 14h]
    sub ecx, edx
    sub ecx, 4
    jmp nf_set1
nf_mk:                                  ; market (no flags): [A2] -> the name entry, +38h the club entry (right-aligned),
    pushad                              ; [A4] -> the club's name or 0
    mov ebx, nf_data
    mov esi, V(nf_regs)
    mov eax, [esi + 28h]
    movzx ecx, word [eax + 38h + 14h]
    movzx edx, word [eax + 38h + 18h]
    add ecx, edx
    movzx edx, word [eax + 14h]
    sub ecx, edx
    sub ecx, 6                          ; (the text's left pad 2 + a gap of 4 before the club)
    mov edi, [esi + 30h]
    or edi, edi
    jz nf_set1
    call nf_width
    sub ecx, eax
    lea edi, V(nf_par)
    call nf_width
    sub ecx, eax
nf_set1:
    mov edx, 1
nf_set:
    mov V(nf_room), ecx
    mov V(nf_mode), edx
    mov esi, V(nf_regs)
    mov eax, [esi + 20h]
    mov V(nf_name), eax
    mov ax, [esi]
    mov V(nf_lim), ax
    popad
    call EXTRACT                        ; the game's cut
    pushad
    mov ebx, nf_data
    mov edx, V(nf_regs)
    mov esi, [edx + 20h]
    cmp dword V(nf_mode), 0
    jne .m1
    movzx ecx, word V(nf_lim)           ; 800Dh: cut = 13 characters ending in '.'
    and ecx, 3FFFh
    xor eax, eax
.len:
    cmp byte [esi + eax], 0
    je .lz
    inc eax
    jmp .len
.lz:
    cmp eax, ecx
    jne .keep
    cmp byte [esi + eax - 1], '.'
    jne .keep
    jmp .fit
.m1:
    cmp esi, V(nf_name)                 ; (no flags: the name itself = not cut)
    je .keep
.fit:
    mov eax, V(nf_ix)
    inc dword V(nf_ix)
    and eax, RING_ - 1
    imul eax, eax, BUF_
    lea ebp, [ebx + nf_bufs - nf_data + eax]   ; ebp -> this call's buffer
    mov esi, V(nf_name)
    call nf_skip
    mov V(nf_first), esi                ; -> the first word
.w1:
    mov al, [esi]
    or al, al
    jz .rs
    cmp al, ' '
    je .rs
    inc esi
    jmp .w1
.rs:
    call nf_skip
    mov V(nf_rest), esi                 ; -> the words past the first (a NUL: one word)
    cmp dword V(nf_mode), 0
    je .ini
    mov esi, V(nf_first)                ; 1. the whole name (market, scorers)
    call nf_cpy0
    call nf_try
    jnc .done
.ini:
    mov esi, V(nf_rest)
    cmp byte [esi], 0
    je .last1
    call nf_inif                        ; 2. the initial + the surname words
    call nf_try
    jnc .done
    mov esi, V(nf_rest)
.drop:                                  ; 3. the surname words, dropping leading words
    push esi
    call nf_cpy0
    call nf_try
    pop esi
    jnc .done
.nw:
    lodsb
    or al, al
    jz .last
    cmp al, ' '
    jne .nw
    call nf_skip
    cmp byte [esi], 0
    jne .drop
.last:                                  ; 4. the initial form cut by pixels
    call nf_inif
    jmp .cut
.last1:                                 ; (one word: itself, then cut)
    mov esi, V(nf_first)
    call nf_cpy0
    call nf_try
    jnc .done
.cut:
    mov ecx, edi
    sub ecx, ebp
.c1:
    cmp ecx, 2
    jb .keep                            ; (nothing fits: the game's text)
    mov word [ebp + ecx - 1], 002Eh     ; ('.' + NUL)
    call nf_try
    jnc .done
    dec ecx
    jmp .c1
.done:
    mov edx, V(nf_regs)
    mov [edx + 20h], ebp
.keep:
    popad
    ret

nf_skip:                                ; esi past spaces
    cmp byte [esi], ' '
    jne .r
    inc esi
    jmp nf_skip
.r: ret

nf_inif:                                ; ebp <- the first word's initial + '. ' + the words at [nf_rest]
    mov edi, ebp
    mov esi, V(nf_first)
    mov al, [esi]
    mov [edi], al
    mov word [edi + 1], 202Eh
    add edi, 3
    mov esi, V(nf_rest)
    jmp nf_cpy
nf_cpy0:
    mov edi, ebp
nf_cpy:                                 ; esi -> NUL-ended text, copied to edi (at most BUF_-1 from ebp), trailing
    lea edx, [ebp + BUF_ - 1]           ; spaces off; edi -> its NUL
.l:
    lodsb
    or al, al
    jz .e
    cmp edi, edx
    jae .e
    stosb
    jmp .l
.e:
    cmp edi, ebp
    je .z
    cmp byte [edi - 1], ' '
    jne .z
    dec edi
    jmp .e
.z:
    mov byte [edi], 0
    ret

nf_try:                                 ; CF clear when the text at ebp fits nf_room (all registers kept but eax)
    push edi
    mov edi, ebp
    call nf_width
    pop edi
    dec eax                             ; (GetTextWidth counts the spacing after the last character)
    cmp V(nf_room), eax
    ret

nf_width:                               ; edi -> text: eax = GetTextWidth(text, smallCharsTable); every x86 register
    pushad                              ; and the game's D0..A6 kept
    mov ebp, V(nf_regs)
    sub esp, 60
    mov edx, edi
    mov esi, ebp
    mov edi, esp
    mov ecx, 15
    cld
    rep movsd
    mov [ebp + 20h], edx
    mov eax, V(nf_small)
    mov [ebp + 24h], eax
    push ebp
    call GTW
    pop ebp
    movzx eax, word [ebp + 1ch]
    mov [esp + 60 + 28], eax            ; (pushad's eax)
    mov esi, esp
    mov edi, ebp
    mov ecx, 15
    rep movsd
    add esp, 60
    popad
    ret

align 4
nf_data:
nf_regs: dd REGS                        ; (the game's D0; +20h A0, +24h A1, +28h A2, +30h A4, D7 +1Ch)
nf_small: dd SMALL
nf_room: dd 0
nf_mode: dd 0
nf_name: dd 0
nf_first: dd 0
nf_rest: dd 0
nf_ix: dd 0
nf_lim: dw 0, 0
nf_par: db '()', 0
align 4
nf_bufs: times RING_ * BUF_ db 0
"""


def sites(p):
    """{'sq': [2 x obj1 offset of the 800Dh `call ExtractSurname`], 'mk': market's (obj1), 'sc': scorers' (OBJ2) in the
    original exe,
    + the register addresses (obj2)."""
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D7 = r['D7']
    D0 = D7 - 28
    P = lambda a: re.escape(struct.pack('<I', a))
    sq = [m.end() - 1 for m in re.finditer(rb'\x66\xc7\x05' + P(D0) + rb'\x0d\x80(?:\xff\x35....){3}\xe8', d1, re.S)]
    assert len(sq) == 2, ('800Dh sites', sq)
    mk = []
    for m in re.finditer(rb'\x66\xc7\x05' + P(D0) + rb'\x0d\x00', d1):
        n = re.match(rb'.{0,40}?(?:\xff\x35....){5}\xe8', d1[m.end():m.end() + 80], re.S)
        if n and re.search(rb'\x66\x01\x05' + P(D0), d1[m.end():m.end() + n.end()]):   # (add word [D0], ax: + D1)
            mk.append(m.end() + n.end() - 1)
    assert len(mk) == 1, ('market site', mk)
    d2 = p.le.obj_bytes(2)                              # (TopGoalScorersBeforeDrawCommon is code in obj2: its call
    sc = [m.end() - 1 for m in re.finditer(rb'\x66\xc7\x05' + P(D0) + rb'\x15\x00(?:\xff\x35....){4}\xe8', d2, re.S)]
    assert len(sc) == 1, ('scorers site (obj2)', sc)    #  a self-relative fixup into obj1)
    regs = dict(A0=r['A0'], D7=D7, D0=D0)
    for k in range(7):
        regs[f'A{k}'] = r['A0'] + 4 * k
    for k in range(8):
        regs[f'D{k}'] = D0 + 4 * k
    return {'sq': sq, 'mk': mk[0], 'sc': sc[0], 'regs': regs}


def _rel(d, c):
    return c + 5 + struct.unpack_from('<i', d, c + 1)[0]


def patch(p):
    import lepatch
    import modver
    import swreg
    orig = lepatch.LEPatch(bytes(p.le.data))
    s = sites(orig)
    mv = modver.find(orig)
    d1 = orig.le.obj_bytes(1)
    ext = {_rel(d1, c) for c in s['sq'] + [s['mk']]}
    assert len(ext) == 1 and orig.target(2, s['sc'] + 1) == (1, min(ext)), ('the 4 calls: one ExtractSurname', ext)
    for c in s['sq'] + [s['mk']]:                   # (nobody else hooked them: still the plain calls)
        assert bytes(p.get(1, c, 5)) == bytes(d1[c:c + 5]) and not p.rel_target(1, c + 1), ('namefit: site taken', hex(c))
    assert p.target(2, s['sc'] + 1) == (1, min(ext)), ('namefit: scorers site taken', p.target(2, s['sc'] + 1))
    rg = s['regs']
    sym = dict(REGS=(2, rg['D0']))
    sym.update(EXTRACT=(1, ext.pop()), GTW=(1, mv['textw']), SMALL=mv['small'])
    src = f'%define RING_ {RING}\n%define BUF_ {BUF}\n' + ASM
    at, end = swreg.NAMEFIT_AT, swreg.NAMEFIT_END
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert p.le.obj(4).npages * 0x1000 >= end, 'namefit: obj4 pages (patch.py)'
    assert at + len(code) <= end, ('namefit: past its obj4 room', hex(at + len(code)), hex(end))
    assert not any(p.get(4, at, end - at)), 'namefit: obj4 room not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    for c in s['sq']:
        p.branch(1, c, 0xE8, 4, lab['nf_sq'])
    p.branch(1, s['mk'], 0xE8, 4, lab['nf_mk'])
    p.branch(2, s['sc'], 0xE8, 4, lab['nf_sc'])
    print(f'exe: names-fit (menu names by pixels): obj4+{at:#x} ({len(code)} B, {len(fix)} + {len(rel)} fixups), '
          f'sites obj1 {[hex(c) for c in s["sq"] + [s["mk"]]]}, obj2 {s["sc"]:#x}')
    return lab


def ring_off(label='nf_bufs'):
    """obj4 offset of the ring buffers (nf_bufs; the harness tells the cut rows by their text pointer) or of another
    label (nf_name: the last call's name pointer = the last drawn row's player record)."""
    import swreg
    src = f'%define RING_ {RING}\n%define BUF_ {BUF}\n' + ASM
    sym = dict(REGS=(2, 0), EXTRACT=(1, 0), GTW=(1, 0), SMALL=(2, 0))
    return nasmcave.labels(src, swreg.NAMEFIT_AT, sym)[label]


def model(name, room, mode, width, game_cut):
    """The text nf_go leaves for `name` (Python, the asm's order): None = the game's own text (not cut, or nothing
    fits). width(text) = GetTextWidth; game_cut = the game's ExtractSurname cut it (the trigger)."""
    if not game_cut:
        return None
    fits = lambda t: width(t) - 1 <= room
    cpy = lambda t: t[:BUF - 1].rstrip(' ')
    s = name.lstrip(' ')
    first = s
    k = 0
    while k < len(s) and s[k] != ' ':
        k += 1
    rest = s[k:].lstrip(' ')
    inif = lambda: cpy(first[:1] + '. ' + rest)
    def cut(c):
        n = len(c)
        while n >= 2:
            c2 = c[:n - 1] + '.'
            if fits(c2):
                return c2
            n -= 1
        return None
    if mode:
        c = cpy(first)
        if fits(c):
            return c
    if not rest:
        c = cpy(first)
        return c if fits(c) else cut(c)
    c = inif()
    if fits(c):
        return c
    t = rest
    while True:
        c = cpy(t)
        if fits(c):
            return c
        j = t.find(' ')
        if j < 0:
            break
        t = t[j:].lstrip(' ')
        if not t:
            break
    return cut(inif())
