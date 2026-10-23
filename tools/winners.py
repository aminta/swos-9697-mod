"""SEASON WINNERS page (4.0.1): VINCITORI / WINNERS / VAINQUEURS / SIEGER in the competition view's statistics menu
(fmtpage's 8th entry, career-world builds), the page of fmtpage (title, LINES lines, PREV / NEXT / EXIT): per title of
the viewed league its name, then its winner this season, 'IN CORSO' (started, no winner yet) or 'DA GIOCARE' (not
started).

Titles: the FMTxx[world].DAT file's WIN entries (fmtgame.win_lines: a league division with a title beyond its table;
none = the entry hidden by the menu's onInit), read when the menu opens and when the page opens (fmtpage's buffers),
a text line per title: the title, 01h, its source:
  'L' hh dd    the league's own table: its 1st once it has played hh matches (fmtgame.end_played: the season's);
  'P' k        dplay's play-off k this season (1 Serie B play-off, 2 its play-out: the relegated club, 3 Serie C
               play-off), the career club's (DP_ST, else its saved copy DP_SAVE), else no line;
  'C'          a cup-shaped contest's winner (DIY +39h, the game's: Brazil's state championship, live in slot 1);
  'S' k hh dd  the 1st of stage table k (gplay GP_SS.r[k] written this season: Argentina's annual table), once the
               league has played its hh match days (DIY +1C1h, split's day count); dd: the division (4.0.1);
  'D' s hh     a stage title decided mid-season (gplay GP_ST.dec[s] of play-off hh), else as 'K';
  'K' hh       play-off hh's last tie in gplay GP_ST.ko (the career club's play-off, played);
  'T' hh tt    tie tt's winner of play-off hh (an intermediate title: the MLS conference finals), as 'K'.
A title with nothing this season is left out (no line that would never fill: a play-off the career club is not in is
decided at the season end - 4.0.1's 'WN'); a stage title or stage table of the career's own league shows DA GIOCARE.
4.0.1: then, on a page of its own, the last season ('VINCITORI 2025-26:' and the titles of the division the career
club played in - WN_ST's 'M', the WIN text keyed 01h 'H' file division - as gplay's WN_ST holds them:
the engine block's item 'WN', written at the career country's season end by gp_season, zeroed in an older save: no
such page), the club named by the viewed contest's rows, else by its team file (DATA\\TEAM.nnn: moved since).
The winners are read from state saved with the career (the DIY, GP_ST: no new save item, no after-load call); a club
is named only when it is a row of the viewed league (DIY +6Dh rows: selTeamsPtr + [row + 2B3h], TeamFile.teamName),
so another country's career state never names a club here. Code on the extra pages (xtra / pgroups / bigtables').
"""
import struct

TEXTS = {'it': (b'VINCITORI ', b'DA GIOCARE', b'IN CORSO'), 'en': (b'WINNERS ', b'TO BE PLAYED', b'IN PROGRESS'),
         'fr': (b'VAINQUEURS ', b'A JOUER', b'EN COURS'), 'de': (b'SIEGER ', b'NOCH OFFEN', b'IM GANGE')}

