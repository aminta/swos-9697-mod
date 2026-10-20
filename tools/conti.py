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
K = {'ko': 0, 'groups': 1, 'league_stage': 1}   # (a league stage: simulated as groups, one region a group)
DRAW = {'order': 0, 'pots2': 1, 'same_assoc_pairs': 2, 'seeded_1v2': 3, 'bracket': 4, 'groups': 5, 'fixed': 6, 'slot': 7,
        'fixed_by_place': 8}
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
    if rd['kind'] in ('groups', 'league_stage'):
        return DRAW['groups'], ASSOC.get((d or {}).get('same_assoc', 'no'), 1)
    if isinstance(d, dict) and d.get('kind') == 'fixed_by_place':
        return DRAW['fixed_by_place'], 0
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


def main_round(c, size=None):
    """The round a career club plays as the game's own contest (slot 3): the biggest group stage (OFC: the groups, not
    the qualifying group), else the first knockout round whose clubs are a power of two of the rounds left (CONCACAF:
    the round of 16, its first round of 22 a tie before it; size: load()'s round sizes, else FIELDS)."""
    g = [(r['groups'] * r['size'], -j, j) for j, r in enumerate(c['rounds']) if r['kind'] == 'groups'
         and not r.get('best') and not any(str(t).endswith('_best') for t in (r.get('out') or {}).values())]
    # (a group stage whose best runners-up go on: not the game's contest, simulated - the ACGL from its quarters)
    if g:
        return max(g)[2]
    size = size or next((v[0] for (cf, ck), v in FIELDS.items() if ck == c['key']), None)
    n = len(c['rounds'])
    if size:
        for j in range(n):
            if size[j] == 2 ** (n - j):
                return j
    return 0


S1_HOLD = {}                            # (conf, cup key) -> the 2027 edition's winner (word, association, strength)
FIELDS = {}                             # (conf, cup key) -> (round sizes, outside places, known places): load()'s


def supported(c):
    """The engine plays every round of the cup: knockouts and groups whose places go to a round of the cups."""
    keys = {r['key'] for r in c['rounds']}
    return all(r['kind'] in K for r in c['rounds']) and all(
        ':' in t or t.replace('_best', '') in keys for r in c['rounds'] for t in (r.get('out') or {}).values())


def fields(c, known, outside):
    """A cup's round sizes from the top (final 2, a group stage its own size): -> ([field per round], [outside places per
    round]). known[j] = the places of round j filled by world clubs (access, holders, losers of another cup);
    outside = the access file's 'outside' ({round key: count} or 'rest'): places of associations / cups not in the
    world, filled by the confederation's world associations' next clubs (declared). 'rest' fills what the sizes leave:
    above a group stage its gap, else the lowest round (data can give exact counts instead)."""
    rounds = c['rounds']
    n = len(rounds)
    key = {r['key']: j for j, r in enumerate(rounds)}
    rk_ = lambda rk: rk if rk in key else ALIAS.get(rk, rk)
    out = [0] * n
    if isinstance(outside, dict):
        for rk, k in outside.items():
            out[key[rk_(rk)]] = k
    feed = [0] * n                                      # (a group stage's places into a later round of the cup)
    best = {}
    for r in rounds:
        if r['kind'] in ('groups', 'league_stage'):
            for q, t in (r.get('out') or {}).items():
                if ':' not in t and str(r.get('best')) != str(q):
                    feed[key[t]] += r['groups'] * len(_places(q))
                elif ':' not in t:
                    best[key[t]] = r['groups']
    field = [0] * n
    for j in range(n - 1, -1, -1):
        r = rounds[j]
        if r['kind'] in ('groups', 'league_stage'):
            field[j] = r.get('clubs') or r['groups'] * r['size']
        elif j == n - 1:
            field[j] = 2
        else:
            field[j] = 2 * (field[j + 1] - known[j + 1] - out[j + 1] - feed[j + 1])
        if j in best:                                   # (the best runners-up: the places left, at most a group's)
            feed[j] += min(best[j], max(0, field[j] - known[j] - out[j] - feed[j]))
        if j < n - 1 and r['kind'] in ('groups', 'league_stage'):
            gap = field[j + 1] - known[j + 1] - out[j + 1] - feed[j + 1]
            if gap and outside == 'rest':
                out[j + 1] += gap
            elif gap:
                print(f"conti: {c['key']}:{rounds[j + 1]['key']} {gap} places left by the sizes")
    if outside == 'rest':
        out[0] += field[0] - known[0] - out[0] - feed[0]
    return field, out


def _norm(c):
    """A league stage as groups: its regions as groups of size clubs, one round (each pair once: the real 8 matches a
    club, declared), its 'out' ranges ('1-8') kept for the top-n routing."""
    for r in c['rounds']:
        for q, t in list((r.get('out') or {}).items()):  # ('qf_best': only that place's best clubs across the groups,
            if t.endswith('_best'):                      # as many as the next round has places left: ACGL's 3 best 2nds)
                r['out'][q] = t[:-5]
                r['best'] = int(q)
        if r['kind'] == 'league_stage':
            r.setdefault('groups', r.get('regions') or 2)
            r.setdefault('size', 16)
            r.setdefault('rounds', 1)
    return c


def _places(key):
    """'3' -> [3]; '1-8' -> [1..8]."""
    a, _, b = str(key).partition('-')
    return list(range(int(a), int(b or a) + 1))


IC_KEYS = {'cafcl': ('caf', 'cl')}       # (the Intercontinental's access file: holders by cup key)


def _cup_index(index, key):
    if key in IC_KEYS and IC_KEYS[key] in index:
        return index[IC_KEYS[key]]
    hits = [i for (cf, ck), i in index.items() if ck == key]
    return hits[0] if len(hits) == 1 else None


def _ic_holders(a, entries):
    """The Intercontinental's places: [(holder's cup key, round, slot, parity flag)]. Slots order the stepladder's
    fixed ties (draw 'slot'): r1 both 1 (its winner keeps 1), the African-Asian-Pacific tie = slots 1, 2, the
    Derby of the Americas = 3, 4, the final: the play-off winner v the UEFA holder (5). The AFC / CAF rotation:
    even editions as the access file's holders, odd ones its 'rotation'.odd (0x40 even only, 0x20 odd only)."""
    rot = a.get('rotation') or {}
    rotated = {k for side in rot.values() for ks in side.values() for k in ks}
    out = []
    for par, flag in (('even', 0x40), ('odd', 0x20)):
        for rk, keys in (rot.get(par) or {}).items():
            for k in keys:
                out.append((k, rk, 1 if rk == 'r1' else 2, flag))
    slots = {'lib': 3, 'ccc': 4, 'uefa:cl': 5}
    for k, rk in entries.items():
        if k not in rotated:
            out.append((k, rk, slots.get(k, 2), 0))
    return out


