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
# W (P5 world_fport_ld_win, MC 15/11): one match at 95 (PLAYED when the save is made), two legs at 99 / 103 (the save
# after the first), one at 107 (queued) - odd units, after INTER's Supercoppa window [56, 93] (the calendar starts at 56)
SCHED_W = '95/95/1/1/0/0/103;99/103/2/1/0/0/103;107/107/1/1/4/1/103'
ID_W = {95: 0x7E00, 99: 0x7E01, 107: 0x7E02}            # (the test fixtures' match ids' low word - the log's: season 126
#   (7Eh) << 8 | their index; fpad.c test_add: 7E000000h | season << 8 | index)
TEAM_SD = 'EUROPA,ITALIA,SERIE D,SERIE D GIRONE A,CELLE VARAZZE'
SCHED_SD = '115/115/1/1/0/0/103;107/107/1/1/0/0/103;130/130/1/1/0/0/103'
# fp_step's deepest static chain on the game stack (cobj -fstack-usage, engine 1522654): fp_step 60 > sr_port_poll 32 >
# check 44 > reserved 120 > h_prev 24, + return addresses: 300 B; MC's rule: free at entry >= chain + 512
STK_CHAIN = 300
FL = {1: 'ADD', 2: 'INST', 3: 'RES', 4: 'REFUSED', 5: 'MISSED', 6: 'REVAL', 7: 'SIM', 8: 'ORPHAN', 9: 'NEW', 10: 'LOAD',
      11: 'SEASON', 12: 'LEG', 13: 'LEGX', 14: 'PLOAD'}
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


# Q13 probe (Supercoppa Serie C design 16/11, gap G4 / risk R1): one match at L + 1 = 129 (SCHED_Q13C, the chain:
# three at 129, 130, 131, the second away - rule 5 refuses the 2nd and 3rd at add, sr_port.c:80-81, unless the build
# has the test-only FPORT_R5OFF, fpad.c h_prev) for CAMPOBASSO (Serie C
# girone B, ita division 3: the league's last unit L = 128), forced group winner (DPLAY_FORCE 101 + GPLAY_FORCE 1: no
# play-off of its own). Gap G3 (fport's unconditional [128, END] dplay / play-out windows refuse it at add) bypassed
# with the test-only FPORT_WINEDIT '-128' (every window starting at 128 dropped from the build's table)
TEAM_Q13 = os.environ.get('FPGATE_Q13_TEAM') or 'EUROPA,ITALIA,?SERIE C,GIRONE B|SERIE C GIRONE B,CAMPOBASSO'
SCHED_Q13 = os.environ.get('FPGATE_Q13_SCHED') or '129/129/1/1/0/255/0'
SCHED_Q13C = '129/129/1/1/0/255/0;130/130/1/1/4/255/0;131/131/1/1/0/255/0'
L_Q13 = 128


