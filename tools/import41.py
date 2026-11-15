"""The 4.1 side of the old-save import (4.2 S7, n7-p4.md §4 / §9c, MC 15/11: 42-s7import): what a 4.1 World 2026-27
career save means, as FIXED data - 4.1 is released, its saves never change. The import (sreg_import.c, linked at
obj4+SREG2_AT by sreg.py) reads a 4.1 save's bytes through these:
- base: each 4.1 file-102 slot's base division (DATA\\TMW5.102 record +25; the slot's division = base + the save's
  someLeaguesTable delta at the slot's global), 256 bytes;
- glob: 4.1's global numbers of file 102 (sreg_slt_import's run table: one run of 256 from 92);
- ri_layout: 4.1's RI table (sreg.ri_layout of mkseason.off_pools() on 4.1's world: Italy on 102, 256 slots, pool 42).
They live in tools/import41_fixed.json (committed): the build never needs a 4.1 release dir. gen() writes the file from
one (default c/REL41rc3: its TMW5.102 has the same md5 as REL41's and REL411's, its data world world5tm-403c19);
test_import41 compares the file with that dir when it is present."""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'import41_fixed.json')
M = os.path.expanduser('~/swos-mod')
REL41 = os.path.join(M, 'c', 'REL41rc3', 'SWOS', 'DATA')
WORLD41 = 'world5tm-403c19'                     # (REL41rc3's data world: its build.log)
FILE41 = 102


def base_of(data_dir=REL41):
    """TMW5.102's byte 25 per record (4.1's 256 slots)."""
    d = open(os.path.join(data_dir, 'TMW5.102'), 'rb').read()
    n = struct.unpack('>H', d[:2])[0]
    assert n == 256 and len(d) == 2 + 684 * n, ('import41: TMW5.102 is not 4.1\'s one-file Italy', n, len(d))
    return bytes(d[2 + 684 * i + 25] for i in range(n))


def layout_of(world=WORLD41):
    """sreg.ri_layout of 4.1's off-file pools: mkseason on 4.1's data world (test_globnum's environment)."""
    import sys
    sys.path.insert(0, os.path.join(HERE, 'hosttest', 'tests'))
    import test_globnum
    prev, prevw = os.environ.get('SEASON_PACKS'), os.environ.get('HT_GLOB_WORLD')
    os.environ['HT_GLOB_WORLD'] = world
    test_globnum._env()
    import mkseason
    import sreg
    old_en = mkseason.ENABLED
    try:
        mkseason.ENABLED = os.environ['SEASON_PACKS'].split(',')
        mkseason.packs.__dict__.pop('cache', None)
        return sreg.ri_layout(mkseason.off_pools())
    finally:
        mkseason.ENABLED = old_en
        mkseason.packs.__dict__.pop('cache', None)
        for k, v in (('SEASON_PACKS', prev), ('HT_GLOB_WORLD', prevw)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def gen(data_dir=REL41, world=WORLD41):
    lay = layout_of(world)
    return {'about': '4.1 World 2026-27 saves, fixed (tools/import41.py)', 'file': FILE41,
            'base': base_of(data_dir).hex(), 'glob': [[FILE41, [[92, 256]]]], 'ri_layout': lay.hex()}


def fixed():
    with open(PATH) as f:
        j = json.load(f)
    return dict(file=j['file'], base=bytes.fromhex(j['base']), glob=j['glob'], ri_layout=bytes.fromhex(j['ri_layout']))


def glob_bytes(runs):
    """sreg_slt_import's run table: db files; per file db file, db runs, runs x (dw first, dw count)."""
    return bytes([len(runs)]) + b''.join(bytes([f, len(rs)]) + b''.join(struct.pack('<HH', a, c) for a, c in rs)
                                         for f, rs in runs)


def ri_entry(lay, world, file):
    """(map offset, slots, pool index, queue offset, pool sizes) of (world, file) in a layout, None if absent."""
    p, pi, qo = 1, 0, 0
    for _ in range(lay[0]):
        w, f = lay[p], lay[p + 1]
        moff, nmap = struct.unpack_from('<HH', lay, p + 2)
        ns = list(lay[p + 7:p + 7 + lay[p + 6]])
        if (w, f) == (world, file):
            return moff, nmap, pi, qo, ns
        pi += len(ns)
        qo += sum(ns)
        p += 7 + len(ns)
    return None


def pool_diff(lay41, lay7, world, file41, file7):
    """st_ovr (statespec, an after_load BEFORE the import) reads RI_STATE.ovr / RI_OVR_KEYS by POOL INDEX, never maps[]:
    its overrides at an imported load are right only if every pool keeps its index and size across the two tables
    (Italy's file 102 -> 144 the one renamed entry; Italy's own pool size may change, it has no state contests).
    Returns the differences ([] = the same pools in the same order; MC 15/11: no st_ovr re-run then)."""
    def pools(lay, it_file):
        out, p = [], 1
        for _ in range(lay[0]):
            w, f, ns = lay[p], lay[p + 1], list(lay[p + 7:p + 7 + lay[p + 6]])
            key = (w, 'ITALY') if (w, f) == (world, it_file) else (w, f)
            out += [(key, j, None if key[1] == 'ITALY' else n) for j, n in enumerate(ns)]
            p += 7 + len(ns)
        return out
    a, b = pools(lay41, file41), pools(lay7, file7)
    return [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y] + ([('count', len(a), len(b))] if len(a) != len(b) else [])


if __name__ == '__main__':
    j = gen()
    with open(PATH, 'w') as f:
        json.dump(j, f, indent=1)
        f.write('\n')
    lay = bytes.fromhex(j['ri_layout'])
    print(f'import41: {PATH}: base {len(j["base"]) // 2} B, ri_layout {len(lay)} B ({lay[0]} files), '
          f'Italy {ri_entry(lay, 5, FILE41)}')
