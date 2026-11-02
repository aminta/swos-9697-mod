"""4.0.6 (Nicola via Davide): club income that grows with the club, paid with every match charge; the gate wrap fixed.

The original game charges the career club, at every match charge (cseg_94DB1, about 72 a season), its wage bill
(dseg_D6B9E: each player's wage from his price, cseg_5E345) and the running costs (dseg_D6B9A, set at the season start
by cseg_3D204 to 3.23 x the wages): ~4.2 x the wages in all. Its income (gate receipts: league place / average player
price; the season end's competition bonuses; a rare random sponsorship) does not grow with the squad, so a big squad
lost 10-20 M a season even winning everything (harness, World 2026-27 on 4.0.5: REAL MADRID -16.9, MAN CITY -18.5,
INTER -10.9; BRENTFORD -3.1; original JUVENTUS -3.1).

Here every match charge also pays the club its share of the season's TV / commercial income:
    per charge = BASE[level] / charges + WAGE_MUL / WAGE_DIV x the wage bill per charge
i.e. BASE[level] + 1.1 x the season's wage bill a season (dseg_D6CA2 = the season's charges), added to
sensisoftPlcSponsorship (the finance screen's SPONSORSHIP, reset at every season start) and newBalance. The level is
the career club's division (dseg_D6CDC) counted as the league's levels: a level of parallel groups (Serie C girone
A-C, Serie D girone A-I, ...: menulevels' tables) is one level; a league without groups: division + 1. Levels past
the table: its last value. Nothing is saved: an old save gets it from its next match charge.

The gate receipts (cseg_3C4CE) were cut to 16 bits before x16 (`and D7, 0FFFFh`): a gate over 65535 x 16 wrapped to
a few pounds. Saturated at 0FFFFh now.
"""
import re
import struct

import nasmcave

BASE = (3000000, 1200000, 500000, 200000)   # a season's base income by level 1, 2, 3, 4 (deeper: the last)
WAGE_MUL, WAGE_DIV = 11, 10                 # + 1.1 x the season's wage bill
MAXDIV = 32                                 # (levels table: divisions per league)

ASM = r"""
fi_charge:                              ; replaces `add word [C1750DA], 1` in cseg_94DB1's charge loop
    add word [C1750DA], 1
    pushad
    movzx ebx, word [D6CDC]             ; the club's division -> its level (0-based) in ebx
    mov esi, [D8CAA]                    ; the career league's struct
    mov edi, FI_LV
.lv:
    mov eax, [edi]
    test eax, eax
    jz .plain
    cmp eax, esi
    je .tab
    add edi, 4 + MAXDIV_
    jmp .lv
.tab:
    cmp ebx, MAXDIV_
    jae .plain
    movzx ebx, byte [edi + 4 + ebx]
    jmp .lvok
.plain:
.lvok:
    cmp ebx, NBASE_ - 1
    jbe .b
    mov ebx, NBASE_ - 1
.b:
    mov eax, [FI_BASE + ebx * 4]        ; the season's base / its charges
    movzx ecx, word [D6CA2]
    test ecx, ecx
    jz .nob
    xor edx, edx
    div ecx
    jmp .w
.nob:
    xor eax, eax
.w:
    mov ecx, eax
    mov eax, [D6B9E]                    ; + 1.1 x the wage bill per charge
    imul eax, eax, WAGE_MUL_
    xor edx, edx
    mov ebx, WAGE_DIV_
    div ebx
    add eax, ecx
    add [SPONS], eax                    ; SPONSORSHIP
    add [NEWBAL], eax
    popad
    jmp CHARGE_BACK

fi_gate:                                ; replaces `and dword [D7], 0FFFFh` (cseg_3C4CE's gate receipts, a jump target)
    cmp dword [D7], 0FFFFh
    jle .and
    mov dword [D7], 0FFFFh              ; saturated, not wrapped
.and:
    and dword [D7], 0FFFFh
    jmp GATE_BACK

FI_BASE: BASE_DD
FI_LV: LV_DB
    dd 0
"""


