"""4.1 RC3 (Enzo 09/11; Davide via Regia: option A + per world): money in euros in the worlds where the euro existed.

The game prints money through one conversion routine with exactly two callers: Int2Pounds (the amounts with commas)
and cseg_24AB6 (the short K / M form: market lists, squads). In ENGLISH.EXE that routine is a bare `ret` and the
currency is the glyph of character 9Ch (sprites 46 small / 103 big of CHARSET.DAT, the same in the four exes' font
tables). The other exes print their own currency text and convert: IT 'L' + 'M' / 'MN' / 'MD' x 2 (lire), FR 'FF'
x 10, DE 'DM' x 2 - the strings next to each other in obj2 (pound, nullString, the three short formats).

Here, in a euro world (EUWORLDS: the registered worlds whose season starts in 2002 or later - World 2026-27; the
current one is careerworld's namespace byte WCUR), every exe shows the English output with the euro sign: no
conversion, 9Ch + the English suffixes in place of the language's strings (same fields, same offsets), sprites 46 /
103 holding the euro letter. In any other world (1996-97, Europe 1984-85, Italy 1947-48, the custom teams) the game's
own output, byte for byte: the strings and the pound glyph put back, the conversion run.
- both callers' `call conv` -> eu_money (mode check, then the conversion or none);
- ChainFont (the charset's in-place unchain after every load: the game's start, back from a match, the highlights) ->
  eu_chain: after it, the converted pound pixels of sprites 46 / 103 kept, and the euro template (EURO below, in
  CHARSET.DAT's raw planes) converted by the same UnchainSpriteInMenus, so every video mode gets its own bytes; the
  font holds the pound again (GMODE 0).
CHARSET.DAT is read as it is (no new file). Code in obj1 after lgreal (gplay's free tail: a build with worlds - one
without has no euro world and stays the original). Saves: no change. Amounts in the data: unchanged (2026-27's come
from TM values, in euros).
Left alone: the IT exe's amount list '\\xa325m*' .. '\\xa315M*' (the EN a25k.. strings, there with 9Ch) writes A3h, a
character the fonts do not have (the crossed box), but nothing references it (no XREF in ref/swos.asm): never drawn.
"""
import re
import struct

import nasmcave

SPRITES = {46: ('.2222',                 # small font: 5 x 5 + the shadow (6 x 6, as the pound sign)
                '222..',
                '2....',
                '222..',
                '.2222'),
           103: ('..22222',              # big font: 7 x 7 + the shadow (8 x 8), two-pixel strokes as its letters
                 '.22....',
                 '222222.',
                 '22.....',
                 '222222.',
                 '.22....',
                 '..22222')}
SIZE = {46: (6, 6, 1), 103: (8, 8, 1)}   # (width, lines, quads a line) of the pound sprites
FIRST_EURO_YEAR = 2002
LABELS = {}


def glyph(rows, w, nl):
    """[nl][w] colours: the letter (2) and its shadow (8) one pixel down-right where the letter is not."""
    px = [[0] * w for _ in range(nl)]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '2':
                px[y][x] = 2
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == '2' and y + 1 < nl and x + 1 < w and px[y + 1][x + 1] != 2:
                px[y + 1][x + 1] = 8
    return px


def planes(px, wq):
    """A sprite's lines as CHARSET.DAT stores them: per line and quad, 4 big-endian 16-bit planes."""
    out = bytearray()
    for row in px:
        for q in range(wq):
            for p in range(4):
                v = 0
                for x in range(16):
                    c = row[16 * q + x] if 16 * q + x < len(row) else 0
                    v |= ((c >> p) & 1) << (15 - x)
                out += struct.pack('>H', v)
    return bytes(out)


def template(i):
    """Sprite i's euro letter in CHARSET.DAT's raw form."""
    w, nl, wq = SIZE[i]
    return planes(glyph(SPRITES[i], w, nl), wq)


def sprite(cs, sp, i):
    """(pixel data offset, width, lines, quads a line) of CHARSET sprite i (harness)."""
    h = struct.unpack_from('<I', sp, 4 * i)[0]
    pd = struct.unpack_from('<I', cs, h)[0]
    w, nl, wq = struct.unpack_from('<hhh', cs, h + 10)
    return pd, w, nl, wq


