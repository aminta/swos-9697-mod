#!/usr/bin/env python3
"""PROBE (efficiency plan 5.1, rule R4; MC 19/11): the probe contract of the harness.

A check is proven before it judges. Each scenario may declare a RED TWIN: a variant (a mutant / switched build, a
fixture, an environment) on which the scenario MUST FAIL. The runner (tools/swostest.py main) runs the twin first, in
its own process, cached by build key, then the scenario. Verdicts, one per scenario line:

  PASS         the check ran, saw what it needs, and its twin (if any) FAILs as it must
  FAIL         the game is wrong: the check FAILed twice (the second time alone, in a fresh process) and is proven
  SETUP-ERROR  a precondition of the scenario, not the game (require(), a force that did not take, missing input dir;
               strict mode: a SKIP)
  PROBE-ERROR  the check cannot be trusted: its red twin PASSed (it cannot see the defect), the twin gave no verdict,
               it observed nothing (no ctdraw counters: the old INCONCLUSIVE), or (strict mode) it has no twin
  FLAKY        FAILed in the batch, PASSed alone: harness / host / order, never a product verdict (exit code 3)
  (SKIP and BUILT are not verdicts: the feature is not in the build / build-only run. A SKIP is never a PASS: a
   scenario returning (True, 'SKIP...') prints SKIP since 19/11.)

Declaring a twin, in tools/swostest.py:

    @scenario
    @probe.red_twin(env={'SWOSTEST_BUILD': '@TWIN_BUILD'}, why='release dir with the hook removed')
    def world_x(): ...

  env      variables set in the twin's process ('@NAME' = the value of $NAME in the runner, so the rc can pass the
           twin's dir: TWIN_BUILD=c/REL42x-twin);
  prepare  optional callable run IN the twin's process before the scenario; returns more env (it may build a mutant);
  why      one line: the defect the twin carries;
  expect   regex its FAIL line must match (the check saw THAT defect; a trap or a harness exception is 'twin-wrong').

Environment:
  SWOSTEST_PROBE=strict   no twin = PROBE-ERROR, SKIP = SETUP-ERROR (the canary run of an rc, from Fri 20/11 twins)
  SWOSTEST_TWIN=off       do not run twins (scenario development); =force: ignore the cache
  (internal) SWOSTEST_TWIN=<id> marks the twin's own process

CLI:
  python3 tools/probe.py canaries            the 12 canaries, their scenarios and twin state
  python3 tools/probe.py summary FILE...     a verdict file of at most 20 lines from suite output files
"""
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import time

VERDICTS = ('PASS', 'FAIL', 'SETUP-ERROR', 'PROBE-ERROR', 'FLAKY')
LINE = re.compile(r'^(PASS|FAIL|SETUP-ERROR|PROBE-ERROR|FLAKY|SKIP|BUILT|INCONCLUSIVE) (\S+)')
SKIP_MSG = re.compile(r'\s*SKIP(PED)?\b')
TWINS = {}

