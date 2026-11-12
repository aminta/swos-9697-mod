"""4.2.x (Francesco P. via Davide 12/11): trial players - the role chosen by the manager (T1) and a quality tied to the
career club's level (T2).

What the game does (ref/swos.asm):
  CheckPlayersLeavingComing (weekly): while careerNumPlayers < 30 and Rand < 25 (of 256) -> AddTrialPlayer ->
  PlayerJoinedClubOnTrial. AddTrialPlayer: Rand x 11 >> 8 indexes dseg_17D0D4 (3 3 6 6 7 7 0 1 2 4 5: D D M M A A G RB
  LB RW LW) = the position, then falls into cseg_64B80 (the new slot, the name: cseg_56615 -> cseg_567B5 the skills).
  cseg_567B5's managed-club branch: a random loaded team of the career club's team file (any division), a random one
  of its 16, his price x a bell-shaped percentage (dseg_17A170) x the career club's average price, / 3 = a level
  0..15 -> one of 16 fixed skill templates for that position (dseg_17A1A4 / dseg_17A184).
  cseg_567B5 also builds cpurefill's CPU replacements and the game's invented reserves: only the trial call is flagged.

Here:
  T1  the button 'PROVA: QUALSIASI / P / TD / TS / D / MD / MS / M / A' (each exe's own position abbreviations, POS; 4
      languages) in ACQUISTA GIOCATORE, bottom row left of ESCI (cpurefill's obj3 copy of buyPlayerMenu gets the entries:
      cpurefill.EXTRA; the code: obj4 swreg.TRIAL_AT 0xC800..0xCF00, 4.2 MC 12/11, was obj3). tr_add replaces
      AddTrialPlayer's `mov [A0], offset dseg_17D0D4`: QUALSIASI keeps the game's table (and its one Rand), a position
      points [A0] at an 11-entry table of that position only.
  T2  the button "QUALITA'+: SI / NO" (default SI, all worlds; Davide 12/11), above the trial one. While the trial flag is
      set: tr_same makes the source-team loop of cseg_567B5 accept only a team of the career club's division (team record
      +25; after TRIES draws any team of the file, as the game); tr_floor raises the final level (cseg_56B30, before the
      0..15 clamp) to at least the career club's squad median price / 3 - FLOOR_BELOW. The flag is cleared there.
  The values: engine item 'TR' (1 B: bits 0-3 = 0 QUALSIASI / 1..8 = position 0..7, bit 4 = QUALITA'+ off). An older save
  or a new career = 0 = QUALSIASI with QUALITA'+ on (release notes: old saves start with it on).
  TRIAL_FORCE=1 (test builds only, buildrel clears *_FORCE): a trial player every week (`cmp word [D0], 25` -> 0FFh).
"""
import os
import re
import struct

import nasmcave
import sacups

PREFIX = {'it': 'PROVA: ', 'en': 'TRIAL: ', 'fr': 'ESSAI: ', 'de': 'PROBE: '}
ANY = {'it': 'QUALSIASI', 'en': 'ANY', 'fr': 'TOUS', 'de': 'ALLE'}
# the positions 0..7 (G RB LB D RW LW M A) as each exe writes them in the squad screens: obj2 playerPositionsStringTable
# (IT obj2+0x53b5c, EN +0x53a12, FR +0x536ec, DE +0x5350c; the one-letter ones end in a '*' pad there, not drawn here)
POS = {'it': ('P', 'TD', 'TS', 'D', 'MD', 'MS', 'M', 'A'),
       'en': ('G', 'RB', 'LB', 'D', 'RW', 'LW', 'M', 'A'),
       'fr': ('G', 'DD', 'DG', 'D', 'MD', 'MG', 'M', 'A'),
       'de': ('T', 'RV', 'LV', 'A', 'RA', 'LA', 'M', 'S')}
# T2 on / off (the font has no accented letters: QUALITA', not the accented A)
QPREFIX = {'it': "QUALITA'+: ", 'en': 'QUALITY+: ', 'fr': 'QUALITE+: ', 'de': 'QUALITAT+: '}
QYESNO = {'it': ('SI', 'NO'), 'en': ('ON', 'OFF'), 'fr': ('OUI', 'NON'), 'de': ('AN', 'AUS')}
GAME_TABLE = bytes((3, 3, 6, 6, 7, 7, 0, 1, 2, 4, 5))
BUTTON = (0, 185, 121, 15)             # x, y, w, h: left of ESCI (x 122, w 60), as GIVE FREE TRANSFER in TRANSFERS
QBUTTON = (0, 155, 101, 15)            # QUALITA'+: left of entry 6 (x 102, y 155), above the trial button
COLOR = 0x0E
FLOOR_BELOW = 3                        # T2: the floor = the squad median's level - this (Davide picks)
TRIES = 64                             # T2: source-team draws looking for the career club's division
LABELS = {}


