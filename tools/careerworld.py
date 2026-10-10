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
import os
import re
import struct

TEAM_SIZE = 684
COPY = {'cc': 79, 'cwc': 92, 'uefa': 92}           # in-save struct copies
SMALL = {'cc': 16, 'cwc': 32, 'uefa': 32}           # what fits the in-save copies and the 80 records
MAX = {'cc': 32, 'cwc': 32, 'uefa': 64}             # big worlds (euro 128): a type-1 cup holds 64 clubs at most
TOTAL_MAX = 128
BIGCOPY = {'cc': 92, 'cwc': 92, 'uefa': 160}        # CWC layout: 22 + rounds + 2 B per club
WORLD_BYTE = 1845                                    # someLeaguesTable index (+1 = balance byte)
REC = 52                                             # world record: 8 dwords, 5 words, year byte, pad, 2 dwords
# Big world (more than 80 European clubs or a cup above SMALL): the 128 records, the 3 cups and the 3 working place
# lists move to a zero-filled tail of obj2 (BSS[0] = its first offset, set by patch.py; obj2's virtual size grows by
# BSS_SIZE). The .CAR's 80-record area (fixed part) holds a 'W1' block instead: the 3 cups + per record its (file,
# ordinal) word and the bytes the game changes (VAROFF); load rebuilds all records from the TEAM files. (Not after the
# C7 trailer: a world career caches ~92 teams, so the 68400-B room is nearly full.) Normal careers never take these
# paths.
BSS = [None]
BSS_SIZE = 0x27000
B_TMD, B_CUPS, B_LISTS = 0, 128 * TEAM_SIZE, 128 * TEAM_SIZE + 3 * 160      # cups 160 B apart, lists 64 / 64 / 96
# SaveSelectedTeams / RestoreSelectedTeams park the career's team cache while a contest is simulated (season end):
# the game keeps only its first 32 records (21888 B in DOS memory at dosMemOfs60c00h), the simulated contest reuses
# the cache, so records 32+ come back as the simulated clubs (a 64-club national cup lost its second half -> the
# season end's VerifyTeamLoaded on a finalist -> exit to DOS; world 1984-85, 2026-10-10). A big world parks all 100
# records (count word + 68400 B) at B_SAVE.
B_SAVE, SAVE_SIZE = 0x16000, 2 + 100 * TEAM_SIZE
assert B_LISTS + 224 <= B_SAVE and B_SAVE + SAVE_SIZE <= BSS_SIZE
VAROFF = [4, 22, 25] + [76 + 38 * k + x for k in range(16) for x in (1, 27, 33, 34, 35, 36)]
WMARK = 0x3157                                       # 'W1'
WBLOCK = 2 + sum(BIGCOPY.values()) + TOTAL_MAX * (2 + len(VAROFF))   # in the fixed part's 80-record area
assert WBLOCK <= 80 * TEAM_SIZE
LABELS = {}


def big(w):
    tot = sum(len(w['cups'][k][1]) for k in ('cc', 'cwc', 'uefa'))
    return tot > 80 or any(len(w['cups'][k][1]) > SMALL[k] for k in SMALL)
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

w_big:                                  ; ZF = 0 in a big world (records, cups and place lists moved)
    push ebx
    call w_rec
    jz .r
    cmp byte [ebx + 48], 0
.r:
    pop ebx
    ret

w_dcopy:                                ; ecx dwords esi -> edi
    mov eax, [esi]
    mov [edi], eax
    add esi, 4
    add edi, 4
    dec ecx
    jnz w_dcopy
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
    cmp byte [ebx + 48], 0
    jne .big
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
    jmp .y
.big:                                   ; big world: the cups live in the obj2 tail (the copies stay unused)
    mov esi, [ebx]
    mov edi, WCC
    mov ecx, 92
    call w_copy
    mov esi, [ebx + 4]
    mov edi, WCWC
    mov ecx, 92
    call w_copy
    mov esi, [ebx + 8]
    mov edi, WUEFA
    mov ecx, 160
    call w_copy
