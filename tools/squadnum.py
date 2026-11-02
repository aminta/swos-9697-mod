"""Editable shirt numbers on the club's squad screen (4.0.6, Marco on 4.0.5): the career squad screen (squadMenu: the
club's players with NAZ / GOL / value columns, ESCI / GOL / PRATICA) gets shirtedit's editor as the team screen before
a match has it: LEFT on a player's row lights his number box, UP / DOWN free numbers, digits, a clash swaps, ESC undoes,
the first edit pins the team (benchnum.PIN_BIT). Only for the career club (careerTeam, what the .CAR saves); another
club's squad shown there stays as it is.

squadMenu's rows (entries 28..44, after-draw SquadAfterDrawCommon, LEFT = none as the team screen's rows) draw the
number with DrawPlayerEntries' own block (`mov esi, [A0] / mov word [esi + 4], 1 / ... / mov word [esi + 4], 0`):
- shirtedit's se_ctl `call se_row` -> sq_row: se_row first (the team screen), else a squad screen row 0..15 of
  careerTeam (row 16 draws no number): GetPlayerInfoBreakPosition on the squad's team (dseg_16F486) -> edi = his
  record, ebp = the team (se_row's contract);
- the squad number's `mov word [esi + 4], 0` -> `call se_hl; nop` (the lit box, as the team screen's).
The number column's look (the name bar 2 px right: the shadow and a gap) is numcol.py's.
Code in obj3 after kittrain (CONVENTIONS 23).
"""
import re
import struct

import nasmcave
import shirtedit

ASM = r"""
sq_row:                                 ; se_ctl's `call se_row` (ebx = the selected entry)
    call SE_ROW                         ; the team screen's rows
    jnc .r
    cmp dword [ebx + 34h], SADC         ; a squad screen row (its afterDraw)
    jne .no
    cmp byte [ebx + 8], 0FFh            ; LEFT goes nowhere from it
    jne .no
    mov ebp, [SQT]
    cmp ebp, CT                         ; the career club only
    jne .no
    movzx eax, word [ebx + 2]           ; ordinal: 28.. = rows 0..16 (16: no number)
    sub eax, 28
    jb .no
    cmp eax, 16
    jae .no
    mov [A0], ebp
    mov [D1], ax
    push ebp
    push ebx
    call GPIBP                          ; -> [A0] + 4Ch = his record
    pop ebx
    pop ebp
    mov edi, [A0]
    add edi, 76
    clc
    ret
.no:
    stc
.r:
    ret
"""


def sites(p):
    """SquadAfterDrawCommon, the squad's team pointer and its number entry's `mov word [esi + 4], 0` (original bytes)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    pk = lambda x: re.escape(struct.pack('<I', x))
    d7, d0, d5, a5, a6 = a0 - 4, a0 - 32, a0 - 12, a0 + 20, a0 + 24
    # mov esi,[A5]; mov ax,[esi+2]; mov [D7],ax; sub word [D7],1Ch; mov eax,[dseg_16F486]; mov [A6],eax; cmp word [D7],10h
    m = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(a5) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d7) + rb'\x66\x83\x2d'
                                        + pk(d7) + rb'\x1c\xa1....\xa3' + pk(a6) + rb'\x66\x83\x3d' + pk(d7) + rb'\x10',
                                        d1, re.S)]
    assert len(m) == 1, ('SquadAfterDrawCommon', m)
    sadc = m[0]
    # its number entry (shirtedit's HL_SITE block)
    n = [x.end() - 6 for x in re.finditer(rb'\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x01\x00\x66\xa1' + pk(d5) +
                                          rb'\x66\x0b\xc0\x75.\x66\xc7\x05' + pk(d0) + rb'\x00\x00\x8b\x35' + pk(a6) +
                                          rb'\x8a\x46\x4e\xa2' + pk(d0) + rb'\x66\xa1' + pk(d0) + rb'\x8b\x35' + pk(a0) +
                                          rb'\x66\x89\x46\x26\x8b\x35' + pk(a0) + rb'\x66\xc7\x46\x04\x00\x00',
                                          d1[sadc:sadc + 0x1000], re.S)]
    assert len(n) == 1, ('squad number entry', n)
    return {'SADC': (1, sadc), 'SQT': p.target(1, sadc + 25), 'HL_SITE': sadc + n[0]}


def patch(p, at):
    """sq_row at obj3:at (after kittrain); returns the end. Nothing without shirtedit (no career worlds)."""
    info = shirtedit.INFO
    if 'se_row' not in info:
        return at
    s = sites(p)
    sym = {'SE_ROW': (1, info['se_row']), 'SADC': s['SADC'], 'SQT': s['SQT']}
    sym.update({k: info[k] for k in ('CT', 'A0', 'D1', 'GPIBP')})
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    cs = info['row_call']                               # se_ctl's `call se_row`
    assert p.call_target(1, cs) == (1, info['se_row']), hex(cs)
    p.branch(1, cs, 0xE8, 3, at)
    hl = s['HL_SITE']
    assert p.get(1, hl, 6) == b'\x66\xc7\x46\x04\x00\x00'
    p.put(1, hl, b'\xe8' + struct.pack('<i', info['se_hl'] - (hl + 5)) + b'\x90')
    print(f'exe: squadnum: editable shirt numbers on the squad screen, obj3+{at:#x} ({len(code)} B), '
          f'number obj1+{hl:#x}')
    return at + len(code)
