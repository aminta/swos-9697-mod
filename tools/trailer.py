"""Extra career data saved as a trailer after the team records of the .CAR file (Roadmap 2).

A career file is the obj2 range careerFileBuffer .. g_numSelectedTeams (95151 bytes, the same in every language)
+ the N cached team records (684 B each) of g_selectedTeams (room for 100). SaveCareerFile writes
fixed + 2 + N*684 bytes (D1 = length, A1 = careerFileBuffer) with WriteFile; LoadCareerFile reads the whole file
into careerFileBuffer with LoadFile (D1 = bytes read) and calls ProcessCareerFile.

Block 'C3' (1.2): the South American lists (Libertadores, Supercopa, CONMEBOL, 3 x 32 B), the Intercontinental pair
(4 B) and the extra cup lists of cafcups.CUPS (4 x 32 B) = 2 + 228 bytes.
save_trailer (replaces `call WriteFile`): writes the block after the team records and adds its size to D1, only if it
fits in g_selectedTeams (N*684 + size <= 68400: the pseudo registers D0..D7 follow).
load_trailer (replaces `call ProcessCareerFile`): every list from the defaults (first season), then from older formats
- 1.0/1.1: 'S2' (3 lists + pair) or 'SA' (3 lists) in someLeaguesTable[1740..1842]; that block (sum 0) is cleared,
  so global numbers 1730..1846 are free again;
- 1.1: trailer 'C1' (3 CAF lists), 1.2 dev: 'C2' (CAF + CONCACAF);
- 'C3': everything.
Then the career mark 'S3' + balance byte at someLeaguesTable[1847..1849] (and leaguesTableCopy): sacups.init_sa
calls new_career_defaults when a season starts without it (InitCareer clears the table = new career).
"""
import re
import struct

import nasmcave
import sacups

MARK, C2, C1, S2, SA = 0x3343, 0x3243, 0x3143, 0x3253, 0x4153   # 'C3' 'C2' 'C1' 'S2' 'SA'
NSA = 4                                   # SA items first: Lib, Sup, CON, Intercontinental pair
OLD_SIZE = 103                            # 1.0/1.1 block in someLeaguesTable (sum 0)
TEAM_SIZE, SELECTED_ROOM = 684, 68400

ASM = '''
save_trailer:
    pushad
    movzx eax, word [NUMSEL]
    imul eax, eax, TEAM_SIZE
    add eax, BLOCK
    cmp eax, ROOM
    ja .skip
    mov edi, [D1]
    add edi, CAREER
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
.skip:
    popad
    jmp WRITEFILE

load_trailer:
    pushad
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
    mov edx, ITEMS
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
    add eax, FIXED                      ; trailer offset in the file
    mov ebx, eax
    lea esi, [eax + CAREER]
    mov edx, ITEMS
    mov ebp, NITEMS
    mov ecx, BLOCK
    cmp word [esi], MARK
    je .check
    mov edx, ITEMS + 8 * NSA            ; 1.1 / 1.2 dev trailers: extra cup lists only
    mov ebp, 4
    mov ecx, 2 + 4 * 32
    cmp word [esi], C2
    je .check
    mov ebp, 3
    mov ecx, 2 + 3 * 32
    cmp word [esi], C1
    jne .done
.check:
    add ecx, ebx
    cmp ecx, [D1]
    ja .done
    add esi, 2
    call items_in
.done:
    call set_mark
    popad
    jmp PROCESS

new_career_defaults:
    pushad
    mov esi, DEFAULTS
    mov edx, ITEMS
    mov ebp, NITEMS
    call items_in
    call set_mark
    popad
    ret

set_mark:                               ; 'S3' + balance: the table still adds up to 0
    mov word [MARK3_AT], MARK3
    mov byte [MARK3_AT + 2], MARK3_BAL
    mov word [MARK3_COPY], MARK3
    mov byte [MARK3_COPY + 2], MARK3_BAL
    ret

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

ITEMS: ITEM_ENTRIES
DEFAULTS: DEFAULT_BYTES
'''


def patch(p, cave, items):
    """items = [(obj1 offset, size)] to save: sacups.SAVE_ITEMS + the extra cup lists. Returns (cave end,
    new_career_defaults offset)."""
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
    assert len(items) == NSA + 4 and [n for _, n in items[:NSA]] == [32, 32, 32, 4]
    block = 2 + sum(n for _, n in items)
    defaults = b''.join(p.get(1, off, n) for off, n in items)
    bal = -(sa.MARK3 & 0xff) - (sa.MARK3 >> 8) & 0xff
    symbols = {'NUMSEL': (2, numsel), 'CAREER': (2, career), 'D1': (2, dreg1), 'WRITEFILE': (1, writefile),
               'PROCESS': (1, process), 'MARK': (0, MARK), 'C2': (0, C2), 'C1': (0, C1), 'S2': (0, S2), 'SA': (0, SA),
               'TEAM_SIZE': (0, TEAM_SIZE), 'ROOM': (0, SELECTED_ROOM), 'BLOCK': (0, block),
               'FIXED': (0, numsel - career + 2), 'NITEMS': (0, len(items)), 'NSA': (0, NSA), 'OLD_SIZE': (0, OLD_SIZE),
               'OLD_SAVED': (2, table + sa.SAVED_GLOBAL), 'MARK3_AT': (2, table + sa.MARK3_GLOBAL),
               'MARK3_COPY': (2, copy + sa.MARK3_GLOBAL), 'MARK3': (0, sa.MARK3), 'MARK3_BAL': (0, bal),
               'DEFAULT_BYTES': (0, 'db ' + ', '.join(str(b) for b in defaults))}
    for k_, (off, n) in enumerate(items):         # obj1 addresses as symbols: nasmcave adds their fixups
        symbols[f'I{k_}'] = (1, off)
    symbols['ITEM_ENTRIES'] = (0, 'dd ' + ', '.join(f'I{k_}, {n}' for k_, (_, n) in enumerate(items)))
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    labels = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.put(1, save_call + 1, struct.pack('<i', labels['save_trailer'] - (save_call + 5)))
    p.put(1, load_call + 1, struct.pack('<i', labels['load_trailer'] - (load_call + 5)))
    print(f'exe: .CAR trailer C3 ({block} B) @ obj1+{cave:#x}, SaveCareerFile call obj1+{save_call:#x}, '
          f'LoadCareerFile call obj1+{load_call:#x}')
    return (cave + len(code) + 3) & ~3, labels['new_career_defaults']
