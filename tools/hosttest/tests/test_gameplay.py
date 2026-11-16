"""4.2 GAMEPLAY page (host side): the row table, the strings in 4 languages (font-safe: gameplay.py's own guard runs on import),
the GM item's constants; the RUOLI row and GP_RUOLI (the byte every position-traits piece reads) in Unicorn on a built exe
(HT_GAMEPLAY_EXE, else c/HTO4/SWOS/ITALIAN.EXE; a HOSTTEST_SYMS build - SKIP when it has no RUOLI row): the start values, the
four RUOLI x GAMEPLAY combinations through the page row's own path (gm_pg -> gm_sync) and the OPTIONS row's (gm_apply), the
save bit through a load and a new career (gm_load / gm_new), the parked CPU values untouched by the bit, and the page image
that gm_fill builds in obj3 against menu_image()."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
import gameplay  # noqa: E402

SIX = ['difficulty', 'dribbling', 'setpieces', 'cpucards', 'cpuinj', 'gkinj']
EXE = os.environ.get('HT_GAMEPLAY_EXE') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'HTO4', 'SWOS', 'ITALIAN.EXE')
B1, B2, B3, B4 = 0x100000, 0x400000, 0x1800000, 0x2000000
STACK, RET, MEM = 0x3F0000, 0x3E0000, 0x3000000


def test_present_rows_are_the_switches_in_order():
    assert [r[0] for r in gameplay.present()] == SIX + ['roles'] * gameplay.roles()
    assert gameplay.roles() == (not os.environ.get('GM_NOROLES'))


def test_absent_rows_leave_no_line():
    for lang in ('it', 'en', 'fr', 'de'):
        labels = [x[0] for x in gameplay.page(lang)]
        assert len(labels) == 6 + gameplay.roles() and gameplay.TAKERS[lang] not in labels
        assert (gameplay.ROLES[lang] in labels) == gameplay.roles()


def test_roles_row_is_last_yes_no_default_yes():
    if not gameplay.roles():
        return True, 'SKIP: GM_NOROLES'
    for lang in ('it', 'en', 'fr', 'de'):
        lab, vals = gameplay.page(lang)[-1]
        assert lab == gameplay.ROLES[lang] and vals == gameplay.YESNO[lang] and len(vals) == 2      # (value 0 = SI: the default)
    import swreg
    assert gameplay.gp_ruoli() == (4, swreg.GAMEPLAY_AT + gameplay.GP_RUOLI_OFF)
    assert gameplay.GM_U_OFF + 3 == gameplay.GM_R_OFF and gameplay.GM_R_OFF + 2 == gameplay.GP_RUOLI_OFF < gameplay.GM_SH_OFF
    return True, f'GP_RUOLI = obj4+{gameplay.gp_ruoli()[1]:#x}'


def test_room_for_every_row_on_the_page():
    assert len(gameplay.ROWS) <= gameplay.PAGE_MAX_ROWS
    assert gameplay.GM_Y + gameplay.GM_DY * (len(gameplay.ROWS) - 1) + 11 <= gameplay.GM_BACK_Y     # (the last row above the buttons)


def test_gm_item_default_is_personalizzato():
    assert gameplay.GM_SIZE == 5 and gameplay.GM_PERSONALIZZATO == 0 and gameplay.GM_ORIGINALE == 1    # (5 B: RUOLI is a bit of it)
    for lang in ('it', 'en', 'fr', 'de'):
        assert gameplay.VALUES[lang][0] != gameplay.VALUES[lang][1]


def test_texts_fit_a_row():
    from complist import px, font_odd
    for lang in ('it', 'en', 'fr', 'de'):                  # (the longest label + value of a page row: the dribbling page's own widths)
        for lab, vals in gameplay.page(lang):
            assert len(lab) + max(map(len, vals)) <= 40, (lang, lab, vals)
        assert len(gameplay.TITLE[lang]) <= 34
        assert px(gameplay.ROLES[lang]) <= 138 and not font_odd(gameplay.ROLES[lang]), (lang, gameplay.ROLES[lang])
        assert all(not font_odd(v) for v in gameplay.YESNO[lang])


# ---- Unicorn: the built band (RUOLI / GP_RUOLI)
class _M:
    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from emu import relocate
        self.syms = json.load(open(os.path.splitext(EXE)[0] + '.syms.json'))
        i1, i2, le = relocate(EXE, B1, B2, base3=B3, base4=B4)
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(0, MEM)
        for b, img in ((B1, i1), (B2, i2), (B3, le.img3), (B4, le.img4)):
            self.uc.mem_write(b, img)
        import swreg
        self.band = B4 + swreg.GAMEPLAY_AT
        self.g = {k: v[1] for k, v in self.syms['gameplay'].items()}

    def a(self, name):                                     # a gameplay label's linear address (obj4)
        return B4 + self.g[name]

    def rd(self, lin, n):
        return bytes(self.uc.mem_read(lin, n))

    def wr(self, lin, data):
        self.uc.mem_write(lin, bytes(data))

    def call(self, name, until=None, **regs):
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP
        self.wr(STACK - 4, struct.pack('<I', RET))
        self.uc.reg_write(UC_X86_REG_ESP, STACK - 4)
        self.uc.reg_write(UC_X86_REG_EBP, regs.get('ebp', 0))
        self.uc.reg_write(UC_X86_REG_EAX, regs.get('eax', 0))
        self.uc.emu_start(self.a(name), until or RET, count=100000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == (until or RET), (name, hex(self.uc.reg_read(UC_X86_REG_EIP)))

    def state(self):
        b, o = self.band, gameplay
        u0 = self.rd(b + o.GM_U_OFF, 1)[0]
        return dict(w=struct.unpack('<H', self.rd(b + o.GM_W_OFF, 2))[0], r=struct.unpack('<H', self.rd(b + o.GM_R_OFF, 2))[0],
                    gp=self.rd(b + o.GP_RUOLI_OFF, 1)[0], bit=u0 >> 7, shbit=self.rd(b + o.GM_SH_OFF + 2, 1)[0] >> 7, u0=u0 & 0x7F)

    def cc(self, val=None):                                # CC_W, CC_I (obj3 words: the CPU rows the swap parks)
        at = B3 + self.syms['cpucards']['CC_W'][1]
        if val is not None:
            self.wr(at, struct.pack('<HH', *val))
        return struct.unpack('<HH', self.rd(at, 4))


def _machine():
    if not os.path.exists(EXE) or not os.path.exists(os.path.splitext(EXE)[0] + '.syms.json'):
        return None, f'SKIP: no HOSTTEST_SYMS build at {EXE}'
    m = _M()
    if 'GP_RUOLI' not in m.g:
        return None, f'SKIP: {EXE} has no RUOLI row (built before it, or GM_NOROLES)'
    return m, ''


def test_gp_ruoli_start():
    m, why = _machine()
    if not m:
        return True, why
    import swreg
    assert (4, m.g['GP_RUOLI']) == gameplay.gp_ruoli() and m.g['GM_R'] == swreg.GAMEPLAY_AT + gameplay.GM_R_OFF
    s = m.state()
    assert s == dict(w=0, r=0, gp=1, bit=0, shbit=0, u0=0), s
    return True, f'at the program start GM_W 0, GM_R 0, GP_RUOLI 1 (obj4+{m.g["GP_RUOLI"]:#x})'


def test_gp_ruoli_four_combinations():
    """RUOLI x GAMEPLAY by the two paths that change them: the page row (GM_R written, gm_sync - what gm_pg does) and the OPTIONS
    row (gm_apply, ax = the new GM_W). CPU cards OFF / injuries ON (CC 1, 0) so the first parked byte is 1 under the RUOLI bit."""
    m, why = _machine()
    if not m:
        return True, why
    out = []
    for r in (0, 1):
        for w in (0, 1):
            m = _M()
            m.cc((1, 0))
            m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', r))
            m.call('gm_sync', ebp=m.band)
            m.call('gm_apply', ebp=m.band, eax=w)
            s = m.state()
            want = int(r == 0 and w == 0)
            assert s['gp'] == want and s['w'] == w and s['r'] == r and s['bit'] == r and s['shbit'] == r, (r, w, s)
            assert m.cc() == ((1, 1) if w else (1, 0)) and (not w or s['u0'] == 1), (r, w, s, m.cc())
            out.append(f'RUOLI {"NO" if r else "SI"} x {"ORIGINALE" if w else "PERSONALIZZATO"} -> {s["gp"]}')
            if w:                                          # back to PERSONALIZZATO: the choice and the parked values come back exactly
                m.call('gm_apply', ebp=m.band, eax=0)
                s = m.state()
                assert s['gp'] == int(r == 0) and s['r'] == r and s['bit'] == r and m.cc() == (1, 0), (r, s, m.cc())
    return True, '; '.join(out)


def test_gp_ruoli_load_and_new_career():
    """The save bit: the item's bytes as a load leaves them (GM_W, parked bytes with / without bit 7) -> gm_load; the session
    copy -> gm_new (the item zeroed by the new career first). An item of zeroes (a 4.1 save, an earlier beta) = RUOLI SI."""
    m, why = _machine()
    if not m:
        return True, why
    n = 0
    for r in (0, 1):
        for w in (0, 1):
            for path in ('gm_load', 'gm_new'):
                m = _M()
                item = struct.pack('<H3B', w, (r << 7) | 1, 0, 1)
                m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', 1 - r))          # (the session had the other choice)
                m.wr(m.band + (gameplay.GM_W_OFF if path == 'gm_load' else gameplay.GM_SH_OFF), item)
                m.call(path)
                s = m.state()
                assert s['r'] == r and s['gp'] == int(r == 0 and w == 0) and s['w'] == w and s['bit'] == r and s['shbit'] == r, (path, r, w, s)
                assert m.rd(m.band + gameplay.GM_W_OFF, 5) == item == m.rd(m.band + gameplay.GM_SH_OFF, 5), (path, r, w)
                n += 1
    return True, f'{n} cases (RUOLI x GAMEPLAY x load / new career): GM_R, GP_RUOLI and the 5 item bytes as saved'


def test_roles_row_keys():
    """The page row itself: gm_pg with RUOLI's entry selected - RIGHT (NO), RIGHT (stays), LEFT (SI), FIRE (NO), FIRE (wraps to
    SI) - up to its jump to the game's DrawMenuItem; then with GAMEPLAY ORIGINALE poked the same keys never give 1."""
    m, why = _machine()
    if not m:
        return True, why
    d = m.syms['difficulty']
    assert d['SYMS.D7_'][0] == 2 and d['SYMS.MENU_'][0] == 2 and d['SYMS.DRAWITEM'][0] == 1
    d7, menu, draw = B2 + d['SYMS.D7_'][1], B2 + d['SYMS.MENU_'][1], B1 + d['SYMS.DRAWITEM'][1]
    n = len(gameplay.present())
    entry = 0x3D0000
    m.wr(entry, struct.pack('<HH', 0, n + 1 + n - 1))      # (the selected entry: its ordinal at +2 = GM_V0 + the last row)
    m.wr(menu + 0xC, struct.pack('<I', entry))
    seq = []
    for w in (0, 1):
        m.wr(m.band + gameplay.GM_W_OFF, struct.pack('<H', w))
        m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', 0))
        for key, bit in (('right', 0x80), ('right', 0x80), ('left', 0x40), ('fire', 0x20), ('fire', 0x20)):
            m.wr(d7, bytes([bit]))
            m.call('gm_pg', until=draw)
            s = m.state()
            seq.append((w, key, s['r'], s['gp'], s['bit']))
    want = [(0, 'right', 1, 0, 1), (0, 'right', 1, 0, 1), (0, 'left', 0, 1, 0), (0, 'fire', 1, 0, 1), (0, 'fire', 0, 1, 0),
            (1, 'right', 1, 0, 1), (1, 'right', 1, 0, 1), (1, 'left', 0, 0, 0), (1, 'fire', 1, 0, 1), (1, 'fire', 0, 0, 0)]
    assert seq == want, seq
    return True, 'RIGHT / LEFT clamp, FIRE wraps; GM_R, GP_RUOLI, the save bit in step (PERSONALIZZATO and ORIGINALE)'


