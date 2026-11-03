"""Host tests runner: python3 tools/hosttest/run.py [-k substring]  (re-runs itself in internal/hosttest/.venv, which
has Unicorn). Every tools/hosttest/tests/test_*.py function test_*() -> (ok, message); exit 1 on any FAIL."""
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
    bad = 0
    for f in sorted(glob.glob(os.path.join(HERE, 'tests', 'test_*.py'))):
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in sorted(n for n in dir(mod) if n.startswith('test_') and sel in n):
            t = time.time()
            try:
                ok, msg = getattr(mod, name)()
            except Exception as e:
                ok, msg = False, f'{type(e).__name__}: {e}'
            bad += not ok
            print(f'{"PASS" if ok else "FAIL"} {name} ({time.time() - t:.2f} s) {msg}')
    sys.exit(1 if bad else 0)
