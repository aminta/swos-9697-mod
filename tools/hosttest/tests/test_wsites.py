"""4.2 S7 WSITES 4a (Panchina 13/11, n7-s7-clubmap.md §4a): the engine items' word / global rows (tools/wsites.py ROWS).

test_wsites_layout (no exe): every ROWS line recomputed from the structs - offsetof() of gplay.c's gp_state / gp_gs /
gp_ss / cd_state / wn_state / rs_state / pr_state and its SC_H / SC_NE, conti.h's ct_state / ct_ed, uesum.h's cup, in
a clang -target i686 probe (the exe's own layout, cobj.CFLAGS' target) - and the asm items' constants (xtra.XSOLD,
xleft.XLMAX): the same set of rows, no more, no less; each row inside its item's saved size (the
modules' *_SIZE = sizeof); no two rows share a byte; forms W / G only (O8 / K: their pieces).

test_wsites_walk (Unicorn, HT_WS_EXE else c/S7W-ws4c: a shaped IT build - the S7 test pack - with the real rows and
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
import re
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
import wsites  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_WS_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-ws4c', 'SWOS', 'ITALIAN.EXE')

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
        ('cdent', 'O(cd_state, ent)'), ('nent', 'Z(cd_state, ent)'),
        ('wn', 'sizeof(struct wn_state)'), ('wne', 'O(wn_state, e)'), ('wnz', 'sizeof(struct wn_e)'),
        ('wnt', 'O(wn_e, team)'), ('WN_N', 'WN_N'),
        ('rs', 'sizeof(struct rs_state)'), ('rsq', 'O(rs_state, q)'), ('RQ', 'RQ'), ('RC', 'RC'),
        ('pr', 'sizeof(struct pr_state)'), ('prc', 'O(pr_state, c)'), ('prz', 'sizeof(struct pr_club)'),
        ('prg', 'O(pr_club, glob)'), ('PR_N', 'PR_N'),
        ('SC_H', 'SC_H'), ('SC_NE', 'SC_NE'), ('scz', 'sizeof(SC_ST)'),
        ('cfz', 'sizeof(struct cf_state)'), ('cfrank', 'O(cf_state, rank)'), ('cffile', 'O(cf_state, file)'),
        ('cfn', 'Z(cf_state, rank)'), ('cnz', 'sizeof(struct cn_state)'), ('cnpad', 'O(cn_state, pad)')])
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
    sizes['CF'], sizes['CN'] = (g['cfz'], gplay.CF_SIZE), (g['cnz'], gplay.CN_SIZE)
    assert g['srteam'] == 0 and g['SC_NE'] == supercup.NE, (g['srteam'], g['SC_NE'])
    rows = [('GP', g['srow'], g['srz'], g['SD'] * g['GT'], W)]
    rows += [('GP', g['ko'] + k * g['koz'] + g['kot'], 2, g['KN'], W) for k in range(2)]
    rows += [('GP', g['dec'] + g[f] + 2 * j, g['decz'], g['ndec'], form) for f, form in (('dect', W), ('decg', G))
             for j in range(2)]
    rows += [('GS', g['gsrow'], g['srz'], g['GSD'] * g['GSR'], W)]
    for it in ('SS', 'SS2'):
        rows += [(it, g['ssr'] + g[f], g['rowz'], g['SS_N'] * g['GT'], form) for f, form in (('rteam', W), ('rglob', G))]
    rows += [('CD', g['cdgen'], 2, g['ngen'], W), ('CD', g['cdent'], wsites.CD_FILL, g['nent'], wsites.WS_R), ('WN', g['wne'] + g['wnz'] + g['wnt'], g['wnz'], g['WN_N'] - 1, W)]
    rows += [('RS', g['rs'] * k + g['rsq'], 2, g['RQ'], G) for k in range(g['RC'])]
    rows += [('PR', g['prc'] + g['prg'], g['prz'], g['PR_N'], G)]
    n = g['SC_NE'] - 1                   # (the cups below the UEFA entry: {db file, cid, 0, 0; dw w, wg, f, fg})
    rows += [('SC', g['SC_H'] + o, 12, n, form) for o, form in ((4, W), (6, G), (8, W), (10, G))]
    rows += [('SC', g['SC_H'] + 12 * n + 4, 2, 4, W)]
    rows += [('CT', c['hold'], c['holdz'], c['NCUP'], W), ('CE', c['mgr'], 0, 1, W), ('CE', c['e'], c['ez'], c['NED'], W)]
    rows += [('US', c['t'] + c[f], c['tz'], c['NTIE'], W) for f in ('tx', 'ty')] + [('US', c['lw'], 2, c['NLP'], W)]
    rows += [('CF', g['cfrank'], 0, g['cfn'], wsites.WS_R), ('CN', g['cnpad'], 2, 1, W)]
    rows += [('XS', 2, 3, xtra.XSOLD, W), ('XL', 5, 3, xleft.XLMAX, W)]   # (BU: HOME words, not walked)
    return rows, sizes


def test_wsites_layout():
    rows, sizes = expected_rows()
    cffile = probe('#include "gplay.c"', [('f', 'O(cf_state, file)')])['f']
    errs = []
    for it, (a, b) in sizes.items():
        if a != b:
            errs.append(f'{it}: sizeof {a} != the saved size {b}')
    got = [(r[0], r[1], r[2], r[3], r[4]) for r in wsites.ROWS if isinstance(r[0], str)]   # (engine items; 4b: test_wsites_cfb)
    if sorted(got) != sorted(rows):
        errs.append(f'ROWS not in the structs: {sorted(set(got) - set(rows))[:4]}; missing {sorted(set(rows) - set(got))[:4]}')
    used = {}
    for it, off, st, cnt, form, aux in [r for r in wsites.ROWS if isinstance(r[0], str)]:
        R = form == wsites.WS_R
        if form not in (wsites.WS_W, wsites.WS_G, wsites.WS_R) or aux != ({'CF': cffile, 'CD': 0}.get(it, -1) if R else 0):
            errs.append(f'{it}+{off}: form {form} aux {aux} (W / G; R on CF with its file byte at +{cffile}, on CD with '
                        f'the file literal)')
        if off + (cnt if R else max(cnt - 1, 0) * st + 2) > sizes[it][1]:
            errs.append(f'{it}+{off}: past its item ({sizes[it][1]} B)')
        for k in range(cnt):
            for b in ((off + k,) if R else (off + k * st, off + k * st + 1)):
                if (it, b) in used:
                    errs.append(f'{it}+{b}: in two rows ({used[it, b]}, {off})')
                used[it, b] = off
    return not errs, '; '.join(errs[:6]) or f'{len(rows)} rows = the structs\' sites ({len(sizes)} items, sizes = sizeof)'


def test_wsites_walk(shift=False):
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
    ids = {engine.item_id(n): n for n in {r[0] for r in wsites.ROWS if isinstance(r[0], str)}}
    enn = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_ENN'), 4))[0]
    eni = struct.unpack(f'<{3 * enn}I', m.rd(m.at('s7swap', 'S7_ENI'), 12 * enn))
    item = {eni[3 * e + 2] & 0xFFFF: (eni[3 * e], eni[3 * e + 1]) for e in range(enn)}
    cfblen = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_CFBLEN'), 4))[0]
    item[wsites.WI_CFB] = (m.at('s7swap', 'S7_CFB'), cfblen)
    item[wsites.WI_CFBH] = (m.at('s7swap', 'S7_CFB') + 0x10000, cfblen - 0x10000)
    ids[wsites.WI_CFB], ids[wsites.WI_CFBH] = 'CFB', 'CFBH'
    if 'CD_TAB' in sy.get('gplay', {}):                 # (CD ent's literal file: the exe's Serie D file, CD_TAB[2])
        wsites.CD_FILE[0] = m.rd(m.at('gplay', 'CD_TAB') + 2, 1)[0]
    want = wsites.resolve([r for r in wsites.ROWS if (r[0] if isinstance(r[0], int) else engine.item_id(r[0])) in item])    # (rows(): the build's own items, = EN_ITEMS)
    absent = sorted({r[0] for r in wsites.ROWS if isinstance(r[0], str)} - {r[0] for r in want})
    if raw != wsites.table(want):
        errs.append(f'WSITES in the exe ({len(tab)} rows) != wsites.table of ROWS on its EN items ({len(want)})')
    if shift:                                           # CONTROL (MC 13/11): ONE row (uefaq br's a, CFB stride 6) 2 bytes early in the
        k6 = next((k for k, r in enumerate(tab) if r[0] == wsites.WI_CFB and r[2] == 6 and r[3] == 320 and r[4] == wsites.WS_W), None)
        if k6 is None:                                  # exe's table only: the decoys / expected bytes stay as for the right rows,
            return False, 'control: no br row'          # so the walker sees the decoy bytes as the word
        m.w(ws + 10 * k6 + 2, struct.pack('<H', tab[k6][1] - 2))
    dn = [e[1] for e in down]
    upw = [e[1] for e in up]
    stay = t7.FA | 10 << 8
    wv = [dn[0], upw[0], stay, 0, 0xFFFF, 103 | 4 << 8, dn[1], upw[1]]
    gv = [glob(t7.FA, dn[0] >> 8), glob(t7.FB, upw[0] >> 8), glob(t7.FA, 10), 7, glob(t7.FA, dn[2] >> 8)]
    before, sites, rrows = {}, {}, []
    dslot = dstale = 0
    for k, (iid, off, st, cnt, form, aux) in enumerate(tab):
        if iid not in item:
            errs.append(f'row {k}: item {ids.get(iid, iid)} not in S7_ENI')
            continue
        ptr, ln = item[iid]
        if off + (cnt if form == wsites.WS_R else st if form == wsites.WS_D else max(cnt - 1, 0) * st + 2) > ln:
            errs.append(f'row {k}: {ids.get(iid)}+{off} past its {ln} B')
        if iid == wsites.WI_CFBH:                       # (one buffer with CFB: the same bytes from +0x10000)
            iid, off = wsites.WI_CFB, off + 0x10000
        if iid not in before:
            before[iid] = bytearray((j * 7 + 0x31) & 0xFF for j in range(item[iid][1]))
        if form == wsites.WS_R:                          # (a place per ordinal, all 2+ (cd_season's places: an up-crosser's
            for i in range(cnt):                         # old row must become the fill, MC 13/11); the file byte = 102,
                before[iid][off + i] = 2 + i % 30        # or the row's literal file: stride = fill | file << 8)
            if not st >> 8:
                before[iid][aux] = t7.FA
            rrows.append((iid, off, cnt, aux, st))
            continue
        if form == wsites.WS_D:                          # (a DIY contest per slot, MC 15/11: league / cup / type 2 with a
            t, n, stg = (1, 17, None) if st == 0x443 else [(0, 20, None), (2, 36, (1, 2)), (2, 36, (0, 36))][dslot % 3]
            dslot += 1                                   #  cup or a league stage; the other types' list areas and the
            for ca, tt, nn in [(off, t, n)] + ([(off + 0x41F, stg[0], stg[1])] if stg else []):   # stale tail: decoys
                struct.pack_into('<HH', before[iid], ca, tt, 0)
                struct.pack_into('<H', before[iid], ca + 49, nn)
                lo = DIY_LIST[tt]
                for i in range(64):
                    v = wv[(i + k) % len(wv)]
                    struct.pack_into('<H', before[iid], ca + lo + 2 * i, v if i < nn else dn[0])
                    if i < nn:
                        sites[iid, ca + lo + 2 * i] = (wsites.WS_W, v)
                for t2, lo2 in DIY_LIST.items():         # (another type's list area: a crosser's word, untouched)
                    if t2 != tt and lo2 + 2 <= (0x41F if ca == off and t == 2 else DIY_SIZE[tt]) and \
                            not any(lo2 <= x - ca < lo2 + 2 for x in [o for (j, o) in sites if j == iid]):
                        struct.pack_into('<H', before[iid], ca + lo2, dn[0])
                        dstale += 1
            continue
        vals = wv if form == wsites.WS_W else gv
        for i in range(cnt):
            v = vals[(i + k) % len(vals)]
            struct.pack_into('<H', before[iid], off + i * st, v)
            sites[iid, off + i * st] = (form, v)
    # DECOYS (MC 13/11): in every record of a strided row (stride >= 4) the two bytes before its word field, when no row
    # covers them (uefaq br's r / aw, the calendar's entry word, ...), hold the going-down crosser's word: a non-team
    # value equal to a crosser's word must come out untouched (the expected bytes keep it as planted)
    cov = {(i, o + d) for (i, o) in sites for d in (0, 1)}
    cov |= {(r[0], r[1] + k) for r in rrows for k in range(r[2])}
    cov |= {(r[0], r[3]) for r in rrows if not r[4] >> 8}
    decoys = 0
    for iid, off, st, cnt, form, aux in tab:
        if form == wsites.WS_R or st < 4 or cnt < 2:
            continue
        if iid == wsites.WI_CFBH:
            iid, off = wsites.WI_CFB, off + 0x10000
        for i in range(cnt):
            o = off + i * st - 2
            if o >= 0 and (iid, o) not in cov and (iid, o + 1) not in cov:
                struct.pack_into('<H', before[iid], o, dn[0])
                cov |= {(iid, o), (iid, o + 1)}
                decoys += 1
    if not decoys:
        errs.append('no decoy planted (a strided row with a free word before its field)')
    if errs:
        return False, '; '.join(errs[:6])
    for iid, b in before.items():
        m.w(item[iid][0], bytes(b))
    stt, nsw, ncr, slt = t7.run(m, down, up)
    if stt != t7.OK:
        return False, f'season status {stt}'
    fs1, word1, at1, _, _ = t7.reg_parse(m.regb())
    ident = {w: i for i, w in enumerate(word)}
    nw = lambda w: word1[ident[w]] if w in ident else w   # noqa: E731

    def nglob(g):
        for f in (t7.FA, t7.FB):
            for o in range(rows_[[x[0] for x in fs].index(f)]):
                if glob(f, o) == g:
                    w2 = nw(f | o << 8)
                    return glob(w2 & 0xFF, w2 >> 8)
        return g
    moved = cleared = 0
    rfill = {}
    for iid, b in before.items():
        exp = bytearray(b)
        for (j, off), (form, v) in sites.items():
            if j != iid:
                continue
            v2 = (nw(v) if v not in (0, 0xFFFF) else v) if form == wsites.WS_W else nglob(v)
            moved += v2 != v
            struct.pack_into('<H', exp, off, v2)
        for r_iid, roff, rcnt, raux, rst in rrows:
            if r_iid != iid:
                continue
            fl = [x[0] for x in fs]
            rf = rst >> 8 or b[raux]
            if rf not in fl:
                errs.append(f'{ids.get(iid)}+{roff}: WS_R file {rf} not one of the registry\'s {fl}')
                continue
            fi = fl.index(rf)
            for k in range(min(rcnt, len(at[fi]))):
                if at[fi][k] != at1[fi][k]:               # (the row's club changed: the fill; the rest as planted)
                    exp[roff + k] = rst & 0xFF
                    cleared += 1
                    rfill[rst & 0xFF] = rfill.get(rst & 0xFF, 0) + 1
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
    if wl[0] != -1 or wl[5] != len(tab) or wl[2] != moved + cleared:      # (row, rc, changed, cache, npair, rows)
        errs.append(f'S7_WLOG {wl} (row -1, rows {len(tab)}, changed {moved} + cleared {cleared})')
    if rrows and not cleared:
        errs.append('WS_R: no row changed its club (crossings?)')
    cdr = [r for r in rrows if r[4] >> 8]               # (CD ent: literal file, fill 1 - MC 13/11: every changed row of the
    if cdr and not rfill.get(wsites.CD_FILL):           #  Serie D file -> 1, an up-crosser's 2+ place included)
        errs.append(f'CD ent: no changed row of file {cdr[0][4] >> 8} set to {wsites.CD_FILL} (fills {rfill})')
    if not moved:
        errs.append('no site moved (crossings?)')
    return not errs, '; '.join(errs[:6]) or (f'{len(tab)} rows on {len(before)} items ({dslot} DIY slots, {dstale} decoys in other types\' list areas + stale tails kept): {moved} moved words / globals '
                                             f'now their clubs\' new ones, the other sites and bytes unchanged ({decoys} decoys: a crosser\'s word in a non-team field, untouched); SLTCOPY re-based for every row '
                                             f'({hi} globals >= 2000: BT_EXT\'s range); WS_R fills {rfill} (CD ent: changed rows of its '
                                             f'file -> 1 over planted 2+ places, the rest kept) (items not saved by this build: {absent})')


def test_wsites_walk_control():
    """MC's control for the decoys: the walk with ONE row shifted 2 bytes early (in the exe's table only) must FAIL - the
    walker then remaps the decoys planted in br's r / aw bytes (and leaves the real a words): the test sees a mis-placed row."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    ok, msg = test_wsites_walk(shift=True)
    if ok:
        return False, 'a row shifted 2 bytes was NOT caught by the walk test'
    if 'differs' not in msg and 'S7_WLOG' not in msg:
        return False, f'the shifted row failed for another reason: {msg[:160]}'
    return True, f'a row 2 bytes early is caught ({msg[:90]})'


