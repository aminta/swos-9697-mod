"""4.2 preseason friendlies, the chooser page tools/frchoose.c + tools/frchoose.py. Host only: the page's C built
natively (clang -shared, ctypes; the game replaced by fc_host_* callbacks: a fake unpacked menu, club records by
team word) over the real frcsel.c / frpick.c, the 4 languages' texts and the menu's layout, and the object built with
the exe's flags. What the selection state does is test_frcsel.py; the pick is test_frpick.py."""
import ctypes
import os
import random
import re
import struct
import subprocess
import sys
import tempfile

import test_frpick as T
import test_frcsel as S
from test_frpick import NONE, mkblob, word

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)
import frchoose                                             # noqa: E402

D = frchoose.cdefs()
NE, ESZ, HDR = D['FC_NE'], 0x38, 0x16
_TMP = tempfile.mkdtemp(prefix='frchoose')
ENT = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)
TEAM = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)
SHOW = ctypes.CFUNCTYPE(None)
PTRF = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)


class Game:
    """the page's C against a fake game: g_currentMenu as bytes, GetTeamPointer by a dict of names, ShowMenu = a
    script of the player's actions run while the page is 'shown'"""

    def __init__(self, names, script=None, swospp=0xFF, list_words=()):
        so = os.path.join(_TMP, 'frchoose.dylib')
        if not os.path.exists(so):
            stub = os.path.join(_TMP, 'stub.c')
            open(stub, 'w').write(
                'unsigned char DREG[60]; unsigned char SWOSPP = 0xFF; unsigned char MENU[0x16 + 0x38 * 64];\n'
                'typedef unsigned char *(*E)(unsigned); typedef const unsigned char *(*T)(unsigned); typedef void (*S)(void);\n'
                'E fc_e; T fc_t; S fc_s; T fc_p;\n'
                'const unsigned char *fc_host_ptr(unsigned v) { return fc_p(v); }\n'
                'unsigned char *fc_host_ent(unsigned k) { return fc_e(k); }\n'
                'const unsigned char *fc_host_team(unsigned w) { return fc_t(w); }\n'
                'void fc_host_show(void) { fc_s(); }\n'
                'void fc_host_set(E e, T t, S s, T p) { fc_e = e; fc_t = t; fc_s = s; fc_p = p; }\n')
            texts = frchoose.texts('it')
            arr = lambda nm, n, w: 'const char %s[%d][%d] = {%s};\n' % (
                nm, n, w, ', '.join('"%s"' % texts[nm][i * w:(i + 1) * w].rstrip(b'\0').decode() for i in range(n)))
            open(stub, 'a').write(arr('FC_S_LVL', 4, 16) + arr('FC_S_BAND', 3, 12) + arr('FC_S_VEN', 2, 4)
                                  + arr('FC_S_MSG', 5, 40))
            subprocess.run(['clang', '-shared', '-O2', '-Wall', '-Werror', '-DFRC_OWN_PICK', '-I', TOOLS, '-o', so,
                            os.path.join(TOOLS, 'frchoose.c'), stub], check=True)
        self.l = l = ctypes.CDLL(so)
        self.menu = (ctypes.c_uint8 * (HDR + ESZ * 64))()
        self.recs = {w: ctypes.create_string_buffer(struct.pack('<H', w) + b'\0\0\0' + n.encode() + b'\0', 684)
                     for w, n in names.items()}
        self.script, self.shown = script, 0
        self.cb = (ENT(lambda k: ctypes.addressof(self.menu) + HDR + ESZ * k),
                   TEAM(lambda w: ctypes.addressof(self.recs[w]) if w in self.recs else None), SHOW(self._show),
                   PTRF(lambda v: self.ptrs.get(v)))
        self.ptrs = {ctypes.addressof(r) & 0xFFFFFFFF: ctypes.addressof(r) for r in self.recs.values()}
        l.fc_host_set(*self.cb)
        ctypes.c_uint8.in_dll(l, 'SWOSPP').value = swospp
        self.dreg = (ctypes.c_uint8 * 60).in_dll(l, 'DREG')
        self.sel = S.FrcSel.in_dll(l, 'FC_SEL')
        self.list_words = list_words

    def _show(self):
        self.shown += 1
        self.l.fc_paint()                                   # (the menu's onInit)
        if self.script:
            self.script(self)

    def ent(self, k):
        return bytes(self.menu[HDR + ESZ * k:HDR + ESZ * (k + 1)])

    def col(self, k):
        return struct.unpack_from('<H', self.ent(k), 0x1E)[0]

    def hidden(self, k):
        return struct.unpack_from('<H', self.ent(k), 4)[0]

    def choose(self, ctx):
        g, v = (ctypes.c_uint16 * 4)(*([NONE] * 4)), ctypes.c_uint8(0xFF)
        self.l.frc_choose(ctypes.byref(ctx), g, ctypes.byref(v))
        return list(g), v.value

    def trace(self):
        return ctypes.c_uint8.in_dll(self.l, 'FC_TRACE').value

    def fire_level(self, left=False):
        self.dreg[28] = 0x40 if left else 0x20
        self.l.fc_level()

    def pick(self, k, w):
        """FIRE on row k's club, then the browser returning club w (None: ESCI)"""
        if not self.l.fc_club(k):
            return False
        struct.pack_into('<I', self.dreg, 0, 0xFFFF if w is None else 0)
        rec = self.recs.get(w)
        struct.pack_into('<I', self.dreg, 32, ctypes.addressof(rec) & 0xFFFFFFFF if rec is not None else 0)
        self.l.fc_picked()
        return True