def run_q13(tag='fpgate_q13', SCHED_Q13=SCHED_Q13, extra=None):
    exe, skip = gate_exe(tag, SCHED_Q13, dict(FPORT_WINEDIT='-128', DPLAY_FORCE='101', GPLAY_FORCE='1', **(extra or {})))
    if skip:
        return True, skip
    off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
    cal = T.CAL_AT - 4
    ok, msg, lines = T.sc_season(TEAM_Q13, dict(W8485_BUILD=exe, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE},{cal:x}:3000'))
    log = season_log(lines, off)
    cals = [T.cal_entries(bytes.fromhex(ln.split()[2])) for ln in lines if ln.startswith(f'HEX {cal:x} ')]
    seas = [bytes.fromhex(ln.split()[2])[0] for ln in lines if ln.startswith(f'HEX {sp:x} ')]
    open(os.path.join(T.RUNS, f'{tag}.txt'), 'w').write('\n'.join(map(str, log)) + '\n' + '\n'.join(
        f'CAL {len(c)} entries, slot 0 {[e[1] for e in c if e[0] == 0]}, other {[e for e in c if e[0]]}' for c in cals) + '\n')
    errs = []
    T.check(ok, f'season (4: the season end, the next season, its save): {msg}', errs)
    first = log[:[e[0] for e in log].index('SEASON')] if 'SEASON' in [e[0] for e in log] else log
    us = [int(x.split('/')[0]) for x in SCHED_Q13.split(';')]
    adds = [e for e in first if e[0] == 'ADD']
    T.check([(e[2], e[4] & 255) for e in adds] == [(0, u) for u in us], f'adds {adds} (want rc 0, units {us})', errs)
    inst = [e for e in first if e[0] == 'INST']
    T.check([(e[2], e[1], e[4] & 255) for e in inst] == [(1, p, u) for p, u in zip([L_Q13] + us, us)],
            f'(1) installs {inst} (want one per fixture, each at the advance from the unit before: {L_Q13}, then the previous match)', errs)
    legs = [e for e in first if e[0] == 'LEG']
    T.check([e[1] for e in legs] == us, f'(2) legs {legs} (want one per fixture, played at {us})', errs)
    res = [e for e in first if e[0] == 'RES']
    T.check([(e[1], e[4] >> 4 & 15, e[3]) for e in res] == [(u, 0, i[3]) for u, i in zip(us, inst)],
            f'(3) results {res} (want each installed fixture\'s, at {us}, status 0)', errs)
    bad = [e for e in first if e[0] in ('REFUSED', 'ORPHAN', 'MISSED', 'SIM')]
    T.check(not bad, f'refused / orphan / missed / simulated {bad}', errs)
    T.check(len(set(seas)) >= 2, f'(4) seasonPlaying values {seas} (want the next season reached)', errs)
    lg = [[e[1] for e in c if e[0] == 0] for c in cals if c]
    T.check(lg and all(x == lg[0] for x in lg) and lg[0][-1] == L_Q13,
            f'(5) the league\'s calendar days moved: {[x for x in lg if x != lg[0]][:2]} vs {lg[0] if lg else None}', errs)
    s4 = sorted({e[:2] for c in cals for e in c if e[0] == 4 and e[1] > L_Q13})
    T.check(all((4, u) in s4 for u in us), f'(1) no slot-4 calendar entry at each of {us} ({s4})', errs)
    return not errs, '; '.join(errs) or f'adds {adds}, installs {inst}, legs {[(e[1], e[4] & 255, e[4] >> 8) for e in legs]} (unit, home, away goals), ' \
        f'results {[(e[1], hex(e[3]), e[4] & 15) for e in res]} (unit, id, winner side); league days {len(lg[0])} to {lg[0][-1]}, ' \
        f'slot-4 entries after L {s4}; seasons {sorted(set(seas))}; {msg[:80]}'


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
    def world_fport_q13():
        """Q13 probe (Supercoppa Serie C, gap G4): a K_PORT match at L + 1 = 129, after the career league's last unit
        128, for CAMPOBASSO forced Serie C group winner (test-only FPORT_WINEDIT '-128' drops the season-end windows:
        gap G3 bypassed) - installed at the advance from 128, played in slot 4, its result back through fp_done, the
        season ends and the next one starts, the league's own days untouched"""
        return run_q13()

    @sc
    def world_fport_q13_chain():
        """Q13 probe, the chain: three K_PORT matches at 129, 130, 131 (the Supercoppa's three days), each installed at
        the advance from the unit before - the calendar's only entries after 128 are the port's own. Rule 5 as it
        stands refuses the 2nd and 3rd (sr_port.c:80-81: the earlier must end strictly before the later's install
        advance): this build bypasses it with the test-only FPORT_R5OFF=128 (fpad.c h_prev: past 128 the install unit
        reported is the fixture's own unit)"""
        return run_q13('fpgate_q13c', SCHED_Q13C, dict(FPORT_R5OFF=str(L_Q13)))

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
        arms, the next step inits with the flag; P5 (MC option A): the FP item restores the queue (PLOAD rc = the
        fixtures, 1 leg played), REVAL before any poll / install, no ADD (the test fixtures are in the loaded queue),
        the tie's second leg credited (RES accepted, no ORPHAN), the one-match tie at 99 then installed, played,
        accepted"""
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
        T.check(codes[:3] == ['LOAD', 'PLOAD', 'REVAL'], f'after the load {codes[:4]}, want LOAD, PLOAD, REVAL first', errs)
        pl = [e for e in log if e[0] == 'PLOAD']
        T.check(len(pl) == 1 and pl[0][2] >= 2 and pl[0][4] == 1,
                f'PLOAD {pl} (rc: the queue - >= 2 fixtures; y: 1 leg played)', errs)
        first = codes[:codes.index('SEASON')] if 'SEASON' in codes else codes
        T.check('ADD' not in first, f'ADD after the load {first} (the loaded queue holds the test fixtures)', errs)
        T.check(li and li[0][0] == 'LOAD' and all(i[1] == i[2] for i in li) and all(i[0] == 'SEASON' for i in li[1:]),
                f'inits after the load {li} (LOAD first, then one SEASON per new season)', errs)
        T.check('ORPHAN' not in first, f'orphans {first.count("ORPHAN")} (P5: the second leg is credited)', errs)
        res = [e for e in log[:len(first)] if e[0] == 'RES']
        T.check(len(res) == 2 and all(e[4] >> 4 & 15 == 0 for e in res) and [e[1] for e in res] == [97, 99],
                f'results after the load {res} (the two-leg tie at 97, then the 99 tie: accepted)', errs)
        T.check('REFUSED' not in codes, f'refused {[e for e in log if e[0] == "REFUSED"]}', errs)
        return not errs, '; '.join(errs) or f'{codes}; {msg2[:60]}'

    @sc
    def world_fport_ld_bad():
        """4.2 fixture port P5 (MC option A): world_fport_load's mid save with a bad FP item - its port section's pack
        hash flipped (refused: PLOAD rc < 0) and with no FP item at all (an older save: PLOAD rc 0, nothing) - each
        loads with an empty queue: the tie in slot 4 an ORPHAN, the test fixtures re-added, the 99 tie accepted"""
        exe, skip = gate_exe('fpgate_a', SCHED_A)
        if skip:
            return True, skip
        errs, info = [], []
        for how, rc in (('hash', True), ('old', False)):
            ok, msg, log = ld_variant(exe, how)
            T.check(ok, f'{how}: {msg[:300]}', errs)
            check_refused(how, log, rc, errs)
            info.append(f'{how}: {[e[0] for e in log]}')
        return not errs, '; '.join(errs) or '; '.join(info)

    def ld_win(cases):
        """SCHED_W's mid save (95 PLAYED, 99 / 103 after its first leg, 107 queued) loaded by builds whose slot-4 window
        table differs (FPORT_WINEDIT; FP_HASH ignores the windows: accepted) - cases [(name, edit)]"""
        exe, skip = gate_exe('fpgate_w', SCHED_W)
        if skip:
            return True, skip
        mid, err = mid_save(exe)
        if not mid:
            return False, err
        it = fp_item(mid)
        if not it or it[0] != 1 or it[1] != ID_W[99] or it[2].get(ID_W[95]) != 2:
            return False, f'the mid save is not after 99\'s first leg with 95 played: FP item {it}'
        errs, info = [], []
        for how, edit in cases:
            lx, _ = gate_exe('fpgate_w' + how, SCHED_W, dict(FPORT_WINEDIT=edit))
            ok, msg, log = load_log(lx, mid, 'win_' + how)
            codes = [e[0] for e in log]
            info.append(f'{how}: {codes}')
            T.check(ok, f'{how}: {msg[:300]}', errs)
            errs += win_errs(how, log)
        return not errs, '; '.join(errs + info)

    @sc
    def world_fport_ld_win():
        """4.2 fixture port P5 (MC 15/11): a save loaded by a build with another slot-4 window table (accepted: FP_HASH
        ignores the windows). rem: a window removed (INTER's Supercoppa [56, 93]) - nothing moves: REVAL 0, the tie's
        second leg and 107 credited. addq: a window [105, 109] over the queued 107 - REVAL refuses it (rule 6), the tie
        still credited, 107 stays queued and is simulated at its poll (never installed). addp: a window [94, 96] over
        the PLAYED 95 - never touched (engine 52301fb: rules 1 / 6 skip PLAYED fixtures): REVAL 0, everything credited.
        REVAL logs every failing fixture (sr_port_revalidate_all: one entry per id, y = how many)"""
        return ld_win((('rem', '-56'), ('addq', '+105:109'), ('addp', '+94:96')))

    @sc
    def world_fport_ld_s4():
        """4.2 fixture port P5 (MC option A, the slot-4 cross-check): world_fport_load's mid save, the pending
        fixture's home side changed in the FP item (slot 4 holds the real tie): refused (PLOAD rc < 0), an empty
        queue - the tie in slot 4 an ORPHAN, the test fixtures re-added, the 99 tie accepted"""
        exe, skip = gate_exe('fpgate_a', SCHED_A)
        if skip:
            return True, skip
        errs = []
        ok, msg, log = ld_variant(exe, 's4')
        T.check(ok, f's4: {msg[:300]}', errs)
        check_refused('s4', log, True, errs)
        return not errs, '; '.join(errs) or f's4: {[e[0] for e in log]}'


def win_errs(how, log):
    """ld_win's checks of one case's decoded log (the window-edit build's load of SCHED_W's mid save): [error, ..].
    addq (MC 15/11): REVAL refuses the queued 107 once, 107 stays queued, refused + simulated at its poll (a SIM, then
    its RES) and never installed; the other cases: REVAL 0, 107 installed and credited. Control (a 107 wrongly
    installed in addq must FAIL): tools/hosttest/tests/test_fpgate_win.py."""
    errs, codes = [], [e[0] for e in log]

    def chk(c, m):
        if not c:
            errs.append(m)

    pl = [e for e in log if e[0] == 'PLOAD']
    chk(codes[:3] == ['LOAD', 'PLOAD', 'REVAL'] and pl[0][2] == 3 and pl[0][4] == 1,
        f'{how}: after the load {log[:3]} (want LOAD, PLOAD rc 3 / 1 leg, REVAL)')
    rv = [e for e in log if e[0] == 'REVAL']
    res = {e[3]: e[4] >> 4 & 15 for e in log if e[0] == 'RES'}
    inst = [e[3] for e in log if e[0] == 'INST']
    chk('ORPHAN' not in codes and res.get(ID_W[99]) == 0, f'{how}: the tie 99 / 103 not credited ({res})')
    if how == 'addq':                   # (MC 15/11: stays QUEUED, SLOT4_RESERVED at its poll -> simulated)
        chk(len(rv) == 1 and rv[0][2] < 0 and rv[0][3] == ID_W[107] and rv[0][4] == 1,
            f'{how}: REVAL {rv} (want one entry: < 0 naming 107, 1 failing)')
        sim = [e for e in log if e[0] == 'SIM' and e[3] == ID_W[107]]      # (simulated at its poll: SIM, then
        chk(ID_W[107] not in inst and len(sim) == 1 and 'REFUSED' in codes,   # its RES - never installed)
            f'{how}: 107 installed / not simulated ({inst}, SIM {sim}, {codes})')
    else:
        chk(len(rv) == 1 and rv[0][2] == 0 and rv[0][4] == 0, f'{how}: REVAL {rv} (want 0: nothing moves)')
        chk(ID_W[107] in inst and res.get(ID_W[107]) == 0, f'{how}: 107 not installed + credited ({inst}, {res})')
    return errs


def mid_save(exe):
    """world_fport_load's mid-season save (the two-leg tie after its first leg), made once per build (cached by exe)."""
    import re, shutil
    keep = os.path.join(T.RUNS, 'fpgate_mid-' + os.path.basename(exe.rstrip('/')) + '.CAR')
    if os.path.exists(keep):
        return keep, ''
    pm = sym(exe, 'gplay', 'GP_PMID', 2)
    ok, msg, _ = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_MIDSAVE=f'{pm:x}:1:1'))
    m = re.search(r'saved mid-season: (\S+\.CAR)', msg)
    if not (ok and m):
        return None, f'no mid-season save: {msg[:300]}'
    shutil.copy(m.group(1), keep + '.tmp')
    os.replace(keep + '.tmp', keep)
    return keep, ''


