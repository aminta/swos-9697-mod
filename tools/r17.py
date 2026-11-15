"""4.2 row-17 hint (backlog-42 row 43, Panchina; MC 15/11): "+N" next to row 17 of the own-team lists when the club has more
than 16 places.

The three own-team lists (pre-match screen, SQUADRA, tactics editor) show 17 rows: places 1..11, the reserves, and the box
whose fire scrolls rows 12..17 over the other places (benchx.py). With a squad of 29 the screen shows 16 names and the
box: a player thought his squad was cut to 16 (Alessio 11/11). N = places - 16 = the players not shown by name: "+13".

Hook: each list's row-17 entry is drawn by its box entry's AFTER-DRAW function, whose tail is `jmp DrawMenuItem` (A5 = the
row-17 entry): pre-match PlayMatch30AfterDraw (D0 = 29), SQUADRA Squad45AfterDraw (44), the tactics editor
EditTactics28AfterDraw (27). That jmp becomes `jmp r17_xx` (a self-relative inter-object fixup, obj1 -> obj4): the stub
calls what the jmp went to (the row, as before; read from the patched bytes, so a hook already on it is chained after
- never replaced), then, when N > 0, draws one more MenuEntry of the band's own (a string "+N", left aligned, the font of
the row, no background) with the game's DrawMenuItem, at a fixed x per screen (the row entry is only the name part: the other columns are drawn after it).
Only the own team: the pre-match screen not while VIEW OPPONENT shows (viewingOpponentTeam), SQUADRA only for careerTeam.
Band: swreg R17_AT..R17_END (a release band, floor >= 256 B), code + the entry + a 4-byte string; no other state.
"""
import re
import struct

import nasmcave
import swreg

PM_X = 168                              # (pre-match: right of the row's columns, left of the pitch panel)
ET_X = 122                              # (tactics editor: the list is on the right and its columns cover the row: left of the box, on the pitch's edge)
WIDTH = 24
FLAGS = 0x800F                          # (left aligned, yellow = colour 0Fh as SquadAfterDrawCommon's, the small font)
SQ_X = 305                              # (SQUADRA: right of the value column - its row bar is only the name part; the NAZ / GOL / value columns follow)

ASM = r"""
r17_pm:                                 ; PlayMatch30AfterDraw's tail (the pre-match screen)
    mov esi, [A5]                       ; the row-17 entry (DrawMenuItem may move A5)
    push esi
    call TGT_PM
    pop esi
    cmp word [VOPP], 0                  ; (VIEW OPPONENT: the opponent's list, left as it is)
    jne .x
    movzx eax, word [NPS]
    sub eax, 16
    mov edx, PM_X
    jmp r17_hint
.x: ret

r17_sq:                                 ; Squad45AfterDraw's tail (SQUADRA)
    mov esi, [A5]
    push esi
    call TGT_SQ
    pop esi
    cmp dword [SQT], CT                 ; (the career club's squad only)
    jne .x
    movzx eax, word [CNP]
    sub eax, 16
    mov edx, SQ_X
    jmp r17_hint
.x: ret

r17_et:                                 ; EditTactics28AfterDraw's tail (the tactics editor)
    mov esi, [A5]
    push esi
    call TGT_ET
    pop esi
    movzx eax, word [ETNP]
    sub eax, 16
    mov edx, ET_X
    jmp r17_hint
.x: ret

r17_hint:                               ; esi = the row-17 entry, eax = N (<= 0: nothing), edx = the hint's x
    cmp eax, 1
    jl .x
    cmp eax, 99
    jle .ok
    mov eax, 99
.ok:
    pushad                              ; (edx = x survives: pushad keeps it; the digits use edx below, so x is saved first)
    push edx
    mov edi, R17_S
    mov byte [edi], '+'
    cmp eax, 10
    jb .one
    xor edx, edx
    mov ecx, 10
    div ecx
    add al, '0'
    mov [edi + 1], al
    mov eax, edx
    add al, '0'
    mov [edi + 2], al
    mov byte [edi + 3], 0
    jmp .set
.one:
    add al, '0'
    mov [edi + 1], al
    mov byte [edi + 2], 0
.set:
    mov ebx, R17_E
    pop ecx
    mov [ebx + 14h], cx
    mov ax, [esi + 16h]                 ; y, height
    mov [ebx + 16h], ax
    mov ax, [esi + 1Ah]
    mov [ebx + 1Ah], ax
    mov word [ebx + 18h], HINT_W
    mov word [ebx + 24h], HINT_FLAGS
    push dword [A5]
    mov [A5], ebx
    call DMI
    pop dword [A5]
    popad
.x: ret

R17_E:                                  ; the hint's MenuEntry (0x38 B): string, no background
    dw 0, 0, 0, 0                       ; alreadyDrawn, ordinal, isInvisible, isDisabled
    times 12 db 0                       ; left..skip entries
    dw 0, 0, 0, 0                       ; x, y, width, height (set per draw)
    dw 0                                ; background: none
    dd 0                                ; bg union
    dw 2                                ; content: ENTRY_STRING
    dw 0                                ; stringFlags (set per draw)
    dd R17_S                            ; fg.string
    dd 0                                ; onSelect
    dw 0                                ; controlMask
    dd 0, 0                             ; beforeDraw, afterDraw
R17_S:
    db 0, 0, 0, 0
R17_END_:
"""

