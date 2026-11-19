"""4.2 beta repair (Davide's MiSTer 19/11): joyname up to its ecx fix typed char 05h with a joystick - every stick frame
with nothing to do handed InputText the code Joy1SetStatus left in cl (5). Names edited with a pad in a 4.2 beta carry
05h bytes (drawn as boxes: 'GIANLUCA PAGLIUCA' + 5 x 05h).

    python3 tools/fixnames.py CUSTOMS.EDT [more files ...]

Every 684-byte team record (CUSTOMS.EDT: a 2-byte count, then the teams): the team name (17 B at +5), the coach (23 B
at +36) and the 16 players' names (22 B at +76 + 38 i + 3) lose their 05h bytes (the rest of the field shifts left, 0
after it). Nothing else changes. A changed file is first copied to <file>.bak; what changed is printed. Not in the
patcher (it never touches CUSTOMS.EDT): run by hand on a tester's file."""
import shutil
import sys

REC = 684
BAD = 0x05
FIELDS = [('team', 5, 17), ('coach', 36, 23)] + [(f'player {i}', 76 + 38 * i + 3, 22) for i in range(16)]


def fix_record(rec, fields=FIELDS):
    """bytes -> (fixed bytes, [(field, old, new)])"""
    r, log = bytearray(rec), []
    for what, off, n in fields:
        f = bytes(r[off:off + n])
        if BAD in f:
            g = f.replace(bytes([BAD]), b'')
            g += bytes(n - len(g))
            r[off:off + n] = g
            log.append((what, f.split(b'\0')[0], g.split(b'\0')[0]))
    return bytes(r), log


def fix_file(data, fields=FIELDS):
    """CUSTOMS.EDT bytes -> (fixed bytes, [(team index, team name, field, old, new)])"""
    n = (len(data) - 2) // REC
    assert len(data) == 2 + n * REC, ('not a team file', len(data))
    out, log = bytearray(data[:2]), []
    for i in range(n):
        rec = data[2 + i * REC:2 + (i + 1) * REC]
        fixed, lg = fix_record(rec, fields)
        out += fixed
        log += [(i, fixed[5:22].split(b'\0')[0], *x) for x in lg]
    return bytes(out), log


def main(paths):
    for p in paths:
        d = open(p, 'rb').read()
        fixed, log = fix_file(d)
        if fixed == d:
            print(f'{p}: clean, unchanged')
            continue
        shutil.copy2(p, p + '.bak')
        open(p, 'wb').write(fixed)
        print(f'{p}: {len(log)} name(s) fixed (backup {p}.bak)')
        for i, team, what, old, new in log:
            print(f'  team {i} {team.decode("latin-1")!r} {what}: {old!r} -> {new.decode("latin-1")!r}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
