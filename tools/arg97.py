"""Argentina 1996-97: Torneo Apertura 1996 and Torneo Clausura 1997 (session 28p, for 2.1).

Davide's decisions (notes/STATUS.md 28p): two tournaments in one season, relegation by "promedio", Nacional B unchanged,
SA cup qualifiers from the aggregate table. The engine has one league per division, so the Primera's double round-robin is
shown as two tournaments: division 0 is named TORNEO APERTURA; when its first cycle ends (19 rounds: every club has played
n - 1 matches and one cycle is left, DIY [5Fh] == 1) arg_after records the Apertura champion, zeroes the 20 table entries and
renames the running league TORNEO CLAUSURA (at the first match of the second cycle, session 28p T12). Steps still to come: aggregate + promedio + save trailer + message/history.
Sources: RSSSF arg97 (Apertura 1996, Clausura 1997), es.wikipedia "Campeonato de Primera Division 1996-97 (Argentina)".
"""
import re
import struct

import nasmcave

FILE = 43
LEAGUE_SIG = bytes((0x56, 0, 0x2B, 0x40, 0x20, 0, 0, 0, 0, 2, 2, 3, 0x35))
NAMES = [(b'TORNEO APERTURA', b'APERTURA'), (b'NACIONAL B', b'NACIONAL B')]
CLAUSURA = b'TORNEO CLAUSURA'

