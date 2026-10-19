"""The other confederations' club cups of World 2026-27 (conti.c's data and glue). See notes/continental-cups.md.

Data: internal/conti/<conf>.format.json (package 6: rounds, draws, routes, names) + <conf>.access.json (data: the
access lists per association pack key, the ranking, the season-1 entrants), merged by cup key.

    spec, assocs, cups = conti.load(['conmebol'])          # spec bytes for CT_SPEC, association keys, cup keys
    python3 tools/conti.py --test [conf ...]               # conti.c natively (ctypes) on a synthetic world
"""
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(ROOT), '..', '..', 'internal', 'conti')
if not os.path.isdir(DATA):
    DATA = os.path.expanduser('~/swos-mod/internal/conti')

RB = 24
OUT, CHAMP = 0xFF, 0xFE
K = {'ko': 0, 'groups': 1}
DRAW = {'order': 0, 'pots2': 1, 'same_assoc_pairs': 2, 'seeded_1v2': 3, 'bracket': 4, 'groups': 5, 'fixed': 6}
ASSOC = {'allow': 0, 'any': 0, 'no': 1, 'no_unless_via': 2, 'allow_if_via': 2}
LEVEL = {'pens': 0, 'et_pens': 1, 'away_pens': 2}
CODE = {'cup': 1, 'next': 0x40, 'ap': 0x41, 'cl': 0x42}
ALIAS = {'r1': 'first', 'playoffs': 'po'}   # (access files' round names -> the format's)


def _read(conf, kind):
    p = os.path.join(DATA, f'{conf}.{kind}.json')
    return json.load(open(p)) if os.path.exists(p) else None


def _draw(rd):
    """(draw byte, association rule byte) of a round's 'draw' value."""
    d = rd.get('draw')
    if rd['kind'] == 'groups':
        return DRAW['groups'], ASSOC.get((d or {}).get('same_assoc', 'no'), 1)
    if isinstance(d, str):
        return DRAW.get(d, DRAW['order']) if d != 'fixed' else DRAW['order'], 0
    if not d:
        return DRAW['order'], 0
    kind = d.get('kind')
    rule = ASSOC.get(d.get('same_assoc', 'allow'), 0)
    if kind == 'same_assoc_pairs':
        return DRAW['same_assoc_pairs'], 0
    if kind == 'seeded_1v2':
        return DRAW['seeded_1v2'], rule
    if kind == 'fixed' and d.get('ties'):
        return DRAW['fixed'], 0
    if kind in ('bracket',):
        return DRAW['bracket'], 0
    if d.get('pots') == 2 or kind in ('pots2',):
        return DRAW['pots2'], rule
    return DRAW['order'], rule


def load(confs):
    """-> (spec bytes, [association pack keys], [(conf, cup key)])."""
    cups, assocs = [], []
    for conf in confs:
        fm, ac = _read(conf, 'format'), _read(conf, 'access')
        assert fm, f'{conf}: no format file'
        acc = {c['key']: c for c in (ac or {}).get('cups', [])}
        for c in fm['cups']:
            cups.append((conf, c, acc.get(c['key'], {})))
            for a in acc.get(c['key'], {}).get('access', {}):
                if a not in ('holders', 'from') and a not in assocs:
                    assocs.append(a)
    index = {(conf, c['key']): i for i, (conf, c, _) in enumerate(cups)}
    rkey = {i: {r['key']: j for j, r in enumerate(c['rounds'])} for i, (_, c, _) in enumerate(cups)}

    def target(conf, ci, s):
        """'r16' / 'sud:po' / 'sud:groups' -> cup << 4 | round."""
        if ':' in s:
            ck, rk = s.split(':')
            cj = index[(conf, ck)]
            return cj << 4 | rkey[cj][rk]
        return ci << 4 | rkey[ci][s]

    body = b''
    access, holders = [], []
    for ci, (conf, c, a) in enumerate(cups):
        rounds = c['rounds']
        out = b''
        for j, rd in enumerate(rounds):
            dr, rule = _draw(rd)
            b = bytearray(RB)
            b[0] = K[rd['kind']]
            b[1] = rd.get('legs', 2 if rd['kind'] == 'ko' else 0)
            b[2] = LEVEL.get(rd.get('level', 'pens'), 0)
            b[3] = 1 if rd.get('host') in ('neutral', 'centralised') else 0
            b[4], b[5] = dr, rule
            if rd['kind'] == 'groups':
                b[6], b[7], b[8] = rd['groups'], rd['size'], rd.get('rounds', 2)
                b[16] = 1 if (rd.get('draw') or {}).get('holder') else 0
            b[9] = rd.get('month') or (rd.get('months') or [8])[0]
            b[10] = CHAMP if j == len(rounds) - 1 else (ci << 4 | (j + 1))
            b[11] = OUT
            for q in range(4):
                b[12 + q] = OUT
            if rd['kind'] == 'groups':
                b[10] = OUT
                for q, t in (rd.get('out') or {}).items():
                    b[12 + int(q) - 1] = target(conf, ci, t)
            if (c.get('losers') or {}).get(rd['key']):
                b[11] = target(conf, ci, c['losers'][rd['key']])
            out += bytes(b)
        body += bytes((len(rounds), 0, 0, 0)) + out
        for ak, entries in (a.get('access') or {}).items():
            if ak == 'holders':
                for src, rk in entries.items():
                    holders.append((index[(conf, src)], ci, rkey[ci][rk]))
                continue
            if ak == 'from':
                continue
            for rk, code in entries:
                rk = ALIAS.get(rk, rk) if rk not in rkey[ci] else rk
                k = CODE[code] if isinstance(code, str) else (0 if code <= 1 else code)
                access.append((assocs.index(ak), ci, rkey[ci][rk], k))
    spec = bytes((len(cups), len(assocs), 0, 0)) + body
    spec += struct.pack('<H', len(access)) + b''.join(bytes(x) for x in access)
    spec += bytes((len(holders),)) + b''.join(bytes(x) for x in holders)
    return spec, assocs, [(conf, c['key']) for conf, c, _ in cups]


