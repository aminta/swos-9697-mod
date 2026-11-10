"""Engine step P0 (PLAN §19.3, 04/11): the career save's round trip, the contract P's state items build on. Fixture
p0_uru_load (c/HTI10j = 406-i10j a25886a, release recipe + HOSTTEST_SYMS=1): a NACIONAL career's season-1 save
(save_s1.CAR, the game's own W84A.CAR) at trailer.load_trailer. The emulated load (load_trailer, its after-load
callbacks, ProcessCareerFile) then the game's own SaveCareerFile (the trailer's save_trailer inside it):

- a save of this build: save(load(x)) = x, byte for byte;
- an older save (the archived set: players' and Davide's saves of 3.3.6 .. 4.0.5): it is upgraded once - the main
  block and every engine item it had unchanged (but an empty 'CE' in a season-1 save: season 1's edition, conti
  ct_load1), only items it lacked added (their defaults), the team cache unchanged,
  the fixed part only the game's own absolute pointers re-based to this exe (dwords both sides pointer-like, or a
  pointer cleared, or a pointer's low word by the same delta), a 4.0 split state moved (sp_migrate) - and the upgrade
  is a fixed point: save(load(save(load(x)))) = save(load(x)).
  The UEFA coefficient block (uefacoef CB, 4.1 uc_chk): a block uc_chk finds damaged (no 'UC' mark, ring / done out of
  range, a season above CHMAX / KHMAX: BOCA rc11, NZ rc17's sprite-written KHIST) comes back as the fresh seed -
  byte for byte the block uc_init writes on this fixture's own save; any other block byte-identical.

(H's '5083 of 16192 B differ' compared an upgraded trailer with an older one byte by byte: the added items shift the
later ones. Item by item nothing changes.)"""
import itertools
import os
import re
import string
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu import Machine  # noqa: E402

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import engine  # noqa: E402
import sacups  # noqa: E402
import uefacoef  # noqa: E402
import trailer  # noqa: E402
from le import LE  # noqa: E402

HOME = os.path.expanduser('~')
FIX = os.environ.get('HT_P0_FIX') or os.path.join(HOME, 'swos-mod', 'internal', 'hosttest', 'fixtures', 'p0_uru_load')
OLD = [os.path.join(HOME, 'swos-mod', 'internal', p) for p in (
    'oldsaves/v3.3.6_W8485_LIVERPOOL_s1.CAR', 'davide-mister-20261021/PHILA.CAR',
    'davide-mister-20261022-rc11/MESTRE.CAR', 'davide-mister-20261022-rc11/BOCA.CAR', 'reports/ischia/ISCHIA.CAR',
    'reports/rc17-davide/NZ.CAR', 'reports/enzo-dup-20261102/ENZO.CAR', 'reports/libero/FENER0910.CAR')]
TEAM_SIZE = 684
_IDN = {}


def _name(iid):
    if not _IDN:
        for c in ['BT_EXT', 'SS2'] + [a + b for a, b in itertools.product(string.ascii_uppercase + string.digits,
                                                                          repeat=2)]:
            _IDN.setdefault(engine.item_id(c), c)
    return _IDN.get(iid, hex(iid))


