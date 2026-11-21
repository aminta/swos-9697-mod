"""Starter-role check of every team record in a DATA dir (or files): the 11 starters (lineup bytes 60..65 first 11)
must hold the slot roles of the record's tactic (mkseason.slots_of: 4-4-2 = GK RB D D LB RW M M LW A A). A squad that cannot supply the
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


REAL_FILES = ('TMW5.',)         # the World 2026-27 namespace: the only files with real line-ups (lineup_src 'real')


def real_lineups(d):
    """{(team file number, club name)} with lineup_src 'real' (reallineups.py: the real XI in rows 1..11) in the world data dir of the release
    whose DATA dir is d: W2627REL_DATA, else 'data <dir>' of the release's build.log (buildrel.sh). set() without one."""
    import csv, re
    src = os.environ.get('W2627REL_DATA')
    if not src:
        log = os.path.join(d, '..', '..', 'build.log')
        m = re.search(r', data (\S+),', open(log).read()) if os.path.exists(log) else None
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'internal', 'world2526', m.group(1)) if m else ''
    out = set()
    if not (src and os.path.isdir(src)):
        return out
    # (Motore 21/11: keyed by (team file, name) - record byte 0 is its file number: TMW5.216's INTER (Taiwan) is not
    #  TMW5.102's real INTER. The country -> file map is the world's build report <src>.txt, 'ITA file 102 ...')
    fno = {ln.split()[0]: int(ln.split()[2]) for ln in open(src.rstrip('/') + '.txt') if ' file ' in ln}
    for r_, _, fs in os.walk(src):
        if 'clubs.csv' in fs:
            for c in csv.DictReader(open(os.path.join(r_, 'clubs.csv'), encoding='utf-8')):
                if c.get('lineup_src') == 'real':
                    assert c['country'] in fno, ('lineupcheck: real club of a country without a team file', c['name'], c['country'])
                    out.add((fno[c['country']], c['name']))
    return out


def control():
    """MC 14/11: a default (identity) line-up that starts worse than its squad allows must be wrong, whatever the
    real-line-up set holds for other clubs; the same record marked 'real' is checked on its own 11 only."""
    r = bytearray(684)
    r[5:9] = b'CTRL'
    r[60:76] = bytes(range(16))
    for j, p in enumerate([0] + [6] * 10 + [3, 3, 3, 3, 7]):     # G + 10 M start; 4 D + an A on the bench
        r[76 + 38 * j + 26] = p << 5
    b = (1).to_bytes(2, 'big') + bytes(r)
    assert check_file(b, real={(0, 'OTHER')})[4], 'lineupcheck control: a suboptimal default line-up passed'
    assert not check_file(b, real={(0, 'CTRL')})[4], 'lineupcheck control: a real XI was checked against all 16'
    o = bytearray(r)                              # (the same name in another team file is not that real club: Taiwan's INTER)
    o[0] = 1
    assert check_file((1).to_bytes(2, 'big') + bytes(o), real={(0, 'CTRL')})[4], 'lineupcheck control: a namesake in another file was taken as real'
    for off, val, want in ((60, bytes([1, 0]), 'no keeper in slot 1'), (70, bytes([11, 10]), 'the XI is not rows 1..11'),
                           (76 + 38 * 5 + 26, b'\0', 'a second keeper in the XI'), (24, bytes([len(mkseason.TACTICS)]), 'is not a game tactic')):
        t = bytearray(r)                          # (red twins, Regia 21/11: a broken real structure must FAIL, for its reason)
        t[off:off + len(val)] = val
        w = check_file((1).to_bytes(2, 'big') + bytes(t), real={(0, 'CTRL')})[4]
        assert w and want in w[0][2], f'lineupcheck control: a real XI with {want!r} gave {w}'


def check_dir(d, orig_dir=None, real=None):
    """-> (lines, totals(records, original, exact, best-possible), wrong_total, errors): errors = wrong records beyond
    KNOWN_EXPLICIT, files seen. real = the clubs whose XI is the data's (default: real_lineups(d)), REAL_FILES only."""
    control()
    real = real_lineups(d) if real is None else real
    shapes = orig_shapes(orig_dir) if orig_dir and os.path.isdir(orig_dir) else set()
    lines, tot, errs = [f'real line-ups (lineup_src real): {len(real)}'], [0, 0, 0, 0], []
    for f, b in team_files(d):
        op = os.path.join(orig_dir, f) if orig_dir else ''
        n, same, ex, oo, wrong = check_file(b, open(op, 'rb').read() if os.path.exists(op) else None, shapes,
                                            real if f.upper().startswith(REAL_FILES) else set())
        tot = [a + c for a, c in zip(tot, (n, same, ex, oo))]
        lines.append(f'{f}: {n} records, original {same}, exact {ex}, best-possible {oo}, wrong {len(wrong)}')
        if len(wrong) > KNOWN_EXPLICIT.get(f, 0):
            errs.append(f'{f}: {len(wrong)} records start the wrong roles (known explicit {KNOWN_EXPLICIT.get(f, 0)}) '
                        f'e.g. {wrong[:3]}')
    return lines, tot, errs


def _score(got, slot=SLOT):
    return (sum(g == w for g, w in zip(got, slot)), sum(CLS[g] == CLS[w] for g, w in zip(got, slot)))


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


def real_structure(lu, pos, tactic):
    """'' (fine) or what is wrong with a real line-up's structure: the XI = rows 1..11, the keeper in slot 1 and no other
    keeper in the XI, a tactic of the game (mkseason.TACTICS; 0 = 4-4-2 is a real formation too)."""
    if sorted(lu[:11]) != list(range(11)):
        return 'the XI is not rows 1..11'
    if pos[lu[0]] != 0:
        return 'no keeper in slot 1'
    if any(pos[j] == 0 for j in lu[1:11]):
        return 'a second keeper in the XI'
    if tactic >= len(mkseason.TACTICS):
        return f'tactic {tactic} is not a game tactic'
    return ''


def check_file(data, orig=None, shapes=(), real=()):
    """-> (records, orig_same, exact, other_ok, wrong[(ordinal, name, got)]). A record byte-identical to the original
    game's (orig = that file's bytes) is left alone (its lineup is the original's, whatever its squad). Any other must
    start 11 players whose roles match the slot roles at least as well as the best choice of its squad (auto_lineup);
    a club in real ((team file, name)) is checked for its structure only (real_structure; its roles: lineups_gate);
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
        if (r[0], name) in real:
            # 4.2 real line-up (clubs.csv lineup_src 'real', reallineups2: rows 1..11 = the real XI, its tactic the club's
            # own record): the XI and its slots are the data's choice by the players' MATCH-SHEET roles, which a team file
            # does not hold (its position bytes are the TM registration: a wing-back registered RB, a 3-4-2-1 attacking
            # midfielder registered M). So only the structure is checked here; the roles are lineups_gate's (the sheet
            # roles), a gate of its own on the rc data dir (Regia 21/11: one rule, no per-club exceptions).
            bad = real_structure(lu, pos, r[24])
            if bad:
                wrong.append((i, name, 'real line-up: ' + bad))
            else:
                ok_other += 1
            continue
        got = [pos[j] for j in lu[:11]]
        slot = mkseason.slots_of(r[24])          # (4.2: the record's own tactic's slot roles, 4-4-2's for 0)
        best = [pos[j] for j in mkseason.auto_lineup(pos, r[24])[:11]]
        if _score(got, slot) < _score(best, slot):
            wrong.append((i, name, got)); continue
        if got == slot:
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
