"""cf_italy (4.2 rc4, MC 21/11, internal/handoff/mc-outbox-20261121-cfitaly.md): last season's places of a SECOND league
file. gplay.c's cf_cap_c kept one file's places (CF_ST.file = the first club's file of the season's captures); in S7
Italy (102 = A/B/C, 144 = D) a Serie D career captures 144 first, so after D -> C the first Coppa Italia Serie C (file
102) had no places: cf_build seeded its entrants in the file's order. The fix: item 'CB' (struct cb_state) keeps the
second file; cf_build / sc_rank / sc_place / cf_last1 read the slot of the file they ask for (cf_ranks).
gplay.c built natively (as test_cflast1), GP_S7=0; a wrapper exposes cf_build's list.
Shape: CF_TAB with two dts - file 102 (divisions 0 A, 1 B, 2 C: levels 0, 1, 2; C = ordinals 10..17) and file 144
(division 0 = Serie D, level 3: ordinals 0..5); one cup (id CUP, the Coppa Italia Serie C): division 2 of file 102,
8 entrants, no byes. Season 5's captures: D (144) first, then C (102) with places 15, 12, 17, 10, 13, 16, 11, 14.
- red (REF_COMMIT, today's gplay.c): season 6's cup = the file's order 10..17 (unranked);
- fixed: the cup = the C table's order; CF_ST byte-identical to the reference (144's places; 'CF' unchanged);
  sc_rank (C places) and the 144 places still read;
- an old save (CB zeroed after the captures, CF kept): the file's order, as before;
- not last season (CF season + 1 != the cup's season): the file's order;
- other leagues' files captured before 102 (the season end captures every league: England 101 first in World 2026-27):
  skipped - CB keeps the TWIN of CF's file (CF_TAB's twins, 102 / 144); a CF_TAB without twins: CB never filled."""
import ctypes
import os
import struct
import subprocess
import tempfile

import test_cflast1 as C1

REF_COMMIT = os.environ.get('CFITALY_REF', '1335b2c')      # (42-int before the fix)
FA, FD, FX = 102, 144, 77
CUP = 0x31
C_ORDS = tuple(range(10, 18))
C_TABLE = (15, 12, 17, 10, 13, 16, 11, 14)
D_TABLE = (3, 0, 5, 1, 4, 2)
A_TABLE = (2, 0, 3, 1)
WRAP = '\nunsigned t_list(unsigned id, unsigned s, unsigned ct, unsigned short *o) { return (unsigned)cf_build((int)id, (int)s, ct, o); }\n' \
       'int tq_rank(unsigned short w) { return sc_rank(w); }\nunsigned tq_place(int f, int p) { return sc_place(f, p); }\n'


def _cftab():
    cup = bytes((CUP, 8, 1, 0)) + bytes((2, 8, 0))                     # (id, n, groups, dt 0; division 2: 8, 0 byes)
    lv_a = [0, 1, 2] + [7] * 13
    pa = [(o, 0) for o in range(0, 4)] + [(o, 1) for o in range(4, 10)] + [(o, 2) for o in C_ORDS]
    dta = struct.pack('<HBH', 0, FA, len(pa)) + bytes(lv_a) + b''.join(bytes(p) for p in pa)
    lv_d = [3] + [7] * 15
    pd = [(o, 0) for o in range(6)]
    dtd = struct.pack('<HBH', 256, FD, len(pd)) + bytes(lv_d) + b''.join(bytes(p) for p in pd)
    return bytes((1, 0, 1)) + cup + bytes((2,)) + dta + dtd + bytes((1, FA, FD))     # (twins: 102 / 144)


def _diy(name, f, ords):
    b = bytearray(C1._diy(name, ords))
    for k, o in enumerate(ords):
        struct.pack_into('<H', b, 0x12D + 2 * k, f | o << 8)
    return bytes(b)


def _lib(d, text, tag):
    L = C1._lib(d, text + WRAP, tag)
    L.cf_cap_c.argtypes = (ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32)
    L.tq_rank.argtypes = (ctypes.c_uint16,)
    L.tq_place.argtypes = (ctypes.c_int, ctypes.c_int)
    L.t_list.argtypes = (ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint16))
    return L


