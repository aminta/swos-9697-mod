"""4.2 GAMEPLAY page (host side): the row table, the strings in 4 languages (font-safe: gameplay.py's own guard runs on import),
the GM item's constants; the RUOLI row and GP_RUOLI (the byte every position-traits piece reads) in Unicorn on a built exe
(HT_GAMEPLAY_EXE, else c/HTO4/SWOS/ITALIAN.EXE; a HOSTTEST_SYMS build - SKIP when it has no RUOLI row): the start values, the
four RUOLI x GAMEPLAY combinations through the page row's own path (gm_pg -> gm_sync) and the OPTIONS row's (gm_apply), the
save bit through a load and a new career (gm_load / gm_new), the parked CPU values untouched by the bit, PREDEFINITI, and the
page image that gm_fill builds in obj3 against menu_image(); the GM_RUOLI_SI test build (HT_GAMEPLAY_EXE_SI). The default is gameplay.RUOLI_DEFAULT (NO since Davide 16/11): the
start values and PREDEFINITI follow it; the save bit is absolute (set = SI), so a save keeps its RUOLI in a build with the other
default - checked on a second exe built with the other RUOLI_DEFAULT (HT_GAMEPLAY_EXE_ALT, else c/REL42rud0/SWOS/ITALIAN.EXE)."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
import gameplay  # noqa: E402

SIX = ['difficulty', 'dribbling', 'setpieces', 'cpucards', 'cpuinj', 'gkinj']
EXE = os.environ.get('HT_GAMEPLAY_EXE') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'HTO4', 'SWOS', 'ITALIAN.EXE')
ALT = os.environ.get('HT_GAMEPLAY_EXE_ALT') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'REL42rud0', 'SWOS', 'ITALIAN.EXE')
SI_EXE = os.environ.get('HT_GAMEPLAY_EXE_SI') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'REL42rusi', 'SWOS', 'ITALIAN.EXE')
D = gameplay.RUOLI_DEFAULT                                 # (0 SI / 1 NO)
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


def test_roles_row_is_last_yes_no():
    if not gameplay.roles():
        return True, 'SKIP: GM_NOROLES'
    for lang in ('it', 'en', 'fr', 'de'):
        lab, vals = gameplay.page(lang)[-1]
        assert lab == gameplay.ROLES[lang] and vals == gameplay.YESNO[lang] and len(vals) == 2      # (value 0 = SI, 1 = NO)
    assert D == 1, 'RUOLI_DEFAULT: NO in 4.2 (Davide 16/11) - a deliberate change edits this line, the notes and the README'
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
    def __init__(self, exe=None):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from emu import relocate
        exe = exe or EXE
        self.syms = json.load(open(os.path.splitext(exe)[0] + '.syms.json'))
        i1, i2, le = relocate(exe, B1, B2, base3=B3, base4=B4)
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


def _machine(exe=None):
    exe = exe or EXE
    if not os.path.exists(exe) or not os.path.exists(os.path.splitext(exe)[0] + '.syms.json'):
        return None, f'SKIP: no HOSTTEST_SYMS build at {exe}'
    m = _M(exe)
    if 'GP_RUOLI' not in m.g:
        return None, f'SKIP: {exe} has no RUOLI row (built before it, or GM_NOROLES)'
    return m, ''


def _reset(m):
    """gm_reset (PREDEFINITI) with the game's DrawMenuItem a bare ret and a fake selected entry (the RESET button)."""
    d = m.syms['difficulty']
    n = len(gameplay.present())
    m.wr(B1 + d['SYMS.DRAWITEM'][1], b'\xc3')
    entry = 0x3D0000
    m.wr(entry, struct.pack('<HH', 0, 2 * n + 2))
    m.wr(B2 + d['SYMS.MENU_'][1] + 0xC, struct.pack('<I', entry))
    m.call('gm_reset')


def test_gp_ruoli_start():
    m, why = _machine()
    if not m:
        return True, why
    import swreg
    assert (4, m.g['GP_RUOLI']) == gameplay.gp_ruoli() and m.g['GM_R'] == swreg.GAMEPLAY_AT + gameplay.GM_R_OFF
    s = m.state()
    assert s == dict(w=0, r=D, gp=1 - D, bit=1 - D, shbit=1 - D, u0=0), s
    m.call('gm_new')                                       # (a new career before any choice: the session copy = the default)
    assert m.state() == s, m.state()
    return True, f'at the program start GM_W 0, GM_R {D} ({"NO" if D else "SI"}), GP_RUOLI {1 - D} (obj4+{m.g["GP_RUOLI"]:#x}); a new career keeps it'


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
            assert s['gp'] == want and s['w'] == w and s['r'] == r and s['bit'] == 1 - r and s['shbit'] == 1 - r, (r, w, s)
            assert m.cc() == ((1, 1) if w else (1, 0)) and (not w or s['u0'] == 1), (r, w, s, m.cc())
            out.append(f'RUOLI {"NO" if r else "SI"} x {"ORIGINALE" if w else "PERSONALIZZATO"} -> {s["gp"]}')
            if w:                                          # back to PERSONALIZZATO: the choice and the parked values come back exactly
                m.call('gm_apply', ebp=m.band, eax=0)
                s = m.state()
                assert s['gp'] == int(r == 0) and s['r'] == r and s['bit'] == 1 - r and m.cc() == (1, 0), (r, s, m.cc())
    return True, '; '.join(out)


