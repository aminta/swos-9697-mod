"""Copa Libertadores 1996-97 with the real 1997 format (session 27).

21 clubs: 20 in 5 groups of 4 (two countries per group, home and away, real 1997 calendar), the holder (River Plate)
straight into the round of 16. Top 3 of every group + the holder = 16. Two-leg round of 16, quarter-finals,
semi-finals and final on the real fixed bracket; aggregate, no away goals, no extra time, penalties.
Sources: RSSSF "Copa Libertadores 1997" (sacups/copa97), Wikipedia "1997 Copa Libertadores".

Engine (notes/STATUS.md session 27):
- the contest struct's first-stage team count is its total ([0Fh]) -> 21; lib_bye (replaces the `call cseg_2573C` at
  the end of cseg_24DFA, preset and career) sets round 1 [161h] to 20: the groups take the first 20 clubs of the list
  A2+59h (contest order), the 21st (holder) plays no group and its team-table index stays in A2+59h[20].
- lib_pre (called by historic.hist_draw before the fixed permutation of the round of 16): A2+59h[15] (the best 4th,
  picked because 16/5 leaves 1) := A2+59h[20] (holder); the 3rd of group 2 and the 3rd of the holder's country group
  swap places (Davide: the holder always meets the 3rd of its own group, as in 1996 and 1997).
- lib_cal (replaces `mov esi, [A0]` at @@european_championships in cseg_89758): our 4-team groups take their matches
  from LIB_CAL (per group 12 (home, away) slot pairs: first cycle as played, second cycle stored reversed because the
  engine swaps home and away when [5Fh] (cycles left) is odd) instead of the game's 4-team table.
Both run only for contest id LIB_ID with 21 clubs (diyFileBufferCopy [31h]): an old 1.3 contest in a saved career keeps
the old behaviour until its season ends.
"""
import re
import struct

import nasmcave
import sacups

LIB_GROUPS = sacups.LIB_GROUPS     # clubs in the group stage; the 21st (last of sacups.LIBERTADORES) is the holder

# group slots = sacups.LIBERTADORES order: (country A champion, country B champion, A runner-up, B runner-up)
GROUPS = [['Bolivar', 'Guarani', 'Oriente', 'Cerro'],
          ['Velez', 'ElNacional', 'Racing', 'Emelec'],
          ['ColoColo', 'Minerven', 'UCatolica', 'Mineros'],
          ['Gremio', 'SCristal', 'Cruzeiro', 'Alianza'],
          ['Penarol', 'Millonarios', 'Nacional', 'Cali']]
# real 1997 matchdays (home-away). Each day = two matches covering the group; days ordered by their first match date
# (RSSSF). Groups 1-4: days 4-6 mirror days 1-3 as played; group 5 (an irregular calendar) gets the closest fit.
CALENDAR = [
    ['Guarani-Cerro Oriente-Bolivar', 'Oriente-Guarani Bolivar-Cerro', 'Bolivar-Guarani Oriente-Cerro',
     'Cerro-Guarani Bolivar-Oriente', 'Guarani-Oriente Cerro-Bolivar', 'Cerro-Oriente Guarani-Bolivar'],
    ['Emelec-ElNacional Racing-Velez', 'ElNacional-Velez Emelec-Racing', 'ElNacional-Racing Emelec-Velez',
     'ElNacional-Emelec Velez-Racing', 'Velez-ElNacional Racing-Emelec', 'Racing-ElNacional Velez-Emelec'],
    ['Mineros-Minerven UCatolica-ColoColo', 'UCatolica-Mineros ColoColo-Minerven', 'ColoColo-Mineros UCatolica-Minerven',
     'ColoColo-UCatolica Minerven-Mineros', 'Mineros-UCatolica Minerven-ColoColo', 'Minerven-UCatolica Mineros-ColoColo'],
    ['Cruzeiro-Gremio SCristal-Alianza', 'Alianza-Cruzeiro SCristal-Gremio', 'SCristal-Cruzeiro Alianza-Gremio',
     'Gremio-Cruzeiro Alianza-SCristal', 'Cruzeiro-Alianza Gremio-SCristal', 'Gremio-Alianza Cruzeiro-SCristal'],
    ['Cali-Millonarios Nacional-Penarol', 'Nacional-Millonarios Cali-Penarol', 'Penarol-Millonarios Cali-Nacional',
     'Millonarios-Penarol Nacional-Cali', 'Penarol-Nacional Millonarios-Cali', 'Millonarios-Nacional Penarol-Cali'],
]

