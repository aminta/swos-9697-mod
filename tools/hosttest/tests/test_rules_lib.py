"""Engine step H, Tier A: the shared rules library (aminta/swos-competition-engine rules/, swosrules.h v1) built and
tested natively - its own `make test` (contract tests, i486 freestanding build, spec / league / season checks, team
words, parallel groups). HT_ENGINE = the checkout (default ~/swos-competition-engine); none there: SKIP as a PASS."""
import os
import subprocess

ENGINE = os.environ.get('HT_ENGINE') or os.path.join(os.path.expanduser('~'), 'swos-competition-engine')


def test_rules_library():
    if not os.path.exists(os.path.join(ENGINE, 'rules', 'swosrules.h')):
        return True, f'SKIP: no engine checkout at {ENGINE}'
    r = subprocess.run(['make', '-C', ENGINE, 'test'], capture_output=True, text=True)
    out = r.stdout + r.stderr
    ok = [ln for ln in out.splitlines() if ln.startswith('PASS')]
    bad = [ln for ln in out.splitlines() if ln.startswith('FAIL') or 'error:' in ln]
    head = subprocess.run(['git', '-C', ENGINE, 'describe', '--tags', '--always'], capture_output=True, text=True)
    return r.returncode == 0 and not bad, f'{head.stdout.strip()}: make test rc {r.returncode}, {len(ok)} PASS' + \
        (f', {bad[:3]}' if bad else '')
