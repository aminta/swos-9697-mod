"""4.2 gphooks (MC 17/11): the one gplay hook registry. Every combination of the hooking modules (none, FPORT, FRND,
both, + the Nazionali / Supercoppa slots) is linked on a fake LE patcher that, like lepatch, asserts on a second fixup
at one site; then the hooks are CALLED through the wired dwords (a model of each module's C: STEP returns non-zero
when it acts else its next's, LEG works and always calls its next, ROW returns its value else its next's) and the call
order and the returns are checked."""
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import gphooks


class FakeP:
    def __init__(self):
        self.fix, self.mem = {}, {}

    def add_ptr(self, objn, off, tobj, toff):
        assert (objn, off) not in self.fix, ('a second fixup at', objn, hex(off))
        self.fix[(objn, off)] = (tobj, toff)
        self.mem[(objn, off)] = toff

    def target(self, objn, off):
        return self.fix[(objn, off)]

    def get(self, objn, off, n):
        return b'\0' * n if (objn, off) not in self.mem else b'\1' * n


def _add(p, off, tobj, toff, objn=1):
    p.add_ptr(objn, off, tobj, toff)


# the hook dwords (gplay .data in obj3) and each module's functions / next dwords (made-up addresses, distinct)
GS = {h: (3, 0x100 + 4 * i) for i, h in enumerate(gphooks.HOOKS)}
MODS = {    # module: {hook: has a next dword}
    'frnd': {'GP_PSTEP': True, 'GP_PLEG': True, 'GP_PROW': True},
    'nazionali': {'GP_PSTEP': True, 'GP_PLEG': True,     # (+ the Supercoppa C's producer, fpml.c / fpmlv.c, 17/11: NEED /
                  'GP_PNEED': True, 'GP_PLEND': True, 'GP_PEND': True,   # LEND / END work then ALWAYS call their next;
                  'GP_PRLINE': False},                   # RLINE = lane 2's fpv_rline_c, no next dword: last in its chain)
    'supercoppa': {'GP_PLEND': True, 'GP_PEND': True, 'GP_PSTEP': True},
    'fpad': {'GP_PSTEP': False, 'GP_PDONE': False, 'GP_PLEG': False, 'GP_PSEAS': False},
}


def _fn(m, h):
    return (4, 0x1000 * (1 + list(MODS).index(m)) + 0x10 * gphooks.HOOKS.index(h))


def _nx(m, h):
    return (4, 0x1000 * (1 + list(MODS).index(m)) + 0x800 + 4 * gphooks.HOOKS.index(h))


def _call(p, h, slot, active, order):
    """Call through a dword: the model of each module's C for hook h."""
    if not p.mem.get(slot):
        return 0
    tgt = p.target(*slot)
    m = next(mm for mm in MODS for hh in MODS[mm] if _fn(mm, hh) == tgt)
    order.append(m)
    nxt = _nx(m, h) if MODS[m][h] else None
    if h == 'GP_PLEG' or h in ('GP_PDONE', 'GP_PSEAS', 'GP_PEND', 'GP_PLEND', 'GP_PNEED'):
        return _call(p, h, nxt, active, order) if nxt else 0
    if m in active:
        return ord(m[0])
    return _call(p, h, nxt, active, order) if nxt else 0


def test_gphooks():
    n = 0
    for k in range(len(MODS) + 1):
        for mods in itertools.combinations(MODS, k):
            gphooks.reset()
            for m in reversed(mods):            # (registration order must not matter)
                for h, has in MODS[m].items():
                    gphooks.register(h, m, _fn(m, h), _nx(m, h) if has else None)
            p = FakeP()
            gphooks.link(p, GS, add_ptr=_add)
            gphooks.check(p)
            want = sorted(mods, key=lambda m: gphooks.ORDER[m])
            for h in gphooks.HOOKS:
                inh = [m for m in want if h in MODS[m]]
                order = []
                r = _call(p, h, GS[h], set(), order)
                if order != inh or r != 0:
                    return False, f'{mods} {h}: called {order} (want {inh}) ret {r}'
                for act in inh:                 # (each module acting alone: the chain stops there for STEP / ROW)
                    order = []
                    r = _call(p, h, GS[h], {act}, order)
                    stops = h in ('GP_PSTEP', 'GP_PROW', 'GP_PRLINE')
                    wo = inh[:inh.index(act) + 1] if stops else inh
                    wr = ord(act[0]) if stops else 0
                    if order != wo or r != wr:
                        return False, f'{mods} {h} {act} active: called {order} ret {r} (want {wo} {wr})'
                n += 1
            sites = sum(len(v) for v in gphooks.LINKED.values())
            if sites != len(p.fix):
                return False, f'{mods}: {len(p.fix)} fixups for {sites} sites'
    # a terminal module (no next dword) before another one: refused at link
    gphooks.reset()
    gphooks.register('GP_PSTEP', 'fpad', _fn('fpad', 'GP_PSTEP'))
    gphooks.ORDER['zz_test'] = 95
    try:
        gphooks.register('GP_PSTEP', 'zz_test', (4, 0x9000))
        try:
            gphooks.link(FakeP(), GS, add_ptr=_add)
            return False, 'a terminal module before another one was linked'
        except AssertionError:
            pass
    finally:
        del gphooks.ORDER['zz_test']
        gphooks.reset()
    # GP_PRLINE: 'nazionali' has no next dword there - alone it links, a later module (supercoppa 30) is refused
    for later, ok in ((None, True), ('supercoppa', False), ('fpad', False)):
        gphooks.reset()
        gphooks.register('GP_PRLINE', 'nazionali', _fn('nazionali', 'GP_PRLINE'))
        if later:
            gphooks.register('GP_PRLINE', later, (4, 0xA000))
        try:
            gphooks.link(FakeP(), GS, add_ptr=_add)
            linked = True
        except AssertionError:
            linked = False
        gphooks.reset()
        if linked != ok:
            return False, f'GP_PRLINE nazionali (terminal) + {later}: linked {linked}, want {ok}'
    # an earlier module with a next dword (frnd 10) before the terminal one: frnd -> nazionali, both called when frnd passes
    gphooks.register('GP_PRLINE', 'frnd', (4, 0xB000), (4, 0xB800))
    gphooks.register('GP_PRLINE', 'nazionali', _fn('nazionali', 'GP_PRLINE'))
    p = FakeP()
    got = gphooks.link(p, GS, add_ptr=_add)
    gphooks.reset()
    if got != {'GP_PRLINE': ['frnd', 'nazionali']} or p.target(4, 0xB800) != _fn('nazionali', 'GP_PRLINE'):
        return False, f'GP_PRLINE frnd + nazionali: {got}'
    # a hook outside the table / a module without an ORDER: refused at register (nobody writes a dword on the side)
    for hook, mod in (('GP_PXXX', 'nazionali'), ('GP_PNEED', 'nobody')):
        try:
            gphooks.register(hook, mod, (4, 0xC000))
            gphooks.reset()
            return False, f'register({hook}, {mod}) accepted'
        except AssertionError:
            pass
    return True, f'{n} hook chains over every combination of {", ".join(MODS)} (incl. none): call order by ORDER, ' \
                 'one fixup per site, STEP / ROW / RLINE stop at the module that acts, LEG / DONE / SEAS / NEED / LEND / END reach every '\
                 'module; GP_PRLINE ends at nazionali (a later module refused)'


if __name__ == '__main__':
    print(test_gphooks())
