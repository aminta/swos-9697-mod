"""4.2 S3 x S7 (TRENTO, 15/11; MC review): the Serie B / Serie C play-off skip bits are LOCAL to each league struct's spec (GP_S3T row,
gplay.s3_local). A shaped S7 pack has one spec per struct, so the global ko_playoffs index (bits 26..28) skipped nothing there and
c_po's winner was promoted by gplay AND dplay (the Serie B skip had the same bug). Each case runs in its own process (mkseason caches
its packs): the shaped world (internal/world2526/world5tm-h3s7): struct 102's spec lists b_po 5, b_pout 6, c_po 7 -> B 0x60, C 0x80, no
other struct; the UNSHAPED one (world5tm-h3s, MC (2)): one struct, the rows equal the old global S3MB / S3MC. SKIP without the world."""
import os
import subprocess
import sys

HOME = os.path.expanduser('~')
TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CODE = """
import os, sys
sys.path.insert(0, %r)
w = %r
os.environ['SEASON_PACKS'] = ','.join(os.path.join(w, ln.split()[0].lower()) for ln in open(w + '.txt') if ' file ' in ln)
import dplay, gplay
loc = {k: v for k, v in gplay.s3_local().items() if v != (0, 0)}
print(repr((loc, dplay.s3_b_mask(), dplay.s3_c_mask())))
"""


def _run(name):
    w = os.path.join(HOME, 'swos-mod', 'internal', 'world2526', name)
    if not os.path.exists(w + '.txt'):
        return None
    r = subprocess.run([sys.executable, '-c', CODE % (TOOLS, w)], capture_output=True, text=True, cwd=TOOLS)
    assert r.returncode == 0, r.stderr[-400:]
    return eval(r.stdout.strip().splitlines()[-1])


def test_s3local():
    got = _run('world5tm-h3s7')
    if got is None:
        return True, 'SKIP: world5tm-h3s7 missing'
    loc, gb, gc = got
    assert loc == {(5, 102): (0x60, 0x80)}, loc
    assert (gb, gc) == (1 << 26 | 1 << 27, 1 << 28)            # (the old global bits: nothing in struct 102's 8 entries)
    return True, 'struct 102: B 0x60, C 0x80 (global 26..28 skipped nothing)'


def test_s3local_unshaped():
    got = _run('world5tm-h3s')
    if got is None:
        return True, 'SKIP: world5tm-h3s missing'
    loc, gb, gc = got
    assert len(loc) == 1 and list(loc.values())[0] == (gb, gc) and gb and gc, (loc, gb, gc)
    return True, f'one struct: (B {gb:#x}, C {gc:#x}) == the old global S3MB / S3MC'
