"""Italian play-offs / play-outs of a career world at the season end: the glue around tools/dplay.c (rules there).

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
Not playable yet (step 2: the career club's ties in slot 4); the season's ties are logged in DP_OUT (harness).
"""
import os
import re
import struct

ASM = '''
dp_find:                                ; -> esi = the DP_TAB entry of the league A4 in the running world, or ZF = 1
    mov edx, [A4R]
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

dp_cap:                                 ; replaces `call cseg_9221F` in cseg_91D4D
    call C9221F
    pushad
    call dp_find
    jz .x
    movzx eax, word [D7R]               ; the division -> table 0 (Serie B) or 1.. (the groups)
    movzx ecx, byte [esi + 2]
    sub eax, ecx
    jb .x
    movzx ecx, byte [esi + 4]
    cmp eax, ecx
    ja .x
    movzx ecx, word [DIY + 31h]
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
    movzx esi, word [DIY + 6Dh + ebx * 2]   ; the place's row offset (row * 12h)
    mov eax, esi
    xor edx, edx
    push ecx
    mov ecx, 12h
    div ecx
    pop ecx
    mov ax, [DIY + 12Dh + eax * 2]      ; its team number
    mov [edi], ax
    mov edx, [DIY + esi + 2B3h]         ; its team record: the global number
    add edx, [SELTEAMS]
    mov ax, [edx + 2]
    mov [edi + 2], ax
    mov ax, [DIY + esi + 2B9h]          ; won
    mov [edi + 4], ax
    mov ax, [DIY + esi + 2BFh]          ; for
    mov [edi + 6], ax
    mov ax, [DIY + esi + 2C1h]          ; against
    mov [edi + 8], ax
    mov ax, [DIY + esi + 2C3h]          ; points
    mov [edi + 10], ax
    add edi, RSZ
    inc ebx
    jmp .r
.x:
    popad
    ret

dp_end:                                 ; replaces `call cseg_9228D` (the play-offs of division D7) in cseg_91D4D
    call C9228D
    pushad
    call dp_find
    jz .x
    mov edx, [A4R]
    movzx eax, word [D7R]
    inc eax
    cmp al, [edx + 9]                   ; (the league's last division)
    jne .x
    mov al, [esi + 4]
    mov [DP_IN], al                     ; ng
    movzx ecx, al
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
    pop es
    movzx ecx, byte [DP_OUT]
    xor ebx, ebx
.m:
    cmp ebx, ecx
    jae .clr
    imul esi, ebx, MSZ
    add esi, DP_OUT + O_MV
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

DP_TAB: TAB_BYTES
'''


def _sites(p):
    """(call of cseg_9221F, cseg_9221F, call of cseg_9228D, cseg_9228D, DIY, careerTeam, relegated / promoted
    animation flags), all in cseg_91D4D / cseg_925C9."""
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


def table_bytes(tables):
    out = bytearray()
    for world, lid, u, f, ng in tables:
        assert 1 <= world <= 255 and f == u + 1 and 2 <= ng <= 4, (world, u, f, ng)
        out += bytes((world, lid, u, f, ng))
    return bytes(out + b'\0')


LABELS = {}


def patch(p, at, limit, tables, bss_at):
    """C + glue in obj1 at..limit, the C .bss at obj2 bss_at (0x1000). Returns the end."""
    import careerworld
    import cobj
    import mkseason
    import nasmcave
    cap, c9221f, end_site, c9228d, diy, ct, rel, pro, r = _sites(p)
    for s in (cap, end_site):
        assert p.get(1, s, 5) == p.le.obj_bytes(1)[s:s + 5], f'obj1+{s:#x} already hooked'
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dplay.c'))
    syms, cend, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= 0x1000, hex(bss)
    lay = dict(zip(('IN_SIZE', 'OUT_SIZE', 'RSZ', 'NT', 'O_N', 'O_T', 'O_MV', 'MSZ'),
                   struct.unpack('<8I', p.get(1, syms['DP_LAYOUT'][1], 32))))
    assert lay['RSZ'] == 12 and lay['MSZ'] == 8, lay
    sel = mkseason._hook_sites(p)[3]
    s = careerworld.SITES
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update({'NDIV': (0, 5), 'DP_IN': syms['DP_IN'], 'DP_OUT': syms['DP_OUT'], 'dp_season': syms['dp_season'],
                    'A4R': (2, r['A0'] + 16), 'D7R': (2, r['D7']), 'SLT': s['slt'], 'SLTCOPY': s['sltcopy'],
                    'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'DIY': (2, diy), 'SELTEAMS': (2, sel),
                    'CAREERTEAM': (2, ct), 'ANIM_REL': (2, rel), 'ANIM_PRO': (2, pro),
                    'C9221F': (1, c9221f), 'C9228D': (1, c9228d),
                    'TAB_BYTES': (0, 'db ' + ', '.join(str(b) for b in table_bytes(tables)))})
    glue = (cend + 15) & ~15
    code, fix = nasmcave.assemble(ASM, glue, symbols)
    lab = nasmcave.labels(ASM, glue, symbols)
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    for site, target in ((cap, 'dp_cap'), (end_site, 'dp_end')):    # (relative calls: no fixups)
        p.put(1, site + 1, struct.pack('<i', lab[target] - (site + 5)))
    LABELS.update(lab, DP_IN=syms['DP_IN'], DP_OUT=syms['DP_OUT'], layout=lay)
    print(f"exe: Italian play-offs (dplay): {len(tables)} leagues, C obj1+{at:#x}..{cend:#x}, glue ..{glue + len(code):#x}, "
          f"DP_IN obj2+{syms['DP_IN'][1]:#x}, DP_OUT obj2+{syms['DP_OUT'][1]:#x}, hooks obj1+{cap:#x} / +{end_site:#x}")
    return glue + len(code)
