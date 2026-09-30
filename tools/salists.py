"""Print the South American cup lists saved in a career file (someLeaguesTable[1740..]), both block formats."""
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


d = open(sys.argv[1], 'rb').read()
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
