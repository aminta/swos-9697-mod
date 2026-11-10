"""S7-G (MC 11/11): file 144's global numbers through globnum.glob - World 2026-27's numbering (the release recipe's
world data, HT_GLOB_WORLD, default world5tm-s1rank-int3), Italy shaped as S7 option (i): file 102 = Serie A + B + C
(100 rows), file 144 = Serie D 9 x 18 (162 rows), the stand-ins off-file (pool 253) as in 4.1.
- dormant (the one-file pack): no split, guests.alloc as in 4.1, every file one run;
- shaped: file 144 = run 1 right after file 102 (192..347) + run 2 after the guests (2283..2288): 162 numbers, unique,
  below bigtables.LIMIT, overlapping no other file's run, no guest file, not the reserved 1730..1849; the guests keep
  their dormant numbers; glob() = base + ordinal for every other file; exe_split = (5, 144, 156, 2283);
- refusals: too few free numbers (a smaller limit) and a missing file A raise GlobError, never a fallback;
- the exe side: worldpool's wp_glob (nasm, run in Unicorn) for pool 190, file 144 ordinals 0 / 155 / 156 / 161 in
  world 5, file 144 in world 4 (its own base) and another file - and without SPLIT_* the bytes of the 4.1 stub."""
import os
import re
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
M = os.path.expanduser('~/swos-mod')


def _env():
    w = os.path.join(M, 'internal', 'world2526', os.environ.get('HT_GLOB_WORLD', 'world5tm-s1rank-int3'))
    root = os.path.dirname(TOOLS)
    eu = ','.join(sorted(os.path.join(root, 'packs', 'europe-1984-85', d) for d in
                         os.listdir(os.path.join(root, 'packs', 'europe-1984-85'))
                         if os.path.isdir(os.path.join(root, 'packs', 'europe-1984-85', d))))
    files = [ln.split()[0].lower() for ln in open(w + '.txt') if ' file ' in ln]
    os.environ['SEASON_PACKS'] = ','.join(['ddr-1988-89', 'italia-1947-48', 'world-cup-1934', eu]
                                          + [os.path.join(w, f) for f in files])


def _shape(pk):
    """S7 option (i) in memory: what s7pack.py's pack gives mkseason once it loads two-file leagues (div_file)."""
    pk.files['league_b'] = (144, 160)                   # (s7pack --base: the test override, ignored by glob)
    pk.count['league'], pk.count['league_b'] = 100, 162


def test_globnum():
    prev = os.environ.get('SEASON_PACKS')
    _env()
    try:
        return _test()
    finally:
        if prev is None:
            os.environ.pop('SEASON_PACKS', None)
        else:
            os.environ['SEASON_PACKS'] = prev


def _test():
    import bigtables
    import globnum
    import guests
    import mkseason
    out, bad = [], []
    g0 = guests.alloc()
    if globnum.split(5) or globnum.exe_split() is not None:
        bad.append(f'dormant: a split {globnum.split(5)}')
    it = next(pk for pk in mkseason.packs() if pk.world == 5 and pk.files.get('league', (0,))[0] == 102)
    if it.files != {'league': (102, 92), 'pool': (253, 0)} or it.count['league'] != 256:
        bad.append(f'dormant Italy pack {it.files} {it.count}')
    others = {(pk.meta.get('id'), f): (pk, b) for pk in mkseason.packs() + mkseason.nationals() if pk.world == 5
              for _, (f, b) in pk.files.items()}
    saved = dict(it.files), dict(it.count)
    _shape(it)
    globnum._split_cached.cache_clear()
    try:
        g1 = guests.alloc()
        sp = globnum.split(5)
        nums = [globnum.glob(it, 144, i) for i in range(162)]
        if g1 != g0:
            bad.append(f'guests moved: {g0} -> {g1}')
        if sp != {144: [(192, 156), (2283, 6)]}:
            bad.append(f'runs {sp}')
        if len(set(nums)) != 162 or max(nums) >= bigtables.LIMIT:
            bad.append(f'numbers: {len(set(nums))} unique, max {max(nums)}')
        used = {}
        for lo, hi, f in globnum.file_runs(5):
            for g in range(lo, hi):
                used.setdefault(g, f)
        hit = sorted({used[g] for g in nums if g in used and used[g] != 253})
        if hit:
            bad.append(f'overlaps files {hit}')
        gs = {g for f, b in g1.items() for g in range(b, b + guests.counts()[f])}
        if gs & set(nums) or set(globnum.RESERVED) & set(nums):
            bad.append('overlaps the guests or 1730..1849')
        for (pid, f), (pk, b) in others.items():
            if f != 144 and pk.count.get(next(k for k, v in pk.files.items() if v[0] == f), 0) \
                    and globnum.glob(pk, f, 1) != b + 1:
                bad.append(f'{pid} file {f}: glob {globnum.glob(pk, f, 1)} != {b} + 1')
        if globnum.glob(it, 102, 99) != 191 or globnum.base(it, 144) != 192:
            bad.append('file 102 / 144 base')
        if globnum.exe_split() != (5, 144, 156, 2283):
            bad.append(f'exe_split {globnum.exe_split()}')
        if bigtables.world_maxg(5) != bigtables.LIMIT:
            bad.append(f'world_maxg {bigtables.world_maxg(5)}')
        for why, f in (('limit 2285', lambda: globnum.split(5, limit=2285)),
                       ('no file A', lambda: globnum.run1(5, [p for p in mkseason.packs() if p is not it] + [_noa(it)]))):
            try:
                f()
                bad.append(f'{why}: not refused')
            except globnum.GlobError as e:
                out.append(f'{why} refused ({e})')
        out.append(f'file 144: {sp[144]}, guests kept {g1}')
    finally:                                            # (one process runs every test: leave the pack as loaded)
        it.files, it.count = saved
        globnum._split_cached.cache_clear()
    ok, msg = _stub()
    if not ok:
        bad.append(msg)
    out.append(msg)
    return not bad, '; '.join(bad or out)


