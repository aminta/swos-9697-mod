"""TEMP markers (MC 17/11, tools/tempmark.py): a release build with a temporary patch registered is refused; without
one, or as a test / HOSTTEST_SYMS / beta build, it passes. The registry and the sources agree: every TEMP-<NAME>
literal under tools/ is a KNOWN name whose file holds it, every KNOWN name still has its literal, and each one is
declared at build time by a temp_marker('<NAME>') call in a build module. The refusal is patch.py's: check() sits
between the last link step and the exe's save, reset() at the exe's start."""
import os
import re
import sys

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import tempmark

REL = {}                                        # a release build's environment: nothing set
ENVS = (                                        # (environment, a release?)
    (REL, True), ({'MODVER_TAG': 'RC3'}, True), ({'MODVER_TAG': 'rc1'}, True),
    ({'MODVER_TAG': 'B11'}, False), ({'HOSTTEST_SYMS': '1'}, False), ({'FPORT': '1'}, False),
    ({'GPLAY_FORCE': '1'}, False), ({'ANY_NEW_FORCE': '1'}, False), ({'FPML_SEED': '0x2a'}, False),
    ({'GPLAY_FORCE': ''}, True), ({'HOSTTEST_SYMS': ''}, True),
)


def _refused(env):
    try:
        tempmark.check(env, log=lambda t: None)
        return False
    except SystemExit as e:
        assert 'REFUSED' in str(e) and all(f'TEMP-{n}' in str(e) for n in tempmark.MARKS), str(e)
        return True


def test_tempmark_release_refused():
    saved = dict(tempmark.MARKS)
    try:
        n = 0
        for env, rel in ENVS:
            if tempmark.is_release(env) != rel:
                return False, f'is_release({env}) = {not rel}, want {rel}'
            tempmark.reset()                    # no marker: every build passes
            if _refused(env) or tempmark.check(env) != []:
                return False, f'{env}: refused without a marker'
            for names in (('G1',), ('BANDS', 'G5')):
                tempmark.reset()
                for x in names:
                    tempmark.temp_marker(x)
                if _refused(env) != rel:
                    return False, f'{env} with {names}: refused {not rel}, want {rel}'
                n += 1
        tempmark.reset()
        try:                                    # an undeclared name cannot be registered
            tempmark.temp_marker('NOT-KNOWN')
            return False, 'temp_marker of a name outside KNOWN accepted'
        except AssertionError:
            pass
        lines = []
        tempmark.temp_marker('G1')
        tempmark.check({'HOSTTEST_SYMS': '1'}, log=lines.append)
        if len(lines) != 1 or 'TEMP-G1' not in lines[0]:
            return False, f'a test build with a marker logs {lines}'
        return True, f'{n} builds: a release / RC with a marker refused, the same without one passes; test, ' \
                     'HOSTTEST_SYMS and beta builds pass and name their markers'
    finally:
        tempmark.MARKS.clear()
        tempmark.MARKS.update(saved)


def _sources():
    for root, _dirs, files in os.walk(TOOLS):
        if '__pycache__' in root or os.sep + 'hosttest' in root:
            continue
        for f in files:
            if f.endswith(('.py', '.c', '.h', '.asm', '.inc', '.sh')) and f != 'tempmark.py':
                yield os.path.join(root, f)


def test_tempmark_registry_matches_sources():
    found, calls = {}, set()
    for path in _sources():
        text = open(path, errors='replace').read()
        for m in re.finditer(r'TEMP-([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)', text):
            found.setdefault(m.group(1), set()).add(os.path.relpath(path, TOOLS))
        calls |= set(re.findall(r"temp_marker\('([^']+)'", text))
    errs = []
    for name, files in sorted(found.items()):
        if name not in tempmark.KNOWN:
            errs.append(f'TEMP-{name} in {sorted(files)} is not in tempmark.KNOWN')
    for name, (f, _why) in sorted(tempmark.KNOWN.items()):
        if f not in found.get(name, ()):
            errs.append(f'KNOWN {name}: no TEMP-{name} literal in tools/{f} (the block is gone: drop the line and its call)')
        if name not in calls:
            errs.append(f'KNOWN {name}: no temp_marker(\'{name}\') call in a build module')
    for name in sorted(calls - set(tempmark.KNOWN)):
        errs.append(f'temp_marker(\'{name}\') called but not KNOWN')
    src = open(os.path.join(TOOLS, 'patch.py')).read()
    a, b, c = src.find("__import__('tempmark').reset()"), src.find("__import__('tempmark').check()"), src.find('delta, shift = p.save(dst)')
    if not (0 <= a < b < c):
        errs.append(f'patch.py: tempmark reset {a} / check {b} / save {c} (want reset < check < the exe\'s save)')
    return not errs, '; '.join(errs) or f'{len(tempmark.KNOWN)} markers ({", ".join(sorted(tempmark.KNOWN))}): each a literal in its ' \
                                        'file, declared by a temp_marker call; patch.py resets per exe and checks before the save'
