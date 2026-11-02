"""4.0.5 the mod's version on the main menu (Davide: support needs to know what is installed): 'MOD 4.0.5' in the
game's smallest font (smallCharsTable, the match's), centred below LOAD OLD COMPETITION, drawn by the main menu's
on-draw function (SWOS_MainMenu +8, 0 in the game; SWOS++ patches +4 / +0xC / +0x22 / +0x9E / +0xCE, not +8) through
the game's DrawMenuTextCentered. Not drawn while CONTINUE (entry 10) is shown: LOAD OLD COMPETITION is then at the
bottom and nothing fits below it.

The text has one source: mkpatcher.VERSION (the patcher's), + ' ' + MODVER_TAG (betas / release candidates: 'B11',
'RC11'), or ' TEST' in a build with a test switch (*_FORCE and the like) - so a tester's report names the build.
"""
import os
import re
import struct

import nasmcave
import sacups

X, Y, COLOR = 160, 176, 2          # centre x, top y (screen), DrawMenuText's colour (D3)
TEST_VARS = ('GPLAY_FORCE', 'DPLAY_FORCE', 'CD_FORCE', 'CONTI_FORCE', 'SPLIT_FORCE', 'UEFAQ_FORCE', 'GPLAY_KOFORCE',
             'GPLAY_RLFORCE', 'CONTI_GPLACE', 'STATESPEC_TEST', 'CONTI_KOLOSE', 'CAREER_SEED', 'OFFER_FORCE', 'BPLACE_FORCE', 'CONTI_KOWIN', 'GPLAY_GFFORCE', 'GPLAY_GOUT', 'GPLAY_S3DEFER', 'GPLAY_GFREST')
BUILD_SWITCHES = TEST_VARS + (                     # 4.0.6: every switch a test build may set; buildrel.sh clears
    'CONTI_CONFS', 'CONTI_LEAGUE_PLAYED', 'CONTI_GUEST', 'CONTI_TEST_MANAGER', 'CONTI_DUMP', 'SEC_FORCE_B',   # them (and
    'HDR_TEST', 'NO_VC5', 'NO_CUP12', 'MKSEASON_NOBALANCE', 'PROTO36', 'RIPOOL_TEST_SR', 'STATECUP_TEST',  # every *_FORCE)
    'TAILZERO_FILL_TEST', 'SIMDRAW_G0', 'SIMDRAW_G1', 'SIMDRAW_K', 'SIMDRAW_D0', 'SIMDRAW_D1', 'XTRA_HOOK',
    'AFTER_PROCESS_PROBE', 'QUIETEND_OFF')


def text():
    v = re.search(r"^VERSION = '([^']+)'", open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        'mkpatcher.py')).read(), re.M).group(1)   # (no import: the
    tag = os.environ.get('MODVER_TAG') or ('TEST' if any(os.environ.get(v) for v in TEST_VARS) or
                                           any(k.endswith('_FORCE') and v for k, v in os.environ.items()) else '')
    return ('MOD ' + v + (' ' + tag.upper() if tag else '')).encode('ascii')     # patcher's file checks)


ASM = r"""
mv_draw:                                ; SWOS_MainMenu's on-draw function
    pushad
    cmp word [MENU_ + 16h + 10 * 38h + 4], 0
    je .x                               ; (CONTINUE shown: no room)
    sub esp, 60                         ; the game's D0..D7, A0..A6 are memory: keep them
    mov esi, D0_
    mov edi, esp
    mov ecx, 15
    rep movsd
    mov dword [A0_], MV_TEXT
    mov dword [A0_ + 4], SMALLCHARS
    mov word [D0_ + 4], X_
    mov word [D0_ + 8], Y_
    mov word [D0_ + 12], COLOR_
    call CENTERED
    mov esi, esp
    mov edi, D0_
    mov ecx, 15
    rep movsd
    add esp, 60
.x: popad
    ret
"""


def find(p):
    d1 = p.le.obj_bytes(1)
    d2 = p.le.obj_bytes(2)
    r = sacups.regs(d1)
    D0, A0 = r['D7'] - 28, r['A0']
    assert A0 == D0 + 32, (hex(D0), hex(A0))             # (D0..D7 then A0..A6: 15 dwords)
    P = lambda a: re.escape(struct.pack('<I', a))
    # SWOS_MainMenu: dd init, dd GlobalRetn, dd 0 (on draw), dd 5; -998, 0, 1; entry 0: 0, 40, 150, 16, type 2
    m = [x.start() for x in re.finditer(re.escape(struct.pack('<IIhhhhhhhH', 0, 5, -998, 0, 1, 0, 40, 150, 16, 2)), d2)]
    assert len(m) == 1, ('SWOS_MainMenu', m)
    menu = m[0] - 8
    assert not [f for f in p.le.fixups() if f[0] == 2 and f[1] == menu + 8]
    # DrawMenuTextCentered: push D1; push D2; push A0; push A1; call GetTextWidth; pop A1; pop A0; pop D2; pop D1;
    # add word [D7], 1; shr word [D7], 1
    c = [x.start() for x in re.finditer(rb'\xff\x35' + P(D0 + 4) + rb'\xff\x35' + P(D0 + 8) + rb'\xff\x35' + P(A0) +
                                        rb'\xff\x35' + P(A0 + 4) + rb'\xe8....\x8f\x05' + P(A0 + 4) + rb'\x8f\x05' + P(A0) +
                                        rb'\x8f\x05' + P(D0 + 8) + rb'\x8f\x05' + P(D0 + 4) + rb'\x66\x83\x05' + P(D0 + 28) +
                                        rb'\x01\x66\xd1\x2d' + P(D0 + 28) + rb'\x66\xa1' + P(D0 + 28) +
                                        rb'\x66\x29\x05' + P(D0 + 4) + rb'\xe9', d1, re.S)]
    assert len(c) == 1, ('DrawMenuTextCentered', c)
    import namespr                                       # (MakePlayerNameSprite: mov [A0], offset numberBuffer;
    s = namespr.find(p)                                  #  mov [A1], offset smallCharsTable)
    ref = max(s['refs'])
    assert d1[ref + 4:ref + 6] == b'\xc7\x05' and struct.unpack_from('<I', d1, ref + 6)[0] == A0 + 4
    small = p.target(1, ref + 10)
    import zones
    return dict(menu=menu, centered=c[0], small=small, D0=D0, A0=A0, menu_cur=zones._current_menu(p))


def patch(p, at, lang):
    """Code + text at obj1:at; returns the end."""
    import lepatch
    s = find(lepatch.LEPatch(bytes(p.le.data)))          # (the original bytes: patched sites elsewhere don't matter)
    t = text()
    sym = {'MENU_': s['menu_cur'], 'D0_': (2, s['D0']), 'A0_': (2, s['A0']), 'SMALLCHARS': s['small'],
           'CENTERED': (1, s['centered']), 'X_': (0, X), 'Y_': (0, Y), 'COLOR_': (0, COLOR)}
    src = ASM + 'MV_TEXT: db ' + ', '.join(str(b) for b in t + b'\0') + '\n'
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.add_ptr(2, s['menu'] + 8, 1, lab['mv_draw'])
    p.put(2, s['menu'] + 8, struct.pack('<I', lab['mv_draw']))
    print(f"exe: main menu version line {t.decode()!r}: on-draw obj1+{at:#x} ({len(code)} B), menu obj2+{s['menu']:#x}")
    return at + len(code)
