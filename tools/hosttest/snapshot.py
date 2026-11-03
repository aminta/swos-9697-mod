"""Fixtures for the host tests: full memory snapshots of a real game at a routine's entry.

    python3 tools/hosttest/snapshot.py BUILD_DIR MODULE.LABEL[,..] OUT_DIR [--car SAVE.CAR] [--team PATH] [--max N]
                                       [--scenario NAME] [--week-min W]

Runs a World 2026-27 career (world8485; --car: one season from that save) on BUILD_DIR (a build made with
HOSTTEST_SYMS=1: its ITALIAN.syms.json), a breakpoint at the label's entry (obj1); at each hit the whole linear memory
(MEMDUMP, 32 MB) -> OUT_DIR/<n>.bin and <n>.json (obj bases, the hit's EIP, the build, the label). Up to --max hits per label."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))


def syms_of(build):
    return json.load(open(os.path.join(build, 'ITALIAN.syms.json')))


def sym(syms, name):
    mod, lab = name.split('.', 1)
    return syms[mod][lab]


def make_hook(T, build, label, out, week_min=0, max_=12):
    """a world8485 W84_HOOK taking the snapshots (T: the swostest module running the career); -> (hook, state)"""
    sy = syms_of(build)
    labs = []
    for lab in label.split(','):
        obj, off = sym(sy, lab)
        assert obj in (0, 1), (lab, obj)                 # (a code label: obj1)
        labs.append((lab, off))
    cal, cur = sym(sy, 'uefaq.SYMS.CAL'), sym(sy, 'uefaq.SYMS.CAL_CUR')
    os.makedirs(out, exist_ok=True)
    st = {'n': 0, 'armed': False, 'per': {lab: 0 for lab, _ in labs}}   # (max_: per label)

    def hook(s, season, scr):
        if st['armed'] or scr is None:
            return
        st['armed'] = True
        base1 = s.result.base1

        def hit(r, lab):
            c = int.from_bytes(r.obj2(cur[1], 2), 'little')
            week = r.obj2(cal[1] + c + 1, 1)[0]
            if st['per'][lab] >= max_ or week < week_min:
                return
            mem = s.box.dump(0, T.MEMSIZE)
            k = st['n']
            if not k:                                    # (the exe as run - the harness's page: emu.overlay's base)
                import shutil
                shutil.copy(os.path.join(s.run, 'SWOS', 'ITALIAN.EXE'), os.path.join(out, 'run.EXE'))
            open(os.path.join(out, f'{k}.bin'), 'wb').write(mem)
            json.dump({'base1': r.base1, 'base2': r.base2, 'eip': r.eip, 'label': lab, 'build': build,
                       'season': season, 'week': week}, open(os.path.join(out, f'{k}.json'), 'w'))
            s.log.append(f'[snapshot] {lab} hit {k} week {week}')
            st['n'] += 1
            st['per'][lab] += 1
            if all(v >= max_ for v in st['per'].values()):                          # (done: no more breaks - the harness re-arms what bps holds)
                s.bps.clear()
                s.box.watch.clear()
                s.box.cmd('BPDEL *', 0.3)
                s.box.cmd('BPINT 3', 0.2)
        for lab, off in labs:
            s.bp(base1 + off, lambda r, lab=lab: hit(r, lab))
    hook.at_load = True
    hook.pre_load = any(lab.startswith('trailer.load') for lab, _ in labs)   # (armed before the load's key)
    return hook, st


def take(build, label, out, scenario='world_uru_nacional', team=None, car=None, week_min=0, max_=12):
    """the snapshots (see the module doc); -> (n, ok, msg) of the career run"""
    import swostest as T
    hook, st = make_hook(T, build, label, out, week_min, max_)
    keep = {k: os.environ.get(k) for k in ('URU_BUILD', 'URU_TEAM', 'URU_TMO', 'GPLAY_BUILD', 'W8485_FROM')}
    os.environ.update(URU_BUILD=build, URU_TMO='900', GPLAY_BUILD=build)
    if team:
        os.environ['URU_TEAM'] = team
    if car:
        os.environ['W8485_FROM'] = car
    T.W84_HOOK = hook
    try:
        ok, msg = getattr(T, scenario)()
    finally:
        T.W84_HOOK = None
        for k, v in keep.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    return st['n'], ok, msg


def main(argv):
    a = argparse.ArgumentParser()
    a.add_argument('build')
    a.add_argument('label')
    a.add_argument('out')
    a.add_argument('--car')
    a.add_argument('--team')
    a.add_argument('--max', type=int, default=12)
    a.add_argument('--scenario', default='world_uru_nacional')   # (any world8485 scenario: W84_HOOK; GPLAY_BUILD /
    a.add_argument('--week-min', type=int, default=0)            #  URU_BUILD point it at BUILD_DIR)
    o = a.parse_args(argv)
    sys.argv = ['x']
    n, ok, msg = take(o.build, o.label, o.out, o.scenario, o.team, o.car, o.week_min, o.max)
    print(f'{n} snapshots in {o.out}; run: {ok} {msg[:200]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
