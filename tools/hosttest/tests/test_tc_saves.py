"""Team cache, gate H2 (teamcache-fable-design.md 1.8, leg 2): tools/tcaudit.py's classification of a .CAR's cache-relative
values. (1) its layout constants against their owners (wsites.DIY_SLOTS, sreg_walk.c, careerworld, trailer, the original
exes); (2) planted cases on a synthetic save, both cache forms, with an unmarked control; (3) known real saves (private
dir internal/: SKIP without it). The whole archive is run by hand: `python3 tools/tcaudit.py --report ... PATHS`
(report: internal/swostest/tcaudit/leg2-report.md)."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import tcaudit as T  # noqa: E402

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
HOME = os.path.expanduser('~')
INTERNAL = os.path.join(HOME, 'swos-mod', 'internal')
ORIG = os.path.join(HOME, 'swos-mod', 'orig')


def test_tc_layout():
    import careerworld
    import trailer
    import wsites
    assert [(o, r) for _, o, r in T.SLOTS] == wsites.DIY_SLOTS, 'tcaudit.SLOTS != wsites.DIY_SLOTS'
    assert T.IDA_CFB == wsites.IDA_CFB and T.CAL_AT == wsites.CAL and (T.CAL_END - T.CAL_AT) // 22 == wsites.CAL_N
    assert (T.TEAM, T.OLD_ROOM) == (trailer.TEAM_SIZE, trailer.SELECTED_ROOM)
    assert (T.SEL_CAP, T.SEL_ROOM, T.B_SEL) == (careerworld.SEL_CAP, careerworld.SEL_ROOM, careerworld.B_SEL)
    assert (T.BIGC, T.BIGC_AT - T.TMD_AT, T.WMARK) == (careerworld.BIGC, careerworld.BIGC_AT, careerworld.WMARK)
    assert T.WORLD_AT - T.SLT_AT == careerworld.WORLD_BYTE
    assert T.LOADER_RANGE[0] == T.SLOTS[1][1], 'the loader range starts at slot 1 (D8D0A)'
    assert T.LOADER_RANGE[1] == T.SLOTS[0][1] + 0xB52, 'the loader range ends with competitionFileBuffer'
    assert all(T.LOADER_RANGE[0] <= o and o + r <= T.LOADER_RANGE[1] for _, o, r in T.SLOTS)
    c = open(os.path.join(TOOLS, 'sreg_walk.c')).read()
    m = re.search(r'enum \{ DL_N = (\d+), DL_MAX = (\d+), DL_STAGE = (0x[0-9A-Fa-f]+) \};\s*static const uint16_t DL_LIST\[3\] = '
                  r'\{ 301, 589, 153 \}, DL_SIZE\[3\] = \{ (\w+), (\w+), (\w+) \};', c)
    assert m, 'sreg_walk.c: walk_diy constants not found'
    assert (int(m[1]), int(m[2]), int(m[3], 16)) == (T.DL_N, T.DL_MAX, T.DL_STAGE)
    assert tuple(int(m[k], 16) for k in (4, 5, 6)) == T.DL_SIZE
    # the offset arrays end with their contest: league 691 + 64 x 18 = 0x733, cup 0x343 + 64 x 4 = 0x443
    assert [f + T.DL_MAX * s for f, s in T.DL_OFFS] == list(T.DL_SIZE[:2])
    import swreg
    assert T.SWE_CODE == swreg.REG_AT
    # the loader's careerTeam test (same page offset as careerTeam) can never take a record's offset 684 k for it, in any
    # language, with a page-aligned cache (B_SEL) or the game's (design 1.4's arithmetic is the Italian exe's: page offset
    # 0x256 is not a multiple of 4; the English one's, 0x10C, is - its first k is past the cache)
    for page, lang in T.CFB_PAGES.items():
        ctp = (page + T.CT_AT) & 0xFFF
        ks = [k for k in range(1024) if (T.TEAM * k - ctp) % 4096 == 0]
        assert not ks or ks[0] >= T.SEL_CAP, (lang, hex(ctp), ks)
        assert lang == 'en' or ctp % 4, (lang, hex(ctp))
    assert T.CT_OLD % 2 == 1, 'careerTeam - g_selectedTeams is odd'
    # careerFileBuffer's page offset per language, from the original exes (selTeamsPtr dd offset g_selectedTeams)
    exes = {'it': 'ITALIAN.EXE', 'en': 'ENGLISH.EXE', 'fr': 'FRENCH.EXE', 'de': 'GERMAN.EXE'}
    if not all(os.path.exists(os.path.join(ORIG, f)) for f in exes.values()):
        return True, 'constants ok (orig/ exes missing: page offsets not recomputed)'
    from le import LE
    pages = {}
    for lang, f in exes.items():
        le = LE(os.path.join(ORIG, f))
        L = T.exe_layout(le)
        assert le.obj(2).base & 0xFFF == 0
        pages[(L['old'] - T.FIXED) & 0xFFF] = lang
    assert pages == T.CFB_PAGES, pages
    return True, f'constants ok; careerFileBuffer page offsets {sorted(hex(k) for k in pages)}'


def synth(big, n=5, lang_page=0x6D6):
    """A synthetic save: league (4 clubs) in competitionFileBuffer, a cup (3 clubs, order 2 0 1) in slot 1, a type 2 with a
    knockout stage in slot 3 (one tie: list entries 5 and 9), slot 2 a refused buffer (type 7), slot 4 zeros (a league does
    not fit its room: refused); calendar: slots 0, 1, 3.
    -> (bytearray, selTeamsPtr, careerTeam's offset)"""
    cfb = 0x2C0000 + 0x9000 + lang_page
    sel = 0x452000 if big else cfb + T.FIXED
    ct = cfb + T.CT_AT - sel
    b = bytearray(T.FIXED + n * T.TEAM)
    struct.pack_into('<I', b, T.SELPTR_AT, sel)
    struct.pack_into('<H', b, T.NUMSEL_AT, n)
    if big:
        struct.pack_into('<I', b, T.BIGC_AT, T.BIGC)
    b[T.WORLD_AT], b[T.WORLD_AT + 1] = (5, 251) if big else (0, 0)
    o = T.SLOTS[0][1]                               # league: rows +691 + 18 i
    struct.pack_into('<H', b, o + T.DL_N, 4)
    for i, v in enumerate((0, ct, 2 * T.TEAM, 4 * T.TEAM)):
        struct.pack_into('<i', b, o + 691 + 18 * i, v)
    o = T.SLOTS[1][1]                               # cup: +0x343 + 4 x order
    struct.pack_into('<H', b, o, 1)
    struct.pack_into('<H', b, o + T.DL_N, 3)
    b[o + T.DL_ORDER:o + T.DL_ORDER + 3] = bytes((2, 0, 1))
    for i, v in enumerate((T.TEAM, ct, 3 * T.TEAM)):
        struct.pack_into('<i', b, o + 0x343 + 4 * i, v)
    o = T.SLOTS[2][1]                               # refused (type 7)
    struct.pack_into('<H', b, o, 7)
    o = T.SLOTS[3][1]                               # type 2, stage = a cup tie between list entries 5 and 9
    struct.pack_into('<H', b, o, 2)
    struct.pack_into('<H', b, o + T.DL_N, 16)
    s = o + T.DL_STAGE
    struct.pack_into('<H', b, s, 1)
    struct.pack_into('<H', b, s + T.DL_N, 2)
    b[s + T.DL_ORDER:s + T.DL_ORDER + 2] = bytes((5, 9))
    struct.pack_into('<i', b, s + 0x343 + 4 * 5, ct)
    struct.pack_into('<i', b, s + 0x343 + 4 * 9, T.TEAM)
    for k, slot in enumerate((0, 1, 3)):            # calendar entries: slot byte, week, size 22
        struct.pack_into('<BBH', b, T.CAL_AT + 22 * k, slot, 56 + k, 22)
    return b, sel, ct


def test_tc_synthetic():
    errs = []
    for big in (False, True):
        tag = 'big' if big else 'game'
        b, sel, ct = synth(big)
        r = T.audit(bytes(b))
        want = {'live record': 6, 'live careerTeam': 3}
        if (r['form'], r['ct'], r['counts'], r['other'], r['strays'], r['stale'], r['world'], r['lang']) != \
                ('big cache' if big else 'game cache', ct, want, [], [], [], 5 if big else 0, 'it'):
            errs.append(f"{tag} clean: {r['form']} ct {r['ct']} {r['counts']} other {r['other']} strays {r['strays']} stale {r['stale']} {r['lang']}")
        if [(s['state'], s['live']) for s in r['slots']] != [('league', True), ('cup', True), ('refused: type 7', False),
                                                             ('type2+cup', True),
                                                             ('refused: type 0 needs 0x733 > room 0x443', False)]:
            errs.append(f"{tag} slots: {r['slots']}")
        if not big and ct != T.CT_OLD:
            errs.append('game cache: careerTeam offset != -0x9831')
        # planted cases, one at a time: (what, file offset, dword, expected list, expected text)
        cfb = sel + ct - T.CT_AT
        lg, cup, st = T.SLOTS[0][1], T.SLOTS[1][1], T.SLOTS[3][1] + T.DL_STAGE
        tmd3 = cfb + T.TMD_AT + 3 * T.TEAM - sel            # an offset to a record of the 80-record area
        cases = [('league row = a tmd record', lg + 691 + 18 * 2, tmd3, 'other', 'fixed (tmd record)'),
                 ('league row = an object of the fixed part', lg + 691 + 18 * 2, cfb + 0xD750 - sel, 'other', 'fixed'),
                 ('cup entry = a record past N', cup + 0x343 + 4, 9 * T.TEAM, 'other', 'stale-rec'),
                 ('cup entry inside a record', cup + 0x343 + 4, 2 * T.TEAM + 76, 'other', 'in-cache'),
                 ('stage tie entry = garbage', st + 0x343 + 4 * 9, 0x7FFF0001, 'other', 'far'),
                 ('careerTeam past numTeams (league row 5)', lg + 691 + 18 * 5, ct, 'stale', "careerTeam's offset"),
                 ('careerTeam in the refused buffer', T.SLOTS[2][1] + 0x343 + 8, ct, 'stale', "careerTeam's offset"),
                 ('careerTeam at a stage entry outside the tie', st + 0x343 + 4 * 6, ct, 'stale', "careerTeam's offset"),
                 ('careerTeam in the offers area', 0xD82E, ct, 'strays', "careerTeam's offset"),
                 ('careerTeam inside a buffer, not an array place', cup + 0x100, ct, 'strays', "careerTeam's offset"),
                 ('careerTeam in a record', T.FIXED + T.TEAM + 100, ct, 'strays', "careerTeam's offset"),
                 ('address of record 2 in the tmd area', 0x2001, sel + 2 * T.TEAM, 'strays', 'absolute address of record 2'),
                 ('address of record 0 next to selTeamsPtr', T.SELPTR_AT - 5, sel, 'strays', 'absolute address of record 0')]
        if big:
            cases.append(('league row = a B_TMD record', lg + 691 + 18 * 2, 7 * T.TEAM - T.B_SEL, 'other', 'big-tmd'))
        for what, at, v, key, text in cases:
            c = bytearray(b)
            struct.pack_into('<I', c, at, v & 0xFFFFFFFF)
            r = T.audit(bytes(c))
            hits = {k: r[k] for k in ('other', 'strays', 'stale')}
            got = hits[key]
            if len(got) != 1 or got[0]['at'] != at or text != got[0].get('sub', got[0].get('kind')) \
                    or any(hits[k] for k in hits if k != key):
                errs.append(f'{tag} {what}: {hits}')
        # control: an address just outside a record start / a value that is no cache address is no stray
        c = bytearray(b)
        struct.pack_into('<I', c, 0x2001, sel + 2 * T.TEAM + 1)
        struct.pack_into('<I', c, 0x3001, sel - T.TEAM)
        r = T.audit(bytes(c))
        if r['strays'] or r['abs_in_range'] != 1:
            errs.append(f"{tag} control: {r['strays']} in range {r['abs_in_range']}")
        # a trailer: the stray is named by its block
        tr = struct.pack('<H', 0x3743) + bytes(946) + b'EN' + struct.pack('<H', 4 + 40 + 4 + 8) + b'GP' + struct.pack('<H', 40) + \
            bytes(40) + b'XS' + struct.pack('<H', 8) + struct.pack('<iI', ct, sel + T.TEAM)
        r = T.audit(bytes(b) + tr)
        w = sorted(x['where'] for x in r['strays'])
        if w != ["EN item 'XS' +0x4", "EN item 'XS' +0x8"] or r['trailer'] != ['main block C7', "EN item 'GP'", "EN item 'XS'"]:
            errs.append(f"{tag} trailer: {w} {r['trailer']}")
    # every language's page offset finds careerTeam in a big-cache save; another page offset does not
    for page, lang in T.CFB_PAGES.items():
        r = T.audit(bytes(synth(True, lang_page=page)[0]))
        if r['lang'] != lang or r['counts'].get('live careerTeam') != 3:
            errs.append(f"big cache {lang}: {r['lang']} {r['counts']}")
    r = T.audit(bytes(synth(True, lang_page=0x123)[0]))
    if r['ct'] is not None or r['counts'].get('live far') != 3:
        errs.append(f"big cache, unknown page offset: ct {r['ct']} {r['counts']}")
    # a league in a cup-sized slot (the national-team career's friendlies in slot 2): walked, named
    c, sel, ct = synth(False)
    o = T.SLOTS[2][1]
    struct.pack_into('<HH', c, o, 0, 0)
    struct.pack_into('<H', c, o + T.DL_N, 6)
    for i in range(6):
        struct.pack_into('<i', c, o + 691 + 18 * i, ct if i == 0 else i * T.TEAM)
    struct.pack_into('<BBH', c, T.CAL_AT + 22 * 3, 2, 60, 22)
    r = T.audit(bytes(c))
    if r['slots'][2]['state'] != 'league in a cup-sized slot' or not r['slots'][2]['live'] or r['strays'] or r['stale'] \
            or r['counts'] != {'live record': 10, 'live careerTeam': 4, 'live stale-rec': 1}:
        errs.append(f"league in slot 2: {r['slots'][2]} {r['counts']} {r['strays']} {r['stale']}")
    # the cross-save verdict on absolute addresses: a place that follows the cache under 3 addresses is a stray; the same
    # bytes under one address are a coincidence
    def res_of(saves):
        return {'saves': {str(k): dict(T.audit(bytes(x)), paths=[str(k)], copies=1) for k, x in enumerate(saves)}}
    follow, same = [], []
    for page in list(T.CFB_PAGES)[:3]:
        c, sel, ct = synth(False, lang_page=page)
        struct.pack_into('<I', c, 0x2001, sel + 2 * T.TEAM)
        follow.append(c)
        c, sel, ct = synth(False, lang_page=page)
        struct.pack_into('<I', c, 0x2001, 0x2C0000 + 0x9000 + 0x6D6 + T.FIXED + 2 * T.TEAM)     # (the IT address in all three)
        same.append(c)
    g1, g2 = T.grand(res_of(follow)), T.grand(res_of(same))
    if (g1['strays'], g1['coinc'], g2['strays'], g2['coinc']) != (3, 0, 0, 1):
        errs.append(f"verdict: follows {g1['strays']} / {g1['coinc']}, constant {g2['strays']} / {g2['coinc']}")
    assert not errs, '; '.join(errs)
    return True, '2 cache forms x 13-14 planted cases + controls + trailer + 4 languages + league in slot 2 + the cross-save verdict'


# real saves: (path under internal/, world, form, N, {class: count}, strays, stale careerTeam offsets)
REAL = [
    ('swostest/saves/JUVE2.CAR', 0, 'game cache', 47, {'live careerTeam': 3, 'live record': 51}, 0, 1),
    ('swostest/saves/W84E_TEAM254.CAR', 4, 'game cache', 95, {'live careerTeam': 3, 'live record': 115}, 0, 0),
    ('swostest/saves/W84E.CAR', 4, 'big cache', 95, {'live careerTeam': 3, 'live record': 115}, 0, 0),
    ('oldsaves/v3.3.6_W8485_LIVERPOOL_s1.CAR', 4, 'big cache', 94, {'live careerTeam': 3, 'live record': 115}, 0, 0),
    ('reports/enzo-dup-20261102/ENZO.CAR', 5, 'big cache', 72, {'live careerTeam': 4, 'live record': 87}, 0, 1),
    ('swostest/fixtures/cfbguard/ISCHIA02.CAR', 5, 'big cache', 48,
     {'live record': 51, 'live careerTeam': 2, 'idle careerTeam': 1, 'idle record': 1, 'live stale-rec': 2}, 0, 2),
]


def test_tc_saves_real():
    have = [x for x in REAL if os.path.exists(os.path.join(INTERNAL, x[0]))]
    if not have:
        return True, 'SKIP: no real saves (internal/)'
    errs = []
    for path, world, form, n, counts, strays, stale in have:
        r = T.audit(open(os.path.join(INTERNAL, path), 'rb').read())
        got = (r['world'], r['form'], r['n'], r['counts'], len(r['strays']), len(r['stale']))
        if got != (world, form, n, counts, strays, stale):
            errs.append(f'{path}: {got}')
        if any(x['sub'] in T.DEPENDENT for x in r['other']):
            errs.append(f'{path}: a cache-address dependent OTHER')
    assert not errs, '; '.join(errs)
    # the tool end to end on the same files: dedup by sha1, the totals
    res = T.run([os.path.join(INTERNAL, x[0]) for x in have] + [os.path.join(INTERNAL, have[0][0])])
    g = T.grand(res)
    assert len(res['saves']) == len(have) and sum(r['copies'] for r in res['saves'].values()) == len(have) + 1
    assert g['strays'] == 0 and g['dependent'] == 0, g
    text = T.report(res)
    assert '**Result: OTHER = ' in text and '| **all** |' in text
    return True, f'{len(have)}/{len(REAL)} real saves (worlds {sorted({x[1] for x in have})}), strays 0, dependent 0'
