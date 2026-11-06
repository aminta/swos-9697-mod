"""Engine P: the engine's state item 'SWC1' in the career save's 'EN' block (trailer.py save_trailer / en_read /
en_finish, swe.c swe_st_save / swe_st_load), on the static image of HT_P_EXE (else c/HTP5: a release-recipe exe built
with HOSTTEST_SYMS=1). No snapshot: the save is save_trailer's own block with no cached team (NUMSEL 0), WriteFile not
reached; the load is en_read + en_finish + swe_st_load on hand-made blocks.

- the save writes SWC1 (its size, swe.SWC1_SIZE) with the header version 1, the career's world byte and (P 5) its
  season (the game's seasonPlaying);
- a block with this build's SWC1 loads byte for byte, the save's version kept (SWC1_LOADED);
- SWC1 grows: a shorter (older) one loads its bytes and the rest zeroed; a longer (newer) one is not this build's:
  zeroed, started as a save without it (version 1, the world byte, SWC1_LOADED 0) - as a save from before P;
- a plain item of another length is still skipped (zeroed: CC);
- with a load-only (retired) item (EN_RETIRE_PROBE=1 builds: 'RPRB', 4 B, its slot in SWE_IMP): the save never
  writes it; a save from before P that has it gets it imported as SWC1 section 'RP' (engine P 3: swe_import), a save
  without it gets no section, and a save with SWC1 never imports (its own sections stay)."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import engine  # noqa: E402
import swe  # noqa: E402
import trailer  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_P_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTP5', 'SWOS', 'ITALIAN.EXE')
GDT_AT, BUF = 0x6000000, 0x6100000


def static_machine(exe):
    """obj1..obj4 of exe relocated (test_registry's bases), their BSS mapped, flat selectors; (uc, le, rd)"""
    import emu
    from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_CS
    tr.EXE, keep = exe, tr.EXE
    try:
        uc, le, sizes, _ = tr._machine()
    finally:
        tr.EXE = keep
    for b, k, n in ((tr.B1, 1, sizes[0]), (tr.B2, 2, sizes[1])):
        top, end = (n + 0xfff) & ~0xfff, (le.obj(k).vsize + 0xfff) & ~0xfff
        if end > top:
            uc.mem_map(b + top, end - top)
    gdt = bytearray(8 * 64)
    gdt[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
    gdt[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
    uc.mem_map(GDT_AT, 0x1000)
    uc.mem_write(GDT_AT, bytes(gdt))
    uc.reg_write(UC_X86_REG_GDTR, (0, GDT_AT, len(gdt) - 1, 0))
    for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
        uc.reg_write(r, emu.DATA_SEL)
    uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
    return uc, le, lambda a, n: bytes(uc.mem_read(a, n))


def _disp(rd, start, n, pat, k=0):
    """the dword after the k-th `pat` in [start, start + n)"""
    code, i = rd(start, n), -1
    for _ in range(k + 1):
        i = code.find(pat, i + 1)
        assert i >= 0, f'{pat.hex()} #{k} not in {start:#x}+{n}'
    return struct.unpack_from('<I', code, i + len(pat))[0]


def _run(uc, fn, stop, regs=None):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP
    sp = tr.STACK - 0x100
    uc.mem_write(sp, struct.pack('<I', tr.RET))
    uc.reg_write(UC_X86_REG_ESP, sp)
    for r, v in (regs or {}).items():
        uc.reg_write(r, v)
    h = uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=stop, end=stop)
    uc.emu_start(fn, stop, count=5_000_000)
    uc.hook_del(h)


def test_swc1():
    syms = EXE[:-4] + '.syms.json'
    if not os.path.exists(EXE) or not os.path.exists(syms):
        return False, f'{EXE} / its .syms.json missing (HT_P_EXE: a release-recipe exe of step P, HOSTTEST_SYMS=1)'
    sy = json.load(open(syms))
    if 'SWC1' not in sy.get('swe', {}):
        return False, 'no swe.SWC1 (a build before engine P)'
    uc, le, rd = static_machine(EXE)
    base = {1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}
    at = lambda m, k: base[sy[m][k][0] or 1] + sy[m][k][1]
    save, en_read, en_finish = (at('trailer', k) for k in ('save_trailer', 'en_read', 'en_finish'))
    swc1, loaded, st_load = at('swe', 'SWC1'), at('swe', 'SWC1_LOADED'), at('swe', 'swe_st_load')
    imp = at('swe', 'SWE_IMP') if 'SWE_IMP' in sy['swe'] else None
    size = swe.SWC1_SIZE
    uc.mem_map(BUF, 0x40000)
    # save_trailer's variables, from its code (trailer.ASM)
    code = rd(save, 0x400)
    numsel = _disp(rd, save, 0x80, b'\x0f\xb7\x05')               # movzx eax, word [NUMSEL]
    selbase = _disp(rd, save, 0x80, b'\x03\x3d')                  # add edi, [SELBASEV]
    roomv = _disp(rd, save, 0x80, b'\x3b\x05')                    # cmp eax, [ROOMV]
    d1 = _disp(rd, save, 0x200, b'\x81\x05')                      # add dword [D1], BLOCK
    guard = _disp(rd, save, 0x10, b'\xa1')                        # mov eax, [CG_GUARDP]
    out = code.find(b'\x61\xff\x25')                              # .skip: popad, jmp [SAVE_TAIL] (a big world)
    out = code.find(b'\x61\xe9') if out < 0 else out              # (or popad, jmp WriteFile)
    assert out > 0, 'save_trailer: no popad / jmp at its end'
    cwb = _disp(rd, at('swe', 'swe_st_save'), 0x40, b'\x0f\xb6\x05')   # swe.c cw_byte: movzx eax, byte [SWE_CWB]
    sea = _disp(rd, at('swe', 'swe_st_save'), 0x40, b'\x0f\xb6\x05', 1)   # (engine P 5: then [SWE_SEASON])
    errs = []

    uc.mem_write(guard, b'\0' * 4)
    uc.mem_write(numsel, b'\0\0')
    uc.mem_write(selbase, struct.pack('<I', BUF))
    uc.mem_write(roomv, struct.pack('<I', 0x30000))
    uc.mem_write(d1, b'\0' * 4)
    uc.mem_write(cwb, b'\x05')
    uc.mem_write(sea, b'\x7e')                                     # (2026: 126)
    uc.mem_write(swc1, bytes(range(1, size + 1)))
    _run(uc, save, save + out + 1)
    n = struct.unpack('<I', rd(d1, 4))[0]
    blk = rd(BUF, n)
    k = blk.find(struct.pack('<H', trailer.EN_MARK))
    items, order = {}, []
    if k < 0 or blk[:2] != struct.pack('<H', trailer.MARK):
        return False, f'save_trailer wrote {n} B: {blk[:8].hex()} (no main block / no EN)'
    p, end = k + 4, k + 4 + struct.unpack_from('<H', blk, k + 2)[0]
    while p + 4 <= end:
        iid, ln = struct.unpack_from('<HH', blk, p)
        items[iid] = blk[p + 4:p + 4 + ln]
        order.append(iid)
        p += 4 + ln
    sid = engine.item_id('SWC1')
    s = items.get(sid)
    want = struct.pack('<HH', 1, 5) + bytes(range(5, 9)) + struct.pack('<H', 126) + bytes(range(11, size + 1))
    if s != want:
        errs.append(f'saved SWC1 {s.hex() if s else None} (want version 1, world 5, season 126, the rest as in memory)')
    rid = engine.item_id('RPRB')
    probe = None
    en_n = _disp(rd, en_read, 0x60, b'\x81\xf9') if b'\x81\xf9' in rd(en_read, 0x60) else rd(en_read, 0x60)[
        rd(en_read, 0x60).find(b'\x83\xf9') + 2]                  # cmp ecx, EN_N
    if rid in items:
        errs.append('the retired probe RPRB was saved')
    probe = en_n == len(order) + 1
    if not probe and en_n != len(order):
        errs.append(f'EN_N {en_n}, items saved {len(order)}')

    entries = _disp(rd, en_read, 0x60, b'\xba')                   # mov edx, EN_ITEMS
    found = _disp(rd, en_read, 0x80, b'\xc6\x81')                 # mov byte [EN_FOUND + ecx], 1
    cc = engine.item_id('CC')
    ccat = next((struct.unpack('<I', rd(entries + 12 * i, 4))[0] for i in range(en_n)
                 if struct.unpack('<H', rd(entries + 12 * i + 8, 2))[0] == cc), None)

    def load(its, d1len=0x30000):
        body = b''.join(struct.pack('<HH', i, len(b)) + b for i, b in its)
        uc.mem_write(BUF, struct.pack('<HH', trailer.EN_MARK, len(body)) + body)
        uc.mem_write(found, b'\0' * (en_n + 1))
        uc.mem_write(d1, struct.pack('<I', d1len))
        uc.mem_write(swc1, b'\xEE' * size)
        if imp is not None:
            uc.mem_write(imp, b'\xEE' * 4)
        if ccat:
            uc.mem_write(ccat, b'\xEE' * 4)
        from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EBX
        _run(uc, en_read, tr.RET, {UC_X86_REG_ESI: BUF, UC_X86_REG_EBX: 0})
        _run(uc, en_finish, tr.RET)
        pr = rd(imp, 4) if imp is not None else None
        _run(uc, st_load, tr.RET)
        return rd(swc1, size), struct.unpack('<I', rd(loaded, 4))[0], rd(ccat, 4) if ccat else None, pr

    cur = struct.pack('<HH', 1, 4) + bytes(range(10, 10 + size - 4))
    got, ver, _, _ = load([(sid, cur)])
    if got != cur or ver != 1:
        errs.append(f'this build\'s SWC1: loaded {got.hex()} version {ver}')
    short = struct.pack('<HH', 1, 4) + bytes(range(10, 26))       # (an older SWC1: 20 B)
    got, ver, _, _ = load([(sid, short)])
    if got != short + bytes(size - len(short)) or ver != 1:
        errs.append(f'a shorter SWC1: {got.hex()} version {ver}')
    uc.mem_write(cwb, b'\x04')
    for tag, its in (('a longer SWC1', [(sid, cur + b'\x55' * 8)]), ('no SWC1', [])):
        got, ver, _, _ = load(its)
        if got != struct.pack('<HH', 1, 4) + bytes(size - 4) or ver != 0:
            errs.append(f'{tag}: {got.hex()} version {ver} (want started: version 1, world 4, SWC1_LOADED 0)')
    if ccat:
        _, _, c, _ = load([(cc, b'\1\2')])
        if c != b'\0' * 4:
            errs.append(f'CC saved 2 B of 4: loaded {c.hex()} (a plain item: skipped, zeroed)')
    if probe:
        rp = struct.pack('<HH', 0x5052, 4) + b'\x11\x22\x33\x44'
        got, ver, _, pr = load([(rid, b'\x11\x22\x33\x44')])
        if pr != b'\x11\x22\x33\x44':
            errs.append(f'the retired probe not read ({pr.hex() if pr else None})')
        if ver != 0 or got != struct.pack('<HH', 1, 4) + bytes(16) + rp + bytes(size - 28):
            errs.append(f'a save from before P with RPRB: SWC1 {got.hex()} (want started + section RP)')
        got, _, _, _ = load([])
        if got != struct.pack('<HH', 1, 4) + bytes(size - 4):
            errs.append(f'no RPRB: SWC1 {got.hex()} (a section imported from nothing)')
        own = cur[:20] + struct.pack('<HH', 0x4141, 2) + b'\x99\x98' + bytes(size - 26)
        got, ver, _, _ = load([(sid, own), (rid, b'\x11\x22\x33\x44')])
        if got != own or ver != 1:
            errs.append(f'SWC1 v1 + RPRB: {got.hex()} (imported over a save of P)')
    return not errs, '; '.join(errs) or (f'saved {len(order)} items ({n} B), SWC1 {size} B version 1 + world + season; loads: '
                                         f'current, shorter (zero tail), longer / missing (started), CC short skipped'
                                         + ('; retired probe never saved, imported as section RP only into a save from'
                                            ' before P' if probe else ''))


def test_swc1_sections():
    """Engine P 6: SWC1's sections (swe.c swc1_find / swc1_add) on the static image of HT_P_EXE, whatever the saved
    bytes hold: an empty state takes a section (id, length, zeroed bytes, the end marker after it when there is room)
    and finds it back; a section that does not fit is refused; a corrupt state (a length past the item, a chain that
    overruns it, no end marker) never makes either routine read or write outside SWC1 (memory hooks), find answers 0
    for what it cannot reach whole, add refuses."""
    syms = EXE[:-4] + '.syms.json'
    if not os.path.exists(EXE) or not os.path.exists(syms):
        return False, f'{EXE} / its .syms.json missing (HT_P_EXE)'
    sy = json.load(open(syms))
    if 'swc1_find' not in sy.get('swe', {}):
        return False, 'no swe.swc1_find (a build before engine P 3)'
    from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
    uc, le, rd = static_machine(EXE)
    at = lambda k: tr.B4 + sy['swe'][k][1]
    swc1, find, add = at('SWC1'), at('swc1_find'), at('swc1_add')
    size, hdr = swe.SWC1_SIZE, 20
    uc.mem_map(BUF, 0x1000)
    lenp = BUF
    stray = []

    def watch(u, access, a, n, v, d):
        if not (swc1 <= a < swc1 + size or tr.STACK - 0x2000 <= a < tr.STACK + 0x100 or lenp <= a < lenp + 4):
            stray.append((d, hex(a)))
    hooks = [uc.hook_add(UC_HOOK_MEM_READ, watch, 'read'), uc.hook_add(UC_HOOK_MEM_WRITE, watch, 'write')]
    errs = []

    def state(body):
        uc.mem_write(swc1, (struct.pack('<HH', 1, 5) + bytes(hdr - 4) + body).ljust(size, b'\0')[:size])

    def f(i):
        uc.mem_write(lenp, b'\xEE' * 4)
        p = tr._call(uc, find, i, lenp) & 0xFFFFFFFF
        return (p - swc1, struct.unpack('<I', rd(lenp, 4))[0]) if p else None

    a = lambda i, n: ((tr._call(uc, add, i, n) & 0xFFFFFFFF) or swc1) - swc1 or None
    state(b'')
    if f(0x4141) is not None:
        errs.append('empty: a section found')
    uc.mem_write(swc1 + hdr, b'\0\0' + b'\x77' * (size - hdr - 2))      # (stale bytes past the end marker)
    got = a(0x4141, 4)
    want = struct.pack('<HH', 0x4141, 4) + bytes(4) + b'\0\0'
    if got != hdr + 4 or rd(swc1 + hdr, 10) != want or f(0x4141) != (hdr + 4, 4):
        errs.append(f'add 4: at {got}, {rd(swc1 + hdr, 10).hex()}, find {f(0x4141)}')
    if a(0x4242, 3) is not None:                                         # (28 + 4 + 3 > 32)
        errs.append('a section past the item added')
    got = a(0x4343, 0)                                                   # (exactly to the end: no marker room)
    if got != size or f(0x4343) != (size, 0) or f(0x4141) != (hdr + 4, 4):
        errs.append(f'add 0 at the end: {got}, find {f(0x4343)}')
    for tag, body, found in (
            ('length past the item', struct.pack('<HH', 7, 0xFFFF), {7: None}),
            ('chain overrun', struct.pack('<HH', 1, 2) + b'ab' + struct.pack('<HH', 2, 0x10), {1: (hdr + 4, 2), 2: None}),
            ('no end marker', struct.pack('<HH', 3, 8) + b'x' * 8, {3: (hdr + 4, 8), 9: None})):
        state(body)
        for i, w in found.items():
            if f(i) != w:
                errs.append(f'{tag}: find {i:#x} {f(i)}, want {w}')
        before = rd(swc1, size)
        if a(0x5555, 1) is not None or rd(swc1, size) != before:
            errs.append(f'{tag}: add not refused / state changed')
    for h in hooks:
        uc.hook_del(h)
    if stray:
        errs.append(f'accesses outside SWC1: {sorted(set(stray))[:6]}')
    return not errs, '; '.join(errs) or ('add / find on an empty state, a full one refused, 3 corrupt states: no access '
                                         'outside SWC1, find 0 for an unreachable section, add refused')