def setup(seed=1, **kw):
    rnd = random.Random(seed)
    blob, world, clubs = S.table(rnd, per=(20, 30))
    names = {w: f'CLUB {w:04X}' for w in clubs}
    me = clubs[len(clubs) // 2]
    page = S.Page(blob, world, me, **kw)                    # (its ctx; its own FrcSel is the reference)
    return blob, world, clubs, names, me, page


def test_frchoose_texts():
    """4 languages: every text in the font's capitals, inside its box (px), fixed-size tables with room; the same
    number of entries in every language"""
    from complist import px
    n = 0
    for lang in frchoose.LANGS:
        t = frchoose.texts(lang)                            # (asserts charset / widths / sizes itself)
        if set(t) != set(frchoose.texts('it')):
            return False, f'{lang}: symbols {sorted(t)}'
        if sum(len(v) for v in t.values()) > frchoose.STR_BACK - frchoose.BSS_BACK:
            return False, f'{lang}: strings past their room'
        n += len(t)
    widest = max(px(x) for lang in frchoose.LANGS for x in frchoose.MSG[lang])
    return True, f'{n} string blocks in 4 languages, widest message {widest} px of {frchoose.G_MSG[2]}'


def test_frchoose_menu_layout():
    """the packed menu follows frchoose.c's entry numbers; boxes inside the 320 x 200 screen and not overlapping; the
    cursor links form the page's grid (venue <-> club in a row, rows up / down, CONTINUE below, the level above)"""
    src = frchoose.menu(D)
    ents = [e for e in src.split('    dw 0\n') if e.strip()]
    if len(ents) != NE:
        return False, f'{len(ents)} entries, frchoose.c has {NE}'
    box, links = [], {}
    for i, e in enumerate(ents):
        x, y, w, h = map(int, re.match(r'\s*dw (-?\d+), (\d+), (\d+), (\d+)', e).groups())
        if x < 0 or y < 0 or x + w > 320 or y + h > 200:
            return False, f'entry {i} off screen'
        box.append((x, y, w, h))
        m = re.search(r'dw 2\n\s*db (.+)', e)
        if m:
            links[i] = [None if v == '0FFh' else int(v) for v in m.group(1).split(', ')]
    for i in range(NE):
        for j in range(i):
            a, b = box[i], box[j]
            if a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]:
                return False, f'entries {j} and {i} overlap'
    E, GO, LV = D['FC_E_ROW'], D['FC_E_GO'], D['FC_E_LVL']
    sel = {LV, GO} | {E + 4 * k for k in range(4)} | {E + 4 * k + 1 for k in range(4)}
    if set(links) != sel:
        return False, f'selectable entries {sorted(links)}'
    for i, (l, r, u, d) in links.items():
        for t, back in ((l, 1), (r, 0), (u, 3), (d, 2)):
            if t is not None and t not in sel:
                return False, f'entry {i} links to {t}, not selectable'
    for k in range(4):
        if links[E + 4 * k][1] != E + 4 * k + 1 or links[E + 4 * k + 1][0] != E + 4 * k:
            return False, f'row {k}: venue <-> club'
        if links[E + 4 * k + 1][3] != (E + 4 * k + 5 if k < 3 else GO):
            return False, f'row {k}: down'
    if links[GO][2] != E + 13 or links[LV][3] != E + 1:
        return False, 'CONTINUE / level links'
    if box[D['FC_E_LEG']][1] >= box[D['FC_E_LVLL']][1] or box[D['FC_E_LEG']][0] > 16:
        return False, 'the legend is not above the rows, top left (CONVENTIONS 5)'
    return True, f'{NE} entries, {len(sel)} selectable, no overlap, legend top left'


