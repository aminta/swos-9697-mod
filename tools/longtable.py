"""4.0: league tables of more than 24 clubs (World 2026-27: Argentina's Liga Profesional and the MLS, 30 in one division).

The game's table screen (DIY_leagueTournamentMenu) lays out its groups by DIYLeagueTournamentOnRestore: a group takes
rows x row height + its header (D3); groups shown = min(groups, the free height / D3). A 30-row group does not fit even
once (0 groups: the table sits at the screen's bottom), and DIYLeagueTournament16BeforeDraw then draws all its rows
downwards from there: the rows below line 200 are written past the screen buffer, over the font and the menu sprites
(garbage that stays: Davide, 2026-10-19). Every season end walks the world's tables, so every 2026-27 career was hit.

For a table of ONE group with more than ROWS clubs (display only, nothing in the competition changes):
- lt_d3 (OnRestore's `mov ax, [esi+51h] / mov D3, ax`): the group's height counts ROWS rows;
- lt_d5 (BeforeDraw's `mov D5, 1` before the row loop): the first row shown = currentDiyLine (clamped to clubs - ROWS),
  D7 = its index into the order at +6Dh, D5 = its real place (the zone colours' key), the loop's end = first + ROWS;
- lt_end (the loop's `mov ax, [esi+51h] / cmp D5, ax`): compares with that end;
- lt_down (ScrollDown's `mov ax, dseg_10EEF8 / cmp D0, ax`): in the table view (dseg_11F9E2 = 0) the down arrow goes
  on while currentDiyLine < clubs - ROWS (the up arrow's own test, currentDiyLine > 0, already fits);
- lt_arrows (OnRestore's `mov ax, numDiyResults / cmp D0, ax`, groups = groups shown -> entries 40 / 41 hidden): a
  long table keeps its arrows. (cseg_49F01 sets currentDiyLine back to 0 when the screen is entered again.)
"""
import struct

import nasmcave

ROWS = 24                       # the game's own largest table (mkseason: at most 24 clubs a division without fixtures)
MAX = 30                        # the largest table that scrolls (split.NMAX's 30: Argentina, MLS); mkseason refuses more
LABELS = {}

ASM = """
lt_d3:                                  ; esi = DIY_competitionStart
    mov ax, [esi + 51h]
    cmp word [esi + 4Fh], 1
    jne .s
    cmp ax, ROWS_
    jbe .s
    mov ax, ROWS_
.s: mov [D3], ax
    ret

lt_d5:
    pushad
    mov word [D5], 1
    mov esi, DIY
    movzx eax, word [esi + 51h]
    mov [LT_END], ax
    cmp word [esi + 4Fh], 1
    jne .x
    cmp eax, ROWS_
    jbe .x
    movzx ebx, word [CURLINE]
    sub eax, ROWS_                      ; the last first row
    cmp ebx, eax
    jbe .ok
    mov ebx, eax
.ok:
    lea eax, [ebx * 2]
    mov [D7], ax
    lea eax, [ebx + 1]
    mov [D5], ax
    add ebx, ROWS_
    mov [LT_END], bx
.x: popad
    ret

lt_end:                                 ; flags for the loop's jbe: D5 v the last row shown
    push eax
    mov ax, [LT_END]
    cmp [D5], ax
    pop eax
    ret

lt_down:                                ; flags for ScrollDown's jnb (no scroll when 'not below')
    push eax
    push esi
    mov esi, DIY
    cmp word [MODE], 0                  ; (the table view)
    jne .game
    cmp word [esi + 4Fh], 1
    jne .game
    movzx eax, word [esi + 51h]
    cmp eax, ROWS_
    jbe .game
    sub eax, ROWS_
    cmp [CURLINE], ax                   ; below the last first row: scroll
    jmp .r
.game:
    mov ax, [GROUPS]
    cmp [D0], ax
.r: pop esi
    pop eax
    ret

lt_arrows:                              ; flags for OnRestore's jnz (arrows shown when the groups shown < the groups):
    push eax                            ; a long table's arrows are always shown
    push esi
    mov esi, DIY
    cmp word [esi + 4Fh], 1
    jne .game
    cmp word [esi + 51h], ROWS_
    jbe .game
    or esp, esp                         ; (ZF = 0: shown)
    jmp .r
.game:
    mov ax, [NUMRES]
    cmp [D0], ax
.r: pop esi
    pop eax
    ret

align 2
LT_END: dw 0
"""


