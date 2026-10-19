"""Extra career data saved as a trailer after the team records of the .CAR file (Roadmap 2).

A career file is the obj2 range careerFileBuffer .. g_numSelectedTeams (95151 bytes, the same in every language)
+ the N cached team records (684 B each) of g_selectedTeams (room for 100). SaveCareerFile writes
fixed + 2 + N*684 bytes (D1 = length, A1 = careerFileBuffer) with WriteFile; LoadCareerFile reads the whole file
into careerFileBuffer with LoadFile (D1 = bytes read) and calls ProcessCareerFile.

Block 'C6' (session 27): the South American lists (Libertadores 42 B = 20 group clubs + the holder, Supercopa and
CONMEBOL 32 B each), the Intercontinental pair (4 B) and the extra cup lists of cafcups.CUPS (CAF x3, CONCACAF, Asian x2:
6 x 32 B) = 2 + 302 bytes. ('C5' of 1.3 was the same with a 20-club Libertadores, 'C4' of 1.2 with 16 clubs.)
save_trailer (replaces `call WriteFile`): writes the block after the team records and adds its size to D1, only if it
fits in g_selectedTeams (N*684 + size <= 68400: the pseudo registers D0..D7 follow).
load_trailer (replaces `call ProcessCareerFile`): every list from the defaults (first season), then from older formats
- 1.0/1.1: 'S2' (3 lists + pair) or 'SA' (3 lists) in someLeaguesTable[1740..1842]; that block (sum 0) is cleared,
  so global numbers 1730..1846 are free again;
- older trailers (OLD_TRAILERS): 'C1' 1.1 (3 CAF lists), 'C2' and 'C3' 1.2 dev, 'C4' 1.2, 'C5' 1.3 (their 16/20-club
  Libertadores list is completed by lib_merge with default clubs not in it; the season end rebuilds it anyway);
- 'C6': everything.
After the main block (current mark only; only if N*684 + all fits, the main block alone as before): the engine block 'EN' (engine.save_item: word length, then per item word id,
word length, bytes), any world; unknown ids skipped, missing items zeroed (unless saved with clear=False).
Then the career mark 'S3' + balance byte at someLeaguesTable[1847..1849] (and leaguesTableCopy): sacups.init_sa
calls new_career_defaults when a season starts without it (InitCareer clears the table = new career).
"""
import re
import struct

import nasmcave
import sacups

EN_MARK = 0x4E45                          # 'EN': the engine block after the main one (engine.save_item)
MARK, S2, SA = 0x3743, 0x3253, 0x4153     # 'C7' (2.1: + Argentina), 'S2' 'SA' (1.0/1.1 block in someLeaguesTable)
C6 = 0x3643                               # 2.0: the same first 10 items (Libertadores of 21 as saved)
# older trailers: (mark, first item, item count, Libertadores bytes) — 'C5' 1.3 (10 items, 20 clubs), 'C4' 1.2 (10 items,
# 16 clubs), 'C3' 1.2 dev (8 items), 'C2' (CAF + CONCACAF), 'C1' 1.1 (CAF). An old Libertadores list is read through
# OLD_ITEMS<bytes> into LIBOLD, then lib_merge keeps it and adds the first default clubs not among them up to LIB_N.
OLD_TRAILERS = [(0x3643, 0, 10, None), (0x3543, 0, 10, 40), (0x3443, 0, 10, 32), (0x3343, 0, 8, 32), (0x3243, 4, 4, 32), (0x3143, 4, 3, 32)]
OLD_LIB = 32                              # 1.0/1.1 (S2/SA) and 1.2
OLD_LIB_MAX = 40
NSA = 4                                   # SA items first: Lib, Sup, CON, Intercontinental pair
OLD_SIZE = 103                            # 1.0/1.1 block in someLeaguesTable (sum 0)
TEAM_SIZE, SELECTED_ROOM = 684, 68400