.y:
    mov al, [ebx + 42]                  ; the world's first season (InitCareer: -1, then InitializeNewSeason: +1)
    mov [SEASONPLAYING], al
.r:
    popad
    ret

w_list:                                 ; replaces `mov dword [A6], seasonEndList` in cseg_91428
%ifdef DIAG
    mov dword [DG_TICKS], 0             ; diagnostic build: the timer watchdog dumps if the season end hangs
    mov byte [DG_ARMED], 1
%endif
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
%ifdef DIAG
DG_TICKS: dd 0
DG_ARMED: db 0, 0, 0, 0
%endif
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
    # euro 128: every `mov [Ax], offset X` of tmdFileBuffer, the 3 in-save copies and the 3 working place lists
    # (cseg_936C0 writes them, cseg_939C9 / 939FE / 93A60 read them), and dseg_C707E (contests whose clubs come from
    # the tmd buffer: cseg_87DA0 sets DIY [3Bh] = 0 for them)
    fx = list(p.le.fixups())

    def movs(t):
        return [(f[1] - 6, f[1] - 4) for f in fx if f[0] == 1 and f[3] == 2 and f[4] == t
                and orig[f[1] - 6:f[1] - 4] == b'\xc7\x05']
    s['tmd'] = s['cfb'] + 2
    s['tmd_sites'] = movs(s['tmd'])
    assert len(s['tmd_sites']) == 8, s['tmd_sites']
    s['copy_sites'] = [movs(dst[1]) for dst, _ in s['copies']]
    assert [len(x) for x in s['copy_sites']] == [4, 4, 4], s['copy_sites']
    s['lists'] = []
    for k in (0, 1, 3):                                      # cc, cwc, uefa place-table sites: `mov [A1], list` next
        site = s['tabs'][k][0] + 10
        assert orig[site:site + 6] == b'\xc7\x05' + struct.pack('<I', A1), orig[site:site + 10].hex()
        s['lists'].append(p.target(1, site + 6)[1])
    s['list_sites'] = [movs(t) for t in s['lists']]
    assert [len(x) for x in s['list_sites']] == [2, 2, 2], s['list_sites']
    tobj_, tab_ = p.target(1, s['load'][2] + 5 + 6)          # careerContests
    srcs = [f[1] for f in fx if f[0] == 2 and f[3] == 2 and f[4] == s['copies'][0][0][1]]
    srcs = [x for x in srcs if not tab_ <= x < tab_ + 0x100]
    assert len(srcs) == 1, srcs
    base = srcs[0] - 16
    s['clist'] = []
    k = base
    while struct.unpack_from('<i', p.get(2, k, 4))[0] != -1:
        s['clist'].append(p.target(2, k))
        k += 4
    s['clist_refs'] = [f[1] for f in fx if f[0] == 1 and f[3] == 2 and f[4] == base]
    assert len(s['clist_refs']) == 3 and all(orig[x - 6:x - 4] == b'\xc7\x05' for x in s['clist_refs'])
    s['regs'] = dict(D0R=D0, D7R=D7, A0R=A0, A1R=A1, A5R=A0 + 20, A6R=A6)
    return s


def struct_for(p, key, euro, rounds, clubs, size=None):
    """World European cup struct: CWC layout (header, rounds, 0, name dwords, (file, ordinal) pairs) with the
    original cup's id, dates and names, padded to the in-save copy size (size: a big world's buffer)."""
    obj, off = euro
    d = bytes(p.get(obj, off, 100))
    import sacups
    d2 = p.le.obj_bytes(2)
    cwc = d2[sacups.unique(d2, sacups.CWC_HDR):][:14]
    h = bytearray(cwc)
    h[0] = d[0]
    h[10] = len(clubs)
    h[8] = 0            # 0 = first round drawn at random (1 = the list order: the season end fills the lists country
                        # by country, so a country's UEFA clubs met each other; seen by Daniele Bordes, 2026-10-10)
    h += bytes(rounds) + b'\0'
    h[5] = len(h) - 5
    h[7] = len(h) + 8 - 7
    names = d[5 + d[5]:5 + d[5] + 8]
    body = bytes(h) + names + b''.join(bytes(c) for c in clubs)
    size = size or COPY[key]
    assert len(body) <= size, (key, len(body))
    return body.ljust(size, b'\0')


