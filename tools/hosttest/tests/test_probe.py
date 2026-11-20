"""PROBE (plan 5.1, R4; MC 19/11): the verdict classes, the red-twin runner and its cache, the runner wiring in
swostest.main (SKIP is never a PASS, a twin that PASSes = PROBE-ERROR, strict mode) and the scenario index. No DOSBox:
the twin runner is driven with a tiny fake scenario script, the runner with in-process fake scenarios."""
import contextlib
import io
import os
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import probe  # noqa: E402


@contextlib.contextmanager
def _env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_probe_verdicts():
    errs = []
    with _env(SWOSTEST_PROBE=None):
        cases = [(('PASS', 'm', 'proven', 'tw'), 'PASS'), (('FAIL', 'm', 'proven', 'tw'), 'FAIL'),
                 (('PASS', 'm', 'twin-passed', 'tw'), 'PROBE-ERROR'), (('FAIL', 'm', 'twin-passed', 'tw'), 'PROBE-ERROR'),
                 (('PASS', 'm', 'twin-not-run', 'tw'), 'PROBE-ERROR'), (('PASS', 'm'), 'PASS'), (('FAIL', 'm'), 'FAIL'),
                 (('INCONCLUSIVE', 'm'), 'PROBE-ERROR'), (('SKIP', 'm'), 'SKIP'), (('SETUP-ERROR', 'm', 'twin-passed', 't'), 'SETUP-ERROR'),
                 (('FLAKY', 'm'), 'FLAKY'), (('PASS', 'm', 'off', ''), 'PASS')]
        for a, want in cases:
            got = probe.verdict(*a)[0]
            if got != want:
                errs.append(f'{a} -> {got}, want {want}')
        if 'no red twin' not in probe.verdict('PASS', 'm')[1]:
            errs.append('a PASS without a twin is not tagged')
    with _env(SWOSTEST_PROBE='strict'):
        for a, want in [(('PASS', 'm'), 'PROBE-ERROR'), (('FAIL', 'm'), 'PROBE-ERROR'), (('SKIP', 'm'), 'SETUP-ERROR'),
                        (('PASS', 'm', 'proven', 'tw'), 'PASS'), (('FAIL', 'm', 'proven', 'tw'), 'FAIL')]:
            got = probe.verdict(*a)[0]
            if got != want:
                errs.append(f'strict {a} -> {got}, want {want}')
    with _env(SWOSTEST_PROBE='strict', SWOSTEST_TWIN='t1'):
        if probe.verdict('FAIL', 'm')[0] != 'FAIL' or probe.verdict('PASS', 'm')[0] != 'PASS':
            errs.append('in a twin process strict mode changed the twin outcome')
    return not errs, '; '.join(errs) or f'{len(cases) + 7} verdict cases'


FAKE = r'''import os, sys
open(os.environ['FAKE_COUNT'], 'a').write('x')
v = os.environ.get('FAKE_VERDICT', 'FAIL')
print('some log line')
print(f"{v} {sys.argv[-1]} (0 s) twin={os.environ.get('SWOSTEST_TWIN')} norerun={os.environ.get('SWOSTEST_NO_RERUN')} b={os.environ.get('FAKE_B')}")
'''


