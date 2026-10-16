"""Career weeks read unsigned in the job-offer timing (3.2.7, Pietro).

Two career routines (the job offers, cseg_3CCF0 and cseg_5B705 in swos.asm) time the season in quarters:
`(current week [E0048] - first week [DB3E6+1]) * 4 / (last week - first week)`, with the week difference read as a
SIGNED byte (`cbw`) and divided by a word `div` (DX:AX). The game's own calendars stay below week 128, but a career
whose season events include one of the mod's added club cups outside its continent's calendar (an Indian club in the
Asian Club Championship: rounds at weeks 0x40..0x80) reaches week 128 -> -128 * 4 = -512 -> FFFF:FE00 / span = divide
overflow -> DOS/4GW page-fault exit at the season end (FINISCI STAGIONE). `cbw` (66 98) becomes `xor ah, ah` (32 E4):
the same value for weeks below 128, the right one up to 255.
"""
import re


def patch(p):
    d1 = p.le.obj_bytes(1)
    pat = rb'\xa0....\xa2....\xa0....\x28\x05....\xa0....(\x66\x98)\x66\xa3....\x66\xc1\x25....\x02'
    sites = [m.start(1) for m in re.finditer(pat, d1, re.S)]
    assert len(sites) == 2, [hex(s) for s in sites]
    for s in sites:
        assert p.get(1, s, 2) == b'\x66\x98'
        p.put(1, s, b'\x32\xe4')
    print(f"exe: career weeks unsigned in the job-offer timing (obj1+{sites[0]:#x}, +{sites[1]:#x})")
