"""Italian play-offs / play-outs of a career world: the glue around tools/dplay.c (rules there).

Season end (cseg_91D4D, per league struct A4): every division is played (the career club's) or simulated, then
cseg_9221F copies its play-off candidates; after all divisions cseg_9228D runs the native play-offs per division.
- dp_cap replaces `call cseg_9221F`: in a league of DP_TAB (pack.json league 'playoffs': 'ita', with 'parallel') the
  final table of Serie B and of each Serie C group (DIY+6Dh rows in order: team number, global number from the team
  record +2, wins, goals, points) into DP_IN;
- dp_end replaces `call cseg_9228D`: after the league's last division, dp_season() (C) and its moves into
  leaguesTableCopy (signed division deltas, as cseg_925C9 adds the native play-offs' ones), the promotion /
  relegation animation when the career club moves. pgroups (InitializeNewSeason's copy-back) then puts the Serie B
  play-out loser into its area's group and a group's play-off winner into Serie B, as the group winners.
Data: Serie B promoted 2 / relegated 3, the groups promoted 1 / relegated 0 (the play-offs add 1 up and 1 down).

The career club's own Serie B play-off or play-out is played (step 2), as the game's native division play-off:
- dp_lend replaces the two `call cseg_8ECAE` (the career league's last match day): Serie B of DP_TAB -> its final
  table (competitionFileBuffer) into DP_IN, dp_lend() (C) -> the state (DP_ST in the C .bss; its copy DP_SAVE in
  tmdFileBuffer is saved with the career and wins when valid: dp_sync; the season end may clear that copy) and, when the
  club plays one, its contest into slot 4 as InitializeNewSeason builds a native one (cseg_8B2D3, D0 = 4: buffer and
  calendar, dated after the last week), then its clubs as cseg_8ECAE's tail puts them (team list dseg_114EE4).
  PLAY-OFF SERIE B (FD): 6 clubs in the order 5th, 8th, 6th, 7th, 3rd, 4th, no draw (header byte 8), 2 byes (lib97
  BYE_TAB: the 3rd and the 4th wait), rounds single + extra time without penalties / two legs / two legs; PLAY-OUT
  SERIE B (FE): 17th, 16th, two legs (extra time + penalties when level on points).
- dp_perm (lib97 nc_adv, after the round's draw): the semis 3rd v W(6v7), 4th v W(5v8), the return at the 3rd / 4th's;
  the final's first leg at the worse placed's, its legs / extra time / penalties words (level on points: both).
- dp_draw (after historic's coin_draw at cseg_2AE97's 'draw -> replay' mark): a level tie of ours -> the better
  placed club (the 16th in the play-out); dp_rec (cseg_2AE97's end): the last round's winner into the state;
- dp_end: the state's winner instead of the simulated one. (cseg_91D4D runs for every country at the season end; the
  state is used and cleared by Italy's.) Round names: the game's (the preliminary round shows as the first round, no
  'TURNO PRELIMINARE' in its table), dp_round through uefaq's uq_rn1 / uq_rn2.
"""
import os
import re
import struct

DP_PO, DP_OUT = 0xFD, 0xFE      # contest ids (mkseason.RESERVED_IDS)
NAMES = (b'PLAY-OFF SERIE B', b'PLAY-OUT SERIE B')
SAVE_AT = 0xC000                # dp_save in tmdFileBuffer (the 80-record area; after uefaq's state, before BIGC)