# ---- 4b: careerFileBuffer rows against real saves (completeness) ----------------------------------------------------
MAINDIR = os.path.join(HOME, 'swos-mod', 'internal', 'swostest')
CFB_SAVES = [os.path.join(MAINDIR, f) for f in ('s1mid_inter.CAR', 'davide_int.CAR', 'guests_end_squads.CAR')] + \
    [os.path.join(MAINDIR, 'n7', 'saves', f'c20_after_s{n:02d}.CAR') for n in range(2, 20)]
FIX_LEN = 95151                                   # careerFileBuffer's fixed part (trailer INFO FIXED)


DIY_LIST, DIY_SIZE = {0: 301, 1: 589, 2: 153}, {0: 0x733, 1: 0x443, 2: 0xB52}


def diy_lists(c, room):
    """[(offset, count)] a DIY contest's live team list(s) (sreg_walk.c WS_D's rule), [] when WS_D would refuse it"""
    def one(b, rm, maxt):
        t, n = struct.unpack_from('<H', b, 0)[0], struct.unpack_from('<H', b, 49)[0]
        return (t, DIY_LIST[t], n) if t <= maxt and DIY_SIZE[t] <= rm and n <= 64 else None
    a = one(c, room, 2)
    if not a:
        return []
    if a[0] != 2:
        return [a[1:]]
    b = one(c[0x41F:], 0xB52 - 0x41F, 1)
    return [a[1:], (0x41F + b[1], b[2])] if b else []


