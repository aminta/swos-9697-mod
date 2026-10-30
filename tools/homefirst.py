"""4.0.5 (Davide): the career fixture list (CareerGameListCommon: the career menu's list) shows the HOME team first,
as real fixture lists do, with its score first ('FIORENTINA 2 - 1 INTER' and the (A) column for an away match).

A list row's record holds the home team (+12), the away team (+14) and their goals (+16, +17); the routine draws them
in that order unless cglm_team_control is -1, which it sets when the away team is not the computer's (the career
club away): then it swaps both names and both scores so that the career club comes first. The `mov byte [D0], -1`
that sets it becomes 7 nops (its fixup removed): cglm_team_control stays 0, every row home first; the (H) / (A)
column (+10), the rows' other strings and the mod's hooks of the routine (gplay gp_scgl, rnames, the D8CAA label)
are untouched.
"""
import re
import struct

import sacups


def find(p):
    d1 = p.le.obj_bytes(1)
    D0 = sacups.regs(d1)['D7'] - 28
    P = lambda a: re.escape(struct.pack('<I', a))
    # cmp byte [esi + teamControls], 1; mov word [D0], 0; jz @@computer_team; mov byte [D0], -1; mov al, [D0]; cbw
    m = [x.start() for x in re.finditer(rb'\x80\x7e.\x01\x66\xc7\x05' + P(D0) + rb'\x00\x00\x74.\xc6\x05' + P(D0) +
                                        rb'\xff\xa0' + P(D0) + rb'\x66\x98', d1, re.S)]
    assert len(m) == 1, ('CareerGameListCommon cglm_team_control', m)
    return m[0] + 15


def patch(p):
    at = find(p)
    assert p.get(1, at, 2) == b'\xc6\x05'
    p.remove(1, at + 2)
    p.put(1, at, b'\x90' * 7)
    print(f'exe: career fixture list home team first: obj1+{at:#x}')