def patch(p, worlds, at, nasmcave, comp, ct, cont_rec):
    """worlds: [{'n', 'countries': [file], 'map': {file: world}, 'cups': {key: (rounds, [(file, ordinal)])},
    'places': {key: [country file per place]}, 'tmd': name}]. Returns the cave end."""
    import sacups
    s = sites(p)
    data = ['align 4', 'WTAB:']
    extra = []
    nrec = 0
    for w in sorted(worlds, key=lambda w: w['n']):
        n = w['n']
        while nrec < n - 1:                     # WTAB is indexed by the world number (= the byte in the save)
            nrec += 1
            data.append(f'    times {REC} db 0                ; world {nrec}: not in this build')
        nrec += 1
        tot = sum(len(w['cups'][k][1]) for k in ('cc', 'cwc', 'uefa'))
        bw = big(w)
        assert tot <= TOTAL_MAX and all(len(w['cups'][k][1]) <= (MAX if bw else SMALL)[k] for k in MAX), (n, tot)
        data.append(f'    dd W{n}_CC, W{n}_CWC, W{n}_UEFA, W{n}_TMD, W{n}_LIST, W{n}_TCC, W{n}_TCWC, W{n}_TUEFA')
        data.append('    dw %d, %d, %d, %d, %d' % (tot, len(w['cups']['cc'][1]), len(w['cups']['cwc'][1]),
                                                  len(w['cups']['uefa'][1]), tot - 3))   # before the 3 holders
        data.append(f"    db {w['year'] - 1900}, 0")
        data.append(f'    dd W{n}_CONT, {int(bw)}')
        extra.append(f'W{n}_CONT: dd ' + ('WCC, WCWC, WUEFA' if bw else 'CCCOPY, CWCCOPY, UEFACOPY') + ', -1')
        extra.append('    db ' + ', '.join(map(str, w['countries'] + [0xff])))
        for key, euro in zip(('cc', 'cwc', 'uefa'), s['euro']):
            rounds, clubs = w['cups'][key]
            body = struct_for(p, key, euro, rounds, clubs, BIGCOPY[key] if bw else None)
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
    anybig = any(big(w) for w in worlds)
    stubs, bsym, hooks, saves = [], {}, [], []
    if anybig:                                   # euro 128: the moved buffers, one stub per `mov [Ax], offset X`
        assert BSS[0], 'big world: patch.py must give obj2 a zero-filled tail (careerworld.BSS)'
        b = BSS[0]
        groups = [(s['tmd_sites'], [(2, s['tmd'])], [b + B_TMD])]
        groups += [(sites_, [s['copies'][k][0]], [b + B_CUPS + 160 * k]) for k, sites_ in enumerate(s['copy_sites'])]
        groups += [(sites_, [(2, s['lists'][k])], [b + B_LISTS + (0, 64, 128)[k]])
                   for k, sites_ in enumerate(s['list_sites'])]
        i = 0
        for sites_, (normal,), (moved,) in groups:
            for site, regoff in sites_:
                reg = p.target(1, regoff)[1]
                stubs += [f'wp{i}:', '    pushfd', '    push eax', f'    mov eax, PN{i}', '    call w_big', '    jz .o',
                          f'    mov eax, PW{i}', '.o:', f'    mov [PR{i}], eax', '    pop eax', '    popfd', '    ret']
                bsym.update({f'PN{i}': normal, f'PW{i}': (2, moved), f'PR{i}': (2, reg)})
                hooks.append((site, f'wp{i}'))
                i += 1
        orig1 = p.le.obj_bytes(1)
        d1 = bytes(p.get(1, 0, len(orig1)))
        rg = sacups.regs(orig1)
        pk = lambda x: re.escape(struct.pack('<I', x))
        a0, a1 = rg['A0'], rg['A0'] + 4
        for k, pat in enumerate((                # SaveSelectedTeams, RestoreSelectedTeams
                rb'\xa1.{4}\xa3' + pk(a1) + rb'\x8b\x35' + pk(a1) + rb'\x66\xa1.{4}\x66\x89\x06\x83\x05' + pk(a1)
                + rb'\x02(\xc7\x05.{4}\x80\x55\x00\x00)',
                rb'\xa1.{4}\xa3' + pk(a0) + rb'\xa1.{4}\xa3' + pk(a1) + rb'\x8b\x35' + pk(a0) + rb'\x66\x8b\x06\x66\xa3.{4}\x83\x05' + pk(a0)
                + rb'\x02(\xc7\x05.{4}\x80\x55\x00\x00)')):
            m = _one(pat, d1, ('SaveSelectedTeams', 'RestoreSelectedTeams')[k])
            src_site, len_site = m.start(), m.start(1)
            stubs += [f'ws{k}:', '    mov eax, [SVMEM]', '    pushfd', '    call w_big', '    jz .o',
                      '    mov eax, WSAVE', '.o:', '    popfd', '    ret',
                      f'wl{k}:', '    mov dword [SVD0], 21888', '    pushfd', '    call w_big', '    jz .o',
                      f'    mov dword [SVD0], {SAVE_SIZE - 2}', '.o:', '    popfd', '    ret']
            bsym.update({'SVMEM': p.target(1, src_site + 1), 'SVD0': p.target(1, len_site + 2)})
            saves.append((src_site, f'ws{k}', len_site, f'wl{k}'))
        bsym['WSAVE'] = (2, b + B_SAVE)
        stubs += ['align 4', 'WCLIST: dd ' + ', '.join(f'CL{k}' for k in range(len(s['clist'])))
                  + ', WCC, WCWC, WUEFA, -1']
        bsym.update({f'CL{k}': t for k, t in enumerate(s['clist'])})
    b = BSS[0] or 0
    bsym.update({'WTMD': (2, b + B_TMD), 'WCC': (2, b + B_CUPS), 'WCWC': (2, b + B_CUPS + 160),
                 'WUEFA': (2, b + B_CUPS + 320)})
    src = ASM + '\n'.join(stubs + data + extra) + '\n'
    if os.environ.get('DIAG'):
        src = '%define DIAG\n' + src
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
    sym.update(bsym)
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
    for site, name in hooks:                     # euro 128 (big worlds only)
        hook(site, 10, name, (2, 6))
    for src_site, src_name, len_site, len_name in saves:   # big worlds: park all 100 cached teams
        hook(src_site, 5, src_name, (1,))
        hook(len_site, 10, len_name, (2,))
    if anybig:
        for ref in s['clist_refs']:
            p.retarget(1, ref, 1, labels['WCLIST'])
    LABELS.clear()
    LABELS.update(labels)
    LABELS['big'] = anybig
    LABELS['sites'] = s
    LABELS['end'] = (at + len(code) + 3) & ~3
    return LABELS['end']