ASM = r'''
; The Primera is recognised by its name pointer DIY+27h (TORNEO APERTURA / TORNEO CLAUSURA: no other league has them).
; The struct's names (long, short: the career game list shows the short one) change only at three moments: the switch
; (arg_round), every new season (arg_prebuild: APERTURA) and a career load (arg_load -> arg_names, phase of the saved
; league). T16/T17 also synced after every match: during career creation that showed CLAUSURA once.
arg_ours:                               ; ebp = league buffer; ZF = 1 if it is the Argentine Primera
    cmp dword [ebp + 27h], AP_LONG
    je .r
    cmp dword [ebp + 27h], CL_LONG
.r:
    ret

arg_names:                              ; ebp = league buffer (DIY during a matchday, the career slot 0 after a load)
    call arg_ours
    jne .r
    pushad
    mov eax, AP_LONG_OFF
    mov edx, AP_SHORT_OFF
    cmp word [ebp + 31h], 0             ; empty buffer: Apertura
    je .set
    cmp word [ebp + 5Fh], 1             ; cycles left: 2 = Apertura, 1 or 0 = Clausura
    ja .set
    mov eax, CL_LONG_OFF
    mov edx, CL_SHORT_OFF
.set:
    mov [NAME_DW], eax
    mov [NAME_DW + 4], edx
    popad
.r:
    ret

; arg_round: replaces `mov dword [A0], offset DIY_competitionStart` at the start of cseg_8922B, the per-match counters of a
; league: for every match the engine first counts it as played here, THEN adds the result to the table. The calendar
; building calls this routine too, but with the results counters at 0. First match of the second cycle ([5Fh] 1, nothing
; counted in this cycle yet): every club has 19 played AND 19 results = the Apertura is over and the table still holds it
; -> champion, table reset, TORNEO CLAUSURA; then this match is counted into a clean table.
arg_round:
    mov dword [A0], DIY
    push ebp
    mov ebp, DIY
    call arg_ours
    jne .r
    pushad
    cmp word [DIY + 5Fh], 1             ; one cycle left ...
    jne .x
    cmp word [DIY + 5Bh], 0             ; ... first match of a matchday
    jne .x
    cmp word [DIY + 1CBh], 0            ; ... first matchday of the cycle
    jne .x
    movzx ecx, word [DIY + 31h]         ; clubs
    test ecx, ecx
    jz .x
    lea esi, [ecx - 1]                  ; matches of a cycle
    xor ebx, ebx
.chk:                                   ; every club: n-1 played and n-1 results (won + drawn + lost)
    movzx eax, word [DIY + 6Dh + ebx * 2]
    movzx edx, word [DIY + eax + 2B9h]
    add dx, [DIY + eax + 2BBh]
    add dx, [DIY + eax + 2BDh]
    cmp edx, esi
    jne .x
    movzx edx, word [DIY + eax + 2B7h]
    cmp edx, esi
    jne .x
    inc ebx
    cmp ebx, ecx
    jb .chk
    movzx eax, word [DIY + 6Dh]         ; Apertura champion (top of the sorted table)
    mov esi, [DIY + eax + 2B3h]
    add esi, [SELTEAMS]
    mov ax, [esi]
    mov [AP_CH], ax
    xor ebx, ebx
.zero:
    movzx esi, word [DIY + 6Dh + ebx * 2]   ; row offset (row * 12h)
    mov eax, esi
    xor edx, edx
    push ecx
    mov ecx, 12h
    div ecx
    pop ecx
    mov dx, [DIY + 12Dh + eax * 2]      ; team number of the row
    mov edi, ebx
    shl edi, 4
    add edi, AP_TAB
    mov [edi], dx                       ; AP_TAB entry: team, then played, won, drawn, lost, for, against, points
    add edi, 2
    lea esi, [DIY + esi + 2B7h]
    push ecx
    mov ecx, 7
    rep movsw
    pop ecx
    sub esi, 14
    mov edi, esi                        ; ... and the table row is zeroed
    push ecx
    mov ecx, 7
    xor eax, eax
    rep stosw
    pop ecx
    inc ebx
    cmp ebx, ecx
    jb .zero
    mov [AP_N], cx
    mov dword [DIY + 27h], CL_LONG
    mov eax, 'APER'
    mov edx, 'TURA'
    mov ebx, 'CLAU'
    mov edi, 'SURA'
    call arg_text                       ; the name text the game shows
    push dword [A0]                     ; the manager's record of this season (if his club plays the Primera)
    push dword [D0]                     ; (A0 = DIY for the rest of cseg_8922B; D0 used by GetCurrentSeasonPointer)
    call GETSEASON
    mov esi, [A0]
    cmp dword [esi + 16h], AP_LONG_OFF  ; leagueStringOffset
    jne .p
    mov dword [esi + 16h], CL_LONG_OFF
    cmp byte [AP_CH], ARG_FILE          ; 'CLAUSURA (AP: <champion>)': one fixed text per club (survives save and load)
    jne .p
    movzx eax, byte [AP_CH + 1]
    cmp eax, NCHAMP
    jae .p
    mov eax, [CHAMP_TAB + eax * 4]
    sub eax, CHAIRMAN
    mov [esi + 16h], eax
.p:
    pop dword [D0]
    pop dword [A0]
    mov dword [NAME_DW], CL_LONG_OFF    ; the names the struct gives (career game list: the short one)
    mov dword [NAME_DW + 4], CL_SHORT_OFF
.x:
    popad
.r:
    pop ebp
    ret

arg_text:                               ; in DIY+4.. (name text, maybe country first): eax:edx -> ebx:edi (8 letters)
    lea esi, [DIY + 4]
    mov ecx, 23h - 8
.f:
    cmp [esi], eax
    jne .n
    cmp [esi + 4], edx
    jne .n
    mov [esi], ebx
    mov [esi + 4], edi
    ret
.n:
    inc esi
    loop .f
    ret

; arg_prebuild: replaces the `call cseg_8B2D3` that builds the player's league in InitializeNewSeason (right before the
; GetCurrentSeasonPointer call that stores its name in the season record). A new season starts with the Apertura: the
; struct names go back to TORNEO APERTURA / APERTURA before the build copies them (into DIY+4, DIY+27h, the slot buffer
; and the season record). (T15 renamed after the build: the slot copy kept CLAUSURA.)
arg_prebuild:
    mov word [AP_N], 0                  ; a new season: no Apertura stored yet
    mov word [AP_CH], 0FFFFh
    mov dword [NAME_DW], AP_LONG_OFF
    mov dword [NAME_DW + 4], AP_SHORT_OFF
    jmp BUILD

'''
ASM += r'''
; arg_agg: replaces the season end's `call cseg_92D55` (sacups: sa_qualify, which reads the final tables). The player's
; Argentine Primera: Apertura + Clausura = the aggregate table, re-sorted and put back into season slot 0, so the
; qualifiers, the final table screen and the relegation see the aggregate.
arg_agg:
    pushad
    cmp word [AP_N], 0
    je .go
    mov ebp, SLOT0
    call arg_ours
    jne .go
    mov dword [A0], SLOT0
    call LOAD                           ; slot 0 -> DIY_competitionStart
    movzx ecx, word [DIY + 31h]
    xor ebx, ebx                        ; row
.row:
    mov dx, [DIY + 12Dh + ebx * 2]
    mov esi, AP_TAB
    movzx eax, word [AP_N]
.find:
    cmp [esi], dx
    je .add
    add esi, 16
    dec eax
    jnz .find
    jmp .next
.add:
    lea edi, [ebx + ebx * 8]
    add edi, edi                        ; row * 12h
    lea edi, [DIY + edi + 2B7h]
    add esi, 2
    push ecx
    mov ecx, 7
.addw:
    mov ax, [esi]
    add [edi], ax
    add esi, 2
    add edi, 2
    loop .addw
    pop ecx
.next:
    inc ebx
    cmp ebx, ecx
    jb .row
    call SORT                           ; DIY+6Dh = the aggregate order
    mov dword [A0], SLOT0
    call SAVE                           ; DIY -> slot 0
.go:
    popad
    jmp dword [SAFTER_PTR]              ; sacups' sa_qualify (set by late())

; promedio: points (2 per win) / matches over the last three seasons. PROM = 32 x [team, pts, games, pts, games]
; (two seasons back, last season); TP / TG = this season's totals per row. arg_prom computes the two worst rows.
arg_relegate:                           ; replaces the `call cseg_93FD8` (promotions / relegations of a league)
    pushad
    cmp byte [DIY + 2Dh], ARG_ID
    jne .real
    cmp word [DIY + 57h], 0             ; the Primera: relegations
    je .real
    movzx ecx, word [DIY + 31h]
    cmp ecx, 24
    ja .real
    xor ebx, ebx
.tot:                                   ; per row: P = 2*won + drawn (+ history), G = played (+ history)
    lea edi, [ebx + ebx * 8]
    add edi, edi
    movzx eax, word [DIY + edi + 2B9h]
    add eax, eax
    movzx edx, word [DIY + edi + 2BBh]
    add eax, edx
    movzx edx, word [DIY + edi + 2B7h]
    mov [TP + ebx * 4], eax
    mov [TG + ebx * 4], edx
    mov dx, [DIY + 12Dh + ebx * 2]
    mov esi, PROM
    push ecx
    mov ecx, 32
.hist:
    cmp [esi], dx
    jne .hn
    movzx eax, word [esi + 2]
    movzx edx, word [esi + 6]
    add [TP + ebx * 4], eax
    add [TP + ebx * 4], edx
    movzx eax, word [esi + 4]
    movzx edx, word [esi + 8]
    add [TG + ebx * 4], eax
    add [TG + ebx * 4], edx
    jmp .hd
.hn:
    add esi, 10
    loop .hist
.hd:
    pop ecx
    inc ebx
    cmp ebx, ecx
    jb .tot
    mov edi, -1                         ; edi = worst row, esi = second worst (-1 = none yet)
    mov esi, -1
    xor ebx, ebx
.rank:                                  ; promedio(a) < promedio(b)  <=>  TP[a] * TG[b] < TP[b] * TG[a]
    cmp edi, -1
    je .first
    mov eax, [TP + ebx * 4]
    mul dword [TG + edi * 4]
    mov ebp, eax
    mov eax, [TP + edi * 4]
    mul dword [TG + ebx * 4]
    cmp ebp, eax
    jb .newworst
    cmp esi, -1
    je .second
    mov eax, [TP + ebx * 4]
    mul dword [TG + esi * 4]
    mov ebp, eax
    mov eax, [TP + esi * 4]
    mul dword [TG + ebx * 4]
    cmp ebp, eax
    jb .second
    jmp .rn
.first:
    mov edi, ebx
    jmp .rn
.newworst:
    mov esi, edi
    mov edi, ebx
    jmp .rn
.second:
    mov esi, ebx
.rn:
    inc ebx
    cmp ebx, ecx
    jb .rank
    ; rows edi (worst) and esi (second worst) go to the last two places of the sorted list; the order is restored after
    mov ebx, ecx
    shl ebx, 1
    push ecx
    mov ecx, ebx
    shr ecx, 1
    lea eax, [edi + edi * 8]
    add eax, eax                        ; worst row offset
    lea edx, [esi + esi * 8]
    add edx, edx                        ; second worst row offset
    push eax
    push edx
    xor ebx, ebx
    xor ebp, ebp
.copy:
    movzx edi, word [DIY + 6Dh + ebx * 2]
    mov [ORD_SAVE + ebx * 2], di
    cmp edi, [esp]
    je .skipw
    cmp edi, [esp + 4]
    je .skipw
    mov [ORD_NEW + ebp * 2], di
    inc ebp
.skipw:
    inc ebx
    cmp ebx, ecx
    jb .copy
    pop edx
    pop eax
    mov [ORD_NEW + ebp * 2], dx         ; second worst, then worst, last
    mov [ORD_NEW + ebp * 2 + 2], ax
    xor ebx, ebx
.put:
    mov dx, [ORD_NEW + ebx * 2]
    mov [DIY + 6Dh + ebx * 2], dx
    inc ebx
    cmp ebx, ecx
    jb .put
    pop ecx
    mov [ORD_N], cx
    popad
    pushad
    call REL93
    popad
    pushad
    movzx ecx, word [ORD_N]             ; the finishing order back (qualifiers and the table screens read it later)
    xor ebx, ebx
.back:
    mov dx, [ORD_SAVE + ebx * 2]
    mov [DIY + 6Dh + ebx * 2], dx
    inc ebx
    cmp ebx, ecx
    jb .back
    call arg_prom_update
    popad
    ret
.real:
    popad
    jmp REL93

arg_prom_update:                        ; PROM: this season goes in, the oldest goes out; new clubs get an entry
    movzx ecx, word [DIY + 31h]
    xor ebx, ebx
.clr:
    mov byte [USED + ebx], 0
    inc ebx
    cmp ebx, 32
    jb .clr
    mov esi, PROM
    mov ebp, 32
.e:
    mov dx, [esi]
    cmp dx, 0FFFFh
    je .skipe
    xor ebx, ebx
.srch:
    cmp ebx, ecx
    jae .none
    cmp [DIY + 12Dh + ebx * 2], dx
    je .have
    inc ebx
    jmp .srch
.have:
    mov byte [USED + ebx], 1
    lea edi, [ebx + ebx * 8]
    add edi, edi
    movzx eax, word [DIY + edi + 2B9h]
    add eax, eax
    movzx edx, word [DIY + edi + 2BBh]
    add eax, edx
    movzx edx, word [DIY + edi + 2B7h]
    jmp .shift
.none:
    xor eax, eax
    xor edx, edx
.shift:
    mov bx, [esi + 6]                   ; old <- last season, last season <- this one
    mov [esi + 2], bx
    mov bx, [esi + 8]
    mov [esi + 4], bx
    mov [esi + 6], ax
    mov [esi + 8], dx
.skipe:
    add esi, 10
    dec ebp
    jnz .e
    xor ebx, ebx                        ; rows without an entry (promoted clubs)
.new:
    cmp byte [USED + ebx], 0
    jne .nn
    mov dx, [DIY + 12Dh + ebx * 2]
    mov esi, PROM
    mov ebp, 32
.free:
    cmp word [esi], 0FFFFh
    je .take
    add esi, 10
    dec ebp
    jnz .free
    jmp .nn
.take:
    lea edi, [ebx + ebx * 8]
    add edi, edi
    movzx eax, word [DIY + edi + 2B9h]
    add eax, eax
    movzx ecx, word [DIY + edi + 2BBh]
    add eax, ecx
    mov [esi], dx
    mov word [esi + 2], 0
    mov word [esi + 4], 0
    mov [esi + 6], ax
    mov ax, [DIY + edi + 2B7h]
    mov [esi + 8], ax
.nn:
    inc ebx
    movzx ecx, word [DIY + 31h]
    cmp ebx, ecx
    jb .new
    ret

align 4
SAFTER_PTR: dd 0
CHAMP_TAB: CHAMP_TAB_DD
CHAMP_TEXTS
align 4
AP_BLOCK:
AP_N: dw 0
AP_CH: dw 0FFFFh
AP_TAB: times 20 * 16 db 0
PROM: PROM_BYTES
TP: times 32 dd 0
TG: times 32 dd 0
ORD_SAVE: times 32 dw 0
ORD_NEW: times 32 dw 0
ORD_N: dw 0
USED: times 32 db 0
'''
# promedio history (es.wikipedia "Campeonato de Primera Division 1996-97 (Argentina)", Tabla de descenso, 2 points per
# win, 38 matches a season): SWOS club name (TEAM.043) -> points in 1994-95, 1995-96 (None = not in the Primera)
HISTORY = {
    'BANFIELD': (36, 25), 'BOCA JUNIORS': (41, 49), 'COLON SANTA FE': (None, 35), 'DEP. ESPANOL': (36, 32),
    'ESTUDIANTES': (None, 44), 'FERROCARRIL': (32, 34), 'GIMNASIA JUJUY': (32, 35), 'GIMNASIA-ESGRIMA': (49, 43),
    'HUR. CORRIENTES': (None, None), 'HURACAN': (29, 45), 'INDEPENDIENTE': (37, 35), 'LANUS': (39, 49),
    'NEWELLS OLD BOYS': (59, 44), 'PLATENSE': (35, 32), 'RACING CLUB': (39, 46), 'RIVER PLATE': (49, 37),
    'ROSARIO CENTRAL': (39, 41), 'SAN LORENZO': (56, 35), 'UNION SANTA FE': (None, None), 'VELEZ SARSFIELD': (52, 57),
}
AP_SIZE, PROM_SIZE = 4 + 20 * 16, 32 * 10
ARG_ITEMS = []              # [(obj1 offset, size)] saved in the career trailer (set by patch)


