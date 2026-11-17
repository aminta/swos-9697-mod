"""No test reads a fixed c/<old> dir as its default build (MC 17/11, rule 0): the stale c/S1R / c/T3h / c/HTW defaults SKIPped
silently for weeks. A test's default build is the CURRENT tip's fixture (fixroot.build_dir / fixroot.fx) or release dir
(fixroot.release_dir); a missing build FAILs through fixroot.need(). Guard: (1) every `'c', '<NAME>'` literal in a test is
in REFERENCE (an old build on purpose: a golden / a before-after reference, named with its owner); (2) need() raises on a
missing dir and a missing file; (3) build_dir() honours the env, then the fixture."""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import fixroot  # noqa: E402

# old builds read ON PURPOSE (a reference to diff against; the owner re-points them when the reference changes)
REFERENCE = {'REL40rc2': 'test_kits (4.0 kit reference)', 'REL41rc3': 'test_italy_import (4.1 data)',
             'RELpr5': 'test_practice (practice reference exe)', 'REL42i53': 'test_practice (Shaved: off-sites reference)',
             'REL42i70': 'test_frdata (Motore: friendlies data release dir)', 'REL42x5383': 'test_zbis_golden (golden)',
             'REL42strmap-ht': 'test_strmap (rebuilt per tip by the gate script; owner Shaved: move into mkfixtures)'}


def test_no_fixed_default_dirs():
    bad = []
    for f in sorted(os.listdir(HERE)):
        if not f.endswith('.py') or f == os.path.basename(__file__):
            continue
        for i, line in enumerate(open(os.path.join(HERE, f), encoding='utf-8', errors='replace'), 1):
            if line.lstrip().startswith('#') or 'join(' not in line:   # (path joins only: 'c', 'file' in a dict is not a dir)
                continue
            for m in re.finditer(r"'c', '([A-Za-z0-9_.-]+)'", line):
                if m.group(1) not in REFERENCE and not m.group(1).startswith('FX-'):
                    bad.append(f'{f}:{i} {m.group(1)}')
    assert not bad, bad
    return True, f'no test defaults to a fixed c/<dir> except the {len(REFERENCE)} named references'


def test_need_fails_loudly():
    d = tempfile.mkdtemp()
    for args in ((None, 'x'), (os.path.join(d, 'nope'), 'x'), (d, 'x', 'ITALIAN.syms.json')):
        try:
            fixroot.need(*args)
        except RuntimeError as e:
            assert 'x' in str(e)
        else:
            raise AssertionError(f'need{args} did not raise')
    open(os.path.join(d, 'ITALIAN.syms.json'), 'w').close()
    assert fixroot.need(d, 'x', 'ITALIAN.syms.json') == d
    return True, 'a missing dir / a missing file raises (the runner turns it into a FAIL); a present one passes'


def test_build_dir_defaults():
    keep = os.environ.pop('HT_ZZ_BUILD', None)
    try:
        assert fixroot.build_dir('HT_ZZ_BUILD').endswith(os.path.join('HTW', 'SWOS'))
        os.environ['HT_ZZ_BUILD'] = '/x/y'
        assert fixroot.build_dir(('HT_QQ_BUILD', 'HT_ZZ_BUILD')) == '/x/y'
    finally:
        os.environ.pop('HT_ZZ_BUILD', None)
        if keep:
            os.environ['HT_ZZ_BUILD'] = keep
    return True, 'build_dir: env first, else the current fixture HTW'
