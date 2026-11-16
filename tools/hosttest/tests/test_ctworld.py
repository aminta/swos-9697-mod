"""conti.c's world gate (4.2 ctworld, MC 16/11: CT_SDRAW_ERR 0x10301 in worlds 0 / 4). The continental cups' spec is
the World 2026-27 packs'; the glue runs at every career's season end. conti.c ct_wassoc = the associations the ACTIVE
world (CT_W) has; a cup none of whose associations is in the world plays no edition, for every confederation
(ct_wcups), and a field of fewer clubs than groups is no group stage (never the P7 refused path).

Native conti.c (conti._native) on the REAL spec (drawgate.world_spec: the world data), season ends through the game's
own entry points (ct_table / ct_begin / ct_country / ct_go), the holders as the first season end sets them:
  1. worlds 0 (files 0..63, TEAM.000 = Albania included) and 4 (101..132): no refusal, no draw, no entrant, no
     holder, no reserve; the control - conti.c of BASE (42-int before the gate) - refuses 0x10301 on the same input;
  2. world 2026-27: CT_OUT / CT_ED / CT_ST / CT_SEG / CT_IN byte-identical to BASE's, season by season, with a career
     club playing its games;
  3. every confederation in turn out of the world (its files cleared in the spec's world bitmap): its cups sleep,
     the holders' cups it feeds too, the others play, nothing is refused;
  4. a cup of the world whose tables bring no club (the holder alone in the groups): not played, not refused.
Needs the private conti data + the world data (SKIP without)."""
import contextlib
import ctypes
import io
import os
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
BASE = os.environ.get('CTWORLD_BASE', 'd39c4d3')        # (42-int before 42-ctworld: the draws world 2026-27 must keep)
REC = 0x2AC
_C = {}


def _world():
    """(spec, assocs, cups, files) of the world data, or None"""
    if 'w' not in _C:
        try:
            import drawgate
            import conti
            with contextlib.redirect_stdout(io.StringIO()):
                spec = drawgate.world_spec()
                files, words = conti._world_maps(conti.ready())
                _, assocs, cups = conti.load(conti.ready(), files, words)
            _C['w'] = (spec, assocs, cups, files) if files else None
        except Exception as e:                          # (no private data)
            print('SKIP', e)
            _C['w'] = None
    return _C['w']


def _base_lib():
    """conti.c of BASE compiled natively (git), or None"""
    if 'b' not in _C:
        _C['b'] = None
        d = tempfile.mkdtemp()
        root = os.path.dirname(TOOLS)
        ar = subprocess.run(['git', '-C', root, 'archive', BASE, 'tools/conti.c', 'tools/conti.h', 'tools/ctdraw.c',
                             'tools/swce'], capture_output=True)
        if ar.returncode == 0 and subprocess.run(['tar', '-x', '-C', d], input=ar.stdout).returncode == 0:
            import conti
            lib = os.path.join(d, 'base.dylib')
            subprocess.run(['clang', '-O1', '-shared', '-fPIC', '-DNATIVE', '-w', *conti.NATIVE_FLAGS, '-o', lib,
                            os.path.join(d, 'tools', 'conti.c'), os.path.join(d, 'tools', 'ctdraw.c')], check=True)
            _C['b'] = ctypes.CDLL(lib)
    return _C['b']


def _new_lib():
    if 'n' not in _C:
        import conti
        _C['n'] = conti._native()
    return _C['n']