def test_frchoose_page():
    """frc_choose shows the page once; what it paints is the state: 4 club names, the band box's colour, the 1-5
    figure = fr_level, the legend = only the colours painted; the level row, the browser's club, a duplicate (the
    message, nothing replaced), the venue swap, ESCI in the browser, FIRE on a chosen club = back to automatic;
    CONTINUE hands back fr_pick's own inputs for exactly what was shown"""
    blob, world, clubs, names, me, page = setup(3)
    if page.rc:
        return False, f'reference page refused {page.rc}'
    return _page(blob, world, clubs, names, me, page)


def _page(blob, world, clubs, names, me, page):
    lib = T.lib()
    out = {}

    def script(g):
        s = g.sel
        nm = (ctypes.c_char * D['FC_NL'] * 4).in_dll(g.l, 'FC_NAME')
        lv = (ctypes.c_char * 2 * 4).in_dll(g.l, 'FC_LV')
        out['a'] = self_check(g, s, nm, lv)
        g.fire_level()                                      # MIX -> EASY
        out['lvl'] = s.level
        out['b'] = self_check(g, s, nm, lv)
        free = [w for w in clubs if w not in list(s.out.word) and w != me]
        out['picked'] = g.pick(2, free[0])
        out['c'] = self_check(g, s, nm, lv) or (None if s.club[2] == free[0] and s.out.word[2] == free[0] else 'club not set')
        out['chosen_col'] = g.col(D['FC_E_ROW'] + 4 * 2 + 1)
        out['dup'] = (g.pick(1, free[0]), g.trace() >> 1, s.club[1])
        g.l.fc_venue(0)
        out['ven'] = s.venues
        out['abort'] = (g.pick(3, None), s.club[3])
        out['clear'] = (g.pick(2, free[1]), s.club[2])      # (FIRE on a chosen club clears it: no browser)

    def self_check(g, s, nm, lv):
        used = set()
        for k in range(4):
            w, b = s.out.word[k], s.out.band[k]
            bi = 1 if b == T.SIMILAR else 0 if b in (T.STRONGER, T.FAR_UP) else 2
            used.add(bi)
            if nm[k].value.decode() != names[w]:
                return f'row {k}: name {nm[k].value} for {w:#x}'
            if lv[k].value.decode() != str(lib.fr_level(blob, len(blob), world, w)):
                return f'row {k}: level {lv[k].value}'
            if g.col(D['FC_E_ROW'] + 4 * k + 2) != (D['FC_C_STRONG'], D['FC_C_SIMIL'], D['FC_C_WEAK'])[bi]:
                return f'row {k}: band colour'
            if g.col(D['FC_E_ROW'] + 4 * k + 1) != (D['FC_C_CHOSEN'] if s.club[k] != NONE else D['FC_C_AUTO']):
                return f'row {k}: club colour'
        if any(c != NONE for c in list(s.club)):
            used.add(3)                                     # (the chosen club's box)
        leg = [D['FC_E_LEG'] + k for k in range(3)] + [D['FC_E_LEGC']]
        if [g.hidden(e) for e in leg] != [0 if k in used else 1 for k in range(4)]:
            return 'legend != the colours painted (CONVENTIONS 6)'
        xs = [struct.unpack_from('<H', g.ent(e), 0x14)[0] for k, e in enumerate(leg) if k in used]
        if xs != [D['FC_LEG_X'] + D['FC_LEG_DX'] * j for j in range(len(xs))]:
            return f'legend not packed from the left: {xs}'
        return None
    g = Game(names, script)
    given, ven = g.choose(page.ctx)
    for k in 'abc':
        if out.get(k):
            return False, f'paint {k}: {out[k]}'
    if g.shown != 1 or out['lvl'] != S.EASY or not out['picked'] or out['chosen_col'] != D['FC_C_CHOSEN']:
        return False, f'{out}'
    if out['dup'][0] is not True or out['dup'][1] != S.M_DUP or out['dup'][2] != NONE:
        return False, f'duplicate: {out["dup"]}'
    if bin(out['ven']).count('1') != 2 or ven != out['ven']:
        return False, f'venues {out["ven"]:#x} -> {ven:#x}'
    if out['abort'] != (True, NONE) or out['clear'] != (False, NONE):
        return False, f'abort / clear: {out["abort"]} {out["clear"]}'
    exp = [S.FILL[S.EASY]] * 4
    if given != exp or page.frst[S.ST_OFF] >> S.ST_SHIFT != S.EASY:
        return False, f'given {given} level bits {page.frst[S.ST_OFF] >> S.ST_SHIFT}'
    rc, o = page.pick(given, ven)
    return rc == 0, 'page painted from the state (names, levels, colours, legend); level, club, duplicate, venue ' \
                    'swap, ESCI, clear; CONTINUE hands back the level + the swapped venues, fr_pick accepts them'


