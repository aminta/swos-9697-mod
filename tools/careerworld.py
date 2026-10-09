"""Historic career worlds (career packs M2): the world switch in the same exe.

A WORLD is a set of career packs (countries) with the same pack.json `world` number. A career started with a club of
a world country runs in that world: its season-end country list, its European places and cups, its first-season
European clubs. The world byte lives in the save: someLeaguesTable[1845], with the balance byte [1846] = -world
(cseg_9487A traps unless the table sums to 0; globals 1818..1846 belong to no club, 1847..1849 = 'S3' mark; InitCareer
clears the table, so a normal career has 0 = the 1996-97 world). Written to leaguesTableCopy too: InitializeNewSeason
copies that table back over someLeaguesTable (cseg_8CC4E).

European cups of a world are knockout cups that fit the in-save copies (euroCupCopy 79 B = at most 16 clubs,
cupWinnersCupCopy / uefaCupCopy 92 B = at most 32): the season end writes the qualifiers into their team lists, so
nothing has to move. Hooks (all found by content):
  InitCareer   start: remember the club's country; the 3 LoadSomeEuroCup calls: a world loads data\\worldNN.tmd (its
               first-season European clubs) once; after the careerContests copy: the world's 3 cup structs.
  cseg_91428   (season end) seasonEndList and the 16 / 32 / 32 / 80 checks per world.
  cseg_936C0   the 3 static place tables per world.
"""
import re
import struct

TEAM_SIZE = 684
COPY = {'cc': 79, 'cwc': 92, 'uefa': 92}           # in-save struct copies
MAX = {'cc': 16, 'cwc': 32, 'uefa': 32}
WORLD_BYTE = 1845                                    # someLeaguesTable index (+1 = balance byte)
REC = 48                                             # world record: 8 dwords, 5 words, year byte, pad, dword
WCONT = 99                                           # pseudo-continent of the running world (view, foreign browser)

