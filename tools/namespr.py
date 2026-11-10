"""4.0.5 (Marco): in-match player names up to 14 characters (ROBERTO_CARLOS, LUIS_ENRIQUE).

The match draws a player's name (the strip over the pitch, the goal / booking blink: SetCurrentPlayerName) as one of
the 32 name sprites 255..286, made once per match by MakeSpritesFromPlayerNames -> MakePlayerNameSprite: the number,
a space, then ExtractSurname(D0 = 400Bh: the surname only, 11 characters at most - a longer one cut with a dot,
'ROBERTO CA.') into numberBuffer (15 bytes), Text2Sprite into the sprite. The sprites come from SCORE.DAT, 80 x 6
pixels (5 quads), and Text2Sprite draws nothing at all when the text is wider than the sprite. So:
- 400Bh -> 400Eh (14 characters, as PlayerInfo.shortName: InitInGamePlayer's 800Eh, a 15-byte field; '_' stays the
  joiner - Text2Sprite draws it as a space, ExtractSurname keeps it inside the 'surname');
- numberBuffer -> NS_NUM (24 bytes: 'NN ' + 14 + 0) in our page, its two references retargeted;
- the call of MakeSpritesFromPlayerNames in ConvertColorsAndTextSprites -> ns_make: every match (after
  LoadSpritesAndFixOffsets) spritesIndex[255..286] point at 32 sprites of ours, 112 x 6 (7 quads): each header the
  game's own (copied the first time: flags, ordinal, centre; nlines 6), sprData our 336 bytes, pixWidth 112, wquads 7.
  Re-done every match: LoadSpritesAndFixOffsets adds dosMemLinAdr to the sprData of 227..340 again (spriteFixupFlag
  -1), ours included - and ChainFont(227) right after it converts those sprites in place, so from the 2nd match of a
  program run it rewrote 32 x DATA bytes at our pixels + dosMemLinAdr (obj2 0x81C0.. on 4.0.5, 0xA1C0.. on 4.1: the
  country tables, careerFileBuffer, a 1996-97 career's team records; 4.1 ISCHIA / CHIEVO). So that call -> ns_fix:
  the game's routine, then our 32 sprData back on our pixels before ChainFont (idempotent; the first match as before).
  Half / EGA mode: the game leaves 255..286 chained (UnchainSprites 227..254 and 287..306), so the
  names are drawn as they are in both modes.
Code, headers and pixels live in obj1 pages of their own (PAGES; obj2's page count unchanged, nothing saved), sized
for CAP sprites (26 per team) although the game has 32 (N).
The tail past CAP x DATA (p6 + Integratore): ns_at+0x4A40..+0x4EF9 the shaved art (blond.art_patch, 4.0.5); the rest
(ns_at+0x4EF9..+0x4FFF, 263 B) was free; 4.1 long_patch takes its top 0x80 (ns_at+0x4F80..), 135 B left. More room for
namespr = a new page.
4.1 (Marco, RUUD VAN NISTELROOY showed 'VAN NISTEL.'): InitInGamePlayer makes PlayerInfo.shortName with
ExtractSurname 800Eh, the initial + everything past the first word, 14 at most ('R. VAN NISTEL.'), and the sprite's
400Eh then drops its first word. long_patch, at the top of that free tail:
- InitInGamePlayer's call -> nl_init: when the initial + surname was cut (ExtractSurname leaves D6 = 14 only then) but
  the surname alone fits (400Eh not cut), shortName = the surname whole ('VAN NISTELROOY'); else the game's cut.
- MakePlayerNameSprite's call -> nl_spr: a short name without the initial ('X. ', GoalScored's own test) is used whole
  (D0 = 0Eh, no flags: returned as it is, 14 at most); with it, the surname as before. One-word names ('_' joins:
  ROBERTO_CARLOS) are unchanged: no initial either way. GoalScored's scorer line and the bench menu read shortName too
  (both: the initial skipped / shown as it is) - they show the whole surname as well.

Fixed counts a bigger bench would touch (the game's, unchanged here): MakeSpritesFromPlayerNames `mov word [D6], 255`
(the first sprite) and `mov word [D7], 15` twice (16 players per team); SetCurrentPlayerName's `add D1, 255` /
`add D1, 271` (the two teams' bases); plNamesLengthTable (32 bytes, obj2) and plOrdinalsTable (32); sprites 287..
are the big digits, so more than 32 name sprites need indices of their own (as shirtnum's 1335..). Ours: N and CAP
here, ns_make's loop (N_), numberBuffer one 24-byte buffer (per call, not per player).
"""
import re
import struct