def test_options_row_fire_opens_the_obj3_page():
    """gm_tog (the OPTIONS row) with FIRE on PERSONALIZZATO, up to its jump to the game's ShowMenu: A6 = the page image in obj3,
    filled (the title's pointer set); GM_W unchanged."""
    m, why = _machine()
    if not m:
        return True, why
    d = m.syms['difficulty']
    assert d['SYMS.A6_'][0] == 2 and d['SYMS.SHOW_MENU'][0] == 1
    m.wr(B2 + d['SYMS.D7_'][1], bytes([0x20]))
    m.call('gm_tog', until=B1 + d['SYMS.SHOW_MENU'][1])
    a6 = struct.unpack('<I', m.rd(B2 + d['SYMS.A6_'][1], 4))[0]
    title = struct.unpack('<I', m.rd(a6 + 32, 4))[0]            # (the header 16 B + the title entry's 8 words)
    assert a6 == B3 + m.g['GM_IMG3'] and title == B4 + m.g['S_GT'] and m.state()['w'] == 0, (hex(a6), hex(title))
    return True, f'A6 = obj3+{m.g["GM_IMG3"]:#x}, the title -> S_GT'


def test_page_image_built_in_obj3():
    """gm_fill on the exe: the page image in obj3 = menu_image() of the build's own labels with every pointer filled (band /
    obj3 targets), gm_pg on every value row, RUOLI's string table = its word + the CPU rows' two strings."""
    m, why = _machine()
    if not m:
        return True, why
    lab = lambda mod: {k: v[1] for k, v in m.syms[mod].items()}
    dfl, spl, ccl, gkl, g = lab('difficulty'), lab('setpieces'), lab('cpucards'), lab('gkinj'), m.g
    rows = gameplay._rows(dfl, spl, ccl, gkl, g, g['GM_TABRU3'])
    assert len(rows) == 7
    own = {'S_GT': g['S_GT'], 'S_GLG': g['S_GLG'], 'S_BK': dfl['S_BK'], 'S_RS': dfl['S_RS'], 'dp_back': dfl['dp_back'], 'gm_reset': g['gm_reset']}
    img, ft, h0, stride = gameplay.menu_image(rows, lambda n: (0, own[n]))
    assert g['GM_TABRU3'] == g['GM_IMG3'] + len(img)
    want = bytearray(img)
    for o, k, t in ft:
        struct.pack_into('<I', want, o, (B3 if k else B4) + t)
    for i in range(len(rows)):
        struct.pack_into('<I', want, h0 + i * stride, B4 + g['gm_pg'])
    assert m.rd(B3 + g['GM_IMG3'], len(img) + gameplay.TAB_RU_SIZE) == img + bytes(gameplay.TAB_RU_SIZE), 'the image in the exe: pointers zero'
    m.call('gm_fill', ebp=m.band)
    got = m.rd(B3 + g['GM_IMG3'], len(img))
    assert got == bytes(want), [hex(i) for i in range(len(img)) if got[i] != want[i]][:8]
    tab = m.rd(B3 + g['GM_TABRU3'], gameplay.TAB_RU_SIZE)
    cct = m.rd(B3 + ccl['TAB_R'], 14)
    assert tab == struct.pack('<IH', B4 + g['GM_R'], 0) + cct[6:] and struct.unpack('<I', cct[6:10])[0], tab.hex()
    return True, f'{len(rows)} rows, image {len(img)} B at obj3+{g["GM_IMG3"]:#x}, {len(ft)} pointers + {len(rows)} handlers, RUOLI table filled'


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            print('ok', k, f())
