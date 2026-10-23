"""4.0.1: the World 2026-27 national and league cups follow promotions and relegations (Davide: MESTRE promoted to
Serie C played no COPPA ITALIA SERIE C).

A world cup is a type-1 struct with a FIXED team list (mkseason: the pack's ties.csv round-1 clubs + byes), the same
every season. Here each cup's format is read from that real list as counts per division of the league file: n_d
entrants, b_d of them byes (e.g. COPPA ITALIA SERIE C: C/A 5 + C/B 7 + C/C 5, byes 5 / 7 / 3; COPA DEL REY: Primera
20 + Segunda 21, byes 20 + 3). From the world's second season gplay.c cf_list_c rebuilds the list from the clubs'
CURRENT divisions (someLeaguesTable), the career club first when its division takes part, the others in a
deterministic order (season, cup id); the first season keeps the real list and its bracket (lib97 fixed draws).
Hooks: cf_a6 at the fixed list's `mov [A6], eax` (the game's own copy then reads the new words), and gplay's gp_notin
(rule 11) asks cf_member_c, so the cup shows for the clubs that play it. Stateless: no save change, no load hook.
A cup with a club outside the league file (cuponly / pool / another country) keeps its fixed list (declared).
"""
import struct

import mkseason


def pack_cups(pk):
    """[(id, n, [(division, n_d, b_d)])] of a world pack's cups whose real clubs are all league-file clubs."""
    if pk.world is None or not pk.league:
        return [], None
    lfile = pk.files[pk.league['clubs']][0]
    out = []
    for c in pk.comps:
        if c['type'] != 'cup':
            continue
        br = pk.bracket(c)
        keys, nb = br['clubs'], br['byes']
        if not all(k in pk.where and pk.where[k][0] == lfile and k in pk.division for k in keys):
            continue
        groups = {}
        for j, k in enumerate(keys):
            d = pk.division[k]
            e = groups.setdefault(d, [0, 0])
            e[0] += 1
            e[1] += j >= len(keys) - nb
        gs = [(d, n, b) for d, (n, b) in sorted(groups.items())]
        assert len(keys) <= 64 and all(n <= 255 for _, n, _ in gs)
        out.append((int(c['id'], 16), len(keys), gs))
    return out, lfile


SEED = int(__import__('os').environ.get('CF_SEED') or 0)   # the order within a division (gplay.c CF_SEED): 0 = last season's place (Davide's rule B, literal: a
                # promoted / relegated club by its place in its old division); 1 = relegated clubs, then the stayers,
                # then the promoted, each by place (regia's option 2, pending Davide; CF_SEED=1 test builds)


def levels(pk):
    """Division -> level (the parallel groups of one level share it: Serie C A / B / C = one level)."""
    divs = pk.divisions()
    par = pk.league.get('parallel') or []
    par = par if isinstance(par, list) else [par]
    grp = {q['first']: q['count'] for q in par}
    out, lv, d = {}, 0, 0
    while d < len(divs):
        n = grp.get(d, 1)
        for k in range(n):
            out[d + k] = lv
        lv += 1
        d += n
    assert lv <= 7 and len(divs) <= 16, (lv, len(divs))
    return [out.get(d, 0) for d in range(16)]


def dt_bytes(pk, lfile):
    gbase = next(b for ff, b in pk.files.values() if ff == lfile)
    pairs = sorted((pk.where[k][1], pk.division[k]) for k in pk.league_clubs if pk.where[k][0] == lfile)
    assert len(pairs) <= 256
    assert max(d.get('teams', 0) for d in pk.divisions()) <= 31, 'cupsf: places stored in 5 bits'
    return struct.pack('<HBH', gbase, lfile, len(pairs)) + bytes(levels(pk)) + b''.join(bytes(x) for x in pairs)


def table(world):
    """CF_TAB bytes of a world (gplay.c), or None (no cups to follow)."""
    cups, dts = [], []
    for pk in mkseason.packs():
        if pk.world != world:
            continue
        cs, lfile = pack_cups(pk)
        if not cs:
            continue
        dts.append(dt_bytes(pk, lfile))
        for cid, n, gs in cs:
            cups.append((cid, n, gs, len(dts) - 1))
    if not cups:
        return None
    year = globals()['year'](world) - 1900
    out = bytearray((world, year, len(cups)))
    for cid, n, gs, di in cups:
        out += bytes((cid, n, len(gs), di)) + b''.join(bytes(g) for g in gs)
    out += bytes((len(dts),)) + b''.join(dts)
    print(f'exe: cups follow promotions (world {world}): {len(cups)} cups, {len(dts)} league files')
    return bytes(out)


def worlds():
    return sorted({pk.world for pk in mkseason.packs() if pk.world is not None})


def year(world):
    """The world's first season (world_cups.start_year)."""
    return next(w['year'] for w in mkseason.world_defs() if w['n'] == world)
