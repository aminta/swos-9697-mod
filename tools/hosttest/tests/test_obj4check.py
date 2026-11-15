"""obj4check (tools/obj4check.py, MC 15/11: the 4.2 rc freeze's obj4 release-shape checker) on synthetic obj4 images
built from this checkout's swreg bands - a clean release shape PASSes, and each control is caught:
- (a) a planted all-zero page (and an --allow'ed one only reported);
- (b) a band overflow: PRACTICE filled to 100 B under its end (floor 256), and a linked band past OBJ4_PAGES;
- (b) a log extent (a zero-filled table the build reports) counts as used;
- (c) a test-only band (CDKN) and a 4.3 reservation (MKTHOOK) with bytes in a release exe;
- the nested band rule (SLOW owns up to NAMEFIT), the log parser per exe ('OK <path>' sections, '... zero' skipped);
- --grep: a literal next to obj4 in code is a code hit with its swreg symbol, the same in a comment / docstring is a
  comment hit, a line without obj4 context is none; page-region constants of an obj4 module are listed.
HT_OBJ4_REL=<c/RELxx>: the real release dir too (report only: today's 42-int build has the zero pages the freeze packs)."""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import obj4check as oc  # noqa: E402
import swreg  # noqa: E402

BL = oc.bands()
B = {n: (a, e) for n, a, e in BL}
# the freeze's shape (obj1-room.md Release order rule): every test-only band moved into the test region (>= 0x30000)
BLF = sorted([(n, a, e) for n, a, e in BL if oc.kind(n) != 'test-only']
             + [(n, 0x30000 + a, 0x30000 + e) for n, a, e in BL if oc.kind(n) == 'test-only'], key=lambda b: b[1])


def shape(pages, fill=()):
    """obj4 image of `pages` pages: every page non-zero (a marker byte at its start, outside every band's free room
    test), the given (start, end) ranges filled with 0x90."""
    o = bytearray(pages * 0x1000)
    for p in range(pages):
        o[p * 0x1000 + 0xFFF] = 0      # (kept zero)
    for a, e in fill:
        o[a:e] = b'\x90' * (e - a)
    return o


