"""National supercups of World 2026-27 (4.0.5; internal/handoff/supercups.md): step 1, the entrants' source.

At the season end every cup of every country is decided in cseg_91857 (the career's own played, the others
simulated), each through cseg_928CC: after cseg_2ACAE it copies the cup's final order (DIY+2CDh place bytes ->
DIY+24Dh team words) as records into dseg_181FCE (records of 2ACh bytes: +2 the global number) and the team words
into dseg_180727 (winner, finalist, ...). A country with a league cup runs it twice, so dseg_180727 holds only the last
cup when the qualifiers read it (cseg_93974). sc_cup replaces both `call cseg_928CC`: the same call, then the cup's
winner and finalist go into SC_ST by (team file of the winner = the country, the word's low byte; contest id = DIY+2Dh):

    SC_ST (gplay.c): dw magic 'SC', db count, db the last season handled (sc_step_c); NE x (db file, db contest id, db 0, db 0,
                                              dw winner team, dw winner global, dw finalist team, dw finalist global)

SC_ST is saved with the career (engine item 'SC'; an older save loads it zeroed: no entrants known yet). The
supercups themselves (gplay's slot 4, at their real weeks) read it next season (step 2)."""
import json
import os
import re
import struct

NE = 32                                  # cups kept: the national cups of the countries with a supercup (the .CAR's
                                         # engine block has little room: trailer SEL_ROOM)
COUNTRIES = ('ita', 'esp', 'eng', 'ger', 'fra', 'tur', 'ksa', 'bra', 'mex')   # (pack id suffixes; data: step 2)
SC_SIZE = 12 + 12 * NE                    # (gplay.c SC_H + 12 x SC_NE)
MAGIC = 0x4353                           # 'SC'
LABELS = {}

