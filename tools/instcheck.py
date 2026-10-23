"""4.0.1 (Gianmarco's case): a world whose data files are missing (an old or interrupted patcher run) no longer exits to
DOS at the team pick (LoadFile prints the name and quits). When SelectTeamsFinalMenu is about to list a world of CLASSIC
CAREERS (its list id WMENU + n, the CAREER 2026-27 button's way in too), every file of that world is opened (DOS 3Dh)
first; one missing -> the game's error box (ShowErrorMenu's continueMenu, its text in the small font: the message is
wider than the big font's 300 px) with "INCOMPLETE INSTALL: RUN THE PATCHER AGAIN" in the exe's language, then the
team choice ends as when CUSTOMS.EDT is missing (SelectTeamsFinalMenu's err_out: chooseTeamsResult = 0)."""
import re
import struct

MSG = {'it': 'INSTALLAZIONE INCOMPLETA: RILANCIA IL PATCHER', 'en': 'INCOMPLETE INSTALL: RUN THE PATCHER AGAIN',
       'fr': 'INSTALLATION INCOMPLETE: RELANCEZ LE PATCHER', 'de': 'INSTALLATION UNVOLLST\x8eNDIG: PATCHER NEU STARTEN'}   # (\x8e: the German exe's A umlaut,
                                                                        # as in its own menus' AUSL\x8eNDISCH)
FONT_FLAG = 0x1E                        # continueMenu: entry 0's flags word (10h = big font) after the 16-byte header

ASM = '''
inst_chk:                               ; called first in cont_check (D7 = the list about to be shown)
    pushad
    mov esi, INST_TAB
.w:
    cmp word [esi], 0FFFFh
    je .ok
    mov ax, [esi]
    cmp ax, [D7REG]
    je .chk
    add esi, 6
    jmp .w
.chk:
    mov esi, [esi + 2]                  ; the world's groups: prefix, 0, count, count numbers (a name prefix.nnn
.g:                                     ; each; count 0: the prefix is the name); an empty prefix ends them
    cmp byte [esi], 0
    je .ok
    mov edi, inst_name
.cp:
    lodsb
    stosb
    test al, al
    jnz .cp
    dec edi                             ; (the NUL: the number goes there)
    lodsb
    movzx ecx, al
    jecxz .one
.num:
    lodsb
    movzx eax, al
    xor edx, edx
    mov ebx, 100
    div ebx
    add al, '0'
    mov [edi], al
    mov eax, edx
    mov bl, 10
    div bl
    add ax, 3030h
    mov [edi + 1], ax
    mov byte [edi + 3], 0
    call .open
    jc .bad
    loop .num
    jmp .g
.one:
    call .open
    jc .bad
    jmp .g
.open:
    mov edx, inst_name
    mov eax, 3D00h                      ; open, read only (CF: missing)
    int 21h
    jc .r
    mov ebx, eax
    mov eax, 3E00h                      ; close
    int 21h
    clc
.r:
    ret
.ok:
    popad
    ret
.bad:
    popad
    add esp, 4                          ; (cont_check's frame: SelectTeamsFinalMenu's own)
    mov dword [ERRTEXT], INST_MSG
    mov dword [A6R], CONTMENU
    and word [CONTMENU + FONT_FLAG_], 0FFEFh
    call SHOWMENU
    or word [CONTMENU + FONT_FLAG_], 10h
    jmp ERR_OUT
inst_name: times 24 db 0
'''


