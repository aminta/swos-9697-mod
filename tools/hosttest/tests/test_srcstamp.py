"""srcstamp = the one source identity (MC 17/11, rule 0): build_key uses it, so 'which sources built this exe' has one
definition. Trees that are not their own git checkout (rsync'd copies, remote_run's ~/wt/<name>) hash tools/ + packs/:
two copies differing only in packs/ get different stamps AND build keys; equal copies equal ones; REMOTE_SRC_TEST
(the server's copy of a tree stamped on this Mac) wins over the files; this checkout keeps its git identity."""
import hashlib
import os
import shutil
import tempfile
import subprocess
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, TOOLS)


def _copy(dst, pack_text):
    os.makedirs(os.path.join(dst, 'tools'))
    os.makedirs(os.path.join(dst, 'packs', 'x'))
    shutil.copy(os.path.join(TOOLS, 'srcstamp.py'), os.path.join(dst, 'tools'))
    open(os.path.join(dst, 'tools', 'patch_stub.py'), 'w').write('# a build input\n')
    open(os.path.join(dst, 'packs', 'x', 'pack.json'), 'w').write(pack_text)
    return dst


def _noremote():
    return os.environ.pop('REMOTE_SRC_TEST', None)


def test_copies_differing_in_packs():
    import srcstamp
    import swostest
    old = _noremote()
    try:
        with tempfile.TemporaryDirectory() as t:
            a, b, c = (_copy(os.path.join(t, n), x) for n, x in (('a', '{"n": 1}'), ('b', '{"n": 2}'), ('c', '{"n": 1}')))
            sa, sb, sc = (srcstamp.stamp(x) for x in (a, b, c))
            if not (sa and sb and sc and sa['sha'] == ''):
                return False, f'no file stamp: {sa} {sb} {sc}'
            if sa['src'] == sb['src']:
                return False, 'copies differing in packs/ share a stamp'
            if sa['src'] != sc['src']:
                return False, 'equal copies, different stamps'
            ka, kb, kc = (swostest.build_key(x, {}) for x in (a, b, c))
            if ka == kb or ka != kc:
                return False, f'build_key does not follow the stamp: {ka} {kb} {kc}'
            open(os.path.join(c, 'tools', 'patch_stub.py'), 'a').write('# changed\n')
            if srcstamp.stamp(c)['src'] == sa['src']:
                return False, 'copies differing in tools/ share a stamp'
            return True, f'packs/ -> {sa["src"]} vs {sb["src"]}, keys {ka} vs {kb}; equal copies equal; tools/ too'
    finally:
        if old is not None:
            os.environ['REMOTE_SRC_TEST'] = old


def test_remote_src_wins():
    import srcstamp
    old = os.environ.get('REMOTE_SRC_TEST')
    os.environ['REMOTE_SRC_TEST'] = '0123456789abcdef'
    try:
        with tempfile.TemporaryDirectory() as t:
            st = srcstamp.stamp(_copy(os.path.join(t, 'a'), '{}'))
            return st == {'src': '0123456789abcdef', 'sha': ''}, f'server copy: {st}'
    finally:
        if old is None:
            os.environ.pop('REMOTE_SRC_TEST')
        else:
            os.environ['REMOTE_SRC_TEST'] = old


def test_git_checkout_unchanged():
    """this checkout: the git identity remote_run.sh computes on this Mac (HEAD + diff + untracked tools/)"""
    import srcstamp
    root = os.path.abspath(os.path.join(TOOLS, '..'))
    if subprocess.run(['git', '-C', root, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() \
            != os.path.realpath(root):
        return True, 'SKIP: not run from a git checkout'
    st = srcstamp.stamp(root)
    sh = subprocess.run(['bash', '-c', 'git rev-parse HEAD && git diff HEAD --binary && git ls-files --others '
                         '--exclude-standard tools | while read f; do printf "%s\\n" "$f"; cat "$f"; done'],
                        cwd=root, capture_output=True).stdout
    want = hashlib.sha1(sh).hexdigest()[:16]
    return st['src'] == want, f'git stamp {st["src"]} vs remote_run.sh formula {want}'
