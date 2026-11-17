"""4.2 gplay hook registry (MC 17/11, rule 0): ONE mechanism for every module that hooks gplay.c's hook dwords.

gplay.c exposes function-pointer dwords (GP_PSTEP sc_step_c's head, GP_PLEG gp_rec, GP_PDONE, GP_PSEAS, GP_PROW
gp_scrow_c's head, and the Supercoppa C's GP_PLEND / GP_PEND when its build has them). Any number of modules may hook
the same dword. Each module registers, during its own patch, the function it puts there and, if it can pass the call
on, the address of its own "next" dword. link() then wires the chain once, at link time, in the declared ORDER:

    slot -> first module's function; module[i]'s next dword -> module[i + 1]'s function; the last one's next stays 0

with exactly one fixup per site (lepatch's add_ptr asserts on a second one). A module without a next dword ends the
chain: it may only be the last one registered for that hook (asserted). No module writes a hook dword itself.

    gphooks.register('GP_PSTEP', 'frnd', syms['fr_step'], syms['FR_NSTEP'])   # in frnd.patch
    gphooks.register('GP_PSTEP', 'fpad', syms['fp_step'])                     # in fpad.patch (terminal)
    gphooks.link(p, gplay.LABELS)                                             # patch.py, once, after every module
    gphooks.check(p)                                                          # patch.py, before save

Call semantics (each module's C): a STEP-like hook returns non-zero when it acted, else returns its next's result
(or 0); a LEG-like (void) hook does its work and always calls its next; a ROW-like hook returns its value or its
next's. tools/hosttest/tests/test_gphooks.py links every combination and checks the order and the returns.
"""
import struct

# the declared chain order per module (lower = called first). A new module adds its line here, nowhere else.
ORDER = {
    'frnd': 10,         # 4.2 preseason friendlies (frstep.c): before the season's other slot-4 contests
    'nazionali': 20,    # 5.0 lane 1 (session Nazionali exe)
    'supercoppa': 30,   # the Supercoppa C (GP_PLEND / GP_PEND)
    'fpad': 90,         # the fixture port's adapter (fpad.c): the end of every chain it is in
}
HOOKS = ('GP_PSTEP', 'GP_PDONE', 'GP_PLEG', 'GP_PSEAS', 'GP_PROW', 'GP_PLEND', 'GP_PEND')

REG = {}                # hook -> [(module, target (obj, off), next (obj, off) or None)]
LINKED = {}             # hook -> [(site (obj, off), target (obj, off))]: what link() wrote, for check()


def reset():
    """patch.py, at the start of every exe: a fresh registry."""
    REG.clear()
    LINKED.clear()


def register(hook, module, target, nxt=None):
    assert hook in HOOKS, ('gphooks: unknown hook', hook)
    assert module in ORDER, ('gphooks: module without a declared ORDER', module)
    assert all(m != module for m, _, _ in REG.get(hook, ())), ('gphooks: registered twice', hook, module)
    REG.setdefault(hook, []).append((module, tuple(target), tuple(nxt) if nxt else None))


def chain(hook):
    """The hook's entries in call order."""
    return sorted(REG.get(hook, ()), key=lambda e: ORDER[e[0]])


def link(p, gsyms, add_ptr=None):
    """Wire every registered hook: one fixup per site. gsyms: gplay.LABELS (the hook dwords). Returns {hook: [module,
    ...]} in call order."""
    if add_ptr is None:
        import cobj
        add_ptr = cobj.add_ptr
    out = {}
    for hook in HOOKS:
        ents = chain(hook)
        if not ents:
            continue
        assert hook in gsyms, ('gphooks: gplay has no', hook)
        for i, (m, _, nxt) in enumerate(ents[:-1]):
            assert nxt, ('gphooks: a module without a next dword must end the chain', hook, m, [e[0] for e in ents])
        sites = [tuple(gsyms[hook])] + [e[2] for e in ents[:-1]]
        LINKED[hook] = []
        for site, (_, tgt, _) in zip(sites, ents):
            assert not any(p.get(site[0], site[1], 4)), ('gphooks: site already written', hook, site)
            add_ptr(p, site[1], tgt[0], tgt[1], site[0])
            LINKED[hook].append((site, tgt))
        out[hook] = [e[0] for e in ents]
    return out


def check(p):
    """patch.py, before save: every linked site still leads to its target."""
    for hook, pairs in LINKED.items():
        for site, tgt in pairs:
            assert tuple(p.target(*site)) == tgt, ('gphooks: site retargeted after link', hook, site, tgt)


def summary():
    return '; '.join(f'{h}: {" -> ".join(e[0] for e in chain(h))}' for h in HOOKS if REG.get(h))