ASM = r"""
wn_init:                                ; the statistics menu's onInit: fmtpage's (CLASSIFICA GENERALE), then VINCITORI
    call FP_OVINIT                      ; hidden for a competition without a WIN entry
    pushad
    call wn_load
    xor eax, eax
    cmp byte [FOUND], 0
    sete al
    mov [MENU_ + 16h + 7 * 38h + 4], ax
    popad
    ret

wn_open:                                ; VINCITORI (fire): the page
    pushad
    call wn_load
    call wn_lastdiv
    mov edi, TITLE
    mov al, [SEASONPLAYING]
    call wn_title                       ; 'VINCITORI 2026-27'
    mov byte [edi], 0
    cmp byte [FOUND], 0
    je .show
    call wn_render
.show:
    mov dword [PAGE], 0
    call FP_FILL
    popad
    mov dword [A6], FMTMENU
    jmp SHOW_MENU

wn_lastdiv:                             ; 4.0.1 (Davide): the last season's page shows the division the career club
    pushad                              ; played in - WN_ST's 'M' (team word, division) -> the WIN text whose key line
    mov byte [WN_T2], 0                 ; is 01h 'H' file division into TXT2 (WN_T2 = 1), else the viewed contest's
    mov dword [GP_WNSRC], 0100004Dh     ; ('M', the last season)
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    pushad
    call GP_WN_C
    mov [esp + 28], eax
    popad
    cmp ax, 0FFFEh
    jae .x
    mov edi, WN_KEY + 2                 ; 01h 'H' + 2 hex digits of the file (the team word's low byte) + 2 of the
    mov ebx, eax                        ; division
    call .hx
    shr eax, 16
    mov ebx, eax
    call .hx
    mov edx, FNAME
    mov eax, 3D00h
    int 21h
    jc .x
    mov ebx, eax
    mov edx, BUF
    mov ecx, 5000h                      ; (the index: below TXT2, fmtpage.build asserts it)
    mov ah, 3Fh
    int 21h
    jc .c
    cmp dword [BUF], 31544D46h
    jne .c
    movzx eax, word [BUF + 4]
    imul esi, eax, ENTRY_
    add esi, BUF + 8
    movzx ebp, word [BUF + 6]
.e: test ebp, ebp
    jz .c
    mov edx, [esi + NAME_ + 1]          ; (its text's first 6 bytes)
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    jc .c
    mov edx, WN_TMP
    mov ecx, 6
    mov ah, 3Fh
    int 21h
    jc .c
    mov eax, [WN_TMP]
    cmp eax, [WN_KEY]
    jne .nx
    mov ax, [WN_TMP + 4]
    cmp ax, [WN_KEY + 4]
    je .f
.nx:
    add esi, ENTRY_
    dec ebp
    jmp .e
.f: mov edx, [esi + NAME_ + 1]          ; (the whole text)
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    jc .c
    movzx ecx, word [esi + NAME_ + 5]
    cmp ecx, 0FFFh
    jbe .l
    mov ecx, 0FFFh
.l: mov edx, TXT2
    mov ah, 3Fh
    int 21h
    jc .c
    mov byte [TXT2 + eax], 0
    mov byte [WN_T2], 1
.c: mov ah, 3Eh
    int 21h
.x: popad
    ret
.hx:                                    ; bl -> 2 hex digits at edi (upper case), ebx >>= 8
    mov al, bl
    shr al, 4
    call .d
    mov al, bl
    and al, 0Fh
    call .d
    shr ebx, 8
    ret
.d: add al, '0'
    cmp al, '9'
    jbe .s
    add al, 7
.s: stosb
    ret

wn_title:                               ; at edi (advanced): 'VINCITORI ' + the season of al (1900 + al: 2026-27)
    push esi
    push edx
    push ecx
    movzx eax, al
    add eax, 1900
    push eax
    mov esi, WN_TITLE
.t: lodsb
    test al, al
    jz .y
    stosb
    jmp .t
.y: mov eax, [esp]
    mov ecx, 1000
    call .dig
    mov ecx, 100
    call .dig
    mov ecx, 10
    call .dig
    mov ecx, 1
    call .dig
    mov al, '-'
    stosb
    pop eax
    inc eax
    xor edx, edx
    mov ecx, 100
    div ecx
    mov eax, edx
    mov ecx, 10
    call .dig
    mov ecx, 1
    call .dig
    pop ecx
    pop edx
    pop esi
    ret
.dig:                                   ; eax: its digit of place ecx stored, eax = the rest
    xor edx, edx
    div ecx
    add al, '0'
    stosb
    mov eax, edx
    ret

wn_load:                                ; FOUND = 1 with the competition's WIN text in TXT (fmtpage's file, index
    pushad                              ; after its pages' entries: the header's second word)
    mov byte [FOUND], 0
    mov edi, FNAME + FN_BASE_           ; data/fmtxx + the career's world number + .dat
    cmp word [GAMETYPE], 4
    jne .w0
    movzx eax, byte [SLT + WORLD_BYTE_]
    test eax, eax
    jz .w0
    xor edx, edx
    mov ecx, 10
    div ecx
    test eax, eax
    jz .units
    add al, '0'
    stosb
.units:
    lea eax, [edx + '0']
    stosb
.w0:
    mov dword [edi], 7461642Eh          ; '.dat'
    mov byte [edi + 4], 0
    mov edx, FNAME
    mov eax, 3D00h
    int 21h
    jc .x
    mov ebx, eax
    mov edx, BUF
    mov ecx, IDXMAX_
    mov ah, 3Fh
    int 21h
    jc .close
    cmp dword [BUF], 31544D46h          ; 'FMT1'
    jne .close
    movzx eax, word [BUF + 4]
    imul esi, eax, ENTRY_
    add esi, BUF + 8
    movzx ecx, word [BUF + 6]
    mov edi, [DIYNAME]
    mov dl, [edi + 29h]                 ; the slot's contest id (+2Dh)
.find:
    jecxz .close
    mov al, [esi]
    cmp al, 0FFh
    je .name
    cmp al, dl
    jne .next
.name:
    push ecx
    xor ecx, ecx
.cmp:
    mov al, [esi + ecx + 1]
    test al, al
    jz .kend
    cmp al, [edi + ecx]
    jne .ne
    inc ecx
    cmp ecx, NAME_ - 1
    jb .cmp
    jmp .eq
.kend:
    cmp byte [edi + ecx], 0
    jne .ne
.eq:
    pop ecx
    jmp .found
.ne:
    pop ecx
.next:
    add esi, ENTRY_
    dec ecx
    jmp .find
.found:
    mov edx, [esi + NAME_ + 1]
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    jc .close
    movzx ecx, word [esi + NAME_ + 5]
    cmp ecx, TXTMAX_ - 1
    jbe .len
    mov ecx, TXTMAX_ - 1
.len:
    mov edx, TXT
    mov ah, 3Fh
    int 21h
    jc .close
    mov byte [TXT + eax], 0
    mov byte [FOUND], 1
.close:
    mov ah, 3Eh
    int 21h
.x: popad
    ret

wn_render:                              ; TXT's lines (title 01h source) -> per title a block: 'title:', its winner
    pushad                              ; (the page's own menu: centred, the winner yellow), a blank line between
    mov esi, TXT                        ; blocks, 5 to a page (a form feed: no block split); in BUF, then into TXT
    mov edi, BUF
    xor ebp, ebp                        ; (blocks on this page)
    mov byte [WN_MODE], 0               ; (this season; then the last season: 4.0.1's WN_ST, a page of its own)
.line:
    cmp byte [esi], 0
    je .end
    mov [WN_LS], edi                    ; (the block's start: a title with nothing to show is left out)
    mov [WN_BC], ebp
    cmp edi, BUF
    je .ti
    cmp ebp, 5
    jb .sep
    mov al, 0Ch                         ; (a new page)
    stosb
    xor ebp, ebp
    jmp .ti
.sep:
    mov ax, 0A0Ah                       ; (the winner line's end, a blank line)
    stosw
.ti:
    lodsb
    test al, al
    jz .src
    cmp al, 1
    je .src
    cmp al, 0Ah
    je .src
    stosb
    jmp .ti
.src:
    dec esi
    cmp byte [esi], 1
    jne .nos
    inc esi
.nos:
    mov ax, 0A3Ah                       ; ':' LF
    stosw
    call wn_src                         ; edx = the winner's name (or 'DA GIOCARE'), esi past the source;
    jnc .nm                             ; CF: nothing to show - no block
    mov edi, [WN_LS]
    mov ebp, [WN_BC]
    jmp .eol
.nm:
    mov al, [edx]
    test al, al
    jz .ne
    stosb
    inc edx
    jmp .nm
.ne:
    inc ebp
    inc dword [WN_CNT]
.eol:
    lodsb                               ; (the rest of the source line)
    test al, al
    jz .last
    cmp al, 0Ah
    jne .eol
    jmp .line
.last:
    dec esi
    jmp .line
.end:
    cmp byte [WN_MODE], 0
    jne .end1
    mov byte [WN_MODE], 1               ; the last season: 'VINCITORI 2025-26:' (a block), then its titles
    mov [WN_HS], edi
    mov dword [WN_CNT], 0
    cmp edi, BUF
    je .h
    mov al, 0Ch
    stosb
.h: mov al, [SEASONPLAYING]
    dec al
    call wn_title
    mov ax, 0A3Ah                       ; (':' and its empty winner line)
    stosw
    mov ebp, 1
    mov esi, TXT
    cmp byte [WN_T2], 0                 ; (4.0.1: the division the career club played in, when known)
    je .line
    mov esi, TXT2
    jmp .line
.end1:
    cmp dword [WN_CNT], 0
    jne .fin
    mov edi, [WN_HS]                    ; (no title of the last season known: no such page)
.fin:
    mov byte [edi], 0
    mov esi, BUF
    mov edi, TXT
    mov ecx, TXTMAX_ - 1
.cp:
    lodsb
    stosb
    test al, al
    loopnz .cp
    mov byte [edi], 0
    popad
    ret

wn_src:                                 ; esi -> a source: edx = the winner's name, else TBP (to be played); CF = 1:
                                        ; no line (a play-off without its contest this season; a stage title or stage
                                        ; table of another league than the career's, not decided)
    mov edx, TBP
    lodsb
    cmp al, 'H'                         ; (a WIN text's key line: no line)
    je .hk
    cmp byte [WN_MODE], 0
    jne .ls
    cmp al, 'L'
    je .lg
    cmp al, 'C'
    je .cup
    cmp al, 'P'
    je .dp
    xor ebx, ebx                        ; GP_WNSRC: type, stage << 8, play-off << 16
    mov bl, al
    cmp al, 'K'
    je .pi
    cmp al, 'T'
    je .tt
    lodsb                               ; ('D' / 'S': the stage)
    sub al, '0'
    mov bh, al
    cmp bl, 'S'
    jne .pi
    call .hex                           ; ('S': the league's match days, then decided once DIY +1C1h has them)
    shl eax, 4
    mov ecx, eax
    call .hex
    or ecx, eax
    cmp [DIY_ + 1C1h], cx
    jae .call
    cmp word [DIY_ + 1C1h], 0           ; (not over: IN CORSO once a day is played, else DA GIOCARE)
    je .s0
    mov edx, INC
.s0:
    push esi                            ; (as nothing of it this season - GP_CALL's frame)
    jmp .none
.pi:
    call .hex
    shl eax, 4
    mov ecx, eax
    call .hex
    or eax, ecx
    shl eax, 16
    or ebx, eax
    cmp bl, 'D'                         ; ('D': its stage's start, in league days)
    jne .call
    call .hex2
    mov [WN_SS], al
    jmp .call
.tt:                                    ; 'T' pi tt: tie tt of play-off pi (an intermediate title)
    call .hex2
    shl eax, 16
    mov ebx, eax
    call .hex2
    mov bh, al
    mov bl, 'T'
    cmp byte [WN_MODE], 0
    je .call
    or ebx, 1000000h
.call:
    cmp byte [ebx], 0                   ; (dummy: replaced below)
    ret
.hex:
    lodsb
    sub al, '0'
    cmp al, 9
    jbe .h
    sub al, 7
.h: movzx eax, al
    ret
.lg:                                    ; the league's table: its 1st once it has played hh matches (the season's;
                                        ; any league: its table is live)
    call .hex
    shl eax, 4
    mov ecx, eax
    call .hex
    or ecx, eax
    movzx eax, word [DIY_ + 6Dh]        ; (row 0: the leader)
    cmp [DIY_ + eax + 2B7h], cx         ; (its played)
    jae .lw
    cmp word [DIY_ + eax + 2B7h], 0     ; (started: IN CORSO)
    je .lx
    mov edx, INC
    jmp .lx
.lw:
    call wn_row
.lx:
    clc
    ret
.dp:                                    ; 'P' k: dplay's play-off k (1 Serie B play-off, 2 its play-out: the loser, 3
    lodsb                               ; Serie C play-off), the career club's (DP_ST 'DP' this season), else no line
    sub al, '0'
DP_CODE
.ls:                                    ; the last season (WN_ST): 'K' hh / 'D' s hh -> 'K' entry hh; 'L' hh dd /
    xor ebx, ebx                        ; 'S' k hh dd -> 'L' entry dd; 'C', 'P': none
    cmp al, 'K'
    je .lk
    cmp al, 'T'
    je .tt
    cmp al, 'D'
    je .ld
    cmp al, 'S'
    je .lsd
    cmp al, 'L'
    je .ll
    stc
    ret
.lsd:
    lodsb                               ; (the stage)
.ll:
    call .hex2                          ; (the matches / days)
    call .hex2
    mov bl, 'L'
    mov bh, al
    jmp .lc
.ld:
    lodsb                               ; (the stage)
.lk:
    call .hex2
    shl eax, 16
    mov ebx, eax
    mov bl, 'K'
.lc:
    or ebx, 1000000h
    jmp .call
.hex2:
    push ecx
    call .hex
    shl eax, 4
    mov ecx, eax
    call .hex
    or eax, ecx
    pop ecx
    ret
.hk:
    stc
    ret
.cup:                                   ; a cup-shaped contest (a state championship): its winner, DIY +39h (0FFFFh
    mov ax, [DIY_ + 39h]                ; until its final is played; the game's own field)
    cmp ax, 0FFFFh
    jne .cw
    movzx eax, word [DIY_ + 6Dh]        ; (a match played: IN CORSO)
    cmp word [DIY_ + eax + 2B7h], 0
    je .cx
    mov edx, INC
    jmp .cx
.cw:
    call wn_team
.cx:
    clc
    ret

wn_row:                                 ; eax = a row's offset in DIY_: edx = its club's name
    mov eax, [DIY_ + eax + 2B3h]
    add eax, [SELPTR]
    lea edx, [eax + 5]                  ; (TeamFile.teamName)
    ret

wn_team:                                ; ax = a team word: edx = its name if it is a club of the viewed contest
    pushad                              ; (DIY_ +31h clubs, +12Dh their team words, +2B3h their 18-byte entries:
    movzx ecx, word [DIY_ + 31h]        ; selTeamsPtr + [entry]), else unchanged
    cmp ecx, 64
    jbe .n
    mov ecx, 64
.n: xor esi, esi
.r: jecxz .x
    cmp [DIY_ + 12Dh + esi * 2], ax
    je .f
    inc esi
    dec ecx
    jmp .r
.f: imul esi, esi, 18
    mov ebx, [DIY_ + 2B3h + esi]
    add ebx, [SELPTR]
    lea ebx, [ebx + 5]
    mov [esp + 20], ebx                 ; (pushad's edx)
.x: popad
    ret

wn_mine:                                ; ZF = 0 if the career club is a row of the viewed league
    push edx
    push eax
    xor edx, edx
    mov ax, [CAREERTEAM]
    call wn_team
    test edx, edx
    pop eax
    pop edx
    ret

wn_disk:                                ; ax = a team word: edx = its name from DATA\\TEAM.nnn (nnn = al, its record
    pushad                              ; ah: 2 + 684 x ah, TeamFile.teamName), unchanged if not read
    mov esi, eax
    movzx eax, al
    mov edi, WN_FN + 10
    xor edx, edx
    mov ecx, 100
    div ecx
    add al, '0'
    stosb
    mov eax, edx
    xor edx, edx
    mov ecx, 10
    div ecx
    add al, '0'
    stosb
    lea eax, [edx + '0']
    stosb
    mov edx, WN_FN
    mov eax, 3D00h
    int 21h
    jc .x
    mov ebx, eax
    xor ebp, ebp
    mov eax, esi
    movzx eax, ah
    imul edx, eax, 684
    add edx, 2 + 5
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    jc .c
    mov edx, WN_NAME
    mov ecx, 17
    mov ah, 3Fh
    int 21h
    jc .c
    cmp eax, 17
    jne .c
    mov byte [WN_NAME + 17], 0
    inc ebp
.c: mov ah, 3Eh
    int 21h
    test ebp, ebp
    jz .x
    mov dword [esp + 20], WN_NAME       ; (pushad's edx)
.x: popad
    ret

WN_LS: dd 0
WN_BC: dd 0
WN_HS: dd 0
WN_CNT: dd 0
WN_MODE: db 0
WN_T2: db 0
WN_KEY: db 1, 'H', '0000'
WN_TMP: times 8 db 0
WN_SS: db 0FFh
WN_FN: db 'data/team.000', 0
WN_NAME: times 18 db 0
WN_TITLE: WN_TITLE_BYTES
TBP: TBP_BYTES
INC: INC_BYTES
"""


