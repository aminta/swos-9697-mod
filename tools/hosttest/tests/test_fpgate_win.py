"""4.2 fixture port P5 (MC 15/11): the control of world_fport_ld_win's addq rule (fpgate.win_errs). The real logs of
the final tree's run (engine 52301fb, -Oz, FPORT2 0x1D400): addq and rem pass; addq with 107 wrongly installed as a
real fixture (an INST planted in place of the REFUSED / SIM), or with no SIM, must FAIL; rem with 107 simulated must FAIL."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import fpgate

ADDQ = [('LOAD', 100, 0, 0, 126), ('PLOAD', 100, 3, 0, 1), ('REVAL', 100, -16, 32258, 1), ('MISSED', 100, 0, 0, 0),
        ('LEG', 103, 1, 103, 257), ('LEGX', 103, 1, 65535, 65535), ('RES', 103, -2, 32257, 65025),
        ('REFUSED', 106, -16, 0, 0), ('SIM', 106, 0, 32258, 18), ('RES', 106, -2, 32258, 65024),
        ('MISSED', 106, 1, 0, 0)]
REM = [('LOAD', 100, 0, 0, 126), ('PLOAD', 100, 3, 0, 1), ('REVAL', 100, 0, 0, 0), ('LEG', 103, 1, 103, 257),
       ('LEGX', 103, 1, 65535, 65535), ('RES', 103, -2, 32257, 65025), ('INST', 106, 1, 32258, 27499),
       ('LEG', 107, 0, 359, 3), ('LEGX', 107, 0, 65535, 65535), ('RES', 107, -2, 32258, 65024)]
# addq, 107 wrongly installed: the REFUSED / SIM replaced by rem's INST + legs (the same RES)
ADDQ_INST = ADDQ[:7] + REM[6:9] + [ADDQ[9], ADDQ[10]]
ADDQ_INST_SIM = ADDQ[:7] + [ADDQ[7], REM[6]] + ADDQ[8:]          # (installed AND simulated)
ADDQ_NOSIM = ADDQ[:8] + ADDQ[9:]


def test_fpgate_win_addq_control():
    cases = [('addq', ADDQ, True), ('rem', REM, True), ('addq', ADDQ_INST, False), ('addq', ADDQ_INST_SIM, False),
             ('addq', ADDQ_NOSIM, False), ('rem', ADDQ, False)]
    out = []
    for i, (how, log, want) in enumerate(cases):
        e = fpgate.win_errs(how, log)
        if (not e) != want:
            return False, f'case {i} ({how}, want {"PASS" if want else "FAIL"}): errors {e}'
        out.append(f'{i}:{"PASS" if not e else "FAIL"}')
    return True, 'real addq / rem PASS; planted INST, INST + SIM, no SIM, rem rule on addq: FAIL (' + ' '.join(out) + ')'
