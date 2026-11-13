"""4.2 S7 WSITES 4a (Panchina 13/11, n7-s7-clubmap.md §4a): the engine items' word / global rows (tools/wsites.py ROWS).

test_wsites_layout (no exe): every ROWS line recomputed from the structs - offsetof() of gplay.c's gp_state / gp_gs /
gp_ss / cd_state / wn_state / rs_state / pr_state and its SC_H / SC_NE, conti.h's ct_state / ct_ed, uesum.h's cup, in
a clang -target i686 probe (the exe's own layout, cobj.CFLAGS' target) - and the asm items' constants (xtra.XSOLD,
xleft.XLMAX): the same set of rows, no more, no less; each row inside its item's saved size (the
modules' *_SIZE = sizeof); no two rows share a byte; forms W / G only (O8 / K: their pieces).

test_wsites_walk (Unicorn, HT_WS_EXE else c/S7W-ws4a: a shaped IT build - the S7 test pack - with the real rows and
HOSTTEST_SYMS=1; recipe: buildrel's bfull.py with every test switch cleared, SEASON_PACKS = world5tm-h2's with ita ->
internal/s7pack-shaved/ita): the WSITES table in the exe = wsites.table() of the build's rows; every row's item resolves through
S7_ENI (the build's EN_ITEMS) and fits its length; then every site of every row is poked - W sites cycle a club going
down (102 -> 144), one going up (144 -> 102), a 102 club that stays, 0, FFFFh, another file's word; G sites the same
clubs' globals and another country's - and every other byte of those items a pattern; after the season's 9 swaps
(test_s7swap's crossings) each moved word / global is its club's new one, the rest of the sites and every other byte
unchanged; S7_WLOG: no bad row, rows walked = the table's, words changed = the moved ones planted; BT_EXT (MC 13/11):
SLTCOPY holds every row's new delta of both files - the split globals >= 2000 (BT_EXT's range) included - and no
other byte changed (someLeaguesTable is per row: re-based, never permuted)."""
import json
import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import wsites  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_WS_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-ws4a', 'SWOS', 'ITALIAN.EXE')

PROBE = r'''
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32; typedef signed char s8;
#define O(s, f) __builtin_offsetof(struct s, f)
#define Z(s, f) sizeof(((struct s *)0)->f)
'''