def test_frchoose_no_page():
    """no page - given / venues untouched, FC_TRACE 0, FR_ST untouched: under SWOS++, and when the opening state is
    refused (the club not in the table)"""
    blob, world, clubs, names, me, page = setup(4, level=S.HARD)
    g = Game(names, swospp=0x00)
    before = bytes(page.frst)
    r = g.choose(page.ctx)
    if g.shown or r != ([NONE] * 4, 0xFF) or g.trace() or bytes(page.frst) != before:
        return False, f'SWOS++: shown {g.shown} {r}'
    bad = S.Page(blob, world, word(200, 0))
    g = Game(names)
    r = g.choose(bad.ctx)
    if g.shown or r != ([NONE] * 4, 0xFF) or g.trace():
        return False, f'club not in the table: shown {g.shown} {r}'
    g = Game(names)
    r = g.choose(page.ctx)
    return g.shown == 1 and g.trace() == 1 and r[0] == [S.FILL[S.HARD]] * 4, 'SWOS++ and a refused opening state: no page; else shown once (FC_TRACE 1)'


def test_frchoose_exe_object():
    """the band's object with the exe's flags at -Oz: the only undefined symbols are the externs frchoose.py gives,
    no libc call, stack of every function small (the game's stack is 4 KB), size inside the band"""
    import cobj
    flags = ['-Oz' if f == '-Os' else f for f in cobj.CFLAGS] + ['-fno-zero-initialized-in-bss']
    res = {}
    for own in (False, True):
        o = os.path.join(_TMP, f'fc{own}.o')
        r = subprocess.run(['clang', *flags, '-fstack-usage', *(['-DFRC_OWN_PICK'] if own else []), '-c',
                            os.path.join(TOOLS, 'frchoose.c'), '-o', o], capture_output=True, text=True)
        if r.returncode:
            return False, r.stderr[-300:]
        und = set(subprocess.run(['nm', '-u', o], capture_output=True, text=True).stdout.split())
        und -= {'U'}
        want = {'DREG', 'SWOSPP', 'MENU', 'GTP', 'FC_SHOW', 'FC_S_LVL', 'FC_S_BAND', 'FC_S_VEN', 'FC_S_MSG'}
        want |= set() if own else {'fr_pick', 'fr_level', 'fr_given'}
        if und != want:
            return False, f'own={own}: undefined {sorted(und ^ want)}'
        su = o[:-2] + '.su'
        stack = max(int(l.split('\t')[1]) for l in open(su)) if os.path.exists(su) else None
        sz = sum(s['size'] for s in cobj._elf(open(o, 'rb').read()) if s['flags'] & 2 and s['type'] != 8)
        res[own] = (sz, stack)
    room = 0x1000 - frchoose.STR_BACK - 8
    if res[False][0] > room - 1000:                         # (the glue + menu take ~950 B)
        return False, f'C {res[False][0]} B: no room left for the glue in the 0x1000 band'
    if any(v[1] is not None and v[1] >= 256 for v in res.values()):
        return False, f'stack {res}'
    return True, f'with FRND\'s pick: {res[False][0]} B (stack max {res[False][1]}), interim own pick: {res[True][0]} B'


