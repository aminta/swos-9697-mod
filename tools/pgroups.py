"""Parallel groups of one level in a career world (Serie C 2026-27: 3 groups of 20 below Serie B).

The engine knows one chain of divisions per country: at the season end a division's 'promoted' clubs go one division
up and its 'relegated' ones one down, as signed deltas per global club number in leaguesTableCopy (someLeaguesTable
holds the season's own; division = the club record's base division + delta). With the groups as the last divisions
of the chain (pack.json league 'parallel': {upper, first = upper + 1, count}) and their data set to 'promoted' 1 (the
winner) and 'relegated' 0, the game's moves are right but for two things this module fixes in leaguesTableCopy before
InitializeNewSeason copies it back (its `call cseg_7CAA2`, obj1 0x7CB86):
- a group winner below the first group went to the group above it -> the upper division;
- the upper division's relegated clubs all went to the first group -> the group of their area (clubs.csv 'area'),
  else the nearest group with room (each group keeps its size: balancing).
No club leaves the lowest level (Davide: as the original game's lowest English division).
"""
import re
import struct

import nasmcave

ASM = '''
pg_fix:                                 ; replaces `call cseg_7CAA2` (leaguesTableCopy -> someLeaguesTable) in
    pushad                              ; InitializeNewSeason: the running world's tables first
    mov al, [SLT + WORLD_BYTE]
    mov esi, PG_TAB
.t:
    mov cl, [esi]
    test cl, cl
    jz .done
    movzx edx, byte [esi + 3]           ; groups
    movzx ebx, word [esi + 4 + edx]     ; clubs
    cmp cl, al
    jne .n
    pushad
    call pg_one
    popad
.n:
    lea esi, [esi + edx + 6]
    lea esi, [esi + ebx * 4]
    jmp .t
.done:
    popad
    jmp C7CAA2

pg_one:                                 ; esi = a table: db world, upper, first, groups, sizes[groups]; dw clubs;
    mov al, [esi + 1]                   ; clubs x (dw global number, db base division, db area group)
    mov [PG_U], al
    mov al, [esi + 2]
    mov [PG_F], al
    movzx ecx, byte [esi + 3]
    mov [PG_N], cl
    lea eax, [esi + 4]
    mov [PG_SZ], eax
    xor eax, eax
.z:
    mov byte [PG_CNT + eax], 0
    inc eax
    cmp eax, ecx
    jb .z
    movzx ecx, word [esi + 4 + ecx]
    movzx edx, byte [PG_N]
    lea edi, [esi + 6 + edx]
    mov [PG_E], edi
    mov [PG_K], ecx
.p1:                                    ; pass 1: winners up, the clubs staying in a group counted
    call .od                            ; ebx = old division, edx = new, ebp = global, eax = base
    movzx esi, byte [PG_F]
    cmp ebx, esi
    jbe .c1                             ; (old above the groups, or the first group: the chain is right)
    movzx ecx, byte [PG_N]
    add ecx, esi
    cmp ebx, ecx
    jae .c1
    lea ecx, [ebx - 1]
    cmp edx, ecx
    jne .c1
    movzx edx, byte [PG_U]              ; a group winner -> the upper division
    sub edx, eax
    mov [SLTCOPY + ebp], dl
    jmp .n1
.c1:
    movzx esi, byte [PG_U]
    cmp ebx, esi                        ; (relegated from the upper division: pass 2)
    jne .c2
    movzx esi, byte [PG_F]
    cmp edx, esi
    je .n1
.c2:
    movzx esi, byte [PG_F]
    sub edx, esi
    jb .n1
    movzx esi, byte [PG_N]
    cmp edx, esi
    jae .n1
    inc byte [PG_CNT + edx]
.n1:
    add edi, 4
    dec dword [PG_K]
    jnz .p1
    mov edi, [PG_E]                     ; pass 2: the upper division's relegated clubs into their area's group
    movzx esi, byte [PG_N]
    mov ecx, [PG_SZ]
    movzx ecx, word [ecx + esi]
    mov [PG_K], ecx
.p2:
    call .od
    movzx esi, byte [PG_U]
    cmp ebx, esi
    jne .n2
    movzx esi, byte [PG_F]
    cmp edx, esi
    jne .n2
    movzx ecx, byte [edi + 3]           ; its area, then the nearest group with room
    xor ebx, ebx
.g:
    mov edx, ecx
    add edx, ebx
    call .room
    jnc .put
    mov edx, ecx
    sub edx, ebx
    call .room
    jnc .put
    inc ebx
    cmp ebx, 4
    jb .g
    mov edx, ecx                        ; (every group full: its own area's)
.put:
    inc byte [PG_CNT + edx]
    movzx esi, byte [PG_F]
    add edx, esi
    sub edx, eax
    mov [SLTCOPY + ebp], dl
.n2:
    add edi, 4
    dec dword [PG_K]
    jnz .p2
    ret
.od:                                    ; edi = an entry -> ebp = global, eax = base, ebx = old, edx = new division
    movzx ebp, word [edi]
    movzx eax, byte [edi + 2]
    movsx ebx, byte [SLT + ebp]
    add ebx, eax
    movsx edx, byte [SLTCOPY + ebp]
    add edx, eax
    ret
.room:                                  ; edx = a group (any value) -> CF = 0 if it exists and has room
    push esi
    movzx esi, byte [PG_N]
    cmp edx, esi
    jae .no                             ; (negative -> large unsigned)
    mov esi, [PG_SZ]
    push eax
    mov al, [PG_CNT + edx]
    cmp al, [esi + edx]
    pop eax
    jae .no
    pop esi
    clc
    ret
.no:
    pop esi
    stc
    ret

PG_U: db 0
PG_F: db 0
PG_N: db 0
PG_CNT: times 4 db 0
PG_SZ: dd 0
PG_E: dd 0
PG_K: dd 0
PG_TAB: TAB_BYTES
'''


