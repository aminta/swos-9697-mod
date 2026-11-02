"""4.0.6: XTRA players who left their club never come back with it (Enzo's duplicate, 2026-11-02).

xtra.py adds a club's XTRA players (DATA\\XTRA.nnn, players 17-30 of the real squad) to the managed club on every new
career AND every new job (cseg_5DB56). The XTRA block is a static list: a player who had left the club since came back
with it, so he was in two clubs (Enzo: ADRIAN LAHDO bought by SIRACUSA from COMO's extras, then the job at COMO).

The list of XTRA players no longer at their club: xtra's own 'XS' (4.0.2, the XTRA players bought from other clubs on
the market: dw team, db index 16..) plus its overflow 'XL' here, both saved in the .CAR's engine block. An entry is
(the club's team word, the player's index in its XTRA block + 16). Added when an XTRA player leaves his club:
  - bought from it on the market (index >= 16: xtra's xt_sold; here only XS's overflow into XL);
  - bought from its 16-player record (index < 16: an extra the human left in the first 16 of the club's squad order,
    written back into its record at a job change) - xl_sold, chained on the purchase's tail (cseg_56379 -> xt_sold);
  - leaving the managed club: sold, free transfer, any removal (cseg_52EA6, the game's one removal routine) - xl_rm;
  - left in the club's record at a job change (the first 16 by squad order are written back, cseg_942F2 ->
    cseg_5A6A1) - xl_job: he is in the record now, his XTRA copy must not show on the market nor come back.
Read when a club's XTRA block is loaded:
  - xtra_load (new career / new job): xl_read filters the block before the copy into slots 16..: listed players out,
    and any name already in the club's 16 (careerTeam 0..15, the record just copied: also covers saves made before
    this list), then the block compacted (xtra_load counts the first eax named players);
  - the market's block cache (xt_block): xl_readto blanks the XL entries (xt_block blanks the XS ones itself).
XL: db version (1 once written; 0 = an older save or a new career: empty), dw count, dw ring, then XLMAX entries of
3 bytes. XS (128) fills first; XL takes the rest; with XL full too (128 + XLMAX departures of XTRA players in one
career) the oldest XL entry is overwritten (ring). Old saves: no 'XL' -> empty (CONVENTIONS 19: no repair after a
load). Borrowed B-team players (bteam) come from a B club's record, never from an XTRA block: never listed.
4.0.2-4.0.5 crash (found here): an XTRA purchase's tail (cseg_56615 -> AddCareerPoolPlayer) put the generated
replacement into the CPU squads' change list (careerForeignMarketPlayers: dw team, db index, db ext, the player) with the
index 16..; the list's appliers (cseg_243BD when GetTeamPointer loads a club, cseg_5353F / cseg_8C64C over the cache)
copy an entry to record + 76 + index * 38: past the 684-byte record, over the next cached club (its team word) ->
FindTeamInCache's int 3 at obj1+0x17064 at a later season start, or a neighbour's players overwritten. Now xl_sold drops
that entry at once, and the three appliers skip any index >= 16 (gx_0..2): saves that already hold one play on.
The code: obj3 (xtra's obj1 pages are full), the obj1 sites only retargeted (same-size calls).
"""
import re
import struct

import nasmcave
import xtra

XLMAX = 32                             # (the .CAR big-cache room: 125824 B for 160 teams + trailer + engine block)
XL_SIZE = 5 + 3 * XLMAX
LABELS = {}

