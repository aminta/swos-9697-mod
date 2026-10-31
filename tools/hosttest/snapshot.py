"""Fixtures for the host tests: full memory snapshots of a real game at a routine's entry.

    python3 tools/hosttest/snapshot.py BUILD_DIR MODULE.LABEL OUT_DIR [--car SAVE.CAR] [--team PATH] [--max N]

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
    o = a.parse_args(argv)
    sys.argv = ['x']
    import swostest as T
    obj, off = sym(syms_of(o.build), o.label)
    assert obj in (0, 1), (o.label, obj)                 # (a code label: obj1)
    os.makedirs(o.out, exist_ok=True)
    st = {'n': 0, 'armed': False}

    def hook(s, season, scr):
        if st['armed'] or scr is None:
            return
        st['armed'] = True
        base1 = s.result.base1

        def hit(r):
            if st['n'] >= o.max:
                return
            mem = s.box.dump(0, T.MEMSIZE)
            k = st['n']
            open(os.path.join(o.out, f'{k}.bin'), 'wb').write(mem)
            json.dump({'base1': r.base1, 'base2': r.base2, 'eip': r.eip, 'label': o.label, 'build': o.build,
                       'season': season}, open(os.path.join(o.out, f'{k}.json'), 'w'))
            s.log.append(f'[snapshot] {o.label} hit {k}')
            st['n'] += 1
        s.bp(base1 + off, hit)
    hook.at_load = True
    T.W84_HOOK = hook
    os.environ.update(URU_BUILD=o.build, URU_TEAM=o.team, URU_TMO='900')
    if o.car:
        os.environ['W8485_FROM'] = o.car
    ok, msg = T.world_uru_nacional()
    print(f'{st["n"]} snapshots in {o.out}; run: {ok} {msg[:200]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