class Run:
    """one library on one spec: season ends as the game makes them"""
    def __init__(self, L, spec, world=None):
        self.L = L
        self.lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
        self.buf = ctypes.create_string_buffer(spec, len(spec))
        ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(self.buf)
        self.size = {'CT_IN': self.lay[0], 'CT_ST': self.lay[1], 'CT_OUT': self.lay[2], 'CT_ED': self.lay[20],
                     'CT_SEG': self.lay[21]}
        for k in ('CT_ED', 'CT_ST', 'CT_IN', 'CT_OUT'):
            ctypes.memset(ctypes.addressof((ctypes.c_ubyte * self.size[k]).in_dll(L, k)), 0, self.size[k])
        for k in ('CT_SDRAW_ERR', 'CT_SDRAW_N', 'CT_SDRAW_HIT'):
            ctypes.c_uint32.in_dll(L, k).value = 0
        if world is not None:
            ctypes.c_ubyte.in_dll(L, 'CT_W').value = world

    def mem(self, k):
        return bytes((ctypes.c_ubyte * self.size[k]).in_dll(self.L, k))

    def u32(self, k):
        return ctypes.c_uint32.in_dll(self.L, k).value

    def holders(self, hs):
        """CT_ST as after the first season end: 'CT', season 0, {cup: (team word, association)}"""
        b = bytearray(self.size['CT_ST'])
        struct.pack_into('<HH', b, 0, 0x5443, 0)
        for c, (w, a) in hs.items():
            struct.pack_into('<HBBII', b, 4 + 12 * c, w, a, 0, 3000, 500)
        ctypes.memmove((ctypes.c_ubyte * len(b)).in_dll(self.L, 'CT_ST'), bytes(b), len(b))

    def season(self, fileset, s, mgr=0, uefa=0, skip=()):
        """a season end: every country (team file) of the world - its table of 18, the top 9 records, its cup
        winner -, then the editions"""
        L, first = self.L, True
        for f in fileset:
            if f in skip:
                continue
            table = [f | i << 8 for i in range(18)]
            k = (s * 5 + f) % 7
            table = table[k:] + table[:k]
            diy = bytearray(0x12D + 2 * len(table) + 2)
            struct.pack_into('<H', diy, 0x31, len(table))
            for i, w in enumerate(table):
                struct.pack_into('<H', diy, 0x6D + 2 * i, 18 * i)
                struct.pack_into('<H', diy, 0x12D + 2 * i, w)
            stand = bytearray(9 * REC)
            for i, w in enumerate(table[:9]):
                struct.pack_into('<H', stand, i * REC, w)
                for j in range(16):
                    stand[i * REC + 76 + 38 * j + 32] = 200 - 6 * i - (f * 3 + s) % 11
            cuprec = bytearray(REC)
            struct.pack_into('<H', cuprec, 0, table[3 + s % 4])
            for j in range(16):
                cuprec[76 + 38 * j + 32] = 150
            db, sb, cb = (ctypes.create_string_buffer(bytes(x), len(x)) for x in (diy, stand, cuprec))
            L.ct_table(db)
            if first:
                L.ct_begin()
                first = False
            L.ct_country(sb, cb)
        L.ct_go(mgr, 4321 + 17 * s, uefa)

    def nent(self, ncup):
        o, NRD = self.mem('CT_OUT'), self.lay[18]
        return [[o[self.lay[11] + c * NRD + r] for r in range(NRD)] for c in range(ncup)]

    def play(self, s):
        """the career club's games of the edition, one by one (fixed results); -> the states after each"""
        out = []
        for g in range(24):
            seg = self.mem('CT_SEG')
            if seg[2] == 0xFF:
                break
            v = (s + g) % 2 if seg[2] & 0x7F == 0 or seg[2] & 0x40 else 1 + (s + g) % 3
            self.L.ct_result(v)
            out.append(self.state())
        return out

    def state(self):
        return tuple(self.mem(k) for k in ('CT_OUT', 'CT_ED', 'CT_ST', 'CT_SEG', 'CT_IN'))


def _first_holders(assocs, files):
    arg = assocs.index('arg')
    return {0: (files['arg'] | 1 << 8, arg), 1: (files['arg'] | 2 << 8, arg)}   # (lib, sud: the Recopa's two)


W0, W4 = list(range(0, 64)), list(range(101, 133))


def _sleep(L, spec, assocs, cups, files, world, fileset):
    r = Run(L, spec, world)
    r.holders(_first_holders(assocs, files))
    bad = []
    for s in range(3):
        r.season(fileset, s, mgr=fileset[0] | 5 << 8, uefa=fileset[1] | 2 << 8)
        ne = r.nent(len(cups))
        ed, st = r.mem('CT_ED'), r.mem('CT_ST')
        if any(any(x) for x in ne):
            bad.append(f'season {s + 1}: entrants {[cups[c][1] for c in range(len(cups)) if any(ne[c])]}')
        if struct.unpack_from('<H', ed, 2)[0]:
            bad.append(f'season {s + 1}: CT_ED has {struct.unpack_from("<H", ed, 2)[0]} entries')
        if any(struct.unpack_from('<H', st, 4 + 12 * c)[0] for c in range(len(cups))):
            bad.append(f'season {s + 1}: a holder kept')
        if r.mem('CT_SEG')[2] != 0xFF:
            bad.append(f'season {s + 1}: CT_SEG {r.mem("CT_SEG")[:8].hex()}')
        if struct.unpack_from('<H', r.mem('CT_OUT'), r.lay[8])[0]:
            bad.append(f'season {s + 1}: a winner')
    return r.u32('CT_SDRAW_ERR'), r.u32('CT_SDRAW_N'), bad


def test_worlds_0_and_4_sleep():
    w = _world()
    if not w:
        return True, 'SKIP: private conti / world data missing'
    spec, assocs, cups, files = w
    out, ok = [], True
    for name, world, fs in (('world 0 (1996-97)', 0, W0), ('world 4 (Europe 1984-85)', 4, W4)):
        err, n, bad = _sleep(_new_lib(), spec, assocs, cups, files, world, fs)
        ok = ok and not err and not n and not bad
        out.append(f'{name}: CT_SDRAW_ERR {err:#x}, {n} draws, {"; ".join(bad) or "no entrant, no holder, no game"}')
    return ok, ' | '.join(out)