ASM = '''
dp_find:                                ; edx = a league struct -> esi = its DP_TAB entry in the running world, or ZF = 1
    mov al, [SLT + WORLD_BYTE]
    mov ah, [edx]
    mov esi, DP_TAB
.l:
    cmp byte [esi], 0
    je .no
    cmp [esi], ax                       ; (world, league id)
    je .yes
    add esi, 5
    jmp .l
.yes:
    or esi, esi                         ; (ZF = 0)
    ret
.no:
    xor esi, esi
    ret

dp_rows:                                ; eax = DP_IN table, ebp = a league buffer (DIY layout): its sorted table
    movzx ecx, word [ebp + 31h]
    cmp ecx, NT
    jbe .n
    mov ecx, NT
.n:
    mov [DP_IN + O_N + eax], cl
    imul edi, eax, NT * RSZ
    add edi, DP_IN + O_T
    xor ebx, ebx
.r:
    cmp ebx, ecx
    jae .x
    movzx esi, word [ebp + 6Dh + ebx * 2]   ; the place's row offset (row * 12h)
    mov eax, esi
    xor edx, edx
    push ecx
    mov ecx, 12h
    div ecx
    pop ecx
    mov ax, [ebp + 12Dh + eax * 2]      ; its team number
    mov [edi], ax
    mov edx, [ebp + esi + 2B3h]         ; its team record: the global number
    add edx, [SELTEAMS]
    mov ax, [edx + 2]
    mov [edi + 2], ax
    mov ax, [ebp + esi + 2B9h]          ; won
    mov [edi + 4], ax
    mov ax, [ebp + esi + 2BFh]          ; for
    mov [edi + 6], ax
    mov ax, [ebp + esi + 2C1h]          ; against
    mov [edi + 8], ax
    mov ax, [ebp + esi + 2C3h]          ; points
    mov [edi + 10], ax
    add edi, RSZ
    inc ebx
    jmp .r
.x:
    ret

dp_cap:                                 ; replaces `call cseg_9221F` in cseg_91D4D
    call C9221F
    pushad
    mov edx, [A4R]
    call dp_find
    jz .x
    movzx eax, word [D7R]               ; the division -> table 0 (Serie B) or 1.. (the groups)
    movzx ecx, byte [esi + 2]
    sub eax, ecx
    jb .x
    movzx ecx, byte [esi + 4]
    cmp eax, ecx
    ja .x
    mov ebp, DIY
    call dp_rows
.x:
    popad
    ret

dp_end:                                 ; replaces `call cseg_9228D` (the play-offs of division D7) in cseg_91D4D
    call C9228D
    pushad
    mov edx, [A4R]
    call dp_find
    jz .x
    mov edx, [A4R]
    movzx eax, word [D7R]
    inc eax
    cmp al, [edx + 9]                   ; (the league's last division)
    jne .x
    mov al, [esi + 4]
    mov [DP_IN], al                     ; ng
    xor eax, eax                        ; the career club's play-off / play-out played in slot 4
    mov [DP_IN + O_PO], eax
    call dp_sync
    jne .s
    mov ax, [DP_ST + 2]
    cmp byte [DP_ST + SV_KIND], 2
    je .so
    mov [DP_IN + O_PO], ax
    jmp .lg
.so:
    mov [DP_IN + O_PO + 2], ax
.lg:
    push es                             ; the season's log (saved: harness): 'DPLG', the state, the moves
    push ds
    pop es
    cld
    mov dword [DP_LOG], 'DPLG'
    mov esi, DP_ST
    mov edi, DP_LOG + 4
    mov ecx, SV_SIZE
    rep movsb
    pop es
.s:
    mov word [DP_ST], 0
    mov word [DP_SAVE], 0
    movzx ecx, byte [DP_IN]
.c:
    cmp byte [DP_IN + O_N + ecx], 0     ; every table captured (else nothing moves)
    je .clr
    dec ecx
    jns .c
    push es
    push ds
    pop es
    cld
    call dp_season
    mov esi, DP_OUTB                    ; (log: the moves)
    mov edi, DP_LOG + 4 + SV_SIZE
    mov ecx, O_MV + 4 * MSZ
    rep movsb
    pop es
    movzx ecx, byte [DP_OUTB]
    xor ebx, ebx
.m:
    cmp ebx, ecx
    jae .clr
    imul esi, ebx, MSZ
    add esi, DP_OUTB + O_MV
    movzx eax, word [esi]               ; global number
    mov dl, [esi + 4]
    add [SLTCOPY + eax], dl
    mov ax, [esi + 2]
    cmp ax, [CAREERTEAM]
    jne .nm
    test dl, dl
    js .up
    mov word [ANIM_REL], 1
    jmp .nm
.up:
    mov word [ANIM_PRO], 1
.nm:
    inc ebx
    jmp .m
.clr:
    mov edi, DP_IN + O_N
    xor eax, eax
    mov ecx, NDIV
    push es
    push ds
    pop es
    cld
    rep stosb
    pop es
.x:
    popad
    ret

dp_lend:                                ; replaces `call cseg_8ECAE` (the career league's last match day)
    pushad
    mov edx, [D8CAA]
    test edx, edx
    jz .nat
    call dp_find
    jz .nat
    movzx eax, byte [esi + 2]
    cmp ax, [D6CDC]                     ; (the career club's division: Serie B)
    jne .nat
    xor eax, eax
    mov ebp, CFB
    call dp_rows
    mov ax, [CAREERTEAM]
    mov [DP_IN + O_MGR], ax
    movzx eax, word [CAL_CUR]           ; the week of the match day just played (its calendar entry +1)
    movzx eax, byte [CAL + eax + 1]
    mov [DP_IN + O_MGR + 2], ax
    mov dword [DP_SVP], DP_ST
    push es
    push ds
    pop es
    cld
    call dp_lend_c
    mov al, [SEASONPLAYING]             ; (the state's season)
    mov [DP_ST + SV_KIND + 2], al
    mov esi, DP_ST                      ; the saved copy (tmdFileBuffer: a career saved during the play-off)
    mov edi, DP_SAVE
    mov ecx, SV_SIZE
    rep movsb
    pop es
    mov byte [DP_IN + O_N], 0
    cmp word [DP_ST], 5044h
    jne .x
    mov edi, DP_C0                      ; the contest: its weeks, round bytes
    cmp byte [DP_ST + SV_KIND], 1
    je .k
    mov edi, DP_C1
.k:
    mov al, [DP_ST + SV_RB + 3]
    mov [edi + 3], al
    mov al, [DP_ST + SV_RB + 4]
    mov [edi + 4], al
    mov al, [DP_ST + SV_RB]           ; round bytes from header +0Eh (the play-off's 3rd: dp_perm)
    mov [edi + 14], al
    cmp byte [DP_ST + SV_KIND], 1
    jne .b
    mov ax, [DP_ST + SV_RB + 1]
    mov [edi + 15], ax
.b:
    push edi
    push es
    push ds
    pop es
    mov edi, SLOT4                      ; slot 4 cleared, as never used this season
    mov ecx, 443h
    xor eax, eax
    cld
    rep stosb
    pop es
    pop edi
    mov [A0R], edi                      ; slot 4: buffer + calendar (cseg_8B2D3, as cseg_8DAC3 at a season start)
    mov word [D0R], 4
    mov word [D1R], 0
    mov word [D2R], 0
    pushad
    call C8B2D3
    popad
    movzx ecx, byte [DP_ST + SV_KIND + 1]   ; (n)
    xor ebx, ebx
.t:
    mov ax, [DP_ST + SV_TEAM + ebx * 2]   ; its clubs, as cseg_8ECAE's loop lists them
    mov [LIST4 + ebx * 2], ax
    inc ebx
    cmp ebx, ecx
    jb .t
    mov dword [A4R], SLOT4              ; cseg_8ECAE's tail: teams into slot 4, pointers, saved; no sacking
    mov word [D7R], 0
    pushad
    call C8EE5D
    popad
.x:
    popad
    ret
.nat:
    popad
    jmp C8ECAE

dp_ours:                                ; ZF = 1 if DIY holds our contest and the state runs
    call dp_sync
    jne .r
    cmp byte [DIY + 2Dh], DPID_PO
    je .r
    cmp byte [DIY + 2Dh], DPID_OUT
.r:
    ret

dp_sync:                                ; ZF = 1 if the state of this season runs (DP_ST); the saved copy wins when
    pushad                              ; valid (a career loaded during its play-off); the season end may clear it
    mov al, [SEASONPLAYING]
    cmp word [DP_SAVE], 5044h
    jne .b
    cmp [DP_SAVE + SV_KIND + 2], al
    jne .b
    push es
    push ds
    pop es
    cld
    mov esi, DP_SAVE
    mov edi, DP_ST
    mov ecx, SV_SIZE
    rep movsb
    pop es
.b:
    cmp word [DP_ST], 5044h
    jne .x
    cmp [DP_ST + SV_KIND + 2], al
.x:
    popad
    ret

dp_idx:                                 ; ax = a team number -> ebx = its index in the state (or 6)
    xor ebx, ebx
.l:
    cmp ax, [DP_ST + SV_TEAM + ebx * 2]
    je .r
    inc ebx
    cmp ebx, 6
    jb .l
.r:
    ret

dp_decisive:                            ; ZF = 0 if the match just played decides its tie (single, or a second leg)
    cmp word [DIY + 14Bh], 2
    jne .y
    cmp word [DIY + 149h], 0
    ret
.y:
    or esp, esp
    ret

dp_draw:                                ; at cseg_2AE97's 'draw -> replay' mark (after historic's coin_draw)
    call COIN_DRAW
    pushad
    call dp_ours
    jne .x
    call dp_decisive
    jz .x
    test byte [D7R], 2                  ; (decided already)
    jnz .x
    mov esi, [A1R]                      ; the better placed of the match's two clubs goes through
    mov ax, [esi]
    call dp_idx
    mov cl, [DP_ST + SV_PLACE + ebx]
    mov esi, [A2R]
    mov ax, [esi]
    call dp_idx
    mov ch, [DP_ST + SV_PLACE + ebx]
    and byte [D7R], 0FEh
    or byte [D7R], 2
    cmp ch, cl
    jae .x
    or byte [D7R], 1                    ; (the second club)
.x:
    popad
    ret

dp_rec:                                 ; replaces `mov ax, [dseg_11F9CC]` at cseg_2AE97's end (the match's result)
    pushad
    call dp_ours
    jne .x
    call dp_decisive
    jz .x
    test byte [D7R], 2
    jz .x
    mov ax, [DIY + 57h]                 ; (the last round)
    inc eax
    cmp ax, [DIY + 59h]
    jne .x
    mov esi, [A1R]
    test byte [D7R], 1
    jz .w
    mov esi, [A2R]
.w:
    mov ax, [esi]
    mov [DP_ST + 2], ax
    mov [DP_SAVE + 2], ax
.x:
    popad
    mov ax, [W11F9CC]
    ret

dp_perm:                                ; lib97 nc_adv: ecx = the next round's clubs, NC_T = the winners in tie order
    cmp byte [NCW + 2Dh], DPID_PO       ; (+ the byes) -> CF = 0: list +2CDh written
    jne .no
    pushad
    call dp_sync
    cmp ecx, 4
    jne .f
    mov eax, [NC_T]                     ; [W5v8, W6v7, 3rd, 4th] -> [W6v7, 3rd, W5v8, 4th]
    mov [NCW + 2CDh], ah
    shr eax, 16
    mov [NCW + 2CEh], al
    mov [NCW + 2D0h], ah
    mov al, [NC_T]
    mov [NCW + 2CFh], al
    jmp .x
.f:
    cmp ecx, 2
    jne .x
    movzx eax, byte [NC_T]              ; the final: the first leg at the worse placed's
    movzx ebx, byte [NC_T + 1]
    mov dl, [DP_ST + SV_PLACE + eax]
    cmp dl, [DP_ST + SV_PLACE + ebx]
    jb .sw
    mov [NCW + 2CDh], al
    mov [NCW + 2CEh], bl
    jmp .et
.sw:
    mov [NCW + 2CDh], bl
    mov [NCW + 2CEh], al
.et:
    mov dx, [DP_ST + SV_PTS + eax * 2]    ; level on points: extra time and penalties in the return
    cmp dx, [DP_ST + SV_PTS + ebx * 2]
    sete dl
    movzx edx, dl
    mov word [NCW + 65h + 4], 2         ; (round 3: the game decodes 2 round bytes for 6 clubs)
    mov [NCW + 71h + 4], dx
    mov [NCW + 7Dh + 4], dx
.x:
    popad
    clc
    ret
.no:
    stc
    ret

dp_round:                               ; uefaq uq_rn1 / uq_rn2 (cseg_280C0 / cseg_283BD, D0 = the round): CF = 1 and
    push eax                            ; D0 = the name (PRIMO TURNO 0 .. SEMIFINALE 7, FINALE 8) for ours, else
    mov al, [DIY + 2Dh]                 ; uefaq's own test (the contest in DIY, or the copy's)
    cmp al, DPID_OUT
    je .f
    cmp al, DPID_PO
    je .p
    mov al, [DIYCOPY + 2Dh]
    cmp al, DPID_OUT
    je .f
    cmp al, DPID_PO
    jne .no
.p:
    movzx eax, word [D0R]
    mov al, [DP_RN + eax]
    jmp .s
.f:
    mov al, 8
.s:
    movzx eax, al
    mov [D0R], ax
    pop eax
    stc
    ret
.no:
    pop eax
    jmp UQ_TIE_ROUND
DP_RN: db 0, 7, 8, 8                    ; (the preliminary round: the game has no such name)

DP_TAB: TAB_BYTES
'''