# The release's 12 canaries (plan 6.3). 'scenarios' = the harness scenarios that ARE the canary (run on the release
# recipe); 'run' = how a non-scenario canary is run; 'from' = the first release it applies to. A new scenario outside
# this list needs Davide's or the lead's yes and replaces one of the twelve.
CANARIES = [
    dict(id='C1', what='Boot and main menus, 4 languages', proves='the exe loads; object layout; texts',
         scenarios=['world_ns_contest'], env='once per language exe: SWOSTEST_UI=it|en|fr|de, SWOSTEST_BUILD=<rel copy>',
         gap='no object-layout assert (obj1 pages <= 237 is buildrel PAGES OK)'),
    dict(id='C2', what='New career in World 2026-27, first match, save, load', proves='hooks alive; save path; side file',
         scenarios=['world_foreign_buy', 'roundtrip'], env='FOREIGNBUY_BUILD=<rel>',
         gap='no W2627 first match + save + load in one scenario; side file not checked'),
    dict(id='C3', what='Season end + a second season (C20 on 2), release recipe', proves='the season-end chain with release data',
         scenarios=['career_20seasons'], env='C20_SEASONS=2 W8485_BUILD=<rel>'),
    dict(id='C4', what='The old-save trio', proves='migration of 4.0 / 4.1 / 4.2 saves',
         scenarios=['world_winners_oldsave', 'world_cuplist_mestre', 'world_s1conti_oldsave'],
         env='WINNERS_W27 / CUPLIST_REL = <rel>; the private saves (PHILA.CAR, MESTRE.CAR) present, else SKIP'),
    dict(id='C5', what='One port fixture played by the career club in slot 4', proves='the fixture-port adapter',
         scenarios=[], gap='no fport/fpad scenario on 42-int (Supercoppa C lane 2b brings one)'),
    dict(id='C6', what='A continental group draw and its page', proves='the draw in the exe; the VIEW port',
         scenarios=['world_cgame_view'], env='CV_BUILD=<rel>'),
    dict(id='C7', what='A full match with each GAMEPLAY preset', proves='gameplay hooks never hang; frame counter',
         scenarios=['gameplay_presets'], env='SWOSTEST_BUILD=<rel> (IT; 3 friendlies, ~160 s)'),
    dict(id='C8', what='SWOS++ smoke on the English exe', proves='the obj1 limit; timing',
         scenarios=['euro_swospp', 'swospp_bench'], env='SWOSTEST_UI=en, an English-UI copy of the release dir'),
    dict(id='C9', what='Patcher output byte-equal + the Node directory test (no DOSBox)', proves='what players install',
         scenarios=[], run='node internal/release-tools/patcher_node_test40.js R=c/<rel>/ <inputs as rc42.sh>',
         twin='the same with R = the previous release dir (c/REL412a/): output md5 FAIL lines, exit 1 (MC 19/11: the '
              "script is generic over the page's PATCHES, current for 4.2)"),
    dict(id='C10', what='MiSTer disk boot (Davide, by hand)', proves='real hardware', scenarios=[],
         run='by hand: IT + FR or DE exe'),
    dict(id='C11', what='NT match in a FIFA window with the dual job', proves='the squad swap and its state', scenarios=[],
         gap='5.0 item', **{'from': '5.0'}),
    dict(id='C12', what='Market window step with a CPU-CPU transfer on screen', proves='the market hooks', scenarios=[],
         gap='4.3 item', **{'from': '4.3'}),
]


def red_twin(env=None, prepare=None, why='', id='t1', expect=''):
    """Declare the scenario's red twin (see the module doc). Put it UNDER @scenario. expect = a regex the twin's FAIL
    message must match: a FAIL for another reason (a trap, a harness exception) proves nothing -> 'twin-wrong'."""
    def deco(fn):
        TWINS[fn.__name__] = dict(env=dict(env or {}), prepare=prepare, why=why, id=id, expect=expect)
        return fn
    return deco


MAIN = os.path.expanduser('~/swos-mod')


def rel(name, sub='SWOS'):
    """A frozen historical release dir under c/ (a red twin's build: the defect is known to be in it)."""
    return os.path.join(MAIN, 'c', name, sub)


def en_copy(src):
    """prepare() helper: an English-UI copy of release dir `src` (its ITALIAN.EXE = its ENGLISH.EXE, as SWOS++ wants),
    made once under internal/swostest/probe-twins/en/<release>; returns its path."""
    import shutil
    dst = os.path.join(MAIN, 'internal', 'swostest', 'probe-twins', 'en', os.path.basename(os.path.dirname(src.rstrip('/'))))
    ok = os.path.join(dst, '.ok')
    if not os.path.isfile(ok):
        tmp = f'{dst}.{os.getpid()}'
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(src, tmp, symlinks=False)
        shutil.copy(os.path.join(src, 'ENGLISH.EXE'), os.path.join(tmp, 'ITALIAN.EXE'))
        open(os.path.join(tmp, '.ok'), 'w').write(src)
        shutil.rmtree(dst, ignore_errors=True)
        os.replace(tmp, dst)
    return dst


def twin_on(var):
    """In a twin's own process, the twin's fixture switch `var` is set (fixture twins: the scenario breaks its own
    input, e.g. one save byte, to prove the check sees it). Never true in a normal run."""
    return in_twin() and os.environ.get(var, '') not in ('', '0')