ASM = '''
sc_cup:                                 ; replaces `call cseg_928CC` (season end, a cup decided): the same, then its
    call C928CC                         ; winner / finalist into SC_ST
    pushad
    mov ax, [TW]
    mov [SCW], ax
    mov ax, [TW + 2]
    mov [SCF], ax
    mov ax, [REC + 2]
    mov [SCWG], ax
    mov ax, [REC + 2ACh + 2]
    mov [SCFG], ax
    jmp sc_put
sc_cup2:                                ; 4.0.5 BRA: replaces `call cseg_92A63` (a country's cup 2 at the season end,
    call C92A63                         ; cseg_91AD0 - Brazil's COPA DO BRASIL, its cup 1 being the state contest):
    pushad                              ; the winner / finalist from the DIY's final order (cseg_2ACAE: +2CDh the
    movzx ebx, byte [DIY + 2CDh]        ; winners, then the losers), its record's global (dseg_1827D2)
    mov ax, [DIY + 24Dh + ebx * 2]
    mov [SCW], ax
    movzx ebx, byte [DIY + 2CEh]
    mov ax, [DIY + 24Dh + ebx * 2]
    mov [SCF], ax
    mov ax, [REC2 + 2]
    mov [SCWG], ax
    mov word [SCFG], 0
sc_put:
    movzx eax, byte [DIY + 2Dh]         ; the contest id
    mov edi, SC_IDS                     ; only the cups of SC_IDS (the countries with a supercup)
    mov ecx, NE_
.i: cmp [edi], al
    je .in
    inc edi
    loop .i
    jmp .x
.in:
    movzx ecx, byte [SCW]               ; the country: the winner's team file (the word's low byte)
    xor ebx, ebx
.f: cmp ebx, NE_
    jae .x                              ; (full: dropped)
    imul edi, ebx, 12
    add edi, SC_ST + 12
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
    mov ax, [SCW]
    mov [edi + 4], ax
    mov ax, [SCWG]
    mov [edi + 6], ax
    mov ax, [SCF]
    mov [edi + 8], ax
    mov ax, [SCFG]
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
    db 'SCTRPTR', 0                     ; (and gplay.c's SC_TRACE)
    dd SC_TRACE
SCW: dw 0                               ; (the cup's winner / finalist words and globals for sc_put)
SCF: dw 0
SCWG: dw 0
SCFG: dw 0
SC_IDS: db IDS_
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


def sites2(p, tw):
    """4.0.5 (cseg_92A63, its two call sites in cseg_91AD0, dseg_1827D2): the cup-2 recorder - found by its
    `mov dseg_18072D, ax` (dseg_180727 + 6) and the routine with two calls just before it."""
    d1 = bytes(p.le.obj_bytes(1))
    m = [x.start() for x in re.finditer(b'\x66\xa3' + re.escape(struct.pack('<I', tw + 6)), d1)]
    assert len(m) == 1, [hex(x) for x in m]
    tg = {}
    for i in range(len(d1) - 5):
        if d1[i] == 0xe8:
            tg.setdefault(i + 5 + struct.unpack_from('<i', d1, i + 1)[0], []).append(i)
    st = [t for t in range(m[0] - 0x400, m[0]) if len(tg.get(t, [])) == 2]
    assert st, 'cseg_92A63 start'
    c = st[-1]
    r2 = [x.start() for x in re.finditer(b'\xc7\x05.{4}(.{4})', d1[m[0]:m[0] + 0x80], re.S)]
    assert r2, 'dseg_1827D2'
    rec2 = struct.unpack_from('<I', d1, m[0] + r2[0] + 6)[0]
    return c, tg[c], rec2


RULE = {'champion': 1, 'second': 2, 'cup_winner': 3, 'cup_finalist': 4, 'third': 5, 'fourth': 6,
        'title0': 7, 'title1': 8}   # (gplay.c SCR_*; title0 / 1: last season's stage-title winners, 'titles' keys)
LEVEL = {'pens': 3, 'et_pens': 1}                                        # (gplay.c LV_PENS / LV_ET_PENS)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supercups2627.json')


def table(lang, name_off):
    """gplay.c GP_SCT's bytes (db count; per country SC_E = 36 bytes) for the World 2026-27 packs of the build, or
    None when the build has none of them. name_off(text) -> the name's offset (gplay: _sadd - STR_BASE)."""
    import mkseason
    import rnames
    import split
    spec = {k: v for k, v in json.load(open(DATA)).items() if not k.startswith('_')}
    out = []
    for pk in mkseason.packs():
        pid = str(pk.meta.get('id', ''))
        c = pid.split('-')[-1]
        if not pid.startswith('world-2026-27-') or c not in spec:
            continue
        d = spec[c]
        cup = next((x for x in pk.comps if x.get('key') == 'cup' and x.get('id')), None)
        assert cup or not {'cup_winner', 'cup_finalist'} & set(d['rule']), f'supercup {c}: no national cup'
        pos = pk.league.get('ko_playoffs') or []          # (title0 / 1: the stage-title play-offs' indices)
        tix = [[p_.get('key') for p_ in pos].index(k) for k in d.get('titles', [])] + [0, 0]
        assert all(0 <= x < 256 for x in tix) and (len(d.get('titles', [])) == 2 or not {'title0', 'title1'} & set(d['rule'])), c
        lf = pk.files[pk.league['clubs']][0]
        word = lambda k: pk.where[k][0] | pk.where[k][1] << 8
        n = len(d['rule'])
        assert n in (2, 4) and len(d['first_entrants']) == n, c
        fb = d.get('if_double')
        fb = fb if isinstance(fb, list) else [None] + [fb] * (n - 1)
        rules = [RULE[r] | (RULE[f] << 4 if f else 0) for r, f in zip(d['rule'], fb)] + [0] * (4 - n)
        ents = [word(k) for k in d['first_entrants']] + [0] * (4 - n)
        w1 = split.week_of(d['date'])
        w2 = split.week_of(d['final_date']) if n == 4 else w1
        e = bytes([lf, int(cup['id'], 16) if cup else 0, d.get('from_season', 1), w1, d.get('legs', 1), LEVEL[d['level']], n, w2])
        e += bytes(rules) + struct.pack('<4H', *ents)
        nm = d['names'].get(lang) or d['names']['en']
        import complist
        complist.cal_label(nm[1], f'supercup {c} {lang}')   # (the calendar's label: <= 70 px, font chars only)
        e += struct.pack('<II', name_off(nm[0].encode('latin-1')), name_off(nm[1].encode('latin-1')))
        e += bytes([rnames.KEYS['SF'], rnames.KEYS['F'], tix[0], tix[1]])
        import gplay                                # (the season record's line: REGISTRO GESTIONE's column)
        rec = nm[0] if complist.px(nm[0]) <= gplay.REC_PX else nm[1]
        e += struct.pack('<I', name_off(rec.encode('latin-1')))
        assert len(e) == 36
        out.append(e)
    if not out:
        return None
    assert len(out) <= 32
    return list(bytes([len(out)]) + b''.join(out))


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
    c92a63, calls2, rec2 = sites2(p, tw)
    ids = cup_ids()
    assert 0 < len(ids) <= NE, ids
    at = (at + 15) & ~15
    import gplay
    sym = {'SC_ST': gplay.LABELS['SC_ST'], 'SC_TRACE': gplay.LABELS['SC_TRACE'],   # (gplay.c's)
           'C928CC': (1, c928cc), 'C92A63': (1, c92a63), 'REC2': (2, rec2), 'REC': (2, rec), 'TW': (2, tw), 'DIY': (2, diy), 'NE_': (0, NE),
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
    for c in calls2:
        p.put(1, c, b'\xE8' + struct.pack('<i', lab['sc_cup2'] - (c + 5)))
    LABELS.update(sc_cup=lab['sc_cup'], SC_ST=gplay.LABELS['SC_ST'])
    engine.ITEM_AT['SC'] = gplay.LABELS['SC_ST']
    print(f"exe: supercup sc_cup obj1+{lab['sc_cup']:#x} (cseg_928CC obj1+{c928cc:#x}, calls "
          + ' '.join(f'{c:#x}' for c in calls) + f"; cseg_92A63 obj1+{c92a63:#x}, calls "
          + ' '.join(f'{c:#x}' for c in calls2) + f", dseg_1827D2 {rec2:#x}) SC_ST {gplay.LABELS['SC_ST']}")
    return at + len(code)