def _sites(p):
    """Season end (cseg_91D4D / cseg_925C9): (call of cseg_9221F, cseg_9221F, call of cseg_9228D, cseg_9228D, DIY,
    careerTeam, relegated / promoted animation flags, regs)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    a2 = r['A0'] + 8
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]
    # cseg_9221F: mov A2, offset DIY; mov esi, A2; mov ax, [esi+55h]; ... add eax, 1ADh; its one caller in cseg_91D4D
    c = [(m.start(), struct.unpack('<I', m.group(1))[0]) for m in re.finditer(
        rb'\xc7\x05' + pk(a2) + rb'(.{4})\x8b\x35' + pk(a2) + rb'\x66\x8b\x46\x55', d1, re.S)]
    c = [(a, diy, calls(a)) for a, diy in c]
    c = [x for x in c if len(x[2]) == 1]
    assert len(c) == 1, c
    c9221f, diy, (cap,) = c[0]
    c9228d = re.compile(rb'\x79.\xc3\x66\xa1' + pk(r['D7']), re.S).search(d1, c9221f).start() + 3   # (after its retn)
    assert c9228d - c9221f < 0x80, hex(c9228d)
    end = calls(c9228d)
    assert len(end) == 1 and cap < end[0] < cap + 0x80, (hex(cap), end)
    m = list(re.finditer(rb'\x81\x3d' + pk(r['A0']) + rb'(.{4})\x75.\xa0.{4}\x0a\xc0\x78.\x66\xc7\x05(.{4})\x01\x00\xeb.'
                         rb'\x66\xc7\x05(.{4})\x01\x00', d1, re.S))
    assert len(m) == 1, m
    ct, rel, pro = (struct.unpack('<I', g)[0] for g in m[0].groups())
    return cap, c9221f, end[0], c9228d, diy, ct, rel, pro, r


def _play_sites(p, r):
    """The career league's end and slot 4 (cseg_8ECAE and its two callers), cseg_2AE97's draw mark and end."""
    d1 = p.le.obj_bytes(1)
    pk = lambda x: struct.pack('<I', x)
    u = lambda a: struct.unpack_from('<I', d1, a)[0]
    # cseg_8E539 / cseg_8E841: mov ax, [esi+5Fh]; or ax, ax; jnz; call cseg_8ECAE
    lend = [m.start() + 9 for m in re.finditer(rb'\x66\x8b\x46\x5f\x66\x0b\xc0\x75.\xe8', d1, re.S)]
    tg = {a + 5 + struct.unpack_from('<i', d1, a + 1)[0] for a in lend}
    assert len(lend) == 2 and len(tg) == 1, lend
    c8ecae = tg.pop()
    # cmp [D8CBA], 0; jz; mov eax, [D8CC0]; mov [A6], eax; mov [A5], offset 114EE4; mov [A4], offset slot 4
    h = d1[c8ecae:c8ecae + 40]
    assert h[:2] == b'\x83\x3d' and h[13] == 0xa1 and h[18] == 0xa3 and h[23:25] == b'\xc7\x05' and h[33:35] == b'\xc7\x05', h.hex()
    assert u(c8ecae + 25) == r['A0'] + 20 and u(c8ecae + 35) == r['A0'] + 16
    d8cba, list4, slot4 = u(c8ecae + 2), u(c8ecae + 29), u(c8ecae + 39)
    body = d1[c8ecae:c8ecae + 0x280]
    m = re.search(rb'\xc7\x05' + re.escape(pk(r['A0'] + 4)) + rb'(.{4})\xe8', body, re.S)      # mov A1, offset cfb
    cfb = struct.unpack('<I', m.group(1))[0]
    m = re.search(rb'\x66\xa1(.{4})\x66\x39\x05' + re.escape(pk(r['D7'] - 28)), body, re.S)   # mov ax, [D6CDC]; cmp D0, ax
    d6cdc = struct.unpack('<I', m.group(1))[0]
    m = re.search(rb'\x66\xff\x0d' + re.escape(pk(r['D7'])) + rb'\x0f\x89.{4}\xff\x35' + re.escape(pk(r['D7'])), body, re.S)
    tail = c8ecae + m.start()                       # dec D7; jns (loop); push D7: entered with D7 = 0
    # cseg_8EA56 (the current calendar entry): mov [A0], offset calendar; mov ax, [current offset]
    m = re.search(rb'\xc7\x05' + re.escape(pk(r['A0'])) + rb'(.{4})\x66\xa1(.{4})\x66\xa3' + re.escape(pk(r['D7'] - 28))
                  + rb'\x81\x25', d1, re.S)
    cal, cal_cur = struct.unpack('<I', m.group(1))[0], struct.unpack('<I', m.group(2))[0]
    # cseg_2AE97: or byte [D7], 80h; or byte [D7], 2; mov ax, [dseg_11F9CC] (cseg_2B56A follows the first or)
    d7 = re.escape(pk(r['D7']))
    # historic's coin_draw site (cseg_2B52F): the same pattern as historic._coin_sites
    ors = [x.start() for x in re.finditer(re.escape(b'\x80\x0d' + pk(r['D7']) + b'\x08'), d1)]
    sites = [x.start() for x in re.finditer(b'\x80\x0d' + d7 + b'\x80\x80\x25' + d7 + b'\xfd\xeb', d1)]
    sites = [x for x in sites if 0 < x - ors[1] < 0x100]
    assert len(sites) == 1, sites
    m = [x for x in re.finditer(rb'\x80\x0d' + d7 + rb'\x80\x80\x0d' + d7 + rb'\x02\x66\xa1(.{4})\x66\x0b\xc0', d1, re.S)
         if 0 < x.start() - sites[0] < 0x80]                # (just after the draw mark)
    assert len(m) == 1, m
    rec = m[0].start() + 14
    w11f9cc = struct.unpack('<I', m[0].group(1))[0]
    return dict(lend=lend, c8ecae=c8ecae, tail=tail, d8caa=d8cba - 16, list4=list4, slot4=slot4, cfb=cfb,
                d6cdc=d6cdc, cal=cal, cal_cur=cal_cur, rec=rec, w11f9cc=w11f9cc, draw=sites[0])


def table_bytes(tables):
    out = bytearray()
    for world, lid, u, f, ng, _ in tables:
        assert 1 <= world <= 255 and f == u + 1 and 2 <= ng <= 4, (world, u, f, ng)
        out += bytes((world, lid, u, f, ng))
    return bytes(out + b'\0')


def bye_cups(tables):
    """lib97 BYE_TAB entries: the play-off's 6 clubs, 2 byes (the 3rd and the 4th)."""
    return [(DP_PO, world, 6, 2) for world, *_ in tables]