def sel_ptr(p):
    """selTeamsPtr: DIYLeagueTournament16BeforeDraw's row name (mov eax, [esi + 2B3h]; mov A1, eax; mov eax,
    selTeamsPtr; add A1, eax)."""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    a1 = re.escape(struct.pack('<I', sacups.regs(d1)['A0'] + 4))
    ms = {struct.unpack('<I', m.group(1))[0]
          for m in re.finditer(rb'\x8b\x86\xb3\x02\x00\x00\xa3' + a1 + rb'\xa1(.{4})\x01\x05' + a1, d1, re.S)}
    assert len(ms) == 1, ms
    return ms.pop()


def patch(p, at, lang, sites):
    """The page's code at obj1:at (gplay's pages, after longtable); fmtpage.WN's entry and onInit pointers turned to
    it. sites: careerworld.SITES. Returns the code end."""
    import fmtpage
    import gplay
    import nasmcave
    wn = fmtpage.WN
    assert wn, 'fmtpage: no VINCITORI entry (a build without career worlds)'
    sym = dict(wn['sym'], FMTMENU=(2, wn['menu']))     # (the page's own copy of fmtpage's menu)
    sym['TXT2'] = (2, wn['sym']['BUF'][1] + 0x5000)      # (4.0.1 wn_lastdiv: the last season's division's text)
    ttl, tbp, inc = TEXTS[lang]
    sym.update({'FP_OVINIT': (1, wn['ovinit']), 'FP_FILL': (1, wn['fill']),
                'SEASONPLAYING': (2, sites['season']),
                'SELPTR': (2, sel_ptr(p)),
                'GP_WN_C': (1, gplay.LABELS['gp_wn_c'][1]), 'GP_WNSRC': gplay.LABELS['GP_WNSRC'],
                'GP_SEAS': gplay.LABELS['GP_SEAS'], 'GP_MGR': gplay.LABELS['GP_MGR'],
                'SLOT3': (2, __import__('dplay')._play_sites(p, __import__('sacups').regs(p.le.obj_bytes(1)))['slot4']
                          + 0x443),                      # (slot 3's buffer follows slot 4's, 443h each)
                'CAREERTEAM': (2, __import__('dplay')._sites(p)[5]),
                'WN_TITLE_BYTES': (0, 'db ' + ', '.join(str(b) for b in ttl + b'\0')),
                'TBP_BYTES': (0, 'db ' + ', '.join(str(b) for b in tbp + b'\0')),
                'INC_BYTES': (0, 'db ' + ', '.join(str(b) for b in inc + b'\0'))})
    src = nasmcave.sub(ASM, """    cmp byte [ebx], 0                   ; (dummy: replaced below)
    ret""", GP_CALL)
    import dplay
    dpon = 'DP_ST' in dplay.LABELS
    src = nasmcave.sub(src, 'DP_CODE\n', DP_CODE if dpon else '    stc\n    ret\n')
    if dpon:
        lay = dplay.LABELS['layout']
        sym.update({'DP_ST': dplay.LABELS['DP_ST'], 'DP_SAVE': (2, dplay.LABELS['save']), 'SV_KIND': (0, lay['SV_KIND']),
                    'SV_TEAM': (0, lay['SV_TEAM'])})
    at = (at + 15) & ~15
    code, cfix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in cfix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for off, name in ((wn['sel'], 'wn_open'), (wn['init'], 'wn_init')):
        p.retarget(2, off, 1, lab[name])
        p.put(2, off, struct.pack('<I', lab[name]))
    print(f'exe: SEASON WINNERS page: entry obj2+{wn["sel"]:#x}, code obj1+{at:#x} ({len(code)} B)')
    return at + len(code)


