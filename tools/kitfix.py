"""4.0.5 the career club's kits after a data update (Francesco's ISCHIA report, 2026-10-28): a .CAR keeps its own copy of
the managed club (careerFileBuffer + 0DB80h = the save's offset 56192), so a release that changes that club's kits
gives the new ones to every opponent but not to the career club. At the season end (careerworld w_kits, from w_list in
cseg_91428 - no load hook) the career club takes its current kits when its saved home + away kits are still a pair an
earlier RELEASE shipped for it: a kit edited with SELECT KITS is never touched.

Data: kits_shipped.json.gz = every (team file stem, number, ordinal) -> [name, [shipped kits]] of the released builds
(SHIPPED; add each new release with `python3 tools/kitfix.py ship c/RELxx`). gen() (patch.py, from the build's DATA)
writes DATA\\KITFIX.DAT: per club whose shipped kits differ from the build's, one 39-byte record per old pair -
file, ordinal, name (17 bytes, as TeamFile +5), old kits (10, TeamFile +1Ah), new kits (10).
"""
import gzip
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHIP = os.path.join(HERE, 'kits_shipped.json.gz')
SHIPPED = ['REL300', 'REL301', 'REL302', 'REL31', 'REL32', 'REL320', 'REL323', 'REL324', 'REL325', 'REL326', 'REL327',
           'REL330', 'REL331', 'REL332', 'REL333', 'REL334', 'REL335', 'REL336', 'REL40rc12', 'REL40hf', 'REL401rc3',
           'REL402rc2']                                  # (3.0 .. 4.0.2: the released builds' dirs in c/)
REC = 39
NAME, KITS = 5, 0x1A                                     # TeamFile: name +5 (17 bytes), home + away kits +1Ah (10)


def records(data):
    """{'STEM.nnn:ordinal': (name 17 bytes, kits 10 bytes)} of a DATA dir's team files (TEAM.nnn, TMWn.nnn)."""
    out = {}
    for fn in os.listdir(data) if os.path.isdir(data) else []:
        st, _, ext = fn.upper().partition('.')
        if not (st == 'TEAM' or st.startswith('TMW')) or not ext.isdigit():
            continue
        d = open(os.path.join(data, fn), 'rb').read()
        for k in range(struct.unpack('>H', d[:2])[0]):
            r = d[2 + 684 * k:2 + 684 * k + KITS + 10]
            if len(r) == KITS + 10:
                out[f'{st}.{int(ext)}:{k}'] = (r[NAME:NAME + 17], r[KITS:KITS + 10])
    return out


def load():
    return json.loads(gzip.open(SHIP).read()) if os.path.exists(SHIP) else {}


def ship(*dirs):
    """Add released builds' kits (their SWOS/DATA) to kits_shipped.json.gz."""
    s = load()
    for b in dirs:
        for key, (nm, kit) in records(os.path.join(b, 'SWOS', 'DATA')).items():
            e = s.setdefault(key, [nm.hex(), []])
            if kit.hex() not in e[1]:
                e[1].append(kit.hex())
    with gzip.open(SHIP, 'wb', 6) as f:
        f.write(json.dumps(s, sort_keys=True, separators=(',', ':')).encode())
    return len(s), sum(len(v[1]) for v in s.values())


def gen(data):
    """DATA\\KITFIX.DAT from the build's team files: the shipped pairs that differ from the current ones."""
    cur = records(data)
    if not cur:
        return None
    out = bytearray()
    for key, (nm_hex, kits) in sorted(load().items()):
        if key not in cur:
            continue
        nm, new = cur[key]
        if bytes.fromhex(nm_hex) != nm:                  # (another club on that place now: no pair to refresh)
            continue
        f, k = key.split(':')
        for old in kits:
            old = bytes.fromhex(old)
            if old != new:
                out += bytes([int(f.split('.')[1]), int(k)]) + nm + old + new
    assert len(out) % REC == 0
    open(os.path.join(data, 'KITFIX.DAT'), 'wb').write(out)
    return len(out) // REC


if __name__ == '__main__':
    if sys.argv[1:2] == ['ship']:
        print(ship(*sys.argv[2:]))
    elif sys.argv[1:2] == ['gen']:
        print(gen(sys.argv[2]))
