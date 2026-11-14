"""4.2 kits (Davide 12/11; the idea: David on Facebook): the goalkeepers' kit colour (K2) and the yellow referee of
World 2026-27 (R1). Study and decisions: internal/handoff/kits-keeper-referee.md. Masks: kitmask.py.

Today the keeper's shirt is palette entry 8, the players' shadow, and the referee is all black (entry 3, never
converted). The mod:
- K2. At kick-off each keeper gets a shirt colour that clashes with neither team's worn shirt or stripes, nor with
  the referee's shirt, and is not the other keeper's. The first such colour of PREF (grey - David's look - green,
  yellow, orange, light blue, black, then white, blue, red); shorts and socks black, white when black clashes with the
  other team's shorts. Clashes are judged by the game's own conflict tables as the mod leaves them (kitcolors' rows +
  purple's), either way round, in palette entries (TeamGame's pr*Col are entries; maroon and purple share 12). Measured
  on 6000 pairs of the original TEAM.* home kits (kits.eval): the game's keeper (no colour free: shirt 8, the team's
  shorts / socks) 0.4 % of matches, 0.7 % with the yellow referee. Tighter rules left far more keepers in the old
  look: the teams' shorts too 22 % / 6 PREF colours only 7-13 % / the keepers by the clash table instead of equal
  colours 4-9 %. A hand-set keeper kit (SELECT KITS: this match / always, KEEPKIT.DAT) wins unless it
  clashes with the other team, the referee or the other keeper; then that match takes the automatic colour (Davide:
  "passa al colore automatico") and the hand-set kit stays stored.
- R1. The referee's shirt is yellow (entry 15) when the match is World 2026-27's (the engine's swe_match_w27: a
  career's world byte, a friendly / DIY's contest, else the namespace in the tables), unless either team wears a
  shirt or stripes that clash with yellow (Brazil, Villarreal, Dortmund...): then black, the game's referee. Shorts
  and socks stay black. The keepers avoid the referee's colour.

Exe (MC 12/11: obj4 swreg.KITS_AT..KITS_END, pages 16-17; code + masks on page 16, the KEEPKIT table on page 17):
- ConvertColorsAndTextSprites' `call ChainFont` (after LoadSpritesAndFixOffsets: the sprites are reloaded and made
  chunky for every match, replay and highlight) -> kt_chain: ChainFont, then the referee's colour (his shirt mask:
  entry 3 -> 15 on sprites 1273..1283), then both keepers' kits.
- The four keeper loops' `mov A0, offset teamNPlayersColorTable` (sprites 947..1062 team 1, 1063..1178 team 2: GOAL1.DAT
  twice, 116 frames = main + reserve keeper) -> kt_conv1 / kt_conv2: a copy of the team table as it is there (the
  goalie's skin already in it) with entries 10 / 11 = the keeper's shirt, 14 / 15 his shorts / socks, A0 -> it; and
  sprite D0's shirt mask: entry 8 -> 11. Per sprite, right before its conversion, so a sprite the game leaves
  unconverted (the reserve keeper when useIndividualPlayerSkinColor = 0) keeps its 8s. In the 16-colour mode the
  sprites from 309 are unchained after ConvertColorsAndTextSprites (InitGameRestoreTeams): still chunky here.

Harness: the data block's tag 'KITS'."""
import struct

PREF = (1, 14, 15, 6, 13, 3, 2, 11, 10)   # grey, green, yellow, orange, light blue, black, white, blue, red (entries)
BLACK, WHITE, YELLOW, OLD_SHIRT = 3, 2, 15, 8
SHIRT_COLORS = (1, 2, 3, 6, 10, 11, 12, 13, 14, 15)    # shirtColorTable: kit colour 0..9 -> entry (purple 10 -> 12)
PURPLE, MAROON = 10, 6
REF_SPRITES = range(1273, 1284)
KEEPER_FIRST = (947, 1063)


def code_tables():
    """the game's conflict rows as the mod leaves them (kitcolors' variant C + purple's 11th row): (basic, shorts)"""
    import kitsim
    v = kitsim.variants()['C']
    out = []
    for rows in (list(v.basic), list(v.shorts)):
        rows[MAROON] |= 1 << PURPLE
        rows.append(1 << PURPLE | 1 << MAROON)
        out.append(rows)
    return out


def entry_tables():
    """the same in palette entries: 16 words each, bit e2 of row e1 = e1 clashes with e2 (any kit colour of each)"""
    ent = list(SHIRT_COLORS) + [12]
    res = []
    for rows in code_tables():
        t = [0] * 16
        for c1, row in enumerate(rows):
            for c2 in range(len(rows)):
                if row >> c2 & 1:
                    t[ent[c1]] |= 1 << ent[c2]
        res.append(t)
    return res


EB, ES = entry_tables()


def clash(t, a, b):
    """either way round (the game's rows are not symmetric)"""
    return bool(t[a] >> b & 1 or t[b] >> a & 1)


def shirt_ok(s, teams, ref, other):
    """teams = (shirt, stripes, ...) entries; other = the other keeper's shirt (0 = none yet)"""
    return not any(clash(EB, s, t[0]) or clash(EB, s, t[1]) for t in teams) and not clash(EB, s, ref) and s != other


def keeper(own, oth, ref, other=0, hand=None):
    """(shirt, shorts, socks) entries; own / oth = (shirt, stripes, shorts, socks) of the keeper's team / the other
    team; other = the other keeper's shirt (0 = not chosen yet); hand = a hand-set (shirt, shorts, socks) or None"""
    if hand and shirt_ok(hand[0], (oth,), ref, other):
        return tuple(hand)
    for s in PREF:
        if shirt_ok(s, (own, oth), ref, other):
            sh = WHITE if clash(ES, BLACK, oth[2]) else BLACK
            return s, sh, sh
    return OLD_SHIRT, own[2], own[3]


def referee(w27, t1, t2):
    if w27 and not any(clash(EB, YELLOW, t[0]) or clash(EB, YELLOW, t[1]) for t in (t1, t2)):
        return YELLOW
    return BLACK


def match(t1, t2, w27, hand1=None, hand2=None):
    """the reference of kt_chain: (referee, keeper 1, keeper 2)"""
    r = referee(w27, t1, t2)
    k1 = keeper(t1, t2, r, 0, hand1)
    k2 = keeper(t2, t1, r, k1[0], hand2)
    return r, k1, k2


