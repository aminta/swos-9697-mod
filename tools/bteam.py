"""4.0.6 B-team call-ups (Davide 02/11 + 03/11, notes/bteam-trace.md): the career club calls up players of its B team
(clubs.csv 'second_of'): (1) for the next match only (U23 by birth year, a goalkeeper at any age, the country's
over-age cap, at most 4 a match, back to the B team after the match, no money), (2) for the season (at most 3 a
window, in the country's real transfer windows, a generated replacement in the B record, the game's wages).

This file, step 1: the data. DATA\\BAGE.nnn (nnn = the world) is read by the exe when the call-up page opens:
  'BA', db version 2, db teams
  per team (the career club = parent):  dw B team word, dw parent team word (file | ordinal << 8), db rules index,
                                        db players (record places 1..16, then its XTRA places 17..), db age codes
                                        (birth year - 1900; 0 = unknown: callable, never over-age)
  'BR', db rules
  per rules:                            db over-age cap (one-match call-ups: players older than U23 among those
                                        called; 0FFh = no cap), db U23 age limit, db flags (bit 0: a goalkeeper
                                        is callable at any age; off in Australia / New Zealand),
                                        db windows, (db first week, db last week) x windows (split.week_of: the
                                        career calendar's week byte, 8 a month from January of the season's first
                                        year, +96 the next year)
The windows are the real ones per country (Davide (a), 02/11: Europe summer to 1 Sep, winter January); the
one-match call-ups and the normal market are open all year.
"""
import os
import struct

import split

