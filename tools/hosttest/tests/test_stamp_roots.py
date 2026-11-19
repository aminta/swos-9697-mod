"""Every file a build READS is covered by srcstamp.stamp() (MC 17/11: "a build made before an internal/ data change must not
match the tip"). The test traces a real patch_exe (Italian exe: an audit hook on open()) from this checkout with the
release data, then FAILs on any file read from outside this checkout that is not (a) a stamped input (srcstamp.STAMP_ROOTS +
orig/ top level), (b) the per-build data dir and its .txt (SRC_STAMP.json 'data'), (c) in ALLOW with a reason. A new reader of
some internal/ dir therefore fails here until the dir joins STAMP_ROOTS (or ALLOW, with the reason).
Data: HT_STAMP_DATA (a name under internal/world2526), else the 'data <name>' of the newest c/REL42* build.log."""
import glob
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKOUT = os.path.realpath(os.path.join(HERE, '..', '..', '..'))
MAIN = os.path.join(os.path.expanduser('~'), 'swos-mod')
sys.path.insert(0, os.path.join(CHECKOUT, 'tools'))
import srcstamp  # noqa: E402

ALLOW = dict(srcstamp.CONTENT_CACHES)      # (MC 19/11: the content-keyed caches, an explicit named list - srcstamp's own;
                                           #  not a looser root check: any other internal/ read outside the roots still FAILs)
# (c/SWOS/DATA/TEAM.020 gone, MC 17/11: sacups.team_index reads the TEAM.020 this run's patch_teams wrote, patch.TEAM020_OUT)

TRACE = r'''
import sys, os, shutil, tempfile
seen = set()
def hook(ev, args):
    if ev == 'open' and isinstance(args[0], (str, bytes)):
        try:
            seen.add(os.path.realpath(os.fsdecode(args[0])))
        except Exception:
            pass
sys.addaudithook(hook)
sys.path.insert(0, 'tools')
import patch
t = tempfile.mkdtemp()
data = os.path.join(t, 'DATA'); shutil.copytree('orig/DATA', data)
r = patch.patch_teams('orig/DATA/TEAM.020', data + '/TEAM.020')
patch.write_new_teams('orig/DATA', data)
patch.rename_clubs('orig/DATA', data)
patch.patch_exe('orig/ITALIAN.EXE', os.path.join(t, 'ITALIAN.EXE'), r, 'it')
shutil.rmtree(t, ignore_errors=True)
open(sys.argv[1], 'w').write('\n'.join(sorted(seen)))
'''


def _data_name():
    n = os.environ.get('HT_STAMP_DATA')
    if n:
        return n
    for lg in sorted(glob.glob(os.path.join(MAIN, 'c', 'REL42*', 'build.log')), key=os.path.getmtime, reverse=True):
        m = re.search(r', data (world5tm-[A-Za-z0-9_-]+),', open(lg, errors='replace').read())
        if m and os.path.isdir(os.path.join(MAIN, 'internal', 'world2526', m.group(1))):
            return m.group(1)
    raise RuntimeError('no release data to trace with (set HT_STAMP_DATA=<name under internal/world2526>)')


def classify(read, w):
    """(reads outside the stamp, not the data dir, not ALLOW; how many reads were stamped inputs)"""
    stamped = {os.path.realpath(q) for _, q in srcstamp._inputs(CHECKOUT)}
    allow = [os.path.realpath(os.path.join(MAIN, k)) for k in ALLOW]
    wreal = os.path.realpath(w)
    bad, n_stamped = [], 0
    for p in read:
        if not p.startswith(MAIN + os.sep) or p.startswith(CHECKOUT + os.sep):
            continue                                    # (python's own files, temp dirs, this checkout: tools/ + packs/ are stamped)
        if p in stamped:
            n_stamped += 1
        elif p.startswith(wreal + os.sep) or p == wreal + '.txt' or any(p == a or p.startswith(a + os.sep) for a in allow):
            continue
        else:
            bad.append(os.path.relpath(p, MAIN))
    return bad, n_stamped


def test_cache_reads_allowed_stray_reads_fail():
    """MC 19/11: a read under a content-keyed cache (internal/drawgate, internal/swostest/cobj) is allowed by name; red twin:
    a read in another internal/ dir that is neither a stamped root nor in that list still FAILs."""
    w = os.path.join(MAIN, 'internal', 'world2526', 'no-such-data')
    ok = [os.path.join(MAIN, 'internal', 'drawgate', '0' * 16 + '.json'),
          os.path.join(MAIN, 'internal', 'swostest', 'cobj', 'x.o')]
    stray = [os.path.join(MAIN, 'internal', 'stampdg-red-twin', 'x.json'),
             os.path.join(MAIN, 'internal', 'swostest', 'runs', 'x.json')]
    b_ok, _ = classify([os.path.realpath(p) for p in ok], w)
    b_st, _ = classify([os.path.realpath(p) for p in stray], w)
    want = sorted(os.path.relpath(os.path.realpath(p), MAIN) for p in stray)
    return (not b_ok and sorted(b_st) == want,
            f'cache reads flagged {b_ok} (want none); stray reads flagged {sorted(b_st)} (want {want})')


def test_stamp_covers_every_build_read():
    name = _data_name()
    w = os.path.join(MAIN, 'internal', 'world2526', name)
    eu = ','.join(os.path.join(CHECKOUT, p.rstrip('/')) for p in sorted(glob.glob('packs/europe-1984-85/*/')))
    eu = ','.join(os.path.realpath(os.path.join(CHECKOUT, 'packs', 'europe-1984-85', d))
                  for d in sorted(os.listdir(os.path.join(CHECKOUT, 'packs', 'europe-1984-85')))
                  if os.path.isdir(os.path.join(CHECKOUT, 'packs', 'europe-1984-85', d)))
    files = [f'{w}/{ln.split()[0].lower()}' for ln in open(w + '.txt') if ' file ' in ln]
    env = dict(os.environ, SEASON_PACKS=','.join(['ddr-1988-89', 'italia-1947-48', 'world-cup-1934', eu] + files),
               PYTHONDONTWRITEBYTECODE='1')
    out = tempfile.mktemp()
    r = subprocess.run([sys.executable, '-c', TRACE, out], cwd=CHECKOUT, env=env, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError('the traced build failed: ' + (r.stderr.strip().splitlines() or ['?'])[-1][:200])
    read = open(out).read().split('\n')
    os.remove(out)
    bad, n_stamped = classify(read, w)
    assert not bad, ('a build reads files the stamp does not cover - add their root to srcstamp.STAMP_ROOTS (or to ALLOW here, '
                     'with the reason): ' + ', '.join(sorted(bad)[:12]) + (' ...' if len(bad) > 12 else ''))
    # (a stamped file in checkout paths counted: tools/ and packs/ by the HARNESS-free walk)
    return True, f'{name}: every file the Italian build read outside this checkout is a stamped input ({n_stamped}), the data dir, or ALLOW ({len(ALLOW)})'
