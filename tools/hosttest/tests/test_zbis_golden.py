"""secflags (engine rules 4, sr_b_zone): the built exe's zones.py zb_is, run in Unicorn over every input, against the
golden tools/hosttest/golden/zbis.txt that the engine's tests/rules/zone_check.c checks sr_b_zone with.
- The exe: ZBIS_EXE_DIR (default c/REL42x5383/SWOS, the 4.2 release build of 42-int 5383cdb), every language there.
- zb_is is found by its first bytes (push esi / push ecx / xor edx, edx / mov esi, ZB / movzx ecx, byte [esi] / inc
  esi / jecxz) in any object; ZB, SEC_BQ and SEASONP are read from its own relocated operands, so nothing is
  transcribed: the asm decides.
- Inputs: the ZB table's first row (its team word in ax), its build flags byte 0..7, its SEC_BQ byte 0..2 and
  SEC_BQ[0] + 1 == SEASONP (written last season: 'current') or not -> dl (bits 0..1): 8 x 3 x 2 = 48.
- ZBIS_GOLDEN_WRITE=1 writes the golden (build key + exe md5 + 48 rows) instead of comparing; every language's exe
  must give the same 48 outputs."""
import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(HERE, '..'))

ROOT = os.path.join(TOOLS, '..')
EXE_DIR = os.environ.get('ZBIS_EXE_DIR') or os.path.join(ROOT, 'c', 'REL42x5383', 'SWOS')
BUILD_KEY = os.environ.get('ZBIS_BUILD_KEY', 'REL42x5383 = 42-int 5383cdb release build')
GOLDEN = os.path.join(HERE, '..', 'golden', 'zbis.txt')
LANGS = ('ITALIAN', 'ENGLISH', 'FRENCH', 'GERMAN')
SIG = re.compile(rb'\x56\x51\x31\xd2\xbe(....)\x0f\xb6\x0e\x46\xe3', re.S)
BASE1, STACK, SENT = 0x400000, 0x7F0000, 0x7F8000


def _find(le, imgs):
    """(obj, offset) of zb_is in the exe, its relocated image"""
    hits = [(n, m.start()) for n in imgs for m in SIG.finditer(bytes(le.obj_bytes(n)))]
    assert len(hits) == 1, f'zb_is: {len(hits)} matches {hits}'
    return hits[0]


def run(exe):
    """{(flags, bq, current): dl} of that exe's zb_is"""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EDX
    import emu
    from le import LE
    le = LE(open(exe, 'rb').read())
    base2 = (BASE1 + le.obj(1).vsize + 0xFFFF) & ~0xFFFF
    base3 = (base2 + le.obj(2).vsize + 0xFFFF) & ~0xFFFF
    i1, i2, rl = emu.relocate(exe, BASE1, base2, base3)
    imgs = {1: i1, 2: i2, **({3: rl.img3} if rl.img3 else {})}
    bases = {1: BASE1, 2: base2, 3: base3}
    obj, at = _find(le, imgs)
    img = imgs[obj]
    code = bases[obj] + at
    end = bases[3] + len(imgs[3]) if 3 in imgs else base2 + len(imgs[2])
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    size = (end + 0x10FFFF) & ~0xFFFF
    uc.mem_map(0, size)
    for n, b in imgs.items():
        uc.mem_write(bases[n], bytes(b))
    uc.mem_write(SENT, b'\xf4')
    zb = struct.unpack_from('<I', img, at + 5)[0]
    body = bytes(img[at:at + 120])
    sec = struct.unpack_from('<I', body, body.index(b'\x8a\x89') + 2)[0] - 1   # mov cl, [SEC_BQ + 1 + ecx]
    assert struct.unpack_from('<I', body, body.index(b'\xa0') + 1)[0] == sec   # mov al, [SEC_BQ]
    seasonp = struct.unpack_from('<I', body, body.index(b'\x3a\x05') + 2)[0]   # cmp al, [SEASONP]
    n = uc.mem_read(zb, 1)[0]
    assert n >= 1, 'ZB table empty'
    word, idx = struct.unpack('<HB', bytes(uc.mem_read(zb + 1, 3)))
    out = {}
    for flags in range(8):
        for bq in range(3):
            for cur in (0, 1):
                uc.mem_write(zb + 1 + 3, bytes([flags]))
                uc.mem_write(sec + 1 + idx, bytes([bq]))
                uc.mem_write(sec, bytes([40]))
                uc.mem_write(seasonp, bytes([41 if cur else 43]))
                uc.mem_write(STACK, struct.pack('<I', SENT))
                uc.reg_write(UC_X86_REG_ESP, STACK)
                uc.reg_write(UC_X86_REG_EAX, word)
                uc.reg_write(UC_X86_REG_EDX, 0xFFFFFFFF)
                uc.emu_start(code, SENT, count=2000)
                out[flags, bq, cur] = uc.reg_read(UC_X86_REG_EDX) & 0xFF
    return out, f'obj{obj}+{at:#x}'


def text(exe, out):
    md5 = hashlib.md5(open(exe, 'rb').read()).hexdigest()
    rows = [f'{f} {q} {c} {out[f, q, c]}' for f in range(8) for q in range(3) for c in (0, 1)]
    return ('# zb_is (tools/zones.py BSKIP_ASM) run in Unicorn: tools/hosttest/tests/test_zbis_golden.py\n'
            f'build {BUILD_KEY}\nexe {os.path.basename(exe)} md5 {md5}\n'
            '# flags bq current -> dl\n' + '\n'.join(rows) + '\n')


def test_zbis_golden():
    exes = [os.path.join(EXE_DIR, f'{l}.EXE') for l in LANGS if os.path.exists(os.path.join(EXE_DIR, f'{l}.EXE'))]
    assert exes, f'no exe in {EXE_DIR}'
    res = {e: run(e) for e in exes}
    first = res[exes[0]][0]
    for e, (o, where) in res.items():
        assert o == first, f'{e}: zb_is ({where}) differs from {exes[0]}'
        assert set(o.values()) <= {0, 1, 2, 3}, (e, o)
    got = text(exes[0], first)
    if os.environ.get('ZBIS_GOLDEN_WRITE'):
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        open(GOLDEN, 'w').write(got)
        print(f'wrote {GOLDEN} ({len(first)} inputs, zb_is at {res[exes[0]][1]})')
        return
    want = open(GOLDEN).read()
    strip = lambda s: [l for l in s.splitlines() if l[:1].isdigit()]
    assert strip(got) == strip(want), 'zb_is outputs differ from the golden'


if __name__ == '__main__':
    test_zbis_golden()
    print('PASS: zb_is golden')
