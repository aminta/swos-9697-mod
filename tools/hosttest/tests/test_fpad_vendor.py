"""4.2 fixture port P2 (MC 14/11, change 3): the engine sources fpad.c includes are the engine's at tools/swce/SWCE_SHA,
byte for byte. With an engine checkout (HT_ENGINE, default ~/swos-competition-engine) holding that commit: the vendored
files against `git show SWCE_SHA:rules/<file>`; without one: against the sha1s recorded here when they were vendored.
Any drift (a hand edit of tools/swce/, a new copy without its SWCE_SHA) = FAIL."""
import hashlib
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SWCE = os.path.join(HERE, '..', '..', 'swce')
ENGINE = os.environ.get('HT_ENGINE') or os.path.join(os.path.expanduser('~'), 'swos-competition-engine')
FILES = ('sr_port.c', 'swosrules.h')
RECORDED = {'346d040': {'sr_port.c': '18480217430b3587b45d99cdffb8ea7a820ab3c8',
                        'swosrules.h': '1e22ddcb4cec73f5c07886cfef84baca1cec66a9'},
            '1522654': {'sr_port.c': '2ab9a865aa0495ef082cc0e35a342f3a02795814',     # SR_PORT_WINDOWS 24 (MC 14/11)
                        'swosrules.h': '369abc7a9fff6747f8b0ed5e61c567272365003a'}}


def _sha1(b):
    return hashlib.sha1(b).hexdigest()


def test_fpad_vendor():
    sha = open(os.path.join(SWCE, 'SWCE_SHA')).read().strip()
    have = {f: _sha1(open(os.path.join(SWCE, f), 'rb').read()) for f in FILES}
    bad = []
    r = subprocess.run(['git', '-C', ENGINE, 'cat-file', '-t', sha], capture_output=True, text=True) \
        if os.path.isdir(ENGINE) else None
    if r is not None and r.returncode == 0 and r.stdout.strip() == 'commit':
        src = f'engine {sha}'
        for f in FILES:
            g = subprocess.run(['git', '-C', ENGINE, 'show', f'{sha}:rules/{f}'], capture_output=True)
            if g.returncode or _sha1(g.stdout) != have[f]:
                bad.append(f'{f}: tools/swce {have[f][:12]} != engine {sha} {_sha1(g.stdout)[:12] if not g.returncode else "missing"}')
        if sha in RECORDED and RECORDED[sha] != have and not bad:
            bad.append(f'RECORDED[{sha}] out of date (the engine agrees with tools/swce)')
    else:
        src = f'recorded sha1s of {sha} (no engine checkout with it)'
        if sha not in RECORDED:
            return False, f'SWCE_SHA {sha}: no engine checkout and no recorded sha1s - record them'
        bad = [f'{f}: {have[f][:12]} != recorded {RECORDED[sha][f][:12]}' for f in FILES if have[f] != RECORDED[sha][f]]
    return not bad, '; '.join(bad) or f'{", ".join(FILES)} = {src}'