# Knockout (hist_draw permutations, new[k] = old[perm[k]]; consecutive pairs, first club = first leg at home).
# Round of 16 input: 1st of groups 1-5 (0-4), 2nd (5-9), 3rd (10-14), holder (15). Real 1997 ties, bracket order:
# Racing 3G2 - River H | Millonarios 2G5 - Penarol 1G5 | S.Cristal 3G4 - Velez 1G2 | Minerven 3G3 - Bolivar 1G1 |
# El Nacional 2G2 - Cruzeiro 2G4 | Guarani 3G1 - Gremio 1G4 | Nacional 3G5 - Colo Colo 1G3 | U.Catolica 2G3 - Oriente 2G1
R16 = [11, 15, 9, 4, 13, 1, 12, 0, 6, 8, 10, 3, 14, 2, 7, 5]
QF = [1, 0, 3, 2, 4, 5, 7, 6]       # Penarol-Racing, Bolivar-S.Cristal, Cruzeiro-Gremio, U.Catolica-Colo Colo
SF = [0, 1, 2, 3]                   # Racing-S.Cristal, Cruzeiro-Colo Colo
FINAL = [0, 1]                      # S.Cristal-Cruzeiro
DRAWS = [(sacups.LIB_ID, R16), (sacups.LIB_ID, QF), (sacups.LIB_ID, SF), (sacups.LIB_ID, FINAL)]


def calendar_bytes():
    out = bytearray()
    for g, (names, days) in enumerate(zip(GROUPS, CALENDAR)):
        slot = {n: k for k, n in enumerate(names)}
        pairs = [tuple(slot[t] for t in m.split('-')) for day in days for m in day.split()]
        assert len(pairs) == 12 and len(set(pairs)) == 12
        for d in range(6):
            assert sorted(pairs[2 * d] + pairs[2 * d + 1]) == [0, 1, 2, 3], (g, d)
        first, second = pairs[:6], pairs[6:]
        assert {frozenset(p) for p in first} == {frozenset(p) for p in second} and len({frozenset(p) for p in first}) == 6
        assert {(b, a) for a, b in first} == set(second), g          # second cycle = return matches
        for h, a in first:
            out += bytes((h, a))
        for h, a in second:
            out += bytes((a, h))                                      # the engine swaps them back
    return bytes(out)


ASM = '''
lib_bye:                                ; replaces `call cseg_2573C` at the end of cseg_24DFA
    pushad
    mov al, [DIYCOPY + 2Dh]             ; a cup with first-round byes (BYE_TAB: season / world packs with byes in
    mov cx, [DIYCOPY + 161h]            ; ties.csv, FA Cup 1871-72): round 1 = its clubs but the b last ones
    call bye_find
    jc .nb
    movzx eax, byte [esi + 3]
    sub [DIYCOPY + 161h], ax
.nb:
    popad
    cmp byte [DIYCOPY + 2Dh], LIB_ID
    jne .go
    cmp word [DIYCOPY + 161h], LIB_N    ; round 1 = every club of the contest...
    jne .go
    mov word [DIYCOPY + 161h], LIB_GROUPS   ; ... but the holder plays no group
.go:
    jmp CSEG_2573C

bye_find:                               ; al = contest id, cx = its clubs -> CF = 0, esi = its BYE_TAB entry
    mov esi, BYE_TAB                    ; (id, world, clubs, byes); world 0 = any (one-world builds: ids unique)
    mov edx, BYE_NT
.l:
    test edx, edx
    jz .no
    cmp [esi], al
    jne .n
    test ch, ch
    jnz .n
    cmp [esi + 2], cl
    jne .n
%if BW_ON
    cmp byte [esi + 1], 0
    je .ok
    push eax
    mov al, [WORLDB]                    ; the running career's world (several worlds: cup ids per world)
    cmp [esi + 1], al
    pop eax
    jne .n
%endif
.ok:
    clc
    ret
.n:
    add esi, 4
    dec edx
    jmp .l
.no:
    stc
    ret

lib_pre:                                ; hist_draw, before the permutation: esi = DIY buffer, ecx = clubs in the round
    call FIN_PRE                        ; 2.1: NSL / NSSL finals series (finals97.fin_pre)
    pushad                              ; a cup with byes, round 2 (its (N - b) / 2 winners + b): the b clubs left
    mov ebp, esi                        ; out of round 1 (list[N - b ..], untouched) follow the winners (the fixed
    mov edi, ecx                        ; draw then puts them in their bracket slots)
    mov al, [ebp + 2Dh]
    mov cx, [ebp + 31h]
    call bye_find
    jc .nb
    movzx ebx, byte [esi + 3]
    movzx eax, byte [esi + 2]
    sub eax, ebx                        ; N - b: the first one left out
    mov edx, eax
    shr edx, 1                          ; the winners
    lea ecx, [edx + ebx]
    cmp ecx, edi
    jne .nb
.c:
    mov cl, [ebp + 59h + eax]           ; (target < source: an ascending copy is safe)
    mov [ebp + 59h + edx], cl
    inc eax
    inc edx
    dec ebx
    jnz .c
.nb:
    popad
.lib:
    cmp byte [esi + 2Dh], LIB_ID
    jne .r
    cmp ecx, 16
    jne .r
    cmp word [esi + 31h], LIB_N
    jne .r
    pushad
    lea edi, [esi + 59h]
    movzx ebx, byte [edi + LIB_GROUPS]  ; holder's team-table index (no group)
    mov [edi + 15], bl                  ; in place of the best 4th
    mov al, [esi + 99h + ebx*2]         ; its country (team word = country, ordinal)
    movzx ecx, word [esi + 31h]
    xor edx, edx
.f:
    cmp edx, ebx
    je .n
    cmp [esi + 99h + edx*2], al
    je .g
.n:
    inc edx
    cmp edx, ecx
    jb .f
    jmp .done
.g:
    movzx edx, byte [esi + 119h + edx]  ; group of a club of the same country (0-based)
    cmp edx, 5
    jae .done
    mov al, [edi + 11]                  ; 3rd of group 2 <-> 3rd of the holder's group
    xchg al, [edi + 10 + edx]
    mov [edi + 11], al
.done:
    popad
.r:
    ret

lib_cal:                                ; replaces `mov esi, [A0]` in cseg_89758 (A3 = 4-team table)
    mov esi, [A0]
    cmp byte [esi + 2Dh], LIB_ID
    jne .r
    cmp word [esi + 51h], 4
    jne .r
    cmp word [DIYCOPY + 31h], LIB_N
    jne .r
    movzx eax, word [esi + 5Bh]         ; group
    cmp eax, 5
    jae .r
    imul eax, eax, 24
    test byte [esi + 5Fh], 1            ; second cycle: return matches
    jz .a
    add eax, 12
.a:
    add eax, LIB_CAL
    mov [A3], eax
.r:
    ret

LIB_CAL: CAL_BYTES
BYE_TAB: BYE_BYTES
'''