def ld_variant(exe, how):
    """The mid save with its FP item edited (P5 gates): 'hash' the port section's pack hash flipped, 'old' no FP item
    (its tag cleared: an older save), 's4' the pending fixture's home side another club (slot 4 disagrees). Loaded,
    played to the season end: (ok, msg, the decoded log up to the next SEASON)."""
    import fpad
    mid, err = mid_save(exe)
    if not mid:
        return False, err, []
    d = bytearray(open(mid, 'rb').read())
    k = d.find(struct.pack('<HH', __import__('engine').item_id('FP'), fpad.SAVE_SIZE))
    if k < 0:
        return False, 'no FP item in the mid save', []
    b, h = k + 4, k + 4 + fpad.SAVE_HDR             # (the item; its sr_port section)
    if how == 'hash':
        d[h + 4] ^= 0xFF
    elif how == 'old':
        d[b:b + 4] = bytes(4)
    elif how == 's4':
        pend = struct.unpack_from('<I', d, h + 8)[0]
        n = struct.unpack_from('<H', d, h + 2)[0]
        i8, hit = h + 20, False
        for _ in range(n):
            if struct.unpack_from('<I', d, i8)[0] == pend:
                d[i8 + 13] ^= 0x01                  # (home's ordinal: another club of the same file)
                hit = True
            i8 += 33 + (16 if d[i8 + 32] == 2 else 0)
        if not hit:
            return False, f'no pending fixture {pend} in the FP item', []
    car = os.path.join(T.RUNS, f'fpgate_ld_{how}.CAR')
    open(car, 'wb').write(d)
    return load_log(exe, car, how)


