"""4.2 engine P2: cstack.h (a C stack of its own in obj4) under Unicorn, linked by cobj.link as an exe consumer would
be: the code at obj1, the block at the extern CSTACK in obj4, every fixup applied. The caller runs on a 4 KB "game
stack" (the real one is 4043 B).
- the worst draw shapes (data/gdraw_worst.txt: the fuzzer's slow shapes + the hard set's deepest, 62-64 clubs): the
  same result as a direct call on a big stack, ESP inside the block when the draw starts, the game stack untouched
  below the call's own words, the deepest use under CSTACK_SIZE, the guard (1 KB) intact, depth 0 and no overflow after;
- a call from inside the block (depth 2) stays on it; a call with a broken depth from outside is refused (-4);
- a recursion deeper than the block: the overflow counter is set.
The draw is the engine's sr_group_draw at HT_ENGINE (default ~/swce-ecclp; none: SKIP as a PASS), its 737eae4+
version (Kempe repair + budget, the one T2 measured); tools/swce/ is older until P7 re-vendors it."""
import os
import struct
import sys
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import cobj  # noqa: E402

ENGINE = os.environ.get('HT_ENGINE') or os.path.expanduser('~/swce-ecclp')
SHAPES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'gdraw_worst.txt')
SIZE, GUARD, GW = 16384, 0x4B435453, 1024
B1, B2, B4 = 0x100000, 0x400000, 0x5F0000                   # obj1 (code), obj2 (bss), obj4 (the block at +0x10000)
BLK = 0x10000
GAME, GAME_SP = 0x300000, 0x30F000                          # the caller's stack: 4 KB painted under GAME_SP
DATA, RET = 0x900000, 0x900F00

SRC = r'''
#include "%s/rules/sr_stage.c"
#define CSTACK_IMPL
#include "%s/cstack.h"
typedef struct { i32 n, g; const u8 *a; u32 seed; u8 *grp; i32 r; u32 esp; i32 depth; } job;
static int run(void *p)
{
    job *j = p;
    j->esp = (u32)__builtin_frame_address(0);
    j->depth = *(volatile i32 *)(CSTACK + CSTACK_SIZE - 4);
    return j->r = sr_group_draw(j->n, j->g, j->a, j->seed, j->grp);
}
static int nest(void *p) { return cstack_call(run, p); }
int t_draw(job *j) { return cstack_call(run, j); }
int t_nest(job *j) { return cstack_call(nest, j); }
int t_direct(job *j) { return run(j); }
int t_init(void) { cstack_init(); return 0; }
int t_high(void) { return cstack_high(); }
int t_ovf(void) { return cstack_overflows(); }
__attribute__((noinline)) static i32 deep(i32 k) { volatile u8 b[256]; b[k & 255] = (u8)k; return k ? deep(k - 1) + b[k & 255] : 0; }
static int over(void *p) { return deep(*(i32 *)p); }
int t_over(i32 *k) { return cstack_call(over, k); }
'''


class Rec:
    class le:
        page_size = 0x100000

    def __init__(self):
        self.mem, self.ptrs, self.rels = {}, [], []

    def put(self, objn, off, data):
        for i, b in enumerate(data):
            self.mem[(objn, off + i)] = b

    def add_ptr(self, objn, off, tobj, toff):
        self.ptrs.append((objn, off, tobj, toff))

    def add_rel(self, objn, off, tobj, toff):
        self.rels.append((objn, off, tobj, toff))


def _machine():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    with tempfile.TemporaryDirectory() as t:
        src = os.path.join(t, 'cst.c')
        open(src, 'w').write(SRC % (ENGINE, TOOLS))
        os.environ['COBJ_CACHE'] = t
        try:
            obj = cobj.compile_c(src, sections=True)
        finally:
            del os.environ['COBJ_CACHE']
    p = Rec()
    roots = ['t_draw', 't_nest', 't_direct', 't_over', 't_init', 't_high', 't_ovf']
    syms, end, bss = cobj.link(p, obj, 0, (2, 0), externs={'CSTACK': (4, BLK)}, roots=roots)
    assert not p.rels, p.rels
    base = {1: B1, 2: B2, 4: B4}
    img = bytearray(end)
    for (o, off), b in p.mem.items():
        assert o == 1
        img[off] = b
    for o, off, tobj, toff in p.ptrs:                       # the loader: object base + offset
        struct.pack_into('<I', img, off, base[tobj] + toff)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(B1, 0x40000)
    uc.mem_write(B1, bytes(img))
    uc.mem_map(B2, 0x10000)
    uc.mem_map(B4, 0x20000)
    uc.mem_map(GAME, 0x10000)
    uc.mem_map(DATA, 0x10000)
    return uc, {k: B1 + v[1] for k, v in syms.items()}, end


def _call(uc, fn, arg):
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, \
        UC_X86_REG_EBP
    uc.mem_write(GAME_SP - 0x1000, b'\xA5' * 0x1000)
    uc.mem_write(GAME_SP, struct.pack('<2I', RET, arg))
    keep = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
    for i, r in enumerate(keep):
        uc.reg_write(r, 0x11110000 + i)
    uc.reg_write(UC_X86_REG_ESP, GAME_SP)
    uc.emu_start(fn, RET)
    saved = all(uc.reg_read(r) == 0x11110000 + i for i, r in enumerate(keep))
    sp = uc.reg_read(UC_X86_REG_ESP)
    g = uc.mem_read(GAME_SP - 0x1000, 0x1000)
    used = 0x1000 - next((i for i in range(0x1000) if g[i] != 0xA5), 0x1000)
    return struct.unpack('<i', struct.pack('<I', uc.reg_read(UC_X86_REG_EAX)))[0], used, saved and sp == GAME_SP + 4


