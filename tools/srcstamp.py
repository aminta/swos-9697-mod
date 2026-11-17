"""The source stamp of a build (MC 16/11, rule 0: a harness never silently tests a prebuilt exe older than its tree).

stamp(root) = {'src': the source identity, 'sha': git HEAD or ''} (stamp()'s docstring: the one definition). 'src' is the very hash remote_run.sh passes to the
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


TREE_DIRS = ('tools', 'packs')          # (a tree without its own .git: the build's inputs remote_run.sh copies - notes/
                                        #  is copied too but never read by a build)


def _files(root):
    """a tree that is not its own git checkout (an rsync'd copy; remote_run's ~/wt/<name>): every file under
    TREE_DIRS, by relative path - name + NUL + bytes (17/11, Difficolta: its identity used to be the env alone)"""
    h = hashlib.sha1(b'tree\n')
    for d in TREE_DIRS:
        for dp, dn, fn in os.walk(os.path.join(root, d)):
            dn[:] = sorted(x for x in dn if x != '__pycache__')
            for f in sorted(fn):
                q = os.path.join(dp, f)
                h.update(os.path.relpath(q, root).encode() + b'\0')
                if os.path.isfile(q):
                    h.update(open(q, 'rb').read())
    return h.hexdigest()[:16]


def stamp(root=ROOT):
    """ONE definition of 'which sources built this exe' (MC 17/11, rule 0: build_key, patch.py's '_src', remote_run.sh's
    REMOTE_SRC_TEST and snapshot.py all use it). Its own git checkout: HEAD + diff + untracked tools/ files. Not its own
    checkout (no .git, or a copy that sits inside another repo): REMOTE_SRC_TEST when set (the server's copy of a tree
    stamped on this Mac), else the files under TREE_DIRS."""
    try:
        top = _git(root, 'rev-parse', '--show-toplevel').decode().strip()
    except (OSError, subprocess.CalledProcessError):
        top = ''
    if top and os.path.realpath(top) == os.path.realpath(root):
        head = _git(root, 'rev-parse', 'HEAD')
        h = hashlib.sha1(head + _git(root, 'diff', 'HEAD', '--binary'))
        for f in _git(root, 'ls-files', '--others', '--exclude-standard', 'tools').decode().split('\n'):
            if f:                       # (as remote_run.sh's printf + cat: the name always, the bytes if a file)
                h.update(f.encode() + b'\n')
                if os.path.isfile(os.path.join(root, f)):
                    h.update(open(os.path.join(root, f), 'rb').read())
        return {'src': h.hexdigest()[:16], 'sha': head.decode().strip()}
    src = os.environ.get('REMOTE_SRC_TEST')
    if src:
        return {'src': src, 'sha': ''}
    if any(os.path.isdir(os.path.join(root, d)) for d in TREE_DIRS):
        return {'src': _files(root), 'sha': ''}
    return None


def same(a, b):
    """two stamps of the same source"""
    return bool(a and b and a.get('src')) and a.get('src') == b.get('src')


def as_syms(st):
    return {k: [-1, v] for k, v in (st or {}).items()}


def from_syms(d):
    return {k: v[1] for k, v in d.items()} if d else None


if __name__ == '__main__':             # (remote_run.sh: `python3 tools/srcstamp.py ROOT` prints the src, the server's
    import sys                          #  REMOTE_SRC_TEST - the same function as every local reader)
    st = stamp(os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT)
    print(st['src'] if st else '')