def test_gp_ruoli_load_and_new_career():
    """The save bit (set = SI): the item's bytes as a load leaves them (GM_W, parked bytes with / without bit 7) -> gm_load;
    the session copy -> gm_new (the item zeroed by the new career first). An item of zeroes (a 4.1 save: no item; an earlier
    4.2 beta: no bit) = RUOLI NO, GP_RUOLI 0, whatever the session had."""
    m, why = _machine()
    if not m:
        return True, why
    n = 0
    for r in (0, 1):
        for w in (0, 1):
            for path in ('gm_load', 'gm_new'):
                m = _M()
                item = struct.pack('<H3B', w, ((1 - r) << 7) | 1, 0, 1)
                m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', 1 - r))          # (the session had the other choice)
                m.wr(m.band + (gameplay.GM_W_OFF if path == 'gm_load' else gameplay.GM_SH_OFF), item)
                m.call(path)
                s = m.state()
                assert s['r'] == r and s['gp'] == int(r == 0 and w == 0) and s['w'] == w and s['bit'] == 1 - r and s['shbit'] == 1 - r, (path, r, w, s)
                assert m.rd(m.band + gameplay.GM_W_OFF, 5) == item == m.rd(m.band + gameplay.GM_SH_OFF, 5), (path, r, w)
                n += 1
    for was in (0, 1):                                     # the zeroed item (an old save), the session on SI / NO before the load
        m = _M()
        m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', was))
        m.call('gm_sync', ebp=m.band)
        m.wr(m.band + gameplay.GM_W_OFF, bytes(5))
        m.call('gm_load')
        s = m.state()
        assert s == dict(w=0, r=1, gp=0, bit=0, shbit=0, u0=0), (was, s)
    return True, f'{n} cases (RUOLI x GAMEPLAY x load / new career): GM_R, GP_RUOLI and the 5 item bytes as saved; a zeroed item (old save) -> NO, GP_RUOLI 0'


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
    want = [(0, 'right', 1, 0, 0), (0, 'right', 1, 0, 0), (0, 'left', 0, 1, 1), (0, 'fire', 1, 0, 0), (0, 'fire', 0, 1, 1),
            (1, 'right', 1, 0, 0), (1, 'right', 1, 0, 0), (1, 'left', 0, 0, 1), (1, 'fire', 1, 0, 0), (1, 'fire', 0, 0, 1)]
    assert seq == want, seq
    return True, 'RIGHT / LEFT clamp, FIRE wraps; GM_R, GP_RUOLI, the save bit in step (PERSONALIZZATO and ORIGINALE)'


def test_roles_row_from_the_start():
    """As a player: from the program's start (the default), LEFT on the row = SI: GP_RUOLI 1; RIGHT = NO: 0."""
    m, why = _machine()
    if not m:
        return True, why
    d = m.syms['difficulty']
    n = len(gameplay.present())
    m.wr(0x3D0000, struct.pack('<HH', 0, 2 * n))
    m.wr(B2 + d['SYMS.MENU_'][1] + 0xC, struct.pack('<I', 0x3D0000))
    seq = [(m.state()['r'], m.state()['gp'])]
    for bit in (0x40, 0x80):
        m.wr(B2 + d['SYMS.D7_'][1], bytes([bit]))
        m.call('gm_pg', until=B1 + d['SYMS.DRAWITEM'][1])
        seq.append((m.state()['r'], m.state()['gp']))
    assert seq == [(D, 1 - D), (0, 1), (1, 0)], seq
    return True, f'start (GM_R, GP_RUOLI) {seq[0]}, LEFT -> {seq[1]}, RIGHT -> {seq[2]}'


