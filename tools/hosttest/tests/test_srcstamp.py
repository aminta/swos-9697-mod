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


def test_stamp_is_the_build_inputs():
    """MC 17/11: the stamp identifies what goes into the exes + DATA (tools/ minus the harness, packs/), by CONTENT: a commit that
    only touches the harness (tools/hosttest/, tools/swostest.py) or only moves HEAD keeps it; a build input changes it; a git
    checkout and a plain copy of the same files agree (so remote_run's server copy needs no second formula)."""
    import srcstamp
    old = _noremote()
    try:
        with tempfile.TemporaryDirectory() as t:
            g = _copy(os.path.join(t, 'g'), '{"n": 1}')
            os.makedirs(os.path.join(g, 'tools', 'hosttest'))
            open(os.path.join(g, 'tools', 'hosttest', 'run.py'), 'w').write('# harness\n')
            open(os.path.join(g, 'tools', 'swostest.py'), 'w').write('# harness\n')
            run = lambda *a: subprocess.run(['git', '-C', g, '-c', 'user.name=t', '-c', 'user.email=t@t', *a], capture_output=True, check=True)
            run('init', '-q')
            run('add', '-A')
            run('commit', '-q', '-m', 'one')
            s0 = srcstamp.stamp(g)
            cp = os.path.join(t, 'copy')                      # a plain copy: no .git (the server's ~/wt/<name>)
            shutil.copytree(os.path.join(g, 'tools'), os.path.join(cp, 'tools'))
            shutil.copytree(os.path.join(g, 'packs'), os.path.join(cp, 'packs'))
            if srcstamp.stamp(cp)['src'] != s0['src']:
                return False, f'a git checkout and a copy of the same files differ: {s0["src"]} vs {srcstamp.stamp(cp)["src"]}'
            open(os.path.join(g, 'tools', 'hosttest', 'run.py'), 'a').write('# more harness\n')
            open(os.path.join(g, 'tools', 'swostest.py'), 'a').write('# more harness\n')
            run('commit', '-q', '-a', '-m', 'harness only')
            run('commit', '-q', '--allow-empty', '-m', 'moves HEAD')
            s1 = srcstamp.stamp(g)
            if s1['src'] != s0['src']:
                return False, f'a harness-only commit / an empty commit changed the stamp: {s0["src"]} -> {s1["src"]}'
            if s1['sha'] == s0['sha']:
                return False, 'the informational sha did not follow HEAD'
            open(os.path.join(g, 'tools', 'patch_stub.py'), 'a').write('# a build input\n')
            s2 = srcstamp.stamp(g)
            if s2['src'] == s0['src']:
                return False, 'an uncommitted build-input change kept the stamp'
            return True, f'harness-only + empty commits keep {s0["src"]}; a build input -> {s2["src"]}; git checkout == plain copy'
    finally:
        if old is not None:
            os.environ['REMOTE_SRC_TEST'] = old
