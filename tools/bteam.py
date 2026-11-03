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


def patch(p, at, force=None):
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
    src = ASM
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
    if force:
        p.remove(1, s['smm'] + 2)                       # mov ax, [isNationalSelector]
        p.branch(1, s['smm'], 0xE8, 3, lab['bt_smm'], 6)
    engine.ITEM_AT['BU'] = (3, lab['BU'])
    LABELS.update(lab)
    print(f'exe: B-team call-ups runtime: code obj3+{at:#x} ({len(code)} B), adv {[hex(a) for a in adv]}, season end '
          f'{[hex(a) for a in s["end"]]}, surplus {[hex(g) for g in s["gen"]]}, wage {s["wst"]:#x}'
          + (' + BTEAM_FORCE mailbox (test build)' if force else ''))
    return at + len(code)
