"""4.2 the season start's euro-cup term for the other confederations' cups (uprize.c up_eurc / ct_term; Davide 11/11
"1b 2 consigliato"), on the static image of HT_CBONUS_EXE (default c/HTW: the release-recipe exe with HOSTTEST_SYMS=1 that tools/hosttest/mkfixtures.sh builds from this checkout; before 16/11 the private fixture c/HTcbS, which no script made).

cseg_5DEB9's `mov eax, [D8CB6]` calls up_eur(c): its value decides the game's own term (DA111 x the factor of
D8CBE's kind, / 1000 x 1000, into competitionBonuses). For every conti cup, in its own contest (E092F = CT_D7 + its
struct) and in the ties' contest (E092F = CT_D7 + CT_NS, CT_SEG's cup), ANDAMENTO CLUB's switch ON (a league-phase
world) and OFF:
- up_eurc returns 0 (the game's own term skipped) and adds the term itself: the 1st cup of a confederation the
  Champions Cup's factor (100,022), the 2nd the UEFA Cup's (83,336), the others per uprize.THIRD; the game's own
  arithmetic (16-bit x, a 16-bit quotient);
- the Intercontinental (ties only) and the cups of tier 3: nothing;
the UEFA cups (E092F 0..2) and uefaq's qualifying ties (D7 below CT_D7): unchanged - ON 0 (uprize's prizes instead),
OFF D8CB6 (the game's term), competitionBonuses untouched; D8CB6 0: 0 and nothing paid; DA111 0: nothing paid.
The expected terms are computed by the ORIGINAL exe's own code (cseg_5DEB9's term, run in its image for kinds 0 / 2 /
1), not by a formula of ours."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_champ as tc  # noqa: E402
import test_registry as tr  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_CBONUS_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTW', 'SWOS', 'ITALIAN.EXE')
ORIG = os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE')
KIND = {0: 0, 1: 2, 2: 1}                       # uprize.c's tier -> the game's D8CBE kind (0 CC, 2 UEFA, 1 CWC)


def game_terms(xs):
    """{(x, kind): the term} by the original exe's cseg_5DEB9 (from `mov al, [DA111]` to its `add [CBON], eax`)."""
    import re
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from le import LE
    o1 = LE(open(ORIG, 'rb').read()).obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xa1(.{4})\x0b\xc0\x0f\x84.{4}\xa0', o1, re.S)]
    m = [k for k in m if o1[k + 13:k + 18].hex()[:2] == 'a0' and o1.find(b'\x01\x05', k, k + 0xE0) > 0]
    assert len(m) == 1, m
    s = m[0] + 13
    e = o1.find(b'\x01\x05', s, s + 0xE0)       # add [competitionBonuses], eax
    code = o1[s:e]
    da111, = struct.unpack_from('<I', o1, s + 1)
    kind_at, = struct.unpack_from('<I', o1, s + 0x1A)           # cmp word [D8CBE], 1
    out = {}
    for x in xs:
        for kind in (0, 1, 2):
            uc = Uc(UC_ARCH_X86, UC_MODE_32)
            uc.mem_map(0, 0x100000)             # (obj2's absolute offsets as flat addresses)
            uc.mem_map(0x1000000, 0x1000)
            uc.mem_write(0x1000000, code)
            uc.mem_write(da111, bytes([x & 0xFF]))
            uc.mem_write(kind_at, struct.pack('<H', kind))
            uc.emu_start(0x1000000, 0x1000000 + len(code))
            from unicorn.x86_const import UC_X86_REG_EAX
            out[(x, kind)] = uc.reg_read(UC_X86_REG_EAX)
    return out


