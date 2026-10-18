"""Team choice / VIEW WORLD: a league with levels of groups is chosen level first, then group (Davide, 2026-10-19:
Italy 2026-27 'SERIE A, B, C, D' then 'SERIE D GIRONE A .. I'; every country with parallel groups: El Salvador ...).

SelectTeamsFinalMenu lists a country's competitions, one entry per division (the menu shows entries 11..20 only:
Italy's 14 divisions lost the last four). Three hooks:
- ml_list replaces the division loop's first instruction (`mov word [D0], 0` at @@its_a_division): a league of
  LV_TAB gets one entry per LEVEL (a single division as the game names it; a level of groups: its name, number
  80h | level), or, while a level is open (LVL, for the same league struct at the same menu depth), the level's
  divisions; then back to the competition loop as the game's loop ends (numberOfLeagues = the league's divisions);
- ml_pick1 / ml_pick2 follow the two picks (`mov [D0], ax` after the number is read from leagueNumbersTable: the
  career / Season pick and the VIEW WORLD one): a level number opens the level: the country pushed on the menu's
  country's competition list rebuilt at the same menu depth (cseg_4B500, D7 = the country, isCountryNumber 0: a
  push would make the game take it for a division's team list), filtered to the level;
- ml_esc (@@no_league_selected, ESCI) with a level open at this depth: closes it, the levels again;
- ml_load (@@load_team, the career's team choice: leagueNumber = the entry's index): the number from the table
  (a level opens; a cup keeps the index);
- ml_reset (SelectTeamsFinalMenu's first instruction): no level open.
Level names: the groups' common prefix without its last word ('SERIE D GIRONE A' .. 'I' -> 'SERIE D'), per exe
language. Needs menutab (more than 10 competitions in a country).
"""
import re
import struct

GROUP_WORDS = ('GIRONE', 'GROUP', 'GROUPE', 'GRUPPE', 'ZONA', 'ZONE', 'GRUPO', 'POOL')

