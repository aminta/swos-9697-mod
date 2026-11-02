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

NE = 16                                  # cups kept: the national cups of the countries with a supercup (the .CAR's
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
.f: cmp ebx, NE_ - 1
    jae .x                              ; (full: dropped; 4.0.6 the last entry is the UEFA Super Cup's state)
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
    db 'CNSTPTR', 0                     ; (the harness: gplay.c CN_ST, 4.0.5 the last-season division name)
    dd CN_ST
    db 'SCTRPTR', 0                     ; (and gplay.c's SC_TRACE)
    dd SC_TRACE
SCW: dw 0                               ; (the cup's winner / finalist words and globals for sc_put)
SCF: dw 0
SCWG: dw 0
SCFG: dw 0
SC_IDS: db IDS_
'''


USC_ASM = '''
usc_snap:                               ; 4.0.6 replaces the season end's `call cseg_9339D` (cseg_91428: the third
    call C9339D                         ; European cup's season end, after cseg_92D55 / 9307A): the three holders
    pushad                              ; into the UEFA Super Cup's state (SC_ST's last entry +3 the season, +6 the
    mov edi, SC_U                       ; words), before the qualifiers clear a holder that qualified through its
    mov al, [SEASONPLAYING]             ; league (cseg_93BCE); the game does not save them
    mov [edi + 3], al
    mov ax, [HOLD_CC]
    mov [edi + 6], ax
    mov ax, [HOLD_CWC]
    mov [edi + 8], ax
    mov ax, [HOLD_UEFA]
    mov [edi + 10], ax
    popad
    ret

'''


def usc_site(p):
    """4.0.6: cseg_91428's three European season ends (`call cseg_92D55 / 9307A / 9339D`, then `mov careerFileBuffer,
    0` and `mov ax, isNationalSelector`): the third call's site (obj1) and its target in the original exe."""
    import re as _re
    d1 = p.le.obj_bytes(1)
    m = []
    for x in _re.finditer(rb'\xe8.{4}\xe8.{4}\xe8.{4}(\xc6\x05.{4}\x00|\x66\xc7\x05.{4}\x00\x00)\x66\xa1', d1, _re.S):
        t = [x.start() + 5 * i + 5 + struct.unpack_from('<i', d1, x.start() + 5 * i + 1)[0] for i in range(3)]
        if t[1] - t[0] == 0x325 and t[2] - t[1] == 0x323:      # (cseg_92D55 -> 9307A -> 9339D, the same in every language)
            m.append((x.start() + 10, t[2]))
    assert len(m) == 1, m
    return m[0]


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
        'title0': 7, 'title1': 8,   # (gplay.c SCR_*; title0 / 1: last season's stage-title winners, 'titles' keys)
        'uefa_cl': 9, 'uefa_el': 10, 'uefa_ecl': 11}   # (4.0.6: the game's UEFA holders, HOLD_CC / CWC / UEFA)
UEFA_FILE = 0xFF                         # (4.0.6: the UEFA Super Cup's entry - world-level, no country's league file)
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
    where = {}                                       # (4.0.6: pack suffix -> club key -> team word, the UEFA entry's)
    for pk in mkseason.packs():
        pid = str(pk.meta.get('id', ''))
        if pid.startswith('world-2026-27-'):
            where[pid.split('-')[-1]] = {k: v[0] | v[1] << 8 for k, v in pk.where.items()}
    for pk in mkseason.packs():
        pid = str(pk.meta.get('id', ''))
        c = pid.split('-')[-1]
        if not pid.startswith('world-2026-27-') or c not in spec:
            continue
        d = spec[c]
        cup = next((x for x in pk.comps if x.get('key') == 'cup' and x.get('id')), None)
        assert cup or not {'cup_winner', 'cup_finalist'} & set(d['rule']), f'supercup {c}: no national cup'
        pos = pk.league.get('ko_playoffs') or []          # (title0 / 1: the stage-title play-offs' indices)
        keys = [p_.get('key') for p_ in pos if isinstance(p_, dict)] if isinstance(pos, list) else []
        if any(k not in keys for k in d.get('titles', [])):   # (an older data snapshot without those play-offs: no
            print(f'supercup {c}: play-offs {d["titles"]} not in the pack: left out')   # supercup there)
            continue
        tix = [keys.index(k) for k in d.get('titles', [])] + [0, 0]
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
        bn = pk.meta.get('button_names') or {}
        country = (bn.get(lang) or pk.meta.get('button') or '').upper()
        out.append(_entry(d, c, lang, name_off, lf, int(cup['id'], 16) if cup else 0, rules, ents, w1, w2, n, tix, country))
    if not out:
        return None
    d = spec.get('uefa')                             # 4.0.6 the UEFA Super Cup: the last entry (a world's European clubs)
    if d and {'eng', 'fra'} <= set(where):
        n = len(d['rule'])
        assert n == 2 and len(d['first_entrants']) == 2
        rules = [RULE[d['rule'][0]], RULE[d['rule'][1]] | RULE[d['if_double']] << 4, 0, 0]
        ents = [where[k.split(':')[0]][k.split(':')[1]] for k in d['first_entrants']] + [0, 0]
        w1 = split.week_of(d['date'])
        out.append(_entry(d, 'uefa', lang, name_off, UEFA_FILE, 0, rules, ents, w1, w1, 2, [0, 0]))
    assert len(out) <= 32
    return list(bytes([len(out)]) + b''.join(out))


def _entry(d, c, lang, name_off, lf, cid, rules, ents, w1, w2, n, tix, country=''):
    """One GP_SCT entry (SC_E = 36 bytes). country: the pack's button name in lang (the slot's title '<country>
    <long>': the long name fitted to TITLE_MAX and VISUAL. COMPETIZ.'s button, complist's rule - Davide 03/11)."""
    import complist
    import gplay                                    # (the season record's line: REGISTRO GESTIONE's column)
    import rnames
    e = bytes([lf, cid, d.get('from_season', 1) | (0x80 if d.get('early') else 0), w1, d.get('legs', 1), LEVEL[d['level']], n, w2])
    e += bytes(rules) + struct.pack('<4H', *ents)
    nm = d['names'].get(lang) or d['names']['en']
    complist.cal_label(nm[1], f'supercup {c} {lang}')   # (the calendar's label: <= 70 px, font chars only)
    lo = nm[0]
    if country:
        complist.LANG[:] = [lang]
        lo = complist._fit(country, nm[0], nm[1])
        t = f'{country} {lo}'
        assert len(t) <= complist.TITLE_MAX and complist.px(t) <= complist.VC_PX and all(ch in complist.FONT for ch in t), \
            ('supercup title', c, lang, t, len(t), complist.px(t))
    e += struct.pack('<II', name_off(lo.encode('latin-1')), name_off(nm[1].encode('latin-1')))
    e += bytes([rnames.KEYS['SF'], rnames.KEYS['F'], tix[0], tix[1]])
    rec = nm[0] if complist.px(nm[0]) <= gplay.REC_PX else nm[1]
    e += struct.pack('<I', name_off(rec.encode('latin-1')))
    assert len(e) == 36
    return e


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
    assert 0 < len(ids) <= NE - 1, ids                  # (4.0.6: the last entry = the UEFA Super Cup's state)
    at = (at + 15) & ~15
    import gplay
    sym = {'SC_ST': gplay.LABELS['SC_ST'], 'SC_TRACE': gplay.LABELS['SC_TRACE'], 'CN_ST': gplay.LABELS['CN_ST'],   # (gplay.c's)
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


def patch_usc(p, at):
    """4.0.6 usc_snap at obj3:at (the UEFA Super Cup's holders at the season end), the call site chained; returns the
    end. After patch() (SC_ST's address)."""
    import careerworld
    import gplay
    import nasmcave
    usite, _ = usc_site(p)
    cur = bytes(p.get(1, usite, 5))                 # (chained: a hook already there stays, ours calls it)
    assert cur[0] == 0xE8, cur
    q = careerworld._qual_sites(p.le.obj_bytes(1), p)
    so, sa = gplay.LABELS['SC_ST']
    tgt = p.rel_target(1, usite + 1) or (1, usite + 5 + struct.unpack('<i', cur[1:])[0])   # (a cross-object hook: its fixup)
    sym = {'C9339D': tgt, 'SEASONPLAYING': (2, careerworld.SITES['season']),
           'HOLD_CC': q['HOLD_CC'], 'HOLD_CWC': q['HOLD_CWC'], 'HOLD_UEFA': q['HOLD_UEFA'],
           'SC_U': (so, sa + 12 + 12 * (NE - 1))}
    code, fix, rel = nasmcave.assemble_obj(USC_ASM, at, sym, 3)
    lab = nasmcave.labels(USC_ASM, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, usite, 0xE8, 3, lab['usc_snap'], 5)
    print(f"exe: supercup usc_snap obj3+{at:#x} ({len(code)} B), the third European season end's call obj1+{usite:#x}")
    return at + len(code)
