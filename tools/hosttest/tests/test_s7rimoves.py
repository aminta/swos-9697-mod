"""4.2 S7 x pool (s7-ri-fix.md "## Changes", MC's ruling 13/11: the registry is the single source of truth), Shaved's
part, on HT_S7RI_EXE (else c/S7RI-hs: a REAL-pack IT build - internal/s7pack-real/ita, 298 idents, pool idents
262..297 off the files - with HOSTTEST_SYMS=1). ri_pool (s7ri.c) only logs the season end's pool moves in RI_MOVES
{row of 144, out ident, in ident}; s7_season applies them to the registry; s7_load gives a pool ident's row its RS record.

test_s7rimoves:
- the seed: S7_POOL0 / S7_NPOOL = the registry's off-file idents (first, count: 262, 36), consecutive; s7_poolk maps
  pool record k <-> ident S7_POOL0 + k both ways and refuses the rest;
- two moves poked (rows = the last place of Serie D groups A and B, in = pool idents 0 and 1) + the 9-swap season:
  status OK, S7_RIMV (2, ok), out idents off the files (word NONE), in idents at the rows (word = 144 | row << 8), the
  pool count down by 2 and up by 2 (the outs), no ident on two rows, nswap = 9 + 2; RI_S7_BAD 0;
- s7_load of 144 after it, RS5144.DAT poked into RI_POOL (no DOS here): LD_OK, nopool 0, moved 9 + 2, each move's
  row = RS record k with bytes 0..4, 23, 25 kept from the buffer;
- refused (S7_RIMV_BAD, S7_RIMV status 2, the registry unchanged, nothing applied): out not at the row, in already
  on a row, the same row twice, the same in twice, row past 144's rows, in out of range."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_s7swap as t7  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_S7RI_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7RI-hs', 'SWOS', 'ITALIAN.EXE')
NONE = 0xFFFF
RIMV_BAD = 12


def setup():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return None, f'SKIP: {EXE} (a real-pack HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'RI_MOVES' not in sy.get('s7swap', {}):
        return None, f'{EXE}: no RI_MOVES (s7ri.c not linked)'
    m = t7.M(EXE)
    m.fresh()
    m.w(m.at('swefile', 'swe_fopen_r'), b'\xb8\xfe\xff\xff\xff\xc3')   # (Unicorn: no DOS - every open fails)
    return m, ''


def poke_moves(m, mv):
    b = b''.join(struct.pack('<3H', *e) for e in mv)
    m.w(m.at('s7swap', 'RI_MOVES'), b)
    m.w(m.at('s7swap', 'RI_NMOVES'), struct.pack('<i', len(mv)))


def rimv(m):
    return struct.unpack('<BBH', m.rd(m.at('s7swap', 'S7_RIMV'), 4))


def test_s7rimoves():
    m, why = setup()
    if not m:
        return why.startswith('SKIP'), why
    errs = []
    fs, word, at, rdiv, rows = t7.reg_parse(m.regb())
    p0, np_ = struct.unpack('<HH', m.rd(m.at('s7swap', 'S7_POOL0'), 4))
    off = [i for i, w in enumerate(word) if w == NONE]
    if (p0, np_) != ((off[0] if off else NONE), len(off)) or off != list(range(p0, p0 + np_)):
        errs.append(f'seed: S7_POOL0 / S7_NPOOL {p0} / {np_}, off-file idents {off[:3]}..{off[-1:]} ({len(off)})')
    for k in (0, np_ - 1):
        if m.call('s7swap', 's7_poolk', 0x10000 | k) != p0 + k or m.call('s7swap', 's7_poolk', p0 + k) != k:
            errs.append(f's7_poolk: record {k} <-> ident {p0 + k} not both ways')
    for x in (0x10000 | np_, p0 - 1, p0 + np_):
        if m.call('s7swap', 's7_poolk', x) != NONE:
            errs.append(f's7_poolk({x:#x}) not refused')
    fb = [f[0] for f in fs].index(t7.FB)
    ends = [sum(fs[fb][2][:g + 1]) - 1 for g in range(2)]   # (Serie D groups A, B: their last rows)
    mv = [(r, at[fb][r], p0 + k) for k, r in enumerate(ends)]
    # refusals first, each from a fresh registry: nothing applied
    nat = at[fb][0]
    for name, bad in (('out not at the row', [(ends[0], at[fb][ends[1]], p0)]),
                      ('in already on a row', [(ends[0], at[fb][ends[0]], nat)]),
                      ('the same row twice', [mv[0], (ends[0], at[fb][ends[0]], p0 + 1)]),
                      ('the same in twice', [mv[0], (ends[1], at[fb][ends[1]], p0)]),
                      ('row past the rows', [(rows[fb], 0, p0)]),
                      ('in out of range', [(ends[0], at[fb][ends[0]], len(word))])):
        m.fresh()
        r0 = m.regb()
        poke_moves(m, bad)
        st = t7.run(m, *t7.crossings(fs, m.gb))[0]
        if st != RIMV_BAD or rimv(m)[1] != 2 or m.regb() != r0:
            errs.append(f'{name}: status {st}, S7_RIMV {rimv(m)}, registry {"kept" if m.regb() == r0 else "changed"}')
    m.fresh()
    poke_moves(m, mv)
    st, nsw, ncr, _ = t7.run(m, *t7.crossings(fs, m.gb))
    n, mst, _ = rimv(m)
    if (st, n, mst) != (t7.OK, 2, 1) or nsw != 9 + 2:
        errs.append(f'moves: status {st}, S7_RIMV ({n}, {mst}), nswap {nsw} (want OK, (2, 1), 11)')
    fs1, word1, at1, rdiv1, rows1 = t7.reg_parse(m.regb())
    for r, out, inn in mv:
        if word1[out] != NONE or at1[fb][r] != inn or word1[inn] != (t7.FB | r << 8):
            errs.append(f'row {r}: out {out} word {word1[out]:#x}, at {at1[fb][r]}, in {inn} word {word1[inn]:#x}')
    off1 = sorted(i for i, w in enumerate(word1) if w == NONE)
    if off1 != sorted(set(off) - {e[2] for e in mv} | {e[1] for e in mv}):
        errs.append(f'off-file idents after: {len(off1)} (want the pool - ins + outs)')
    seen = {}
    for fi in range(len(fs1)):
        for o in range(rows1[fi]):
            i = at1[fi][o]
            if i in seen:
                errs.append(f'ident {i} on two rows {seen[i]} and {(fs1[fi][0], o)}')
            seen[i] = (fs1[fi][0], o)
            if word1[i] != (fs1[fi][0] | o << 8):
                errs.append(f'ident {i}: word {word1[i]:#x} != its row {fs1[fi][0]}/{o}')
    if struct.unpack('<i', m.rd(m.at('s7swap', 'RI_S7_BAD'), 4))[0]:
        errs.append('RI_S7_BAD != 0')
    # s7_load of 144: the pool rows get their RS record
    data = os.path.join(os.path.dirname(EXE), 'DATA')
    fil = {f: open(os.path.join(data, f'TMW5.{f}'), 'rb').read() for f in (t7.FA, t7.FB)}
    rs = open(os.path.join(data, 'RS5144.DAT'), 'rb').read()
    import s7swap
    oat = struct.unpack('<II', m.rd(m.at('s7swap', 'S7_OAT'), 8))
    orig = m.at('swe', 'S7_ORIG')
    for s_, f in enumerate((t7.FA, t7.FB)):
        m.w(orig + oat[s_], fil[f])
    b = bytearray(m.rd(m.at('s7swap', 'S7_LD'), 16))
    b[1] = 1
    m.w(m.at('s7swap', 'S7_LD'), bytes(b))
    m.w(m.at('s7swap', 'S7_FNV'), struct.pack('<II', *(s7swap.fnv(fil[f]) for f in (t7.FA, t7.FB))))
    ripool = struct.unpack('<I', m.rd(m.at('s7swap', 'S7_RIPOOL'), 4))[0]
    if not ripool:
        errs.append('S7_RIPOOL not set')
    else:
        m.w(ripool, rs)
    m.uc.mem_map(t7.TB, 0x40000)
    buf = bytearray(fil[t7.FB])
    for k, kb in enumerate(t7.KEPT):                    # (row bytes marked: kept from the buffer)
        for r, _, _ in mv:
            buf[2 + 684 * r + kb] = (0x40 + 7 * k + r) & 0xFF
    m.w(t7.OB, fil[t7.FB])
    m.w(t7.TB, bytes(buf))
    m.call('s7swap', 's7_load', t7.TB, t7.FB, t7.OB)
    lst, _, _, nopool, moved = struct.unpack('<BBBBH', m.rd(m.at('s7swap', 'S7_LD'), 6))
    if (lst, nopool, moved) != (t7.LD_OK, 0, 11):
        errs.append(f's7_load 144: status {lst} nopool {nopool} moved {moved} (want {t7.LD_OK}, 0, 11)')
    got = m.rd(t7.TB, len(buf))
    for k, (r, _, _) in enumerate(mv):
        want = bytearray(rs[2 + 684 * k:2 + 684 * (k + 1)])
        for kb in t7.KEPT:
            want[kb] = buf[2 + 684 * r + kb]
        if got[2 + 684 * r:2 + 684 * (r + 1)] != bytes(want):
            errs.append(f's7_load row {r}: not RS record {k} (kept bytes from the row)')
    return not errs, '; '.join(errs[:6]) or (f'pool idents {p0}..{p0 + np_ - 1} seeded, s7_poolk both ways; 2 moves + '
                                             f'9 swaps: outs off the files, ins at rows {ends}, one row per ident, '
                                             f'RI_S7_BAD 0; s7_load: RS records 0 / 1 on those rows, nopool 0; '
                                             f'6 refusals with the registry kept')