ASM = '''
ml_reset:
    mov word [LEAGUENUM], 0
    mov byte [LVL], 0FFh
    jmp RESET_BACK

ml_list:                                ; A1 = a league struct, its divisions about to be listed
    mov eax, [A1]
    mov esi, LV_TAB
.f:
    mov edx, [esi]
    or edx, edx
    jz .orig
    cmp edx, eax
    je .found
    movzx ecx, byte [esi + 4]
    lea esi, [esi + 5 + 2 * ecx]
    lea esi, [esi + 4 * ecx]
    jmp .f
.orig:
    mov word [D0], 0
    jmp LOOP_BACK
.found:
    mov [LVL_LAST], eax
    movzx ecx, byte [esi + 4]
    add esi, 5
    cmp byte [LVL], 0FFh
    je .levels
    cmp [LVL_STRUCT], eax
    jne .levels
    mov edx, [CSP]
    cmp edx, [LVL_DEPTH]
    jne .levels
    movzx edx, byte [LVL]
    lea esi, [esi + 2 * edx]
    lea esi, [esi + 4 * edx]
    movzx ebx, byte [esi]
    movzx ecx, byte [esi + 1]
.g:
    push ecx
    call emit_div
    pop ecx
    inc ebx
    loop .g
    mov eax, [A1]                       ; an open level lists its groups only (no cups after it: VIEW WORLD)
    movzx eax, byte [eax + 9]
    mov [NUMLEAGUES], ax
    jmp NO_MORE
.levels:
    xor edx, edx
.l:
    push ecx
    movzx ebx, byte [esi]
    cmp byte [esi + 1], 1
    jne .lv
    call emit_div
    jmp .ln
.lv:
    mov eax, [esi + 2]
    mov ecx, edx
    or ecx, 80h
    call emit
.ln:
    add esi, 6
    inc edx
    pop ecx
    loop .l
.done:
    mov eax, [A1]
    movzx eax, byte [eax + 9]
    mov [NUMLEAGUES], ax
    jmp CUR_NEXT

emit_div:                               ; ebx = division: its name as the game's loop takes it
    mov eax, [A1]
    movsx ecx, byte [eax + 5]
    or ecx, ecx
    jnz .c
    mov eax, [DIVTAB + 4 * ebx]
    jmp .e
.c:
    lea eax, [eax + 5 + ecx]
    mov eax, [eax + 8 * ebx]
    add eax, STRBASE
.e:
    mov ecx, ebx
emit:                                   ; eax = name, cx = number
    push edi
    mov edi, [A2]
    mov [edi], eax
    add dword [A2], 4
    mov edi, [A3]
    mov eax, [A1]
    mov [edi], eax
    add dword [A3], 4
    mov edi, [A4]
    mov [edi], cx
    add dword [A4], 2
    inc word [D1]
    pop edi
    ret

ml_pick1:
    mov [D0], ax
    cmp ax, 80h
    jb .back
    cmp ax, 0FFh
    ja .back
    call open
.back:
    jmp BACK1

ml_pick2:
    mov [D0], ax
    cmp ax, 80h
    jb .back
    cmp ax, 0FFh
    ja .back
    call open
.back:
    jmp BACK2

ml_load:                                ; @@load_team (career team choice): leagueNumber = the entry's index D7
    movzx eax, word [D7]                ; -> its number in leagueNumbersTable (= the index for a plain division)
    mov ax, [NUMS + 2 * eax]
    cmp ax, 80h
    jb .div
    cmp ax, 0FFh
    ja .orig
    mov [D0], ax
    call open
.orig:
    mov ax, [D7]                        ; (a cup: no number, the game's index)
.div:
    mov [LEAGUENUM], ax
    jmp BACK3

open:                                   ; a level picked: the country's list again, at the same menu depth (no
    pop eax                             ; push: the depth tells the game which kind of list it shows), filtered
    mov al, [D0]                        ; (no return)
    and al, 7Fh
    mov [LVL], al
    mov eax, [LVL_LAST]
    mov [LVL_STRUCT], eax
    mov eax, [CSP]
    mov [LVL_DEPTH], eax
    mov ax, [D6]                        ; (D6 = the country at a division pick)
    mov [LVL_COUNTRY], ax
reopen:
    mov word [ISCN], 0                  ; the country's competitions (its file D7), not a division's teams
    mov ax, [LVL_COUNTRY]
    mov [D7], ax
    jmp REBUILD

ml_esc:                                 ; @@no_league_selected (ESCI): a level open -> close it, the levels again
    cmp byte [LVL], 0FFh
    je .orig
    mov eax, [CSP]
    cmp eax, [LVL_DEPTH]
    jne .orig
    mov byte [LVL], 0FFh
    jmp reopen
.orig:
    mov ax, [NUMSEL]
    jmp ESC_BACK

LVL: db 0FFh
align 4
LVL_LAST: dd 0
LVL_STRUCT: dd 0
LVL_DEPTH: dd 0
LVL_COUNTRY: dd 0
LV_TAB: LV_BYTES
    dd 0
'''


def level_name(names):
    """The groups' common prefix, whole words, without a trailing group word ('SERIE D GIRONE A' .. -> 'SERIE D')."""
    pre = names[0]
    for n in names[1:]:
        while not n.startswith(pre):
            pre = pre[:-1]
    w = pre.split(' ')
    if not pre.endswith(' '):
        w = w[:-1]                              # (a word cut by the prefix)
    w = [x for x in w if x]
    while w and w[-1] in GROUP_WORDS:
        w.pop()
    return ' '.join(w) or names[0]


