"""ripool's IDA_TAB over a split file (S7-G, MC 11/11): ri_ida1 (nasm, run in Unicorn) and ida_bytes.
- dormant: ida_bytes and _asm are today's bytes / text exactly (no split entry: 10-byte headers, global - base);
- shaped (ida_two): 14-byte headers (+ base2, ord2); file 144's 162 slots = globals 192..347 (rows 0..155) + 2283..2288
  (rows 156..161): rows 155 / 156 / 161 get their current identity's areas (a slot's, a pool record's after nslots, its
  own); globals 348..353 (another file's) and 191 alias no slot; a one-run entry (base2 FFFFh) in the same build;
- mutation: the one-run slot code with the 14-byte headers misses run 2 (caught);
- the S7 pack (s7pack output): off_pool on file 144, its slots' globals = globnum's two runs, ida_two."""
import os
import re
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)

IDA, SLT, MAPS, NA, CLUB = 0x4000, 0x3000, 0x2000, 0x3800, 0x3900
WORLD_BYTE = 0x10


def _body(src):
    m = re.search(r'\nri_ida1:.*?\n    ret\n', src, re.S)
    return m.group(0)


def _code(body):
    defs = {'IDA_TAB': IDA, 'SLT': SLT, 'WORLD_BYTE': WORLD_BYTE, 'RI_MAPS': MAPS, 'RI_NA': NA}
    text = ''.join(f'%define {k} {v}\n' for k, v in defs.items()) + 'bits 32\norg 0x1000\n' + body
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 's.asm'), 'w').write(text)
        subprocess.run(['nasm', '-f', 'bin', '-o', os.path.join(d, 's.bin'), os.path.join(d, 's.asm')], check=True)
        return open(os.path.join(d, 's.bin'), 'rb').read()


def _run(code, ida, maps, world, glob):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_ESP
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(0, 0x10000)
    u.mem_write(0x1000, code)
    u.mem_write(IDA, ida)
    u.mem_write(MAPS, b''.join(struct.pack('<H', m) for m in maps))
    u.mem_write(SLT + WORLD_BYTE, bytes((world,)))
    u.mem_write(NA, struct.pack('<I', 1))
    u.mem_write(CLUB, struct.pack('<HB', glob, 0) + b'\xEE')     # (dw global, db base, 1 x db area)
    u.mem_write(0xF000, struct.pack('<I', 0xFFF0))
    u.reg_write(UC_X86_REG_ESP, 0xF000)
    u.reg_write(UC_X86_REG_ESI, CLUB)
    u.emu_start(0x1000, 0xFFF0)
    return u.mem_read(CLUB + 3, 1)[0]


