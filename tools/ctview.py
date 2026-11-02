"""COPPE CONTINENTALI / CONTINENTAL CUPS (4.0.6, Gianmarco's ask; Davide GO 02/11): the other confederations' club
cups of a world career, viewed without taking part. VISUAL. COMPETIZ.'s entry 9 (World 2026-27 careers) -> a menu of
the confederations (the career club's first) -> fmtpage's page: each cup of that confederation from a new page, its
holder, every round in calendar order (ties with '>' before the club that went through, groups by final place), the
winner; a round not yet drawn, or drawn and not yet over, TO BE PLAYED. No scores: the conti matches have no goals.

ctview.c (obj3) replays the edition in progress (conti.c ct_resume: the run a load does, nothing changed) and writes
the page's text; this module builds its table (CV_TAB: texts in the exe's language, font widths, the associations'
files and confederations, cup and round names) and the native test.

    python3 tools/ctview.py --test [lang]      # the pages along conti's test seasons (career club CONTI_TEST_MANAGER)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conti        # noqa: E402

TEXTS = {   # holder, to be played, winner, group, earlier rounds (season 1), none; the menu entry
    'it': (b'DETENTORE', b'DA GIOCARE', b'VINCITORE', b'GRUPPO', b'TURNI PRECEDENTI GIOCATI PRIMA DELLA STAGIONE',
           b'NESSUNA COPPA IN CORSO', b'COPPE CONTINENTALI'),
    'en': (b'HOLDER', b'TO BE PLAYED', b'WINNER', b'GROUP', b'EARLIER ROUNDS PLAYED BEFORE THE SEASON',
           b'NO CUP IN PROGRESS', b'CONTINENTAL CUPS'),
    'fr': (b'TENANT', b'A JOUER', b'VAINQUEUR', b'GROUPE', b'TOURS PRECEDENTS JOUES AVANT LA SAISON',
           b'AUCUNE COUPE EN COURS', b'COUPES CONTINENTALES'),
    'de': (b'TITELVERTEIDIGER', b'NOCH OFFEN', b'SIEGER', b'GRUPPE', b'FRUHERE RUNDEN VOR DER SAISON GESPIELT',
           b'KEIN POKAL IM GANGE', b'KONTINENTALPOKALE'),
}
CONF_NAMES = {'conmebol': b'CONMEBOL', 'concacaf': b'CONCACAF', 'afc': b'AFC', 'caf': b'CAF', 'ofc': b'OFC',
              'fifa': b'FIFA'}


def round_name(r, lang):
    """A format round's long name in the exe's language (rnames: its own names, else CT_NEW, else the game's)."""
    import rnames
    own = r.get('names')
    if own:
        return (own.get(lang) or own['en'])[0].upper()
    if r['key'] in rnames.CT_NEW[lang]:
        return rnames.CT_NEW[lang][r['key']][0]
    return rnames.NAMES[lang][rnames.CT_KEYS[r['key']] - rnames.N_OLD][0]


def _spec_access(spec):
    """(nrd per cup, [(assoc, cup)] of the access entries) from conti.load()'s spec (conti.c parse())."""
    ncup, p = spec[0], 4
    nrd = []
    for _ in range(ncup):
        nrd.append(spec[p])
        p += 4 + spec[p] * conti.RB
    nacc = struct.unpack_from('<H', spec, p)[0]
    acc = [(spec[p + 2 + 4 * i], spec[p + 3 + 4 * i]) for i in range(nacc)]
    return nrd, acc


def table(lang, confs, files=None, words=None):
    """CV_TAB's bytes (ctview.c's layout) and the confederations' order numbers."""
    import complist
    spec, assocs, cups = conti.load(list(confs), files, words)
    nrd, acc = _spec_access(spec)
    fmt = {}
    for conf in confs:
        for c in conti._read(conf, 'format')['cups']:
            fmt[conf, c['key']] = c
    cnum = {conf: i for i, conf in enumerate(conti.CONFS)}
    aconf = [0xFF] * len(assocs)
    for a, ci in acc:
        if a < len(assocs) and aconf[a] == 0xFF:
            aconf[a] = cnum[cups[ci][0]]
    afile = [0 if a.startswith('g:') else (files or {}).get(a, 100 + i) & 0xFF for i, a in enumerate(assocs)]
    strs, body = bytearray(), []
    pool = {}

    def s(t):                           # a string's offset (shared), filled in below
        if t not in pool:
            pool[t] = len(strs)
            strs.extend(t + b'\0')
        return pool[t]
    tx = TEXTS[lang]
    toff = [s(t) for t in tx[:6]] + [0, 0]
    for ci, (conf, key) in enumerate(cups):
        c = fmt[conf, key]
        rounds = c['rounds']
        assert len(rounds) == nrd[ci], (conf, key, len(rounds), nrd[ci])
        nm = (c['names'].get(lang) or c['names']['en'])[0].upper().encode('latin1')
        for t in [nm] + [round_name(r, lang).encode('latin1') for r in rounds]:
            assert complist.px(t.decode('latin1')) <= 298 and all(ch in complist.FONT for ch in t.decode('latin1')), (lang, t)
        body.append((cnum[conf], nrd[ci], s(nm), [s(round_name(r, lang).encode('latin1')) for r in rounds]))
    for t in tx:
        assert all(ch in complist.FONT for ch in t.decode('latin1')), (lang, t)
    head = 16 + 64 + 2 + 2 * len(assocs) + sum(4 + 2 * n for _, n, _, _ in body)
    out = bytearray(struct.pack('<8H', *[head + o for o in toff[:6]] + [0, 0]))
    out += bytes(min(255, complist.px(chr(0x20 + k))) if chr(0x20 + k) in complist.FONT else 6 for k in range(64))
    out += bytes((len(assocs), len(cups))) + bytes(afile) + bytes(aconf)
    for cf, n, nmo, ro in body:
        out += bytes((cf, n)) + struct.pack('<H', head + nmo) + b''.join(struct.pack('<H', head + o) for o in ro)
    assert len(out) == head
    return bytes(out + strs), spec


def test(lang='it', confs=('conmebol',)):
    import ctypes
    L = conti._native(('ctview.c',))
    tab, _ = table(lang, confs)
    ctypes.memmove(ctypes.addressof(ctypes.c_ubyte.in_dll(L, 'CV_TAB')), tab, len(tab))
    names = {}
    NAMEF = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_uint32)
    keep = []

    def nm(w):
        b = ctypes.create_string_buffer(names.get(w, f'C{w:04X}').upper().encode()[:17])
        keep.append(b)
        return ctypes.addressof(b)
    cb = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)(nm)
    ctypes.c_void_p.in_dll(L, 'cv_native_name').value = ctypes.cast(cb, ctypes.c_void_p).value
    SEG = (ctypes.c_ubyte * 72).in_dll(L, 'CT_SEG')
    OUTB = (ctypes.c_ubyte * (ctypes.c_uint32 * 3).in_dll(L, 'CT_LAYOUT')[2]).in_dll(L, 'CT_OUT')
    buf = ctypes.create_string_buffer(0x2000)
    L.cv_text.restype = ctypes.c_uint32
    weeks = [int(w) for w in os.environ.get('CTVIEW_WEEKS', '64,80,104,140').split(',')]

    def hook(L2, nms, step):
        names.update(nms)
        for w in weeks:
            snap = bytes(SEG), bytes(OUTB)
            n = L.cv_text(conti.CONFS.index(confs[0]), w, buf, len(buf))
            assert (bytes(SEG), bytes(OUTB)) == snap, f'the view changed the state ({step}, week {w})'
            assert n < len(buf) - 1, 'page text full'
            if os.environ.get('CTVIEW_SHOW') in (step, 'all') or (w == weeks[-1] and step.endswith('start')):
                print(f'=== {step}, week {w} ({n} B)')
                for pg in buf.raw[:n].decode('latin1').split('\f'):
                    print('\n'.join('  | ' + x for x in pg.split('\n')))
                    print('  +' + '-' * 40)
    conti.test(confs, seasons=int(os.environ.get('CTVIEW_SEASONS', 2)), L=L, hook=hook)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--test']:
        test(*(sys.argv[2:3] or ['it']), confs=tuple(sys.argv[3:]) or ('conmebol',))
