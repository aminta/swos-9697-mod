"""4.2 option C: the past-season names of an old (4.1) career save (internal/handoff/oldsave-c-plan.md).

A season record's lines (+16h league, +1Ah cup, +1Eh / +22h continental) keep a name as an obj2 offset relative to
STR_BASE (aChairmanScenes). Names move between releases: a 4.1 save read by a 4.2 exe showed other names. The 4.2 build
ships DATA\\STRMAP41.DAT, per language the 4.1 offsets whose name moved -> its offset in this exe (0: gone), and
gplay's gp_strmap_c translates a 4.1 save's lines at the load, before gp_fixload_c's heuristic.

  STRMAP41.DAT: 'SMAP', u16 format 1, u16 from 41, u16 to 42, u16 0; 4 x (u32 offset, u32 count) for IT EN FR DE;
                per language count x (u32 old rel, u32 new rel), sorted by old rel (only names that moved or are gone).

The 4.1 names come from release/strmap/v4.1-<lang>.json ({'md5': {exe: md5}, 'names': {rel: text}}), pinned once from
the released 4.1 exes (`strmap.py pin REL41dir`); one STRMAP41 serves every 4.1.x save (Davide 10/11: a 4.1.x release
never moves obj2 names).

    python3 tools/strmap.py pin c/REL41<final>          # release/strmap/v4.1-*.json
    python3 tools/strmap.py build c/REL42xx [pins dir]  # c/REL42xx/SWOS/DATA/STRMAP41.DAT
"""
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import le  # noqa: E402

STR_BASE = 0x16F8                          # aChairmanScenes (sacups.STR_BASE: the same in every language)
LANGS = [('it', 'ITALIAN.EXE'), ('en', 'ENGLISH.EXE'), ('fr', 'FRENCH.EXE'), ('de', 'GERMAN.EXE')]
FROM, TO = 41, 42
NAME = 'STRMAP41.DAT'
TAG_GLOBAL, TAG = 1842, 1                 # someLeaguesTable[1842] = this release's save tag, [1843] = -tag (CONVENTIONS 21bis:
                                          # 0 = 4.1 or older, 1 = 4.2); trailer.save_trailer writes it into every save
EN41_ITEM = 'CC'                          # an engine block item 4.1 brought in, saved by every career (world 0 too):
                                          # seen at a load = a 4.1 save (none in 4.0.x: gp_strmap_c leaves those alone)
PINS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'release', 'strmap')
OK = set(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-\'/&()')


def str_ok(d, i):
    """gplay.c str_ok: the start of a name string at d[i] (NUL before, 'A'..'Z' first, 2..41 name chars, NUL)."""
    if i <= 0 or d[i - 1] or not 0x41 <= d[i] <= 0x5A:
        return None
    n = 0
    while n < 41 and i + n < len(d) and d[i + n]:
        if d[i + n] not in OK:
            return None
        n += 1
    return bytes(d[i:i + n]) if n >= 2 and i + n < len(d) and not d[i + n] else None


def names(exe):
    """{rel: text} of every str_ok start in obj2 from STR_BASE (the original pool and every added page)."""
    d = le.LE(exe).obj_bytes(2)
    assert d[STR_BASE:STR_BASE + 6] in (b'SCENE ', b'CHAIRM', b'SCENES', b'PR\x8eSID'), (exe, d[STR_BASE:STR_BASE + 12])
    out = {}
    i = STR_BASE
    while i < len(d):
        t = str_ok(d, i)
        if t:
            out[i - STR_BASE] = t
            i += len(t) + 1
        else:
            i += 1
    return out


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def pair(rel_dir, exe):
    """(CD names, GOG names) of one language: they must be the same (one section serves both)."""
    cd, gog = os.path.join(rel_dir, 'SWOS', exe), os.path.join(rel_dir, 'gog', exe)
    a = names(cd)
    if os.path.exists(gog):
        b = names(gog)
        assert a == b, f'{exe}: CD and GOG names differ ({len(set(a.items()) ^ set(b.items()))} strings)'
    return a, [p for p in (cd, gog) if os.path.exists(p)]


def pin(rel_dir, out=PINS):
    """release/strmap/v4.1-<lang>.json from the released 4.1 build (CD + GOG)."""
    os.makedirs(out, exist_ok=True)
    for lang, exe in LANGS:
        a, paths = pair(rel_dir, exe)
        j = {'from': os.path.basename(os.path.normpath(rel_dir)),
             'md5': {os.path.relpath(p, rel_dir): md5(p) for p in paths},
             'names': {str(r): t.decode('latin-1') for r, t in sorted(a.items())}}
        with open(os.path.join(out, f'v4.1-{lang}.json'), 'w') as f:
            json.dump(j, f, indent=0, sort_keys=False)
            f.write('\n')
        print(f'strmap pin {lang}: {len(a)} names ({exe})')


def mapping(old, new):
    """[(old rel, new rel or 0)] for the old names not at the same place in the new exe, sorted. The new rel: the
    first copy of the text (the lowest offset, as gplay's _sadd keeps one copy)."""
    first = {}
    for r in sorted(new):
        first.setdefault(new[r], r)
    out = []
    for r in sorted(old):
        if new.get(r) == old[r]:
            continue
        out.append((r, first.get(old[r], 0)))
    return out


def check(old, new, m):
    keys = [r for r, _ in m]
    assert keys == sorted(set(keys)), 'strmap: keys not sorted / unique'
    for r, n in m:
        assert r in old and new.get(r) != old[r], r
        assert n == 0 or new.get(n) == old[r], (r, n)


def load_pin(lang, pins=PINS):
    with open(os.path.join(pins, f'v4.1-{lang}.json')) as f:
        j = json.load(f)
    return {int(r): t.encode('latin-1') for r, t in j['names'].items()}


def pack(sections):
    """STRMAP41.DAT bytes from 4 sections [(old, new)] (IT EN FR DE)."""
    hdr = b'SMAP' + struct.pack('<4H', 1, FROM, TO, 0)
    off = len(hdr) + 8 * len(sections)
    tab, body = b'', b''
    for m in sections:
        tab += struct.pack('<2I', off + len(body), len(m))
        body += b''.join(struct.pack('<2I', a, b) for a, b in m)
    return hdr + tab + body


def build(rel_dir, pins=PINS):
    """SWOS/DATA/STRMAP41.DAT of a 4.2 release dir (its CD and GOG exes), against the pinned 4.1 names."""
    secs = []
    for lang, exe in LANGS:
        old = load_pin(lang, pins)
        new, _ = pair(rel_dir, exe)
        m = mapping(old, new)
        check(old, new, m)
        secs.append(m)
        print(f'strmap41 {lang}: {sum(1 for _, n in m if n)} moved, {sum(1 for _, n in m if not n)} gone '
              f'(of {len(old)} 4.1 names)')
    data = pack(secs)
    with open(os.path.join(rel_dir, 'SWOS', 'DATA', NAME), 'wb') as f:   # (one DATA for CD and GOG: the patcher's)
        f.write(data)
    print(f'strmap41: {NAME} {len(data)} B')
    return data


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'pin':
        pin(sys.argv[2], *sys.argv[3:4])
    elif len(sys.argv) >= 3 and sys.argv[1] == 'build':
        build(sys.argv[2], *sys.argv[3:4])
    else:
        sys.exit(__doc__)