def eval_pairs(n=6000, seed=2, data='orig/DATA'):
    """(share of matches with a keeper in the old look, w27 off / on) over random pairs of the TEAM.* home kits"""
    import glob
    import random
    ent = list(SHIRT_COLORS) + [12]
    teams = []
    for f in glob.glob(data + '/TEAM.*'):
        d = open(f, 'rb').read()
        for i in range((len(d) - 2) // 0x2AC):
            ty, st, ba, sh, so = d[2 + i * 0x2AC + 0x1A:2 + i * 0x2AC + 0x1F]
            if max(st, ba, sh, so) <= 10:      # (ConvertTeamKitColors: the shirt from +1Bh, the stripes +1Ch)
                teams.append((ent[st], ent[ba] if ty else ent[st], ent[sh], ent[so]))
    rnd = random.Random(seed)
    old = [0, 0]
    for _ in range(n):
        t1, t2 = rnd.sample(teams, 2)
        for w in (0, 1):
            r, k1, k2 = match(t1, t2, w)
            old[w] += OLD_SHIRT in (k1[0], k2[0])
    return old[0] / n, old[1] / n


def kits():
    """every worn kit (shirt, stripes, shorts, socks) in entries: plain and striped shirts of the 11 kit colours"""
    ent = list(SHIRT_COLORS) + [12]
    ent = sorted(set(ent))
    out = []
    for a in ent:
        for b in ent:
            for c in ent:
                out.append((a, b, c, c))
    return out


KK_ASM = r"""
kk_kit:                                 ; [esi + 18..20] kit colours -> [ebx] palette entries, on
    push eax
    push edx
    mov edx, KT_CODE
    movzx eax, byte [esi + 18]
    mov al, [edx + eax]
    mov [ebx], al
    movzx eax, byte [esi + 19]
    mov al, [edx + eax]
    mov [ebx + 1], al
    movzx eax, byte [esi + 20]
    mov al, [edx + eax]
    mov [ebx + 2], al
    mov byte [ebx + 3], 1
    pop edx
    pop eax
    ret

kk_same:                                ; ZF = 1: the names at esi / edi are equal up to the 0, 17 B at most (as
    push eax                            ; stored: the '_' joiner a character like any other)
    push ecx
    push esi
    push edi
    mov ecx, 17
.c: mov al, [esi]
    cmp al, [edi]
    jne .x
    test al, al
    jz .x
    inc esi
    inc edi
    loop .c
    cmp eax, eax
.x: pop edi
    pop esi
    pop ecx
    pop eax
    ret

; --- 4.2 KEEPKIT.DAT (MC 13/11): SEMPRE's keeper kit of the career club, per game folder (every career / save with
; that club shares it). Table on obj4 page 17 (KK_FILE = the file's image): header 'KEEP', u16 1, u16 count, u16 next
; stamp, u16 0; KK_N records of KK_ B: world byte, country, u16 stamp (the OK that wrote it), name 17, shirt, shorts,
; socks (kit colours 0..10). Key: world + country + name (a club clubmap moves between files keeps its country).
kk_load:                                ; once: KEEPKIT.DAT -> KK_FILE (swe_recover first); none / short / bad = empty
    cmp byte [KK_LOADED], 0
    jne .x
    pushad
    mov byte [KK_LOADED], 1
    push KK_NAME
    call SWE_RECOVER
    add esp, 4
    push KK_NAME
    call SWE_FOPEN_R
    add esp, 4
    mov [KK_ERR], eax
    test eax, eax
    js .empty
    mov ebx, eax
    push KK_HDR + KK_N * KK_
    push KK_FILE
    push ebx
    call SWE_FREAD
    add esp, 12
    mov esi, eax
    push ebx
    call SWE_FCLOSE
    add esp, 4
    cmp esi, KK_HDR
    jl .empty
    cmp dword [KK_FILE], 'KEEP'
    jne .empty
    cmp word [KK_FILE + 4], 1
    jne .empty
    movzx ecx, word [KK_FILE + 6]
    cmp ecx, KK_N
    ja .empty
    imul eax, ecx, KK_
    add eax, KK_HDR
    cmp esi, eax
    jl .empty
    mov edi, KK_FILE + KK_HDR
.v: jecxz .ok
    cmp byte [edi + 21], 10
    ja .empty
    cmp byte [edi + 22], 10
    ja .empty
    cmp byte [edi + 23], 10
    ja .empty
    add edi, KK_
    dec ecx
    jmp .v
.empty:
    mov dword [KK_FILE], 'KEEP'
    mov dword [KK_FILE + 4], 1
    mov dword [KK_FILE + 8], 1
.ok:
    popad
.x: ret

kk_find:                                ; esi -> a name, al = world, ah = country: edi -> its record, or 0
    push ecx
    movzx ecx, word [KK_FILE + 6]
    mov edi, KK_FILE + KK_HDR
.l: jecxz .no
    cmp [edi], ax
    jne .n
    add edi, 4
    call kk_same
    lea edi, [edi - 4]
    je .x
.n: add edi, KK_
    dec ecx
    jmp .l
.no:
    xor edi, edi
.x: pop ecx
    ret

kk_club:                                ; a career: ebp -> the career club's keeper slot, CF = 0; else CF = 1
    cmp word [GAMETYPE], 4
    jne .no
    push esi
    push edi
    mov esi, CAREER_TEAM + 5
    mov edi, KS
    call kk_same
    je .y
    add edi, KS_
    call kk_same
    je .y
    pop edi
    pop esi
.no:
    stc
    ret
.y: mov ebp, edi
    pop edi
    pop esi
    clc
    ret

kk_mine:                                ; esi = CAREER_TEAM's name, ax = world, country; kk_find
    call kk_load
    mov esi, CAREER_TEAM + 5
    mov al, [CWB]
    mov ah, [CAREER_TEAM]
    jmp kk_find

kk_fill:                                ; a career's new match: the club's keeper slot <- its record (SET)
    call kk_club
    jc .x
    call kk_mine
    test edi, edi
    jz .x
    mov eax, [edi + 20]
    shr eax, 8
    mov [ebp + 18], ax
    shr eax, 16
    mov [ebp + 20], al
    mov byte [ebp + 21], 1
.x: ret

kk_rec:                                 ; kick-off, esi -> TeamGame: the career club's record -> [ebx]
    cmp word [GAMETYPE], 4
    jne .x
    push esi
    push edi
    add esi, 16h
    mov edi, CAREER_TEAM + 5
    call kk_same
    jne .o
    call kk_mine
    test edi, edi
    jz .o
    lea esi, [edi + 3]                  ; (kk_kit reads +18..20: the record's 21..23)
    call kk_kit
.o: pop edi
    pop esi
.x: ret

kk_keep:                                ; OK with SEMPRE in a career: the club's keeper slot -> its record (AUTO: the
    cmp byte [KM_ALWAYS], 0             ; record removed); KEEPKIT.DAT saved (swe_save_atomic). Full: the record with
    je .x                               ; the lowest stamp replaced (KK_EVICT)
    call kk_club
    jc .x
    call kk_mine
    cmp byte [ebp + 21], 0
    jne .set
    test edi, edi
    jz .x
    movzx ecx, word [KK_FILE + 6]       ; AUTO: the last record into its place
    dec ecx
    mov [KK_FILE + 6], cx
    imul esi, ecx, KK_
    add esi, KK_FILE + KK_HDR
    mov ecx, KK_ / 4
    rep movsd
    jmp .save
.set:
    test edi, edi
    jnz .w
    movzx ecx, word [KK_FILE + 6]
    imul edi, ecx, KK_
    add edi, KK_FILE + KK_HDR
    cmp ecx, KK_N
    jb .add
    mov edi, KK_FILE + KK_HDR           ; full: the oldest (lowest stamp)
    mov esi, edi
    mov ecx, KK_N
.m: mov ax, [esi + 2]
    cmp ax, [edi + 2]
    jae .m2
    mov edi, esi
.m2:
    add esi, KK_
    loop .m
    inc dword [KK_EVICT]
    jmp .w
.add:
    inc word [KK_FILE + 6]
.w: push edi
    xor eax, eax
    mov ecx, KK_ / 4
    rep stosd
    pop edi
    mov al, [CWB]
    mov ah, [CAREER_TEAM]
    mov [edi], ax
    mov ax, [KK_FILE + 8]
    mov [edi + 2], ax
    inc word [KK_FILE + 8]              ; (no renormalisation at the u16 wrap, MC 13/11: one step per OK with SEMPRE
                                        ; and a set keeper kit only, so 65535 is out of reach; past it the newest
                                        ; stamps restart low and could be evicted, and only with all 128 places used)
    xor ecx, ecx
.nm:
    mov al, [CAREER_TEAM + 5 + ecx]
    test al, al
    jz .nd
    mov [edi + 4 + ecx], al
    inc ecx
    cmp ecx, 17
    jb .nm
.nd:
    mov ax, [ebp + 18]
    mov [edi + 21], ax
    mov al, [ebp + 20]
    mov [edi + 23], al
.save:
    movzx eax, word [KK_FILE + 6]
    imul eax, eax, KK_
    add eax, KK_HDR
    push eax
    push KK_FILE
    push KK_NAME
    call SWE_SAVE
    add esp, 12
    mov [KK_ERR], eax
    inc dword [KK_SAVES]
.x: ret
"""

ASM = r"""
kt_chain:                               ; ConvertColorsAndTextSprites' `call ChainFont` (D0 = 227)
    call CHAINFONT
    pushad
    inc dword [KT_CALLS]
    xor eax, eax
%if W27_
    call SWE_W27F                       ; (the engine's swe_match_w27, cdecl)
%endif
    mov [KT_W27], al
    mov esi, [A5]                       ; the two TeamGame: pr*Col words = palette entries
    mov edi, [A6]
    push eax
    mov ecx, 4                          ; (harness: KT_IN = both teams' shirt, stripes, shorts, socks)
.in:
    mov al, [esi + ecx * 2]
    mov [KT_IN - 1 + ecx], al
    mov al, [edi + ecx * 2]
    mov [KT_IN + 3 + ecx], al
    loop .in
    pop eax
    mov bl, BLACK_
    test eax, eax
    jz .ref
    mov al, YELLOW_                     ; yellow unless a team's shirt or stripes clash with it
    mov dl, [esi + 2]
    call kt_cl
    jc .ref
    mov dl, [esi + 4]
    call kt_cl
    jc .ref
    mov dl, [edi + 2]
    call kt_cl
    jc .ref
    mov dl, [edi + 4]
    call kt_cl
    jc .ref
    mov bl, YELLOW_
.ref:
    mov [KT_REF], bl
    cmp bl, YELLOW_
    jne .k
    mov ecx, REF0_                      ; his shirt mask: 3 -> 15 on 1273..1283 (masks 116..126)
.rl:
    lea edx, [ecx - REF0_ + KEEPN_]
    push ebx
    mov bx, 0F03h
    call kt_mask
    pop ebx
    inc ecx
    cmp ecx, REF0_ + REFN_
    jb .rl
.k:
    call kg_match                       ; (4.2: HS1 / HS2 from SELECT KITS' keeper page, by the teams' names)
    xor ecx, ecx                        ; keeper 1: own A5, other A6, no other keeper yet
    mov ebx, HS1
    mov ebp, KK1
    call kt_pick
    xchg esi, edi                       ; keeper 2: own A6, other A5, not keeper 1's shirt
    movzx ecx, byte [KK1]
    mov ebx, HS2
    mov ebp, KK2
    call kt_pick
    popad
    ret

kt_pick:                                ; esi / edi -> own / other TeamGame, cl = the other keeper's shirt (0 = none),
    cmp byte [ebx + 3], 0               ; ebx -> a hand-set kit (shirt, shorts, socks, on), ebp -> the kit out
    je .auto
    mov al, [ebx]                       ; hand-set: kept unless it clashes with the other team / referee / keeper
    call kt_okx
    jc .auto
    mov ax, [ebx]
    mov [ebp], ax
    mov al, [ebx + 2]
    mov [ebp + 2], al
    ret
.auto:
    push ebx
    mov ebx, KT_PREF
.n: mov al, [ebx]
    test al, al
    jz .old
    inc ebx
    call kt_okx
    jc .n
    xchg esi, edi
    call kt_okt                         ; (xchg keeps the flags)
    xchg esi, edi
    jc .n
    mov [ebp], al
    mov al, BLACK_                      ; shorts / socks black, white when black clashes with the other's shorts
    mov dl, [edi + 6]
    call kt_cls
    jnc .s
    mov al, WHITE_
.s: mov [ebp + 1], al
    mov [ebp + 2], al
    pop ebx
    ret
.old:
    mov byte [ebp], OLD_                ; no colour free: the game's keeper
    mov al, [esi + 6]
    mov [ebp + 1], al
    mov al, [esi + 8]
    mov [ebp + 2], al
    pop ebx
    ret

kt_okx:                                 ; al = a shirt: CF = 1 if it clashes with the team at edi, the referee or is
    call kt_okt                         ; the other keeper's (cl)
    jc .r
    mov dl, [KT_REF]
    call kt_cl
    jc .r
    cmp al, cl
    jne .ok
    stc
    ret
.ok: clc
.r: ret

kt_okt:                                 ; al vs the shirt / stripes of the TeamGame at edi
    mov dl, [edi + 2]
    call kt_cl
    jc .r
    mov dl, [edi + 4]
    call kt_cl
.r: ret

kt_cls:                                 ; CF = 1: al and dl clash (the shorts table), either way round
    push ebx
    mov ebx, KT_ES
    jmp kt_c
kt_cl:                                  ; CF = 1: al and dl clash (the basic table), either way round
    push ebx
    mov ebx, KT_EB
kt_c:
    push eax
    push ecx
    push edx
    and eax, 15
    and edx, 15
    movzx ecx, word [ebx + eax * 2]
    bt ecx, edx
    jc .y
    movzx ecx, word [ebx + edx * 2]
    bt ecx, eax
.y: pop edx
    pop ecx
    pop eax
    pop ebx
    ret

kt_conv1:                               ; the keeper loops' `mov A0, offset teamNPlayersColorTable`, sprite [D0]
    pushad
    mov esi, TAB1
    mov edi, KT1
    mov ebx, KK1
    mov ebp, KEEP1_
    jmp kt_conv
kt_conv2:
    pushad
    mov esi, TAB2
    mov edi, KT2
    mov ebx, KK2
    mov ebp, KEEP2_
kt_conv:
    push edi                            ; the team table as it is now (the goalie's skin in it)
    mov ecx, 16
    rep movsw
    pop edi
    mov [A0], edi
    movzx eax, byte [ebx]               ; 10 / 11 = the keeper's shirt, 14 / 15 his shorts / socks
    mov [edi + 20], ax
    mov [edi + 22], ax
    mov al, [ebx + 1]
    mov [edi + 28], ax
    mov al, [ebx + 2]
    mov [edi + 30], ax
    movzx ecx, word [D0]
    mov edx, ecx
    sub edx, ebp
    cmp edx, KEEPN_
    jae .x
    mov bx, 0B08h                       ; his shirt mask: 8 -> 11
    call kt_mask
%if W27_
    cmp byte [KT_W27], 0                ; 4.2 gloves (David Foster; World 2026-27 only). KT_W27 = 'this match is World 2026-27's' (the engine's
                                        ; swe_match_w27, stored by kt_chain): a WORLD flag, read by the referee rule AND here, not the referee's own
                                        ; switch - a later referee-kit change must keep it as it is. The hand pixels
    je .ng                              ; (skin 5 / 6 touching the shirt: gkgloves.py) -> entry 7, which this table maps to white
    mov word [edi + 14], WHITE_
    call kt_gl
.ng:
%endif
    inc dword [KT_CONV]
.x: popad
    ret

kt_gl:                                  ; ecx = sprite, edx = keeper frame: its glove pixels (KT_HC: count | first row << 3, KT_HP: one
    pushad                              ; byte a pixel, (row - first row) << 4 | x) 5 / 6 -> 7
    mov esi, [SGP]
    mov esi, [esi + ecx * 4]
    test esi, esi
    jz .x
    cmp word [esi + 14], 1              ; (16 px wide)
    jne .x
    xor ebx, ebx                        ; the pixels of the frames before this one
    xor eax, eax
.s: cmp eax, edx
    jae .c
    movzx ecx, byte [KT_HC + eax]
    and ecx, 7
    add ebx, ecx
    inc eax
    jmp .s
.c: movzx ecx, byte [KT_HC + edx]
    mov ebp, ecx
    shr ebp, 3                          ; first row
    and ecx, 7
    lea ebx, [KT_HP + ebx]
    mov edi, [esi]
.p: test ecx, ecx
    jz .x
    movzx eax, byte [ebx]
    inc ebx
    dec ecx
    mov edx, eax
    shr eax, 4
    add eax, ebp                        ; row
    and edx, 15                         ; x
    cmp ax, [esi + 12]                  ; (rows)
    jae .p
    lea eax, [edi + eax * 8]
    shr edx, 1                          ; CF = x odd (chunky: the high nibble first)
    lea eax, [eax + edx]
    mov dl, [eax]
    jc .lo
    and dl, 0Fh                         ; (whatever skin entry the game left there: the position is the hand)
    or dl, 70h
    mov [eax], dl
    jmp .p
.lo:
    and dl, 0F0h
    or dl, 7
    mov [eax], dl
    jmp .p
.x: popad
    ret

kt_mask:                                ; ecx = sprite, edx = mask, bl -> bh on the mask's pixels (chunky: 8 B a row,
    pushad                              ; the high nibble first)
    mov esi, [SGP]
    mov esi, [esi + ecx * 4]
    test esi, esi
    jz .x
    cmp word [esi + 14], 1              ; (16 px wide)
    jne .x
    movzx eax, word [KT_MOFF + edx * 2]
    add eax, KT_MS
    movzx ecx, byte [eax]               ; its first row, rows
    movzx edx, byte [eax + 1]
    lea ebp, [ecx + edx]
    cmp bp, [esi + 12]
    ja .x
    mov edi, [esi]
    lea edi, [edi + ecx * 8]
    add eax, 2
.row:
    test edx, edx
    jz .x
    push edx
    movzx ebp, word [eax]
    add eax, 2
    xor ecx, ecx
.b: mov dl, [edi + ecx]
    test bp, 8000h
    jz .lo
    mov dh, dl
    shr dh, 4
    cmp dh, bl
    jne .lo
    and dl, 0Fh
    mov dh, bh
    shl dh, 4
    or dl, dh
.lo:
    test bp, 4000h
    jz .st
    mov dh, dl
    and dh, 0Fh
    cmp dh, bl
    jne .st
    and dl, 0F0h
    or dl, bh
.st:
    mov [edi + ecx], dl
    shl bp, 2
    inc ecx
    cmp ecx, 8
    jb .b
    add edi, 8
    pop edx
    dec edx
    jmp .row
.x: popad
    ret


; --- 4.2 SELECT KITS keeper page (kitcolors' kg_slot -> kg_hook; Davide 12/11: SELECT KITS only, SOLO PARTITA /
; SEMPRE, a hand-set kit that clashes falls back to the automatic colour for that match) ------------------------------
kg_match:                               ; esi / edi -> TeamGame 1 / 2: HS1 / HS2 <- an armed keeper slot of that name
    pushad                              ; (team 1 tries slot 0 first, team 2 slot 1: a training game's two teams
    mov ebx, HS1                        ;  share one name), else the build's HD1 / HD2 (0 = automatic)
    mov edx, HD1
    mov ebp, KS
    call .one
    mov esi, edi
    mov ebx, HS2
    mov edx, HD2
    mov ebp, KS + KS_
    call .one
    popad
    ret
.one:
    mov eax, [edx]
    mov [ebx], eax
    cmp byte [KG_ARM], 0
    je .rec
    call .try
    jnc .x
    add ebp, KS_                        ; (the other slot)
    cmp ebp, KS + 2 * KS_
    jb .o2
    mov ebp, KS
.o2:
    call .try
    jnc .x
.rec:
    call kk_rec                         ; (no armed slot of that name: the career club's KEEPKIT.DAT record)
.x: ret
.try:                                   ; ebp -> slot: CF = 1 not this team's; its name: CF = 0, SET -> [ebx] (AUTO:
    push esi                            ; as is - SOLO PARTITA's AUTO wins over a stored record too)
    push edi
    add esi, 16h                        ; TeamGame.teamName
    mov edi, ebp
    call kk_same
    pop edi
    pop esi
    jne .no
    cmp byte [ebp + 21], 0
    je .tk
    push esi
    mov esi, ebp
    call kk_kit
    pop esi
.tk:
    clc
    ret
.no:
    stc
    ret

kg_open:                                ; kitcolors' 5-byte sites (KG_SITES) -> these; eax out, the rest kept
    mov eax, 9
    jmp kg_hook
kg_new:
    mov eax, 1
    jmp kg_hook
kg_load:
    mov eax, 2
    jmp kg_hook
kg_vis:
    mov eax, 3
    jmp kg_hook
kg_save:
    mov eax, 4
    jmp kg_hook
kg_reset:
    mov eax, 5
    jmp kg_hook
kg_ok:
    mov eax, 7
    jmp kg_hook
kg_cancel1:
kg_cancel2:
    mov eax, 8
    jmp kg_hook

kg_gk:                                  ; SELECT KITS entry 24: the editor on the goalkeeper's kit / back on the team's
    pushad
    call SAVE_KITS
    xor byte [KG_MODE], 1
    popad
    call KM_INIT
    jmp DRAW_MENU

kg_hook:                                ; eax = op, eax out; the rest kept
    push ebx
    push ecx
    push edx
    push esi
    push edi
    push ebp
    push dword [D0]
    push dword [A0]
    movzx ecx, byte [KM_TEAM]
    imul ebp, ecx, KS_
    add ebp, KS                         ; ebp -> the edited team's keeper slot
    mov edx, eax
    xor eax, eax
    cmp edx, 1
    je .new
    cmp edx, 9
    je .open
    cmp edx, 7
    je .ok
    cmp edx, 8
    je .cancel
    cmp byte [KG_MODE], 0               ; the rest act on the keeper page only (3: entry 24's text always)
    jne .page
    cmp edx, 3
    je .vis
    jmp .out
.page:
    cmp edx, 2
    je .load
    cmp edx, 3
    je .vis
    cmp edx, 4
    je .save
    cmp edx, 5
    je .reset
.out:
    pop dword [A0]
    pop dword [D0]
    pop ebp
    pop edi
    pop esi
    pop edx
    pop ecx
    pop ebx
    ret

.new:                                   ; KITS on a new match: both slots named, AUTO, nothing armed
    mov byte [KG_ARM], 0
    mov edi, KS
    mov esi, SLOTS
    call .name
    mov edi, KS + KS_
    mov esi, SLOTS + SLOT_
    call .name
    call kk_fill                        ; (a career: the club's KEEPKIT.DAT record, SET)
    jmp .out
.name:
    push edi
    mov ecx, KS_ / 4
    xor eax, eax
    rep stosd
    pop edi
    mov ecx, 18
    rep movsb
    ret
.open:
    mov byte [KG_MODE], 0
    jmp .out
.ok:
    mov byte [KG_ARM], 1
    call kk_keep                        ; (SEMPRE in a career: KEEPKIT.DAT)
    xor eax, eax
    jmp .out
.cancel:
    mov byte [KG_ARM], 0
    jmp .out

.load:                                  ; editTeamsTeam's first kit <- the keeper's: plain shirt, shorts, socks
    lea esi, [ebp + 18]
    cmp byte [ebp + 21], 0
    jne .l
    mov esi, GK_DEF                     ; (AUTO: David's look shown, grey / black / black)
.l: mov edi, EDIT_TEAM + 26
    mov byte [edi], 0
    mov al, [esi]
    mov [edi + 1], al
    mov [edi + 2], al
    mov al, [esi + 1]
    mov [edi + 3], al
    mov al, [esi + 2]
    mov [edi + 4], al
    jmp .out

.save:                                  ; the keeper page's first kit -> the keeper slot (set); eax = 1: the team's
    mov esi, EDIT_TEAM + 26             ; kits untouched. Unchanged from AUTO's shown look: still AUTO
    mov al, [esi + 1]
    mov ah, [esi + 3]
    mov dl, [esi + 4]
    cmp byte [ebp + 21], 0
    jne .sv
    cmp al, [GK_DEF]
    jne .sv
    cmp ah, [GK_DEF + 1]
    jne .sv
    cmp dl, [GK_DEF + 2]
    je .one1
.sv:
    mov [ebp + 18], al
    mov [ebp + 19], ah
    mov [ebp + 20], dl
    mov byte [ebp + 21], 1
.one1:
    mov eax, 1
    jmp .out
.reset:
    mov byte [ebp + 21], 0
    mov eax, 1
    jmp .out

.vis:                                   ; entry 24's text; the keeper page hides 2 and 8..19, entry 4 = its title
    mov edi, GK_BUF
    cmp byte [KG_MODE], 0
    je .t1
    mov esi, TXT_GBACK
    call .cat
    jmp .t2
.t1:
    mov esi, TXT_GK
    call .cat
    mov esi, TXT_GAUTO
    cmp byte [ebp + 21], 0
    je .t3
    mov esi, TXT_GSET
.t3:
    call .cat
.t2:
    mov byte [edi], 0
    movzx ebx, byte [KG_MODE]
    mov ecx, 2
    call .hide
    mov ecx, 8
.h: call .hide
    inc ecx
    cmp ecx, 20
    jb .h
    mov dword [D0], 4                   ; entry 4: FIRST KIT / the keeper title
    call CALC
    mov esi, [A0]
    mov eax, [esi + 26h]
    cmp eax, TXT_GLABEL
    je .g
    mov [KG_ORIG4], eax
.g: mov eax, [KG_ORIG4]
    cmp byte [KG_MODE], 0
    je .g2
    mov eax, TXT_GLABEL
.g2:
    mov [esi + 26h], eax
    jmp .out
.hide:                                  ; entry ecx hidden = bl
    push ebx
    push ecx
    mov [D0], ecx
    call CALC
    pop ecx
    pop ebx
    mov esi, [A0]
    movzx eax, bl
    mov [esi + 4], ax
    ret
.cat:
    lodsb
    test al, al
    jz .c2
    stosb
    jmp .cat
.c2:
    ret

    align 4
    db 'KITS'
KT_REF: db 0                            ; this match's referee shirt (3 / 15), swe_match_w27's answer
KT_W27: db 0
    db 0, 0
KK1: db 0, 0, 0, 0                      ; the keepers' kits (shirt, shorts, socks entries)
KK2: db 0, 0, 0, 0
HS1: db 0, 0, 0, 0                      ; hand-set keeper kits (shirt, shorts, socks entries, on) at this kick-off:
HS2: db 0, 0, 0, 0                      ; kg_match (SELECT KITS / KEEPKIT.DAT, else HD1 / HD2)
KT_CALLS: dd 0                          ; (harness: kt_chain runs, keeper sprites masked)
KT_CONV: dd 0
KT_IN: times 8 db 0
KT_W27P: dd W27V                        ; (harness: -> the engine's SWE_W27, 0 = none)
KT_W27F: dd W27FN                       ; (host test: -> swe_match_w27, 0 = none)
KT1: times 16 dw 0
KT2: times 16 dw 0
KG_MODE: db 0                           ; (4.2 keeper page) SELECT KITS on the keeper's kit
KG_ARM: db 0                            ; OK pressed: the slots' set kits are this match's
    db 0, 0
KG_ORIG4: dd 0                          ; entry 4's own text (FIRST KIT)
KS: times 2 * KS_ db 0                  ; per team: name 18, shirt, shorts, socks (kit colours 0..10), set, pad
HD1: db HAND1_                          ; (test builds: KITS_HAND1 / 2)
HD2: db HAND2_
KT_CODE: db 1, 2, 3, 6, 10, 11, 12, 13, 14, 15, 12   ; kit colour -> palette entry (shirtColorTable; purple 10 -> 12)
GK_DEF: db 0, 2, 2                      ; AUTO's look on the page: grey, black, black
"""

KEEPN, REFN = 116, 11
LABELS = {}


def build_masks(game):
    """(MOFF words: 116 keeper + 11 referee masks, MS bytes: per mask first row, rows, the row words) from a game dir"""
    import kitmask
    m = kitmask.build(game)
    ws = [w for _, w in m['keeper']] + [m['ref'][s]['shirt'][1] for s in REF_SPRITES]
    assert len(ws) == KEEPN + REFN
    moff, ms = [], bytearray()
    for w in ws:
        nz = [i for i, x in enumerate(w) if x]
        moff.append(len(ms))
        a, b = (nz[0], nz[-1] + 1) if nz else (0, 0)
        ms += bytes([a, b - a]) + struct.pack(f'<{b - a}H', *w[a:b])
    return moff, bytes(ms)


def build_hands(game):
    """(HC: per keeper frame count | first row << 3, HP: the glove pixels, one byte each: (row - first row) << 4 | x - frame by
    frame) - 4.2 gloves, kt_gl (page 16 had room for ~400 B: one byte a pixel)"""
    import kitmask
    hands = kitmask.build(game)['hands']
    assert len(hands) == KEEPN
    hc, hp = bytearray(), bytearray()
    for h in hands:
        y0 = min((y for y, _ in h), default=0)
        assert len(h) < 8 and y0 < 32 and all(y - y0 < 16 and x < 16 for y, x in h), h
        hc.append(len(h) | y0 << 3)
        hp += bytes((y - y0) << 4 | x for y, x in h)
    return bytes(hc), bytes(hp)


def write_masks(game, out):
    """tools/kitmasks.py (committed: builds need no game files; test_kits checks it against the sprites)"""
    moff, ms = build_masks(game)
    hc, hp = build_hands(game)
    h = ms.hex()
    with open(out, 'w') as f:
        f.write('"""Generated by kits.write_masks from GOAL1.DAT / BENCH.DAT / TEAM1.DAT (kitmask.py): do not edit."""\n')
        f.write(f'MOFF = {moff!r}\n')
        f.write('MS = bytes.fromhex(\n' + ''.join(f"    '{h[k:k + 112]}'\n" for k in range(0, len(h), 112)) + ')\n')
        f.write(f'HC = bytes.fromhex({hc.hex()!r})\nHP = bytes.fromhex({hp.hex()!r})\n')


def masks():
    import kitmasks
    return kitmasks.MOFF, kitmasks.MS


def hand_data():
    import kitmasks
    return kitmasks.HC, kitmasks.HP


def find(p):
    """the ChainFont call after LoadSpritesAndFixOffsets / D0 = 227 (then `cmp EGA_graphics, -1`) and the four keeper
    loops' `mov A0, offset teamNPlayersColorTable` (their `cmp word [D0], 1005 / 1063 / 1121 / 1179`)"""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d0, a0 = r['D7'] - 28, r['A0']
    cf = [m.start() + 15 for m in re.finditer(rb'\xe8....\xc7\x05' + pk(d0) + rb'\xe3\x00\x00\x00\xe8....\x66\x83\x3d....\xff',
                                              d1, re.S)]
    assert len(cf) == 1, ('ConvertColorsAndTextSprites: ChainFont', cf)
    loops = {}
    for m in re.finditer(rb'\xc7\x05' + pk(a0), d1):
        c = re.search(rb'\x66\x81\x3d' + pk(d0) + rb'(..)', d1[m.start():m.start() + 0x60], re.S)   # (the loop's
        lim = c and struct.unpack('<H', c.group(1))[0]                                               # first cmp)
        if lim in (1005, 1063, 1121, 1179):
            loops.setdefault(lim, []).append(m.start())
    assert sorted(loops) == [1005, 1063, 1121, 1179] and all(len(v) == 1 for v in loops.values()), ('keeper loops', loops)
    tabs = {lim: p.target(1, o[0] + 6) for lim, o in loops.items()}
    assert tabs[1005] == tabs[1063] and tabs[1121] == tabs[1179] and tabs[1005] != tabs[1121], tabs
    sgo = [m.start() + 9 for m in re.finditer(rb'\xc1\x25' + pk(d0) + rb'\x02\x8b\x35....\x03\x35' + pk(d0)
                                              + rb'\x8b\x06\x0b\xc0\x74', d1, re.S)]   # (ChainFont's loop & co.)
    assert sgo and len({p.target(1, o) for o in sgo}) == 1, 'g_spriteGraphicsPtr'
    return {'CF_AT': cf[0], 'LOOPS': {lim: o[0] for lim, o in loops.items()}, 'TAB1': tabs[1005], 'TAB2': tabs[1121],
            'D0': (2, d0), 'A0': (2, a0), 'A5': (2, a0 + 20), 'A6': (2, a0 + 24), 'SGP': p.target(1, sgo[0])}


def hand_env(name):
    """KITS_HAND1 / 2 = 'shirt,shorts,socks' palette entries (test builds only): a hand-set keeper kit"""
    import os
    v = os.environ.get(name)
    if not v:
        return '0, 0, 0, 0'
    import modver
    assert modver.is_test(), name + ': test builds only'
    a = [int(x) for x in v.split(',')]
    assert len(a) == 3 and all(0 < x < 16 for x in a), (name, v)
    return ', '.join(map(str, a + [1]))


KS_ = 24                                # a keeper slot: name 18, shirt, shorts, socks, set, pad 2
KK_, KK_N, KK_HDR = 24, 128, 12         # 4.2 KEEPKIT.DAT (MC 13/11): record, records, header ('KEEP', 1, count, stamp, 0)
KK_NAME = b'KEEPKIT.DAT'                # (the game folder: a user file, never shipped - mkpatcher asserts it)
# obj4 page 17 (swreg.KITS_PAGE16_END): 'KKST', the harness / host test block, then the file's image KK_FILE
KK_OFF = {'KK_LOADED': 4, 'KK_ERR': 8, 'KK_SAVES': 12, 'KK_EVICT': 16, 'KK_NAME': 72, 'KK_FILE': 88}
KK_PTRS = ('kk_keep', 'kk_load', 'kg_match', 'kg_new', 'CWB', 'GAMETYPE', 'CAREER_TEAM', 'KM_ALWAYS', 'KS', 'KG_ARM',
           'kk_fill', 'kk_rec')           # (dd at +20.., in this order)


def kk_page():
    """page 17's bytes before the pointers (KK_PTRS at +20, fixups): tag, state, name, an empty table"""
    b = bytearray(KK_OFF['KK_FILE'] + KK_HDR + KK_N * KK_)
    b[0:4] = b'KKST'
    assert 20 + 4 * len(KK_PTRS) <= KK_OFF['KK_NAME']
    b[KK_OFF['KK_NAME']:KK_OFF['KK_NAME'] + len(KK_NAME)] = KK_NAME
    b[KK_OFF['KK_FILE']:KK_OFF['KK_FILE'] + 12] = b'KEEP' + bytes((1, 0, 0, 0, 1, 0, 0, 0))
    return bytes(b)


def gk_texts():
    """the keeper page's texts in the exe's language (kitcolors.GK_TEXTS)"""
    import kitcolors
    t = kitcolors.GK_TEXTS[kitcolors.INFO['lang']]
    return ''.join(f"\nTXT_{k.upper()}: db {', '.join(map(str, v + bytes(1)))}" for k, v in t.items())


def patch(p):
    """Code + masks at obj4+swreg.KITS_AT (page 16, MC 12/11); after swe.patch (swe_match_w27). Returns the end."""
    import re
    import kitcolors
    import nasmcave
    import swe
    import swreg
    s = find(p)
    moff, ms = masks()
    hc, hp = hand_data()
    w27 = 'swe_match_w27' in swe.LABELS
    src = (f'%define W27_ {int(w27)}\n' + ''.join(f'%define {k}_ {v}\n' for k, v in (
        ('BLACK', BLACK), ('WHITE', WHITE), ('YELLOW', YELLOW), ('OLD', OLD_SHIRT), ('REF0', REF_SPRITES[0]),
        ('REFN', REFN), ('KEEPN', KEEPN), ('KEEP1', KEEPER_FIRST[0]), ('KEEP2', KEEPER_FIRST[1])))
        + f'%define HAND1_ {hand_env("KITS_HAND1")}\n%define HAND2_ {hand_env("KITS_HAND2")}\n' + ASM
        + 'KT_EB: dw ' + ', '.join(map(str, EB)) + '\nKT_ES: dw ' + ', '.join(map(str, ES))
        + '\nKT_PREF: db ' + ', '.join(map(str, PREF + (0,))) + '\nKT_MOFF: dw ' + ', '.join(map(str, moff))
        + '\nKT_MS: db ' + ', '.join(map(str, ms)) + '\nKT_HC: db ' + ', '.join(map(str, hc)) + '\nKT_HP: db ' + ', '.join(map(str, hp))
        + gk_texts() + '\nKT_END:\n')
    at = swreg.KITS_AT
    sym = {'CHAINFONT': p.call_target(1, s['CF_AT']), 'TAB1': s['TAB1'], 'TAB2': s['TAB2'], 'SGP': s['SGP'],
           **{k: s[k] for k in ('D0', 'A0', 'A5', 'A6')}}
    kc = kitcolors.INFO
    assert kc.get('kg_sites') and kc.get('sym'), 'kits: kitcolors.button first (the keeper page)'
    sym.update(kc['sym'], GK_BUF=kc['gkbuf'], KS_=(0, KS_), SLOT_=(0, kitcolors.SLOT))
    sym['W27V'] = swe.LABELS.get('SWE_W27', (0, 0))
    sym['W27FN'] = swe.LABELS.get('swe_match_w27', (0, 0))
    if w27:
        sym['SWE_W27F'] = swe.LABELS['swe_match_w27']
    import careerworld                                  # 4.2 KEEPKIT.DAT: the career's world byte (the moved SLT,
    import swefile                                      #  as swe.c's SWE_CWB), the file layer, page 17
    k17 = swreg.KITS_PAGE16_END
    kkw = careerworld.SITES.get('slt')
    sym['CWB'] = (kkw[0], kkw[1] + careerworld.WORLD_BYTE) if kkw else (4, k17 + KK_OFF['KK_LOADED'] + 1)
    assert swefile.LABELS, 'kits: KEEPKIT.DAT needs the file layer (swe.SWEFILE, patch.py)'
    sym.update(SWE_RECOVER=swefile.LABELS['swe_recover'], SWE_FOPEN_R=swefile.LABELS['swe_fopen_r'],
               SWE_FREAD=swefile.LABELS['swe_fread'], SWE_FCLOSE=swefile.LABELS['swe_fclose'],
               SWE_SAVE=swefile.LABELS['swe_save_atomic'], KK_=(0, KK_), KK_N=(0, KK_N), KK_HDR=(0, KK_HDR),
               **{k: (4, k17 + v) for k, v in KK_OFF.items()})
    kat = k17 + (len(kk_page()) + 15 & ~15)            # (4.2 KEEPKIT's code on page 17 after the table: page 16 is
    kk_names = re.findall(r'^(kk_\w+):', KK_ASM, re.M)  #  full; the two blocks call each other: labels first)
    dummy = {**sym, **{k: (4, 0) for k in ('KS', 'KT_CODE')}}     # (sym has no kk_* yet)
    klab = nasmcave.labels(KK_ASM, kat, dummy)
    sym.update({k: (4, klab[k]) for k in kk_names})
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    ksym = {**{k: v for k, v in sym.items() if k not in kk_names}, 'KS': (4, lab['KS']), 'KT_CODE': (4, lab['KT_CODE'])}
    kcode, kfix, krel = nasmcave.assemble_obj(KK_ASM, kat, ksym, 4)
    assert nasmcave.labels(KK_ASM, kat, ksym) == klab
    assert kat + len(kcode) <= swreg.KITS_END, ('kits: KEEPKIT code past page 17', hex(kat + len(kcode)))
    lab.update(klab)
    end = at + len(code)
    page = swreg.KITS_PAGE16_END
    assert end <= page, ('kits: code + masks past page 16 (MC: masks to page 17, never cut code)', hex(end))
    assert p.le.obj(4).npages * 0x1000 >= page, 'kits: obj4 pages (patch.py)'
    assert not any(p.get(4, at, page - at)), 'kits: obj4 room not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.branch(1, s['CF_AT'], 0xE8, 4, lab['kt_chain'])
    kp = kk_page()                                      # (4.2 KEEPKIT.DAT: page 17)
    assert k17 + len(kp) <= swreg.KITS_END and p.le.obj(4).npages * 0x1000 >= swreg.KITS_END, 'kits: page 17'
    assert not any(p.get(4, k17, swreg.KITS_END - k17)), 'kits: page 17 not free'
    p.put(4, k17, kp)
    p.put(4, kat, kcode)
    for o, t_obj, t_off in kfix:
        p.add_ptr(4, kat + o, t_obj, t_off)
    for o, t_obj, t_off in krel:
        p.add_rel(4, kat + o, t_obj, t_off)
    for i, k in enumerate(KK_PTRS):
        t = sym[k] if k in sym else (4, lab[k])
        p.put(4, k17 + 20 + 4 * i, bytes(4))
        p.add_ptr(4, k17 + 20 + 4 * i, t[0], t[1])
    for k, o in kc['kg_sites'].items():                 # (4.2: SELECT KITS' keeper page)
        assert p.get(1, o, 5) == bytes((0x0F, 0x1F, 0x44, 0, kitcolors.KG_SITES[k])), k
        p.branch(1, o, 0xE8, 4, lab[k])
    assert p.get(2, kc['gk_sel'], 4) == bytes(4)
    p.add_ptr(2, kc['gk_sel'], 4, lab['kg_gk'])         # (entry 24's select function)
    for lim, o in s['LOOPS'].items():
        assert p.get(1, o, 2) == b'\xc7\x05' and p.target(1, o + 6) == (s['TAB1'] if lim < 1100 else s['TAB2'])
        p.remove(1, o + 2)                              # (A0's and the table's fixups: the 10 bytes are overwritten)
        p.remove(1, o + 6)
        p.branch(1, o, 0xE8, 4, lab['kt_conv1' if lim < 1100 else 'kt_conv2'], n=10)
    LABELS.clear()
    LABELS.update(lab)
    print(f'exe: kits (K2 keepers, R1 referee{"" if w27 else " - no swe_match_w27: always black"}): obj4+{at:#x}..'
          f'{end:#x} ({len(code)} B, masks {len(ms) + 2 * len(moff)} B; page 16 margin {page - end} B), KEEPKIT.DAT '
          f'table obj4+{k17:#x}..{k17 + len(kp):#x} ({KK_N} x {KK_} B) + code ..{kat + len(kcode):#x} '
          f'({swreg.KITS_END - kat - len(kcode)} B left), '
          f'ChainFont call obj1+{s["CF_AT"]:#x}, keeper loops ' + ', '.join(f'{v:#x}' for v in s['LOOPS'].values()))
    return end