def test_control_base_refuses():
    """the same input on BASE's conti.c: the bug (0x10301: season 1, cup 0 = the Libertadores, round 3 = its groups)"""
    w, B = _world(), _base_lib()
    if not w or not B:
        return True, 'SKIP: world data or the base commit missing'
    spec, assocs, cups, files = w
    res = []
    for fs in (W0, W4):
        r = Run(B, spec[:-1])                           # (BASE's spec: without the world byte)
        r.holders(_first_holders(assocs, files))
        r.season(fs, 0, mgr=fs[0] | 5 << 8)
        res.append((r.u32('CT_SDRAW_ERR'), r.u32('CT_SDRAW_N')))
    return all(e == 0x10301 for e, _ in res), f'BASE {BASE} on worlds 0 / 4: (CT_SDRAW_ERR, draws) {[(hex(e), n) for e, n in res]}'


def test_world_2627_identical_to_base():
    w, B = _world(), _base_lib()
    if not w or not B:
        return True, 'SKIP: world data or the base commit missing'
    spec, assocs, cups, files = w
    fs = sorted(files.values())
    n = diff = 0
    for mgr, world in ((files['arg'] | 4 << 8, 5), (files['jpn'] | 9 << 8, 5), (files['rsa'] | 1 << 8, 0xFF),
                       (files['ita'] | 3 << 8, 5), (0, 5)):
        a, b = Run(_new_lib(), spec, world), Run(B, spec[:-1])
        seq = []
        for r in (a, b):
            st = []
            for s in range(4):
                r.season(fs, s, mgr=mgr, uefa=files['esp'] | 2 << 8)
                st.append(r.state())
                st += r.play(s)
            seq.append(st)
        n += len(seq[0])
        if len(seq[0]) != len(seq[1]):
            diff += 1
        diff += sum(x != y for x, y in zip(*seq))
        if a.u32('CT_SDRAW_ERR') or (a.u32('CT_SDRAW_N'), a.u32('CT_SDRAW_HIT')) != (b.u32('CT_SDRAW_N'), b.u32('CT_SDRAW_HIT')):
            diff += 1
        if not all(any(x) for x in a.nent(len(cups))):
            return False, f'a cup of world 2026-27 asleep: {[cups[c][1] for c, x in enumerate(a.nent(len(cups))) if not any(x)]}'
    return not diff, (f'{n} states (5 careers x 4 season ends + the career club\'s games): CT_OUT / CT_ED / CT_ST / '
                      f'CT_SEG / CT_IN {"identical to" if not diff else f"DIFFER ({diff}) from"} BASE {BASE}')


def _wfile_at(spec):
    """the offset of the spec's world-files bitmap (conti.c parse())"""
    ncup, na = spec[0], spec[1]
    p = 4
    for _ in range(ncup):
        p += 4 + spec[p] * 24
    nacc = struct.unpack_from('<H', spec, p)[0]
    acc = [tuple(spec[p + 2 + 4 * i:p + 6 + 4 * i]) for i in range(nacc)]
    p += 2 + 4 * nacc
    hol = [tuple(spec[p + 1 + 4 * i:p + 5 + 4 * i]) for i in range(spec[p])]
    p += 1 + 4 * spec[p] + na
    p += 2 + 4 * struct.unpack_from('<H', spec, p)[0]
    p += 2 + 8 * struct.unpack_from('<H', spec, p)[0]
    return p + na, acc, hol


def test_each_confederation_out_of_the_world():
    w = _world()
    if not w:
        return True, 'SKIP: private conti / world data missing'
    spec, assocs, cups, files = w
    wf, acc, hol = _wfile_at(spec)
    fs = sorted(files.values())
    confs = []
    for cf, _ in cups:
        if cf not in confs:
            confs.append(cf)
    bad, seen = [], []
    for cf in confs:
        mine = {c for c, (f, _) in enumerate(cups) if f == cf}
        afs = {files[assocs[a]] for a, c, _, _ in acc if c in mine and a != 0xFE and assocs[a] in files}
        if not afs:                                     # (the Intercontinental: no league of its own)
            continue
        sp = bytearray(spec)
        for f in afs:
            sp[wf + (f >> 3)] &= ~(1 << (f & 7))
        want_off = set(mine)                            # + the holders' cups only its cups feed
        lg = {c for a, c, _, _ in acc if a != 0xFE}
        for c in range(len(cups)):
            src = {s for s, d, _, _ in hol if d == c and s != 0xFF}
            if c not in lg and src and src <= mine:
                want_off.add(c)
        r = Run(_new_lib(), bytes(sp), 5)
        r.holders(_first_holders(assocs, files))
        for s in range(2):
            r.season(fs, s)                             # (no career club: every round played at once)
        ne = r.nent(len(cups))
        off = {c for c in range(len(cups)) if not any(ne[c])}
        st = r.mem('CT_ST')
        held = {c for c in want_off if struct.unpack_from('<H', st, 4 + 12 * c)[0]}
        if off != want_off or r.u32('CT_SDRAW_ERR') or held:
            bad.append(f'{cf}: asleep {sorted(cups[c][1] for c in off)}, want {sorted(cups[c][1] for c in want_off)}, '
                       f'ERR {r.u32("CT_SDRAW_ERR"):#x}, holders kept {sorted(held)}')
        seen.append(f'{cf} -> {"/".join(cups[c][1] for c in sorted(off))}')
    return not bad, '; '.join(bad) or 'out of the world in turn, asleep: ' + ', '.join(seen) + '; the others play, no refusal'