GP_CALL = """    mov [GP_WNSRC], ebx                 ; gplay.c gp_wn_c: the winner's team word, 0FFFFh being played, 0FFFEh
    mov ax, [CAREERTEAM]                ; nothing
    mov [GP_MGR], ax
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    push esi
    pushad
    call GP_WN_C
    mov [esp + 28], eax                 ; (pushad's eax)
    popad
    cmp byte [WN_MODE], 0
    jne .lst
    cmp ax, 0FFFCh
    je .t2
    cmp ax, 0FFFFh                      ; (its contest running: IN CORSO)
    je .inc
    cmp ax, 0FFFEh
    je .none
    push edx
    xor edx, edx
    call wn_team                        ; (a club of another league: another country's state)
    test edx, edx
    jz .nf
    add esp, 4
    jmp .tbp
.nf:
    pop edx
.none:
    cmp bl, 'K'                         ; (a play-off without its contest: decided at the season end)
    je .skip
    cmp bl, 'T'
    je .skip
    cmp bl, 'D'                         ; (a stage title: IN CORSO once its stage has a day played)
    jne .nm2
    movzx ecx, byte [WN_SS]
    cmp ecx, 0FFh
    je .nm2
    cmp [DIY_ + 1C1h], cx
    jbe .nm2
    mov edx, INC
.nm2:
    call wn_mine                        ; (a stage title / table of the career's league: to be played)
    jz .skip
    jmp .tbp
.inc:
    mov edx, INC
.tbp:
    pop esi
    clc
    ret
.lst:                                   ; the last season: its club by the viewed contest's rows, else its team file
    cmp ax, 0FFFEh
    jae .skip
    push edx
    xor edx, edx
    call wn_team
    test edx, edx
    jnz .lf
    call wn_disk
    test edx, edx
    jnz .lf
    pop edx
    jmp .skip
.lf:
    add esp, 4
    jmp .tbp
.t2:                                    ; a group contest of ours (the Poule Scudetto, slot 3, id FEh): its winner
    cmp byte [SLOT3 + 2Dh], 0FEh        ; the game's (DIY +39h, 0FFFFh until its final); a club of another group:
    jne .skip                           ; its team file's name
    mov ax, [SLOT3 + 39h]
    cmp ax, 0FFFFh
    je .inc
    push edx
    xor edx, edx
    call wn_team
    test edx, edx
    jnz .lf
    call wn_disk
    test edx, edx
    jnz .lf
    pop edx
    jmp .skip
.skip:
    pop esi
    stc
    ret"""