def test_probe_twin_runner():
    errs = []
    with tempfile.TemporaryDirectory() as d:
        script, count = os.path.join(d, 'fake.py'), os.path.join(d, 'count')
        open(script, 'w').write(FAKE)
        cmd = [sys.executable, script, 'run', 'fake_sc']
        cache, runs = os.path.join(d, 'cache'), os.path.join(d, 'runs')

        def fn():
            return True, 'ok'
        probe.TWINS.pop('fake_sc', None)
        st, _ = probe.run_twin('fake_sc', fn, cmd, cache, runs)
        if st != 'none':
            errs.append(f'no twin declared -> {st}')
        probe.red_twin(env={'FAKE_B': '@FAKE_TWIN_DIR'}, why='hook removed')(fn)
        probe.TWINS['fake_sc'] = probe.TWINS.pop('fn')
        n = lambda: len(open(count).read()) if os.path.exists(count) else 0   # noqa: E731
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=None, SWOSTEST_TWIN=None):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'twin-not-run' or 'FAKE_TWIN_DIR' not in det or n():
                errs.append(f'@VAR missing: {st} {det} runs={n()}')
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='FAIL', SWOSTEST_TWIN=None):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'proven' or n() != 1:
                errs.append(f'FAILing twin: {st} {det} runs={n()}')
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'proven' or 'cached' not in det or n() != 1:
                errs.append(f'cache: {st} {det} runs={n()}')
            with _env(SWOSTEST_TWIN='force'):
                probe.run_twin('fake_sc', fn, cmd, cache, runs)
                if n() != 2:
                    errs.append(f'force: runs={n()}')
            with _env(SWOSTEST_TWIN='off'):
                st, _ = probe.run_twin('fake_sc', fn, cmd, cache, runs)
                if st != 'off' or n() != 2:
                    errs.append(f'off: {st} runs={n()}')
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='PASS', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'twin-passed':
                errs.append(f'PASSing twin: {st} {det}')
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='SKIP', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'twin-not-run':
                errs.append(f'SKIPping twin: {st} {det}')
        probe.TWINS['fake_sc'][0]['expect'] = r'hook gone'                 # (a FAIL for another reason: twin-wrong)
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='FAIL', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'twin-wrong' or probe.verdict('PASS', 'm', st, det)[0] != 'PROBE-ERROR':
                errs.append(f'expect not matched: {st} {det}')
        probe.TWINS['fake_sc'][0]['expect'] = r'twin=t1'
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='FAIL', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'proven':
                errs.append(f'expect matched: {st} {det}')
        probe.TWINS['fake_sc'][0]['expect'] = ''
        # the key moves with the scenario source and with a prebuilt dir's identity
        t = probe.TWINS['fake_sc'][0]
        k1 = probe.twin_key('fake_sc', fn, t, 'tree', {})
        os.makedirs(os.path.join(d, 'rel'))
        open(os.path.join(d, 'rel', 'ITALIAN.EXE'), 'wb').write(b'a')
        k2 = probe.twin_key('fake_sc', fn, t, 'tree', {'SWOSTEST_BUILD': os.path.join(d, 'rel')})
        open(os.path.join(d, 'rel', 'ITALIAN.EXE'), 'wb').write(b'b')
        k3 = probe.twin_key('fake_sc', fn, t, 'tree', {'SWOSTEST_BUILD': os.path.join(d, 'rel')})
        k4 = probe.twin_key('fake_sc', fn, t, 'tree2', {})
        if len({k1, k2, k3, k4}) != 4:
            errs.append(f'keys {k1} {k2} {k3} {k4}')
        line = open(os.path.join(cache, os.listdir(cache)[0])).read() if os.path.isdir(cache) else ''
        if 'twin=t1' not in line or 'norerun=1' not in line or f'b={d}' not in line:
            errs.append(f'twin env not passed: {line[:200]}')
        probe.TWINS.pop('fake_sc', None)
    return not errs, '; '.join(errs) or 'none / @VAR missing / proven / cached / force / off / passed / not-run / wrong / expect / keys'


FAKE2 = r'''import os, sys
tid = os.environ.get('SWOSTEST_TWIN')
open(os.environ['FAKE_COUNT'], 'a').write(tid + ' ')
v = os.environ.get('FAKE_VERDICT_' + tid, 'FAIL')
print(f"{v} {sys.argv[-1]} (0 s) twin={tid} fix={os.environ.get('FAKE_FIX')} b={os.environ.get('FAKE_B')} "
      f"runs={os.environ.get('SWOSTEST_RUNS')} of={os.environ.get('SWOSTEST_TWIN_OF')}")
'''


