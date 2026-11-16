"""XW-F (MC 11/11): the team-file numbers free in EVERY namespace of a built exe - what XW's fixed visitor pool may add
to 220..238 - derived, never listed by hand, so a future pack that takes one fails here.

Source: the build's DATA team files (HT_XWFREE_BUILD, default c/HTW: mkfixtures' release recipe), one namespace per
stem: TEAM.nnn = the 1996-97 game + the base world (1984-85) + the global packs (tourneys, seasons), TMWn.nnn = world
n's own files (World 2026-27: TMW5). A number with a file in any namespace is used.
Reserved, not free (each read from its owner, not hard-coded): mkseason.POOL_IDS (190..199: the worlds' pools and the
guest files), mkseason.WMENU .. + 9 (200..209: the CLASSIC CAREERS world entries), xw.c XW_FIRST - 1 (219: the
registry's end; XW's own 220..), and the file numbers of packs/_template_tourney/pack.json (147, 148: the guide's slot
for the next tourney pack, MC 11/11). The range: 101 (after the game's 0..100, 100 = CUSTOMS) .. XW_FIRST - 1.
- the free set is not empty, and is exactly XW's constant once xw.c has one (XW_FREE_FILES); today it is printed
  (MC 11/11: {189});
- named example of "used in one namespace only": 144 = TEAM.144 (Europe 1984-85) and, with S7, TMW5.144 (Serie D):
  never free, as every number a world uses (XW borrows such numbers per contest instead);
- control: the build's file names with one more TMW5 file on the lowest free number: that number is no longer free;
- the design's old six (145..148, 162, 189: xw-design "Lifting the 19") are reported with their users."""
import glob
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import fixroot  # noqa: E402
ROOT = os.path.dirname(TOOLS)
M = os.path.expanduser('~/swos-mod')
FIRST = 101                                     # (the 1996-97 game's files are 0..100)


def _xw_first():
    src = open(os.path.join(TOOLS, 'xw.c')).read()
    first = int(re.search(r'#define XW_FIRST (\d+)', src).group(1))
    m = re.search(r'#define XW_FREE_FILES \{([\d, ]*)\}', src)
    return first, (set(int(x) for x in m.group(1).replace(' ', '').split(',') if x) if m else None)


def _template():
    m = json.load(open(os.path.join(ROOT, 'packs', '_template_tourney', 'pack.json')))
    return {v[0] if isinstance(v, list) else v['file'] if isinstance(v, dict) else v for v in m['files'].values()}


def namespaces(data):
    """{stem: {file number}} of the build's team files."""
    out = {}
    for f in glob.glob(os.path.join(data, '*.[0-9][0-9][0-9]')):
        stem, n = os.path.basename(f).upper().rsplit('.', 1)
        if stem == 'TEAM' or re.fullmatch(r'TMW\d+', stem):
            out.setdefault(stem, set()).add(int(n))
    return out


def free_files(data):
    import mkseason
    first, xw_const = _xw_first()
    ns = namespaces(data)
    used = set().union(*ns.values())
    reserved = {'POOL_IDS': set(mkseason.POOL_IDS), 'WMENU': set(range(mkseason.WMENU, mkseason.WMENU + 10)),
                'registry end': {first - 1}, '_template_tourney': _template()}
    res = set().union(*reserved.values())
    free = {n for n in range(FIRST, first) if n not in used and n not in res}
    return free, ns, reserved, xw_const


def test_xw_free_files():
    build = os.environ.get('HT_XWFREE_BUILD', fixroot.fx('HTW', 'SWOS'))
    data = os.path.join(build, 'DATA')
    if not os.path.isdir(data):
        return True, f'SKIP: no build {build}'
    free, ns, reserved, xw_const = free_files(data)
    bad, out = [], []
    if 'TEAM' not in ns or len(ns) < 2:
        bad.append(f'namespaces {sorted(ns)}: expected TEAM + at least one TMWn')
    if not free:
        bad.append('no team-file number is free in every namespace')
    if xw_const is not None and xw_const != free:
        bad.append(f"xw.c XW_FREE_FILES {sorted(xw_const)} != the build's free set {sorted(free)}")
    where = lambda n: [s for s in sorted(ns) if n in ns[s]] or [k for k, v in reserved.items() if n in v] or ['free']
    if 144 in free or 'TEAM' not in where(144):
        bad.append(f'144 (TEAM.144, 1984-85): {where(144)}')
    out.append(f'144 used in {where(144)} (one namespace, S7 adds TMW5.144: borrowed per contest, never free)')
    out.append('old six: ' + ', '.join(f'{n} {"/".join(where(n))}' for n in (145, 146, 147, 148, 162, 189)))
    out.append(f'free in every namespace ({"/".join(sorted(ns))}): {sorted(free)}'
               + (' = xw.c XW_FREE_FILES' if xw_const is not None else ' (xw.c has no XW_FREE_FILES yet)'))
    import tempfile                             # the control: a future pack's file on a free number takes it away
    with tempfile.TemporaryDirectory() as d:
        for stem, nums in ns.items():
            for n in nums:
                open(os.path.join(d, f'{stem}.{n:03d}'), 'wb').close()
        taken = min(free) if free else None
        if taken is not None:
            open(os.path.join(d, f'TMW5.{taken:03d}'), 'wb').close()
            f2 = free_files(d)[0]
            if taken in f2 or f2 != free - {taken}:
                bad.append(f'control: TMW5.{taken} added, free {sorted(f2)}')
            out.append(f'control: a TMW5.{taken} leaves {sorted(f2)}')
    return not bad, '; '.join(bad) + (' | ' if bad else '') + '; '.join(out)