def load(confs, files=None, words=None, s1=None):
    """-> (spec bytes, [association pack keys], [(conf, cup key)]). files: {association key: its league team file}
    (the game's build; the tests: 100 + index), words: {club key: team word} (the ranking's clubs)."""
    cups, assocs = [], []
    for conf in confs:
        fm, ac = _read(conf, 'format'), _read(conf, 'access')
        assert fm, f'{conf}: no format file'
        acc = {c['key']: c for c in (ac or {}).get('cups', [])}
        for c in fm['cups']:
            _norm(c)
            if not supported(c):
                print(f"conti: {conf}:{c['key']} not built (a round kind / route the engine lacks)")
                continue
            cups.append((conf, c, acc.get(c['key'], {})))
            for a in acc.get(c['key'], {}).get('access', {}):
                if a not in ('holders', 'from', 'outside') and a not in assocs:
                    assocs.append(a)
    import guests as gmod
    gl, gin = [], {}                                    # the guests: (word, association index, strength)
    for conf in confs:
        g = gmod.load(conf)
        for i, c in enumerate((g or {}).get('clubs', [])):
            ak = 'g:' + c['assoc']
            if ak not in assocs:
                assocs.append(ak)
            rec = gmod.record(conf, i, c, 0)
            gin[(conf, c['key'])] = len(gl)
            gl.append((gmod.FILES[conf] | i << 8, assocs.index(ak), sum(rec[76 + 38 * j + 32] for j in range(16))))
    gs1 = {conf: (gmod.load(conf) or {}).get('season1', {}) for conf in confs}
    index = {(conf, c['key']): i for i, (conf, c, _) in enumerate(cups)}
    xlosers = {}                                        # (an access file's 'from': {'acl2:pre_losers': 'groups'}: that
    for conf, c, a in cups:                             # round's losers into this cup's round, as a format 'losers')
        for src, rk in ((a.get('access') or {}).get('from') or {}).items():
            sc, _, what = src.partition(':')
            if what.endswith('_losers'):
                xlosers[(conf, sc, what[:-7])] = f"{c['key']}:{rk}"
    for conf, c, a in cups:                             # (the short group stages: a 'clubs' count below the groups')
        for rk, n in (a.get('clubs') or {}).items():
            for r in c['rounds']:
                if r['key'] == rk:
                    r['clubs'] = n
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
    incoming = {}                                       # (cup, round) -> places from another cup's losers
    for ci, (conf, c, a) in enumerate(cups):
        rounds = c['rounds']
        known = [incoming.get((ci, j), 0) for j in range(len(rounds))]
        for ak, entries in (a.get('access') or {}).items():
            if ak == 'holders':
                for rk in entries.values():
                    known[rkey[ci][rk]] += 1
            elif ak not in ('from', 'outside'):
                for rk, _ in entries:
                    known[rkey[ci][ALIAS.get(rk, rk) if rk not in rkey[ci] else rk]] += 1
        gr = gs1.get(conf, {}).get(c['key']) or {}     # the guests' real places: they ARE the outside places
        for rk, keys in gr.items():
            known[rkey[ci][rk if rk in rkey[ci] else ALIAS.get(rk, rk)]] += len([k for k in keys if (conf, k) in gin])
        size, outside = fields(c, known, None if gr else (a.get('access') or {}).get('outside'))
        for j, r in enumerate(rounds):                  # (data's lists must close the sizes: a report, not a guess)
            feed = sum(rr['groups'] * len(_places(q)) for rr in rounds if rr['kind'] in ('groups', 'league_stage')
                       for q, t in (rr.get('out') or {}).items() if t == r['key'] and str(rr.get('best')) != str(q))
            win = size[j - 1] // 2 if j and rounds[j - 1]['kind'] == 'ko' else 0
            have = known[j] + outside[j] + feed + win
            for rr in rounds:                           # (the best runners-up: the places left, at most a group's)
                if rr.get('best') and rr['out'].get(str(rr['best'])) == r['key']:
                    have += min(rr['groups'], max(0, size[j] - have))
            if gr and have != size[j]:
                print(f"conti: {conf}:{c['key']}:{r['key']} {have} clubs for {size[j]} places (data's lists)")
        FIELDS[(conf, c['key'])] = size, outside, known
        for r in rounds:                                # (a group place into another cup's round)
            for t in (r.get('out') or {}).values() if r['kind'] in ('groups', 'league_stage') else ():
                if ':' in t and (conf, t.split(':')[0]) in index:
                    cj = index[(conf, t.split(':')[0])]
                    incoming[(cj, rkey[cj][t.split(':')[1]])] = incoming.get((cj, rkey[cj][t.split(':')[1]]), 0) + r['groups']
        lmap = dict(c.get('losers') or {})
        lmap.update({k[2]: v for k, v in xlosers.items() if k[:2] == (conf, c['key'])})
        for rk, t in lmap.items():
            if ':' in t:
                ck, tr = t.split(':')
                if (conf, ck) in index:
                    cj = index[(conf, ck)]
                    incoming[(cj, rkey[cj][tr])] = incoming.get((cj, rkey[cj][tr]), 0) + size[rkey[ci][rk]] // 2
        out = b''
        for j, rd in enumerate(rounds):
            dr, rule = _draw(rd)
            b = bytearray(RB)
            b[0] = K[rd['kind']]
            b[1] = rd.get('legs', 2 if rd['kind'] == 'ko' else 0)
            b[2] = LEVEL.get(rd.get('level', 'pens'), 0)
            b[3] = 1 if rd.get('host') in ('neutral', 'centralised') else 0
            b[4], b[5] = dr, rule
            if c.get('stepladder'):                     # (the Intercontinental: each club in its slot)
                b[4] = DRAW['slot']
            if rd['kind'] in ('groups', 'league_stage'):
                b[6], b[7], b[8] = rd['groups'], rd['size'], rd.get('rounds', 2)
                b[16] = 1 if (rd.get('draw') or {}).get('holder') else 0
            b[9] = rd.get('month') or (rd.get('months') or [8])[0]
            b[17] = 1 if j == main_round(c, size) and not c.get('stepladder') else 0   # (the Intercontinental: no
                                                # contest of its own, every game a tie; its final as 'main' loaded
                                                # ct_structs past the end: the trap after the Challenger Cup)
            b[18] = min(size[j], 255)                   # (the round's places: byes when the world cannot fill it)
            b[10] = CHAMP if j == len(rounds) - 1 else (ci << 4 | (j + 1))
            b[11] = OUT
            for q in range(4):
                b[12 + q] = OUT
            if rd['kind'] in ('groups', 'league_stage'):
                b[10] = OUT
                for q, t in (rd.get('out') or {}).items():
                    ps = _places(q)
                    if len(ps) > 1:                     # (a range: the top n into one round)
                        assert ps[0] == 1, (c['key'], q)
                        b[19], b[20] = len(ps), target(conf, ci, t)
                    else:
                        b[12 + ps[0] - 1] = target(conf, ci, t)
                if rd.get('best'):                      # (the best of that place: as many as the target has left)
                    tj = rkey[ci][rd['out'][str(rd['best'])]]
                    b[21] = rd['best']
                    b[22] = size[tj] - rd['groups'] * len([q for q in rd['out'] if q != str(rd['best'])]) - known[tj]
            lt = (c.get('losers') or {}).get(rd['key']) or xlosers.get((conf, c['key'], rd['key']))
            if lt:
                b[11] = target(conf, ci, lt)
            if rd.get('clubs'):                         # (a short group stage: no fill to its places)
                b[23] = 1
            out += bytes(b)
        body += bytes((len(rounds), 0, 0, 0)) + out
        if s1 is not None:                              # season 1 (the build): data's real entrants as fixed clubs
            for (cf, ck, rk), ws in s1.items():
                if (cf, ck) != (conf, c['key']):
                    continue
                for w, ak in ws:
                    if ak not in assocs:
                        assocs.append(ak)
                    gin[('s1', w)] = gin.get(('s1', w), len(gl))
                    if gin[('s1', w)] == len(gl):
                        gl.append((w, assocs.index(ak), 1))
                    access.append((0xFE, ci, rkey[ci][rk if rk in rkey[ci] else ALIAS.get(rk, rk)], gin[('s1', w)]))
        for ak, entries in ({} if s1 is not None else (a.get('access') or {})).items():
            if ak == 'holders' and c.get('stepladder'):  # the Intercontinental: the confederations' holders by slot
                for src, rk, slot, par in _ic_holders(a, entries):
                    si = 0xFF if src == 'uefa:cl' else _cup_index(index, src)
                    if si is not None:
                        holders.append((si, ci, rkey[ci][rk] | par, slot))
                continue
            if ak == 'holders':                         # (CAF: a holder qualified through its league keeps that
                own = a.get('holder_rule', 'own_place' if conf == 'caf' else 'extra') == 'own_place'   # one place)
                for src, rk in entries.items():
                    if (conf, src) in index:
                        holders.append((index[(conf, src)], ci, rkey[ci][rk] | (0x80 if own else 0), 0))
                continue
            if ak == 'from':
                continue
            if ak == 'outside':
                continue
            for rk, code in entries:
                rk = ALIAS.get(rk, rk) if rk not in rkey[ci] else rk
                k = CODE[code] if isinstance(code, str) else (0 if code <= 1 else code)
                access.append((assocs.index(ak), ci, rkey[ci][rk], k))
        for rk, keys in (gs1.get(conf, {}).get(c['key']) or {}).items():   # the guests' places (data's real list)
            j = rkey[ci][rk if rk in rkey[ci] else ALIAS.get(rk, rk)]
            for gk in keys:
                if (conf, gk) in gin and len(gin) < 255:
                    access.append((0xFE, ci, j, gin[(conf, gk)]))
        mine = [x for x in (a.get('access') or {}) if x not in ('holders', 'from', 'outside')]
        q = 0
        for j, k in enumerate(outside if s1 is None else ()):                 # the outside places left: the world associations' next clubs
            for _ in range(k):
                access.append((assocs.index(mine[q % len(mine)]), ci, j, CODE['next']))
                q += 1
    force = (0xFF, 0xFF)                                # CONTI_FORCE=<cup>:<round> (test builds only): the
    if os.environ.get('CONTI_FORCE'):                   # career club enters that round at every season end
        fk, fr = os.environ['CONTI_FORCE'].split(':')
        fc = next((i for i, (_, c, _) in enumerate(cups) if c['key'] == fk), None)
        if fc is not None:                              # (season1_native loads one confederation at a time)
            force = (fc, rkey[fc][fr])
            print(f'exe: CONTI_FORCE={fk}:{fr} (test build)')
    spec = bytes((len(cups), len(assocs)) + force) + body
    spec += struct.pack('<H', len(access)) + b''.join(bytes(x) for x in access)
    spec += bytes((len(holders),)) + b''.join(bytes(x) for x in holders)     # (src, dst, round | flags, slot)
    spec += bytes(0 if a.startswith('g:') else (files or {}).get(a, 100 + i) & 0xFF for i, a in enumerate(assocs))
    rank = {}
    for conf in confs:
        for k, v in ((_read(conf, 'access') or {}).get('ranking') or {}).items():
            if words and k in words:
                rank[words[k]] = min(int(round(v)), 0xFFFF)
    spec += struct.pack('<H', len(rank)) + b''.join(struct.pack('<HH', w, v) for w, v in sorted(rank.items()))
    spec += struct.pack('<H', len(gl)) + b''.join(struct.pack('<HBBI', w, a, 0, st) for w, a, st in gl)
    reg = {}                                            # (a league stage's regions: data's <conf>.<cup>_league.json)
    for conf in confs:
        for c in (_read(conf, 'format') or {}).get('cups', []):
            lg = _read(conf, c['key'] + '_league')
            for ri, (rn, rd) in enumerate((lg or {}).get('regions', {}).items()):
                for pot in rd.get('pots', []):
                    for e in pot:
                        a = e.get('assoc', '').lower()
                        for ak in (a, 'g:' + e.get('assoc', '')):
                            if ak in assocs:
                                reg.setdefault(ak, ri)
    spec += bytes(reg.get(a, 0xFF) for a in assocs)
    wf = bytearray(32)                                  # (the world's team files: a UEFA holder outside it - the
    for f in (files or {}).values():                    # game's own 1996-97 Champions Cup holder - is no finalist)
        wf[f >> 3] |= 1 << (f & 7)
    spec += bytes(wf)
    for conf, c, _ in cups:                             # (each cup's season-1 holder: season1_native's run)
        w, an, st = S1_HOLD.get((conf, c['key']), (0, None, 0))
        spec += struct.pack('<HBBI', w, assocs.index(an) if an in assocs else 0xFE, 0, st)
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
            if ak.startswith('g:'):
                continue
            base = 3000 if ak in ('bra', 'arg') else 1500
            for k in range(18):
                cid = (100 + a) | k << 8
                names[cid] = f'{ak}{k + 1}'
                clubs.append((cid, a, base + rnd.randint(0, 1500) - 60 * k, rnd.randint(100, 9000)))
        struct.pack_into('<IHH', b, 0, seed * 100 + season, len(clubs), int(os.environ.get('CONTI_TEST_MANAGER', 0)))
        for i, (cid, a, st, pt) in enumerate(clubs):
            struct.pack_into("<HBBII", b, o_club + 12 * i, cid, a, 0, st, pt)
        for a in range(len(assocs)):
            mine = sorted([i for i, c in enumerate(clubs) if c[1] == a], key=lambda i: -clubs[i][2] + rnd.randint(0, 900))
            if not mine:
                continue
            for l in range(min(NL, len(mine))):
                struct.pack_into('<H', b, o_league + 2 * (a * NL + l), mine[l] + 1)
            struct.pack_into('<H', b, o_cup + 2 * a, mine[rnd.randint(0, 6)] + 1)
        ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
        L.ct_finish()                               # (the game: ct_begin, the season end's first country)
        ctypes.memmove(IN, bytes(b), s_in)
        L.ct_season()
        if os.environ.get('CONTI_TEST_MANAGER'):    # phase B: the career club's games, one by one (random results)
            SEG = (ctypes.c_ubyte * 72).in_dll(L, 'CT_SEG')
            path = []
            for _ in range(20):
                g = bytes(SEG)
                if g[2] == 0xFF:
                    break
                cn = cups[g[0]][1]
                if g[2] == 0:
                    opp = struct.unpack_from('<H', g, 8 + 2 * (1 - g[7]))[0]
                    v = rnd.randint(0, 1)
                    path.append(f'{cn}:{g[1]} v {opp:#x} {"W" if v else "L"}')
                else:
                    v = rnd.randint(1, 4)
                    path.append(f'{cn}:{g[1]} groups ({g[3]}) place {v}')
                L.ct_result(v)
            print('    career club:', ' -> '.join(path) or 'no game')
            L.ct_season.restype = None
        o = bytes(OUTB)
        print(f'--- season {season + 1}')
        for ci, (conf, ck) in enumerate(cups):
            w, s2 = struct.unpack_from('<H', o, o_win + 2 * ci)[0], struct.unpack_from('<H', o, o_sec + 2 * ci)[0]
            ib = bytes(IN)                              # (club indices: the run's own, CT_ED's order)
            nm = lambda x: names.get(struct.unpack_from('<H', ib, o_club + 12 * (x - 1))[0], 'guest') if x else '-'
            counts = [o[o_nent + ci * NRD + r] for r in range(NRD)]
            print(f'{conf}:{ck} rounds {[c for c in counts if c]} winner {nm(w)} runner-up {nm(s2)}')
            if os.environ.get('CONTI_DUMP') == ck:
                for r in range(NRD):
                    if counts[r]:
                        es = struct.unpack_from(f'<{counts[r]}H', o, o_ent + 2 * (ci * NRD * NE + r * NE))
                        print('   ', r, [nm(x) for x in es])


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['--test']:
        test(sys.argv[2:] or ['conmebol'])