ASM = r"""
xl_read:                                ; xtra_load's `call xtra_read`: the managed club's block, then filtered + compacted
    call XTRA_READ
    pushad
    xor ebx, ebx                        ; j
.f:
    cmp ebx, MAXE_
    jae .pack
    imul edi, ebx, PLAYER_
    add edi, XBLOCK
    cmp byte [edi + 3], 0
    je .fn
    mov ax, [SEL]
    lea ecx, [ebx + 16]
    call xl_listed
    test eax, eax
    jnz .out1
    lea esi, [edi + 3]
    call xl_inrec
    test eax, eax
    jz .fn
.out1:
    mov byte [edi + 3], 0               ; no name = not there
.fn:
    inc ebx
    jmp .f
.pack:                                  ; the named ones to the front, the rest zeroed
    mov esi, XBLOCK
    mov edi, XBLOCK
    xor edx, edx                        ; kept
    mov ebx, MAXE_
.p:
    cmp byte [esi + 3], 0
    je .pn
    inc edx
    cmp esi, edi
    je .same
    mov ecx, PLAYER_
    push esi
    rep movsb
    pop esi
    jmp .pn
.same:
    add edi, PLAYER_
.pn:
    add esi, PLAYER_
    dec ebx
    jnz .p
    mov ecx, XBLOCK + MAXE_ * PLAYER_
    sub ecx, edi
    xor eax, eax
    rep stosb
    mov [XCOUNT], dl
    mov [esp + 28], edx                 ; eax after popad = the players kept
    popad
    ret

xl_readto:                              ; xt_block's `call xtra_readto` (ax team, edi buffer): the XL entries blanked
    push eax
    call XTRA_READTO
    xchg eax, [esp]                     ; (the count stays the raw one: xt_block's indexes)
    pushad
    movzx edx, word [XL + 1]
    cmp edx, XLMAX_
    jbe .n
    mov edx, XLMAX_
.n:
    cmp byte [XL], 0
    je .out
    mov esi, XL + 5
.e:
    test edx, edx
    jz .out
    cmp [esi], ax
    jne .en
    movzx ecx, byte [esi + 2]
    sub ecx, 16
    jb .en
    cmp ecx, MAXE_
    jae .en
    imul ecx, ecx, PLAYER_
    mov byte [edi + ecx + 3], 0
.en:
    add esi, 3
    dec edx
    jmp .e
.out:
    popad
    pop eax
    ret

xl_listed:                              ; ax team, cl index -> eax 1 if in XS or XL
    push ecx
    push edx
    push esi
    movzx edx, word [XSOLD]
    cmp edx, XSOLD_
    jbe .s0
    mov edx, XSOLD_
.s0:
    mov esi, XSOLD + 2
.s:
    test edx, edx
    jz .l
    cmp [esi], ax
    jne .sn
    cmp [esi + 2], cl
    je .yes
.sn:
    add esi, 3
    dec edx
    jmp .s
.l:
    cmp byte [XL], 0
    je .no
    movzx edx, word [XL + 1]
    cmp edx, XLMAX_
    jbe .l0
    mov edx, XLMAX_
.l0:
    mov esi, XL + 5
.le:
    test edx, edx
    jz .no
    cmp [esi], ax
    jne .ln
    cmp [esi + 2], cl
    je .yes
.ln:
    add esi, 3
    dec edx
    jmp .le
.yes:
    mov eax, 1
    jmp .r
.no:
    xor eax, eax
.r:
    pop esi
    pop edx
    pop ecx
    ret

xl_add:                                 ; ax team, cl index: into XS while it has room, else XL (full: the oldest)
    pushad
    call xl_listed
    test eax, eax
    jnz .out
    mov eax, [esp + 28]                 ; (xl_listed's answer took eax: the team again)
    movzx edx, word [XSOLD]
    cmp edx, XSOLD_
    jae .xl
    lea edx, [edx + edx * 2]
    mov [XSOLD + 2 + edx], ax
    mov [XSOLD + 4 + edx], cl
    inc word [XSOLD]
    jmp .out
.xl:
    mov byte [XL], 1
    movzx edx, word [XL + 1]
    cmp edx, XLMAX_
    jb .app
    movzx edx, word [XL + 3]            ; full: overwrite the oldest
    lea esi, [edx + 1]
    cmp esi, XLMAX_
    jb .rg
    xor esi, esi
.rg:
    mov [XL + 3], si
    jmp .put
.app:
    inc word [XL + 1]
.put:
    lea edx, [edx + edx * 2]
    mov [XL + 5 + edx], ax
    mov [XL + 7 + edx], cl
.out:
    popad
    ret

xl_inrec:                               ; esi -> a name: eax 1 if one of careerTeam's 16 (the record) has it
    push ecx
    push edx
    push esi
    push edi
    xor edx, edx
.q:
    imul edi, edx, PLAYER_
    add edi, CT + 76 + 3
    push esi
    mov ecx, 23
    repe cmpsb
    pop esi
    je .yes
    inc edx
    cmp edx, 16
    jb .q
    xor eax, eax
    jmp .r
.yes:
    mov eax, 1
.r:
    pop edi
    pop esi
    pop edx
    pop ecx
    ret

xl_find:                                ; ax team, esi -> a name: eax = his index (16..) in the team's XTRA block, or 0
    push ebx                            ; (the block read raw into xlbuf, cached by team + file name)
    push ecx
    push edx
    push edi
    cmp ax, [xlbt]
    jne .rd
    mov edx, [XNAMEP]
    cmp edx, [xlbn]
    je .ok
.rd:
    mov [xlbt], ax
    mov edx, [XNAMEP]
    mov [xlbn], edx
    mov edi, xlbuf
    call XTRA_READTO
.ok:
    xor ebx, ebx
.j:
    imul edi, ebx, PLAYER_
    add edi, xlbuf + 3
    cmp byte [edi], 0
    je .jn
    push esi
    mov ecx, 23
    repe cmpsb
    pop esi
    je .hit
.jn:
    inc ebx
    cmp ebx, MAXE_
    jb .j
    xor eax, eax
    jmp .r
.hit:
    lea eax, [ebx + 16]
.r:
    pop edi
    pop edx
    pop ecx
    pop ebx
    ret

xl_rm:                                  ; cseg_52EA6's first `mov ax, [selTeamNumber]`: careerTeam slot D1 leaves the club
    pushad
    movzx ecx, word [D1]
    cmp ecx, 32
    jae .out
    imul esi, ecx, PLAYER_
    add esi, CT + 76 + 3
    cmp byte [esi], 0
    je .out
    mov ax, [SEL]
    call xl_find
    test eax, eax
    jz .out
    mov ecx, eax
    mov ax, [SEL]
    call xl_add
.out:
    popad
    mov ax, [SEL]
    ret

xl_job:                                 ; cseg_942F2's `call cseg_5A6A1` (the old club's first 16 by squad order -> its record)
    pushad
    xor ebx, ebx
.k:
    movzx ecx, byte [CMP + ebx]
    cmp ecx, 32
    jae .kn
    imul esi, ecx, PLAYER_
    add esi, CT + 76 + 3
    cmp byte [esi], 0
    je .kn
    mov ax, [SEL]
    call xl_find
    test eax, eax
    jz .kn
    mov ecx, eax
    mov ax, [SEL]
    call xl_add
.kn:
    inc ebx
    cmp ebx, 16
    jb .k
    popad
    jmp PREV_JOB

xl_sold:                                ; cseg_56379's tail call (D0 seller, D1 index): a player of his 16 who is one of
    pushad                              ; the seller's XTRA players -> listed (the name read before the game replaces him)
    mov byte [xlname], 0
    movzx ecx, word [D1]
    cmp ecx, 16
    jae .pre
    mov esi, REGS
    mov edi, xlregs
    mov ecx, 15
    rep movsd
    call GTP                            ; GetTeamPointer: D0 -> A0 = the record
    mov esi, [A0]
    movzx ecx, word [xlregs + 4]
    imul ecx, ecx, PLAYER_
    lea esi, [esi + 76 + ecx + 3]
    mov edi, xlname
    mov ecx, 23
    rep movsb
    mov esi, xlregs
    mov edi, REGS
    mov ecx, 15
    rep movsd
.pre:
    mov eax, [D0]
    mov [xlsd0], eax
    mov eax, [D1]
    mov [xlsd1], eax
    popad
    call PREV_SOLD                      ; xtra's xt_sold (the game's tail, then XS)
    pushad
    mov ax, [xlsd0]
    cmp ax, [SEL]
    je .out
    movzx ecx, word [xlsd1]
    cmp ecx, 16
    jb .rec
    cmp ecx, 16 + MAXE_
    jae .out
    call xl_add                         ; (already in XS: nothing; XS full: into XL)
    movzx edx, word [NFM2]              ; the game's tail added the generated replacement to the CPU squads' change list
    test edx, edx                       ; with index 16..: drop it (applied, it would land past the 684-byte record)
    jz .out
    dec edx
    imul edx, edx, 42
    add edx, CFMP
    cmp [edx], ax
    jne .out
    cmp [edx + 2], cl
    jne .out
    dec word [NFM2]
    cmp word [NEWN], 0
    je .out
    dec word [NEWN]
    jmp .out
.rec:
    cmp byte [xlname], 0
    je .out
    mov esi, xlname
    call xl_find
    test eax, eax
    jz .out
    mov ecx, eax
    mov ax, [xlsd0]
    call xl_add
.out:
    popad
    ret

gx_0:                                   ; the change list's three appliers (cseg_243BD, cseg_5353F, cseg_8C64C): their
    mov esi, [A6]                       ; `mov esi, [A6] / mov al, [esi + 2]` (the entry's player index); index >= 16
    mov al, [esi + 2]                   ; (4.0.2-4.0.5 saves: an XTRA purchase's replacement) = not this club's entry
    cmp al, 16
    jb .ok
    mov dword [esp], SKIP_0
.ok:
    ret
gx_1:
    mov esi, [A6]
    mov al, [esi + 2]
    cmp al, 16
    jb .ok
    mov dword [esp], SKIP_1
.ok:
    ret
gx_2:
    mov esi, [A6]
    mov al, [esi + 2]
    cmp al, 16
    jb .ok
    mov dword [esp], SKIP_2
.ok:
    ret

align 4
xlbn: dd 0
xlsd0: dd 0
xlsd1: dd 0
xlregs: times 15 dd 0
xlbt: dw -1
xlname: times 24 db 0
xlmark: db 'XLFT'                      ; (the harness finds the list by this)
XL: times XLSZ_ db 0
align 4
xlbuf: times MAXE_ * PLAYER_ db 0
"""