EN_SAVE = '''
    lea eax, [ebx + TOTAL]              ; the engine block, if it fits too (else a load clears its items)
    cmp eax, [ROOMV]
    ja .skip
    mov word [edi], EN_MARK
    mov word [edi + 2], TOTAL - BLOCK - 4
    add edi, 4
    mov edx, EN_ITEMS
    mov ebp, EN_N
.en:
    mov ax, [edx + 8]
    mov [edi], ax
    mov eax, [edx + 4]
    mov [edi + 2], ax
    add edi, 4
    mov esi, [edx]
    mov ecx, [edx + 4]
.eb:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .eb
    add edx, 12
    dec ebp
    jnz .en
    add dword [D1], TOTAL - BLOCK'''

ASM = '''
save_trailer:
    pushad
    movzx eax, word [NUMSEL]
    imul eax, eax, TEAM_SIZE
    mov edi, eax                        ; after the records: the career's cache + N*684 (g_selectedTeams =
    add edi, [SELBASEV]                 ; careerFileBuffer + [D1], or a league-phase world's big cache, careerworld)
    mov ebx, eax
    add eax, BLOCK
    cmp eax, [ROOMV]
    ja .skip
    mov word [edi], MARK
    add edi, 2
    mov edx, ITEMS
    mov ebp, NITEMS
.next:
    mov esi, [edx]
    mov ecx, [edx + 4]
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    add edx, 8
    dec ebp
    jnz .next
    add dword [D1], BLOCK
;EN_SAVE
.skip:
    popad
    jmp WRITEFILE

load_trailer:
    call [LOADCOPY]                     ; (a big world: the file read into its stage, out to the fixed part + cache)
    pushad
    call en_reset
    mov word [LIBOLD], 0FFFFh           ; no old Libertadores list read (yet)
    mov dword [LIBOLD_N], OLD_LIB
    mov esi, DEFAULTS
    mov edx, ITEMS
    mov ebp, NITEMS
    call items_in
    mov ebx, OLD_SAVED                  ; 1.0/1.1: lists in someLeaguesTable[1740..]
    mov ebp, NSA                        ; 'S2': 3 lists + Intercontinental pair, same order as ITEMS
    cmp word [ebx], S2
    je .old
    mov ebp, 3                          ; 'SA': 3 lists
    cmp word [ebx], SA
    jne .trailer
.old:
    lea esi, [ebx + 2]
    mov edx, OLD_ITEMS
    call items_in
    mov edi, ebx                        ; the block adds up to 0: clearing it keeps cseg_9487A's check
    mov ecx, OLD_SIZE
.z:
    mov byte [edi], 0
    inc edi
    dec ecx
    jnz .z
.trailer:
    movzx eax, word [NUMSEL]
    imul eax, eax, TEAM_SIZE
    mov esi, eax                        ; after the records (the career's cache + N*684)
    add esi, [SELBASEV]
    add eax, FIXED                      ; trailer offset in the file
    mov ebx, eax
    mov edx, ITEMS
    mov ebp, NITEMS
    mov ecx, BLOCK
    cmp word [esi], MARK
    je .cur
;OLD_TRAILERS
    jmp .done
.cur:
    mov byte [EN_CUR], 1                ; (the current main block: the engine block may follow)
.check:
    add ecx, ebx
    cmp ecx, [D1]
    ja .done
    add esi, 2
    call items_in
    cmp byte [EN_CUR], 1
    jne .done
    call en_read                        ; esi = after the main block, ebx = its offset in the file
.done:
    call en_finish
;EN_AFTER
    call lib_merge
    call set_mark
    popad
    jmp PROCESS

lib_merge:                              ; an old 16/20-club list: keep it, then default clubs not in it up to LIB_N
    cmp word [LIBOLD], 0FFFFh
    je .ret
    mov esi, LIBOLD
    mov edi, [ITEMS]
    mov ecx, [LIBOLD_N]
.c:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .c
    mov ebx, DEFAULTS                   ; the default Libertadores list comes first
    mov edx, LIB_N
.cand:
    mov ax, [ebx]
    mov esi, [ITEMS]
    mov ecx, [LIBOLD_N]
    shr ecx, 1
.in:
    cmp [esi], ax
    je .skip
    add esi, 2
    dec ecx
    jnz .in
    mov [edi], ax
    add edi, 2
    mov eax, [ITEMS]
    add eax, 2 * LIB_N
    cmp edi, eax
    je .end
.skip:
    add ebx, 2
    dec edx
    jnz .cand
.end:
    mov word [LIBOLD], 0FFFFh
.ret:
    ret

new_career_defaults:
    pushad
    mov esi, DEFAULTS
    mov edx, ITEMS
    mov ebp, NITEMS
    call items_in
    call en_reset                       ; a new career: the engine items from zero (clear flag)
    call en_finish
    call set_mark
    popad
    ret

set_mark:                               ; 'S3' + balance: the table still adds up to 0
    mov word [MARK3_AT], MARK3
    mov byte [MARK3_AT + 2], MARK3_BAL
    mov word [MARK3_COPY], MARK3
    mov byte [MARK3_COPY + 2], MARK3_BAL
    ret

lt_ret:
    ret
align 4
ROOMV: dd ROOM                          ; room for the records + this block (careerworld: a big world's cache)
SELBASEV: dd SELBUF                     ; the career's team cache (careerworld: a league-phase world's is bigger)
LOADCOPY: dd lt_ret

items_in:                               ; esi -> ebp items starting at [edx] (dd address, dd size)
    mov edi, [edx]
    mov ecx, [edx + 4]
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    add edx, 8
    dec ebp
    jnz items_in
    ret

; the engine block 'EN' (engine.save_item): mark, word length, then per item word id, word length, the bytes;
; items another build does not know are skipped; items missing from the save are zeroed (unless their clear flag is 0)
en_reset:
    push ecx
    mov byte [EN_CUR], 0
    mov ecx, EN_N + 1
.z:
    mov byte [EN_FOUND + ecx - 1], 0
    dec ecx
    jnz .z
    pop ecx
    ret

en_read:
    pushad
    cmp word [esi], EN_MARK
    jne .r
    movzx ecx, word [esi + 2]
    lea eax, [ebx + BLOCK + 4]
    add eax, ecx
    cmp eax, [D1]                       ; (all of it in the file)
    ja .r
    lea edi, [esi + 4]
    add ecx, edi                        ; end
.e:
    cmp edi, ecx
    jae .r
    movzx eax, word [edi]               ; id
    movzx ebp, word [edi + 2]           ; length
    push ecx
    mov edx, EN_ITEMS
    xor ecx, ecx
.f:
    cmp ecx, EN_N
    jae .nf
    cmp ax, [edx + 8]
    jne .nx
    cmp ebp, [edx + 4]                  ; (another size: not this build's item)
    jne .nf
    mov byte [EN_FOUND + ecx], 1
    push edi
    lea esi, [edi + 4]
    mov edi, [edx]
    mov ecx, ebp
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    pop edi
    jmp .nf
.nx:
    add edx, 12
    inc ecx
    jmp .f
.nf:
    pop ecx
    lea edi, [edi + ebp + 4]
    jmp .e
.r:
    popad
    ret

en_finish:
    pushad
    mov edx, EN_ITEMS
    xor ecx, ecx
.l:
    cmp ecx, EN_N
    jae .r
    cmp byte [EN_FOUND + ecx], 0
    jne .n
    test byte [edx + 10], 1             ; clear flag
    jz .n
    mov edi, [edx]
    mov eax, [edx + 4]
.z:
    mov byte [edi], 0
    inc edi
    dec eax
    jnz .z
.n:
    add edx, 12
    inc ecx
    jmp .l
.r:
    mov byte [EN_CUR], 0
    popad
    ret

EN_CUR: db 0
EN_FOUND: times EN_N + 1 db 0
align 4
EN_ITEMS: EN_ENTRIES
ITEMS: ITEM_ENTRIES
OLD_ITEMS: dd LIBOLD, OLD_LIB       ; the rest as ITEMS
    OLD_ENTRIES
OLD_ITEMS40: dd LIBOLD, 40
    OLD_ENTRIES
LIBOLD_N: dd OLD_LIB
LIBOLD: times OLD_LIB_MAX db 0
DEFAULTS: DEFAULT_BYTES
'''