def strict():
    return os.environ.get('SWOSTEST_PROBE', '').lower() == 'strict'


def in_twin():
    v = os.environ.get('SWOSTEST_TWIN', '')
    return v not in ('', 'off', 'force')


def _src(obj):
    try:
        return inspect.getsource(inspect.unwrap(obj))
    except (OSError, TypeError):
        return repr(obj)


def _dir_identity(d):
    """A prebuilt dir's identity: its SRC_STAMP.json (release dirs since 17/11), else ITALIAN.EXE's md5."""
    for p in (os.path.join(d, 'SRC_STAMP.json'), os.path.join(os.path.dirname(d.rstrip('/')), 'SRC_STAMP.json')):
        if os.path.isfile(p):
            return open(p, 'rb').read()
    exe = os.path.join(d, 'ITALIAN.EXE')
    if os.path.isfile(exe):
        return hashlib.md5(open(exe, 'rb').read()).hexdigest().encode()
    return b'-'


def twin_key(name, fn, twin, tree_key='', environ=None):
    """The twin's cache key: the scenario's and the twin's source, the twin spec, the harness tree's build key
    (swostest.build_key: sources + build env) and the identity of every prebuilt dir the runner points at."""
    env = os.environ if environ is None else environ
    h = hashlib.sha256()
    for part in (name, twin['id'], repr(sorted(twin['env'].items())), twin['why'], twin.get('expect', ''), _src(fn),
                 _src(twin['prepare']) if twin['prepare'] else '', tree_key):
        h.update(part.encode() + b'\0')
    for k in sorted(env):
        v = env[k]
        if (k.endswith('_BUILD') or k.endswith('_DATA')) and v and os.path.isdir(v):
            h.update(k.encode() + b'=' + _dir_identity(v) + b'\0')
    return h.hexdigest()[:12]


def _expand(env):
    """'@NAME' -> $NAME of the runner (missing: the twin cannot be set up -> PROBE-ERROR, said by name)."""
    out, missing = {}, []
    for k, v in env.items():
        if isinstance(v, str) and v.startswith('@'):
            if v[1:] not in os.environ:
                missing.append(v[1:])
                continue
            v = os.environ[v[1:]]
        out[k] = v
    return out, missing


def apply_twin_env(name):
    """In the twin's own process: set the twin's env (+ prepare()'s). Called by the runner before the scenario."""
    t = TWINS.get(name)
    if not t:
        return
    env, _ = _expand(t['env'])
    os.environ.update(env)
    if t['prepare']:
        os.environ.update({k: str(v) for k, v in (t['prepare']() or {}).items()})


def run_twin(name, fn, cmd, cache_dir, runs, tree_key=''):
    """Run (or read from the cache) the red twin of scenario `name`. cmd = argv running ONE scenario in a fresh
    process (swostest.py run NAME). Returns (state, detail): state 'proven' | 'twin-passed' | 'twin-wrong' (FAILed,
    not matching `expect`) | 'twin-not-run' | 'none' | 'off'."""
    t = TWINS.get(name)
    mode = os.environ.get('SWOSTEST_TWIN', '')
    if not t:
        return 'none', ''
    if mode == 'off':
        return 'off', 'twins off (SWOSTEST_TWIN=off)'
    env, missing = _expand(t['env'])
    if missing:
        return 'twin-not-run', f'twin {t["id"]}: runner env lacks {", ".join(missing)}'
    key = twin_key(name, fn, t, tree_key)
    cf = os.path.join(cache_dir, f'{name}-{t["id"]}-{key}.json')
    if mode != 'force' and os.path.isfile(cf):
        try:
            c = json.load(open(cf))
            return c['state'], f'{c["detail"]} (cached {key})'
        except (OSError, ValueError, KeyError):
            pass
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True,
                       env=dict(os.environ, **env, SWOSTEST_TWIN=t['id'], SWOSTEST_NO_RERUN='1',
                                SWOSTEST_RUNS=runs.rstrip('/') + '-twin'))
    last = [ln for ln in r.stdout.splitlines() if LINE.match(ln) and LINE.match(ln).group(2) == name]
    v = LINE.match(last[-1]).group(1) if last else None
    if v == 'FAIL' and t.get('expect') and not re.search(t['expect'], last[-1]):
        state, detail = 'twin-wrong', (f'red twin {t["id"]} FAILed for another reason (want /{t["expect"]}/): '
                                       f'{last[-1][:200]}')
    elif v == 'FAIL':
        state, detail = 'proven', f'red twin {t["id"]} FAILs as it must ({t["why"]}; {time.time() - t0:.0f} s)'
    elif v == 'PASS':
        state, detail = 'twin-passed', f'red twin {t["id"]} PASSed ({t["why"]}): the check cannot see that defect'
    else:
        tail = (last[-1] if last else (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or ['no output'])[-1])
        return 'twin-not-run', f'red twin {t["id"]} gave no FAIL/PASS: {tail[:160]}'
    try:                                    # (FAIL and PASS are a property of this build key: cached; anything else is not)
        os.makedirs(cache_dir, exist_ok=True)
        tmp = cf + f'.{os.getpid()}'
        json.dump({'state': state, 'detail': detail, 'line': last[-1][:400], 'time': time.strftime('%Y-%m-%d %H:%M')},
                  open(tmp, 'w'))
        os.replace(tmp, cf)
    except OSError:
        pass
    return state, detail


