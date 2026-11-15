"""obj4pack (tools/obj4pack.py, MC 15/11: the 4.2 rc freeze's layout proposer) on a synthetic obj4 map:
- the map table's order and classes (release / '(test)' / '(4.3)', obj4check.TEST_ONLY);
- holes between release bands removed, a fixed non-map band jumped over, every band sized used + floor rounded to
  0x100 (a band under its floor grows, an oversized one shrinks; 128 B for SETPIECE / DIFF2 / SPX);
- test-only bands moved from 0x30000 with their sizes (after the ones already there), a release band with no byte in
  any exe moved with them (--ship packs it), the 4.3 reservations after the last release band;
- the swreg patch: literal AT / END lines only, a band's inner constant (NAME_CC) moved with it, a chain assert that
  the new values break reported, the patched module = the plan;
- --verify's compare: the planned layout PASSes; controls: a band whose used bytes grew past its packed size and a
  swreg value off the plan are caught.
HT_OBJ4PACK_REL=<c/RELxx>: a proposal on the real release dir too (report only)."""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import obj4pack as op  # noqa: E402

MAP = """# x
## obj4 map (synthetic)

| band | range | owner | linked |
|---|---|---|---|
| KITS | 0xF000..0x11000 | p | always |
| OBJ1MV | 0x15000..0x16800 | s | always |
| SETPIECE | 0x16800..0x17000 | d | >= 128 B left |
| FPORT | 0x17000..0x19000 | m | GP_PORT |
| S7GEO | 0x19000..0x1A000 | p | GP_S7 |
| PRACTICE | 0x1C800..0x1D400 | s | x |
| MKTHOOK (4.3) | 6 KB | c | reservation |
| SESTRIP | 1 KB, temporary 0x22C00..0x23000 | s | x |
| SP_METER (test) | 0x30000..0x34000 | d | test |

## next section
| NOTABAND | x | x | x |
"""
SWREG = """REG_AT = 0x1800
OBJ4_END = 0x2000
T3_AT = 0xD000
T3_END = 0xE000
KITS_AT = 0xF000
KITS_END = 0x11000                      # (a comment kept)
WALL_AT = 0x11400                       # a fixed non-map band inside the packed range
WALL_END = 0x11800
OBJ1MV_AT = 0x15000
OBJ1MV_END = 0x16800
OBJ1MV_CC = 0x15C00
SETPIECE_AT = 0x16800
SETPIECE_END = 0x17000
FPORT_AT = 0x17000
FPORT_END = 0x19000
S7GEO_AT = 0x19000
S7GEO_END = 0x1A000
PRACTICE_AT = 0x1C800
PRACTICE_END = 0x1D400
MKTHOOK_AT = 0x1E800
MKTHOOK_END = 0x20000
SESTRIP_AT = 0x22C00
SESTRIP_END = 0x23000
SP_METER_AT = 0x30000
SP_METER_END = 0x34000
assert OBJ1MV_AT < OBJ1MV_CC < OBJ1MV_END, 'OBJ1MV_CC inside'
assert OBJ1MV_END <= FPORT_AT < FPORT_END <= PRACTICE_AT, 'chain'
"""
USED = {'KITS': 8028, 'OBJ1MV': 3200, 'SETPIECE': 900, 'FPORT': None, 'S7GEO': None, 'PRACTICE': 1884,
        'MKTHOOK': None, 'SESTRIP': 505, 'SP_METER': None, 'T3': 2000, 'WALL': 100, 'REG': 1100}


def setup(ship=()):
    ns = op.oc.swreg_ns(SWREG)

    class M:
        pass
    m = M()
    m.__dict__.update(ns)
    bl = op.oc.bands(m)
    mp = op.read_map(MAP, {b[0] for b in bl})
    used = {x: dict(USED) for x in ('SWOS/ITALIAN.EXE', 'gog/GERMAN.EXE')}
    used['gog/GERMAN.EXE']['OBJ1MV'] = 3250                         # (the max over the exes counts)
    plan, notes, pages = op.pack(bl, mp, used, ship)
    return bl, mp, used, plan, notes, pages


def test_obj4pack_map():
    bl, mp, *_ = setup()
    assert mp == [('KITS', 'release'), ('OBJ1MV', 'release'), ('SETPIECE', 'release'), ('FPORT', 'test'),
                  ('S7GEO', 'release'), ('PRACTICE', 'release'), ('MKTHOOK', '4.3'), ('SESTRIP', 'release'),
                  ('SP_METER', 'test')], mp
    return True, f'{len(mp)} rows, classes from (test) / (4.3) / TEST_ONLY, the next section ignored'


