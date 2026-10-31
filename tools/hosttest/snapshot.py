"""Fixtures for the host tests: full memory snapshots of a real game at a routine's entry.

    python3 tools/hosttest/snapshot.py BUILD_DIR MODULE.LABEL[,..] OUT_DIR [--car SAVE.CAR] [--team PATH] [--max N]
                                       [--scenario NAME] [--week-min W]

Runs a World 2026-27 career (world8485; --car: one season from that save) on BUILD_DIR (a build made with
HOSTTEST_SYMS=1: its ITALIAN.syms.json), a breakpoint at the label's entry (obj1); at each hit the whole linear memory
(MEMDUMP, 32 MB) -> OUT_DIR/<n>.bin and <n>.json (obj bases, the hit's EIP, the build, the label). Up to --max hits."""
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


def main(argv):
    a = argparse.ArgumentParser()
    a.add_argument('build')
    a.add_argument('label')
    a.add_argument('out')
    a.add_argument('--car')
    a.add_argument('--team', default='SUDAMERICA,URUGUAY,CAMPEONATO URUGUAYO,NACIONAL')
    a.add_argument('--max', type=int, default=12)
    a.add_argument('--scenario', default='world_uru_nacional')   # (any world8485 scenario: W84_HOOK; GPLAY_BUILD /
    a.add_argument('--week-min', type=int, default=0)            #  URU_BUILD point it at BUILD_DIR)
    o = a.parse_args(argv)
    sys.argv = ['x']
    import swostest as T
    sy = syms_of(o.build)
    labs = []
    for lab in o.label.split(','):
        obj, off = sym(sy, lab)
        assert obj in (0, 1), (lab, obj)                 # (a code label: obj1)
        labs.append((lab, off))
    cal, cur = sym(sy, 'uefaq.SYMS.CAL'), sym(sy, 'uefaq.SYMS.CAL_CUR')
    os.makedirs(o.out, exist_ok=True)
    st = {'n': 0, 'armed': False}

    def hook(s, season, scr):
        if st['armed'] or scr is None:
            return
        st['armed'] = True
        base1 = s.result.base1

        def hit(r, lab):
            c = int.from_bytes(r.obj2(cur[1], 2), 'little')
            week = r.obj2(cal[1] + c + 1, 1)[0]
            if st['n'] >= o.max or week < o.week_min:
                return
            mem = s.box.dump(0, T.MEMSIZE)
            k = st['n']
            open(os.path.join(o.out, f'{k}.bin'), 'wb').write(mem)
            json.dump({'base1': r.base1, 'base2': r.base2, 'eip': r.eip, 'label': lab, 'build': o.build,
                       'season': season, 'week': week}, open(os.path.join(o.out, f'{k}.json'), 'w'))
            s.log.append(f'[snapshot] {lab} hit {k} week {week}')
            st['n'] += 1
        for lab, off in labs:
            s.bp(base1 + off, lambda r, lab=lab: hit(r, lab))
    hook.at_load = True
    T.W84_HOOK = hook
    os.environ.update(URU_BUILD=o.build, URU_TEAM=o.team, URU_TMO='900', GPLAY_BUILD=o.build)
    if o.car:
        os.environ['W8485_FROM'] = o.car
    ok, msg = getattr(T, o.scenario)()
    print(f'{st["n"]} snapshots in {o.out}; run: {ok} {msg[:200]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
