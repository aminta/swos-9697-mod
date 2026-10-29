"""4.0.5 (4.0.1 parked fix, Regia 29/10: reproduced on rc10, world_gplay_seried_res): the job-offer letter leaves stray pixels in the menu buttons' texture (FILL.256 at [linAdr384k] + 65536):
drawing the letter (gotJobOfferMenu) writes 11 16-byte blocks from FILL + EC30h (its ACCEPT button's column at
screen y 393 = 185 + 208: DrawEmptyMenuItem has no clipping), and every menu after it shows them until a match
reloads the texture (GameLoop's LoadFillAndSwtitle). The game's 4 `mov [A6], offset gotJobOfferMenu; call ShowMenu`
(JobOffersMenu, the national job offers, ...) call fx_menu instead: ShowMenu, then LoadFillAndSwtitle (FILL.256 +
its menu palette, SWTITLE.256: the files the game reloads after a match), the pseudo-registers it uses kept.
The letter itself is drawn as before; the menus after it get the clean texture back."""
import re
import struct

ASM = '''
fx_menu:                                ; replaces `call ShowMenu` after `mov [A6], offset gotJobOfferMenu`
    call SHOWMENU
    pushad
    pushfd
    push dword [D0R]
    push dword [D1R]
    push dword [A0R]
    push dword [A1R]
    call LOADFILL
    pop dword [A1R]
    pop dword [A0R]
    pop dword [D1R]
    pop dword [D0R]
    popfd
    popad
    ret
'''


def sites(p):
    """(the 4 `call ShowMenu` offsets, ShowMenu, LoadFillAndSwtitle, the regs)."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a6, a1 = (struct.pack('<I', x) for x in (r['A0'] + 24, r['A0'] + 4))
    m = list(re.finditer(rb'\xc7\x05' + re.escape(a6) + rb'(.{4})\xe8(.{4})\xeb.\xc7\x05' + re.escape(a6) + rb'(.{4})\xe8',
                         d1, re.S))                 # JobOffersMenu: jobOffersMenu, ShowMenu, jmp, gotJobOfferMenu
    assert len(m) == 1, len(m)
    calls = [x.start() + 10 for x in re.finditer(rb'\xc7\x05' + re.escape(a6) + re.escape(m[0].group(3)) + rb'\xe8', d1)]
    assert len(calls) == 4, calls
    tgt = lambda a: a + 5 + struct.unpack_from('<i', d1, a + 1)[0]
    show = {tgt(c) for c in calls}
    assert len(show) == 1, show
    lf = [x.start() - 10 for x in re.finditer(rb'\xa1.{4}\x05\x00\x00\x01\x00\xa3' + re.escape(a1), d1, re.S)]
    assert len(lf) == 1 and d1[lf[0]:lf[0] + 2] == b'\xc7\x05', lf   # (its first instruction: mov [A0], 'fill.256')
    return calls, show.pop(), lf[0], r


def patch(p, at, nasmcave):
    """The stub at obj1 offset at (the career cave); returns the end."""
    calls, show, lf, r = sites(p)
    for c in calls:                                   # (another hook already there: refuse)
        assert p.get(1, c, 5) == p.le.obj_bytes(1)[c:c + 5], f'fillfix: {c:#x} already patched'
    sym = {'SHOWMENU': (1, show), 'LOADFILL': (1, lf), 'D0R': (2, r['D7'] - 28), 'D1R': (2, r['D7'] - 24),
           'A0R': (2, r['A0']), 'A1R': (2, r['A0'] + 4)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, tobj, toff in fix:
        p.add_ptr(1, at + o, tobj, toff)
    for c in calls:                                   # (relative calls: no fixups)
        p.put(1, c, b'\xe8' + struct.pack('<i', lab['fx_menu'] - (c + 5)))
    print(f'exe: job-offer letter: menu texture reloaded after it, obj1+{at:#x} ({len(code)} B), calls '
          + ', '.join(f'{c:#x}' for c in calls))
    return (at + len(code) + 3) & ~3