def _sites(p):
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = r['D7'] + 4
    # end of cseg_24DFA: mov [esi+161h], ax; call cseg_2573C; call cseg_258E4; retn; int 3; jmp $
    m = [x for x in re.finditer(rb'\x66\x89\x86\x61\x01\x00\x00\xe8(.{4})\xe8.{4}\xc3\xcc\xeb\xfe', d1, re.S)]
    assert len(m) == 1, len(m)
    bye_call = m[0].start() + 7
    c2573c = bye_call + 5 + struct.unpack('<i', m[0].group(1))[0]
    # cseg_2573C: mov byte/word [...], 1; call nullsub; ... mov [A0], offset diyFileBufferCopy
    k = d1.find(b'\xc7\x05' + struct.pack('<I', a0), c2573c)
    assert 0 < k - c2573c < 0x60, hex(k - c2573c)
    diycopy = struct.unpack_from('<I', d1, k + 6)[0]
    # cseg_89758 @@european_championships: mov esi,[A0]; mov ax,[esi+1CBh]; mov [D0],ax; shl [D0],1
    m = [x.start() for x in re.finditer(re.escape(b'\x8b\x35' + struct.pack('<I', a0) + b'\x66\x8b\x86\xcb\x01\x00\x00'), d1)]
    m = [x for x in m if d1[x + 13:x + 15] == b'\x66\xa3']
    assert len(m) == 1, [hex(x) for x in m]
    return a0, bye_call, c2573c, diycopy, m[0]


def patch(p, cave, fin_pre):
    import mkseason
    bc = [(0xC3, 0, 15, 1)] + mkseason.bye_cups()           # historic.FA_ID: FA Cup 1871-72 (15 clubs, 1 bye)
    assert all(0 < b and n <= 255 and (n - b) % 2 == 0 for _, _, n, b in bc), bc
    bw = mkseason.multi_ns() and any(w for _, w, _, _ in bc)  # several worlds: a world's cup ids are its own
    if bw:
        import careerworld
        slt = careerworld.SITES['slt']
    """Returns (cave end, lib_pre offset) — lib_pre is called by historic.hist_draw."""
    a0, bye_call, c2573c, diycopy, cal_site = _sites(p)
    symbols = {'DIYCOPY': (2, diycopy), 'LIB_ID': (0, sacups.LIB_ID), 'LIB_N': (0, sacups.LIB_N),
               'LIB_GROUPS': (0, LIB_GROUPS), 'CSEG_2573C': (1, c2573c), 'A0': (2, a0), 'A3': (2, a0 + 12),
               'BYE_NT': (0, len(bc)), 'BYE_BYTES': (0, 'db ' + ', '.join(str(x) for e in bc for x in e)),
               'BW_ON': (0, int(bw)), 'WORLDB': (slt[0], slt[1] + careerworld.WORLD_BYTE) if bw else (0, 0),
               'FIN_PRE': (1, fin_pre),
               'CAL_BYTES': (0, 'db ' + ', '.join(str(b) for b in calendar_bytes()))}
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    labels = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.put(1, bye_call + 1, struct.pack('<i', labels['lib_bye'] - (bye_call + 5)))
    p.remove(1, cal_site + 2)                                     # mov esi, [A0] (6 B) -> call lib_cal; nop
    p.put(1, cal_site, b'\xe8' + struct.pack('<i', labels['lib_cal'] - (cal_site + 5)) + b'\x90')
    print(f'exe: Libertadores 1997: bye call obj1+{bye_call:#x} (lib_bye {labels["lib_bye"]:#x}, BYE_TAB {len(bc)}), '
          f'calendar obj1+{cal_site:#x}, code @ obj1+{cave:#x} '
          f'(diyFileBufferCopy obj2+{diycopy:#x})')
    return (cave + len(code) + 3) & ~3, labels['lib_pre']