def letter(cs, sp, i):
    """Sprite i's letter pixels (colour 2) as rows of bools, the shadow column / row left out (harness: euro_money)."""
    pd, w, nl, wq = sprite(cs, sp, i)
    return [[((sum(((struct.unpack_from('>H', cs, pd + (y * wq + x // 16) * 8 + 2 * p)[0] >> (15 - x % 16)) & 1) << p
                   for p in range(4))) == 2) for x in range(w - 1)] for y in range(nl - 1)]


def euro_letter(i):
    """The euro letter (colour 2) as rows of bools, as letter() reads a sprite."""
    w, nl, _ = SIZE[i]
    return [[c == 2 for c in r[:w - 1]] for r in glyph(SPRITES[i], w, nl)[:nl - 1]]


ASM = r"""
eu_money:                               ; both `call conv` (Int2Pounds, cseg_24AB6): D0 = the amount
    pushad
    movzx eax, byte [WCUR]
    bt [EUBM], eax                      ; CF: a euro world
    setc bl
    cmp bl, [SMODE]
    je .g
    mov [SMODE], bl                     ; the currency strings: euro or the language's own
%if STRLEN_
    mov esi, ORSTR
    test bl, bl
    jz .s
    mov esi, EUSTR
.s: mov edi, STR
    mov ecx, STRLEN_
    rep movsb
%endif
.g: cmp bl, [GMODE]
    je .d
    mov [GMODE], bl                     ; the glyphs: euro or pound pixels into sprites 46 / 103
    mov edx, [SGP]
    mov esi, BUF46P
    test bl, bl
    jz .g1
    mov esi, BUF46E
.g1:mov eax, [edx + 46 * 4]
    mov edi, [eax]
    mov ecx, N46_
    rep movsb
    mov esi, BUF103P
    test bl, bl
    jz .g2
    mov esi, BUF103E
.g2:mov eax, [edx + 103 * 4]
    mov edi, [eax]
    mov ecx, N103_
    rep movsb
.d: popad
    cmp byte [SMODE], 0
    jne .r
    jmp CONV                            ; (the language's conversion; its ret returns to the caller)
.r: ret

eu_chain:                               ; ChainFont's `shl D0, 2` (D0 = the first sprite: 0 = the charset)
    push dword [D0]
    shl dword [D0], 2
    call CFLOOP                         ; (ChainFont's loop; its retn comes back here)
    pop eax
    test eax, eax
    jnz .r
    pushad
    mov edx, [SGP]
    mov eax, [edx + 46 * 4]             ; the pound pixels as converted
    mov esi, [eax]
    mov edi, BUF46P
    mov ecx, N46_
    rep movsb
    mov eax, [edx + 103 * 4]
    mov esi, [eax]
    mov edi, BUF103P
    mov ecx, N103_
    rep movsb
    mov esi, T46                        ; the euro: the raw template, converted in place as the charset was
    mov edi, BUF46E
    mov ecx, N46_
    rep movsb
    mov esi, T103
    mov edi, BUF103E
    mov ecx, N103_
    rep movsb
    mov word [D0], Q46_
    mov word [D1], L46_
    mov dword [A0], BUF46E
    call UNCHAIN
    mov word [D0], Q103_
    mov word [D1], L103_
    mov dword [A0], BUF103E
    call UNCHAIN
    mov byte [GMODE], 0                 ; (the font holds the pound again; texts already formatted in a euro world
    cmp byte [SMODE], 0                 ;  keep their euro: back from a match the menus are not all formatted again)
    je .p
    mov byte [GMODE], 1
    mov eax, [edx + 46 * 4]
    mov edi, [eax]
    mov esi, BUF46E
    mov ecx, N46_
    rep movsb
    mov eax, [edx + 103 * 4]
    mov edi, [eax]
    mov esi, BUF103E
    mov ecx, N103_
    rep movsb
.p: popad
.r: ret

align 4
EUBM: times 32 db 0                     ; the euro worlds (bits by WCUR's value)
SMODE: db 0
GMODE: db 0
align 4
T46: times N46_ db 0
T103: times N103_ db 0
BUF46P: times N46_ db 0
BUF103P: times N103_ db 0
BUF46E: times N46_ db 0
BUF103E: times N103_ db 0
ORSTR: times STRLEN_ db 0
EUSTR: times STRLEN_ db 0
"""

# the currency block in obj2: pound, nullString, then the short formats '%1' thousands, '%0' millions, '%0.%1' millions
BLOCK = re.compile(rb'([^\0]{1,2})\0([^\0]?)\0\1%1([^\0]*)\0\1%0([^\0]*)\0\1%0\.%1([^\0]*)\0')


def block(d2):
    """(obj2 offset, original bytes, euro bytes) of the currency strings: every field keeps its offset and length."""
    m = [x for x in BLOCK.finditer(d2)]
    assert len(m) == 1, ('the currency strings', len(m))
    m = m[0]
    cur, null = m.group(1), m.group(2)
    if cur == b'\x9c' and not null:
        return m.start(), m.group(0), m.group(0)       # (ENGLISH: the same strings, the glyph only)
    new = [b'\x9c', b'', b'\x9c%1K', b'\x9c%0M', b'\x9c%0.%1M']
    old = [cur, null, cur + b'%1' + m.group(3), cur + b'%0' + m.group(4), cur + b'%0.%1' + m.group(5)]
    out = b''
    for n, o in zip(new, old):
        assert len(n) <= len(o), (n, o)
        out += n + bytes(len(o) - len(n) + 1)
    assert len(out) == len(m.group(0))
    return m.start(), m.group(0), out


def sites(p):
    """The conversion routine and its two callers, ChainFont (its `shl D0, 2`, loop, unchain call, D0 / D1 / A0,
    the sprites index pointer), the currency strings."""
    d1, d2 = bytes(p.le.obj_bytes(1)), bytes(p.le.obj_bytes(2))
    at, orig, eu = block(d2)
    rel = lambda o: o + 5 + struct.unpack_from('<i', d1, o + 1)[0]

    def tg(o):
        try:
            return p.target(1, o)
        except AssertionError:
            return None
    # Int2Pounds: call conv; mov A0, offset pound
    m = [x.start() for x in re.finditer(rb'\xe8....\xc7\x05', d1, re.S) if tg(x.start() + 11) == (2, at)]
    assert len(m) == 1, ('Int2Pounds', m)
    conv = rel(m[0])
    calls = [o for o in range(len(d1) - 5) if d1[o] == 0xE8 and rel(o) == conv]
    assert len(calls) == 2 and m[0] in calls, ('the conversion routine\'s callers', [hex(c) for c in calls])
    for o in calls:                                     # (nothing hooked them before: p.get = the original)
        assert bytes(p.get(1, o, 5)) == d1[o:o + 5], ('euro: a caller already patched', hex(o))
    # ChainFont: shl D0, 2 / mov esi, [g_spriteGraphicsPtr] / add esi, [D0] / mov eax, [esi] / or eax, eax / jz
    c = [x.start() for x in re.finditer(rb'\xc1\x25(....)\x02\x8b\x35....\x03\x35\1\x8b\x06\x0b\xc0\x74', d1, re.S)]
    ncall = lambda f: sum(1 for o in range(len(d1) - 5) if d1[o] == 0xE8 and rel(o) == f)
    c = [f for f in c if ncall(f) == 4]                 # (two more loops of its shape: 0 and 1 callers)
    assert len(c) == 1, ('ChainFont', c)
    cf = c[0]
    assert bytes(p.get(1, cf, 7)) == d1[cf:cf + 7], 'euro: ChainFont already patched'
    # its body: ... mov word [D1], ax ... call UnchainSpriteInMenus (after push cx = 66 51)
    u = re.search(rb'\x66\x51\xe8', d1[cf:cf + 0x60])
    assert u, 'ChainFont: the unchain call'
    a0 = re.search(rb'\xa3(....)\x8b\x3d\1', d1[cf:cf + 0x40], re.S)   # (mov A0, eax / mov edi, A0)
    d1w = re.search(rb'\x66\x8b\x47.\x66\xa3', d1[cf:cf + 0x40], re.S)  # (mov ax, [edi+nlines] / mov word [D1], ax)
    assert a0 and d1w, 'ChainFont: A0 / D1'
    return {'conv': conv, 'calls': calls, 'chain': cf, 'STR': (2, at), 'orig': orig, 'euro': eu,
            'D0': p.target(1, cf + 2), 'SGP': p.target(1, cf + 9), 'CFLOOP': (1, cf + 7),
            'UNCHAIN': (1, rel(cf + u.start() + 2)), 'A0': p.target(1, cf + a0.start() + 1),
            'D1': p.target(1, cf + d1w.end())}


def euro_worlds():
    """The registered worlds (mkseason packs' world numbers) whose season starts in FIRST_EURO_YEAR or later."""
    import mkseason
    out = set()
    for pk in mkseason.packs():
        y = re.search(r'(\d{4})-\d{2}', pk.meta.get('id', ''))
        if getattr(pk, 'world', None) and y and int(y.group(1)) >= FIRST_EURO_YEAR:
            out.add(pk.world)
    return out


def patch(p, at, limit, wcur, worlds=None, obj=1):
    """eu_* at obj:at (< limit; 4.2: obj3's last page, after longtable + mainbtn, in a release build); wcur =
    careerworld's WCUR (obj, off). Returns the end."""
    worlds = euro_worlds() if worlds is None else worlds
    s = sites(p)
    slen = len(s['orig']) if s['orig'] != s['euro'] else 0
    sym = {k: s[k] for k in ('STR', 'D0', 'D1', 'A0', 'SGP', 'CFLOOP', 'UNCHAIN')}
    sym.update(CONV=(1, s['conv']), WCUR=wcur, STRLEN_=(0, slen))
    for i in (46, 103):
        w, nl, wq = SIZE[i]
        sym.update({f'N{i}_': (0, nl * wq * 8), f'Q{i}_': (0, wq), f'L{i}_': (0, nl)})
    at = (at + 15) & ~15
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, obj)
    lab = nasmcave.labels(ASM, at, sym)
    assert at + len(code) <= limit, ('euro: no room', obj, hex(at), hex(at + len(code)), hex(limit))
    assert not any(p.get(obj, at, len(code))), (obj, hex(at))
    code = bytearray(code)
    bm = bytearray(32)
    for w in worlds:
        bm[w >> 3] |= 1 << (w & 7)
    for name, data in (('EUBM', bytes(bm)), ('T46', template(46)), ('T103', template(103))) + \
            ((('ORSTR', s['orig']), ('EUSTR', s['euro'])) if slen else ()):
        o = lab[name] - at
        code[o:o + len(data)] = data
    p.put(obj, at, bytes(code))
    for o, t_obj, t_off in fix:
        p.add_ptr(obj, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:                          # (code outside obj1: its rel32s back into obj1)
        p.add_rel(obj, at + o, t_obj, t_off)
    for c in s['calls']:
        p.branch(1, c, 0xE8, obj, lab['eu_money'])
    p.remove(1, s['chain'] + 2)                          # (`shl [D0], 2`: its D0 fixup goes with it)
    p.branch(1, s['chain'], 0xE9, obj, lab['eu_chain'], n=7)
    LABELS.clear()
    LABELS.update({k: (obj, v) for k, v in lab.items()})
    print(f'exe: euro in the worlds {sorted(worlds)} (conversion obj1+{s["conv"]:#x}, callers '
          f'{", ".join(hex(c) for c in s["calls"])}, ChainFont obj1+{s["chain"]:#x}, strings obj2+{s["STR"][1]:#x} '
          f'{len(s["orig"])} B{"" if slen else " (the same)"}), code obj{obj}+{at:#x} ({len(code)} B, {limit - at - len(code)} B left to obj{obj}+{limit:#x})')
    return at + len(code)