def test_probe_two_twins():
    """Two twins per scenario (t1 a fixture on the current build, t2 a historical build): TWINS[name] is the list in
    source order, each runs in its own process with its own env only, its own run dir and cache entry; ALL must FAIL
    with their own expect - one that PASSes / FAILs otherwise / gives no verdict decides the state, the proven one
    stays cached; a second twin with the same id is refused; apply_twin_env picks the process's id."""
    errs = []
    with tempfile.TemporaryDirectory() as d:
        script, count = os.path.join(d, 'fake.py'), os.path.join(d, 'count')
        open(script, 'w').write(FAKE2)
        cmd = [sys.executable, script, 'run', 'fake2']
        cache, runs = os.path.join(d, 'cache'), os.path.join(d, 'runs')

        def fake2():
            return True, 'ok'
        probe.TWINS.pop('fake2', None)
        deco1 = probe.red_twin(env={'FAKE_FIX': '1'}, why='fixture', expect=r'twin=t1 fix=1 b=None ')
        deco2 = probe.red_twin(env={'FAKE_B': 'old'}, why='old build', id='t2', expect=r'twin=t2 fix=None b=old ')
        deco1(deco2(fake2))                               # (as stacked decorators: the lower one first)
        ids = [t['id'] for t in probe.twins('fake2')]
        if ids != ['t1', 't2']:
            errs.append(f'source order: {ids}')
        try:
            probe.red_twin(env={}, why='again')(fake2)
            errs.append('a second t1 accepted')
        except ValueError:
            pass
        seen = lambda: open(count).read().split() if os.path.exists(count) else []   # noqa: E731
        base = dict(FAKE_COUNT=count, SWOSTEST_TWIN=None, FAKE_FIX=None, FAKE_B=None, FAKE_VERDICT_t1=None,
                    FAKE_VERDICT_t2=None)
        with _env(**base):
            st, det = probe.run_twin('fake2', fake2, cmd, cache, runs)
            if st != 'proven' or seen() != ['t1', 't2'] or 'red twin t1 FAILs' not in det or 'red twin t2 FAILs' not in det:
                errs.append(f'both FAIL: {st} {det} runs={seen()}')
            files = sorted(os.listdir(cache)) if os.path.isdir(cache) else []
            if [f.split('-')[1] for f in files] != ['t1', 't2']:
                errs.append(f'cache per id: {files}')
            lines = [open(os.path.join(cache, f)).read() for f in files]
            if len(lines) == 2 and (f'runs={runs}-twin of={runs}' not in lines[0] or f'runs={runs}-twin-t2 of={runs}' not in lines[1]):
                errs.append(f'run dirs / SWOSTEST_TWIN_OF: {[x[-160:] for x in lines]}')
            st, det = probe.run_twin('fake2', fake2, cmd, cache, runs)
            if st != 'proven' or det.count('cached') != 2 or len(seen()) != 2:
                errs.append(f'both cached: {st} {det} runs={seen()}')
        for var, verdict, want in (('FAKE_VERDICT_t2', 'PASS', 'twin-passed'), ('FAKE_VERDICT_t1', 'PASS', 'twin-passed'),
                                   ('FAKE_VERDICT_t2', 'SKIP', 'twin-not-run')):
            n0 = len(seen())
            with _env(**dict(base, SWOSTEST_TWIN='force', **{var: verdict})):
                st, det = probe.run_twin('fake2', fake2, cmd, cache, runs)
            tid = var[-2:]
            if st != want or len(seen()) != n0 + 2 or f'red twin {tid}' not in det or '1 of 2 twins proven' not in det \
                    or probe.verdict('PASS', 'm', st, det)[0] != 'PROBE-ERROR':
                errs.append(f'{tid} {verdict}: {st} {det} runs={seen()[n0:]}')
        probe.TWINS['fake2'][1]['expect'] = r'twin=t1 '   # (t2 FAILs, but not with ITS expect: wrong; t1 from the cache)
        n0 = len(seen())
        with _env(**base):
            st, det = probe.run_twin('fake2', fake2, cmd, cache, runs)
        if st != 'twin-wrong' or seen()[n0:] != ['t2'] or 'red twin t2 FAILed for another reason' not in det:
            errs.append(f't2 wrong expect: {st} {det} runs={seen()[n0:]}')
        with _env(**dict(base, FAKE_VERDICT_t1='PASS', FAKE_VERDICT_t2='SKIP', SWOSTEST_TWIN='force')):
            st, det = probe.run_twin('fake2', fake2, cmd, cache, runs)   # (the worst state wins: passed > not-run)
        if st != 'twin-passed' or 'red twin t1 PASSed' not in det or 'red twin t2 gave no' not in det:
            errs.append(f'passed + not-run: {st} {det}')
        # the twin's own process: its id's env only; an id the scenario lacks is refused
        with _env(SWOSTEST_TWIN='t2', FAKE_FIX=None, FAKE_B=None):
            probe.apply_twin_env('fake2')
            if os.environ.get('FAKE_B') != 'old' or os.environ.get('FAKE_FIX') or probe.twin_on('FAKE_FIX'):
                errs.append('apply_twin_env t2 set the wrong env')
            if probe.parent_runs() is not None:
                errs.append('parent_runs without SWOSTEST_TWIN_OF')
        with _env(SWOSTEST_TWIN='t1', FAKE_FIX=None, FAKE_B=None, SWOSTEST_TWIN_OF=runs):
            probe.apply_twin_env('fake2')
            if not probe.twin_on('FAKE_FIX') or os.environ.get('FAKE_B') or probe.parent_runs() != runs:
                errs.append('apply_twin_env t1 / parent_runs')
        with _env(SWOSTEST_TWIN='t9'):
            try:
                probe.apply_twin_env('fake2')
                errs.append('unknown twin id accepted')
            except SystemExit as e:
                if 't9' not in str(e) or 't1, t2' not in str(e):
                    errs.append(f'unknown id message: {e}')
        with _env(SWOSTEST_TWIN=None, SWOSTEST_TWIN_OF=runs):
            if probe.parent_runs() is not None:
                errs.append('parent_runs outside a twin')
        probe.TWINS.pop('fake2', None)
    return not errs, '; '.join(errs) or ('source order / one twin per id / both proven / cache + run dir per id / t2 passed / '
                                         't1 passed / not-run / wrong expect / worst state / env per id / unknown id refused')


