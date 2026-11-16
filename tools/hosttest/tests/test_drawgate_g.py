"""Root fix G (MC 12/11): drawgate's pot / fill / field sweeps, host only (conti.c natively; no build, no DOSBox).

- compositions(): distinct pot contents, each association's clubs together from every pot, within the cap;
- pot_sweep() refuses an illegal multiset (an association with ng + 1 clubs under A_NO: no draw exists) - the
  sweep sees a refusal - and passes a legal one in every composition;
- fill_sweep(): PASS on this conti.c; FAIL on 9b14728's parent (the group fill past the association rule: hold_rec's
  Sud groups, 0x11102) - the sweep finds the bug the harness found in DOSBox;
- field(): the 4.2 hold_rec dump (runs-acl2h-field, private) FAILs; skipped when the run dir is not there.
The world data: W2627REL_DATA (default world5tm-h2), as the gates."""
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)
import drawgate  # noqa: E402

FIELD = os.path.expanduser('~/swos-mod/internal/swostest/runs-acl2h-field/world_conti_hold_rec_w84_2')


def _world():
    drawgate.world_spec()
    import conti
    return conti


def test_compositions():
    rnd = random.Random(1)
    asb = bytes([1] * 4 + [2] * 3 + [3] * 3 + [4] * 6)      # (16 clubs, 4 pots of 4)
    cs = drawgate.compositions(asb, 4, 4, rnd)
    assert 0 < len(cs) <= drawgate.NPOT
    keys = set()
    for o in cs:
        assert sorted(o) == list(range(16))
        k = tuple(tuple(sorted(asb[i] for i in o[p * 4:(p + 1) * 4])) for p in range(4))
        assert k not in keys, 'a composition twice'
        keys.add(k)
    for a in (1, 2, 3, 4):                                  # (a's clubs together from pot 1: in the set)
        n = asb.count(a)
        assert any(sum(1 for i in o[:4] if asb[i] == a) == min(4, n) for o in cs), a


def test_pot_sweep_refuses_illegal():
    conti = _world()
    L = drawgate.native()
    ng, gs = 4, 4
    base = dict(c=0, j=0, rule=1, ng=ng, gs=gs, pr=False, via=False, region={}, exact=[], loose=[], wvar=None)
    legal = dict(base, direct={1: 4, 2: 4, 3: 4, 4: 4}, avail={}, nvar=0)
    bad = dict(base, direct={1: 5, 2: 3, 3: 4, 4: 4}, avail={}, nvar=0)   # (5 of one association, 4 groups)
    names = ['x', 'a1', 'a2', 'a3', 'a4']
    cups = [('t', 'cup')]
    ok = drawgate.pot_sweep([legal], L, cups, names, quiet=True)
    assert ok[0]['compositions'] and not ok[0]['nfail'], ok
    no = drawgate.pot_sweep([bad], L, cups, names, quiet=True)
    assert no[0]['nfail'] == no[0]['draws'], no              # (every draw refused: none exists)
    del conti


def test_fill_sweep_finds_9b14728():
    # (MC 16/11: the sweep is deterministic - fixed seeds 7/3/11/19/23/31 - so there is no retry: a result that depends on load is a
    #  build race, never a pass to hope for. Every native library is compiled into its own mkdtemp dir, nothing shared.)
    _world()
    r0 = drawgate.fill_sweep(['conmebol'], quiet=True)
    assert not r0['fails'], r0['fails'][:3]
    t = tempfile.mkdtemp()
    old = os.path.join(t, 'conti_pre9b.c')
    src = subprocess.run(['git', '-C', TOOLS, 'show', '9b14728~1:tools/conti.c'], capture_output=True)
    if src.returncode:                                      # (a checkout without that history)
        return
    open(old, 'wb').write(src.stdout)
    r = drawgate.fill_sweep(['conmebol'], L=drawgate.native(old), quiet=True)
    assert r['fails'], 'the fill sweep missed the pre-9b14728 Sud groups refusal (first sweep)'
    assert any('0x11102' in str(f[4]) or 'refused' in str(f[4]) for f in r['fails']), r['fails'][:3]


def test_field_hold_rec_dump():
    if not os.path.isdir(os.path.join(FIELD, 'ctsd_dump')):
        return                                              # (private run dir)
    r = drawgate.field(FIELD, nseeds=16, quiet=True)
    assert r['refused'] or r['field'], 'the pre-fix hold_rec field passed'


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
            print('ok', k)
