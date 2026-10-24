"""Starter-role check of every team record in a DATA dir (or files): the 11 starters (lineup bytes 60..65 first 11)
must hold the game's 4-4-2 slot roles GK RB D D LB RW M M LW A A (mkseason.SLOT_POS). A squad that cannot supply the
exact positions is checked by class (GK / defender / midfielder / attacker) and, below that, counted as 'short'.
python3 tools/lineupcheck.py DATA_DIR  -> per-file counts, exit 1 on any wrong record."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkseason

SLOT, CLS = mkseason.SLOT_POS, mkseason._POS_CLASS


# explicit-lineup records of the historic tourney packs whose hand-written lineups start worse than the squad allows
# (2026-10-23: "explicit lineup wins"; counts per team file, the checker fails on more or on any other file)
# Kept as they are on purpose (Regia 2026-10-23): hand-written historic line-ups, where a player out of his usual role
# can be the real XI.
KNOWN_EXPLICIT = {'TEAM.089': 15, 'TEAM.090': 16, 'TEAM.091': 14, 'TEAM.092': 11, 'TEAM.093': 6, 'TEAM.146': 16}


def check_dir(d, orig_dir=None):
    """-> (lines, totals(records, original, exact, best-possible), wrong_total, errors): errors = wrong records beyond
    KNOWN_EXPLICIT, files seen."""
    shapes = orig_shapes(orig_dir) if orig_dir and os.path.isdir(orig_dir) else set()
    lines, tot, errs = [], [0, 0, 0, 0], []
    for f, b in team_files(d):
        op = os.path.join(orig_dir, f) if orig_dir else ''
        n, same, ex, oo, wrong = check_file(b, open(op, 'rb').read() if os.path.exists(op) else None, shapes)
        tot = [a + c for a, c in zip(tot, (n, same, ex, oo))]
        lines.append(f'{f}: {n} records, original {same}, exact {ex}, best-possible {oo}, wrong {len(wrong)}')
        if len(wrong) > KNOWN_EXPLICIT.get(f, 0):
            errs.append(f'{f}: {len(wrong)} records start the wrong roles (known explicit {KNOWN_EXPLICIT.get(f, 0)}) '
                        f'e.g. {wrong[:3]}')
    return lines, tot, errs


def _score(got):
    return (sum(g == w for g, w in zip(got, SLOT)), sum(CLS[g] == CLS[w] for g, w in zip(got, SLOT)))


def orig_shapes(d):
    """{(lineup, positions)} of every record of the original game's team files in d: a mod record that keeps one
    of them (season packs keep the template's lineup and positions) is the original's own choice."""
    out = set()
    for f, b in team_files(d):
        n = struct.unpack('>H', b[:2])[0]
        for i in range(n):
            r = b[2 + 684 * i:2 + 684 * (i + 1)]
            out.add((bytes(r[60:76]), bytes(r[76 + 38 * j + 26] >> 5 for j in range(16))))
    return out


def check_file(data, orig=None, shapes=()):
    """-> (records, orig_same, exact, other_ok, wrong[(ordinal, name, got)]). A record byte-identical to the original
    game's (orig = that file's bytes) is left alone (its lineup is the original's, whatever its squad). Any other must
    start 11 players whose roles match the slot roles at least as well as the best choice of its squad (auto_lineup);
    'exact' = all 11 slot positions equal."""
    n = struct.unpack('>H', data[:2])[0]
    assert len(data) >= 2 + 684 * n
    same = ex = ok_other = 0
    wrong = []
    for i in range(n):
        r = data[2 + 684 * i:2 + 684 * (i + 1)]
        if orig is not None and i < struct.unpack('>H', orig[:2])[0] and orig[2 + 684 * i:2 + 684 * (i + 1)] == r:
            same += 1; continue
        lu = list(r[60:76])
        pos = [r[76 + 38 * j + 26] >> 5 for j in range(16)]
        if (bytes(lu), bytes(pos)) in shapes:
            same += 1; continue
        name = r[5:22].split(b'\0')[0].decode('latin1')
        if sorted(lu) != list(range(16)):
            wrong.append((i, name, 'not a permutation')); continue
        got = [pos[j] for j in lu[:11]]
        best = [pos[j] for j in mkseason.auto_lineup(pos)[:11]]
        if _score(got) < _score(best):
            wrong.append((i, name, got)); continue
        if got == SLOT:
            ex += 1
        else:
            ok_other += 1
    return n, same, ex, ok_other, wrong


def team_files(d):
    """(name, bytes) of every file in d that is a team file (BE count + 684-byte records, exact size)."""
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.getsize(p) > 700:
            b = open(p, 'rb').read()
            n = struct.unpack('>H', b[:2])[0]
            if 0 < n < 1000 and len(b) in (2 + 684 * n, 2 + 684 * n + 1) and \
                    f.upper().startswith(('TEAM.', 'TMW', 'XTW', 'POOL')) and not f.upper().startswith('POOL05.DAT'):
                yield f, b


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    lines, tot, errs = check_dir(sys.argv[1], os.environ.get('LINEUP_ORIG', os.path.join(root, 'orig', 'DATA')))
    print('\n'.join(lines))
    print(f'TOTAL {tot[0]} records, original {tot[1]}, exact {tot[2]}, best-possible {tot[3]}; errors: {len(errs)}')
    print('\n'.join(errs))
    sys.exit(1 if errs else 0)