def _cfb_covered(rows, d=None):
    cov = set()
    for it, off, st, cnt, form, aux in rows:
        if it in (wsites.WI_CFB, wsites.WI_CFBH) and form == wsites.WS_D and d is not None:
            base = (0x10000 if it == wsites.WI_CFBH else 0) + off
            for lo, n in diy_lists(d[base:base + st], st):
                for k in range(n):
                    cov.update((base + lo + 2 * k, base + lo + 2 * k + 1))
        if it in (wsites.WI_CFB, wsites.WI_CFBH) and form == wsites.WS_W:
            base = 0x10000 if it == wsites.WI_CFBH else 0
            for k in range(cnt):
                cov.update((base + off + k * st, base + off + k * st + 1))
    return cov


def _stale(d, cov):
    """file-102 words (low byte 66h, ordinal < 157) of the fixed part outside every CFB row, clustered (>2 within 64 B:
    an isolated hit is noise level, 1 in 256 x 157 / 256 per byte pair)"""
    loose = [o for o in range(FIX_LEN - 1) if d[o] == 0x66 and d[o + 1] < 0x9D and o not in cov]
    return [o for o in loose if sum(abs(o - p) <= 64 for p in loose) > 2]


def test_wsites_cfb():
    """every file-102 word of the career block of every real 4.1 save (26: season 1, 2+, c20 seasons 2..19) lies in a
    WI_CFB row (the rows' bytes: wsites.ROWS), clustered hits only (noise level ignored); each row pulled out is caught on a
    save that uses it (no row is dead weight); every row inside the fixed part."""
    saves = [p for p in CFB_SAVES if os.path.exists(p)]
    if not saves:
        return True, 'SKIP: no real 4.1 saves (internal/swostest)'
    rows = [r for r in wsites.ROWS if r[0] in (wsites.WI_CFB, wsites.WI_CFBH)]
    errs = []
    data = {p: open(p, 'rb').read() for p in saves}
    cov = _cfb_covered(rows)
    if cov and max(cov) >= FIX_LEN:
        errs.append(f'a row past the fixed part ({max(cov)})')
    rooms = set()                                    # (WS_D buffers: words past numTeams / in another type's list area
    for it, off, st, cnt, form, aux in rows:         #  are stale by the layout - nothing reads them - counted, not walked)
        if form == wsites.WS_D:
            b0 = (0x10000 if it == wsites.WI_CFBH else 0) + off
            rooms.update(range(b0, b0 + st))
    stale = 0
    for p, d in data.items():
        bad = _stale(d, _cfb_covered(rows, d))
        stale += sum(o in rooms for o in bad)
        bad = [o for o in bad if o not in rooms]
        if bad:
            errs.append(f'{os.path.basename(p)}: {len(bad)} file-102 words outside the rows: {[hex(o) for o in bad[:6]]}')
    dead = []
    code = set(cfb_code_rows()[0])                  # (4c: rows from the code need no save to prove them)
    for r in [x for x in rows if x not in code]:
        if not any([o for o in _stale(d, _cfb_covered([x for x in rows if x is not r], d)) if o not in rooms]
                   for d in data.values()):
            dead.append(hex(r[1] + (0x10000 if r[0] == wsites.WI_CFBH else 0)))
    if dead:
        errs.append(f'rows no save needs (nothing clustered without them): {dead}')
    return not errs, '; '.join(errs[:5]) or (f'{len(saves)} real saves: every clustered file-102 word is in one of {len(rows)} CFB rows, each row needed '
                                         f'({stale} stale words in DIY buffers outside their live lists: not walked, by the layout)')



