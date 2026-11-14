"""4.2 fixture port P2 gate (Motore; MC 14/11): fpad.c on a World 2026-27 career, an FPORT=1 FPORT_TEST build (test
builds only). The probe's schedules (42-fprobe) as port fixtures: sr_port_add's rules, the install in slot 4 through
gplay (K_PORT), the legs' goals from cseg_2AE97 (fp_leg), the result checked by the engine (fp_done ->
sr_port_result_in: 0 = accepted), the fixtures refused by a slot-4 window simulated (missed), the load path (MC 2:
the flag, revalidate before the poll). FP_ST (swe.c .bss, obj4) read through W8485_HEX o4/.

Registered by swostest (register(mod), as zonetest) or run alone: python3 tools/fpgate.py <scenario>."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = None
TEAM = os.environ.get('FPGATE_TEAM') or 'EUROPA,ITALIA,SERIE A,INTER'
# A: 60 inside INTER's Supercoppa window [56, 93] (rule 6: refused at add, never installed); two legs v a Spanish club
# (file 103) at 95 / 97 and one tie away at 99 (flag 4) - odd units: Serie A plays every even unit 94-128 (rule 1);
# one after the league's end window (B 128: refused)
SCHED_A = os.environ.get('FPGATE_SCHED') or '60/60/1/1/0/0/103;95/97/2/1/0/0/103;99/99/1/1/4/1/103;134/134/1/1/0/2/103'
# Serie D girone A (CELLE VARAZZE, ita division 5: 9 distinct windows - placement / play-out / poule [60, 61] [62, 63]
# [71, 73], Coppa D [77, 78] .. [106, 112], season end [128, end]): 115 between them (no league match: accepted), 107
# in the 8th window and 130 in the last (refused at add: every window read, SR_PORT_WINDOWS 24 - MC 14/11)
TEAM_SD = 'EUROPA,ITALIA,SERIE D,SERIE D GIRONE A,CELLE VARAZZE'
SCHED_SD = '115/115/1/1/0/0/103;107/107/1/1/0/0/103;130/130/1/1/0/0/103'
# fp_step's deepest static chain on the game stack (cobj -fstack-usage, engine 1522654): fp_step 60 > sr_port_poll 32 >
# check 44 > reserved 120 > h_prev 24, + return addresses: 300 B; MC's rule: free at entry >= chain + 512
STK_CHAIN = 300
FL = {1: 'ADD', 2: 'INST', 3: 'RES', 4: 'REFUSED', 5: 'MISSED', 6: 'REVAL', 7: 'SIM', 8: 'ORPHAN', 9: 'NEW', 10: 'LOAD',
      11: 'SEASON', 12: 'LEG', 13: 'LEGX'}
MAGIC, ST_SIZE = 0x50504631, 420


def world_env(extra=None):
    src = os.environ.get('W2627REL_DATA') or os.path.join(T.MAIN, 'internal', 'world2526', 'world5tm-h2')
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])}
    env.update(extra or {})
    return src, env


def gate_exe(name, sched, extra=None):
    src, env = world_env(dict(FPORT='1', FPORT_TEST=sched, **(extra or {})))   # (extra: BPLACE_FORCE / FPORT_ETFORCE)
    if not os.path.isdir(src):
        return None, f'SKIP: private data {src} missing'
    return os.environ.get('FPGATE_BUILD') or T.build(name, env=env), None


def sym(exe, mod, name, obj):
    import json
    s = json.load(open(os.path.join(exe, 'ITALIAN.syms.json'))).get(mod, {}).get(name)
    assert s and s[0] == obj, (f'fpgate: {mod}.{name} not in ITALIAN.syms.json (obj{obj})', s)
    return s[1]


def fp_st_at(exe):
    return sym(exe, 'fpad', 'FP_ST', 4)


def decode(b):
    """FP_ST bytes -> (magic, season, loaded, nlog, [(code, unit, rc, id, y)] in order)"""
    magic, season, loaded, _tadded, nlog = struct.unpack_from('<IBBBB', b, 0)
    ents = []
    for i in range(min(nlog, 48)):
        c, u, rc, _x, mid, y = struct.unpack_from('<BBbBHH', b, 36 + 8 * i)
        ents.append((FL.get(c, c), u, rc, mid, y))
    return magic, season, loaded, nlog, ents


def states(lines, off):
    p = f'HEX o4/{off:x} '
    return [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(p)]


def season_log(lines, off):
    """every log entry seen (FP_ST's successive states merged, the log restarting at each init)"""
    out, last = [], []
    for b in states(lines, off):
        m, s, ld, n, e = decode(b)
        if m != MAGIC:
            continue
        if len(e) < len(last) or e[:len(last)] != last:
            last = []
        out += e[len(last):]
        last = e
    return out


INITS = ('NEW', 'SEASON', 'LOAD')


def season_inits(lines, off, sp):
    """MC (P2 review 2): [(init code, its season y, seasonPlaying then)] in log order, and the seasons in which the port
    ran (seasonPlaying - W8485_HEX on the game's byte, obj2 sp - at every FP_ST state under the magic): every init must
    carry the season then current, every season the port ran in exactly one init"""
    cur, seen, out, last = None, set(), [], []
    pk, ps = f'HEX o4/{off:x} ', f'HEX {sp:x} '
    for ln in lines:
        if ln.startswith(ps):
            cur = bytes.fromhex(ln.split()[2])[0]
        elif ln.startswith(pk):
            m, _s, _ld, _n, e = decode(bytes.fromhex(ln.split()[2]))
            if m != MAGIC:
                continue
            seen.add(cur)                       # (a season in which the port ran: an FP_ST state under FP_MAGIC)
            if len(e) < len(last) or e[:len(last)] != last:
                last = []
            out += [(x[0], x[4], cur) for x in e[len(last):] if x[0] in INITS]
            last = e
    return out, seen


def check_inits(inits, seen, errs, nseasons):
    bad = [i for i in inits if i[1] != i[2]]
    T.check(not bad, f'inits whose season is not the one current {bad}', errs)
    ran = sorted(x for x in seen if x is not None)
    have = sorted(i[1] for i in inits if i[0] != 'LOAD')   # (a load is an explicit init of its own, MC 2: extra)
    want = ran if not inits or inits[0][0] != 'LOAD' else ran[1:]   # (a run from a load: its first season's init is it)
    T.check(have == want and len(ran) >= nseasons, f'inits {inits}: one NEW / SEASON per season the port ran in {ran} '
            f'(>= {nseasons}; LOAD inits extra)', errs)


def seasons2(team, extra):
    """swostest.sc_season with W8485_ONE '' (two seasons: sc_season forces '1') -> (ok, msg, lines of both seasons)"""
    keys = ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K', 'W8485_NOSACK', 'W8485_ONE', 'W8485_HEX')
    keep = {k: os.environ.get(k) for k in keys}
    os.environ.update(W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1',
                      W8485_ONE='', **extra)
    try:
        ok, msg = T.world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lines = []
    for n in (1, 2):
        p = os.path.join(T.RUNS, T.w84_tag() + f'_{n}', 'session.log')
        if os.path.exists(p):
            lines += open(p, errors='replace').read().splitlines()
    return ok, msg, lines


def stk_free(exe, lines):
    """FP_STKFREE's last value in the session's HEX lines (the least free stack at fp_step's entry), or None"""
    at = sym(exe, 'fpad', 'FP_STKFREE', 4)
    v = [struct.unpack('<I', bytes.fromhex(ln.split()[2]))[0] for ln in lines if ln.startswith(f'HEX o4/{at:x} ')]
    v = [x for x in v if x != 0xFFFFFFFF]
    return min(v) if v else None


def check_stk(exe, lines, errs):
    f = stk_free(exe, lines)
    T.check(f is not None and f >= STK_CHAIN + 512, f'free stack at fp_step {f} B < chain {STK_CHAIN} + 512', errs)
    return f


def run_a(tag='fpgate_a', sched=SCHED_A, extra=None):
    exe, skip = gate_exe(tag, sched)
    if skip:
        return True, skip
    off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
    stk = sym(exe, 'fpad', 'FP_STKFREE', 4)
    ok, msg, lines = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE},o4/{stk:x}:4',
                                            **(extra or {})))
    log = season_log(lines, off)
    inits, seen = season_inits(lines, off, sp)
    open(os.path.join(T.RUNS, f'{tag}.txt'), 'w').write('\n'.join(map(str, log)) + '\n')
    errs = []
    T.check(ok, f'season: {msg}', errs)
    adds = [e for e in log if e[0] == 'ADD']
    want = [-16, 0, 0, -16]                     # (SR_PORT_E_SLOT4_RESERVED: 60 in [56, 93], 134 in [128, end])
    T.check([e[2] for e in adds[:4]] == want, f'adds rc {[e[2] for e in adds[:4]]}, want {want}', errs)
    inst = [e for e in log if e[0] == 'INST']
    T.check([e[2] for e in inst] == [1, 1], f'installs {inst}', errs)
    legs = [e for e in log if e[0] == 'LEG']
    T.check(len(legs) == 3, f'legs {legs} (2 + 1)', errs)
    res = [e for e in log if e[0] == 'RES']
    T.check(len(res) == 2 and all(e[4] >> 4 & 15 == 0 for e in res), f'results {res}', errs)
    bad = [e for e in log if e[0] in ('REFUSED', 'ORPHAN')]
    T.check(not bad, f'refused / orphan {bad}', errs)
    check_inits(inits, seen, errs, 1)
    fs = check_stk(exe, lines, errs)
    return not errs, '; '.join(errs) or f'{len(log)} log entries: adds {[e[2] for e in adds]}, installs {len(inst)}, ' \
        f'legs {[(e[1], e[4] & 255, e[4] >> 8) for e in legs]}, results {[(e[1], e[4] & 15) for e in res]}; ' \
        f'free stack at fp_step {fs} B (chain {STK_CHAIN} + 512); {msg[:60]}'