def patch(p, at):
    """Code at obj1:at; returns its end."""
    import lp36
    d1 = p.le.obj_bytes(1)
    a0 = lp36._sites(p)['A0']                     # the pseudo registers: Dn = A0 - 32 + 4n
    B = 0x101AC                         # (ref/swos.asm cseg_XXXXX labels = obj1 offset + B)
    h1 = _find(d1, rb'\x66\x8b\x46\x51\x66\xa3', 0x4882A - B, 0x80)          # OnRestore: D3 = rows x height
    h2 = 0x498FA - B - 9                                                    # BeforeDraw: mov D5, 1 / cseg_498FA:
    h3 = _find(d1, rb'\x66\x8b\x46\x51\x66\x39\x05', 0x49B65 - B, 0x400)    # the loop's end
    h4 = _find(d1, rb'\x66\xa1....\x66\x39\x05....\x73', 0x49E7A - B, 0x80)  # ScrollDown: mov ax, groups / cmp D0, ax
    h5 = _find(d1, rb'\x66\x8b\x46\x4f\x66\xa3....\x66\x0b\xc0\x66\xa1....\x66\x39\x05....\x75',
               0x48A13 - B, 0x100) + 13                                     # OnRestore: the arrows (entries 40, 41)
    assert d1[h2:h2 + 3] == b'\x66\xc7\x05' and d1[h2 + 7:h2 + 9] == b'\x01\x00', d1[h2:h2 + 9].hex()
    assert d1[h3 + 11:h3 + 13] == b'\x0f\x86'
    j = h3 + 11
    assert j + 6 + struct.unpack_from('<i', d1, j + 2)[0] == h2 + 9, 'the loop jumps back to cseg_498FA'
    mode = 0x484C4 - B                                                      # OnRestore: mov ax, dseg_11F9E2
    assert d1[mode:mode + 2] == b'\x66\xa1'
    curline = h4 - 25                                                       # ScrollDown: mov ax, currentDiyLine
    assert d1[curline:curline + 2] == b'\x66\xa1', d1[curline:curline + 8].hex()
    d0, d3, d5, d7 = a0 - 32, a0 - 20, a0 - 12, a0 - 4
    assert p.target(1, h2 + 3) == (2, d5) and p.target(1, h3 + 7) == (2, d5) and p.target(1, h1 + 6) == (2, d3)
    assert p.target(1, h4 + 9) == (2, d0) and p.target(1, h5 + 9) == (2, d0)
    sym = {'D0': (2, d0), 'D3': (2, d3), 'D5': (2, d5), 'D7': (2, d7), 'DIY': (2, lp36._sites(p)['DIY']),
           'CURLINE': p.target(1, curline + 2), 'MODE': p.target(1, mode + 2), 'GROUPS': p.target(1, h4 + 2),
           'NUMRES': p.target(1, h5 + 2), 'ROWS_': (0, ROWS)}
    for site, n in ((h1, 10), (h2, 9), (h3, 11), (h4, 13), (h5, 13)):     # (no other hook there: the patched bytes = the original)
        assert bytes(p.get(1, site, n)) == d1[site:site + n], hex(site)
    at = (at + 15) & ~15
    code, cfix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for off, t_obj, t_off in cfix:
        p.add_ptr(1, at + off, t_obj, t_off)

    def hook(site, length, label, fix):
        for f in fix:
            p.remove(1, site + f)
        p.put(1, site, b'\xE8' + struct.pack('<i', lab[label] - (site + 5)) + b'\x90' * (length - 5))
    hook(h1, 10, 'lt_d3', (6,))
    hook(h2, 9, 'lt_d5', (3,))
    hook(h3, 11, 'lt_end', (7,))
    hook(h4, 13, 'lt_down', (2, 9))
    hook(h5, 13, 'lt_arrows', (2, 9))
    LABELS.update(lab)
    print(f'exe: league tables over {ROWS} clubs scroll ({ROWS} rows shown; OnRestore obj1+{h1:#x}, row loop '
          f'obj1+{h2:#x} / {h3:#x}, ScrollDown obj1+{h4:#x}; code obj1+{at:#x}, {len(code)} B)')
    return at + len(code)


def _find(d, pat, start, span):
    import re
    m = [x.start() for x in re.finditer(pat, d, re.S) if start <= x.start() < start + span]
    assert len(m) == 1, (pat, hex(start), m)
    return m[0]
