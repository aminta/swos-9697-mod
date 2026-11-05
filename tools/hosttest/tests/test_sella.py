"""Outgoing transfers rule A (sella.py): the game's offer for one of the career club's players (cseg_5AB36, through
sella's sl_try) run over many random states on fixtures taken at the scan's call into it (snapshot.py / ht_snapshot HT_LABELS=
sella.@TRY_AT on a SELLOFF_FORCE + HOSTTEST_SYMS build; HT_SA = the fixture dir, default sa_it: a World 2026-27
career at CELLE VARAZZE, Serie D). Each pool forced in turn (the pool draw's jb: never = our country's loaded clubs,
always = the team file's other countries); every offer made: the buyer not our club, not a cup-only club (league byte
4), of the forced pool's country side, and fewer than N of its 16 players priced above the player's value + MARGIN.
Also measured: the pools' sizes against the candidate list (116 bytes, byte indices) - the original test's and rule A's
candidates for each player value."""
import glob
import json
import os
import random
import struct
import sys

from emu import Machine

HOME = os.path.expanduser('~')
FIX = os.path.join(HOME, 'swos-mod', 'internal', 'hosttest', 'fixtures', os.environ.get('HT_SA', 'sa_it'))
SEEDS = int(os.environ.get('HT_SA_SEEDS', 400))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _sites():
    import gkinj
    import lepatch
    import sacups
    import sella
    p = lepatch.LEPatch(os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE'))
    s = sella.find(p)
    g = gkinj.find(p)
    s['SEL'] = p.target(1, s['CHK'] + 17)
    s['RNG'] = (g['RNG1'][1], g['RNG2'][1])
    s['A0'] = sacups.regs(p.le.obj_bytes(1))['A0']
    return s


def _snaps():
    out = []
    for js in glob.glob(os.path.join(FIX, '*.json')):
        if json.load(open(js))['label'].endswith(('sl_try', 'TRY_AT')):
            out.append(int(os.path.basename(js)[:-5]))
    return sorted(out)


def _orig_ok(rec, val, sel):
    """cseg_5B3B5 as the game: not our club, not cup-only, a player of the same value or both a cheaper and a pricier"""
    if struct.unpack_from('<H', rec)[0] == sel or rec[0x19] == 4:
        return False
    vs = rec[0x6C:0x6C + 16 * 0x26:0x26]
    return val in vs or (min(vs) < val < max(vs))


def _above(rec, val, margin):
    return sum(v > val + margin for v in rec[0x6C:0x6C + 16 * 0x26:0x26])


def test_sella_buyers():
    ks = _snaps()
    if not ks:
        return False, f'no sl_try fixture in {FIX}'
    s = _sites()
    o2 = lambda m, t: m.base2 + t[1]
    stats, bad, sizes = {}, [], []
    for k in ks:
        m = Machine(FIX, k)
        n_, mg, ring, rule = m.read('sella.SL_PARM', 4)
        regs = m.read(o2(m, (2, s['d0'])), 15 * 4)
        sel = m.u16(o2(m, s['SEL']))
        jb = m.base1 + s['POOL_JB']
        orig_jb = m.read(jb, 6)
        at = lambda k: m.u32(m.base1 + s[k])          # (the live absolute address in that instruction)
        nsel, ntmd = m.u16(at('NSEL')), m.u16(at('NTMD'))
        selp, tmd = m.u32(at('SELP')), at('TMD')
        dom = [m.read(selp + 0x2AC * i, 0x2AC) for i in range(nsel)]
        fgn = [m.read(tmd + 0x2AC * i, 0x2AC) for i in range(ntmd)]
        for val in range(0, 50, 7):                     # (pool sizes vs the 116-byte list, per value byte)
            od = [r for r in dom if r[0] == sel & 0xFF and _orig_ok(r, val, sel)]
            ad = [r for r in od if _above(r, val, mg) < n_]
            sizes.append((k, val, nsel, len(od), len(ad)))
        rnd = random.Random(k)
        for pool in ('dom', 'fgn'):
            m.write(jb, b'\x90' * 6 if pool == 'dom' else
                    b'\xe9' + struct.pack('<i', struct.unpack('<i', orig_jb[2:])[0] + 1) + b'\x90')
            st = stats.setdefault(pool, dict(tries=0, offers=0, vals=set()))
            for i in range(SEEDS):
                m.write(o2(m, (2, s['d0'])), regs)
                m.write(o2(m, (2, s['d0'] + 4)), struct.pack('<H', rnd.randrange(16)))   # D1 = a player index
                for at in s['RNG']:
                    m.write(m.base2 + at, bytes(rnd.randrange(256) for _ in range(3)))
                m.write(o2(m, s['NOFF']), b'\0\0')
                made = m.u32('sella.SL_MADE')
                m.call('sella.sl_try')
                st['tries'] += 1
                if m.u32('sella.SL_MADE') == made:
                    continue
                st['offers'] += 1
                rec = m.read(m.u32(o2(m, (2, s['A0'] + 24))), 0x2AC)     # (A6: the chosen buyer's record)
                val = m.u8(o2(m, (2, s['d0'] + 28)))                     # (D7: the player's value byte)
                st['vals'].add(val)
                buyer = struct.unpack_from('<H', rec)[0]
                why = []
                if buyer != m.u16(o2(m, s['TOFF'])):
                    why.append(f'record {buyer:#x} != teamOffering {m.u16(o2(m, s["TOFF"])):#x}')
                if buyer == sel or rec[0x19] == 4:
                    why.append('own / cup-only club')
                if (rec[0] == sel & 0xFF) != (pool == 'dom'):
                    why.append(f'country {rec[0]} in the {pool} pool')
                if rule and _above(rec, val, mg) >= n_:
                    why.append(f'{_above(rec, val, mg)} above v{val}+{mg}')
                if why:
                    bad.append((k, pool, rec[5:22].split(b'\0')[0].decode('latin-1'), val, why))
        m.write(jb, orig_jb)
    worst = max(sizes, key=lambda x: x[3])
    msg = (f'fixtures {ks}, N {n_} margin {mg} rule {rule}; ' +
           ', '.join(f'{p}: {v["tries"]} tries {v["offers"]} offers values {sorted(v["vals"])}' for p, v in stats.items()) +
           f'; domestic pool {worst[2]} clubs, original candidates up to {worst[3]} (value {worst[1]}), with rule A '
           f'{max(x[4] for x in sizes)} (list 116 B, byte indices); bad {bad[:6]}')
    ok = not bad and all(v['offers'] for v in stats.values())
    return ok, msg
