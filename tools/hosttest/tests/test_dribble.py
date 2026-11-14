"""4.2 dribble.py (the DRIBBLING test, Davide 12/11): per site, the original and the DRIBBLE_TEST exe of every language.
- A: UpdatePlayerSpeed's carrier slowdown runs in Unicorn (the relocated exe, from `mov ax, [esi+Sprite.speed]` to
  `sub [esi+Sprite.speed], ax`): speed 1024 -> 896 on the original (87.5 %), 960 on the test exe (93.75 %); 1250 (the
  fastest) -> 1094 / 1172.
- B: the two hold-back compares are `cmp dword [esi+Sprite.ballDistance], imm32` + `ja short`: 3200 -> 4400 both.
- C: the two `mov word [esi+TeamGeneralInfo.wonTheBallTimer], imm16`: 12 -> 16 both.
- Nothing else: obj1 differs from the original at those bytes only (1 + 2 x 4 + 2 x 2), obj2 identical; without
  DRIBBLE_TEST the patch writes nothing."""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(HERE, '..'))
import dribble                                                  # noqa: E402

ORIG = os.path.join(TOOLS, '..', 'orig')
LANGS = ('ENGLISH', 'ITALIAN', 'FRENCH', 'GERMAN')
BASE1, SCRATCH = 0x100000, 0x1F00000


def _build(lang, on):
    import lepatch
    old = os.environ.get('DRIBBLE_TEST')
    os.environ['DRIBBLE_TEST'] = '1' if on else ''
    try:
        p = lepatch.LEPatch(os.path.join(ORIG, f'{lang}.EXE'))
        dribble.patch(p)
    finally:
        if old is None:
            os.environ.pop('DRIBBLE_TEST', None)
        else:
            os.environ['DRIBBLE_TEST'] = old
    out = os.path.join(tempfile.mkdtemp(prefix='dribble_'), f'{lang}.EXE')
    p.save(out)
    return out


def _carrier(path, a, speed):
    """speed after the A snippet (obj1 offset a = the pattern's start), the sprite at SCRATCH"""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESI
    import emu
    from le import LE
    le = LE(open(path, 'rb').read())
    base2 = (BASE1 + le.obj(1).vsize + 0xFFFF) & ~0xFFFF
    img1, img2, _ = emu.relocate(path, BASE1, base2)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, 0x2000000)
    uc.mem_write(BASE1, img1)
    uc.mem_write(base2, img2)
    a1 = struct.unpack_from('<I', img1, a + 29)[0]              # mov esi, [A1] (8b 35 A1) inside the snippet
    uc.mem_write(a1, struct.pack('<I', SCRATCH))
    uc.mem_write(SCRATCH, b'\0' * 0x100)
    uc.mem_write(SCRATCH + 0x2C, struct.pack('<H', speed))
    uc.reg_write(UC_X86_REG_ESI, SCRATCH)
    uc.emu_start(BASE1 + a, BASE1 + a + 37, count=100)          # (to the end of `sub [esi+2Ch], ax`)
    return struct.unpack('<H', uc.mem_read(SCRATCH + 0x2C, 2))[0]


def test_dribble():
    import re
    from le import LE
    errs = []
    for lang in LANGS:
        orig = os.path.join(ORIG, f'{lang}.EXE')
        lo = LE(open(orig, 'rb').read())
        o1 = lo.obj_bytes(1)
        st = dribble.sites(o1)
        a = re.search(dribble.A, o1, re.S).start()
        off, on = _build(lang, False), _build(lang, True)
        loff, lon = LE(open(off, 'rb').read()), LE(open(on, 'rb').read())
        if loff.obj_bytes(1) != o1:
            errs.append(f'{lang}: without DRIBBLE_TEST obj1 changed')
        n1 = lon.obj_bytes(1)
        want = {}
        for name, at, old, new in st:
            for k in range(len(old)):
                if old[k] != new[k]:
                    want[at + k] = new[k]
        diff = {i: n1[i] for i in range(len(o1)) if o1[i] != n1[i]}
        if diff != want:
            errs.append(f'{lang}: obj1 diff {sorted(hex(i) for i in diff)} != the sites {sorted(hex(i) for i in want)}')
        if lon.obj_bytes(2) != lo.obj_bytes(2):
            errs.append(f'{lang}: obj2 changed')
        for name, at, old, new in st:
            if name.startswith('B') and (n1[at - 3:at] != b'\x81\x7e\x4a' or n1[at + 4] != 0x77
                                         or struct.unpack_from('<I', n1, at)[0] != 4400):
                errs.append(f'{lang}: {name} is not cmp [esi+4Ah], 4400 / ja ({n1[at - 3:at + 5].hex()})')
            if name.startswith('C') and (n1[at - 7:at] != b'\x66\xc7\x86\x8a\x00\x00\x00'
                                         or struct.unpack_from('<H', n1, at)[0] != 16):
                errs.append(f'{lang}: {name} is not mov word [esi+8Ah], 16 ({n1[at - 7:at + 2].hex()})')
        for sp, wo, wn in ((1024, 896, 960), (1250, 1094, 1172)):
            g = (_carrier(orig, a, sp), _carrier(on, a, sp))
            if g != (wo, wn):
                errs.append(f'{lang}: carrier speed {sp} -> {g}, want ({wo}, {wn})')
    return not errs, '; '.join(errs) or (f'{len(LANGS)} languages: carrier 1024 -> 896 / 960, hold-back 3200 -> 4400 x 2, '
                                         'wonTheBallTimer 12 -> 16 x 2; 5 sites only, obj2 identical, off = no change')