# Over-age caps and windows by country (the B team's league rules, pack.json second_teams.rules). Week = split.week_of.
#   ITA: Serie C U23 squads (Juventus NG, Atalanta U23, Inter U23, Milan Futuro) - 4 over-age players in a match list;
#        windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   GER: 3. Liga II teams - 3 over-age (U23) players on the pitch; windows 1 Jul - 1 Sep, 1 Jan - 1 Feb.
#   ESP: Primera Federacion filial - 4 over-age; windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   NED: Jong / U21 in the Eerste Divisie - count-only (no cap in the game: the real rule counts appearances, <15
#        apps, which SWOS does not keep - approximate); windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   POR: Liga 2 B teams - generic U23 + 4 over-age; windows 1 Jul - 1 Sep, 2 Jan - 2 Feb.
#   AUS: the A-League clubs' NPL sides are U23 squads, no over-age player (Football NSW 2026 3.2, Football Victoria
#        2026 6.1.8, Football Queensland 2026 f; sources in notes/bteam-trace.md); windows = Football Australia's
#        2026/27 men's windows: 24 Jun - 15 Sep 2026, 12 Jan - 8 Feb 2027 (Domestic Match Calendar 2026/27).
#   NZL: AUCKLAND / WELLINGTON are A-League clubs: the same FA windows; the reserves' over-age cap NOT FOUND in an
#        official source: APPROXIMATION (Davide B = (b), 03/11): no over-age player, like Australia.
#   GK flag (Davide A = (b), 03/11): Europe's B-team rules let a goalkeeper of any age play; AUS has no keeper
#        exception (U23 squads), NZL follows AUS.
RULES = {
    'ita': (4, 23, True, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'ger': (3, 23, True, (('1/7', '1/9'), ('1/1+1', '1/2+1'))),
    'esp': (4, 23, True, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'ned': (0xFF, 23, True, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'por': (4, 23, True, (('1/7', '1/9'), ('2/1+1', '2/2+1'))),
    'aus': (0, 23, False, (('24/6', '15/9'), ('12/1+1', '8/2+1'))),
    'nzl': (0, 23, False, (('24/6', '15/9'), ('12/1+1', '8/2+1'))),
}
RULE_IDS = list(RULES)
MAX_MATCH = 4                   # (1) at most 4 called up for one match
MAX_WINDOW = 3                  # (2) at most 3 attached in one window


def team_word(pk, key):
    f, i = pk.where[key]
    return f | i << 8


def links(packs):
    """[(world, pack of B, B key, pack of parent, parent key, rules)] for every B team of the career worlds."""
    by_country = {}
    for pk in packs:
        if pk.world is not None:
            by_country.setdefault((pk.world, pk.meta.get('id', '').rsplit('-', 1)[-1].upper()), pk)
    out = []
    for pk in packs:
        if pk.world is None:
            continue
        st = (pk.league or {}).get('second_teams') or {}
        for k, c in pk.clubs.items():
            par = c.get('second_of')
            if not par:
                continue
            ppk = pk
            if ':' in par:                      # (NZ reserves: 'AUS:auckland', the parent in another country's pack)
                cc, par = par.split(':')
                ppk = by_country.get((pk.world, cc))
                assert ppk is not None, f'bteam: {k}: no pack for {cc}'
            assert par in ppk.clubs, f'bteam: {k}: parent {par} not in {ppk.meta.get("id")}'
            r = st.get('rules')
            assert r in RULES, f'bteam: {k}: rules {r!r} not in bteam.RULES'
            out.append((pk.world, pk, k, ppk, par, r))
    return out


def ages(pk, key):
    """Age codes (birth year - 1900, 0 = unknown) of the club's players in record order (places 1..16, then XTRA)."""
    out = []
    for row in pk.prows[key]:
        b = (row.get('born') or '').strip()
        out.append(int(b) - 1900 if b.isdigit() and 1901 <= int(b) <= 2155 else 0)
    return out


def bage(packs):
    """{'BAGE.nnn': bytes} per world with B teams."""
    by_world = {}
    for w, pk, k, ppk, par, r in links(packs):
        by_world.setdefault(w, []).append((team_word(pk, k), team_word(ppk, par), RULE_IDS.index(r), ages(pk, k)))
    out = {}
    for w, rows in sorted(by_world.items()):
        d = b'BA' + bytes((2, len(rows)))
        for bw, pw, ri, a in rows:
            assert len(a) <= 30, (w, bw, len(a))
            d += struct.pack('<HHBB', bw, pw, ri, len(a)) + bytes(a)
        d += b'BR' + bytes((len(RULE_IDS),))
        for r in RULE_IDS:
            cap, u, gk, wins = RULES[r]
            d += bytes((cap, u, int(gk), len(wins))) + b''.join(bytes((split.week_of(a), split.week_of(b))) for a, b in wins)
        out['BAGE.%03d' % w] = d
    return out


def files():
    """mkpatcher / patch.py: the names (and bytes) of the build's BAGE files."""
    import mkseason
    return bage(mkseason.packs())


def write(data_dir):
    """patch.py: the BAGE files into the build's DATA; a summary line."""
    fs = files()
    if not os.path.isdir(data_dir):                 # (a GOG exe of a release build: its DATA is SWOS/DATA, written there)
        return 'no DATA beside the exe (not written)'
    for n, d in fs.items():
        with open(os.path.join(data_dir, n), 'wb') as f:
            f.write(d)
    return ', '.join(f'{n} {len(d)} B' for n, d in fs.items()) or 'none (no B teams)'


# ---- step 2 (M2): the runtime, obj3 at the chain's end (patch.py) ------------------------------------------------
# BU (engine item, saved with the career): db entries, 3 spare, then BU_MAX entries of 8 bytes:
#   db kind (bits 0-1: 1 next match / 2 season; bit 3: over-age; bits 4-5: the window of a kind 2, 1..), db B index
#   (0..15 the record, 16.. its XTRA block), dw B team word, dd hash of the player's 22-byte name (his careerTeam slot is
#   found by it: slots do not move, but a load or a filler may change what a slot holds).
BU_MAX = 10                     # 4 for one match + 2 windows x 3
BU_SIZE = 4 + 8 * BU_MAX
BUF_SIZE = 1024                 # DATA\\BAGE.nnn read whole (World 2026-27: 753 B)
CODES = ('ok', 'max 4 a match', 'over-age cap', 'window closed', 'squad full (30)', 'window max 3', 'already called',
         'no B team', 'no such player', 'list full')      # bt_can / bt_add's eax (M3: the refusals' texts)
LABELS = {}

ASM = r"""
bt_save:                                ; the 15 pseudo registers D0..A6 -> btrs (the game routines we call use them)
    pushad
    mov esi, REGS
    mov edi, btrs
    mov ecx, 15
    rep movsd
    popad
    ret
bt_rest:
    pushad
    mov esi, btrs
    mov edi, REGS
    mov ecx, 15
    rep movsd
    popad
    ret

bt_hash:                                ; esi -> a name (22 bytes) -> eax (never 0)
    push ecx
    push esi
    xor eax, eax
    mov ecx, 22
.h:
    rol eax, 5
    xor al, [esi]
    inc esi
    dec ecx
    jnz .h
    or eax, 1
    pop esi
    pop ecx
    ret

bt_isb:                                 ; esi -> a name -> eax = the kind byte of his BU entry, or 0
    push ebx
    push ecx
    push edx
    xor eax, eax
    movzx ecx, byte [BU]
    test ecx, ecx
    jz .r
    cmp ecx, BUMAX_
    jbe .n
    mov ecx, BUMAX_
.n:
    call bt_hash
    mov edx, eax
    xor eax, eax
    mov ebx, BU + 4
.e:
    cmp [ebx + 4], edx
    je .hit
    add ebx, 8
    dec ecx
    jnz .e
    jmp .r
.hit:
    movzx eax, byte [ebx]
.r:
    pop edx
    pop ecx
    pop ebx
    ret

bt_inbu:                                ; ax B team word, cl index -> eax = his BU entry, or 0
    push ecx
    push edx
    movzx edx, byte [BU]
    cmp edx, BUMAX_
    jbe .n
    mov edx, BUMAX_
.n:
    push eax
    mov eax, BU + 4
.e:
    test edx, edx
    jz .no
    push ebx
    mov bx, [esp + 4]
    cmp [eax + 2], bx
    pop ebx
    jne .nx
    cmp [eax + 1], cl
    je .yes
.nx:
    add eax, 8
    dec edx
    jmp .e
.no:
    xor eax, eax
.yes:
    add esp, 4
    pop edx
    pop ecx
    ret

bt_load:                                ; ZF = 0 when this career world's DATA\\BAGE.nnn is in btbuf
    pushad
    movzx eax, byte [SLT + WORLD_BYTE]
    test eax, eax
    jz .no
    cmp al, [btw]
    je .have
    mov [btw], al
    mov byte [btok], 0
    xor edx, edx
    mov ecx, 100
    div ecx
    add al, '0'
    mov [btname + 10], al
    mov eax, edx
    mov cl, 10
    div cl
    add ax, 3030h
    mov [btname + 11], ax
    mov edi, btbuf
    mov ecx, BUFSZ_
    xor eax, eax
    rep stosb
    mov ax, 3D00h
    mov edx, btname
    int 21h
    jc .have
    movzx ebx, ax
    mov ah, 3Fh
    mov ecx, BUFSZ_
    mov edx, btbuf
    int 21h
    jc .close
    cmp eax, 6
    jb .close
    cmp word [btbuf], 'BA'
    jne .close
    cmp byte [btbuf + 2], 2
    jne .close
    mov byte [btok], 1
.close:
    mov ah, 3Eh
    int 21h
.have:
    cmp byte [btok], 0
    popad
    ret
.no:
    cmp eax, eax
    popad
    ret

bt_team:                                ; ax = the parent's team word -> esi = its BAGE team row, or 0
    push ecx
    push edx
    movzx ecx, byte [btbuf + 3]
    mov esi, btbuf + 4
.t:
    test ecx, ecx
    jz .none
    cmp esi, btbuf + BUFSZ_ - 6
    jae .none
    cmp [esi + 2], ax
    je .r
    movzx edx, byte [esi + 5]
    lea esi, [esi + 6 + edx]
    dec ecx
    jmp .t
.none:
    xor esi, esi
.r:
    pop edx
    pop ecx
    ret

bt_rules:                               ; al = rules index -> esi = its BR row (cap, U23 limit, flags, windows, (first, last)..)
    push eax
    push ecx
    push edx
    movzx edx, al
    movzx ecx, byte [btbuf + 3]
    mov esi, btbuf + 4
.t:
    test ecx, ecx
    jz .br
    movzx eax, byte [esi + 5]
    lea esi, [esi + 6 + eax]
    dec ecx
    jmp .t
.br:
    add esi, 3                          ; 'BR', db rules
.r:
    test edx, edx
    jz .o
    movzx eax, byte [esi + 3]
    lea esi, [esi + 4 + eax * 2]
    dec edx
    jmp .r
.o:
    pop edx
    pop ecx
    pop eax
    ret

bt_yr:                                  ; eax = the season's first year - 1900 (the world's first year + seasons played)
    push ebx
    call W_REC
    jz .base
    movzx eax, byte [ebx + 42]
    movzx ebx, word [CSN]
    add eax, ebx
    pop ebx
    ret
.base:
    movzx eax, word [CSN]
    add eax, 96
    pop ebx
    ret

bt_week:                                ; eax = the career calendar's current week (split.week_of), 0FFh = none
%ifdef NOCAL
    mov eax, 0FFh
%else
    movzx eax, word [CAL_CUR]
    movzx eax, byte [CAL + eax + 1]
%endif
    ret

bt_src:                                 ; ax B team word, cl index -> esi = the player's 38 bytes there (name set), or 0
    pushad
    movzx ecx, cl
    cmp ecx, 16
    jae .x
    push ecx
    push eax
    mov esi, REGS
    mov edi, btrs2
    mov ecx, 15
    rep movsd
    pop eax
    pop ecx
    mov [D0], ax
    mov [D1], cx
    call GP                             ; GetPlayer: A0 = the player - 4Ch (the record, change list applied)
    mov esi, [A0]
    add esi, 4Ch
    push esi
    mov esi, btrs2
    mov edi, REGS
    mov ecx, 15
    rep movsd
    pop esi
    jmp .chk
.x:
    call XTB                            ; xt_block: the market's cache of its XTRA block (sold / left / ours blanked)
    test eax, eax
    jz .none
    sub ecx, 16
    movzx edx, byte [eax + 2]
    cmp ecx, edx
    jae .none
    imul ecx, ecx, PLAYER_
    lea esi, [eax + 4 + ecx]
.chk:
    cmp byte [esi + 3], 0
    jne .r
.none:
    xor esi, esi
.r:
    mov [esp + 4], esi
    popad
    ret

bt_can:                                 ; al kind (1 / 2), cl B index -> eax = 0 or the refusal (bteam.CODES); sets
    pushad                              ; btk, bti, btbw, btte, btov, btwin for bt_add
    mov [btk], al
    mov [bti], cl
    mov byte [btov], 0
    mov byte [btwin], 0
    mov ebp, 7
    cmp word [ISNAT], 0
    jne .r
    call bt_load
    jz .r
    mov ax, [SEL]
    call bt_team
    test esi, esi
    jz .r
    mov [btte], esi
    mov ax, [esi]
    mov [btbw], ax
    mov ebp, 8
    movzx ecx, byte [bti]
    cmp cl, [esi + 5]
    jae .r
    mov ebp, 6
    call bt_inbu
    test eax, eax
    jnz .r
    mov ebp, 8
    mov ax, [btbw]
    call bt_src
    test esi, esi
    jz .r
    mov ebx, esi
    mov ebp, 4
    cmp word [CNP], 30
    jae .r
    mov ebp, 9
    cmp byte [BU], BUMAX_
    jae .r
    mov esi, [btte]
    movzx edx, byte [esi + 6 + ecx]     ; age code (0 = unknown: never over-age)
    mov al, [esi + 4]
    call bt_rules
    mov edi, esi                        ; edi = the rules
    test edx, edx
    jz .young
    test byte [edi + 2], 1              ; the country lets a goalkeeper play at any age?
    jz .gkage
    test byte [ebx + 1Ah], 0E0h
    jz .young
.gkage:
    call bt_yr
    movzx ecx, byte [edi + 1]
    sub eax, ecx
    cmp edx, eax
    jge .young
    mov byte [btov], 1
.young:
    cmp byte [btk], 1
    jne .k2
    xor ecx, ecx                        ; kind 1 entries
    xor edx, edx                        ; over-age among them
    movzx eax, byte [BU]
    mov esi, BU + 4
.c1:
    test eax, eax
    jz .c1e
    mov bl, [esi]
    and bl, 3
    cmp bl, 1
    jne .c1n
    inc ecx
    test byte [esi], 8
    jz .c1n
    inc edx
.c1n:
    add esi, 8
    dec eax
    jmp .c1
.c1e:
    mov ebp, 1
    cmp ecx, MAXM_
    jae .r
    cmp byte [btov], 0
    je .ok
    mov ebp, 2
    movzx eax, byte [edi]               ; the over-age cap (0FFh: none)
    cmp edx, eax
    jae .r
    jmp .ok
.k2:
    mov ebp, 3
    call bt_week
    movzx ecx, byte [edi + 3]
    xor ebx, ebx
.w:
    cmp ebx, ecx
    jae .r
    cmp al, [edi + 4 + ebx * 2]
    jb .wn
    cmp al, [edi + 5 + ebx * 2]
    jbe .win
.wn:
    inc ebx
    jmp .w
.win:
    inc ebx
    mov [btwin], bl
    shl bl, 4
    xor ecx, ecx
    movzx eax, byte [BU]
    mov esi, BU + 4
.c2:
    test eax, eax
    jz .c2e
    mov dl, [esi]
    and dl, 33h
    or bl, 2
    cmp dl, bl
    jne .c2n
    inc ecx
.c2n:
    add esi, 8
    dec eax
    jmp .c2
.c2e:
    mov ebp, 5
    cmp ecx, MAXW_
    jae .r
.ok:
    xor ebp, ebp
.r:
    mov [esp + 28], ebp
    popad
    ret

bt_add:                                 ; al kind (1 / 2), cl B index -> eax = 0 (called up) or bt_can's refusal
    pushad
    call bt_can
    mov [esp + 28], eax
    test eax, eax
    jnz .out
    call bt_save
    mov ax, [btbw]
    mov cl, [bti]
    call bt_src
    mov edi, bttmp
    mov ecx, PLAYER_
    rep movsb
    xor edx, edx                        ; the lowest slot not in the squad order (cseg_56379's way)
.s:
    movzx ecx, word [CNP]
.s0:
    test ecx, ecx
    jz .free
    dec ecx
    cmp [CMP + ecx], dl
    jne .s0
    inc edx
    jmp .s
.free:
    mov [btslot], edx
    mov [D1], edx
    call C63919                         ; trainingMatchSavedPlayers[careerNumPlayers] = the slot (a removal looks it up)
    mov edx, [btslot]
    imul edi, edx, PLAYER_
    add edi, CT + 76
    mov esi, bttmp
    mov ecx, PLAYER_
    rep movsb
    sub edi, PLAYER_
    or byte [edi + 1Ah], 2              ; 'generated': never listed, never bid for, the fillers' colour
    mov dword [edi + 21h], 0            ; his season's stats here start at 0
    mov esi, COMPFB                     ; after the match's 11 + bench (cseg_56379)
    movzx eax, word [esi + 65h]
    cmp word [esi], 2
    jne .b
    movzx eax, word [esi + 4Dh]
.b:
    add eax, 11
    movzx ecx, word [CNP]
    cmp eax, ecx
    jbe .ins
    mov eax, ecx
.ins:
    cmp ecx, eax
    je .put
    mov bl, [CMP + ecx - 1]
    mov [CMP + ecx], bl
    dec ecx
    jmp .ins
.put:
    mov bl, [btslot]
    mov [CMP + eax], bl
    movzx ebx, byte [BU]                ; BU entry (before the wage: a kind 1 is paid 0, bt_wst)
    inc byte [BU]
    lea ebx, [BU + 4 + ebx * 8]
    mov al, [btwin]
    shl al, 4
    or al, [btk]
    cmp byte [btov], 0
    je .nov
    or al, 8
.nov:
    mov [ebx], al
    mov al, [bti]
    mov [ebx + 1], al
    mov ax, [btbw]
    mov [ebx + 2], ax
    lea esi, [edi + 3]
    call bt_hash
    mov [ebx + 4], eax
    mov dword [A0], CT
    mov eax, [btslot]
    mov [D1], eax
    call SETBENCH
    inc word [CNP]
    mov eax, [btslot]
    mov [D1], eax
    call WAGE                           ; cseg_5E345 (kind 1: bt_wst stores 0)
    movzx eax, word [btbw]
    mov [D0], eax
    movzx eax, byte [bti]
    mov [D1], eax
    call C546DF                         ; off the transfer lists (as a purchase does with the seller's player)
    cmp byte [btk], 2
    jne .xb
    cmp byte [bti], 16
    jae .xb
    movzx eax, word [btbw]
    mov [D0], eax
    movzx eax, byte [bti]
    mov [D1], eax
    call C56615                         ; the season: the game's generated replacement in the B record (+ change list)
.xb:
    movzx ecx, byte [bti]
    sub ecx, 16
    jb .done
    mov ax, [btbw]
    call XTB                            ; an XTRA player: his name blanked in the market's cached block now
    test eax, eax
    jz .done
    imul ecx, ecx, PLAYER_
    mov byte [eax + 4 + ecx + 3], 0
.done:
    call bt_rest
.out:
    popad
    ret

bt_slot:                                ; eax = a BU hash -> ecx = his careerTeam slot (in the squad order), or -1
    push ebx
    push edx
    push esi
    mov edx, eax
    movzx ebx, word [CNP]
.k:
    test ebx, ebx
    jz .no
    dec ebx
    movzx ecx, byte [CMP + ebx]
    cmp ecx, 32
    jae .k
    imul esi, ecx, PLAYER_
    add esi, CT + 76 + 3
    call bt_hash
    cmp eax, edx
    jne .k
    jmp .r
.no:
    mov ecx, -1
.r:
    mov eax, edx
    pop esi
    pop edx
    pop ebx
    ret

bt_back:                                ; esi = a BU entry: the player back to his B team, out of careerTeam
    pushad
    mov ebp, esi
    mov eax, [ebp + 4]
    call bt_slot
    cmp ecx, -1
    je .xtra
    mov [btslot], ecx
    mov al, [ebp]
    and al, 3
    cmp al, 2
    jne .rm
    cmp byte [ebp + 1], 16
    jae .rm
    imul esi, ecx, PLAYER_              ; the season: his bytes now (form, value) replace the generated one in the
    add esi, CT + 76                    ; B record and in its change list entry
    mov edi, bttmp
    mov ecx, PLAYER_
    rep movsb
    and byte [bttmp + 1Ah], 0FDh
    movzx ecx, word [NFM2]
.cl:
    test ecx, ecx
    jz .rec
    dec ecx
    imul edi, ecx, 42
    add edi, CFMP
    mov ax, [ebp + 2]
    cmp [edi], ax
    jne .cl
    mov al, [ebp + 1]
    cmp [edi + 2], al
    jne .cl
    add edi, 4
    mov esi, bttmp
    mov ecx, PLAYER_
    rep movsb
.rec:
    movzx eax, word [ebp + 2]
    mov [D0], eax
    movzx eax, byte [ebp + 1]
    mov [D1], eax
    call GP
    mov edi, [A0]
    add edi, 4Ch
    mov esi, bttmp
    mov ecx, PLAYER_
    rep movsb
.rm:
    mov eax, [btslot]
    mov [D1], eax
    call RM                             ; cseg_52EA6 (the game's removal; a squad of 16: a filler takes the slot)
.xtra:
    movzx ecx, byte [ebp + 1]
    cmp ecx, 16
    jb .r
    mov ax, [ebp + 2]
    call XTB                            ; his name back in the market's block: read again
    test eax, eax
    jz .r
    mov byte [eax + 3], 0
.r:
    popad
    ret

bt_ret:                                 ; bl = kinds (1 = the one-match call-ups, 3 = all): those players go back
    pushad
    cmp byte [BU], 0
    je .out
    call bt_save
    movzx ecx, byte [BU]
    cmp ecx, BUMAX_
    jbe .e
    mov ecx, BUMAX_
    mov [BU], cl
.e:
    test ecx, ecx
    jz .done
    dec ecx
    lea esi, [BU + 4 + ecx * 8]
    mov al, [esi]
    and al, 3
    test al, bl
    jz .e
    call bt_back
    movzx edx, byte [BU]                ; the entry out of the list
    dec edx
    mov [BU], dl
    lea edi, [BU + 4 + ecx * 8]
    lea esi, [edi + 8]
    lea eax, [BU + 4 + edx * 8]
    push ecx
    mov ecx, eax
    sub ecx, edi
    rep movsb
    pop ecx
    mov dword [eax], 0
    mov dword [eax + 4], 0
    jmp .e
.done:
    call bt_rest
.out:
    popad
    ret

bt_adv:                                 ; the calendar advance's 4 calls (after an event): the one-match call-ups back
    pushad
    mov bl, 1
    call bt_ret
    popad
    jmp PREV_ADV

bt_end:                                 ; ContinueCareerNextSeason's 2 `call cseg_91428` (before a job change writes the
    pushad                              ; old club's record, before the new season): every call-up back
    mov bl, 3
    call bt_ret
    popad
    jmp PREV_END

bt_gen:                                 ; cseg_52588's surplus removals: `mov esi, [A0] / test byte [esi+66h], 2` -
    mov esi, [A0]                       ; a called-up player is not a filler to drop (ZF = 1: not generated)
    test byte [esi + 66h], 2
    jz .r
    push eax
    push esi
    add esi, 4Fh
    call bt_isb
    pop esi
    test eax, eax
    pop eax
    jz .gen
    cmp eax, eax
    ret
.gen:
    test byte [esi + 66h], 2
.r:
    ret

bt_wst:                                 ; cseg_5E345's `mov [esi+ebx], eax / jmp` (the wage of slot ebx / 4): 0 for a
    mov [esi + ebx], eax                ; one-match call-up
    cmp byte [BU], 0
    je .r
    pushad
    mov ecx, ebx
    shr ecx, 2
    cmp ecx, 32
    jae .p
    imul esi, ecx, PLAYER_
    add esi, CT + 76 + 3
    call bt_isb
    and al, 3
    cmp al, 1
    jne .p
    mov esi, [esp + 4]
    mov dword [esi + ebx], 0
.p:
    popad
.r:
    mov dword [esp], WST_JT
    ret

bt_readto:                              ; xt_block's block read (ax team, edi buffer): our XTRA call-ups blanked too
    mov [btrt], ax
    call PREV_READTO
    pushad
    movzx edx, byte [BU]
    mov esi, BU + 4
    mov ax, [btrt]
.e:
    test edx, edx
    jz .o
    cmp [esi + 2], ax
    jne .n
    movzx ecx, byte [esi + 1]
    sub ecx, 16
    jb .n
    cmp ecx, MAXE_
    jae .n
    imul ecx, ecx, PLAYER_
    mov byte [edi + ecx + 3], 0
.n:
    add esi, 8
    dec edx
    jmp .e
.o:
    popad
    ret

%ifdef BT_FORCE
bt_smm:                                 ; (BTEAM_FORCE test builds) cseg_52588's `mov ax, [isNationalSelector]`: the
    pushad                              ; harness's requests in btmb done here (db count, then up to 8 x (db kind,
    movzx edx, byte [btmb + 4]          ; db B index): kind 1 / 2 a call-up, 3 all back, 4 the one-match ones back;
    cmp edx, 8                          ; the results at btmb + 21, a counter at btmb + 29)
    jbe .n
    mov edx, 8
.n:
    xor esi, esi
.q:
    cmp esi, edx
    jae .d
    mov al, [btmb + 5 + esi * 2]
    mov cl, [btmb + 6 + esi * 2]
    cmp al, 3
    jae .ret
    call bt_add
    jmp .res
.ret:
    mov bl, 1
    cmp al, 4
    je .rb
    mov bl, 3
.rb:
    call bt_ret
    xor eax, eax
.res:
    mov [btmb + 21 + esi], al
    inc esi
    jmp .q
.d:
    mov byte [btmb + 4], 0
    inc byte [btmb + 29]
    popad
    mov ax, [ISNAT]
    ret
btmb: db 'BTRQ', 0
    times 16 db 0
    times 8 db 0FFh
    db 0
%endif

align 4
btrs: times 15 dd 0
btrs2: times 15 dd 0
btte: dd 0
btslot: dd 0
btbw: dw 0
btrt: dw 0
btk: db 0
bti: db 0
btov: db 0
btwin: db 0
btw: db 0FFh
btok: db 0
btname: db 'data\bage.000', 0
bttmp: times PLAYER_ db 0
align 4
btmark: db 'BTBU'                       ; (the harness finds the list by this)
BU: times BUSZ_ db 0
align 4
btbuf: times BUFSZ_ db 0
"""


def sites(p):
    """obj1 / obj2 offsets in the original exe (bytes of p.le.obj_bytes(1)): the purchase copy's routines (cseg_56379),
    cseg_52588's head + its 2 surplus tests, cseg_5E345's wage store, currentSeasonNumber, ContinueCareerNextSeason's 2
    `call cseg_91428`."""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    D0 = r['D7'] - 28
    D1, A0, A1 = D0 + 4, r['A0'], r['A0'] + 4
    ptr = lambda a: re.escape(struct.pack('<I', a))
    rel = lambda o: o + 5 + struct.unpack('<i', d1[o + 1:o + 5])[0]
    u32 = lambda m, k: struct.unpack('<I', m.group(k))[0]

    def one(pat, what):
        m = list(re.finditer(pat, d1, re.S))
        assert len(m) == 1, (what, [hex(x.start()) for x in m])
        return m[0]
    s = {'D0': D0, 'D1': D1, 'A0': A0}
    m = one(rb'\xff\x35' + ptr(D0) + rb'\xff\x35' + ptr(D1) + rb'(\xe8....)(\xe8....)\xa1' + ptr(A0) + rb'\xa3' + ptr(A1) +
            rb'\xc7\x05' + ptr(A0), 'cseg_56379 head')
    s['c546df'], s['gp'] = rel(m.start(1)), rel(m.start(2))
    m = one(rb'\x66\xa1....\x66\xa3' + ptr(D0) + rb'(\xe8....)(\xe8....)\x8b\x35' + ptr(A1) + rb'\x80\x4e\x66\x04', 'cseg_56379 copy')
    assert rel(m.start(1)) == s['gp']
    s['c63919'] = rel(m.start(2))
    copy = m.start()
    m = one(rb'\xc7\x05' + ptr(A0) + rb'(....)\x8b\x35' + ptr(A0) + rb'\x66\x83\x3e\x02\x74\x12\x8b\x35' + ptr(A0) +
            rb'\x66\x8b\x46\x65.{0,200}?\xc7\x05' + ptr(A0) + rb'(....)\xff\x35' + ptr(D1) + rb'(\xe8....)\x8f\x05' + ptr(D1) +
            rb'\x66\x83\x05(....)\x01(\xe8....)\x8f\x05' + ptr(D1) + rb'\x8f\x05' + ptr(D0) + rb'(\xe8....)\xc3', 'cseg_56379 tail')
    assert copy < m.start() < copy + 0x200
    s['compfb'], s['ct'], s['setbench'], s['cnp'] = u32(m, 1), u32(m, 2), rel(m.start(3)), u32(m, 4)
    s['wage'], s['c56615'] = rel(m.start(5)), rel(m.start(6))
    m = one(rb'(\x66\xa1(....))\x66\x0b\xc0\x0f\x85....\x66\xa1....\x66\x0b\xc0\x74\x07\x66\xd1\x25' + ptr(D1), 'cseg_52588 head')
    s['smm'], s['isnat'] = m.start(1), u32(m, 2)
    gen = [x.start() + 10 for x in re.finditer(rb'\x66\x83\x3d' + ptr(D0) + rb'\x00[\x74\x75].\x8b\x35' + ptr(A0) +
                                               rb'\xf6\x46\x66\x02\x75', d1, re.S)]
    assert len(gen) == 2 and s['smm'] < gen[0] < gen[1] < s['smm'] + 0x300, ('cseg_52588 surplus tests', gen)
    s['gen'] = gen
    m = one(rb'\xc7\x05' + ptr(A0) + rb'(....)\x66\xc1\x25' + ptr(D1) + rb'\x02\xa1' + ptr(D0) + rb'\x8b\x35' + ptr(A0) +
            rb'\x0f\xb7\x1d' + ptr(D1) + rb'(\x89\x04\x1e\xeb(.))', 'cseg_5E345 wage store')
    s['wst'] = m.start(2)
    s['wst_jt'] = m.start(2) + 5 + struct.unpack('b', m.group(3))[0]
    m = [x for x in re.finditer(rb'\x66\xa1(....)\x66\xa3' + ptr(D0) + rb'\x66\x83\x05' + ptr(D0) + rb'\x01\x66\xa1(....)\x66\xa3' +
                                ptr(D1), d1, re.S) if x.group(1) == x.group(2)]
    assert len(m) == 1, 'currentSeasonNumber'
    s['csn'] = u32(m[0], 1)
    m = one(rb'(\xe8....)\x66\xa1....\x66\xa3' + ptr(D0) + rb'\xa1....\xa3' + ptr(D1) + rb'\xe8....\xe9', 'ContinueCareerNextSeason')
    c91 = rel(m.start(1))
    s['end'] = [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and rel(i) == c91]
    assert len(s['end']) == 2 and s['end'][1] - s['end'][0] < 0x40, ('call cseg_91428', s['end'])
    return s



# ---- step 3 (M3): the UI - the squad screen's SQ. B button, the B squad (ShowSquad), the call-up page ---------------
# The career squad screen (squadMenu, obj2: 64 packed entries, ESCI = 9 at x 167 y 185) is shown from a copy made at
# each show (bt_sqshow replaces both `mov dword [A6], squadMenu`; a copy at run time keeps what SWOS++ patched in the
# original, as kitcolors' pm_show): + entry 64 SQ. B (45 x 15, left of ESCI, hidden), its init / onReturn the game's
# then bt_vis (shown, ESCI's left -> it: the career club's own squad, not a national team, with a B team). Fire:
# ShowSquad on the B team's record (squadTeamPtr; xbrowse's offer mode vs_ofr: page 2 = its extras 17..30 pickable),
# then the call-up page for the picked player: NEXT MATCH ONLY / FOR THE SEASON (bt_add) / EXIT, the result in a line
# (TEXTS: the codes' words per language).
SQ_ENTRY = 64
SQ_BUTTON = (121, 185, 45, 15)          # menu x, y, w, h (the screen adds 8): ESCI's left, the coach's name below 121
TEXTS = {
    'it': dict(head='SQUADRA B: SCEGLI UN GIOCATORE', btn='SQ. B', c1='SOLO PROSSIMA PARTITA', c2='PER LA STAGIONE', exit='ESCI',
               ok1='CONVOCATO PER LA PROSSIMA PARTITA', ok2='CONVOCATO PER LA STAGIONE',
               codes=('', 'MASSIMO 4 A PARTITA', 'TROPPI FUORI QUOTA', 'MERCATO CHIUSO', 'ROSA PIENA (30)',
                      'MASSIMO 3 PER FINESTRA', "GIA' CONVOCATO", 'NESSUNA SQUADRA B', 'GIOCATORE NON VALIDO',
                      'TROPPI CONVOCATI')),
    'en': dict(head='B TEAM: CHOOSE A PLAYER', btn='B TEAM', c1='NEXT MATCH ONLY', c2='FOR THE SEASON', exit='EXIT',
               ok1='CALLED UP FOR THE NEXT MATCH', ok2='CALLED UP FOR THE SEASON',
               codes=('', 'AT MOST 4 A MATCH', 'TOO MANY OVER-AGE PLAYERS', 'TRANSFER WINDOW CLOSED',
                      'SQUAD FULL (30)', 'AT MOST 3 A WINDOW', 'ALREADY CALLED UP', 'NO B TEAM', 'NOT A VALID PLAYER',
                      'TOO MANY CALLED UP')),
    'fr': dict(head='EQUIPE B: CHOISIS UN JOUEUR', btn='EQ. B', c1='LE PROCHAIN MATCH', c2='POUR LA SAISON', exit='QUITTER',
               ok1='APPELE POUR LE PROCHAIN MATCH', ok2='APPELE POUR LA SAISON',
               codes=('', 'MAXIMUM 4 PAR MATCH', 'TROP DE JOUEURS HORS AGE', 'MERCATO FERME', 'EFFECTIF COMPLET (30)',
                      'MAXIMUM 3 PAR MERCATO', 'DEJA APPELE', "PAS D'EQUIPE B", 'JOUEUR NON VALABLE',
                      "TROP D'APPELES")),
    'de': dict(head='B-TEAM: SPIELER WAEHLEN', btn='B-TEAM', c1='NUR NAECHSTES SPIEL', c2='FUER DIE SAISON', exit='ENDE',
               ok1='FUER DAS NAECHSTE SPIEL BERUFEN', ok2='FUER DIE SAISON BERUFEN',
               codes=('', 'HOECHSTENS 4 PRO SPIEL', 'ZU VIELE UEBER 23', 'TRANSFERFENSTER ZU', 'KADER VOLL (30)',
                      'HOECHSTENS 3 PRO FENSTER', 'SCHON BERUFEN', 'KEIN B-TEAM', 'KEIN GUELTIGER SPIELER',
                      'ZU VIELE BERUFEN')),
}
MSG = 40                                # the result line's buffer

UI_ASM = r"""
bt_sqshow:                              ; the 2 `mov dword [A6], squadMenu`: a copy with SQ. B (entry 64)
    pushad
    mov esi, SQM
    mov edi, btsq
    mov ecx, SQLEN_                     ; (the original without its -999)
    rep movsb
    mov esi, btent
    mov ecx, btent_end - btent
    rep movsb
    mov eax, [SQM]
    mov [bt_oinit], eax
    mov eax, [SQM + 4]
    mov [bt_oret], eax
    mov dword [btsq], bt_sqinit
    mov dword [btsq + 4], bt_sqret
    popad
    mov dword [A6], btsq
    ret

bt_sqinit:                              ; the copy's init: the game's, then the button
    mov eax, [bt_oinit]
    test eax, eax
    jz bt_vis
    call eax
    jmp bt_vis

bt_sqret:                               ; on return (from the B squad, the call-up page...): the game's, the button
    mov eax, [bt_oret]
    test eax, eax
    jz bt_vis
    call eax

bt_vis:                                 ; SQ. B shown (and ESCI's left -> it) for the career club's own squad, not a
    pushad                              ; national team, with a B team in this world
    mov eax, [D0]
    push eax
    mov eax, [A0]
    push eax
    mov eax, [SQT]
    cmp eax, CT
    jne .x
    cmp word [ISNAT], 0
    jne .x
    call bt_load
    jz .x
    mov ax, [SEL]
    call bt_team
    test esi, esi
    jz .x
    mov dword [D0], SQE_
    call CALC
    mov edi, [A0]
    mov word [edi + 4], 0               ; (isInvisible)
    movzx ebp, word [edi + 14h]         ; (SQ. B's x)
    mov dword [D0], 9
    call CALC
    mov edi, [A0]
    mov byte [edi + 8], SQE_            ; ESCI: left -> SQ. B
    mov dword [D0], 5                   ; the coach's name: shown cut at SQ. B (Davide 02/11 (a)), the name untouched
    call CALC
    mov edi, [A0]
    mov esi, [edi + 26h]
    cmp esi, bt_coach
    je .x
    test esi, esi
    jz .x
    movzx eax, word [edi + 14h]
    sub ebp, eax                        ; the free width: SQ. B's x - the entry's x - 2 (- 2 more with a background)
    sub ebp, 2
    cmp word [edi + 1Ch], 0
    je .bg
    sub ebp, 2
.bg:
    mov dword [edi + 26h], bt_coach
    mov ebx, bt_coach
    mov ecx, 23
.ch:
    lodsb
    test al, al
    jz .end
    mov dl, 6                           ; the menus' small font (complist.SMALL_W)
    cmp al, ' '
    jne .c1
    mov dl, 3
.c1:
    cmp al, '-'
    jne .c2
    mov dl, 4
.c2:
    cmp al, '('
    je .w3
    cmp al, ')'
    jne .c3
.w3:
    mov dl, 3
.c3:
    push edi
    mov edi, bt_w2
    push ecx
    mov ecx, 7
    repne scasb
    pop ecx
    pop edi
    jne .c4
    mov dl, 2
.c4:
    movzx edx, dl
    sub ebp, edx
    js .end
    mov [ebx], al
    inc ebx
    dec ecx
    jnz .ch
.end:
    mov byte [ebx], 0
.x: pop eax
    mov [A0], eax
    pop eax
    mov [D0], eax
    popad
    ret

bt_open:                                ; fire on SQ. B: the B squad (pick a player), then the call-up page
    pushad
    call bt_load
    jz .x
    mov ax, [SEL]
    call bt_team
    test esi, esi
    jz .x
    mov ax, [esi]
    mov [bt_bw2], ax
    mov [D0], ax
    call GETTEAM                        ; A0 = the B team's record
    mov eax, [SQTP]
    mov [bt_sqtp], eax
    xor ebx, ebx                        ; ShowSquad: A0 the team, A1 the title, D0 the rows shown disabled (bit =
    xor ecx, ecx                        ; index: the ones already called up), D1 none lit, D2 0 (rows pickable, ESCI),
.m: mov ax, [bt_bw2]                    ; D3 the first row selected
    call bt_inbu
    test eax, eax
    jz .mn
    bts ebx, ecx
.mn:
    inc ecx
    cmp ecx, 30
    jb .m
    mov [D0], ebx
    mov dword [D0 + 4], 0
    mov word [D0 + 8], 0
    mov word [D0 + 12], 0
    mov dword [A0 + 4], bt_hd
    mov byte [VS_OFR], 1
    call SHOWSQ
    mov byte [VS_OFR], 0
    js .back                            ; (ESCI: nothing picked)
    mov ax, [D0]
    mov [bt_pick], al
    mov eax, [bt_sqtp]
    mov [SQTP], eax
    mov ax, [bt_bw2]                    ; the page's title: the player's name
    mov cl, [bt_pick]
    call bt_src
    test esi, esi
    jz .x
    add esi, 3
    mov edi, bt_title
    mov ecx, 22
    rep movsb
    mov byte [edi], 0
    mov byte [bt_msg], 0
    mov dword [A6], btmenu
    call SHOW_MENU
    jmp .x
.back:
    mov eax, [bt_sqtp]
    mov [SQTP], eax
.x: popad
    ret

bt_c1:                                  ; NEXT MATCH ONLY
    mov al, 1
    jmp bt_cc
bt_c2:                                  ; FOR THE SEASON
    mov al, 2
bt_cc:
    pushad
    mov cl, [bt_pick]
    movzx ebx, al
    call bt_add
    movzx eax, al
    mov esi, [bt_codes + eax * 4]
    test eax, eax
    jnz .m
    mov esi, [bt_oks + ebx * 4 - 4]
.m: mov edi, bt_msg
    mov ecx, MSG_ - 1
.c: lodsb
    stosb
    test al, al
    jz .d
    loop .c
    mov byte [edi], 0
.d: popad
    jmp DRAWMENU

bt_cx:                                  ; EXIT
    mov word [EXITM], 1
bt_dinit:
    ret

bt_hl:                                  ; squadnum's number entry (esi = it, [A6] + 4Ch = his record): a borrowed one's number
    call SE_HL                          ; in yellow (4.0.6 Davide's MiSTer 04/11: no "12B" - the entry stays the game's
    cmp byte [bt_nw], 0                 ; ENTRY_NUMBER, right-aligned as the others; one entry for every row)
    je .k
    mov byte [bt_nw], 0                 ; a borrowed one last time: the number's own colour back
    and word [esi + 24h], 0FFF0h
    push eax
    mov al, [bt_nc]
    or [esi + 24h], al
    pop eax
.k:
    pushad
    cmp dword [SQT], CT                 ; the career club's squad only
    jne .r
    mov edi, [A6]
    add edi, 4Ch
    test byte [edi + 1Ah], 2            ; (bit 1: borrowed or the game's generated filler)
    jz .r
    push esi
    lea esi, [edi + 3]
    call bt_isb
    pop esi
    test eax, eax
    jz .r
    mov al, [esi + 24h]
    and al, 0Fh
    mov [bt_nc], al
    or byte [esi + 24h], 0Fh            ; in the yellow of his PRES. (SquadAfterDrawCommon's colour 0Fh for bit 1)
    mov byte [bt_nw], 1
.r:
    popad
    ret

align 4
bt_coach: times 24 db 0
bt_w2: db "I1',.:", 0                   ; 2 px wide
bt_nc: db 0
bt_nw: db 0
align 4
bt_oinit: dd 0
bt_oret: dd 0
bt_sqtp: dd 0
bt_bw2: dw 0
bt_pick: db 0
align 4
bt_title: times 24 db 0
bt_msg: times MSG_ db 0
align 4
BT_TEXTS
align 4
btmenu:                                 ; the call-up page: 0 the player, 1 / 2 the two call-ups, 3 EXIT, 4 the result
    dd bt_dinit, 0, 0, 1
    dw 0, 30, 304, 14
    dw 4, 17h
    dw 8, 0
    dd bt_title
    dw 0
    dw 52, 70, 200, 15
    dw 2
    db 0FFh, 0FFh, 3, 2
    dw 4, 0Eh
    dw 8, 0
    dd bt_t1
    dw 13
    dd bt_c1
    dw 0
    dw 52, 92, 200, 15
    dw 2
    db 0FFh, 0FFh, 1, 3
    dw 4, 0Eh
    dw 8, 0
    dd bt_t2
    dw 13
    dd bt_c2
    dw 0
    dw 102, 170, 100, 15
    dw 2
    db 0FFh, 0FFh, 2, 1
    dw 4, 0Ch
    dw 8, 0
    dd bt_tx
    dw 13
    dd bt_cx
    dw 0
    dw 0, 130, 304, 10
    dw 8, 0
    dd bt_msg
    dw 0
    dw -999
align 4
btent:                                  ; entry 64 (an origin reset first: menu coordinates), then the end mark
    dw -998, 0, 0
    dw BX_, BY_, BW_, BH_
    dw 1
    dw 2
    db 2Ch, 9, 2Ch, 0FFh
    dw 4, 0Eh
    dw 8, 0
    dd bt_lbl
    dw 13
    dd bt_open
    dw 0
    dw -999
btent_end:
align 4
btsq: times SQLEN_ + 64 db 0
"""


def _db(b):
    return 'db ' + ', '.join(str(x) for x in b + b'\0')


def ui_texts(lang):
    """BT_TEXTS: the button, the page's words and the codes' lines (pointer tables bt_codes / bt_oks)."""
    T = TEXTS[lang]
    enc = lambda t: t.encode('latin-1')
    for t in (T['ok1'], T['ok2']) + T['codes']:
        assert len(t) < MSG, t
    out = [f'bt_lbl: {_db(enc(T["btn"]))}', f'bt_t1: {_db(enc(T["c1"]))}', f'bt_t2: {_db(enc(T["c2"]))}',
           f'bt_tx: {_db(enc(T["exit"]))}', f'bt_hd: {_db(enc(T["head"]))}', f'bt_ok1: {_db(enc(T["ok1"]))}', f'bt_ok2: {_db(enc(T["ok2"]))}']
    out += [f'bt_cd{i}: {_db(enc(t))}' for i, t in enumerate(T['codes'])]
    out += ['align 4', 'bt_oks: dd bt_ok1, bt_ok2', 'bt_codes: dd ' + ', '.join(f'bt_cd{i}' for i in range(len(T['codes'])))]
    return '\n'.join(out)


def ui_sites(p):
    """The squad screen's menu (obj2 offset, packed length without its -999) and its two `mov dword [A6], squadMenu`;
    ShowMenu / A6 / g_exitMenu (fmtpage, controls' pattern)."""
    import re
    import fmtpage
    import squadnum
    import xbrowse
    d1, d2 = p.le.obj_bytes(1), p.le.obj_bytes(2)
    sadc = squadnum.sites(p)['SADC'][1]
    ref = [s for so, s, _, t, o, *_ in p.le.fixups() if so == 2 and t == 1 and o == sadc]
    assert len(ref) == 1, ref
    _, _, _, show, a6 = fmtpage.locate(p)
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    users = [s - 2 for s, to in fx.items() if to == tuple(a6) and d1[s - 2:s] == b'\xc7\x05' and fx.get(s + 4)
             and fx[s + 4][0] == 2 and fx[s + 4][1] is not None and 0 < ref[0] - fx[s + 4][1] < 0x400]
    m = max(fx[x + 6][1] for x in users)                # (the menu just before SquadAfterDrawCommon's reference;
    users = [x for x in users if fx[x + 6][1] == m]     # the one before it is another menu)
    assert len(users) == 2, users
    pay = dict(xbrowse.PAYLOAD)
    pay[7] = 4                                          # (type 7: a dword - xbrowse's parser has no 7)
    saved, xbrowse.PAYLOAD = xbrowse.PAYLOAD, pay
    try:
        end, ents = xbrowse.menu_parse(d2, m)
    finally:
        xbrowse.PAYLOAD = saved
    assert len(ents) == SQ_ENTRY, len(ents)
    assert d2[ents[9][1]:ents[9][1] + 4] == bytes((0x2C, 8, 0x2C, 0xFF)), d2[ents[9][1]:ents[9][1] + 4].hex()
    e = re.search(rb'\x66\xc7\x05....\x00\x00\xe8', d1[show:show + 0x80], re.S)   # mov g_exitMenu, 0 / call ActivateMenu
    return {'menu': m, 'len': end - m, 'users': users, 'show': show, 'a6': a6, 'exitm': fx[show + e.start() + 3]}


def patch(p, at, force=None, lang='it'):
    """obj3 code + data at `at` (the obj3 chain's end: after xleft, ctview / ctgame); returns the end. Needs xtra, xleft,
    careerworld (and gplay for the windows) patched first. force: the BTEAM_FORCE test mailbox (default: the env)."""
    import os
    import careerworld
    import engine
    import gplay
    import nasmcave
    import xleft
    import xtra
    force = os.environ.get('BTEAM_FORCE') if force is None else force
    d1 = p.le.obj_bytes(1)
    s = sites(p)
    xs = xleft.sites(p, __import__('sacups').regs(d1))
    X = xtra.LABELS
    _, cnp, ct, cmp, sel = X['SITES']
    assert (cnp, ct) == (s['cnp'], s['ct']), 'careerNumPlayers / careerTeam'
    for site, n in [(s['wst'], 5)] + [(g, 10) for g in s['gen']] + ([(s['smm'], 6)] if force else []):
        assert p.get(1, site, n) == d1[site:site + n], ('bteam site already patched', hex(site))
    adv = gplay._adv_sites(p)[1]
    prev_adv = {p.call_target(1, a) for a in adv}
    prev_end = {p.call_target(1, a) for a in s['end']}
    assert len(prev_adv) == 1 and len(prev_end) == 1, (prev_adv, prev_end)
    b = bytes(p.get(1, X['xt_block'], 0x80))       # xt_block's block read (xleft's xl_readto, or xtra_readto)
    rd_ok = {(3, xleft.LABELS['xl_readto'])} if 'xl_readto' in xleft.LABELS else {(1, X['xtra_readto'])}
    rd = [X['xt_block'] + i for i in range(0x80 - 5) if b[i] == 0xE8 and p.call_target(1, X['xt_block'] + i) in rd_ok]
    assert len(rd) == 1, ('xt_block read', rd)
    sym = {'REGS': (2, s['D0']), 'D0': (2, s['D0']), 'D1': (2, s['D1']), 'A0': (2, s['A0']), 'SEL': (2, sel), 'CT': (2, ct),
           'CMP': (2, cmp), 'CNP': (2, cnp), 'ISNAT': (2, s['isnat']), 'COMPFB': (2, s['compfb']), 'CSN': (2, s['csn']),
           'NFM2': (2, xs['nfm2']), 'CFMP': (2, xs['cfmp']), 'GP': (1, s['gp']), 'C63919': (1, s['c63919']),
           'C546DF': (1, s['c546df']), 'C56615': (1, s['c56615']), 'SETBENCH': (1, s['setbench']), 'WAGE': (1, s['wage']),
           'RM': (1, xs['rm']), 'XTB': (1, X['xt_block']), 'W_REC': (1, careerworld.LABELS['w_rec']),
           'SLT': careerworld.LABELS['sites']['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
           'WST_JT': (1, s['wst_jt']), 'PREV_ADV': prev_adv.pop(), 'PREV_END': prev_end.pop(),
           'PREV_READTO': p.call_target(1, rd[0]), 'PLAYER_': (0, xtra.PLAYER), 'MAXE_': (0, xtra.MAX_EXTRA),
           'BUMAX_': (0, BU_MAX), 'BUSZ_': (0, BU_SIZE), 'BUFSZ_': (0, BUF_SIZE), 'MAXM_': (0, MAX_MATCH),
           'MAXW_': (0, MAX_WINDOW)}
    import squadnum
    import xbrowse
    u = ui_sites(p)
    import lepatch
    xb = xbrowse.find(lepatch.LEPatch(bytes(p.le.data)))   # (its sites' fixups: xbrowse.patch removed some)
    assert d1[xb['init'] + 12] == 0xE8, 'BuyOtherPlayersInit: call GetTeamPointer'
    for x in u['users']:
        assert p.get(1, x, 10) == d1[x:x + 10], ('bteam: squadMenu user already patched', hex(x))
    x, y, w, h = SQ_BUTTON
    sym.update({'SQM': (2, u['menu']), 'SQLEN_': (0, u['len']), 'SQE_': (0, SQ_ENTRY), 'BX_': (0, x), 'BY_': (0, y),
                'BW_': (0, w), 'BH_': (0, h), 'SQT': squadnum.sites(p)['SQT'], 'CALC': (1, xb['calc']),
                'DRAWMENU': (1, xb['drawmenu']), 'GETTEAM': (1, xb['init'] + 17 + struct.unpack_from('<i', d1, xb['init'] + 13)[0]),
                'SQTP': (2, xb['sqtp']), 'SHOWSQ': (1, xb['showsq']), 'VS_OFR': (1, xbrowse.LABELS['vs_ofr']),
                'SHOW_MENU': (1, u['show']), 'A6': u['a6'], 'EXITM': u['exitm'], 'MSG_': (0, MSG)})
    hl = squadnum.sites(p)['HL_SITE']                   # squadnum's `call se_hl` on the number entry
    assert p.get(1, hl, 1) == b'\xe8', 'bteam: squadnum before bteam'
    sym['SE_HL'] = p.call_target(1, hl)
    src = ASM + UI_ASM.replace('BT_TEXTS', ui_texts(lang))
    if 'CAL' in gplay.LABELS and 'CAL_CUR' in gplay.LABELS:
        sym['CAL'], sym['CAL_CUR'] = gplay.LABELS['CAL'], gplay.LABELS['CAL_CUR']
    else:
        src = '%define NOCAL\n' + src
    if force:
        src = '%define BT_FORCE\n' + src
    at = (at + 15) & ~15
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    for a in adv:
        p.branch(1, a, 0xE8, 3, lab['bt_adv'])
    for a in s['end']:
        p.branch(1, a, 0xE8, 3, lab['bt_end'])
    p.branch(1, rd[0], 0xE8, 3, lab['bt_readto'])
    for g in s['gen']:
        p.remove(1, g + 2)                              # mov esi, [A0]
        p.branch(1, g, 0xE8, 3, lab['bt_gen'], 10)
    p.branch(1, s['wst'], 0xE8, 3, lab['bt_wst'])
    p.branch(1, hl, 0xE8, 3, lab['bt_hl'])              # a borrowed player's number in yellow
    for x in u['users']:                                # M3: mov dword [A6], squadMenu -> the copy with SQ. B
        p.remove(1, x + 2)
        p.remove(1, x + 6)
        p.branch(1, x, 0xE8, 3, lab['bt_sqshow'], 10)
    if force:
        p.remove(1, s['smm'] + 2)                       # mov ax, [isNationalSelector]
        p.branch(1, s['smm'], 0xE8, 3, lab['bt_smm'], 6)
    engine.ITEM_AT['BU'] = (3, lab['BU'])
    LABELS.update(lab)
    print(f'exe: B-team call-ups runtime: code obj3+{at:#x} ({len(code)} B), adv {[hex(a) for a in adv]}, season end '
          f'{[hex(a) for a in s["end"]]}, surplus {[hex(g) for g in s["gen"]]}, wage {s["wst"]:#x}'
          + (' + BTEAM_FORCE mailbox (test build)' if force else ''))
    return at + len(code)