# ---- 4c: careerFileBuffer rows from the code (MC's code pass 13/11) ------------------------------------------------
LISTING = os.path.join(HOME, 'swos-mod', 'ref', 'swos.asm')


def cfb_code_rows():
    """([(item, off, stride, count, form, aux)] the CFB rows whose extent the code gives, [errors]): the mod's structs in
    tmdFileBuffer's 80-record area (uefacoef.py's block at NG = bigtables.LIMIT, uefaq.c's uq_state, dplay.c's dp_save and
    its log) from offsetof / the modules' constants, the game's arrays from ref/swos.asm (their declarations and the
    writers' bounds)."""
    import bigtables
    import dplay
    import uefacoef as uc
    W, G, C, H = wsites.WS_W, wsites.WS_G, wsites.WI_CFB, wsites.WI_CFBH
    errs = []
    on = bigtables.ON[0]
    bigtables.ON[0] = True                       # (the S7 world numbers clubs 2000+: NG = LIMIT)
    try:
        uc.layout()
        prev, size, cb = uc.PREV, uc.SIZE, uc.CB_OFF
    finally:
        bigtables.ON[0] = on
        uc.layout()
    q = probe('#include "uefaq.c"', [('st', 'sizeof(struct uq_state)'), ('m', 'O(uq_state, m)'), ('s', 'O(uq_state, s)'),
                                     ('gl', 'O(uq_state, gl)'), ('gln', 'Z(uq_state, gl) / 2'), ('br', 'O(uq_state, br)'),
                                     ('brz', 'Z(uq_state, br[0])'), ('bra', 'O(uq_state, br[0].a)'),
                                     ('brb', 'O(uq_state, br[0].b)'), ('NBR', 'NBR')])
    d = probe('#include "dplay.c"', [('sv', 'sizeof(struct dp_save)'), ('res', 'O(dp_save, res)'),
                                     ('team', 'O(dp_save, team)'), ('SN', 'SN'), ('srow', 'O(dp_save, srow)'),
                                     ('srz', 'sizeof(struct dp_srow)'), ('srt', 'O(dp_srow, team)'), ('SR', 'SR'),
                                     ('mv', 'O(dp_out, mv)'), ('mvz', 'sizeof(struct dp_mv)'), ('nmv', 'Z(dp_out, mv) / sizeof(struct dp_mv)'),
                                     ('mvg', 'O(dp_mv, glob)'), ('mvt', 'O(dp_mv, team)')])
    tmd = wsites.TMD
    if q['m'] + 2 != q['s'] or q['bra'] != q['br'] + 2 or q['brb'] != q['br'] + 4:
        errs.append('uq_state: m, s not adjacent or br[] not {r, aw, a, b}')
    st_end = cb + size + q['st']
    save_at = dplay.SAVE_AT if st_end <= dplay.SAVE_AT else (st_end + 15) & ~15     # (dplay.patch's rule)
    sv = tmd + save_at
    log = sv + dplay.LOG_AT + 4
    rows = [(C, tmd + cb + prev + 36 * c + 4, 2, 16, W, 0) for c in range(3)] + [
        (C, tmd + cb + prev + 0x6C, 2, 6, W, 0),
        (C, tmd + cb + size + q['m'], 2, 2, W, 0),
        (C, tmd + cb + size + q['gl'], 2, q['gln'], W, 0),
        (C, tmd + cb + size + q['bra'], q['brz'], q['NBR'], W, 0),
        (C, tmd + cb + size + q['brb'], q['brz'], q['NBR'], W, 0)]
    for base in (sv, log):
        rows += [(C, base + d['res'], 2, 1, W, 0), (C, base + d['team'], 2, d['SN'], W, 0),
                 (C, base + d['srow'] + d['srt'], d['srz'], 2 * d['SR'], W, 0)]
    rows += [(C, log + d['sv'] + d['mv'] + d['mvg'], d['mvz'], d['nmv'], G, 0),
             (C, log + d['sv'] + d['mv'] + d['mvt'], d['mvz'], d['nmv'], W, 0)]
    if save_at + dplay.LOG_AT != save_at + 0x400 or d['sv'] > dplay.LOG_AT - 4:
        errs.append('dplay: the log does not follow the state')
    # the game's arrays (ref/swos.asm): CFB = IDA - IDA_CFB, the label map checked on two known labels
    if not os.path.exists(LISTING):
        return rows, errs + [f'{LISTING} missing']
    a = open(LISTING, encoding='latin-1').read()
    ida = wsites.IDA_CFB
    need = [('careerFileBuffer dw 0', 'the CFB start'), ('tmdFileBuffer db 54720 dup(0)', 'the 80 records'),
            ('cmp     numForeignMarketPlayers, 15', 'AddForeignMarketPlayer bound'),
            ('cmp     numHomeMarketPlayers, 25', 'AddPlayerToCareerContest bound'),
            ('foreignMarketPlayers dd 15 dup(0)', 'foreign market'), ('JobOffer struc ; (sizeof=0x1A', 'JobOffer 26 B'),
            ('newJobOffers JobOffer 5 dup', 'newJobOffers[5]'), ('jobOffers JobOffer 5 dup', 'jobOffers[5]'),
            ('mov     word ptr D5, 16h', 'career calendar record 16h B (cseg_8C2AE)'),
            ('cmp     A4, offset dseg_DF4F4', 'calendar bound (cseg_8C516)'),
            ('dseg_DB3E6 db 1870 dup(0)', 'the calendar'), ('\ndseg_DF4F4 dw 0', 'the calendar end')]
    for text, what in need:
        if text not in a:
            errs.append(f'listing: {what} ({text!r}) not found')
    # CFB of the named arrays: from dseg_ labels around them (numOffers = dseg_D6D18 + 2 is not named: count the bytes)
    fm = 0xD6D1A - ida                                   # foreignMarketPlayers (numOffers dw at D6D18)
    hm = fm + 4 * 15
    nj = 0xD6E12 - ida                                   # newJobOffers (numNewJobOffers dw at D6E10)
    jo = nj + 5 * 26 + 2
    if jo + 5 * 26 + 2 + 2 + 10 != 0xD6F26 - ida:      # (timeToNegotiate, numPlayers.., playersOnTransferMarket[5])
        errs.append('jobOffers .. dseg_D6F26: not 5 x 26 B')
    if hm + 4 * 25 != 0xD6DBA - ida:
        errs.append('homeMarketPlayers .. dseg_D6DBA: not 25 x 4 B')
    if 0xD6CDC - ida != 0xD750:                          # (s7-bp-run.md: dseg_D6CDC = obj2+16E26h = .CAR +D750h)
        errs.append('IDA_CFB: dseg_D6CDC not at CFB D750h')
    # full pass (Motore 15/11): incoming offers dseg_D6DBA 5 x 14 B (+0 teamOffering), teamNoOfferAccepted (after dseg_D6CA2);
    # the 5 DIY contest slots (ProcessCareerFile's arrayOfPointers) as WS_D, room = the biggest type each holds: the
    # copy sizes of cseg_8B71C / 8B7EA (733h / 443h / B52h - 1 counts), slots 2 / 4 = 443h apart (cups only)
    need = [('dseg_D6DBA db 70 dup(0)', 'the offers (5 x 14)'), ('cmp     numOffers, 5', 'the offers bound'),
            ('mov     teamOffering, ax', 'offer +0 = teamOffering (OffersCommon)'),
            ('dseg_D6CA2 dw 0', 'the word before teamNoOfferAccepted'), ('\nteamNoOfferAccepted dw 0', 'teamNoOfferAccepted'),
            ('mov     teamNoOfferAccepted, ax', 'AcceptJobOffer writes it'),
            ('mov     word ptr D0, 732h', 'league copy 733h'), ('mov     word ptr D0, 442h', 'cup copy 443h'),
            ('mov     word ptr D0, 0B51h', 'type-2 copy B52h'),
            ('add     eax, 301    ; league offset', 'league list +301'), ('add     eax, 589    ; cup offset', 'cup list +589'),
            ('add     eax, 153    ; tournament offset', 'type-2 list +153')]
    for text, what in need:
        if text not in a:
            errs.append(f'listing: {what} ({text!r}) not found')
    pcf = a[a.index('ProcessCareerFile proc near'):a.index('ProcessCareerFile endp')]
    slots = re.findall(r'mov     dword ptr \[esi\], offset (\w+)', pcf)
    addr = {'competitionFileBuffer': 0xDF4F6, 'dseg_D8D0A': 0xD8D0A, 'dseg_D985C': 0xD985C, 'dseg_DA0E2': 0xDA0E2,
            'dseg_D9C9F': 0xD9C9F}
    if slots != list(addr):
        errs.append(f'arrayOfPointers: {slots}')
    ext = {0xD8D0A: 0xD985C, 0xD985C: 0xD9C9F, 0xD9C9F: 0xDA0E2, 0xDA0E2: 0xDACB4, 0xDF4F6: 0xDF4F6 + 0xB53}   # (next label)
    for o, room in wsites.DIY_SLOTS:
        if o + ida + room > ext[o + ida] or room not in (0x443, 0xB52) or (room == 0x443) != (ext[o + ida] - o - ida < 0xB52):
            errs.append(f'DIY slot {o + ida:#x}: room {room:#x} vs its extent {ext[o + ida] - o - ida:#x}')
    rows += [(C, 0xD6DBA - ida, 14, 5, W, 0), (C, 0xD6CA4 - ida, 0, 1, W, 0)]
    rows += [(C if o < 0x10000 else H, o & 0xFFFF, room, 1, wsites.WS_D, 0)
             for o, room in [(addr[n] - ida, 0x443 if ext[addr[n]] - addr[n] < 0xB52 else 0xB52) for n in slots]]
    cal, cend = 0xDB3E6 - ida, 0xDF4F4 - ida
    rows += [(C, fm, 4, 15, W, 0), (C, hm, 4, 25, W, 0), (C, nj, 26, 5, W, 0), (C, jo, 26, 5, W, 0),
             (H, cal - 0x10000 + 12, 22, (cend - cal) // 22, W, 0), (H, cal - 0x10000 + 14, 22, (cend - cal) // 22, W, 0)]
    return rows, errs


def test_wsites_cfb_layout():
    """WSITES 4c: every CFB row whose extent the code gives (cfb_code_rows: uefacoef PREV[3] x 16 / FIN[3] x 2, uefaq
    uq_state m, s, gl[3][36], br[NBR] a / b, dplay dp_save + its log res / team[SN] / srow[2][SR] / mv[4], the foreign /
    home markets 15 / 25, the job offers 5 + 5, the career calendar's CAL_N 16h-B records) is in wsites.ROWS with that
    offset, stride and count - the capacity, not what the saves showed; CFB rows share no byte and stay inside the
    fixed part."""
    rows, errs = cfb_code_rows()
    have = [r for r in wsites.ROWS if r[0] in (wsites.WI_CFB, wsites.WI_CFBH)]
    miss = [r for r in rows if r not in have]
    if miss:
        errs.append(f'not in ROWS: {[(r[0], hex(r[1]), r[2], r[3]) for r in miss[:4]]}')
    used = {}
    for it, off, st, cnt, form, aux in have:
        base = (0x10000 if it == wsites.WI_CFBH else 0) + off
        span = st if form == wsites.WS_D else (cnt - 1) * st + 2
        if base + span > FIX_LEN:
            errs.append(f'{base:#x}: past the fixed part')
        for k in range(cnt):
            for b in (range(base, base + st) if form == wsites.WS_D else (base + k * st, base + k * st + 1)):
                if b in used:
                    errs.append(f'{b:#x}: in rows {used[b]:#x} and {base:#x}')
                used[b] = base
    return not errs, '; '.join(errs[:6]) or (f'{len(rows)} CFB rows = the code\'s extents (uefaq br {rows[6][3]}, '
                                             f'calendar {rows[-1][3]} records, markets 15 / 25, job offers 5 + 5); '
                                             f'{len(have)} CFB rows, no shared byte')


# ---- CF_ST in the S7 swap (cf-st-s7.md): the career club's division winner word (CN pad) ---------------------------------
def test_wsites_cn():
    """item 'CN' (struct cn_state {u8 season, pad[3], name[32]}): pad[0..1] = the winner's word, pad[2] = 'W' (the marker:
    word 0 is a real club). On the shaped build: (1) a winner that crosses at the swap is its new word, the marker kept;
    a winner that stays is untouched; (2) multi-swap (MC 13/11): the winner crosses again at the NEXT season's swap and is
    walked again: the page still names the same club (identity kept over two swaps); (3) no marker (an old save, zero pad):
    pad[2] never becomes 'W' (the walk touches words only; cf_last1 falls back to the CF path - the build's C)."""
    import test_s7swap as t7
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    import engine
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    m = t7.M(EXE)
    errs = []
    m.fresh()
    enn = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_ENN'), 4))[0]
    eni = struct.unpack(f'<{3 * enn}I', m.rd(m.at('s7swap', 'S7_ENI'), 12 * enn))
    cn = next((eni[3 * e] for e in range(enn) if eni[3 * e + 2] & 0xFFFF == engine.item_id('CN')), None)
    if cn is None:
        return False, 'item CN not in S7_ENI'
    fs, word, at, rdiv, rows_ = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    ident = {w: i for i, w in enumerate(word)}

    def put(w, marker=True):
        m.w(cn, bytes([6]) + struct.pack('<H', w) + (b'W' if marker else b'\0'))

    def get():
        b = m.rd(cn, 4)
        return struct.unpack_from('<H', b, 1)[0], b[3]
    stay = t7.FA | 10 << 8
    for w in (down[0][1], up[0][1], stay):                  # (1) crosses down / crosses up / stays
        m.fresh()
        fs, word, at, rdiv, rows_ = t7.reg_parse(m.regb())
        put(w)
        stt, *_ = t7.run(m, down, up)
        word1 = t7.reg_parse(m.regb())[1]
        nw = word1[ident[w]]
        got = get()
        if stt != t7.OK or got != (nw, ord('W')):
            errs.append(f'winner {w:#x}: after the swap {got[0]:#x}/{got[1]:#x} (want {nw:#x}/W), status {stt}')
        if (w == stay) != (nw == w):
            errs.append(f'winner {w:#x}: moved = {nw != w} (a staying club must not move)')
    m.fresh()                                               # (2) the same club crosses twice
    fs, word, at, rdiv, rows_ = t7.reg_parse(m.regb())
    w0 = up[0][1]                                           # (a Serie D first: goes up at swap 1)
    put(w0)
    stt, *_ = t7.run(m, down, up)
    fs1, word1, at1, _, _ = t7.reg_parse(m.regb())
    w1 = word1[ident[w0]]
    down2, up2 = t7.crossings(fs1, m.gb)
    cross2 = down2[0][1]                                    # (the club at this word goes down at swap 2)
    c2_ident = next(i for i, ww in enumerate(word1) if ww == cross2)
    put(cross2)
    stt2, *_ = t7.run(m, down2, up2, sa=t7.SEASON + 1, sb=t7.SEASON + 1)
    if stt2 != t7.OK:
        errs.append(f'second swap status {stt2}')
    else:
        word2 = t7.reg_parse(m.regb())[1]
        got = get()
        if got != (word2[c2_ident], ord('W')) or word2[c2_ident] == cross2:
            errs.append(f'second swap: the winner {cross2:#x} is {got[0]:#x} (want {word2[c2_ident]:#x}, moved)')
    m.fresh()                                               # (3) no marker: left as it is
    put(down[0][1], marker=False)
    t7.run(m, down, up)
    if get()[1] == ord('W'):
        errs.append('no marker: pad[2] became W')
    return not errs, '; '.join(errs[:5]) or ('CN winner word: a crosser (down / up) -> its new word, marker kept; a staying club '
                                             'untouched; walked again at the next swap (same club); no marker stays no marker')


OLD_CN_SAVES = [os.path.join(HOME, 'swos-mod', 'internal', f) for f in (
    'davide-mister-20261022-rc11/PHILA.CAR', 'davide-mister-20261022-rc11/MESTRE.CAR', 'uesum/cv_s2_cl_it.CAR',
    'swostest/saves/W84E.CAR', 'swostest/saves/W84E_TEAM254.CAR')]


def _en_items(d):
    """the engine block's {item id: bytes} of a .CAR (EN mark, u16 length, items {u16 id, u16 length, bytes}), or None"""
    import zlib
    known = {zlib.crc32(n.encode()) & 0xFFFF for n in ('GP', 'CF', 'CN', 'SC', 'WN', 'SWC1', 'CC', 'CT', 'CE', 'US')}
    o = -1
    while True:
        o = d.find(b'EN', o + 1)
        if o < 0 or o + 4 > len(d):
            return None
        p, end, items = o + 4, o + 4 + struct.unpack_from('<H', d, o + 2)[0], {}
        if end > len(d):
            continue
        while p + 4 <= end and p + 4 + struct.unpack_from('<H', d, p + 2)[0] <= end:
            ln = struct.unpack_from('<H', d, p + 2)[0]
            items[struct.unpack_from('<H', d, p)[0]] = d[p + 4:p + 4 + ln]
            p += 4 + ln
        if p == end and len(known & set(items)) >= 3:
            return items


def test_wsites_cn_oldsaves():
    """MC 13/11: cf_last1 takes the career club's winner word only when CN pad[2] == 'W'. In the old saves we have
    (PHILA, MESTRE, W84E, W84E_TEAM254, cv_s2) the item CN is absent (loaded as zero) or has pad[2] != 'W': the fallback
    (the old CF path, unchanged code) is taken, so the VINCITORI last-season page is what it is today."""
    import zlib
    cid = zlib.crc32(b'CN') & 0xFFFF
    seen, errs = [], []
    for p in OLD_CN_SAVES:
        if not os.path.exists(p):
            continue
        items = _en_items(open(p, 'rb').read())
        cn = None if items is None else items.get(cid)
        if cn is not None and len(cn) >= 4 and cn[3] == ord('W'):
            errs.append(f'{os.path.basename(p)}: CN pad[2] is already W ({cn[:4].hex()})')
        seen.append(f'{os.path.basename(p)}:{"no item" if cn is None else cn[:4].hex()}')
    if not seen:
        return True, 'SKIP: no old saves'
    return not errs, '; '.join(errs) or f'fallback path in every old save ({", ".join(seen)})'


def test_wsites_wn_m():
    """WN_ST entry 0 is 'M': the career club's last-season division (its team file + local division - the key of the
    WINNERS page's division title). Its word is not walked: after a crossing the page must keep naming the OLD division
    (Panchina 13/11: a walked word gave 'SERIE A (STAGIONE REGOLARE)' for a Serie D club that went up). Entry 1.. (a
    division winner's word) are walked: a crosser -> its new word. Planted on the shaped build: e0 = 'M' + a crosser's word,
    e1 = 'L' + the same word, e2 = 'L' + a staying club."""
    import test_s7swap as t7
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    import engine
    m = t7.M(EXE)
    m.fresh()
    enn = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_ENN'), 4))[0]
    eni = struct.unpack(f'<{3 * enn}I', m.rd(m.at('s7swap', 'S7_ENI'), 12 * enn))
    wn = next((eni[3 * e] for e in range(enn) if eni[3 * e + 2] & 0xFFFF == engine.item_id('WN')), None)
    if wn is None:
        return False, 'item WN not in S7_ENI'
    fs, word, at, rdiv, rows_ = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    ident = {w: i for i, w in enumerate(word)}
    cross, stay = down[0][1], t7.FA | 10 << 8
    m.w(wn, struct.pack('<HBB', 0x4E57, 0x7E, 3) + struct.pack('<BBH', ord('M'), 1, cross) +
        struct.pack('<BBH', ord('L'), 0, cross) + struct.pack('<BBH', ord('L'), 1, stay))
    stt, *_ = t7.run(m, down, up)
    new = t7.reg_parse(m.regb())[1][ident[cross]]
    e = [struct.unpack_from('<BBH', m.rd(wn + 4, 12), 4 * k) for k in range(3)]
    errs = []
    if stt != t7.OK or new == cross:
        errs.append(f'status {stt}, the crosser moved: {new != cross}')
    if e[0] != (ord('M'), 1, cross):
        errs.append(f'M entry changed: {e[0]} (want the old word {cross:#x})')
    if e[1] != (ord('L'), 0, new):
        errs.append(f"L entry: {e[1]} (want the new word {new:#x})")
    if e[2] != (ord('L'), 1, stay):
        errs.append(f'staying winner changed: {e[2]}')
    return not errs, '; '.join(errs) or "WN 'M' (last season's division key) kept, a crossing winner's word walked, a stayer untouched"


def test_wsites_wn_kinds():
    """MC 13/11: the WN row starts at entry 1 because entry 0 is the ONLY non-club entry of WN_ST. Read from gplay.c at
    test time, every writer of WN_ST entries: wn_add('M', division, career club) - the last-season DIVISION KEY, first, once
    (right after WN_ST.n = 0); wn_add('L', division, its winner), wn_add('K', play-off id, its winner),
    wn_add(0x80 | play-off id, place, a club): all club words (walked); the preview marker WN_PRE 'p' (idx = the season,
    team word 0: nothing to walk). A new kind, a second 'M' or a different first call FAILs here: it needs a decision on the
    WN row (a fixed 'start at 1' would be wrong for another division key)."""
    import re
    src = open(os.path.join(TOOLS, 'gplay.c')).read()
    calls = [(m.start(), m.group(1).strip()) for m in re.finditer(r"\bwn_add\(\s*([^,]+),", src)
             if not src[max(0, m.start() - 12):m.start()].endswith('void ')]
    kinds = [k for _, k in calls]
    errs = []
    allowed = {"'M'", "'L'", "'K'", '0x80 | (pidx & 0x7F)'}
    for k in set(kinds) - allowed:
        errs.append(f'new wn_add kind {k}: decide the WN row')
    if kinds.count("'M'") != 1:
        errs.append(f"wn_add('M') x {kinds.count(chr(39) + 'M' + chr(39))} (want exactly 1)")
    first = src.index("wn_add('M'")
    reset = src.rindex('WN_ST.n = 0', 0, first)
    if any(reset < p < first for p, _ in calls):
        errs.append("a wn_add call between WN_ST.n = 0 and wn_add('M'): 'M' is not entry 0")
    if "x->type = WN_PRE; x->idx = GP_SEAS; x->team = 0;" not in src:
        errs.append('the preview marker no longer has team word 0')
    return not errs, '; '.join(errs) or f"wn_add kinds {sorted(allowed)} + the 'p' marker (team 0); 'M' once, entry 0: the WN row's \"start at 1\" holds"


# ---- MC 15/11: the old-save import (42-s7import's s7_imp_walk) over the offers / accepted-job rows ------------------
IMP_SAVES = [os.path.join(MAINDIR, 's7imp', f) for f in ('ligorna41_mid.CAR', 'trento41_mid.CAR')]


def test_wsites_import(drop=False):
    """The 4.1 -> S7 import's walk (s7swap.c s7_imp_walk, the word map sr_wmap_import gives - here a stand-in: every
    4.1 Serie D word 102|x (x >= 100) -> 144|x-100, the rest kept) on two real 4.1 mid-season saves with a pending
    transfer offer (ligorna41_mid: offer from 102|115, a Serie D club - moves; trento41_mid: from 102|71 - kept), each
    loaded into careerFileBuffer (S7_CFB) of HT_WS_EXE. The accepted job (teamNoOfferAccepted, set between the season
    end and the next season) is planted: a moving club in both. Differential: run A = the save with the five offer
    words and the accepted job cleared (0 / FFFFh), run B = the save as is + the job; the two CFBs after the walk differ
    exactly at the planted words, each its club's new word (or kept), every other offer byte (records +2..+13) as
    loaded, a decoy (the moving club's old word at +4 of the next free record: a non-team field) untouched; S7_WLOG
    row -1 (every site resolved), B's changed count = A's + the planted words that move."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    saves = [p for p in IMP_SAVES if os.path.exists(p)]
    if not saves:
        return True, 'SKIP: no 4.1 mid-season saves (internal/swostest/s7imp)'
    import test_s7swap as t7
    import test_swc1 as ts
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 's7_imp_walk' not in sy.get('s7swap', {}):
        return False, f'{EXE}: no s7_imp_walk (a 42-s7import build?)'
    m = t7.M(EXE)
    if drop:                                            # (the control: the offers / accepted-job rows count 0 in the exe)
        ws = m.at('s7swap', 'WSITES')
        for k in range(wsites.WS_MAX):
            r = struct.unpack('<4H2B', m.rd(ws + 10 * k, 10))
            if r[0] == wsites.WS_END:
                break
            if r[0] == wsites.WI_CFB and r[1] in (wsites.OFFERS, wsites.JOBACC):
                m.w(ws + 10 * k + 6, b'\0\0')
    cfb = m.at('s7swap', 'S7_CFB')
    cfblen = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_CFBLEN'), 4))[0]
    MAP_AT, SLT_AT = ts.BUF, ts.BUF + 0x8000
    pairs = [(102 | x << 8, 144 | (x - 100) << 8) for x in range(100, 256)]
    pairs.sort()
    nw = dict(pairs)
    W = lambda d, o: struct.unpack_from('<H', d, o)[0]          # noqa: E731
    OFF = [wsites.OFFERS + 14 * k for k in range(5)]
    errs, notes = [], []

    def walk(img):
        m.fresh()
        m.w(cfb, bytes(cfblen))
        m.w(cfb, img[:cfblen])
        m.w(MAP_AT, b''.join(struct.pack('<HH', a, b) for a, b in pairs))
        m.w(SLT_AT, bytes(2400))
        rc = m.call('s7swap', 's7_imp_walk', MAP_AT, len(pairs), SLT_AT)
        wl = struct.unpack('<hhHHHH', m.rd(m.at('s7swap', 'S7_WLOG'), 12))
        return rc, wl, m.rd(cfb, cfblen)
    for p in saves:
        tag = os.path.basename(p)
        d = open(p, 'rb').read()
        offer = W(d, OFF[0])
        job = offer if offer >> 8 >= 100 else 102 | 120 << 8          # (a moving club either way)
        a = bytearray(d)
        for o in OFF:
            struct.pack_into('<H', a, o, 0)
        struct.pack_into('<H', a, wsites.JOBACC, 0xFFFF)
        b = bytearray(d)
        struct.pack_into('<H', b, wsites.JOBACC, job)
        free = next(k for k in range(5) if W(d, OFF[k]) == 0)
        struct.pack_into('<H', a, OFF[free] + 4, offer)                 # (the decoy, both runs)
        struct.pack_into('<H', b, OFF[free] + 4, offer)
        planted = {o: W(b, o) for o in OFF if W(b, o) not in (0, 0xFFFF)}
        planted[wsites.JOBACC] = job
        ra, wa, oa = walk(bytes(a))
        rb, wb, ob = walk(bytes(b))
        if (ra, rb, wa[0], wb[0]) != (0, 0, -1, -1):
            errs.append(f'{tag}: rc {ra} / {rb}, S7_WLOG.row {wa[0]} / {wb[0]}')
            continue
        diff = {o & ~1 for o in range(cfblen) if oa[o] != ob[o]}
        want = set(planted)
        if not diff <= want:
            errs.append(f'{tag}: A / B differ outside the planted words: {[hex(o) for o in sorted(diff - want)[:6]]}')
        for o, v in planted.items():
            if W(ob, o) != nw.get(v, v):
                errs.append(f'{tag}: +{o:#x} {v:#x} -> {W(ob, o):#x}, want {nw.get(v, v):#x}')
        for k, o in enumerate(OFF):
            if ob[o + 2:o + 14] != b[o + 2:o + 14] or oa[o + 2:o + 14] != a[o + 2:o + 14]:
                errs.append(f'{tag}: offer {k} bytes +2..+13 changed (decoy {"here" if k == free else "no"})')
        moves = sum(nw.get(v, v) != v for v in planted.values())
        if wb[2] != wa[2] + moves:
            errs.append(f'{tag}: changed {wb[2]} != {wa[2]} + {moves}')
        notes.append(f'{tag}: offer {offer:#x} -> {W(ob, OFF[0]):#x}, job {job:#x} -> {W(ob, wsites.JOBACC):#x} '
                     f'({wa[2]} background words moved in both, +{moves})')
    return not errs, '; '.join(errs[:6]) or '; '.join(notes) + '; decoys and the other offer bytes untouched'


def test_wsites_import_control():
    """test_wsites_import with the offers and accepted-job rows switched off in the exe's WSITES (count 0): must FAIL -
    the words stay 4.1's (the rows are what remaps them)."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    ok, msg = test_wsites_import(drop=True)
    if msg.startswith('SKIP'):
        return True, msg
    if ok:
        return False, 'the import moved the offer / job words with their rows off'
    return True, f'rows off: caught ({msg[:120]})'
