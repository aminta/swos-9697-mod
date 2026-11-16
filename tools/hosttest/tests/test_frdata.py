"""4.2 preseason friendlies, the data tables (tools/frstr.py strength, tools/frturns.py turns; design 5.1 / 5.3 / 5.4):
the committed tables tools/frdata/*_w0.* (built from a release-recipe build's exe + DATA), the rules they must keep,
and the tools themselves on the original game (orig/). Host only. HT_F9697_BUILD = a build dir (c/RELxx) to
regenerate the tables from and compare (default: the build the tables name; SKIP when it is gone)."""
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


# ---------------------------------------------------------------------------------------------------- strength
def test_frstr_format():
    """the FRSS table parses; blocks sorted by (world, file); every value 0 (no club) or 5 .. 539"""
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
        for i in {n, min(n + 1, 255), 255}:
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
    """blob() / table() refuse what the engine could not index: a count over 255, a record whose own team word is
    not (file, ordinal)"""
    try:
        frstr.blob({(0, 1): [(5, 'X', 0)] * 256})
        return False, 'a 256-club block was accepted'
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
            return True, 'count 256 and a wrong ordinal byte refused'


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