def _cap(L, keep, season=5, third=False, old=False, tab=True):
    for n, z in (('CF_ST', 260), ('CB_ST', 258)):
        try:
            ctypes.memset(ctypes.addressof(ctypes.c_uint8.in_dll(L, n)), 0, z)
        except ValueError:
            pass                                    # (the reference has no CB_ST)
    if tab:
        ctypes.c_void_p.in_dll(L, 'CF_TAB').value = ctypes.addressof(keep['tab'])
    ctypes.c_void_p.in_dll(L, 'GP_SLT').value = ctypes.addressof(keep['slt'])
    ctypes.c_uint16.in_dll(L, 'GP_MGR').value = FD | 3 << 8           # (a Serie D career club)
    L.cf_cap_c(0, keep['d'], season)
    L.cf_cap_c(0, keep['x'], season)                 # (another country's league between them: the season end captures
    if third:                                        #  every league - World 2026-27: England 101 before Italy 102)
        L.cf_cap_c(0, keep['x2'], season)
    L.cf_cap_c(2, keep['c'], season)
    L.cf_cap_c(0, keep['a'], season)
    if old:                                          # (a save from before 'CB': the item zeroed at load)
        ctypes.memset(ctypes.addressof(ctypes.c_uint8.in_dll(L, 'CB_ST')), 0, 258)


def _list(L, season):
    o = (ctypes.c_uint16 * 64)()
    n = L.t_list(CUP, season, 0xFFFF, o)
    return [o[i] >> 8 for i in range(n)] if n else None


def test_cfitaly():
    d = tempfile.mkdtemp(prefix='cfit')
    keep = {'tab': ctypes.create_string_buffer(_cftab(), 256), 'tab0': ctypes.create_string_buffer(_cftab()[:-3], 256), 'slt': ctypes.create_string_buffer(4096),
            'd': _diy(b'SERIE D', FD, D_TABLE), 'c': _diy(b'SERIE C', FA, C_TABLE), 'x': _diy(b'OTHER', FX, (1, 2)), 'x2': _diy(b'OTHER2', FX + 1, (3, 4)),
            'a': _diy(b'SERIE A', FA, A_TABLE)}
    errs, notes = [], []
    cur = open(os.path.join(C1.TOOLS, 'gplay.c')).read()
    L = _lib(d, cur, 'fix')
    ref = subprocess.run(['git', '-C', C1.TOOLS, 'show', f'{REF_COMMIT}:tools/gplay.c'], capture_output=True, text=True)
    cf_ref = None
    if ref.returncode:
        notes.append(f'red SKIPPED ({REF_COMMIT} not in this repo)')
    else:
        dr = os.path.join(d, 'ref')
        os.makedirs(dr)
        gx = subprocess.run(['git', '-C', C1.TOOLS, 'show', f'{REF_COMMIT}:tools/gplx.c'], capture_output=True, text=True)
        open(os.path.join(dr, 'gplx.c'), 'w').write(gx.stdout)
        R = _lib(dr, ref.stdout, 'ref')
        _cap(R, keep)
        got = _list(R, 6)
        if got != list(C_ORDS):
            errs.append(f'red: {REF_COMMIT} gave {got}, expected the unranked file order {list(C_ORDS)}')
        else:
            notes.append(f'red: {REF_COMMIT} seeds the C cup in the file order (no places for 102)')
        if R.tq_rank(FA | A_TABLE[0] << 8) != 9:
            errs.append('red: the reference ranks a 102 club with CF on 144')
        cf_ref = ctypes.string_at(ctypes.addressof(ctypes.c_uint8.in_dll(R, 'CF_ST')), 260)
    _cap(L, keep)
    got = _list(L, 6)
    if got != list(C_TABLE):
        errs.append(f'fixed: the C cup {got} != last season\'s C table {list(C_TABLE)}')
    rk = (L.tq_rank(FA | A_TABLE[0] << 8), L.tq_rank(FA | A_TABLE[2] << 8), L.tq_rank(FA | C_TABLE[0] << 8))
    if rk != (1, 3, 9):                 # (sc_rank / sc_place: the top division only, level 0; C = 9)
        errs.append(f'sc_rank: A 1st / 3rd, C 1st = {rk} (want 1, 3, 9)')
    if L.tq_place(FA, 1) != (FA | A_TABLE[0] << 8):
        errs.append(f'sc_place(102, 1) = {L.tq_place(FA, 1):#06x} (want the Serie A champion, from CB)')
    cf = ctypes.string_at(ctypes.addressof(ctypes.c_uint8.in_dll(L, 'CF_ST')), 260)
    if cf_ref is not None and cf != cf_ref:
        errs.append('CF_ST differs from the reference (the item must stay byte-identical)')
    if cf[3] != FD or [cf[4 + o] & 31 for o in D_TABLE] != list(range(1, 7)):
        errs.append(f'CF_ST: file {cf[3]}, D places {[cf[4 + o] for o in D_TABLE]}')
    cb = ctypes.string_at(ctypes.addressof(ctypes.c_uint8.in_dll(L, 'CB_ST')), 258)
    if cb[0] != 6 or cb[1] != FA or [cb[2 + o] for o in C_TABLE] != [k | 2 << 5 for k in range(1, 9)] \
            or [cb[2 + o] for o in A_TABLE] != [1, 2, 3, 4]:
        errs.append(f'CB_ST: season {cb[0]} file {cb[1]} C places {[cb[2 + o] for o in C_TABLE]} (want season + 1 = 6, '
                    f'102, place | level 2 << 5)')
    _cap(L, keep, old=True)
    if _list(L, 6) != list(C_ORDS):
        errs.append('old save (CB zeroed): not the file order')
    _cap(L, keep)
    if _list(L, 7) != list(C_ORDS):
        errs.append('season 7 (places of season 5): not the file order')
    _cap(L, keep, third=True)
    cb = ctypes.string_at(ctypes.addressof(ctypes.c_uint8.in_dll(L, 'CB_ST')), 258)
    if cb[1] != FA or _list(L, 6) != list(C_TABLE):
        errs.append(f'two other files first: CB file {cb[1]} (want the twin {FA}), C cup {_list(L, 6)} (want the C table)')
    ctypes.c_void_p.in_dll(L, 'CF_TAB').value = ctypes.addressof(keep['tab0'])
    _cap(L, keep, tab=False)
    if _list(L, 6) != list(C_ORDS):
        errs.append('a CF_TAB without twins: CB filled (want the file order, as before)')
    return not errs, '; '.join(errs) or ('; '.join(notes) + '; fixed: C cup = last season\'s C table, CF_ST identical '
                                         '(144), CB_ST 102 places, sc_rank / sc_place read the Serie A champion from CB (red: 9); '
                                         'other leagues captured between them skipped (twins: CB = 102); old save / stale '
                                         'season / no twins -> the file order')