ASM = '''
w_entry:                                ; replaces `mov ax, [D0]; mov [D7], ax` at the start of InitCareer
    mov ax, [D0R]
    mov [D7R], ax
    mov [WSEL], al                      ; the chosen club's country (team number low byte)
    ret

w_rec:                                  ; ebx = this career's world record, ZF = 1 for the 1996-97 world
    movzx ebx, byte [SLT + WORLD_BYTE]
    test ebx, ebx
    jz .r
    imul ebx, ebx, REC
    add ebx, WTAB - REC
.r:
    ret

w_load1:                                ; replaces the first `call LoadSomeEuroCup` (euroCup) in InitCareer
    push esi
    push eax
    mov al, [WSEL]
    mov esi, WMAP                       ; country, world pairs + FF
.l:
    cmp byte [esi], 0xff
    je .none
    cmp [esi], al
    je .found
    add esi, 2
    jmp .l
.none:
    mov byte [SLT + WORLD_BYTE], 0
    mov byte [SLTCOPY + WORLD_BYTE], 0
    pop eax
    pop esi
    jmp LOADEURO
.found:
    mov al, [esi + 1]
    mov [SLT + WORLD_BYTE], al          ; also in leaguesTableCopy: InitializeNewSeason (cseg_8CC4E) copies it back
    mov [SLTCOPY + WORLD_BYTE], al      ; over someLeaguesTable, like the 'S3' mark (trailer.set_mark)
    neg al
    mov [SLT + WORLD_BYTE + 1], al      ; the tables must keep summing to 0
    mov [SLTCOPY + WORLD_BYTE + 1], al
    push ebx
    call w_rec
    mov eax, [ebx + 12]
    mov [A1R], eax                      ; data\\worldNN.tmd
    pop ebx
    pop eax
    pop esi
    jmp KNOWN                           ; LoadSomeEuroCup body: load [A1] at tmdFileBuffer + careerFileBuffer * 684

w_load23:                               ; replaces the 2nd and 3rd `call LoadSomeEuroCup`: nothing more in a world
    cmp byte [SLT + WORLD_BYTE], 0
    jne .r
    jmp LOADEURO
.r:
    ret

w_cups:                                 ; replaces `mov word [teamsLoaded], 0` after the careerContests copy
    mov word [TEAMSLOADED], 0
    pushad
    call w_rec
    jz .r
    mov esi, [ebx]
    mov edi, CCCOPY
    mov ecx, 79
    call w_copy
    mov esi, [ebx + 4]
    mov edi, CWCCOPY
    mov ecx, 92
    call w_copy
    mov esi, [ebx + 8]
    mov edi, UEFACOPY
    mov ecx, 92
    call w_copy
    mov al, [ebx + 42]                  ; the world's first season (InitCareer: -1, then InitializeNewSeason: +1)
    mov [SEASONPLAYING], al
.r:
    popad
    ret

w_list:                                 ; replaces `mov dword [A6], seasonEndList` in cseg_91428
    push ebx
    call w_rec
    jz .o
    mov ebx, [ebx + 16]
    mov [A6R], ebx
    pop ebx
    ret
.o:
    mov dword [A6R], SEASONLIST
    pop ebx
    ret

%macro W_TAB 3                          ; replaces `mov dword [A0], <static place table>` in cseg_936C0
%1:
    push ebx
    call w_rec
    jz .o
    mov ebx, [ebx + %2]
    mov [A0R], ebx
    pop ebx
    ret
.o:
    mov dword [A0R], %3
    pop ebx
    ret
%endmacro
W_TAB w_cctab, 20, CCTAB
W_TAB w_cwctab, 24, CWCTAB
W_TAB w_uefatab, 28, UEFATAB

w_uefa0:                                ; replaces `mov eax, [UEFATAB]` (first group pointer) in cseg_936C0
    push ebx
    call w_rec
    jz .o
    mov eax, [ebx + 28]
    mov eax, [eax]
    pop ebx
    ret
.o:
    mov eax, [UEFATAB]
    pop ebx
    ret

%macro W_CHK 4                          ; replaces `cmp word [%3], %4` (season-end checks); flags survive pop / ret
%1:
    push ebx
    call w_rec
    jz .o
    mov bx, [ebx + %2]
    cmp [%3], bx
    pop ebx
    ret
.o:
    cmp word [%3], %4
    pop ebx
    ret
%endmacro
W_CHK w_chk_tot, 32, CFB, 80
W_CHK w_chk_tot0, 40, CFB, 80
W_CHK w_chk_cc, 34, CNT_CC, 16
W_CHK w_chk_cwc, 36, CNT_CWC, 32
W_CHK w_chk_uefa, 38, CNT_UEFA, 32

w_copy:                                 ; ecx bytes esi -> edi (no string instructions: ES may differ from DS)
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz w_copy
    ret

%macro W_YEAR 2                         ; replaces `cmp word [D0], %2` (year 1900 + seasonPlaying below it gets +100)
%1:
    push ebx
    call w_rec
    jz .o
    push eax
    movzx eax, byte [ebx + 42]
    add eax, 1900 + %2 - 1996           ; a world wraps at its own first year
    cmp [D0R], ax
    pop eax
    pop ebx
    ret
.o:
    cmp word [D0R], %2
    pop ebx
    ret
%endmacro
W_YEAR w_year96, 1996
W_YEAR w_year95, 1995

%macro W_SWAP 2                         ; replaces `call %2`: in a world, competitionsTable[254] = [.., -1, 99] and
%1:                                     ; [99] = the world's continent (its countries, its cups = the in-save copies)
    push ebx
    call w_rec
    jz .o
    push dword [COMP254]
    push dword [COMP99]
    mov dword [COMP254], WVIEW
    mov ebx, [ebx + 44]
    mov [COMP99], ebx
    call %2
    pop dword [COMP99]
    pop dword [COMP254]
    pop ebx
    ret
.o:
    pop ebx
    jmp %2
%endmacro
W_SWAP w_view, CHOOSECOMP
W_SWAP w_buy, CHOOSETEAMS

w_nat:                                  ; replaces `mov ax, [D0]; mov [lastNationalityCall], ax`: no national team
    mov ax, [D0R]                       ; job in a world (-1 = none)
    push ebx
    call w_rec
    pop ebx
    jz .s
    mov ax, -1
.s:
    mov [LASTNAT], ax
    ret

w_holders:                              ; replaces `call cseg_92BBF`: in a world the holders get a place of their own
    push ebx                            ; (appended to the list + record), the game replaces a random qualifier
    call w_rec
    pop ebx
    jnz .w
    jmp HOLDERS
.w:
    pushad
    mov esi, HOLDTAB                    ; per cup: holder, list start pointer, counter, saved holder record
.c:
    mov ebx, [esi]
    cmp ebx, -1
    je .r
    mov ax, [ebx]
    cmp ax, 0FFFFh
    je .n
    mov edi, [esi + 4]
    mov edi, [edi]
    mov edx, [esi + 8]
    movzx ecx, word [edx]
    mov [edi + ecx * 2], ax
    inc word [edx]
    mov eax, [esi + 12]
    mov [A0R], eax
    push esi
    call ADDREC                         ; cseg_94193: record [A0] -> tmdFileBuffer[careerFileBuffer++]
    pop esi
.n:
    add esi, 16
    jmp .c
.r:
    popad
    ret

w_isholder:                             ; ZF = 1 when word [D0] is one of the three holders or already in a list
    push eax                            ; (a club skipped by one cup must not be taken twice by the next)
    push esi
    push ecx
    mov ax, [D0R]
    cmp ax, [HOLD_CC]
    je .y
    cmp ax, [HOLD_CWC]
    je .y
    cmp ax, [HOLD_UEFA]
    je .y
    mov esi, HOLDTAB
.l:
    cmp dword [esi], -1
    je .n
    mov ecx, [esi + 8]
    movzx ecx, word [ecx]
    push esi
    mov esi, [esi + 4]
    mov esi, [esi]
.e:
    test ecx, ecx
    jz .x
    cmp ax, [esi]
    je .f
    add esi, 2
    dec ecx
    jmp .e
.f:
    pop esi
    jmp .y
.x:
    pop esi
    add esi, 16
    jmp .l
.n:
    or esi, esi                         ; ZF = 0 (esi -> HOLDTAB end, not 0)
.y:
    pop ecx
    pop esi
    pop eax
    ret

w_pick_cc:                              ; replaces `call cseg_93BCE` in cseg_939C9 (Champions Cup = the champion): in
    push ebx                            ; a world a holder plays its own cup as holder, so the place goes to the next
    call w_rec                          ; club of the table (cseg_93BCE would clear the holder: one place short)
    pop ebx
    jnz .w
    jmp CLEARHOLD
.w:
    call w_isholder
    jne .r
    add dword [A5R], 684
    push eax
    mov eax, [A5R]
    mov ax, [eax]
    mov [D0R], ax
    pop eax
    jmp .w
.r:
    ret

%macro W_PICK 2                         ; replaces `call cseg_93BCE` in the CWC / UEFA loops: a holder is skipped
%1:                                     ; (back to the loop: the next club of the table)
    push ebx
    call w_rec
    pop ebx
    jnz .w
    jmp CLEARHOLD
.w:
    call w_isholder
    jne .r
    add esp, 4
    jmp %2
.r:
    ret
%endmacro
W_PICK w_pick_cwc, LOOP_CWC
W_PICK w_pick_uefa, LOOP_UEFA

align 4
HOLDTAB:
    dd HOLD_CC, LIST_CC, CNT_CC, BUF_CC
    dd HOLD_CWC, LIST_CWC, CNT_CWC, BUF_CWC
    dd HOLD_UEFA, LIST_UEFA, CNT_UEFA, BUF_UEFA
    dd -1
WVIEW:
    dd VIEWFIRST, -1
    db WCONT, 0xff
WSEL: db 0
'''


