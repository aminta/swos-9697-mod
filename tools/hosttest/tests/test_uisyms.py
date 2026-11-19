"""42-uisyms (MC 19/11): ui_build under SWOSTEST_UI=en on a HOSTTEST_SYMS build dir gives the copy the English exe's
symbols as ITALIAN.syms.json (before: the Italian ones stayed beside the English exe; 43-stars stars_editor EN FAILed
x3 / GP_SCDONE / GP_CT on Italian addresses). No ENGLISH.syms.json but an ITALIAN.syms.json: none in the copy (never
silent stale symbols). A copy made before the fix is put right when reused. Red twin: the old ui_build body (exe only)
FAILs the first check. Fake build dirs in a temp WORK; host only."""
import hashlib
import os
import shutil
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)

md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()


def fake(root, en_syms=True):
    b = os.path.join(root, 'BUILD', 'SWOS')
    os.makedirs(b)
    for n, data in (('ITALIAN.EXE', b'MZ it exe'), ('ENGLISH.EXE', b'MZ en exe'),
                    ('ITALIAN.syms.json', b'{"it": 1}'), ('ENGLISH.syms.json', b'{"en": 2}')):
        if n == 'ENGLISH.syms.json' and not en_syms:
            continue
        open(os.path.join(b, n), 'wb').write(data)
    return b


def old_ui_build(T, b):
    """the ui_build body before 42-uisyms (the red twin): the exe swapped, nothing else"""
    src = os.path.join(b, T.UI_ORIG)
    d = os.path.join(T.WORK, 'builds-x', 'ui_' + T.UI + '_old')
    shutil.copytree(b, d, symlinks=True)
    shutil.copyfile(src, os.path.join(d, 'ITALIAN.EXE'))
    return d


def run(fn, en_syms=True):
    import swostest as T
    keep = T.UI, T.UI_ORIG, T.WORK
    root = tempfile.mkdtemp()
    try:
        T.UI, T.UI_ORIG, T.WORK = 'en', 'ENGLISH.EXE', root
        b = fake(root, en_syms)
        return fn(T, b)
    finally:
        T.UI, T.UI_ORIG, T.WORK = keep
        shutil.rmtree(root, ignore_errors=True)


def check_copy(T, b, d):
    errs = []
    if md5(os.path.join(d, 'ITALIAN.EXE')) != md5(os.path.join(b, 'ENGLISH.EXE')):
        errs.append('ITALIAN.EXE is not the English exe')
    sy = os.path.join(d, 'ITALIAN.syms.json')
    own = os.path.join(b, 'ENGLISH.syms.json')
    if os.path.isfile(own):
        if not os.path.isfile(sy) or md5(sy) != md5(own):
            errs.append('ITALIAN.syms.json is not ENGLISH.syms.json')
    elif os.path.lexists(sy):
        errs.append('Italian symbols left beside the English exe')
    return errs


def test_uisyms_copy_takes_ui_syms():
    errs = run(lambda T, b: check_copy(T, b, T.ui_build(b)))
    assert not errs, errs


def test_uisyms_no_own_syms_removes_italian():
    errs = run(lambda T, b: check_copy(T, b, T.ui_build(b)), en_syms=False)
    assert not errs, errs


def test_uisyms_reused_old_copy_fixed():
    def fn(T, b):
        d = T.ui_build(b)                           # a copy as the old code left it: the Italian symbols
        shutil.copyfile(os.path.join(b, 'ITALIAN.syms.json'), os.path.join(d, 'ITALIAN.syms.json'))
        d2 = T.ui_build(b)                          # (reused: same exe md5)
        return ([] if d2 == d else [f'not reused: {d} / {d2}']) + check_copy(T, b, d2)
    errs = run(fn)
    assert not errs, errs


def test_uisyms_red_twin_old_body_fails():
    errs = run(lambda T, b: check_copy(T, b, old_ui_build(T, b)))
    assert errs == ['ITALIAN.syms.json is not ENGLISH.syms.json'], errs
    errs = run(lambda T, b: check_copy(T, b, old_ui_build(T, b)), en_syms=False)
    assert errs == ['Italian symbols left beside the English exe'], errs


def test_uisyms_symlinked_dst_not_written_through():
    """the copy's ITALIAN.syms.json a symlink to a file X: after ui_syms X is unchanged, dst a regular file = own"""
    def fn(T, b):
        d = T.ui_build(b)
        x = os.path.join(T.WORK, 'X.syms.json')
        open(x, 'wb').write(b'{"x": 3}')
        dst = os.path.join(d, 'ITALIAN.syms.json')
        os.remove(dst)
        os.symlink(x, dst)
        T.ui_syms(b, d)
        errs = []
        if open(x, 'rb').read() != b'{"x": 3}':
            errs.append('written through the symlink into X')
        if os.path.islink(dst) or md5(dst) != md5(os.path.join(b, 'ENGLISH.syms.json')):
            errs.append('dst not a regular copy of ENGLISH.syms.json')
        return errs
    errs = run(fn)
    assert not errs, errs