def test_cbonus():
    syms = EXE[:-4] + '.syms.json'
    if not os.path.exists(EXE) or not os.path.exists(syms):
        return False, f'{EXE} / its .syms.json missing (HT_CBONUS_EXE)'
    j = json.load(open(syms))
    u, cw = j.get('uprize', {}), j.get('careerworld', {})
    if 'CT_D7' not in u:
        return False, 'no conti term in this exe (uprize CT_D7)'
    uc, le, rd = tc.static_machine(EXE)
    base = {0: tr.B1, 1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}
    at = lambda v: base[v[0]] + v[1]
    fn = at(u['up_eurc'])
    d7, ns = u['CT_D7'][1], u['CT_NS'][1]
    tiers = [u[f'CT_TIER{i}'][1] for i in range(64) if f'CT_TIER{i}' in u]
    scup = [u[f'CT_SCUP{i}'][1] for i in range(ns)]
    X = {k: at(u['X.' + k]) for k in ('E092F', 'CT_SEG', 'DA111', 'D8CB6', 'CBON', 'GAMETYPE')}
    off = at(u['UP']) + 4 + 7                   # (struct up's off: ANDAMENTO CLUB's switch, 1 = OFF)
    w_lpw = at(cw['w_lpw'])
    keep = rd(w_lpw, 3)
    xs = (19, 1, 127)
    terms = game_terms(xs + (0,))
    sample = {k: terms[(19, k)] for k in (0, 2, 1)}
    if sample != {0: 1_900_000, 2: 1_583_000, 1: 1_190_000}:    # (DA111 19: 19 x 100,022 / 83,336 / 62,644)
        return False, f'the original term: {sample}'
    errs, n = [], 0
    CB0 = 485_000

    def run(e092f, x, sw, cup=0, d8=0x35A000):
        uc.mem_write(X['E092F'], struct.pack('<H', e092f))
        uc.mem_write(X['CT_SEG'], bytes([cup]))
        uc.mem_write(X['DA111'], bytes([x & 0xFF]))
        uc.mem_write(X['D8CB6'], struct.pack('<I', d8))
        uc.mem_write(X['CBON'], struct.pack('<i', CB0))
        uc.mem_write(X['GAMETYPE'], struct.pack('<H', 4))
        uc.mem_write(off, bytes([sw == 'OFF']))
        uc.mem_write(w_lpw, b'\x38\xc0\xc3')    # (cmp al, al; ret: ZF 1 - a league-phase world)
        r = tr._call(uc, fn) & 0xFFFFFFFF
        return r, struct.unpack('<i', rd(X['CBON'], 4))[0] - CB0

    def want(tier, x):
        return 0 if tier > 2 else terms[(x, KIND[tier])]

    for sw in ('ON', 'OFF'):
        for i in range(ns):                     # each cup's own contest
            for x in xs:
                r, got = run(d7 + i, x, sw)
                n += 1
                if (r, got) != (0, want(tiers[scup[i]], x)):
                    errs.append(f'{sw} contest {i} (cup {scup[i]}, tier {tiers[scup[i]]}) x {x}: {r:#x} +{got}')
        for ci, t in enumerate(tiers):          # the ties' contest, CT_SEG's cup (the Intercontinental's too)
            r, got = run(d7 + ns, 19, sw, ci)
            n += 1
            if (r, got) != (0, want(t, 19)):
                errs.append(f'{sw} ties cup {ci} (tier {t}): {r:#x} +{got}')
        r, got = run(d7, 0, sw)
        n += 1
        if (r, got) != (0, 0):
            errs.append(f'{sw} DA111 0: {r:#x} +{got}')
        for e in [0, 1, 2] + list(range(6, d7)):   # UEFA: its cups, uefaq's ties (and older chains' contests)
            r, got = run(e, 19, sw)
            n += 1
            if (r, got) != ((0 if sw == 'ON' else 0x35A000), 0):
                errs.append(f'{sw} UEFA E092F {e}: {r:#x} +{got}')
        for e in (0, d7, d7 + ns):              # D8CB6 0: no cup in slot 3
            r, got = run(e, 19, sw, d8=0)
            n += 1
            if (r, got) != (0, 0):
                errs.append(f'{sw} D8CB6 0, E092F {e}: {r:#x} +{got}')
    uc.mem_write(w_lpw, keep)
    first = {t: sum(1 for x in tiers if x == t) for t in range(4)}
    return not errs, '; '.join(errs[:6]) or (
        f'{n} cases: {ns} conti contests + the ties\' contest x {len(tiers)} cups (tiers CC {first[0]}, UEFA '
        f'{first[1]}, CWC {first[2]}, none {first[3]}) x ON/OFF: 0 returned, the original exe\'s own term paid '
        f'(DA111 19: CC {sample[0]:,}, UEFA {sample[2]:,}, CWC {sample[1]:,}); UEFA E092F 0..2 + 6..{d7 - 1} unchanged '
        '(ON 0, OFF D8CB6, nothing paid); D8CB6 0 / DA111 0: nothing')