def _noa(pk):
    class P:
        pass
    q = P()
    q.world, q.meta = pk.world, pk.meta
    q.files = {'league_b': pk.files['league_b'], 'league': (102, 92)}
    q.count = {'league_b': 162}
    return q


def _asm(defs):
    import worldpool
    src = worldpool.ASM
    m = re.search(r'%ifdef WP_GLOB\n(.*?\n    ret\n)%endif\n', src, re.S)
    body = ''.join(f'%define {k} {v}\n' for k, v in defs.items()) + 'bits 32\norg 0x1000\n' + m.group(1)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 's.asm'), 'w').write(body)
        subprocess.run(['nasm', '-f', 'bin', '-o', os.path.join(d, 's.bin'), os.path.join(d, 's.asm')], check=True)
        return open(os.path.join(d, 's.bin'), 'rb').read()


def _stub():
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP
    A0, WCUR, REC = 0x8000, 0x8010, 0x9000
    base = {'A0': A0, 'POOLG': 2282, 'POOL_FILE': 190}
    split = {'WCUR': WCUR, 'SPLIT_FILE': 144, 'SPLIT_WORLD': 5, 'SPLIT_N1': 156, 'SPLIT_B2': 2283}
    old = bytes.fromhex('8b35' + struct.pack('<I', A0).hex() + '803ebe7504' + '66b8ea08' + '66894602c3')
    plain = _asm(base)
    if plain != old:
        return False, f'wp_glob without SPLIT_*: {plain.hex()} != the 4.1 stub {old.hex()}'
    code = _asm({**base, **split})
    cases = [(5, 190, 3, 77, 2282), (5, 144, 0, 192, 192), (5, 144, 155, 347, 347), (5, 144, 156, 348, 2283),
             (5, 144, 161, 353, 2288), (4, 144, 160, 1100, 1100), (5, 102, 200, 292, 292)]
    bad = []
    for w, f, o, ax, want in cases:
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0, 0x10000)
        u.mem_write(0x1000, code)
        u.mem_write(A0, struct.pack('<I', REC))
        u.mem_write(WCUR, bytes((w,)))
        u.mem_write(REC, bytes((f, o, 0, 0)))
        u.mem_write(0xF000, struct.pack('<I', 0xFFF0))
        u.reg_write(UC_X86_REG_ESP, 0xF000)
        u.reg_write(UC_X86_REG_EAX, 0x5A5A0000 | ax)
        u.emu_start(0x1000, 0xFFF0)
        got = struct.unpack('<H', bytes(u.mem_read(REC + 2, 2)))[0]
        if got != want:
            bad.append(f'world {w} file {f} ord {o}: {got} != {want}')
    return not bad, '; '.join(bad) or f'wp_glob: 4.1 bytes without SPLIT_*, {len(cases)} cases in Unicorn'