def run_sd(tag='fpgate_sd'):
    """CELLE VARAZZE (Serie D girone A, 9 slot-4 windows): SCHED_SD - 115 accepted, installed, played, its result
    accepted; 107 and 130 refused at add (-16: the 8th and the last window read)"""
    exe, skip = gate_exe(tag, SCHED_SD)
    if skip:
        return True, skip
    off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
    stk = sym(exe, 'fpad', 'FP_STKFREE', 4)
    ok, msg, lines = T.sc_season(TEAM_SD, dict(W8485_BUILD=exe, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE},o4/{stk:x}:4'))
    log = season_log(lines, off)
    inits, seen = season_inits(lines, off, sp)
    open(os.path.join(T.RUNS, f'{tag}.txt'), 'w').write('\n'.join(map(str, log)) + '\n')
    errs = []
    T.check(ok, f'season: {msg}', errs)
    adds = [e[2] for e in log if e[0] == 'ADD']
    T.check(adds[:3] == [0, -16, -16], f'adds rc {adds[:3]}, want [0, -16, -16] (115 free, 107 / 130 in windows 8 / 9)', errs)
    inst = [e for e in log if e[0] == 'INST']
    res = [e for e in log if e[0] == 'RES']
    T.check(len(inst) == 1, f'installs {inst} (115 only)', errs)
    T.check(len(res) == 1 and res[0][4] >> 4 & 15 == 0, f'results {res} (accepted)', errs)
    bad = [e for e in log if e[0] in ('REFUSED', 'ORPHAN')]
    T.check(not bad, f'refused / orphan {bad}', errs)
    check_inits(inits, seen, errs, 1)
    fs = check_stk(exe, lines, errs)
    return not errs, '; '.join(errs) or f'adds {adds}, install {inst}, result {[(e[1], e[4] & 15) for e in res]}; ' \
        f'free stack at fp_step {fs} B; {msg[:60]}'


def legs_detail(log):
    """every leg fp_leg stored, from the log's LEG + LEGX pairs: [(unit, home, g90 home, g90 away, et (h, a) or None,
    pens (h, a) or None)]"""
    out, pend = [], None
    for c, u, _rc, mid, y in log:
        if c == 'LEG':
            pend = (u, mid, y & 255, y >> 8)
        elif c == 'LEGX' and pend:
            out.append((*pend, None if mid == 0xFFFF else (mid & 255, mid >> 8),
                        None if y == 0xFFFF else (y & 255, y >> 8)))
            pend = None
    return out


def run_et(tag, extra, want_pens):
    """MC guard 3: BPLACE_FORCE (every decisive match level after 90 minutes / on aggregate, bf_et: no e.t. goals)
    with fp_et chained after it - SCHED_A's single match (99) and the two-leg tie's second leg (97) go to e.t.;
    want_pens: e.t. level -> penalties (BPLACE_FORCE alone); else FPORT_ETFORCE's 1-0 to the home side, no penalties.
    Each leg's 90 minutes / e.t. / penalties against the forced result; the engine's winner check (fp_done's game
    winner vs sr_port_winner: E_WINNER) against the game's own"""
    exe, skip = gate_exe(tag, SCHED_A, dict(BPLACE_FORCE='1', **extra))
    if skip:
        return True, skip
    off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
    ok, msg, lines = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE}'))
    log = season_log(lines, off)
    legs = legs_detail(log)
    open(os.path.join(T.RUNS, f'{tag}.txt'), 'w').write('\n'.join(map(str, log + legs)) + '\n')
    errs = []
    T.check(ok, f'season: {msg}', errs)
    T.check(len(legs) >= 3, f'legs {legs} (95, 97, 99)', errs)
    if len(legs) >= 3:
        l1, l2, l3 = legs[:3]
        agg = (l1[2] + l2[3], l1[3] + l2[2])           # (side 0 = leg 1's home: its goals in leg 2 are the away ones)
        T.check(l1[4] is None and l1[5] is None, f'leg 1 (not decisive) {l1}: no e.t. / penalties', errs)
        T.check(agg[0] == agg[1], f'leg 2 {l2}: aggregate after 90 minutes level (BPLACE_FORCE) {agg}', errs)
        T.check(l3[2] == l3[3], f'single match {l3}: level after 90 minutes (BPLACE_FORCE)', errs)
        et = (0, 0) if want_pens else (1, 0)
        for leg in (l2, l3):
            T.check(leg[4] == et, f'{leg}: e.t. {leg[4]}, want {et}', errs)
            T.check((leg[5] is not None and leg[5][0] != leg[5][1]) if want_pens else leg[5] is None,
                    f'{leg}: penalties {leg[5]} ({"decisive" if want_pens else "none"})', errs)
    res = [e for e in log if e[0] == 'RES']
    T.check(len(res) == 2 and all(e[4] >> 4 & 15 == 0 for e in res), f'results {res} (accepted)', errs)
    bad = [e for e in log if e[0] in ('REFUSED', 'ORPHAN')]
    T.check(not bad, f'refused / orphan {bad}', errs)
    return not errs, '; '.join(errs) or f'legs {legs[:3]}; results {[(e[1], e[4] & 15) for e in res]}; {msg[:60]}'