import nasmcave
import sacups

PAGES = 5
FIRST, N = 255, 32                     # the game's name sprites: 255..270 the top team's 16, 271..286 the bottom's
CAP = 52                               # room for 26 per team (the bench study, 'SWOS Panchina': internal/panchina/fase1.md)
QUADS, LINES = 7, 6
DATA = QUADS * 8 * LINES               # 336 bytes of pixels per sprite

ASM = r"""
ns_make:                                ; replaces `call MakeSpritesFromPlayerNames` (ConvertColorsAndTextSprites)
    pushad
    xor ecx, ecx
.l: mov esi, [SPRIDX + FIRST_ * 4 + ecx * 4]
    imul edi, ecx, 24
    add edi, NS_HDR
    cmp esi, edi
    je .own                             ; (ours since an earlier match)
    push ecx
    push edi
    mov ecx, 24
    rep movsb                           ; the game's header: flags, ordinal, centre, nlines
    pop edi
    pop ecx
.own:
    imul eax, ecx, DATA_
    add eax, NS_DATA
    mov [edi], eax                      ; sprData
    mov word [edi + 10], QUADS_ * 16    ; pixWidth
    mov word [edi + 12], LINES_         ; nlines
    mov word [edi + 14], QUADS_         ; wquads
    mov [SPRIDX + FIRST_ * 4 + ecx * 4], edi
    inc ecx
    cmp ecx, N_
    jb .l
    popad
    jmp MAKESPR

ns_fix:                                 ; replaces `call LoadSpritesAndFixOffsets` (ConvertColorsAndTextSprites)
    call LOADSPR                        ; (its spriteFixupFlag -1 pass adds dosMemLinAdr to the sprData of 227..340
    pushad                              ;  again - ours too, once spritesIndex points at them: ChainFont would then
    xor ecx, ecx                        ;  convert 32 x DATA_ bytes in place at our pixels + dosMemLinAdr = obj2
.f: imul edi, ecx, 24                   ;  0x81C0.. / 0xA1C0.. - the docstring)
    add edi, NS_HDR
    cmp [SPRIDX + FIRST_ * 4 + ecx * 4], edi
    jne .n                              ; (the game's own header: fixed up once, right)
    imul eax, ecx, DATA_
    add eax, NS_DATA
    mov [edi], eax                      ; sprData back on our pixels before ChainFont (ns_make sets the same)
.n: inc ecx
    cmp ecx, N_
    jb .f
    popad
    ret
"""


LONG_ASM = r"""
nl_init:                                ; replaces InitInGamePlayer's `call ExtractSurname` (D0 = 800Eh, A0 -> name)
    mov eax, [A0]
    push eax
    call EXTRACT1                       ; the game's: initial + surname, 14 at most
    pop eax
    cmp word [D6], 14
    jne .out                            ; (not cut)
    mov esi, [A0]
    cmp word [esi + 1], 202Eh
    jne .out                            ; (no initial: one word, cut)
    push eax
    mov [A0], eax
    mov word [D0], 400Eh
    call EXTRACT1                       ; the surname alone
    pop eax
    cmp word [D6], 14
    jne .out                            ; (fits whole)
    mov [A0], eax
    mov word [D0], 800Eh
    jmp EXTRACT1                        ; longer than 14 too: the game's cut
.out:
    ret

nl_spr:                                 ; replaces MakePlayerNameSprite's `call ExtractSurname` (A0 -> shortName)
    mov esi, [A0]
    cmp word [esi + 1], 202Eh
    je EXTRACT2                         ; 'X. ...': the surname (D0 400Eh)
    mov word [D0], 0Eh                  ; no initial: the short name whole
    jmp EXTRACT2
"""
LONG_SIZE = 0x80


