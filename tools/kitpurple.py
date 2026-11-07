"""4.1 navy / dark grey -> purple fix (Davide 07/11, choice A): World 2026-27 kits picked purple (10) for navy and dark
grey sources, because purple (100,40,140) is the nearest SWOS colour to them by RGB distance.

The rule (also in internal/world2526/tmkits.colour, for future world builds), by the source colour's HSV:
- purple (10) only for hue 248..335 with saturation >= 0.2;
- saturation < 0.2 (greys): black below value 0.2, white from 0.85, grey (0) between;
- hue 195..247 (navy, blues): blue (5), light blue (7) only when light (value >= 0.85 and saturation < 0.5);
- any other colour: the nearest of the ten others by RGB distance.
(Plain RGB distance alone puts navy on maroon or green: BOCHUM 313055 -> maroon, MILLWALL 1A3256 -> green.)
One exception: MARIBOR keeps its purple (its real colour, which the sources give as a dark violet-blue).

    python3 tools/kitpurple.py AUDIT SRC DST     copy world dir SRC to DST with only the audited kit fields changed

AUDIT = the audit's json (internal/hosttest/fixtures/kitpurple/audit.json): one row per kit that had a purple field:
{cc, key, name, kit, before, fields: [[field, hex or None, hsv, source], ...]}."""
import colorsys
import csv
import json
import os
import shutil
import sys

RGB = [(150, 150, 150), (255, 255, 255), (0, 0, 0), (255, 140, 0), (220, 0, 0), (0, 40, 180), (120, 20, 40),
       (110, 180, 240), (0, 140, 60), (255, 220, 0), (100, 40, 140)]           # (tmkits.RGB, 10 = purple)
PURPLE = 10
HUE = (248, 335)
SAT = 0.2
KEEP = {('svn', 'maribor')}                     # (cc, key): purple kept
FIELDS = ['shirt', 'stripes', 'shorts', 'socks']        # kit string positions 1..4 (0 = type)


NAVY = (195, 247)


def hsv(h):
    """(hue 0..359, saturation, value) of hex h"""
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
    return round(hue * 360) % 360, sat, val


def is_purple(h):
    hue, sat, _ = hsv(h)
    return HUE[0] <= hue <= HUE[1] and sat >= SAT


def colour(h):
    """the SWOS colour of hex h"""
    hue, sat, val = hsv(h)
    if sat < SAT:
        return 2 if val < 0.2 else 1 if val >= 0.85 else 0
    if NAVY[0] <= hue <= NAVY[1]:
        return 7 if val >= 0.85 and sat < 0.5 else 5
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    cands = range(len(RGB)) if is_purple(h) else [c for c in range(len(RGB)) if c != PURPLE]
    return min(cands, key=lambda c: sum((a - b) ** 2 for a, b in zip(rgb, RGB[c])))


def fixed(row):
    """the audited kit string under the rule: only its purple fields with a known source hex change"""
    k = row['before'].split()
    if (row['cc'], row['key']) in KEEP:
        return ' '.join(k)
    for f, h, _, _ in row['fields']:
        i = FIELDS.index(f) + 1
        if h and k[i] == str(PURPLE):
            k[i] = str(colour(h))
    if k[0] == '0' and k[2] == str(PURPLE) and k[1] != str(PURPLE):
        k[2] = k[1]                     # (a plain shirt's stripes = the shirt, as tmkits writes them)
    return ' '.join(k)


def patch(audit, src, dst):
    """copy src to dst, rewriting only the audited kit cells; returns [(cc, key, kit, before, after)]"""
    assert not os.path.exists(dst), dst
    shutil.copytree(src, dst, symlinks=True)
    by = {}
    for r in audit:
        by.setdefault(r['cc'], []).append(r)
    out = []
    for cc, rows in sorted(by.items()):
        f = os.path.join(dst, cc, 'clubs.csv')
        raw = open(f, 'rb').read()
        text = raw.decode('utf-8')
        lines = text.splitlines(keepends=True)
        hdr = next(csv.reader([lines[0]]))
        for r in rows:
            new = fixed(r)
            if new == r['before']:
                continue
            hit = [i for i, ln in enumerate(lines[1:], 1) if next(csv.reader([ln]))[hdr.index('key')] == r['key']]
            assert len(hit) == 1, (cc, r['key'])
            cells = next(csv.reader([lines[hit[0]]]))
            assert cells[hdr.index(r['kit'])] == r['before'], (cc, r['key'], r['kit'])
            # (the cell is a bare 'n n n n n' with no quotes: replace that one field in place, the rest byte for byte)
            col = hdr.index(r['kit'])
            parts = lines[hit[0]].split(',')
            assert parts[col] == r['before'] and len(parts) == len(cells), (cc, r['key'], 'quoted cells before the kit')
            parts[col] = new
            lines[hit[0]] = ','.join(parts)
            out.append((cc, r['key'], r['kit'], r['before'], new))
        tmp = f + '.tmp'
        open(tmp, 'wb').write(''.join(lines).encode('utf-8'))
        os.replace(tmp, f)
    return out


if __name__ == '__main__':
    a, s, d = sys.argv[1:4]
    for x in patch(json.load(open(a)), s, d):
        print(*x, sep='\t')
