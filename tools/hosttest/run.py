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
    sys.path.insert(0, os.path.join(HERE, 'tests'))     # (a test module imports its siblings: test_s7pack -> test_globnum)
    sel = sys.argv[sys.argv.index('-k') + 1] if '-k' in sys.argv else ''
    one = sys.argv[sys.argv.index('--one') + 1] if '--one' in sys.argv else None
    bad, n = 0, {'PASS': 0, 'SKIP': 0, 'FAIL': 0}
    files = [one] if one else sorted(glob.glob(os.path.join(HERE, 'tests', 'test_*.py')))
    if not one and not os.environ.get('HOSTTEST_INPROC'):
        # 42-fixroot (MC 16/11): ONE PROCESS PER TEST MODULE. In one process a test's side effects leaked into the later ones
        # (SEASON_PACKS read at import by mkseason + its packs() cache, set by test_seaw0 / drawgate._world: test_cd_dt, globnum,
        # ri_ida FAILed on it). HOSTTEST_INPROC=1 keeps the old single process (debugging a pollution).
        import subprocess
        import fcntl
        import threading
        n['TIMEOUT'] = 0
        LONG = ('test_ctgame',)         # (MC 16/11: test_ctgame* run ONE AT A TIME across every suite on this Mac (a file lock), 20 min
        for f in files:                 #  timeout reported as TIMEOUT with the load average, never as a FAIL or a PASS)
            long_ = os.path.basename(f)[:-3] in LONG
            lock = None
            if long_:
                os.makedirs(os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest'), exist_ok=True)
                lock = open(os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', '.ctgame.lock'), 'w')
                t0 = time.time()
                fcntl.flock(lock, fcntl.LOCK_EX)
                if time.time() - t0 > 1:
                    print(f'(test_ctgame: waited {time.time() - t0:.0f} s for the cross-suite lock)', flush=True)
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--one', f] + (['-k', sel] if sel else []),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace',
                                 env=dict(os.environ, HOSTTEST_NOVENV='1'))
            timed = []
            if long_:
                def _kill(p=p, timed=timed):
                    timed.append(1)
                    p.kill()
                tm = threading.Timer(float(os.environ.get('HOSTTEST_LONG_TIMEOUT', 1200)), _kill)
                tm.start()
            for line in p.stdout:
                if line.startswith('hosttest: '):
                    continue
                print(line, end='', flush=True)
                for k in n:
                    if line.startswith(k + ' '):
                        n[k] += 1
            p.wait()
            if long_:
                tm.cancel()
                if timed:
                    n['TIMEOUT'] += 1
                    print(f"TIMEOUT {os.path.basename(f)[:-3]} (> {os.environ.get('HOSTTEST_LONG_TIMEOUT', 1200)} s, load average {os.getloadavg()[0]:.1f} {os.getloadavg()[1]:.1f} {os.getloadavg()[2]:.1f}): "
                          'not a PASS, not a FAIL: rerun it alone on a quiet machine', flush=True)
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
        print(f"hosttest: {n['PASS']} PASS, {n['SKIP']} SKIP, {n['FAIL']} FAIL" + (f", {n['TIMEOUT']} TIMEOUT" if n['TIMEOUT'] else ''))
        sys.exit(1 if n['FAIL'] or n['TIMEOUT'] else 0)
    for f in files:
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
            env0 = dict(os.environ)             # (42-fixroot: a test may set SEASON_PACKS & co (test_seaw0, drawgate._world); the next
            try:                                #  tests in this one process must not see it: cd_dt / globnum / ri_ida FAILed on it)
                r = getattr(mod, name)()
                ok, msg = (True, '(asserts)') if r is None else r      # (pytest-style: no exception = PASS; MC 12/11)
            except Exception as e:
                ok, msg = False, f'{type(e).__name__}: {e}'
            finally:
                os.environ.clear()
                os.environ.update(env0)
            bad += not ok
            st = 'FAIL' if not ok else 'SKIP' if str(msg).startswith('SKIP') else 'PASS'
            n[st] += 1
            print(f'{st} {name} ({time.time() - t:.2f} s) {msg}')
    print(f"hosttest: {n['PASS']} PASS, {n['SKIP']} SKIP, {n['FAIL']} FAIL")
    sys.exit(1 if bad else 0)
