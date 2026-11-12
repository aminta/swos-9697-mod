"""4.1.2 zone positions (MC's condition 4): gplay.c gp_stwins_c - the stage titles the career club won this season, for
the season-end opinion in a league in zones (split.py zp_bonus: -2 each) - every title kind forced on synthetic
GP_ST.dec slots, none left to a season's luck.

Fixture zp_stwins_pan: world_zone_pan_titles (VERAGUAS UNITED, Panama, zone 2) on a HOSTTEST_SYMS=1 build of
412-zonepos with GPLAY_KOFORCE=2 (exe = the zonepos_wk2 build byte for byte), HT_SNAP_LABELS=gplay.csyms.gp_stwins_c:
the snapshot at zp_bonus's call (the season-end opinion), with the Clausura knockout still live in ko[0] and WON by
the club (the game's own club_res; GP_RLFORCE is a compile-time switch, so the live case must be a real one).

Cases (gp_dec: season, done, pad[0] = the club's result (1 = won), pad[1] = play-off index + 1):
- ko[0] off: dec[0] / dec[1] / dec[2] won one at a time (Apertura / Clausura / Trofeo) -> 1 each; all three -> 3;
  decided but not won (0 / -100), another season, not done, no play-off -> 0;
- ko[0] live (the snapshot's): alone -> 1; plus each dec slot won in turn -> 2, except the live stage's own slot
  (skipped, not counted twice) -> 1, exactly one such slot; all three slots won -> 3;
- a club not among the live knockout's entrants (club_res 0): the dec slots only (0, then 1 with one slot won)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from emu import Machine  # noqa: E402

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures', 'zp_stwins_pan')
DEC, KO, KOSZ = 0x7cc, 0x288, 0x2a2     # offsetof(struct gp_state, dec / ko), sizeof(struct gp_ko) (clang i686)
K_KIND, K_N, K_TEAM = 6, 7, 0x1da
MAGIC, K_STAGE = 0x4B47, 8
ST = 'gplay.csyms.GP_ST'


def _decs(m, decs):
    m.write(ST, b''.join(struct.pack('<BBbB4H', *(d or (0, 0, 0, 0)), 0, 0, 0, 0) for d in decs), DEC)


def test_stwins():
    if not os.path.isdir(FIX):
        return True, f'SKIP: fixture {FIX} missing'
    m = Machine(FIX, 0)
    seas = m.read('gplay.csyms.GP_SEAS', 1)[0]
    if struct.unpack('<H', m.read(ST, 2))[0] != MAGIC or m.read(ST, 1, 2)[0] != seas:
        return False, 'GP_ST not live in the snapshot'
    ko = m.read(ST, KOSZ, KO)
    if not (struct.unpack_from('<H', ko)[0] == MAGIC and ko[2] == seas and ko[K_KIND] == K_STAGE):
        return False, f'ko[0] is no live stage knockout in the snapshot (kind {ko[K_KIND]})'
    teams = list(struct.unpack_from(f'<{ko[K_N]}H', ko, K_TEAM))
    mgr = 0x3b2                         # (VERAGUAS UNITED's team number: selTeamNumber in the world_zone_pan_titles runs)
    if mgr not in teams:
        return False, f'the club {mgr:#x} is not in the live knockout {[hex(t) for t in teams]}'
    other = next(t for t in range(0x1b2, 0xcb2, 0x100) if t not in teams)
    won = (seas, 1, 1, 1)
    bad, out = [], []

    def case(name, decs, live, who, want):
        _decs(m, decs)
        m.write(ST, ko if live else b'\0\0', KO)
        got = m.call('gplay.csyms.gp_stwins_c', who)
        out.append(f'{name} {got}')
        if want is not None and got != want:
            bad.append(f'{name}: {got}, expected {want}')
        return got
    case('none', [None] * 3, 0, mgr, 0)
    for s, nm in enumerate(('Apertura', 'Clausura', 'Trofeo')):
        case(f'{nm} won', [won if i == s else None for i in range(3)], 0, mgr, 1)
    case('all three won', [won] * 3, 0, mgr, 3)
    case('decided, not won', [(seas, 1, 0, 1), (seas, 1, -100, 1), (seas, 1, -101, 1)], 0, mgr, 0)
    case('another season', [((seas - 1) & 0xff, 1, 1, 1), None, None], 0, mgr, 0)
    case('not done', [(seas, 0, 1, 1), None, None], 0, mgr, 0)
    case('no play-off', [(seas, 1, 1, 0), None, None], 0, mgr, 0)
    case('live won', [None] * 3, 1, mgr, 1)
    own = [case(f'live + slot {s}', [won if i == s else None for i in range(3)], 1, mgr, None) for s in range(3)]
    if sorted(own) != [1, 2, 2]:
        bad.append(f'live + one slot: {own}, expected one 1 (the live stage\'s own slot) and two 2')
    case('live + all three slots', [won] * 3, 1, mgr, 3)
    case('club not in the live knockout', [None] * 3, 1, other, 0)
    s2 = own.index(2) if 2 in own else 1    # (a slot of another stage: the live stage's own is skipped for any club)
    case('club not in it + one slot', [won if i == s2 else None for i in range(3)], 1, other, 1)
    return not bad, '; '.join(bad) or f'{len(out)} cases (live stage = slot {own.index(1)}): ' + ', '.join(out)
