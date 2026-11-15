"""tools/import41.py (42-s7import, MC 15/11): the 4.1 side of the old-save import as fixed data.
- test_import41_fixed: tools/import41_fixed.json == what gen() reads from c/REL41rc3 (TMW5.102's byte 25, 4.1's RI layout
  on its data world) - SKIP without that private dir (the build never needs it);
- test_import41_pools: st_ovr's guard (pool_diff): the committed 4.1 layout against an S7-shaped one (Italy 102 -> 144,
  162 slots, pool 36, every other map offset -94): no difference; controls: a pool resized and two entries swapped are
  caught, Italy's own pool size is not a difference."""
import os
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import import41  # noqa: E402


def _ents(lay):
    out, p = [], 1
    for _ in range(lay[0]):
        mo, nm = struct.unpack_from('<HH', lay, p + 2)
        out.append([lay[p], lay[p + 1], mo, nm, list(lay[p + 7:p + 7 + lay[p + 6]])])
        p += 7 + lay[p + 6]
    return out


def _lay(ents):
    return bytes([len(ents)]) + b''.join(bytes([w, f]) + struct.pack('<HH', mo, nm) + bytes([len(ns)]) + bytes(ns)
                                         for w, f, mo, nm, ns in ents)


def test_import41_fixed():
    if not os.path.exists(os.path.join(import41.REL41, 'TMW5.102')):
        return True, f'SKIP: {import41.REL41} missing (private)'
    fx = import41.fixed()
    g = import41.gen()
    assert fx['base'] == bytes.fromhex(g['base']), 'import41_fixed.json base != REL41rc3 TMW5.102'
    assert fx['ri_layout'] == bytes.fromhex(g['ri_layout']), 'import41_fixed.json ri_layout != 4.1 world\'s'
    assert fx['glob'] == g['glob'] and fx['file'] == g['file']
    e = import41.ri_entry(fx['ri_layout'], 5, 102)
    return True, f'base 256 B + RI layout ({fx["ri_layout"][0]} files, Italy {e[:2]} pool {e[4]}) = REL41rc3\'s'


def test_import41_pools():
    lay41 = import41.fixed()['ri_layout']
    e = _ents(lay41)
    s7 = [[5, 144, 0, 162, [36]]] + [[w, f, mo - 94, nm, ns] for w, f, mo, nm, ns in e[1:]]
    assert import41.pool_diff(lay41, _lay(s7), 5, 102, 144) == [], import41.pool_diff(lay41, _lay(s7), 5, 102, 144)
    bad1 = [x[:] for x in s7]
    bad1[2] = bad1[2][:4] + [[5]]
    d1 = import41.pool_diff(lay41, _lay(bad1), 5, 102, 144)
    bad2 = [s7[0], s7[2], s7[1]] + s7[3:]
    d2 = import41.pool_diff(lay41, _lay(bad2), 5, 102, 144)
    assert d1 and d2, (d1, d2)
    return True, f'S7-shaped table: same pools; controls caught (a pool resized: {len(d1)}, two entries swapped: {len(d2)})'