def verdict(res, msg, twin_state='none', twin_detail=''):
    """The final verdict from the scenario's own result and its twin's state (R4). In a twin's own process the
    scenario's result is the twin's outcome as it is (no strict mode, no tag): the parent judges it."""
    if in_twin():
        return res, msg + ' [twin]'
    if res in ('SKIP', 'BUILT'):
        if res == 'SKIP' and strict():
            return 'SETUP-ERROR', 'SKIP in strict mode (a canary never SKIPs): ' + msg
        return res, msg
    if res == 'INCONCLUSIVE':
        return 'PROBE-ERROR', 'observed nothing: ' + msg
    if res in ('SETUP-ERROR', 'FLAKY', 'PROBE-ERROR'):
        return res, msg + (f' [probe: {twin_detail}]' if twin_detail else '')
    if twin_state == 'proven':
        return res, msg + f' [probe: {twin_detail}]'
    if twin_state in ('twin-passed', 'twin-not-run', 'twin-wrong'):
        return 'PROBE-ERROR', f'{twin_detail}; was {res}: ' + msg
    if strict():
        return 'PROBE-ERROR', f'no red twin (R4, SWOSTEST_PROBE=strict); was {res}: ' + msg
    return res, msg + (' [probe: twins off]' if twin_state == 'off' else ' [probe: no red twin]')


def summary(paths, limit=20):
    """Counts per verdict + the non-PASS lines, at most `limit` lines in all (R6 verdict file)."""
    n, bad = {}, []
    for p in paths:
        for ln in open(p, errors='replace'):
            m = LINE.match(ln)
            if not m:
                continue
            v = 'PROBE-ERROR' if m.group(1) == 'INCONCLUSIVE' else m.group(1)
            n[v] = n.get(v, 0) + 1
            if v not in ('PASS', 'BUILT'):
                bad.append(f'{os.path.basename(p)}: {ln.strip()[:160]}')
    head = ' '.join(f'{k} {n.get(k, 0)}' for k in VERDICTS + ('SKIP',))
    out = [head] + bad[:limit - 2]
    if len(bad) > limit - 2:
        out.append(f'... {len(bad) - (limit - 2)} more non-PASS lines')
    return out


def main(argv):
    if argv[:1] == ['canaries']:
        import swostest_index                       # (twin state from the cached index)
        rows = {r['name']: r for r in swostest_index.index()}
        for c in CANARIES:
            sc = ', '.join(f"{s}:{rows[s]['line'] if s in rows else 'MISSING'}{' twin' if rows.get(s, {}).get('twin') else ' no-twin'}"
                           for s in c['scenarios']) or c.get('run') or 'NONE'
            print(f"{c['id']:4} {c['what']}{' [from ' + c['from'] + ']' if c.get('from') else ''}: {sc}")
            for k in ('env', 'twin', 'gap'):
                if c.get(k):
                    print(f"       {k}: {c[k]}")
        return 0
    if argv[:1] == ['summary'] and argv[1:]:
        print('\n'.join(summary(argv[1:])))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
