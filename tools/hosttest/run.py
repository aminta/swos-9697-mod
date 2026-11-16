"""Host tests runner: python3 tools/hosttest/run.py [-k substring]  (re-runs itself in internal/hosttest/.venv, which
has Unicorn). Every tools/hosttest/tests/test_*.py function test_*() -> (ok, message); exit 1 on any FAIL. A test that
returns (True, 'SKIP: ...') prints SKIP and is not counted as a PASS (a SKIP never counts as a PASS, MC 15/11)."""
import glob
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', '.venv', 'bin', 'python')

if __name__ == '__main__':
    if sys.executable != VENV and os.path.exists(VENV) and not os.environ.get('HOSTTEST_NOVENV'):
        os.execv(VENV, [VENV] + sys.argv)
    sys.path.insert(0, HERE)
    sel = sys.argv[sys.argv.index('-k') + 1] if '-k' in sys.argv else ''
    bad, n = 0, {'PASS': 0, 'SKIP': 0, 'FAIL': 0}
    for f in sorted(glob.glob(os.path.join(HERE, 'tests', 'test_*.py'))):
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:      # (42-fixroot: a stale / edited fixture (manifest mismatch) fails its module, not the run)
            if sel and sel not in os.path.basename(f):
                continue
            bad += 1
            n['FAIL'] += 1
            print(f"FAIL {os.path.basename(f)[:-3]} (0.00 s) {type(e).__name__}: {e}")
            continue
        for name in sorted(n for n in dir(mod) if n.startswith('test_') and sel in n):
            t = time.time()
            try:
                r = getattr(mod, name)()
                ok, msg = (True, '(asserts)') if r is None else r      # (pytest-style: no exception = PASS; MC 12/11)
            except Exception as e:
                ok, msg = False, f'{type(e).__name__}: {e}'
            bad += not ok
            st = 'FAIL' if not ok else 'SKIP' if str(msg).startswith('SKIP') else 'PASS'
            n[st] += 1
            print(f'{st} {name} ({time.time() - t:.2f} s) {msg}')
    print(f"hosttest: {n['PASS']} PASS, {n['SKIP']} SKIP, {n['FAIL']} FAIL")
    sys.exit(1 if bad else 0)
