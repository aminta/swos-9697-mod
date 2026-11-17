"""MC 16/11 (ui_build audit, internal/handoff/ui-build-audit.md): every harness scenario that takes its build from the
environment through ui_dir / ui_build launches, under SWOSTEST_UI=en / fr / de, that language's exe - no DOSBox.

Each scenario runs in its own python (swostest reads SWOSTEST_UI at import) with SWOSTEST_BUILD / W8485_BUILD (and the
scenario-specific *_BUILD it names) = UIGUARD_BUILD (default c/HTW/SWOS, a release-recipe dir with the 4 exes), a stub
Session / Dosbox start that records exe_lang of the exe it would launch and stops the scenario, and a stub build() /
builds() (no exe is built). A scenario that returns or skips before its first game start (it needs a save or data
that this dir lacks) is listed as not reached, never as a PASS of its own; one that reaches a launch with the wrong
language FAILs. UIGUARD_ONLY=a,b: those scenarios only."""
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROOT = os.path.dirname(TOOLS)
MAIN = os.path.join(os.path.expanduser('~'), 'swos-mod')
ENVS = ('SWOSTEST_BUILD', 'W8485_BUILD', 'COACHNAT_BUILD', 'ZBSKIP_BUILD', 'STM_BUILD', 'TITLENAV_BUILD',
        'MAINBTN_BUILD', 'TEAMCOL_BUILD')
DRIVER = r'''
import json, os, sys
sys.path.insert(0, os.path.join(sys.argv[1], 'tools'))
import swostest as T
name = sys.argv[2]
seen = []
class Stop(BaseException):
    pass
def rec(exe_dir):
    e = exe_dir if os.path.isfile(exe_dir) else os.path.join(exe_dir, 'ITALIAN.EXE')
    seen.append(T.exe_lang(e) if os.path.isfile(e) else None)
    raise Stop()
class S:
    def __init__(self, name, exe_dir, *a, **k):
        rec(exe_dir)
T.Session = S
T.Dosbox = S
T.build = lambda *a, **k: (_ for _ in ()).throw(Stop())
try:
    T.SCENARIOS[name]()
except Stop:
    pass
except BaseException as e:
    if not seen:
        print(json.dumps({'reached': False, 'why': type(e).__name__ + ': ' + str(e)[:120]}))
        sys.exit(0)
print(json.dumps({'reached': bool(seen), 'lang': seen[0] if seen else None}))
'''


def _scenarios():
    """The scenarios whose body takes a build through ui_dir( / ui_build( and names an env build variable."""
    L = open(os.path.join(TOOLS, 'swostest.py'), errors='replace').read().split('\n')
    out, i = [], 0
    while i < len(L):
        if L[i].startswith('@scenario'):
            j = i + 1
            while not L[j].startswith('def '):
                j += 1
            name = re.match(r'def (\w+)\(', L[j]).group(1)
            k = j + 1
            while k < len(L) and not re.match(r'(def |@|class )', L[k]):
                k += 1
            body = '\n'.join(L[j:k])
            if re.search(r'\bui_(dir|build)\(', body) and re.search(r"'(%s)'" % '|'.join(ENVS), body):
                out.append(name)
            i = k
        else:
            i += 1
    return out


def test_uiguard_scenarios():
    import fixroot
    b = fixroot.need(fixroot.release_dir(('UIGUARD_BUILD', 'HOSTTEST_REL')), 'test_uiguard_scenarios',
                     *(x + '.EXE' for x in ('ITALIAN', 'ENGLISH', 'FRENCH', 'GERMAN')))   # (a 4-exe release dir: the newest REL42*)
    only = [x for x in os.environ.get('UIGUARD_ONLY', '').split(',') if x]
    names = [n for n in _scenarios() if not only or n in only]
    py = '/opt/homebrew/bin/python3' if os.path.exists('/opt/homebrew/bin/python3') else sys.executable
    bad, ok, notr = [], 0, []
    for n in names:
        for ui in ('en', 'fr', 'de'):
            env = {k: v for k, v in os.environ.items() if k not in ENVS and k != 'SWOSTEST_UI_ANYEXE'}
            env.update({k: b for k in ENVS}, SWOSTEST_UI=ui, SWOSTEST_RUNS=os.path.join(MAIN, 'internal', 'swostest',
                                                                                         'runs-uiguard'))
            r = subprocess.run([py, '-c', DRIVER, ROOT, n], env=env, capture_output=True, text=True, timeout=300)
            try:
                res = json.loads(r.stdout.strip().split('\n')[-1])
            except (ValueError, IndexError):
                res = {'reached': False, 'why': (r.stderr.strip().split('\n') or ['?'])[-1][:120]}
            if not res['reached']:
                notr.append(f'{n}/{ui} ({res.get("why", "returned before a launch")})')
            elif res['lang'] != ui:
                bad.append(f'{n}: SWOSTEST_UI={ui} launches the {res["lang"]} exe')
            else:
                ok += 1
    assert not bad, bad
    return True, (f'{len(names)} scenarios x en/fr/de: {ok} launches in the UI language, 0 wrong; not reached '
                  f'(a skip / missing input before the first launch) {len(notr)}: {"; ".join(notr)[:1500]}')
