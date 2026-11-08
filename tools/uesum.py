"""4.1 S2a (Davide 08/11): STAT > RIEPILOGO of a world's UEFA cups - uesum.c in obj4 after swe.c (its own page:
obj4+swreg.UESUM_AT, the 3rd), the page text built from the viewed contest (see uesum.c). ctview's
glue (obj3) holds two pointers, set here: CV_USOK -> us_ok (cv_stinit: entry 10 shown), CV_UST -> us_text (cv_sum:
the page, then cv_page's tail)."""
import os
import struct

import rnames

TEXTS = {   # pens, a.e.t. (holder, to be played, winner: ctview.TEXTS')
    'it': (b'RIG.', b'D.T.S.'), 'en': (b'PENS', b'AET'), 'fr': (b'TAB', b'A.P.'), 'de': (b'I.E.', b'N.V.')}
STAGES = (0, 1, 2, 12, 13, 14)  # rnames.NAMES' long names: league phase, play-offs, round of 16, QF, SF, final
LABELS = {}


def table(lang):
    import complist
    import ctview
    cv = ctview.TEXTS[lang]
    txt = [cv[0], cv[1], cv[2], *TEXTS[lang]] + [rnames.NAMES[lang][k][0].encode('latin1') for k in STAGES]
    for t in txt:
        assert all(ch in complist.FONT for ch in t.decode('latin1')) and complist.px(t.decode('latin1')) <= 200, (lang, t)
    head = 2 * len(txt) + 64
    offs, strs = [], bytearray()
    for t in txt:
        offs.append(head + len(strs))
        strs += t + b'\0'
    wid = bytes(min(255, complist.px(chr(0x20 + k))) if chr(0x20 + k) in complist.FONT else 6 for k in range(64))
    return struct.pack(f'<{len(txt)}H', *offs) + wid + bytes(strs)


def patch(p, at, lang, usc=False):
    """uesum.c + its table at obj4:swreg.UESUM_AT (at: swe.patch's end, below it); ctview's pointers to it; usc: supercup's
    usc_snap patched (the holders' saved copy). Returns the end."""
    import careerworld
    import cobj
    import ctview
    import fmtpage
    import lib97
    import trailer
    import winners
    assert ctview.CR_PTRS.get('usok'), 'uesum: ctview first'
    import swe
    import swreg
    room = 0x1000 * swe.OBJ4_PAGES                      # (obj4: uesum's own page above the registry's end, MC 08/11)
    assert at <= swreg.REG_AT and swreg.OBJ4_END <= swreg.UESUM_AT < room == p.le.obj(4).npages * 0x1000, (hex(at), room)
    t0 = at = swreg.UESUM_AT
    tab = table(lang)
    p.put(4, at, tab)
    tab_at, at = at, (at + len(tab) + 3) & ~3
    ws = fmtpage.WN['sym']
    diycopy = lib97._sites(p)[3]
    import supercup                                     # the holders: usc_snap's copy in the UEFA Super Cup's saved
    if usc:                                             # state (SC_ST's last entry +6: CC, CWC, UEFA words; the
        so, sa = supercup.LABELS['SC_ST']               # game's HOLD_* are not saved - 0 after a load)
        hold = (so, sa + 12 + 12 * (supercup.NE - 1) + 6)
    else:
        q = careerworld._qual_sites(p.le.obj_bytes(1), p)
        assert q['HOLD_CWC'][1] == q['HOLD_CC'][1] + 2 and q['HOLD_UEFA'][1] == q['HOLD_CC'][1] + 4
        hold = q['HOLD_CC']
    ext = {'UC': (2, diycopy), 'UD': (2, diycopy + 0x41F), 'SELPTR': (2, winners.sel_ptr(p)),
           'NUMSEL': trailer.INFO['NUMSEL'], 'HOLD': hold, 'TXT': ws['TXT'], 'TITLE': ws['TITLE'],
           'W_LPW': (1, careerworld.LABELS['w_lpw']), 'US_TAB': (4, tab_at)}
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uesum.c'),
                         ['-Oz', '-fno-zero-initialized-in-bss', f'-DTXTMAX={fmtpage.TXTMAX}'])
    syms, end, bss = cobj.link(p, obj, at, (4, 0), externs=ext, limit=room, text_obj=4)
    assert bss == 0, ('uesum.c: no .bss (statics in its data)', bss)
    assert end <= room, ('uesum past obj4', hex(end), hex(room))
    cp = ctview.CR_PTRS
    for k, f in (('usok', 'us_ok'), ('ust', 'us_text')):
        p.add_ptr(3, cp[k], *syms[f])
        p.put(3, cp[k], struct.pack('<I', syms[f][1]))
    LABELS.clear()
    LABELS.update(syms)
    print(f'exe: UEFA RIEPILOGO (uesum, 4.1 S2a): obj4+{t0:#x}..{end:#x} ({end - t0} B: table {len(tab)}, C {end - at}); '
          f'obj4 left {room - end} B')
    return end