# --- native test ------------------------------------------------------------------------------------------------------
def _native():
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    lib = os.path.join(d, 'conti.dylib')
    subprocess.run(['clang', '-O1', '-shared', '-fPIC', '-o', lib, os.path.join(ROOT, 'tools', 'conti.c')], check=True)
    return ctypes.CDLL(lib)


def test(confs=('conmebol',), seasons=3, seed=7):
    import ctypes
    import random
    spec, assocs, cups = load(list(confs))
    L = _native()
    lay = (ctypes.c_uint32 * 20).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out = lay[0], lay[1], lay[2]
    o_league, o_cup, o_ap, o_cl, o_club = lay[3], lay[4], lay[5], lay[6], lay[7]
    o_win, o_sec, o_last, o_nent, o_ent, o_res = lay[8], lay[9], lay[10], lay[11], lay[12], lay[13]
    NA, NL, NC, NCUP, NRD, NE = lay[14:20]
    buf = ctypes.create_string_buffer(spec, len(spec))
    ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
    IN = (ctypes.c_ubyte * s_in).in_dll(L, 'CT_IN')
    OUTB = (ctypes.c_ubyte * s_out).in_dll(L, 'CT_OUT')
    rnd = random.Random(seed)
    names = {}
    for season in range(seasons):
        b = bytearray(s_in)
        clubs = []
        for a, ak in enumerate(assocs):         # 12 clubs per association, strength by size
            base = 3000 if ak in ('bra', 'arg') else 1500
            for k in range(18):
                cid = (100 + a) | k << 8
                names[cid] = f'{ak}{k + 1}'
                clubs.append((cid, a, base + rnd.randint(0, 1500) - 60 * k, rnd.randint(100, 9000)))
        struct.pack_into('<IHH', b, 0, seed * 100 + season, len(clubs), 0)
        for i, (cid, a, st, pt) in enumerate(clubs):
            struct.pack_into("<HBBII", b, o_club + 12 * i, cid, a, 0, st, pt)
        for a in range(len(assocs)):
            mine = sorted([i for i, c in enumerate(clubs) if c[1] == a], key=lambda i: -clubs[i][2] + rnd.randint(0, 900))
            for l in range(NL):
                struct.pack_into('<H', b, o_league + 2 * (a * NL + l), mine[l] + 1)
            struct.pack_into('<H', b, o_cup + 2 * a, mine[rnd.randint(0, 6)] + 1)
        ctypes.memmove(IN, bytes(b), s_in)
        L.ct_season()
        o = bytes(OUTB)
        print(f'--- season {season + 1}')
        for ci, (conf, ck) in enumerate(cups):
            w, s2 = struct.unpack_from('<H', o, o_win + 2 * ci)[0], struct.unpack_from('<H', o, o_sec + 2 * ci)[0]
            nm = lambda x: names[clubs[x - 1][0]] if x else '-'
            counts = [o[o_nent + ci * NRD + r] for r in range(NRD)]
            print(f'{conf}:{ck} rounds {[c for c in counts if c]} winner {nm(w)} runner-up {nm(s2)}')


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['--test']:
        test(sys.argv[2:] or ['conmebol'])