# --- the game ---------------------------------------------------------------------------------------------------------
PAGES = 6                               # obj1 pages: the C code + the glue (patch.py: after split's / statecup's)
BSS = 0x18000                           # obj2 .bss: CT_IN, CT_ST, CT_OUT, the edition (patch.py: in the career BSS)
CONFS = ['conmebol', 'concacaf', 'afc', 'caf', 'ofc', 'fifa']
LABELS = {}
ST_SIZE = 4 + 16 * 12                   # sizeof(struct ct_state)
ED_SIZE = 2260                          # sizeof(struct ct_ed) (phase B, the save's item 'CE')


BUILT = ['conmebol', 'concacaf', 'afc', 'caf', 'ofc']                    # (the confederations the engine handles so far; CONTI_CONFS: dev builds)


def ready():
    """The confederations built: in BUILT, with both files (format + access)."""
    want = os.environ.get('CONTI_CONFS', '').split(',') if os.environ.get('CONTI_CONFS') else BUILT
    return [c for c in CONFS if c in want and _read(c, 'format') and _read(c, 'access')]


def enabled():
    return bool(ready())


GLUE = r'''
ct_tab:                                 ; replaces `call cseg_927A2` (the season end's top 9 of a division): its whole
    pushad                              ; final order first (conti.c ct_table: up to 16 clubs, DIY = that division)
    push es
    push ds
    pop es
    cld
    push dword DIY
    call CT_TABLE
    add esp, 4
    pop es
    popad
    jmp C927A2

ct_ctry:                                ; replaces `call cseg_93974` (a country's qualifiers, Europe only): the
    pushad                              ; other confederations' input first (its table, the top 9 records, the cup
    push es                             ; winner's record), the first country of a season end clears it
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    cmp byte [ct_on], 0
    jne .on
    mov byte [ct_on], 1
    call CT_BEGIN
.on:
    push dword CUPREC + 2ACh
    push dword STAND
    call CT_COUNTRY
    add esp, 8
    pop es
    popad
    jmp C93974

ct_fill:                                ; careerworld w_ct_fill (the season end's record count, after uefaq's fill):
    cmp byte [ct_on], 0                 ; every country seen -> the editions
    je .r
    pushad
    mov byte [ct_on], 0
    push es
    push ds
    pop es
    cld
    call ct_lp
    movzx eax, word [SEL]
    movzx ecx, word [HOLD_CC]           ; (the UEFA Champions League holder: the Intercontinental's final)
    push ecx
    push dword [STAND]                  ; (a seed: changes every season)
    push eax
    call CT_GO
    add esp, 12
    pop es
    call ct_prep                        ; (phase B: the career club's first game: a tie into the ties' contest, which
    popad                               ; the season start's slot-3 chain finds as any contest)
.r:
    ret

; --- phase B: the career club's games one by one (conti.c ct_result / ct_resume; CT_SEG: cup, round, kind, n,
; round byte, level, month x 8, pos, the clubs) -----------------------------------------------------------------
ct_lp:                                  ; the contests' team lists for conti.c (CT_LP: BSS, empty after a load)
    ;CT_LP
    ret

ct_pre:                                 ; the season start's slot-3 chain, before conti's checks: after a load the
    push es                             ; exe's lists, CT_SEG empty -> both again from the saved edition
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    cmp word [CT_ED], 4543h
    jne .r
    call ct_lp
    call CT_RESUME
    call ct_prep
    mov eax, [CT_ED + 4]
    mov [ct_seen], eax
    mov al, [CT_ED + 10]
    mov [ct_seen + 4], al
.r:
    pop es
    ret

ct_prep:                                ; CT_SEG a tie -> the ties' contest (its cup's name, the two clubs, its round
    mov byte [ct_live], 0               ; byte, its month); ct_live: our tie is (or will be) in slot 3
    cmp byte [CT_SEG + 2], 0
    jne .r
    mov edi, TIE
    mov al, [CT_SEG + 6]
    mov [edi + 3], al
    add al, 2
    mov [edi + 4], al
    mov al, [CT_SEG + 4]
    mov [edi + 14], al
    movzx eax, byte [CT_SEG]
    push dword [ct_snames + eax * 4]    ; (the short name: the calendar's first line)
    mov eax, [ct_names + eax * 4]
    mov [edi + 16], eax
    pop dword [edi + 20]
    mov eax, [CT_SEG + 8]
    mov [edi + 24], eax
    movzx eax, byte [CT_SEG]            ; (its round's name: rnames' RN_TIE, from the cup and round)
    shl eax, 4
    or al, [CT_SEG + 1]
    mov al, [ct_rn + eax]
    mov [RN_TIE], al
    mov byte [ct_live], 1
.r:
    ret

ct_daily:                               ; before the next match (uefaq's uq_daily site, chained): our tie decided ->
    pushad                              ; ct_result, the next game into slot 3
    push es
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    mov eax, [CT_ED + 4]                ; (a load / another career: CT_SEG again from the saved edition)
    mov dx, [CT_ED]
    cmp eax, [ct_seen]
    jne .resume
    mov al, [CT_ED + 10]
    cmp al, [ct_seen + 4]
    je .chk
.resume:
    mov eax, [CT_ED + 4]
    mov [ct_seen], eax
    mov al, [CT_ED + 10]
    mov [ct_seen + 4], al
    cmp dx, 4543h
    jne .x
    call ct_lp                          ; (the lists again: the exe's after a load, conti.c rewrites the main one)
    call CT_RESUME
    call ct_prep
.chk:
    cmp byte [ct_live], 0
    je .x
    mov al, [SLOT3 + 2Dh]
    cmp al, TIE_ID
    jne .x
    mov ax, [SLOT3 + 39h]               ; the tie's winner (FFFF until it is decided)
    cmp ax, 0FFFFh
    je .x
    xor ecx, ecx
    cmp ax, [SEL]
    jne .l
    inc ecx
.l:
    push ecx
    call CT_RESULT
    add esp, 4
    mov al, [CT_ED + 10]
    mov [ct_seen + 4], al
    call ct_prep
    movzx eax, byte [CT_SEG + 2]
    cmp al, 0FFh
    je .none
    test al, 80h
    jnz .main
    mov dword [A0R], TIE                ; the next tie
    call ct_build
    mov word [E092F], TIE_D7
    mov word [CUP_KIND], 0
    jmp .x
.main:
    movzx ebx, byte [CT_SEG]            ; the cup's main round (its list: CT_LP, just written)
    cmp ebx, CT_NS                      ; (a cup with no contest of its own: none - never past the table)
    jae .none
    mov eax, [ct_structs + ebx * 4]
    mov [A0R], eax
    call ct_build
    add ebx, CT_D7
    mov [E092F], bx
    mov word [CUP_KIND], 0
    jmp .x
.none:
    mov word [E092F], -1                ; (out: the finished tie stays in slot 3, not reloaded)
.x:
    pop es
    popad
    jmp NEXT_DAILY

ct_build:                               ; [A0R] -> slot 3, as uefaq's .build: the played slot-3 calendar entries get
    pushad                              ; round FFh, the slot cleared, the stale type-2 stage reset, cseg_8B2D3
    mov esi, CAL
    movzx ecx, word [CAL_CUR]
    add ecx, esi
.c0:
    cmp esi, ecx
    jae .c1
    cmp byte [esi], 3
    jne .c2
    mov byte [esi + 7], 0FFh
.c2:
    movzx eax, word [esi + 2]
    test eax, eax
    jz .c1
    add esi, eax
    jmp .c0
.c1:
    mov edi, SLOT3
    mov ecx, 0B52h
    xor eax, eax
    rep stosb
    mov word [STAGE_G], 0
    mov word [D0R], 3
    mov word [D1R], 0
    mov word [D2R], 0
    call C8B2D3
    mov word [SLOT3 + 39h], 0FFFFh
    popad
    ret

ct_on: db 0
ct_live: db 0
align 4
ct_seen: dd 0, 0
ct_structs:
    ;CT_STRUCTS
ct_names:
    ;CT_NAMES
ct_snames:
    ;CT_SNAMES
ct_rn:                                  ; each cup's rounds' name index (rnames.CT_IDX; 16 per cup, 0 = the game's)
    ;CT_RN
ct_rntie: db 0                          ; (RN_TIE without rnames)
'''


