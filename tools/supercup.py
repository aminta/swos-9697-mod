"""National supercups of World 2026-27 (4.0.5; internal/handoff/supercups.md): step 1, the entrants' source.

At the season end every cup of every country is decided in cseg_91857 (the career's own played, the others
simulated), each through cseg_928CC: after cseg_2ACAE it copies the cup's final order (DIY+2CDh place bytes ->
DIY+24Dh team words) as records into dseg_181FCE (records of 2ACh bytes: +2 the global number) and the team words
into dseg_180727 (winner, finalist, ...). A country with a league cup runs it twice, so dseg_180727 holds only the last
cup when the qualifiers read it (cseg_93974). sc_cup replaces both `call cseg_928CC`: the same call, then the cup's
winner and finalist go into SC_ST by (team file of the winner = the country, the word's low byte; contest id = DIY+2Dh):

    SC_ST: dw magic 'SC', db count, db 0; NE x (db file, db contest id, db 0, db 0,
                                              dw winner team, dw winner global, dw finalist team, dw finalist global)

SC_ST is saved with the career (engine item 'SC'; an older save loads it zeroed: no entrants known yet). The
supercups themselves (gplay's slot 4, at their real weeks) read it next season (step 2)."""
import re
import struct

NE = 32                                  # cups kept: the national cups of the countries with a supercup (the .CAR's
                                         # engine block has little room: trailer SEL_ROOM)
COUNTRIES = ('ita', 'esp', 'eng', 'ger', 'fra', 'tur', 'ksa', 'bra', 'mex')   # (pack id suffixes; data: step 2)
SC_SIZE = 4 + 12 * NE
MAGIC = 0x4353                           # 'SC'
LABELS = {}

ASM = '''
sc_cup:                                 ; replaces `call cseg_928CC` (season end, a cup decided): the same, then its
    call C928CC                         ; winner / finalist into SC_ST
    pushad
    movzx eax, byte [DIY + 2Dh]         ; the contest id
    mov edi, SC_IDS                     ; only the cups of SC_IDS (the countries with a supercup)
    mov ecx, NE_
.i: cmp [edi], al
    je .in
    inc edi
    loop .i
    jmp .x
.in:
    movzx ecx, byte [TW]                ; the country: the winner's team file (the word's low byte)
    xor ebx, ebx
.f: cmp ebx, NE_
    jae .x                              ; (full: dropped)
    imul edi, ebx, 12
    add edi, SC_ST + 4
    cmp byte [edi + 1], 0
    je .put                             ; (a free entry)
    cmp [edi], cl
    jne .n
    cmp [edi + 1], al
    je .put
.n: inc ebx
    jmp .f
.put:
    mov [edi], cl
    mov [edi + 1], al
    mov ax, [TW]
    mov [edi + 4], ax
    mov ax, [REC + 2]
    mov [edi + 6], ax
    mov ax, [TW + 2]
    mov [edi + 8], ax
    mov ax, [REC + 2ACh + 2]
    mov [edi + 10], ax
    mov word [SC_ST], MAGIC_
    lea eax, [ebx + 1]
    cmp al, [SC_ST + 2]
    jbe .x
    mov [SC_ST + 2], al
.x: popad
    ret

    db 'SCSTPTR', 0                     ; (the harness: SC_ST's address)
    dd SC_ST
SC_IDS: db IDS_
    align 4
SC_ST: times SC_SIZE_ db 0
'''


def sites(p):
    """(cseg_928CC, its two call sites, dseg_181FCE, dseg_180727, the DIY start) of this exe."""
    import careerworld
    import lib97
    d1 = p.le.obj_bytes(1)
    q = careerworld._qual_sites(d1, p)
    rec = q['CUPREC'][1] + 0x2AC                    # dseg_181FCE (obj2)
    pk = lambda x: re.escape(struct.pack('<I', x))
    import sacups
    r = sacups.regs(d1)
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(r['A0'] + 4) + pk(rec) + rb'\xc7\x05' + pk(r['A0'] + 12) + b'(.{4})',
                                        d1, re.S)]
    assert len(m) == 1, m
    tw = struct.unpack_from('<I', d1, m[0] + 16)[0]  # dseg_180727 (mov A3, offset ...)
    starts = [t for t in range(m[0] - 0x100, m[0]) if d1[t:t + 2] == b'\xff\x35' and
              d1[t + 2:t + 6] == struct.pack('<I', r['D7'] - 28)]   # (push D0: the routine's first instruction)
    assert starts, 'cseg_928CC start'
    c928cc = starts[0]
    calls = [i for i in range(len(d1) - 5) if d1[i] == 0xe8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == c928cc]
    assert len(calls) == 2, [hex(x) for x in calls]
    return c928cc, calls, rec, tw, lib97._sites(p)[3] + 0x41F


def cup_ids():
    """The national cups' contest ids ('cup' key) of the World 2026-27 packs of COUNTRIES."""
    import mkseason
    out = []
    for pk in mkseason.packs():
        pid = str(pk.meta.get('id', ''))
        if pid.startswith('world-2026-27-') and pid.split('-')[-1] in COUNTRIES:
            c = next((c for c in pk.comps if c.get('key') == 'cup' and c.get('id')), None)
            if c:
                out.append(int(c['id'], 16))
    return out


def patch(p, at):
    """Code + SC_ST at obj1:at; returns the end."""
    import nasmcave
    import engine
    c928cc, calls, rec, tw, diy = sites(p)
    ids = cup_ids()
    assert 0 < len(ids) <= NE, ids
    at = (at + 15) & ~15
    sym = {'C928CC': (1, c928cc), 'REC': (2, rec), 'TW': (2, tw), 'DIY': (2, diy), 'NE_': (0, NE),
           'SC_SIZE_': (0, SC_SIZE), 'MAGIC_': (0, MAGIC),
           'IDS_': (0, ', '.join(str(x) for x in ids + [0] * (NE - len(ids))))}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for c in calls:                                  # (relative calls: no fixup)
        p.put(1, c, b'\xE8' + struct.pack('<i', lab['sc_cup'] - (c + 5)))
    LABELS.update(sc_cup=lab['sc_cup'], SC_ST=lab['SC_ST'])
    engine.ITEM_AT['SC'] = (1, lab['SC_ST'])
    print(f"exe: supercup sc_cup obj1+{lab['sc_cup']:#x} (cseg_928CC obj1+{c928cc:#x}, calls "
          + ' '.join(f'{c:#x}' for c in calls) + f") SC_ST obj1+{lab['SC_ST']:#x}")
    return at + len(code)