def test_predefiniti_resets_roles_to_the_default():
    """gm_reset from RUOLI = the non-default choice: PERSONALIZZATO -> GM_R = RUOLI_DEFAULT, GP_RUOLI = 1 - it, the bit in
    step, the CPU words 0; ORIGINALE (the parked values reset) -> GM_R = RUOLI_DEFAULT, GP_RUOLI 0."""
    m, why = _machine()
    if not m:
        return True, why
    out = []
    for w in (0, 1):
        m = _M()
        m.cc((1, 1))
        m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', 1 - D))
        m.call('gm_sync', ebp=m.band)
        m.call('gm_apply', ebp=m.band, eax=w)
        assert m.state()['r'] == 1 - D and m.state()['bit'] == D, m.state()
        _reset(m)
        s = m.state()
        assert s == dict(w=w, r=D, gp=0 if w else 1 - D, bit=1 - D, shbit=1 - D, u0=0), (w, s)
        assert m.cc() == ((1, 1) if w else (0, 0)), (w, m.cc())
        out.append(f'{"ORIGINALE" if w else "PERSONALIZZATO"}: GM_R {s["r"]}, GP_RUOLI {s["gp"]}')
    return True, '; '.join(out)


def test_save_keeps_roles_across_a_default_change():
    """MC 16/11: the saved bit is absolute. The item as THIS build saves it with RUOLI NO and with RUOLI SI (GM_R set, gm_sync;
    the 5 bytes read back), loaded (gm_load) into the exe built with the OTHER RUOLI_DEFAULT (ALT) and into this one: NO stays
    NO, SI stays SI, in both. ALT's own start values are its default's (it IS the other build)."""
    m, why = _machine()
    if not m:
        return True, why
    a, why = _machine(ALT)
    if not a:
        return True, why
    s0 = a.state()
    if (s0['r'], s0['gp'], s0['bit'], s0['shbit']) != (1 - D, D, D, D):
        return True, f'SKIP: {ALT} is not a RUOLI_DEFAULT = {1 - D} build (start {s0})'
    out = []
    for r in (1, 0):
        m = _M()
        m.wr(m.band + gameplay.GM_R_OFF, struct.pack('<H', r))
        m.call('gm_sync', ebp=m.band)
        item = m.rd(m.band + gameplay.GM_W_OFF, 5)
        assert item[2] >> 7 == 1 - r, item.hex()
        for exe in (ALT, EXE):
            x = _M(exe)
            x.wr(x.band + gameplay.GM_W_OFF, item)
            x.call('gm_load')
            s = x.state()
            assert s['r'] == r and s['gp'] == 1 - r and s['bit'] == 1 - r, (exe, r, s)
        out.append(f'saved {"NO" if r else "SI"} (item {item.hex()}) -> {"NO" if r else "SI"} under default {"SI" if D else "NO"} and under default {"NO" if D else "SI"}')
    x = _M(ALT)                                            # (and ALT's first new career = ITS default)
    x.call('gm_new')
    assert x.state() == s0, x.state()
    return True, '; '.join(out)


def test_ruoli_si_test_build():
    """GM_RUOLI_SI=1 (the traits pieces' test switch; HT_GAMEPLAY_EXE_SI, else c/REL42rusi): the program starts with RUOLI SI -
    GM_R 0, GP_RUOLI 1, the item's and the session copy's bit set, so the first new career keeps SI - and nothing else moves:
    PREDEFINITI still gives RUOLI_DEFAULT, a zeroed item (an old save) still loads NO, the code is the release build's
    (the two bands differ only in the 4 start bytes)."""
    m, why = _machine()
    if not m:
        return True, why
    x, why = _machine(SI_EXE)
    if not x:
        return True, why
    s0 = x.state()
    if s0 != dict(w=0, r=0, gp=1, bit=1, shbit=1, u0=0):
        return (True, f'SKIP: {SI_EXE} is not a GM_RUOLI_SI build (start {s0})') if D else (False, f'start {s0}')
    import swreg
    n = swreg.GAMEPLAY_END - swreg.GAMEPLAY_AT
    a, b = m.rd(m.band, n), x.rd(x.band, n)
    diff = [i for i in range(n) if a[i] != b[i]]
    o = gameplay
    assert set(diff) <= {o.GM_U_OFF, o.GM_R_OFF, o.GP_RUOLI_OFF, o.GM_SH_OFF + 2}, [hex(i) for i in diff]
    x.call('gm_new')
    assert x.state() == s0, x.state()
    _reset(x)
    s = x.state()
    assert (s['r'], s['gp'], s['bit']) == (D, 1 - D, 1 - D), s
    x = _M(SI_EXE)
    x.wr(x.band + o.GM_W_OFF, bytes(5))
    x.call('gm_load')
    s = x.state()
    assert (s['r'], s['gp'], s['bit']) == (1, 0, 0), s
    return True, f'start GM_R 0, GP_RUOLI 1; a new career keeps SI; PREDEFINITI -> GM_R {D}; an old save -> NO; the band differs from the release build in {len(diff)} start bytes'


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