def load_log(exe, car, how):
    """car loaded by exe, played to the season end: (ok, msg, the decoded log up to the next SEASON)"""
    off, sp = fp_st_at(exe), sym(exe, 'gplay', 'SEASONPLAYING', 2)
    ok, msg, lines = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_FROM=car, W8485_HEX=f'{sp:x}:1,o4/{off:x}:{ST_SIZE}'), 2)
    log = season_log(lines, off)
    open(os.path.join(T.RUNS, f'fpgate_ld_{how}.txt'), 'w').write('\n'.join(map(str, log)) + '\n')
    codes = [e[0] for e in log]
    return ok, msg, log[:codes.index('SEASON')] if 'SEASON' in codes else log


def fp_item(car):
    """(header nleg, pending match id, {match id: state}) of a .CAR's FP item (ids: low words), or None"""
    import fpad
    d = open(car, 'rb').read()
    k = d.find(struct.pack('<HH', __import__('engine').item_id('FP'), fpad.SAVE_SIZE))
    if k < 0:
        return None
    b = k + 4
    h = b + fpad.SAVE_HDR
    n, pend = struct.unpack_from('<H', d, h + 2)[0], struct.unpack_from('<I', d, h + 8)[0]
    st, i8 = {}, h + 20
    for _ in range(n):
        st[struct.unpack_from('<I', d, i8)[0]] = d[i8 + 32]
        i8 += 33 + (16 if d[i8 + 32] == 2 else 0)
    return d[b + 5], pend & 0xFFFF, {k & 0xFFFF: v for k, v in st.items()}   # (ids: their low word, as the log's)