def test_frchoose_list():
    """the club list's colours while the page browses for a row: every listed club painted by the band it would have
    in that row, grey when fr_pick would refuse it (a club already chosen in another row, the B team); hidden entries
    and the entries outside 7..54 untouched; outside the page (FC_K = 4) nothing is painted"""
    blob, world, clubs, names, me, page = setup(5)
    b2 = next(w for w in clubs if w != me)
    page = S.Page(blob, world, me, self2=b2)
    if page.rc:
        return False, f'reference page refused {page.rc}'
    out = {}
    L0, L1 = D['FC_LIST0'], D['FC_LIST1']

    def fill(g, ws):
        for i in range(64):
            struct.pack_into('<H', g.menu, HDR + ESZ * i + 4, 1)
            struct.pack_into('<H', g.menu, HDR + ESZ * i + 0x1E, 0x55)
        for i, w in enumerate(ws):
            o = HDR + ESZ * (L0 + i)
            struct.pack_into('<H', g.menu, o + 4, 0)
            struct.pack_into('<I', g.menu, o + 0x26, (ctypes.addressof(g.recs[w]) + 5) & 0xFFFFFFFF)

    def script(g):
        s = g.sel
        free = [w for w in clubs if w not in list(s.out.word) and w not in (me, b2)]
        g.pick(0, free[0])                                  # row 0 = a chosen club
        ws = [free[0], b2] + free[1:40]
        fill(g, ws)
        g.l.fc_list()                                       # outside a browse: nothing
        out['idle'] = all(g.col(i) == 0x55 and g.hidden(i) for i in range(1, L0)) and \
            all(g.col(L0 + i) == 0x55 for i in range(len(ws)))
        if g.l.fc_club(2) != 1:                             # FIRE on row 2 (automatic): the browser opens
            out['err'] = 'row 2 did not open the browser'
            return
        g.l.fc_list()
        ref = S.Page(blob, world, me, self2=b2)
        ref.club(0, free[0])
        cols = (D['FC_C_STRONG'], D['FC_C_SIMIL'], D['FC_C_WEAK'])
        grey, seen = 0, set()
        for i, w in enumerate(ws):
            rc, band = ref.trial(2, w)
            want = D['FC_C_NO'] if rc else cols[1 if band == T.SIMILAR else 0 if band in (T.STRONGER, T.FAR_UP) else 2]
            grey += bool(rc)
            if g.col(L0 + i) != want:
                out['err'] = f'entry {L0 + i} club {w:#x}: colour {g.col(L0 + i):#x}, want {want:#x} (rc {rc} band {band})'
                return
            if not rc:
                seen.add(cols.index(want))
        j = 0                                               # the game's legend row = the bands on the list, packed
        for b in range(3):
            eb, et = D['FC_LL_BOX'] + b, D['FC_LL_TEXT'] + b
            x = lambda e: struct.unpack_from('<H', g.ent(e), 0x14)[0]
            if (g.hidden(eb), g.hidden(et)) != ((0, 0) if b in seen else (1, 1)):
                out['err'] = f'list legend {b}: hidden {g.hidden(eb)} / {g.hidden(et)}, bands on the list {seen}'
                return
            if b in seen:
                if (g.col(eb), x(eb), x(et)) != (cols[b], D['FC_LL_X'] + D['FC_LL_DX'] * j,
                                                 D['FC_LL_X'] + D['FC_LL_DX'] * j + D['FC_LL_TX']):
                    out['err'] = f'list legend {b}: colour {g.col(eb):#x} x {x(eb)} / {x(et)} (shown as {j})'
                    return
                j += 1
        out['leg'] = sorted(seen)
        out['n'], out['grey'] = len(ws), grey
        out['rest'] = all(g.col(i) == 0x55 for i in [0] + list(range(D['FC_LL_TEXT'], L0)) + list(range(L0 + len(ws), 64)))
        struct.pack_into('<I', g.dreg, 0, 0xFFFF)
        g.l.fc_picked()                                     # ESCI
        fill(g, ws)
        g.l.fc_list()
        out['after'] = all(g.col(i) == 0x55 and g.hidden(i) for i in range(1, L0)) and \
            all(g.col(L0 + i) == 0x55 for i in range(len(ws)))
    g = Game(names, script)
    g.choose(page.ctx)
    if out.get('err'):
        return False, out['err']
    if not (out.get('idle') and out.get('rest') and out.get('after')) or out['grey'] < 2 or L1 != 55:
        return False, f'{out}'
    return True, f'{out["n"]} listed clubs painted by band ({out["grey"]} grey: chosen elsewhere / B team), the ' \
                 f'legend row = bands {out["leg"]} packed; nothing ' \
                 f'painted outside a browse'
