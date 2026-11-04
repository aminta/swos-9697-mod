"""Engine step O (CONVENTIONS 23bis): obj4, the engine's object, on its own - no snapshot, no game state. The exe's obj4
(HT_SWE_EXE, else c/HTO4/SWOS/ITALIAN.EXE) relocated at a base of its own in a bare Unicorn machine (flat 4 GB
segments), its zero-fill tail (the arena) filled with garbage as DOS/4GW may leave it, then swe_init() through the
header's pointer: it returns the version, zeroes the whole arena and nothing past it, and sets SWE_STATE."""
import os
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import swe  # noqa: E402
from le import LE  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_SWE_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTO4', 'SWOS', 'ITALIAN.EXE')
BASE, STACK, RET = 0x400000, 0x300000, 0x2FF000


def test_swe_init():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    if not os.path.exists(EXE):
        return False, f'{EXE} missing (HT_SWE_EXE: an exe with obj4)'
    le = LE(open(EXE, 'rb').read())
    if len(le.objs) < 4:
        return False, f'{len(le.objs)} objects: no obj4'
    o = le.obj(4)
    img = bytearray(le.obj_bytes(4)).ljust(o.vsize, b'\xAA')      # (the tail: garbage, as DOS/4GW may leave it)
    file_n = 0x1000 * o.npages
    for sobj, soff, t, tobj, toff, *_ in le.fixups():
        if sobj == 4:
            assert t == 7 and tobj == 4, (soff, t, tobj)              # (the empty engine: only pointers into obj4)
            struct.pack_into('<I', img, soff, BASE + toff)
    hdr = bytes(img[:32])
    assert hdr[:8] == swe.MAGIC, hdr[:8]
    ver, self_p, init_p, arena_p, bss_n, state_p = struct.unpack_from('<6I', hdr, 8)
    arena_n = swe.ARENA
    size = (o.vsize + 0x1fff) & ~0xfff
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, size)
    uc.mem_write(BASE, bytes(img) + b'\xBB' * (size - len(img)))  # (past vsize: a canary)
    uc.mem_map(RET & ~0xfffff, 0x200000)
    uc.mem_write(RET, b'\xF4')
    uc.reg_write(UC_X86_REG_ESP, STACK - 16)
    uc.mem_write(STACK - 16, struct.pack('<I', RET))
    uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=RET, end=RET)
    uc.emu_start(init_p, RET, count=5_000_000)
    rv = uc.reg_read(UC_X86_REG_EAX)
    mem = bytes(uc.mem_read(BASE, size))
    a0, a1 = arena_p - BASE, arena_p - BASE + arena_n
    st = struct.unpack_from('<I', mem, state_p - BASE)[0]
    errs = []
    if self_p != BASE or not (BASE + swe.CODE_AT <= init_p < BASE + file_n) or a0 < file_n:
        errs.append(f'header self {self_p:#x} init {init_p:#x} arena {arena_p:#x}')
    if rv != ver or ver != swe.VERSION:
        errs.append(f'swe_init returned {rv}, header v{ver}')
    if st != 1:
        errs.append(f'SWE_STATE {st}')
    if bss_n != o.vsize - file_n:
        errs.append(f'.bss {bss_n:#x} != the tail {o.vsize - file_n:#x}')
    if any(mem[a0:a1]):
        errs.append(f'arena not zeroed: {sum(1 for x in mem[a0:a1] if x)} bytes')
    if mem[o.vsize:size] != b'\xBB' * (size - o.vsize):
        errs.append('wrote past obj4\'s vsize')
    s0 = state_p - BASE
    tail = [i for i in range(file_n, o.vsize) if not a0 <= i < a1 and not s0 <= i < s0 + 4 and mem[i] != 0xAA]
    if tail:
        errs.append(f'tail bytes outside the arena changed: {[hex(i) for i in tail[:4]]}')
    return not errs, '; '.join(errs) or f'v{rv}, arena obj4+{a0:#x}..{a1:#x} zeroed (was 0xAA), SWE_STATE 1, vsize {o.vsize:#x}'
