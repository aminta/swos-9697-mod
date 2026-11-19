"""HOSTTEST_SYMS never changes the exe (MC 19/11): a syms build is the release bytes + <EXE>.syms.json beside them, so
a scenario on a syms build tests what ships. Only patch.py reads the switch (to write the labels after the build);
a build module that wants test-only code takes its own TEST_VAR (frnd.py: FRND_TEST -> FR_TEST, no longer
HOSTTEST_SYMS). Static rule over every build module (tools/*.py except the harness / host-side tools), with a red
twin: the 19/11 frnd.py line must be flagged. The byte-level proof (an IT build with and without HOSTTEST_SYMS,
cmp-identical) was made by hand for 42-symsfix; this test keeps the rule from coming back."""
import os
import re

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HOST_SIDE = {'patch.py', 'swostest.py', 'swostest_index.py', 'srcstamp.py', 'mkpatcher.py', 'probe.py'}   # (not build code,
#  or patch.py itself: it writes the syms after the exe is final)
READ = re.compile(r"""(environ(\.get)?\s*[\[(]\s*['"]HOSTTEST_SYMS['"]|getenv\s*\(\s*['"]HOSTTEST_SYMS['"])""")


def offenders(files):
    """[(name, line no, line)] of the build modules that read HOSTTEST_SYMS"""
    out = []
    for name, text in files:
        if name in HOST_SIDE:
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            if READ.search(ln.split('#', 1)[0]):
                out.append((name, i, ln.strip()))
    return out


def _tree():
    return [(f, open(os.path.join(TOOLS, f), encoding='utf-8', errors='replace').read())
            for f in sorted(os.listdir(TOOLS)) if f.endswith('.py')]


def test_syms_bytes_rule():
    bad = offenders(_tree())
    assert not bad, f'build modules read HOSTTEST_SYMS (a syms build would differ from the release bytes): {bad}'
    return True, f'{len(_tree())} tools/*.py: no build module reads HOSTTEST_SYMS (only {sorted(HOST_SIDE)})'


def test_syms_bytes_red_twin():
    old = "    test = os.environ.get('HOSTTEST_SYMS') == '1'     # (test builds: FR_TRACE, ...)\n"
    assert offenders([('frnd.py', old)]), 'twin: the 19/11 frnd.py line was not flagged'
    assert offenders([('x.py', "if os.getenv('HOSTTEST_SYMS'):\n")]), 'twin: getenv form not flagged'
    assert not offenders([('patch.py', old)]), 'patch.py is the one reader'
    assert not offenders([('y.py', "    # os.environ.get('HOSTTEST_SYMS') in a comment\n")]), 'a comment is no read'
    return True, 'the 19/11 frnd.py read and the getenv form are flagged; patch.py and comments are not'
