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
