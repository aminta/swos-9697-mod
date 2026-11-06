"""XW groundwork (notes/engine/xw-design.md): tools/xw.c's pure functions, compiled for the host (clang -shared) and
called through ctypes - no exe, no snapshot.

- xw_alloc: a visitor file gets the first free number of 220..253, the same file the same number, 34 files at most
  (the 35th refused, 0), a bad file (0, 220+) refused;
- xw_file: the number back to its file, 0 for a number not mapped;
- xw_wm_put / xw_wm_get: the DIY tail 'WM' v2 (len 2 + 3k: host, visitor, (r, f, flags) x k) round trip, empty and
  full maps; a mixing-A tail ('WM' 1, world) reads as version 1, the world as host; anything else reads as 0 (no
  block): a short / long length, a cut file, k > 34, r outside 220..253, a repeated r or f, f 0 / 220+, another tag."""
import ctypes
import os
import subprocess
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(TOOLS, 'xw.c')


class Map(ctypes.Structure):
    _fields_ = [('host', ctypes.c_uint8), ('vis', ctypes.c_uint8), ('k', ctypes.c_uint8), ('pad', ctypes.c_uint8),
                ('r', ctypes.c_uint8 * 34), ('f', ctypes.c_uint8 * 34), ('fl', ctypes.c_uint8 * 34)]


def _lib():
    out = os.path.join(tempfile.mkdtemp(prefix='xw'), 'xw.dylib')
    subprocess.run(['clang', '-shared', '-O2', '-Wall', '-Werror', '-o', out, SRC], check=True)
    lib = ctypes.CDLL(out)
    for fn in ('xw_alloc', 'xw_file', 'xw_wm_put', 'xw_wm_get'):
        getattr(lib, fn).restype = ctypes.c_uint32
    return lib


def test_xw():
    x = _lib()
    m = Map()
    errs = []
    x.xw_clear(ctypes.byref(m), 5, 4)
    got = [x.xw_alloc(ctypes.byref(m), f) for f in (105, 112, 105, 131)]
    if got != [220, 221, 220, 222] or m.k != 3:
        errs.append(f'alloc 105 112 105 131 -> {got}, k {m.k}')
    if [x.xw_alloc(ctypes.byref(m), f) for f in (0, 220, 255)] != [0, 0, 0] or m.k != 3:
        errs.append('a bad file was mapped')
    if [x.xw_file(ctypes.byref(m), r) for r in (220, 221, 222, 223, 105)] != [105, 112, 131, 0, 0]:
        errs.append('xw_file')
    full = Map()
    x.xw_clear(ctypes.byref(full), 4, 5)
    rs = [x.xw_alloc(ctypes.byref(full), f) for f in range(101, 135)]
    if rs != list(range(220, 254)) or x.xw_alloc(ctypes.byref(full), 135) != 0 or \
            x.xw_alloc(ctypes.byref(full), 134) != 253:
        errs.append(f'34 files {rs[:3]}..{rs[-2:]}, the 35th not refused / a mapped one lost')

    def put(mp):
        b = (ctypes.c_uint8 * 128)()
        n = x.xw_wm_put(ctypes.byref(mp), b)
        return bytes(b[:n])

    def get(t):
        b = (ctypes.c_uint8 * max(len(t), 1)).from_buffer_copy(t or b'\0')
        o = Map()
        v = x.xw_wm_get(b, len(t), ctypes.byref(o))
        return v, o

    m.fl[1] = 7
    for tag, mp in (('3 files', m), ('34 files', full)):
        t = put(mp)
        v, o = get(t)
        if t[:5] != bytes([0x57, 0x4D, 2 + 3 * mp.k, mp.host, mp.vis]) or len(t) != 5 + 3 * mp.k:
            errs.append(f'{tag}: tail {t[:8].hex()} ({len(t)} B)')
        if v != 2 or bytes(o) != bytes(mp):
            errs.append(f'{tag}: read back version {v}, map {"same" if bytes(o) == bytes(mp) else "differs"}')
    e = Map()
    x.xw_clear(ctypes.byref(e), 5, 4)
    v, o = get(put(e))
    if put(e) != b'WM\x02\x05\x04' or v != 2 or o.k != 0 or (o.host, o.vis) != (5, 4):
        errs.append(f'empty map: {put(e).hex()} -> {v}')
    v, o = get(b'WM\x01\x04')
    if v != 1 or (o.host, o.vis, o.k) != (4, 0, 0):
        errs.append(f'mixing A tail: version {v}, host {o.host}')
    t = put(m)
    bad = {'cut': t[:-1], 'long': t + b'\0', 'len short': t[:2] + bytes([t[2] - 3]) + t[3:],
           'len not 2+3k': t[:2] + bytes([t[2] + 1]) + t[3:] + b'\0', 'tag': b'WX' + t[2:], 'empty': b'',
           'r 219': t[:5] + b'\xdb' + t[6:], 'r 254': t[:5] + b'\xfe' + t[6:], 'f 0': t[:6] + b'\0' + t[7:],
           'f 220': t[:6] + b'\xdc' + t[7:], 'r twice': t[:8] + t[5:6] + t[9:], 'f twice': t[:9] + t[6:7] + t[10:],
           'k 35': b'WM' + bytes([2 + 105, 4, 5]) + b''.join(bytes([220 + i % 34, 101 + i, 0]) for i in range(35)),
           'v1 cut': b'WM\x01'}
    for tag, tt in bad.items():
        v, _ = get(tt)
        if v != 0:
            errs.append(f'{tag}: read as version {v}')
    return not errs, '; '.join(errs) or (f'alloc 220.. per file (34 max, bad files refused), WM v2 round trip (0 / 3 / '
                                         f'34 files, {len(put(full))} B max), mixing A = v1, {len(bad)} bad tails = 0')
