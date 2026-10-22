"""4.0 match titles within 40 characters: the leg word of the French match title.

The game composes a match's title (cseg_29E79) as gameName (the contest's DIY+4 title) + ' ' + the round's long name +
' ' + the leg word: the second leg's string, or the first leg's (+149h / +14Bh), into a 40-character title. The French
exe's leg words are 'MATCH ALLER' / 'MATCH RETOUR' (11 / 12 characters, against ANDATA / RITORNO, 1ST / 2ND LEG,
HINSPIEL / RUCKSPIEL): World 2026-27 titles overflowed and were cut ('... 1/4 FINALE MATCH ALL', CONVENTIONS 1). The
title builders' references are repointed to 'ALLER' / 'RETOUR' (the same strings elsewhere - the competition
editor's labels - stay as they are). The German exe likewise: HINSPIEL / RUCKSPIEL (8 / 9, cut in 'PREMIERSHIP-RELEGATION
VIERTELF. HINSPIE') -> HINSP. / RUCKSP. (its own U-umlaut). Italian and English unchanged.
"""
import re
import struct

LEGS = {'fr': (b'ALLER', b'RETOUR'), 'de': (b'HINSP.', b'R\x9aCKSP.')}   # (DE: the exe's own U-umlaut, 9Ah)     # (first leg, second leg) where the exe's own words are too long
GAME_LEGS = {'it': ('ANDATA', 'RITORNO'), 'en': ('1ST LEG', '2ND LEG'), 'fr': ('ALLER', 'RETOUR'),
             'de': ('HINSP.', 'RUCKSP.')}   # the leg words the titles use after this patch


def sites(p, a0, a2):
    """[(obj1 offset of the 2nd-leg reference, of the 1st-leg reference)] in the title builders (the match title of
    cseg_29E79 and its twin)."""
    d = p.le.obj_bytes(1)
    A = lambda x: struct.pack('<I', x)
    pat = (rb'\xc7\x05' + re.escape(A(a0)) + rb'(....)\x8b\x35' + re.escape(A(a2)) +
           rb'\x66\x83\xbe\x49\x01\x00\x00\x01\x74.\x8b\x35' + re.escape(A(a2)) +
           rb'\x66\x83\xbe\x4b\x01\x00\x00\x02\x75.\xc7\x05' + re.escape(A(a0)) + rb'(....)')
    m = [x for x in re.finditer(pat, d, re.S)]
    assert len(m) == 2, len(m)
    return [(x.start(1), x.start(2)) for x in m]


def patch(p, area, lang):
    if lang not in LEGS:
        return
    import sacups
    r = sacups.regs(p.le.obj_bytes(1))
    pairs = sites(p, r['A0'], r['A0'] + 8)
    offs = [area.add(x + b'\0') for x in LEGS[lang]]
    for second, first in pairs:
        for site, off in ((first, offs[0]), (second, offs[1])):
            p.retarget(1, site, 2, off)
            p.put(1, site, struct.pack('<I', off))
    print(f"exe: match titles: the leg words {LEGS[lang][0].decode('latin-1')} / {LEGS[lang][1].decode('latin-1')} "
          f"({', '.join(f'obj1+{a:#x}/{b:#x}' for b, a in pairs)})")
