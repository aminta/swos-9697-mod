"""Outgoing transfers rule A (sella.py): the game's offer for one of the career club's players (cseg_5AB36, through
sella's sl_try) run over many random states on fixtures taken at the scan's call into it (snapshot.py / ht_snapshot HT_LABELS=
sella.@TRY_AT on a SELLOFF_FORCE + HOSTTEST_SYMS build; HT_SA = the fixture dir, default sa_it: a World 2026-27
career at CELLE VARAZZE, Serie D). Each pool forced in turn (the pool draw's jb: never = the loaded clubs of our team file - in a world career our
division -, always = the other files' clubs: in a world career careerworld's big-world buffer); every offer made: the
buyer not our club, not a cup-only club (league byte 4), of the forced pool's side, and fewer than N of its 16 players
priced above the player's value + MARGIN. Also measured and asserted, with every price byte 0-49 on our player 0
(careerTeam): the candidate list's real use (fill bytes, the highest written) never past its capacity (116 bytes, byte
indices; or sella's moved list, SL_CAP) and no call writes past it."""
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
CAP, LIST_ORIG, GUARD = 116, 0xB4EAE, 64        # (dseg_175036: 116 B of byte indices, then dseg_1750AA - the national
                                                #  selector table; a moved list: sella's SL_CAP)
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


def _above(rec, val, margin):
    return sum(v > val + margin for v in rec[0x6C:0x6C + 16 * 0x26:0x26])


def _career_team(m, s, sel):
    """careerTeam's player array (GetPlayer's for our club): our record's 16 value bytes found again in obj2"""
    at = lambda k: m.u32(m.base1 + s[k])
    selp, nsel = m.u32(at('SELP')), m.u16(at('NSEL'))
    me = [selp + 0x2AC * i for i in range(nsel) if m.u16(selp + 0x2AC * i) == sel][0]
    pl = bytes(m.u8(me + 0x6C + 0x26 * j) for j in range(16))
    mem = m.read(m.base2, 0x200000)
    ct = [m.base2 + i for i in range(len(mem) - 0x26 * 16)
          if all(mem[i + 0x26 * j] == pl[j] for j in range(16)) and m.base2 + i != me + 0x6C]
    assert ct, 'careerTeam not found'
    return ct[0]


def test_sella_buyers():
    ks = _snaps()
    if not ks:
        return False, f'no sl_try fixture in {FIX}'
    s = _sites()
    o2 = lambda m, t: m.base2 + t[1]
    stats, bad, use = {}, [], {}
    for k in ks:
        for pool in ('dom', 'fgn'):                     # (a fresh machine per pool: Unicorn keeps translated code, so
            m = Machine(FIX, k)                         #  the pool draw's jb is patched before the first call)
            n_, mg, ring, rule = m.read('sella.SL_PARM', 4)
            regs = m.read(o2(m, (2, s['d0'])), 15 * 4)
            sel = m.u16(o2(m, s['SEL']))
            jb = m.base1 + s['POOL_JB']
            orig_jb = m.read(jb, 6)
            m.write(jb, b'\x90' * 6 if pool == 'dom' else
                    b'\xe9' + struct.pack('<i', struct.unpack('<i', orig_jb[2:])[0] + 1) + b'\x90')
            lst = m.u32(m.base1 + s['BUF'])              # (the candidate list as the exe uses it)
            cap = CAP if lst == m.base2 + LIST_ORIG else m.u16('sella.SL_CAP')
            guard = m.read(lst + cap, GUARD)
            ct = _career_team(m, s, sel)
            keep = m.read(ct, 1)
            u = use.setdefault(pool, [0, 0, 0, 0])      # (list bytes used, value, rule A's drops at that value, drops)
            for val in range(50):                       # (every price byte for our player 0: the list's real use -
                m.write(ct, bytes([val]))               #  fill bytes, then the highest one written - and rule A's drops)
                m.write(o2(m, (2, s['d0'])), regs)
                m.write(o2(m, (2, s['d0'] + 4)), b'\0\0')
                m.write(o2(m, s['NOFF']), b'\0\0')
                m.write(lst, b'\xee' * cap)
                dr = m.u32('sella.SL_DROP')
                m.call('sella.sl_try')
                b = m.read(lst, cap)
                n = max([i + 1 for i in range(cap) if b[i] != 0xEE] or [0])
                dr = m.u32('sella.SL_DROP') - dr
                u[3] += dr
                if n + dr > u[0] + u[2]:
                    u[:3] = [n, val, dr]
                if m.read(lst + cap, GUARD) != guard:
                    bad.append((k, pool, f'v{val}: candidate list written past its {cap} bytes'))
                    m.write(lst + cap, guard)
            m.write(ct, keep)
            rnd = random.Random(k)
            st = stats.setdefault(pool, dict(tries=0, offers=0, vals=set()))
            for i in range(SEEDS):
                m.write(o2(m, (2, s['d0'])), regs)
                m.write(o2(m, (2, s['d0'] + 4)), struct.pack('<H', rnd.randrange(16)))   # D1 = a player index
                for a in s['RNG']:
                    m.write(m.base2 + a, bytes(rnd.randrange(256) for _ in range(3)))
                m.write(o2(m, s['NOFF']), b'\0\0')
                made = m.u32('sella.SL_MADE')
                m.call('sella.sl_try')
                st['tries'] += 1
                if m.read(lst + cap, GUARD) != guard:
                    bad.append((k, pool, i, f'candidate list written past its {cap} bytes'))
                    m.write(lst + cap, guard)
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
                if (rec[0] == sel & 0xFF) != (pool == 'dom'):      # (byte 0: the team file - a world's division)
                    why.append(f'file {rec[0]} in the {pool} pool')
                if rule and _above(rec, val, mg) >= n_:
                    why.append(f'{_above(rec, val, mg)} above v{val}+{mg}')
                if why:
                    bad.append((k, pool, rec[5:22].split(b'\0')[0].decode('latin-1'), val, why))
    msg = (f'fixtures {ks}, N {n_} margin {mg} rule {rule}; ' +
           ', '.join(f'{p}: {v["tries"]} tries {v["offers"]} offers values {sorted(v["vals"])}' for p, v in stats.items()) +
           '; candidate list (' + f'{cap} B, byte indices): ' +
           ', '.join(f'{p} up to {u[0]} used (value {u[1]}; rule A dropped {u[2]} more there, {u[3]} over values 0-49)'
                     for p, u in use.items()) + f'; bad {bad[:6]}')
    ok = not bad and all(v['offers'] for v in stats.values())
    return ok, msg