def _world_maps(confs):
    """{association pack key: league team file}, {club key: team word} from the enabled World 2026-27 packs."""
    import mkseason
    files, words = {}, {}
    for pk in mkseason.packs():
        pid = pk.meta.get('id', '')
        if not pid.startswith('world-2026-27-'):
            continue
        key = pid[len('world-2026-27-'):]
        try:
            files[key] = pk.files[pk.league['clubs']][0]
        except (KeyError, TypeError, AttributeError):
            continue
        for k, (fl, n) in getattr(pk, 'where', {}).items():
            words[(key, k)] = fl | n << 8               # (club keys repeat across associations: HURACAN ARG / URU)
            words[k] = None if k in words and words[k] != fl | n << 8 else fl | n << 8
    return files, {k: v for k, v in words.items() if v is not None}


def patch(p, at, limit, bss_at, area):
    """conti.c + its glue at obj1:at (..limit), .bss at obj2:bss_at; returns the code end. World 2026-27 only."""
    import re
    import cobj
    import nasmcave
    import sacups
    import careerworld as cw
    import engine
    import lib97
    confs = ready()
    files, words = _world_maps(confs)
    spec, assocs, cups = load(confs, files, words)
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    t927 = [m.start() for m in re.finditer(rb'\xc7\x05' + A(a0 + 4) + rb'.{4}\xc7\x05' + A(a0 + 12) + rb'.{4}\xc7\x05' +
                                           A(a0 + 8) + rb'.{4}\xa1' + A(a0 + 8) + rb'\x83\xc0\x6d', d1, re.S)]
    t939 = [m.start() for m in re.finditer(rb'\xa0.{4}\xa2' + A(a0 - 32) + rb'\x66\x81\x25' + A(a0 - 32) +
                                           rb'\xff\x00\x66\xc1\x25' + A(a0 - 32) + rb'\x02\xc7\x05' + A(a0), d1, re.S)]
    assert len(t927) == 1 and len(t939) == 1, (t927, t939)
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]
    c927, c939 = calls(t927[0]), calls(t939[0])
    assert len(c927) == 2 and len(c939) == 2, (c927, c939)
    obj = cobj.compile_c(os.path.join(ROOT, 'tools', 'conti.c'))
    syms, end, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= BSS, hex(bss)
    q = cw._qual_sites(d1, p)
    symbols = {'DIY': (2, lib97._sites(p)[3] + 0x41F), 'STAND': q['STAND'], 'CUPREC': q['CUPREC'],
               'SEL': (2, sacups.SEL_ADDR[0]), 'HOLD_CC': q['HOLD_CC'], 'SPEC': (1, (end + 15) & ~15), 'C927A2': (1, t927[0]),
               'C93974': (1, t939[0]), 'CT_SPEC': syms['CT_SPEC'], 'CT_TABLE': syms['ct_table'],
               'CT_BEGIN': syms['ct_begin'], 'CT_COUNTRY': syms['ct_country'], 'CT_GO': syms['ct_go']}
    lp = []
    for ci, off, lst, n in STRUCTS:                     # the contests' lists (conti.c writes the main rounds there)
        symbols[f'LIST{ci}'] = (1, lst)
        lp.append(f'    mov dword [CT_LP + {4 * ci}], LIST{ci}')
    symbols['CT_LP'] = syms['CT_LP']
    import uefaq
    u = uefaq.SYMS
    assert u, 'conti phase B: uefaq (the daily site, slot 3) first'
    for i, (ci, off, lst, n) in enumerate(STRUCTS):
        symbols[f'XST{i}'] = (1, off)
    symbols.update({k: u[k] for k in ('SLOT3', 'CAL', 'CAL_CUR', 'STAGE_G', 'D0R', 'D1R', 'D2R', 'C8B2D3', 'A0R',
                                      'E092F', 'CUP_KIND')})
    symbols.update(NEXT_DAILY=u['uq_daily'], TIE=(1, TIE[0]), TIE_ID=(0, p.get(1, TIE[0], 1)[0]),
                   TIE_D7=(0, D7_BASE[0] + len(STRUCTS)), CT_D7=(0, D7_BASE[0]), CT_SEG=syms['CT_SEG'], CT_NS=(0, len(STRUCTS)),
                   CT_ED=syms['CT_ED'], CT_RESULT=syms['ct_result'], CT_RESUME=syms['ct_resume'])
    asm = GLUE.replace("    ;CT_LP", "\n".join(lp)).replace(
        "    ;CT_STRUCTS", "\n".join(f'    dd XST{i}' for i in range(len(STRUCTS))) or '    dd 0').replace(
        "    ;CT_NAMES", "\n".join(f'    dd {r}' for r in NAMES) or '    dd 0').replace(
        "    ;CT_SNAMES", "\n".join(f'    dd {r}' for r in SNAMES) or '    dd 0')
    import rnames
    rn = [rnames.CT_IDX.get((ci, j), 0) for ci in range(16) for j in range(16)]
    asm = asm.replace("    ;CT_RN", '    db ' + ', '.join(map(str, rn)))
    if 'RN_TIE' in rnames.LABELS:
        symbols['RN_TIE'] = (1, rnames.LABELS['RN_TIE'])
    else:
        asm = asm.replace('[RN_TIE]', '[ct_rntie]')
    bad = {k: v for k, v in symbols.items() if not (isinstance(v, tuple) and isinstance(v[1], int))}
    assert not bad, bad
    spec_at = (end + 15) & ~15                          # (the spec in our own pages: the obj2 string area is
    p.put(1, spec_at, spec)                             # nearly full with five confederations' names)
    glue = (spec_at + len(spec) + 15) & ~15
    code, fix = nasmcave.assemble(asm, glue, symbols)
    lab = nasmcave.labels(asm, glue, symbols)
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    rel = lambda a, to: struct.pack('<i', to - (a + 5))
    for c in c927:
        p.put(1, c + 1, rel(c, lab['ct_tab']))
    for c in c939:
        p.put(1, c + 1, rel(c, lab['ct_ctry']))
    pp = sacups.CT_PRE_PTR[0]                           # (the season start's chain calls ct_pre through it)
    p.put(1, pp, struct.pack('<I', lab['ct_pre']))
    cobj.add_ptr(p, pp, 1, lab['ct_pre'])
    site = u['DAILY_SITE']                              # (the daily site: ours first, then uefaq's uq_daily)
    p.put(1, site + 1, rel(site, lab['ct_daily']))
    a = cw.LABELS['w_ct_fill']
    p.put(1, a, b'\xe9' + rel(a, lab['ct_fill']))
    assert struct.unpack('<I', p.get(1, syms['CT_LAYOUT'][1] + 4, 4))[0] == ST_SIZE      # (engine item 'CT')
    engine.ITEM_AT['CT'] = syms['CT_ST']
    assert struct.unpack('<I', p.get(1, syms['CT_LAYOUT'][1] + 80, 4))[0] == ED_SIZE
    if 'CE' in engine.SAVE_ITEMS:
        engine.ITEM_AT['CE'] = syms['CT_ED']
    LABELS.update(lab, syms=syms, assocs=assocs, cups=cups)
    print(f'exe: other confederations\' cups (conti.c): {len(cups)} cups of {", ".join(confs)}, '
          f'{len(assocs)} associations, spec {len(spec)} B; C obj1+{at:#x}..{end:#x}, glue ..{glue + len(code):#x}, '
          f'bss obj2+{bss_at:#x} ({bss} B)')
    return glue + len(code)