def test_ri_ida():
    import ripool
    errs = []
    g144 = list(range(192, 348)) + list(range(2283, 2289))
    area = lambda i: 1 + i % 9
    # tabs as mkseason.off_pools gives them: (world, file, pools, base, spares, nrec, npool)
    split = (5, 144, [('league', 5, [(g, 5 + i // 18, 0) for i, g in enumerate(g144)], [0xFF] * 3, [0, 1, 2],
                       [[area(i)] for i in range(162)] + [[100 + r] for r in range(3)])], 192, [], 162, 3)
    one = (6, 102, [('league', 1, [(92 + i, 1, 0) for i in range(4)], [0xFF], [0], [[40 + i] for i in range(5)])],
           92, [], 4, 1)
    # dormant: today's bytes / text
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    old = subprocess.run(['git', '-C', TOOLS, 'show', os.environ.get('RI_IDA_REF', '421691e') + ':tools/ripool.py'], capture_output=True, text=True).stdout
    om = {}
    if 'def ida_bytes' not in old or '{SLOT}' in old:
        errs.append('no dormant reference (RI_IDA_REF, default 421691e: ripool.py before the two-run change)')
    else:
        exec(compile(old, 'ripool_old', 'exec'), om)
        if om['ida_bytes']([one]) != ripool.ida_bytes([one]):
            errs.append('dormant ida_bytes changed')
        if om['_asm'](1) != ripool._asm(1) or om['_asm'](3) != ripool._asm(3):
            errs.append('dormant asm changed')
    if ripool.ida_two([one]) or not ripool.ida_two([split, one]):
        errs.append('ida_two')
    ib = ripool.ida_bytes([split, one])
    if ib[0] != 2 or struct.unpack('<HHHHBHH', ib[2:15]) != (192, 0, 162, 165, 1, 2283, 156):
        errs.append(f'split header {ib[:15].hex()}')
    o2 = 1 + 14 + 165
    if struct.unpack('<HHHHBHH', ib[o2 + 1:o2 + 14]) != (92, 162, 4, 5, 1, 0xFFFF, 4):
        errs.append(f'one-run header in a two-run build {ib[o2:o2 + 15].hex()}')
    maps = [0] * 200
    maps[155] = 161 + 1                         # row 155: slot 161's identity
    maps[156] = 256 + 1 + 1                     # row 156: pool record 1 (after the 162 slots)
    maps[162 + 2] = 256 + 0 + 1                 # (the one-run file, slot 2: its pool record 0)
    code = _code(_body(ripool._asm(1, True)))
    cases = [(5, 192, area(0)), (5, 347, area(161)), (5, 2283, 101), (5, 2288, area(161)), (5, 2284, area(157)),
             (5, 348, 0xEE), (5, 353, 0xEE), (5, 191, 0xEE), (5, 2289, 0xEE), (6, 2283, 0xEE),
             (6, 93, 41), (6, 94, 44), (6, 96, 0xEE)]
    for w, g, want in cases:
        got = _run(code, ib, maps, w, g)
        if got != want:
            errs.append(f'world {w} global {g}: area {got} != {want}')
    mut = _code(_body(ripool._asm(1, True)).replace(
        ripool._asm(1, True)[ripool._asm(1, True).index('    mov eax, ebx                        ; its slot: run 2'):
                             ripool._asm(1, True).index('.s2:\n') + 5],
        '    mov eax, ebx\n    movzx edx, word [edi + 1]\n    sub eax, edx\n'))
    if _run(mut, ib, maps, 5, 2283) == 101 and _run(mut, ib, maps, 5, 2288) == area(161):
        errs.append('mutation (no run 2): not caught')
    # the S7 pack: off_pool on file 144 with globnum's runs
    import test_s7pack
    if os.path.isdir(test_s7pack.SRC) and os.path.isfile(test_s7pack.GROUPS):
        import test_globnum
        prev = os.environ.get('SEASON_PACKS')
        test_globnum._env()
        tmp = tempfile.mkdtemp(prefix='riida')
        try:
            import mkseason
            import s7pack
            s7pack.build(test_s7pack.SRC, test_s7pack.GROUPS, os.path.join(tmp, 'ita'))
            pk = mkseason.Pack(os.path.join(tmp, 'ita'))
            t = pk.off_pool()
            pl = t[2][0]
            gs = [g for g, *_ in pl[2]]
            if (t[1], t[3], len(gs), t[5], t[6]) != (144, 192, 162, 162, 36) or gs != g144:
                errs.append(f'S7 off_pool: file {t[1]} base {t[3]} {len(gs)} slots, nrec {t[5]}, npool {t[6]}')
            if pl[1] != 5 or sorted({d for _, d, _ in pl[2]}) != list(range(5, 14)):
                errs.append(f'S7 off_pool: low {pl[1]}, divisions {sorted({d for _, d, _ in pl[2]})}')
            if not ripool.ida_two([t]) or ripool._runs2(t[3], pl[2]) != (2283, 156):
                errs.append('S7 off_pool: not two IDA runs (2283, 156)')
            if not pl[5] or len(pl[5]) != 162 + 36:
                errs.append(f'S7 off_pool: ida rows {len(pl[5]) if pl[5] else 0}')
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            if prev is None:
                os.environ.pop('SEASON_PACKS', None)
            else:
                os.environ['SEASON_PACKS'] = prev
    return not errs, '; '.join(errs) or (f'dormant ida_bytes / asm as today; two-run: rows 0 / 155 / 156 / 161 / 157 '
                                         f'(their identities: own, a slot, a pool record after nslots), 348 / 353 / '
                                         f'191 / 2289 / another world alias nothing, a one-run entry in the same '
                                         f'build; mutation (no run 2) caught; S7 pack: off_pool on 144, 162 slots '
                                         f'192..347 + 2283..2288, groups 5..13, 36 pool, IDA (2283, 156)')