def clean(BL=BLF):
    """A release shape (the freeze's bands, BLF): every release band below OBJ4_PAGES linked with 1 KB (or less)
    used, every page non-zero."""
    pages = -(-B['PRACTICE'][1] // 0x1000)
    fill = []
    for n, a, e in BL:
        if oc.kind(n) != 'release' or e > pages * 0x1000:
            continue
        inner = [a2 for n2, a2, e2 in BL if n2 != n and a < a2 and e2 <= e]
        top = min(inner) if inner else e
        fill.append((a, a + min(0x400, top - a - 256 if top - a > 512 else (top - a) // 4)))
    o = shape(pages, fill)
    for p in range(pages):                              # (pages no band covers: a byte in each)
        if not any(o[p * 0x1000:(p + 1) * 0x1000]):
            hit = [n for n, a, e in BL if a < (p + 1) * 0x1000 and e > p * 0x1000]
            if not hit:
                o[p * 0x1000] = 1
    for p in range(pages):                              # (a zero page inside an unlinked band: link it lightly)
        if not any(o[p * 0x1000:(p + 1) * 0x1000]):
            for n, a, e in BL:
                if oc.kind(n) == 'release' and a <= p * 0x1000 < e:
                    o[p * 0x1000] = 1
                    break
    return o


def test_obj4check_clean():
    o = clean()
    f, i, rows = oc.check_obj4(o, BLF)
    assert not f, f
    return True, f'{len(rows)} bands, {len(o) // 0x1000:#x} pages, 0 findings'


def test_obj4check_control_zero_page():
    o = clean()
    a, e = B['OBJ1MV']
    o[0x16000:0x17000] = bytes(0x1000)                  # (OBJ1MV's top page + nothing else there)
    f, i, _ = oc.check_obj4(o, BL)
    assert any(x.startswith('(a) zero page obj4+0x16000') for x in f), f
    f2, i2, _ = oc.check_obj4(o, BL, allow=[n for n, a2, e2 in BL if a2 < 0x17000 and e2 > 0x16000])
    assert not any('0x16000' in x for x in f2) and any('0x16000' in x and 'allowed' in x for x in i2), (f2, i2)
    return True, 'zero page 0x16000 caught; --allow reports it only'


def test_obj4check_control_overflow():
    o = clean()
    a, e = B['PRACTICE']
    o[a:e - 100] = b'\x90' * (e - 100 - a)
    f, _, _ = oc.check_obj4(o, BL)
    assert any(x.startswith('(b) band PRACTICE') and '100 B free' in x for x in f), f
    o2 = clean()[:(a // 0x1000 + 1) * 0x1000]           # (OBJ4_PAGES cut inside PRACTICE)
    f2, _, _ = oc.check_obj4(o2, BL)
    assert any('PRACTICE' in x and 'crosses OBJ4_PAGES' in x for x in f2), f2
    o3 = clean()
    f3, _, _ = oc.check_obj4(o3, BL, extents=[(B['KITS'][0], B['KITS'][1] - 64)])
    assert any(x.startswith('(b) band KITS') and '64 B free' in x for x in f3), f3
    return True, 'PRACTICE 100 B free caught, PRACTICE past OBJ4_PAGES caught, a log extent counted (KITS 64 B)'


def test_obj4check_control_test_only():
    o = clean()
    o += bytes(max(0, B['MKTHOOK'][0] + 0x1000 - len(o)))
    a, e = B['CDKN']
    o[a + 0x10] = 0xC3
    o[B['MKTHOOK'][0] + 4] = 0xC3
    f, _, _ = oc.check_obj4(o, BL)
    assert any(x.startswith('(c) test-only band CDKN') for x in f), f
    assert any(x.startswith('(c) unlinked (4.3) band MKTHOOK') for x in f), f
    return True, 'CDKN and MKTHOOK bytes caught'


def test_obj4check_nested_and_log():
    o = clean()
    _, _, rows = oc.check_obj4(o, BL)
    r = {n: (a, e) for n, k, a, e, u, fr in rows}
    if 'SLOW' in r and 'NAMEFIT' in B:
        assert r['SLOW'][1] == B['NAMEFIT'][0], r['SLOW']
    log = ('exe: x obj4+0xc000..0xc400 zero\nexe: kits obj4+0xf000..0xfda3 (3491 B), table obj4+0x10000..0x10c64\n'
           'exe: practice page obj4+0x1c800 (1860 B, 1212 B left)\nOK /x/c/R/SWOS/ITALIAN.EXE\n'
           'exe: y obj4+0x11000..0x1137d\nOK /x/c/R/gog/GERMAN.EXE\n')
    ex = oc.log_extents(log)
    assert ex['SWOS/ITALIAN.EXE'] == [(0xf000, 0xfda3), (0x10000, 0x10c64), (0x1c800, 0x1c800 + 1860)], ex
    assert ex['gog/GERMAN.EXE'] == [(0x11000, 0x1137d)], ex
    return True, 'SLOW owns up to NAMEFIT; log sections per exe, parked zero range skipped'


def test_obj4check_grep():
    files = {
        'tools/a.py': 'X = 1\nsite = p.get(4, 0x1C800, 16)\n# obj4 band at 0x1C800\n'
                      'def f():\n    """obj4 docstring 0x1C800\n    more 0x1D000"""\n    return 0x1C800\n',
        'tools/b.c': 'int x = 0x1C800; /* obj4 0x1D400 */\n// obj4 0x1A800\n',
        'tools/c.py': 'NAME_AT = 0x1C800                # a band kept outside swreg\nprint("obj4")\n',
    }
    hits = oc.grep_files(files)
    code = sorted((f, n, lit) for f, n, lit, s, c in hits if not c)
    com = sorted((f, n, lit) for f, n, lit, s, c in hits if c)
    assert ('tools/a.py', 2, '0x1C800') in code, code
    assert ('tools/a.py', 7, '0x1C800') not in code + com, (code, com)        # (no obj4 context on that line)
    assert ('tools/a.py', 3, '0x1C800') in com and ('tools/a.py', 5, '0x1C800') in com, com
    assert ('tools/b.c', 1, '0x1C800') in code and ('tools/b.c', 1, '0x1D400') in com and ('tools/b.c', 2, '0x1A800') in com, (code, com)
    sym = {lit: s for f, n, lit, s, c in hits}
    assert 'PRACTICE_AT' in sym['0x1C800'], sym
    asg = oc.grep_assign(files)
    assert ('tools/c.py', 1, '0x1C800', [s for s in [sym['0x1C800']]][0]) in asg, asg
    return True, f'{len(code)} code / {len(com)} comment hits, {len(asg)} assignment'


def test_obj4check_real():
    rel = os.environ.get('HT_OBJ4_REL')
    if not rel:
        return True, 'SKIP: HT_OBJ4_REL not set'
    ok, rep = oc.check_release(rel)
    lines = rep.splitlines()
    return True, f'report only ({"PASS" if ok else "FAIL"}): ' + ' | '.join(lines[:3])


def test_obj4check_static():
    """--static (MC 15/11): an OBJ4_PAGES line that floors END // 0x1000 needs END page-aligned. Control: a synthetic
    checkout with BOX_END 0xD080 (and a page_end() returning 0x1D400) is caught; the rounding forms are not flagged;
    this checkout's patch.py passes."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'tools'))
        w = lambda n, s: open(os.path.join(d, 'tools', n), 'w').write(s)
        w('swreg.py', 'BOX_END = 0xD080\nKITS_END = 0x11000\nPRACTICE_END = 0x1D400\nFPORT_END = 0x19000\n')
        w('cdkn.py', 'def page_end():\n    """x"""\n    import swreg\n    return swreg.PRACTICE_END\n')
        w('patch.py', 'def f():\n'
                      '    swe.OBJ4_PAGES = max(swe.OBJ4_PAGES, swreg.BOX_END // 0x1000)   # c\n'
                      '    swe.OBJ4_PAGES = max(swe.OBJ4_PAGES, swreg.KITS_END // 0x1000)\n'
                      '    swe.OBJ4_PAGES = max(swe.OBJ4_PAGES, cdkn.page_end() // 0x1000)\n'
                      '    swe.OBJ4_PAGES = max(swe.OBJ4_PAGES, (swreg.FPORT_END + 0xFFF) // 0x1000)\n'
                      '    swe.OBJ4_PAGES = max(swe.OBJ4_PAGES, -(-swreg.PRACTICE_END // 0x1000))\n')
        rows = {n: (v, st) for n, e, v, st in oc.static_pages(root=d)}
    assert rows[2] == (0xD080, 'NOT ALIGNED') and rows[3] == (0x11000, 'ok') and rows[4] == (0x1D400, 'NOT ALIGNED'), rows
    assert rows[5][1] == rows[6][1] == 'rounds up', rows
    real = oc.static_pages()
    bad = [r for r in real if r[3] in ('NOT ALIGNED', 'unresolved')]
    assert not bad, bad
    return True, f'BOX_END 0xd080 + page_end 0x1d400 caught; this checkout: {len(real)} lines, 0 bad'


def test_obj4check_live_item_page():
    """MC 15/11: a zero page holding a linked item the build log reports (patch.py 'engine item ST ... obj4+A..B', the
    ledger's live zero state) is used - info, not a finding; controls: the same page with no logged item FAILs (a), and
    a log line giving a whole band's AT..END over a zero page is no live item (FAILs (a))."""
    o = clean()
    a = 0x5000
    if len(o) <= a + 0x1000:
        o += bytes(a + 0x1000 - len(o))
    o[a:a + 0x1000] = bytes(0x1000)
    lg = 'exe: engine item ST (live state, 144 B) obj4+0x5000..0x5090\nOK /x/c/R/SWOS/ITALIAN.EXE\n'
    ex, it = oc.log_extents(lg), oc.log_items(lg)
    assert it['SWOS/ITALIAN.EXE'] == {(0x5000, 0x5090)}, it
    f, i, _ = oc.check_obj4(o, BLF, ex['SWOS/ITALIAN.EXE'], items=it['SWOS/ITALIAN.EXE'])
    assert not any('0x5000' in x for x in f) and any('obj4+0x5000 used by a logged extent 0x5000..0x5090' in x for x in i), (f, i)
    f2, _, _ = oc.check_obj4(o, BLF)
    assert any(x.startswith('(a) zero page obj4+0x5000') for x in f2), f2
    a3, e3 = B['PRACTICE']                          # control 2 (MC 15/11): a log line with a whole band's range
    o3 = clean()                                    # over its zero page is no live item: still (a)
    p3 = a3 // 0x1000 * 0x1000
    o3[p3:p3 + 0x1000] = bytes(0x1000)
    ex3 = oc.log_extents(f'exe: PRACTICE band obj4+{a3:#x}..{e3:#x}\nOK /x/c/R/SWOS/ITALIAN.EXE\n')['SWOS/ITALIAN.EXE']
    f3, i3, _ = oc.check_obj4(o3, BL, ex3)
    assert any(x.startswith(f'(a) zero page obj4+{p3:#x}') for x in f3) and not any('logged extent' in x for x in i3), (f3, i3)
    return True, 'ST page used via its logged extent; without the log line it FAILs (a); a whole-band log range FAILs (a)'