# --- season 1: the 2027 editions' main rounds at build time ---------------------------------------------------------
def season1(confs, files, words, seed=2027, stand_ins_only=False):
    """{(conf, cup key): [team words of the main round, in the drawn order]} from the access files' entrants_season1
    (data: the real 2027 entrants where known, else the access list on the starting tables). Rounds before the main
    one are simulated here (seeded, 50/50 or by the ranking); a vacant holder place (holders_season1 None: the 2026
    finals come after the release) goes to the best-placed club not in any cup of the top-ranked associations (BRA,
    ARG, ...), the same clubs stand in as the Recopa's pair. Declared in the notes."""
    import random
    rnd = random.Random(seed)
    out = {}
    for conf in confs:
        fm, ac = _read(conf, 'format'), _read(conf, 'access') or {}
        acc = {c['key']: c for c in ac.get('cups', [])}
        rank = {words[k]: v for k, v in (ac.get('ranking') or {}).items() if k in words}
        top = sorted({e['assoc'] for c in acc.values() for e in c.get('entrants_season1') or []},
                     key=lambda a: ('bra', 'arg').index(a) if a in ('bra', 'arg') else 9)
        taken = {words[(e['assoc'], e['club'])] for c in acc.values() for e in c.get('entrants_season1') or []}

        def stand_in(i):
            if rank:
                return max((w for w in rank if w not in taken), key=rank.get)
            a = top[i % len(top)]
            return min((w for k, w in words.items() if isinstance(k, tuple) and w & 0xFF == files[a] and w not in taken),
                       key=lambda w: w >> 8)

        subs = []
        extra = {}                                      # (cup key, round key) -> words moved in (losers, holders)
        afile = {v: k for k, v in files.items()}
        held = {}
        for c in fm['cups']:
            a = acc.get(c['key'], {})
            own = a.get('holder_rule', 'own_place' if conf == 'caf' else 'extra') == 'own_place'
            for h, w in (a.get('holders_season1') or {}).items():
                if w is None:
                    if own:                             # (CAF: no extra place for a holder)
                        continue
                    w = held.get(h) or stand_in(len(subs))
                    if w not in subs:
                        taken.add(w)
                        subs.append(w)
                else:
                    w = words.get(w)
                    if w is None:
                        continue
                held[h] = w
                rk = (a.get('access') or {}).get('holders', {}).get(h)
                if rk:
                    extra.setdefault((c['key'], ALIAS.get(rk, rk)), []).append(w)
        if stand_ins_only:
            res = {}
            for (ck, rk), ws in extra.items():
                res[(conf, ck, rk)] = [(w, afile.get(w & 0xFF, '?')) for w in ws]
            for c in fm['cups']:                        # (the Recopa: the two stand-in holders)
                if not acc.get(c['key'], {}).get('entrants_season1') and len(c['rounds']) == 1 and len(subs) >= 2 \
                        and not any(k[0] == c['key'] for k in extra):
                    res[(conf, c['key'], c['rounds'][0]['key'])] = [(w, afile.get(w & 0xFF, '?')) for w in subs[:2]]
            out.update(res)
            continue
        for c in fm['cups']:
            a = acc.get(c['key'], {})
            j0 = main_round(c)
            rk = {r['key']: r for r in c['rounds']}
            ent = {}
            for e in a.get('entrants_season1') or []:
                r = ALIAS.get(e['round'], e['round'])
                ent.setdefault(r, []).append((words[(e['assoc'], e['club'])], e['assoc']))
            if not ent and not any(k[0] == c['key'] for k in extra):
                if c['key'] == 'rec' and len(subs) >= 2:
                    out[(conf, c['key'])] = subs[:2]
                continue
            if c['key'] == 'rec' and not ent and len(subs) >= 2:
                out[(conf, c['key'])] = subs[:2]
                continue
            asc = {w: e for r in ent.values() for w, e in r}
            for w in [x for v in extra.values() for x in v]:
                asc.setdefault(w, next((k for k, f in files.items() if f == w & 0xFF), '?'))
            win = []
            for j, rd in enumerate(c['rounds'][:j0 + 1]):
                field = win + [w for w, _ in ent.get(rd['key'], [])] + extra.get((c['key'], rd['key']), [])
                if j == j0:
                    break
                d = rd.get('draw') or {}
                if isinstance(d, dict) and d.get('kind') == 'same_assoc_pairs':
                    by = {}
                    for w in field:
                        by.setdefault(asc[w], []).append(w)
                    field = [w for v in by.values() for w in v]
                else:
                    field = sorted(field, key=lambda w: -rank.get(w, 0))
                    h = len(field) // 2
                    field = [x for t in zip(field[:h], rnd.sample(field[h:], h)) for x in t]
                assert len(field) % 2 == 0, (c['key'], rd['key'], len(field))
                win, lose = [], []
                for x, y in zip(field[::2], field[1::2]):
                    rx, ry = rank.get(x, 1), rank.get(y, 1)
                    wx = rnd.random() < rx / (rx + ry)
                    win.append(x if wx else y)
                    lose.append(y if wx else x)
                lt = (c.get('losers') or {}).get(rd['key'])
                if lt:
                    ck, rr = lt.split(':')
                    extra.setdefault((ck, rr), []).extend(lose)
            rd = c['rounds'][j0]
            if rd['kind'] == 'groups':
                n, g = rd['groups'] * rd['size'], rd['groups']
                assert len(field) == n, (c['key'], len(field), n)
                rule = (rd.get('draw') or {}).get('same_assoc', 'no')
                direct = {w for w, _ in ent.get(rd['key'], [])}
                order = sorted(field, key=lambda w: (-rank.get(w, 0), w not in direct))
                pots = [order[i * g:(i + 1) * g] for i in range(rd['size'])]
                groups = None
                for _ in range(2000):
                    gs = [[] for _ in range(g)]
                    ok = True
                    for pi, pot in enumerate(pots):
                        for w in rnd.sample(pot, g):
                            free = [i for i in range(g) if len(gs[i]) == pi and (rule == 'allow' or not any(
                                asc[w] == asc[x] and (rule == 'no' or (w in direct and x in direct)) for x in gs[i]))]
                            if not free:
                                ok = False
                                break
                            gs[rnd.choice(free)].append(w)
                        if not ok:
                            break
                    if ok:
                        groups = gs
                        break
                assert groups, (c['key'], 'no draw')
                out[(conf, c['key'])] = [w for gr in groups for w in gr]
            else:
                out[(conf, c['key'])] = field
    return out