def sites(p):
    """{'ERRTEXT', 'CONTMENU', 'SHOWMENU', 'A6R', 'ERR_OUT'}: ShowErrorMenu's parts (`mov eax, [A0]; mov [errorText], eax;
    mov [A6], offset continueMenu; call ShowMenu; ret`, two identical copies) and SelectTeamsFinalMenu's err_out
    (`mov word [chooseTeamsResult], 0; ret`, the target of the jnz after LoadTeamFile(100) at its start)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0, a6, d0 = (struct.pack('<I', x) for x in (r['A0'], r['A0'] + 24, r['D7'] - 28))
    fx = {s: (t, o) for so, s, _, t, o, *_ in p.le.fixups() if so == 1}
    ms = list(re.finditer(rb'\xa1' + re.escape(a0) + rb'\xa3(.{4})\xc7\x05' + re.escape(a6) + rb'(.{4})\xe8(.{4})\xc3',
                          d1, re.S))
    assert ms and len({(fx[m.start(1)], fx[m.start(2)]) for m in ms}) == 1, len(ms)
    m = ms[0]
    menu = fx[m.start(2)]
    assert menu[0] == 1 and d1[menu[1] + FONT_FLAG:menu[1] + FONT_FLAG + 2] == b'\x10\x00', 'continueMenu flags'
    show = m.end(3) + struct.unpack('<i', m.group(3))[0]
    eo = [x.end() + struct.unpack('<i', x.group(1))[0] for x in re.finditer(
        rb'\x66\xc7\x05' + re.escape(d0) + rb'\x64\x00\xe8.{4}\x8f\x05' + re.escape(d0) + rb'\x0f\x85(.{4})', d1, re.S)]
    assert len(eo) == 1 and d1[eo[0]:eo[0] + 3] == b'\x66\xc7\x05' and d1[eo[0] + 7:eo[0] + 10] == b'\x00\x00\xc3', eo
    return {'ERRTEXT': fx[m.start(1)], 'CONTMENU': menu, 'SHOWMENU': (1, show), 'A6R': (2, r['A0'] + 24),
            'ERR_OUT': (1, eo[0]), 'FONT_FLAG_': (0, FONT_FLAG)}


def files(w):
    """The DATA files of world w the game opens: its team files (ns stem), WORLDnn.TMD, its XTRA / XTW and RS files,
    its transfer pool."""
    import mkseason
    stem = mkseason.ns_stem(w).upper()
    out = ['%s.%03d' % (stem, n) for n in mkseason.ns_files(w)]
    out += [k for k in mkseason.world_files() if k in ('WORLD%02d.TMD' % w, 'POOL%02d.DAT' % w)]
    xw = 'XTW%d.' % w if stem != 'TEAM' else None
    out += sorted(k for k in mkseason.xtra_files() if xw and k.startswith(xw))
    out += sorted(k for k in mkseason.rs_files() if k.startswith('RS%d' % w))
    return out


def groups(names):
    """[(prefix, [numbers])]: names 'STEM.nnn' grouped by stem (nnn < 256), the others alone (no numbers)."""
    out, by = [], {}
    for n in names:
        m = re.fullmatch(r'([A-Z0-9]+\.)(\d{3})', n)
        if m and int(m.group(2)) < 256:
            by.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            out.append((n, []))
    return [(k, v[i:i + 255]) for k, v in by.items() for i in range(0, len(v), 255)] + out


def asm(wmenus, lang):
    """The routine + its data: wmenus = {list id: world number}."""
    tab = ['align 4', 'INST_TAB:']
    data = []
    for k, (wid, w) in enumerate(sorted(wmenus.items())):
        tab.append(f'    dw {wid}')
        tab.append(f'    dd INST_F{k}')
        b = b''.join(b'DATA\\' + pre.encode() + b'\0' + bytes([len(nums)] + nums) for pre, nums in groups(files(w)))
        data.append(f'INST_F{k}: db ' + ', '.join(map(str, b + b'\0')))
    tab.append('    dw 0FFFFh')
    data.append('INST_MSG: db ' + ', '.join(map(str, MSG[lang].encode('latin1') + b'\0')))
    return ASM + '\n'.join(tab + data) + '\n'


def place(p, at, lang):
    """The check at obj1 offset at (the career cave) and cont_check's stub -> jmp to it. Returns the end."""
    import mkseason
    import nasmcave
    import sacups
    stub = mkseason.INST_STUB[0]
    if stub is None:
        return at
    sym = dict(sites(p), D7REG=(2, sacups.regs(p.le.obj_bytes(1))['D7']))
    src = asm({mkseason.WMENU + n: n for n in mkseason.worlds()}, lang)
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, tobj, toff in fix:
        p.add_ptr(1, at + o, tobj, toff)
    p.put(1, stub, b'\xe9' + struct.pack('<i', lab['inst_chk'] - (stub + 5)))
    print(f'exe: world files check obj1+{at:#x} ({len(code)} B), worlds {sorted(mkseason.worlds())}')
    return (at + len(code) + 3) & ~3