def check_refused(how, log, want_rc, errs):
    """A refused / absent FP item: an empty queue - the tie in slot 4 plays as an ORPHAN, FPORT_TEST re-adds its
    fixtures, the 99 tie installed, played, accepted; no crash"""
    codes = [e[0] for e in log]
    T.check(codes[:3] == ['LOAD', 'PLOAD', 'REVAL'], f'{how}: after the load {codes[:4]}', errs)
    pl = [e for e in log if e[0] == 'PLOAD']
    T.check(len(pl) == 1 and (pl[0][2] < 0 if want_rc else pl[0][2] == 0) and pl[0][4] == 0,
            f'{how}: PLOAD {pl} (want rc {"< 0" if want_rc else "0: none"}, no tie in progress)', errs)
    T.check(codes.count('ORPHAN') == 1, f'{how}: orphans {codes.count("ORPHAN")} (the tie in slot 4: 1)', errs)
    T.check('ADD' in codes, f'{how}: no ADD (the empty queue: FPORT_TEST re-adds)', errs)
    res = [e for e in log if e[0] == 'RES']
    T.check(len(res) == 1 and res[0][1] == 99 and res[0][4] >> 4 & 15 == 0, f'{how}: results {res} (the 99 tie)', errs)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import swostest
    register(swostest)
    sys.exit(swostest.main(sys.argv[1:]))
