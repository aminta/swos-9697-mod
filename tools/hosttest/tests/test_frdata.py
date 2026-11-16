"""4.2 preseason friendlies, the data tables (tools/frstr.py strength, tools/frturns.py turns; design 5.1 / 5.3 / 5.4):
the committed tables tools/frdata/* (built from a release-recipe build's exe + DATA), the rules they must keep,
and the tools themselves on the original game (orig/). Host only. HT_F9697_BUILD = a build dir (c/RELxx) to
regenerate the tables from and compare (default: the build the tables name; SKIP when it is gone).
Strength: FRSS v2 per world (frstr_w0 1996-97, frstr_w4 Europe 1984-85, frstr_w5 World 2026-27) + DATA\\FRSS.DAT (all
three); the career worlds are regenerated in a subprocess under the build's own SEASON_PACKS (buildrel.sh's recipe,
the world data named by the build's build.log; SKIP when that data folder is gone)."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)
import frstr  # noqa: E402
import frturns  # noqa: E402

MAIN = os.path.dirname(TOOLS)
DATA = os.path.join(TOOLS, 'frdata')
ORIG = os.path.join(MAIN, 'orig')
BUILD = os.environ.get('HT_F9697_BUILD') or os.path.join(MAIN, 'c', 'REL42i70')
SHIFTED = {46: (0, 40, 8, 48), 69: (0, 80, 8, 88), 75: (0, 24, 8, 32)}     # Brazil, South Africa, India (option A)
_C = {}


def _str():
    return frstr.parse(open(os.path.join(DATA, 'frstr_w0.bin'), 'rb').read())


def _turns():
    return frturns.parse(open(os.path.join(DATA, 'frturns_w0.bin'), 'rb').read())


def _json():
    return json.load(open(os.path.join(DATA, 'frturns_w0.json')))


def _orig(lang='ENGLISH'):
    if lang not in _C:
        _C[lang] = frturns.rows(frturns.Exe(os.path.join(ORIG, lang + '.EXE')))
    return _C[lang]


def _no_orig():
    if not os.path.isfile(os.path.join(ORIG, 'ENGLISH.EXE')) or not os.path.isdir(os.path.join(ORIG, 'DATA')):
        return True, f'SKIP: {ORIG} missing'
    return None


def _no_build():
    if not os.path.isfile(os.path.join(BUILD, 'SWOS', 'ENGLISH.EXE')):
        return True, f'SKIP: {BUILD} missing (HT_F9697_BUILD)'
    return None


WORLDS = {0: ('1996-97', 76, 76, 1626, '063a16608c704efafe4c1a4ba4932e56'),         # world byte: name, files, countries,
          4: ('Europe 1984-85', 32, 32, 772, '140f3c4f9f2821cc4b6555e838bbc320'),   # clubs, md5 of the slice
          5: ('World 2026-27', 92, 91, 2122, '16c46ffcc71d591d3b748d58672e2b53')}
FRSS_DAT = (10308, '0bb31ea376a7d5bcef4bb8231e7763ac')
# the countries with two club files (country id = the lower file): 2026-27's Brazil + its state championships' file
TWO_FILES = {0: {}, 4: {}, 5: {161: 162}}
# the file rule: the cup-only files of Europe 1984-85 (pack role 'cuponly'), never in a table; none in World 2026-27
CUP_ONLY = {4: [133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144], 5: []}
ITALY = {0: [20], 4: [105], 5: [102]}                # Italy's club files per world (one file each today)


def _md5(b):
    import hashlib
    return hashlib.md5(b).hexdigest()


def _slice(w):
    return open(os.path.join(DATA, f'frstr_w{w}.bin'), 'rb').read()


def _season_packs():
    """(SEASON_PACKS of the build as buildrel.sh exports it, None) or (None, the SKIP text)"""
    import glob
    import re
    log = os.path.join(BUILD, 'build.log')
    m = re.search(r'^\S+ = \S+, data (\S+),', open(log).read(), re.M) if os.path.isfile(log) else None
    if not m:
        return None, f'SKIP: {log} names no world data'
    w = os.path.join(MAIN, 'internal', 'world2526', m.group(1))
    if not os.path.isfile(w + '.txt') or not os.path.isdir(w):
        return None, f'SKIP: world data {w} missing'
    eu = sorted(d.rstrip('/') for d in glob.glob(os.path.join(MAIN, 'packs', 'europe-1984-85', '*/')))
    wp = [os.path.join(w, ln.split()[0].lower()) for ln in open(w + '.txt') if ' file ' in ln]
    return ','.join(['ddr-1988-89', 'italia-1947-48', 'world-cup-1934'] + eu + wp), None


def _regen():
    """the build's tables by a fresh `frstr.py --all` (+ `frstr.py packs`) under its SEASON_PACKS:
    ({name: bytes}, {world: {pack: files}}, None) or (None, None, the SKIP text)"""
    if 'regen' not in _C:
        import subprocess
        import tempfile
        s = _no_build()
        sp, why = (None, s[1]) if s else _season_packs()
        if sp is None:
            _C['regen'] = (None, None, why)
        else:
            env = dict(os.environ, SEASON_PACKS=sp)
            sw = os.path.join(BUILD, 'SWOS')
            with tempfile.TemporaryDirectory() as t:
                r = subprocess.run([sys.executable, os.path.join(TOOLS, 'frstr.py'), '--exe', os.path.join(sw, 'ENGLISH.EXE'),
                                    '--data', os.path.join(sw, 'DATA'), '--all', '--out', t],
                                   cwd=MAIN, env=env, capture_output=True, text=True)
                assert r.returncode == 0, r.stderr[-600:]
                out = {n: open(os.path.join(t, n), 'rb').read() for n in os.listdir(t)}
            out['log'] = r.stdout.encode()
            r = subprocess.run([sys.executable, os.path.join(TOOLS, 'frstr.py'), 'packs'], cwd=MAIN, env=env,
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr[-600:]
            pk = {int(w): v for w, v in json.loads(r.stdout.strip().splitlines()[-1]).items()}
            _C['regen'] = (out, pk, None)
    return _C['regen']


# ---------------------------------------------------------------------------------------------------- strength
def test_frss_v1_refused():
    """FRSS v2 only: the same table with version byte 1 (the v1 layout) is refused by parse / countries / pack; a bad
    magic, a short blob and a length that does not match the index too"""
    b = _slice(0)
    bad = {'v1': b[:4] + b'\x01' + b[5:], 'v3': b[:4] + b'\x03' + b[5:], 'magic': b'FRSX' + b[4:], 'short': b[:-2],
           'long': b + b'\0\0', 'tiny': b[:6]}
    took = []
    for k, x in bad.items():
        for fn in (frstr.parse, frstr.countries, lambda y: frstr.pack({0: y})):
            try:
                fn(x)
                took.append(k)
            except AssertionError:
                pass
    return not took and b[4] == 2 and frstr.VERSION == 2, f'v2 read; refused {sorted(bad)}; accepted {took}'


def test_frss_slices_pinned():
    """the three committed slices: FRSS v2, one world each, the pinned md5 / files / countries / clubs; every value 0
    or 5 .. 539; no national team file (80..85), no guest file (190..194) in a career world"""
    got = {}
    for w, (name, nf, nc, ncl, md5) in WORLDS.items():
        b = _slice(w)
        t, c = frstr.parse(b), frstr.countries(b)
        vals = [v for vs in t.values() for v in vs]
        got[w] = (len(t), len(set(c.values())), len(vals), _md5(b))
        if got[w] != (nf, nc, ncl, md5) or {k[0] for k in t} != {w} or len(b) != 8 + 6 * nf + 2 * ncl:
            return False, f'world {w} ({name}): {got[w]}, {len(b)} B'
        if w and any(k[1] in CUP_ONLY[w] for k in t):
            return False, f'world {w}: a cup-only file in the table'
        if not all(v == 0 or 5 <= v <= 11 * 49 for v in vals) or (w and any(80 <= k[1] <= 85 or 190 <= k[1] <= 194 for k in t)):
            return False, f'world {w}: a value out of range or a national / guest file'
    return True, '; '.join(f'world {w} {WORLDS[w][0]}: {g[0]} files {g[1]} countries {g[2]} clubs {len(_slice(w))} B'
                           for w, g in got.items())


def test_frss_countries():
    """the country id (index byte +3) in every world: a country's id = its lowest file, itself a file of the world
    with that id; world 0 and Europe 1984-85 a country = a file; the two-file countries are exactly the pinned ones
    (2026-27's Brazil 161 + 162) and share one id; Italy's files share one id in every world; two clubs'
    lookups in one country give one id, in two countries two"""
    for w in WORLDS:
        c = {k[1]: v for k, v in frstr.countries(_slice(w)).items()}
        grp = {}
        for fl, i in c.items():
            grp.setdefault(i, []).append(fl)
        if any(i != min(fls) or c.get(i) != i for i, fls in grp.items()):
            return False, f'world {w}: an id that is not its country\'s lowest file'
        two = {i: fls[1] for i, fls in grp.items() if len(fls) == 2}
        if two != TWO_FILES[w] or any(len(fls) > 2 for fls in grp.values()):
            return False, f'world {w}: two-file countries {two}'
        it = {c.get(fl) for fl in ITALY[w]}
        if len(it) != 1 or None in it:
            return False, f'world {w}: Italy\'s files {ITALY[w]} -> ids {it}'
    n5 = [k for k, v in frstr.countries(_slice(5)).items() if v == 161]
    return n5 == [(5, 161), (5, 162)], 'ids = lowest file; two-file countries: ' + ', '.join(
        f'world {w}: {len(v)}' for w, v in TWO_FILES.items()) + '; Italy one id per world'


def test_frss_countries_from_packs():
    """the file rule + the country rule from the build's packs: every career pack's league and state-championship
    files (frstr.pack_roles; not its off-file pool) are in its world's slice under ONE id = the pack's lowest file;
    two packs never share an id; no file of the slice belongs to no pack; the files left out are exactly the pinned
    cup-only ones (role 'cuponly': 12 in Europe 1984-85, none in World 2026-27); Italy's pack is in both worlds"""
    out, packs, skip = _regen()
    if skip:
        return True, skip
    n = 0
    for w in (4, 5):
        c = {k[1]: v for k, v in frstr.countries(_slice(w)).items()}
        seen = {}
        left = {int(f): r for x in packs[w].values() for f, r in x['out'].items()}
        if sorted(left) != CUP_ONLY[w] or set(left.values()) - {'cuponly'} or set(left) & set(c):
            return False, f'world {w}: files left out {left}'
        files = {pid: x['files'] for pid, x in packs[w].items()}
        for pid, fls in files.items():
            ids = {c.get(f) for f in fls}
            if ids != {min(fls)} or min(fls) in seen:
                return False, f'world {w} {pid}: files {fls} -> ids {ids}'
            seen[min(fls)] = pid
            n += 1
        if sorted(f for fls in files.values() for f in fls) != sorted(c):
            return False, f'world {w}: files of the slice != the packs\' files'
        it = [fls for pid, fls in files.items() if pid.endswith('-ita')]
        if it != [ITALY[w]]:
            return False, f'world {w}: Italy\'s pack files {it}'
    return True, f'{n} career packs, one id each (worlds 4, 5); cup-only files left out: {len(CUP_ONLY[4])} + {len(CUP_ONLY[5])}'


def test_frss_worlds_regen():
    """every world's slice regenerated from the build's exe + DATA by frstr (statespec.club_strength on the team
    files' price bytes) == the committed slice == its pinned md5"""
    out, _packs, skip = _regen()
    if skip:
        return True, skip
    for w, (name, _nf, _nc, _ncl, md5) in WORLDS.items():
        b = out.get(f'frstr_w{w}.bin')
        if b is None or b != _slice(w) or _md5(b) != md5:
            return False, f'world {w} ({name}): the build gives {None if b is None else _md5(b)}, pinned {md5}'
    extra = sorted(n for n in out if n.endswith('.bin') and n not in {f'frstr_w{w}.bin' for w in WORLDS})
    return not extra, f'worlds {sorted(WORLDS)} == the committed slices; other worlds in the build: {extra}'


def test_frss_rule_career_worlds():
    """the career worlds' values: every club of the build's TEAM.nnn (world 4) / TMW5.nnn (world 5) files = the rule
    computed here from the raw bytes (best 11 price bytes, at least 5), ordinal by ordinal; a nameless record = 0"""
    s = _no_build()
    if s:
        return s
    n = 0
    for w, stem in ((4, 'TEAM'), (5, 'TMW5')):
        for (_w, fl), vals in frstr.parse(_slice(w)).items():
            f = os.path.join(BUILD, 'SWOS', 'DATA', '%s.%03d' % (stem, fl))
            if not os.path.isfile(f):
                return True, f'SKIP: {f} missing'
            recs = frstr.records(f)
            want = [max(5, sum(sorted((r[76 + 38 * j + 32] for j in range(16)), reverse=True)[:11])) if frstr.name_of(r) else 0
                    for r in recs]
            if want != vals:
                return False, f'world {w} file {fl}: differs'
            n += len(vals)
    return n == WORLDS[4][3] + WORLDS[5][3], f'{n} clubs of worlds 4 + 5'


def test_frss_256th_club():
    """count byte 0 = 256 clubs (frpick.h): World 2026-27's Italy (TMW5.102, 256 clubs) is written with count 0 and
    read as 256; its ordinal 255 (LICATA) is served by lookup, with the build's own strength; no other block of any
    world has count 0; a 256-club table round-trips through blob / parse, a 257-club one is refused"""
    b = _slice(5)
    t = frstr.parse(b)
    i102 = next(i for i in range(len(t)) if b[8 + 6 * i + 1] == 102)
    zero = [(w, x[8 + 6 * i + 1]) for w in WORLDS for x in [_slice(w)] for i in range(len(frstr.parse(x))) if x[8 + 6 * i + 2] == 0]
    rt = frstr.parse(frstr.blob({(9, 1): [(5 + i, 'X', 0) for i in range(256)]}))
    ok = b[8 + 6 * i102 + 2] == 0 and len(t[(5, 102)]) == 256 and zero == [(5, 102)] \
        and frstr.lookup(t, 5, 102 | 255 << 8) == t[(5, 102)][255] > 0 and rt == {(9, 1): [5 + i for i in range(256)]}
    try:
        frstr.blob({(0, 1): [(5, 'X', 0)] * 257})
        return False, 'a 257-club block was accepted'
    except AssertionError:
        pass
    f = os.path.join(BUILD, 'SWOS', 'DATA', 'TMW5.102')
    if _no_build() or not os.path.isfile(f):
        return ok, f'count 0 blocks {zero}, 256 values; (build file not checked: TMW5.102 missing)'
    recs = frstr.records(f)
    return ok and len(recs) == 256 and frstr.club_strength(recs[255]) == t[(5, 102)][255], \
        f'TMW5.102: {len(recs)} clubs, count byte 0; ordinal 255 {frstr.name_of(recs[255])} strength {t[(5, 102)][255]}'


def test_frss_dat_roundtrip():
    """DATA\\FRSS.DAT: pack() of the three slices = the pinned file (size, md5); unpack() gives the slices back;
    the engine's read (world_slice) of each world = its slice, of a world not in the file = None; the header / index
    are the documented bytes; a cut file, a wrong magic / version, an index out of order or with a gap are refused"""
    import struct
    sl = {w: _slice(w) for w in WORLDS}
    b = frstr.pack(sl)
    if (len(b), _md5(b)) != FRSS_DAT or frstr.unpack(b) != sl:
        return False, f'{len(b)} B {_md5(b)}'
    if any(frstr.world_slice(b, w) != sl[w] for w in sl) or frstr.world_slice(b, 1) is not None:
        return False, 'world_slice'
    off, idx = 8 + 12 * 3, []
    for w in sorted(sl):
        idx.append(struct.pack('<BBHII', w, 0, 0, off, len(sl[w])))
        off += len(sl[w])
    if b[:8] != b'FRSD\x01\x03\0\0' or b[8:44] != b''.join(idx) or off != len(b):
        return False, 'header / index bytes'
    e = [b[8 + 12 * i:20 + 12 * i] for i in range(3)]
    bad = {'cut': b[:-1], 'long': b + b'\0', 'magic': b'FRSS' + b[4:], 'version': b[:4] + b'\x02' + b[5:],
           'order': b[:8] + e[1] + e[0] + e[2] + b[44:], 'gap': b[:12] + struct.pack('<I', 46) + b[16:],
           'v1 slice': b[:44] + sl[0][:4] + b'\x01' + b[49:], 'world': b[:8] + b'\x07' + b[9:]}
    took = []
    for k, x in bad.items():
        try:
            frstr.unpack(x)
            took.append(k)
        except AssertionError:
            pass
    return not took, f'{len(b)} B, worlds {sorted(sl)}; refused {sorted(bad)}; accepted {took}'


def test_frss_test_vector():
    """the docstring's TEST VECTOR (frstr.py, the lines 'TV +nn: hex'): the bytes parsed out of the docstring == pack()
    of the same two tiny worlds built here; every line starts at the offset it names; unpack / world_slice / lookup
    read it back (world 5 = bytes 50..65, world 4 = no entry)"""
    import re
    got, n = b'', 0
    for m in re.finditer(r'^  TV \+(\d+): ((?:[0-9A-F]{2} ?)+)', frstr.__doc__, re.M):
        if int(m.group(1)) != len(got):
            return False, f'line TV +{m.group(1)} starts at {len(got)}'
        got += bytes.fromhex(m.group(2))
        n += 1
    s0 = frstr.blob({(0, 20): [(455, 'A', 0), (300, 'B', 0)]})
    s5 = frstr.blob({(5, 102): [(462, 'C', 0)]}, {(5, 102): 102})
    want = frstr.pack({0: s0, 5: s5})
    if got != want:
        return False, f'docstring {got.hex()} != pack() {want.hex()}'
    t5 = frstr.parse(frstr.world_slice(got, 5))
    ok = frstr.unpack(got) == {0: s0, 5: s5} and got[50:66] == s5 and frstr.world_slice(got, 4) is None \
        and frstr.lookup(t5, 5, 102) == 462 and frstr.lookup(t5, 5, 102 | 1 << 8) is None \
        and frstr.lookup(frstr.parse(s0), 0, 20 | 1 << 8) == 300 and frstr.countries(s5) == {(5, 102): 102}
    return ok and n == 9 and len(got) == 66, f'{len(got)} B in {n} docstring lines == pack(); read back'


def test_frss_check_words():
    """the release check's word assert (frstr.verify_words / `frstr.py check`): every (world, file, ordinal) with a
    strength > 0 in FRSS.DAT is a named record with bytes 0 / 1 = file / ordinal in the build's team files -> no
    finding on the build; on a copy of the build's DATA with ONE record removed (TMW5.102's last, LICATA), with a
    blanked name, with a wrong ordinal byte or with a file gone, the words are named; and `frstr.py check` itself
    answers FRSS OK (rc 0) on the good copy, FRSS FAIL (rc 1) on the copy with the record removed (both --frnd); without
    FRND (--no-frnd) the file is a FAIL, no file OK (data after engine)"""
    import shutil
    import subprocess
    import tempfile
    out, _packs, skip = _regen()
    if skip:
        return True, skip
    b, stems = out['FRSS.DAT'], {0: 'TEAM', 4: 'TEAM', 5: 'TMW5'}
    src = os.path.join(BUILD, 'SWOS', 'DATA')
    if frstr.verify_words(b, src, stems):
        return False, f'the build itself: {frstr.verify_words(b, src, stems)[:3]}'
    sp, _why = _season_packs()
    with tempfile.TemporaryDirectory() as t:
        dd = os.path.join(t, 'SWOS', 'DATA')
        os.makedirs(dd)
        for n in os.listdir(src):
            if n.startswith(('TEAM.', 'TMW5.')):
                shutil.copy(os.path.join(src, n), os.path.join(dd, n))
        shutil.copy(os.path.join(BUILD, 'SWOS', 'ENGLISH.EXE'), os.path.join(t, 'SWOS', 'ENGLISH.EXE'))
        open(os.path.join(dd, 'FRSS.DAT'), 'wb').write(b)
        run = lambda sw='--frnd': subprocess.run([sys.executable, os.path.join(TOOLS, 'frstr.py'), 'check', t, sw], cwd=MAIN,
                                                 env=dict(os.environ, SEASON_PACKS=sp), capture_output=True, text=True)
        r0 = run()
        rx = run('--no-frnd')                   # (data after engine: the file in a build without FRND is a FAIL)
        f = os.path.join(dd, 'TMW5.102')
        good = open(f, 'rb').read()
        cases = {'removed': (b'\x00\xff' + good[2:2 + 684 * 255], ['TMW5.102 ordinal 255']),
                 'no name': (good[:2 + 684 * 7 + 5] + bytes(17) + good[2 + 684 * 7 + 22:], ['TMW5.102 ordinal 7 ']),
                 'ordinal byte': (good[:2 + 684 * 3 + 1] + b'\x09' + good[2 + 684 * 3 + 2:], ['TMW5.102 ordinal 3 ']),
                 'cut file': (good[:2 + 684 * 200], [f'TMW5.102 ordinal {i} ' for i in (200, 255)])}
        for k, (d, want) in cases.items():
            open(f, 'wb').write(d)
            bad = frstr.verify_words(b, dd, stems)
            if not bad or any(not any(w in x for x in bad) for w in want) or any('TMW5.102' not in x for x in bad):
                return False, f'{k}: {bad[:3]}'
        nfound = len(bad)
        open(f, 'wb').write(cases['removed'][0])
        r1 = run()
        os.remove(f)
        gone = frstr.verify_words(b, dd, stems)
        os.remove(os.path.join(dd, 'FRSS.DAT'))
        ry = run('--no-frnd')                   # (no FRND, no file: OK)
    ok = r0.returncode == 0 and r0.stdout.strip().splitlines()[-1].startswith('FRSS OK') \
        and r1.returncode == 1 and r1.stdout.strip().splitlines()[-1].startswith('FRSS FAIL') \
        and 'TMW5.102 ordinal 255' in r1.stdout and len(gone) == 256 and nfound == 56 \
        and rx.returncode == 1 and 'without FRND' in rx.stdout and ry.returncode == 0 and 'FRND not linked' in ry.stdout
    return ok, f'build clean; check: good copy rc {r0.returncode}, one record removed rc {r1.returncode}, ' \
               f'no FRND: file rc {rx.returncode} / none rc {ry.returncode} ' \
               f'({r1.stdout.strip().splitlines()[-1][:120] if r1.stdout.strip() else r1.stderr[-200:]})'


def test_frss_dat_build():
    """the build: `frstr.py --all` writes the same FRSS.DAT as pack() of the committed slices; when the build dir
    already ships DATA\\FRSS.DAT (a build made after this change) it is that file too"""
    out, _packs, skip = _regen()
    if skip:
        return True, skip
    b = out.get('FRSS.DAT')
    if b is None or (len(b), _md5(b)) != FRSS_DAT:
        return False, f'regenerated FRSS.DAT: {None if b is None else (len(b), _md5(b))}'
    f = os.path.join(BUILD, 'SWOS', 'DATA', 'FRSS.DAT')
    if not os.path.isfile(f):
        return True, f'regenerated == pinned ({len(b)} B); the build itself predates FRSS.DAT (not shipped in {os.path.basename(BUILD)})'
    return open(f, 'rb').read() == b, f'regenerated == pinned == the build\'s DATA\\FRSS.DAT ({len(b)} B)'


def test_frstr_format():
    """the FRSS v2 table of world 0 parses; blocks sorted by (world, file); every value 0 (no club) or 5 .. 539"""
    t = _str()
    vals = [v for vs in t.values() for v in vs]
    ok = all(0 < len(vs) <= 255 for vs in t.values()) and all(v == 0 or 5 <= v <= 11 * 49 for v in vals)
    return ok and len(t) >= 65, f'{len(t)} files, {len(vals)} clubs, {min(vals)}..{max(vals)}'


def test_frstr_ordinal_bound():
    """the guard: an ordinal >= the file's club count is refused in every file (count, count + 1, 255); the last
    real ordinal is served; the same file under another world byte is refused (the table is keyed by world)"""
    t = _str()
    bad = []
    for (w, fl), vs in t.items():
        n = len(vs)
        for i in {n, min(n + 1, 255), 255} - set(range(n)):
            if frstr.lookup(t, w, fl | i << 8) is not None:
                bad.append((w, fl, i))
        if frstr.lookup(t, w, fl | (n - 1) << 8) != (vs[n - 1] or None):
            bad.append((w, fl, n - 1))
        for w2 in (4, 5, 255):
            if (w2, fl) not in t and frstr.lookup(t, w2, fl) is not None:
                bad.append((w2, fl, 0))
    miss = frstr.lookup(t, 0, 72) is None and frstr.lookup(t, 0, 80) is None      # customs, national teams: no block
    return not bad and miss, f'{len(t)} files; refused past the count; bad {bad[:5]}'


def test_frstr_blob_bound_assert():
    """blob() / table() refuse what the engine could not index: a count over 256 (256 = count byte 0), a record whose
    own team word is not (file, ordinal)"""
    try:
        frstr.blob({(0, 1): [(5, 'X', 0)] * 257})
        return False, 'a 257-club block was accepted'
    except AssertionError:
        pass
    s = _no_orig()
    if s:
        return s
    import tempfile
    d = bytearray(open(os.path.join(ORIG, 'DATA', 'TEAM.000'), 'rb').read())
    d[2 + 684 + 1] = 7                                  # record 1 says ordinal 7
    with tempfile.NamedTemporaryFile(suffix='.000') as f:
        f.write(d)
        f.flush()
        try:
            frstr.table(0, {0: f.name})
            return False, 'a wrong ordinal byte was accepted'
        except AssertionError:
            return True, 'count 257 and a wrong ordinal byte refused'


def test_frstr_rule_is_shared():
    """every original club: frstr.club_strength (statespec.club_strength through the price rows) == the rule
    computed here from the raw bytes (the best 11 price bytes, at least 5)"""
    s = _no_orig()
    if s:
        return s
    files = frstr.world0_files(os.path.join(ORIG, 'ENGLISH.EXE'), os.path.join(ORIG, 'DATA'))
    n = 0
    for fl, path in files.items():
        for r in frstr.records(path):
            want = max(5, sum(sorted((r[76 + 38 * j + 32] for j in range(16)), reverse=True)[:11]))
            if frstr.club_strength(r) != want:
                return False, f'file {fl} {frstr.name_of(r)}: {frstr.club_strength(r)} != {want}'
            n += 1
    return n == 1440 and len(files) == 65 and 'statespec' in frstr.club_strength.__code__.co_names, \
        f'{n} clubs of {len(files)} original files'


def test_frstr_covers_turns():
    """the two tables name the same (world, file / country) set: a club of every league with turns has a strength"""
    a, b = set(_str()), set(_turns())
    return a == b, f'{len(a)} strength blocks, {len(b)} turn rows, only one side {sorted(a ^ b)[:6]}'


def test_frstr_build_regen():
    """the committed table == frstr on the build's own exe + DATA (the shipped 1996-97 files)"""
    s = _no_build()
    if s:
        return s
    tab = frstr.table(0, frstr.world0_files(os.path.join(BUILD, 'SWOS', 'ENGLISH.EXE'), os.path.join(BUILD, 'SWOS', 'DATA')))
    b = frstr.blob(tab)
    return b == open(os.path.join(DATA, 'frstr_w0.bin'), 'rb').read(), f'{len(b)} B, {sum(map(len, tab.values()))} clubs'


# ------------------------------------------------------------------------------------------------------- turns
def test_frturns_rules():
    """every row: 4 turns, even, ascending, 2 apart, >= 0, every one before the first league day F"""
    t = _turns()
    bad = [(k, r) for k, r in t.items()
           if not (len(r['turns']) == 4 and all(w % 2 == 0 for w in r['turns'])
                   and [b - a for a, b in zip(r['turns'], r['turns'][1:])] == [2, 2, 2]
                   and 0 <= r['turns'][0] and r['turns'][3] < r['f'])]
    return not bad and len(t) >= 65, f'{len(t)} rows; bad {bad[:3]}'


def test_frturns_no_clash():
    """no friendly turn on a week of a known cup / qualifier of the country: outside the span of every national cup
    and of every club cup of its continent (the first rounds = the qualifiers a career club can be in at the season
    start; 1996-97 has no UEFA summer qualifying), and in a world with uefaq never on its weeks"""
    j, t = _json(), _turns()
    bad = []
    for r in j['rows']:
        tt = t[(r['world'], r['country'])]['turns']
        assert tt == r['turns']
        for c in r['cups'] + r['conti']:
            a, b = frturns.span(c[1], c[2])
            if any(a <= w <= b for w in tt):
                bad.append((r['country'], tt, c))
        if r['world'] == 5 and set(tt) & {49, 51, 53, 55, 57, 59, 60, 62}:        # (uefaq.py's ties: World 2026-27)
            bad.append((r['country'], tt, 'uefaq'))
    early = sorted(r['country'] for r in j['rows'] if r['flags'] & frturns.EARLY)
    return not bad and early == [20, 32], f'{len(j["rows"])} rows clear; moved before a cup (EARLY): {early}; bad {bad[:3]}'


def test_frturns_plan():
    """the plan F-8, F-6, F-4, F-2 holds in every country but the EARLY ones (Italy: Coppa Italia from week 56 with
    the league at 64 -> 48..54; San Marino: league at 72, the European cups from 64 -> 56..62)"""
    t = _turns()
    bad = [k for k, r in t.items() if not r['flags'] & frturns.EARLY and r['turns'] != [r['f'] - 8 + 2 * i for i in range(4)]]
    it, sm = t[(0, 20)], t[(0, 32)]
    ok = it['f'] == 64 and it['turns'] == [48, 50, 52, 54] and sm['f'] == 72 and sm['turns'] == [56, 58, 60, 62]
    return not bad and ok, f'Italy F {it["f"]} {it["turns"]}, San Marino F {sm["f"]} {sm["turns"]}; bad {bad[:4]}'


def test_frturns_shifted():
    """option A (Davide 16/11): exactly Brazil, South Africa, India are shifted, + 8 on both header weeks (8-48, 8-88,
    8-32), friendlies at 0, 2, 4, 6; every match day of the league moves by exactly 8"""
    j, t = _json(), _turns()
    sh = {r['country']: r for r in j['rows'] if r['flags'] & frturns.SHIFT}
    if sorted(sh) != sorted(SHIFTED):
        return False, f'shifted {sorted(sh)}'
    for n, (f0, l0, f, last) in SHIFTED.items():
        r = sh[n]
        if (r['f0'], r['l0'], r['f'], r['last'], r['shift']) != (f0, l0, f, last, 8) or t[(0, n)]['turns'] != [0, 2, 4, 6] \
                or t[(0, n)]['shift'] != 8 or t[(0, n)]['f'] != 8:
            return False, f'country {n}: {r}'
        a, b = frturns.league_days(r, 0, False), frturns.league_days(r, 0, True)
        if [w + 8 for w in a] != b or b[0] != 8 or b[-1] != last:
            return False, f'country {n}: days {a[:4]} -> {b[:4]}'
    others = [r['country'] for r in j['rows'] if r['shift'] and r['country'] not in SHIFTED] \
        + [k for k, r in t.items() if r['f'] < 8]
    return not others, 'BRA 8-48, RSA 8-88, IND 8-32; turns 0 2 4 6; days + 8'


def test_frturns_shift_findings():
    """the two checks of option A, kept as facts: South Africa's league now ends (88) after its cup (56-80, it ended
    with it at 80); Brazil's league (8-48, 46 days) stays clear of every South American club cup (64-128) and the
    career's last week stays 128"""
    j = _json()
    r = {x['country']: x for x in j['rows']}
    rsa, bra = r[69], r[46]
    cup = [frturns.span(c[1], c[2]) for c in rsa['cups']]
    sa = [frturns.span(c[1], c[2]) for c in bra['conti']]
    days = frturns.league_days(bra)
    ok = cup == [(56, 80)] and rsa['l0'] == 80 and rsa['last'] == 88 \
        and all(a > bra['last'] for a, _ in sa) and len(days) == 46 and days[-1] == 48 and max(b for _, b in sa) == 128
    return ok, f'RSA league 8-88 v cup {cup}; BRA league 8-48 ({len(days)} days) v SA cups {sorted(set(sa))}'


def test_frturns_shift_sites():
    """the bytes option A changes: in each original exe (CD + GOG, 4 languages) the 3 league headers' weeks, 2 bytes
    each at struct +3; the file holds the old bytes there today"""
    s = _no_orig()
    if s:
        return s
    j = _json()
    sites = frturns.shift_sites()
    if sites != j['shift_sites']:
        return False, 'shift_sites() differs from the committed list'
    exes = {x['exe'] for x in sites}
    for x in sites:
        f0, l0, f, last = SHIFTED[x['country']]
        d = open(os.path.join(MAIN, x['exe']), 'rb').read()
        if x['old'] != [f0, l0] or x['new'] != [f, last] or list(d[x['file_off']:x['file_off'] + 2]) != x['old'] \
                or d[x['file_off'] - 1] != x['country']:
            return False, f'{x}'
    return len(sites) == 3 * len(exes) and len(exes) >= 4, f'{len(sites)} sites in {len(exes)} exes'


def test_frturns_slot4():
    """the re-install marks: NATIVE = the divisions with a native play-off (England 2-4, Holland / Scotland / Spain /
    Uruguay top two in the original; + finals97's NSL and NSSL in the build), ICUP4 = the Intercontinental can take
    slot 4 (a league cup + a continent with the Intercontinental: England, Scotland)"""
    s = _no_orig()
    if s:
        return s
    t = _turns()
    orig = {r['country']: r['pomask'] for r in _orig() if r['flags'] & frturns.NATIVE}
    want = {8: 0b1110, 25: 0b11, 33: 0b11, 35: 0b11, 71: 0b11}
    nat = {k[1]: r['pomask'] for k, r in t.items() if r['flags'] & frturns.NATIVE}
    icup = sorted(k[1] for k, r in t.items() if r['flags'] & frturns.ICUP4)
    ok = orig == want and nat == {**want, 44: 1, 62: 1} and icup == [8, 33] \
        and not any(t[(0, n)]['flags'] & (frturns.NATIVE | frturns.ICUP4) for n in SHIFTED)
    return ok, f'NATIVE {nat}, ICUP4 {icup}'


def test_frturns_orig():
    """the original game: 65 club leagues (the design's 67 headers = these + CUSTOM 72 at 64 + the Oceania nations'
    entry 85 at 72), first league weeks 0 x 3, 16 x 4, 24 x 12, 32 x 3, 48 x 1, 56 x 28, 64 x 13, 72 x 1; the four
    languages agree; every original row is in the committed table with the same F / turns / shift"""
    s = _no_orig()
    if s:
        return s
    rs = _orig()
    hist = {}
    for r in rs:
        hist[r['f0']] = hist.get(r['f0'], 0) + 1
    x = frturns.Exe(os.path.join(ORIG, 'ENGLISH.EXE'))
    extra = [frturns.league_of(x, n)[1][3] for n in (72, 85)]
    key = lambda q: [(r['country'], r['f'], r['turns'], r['flags'], r['pomask'], r['shift']) for r in q]
    langs = all(key(_orig(lang)) == key(rs) for lang in frturns.LANGS[1:])
    t = _turns()
    same = all((0, r['country']) in t and (t[(0, r['country'])]['f'], t[(0, r['country'])]['turns'], t[(0, r['country'])]['shift'])
               == (r['f'], r['turns'], r['shift']) and t[(0, r['country'])]['flags'] & r['flags'] == r['flags'] for r in rs)
    ok = len(rs) == 65 and hist == {0: 3, 16: 4, 24: 12, 32: 3, 48: 1, 56: 28, 64: 13, 72: 1} and extra == [64, 72]
    return ok and langs and same, f'{len(rs)} leagues, F {sorted(hist.items())}; 4 languages {langs}; in the table {same}'


def test_frturns_build_regen():
    """the committed table == frturns on the build's exes (4 languages the same rows): the mod's rebuilt / added
    leagues (arg97, mls97, nsl97, nz97, finals97, africa, asia, namerica) are read from what ships"""
    s = _no_build()
    if s:
        return s
    gold = open(os.path.join(DATA, 'frturns_w0.bin'), 'rb').read()
    n = 0
    for lang in frturns.LANGS:
        rs = frturns.rows(frturns.Exe(os.path.join(BUILD, 'SWOS', lang + '.EXE')))
        frturns.check(rs)
        if frturns.blob(rs) != gold:
            return False, f'{lang}: differs'
        n = len(rs)
    return n == len(_turns()), f'{n} leagues x 4 languages == the table'
