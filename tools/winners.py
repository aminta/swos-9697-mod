"""SEASON WINNERS page (4.0.1): VINCITORI / WINNERS / VAINQUEURS / SIEGER in the competition view's statistics menu
(fmtpage's 8th entry, career-world builds), the page of fmtpage (title, LINES lines, PREV / NEXT / EXIT): per title of
the viewed league its name, then its winner this season or 'DA GIOCARE' (to be played).

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
  'K' hh       play-off hh's last tie in gplay GP_ST.ko (the career club's play-off, played).
A title with nothing this season is left out (no line that would never fill: a play-off the career club is not in is
decided at the season end - 4.0.1's 'WN'); a stage title or stage table of the career's own league shows DA GIOCARE.
The winners are read from state saved with the career (the DIY, GP_ST: no new save item, no after-load call); a club
is named only when it is a row of the viewed league (DIY +6Dh rows: selTeamsPtr + [row + 2B3h], TeamFile.teamName),
so another country's career state never names a club here. Code in gplay's pages (the cosmetics page is full).
"""
import struct

TEXTS = {'it': (b'VINCITORI ', b'DA GIOCARE'), 'en': (b'WINNERS ', b'TO BE PLAYED'),
         'fr': (b'VAINQUEURS ', b'A JOUER'), 'de': (b'SIEGER ', b'NOCH OFFEN')}

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
    mov esi, WN_TITLE                   ; 'VINCITORI ' + the season, e.g. 2026-27 (1900 + seasonPlaying)
    mov edi, TITLE
.t: lodsb
    test al, al
    jz .y
    stosb
    jmp .t
.y: movzx eax, byte [SEASONPLAYING]
    add eax, 1900
    push eax
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
    push esi                            ; (not over: as nothing of it this season - GP_CALL's frame)
    jmp .none
.pi:
    call .hex
    shl eax, 4
    mov ecx, eax
    call .hex
    or eax, ecx
    shl eax, 16
    or ebx, eax
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
    jb .lx
    call wn_row
.lx:
    clc
    ret
.dp:                                    ; 'P' k: dplay's play-off k (1 Serie B play-off, 2 its play-out: the loser, 3
    lodsb                               ; Serie C play-off), the career club's (DP_ST 'DP' this season), else no line
    sub al, '0'
DP_CODE
.cup:                                   ; a cup-shaped contest (a state championship): its winner, DIY +39h (0FFFFh
    mov ax, [DIY_ + 39h]                ; until its final is played; the game's own field)
    cmp ax, 0FFFFh
    je .cx
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

WN_LS: dd 0
WN_BC: dd 0
WN_TITLE: WN_TITLE_BYTES
TBP: TBP_BYTES
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
    ttl, tbp = TEXTS[lang]
    sym.update({'FP_OVINIT': (1, wn['ovinit']), 'FP_FILL': (1, wn['fill']),
                'SEASONPLAYING': (2, sites['season']),
                'SELPTR': (2, sel_ptr(p)),
                'GP_WN_C': (1, gplay.LABELS['gp_wn_c'][1]), 'GP_WNSRC': gplay.LABELS['GP_WNSRC'],
                'GP_SEAS': gplay.LABELS['GP_SEAS'], 'CAREERTEAM': (2, __import__('dplay')._sites(p)[5]),
                'WN_TITLE_BYTES': (0, 'db ' + ', '.join(str(b) for b in ttl + b'\0')),
                'TBP_BYTES': (0, 'db ' + ', '.join(str(b) for b in tbp + b'\0'))})
    src = ASM.replace("""    cmp byte [ebx], 0                   ; (dummy: replaced below)
    ret""", GP_CALL)
    import dplay
    dpon = 'DP_ST' in dplay.LABELS
    src = src.replace('DP_CODE\n', DP_CODE if dpon else '    stc\n    ret\n')
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
    mov al, [SEASONPLAYING]             ; nothing this season
    mov [GP_SEAS], al
    push esi
    pushad
    call GP_WN_C
    mov [esp + 28], eax                 ; (pushad's eax)
    popad
    cmp ax, 0FFFFh
    je .tbp
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
    call wn_mine                        ; (a stage title / table of the career's league: to be played)
    jz .skip
.tbp:
    pop esi
    clc
    ret
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
    mov cx, [esi + 2]                   ; (res: the last round's winner, 0 until then)
    test cx, cx
    jz .dpt
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