DP_CODE = """    push esi                            ; (the live state DP_ST, else its saved copy DP_SAVE: after a load
    mov esi, DP_ST                      ; dp_sync restores DP_ST only when dplay runs)
    mov ah, [SEASONPLAYING]
    cmp word [esi], 5044h
    jne .dp2
    cmp [esi + SV_KIND + 2], ah
    je .dp3
.dp2:
    mov esi, DP_SAVE
    cmp word [esi], 5044h
    jne .dps
    cmp [esi + SV_KIND + 2], ah
    jne .dps
.dp3:
    cmp [esi + SV_KIND], al
    jne .dps
    mov cx, [esi + 2]                   ; (res: the last round's winner, 0 until then: IN CORSO)
    test cx, cx
    jnz .dpg
    mov edx, INC
    jmp .dpt
.dpg:
    cmp al, 2
    jne .dpw
    mov dx, [esi + SV_TEAM]             ; (the play-out: the other of its two clubs, relegated)
    cmp dx, cx
    jne .dpl
    mov dx, [esi + SV_TEAM + 2]
.dpl:
    mov cx, dx
.dpw:
    mov ax, cx
    mov edx, TBP
    call wn_team
.dpt:
    pop esi
    clc
    ret
.dps:
    pop esi
    stc
    ret
"""