def _one(pat, d, what):
    ms = list(re.finditer(pat, d, re.S))
    assert len(ms) == 1, (what, len(ms))
    return ms[0]


def sites(p):
    """Every hook site and the addresses the hooks use (obj, offset)."""
    import countries
    import sacups
    orig = p.le.obj_bytes(1)
    d1 = bytes(p.get(1, 0, len(orig)))
    r = sacups.regs(orig)
    D7, A0 = r['D7'], r['A0']
    D0, A1, A6 = D7 - 28, A0 + 4, A0 + 24
    pk = lambda x: re.escape(struct.pack('<I', x))
    s = {}
    # InitCareer
    m = _one(rb'\x66\xa1' + pk(D0) + rb'\x66\xa3' + pk(D7) + rb'\x66\xc7\x05.{4}\x52\x02', d1, 'InitCareer')
    s['entry'] = m.start()
    m = _one(rb'\xc7\x05' + pk(A0) + rb'.{4}\x66\xc7\x05' + pk(D0) + rb'\xcf\x07', d1[m.start():m.start() + 0x40], 'SLT')
    s['slt'] = p.target(1, s['entry'] + m.start() + 6)
    # cseg_8CC0A: mov [D0], 1999; mov [A0], someLeaguesTable; mov [A1], leaguesTableCopy
    slt_raw = d1[s['entry'] + m.start() + 6:s['entry'] + m.start() + 10]
    ms = list(re.finditer(rb'\xc7\x05' + pk(A0) + re.escape(slt_raw) + rb'\xc7\x05' + pk(A1), d1))
    tg = {p.target(1, x.end()) for x in ms}                  # cseg_8CC0A and cseg_8CC4E: the same table
    assert len(ms) == 2 and len(tg) == 1, (len(ms), tg)
    s['sltcopy'] = tg.pop()
    m = _one(rb'\x66\xc7\x05(.{4})\x00\x00' + (rb'\xc7\x05' + pk(A0) + rb'.{4}\xe8(.{4})') * 3, d1, 'LoadSomeEuroCup x3')
    s['cfb'] = struct.unpack('<I', m.group(1))[0]
    s['load'] = [m.start() + 9 + 15 * k + 10 for k in range(3)]
    s['loadeuro'] = s['load'][0] + 5 + struct.unpack('<i', m.group(2))[0]
    s['euro'] = [p.target(1, m.start() + 9 + 15 * k + 6) for k in range(3)]
    le = s['loadeuro']                                       # @@known_contest = target of its first jz short
    assert d1[le] == 0xc7 and d1[le + 10] == 0x81 and d1[le + 20] == 0x74, d1[le:le + 24].hex()
    s['known'] = le + 22 + d1[le + 21]
    m = _one(rb'\x66\xc7\x05(.{4})\x00\x00\x66\xc7\x05.{4}\x05\x00\x66\xc7\x05.{4}\x02\x00\x66\xc7\x05.{4}\x08\x00'
             rb'\x66\xc7\x05.{4}\x05\x00', d1, 'teamsLoaded')
    s['cups'], s['teamsloaded'] = m.start(), struct.unpack('<I', m.group(1))[0]
    # careerContests copies: [src, dst, size] from the table InitCareer reads (mov [A2], table right after the loads)
    tobj, tab = p.target(1, s['load'][2] + 5 + 6)
    td = p.le.obj_bytes(tobj)
    copies = {}
    k = tab
    while struct.unpack_from('<i', p.get(tobj, k, 4))[0] != -1:
        src, dst = p.target(tobj, k), p.target(tobj, k + 4)
        copies[src] = (dst, struct.unpack_from('<H', p.get(tobj, k + 8, 2))[0])
        k += 10
    s['copies'] = [copies[e] for e in s['euro']]
    for (dst, n), key in zip(s['copies'], ('cc', 'cwc', 'uefa')):
        assert n == COPY[key], (key, n)
    # cseg_91428: the seasonEndList reference (countries.tables) and the checks after the country loop
    _, _, _, ref = countries.tables(p)
    s['list'] = ref - 6
    assert d1[s['list']:s['list'] + 2] == b'\xc7\x05' and d1[s['list'] + 2:s['list'] + 6] == struct.pack('<I', A6)
    s['seasonlist'] = p.target(1, ref)
    tail = d1[s['list']:s['list'] + 0x120]
    cfb = pk(s['cfb'])
    m = _one(rb'\x66\x83\x3d' + cfb + rb'\x50\x75.\xe8.{4}\x66\xc7\x05.{4}\x00\x00\xe8.{4}'
             rb'\x66\x83\x3d(.{4})\x10\x75.\x66\x83\x3d(.{4})\x20\x75.\x66\x83\x3d(.{4})\x20\x75.'
             rb'\x66\x83\x3d' + cfb + rb'\x50\x75', tail, 'checks')
    b = s['list'] + m.start()
    s['chk'] = [(b, 'w_chk_tot0'), (b + 29, 'w_chk_cc'), (b + 39, 'w_chk_cwc'), (b + 49, 'w_chk_uefa'),
                (b + 59, 'w_chk_tot')]
    s['cnt'] = [struct.unpack('<I', m.group(k))[0] for k in (1, 2, 3)]
    # cseg_936C0: the static place tables are 0x42 / 0x91 / 0xE0 after the original seasonEndList (obj2)
    o2 = countries.tables(p)[2]
    s['tabs'] = []
    for delta, name, op in ((0x42, 'w_cctab', b'\xc7\x05'), (0x91, 'w_cwctab', b'\xc7\x05'),
                            (0xE0, 'w_uefa0', b'\xa1'), (0xE0, 'w_uefatab', b'\xc7\x05')):
        if op == b'\xa1':
            refs = [f[1] - 1 for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] == o2 + delta
                    and orig[f[1] - 1] == 0xa1]
        else:
            refs = [f[1] - 6 for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] == o2 + delta
                    and orig[f[1] - 6:f[1]] == op + struct.pack('<I', A0)]
        assert len(refs) == 1, (name, refs)
        s['tabs'].append((refs[0], name, o2 + delta))
    # M3 holders: call cseg_92BBF after the first check; per cup mov ax,[holder]; mov [D2],ax; mov [A3],buf;
    # mov eax,[list]; mov [A2],eax; mov ax,[counter]; mov [D3],ax; call cseg_92C4D
    hb = b + 15 + struct.unpack_from('<i', d1, b + 11)[0]
    assert d1[b + 10] == 0xe8
    s['holders'], s['holders_call'] = hb, b + 10
    s['hold'] = []
    blk = (rb'\x66\xa1(.{4})\x66\xa3' + pk(D7 - 20) + rb'\xc7\x05' + pk(A0 + 12) + rb'(.{4})\xa1(.{4})\xa3' + pk(A0 + 8)
           + rb'\x66\xa1(.{4})\x66\xa3' + pk(D7 - 16))
    k = hb
    for i in range(3):                                       # the third block falls through into cseg_92C4D
        m = re.match(blk, d1[k:k + 60], re.S)
        assert m, d1[k:k + 60].hex()
        s['hold'].append(tuple(struct.unpack('<I', m.group(j))[0] for j in (1, 2, 3, 4)))
        k += m.end()
        if i < 2:
            assert d1[k] == 0xe8
            c4d = k + 5 + struct.unpack_from('<i', d1, k + 1)[0]
            k += 5
    assert c4d == k, (hex(c4d), hex(k))
    m = _one(rb'\xa1' + pk(A0 + 12) + rb'\xa3' + pk(A0) + rb'\xe8(.{4})', d1[c4d:c4d + 0x120], 'cseg_94193 call')
    s['addrec'] = c4d + m.end() + struct.unpack('<i', m.group(1))[0]
    # year: InitCareer `sub byte [seasonPlaying], 1; call InitializeNewSeason`; PrintNameAndSeason cmp 1996,
    # CareerOverFinish cmp 1995
    m = _one(rb'\x80\x2d(.{4})\x01\xe8', d1, 'seasonPlaying')
    s['season'] = struct.unpack('<I', m.group(1))[0]
    s['y96'] = _one(rb'\x66\x81\x3d' + pk(D0) + rb'\xcc\x07', d1, '1996').start()
    s['y95'] = _one(rb'\x66\x81\x3d' + pk(D0) + rb'\xcb\x07', d1, '1995').start()
    # ViewWorldMenu: call ChooseCompetitionMenu; mov ax,[chooseTeamsResult]; or ax,ax; jz; mov eax,[selectedContest]
    m = _one(rb'\xe8(.{4})\x66\xa1.{4}\x66\x0b\xc0\x74.\xa1.{4}\xa3' + pk(A0) + rb'\x66\xa1.{4}\x66\xa3' + pk(D0)
             + rb'\xe8', d1, 'ViewWorldMenu')
    s['view'] = m.start()
    s['choosecomp'] = m.start() + 5 + struct.unpack('<i', m.group(1))[0]
    # BuyOtherForeignPlayer: ... D2 = 1, D3 = D4 = 0, call ChooseTeamsDialog; cmp word [D0], -1
    m = _one(rb'\xc7\x05' + pk(A1) + rb'\x00\x00\x00\x00\x66\xc7\x05' + pk(D7 - 20) + rb'\x01\x00\x66\xc7\x05' + pk(D7 - 16)
             + rb'\x00\x00\x66\xc7\x05' + pk(D7 - 12) + rb'\x00\x00\xe8(.{4})\x66\x83\x3d' + pk(D0) + rb'\xff\x74', d1,
             'BuyOtherForeignPlayer')
    s['buy'] = m.start() + 37
    assert d1[s['buy']] == 0xe8
    s['chooseteams'] = s['buy'] + 5 + struct.unpack('<i', m.group(1))[0]
    # cseg_8D7B4 tail: mov word [D0], -1; mov ax, [D0]; mov [lastNationalityCall], ax; or ax, ax; ret
    m = _one(rb'\x66\xc7\x05' + pk(D0) + rb'\xff\xff\x66\xa1' + pk(D0) + rb'\x66\xa3(.{4})\x66\x0b\xc0\xc3', d1, 'lastNat')
    s['nat'], s['lastnat'] = m.start() + 9, struct.unpack('<I', m.group(1))[0]
    # cseg_93BCE (clears a holder that qualified through its league) and its 3 calls: cseg_939C9 (CC champion),
    # cseg_939FE / cseg_93A60 (CWC / UEFA loops: the jz before the call goes back to the loop)
    hcc = s['hold'][0][0]
    m = _one(rb'\x66\xa1' + pk(hcc) + rb'\x66\x39\x05' + pk(D0) + rb'\x75.\x66\xc7\x05' + pk(hcc) + rb'\xff\xff\xc3', d1,
             'cseg_93BCE')
    s['clearhold'] = m.start()
    calls = [i for i in range(len(d1) - 5) if d1[i] == 0xe8
             and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == s['clearhold']]
    assert len(calls) == 3, calls
    assert d1[calls[0] - 2] != 0x74 and d1[calls[1] - 2] == 0x74 and d1[calls[2] - 2] == 0x74
    s['pick'] = [(calls[0], 'w_pick_cc', None)] + [(c, n, c + struct.unpack_from('<b', d1, c - 1)[0])
                                                   for c, n in zip(calls[1:], ('w_pick_cwc', 'w_pick_uefa'))]
    s['regs'] = dict(D0R=D0, D7R=D7, A0R=A0, A1R=A1, A5R=A0 + 20, A6R=A6)
    return s


