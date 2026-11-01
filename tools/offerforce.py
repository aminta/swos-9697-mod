"""OFFER_FORCE (test builds only, 4.0.5): every transfer offer accepted at the offered amount. The club's answer
(cseg_584D7, PlayerOffersOnSelect12's) compares the offer with its asked value, seeded by the players and the game's
running state (a pair's asked value moves from career to career): `mov ax,[D5]; cmp [D6],ax; jnb accept` - with
OFFER_FORCE=1 the jnb is a jmp (accept: teamWillingToSellOrExchange 0). The harness's way to complete a 2-player
deal every run (xtra_offer_plus)."""
import os
import re
import struct

import sacups


def patch(p):
    if not os.environ.get('OFFER_FORCE'):
        return
    d = p.le.obj_bytes(1)
    D0 = sacups.regs(d)['D7'] - 28
    pt = lambda a: re.escape(struct.pack('<I', a))
    hits = list(re.finditer(rb'\x66\xa1' + pt(D0 + 20) + rb'\x66\x39\x05' + pt(D0 + 24) + rb'\x0f\x83(....)', d, re.S))
    assert len(hits) == 1, len(hits)
    o = hits[0].end() - 6
    tgt = o + 6 + struct.unpack('<i', hits[0].group(1))[0]
    assert bytes(p.get(1, o, 6)) == d[o:o + 6], 'OFFER_FORCE site already patched'
    p.put(1, o, b'\xe9' + struct.pack('<i', tgt - (o + 5)) + b'\x90')
    print(f'exe: OFFER_FORCE (test build: every offer accepted) obj1+{o:#x}')
