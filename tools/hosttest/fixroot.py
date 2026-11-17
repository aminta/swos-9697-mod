"""Host-test fixture root (42-fixroot, MC 16/11). Every test's default fixture path goes through fx(): the fixture dirs
live under ONE root, built once per tip by mkfixtures.sh into c/FX-<tip sha>/ (never rebuilt in place, so another session's
mkfixtures cannot change what a running suite reads), with a MANIFEST.json of md5s.

    export HOSTTEST_FIXROOT=~/swos-mod/c/FX-<sha>      (mkfixtures.sh prints this line)
    fx('HTW', 'SWOS', 'ITALIAN.EXE')  ->  $HOSTTEST_FIXROOT/HTW/SWOS/ITALIAN.EXE

Without HOSTTEST_FIXROOT the root is ~/swos-mod/c, as before (no manifest check). With it, the first fx() of a fixture
checks that fixture's files against MANIFEST.json and raises RuntimeError on a mismatch or a missing manifest entry; the
runner turns that into a FAIL naming the fixture (a stale or edited fixture never PASSes)."""
import hashlib
import json
import os

LEGACY = os.path.join(os.path.expanduser('~'), 'swos-mod', 'c')
_ok = set()


def _auto():
    """HOSTTEST_FIXROOT unset: the newest c/FX-<this checkout's sha>* that mkfixtures.sh built for this tip, else the legacy root."""
    import glob
    import subprocess
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        sha = subprocess.run(['git', '-C', here, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except Exception:
        return None
    c = sorted((p for p in glob.glob(os.path.join(LEGACY, 'FX-' + sha + '*')) if os.path.exists(os.path.join(p, 'MANIFEST.json'))),
               key=os.path.getmtime) if sha else []
    return c[-1] if c else None


def root():
    r = os.environ.get('HOSTTEST_FIXROOT')
    if not r:
        r = _auto()
        if r:
            os.environ['HOSTTEST_FIXROOT'] = r      # (child processes and fx() see the same root; `mkfixtures.sh; run.py` just works)
    return r or LEGACY


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def verify(r, name):
    """Raise RuntimeError unless every file listed for `name` in r/MANIFEST.json exists with the listed md5."""
    if (r, name) in _ok:
        return
    mf = os.path.join(r, 'MANIFEST.json')
    if not os.path.exists(mf):
        raise RuntimeError(f'fixture root {r}: no MANIFEST.json (build it with tools/hosttest/mkfixtures.sh)')
    ent = json.load(open(mf)).get(name)
    if ent is None:
        raise RuntimeError(f'fixture {name!r} is not in {mf} (mkfixtures.sh did not build it)')
    for rel, want in sorted(ent.items()):
        p = os.path.join(r, name, rel)
        got = md5(p) if os.path.isfile(p) else None
        if got != want:
            raise RuntimeError(f'fixture {name}: manifest mismatch for {rel} in {r} (manifest {want}, file {got}): '
                               'stale or edited fixture, rebuild with tools/hosttest/mkfixtures.sh')
    _ok.add((r, name))


def fx(name, *parts):
    r = root()
    if os.environ.get('HOSTTEST_FIXROOT'):
        verify(r, name)
    return os.path.join(r, name, *parts)


def build_dir(env_names, fixture='HTW'):
    """The build a test reads: the first set of env_names (an explicit choice), else the CURRENT tip's fixture dir (never a
    fixed c/<old> dir: MC 17/11, stale defaults silently SKIPped). Returns a path; does not check it exists (see need())."""
    if isinstance(env_names, str):
        env_names = (env_names,)
    for n in env_names:
        if os.environ.get(n):
            return os.environ[n]
    return fx(fixture, 'SWOS')


def release_dir(env_names=('HOSTTEST_REL',)):
    """A 4-exe release dir: the first set of env_names, else the NEWEST c/REL42*/SWOS with its 4 exes (the release the rc runner
    just built; set HOSTTEST_REL to pin it). None when there is none (callers FAIL through need())."""
    import glob
    for n in env_names:
        if os.environ.get(n):
            return os.environ[n]
    c = [p for p in glob.glob(os.path.join(LEGACY, 'REL42*', 'SWOS'))
         if all(os.path.isfile(os.path.join(p, x + '.EXE')) for x in ('ITALIAN', 'ENGLISH', 'FRENCH', 'GERMAN'))]
    return max(c, key=os.path.getmtime) if c else None


def need(path, what, *files):
    """RuntimeError (the runner turns it into a FAIL) when the build/dir a test needs is missing or lacks `files`: a missing
    input is never a silent SKIP (MC 17/11)."""
    if not path or not os.path.isdir(path):
        raise RuntimeError(f'{what}: no build at {path} (set the *_BUILD / HOSTTEST_REL env, or run tools/hosttest/mkfixtures.sh)')
    for f in files:
        if not os.path.exists(os.path.join(path, f)):
            raise RuntimeError(f'{what}: {path} lacks {f} (rebuild: tools/hosttest/mkfixtures.sh)')
    return path