def prom_bytes(src_dir):
    d = open(f'{src_dir}/TEAM.{FILE:03d}', 'rb').read()
    out = b''
    names = {}
    for i in range(struct.unpack('>H', d[:2])[0]):
        names[d[2 + i * 684 + 5:2 + i * 684 + 22].split(b'\0')[0].decode('latin1').strip()] = i
    for name, (a, b) in HISTORY.items():
        team = FILE | (names[name] << 8)
        out += struct.pack('<HHHHH', team, a or 0, 38 if a else 0, b or 0, 38 if b else 0)
    out += struct.pack('<HHHHH', 0xFFFF, 0, 0, 0, 0) * (32 - len(HISTORY))
    assert len(out) == PROM_SIZE
    return out


def champ_texts(src_dir):
    """One text per TEAM.043 club: the Clausura line of the record with the Apertura champion in brackets."""
    d = open(f'{src_dir}/TEAM.{FILE:03d}', 'rb').read()
    n = struct.unpack('>H', d[:2])[0]
    names = [d[2 + i * 684 + 5:2 + i * 684 + 22].split(b'\0')[0].decode('latin1').strip() for i in range(n)]
    return [f'CLAUSURA (AP: {nm[:11].strip()})' for nm in names]


LOAD_ASM = r'''
; arg_load: wraps the call that processes a loaded career (trailer.load_trailer): names in step with the saved league.
arg_load:
    call LOADER
    pushfd
    push ebp
    mov ebp, SLOT0                      ; the player's league as loaded from the .CAR
    call ARG_NAMES
    pop ebp
    popfd
    ret
'''
LABELS = {}
ROUND_HOOK = True
SLOT0 = None


