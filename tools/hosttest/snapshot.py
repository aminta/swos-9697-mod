"""Fixtures for the host tests: full memory snapshots of a real game at a routine's entry.

    python3 tools/hosttest/snapshot.py BUILD_DIR MODULE.LABEL[,..] OUT_DIR [--car SAVE.CAR] [--team PATH] [--max N]
                                       [--scenario NAME] [--week-min W] [--every N]

Runs a World 2026-27 career (world8485; --car: one season from that save) on BUILD_DIR (a build made with
HOSTTEST_SYMS=1: its ITALIAN.syms.json), a breakpoint at the label's entry (in the label's own object: obj1, obj3 or obj4, from the symbols); at each hit the whole linear memory
(MEMDUMP, 32 MB) -> OUT_DIR/<n>.bin and <n>.json (obj bases, the hit's EIP, the build, the label). Up to --max hits per label.

Every snapshot set stores its RECIPE beside it (MC 17/11: a fixture that cannot be regenerated goes stale with the next
layout change): OUT_DIR/RECIPE.json = the build (dir, its source stamp from the syms file, its build log's last lines, and
the exact build command when the caller gives it in HT_SNAP_BUILD_CMD), the tree the harness ran from (stamp), the labels /
week-min / max / every, the environment that shapes the run (recipe_env) and the exact command line (`command`: cd, env,
python, argv) - run it again to regenerate the set. Each <n>.json names it ('recipe') and carries the build's stamp.
tools/hosttest/fixindex.py lists every fixture with its state (CURRENT / STALE) and whether it has a recipe."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))


def syms_of(build):
    return json.load(open(os.path.join(build, 'ITALIAN.syms.json')))


def sym(syms, name):
    if name.startswith('obj1+'):                         # (4.2 opsign: a raw obj1 offset - the original game's code)
        return [0, int(name[5:], 16)]
    mod, lab = name.split('.', 1)
    return syms[mod][lab]


ENV_PREFIX = ('W8485_', 'HT_', 'SWOSTEST_', 'W2627', 'GPLAY_', 'C20_', 'URU_', 'WSK_', 'WSM_', 'CONTI_', 'CD_', 'S7_', 'S3_',
              'SEASON_PACKS', 'COBJ_', 'REMOTE_SRC_TEST')


def recipe_env():
    """the environment that shapes a snapshot run: the harness's and the scenarios' variables (ENV_PREFIX), every build
    switch (modver.BUILD_SWITCHES) and any *_FORCE* / *_BUILD / *_DATA / *_TEAM / *_TEST one. Nothing else (no secrets)."""
    try:
        sys.path.insert(0, os.path.join(HERE, '..'))
        import modver
        sw = set(getattr(modver, 'BUILD_SWITCHES', ()))
    except Exception:
        sw = set()
    keep = lambda k: k.startswith(ENV_PREFIX) or k in sw or '_FORCE' in k or k.endswith(('_BUILD', '_DATA', '_TEAM', '_TEST'))
    return {k: v for k, v in sorted(os.environ.items()) if keep(k)}


def recipe(build, label, week_min, max_, every, argv=None, cwd=None):
    """what regenerates a snapshot set (see the module doc); written once per set as OUT_DIR/RECIPE.json"""
    import datetime
    import shlex
    sy = syms_of(build)
    try:
        sys.path.insert(0, os.path.join(HERE, '..'))
        import srcstamp
        tree = srcstamp.stamp()
    except Exception:
        tree = None
    log = next((p for p in (os.path.join(build, '..', n) for n in ('build-it.log', 'build.log')) if os.path.isfile(p)), None)
    env, cwd = recipe_env(), cwd or os.getcwd()
    argv = list(argv or (os.environ['HT_SNAP_ARGV'].split(' ') if os.environ.get('HT_SNAP_ARGV') else sys.argv))
    env.pop('HT_SNAP_ARGV', None)
    return {'format': 1, 'date': datetime.datetime.now().isoformat(timespec='seconds'),
            'build': os.path.abspath(build), 'build_src': {k: v[1] for k, v in (sy.get('_src') or {}).items()},
            'build_command': os.environ.get('HT_SNAP_BUILD_CMD'),
            'build_log_tail': open(log, errors='replace').read().split('\n')[-6:] if log else None,
            'tree': tree, 'labels': label, 'week_min': week_min, 'max': max_, 'every': every,
            'env': env, 'cwd': cwd, 'python': sys.executable, 'argv': argv,
            'command': 'cd ' + shlex.quote(cwd) + ' && env ' + ' '.join(f'{k}={shlex.quote(v)}' for k, v in env.items())
                       + ' ' + ' '.join(shlex.quote(x) for x in [sys.executable] + argv)}


def make_hook(T, build, label, out, week_min=0, max_=12, every=1):
    """a world8485 W84_HOOK taking the snapshots (T: the swostest module running the career); -> (hook, state)"""
    sy = syms_of(build)
    labs = []
    for lab in label.split(','):
        obj, off = sym(sy, lab)
        assert obj in (0, 1, 3, 4), (lab, obj)           # (a code label's object comes from the build's symbols - its link
        labs.append((lab, off, obj or 1))                #  map - never assumed: obj1 (a bare asm label: 0), obj3 (benchx,
                                                         #  gplay.c since 4.2 x3all: gplay.csyms.<function>), obj4 (the
                                                         #  engine and its bands); obj2 is data: no breakpoint there)
    cal, cur = sym(sy, 'uefaq.SYMS.CAL'), sym(sy, 'uefaq.SYMS.CAL_CUR')
    os.makedirs(out, exist_ok=True)
    st = {'n': 0, 'armed': False, 'per': {lab: 0 for lab, *_ in labs}, 'hits': {lab: 0 for lab, *_ in labs}}   # (max_: per label)
    rec = recipe(build, label, week_min, max_, every)   # (now: the caller's argv and environment, before the run changes them)

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
            st['hits'][lab] += 1                         # (every: one hit in that many - a season's spread)
            if (st['hits'][lab] - 1) % every:
                return
            mem = s.box.dump(0, T.MEMSIZE)
            k = st['n']
            if not k:                                    # (the exe as run - the harness's page: emu.overlay's base)
                import shutil
                shutil.copy(os.path.join(s.run, 'SWOS', 'ITALIAN.EXE'), os.path.join(out, 'run.EXE'))
                json.dump(rec, open(os.path.join(out, 'RECIPE.json'), 'w'), indent=1, sort_keys=True)   # (the set's recipe)
            open(os.path.join(out, f'{k}.bin'), 'wb').write(mem)
            json.dump({'base1': r.base1, 'base2': r.base2, 'eip': r.eip, 'label': lab, 'build': build,
                       'season': season, 'week': week, 'recipe': 'RECIPE.json', 'build_src': rec['build_src']},
                      open(os.path.join(out, f'{k}.json'), 'w'))
            s.log.append(f'[snapshot] {lab} hit {k} week {week}')
            st['n'] += 1
            st['per'][lab] += 1
            if all(v >= max_ for v in st['per'].values()):                          # (done: no more breaks - the harness re-arms what bps holds)
                s.bps.clear()
                s.box.watch.clear()
                s.box.cmd('BPDEL *', 0.3)
                s.box.cmd('BPINT 3', 0.2)
        for lab, off, obj in labs:
            s.bp(s.result.lin((obj, off)), lambda r, lab=lab: hit(r, lab))   # (Result.lin: each object's own base)
    hook.at_load = True
    hook.pre_load = any(lab.startswith('trailer.load') for lab, *_ in labs)   # (armed before the load's key)
    return hook, st


def take(build, label, out, scenario='world_uru_nacional', team=None, car=None, week_min=0, max_=12, every=1):
    """the snapshots (see the module doc); -> (n, ok, msg) of the career run"""
    import swostest as T
    hook, st = make_hook(T, build, label, out, week_min, max_, every)
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
    a.add_argument('--every', type=int, default=1)
    o = a.parse_args(argv)
    os.environ.setdefault('HT_SNAP_ARGV', ' '.join(sys.argv))   # (the recipe's command line: sys.argv is replaced below)
    sys.argv = ['x']
    n, ok, msg = take(o.build, o.label, o.out, o.scenario, o.team, o.car, o.week_min, o.max, o.every)
    print(f'{n} snapshots in {o.out}; run: {ok} {msg[:200]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