def season1_native(confs, files, words):
    """{(conf, cup key): [team words of the main round, drawn]}: conti.c itself on data's season-1 entrants (the
    access files' entrants_season1 + holders_season1, the guests' season1), natively at the build: the rounds before
    the main one simulated (strength: none, 50/50), the same draws / byes / fills as in the game. Vacant season-1
    holder places: the best-placed clubs in no cup of the top associations (season1()'s stand-ins)."""
    import ctypes
    L = _native()
    out = {}
    for conf in confs:
        fm, ac = _read(conf, 'format'), _read(conf, 'access') or {}
        if all(c.get('stepladder') for c in fm['cups']):
            continue                                    # (the Intercontinental: no contest of its own)
        acc = {c['key']: c for c in ac.get('cups', [])}
        s1 = {}
        for c in fm['cups']:
            for e in (acc.get(c['key'], {}).get('entrants_season1') or []):
                w = words.get((e['assoc'], e['club']))
                if w is not None:
                    s1.setdefault((conf, c['key'], e['round']), []).append((w, e['assoc']))
        base = season1([conf], files, words, stand_ins_only=True)
        for (cf, ck, rk), ws in base.items():
            s1.setdefault((cf, ck, rk), []).extend(ws)
        spec, assocs, cups = load([conf], files, words, s1=s1)
        lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
        buf = ctypes.create_string_buffer(spec, len(spec))
        ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
        ctypes.memset(ctypes.addressof(ctypes.c_ubyte.in_dll(L, 'CT_IN')), 0, lay[0])
        lists = [(ctypes.c_uint16 * 32)(*([0xFFFF] * 32)) for _ in cups]
        lp = (ctypes.c_void_p * 16).in_dll(L, 'CT_LP')
        for i in range(16):
            lp[i] = ctypes.addressof(lists[i]) if i < len(cups) else None
        L.ct_season()
        o, ib = bytes((ctypes.c_ubyte * lay[2]).in_dll(L, 'CT_OUT')), bytes((ctypes.c_ubyte * lay[0]).in_dll(L, 'CT_IN'))
        for i, (cf, ck) in enumerate(cups):             # (the 2027 editions' winners: the first season end's holders)
            w = struct.unpack_from('<H', o, lay[8] + 2 * i)[0]
            if w:
                cid, ca, _, cs = struct.unpack_from('<HBBI', ib, lay[7] + 12 * (w - 1))
                S1_HOLD[(cf, ck)] = (cid, assocs[ca] if ca < len(assocs) else '?', cs)
        for i, (cf, ck) in enumerate(cups):
            c = next(x for x in fm['cups'] if x['key'] == ck)
            rd = c['rounds'][main_round(c)]
            n = rd['groups'] * rd['size'] if rd['kind'] == 'groups' else 2 ** (len(c['rounds']) - main_round(c))
            ws = list(lists[i])[:n]
            if any(w != 0xFFFF for w in ws):
                out[(cf, ck)] = ws
        for i in range(16):
            lp[i] = None
    return out