def _refs(p, lo):
    import finals97
    return finals97._refs(p, lo)


def patch(p, area, str_base, at, site_b, src_dir):
    """Named Argentine struct (new obj2 page) + arg_round at obj1:at (hook at the start of cseg_8922B); site_b unused."""
    import sacups
    d2 = p.le.obj_bytes(2)
    lo = d2.find(LEAGUE_SIG)
    assert lo >= 0 and d2.count(LEAGUE_SIG) == 1
    nd = d2[lo + 9]
    body = bytearray(d2[lo:lo + 13 + 6 * nd + 1])
    body[5] = 13 + 6 * nd + 1 - 5                       # names right after the divisions
    ap, cl = [], []                                     # (long, short) obj2 string offsets
    for k, (long, short) in enumerate(NAMES):
        lp, sp = area.add(long + b'\0'), area.add(short + b'\0')
        body += struct.pack('<II', lp - str_base, sp - str_base)
        if k == 0:
            ap = [lp, sp]
    cl = [area.add(CLAUSURA + b'\0'), area.add(b'CLAUSURA\0')]
    names_at = 13 + 6 * nd + 1
    new = area.add(bytes(body))
    refs = _refs(p, lo)
    assert refs
    for objn, off in refs:
        p.retarget(objn, off, 2, new)
    d1 = p.le.obj_bytes(1)
    regs = sacups.regs(d1)
    a0 = regs['D7'] + 4
    A = {n: a0 + 4 * i for i, n in enumerate(('A0', 'A1', 'A2', 'A3', 'A4'))}
    e = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xc7\x05' + e(A['A4']) + rb'(.{4})\x8b\x35' + e(A['A4']) + rb'\x66\x8b\x46\x4f', d1, re.S)]
    assert len(m) == 1
    diy = struct.unpack('<I', m[0].group(1))[0]
    # cseg_8922B: mov [A0], offset DIY; mov esi,[A1]; add word [esi+2B7h],1; mov esi,[A2]; add word [esi+2B7h],1
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + e(A['A0']) + e(diy) + rb'\x8b\x35' + e(A['A1'])
                                        + rb'\x66\x83\x86\xb7\x02\x00\x00\x01\x8b\x35' + e(A['A2']), d1)]
    assert len(m) == 1, m
    site = m[0]
    m = {struct.unpack('<I', x.group(1))[0] for x in re.finditer(rb'\x8b\x35' + e(A['A1']) + rb'\x8b\x86\xb3\x02\x00\x00\xa3'
                                                                  + e(A['A1']) + rb'\xa1(.{4})\x01\x05' + e(A['A1']), d1, re.S)}
    assert len(m) == 1
    sel = m.pop()
    # InitializeNewSeason: call GetCurrentSeasonPointer; mov eax,[DIY+27h]; sub eax, offset aChairmanScenes;
    # mov esi,[A0]; mov [esi+16h] (leagueStringOffset), eax
    m = [x for x in re.finditer(rb'\xe8(.{4})\xa1(.{4})\x2d(.{4})\x8b\x35' + e(A['A0']) + rb'\x89\x46\x16', d1, re.S)]
    assert len(m) == 1
    season_site = m[0].start()
    getseason = season_site + 5 + struct.unpack('<i', m[0].group(1))[0]
    # ... preceded by: push dword [A6]; call cseg_8B2D3; pop dword [A6]
    build_site = season_site - 6 - 5
    assert d1[build_site] == 0xE8 and d1[build_site - 6:build_site - 4] == b'\xff\x35' and d1[season_site - 6:season_site - 4] == b'\x8f\x05'
    build = build_site + 5 + struct.unpack_from('<i', d1, build_site + 1)[0]
    global SLOT0
    SLOT0 = struct.unpack('<I', m[0].group(2))[0] - 0x27        # the player's league buffer (its +27h = name pointer)
    slot0 = SLOT0
    # cseg_8B71C (slot -> DIY) and cseg_8B7EA (DIY -> slot)
    m = [x for x in re.finditer(rb'\xc7\x05' + e(A['A0']) + rb'(.{4})\xeb.\xc7\x05' + e(A['A0']) + rb'\1\xe9(.{4})', d1, re.S)]
    assert m
    load = m[0].start() + 12 + d1[m[0].start() + 11]
    save = m[0].end() + struct.unpack('<i', m[0].group(2))[0]
    # cseg_93FD8 (promotions and relegations) and its single caller
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + e(A['A3']) + e(diy) + rb'\x8b\x35' + e(A['A3']) + rb'\x66\x83\x3e\x00\x0f\x85', d1)]
    assert len(m) == 1
    rel93 = m[0]
    calls = [k for k in range(len(d1) - 5) if d1[k] == 0xE8 and k + 5 + struct.unpack_from('<i', d1, k + 1)[0] == rel93]
    assert len(calls) == 1, calls
    site_rel = calls[0]
    # cseg_883DD, the table sort
    m = [x for x in re.finditer(rb'\xc7\x05' + e(A['A4']) + e(diy) + rb'\x8b\x35' + e(A['A4']) + rb'\x66\x8b\x46\x4f', d1, re.S)]
    assert len(m) == 1
    sort = m[0].start()
    symbols = {'DIY': (2, diy), 'A0': (2, A['A0']), 'SELTEAMS': (2, sel), 'D0': (2, regs['D7'] - 28),
               'SORT': (1, sort), 'LOAD': (1, load), 'SAVE': (1, save), 'REL93': (1, rel93),
               'SLOT0': (2, slot0), 'ARG_ID': (0, LEAGUE_SIG[0]),
               'CHAIRMAN': (2, str_base), 'ARG_FILE': (0, FILE), 'NCHAMP': (0, len(champ_texts(src_dir))),
               'CHAMP_TAB_DD': (0, 'dd ' + ', '.join(f'CT{i}' for i in range(len(champ_texts(src_dir))))),
               'CHAMP_TEXTS': (0, '\n'.join(f'CT{i}: db "{t}", 0' for i, t in enumerate(champ_texts(src_dir)))),
               'PROM_BYTES': (0, 'db ' + ', '.join(str(b) for b in prom_bytes(src_dir))),
               'GETSEASON': (1, getseason), 'BUILD': (1, build), 'NAME_DW': (2, new + names_at),
               'AP_LONG': (2, ap[0]), 'CL_LONG': (2, cl[0]),
               'AP_LONG_OFF': (0, ap[0] - str_base), 'AP_SHORT_OFF': (0, ap[1] - str_base),
               'CL_LONG_OFF': (0, cl[0] - str_base), 'CL_SHORT_OFF': (0, cl[1] - str_base)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    if ROUND_HOOK:
        p.remove(1, site + 2)                           # the replaced mov holds two absolute addresses
        p.remove(1, site + 6)
        p.put(1, site, b'\xe8' + struct.pack('<i', labels['arg_round'] - (site + 5)) + b'\x90' * 5)
    p.put(1, build_site + 1, struct.pack('<i', labels['arg_prebuild'] - (build_site + 5)))   # relative call: no fixup
    p.put(1, site_rel + 1, struct.pack('<i', labels['arg_relegate'] - (site_rel + 5)))        # relegations by promedio
    ARG_ITEMS[:] = [(labels['AP_BLOCK'], AP_SIZE), (labels['PROM'], PROM_SIZE)]
    assert labels['PROM'] - labels['AP_BLOCK'] == AP_SIZE
    LABELS.update(labels)
    print(f'exe: Argentina Apertura/Clausura: struct obj2+{new:#x}, counters obj1+{site:#x}, new season obj1+{build_site:#x}, '
          f'code obj1+{at:#x} ({len(code)} B)')
    return (at + len(code) + 15) & ~15


def load_hook(p, at):
    """After trailer.patch: wrap the LoadCareerFile -> ProcessCareerFile call (now trailer's load_trailer)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    a1 = sacups.regs(d1)['A1']
    m = [x for x in re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', a1)) + rb'(.{4})\xe8.{4}\x75.\xe8.{4}\x75.\xe8(.{4})',
                                d1, re.S)]
    m = [x for x in m if sum(y.group(1) == x.group(1) for y in m) == 1]
    assert len(m) == 1, len(m)
    call = m[0].end() - 5
    loader = m[0].end() + struct.unpack('<i', p.get(1, call + 1, 4))[0]     # trailer's load_trailer (patched bytes)
    assert loader != m[0].end() + struct.unpack('<i', m[0].group(2))[0], 'trailer not applied yet'
    symbols = {'LOADER': (1, loader), 'ARG_NAMES': (1, LABELS['arg_names']), 'SLOT0': (2, SLOT0)}
    code, fix = nasmcave.assemble(LOAD_ASM, at, symbols)
    assert not any(p.le.obj_bytes(1)[at:at + len(code)])
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, call + 1, struct.pack('<i', at - (call + 5)))
    print(f'exe: Argentina: career load call obj1+{call:#x} -> obj1+{at:#x}')
    return (at + len(code) + 15) & ~15


def late(p):
    """After sacups.patch: the season end's `call cseg_92D55` now calls sacups' sa_qualify; put arg_agg in front of it."""
    d1 = p.le.obj_bytes(1)
    site_se = [i for i in range(len(d1) - 24) if d1[i] == 0xe8 and d1[i + 5] == 0xe8 and d1[i + 10] == 0xe8
               and d1[i + 15:i + 18] == b'\x66\xc7\x05' and d1[i + 22:i + 24] == b'\x00\x00' and d1[i + 24:i + 26] == b'\x66\xa1']
    tg = lambda i: i + 5 + struct.unpack_from('<i', d1, i + 1)[0]
    site_se = [i for i in site_se if 0 < tg(i + 5) - tg(i) < 0x1000 and 0 < tg(i + 10) - tg(i + 5) < 0x1000]
    assert len(site_se) == 1, site_se
    site_se = site_se[0]
    safter = site_se + 5 + struct.unpack('<i', p.get(1, site_se + 1, 4))[0]        # sacups' sa_qualify (patched bytes!)
    assert safter != tg(site_se), 'sacups not applied yet'
    p.add_ptr(1, LABELS['SAFTER_PTR'], 1, safter)
    p.put(1, site_se + 1, struct.pack('<i', LABELS['arg_agg'] - (site_se + 5)))
    print(f'exe: Argentina season end: aggregate table before the qualifiers, call obj1+{site_se:#x} -> arg_agg '
          f'(then obj1+{safter:#x})')
