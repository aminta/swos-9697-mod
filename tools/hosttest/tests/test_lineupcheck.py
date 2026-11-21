"""4.2 lineupcheck, real line-ups (Regia 21/11): a lineup_src 'real' club is checked for its STRUCTURE only (XI = rows
1..11, the keeper in slot 1 and no other keeper in the XI, a game tactic), the roles are lineups_gate's (match-sheet
roles a team file does not hold). The control's red twins (each broken structure FAILs for its reason, a namesake in
another team file is not real) and, when the 4.2 rc data is here, the same on real records: the 12 Italian clubs whose
TM position bytes do not fit their (real) tactic PASS, and ROMA with its keeper moved out of slot 1 FAILs."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import lineupcheck

REL = os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', os.environ.get('LUCHECK_REL', 'REL42rc3'), 'SWOS', 'DATA')
TWELVE = ('ROMA', 'MILAN', 'UDINESE', 'EMPOLI', 'PALERMO', 'SASSUOLO', 'CATANZARO', 'MODENA', 'MANTOVA', 'CARRARESE',
          'SUDTIROL', 'PISA')


def test_lineupcheck_real():
    lineupcheck.control()
    f = os.path.join(REL, 'TMW5.102')
    if not os.path.exists(f):
        return True, f'control (red twins + namesake) PASS; real records not checked: no {f}'
    b = open(f, 'rb').read()
    recs = {b[2 + 684 * i + 5:2 + 684 * i + 22].split(b'\0')[0].decode('latin1'): i for i in range(struct.unpack('>H', b[:2])[0])}
    real = {(102, n) for n in TWELVE}
    w = lineupcheck.check_file(b, real=real)[4]
    bad = [x for x in w if x[1] in TWELVE]
    if bad:
        return False, f'real clubs flagged: {bad}'
    t = bytearray(b)
    o = 2 + 684 * recs['ROMA'] + 60
    t[o], t[o + 1] = t[o + 1], t[o]                   # (ROMA: keeper out of slot 1)
    w = [x for x in lineupcheck.check_file(bytes(t), real=real)[4] if x[1] == 'ROMA']
    if not w or 'no keeper in slot 1' not in w[0][2]:
        return False, f'ROMA with its keeper out of slot 1 was not flagged: {w}'
    return True, f'control PASS; {REL}: the 12 real clubs PASS, ROMA keeper-out-of-slot-1 FAILs ({w[0][2]})'


if __name__ == '__main__':
    print(test_lineupcheck_real())
