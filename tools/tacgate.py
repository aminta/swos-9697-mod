"""4.2 club tactics + real Serie A / B line-ups (Motore; MC 14/11 spot-check, Regia harness (b)): in a new World 2026-27
career the game must hold every club with its DATA record's tactic and lineup, and the managed club must start the
real XI with the real bench (internal/world2526/reallineups.txt of the data dir).
Registered by swostest (register(mod), as fpgate) or run alone: python3 tools/tacgate.py <scenario>."""
import os, re, struct, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
T = None
CAREER = ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'MONDO 2026-27', 'EUROPA', 'ITALIA']


def data_dir():
    return os.environ.get('W2627REL_DATA') or os.path.join(T.MAIN, 'internal', 'world2526', 'world5tm-h3l')


def exe_for(tag):
    """TACGATE_BUILD (a built exe dir), else a build of the data dir (SKIP without the private data)."""
    if os.environ.get('TACGATE_BUILD'):
        return os.environ['TACGATE_BUILD'], None
    src = data_dir()
    if not os.path.isdir(src):
        return None, f'SKIP: private data {src} missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    return T.build(tag, env={'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])}), None


def records(exe):
    """{name: 684-byte record} of every team file of the build's DATA (TEAM.1xx: the world's)."""
    out = {}
    d = os.path.join(exe, 'DATA')
    for f in sorted(os.listdir(d)):
        if re.fullmatch(r'TEAM\.1\d\d', f):
            b = open(os.path.join(d, f), 'rb').read()
            n = struct.unpack('>H', b[:2])[0]
            for i in range(n):
                r = b[2 + 684 * i:2 + 684 * (i + 1)]
                out.setdefault(r[5:22].split(b'\0')[0].decode('latin-1'), r)
    return out


def pname(r, q):
    return bytes(r[76 + 38 * q + 3:76 + 38 * q + 26]).split(b'\0')[0].decode('latin-1')


def expected(club):
    """(XI names, bench names) of reallineups.txt for club, or None."""
    f = os.path.join(data_dir(), 'reallineups.txt')
    for ln in open(f) if os.path.exists(f) else []:
        if ln.startswith(club + ' ['):
            xi = [re.sub(r' \d+$', '', x) for x in ln.split('XI ', 1)[1].split(' | ')[0].split(', ')]
            be = [re.sub(r' \d+$', '', x) for x in ln.split('bench ', 1)[1].split(' | ')[0].split(', ')]
            return xi, be
    return None


