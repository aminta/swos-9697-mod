"""The source stamp of a build (MC 16/11, rule 0: a harness never silently tests a prebuilt exe older than its tree).

stamp(root) = {'sha': git HEAD, 'dirty': '' for a clean tree, else the md5 of the uncommitted state (git diff HEAD --
binary, plus every untracked file's path and bytes, git ls-files --others --exclude-standard)}. patch.py writes it into
a HOSTTEST_SYMS build's <EXE>.syms.json as '_src' in the file's [obj, value] shape with obj -1 (as_syms: readers that
walk every module's [obj, offset] pairs - hosttest emu - match no obj -1); swostest's build_stale(exe_dir) compares it
with the tree it runs from."""
import hashlib
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(root, *a):
    return subprocess.run(['git', '-C', root, *a], capture_output=True, check=True).stdout


def stamp(root=ROOT):
    try:
        sha = _git(root, 'rev-parse', 'HEAD').decode().strip()
        h = hashlib.md5(_git(root, 'diff', 'HEAD', '--binary'))
        for f in sorted(_git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')):
            if f and os.path.isfile(os.path.join(root, f)):
                h.update(f.encode() + b'\0' + open(os.path.join(root, f), 'rb').read())
        d = h.hexdigest()
        return {'sha': sha, 'dirty': '' if d == hashlib.md5(b'').hexdigest() else d}
    except (OSError, subprocess.CalledProcessError):
        return {'sha': '', 'dirty': 'no git'}


def same(a, b):
    """two stamps of the same source (a stamp without a sha - no git - never matches)"""
    return bool(a and b and a.get('sha')) and (a.get('sha'), a.get('dirty')) == (b.get('sha'), b.get('dirty'))


def as_syms(st):
    return {k: [-1, v] for k, v in st.items()}


def from_syms(d):
    return {k: v[1] for k, v in d.items()} if d else None
