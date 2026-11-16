"""The release exes the team-cache gates read (test_tc_fixups, test_tc_cap): the newest c/REL42* that holds the 4 CD and
the 4 GOG exes (TC_REL=dir overrides), + its swospp/ exes, or the newest REL42*'s that has them."""
import glob
import os

C = os.path.join(os.path.expanduser('~'), 'swos-mod', 'c')
ORIG = os.path.join(os.path.expanduser('~'), 'swos-mod', 'orig')
LANGS = ('ITALIAN.EXE', 'ENGLISH.EXE', 'FRENCH.EXE', 'GERMAN.EXE')


def release():
    """-> (dir, [exe paths: 4 CD, 4 GOG], [SWOS++ exe paths], swospp dir) or (None, [], [], None)"""
    dirs = [os.environ['TC_REL']] if os.environ.get('TC_REL') else \
        sorted(glob.glob(os.path.join(C, 'REL42*')), key=os.path.getmtime, reverse=True)
    full = lambda d: [os.path.join(d, s, f) for s in ('SWOS', 'gog') for f in LANGS]
    rel = next((d for d in dirs if all(os.path.exists(p) for p in full(d))), None)
    if rel is None:
        return None, [], [], None
    spp = lambda d: sorted(glob.glob(os.path.join(d, 'swospp', '*.EXE')) + glob.glob(os.path.join(d, 'swospp', 'gog', '*.EXE')))
    sd = next((d for d in [rel] + dirs if spp(d)), None)
    return rel, full(rel), spp(sd) if sd else [], sd


def originals():
    return [p for p in (os.path.join(ORIG, f) for f in LANGS) if os.path.exists(p)]
