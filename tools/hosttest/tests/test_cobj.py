"""4.2 engine P1: cobj's dead-code removal on its own - no build, no game. A small C file (a used and an unused
function, a used and an unused variable, a static helper, a top-level asm hook) compiled with sections=True and linked
with roots into a recording stand-in for LEPatch:
- roots: the hook and what it reaches are laid out (the call displacement right, the data fixup to the kept
  variable), the unused function and variable are not, nor their symbols;
- no roots: every section, the same symbols as the object without sections;
- lrank.c (the real consumer, its #included library): with its ROOTS only lrank's own globals and sr_league_rank
  remain, the code shorter than without."""
import os
import struct
import sys
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import cobj  # noqa: E402

SRC = r'''
int used_v = 5, unused_v[64] = { 1 };
static int helper(int x) { return x * used_v + 1; }
__attribute__((noinline)) int used_f(int x) { return helper(x) ^ 3; }
int unused_f(int x) { return unused_v[x] + used_f(x); }
__asm__(".globl hook\nhook:\n\tpushal\n\tpushl $7\n\tcall used_f\n\taddl $4, %esp\n\tpopal\n\tret\n");
'''


class Rec:
    """the LEPatch calls link() makes: bytes put, LE pointer fixups, cross-object rel32s"""
    class le:                                               # (cobj.add_ptr: a page-straddling dword; the tests'
        page_size = 0x100000                                #  layouts never straddle one)

    def __init__(self):
        self.mem, self.ptrs, self.rels = {}, [], []

    def put(self, objn, off, data):
        for i, b in enumerate(data):
            self.mem[(objn, off + i)] = b

    def add_ptr(self, objn, off, tobj, toff):
        self.ptrs.append((objn, off, tobj, toff))

    def add_rel(self, objn, off, tobj, toff):
        self.rels.append((objn, off, tobj, toff))

    def get(self, objn, off, n):
        return bytes(self.mem.get((objn, off + i), 0) for i in range(n))


def _compile(sections):
    with tempfile.TemporaryDirectory() as t:
        src = os.path.join(t, 'gc.c')
        open(src, 'w').write(SRC)
        os.environ['COBJ_CACHE'] = t                       # (nothing left in the shared cache)
        try:
            return cobj.compile_c(src, sections=sections)
        finally:
            del os.environ['COBJ_CACHE']


def test_cobj_gc():
    obj = _compile(True)
    p = Rec()
    syms, end, bss = cobj.link(p, obj, 0x1000, (2, 0x8000), roots=['hook'])
    bad = []
    for k in ('hook', 'used_f', 'used_v'):
        if k not in syms:
            bad.append(f'{k} dropped')
    for k in ('unused_f', 'unused_v'):
        if k in syms:
            bad.append(f'{k} kept')
    if syms.get('used_v') and not any((t, o) == tuple(syms['used_v']) for _, _, t, o in p.ptrs):
        bad.append('no fixup to used_v')
    h = syms['hook'][1]                                     # pushal; push 7; call rel32 -> used_f
    code = p.get(1, h, 8)
    if code[0] != 0x60 or code[3] != 0xE8:
        bad.append(f'hook bytes {code.hex()}')
    elif h + 8 + struct.unpack('<i', code[4:8])[0] != syms['used_f'][1]:
        bad.append('call displacement')
    full = Rec()
    fsyms, fend, _ = cobj.link(full, obj, 0x1000, (2, 0x8000))
    plain = cobj.link(Rec(), _compile(False), 0x1000, (2, 0x8000))[0]
    if set(fsyms) != set(plain):
        bad.append(f'no roots: symbols {sorted(set(fsyms) ^ set(plain))}')
    if not end < fend:
        bad.append(f'no code dropped ({end - 0x1000} / {fend - 0x1000} B)')
    try:
        cobj.link(Rec(), obj, 0x1000, (2, 0x8000), roots=['nosuch'])
        bad.append('an unknown root accepted')
    except AssertionError:
        pass
    return not bad, (', '.join(bad) or f'kept {sorted(syms)}, code {end - 0x1000} of {fend - 0x1000} B')


def test_cobj_gc_lrank():
    import lrank
    src = os.path.join(TOOLS, 'lrank.c')
    flags = ['-Oz', '-fno-zero-initialized-in-bss', '-DSPLIT_ST=0', '-DSPLIT_MAGIC=0']
    with tempfile.TemporaryDirectory() as t:
        os.environ['COBJ_CACHE'] = t
        try:
            gc, plain = cobj.compile_c(src, flags, sections=True), cobj.compile_c(src, flags)
        finally:
            del os.environ['COBJ_CACHE']
    ext = {n: (2, 0x100) for n in ('UD', 'A3', 'A4', 'D1', 'D2', 'GAMETYPE', 'SIMFLAG', 'CAREERTEAM', 'D6CDC', 'D8CAA',
                                   'WORLDB', 'SEASONP', 'LR_TAB', 'SORT_NEXT')}
    s1, e1, _ = cobj.link(Rec(), gc, 0, (4, 0), externs=ext, text_obj=4, roots=lrank.ROOTS)
    s0, e0, _ = cobj.link(Rec(), plain, 0, (4, 0), externs=ext, text_obj=4)
    lib = sorted(k for k in s1 if k.startswith('sr_'))
    ok = lib == ['sr_league_rank'] and set(lrank.ROOTS) <= set(s1) and e1 < e0
    return ok, f'library kept {lib}; code {e1} B with ROOTS, {e0} B without ({e0 - e1} B dropped)'
