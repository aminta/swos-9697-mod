"""4.2 S7 (MC 13/11, world_s7cross_winners / _x): the SEASON WINNERS texts of a league over two team files. gplay.c
keeps the career club's last season in WN_ST by struct: 'M' = (its team word, the division inside its file), 'L' dd =
that file's division, 'K' / 'T' pi = the play-off's number in its struct's spec (mkseason po_keys). The WIN texts
(fmtgame.win_lines) must use the same numbers: the key line 01h 'H' file dd, the 'L' / 'S' division byte, the 'K' /
'T' / 'D' / 'Q' play-off byte. Before the fix they used the league file (102) and the global numbers (Serie D
divisions 5..13, play-offs 5..25): no H90xx key, so no last-season page or another division's.
On HT_S7PACK (else internal/s7pack-real/ita: Italy 102 + 144):
- the 14 key lines are H6600..H6604 (Serie A..C) and H9000..H9008 (Serie D girone A..I), one per division;
- every 'L' / 'S' source's division byte = its key line's;
- every play-off byte is (struct, local number) of mkseason.Pack.po_keys for a play-off of that division's struct;
- control: the dormant numbering (global k / pi) gives no H90xx key.
With HT_WK_DATA (a built DATA dir of that pack): FMTxx5.DAT holds H9000..H9008 in all four languages."""
import os
import re
import sys

HOME = os.path.expanduser('~')
PACK = os.environ.get('HT_S7PACK') or os.path.join(HOME, 'swos-mod', 'internal', 's7pack-real', 'ita')
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def test_wnkeys_s7():
    if not os.path.exists(os.path.join(PACK, 'pack.json')):
        return True, f'SKIP: {PACK} missing (the real S7 pack)'
    sys.path.insert(0, TOOLS)
    import fmtgame
    import mkseason
    pk = mkseason.Pack(PACK)
    pok = pk.po_keys()
    errs = []
    blocks = [t['win']['it'] for _, _, _, t in fmtgame.from_pack(PACK) if 'win' in t]
    keys = []
    for b in blocks:
        srcs = [s for _, s in b]
        h = [s for s in srcs if s.startswith('H')]
        if len(h) != 1 or srcs[0] != h[0]:
            errs.append(f'{srcs}: want one key line first')
            continue
        f, dd = int(h[0][1:3], 16), int(h[0][3:5], 16)
        keys.append(h[0])
        for s in srcs[1:]:
            if s[0] == 'L' and int(s[-2:], 16) != dd:
                errs.append(f'{h[0]}: {s} division byte != the key\'s')
            if s[0] == 'S' and int(s[-2:], 16) != dd:
                errs.append(f'{h[0]}: {s} division byte != the key\'s')
            pi = int(s[1:3], 16) if s[0] in 'KT' else int(s[2:4], 16) if s[0] in 'DQ' else None
            if pi is not None and (f, pi) not in pok:
                errs.append(f'{h[0]}: {s} play-off {pi} is not one of file {f}\'s ({sum(x[0] == f for x in pok)})')
    want = [f'H66{d:02X}' for d in range(5)] + [f'H90{d:02X}' for d in range(9)]
    if sorted(keys) != want:
        errs.append(f'key lines {sorted(keys)}: want {want}')
    k_lines = sorted({s for b in blocks for _, s in b if s[0] == 'K' and b[0][1].startswith('H90')})
    if k_lines != ['K00', 'K14']:                       # (dA_title = 144's 0, poule_scudetto = 144's 20)
        errs.append(f'Serie D play-off lines {k_lines}: want K00 (dA_title) and K14 (the Poule, 144\'s 20th)')
    keep = fmtgame.s7_keys                               # (control: the dormant numbering - no H90xx, Serie D's
    fmtgame.s7_keys = lambda d, m: None                  # play-offs K05 / K19 as before the fix)
    try:
        old = [s for _, _, _, t in fmtgame.from_pack(PACK) if 'win' in t for _, s in t['win']['it']]
    finally:
        fmtgame.s7_keys = keep
    if any(s.startswith('H90') for s in old) or 'K19' not in old:
        errs.append(f'control: the dormant numbering {sorted(set(old))[:20]} (the test cannot tell)')
    dd = os.environ.get('HT_WK_DATA')
    if dd:
        for lang in ('IT', 'EN', 'FR', 'DE'):
            b = open(os.path.join(dd, f'FMT{lang}5.DAT'), 'rb').read()
            ks = {m.group(1).decode() for m in re.finditer(rb'\x01H([0-9A-F]{4})', b)}
            miss = [w for w in want if w[1:] not in ks]
            if miss:
                errs.append(f'FMT{lang}5.DAT: no key {miss}')
    return not errs, '; '.join(errs) or (f'{len(keys)} key lines, Serie D H9000..H9008, play-offs K00 / K14 by '
                                         f'struct' + (', FMTxx5.DAT x4 hold them' if dd else ''))