def tables(lang):
    """[(league struct (obj, offset), [(first, count, level name or None)])] of every league with levels of groups."""
    import mkseason
    out = []
    for pk in mkseason.packs():
        par = pk.parallel()
        if not par:
            continue
        lfile = pk.files[pk.league['clubs']][0]
        at = mkseason.LEAGUE_AT.get((pk.world, lfile))
        if at is None:
            continue
        divs = pk.divisions()
        lv = []
        for first, sizes in par[1]:
            if len(sizes) == 1:
                lv.append((first, 1, None))
            else:
                nm = [(divs[first + g]['names'].get(lang) or divs[first + g]['names']['*'])[0] for g in range(len(sizes))]
                lv.append((first, len(sizes), level_name(nm)))
        out.append(((1, at) if isinstance(at, int) else at, lv))
    out += EXTRA
    return out


EXTRA = []              # (league struct (obj, offset), levels): world 0's leagues (4.1: seriec.py's Italy)


def _sites(p):
    import menutab
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    D7 = r['D7']
    D0, D1, D2, D6, A0 = D7 - 28, D7 - 24, D7 - 20, D7 - 4, r['A0']
    A1, A2, A3, A4 = A0 + 4, A0 + 8, A0 + 12, A0 + 16
    m = list(re.finditer(rb'\x66\xc7\x05' + pk(D0) + rb'\x00\x00\x8b\x35' + pk(A1) + rb'\x8a\x46\x05\xa2' + pk(D2) +
                         rb'\x0a\xc0\x75.\xc7\x05' + pk(A0) + rb'(.{4})', d1, re.S))
    assert len(m) == 1, len(m)
    loop = m[0].start()
    divtab = p.target(1, m[0].start(1))
    end = next(k for k in range(loop, loop + 0x200) if d1[k:k + 2] == b'\x66\xa3' and d1[k + 6] == 0xe9)
    numl = p.target(1, end + 2)
    cur_next = end + 11 + struct.unpack_from('<i', d1, end + 7)[0]
    k = d1.find(b'\x0f\x84', cur_next, cur_next + 40)      # cmp [A1], -1; jz @@no_more_competition_ptrs_for_country
    no_more = k + 6 + struct.unpack_from('<i', d1, k + 2)[0]
    picks = []
    for st in sorted(f[1] for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] == menutab.ORIG[1]):
        k = d1.find(b'\x66\x8b\x04\x06', st, st + 40)     # mov ax, [esi + eax]; mov [D0], ax
        if k > 0 and d1[k + 4:k + 6] == b'\x66\xa3' and d1[k + 6:k + 10] == struct.pack('<I', D0):
            picks.append(k + 4)
    assert len(picks) == 2, picks
    first = min(picks)                          # (the career / Season pick: its PushContinent .. jmp cseg_4B500 tail)
    t = re.search(rb'\xe8(.{4})\xe8(.{4})\x66\xc7\x05(.{4})\x01\x00\x66\xa1' + pk(D6) + rb'\x66\xa3(.{4})\xe9(.{4})',
                  d1[first:first + 0x100], re.S)
    k = first + t.start()
    rel = lambda o: k + o + 5 + struct.unpack_from('<i', d1, k + o + 1)[0]
    pushc, setsel, rebuild = rel(0), rel(5), rel(31)
    iscn, cn = p.target(1, k + 13), p.target(1, k + 27)
    csp = p.target(1, pushc + 1)
    m = list(re.finditer(rb'\x66\xc7\x05(.{4})\x00\x00\xc7\x05' + pk(A0) + rb'(.{4})\x8b\x35' + pk(A0) + rb'\xc6\x46\x09\x03',
                         d1, re.S))
    assert len(m) == 1, len(m)
    reset = m[0].start()
    leaguenum = p.target(1, reset + 3)
    m = list(re.finditer(rb'\xa0' + pk(D6) + rb'\xa2' + pk(D0) + rb'\x66\xa1' + pk(D7) + rb'\x66\xa3' + pk(leaguenum[1]) +
                         rb'\xe8', d1, re.S))
    assert len(m) == 1, len(m)
    load = m[0].start() + 10                    # @@load_team: mov ax, [D7]; mov [leagueNumber], ax
    m = list(re.finditer(rb'\x66\xa1(.{4})\x66\x0b\xc0\x0f\x84.{4}\x66\xc7\x05' + pk(iscn[1]) + rb'\x00\x00\xe8', d1, re.S))
    assert len(m) == 1, len(m)
    esc, numsel = m[0].start(), p.target(1, m[0].start(1))    # @@no_league_selected: mov ax, [numSelectedTeams]
    return dict(loop=loop, divtab=divtab, numl=numl, cur_next=cur_next, no_more=no_more, picks=sorted(picks), pushc=pushc, setsel=setsel,
                rebuild=rebuild, iscn=iscn, cn=cn, csp=csp, reset=reset, leaguenum=leaguenum, load=load, esc=esc, numsel=numsel,
                regs=dict(D0=D0, D1=D1, D6=D6, A1=A1, A2=A2, A3=A3, A4=A4))