TAILS_ASM = '''
w_save_tail:                            ; SaveCareerFile after save_trailer (trailer.SAVE_TAIL)
    call w_big
    jnz .w
    jmp WRITEFILE
.w:
    pushad                              ; the fixed part's 80-record area (tmdFileBuffer, unused in a big world) gets
    mov edi, TMDBUF                     ; the W1 block: the 3 cups + per record its (file, ordinal) word + VAROFF bytes
    mov word [edi], WMARK
    add edi, 2
    mov esi, WCC
    mov ecx, 92
    call w_copy
    mov esi, WCWC
    mov ecx, 92
    call w_copy
    mov esi, WUEFA
    mov ecx, 160
    call w_copy
    mov dword [WI], 0
.rec:
    mov esi, [WI]
    imul esi, esi, 684
    add esi, WTMD
    mov ax, [esi]
    mov [edi], ax
    add edi, 2
    mov ebx, VAROFFS
    mov ecx, VARN
.v:
    movzx eax, word [ebx]
    mov dl, [esi + eax]
    mov [edi], dl
    inc edi
    add ebx, 2
    dec ecx
    jnz .v
    inc dword [WI]
    cmp dword [WI], 128
    jb .rec
    popad
    jmp WRITEFILE

w_load_tail:                            ; LoadCareerFile after load_trailer (trailer.LOAD_TAIL)
    call w_big
    jnz .w
    jmp PROCESS
.w:
    pushad
    mov esi, TMDBUF
    cmp word [esi], WMARK
    jne .x
    add esi, 2
    mov edi, WCC
    mov ecx, 92
    call w_copy
    mov edi, WCWC
    mov ecx, 92
    call w_copy
    mov edi, WUEFA
    mov ecx, 160
    call w_copy
    mov [WPTR], esi
    mov dword [WI], 0
.rec:                                   ; every record from its TEAM file + the saved bytes
    movzx eax, word [CFB]
    cmp [WI], eax
    jae .x
    mov esi, [WPTR]
    movzx eax, word [esi]
    mov [WPAIR], eax
    mov [D0R], eax
    call LOADTEAM                       ; D0 = country file (low byte): data\\team.nnn -> teamFileBuffer, division
    mov esi, TEAMBUF + 2                ; numbers from this save's someLeaguesTable, global numbers set
    mov ecx, 94
.s:
    mov ax, [esi]
    cmp ax, [WPAIR]
    je .f
    add esi, 684
    dec ecx
    jnz .s
    jmp .n                              ; not in its file (cannot happen with an unchanged world)
.f:
    mov edi, [WI]
    imul edi, edi, 684
    add edi, WTMD
    push edi
    mov ecx, 684
    call w_copy
    pop edi
    mov esi, [WPTR]
    add esi, 2
    mov ebx, VAROFFS
    mov ecx, VARN
.v:
    movzx eax, word [ebx]
    mov dl, [esi]
    mov [edi + eax], dl
    inc esi
    add ebx, 2
    dec ecx
    jnz .v
.n:
    add dword [WPTR], 2 + VARN
    inc dword [WI]
    jmp .rec
.x:
    mov word [TEAMSLOADED], 0           ; teamFileBuffer holds another file now: force a reload
    popad
    jmp PROCESS

%ifdef DIAG
diag_install:                           ; DPMI: protected-mode int 3 and int 8 (timer watchdog) handlers, once
    cmp byte [DGDONE], 0
    jne .r
    mov byte [DGDONE], 1
    pushad
    mov [DGDS], ds
    mov ax, 0204h
    mov bl, 8
    int 31h
    mov [OLD8], edx
    mov [OLD8 + 4], cx
    mov ax, 0205h
    mov bl, 8
    mov cx, cs
    mov edx, diag8
    int 31h
    mov ax, 0205h
    mov bl, 3
    mov cx, cs
    mov edx, diag3
    int 31h
    popad
.r:
    ret

diag3:
    pushad
    push ds
    push es
    mov ax, [cs:DGDS]
    mov ds, ax
    mov es, ax
    mov eax, [esp + 40]
    mov byte [DGEIP + 8], 3
    call diag_dump
    pop es
    pop ds
    popad
    iretd

diag8:
    pushad
    push ds
    push es
    mov ax, [cs:DGDS]
    mov ds, ax
    mov es, ax
    cmp byte [DG_ARMED], 0
    je .c
    inc dword [DG_TICKS]
    cmp dword [DG_TICKS], 364           ; ~20 s after the season end started
    jne .c
    mov eax, [esp + 40]
    mov byte [DGEIP + 8], 8
    call diag_dump
.c:
    pop es
    pop ds
    popad
    jmp far [cs:OLD8]

diag_dump:                              ; eax = interrupted EIP -> DIAG.BIN
    mov [DGEIP], eax
    mov dword [DGEIP + 4], diag3
    mov ah, 3Ch
    xor ecx, ecx
    mov edx, DGNAME
    int 21h
    jc .r
    movzx ebx, ax
    mov esi, DGBLK
.b:
    mov edx, [esi]
    test edx, edx
    jz .c
    mov ecx, [esi + 4]
    mov ah, 40h
    push esi
    push ebx
    int 21h
    pop ebx
    pop esi
    add esi, 8
    jmp .b
.c:
    mov ah, 3Eh
    int 21h
.r:
    ret

align 4
OLD8: dd 0, 0
DGDS: dd 0
DGDONE: dd 0
DGEIP: dd 0, 0, 0
DGBLK: dd DGEIP, 12, DREGS, 32, AREGS, 28, CFB, 2, HOLDREG, 0C0h, WCC, 2C0h, 0, 0
DGNAME: db "DIAG.BIN", 0
%endif
align 4
WI: dd 0
WPTR: dd 0
WPAIR: dd 0
VAROFFS: VAROFF_WORDS
'''