def test_probe_runner_wiring():
    """swostest.main run NAME in process: (True, 'SKIP...') prints SKIP (exit 0, never PASS); a twin that PASSes
    -> PROBE-ERROR (exit 1); a proven twin keeps the scenario's verdict; strict mode without a twin -> PROBE-ERROR."""
    import swostest
    errs = []

    def sk():
        return True, 'SKIP: no release dir'

    def ok():
        return True, 'fine'
    swostest.SCENARIOS.update(probe_fake_skip=sk, probe_fake_ok=ok)
    real = probe.run_twin
    try:
        def go(name, **kv):
            out = io.StringIO()
            kv.setdefault('SWOSTEST_RERUN', '1')          # (no FAIL re-run, no twin, unless a case clears it)
            with _env(SWOSTEST_BUILD=None, W8485_BUILD=None, **kv), contextlib.redirect_stdout(out):
                rc = swostest.main(['run', name])
            return rc, [ln for ln in out.getvalue().splitlines() if probe.LINE.match(ln)]
        rc, ln = go('probe_fake_skip', SWOSTEST_PROBE=None)
        if rc != 0 or not ln or not ln[-1].startswith('SKIP probe_fake_skip'):
            errs.append(f'SKIP-as-PASS: rc {rc} {ln}')
        rc, ln = go('probe_fake_skip', SWOSTEST_PROBE='strict')
        if rc != 1 or not ln or not ln[-1].startswith('SETUP-ERROR'):
            errs.append(f'strict SKIP: rc {rc} {ln}')
        rc, ln = go('probe_fake_ok', SWOSTEST_PROBE=None)
        if rc != 0 or not ln or not ln[-1].startswith('PASS') or 'no red twin' not in ln[-1]:
            errs.append(f'no twin: rc {rc} {ln}')
        rc, ln = go('probe_fake_ok', SWOSTEST_PROBE='strict')
        if rc != 1 or not ln or not ln[-1].startswith('PROBE-ERROR'):
            errs.append(f'strict no twin: rc {rc} {ln}')
        probe.TWINS['probe_fake_ok'] = [dict(env={}, prepare=None, why='w', id='t1')]
        swostest.build_key = (lambda f: lambda *a, **k: 'k')(swostest.build_key)   # (no tree hash in the test)
        for st, want, wrc in (('twin-passed', 'PROBE-ERROR', 1), ('proven', 'PASS', 0), ('twin-not-run', 'PROBE-ERROR', 1)):
            probe.run_twin = lambda *a, _s=st, **k: (_s, f'detail {_s}')
            rc, ln = go('probe_fake_ok', SWOSTEST_PROBE='strict', SWOSTEST_RERUN=None, SWOSTEST_TWIN=None)
            if rc != wrc or not ln or not ln[-1].startswith(want):
                errs.append(f'twin {st}: rc {rc} {ln}')
    finally:
        probe.run_twin = real
        probe.TWINS.pop('probe_fake_ok', None)
        for k in ('probe_fake_skip', 'probe_fake_ok'):
            swostest.SCENARIOS.pop(k, None)
    return not errs, '; '.join(errs) or 'skip-as-SKIP / strict SKIP / no twin / strict no twin / twin passed / proven / not run'