def texts(lang):
    """(the trial button's 9 labels, the QUALITA'+ button's 2)."""
    return ([PREFIX[lang] + x for x in (ANY[lang],) + POS[lang]],
            [QPREFIX[lang] + x for x in QYESNO[lang]])


ASM = r"""
tr_add:                                 ; replaces AddTrialPlayer's mov [A0], offset dseg_17D0D4
    push eax
    movzx eax, byte [tr_mode]
    and eax, 15
    jz .any
    cmp eax, 8
    ja .any
    push edi                            ; a position: an 11-entry table of it
    push ecx
    dec eax
    mov edi, tr_one
    mov ecx, 11
    rep stosb
    pop ecx
    pop edi
    mov dword [A0], tr_one
    jmp .f
.any:
    mov dword [A0], ORIGTAB             ; QUALSIASI: the game's table (and its one Rand)
.f: mov byte [tr_flag], 1
    mov dword [tr_tries], 0
    pop eax
    ret

tr_t2:                                  ; ZF = 1: T2 applies now (the trial flag, QUALITA'+ on = bit 4 clear)
    cmp byte [tr_flag], 1
    jne .r
    test byte [tr_mode], 16
.r: ret

tr_same:                                ; replaces cseg_567B5's mov al, byte [selTeamNumber]; mov byte [D0], al
    mov al, [SELT]                      ; (the loop then: cmp byte [D0], [team]; jnz another draw)
    call tr_t2
    jne .w
    cmp dword [tr_tries], TRIES_
    jae .w
    inc dword [tr_tries]
    push esi
    push ebx
    mov esi, [A0]                       ; the drawn team's record
    mov bl, [esi + 25]
    cmp bl, [CAREER + 25]               ; another division: make the file test fail (one more draw)
    je .k
    mov al, [esi]
    xor al, 1
.k: pop ebx
    pop esi
.w: mov [D0], al
    ret

tr_floor:                               ; replaces cseg_56B30's mov ax, [D2] (the level before the 0..15 clamp)
    call tr_t2
    jne .w
    pushad
    mov edx, 49                         ; the squad median: the largest v with 8 of the 16 priced >= v
.v: xor ecx, ecx
    xor ebx, ebx
.c: imul esi, ebx, 38
    movzx eax, byte [CAREER + 76 + 32 + esi]
    cmp eax, edx
    jb .n
    inc ecx
.n: inc ebx
    cmp ebx, 16
    jb .c
    cmp ecx, 8
    jae .m
    dec edx
    jns .v
    xor edx, edx
.m: mov eax, edx
    xor edx, edx
    mov ecx, 3
    div ecx
    sub eax, FLOOR_
    movsx ecx, word [D2]
    cmp ecx, eax
    jge .k
    mov [D2], ax
.k: mov [tr_last], ax
    popad
.w: mov byte [tr_flag], 0
    mov ax, [D2]
    ret

tr_label:                               ; both buttons' labels for tr_mode -> tr_buf, tr_qbuf
    pushad
    mov edi, tr_buf
    mov esi, tr_pre
    call .cp
    dec edi
    movzx ecx, byte [tr_mode]
    and ecx, 15
    cmp ecx, 8
    jbe .s
    xor ecx, ecx
.s: mov esi, tr_sfx                     ; the ecx-th of the 9 NUL-ended names (ecx: lodsb writes al)
.z: test ecx, ecx
    jz .t
.y: lodsb
    test al, al
    jnz .y
    dec ecx
    jmp .z
.t: call .cp
    mov edi, tr_qbuf
    mov esi, tr_qpre
    call .cp
    dec edi
    mov esi, tr_qyes
    test byte [tr_mode], 16
    jz .q
    mov esi, tr_qno
.q: call .cp
    popad
    ret
.cp:
    lodsb
    stosb
    test al, al
    jnz .cp
    ret

tr_toggle:                              ; fire on the trial button: the next role, redrawn, the cursor stays on it
    push eax                            ; (eax kept: the menu code's caller expects it, as cpurefill's cr_toggle)
    mov al, [tr_mode]
    mov ah, al
    and al, 15
    inc al
    cmp al, 8
    jbe .s
    xor al, al
.s: and ah, 16
    or al, ah
    mov [tr_mode], al
    pop eax
    call tr_label
    mov dword [D0], ENT_
    call SETCUR
    jmp DRAWMENU

tr_qtoggle:                             ; fire on QUALITA'+: on <-> off
    xor byte [tr_mode], 16
    call tr_label
    mov dword [D0], QENT_
    call SETCUR
    jmp DRAWMENU

tr_load:                                ; engine: after a career load (an older save: 0 = QUALSIASI, QUALITA'+ on)
    mov al, [tr_mode]
    and al, 31
    mov ah, al
    and ah, 15
    cmp ah, 8
    jbe .k
    and al, 16
.k: mov [tr_mode], al
    jmp tr_label

tr_new:                                 ; engine: a new career = QUALSIASI, QUALITA'+ on
    mov byte [tr_mode], 0
    jmp tr_label

align 4
tr_tries: dd 0
tr_last: dw 0                           ; (the last floored level: the harness reads it)
tr_mark: db 'TRFL'                      ; (the harness finds tr_mode by this)
tr_mode: db 0                           ; engine item 'TR': bits 0-3 = 0 QUALSIASI / 1..8 = position 0..7, bit 4 = T2 off
tr_flag: db 0
tr_one: times 11 db 0
"""


