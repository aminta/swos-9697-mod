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
# (file 103, no league clash: the probe's run B) at 100 / 102; one tie away at 106 (flag 4); one after the league's end
# window (B 128: refused)
SCHED_A = os.environ.get('FPGATE_SCHED') or '60/60/1/1/0/0/103;100/102/2/1/0/0/103;106/106/1/1/4/1/103;134/134/1/1/0/2/103'
FL = {1: 'ADD', 2: 'INST', 3: 'RES', 4: 'REFUSED', 5: 'MISSED', 6: 'REVAL', 7: 'SIM', 8: 'ORPHAN', 9: 'NEW', 10: 'LOAD',
      11: 'SEASON', 12: 'LEG'}
MAGIC, ST_SIZE = 0x50504631, 420


def world_env(extra=None):
    src = os.environ.get('W2627REL_DATA') or os.path.join(T.MAIN, 'internal', 'world2526', 'world5tm-h2')
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])}
    env.update(extra or {})
    return src, env


def gate_exe(name, sched, extra=None):
    src, env = world_env(dict(FPORT='1', FPORT_TEST=sched, **(extra or {})))
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


def run_a(tag='fpgate_a', sched=SCHED_A, extra=None):
    exe, skip = gate_exe(tag, sched)
    if skip:
        return True, skip
    off = fp_st_at(exe)
    ok, msg, lines = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_HEX=f'o4/{off:x}:{ST_SIZE}', **(extra or {})))
    log = season_log(lines, off)
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
    T.check(log and log[0][0] == 'NEW', f'first entry {log[:1]} (fp_new -> init at the first step)', errs)
    return not errs, '; '.join(errs) or f'{len(log)} log entries: adds {[e[2] for e in adds]}, installs {len(inst)}, ' \
        f'legs {[(e[1], e[4] & 255, e[4] >> 8) for e in legs]}, results {[(e[1], e[4] & 15) for e in res]}; {msg[:60]}'


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
    def world_fport_load():
        """4.2 fixture port P2 gate (MC 2): a save mid-season between the two-leg tie's legs (GP_WK 102), loaded: fp_load
        arms, the next step inits with the flag, REVAL logged before any poll / install; interim before P5 (no FP save
        section): the tie's second leg is played and logged as an ORPHAN (not credited), the queue re-added by
        FPORT_TEST, the one-match tie at 106 then installed, played, accepted"""
        exe, skip = gate_exe('fpgate_a', SCHED_A)
        if skip:
            return True, skip
        off = fp_st_at(exe)
        wk = sym(exe, 'gplay', 'GP_WK', 2)
        ok, msg, l1 = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_MIDSAVE=f'{wk:x}:102:1',
                                              W8485_HEX=f'o4/{off:x}:{ST_SIZE}'))
        mid = os.path.join(T.RUNS, T.w84_tag() + '_1', 'mid')
        ok2, msg2, l2 = T.sc_season(TEAM, dict(W8485_BUILD=exe, W8485_FROM=mid, W8485_HEX=f'o4/{off:x}:{ST_SIZE}'), 2)
        log = season_log(l2, off)
        open(os.path.join(T.RUNS, 'fpgate_load.txt'), 'w').write('\n'.join(map(str, log)) + '\n')
        errs = []
        T.check(ok and ok2, f'seasons: {msg} / {msg2}', errs)
        codes = [e[0] for e in log]
        T.check(codes[:2] == ['LOAD', 'REVAL'], f'after the load {codes[:4]}, want LOAD, REVAL first', errs)
        T.check(codes.count('ORPHAN') == 1, f'orphans {codes.count("ORPHAN")} (the second leg after the load: 1)', errs)
        res = [e for e in log if e[0] == 'RES']
        T.check(len(res) == 1 and res[0][4] >> 4 & 15 == 0, f'results after the load {res} (the 106 tie)', errs)
        T.check('REFUSED' not in codes, f'refused {[e for e in log if e[0] == "REFUSED"]}', errs)
        return not errs, '; '.join(errs) or f'{codes}; {msg2[:60]}'


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import swostest
    register(swostest)
    sys.exit(swostest.main(sys.argv[1:]))