# --- the career club's contests (the slot-3 chain) --------------------------------------------------------------------
IDS = [0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD0, 0xD1, 0xDA, 0xDD, 0xDE, 0xDF, 0xEC, 0xED, 0xEE, 0xEF]   # (mkseason.RESERVED_IDS)
STRUCTS = []                            # [(cup index, struct offset, team list offset, list length)]
D7_BASE = [0]                           # (patch.py: sacups' D7 / E092F of the first one)
NAMES = []                              # each cup's name (rel to sacups.STR_BASE)
SNAMES = []                             # its short name, the career calendar's first line (complist.fit_short, 70 px)
TIE = [None]                            # the ties' contest (obj1), D7 = D7_BASE + len(STRUCTS)
CUPROUNDS = []                          # each cup's rounds (format), by cup index: rnames' names per round
SROUNDS = []                            # per struct: the round index of its rounds / stages (rnames' RN_CTMAP)
SKINDS = []                             # per struct: 1 type 1 (a knockout), 2 type 2 (groups + knockouts)


def _short(c, lang):
    """A cup's short name for the career calendar's first line: fitted before the (C) / (F) marker (CAL_PX)."""
    import complist
    sh = complist.fit_short((c['names'].get(lang) or c['names']['en'])[1])
    assert complist.px(sh) <= complist.CAL_PX and all(ch in complist.FONT for ch in sh), (c['key'], lang, sh)
    return sh.encode('latin1')


