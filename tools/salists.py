"""Print the South American cup lists saved in a career file: .CAR trailer C4/C5 (1.2/1.3), else the 1.0/1.1 block
in someLeaguesTable[1740..] (S2/SA)."""
import os
import struct
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
SAVED = 0x17fb2 + 1740 - 0x96d6          # obj2 someLeaguesTable + SAVED_GLOBAL - careerFileBuffer


def name(fileno, idx):
    d = open(os.path.join(ROOT, 'c/SWOS/DATA/TEAM.%03d' % fileno), 'rb').read()
    return d[2 + idx * 684 + 5:2 + idx * 684 + 22].split(b'\0')[0].decode('latin1')


SA_FILES = {43, 45, 46, 48, 49, 50, 64, 65, 71, 77}       # South American team files


def find_block(d):
    """Saved block offset: the ITALIAN.EXE one, else search (other exe languages keep it elsewhere in the save)."""
    def ok(at):
        mark = d[at:at + 2]
        size = {b'S2': 103, b'SA': 99}.get(mark)
        return size and sum(d[at:at + size]) % 256 == 0 and all(d[at + 2 + i] in SA_FILES for i in range(0, 32, 2))
    if ok(SAVED):
        return SAVED
    hits = [i for i in range(len(d) - 103) if ok(i)]
    return hits[0] if len(hits) == 1 else SAVED


def trailer(d):
    """1.2/1.3/C6: block after the N cached team records (N = word at save offset 95151)."""
    n = struct.unpack_from('<H', d, 95151)[0]
    at = 95153 + n * 684
    mark = d[at:at + 2]
    lib = {b'C7': 21, b'C6': 21, b'C5': 20, b'C4': 16}.get(mark)
    if not lib:
        return False
    at += 2
    print(f'trailer {mark.decode()} ({len(d) - at + 2} B)')
    for cup, k in (('LIBERTADORES', lib), ('SUPERCOPA', 16), ('CONMEBOL', 16)):
        teams = [name(d[at + i], d[at + i + 1]) for i in range(0, 2 * k, 2)]
        at += 2 * k
        print(cup + ':')
        for g in range(0, k, 4):
            print('   ' + ', '.join(teams[g:g + 4]))
    print('INTERCONTINENTALE: ' + name(d[at], d[at + 1]) + ' - ' + name(d[at + 2], d[at + 3]))
    return True


d = open(sys.argv[1], 'rb').read()
if trailer(d):
    sys.exit()
SAVED = find_block(d)
mark = struct.unpack_from('<H', d, SAVED)[0]
if mark not in (0x4153, 0x3253):
    sys.exit(f'no SA lists in this save (marker {mark:#x}): the 1997 lists are used')
size = 103 if mark == 0x3253 else 99       # 'S2': + Intercontinental pair; last byte balances the table sum
print(f"format {'S2' if mark == 0x3253 else 'SA (session 12)'}, block sum mod 256 = {sum(d[SAVED:SAVED + size]) % 256}")
for k, cup in enumerate(('LIBERTADORES', 'SUPERCOPA', 'CONMEBOL')):
    lst = d[SAVED + 2 + 32 * k:SAVED + 34 + 32 * k]
    teams = [name(lst[i], lst[i + 1]) for i in range(0, 32, 2)]
    print(cup + ':')
    for g in range(0, 16, 4):
        print('   ' + ', '.join(teams[g:g + 4]))
if mark == 0x3253:
    i = d[SAVED + 98:SAVED + 102]
    print('INTERCONTINENTALE: ' + name(i[0], i[1]) + ' - ' + name(i[2], i[3]))
else:
    print('INTERCONTINENTALE: not saved (old format) -> default JUVENTUS - RIVER PLATE')
