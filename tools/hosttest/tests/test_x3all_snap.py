"""4.2 x3all baseline (MC 17/11): snapshots taken from a build with ALL of gplay.c in obj3 (fixture x3all_mlt: a Malta
season on the release recipe, labels gplay.csyms.gp_season / gplay.csyms.gp_end_c in obj3 and gplay.gp_end in obj1; its
RECIPE.json regenerates it). Each snapshot: the hit's EIP is the label's address in the label's OWN object (snapshot.py:
never assumed obj1), and gplay.c runs in the emulator both at its obj3 address and through its obj1 thunk (the glue's
bound dword GP_CT), with the same result."""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures', os.environ.get('HT_X3ALL', 'x3all_mlt'))


def test_x3all_snapshots():
    ks = sorted(int(os.path.basename(f)[:-5]) for f in glob.glob(os.path.join(FIX, '[0-9]*.json')))
    if not ks:
        return True, f'SKIP: fixture {FIX} not there'
    assert os.path.isfile(os.path.join(FIX, 'RECIPE.json')), 'the set has no RECIPE.json (snapshot.py writes one)'
    from emu import Machine
    seen = set()
    for k in ks:
        m = Machine(FIX, k)
        lab = m.meta['label']
        mod, name = lab.split('.', 1)
        obj = m.syms[mod][name][0] or 1
        assert m.meta['eip'] == m.lin(lab), (k, lab, hex(m.meta['eip']), hex(m.lin(lab)))
        who = int.from_bytes(m.read('gplay.CAREERTEAM', 2), 'little')
        a, b = m.call('gplay.csyms.gp_stwins_c', who), m.call('gplay.gpx_gp_stwins_c', who)
        assert a == b, (k, a, b)
        seen.add((lab, obj))
    assert {o for _, o in seen} >= {1, 3}, f'labels in obj1 and obj3 wanted: {sorted(seen)}'
    return True, f'{len(ks)} snapshots, EIP = the label in its own object {sorted(seen)}; gp_stwins_c the same in obj3 and through its obj1 thunk'