INFO = {}                                 # symbols + tail dwords for careerworld.patch_tails (big worlds)


def patch(p, cave, items, tails=False):
    """items = [(obj1 offset, size)] to save: sacups.SAVE_ITEMS + the extra cup lists. tails: save_trailer and
    load_trailer end with `jmp [SAVE_TAIL]` / `jmp [LOAD_TAIL]` (dwords = WriteFile / ProcessCareerFile, retargeted by
    careerworld.patch_tails: a big world appends its 'W1' block). Returns (cave end, new_career_defaults offset)."""
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a1, dreg1 = r['A1'], r['D7'] - 24                     # D0..D7 consecutive dwords
    A1, D1 = (re.escape(struct.pack('<I', x)) for x in (a1, dreg1))
    # LoadCareerFile: mov A1, offset careerFileBuffer; call LoadFile; jnz; call SetZeroFlag2; jnz; call ProcessCareerFile
    m = [x for x in re.finditer(rb'\xc7\x05' + A1 + rb'(.{4})\xe8.{4}\x75.\xe8.{4}\x75.\xe8(.{4})', d1, re.S)]
    m = [x for x in m if sum(y.group(1) == x.group(1) for y in m) == 1]   # the other two load competition files
    assert len(m) == 1, len(m)
    career = struct.unpack('<I', m[0].group(1))[0]
    load_call = m[0].end() - 5
    load_a1 = m[0].start() + 6                            # (its careerFileBuffer immediate: a big world's stage)
    process = m[0].end() + struct.unpack('<i', m[0].group(2))[0]
    # SaveCareerFile: mov A1, offset careerFileBuffer; mov eax, A1; sub D1, eax; call WriteFile
    m = [x for x in re.finditer(rb'\xc7\x05' + A1 + re.escape(struct.pack('<I', career)) + rb'\xa1' + A1 +
                                rb'\x29\x05' + D1 + rb'\xe8(.{4})', d1, re.S)]
    assert len(m) == 1, len(m)
    save_call = m[0].end() - 5
    writefile = m[0].end() + struct.unpack('<i', m[0].group(1))[0]
    # ... its start: mov D1, offset g_numSelectedTeams; mov ax, g_numSelectedTeams
    k = d1.rfind(b'\xc7\x05' + struct.pack('<I', dreg1), save_call - 0x80, save_call)
    numsel = struct.unpack_from('<I', d1, k + 6)[0]
    assert d1[k + 10:k + 12] == b'\x66\xa1' and struct.unpack_from('<I', d1, k + 12)[0] == numsel
    assert numsel - career == 95151, hex(numsel - career)          # g_numSelectedTeams at save offset 95151

    import sacups as sa
    table, copy = sa.TABLES[0]
    assert len(items) >= NSA + 4 and [n for _, n in items[:NSA]] == [2 * sacups.LIB_N, 32, 32, 4]
    block = 2 + sum(n for _, n in items)
    import engine
    en = engine.save_items()                      # the engine block 'EN' after the main one
    en_block = 4 + sum(4 + sz for _, _, sz, _, _ in en) if en else 0
    nmax = (SELECTED_ROOM - block - en_block) // TEAM_SIZE   # save_trailer writes 'EN' only if N*684 + all <= 68400
    assert en_block < 0x10000 and nmax >= 80, (block, en_block, nmax)   # (the main block alone: N <= 98; EN in the normal
                                                  # cache matters for world-0 careers only, whose 4.0 items are unused)
    import careerworld                            # a big world's cache (its own SELBASEV / ROOMV): all of it at SEL_N
    if careerworld.BSS[0] is not None:
        assert careerworld.SEL_N * TEAM_SIZE + block + en_block <= careerworld.SEL_ROOM, \
            ('big cache room', careerworld.SEL_N, block, en_block, careerworld.SEL_ROOM)
    defaults = b''.join(p.get(1, off, n) for off, n in items)
    bal = -(sa.MARK3 & 0xff) - (sa.MARK3 >> 8) & 0xff
    symbols = {'NUMSEL': (2, numsel), 'CAREER': (2, career), 'D1': (2, dreg1), 'WRITEFILE': (1, writefile),
               'SELBUF': (2, numsel + 2),
               'PROCESS': (1, process), 'MARK': (0, MARK), 'S2': (0, S2), 'SA': (0, SA),
               'TEAM_SIZE': (0, TEAM_SIZE), 'ROOM': (0, SELECTED_ROOM), 'BLOCK': (0, block),
               'FIXED': (0, numsel - career + 2), 'NITEMS': (0, len(items)), 'NSA': (0, NSA), 'OLD_SIZE': (0, OLD_SIZE),
               'OLD_SAVED': (2, table + sa.SAVED_GLOBAL), 'MARK3_AT': (2, table + sa.MARK3_GLOBAL),
               'MARK3_COPY': (2, copy + sa.MARK3_GLOBAL), 'OLD_LIB': (0, OLD_LIB), 'OLD_LIB_MAX': (0, OLD_LIB_MAX), 'LIB_N': (0, sacups.LIB_N), 'MARK3': (0, sa.MARK3), 'MARK3_BAL': (0, bal),
               'DEFAULT_BYTES': (0, 'db ' + ', '.join(str(b) for b in defaults)),
               'TOTAL': (0, block + en_block), 'EN_N': (0, len(en)), 'EN_MARK': (0, EN_MARK)}
    late = []                                     # items / routines whose address comes later in patch_exe
    for k_, (name, _, _, _, at) in enumerate(en):
        symbols[f'E{k_}'] = at or (1, cave)       # (a placeholder fixup, retargeted by late())
        if at is None:
            late.append(('item', name, 'EN_ITEMS', 12 * k_))
    symbols['EN_ENTRIES'] = (0, 'dd ' + ', '.join(f'E{k_}, {sz}, {iid | (int(cl) << 16)}'
                                                  for k_, (_, iid, sz, cl, _) in enumerate(en)) if en else 'dd 0')
    for k_, (off, n) in enumerate(items):         # obj1 addresses as symbols: nasmcave adds their fixups
        symbols[f'I{k_}'] = (1, off)
    symbols['ITEM_ENTRIES'] = (0, 'dd ' + ', '.join(f'I{k_}, {n}' for k_, (_, n) in enumerate(items)))
    symbols['OLD_ENTRIES'] = (0, 'dd ' + ', '.join(f'I{k_}, {n}' for k_, (_, n) in enumerate(items) if k_))
    olds = []
    for mark, first, count, lib_b in OLD_TRAILERS:
        if lib_b is None:                         # a trailer whose items are the first ones of the current: straight in
            size = 2 + sum(n for k_, (_, n) in enumerate(items) if first <= k_ < first + count)
            olds += [f'    mov edx, ITEMS + 8 * {first}', f'    mov ebp, {count}', f'    mov ecx, {size}',
                     f'    cmp word [esi], {mark:#x}', '    je .check']
            continue
        size = 2 + sum(lib_b if k_ == 0 else n for k_, (_, n) in enumerate(items) if first <= k_ < first + count)
        tbl = 'OLD_ITEMS' if lib_b == OLD_LIB else f'OLD_ITEMS{lib_b}'
        olds += [f'    mov edx, {tbl} + 8 * {first}', f'    mov ebp, {count}', f'    mov ecx, {size}',
                 f'    mov dword [LIBOLD_N], {lib_b}', f'    cmp word [esi], {mark:#x}', '    je .check']
    asm = ASM.replace(';OLD_TRAILERS', '\n'.join(olds))
    if en:
        asm = asm.replace(';EN_SAVE', EN_SAVE)
    cbs = engine.after_loads()                    # after the engine items (or their clearing): pushad, call, popad
    asm = asm.replace(';EN_AFTER', '\n'.join(f'    pushad\n    call [EN_CB + {4 * k}]\n    popad' for k in range(len(cbs))))
    asm += 'align 4\nEN_CB: ' + ('dd ' + ', '.join(f'CB{k}' for k in range(len(cbs))) if cbs else 'dd 0') + '\n'
    for k, (name, at) in enumerate(cbs):
        symbols[f'CB{k}'] = at or (1, cave)
        if at is None:
            late.append(('call', name, 'EN_CB', 4 * k))
    if tails:
        asm = asm.replace('    popad\n    jmp WRITEFILE', '    popad\n    jmp [SAVE_TAIL]')
        asm = asm.replace('    popad\n    jmp PROCESS', '    popad\n    jmp [LOAD_TAIL]')
        asm += 'align 4\nSAVE_TAIL: dd WRITEFILE\nLOAD_TAIL: dd PROCESS\n'
    while True:                                   # no pointer may straddle an obj1 page (LE fixups are per page)
        code, fix = nasmcave.assemble(asm, cave, symbols)
        if all((cave + off) % 0x1000 <= 0x1000 - 4 for off, _, _ in fix):
            break
        cave += 4
    labels = nasmcave.labels(asm, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.put(1, save_call + 1, struct.pack('<i', labels['save_trailer'] - (save_call + 5)))
    p.put(1, load_call + 1, struct.pack('<i', labels['load_trailer'] - (load_call + 5)))
    INFO.clear()
    INFO.update({k: symbols[k] for k in ('NUMSEL', 'CAREER', 'D1', 'WRITEFILE', 'PROCESS', 'BLOCK', 'FIXED', 'ROOM',
                                         'MARK', 'SELBUF')})
    INFO.update(load_a1=load_a1, roomv=labels['ROOMV'], loadcopy=labels['LOADCOPY'], selbasev=labels['SELBASEV'])
    if tails:
        INFO['tails'] = (labels['SAVE_TAIL'], labels['LOAD_TAIL'])
    INFO['EN'] = [(n, iid, sz) for n, iid, sz, _, _ in en]
    INFO['late'] = [(kind, name, labels[lab] + off) for kind, name, lab, off in late]
    print(f'exe: .CAR trailer {chr(MARK & 0xff)}{chr(MARK >> 8)} ({block} B' + (f' + engine block EN {en_block} B: ' + ', '.join(n for n, *_ in en)
                                                if en else '') + f'; EN saved with up to {nmax} cached teams'
          + (f'; after load: {", ".join(n for n, _ in cbs)}' if cbs else '') + f') @ obj1+{cave:#x}, '
          f'SaveCareerFile call obj1+{save_call:#x}, '
          f'LoadCareerFile call obj1+{load_call:#x}')
    return (cave + len(code) + 3) & ~3, labels['new_career_defaults']


def late(p):
    """End of patch_exe: bind the engine items / after-load routines whose addresses were not known at trailer.patch
    (engine.ITEM_AT / CALL_AT set since, e.g. gplay's RS_STATE)."""
    import engine
    for kind, name, off in INFO.get('late', []):
        at = (engine.ITEM_AT if kind == 'item' else engine.CALL_AT).get(name)
        assert at is not None, f'engine {kind} {name}: no address'
        p.retarget(1, off, at[0], at[1])
        p.put(1, off, struct.pack('<I', at[1]))
    INFO['late'] = []
