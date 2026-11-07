"""4.1 (Davide 07/11, slot 28): French team-pick headers short enough for the world's name.

SelectTeams' header is its first part (the default 'CHOISIR LES EQUIPES POUR ', 25 characters) + gameTypeStr (the
friendly's 'MATCH AMICAL', 12; a DIY / preset competition's name), then ' - ' + the menu's place (the world at the
top: MONDE 2026-27 / MONDE 1996-97 / EUROPE 1984-85, a continent or country inside it) only when the first two + the
place are at most 47 characters (the game's own test, obj1 0x3a631 / 0x3d2d8 'cmp word [0x3114b], 2Fh': a header of at
most 50), else no place at all: the French friendly's 25 + 12 + MONDE 2026-27's 13 = 50, over 47, showed neither World
2026-27 nor Europe 1984-85 (IT 'SCEGLI SQUADRE PER ' 19 does). The French exe's own string shortened in place (obj2,
NUL-padded to the old length: every reference unchanged, nothing saved): 'EQUIPES : ' (10) -> 'EQUIPES : MATCH AMICAL
- MONDE 2026-27' (38), 'EQUIPES : COUPE PERSONNELLE - EUROPE 1984-85' (44). More headers = more HDRS rows. Other
languages unchanged.
"""
import re

HDRS = {'fr': [(b'CHOISIR LES EQUIPES POUR ', b'EQUIPES : ')]}   # (the exe's string, ours: not longer)


def patch(p, lang):
    if lang not in HDRS:
        return
    d2 = p.le.obj_bytes(2)
    for old, new in HDRS[lang]:
        assert len(new) <= len(old), (old, new)
        at = [m.start() + 1 for m in re.finditer(re.escape(b'\0' + old + b'\0'), d2)]
        assert len(at) == 1, (old, at)
        assert bytes(p.get(2, at[0], len(old) + 1)) == old + b'\0', (old, bytes(p.get(2, at[0], len(old) + 1)))
        p.put(2, at[0], new.ljust(len(old), b'\0'))
        print(f"exe: header {old.decode('latin-1')!r} -> {new.decode('latin-1')!r} (obj2+{at[0]:#x})")
