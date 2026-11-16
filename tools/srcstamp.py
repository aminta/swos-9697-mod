"""The source stamp of a build (MC 16/11, rule 0: a harness never silently tests a prebuilt exe older than its tree).

stamp(root) = {'src': the source identity, 'sha': git HEAD or ''}. 'src' is the very hash remote_run.sh passes to the
server as REMOTE_SRC_TEST (shasum, first 16 hex, of: git rev-parse HEAD, git diff HEAD --binary, then each untracked
file under tools/ as its name + newline + its bytes) - so a build stamped here matches the same tree on
MacMiniM1Server, whose copy has no .git (there the identity comes from REMOTE_SRC_TEST). No git and no REMOTE_SRC_TEST:
None (the tree cannot be identified: nothing is judged).

patch.py writes it into a HOSTTEST_SYMS build's <EXE>.syms.json as '_src' in the file's [obj, value] shape with obj -1
(as_syms: readers that walk every module's [obj, offset] pairs - hosttest emu - match no obj -1); swostest's
build_stale(exe_dir) compares it with the tree it runs from."""
import hashlib
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(root, *a):
    return subprocess.run(['git', '-C', root, *a], capture_output=True, check=True).stdout


def stamp(root=ROOT):
    try:
        head = _git(root, 'rev-parse', 'HEAD')
        h = hashlib.sha1(head + _git(root, 'diff', 'HEAD', '--binary'))
        for f in _git(root, 'ls-files', '--others', '--exclude-standard', 'tools').decode().split('\n'):
            if f:                       # (as remote_run.sh's printf + cat: the name always, the bytes if a file)
                h.update(f.encode() + b'\n')
                if os.path.isfile(os.path.join(root, f)):
                    h.update(open(os.path.join(root, f), 'rb').read())
        return {'src': h.hexdigest()[:16], 'sha': head.decode().strip()}
    except (OSError, subprocess.CalledProcessError):
        src = os.environ.get('REMOTE_SRC_TEST')
        return {'src': src, 'sha': ''} if src else None


def same(a, b):
    """two stamps of the same source"""
    return bool(a and b and a.get('src')) and a.get('src') == b.get('src')


def as_syms(st):
    return {k: [-1, v] for k, v in (st or {}).items()}


def from_syms(d):
    return {k: v[1] for k, v in d.items()} if d else None