def patch_tails(p, at, nasmcave):
    """Big worlds: the save / load tails of the .CAR trailer ('W1' block after C7). Call after trailer.patch(tails=True).
    Returns the cave end."""
    import trailer
    t, s = trailer.INFO, LABELS['sites']
    orig = p.le.obj_bytes(1)
    # GetTeamPointer: call FindTeamInCache; jz; call SearchTeamInTmdFile; jz; mov ax,[D0]; mov [D2],ax; call LoadTeamFile;
    # mov [A0], offset teamFileBuffer + 2
    D0, A0 = s['regs']['D0R'], s['regs']['A0R']
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = _one(rb'\x66\xa1' + pk(D0) + rb'\x66\xa3.{4}\xe8(.{4})\xc7\x05' + pk(A0), orig, 'GetTeamPointer')
    load_team = m.end() - 6 + struct.unpack('<i', m.group(1))[0]
    team_buf = p.target(1, m.end())
    sym = {'WRITEFILE': t['WRITEFILE'], 'PROCESS': t['PROCESS'], 'NUMSEL': t['NUMSEL'], 'CAREER': t['CAREER'],
           'D1R': t['D1'], 'TBLOCK': t['BLOCK'], 'FIXED': t['FIXED'], 'ROOM': t['ROOM'], 'TMARK': t['MARK'],
           'WBLOCK': (0, WBLOCK), 'WMARK': (0, WMARK), 'VARN': (0, len(VAROFF)),
           'VAROFF_WORDS': (0, 'dw ' + ', '.join(map(str, VAROFF))),
           'TMDBUF': (2, s['tmd']), 'CFB': (2, s['cfb']), 'D0R': (2, D0), 'LOADTEAM': (1, load_team),
           'TEAMBUF': (team_buf[0], team_buf[1] - 2), 'TEAMSLOADED': (2, s['teamsloaded']),
           'w_big': (1, LABELS['w_big']), 'w_copy': (1, LABELS['w_copy']), 'w_dcopy': (1, LABELS['w_dcopy'])}
    b = BSS[0]
    sym.update({'WTMD': (2, b + B_TMD), 'WCC': (2, b + B_CUPS), 'WCWC': (2, b + B_CUPS + 160),
                'WUEFA': (2, b + B_CUPS + 320)})
    src = TAILS_ASM
    if os.environ.get('DIAG'):                   # diagnostic build: int 3 handler writes DIAG.BIN
        src = '%define DIAG\n' + src.replace('.w:\n    pushad\n    mov esi, TMDBUF', '.w:\n    call diag_install\n    pushad\n    mov esi, TMDBUF')
        sym.update({'DREGS': (2, D0 - 0), 'AREGS': (2, A0), 'HOLDREG': (2, s['hold'][0][0] - 0x10),
                    'DG_TICKS': (1, LABELS['DG_TICKS']), 'DG_ARMED': (1, LABELS['DG_ARMED'])})
    code, fix = nasmcave.assemble(src, at, sym)
    labels = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    save_dd, load_dd = t['tails']
    p.retarget(1, save_dd, 1, labels['w_save_tail'])
    p.retarget(1, load_dd, 1, labels['w_load_tail'])
    print(f'exe: big world .CAR block W1 ({WBLOCK} B, in the 80-record area) @ obj1+{at:#x}, records moved to obj2+{b:#x}')
    return (at + len(code) + 3) & ~3