def sites(p):
    """AddTrialPlayer's table load, CheckPlayersLeavingComing's trial roll, cseg_567B5's source-team test and its
    level clamp (cseg_56B30), careerTeam."""
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    D0, D2, A0 = r['D7'] - 28, r['D7'] - 20, r['A0']
    pk = lambda a: re.escape(struct.pack('<I', a))
    m = [x for x in re.finditer(rb'\x66\xbb\x0b\x00\x66\xf7\xe3\x66\xa3' + pk(D0) + rb'\x66\x89\x15.{4}\x66\xc1\x2d'
                                + pk(D0) + rb'\x08\xc7\x05' + pk(A0) + rb'(.{4})', d, re.S)]
    assert len(m) == 1, ('AddTrialPlayer', len(m))
    tab_site = m[0].start(1) - 6
    tab = p.target(1, tab_site + 6)
    assert tab[0] == 2 and bytes(p.le.obj_bytes(2)[tab[1]:tab[1] + 11]) == GAME_TABLE, tab
    roll = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + pk(D0) + rb'\x19\x73.\xe8', d, re.S)]
    assert len(roll) == 1, ('trial roll', roll)
    m = [x for x in re.finditer(rb'\xa0(.{4})\xa2' + pk(D0) + rb'\x8b\x35' + pk(A0) + rb'\x8a\x06\x38\x05' + pk(D0)
                                + rb'\x75', d, re.S)]
    assert len(m) == 1, ('cseg_567B5 team test', len(m))
    same = m[0].start()
    clamp = [x.start() for x in re.finditer(rb'\x66\xa1' + pk(D2) + rb'\x66\x0b\xc0\x79.\x66\xc7\x05' + pk(D2)
                                            + rb'\x00\x00\xeb', d[same:same + 0x300], re.S)]
    assert len(clamp) == 1, ('cseg_56B30', clamp)
    return {'tab_site': tab_site, 'tab': tab, 'roll': roll[0], 'same': same, 'sel': p.target(1, same + 1),
            'clamp': same + clamp[0], 'D0': D0, 'D2': D2, 'A0': A0}