def long_sites(p):
    """(InitInGamePlayer's call ExtractSurname, MakePlayerNameSprite's): obj1 offsets in the original exe."""
    d1 = p.le.obj_bytes(1)
    D0 = sacups.regs(d1)['D7'] - 28
    m = [x.start() + 45 for x in re.finditer(rb'\x66\xc7\x05' + re.escape(struct.pack('<I', D0)) + rb'\x0e\x80(?:\xff\x35....){6}'
                                              rb'\xe8', d1, re.S)]
    assert len(m) == 1, ('InitInGamePlayer 800Eh', m)
    lim = [x.start() for x in re.finditer(rb'\x66\xc7\x05' + re.escape(struct.pack('<I', D0)) + rb'\x0b\x40', d1)]
    assert len(lim) == 1, ('400Bh', lim)                  # (MakePlayerNameSprite's, as find(): obj_bytes = the original)
    lim = lim[0]
    c = [x.end() - 1 + lim for x in re.finditer(rb'(?:\xff\x35....){7}\xe8', d1[lim:lim + 0x60], re.S)]
    assert len(c) == 1 and _rel(d1, c[0]) == _rel(d1, m[0]), ('MakePlayerNameSprite ExtractSurname', c)
    return m[0], c[0]


def long_patch(p, end):
    """4.1 whole surnames up to 14 (VAN NISTELROOY): code at the top of namespr's free tail (end = ns_at + PAGES pages,
    after blond.art_patch). Both calls chained (their current targets)."""
    d1 = p.le.obj_bytes(1)
    ini, spr = long_sites(p)
    tgt = {}
    for k, o in (('EXTRACT1', ini), ('EXTRACT2', spr)):
        cur = bytes(p.get(1, o, 5))
        assert cur[0] == 0xE8
        tgt[k] = (1, _rel(cur, 0) + o)
    r = sacups.regs(d1)
    at = end - LONG_SIZE
    sym = dict(tgt, A0=(2, r['A0']), D0=(2, r['D7'] - 28), D6=(2, r['D7'] - 4))
    code, fix = nasmcave.assemble(LONG_ASM, at, sym)
    lab = nasmcave.labels(LONG_ASM, at, sym)
    assert len(code) <= LONG_SIZE and not any(p.get(1, at, LONG_SIZE)), (len(code), hex(at))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for o, l in ((ini, 'nl_init'), (spr, 'nl_spr')):
        p.put(1, o, b'\xE8' + struct.pack('<i', lab[l] - (o + 5)))
    print(f'exe: whole surnames up to 14 in the match: code obj1+{at:#x} ({len(code)} B, {len(fix)} fixups)')
    return at


def _rel(d, c):
    return c + 5 + struct.unpack_from('<i', d, c + 1)[0]


def fix_site(p):
    """ConvertColorsAndTextSprites' `call LoadSpritesAndFixOffsets` (right before `mov D0, 227; call ChainFont`): obj1
    offset in the original exe."""
    d1 = p.le.obj_bytes(1)
    D0 = sacups.regs(d1)['D7'] - 28
    m = [x.start() for x in re.finditer(rb'\xe8....\xc7\x05' + re.escape(struct.pack('<I', D0)) + rb'\xe3\x00\x00\x00\xe8',
                                        d1, re.S)]
    assert len(m) == 1, ('call LoadSpritesAndFixOffsets', m)
    return m[0]