def patch(p, at, area, lang):
    """The three hooks + LV_TAB at obj1:at (needs menutab.patch and mkseason.patch first); returns the end."""
    import menutab
    import nasmcave
    import sacups
    tabs = tables(lang)
    if not tabs:
        return at
    s = _sites(p)
    lv = []
    for (obj, off), levels in tabs:
        rows = ['dd S%d' % len(lv)]
        rows.append(f'db {len(levels)}')
        for first, count, name in levels:
            rows.append(f'db {first}, {count}')
            rows.append(f'dd N{len(lv)}_{first}' if name else 'dd 0')
        lv.append(((obj, off), levels, rows))
    sym = {k: (2, v) for k, v in s['regs'].items()}
    sym.update({'LEAGUENUM': s['leaguenum'], 'DIVTAB': s['divtab'], 'NUMLEAGUES': s['numl'], 'CSP': s['csp'],
                'ISCN': s['iscn'], 'CN': s['cn'], 'STRBASE': (2, sacups.STR_BASE),
                'RESET_BACK': (1, s['reset'] + 9), 'LOOP_BACK': (1, s['loop'] + 9), 'CUR_NEXT': (1, s['cur_next']), 'NO_MORE': (1, s['no_more']),
                'BACK1': (1, s['picks'][0] + 6), 'BACK2': (1, s['picks'][1] + 6), 'PUSHC': (1, s['pushc']),
                'SETSEL': (1, s['setsel']), 'REBUILD': (1, s['rebuild']), 'BACK3': (1, s['load'] + 12),
                'NUMS': (2, menutab.NEW[1]), 'D7': (2, s['regs']['D6'] + 4), 'NUMSEL': s['numsel'],
                'ESC_BACK': (1, s['esc'] + 6)})
    body = []
    for k, ((obj, off), levels, rows) in enumerate(lv):
        sym[f'S{k}'] = (obj, off)
        for first, count, name in levels:
            if name:
                sym[f'N{k}_{first}'] = (2, area.add(name.encode('latin1') + b'\0'))
        body += rows
    src = ASM.replace('LV_BYTES', '\n    '.join(body))     # (several lines: in the text, not a one-line symbol)
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    jmp = lambda src, dst, n: p.put(1, src, b'\xe9' + struct.pack('<i', dst - (src + 5)) + b'\x90' * (n - 5))
    for src, n in ((s['reset'], 9), (s['loop'], 9)):
        p.remove(1, src + 3)                       # (the overwritten instruction's fixup: mov word [abs], imm)
    jmp(s['reset'], lab['ml_reset'], 9)
    jmp(s['loop'], lab['ml_list'], 9)
    p.remove(1, s['load'] + 2)                     # mov ax, [D7]; mov [leagueNumber], ax (12 bytes)
    p.remove(1, s['load'] + 8)
    jmp(s['load'], lab['ml_load'], 12)
    p.remove(1, s['esc'] + 2)
    jmp(s['esc'], lab['ml_esc'], 6)
    for k, src in enumerate(s['picks']):
        p.remove(1, src + 2)
        jmp(src, lab[f'ml_pick{k + 1}'], 6)
    print(f'exe: team choice level -> group: {len(lv)} leagues, code obj1+{at:#x}..{at + len(code):#x}')
    return at + len(code)