SITES = (('pm', 29), ('sq', 44), ('et', 27))


def sites(p):
    """The three tail jmps (obj1 offsets): by the shape of the after-draw functions - mov eax,[A0] / xchg [A5],eax /
    mov [A0],eax / push [D0] / mov dword [D0], box-1 / call CalcMenuEntryAddress / pop [D0] / the same swap back / jmp
    DrawMenuItem (found in the original bytes, read again in the patched ones by patch())."""
    import sacups
    d = p.le.obj_bytes(1)
    regs = sacups.regs(d)
    a0, d0 = regs['A0'], regs['D7'] - 28
    a5 = a0 + 20
    pk = lambda x: re.escape(struct.pack('<I', x))
    swap = rb'\xa1' + pk(a0) + rb'\x87\x05' + pk(a5) + rb'\xa3' + pk(a0)
    pat = (swap + rb'\xff\x35' + pk(d0) + rb'\xc7\x05' + pk(d0) + rb'(....)\xe8....\x8f\x05' + pk(d0) + swap + rb'\xe9(....)')
    out = {}
    for m in re.finditer(pat, d, re.S):
        n = struct.unpack('<I', m.group(1))[0]
        for k, box1 in SITES:
            if n == box1:
                assert k not in out, ('r17: two after-draw tails for', k)
                out[k] = (m.end() - 5, m.end() - 5 + 5 + struct.unpack('<i', m.group(2))[0])
    assert set(out) == {k for k, _ in SITES}, ('r17: after-draw tails', sorted(out))
    assert len({t for _, t in out.values()}) == 1, ('r17: one DrawMenuItem', {k: hex(t) for k, (_, t) in out.items()})
    return {'jmp': {k: j for k, (j, _) in out.items()}, 'DMI': next(iter(out.values()))[1], 'A5': a5}


def patch(p):
    """After benchx (its sym: the counts). Returns the band's end."""
    import benchx
    sy = benchx.INFO['SYM']
    s = sites(p)
    at = swreg.R17_AT
    jmps = s['jmp']
    tg = {}
    for k, j in jmps.items():                           # (a chained hook: its target; the original: DrawMenuItem)
        assert p.get(1, j, 1) == b'\xe9', ('r17: the tail of the', k, 'AfterDraw is not a jmp any more', p.get(1, j, 5).hex())
        tg[k] = p.call_target(1, j)
    sym = {'A5': (2, s['A5']), 'DMI': (1, s['DMI']), 'NPS': sy['NPS'], 'ETNP': sy['ETNP'], 'CNP': sy['CNP'], 'CT': sy['CT'],
           'VOPP': sy['VOPP'], 'SQT': (sy['SQCNT'][0], sy['SQCNT'][1] + 2),
           'TGT_PM': tg['pm'], 'TGT_SQ': tg['sq'], 'TGT_ET': tg['et'],
           'HINT_W': (0, WIDTH), 'HINT_FLAGS': (0, FLAGS), 'SQ_X': (0, SQ_X), 'PM_X': (0, PM_X), 'ET_X': (0, ET_X)}
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 4)
    lab = nasmcave.labels(ASM, at, sym)
    end = at + len(code)
    assert end <= swreg.R17_END - 256, ('r17: band floor (>= 256 B left)', hex(end))
    assert p.le.obj(4).npages * 0x1000 >= swreg.R17_END, 'r17: obj4 pages (patch.py R17 line)'
    assert not any(p.get(4, at, swreg.R17_END - at)), 'r17: band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    for k, j in jmps.items():
        p.branch(1, j, 0xE9, 4, lab['r17_' + k])
        assert p.rel_target(1, j + 1) == (4, lab['r17_' + k]), ('r17: fixup of the', k, 'jmp')
    LABELS.clear()
    LABELS.update(lab)
    print(f'exe: row-17 hint (r17): obj4+{at:#x}..{end:#x} ({len(code)} B, {swreg.R17_END - end} B of the band left), '
          f'tails obj1+' + ', '.join(f'{k} {j:#x}' for k, j in jmps.items()) + f' (DrawMenuItem obj1+{s["DMI"]:#x}; chained: '
          + (', '.join(k for k, t in tg.items() if t != (1, s['DMI'])) or 'none') + ')')
    return end


LABELS = {}