def make_sites(p):
    """(MakeSpritesFromPlayerNames, its call in ConvertColorsAndTextSprites): obj1 offsets in the original exe."""
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    P = lambda a: re.escape(struct.pack('<I', a))
    # MakeSpritesFromPlayerNames: mov [A4], offset plNamesLengthTable; mov word [D6], 255; mov word [D7], 15
    ms = [m.start() for m in re.finditer(rb'\xc7\x05' + P(r['A0'] + 16) + rb'....\x66\xc7\x05' + P(D0 + 24) + rb'\xff\x00'
                                        rb'\x66\xc7\x05' + P(D0 + 28) + rb'\x0f\x00', d1, re.S)]
    assert len(ms) == 1, ('MakeSpritesFromPlayerNames', ms)
    calls = [c for c in range(len(d1) - 5) if d1[c] == 0xE8 and _rel(d1, c) == ms[0]]
    assert len(calls) == 1, ('its call', calls)
    return ms[0], calls[0]


def find(p):
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    A0 = r['A0']
    P = lambda a: re.escape(struct.pack('<I', a))
    make, call = make_sites(p)
    # MakePlayerNameSprite: mov word [D0], 400Bh (the surname, 11 characters)
    lim = [m.start() for m in re.finditer(rb'\x66\xc7\x05' + P(D0) + rb'\x0b\x40', d1)]
    assert len(lim) == 1, ('400Bh', lim)
    # numberBuffer: mov [A1], offset numberBuffer (the routine's head), then every reference to it
    nb = [m.start() for m in re.finditer(rb'\xc7\x05' + P(A0 + 4) + rb'....\xe8', d1[lim[0] - 0x140:lim[0]], re.S)]
    assert nb, 'numberBuffer'
    numbuf = p.target(1, lim[0] - 0x140 + nb[-1] + 6)
    refs = [o for so, o, t, to, tt, *_ in p.le.fixups() if so == 1 and (to, tt) == numbuf]
    assert len(refs) == 2, ('numberBuffer refs', refs)
    import shirtnum
    return dict(make=make, call=call, lim=lim[0] + 7, numbuf=numbuf, refs=refs, spridx=shirtnum.spr_index(p))


def layout(at):
    """(headers, pixels, numberBuffer) of the pages at obj1:at: CAP 24-byte headers, CAP x DATA bytes (benchx uses
    the spare N..CAP-1 for places 17..26)."""
    hdr = at + 0x100
    return hdr, hdr + ((CAP * 24 + 0xFF) & ~0xFF), at + 0xE0


def patch(p, at, lang):
    """Code + buffers at obj1:at (PAGES pages). Returns the end."""
    s = find(p)
    hdr, data, num = layout(at)
    assert data + CAP * DATA <= at + PAGES * 0x1000
    fs = fix_site(p)
    cur = bytes(p.get(1, fs, 5))                           # (chained: the call's current target, patched or not)
    assert cur[0] == 0xE8
    sym = {'SPRIDX': (2, s['spridx']), 'NS_HDR': (1, hdr), 'NS_DATA': (1, data), 'MAKESPR': (1, s['make']),
           'LOADSPR': (1, _rel(cur, 0) + fs),
           'FIRST_': (0, FIRST), 'N_': (0, N), 'QUADS_': (0, QUADS), 'LINES_': (0, LINES), 'DATA_': (0, DATA)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert len(code) <= 0xE0 and not any(p.get(1, at, PAGES * 0x1000))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.put(1, s['call'], b'\xE8' + struct.pack('<i', lab['ns_make'] - (s['call'] + 5)))
    p.put(1, fs, b'\xE8' + struct.pack('<i', lab['ns_fix'] - (fs + 5)))
    assert p.get(1, s['lim'], 2) == b'\x0b\x40'
    p.put(1, s['lim'], b'\x0e')                           # 400Bh -> 400Eh
    for o in s['refs']:                                    # numberBuffer -> NS_NUM (24 bytes)
        p.retarget(1, o, 1, num)
        p.put(1, o, struct.pack('<I', num))
    print(f'exe: 14-character match names: sprites {FIRST}..{FIRST + N - 1} {QUADS * 16} px at obj1+{data:#x}, '
          f'numberBuffer obj1+{num:#x}, code obj1+{at:#x} ({len(code)} B)')
    return data + CAP * DATA