def test_swostest_index():
    """The generated index: one row per scenario the runner knows (swostest.SCENARIOS, registered modules and
    generated ones included), each row's line = a `def` in its file, every canary scenario exists."""
    import swostest
    import swostest_index
    rows = swostest_index.build_index()
    root = os.path.dirname(TOOLS)
    src = {}
    bad = []
    for r in rows:
        ls = src.setdefault(r['file'], open(os.path.join(root, r['file']), encoding='utf-8', errors='replace').read().splitlines())
        if not ls[r['line'] - 1].lstrip().startswith('def '):
            bad.append(r['name'])
    names = {r['name'] for r in rows}
    miss = [s for c in probe.CANARIES for s in c['scenarios'] if s not in names]
    lost = sorted(set(swostest.SCENARIOS) - names)
    files = sorted({r['file'] for r in rows})
    ok = not bad and not miss and not lost and len(rows) == len(swostest.SCENARIOS)
    return ok, f'{len(rows)} scenarios in {files}, bad lines {bad[:3]}, missing canaries {miss}, not indexed {lost[:5]}'


FIXTURE_TWINS = ('world_cgame_view', 'world_s1conti_oldsave', 'world_winners_oldsave')


def test_canary_twins():
    """Every canary scenario declares a red twin with an `expect` (the FAIL must name the defect); every build dir a
    twin names (env values that are paths) exists."""
    import swostest  # noqa: F401  (registers the twins)
    errs = []
    for c in probe.CANARIES:
        for s in c['scenarios']:
            ts = probe.twins(s)
            if not ts:
                errs.append(f'{c["id"]} {s}: no twin')
                continue
            if len({t['id'] for t in ts}) != len(ts):
                errs.append(f'{s}: twin ids not unique {[t["id"] for t in ts]}')
            for t in ts:
                if not t.get('expect'):
                    errs.append(f'{s}: twin {t["id"]} without expect')
                for k, v in t['env'].items():
                    if isinstance(v, str) and v.startswith('/') and not os.path.isfile(os.path.join(v, 'ITALIAN.EXE')):
                        errs.append(f'{s}: {k}={v} has no ITALIAN.EXE')
            fixture = [t for t in ts if not any(isinstance(v, str) and v.startswith(('/', '@')) for v in t['env'].values())]
            if s in FIXTURE_TWINS:                        # (C4 / C6: the FAIL must come from the check itself, on the
                t1 = probe.twin(s, 't1')                  #  current build - not from a precondition of an old one)
                if t1 not in fixture or not t1['expect'].startswith(r'\(\d+ s\) '):
                    errs.append(f'{s}: t1 is not a fixture twin with an anchored expect')
                if not probe.twin(s, 't2'):
                    errs.append(f'{s}: the historical-build twin t2 is gone')
    n = sum(len(c['scenarios']) for c in probe.CANARIES)
    m = sum(len(probe.twins(s)) for c in probe.CANARIES for s in c['scenarios'])
    return not errs, '; '.join(errs) or f'{n} canary scenarios, {m} twins, all with an expect, twin dirs present'