def test_no_stage_is_not_a_refusal():
    """(2): world 2026-27, but no CONMEBOL table reaches the season end - the Libertadores groups get the holder
    alone: the round is not played and no draw is refused (BASE: 0x10301)"""
    w = _world()
    if not w:
        return True, 'SKIP: private conti / world data missing'
    spec, assocs, cups, files = w
    wf, acc, hol = _wfile_at(spec)
    skip = {files[assocs[a]] for a, c, _, _ in acc if cups[c][0] == 'conmebol' and a != 0xFE}
    res = []
    for L, sp in ((_new_lib(), spec), (_base_lib(), spec[:-1])):
        if L is None:
            res.append(None)
            continue
        r = Run(L, sp)
        r.holders(_first_holders(assocs, files))
        r.season(sorted(files.values()), 0, skip=skip)
        ne = r.nent(len(cups))
        res.append((r.u32('CT_SDRAW_ERR'), ne[0][3], r.mem('CT_OUT')[r.lay[13] + 3 * r.lay[19]],
                    sum(any(x) for x in ne[3:])))
    new, base = res
    ok = new[0] == 0 and new[1] == 0 and new[2] != 0xFF and new[3] >= 7 and (base is None or base[0] == 0x10301)
    return ok, f'(CT_SDRAW_ERR, lib groups entrants, its "not drawn" mark, other cups played) new {new}, BASE {base}'


def test_old_edition_of_world_0_replays_then_sleeps():
    """a save of world 0 made before the gate, as a released exe made it (no ED_S: CT_NOS): its running edition
    (guests-only cups, the CONMEBOL holders) replays in the new code exactly as BASE replays it - CT_OUT the same, no
    refusal -, then the next season end: no edition, no holder"""
    w, B = _world(), _base_lib()
    if not w or not B:
        return True, 'SKIP: world data or the base commit missing'
    spec, assocs, cups, files = w
    b = Run(B, spec[:-1])
    ctypes.c_ubyte.in_dll(B, 'CT_NOS').value = 1
    try:
        b.holders(_first_holders(assocs, files))
        b.season(W0, 0, mgr=W0[0] | 5 << 8)
        ed, st = b.mem('CT_ED'), b.mem('CT_ST')
        B.ct_resume()
        ref = b.mem('CT_OUT')
    finally:
        ctypes.c_ubyte.in_dll(B, 'CT_NOS').value = 0
    a = Run(_new_lib(), spec, 0)
    for k, v in (('CT_ED', ed), ('CT_ST', st)):
        ctypes.memmove((ctypes.c_ubyte * len(v)).in_dll(a.L, k), v, len(v))
    a.L.ct_resume()                                     # (the load)
    same = a.mem('CT_OUT') == ref and a.mem('CT_ED') == ed
    played = sum(any(x) for x in a.nent(len(cups)))
    e1 = a.u32('CT_SDRAW_ERR')
    a.season(W0, 1, mgr=W0[0] | 5 << 8)                 # (the next season end: ct_finish on the old edition, then the gate)
    ne = a.nent(len(cups))
    st2 = a.mem('CT_ST')
    held = [c for c in range(len(cups)) if struct.unpack_from('<H', st2, 4 + 12 * c)[0]]
    ok = same and played and not e1 and not a.u32('CT_SDRAW_ERR') and not any(any(x) for x in ne) and not held
    return ok, (f'old edition: {played} cups replayed, CT_OUT {"==" if same else "!="} BASE, ERR {e1:#x}; next season end: '
                f'entrants {sum(map(sum, ne))}, holders {held}, ERR {a.u32("CT_SDRAW_ERR"):#x}')


if __name__ == '__main__':
    for k, f in sorted(globals().items()):
        if k.startswith('test_'):
            print(k, f())
