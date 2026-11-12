"""A booked player on a carried yellow can be substituted (4.2, Marco's bug, backlog-42 row 44 point 4).

The in-match card state, PlayerInfoHeader.cards (+34h): InitInGamePlayer starts it from the player's record
(PlayerFile.cardsInjuries bits 2-4: 0 clean, 1 one yellow carried over, 2..4 banned; plg_D3_param is always 0 in the
original - its source dseg_10EEE4 is never written - so every match, league or cup, takes this branch) and keeps that
start in previousCards. TryBookingThePlayer then takes the new value from dseg_17E3EE {0, 1, 3, 3, 3} (clean) or, with
a carried yellow (previousCards != 0), dseg_17E3F3 {1, 2, 4, 4, 4}, indexed by the match's yellows + 1: a carried yellow
plus a first booking = 2 ("banned for the next match"), and he stays ON the pitch; 3 / 4 = sent off.

The subs menu treats the PITCH player's cards >= 2 as "sent off", so that player is never offered again: a cup
tie's 1st-leg yellow is carried into the 2nd leg (the same record), and a booking there leaves him unsubstitutable
for the rest of the match (Marco, 12/11; the same in a league after a yellow). The three checks on the player LEAVING
the pitch become cards >= 3 (really sent off):
- IsPlayerOkToSubstitute (UpdateSubstitutePlayerIndices: the cursor moves only onto players it takes),
- FindInitialPlayerToBeSubstituted (the menu's first choice of the player to take off),
- MarkPlayersMenuHandler (the man-marking choice of the same pitch player).
(The fire that makes the change checks nothing more: the menu just never lands on him.)
The BENCH checks stay >= 2 - IsThisPlayerOkToSelect, FirePressedInSubsMenu, DrawBenchPlayersAndCoach: there 2 at
kick-off means banned, and a banned player still cannot come on. The card values themselves are unchanged (the ban
after the match is the game's own). Three imm8 bytes, no code, no room.

Not changed (reported to Regia, 12/11): BumpPlayerLastPlayedHalfAtHalfStart / End also skip cards >= 2, so a player on
2 does not get his halves counted in halfPlayed.
"""
import re

SITES = {                                         # name: (pattern, offset of the imm8 in the match)
    'IsPlayerOkToSubstitute': (rb'\x80\x7e\x34\x02\x73\x24\x66\x83\x3d....\x03\x75', 3),   # cmp [g_subsState], 3
    'FindInitialPlayerToBeSubstituted': (rb'\xe8\x1b\x02\x00\x00\x8b\x35....\x80\x7e\x34\x02\x0f\x83\xda\x00\x00\x00',
                                         14),    # call GetBenchPlayerPointer / mov esi, [A0]
    'MarkPlayersMenuHandler': (rb'\x80\x7e\x34\x02\x73\x5a\x66\x83\x3d....\x08\x75', 3),   # cmp [subsFireTimer], 8
}


def sites(d):
    """{name: obj1 offset of the imm8 2} in obj1 bytes d (the original exe's, every language)."""
    out = {}
    for name, (pat, k) in SITES.items():
        m = [x.start() for x in re.finditer(pat, d, re.S)]
        assert len(m) == 1, (name, len(m))
        out[name] = m[0] + k
    assert len(re.findall(rb'\x80\x7e\x34\x02', d)) == 10, 'cmp byte [esi+34h], 2: not the 10 of the original'
    return out


def patch(p):
    d = p.le.obj_bytes(1)
    for name, at in sites(d).items():
        assert p.get(1, at - 3, 4) == b'\x80\x7e\x34\x02', (name, p.get(1, at - 3, 4).hex())
        p.put(1, at, b'\x03')
    print('exe: a booked player on a carried yellow can be substituted (pitch-player checks cards >= 3, 3 sites)')