def table_bytes(tables):
    out = bytearray()
    for world, u, f, sizes, clubs in tables:
        out += bytes((world, u, f, len(sizes))) + bytes(sizes) + struct.pack('<H', len(clubs))
        for g, base, area in clubs:
            out += struct.pack('<HBB', g, base, area)
    return bytes(out + b'\0')


def _site(p):
    """The call of cseg_7CAA2 (leaguesTableCopy -> someLeaguesTable) in InitializeNewSeason."""
    import careerworld
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    s = careerworld.SITES                   # (careerworld.patch ran first; its patterns are hooked by now)
    pk = lambda x: re.escape(struct.pack('<I', x))
    slt = struct.pack('<I', s['slt'][1])
    starts = [x.start() - 9 for x in re.finditer(rb'\xc7\x05' + pk(r['A0']) + re.escape(slt) + rb'\xc7\x05' +
                                                 pk(r['A0'] + 4), d1)]
    # the copy back: reads [A1] (leaguesTableCopy) first: mov esi, [A1] right after the three set-ups
    back = [st for st in starts if d1[st + 29:st + 35] == b'\x8b\x35' + struct.pack('<I', r['A0'] + 4)]
    assert len(back) == 1, [hex(x) for x in starts]
    calls = [i for i in range(len(d1) - 5) if d1[i] == 0xe8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == back[0]]
    assert len(calls) == 1, calls
    return calls[0], back[0], s


def patch(p, at, tables):
    """Code + tables at obj1:at; returns the end."""
    import careerworld
    site, c7caa2, s = _site(p)
    assert p.get(1, site, 5) == p.le.obj_bytes(1)[site:site + 5], 'the copy-back call is already hooked'
    sym = {'SLT': s['slt'], 'SLTCOPY': s['sltcopy'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'C7CAA2': (1, c7caa2), 'TAB_BYTES': (0, 'db ' + ', '.join(str(b) for b in table_bytes(tables)))}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', lab['pg_fix'] - (site + 5)))   # (a relative call: no fixup)
    print(f'exe: parallel groups: {len(tables)} countries, copy-back call obj1+{site:#x}, code obj1+{at:#x}..'
          f'{at + len(code):#x}')
    return at + len(code)
