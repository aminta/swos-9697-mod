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

# old builds read ON PURPOSE: GOLDEN references ("golden output of X, must not change"; MC 17/11). A reference without a reason
# written by its owner follows the current build. Owners: write the reason in place of 'owner: ...'.
REFERENCE = {'REL40rc2': 'test_kits: golden 4.0 kit output (owner: write the reason)',
             'REL41rc3': 'test_italy_import: golden 4.1 data (owner: write the reason)',
             # (Motore 17/11) test_frdata: the committed friendlies tables tools/frdata/ (frstr_w0/w4/w5.bin, frturns_w0) were generated
             # from REL42i70's exes + DATA; regenerating them from that same build must give the committed bytes (frstr / frturns
             # determinism + the pinned FRSS slices). A newer build legitimately differs (team data / skills change), so this must
             # not follow the current build. If REL42i70 is removed the test SKIPs (HT_F9697_BUILD): regenerate the tables from a new
             # release build and re-pin them, as a deliberate data change.
             'REL42i70': 'test_frdata: golden - the committed tools/frdata tables were generated from this build (Motore)',
             'REL42x5383': 'test_zbis_golden: golden (owner: write the reason)'}
# NOT valid references (MC 17/11): they must follow the current build; the owner converts them, then this entry goes
PENDING = {'RELpr5': 'test_practice REF (Difficolta: stale for today\'s PRACTICE band, e1f9ce9)',
           'REL42i53': 'test_practice off-sites / RBAR REF (Difficolta: stale, e1f9ce9; ask which old-vs-new pair it needs)',
           'REL42strmap-ht': 'test_strmap: rebuilt per tip by the gate script; goes into mkfixtures (Shaved)'}


def test_no_fixed_default_dirs():
    bad = []
    for f in sorted(os.listdir(HERE)):
        if not f.endswith('.py') or f == os.path.basename(__file__):
            continue
        for i, line in enumerate(open(os.path.join(HERE, f), encoding='utf-8', errors='replace'), 1):
            if line.lstrip().startswith('#') or 'join(' not in line:   # (path joins only: 'c', 'file' in a dict is not a dir)
                continue
            for m in re.finditer(r"'c', '([A-Za-z0-9_.-]+)'", line):
                if m.group(1) not in REFERENCE and m.group(1) not in PENDING and not m.group(1).startswith('FX-'):
                    bad.append(f'{f}:{i} {m.group(1)}')
    assert not bad, bad
    return True, f'no test defaults to a fixed c/<dir> except {len(REFERENCE)} named golden references and {len(PENDING)} PENDING conversions ({', '.join(PENDING)})'


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


def test_release_dir_matches_the_tip():
    import json
    sys.path.insert(0, os.path.join(HERE, '..', '..'))
    import srcstamp
    want = srcstamp.stamp(os.path.abspath(os.path.join(HERE, '..', '..', '..')))
    keep = os.environ.pop('HOSTTEST_REL', None)
    try:
        d = tempfile.mkdtemp()
        sw = os.path.join(d, 'REL42zz', 'SWOS')
        os.makedirs(sw)
        json.dump(want, open(os.path.join(d, 'REL42zz', 'SRC_STAMP.json'), 'w'))
        os.environ['HOSTTEST_REL'] = sw
        assert fixroot.release_dir() == sw
        json.dump({'src': '0' * 16, 'sha': 'x'}, open(os.path.join(d, 'REL42zz', 'SRC_STAMP.json'), 'w'))
        try:
            fixroot.release_dir()
        except RuntimeError as e:
            assert 'not from this tree' in str(e), str(e)
        else:
            raise AssertionError('a release dir built from another tree was accepted')
        os.remove(os.path.join(d, 'REL42zz', 'SRC_STAMP.json'))
        try:
            fixroot.release_dir()
        except RuntimeError:
            pass
        else:
            raise AssertionError('a release dir with no stamp was accepted')
    finally:
        os.environ.pop('HOSTTEST_REL', None)
        if keep:
            os.environ['HOSTTEST_REL'] = keep
    return True, 'release_dir: a pinned dir must carry this tree\'s stamp (another stamp / none: RuntimeError)'