def _legs(rd):
    """The game's round byte: bits 7-6 legs (2), 5-4 extra time, 3-2 penalties."""
    if rd.get('legs', 2) == 2:
        return 0x94 if rd.get('level') == 'et_pens' else 0x84
    return 0x14


def _month(m):                          # the contest's months: x 8 from January, a season's Jan-Jul in the next year
    return (m - 1 + (12 if m < 8 else 0)) * 8


def structs(p, area, lang, at):
    """The career club's contests (one per cup: its main round as the game's own contest) at obj1:at; returns (end,
    [(1, struct offset)], [euro rank per struct]) for sacups' slot-3 chain (D7 / E092F = 6 + index)."""
    import sacups
    import mkseason
    confs = ready()
    used = {int(str(c['id']), 16) for pk in mkseason.packs() if pk.meta.get('id', '').startswith('world-2026-27-')
            for c in pk.meta.get('competitions', []) if c.get('id')}
    assert not used & set(IDS), ('conti: World 2026-27 packs use its contest ids', sorted(used & set(IDS)))
    d2 = p.le.obj_bytes(2)
    euro = sacups.unique(d2, sacups.EUROCUP_HDR)
    cwc = sacups.unique(d2, sacups.CWC_HDR)
    out, kinds = [], []
    STRUCTS.clear()
    NAMES.clear()
    SNAMES.clear()
    CUPROUNDS.clear()
    SROUNDS.clear()
    SKINDS.clear()
    files, words = _world_maps(confs)
    first = season1_native(confs, files, words)         # (the 2027 editions' main rounds: the contests' lists)
    ci = 0
    for conf in confs:
        for k, c in enumerate(c for c in _read(conf, 'format')['cups'] if supported(c)):
            CUPROUNDS.append(c['rounds'])
            SNAMES.append(area.add(_short(c, lang) + b'\0') - sacups.STR_BASE)
            if c.get('stepladder'):                     # (the Intercontinental: its games as ties only; its name)
                nm = (c['names'].get(lang) or c['names']['en'])[0].upper().encode('latin1')[:30]
                NAMES.append(area.add(nm + b'\0') - sacups.STR_BASE)
                ci += 1
                continue
            assert ci < len(IDS), 'conti: more cups than ids'
            cid, j0 = IDS[ci], main_round(c)
            rd, rounds = c['rounds'][j0], c['rounds']
            nm = (c['names'].get(lang) or c['names']['en'])[0].upper().encode('latin1')[:30]
            rel = area.add(nm + b'\0') - sacups.STR_BASE
            last = rounds[-1].get('month') or 5
            if rd['kind'] == 'groups':
                body = bytearray(d2[euro:euro + 47])
                body[0] = cid
                n = rd['groups'] * rd['size']
                ko = [r for r in rounds[j0 + 1:] if r['kind'] == 'ko'][-4:]
                kn = len(ko)                                # (stages: the groups, then kn knockout rounds of
                st = [1 + kn, n, rd['groups'], rd['size']]  # 2^kn .. 2 clubs; the winners count; a round byte per
                for t in range(kn):                         # stage from +22h: the groups' 0, then the knockouts')
                    st += [2 ** (kn - t), 0, 2 ** (kn - t)]
                st += [1] + [0] * (20 - len(st) - 1)
                st += [0] + [_legs(r) for r in ko] + [0] * (4 - kn)
                assert len(st) == 0x27 - 0x0e and 1 <= kn <= 4, (c['key'], kn, len(st))
                body[0x0e:0x27] = bytes(st)
                body[9] = 0                                 # (every round through the game's own draw: our list order)
                body[3], body[4] = _month((rd.get('months') or [10])[0]), _month(last)
                name_at = 39
            else:
                ko = rounds[j0:]
                n = 2 ** len(ko)
                body = sacups.knockout16(d2[cwc:cwc + 28], cid, n, tuple(_legs(r) for r in ko))
                body[3], body[4] = _month(rd.get('month') or 8), _month(last)
                if body[4] <= body[3]:                  # (a one-round cup, the Recopa / CAF Super Cup: a month's window,
                    body[4] = body[3] + 8               # as the game's Intercontinental 58h / 60h)
                name_at = len(body)
            if rd['kind'] == 'groups':                  # (away goals after 90': the type-2 header's byte; a knockout
                body[0x0a] = 1 if any(r.get('level') == 'away_pens' for r in rounds) else 0   # header's +0Ah is its
                                                                                              # clubs: CONCACAF had 1)
            ws = list(first.get((conf, c['key'])) or [])
            assert len(ws) in (0, n), (c['key'], len(ws), n)
            g = os.environ.get('CONTI_GUEST')           # (test builds: 'cup:guest word[,guest word..]:club word', hex -
            if g and g.split(':')[0] == c['key']:       # the guests in place of the career club's next group-mates /
                _, gws, cw = g.split(':')               # its opponent)
                if int(cw, 16) in ws:
                    i = ws.index(int(cw, 16))
                    sz = rd['size'] if rd['kind'] == 'groups' else 2
                    for k, gw in enumerate(gws.split(',')[:sz - 1]):
                        ws[i - i % sz + (i % sz + 1 + k) % sz] = int(gw, 16)
            ws = ws or [0xFFFF] * n
            blob = bytes(body[:name_at]) + struct.pack('<II', rel, SNAMES[-1]) + struct.pack(f'<{n}H', *ws)
            assert blob[5] + 5 == name_at and blob[7] + 7 == name_at + 8, c['key']
            p.put(1, at, blob)
            NAMES.append(rel)
            STRUCTS.append((ci, at, at + name_at + 8, n))
            if rd['kind'] == 'groups':
                SROUNDS.append([j0] + [rounds.index(r) for r in ko])
                SKINDS.append(2)
            else:
                SROUNDS.append(list(range(j0, len(rounds))))
                SKINDS.append(1)
            out.append(at)
            kinds.append(min(k, 2))                         # (the trophy's rank: the first cup as the Champions Cup)
            at += (len(blob) + 3) & ~3
            ci += 1
    # phase B: the career club's ties (a qualifying round, a knockout round before the main one): one 2-club
    # knockout contest, rewritten by the glue for each tie (its cup's name, the two clubs, the round byte, months)
    body = sacups.knockout16(d2[cwc:cwc + 28], IDS[len(out)], 2, (0x84,))
    rel = NAMES[0] if NAMES else 0
    blob = bytes(body) + struct.pack('<II', rel, SNAMES[0] if SNAMES else 0) + struct.pack('<2H', 0xFFFF, 0xFFFF)
    assert blob[5] + 5 == len(body) and len(body) == 16
    p.put(1, at, blob)
    TIE[0] = at
    out.append(at)
    kinds.append(0)
    at += (len(blob) + 3) & ~3
    print(f'exe: other confederations\' contests (slot-3 chain): {len(out)} at obj1+{out[0] if out else at:#x} '
          '(the last: the career club\'s ties)')
    return at, out, kinds