def run(path, club, tag):
    import lepatch, mkseason, xtra
    exe, skip = exe_for(tag)
    if skip:
        return True, skip
    recs = records(exe)
    want = recs.get(club)
    if want is None:
        return False, f'{club} not in the DATA team files of {exe}'
    errs, info = [], []
    _, cnp, ct, cmp_, _ = xtra.sites(lepatch.LEPatch(os.path.join(exe, 'ITALIAN.EXE')))
    with T.Session('tacgate_' + tag, exe, {}, 'dump:2', 600) as s:
        s.wait()
        for t in CAREER + list(path) + [club]:
            if T.press(s, s.screen(), t, 3) is None:
                return False, f'new career: {t} not reached ({s.screen().texts()[:6]})'
        s.send('fire dump:3')
        r = s.result
        rec = r.obj2(ct, 684)
        n = struct.unpack('<H', r.obj2(cnp, 2))[0]
        order = list(r.obj2(cmp_, n))
        T.check(rec[5:22] == want[5:22], f'careerTeam {rec[5:22]!r} is not {club}', errs)
        T.check(rec[24] == want[24], f'{club} tactic {rec[24]} != DATA {want[24]}', errs)
        T.check(bytes(rec[60:76]) == bytes(want[60:76]), f'{club} lineup {list(rec[60:76])} != DATA {list(want[60:76])}', errs)
        xi = [pname(rec, q) for q in order[:11]]
        be = [pname(rec, q) for q in order[11:16]]
        tac = mkseason.TACTICS[rec[24]] if rec[24] < 12 else rec[24]
        pos = [rec[76 + 38 * q + 26] >> 5 for q in order[:11]]
        cls = [sum(1 for p in pos if mkseason._POS_CLASS[p] == c) for c in (1, 2, 3)]
        slot = [sum(1 for p in mkseason.slots_of(rec[24]) if mkseason._POS_CLASS[p] == c) for c in (1, 2, 3)]
        info.append(f'{club} {tac} XI {", ".join(xi)} | bench {", ".join(be)} (D/M/A {cls}, slots {slot})')
        exp = expected(club)
        if exp:
            T.check(sorted(xi) == sorted(exp[0]), f'{club} XI in game {xi} != reallineups {exp[0]}', errs)
            T.check(sorted(be) == sorted(exp[1]), f'{club} bench in game {be} != reallineups {exp[1]}', errs)
        # every club record the game holds now (its league's file): the DATA tactic + lineup
        m = r.mem
        seen, bad, tacs = 0, [], {}
        for nm, w in recs.items():
            if nm == club:
                continue
            k = m.find(bytes(w[:22]))
            if k < 0:
                continue
            seen += 1
            if m[k + 24] != w[24] or m[k + 60:k + 76] != bytes(w[60:76]):
                bad.append(nm)
            tacs[w[24]] = tacs.get(w[24], 0) + 1
        T.check(seen >= 10, f'only {seen} other club records found in memory', errs)
        T.check(not bad, f'{len(bad)} clubs in memory differ from DATA (tactic / lineup): {bad[:8]}', errs)
        grp = group_of(club)                    # (Marco S.: a Serie D career saw only 4-4-2 opponents)
        if grp:
            got = {}
            for nm in grp:
                k = m.find(bytes(recs[nm][:22])) if nm in recs else -1
                if k >= 0:
                    got[nm] = m[k + 24]
            tl = {mkseason.TACTICS[t] if t < 12 else t for t in got.values()}
            T.check(len(got) >= 3 and len(tl) >= 2, f'{club} group opponents in memory {len(got)}, tactics {tl}', errs)
            info.append(f'group opponents: ' + ', '.join(f'{nm} {mkseason.TACTICS[t] if t < 12 else t}'
                                                        for nm, t in list(got.items())[:6]) + f' ... ({len(got)}, {len(tl)} tactics)')
        info.append(f'{seen} other clubs in memory = DATA, tactics ' +
                    ', '.join(f'{mkseason.TACTICS[t] if t < 12 else t} {k}' for t, k in sorted(tacs.items(), key=lambda x: -x[1])))
    return (not errs), '; '.join(errs + info)


def group_of(club):
    """The other clubs of club's division (clubs.csv of the data dir's ita pack), or [] without it."""
    import csv
    f = os.path.join(data_dir(), 'ita', 'clubs.csv')
    if not os.path.exists(f):
        return []
    rows = list(csv.DictReader(open(f, encoding='utf-8')))
    d = next((r['division'] for r in rows if r['name'] == club and r['file'] == 'league'), None)
    return [r['name'] for r in rows if r['file'] == 'league' and r['division'] == d and r['name'] != club] if d else []


def register(mod):
    global T
    T = mod
    sc = mod.scenario

    @sc
    def world_tactics_juve():
        """4.2 club tactics + real line-ups: a new World 2026-27 career at JUVENTUS - careerTeam's tactic and lineup =
        the DATA record's, XI / bench = reallineups (Vicario in goal, Pinsoglio on the bench); every other club the game
        holds = its DATA tactic + lineup"""
        return run(['SERIE A'], 'JUVENTUS', 'tacgate')

    @sc
    def world_tactics_milan():
        """4.2 club tactics + real line-ups: as world_tactics_juve at MILAN (Camarda not in the XI)"""
        return run(['SERIE A'], 'MILAN', 'tacgate')

    @sc
    def world_tactics_serieb():
        """4.2 club tactics + real line-ups: as world_tactics_juve at a Serie B club (TACGATE_B, default PALERMO)"""
        return run(['SERIE B'], os.environ.get('TACGATE_B', 'PALERMO'), 'tacgate')


    @sc
    def world_tactics_seried():
        """4.2 club tactics (Marco S.: a Serie D career showed only 4-4-2 opponents): a new World 2026-27 career at
        CELLE VARAZZE (Serie D girone A) - every club in memory = its DATA tactic + lineup, the group's opponents on
        two or more tactics"""
        return run(['SERIE D', 'SERIE D GIRONE A'], 'CELLE VARAZZE', 'tacgate')


if __name__ == '__main__':
    import swostest
    register(swostest)
    swostest.main(['run'] + sys.argv[1:]) if hasattr(swostest, 'main') else None
