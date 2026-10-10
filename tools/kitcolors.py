"""Automatic home/away kit choice (SetInGameTeamsPrimaryColors / GetTeamKitsSimilarityFactor).

The game scores how alike two kits look (5 or 2 points for each pair of clashing colours) and uses the first of
home-home, home-away, away-home, away-away that scores below 11. Many classic pairings never met in home kits
(Juventus-Milan, Milan-Inter, Inter-Juventus, Chelsea against Juventus, Newcastle or Manchester City).
Analysis of the colour adjacency graph: Daniele Bordes (DaniSwos), SWOS United forum thread "Home-Away kit
automatic selection". Variants tested on every same-country pairing with tools/kitsim.py (variant 'C').

Changes (all four languages, found by byte content):
 1. conflict tables (conflictingBasicTeamColorsTable, conflictingShortsTeamColorsTable): black no longer clashes
    with blue or green, blue no longer with light blue (far apart in the in-game palette, pal.256);
 2. GetTeamKitsSimilarityFactor bug: after the stripe-merge pass (a striped shirt checked again as its blended
    colour, e.g. red+black -> maroon) the loop start tests D0/D4, which then hold the 'converted' flags, not the
    shirt types, so the other striped team lost its stripes (Inter became all black). The two tests now read
    shirtType1/shirtType2 (same on the first pass);
 3. same-coloured shorts on both teams weigh 3 instead of 5.
"""
import re
import struct

import kitsim

TABLE_BYTES = 20


def patch(p):
    # 1. conflict tables (obj2)
    d2 = p.le.obj_bytes(2)
    new = kitsim.variants()['C']
    for old, rows in ((kitsim.BASIC, new.basic), (kitsim.SHORTS, new.shorts)):
        b = struct.pack('<10H', *old)
        at = d2.find(b)
        assert at >= 0 and d2.count(b) == 1, 'kit colour table'
        assert p.get(2, at, TABLE_BYTES) == b
        p.put(2, at, struct.pack('<10H', *rows))

    # 2. GetTeamKitsSimilarityFactor prologue:
    #    mov al,[D0]; mov [shirtType1],al; mov al,[D4]; mov [shirtType2],al
    #    cmp byte [D0],0; jnz; mov al,[D1]; mov [D2],al; cmp byte [D4],0; jnz
    d1 = p.le.obj_bytes(1)
    pat = re.compile(rb'\xA0....\xA2....\xA0....\xA2....\x80\x3D....\x00\x75.\xA0....\xA2....\x80\x3D....\x00\x75', re.S)
    hits = [m.start() for m in pat.finditer(d1)]
    assert len(hits) == 1, 'GetTeamKitsSimilarityFactor'
    o = hits[0]
    assert p.get(1, o, 4) == d1[o:o + 4]
    for cmp_at, st_at, d_at in ((o + 22, o + 6, o + 1), (o + 41, o + 16, o + 11)):
        assert p.target(1, cmp_at) == p.target(1, d_at)            # cmp byte [D0|D4], 0
        tobj, toff = p.target(1, st_at)                           # shirtType1|2
        p.retarget(1, cmp_at, tobj, toff)
        p.put(1, cmp_at, struct.pack('<I', toff))

    # 3. the last 'add similarityFactor, n' of the no-conflict sum (D3 vs D7: shorts vs shorts)
    sim = None
    adds = []
    for m in re.finditer(rb'\x66\xC7\x05....\x63\x00', d1[o:o + 0x200], re.S):   # mov similarityFactor, 99
        sim = p.target(1, o + m.start() + 3)
        break
    assert sim
    for m in re.finditer(rb'\x66\x83\x05....(.)', d1[o:o + 0x600], re.S):
        at = o + m.start()
        try:
            t = p.target(1, at + 3)
        except AssertionError:      # look-alike bytes without a fixup
            continue
        if t == sim:
            adds.append(at)
    imms = [d1[a + 7] for a in adds]
    assert imms == [1, 5, 5, 2, 5, 5, 2, 2, 2, 5], imms
    p.put(1, adds[-1] + 7, bytes([new.wshorts]))
