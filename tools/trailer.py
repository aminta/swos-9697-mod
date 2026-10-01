"""Extra career data saved as a trailer after the team records of the .CAR file (Roadmap 2).

A career file is the obj2 range careerFileBuffer .. g_numSelectedTeams (95151 bytes, the same in every language)
+ the N cached team records (684 B each) of g_selectedTeams (room for 100). SaveCareerFile writes
fixed + 2 + N*684 bytes (D1 = length, A1 = careerFileBuffer) with WriteFile; LoadCareerFile reads the whole file
into careerFileBuffer with LoadFile (D1 = bytes read) and calls ProcessCareerFile.

save_trailer (replaces `call WriteFile`): copies [MARK][lists] right after the team records and adds its size to
D1, only if it fits in g_selectedTeams (N*684 + size <= 68400: after it come the pseudo registers D0..D7).
load_trailer (replaces `call ProcessCareerFile`): if the file is long enough and has the mark, the lists come from
it, otherwise (saves without trailer) the defaults (first-season lists). new_career_defaults is called by
sacups' init_sa when a new career starts.
Block: 'C2' + the extra cup lists in cafcups.CUPS order (CAF x3, CONCACAF; 4 x 32 B). 1.1 saves have 'C1' + the
three CAF lists: those are read and the newer lists start from the defaults.
"""
import re
import struct

import nasmcave
import sacups

MARK = 0x3243                    # 'C2': CAF lists + CONCACAF (1.2)
OLD_MARK, OLD_LISTS = 0x3143, 3   # 'C1' (1.1): the three CAF lists
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
    mov edx, LISTS
.next:
    mov esi, [edx]
    mov ecx, 32
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    add edx, 4
    cmp edx, LISTS_END
    jne .next
    add dword [D1], BLOCK
.skip:
    popad
    jmp WRITEFILE

load_trailer:
    pushad
    movzx eax, word [NUMSEL]
    imul eax, eax, TEAM_SIZE
    add eax, FIXED
    mov esi, eax
    add eax, 2                          ; at least a mark
    cmp eax, [D1]
    ja .defaults
    add esi, CAREER
    mov ebp, NLISTS
    cmp word [esi], MARK
    jne .old
    mov eax, esi
    sub eax, CAREER
    add eax, BLOCK
    cmp eax, [D1]
    jbe .file
    jmp .defaults
.old:
    mov ebp, OLD_LISTS
    cmp word [esi], OLD_MARK            ; 1.1 save: its CAF lists, the others from the defaults
    jne .defaults
    mov eax, esi
    sub eax, CAREER
    add eax, OLD_BLOCK
    cmp eax, [D1]
    ja .defaults
.file:
    push esi
    mov esi, DEFAULTS
    call lists_in
    pop esi
    add esi, 2
    mov ecx, ebp
    call lists_n
    popad
    jmp PROCESS
.defaults:
    mov esi, DEFAULTS
    call lists_in
    popad
    jmp PROCESS

new_career_defaults:
    pushad
    mov esi, DEFAULTS
    call lists_in
    popad
    ret

lists_in:                       ; esi -> all the lists, 32 B each
    mov ecx, NLISTS
lists_n:                        ; esi -> the first ecx lists
    mov edx, LISTS
.next:
    push ecx
    mov edi, [edx]
    mov ecx, 32
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    add edx, 4
    pop ecx
    dec ecx
    jnz .next
    ret

LISTS: LIST_PTRS
LISTS_END:
DEFAULTS: DEFAULT_BYTES
'''


def patch(p, cave, lists):
    """lists = obj1 offsets of the 32-byte team lists to save. Returns (cave end, new_career_defaults offset)."""
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

    defaults = b''.join(p.get(1, off, 32) for off in lists)
    symbols = {'NUMSEL': (2, numsel), 'CAREER': (2, career), 'D1': (2, dreg1), 'WRITEFILE': (1, writefile),
               'PROCESS': (1, process), 'MARK': (0, MARK), 'TEAM_SIZE': (0, TEAM_SIZE), 'ROOM': (0, SELECTED_ROOM),
               'BLOCK': (0, 2 + 32 * len(lists)), 'FIXED': (0, numsel - career + 2), 'NLISTS': (0, len(lists)),
               'OLD_MARK': (0, OLD_MARK), 'OLD_LISTS': (0, OLD_LISTS), 'OLD_BLOCK': (0, 2 + 32 * OLD_LISTS),
               'DEFAULT_BYTES': (0, 'db ' + ', '.join(str(b) for b in defaults))}
    # list pointers are obj1 addresses: give them as symbols so nasmcave adds their fixups
    for k_, off in enumerate(lists):
        symbols[f'L{k_}'] = (1, off)
    symbols['LIST_PTRS'] = (0, 'dd ' + ', '.join(f'L{k_}' for k_ in range(len(lists))))
    code, fix = nasmcave.assemble(ASM, cave, symbols)
    labels = nasmcave.labels(ASM, cave, symbols)
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    p.put(1, save_call + 1, struct.pack('<i', labels['save_trailer'] - (save_call + 5)))
    p.put(1, load_call + 1, struct.pack('<i', labels['load_trailer'] - (load_call + 5)))
    print(f'exe: .CAR trailer ({2 + 32 * len(lists)} B) @ obj1+{cave:#x}, SaveCareerFile call obj1+{save_call:#x}, '
          f'LoadCareerFile call obj1+{load_call:#x}')
    return (cave + len(code) + 3) & ~3, labels['new_career_defaults']
