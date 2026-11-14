"""4.2 Mod caps (MC 14/11): tools/split.py _orient gets a node bound (SR_SPLIT_FIRST as the engine's sr_split.c, applied lower here because this walk
is ~1000x slower: SPLIT_PY_FIRST) and fails loudly instead of hanging; tools/fport.py asserts a stage window's end <= 255 instead of clamping.
Bytes unchanged: every group size that works today (2..18 clubs) gives the orientation it gave before (sha256 of the committed split.py's output,
recorded below), and fport --json is byte-equal on all world5tm-* (checked at the commit: 109 worlds, none clamped)."""
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import split  # noqa: E402

# sha256 of repr(_orient(m, _round_robin(m))) for m = 2..18 as the committed split.py (before the cap) gives it
SHA = {
    2: '262e139c97fa9ad965ee0eaa13a415ec8fa0318f3f68c057eb2e1b495650c873',
    3: 'bc9a3aa4e4b597c917661eeb76c07b47ab667cc89263b4f22ebfc8065b24d68b',
    4: '733bbd1a489713b11adada69699f0f38b85fd0fb46d841b9f3084d121f72a386',
    5: '8a2cd99cc673eaa3f6a737f253f531acf598fca000ec6c4cfe38d7e42db955bc',
    6: '81276be3d429f8b615bbc2d49e17c647bcb3a6bf170a04ca525dbb02212ef853',
    7: 'b77f5d7903e2bc44be3622afcf856f3ac30f55cecf2aec131b2322d56986872a',
    8: 'dc6d5268ebff065e2768e9c970d4f5e8fab35a116d5d647562127729ee3f53b3',
    9: '1c3418713d68a36ccea614332bbe764b53c0f43273c6718c950569ce01d0e32a',
    10: '272f4d54df108c959f2fff8539801c77d715d3b4ab430ac6e7249b89e4e0def6',
    11: 'fd067e5a6c1c5490389ba9f88d120965930695b00f8d791ad8bb25b8c0312a06',
    12: 'd51c68559e75a4e6a6a6a5c34bb64bd52c87d051067be02b21f675132a493c3a',
    13: '92a2a96215a1872b0d40e57549d86d17dc034bc77c6f2c179dfe44ea9b8aef8c',
    14: 'f8f64bdcd4d14f6eba7a64408bc7c84757c997a6cf88780b408717bfe0c629d0',
    15: 'e4858b502cfb5cf9451b5bba53c61cdeff0a49b43720a713dc9c580e514dd7e5',
    16: '39122734f51308d7d9510f7b3663f2dc21b7df73f095ae9f63d8ec255e8d7c2f',
    17: '54e167703a1252034f5895dee12750a8cb5ae5fffb0a0061a3b0e6180100cb4b',
    18: 'f349c31d0b66c6a710b582cb863bab6fff22f01fed20c46c721cf3871ac3043f',
}


def digest(m):
    return hashlib.sha256(repr(split._orient(m, split._round_robin(m))).encode()).hexdigest()


def test_split_orient_cap():
    errs = []
    assert split.SR_SPLIT_FIRST == 200_000_000, split.SR_SPLIT_FIRST          # (the engine's value, same name)
    # the sizes that work: first orientation within the Python cap, with margin (18 clubs need 225,661 of 300,000)
    for m in range(2, 19):
        d = digest(m)
        if SHA[m] != d:
            errs.append(f'{m}: orientation changed')
    # 20 / 24 clubs: refused within seconds, naming the size and the node count
    for m in (20, 24):
        t = time.time()
        try:
            split._orient(m, split._round_robin(m))
            errs.append(f'{m} clubs: not refused')
        except AssertionError as e:
            msg = str(e)
            if f'group of {m} clubs' not in msg or 'nodes' not in msg or time.time() - t > 15:
                errs.append(f'{m} clubs: refusal {msg[:120]!r} after {time.time() - t:.1f} s')
    assert not errs, '; '.join(errs)


def test_split_orient_parity_with_head():
    """the committed (pre-cap) split.py, from git, is the oracle: the same orientation for 2..18 clubs."""
    import subprocess
    import types
    here = os.path.join(os.path.dirname(__file__), '..', '..')
    try:
        src = subprocess.check_output(['git', 'show', 'HEAD~1:tools/split.py'], cwd=here, stderr=subprocess.DEVNULL).decode()
    except Exception:
        print('SKIP: no git history for the oracle')
        return
    if 'SR_SPLIT_FIRST' in src:
        print('SKIP: HEAD~1 already has the cap')
        return
    old = types.ModuleType('split_old')
    exec(compile(src, 'split_old', 'exec'), old.__dict__)
    for m in range(2, 19):
        assert old._orient(m, old._round_robin(m)) == split._orient(m, split._round_robin(m)), m


def test_fport_window_assert():
    import fport
    root = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'world2526', 'world5tm-h2')
    if not os.path.isdir(root):
        print('SKIP: no world5tm-h2')
        return
    fport.world(root)                                      # (as it is: no window past 255, no assert)
    real = fport.po_days
    fport.po_days = lambda po: 300                         # (forced: a play-off of 300 days)
    try:
        try:
            fport.world(root)
            raise AssertionError('a 300-day play-off window was clamped, not refused')
        except AssertionError as e:
            if 'past 255' not in str(e):
                raise
    finally:
        fport.po_days = real