def patch(p, at, lang, cr):
    """Code at obj4 swreg.TRIAL_AT..TRIAL_END (4.2, MC 12/11: out of obj3, whose room the 4.2 line ran out of; obj1's
    three call sites = type-8 fixups into obj4); cr = the cpurefill module, its obj3 menu copy gets the buttons through
    cpurefill.EXTRA (their text / function pointers into obj4). at = the obj3 chain's end, returned unchanged."""
    import engine
    import swreg
    import gkinj
    import xbrowse
    import lepatch
    from complist import px, font_odd
    s = sites(p)
    labs, qlabs = texts(lang)
    assert all(px(t) <= 113 for t in labs) and all(px(t) <= QBUTTON[2] - 8 for t in qlabs), \
        [(t, px(t)) for t in labs + qlabs]
    assert all(not font_odd(t) for t in labs + qlabs), [(t, font_odd(t)) for t in labs + qlabs]
    xb = xbrowse.find(lepatch.LEPatch(bytes(p.le.data)))
    career = gkinj.find(p)['CAREER']
    ent, qent = cr.NEWENT + 1, cr.NEWENT + 2
    src = f'%define TRIES_ {TRIES}\n%define FLOOR_ {FLOOR_BELOW}\n%define ENT_ {ent}\n%define QENT_ {qent}\n' + ASM
    q = lambda t: "'" + t + "'" if "'" not in t else '"' + t + '"'
    src += f"tr_pre: db {q(PREFIX[lang])}, 0\ntr_sfx:\n" + ''.join(f"    db {q(x)}, 0\n" for x in (ANY[lang],) + POS[lang])
    src += f"tr_qpre: db {q(QPREFIX[lang])}, 0\ntr_qyes: db {q(QYESNO[lang][0])}, 0\ntr_qno: db {q(QYESNO[lang][1])}, 0\n"
    src += f"tr_buf: db {q(labs[0])}, 0\n    times {24 - len(labs[0]) - 1} db 0\n"
    src += f"tr_qbuf: db {q(qlabs[0])}, 0\n    times {20 - len(qlabs[0]) - 1} db 0\n"
    sym = {'A0': (2, s['A0']), 'D0': (2, s['D0']), 'D2': (2, s['D2']), 'SELT': s['sel'], 'CAREER': career,
           'ORIGTAB': s['tab'], 'SETCUR': (1, xb['setcur']),
           'DRAWMENU': (1, xb['drawmenu'])}
    at3, at = at, swreg.TRIAL_AT
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert p.le.obj(4).npages * 0x1000 >= swreg.TRIAL_END, 'trial: obj4 pages (patch.py)'
    assert at + len(code) <= swreg.TRIAL_END, ('trial: past its obj4 room', hex(at + len(code)), hex(swreg.TRIAL_END))
    assert not any(p.get(4, at, swreg.TRIAL_END - at)), 'trial: obj4 room not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    # AddTrialPlayer: mov [A0], offset dseg_17D0D4 (10 B) -> call tr_add; 5 x nop
    t = s['tab_site']
    p.remove(1, t + 2)
    p.remove(1, t + 6)
    p.put(1, t, b'\xe8' + struct.pack('<i', 0) + b'\x90' * 5)
    p.branch(1, t, 0xE8, 4, lab['tr_add'])
    # cseg_567B5: mov al, byte [selTeamNumber]; mov byte [D0], al (10 B) -> call tr_same; 5 x nop
    q = s['same']
    p.remove(1, q + 1)
    p.remove(1, q + 6)
    p.put(1, q, b'\xe8' + struct.pack('<i', 0) + b'\x90' * 5)
    p.branch(1, q, 0xE8, 4, lab['tr_same'])
    # cseg_56B30: mov ax, [D2] (6 B) -> call tr_floor; nop
    c = s['clamp']
    p.remove(1, c + 2)
    p.put(1, c, b'\xe8' + struct.pack('<i', 0) + b'\x90')
    p.branch(1, c, 0xE8, 4, lab['tr_floor'])
    if os.environ.get('TRIAL_FORCE'):                # test builds only: a trial player every week (< 30 players)
        p.put(1, s['roll'] + 7, b'\xff')
    # the buttons: entries appended to cpurefill's buyPlayerMenu copy (cr.EXTRA): the trial button left of ESCI
    # (ESCI's left -> it), QUALITA'+ above it, left of entry 6 (entry 6's left -> it)
    def entry(box, links, buf, fn):
        x, y, w, h = box
        e = struct.pack('<hhh', -998, 0, 0) + struct.pack('<hhhhH', x, y, w, h, 2) + bytes(links)
        e += struct.pack('<HHHH', 4, COLOR, 8, 0)
        b_at = len(e)
        e += struct.pack('<IH', 0, 13)
        f_at = len(e)
        e += struct.pack('<IH', 0, 0)
        return {'bytes': e, 'ptrs': [(b_at, 4, lab[buf]), (f_at, 4, lab[fn])]}
    cr.EXTRA.append(dict(entry(BUTTON, (0xFF, cr.NEWENT - 1, qent, 0xFF), 'tr_buf', 'tr_toggle'), esci_left=ent))
    cr.EXTRA.append(dict(entry(QBUTTON, (0xFF, cr.NEWENT - 2, cr.NEWENT - 3, ent), 'tr_qbuf', 'tr_qtoggle'),
                         links={cr.NEWENT - 2: (0, qent)}))
    engine.ITEM_AT['TR'] = (4, lab['tr_mode'])
    engine.CALL_AT['tr_load'] = (4, lab['tr_load'])
    engine.CALL_AT['tr_new'] = (4, lab['tr_new'])
    LABELS.update(lab)
    print(f'exe: trial players (T1 role button entry {ent}, QUALITA+ entry {qent}, T2 all worlds'
          f', floor median/3 - {FLOOR_BELOW}{", TRIAL_FORCE" if os.environ.get("TRIAL_FORCE") else ""}): code obj4+{at:#x} '
          f'({len(code)} B), AddTrialPlayer obj1+{t:#x}, source test obj1+{q:#x}, clamp obj1+{c:#x}')
    return at3
