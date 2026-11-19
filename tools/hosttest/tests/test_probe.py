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
        probe.TWINS['fake_sc']['expect'] = r'hook gone'                 # (a FAIL for another reason: twin-wrong)
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='FAIL', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'twin-wrong' or probe.verdict('PASS', 'm', st, det)[0] != 'PROBE-ERROR':
                errs.append(f'expect not matched: {st} {det}')
        probe.TWINS['fake_sc']['expect'] = r'twin=t1'
        with _env(FAKE_COUNT=count, FAKE_TWIN_DIR=d, FAKE_VERDICT='FAIL', SWOSTEST_TWIN='force'):
            st, det = probe.run_twin('fake_sc', fn, cmd, cache, runs)
            if st != 'proven':
                errs.append(f'expect matched: {st} {det}')
        probe.TWINS['fake_sc']['expect'] = ''
        # the key moves with the scenario source and with a prebuilt dir's identity
        t = probe.TWINS['fake_sc']
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
        probe.TWINS['probe_fake_ok'] = dict(env={}, prepare=None, why='w', id='t1')
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


def test_canary_twins():
    """Every canary scenario declares a red twin with an `expect` (the FAIL must name the defect); every build dir a
    twin names (env values that are paths) exists."""
    import swostest  # noqa: F401  (registers the twins)
    errs = []
    for c in probe.CANARIES:
        for s in c['scenarios']:
            t = probe.TWINS.get(s)
            if not t:
                errs.append(f'{c["id"]} {s}: no twin')
                continue
            if not t.get('expect'):
                errs.append(f'{s}: twin without expect')
            for k, v in t['env'].items():
                if isinstance(v, str) and v.startswith('/') and not os.path.isfile(os.path.join(v, 'ITALIAN.EXE')):
                    errs.append(f'{s}: {k}={v} has no ITALIAN.EXE')
    n = sum(len(c['scenarios']) for c in probe.CANARIES)
    return not errs, '; '.join(errs) or f'{n} canary scenarios, all with a twin + expect, twin dirs present'