def _elf_sym(b, name):
    shoff, = struct.unpack_from('<I', b, 0x20)
    shentsize, shnum = struct.unpack_from('<HH', b, 0x2e)
    sh = [struct.unpack_from('<10I', b, shoff + i * shentsize) for i in range(shnum)]
    symtab = next(s for s in sh if s[1] == 2)
    strs = sh[symtab[6]]
    for i in range(symtab[5] // 16):
        n, v, sz, _, _, shn = struct.unpack_from('<IIIBBH', b, symtab[4] + 16 * i)
        e = b.index(b'\0', strs[4] + n)
        if b[strs[4] + n:e].decode() == name:
            return struct.unpack_from(f'<{sz // 4}I', b, sh[shn][4] + v)
    raise KeyError(name)


def probe(src, exprs):
    """{name: value} of C constant expressions after `src` (clang -target i686, as cobj compiles the exe's C)."""
    with tempfile.TemporaryDirectory() as d:
        c, o = os.path.join(d, 'p.c'), os.path.join(d, 'p.o')
        open(c, 'w').write(PROBE + src + '\nconst unsigned PROBE_V[] = {' + ', '.join(v for _, v in exprs) + '};\n')
        subprocess.run(['clang', '-target', 'i686-unknown-none-elf', '-march=i486', '-ffreestanding', '-fno-builtin',
                        '-w', '-I', TOOLS, '-c', c, '-o', o], check=True, capture_output=True)
        return dict(zip([k for k, _ in exprs], _elf_sym(open(o, 'rb').read(), 'PROBE_V')))


def expected_rows():
    """[(item, off, stride, count, form)] from the structs and the asm modules' constants."""
    W, G = wsites.WS_W, wsites.WS_G
    g = probe('#include "gplay.c"', [
        ('st', 'sizeof(struct gp_state)'), ('srow', 'O(gp_state, srow)'), ('srz', 'sizeof(struct gp_srow)'),
        ('srteam', 'O(gp_srow, team)'), ('SD', 'SD'), ('GT', 'GT'), ('ko', 'O(gp_state, ko)'),
        ('koz', 'sizeof(struct gp_ko)'), ('kot', 'O(gp_ko, team)'), ('KN', 'KN'), ('dec', 'O(gp_state, dec)'),
        ('decz', 'sizeof(struct gp_dec)'), ('dect', 'O(gp_dec, team)'), ('decg', 'O(gp_dec, glob)'),
        ('ndec', 'Z(gp_state, dec) / sizeof(struct gp_dec)'),
        ('gs', 'sizeof(struct gp_gs)'), ('gsrow', 'O(gp_gs, srow)'), ('GSD', 'GSD'), ('GSR', 'GSR'),
        ('ss', 'sizeof(struct gp_ss)'), ('ssr', 'O(gp_ss, r)'), ('rowz', 'sizeof(struct gp_row)'),
        ('rteam', 'O(gp_row, team)'), ('rglob', 'O(gp_row, glob)'), ('SS_N', 'SS_N'),
        ('cd', 'sizeof(struct cd_state)'), ('cdgen', 'O(cd_state, gen)'), ('ngen', 'Z(cd_state, gen) / 2'),
        ('wn', 'sizeof(struct wn_state)'), ('wne', 'O(wn_state, e)'), ('wnz', 'sizeof(struct wn_e)'),
        ('wnt', 'O(wn_e, team)'), ('WN_N', 'WN_N'),
        ('rs', 'sizeof(struct rs_state)'), ('rsq', 'O(rs_state, q)'), ('RQ', 'RQ'), ('RC', 'RC'),
        ('pr', 'sizeof(struct pr_state)'), ('prc', 'O(pr_state, c)'), ('prz', 'sizeof(struct pr_club)'),
        ('prg', 'O(pr_club, glob)'), ('PR_N', 'PR_N'),
        ('SC_H', 'SC_H'), ('SC_NE', 'SC_NE'), ('scz', 'sizeof(SC_ST)')])
    c = probe('#include "conti.h"\n#include "uesum.h"', [
        ('ct', 'sizeof(struct ct_state)'), ('hold', 'O(ct_state, hold)'), ('holdz', 'Z(ct_state, hold[0])'),
        ('NCUP', 'NCUP'), ('ed', 'sizeof(struct ct_ed)'), ('mgr', 'O(ct_ed, mgr)'), ('e', 'O(ct_ed, e)'),
        ('ez', 'Z(ct_ed, e[0])'), ('NED', 'NED'),
        ('us', 'sizeof(struct cup)'), ('t', 'O(cup, t)'), ('tz', 'sizeof(struct tie)'), ('tx', 'O(tie, x)'),
        ('ty', 'O(tie, y)'), ('NTIE', 'NTIE'), ('lw', 'O(cup, lw)'), ('NLP', 'NLP')])
    import conti
    import gplay
    import supercup
    import uesum
    import xleft
    import xtra
    sizes = {'GP': (g['st'], gplay.GP_ST_SIZE), 'GS': (g['gs'], gplay.GS_SIZE), 'SS': (g['ss'], gplay.SS_ITEM),
             'CD': (g['cd'], gplay.CD_SIZE), 'WN': (g['wn'], gplay.WN_SIZE), 'RS': (g['RC'] * g['rs'], gplay.RS_SIZE),
             'PR': (g['pr'], 4 + 48 * 8), 'SC': (g['scz'], supercup.SC_SIZE), 'CT': (c['ct'], conti.ST_SIZE),
             'CE': (c['ed'], conti.ED_SIZE), 'US': (c['us'], uesum.REC_SIZE),
             'XS': (2 + 3 * xtra.XSOLD, xtra.XS_SIZE),
             'XL': (5 + 3 * xleft.XLMAX, xleft.XL_SIZE)}
    sizes['SS2'] = sizes['SS']
    assert g['srteam'] == 0 and g['SC_NE'] == supercup.NE, (g['srteam'], g['SC_NE'])
    rows = [('GP', g['srow'], g['srz'], g['SD'] * g['GT'], W)]
    rows += [('GP', g['ko'] + k * g['koz'] + g['kot'], 2, g['KN'], W) for k in range(2)]
    rows += [('GP', g['dec'] + g[f] + 2 * j, g['decz'], g['ndec'], form) for f, form in (('dect', W), ('decg', G))
             for j in range(2)]
    rows += [('GS', g['gsrow'], g['srz'], g['GSD'] * g['GSR'], W)]
    for it in ('SS', 'SS2'):
        rows += [(it, g['ssr'] + g[f], g['rowz'], g['SS_N'] * g['GT'], form) for f, form in (('rteam', W), ('rglob', G))]
    rows += [('CD', g['cdgen'], 2, g['ngen'], W), ('WN', g['wne'] + g['wnt'], g['wnz'], g['WN_N'], W)]
    rows += [('RS', g['rs'] * k + g['rsq'], 2, g['RQ'], G) for k in range(g['RC'])]
    rows += [('PR', g['prc'] + g['prg'], g['prz'], g['PR_N'], G)]
    n = g['SC_NE'] - 1                   # (the cups below the UEFA entry: {db file, cid, 0, 0; dw w, wg, f, fg})
    rows += [('SC', g['SC_H'] + o, 12, n, form) for o, form in ((4, W), (6, G), (8, W), (10, G))]
    rows += [('SC', g['SC_H'] + 12 * n + 4, 2, 4, W)]
    rows += [('CT', c['hold'], c['holdz'], c['NCUP'], W), ('CE', c['mgr'], 0, 1, W), ('CE', c['e'], c['ez'], c['NED'], W)]
    rows += [('US', c['t'] + c[f], c['tz'], c['NTIE'], W) for f in ('tx', 'ty')] + [('US', c['lw'], 2, c['NLP'], W)]
    rows += [('XS', 2, 3, xtra.XSOLD, W), ('XL', 5, 3, xleft.XLMAX, W)]   # (BU: HOME words, not walked)
    return rows, sizes


def test_wsites_layout():
    rows, sizes = expected_rows()
    errs = []
    for it, (a, b) in sizes.items():
        if a != b:
            errs.append(f'{it}: sizeof {a} != the saved size {b}')
    got = [(r[0], r[1], r[2], r[3], r[4]) for r in wsites.ROWS]
    if sorted(got) != sorted(rows):
        errs.append(f'ROWS not in the structs: {sorted(set(got) - set(rows))[:4]}; missing {sorted(set(rows) - set(got))[:4]}')
    used = {}
    for it, off, st, cnt, form, aux in wsites.ROWS:
        if form not in (wsites.WS_W, wsites.WS_G) or aux:
            errs.append(f'{it}+{off}: form {form} aux {aux} (W / G only)')
        if off + max(cnt - 1, 0) * st + 2 > sizes[it][1]:
            errs.append(f'{it}+{off}: past its item ({sizes[it][1]} B)')
        for k in range(cnt):
            for b in (off + k * st, off + k * st + 1):
                if (it, b) in used:
                    errs.append(f'{it}+{b}: in two rows ({used[it, b]}, {off})')
                used[it, b] = off
    return not errs, '; '.join(errs[:6]) or f'{len(rows)} rows = the structs\' sites ({len(sizes)} items, sizes = sizeof)'


def test_wsites_walk():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    import engine
    import test_s7swap as t7
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'S7_ENI' not in sy.get('s7swap', {}):
        return False, f'{EXE}: no S7_ENI in the syms'
    m = t7.M(EXE)
    errs = []
    m.fresh()
    fs, word, at, rdiv, rows_ = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    gb = m.gb

    def glob(f, o):
        return t7.glob_of(gb[0 if f == t7.FA else 1], o)
    ws = m.at('s7swap', 'WSITES')
    raw = m.rd(ws, 10 * wsites.WS_MAX)
    tab = []
    for k in range(wsites.WS_MAX):
        r = struct.unpack_from('<4H2B', raw, 10 * k)
        if r[0] == wsites.WS_END:
            break
        tab.append(r)
    ids = {engine.item_id(n): n for n in {r[0] for r in wsites.ROWS}}
    enn = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_ENN'), 4))[0]
    eni = struct.unpack(f'<{3 * enn}I', m.rd(m.at('s7swap', 'S7_ENI'), 12 * enn))
    item = {eni[3 * e + 2] & 0xFFFF: (eni[3 * e], eni[3 * e + 1]) for e in range(enn)}
    want = [r for r in wsites.ROWS if engine.item_id(r[0]) in item]    # (rows(): the build's own items, = EN_ITEMS)
    absent = sorted({r[0] for r in wsites.ROWS} - {r[0] for r in want})
    if raw != wsites.table(want):
        errs.append(f'WSITES in the exe ({len(tab)} rows) != wsites.table of ROWS on its EN items ({len(want)})')
    dn = [e[1] for e in down]
    upw = [e[1] for e in up]
    stay = t7.FA | 10 << 8
    wv = [dn[0], upw[0], stay, 0, 0xFFFF, 103 | 4 << 8, dn[1], upw[1]]
    gv = [glob(t7.FA, dn[0] >> 8), glob(t7.FB, upw[0] >> 8), glob(t7.FA, 10), 7, glob(t7.FA, dn[2] >> 8)]
    before, sites = {}, {}
    for k, (iid, off, st, cnt, form, aux) in enumerate(tab):
        if iid not in item:
            errs.append(f'row {k}: item {ids.get(iid, iid)} not in S7_ENI')
            continue
        ptr, ln = item[iid]
        if off + max(cnt - 1, 0) * st + 2 > ln:
            errs.append(f'row {k}: {ids.get(iid)}+{off} past its {ln} B')
        if iid not in before:
            before[iid] = bytearray((j * 7 + 0x31) & 0xFF for j in range(ln))
        vals = wv if form == wsites.WS_W else gv
        for i in range(cnt):
            v = vals[(i + k) % len(vals)]
            struct.pack_into('<H', before[iid], off + i * st, v)
            sites[iid, off + i * st] = (form, v)
    if errs:
        return False, '; '.join(errs[:6])
    for iid, b in before.items():
        m.w(item[iid][0], bytes(b))
    stt, nsw, ncr, slt = t7.run(m, down, up)
    if stt != t7.OK:
        return False, f'season status {stt}'
    fs1, word1, _, _, _ = t7.reg_parse(m.regb())
    ident = {w: i for i, w in enumerate(word)}
    nw = lambda w: word1[ident[w]] if w in ident else w   # noqa: E731

    def nglob(g):
        for f in (t7.FA, t7.FB):
            for o in range(rows_[[x[0] for x in fs].index(f)]):
                if glob(f, o) == g:
                    w2 = nw(f | o << 8)
                    return glob(w2 & 0xFF, w2 >> 8)
        return g
    moved = 0
    for iid, b in before.items():
        exp = bytearray(b)
        for (j, off), (form, v) in sites.items():
            if j != iid:
                continue
            v2 = (nw(v) if v not in (0, 0xFFFF) else v) if form == wsites.WS_W else nglob(v)
            moved += v2 != v
            struct.pack_into('<H', exp, off, v2)
        got = m.rd(item[iid][0], len(b))
        if got != bytes(exp):
            bad = [o for o in range(len(b)) if got[o] != exp[o]]
            errs.append(f'{ids.get(iid)}: differs at +{bad[:6]} (got {got[bad[0]:bad[0] + 2].hex()} want '
                        f'{exp[bad[0]:bad[0] + 2].hex()})')
    # BT_EXT (MC 13/11): someLeaguesTable bytes 2000+ are indexed by global = by ROW, not by club - no permutation;
    # s7_season's re-base writes every row's delta of both files in SLTCOPY (leaguesTableCopy), file 144's split
    # globals (2283.., BT_EXT's range) included, and InitializeNewSeason's copy (cseg_8CC4E, its loop widened to
    # LIMIT by bigtables.py) puts them into someLeaguesTable: every row's delta = its new division - its base, every
    # other byte of SLTCOPY untouched
    _, _, _, rdiv1, rows1 = t7.reg_parse(m.regb())
    mine, hi = set(), 0
    for fi, f in enumerate(fs1):
        for o in range(rows1[fi]):
            b = t7.base_local(f, o)
            if b < 0:
                continue
            g = t7.glob_of(gb[fi], o)
            mine.add(g)
            hi += g >= 2000
            d = struct.unpack('b', slt[g:g + 1])[0]
            if d != f[1].index(rdiv1[fi][o]) - b:
                errs.append(f'SLTCOPY file {f[0]} row {o} (global {g}): delta {d} != {f[1].index(rdiv1[fi][o]) - b}')
    if any(slt[g] for g in range(len(slt)) if g not in mine):
        errs.append('SLTCOPY: a byte outside the two files\' rows changed')
    if not hi:
        errs.append('no row global >= 2000 in this build (BT_EXT range not exercised)')
    wl = struct.unpack('<hhHHHH', m.rd(m.at('s7swap', 'S7_WLOG'), 12))
    if wl[0] != -1 or wl[5] != len(tab) or wl[2] != moved:      # (row, rc, changed, cache, npair, rows)
        errs.append(f'S7_WLOG {wl} (row -1, rows {len(tab)}, changed {moved})')
    if not moved:
        errs.append('no site moved (crossings?)')
    return not errs, '; '.join(errs[:6]) or (f'{len(tab)} rows on {len(before)} items: {moved} moved words / globals '
                                             f'now their clubs\' new ones, the other sites and bytes unchanged; SLTCOPY re-based for every row '
                                             f'({hi} globals >= 2000: BT_EXT\'s range) (items not saved by this build: {absent})')
