"""POSITION TRAITS release guard and its red twin (MC 19/11): trhead.relcheck - run by buildrel on every release dir -
must say OK on a default build of a GP_RUOLI tree and REFUSE a TRHD_NOLINK=1 build (the structural REF).

  python3 tools/hosttest/trhd_relguard.py DEFAULT_BUILD NOLINK_BUILD     (each a dir with ITALIAN.EXE or SWOS/ITALIAN.EXE)
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import trhead


def as_rel(build, tmp, name):
    """A release-shaped dir (SWOS/ITALIAN.EXE) for one build dir."""
    if os.path.exists(os.path.join(build, 'SWOS', 'ITALIAN.EXE')):
        return build
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, 'SWOS'))
    shutil.copy(os.path.join(build, 'ITALIAN.EXE'), os.path.join(d, 'SWOS', 'ITALIAN.EXE'))
    return d


def main():
    assert len(sys.argv) == 3, __doc__
    assert trhead._gameplay() is not None, 'a tree with GP_RUOLI (gameplay.gp_ruoli) only'
    with tempfile.TemporaryDirectory() as tmp:
        ok_def, l_def = trhead.relcheck(as_rel(sys.argv[1], tmp, 'def'))
        ok_nl, l_nl = trhead.relcheck(as_rel(sys.argv[2], tmp, 'nolink'))
    print(f'default: {l_def}\nNOLINK (red twin, expect FAIL): {l_nl}')
    good = ok_def and not ok_nl and 'TRHD FAIL' in l_nl
    print('PASS' if good else 'FAIL')
    sys.exit(0 if good else 1)


if __name__ == '__main__':
    main()
