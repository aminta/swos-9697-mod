"""4.2 tacgate (Shaved / MC 15/11): game_copies finds only the game's loaded copies of a DATA club record (+2 word
little-endian, +4 = 0 / 1), never the raw file buffer (big-endian word), and copy_diffs catches one corrupted copy
among several - the tactic in the last copy, a lineup byte in the first - while clean copies give none."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import tacgate as g


def _rec(tac=3, lu=bytes(range(16))):
    r = bytearray(684)
    r[0:2], r[2:4], r[4] = b'\x00\x01', b'\x01\x02', 9          # (the file: word 0x0102 big-endian)
    r[5:22] = b'NAPOLI'.ljust(17, b'\0')
    r[24], r[60:76] = tac, lu
    return bytes(r)


def _copy(w, second):
    c = bytearray(w)
    c[2:4], c[4] = w[3:1:-1], second                               # (the game: little-endian, +4 = 0 / 1)
    return c


def test_tacgate_copies():
    w = _rec()
    copies = [_copy(w, 0), _copy(w, 1), _copy(w, 1)]
    bad4 = _copy(w, 7)                                             # (+4 not 0 / 1: not a game copy)
    gap = b'\xee' * 37

    def mem(cs):
        return b'\xcc' * 64 + w + gap + gap.join(bytes(c) for c in cs) + gap + bytes(bad4) + gap

    m = mem(copies)
    ks = g.game_copies(m, w)
    want = [64 + 684 + 37 + i * (684 + 37) for i in range(3)]
    if ks != want:
        return False, f'game copies {ks} != {want} (raw buffer / +4=7 copy must be skipped)'
    if g.copy_diffs(m, w, ks):
        return False, f'clean copies flagged {g.copy_diffs(m, w, ks)}'
    c = [bytearray(x) for x in copies]
    c[2][24] ^= 1                                                  # the tactic in the last copy
    d = g.copy_diffs(mem(c), w, ks)
    if d != [want[2]]:
        return False, f'tactic flipped in the last copy: caught {d}, want {[want[2]]}'
    c = [bytearray(x) for x in copies]
    c[0][61] ^= 0x10                                               # a lineup byte in the first copy
    d = g.copy_diffs(mem(c), w, ks)
    if d != [want[0]]:
        return False, f'lineup byte flipped in the first copy: caught {d}, want {[want[0]]}'
    return True, f'3 game copies found (raw buffer + bad +4 skipped); clean 0 bad; tactic / lineup corruption caught'
