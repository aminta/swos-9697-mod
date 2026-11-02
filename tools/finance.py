"""4.0.6 (Nicola via Davide): club income that grows with the club - sponsorship / TV at every season start.

The game charges the career club, every match week, its wage bill (each player's wage from his price, cseg_5E345)
plus the running costs, which InitializeNewSeason's cseg_3D204 sets to 3.23 x the wages (x207/6144 x96). Its income
(gate receipts: league place / average player price, at most ~1.05 M a match; the season end's competition bonuses;
a rare random sponsorship) does not grow with the squad, so a big squad loses 10-20 M a season even winning
everything (harness, 2026-27: REAL MADRID -16.9, MAN CITY -18.5, INTER -10.9; original JUVENTUS -3.1).

Here, at every season start (cseg_3D204, right after the running costs are set: `mov [D6B9A], eax`), the club gets
CREDIT (now 1.5 x) its season wage bill (dseg_D6BA2 = the weekly wages x the season's weeks, computed just before) as
sponsorship: added to sensisoftPlcSponsorship (the finance screen's SPONSORSHIP) and newBalance. InitializeNewSeason
runs once a season (a new career's first season too); a save keeps the credited balance, so a loaded save is never
credited again, and an old save gets it at its next season start. Only the career club has finances.
"""
import nasmcave

MUL, DIV = 15, 10                       # the credit = MUL / DIV x the season's wage bill (Davide: 1.5)

CREDIT = r"""
    mov eax, [D6BA2]                    ; the credit in eax: the season's wage bill x MUL / DIV
    imul eax, eax, MUL_
    xor edx, edx
    mov ecx, DIV_
    div ecx
"""                                     # (THE FORMULA: one place; any variant replaces this block, eax = the credit)

ASM = r"""
fi_go:                                  ; replaces `mov [D6B9A], eax` (cseg_3D204: the running costs per match)
    mov [D6B9A], eax
    pushad
""" + CREDIT + r"""
    add [SPONS], eax                    ; SPONSORSHIP
    add [NEWBAL], eax
    popad
    jmp CONT
"""


def find(p):
    """The `mov [D6B9A], eax` site and the variables, from the running costs' `mov bx, 0CFh; mul bx`."""
    d = p.le.obj_bytes(1)
    cf = [i for i in range(len(d)) if d.startswith(bytes.fromhex('66bbcf0066f7e3'), i)]
    assert len(cf) == 1, cf
    site = next(i for i in range(cf[0], cf[0] + 0x200) if d[i] == 0xA3 and d[i + 5:i + 7] == b'\xc7\x05')
    o, b9a = p.target(1, site + 1)
    assert o == 2
    ba2 = [i for i in range(cf[0] - 0x80, cf[0]) if d[i] == 0xA3 and p.target(1, i + 1) == (2, b9a + 8)]
    assert len(ba2) == 1, 'dseg_D6BA2 store'
    return {'site': site, 'D6B9A': b9a, 'D6BA2': b9a + 8, 'SPONS': b9a - 0xA, 'NEWBAL': b9a - 0x32}


def patch(p, at):
    """Code at obj3:at; returns the end."""
    s = find(p)
    d = p.le.obj_bytes(1)
    assert p.get(1, s['site'], 5) == d[s['site']:s['site'] + 5], 'finance site already patched'
    sym = {'D6B9A': (2, s['D6B9A']), 'D6BA2': (2, s['D6BA2']), 'SPONS': (2, s['SPONS']), 'NEWBAL': (2, s['NEWBAL']),
           'CONT': (1, s['site'] + 5), 'MUL_': (0, MUL), 'DIV_': (0, DIV)}
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.remove(1, s['site'] + 1)                           # (the store's offset fixup: now a jmp)
    p.branch(1, s['site'], 0xE9, 3, lab['fi_go'])
    print(f'exe: season-start sponsorship {MUL}/{DIV} x the wage bill: code obj3+{at:#x} ({len(code)} B), '
          f'site obj1+{s["site"]:#x}, newBalance obj2+{s["NEWBAL"]:#x}')
    return at + len(code)