def late(p, at, nasmcave):
    """After arg97.late: in a world the season end skips the 1996-97 qualifier simulations (arg_agg -> sa_qualify:
    South America, CAF, Asia, CONCACAF, Argentina) and calls cseg_92D55 directly. Those simulations read
    someLeaguesTable at the global numbers of their clubs, which a world's clubs reuse (bases 0..): after the world's
    promotions a simulated division has the wrong club count and cseg_3283C traps (seen: euro 128 test, season 2 end,
    after PARAGUAY). Returns the cave end."""
    orig = p.le.obj_bytes(1)
    d1 = bytes(p.get(1, 0, len(orig)))
    site = [i for i in range(len(orig) - 24) if orig[i] == 0xe8 and orig[i + 5] == 0xe8 and orig[i + 10] == 0xe8
            and orig[i + 15:i + 18] == b'\x66\xc7\x05' and orig[i + 22:i + 24] == b'\x00\x00'
            and orig[i + 24:i + 26] == b'\x66\xa1']
    tgt = lambda d, i: i + 5 + struct.unpack_from('<i', d, i + 1)[0]
    site = [i for i in site if 0 < tgt(orig, i + 5) - tgt(orig, i) < 0x1000 and 0 < tgt(orig, i + 10) - tgt(orig, i + 5) < 0x1000]
    assert len(site) == 1, site
    site = site[0]
    c92d55, cur = tgt(orig, site), tgt(d1, site)
    assert cur != c92d55, 'sacups / arg97 not applied yet'
    # cseg_92D55 ends the Champions Cup as the 1996-97 group cup (type 2): played -> cseg_89B5C, simulated ->
    # cseg_3ADAE (whose cseg_320A3 reads the club count at byte 15). A world's Champions Cup is a knockout (type 1)
    # like the CWC: cseg_9307A uses cseg_45B51 / cseg_3ACAB. The winner readers (cseg_92F1C / cseg_93241) are alike.
    c9307a = tgt(orig, site + 5)

    def calls(at, n):
        out, i = [], at
        while len(out) < n:
            if orig[i] == 0xe8:
                out.append((i, tgt(orig, i)))
                i += 5
            else:
                i += 1
            assert i < at + 0x200
        return out
    cc, cw = calls(c92d55, 6), calls(c9307a, 6)
    assert [t for _, t in cc[:2]] == [t for _, t in cw[:2]] and cc[4][1] == cw[4][1], (cc, cw)
    play_site, sim_site = cc[2][0], cc[5][0]
    assert tgt(d1, play_site) == cc[2][1] and tgt(d1, sim_site) == cc[5][1], 'cseg_92D55 calls already hooked'
    src = '''
w_cc_play:                              ; cseg_92D55: the player's Champions Cup -> knockout play-out in a world
    push ebx
    call w_rec
    pop ebx
    jz .n
    jmp KO_PLAY
.n:
    jmp GROUP_PLAY

w_cc_sim:                               ; cseg_92D55: a simulated Champions Cup -> knockout simulation in a world
    push ebx
    call w_rec
    pop ebx
    jz .n
    jmp KO_SIM
.n:
    jmp GROUP_SIM

w_season_end:                           ; replaces `call arg_agg` (-> sa_qualify -> cseg_92D55) at the season end
    push ebx
    call w_rec
    pop ebx
    jz .n
    jmp C92D55
.n:
    jmp CUR
'''
    sym = {'w_rec': (1, LABELS['w_rec']), 'C92D55': (1, c92d55), 'CUR': (1, cur), 'KO_PLAY': (1, cw[2][1]),
           'GROUP_PLAY': (1, cc[2][1]), 'KO_SIM': (1, cw[5][1]), 'GROUP_SIM': (1, cc[5][1])}
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', lab['w_season_end'] - (site + 5)))
    p.put(1, play_site + 1, struct.pack('<i', lab['w_cc_play'] - (play_site + 5)))
    p.put(1, sim_site + 1, struct.pack('<i', lab['w_cc_sim'] - (sim_site + 5)))
    print(f'exe: career worlds skip the 1996-97 qualifier simulations: call obj1+{site:#x} -> obj1+{at:#x}')
    return (at + len(code) + 3) & ~3
