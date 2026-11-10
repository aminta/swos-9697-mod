"""The squad lists' number column 1 px wider (4.0.5, Marco): on the team screen (playMatchMenu) and the tactics editor
(editTacticsMenu) the shirt number is a centred type-12 entry at x 13, 10 px wide, and the name bar starts at x 23:
a two-digit number (10.., the mod's 17..99) fills the 10 px and its right digit's shadow column (x 23) was drawn over
by the name bar. Each menu's name template (x 23, width 82) and its list rows (the 17 position entries x 23 / 82)
move to x 24, width 81: the shadow shows, single digits and the names' text start (+1 px) as before otherwise.
shirtedit's lit number box is 11 px wide (se_hl) to cover that column too.
4.0.6 (Marco): the club's squad screen (squadMenu: number x 13 / 10 px, name bar x 23, 134 px, its 17 rows the same)
had the same covered shadow, and the number touched the name ("99MILE SVILAR"): its name template and rows move to
x 25, width 132 (the shadow column x 23, then a 1 px gap).
4.0.6 (Davide 02/11, MiSTer): a centred two-digit number (11 px with its shadow in the 10 px column) started on the
face box's last column. The number column moves 1 px right (x 14) on all three; the names 2 px right on the lists
(x 26 / width 79, Davide 03/11: with +1 a two-digit number's shadow met the name bar) and the squad screen's x 26 / 131:
names 2 px after the number column everywhere, 1 px clear on both sides of a two-digit number. shirtedit's lit box
(se_hl: the entry's own x, 11 px) follows the entry.
Data only (obj2 packed menus, the same bytes in every exe)."""
import re

TEMPLATE = (b'\x0d\x00\x00\x00\x0a\x00\x08\x00\x0c\x00\x00\x00\x00\x00\x00\x00'   # number: x 13, w 10, type 12
            b'\x17\x00\x00\x00\x52\x00\x08\x00\x04\x00\x0a\x00\x08\x00\x00\x80')  # name: x 23, w 82, red, text
SQUAD = TEMPLATE[:20] + b'\x86' + TEMPLATE[21:]        # squadMenu: name w 134


def patch(p):
    d2 = bytes(p.le.obj_bytes(2))
    hits = [m.start() for m in re.finditer(re.escape(TEMPLATE), d2)]
    assert len(hits) == 2, ('numcol: the two squad-list templates', hits)
    n = 0
    for h in hits:
        p.put(2, h, b'\x0e\x00')                         # 4.0.6: number x 14
        p.put(2, h + 16, b'\x1a\x00')                    # name template: x 26 (4.0.5: 24)
        p.put(2, h + 20, b'\x4f\x00')                    # width 79 (4.0.5: 81)
        rows = [h - 0x900 + m.start() for m in re.finditer(rb'\x17\x00.\x00\x52\x00\x08\x00\x02\x00',
                                                            d2[h - 0x900:h], re.S)]
        assert len(rows) == 17, ('numcol: list rows', len(rows))
        for r in rows:
            p.put(2, r, b'\x1a\x00')
            p.put(2, r + 4, b'\x4f\x00')
        n += len(rows)
    h = [m.start() for m in re.finditer(re.escape(SQUAD), d2)]
    assert len(h) == 1, ('numcol: the squad screen template', h)
    h = h[0]
    p.put(2, h, b'\x0e\x00')                            # number x 14 (Davide 02/11)
    p.put(2, h + 16, b'\x1a\x00')                       # 4.0.6: x 26, width 131
    p.put(2, h + 20, b'\x83\x00')
    rows = [h - 0x900 + m.start() for m in re.finditer(rb'\x17\x00.\x00\x86\x00\x08\x00\x02\x00', d2[h - 0x900:h], re.S)]
    assert len(rows) == 17, ('numcol: squad screen rows', len(rows))
    for r in rows:
        p.put(2, r, b'\x1a\x00')
        p.put(2, r + 4, b'\x83\x00')
    print(f'exe: squad lists\' number column x 14 (names x 26: 2 templates, {n} rows; the squad screen x 26)')
