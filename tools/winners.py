"""SEASON WINNERS page (4.0.1): VINCITORI / WINNERS / VAINQUEURS / SIEGER in the competition view's statistics menu
(fmtpage's 8th entry, career-world builds), the page of fmtpage (title, LINES lines, PREV / NEXT / EXIT): per title of
the viewed league its name, then its winner this season or 'DA GIOCARE' (to be played).

Titles: the FMTxx[world].DAT file's WIN entries (fmtgame.win_lines: a league division with a title beyond its table;
none = the entry hidden by the menu's onInit), read when the menu opens and when the page opens (fmtpage's buffers),
a text line per title: the title, 01h, its source:
  'L' hh       the league's own table: its 1st once it has played hh matches (fmtgame.end_played: the season's);
  'S' k        the 1st of stage table k (gplay GP_SS.r[k] written this season: Argentina's annual table);
  'D' s hh     a stage title decided mid-season (gplay GP_ST.dec[s] of play-off hh), else as 'K';
  'K' hh       play-off hh's last tie in gplay GP_ST.ko (the career club's play-off, played).
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

wn_render:                              ; TXT's lines (title 01h source) -> per title two lines, 'title:' and its
    pushad                              ; winner indented, LINES_ to a page (form feeds); built in BUF, then into TXT
    mov esi, TXT
    mov edi, BUF
    xor ebp, ebp                        ; (lines on this page)
.line:
    cmp byte [esi], 0
    je .end
    cmp ebp, LINES_
    jb .ti
    mov byte [edi - 1], 0Ch             ; (the page's last line feed: a form feed)
    xor ebp, ebp
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
    mov eax, '    '
    stosd
    call wn_src                         ; edx = the winner's name (or 'DA GIOCARE'), esi past the source
.nm:
    mov al, [edx]
    test al, al
    jz .ne
    stosb
    inc edx
    jmp .nm
.ne:
    mov al, 0Ah
    stosb
    add ebp, 2
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
    cmp edi, BUF
    je .z
    dec edi                             ; (no trailing line feed)
.z: mov byte [edi], 0
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

wn_src:                                 ; esi -> a source: edx = the winner's name, else TBP (to be played)
    mov edx, TBP
    lodsb
    cmp al, 'L'
    je .lg
    xor ebx, ebx                        ; GP_WNSRC: type, stage << 8, play-off << 16
    mov bl, al
    cmp al, 'K'
    je .pi
    lodsb                               ; ('D' / 'S': the stage)
    sub al, '0'
    mov bh, al
    cmp bl, 'S'
    je .call
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
.lg:                                    ; the league's table: its 1st once it has played hh matches (the season's)
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
    ret

wn_row:                                 ; eax = a row's offset in DIY_: edx = its club's name
    mov eax, [DIY_ + eax + 2B3h]
    add eax, [SELPTR]
    lea edx, [eax + 5]                  ; (TeamFile.teamName)
    ret

wn_team:                                ; ax = a team word: edx = its name if it is a row of the viewed league
    pushad                              ; (DIY_ +6Dh: groups x clubs rows), else unchanged
    movzx ecx, word [DIY_ + 4Fh]
    movzx ebx, word [DIY_ + 51h]
    imul ecx, ebx
    cmp ecx, 64
    jbe .n
    mov ecx, 64
.n: xor esi, esi
.r: jecxz .x
    movzx ebx, word [DIY_ + 6Dh + esi * 2]
    mov ebx, [DIY_ + ebx + 2B3h]
    add ebx, [SELPTR]
    cmp [ebx], ax
    je .f
    inc esi
    dec ecx
    jmp .r
.f: lea ebx, [ebx + 5]
    mov [esp + 20], ebx                 ; (pushad's edx)
.x: popad
    ret

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
    sym = dict(wn['sym'])
    ttl, tbp = TEXTS[lang]
    sym.update({'FP_OVINIT': (1, wn['ovinit']), 'FP_FILL': (1, wn['fill']),
                'SEASONPLAYING': (2, sites['season']),
                'SELPTR': (2, sel_ptr(p)),
                'GP_WN_C': (1, gplay.LABELS['gp_wn_c'][1]), 'GP_WNSRC': gplay.LABELS['GP_WNSRC'],
                'GP_SEAS': gplay.LABELS['GP_SEAS'],
                'WN_TITLE_BYTES': (0, 'db ' + ', '.join(str(b) for b in ttl + b'\0')),
                'TBP_BYTES': (0, 'db ' + ', '.join(str(b) for b in tbp + b'\0'))})
    src = ASM.replace("""    cmp byte [ebx], 0                   ; (dummy: replaced below)
    ret""", GP_CALL)
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


GP_CALL = """    mov [GP_WNSRC], ebx                 ; gplay.c gp_wn_c: the winner's team word, 0FFFFh to be played
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    push esi
    push edx
    pushad
    call GP_WN_C
    mov [esp + 28], eax                 ; (pushad's eax)
    popad
    pop edx
    cmp ax, 0FFFFh
    je .k
    call wn_team
.k: pop esi
    ret"""
