"""4.2 beta repair tools/fixnames.py (Davide's MiSTer 19/11: joyname typed 05h with a pad): every name field of every
team loses its 05h bytes, nothing else changes, a clean file stays byte-identical, a second run changes nothing.
Red twin: a fixer that only looks at the players' names leaves the coach's 05h."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import fixnames  # noqa: E402


def team(name, coach, players):
    r = bytearray(fixnames.REC)
    r[5:5 + len(name)] = name
    r[36:36 + len(coach)] = coach
    for i, p in enumerate(players):
        o = 76 + 38 * i
        r[o + 2] = i + 1
        r[o + 3:o + 3 + len(p)] = p
        r[o + 26:o + 33] = bytes([0x40, 0, 0x12, 0xf3, 0x05, 0x35, 0x23])   # (05h in the skills: not a name, kept)
    return bytes(r)


CLEAN = [b'GIANLUCA PAGLIUCA', b'ANDREA MAZZANTINI', b'MARCO BRANCA'] + [b'P%d' % i for i in range(13)]
DIRTY = [b'GIANLUCA PAGLIUCA' + b'\x05' * 5, b'ANDREA MAZZANTINI' + b'\x05' * 5, b'MARCO BRANCA' + b'\x05' * 5] + \
    [b'P%d' % i for i in range(13)]


def file_(*teams):
    return bytes([0, len(teams)]) + b''.join(teams)


def test_fixnames_strips_05_only_in_names():
    good = team(b'INTER', b'ROY HODGSON', CLEAN)
    bad = team(b'INTER\x05', b'ROY\x05 HODGSON', DIRTY)
    other = team(b'90 MINUTES XI', b'DAVIDS', [b'HERMAN FESTERS'] * 16)
    fixed, log = fixnames.fix_file(file_(other, bad, other))
    assert fixed == file_(other, good, other), [i for i in range(len(fixed)) if fixed[i] != file_(other, good, other)[i]][:8]
    assert len(log) == 5 and {x[2] for x in log} == {'team', 'coach', 'player 0', 'player 1', 'player 2'}, log
    again, log2 = fixnames.fix_file(fixed)
    assert again == fixed and not log2


def test_fixnames_clean_file_identical():
    d = file_(team(b'INTER', b'ROY HODGSON', CLEAN), team(b'MILAN', b'TABAREZ', CLEAN))
    assert fixnames.fix_file(d) == (d, [])


def test_fixnames_red_twin_players_only():
    """the twin: a fixer limited to the players' fields leaves the coach's 05h - this test's check catches it"""
    bad = file_(team(b'INTER', b'ROY\x05 HODGSON', DIRTY))
    good = file_(team(b'INTER', b'ROY HODGSON', CLEAN))
    players = [f for f in fixnames.FIELDS if f[0].startswith('player')]
    assert fixnames.fix_file(bad, players)[0] != good
    assert fixnames.fix_file(bad)[0] == good