def _blk(uc, off):
    return struct.unpack('<i', uc.mem_read(B4 + BLK + off, 4))[0]


def _shapes():
    out = []
    for line in open(SHAPES):
        t = [int(x) for x in line.split()]
        if t:
            out.append((t[0] & 0xFFFFFFFF, t[1], t[2], bytes(t[3:3 + t[1]])))
    return out


def _job(uc, n, g, a, seed):
    uc.mem_write(DATA + 0x100, a + bytes(64 - n))
    uc.mem_write(DATA + 0x200, bytes(64))
    uc.mem_write(DATA, struct.pack('<iiIIIiIi', n, g, DATA + 0x100, seed, DATA + 0x200, 0, 0, 0))


def test_cstack_worst_draws():
    if not os.path.isfile(os.path.join(ENGINE, 'rules', 'sr_stage.c')):
        return True, f'SKIP: no engine checkout at {ENGINE}'
    uc, s, end = _machine()
    bad, deepest, game = [], 0, 0
    sh = _shapes()
    for k, (seed, n, g, a) in enumerate(sh):
        _job(uc, n, g, a, seed)
        r0, _, ok0 = _call(uc, s['t_direct'], DATA)
        want = (r0, bytes(uc.mem_read(DATA + 0x200, n)))
        _job(uc, n, g, a, seed)
        uc.mem_write(B4 + BLK, b'\x5A' * SIZE)                     # (garbage, as DOS/4GW leaves a tail)
        _call(uc, s['t_init'], 0)                                   # (swe_init's cstack_init: paint, state 0)
        r, used, ok = _call(uc, s['t_draw'], DATA)
        got = (r, bytes(uc.mem_read(DATA + 0x200, n)))
        esp, depth = struct.unpack('<Ii', uc.mem_read(DATA + 24, 8))
        m = uc.mem_read(B4 + BLK + GW, SIZE - 12 - GW)          # (above the guard)
        low = next((i for i in range(len(m)) if m[i] != 0xA5), len(m))
        use = len(m) - low
        high = _call(uc, s['t_high'], 0)[0]
        deepest, game = max(deepest, use), max(game, used)
        guard = uc.mem_read(B4 + BLK, GW) != struct.pack('<I', GUARD) * (GW // 4)
        why = [w for w, c in (('result differs', got != want), ('registers / ESP not restored', not (ok and ok0)),
                              ('draw not on the block', not B4 + BLK < esp < B4 + BLK + SIZE), (f'depth {depth}', depth != 1),
                              ('guard', guard), ('depth after', _blk(uc, SIZE - 4)),
                              ('overflow', _blk(uc, SIZE - 12)), (f'game stack {used} B', used > 32),
                              ('into the guard', low == 0), (f'cstack_high {high} != {use}', high != use)) if c]
        if why:
            bad.append(f'{k} (n {n} g {g}): {", ".join(why)}')
    return not bad, '; '.join(bad) or (f'{len(sh)} shapes = direct calls; deepest {deepest} B of {SIZE}, game stack '
                                       f'{game} B, guard intact, code {end} B')


def test_cstack_nest_refuse_overflow():
    if not os.path.isfile(os.path.join(ENGINE, 'rules', 'sr_stage.c')):
        return True, f'SKIP: no engine checkout at {ENGINE}'
    uc, s, _ = _machine()
    uc.mem_write(B4 + BLK, b'\x5A' * SIZE)
    _call(uc, s['t_init'], 0)
    bad = []
    seed, n, g, a = _shapes()[0]
    _job(uc, n, g, a, seed)
    r0, _, _ = _call(uc, s['t_direct'], DATA)
    _job(uc, n, g, a, seed)
    r, used, ok = _call(uc, s['t_nest'], DATA)
    esp, depth = struct.unpack('<Ii', uc.mem_read(DATA + 24, 8))
    if r != r0 or depth != 2 or not B4 + BLK < esp < B4 + BLK + SIZE or not ok or _blk(uc, SIZE - 4):
        bad.append(f'nested: r {r}/{r0} depth {depth} esp {esp:#x}')
    uc.mem_write(B4 + BLK + SIZE - 4, struct.pack('<i', 1))  # a broken depth, called from the game's stack
    _job(uc, n, g, a, seed)
    r, used, ok = _call(uc, s['t_draw'], DATA)
    if r != -4 or struct.unpack('<I', uc.mem_read(DATA + 24, 4))[0] or not ok:
        bad.append(f'refuse: r {r}')
    uc.mem_write(B4 + BLK + SIZE - 4, bytes(4))
    uc.mem_write(DATA + 0x300, struct.pack('<i', 40))       # ~11 KB: fits
    r, used, ok = _call(uc, s['t_over'], DATA + 0x300)
    if _blk(uc, SIZE - 12) or not ok:
        bad.append('40 levels: overflow counted')
    uc.mem_write(DATA + 0x300, struct.pack('<i', 80))       # ~22 KB: through the guard (the test maps 64 KB under it)
    r, used, ok = _call(uc, s['t_over'], DATA + 0x300)
    if _blk(uc, SIZE - 12) != 1 or _call(uc, s['t_ovf'], 0)[0] != 1 or not ok or _blk(uc, SIZE - 4):
        bad.append(f'80 levels: overflow {_blk(uc, SIZE - 12)}, cstack_overflows {_call(uc, s["t_ovf"], 0)[0]}')
    return not bad, '; '.join(bad) or 'nested call stays on the block (depth 2), broken depth refused (-4), ' \
                                      'overflow counted past the block (cstack_overflows 1), not before'