def register(mod):
    global T
    T = mod
    sc = mod.scenario

    @sc
    def world_fport_a():
        """4.2 fixture port P2 gate A: INTER, SCHED_A as port fixtures - two refused by slot-4 windows at add, a two-leg
        tie and a one-match tie installed through gplay, played, their results accepted by the engine"""
        return run_a()

    @sc
    def world_fport_sd():
        """4.2 fixture port (MC 14/11, SR_PORT_WINDOWS 24): a Serie D girone career (CELLE VARAZZE, 9 slot-4 windows):
        a fixture between the windows accepted and played, one in the 8th window and one in the last refused at add -
        every window of the division read"""
        return run_sd()

    @sc
    def world_fport_etp():
        """4.2 fixture port P2 (MC guard 3 + guard 1's combined build): BPLACE_FORCE + FPORT - the single match and
        the second leg level, e.t. 0-0 (bf_et, chained before fp_et's capture), penalties; each leg's 90 minutes /
        e.t. / penalties as forced, both results accepted"""
        return run_et('fpgate_etp', {}, True)

    @sc
    def world_fport_etx():
        """4.2 fixture port P2 (MC guard 3): BPLACE_FORCE + FPORT_ETFORCE - the single match and the second leg level
        after 90 minutes, e.t. 1-0 to the home side, no penalties; each leg as forced, both results accepted"""
        return run_et('fpgate_etx', dict(FPORT_ETFORCE='1'), False)

    @sc
    def world_fport_mlt():
        """4.2 fixture port P2 gate (MC: 'every career'): HAMRUN SPARTANS (Malta: no play-offs, no S7), two season
        ends - pg_fix (InitializeNewSeason) re-arms every season: exactly one init per season, each carrying the season
        then played (seasonPlaying)"""
        exe, skip = gate_exe('fpgate_a', SCHED_A)
        if skip:
            return True, skip
        off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
        team = 'EUROPA,MALTA,?MALTESE PREMIER LEAGUE|PREMIER LEAGUE,HAMRUN SPARTANS'
        ok, msg, lines = seasons2(team, dict(W8485_BUILD=exe, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE}'))
        inits, seen = season_inits(lines, off, sp)
        open(os.path.join(T.RUNS, 'fpgate_mlt.txt'), 'w').write(f'{inits}\n{seen}\n')
        errs = []
        T.check(ok, f'seasons: {msg}', errs)
        check_inits(inits, seen, errs, 2)
        return not errs, '; '.join(errs) or f'inits {inits}, seasons {sorted(seen)}; {msg[:60]}'

    @sc
    def world_fport_load():
        """4.2 fixture port P2 gate (MC 2): a save mid-season between the two-leg tie's legs (GP_PMID, the port tie's legs played, 1:
        after its first leg), loaded: fp_load
        arms, the next step inits with the flag, REVAL logged before any poll / install; interim before P5 (no FP save
        section): the tie's second leg is played and logged as an ORPHAN (not credited), the queue re-added by
        FPORT_TEST, the one-match tie at 99 then installed, played, accepted"""
        exe, skip = gate_exe('fpgate_a', SCHED_A)
        if skip:
            return True, skip
        off = fp_st_at(exe)
        pm = sym(exe, 'gplay', 'GP_PMID', 2)       # (fp_leg: the port tie's legs played, 1 = after the first)
        ok, msg, l1 = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_MIDSAVE=f'{pm:x}:1:1',
                                              W8485_HEX=f'o4/{off:x}:{ST_SIZE}'))
        import re
        m = re.search(r'saved mid-season: (\S+\.CAR)', msg)
        if not (ok and m):
            return False, f'no mid-season save: {msg[:300]}'
        mid = m.group(1)
        sp = sym(exe, 'gplay', 'SEASONPLAYING', 2)
        ok2, msg2, l2 = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_FROM=mid, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE}'), 2)
        li, _seen = season_inits(l2, off, sp)
        log = season_log(l2, off)
        open(os.path.join(T.RUNS, 'fpgate_load.txt'), 'w').write('\n'.join(map(str, log)) + '\n')
        errs = []
        T.check(ok and ok2, f'seasons: {msg} / {msg2}', errs)
        codes = [e[0] for e in log]
        T.check(codes[:2] == ['LOAD', 'REVAL'], f'after the load {codes[:4]}, want LOAD, REVAL first', errs)
        T.check(li and li[0][0] == 'LOAD' and all(i[1] == i[2] for i in li) and all(i[0] == 'SEASON' for i in li[1:]),
                f'inits after the load {li} (LOAD first, then one SEASON per new season)', errs)
        T.check(codes.count('ORPHAN') == 1, f'orphans {codes.count("ORPHAN")} (the second leg after the load: 1)', errs)
        res = [e for e in log if e[0] == 'RES']
        T.check(len(res) == 1 and res[0][4] >> 4 & 15 == 0, f'results after the load {res} (the 99 tie)', errs)
        T.check('REFUSED' not in codes, f'refused {[e for e in log if e[0] == "REFUSED"]}', errs)
        return not errs, '; '.join(errs) or f'{codes}; {msg2[:60]}'


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import swostest
    register(swostest)
    sys.exit(swostest.main(sys.argv[1:]))