def sites(p, regs):
    """obj1 sites in the original exe: rm = cseg_52EA6's first `mov ax, [selTeamNumber]` (6 bytes), job = cseg_942F2's
    `call cseg_5A6A1` (the old club's record written back)."""
    d1 = p.le.obj_bytes(1)
    _, _, ct, cmp, sel = xtra.LABELS['SITES']
    D0 = regs['D7'] - 28
    D1, D7, A0 = D0 + 4, regs['D7'], regs['A0']
    ptr = lambda a: re.escape(struct.pack('<I', a))
    m = [x.start() for x in re.finditer(rb'\x66\xa1' + ptr(sel) + rb'\x66\xa3' + ptr(D0) + rb'\xff\x35' + ptr(D1) +
                                        rb'\xe8....\x8f\x05' + ptr(D1) + rb'\x66\xc7\x05' + ptr(D0) + rb'\x00\x00\x8b\x35' +
                                        ptr(A0) + rb'\x8a\x46\x6d', d1, re.S)]
    assert len(m) == 1, ('cseg_52EA6', m)
    rm = m[0]
    m = [x.start(1) for x in re.finditer(rb'\x66\xa1' + ptr(D0) + rb'\x66\xa3' + ptr(D7) + rb'\x66\xa1....\x66\x0b\xc0\x75.'
                                         rb'\xff\x35' + ptr(D1) + rb'\xff\x35' + ptr(D7) + rb'(\xe8....)\x8f\x05' + ptr(D7) +
                                         rb'\x8f\x05' + ptr(D1), d1, re.S)]
    assert len(m) == 1, ('cseg_942F2', m)
    job = m[0]
    A6 = A0 + 24
    gx = [(x.start() + 6, x.start() + 6 + struct.unpack('<i', x.group(1))[0])
          for x in re.finditer(rb'\x0f\x85(....)\x8b\x35' + ptr(A6) + rb'\x8a\x46\x02\xa2' + ptr(D0) + rb'\xa0' + ptr(D0) +
                               rb'\x66\x98', d1, re.S)]
    assert len(gx) == 3, ('change list appliers', gx)      # (site, its `jnz` = not this club's entry)
    m = [x for x in re.finditer(rb'\x66\x83\x05(....)\x01\x66\x83\x05(....)\x01\xc6\x05....\xff\xc3', d1, re.S)]
    assert len(m) == 1, ('AddCareerPoolPlayer', m)
    nfm2, newn = (struct.unpack('<I', m[0].group(k))[0] for k in (1, 2))
    k = d1.rfind(b'\xc7\x05' + struct.pack('<I', A6), m[0].start() - 0xc0, m[0].start())
    assert k > 0, 'careerForeignMarketPlayers'
    cfmp = struct.unpack_from('<I', d1, k + 6)[0]
    return {'rm': rm, 'job': job, 'gx': gx, 'nfm2': nfm2, 'newn': newn, 'cfmp': cfmp, 'A6': A6, 'ct': ct, 'cmp': cmp, 'sel': sel, 'D0': D0, 'D1': D1, 'A0': A0}