def find(p):
    """The charge loop's counter add, the gate mask and the variables (located from the code, every language)."""
    d = p.le.obj_bytes(1)
    cf = [i for i in range(len(d)) if d.startswith(bytes.fromhex('66bbcf0066f7e3'), i)]
    assert len(cf) == 1, cf
    st = next(i for i in range(cf[0], cf[0] + 0x200) if d[i] == 0xA3 and d[i + 5:i + 7] == b'\xc7\x05')
    o, b9a = p.target(1, st + 1)                        # mov [D6B9A], eax (the running costs per charge)
    assert o == 2
    ca2 = [i for i in range(cf[0], cf[0] + 0x100) if d[i:i + 3] == b'\x66\xf7\x35']
    assert len(ca2) == 1, 'div word [D6CA2]'
    key = b'\xa1' + struct.pack('<I', b9a + 4)          # mov eax, [D6B9E]: the cost formula's, then the charge loop's
    hits = [m.start() for m in re.finditer(re.escape(key), d)]
    assert len(hits) == 2, [hex(x) for x in hits]
    loop = hits[1]
    cnt = [i for i in range(loop, loop + 0x80) if d[i:i + 3] == b'\x66\x83\x05' and d[i + 7:i + 11] == b'\x01\x66\xff\x0d']
    assert len(cnt) == 1, 'the charge loop counter'
    g = [m.start() for m in re.finditer(rb'\x81\x25(....)\xff\xff\x00\x00\xc1\x25\1\x04\xa1\1\x01\x05', d, re.S)]
    assert len(g) == 1, g
    import gplay
    return {'charge': cnt[0], 'C1750DA': p.target(1, cnt[0] + 3), 'gate': g[0], 'D7': p.target(1, g[0] + 2),
            'D6B9E': (2, b9a + 4), 'D6CA2': p.target(1, ca2[0] + 3), 'SPONS': (2, b9a - 0xA), 'NEWBAL': (2, b9a - 0x32),
            'D6CDC': (2, gplay._cardiv(p))}


def levels(lang):
    """[(league struct (obj, off), [level of division 0, 1, ...])] of the leagues with levels of groups."""
    import menulevels
    out = []
    for at, lv in menulevels.tables(lang):
        row = []
        for k, (first, count, _) in enumerate(lv):
            assert first == len(row), (at, lv)
            row += [k] * count
        assert len(row) <= MAXDIV, (at, len(row))
        out.append((at, row))
    return out


def patch(p, at, lang):
    """Code + tables at obj3:at; returns the end."""
    import sacups
    s = find(p)
    d = p.le.obj_bytes(1)
    for k, n in (('charge', 8), ('gate', 10)):
        assert p.get(1, s[k], n) == d[s[k]:s[k] + n], ('finance site already patched', k)
    lv = levels(lang)
    rows = []
    sym = {k: s[k] for k in ('C1750DA', 'D7', 'D6B9E', 'D6CA2', 'SPONS', 'NEWBAL', 'D6CDC')}
    for j, (lat, row) in enumerate(lv):
        sym[f'LV{j}'] = lat
        rows.append(f'dd LV{j}')
        rows.append('db ' + ', '.join(str(x) for x in row + [row[-1]] * (MAXDIV - len(row))))
    sym.update({'D8CAA': (2, sacups.COMP_SLOTS[0]), 'CHARGE_BACK': (1, s['charge'] + 8), 'GATE_BACK': (1, s['gate'] + 10),
                'MAXDIV_': (0, MAXDIV), 'NBASE_': (0, len(BASE)), 'WAGE_MUL_': (0, WAGE_MUL), 'WAGE_DIV_': (0, WAGE_DIV)})
    src = nasmcave.sub(nasmcave.sub(ASM, 'BASE_DD', 'dd ' + ', '.join(str(b) for b in BASE)),
                       'LV_DB', '\n    '.join(rows))
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['charge'] + 3)                         # (the overwritten instructions' fixups)
    p.branch(1, s['charge'], 0xE9, 3, lab['fi_charge'], 8)
    p.remove(1, s['gate'] + 2)
    p.branch(1, s['gate'], 0xE9, 3, lab['fi_gate'], 10)
    print(f'exe: club income per match charge (base {[b // 1000 for b in BASE]} k by level + {WAGE_MUL}/{WAGE_DIV} x the '
          f'wages; {len(lv)} leagues with levels of groups) + gate saturated: code obj3+{at:#x} ({len(code)} B), sites '
          f'obj1+{s["charge"]:#x} / +{s["gate"]:#x}')
    return at + len(code)