def _contests(p, area, lfile):
    """PLAY-OFF / PLAY-OUT SERIE B: type-1 cups in the layout of the game's Australian cup (mkseason 'national')."""
    import mkseason
    import sacups
    d2 = p.le.obj_bytes(2)
    lo = d2.find(mkseason.AU_CUP_SIG)
    assert lo >= 0 and d2.count(mkseason.AU_CUP_SIG) == 1
    out = []
    for cid, n, rounds, name in ((DP_PO, 6, 3, NAMES[0]), (DP_OUT, 2, 1, NAMES[1])):
        h = bytearray(d2[lo:lo + 14])
        h[0], h[2], h[8], h[10], h[11], h[13] = cid, lfile, 1, n, 0, 1    # no draw, no away goals
        h += bytes(rounds) + b'\0'
        h[5] = len(h) - 5
        h[7] = len(h) + 8 - 7
        rel = area.add(name + b'\0') - sacups.STR_BASE
        out.append(bytes(h) + struct.pack('<II', rel, rel) + bytes((lfile, 0)) * n)
    return out


LABELS = {}


def patch(p, at, limit, tables, bss_at, area):
    """tables: mkseason.dplay_tables() (one world). C + glue + the two contests in obj1 at..limit, the C .bss at obj2
    bss_at (0x1000). Returns the end."""
    import careerworld
    import cobj
    import lib97
    import mkseason
    import nasmcave
    import sacups
    import uefaq
    cap, c9221f, end_site, c9228d, diy, ct, rel, pro, r = _sites(p)
    ps = _play_sites(p, r)
    for s in (cap, end_site, *ps['lend']):
        assert p.get(1, s, 5) == p.le.obj_bytes(1)[s:s + 5], f'obj1+{s:#x} already hooked'
    assert p.get(1, ps['draw'], 1) == b'\xe8', 'historic coin_draw expected at the draw mark'
    coin = ps['draw'] + 5 + struct.unpack('<i', p.get(1, ps['draw'] + 1, 4))[0]
    assert lib97.LABELS.get('NC_DPP') and lib97.LABELS.get('NC_T'), 'lib97 without the dplay slot'
    se = uefaq.STATE_END[0] or 0
    assert se <= SAVE_AT and SAVE_AT + 256 <= careerworld.BIGC_AT, (hex(se), hex(SAVE_AT))
    force = int(os.environ.get('DPLAY_FORCE') or 0)          # (test builds: the career club's Serie B place)
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dplay.c'), [f'-DDP_FORCE={force}'])
    syms, cend, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= 0x1000, hex(bss)
    keys = ('IN_SIZE', 'OUT_SIZE', 'RSZ', 'NT', 'O_N', 'O_T', 'O_MV', 'MSZ', 'O_PO', 'O_MGR', 'SV_SIZE', 'SV_KIND',
            'SV_TEAM', 'SV_PTS', 'SV_PLACE', 'SV_RB')
    lay = dict(zip(keys, struct.unpack(f'<{len(keys)}I', p.get(1, syms['DP_LAYOUT'][1], 4 * len(keys)))))
    assert lay['RSZ'] == 12 and lay['MSZ'] == 8 and lay['SV_SIZE'] <= 64 and lay['SV_KIND'] == 4, lay
    sel = mkseason._hook_sites(p)[3]
    s = careerworld.SITES
    tmd = careerworld.LABELS['sites']['tmd']
    assert len(tables) == 1, 'dplay: one world with the Italian play-offs'
    cps = _contests(p, area, tables[0][5])
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update({'NDIV': (0, 5), 'DP_IN': syms['DP_IN'], 'DP_OUTB': syms['DP_OUT'], 'dp_season': syms['dp_season'],
                    'dp_lend_c': syms['dp_lend'], 'DP_SVP': syms['DP_SVP'], 'A0R': (2, r['A0']), 'A1R': (2, r['A0'] + 4), 'A2R': (2, r['A0'] + 8),
                    'A4R': (2, r['A0'] + 16), 'D7R': (2, r['D7']), 'D0R': (2, r['A0'] - 32), 'D1R': (2, r['A0'] - 28),
                    'D2R': (2, r['A0'] - 24), 'SLT': s['slt'], 'SLTCOPY': s['sltcopy'],
                    'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'DIY': (2, diy), 'NCW': (2, diy), 'SELTEAMS': (2, sel),
                    'CAREERTEAM': (2, ct), 'ANIM_REL': (2, rel), 'ANIM_PRO': (2, pro),
                    'C9221F': (1, c9221f), 'C9228D': (1, c9228d), 'C8ECAE': (1, ps['c8ecae']), 'C8EE5D': (1, ps['tail']),
                    'C8B2D3': (1, sacups.SITES['c8b2d3']), 'D8CAA': (2, ps['d8caa']), 'D6CDC': (2, ps['d6cdc']),
                    'CFB': (2, ps['cfb']), 'CAL': (2, ps['cal']), 'CAL_CUR': (2, ps['cal_cur']), 'SLOT4': (2, ps['slot4']), 'LIST4': (2, ps['list4']),
                    'W11F9CC': (2, ps['w11f9cc']), 'DIYCOPY': (2, diy - 0x41F), 'UQ_TIE_ROUND': (1, uefaq.LABELS['uq_tie_round']), 'COIN_DRAW': (1, coin), 'NC_T': (1, lib97.LABELS['NC_T']),
                    'DP_ST': syms['DP_ST'], 'SEASONPLAYING': (2, s['season']),
                    'DP_SAVE': (2, tmd + SAVE_AT), 'DP_LOG': (2, tmd + SAVE_AT + 64), 'DPID_PO': (0, DP_PO), 'DPID_OUT': (0, DP_OUT),
                    'TAB_BYTES': (0, 'db ' + ', '.join(str(b) for b in table_bytes(tables)))})
    glue = (cend + 15) & ~15
    # the two contests after the glue (their address known after a first assembly)
    symbols.update({'DP_C0': (1, 0), 'DP_C1': (1, 0)})
    code, _ = nasmcave.assemble(ASM, glue, symbols)
    c0 = (glue + len(code) + 15) & ~15
    c1 = (c0 + len(cps[0]) + 3) & ~3
    symbols.update({'DP_C0': (1, c0), 'DP_C1': (1, c1)})
    code, fix = nasmcave.assemble(ASM, glue, symbols)
    lab = nasmcave.labels(ASM, glue, symbols)
    assert c0 >= glue + len(code) and c1 + len(cps[1]) <= limit, hex(c1 + len(cps[1]))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    p.put(1, c0, cps[0])
    p.put(1, c1, cps[1])
    for site, target in ((cap, 'dp_cap'), (end_site, 'dp_end'), (ps['lend'][0], 'dp_lend'), (ps['lend'][1], 'dp_lend'),
                         (ps['draw'], 'dp_draw')):           # (relative calls: no fixups)
        p.put(1, site + 1, struct.pack('<i', lab[target] - (site + 5)))
    p.remove(1, ps['rec'] + 2)                               # mov ax, [dseg_11F9CC] (6 B) -> call dp_rec; nop
    p.put(1, ps['rec'], b'\xe8' + struct.pack('<i', lab['dp_rec'] - (ps['rec'] + 5)) + b'\x90')
    p.add_ptr(1, lib97.LABELS['NC_DPP'], 1, lab['dp_perm'])  # (lib97 nc_adv's slot)
    for rn in ('uq_rn1', 'uq_rn2'):                          # their `call uq_tie_round` -> dp_round
        a = uefaq.LABELS[rn]
        assert p.get(1, a, 1) == b'\xe8' and a + 5 + struct.unpack('<i', p.get(1, a + 1, 4))[0] == uefaq.LABELS['uq_tie_round']
        p.put(1, a + 1, struct.pack('<i', lab['dp_round'] - (a + 5)))
    LABELS.update(lab, DP_IN=syms['DP_IN'], DP_OUT=syms['DP_OUT'], layout=lay, contests=(c0, c1), save=tmd + SAVE_AT,
                  sites=ps)
    print(f"exe: Italian play-offs (dplay): {len(tables)} leagues, C obj1+{at:#x}..{cend:#x}, glue ..{glue + len(code):#x}, "
          f"contests obj1+{c0:#x} / +{c1:#x}, DP_IN obj2+{syms['DP_IN'][1]:#x}, state obj2+{tmd + SAVE_AT:#x}, "
          f"hooks obj1+{cap:#x} / +{end_site:#x}, league end +{ps['lend'][0]:#x} / +{ps['lend'][1]:#x}, "
          f"draw +{ps['draw']:#x}, result +{ps['rec']:#x}")
    return c1 + len(cps[1])