def test_obj4pack_layout():
    bl, mp, used, plan, notes, pages = setup()
    P = {p['name']: p for p in plan}
    rel = [p for p in plan if p['cls'] == 'release']
    assert [p['name'] for p in rel] == ['KITS', 'OBJ1MV', 'SETPIECE', 'PRACTICE', 'SESTRIP'], rel
    for p in rel:
        assert p['at'] % 0x100 == 0 and p['end'] % 0x100 == 0, p
        assert p['end'] - p['at'] - p['used'] >= p['floor'], p                        # floors met
        assert p['end'] - p['at'] - p['used'] < p['floor'] + 0x100, p                 # no more than the rounding
    assert P['KITS']['end'] == 0x11100 and P['KITS']['at'] == 0xF000, P['KITS']          # KITS grown (164 -> 420 B)
    assert P['SETPIECE']['floor'] == 128
    assert P['OBJ1MV']['used'] == 3250
    assert P['OBJ1MV']['at'] == 0x11800 and any('jumps over fixed band WALL' in n for n in notes), (P['OBJ1MV'], notes)
    for a, b in zip(rel[1:], rel[2:]):
        assert a['end'] == b['at'], (a, b)                                              # no holes after the wall
    assert pages == -(-rel[-1]['end'] // 0x1000)
    assert P['MKTHOOK']['at'] == rel[-1]['end'] and P['MKTHOOK']['end'] - P['MKTHOOK']['at'] == 0x1800
    assert P['FPORT']['at'] == 0x34000 and P['FPORT']['end'] == 0x36000, P['FPORT']    # after SP_METER, size kept
    assert P['SP_METER']['at'] == 0x30000
    assert P['S7GEO']['cls'] == 'release-unlinked' and P['S7GEO']['at'] >= 0x30000, P['S7GEO']
    assert any(n.startswith('S7GEO: release map band with no byte') for n in notes), notes
    _, _, _, plan2, _, _ = setup(ship=['S7GEO'])
    P2 = {p['name']: p for p in plan2}
    assert P2['S7GEO']['cls'] == 'release' and P2['S7GEO']['end'] - P2['S7GEO']['at'] == 0x1000, P2['S7GEO']
    return True, (f"KITS 0xf000..{P['KITS']['end']:#x}, wall jumped, {len(rel)} release bands to {rel[-1]['end']:#x}, "
                  f"OBJ4_PAGES {pages:#x}, FPORT -> {P['FPORT']['at']:#x}, S7GEO unlinked -> test (--ship packs it)")


def test_obj4pack_swreg_patch():
    bl, mp, used, plan, notes, pages = setup()
    new, inner, fails, g = op.swreg_patch(SWREG, plan)
    for p in plan:
        assert (g[p['name'] + '_AT'], g[p['name'] + '_END']) == (p['at'], p['end']), p
    P = {p['name']: p for p in plan}
    assert g['OBJ1MV_CC'] == 0x15C00 + P['OBJ1MV']['at'] - 0x15000 and any(s.startswith('OBJ1MV_CC') for s in inner)
    assert 'KITS_END = 0x11100                      # (a comment kept)' in new, new
    assert any('chain' in f for f in fails) and not any('OBJ1MV_CC inside' in f for f in fails), fails
    old_l, new_l = SWREG.splitlines(), new.splitlines()
    changed = [o for o, n in zip(old_l, new_l) if o != n]
    assert all(o.split('=')[0].strip().endswith(('_AT', '_END', '_CC')) for o in changed), changed
    assert g['T3_AT'] == 0xD000 and g['WALL_AT'] == 0x11400                 # fixed bands untouched
    return True, f'{len(changed)} lines changed, OBJ1MV_CC moved, chain assert reported'


def test_obj4pack_verify_compare():
    bl, mp, used, plan, notes, pages = setup()
    new, inner, fails, g = op.swreg_patch(SWREG, plan)

    class M:
        pass
    m = M()
    m.__dict__.update(g)
    bl2 = op.oc.bands(m)
    prop = dict(rel='x', plan=plan, used=used)
    assert op.compare(prop, bl2, used) == [], op.compare(prop, bl2, used)
    now = {x: dict(d) for x, d in used.items()}
    P = {p['name']: p for p in plan}
    now['SWOS/ITALIAN.EXE']['PRACTICE'] = P['PRACTICE']['end'] - P['PRACTICE']['at'] - 100   # (grown into the floor)
    e = op.compare(prop, bl2, now)
    assert any('PRACTICE: overflows its packed size' in x for x in e), e
    g2 = dict(g, SESTRIP_END=g['SESTRIP_END'] + 0x100)
    m.__dict__.update(g2)
    e2 = op.compare(prop, op.oc.bands(m), used)
    assert any(x.startswith('swreg SESTRIP') for x in e2), e2
    e3 = op.compare(prop, op.oc.bands(m), used)
    return True, f'plan PASS; controls: PRACTICE overflow caught, SESTRIP off the plan caught ({len(e3)} finding)'


def test_obj4pack_real():
    rel = os.environ.get('HT_OBJ4PACK_REL')
    if not rel:
        return True, 'SKIP: HT_OBJ4PACK_REL not set'
    plan, rep, diff = op.propose(rel)
    return True, 'report only: ' + ' | '.join(rep.splitlines()[2:5])
