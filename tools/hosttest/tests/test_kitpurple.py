"""4.1 navy / dark grey -> purple fix (tools/kitpurple.py): the audit's 100 kits with a purple field replayed through the
rule, the world builder's rule (internal/world2526/tmkits.py) checked against it, and the patched world data checked
byte for byte against its base.
Fixture internal/hosttest/fixtures/kitpurple/audit.json (the 07/11 audit, unversioned like every fixture).
HT_KIT_BASE / HT_KIT_DATA = the world dirs (default world5tm-403c14 / world5tm-403c15)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
import kitpurple                                                # noqa: E402

MAIN = os.path.expanduser('~/swos-mod')
W = os.path.join(MAIN, 'internal', 'world2526')
AUDIT = os.path.join(MAIN, 'internal', 'hosttest', 'fixtures', 'kitpurple', 'audit.json')
BASE = os.environ.get('HT_KIT_BASE') or os.path.join(W, 'world5tm-403c14')
DATA = os.environ.get('HT_KIT_DATA') or os.path.join(W, 'world5tm-403c15')
P = str(kitpurple.PURPLE)


def _band(h):
    hue, sat, _ = kitpurple.hsv(h)
    return 'grey' if sat < kitpurple.SAT else 'navy' if kitpurple.NAVY[0] <= hue <= kitpurple.NAVY[1] else \
        'purple' if kitpurple.is_purple(h) else 'other'


def test_kitpurple_rule():
    audit = json.load(open(AUDIT))
    bands, errs = {}, []
    for r in audit:
        after = kitpurple.fixed(r).split()
        keep = (r['cc'], r['key']) in kitpurple.KEEP
        for f, h, _, _ in r['fields']:
            i = kitpurple.FIELDS.index(f) + 1
            if not h:
                continue
            b = _band(h)
            bands[b] = bands.get(b, 0) + 1
            if f == 'stripes' and after[0] == '0' and after[2] == after[1] != P and not keep:
                continue                # (a plain shirt's stripes follow the shirt: LA GALAXY's navy kit2)
            if b == 'purple' or keep:
                if after[i] != P:
                    errs.append(f'{r["name"]} {r["kit"]} {f} {h}: purple lost')
            elif after[i] == P:
                errs.append(f'{r["name"]} {r["kit"]} {f} {h} ({b}): still purple')
            elif b == 'navy' and after[i] not in ('5', '7'):
                errs.append(f'{r["name"]} {r["kit"]} {f} {h}: navy -> {after[i]}')
            elif b == 'grey' and after[i] not in ('0', '1', '2'):
                errs.append(f'{r["name"]} {r["kit"]} {f} {h}: grey -> {after[i]}')
        if after[0] == '0' and after[1] != P and after[2] == P:
            errs.append(f'{r["name"]} {r["kit"]}: a plain shirt with purple stripes')
    # the rule's own controls: plain RGB distance put these on purple / maroon / green
    for h, want in (('313055', '5'), ('1A3256', '5'), ('555555', '0'), ('221F64', '5'), ('5c2195', P), ('373C7D', '5')):
        if str(kitpurple.colour(h)) != want:
            errs.append(f'control {h} -> {kitpurple.colour(h)}, want {want}')
    # the world builder's rule gives the same colour for every audited source
    os.environ.setdefault('TOOLS', TOOLS)
    sys.path.insert(0, W)
    import tmkits
    if len(tmkits.RGB) != 11:
        errs.append('tmkits without purple (TOOLS has no purple.py)')
    for r in audit:
        for f, h, _, _ in r['fields']:
            if h and (r['cc'], r['key']) not in kitpurple.KEEP and tmkits.colour(h) != kitpurple.colour(h):
                errs.append(f'tmkits {h} -> {tmkits.colour(h)}, kitpurple {kitpurple.colour(h)}')
    if tmkits.colour('373C7D') != kitpurple.PURPLE:
        errs.append('tmkits: MARIBOR not purple')
    if errs:
        return False, '; '.join(errs[:12])
    return True, f'{len(audit)} kits, fields by source band {bands}; 6 controls; tmkits agrees'


def test_kitpurple_data():
    """DATA = BASE with only the audited kit cells changed, each to kitpurple.fixed()"""
    audit = json.load(open(AUDIT))
    want = {(r['cc'], r['key'], r['kit']): (r['before'], kitpurple.fixed(r)) for r in audit}
    errs, cells, files = [], 0, 0
    for root, _, fs in os.walk(BASE):
        for fn in fs:
            a = os.path.join(root, fn)
            rel = os.path.relpath(a, BASE)
            b = os.path.join(DATA, rel)
            files += 1
            if not os.path.exists(b):
                errs.append(f'{rel} missing')
                continue
            x, y = open(a, 'rb').read(), open(b, 'rb').read()
            if x == y:
                continue
            if fn != 'clubs.csv':
                errs.append(f'{rel} changed')
                continue
            xl, yl = x.split(b'\n'), y.split(b'\n')
            if len(xl) != len(yl):
                errs.append(f'{rel} line count')
                continue
            hdr = xl[0].decode().split(',')
            for p, q in zip(xl, yl):
                if p == q:
                    continue
                pc, qc = p.decode('utf-8').split(','), q.decode('utf-8').split(',')
                d = [i for i in range(len(pc)) if len(pc) == len(qc) and pc[i] != qc[i]]
                if len(d) != 1 or hdr[d[0]] not in ('kit1', 'kit2'):
                    errs.append(f'{rel}: {pc[0]} changed outside its kit cell')
                    continue
                k = (rel.split(os.sep)[0], pc[0], hdr[d[0]])
                if want.get(k) != (pc[d[0]], qc[d[0]]):
                    errs.append(f'{k}: {pc[d[0]]} -> {qc[d[0]]}, want {want.get(k)}')
                cells += 1
    extra = sum(len(fs) for _, _, fs in os.walk(DATA)) - files
    if extra:
        errs.append(f'{extra} files only in the patched dir')
    changed = sum(1 for b, a in want.values() if b != a)
    if cells != changed:
        errs.append(f'{cells} cells changed, the audit changes {changed}')
    if errs:
        return False, '; '.join(errs[:12])
    return True, f'{files} files: {cells} kit cells changed as the rule says, every other byte identical'