def struct_for(p, key, euro, rounds, clubs):
    """World European cup struct: CWC layout (header, rounds, 0, name dwords, (file, ordinal) pairs) with the
    original cup's id, dates and names, padded to the in-save copy size."""
    obj, off = euro
    d = bytes(p.get(obj, off, 100))
    import sacups
    d2 = p.le.obj_bytes(2)
    cwc = d2[sacups.unique(d2, sacups.CWC_HDR):][:14]
    h = bytearray(cwc)
    h[0] = d[0]
    h[10] = len(clubs)
    h += bytes(rounds) + b'\0'
    h[5] = len(h) - 5
    h[7] = len(h) + 8 - 7
    names = d[5 + d[5]:5 + d[5] + 8]
    body = bytes(h) + names + b''.join(bytes(c) for c in clubs)
    assert len(body) <= COPY[key], (key, len(body))
    return body.ljust(COPY[key], b'\0')


def patch(p, worlds, at, nasmcave, comp, ct, cont_rec):
    """worlds: [{'n', 'countries': [file], 'map': {file: world}, 'cups': {key: (rounds, [(file, ordinal)])},
    'places': {key: [country file per place]}, 'tmd': name}]. Returns the cave end."""
    s = sites(p)
    data = ['align 4', 'WTAB:']
    extra = []
    for w in worlds:
        n = w['n']
        tot = sum(len(w['cups'][k][1]) for k in ('cc', 'cwc', 'uefa'))
        assert tot <= 80
        data.append(f'    dd W{n}_CC, W{n}_CWC, W{n}_UEFA, W{n}_TMD, W{n}_LIST, W{n}_TCC, W{n}_TCWC, W{n}_TUEFA')
        data.append('    dw %d, %d, %d, %d, %d' % (tot, len(w['cups']['cc'][1]), len(w['cups']['cwc'][1]),
                                                  len(w['cups']['uefa'][1]), tot - 3))   # before the 3 holders
        data.append(f"    db {w['year'] - 1900}, 0")
        data.append(f'    dd W{n}_CONT')
        extra.append(f'W{n}_CONT: dd CCCOPY, CWCCOPY, UEFACOPY, -1')   # world view: the in-save cups
        extra.append('    db ' + ', '.join(map(str, w['countries'] + [0xff])))
        for key, euro in zip(('cc', 'cwc', 'uefa'), s['euro']):
            rounds, clubs = w['cups'][key]
            body = struct_for(p, key, euro, rounds, clubs)
            extra.append(f'W{n}_{key.upper()}: db ' + ', '.join(map(str, body)))
            pl = w['places'][key]               # one group: every listed place is taken (n = take)
            extra.append(f'W{n}_T{key.upper()}: dd W{n}_P{key.upper()}')
            extra.append(f'    dw {len(pl)}, {len(pl)}')
            extra.append('    dd -1')
            extra.append(f'W{n}_P{key.upper()}: db ' + ', '.join(map(str, pl)))
        extra.append(f'W{n}_LIST: db ' + ', '.join(map(str, w['countries'] + [0xff])))
        extra.append(f'W{n}_TMD: db "data\\\\{w["tmd"].lower()}", 0')
    pairs = [x for w in worlds for f in w['countries'] for x in (f, w['n'])]
    extra.append('WMAP: db ' + ', '.join(map(str, pairs + [0xff])))
    src = ASM + '\n'.join(data + extra) + '\n'
    vobj, vtab = p.target(2, comp + 4 * 254)
    assert ct + 4 * WCONT not in {f[1] for f in p.le.fixups() if f[0] == 2} and p.get(2, comp + 4 * WCONT, 4) == bytes(4)
    p.add_ptr(2, ct + 4 * WCONT, *cont_rec)        # continent button name (the CLASSIC CAREERS record)
    sym = {k: (2, v) for k, v in s['regs'].items()}
    sobj, slt = s['slt']
    sym.update({'SLT': (sobj, slt), 'SLTCOPY': s['sltcopy'], 'WORLD_BYTE': (0, WORLD_BYTE), 'REC': (0, REC),
                'LOADEURO': (1, s['loadeuro']), 'KNOWN': (1, s['known']), 'TEAMSLOADED': (2, s['teamsloaded']),
                'CCCOPY': s['copies'][0][0],
                'CWCCOPY': s['copies'][1][0], 'UEFACOPY': s['copies'][2][0],
                'SEASONLIST': s['seasonlist'], 'CFB': (2, s['cfb']),
                'CNT_CC': (2, s['cnt'][0]), 'CNT_CWC': (2, s['cnt'][1]), 'CNT_UEFA': (2, s['cnt'][2]),
                'CCTAB': (2, s['tabs'][0][2]), 'CWCTAB': (2, s['tabs'][1][2]), 'UEFATAB': (2, s['tabs'][3][2]),
                'WCONT': (0, WCONT), 'SEASONPLAYING': (2, s['season']), 'COMP254': (2, comp + 4 * 254),
                'COMP99': (2, comp + 4 * WCONT), 'VIEWFIRST': p.target(vobj, vtab), 'CHOOSECOMP': (1, s['choosecomp']),
                'CHOOSETEAMS': (1, s['chooseteams']), 'LASTNAT': (2, s['lastnat']), 'HOLDERS': (1, s['holders']),
                'ADDREC': (1, s['addrec']), 'CLEARHOLD': (1, s['clearhold']),
                'LOOP_CWC': (1, s['pick'][1][2]), 'LOOP_UEFA': (1, s['pick'][2][2])})
    for key, (hold, buf, lst, cnt) in zip(('CC', 'CWC', 'UEFA'), s['hold']):
        sym.update({f'HOLD_{key}': (2, hold), f'BUF_{key}': (2, buf), f'LIST_{key}': (2, lst)})
        assert cnt == s['cnt'][('CC', 'CWC', 'UEFA').index(key)]
    code, fix = nasmcave.assemble(src, at, sym)
    labels = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)

    def hook(site, length, label, fixups):
        for f in fixups:
            p.remove(1, site + f)
        p.put(1, site, b'\xe8' + struct.pack('<i', labels[label] - (site + 5)) + b'\x90' * (length - 5))

    hook(s['entry'], 12, 'w_entry', (2, 8))
    hook(s['load'][0], 5, 'w_load1', ())
    hook(s['load'][1], 5, 'w_load23', ())
    hook(s['load'][2], 5, 'w_load23', ())
    hook(s['cups'], 9, 'w_cups', (3,))
    hook(s['list'], 10, 'w_list', (2, 6))
    for site, name in s['chk']:
        hook(site, 8, name, (3,))
    for site, name, _ in s['tabs']:
        hook(site, 5 if name == 'w_uefa0' else 10, name, (1,) if name == 'w_uefa0' else (2, 6))
    hook(s['holders_call'], 5, 'w_holders', ())
    hook(s['y96'], 9, 'w_year96', (3,))
    hook(s['y95'], 9, 'w_year95', (3,))
    hook(s['view'], 5, 'w_view', ())
    hook(s['buy'], 5, 'w_buy', ())
    hook(s['nat'], 12, 'w_nat', (2, 8))
    for site, name, _ in s['pick']:
        hook(site, 5, name, ())
    return (at + len(code) + 3) & ~3