class Game:
    """the fixture's machine: its .CAR stage, the D1 register, SaveCareerFile (from the original exe's code)"""

    def __init__(self):
        self.meta = Machine(FIX, 0).meta
        b = self.meta['build']
        self.build = b if os.path.isdir(b) else os.path.join(HOME, b[b.find('/swos-mod/') + 1:])
        self.car = open(os.path.join(FIX, 'save_s1.CAR'), 'rb').read()
        d1 = LE(open(os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
        r = sacups.regs(d1)
        self.dreg1 = r['D7'] - 24
        a1, dr = (re.escape(struct.pack('<I', x)) for x in (r['A1'], self.dreg1))
        m = list(re.finditer(rb'\xc7\x05' + a1 + rb'(.{4})\xe8.{4}\x75.\xe8.{4}\x75.\xe8', d1, re.S))   # (trailer.patch:
        m = [x for x in m if sum(y.group(1) == x.group(1) for y in m) == 1]   # LoadCareerFile's careerFileBuffer - the
        assert len(m) == 1, len(m)                                            # other two load competition files)
        career = struct.unpack('<I', m[0].group(1))[0]
        m = list(re.finditer(rb'\xc7\x05' + a1 + re.escape(struct.pack('<I', career)) + rb'\xa1' + a1 + rb'\x29\x05' +
                             dr + rb'\xe8', d1, re.S))
        assert len(m) == 1, len(m)
        k = d1.rfind(b'\xc7\x05' + struct.pack('<I', self.dreg1), m[0].start() - 0x80, m[0].start())
        numsel = struct.unpack_from('<I', d1, k + 6)[0]
        self.save_fn = d1.rfind(b'\xc3', k - 0x80, k) + 1   # SaveCareerFile (after the routine before it)
        self.fixed = numsel - career + 2
        mach = self.machine()
        self.stage = bytes(mach.uc.mem_read(0, 0x2000000)).find(self.car[:4096])
        assert self.stage > 0, 'the save not found in the snapshot'

    def machine(self):
        m = Machine(FIX, 0)
        m.dos_files(self.build, writes=True)
        return m

    def round_trip(self, x, seed=False):
        m = self.machine()
        m.write(self.stage, x + bytes(max(0, len(self.car) - len(x))))
        m.write(m.base2 + self.dreg1, struct.pack('<I', len(x)))
        m.call('trailer.load_trailer', max_insn=300_000_000)
        if seed:                                       # (the fresh UEFA coefficient block: uc_init after the load)
            m.call('uefacoef.uc_init', max_insn=50_000_000)
        m.files_written.clear()
        m.call(m.base1 + self.save_fn, max_insn=300_000_000)
        return next(iter(m.files_written.values()), b'')

    def parts(self, x):
        """(fixed part, team cache, main block or None, {item: bytes})"""
        n = struct.unpack_from('<H', x, self.fixed - 2)[0]
        t = self.fixed + n * TEAM_SIZE
        k = x.find(struct.pack('<H', trailer.EN_MARK), t)
        items, main = {}, None
        if k >= 0:
            main = x[t:k]
            p, end = k + 4, k + 4 + struct.unpack_from('<H', x, k + 2)[0]
            while p + 4 <= end:
                iid, ln = struct.unpack_from('<HH', x, p)
                items[_name(iid)] = x[p + 4:p + 4 + ln]
                p += 4 + ln
        return x[:self.fixed], x[self.fixed:t], main, items


CB = 2 + uefacoef.CB_OFF                                # the coefficient block in the fixed part (tmdFileBuffer + 0x3800)


def _uc_block(g):
    """(size, fresh seed, damaged(fixed part)) of the build's coefficient block when it has uc_chk (4.1), else None.
    NG from uc_chk's own `cmp ecx, 5 * NG` (bigtables: 2409); the seed = uc_init on the fixture's save."""
    m = g.machine()
    if 'uc_chk' not in m.syms.get('uefacoef', {}):
        return None
    code = m.read(m.lin('uefacoef.uc_chk'), 0x80)
    ng = struct.unpack_from('<I', code, [k.start() for k in re.finditer(rb'\x81\xf9', code)][-1] + 2)[0] // 5
    kh = uefacoef.KPTS + 2 * ng
    size = kh + 10 * ng + 0x6C + 0xC                 # (uefacoef.layout: PREV = KHIST + 10 NG, FIN = PREV + 6Ch, + 0Ch)
    seed = g.parts(g.round_trip(g.car, seed=True))[0][CB:CB + size]
    assert seed[:2] == b'UC', seed[:4]

    def damaged(f):                                  # uc_chk in Python (uefacoef.ASM)
        b = f[CB:CB + size]
        return (b[:2] != b'UC' or b[uefacoef.RING] >= 5 or b[uefacoef.DONE] > 1
                or max(struct.unpack_from('<1280I', b, uefacoef.CHIST)) > uefacoef.CHMAX
                or max(struct.unpack_from(f'<{5 * ng}H', b, kh)) > uefacoef.KHMAX)
    return size, seed, damaged


def _ptr(v):
    return v == 0 or 0x80000 <= v < 0x10000000         # (a big-memory machine's DOS/4GW base: 0x056xxxxx, FENER0910)


def _fixed_ok(a, b):
    """the fixed part's differences, each one of: a dword pointer-like on both sides (or cleared) - the game's own
    absolute pointers, re-based to this exe; the low word of a pointer moved by one of those deltas; a split state
    (split.MAGIC, ST_SIZE bytes) moved by sp_migrate (4.0's layout) - on either side. Returns the others."""
    import split
    ok = bytearray(len(a))
    for x in (a, b):
        k = x.find(struct.pack('<H', split.MAGIC))
        while k >= 0:
            ok[k:k + split.ST_SIZE] = b'\1' * len(ok[k:k + split.ST_SIZE])
            k = x.find(struct.pack('<H', split.MAGIC), k + 1)
    deltas, i = set(), 0
    while i < len(a):
        if a[i] == b[i] or ok[i]:
            i += 1
            continue
        for s in range(max(0, i - 3), min(i, len(a) - 4) + 1):
            va, vb = struct.unpack_from('<I', a, s)[0], struct.unpack_from('<I', b, s)[0]
            if _ptr(va) and _ptr(vb):
                ok[s:s + 4] = b'\1\1\1\1'
                if va and vb:
                    deltas.add((vb - va) & 0xFFFF)
                break
        i += 1
    bad = []
    for i in range(len(a)):
        if a[i] == b[i] or ok[i]:
            continue
        if not any(s + 2 <= len(a) and (struct.unpack_from('<H', b, s)[0] - struct.unpack_from('<H', a, s)[0]) & 0xFFFF
                   in deltas for s in (i - 1, i)):
            bad.append(hex(i))
    return bad


def test_roundtrip_current():
    """a save of this build: save(load(x)) = x"""
    g = Game()
    y = g.round_trip(g.car)
    diff = sum(1 for i in range(min(len(y), len(g.car))) if y[i] != g.car[i])
    return y == g.car, f'{len(g.car)} B -> {len(y)} B, {diff} bytes differ'


def test_roundtrip_old():
    """older saves: upgraded once (only added items, pointers re-based), then a fixed point"""
    g = Game()
    uc = _uc_block(g)
    out, bad = [], []
    for f in OLD:
        if not os.path.exists(f):
            out.append(f'{os.path.basename(f)} missing')
            continue
        x = open(f, 'rb').read()
        y = g.round_trip(x)
        z = g.round_trip(y)
        fx, cx, mx, ix = g.parts(x)
        fy, cy, my, iy = g.parts(y)
        tag = os.path.basename(os.path.dirname(f)) + '/' + os.path.basename(f)
        why = []
        if z != y:
            why.append('not a fixed point')
        if cx != cy:
            why.append('team cache changed')
        if mx is not None and mx != my:
            why.append('main block changed')
        chg = sorted(k for k in set(ix) & set(iy) if ix[k] != iy[k]
                     and not (k == 'CE' and ix[k][:2] != b'CE' and iy[k][:2] == b'CE'))   # (4.0.6 B2 M3: a season-1
                                                    # save with no edition gets season 1's at the load - ct_load1)
        gone = sorted(set(ix) - set(iy))
        if chg or gone:
            why.append(f'items changed {chg} gone {gone}')
        if uc:                                         # (4.1 uc_chk: a damaged block re-seeded, any other kept)
            n, seed, damaged = uc
            if damaged(fx) and fy[CB:CB + n] != fx[CB:CB + n]:
                if fy[CB:CB + n] != seed:
                    why.append('coefficient block not the fresh seed')
                tag += ' (UEFA coefficients re-seeded)'
            elif fy[CB:CB + n] != fx[CB:CB + n]:
                why.append('coefficient block changed')
            fx, fy = fx[:CB] + fy[CB:CB + n] + fx[CB + n:], fy   # (the block compared above: not by _fixed_ok)
        fb = _fixed_ok(fx, fy)
        if fb:
            why.append(f'fixed part not pointers at {fb[:6]}')
        if why:
            bad.append(f'{tag}: {", ".join(why)}')
        out.append(f'{tag} +{sorted(set(iy) - set(ix))}')
    return not bad, ('; '.join(bad) + ' | ' if bad else '') + '; '.join(out)