def test_cfitaly_twins():
    """cupsf.table's twins come from the packs' data (MC 22/11): every league over two team files once, in pack order;
    a league over 3+ files and a file in two twins refused (mkseason.PackError); one-file leagues add none. Fake packs
    (cupsf.pack_cups / dt_bytes stubbed: the twins only)."""
    import sys
    sys.path.insert(0, C1.TOOLS)
    import cupsf
    import mkseason

    class P:
        def __init__(self, i, files, world=5):
            self.meta, self.world, self.league, self._f = {'id': i}, world, {'x': 1}, files

        def league_files(self):
            return self._f
    saved = (mkseason.packs, cupsf.pack_cups, cupsf.dt_bytes, cupsf.year)
    cupsf.pack_cups = lambda pk, f: ([(0x31, 2, [(0, 2, 0)])], f)
    cupsf.dt_bytes = lambda pk, f: bytes((0, 0, f, 0, 0)) + bytes(16)
    cupsf.year = lambda w: 2026
    errs = []
    try:
        def tw(packs):
            mkseason.packs = lambda: packs
            t = cupsf.table(5)
            c = t[3:]
            for _ in range(t[2]):
                c = c[4 + 3 * c[2]:]
            d = c[1:]
            for _ in range(c[0]):
                d = d[21 + 2 * (d[3] | d[4] << 8):]
            return [(d[1 + 2 * k], d[2 + 2 * k]) for k in range(d[0])]
        got = tw([P('eng', [101]), P('ita', [102, 144]), P('esp', [103, 150]), P('other', [104], world=4)])
        if got != [(102, 144), (103, 150)]:
            errs.append(f'two two-file leagues: twins {got}')
        if tw([P('eng', [101])]) != []:
            errs.append('one-file leagues: twins not empty')
        for bad, why in (([P('x', [102, 144, 145])], '3 files'), ([P('a', [102, 144]), P('b', [144, 150])], 'file in two twins')):
            try:
                tw(bad)
                errs.append(f'{why}: not refused')
            except mkseason.PackError:
                pass
    finally:
        mkseason.packs, cupsf.pack_cups, cupsf.dt_bytes, cupsf.year = saved
    return not errs, '; '.join(errs) or ('twins from the packs: two two-file leagues -> both once in pack order, other '
                                         'worlds / one-file leagues none; 3 files and a file in two twins refused')
