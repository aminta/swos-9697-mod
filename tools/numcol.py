"""The squad lists' number column 1 px wider (4.0.5, Marco): on the team screen (playMatchMenu) and the tactics editor
(editTacticsMenu) the shirt number is a centred type-12 entry at x 13, 10 px wide, and the name bar starts at x 23:
a two-digit number (10.., the mod's 17..99) fills the 10 px and its right digit's shadow column (x 23) was drawn over
by the name bar. Each menu's name template (x 23, width 82) and its list rows (the 17 position entries x 23 / 82)
move to x 24, width 81: the shadow shows, single digits and the names' text start (+1 px) as before otherwise.
shirtedit's lit number box is 11 px wide (se_hl) to cover that column too.
Data only (obj2 packed menus, the same bytes in every exe)."""
import re

TEMPLATE = (b'\x0d\x00\x00\x00\x0a\x00\x08\x00\x0c\x00\x00\x00\x00\x00\x00\x00'   # number: x 13, w 10, type 12
            b'\x17\x00\x00\x00\x52\x00\x08\x00\x04\x00\x0a\x00\x08\x00\x00\x80')  # name: x 23, w 82, red, text


def patch(p):
    d2 = bytes(p.le.obj_bytes(2))
    hits = [m.start() for m in re.finditer(re.escape(TEMPLATE), d2)]
    assert len(hits) == 2, ('numcol: the two squad-list templates', hits)
    n = 0
    for h in hits:
        p.put(2, h + 16, b'\x18\x00')                    # name template: x 24
        p.put(2, h + 20, b'\x51\x00')                    # width 81
        rows = [h - 0x900 + m.start() for m in re.finditer(rb'\x17\x00.\x00\x52\x00\x08\x00\x02\x00',
                                                            d2[h - 0x900:h], re.S)]
        assert len(rows) == 17, ('numcol: list rows', len(rows))
        for r in rows:
            p.put(2, r, b'\x18\x00')
            p.put(2, r + 4, b'\x51\x00')
        n += len(rows)
    print(f'exe: squad lists\' number column 1 px wider (names x 24: 2 templates, {n} rows)')