def patch(p, at):
    """Code + data at obj3:at (after the previous obj3 block's end); returns the end. Needs xtra.patch first."""
    import engine
    import sacups
    d1 = p.le.obj_bytes(1)
    regs = sacups.regs(d1)
    s = sites(p, regs)
    X = xtra.LABELS
    assert p.get(1, s['rm'], 6) == d1[s['rm']:s['rm'] + 6], 'cseg_52EA6 already patched'
    # xtra's own calls of its block readers, retargeted: xtra_load -> xtra_read, xt_block -> xtra_readto
    def call_in(fn, target, span=0x60):
        b = bytes(p.get(1, fn, span))
        k = [i for i in range(span - 5) if b[i] == 0xE8 and fn + i + 5 + struct.unpack_from('<i', b, i + 1)[0] == target]
        assert len(k) == 1, (hex(fn), hex(target), k)
        return fn + k[0]
    c_read = call_in(X['xtra_load'], X['xtra_read'])
    c_readto = call_in(X['xt_block'], X['xtra_readto'], 0x80)
    sym = {'XTRA_READ': (1, X['xtra_read']), 'XTRA_READTO': (1, X['xtra_readto']), 'XBLOCK': (1, X['xblock']),
           'XCOUNT': (1, X['xcount']), 'XSOLD': (1, X['xsold']), 'XNAMEP': (1, X['xtra_namep']), 'GTP': (1, X['GTP']),
           'SEL': (2, s['sel']), 'CT': (2, s['ct']), 'CMP': (2, s['cmp']), 'REGS': (2, s['D0']), 'D0': (2, s['D0']),
           'D1': (2, s['D1']), 'A0': (2, s['A0']), 'PREV_JOB': p.call_target(1, s['job']),
           'PREV_SOLD': p.call_target(1, X['SOLD_SITE']), 'PLAYER_': (0, xtra.PLAYER), 'MAXE_': (0, xtra.MAX_EXTRA),
           'XSOLD_': (0, xtra.XSOLD), 'XLMAX_': (0, XLMAX), 'XLSZ_': (0, XL_SIZE), 'A6': (2, s['A6']),
           'NFM2': (2, s['nfm2']), 'NEWN': (2, s['newn']), 'CFMP': (2, s['cfmp'])}
    for i, (site, skip) in enumerate(s['gx']):
        assert p.get(1, site, 9) == d1[site:site + 9], ('change list applier already patched', hex(site))
        sym[f'SKIP_{i}'] = (1, skip)
    assert sym['PREV_SOLD'] == (1, X['xt_sold']), sym['PREV_SOLD']
    at = (at + 15) & ~15
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['rm'] + 2)                            # mov ax, [selTeamNumber]
    p.branch(1, s['rm'], 0xE8, 3, lab['xl_rm'], 6)
    p.branch(1, s['job'], 0xE8, 3, lab['xl_job'])
    p.branch(1, X['SOLD_SITE'], 0xE8, 3, lab['xl_sold'])
    p.branch(1, c_read, 0xE8, 3, lab['xl_read'])
    p.branch(1, c_readto, 0xE8, 3, lab['xl_readto'])
    for i, (site, _) in enumerate(s['gx']):
        p.remove(1, site + 2)                           # mov esi, [A6]
        p.branch(1, site, 0xE8, 3, lab[f'gx_{i}'], 9)
    engine.ITEM_AT['XL'] = (3, lab['XL'])
    LABELS.update(lab)
    print(f'exe: XTRA players who left stay out (XS + XL {XLMAX}): code obj3+{at:#x} ({len(code)} B), sites rm '
          f'{s["rm"]:#x} job {s["job"]:#x} sold {X["SOLD_SITE"]:#x}, change list guards {[hex(g) for g, _ in s["gx"]]}')
    return at + len(code)
